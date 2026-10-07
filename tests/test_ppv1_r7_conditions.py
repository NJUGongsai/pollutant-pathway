"""R7 条件与上下文线回归(Codex R6 复审 R6-03;v7)。

规则级合成夹具;无金标/封存材料。先红后绿:红验证在基线 6d90201
工作树复跑本文件(与 R6 同口径);v7 实现后全绿。

R6-03:derive_child_context 先验证父对象(与 from_dict/audit 共用
validate_context_object 同源契约);历史快照 covered_requirement_
signatures 必须与逐条评估行的 requirement_signature 集合双向一致
(签名须对应**实际记录的评估**,不能只属累积要求集合)。旧 pH
unknown 快照删 per_requirement/清 coverage/降 has_gate 而保留真实
签名:直接 audit 拒、公开 derive 拒(不得不加新事实重算子 ID 洗掉
旧必要未知)、from_dict 拒;合法历史 unknown/conflict/satisfied、
正常阶段转换、same phase 跨 scenario、凭空签名拒绝控制保持。
"""

from __future__ import annotations

import copy
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pathway_v43.pollutant.audit import (  # noqa: E402
    audit_hypothesis,
    center_evidence_from_donor_diagnostic,
    check_edit_against_donor,
    decide_admission,
)
from pathway_v43.pollutant.chemstate import (  # noqa: E402
    build_chemical_state,
)
from pathway_v43.pollutant.hypothesis import (  # noqa: E402
    Participant,
    build_hypothesis,
)
from pathway_v43.pollutant.path_context import (  # noqa: E402
    ConditionContractError,
    PathContext,
    assess_candidate_conditions,
    build_condition_fact,
    build_path_context,
    build_requirement,
    derive_child_context,
)
from pathway_v43.services.atom_tool import (  # noqa: E402
    execute_edits,
    roundtrip,
)

SRC = ["src:synthetic-rule"]


def _fact(key, value, **kw):
    return build_condition_fact(key=key, value=value,
                                status="known_present", **kw)


def _req(key, value, **kw):
    return build_requirement(key=key, level="essential", value=value,
                             source_refs=SRC, **kw)


def _oxygen_hyp(requirements=None):
    """带氧气必要要求的乙醇氧化假设(供条件检查消费)。"""
    states = {s: build_chemical_state(s, "raw_input")
              for s in ("CCO", "CC=O", "[H][H]")}
    hyp = build_hypothesis(
        parent_path_id="p1", substrate_state_ref=states["CCO"].state_id,
        participants=[
            Participant(state_ref=states["CCO"].state_id, side="reactant",
                        role="primary_substrate", coefficient=1,
                        coefficient_status="known"),
            Participant(state_ref=states["CC=O"].state_id, side="product",
                        role="principal_product", coefficient=1,
                        coefficient_status="known"),
            Participant(state_ref=states["[H][H]"].state_id,
                        side="product", role="coproduct", coefficient=1,
                        coefficient_status="known")],
        participant_list_status="declared_complete",
        step_scope="net_reaction", origin_group_key="r7-cond",
        requirements=requirements or [
            _req("oxygen_regime", "aerobic").to_dict()])
    render = roundtrip("CCO", name="S")
    edits = [{"op": "change_bond_order", "atom1": "S_C_2",
              "atom2": "S_O_1", "from_order": "single",
              "to_order": "double"}]
    execution = execute_edits(render, edits)
    assert execution["ok"] is True
    diag = check_edit_against_donor(
        current={"smiles": render.smiles,
                 "atom_id_map": dict(render.atom_id_map)},
        donor={"center_atom_ids": ["dC", "dO"]},
        alignment={"status": "resolved",
                   "donor_to_current": {"dC": "S_C_2", "dO": "S_O_1"},
                   "equivalence_classes": [], "ref": "r7-cond"},
        expectation={"target_smiles": execution["product_smiles"]},
        result=execution, edits=edits)
    return hyp, {s.state_id: s for s in states.values()}, \
        center_evidence_from_donor_diagnostic(diag)


def _audit(hyp, states, context, evidence):
    audit = audit_hypothesis(hyp, states=states, context=context,
                             center_evidence=evidence)
    condition = next(c for c in audit.checks
                     if c.name == "condition_check")
    return {"condition_status": condition.status,
            "admission": decide_admission(audit)}


def _ph_unknown_child():
    """R6 复审场景:p0 必要 pH 6–8、事实缺失为 unknown;转 p1 当前
    有氧必要条件满足(旧 pH 快照使审核 retain)。"""
    parent = build_path_context(
        condition_facts=[_fact("oxygen_regime", "aerobic")],
        phase_id="p0", scenario_ref="s",
        accumulated_requirements=[_req("pH", {"lo": 6, "hi": 8})],
        assessment_scope=["oxygen_regime", "pH"])
    return derive_child_context(
        parent, step_requirements=[_req("oxygen_regime", "aerobic")],
        step_edge_ref="hyp:current",
        scenario_transition={"new_phase_id": "p1",
                             "source_ref": "user:synthetic-transition"})


def _tamper_snapshot(context, drop_signature=False):
    """就地清空快照评估行/coverage/降 has_gate;默认保留真实签名。"""
    snap = context.phase_history[0]
    snap["per_requirement"] = []
    snap["requirement_coverage"] = {
        k: [] for k in snap["requirement_coverage"]}
    snap["has_gate_requirements"] = False
    # 摘要保持 unknown(与既有快照记录一致方向,非洗绿)
    if drop_signature:
        snap["covered_requirement_signatures"] = []
    return context


# ------------------------------------------------------ R6-03 反例

def test_r6_03_untempered_child_keeps_honest_unknown() -> None:
    """对照(基线亦绿):未篡改的合法子上下文 —— 旧 pH unknown 由
    快照承载,路线 unknown、条件检查 unknown、retain(不 R6)。"""
    child = _ph_unknown_child()
    hyp, states, evidence = _oxygen_hyp()
    result = _audit(hyp, states, child, evidence)
    assert result["condition_status"] == "unknown"
    assert result["admission"][0] == "retain_conditional"
    # 合法快照:签名与评估行双向同源(行携带 requirement_signature)
    snap = child.phase_history[0]
    row_sigs = {row["requirement_signature"]
                for row in snap["per_requirement"]}
    assert row_sigs == set(snap["covered_requirement_signatures"])
    assert snap["covered_requirement_signatures"]
    # to_dict→from_dict 幂等往返(合法历史)
    restored = PathContext.from_dict(child.to_dict())
    assert restored.context_id == child.context_id


def test_r6_03_tampered_parent_direct_audit_rejected() -> None:
    """R6 复审残余(基线半红):删评估行/清 coverage/降 has_gate 而
    保留真实 pH 签名 —— 基线直接 audit 已拒(内容身份);v7 还在
    快照一致性层拒绝(签名无对应评估行),双重同源。"""
    child = _tamper_snapshot(_ph_unknown_child())
    hyp, states, evidence = _oxygen_hyp()
    with pytest.raises(ConditionContractError) as ei:
        _audit(hyp, states, child, evidence)
    assert ei.value.detail["kind"] in (
        "context_snapshot_inconsistent", "context_content_identity_mismatch")


def test_r6_03_derive_rejects_tampered_parent() -> None:
    """R6 复审反例,基线 6d90201 红:public derive_child_context
    (parent) 不传新事实/要求/转换,却重算合法新 child ID —— 旧 pH
    不再参与门禁、audit verified/R6、child→dict→from_dict 后再审也
    R6。v7:派生入口先走 validate_context_object(父对象内容身份/
    快照一致性),篡改父 ⇒ 拒,不再产生"合法"子对象。"""
    child = _tamper_snapshot(_ph_unknown_child())
    with pytest.raises(ConditionContractError) as ei:
        derive_child_context(child)
    assert ei.value.detail["kind"] in (
        "context_snapshot_inconsistent", "context_content_identity_mismatch")


def test_r6_03_from_dict_rejects_signature_without_rows() -> None:
    """R6-03 恢复入口收紧,v7 生效(基线说明按 Codex R7 §6.4 更正:
    **id 未换**的篡改载荷经 from_dict 在基线已由内容身份层拒绝,此项
    基线绿;R6-03 原反例的基线红在 **derive 洗出新 ID** 后恢复接受。
    v7 新增的是快照一致性层签名↔评估行双向对应—— 保留签名/删行且
    id 未换的形状现在在该层报 signature_row_correspondence,恢复入口
    与 audit/derive 同源)。"""
    child = _tamper_snapshot(_ph_unknown_child())
    raw = child.to_dict()
    with pytest.raises(ConditionContractError) as ei:
        PathContext.from_dict(raw)
    assert ei.value.detail["kind"] in (
        "context_snapshot_inconsistent", "context_content_identity_mismatch")


def test_r6_03_signature_row_correspondence_error_is_specific() -> None:
    """R6-03 验收细节:残余形状(签名保留/行删空)在快照一致性层报
    signature_row_correspondence(区别于内容身份/凭空签名两族),
    机器披露"签名无评估行"一侧。"""
    from pathway_v43.pollutant.path_context import (
        _validate_phase_history_snapshot)
    child = _ph_unknown_child()
    snap = child.phase_history[0]
    kept = list(snap["covered_requirement_signatures"])
    snap["per_requirement"] = []
    snap["requirement_coverage"] = {
        k: [] for k in snap["requirement_coverage"]}
    snap["has_gate_requirements"] = False
    with pytest.raises(ConditionContractError) as ei:
        _validate_phase_history_snapshot(
            child.phase_history, child.accumulated_requirements)
    assert ei.value.detail["check"] == "signature_row_correspondence"
    assert ei.value.detail["signatures_without_rows"]
    assert kept  # 场景自证:确实保留了真实签名


def test_r6_03_drop_signature_and_rows_is_orphan_unknown() -> None:
    """诚实方向(基线亦绿):连签名一起删的"空快照"在快照一致性层
    自洽(双方皆空);完全重算 id 的自洽历史不在验收内,此处构造
    同一形状验证诚实语义:旧 pH 要求变孤儿绑定,路线/条件 unknown、
    retain —— 未知以孤儿行显式保留(不静默丢弃,不拿当前事实重评),
    不比基线更差。"""
    child = _ph_unknown_child()
    _tamper_snapshot(child, drop_signature=True)
    rebuilt = _rebuild_self_consistent(child)
    hyp, states, evidence = _oxygen_hyp()
    assessment = assess_candidate_conditions(rebuilt, hyp)
    assert assessment.environment_fit == "unknown"
    orphan_rows = [p for p in assessment.per_requirement
                   if p.get("route_edge_source") == "orphan_binding"]
    assert orphan_rows and orphan_rows[0]["key"] == "pH"
    assert _audit(hyp, states, rebuilt, evidence)[
        "condition_status"] == "unknown"


def _rebuild_self_consistent(context):
    """按篡改后的语义字段重算内容身份,构造自洽对象(模拟完全重造
    自洽历史;验收只要求该方向诚实保留 unknown,不要求防住)。"""
    from pathway_v43.pollutant.path_context import (
        ConditionFact, Dependency, Requirement, _recompute_context_hash)
    payload = context.to_dict()
    rebuilt = PathContext(
        context_id="pending", parent_context_ref=payload[
            "parent_context_ref"],
        phase_id=payload["phase_id"],
        requested_scope=payload["requested_scope"],
        condition_facts=[ConditionFact(**f)
                         for f in payload["condition_facts"]],
        accumulated_requirements=[Requirement(**r) for r in
                                  payload["accumulated_requirements"]],
        assumptions=list(payload["assumptions"]),
        dependency_refs=list(payload["dependency_refs"]),
        dependencies=[Dependency(**d) for d in
                      payload["dependencies"]],
        assessment_scope=list(payload["assessment_scope"]),
        scenario_ref=payload["scenario_ref"],
        scenario_transition=payload["scenario_transition"],
        phase_history=copy.deepcopy(payload["phase_history"]))
    rebuilt.context_id = _recompute_context_hash(rebuilt)
    return rebuilt


# ------------------------------------------------------ 既有控制保持

def test_r6_03_legal_conflict_history_roundtrip_kept() -> None:
    """既有控制(基线亦绿):合法历史 conflict 往返保持 defer/拒。"""
    parent = build_path_context(
        condition_facts=[_fact("oxygen_regime", "anaerobic",
                               phase_id="p0",
                               subject_scenario_ref="sA"),
                         _fact("oxygen_regime", "aerobic",
                               phase_id="p1",
                               subject_scenario_ref="sB")],
        phase_id="p0", scenario_ref="sA",
        accumulated_requirements=[_req("oxygen_regime", "anaerobic")],
        assessment_scope=["oxygen_regime"])
    child = derive_child_context(
        parent, step_requirements=[_req("oxygen_regime", "anaerobic")],
        scenario_transition={"new_phase_id": "p1",
                             "new_scenario_ref": "sB",
                             "source_ref": "user:synthetic"})
    restored = PathContext.from_dict(child.to_dict())
    assert restored.context_id == child.context_id
    hyp, states, evidence = _oxygen_hyp(
        [_req("oxygen_regime", "anaerobic").to_dict()])
    result = _audit(hyp, states, restored, evidence)
    assert result["condition_status"] == "violated"
    assert result["admission"][0] == "defer"


def test_r6_03_legal_satisfied_history_and_transition_kept() -> None:
    """既有控制(基线亦绿):满足历史 + 正常阶段转换 ⇒ 子上下文可
    往返;同 phase 跨 scenario 转换合法;多重 derive 链(孙上下文)
    仍验证父对象通过。"""
    parent = build_path_context(
        condition_facts=[_fact("oxygen_regime", "aerobic")],
        phase_id="p0", scenario_ref="sA",
        accumulated_requirements=[_req("oxygen_regime", "aerobic")],
        assessment_scope=["oxygen_regime"])
    child = derive_child_context(
        parent,
        scenario_transition={"new_phase_id": "p1",
                             "new_scenario_ref": "sB",
                             "source_ref": "user:synthetic"})
    grandchild = derive_child_context(child)  # 无转换派生:验证父通过
    restored = PathContext.from_dict(grandchild.to_dict())
    assert restored.context_id == grandchild.context_id
    hyp, states, evidence = _oxygen_hyp()
    result = _audit(hyp, states, restored, evidence)
    assert result["condition_status"] == "verified"
    assert result["admission"][0] == "expand"


def test_r6_03_invented_signature_still_rejected() -> None:
    """既有控制(基线亦绿):凭空签名(累积要求集合之外)拒绝。"""
    child = _ph_unknown_child()
    raw = child.to_dict()
    raw["phase_history"][0]["covered_requirement_signatures"].append(
        "unassessed:invented_signature")
    with pytest.raises(ConditionContractError) as ei:
        PathContext.from_dict(raw)
    assert ei.value.detail["check"] == "signature_not_in_requirements"


def test_r6_03_snapshot_row_tampering_still_rejected() -> None:
    """既有控制(基线亦绿):摘要/旗标篡改(洗绿)在恢复与直接对象
    入口保持拒绝(v7 签名↔行对应在其上再加一层,不替代)。
    R8 P2 修正:末段此前的实参顺序写反(_oxygen_hyp() 展开把 evidence
    当 context 传,实际断的是 context_object_invalid_type 而非旗标
    篡改);修正后 child2 的 has_gate_requirements 篡改按真实链路报
    gate_flag_mismatch(Codex R7 §6.3)。"""
    child = _ph_unknown_child()
    raw = child.to_dict()
    raw["phase_history"][0]["environment_fit"] = "compatible"
    with pytest.raises(ConditionContractError):
        PathContext.from_dict(raw)
    child2 = _ph_unknown_child()
    child2.phase_history[0]["has_gate_requirements"] = False
    hyp, states, evidence = _oxygen_hyp()
    with pytest.raises(ConditionContractError) as ei:
        _audit(hyp, states, child2, evidence)
    assert ei.value.detail["check"] == "gate_flag_mismatch"
