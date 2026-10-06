"""R2 复审条件/科学前提线第三轮回修回归(Codex R2-04/05/06/07 + P2)。

全部合成夹具;先红后绿:本文件各断言对应 R2 复审反例或 P2 表项,
在未修复代码上失败,修复后转绿。既有 v2 正确语义(F02 固定场景、
C01–C06、known_absent 同实体冲突、无源 essential、optimum 偏离、
mesophilic unknown)保留在原测试文件,不在此重复。
"""

from __future__ import annotations

import sys
from fractions import Fraction
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pathway_v43.pollutant.chemstate import (  # noqa: E402
    STRUCTURE_ORIGIN_RAW_INPUT,
    STRUCTURE_ORIGIN_SOURCE_PRODUCT,
    build_chemical_state,
)
from pathway_v43.pollutant.hypothesis import (  # noqa: E402
    COEFFICIENT_KNOWN,
    PARTICIPANT_LIST_DECLARED_COMPLETE,
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
    ConditionContractError,
    PathContext,
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
from pathway_v43.pollutant.store import PollutantPathwayStore  # noqa: E402

SRC = ["src:synthetic-r3"]


def f(key, value, **kw):
    return build_condition_fact(key=key, value=value,
                                status="known_present", **kw)


def r(key, value, **kw):
    return build_requirement(key=key, value=value, level="essential",
                             source_refs=SRC, **kw)


def per_key(result):
    return {p["key"]: p for p in result.per_requirement}


# ================================================================ R2-04


def test_r2_04_requirement_binds_introducing_phase_scenario_edge() -> None:
    """要求引入时的 phase/scenario/边绑定随要求保存(R2-04)。"""
    facts = [f(CONDITION_KEY_OXYGEN, "aerobic", phase_id="p0",
               subject_scenario_ref="s")]
    root = build_path_context(
        condition_facts=facts, phase_id="p0", scenario_ref="s",
        accumulated_requirements=[r(CONDITION_KEY_OXYGEN, "aerobic")])
    bound = root.accumulated_requirements[0]
    assert bound.introduced_phase_id == "p0"
    assert bound.introduced_scenario_ref == "s"
    child = derive_child_context(
        root, step_requirements=[r(CONDITION_KEY_OXYGEN, "anaerobic")],
        step_edge_ref="hyp:edge-1")
    new_req = [q for q in child.accumulated_requirements
               if q.value == "anaerobic"][0]
    assert new_req.introduced_phase_id == "p0"   # 同阶段派生:绑定当前阶段
    assert new_req.introduced_edge == "hyp:edge-1"
    # 历史要求绑定不被追改
    assert bound.introduced_phase_id == "p0"
    assert bound.introduced_edge == ""


def test_r2_04_phase_transition_no_false_conflict() -> None:
    """p0 有氧相容 → 显式转 p1 无氧 + 无氧要求:不得拿 p1 事实重评
    旧有氧要求而假冲突(R2-04 反例 phase_transition_false_conflict)。"""
    facts = [f(CONDITION_KEY_OXYGEN, "aerobic", phase_id="p0",
               subject_scenario_ref="s"),
             f(CONDITION_KEY_OXYGEN, "anaerobic", phase_id="p1",
               subject_scenario_ref="s")]
    root = build_path_context(
        condition_facts=facts, phase_id="p0", scenario_ref="s",
        accumulated_requirements=[r(CONDITION_KEY_OXYGEN, "aerobic")],
        assessment_scope=[CONDITION_KEY_OXYGEN])
    assert root.assessed_scope == "condition_compatible"
    child = derive_child_context(
        root, step_requirements=[r(CONDITION_KEY_OXYGEN, "anaerobic")],
        scenario_transition={"new_phase_id": "p1",
                             "source_ref": "user:explicit_transition"})
    # 路线聚合:逐边合取,旧有氧要求按 p0 事实评估 → satisfied;
    # 新无氧要求按 p1 事实评估 → satisfied ⇒ 路线相容,不是 conflicted
    assert child.assessed_scope == "condition_compatible"
    route = child.route_assessment()
    assert route.environment_fit == "compatible"
    by_req = {(p["key"], p["reason"]) for p in route.per_requirement}
    assert ("oxygen_regime", "value_match:oxygen_regime") in by_req
    # 本步(p1 边)单独评估:相容,与路线分层呈现
    step = child.current_step_assessment()
    assert step.environment_fit == "compatible"
    assert all(p["introduced_phase_id"] == "p1"
               for p in step.per_requirement)


def test_r2_04_phase_transition_keeps_past_conflict() -> None:
    """p0 无氧要求×有氧事实已冲突 → 转 p1 无氧:路线仍 conflicted,
    历史快照保留(R2-04 反例 phase_transition_erases_past_conflict)。"""
    facts = [f(CONDITION_KEY_OXYGEN, "aerobic", phase_id="p0",
               subject_scenario_ref="s"),
             f(CONDITION_KEY_OXYGEN, "anaerobic", phase_id="p1",
               subject_scenario_ref="s")]
    root = build_path_context(
        condition_facts=facts, phase_id="p0", scenario_ref="s",
        accumulated_requirements=[r(CONDITION_KEY_OXYGEN, "anaerobic")],
        assessment_scope=[CONDITION_KEY_OXYGEN])
    assert root.assessed_scope == "conflicted"
    child = derive_child_context(
        root, scenario_transition={"new_phase_id": "p1",
                                   "source_ref": "user:explicit_transition"})
    # 路线聚合按选定边:旧边冲突保持,不被转换洗掉
    assert child.assessed_scope == "conflicted"
    assert child.route_assessment().environment_fit == "conflict"
    # 转换边本身(p1)无要求:本步不自动相容,与路线分层呈现
    assert child.current_step_assessment().environment_fit == "unknown"
    # 历史快照:冻结 p0 评估,含 per_requirement 与来源
    assert len(child.phase_history) == 1
    snap = child.phase_history[0]
    assert snap["phase_id"] == "p0"
    assert snap["environment_fit"] == "conflict"
    assert snap["snapshot_basis"] == "scenario_transition"
    assert snap["source_ref"] == "user:explicit_transition"
    assert any(p["status"] == "conflict" for p in snap["per_requirement"])
    # 父对象不被追改
    assert root.assessed_scope == "conflicted"
    assert root.phase_history == []


def test_r2_04_transition_only_affects_subsequent_not_reaction_edge() -> None:
    """转换只影响后续步骤;阶段转换不写成反应边(留在
    scenario_transition/phase_history,不产生参与物或事件)。"""
    root = build_path_context(
        condition_facts=[f(CONDITION_KEY_TEMPERATURE, 25.0)],
        accumulated_requirements=[
            r(CONDITION_KEY_TEMPERATURE, {"lo": 20, "hi": 30})],
        assessment_scope=[CONDITION_KEY_TEMPERATURE])
    child = derive_child_context(root, scenario_transition={
        "new_phase_id": "p1", "source_ref": "user:switch"})
    assert child.scenario_transition["new_phase_id"] == "p1"
    assert child.phase_id == "p1"
    # 转换不是反应边:子上下文不新增参与物/假设/事件(只有上下文对象)
    assert not hasattr(child, "participants")
    # 后续步骤语义:旧阶段事实(空 phase_id 除外)对新阶段不适用
    assert child.current_step_assessment().environment_fit == "unknown"


def test_r2_04_branch_isolation_requirement_objects() -> None:
    """分支不共享可变要求对象(R2-04 反例 requirement_branch_alias):
    改 A 分支温度要求字典不得影响 parent 与 B 分支结果。"""
    parent = build_path_context(
        condition_facts=[f(CONDITION_KEY_TEMPERATURE, 25)],
        accumulated_requirements=[
            r(CONDITION_KEY_TEMPERATURE, {"lo": 20, "hi": 30})],
        assessment_scope=[CONDITION_KEY_TEMPERATURE])
    branch_a = derive_child_context(parent)
    branch_b = derive_child_context(parent)
    assert parent.assessed_scope == "condition_compatible"
    assert branch_a.accumulated_requirements[0] \
        is not parent.accumulated_requirements[0]
    # 深隔离:改 A 的要求值(区间字典)只影响 A
    branch_a.accumulated_requirements[0].value["lo"] = 40
    branch_a.accumulated_requirements[0].value["hi"] = 50
    assert parent.assessed_scope == "condition_compatible"
    assert branch_b.assessed_scope == "condition_compatible"
    assert branch_a.assessed_scope == "conflicted"
    # parent 语义对象未被改动
    assert parent.accumulated_requirements[0].value == {"lo": 20, "hi": 30}
    # 要求对象不可属性赋值(frozen)
    with pytest.raises(Exception):
        parent.accumulated_requirements[0].level = "preference"


def test_r2_04_fact_and_dependency_objects_isolated() -> None:
    """事实/依赖同样不可变隔离:子上下文事实列表不与父共享对象。"""
    parent = build_path_context(
        condition_facts=[f(CONDITION_KEY_TEMPERATURE, 25)])
    child = derive_child_context(parent)
    assert child.condition_facts[0] is not parent.condition_facts[0]
    with pytest.raises(Exception):
        parent.condition_facts[0].value = 99
    dep = build_dependency(kind="mechanism", statement="synthetic")
    with pytest.raises(Exception):
        dep.status = "supported"
    # context_id 继续覆盖全部语义字段:阶段历史不同 ⇒ 不同身份
    other = derive_child_context(parent, scenario_transition={
        "new_phase_id": "p9", "source_ref": "user:x"})
    assert other.context_id != child.context_id


def test_r2_04_current_step_vs_route_two_layers() -> None:
    """本步相容与全路线相容分开呈现(两个字段/两层 API)。"""
    root = build_path_context(
        condition_facts=[f(CONDITION_KEY_TEMPERATURE, 45, phase_id="p0")],
        phase_id="p0",
        accumulated_requirements=[
            r(CONDITION_KEY_TEMPERATURE, {"lo": 20, "hi": 30})],
        assessment_scope=[CONDITION_KEY_TEMPERATURE])
    child = derive_child_context(root, scenario_transition={
        "new_phase_id": "p1", "source_ref": "user:t"},
        step_requirements=[
            r(CONDITION_KEY_TEMPERATURE, {"lo": 40, "hi": 50})])
    # 本步(p1,40–50 × 无 p1 事实)unknown;路线(p0 冲突)conflict
    assert child.current_step_assessment().environment_fit == "unknown"
    assert child.assessed_scope == "conflicted"
    # 对照:无阶段限定事实按语义对全部阶段适用(本步按当前事实评估)
    root2 = build_path_context(
        condition_facts=[f(CONDITION_KEY_TEMPERATURE, 45)],
        accumulated_requirements=[
            r(CONDITION_KEY_TEMPERATURE, {"lo": 20, "hi": 30})],
        assessment_scope=[CONDITION_KEY_TEMPERATURE])
    child2 = derive_child_context(root2, scenario_transition={
        "new_phase_id": "p1", "source_ref": "user:t"},
        step_requirements=[
            r(CONDITION_KEY_TEMPERATURE, {"lo": 40, "hi": 50})])
    assert child2.current_step_assessment().environment_fit == "compatible"
    assert child2.assessed_scope == "conflicted"  # 路线仍保持旧边冲突


def test_r2_04_context_json_roundtrip_v3() -> None:
    """PathContext v3 往返(含新字段);未知版本拒绝。"""
    facts = [f(CONDITION_KEY_OXYGEN, "aerobic", phase_id="p0",
               subject_scenario_ref="s")]
    root = build_path_context(
        condition_facts=facts, phase_id="p0", scenario_ref="s",
        accumulated_requirements=[r(CONDITION_KEY_OXYGEN, "aerobic")],
        assessment_scope=[CONDITION_KEY_OXYGEN])
    child = derive_child_context(
        root, scenario_transition={"new_phase_id": "p1",
                                   "source_ref": "user:t"})
    d = child.to_dict()
    assert d["schema_version"] == "ppv1-context-4"
    restored = PathContext.from_dict(d)
    assert restored.context_id == child.context_id
    assert restored.phase_history == child.phase_history
    assert restored.route_assessment().environment_fit == \
        child.route_assessment().environment_fit
    bad = dict(d)
    bad["schema_version"] = "ppv1-context-999"
    with pytest.raises(ConditionContractError, match="版本未知"):
        PathContext.from_dict(bad)


# ================================================================ R2-05


def test_r2_05_point_inside_interval_unknown() -> None:
    """事实区间 [6.8,7.2] × 必需点 7.0 → unknown(实际点值不确定),
    独立理由码 point_in_uncertain_range(不复用区间判据码)。"""
    result = aggregate_environment_fit(
        facts=[f(CONDITION_KEY_PH, {"lo": 6.8, "hi": 7.2})],
        requirements=[r(CONDITION_KEY_PH, 7.0, value_basis="point")],
        declared_scope=[CONDITION_KEY_PH])
    assert result.environment_fit == "unknown"
    row = per_key(result)[CONDITION_KEY_PH]
    assert row["status"] == "unknown"
    assert "point_in_uncertain_range" in row["reason"]
    assert "range_disjoint_or_outside" not in row["reason"]


def test_r2_05_degenerate_interval_point_satisfied() -> None:
    """退化区间 [7,7] × 必需点 7 → satisfied。"""
    result = aggregate_environment_fit(
        facts=[f(CONDITION_KEY_PH, {"lo": 7.0, "hi": 7.0})],
        requirements=[r(CONDITION_KEY_PH, 7.0, value_basis="point")],
        declared_scope=[CONDITION_KEY_PH])
    row = per_key(result)[CONDITION_KEY_PH]
    assert row["status"] == "satisfied"
    assert result.environment_fit == "compatible"


def test_r2_05_point_outside_interval_conflict_distinct_reason() -> None:
    """点 ∉ 事实区间 [8,9] → conflict,理由码 point_outside_interval。"""
    result = aggregate_environment_fit(
        facts=[f(CONDITION_KEY_PH, {"lo": 8.0, "hi": 9.0})],
        requirements=[r(CONDITION_KEY_PH, 7.0, value_basis="point")],
        declared_scope=[CONDITION_KEY_PH])
    row = per_key(result)[CONDITION_KEY_PH]
    assert row["status"] == "conflict"
    assert "point_outside_interval" in row["reason"]
    assert "range_disjoint_or_outside" not in row["reason"]


def test_r2_05_kelvin_unit_not_compared_as_celsius() -> None:
    """temperature_C 事实 unit=K ⇒ 结构化 unknown(unit_mismatch),
    不得按 25 当 °C 比较;显式 °C 单位照常比较(首版无 K→°C 换算)。"""
    result = aggregate_environment_fit(
        facts=[f(CONDITION_KEY_TEMPERATURE, 25, unit="K")],
        requirements=[r(CONDITION_KEY_TEMPERATURE, {"lo": 20, "hi": 30})],
        declared_scope=[CONDITION_KEY_TEMPERATURE])
    assert result.environment_fit == "unknown"
    row = per_key(result)[CONDITION_KEY_TEMPERATURE]
    assert row["status"] == "unknown"
    assert "unit_mismatch" in row["reason"]
    ok = aggregate_environment_fit(
        facts=[f(CONDITION_KEY_TEMPERATURE, 25, unit="°C")],
        requirements=[r(CONDITION_KEY_TEMPERATURE, {"lo": 20, "hi": 30})],
        declared_scope=[CONDITION_KEY_TEMPERATURE])
    assert ok.environment_fit == "compatible"


def test_r2_05_unrelated_entity_absence_not_conflict() -> None:
    """acetate known_absent 与必需 NADH 无关:NADH 状态未知,
    不是 conflict(实体缺席按实体身份匹配,R2-05)。"""
    result = aggregate_environment_fit(
        facts=[build_condition_fact(
            key=CONDITION_KEY_ELECTRON_DONOR, value="acetate",
            status="known_absent")],
        requirements=[r(CONDITION_KEY_ELECTRON_DONOR, "NADH")],
        declared_scope=[CONDITION_KEY_ELECTRON_DONOR])
    assert result.environment_fit == "unknown"
    row = per_key(result)[CONDITION_KEY_ELECTRON_DONOR]
    assert row["status"] == "unknown"


def test_r2_05_multiple_known_donors_coexist() -> None:
    """多种已知供体并存:事实集不得按键 last-wins;
    NADH+acetate 都 present × 必需 NADH → satisfied。"""
    result = aggregate_environment_fit(
        facts=[f(CONDITION_KEY_ELECTRON_DONOR, "NADH"),
               f(CONDITION_KEY_ELECTRON_DONOR, "acetate",
                 source_ref="src:other")],
        requirements=[r(CONDITION_KEY_ELECTRON_DONOR, "NADH")],
        declared_scope=[CONDITION_KEY_ELECTRON_DONOR])
    row = per_key(result)[CONDITION_KEY_ELECTRON_DONOR]
    assert row["status"] == "satisfied"
    assert result.environment_fit == "compatible"


def test_r2_05_same_entity_known_absent_still_conflicts() -> None:
    """必需实体自身 known_absent ⇒ conflict(F03 语义保留)。"""
    result = aggregate_environment_fit(
        facts=[build_condition_fact(
            key=CONDITION_KEY_ELECTRON_DONOR, value="NADH",
            status="known_absent")],
        requirements=[r(CONDITION_KEY_ELECTRON_DONOR, "NADH")],
        declared_scope=[CONDITION_KEY_ELECTRON_DONOR])
    row = per_key(result)[CONDITION_KEY_ELECTRON_DONOR]
    assert row["status"] == "conflict"


def test_r2_05_species_requirement_other_entity_present_unknown() -> None:
    """物种键:必需实体无自身事实,另一实体 present 不证明其缺席
    (不可解析/未匹配实体引用 → unknown 而非 conflict)。"""
    result = aggregate_environment_fit(
        facts=[f(CONDITION_KEY_ELECTRON_DONOR, "acetate")],
        requirements=[r(CONDITION_KEY_ELECTRON_DONOR, "NADH")],
        declared_scope=[CONDITION_KEY_ELECTRON_DONOR])
    row = per_key(result)[CONDITION_KEY_ELECTRON_DONOR]
    assert row["status"] == "unknown"


def test_r2_05_oxygen_enum_mismatch_still_conflict() -> None:
    """枚举键(oxygen_regime 封闭集)字符串不匹配仍 conflict
    (不得为过测试把所有字符串改 unknown;C02 语义)。"""
    result = aggregate_environment_fit(
        facts=[f(CONDITION_KEY_OXYGEN, "anaerobic")],
        requirements=[r(CONDITION_KEY_OXYGEN, "aerobic")],
        declared_scope=[CONDITION_KEY_OXYGEN])
    row = per_key(result)[CONDITION_KEY_OXYGEN]
    assert row["status"] == "conflict"
    assert result.environment_fit == "conflict"


def test_r2_05_label_basis_only_for_interval_keys() -> None:
    """label basis 定案:仅区间键走注册表(空 ⇒ unknown);
    物种/枚举键不走 label/注册表,走实体/枚举比对(理由码可区分)。"""
    # 区间键 label:注册表为空 ⇒ unknown(保留 mesophilic 语义)
    label_req = r(CONDITION_KEY_TEMPERATURE, "mesophilic")
    assert label_req.value_basis == "label"
    result = aggregate_environment_fit(
        facts=[f(CONDITION_KEY_TEMPERATURE, 25.0)],
        requirements=[label_req],
        declared_scope=[CONDITION_KEY_TEMPERATURE])
    row = per_key(result)[CONDITION_KEY_TEMPERATURE]
    assert row["status"] == "unknown"
    assert "label_without_registered_range" in row["reason"]
    # 物种键字符串:entity 比对,不是 label
    donor_req = r(CONDITION_KEY_ELECTRON_DONOR, "NADH")
    assert donor_req.value_basis == "entity"
    # 枚举键字符串:entity 比对,不是 label
    oxy_req = r(CONDITION_KEY_OXYGEN, "aerobic")
    assert oxy_req.value_basis == "entity"


# ================================================================ R2-06


def test_r2_06_regeneration_only_cycle_keeps_startup_unknown() -> None:
    """A→B→C→A 三条再生关系全部 supported、无初始池证据 ⇒
    unresolved_initial_supply 保留(不称化学不可能,不自动 reject)。"""
    deps = [build_dependency(kind="cosubstrate_supply", statement=s)
            for s in ("supplies:A:B", "supplies:B:C", "supplies:C:A")]
    resolved = [
        resolve_dependency(d, new_evidence=[f"src:regeneration:{i}"],
                           resolution="supported",
                           support_axis="regeneration",
                           note="再生观察;无初始池证据")
        for i, d in enumerate(deps)]
    result = detect_circular_dependencies(resolved)
    assert result["cycles"] == [["A", "B", "C"]]
    assert result["unresolved_initial_supply"] == [["A", "B", "C"]]
    assert "不称化学不可能" in result["note"]


def test_r2_06_initial_supply_evidence_resolves_startup_unknown() -> None:
    """补可追溯初始供给证据(support_axis=initial_supply)才解决
    启动未知;仅再生/反应支持不解决。"""
    deps = [build_dependency(kind="cosubstrate_supply", statement=s)
            for s in ("supplies:A:B", "supplies:B:C", "supplies:C:A")]
    regenerated = [
        resolve_dependency(d, new_evidence=["src:regen"],
                           resolution="supported",
                           support_axis="regeneration")
        for d in deps]
    seeded = resolve_dependency(
        regenerated[0], new_evidence=["src:inoculation"],
        resolution="supported", support_axis="initial_supply",
        note="接种初始池,可追溯")
    result = detect_circular_dependencies(
        [seeded] + regenerated[1:])
    assert result["unresolved_initial_supply"] == []
    # 轨迹保留两次解决(再生 + 初始供给),轴可追溯
    assert [e["support_axis"] for e in seeded.resolution_log] == \
        ["regeneration", "initial_supply"]


def test_r2_06_default_axis_is_reaction_not_startup() -> None:
    """默认解决轴为 reaction(关系支持):下游命中/关系证据不自动
    解决启动供给(R2-06:下游命中不自动解决上游依赖)。"""
    deps = [build_dependency(kind="cosubstrate_supply", statement=s)
            for s in ("supplies:A:B", "supplies:B:C", "supplies:C:A")]
    resolved = [
        resolve_dependency(d, new_evidence=["src:reaction-hit"],
                           resolution="supported")  # 未声明轴 ⇒ reaction
        for d in deps]
    result = detect_circular_dependencies(resolved)
    assert result["unresolved_initial_supply"] == [["A", "B", "C"]]
    assert resolved[0].resolution_log[0]["support_axis"] == "reaction"


def test_r2_06_unsupported_relation_disclosed_separately() -> None:
    """关系未支持与启动未知分轴呈现:环上一边无来源支持时,
    unsupported 关系单独披露,不混入 initial_supply 语义。"""
    a_b = build_dependency(kind="cosubstrate_supply",
                           statement="supplies:A:B")
    b_a = build_dependency(kind="cosubstrate_supply",
                           statement="supplies:B:A")
    result = detect_circular_dependencies([a_b, b_a])
    assert result["unresolved_initial_supply"] == [["A", "B"]]
    assert result["unsupported_relation_cycles"] == [["A", "B"]]
    seeded = resolve_dependency(
        a_b, new_evidence=["src:seed"], resolution="supported",
        support_axis="initial_supply")
    result2 = detect_circular_dependencies([seeded, b_a])
    # 初始供给已知(不再列入 unresolved_initial_supply),
    # 但 B→A 关系未支持仍单独披露
    assert result2["unresolved_initial_supply"] == []
    assert result2["unsupported_relation_cycles"] == [["A", "B"]]


# ================================================================ R2-07


def _states_for_hyp():
    sub = build_chemical_state("CCO", STRUCTURE_ORIGIN_RAW_INPUT)
    prod = build_chemical_state("CCO", STRUCTURE_ORIGIN_SOURCE_PRODUCT)
    return sub, prod


def _hyp(sub, prod, requirements, dependencies=None, assumptions=None):
    return build_hypothesis(
        parent_path_id="synthetic:parent",
        substrate_state_ref=sub.state_id,
        participants=[
            Participant(state_ref=sub.state_id,
                        side=PARTICIPANT_SIDE_REACTANT,
                        role=PARTICIPANT_ROLE_PRIMARY_SUBSTRATE,
                        coefficient=Fraction(1),
                        coefficient_status=COEFFICIENT_KNOWN),
            Participant(state_ref=prod.state_id,
                        side=PARTICIPANT_SIDE_PRODUCT,
                        role=PARTICIPANT_ROLE_PRINCIPAL_PRODUCT,
                        coefficient=Fraction(1),
                        coefficient_status=COEFFICIENT_KNOWN)],
        participant_list_status=PARTICIPANT_LIST_DECLARED_COMPLETE,
        step_scope="net_reaction",
        transformation_signature_status="verified",
        origin_group_key="same:source",
        requirements=[v.to_dict() for v in requirements],
        dependency_refs=dependencies,
        assumptions=assumptions)


def test_r2_07_different_premises_distinct_hypothesis_ids_coexist(
        tmp_path) -> None:
    """同父/同结构/同来源组键,不同科学前提(有氧/无氧/有氧+未解决
    依赖)⇒ 三个不同 hypothesis_id,可共存落账(put 不冲突)。"""
    sub, prod = _states_for_hyp()
    h1 = _hyp(sub, prod, [r(CONDITION_KEY_OXYGEN, "aerobic")])
    h2 = _hyp(sub, prod, [r(CONDITION_KEY_OXYGEN, "anaerobic")])
    h3 = _hyp(sub, prod, [r(CONDITION_KEY_OXYGEN, "aerobic")],
              dependencies=["dep:unknown"])
    ids = {h.hypothesis_id for h in (h1, h2, h3)}
    assert len(ids) == 3
    store = PollutantPathwayStore(tmp_path / "ppv1.sqlite")
    store.put_hypothesis(h1.to_dict(), context_hash="ctx:syn")
    store.put_hypothesis(h2.to_dict(), context_hash="ctx:syn")  # 共存
    store.put_hypothesis(h3.to_dict(), context_hash="ctx:syn")
    assert store.counts()["hypotheses"] == 3
    store.close()


def test_r2_07_same_premises_replay_idempotent(tmp_path) -> None:
    """相同语义重放 ⇒ 同 id 幂等(不抛冲突,不重复落账)。"""
    sub, prod = _states_for_hyp()
    h1 = _hyp(sub, prod, [r(CONDITION_KEY_OXYGEN, "aerobic")])
    h1_again = _hyp(sub, prod, [r(CONDITION_KEY_OXYGEN, "aerobic")])
    assert h1.hypothesis_id == h1_again.hypothesis_id
    store = PollutantPathwayStore(tmp_path / "ppv1.sqlite")
    store.put_hypothesis(h1.to_dict())
    store.put_hypothesis(h1_again.to_dict())  # 幂等重放
    assert store.counts()["hypotheses"] == 1
    store.close()


def test_r2_07_requirement_level_and_assumptions_change_identity() -> None:
    """requirements 全语义(essential/preference)与 assumptions
    均入身份哈希;requirements 顺序不影响(幂等)。"""
    sub, prod = _states_for_hyp()
    essential = _hyp(sub, prod, [build_requirement(
        key=CONDITION_KEY_OXYGEN, level="essential", value="aerobic",
        source_refs=SRC)])
    preference = _hyp(sub, prod, [build_requirement(
        key=CONDITION_KEY_OXYGEN, level="preference", value="aerobic",
        source_refs=SRC)])
    assert essential.hypothesis_id != preference.hypothesis_id
    with_assumption = _hyp(sub, prod,
                           [r(CONDITION_KEY_OXYGEN, "aerobic")],
                           assumptions=["假设:共培养提供辅酶"])
    without = _hyp(sub, prod, [r(CONDITION_KEY_OXYGEN, "aerobic")])
    assert with_assumption.hypothesis_id != without.hypothesis_id
    reordered = _hyp(sub, prod, [r(CONDITION_KEY_PH, {"lo": 6, "hi": 8}),
                                 r(CONDITION_KEY_OXYGEN, "aerobic")])
    same_order = _hyp(sub, prod, [r(CONDITION_KEY_OXYGEN, "aerobic"),
                                  r(CONDITION_KEY_PH, {"lo": 6, "hi": 8})])
    assert reordered.hypothesis_id == same_order.hypothesis_id


def test_r2_07_hypothesis_from_dict_gate_v3() -> None:
    """from_dict 版本门:v3 接受,未知版本拒绝(保持 fail-closed)。"""
    from pathway_v43.pollutant.hypothesis import ReactionHypothesis

    sub, prod = _states_for_hyp()
    h = _hyp(sub, prod, [r(CONDITION_KEY_OXYGEN, "aerobic")])
    d = h.to_dict()
    assert d["schema_version"] == "ppv1-hypothesis-4"
    assert ReactionHypothesis.from_dict(d).hypothesis_id == h.hypothesis_id
    bad = dict(d)
    bad["schema_version"] = "ppv1-hypothesis-999"
    with pytest.raises(Exception, match="版本未知"):
        ReactionHypothesis.from_dict(bad)


# ================================================================ P2(scope/coverage/来源/basis)


def test_p2_scope_derived_from_executed_checks() -> None:
    """assessed scope 从实际执行的检查派生:只评氧要求 ⇒ 不得输出
    氧+pH+温度已评估;有事实 ≠ 已检查(未评维度不进 assessment_scope)。"""
    result = aggregate_environment_fit(
        facts=[f(CONDITION_KEY_OXYGEN, "aerobic"),
               f(CONDITION_KEY_PH, 7.0)],  # 有 pH 事实但没有 pH 要求
        requirements=[r(CONDITION_KEY_OXYGEN, "aerobic")],
        declared_scope=[CONDITION_KEY_OXYGEN, CONDITION_KEY_PH,
                        CONDITION_KEY_TEMPERATURE])
    assert result.assessment_scope == [CONDITION_KEY_OXYGEN]
    assert result.environment_fit == "compatible"
    assert result.declared_scope == [CONDITION_KEY_OXYGEN, CONDITION_KEY_PH,
                                     CONDITION_KEY_TEMPERATURE]


def test_p2_scope_narrowing_leaves_trace_and_cannot_hide_unknown() -> None:
    """缩范围留痕 scope_narrowed_by;缩 scope 不得隐藏必需未知维度。"""
    # 声明只覆盖氧,但必需 pH 无事实 ⇒ 仍 unknown(隐藏不了)
    narrowed = aggregate_environment_fit(
        facts=[f(CONDITION_KEY_OXYGEN, "aerobic")],
        requirements=[r(CONDITION_KEY_OXYGEN, "aerobic"),
                      r(CONDITION_KEY_PH, {"lo": 6, "hi": 8})],
        declared_scope=[CONDITION_KEY_OXYGEN])
    assert narrowed.environment_fit == "unknown"
    assert narrowed.scope_narrowed is True
    assert narrowed.scope_narrowed_by == [CONDITION_KEY_PH]
    # 缩范围但必需项全部评过且满足 ⇒ compatible,带 narrowed 标注
    satisfied = aggregate_environment_fit(
        facts=[f(CONDITION_KEY_OXYGEN, "aerobic"),
               f(CONDITION_KEY_PH, 7.0)],
        requirements=[r(CONDITION_KEY_OXYGEN, "aerobic"),
                      r(CONDITION_KEY_PH, {"lo": 6, "hi": 8})],
        declared_scope=[CONDITION_KEY_OXYGEN])
    assert satisfied.environment_fit == "compatible"
    assert satisfied.scope_narrowed is True
    assert satisfied.scope_narrowed_by == [CONDITION_KEY_PH]


def test_p2_coverage_worst_status_assessed_satisfied_split() -> None:
    """coverage 聚合按最坏状态(conflict > unknown > satisfied);
    区分 assessed_keys 与 satisfied_keys;同键评过且冲突可呈现,
    不按键 last-wins;总判定语义不回退(仍 conflict)。"""
    result = aggregate_environment_fit(
        facts=[f(CONDITION_KEY_PH, 7.0)],
        requirements=[r(CONDITION_KEY_PH, {"lo": 4, "hi": 5}),
                      r(CONDITION_KEY_PH, {"lo": 6, "hi": 8})],
        declared_scope=[CONDITION_KEY_PH])
    assert result.environment_fit == "conflict"
    cov = result.requirement_coverage
    assert cov["essential_keys"] == [CONDITION_KEY_PH]
    assert cov["assessed_keys"] == [CONDITION_KEY_PH]     # 评过(两条)
    assert cov["satisfied_keys"] == []                    # 最坏=conflict
    assert cov["covered_keys"] == []                      # 兼容字段同语义
    assert cov["conflict_keys"] == [CONDITION_KEY_PH]
    # 逐条结果全保留:同键两条(satisfied + conflict)都在
    statuses = sorted(p["status"] for p in result.per_requirement)
    assert statuses == ["conflict", "satisfied"]


def test_p2_identical_facts_distinct_sources_not_inconsistent() -> None:
    """同值不同来源不是事实不一致(不降 unknown);来源都保留;
    值真正不同才走不一致路径。"""
    result = aggregate_environment_fit(
        facts=[f(CONDITION_KEY_PH, 7.0, source_ref="src:A"),
               f(CONDITION_KEY_PH, 7.0, source_ref="src:B")],
        requirements=[r(CONDITION_KEY_PH, {"lo": 6, "hi": 8})],
        declared_scope=[CONDITION_KEY_PH])
    row = per_key(result)[CONDITION_KEY_PH]
    assert row["status"] == "satisfied"
    assert sorted(row["fact_sources"]) == ["src:A", "src:B"]
    # 值真正不同(同场景同键)⇒ 保守 unknown
    conflicting = aggregate_environment_fit(
        facts=[f(CONDITION_KEY_PH, 7.0, source_ref="src:A"),
               f(CONDITION_KEY_PH, 8.5, source_ref="src:B")],
        requirements=[r(CONDITION_KEY_PH, {"lo": 6, "hi": 8})],
        declared_scope=[CONDITION_KEY_PH])
    row2 = per_key(conflicting)[CONDITION_KEY_PH]
    assert row2["status"] == "unknown"
    assert "conflicting_applicable_facts" in row2["reason"]


def test_p2_basis_shape_mismatch_rejected_at_construction() -> None:
    """构造期校验 basis 与值形状一致:dict⇒range;标量⇒point/
    optimum/unspecified;不一致抛 ConditionContractError(不静默改写)。"""
    with pytest.raises(ConditionContractError, match="basis"):
        build_requirement(key=CONDITION_KEY_PH, level="essential",
                          value={"lo": 6, "hi": 8},
                          value_basis="point", source_refs=SRC)
    with pytest.raises(ConditionContractError, match="basis"):
        build_requirement(key=CONDITION_KEY_PH, level="essential",
                          value=7.0, value_basis="range", source_refs=SRC)
    # 数据类直构路径(from_dict/假设侧字典,Requirement(**r))同样校验
    with pytest.raises(ConditionContractError, match="basis"):
        Requirement(key=CONDITION_KEY_PH, level="essential",
                    value={"lo": 6, "hi": 8}, value_basis="point")
    # 合法组合照常
    ok = build_requirement(key=CONDITION_KEY_PH, level="essential",
                           value={"lo": 6, "hi": 8}, source_refs=SRC)
    assert ok.value_basis == "range"
    ok_point = build_requirement(key=CONDITION_KEY_PH, level="essential",
                                 value=7.0, value_basis="point",
                                 source_refs=SRC)
    assert ok_point.value_basis == "point"
