"""R4 条件与科学前提线回归(Codex R3-06/07/08/12 + §4 行 1/2/8)。

全部合成夹具;先红后绿:各断言对应 R3 复审反例(conditions_probe.py
复现)或 §4 表项,在未修复代码上失败,修复后转绿。R3 已修语义
(阶段绑定/分支隔离/区间×点三态/单位不匹配 unknown/物种实体先匹配/
再生分轴/F02/C01–C06)由既有测试文件继续钉住,不在此重复。

AND/OR 立体语义说明(RDKit Book,§4 行 7):AND=两组分(该手性分子
及其镜像)都在的混合物;OR=二者未知何者的单一未定物质;ABS=单一
确定构型。本文件不涉及增强立体键,仅按此口径不误述。
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
    HypothesisContractError,
    Participant,
    build_hypothesis,
    canonical_hypothesis_payload,
    recompute_hypothesis_id,
)
from pathway_v43.pollutant.path_context import (  # noqa: E402
    CONDITION_KEY_MATRIX,
    CONDITION_KEY_OXYGEN,
    CONDITION_KEY_PH,
    CONDITION_KEY_TEMPERATURE,
    ConditionContractError,
    PathContext,
    Requirement,
    aggregate_environment_fit,
    assess_candidate_conditions,
    build_condition_fact,
    build_dependency,
    build_path_context,
    build_requirement,
    derive_child_context,
    detect_circular_dependencies,
    resolve_dependency,
    validate_context_object,
    validate_requirement_dict,
)
from pathway_v43.pollutant.store import PollutantPathwayStore  # noqa: E402

SRC = ["src:synthetic-r4"]


def f(key, value, **kw):
    return build_condition_fact(key=key, value=value,
                                status="known_present", **kw)


def r(key, value, **kw):
    return build_requirement(key=key, value=value, level="essential",
                             source_refs=SRC, **kw)


def per_key(result):
    return {p["key"]: p for p in result.per_requirement}


def _states():
    sub = build_chemical_state("CCO", STRUCTURE_ORIGIN_RAW_INPUT)
    prod = build_chemical_state("CCO", STRUCTURE_ORIGIN_SOURCE_PRODUCT)
    return sub, prod


def _hyp(sub, prod, requirements=None, dependencies=None,
         origin_group_key="r4:syn"):
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
        origin_group_key=origin_group_key,
        requirements=[v.to_dict() for v in (requirements or [])],
        dependency_refs=dependencies)


# ================================================================ R3-06
# 场景:sA:p0 有氧;sB:p0、sB:p1 无氧;父在 sA:p0,显式转至 sB:p1。


def _switched_child(old_required: str):
    """R3-06 两行验收表的公共夹具(审核 conditions_probe 同构)。"""
    facts = [f(CONDITION_KEY_OXYGEN, "aerobic", phase_id="p0",
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
        scenario_transition={"new_phase_id": "p1", "new_scenario_ref": "sB",
                             "source_ref": "user:transition"})
    return child


def _cand_hyp(requirements):
    sub, prod = _states()
    return _hyp(sub, prod, requirements)


def test_r3_06_row1_old_edge_conflict_kept() -> None:
    """父必需无氧旧边(sA:p0 有氧)已冲突 + sB:p1 子步无氧:
    候选评估必须 conflict(旧边记录值合取,不得被当前事实洗掉)。"""
    child = _switched_child("anaerobic")
    hyp = _cand_hyp([r(CONDITION_KEY_OXYGEN, "anaerobic")])
    result = assess_candidate_conditions(child, hyp)
    assert result.environment_fit == "conflict"
    assert result.assessed_scope == "conflicted"
    # 旧边来自 phase_history 记录值,不重评
    edges = result.detail["route_edge_fits"]
    assert edges[0]["source"] == "phase_history"
    assert edges[0]["phase_id"] == "p0"
    assert edges[0]["scenario_ref"] == "sA"
    assert edges[0]["environment_fit"] == "conflict"
    # 双层显示:当前步 compatible 与路线 conflict 并列
    assert result.detail["current_step_environment_fit"] == "compatible"
    assert result.detail["route_environment_fit"] == "conflict"
    # 旧边冲突行来自快照(记录值),不拿 sB 事实重评
    old_rows = [p for p in result.per_requirement
                if p.get("route_edge_source") == "phase_history:p0/sA"]
    assert old_rows and all(p["status"] == "conflict" for p in old_rows)


def test_r3_06_row2_old_edge_satisfied_not_falsely_killed() -> None:
    """父必需有氧旧边满足 + sB:p1 子步无氧:候选评估 compatible
    (不得拿 sB:p0 无氧事实重评旧有氧要求而冤杀)。"""
    child = _switched_child("aerobic")
    hyp = _cand_hyp([r(CONDITION_KEY_OXYGEN, "anaerobic")])
    result = assess_candidate_conditions(child, hyp)
    assert result.environment_fit == "compatible"
    assert result.assessed_scope == "condition_compatible"
    edges = result.detail["route_edge_fits"]
    assert edges[0]["environment_fit"] == "compatible"
    assert result.detail["route_environment_fit"] == "compatible"


def test_r3_06_current_phase_live_requirements_follow_r3_semantics() -> None:
    """仍在当前阶段的累积旧要求按 R3 语义 live 评估(当前事实);
    候选新要求并入同一当前作用域。"""
    facts = [f(CONDITION_KEY_OXYGEN, "anaerobic")]
    root = build_path_context(
        condition_facts=facts, phase_id="p0", scenario_ref="s",
        accumulated_requirements=[r(CONDITION_KEY_OXYGEN, "anaerobic")],
        assessment_scope=[CONDITION_KEY_OXYGEN])
    hyp = _cand_hyp([r(CONDITION_KEY_OXYGEN, "anaerobic")])
    result = assess_candidate_conditions(root, hyp)
    assert result.environment_fit == "compatible"
    assert all(p.get("route_edge_source") == "current_step"
               for p in result.per_requirement)


def test_r3_06_cross_phase_fact_serves_multiple_edges() -> None:
    """空 phase_id 的跨阶段事实可同时服务旧边与当前边(保持)。"""
    fact = f(CONDITION_KEY_TEMPERATURE, 25, unit="C")  # 无 phase_id:全阶段适用
    root = build_path_context(
        condition_facts=[fact], phase_id="p0", scenario_ref="s",
        accumulated_requirements=[
            r(CONDITION_KEY_TEMPERATURE, {"lo": 20, "hi": 30})],
        assessment_scope=[CONDITION_KEY_TEMPERATURE])
    child = derive_child_context(
        root, step_requirements=[
            r(CONDITION_KEY_TEMPERATURE, {"lo": 20, "hi": 30})],
        scenario_transition={"new_phase_id": "p1",
                             "source_ref": "user:transition"})
    hyp = _cand_hyp([r(CONDITION_KEY_TEMPERATURE, {"lo": 20, "hi": 30})])
    result = assess_candidate_conditions(child, hyp)
    assert result.environment_fit == "compatible"
    # 两条边都用同一空 phase 事实得到 satisfied
    rows = [p for p in result.per_requirement
            if p["status"] == "satisfied"]
    assert len(rows) >= 2


def test_r3_06_orphan_binding_unknown_not_dropped() -> None:
    """累积要求绑定到无快照覆盖的旧阶段:unknown 显式呈现,
    不静默丢弃(fail-closed)。"""
    root = build_path_context(
        condition_facts=[f(CONDITION_KEY_OXYGEN, "anaerobic")],
        phase_id="p1", scenario_ref="s",
        accumulated_requirements=[])
    orphan = r(CONDITION_KEY_OXYGEN, "anaerobic")
    orphan = Requirement(**{**orphan.to_dict(),
                            "introduced_phase_id": "p0",
                            "introduced_scenario_ref": "s",
                            "introduced_edge": "hyp:old"})
    root.accumulated_requirements.append(orphan)
    hyp = _cand_hyp([])
    result = assess_candidate_conditions(root, hyp)
    assert result.environment_fit == "unknown"
    orphan_rows = [p for p in result.per_requirement
                   if "not_in_route_snapshot" in p["reason"]]
    assert orphan_rows and all(p["status"] == "unknown"
                               for p in orphan_rows)


def test_r3_06_candidate_requirements_evaluated_in_current_scope() -> None:
    """本候选新增要求在当前 scenario+phase 作用域评估:
    当前 p1 有氧 + 新假设必需无氧 ⇒ conflict(不借 p0 无氧旧事实,
    也不因要求值与旧阶段事实相容而绕过当前作用域)。"""
    facts = [f(CONDITION_KEY_OXYGEN, "anaerobic", phase_id="p0",
               subject_scenario_ref="s"),
             f(CONDITION_KEY_OXYGEN, "aerobic", phase_id="p1",
               subject_scenario_ref="s")]
    ctx = build_path_context(
        condition_facts=facts, phase_id="p1", scenario_ref="s",
        assessment_scope=[CONDITION_KEY_OXYGEN])
    hyp = _cand_hyp([r(CONDITION_KEY_OXYGEN, "anaerobic")])
    result = assess_candidate_conditions(ctx, hyp)
    assert result.environment_fit == "conflict"
    row = per_key(result)[CONDITION_KEY_OXYGEN]
    assert row["status"] == "conflict"


def test_r3_06_foreign_requirement_binding_structured_reject() -> None:
    """调用方给 build_hypothesis 的 requirements 预填外来绑定
    (属于另一旧边)⇒ HypothesisContractError(kind=foreign_requirement_
    binding),不是静默保留(R3-06 第三反例)。"""
    sub, prod = _states()
    foreign = r(CONDITION_KEY_OXYGEN, "anaerobic").to_dict()
    foreign.update(introduced_phase_id="p0",
                   introduced_scenario_ref="s",
                   introduced_edge="another:hypothesis")
    with pytest.raises(HypothesisContractError) as ei:
        _hyp(sub, prod, [Requirement(**foreign)])
    assert ei.value.detail.get("kind") == "foreign_requirement_binding"
    # phase-only 绑定(无自边锚)同样拒绝
    phase_only = r(CONDITION_KEY_OXYGEN, "anaerobic").to_dict()
    phase_only.update(introduced_phase_id="p0")
    with pytest.raises(HypothesisContractError) as ei2:
        _hyp(sub, prod, [Requirement(**phase_only)])
    assert ei2.value.detail.get("kind") == "foreign_requirement_binding"


def test_r3_06_self_binding_allowed_and_id_stable() -> None:
    """合法自绑定(本假设 id)允许:重放带自绑定的要求字典 ⇒ 同 id、
    载荷绑定归一(绑定出处归上下文层,不进假设身份)。"""
    sub, prod = _states()
    req = r(CONDITION_KEY_OXYGEN, "anaerobic")
    h1 = _hyp(sub, prod, [req])
    bound = req.to_dict()
    bound.update(introduced_phase_id="p1",
                 introduced_scenario_ref="s",
                 introduced_edge=h1.hypothesis_id)
    h2 = _hyp(sub, prod, [Requirement(**bound)])
    assert h2.hypothesis_id == h1.hypothesis_id
    # 载荷中绑定字段归一为空(与未绑定构造同 payload)
    assert h2.to_dict() == h1.to_dict()


def test_r3_06_dict_hypothesis_supported() -> None:
    """assess_candidate_conditions 支持对象与 dict 两种假设输入。"""
    child = _switched_child("anaerobic")
    hyp = _cand_hyp([r(CONDITION_KEY_OXYGEN, "anaerobic")])
    result_obj = assess_candidate_conditions(child, hyp)
    result_dict = assess_candidate_conditions(child, hyp.to_dict())
    assert result_obj.environment_fit == result_dict.environment_fit


# ================================================================ R3-07


def test_r3_07_dependency_states_covers_context_dependencies() -> None:
    """context.dependency_states() 覆盖累积依赖(对象 + 裸引用):
    缺解析 ≠ 没有依赖;status/support_axes/statement 三键。"""
    dep = build_dependency(kind="cosubstrate_supply",
                           statement="supplies:A:B")
    resolved = resolve_dependency(
        dep, new_evidence=["src:initial"], resolution="supported",
        support_axis="initial_supply")
    resolved = resolve_dependency(
        resolved, new_evidence=["src:regen"], resolution="supported",
        support_axis="regeneration")
    ctx = build_path_context(
        condition_facts=[f(CONDITION_KEY_OXYGEN, "aerobic")],
        dependencies=[resolved],
        dependency_refs=["dep:unresolved_upstream"])
    states = ctx.dependency_states()
    assert set(states) == {resolved.dependency_id,
                           "dep:unresolved_upstream"}
    own = states[resolved.dependency_id]
    assert own["status"] == "supported"
    assert sorted(own["support_axes"]) == ["initial_supply",
                                           "regeneration"]
    assert own["statement"] == "supplies:A:B"
    # 裸引用:引用存在但无解析 ⇒ unresolved,不当作没有依赖
    bare = states["dep:unresolved_upstream"]
    assert bare["status"] == "unresolved"
    assert bare["support_axes"] == []
    # 无任何依赖 ⇒ 空字典(不是 None/异常)
    empty = build_path_context()
    assert empty.dependency_states() == {}


def test_r3_07_dependencies_inherit_and_enter_identity() -> None:
    """子上下文继承依赖对象;依赖(含解析状态/支持轴)进 context_id
    与 to_dict(R3-08:解析状态是真实科学输入)。"""
    dep = build_dependency(kind="mechanism", statement="假设水解")
    root = build_path_context(dependencies=[dep])
    resolved = resolve_dependency(
        dep, new_evidence=["src:e"], resolution="supported",
        support_axis="reaction")
    child = derive_child_context(root, step_dependencies=[resolved])
    states = child.dependency_states()
    assert states[dep.dependency_id]["status"] == "supported"
    # 解析状态不同 ⇒ 不同 context 身份
    unresolved_child = derive_child_context(root)
    assert unresolved_child.context_id != child.context_id
    # to_dict 覆盖依赖对象(含 status/support_axes)
    d = child.to_dict()
    dep_dicts = {x["dependency_id"]: x for x in d["dependencies"]}
    assert dep_dicts[dep.dependency_id]["status"] == "supported"
    assert dep_dicts[dep.dependency_id]["support_axes"] == ["reaction"]
    # 往返
    restored = PathContext.from_dict(d)
    assert restored.context_id == child.context_id
    assert restored.dependency_states() == child.dependency_states()


# ================================================================ R3-08


def test_r3_08_frozen_requirement_nested_collections() -> None:
    """frozen Requirement 的嵌套集合构造期冻结(tuple/冻结映射):
    对自身 source_refs/区间 value 的就地修改必须失败,context_id
    与内容不变(反例 frozen_nested_source_refs_mutable)。"""
    unsourced = build_requirement(key=CONDITION_KEY_OXYGEN,
                                  value="aerobic", level="essential")
    ctx = build_path_context(
        condition_facts=[f(CONDITION_KEY_OXYGEN, "aerobic")],
        accumulated_requirements=[unsourced],
        assessment_scope=[CONDITION_KEY_OXYGEN])
    before_id = ctx.context_id
    before = ctx.assessed_scope
    with pytest.raises((AttributeError, TypeError)):
        ctx.accumulated_requirements[0].source_refs.append(
            "src:added_after_hash")
    assert ctx.context_id == before_id
    assert ctx.assessed_scope == before
    # 区间 value 同样冻结
    req = r(CONDITION_KEY_TEMPERATURE, {"lo": 20, "hi": 30})
    with pytest.raises((TypeError, ConditionContractError)):
        req.value["lo"] = 40
    assert dict(req.value) == {"lo": 20, "hi": 30}
    # to_dict 输出普通可变副本(调用方可持有)
    plain = req.to_dict()
    plain["value"]["lo"] = 40
    assert dict(req.value) == {"lo": 20, "hi": 30}


def test_r3_08_caller_owned_requirement_list_not_shared() -> None:
    """调用方持有原 source_refs list 的后续 append 不影响对象内容。"""
    refs = ["src:original"]
    req = build_requirement(key=CONDITION_KEY_OXYGEN, value="aerobic",
                            level="essential", source_refs=refs)
    refs.append("src:later")
    assert list(req.source_refs) == ["src:original"]


def test_r3_08_fact_value_frozen() -> None:
    """ConditionFact 区间值冻结:构造后不可就地修改。"""
    fact = f(CONDITION_KEY_PH, {"lo": 6.8, "hi": 7.2})
    with pytest.raises((TypeError, ConditionContractError)):
        fact.value["lo"] = 1
    assert dict(fact.value) == {"lo": 6.8, "hi": 7.2}


def test_r3_08_dependency_nested_frozen() -> None:
    """Dependency 的 source_refs/resolution_log 构造期冻结。"""
    dep = build_dependency(kind="mechanism", statement="s",
                           source_refs=["src:1"])
    with pytest.raises((AttributeError, TypeError)):
        dep.source_refs.append("src:2")
    resolved = resolve_dependency(dep, new_evidence=["src:e"],
                                  resolution="supported")
    with pytest.raises((TypeError, ConditionContractError)):
        resolved.resolution_log[0]["evidence"] = []
    assert list(resolved.resolution_log[0]["evidence"]) == ["src:e"]


def test_r3_08_hypothesis_requirements_deep_copied() -> None:
    """build_hypothesis 对 requirements dicts 深拷贝:caller-owned
    dict 后续修改不影响假设内容/身份(反例 hypothesis_nested_
    caller_alias)。"""
    sub, prod = _states()
    raw_req = r(CONDITION_KEY_TEMPERATURE,
                {"lo": 20, "hi": 30}).to_dict()
    hyp = _hyp(sub, prod, [Requirement(**raw_req)])
    hid = hyp.hypothesis_id
    payload_before = hyp.to_dict()
    raw_req["value"].update(lo=40, hi=50)
    assert hyp.requirements[0]["value"] == {"lo": 20, "hi": 30}
    assert hyp.hypothesis_id == hid
    assert hyp.to_dict() == payload_before


def test_r3_08_order_invariant_same_id_and_payload(tmp_path) -> None:
    """同 oxygen/pH 要求不同顺序 ⇒ 同 id 且同 payload(排序归一);
    第二次 put 不冲突(payload 归一是本线职责)。"""
    sub, prod = _states()
    q1 = r(CONDITION_KEY_OXYGEN, "aerobic").to_dict()
    q2 = r(CONDITION_KEY_PH, {"lo": 6, "hi": 8}).to_dict()
    ha = _hyp(sub, prod, [Requirement(**q1), Requirement(**q2)])
    hb = _hyp(sub, prod, [Requirement(**q2), Requirement(**q1)])
    assert ha.hypothesis_id == hb.hypothesis_id
    assert ha.to_dict() == hb.to_dict()
    assert canonical_hypothesis_payload(ha.to_dict()) == \
        canonical_hypothesis_payload(hb.to_dict())
    store = PollutantPathwayStore(tmp_path / "ppv1.sqlite")
    store.put_hypothesis(ha.to_dict(), context_hash="ctx:syn")
    store.put_hypothesis(hb.to_dict(), context_hash="ctx:syn")  # 幂等
    assert store.counts()["hypotheses"] == 1
    store.close()


def test_r3_08_recompute_hypothesis_id_matches_construction() -> None:
    """recompute_hypothesis_id 与构造期同算法:
    to_dict(含/不含 id 字段)重推导 == 构造 id。"""
    sub, prod = _states()
    hyp = _hyp(sub, prod, [r(CONDITION_KEY_OXYGEN, "aerobic")])
    payload = hyp.to_dict()
    assert recompute_hypothesis_id(payload) == hyp.hypothesis_id
    without_id = {k: v for k, v in payload.items()
                  if k != "hypothesis_id"}
    assert recompute_hypothesis_id(without_id) == hyp.hypothesis_id
    # 顺序无关:换序载荷重推导同 id
    swapped = dict(payload)
    swapped["requirements"] = list(reversed(payload["requirements"]))
    assert recompute_hypothesis_id(swapped) == hyp.hypothesis_id
    # 载荷变化 ⇒ id 变化
    tampered = dict(payload)
    tampered["assumptions"] = ["多一条假设"]
    assert recompute_hypothesis_id(tampered) != hyp.hypothesis_id


def test_r3_08_recompute_rejects_foreign_binding() -> None:
    """recompute 与构造期同算法:外来绑定同样结构化拒绝。"""
    sub, prod = _states()
    hyp = _hyp(sub, prod, [r(CONDITION_KEY_OXYGEN, "aerobic")])
    payload = hyp.to_dict()
    payload["requirements"][0]["introduced_edge"] = "another:hypothesis"
    with pytest.raises(HypothesisContractError) as ei:
        recompute_hypothesis_id(payload)
    assert ei.value.detail.get("kind") == "foreign_requirement_binding"


def _bare_hyp(sub, prod, requirements):
    """直接把 requirements(对象或 dict)传给 build_hypothesis。"""
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
        step_scope="net_reaction", origin_group_key="r4:syn",
        requirements=requirements)


def test_r3_08_build_hypothesis_contract_errors_structured() -> None:
    """构造校验:HypothesisContractError 带 detail,绝无裸 TypeError
    (反例 contract_requirement_object/missing_fields/invalid_level/
    invalid_interval)。"""
    sub, prod = _states()
    # Requirement 对象不受支持(不是裸 TypeError)
    with pytest.raises(HypothesisContractError) as ei:
        _bare_hyp(sub, prod, [r(CONDITION_KEY_OXYGEN, "aerobic")])
    assert ei.value.detail.get("kind") == "requirement_object_not_supported"
    # 缺 level / value(键缺失)
    with pytest.raises(HypothesisContractError) as ei_level:
        _bare_hyp(sub, prod, [{"key": "temperature_C", "value": 25}])
    assert ei_level.value.detail.get("kind") == "missing_requirement_field"
    with pytest.raises(HypothesisContractError) as ei_value:
        _bare_hyp(sub, prod, [{"key": "temperature_C",
                               "level": "essential"}])
    assert ei_value.value.detail.get("kind") == "missing_requirement_field"
    # 非法 level(bogus 拒)
    with pytest.raises(HypothesisContractError) as ei_bogus:
        _bare_hyp(sub, prod, [
            {"key": CONDITION_KEY_OXYGEN, "level": "bogus",
             "value": "aerobic", "source_refs": SRC}])
    assert ei_bogus.value.detail.get("kind") == "invalid_requirement_level"
    # 反向区间(lo>hi 拒)
    with pytest.raises(HypothesisContractError) as ei_interval:
        _bare_hyp(sub, prod, [
            {"key": CONDITION_KEY_PH, "level": "essential",
             "value": {"lo": 8, "hi": 6}, "source_refs": SRC}])
    assert ei_interval.value.detail.get("kind") == "invalid_interval"
    # 未知条件键
    with pytest.raises(HypothesisContractError) as ei_key:
        _bare_hyp(sub, prod, [
            {"key": "temperature", "level": "essential",
             "value": 25, "source_refs": SRC}])
    assert ei_key.value.detail.get("kind") == "unknown_condition_key"
    # source_refs 类型校验
    with pytest.raises(HypothesisContractError) as ei_refs:
        _bare_hyp(sub, prod, [
            {"key": CONDITION_KEY_OXYGEN, "level": "essential",
             "value": "aerobic", "source_refs": "src:not-a-list"}])
    assert ei_refs.value.detail.get("kind") == "invalid_source_refs"


def test_r3_08_support_axes_accumulate_per_axis() -> None:
    """支持轴按轴集合累积(不再最近覆盖):initial_supply supported
    后再 regeneration supported ⇒ 两轴都在,启动未知不回退
    (§4 行 2/反例 later_regeneration_overwrites_initial_axis)。"""
    deps = [build_dependency(kind="cosubstrate_supply", statement=s)
            for s in ("supplies:A:B", "supplies:B:C", "supplies:C:A")]
    regen = [resolve_dependency(d, new_evidence=["src:regen"],
                                resolution="supported",
                                support_axis="regeneration")
             for d in deps]
    seeded = resolve_dependency(
        regen[0], new_evidence=["src:initial_pool"],
        resolution="supported", support_axis="initial_supply")
    later = resolve_dependency(
        seeded, new_evidence=["src:later_regen"],
        resolution="supported", support_axis="regeneration")
    assert sorted(later.support_axes) == ["initial_supply",
                                          "regeneration"]
    result = detect_circular_dependencies([later] + regen[1:])
    assert result["unresolved_initial_supply"] == []
    # 初始供给轴无证据 ⇒ 该轴 unknown 保持(仅再生不解决启动)
    only_regen = detect_circular_dependencies(regen)
    assert only_regen["unresolved_initial_supply"] == [["A", "B", "C"]]
    # 未解决依赖:支持轴为空
    fresh = build_dependency(kind="cosubstrate_supply",
                             statement="supplies:X:Y")
    assert fresh.support_axes == ()


def test_r3_08_support_axes_in_dependency_states_and_payload() -> None:
    """支持轴随依赖对象保存并进入 context.to_dict 科学载荷。"""
    dep = build_dependency(kind="cosubstrate_supply",
                           statement="supplies:A:B")
    both = resolve_dependency(dep, new_evidence=["src:i"],
                              resolution="supported",
                              support_axis="initial_supply")
    both = resolve_dependency(both, new_evidence=["src:r"],
                              resolution="supported",
                              support_axis="regeneration")
    ctx = build_path_context(dependencies=[both])
    d = ctx.to_dict()
    assert d["dependencies"][0]["support_axes"] == [
        "initial_supply", "regeneration"]
    assert sorted(ctx.dependency_states()[
        both.dependency_id]["support_axes"]) == [
        "initial_supply", "regeneration"]


def test_r3_08_validate_context_object_structured() -> None:
    """直接对象的缺/未来 context 版本:validate_context_object
    结构化 raise(audit 入口接线由主线做,本线交付函数)。"""
    ctx = build_path_context(
        condition_facts=[f(CONDITION_KEY_OXYGEN, "aerobic")])
    assert validate_context_object(ctx) is None
    missing = PathContext.from_dict(ctx.to_dict())
    missing.schema_version = None
    with pytest.raises(ConditionContractError) as ei:
        validate_context_object(missing)
    assert ei.value.detail.get("kind") == "context_schema_version_missing"
    future = PathContext.from_dict(ctx.to_dict())
    future.schema_version = "future-context-999"
    with pytest.raises(ConditionContractError) as ei2:
        validate_context_object(future)
    assert ei2.value.detail.get("kind") == "context_schema_version_unknown"
    with pytest.raises(ConditionContractError) as ei3:
        validate_context_object({"not": "a context"})
    assert ei3.value.detail.get("kind") == "context_object_invalid_type"


def test_r3_08_context_to_dict_full_science_payload() -> None:
    """context.to_dict() 覆盖全部科学载荷(R3-08:主会话将
    content_hash(context.to_dict()) 进 audit input_hash)。"""
    dep = build_dependency(kind="mechanism", statement="s")
    facts = [f(CONDITION_KEY_OXYGEN, "aerobic", phase_id="p0",
               subject_scenario_ref="sA")]
    root = build_path_context(
        condition_facts=facts, phase_id="p0", scenario_ref="sA",
        accumulated_requirements=[r(CONDITION_KEY_OXYGEN, "aerobic")],
        assumptions=["假设:共培养"], dependency_refs=["dep:1"],
        dependencies=[dep],
        assessment_scope=[CONDITION_KEY_OXYGEN])
    child = derive_child_context(
        root, step_requirements=[r(CONDITION_KEY_OXYGEN, "anaerobic")],
        scenario_transition={"new_phase_id": "p1", "new_scenario_ref": "sB",
                             "source_ref": "user:transition"})
    d = child.to_dict()
    for key in ("schema_version", "context_id", "parent_context_ref",
                "phase_id", "requested_scope", "condition_facts",
                "accumulated_requirements", "assumptions",
                "dependency_refs", "dependencies", "assessment_scope",
                "scenario_ref", "scenario_transition", "phase_history",
                "assessed_scope"):
        assert key in d, f"to_dict 缺科学载荷键:{key}"
    # 依赖对象含 status/support_axes;phase_history 含旧边快照
    assert d["dependencies"][0]["status"] == "unresolved"
    assert d["dependencies"][0]["support_axes"] == []
    assert d["phase_history"][0]["environment_fit"] == "compatible"
    # 载荷变化 ⇒ content_hash 变化(区分已解决/未解决依赖)
    from pathway_v43.domain.models import content_hash
    resolved = resolve_dependency(dep, new_evidence=["src:e"],
                                  resolution="supported")
    child2 = derive_child_context(
        root, step_dependencies=[resolved],
        scenario_transition={"new_phase_id": "p1",
                             "new_scenario_ref": "sB",
                             "source_ref": "user:transition"})
    assert content_hash(child.to_dict()) != content_hash(child2.to_dict())


# ================================================================ R3-12


def test_r3_12_matrix_string_mismatch_unknown() -> None:
    """matrix 键无语义关系(无封闭枚举/注册映射/范围)的字符串不等
    ⇒ unknown(matrix_value_unresolved),不得硬判 conflict
    (反例 matrix_overlap)。同字符串 ⇒ satisfied。"""
    result = aggregate_environment_fit(
        facts=[f(CONDITION_KEY_MATRIX, "sandy soil")],
        requirements=[r(CONDITION_KEY_MATRIX, "soil")],
        declared_scope=[CONDITION_KEY_MATRIX])
    row = per_key(result)[CONDITION_KEY_MATRIX]
    assert row["status"] == "unknown"
    assert "matrix_value_unresolved" in row["reason"]
    assert result.environment_fit == "unknown"
    same = aggregate_environment_fit(
        facts=[f(CONDITION_KEY_MATRIX, "soil")],
        requirements=[r(CONDITION_KEY_MATRIX, "soil")],
        declared_scope=[CONDITION_KEY_MATRIX])
    assert per_key(same)[CONDITION_KEY_MATRIX]["status"] == "satisfied"


def test_r3_12_oxygen_enum_mismatch_still_conflict() -> None:
    """氧枚举封闭集不等仍 conflict(既有行为不变,不因 matrix 放宽)。"""
    result = aggregate_environment_fit(
        facts=[f(CONDITION_KEY_OXYGEN, "anaerobic")],
        requirements=[r(CONDITION_KEY_OXYGEN, "aerobic")],
        declared_scope=[CONDITION_KEY_OXYGEN])
    row = per_key(result)[CONDITION_KEY_OXYGEN]
    assert row["status"] == "conflict"
    assert "value_mismatch" in row["reason"]


# ================================================================ §4 行 1


def test_unit_basis_assumed_canonical_disclosed() -> None:
    """R5(R4-03):要求值恒为键规范单位(构造器无 unit 字段);事实
    无单位(必须显式单位的键 temperature_C)= 原来源单位未知 ⇒
    **unknown + unit_basis: source_unit_unknown**(注记不再把未知
    来源升级为 satisfied;此前 v4 的 assumed_canonical+satisfied 是
    复审点名缺陷);显式规范单位 ⇒ canonical + 参与比较;显式错误
    单位仍 unknown/unit_mismatch;pH 等无量纲键空单位合法。"""
    # 无单位事实:原来源单位未知 ⇒ unknown,不按数值直比
    no_unit = aggregate_environment_fit(
        facts=[f(CONDITION_KEY_TEMPERATURE, 25, origin="curated_source",
                 source_ref="src:unit_not_reported",
                 subject_scenario_ref="s")],
        requirements=[r(CONDITION_KEY_TEMPERATURE, {"lo": 20, "hi": 30})],
        scenario_ref="s", declared_scope=[CONDITION_KEY_TEMPERATURE])
    row = per_key(no_unit)[CONDITION_KEY_TEMPERATURE]
    assert row["status"] == "unknown"
    assert row["unit_basis"] == "source_unit_unknown"
    assert "source_unit_unknown" in row["reason"]
    # 显式规范单位:已归一输入
    explicit = aggregate_environment_fit(
        facts=[f(CONDITION_KEY_TEMPERATURE, 25, unit="°C")],
        requirements=[r(CONDITION_KEY_TEMPERATURE, {"lo": 20, "hi": 30})],
        declared_scope=[CONDITION_KEY_TEMPERATURE])
    row2 = per_key(explicit)[CONDITION_KEY_TEMPERATURE]
    assert row2["status"] == "satisfied"
    assert row2["unit_basis"] == "canonical"
    # 显式错误单位:仍 unknown/unit_mismatch,不给 unit_basis 冒充
    kelvin = aggregate_environment_fit(
        facts=[f(CONDITION_KEY_TEMPERATURE, 25, unit="K")],
        requirements=[r(CONDITION_KEY_TEMPERATURE, {"lo": 20, "hi": 30})],
        declared_scope=[CONDITION_KEY_TEMPERATURE])
    row3 = per_key(kelvin)[CONDITION_KEY_TEMPERATURE]
    assert row3["status"] == "unknown"
    assert "unit_mismatch" in row3["reason"]
    assert "unit_basis" not in row3
    # build_requirement 不支持 unit 字段(要求值恒为键规范单位)
    with pytest.raises(TypeError):
        build_requirement(key=CONDITION_KEY_TEMPERATURE, level="essential",
                          value={"lo": 20, "hi": 30}, unit="K")


def test_unit_basis_in_candidate_assessment_rows() -> None:
    """assess_candidate_conditions 的 per-requirement 同样带
    unit_basis(§4 行 1 适用全部评估路径;R5:显式规范单位 ⇒
    canonical,空单位 ⇒ source_unit_unknown + unknown)。"""
    ctx = build_path_context(
        condition_facts=[f(CONDITION_KEY_TEMPERATURE, 25, unit="C")],
        phase_id="p0", scenario_ref="s",
        assessment_scope=[CONDITION_KEY_TEMPERATURE])
    hyp = _cand_hyp([r(CONDITION_KEY_TEMPERATURE, {"lo": 20, "hi": 30})])
    result = assess_candidate_conditions(ctx, hyp)
    row = per_key(result)[CONDITION_KEY_TEMPERATURE]
    assert row["status"] == "satisfied"
    assert row["unit_basis"] == "canonical"
    # 空单位(原来源单位未知):candidate 路径同样 unknown + 注记
    ctx2 = build_path_context(
        condition_facts=[f(CONDITION_KEY_TEMPERATURE, 25)],
        phase_id="p0", scenario_ref="s",
        assessment_scope=[CONDITION_KEY_TEMPERATURE])
    result2 = assess_candidate_conditions(ctx2, hyp)
    row2 = per_key(result2)[CONDITION_KEY_TEMPERATURE]
    assert row2["status"] == "unknown"
    assert row2["unit_basis"] == "source_unit_unknown"


# ================================================================ 契约函数


def test_validate_requirement_dict_structured_errors() -> None:
    """path_context 侧要求字典校验器:结构化 kind,供假设侧/评估侧
    共用(缺字段/非法枚举/反向区间/未知键/类型)。"""
    with pytest.raises(ConditionContractError) as ei:
        validate_requirement_dict({"key": CONDITION_KEY_PH})
    assert ei.value.detail.get("kind") == "missing_requirement_field"
    with pytest.raises(ConditionContractError) as ei2:
        validate_requirement_dict(
            {"key": CONDITION_KEY_PH, "level": "bogus",
             "value": {"lo": 6, "hi": 8}})
    assert ei2.value.detail.get("kind") == "invalid_requirement_level"
    with pytest.raises(ConditionContractError) as ei3:
        validate_requirement_dict(
            {"key": CONDITION_KEY_PH, "level": "essential",
             "value": {"lo": 8, "hi": 6}})
    assert ei3.value.detail.get("kind") == "invalid_interval"
    with pytest.raises(ConditionContractError) as ei4:
        validate_requirement_dict(
            {"key": "salinity", "level": "essential", "value": 1})
    assert ei4.value.detail.get("kind") == "unknown_condition_key"
    with pytest.raises(ConditionContractError) as ei5:
        validate_requirement_dict(
            {"key": CONDITION_KEY_PH, "level": "essential", "value": 7,
             "unexpected_field": 1})
    assert ei5.value.detail.get("kind") == "unknown_requirement_field"
    # 合法载荷通过
    ok = r(CONDITION_KEY_PH, {"lo": 6, "hi": 8}).to_dict()
    validate_requirement_dict(ok)


def test_candidate_assessment_shape_matches_assess_conditions() -> None:
    """assess_candidate_conditions 返回对象与 assess_conditions
    同形状(契约 1);detail 为新增可序列化字段。"""
    child = _switched_child("anaerobic")
    hyp = _cand_hyp([r(CONDITION_KEY_OXYGEN, "anaerobic")])
    result = assess_candidate_conditions(child, hyp)
    d = result.to_dict()
    for key in ("per_requirement", "environment_fit", "assessed_scope",
                "assessment_scope", "unassessed_dimensions",
                "requirement_coverage", "preference_notes",
                "declared_scope", "schema_version"):
        assert key in d, f"评估结果缺字段:{key}"
    import json
    json.dumps(d, ensure_ascii=False)  # detail 可序列化
