"""S1 领域契约测试(规则级夹具;模型 scripted/off,无金标、无付费实验)。

覆盖验收矩阵:
- A01 A→B 或 A→C:两个反应假设/事件,不把 B+C 当同一反应;
- A02 A 裂解共同生成 B+C:一个事件保存两产物;报告 K=1 也不丢 C;
- A03 某共同产物不继续追踪:完整事件仍保留;展开计划有独立原因;
- A04 旧 novel 平列表导入:原语义不确定明确挂牌,不猜分组;
- B01 对映体/可中和电荷差异:严格状态不同,允许旧 CN 相同;
- B02 映射号改动/只有旧 CN:映射号不改分子身份;CN-only 不伪造手性;
- H02 零/负/非有限系数违反输入契约;
- H03 重复参与物:声明并列可求和,未知保留歧义;
- 事件幂等/冲突;legacy 只读导入零写回。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pathway_v43.pollutant.chemstate import (  # noqa: E402
    REPRESENTATION_ARCHIVE_RECOVERED,
    STRUCTURE_ORIGIN_LEGACY_CN_ONLY,
    STRUCTURE_ORIGIN_RAW_INPUT,
    STRUCTURE_ORIGIN_SOURCE_PRODUCT,
    ChemicalStateError,
    build_chemical_state,
    build_chemical_state_from_cn_only,
)
from pathway_v43.pollutant.events import (  # noqa: E402
    ParticipantStateError,
    build_event_states,
    build_expansion_plan,
    build_pathway_event,
    build_report_projection,
)
from pathway_v43.pollutant.hypothesis import (  # noqa: E402
    COEFFICIENT_KNOWN,
    COEFFICIENT_UNKNOWN,
    HypothesisContractError,
    LEGACY_RELATIONSHIP_UNSPECIFIED,
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
from pathway_v43.pollutant.store import (  # noqa: E402
    Ppv1EventConflict,
    PollutantPathwayStore,
)

ETHANOL = "CCO"
ACETALDEHYDE = "CC=O"
ACETIC = "CC(=O)O"
# 裂解示例:苯乙醇裂成苯甲醛 + …(用简单可解析分子构造共同产物场景)
PHENYLETHANOL = "OC(=O)c1ccccc1O"  # 水杨酸(双产物裂解用例的底物母体)
BENZALDEHYDE = "O=Cc1ccccc1"
CO2 = "O=C=O"


def _state(smiles: str, origin: str = STRUCTURE_ORIGIN_SOURCE_PRODUCT):
    return build_chemical_state(smiles, origin)


def _substrate_participant(ref: str) -> Participant:
    return Participant(state_ref=ref, side=PARTICIPANT_SIDE_REACTANT,
                       role=PARTICIPANT_ROLE_PRIMARY_SUBSTRATE,
                       coefficient=None,
                       coefficient_status=COEFFICIENT_UNKNOWN)


def _product_participant(ref: str, role=PARTICIPANT_ROLE_PRINCIPAL_PRODUCT,
                         coefficient=None) -> Participant:
    return Participant(state_ref=ref, side=PARTICIPANT_SIDE_PRODUCT,
                       role=role, coefficient=coefficient,
                       coefficient_status=(COEFFICIENT_KNOWN if coefficient
                                           else COEFFICIENT_UNKNOWN))


# ---------------------------------------------------------------- B01/B02


def test_b01_enantiomers_distinct_state_same_cn() -> None:
    left = build_chemical_state("C[C@H](N)C(=O)O",
                                STRUCTURE_ORIGIN_RAW_INPUT)
    right = build_chemical_state("C[C@@H](N)C(=O)O",
                                 STRUCTURE_ORIGIN_RAW_INPUT)
    assert left.state_id != right.state_id        # 严格状态不同
    assert left.cn_identity == right.cn_identity  # 允许旧 CN 相同
    assert left.stereo_information_status == "specified"


def test_b01_neutralizable_charge_distinct_state() -> None:
    charged = build_chemical_state("C[NH3+]", STRUCTURE_ORIGIN_RAW_INPUT)
    neutral = build_chemical_state("CN", STRUCTURE_ORIGIN_RAW_INPUT)
    assert charged.state_id != neutral.state_id
    assert charged.formal_charge == 1
    assert neutral.formal_charge == 0
    assert charged.cn_identity == neutral.cn_identity  # 归一化后同 CN


def test_b02_atom_map_numbers_do_not_change_identity() -> None:
    plain = build_chemical_state("CO", STRUCTURE_ORIGIN_RAW_INPUT)
    mapped = build_chemical_state("[CH3:1][OH:2]", STRUCTURE_ORIGIN_RAW_INPUT)
    assert plain.state_id == mapped.state_id  # 映射号不属于分子身份
    assert plain.smiles_isomeric == mapped.smiles_isomeric


def test_b02_cn_only_does_not_fabricate_stereo() -> None:
    state = build_chemical_state_from_cn_only("CC(O)C")
    assert state.structure_origin == STRUCTURE_ORIGIN_LEGACY_CN_ONLY
    assert state.stereo_information_status == "unknown"
    assert state.isotope_information_status == "unknown"
    assert state.original_structure_available is False
    assert state.formal_charge is None
    assert state.smiles_isomeric == ""
    assert state.representation_fidelity == "cn_only_projection"
    # 幂等:同 CN 重建同 id
    assert build_chemical_state_from_cn_only(
        "CC(O)C").state_id == state.state_id


def test_chemstate_unparseable_fails_closed() -> None:
    with pytest.raises(ChemicalStateError):
        build_chemical_state("not-a-smiles", STRUCTURE_ORIGIN_RAW_INPUT)
    with pytest.raises(ChemicalStateError):
        build_chemical_state("", STRUCTURE_ORIGIN_RAW_INPUT)
    with pytest.raises(ChemicalStateError):
        build_chemical_state("CCO", "bogus_origin")


def test_chemstate_json_roundtrip_and_archive_fidelity() -> None:
    state = build_chemical_state(
        "O", STRUCTURE_ORIGIN_SOURCE_PRODUCT,
        source_refs=[{"role": "legacy_event_product", "event_id": "e1"}],
        representation_fidelity=REPRESENTATION_ARCHIVE_RECOVERED)
    d = state.to_dict()
    assert d["representation_fidelity"] == REPRESENTATION_ARCHIVE_RECOVERED
    assert json.loads(json.dumps(d))["state_id"] == state.state_id
    again = build_chemical_state("O", STRUCTURE_ORIGIN_SOURCE_PRODUCT)
    assert again.state_id == state.state_id  # 幂等重建


# ---------------------------------------------------------------- A01


def test_a01_two_alternatives_are_two_hypotheses() -> None:
    a = _state(ETHANOL, STRUCTURE_ORIGIN_RAW_INPUT)
    b = _state(ACETALDEHYDE)
    c = _state(ACETIC)
    hyp_b = build_hypothesis(
        parent_path_id="p1", substrate_state_ref=a.state_id,
        participants=[_substrate_participant(a.state_id),
                      _product_participant(b.state_id)],
        participant_list_status=PARTICIPANT_LIST_PARTIAL,
        step_scope="net_reaction", origin_group_key="src1")
    hyp_c = build_hypothesis(
        parent_path_id="p1", substrate_state_ref=a.state_id,
        participants=[_substrate_participant(a.state_id),
                      _product_participant(c.state_id)],
        participant_list_status=PARTICIPANT_LIST_PARTIAL,
        step_scope="net_reaction", origin_group_key="src2")
    assert hyp_b.hypothesis_id != hyp_c.hypothesis_id
    # B 与 C 不混成一个"反应":每个假设各只有一个产物侧参与物
    assert [p.state_ref for p in hyp_b.participants
            if p.side == PARTICIPANT_SIDE_PRODUCT] == [b.state_id]
    assert [p.state_ref for p in hyp_c.participants
            if p.side == PARTICIPANT_SIDE_PRODUCT] == [c.state_id]


def test_a01_same_semantics_rebuild_same_hypothesis_id() -> None:
    a = _state(ETHANOL, STRUCTURE_ORIGIN_RAW_INPUT)
    b = _state(ACETALDEHYDE)
    parts = [_substrate_participant(a.state_id),
             _product_participant(b.state_id)]
    h1 = build_hypothesis(parent_path_id="p1",
                          substrate_state_ref=a.state_id,
                          participants=list(parts),
                          participant_list_status=PARTICIPANT_LIST_PARTIAL,
                          step_scope="net_reaction",
                          origin_group_key="src1")
    h2 = build_hypothesis(parent_path_id="p1",
                          substrate_state_ref=a.state_id,
                          participants=[Participant(
                              state_ref=parts[0].state_ref,
                              side=parts[0].side, role=parts[0].role,
                              coefficient=None,
                              coefficient_status=COEFFICIENT_UNKNOWN),
                              Participant(
                              state_ref=parts[1].state_ref,
                              side=parts[1].side, role=parts[1].role,
                              coefficient=None,
                              coefficient_status=COEFFICIENT_UNKNOWN)],
                          participant_list_status=PARTICIPANT_LIST_PARTIAL,
                          step_scope="net_reaction",
                          origin_group_key="src1")
    assert h1.hypothesis_id == h2.hypothesis_id  # 冻结语义幂等


# ---------------------------------------------------------------- A02/A03


def _cleavage_hypothesis(substrate, *products):
    return build_hypothesis(
        parent_path_id="p1", substrate_state_ref=substrate.state_id,
        participants=[_substrate_participant(substrate.state_id)]
        + [_product_participant(p.state_id) for p in products],
        participant_list_status=PARTICIPANT_LIST_PARTIAL,
        step_scope="net_reaction", origin_group_key="cleavage-1")


def test_a02_cleavage_event_keeps_both_products_even_k1(tmp_path: Path) -> None:
    substrate = _state(PHENYLETHANOL, STRUCTURE_ORIGIN_RAW_INPUT)
    b = _state(BENZALDEHYDE)
    c = _state(CO2)
    hyp = _cleavage_hypothesis(substrate, b, c)
    # 共同产物 = 一个假设/事件的两条产物侧参与物(不拆成两个反应)
    product_refs = [p.state_ref for p in hyp.participants
                    if p.side == PARTICIPANT_SIDE_PRODUCT]
    assert product_refs == [b.state_id, c.state_id]

    event = build_pathway_event(hyp, run_id="r-a02",
                                context_hash="ctx-1")
    # 报告 K=1:投影只给 B 位次
    report = build_report_projection(
        hyp, max_reportable=1, ranked_state_refs=[b.state_id, c.state_id],
        reasons=["test:report K=1"])
    # 完整事件不被 K 截断:C 仍在事件参与物里
    assert c.state_id in event.participant_state_refs
    assert len([p for p in event.participants
                if p["side"] == PARTICIPANT_SIDE_PRODUCT]) == 2
    # 投影如实:C 记宽度上限,不冒充有位次
    by_ref = {r["state_ref"]: r for r in report.product_ranks}
    assert by_ref[b.state_id]["report_rank"] == 1
    assert by_ref[c.state_id]["report_rank"] is None
    assert by_ref[c.state_id]["basis"] == "report_width_cap"

    store = PollutantPathwayStore(tmp_path / "ppv1.sqlite")
    states = build_event_states(
        hyp, raw_structures={
            substrate.state_id: PHENYLETHANOL,
            b.state_id: BENZALDEHYDE, c.state_id: CO2})
    result = store.submit_event(
        event, report_projection=report.to_dict(),
        expansion_plan=build_expansion_plan(
            hyp, expanded=[b.state_id], deferred=[],
            not_tracked=[c.state_id],
            reasons={c.state_id: "test:not tracking CO2"}).to_dict(),
        states=[s.to_dict() for s in states.values()])
    assert result["created"] is True
    # K=1 之后事件里 C 仍然在(存储层程序证据)
    stored = store.get_event(event.event_id)
    payload = json.loads(stored["payload"])
    assert len(payload["participant_state_refs"]) == 3
    assert c.state_id in payload["participant_state_refs"]
    store.close()


def test_a02_illegal_coproduct_fails_whole_event_not_silent_drop() -> None:
    substrate = _state(PHENYLETHANOL, STRUCTURE_ORIGIN_RAW_INPUT)
    b = _state(BENZALDEHYDE)
    # C 为格式非法的共同产物:构建参与物状态时整体失败,不静默丢
    with pytest.raises(ParticipantStateError) as exc_info:
        build_event_states(
            _cleavage_hypothesis(substrate, b, _state_placeholder()),
            raw_structures={substrate.state_id: PHENYLETHANOL,
                            b.state_id: BENZALDEHYDE,
                            "bad": "!!not-smiles!!"})
    assert exc_info.value.detail["kind"] in (
        "missing_structure", "unparseable_participant")
    assert exc_info.value.detail["state_ref"] == "bad"


def _state_placeholder():
    class _Ref:
        state_id = "bad"
    return _Ref()


def test_a03_not_tracked_product_kept_with_reason(tmp_path: Path) -> None:
    substrate = _state(PHENYLETHANOL, STRUCTURE_ORIGIN_RAW_INPUT)
    b = _state(BENZALDEHYDE)
    c = _state(CO2)
    hyp = _cleavage_hypothesis(substrate, b, c)
    event = build_pathway_event(hyp, run_id="r-a03",
                                context_hash="ctx-1")
    plan = build_expansion_plan(
        hyp, expanded=[b.state_id], deferred=[], not_tracked=[c.state_id],
        reasons={c.state_id: "no_rule_evidence_for_further_steps"})
    store = PollutantPathwayStore(tmp_path / "ppv1.sqlite")
    states = build_event_states(
        hyp, raw_structures={substrate.state_id: PHENYLETHANOL,
                             b.state_id: BENZALDEHYDE, c.state_id: CO2})
    store.submit_event(event, report_projection=build_report_projection(
        hyp, max_reportable=2, ranked_state_refs=[b.state_id, c.state_id],
        reasons=[""]).to_dict(),
        expansion_plan=plan.to_dict(),
        states=[s.to_dict() for s in states.values()])
    stored_plan = store.expansion_plan(event.event_id)
    by_ref = {e["state_ref"]: e for e in stored_plan["entries"]}
    assert by_ref[c.state_id]["status"] == "not_tracked"
    assert by_ref[c.state_id]["reason"] == "no_rule_evidence_for_further_steps"
    # 完整事件仍保留 C(事件与展开计划分开)
    stored_event = store.get_event(event.event_id)
    assert c.state_id in json.loads(
        stored_event["payload"])["participant_state_refs"]
    store.close()


def test_a03_unlisted_product_gets_explicit_reason() -> None:
    substrate = _state(PHENYLETHANOL, STRUCTURE_ORIGIN_RAW_INPUT)
    b = _state(BENZALDEHYDE)
    c = _state(CO2)
    hyp = _cleavage_hypothesis(substrate, b, c)
    plan = build_expansion_plan(hyp, expanded=[b.state_id], deferred=[],
                                not_tracked=[])
    by_ref = {e["state_ref"]: e for e in plan.entries}
    assert by_ref[c.state_id]["status"] == "not_tracked"
    assert by_ref[c.state_id]["reason"] == "not_declared_in_expansion_plan"


# ---------------------------------------------------------------- H02/H03


@pytest.mark.parametrize("bad", [0, -1, 0.0, -0.5, float("inf"),
                                  float("nan"), "0", "-2/3"])
def test_h02_invalid_coefficients_rejected(bad) -> None:
    with pytest.raises(HypothesisContractError):
        Participant(state_ref="cs_x", side=PARTICIPANT_SIDE_REACTANT,
                    role=PARTICIPANT_ROLE_PRIMARY_SUBSTRATE,
                    coefficient=bad, coefficient_status=COEFFICIENT_KNOWN)


def test_h02_known_null_and_unknown_value_rejected() -> None:
    with pytest.raises(HypothesisContractError, match="known"):
        Participant(state_ref="cs_x", side=PARTICIPANT_SIDE_REACTANT,
                    role=PARTICIPANT_ROLE_PRIMARY_SUBSTRATE,
                    coefficient=None, coefficient_status=COEFFICIENT_KNOWN)
    with pytest.raises(HypothesisContractError, match="unknown"):
        Participant(state_ref="cs_x", side=PARTICIPANT_SIDE_REACTANT,
                    role=PARTICIPANT_ROLE_PRIMARY_SUBSTRATE,
                    coefficient=1, coefficient_status=COEFFICIENT_UNKNOWN)


def test_h03_parallel_declared_duplicates_summed_with_trace() -> None:
    p1 = Participant(state_ref="cs_o2", side=PARTICIPANT_SIDE_REACTANT,
                     role=PARTICIPANT_ROLE_COSUBSTRATE, coefficient=1,
                     coefficient_status=COEFFICIENT_KNOWN,
                     parallel_contribution=True)
    p2 = Participant(state_ref="cs_o2", side=PARTICIPANT_SIDE_REACTANT,
                     role=PARTICIPANT_ROLE_COSUBSTRATE, coefficient=2,
                     coefficient_status=COEFFICIENT_KNOWN,
                     parallel_contribution=True)
    hyp = build_hypothesis(
        parent_path_id="p1", substrate_state_ref="cs_s",
        participants=[Participant(
            state_ref="cs_s", side=PARTICIPANT_SIDE_REACTANT,
            role=PARTICIPANT_ROLE_PRIMARY_SUBSTRATE, coefficient=None,
            coefficient_status=COEFFICIENT_UNKNOWN), p1, p2],
        participant_list_status=PARTICIPANT_LIST_PARTIAL,
        step_scope="net_reaction")
    o2_entries = [p for p in hyp.participants if p.state_ref == "cs_o2"]
    assert len(o2_entries) == 1                      # 求和为一个条目
    assert o2_entries[0].coefficient == 3            # 1 + 2
    assert len(o2_entries[0].merged_from) == 2       # 归并轨迹保留
    assert hyp.ambiguous_participants is False


def test_h03_undeclared_duplicates_keep_ambiguity() -> None:
    p1 = Participant(state_ref="cs_o2", side=PARTICIPANT_SIDE_REACTANT,
                     role=PARTICIPANT_ROLE_COSUBSTRATE, coefficient=1,
                     coefficient_status=COEFFICIENT_KNOWN)
    p2 = Participant(state_ref="cs_o2", side=PARTICIPANT_SIDE_REACTANT,
                     role=PARTICIPANT_ROLE_COSUBSTRATE, coefficient=1,
                     coefficient_status=COEFFICIENT_KNOWN)
    hyp = build_hypothesis(
        parent_path_id="p1", substrate_state_ref="cs_s",
        participants=[Participant(
            state_ref="cs_s", side=PARTICIPANT_SIDE_REACTANT,
            role=PARTICIPANT_ROLE_PRIMARY_SUBSTRATE, coefficient=None,
            coefficient_status=COEFFICIENT_UNKNOWN), p1, p2],
        participant_list_status=PARTICIPANT_LIST_PARTIAL,
        step_scope="net_reaction")
    o2_entries = [p for p in hyp.participants if p.state_ref == "cs_o2"]
    assert len(o2_entries) == 2                      # 不静默去重/求和
    assert hyp.ambiguous_participants is True        # 保留歧义标记


def test_h03_unknown_coefficient_duplicates_not_summed() -> None:
    p1 = Participant(state_ref="cs_o2", side=PARTICIPANT_SIDE_REACTANT,
                     role=PARTICIPANT_ROLE_COSUBSTRATE, coefficient=None,
                     coefficient_status=COEFFICIENT_UNKNOWN,
                     parallel_contribution=True)
    p2 = Participant(state_ref="cs_o2", side=PARTICIPANT_SIDE_REACTANT,
                     role=PARTICIPANT_ROLE_COSUBSTRATE, coefficient=None,
                     coefficient_status=COEFFICIENT_UNKNOWN,
                     parallel_contribution=True)
    hyp = build_hypothesis(
        parent_path_id="p1", substrate_state_ref="cs_s",
        participants=[Participant(
            state_ref="cs_s", side=PARTICIPANT_SIDE_REACTANT,
            role=PARTICIPANT_ROLE_PRIMARY_SUBSTRATE, coefficient=None,
            coefficient_status=COEFFICIENT_UNKNOWN), p1, p2],
        participant_list_status=PARTICIPANT_LIST_PARTIAL,
        step_scope="net_reaction")
    o2_entries = [p for p in hyp.participants if p.state_ref == "cs_o2"]
    assert len(o2_entries) == 2  # 系数未知:不猜求和
    assert hyp.ambiguous_participants is True


# ---------------------------------------------------------------- 事件存储契约


def test_event_idempotent_replay_and_conflict(tmp_path: Path) -> None:
    substrate = _state(ETHANOL, STRUCTURE_ORIGIN_RAW_INPUT)
    b = _state(ACETALDEHYDE)
    hyp = build_hypothesis(
        parent_path_id="p1", substrate_state_ref=substrate.state_id,
        participants=[_substrate_participant(substrate.state_id),
                      _product_participant(b.state_id)],
        participant_list_status=PARTICIPANT_LIST_PARTIAL,
        step_scope="net_reaction", origin_group_key="s")
    event = build_pathway_event(hyp, run_id="r-idem", context_hash="ctx")
    report = build_report_projection(
        hyp, max_reportable=1, ranked_state_refs=[b.state_id])
    plan = build_expansion_plan(hyp, expanded=[b.state_id], deferred=[],
                                not_tracked=[])
    states = build_event_states(
        hyp, raw_structures={substrate.state_id: ETHANOL,
                             b.state_id: ACETALDEHYDE})
    store = PollutantPathwayStore(tmp_path / "ppv1.sqlite")
    first = store.submit_event(event, report_projection=report.to_dict(),
                               expansion_plan=plan.to_dict(),
                               states=[s.to_dict() for s in
                                       states.values()])
    again = store.submit_event(event, report_projection=report.to_dict(),
                               expansion_plan=plan.to_dict(),
                               states=[s.to_dict() for s in
                                       states.values()])
    assert first["created"] is True
    assert again["created"] is False     # 同键重放不新增事件
    assert store.counts()["events"] == 1

    # 同键不同内容:改投影内容 → 冲突(不借重放改投影)
    report2 = build_report_projection(
        hyp, max_reportable=1, ranked_state_refs=[])
    with pytest.raises(Ppv1EventConflict):
        store.submit_event(event, report_projection=report2.to_dict(),
                           expansion_plan=plan.to_dict(),
                           states=[s.to_dict() for s in states.values()])
    store.close()


def test_event_transaction_atomicity_on_state_failure(tmp_path) -> None:
    """参与物状态缺结构 → 提交前失败,库内零事件(不部分提交)。"""
    substrate = _state(ETHANOL, STRUCTURE_ORIGIN_RAW_INPUT)
    b = _state(ACETALDEHYDE)
    hyp = build_hypothesis(
        parent_path_id="p1", substrate_state_ref=substrate.state_id,
        participants=[_substrate_participant(substrate.state_id),
                      _product_participant(b.state_id)],
        participant_list_status=PARTICIPANT_LIST_PARTIAL,
        step_scope="net_reaction", origin_group_key="s")
    store = PollutantPathwayStore(tmp_path / "ppv1.sqlite")
    with pytest.raises(ParticipantStateError):
        build_event_states(hyp, raw_structures={
            substrate.state_id: ETHANOL})  # b 缺结构
    assert store.counts()["events"] == 0
    store.close()


def test_catalytic_support_not_in_reaction_stoichiometry() -> None:
    """酶/催化剂另存 catalytic_support,不进净反应计量(§5.3)。"""
    from pathway_v43.pollutant.events import CatalyticSupport

    substrate = _state(ETHANOL, STRUCTURE_ORIGIN_RAW_INPUT)
    b = _state(ACETALDEHYDE)
    hyp = build_hypothesis(
        parent_path_id="p1", substrate_state_ref=substrate.state_id,
        participants=[_substrate_participant(substrate.state_id),
                      _product_participant(b.state_id)],
        participant_list_status=PARTICIPANT_LIST_PARTIAL,
        step_scope="net_reaction", origin_group_key="s")
    event = build_pathway_event(
        hyp, run_id="r-cat", context_hash="ctx",
        catalytic_support=[CatalyticSupport(
            agent_ref="enzyme:EC1.1.3.4", role="catalyst",
            evidence_refs=["src:enz"], status="inferred")])
    # 参与物计量只有底物 + 产物;催化剂在 catalytic_support 块
    assert all(p["state_ref"] in (substrate.state_id, b.state_id)
               for p in event.participants)
    assert event.catalytic_support[0]["agent_ref"] == "enzyme:EC1.1.3.4"


# ---------------------------------------------------------------- A04 legacy


def _build_legacy_store(tmp_path: Path) -> Path:
    """构造一个旧 v43 账本 run(用 PathwayStore 正常写,模拟历史数据)。"""
    from pathway_v43.storage.pathway_store import PathwayStore

    run_dir = tmp_path / "legacy_run"
    run_dir.mkdir(parents=True)
    store = PathwayStore(run_dir / "pathway.sqlite")
    root_pid = store.ensure_run("r-legacy", ETHANOL,
                                _state(ETHANOL).cn_identity)
    # 旧 run 必有 run_identity.json(root 输入从这里恢复)
    (run_dir / "run_identity.json").write_text(json.dumps({
        "schema_version": "v43-identity-1",
        "inputs": {"root_smiles": ETHANOL,
                   "root_identity": _state(ETHANOL).cn_identity},
    }), encoding="utf-8")
    # 一个 novel 平列表事件(2 产物,无共同产物分组信息)
    card = {
        "evidence_id": "E-novel-1",
        "kind": "novel_proposal",
        "source_id": "model|via:novel_proposal",
        "condition_fit": "unknown",
        "_content_hash": "x" * 64,
        "products": [
            {"position": 0, "product_smiles": ACETALDEHYDE,
             "product_smiles_full": ACETALDEHYDE,
             "product_identity": _state(ACETALDEHYDE).cn_identity},
            {"position": 1, "product_smiles": ACETIC,
             "product_smiles_full": ACETIC,
             "product_identity": _state(ACETIC).cn_identity},
        ],
    }
    store.submit_event(run_id="r-legacy", parent_path_id=root_pid,
                       substrate_identity=_state(ETHANOL).cn_identity,
                       evidence=card,
                       products=card["products"],
                       expandable_path_ids=[],
                       deferred_path_ids=[])
    store.close()
    return run_dir


def test_a04_legacy_novel_flat_list_import_labeled(tmp_path: Path) -> None:
    from pathway_v43.pollutant.legacy_reader import import_legacy_run

    legacy_dir = _build_legacy_store(tmp_path)
    db_hash_before = (tmp_path / "legacy_run" / "pathway.sqlite").read_bytes()

    new_store = PollutantPathwayStore(tmp_path / "new" / "ppv1.sqlite")
    result = import_legacy_run(legacy_dir, new_run_id="r-new",
                               target_store=new_store)
    assert result["n_created"] == 1
    assert any("legacy_novel_flat_product_list" in n
               for n in result["uncertainty_notes"])

    events = new_store.list_events("r-new")
    assert len(events) == 1
    hypothesis = new_store.get_hypothesis(events[0]["hypothesis_id"])
    assert hypothesis is not None
    assert hypothesis["legacy_relationship_status"] == \
        LEGACY_RELATIONSHIP_UNSPECIFIED
    # 不猜分组:两产物在同一假设中(平列表原样),未被拆成两个假设
    product_side = [p for p in hypothesis["participants"]
                    if p["side"] == PARTICIPANT_SIDE_PRODUCT]
    assert len(product_side) == 2
    assert hypothesis["participant_list_status"] == "unknown"

    # 旧库零写回(字节级不变)
    db_hash_after = (tmp_path / "legacy_run" / "pathway.sqlite").read_bytes()
    assert db_hash_before == db_hash_after
    new_store.close()


def test_legacy_import_idempotent_replay(tmp_path: Path) -> None:
    from pathway_v43.pollutant.legacy_reader import import_legacy_run

    legacy_dir = _build_legacy_store(tmp_path)
    new_store = PollutantPathwayStore(tmp_path / "new" / "ppv1.sqlite")
    first = import_legacy_run(legacy_dir, new_run_id="r-new",
                              target_store=new_store)
    second = import_legacy_run(legacy_dir, new_run_id="r-new",
                               target_store=new_store)
    assert first["n_created"] == 1
    assert second["n_created"] == 0 and second["n_replayed"] == 1
    assert new_store.counts()["events"] == 1
    new_store.close()


def test_legacy_import_states_recovered_as_archive(tmp_path: Path) -> None:
    from pathway_v43.pollutant.legacy_reader import import_legacy_event, \
        read_legacy_events

    legacy_dir = _build_legacy_store(tmp_path)
    events = read_legacy_events(legacy_dir)
    imported = import_legacy_event(legacy_dir, events[0],
                                   new_run_id="r-new")
    for state in imported["states"]:
        if state["structure_origin"] == "source_product":
            assert state["representation_fidelity"] == \
                REPRESENTATION_ARCHIVE_RECOVERED  # 存档形:不冒称全知
    substrate = [s for s in imported["states"]
                 if s["structure_origin"] == "raw_input"]
    assert substrate and substrate[0]["structure_smiles_raw"] == ETHANOL
