"""S2 上下文/诊断/审计测试(v2 回修;规则级夹具;模型 off,无金标)。

覆盖验收矩阵 C01–C06、D01–D03、H01、H04 与回修新增反例(F01/F02/F03/
F05/F06/P2)。**v2 修正了 v1 的错误正例**:2 C2H6O + O2 → 2 C2H4O2
实际缺 4 个氢,不再是"配平"正例;正确正例改为 CCO + O=O → CC(=O)O + O
(元素差为零),缺氢/缺水反例一并钉住。
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
    STRUCTURE_UNAVAILABLE,
    audit_hypothesis,
    check_edit_against_donor,
    decide_admission,
    legacy_validation_to_gate_decisions,
)
from pathway_v43.pollutant.chemstate import (  # noqa: E402
    STRUCTURE_ORIGIN_RAW_INPUT,
    STRUCTURE_ORIGIN_SOURCE_PRODUCT,
    build_chemical_state,
    build_chemical_state_from_cn_only,
)
from pathway_v43.pollutant.hypothesis import (  # noqa: E402
    COEFFICIENT_KNOWN,
    COEFFICIENT_UNKNOWN,
    PARTICIPANT_LIST_DECLARED_COMPLETE,
    PARTICIPANT_LIST_PARTIAL,
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
    FACT_ORIGIN_CURATED_SOURCE,
    FACT_ORIGIN_SCENARIO_TRANSITION,
    FACT_ORIGIN_USER_INPUT,
    FACT_STATUS_KNOWN_ABSENT,
    FACT_STATUS_KNOWN_PRESENT,
    REQUESTED_SCOPE_CONDITION_COMPATIBLE,
    REQUESTED_SCOPE_POSSIBLE,
    VALUE_BASIS_OPTIMUM,
    VALUE_BASIS_POINT,
    aggregate_environment_fit,
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
HYDROGEN = "[H][H]"
METHYL_ACETATE = "COC(C)=O"
METHANOL = "CO"
WATER = "O"
SRC = ["src:rule-1"]


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


def _states(*smiles):
    return {s: _pstate(s) for s in smiles}


# ------------------------------------------------- F01:元素账(全氢)正反例


def _balanced_hypothesis(states):
    """**正确配平**正例:CCO + O=O → CC(=O)O + H2O(元素差为零,含全部氢)。

    左:C2H6O + O2 = C2 H6 O3;右:C2H4O2 + H2O = C2 H6 O3 ✓。
    (v1 的 2 C2H6O + O2 → 2 C2H4O2 实际缺 4H,已废除;"O"= 水。)
    """
    sub = states[ETHANOL]
    o2 = states[O2]
    acetic = states[ACETIC_ACID]
    atomic_o = states[WATER]
    return build_hypothesis(
        parent_path_id="p1", substrate_state_ref=sub.state_id,
        participants=[
            _sub(sub.state_id, coefficient=1),
            Participant(state_ref=o2.state_id,
                        side=PARTICIPANT_SIDE_REACTANT,
                        role=PARTICIPANT_ROLE_COSUBSTRATE,
                        coefficient=1, coefficient_status=COEFFICIENT_KNOWN),
            _prod(acetic.state_id, coefficient=1),
            _prod(atomic_o.state_id, coefficient=1,
                  role="coproduct"),
        ],
        participant_list_status=PARTICIPANT_LIST_DECLARED_COMPLETE,
        step_scope="net_reaction", origin_group_key="balanced-oxidation",
        transformation_signature_status="verified",
        step_scope_evidence_refs=["src:balanced-example"])


def test_f01_balanced_reaction_all_hydrogen_verified() -> None:
    states = {s: _pstate(s) for s in (ETHANOL, O2, ACETIC_ACID, WATER)}
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
    check = next(c for c in audit.checks
                 if c.name == CHECK_ELEMENT_ACCOUNTING)
    assert check.detail["element_delta"] == {}  # 结构化差值:零缺口
    assert check.detail["accounting_scope"] == "full_balance_all_hydrogen"


def test_f01_missing_hydrogen_violated_not_verified() -> None:
    """v1 错误正例的反例:CCO → CC=O 声明完整 ⇒ ΔH=+2 ⇒ violated。"""
    states = _states(ETHANOL, ACETALDEHYDE)
    hyp = build_hypothesis(
        parent_path_id="p1", substrate_state_ref=states[ETHANOL].state_id,
        participants=[_sub(states[ETHANOL].state_id, coefficient=1),
                      _prod(states[ACETALDEHYDE].state_id, coefficient=1)],
        participant_list_status=PARTICIPANT_LIST_DECLARED_COMPLETE,
        step_scope="net_reaction", origin_group_key="missing-h2")
    audit = audit_hypothesis(
        hyp, states={s.state_id: s for s in states.values()})
    check = next(c for c in audit.checks
                 if c.name == CHECK_ELEMENT_ACCOUNTING)
    assert check.status == CHECK_VIOLATED
    assert check.reason_code.startswith("declared_account_violated")
    assert check.detail["element_delta"] == {"H": "2"}
    assert check.detail["omission_pattern_matches"] == ["2H:reactant_side"]
    # 违规不 reject(P2-1 独立理由码),且绝不进入"全部核实"
    disposition, reasons = decide_admission(audit)
    assert disposition == ADMISSION_RETAIN_CONDITIONAL
    assert any(r.startswith("R5d:declared_account_violated")
               for r in reasons)


def test_f01_explicit_h2_product_balanced() -> None:
    """CCO → CC=O + H2(显式氢气产物):全氢账为零 ⇒ verified。"""
    states = _states(ETHANOL, ACETALDEHYDE, HYDROGEN)
    hyp = build_hypothesis(
        parent_path_id="p1", substrate_state_ref=states[ETHANOL].state_id,
        participants=[_sub(states[ETHANOL].state_id, coefficient=1),
                      _prod(states[ACETALDEHYDE].state_id, coefficient=1),
                      _prod(states[HYDROGEN].state_id, coefficient=1,
                            role="coproduct")],
        participant_list_status=PARTICIPANT_LIST_DECLARED_COMPLETE,
        step_scope="net_reaction", origin_group_key="explicit-h2")
    audit = audit_hypothesis(
        hyp, states={s.state_id: s for s in states.values()})
    assert audit.check_status(CHECK_ELEMENT_ACCOUNTING) == CHECK_VERIFIED
    assert audit.check_status(CHECK_FORMAL_CHARGE_ACCOUNTING) == \
        CHECK_VERIFIED


def test_f01_v1_bad_example_actually_imbalanced() -> None:
    """钉住 v1 错误正例:2 C2H6O + O2 → 2 C2H4O2 缺 4H(审核 F01)。"""
    states = _states(ETHANOL, O2, ACETIC_ACID)
    hyp = build_hypothesis(
        parent_path_id="p1", substrate_state_ref=states[ETHANOL].state_id,
        participants=[
            _sub(states[ETHANOL].state_id, coefficient=2),
            Participant(state_ref=states[O2].state_id,
                        side=PARTICIPANT_SIDE_REACTANT,
                        role=PARTICIPANT_ROLE_COSUBSTRATE,
                        coefficient=1, coefficient_status=COEFFICIENT_KNOWN),
            _prod(states[ACETIC_ACID].state_id, coefficient=2)],
        participant_list_status=PARTICIPANT_LIST_DECLARED_COMPLETE,
        step_scope="net_reaction", origin_group_key="v1-bad-example")
    audit = audit_hypothesis(
        hyp, states={s.state_id: s for s in states.values()})
    check = next(c for c in audit.checks
                 if c.name == CHECK_ELEMENT_ACCOUNTING)
    assert check.status == CHECK_VIOLATED
    assert check.detail["element_delta"] == {"H": "4"}


def test_f01_hydrolysis_convention_pattern_flagged() -> None:
    """文献惯例水解式(不写 H2O 反应物):violated + H2O 模式数值相符。

    乙酸甲酯 → 乙酸 + 甲醇(缺反应物 H2O):Δ = H:-2, O:-1。
    模式标注只表示数值相符,不证明缺项原因(Codex 收紧)。
    """
    states = _states(METHYL_ACETATE, ACETIC_ACID, METHANOL)
    hyp = build_hypothesis(
        parent_path_id="p1", substrate_state_ref=states[METHYL_ACETATE
                                                        ].state_id,
        participants=[
            _sub(states[METHYL_ACETATE].state_id, coefficient=1),
            _prod(states[ACETIC_ACID].state_id, coefficient=1),
            _prod(states[METHANOL].state_id, coefficient=1,
                  role="coproduct")],
        participant_list_status=PARTICIPANT_LIST_DECLARED_COMPLETE,
        step_scope="net_reaction", origin_group_key="hydrolysis-conv")
    audit = audit_hypothesis(
        hyp, states={s.state_id: s for s in states.values()})
    check = next(c for c in audit.checks
                 if c.name == CHECK_ELEMENT_ACCOUNTING)
    assert check.status == CHECK_VIOLATED
    assert check.detail["element_delta"] == {"H": "-2", "O": "-1"}
    assert check.detail["omission_pattern_matches"] == \
        ["H2O:product_side"]
    assert "不证明实际缺该物质" in \
        check.detail["omission_pattern_semantics"]


def test_f01_ambiguous_participants_not_full() -> None:
    """未确认并列计量的重复参与物 ⇒ 完整度/全账 unknown(F01)。"""
    states = _states(ETHANOL, ACETIC_ACID, O2)
    p1 = Participant(state_ref=states[O2].state_id,
                     side=PARTICIPANT_SIDE_REACTANT,
                     role=PARTICIPANT_ROLE_COSUBSTRATE,
                     coefficient=1, coefficient_status=COEFFICIENT_KNOWN)
    p2 = Participant(state_ref=states[O2].state_id,
                     side=PARTICIPANT_SIDE_REACTANT,
                     role=PARTICIPANT_ROLE_COSUBSTRATE,
                     coefficient=1, coefficient_status=COEFFICIENT_KNOWN)
    hyp = build_hypothesis(
        parent_path_id="p1", substrate_state_ref=states[ETHANOL].state_id,
        participants=[_sub(states[ETHANOL].state_id, coefficient=2),
                      p1, p2,
                      _prod(states[ACETIC_ACID].state_id, coefficient=2)],
        participant_list_status=PARTICIPANT_LIST_DECLARED_COMPLETE,
        step_scope="net_reaction", origin_group_key="ambiguous")
    assert hyp.ambiguous_participants is True
    audit = audit_hypothesis(
        hyp, states={s.state_id: s for s in states.values()})
    completeness = next(c for c in audit.checks
                        if c.name == "participant_completeness")
    assert completeness.status == CHECK_UNKNOWN
    assert audit.check_status(CHECK_ELEMENT_ACCOUNTING) == CHECK_UNKNOWN
    assert audit.participant_accounting_status != "full"
    d, _ = decide_admission(audit)
    assert d != ADMISSION_EXPAND  # 歧义绝不进入"全部核实"


def test_f05_cn_only_charge_account_unknown() -> None:
    """CN-only/中和形输入:电荷账 unknown,不得拿中和后电荷算假通过。"""
    sub_cn = build_chemical_state_from_cn_only("CCO")
    states = _states(ACETIC_ACID, O2, "[O]")
    hyp = build_hypothesis(
        parent_path_id="p1", substrate_state_ref=sub_cn.state_id,
        participants=[_sub(sub_cn.state_id, coefficient=1),
                      Participant(state_ref=states[O2].state_id,
                                  side=PARTICIPANT_SIDE_REACTANT,
                                  role=PARTICIPANT_ROLE_COSUBSTRATE,
                                  coefficient=1,
                                  coefficient_status=COEFFICIENT_KNOWN),
                      _prod(states[ACETIC_ACID].state_id, coefficient=1),
                      _prod(states["[O]"].state_id, coefficient=1,
                            role="coproduct")],
        participant_list_status=PARTICIPANT_LIST_DECLARED_COMPLETE,
        step_scope="net_reaction", origin_group_key="cn-only-charge")
    all_states = {s.state_id: s for s in states.values()}
    all_states[sub_cn.state_id] = sub_cn
    audit = audit_hypothesis(hyp, states=all_states)
    # CN-only 是合法缺结构(F05):parse 检查 unknown,不是 violated
    assert audit.check_status(CHECK_STRUCTURE_PARSE_VALENCE) == \
        CHECK_UNKNOWN
    charge = next(c for c in audit.checks
                  if c.name == CHECK_FORMAL_CHARGE_ACCOUNTING)
    assert charge.status == CHECK_UNKNOWN
    assert "original_charge_unavailable" in charge.reason_code
    element = next(c for c in audit.checks
                   if c.name == CHECK_ELEMENT_ACCOUNTING)
    assert element.reason_code == STRUCTURE_UNAVAILABLE
    # admission:R1 不触发(非语法非法),走 unknown → retain_conditional
    d, reasons = decide_admission(audit)
    assert d == ADMISSION_RETAIN_CONDITIONAL
    assert not any(r.startswith("R1:") for r in reasons)


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
        value={"lo": 5.5, "hi": 8.0}, source_refs=SRC),
        build_requirement(
            key=CONDITION_KEY_ELECTRON_DONOR, level="essential",
            value="H2O", source_refs=SRC)]
    ctx = _ctx(facts, reqs)
    result = aggregate_environment_fit(
        facts=facts, requirements=reqs,
        declared_scope=["pH", "electron_donor", "oxygen_regime"])
    assert result.environment_fit == "unknown"
    per = {p["key"]: p for p in result.per_requirement}
    assert per["pH"]["status"] == "satisfied"
    # 供体:没有适用事实 → unknown(未列出 ≠ known_absent,不判 conflict)
    assert per["electron_donor"]["status"] == "unknown"
    assert result.assessed_scope == "possible"


def test_f03_required_donor_known_absent_conflict() -> None:
    """F03:必需 NADH 的 fact 状态是 known_absent ⇒ conflict(不是 satisfied)。"""
    facts = [build_condition_fact(
        key=CONDITION_KEY_ELECTRON_DONOR, value="NADH",
        status=FACT_STATUS_KNOWN_ABSENT,
        origin=FACT_ORIGIN_USER_INPUT)]
    reqs = [build_requirement(
        key=CONDITION_KEY_ELECTRON_DONOR, level="essential",
        value="NADH", source_refs=SRC)]
    result = aggregate_environment_fit(
        facts=facts, requirements=reqs,
        declared_scope=["electron_donor"])
    per = {p["key"]: p for p in result.per_requirement}
    assert per["electron_donor"]["status"] == "conflict"
    assert result.environment_fit == "conflict"


def test_f03_unsourced_essential_never_compatible_no_conflict() -> None:
    """F03:无来源 essential = 未核实假设:阻止 compatible,不产生冲突。"""
    facts = [build_condition_fact(
        key=CONDITION_KEY_OXYGEN, value="aerobic",
        status=FACT_STATUS_KNOWN_PRESENT)]
    reqs = [build_requirement(
        key=CONDITION_KEY_OXYGEN, level="essential", value="aerobic",
        source_refs=[])]  # 无来源
    result = aggregate_environment_fit(
        facts=facts, requirements=reqs,
        declared_scope=["oxygen_regime"])
    per = {p["key"]: p for p in result.per_requirement}
    assert per["oxygen_regime"]["status"] == "unknown"
    assert "necessity_unsourced" in per["oxygen_regime"]["reason"]
    assert result.environment_fit == "unknown"  # 不能证明 compatible


def test_f03_historical_scenario_fact_not_current() -> None:
    """F03:文献/历史场景事实不成为当前事实(除非场景匹配)。"""
    historical = [build_condition_fact(
        key=CONDITION_KEY_OXYGEN, value="aerobic",
        status=FACT_STATUS_KNOWN_PRESENT,
        origin=FACT_ORIGIN_CURATED_SOURCE, source_ref="doi:10.x",
        subject_scenario_ref="historical-scenario")]
    reqs = [build_requirement(key=CONDITION_KEY_OXYGEN, level="essential",
                              value="aerobic", source_refs=SRC)]
    # 当前场景 ≠ historical-scenario ⇒ 该事实不适用
    result = aggregate_environment_fit(
        facts=historical, requirements=reqs,
        declared_scope=["oxygen_regime"], scenario_ref="current-scenario")
    per = {p["key"]: p for p in result.per_requirement}
    assert per["oxygen_regime"]["status"] == "unknown"
    assert result.environment_fit == "unknown"
    # 显式采用该场景(scenario_ref 匹配)⇒ 事实适用
    result2 = aggregate_environment_fit(
        facts=historical, requirements=reqs,
        declared_scope=["oxygen_regime"],
        scenario_ref="historical-scenario")
    per2 = {p["key"]: p for p in result2.per_requirement}
    assert per2["oxygen_regime"]["status"] == "satisfied"
    assert result2.environment_fit == "compatible"


def test_f03_phase_scoped_fact_not_applicable_across_phases() -> None:
    """F03:阶段限定事实只在该阶段适用(转换只影响后续)。"""
    fact = build_condition_fact(
        key=CONDITION_KEY_TEMPERATURE, value=25.0,
        status=FACT_STATUS_KNOWN_PRESENT,
        origin=FACT_ORIGIN_SCENARIO_TRANSITION,
        subject_scenario_ref="s1", phase_id="phase-1", source_ref="user:t")
    reqs = [build_requirement(
        key=CONDITION_KEY_TEMPERATURE, level="essential",
        value={"lo": 20.0, "hi": 30.0}, source_refs=SRC)]
    result = aggregate_environment_fit(
        facts=[fact], requirements=reqs,
        declared_scope=["temperature_C"], scenario_ref="s1",
        phase_id="phase-0")  # phase-0:事实未生效
    assert result.environment_fit == "unknown"
    result2 = aggregate_environment_fit(
        facts=[fact], requirements=reqs,
        declared_scope=["temperature_C"], scenario_ref="s1",
        phase_id="phase-1")
    assert result2.environment_fit == "compatible"


def test_f03_label_value_unknown_without_registry() -> None:
    """F03/mimo:mesophilic 标签无注册映射 ⇒ unknown(不产生假冲突)。"""
    facts = [build_condition_fact(
        key=CONDITION_KEY_TEMPERATURE, value=25.0,
        status=FACT_STATUS_KNOWN_PRESENT)]
    reqs = [build_requirement(
        key=CONDITION_KEY_TEMPERATURE, level="essential",
        value="mesophilic", source_refs=SRC)]
    result = aggregate_environment_fit(
        facts=facts, requirements=reqs,
        declared_scope=["temperature_C"])
    per = {p["key"]: p for p in result.per_requirement}
    assert per["temperature_C"]["status"] == "unknown"
    assert "label_without_registered_range" in \
        per["temperature_C"]["reason"]
    assert result.environment_fit == "unknown"  # 不判 conflict


def test_f03_optimum_never_conflicts() -> None:
    """mimo 4.2(1)/Codex:最适值偏离只作 preference,永不 conflict;
    单数值未声明 basis 不自动推为 optimum ⇒ unknown。"""
    facts = [build_condition_fact(
        key=CONDITION_KEY_TEMPERATURE, value=45.0,
        status=FACT_STATUS_KNOWN_PRESENT)]
    req_opt = build_requirement(
        key=CONDITION_KEY_TEMPERATURE, level="essential", value=30.0,
        value_basis=VALUE_BASIS_OPTIMUM, source_refs=SRC)
    result = aggregate_environment_fit(
        facts=facts, requirements=[req_opt],
        declared_scope=["temperature_C"])
    per = {p["key"]: p for p in result.per_requirement}
    assert per["temperature_C"]["status"] == "not_applicable"  # preference
    assert result.environment_fit == "unknown"
    assert any("optimum_deviation" in n for n in result.preference_notes)
    # 未声明 basis 的单数值:从严 unknown,不自动 optimum/point
    req_unspec = build_requirement(
        key=CONDITION_KEY_TEMPERATURE, level="essential", value=30.0,
        source_refs=SRC)
    result2 = aggregate_environment_fit(
        facts=facts, requirements=[req_unspec],
        declared_scope=["temperature_C"])
    per2 = {p["key"]: p for p in result2.per_requirement}
    assert per2["temperature_C"]["status"] == "unknown"
    # 显式 point:偏离 = conflict(声明的必需点值)
    req_point = build_requirement(
        key=CONDITION_KEY_TEMPERATURE, level="essential", value=30.0,
        value_basis=VALUE_BASIS_POINT, source_refs=SRC)
    result3 = aggregate_environment_fit(
        facts=facts, requirements=[req_point],
        declared_scope=["temperature_C"])
    assert result3.environment_fit == "conflict"


def test_f03_unassessed_dimensions_disclosed() -> None:
    """相容结论必须附带未评估维度(不显示为全维度相容)。"""
    facts = [build_condition_fact(
        key=CONDITION_KEY_OXYGEN, value="aerobic",
        status=FACT_STATUS_KNOWN_PRESENT)]
    reqs = [build_requirement(key=CONDITION_KEY_OXYGEN, level="essential",
                              value="aerobic", source_refs=SRC)]
    result = aggregate_environment_fit(
        facts=facts, requirements=reqs,
        declared_scope=["oxygen_regime"])
    assert result.environment_fit == "compatible"
    assert "light_regime" in result.unassessed_dimensions
    assert "biotic_abiotic" in result.unassessed_dimensions


def test_c02_anaerobic_vs_required_o2_conflict() -> None:
    """C02:明确无氧 vs 有来源的必需 O₂ → conflict;admission=defer。"""
    facts = [build_condition_fact(
        key=CONDITION_KEY_OXYGEN, value="anaerobic",
        status=FACT_STATUS_KNOWN_PRESENT,
        origin=FACT_ORIGIN_CURATED_SOURCE, source_ref="user:scenario")]
    reqs = [build_requirement(
        key=CONDITION_KEY_OXYGEN, level="essential", value="aerobic",
        source_refs=["src:reaction123"])]
    ctx = _ctx(facts, reqs)
    assert ctx.assessed_scope == "conflicted"
    sub = _pstate(ETHANOL, STRUCTURE_ORIGIN_RAW_INPUT)
    hyp = build_hypothesis(
        parent_path_id="p1", substrate_state_ref=sub.state_id,
        participants=[_sub(sub.state_id), _prod(_pstate(O2).state_id)],
        participant_list_status=PARTICIPANT_LIST_PARTIAL,
        step_scope="net_reaction",
        requirements=[{"key": CONDITION_KEY_OXYGEN, "level": "essential",
                       "value": "aerobic", "source_refs": ["src:r123"],
                       "value_basis": "unspecified"}],
        origin_group_key="o2-requiring")
    audit = audit_hypothesis(
        hyp, states={s.state_id: s for s in (
            sub, _pstate(ETHANOL), _pstate(O2))}, context=ctx)
    disposition, reasons = decide_admission(
        audit, gate_decisions={"gate_direction_source": {"ok": True}})
    assert disposition == ADMISSION_DEFER
    assert any("current_scenario_conflict" in r for r in reasons)


def test_f02_conflict_inherited_not_overwritten() -> None:
    """F02 复现 1:父步骤 20–30°C,当前 45°C 已 conflict;子步骤要求
    40–50°C 后评估仍为 conflict(不允许覆盖成 compatible)。"""
    facts = [build_condition_fact(
        key=CONDITION_KEY_TEMPERATURE, value=45.0,
        status=FACT_STATUS_KNOWN_PRESENT)]
    root = build_path_context(
        condition_facts=facts,
        accumulated_requirements=[build_requirement(
            key=CONDITION_KEY_TEMPERATURE, level="essential",
            value={"lo": 20.0, "hi": 30.0}, source_refs=SRC)],
        assessment_scope=["temperature_C"])
    assert root.assessed_scope == "conflicted"
    child = derive_child_context(root, step_requirements=[
        build_requirement(key=CONDITION_KEY_TEMPERATURE, level="essential",
                          value={"lo": 40.0, "hi": 50.0}, source_refs=SRC)])
    # 双方保留 ⇒ 合取:父要求与 45°C 冲突仍在
    assert child.assessed_scope == "conflicted"
    n_temp_reqs = sum(1 for r in child.accumulated_requirements
                      if r.key == CONDITION_KEY_TEMPERATURE)
    assert n_temp_reqs == 2  # 不覆盖:两条要求都在


def test_f02_step_conflict_survives_derivation() -> None:
    """F02 复现 2:当前 25°C,父 20–30 满足;子加 40–50 ⇒ 本步冲突,
    派生上下文仍 conflict(不允许子评估回 compatible)。"""
    facts = [build_condition_fact(
        key=CONDITION_KEY_TEMPERATURE, value=25.0,
        status=FACT_STATUS_KNOWN_PRESENT)]
    root = build_path_context(
        condition_facts=facts,
        accumulated_requirements=[build_requirement(
            key=CONDITION_KEY_TEMPERATURE, level="essential",
            value={"lo": 20.0, "hi": 30.0}, source_refs=SRC)],
        assessment_scope=["temperature_C"])
    assert root.assessed_scope == "condition_compatible"
    child = derive_child_context(root, step_requirements=[
        build_requirement(key=CONDITION_KEY_TEMPERATURE, level="essential",
                          value={"lo": 40.0, "hi": 50.0}, source_refs=SRC)])
    assert child.assessed_scope == "conflicted"


def test_f02_identical_requirements_deduped() -> None:
    """仅语义完全相同的要求可去重(F02)。"""
    root = build_path_context(accumulated_requirements=[
        build_requirement(key=CONDITION_KEY_OXYGEN, level="essential",
                          value="aerobic", source_refs=SRC)])
    child = derive_child_context(root, step_requirements=[
        build_requirement(key=CONDITION_KEY_OXYGEN, level="essential",
                          value="aerobic", source_refs=SRC)])
    assert len(child.accumulated_requirements) == 1


def test_c03_branches_isolated_and_scenario_transition_sourced() -> None:
    """C03:两分支不互相污染;阶段切换须有来源,不追改此前步骤。"""
    root = build_path_context(
        requested_scope=REQUESTED_SCOPE_POSSIBLE,
        condition_facts=[build_condition_fact(
            key=CONDITION_KEY_OXYGEN, value="aerobic",
            status=FACT_STATUS_KNOWN_PRESENT)],
        accumulated_requirements=[])
    branch_a = derive_child_context(root, step_requirements=[
        build_requirement(key=CONDITION_KEY_OXYGEN, level="essential",
                          value="aerobic", source_refs=SRC)])
    branch_b = derive_child_context(root, step_requirements=[
        build_requirement(key=CONDITION_KEY_PH, level="essential",
                          value={"lo": 5.0, "hi": 9.0}, source_refs=SRC)])
    keys_a = {r.key for r in branch_a.accumulated_requirements}
    keys_b = {r.key for r in branch_b.accumulated_requirements}
    assert CONDITION_KEY_OXYGEN in keys_a and CONDITION_KEY_OXYGEN not in \
        keys_b
    assert CONDITION_KEY_PH in keys_b and CONDITION_KEY_PH not in keys_a
    assert root.accumulated_requirements == []  # 父不可变
    with pytest.raises(Exception, match="必须有来源"):
        derive_child_context(root, scenario_transition={
            "new_phase_id": "phase-1"})
    ok = derive_child_context(root, scenario_transition={
        "new_phase_id": "phase-1", "source_ref": "user:phase-change"})
    assert ok.phase_id == "phase-1"
    assert ok.parent_context_ref == root.context_id
    assert root.phase_id == "phase-0"  # 不追改此前步骤


def test_c03_same_scenario_requirement_diff_recorded_both_kept() -> None:
    """同固定场景同键差异:显式记录 + 双方保留(不静默覆盖)。"""
    root = build_path_context(accumulated_requirements=[
        build_requirement(key=CONDITION_KEY_TEMPERATURE, level="essential",
                          value={"lo": 20, "hi": 30}, source_refs=SRC)])
    child = derive_child_context(root, step_requirements=[
        build_requirement(key=CONDITION_KEY_TEMPERATURE, level="essential",
                          value={"lo": 40, "hi": 50}, source_refs=SRC)])
    assert any("requirement_differs_at_same_scenario" in a
               for a in child.assumptions)
    assert len(child.accumulated_requirements) == 2


def test_c04_literature_oxygen_not_current_fact() -> None:
    """C04:文献有氧(观察条件参考),当前场景无条件 → 仍 unknown。"""
    facts = []
    reqs = [build_requirement(
        key=CONDITION_KEY_OXYGEN, level="essential", value="aerobic",
        basis="observed_condition_reference",
        source_refs=["doi:10.x/literature"],
        observed_source_conditions=[{
            "note": "来源报告该反应在好氧条件被观察",
            "source_ref": "doi:10.x/literature"}])]
    result = aggregate_environment_fit(
        facts=facts, requirements=reqs, declared_scope=["oxygen_regime"])
    per = {p["key"]: p for p in result.per_requirement}
    assert result.environment_fit == "unknown"
    assert per[CONDITION_KEY_OXYGEN]["status"] == "not_applicable"
    assert reqs[0].observed_source_conditions[0]["source_ref"] == \
        "doi:10.x/literature"


def test_c05_requested_compatible_one_unknown_assessed_possible() -> None:
    facts = [build_condition_fact(
        key=CONDITION_KEY_OXYGEN, value="aerobic",
        status=FACT_STATUS_KNOWN_PRESENT)]
    reqs = [build_requirement(key=CONDITION_KEY_OXYGEN, level="essential",
                              value="aerobic", source_refs=SRC),
            build_requirement(key=CONDITION_KEY_PH, level="essential",
                              value={"lo": 6.0, "hi": 8.0}, source_refs=SRC)]
    ctx = _ctx(facts, reqs, requested=REQUESTED_SCOPE_CONDITION_COMPATIBLE)
    assert ctx.requested_scope == REQUESTED_SCOPE_CONDITION_COMPATIBLE
    assert ctx.assessed_scope == "possible"  # 派生,不继承请求标签


def test_all_satisfied_within_declared_scope_compatible() -> None:
    facts = [
        build_condition_fact(key=CONDITION_KEY_OXYGEN, value="aerobic",
                             status=FACT_STATUS_KNOWN_PRESENT),
        build_condition_fact(key=CONDITION_KEY_PH, value=7.0,
                             status=FACT_STATUS_KNOWN_PRESENT),
    ]
    reqs = [
        build_requirement(key=CONDITION_KEY_OXYGEN, level="essential",
                          value="aerobic", source_refs=SRC),
        build_requirement(key=CONDITION_KEY_PH, level="essential",
                          value={"lo": 6.0, "hi": 8.0}, source_refs=SRC),
    ]
    ctx = _ctx(facts, reqs)
    assert ctx.assessed_scope == "condition_compatible"


def test_empty_requirements_not_auto_compatible() -> None:
    ctx = _ctx(facts=[], requirements=[])
    assert ctx.assessed_scope == "possible"


def test_condition_key_validation_fail_closed() -> None:
    from pathway_v43.pollutant.path_context import ConditionContractError

    with pytest.raises(ConditionContractError, match="未知条件键"):
        build_condition_fact(key="pressure_atm", value=1.0,
                             status=FACT_STATUS_KNOWN_PRESENT)
    with pytest.raises(ConditionContractError):
        build_condition_fact(key=CONDITION_KEY_OXYGEN, value="very_oxygenic",
                             status=FACT_STATUS_KNOWN_PRESENT)
    with pytest.raises(ConditionContractError, match="非有限"):
        build_condition_fact(key=CONDITION_KEY_PH,
                             value=float("nan"),
                             status=FACT_STATUS_KNOWN_PRESENT)


def test_f06_context_id_covers_semantic_fields() -> None:
    """F06:评估范围/依赖等语义字段进 context_id;不同前提不同身份。"""
    facts = [build_condition_fact(
        key=CONDITION_KEY_OXYGEN, value="aerobic",
        status=FACT_STATUS_KNOWN_PRESENT)]
    reqs = [build_requirement(key=CONDITION_KEY_OXYGEN, level="essential",
                              value="aerobic", source_refs=SRC)]
    ctx_no_scope = build_path_context(
        condition_facts=facts, accumulated_requirements=reqs,
        assessment_scope=[])
    ctx_scoped = build_path_context(
        condition_facts=facts, accumulated_requirements=reqs,
        assessment_scope=["oxygen_regime"])
    # v1 缺陷:两者 context_id 相同而结论 possible/compatible 相反
    assert ctx_no_scope.context_id != ctx_scoped.context_id
    assert ctx_no_scope.assessed_scope == "possible"
    assert ctx_scoped.assessed_scope == "condition_compatible"
    # 依赖引用差异 ⇒ 不同身份
    root = build_path_context(condition_facts=facts)
    child_x = derive_child_context(root, step_dependency_refs=["depX"])
    child_y = derive_child_context(root, step_dependency_refs=["depY"])
    assert child_x.context_id != child_y.context_id
    # from_dict 未知版本拒绝(F08)
    from pathway_v43.pollutant.path_context import (
        PathContext, ConditionContractError)

    d = ctx_scoped.to_dict()
    d["schema_version"] = "ppv1-context-999"
    with pytest.raises(ConditionContractError, match="版本未知"):
        PathContext.from_dict(d)


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
    assert result["unresolved_initial_supply"] == [
        ["speciesA", "speciesB"]]
    assert "不称化学不可能" in result["note"]
    resolved = resolve_dependency(
        a_b, new_evidence=["src:inoculation"], resolution="supported",
        note="接种提供初始供给")
    result2 = detect_circular_dependencies([resolved, b_a])
    assert result2["unresolved_initial_supply"] == [
        ["speciesA", "speciesB"]]
    both = resolve_dependency(
        b_a, new_evidence=["src:regeneration"], resolution="supported")
    result3 = detect_circular_dependencies([resolved, both])
    assert result3["unresolved_initial_supply"] == []


def test_f06_three_node_cycle_detected() -> None:
    """F06:v1 漏检的 A→B→C→A 三元环。"""
    deps = [
        build_dependency(kind="cosubstrate_supply",
                         statement="supplies:A:B"),
        build_dependency(kind="cosubstrate_supply",
                         statement="supplies:B:C"),
        build_dependency(kind="cosubstrate_supply",
                         statement="supplies:C:A"),
    ]
    result = detect_circular_dependencies(deps)
    assert result["cycles"] == [["A", "B", "C"]]
    assert result["unresolved_initial_supply"] == [["A", "B", "C"]]
    # 全部有来源支持 ⇒ 不阻断(unresolved 为空)
    resolved = [
        resolve_dependency(d, new_evidence=["src:e"], resolution="supported")
        for d in deps]
    assert detect_circular_dependencies(
        resolved)["unresolved_initial_supply"] == []


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


def test_f06_dependency_refs_without_resolution_not_verified() -> None:
    """F06:有依赖引用但未提供解析状态 ⇒ 不得视为已解决(unknown)。"""
    states = {s: _pstate(s) for s in (ETHANOL, ACETIC_ACID, O2, "[O]")}
    hyp = build_hypothesis(
        parent_path_id="p1", substrate_state_ref=states[ETHANOL].state_id,
        participants=[_sub(states[ETHANOL].state_id),
                      _prod(states[ACETIC_ACID].state_id)],
        participant_list_status=PARTICIPANT_LIST_PARTIAL,
        step_scope="net_reaction", origin_group_key="dep-refs",
        dependency_refs=["dep:1"])
    audit = audit_hypothesis(
        hyp, states={s.state_id: s for s in states.values()},
        unresolved_dependency_ids=None)  # 未提供解析状态
    check = next(c for c in audit.checks
                 if c.name == "provenance_dependency")
    assert check.status == CHECK_UNKNOWN
    assert check.reason_code == "dependency_resolution_not_provided"


# ---------------------------------------------------------------- H01/C06/D03


def test_h01_unparseable_prerequisite_failed_not_run() -> None:
    sub = _pstate(ETHANOL, STRUCTURE_ORIGIN_RAW_INPUT)
    from pathway_v43.pollutant.chemstate import build_chemical_state_from_cn_only

    bad = build_chemical_state_from_cn_only("not-a-real-structure-x")
    hyp = build_hypothesis(
        parent_path_id="p1", substrate_state_ref=sub.state_id,
        participants=[_sub(sub.state_id), _prod(bad.state_id)],
        participant_list_status=PARTICIPANT_LIST_PARTIAL,
        step_scope="net_reaction", origin_group_key="cn-only-participant")
    audit = audit_hypothesis(hyp, states={sub.state_id: sub,
                                          bad.state_id: bad})
    # CN-only 参与物(F05 修正):合法缺结构 ⇒ parse unknown 非 violated
    assert audit.check_status(CHECK_STRUCTURE_PARSE_VALENCE) == \
        CHECK_UNKNOWN
    for name in (CHECK_ELEMENT_ACCOUNTING,
                 CHECK_FORMAL_CHARGE_ACCOUNTING):
        check = next(c for c in audit.checks if c.name == name)
        assert check.status == CHECK_UNKNOWN
    d, _ = decide_admission(audit, gate_decisions={
        "gate_direction_source": {"ok": True}})
    assert d == ADMISSION_RETAIN_CONDITIONAL  # 非 R1 reject

    # 真·语法非法:构造期就 fail-closed(H01)
    from pathway_v43.pollutant.chemstate import ChemicalStateError

    with pytest.raises(ChemicalStateError):
        build_chemical_state("C1CC", STRUCTURE_ORIGIN_SOURCE_PRODUCT)


def test_d03_partial_participants_full_balance_unknown() -> None:
    states = _states(ETHANOL, ACETIC_ACID)
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
    assert audit.participant_accounting_status == "partial"
    balanced_states = {s: _pstate(s)
                       for s in (ETHANOL, O2, ACETIC_ACID, WATER)}
    hyp2 = _balanced_hypothesis(balanced_states)
    audit2 = audit_hypothesis(
        hyp2, states={s.state_id: s for s in balanced_states.values()})
    assert audit2.participant_accounting_status == "full"
    assert audit2.biological_support_status == "unknown"


def test_declared_complete_but_unknown_coeff_not_verified() -> None:
    states = _states(ETHANOL, ACETIC_ACID)
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
    """C06 admission 策略级:结构有效、gate 接受、账目/依赖未知 →
    retain_conditional(不自动拒绝,继承未知依赖)。"""
    states = _states(ETHANOL, ACETIC_ACID)
    hyp = build_hypothesis(
        parent_path_id="p1",
        substrate_state_ref=states[ETHANOL].state_id,
        participants=[_sub(states[ETHANOL].state_id),
                      _prod(states[ACETIC_ACID].state_id)],
        participant_list_status=PARTICIPANT_LIST_PARTIAL,
        step_scope="net_reaction", origin_group_key="c06",
        dependency_refs=["dep:upstream-model-assumption"])
    audit = audit_hypothesis(
        hyp, states={s.state_id: s for s in states.values()},
        unresolved_dependency_ids=["dep:upstream-model-assumption"])
    disposition, reasons = decide_admission(
        audit, gate_decisions={"gate_direction_source": {"ok": True},
                               "gate_recorded_eligibility": {"ok": True}})
    assert disposition == ADMISSION_RETAIN_CONDITIONAL
    assert any("unknown_checks_present" in r for r in reasons)
    assert any("不自动拒绝" in r for r in reasons)
    check = next(c for c in audit.checks
                 if c.name == "provenance_dependency")
    assert "dep:upstream-model-assumption" in check.evidence_refs


def test_admission_policy_decision_table_explicit() -> None:
    """P0-4(v2):决策表显式有序(含 R2b/R5d/R7);JSON 往返;版本门。"""
    policy = AdmissionPolicy()
    d = policy.to_dict()
    rules = d["rules"]
    assert [r["rule_id"] for r in rules] == [
        "R1", "R2", "R2b", "R3", "R4", "R5d", "R5", "R6", "R7"]
    assert [r["disposition"] for r in rules] == [
        "reject", "reject", "reject", "defer", "defer",
        "retain_conditional", "retain_conditional", "expand",
        "retain_conditional"]
    restored = AdmissionPolicy.from_dict(d)
    assert restored.to_dict() == d
    from pathway_v43.pollutant.audit import AuditContractError

    with pytest.raises(AuditContractError):
        AdmissionPolicy.from_dict({"policy_version": "bogus"})
    with pytest.raises(AuditContractError, match="未知门禁"):
        AdmissionPolicy.from_dict({
            "policy_version": "ppv1-admission-2",
            "reject_gates": ["gate_not_reviewed"]})


def test_p2_1_violated_reason_code_not_empty_audit() -> None:
    """P2-1:非空审计的元素 violated 落 R5d,不再冒 empty_audit 理由。"""
    states = _states(ETHANOL, ACETALDEHYDE)
    hyp = build_hypothesis(
        parent_path_id="p1", substrate_state_ref=states[ETHANOL].state_id,
        participants=[_sub(states[ETHANOL].state_id, coefficient=1),
                      _prod(states[ACETALDEHYDE].state_id, coefficient=1)],
        participant_list_status=PARTICIPANT_LIST_DECLARED_COMPLETE,
        step_scope="net_reaction", origin_group_key="violated-code")
    audit = audit_hypothesis(
        hyp, states={s.state_id: s for s in states.values()})
    d, reasons = decide_admission(audit)
    assert d == ADMISSION_RETAIN_CONDITIONAL
    assert reasons[0].startswith("R5d:declared_account_violated")
    assert "empty_audit" not in reasons[0]


def test_p2_1_r2b_contract_violation_not_chemical() -> None:
    """P2-1/mimo R2b:表示契约违反 → reject + 专属码(不冒称结构/
    化学不可能)。"""
    states = _states(ETHANOL, ACETIC_ACID)
    hyp = build_hypothesis(
        parent_path_id="p1", substrate_state_ref=states[ETHANOL].state_id,
        participants=[_sub(states[ETHANOL].state_id),
                      _prod(states[ACETIC_ACID].state_id)],
        participant_list_status=PARTICIPANT_LIST_PARTIAL,
        step_scope="net_reaction", origin_group_key="r2b")
    audit = audit_hypothesis(
        hyp, states={s.state_id: s for s in states.values()})
    d, reasons = decide_admission(
        audit, contract_violation={
            "kind": "non_positive_coefficient", "value": "0"})
    assert d == ADMISSION_REJECT
    assert reasons[0].startswith("R2b:contract_violated_representation")
    assert "非化学不可能" in reasons[0]


def test_p2_2_legacy_gate_mapper_keeps_per_product_verdicts() -> None:
    """P2-2:旧 validation → gate_decisions 映射(版本化,逐产物保留)。"""
    validation = {
        "evidence_id": "E-x",
        "gates": {
            "direction_source": {"ok": True, "reason": ""},
            "atom_mapping": {"ok": True, "reason": "", "value": "unavailable"},
            "recorded_eligibility": {"ok": False,
                                     "reason": "substrate_mismatch"},
        },
        "verdicts": [
            {"position": 0, "accepted": True, "reasons": []},
            {"position": 1, "accepted": False,
             "reasons": ["smiles_invalid"]},
        ],
    }
    mapped = legacy_validation_to_gate_decisions(validation)
    assert mapped["gate_direction_source"]["ok"] is True
    assert mapped["gate_recorded_eligibility"]["ok"] is False
    assert mapped["gate_recorded_eligibility"]["reason"] == \
        "substrate_mismatch"
    assert mapped["gate_atom_mapping_declared"]["ok"] is True
    # 逐产物 verdicts 全量保留(元素门禁在逐产物层,不丢)
    assert mapped["per_product_verdicts"] == [
        {"position": 0, "accepted": True, "reasons": []},
        {"position": 1, "accepted": False, "reasons": ["smiles_invalid"]},
    ]
    assert mapped["gate_ref"]["mapper_version"] == "ppv1-gate-mapper-1"
    # mapper 输出可直接喂 decide_admission(资格失败 → reject)
    states = _states(ETHANOL, ACETIC_ACID)
    hyp = build_hypothesis(
        parent_path_id="p1", substrate_state_ref=states[ETHANOL].state_id,
        participants=[_sub(states[ETHANOL].state_id),
                      _prod(states[ACETIC_ACID].state_id)],
        participant_list_status=PARTICIPANT_LIST_PARTIAL,
        step_scope="net_reaction", origin_group_key="mapper")
    audit = audit_hypothesis(
        hyp, states={s.state_id: s for s in states.values()})
    d, _ = decide_admission(audit, gate_decisions=mapped)
    assert d == ADMISSION_REJECT


def test_admission_gate_rejected_only_for_declared_gates() -> None:
    states = _states(ETHANOL, ACETIC_ACID)
    hyp = build_hypothesis(
        parent_path_id="p1", substrate_state_ref=states[ETHANOL].state_id,
        participants=[_sub(states[ETHANOL].state_id),
                      _prod(states[ACETIC_ACID].state_id)],
        participant_list_status=PARTICIPANT_LIST_PARTIAL,
        step_scope="net_reaction", origin_group_key="gate-check")
    audit = audit_hypothesis(
        hyp, states={s.state_id: s for s in states.values()})
    d, _ = decide_admission(audit, gate_decisions={
        "gate_direction_source": {"ok": False, "reason": "方向错误"}})
    assert d == ADMISSION_REJECT
    d2, _ = decide_admission(audit, gate_decisions={
        "gate_some_future_thing": {"ok": False}})
    assert d2 != ADMISSION_REJECT  # 名单外不触发


def test_admission_budget_defer_independent_reason() -> None:
    states = {s: _pstate(s) for s in (ETHANOL, O2, ACETIC_ACID, WATER)}
    hyp = _balanced_hypothesis(states)
    audit = audit_hypothesis(
        hyp, states={s.state_id: s for s in states.values()})
    d, reasons = decide_admission(
        audit, gate_decisions={}, budget_state={
            "exhausted": True, "reason": "max_total_search_actions"})
    assert d == ADMISSION_DEFER
    assert any(r.startswith("R4:") for r in reasons)


def test_admission_all_verified_expand() -> None:
    states = {s: _pstate(s) for s in (ETHANOL, O2, ACETIC_ACID, WATER)}
    hyp = _balanced_hypothesis(states)
    ctx = build_path_context(
        requested_scope=REQUESTED_SCOPE_CONDITION_COMPATIBLE,
        condition_facts=[
            build_condition_fact(key=CONDITION_KEY_OXYGEN,
                                 value="aerobic",
                                 status=FACT_STATUS_KNOWN_PRESENT)],
        accumulated_requirements=[
            build_requirement(key=CONDITION_KEY_OXYGEN, level="essential",
                              value="aerobic", source_refs=SRC)],
        assessment_scope=["oxygen_regime"])
    audit = audit_hypothesis(
        hyp, states={s.state_id: s for s in states.values()}, context=ctx)
    d, _ = decide_admission(audit, gate_decisions={
        "gate_direction_source": {"ok": True}})
    assert d == ADMISSION_EXPAND


# ---------------------------------------------------------------- D01/D02/F11


def _ethanol_co_edit_execution():
    """真实 AtomTool 协议:乙醇 C–O single→double(审核 F11 复现场景)。"""
    from pathway_v43.services.atom_tool import execute_edits, roundtrip

    render = roundtrip(ETHANOL, name="S")
    edits = [{"op": "change_bond_order",
              "atom1": "S_C_2", "atom2": "S_O_1",
              "from_order": "single", "to_order": "double"}]
    execution = execute_edits(render, edits)
    assert execution["ok"] is True
    current = {"smiles": render.smiles,
               "atom_id_map": dict(render.atom_id_map)}
    return current, edits, execution


def test_f11_donor_diagnostic_consumes_real_protocol() -> None:
    """F11 主复现:真实编辑协议下,中心在映射内 ⇒ center=True(basis)。"""
    current, edits, execution = _ethanol_co_edit_execution()
    diag = check_edit_against_donor(
        current=current,
        donor={"center_atom_ids": ["dC", "dO"]},
        alignment={"status": "resolved",
                   "donor_to_current": {"dC": "S_C_2", "dO": "S_O_1"},
                   "equivalence_classes": [], "ref": "align-f11"},
        expectation={"target_smiles": ACETALDEHYDE},
        result=execution,
        edits=edits)
    assert diag.reaction_center_match is True   # v1 在此为 None
    assert diag.center_match_basis == "direct"
    assert diag.strict_target_match is True     # CC=O == 预期
    assert diag.legacy_cn_match is True
    # 实际键变化被记录(order_change single→double,在中心内)
    kinds = {c["kind"] for c in diag.executed_bond_changes}
    assert kinds == {"order_change"}
    assert diag.missing_info_reasons == []


def test_f11_center_outside_mapping_unknown_not_partial_true() -> None:
    """F11:供体中心只映射到一半(部分中心缺映射)⇒ unknown,不部分 True。"""
    current, edits, execution = _ethanol_co_edit_execution()
    diag = check_edit_against_donor(
        current=current,
        donor={"center_atom_ids": ["dC", "dO"]},
        alignment={"status": "resolved",
                   "donor_to_current": {"dC": "S_C_2"},  # dO 缺映射
                   "equivalence_classes": [], "ref": "align-partial"},
        expectation={"target_smiles": ACETALDEHYDE},
        result=execution,
        edits=edits)
    assert diag.reaction_center_match is None  # 未知,不是 True
    assert any("partially_unmapped" in r
               for r in diag.missing_info_reasons)


def test_f11_fake_equivalence_class_rejected() -> None:
    """F11:调用方自报的非等价类(C 与 O)不被采信。"""
    current, edits, execution = _ethanol_co_edit_execution()
    diag = check_edit_against_donor(
        current=current,
        donor={"center_atom_ids": ["dC"]},
        alignment={"status": "resolved",
                   "donor_to_current": {"dC": "S_C_2"},
                   # C_2 与 O_1 在乙醇图上不同构(度数不同)⇒ 拒绝
                   "equivalence_classes": [["S_C_2", "S_O_1"]],
                   "ref": "align-fake"},
        expectation={"target_smiles": ACETALDEHYDE},
        result=execution,
        edits=edits)
    assert diag.reaction_center_match is False  # 等价类被拒后按 direct 判
    assert any("equivalence_class_rejected" in r
               for r in diag.missing_info_reasons)


def test_d01_legal_edit_deviating_from_donor_expectation() -> None:
    """D01:编辑合法且在中心内,但产物偏离预期 ⇒ strict=False 分轴报告。"""
    current, edits, execution = _ethanol_co_edit_execution()
    diag = check_edit_against_donor(
        current=current,
        donor={"center_atom_ids": ["dC", "dO"]},
        alignment={"status": "resolved",
                   "donor_to_current": {"dC": "S_C_2", "dO": "S_O_1"},
                   "equivalence_classes": [], "ref": "align-d01"},
        expectation={"target_smiles": METHYL_ACETATE},  # 不同预期目标
        result=execution,
        edits=edits)
    assert diag.strict_target_match is False  # strict 识别目标偏离
    assert diag.reaction_center_match is True  # center 分轴独立


def test_d02_symmetry_equivalent_center_via_validated_class() -> None:
    """D02:经验证的对称等价类内替换 ⇒ symmetric_equivalent,不误拒。"""
    from pathway_v43.services.atom_tool import execute_edits, roundtrip

    render = roundtrip("c1ccccc1", name="S")
    # 苯 C1-C2 单键 → 双键(Kekulé 读取后可执行;苯的 C 全对称)
    edits = [{"op": "change_bond_order",
              "atom1": "S_C_1", "atom2": "S_C_2",
              "from_order": "single", "to_order": "double"}]
    execution = execute_edits(render, edits)
    # R3 skip 清理:本环境实测该编辑可执行(Kekulé 读取后 single→
    # double 成功);"环境不可执行"skip 不保留 —— 执行失败应如实失败
    assert execution["ok"] is True, execution["reasons"]
    current = {"smiles": render.smiles,
               "atom_id_map": dict(render.atom_id_map)}
    # 供体中心只对齐到 S_C_3(与 S_C_5 在苯图上对称等价);
    # 编辑涉及 S_C_1/S_C_2 —— 用合法等价类 [S_C_1,S_C_3]/[S_C_2,S_C_5]
    # 的组合覆盖:等价类经分子图自同构验证后参与命中
    diag = check_edit_against_donor(
        current=current,
        donor={"center_atom_ids": ["dA", "dB"]},
        alignment={"status": "resolved",
                   "donor_to_current": {"dA": "S_C_3", "dB": "S_C_4"},
                   "equivalence_classes": [["S_C_1", "S_C_3", "S_C_5"],
                                           ["S_C_2", "S_C_4", "S_C_6"]],
                   "ref": "align-sym"},
        expectation={"target_smiles": execution["product_smiles"]},
        result=execution,
        edits=edits)
    assert diag.reaction_center_match is True
    assert diag.center_match_basis == "symmetric_equivalent"
    assert diag.strict_target_match is True


def test_d02_alignment_unavailable_center_unknown_others_kept() -> None:
    current, edits, execution = _ethanol_co_edit_execution()
    diag = check_edit_against_donor(
        current=current,
        donor={"center_atom_ids": ["dC", "dO"]},
        alignment={"status": "unavailable", "ref": "align-3"},
        expectation={"target_smiles": ACETALDEHYDE},
        result=execution,
        edits=edits)
    assert diag.reaction_center_match is None   # 受影响轴 unknown
    assert diag.strict_target_match is True     # 其他轴不被抹掉
    assert diag.legacy_cn_match is True
    assert any("alignment_unavailable" in r
               for r in diag.missing_info_reasons)


def test_f11_execution_failed_all_unknown() -> None:
    from pathway_v43.services.atom_tool import roundtrip

    render = roundtrip(ETHANOL, name="S")
    bad_execution = {"ok": False, "reasons": ["edit_execution_failed:x"],
                     "product_smiles": "", "product_mapped_smiles": "",
                     "atom_id_map": {}, "n_edits": 1}
    diag = check_edit_against_donor(
        current={"smiles": render.smiles,
                 "atom_id_map": dict(render.atom_id_map)},
        donor={"center_atom_ids": ["dC"]},
        alignment={"status": "resolved",
                   "donor_to_current": {"dC": "S_C_2"}, "ref": "a"},
        expectation={"target_smiles": ACETALDEHYDE},
        result=bad_execution,
        edits=[])
    assert diag.reaction_center_match is None
    assert diag.strict_target_match is None
    assert any("execution_failed" in r
               for r in diag.missing_info_reasons)


def test_f11_same_center_different_bond_op_reported() -> None:
    """同中心原子、不同键操作:break+form 重建键 ⇒ center 外无变化时
    仍按实际键变化集合判定(不是"落入允许集合即 True")。"""
    from pathway_v43.services.atom_tool import execute_edits, roundtrip

    render = roundtrip("CCOCC", name="S")  # 乙氧基乙烷
    # 真实断键:C2–O1 醚键断裂(R3 夹具修正:S_O_3 不存在,该原子 ID
    # 是 S_O_1 —— 审核对照 skip_control.json:S_C_2–S_O_1 断键成功,
    # 产物 CC.CCO;不用环境 skip 掩盖夹具错误)
    edits = [{"op": "break_bond", "atom1": "S_C_2", "atom2": "S_O_1"}]
    execution = execute_edits(render, edits)
    assert execution["ok"] is True, execution["reasons"]
    current = {"smiles": render.smiles,
               "atom_id_map": dict(render.atom_id_map)}
    diag = check_edit_against_donor(
        current=current,
        donor={"center_atom_ids": ["dC"]},
        alignment={"status": "resolved",
                   "donor_to_current": {"dC": "S_C_2"},
                   "equivalence_classes": [], "ref": "align-break"},
        expectation={"target_smiles": execution["product_smiles"]},
        result=execution,
        edits=edits)
    # 断键涉及 S_O_1,不在中心 {S_C_2} 内 ⇒ extra_changes 报告 O 侧
    assert diag.reaction_center_match is False
    assert diag.extra_changes  # 中心外变化以元素语言可读
    kinds = {c["kind"] for c in diag.executed_bond_changes}
    assert kinds == {"bond_broken"}


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
    with pytest.raises(PoolAuditError, match="顺序"):
        build_pool_audit(run_id="r", path_id="p", stages=[
            record_pool_stage(stage="bounded", input_items=[],
                              output_items=[]), stage],
            input_preview_policy=INPUT_PREVIEW_OFF)


def test_p2_5_hash_chain_continuity_enforced() -> None:
    """P2-5:相邻阶段 hash 链断裂(前输出 a、后输入 b)⇒ 拒绝。"""
    raw_out = [_pool_item(1, "curated_reaction", "E1")]
    s1 = record_pool_stage(stage="retrieved_raw", input_items=[],
                           output_items=raw_out)
    # 下一阶段输入被外部改写(不是 s1 的输出)
    tampered = [_pool_item(2, "analog_transfer", "E9")]
    s2 = record_pool_stage(stage="typed_and_grouped",
                           input_items=tampered, output_items=tampered)
    with pytest.raises(PoolAuditError, match="哈希链断裂"):
        build_pool_audit(run_id="r", path_id="p", stages=[s1, s2],
                         input_preview_policy=INPUT_PREVIEW_OFF)
    # 显式登记转换(from_previous=False + reason)⇒ 允许且留痕
    s2b = record_pool_stage(stage="typed_and_grouped",
                            input_items=tampered, output_items=tampered,
                            from_previous=False,
                            transition_reason="manual_regroup_for_test")
    record = build_pool_audit(run_id="r", path_id="p", stages=[s1, s2b],
                              input_preview_policy=INPUT_PREVIEW_OFF)
    assert record.stages[1].transition_reason == "manual_regroup_for_test"
    with pytest.raises(PoolAuditError, match="transition_reason"):
        build_pool_audit(run_id="r", path_id="p", stages=[
            s1, record_pool_stage(stage="typed_and_grouped",
                                  input_items=tampered,
                                  output_items=tampered,
                                  from_previous=False)],
            input_preview_policy=INPUT_PREVIEW_OFF)


def test_p2_5_order_pool_limit_domain() -> None:
    items = [_pool_item(1, "curated_reaction", "E1"),
             _pool_item(2, "analog_transfer", "E2")]
    with pytest.raises(PoolAuditError, match="limit 非法"):
        order_pool(items, limit=-1)   # v1 静默切片保留一部分
    kept, disclosure = order_pool(items, limit=0)  # 0 = 零预算合法
    assert kept == []
    assert disclosure["n_truncated"] == 2
    assert disclosure["covers_full_pool"] is False


def test_input_preview_off_records_not_run() -> None:
    out = run_input_preview(
        substrate_smiles="CCO", candidates=[{"smiles": "CC(=O)O"}],
        policy=INPUT_PREVIEW_OFF)
    assert out["status"] == "not_run"
    assert out["reason"] == "input_preview_policy_off"
    assert "versions" not in out


def test_input_preview_diagnostic_does_not_change_pool() -> None:
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
        _pool_item(1, "analog_transfer", "E2"),
        _pool_item(2, "biotransformation_rule", "E4"),
    ]
    ordered, disclosure = order_pool(items, limit=3)
    assert [it["evidence_id"] for it in ordered] == ["E2", "E1", "E4"]
    assert disclosure["n_truncated"] == 1
    assert disclosure["truncated_source_origins"] == {"analog_transfer": 1}
    assert disclosure["covers_full_pool"] is False
    assert disclosure["order_key_version"] == "ppv1-pool-order-2"
    _, full = order_pool(items)
    assert full["covers_full_pool"] is True
    again, _ = order_pool(list(reversed(items)), limit=3)
    assert [it["evidence_id"] for it in again] == ["E2", "E1", "E4"]


def test_pool_dedupe_rejects_cn_key_and_keeps_unkeyed() -> None:
    items = [
        _pool_item(1, "curated_reaction", "E1"),
        _pool_item(2, "curated_reaction", "E1"),
        {"retrieval_rank": 3, "source_origin": "unknown"},
    ]
    with pytest.raises(PoolAuditError, match="不得使用 CN"):
        dedupe_pool(items, dedupe_key="cn")
    kept, dups = dedupe_pool(items, dedupe_key="evidence_id")
    assert len(kept) == 2
    assert dups[0]["duplicate_of"] == "E1"


# ---------------------------------------------------------------- 底物档案


def test_substrate_profile_independent_and_all_hydrogen() -> None:
    state = build_chemical_state("C[C@H](N)C(=O)O",
                                 STRUCTURE_ORIGIN_RAW_INPUT)
    ctx = build_path_context(condition_facts=[
        build_condition_fact(key=CONDITION_KEY_PH, value=7.0,
                             status=FACT_STATUS_KNOWN_PRESENT)])
    profile = build_substrate_profile(state, ctx)
    assert profile.structure_smiles == state.smiles_isomeric
    assert profile.cn_identity == state.cn_identity
    assert profile.formal_charge == 0
    assert profile.stereo_information_status == "specified"
    # F01:与元素账同一全氢基准(C3 H7 N O2)
    assert profile.element_counts == {"C": 3, "H": 7, "N": 1, "O": 2}
    assert profile.molecular_formula == "C3H7NO2"
    assert profile.condition_keys_known == ["pH"]
    assert profile.context_ref == ctx.context_id
    assert profile.representation_fidelity["stereo"] == "as_written"


def test_substrate_profile_cn_only_state_honest() -> None:
    state = build_chemical_state_from_cn_only("CCO")
    profile = build_substrate_profile(state)
    assert profile.structure_smiles == ""
    assert profile.element_counts == {}
    assert profile.original_structure_available is False
    assert profile.representation_fidelity["formal_charge"] == "unknown"
    assert profile.representation_fidelity["protonation_basis"] == \
        "neutralized_by_cn"


def test_substrate_profile_feature_policy_validation() -> None:
    from pathway_v43.pollutant.substrate_profile import \
        SubstrateProfileError

    state = build_chemical_state("CCO", STRUCTURE_ORIGIN_RAW_INPUT)
    with pytest.raises(SubstrateProfileError, match="未知特征策略键"):
        build_substrate_profile(state, None, {"bogus_key": True})
    slim = build_substrate_profile(
        state, None, {"include_element_counts": False})
    assert slim.element_counts == {}
    assert slim.molecular_formula == "C2H6O"
