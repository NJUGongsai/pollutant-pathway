"""候选报告裁决(EC298 Phase B)— 一父节点一份完整候选裁决。

任务书 TASK_V43_EC298_PHASE_B §2/§3:报告与路径展开解耦。每个父
PathInstance 的**每张进入审查范围的证据卡**都有卡级记录,卡内每个产物有
产品级记录;合格产物可进入最多五位的报告列表;只有策略选定的反应进入
ReactionEvent,只有调度选中的产物成为继续探索的 frontier。报告声明、
化学事实和调度决定分别可追溯。

分层(全部确定性、可重放):

1. **逐卡验证** ``validate_card_for_reporting``:对**未选中**卡按其证据
   类型过确定性门禁。recorded 至少核对同规范底物、精确来源、反应方向、
   条件无冲突、可解析/价态、路径内循环和产物身份(复用 validation.gates
   的语义,但不用针对已提交兄弟路径的 sibling_dedup —— 跨卡去重在裁决层
   单独定义);原始规则/类比卡只有结构可解析不等于反应适用,缺映射适用性
   记 ``not_validated_for_reporting``(留给 Phase C),其产品不进报告。
2. **裁决** ``adjudicate_parent``:唯一纯函数,输入本父检索/任务/预测/
   验证产物与事件提交事实,输出完整候选裁决(v2 payload;stage=draft 无
   事件引用,stage=final 含真实事件引用或显式 no_event 终态)。排序规则
   唯一且版本化:选中卡合格产品占优先位次,模型 ``order`` 只为剩余候选
   提供相对顺序;唯一 recorded 直通无模型顺序,额外合格卡按冻结后备键
   ``(retrieval_rank, evidence_id, position)`` 排列并标
   ``rank_basis=deterministic_fallback``。
3. **不变量** ``validate_adjudication_payload``:写入前与导出/报告读取时
   都执行 —— ``expand_selected ⇒ committed_event_ref != null ⇒
   reportable ⇒ accepted``;``report_rank`` 仅给最终可报告去重项,按父
   节点连续从 1 编号、最多五位;相同 cn 的多卡候选只占一个位次,保留全部
   来源/验证引用;审查与报告以父 path_id 为作用域。

模型 ``order`` 从未进入选择集的预测性卡不推断模型认可;hold/abstain/
failed 不批准任何其他候选(本阶段冻结策略:无单独可核验证据不升级)。
"""

from __future__ import annotations

import hashlib

from ..domain.identity import cn_identity
from ..domain.models import (
    CONDITION_CONFLICT,
    EVIDENCE_KIND_ANALOG,
    EVIDENCE_KIND_NOVEL,
    EVIDENCE_KIND_RECORDED,
    EVIDENCE_KIND_RULE,
    PREDICTION_MODE_RANK,
    content_hash,
)
from ..validation.gates import gate_smiles
from ..domain.pathway import is_in_path_cycle

REPORT_ADJUDICATION_SCHEMA_V2 = "v43-report-adjudication-2"
REPORT_ADJUDICATION_SCHEMA_V1 = "v43-report-adjudication-1"
REPORT_ADJUDICATION_POLICY_VERSION = "v43-repadj-1"

STAGE_DRAFT = "draft"
STAGE_FINAL = "final"

# 卡从哪一层进入审查范围
ENTRY_LAYER_RETRIEVAL = "retrieval"
ENTRY_LAYER_MODEL_PROPOSAL = "model_proposal"

# rank 依据(载荷级 rank_basis)
RANK_BASIS_MODEL_ORDER = "model_order"
RANK_BASIS_ORDER_MISSING = "order_missing_selected_only"
RANK_BASIS_DETERMINISTIC = "deterministic_fallback"

REPORT_ADJUDICATION_POLICY_DEFAULTS: dict = {
    "policy_version": REPORT_ADJUDICATION_POLICY_VERSION,
    # 每步最多报告五个候选(任务书 §0/§2)
    "max_reportable_products": 5,
    # rank 模式 order 契约:全部来自本次任务候选、无重复、selected 恰出现
    # 一次并排第一(解析失败走既有有界重试)
    "rank_mode_order_contract":
        "task_candidate_ids_no_duplicates_selected_first",
    # 旧形制未给 order:只报告被选卡的合格产品
    "order_missing_policy": "selected_only",
    # order 不完整:仅按列出的卡排列,不自动把遗漏卡补进报告
    "order_incomplete_policy": "listed_only_not_auto_filled",
    # 未进模型选择集的卡不因检索/分数升格(不推断模型认可)
    "non_selected_promotion": "model_selection_set_plus_kind_gates_only",
    # 原始规则/类比卡:结构可解析不等于反应适用;缺映射适用性不进报告
    "raw_rule_analog_policy": "not_validated_for_reporting",
    # 相同 cn 多卡候选:占一个位次,保留全部来源/验证引用,主来源 =
    # 排序键首个(选中卡优先,其后模型 order / 后备键)
    "cross_card_dedup": "keep_first_in_rank_order_record_all_sources",
    # 唯一 recorded 直通无模型顺序时,额外合格卡的后备排序键
    "unique_recorded_fallback_order": "retrieval_rank_evidence_id_position",
    # 父节点无 ReactionEvent 但存在最终可报告候选:允许只报告不提交,
    # 导出生成父步骤、不产生子步骤(策略显式允许并有测试,不靠导出器删掉)
    "no_event_reportable": "allow_report_only_step",
}


class AdjudicationError(RuntimeError):
    """候选裁决构造或不变量校验失败(结构化;fail-closed)。"""

    def __init__(self, message: str, detail: dict | None = None):
        super().__init__(message)
        self.detail = detail or {}


def cardval_artifact_name(evidence_id: str) -> str:
    """逐卡验证产物的 artifact 名(evidence_id 可能含非文件字符,取哈希)。"""
    return "cardval." + hashlib.sha256(
        evidence_id.encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------- 逐卡验证


def _recorded_card_reasons(card: dict, substrate_identity: str) -> list[str]:
    """recorded 卡的证据资格门禁(单一事实源:policy 完整判据,留拒因)。

    Phase B R1 修复:与任务候选筛选/路由/选中卡复验共用
    ``policy.recorded_eligibility_reasons`` —— 任一处都不得放宽。
    """
    from ..domain.policy import recorded_eligibility_reasons

    return recorded_eligibility_reasons(card, substrate_identity)


def validate_card_for_reporting(
    *,
    card: dict,
    substrate_identity: str,
    ancestry_cns: list[str],
    entry_layer: str,
    policy: dict | None = None,
) -> dict:
    """未选中卡的逐卡确定性验证(任务书 §2:每张进入审查范围的卡都有
    卡级记录;每个产物有产品级记录,未通过者保留明确拒因)。

    - recorded:证据资格门禁 + 逐产物(可解析/价态、原始字符串重算身份、
      路径内循环);多产物卡逐项裁决,一项失败不丢其余有效项;
    - rule/analog 原始卡(非模型提案):记 ``not_validated_for_reporting``
      (Phase C 处理弱映射/供体选择),产品仍记录原始形与重算身份,
      但不进报告;类比供体原始产品不是本底物的报告产品;
    - 不使用 sibling_dedup:跨卡去重在裁决层单独定义(任务书 §2)。
    """
    kind = card.get("kind")
    card_reasons: list[str] = []
    not_validated = False
    if kind == EVIDENCE_KIND_RECORDED:
        card_reasons = _recorded_card_reasons(card, substrate_identity)
    elif kind in (EVIDENCE_KIND_RULE, EVIDENCE_KIND_ANALOG, EVIDENCE_KIND_NOVEL):
        # 原始规则/类比卡:映射适用性未对本底物建立,不冒充可报告
        not_validated = True
        card_reasons.append(
            "not_validated_for_reporting:规则/类比原始卡缺本底物映射适用性"
            "证据(Phase C);结构可解析不等于反应适用")
    else:
        not_validated = True
        card_reasons.append(f"unknown_evidence_kind:{kind!r}")

    verdicts: dict[int, dict] = {}
    for prod in card.get("products", []):
        pos = int(prod.get("position", 0))
        raw_full = (prod.get("product_smiles_full") or "").strip()
        raw_smiles = (prod.get("product_smiles") or "").strip()
        raw = raw_full or raw_smiles
        computed = cn_identity(raw) if raw else None
        stored = prod.get("product_identity")
        reasons: list[str] = []
        ok, reason = gate_smiles(raw)
        if not ok:
            reasons.append(reason)
        if computed is None:
            reasons.append("identity_uncomputable:原始字符串无法重算规范身份")
        elif stored is not None and stored != computed:
            reasons.append(
                f"identity_mismatch:缓存身份与原始字符串重算不符"
                f"(stored={str(stored)[:60]},computed={computed[:60]})")
        if computed is not None and is_in_path_cycle(computed, ancestry_cns):
            reasons.append("in_path_cycle:产物回到本路径祖先分子")
        verdicts[pos] = {
            "position": pos,
            "product_smiles": raw,
            "product_identity": computed or (stored or ""),
            "stored_product_identity": stored,
            "identity_match": bool(computed is not None and stored == computed),
            "accepted": not reasons,
            "reasons": reasons,
        }
    card_eligible = not card_reasons
    return {
        "schema_version": "v43-card-validation-1",
        "task_kind": "card_validation",
        "evidence_id": card.get("evidence_id", ""),
        "kind": kind,
        "entry_layer": entry_layer,
        "source_id": card.get("source_id", ""),
        "retrieval_rank": card.get("retrieval_rank"),
        "condition_fit": card.get("condition_fit"),
        "match_type": card.get("match_type"),
        "mapping_status": card.get("mapping_status"),
        "source_file": card.get("asset_file", ""),
        "asset_sha256": card.get("asset_sha256", ""),
        "card_eligible": card_eligible,
        "not_validated_for_reporting": not_validated,
        "card_reasons": card_reasons,
        "gates": {"recorded_eligibility": {
            "ok": card_eligible if kind == EVIDENCE_KIND_RECORDED else None,
            "reasons": card_reasons,
        }},
        "policy_version": (policy or REPORT_ADJUDICATION_POLICY_DEFAULTS)[
            "policy_version"],
        "verdicts": [verdicts[k] for k in sorted(verdicts)],
        "n_accepted": sum(1 for v in verdicts.values() if v["accepted"]),
        "n_total": len(verdicts),
    }


def _selected_card_validation_view(selected_card: dict,
                                   selected_validation: dict | None,
                                   substrate_identity: str,
                                   entry_layer: str = ENTRY_LAYER_RETRIEVAL) -> dict:
    """把 validate_products 产物(选中卡)包装成统一卡级验证视图。

    选中卡的方向/来源/映射门禁与逐产物裁决已在该产物中执行;此处统一
    字段形状、补原始字符串重算身份的核对(不信任缓存 product_identity),
    并**复验完整 recorded 资格判据**(Phase B R1:即使任务构造或上游门禁
    放入脏卡,选中后也不得凭模型 evidence_id 升格 —— card_eligible 由
    同一判据重新计算,不硬编码 True)。

    Phase B R2:检索层 rule/analog 原始卡即使被选中也不得升格为可提交/
    可报告(任务书 §1:规则/类比须各走 analogy_edit/novel 的适用性与
    编辑流程;rank 可选 ID 已限合格 recorded —— 此处是第二道守卫);
    模型提案卡(entry_layer=model_proposal)已过 AtomTool/元素门禁,
    资格不变。
    """
    verdict_list = ((selected_validation or {}).get("verdicts")
                    if selected_validation else []) or []
    verdicts: dict[int, dict] = {}
    for v in verdict_list:
        pos = int(v["position"])
        reasons = list(v.get("reasons", []))
        raw = (v.get("product_smiles") or "").strip()
        computed = cn_identity(raw) if raw else None
        stored = v.get("product_identity")
        # 不信任缓存身份:原始字符串重算不符 = 显式拒绝(任务书 §2)
        if computed is None:
            reasons.append("identity_uncomputable:原始字符串无法重算规范身份")
        elif stored is not None and stored != computed:
            reasons.append(
                f"identity_mismatch:缓存身份与原始字符串重算不符"
                f"(stored={str(stored)[:60]},computed={computed[:60]})")
        accepted = bool(v.get("accepted")) and computed is not None and (
            stored is None or stored == computed)
        verdicts[pos] = {
            "position": pos,
            "product_smiles": raw,
            "product_identity": computed or (stored or ""),
            "stored_product_identity": stored,
            "identity_match": bool(computed is not None and stored == computed),
            "accepted": accepted,
            "reasons": reasons,
        }
    from ..domain.policy import recorded_eligibility_reasons

    sel_kind = selected_card.get("kind")
    sel_reasons = recorded_eligibility_reasons(selected_card,
                                               substrate_identity)
    # 检索层规则/类比原始卡:结构可解析 ≠ 反应适用,与未选中卡同判
    raw_predictive = (
        entry_layer == ENTRY_LAYER_RETRIEVAL
        and sel_kind in (EVIDENCE_KIND_RULE, EVIDENCE_KIND_ANALOG,
                         EVIDENCE_KIND_NOVEL))
    if raw_predictive:
        sel_eligible = False
        sel_reasons = [
            "not_validated_for_reporting:规则/类比原始卡缺本底物映射适用性"
            "证据,不得经 rank 选择直接提交;须各走 analogy_edit/novel 流程"]
    else:
        sel_eligible = not sel_reasons
    if (sel_kind == EVIDENCE_KIND_RECORDED and not sel_eligible) \
            or raw_predictive:
        # 资格复验失败:选中卡全部产物显式拒绝(双保险;上游门禁应已拒绝
        # —— 两处同判,单独构造的载荷同样不可升格)
        for v in verdicts.values():
            if v["accepted"]:
                v["accepted"] = False
                v["reasons"] = sel_reasons + [
                    "selected_card_ineligible:选中卡资格复验失败,不得升格"]
    return {
        "schema_version": "v43-card-validation-1",
        "task_kind": "card_validation",
        "evidence_id": selected_card.get("evidence_id", ""),
        "kind": sel_kind,
        "entry_layer": entry_layer,
        "source_id": selected_card.get("source_id", ""),
        "retrieval_rank": selected_card.get("retrieval_rank"),
        "condition_fit": selected_card.get("condition_fit"),
        "match_type": selected_card.get("match_type"),
        "mapping_status": selected_card.get("mapping_status"),
        "source_file": selected_card.get("asset_file", ""),
        "asset_sha256": selected_card.get("asset_sha256", ""),
        "card_eligible": sel_eligible,
        # R3 P3:检索层规则/类比卡被选中拒升格时,布尔字段与拒因一致
        "not_validated_for_reporting": raw_predictive,
        "card_reasons": sel_reasons,
        "gates": {
            "direction_source": (selected_validation or {}).get("gates", {}).get(
                "direction_source"),
            "atom_mapping": (selected_validation or {}).get("gates", {}).get(
                "atom_mapping"),
            "recorded_eligibility": {
                "ok": sel_eligible if sel_kind == EVIDENCE_KIND_RECORDED
                else None,
                "reasons": sel_reasons},
            "raw_predictive_selected": {
                "ok": not raw_predictive,
                "reasons": sel_reasons if raw_predictive else []},
        },
        "policy_version": REPORT_ADJUDICATION_POLICY_VERSION,
        "verdicts": [verdicts[k] for k in sorted(verdicts)],
        "n_accepted": sum(1 for v in verdicts.values() if v["accepted"]),
        "n_total": len(verdicts),
    }


# ---------------------------------------------------------------- 裁决


def _selection_context(prediction_result: dict | None,
                       decision_payload: dict | None) -> dict:
    """从预测结果/决策产物提取选择上下文(选中卡、模型 order、依据)。"""
    outcome = (prediction_result or {}).get("outcome")
    mode = (prediction_result or {}).get("mode", "")
    model_ref = ""
    if prediction_result and prediction_result.get("task_id"):
        model_ref = (f"prediction:{prediction_result['task_id']}"
                     f"#a{prediction_result.get('attempt', 0)}")
    if outcome == "selected" and mode == PREDICTION_MODE_RANK:
        order = [str(x) for x in (prediction_result.get("order") or [])]
        return {
            "selected_evidence_id": prediction_result.get("selected_evidence_id"),
            "model_order": order,
            "order_missing": not order,
            "rank_basis": (RANK_BASIS_MODEL_ORDER if order
                           else RANK_BASIS_ORDER_MISSING),
            "mode": mode,
            "model_decision_ref": model_ref,
        }
    # 确定性直通(唯一 usable recorded / 模型提案卡;无模型 order)
    return {
        "selected_evidence_id": (decision_payload or {}).get(
            "accepted_evidence_id"),
        "model_order": [],
        "order_missing": False,
        "rank_basis": RANK_BASIS_DETERMINISTIC,
        "mode": mode or "deterministic",
        "model_decision_ref": model_ref,
    }


def _fallback_card_key(card: dict) -> tuple:
    """冻结后备键:(retrieval_rank, evidence_id, 卡内最小 position)。"""
    positions = [int(p.get("position", 0))
                 for p in card.get("products", [])] or [0]
    return (card.get("retrieval_rank") if card.get("retrieval_rank")
            is not None else 1 << 30,
            card.get("evidence_id", ""), min(positions))


def adjudicate_parent(
    *,
    run_id: str,
    path_id: str,
    substrate_identity: str,
    retrieval_payload: dict,
    decision_payload: dict | None,
    prediction_task: dict | None,
    prediction_result: dict | None,
    selected_evidence_id: str,
    selected_card: dict,
    selected_validation: dict | None,
    card_validations: dict[str, dict],
    validation_refs: dict[str, dict],
    stage: str,
    event_commit: dict | None = None,
    no_event_reason: str = "",
    policy: dict | None = None,
) -> dict:
    """唯一纯函数裁决(任务书 §3):输入全部为不可变产物与事件提交事实,
    输出本父完整候选裁决 v2 payload;重放同输入得同 payload(幂等)。

    validation_refs:evidence_id → ``{"task_id", "artifact",
    "payload_sha256"}``(Phase B R1:选中卡指 validation.json,未选中卡指
    cardval.<...>.json;可报告条目必须能按引用回查验证产物,缺失/错指/
    哈希不符由读取端 fail-closed)。

    event_commit:None = 草稿或 no_event 终态;否则
    ``{"event_id", "expand_positions", "deferred_positions"}``(位次为选中
    卡的原始产物位次)。
    """
    if stage not in (STAGE_DRAFT, STAGE_FINAL):
        raise AdjudicationError(f"未知裁决阶段:{stage!r}", {"stage": stage})
    pol = dict(REPORT_ADJUDICATION_POLICY_DEFAULTS)
    if policy:
        pol.update({k: v for k, v in policy.items() if k in pol})
    max_reportable = int(pol["max_reportable_products"])
    sel = _selection_context(prediction_result, decision_payload)
    if sel["selected_evidence_id"] not in (None, selected_evidence_id):
        raise AdjudicationError(
            "选择上下文与选中卡不一致",
            {"context": sel["selected_evidence_id"],
             "card": selected_evidence_id})

    # ---- 卡范围:本父检索产物 + 模型提案卡(任务书 §2 审查范围下限)
    scope: list[tuple[dict, str]] = [
        (e, ENTRY_LAYER_RETRIEVAL)
        for e in retrieval_payload.get("evidences", [])
    ]
    proposed = (prediction_result or {}).get("proposed_card")
    if proposed:
        scope.append((proposed, ENTRY_LAYER_MODEL_PROPOSAL))
    if not any(c.get("evidence_id") == selected_evidence_id
               for c, _ in scope):
        raise AdjudicationError(
            "选中卡不在本父审查范围(检索产物/提案卡)",
            {"selected": selected_evidence_id, "path_id": path_id})

    task_candidates = (prediction_task or {}).get("candidates") or []
    task_pos = {c.get("evidence_id"): i for i, c in enumerate(task_candidates)}
    order = sel["model_order"]
    order_pos = {eid: i for i, eid in enumerate(order)}

    # ---- 卡级记录(P2 R1:四层分开命名 —— 任务候选层 in_task、模型排序层
    # in_model_order、选中位 selected、化学门禁层 card_eligible;模型可以
    # 省略某任务候选的排序,"在任务中"不得冒充"模型未给机会",反之亦然)
    cards: list[dict] = []
    val_by_eid: dict[str, dict] = {}
    for card, layer in scope:
        eid = card["evidence_id"]
        if eid == selected_evidence_id:
            val = _selected_card_validation_view(card, selected_validation,
                                                 substrate_identity,
                                                 entry_layer=layer)
        else:
            val = card_validations.get(eid)
            if val is None:
                raise AdjudicationError(
                    "审查范围内卡缺少逐卡验证产物",
                    {"evidence_id": eid, "path_id": path_id})
        ref = validation_refs.get(eid)
        if not ref or not ref.get("task_id") or not ref.get("artifact")                 or not ref.get("payload_sha256"):
            raise AdjudicationError(
                "卡缺少验证产物引用(task_id/artifact/payload_sha256)",
                {"evidence_id": eid, "path_id": path_id})
        val_by_eid[eid] = val
        cards.append({
            "evidence_id": eid,
            "kind": card.get("kind"),
            "source_id": card.get("source_id", ""),
            "entry_layer": layer,
            "in_task": eid in task_pos,
            "task_candidate_position": task_pos.get(eid),
            "selected": eid == selected_evidence_id,
            "in_model_order": eid in order_pos,
            "model_order_position": order_pos.get(eid),
            "retrieval_rank": card.get("retrieval_rank"),
            "source_file": card.get("asset_file", ""),
            "asset_sha256": card.get("asset_sha256", ""),
            "condition_fit": card.get("condition_fit"),
            "match_type": card.get("match_type"),
            "mapping_status": card.get("mapping_status"),
            "card_eligible": bool(val.get("card_eligible")),
            "not_validated_for_reporting": bool(
                val.get("not_validated_for_reporting")),
            "card_reasons": list(val.get("card_reasons", [])),
            "validation_ref": dict(ref),
            "n_products": int(val.get("n_total", 0)),
            "n_accepted": int(val.get("n_accepted", 0)),
        })

    # ---- 排序:选中卡合格产品优先 → 模型 order 剩余候选 → 冻结后备键
    def endorsed(eid: str, val: dict) -> bool:
        if eid == selected_evidence_id:
            return True
        if sel["rank_basis"] == RANK_BASIS_MODEL_ORDER:
            # order 不完整时仅按列出的卡排列,不自动补进报告
            return eid in order_pos
        if sel["rank_basis"] == RANK_BASIS_DETERMINISTIC:
            # 唯一 recorded 直通:其他逐卡证明可报告的候选按后备键排列
            return bool(val.get("card_eligible")) and not val.get(
                "not_validated_for_reporting")
        return False  # order_missing:只报告被选卡的合格产品

    ordered_cards: list[tuple[dict, dict]] = []
    seen_eids: set[str] = set()
    for eid in [selected_evidence_id] + [
            e for e in order if e != selected_evidence_id]:
        for card, _layer in scope:
            if card["evidence_id"] == eid and eid not in seen_eids:
                ordered_cards.append((card, val_by_eid[eid]))
                seen_eids.add(eid)
    remaining = sorted(
        ((card, val_by_eid[card["evidence_id"]])
         for card, _ in scope if card["evidence_id"] not in seen_eids),
        key=lambda pair: _fallback_card_key(pair[0]))
    # 排序序列在前(选中卡 → 模型 order → 背书后备键);其余审查范围内卡
    # 的产品记录同样逐条保留(带拒因),只是不进入报告排序
    ordered_cards.extend(remaining)

    # ---- 产品级记录(逐位重算身份,不信任缓存)
    products: list[dict] = []
    for card, val in ordered_cards:
        eid = card["evidence_id"]
        verdict_by_pos = {int(v["position"]): v
                          for v in val.get("verdicts", [])}
        for prod in sorted(card.get("products", []),
                           key=lambda q: int(q.get("position", 0))):
            pos = int(prod.get("position", 0))
            raw_full = (prod.get("product_smiles_full") or "").strip()
            raw_smiles = (prod.get("product_smiles") or "").strip()
            raw = raw_full or raw_smiles
            computed = cn_identity(raw) if raw else None
            verdict = verdict_by_pos.get(pos)
            accepted = bool(verdict and verdict.get("accepted"))
            reasons = list(verdict.get("reasons", [])) if verdict else [
                "missing_card_validation"]
            if not raw:
                reasons.append("missing_raw_smiles:无原始产物 SMILES")
            if verdict is not None and not verdict.get("identity_match", True):
                if "identity_mismatch" not in " ".join(reasons):
                    reasons.append("identity_mismatch:原始字符串重算身份不符")
                accepted = False
            products.append({
                "path_id": path_id,
                "evidence_id": eid,
                "card_kind": card.get("kind"),
                "entry_layer": val.get("entry_layer",
                                       ENTRY_LAYER_RETRIEVAL),
                "retrieval_rank": card.get("retrieval_rank"),
                "task_candidate_position": task_pos.get(eid),
                "model_order_position": order_pos.get(eid),
                "position": pos,
                "product_smiles_full": raw_full,
                "product_smiles": raw_smiles,
                "raw_source": "product_smiles_full" if raw_full
                else ("product_smiles" if raw_smiles else ""),
                "cn_identity": computed or "",
                "stored_product_identity": prod.get("product_identity"),
                "identity_match": bool(
                    computed is not None
                    and prod.get("product_identity") == computed),
                "validation_ref": dict(validation_refs[eid]),
                "validation_verdict_hash": content_hash(verdict) if verdict
                else "",
                "accepted": accepted,
                "reasons": reasons,
                "reportable": False,       # 由下方去重/上限/背书决定
                "report_rank": None,
                "dedup_reason": "",
                "committed_event_ref": None,
                "expand_selected": False,
                "deferred": False,
                "expand_status": "accepted" if accepted else "rejected",
                "endorsed": endorsed(eid, val),
            })

    def ref_of(rec: dict) -> dict:
        return {"evidence_id": rec["evidence_id"],
                "position": rec["position"],
                "validation_ref": rec["validation_ref"],
                "cn_identity": rec["cn_identity"]}

    # ---- 去重 + 位次:相同 cn 只占一个位次;超过宽度不占位,留拒因
    rank = 0
    primary_by_cn: dict[str, dict] = {}
    for rec in products:
        if not (rec["accepted"] and rec["endorsed"]
                and val_by_eid[rec["evidence_id"]].get("card_eligible", True)):
            continue
        cn = rec["cn_identity"]
        if not cn:
            continue
        primary = primary_by_cn.get(cn)
        if primary is not None:
            rec["dedup_reason"] = (
                f"duplicate_cn_of:{primary['evidence_id']}"
                f"#{primary['position']}")
            primary.setdefault("same_identity_sources", []).append(ref_of(rec))
            continue
        if rank >= max_reportable:
            rec["dedup_reason"] = (
                f"report_width_cap:{max_reportable}")
            continue
        rank += 1
        rec["reportable"] = True
        rec["report_rank"] = rank
        primary_by_cn[cn] = rec

    # ---- 事件提交事实(final)
    # 提交集 = 选中卡**占用报告位次**的产物(committed ⇒ reportable 不变量;
    # 超出报告宽度的合格产物保持已验证、未提交,留宽度拒因)
    event_id = None
    if stage == STAGE_FINAL and event_commit:
        event_id = event_commit["event_id"]
        expand_pos = set(event_commit.get("expand_positions", []))
        deferred_pos = set(event_commit.get("deferred_positions", []))
        for rec in products:
            if rec["evidence_id"] != selected_evidence_id \
                    or rec["report_rank"] is None:
                continue
            rec["committed_event_ref"] = event_id
            if rec["position"] in expand_pos:
                rec["expand_selected"] = True
                rec["expand_status"] = "frontier"
            elif rec["position"] in deferred_pos:
                rec["deferred"] = True
                rec["expand_status"] = "deferred"

    n_ranked = sum(1 for r in products if r["reportable"])
    # 未进报告的已接受产物留显式拒因(P2 R1:层次分明)—— 卡资格复验
    # 失败 → 带卡级拒因(含选中卡);order 未含此卡 → 不推断模型认可
    for rec in products:
        if rec["accepted"] and not rec["reportable"] and not rec["dedup_reason"]:
            card_val = val_by_eid[rec["evidence_id"]]
            if not card_val.get("card_eligible", True):
                rec["reasons"].extend(
                    r for r in card_val.get("card_reasons", [])
                    if r not in rec["reasons"])
            elif not rec["endorsed"]:
                rec["reasons"].append(
                    "not_in_model_order_not_promoted:"
                    "模型 order 未含此卡且无单独可核验证据,不升格为可报告")
    payload = {
        "schema_version": REPORT_ADJUDICATION_SCHEMA_V2,
        "task_kind": "report_adjudication",
        "stage": stage,
        "run_id": run_id,
        "path_id": path_id,
        "substrate_identity": substrate_identity,
        "policy": {k: v for k, v in pol.items()},
        "rank_basis": sel["rank_basis"],
        "selection": {
            "selected_evidence_id": selected_evidence_id,
            "selected_card_kind": selected_card.get("kind"),
            "model_order": list(order),
            "order_missing": bool(sel["order_missing"]),
            "mode": sel["mode"],
            "model_decision_ref": sel["model_decision_ref"],
        },
        "cards": cards,
        "products": products,
        "event": (
            {"event_id": event_id, "no_event": event_id is None,
             "no_event_reason": no_event_reason}
            if stage == STAGE_FINAL else None),
        "n_reportable": n_ranked,
        "n_committed": sum(1 for r in products
                           if r["committed_event_ref"] is not None),
        "n_expand_selected": sum(1 for r in products if r["expand_selected"]),
        "n_deferred": sum(1 for r in products if r["deferred"]),
    }
    validate_adjudication_payload(payload)
    return payload


# ---------------------------------------------------------------- 不变量


def validate_adjudication_payload(payload: dict) -> None:
    """v2 裁决不变量(任务书 §2;写入前与导出/报告读取时都执行):

    - ``expand_selected ⇒ committed_event_ref != null ⇒ reportable ⇒
      accepted``;已提交条目必须属于选中卡;
    - ``report_rank`` 仅给最终可报告去重项,按父节点连续从 1 编号、
      最多五位;reportable ⇔ report_rank != null;
    - 相同 cn 只占一个位次;审查与报告以父 path_id 为作用域;
    - final 必须有事件块(真实事件引用或显式 no_event);draft 无事件块。
    """
    def bad(msg: str, detail: dict) -> None:
        raise AdjudicationError(f"裁决不变量违反:{msg}", detail)

    if payload.get("schema_version") != REPORT_ADJUDICATION_SCHEMA_V2:
        bad("schema_version 非 v2",
            {"schema_version": payload.get("schema_version")})
    stage = payload.get("stage")
    if stage not in (STAGE_DRAFT, STAGE_FINAL):
        bad("stage 非法", {"stage": stage})
    path_id = payload.get("path_id")
    max_reportable = int(
        (payload.get("policy") or {}).get("max_reportable_products", 5))
    products = payload.get("products") or []
    selected = (payload.get("selection") or {}).get("selected_evidence_id")
    event_block = payload.get("event")
    if stage == STAGE_FINAL and event_block is None:
        bad("final 裁决缺事件块", {"path_id": path_id})
    if stage == STAGE_DRAFT and event_block is not None:
        bad("draft 裁决不得含事件块", {"path_id": path_id})

    ranks: list[int] = []
    ranked_cns: set[str] = set()
    for rec in products:
        if rec.get("path_id") != path_id:
            bad("产品记录跨父串线",
                {"path_id": path_id, "record": rec.get("path_id")})
        accepted = bool(rec.get("accepted"))
        reportable = bool(rec.get("reportable"))
        rrank = rec.get("report_rank")
        cref = rec.get("committed_event_ref")
        expand = bool(rec.get("expand_selected"))
        if reportable != (rrank is not None):
            bad("reportable 与 report_rank 不一致",
                {"path_id": path_id, "position": rec.get("position"),
                 "reportable": reportable, "report_rank": rrank})
        if reportable and not accepted:
            bad("可报告产物未通过逐项验证(reportable ⇒ accepted)",
                {"path_id": path_id, "evidence_id": rec.get("evidence_id"),
                 "position": rec.get("position"), "reasons":
                     rec.get("reasons", [])})
        if reportable:
            # Phase B R1(P1-2):可报告条目必须携带完整验证产物引用,
            # 能按裁决直接回查逐卡验证(validation.json / cardval.*.json)
            ref = rec.get("validation_ref") or {}
            missing = [k for k in ("task_id", "artifact", "payload_sha256")
                       if not ref.get(k)]
            if missing:
                bad("可报告条目验证引用不完整",
                    {"path_id": path_id,
                     "evidence_id": rec.get("evidence_id"),
                     "position": rec.get("position"),
                     "missing": missing})
        if expand and cref is None:
            bad("expand_selected 但无 committed_event_ref",
                {"path_id": path_id, "position": rec.get("position")})
        if cref is not None:
            if not reportable:
                bad("已提交产物不可报告(committed ⇒ reportable)",
                    {"path_id": path_id, "position": rec.get("position")})
            if rec.get("evidence_id") != selected:
                bad("已提交条目不属于选中卡",
                    {"path_id": path_id, "evidence_id": rec.get("evidence_id"),
                     "selected": selected})
            if stage == STAGE_FINAL and event_block.get("event_id") != cref:
                bad("已提交引用与事件块不一致",
                    {"path_id": path_id, "ref": cref,
                     "event": event_block.get("event_id")})
        if rrank is not None:
            ranks.append(int(rrank))
            cn = rec.get("cn_identity") or ""
            if cn in ranked_cns:
                bad("相同 cn 占用多个报告位次",
                    {"path_id": path_id, "cn": cn})
            ranked_cns.add(cn)
    if ranks != list(range(1, len(ranks) + 1)):
        bad("report_rank 必须按父节点连续从 1 编号",
            {"path_id": path_id, "ranks": ranks})
    if len(ranks) > max_reportable:
        bad("报告位次超过每父上限",
            {"path_id": path_id, "n": len(ranks), "cap": max_reportable})
    if stage == STAGE_FINAL and event_block.get("no_event"):
        if any(r.get("committed_event_ref") is not None for r in products):
            bad("no_event 终态含已提交引用", {"path_id": path_id})
        if not event_block.get("no_event_reason"):
            bad("no_event 终态缺拒因", {"path_id": path_id})


def resolve_adjudication_validation_refs(run_dir, payload: dict) -> dict:
    """读取端 fail-closed 回查(Phase B R1 P1-2):最终裁决的每个可报告
    条目必须能解析到真实验证产物及其对应 verdict —— ID、位次、raw/cn 与
    accepted 值逐项一致;产物缺失、引用错指、payload 哈希不符即抛
    AdjudicationError(导出/报告读取时调用,不静默放过)。

    run_dir = 运行目录(含 results/);产物路径
    ``<run_dir>/results/<task_id>/<artifact>.json``,读取时核信封
    payload_hash 与裁决引用一致。返回核对摘要;不修改任何产物。
    """
    import json as _json
    from pathlib import Path as _Path

    from ..domain.models import content_hash

    results = _Path(run_dir) / "results"
    loaded: dict[tuple[str, str], dict] = {}

    def _load(ref: dict) -> dict:
        key = (ref["task_id"], ref["artifact"])
        if key not in loaded:
            path = results / ref["task_id"] / f"{ref['artifact']}.json"
            if not path.is_file():
                raise AdjudicationError(
                    "验证产物缺失(裁决引用悬空)",
                    {"task_id": ref["task_id"],
                     "artifact": ref["artifact"],
                     "path": str(path)})
            try:
                envelope = _json.loads(path.read_text(encoding="utf-8"))
            except Exception as exc:
                raise AdjudicationError(
                    f"验证产物无法解析:{path}",
                    {"error": str(exc)[:200]})
            actual = content_hash(envelope.get("payload", {}))
            if envelope.get("payload_hash") != actual:
                raise AdjudicationError(
                    "验证产物信封哈希与内容不符(被篡改或损坏)",
                    {"task_id": ref["task_id"],
                     "artifact": ref["artifact"]})
            if actual != ref["payload_sha256"]:
                raise AdjudicationError(
                    "验证产物哈希与裁决引用不符(错指或篡改)",
                    {"task_id": ref["task_id"],
                     "artifact": ref["artifact"],
                     "ref_sha": str(ref["payload_sha256"])[:12],
                     "actual_sha": actual[:12]})
            loaded[key] = envelope["payload"]
        return loaded[key]

    checked = 0
    for rec in payload.get("products", []):
        if not rec.get("reportable"):
            continue
        ref = rec.get("validation_ref") or {}
        val = _load(ref)
        if val.get("evidence_id") != rec.get("evidence_id"):
            raise AdjudicationError(
                "验证产物 evidence_id 与裁决条目不一致",
                {"artifact_evidence_id": val.get("evidence_id"),
                 "entry_evidence_id": rec.get("evidence_id"),
                 "position": rec.get("position")})
        pos = rec.get("position")
        verdict = next(
            (v for v in val.get("verdicts", [])
             if int(v.get("position", -1)) == int(pos)), None)
        if verdict is None:
            raise AdjudicationError(
                "验证产物无对应位次 verdict",
                {"task_id": ref["task_id"], "artifact": ref["artifact"],
                 "position": pos})
        raw = (rec.get("product_smiles_full") or rec.get("product_smiles")
               or "").strip()
        if (verdict.get("product_smiles") or "").strip() != raw:
            raise AdjudicationError(
                "verdict 原始 SMILES 与裁决条目不一致",
                {"position": pos, "verdict": verdict.get("product_smiles"),
                 "entry": raw})
        if verdict.get("product_identity") != rec.get("cn_identity"):
            raise AdjudicationError(
                "verdict 身份与裁决条目 cn_identity 不一致",
                {"position": pos,
                 "verdict": verdict.get("product_identity"),
                 "entry": rec.get("cn_identity")})
        if bool(verdict.get("accepted")) != bool(rec.get("accepted")):
            raise AdjudicationError(
                "verdict accepted 与裁决条目不一致",
                {"position": pos, "verdict": verdict.get("accepted"),
                 "entry": rec.get("accepted")})
        checked += 1
    return {"n_reportable_checked": checked,
            "n_validation_artifacts": len(loaded)}
