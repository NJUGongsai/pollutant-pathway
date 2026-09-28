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

PREDICTION_TASK_SCHEMA_VERSION = "v43-prediction-task-3"  # v3:donor 块带 applicability/transform/编辑协议 v2(Phase C)
PREDICTION_RESPONSE_SCHEMA_VERSION = "v43-prediction-response-1"
PREDICTION_RESULT_SCHEMA_VERSION = "v43-prediction-result-1"

MAX_REPORTABLE_PRODUCTS = 5  # 每步最多报告五个候选(任务书 §0)

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
    error_kind: str = ""            # not_json | bad_shape | invalid_evidence_id | too_many_products | abstain...
    error_message: str = ""
    decision: str = ""              # select|hold|apply|abstain|propose
    selected_evidence_id: str | None = None
    order: list = field(default_factory=list)
    reasons: dict = field(default_factory=dict)
    reason: str = ""
    target_molecode: str = ""
    edits: list = field(default_factory=list)
    referenced_evidence_id: str | None = None
    products: list = field(default_factory=list)   # [{smiles, note}]
    uncertainty: str = ""

    def to_dict(self) -> dict:
        return dict(self.__dict__)


def parse_model_response(mode: str, raw_text: str,
                         candidate_ids: list[str] | None = None) -> ParsedPrediction:
    """模型原文 → 结构化结果;契约违反都是显式 error(任务书 §2)。"""
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
        return ParsedPrediction(
            ok=True, mode=mode, decision=decision,
            selected_evidence_id=selected if decision == "select" else None,
            order=order, reasons={str(k): str(v) for k, v in reasons.items()},
            reason=reason,
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
