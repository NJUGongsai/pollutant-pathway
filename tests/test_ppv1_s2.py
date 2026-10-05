"""S2 上下文/诊断/审计测试(规则级夹具;模型 scripted/off,无金标)。

覆盖验收矩阵:
- C01 无条件、没列供体、pH 部分相交 → unknown;没列供体 ≠ absent;
- C02 明确无氧 vs 有来源的必需 O₂ → conflict;不在此场景展开(defer);
- C03 分支上下文与显式阶段切换:两分支不污染;转换须有来源;
- C04 文献有氧、当前场景无条件 → 当前氧状态仍未知;
- C05 请求 condition_compatible、一条必要条件未知 → assessed=possible;
- C06 结构有效、活动 gate 接受、条件/账目未知 → retain_conditional
  (admission 策略级,不自动拒绝);
- D01 合法编辑但偏离供体预期 → strict 识别偏离;center 分轴;
- D02 对称等价/映射缺失/立体未知 → 等价不误拒;受影响轴未知;
- D03 参与物/系数缺失 vs 完整人工配平:前者 full_balance 未知;
  后者只核命名账目(biological_support 不冒充);
- H01 结构无法解析 → violated;后续项 unknown/prerequisite_failed;
- H04 共底物循环(依赖诊断部分):未知 → unresolved_initial_supply。
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pathway_v43.pollutant.audit import (  # noqa: E402
    ADMISSION_DEFER,
    ADMISSION_REJECT,
    ADMISSION_RETAIN_CONDITIONAL,
    ADMISSION_EXPAND,
    AdmissionPolicy,
    CHECK_CONDITION_CHECK,
    CHECK_ELEMENT_ACCOUNTING,
    CHECK_FORMAL_CHARGE_ACCOUNTING,
    CHECK_STRUCTURE_PARSE_VALENCE,
    CHECK_UNKNOWN,
    CHECK_VERIFIED,
    CHECK_VIOLATED,
    PREREQUISITE_FAILED,
    audit_hypothesis,
    check_edit_against_donor,
    decide_admission,
)
from pathway_v43.pollutant.chemstate import (  # noqa: E402
    STRUCTURE_ORIGIN_RAW_INPUT,
    STRUCTURE_ORIGIN_SOURCE_PRODUCT,
    build_chemical_state,
)
from pathway_v43.pollutant.hypothesis import (  # noqa: E402
    COEFFICIENT_KNOWN,
    COEFFICIENT_UNKNOWN,
    PARTICIPANT_LIST_DECLARED_COMPLETE,
    PARTICIPANT_LIST_PARTIAL,
    PARTICIPANT_ROLE_COPRODUCT,
    PARTICIPANT_ROLE_COSUBSTRATE,
    PARTICIPANT_ROLE_PRIMARY_SUBSTRATE,
    PARTICIPANT_ROLE_PRINCIPAL_PRODUCT,
    PARTICIPANT_SIDE_PRODUCT,
    PARTICIPANT_SIDE_REACTANT,
    Participant,
    build_hypothesis,
)
from pathway_v43.pollutant.path_context import (  # noqa: E402
    CONDITION_KEY_ELECTRON_DONOR,
    CONDITION_KEY_OXYGEN,
    CONDITION_KEY_PH,
    CONDITION_KEY_TEMPERATURE,
    DEPENDENCY_SUPPORTED,
    DEPENDENCY_UNRESOLVED,
    FACT_ORIGIN_CURATED_SOURCE,
    FACT_ORIGIN_SCENARIO_TRANSITION,
    FACT_STATUS_KNOWN_ABSENT,
    FACT_STATUS_KNOWN_PRESENT,
    REQUESTED_SCOPE_CONDITION_COMPATIBLE,
    REQUESTED_SCOPE_POSSIBLE,
    build_condition_fact,
    build_dependency,
    build_path_context,
    build_requirement,
    derive_child_context,
    detect_circular_dependencies,
    resolve_dependency,
)
from pathway_v43.pollutant.pool_audit import (  # noqa: E402
    INPUT_PREVIEW_DIAGNOSTIC,
    INPUT_PREVIEW_OFF,
    PoolAuditError,
    build_pool_audit,
    dedupe_pool,
    order_pool,
    record_pool_stage,
    run_input_preview,
)
from pathway_v43.pollutant.substrate_profile import (  # noqa: E402
    build_substrate_profile,
)

ETHANOL = "CCO"
ACETALDEHYDE = "CC=O"
ACETIC_ACID = "CC(=O)O"
O2 = "O=O"
WATER = "O"


def _pstate(smiles, origin=STRUCTURE_ORIGIN_SOURCE_PRODUCT):
    return build_chemical_state(smiles, origin)


def _sub(ref, coefficient=None):
    return Participant(state_ref=ref, side=PARTICIPANT_SIDE_REACTANT,
                       role=PARTICIPANT_ROLE_PRIMARY_SUBSTRATE,
                       coefficient=coefficient,
                       coefficient_status=(COEFFICIENT_KNOWN
                                           if coefficient is not None
                                           else COEFFICIENT_UNKNOWN))


def _prod(ref, coefficient=None, role=PARTICIPANT_ROLE_PRINCIPAL_PRODUCT):
    return Participant(state_ref=ref, side=PARTICIPANT_SIDE_PRODUCT,
                       role=role, coefficient=coefficient,
                       coefficient_status=(COEFFICIENT_KNOWN
                                           if coefficient is not None
                                           else COEFFICIENT_UNKNOWN))


# ---------------------------------------------------------------- C01–C05


def _ctx(facts, requirements, scope=("oxygen_regime", "pH",
                                      "electron_donor"),
         requested=REQUESTED_SCOPE_CONDITION_COMPATIBLE):
    return build_path_context(
        requested_scope=requested,
        condition_facts=facts,
        accumulated_requirements=requirements,
        assessment_scope=list(scope),
    )


def test_c01_no_facts_unlisted_donor_partial_ph_unknown() -> None:
    """无条件、没列供体、pH 部分相交 → unknown;没列供体不判 absent。"""
    facts = [build_condition_fact(
        key=CONDITION_KEY_PH, value=6.0, unit="",
        status=FACT_STATUS_KNOWN_PRESENT)]
    reqs = [build_requirement(
        key=CONDITION_KEY_PH, level="essential",
        value={"lo": 5.5, "hi": 8.0}),
        build_requirement(
            key=CONDITION_KEY_ELECTRON_DONOR, level="essential",
            value="H2O")]
    ctx = _ctx(facts, reqs)
    assessment = ctx.assessed_scope and None  # noqa: F632
    from pathway_v43.pollutant.path_context import \
        aggregate_environment_fit

    result = aggregate_environment_fit(
        facts=facts, requirements=reqs,
        declared_scope=["pH", "electron_donor", "oxygen_regime"])
    assert result.environment_fit == "unknown"
    per = {p["key"]: p for p in result.per_requirement}
    # pH 点值 6.0 在 [5.5, 8.0] → 满足
    assert per["pH"]["status"] == "satisfied"
    # 供体:没有 fact → unknown(未列出 ≠ known_absent,不判 conflict)
    assert per["electron_donor"]["status"] == "unknown"
    assert result.assessed_scope == "possible"


def test_c02_anaerobic_vs_required_o2_conflict() -> None:
    """明确无氧 vs 有来源的必需 O₂ → conflict;admission=defer(blocked)。"""
    facts = [build_condition_fact(
        key=CONDITION_KEY_OXYGEN, value="anaerobic",
        status=FACT_STATUS_KNOWN_PRESENT,
        origin=FACT_ORIGIN_CURATED_SOURCE, source_ref="user:scenario")]
    reqs = [build_requirement(
        key=CONDITION_KEY_OXYGEN, level="essential", value="aerobic",
        source_refs=["src:reaction123"])]
    ctx = _ctx(facts, reqs)
    assert ctx.assessed_scope == "conflicted"
    # admission 层:当前场景有来源必要条件冲突 → defer(不在此场景展开)
    sub = _pstate(ETHANOL, STRUCTURE_ORIGIN_RAW_INPUT)
    hyp = build_hypothesis(
        parent_path_id="p1", substrate_state_ref=sub.state_id,
        participants=[_sub(sub.state_id), _prod(_pstate(O2).state_id)],
        participant_list_status=PARTICIPANT_LIST_PARTIAL,
        step_scope="net_reaction",
        requirements=[{"key": CONDITION_KEY_OXYGEN, "level": "essential",
                       "value": "aerobic",
                       "source_refs": ["src:reaction123"]}],
        origin_group_key="o2-requiring")
    audit = audit_hypothesis(
        hyp, states={s.state_id: s for s in (
            sub, _pstate(ETHANOL), _pstate(O2))}, context=ctx)
    disposition, reasons = decide_admission(
        audit, gate_decisions={"gate_direction_source": {"ok": True}})
    assert disposition == ADMISSION_DEFER
    assert any("current_scenario_conflict" in r for r in reasons)


def test_c03_branches_isolated_and_scenario_transition_sourced() -> None:
    """两分支不互相污染;阶段切换须有来源,不追改此前步骤。"""
    root = build_path_context(
        requested_scope=REQUESTED_SCOPE_POSSIBLE,
        condition_facts=[build_condition_fact(
            key=CONDITION_KEY_OXYGEN, value="aerobic",
            status=FACT_STATUS_KNOWN_PRESENT)],
        accumulated_requirements=[])
    # 分支 A:加必需 O2;分支 B:加 pH 范围
    branch_a = derive_child_context(root, step_requirements=[
        build_requirement(key=CONDITION_KEY_OXYGEN, level="essential",
                          value="aerobic")])
    branch_b = derive_child_context(root, step_requirements=[
        build_requirement(key=CONDITION_KEY_PH, level="essential",
                          value={"lo": 5.0, "hi": 9.0})])
    # A 的要求没有泄进 B(分支隔离)
    keys_a = {r.key for r in branch_a.accumulated_requirements}
    keys_b = {r.key for r in branch_b.accumulated_requirements}
    assert CONDITION_KEY_OXYGEN in keys_a and CONDITION_KEY_OXYGEN not in \
        keys_b
    assert CONDITION_KEY_PH in keys_b and CONDITION_KEY_PH not in keys_a
    # 父上下文不可变(未被子上下文修改)
    assert root.accumulated_requirements == []
    # 阶段转换须有来源
    with pytest.raises(Exception, match="必须有来源"):
        derive_child_context(root, scenario_transition={
            "new_phase_id": "phase-1"})
    ok = derive_child_context(root, scenario_transition={
        "new_phase_id": "phase-1", "source_ref": "user:phase-change"})
    assert ok.phase_id == "phase-1"
    assert ok.parent_context_ref == root.context_id
    # 转换只影响后续:父(此前步骤)的 phase 不变
    assert root.phase_id == "phase-0"


def test_c03_same_scenario_requirement_conflict_recorded() -> None:
    root = build_path_context(accumulated_requirements=[
        build_requirement(key=CONDITION_KEY_TEMPERATURE, level="essential",
                          value={"lo": 20, "hi": 30})])
    child = derive_child_context(root, step_requirements=[
        build_requirement(key=CONDITION_KEY_TEMPERATURE, level="essential",
                          value={"lo": 40, "hi": 50})])
    assert any("requirement_conflict_at_same_scenario" in a
               for a in child.assumptions)


def test_c04_literature_oxygen_not_current_fact() -> None:
    """文献有氧(观察条件参考),当前场景无条件 → 当前氧状态仍 unknown。"""
    facts = []  # 当前场景无条件
    reqs = [build_requirement(
        key=CONDITION_KEY_OXYGEN, level="essential", value="aerobic",
        basis="observed_condition_reference",
        source_refs=["doi:10.x/literature"],
        observed_source_conditions=[{
            "note": "来源报告该反应在好氧条件被观察",
            "source_ref": "doi:10.x/literature"}])]
    from pathway_v43.pollutant.path_context import \
        aggregate_environment_fit

    result = aggregate_environment_fit(
        facts=facts, requirements=reqs, declared_scope=["oxygen_regime"])
    per = {p["key"]: p for p in result.per_requirement}
    # 观察条件参考不参与门禁;当前事实缺失 → 聚合 unknown
    assert result.environment_fit == "unknown"
    assert per[CONDITION_KEY_OXYGEN]["status"] == "not_applicable"
    # requirement 的 observed_source_conditions 保留(不丢失文献信息)
    assert reqs[0].observed_source_conditions[0]["source_ref"] == \
        "doi:10.x/literature"


def test_c05_requested_compatible_one_unknown_assessed_possible() -> None:
    facts = [build_condition_fact(
        key=CONDITION_KEY_OXYGEN, value="aerobic",
        status=FACT_STATUS_KNOWN_PRESENT)]
    reqs = [build_requirement(key=CONDITION_KEY_OXYGEN, level="essential",
                              value="aerobic"),
            build_requirement(key=CONDITION_KEY_PH, level="essential",
                              value={"lo": 6.0, "hi": 8.0})]
    ctx = _ctx(facts, reqs, requested=REQUESTED_SCOPE_CONDITION_COMPATIBLE)
    # pH 无 fact → 未知;assessed_scope 派生为 possible,不继承请求标签
    assert ctx.requested_scope == REQUESTED_SCOPE_CONDITION_COMPATIBLE
    assert ctx.assessed_scope == "possible"


def test_all_satisfied_within_declared_scope_compatible() -> None:
    facts = [
        build_condition_fact(key=CONDITION_KEY_OXYGEN, value="aerobic",
                             status=FACT_STATUS_KNOWN_PRESENT),
        build_condition_fact(key=CONDITION_KEY_PH, value=7.0,
                             status=FACT_STATUS_KNOWN_PRESENT),
    ]
    reqs = [
        build_requirement(key=CONDITION_KEY_OXYGEN, level="essential",
                          value="aerobic"),
        build_requirement(key=CONDITION_KEY_PH, level="essential",
                          value={"lo": 6.0, "hi": 8.0}),
    ]
    ctx = _ctx(facts, reqs)
    assert ctx.assessed_scope == "condition_compatible"


def test_empty_requirements_not_auto_compatible() -> None:
    ctx = _ctx(facts=[], requirements=[])
    assert ctx.assessed_scope == "possible"  # 空要求列表 → unknown


def test_condition_key_validation_fail_closed() -> None:
    from pathway_v43.pollutant.path_context import ConditionContractError

    with pytest.raises(ConditionContractError, match="未知条件键"):
        build_condition_fact(key="pressure_atm", value=1.0,
                             status=FACT_STATUS_KNOWN_PRESENT)
    with pytest.raises(ConditionContractError):
        build_condition_fact(key=CONDITION_KEY_OXYGEN, value="very_oxygenic",
                             status=FACT_STATUS_KNOWN_PRESENT)


# ---------------------------------------------------------------- H04(S2 部分)


def test_h04_circular_cosubstrate_dependency_diagnosis() -> None:
    a_b = build_dependency(kind="cosubstrate_supply",
                           statement="supplies:speciesA:speciesB",
                           introduced_at_hypothesis_id="h1")
    b_a = build_dependency(kind="cosubstrate_supply",
                           statement="supplies:speciesB:speciesA",
                           introduced_at_hypothesis_id="h2")
    result = detect_circular_dependencies([a_b, b_a])
    assert result["cycles"] == [["speciesA", "speciesB"]]
    # 未知(无启动支持)→ unresolved_initial_supply;不称化学不可能
    assert result["unresolved_initial_supply"] == [
        ["speciesA", "speciesB"]]
    assert "不称化学不可能" in result["note"]
    # 有启动/再生支持 → 不阻断
    resolved = resolve_dependency(
        a_b, new_evidence=["src:inoculation"], resolution="supported",
        note="接种提供初始供给")
    result2 = detect_circular_dependencies([resolved, b_a])
    assert result2["cycles"] == [["speciesA", "speciesB"]]
    assert result2["unresolved_initial_supply"] == [
        ["speciesA", "speciesB"]]  # b_a 仍未知 → 依显式策略处理
    both = resolve_dependency(
        b_a, new_evidence=["src:regeneration"], resolution="supported")
    result3 = detect_circular_dependencies([resolved, both])
    assert result3["unresolved_initial_supply"] == []


def test_dependency_resolution_needs_evidence_and_keeps_log() -> None:
    dep = build_dependency(kind="mechanism", statement="假设水解酶催化")
    from pathway_v43.pollutant.path_context import ConditionContractError

    with pytest.raises(ConditionContractError, match="来源新证据"):
        resolve_dependency(dep, new_evidence=[], resolution="supported")
    resolved = resolve_dependency(
        dep, new_evidence=["src:evidence"], resolution="supported",
        note="来源新证据")
    assert resolved.status == DEPENDENCY_SUPPORTED
    assert resolved.resolution_log[0]["evidence"] == ["src:evidence"]


# ---------------------------------------------------------------- H01/C06/D03 审计


def _balanced_hypothesis(states):
    """配平占位反应:2 C2H6O + O2 → 2 C2H4O2(元素账平衡)。"""
    sub = states[ETHANOL]
    o2 = states[O2]
    acetic = states[ACETIC_ACID]
    return build_hypothesis(
        parent_path_id="p1", substrate_state_ref=sub.state_id,
        participants=[
            _sub(sub.state_id, coefficient=2),
            Participant(state_ref=o2.state_id,
                        side=PARTICIPANT_SIDE_REACTANT,
                        role=PARTICIPANT_ROLE_COSUBSTRATE,
                        coefficient=1, coefficient_status=COEFFICIENT_KNOWN),
            _prod(acetic.state_id, coefficient=2),
        ],
        participant_list_status=PARTICIPANT_LIST_DECLARED_COMPLETE,
        step_scope="net_reaction", origin_group_key="balanced-oxidation",
        transformation_signature_status="verified",
        step_scope_evidence_refs=["src:balanced-example"])


def _std_states():
    return {s: _pstate(s) for s in (ETHANOL, O2, ACETIC_ACID, WATER)}


def test_balanced_reaction_element_and_charge_verified() -> None:
    states = _std_states()
    hyp = _balanced_hypothesis(states)
    audit = audit_hypothesis(
        hyp, states={s.state_id: s for s in states.values()})
    assert audit.check_status(CHECK_STRUCTURE_PARSE_VALENCE) == \
        CHECK_VERIFIED
    assert audit.check_status(CHECK_ELEMENT_ACCOUNTING) == CHECK_VERIFIED
    assert audit.check_status(CHECK_FORMAL_CHARGE_ACCOUNTING) == \
        CHECK_VERIFIED
    assert audit.participant_accounting_status == "full"
    # 元素/电荷核实 ≠ 生物支持核实(分轴,不冒充)
    assert audit.biological_support_status == "unknown"


def test_h01_unparseable_prerequisite_failed_not_run() -> None:
    sub = _pstate(ETHANOL, STRUCTURE_ORIGIN_RAW_INPUT)
    # 产物结构非法:states 里给一个无法解析的"状态"(用 raw 构建失败,
    # 换成手工坏 states:smiles_isomeric 为空 → parse violated)
    from pathway_v43.pollutant.chemstate import \
        build_chemical_state_from_cn_only

    bad = build_chemical_state_from_cn_only("not-a-real-structure-x")
    hyp = build_hypothesis(
        parent_path_id="p1", substrate_state_ref=sub.state_id,
        participants=[_sub(sub.state_id), _prod(bad.state_id)],
        participant_list_status=PARTICIPANT_LIST_PARTIAL,
        step_scope="net_reaction", origin_group_key="bad-structure")
    audit = audit_hypothesis(hyp, states={sub.state_id: sub,
                                          bad.state_id: bad})
    assert audit.check_status(CHECK_STRUCTURE_PARSE_VALENCE) == \
        CHECK_VIOLATED
    # 依赖解析的后续项:unknown + prerequisite_failed_not_run(不伪装通过)
    for name in (CHECK_ELEMENT_ACCOUNTING,
                 CHECK_FORMAL_CHARGE_ACCOUNTING):
        check = next(c for c in audit.checks if c.name == name)
        assert check.status == CHECK_UNKNOWN
        assert check.reason_code == PREREQUISITE_FAILED
    # admission:结构非法 → reject
    disposition, _ = decide_admission(audit, gate_decisions={
        "gate_direction_source": {"ok": True}})
    assert disposition == ADMISSION_REJECT


def test_h01_raw_unparseable_string_fails_state_construction() -> None:
    """SMILES 无法解析:状态构建 fail-closed(记结构失败,不猜)。"""
    from pathway_v43.pollutant.chemstate import ChemicalStateError

    with pytest.raises(ChemicalStateError):
        build_chemical_state("C1CC", STRUCTURE_ORIGIN_SOURCE_PRODUCT)


def test_d03_partial_participants_full_balance_unknown() -> None:
    states = _std_states()
    # 参与物/系数缺失:partial 列表
    hyp = build_hypothesis(
        parent_path_id="p1",
        substrate_state_ref=states[ETHANOL].state_id,
        participants=[_sub(states[ETHANOL].state_id),
                      _prod(states[ACETIC_ACID].state_id)],
        participant_list_status=PARTICIPANT_LIST_PARTIAL,
        step_scope="net_reaction", origin_group_key="partial")
    audit = audit_hypothesis(
        hyp, states={s.state_id: s for s in states.values()})
    assert audit.check_status(CHECK_ELEMENT_ACCOUNTING) == CHECK_UNKNOWN
    assert audit.check_status(CHECK_FORMAL_CHARGE_ACCOUNTING) == \
        CHECK_UNKNOWN
    assert audit.participant_accounting_status == "partial"
    # 完整人工配平(D03 下半):只核命名账目;biological 不冒充酶可行
    hyp2 = _balanced_hypothesis(states)
    audit2 = audit_hypothesis(
        hyp2, states={s.state_id: s for s in states.values()})
    assert audit2.participant_accounting_status == "full"
    assert audit2.biological_support_status == "unknown"


def test_declared_complete_but_unknown_coeff_not_verified() -> None:
    """声明完整但系数 unknown:完整度 unknown(declared ≠ 程序验算)。"""
    states = _std_states()
    hyp = build_hypothesis(
        parent_path_id="p1",
        substrate_state_ref=states[ETHANOL].state_id,
        participants=[_sub(states[ETHANOL].state_id),
                      _prod(states[ACETIC_ACID].state_id)],
        participant_list_status=PARTICIPANT_LIST_DECLARED_COMPLETE,
        step_scope="net_reaction", origin_group_key="declared-unknown-coeff")
    audit = audit_hypothesis(
        hyp, states={s.state_id: s for s in states.values()})
    check = next(c for c in audit.checks
                 if c.name == "participant_completeness")
    assert check.status == CHECK_UNKNOWN
    assert "coefficients_unknown" in check.reason_code


def test_c06_structure_valid_gate_ok_unknowns_retain_conditional() -> None:
    """C06 admission 策略级:结构有效、活动 gate 接受、条件/账目未知
    → retain_conditional(可有界探索,继承未知依赖,不自动拒绝)。"""
    states = _std_states()
    hyp = build_hypothesis(
        parent_path_id="p1",
        substrate_state_ref=states[ETHANOL].state_id,
        participants=[_sub(states[ETHANOL].state_id),
                      _prod(states[ACETIC_ACID].state_id)],
        participant_list_status=PARTICIPANT_LIST_PARTIAL,
        step_scope="net_reaction", origin_group_key="c06")
    # 无上下文:条件检查 not_applicable;账目 unknown
    audit = audit_hypothesis(
        hyp, states={s.state_id: s for s in states.values()},
        unresolved_dependency_ids=["dep:upstream-model-assumption"])
    disposition, reasons = decide_admission(
        audit, gate_decisions={"gate_direction_source": {"ok": True},
                               "gate_recorded_eligibility": {"ok": True}})
    assert disposition == ADMISSION_RETAIN_CONDITIONAL
    assert any("unknown_checks_present" in r for r in reasons)
    assert any("不自动拒绝" in r for r in reasons)
    # 未知依赖沿途保留(审计记录引用)
    check = next(c for c in audit.checks
                 if c.name == "provenance_dependency")
    assert "dep:upstream-model-assumption" in check.evidence_refs


def test_admission_policy_decision_table_explicit() -> None:
    """P0-4:决策表显式、有序;policy JSON 往返;未知版本 fail-closed。"""
    policy = AdmissionPolicy()
    d = policy.to_dict()
    rules = d["rules"]
    assert [r["rule_id"] for r in rules] == ["R1", "R2", "R3", "R4",
                                             "R5", "R6"]
    assert [r["disposition"] for r in rules] == [
        "reject", "reject", "defer", "defer", "retain_conditional",
        "expand"]
    restored = AdmissionPolicy.from_dict(d)
    assert restored.to_dict() == d
    from pathway_v43.pollutant.audit import AuditContractError

    with pytest.raises(AuditContractError):
        AdmissionPolicy.from_dict({"policy_version": "bogus"})
    with pytest.raises(AuditContractError, match="未知门禁"):
        AdmissionPolicy.from_dict({
            "policy_version": "ppv1-admission-1",
            "reject_gates": ["gate_not_reviewed"]})


def test_admission_gate_rejected_only_for_declared_gates() -> None:
    """活动门禁显式拒绝 → reject;但未列入名单的门不触发(不暗改)。"""
    states = _std_states()
    hyp = build_hypothesis(
        parent_path_id="p1",
        substrate_state_ref=states[ETHANOL].state_id,
        participants=[_sub(states[ETHANOL].state_id),
                      _prod(states[ACETIC_ACID].state_id)],
        participant_list_status=PARTICIPANT_LIST_DECLARED_COMPLETE,
        step_scope="net_reaction", origin_group_key="gate-check")
    audit = audit_hypothesis(
        hyp, states={s.state_id: s for s in states.values()})
    # 名单内的门违规 → reject
    d, _ = decide_admission(audit, gate_decisions={
        "gate_direction_source": {"ok": False, "reason": "方向错误"}})
    assert d == ADMISSION_REJECT
    # 名单外的"门"不触发 reject(不暗改冻结判据集)
    d2, _ = decide_admission(audit, gate_decisions={
        "gate_some_future_thing": {"ok": False}})
    assert d2 != ADMISSION_REJECT


def test_admission_budget_defer_independent_reason() -> None:
    states = _std_states()
    hyp = build_hypothesis(
        parent_path_id="p1",
        substrate_state_ref=states[ETHANOL].state_id,
        participants=[_sub(states[ETHANOL].state_id, coefficient=2),
                      _prod(states[ACETIC_ACID].state_id, coefficient=2),
                      Participant(
                          state_ref=states[O2].state_id,
                          side=PARTICIPANT_SIDE_REACTANT,
                          role=PARTICIPANT_ROLE_COSUBSTRATE,
                          coefficient=1,
                          coefficient_status=COEFFICIENT_KNOWN)],
        participant_list_status=PARTICIPANT_LIST_DECLARED_COMPLETE,
        step_scope="net_reaction", origin_group_key="budget")
    audit = audit_hypothesis(
        hyp, states={s.state_id: s for s in states.values()})
    d, reasons = decide_admission(
        audit, gate_decisions={}, budget_state={
            "exhausted": True, "reason": "max_total_search_actions"})
    assert d == ADMISSION_DEFER
    assert any(r.startswith("R4:") for r in reasons)


def test_admission_all_verified_expand() -> None:
    states = _std_states()
    hyp = _balanced_hypothesis(states)
    ctx = build_path_context(
        requested_scope=REQUESTED_SCOPE_CONDITION_COMPATIBLE,
        condition_facts=[
            build_condition_fact(key=CONDITION_KEY_OXYGEN,
                                 value="aerobic",
                                 status=FACT_STATUS_KNOWN_PRESENT)],
        accumulated_requirements=[
            build_requirement(key=CONDITION_KEY_OXYGEN, level="essential",
                              value="aerobic")],
        assessment_scope=["oxygen_regime"])
    audit = audit_hypothesis(
        hyp, states={s.state_id: s for s in states.values()}, context=ctx)
    d, _ = decide_admission(audit, gate_decisions={
        "gate_direction_source": {"ok": True}})
    assert d == ADMISSION_EXPAND


# ---------------------------------------------------------------- D01/D02


def _donor_diag(**kw):
    defaults = dict(
        current={"smiles": "c1ccccc1"},
        donor={"center_atom_ids": ["d5"]},
        alignment={"status": "resolved",
                   "donor_to_current": {"d5": "c5"},
                   "equivalence_classes": [],
                   "ref": "align-1"},
        expectation={"target_smiles": "Oc1ccccc1"},
        result={"product_smiles": "Oc1ccccc1", "edit_atom_ids": ["c5"]},
        edits=[{"atom_id": "c5", "op": "add_OH"}],
    )
    defaults.update(kw)
    return check_edit_against_donor(**defaults)


def test_d01_legal_edit_deviating_from_donor_expectation() -> None:
    """合法编辑但偏离供体预期:strict=False;center 独立报告。

    用对映体偏离表达"CN 相同(旁证通过)但严格结构不一致":
    CN 旁证不升格为 strict 一致(§5.1)。
    """
    diag = _donor_diag(
        current={"smiles": "C[C@H](N)C(=O)O"},
        donor={"center_atom_ids": ["d5"]},
        alignment={"status": "resolved",
                   "donor_to_current": {"d5": "c5"},
                   "equivalence_classes": [], "ref": "align-d01"},
        expectation={"target_smiles": "C[C@H](N)C(=O)O"},
        result={"product_smiles": "C[C@@H](N)C(=O)O",
                "edit_atom_ids": ["c5"]},
        edits=[{"atom_id": "c5", "op": "invert"}])
    assert diag.strict_target_match is False   # strict 识别目标偏离
    assert diag.reaction_center_match is True  # center 依映射分别报告
    assert diag.legacy_cn_match is True        # CN 旁证:立体盲口径相同
    # CN 旁证不升格:cn 一致但严格结构不一致(分轴)
    assert diag.legacy_cn_match is not diag.strict_target_match


def test_d01_center_deviation_reported_separately() -> None:
    diag = _donor_diag(
        result={"product_smiles": "Oc1ccccc1",
                "edit_atom_ids": ["c1", "c5"]},  # 编辑了中心外原子
        edits=[{"atom_id": "c1", "op": "add_OH"},
               {"atom_id": "c5", "op": "add_OH"}])
    assert diag.strict_target_match is True    # 结果恰与预期一致
    assert diag.reaction_center_match is False  # 但 center 外有变更
    assert diag.extra_changes == ["c1"]


def test_d02_symmetry_equivalent_center_not_rejected() -> None:
    """对称等价:中心在对齐等价类内 → 不误拒。"""
    diag = _donor_diag(
        alignment={"status": "resolved",
                   "donor_to_current": {"d5": "c1"},
                   # c1 与 c5 是对称等价位
                   "equivalence_classes": [["c1", "c5"]],
                   "ref": "align-2"},
        result={"product_smiles": "Oc1ccccc1",
                "edit_atom_ids": ["c5"]},
        edits=[{"atom_id": "c5", "op": "add_OH"}])
    assert diag.reaction_center_match is True  # 等价类内:不误拒
    assert diag.extra_changes == []


def test_d02_alignment_unavailable_center_unknown_others_kept() -> None:
    """映射缺失:受影响轴 center unknown;strict/CN 轴不被抹掉。"""
    diag = _donor_diag(
        alignment={"status": "unavailable", "ref": "align-3"},
        expectation={"target_smiles": "Oc1ccccc1"},
        result={"product_smiles": "Oc1ccccc1", "edit_atom_ids": ["c5"]})
    assert diag.reaction_center_match is None     # 受影响轴 unknown
    assert diag.strict_target_match is True       # 其他轴照常输出
    assert diag.legacy_cn_match is True
    assert any("alignment_unavailable" in r
               for r in diag.missing_info_reasons)


def test_d02_stereo_unknown_does_not_invalidate_center() -> None:
    """立体未知不必使已有充分映射支持的变换中心变 unknown。"""
    diag = _donor_diag(
        current={"smiles": "C[C@H](N)C(=O)O"},
        expectation={"target_smiles": "C[C@@H](N)C(=O)O"},
        result={"product_smiles": "C[C@@H](N)C(=O)O",
                "edit_atom_ids": ["c5"]},
        edits=[{"atom_id": "c5", "op": "invert"}])
    # center 有充分映射支持 → 判定照常;strict 独立判立体一致性
    assert diag.reaction_center_match is True
    assert diag.strict_target_match is True


def test_donor_diagnostic_missing_inputs_unknown() -> None:
    diag = _donor_diag(
        expectation={"target_smiles": ""},
        result={"product_smiles": ""})
    assert diag.strict_target_match is None
    assert diag.legacy_cn_match is None
    assert any("missing" in r for r in diag.missing_info_reasons)


# ---------------------------------------------------------------- 池审计


def _pool_item(rank, origin, eid, smiles="CCO"):
    return {"retrieval_rank": rank, "source_origin": origin,
            "evidence_id": eid, "smiles": smiles}


def test_pool_stage_record_and_order_validation() -> None:
    stage = record_pool_stage(
        stage="retrieved_raw", input_items=[], output_items=[
            _pool_item(1, "curated_reaction", "E1")],
        item_dispositions=[{"id": "E1", "disposition_code": "kept"}])
    assert stage.n_input == 0 and stage.n_output == 1
    assert stage.source_origin_distribution == {"curated_reaction": 1}
    record = build_pool_audit(run_id="r", path_id="p", stages=[stage],
                              input_preview_policy=INPUT_PREVIEW_OFF)
    assert record.input_preview["status"] == "not_run"
    # 阶段顺序非法 → fail-closed
    bad = record_pool_stage(stage="bounded", input_items=[], output_items=[])
    with pytest.raises(PoolAuditError, match="顺序"):
        build_pool_audit(run_id="r", path_id="p", stages=[bad, stage],
                         input_preview_policy=INPUT_PREVIEW_OFF)


def test_input_preview_off_records_not_run() -> None:
    """off:记录未执行及原因,不冒称已做 G2。"""
    out = run_input_preview(
        substrate_smiles="CCO", candidates=[{"smiles": "CC(=O)O"}],
        policy=INPUT_PREVIEW_OFF)
    assert out["status"] == "not_run"
    assert out["reason"] == "input_preview_policy_off"
    assert "versions" not in out  # 没跑就没有 G2 版本块


def test_input_preview_diagnostic_does_not_change_pool() -> None:
    """diagnostic:只附诊断;池成员/顺序不变(不消费筛选/排序结果)。"""
    candidates = [
        {"smiles": "CCO", "note": ""},
        {"smiles": "CC(=O)O", "note": ""},
    ]
    out = run_input_preview(
        substrate_smiles="c1ccccc1", candidates=candidates,
        surface_text="", policy=INPUT_PREVIEW_DIAGNOSTIC)
    assert out["policy"] == INPUT_PREVIEW_DIAGNOSTIC
    assert out["pool_unchanged"] is True
    assert set(out["diagnostics"].keys()) == {"0", "1"}
    for diag in out["diagnostics"].values():
        assert diag["disposition"].startswith("diagnostic_only")
    assert "v43-cons-2" in out["versions"]["cons_filter"]


def test_pool_order_stable_and_truncation_disclosed() -> None:
    items = [
        _pool_item(3, "analog_transfer", "E3"),
        _pool_item(1, "curated_reaction", "E1"),
        _pool_item(1, "analog_transfer", "E2"),   # 同位次 → source/ID tie-break
        _pool_item(2, "biotransformation_rule", "E4"),
    ]
    ordered, disclosure = order_pool(items, limit=3)
    # 键序 (rank, source_origin, evidence_id):rank 1 的两项按来源字典序,
    # analog_transfer < curated_reaction → E2 先;确定性 tie-break,稳定
    assert [it["evidence_id"] for it in ordered] == ["E2", "E1", "E4"]
    assert disclosure["n_truncated"] == 1
    assert disclosure["truncated_source_origins"] == {"analog_transfer": 1}
    assert disclosure["covers_full_pool"] is False
    assert disclosure["order_key_version"] == "ppv1-pool-order-1"
    # 不限:全覆盖
    _, full = order_pool(items)
    assert full["covers_full_pool"] is True
    # 稳定性:同输入重排得同输出(重放确定性)
    again, _ = order_pool(list(reversed(items)), limit=3)
    assert [it["evidence_id"] for it in again] == ["E2", "E1", "E4"]


def test_pool_dedupe_rejects_cn_key_and_keeps_unkeyed() -> None:
    items = [
        _pool_item(1, "curated_reaction", "E1"),
        _pool_item(2, "curated_reaction", "E1"),   # 重复 evidence_id
        {"retrieval_rank": 3, "source_origin": "unknown"},  # 无键
    ]
    with pytest.raises(PoolAuditError, match="不得使用 CN"):
        dedupe_pool(items, dedupe_key="cn")
    kept, dups = dedupe_pool(items, dedupe_key="evidence_id")
    assert len(kept) == 2
    assert dups[0]["duplicate_of"] == "E1"


# ---------------------------------------------------------------- 底物档案


def test_substrate_profile_independent_of_candidates() -> None:
    """底物档案只依赖状态+上下文(不依赖候选列表)。"""
    state = build_chemical_state("C[C@H](N)C(=O)O",
                                 STRUCTURE_ORIGIN_RAW_INPUT)
    ctx = build_path_context(condition_facts=[
        build_condition_fact(key=CONDITION_KEY_PH, value=7.0,
                             status=FACT_STATUS_KNOWN_PRESENT)])
    profile = build_substrate_profile(state, ctx)
    assert profile.structure_smiles == state.smiles_isomeric  # 完整结构
    assert profile.cn_identity == state.cn_identity           # CN 兼容键
    assert profile.formal_charge == 0
    assert profile.stereo_information_status == "specified"
    assert profile.element_counts["C"] == 3
    assert profile.condition_keys_known == ["pH"]
    assert profile.context_ref == ctx.context_id
    # 模型输入用完整结构(非 CN;序列化键为 structure_smiles)
    d = profile.to_dict()
    assert d["structure_smiles"] == profile.structure_smiles
    assert d["cn_identity"] == profile.cn_identity


def test_substrate_profile_cn_only_state_honest() -> None:
    from pathway_v43.pollutant.chemstate import \
        build_chemical_state_from_cn_only

    state = build_chemical_state_from_cn_only("CCO")
    profile = build_substrate_profile(state)
    assert profile.structure_smiles == ""    # 不从 CN 猜结构
    assert profile.element_counts == {}
    assert profile.original_structure_available is False
    assert profile.representation_fidelity == "cn_only_projection"


def test_substrate_profile_feature_policy_validation() -> None:
    from pathway_v43.pollutant.substrate_profile import \
        SubstrateProfileError

    state = build_chemical_state("CCO", STRUCTURE_ORIGIN_RAW_INPUT)
    with pytest.raises(SubstrateProfileError, match="未知特征策略键"):
        build_substrate_profile(state, None, {"bogus_key": True})
    slim = build_substrate_profile(
        state, None, {"include_element_counts": False})
    assert slim.element_counts == {}
    assert slim.molecular_formula == "C2H6O"  # 其他特征仍输出
