"""ppv1-criteria-v5 / role_bound_product_hit 回归(2026-11-05)。

预注册草案(已签 v2):
``docs/tasks/active/CRITERIA_V5_ROLE_BOUND_PREREG_DRAFT_2026-11-05.md``
(§1 判据 / §2 合法事件五条件与五桶 / §5 披露轴 / §7 负控电池 / §8 翻转)。
全部夹具为合成规则级:零金标、零真实 qid;不外推 dev/298,不构成
科学性能声明。

覆盖:
- 版本承载:常量/白名单/resolve/非法值结构化拒;v5 在
  PPV1_CRITERIA_VERSIONS;
- §7 负控电池 NC-1(三变体)/NC-2/NC-3/NC-4/NC-5:双口径断言
  (v4 与 v5 各判一次),任一负控 v5 >0 或 v5 > v4 即否决;
- §7 正控 PC-1/PC-2/PC-3;
- A.2 六用例(A 对冲 / B 角色互换 / C 负控 / D 参考侧控 / E 诚实 /
  F 多报压力);
- §1 角色缺失 fail-closed(缺失/空/unknown/大小写/其它字符串不进
  ``T_E^principal``);
- §5.1 披露 6 字段 + 分桶;§5.2 只输出 unknown / not_applicable;
- §8 单调性夹具级核对(v5 命中 ⇒ v4 命中;v1–v4 输出零 v5 键);
- 判分透传:``_role_bound_hit_row`` / ``_role_bound_hit_caliber_block``
  独立块(与 main_caliber strict、v4 matched_product_hit 分列)。
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
from pathway_v43.pollutant.chemstate import strict_identity_of  # noqa: E402
from pathway_v43.pollutant.evaluation import (  # noqa: E402
    CRITERIA_V5_BUCKET_MATCHED,
    CRITERIA_V5_BUCKET_NO_EVENT,
    CRITERIA_V5_BUCKET_PARTIAL,
    CRITERIA_V5_BUCKET_PRODUCT_MISMATCH,
    CRITERIA_V5_BUCKET_REFERENCE_INVALID,
    CRITERIA_V5_BUCKETS,
    CRITERIA_V5_EVENT_PRINCIPAL_ROLE,
    CRITERIA_V5_HIT_MODE_SCOPE,
    CRITERIA_V4_REFERENCE_TARGET_EMPTY,
    EvaluationContractError,
    PPV1_CRITERIA_V1,
    PPV1_CRITERIA_V2,
    PPV1_CRITERIA_V3,
    PPV1_CRITERIA_V4,
    PPV1_CRITERIA_V5,
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
    _role_bound_hit_caliber_block,
    _role_bound_hit_row,
)

from test_ppv1_s5a_schema import (  # noqa: E402
    synth_evaluation_input,
    synth_split_manifest,
)

# ---- 合成规则常量(零金标零真实 qid;通用分子)----
SUBSTRATE = "C[C@@H](N)C(=O)O"          # 丙氨酸(占位底物)
PRODUCT_A = "CC=O"                       # 乙醛(参考主产物)
PRODUCT_B = "CC(=O)O"                    # 乙酸(第二主产物/干扰)
OTHER_SUBSTRATE = "CC(=O)O"              # 与底物不同的"回显"分子
WRONG_PRODUCT = "CCC=O"                  # 错误产物
WATER = "O"
CARBON_DIOXIDE = "O=C=O"
AMMONIA = "N"
FILLER = ["CCO", "CCCO", "CC(C)O", "CCCCO", "CCCC(=O)C", "CC(C)=O",
          "CCOC", "CCC(C)O", "CCCC=O", "CC(C)C=O", "OCC(O)CO",
          "CC(O)C(=O)O"]
QID = "q-syn-v5"
RUN_ID = "r-syn-v5"

_BASE = {
    "reference_graph_id": "rg-syn-v5",
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
                         "route_group_keys": ["rg-syn-v5"],
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
    for node_id, role in zip(from_ids, roles[:len(from_ids)]):
        participants.append({
            "node_id": node_id, "role": role, "side": "reactant",
            "coefficient": None, "coefficient_status": "unknown"})
    for node_id, role in zip(to_ids, roles[len(from_ids):]):
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


def _single_graph(principal: str = PRODUCT_A,
                  to_role: str = "principal_product") -> dict:
    return _graph(
        [_node("n-root", SUBSTRATE, "root"),
         _node("n-p1", principal, to_role)],
        [_edge("e-1", ["n-root"], ["n-p1"], ["substrate", "coproduct"])])


def _participant(state_id: str, side: str, role, seq: int) -> dict:
    row = {"state_ref": state_id, "side": side,
           "coefficient": None, "coefficient_status": "unknown",
           "entry_id": f"pe-{seq}", "merged_from": [],
           "parallel_contribution": False}
    if role is not None:  # role=None ⇒ 键缺失(fail-closed 语义)
        row["role"] = role
    return row


def _event(event_id: str, entries: list[tuple[str, str, object]],
           *, created_at: str = "2026-01-01T00:00:00Z",
           run_id: str = RUN_ID) -> dict:
    """``entries`` = [(state_id, side, role), ...];role=None ⇒ 键缺失。"""
    participants = [
        _participant(state_id, side, role, seq)
        for seq, (state_id, side, role) in enumerate(entries, 1)]
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
            "step_scope": "net_reaction", "provenance_refs": [],
            # T4c-2:§5.2 C4* 的清单完整度门读 hypothesis 的该字段
            # (合成夹具显式声明清单完整;系数仍为 unknown)
            "participant_list_status": "declared_complete",
            "ambiguous_participants": False})}]
    return {
        "run_id": RUN_ID,
        "states": [{"state_id": state_id,
                    "payload": {"smiles_isomeric":
                                strict_identity_of(smiles),
                                "cn_identity": cn_identity(smiles)}}
                   for state_id, smiles in states.items()],
        "events": events,
        "hypotheses": hypotheses,
        "provenance_records": [],
    }


def _judge(graph: dict, payload: dict, version: str) -> dict:
    """返回 (entry, block, hit, bucket) 的紧凑字典(双口径各自调用)。"""
    node_matches = match_reference_nodes(
        graph, payload, criteria_version=version)
    entry = match_reference_edges(
        graph, payload, node_matches, criteria_version=version)[0]
    if version == PPV1_CRITERIA_V4:
        block = entry["criteria_v4"]
        return {"entry": entry, "block": block,
                "hit": bool(block["matched_product_hit"]),
                "bucket": block["bucket"]}
    block = entry["criteria_v5"]
    return {"entry": entry, "block": block,
            "hit": bool(block["role_bound_product_hit"]),
            "bucket": block["bucket"]}


def _dual(graph: dict, payload: dict) -> tuple[dict, dict]:
    return (_judge(graph, payload, PPV1_CRITERIA_V4),
            _judge(graph, payload, PPV1_CRITERIA_V5))


# ---------------------------------------------------------------- 版本承载


def test_criteria_v5_constants_and_whitelist() -> None:
    assert PPV1_CRITERIA_V5 == "ppv1-criteria-v5"
    assert CRITERIA_V5_HIT_MODE_SCOPE == (
        "declared_principal_products_and_substrate_identity_role_bound")
    assert CRITERIA_V5_EVENT_PRINCIPAL_ROLE == "principal_product"
    assert PPV1_CRITERIA_VERSIONS == {PPV1_CRITERIA_V1, PPV1_CRITERIA_V2,
                                      PPV1_CRITERIA_V3, PPV1_CRITERIA_V4,
                                      PPV1_CRITERIA_V5}
    assert resolve_criteria_version(PPV1_CRITERIA_V5) == PPV1_CRITERIA_V5
    assert CRITERIA_V5_BUCKETS == (
        "role_bound_product_hit", "product_hit_partial",
        "unmatched_no_event", "unmatched_reference_invalid",
        "unmatched_product_mismatch")


def test_criteria_v5_unknown_version_is_structurally_rejected() -> None:
    """fail-closed:未登记版本不得静默回退到 v4。"""
    with pytest.raises(EvaluationContractError) as excinfo:
        resolve_criteria_version("ppv1-criteria-v9")
    assert excinfo.value.detail["kind"] == "criteria_version_invalid"
    assert PPV1_CRITERIA_V5 in excinfo.value.detail["allowed"]


# ---------------------------------------------------------------- §7 负控电池


def test_nc1_empty_event_variants_score_zero_in_both_calibers() -> None:
    """NC-1 三变体:无事件 / 事件无参与物 / 产物侧为空 ⇒ 两口径 0。"""
    graph = _single_graph()
    variants = {
        "no_event": _payload({"cs-sub": SUBSTRATE}, []),
        "event_without_participants": _payload(
            {"cs-sub": SUBSTRATE}, [_event("ev-1", [])]),
        "product_side_empty": _payload(
            {"cs-sub": SUBSTRATE},
            [_event("ev-1", [("cs-sub", "reactant", "primary_substrate")])]),
    }
    for name, payload in variants.items():
        v4, v5 = _dual(graph, payload)
        assert v4["hit"] is False, name
        assert v5["hit"] is False, name
        assert v5["bucket"] == CRITERIA_V5_BUCKET_NO_EVENT, name
        assert int(v5["hit"]) <= int(v4["hit"]), name


def test_nc2_substrate_echo_scores_zero_in_both_calibers() -> None:
    """NC-2:产物侧只有底物本身(标 principal)⇒ 两口径 0。"""
    graph = _single_graph()
    # 同一个 state 不能同时作反应物与产物 → 另造回显 state
    payload = _payload(
        {"cs-sub": SUBSTRATE, "cs-echo": SUBSTRATE},
        [_event("ev-1", [("cs-sub", "reactant", "primary_substrate"),
                         ("cs-echo", "product", "principal_product")])])
    v4, v5 = _dual(graph, payload)
    assert v4["hit"] is False
    assert v5["hit"] is False
    assert int(v5["hit"]) <= int(v4["hit"])


def test_nc3_all_pool_products_in_coproduct_slot_v4_hits_v5_misses() -> None:
    """NC-3:参考主产物只在 coproduct 位 ⇒ v4 可中,v5 必须 0。"""
    graph = _single_graph()
    payload = _payload(
        {"cs-sub": SUBSTRATE, "cs-gold": PRODUCT_A,
         "cs-wrong": WRONG_PRODUCT},
        [_event("ev-1", [("cs-sub", "reactant", "primary_substrate"),
                         ("cs-wrong", "product", "principal_product"),
                         ("cs-gold", "product", "coproduct")])])
    v4, v5 = _dual(graph, payload)
    assert v4["hit"] is True          # v4 角色盲(空子存在)
    assert v5["hit"] is False         # v5 必须挡住
    assert v5["bucket"] == CRITERIA_V5_BUCKET_PRODUCT_MISMATCH
    assert int(v5["hit"]) <= int(v4["hit"])


def test_nc4_role_swap_v4_hits_v5_misses() -> None:
    """NC-4:主产物标 coproduct、错误产物标 principal ⇒ v4 可中,v5 0。"""
    graph = _single_graph()
    payload = _payload(
        {"cs-sub": SUBSTRATE, "cs-gold": PRODUCT_A,
         "cs-wrong": WRONG_PRODUCT},
        [_event("ev-1", [("cs-sub", "reactant", "primary_substrate"),
                         ("cs-wrong", "product", "principal_product"),
                         ("cs-gold", "product", "coproduct")])])
    v4, v5 = _dual(graph, payload)
    assert v4["hit"] is True
    assert v5["hit"] is False
    assert int(v5["hit"]) <= int(v4["hit"])


def test_nc5_small_inorganic_in_principal_slot_v5_zero() -> None:
    """NC-5:principal 位写小无机物,参考主产物缺席或只在 coproduct 位。"""
    graph = _single_graph()
    # (a) 参考主产物只在 coproduct 位,principal 位写水
    payload_a = _payload(
        {"cs-sub": SUBSTRATE, "cs-gold": PRODUCT_A,
         "cs-water": WATER},
        [_event("ev-1", [("cs-sub", "reactant", "primary_substrate"),
                         ("cs-water", "product", "principal_product"),
                         ("cs-gold", "product", "coproduct")])])
    # (b) 参考主产物完全缺席
    payload_b = _payload(
        {"cs-sub": SUBSTRATE, "cs-water": WATER,
         "cs-co2": CARBON_DIOXIDE, "cs-nh3": AMMONIA},
        [_event("ev-1", [("cs-sub", "reactant", "primary_substrate"),
                         ("cs-water", "product", "principal_product"),
                         ("cs-co2", "product", "principal_product"),
                         ("cs-nh3", "product", "principal_product")])])
    for payload in (payload_a, payload_b):
        v4, v5 = _dual(graph, payload)
        assert v5["hit"] is False
        assert int(v5["hit"]) <= int(v4["hit"])


# ---------------------------------------------------------------- §7 正控


def test_pc1_honest_single_principal_hits_both() -> None:
    graph = _single_graph()
    payload = _payload(
        {"cs-sub": SUBSTRATE, "cs-p1": PRODUCT_A},
        [_event("ev-1", [("cs-sub", "reactant", "primary_substrate"),
                         ("cs-p1", "product", "principal_product")])])
    v4, v5 = _dual(graph, payload)
    assert v4["hit"] is True
    assert v5["hit"] is True
    assert v5["bucket"] == CRITERIA_V5_BUCKET_MATCHED


def test_pc2_honest_multi_product_with_coproduct_hits_both() -> None:
    graph = _single_graph()
    payload = _payload(
        {"cs-sub": SUBSTRATE, "cs-p1": PRODUCT_A,
         "cs-water": WATER, "cs-co2": CARBON_DIOXIDE},
        [_event("ev-1", [("cs-sub", "reactant", "primary_substrate"),
                         ("cs-p1", "product", "principal_product"),
                         ("cs-water", "product", "coproduct"),
                         ("cs-co2", "product", "coproduct")])])
    v4, v5 = _dual(graph, payload)
    assert v4["hit"] is True
    assert v5["hit"] is True


@pytest.mark.parametrize("role", [None, "", "unknown", "Unknown"])
def test_pc3_role_missing_or_unknown_is_not_hit(role) -> None:
    """PC-3:正确主产物但 role 缺失/未知 ⇒ v5 不命中(fail-closed)。"""
    graph = _single_graph()
    payload = _payload(
        {"cs-sub": SUBSTRATE, "cs-p1": PRODUCT_A},
        [_event("ev-1", [("cs-sub", "reactant", "primary_substrate"),
                         ("cs-p1", "product", role)])])
    v4, v5 = _dual(graph, payload)
    assert v4["hit"] is True            # v4 角色盲
    assert v5["hit"] is False
    assert v5["bucket"] == CRITERIA_V5_BUCKET_PRODUCT_MISMATCH
    events = v5["block"]["events"]
    assert events[0]["role_missing_or_unknown_present"] is True
    assert int(v5["hit"]) <= int(v4["hit"])


# ---------------------------------------------------------------- A.2 六用例


def test_a2_a_hedging_v4_hits_v5_misses() -> None:
    """A 对冲:错误 principal + 金标 coproduct + 6 无关 coproduct,账不平。"""
    graph = _single_graph()
    states = {"cs-sub": SUBSTRATE, "cs-wrong": WRONG_PRODUCT,
              "cs-gold": PRODUCT_A}
    entries = [("cs-sub", "reactant", "primary_substrate"),
               ("cs-wrong", "product", "principal_product"),
               ("cs-gold", "product", "coproduct")]
    for index, smiles in enumerate(FILLER[:6]):
        states[f"cs-f{index}"] = smiles
        entries.append((f"cs-f{index}", "product", "coproduct"))
    payload = _payload(states, [_event("ev-1", entries)])
    v4, v5 = _dual(graph, payload)
    assert v4["hit"] is True
    assert v5["hit"] is False
    assert v5["bucket"] == CRITERIA_V5_BUCKET_PRODUCT_MISMATCH


def test_a2_b_role_swap_v4_hits_v5_misses() -> None:
    graph = _single_graph()
    payload = _payload(
        {"cs-sub": SUBSTRATE, "cs-wrong": WRONG_PRODUCT,
         "cs-gold": PRODUCT_A},
        [_event("ev-1", [("cs-sub", "reactant", "primary_substrate"),
                         ("cs-wrong", "product", "principal_product"),
                         ("cs-gold", "product", "coproduct")])])
    v4, v5 = _dual(graph, payload)
    assert v4["hit"] is True
    assert v5["hit"] is False


def test_a2_c_negative_control_both_miss() -> None:
    graph = _single_graph()
    payload = _payload(
        {"cs-sub": SUBSTRATE, "cs-wrong": WRONG_PRODUCT},
        [_event("ev-1", [("cs-sub", "reactant", "primary_substrate"),
                         ("cs-wrong", "product", "principal_product")])])
    v4, v5 = _dual(graph, payload)
    assert v4["hit"] is False
    assert v5["hit"] is False
    assert v5["bucket"] == CRITERIA_V5_BUCKET_PRODUCT_MISMATCH


def test_a2_d_reference_side_control_not_evaluable_in_both() -> None:
    """D 参考侧控:参考图金标节点 role=coproduct ⇒ P=∅ ⇒ 两口径不评。"""
    graph = _single_graph(to_role="coproduct")
    payload = _payload(
        {"cs-sub": SUBSTRATE, "cs-p1": PRODUCT_A},
        [_event("ev-1", [("cs-sub", "reactant", "primary_substrate"),
                         ("cs-p1", "product", "principal_product")])])
    v4, v5 = _dual(graph, payload)
    assert v4["hit"] is False
    assert v5["hit"] is False
    assert v4["bucket"] == CRITERIA_V5_BUCKET_REFERENCE_INVALID
    assert v5["bucket"] == CRITERIA_V5_BUCKET_REFERENCE_INVALID
    assert v5["block"]["reference_invalid_reason"] == \
        CRITERIA_V4_REFERENCE_TARGET_EMPTY


def test_a2_e_honest_model_hits_both_without_collateral_damage() -> None:
    graph = _single_graph()
    payload = _payload(
        {"cs-sub": SUBSTRATE, "cs-p1": PRODUCT_A},
        [_event("ev-1", [("cs-sub", "reactant", "primary_substrate"),
                         ("cs-p1", "product", "principal_product")])])
    v4, v5 = _dual(graph, payload)
    assert v4["hit"] is True
    assert v5["hit"] is True


def test_a2_f_multi_report_pressure_hits_both_and_discloses_width() -> None:
    """F 多报压力:正确 principal + 12 无关 coproduct ⇒ 两口径都中。

    v5 不罚多报(预注册 §10 已披露缺口),由 §5.1 产物种数分布承担。
    """
    graph = _single_graph()
    states = {"cs-sub": SUBSTRATE, "cs-p1": PRODUCT_A}
    entries = [("cs-sub", "reactant", "primary_substrate"),
               ("cs-p1", "product", "principal_product")]
    for index, smiles in enumerate(FILLER):
        states[f"cs-x{index}"] = smiles
        entries.append((f"cs-x{index}", "product", "coproduct"))
    payload = _payload(states, [_event("ev-1", entries)])
    v4, v5 = _dual(graph, payload)
    assert v4["hit"] is True
    assert v5["hit"] is True
    row = v5["block"]["events"][0]
    assert row["n_coproduct_species"] == 12
    assert row["n_product_species_total"] == 13
    assert row["product_species_bucket"] == ">8"
    assert row["coproduct_traceability"] == "unknown"


# ---------------------------------------------------------------- 角色词表


@pytest.mark.parametrize("role", ["Principal_Product", "principalproduct",
                                  "main_product", "substrate",
                                  "coproduct"])
def test_v5_role_vocabulary_is_exact_and_fail_closed(role) -> None:
    graph = _single_graph()
    payload = _payload(
        {"cs-sub": SUBSTRATE, "cs-p1": PRODUCT_A},
        [_event("ev-1", [("cs-sub", "reactant", "primary_substrate"),
                         ("cs-p1", "product", role)])])
    v4, v5 = _dual(graph, payload)
    assert v4["hit"] is True
    assert v5["hit"] is False


# ---------------------------------------------------------------- §5 披露轴


def test_v5_disclosure_fields_and_species_bucket() -> None:
    graph = _single_graph()
    payload = _payload(
        {"cs-sub": SUBSTRATE, "cs-p1": PRODUCT_A,
         "cs-water": WATER, "cs-co2": CARBON_DIOXIDE,
         "cs-eth": "CCO"},
        [_event("ev-1", [("cs-sub", "reactant", "primary_substrate"),
                         ("cs-p1", "product", "principal_product"),
                         ("cs-water", "product", "coproduct"),
                         ("cs-co2", "product", "coproduct"),
                         ("cs-eth", "product", "coproduct")])])
    v4, v5 = _dual(graph, payload)
    assert v5["hit"] is True
    row = v5["block"]["events"][0]
    assert row["n_product_species_total"] == 4
    assert row["n_principal_species"] == 1
    assert row["n_coproduct_species"] == 3
    assert row["n_other_role_species"] == 0
    assert row["n_participant_entries"] == 4
    assert row["product_species_bucket"] == "3-4"
    # T4c-2:§5.2 升级为 C4*(合成夹具系数全 unknown ⇒ 无法算非氢预算)
    assert row["coproduct_traceability"] == "unknown"
    assert row["coproduct_traceability_reason"] == "unknown_coefficient"
    assert row["c4star_budget"]["rule_version"] == \
        "c4star-declared-non-hydrogen-budget-1"
    assert v5["block"]["max_product_species_any_qualifying_event"] >= 4


def test_v5_disclosure_without_coproduct_is_not_applicable() -> None:
    graph = _single_graph()
    payload = _payload(
        {"cs-sub": SUBSTRATE, "cs-p1": PRODUCT_A},
        [_event("ev-1", [("cs-sub", "reactant", "primary_substrate"),
                         ("cs-p1", "product", "principal_product")])])
    _, v5 = _dual(graph, payload)
    row = v5["block"]["events"][0]
    assert row["n_coproduct_species"] == 0
    assert row["coproduct_traceability"] == "not_applicable"
    assert row["coproduct_traceability_reason"] == \
        "no_coproduct_participant"


def test_v5_coproduct_traceability_uses_c4star_four_states() -> None:
    """T4c-2:§5.2 已升级为 C4*(按声明的非氢元素预算)四状态判定。

    规则权威 = Codex 代 mimo 评审第一节;本测试只核**枚举与规则身份**
    接线(细则见 tests/test_ppv1_c4star_disclosure.py)。
    """
    allowed = {"traceable", "untraceable", "unknown", "not_applicable"}
    graph = _single_graph()
    payload = _payload(
        {"cs-sub": SUBSTRATE, "cs-p1": PRODUCT_A, "cs-w": WATER},
        [_event("ev-1", [("cs-sub", "reactant", "primary_substrate"),
                         ("cs-p1", "product", "principal_product"),
                         ("cs-w", "product", "coproduct")])])
    _, v5 = _dual(graph, payload)
    assert v5["block"]["events"][0]["coproduct_traceability"] in allowed
    graphs = {graph["reference_graph_id"]: graph}
    output = evaluate_scientific(
        _evaluation_input(graph), reference_graphs=graphs,
        native_export_reader=_fake_reader(payload),
        criteria_version=PPV1_CRITERIA_V5)
    traceability = output["criteria_v5"]["coproduct_traceability"]
    assert traceability["status"] == "implemented_c4star"
    assert traceability["implemented_rules"] == [
        "c4star_declared_non_hydrogen_budget"]
    assert set(traceability["allowed_outputs"]) == allowed
    assert traceability["display_name"] == "按声明的非氢元素预算检查"


# ---------------------------------------------------------------- 分桶


def test_v5_partial_bucket_uses_literal_prereg_trigger() -> None:
    """多主产物题只命中部分主产物 ⇒ partial(不记命中)。"""
    graph = _graph(
        [_node("n-root", SUBSTRATE, "root"),
         _node("n-p1", PRODUCT_A, "principal_product"),
         _node("n-p2", PRODUCT_B, "principal_product")],
        [_edge("e-1", ["n-root"], ["n-p1", "n-p2"],
               ["substrate", "principal_product", "principal_product"])])
    payload = _payload(
        {"cs-sub": SUBSTRATE, "cs-p1": PRODUCT_A},
        [_event("ev-1", [("cs-sub", "reactant", "primary_substrate"),
                         ("cs-p1", "product", "principal_product")])])
    v4, v5 = _dual(graph, payload)
    assert v4["hit"] is False
    assert v5["hit"] is False
    assert v5["bucket"] == CRITERIA_V5_BUCKET_PARTIAL
    assert v5["block"]["product_hit_partial"] is True
    assert v5["block"]["partial_product_hit_events"] == ["ev-1"]


def test_v5_partial_bucket_legacy_axis_disclosed_separately() -> None:
    """v4 旧 coverage 轴归属与 §2.2 字面 trigger 并列披露。"""
    graph = _graph(
        [_node("n-root", SUBSTRATE, "root"),
         _node("n-p1", PRODUCT_A, "principal_product"),
         _node("n-p2", PRODUCT_B, "principal_product")],
        [_edge("e-1", ["n-root"], ["n-p1", "n-p2"],
               ["substrate", "principal_product", "principal_product"])])
    payload = _payload(
        {"cs-sub": SUBSTRATE, "cs-p1": PRODUCT_A},
        [_event("ev-1", [("cs-sub", "reactant", "primary_substrate"),
                         ("cs-p1", "product", "principal_product")])])
    node_matches = match_reference_nodes(
        graph, payload, criteria_version=PPV1_CRITERIA_V5)
    entry = match_reference_edges(
        graph, payload, node_matches, criteria_version=PPV1_CRITERIA_V5)[0]
    block = entry["criteria_v5"]
    assert block["bucket"] == CRITERIA_V5_BUCKET_PARTIAL
    # 旧 coverage 轴:该事件产物侧缺 n-p2 ⇒ 旧状态为覆盖不足(非 partial)
    assert entry["match_status"] == "unmatched_required_node_uncovered"
    assert block["product_hit_partial_legacy_coverage_axis"] is False


# ---------------------------------------------------------------- 单调性/隔离


def test_v5_never_hits_where_v4_misses_and_blocks_do_not_mix() -> None:
    """§1 单调性夹具级:所有夹具 v5 命中 ⇒ v4 命中;两版本块不混写。"""
    graph_multi = _graph(
        [_node("n-root", SUBSTRATE, "root"),
         _node("n-p1", PRODUCT_A, "principal_product"),
         _node("n-p2", PRODUCT_B, "principal_product")],
        [_edge("e-1", ["n-root"], ["n-p1", "n-p2"],
               ["substrate", "principal_product", "principal_product"])])
    fixtures = [
        (_single_graph(), _payload(
            {"cs-sub": SUBSTRATE, "cs-p1": PRODUCT_A},
            [_event("ev-1", [("cs-sub", "reactant", "primary_substrate"),
                             ("cs-p1", "product",
                              "principal_product")])])),
        (graph_multi, _payload(
            {"cs-sub": SUBSTRATE, "cs-p1": PRODUCT_A,
             "cs-p2": PRODUCT_B},
            [_event("ev-1", [("cs-sub", "reactant", "primary_substrate"),
                             ("cs-p1", "product", "principal_product"),
                             ("cs-p2", "product", "principal_product")])])),
        (_single_graph(), _payload({"cs-sub": SUBSTRATE}, [])),
    ]
    for graph, payload in fixtures:
        v4, v5 = _dual(graph, payload)
        assert int(v5["hit"]) <= int(v4["hit"])
        assert "criteria_v4" not in v5["entry"]
        assert "criteria_v5" not in v4["entry"]


def test_v1_v2_v3_v4_outputs_have_no_criteria_v5_key() -> None:
    graph = _single_graph()
    payload = _payload(
        {"cs-sub": SUBSTRATE, "cs-p1": PRODUCT_A},
        [_event("ev-1", [("cs-sub", "reactant", "primary_substrate"),
                         ("cs-p1", "product", "principal_product")])])
    graphs = {graph["reference_graph_id"]: graph}
    for version in (PPV1_CRITERIA_V1, PPV1_CRITERIA_V2, PPV1_CRITERIA_V3,
                    PPV1_CRITERIA_V4):
        output = evaluate_scientific(
            _evaluation_input(graph), reference_graphs=graphs,
            native_export_reader=_fake_reader(payload),
            criteria_version=version)
        assert "criteria_v5" not in output, version
        sample = output["sample_results"][0]
        assert "criteria_v5" not in sample, version
        assert "role_bound_product_hit" not in sample, version


def test_v5_run_emits_v5_blocks_only() -> None:
    graph = _single_graph()
    payload = _payload(
        {"cs-sub": SUBSTRATE, "cs-p1": PRODUCT_A},
        [_event("ev-1", [("cs-sub", "reactant", "primary_substrate"),
                         ("cs-p1", "product", "principal_product")])])
    graphs = {graph["reference_graph_id"]: graph}
    output = evaluate_scientific(
        _evaluation_input(graph), reference_graphs=graphs,
        native_export_reader=_fake_reader(payload),
        criteria_version=PPV1_CRITERIA_V5)
    assert "criteria_v5" in output
    assert "criteria_v4" not in output
    sample = output["sample_results"][0]
    assert sample["criteria_v5"]["bucket"] == \
        CRITERIA_V5_BUCKET_MATCHED
    assert sample.get("role_bound_product_hit") is True
    assert "criteria_v4" not in sample
    assert output["criteria_v5"]["buckets"][
        CRITERIA_V5_BUCKET_MATCHED] == 1
    # 端到端:判分层从**边块**取首命中事件披露(样本块只有聚合字段)
    row = _role_bound_hit_row(sample, payload, graph)
    assert row["role_bound_product_hit"] is True
    assert row["disclosure"] is not None
    assert row["disclosure"]["event_id"] == "ev-1"
    assert row["disclosure"]["product_species_bucket"] == "1"
    assert row["disclosure"]["coproduct_traceability"] == \
        "not_applicable"


# ---------------------------------------------------------------- 判分透传


def test_role_bound_hit_row_rank_uses_pre_fixed_candidate_order() -> None:
    graph = _single_graph()
    payload = _payload(
        {"cs-sub": SUBSTRATE, "cs-wrong": WRONG_PRODUCT,
         "cs-p1": PRODUCT_A},
        [_event("ev-1", [("cs-sub", "reactant", "primary_substrate"),
                         ("cs-wrong", "product", "principal_product")],
                created_at="2026-01-01T00:00:00Z"),
         _event("ev-2", [("cs-sub", "reactant", "primary_substrate"),
                         ("cs-p1", "product", "principal_product")],
                created_at="2026-01-01T00:00:01Z")])
    sample = {
        "scoring_status": "scored",
        "predicted_edge_matches": [{
            "match_status": "matched_participant_coverage_partial",
            "criteria_v5": {
                "bucket": CRITERIA_V5_BUCKET_MATCHED,
                "role_bound_hit_events": ["ev-2"],
                "max_product_species_any_qualifying_event": 1,
                "events": [
                    {"event_id": "ev-1", "eligible": True,
                     "n_product_species_total": 1,
                     "n_principal_species": 0, "n_coproduct_species": 0,
                     "n_other_role_species": 1, "n_multirole_species": 0,
                     "n_participant_entries": 1,
                     "n_role_missing_entries": 0,
                     "n_role_unknown_entries": 0,
                     "role_missing_or_unknown_present": False,
                     "product_species_bucket": "1",
                     "coproduct_traceability": "not_applicable",
                     "coproduct_traceability_reason":
                         "no_coproduct_participant"},
                    {"event_id": "ev-2", "eligible": True,
                     "n_product_species_total": 1,
                     "n_principal_species": 1, "n_coproduct_species": 0,
                     "n_other_role_species": 0, "n_multirole_species": 0,
                     "n_participant_entries": 1,
                     "n_role_missing_entries": 0,
                     "n_role_unknown_entries": 0,
                     "role_missing_or_unknown_present": False,
                     "product_species_bucket": "1",
                     "coproduct_traceability": "not_applicable",
                     "coproduct_traceability_reason":
                         "no_coproduct_participant"},
                ],
            },
        }],
        "predicted_node_matches": match_reference_nodes(
            graph, payload, criteria_version=PPV1_CRITERIA_V5),
        "criteria_v5": {
            "bucket": CRITERIA_V5_BUCKET_MATCHED,
            "role_bound_hit_events": ["ev-2"],
            "max_product_species_any_qualifying_event": 1,
        },
    }
    row = _role_bound_hit_row(sample, payload, graph)
    assert row["rank"] == 2
    assert row["bucket"] == CRITERIA_V5_BUCKET_MATCHED
    assert row["disclosure_event_id"] == "ev-2"
    assert row["disclosure"]["product_species_bucket"] == "1"
    assert row["disclosure"]["n_principal_species"] == 1
    assert row["matched_event_not_in_candidates"] is False


def test_role_bound_hit_row_without_hit_has_null_rank() -> None:
    graph = _single_graph()
    payload = _payload(
        {"cs-sub": SUBSTRATE, "cs-p1": PRODUCT_A},
        [_event("ev-1", [("cs-sub", "reactant", "primary_substrate"),
                         ("cs-p1", "product", "coproduct")])])
    sample = {
        "scoring_status": "scored",
        "predicted_edge_matches": [{"match_status": "unmatched"}],
        "predicted_node_matches": match_reference_nodes(
            graph, payload, criteria_version=PPV1_CRITERIA_V5),
        "criteria_v5": {
            "bucket": CRITERIA_V5_BUCKET_PRODUCT_MISMATCH,
            "role_bound_hit_events": [],
            "max_product_species_any_qualifying_event": 1,
            "events": [],
        },
    }
    row = _role_bound_hit_row(sample, payload, graph)
    assert row["rank"] is None
    assert row["role_bound_product_hit"] is False
    assert row["disclosure"] is None


def test_role_bound_hit_row_missing_sample_stays_in_denominator() -> None:
    graph = _single_graph()
    row = _role_bound_hit_row(None, {}, graph)
    assert row["rank"] is None
    assert row["bucket"] == CRITERIA_V5_BUCKET_NO_EVENT
    assert row["role_bound_product_hit"] is False


def _species_bucket_label(n: int) -> str:
    if n <= 0:
        return "0"
    if n == 1:
        return "1"
    if n == 2:
        return "2"
    if n <= 4:
        return "3-4"
    if n <= 8:
        return "5-8"
    return ">8"


def _disclosure_row(event_id: str, bucket: str, species: int,
                    trace: str) -> dict:
    return {
        "rank": 1 if bucket == CRITERIA_V5_BUCKET_MATCHED else None,
        "bucket": bucket,
        "disclosure": {
            "event_id": event_id,
            "n_product_species_total": species,
            "n_principal_species": 1,
            "n_coproduct_species": max(species - 1, 0),
            "n_other_role_species": 0,
            "n_multirole_species": 0,
            "n_participant_entries": species,
            "product_species_bucket": _species_bucket_label(species),
            "coproduct_traceability": trace,
            "coproduct_traceability_reason": "rule_pending_mimo",
        } if bucket == CRITERIA_V5_BUCKET_MATCHED else None,
        "max_product_species_any_qualifying_event": species,
        "matched_event_not_in_candidates": False,
    }


def test_role_bound_hit_caliber_block_closed_and_disclosed() -> None:
    rows = [
        _disclosure_row("ev-1", CRITERIA_V5_BUCKET_MATCHED, 1, "not_applicable"),
        _disclosure_row("ev-2", CRITERIA_V5_BUCKET_MATCHED, 5, "unknown"),
        _disclosure_row("ev-3", CRITERIA_V5_BUCKET_PARTIAL, 2, "unknown"),
        _disclosure_row("ev-4", CRITERIA_V5_BUCKET_NO_EVENT, 0, "unknown"),
        _disclosure_row("ev-5", CRITERIA_V5_BUCKET_REFERENCE_INVALID, 0,
                        "unknown"),
        _disclosure_row("ev-6", CRITERIA_V5_BUCKET_PRODUCT_MISMATCH, 3,
                        "unknown"),
    ]
    block = _role_bound_hit_caliber_block(rows, 6, domain_tag="298")
    assert block["role_bound_product_hit"] == 2
    assert block["product_hit_partial"] == 1
    assert block["hit@1"] == 2
    assert block["hit@3"] == 2
    assert block["hit@5"] == 2
    assert sum(block["buckets"].values()) == 6
    assert block["separate_from_strict"] is True
    assert block["separate_from_v4"] is True
    assert block["metric_name"] == "role_bound_product_hit"
    disclosure = block["disclosure_axis_5_1"]
    assert disclosure["n_hit_with_disclosure"] == 2
    assert disclosure["n_hit_without_disclosure"] == 0
    assert disclosure["product_species_bucket"] == {"1": 1, "5-8": 1}
    axis_5_2 = block["disclosure_axis_5_2"]
    assert axis_5_2["status"] == "implemented_c4star"
    assert axis_5_2["implemented_rules"] == [
        "c4star_declared_non_hydrogen_budget"]
    assert set(axis_5_2["counts"]) <= {
        "unknown", "not_applicable", "traceable", "untraceable"}
    qualification = block["domain_qualification"]
    assert qualification["main_caliber_eligible"] is False
    assert qualification["disclosure_only"] is False


def test_role_bound_hit_caliber_block_b121_is_disclosure_only() -> None:
    rows = [_disclosure_row("ev-1", CRITERIA_V5_BUCKET_MATCHED, 1,
                            "not_applicable")]
    block = _role_bound_hit_caliber_block(rows, 1,
                                          domain_tag="biosysmodb121")
    qualification = block["domain_qualification"]
    assert qualification["main_caliber_eligible"] is False
    assert qualification["disclosure_only"] is True
    assert qualification["disclosure_label"] == "[biosysmodb121·披露]"


def test_role_bound_hit_caliber_block_rejects_bucket_total_mismatch() -> None:
    from pathway_v43.pollutant.s5b_scoring import S5bScoringError
    rows = [_disclosure_row("ev-1", CRITERIA_V5_BUCKET_MATCHED, 1,
                            "not_applicable")]
    with pytest.raises(S5bScoringError) as excinfo:
        _role_bound_hit_caliber_block(rows, 2)
    assert excinfo.value.detail["kind"] == \
        "s5b_role_bound_product_hit_bucket_total_mismatch"


def test_role_bound_hit_caliber_block_rejects_hitk_monotonicity() -> None:
    """防御断言:非命中桶却带 rank(rank 归属错误)⇒ fail-closed。"""
    from pathway_v43.pollutant.s5b_scoring import S5bScoringError
    rows = [{"rank": 1, "bucket": CRITERIA_V5_BUCKET_NO_EVENT,
             "disclosure": None,
             "max_product_species_any_qualifying_event": 0,
             "matched_event_not_in_candidates": False}]
    with pytest.raises(S5bScoringError) as excinfo:
        _role_bound_hit_caliber_block(rows, 1)
    assert excinfo.value.detail["kind"] == \
        "s5b_role_bound_product_hit_monotonicity_violation"


# ---------------------------------------------------------------- 夹具辅助


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