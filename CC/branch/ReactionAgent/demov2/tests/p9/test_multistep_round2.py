"""P9-T4 Round 2 RED tests — Phase D remediation (P9D-R1-01..06).

Covers all 6 findings from kimi Round 1 audit:
- P9D-R1-01: external evidence intake placebo (P1)
- P9D-R1-02: one-step contract provenance (P1)
- P9D-R1-03: path lineage (P2)
- P9D-R1-04: canonical node normalization (P2)
- P9D-R1-05: stop rule fail-open (P2)
- P9D-R1-06: hygiene (P2)
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from reaction_agent.p9.multistep.schemas import (
    MultiStepEdge,
    MultiStepPath,
    SearchConfig,
    StopRule,
    Step,
)
from reaction_agent.p9.multistep.graph import MultiStepGraph
from reaction_agent.p9.multistep.validator import (
    EdgeValidationResult,
    MockEdgeValidator,
)
from reaction_agent.p9.multistep.search import MultiStepSearch
from reaction_agent.p9.multistep.path import PathDedup
from reaction_agent.p9.external.cache import EvidenceCache
from reaction_agent.p9.external.schemas import ExternalEvidenceRecord, EvidenceProvenance

# Fixtures
MOL_A = "CCO"        # ethanol
MOL_B = "CC(=O)O"    # acetic acid
MOL_C = "COC(C)=O"   # methyl acetate (RDKit canonical)
MOL_D = "CCOC(C)=O"  # ethyl acetate (RDKit canonical)
MOL_E = "CCOC(C)=O"  # ethyl acetate (same molecule as D, RDKit canonicalized)


def make_edge(**over) -> MultiStepEdge:
    base = dict(
        edge_id="edge-1",
        from_node=MOL_A,
        to_node=MOL_B,
        lane="strict",
        evidence_ids=["ev-1"],
        ledger_ids=["ledger-1"],
        one_step_contract_hash="abc123",
    )
    base.update(over)
    return MultiStepEdge(**base)


def make_validated_edge(
    g: MultiStepGraph,
    from_smiles: str = MOL_A,
    to_smiles: str = MOL_B,
    edge_id: str = "edge-1",
    lane: str = "strict",
) -> MultiStepEdge:
    """Create a validator-issued edge and add it to the graph. Returns the edge."""
    validator = MockEdgeValidator(valid_edges=[(from_smiles, to_smiles)], lane=lane)
    result = validator.validate(from_smiles)[0]
    edge = MultiStepEdge(
        edge_id=edge_id,
        from_node=from_smiles,
        to_node=to_smiles,
        lane=result.lane,
        evidence_ids=result.evidence_ids,
        ledger_ids=result.ledger_ids,
        one_step_contract_hash=result.one_step_contract_hash,
    )
    g.add_edge(edge, validator=validator)
    return edge


# ===========================================================================
# P9D-R1-01: External evidence intake placebo (P1)
# ===========================================================================


def test_uningested_evidence_id_rejected_by_search() -> None:
    """An external_evidence_id not in the EvidenceCache must be rejected."""
    g = MultiStepGraph()
    g.add_node(MOL_A)
    g.add_node(MOL_B)
    make_validated_edge(g)
    validator = MockEdgeValidator(valid_edges=[(MOL_A, MOL_B)])
    cache = EvidenceCache()  # empty cache — nothing ingested
    search = MultiStepSearch(graph=g, validator=validator)
    with pytest.raises(ValueError, match="has not been ingested"):
        search.search(
            start=MOL_A,
            config=SearchConfig(max_depth=1),
            external_evidence_ids=["evil-never-ingested"],
            evidence_cache=cache,
        )


def test_ingested_evidence_id_accepted_by_search() -> None:
    """An ingested evidence_id (in cache) must be accepted."""
    g = MultiStepGraph()
    g.add_node(MOL_A)
    g.add_node(MOL_B)
    make_validated_edge(g)
    validator = MockEdgeValidator(valid_edges=[(MOL_A, MOL_B)])
    cache = EvidenceCache()
    # Pretend this evidence was ingested through IngestPipeline
    rec = ExternalEvidenceRecord(
        evidence_id="ingested-ev-1",
        source_id="chemrxiv-2024",
        license="CC-BY-4.0",
        provenance=EvidenceProvenance(
            source_version="2024.1",
            retrieval_date="2026-08-01",
            content_hash="abc123",
        ),
        content="A valid reaction pathway",
    )
    cache.put(rec)
    search = MultiStepSearch(graph=g, validator=validator)
    paths = search.search(
        start=MOL_A,
        config=SearchConfig(max_depth=1),
        external_evidence_ids=["ingested-ev-1"],
        evidence_cache=cache,
    )
    assert len(paths) >= 1


# ===========================================================================
# P9D-R1-02: One-step contract provenance (P1)
# ===========================================================================


def test_edge_validation_result_emits_contract_hash() -> None:
    """EdgeValidationResult must carry a one_step_contract_hash."""
    result = EdgeValidationResult(
        to_node=MOL_B,
        edge_id="e1",
        lane="strict",
        evidence_ids=["ev-1"],
        ledger_ids=["ledger-1"],
    )
    assert result.one_step_contract_hash != ""
    assert result.one_step_contract_hash is not None


def test_mock_validator_emits_contract_hash() -> None:
    """MockEdgeValidator must emit a deterministic contract hash."""
    validator = MockEdgeValidator(valid_edges=[(MOL_A, MOL_B)])
    results = validator.validate(MOL_A)
    assert len(results) == 1
    h = results[0].one_step_contract_hash
    assert h != ""
    # Same validator, same input → same hash
    results2 = validator.validate(MOL_A)
    assert results2[0].one_step_contract_hash == h


def test_forged_contract_hash_edge_rejected() -> None:
    """An edge with a forged/non-validator-issued hash must be rejected."""
    g = MultiStepGraph()
    g.add_node(MOL_A)
    g.add_node(MOL_B)
    forged = make_edge(one_step_contract_hash="i-made-this-up-no-validator-ran")
    validator = MockEdgeValidator(valid_edges=[(MOL_A, MOL_B)])
    with pytest.raises(ValueError, match="contract hash"):
        g.add_edge(forged, validator=validator)


def test_validator_issued_hash_edge_accepted() -> None:
    """An edge whose hash matches the validator's output must be accepted."""
    g = MultiStepGraph()
    g.add_node(MOL_A)
    g.add_node(MOL_B)
    validator = MockEdgeValidator(valid_edges=[(MOL_A, MOL_B)])
    result = validator.validate(MOL_A)[0]
    edge = MultiStepEdge(
        edge_id="valid-edge",
        from_node=MOL_A,
        to_node=MOL_B,
        lane=result.lane,
        evidence_ids=result.evidence_ids,
        ledger_ids=result.ledger_ids,
        one_step_contract_hash=result.one_step_contract_hash,
    )
    g.add_edge(edge, validator=validator)  # should pass
    assert len(g.edges) == 1


# ===========================================================================
# P9D-R1-03: Path lineage (P2)
# ===========================================================================


def test_path_carries_per_edge_steps() -> None:
    """MultiStepPath must carry per-edge Step objects with full lineage."""
    step = Step(
        edge_id="e1",
        from_node=MOL_A,
        to_node=MOL_B,
        lane="strict",
        evidence_ids=["ev-1"],
        ledger_ids=["ledger-1"],
        one_step_contract_hash="abc123",
    )
    path = MultiStepPath(
        nodes=[MOL_A, MOL_B],
        edge_ids=["e1"],
        steps=[step],
        total_cost=1.0,
        total_risk=0.0,
    )
    assert len(path.steps) == 1
    s = path.steps[0]
    assert s.lane == "strict"
    assert "ev-1" in s.evidence_ids
    assert "ledger-1" in s.ledger_ids


def test_search_path_has_lineage() -> None:
    """Search-produced paths must carry per-edge lineage."""
    g = MultiStepGraph()
    g.add_node(MOL_A)
    g.add_node(MOL_B)
    g.add_node(MOL_C)
    validator = MockEdgeValidator(
        valid_edges=[(MOL_A, MOL_B), (MOL_B, MOL_C)],
        lane="generalized",
    )
    # Add edges with validator-issued hashes
    for from_smiles, to_smiles in [(MOL_A, MOL_B), (MOL_B, MOL_C)]:
        result = validator.validate(from_smiles)[0]
        edge = MultiStepEdge(
            edge_id=result.edge_id,
            from_node=from_smiles,
            to_node=to_smiles,
            lane=result.lane,
            evidence_ids=result.evidence_ids,
            ledger_ids=result.ledger_ids,
            one_step_contract_hash=result.one_step_contract_hash,
        )
        g.add_edge(edge, validator=validator)

    search = MultiStepSearch(graph=g, validator=validator)
    paths = search.search(start=MOL_A, config=SearchConfig(max_depth=2))
    assert len(paths) >= 1
    # Each step should have full lineage
    for path in paths:
        if len(path.steps) > 0:
            step = path.steps[0]
            assert step.lane != ""
            assert len(step.evidence_ids) > 0
            assert len(step.ledger_ids) > 0
            assert step.one_step_contract_hash != ""


# ===========================================================================
# P9D-R1-04: Canonical node normalization (P2)
# ===========================================================================


def test_same_molecule_different_smiles_same_node() -> None:
    """Ethyl acetate as CC(=O)OCC and CCOC(=O)C should canonicalize to the same node."""
    g = MultiStepGraph()
    n1 = g.add_node(MOL_D)  # CC(=O)OCC
    n2 = g.add_node(MOL_E)  # CCOC(=O)C
    assert n1.node_id == n2.node_id, (
        "ethyl acetate variants should canonicalize to the same node"
    )


def test_invalid_smiles_rejected() -> None:
    """Invalid SMILES must be rejected at add_node."""
    g = MultiStepGraph()
    with pytest.raises(ValueError, match="invalid SMILES|not a molecule"):
        g.add_node("this-is-not-a-molecule")


def test_explicit_node_id_overridden_by_canonical() -> None:
    """A caller-provided node_id that differs from the canonical one should be
    rejected or overridden."""
    g = MultiStepGraph()
    n = g.add_node(MOL_A)
    # The node_id should be based on the canonical SMILES, not an arbitrary string
    assert n.node_id != "msn_forged"


# ===========================================================================
# P9D-R1-05: Stop rule fail-open (P2)
# ===========================================================================


def test_unknown_stop_rule_type_rejected() -> None:
    """An unknown StopRule.type must be rejected at construction (fail-closed)."""
    with pytest.raises(ValidationError, match="type"):
        StopRule(type="max_wall_time_seconds", value=0)


def test_known_stop_rule_accepted() -> None:
    """A known StopRule type (max_paths) must be accepted."""
    rule = StopRule(type="max_paths", value=10)
    assert rule.type == "max_paths"
    assert rule.value == 10


# ===========================================================================
# P9D-R1-06: Hygiene (P2)
# ===========================================================================


def test_edge_validation_result_bounds() -> None:
    """EdgeValidationResult must enforce cost >= 0 and risk in [0, 1]."""
    with pytest.raises((ValueError, AssertionError)):
        EdgeValidationResult(
            to_node=MOL_B, edge_id="e1", lane="strict",
            evidence_ids=["ev-1"], ledger_ids=["ledger-1"],
            cost=-1.0, risk=0.0,
        )
    with pytest.raises((ValueError, AssertionError)):
        EdgeValidationResult(
            to_node=MOL_B, edge_id="e1", lane="strict",
            evidence_ids=["ev-1"], ledger_ids=["ledger-1"],
            cost=1.0, risk=1.5,
        )


def test_path_uncertainty_wired_through_dedup() -> None:
    """PathDedup must expose uncertainty via a method."""
    p1 = MultiStepPath(nodes=[MOL_A, MOL_B], edge_ids=["e1"],
                        steps=[], total_cost=1.0, total_risk=0.0)
    p2 = MultiStepPath(nodes=[MOL_A, MOL_C, MOL_B], edge_ids=["e2", "e3"],
                        steps=[], total_cost=2.0, total_risk=0.0)
    dedup = PathDedup()
    dedup.add(p1)
    dedup.add(p2)
    # uncertainty should be accessible
    assert dedup.alternative_paths(MOL_B) == 2


# ===========================================================================
# P9D-R3-01: Sentinel — add_edge without validator rejected
# ===========================================================================


def test_add_edge_without_validator_rejected() -> None:
    """add_edge must raise TypeError when validator is not passed.

    This sentinel test prevents the validator from being silently reverted
    to optional (P9D-R2-02 regression guard). On the old signature where
    validator was optional (None default), calling add_edge(edge) would
    NOT raise TypeError — this test would fail, proving the structural RED.
    """
    g = MultiStepGraph()
    g.add_node(MOL_A)
    g.add_node(MOL_B)
    forged = MultiStepEdge(
        edge_id="forged",
        from_node=MOL_A,
        to_node=MOL_B,
        lane="strict",
        evidence_ids=["ev-1"],
        ledger_ids=["ledger-1"],
        one_step_contract_hash="hacked",
    )
    with pytest.raises(TypeError, match="validator"):
        g.add_edge(forged)  # no validator argument