"""PredictionAgent 服务层 — 任务书组装、响应解析与提案卡构造(任务书 §2)。

三协议(``rank_candidates / analogy_edit / novel_proposal``)共用一套
确定性机制,只有输入职责与解析契约不同(提示词见 configs/prompts/):

- **任务书**由 PathwayStore(祖先链、事件/证据引用、兄弟路径)与不可变
  检索产物(候选卡与哈希)确定性组装——不能只传当前分子,更不能靠
  ``S211`` 一类展示名反推来路;模型/提示词/策略版本与剩余额度一并入卡。
- **响应解析**是确定性 JSON 校验:非法证据 ID、超量产物、缺字段、非 JSON
  都是显式 parse 结果(ok=false + error_kind),由调用方按重试上限处置。
- **提案卡**(analogy/novel 的产物)构造为证据卡形状的事件源,kind 挂牌
  ``analog_reaction``/``novel_proposal``,score_semantics 声明无校准分数;
  它们仍要过 validation 全部门禁才能入 PathwayStore。

模型输出永远不是化学事实:本模块不判定化学正确性,只判结构契约。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from ..domain.models import (
    EVIDENCE_KIND_ANALOG,
    EVIDENCE_KIND_NOVEL,
    EVIDENCE_KIND_RECORDED,
    PREDICTION_MODE_ANALOGY,
    PREDICTION_MODE_NOVEL,
    PREDICTION_MODE_RANK,
    content_hash,
    stable_id,
)
from ..domain.policy import recorded_eligibility_reasons
from ..adapters.llm_client import request_hash
from .reaction_finder import validate_retrieval_payload

PREDICTION_TASK_SCHEMA_VERSION = "v43-prediction-task-3"  # v3:donor 块带 applicability/transform/编辑协议 v2(Phase C)
PREDICTION_TASK_SCHEMA_VERSION_V2 = "v43-prediction-task-4"  # v4:S1 E1 分层候选卡(仅 rank+presentation=v2 任务;v1 任务保持 v3 逐字节不变)
PREDICTION_RESPONSE_SCHEMA_VERSION = "v43-prediction-response-1"
PREDICTION_RESULT_SCHEMA_VERSION = "v43-prediction-result-1"

MAX_REPORTABLE_PRODUCTS = 5  # 每步最多报告五个候选(任务书 §0)

# ---------------------------------------------------------------- S1 E1 协议臂
# rank_candidates v2 呈现(HIT60 S1 E1):分层候选卡 + 有界证据卡密度 +
# 完整 order 契约 + 结构化放弃理由。单一开关 domain.policy.
# rank_candidate_presentation(默认 v1 = 与历史行为逐字节一致)。

RANK_PRESENTATION_V2 = "v2"  # 值域对齐 domain.policy.RANK_PRESENTATION_VERSIONS

# 密度预算(硬上限;确定性截断,逐项留痕)。上限是界不是目标:现状合格
# recorded 卡约 600–800 字符/卡,以下取值留约 2× 余量,正常路径不触发;
# 触发时按 DENSITY_DROP_ORDER 逐级裁剪,决策字段不裁(见 _apply_density_cap)。
DENSITY_PRODUCT_SMILES_FULL_CHAR_CAP = 300   # 单条 full SMILES 字符上限
DENSITY_PER_CANDIDATE_CHAR_CAP = 1600        # 单卡序列化字符上限(不含 density 留痕块)
DENSITY_DROP_ORDER = (
    "per_product_filter_flags",   # ① 逐产物 ion/cofactor 过滤标记(最弱信号)
    "product_smiles_full",        # ② full SMILES(保留短形 + 规范身份)
    "source_n_evidence",          # ③ 来源文献行数
)

# decision=hold 的结构化放弃理由枚举(v2 解析 fail-closed 判据)。
# 枚举维度 = v2 任务书呈现的四层决策信号(来源/条件/验证/引擎)+ 密度
# 充分性 + 兜底,不含任何逐题或题库语义(I1:协议模型无关、题目无关)。
HOLD_KINDS = (
    "condition_conflict",             # 条件层:候选条件状态与任务条件冲突
    "direction_or_substrate_doubt",   # 来源层:底物/方向挂牌存疑
    "product_validity_doubt",         # 验证层:产物验证预览有红标
    "insufficient_discrimination",    # 密度层:四层信号不足以区分候选
    "engine_rank_disagreement",       # 引擎层:引擎位次与证据强度矛盾
    "other",                          # 其余(note 必填)
)
HOLD_NOTE_CHAR_CAP = 500      # hold.note 确定性截断上限(截断不失败)
REASON_TEXT_CHAR_CAP = 600    # 逐候选理由文本确定性截断上限

DISCIPLINE_RULES = [
    "model_output_is_not_chemical_fact",
    "no_declaring_exact_hit",
    "no_claiming_condition_compatibility",
    "no_calibrated_probabilities",
    "no_inventing_evidence_ids_or_structures",
]


class PredictionTaskError(RuntimeError):
    """任务书组装失败(如 analogy 模式下当前分子表示有损)。"""

    def __init__(self, reason: str, message: str):
        super().__init__(f"{reason}:{message}")
        self.reason = reason


def prediction_task_id(
    *, run_id: str, path_id: str, substrate_identity: str,
    retrieval_payload_hash: str, mode: str, model_id: str,
    prompt_versions: dict, policy_version: str, strategy_version: str,
) -> str:
    """预测任务幂等键(任务书 §4):路径+当前分子+检索产物哈希+预测模式
    +模型/提示词/策略版本。"""
    return stable_id(
        "T", run_id, path_id, "prediction", substrate_identity,
        retrieval_payload_hash, mode, model_id,
        content_hash(prompt_versions), policy_version, strategy_version,
    )


# ---------------------------------------------------------------- 任务书


def _ancestry_task_block(store, path_id: str) -> list[dict]:
    """按时间顺序的完整祖先链(根→当前),每步带父/子、事件与证据 ID。"""
    from ..domain.pathway import ancestry_chain, display_name

    chain = ancestry_chain(store, path_id)
    steps: list[dict] = []
    for i, path in enumerate(chain):
        ev = store.get_event(path.event_id) if path.event_id else None
        steps.append({
            "position": i,
            "path_id": path.path_id,
            "display_name": display_name(chain[: i + 1]),
            "substrate_identity": path.substrate_identity,
            "parent_path_id": path.parent_path_id,
            "event_id": path.event_id,
            "product_position": path.product_position,
            "depth": path.depth,
            # 事件证据引用:证据全文在不可变检索产物中,事件只持 ID+哈希
            "evidence_id": ev.evidence_id if ev else None,
            "evidence_hash": ev.evidence_hash if ev else None,
            "evidence_kind": ev.kind if ev else None,
            "evidence_source_id": ev.source_id if ev else None,
        })
    return steps


def sibling_task_block(store, path_id: str) -> list[dict]:
    """已有兄弟路径(任务书 §2):与当前路径同父的其他路径(组装时点已
    提交的产物路径)。根路径无父 → 无兄弟,返回空列表。

    每条含稳定 ID、底物身份、深度、状态、原始产物位次、入边事件引用
    (event_id/evidence_id/evidence_kind,经 store.get_event;无事件为 None)
    与展示名(第一阶段口径 ``S{深度}{完整位次链}``,由 domain.pathway 按
    结构计算,仅冗余视图 —— 不得据展示名反推来路)。兄弟范围严格限定
    同父:其他来路的同分子路径不是兄弟,不得串入。
    """
    from ..domain.pathway import ancestry_chain, display_name

    current = store.get_path(path_id)
    if current is None or current.parent_path_id is None:
        return []
    blocks: list[dict] = []
    for row in store.list_paths(current.run_id):  # 按 seq(创建序)稳定排序
        if row["parent_path_id"] != current.parent_path_id \
                or row["path_id"] == path_id:
            continue
        ev = store.get_event(row["event_id"]) if row["event_id"] else None
        blocks.append({
            "path_id": row["path_id"],
            "display_name": display_name(ancestry_chain(store, row["path_id"])),
            "substrate_identity": row["substrate_identity"],
            "depth": row["depth"],
            "status": row["status"],
            "product_position": row["product_position"],
            "event_id": ev.event_id if ev else None,
            "evidence_id": ev.evidence_id if ev else None,
            "evidence_kind": ev.kind if ev else None,
        })
    return blocks


# ----------------------------------------------- S1 E1:rank v2 分层候选呈现


def _rank_v2_candidate_card(e: dict, ancestry_cns: list[str],
                            per_card_keys: tuple[str, ...] = (),
                            ) -> tuple[dict, list[dict]]:
    """单张 v2 分层候选卡:engine / source / condition / verification 四层。

    字段白名单 = 检索卡运行时已有字段,不引入任何需要回查金标的信息;
    verification 层为确定性**预览**(与裁决层逐卡验证同源同函数:
    gate_smiles / cn_identity / is_in_path_cycle),仅呈现、不门禁 ——
    门禁语义仍在裁决层,此处不放宽也不收紧。返回 (卡, 截断清单)。

    per_card_keys:E1_DESIGN §3.1"不恒真不上提,该字段仍在逐卡层"——
    候选间**不恒真**的 uniform 候选字段(kind/match_type/mapping_status/
    donor_refs)逐卡原样保留,不静默丢失(正常 rank 任务中四字段由入围
    资格保证恒真,本参数为空)。
    """
    from ..validation.gates import gate_smiles
    from ..domain.identity import cn_identity
    from ..domain.pathway import is_in_path_cycle

    drops: list[dict] = []
    products: list[dict] = []
    for p in e.get("products", []):
        raw_full = (p.get("product_smiles_full") or "").strip()
        raw = (p.get("product_smiles") or "").strip()
        source_raw = raw_full or raw
        computed = cn_identity(source_raw) if source_raw else None
        stored = p.get("product_identity")
        parse_ok, _gate_reason = gate_smiles(source_raw)
        entry: dict = {
            "position": p.get("position"),
            "product_smiles": raw,
            "product_identity": stored,
            "parse_ok": parse_ok,
            "identity_match": bool(computed is not None
                                   and stored == computed),
        }
        if computed is not None and is_in_path_cycle(computed, ancestry_cns):
            entry["in_path_cycle"] = True
        if raw_full and raw_full != raw:
            # 密度规则 1:超长 full SMILES 截掉(短形 + 规范身份保留,
            # 决策键不丢);截断留痕,被裁 ≠ 不存在
            if len(raw_full) <= DENSITY_PRODUCT_SMILES_FULL_CHAR_CAP:
                entry["product_smiles_full"] = raw_full
            else:
                drops.append({"field": "product_smiles_full",
                              "action": "dropped_over_char_cap",
                              "chars": len(raw_full)})
        # 运行时已有的行级过滤标记(lookup 产物行)
        for flag in ("ion_filtered", "cofactor_filtered"):
            if p.get(flag) is not None:
                entry[flag] = bool(p[flag])
        products.append(entry)
    record = e.get("source_record") or {}
    card = {
        "evidence_id": e["evidence_id"],
        "engine": {
            # 引擎参照位次:检索引擎的排序,不是裁决结论(prompt 明示)
            "reference_rank": e.get("retrieval_rank"),
            "score": e.get("score"),
            "score_semantics": e.get("score_semantics"),
        },
        "source": {
            "source_id": e.get("source_id"),
            "n_evidence": record.get("n_evidence"),
        },
        "condition": e.get("condition_fit"),
        "verification": {
            "products": products,
            "all_products_parse_ok": all(p["parse_ok"] for p in products),
            "all_identity_match": all(p["identity_match"] for p in products),
            "any_in_path_cycle": any(p.get("in_path_cycle", False)
                                     for p in products),
        },
    }
    # 不恒真字段留逐卡层(见 docstring;在密度预算之前加入,预算内可裁
    # 情况与四层字段一致对待)
    for k in per_card_keys:
        card[k] = e.get(k)
    drops = _apply_density_cap(card, drops)
    return card, drops


def _apply_density_cap(card: dict, drops: list[dict]) -> list[dict]:
    """单卡密度预算:序列化(不含 density 留痕块)超
    DENSITY_PER_CANDIDATE_CHAR_CAP 时按 DENSITY_DROP_ORDER 逐级裁剪
    (确定性、可重放);evidence_id / engine / condition / verification
    聚合与 product_identity 永不裁 —— 卡间可区分性不因预算受损。"""

    def _chars() -> int:
        return len(json.dumps(card, ensure_ascii=False, sort_keys=True))

    def _drop(step: str) -> None:
        if step == "per_product_filter_flags":
            for p in card["verification"]["products"]:
                p.pop("ion_filtered", None)
                p.pop("cofactor_filtered", None)
        elif step == "product_smiles_full":
            for p in card["verification"]["products"]:
                p.pop("product_smiles_full", None)
        elif step == "source_n_evidence":
            card["source"].pop("n_evidence", None)

    for step in DENSITY_DROP_ORDER:
        if _chars() <= DENSITY_PER_CANDIDATE_CHAR_CAP:
            break
        _drop(step)
        drops.append({"field": step, "action": "dropped_over_card_cap"})
    card["density"] = {
        "per_candidate_char_cap": DENSITY_PER_CANDIDATE_CHAR_CAP,
        "truncated": drops,
    }
    return drops


UNIFORM_FACT_CANDIDATE_KEYS = ("kind", "match_type", "mapping_status",
                               "donor_refs")


def _rank_uniform_facts(cards: list[dict]
                        ) -> tuple[dict, tuple[str, ...]]:
    """逐字段核对恒真性:跨候选恒真的字段上提 candidate_set(单份),
    不恒真的返回键名列表(调用方使其留逐卡层,不静默丢失)。"""
    uniform: dict = {}
    non_uniform: list[str] = []
    for key in UNIFORM_FACT_CANDIDATE_KEYS:
        vals = [json.dumps(e.get(key), sort_keys=True, ensure_ascii=False)
                for e in cards]
        if cards and len(set(vals)) == 1:
            uniform[key] = cards[0].get(key)
        else:
            non_uniform.append(key)
    return uniform, tuple(non_uniform)


def _rank_v2_candidate_set(cards: list[dict], policy: dict,
                           truncations: list[dict],
                           uniform: dict | None = None) -> dict:
    """candidate_set:候选集级事实(上提到任务层,逐卡不再重复)。

    - uniform_facts:跨候选**恒真**的卡级字段才上提(组装时点逐字段
      核对;不恒真不上提,该字段仍在逐卡层);kind/match_type 等由
      入围资格保证恒真,通常全部上提;
    - provenance:全部候选共用的资产来源去重后单份(逐卡不再重复
      64 位 SHA 等零区分度字段);
    - answer_semantics:把下游(不变量的)答卷语义显式告知模型 ——
      选中卡产物按卡内 position 顺序占据答卷位次、宽度上限;
    - density_budget:预算常量 + 全部截断留痕。
    """
    if uniform is None:
        uniform, _ = _rank_uniform_facts(cards)
    provenance: dict[str, dict] = {}
    for e in cards:
        for src in e.get("asset_sources") or []:
            role = str(src.get("role", ""))
            if role and role not in provenance:
                provenance[role] = {
                    "asset_file": src.get("asset_file", ""),
                    "asset_sha256": src.get("asset_sha256", ""),
                }
    return {
        "presentation": RANK_PRESENTATION_V2,
        "n_candidates": len(cards),
        "selection_rule": "eligible_recorded_only",
        "uniform_facts": uniform,
        "provenance": provenance,
        "answer_semantics": {
            "answer_width": int(policy.get(
                "max_reportable_products", MAX_REPORTABLE_PRODUCTS)),
            "within_card_product_order": "fixed_by_position",
            "selected_card_products_fill_answer": "in_card_position_order",
        },
        "density_budget": {
            "per_candidate_char_cap": DENSITY_PER_CANDIDATE_CHAR_CAP,
            "product_smiles_full_char_cap":
                DENSITY_PRODUCT_SMILES_FULL_CHAR_CAP,
            "drop_order": list(DENSITY_DROP_ORDER),
            "truncated": truncations,
        },
    }


def _apply_rank_presentation_v2(task: dict, cards: list[dict],
                                policy: dict) -> dict:
    """E1 协议臂:rank 任务候选分层呈现 + 密度预算(呈现层唯一改动)。

    只读运行时已有素材(检索卡 + 任务书祖先链),不回写检索产物、不改
    入围规则、不触窗口/裁决/门禁;schema_version 升 v4 供消费端区分,
    v1 任务保持 v3 逐字节不变。
    """
    ancestry_cns = [s.get("substrate_identity") or ""
                    for s in task.get("ancestry", [])]
    uniform, non_uniform = _rank_uniform_facts(cards)
    layered: list[dict] = []
    truncations: list[dict] = []
    for e in cards:
        card, drops = _rank_v2_candidate_card(e, ancestry_cns, non_uniform)
        layered.append(card)
        truncations.extend({"evidence_id": card["evidence_id"], **d}
                           for d in drops)
    task["schema_version"] = PREDICTION_TASK_SCHEMA_VERSION_V2
    task["candidates"] = layered
    task["candidate_set"] = _rank_v2_candidate_set(
        cards, policy, truncations, uniform)
    return task


def build_prediction_task(
    *,
    store,
    run_id: str,
    path_id: str,
    substrate_identity: str,
    substrate_smiles: str,
    root_smiles: str,
    mode: str,
    retrieval_payload: dict,
    retrieval_payload_hash: str,
    conditions: dict | None,
    model_block: dict,
    policy: dict,
    budget: dict,
    atomtool_info: dict | None = None,
    molecule_render: dict | None = None,
    siblings: list[dict] | None = None,
    analogy_eligibility: dict | None = None,
) -> dict:
    """组装 PredictionTask(版本化 JSON;只读素材,落盘后不可变)。

    molecule_render:analogy_edit 模式必填(当前分子的 MoleCode 编辑视图,
    由 AtomTool 往返核对后传入;缺失/有损在调用方先处理)。
    siblings:已有兄弟路径(sibling_task_block 组装;缺省空)。
    analogy_eligibility:Phase C 资格裁决产物(classify 落盘的不可变块);
    analogy_edit 模式必填且 status=applicable —— 供体由门禁选定,
    ``mapping_status=resolved`` 不再单独构成进入类比的资格。
    """
    if mode not in (PREDICTION_MODE_RANK, PREDICTION_MODE_ANALOGY,
                    PREDICTION_MODE_NOVEL):
        raise PredictionTaskError("unknown_mode", mode)
    # 消费端版本校验(fable5 §5.1/§7-2):任务组装基于检索产物组装候选,
    # 未知 schema 版本 fail-closed,不按旧结构静默解析(缺失字段 legacy 容忍)
    validate_retrieval_payload(retrieval_payload, origin="prediction_task")

    evidences = sorted(
        retrieval_payload.get("evidences", []),
        key=lambda e: (e.get("retrieval_rank", 0), e.get("evidence_id", "")),
    )
    if mode == PREDICTION_MODE_RANK:
        # Phase B R1/R2 修复:rank 的可选 ID 限于**合格 recorded 卡**
        # (任务书 §1:rank 在既有已记录候选间裁决;规则/类比卡属预测,
        # 须各走 analogy_edit/novel 的适用性与编辑流程,不得经 rank 选择
        # 后直接提交为 ReactionEvent)。判据 = policy 完整资格单一事实源
        # (身份/精确挂牌/条件全核);脏卡与规则/类比卡仍保留在检索产物
        # 与裁决审查范围,只是不进任务。
        usable = [
            e for e in evidences
            if e.get("kind") == EVIDENCE_KIND_RECORDED
            and not recorded_eligibility_reasons(e, substrate_identity)
        ]
        # 入围上限从 policy 读(默认 8;S1 E3 窗口臂经
        # prediction_policy_overrides.max_candidates_for_ranking=16 表达,
        # 取值随 policy 块进 run/batch identity)。只截断数量,不改入围
        # 规则:仍只合格 recorded 卡,脏卡/规则/类比卡照旧不进任务。
        candidates = usable[: int(policy.get("max_candidates_for_ranking", 8))]
    elif mode == PREDICTION_MODE_ANALOGY:
        if not analogy_eligibility \
                or analogy_eligibility.get("status") != "applicable" \
                or not (analogy_eligibility.get("selected") or {}):
            raise PredictionTaskError(
                "donor_not_applicable",
                "analogy_edit 需要通过适用性门禁的选定供体(资格块缺失或"
                "未通过;mapping_status=resolved 单独出现不再构成资格)")
        sel_eid = analogy_eligibility["selected"]["evidence_id"]
        candidates = [e for e in evidences if e["evidence_id"] == sel_eid]
        if not candidates:
            # R1 修复(v43-applicability-3):相似通道等资格块自有供体的
            # 载体卡不在检索 evidences 中;selected 自带完整 donor_ref
            # (含映射模板)时在任务内合成载体卡,不回写检索产物。
            # 旧形状(无 donor_ref)仍显式失败 —— 不静默换供体。
            sel_ref = (analogy_eligibility["selected"].get("donor_ref")
                       or {})
            if sel_ref.get("mapped_lhs") and sel_ref.get("mapped_rhs"):
                candidates = [{"evidence_id": sel_eid,
                               "donor_refs": [dict(sel_ref)]}]
            else:
                raise PredictionTaskError(
                    "selected_donor_card_missing",
                    f"资格块选定的证据卡不在检索产物中且 selected 不含"
                    f"完整供体引用:{sel_eid}")
    else:
        candidates = []

    donor_block = None
    if mode == PREDICTION_MODE_ANALOGY:
        from ..services.atom_tool import EDIT_PROTOCOL_VERSION

        card = candidates[0]
        if molecule_render is None:
            raise PredictionTaskError(
                "representation_required", "analogy_edit 需要当前分子 MoleCode"
            )
        sel = analogy_eligibility["selected"]
        # 选定供体的引用必须与资格块一致(donor_refs 内含该 record_id 且
        # 挂所选对齐 —— 对齐来自门禁枚举,不再取 RDKit 首个匹配)
        donor_ref = next((r for r in (card.get("donor_refs") or [])
                          if r.get("record_id") == sel.get("record_id")
                          and r.get("mapped_lhs")), None)
        if donor_ref is None:
            raise PredictionTaskError(
                "selected_donor_ref_missing",
                f"选定供体 {sel.get('record_id')!r} 不在证据卡 donor_refs")
        donor_ref = dict(donor_ref)
        donor_ref["alignment"] = sel.get("alignment")
        donor_ref["alignment_strategy"] = (sel.get("alignment") or {}).get(
            "strategy", "")
        donor_block = {
            "evidence_id": card["evidence_id"],
            "donor": donor_ref,
            "transform": sel.get("transform"),
            "applicability": {
                "schema_version": (analogy_eligibility or {}).get(
                    "schema_version", ""),
                "status": "applicable",
                "target_expectation": sel.get("target_smiles", ""),
                "unverified_conditions": sel.get(
                    "unverified_conditions", []),
                "n_supporting_donors": sel.get("n_supporting_donors", 1),
            },
            "edit_protocol_version": EDIT_PROTOCOL_VERSION,
            "alternatives_considered": (analogy_eligibility or {}).get(
                "alternatives", []),
            "current_molecode": molecule_render["molecode"],
            "current_atom_ids": molecule_render["atom_ids"],
            "edit_rules": [
                "edits_must_reference_existing_atom_ids",
                "existing_atoms_must_not_vanish",
                "element_of_existing_atom_ids_must_not_change",
                "bond_order_changes_must_use_change_bond_order_with_"
                "explicit_from_and_to",
                "form_bond_rejects_bonds_that_already_exist",
                "add_atom_requires_unique_new_atom_id_matching_element",
                "edits_execute_in_list_order_on_the_current_molecule",
                "referenced_evidence_id_must_equal_donor_evidence_id",
                "abstain_is_a_valid_answer",
            ],
        }

    task = {
        "schema_version": PREDICTION_TASK_SCHEMA_VERSION,
        "task_kind": "prediction_task",
        "run_id": run_id,
        "path_id": path_id,
        "mode": mode,
        "root": {
            # 真实原始输入(run_identity inputs);canonical 身份另行给出
            "smiles_raw": root_smiles,
            "identity": _ancestry_root_identity(store, run_id, path_id),
        },
        # current 只持 canonical 身份:店内只持久化身份,非根路径的原始
        # SMILES 不可得,不得以 canonical 冒充 raw(v2 诚实化,任务书 §2
        # "原始/规范 SMILES" 中 current 如实只给规范一栏)
        "current": {
            "smiles_canonical": retrieval_payload.get("query", {}).get(
                "canonical_smiles", substrate_smiles),
            "identity": substrate_identity,
            **({"molecode": molecule_render["molecode"],
                "atom_ids": molecule_render["atom_ids"]}
               if molecule_render else {}),
        },
        "ancestry": _ancestry_task_block(store, path_id),
        "conditions": conditions,
        "retrieval": {
            "task_id": retrieval_payload.get("task_ref", ""),
            "payload_hash": retrieval_payload_hash,
            "substrate_identity": retrieval_payload.get("query", {}).get(
                "substrate_identity"),
        },
        "candidates": [
            {
                "evidence_id": e["evidence_id"],
                "kind": e.get("kind"),
                "source_id": e.get("source_id"),
                "match_type": e.get("match_type"),
                "condition_fit": e.get("condition_fit"),
                "retrieval_rank": e.get("retrieval_rank"),
                "score": e.get("score"),
                "score_semantics": e.get("score_semantics"),
                "mapping_status": e.get("mapping_status"),
                "products": [
                    {"position": p.get("position"),
                     "product_smiles": p.get("product_smiles"),
                     "product_identity": p.get("product_identity")}
                    for p in e.get("products", [])
                ],
                "asset_sources": e.get("asset_sources", []),
                "donor_refs": e.get("donor_refs", []),
            }
            for e in candidates
        ],
        "donor": donor_block,
        "siblings": list(siblings) if siblings else [],
        "budget": {
            "depth_remaining": max(0, int(budget["max_depth"]) - int(
                budget.get("active_depth", 0))),
            "expansions_remaining": max(
                0, int(budget["max_expansions"]) - int(budget["used_expansions"])),
            "llm_remaining": max(
                0, int(budget.get("max_llm_calls", 0))
                - int(budget.get("used_llm_calls", 0))),
            "proposals_remaining": max(
                0, int(budget.get("max_proposals", 0))
                - int(budget.get("used_proposals", 0))),
            "max_reportable_products": int(
                policy.get("max_reportable_products", MAX_REPORTABLE_PRODUCTS)),
        },
        "discipline": {"model_may_not": list(DISCIPLINE_RULES)},
        "model": {
            "provider": model_block.get("provider"),
            "model_id": model_block.get("model_id"),
            "prompt_version": model_block.get("prompt_versions", {}).get(mode),
        },
        "policy_version": policy.get("policy_version", ""),
    }
    # S1 E1:rank 协议 v2 呈现(组装末端的纯呈现层改写;默认 v1 时本块
    # 不执行,任务书与历史行为逐字节一致)
    if mode == PREDICTION_MODE_RANK and str(policy.get(
            "rank_candidate_presentation", "v1")) == RANK_PRESENTATION_V2:
        task = _apply_rank_presentation_v2(task, candidates, policy)
    return task


def _ancestry_root_identity(store, run_id: str, path_id: str) -> str | None:
    from ..domain.pathway import ancestry_chain

    chain = ancestry_chain(store, path_id)
    return chain[0].substrate_identity if chain else None


def task_user_payload(task: dict) -> str:
    """发给模型的用户消息(完整任务书 JSON;确定性序列化)。"""
    return json.dumps(task, ensure_ascii=False, sort_keys=True)


def task_input_hash(task: dict) -> str:
    return request_hash(task)


# ---------------------------------------------------------------- 响应解析


@dataclass
class ParsedPrediction:
    """一次响应的确定性解析结果(显式成败,不静默)。"""

    ok: bool
    mode: str
    error_kind: str = ""            # not_json | bad_shape | invalid_evidence_id | too_many_products | order_missing | order_incomplete | order_with_hold | hold_reason_invalid | ...
    error_message: str = ""
    decision: str = ""              # select|hold|apply|abstain|propose
    selected_evidence_id: str | None = None
    order: list = field(default_factory=list)
    reasons: dict = field(default_factory=dict)
    reason: str = ""
    hold_kind: str = ""             # S1 E1 v2:hold 结构化理由枚举(HOLD_KINDS)
    hold_note: str = ""             # S1 E1 v2:放弃理由说明(确定性截断)
    target_molecode: str = ""
    edits: list = field(default_factory=list)
    referenced_evidence_id: str | None = None
    products: list = field(default_factory=list)   # [{smiles, note}]
    uncertainty: str = ""

    def to_dict(self) -> dict:
        return dict(self.__dict__)


def parse_model_response(mode: str, raw_text: str,
                         candidate_ids: list[str] | None = None, *,
                         rank_presentation: str = "v1") -> ParsedPrediction:
    """模型原文 → 结构化结果;契约违反都是显式 error(任务书 §2)。

    rank_presentation(S1 E1):默认 "v1" = 既有契约(order 可省略、hold
    只要自由文本 reason),全部既有调用方行为不变;"v2" = E1 协议臂契约
    (select 必须给任务书全部候选的完整 order;hold 必须给结构化
    hold={kind,note},kind ∈ HOLD_KINDS;违反 fail-closed 走既有有界重试)。
    """
    text = (raw_text or "").strip()
    if not text:
        return ParsedPrediction(ok=False, mode=mode, error_kind="empty_response")
    # 容忍 markdown 代码栅栏,但不容忍任何其他包装
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    try:
        obj = json.loads(text)
    except Exception:
        return ParsedPrediction(ok=False, mode=mode,
                                error_kind="not_json",
                                error_message="响应不是合法 JSON")
    if not isinstance(obj, dict):
        return ParsedPrediction(ok=False, mode=mode,
                                error_kind="bad_shape",
                                error_message="响应必须是 JSON 对象")
    decision = str(obj.get("decision", ""))
    reason = str(obj.get("reason", ""))

    if mode == PREDICTION_MODE_RANK:
        if decision not in ("select", "hold"):
            return _bad(mode, f"decision 必须为 select|hold,得到 {decision!r}")
        selected = obj.get("evidence_id")
        if decision == "select":
            if selected not in (candidate_ids or []):
                return ParsedPrediction(
                    ok=False, mode=mode, error_kind="invalid_evidence_id",
                    error_message=f"evidence_id {selected!r} 不在候选集",
                )
        order = [x for x in (obj.get("order") or []) if isinstance(x, str)]
        unknown = [x for x in order if candidate_ids and x not in candidate_ids]
        if unknown:
            return ParsedPrediction(
                ok=False, mode=mode, error_kind="invalid_evidence_id",
                error_message=f"order 含非法证据 ID:{unknown}",
            )
        # Phase B 排序契约(任务书 §3.2):order 全部来自本次任务候选、
        # 无重复;selected_evidence_id 恰出现一次并排第一。违反 = 解析失败,
        # 走既有有界重试。旧形制未给 order 仍接受(报告侧记录
        # order_missing_selected_only)。
        if len(set(order)) != len(order):
            dupes = sorted({x for x in order if order.count(x) > 1})
            return ParsedPrediction(
                ok=False, mode=mode, error_kind="duplicate_order_id",
                error_message=f"order 含重复证据 ID:{dupes}",
            )
        # ---- S1 E1 v2 契约(仅 rank_presentation=v2;v1 行为不变)----
        hold_kind, hold_note = "", ""
        if rank_presentation == RANK_PRESENTATION_V2:
            if decision == "select":
                # 完整 order 契约:select 必须给任务书**全部**候选各一次的
                # 排列(答卷 2–5 位由 order 尾部决定;漏卡 = 隐式弃权,
                # 不允许 —— 要弃就显式 hold)。fail-closed 走既有有界重试。
                if not order:
                    return ParsedPrediction(
                        ok=False, mode=mode, error_kind="order_missing",
                        error_message="decision=select 必须给出 order"
                                      "(任务书全部候选的完整排列)",
                    )
                missing = [c for c in (candidate_ids or [])
                           if c not in order]
                if missing:
                    return ParsedPrediction(
                        ok=False, mode=mode, error_kind="order_incomplete",
                        error_message=f"order 缺少任务书候选:{missing}"
                                      "(须全部候选各出现一次)",
                    )
            else:
                # hold:结构化放弃理由(枚举 + note);不得携带 order
                if order:
                    return ParsedPrediction(
                        ok=False, mode=mode, error_kind="order_with_hold",
                        error_message="decision=hold 不得携带 order",
                    )
                hold = obj.get("hold")
                if not isinstance(hold, dict):
                    return ParsedPrediction(
                        ok=False, mode=mode, error_kind="hold_reason_invalid",
                        error_message="decision=hold 需要 "
                                      "hold={kind,note}(kind 为任务书"
                                      "枚举值)",
                    )
                hold_kind = str(hold.get("kind", ""))
                hold_note = str(hold.get("note", ""))
                if hold_kind not in HOLD_KINDS:
                    return ParsedPrediction(
                        ok=False, mode=mode, error_kind="hold_reason_invalid",
                        error_message=f"hold.kind {hold_kind!r} 不在枚举 "
                                      f"{list(HOLD_KINDS)}",
                    )
                if hold_kind == "other" and not hold_note.strip():
                    return ParsedPrediction(
                        ok=False, mode=mode, error_kind="hold_reason_invalid",
                        error_message="hold.kind=other 时 note 必填",
                    )
                hold_note = hold_note[:HOLD_NOTE_CHAR_CAP]
        if decision == "select" and order:
            if selected not in order:
                return ParsedPrediction(
                    ok=False, mode=mode, error_kind="selected_missing_from_order",
                    error_message=f"选中 {selected!r} 未出现在 order 中",
                )
            if order[0] != selected:
                return ParsedPrediction(
                    ok=False, mode=mode, error_kind="selected_not_first",
                    error_message=f"选中 {selected!r} 必须排在 order 首位",
                )
        reasons = obj.get("reasons") or {}
        if not isinstance(reasons, dict):
            reasons = {}
        if rank_presentation == RANK_PRESENTATION_V2:
            # v2:逐候选理由结构化 {verdict, note}(verdict ∈
            # chosen|competitive|rejected;旧字符串形规约为 note,不失败);
            # 文本确定性截断,不因长度 fail
            norm: dict = {}
            for k, v in reasons.items():
                if isinstance(v, dict):
                    norm[str(k)] = {
                        "verdict": str(v.get("verdict", "")),
                        "note": str(v.get("note", ""))[:REASON_TEXT_CHAR_CAP],
                    }
                else:
                    norm[str(k)] = {
                        "verdict": "",
                        "note": str(v)[:REASON_TEXT_CHAR_CAP],
                    }
            reasons = norm
        else:
            reasons = {str(k): str(v) for k, v in reasons.items()}
        return ParsedPrediction(
            ok=True, mode=mode, decision=decision,
            selected_evidence_id=selected if decision == "select" else None,
            order=order, reasons=reasons,
            reason=reason,
            hold_kind=hold_kind if decision == "hold" else "",
            hold_note=hold_note if decision == "hold" else "",
        )

    if mode == PREDICTION_MODE_ANALOGY:
        if decision == "abstain":
            return ParsedPrediction(ok=True, mode=mode, decision="abstain",
                                    reason=reason)
        if decision != "apply":
            return _bad(mode, f"decision 必须为 apply|abstain,得到 {decision!r}")
        target = obj.get("target_molecode")
        if not target or not isinstance(target, str):
            return _bad(mode, "apply 需要 target_molecode 字符串")
        edits = obj.get("edits") or []
        if not isinstance(edits, list):
            edits = []
        return ParsedPrediction(
            ok=True, mode=mode, decision="apply", target_molecode=target,
            edits=edits,
            referenced_evidence_id=obj.get("referenced_evidence_id"),
            reason=reason,
        )

    if mode == PREDICTION_MODE_NOVEL:
        if decision == "abstain":
            return ParsedPrediction(ok=True, mode=mode, decision="abstain",
                                    reason=reason)
        if decision != "propose":
            return _bad(mode, f"decision 必须为 propose|abstain,得到 {decision!r}")
        products = obj.get("products") or []
        if not isinstance(products, list):
            return _bad(mode, "products 必须是列表")
        if len(products) > MAX_REPORTABLE_PRODUCTS:
            return ParsedPrediction(
                ok=False, mode=mode, error_kind="too_many_products",
                error_message=f"提案 {len(products)} 个 > 上限 "
                f"{MAX_REPORTABLE_PRODUCTS}",
            )
        cleaned = []
        for p in products:
            if not isinstance(p, dict) or not str(p.get("smiles", "")).strip():
                return _bad(mode, "每个提案需要 {smiles, note}")
            cleaned.append({"smiles": str(p["smiles"]).strip(),
                            "note": str(p.get("note", ""))})
        return ParsedPrediction(
            ok=True, mode=mode, decision="propose", products=cleaned,
            uncertainty=str(obj.get("uncertainty", "high")), reason=reason,
        )
    return _bad(mode, f"未知预测模式 {mode!r}")


def _bad(mode: str, msg: str) -> ParsedPrediction:
    return ParsedPrediction(ok=False, mode=mode, error_kind="bad_shape",
                            error_message=msg)


# ---------------------------------------------------------------- 提案卡


def build_proposed_card(
    *, run_id: str, path_id: str, substrate_identity: str, mode: str,
    parsed: ParsedPrediction, task: dict, task_id: str,
    products: list[dict], donor_ref: dict | None = None,
    atomtool_checks: dict | None = None,
) -> dict:
    """把模型提案构造为证据卡形状的事件源(全部挂牌为预测)。

    - kind:analogy_edit → analog_reaction;novel_proposal → novel_proposal;
    - score_semantics 显式声明"模型提案、无校准分数";
    - source_record 携带任务书/响应引用、模型与策略版本、供体映射与
      AtomTool 核验结果 —— 逐项可审计;
    - 证据 ID 由(任务, 解析产物)内容派生:重放同内容幂等,内容变化不伪装同键。
    """
    kind = (EVIDENCE_KIND_ANALOG if mode == PREDICTION_MODE_ANALOGY
            else EVIDENCE_KIND_NOVEL)
    product_identities = [p["product_identity"] for p in products]
    card = {
        "evidence_id": stable_id(
            "E", run_id, path_id, "proposed", mode, task["task_ref"],
            "\x00".join(product_identities),
        ),
        "source_id": (
            f"{(donor_ref or {}).get('record_id', 'model')}|via:{mode}"
        ),
        "kind": kind,
        "query_identity": substrate_identity,
        "match_type": (
            "model_analogy_transfer" if mode == PREDICTION_MODE_ANALOGY
            else "model_constrained_proposal"
        ),
        "reactant_smiles": substrate_identity,
        "reactant_identity": substrate_identity,
        "products": products,
        "atom_mapping": (
            "model_edit_view" if mode == PREDICTION_MODE_ANALOGY
            else "unavailable"
        ),
        "donor_refs": [donor_ref] if donor_ref else [],
        "mapping_status": (
            "resolved" if mode == PREDICTION_MODE_ANALOGY else "unavailable"
        ),
        "mapping_reason": (
            "aligned_donor_from_task" if mode == PREDICTION_MODE_ANALOGY
            else "no_donor_model_proposal"
        ),
        "condition_fit": "unknown",
        "retrieval_rank": 0,
        "score": 0.0,
        "score_semantics": (
            "model_proposal_qualitative_only_no_calibrated_probability"
        ),
        "source_record": {
            "prediction_task_id": task_id,
            "task_input_hash": task.get("input_hash", ""),
            "task_ref": task.get("task_ref", ""),
            "model_provider": (task.get("model") or {}).get("provider"),
            "model_id": (task.get("model") or {}).get("model_id"),
            "prompt_version": (task.get("model") or {}).get("prompt_version"),
            "policy_version": task.get("policy_version"),
            "model_reason": parsed.reason,
            "model_uncertainty": parsed.uncertainty,
            "atomtool_checks": atomtool_checks or {},
            "donor": donor_ref,
            "predicted_by_model": True,
        },
        "asset_file": "",
        "asset_sha256": "",
        "asset_sources": [],
        "run_id": run_id,
        "path_id": path_id,
        "created_at": "",  # 由 finder 卡的字段惯例;提案卡不带检索时间戳
    }
    card["_content_hash"] = content_hash(
        {k: v for k, v in card.items()
         if k not in ("created_at", "_content_hash")}
    )
    return card
