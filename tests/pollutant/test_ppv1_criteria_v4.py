"""ppv1-criteria-v4 / matched_product_hit 回归(2026-10-28)。

预注册草案:
``docs/CRITERIA_V4_MATCHED_PRODUCT_HIT_PREREG_DRAFT_2026-10-28.md``
(§1 定义 / §2 合法事件 / §3 桶 / §4 版本组合)。全部夹具为合成
规则级:零金标、零真实 qid;不外推 dev/298,不构成科学性能声明。

覆盖:
- 版本承载:常量/白名单/resolve/非法值;v4 在 PPV1_CRITERIA_VERSIONS;
- §1 判定:同一事件 S ∈ R_E 且 P ⊆ T_E;superset 事件命中但原
  coverage 事实保留(superset 不改写 exact);跨事件拼答案不命中;
- §2 目标集合:只取产物侧 principal_product(非 principal 的 to 节点
  不进目标集 ⇒ reference_target_empty);
- §3 桶:matched_product_hit / product_hit_partial /
  unmatched_no_event / unmatched_product_mismatch /
  unmatched_reference_invalid(scope 封顶 / 不可解析);
- §4:v2 豁免旁路(计数 0 披露)+ v3 披露轴并列(v4+v3 两者输出、
  互不改写;v1/v2/v3 零 criteria_v4 新键);
- 判分透传:``_product_hit_row`` / ``_product_hit_caliber_block``
  独立块(与 main_caliber strict 分列)。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rdkit import RDLogger  # noqa: E402

RDLogger.DisableLog("rdApp.*")

from pathway_v43.domain.identity import cn_identity  # noqa: E402
from pathway_v43.pollutant.evaluation import (  # noqa: E402
    CRITERIA_V4_BUCKET_MATCHED,
    CRITERIA_V4_BUCKET_NO_EVENT,
    CRITERIA_V4_BUCKET_PARTIAL,
    CRITERIA_V4_BUCKET_PRODUCT_MISMATCH,
    CRITERIA_V4_BUCKET_REFERENCE_INVALID,
    CRITERIA_V4_HIT_MODE_SCOPE,
    CRITERIA_V4_REFERENCE_SCOPE_INSUFFICIENT,
    CRITERIA_V4_REFERENCE_TARGET_EMPTY,
    CRITERIA_V4_REFERENCE_UNPARSEABLE,
    EvaluationContractError,
    PPV1_CRITERIA_V1,
    PPV1_CRITERIA_V2,
    PPV1_CRITERIA_V3,
    PPV1_CRITERIA_V4,
    PPV1_CRITERIA_VERSIONS,
    evaluate_scientific,
    match_reference_edges,
    match_reference_nodes,
    resolve_criteria_version,
)
from pathway_v43.pollutant.profile import (  # noqa: E402
    PPV1_REFERENCE_GRAPH_VERSION,
)
from pathway_v43.pollutant.reference_graph import (  # noqa: E402
    reference_graph_sha256,
    validate_reference_graph,
)
from pathway_v43.pollutant.s5b_scoring import (  # noqa: E402
    _product_hit_caliber_block,
    _product_hit_row,
)

from test_ppv1_s5a_schema import (  # noqa: E402
    synth_evaluation_input,
    synth_split_manifest,
)

# ---- 合成规则常量(零金标零真实 qid)----
SUBSTRATE = "C[C@@H](N)C(=O)O"
PRODUCT_A = "CC=O"
PRODUCT_B = "CC(=O)O"
EXTRA_PRODUCT = "CCO"
OTHER_SUBSTRATE = "CC(=O)O"
QID = "q-syn-v4"
RUN_ID = "r-syn-v4"

_BASE = {
    "reference_graph_id": "rg-syn-v4",
    "schema_version": PPV1_REFERENCE_GRAPH_VERSION,
    "domain": "298",
    "track": "known_evidence_reconstruction",
    "edges": [],
    "provenance_manifest": [{
        "provenance_id": "pv-1", "citation_ref": "cite-1",
        "evidence_basis": "database_recorded_reaction",
        "independent_status": "unknown",
        "observation_scope": "recorded_only",
        "source_conditions": [], "source_group_id": "sg-a",
        "source_origin": "database",
        "structure_match_scope": "strict_structure"}],
    "source_groups": [{
        "source_group_id": "sg-a", "member_records": ["rec-1"],
        "independence_status": "unknown",
        "note": "synthetic rule-level fixture"}],
    "split_assignment": {"split": "development",
                         "route_group_keys": ["rg-syn-v4"],
                         "split_rule_version": "split-rule-1"},
    "coverage_statement": {"covered_axes": ["exact_edges"], "known_gaps": [],
                           "not_evaluable_edge_ids": [],
                           "not_evaluable_node_ids": []},
    "endpoint_annotations": [],
    "creation_review": {"review_status": "pending_user_teacher_review",
                        "reviewer": "synthetic-fixture",
                        "note": "synthetic rule-level fixture"},
}


def _node(node_id: str, smiles: str, role: str,
          scope: str = "strict_structure") -> dict:
    return {
        "node_id": node_id, "state_identity": f"strict:{smiles}",
        "structure_smiles": smiles, "structure_identity_scope": scope,
        "role": role, "occurrence_id": f"occ-{node_id}",
        "source_group_refs": ["sg-a"], "condition_scope": [],
        "provenance_refs": ["pv-1"], "node_status": "observed"}


def _edge(edge_id: str, from_ids: list[str], to_ids: list[str],
          roles: list[str]) -> dict:
    participants = []
    seq = 0
    for node_id, role in zip(from_ids, roles[:len(from_ids)]):
        seq += 1
        participants.append({
            "node_id": node_id, "role": role, "side": "reactant",
            "coefficient": None, "coefficient_status": "unknown"})
    for node_id, role in zip(to_ids, roles[len(from_ids):]):
        seq += 1
        participants.append({
            "node_id": node_id, "role": role, "side": "product",
            "coefficient": None, "coefficient_status": "unknown"})
    return {
        "edge_id": edge_id, "edge_status": "reference_only",
        "from_node_ids": list(from_ids), "to_node_ids": list(to_ids),
        "participants": participants,
        "step_scope": "net_reaction", "condition_requirements": [],
        "provenance_refs": ["pv-1"], "source_group_refs": ["sg-a"],
        "evidence_basis": "database_recorded_reaction",
        "scenario_scope": "rhea_generic_enzymology_no_scenario",
        "coefficient_status": "unknown",
        "participant_list_status": "partial",
        "transformation_ref": f"rhea:{edge_id}",
        "transformation_signature_status": "unknown"}


def _graph(nodes: list[dict], edges: list[dict]) -> dict:
    graph = json.loads(json.dumps(_BASE))
    graph["nodes"] = nodes
    graph["edges"] = edges
    graph["root_entity"] = {
        "entity_id": "ent-1", "structure_smiles_raw": SUBSTRATE,
        "strict_structure_identity": SUBSTRATE, "source_refs": [QID],
        "formal_charge": 0, "isotope_information_status": "unknown",
        "stereo_information_status": "unknown"}
    validate_reference_graph(graph)
    return graph


def _participant(state_id: str, side: str, role: str,
                 seq: int) -> dict:
    return {"state_ref": state_id, "side": side, "role": role,
            "coefficient": None, "coefficient_status": "unknown",
            "entry_id": f"pe-{seq}", "merged_from": [],
            "parallel_contribution": False}


def _event(event_id: str, state_ids: tuple[str, ...],
           *, created_at: str = "2026-01-01T00:00:00Z",
           run_id: str = RUN_ID) -> dict:
    participants = []
    for seq, state_id in enumerate(state_ids, 1):
        side = "reactant" if seq == 1 else "product"
        role = "primary_substrate" if side == "reactant" else (
            "principal_product")
        participants.append(_participant(state_id, side, role, seq))
    return {
        "event_id": event_id, "hypothesis_id": "hyp-1",
        "run_id": run_id, "created_at": created_at,
        "payload": json.dumps({
            "schema_version": "ppv1-event-8",
            "participants": participants,
            "participant_state_refs": [
                p["state_ref"] for p in participants]})}


def _payload(states: dict[str, str], events: list[dict],
             *, hypotheses: list[dict] | None = None) -> dict:
    if hypotheses is None:
        hypotheses = [{"hypothesis_id": "hyp-1", "payload": json.dumps({
            "schema_version": "ppv1-hypothesis-8",
            "step_scope": "net_reaction", "provenance_refs": []})}]
    return {
        "run_id": RUN_ID,
        "states": [{"state_id": state_id,
                    "payload": {"smiles_isomeric": smiles,
                                "cn_identity": cn_identity(smiles)}}
                   for state_id, smiles in states.items()],
        "events": events,
        "hypotheses": hypotheses,
        "provenance_records": [],
    }


def _edges(graph: dict, payload: dict, version: str,
           disclosure: tuple[str, ...] = ()) -> dict:
    node_matches = match_reference_nodes(
        graph, payload, criteria_version=version,
        disclosure_criteria_versions=disclosure)
    edge_matches = match_reference_edges(
        graph, payload, node_matches, criteria_version=version)
    return edge_matches[0]


def _single_graph(**kwargs) -> dict:
    scope = kwargs.get("principal_scope", "strict_structure")
    principal_smiles = kwargs.get("principal_smiles", PRODUCT_A)
    to_role = kwargs.get("to_role", "principal_product")
    return _graph(
        [_node("n-root", SUBSTRATE, "root"),
         _node("n-p1", principal_smiles, to_role, scope)],
        [_edge("e-1", ["n-root"], ["n-p1"], ["substrate", "coproduct"])])


# ---------------------------------------------------------------- 版本承载


def test_criteria_v4_constants_and_whitelist() -> None:
    assert PPV1_CRITERIA_V4 == "ppv1-criteria-v4"
    # 版本断言同步(ppv1-criteria-v5,2026-11-05):白名单新增 v5;
    # 本文件 v4 判定断言面不变
    from pathway_v43.pollutant.evaluation import PPV1_CRITERIA_V5
    assert PPV1_CRITERIA_V5 == "ppv1-criteria-v5"
    assert PPV1_CRITERIA_VERSIONS == {PPV1_CRITERIA_V1, PPV1_CRITERIA_V2,
                                      PPV1_CRITERIA_V3, PPV1_CRITERIA_V4,
                                      PPV1_CRITERIA_V5}
    assert resolve_criteria_version(PPV1_CRITERIA_V4) == PPV1_CRITERIA_V4
    with pytest.raises(EvaluationContractError) as excinfo:
        resolve_criteria_version("ppv1-criteria-v9")
    assert excinfo.value.detail["kind"] == "criteria_version_invalid"
    assert PPV1_CRITERIA_V4 in \
        excinfo.value.detail["allowed"]


def test_criteria_v4_hit_mode_scope_name() -> None:
    assert CRITERIA_V4_HIT_MODE_SCOPE == (
        "declared_principal_products_and_substrate_identity")


# ---------------------------------------------------------------- §1 判定


def test_v4_superset_event_hits_and_coverage_facts_preserved() -> None:
    """多写一个副产物:coverage 仍是 superset(不改写 exact),v4 命中。"""
    graph = _single_graph()
    payload = _payload(
        {"cs-sub": SUBSTRATE, "cs-prod": PRODUCT_A,
         "cs-extra": EXTRA_PRODUCT},
        [_event("ev-1", ("cs-sub", "cs-prod", "cs-extra"))])
    entry = _edges(graph, payload, PPV1_CRITERIA_V4)
    assert entry["matched_events"] == []
    assert entry["match_status"] == \
        "matched_participant_coverage_partial"
    assert entry["coverage_mismatch_events"][0][
        "participant_coverage"] == "superset"
    assert entry["hit_mode_scope"] == CRITERIA_V4_HIT_MODE_SCOPE
    assert entry["matched_product_hit"] is True
    assert entry["product_hit_partial"] is False
    assert entry["product_hit_events"] == ["ev-1"]
    block = entry["criteria_v4"]
    assert block["bucket"] == CRITERIA_V4_BUCKET_MATCHED
    assert block["coverage_facts_preserved"] is True


def test_v4_substrate_and_products_must_share_one_event() -> None:
    """跨事件拼答案不命中:一个事件只有底物,另一个事件只有主产物。"""
    graph = _single_graph()
    payload = _payload(
        {"cs-sub": SUBSTRATE, "cs-other": OTHER_SUBSTRATE,
         "cs-prod": PRODUCT_A},
        [_event("ev-1", ("cs-sub",)),
         _event("ev-2", ("cs-other", "cs-prod"))])
    entry = _edges(graph, payload, PPV1_CRITERIA_V4)
    assert entry["matched_product_hit"] is False
    assert entry["criteria_v4"]["bucket"] == \
        CRITERIA_V4_BUCKET_PRODUCT_MISMATCH


def test_v4_products_must_cover_all_principal_products() -> None:
    """多主产物题:同一事件缺一个主产物 ⇒ 不命中(partial 桶)。"""
    graph = _graph(
        [_node("n-root", SUBSTRATE, "root"),
         _node("n-p1", PRODUCT_A, "principal_product"),
         _node("n-p2", PRODUCT_B, "principal_product")],
        [_edge("e-1", ["n-root"], ["n-p1", "n-p2"],
               ["substrate", "principal_product", "principal_product"])])
    payload = _payload(
        {"cs-sub": SUBSTRATE, "cs-p1": PRODUCT_A, "cs-p2": PRODUCT_B},
        [_event("ev-1", ("cs-sub", "cs-p1"))])
    entry = _edges(graph, payload, PPV1_CRITERIA_V4)
    assert entry["matched_product_hit"] is False
    assert entry["product_hit_partial"] is True
    assert entry["criteria_v4"]["partial_product_hit_events"] == ["ev-1"]
    assert entry["criteria_v4"]["bucket"] == \
        CRITERIA_V4_BUCKET_PARTIAL


def test_v4_partial_bucket_follows_existing_coverage_axis() -> None:
    """旧轴 unmatched(声明必要节点无严格命中)⇒ product_mismatch 桶,
    但「部分主产物命中」零信息损失披露(不静默丢弃)。"""
    graph = _graph(
        [_node("n-root", SUBSTRATE, "root"),
         _node("n-p1", PRODUCT_A, "principal_product"),
         _node("n-p2", PRODUCT_B, "principal_product")],
        [_edge("e-1", ["n-root"], ["n-p1", "n-p2"],
               ["substrate", "principal_product", "principal_product"])])
    # cs-p2 是别的身份 ⇒ n-p2 无严格命中 ⇒ 旧轴 unmatched
    payload = _payload(
        {"cs-sub": SUBSTRATE, "cs-p1": PRODUCT_A,
         "cs-p2": EXTRA_PRODUCT},
        [_event("ev-1", ("cs-sub", "cs-p1"))])
    entry = _edges(graph, payload, PPV1_CRITERIA_V4)
    block = entry["criteria_v4"]
    assert entry["match_status"] == "unmatched_required_node_uncovered"
    assert block["bucket"] == CRITERIA_V4_BUCKET_PRODUCT_MISMATCH
    assert block["product_hit_partial"] is False
    assert block["product_hit_partial_v4_sense"] is True
    assert block["product_hit_partial_outside_legacy_partial"] is True
    assert block["partial_product_hit_events"] == ["ev-1"]


def test_v4_partial_hit_is_not_a_hit_and_full_event_wins() -> None:
    graph = _graph(
        [_node("n-root", SUBSTRATE, "root"),
         _node("n-p1", PRODUCT_A, "principal_product"),
         _node("n-p2", PRODUCT_B, "principal_product")],
        [_edge("e-1", ["n-root"], ["n-p1", "n-p2"],
               ["substrate", "principal_product", "principal_product"])])
    payload = _payload(
        {"cs-sub": SUBSTRATE, "cs-other": OTHER_SUBSTRATE,
         "cs-p1": PRODUCT_A, "cs-p2": PRODUCT_B},
        [_event("ev-1", ("cs-sub", "cs-p1")),
         _event("ev-2", ("cs-other", "cs-p1", "cs-p2")),
         _event("ev-3", ("cs-sub", "cs-p1", "cs-p2"))])
    entry = _edges(graph, payload, PPV1_CRITERIA_V4)
    assert entry["product_hit_events"] == ["ev-3"]
    assert entry["criteria_v4"]["bucket"] == CRITERIA_V4_BUCKET_MATCHED


def test_v4_target_set_only_principal_products() -> None:
    """参考边 to 侧不是 principal_product ⇒ 目标集为空(不拿中间体顶替)。"""
    graph = _single_graph(to_role="intermediate")
    payload = _payload(
        {"cs-sub": SUBSTRATE, "cs-prod": PRODUCT_A},
        [_event("ev-1", ("cs-sub", "cs-prod"))])
    entry = _edges(graph, payload, PPV1_CRITERIA_V4)
    block = entry["criteria_v4"]
    assert block["reference_status"] == "not_evaluable"
    assert block["reference_invalid_reason"] == \
        CRITERIA_V4_REFERENCE_TARGET_EMPTY
    assert block["bucket"] == CRITERIA_V4_BUCKET_REFERENCE_INVALID


def test_v4_identity_scope_capped_is_reference_invalid() -> None:
    """S5A-01 封顶节点(scope != strict_structure)⇒ 参考无效,不真空通过。"""
    graph = _single_graph(principal_scope="cn_only")
    payload = _payload(
        {"cs-sub": SUBSTRATE, "cs-prod": PRODUCT_A},
        [_event("ev-1", ("cs-sub", "cs-prod"))])
    entry = _edges(graph, payload, PPV1_CRITERIA_V4)
    block = entry["criteria_v4"]
    assert block["reference_invalid_reason"] == \
        CRITERIA_V4_REFERENCE_SCOPE_INSUFFICIENT
    assert block["bucket"] == CRITERIA_V4_BUCKET_REFERENCE_INVALID


def test_v4_unparseable_reference_is_reference_invalid() -> None:
    graph = _single_graph(principal_smiles="not-a-smiles")
    payload = _payload(
        {"cs-sub": SUBSTRATE, "cs-prod": PRODUCT_A},
        [_event("ev-1", ("cs-sub", "cs-prod"))])
    # 参考节点不可解析 ⇒ 节点匹配 reference_structure_unparseable;
    # 边匹配的 v4 块给 not_evaluable(不猜目标)
    node_matches = match_reference_nodes(
        graph, payload, criteria_version=PPV1_CRITERIA_V4)
    edge_matches = match_reference_edges(
        graph, payload, node_matches, criteria_version=PPV1_CRITERIA_V4)
    block = edge_matches[0]["criteria_v4"]
    assert block["reference_status"] == "not_evaluable"
    assert block["reference_invalid_reason"] == \
        CRITERIA_V4_REFERENCE_UNPARSEABLE


def test_v4_no_events_is_no_event_bucket() -> None:
    graph = _single_graph()
    payload = _payload({"cs-sub": SUBSTRATE}, [])
    entry = _edges(graph, payload, PPV1_CRITERIA_V4)
    assert entry["criteria_v4"]["bucket"] == \
        CRITERIA_V4_BUCKET_NO_EVENT
    assert entry["matched_product_hit"] is False


def test_v4_step_scope_mismatch_event_is_illegal() -> None:
    graph = _single_graph()
    payload = _payload(
        {"cs-sub": SUBSTRATE, "cs-prod": PRODUCT_A},
        [_event("ev-1", ("cs-sub", "cs-prod"))],
        hypotheses=[{"hypothesis_id": "hyp-1", "payload": json.dumps({
            "schema_version": "ppv1-hypothesis-8",
            "step_scope": "elementary_step", "provenance_refs": []})}])
    entry = _edges(graph, payload, PPV1_CRITERIA_V4)
    block = entry["criteria_v4"]
    assert block["eligible_event_count"] == 0
    assert block["ineligible_event_reasons"] == {
        "step_scope_mismatch": 1}
    assert block["bucket"] == CRITERIA_V4_BUCKET_NO_EVENT


# ---------------------------------------------------------------- §4 版本组合


def test_v4_does_not_emit_v2_exemption_block() -> None:
    """v4 旁路 v2 豁免:输出无 criteria_v2,豁免计数 0 披露。"""
    graph = _single_graph()
    payload = _payload(
        {"cs-sub": SUBSTRATE, "cs-prod": PRODUCT_A,
         "cs-extra": EXTRA_PRODUCT},
        [_event("ev-1", ("cs-sub", "cs-prod", "cs-extra"))])
    output = evaluate_scientific(
        _evaluation_input(graph), reference_graphs={graph["reference_graph_id"]: graph},
        native_export_reader=_fake_reader(payload),
        criteria_version=PPV1_CRITERIA_V4)
    assert "criteria_v2" not in output
    block = output["criteria_v4"]
    assert block["exemption_bypassed"] is True
    assert block["exemption_counts"]["edges_with_exemption"] == 0
    assert block["exemption_counts"]["tier_counts"] == {
        "v1_exempt": 0, "not_exempt_maintains_partial": 0}
    assert block["matched_product_hit"] == 1
    assert block["denominator"] == 1


def test_v4_keeps_legacy_strict_bucket_separate() -> None:
    graph = _single_graph()
    payload = _payload(
        {"cs-sub": SUBSTRATE, "cs-prod": PRODUCT_A,
         "cs-extra": EXTRA_PRODUCT},
        [_event("ev-1", ("cs-sub", "cs-prod", "cs-extra"))])
    output = evaluate_scientific(
        _evaluation_input(graph),
        reference_graphs={graph["reference_graph_id"]: graph},
        native_export_reader=_fake_reader(payload),
        criteria_version=PPV1_CRITERIA_V4)
    block = output["criteria_v4"]
    assert block["matched_product_hit"] == 1
    assert block["legacy_match_status_bucket_counts"] == {
        "matched_participant_coverage_partial": 1}


def test_v4_and_v3_coexist_without_rewriting() -> None:
    """v4 主口径 + v3 披露轴同时启用:两者都输出,互不改写。"""
    graph = _single_graph()
    payload = _payload(
        {"cs-sub": SUBSTRATE, "cs-prod": PRODUCT_A},
        [_event("ev-1", ("cs-sub", "cs-prod"))])
    graphs = {graph["reference_graph_id"]: graph}
    inp = _evaluation_input(graph)
    v4_only = evaluate_scientific(
        inp, reference_graphs=graphs,
        native_export_reader=_fake_reader(payload),
        criteria_version=PPV1_CRITERIA_V4)
    both = evaluate_scientific(
        inp, reference_graphs=graphs,
        native_export_reader=_fake_reader(payload),
        criteria_version=PPV1_CRITERIA_V4,
        disclosure_criteria_versions=(PPV1_CRITERIA_V3,))
    v3_only = evaluate_scientific(
        inp, reference_graphs=graphs,
        native_export_reader=_fake_reader(payload),
        criteria_version=PPV1_CRITERIA_V3)
    assert "criteria_v3" not in v4_only
    assert both["criteria_v3"] == v3_only["criteria_v3"]
    assert both["criteria_v4"] == v4_only["criteria_v4"]
    v4_sample = both["sample_results"][0]["criteria_v4"]
    assert v4_sample["matched_product_hit"] is True
    node_blocks = [entry.get("criteria_v3_normalized_identity")
                   for entry in both["sample_results"][0][
                       "predicted_node_matches"]]
    assert all(block is not None for block in node_blocks)


def test_v1_v2_v3_outputs_have_no_criteria_v4_key() -> None:
    graph = _single_graph()
    payload = _payload(
        {"cs-sub": SUBSTRATE, "cs-prod": PRODUCT_A},
        [_event("ev-1", ("cs-sub", "cs-prod"))])
    graphs = {graph["reference_graph_id"]: graph}
    for version in (PPV1_CRITERIA_V1, PPV1_CRITERIA_V2,
                    PPV1_CRITERIA_V3):
        output = evaluate_scientific(
            _evaluation_input(graph), reference_graphs=graphs,
            native_export_reader=_fake_reader(payload),
            criteria_version=version)
        assert "criteria_v4" not in output
        sample = output["sample_results"][0]
        assert "criteria_v4" not in sample
        assert "matched_product_hit" not in sample
        assert "hit_mode_scope" not in sample


def test_disclosure_versions_reject_non_disclosure_axis() -> None:
    graph = _single_graph()
    payload = _payload({"cs-sub": SUBSTRATE}, [])
    with pytest.raises(EvaluationContractError) as excinfo:
        evaluate_scientific(
            _evaluation_input(graph),
            reference_graphs={graph["reference_graph_id"]: graph},
            native_export_reader=_fake_reader(payload),
            criteria_version=PPV1_CRITERIA_V4,
            disclosure_criteria_versions=(PPV1_CRITERIA_V2,))
    assert excinfo.value.detail["kind"] == \
        "criteria_disclosure_version_not_disclosure_axis"
    with pytest.raises(EvaluationContractError) as excinfo:
        evaluate_scientific(
            _evaluation_input(graph),
            reference_graphs={graph["reference_graph_id"]: graph},
            native_export_reader=_fake_reader(payload),
            criteria_version=PPV1_CRITERIA_V4,
            disclosure_criteria_versions=("ppv1-criteria-v9",))
    assert excinfo.value.detail["kind"] == \
        "criteria_disclosure_version_invalid"


# ---------------------------------------------------------------- 判分透传


def test_product_hit_row_rank_uses_pre_fixed_candidate_order() -> None:
    graph = _single_graph()
    payload = _payload(
        {"cs-sub": SUBSTRATE, "cs-other": OTHER_SUBSTRATE,
         "cs-prod": PRODUCT_A},
        [_event("ev-1", ("cs-other", "cs-prod"),
                created_at="2026-01-01T00:00:00Z"),
         _event("ev-2", ("cs-sub", "cs-prod"),
                created_at="2026-01-01T00:00:01Z")])
    sample = {
        "scoring_status": "scored",
        "predicted_edge_matches": [{
            "match_status": "matched_participant_coverage_partial"}],
        "predicted_node_matches": match_reference_nodes(
            graph, payload, criteria_version=PPV1_CRITERIA_V4),
        "criteria_v4": {"bucket": CRITERIA_V4_BUCKET_MATCHED,
                        "product_hit_events": ["ev-2"]},
    }
    row = _product_hit_row(sample, payload, graph)
    assert row["rank"] == 1
    assert row["bucket"] == CRITERIA_V4_BUCKET_MATCHED
    assert row["matched_event_not_in_candidates"] is False


def test_product_hit_row_without_hit_has_null_rank() -> None:
    graph = _single_graph()
    payload = _payload(
        {"cs-sub": SUBSTRATE, "cs-other": OTHER_SUBSTRATE,
         "cs-prod": PRODUCT_A},
        [_event("ev-1", ("cs-other", "cs-prod"))])
    sample = {
        "scoring_status": "scored",
        "predicted_edge_matches": [{
            "match_status": "matched_participant_coverage_partial"}],
        "predicted_node_matches": match_reference_nodes(
            graph, payload, criteria_version=PPV1_CRITERIA_V4),
        "criteria_v4": {
            "bucket": CRITERIA_V4_BUCKET_PRODUCT_MISMATCH,
            "product_hit_events": []},
    }
    row = _product_hit_row(sample, payload, graph)
    assert row["rank"] is None
    assert row["matched_product_hit"] is False


def test_product_hit_caliber_block_separate_and_closed() -> None:
    rows = [
        {"rank": 1, "bucket": CRITERIA_V4_BUCKET_MATCHED},
        {"rank": 3, "bucket": CRITERIA_V4_BUCKET_MATCHED},
        {"rank": None, "bucket": CRITERIA_V4_BUCKET_PARTIAL},
        {"rank": None, "bucket": CRITERIA_V4_BUCKET_NO_EVENT},
        {"rank": None, "bucket": CRITERIA_V4_BUCKET_REFERENCE_INVALID},
        {"rank": None, "bucket": CRITERIA_V4_BUCKET_PRODUCT_MISMATCH},
    ]
    block = _product_hit_caliber_block(rows, 6)
    assert block["matched_product_hit"] == 2
    assert block["product_hit_partial"] == 1
    assert block["hit@1"] == 1
    assert block["hit@3"] == 2
    assert block["hit@5"] == 2
    assert sum(block["buckets"].values()) == 6
    assert block["separate_from_strict"] is True
    assert block["metric_name"] == "matched_product_hit"


def test_render_report_lists_matched_product_hit_separately() -> None:
    """报表新指标与旧 strict 分列(不得同名/不得混排)。"""
    from pathway_v43.pollutant.s5b_scoring import (
        render_plain_report, render_report)
    rows = [{"rank": 1, "bucket": CRITERIA_V4_BUCKET_MATCHED},
            {"rank": None, "bucket": CRITERIA_V4_BUCKET_NO_EVENT}]
    v4_block = _product_hit_caliber_block(rows, 2)
    aggregate = {
        "domain_tag": "298",
        "denominator": 2,
        "data_scope": "synthetic_rule_level",
        "evaluator_output_status": "interface_verified_only",
        "main_caliber": {
            "hit@1": 1, "hit@3": 1, "hit@5": 1,
            "hit@1_rate": 0.5, "hit@3_rate": 0.5, "hit@5_rate": 0.5,
            "definition": "strict definition",
            "pass_line_semantics": "strict semantics"},
        "old_caliber_sensitivity": {
            "hit@1": 0, "hit@3": 0, "hit@5": 0,
            "hit@1_rate": 0.0, "hit@3_rate": 0.0, "hit@5_rate": 0.0,
            "definition": "old definition"},
        "old_caliber_anyof_multicomponent": {
            "hit@1": 0, "hit@3": 0, "hit@5": 0},
        "buckets": {"matched_strict": 1,
                    "unmatched_required_node_uncovered": 1},
        "run_status_table": {"completed": 2},
        "aggregate_diagnosis": {
            "U_strict_matched_questions": 1, "H5": 1, "L_below_k": 0},
        "confidence_intervals": {},
        "matched_product_hit_caliber": v4_block,
    }
    md = render_report(aggregate, {})
    assert "## 主口径" in md
    assert "## matched_product_hit 口径" in md
    assert "不得同名" in md
    assert "matched_product_hit" in md
    plain = render_plain_report(aggregate)
    assert "matched_product_hit" in plain
    assert "不是 strict" in plain


# ---------------------------------------------------------------- 夹具


def _fake_reader(payload: dict):
    blob = json.dumps(payload)

    def reader(entry):  # noqa: ARG001 —— 合成读取通道
        return {"payload": json.loads(blob)}

    return reader


def _evaluation_input(graph: dict) -> dict:
    inp = synth_evaluation_input(
        domain="298", graphs=[graph],
        split_manifest=synth_split_manifest(
            graph_id=graph["reference_graph_id"],
            group_ids=["sg-a"]),
        exports=[{"run_id": RUN_ID, "export_digest": "d" * 32,
                  "qid": QID, "lossy_projection": False}])
    inp["run_identity"]["run_id"] = RUN_ID
    inp["reference_graph_manifest"] = [{
        "reference_graph_id": graph["reference_graph_id"],
        "sha256": reference_graph_sha256(graph), "domain": "298",
        "track": "known_evidence_reconstruction", "qid": QID}]
    return inp