"""R5 条件与科学前提线回归(Codex R4 复审 R4-03/04/05 + R4-02 部分;v5)。

规则级合成夹具;模型 off,无金标/封存材料。先红后绿:红验证在基线
工作树(e80f459)复跑本文件;v5 实现后全绿。

R4-03:带量纲键单位未知 ⇒ unknown(不以 assumed_canonical 注记升级
satisfied);无量纲键不受影响。
R4-04:live 作用域含 scenario+phase(同阶段名不同场景不重评);快照
覆盖按具体要求签名(空快照不掩盖孤儿必要要求)。
R4-05:依赖支持按轴当前有效状态(反驳撤销该轴;再生不洗掉初始反驳;
恢复须该轴新证据)。
R4-02(条件部分):冻结 dict 封 __ior__;hypothesis requirements 嵌套
冻结。
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pathway_v43.pollutant.audit import (  # noqa: E402
    CHECK_CONDITION_CHECK,
    audit_hypothesis,
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
    CONDITION_KEY_MATRIX,
    CONDITION_KEY_OXYGEN,
    CONDITION_KEY_PH,
    CONDITION_KEY_TEMPERATURE,
    FACT_ORIGIN_CURATED_SOURCE,
    Requirement,
    aggregate_environment_fit,
    build_condition_fact,
    build_dependency,
    build_path_context,
    build_requirement,
    derive_child_context,
    detect_circular_dependencies,
    resolve_dependency,
)

SRC = ["src:rule-1"]


def f(key, value, **kw):
    return build_condition_fact(key=key, value=value,
                                status="known_present", **kw)


def r(key, value, **kw):
    return build_requirement(key=key, value=value, level="essential",
                             source_refs=SRC, **kw)


def _audit_hyp(reqs=None, deps=None):
    """(hyp, state_map):参与物状态随假设提供(audit 需完整参与物)。"""
    states = {s: build_chemical_state(s, "raw_input")
              for s in ("CCO", "CC=O", "[H][H]")}
    participants = [
        Participant(state_ref=states["CCO"].state_id, side="reactant",
                    role="primary_substrate", coefficient=1,
                    coefficient_status=COEFFICIENT_KNOWN),
        Participant(state_ref=states["CC=O"].state_id, side="product",
                    role="principal_product", coefficient=1,
                    coefficient_status=COEFFICIENT_KNOWN),
        Participant(state_ref=states["[H][H]"].state_id, side="product",
                    role="coproduct", coefficient=1,
                    coefficient_status=COEFFICIENT_KNOWN)]
    hyp = build_hypothesis(
        parent_path_id="synthetic:parent",
        substrate_state_ref=states["CCO"].state_id,
        participants=participants,
        participant_list_status=PARTICIPANT_LIST_DECLARED_COMPLETE,
        step_scope="net_reaction", origin_group_key="r5-cond",
        requirements=reqs or [], dependency_refs=deps or [])
    return hyp, {s.state_id: s for s in states.values()}


# ============================================================ R4-03 单位


def test_r4_03_source_unit_unknown_not_satisfied() -> None:
    """复审反例:curated_source 温度 25、unit=''、来源必要区间
    20–30°C ⇒ unknown + source_unit_unknown(v4 satisfied +
    assumed_canonical → audit verified → R6;注记不能把未知来源变
    verified)。"""
    ctx = build_path_context(
        condition_facts=[f(CONDITION_KEY_TEMPERATURE, 25,
                           origin=FACT_ORIGIN_CURATED_SOURCE,
                           source_ref="src:source_unit_unreported",
                           subject_scenario_ref="s")],
        phase_id="p0", scenario_ref="s",
        assessment_scope=[CONDITION_KEY_TEMPERATURE])
    hyp, state_map = _audit_hyp(
        [r(CONDITION_KEY_TEMPERATURE, {"lo": 20, "hi": 30}).to_dict()])
    audit = audit_hypothesis(hyp, states=state_map, context=ctx)
    cond = next(c for c in audit.checks
                if c.name == CHECK_CONDITION_CHECK)
    assert cond.status == "unknown"
    # per-row 理由经聚合评估可见(单位未知 ⇒ 该行 unknown)
    row = aggregate_environment_fit(
        facts=ctx.condition_facts,
        requirements=[r(CONDITION_KEY_TEMPERATURE, {"lo": 20, "hi": 30})],
        scenario_ref="s", declared_scope=[CONDITION_KEY_TEMPERATURE]
    ).per_requirement[0]
    assert row["status"] == "unknown"
    assert row["unit_basis"] == "source_unit_unknown"
    d, _ = decide_admission(audit)
    assert d != "expand"  # v4 曾 R6


def test_r4_03_explicit_canonical_unit_verified() -> None:
    """显式规范单位(°C/C/celsius)⇒ canonical + 正常比较;
    显式 K 不匹配 ⇒ unknown(既有行为)。"""
    result = aggregate_environment_fit(
        facts=[f(CONDITION_KEY_TEMPERATURE, 25, unit="°C")],
        requirements=[r(CONDITION_KEY_TEMPERATURE, {"lo": 20, "hi": 30})],
        declared_scope=[CONDITION_KEY_TEMPERATURE])
    row = {p["key"]: p for p in result.per_requirement}[
        CONDITION_KEY_TEMPERATURE]
    assert row["status"] == "satisfied"
    assert row["unit_basis"] == "canonical"
    kelvin = aggregate_environment_fit(
        facts=[f(CONDITION_KEY_TEMPERATURE, 25, unit="K")],
        requirements=[r(CONDITION_KEY_TEMPERATURE, {"lo": 20, "hi": 30})],
        declared_scope=[CONDITION_KEY_TEMPERATURE])
    row_k = {p["key"]: p for p in kelvin.per_requirement}[
        CONDITION_KEY_TEMPERATURE]
    assert row_k["status"] == "unknown"
    assert "unit_mismatch" in row_k["reason"]


def test_r4_03_dimensionless_keys_not_affected() -> None:
    """无量纲键不受单位契约影响(pH 空单位合法;oxygen/matrix 恒无
    单位;不一概判未知)。"""
    result = aggregate_environment_fit(
        facts=[f(CONDITION_KEY_PH, 7.0)],
        requirements=[r(CONDITION_KEY_PH, {"lo": 6.0, "hi": 8.0})],
        declared_scope=[CONDITION_KEY_PH])
    row = {p["key"]: p for p in result.per_requirement}[CONDITION_KEY_PH]
    assert row["status"] == "satisfied"
    result_o = aggregate_environment_fit(
        facts=[f(CONDITION_KEY_OXYGEN, "aerobic")],
        requirements=[r(CONDITION_KEY_OXYGEN, "aerobic")],
        declared_scope=[CONDITION_KEY_OXYGEN])
    row_o = {p["key"]: p for p in result_o.per_requirement}[
        CONDITION_KEY_OXYGEN]
    assert row_o["status"] == "satisfied"
    assert "unit_basis" not in row_o  # 无量纲键不带注记
    result_m = aggregate_environment_fit(
        facts=[f(CONDITION_KEY_MATRIX, "sandy soil")],
        requirements=[r(CONDITION_KEY_MATRIX, "soil")],
        declared_scope=[CONDITION_KEY_MATRIX])
    row_m = {p["key"]: p for p in result_m.per_requirement}[
        CONDITION_KEY_MATRIX]
    assert row_m["status"] == "unknown"  # matrix 无语义关系(R3-12 保持)


# ============================================================ R4-04 作用域


def _phase_case(old_required, new_phase):
    """R4-04 复审探针场景:sA:p0 有氧旧边 → 显式转 sB:<new_phase>,
    新候选无氧要求(合法两行语义)。"""
    facts = [
        f(CONDITION_KEY_OXYGEN, "aerobic", phase_id="p0",
          subject_scenario_ref="sA"),
        f(CONDITION_KEY_OXYGEN, "anaerobic", phase_id="p0",
          subject_scenario_ref="sB"),
        f(CONDITION_KEY_OXYGEN, "anaerobic", phase_id="p1",
          subject_scenario_ref="sB")]
    parent = build_path_context(
        condition_facts=facts, phase_id="p0", scenario_ref="sA",
        accumulated_requirements=[r(CONDITION_KEY_OXYGEN, old_required)],
        assessment_scope=[CONDITION_KEY_OXYGEN])
    child = derive_child_context(
        parent, step_requirements=[r(CONDITION_KEY_OXYGEN, "anaerobic")],
        scenario_transition={"new_phase_id": new_phase,
                             "new_scenario_ref": "sB",
                             "source_ref": "user:synthetic_transition"})
    return parent, child


def test_r4_04_same_local_phase_different_scenario_not_reevaluated() -> None:
    """复审反例:转 sB:p0(阶段同名、场景不同)—— 旧有氧要求不被
    sB 无氧事实重评出 conflict(v4 conflict → defer);行为与转
    sB:p1 一致(接口允许只转 scenario,不强迫改阶段名规避)。"""
    parent, child = _phase_case("aerobic", "p0")
    assert child.current_step_assessment().environment_fit == "compatible"
    assert child.route_assessment().environment_fit == "compatible"
    # 对照:p1 行为一致
    _, child_p1 = _phase_case("aerobic", "p1")
    assert child_p1.route_assessment().environment_fit == \
        child.route_assessment().environment_fit


def test_r4_04_old_edge_conflict_preserved() -> None:
    """控制:旧边真实冲突(旧要求与 sA 事实冲突)在路线中保持
    (转 sB 不洗掉旧边 conflict)。"""
    _, child = _phase_case("anaerobic", "p1")
    assert child.route_assessment().environment_fit == "conflict"


def test_r4_04_audit_consumes_candidate_semantics_same_phase() -> None:
    """audit→admission 全链:同阶段名转场景后的合法路线不 conflict/
    不 defer(v4 曾 defer/R3 错杀)。"""
    _, child = _phase_case("aerobic", "p0")
    hyp, state_map = _audit_hyp(
        [r(CONDITION_KEY_OXYGEN, "anaerobic").to_dict()])
    audit = audit_hypothesis(hyp, states=state_map, context=child)
    cond = next(c for c in audit.checks
                if c.name == CHECK_CONDITION_CHECK)
    assert cond.status == "verified"
    d, _ = decide_admission(audit)
    assert d != "defer"


def test_r4_04_empty_snapshot_cannot_cover_orphan_requirement() -> None:
    """复审反例:父 p0 无必要要求;转 p1 时带入已绑定 p0/缺失旧边的
    essential pH 6–8 ⇒ 父快照空(has_gate_requirements=False)不得
    把该必要要求当已覆盖从评估中消失(v4 audit verified → R6);
    有无空快照都应显式 unknown。"""
    parent = build_path_context(
        condition_facts=[f(CONDITION_KEY_OXYGEN, "aerobic")],
        phase_id="p0", scenario_ref="s",
        assessment_scope=[CONDITION_KEY_OXYGEN, CONDITION_KEY_PH])
    foreign = Requirement(**{
        **r(CONDITION_KEY_PH, {"lo": 6, "hi": 8}).to_dict(),
        "introduced_phase_id": "p0", "introduced_scenario_ref": "s",
        "introduced_edge": "hyp:missing_older_edge"})
    child = derive_child_context(
        parent, step_requirements=[foreign],
        scenario_transition={"new_phase_id": "p1",
                             "source_ref": "user:synthetic_transition"},
        step_edge_ref="hyp:new")
    hyp, state_map = _audit_hyp(
        [r(CONDITION_KEY_OXYGEN, "aerobic").to_dict()])

    def _check(ctx):
        audit = audit_hypothesis(hyp, states=state_map, context=ctx)
        cond = next(c for c in audit.checks
                    if c.name == CHECK_CONDITION_CHECK)
        return audit, cond

    audit, cond = _check(child)
    assert cond.status == "unknown"  # 孤儿 pH ⇒ 显式未知
    d, _ = decide_admission(audit)
    assert d != "expand"  # v4 曾 R6
    # 无快照对照:同样孤儿 unknown(行为一致,快照有无不改变结论)。
    # R6(R5-04)更动说明:原对照就地 child.phase_history = [] 后再走
    # audit —— 就地删除快照属于内容身份篡改,audit 入口现在按
    # context_content_identity_mismatch 结构化拒绝(该拒绝行为由
    # test_ppv1_r6_conditions.py 钉住);本对照改为经 build_path_context
    # 合法构造等价无快照上下文(p1 场景 + 同一 p0 绑定孤儿要求),
    # 保留原控制语义"孤儿 ⇒ 显式 unknown,不依赖快照存在"。
    orphan_ctx = build_path_context(
        condition_facts=[f(CONDITION_KEY_OXYGEN, "aerobic")],
        phase_id="p1", scenario_ref="s",
        accumulated_requirements=[foreign],
        assessment_scope=[CONDITION_KEY_OXYGEN, CONDITION_KEY_PH])
    _, cond2 = _check(orphan_ctx)
    assert cond2.status == "unknown"


def test_r4_04_covered_requirement_not_orphan() -> None:
    """控制:快照**按签名**承载过的要求不进孤儿(旧边结论由快照
    保留,不重评也不消失)。"""
    parent = build_path_context(
        condition_facts=[f(CONDITION_KEY_OXYGEN, "aerobic")],
        phase_id="p0", scenario_ref="sA",
        accumulated_requirements=[r(CONDITION_KEY_OXYGEN, "aerobic")],
        assessment_scope=[CONDITION_KEY_OXYGEN])
    child = derive_child_context(
        parent, scenario_transition={"new_phase_id": "p1",
                                     "new_scenario_ref": "sB",
                                     "source_ref": "user:t"})
    # 旧要求被 (sA,p0) 快照按签名覆盖:非 live、非孤儿,
    # 路线结果 = 快照记录值(旧氧要求 satisfied 记录在快照行)
    assert child.route_assessment().environment_fit == "compatible"
    per = child.route_assessment().per_requirement
    assert any(p["key"] == CONDITION_KEY_OXYGEN
               and p["status"] == "satisfied" for p in per)


# ============================================================ R4-05 依赖


def _cycle_dep(statement):
    return build_dependency(kind="cosubstrate_supply", statement=statement)


def test_r4_05_contradiction_revokes_axis_support() -> None:
    """复审反例:initial_supply supported → 该轴 contradicted → 仅
    regeneration supported ⇒ 轴状态 {initial: contradicted, regen:
    supported};总体 contradicted;audit 不可当已解决进 R6(v4 状态
    supported、support_axes 永久保留初始支持)。"""
    dep = _cycle_dep("supplies:A:B")
    regen = resolve_dependency(
        dep, new_evidence=["src:regen"], resolution="supported",
        support_axis="regeneration")
    initial = resolve_dependency(
        regen, new_evidence=["src:startup"], resolution="supported",
        support_axis="initial_supply")
    initial_negated = resolve_dependency(
        initial, new_evidence=["src:startup_absent"],
        resolution="contradicted", support_axis="initial_supply")
    later_regen = resolve_dependency(
        initial_negated, new_evidence=["src:regen_again"],
        resolution="supported", support_axis="regeneration")
    # 轴状态:initial 当前 contradicted(反驳撤销该轴支持)
    assert "initial_supply" not in later_regen.support_axes
    assert "regeneration" in later_regen.support_axes
    assert later_regen.status == "contradicted"  # 任一轴矛盾 ⇒ 总体矛盾
    ctx = build_path_context(
        condition_facts=[f(CONDITION_KEY_OXYGEN, "aerobic")],
        assessment_scope=[CONDITION_KEY_OXYGEN],
        dependencies=[later_regen])
    hyp, state_map = _audit_hyp(
        [r(CONDITION_KEY_OXYGEN, "aerobic").to_dict()])
    audit = audit_hypothesis(hyp, states=state_map, context=ctx)
    d, _ = decide_admission(audit)
    assert d != "expand"  # v4 曾 R6(all_dependency_refs_reported_resolved)


def test_r4_05_circular_unresolved_initial_supply_after_contradiction():
    """环诊断:反驳后仅再生支持 ⇒ unresolved_initial_supply(启动
    供给轴当前无支持);普通正控制(初始+再生都支持)不回退。"""
    dep = _cycle_dep("supplies:A:B")
    dep_b = _cycle_dep("supplies:B:A")
    regen_a = resolve_dependency(
        dep, new_evidence=["src:regen"], resolution="supported",
        support_axis="regeneration")
    regen_b = resolve_dependency(
        dep_b, new_evidence=["src:regen"], resolution="supported",
        support_axis="regeneration")
    initial = resolve_dependency(
        regen_a, new_evidence=["src:startup"], resolution="supported",
        support_axis="initial_supply")
    negated = resolve_dependency(
        initial, new_evidence=["src:absent"], resolution="contradicted",
        support_axis="initial_supply")
    after = resolve_dependency(
        negated, new_evidence=["src:regen_again"], resolution="supported",
        support_axis="regeneration")
    # 正控制:初始+再生 ⇒ has_initial
    ok = detect_circular_dependencies([initial, regen_b])
    assert [initial.dependency_id, regen_b.dependency_id] and \
        ok["unresolved_initial_supply"] == []
    # 反驳后仅再生 ⇒ unresolved_initial_supply(不被再生洗掉)
    bad = detect_circular_dependencies([after, regen_b])
    assert bad["unresolved_initial_supply"]  # 复审:启动未知被清空过


def test_r4_05_axis_restore_requires_axis_evidence() -> None:
    """恢复某轴须**该轴**新证据:initial 反驳后再加 initial 的
    supported ⇒ 该轴恢复、总体 supported;仅再生支持不恢复该轴。"""
    dep = _cycle_dep("supplies:A:B")
    regen = resolve_dependency(
        dep, new_evidence=["src:regen"], resolution="supported",
        support_axis="regeneration")
    initial = resolve_dependency(
        regen, new_evidence=["src:startup"], resolution="supported",
        support_axis="initial_supply")
    negated = resolve_dependency(
        initial, new_evidence=["src:absent"], resolution="contradicted",
        support_axis="initial_supply")
    # 再生支持不恢复 initial 轴
    after_regen = resolve_dependency(
        negated, new_evidence=["src:regen2"], resolution="supported",
        support_axis="regeneration")
    assert "initial_supply" not in after_regen.support_axes
    assert after_regen.status == "contradicted"
    # initial 轴新证据 ⇒ 恢复
    restored = resolve_dependency(
        after_regen, new_evidence=["src:startup2"],
        resolution="supported", support_axis="initial_supply")
    assert "initial_supply" in restored.support_axes
    assert restored.status == "supported"


def test_r4_05_positive_control_initial_then_regen_supported():
    """正控制:initial_supply supported → regeneration supported ⇒
    两轴都在、总体 supported(启动未知不回退,R3 行为保留)。"""
    dep = _cycle_dep("supplies:A:B")
    initial = resolve_dependency(
        dep, new_evidence=["src:startup"], resolution="supported",
        support_axis="initial_supply")
    both = resolve_dependency(
        initial, new_evidence=["src:regen"], resolution="supported",
        support_axis="regeneration")
    assert set(both.support_axes) == {"initial_supply", "regeneration"}
    assert both.status == "supported"


def test_r4_05_axis_status_disclosed() -> None:
    """dependency_states 披露逐轴当前有效状态(axis_status)。"""
    dep = _cycle_dep("supplies:A:B")
    initial = resolve_dependency(
        dep, new_evidence=["src:s"], resolution="supported",
        support_axis="initial_supply")
    ctx = build_path_context(
        condition_facts=[f(CONDITION_KEY_OXYGEN, "aerobic")],
        dependencies=[initial])
    states = ctx.dependency_states()
    info = states[initial.dependency_id]
    assert info["axis_status"] == {"initial_supply": "supported"}
    assert info["support_axes"] == ["initial_supply"]


# ==================================================== R4-02 载荷不可变


def test_r4_02_frozen_value_dict_ior_blocked() -> None:
    """复审反例:冻结区间 dict 的 `|=` 就地合并不经 __setitem__(v4
    静默改必要区间、context_id 不变、defer→R6)⇒ TypeError。"""
    parent = build_path_context(
        condition_facts=[f(CONDITION_KEY_TEMPERATURE, 25, unit="C")],
        accumulated_requirements=[
            r(CONDITION_KEY_TEMPERATURE, {"lo": 40, "hi": 50})],
        assessment_scope=[CONDITION_KEY_TEMPERATURE])
    before = parent.route_assessment().environment_fit
    value_alias = parent.accumulated_requirements[0].value
    with pytest.raises(TypeError, match="冻结"):
        value_alias |= {"lo": 20, "hi": 30}
    # 修改被拒 ⇒ 评估与身份不变
    assert parent.accumulated_requirements[0].value == {"lo": 40, "hi": 50}
    assert parent.route_assessment().environment_fit == before


def test_r4_02_hypothesis_requirements_nested_frozen() -> None:
    """复审反例:hypothesis 自身 requirements 嵌套 value 的就地修改
    (update/setitem/嵌套改写)⇒ TypeError(v4 改科学前提而
    hypothesis_id 保留);入口复算由 store 侧回归覆盖。"""
    hyp, _sm = _audit_hyp(
        [r(CONDITION_KEY_TEMPERATURE, {"lo": 40, "hi": 50}).to_dict()])
    with pytest.raises(TypeError, match="冻结"):
        hyp.requirements[0]["value"].update(lo=20, hi=30)
    with pytest.raises(TypeError, match="冻结"):
        hyp.requirements[0]["value"]["lo"] = 20
    with pytest.raises(TypeError, match="冻结"):
        hyp.requirements[0]["level"] = "preference"
    # to_dict 输出普通可变副本(载荷路径不变)
    payload = hyp.to_dict()
    assert payload["requirements"][0]["value"] == {"lo": 40, "hi": 50}
    payload["requirements"][0]["value"]["lo"] = 20  # 可变副本不抛
    assert hyp.requirements[0]["value"] == {"lo": 40, "hi": 50}
