"""R6 条件与科学前提线回归(Codex R5 复审 R5-03/R5-04 + §4 披露 2;v6)。

规则级合成夹具;模型 off,无金标/封存材料。先红后绿:红验证在基线
工作树(293bc62,v5)复跑本文件;v6 实现后全绿。复审反例精确形状取自
docs/review_evidence/ppv1_r5_codex_2026-10-07/conditions_probe.py
(known_absent_non_species_false_satisfied、snapshot_from_dict_
conflict_summary_and_flag_tamper、axis_controls_and_cross_axis_
diagnostic),真实诊断→audit→admission 全链复用探针模式
(roundtrip CCO + change_bond_order S_C_2–S_O_1)。

R5-03:非物种 known_absent 不作正事实 —— oxygen aerobic absent /
matrix soil absent ⇒ conflict(必需值被明确否定);温度数值 absent ⇒
unknown(数值否定语义未定义);不同字符串值缺席 ⇒ unknown。物种实体
缺席负控制(required_entity_known_absent)、present、单位三态、
氧枚举不等 ⇒ conflict 均保持。

R5-04:from_dict(恢复入口)与 audit 直接对象入口核 phase_history
快照内部一致性(environment_fit 摘要/has_gate_requirements 旗标/
requirement_coverage.essential_keys 与逐条行同源派生 +
covered_requirement_signatures ∈ 当前累积要求签名集合)+ 内容身份
(与构造期同源 _context_hash 重算 context_id)。篡改摘要/旗标/事实
而保留原 context_id ⇒ 结构化拒绝;合法 to_dict→from_dict 往返幂等
(含依赖对象);正常阶段转换路线 conflict→defer 不被重评洗掉。

P2(§4 披露 2):环诊断按对应有效轴消费 —— 启动轴与关系轴分立,
不以总体 status 污染两种语义;audit 侧 provenance 仍消费总体
status(方向正确)保持。
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pathway_v43.pollutant.audit import (  # noqa: E402
    CHECK_CONDITION_CHECK,
    audit_hypothesis,
    center_evidence_from_donor_diagnostic,
    check_edit_against_donor,
    decide_admission,
)
from pathway_v43.pollutant.chemstate import build_chemical_state  # noqa: E402
from pathway_v43.pollutant.hypothesis import (  # noqa: E402
    PARTICIPANT_LIST_DECLARED_COMPLETE,
    COEFFICIENT_KNOWN,
    Participant,
    build_hypothesis,
)
from pathway_v43.pollutant.path_context import (  # noqa: E402
    CONDITION_KEY_ELECTRON_DONOR,
    CONDITION_KEY_MATRIX,
    CONDITION_KEY_OXYGEN,
    CONDITION_KEY_PH,
    CONDITION_KEY_TEMPERATURE,
    ConditionContractError,
    PathContext,
    aggregate_environment_fit,
    assess_candidate_conditions,
    build_condition_fact,
    build_dependency,
    build_path_context,
    build_requirement,
    derive_child_context,
    detect_circular_dependencies,
    resolve_dependency,
)
from pathway_v43.services.atom_tool import execute_edits, roundtrip  # noqa: E402

SRC = ["src:rule-r6"]


def f(key, value, **kw):
    return build_condition_fact(key=key, value=value,
                                status="known_present", **kw)


def r(key, value, **kw):
    return build_requirement(key=key, value=value, level="essential",
                             source_refs=SRC, **kw)


def per_key(result):
    return {p["key"]: p for p in result.per_requirement}


# ------------------------------------------------- 真实诊断链(探针模式)
# roundtrip CCO + change_bond_order S_C_2–S_O_1 → 诊断 → center 证据;
# 与 conditions_probe.py 同构,全部合成结构。

_STATES = {s: build_chemical_state(s, "raw_input")
           for s in ("CCO", "CC=O", "[H][H]")}
STATE_MAP = {s.state_id: s for s in _STATES.values()}
_RENDER = roundtrip("CCO", name="S")
_EDITS = [{"op": "change_bond_order", "atom1": "S_C_2", "atom2": "S_O_1",
           "from_order": "single", "to_order": "double"}]
_EXECUTION = execute_edits(_RENDER, _EDITS)
assert _EXECUTION["ok"]
_DIAG = check_edit_against_donor(
    current={"smiles": _RENDER.smiles,
             "atom_id_map": dict(_RENDER.atom_id_map)},
    donor={"center_atom_ids": ["dC", "dO"]},
    alignment={"status": "resolved",
               "donor_to_current": {"dC": "S_C_2", "dO": "S_O_1"},
               "equivalence_classes": [], "ref": "synthetic:alignment"},
    expectation={"target_smiles": _EXECUTION["product_smiles"]},
    result=_EXECUTION, edits=_EDITS)
CENTER = center_evidence_from_donor_diagnostic(_DIAG)


def _hyp(reqs=None, deps=None):
    return build_hypothesis(
        parent_path_id="synthetic:parent",
        substrate_state_ref=_STATES["CCO"].state_id,
        participants=[Participant(state_ref=_STATES[s].state_id, side=side,
                                  role=role, coefficient=1,
                                  coefficient_status=COEFFICIENT_KNOWN)
                      for s, side, role in (
                          ("CCO", "reactant", "primary_substrate"),
                          ("CC=O", "product", "principal_product"),
                          ("[H][H]", "product", "coproduct"))],
        participant_list_status=PARTICIPANT_LIST_DECLARED_COMPLETE,
        step_scope="net_reaction", origin_group_key="r6-cond",
        requirements=[v.to_dict() for v in (reqs or [])],
        dependency_refs=deps or [])


def _audit(ctx, reqs):
    """真实诊断→audit→admission 全链;返回 (条件检查, 处置)。"""
    hyp = _hyp(reqs)
    audit = audit_hypothesis(hyp, states=STATE_MAP, context=ctx,
                             center_evidence=CENTER)
    cond = next(c for c in audit.checks if c.name == CHECK_CONDITION_CHECK)
    disposition, _ = decide_admission(audit)
    return cond, disposition


# ============================================================ R5-03
# 非物种 known_absent 不作正事实(conditions_probe:
# known_absent_non_species_false_satisfied)


def test_r5_03_oxygen_required_value_absent_conflict() -> None:
    """复审反例:oxygen_regime='aerobic' known_absent + 必需 aerobic ⇒
    conflict(required_value_known_absent;明确否定必需值),audit 条件
   检查 violated ⇒ admission defer(v5 satisfied/value_match →
    verified → R6)。"""
    ctx = build_path_context(
        condition_facts=[build_condition_fact(
            key=CONDITION_KEY_OXYGEN, value="aerobic",
            status="known_absent", source_ref="src:synthetic_absence")],
        phase_id="p0", scenario_ref="s",
        assessment_scope=[CONDITION_KEY_OXYGEN])
    result = aggregate_environment_fit(
        facts=ctx.condition_facts,
        requirements=[r(CONDITION_KEY_OXYGEN, "aerobic")],
        declared_scope=[CONDITION_KEY_OXYGEN])
    row = per_key(result)[CONDITION_KEY_OXYGEN]
    assert row["status"] == "conflict"
    assert "required_value_known_absent" in row["reason"]
    assert result.environment_fit == "conflict"
    cond, disposition = _audit(
        ctx, [r(CONDITION_KEY_OXYGEN, "aerobic")])
    assert cond.status == "violated"
    assert disposition == "defer"  # v5 曾 R6 expand


def test_r5_03_matrix_required_value_absent_conflict() -> None:
    """复审反例:matrix='soil' known_absent + 必需 soil ⇒ conflict
    (同词标签被明确否定);audit violated ⇒ defer(v5 satisfied → R6)。"""
    ctx = build_path_context(
        condition_facts=[build_condition_fact(
            key=CONDITION_KEY_MATRIX, value="soil",
            status="known_absent", source_ref="src:synthetic_absence")],
        phase_id="p0", scenario_ref="s",
        assessment_scope=[CONDITION_KEY_MATRIX])
    cond, disposition = _audit(ctx, [r(CONDITION_KEY_MATRIX, "soil")])
    assert cond.status == "violated"
    assert disposition == "defer"  # v5 曾 R6 expand


def test_r5_03_numeric_absence_unknown_not_satisfied() -> None:
    """复审反例:温度 25°C known_absent + 必需区间 20–30 ⇒ unknown
    (numeric_absence_semantics_undefined:"25 不存在"推不出整个区间
    不存在;首版未定义数值否定语义,不按正值直比),audit unknown ⇒
    不可 expand(v5 within_range satisfied → R6)。"""
    ctx = build_path_context(
        condition_facts=[build_condition_fact(
            key=CONDITION_KEY_TEMPERATURE, value=25, unit="C",
            status="known_absent", source_ref="src:synthetic_absence")],
        phase_id="p0", scenario_ref="s",
        assessment_scope=[CONDITION_KEY_TEMPERATURE])
    result = aggregate_environment_fit(
        facts=ctx.condition_facts,
        requirements=[r(CONDITION_KEY_TEMPERATURE, {"lo": 20, "hi": 30})],
        declared_scope=[CONDITION_KEY_TEMPERATURE])
    row = per_key(result)[CONDITION_KEY_TEMPERATURE]
    assert row["status"] == "unknown"
    assert "numeric_absence_semantics_undefined" in row["reason"]
    assert row["unit_basis"] == "canonical"  # 单位三态已消费(保留)
    cond, disposition = _audit(
        ctx, [r(CONDITION_KEY_TEMPERATURE, {"lo": 20, "hi": 30})])
    assert cond.status == "unknown"
    assert disposition != "expand"  # v5 曾 R6 expand


def test_r5_03_other_string_value_absent_not_determining() -> None:
    """不同字符串值的缺席不判定必需值状态(不明判 unknown 也不冒充
    conflict):oxygen 封闭枚举下"anaerobic 缺席"不证明 aerobic 在场;
    matrix 文本不等只证明标签未解析。"""
    oxygen = aggregate_environment_fit(
        facts=[build_condition_fact(
            key=CONDITION_KEY_OXYGEN, value="anaerobic",
            status="known_absent", source_ref="src:synthetic_absence")],
        requirements=[r(CONDITION_KEY_OXYGEN, "aerobic")],
        declared_scope=[CONDITION_KEY_OXYGEN])
    row = per_key(oxygen)[CONDITION_KEY_OXYGEN]
    assert row["status"] == "unknown"
    assert "other_value_known_absent_not_determining" in row["reason"]
    matrix = aggregate_environment_fit(
        facts=[build_condition_fact(
            key=CONDITION_KEY_MATRIX, value="sandy soil",
            status="known_absent", source_ref="src:synthetic_absence")],
        requirements=[r(CONDITION_KEY_MATRIX, "soil")],
        declared_scope=[CONDITION_KEY_MATRIX])
    row_m = per_key(matrix)[CONDITION_KEY_MATRIX]
    assert row_m["status"] == "unknown"
    assert "other_value_known_absent_not_determining" in row_m["reason"]


def test_r5_03_positive_controls_kept() -> None:
    """正控制:物种实体缺席仍 conflict(实体语义不因本修复放宽);
    present 正常满足;单位三态与氧枚举既有行为不变。"""
    # 物种键:必需实体自身缺席 ⇒ conflict(既有负控制保持)
    species = aggregate_environment_fit(
        facts=[build_condition_fact(
            key=CONDITION_KEY_ELECTRON_DONOR, value="NADH",
            status="known_absent", source_ref="src:synthetic_absence")],
        requirements=[r(CONDITION_KEY_ELECTRON_DONOR, "NADH")],
        declared_scope=[CONDITION_KEY_ELECTRON_DONOR])
    row_s = per_key(species)[CONDITION_KEY_ELECTRON_DONOR]
    assert row_s["status"] == "conflict"
    assert "required_entity_known_absent" in row_s["reason"]
    # present 正常满足
    present = aggregate_environment_fit(
        facts=[f(CONDITION_KEY_OXYGEN, "aerobic")],
        requirements=[r(CONDITION_KEY_OXYGEN, "aerobic")],
        declared_scope=[CONDITION_KEY_OXYGEN])
    assert per_key(present)[CONDITION_KEY_OXYGEN]["status"] == "satisfied"
    # 枚举同值 present 不等 ⇒ conflict(既有 C02 保持)
    mismatch = aggregate_environment_fit(
        facts=[f(CONDITION_KEY_OXYGEN, "anaerobic")],
        requirements=[r(CONDITION_KEY_OXYGEN, "aerobic")],
        declared_scope=[CONDITION_KEY_OXYGEN])
    row_m = per_key(mismatch)[CONDITION_KEY_OXYGEN]
    assert row_m["status"] == "conflict"
    assert "value_mismatch" in row_m["reason"]
    # 单位三态:显式 C 满足(canonical);空单位 unknown;K 未知
    units = {}
    for unit in ("", "C", "K"):
        units[unit] = aggregate_environment_fit(
            facts=[f(CONDITION_KEY_TEMPERATURE, 25, unit=unit)],
            requirements=[r(CONDITION_KEY_TEMPERATURE,
                            {"lo": 20, "hi": 30})],
            declared_scope=[CONDITION_KEY_TEMPERATURE])
    row_c = per_key(units["C"])[CONDITION_KEY_TEMPERATURE]
    assert row_c["status"] == "satisfied"
    assert row_c["unit_basis"] == "canonical"
    row_empty = per_key(units[""])[CONDITION_KEY_TEMPERATURE]
    assert row_empty["status"] == "unknown"
    assert row_empty["unit_basis"] == "source_unit_unknown"
    row_k = per_key(units["K"])[CONDITION_KEY_TEMPERATURE]
    assert row_k["status"] == "unknown"
    assert "unit_mismatch" in row_k["reason"]
    # pH 无量纲不受影响
    ph = aggregate_environment_fit(
        facts=[f(CONDITION_KEY_PH, 7.0)],
        requirements=[r(CONDITION_KEY_PH, {"lo": 6.0, "hi": 8.0})],
        declared_scope=[CONDITION_KEY_PH])
    assert per_key(ph)[CONDITION_KEY_PH]["status"] == "satisfied"


# ============================================================ R5-04
# 恢复/审核入口核快照一致性与内容身份(conditions_probe:
# snapshot_from_dict_conflict_summary_and_flag_tamper)


def _historical_child(old_required="anaerobic"):
    """复审探针场景:sA:p0 有氧事实与旧 essential <old_required>(默认
    冲突);显式转 sB:p1 后新无氧必要要求满足 —— 正常阶段转换。"""
    facts = [
        f(CONDITION_KEY_OXYGEN, "aerobic", phase_id="p0",
          subject_scenario_ref="sA"),
        f(CONDITION_KEY_OXYGEN, "anaerobic", phase_id="p1",
          subject_scenario_ref="sB")]
    parent = build_path_context(
        condition_facts=facts, phase_id="p0", scenario_ref="sA",
        accumulated_requirements=[r(CONDITION_KEY_OXYGEN, old_required)],
        assessment_scope=[CONDITION_KEY_OXYGEN])
    return derive_child_context(
        parent, step_requirements=[r(CONDITION_KEY_OXYGEN, "anaerobic")],
        scenario_transition={"new_phase_id": "p1", "new_scenario_ref": "sB",
                             "source_ref": "user:synthetic_transition"})


def test_r5_04_snapshot_summary_tamper_rejected() -> None:
    """复审反例:合法载荷 to_dict 后仅改 phase_history[0].
    environment_fit='compatible'(旧逐行 conflict 仍在)⇒ from_dict
    结构化拒绝(v5 回读后路线洗绿 compatible → verified → R6)。"""
    child = _historical_child("anaerobic")
    assert child.route_assessment().environment_fit == "conflict"
    raw = child.to_dict()
    raw["phase_history"][0]["environment_fit"] = "compatible"
    with pytest.raises(ConditionContractError) as ei:
        PathContext.from_dict(raw)
    assert ei.value.detail.get("kind") == "context_snapshot_inconsistent"
    assert ei.value.detail.get("check") == "fit_conflict_mismatch"


def test_r5_04_gate_flag_tamper_rejected() -> None:
    """复审反例:仅改 has_gate_requirements=False ⇒ 拒(旗标须与必要
    行集合同源;篡改不能跳过必要评估把旧冲突从消费中洗掉)。"""
    child = _historical_child("anaerobic")
    raw = child.to_dict()
    raw["phase_history"][0]["has_gate_requirements"] = False
    with pytest.raises(ConditionContractError) as ei:
        PathContext.from_dict(raw)
    assert ei.value.detail.get("kind") == "context_snapshot_inconsistent"
    assert ei.value.detail.get("check") == "gate_flag_mismatch"


def test_r5_04_legal_roundtrip_idempotent() -> None:
    """正控制:合法载荷 to_dict→from_dict 幂等 —— 同 context_id、
    路线结论不变、二次往返载荷一致;依赖对象(从 resolution_log
    重推导)与空快照历史同样往返通过。"""
    child = _historical_child("anaerobic")
    raw = child.to_dict()
    restored = PathContext.from_dict(raw)
    assert restored.context_id == child.context_id
    assert restored.route_assessment().environment_fit == "conflict"
    assert restored.to_dict() == raw  # 幂等:再往返载荷一致
    hyp = _hyp([r(CONDITION_KEY_OXYGEN, "anaerobic")])
    r1 = assess_candidate_conditions(child, hyp)
    r2 = assess_candidate_conditions(restored, hyp)
    assert r2.environment_fit == r1.environment_fit == "conflict"
    # 依赖对象往返进内容身份(解析轨迹重推导 ⇒ 同 id)
    dep = build_dependency(kind="cosubstrate_supply",
                           statement="supplies:A:B")
    resolved = resolve_dependency(dep, new_evidence=["src:initial"],
                                  resolution="supported",
                                  support_axis="initial_supply")
    root = build_path_context(
        condition_facts=[f(CONDITION_KEY_OXYGEN, "aerobic")],
        assessment_scope=[CONDITION_KEY_OXYGEN],
        dependencies=[resolved])
    restored_dep = PathContext.from_dict(root.to_dict())
    assert restored_dep.context_id == root.context_id
    assert restored_dep.dependency_states() == root.dependency_states()
    # 空快照历史(父无必要要求)同样合法往返,不误拒
    empty_parent = build_path_context(
        condition_facts=[f(CONDITION_KEY_OXYGEN, "aerobic")],
        assessment_scope=[CONDITION_KEY_OXYGEN])
    empty_child = derive_child_context(
        empty_parent, scenario_transition={"new_phase_id": "p1",
                                           "source_ref": "user:t"})
    assert PathContext.from_dict(
        empty_child.to_dict()).context_id == empty_child.context_id
    # 全部满足但声明 scope 为空的历史合法记录 unknown(单向矛盾判定,
    # 不误拒)
    scopeless = build_path_context(
        condition_facts=[f(CONDITION_KEY_OXYGEN, "aerobic")],
        accumulated_requirements=[r(CONDITION_KEY_OXYGEN, "aerobic")],
        assessment_scope=[])
    scopeless_child = derive_child_context(
        scopeless, scenario_transition={"new_phase_id": "p1",
                                        "source_ref": "user:t"})
    snap = scopeless_child.phase_history[0]
    assert snap["environment_fit"] == "unknown"  # scope 空 ⇒ 合法 unknown
    assert PathContext.from_dict(
        scopeless_child.to_dict()).context_id == scopeless_child.context_id


def test_r5_04_inplace_tampered_phase_history_rejected_at_audit() -> None:
    """复审反例:audit_hypothesis 传入就地篡改过 phase_history 的直接
    context 对象 ⇒ validate_context_object 拒(内存对象摘要被改,
    消费入口不再信任)。"""
    hyp = _hyp([r(CONDITION_KEY_OXYGEN, "anaerobic")])
    child = _historical_child("anaerobic")
    child.phase_history[0]["environment_fit"] = "compatible"
    with pytest.raises(ConditionContractError) as ei:
        audit_hypothesis(hyp, states=STATE_MAP, context=child,
                         center_evidence=CENTER)
    assert ei.value.detail.get("kind") == "context_snapshot_inconsistent"
    # 旗标篡改同样拒绝
    child2 = _historical_child("anaerobic")
    child2.phase_history[0]["has_gate_requirements"] = False
    with pytest.raises(ConditionContractError) as ei2:
        audit_hypothesis(hyp, states=STATE_MAP, context=child2,
                         center_evidence=CENTER)
    assert ei2.value.detail.get("kind") == "context_snapshot_inconsistent"
    assert ei2.value.detail.get("check") == "gate_flag_mismatch"


def test_r5_04_fact_tamper_kept_context_id_rejected() -> None:
    """内容身份:改事实(载荷或就地)而不改 context_id ⇒ 拒
    (context_content_identity_mismatch;篡改任何语义字段保留原身份,
    不是同 hash 漏项问题)。"""
    child = _historical_child("anaerobic")
    raw = child.to_dict()
    raw["condition_facts"][0]["value"] = "anaerobic"  # 原 aerobic
    with pytest.raises(ConditionContractError) as ei:
        PathContext.from_dict(raw)
    assert ei.value.detail.get("kind") == "context_content_identity_mismatch"
    # 直接对象:就地新增事实而 context_id 不变 ⇒ audit 入口拒
    ctx_obj = build_path_context(
        condition_facts=[f(CONDITION_KEY_OXYGEN, "aerobic")],
        phase_id="p0", scenario_ref="s",
        assessment_scope=[CONDITION_KEY_OXYGEN])
    ctx_obj.condition_facts.append(
        f(CONDITION_KEY_OXYGEN, "anaerobic", phase_id="p1"))
    hyp = _hyp([r(CONDITION_KEY_OXYGEN, "aerobic")])
    with pytest.raises(ConditionContractError) as ei2:
        audit_hypothesis(hyp, states=STATE_MAP, context=ctx_obj,
                         center_evidence=CENTER)
    assert ei2.value.detail.get("kind") == "context_content_identity_mismatch"


def test_r5_04_normal_phase_transition_conflict_to_defer() -> None:
    """正控制:正常 sA:p0→sB:p1 阶段转换 —— 旧边记录值(快照
    conflict)不被当前无氧事实重评洗掉,路线 conflict ⇒ audit
    violated ⇒ defer;当前步 compatible 与路线 conflict 双层并列。"""
    child = _historical_child("anaerobic")
    hyp = _hyp([r(CONDITION_KEY_OXYGEN, "anaerobic")])
    audit = audit_hypothesis(hyp, states=STATE_MAP, context=child,
                             center_evidence=CENTER)
    cond = next(c for c in audit.checks if c.name == CHECK_CONDITION_CHECK)
    assert cond.status == "violated"
    disposition, _ = decide_admission(audit)
    assert disposition == "defer"
    result = assess_candidate_conditions(child, hyp)
    assert result.detail["current_step_environment_fit"] == "compatible"
    assert result.detail["route_environment_fit"] == "conflict"
    old_rows = [p for p in result.per_requirement
                if p.get("route_edge_source") == "phase_history:p0/sA"]
    assert old_rows and all(p["status"] == "conflict" for p in old_rows)


# ============================================================ P2(§4-2)
# 环诊断按对应有效轴消费(conditions_probe:
# axis_controls_and_cross_axis_diagnostic)


def _cycle_dep(statement):
    return build_dependency(kind="cosubstrate_supply", statement=statement)


def _probe_axis_dependencies():
    """探针的轴控制链(与 conditions_probe.py 同构)。"""
    a, b = (_cycle_dep("supplies:A:B"), _cycle_dep("supplies:B:A"))
    regen_a = resolve_dependency(
        a, new_evidence=["src:regen"], resolution="supported",
        support_axis="regeneration")
    regen_b = resolve_dependency(
        b, new_evidence=["src:regen_b"], resolution="supported",
        support_axis="regeneration")
    initial = resolve_dependency(
        regen_a, new_evidence=["src:initial"], resolution="supported",
        support_axis="initial_supply")
    initial_no = resolve_dependency(
        initial, new_evidence=["src:initial_no"], resolution="contradicted",
        support_axis="initial_supply")
    later = resolve_dependency(
        initial_no, new_evidence=["src:later_regen"], resolution="supported",
        support_axis="regeneration")
    restored = resolve_dependency(
        later, new_evidence=["src:new_initial"], resolution="supported",
        support_axis="initial_supply")
    reaction_no = resolve_dependency(
        initial, new_evidence=["src:reaction_no"], resolution="contradicted",
        support_axis="reaction")
    return {"regen_a": regen_a, "regen_b": regen_b, "initial": initial,
            "later": later, "restored": restored, "reaction_no": reaction_no}


def test_p2_initial_supported_reaction_contradicted_split() -> None:
    """交叉轴案例 1:初始轴 supported + reaction 轴 contradicted(总体
    contradicted)⇒ 环 NOT in unresolved_initial_supply(启动轴仍在,
    不误报启动未知)、IS in unsupported_relation_cycles(reaction 轴
    被反驳,关系不成立)。v5 以总体 status 同时判两种语义 ⇒ 误报
    启动未知。"""
    d = _probe_axis_dependencies()
    result = detect_circular_dependencies(
        [d["reaction_no"], d["regen_b"]])
    assert result["unresolved_initial_supply"] == []
    assert result["unsupported_relation_cycles"] == [["A", "B"]]


def test_p2_initial_contradicted_later_regen_split() -> None:
    """交叉轴案例 2:initial 轴 contradicted + regeneration 轴
    supported(总体 contradicted)⇒ IS in unresolved_initial_supply
    (启动轴当前无支持,不被再生洗掉)、NOT in unsupported_relation_
    cycles(关系轴成立,不混入关系不支持)。v5 混入关系不支持。"""
    d = _probe_axis_dependencies()
    result = detect_circular_dependencies([d["later"], d["regen_b"]])
    assert result["unresolved_initial_supply"] == [["A", "B"]]
    assert result["unsupported_relation_cycles"] == []


def test_p2_regen_only_unresolved_not_relation() -> None:
    """控制:仅再生支持 ⇒ in unresolved_initial_supply、not in
    unsupported_relation_cycles(再生是关系支持,不解决启动)。"""
    d = _probe_axis_dependencies()
    result = detect_circular_dependencies([d["regen_a"], d["regen_b"]])
    assert result["unresolved_initial_supply"] == [["A", "B"]]
    assert result["unsupported_relation_cycles"] == []


def test_p2_double_supported_positive_control() -> None:
    """正控制:初始+再生双支持(以及反驳后按轴恢复)⇒ 两者皆无。"""
    d = _probe_axis_dependencies()
    for dep in (d["initial"], d["restored"]):
        result = detect_circular_dependencies([dep, d["regen_b"]])
        assert result["unresolved_initial_supply"] == []
        assert result["unsupported_relation_cycles"] == []


def test_p2_audit_consumes_overall_status_kept() -> None:
    """audit 侧 provenance_dependency 检查仍消费 dep.status(总体):
    reaction 轴被反驳 ⇒ 总体 contradicted ⇒ unresolved ⇒ unknown ⇒
    retain(不可 R6,方向正确);总体 supported 的正控制不被环诊断
    阻断。"""
    d = _probe_axis_dependencies()
    reqs = [r(CONDITION_KEY_OXYGEN, "aerobic")]
    ctx_contradicted = build_path_context(
        condition_facts=[f(CONDITION_KEY_OXYGEN, "aerobic")],
        assessment_scope=[CONDITION_KEY_OXYGEN],
        dependencies=[d["reaction_no"], d["regen_b"]])
    cond, disposition = _audit(ctx_contradicted, reqs)
    assert cond.status == "verified"
    assert disposition != "expand"  # 总体 contradicted ⇒ 不可 R6
    ctx_supported = build_path_context(
        condition_facts=[f(CONDITION_KEY_OXYGEN, "aerobic")],
        assessment_scope=[CONDITION_KEY_OXYGEN],
        dependencies=[d["initial"], d["regen_b"]])
    cond2, disposition2 = _audit(ctx_supported, reqs)
    assert cond2.status == "verified"
    assert disposition2 == "expand"
