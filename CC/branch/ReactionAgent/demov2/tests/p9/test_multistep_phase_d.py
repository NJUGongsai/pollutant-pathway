"""P9-T4 RED tests — Multi-step candidate graph (final_plan §12.4).

Phase D checklist:
- [ ] canonical molecule nodes + validated reaction edges
- [ ] per-edge evidence + dual-ledger + lane
- [ ] branch/beam + cycle detection + depth/cost/risk budgets
- [ ] path dedup + path uncertainty + stop rules
- [ ] external evidence consumption via IngestPipeline.ingest
"""
from __future__ import annotations

from reaction_agent.p9.external.schemas import (
    ExternalEvidenceRecord,
    EvidenceProvenance,
)
from reaction_agent.p9.external.ingest import IngestPipeline
from reaction_agent.p9.external.allowlist import SourceAllowlist
from reaction_agent.p9.external.cache import EvidenceCache
from reaction_agent.p9.external.schemas import ExternalEvidenceSource
from reaction_agent.p9.multistep.schemas import (
    MultiStepNode,
    MultiStepEdge,
    MultiStepPath,
    SearchConfig,
    Budget,
    StopRule,
)
from reaction_agent.p9.multistep.graph import MultiStepGraph
from reaction_agent.p9.multistep.search import (
    MultiStepSearch,
)
from reaction_agent.p9.multistep.validator import (
    EdgeValidationResult,
    MockEdgeValidator,
)
from reaction_agent.p9.multistep.path import (
    PathDedup,
    canonical_path_signature,
)

# ===========================================================================
# Fixtures
# ===========================================================================

MOL_A = "CCO"        # ethanol
MOL_B = "CC(=O)O"    # acetic acid
MOL_C = "COC(C)=O"   # methyl acetate (RDKit canonical)
MOL_D = "CCOC(C)=O"  # ethyl acetate (RDKit canonical)
MOL_E = "CCOC(C)=O"  # ethyl acetate (same as D — RDKit canonicalized)
MOL_F = "CCCOC(C)=O" # propyl acetate (RDKit canonical)


def make_node(canonical_smiles: str) -> MultiStepNode:
    return MultiStepNode(canonical_smiles=canonical_smiles)


def make_edge(
    from_smiles: str = MOL_A,
    to_smiles: str = MOL_B,
    edge_id: str = "edge-1",
    lane: str = "strict",
    evidence_id: str = "ev-1",
    ledger_id: str = "ledger-1",
) -> MultiStepEdge:
    return MultiStepEdge(
        edge_id=edge_id,
        from_node=from_smiles,
        to_node=to_smiles,
        lane=lane,
        evidence_ids=[evidence_id],
        ledger_ids=[ledger_id],
        one_step_contract_hash="abc123",
    )


# ===========================================================================
# 1. Canonical molecule nodes + validated reaction edges
# ===========================================================================


def test_multi_step_node_created() -> None:
    node = make_node(MOL_A)
    assert node.canonical_smiles == MOL_A
    assert node.node_id != ""


def test_multi_step_edge_created() -> None:
    edge = make_edge()
    assert edge.from_node == MOL_A
    assert edge.to_node == MOL_B
    assert edge.lane == "strict"


def test_graph_add_node() -> None:
    g = MultiStepGraph()
    n = g.add_node(MOL_A)
    assert n.canonical_smiles == MOL_A
    assert MOL_A in g


def test_graph_add_edge() -> None:
    g = MultiStepGraph()
    g.add_node(MOL_A)
    g.add_node(MOL_B)
    e = g.add_edge(make_edge())
    assert e.to_node == MOL_B


def test_same_canonical_smiles_same_node() -> None:
    g = MultiStepGraph()
    n1 = g.add_node(MOL_A)
    n2 = g.add_node(MOL_A)
    assert n1.node_id == n2.node_id


def test_edge_validation_contract() -> None:
    """Each edge must satisfy the one-step contract via validator."""
    edge = make_edge()
    assert edge.one_step_contract_hash != ""


# ===========================================================================
# 2. Per-edge evidence + dual-ledger + lane
# ===========================================================================


def test_edge_carries_evidence() -> None:
    edge = make_edge(evidence_id="ev-1")
    assert "ev-1" in edge.evidence_ids


def test_edge_carries_lane() -> None:
    edge = make_edge(lane="strict")
    assert edge.lane == "strict"


def test_edge_carries_ledger() -> None:
    edge = make_edge(ledger_id="ledger-1")
    assert "ledger-1" in edge.ledger_ids


def test_edge_lane_isolated() -> None:
    """Edges in different lanes can coexist in the same graph."""
    g = MultiStepGraph()
    g.add_node(MOL_A)
    g.add_node(MOL_B)
    strict_edge = make_edge(edge_id="e1", lane="strict")
    gen_edge = make_edge(edge_id="e2", lane="generalized", evidence_id="ev-2")
    g.add_edge(strict_edge)
    g.add_edge(gen_edge)
    assert len(g.edges) == 2


# ===========================================================================
# 3. Branch/beam + cycle detection + depth/cost/risk budgets
# ===========================================================================


def test_cycle_detection() -> None:
    """A→B→A is a cycle and should be detected."""
    g = MultiStepGraph()
    g.add_node(MOL_A)
    g.add_node(MOL_B)
    g.add_edge(make_edge(edge_id="e1", from_smiles=MOL_A, to_smiles=MOL_B))
    assert g.has_cycle([MOL_A, MOL_B, MOL_A]) is True


def test_no_cycle_for_linear_path() -> None:
    g = MultiStepGraph()
    g.add_node(MOL_A)
    g.add_node(MOL_B)
    g.add_node(MOL_C)
    assert g.has_cycle([MOL_A, MOL_B, MOL_C]) is False


def test_beam_search_basic() -> None:
    """Beam search finds paths from a start molecule."""
    g = MultiStepGraph()
    g.add_node(MOL_A)
    g.add_node(MOL_B)
    g.add_edge(make_edge())
    validator = MockEdgeValidator(valid_edges=[(MOL_A, MOL_B)])
    search = MultiStepSearch(graph=g, validator=validator)
    paths = search.search(start=MOL_A, config=SearchConfig(max_depth=2))
    assert len(paths) >= 1
    assert paths[0].nodes[0] == MOL_A
    assert paths[0].nodes[-1] == MOL_B


def test_beam_search_depth_limit() -> None:
    """Search should not exceed max_depth."""
    g = MultiStepGraph()
    for smi in [MOL_A, MOL_B, MOL_C, MOL_D]:
        g.add_node(smi)
    g.add_edge(make_edge(edge_id="e1", from_smiles=MOL_A, to_smiles=MOL_B))
    g.add_edge(make_edge(edge_id="e2", from_smiles=MOL_B, to_smiles=MOL_C, evidence_id="ev-2"))
    g.add_edge(make_edge(edge_id="e3", from_smiles=MOL_C, to_smiles=MOL_D, evidence_id="ev-3"))
    validator = MockEdgeTransformer(g)
    search = MultiStepSearch(graph=g, validator=validator)
    paths = search.search(start=MOL_A, config=SearchConfig(max_depth=2))
    for p in paths:
        assert len(p.nodes) <= 2 + 1  # depth 2 means 2 edge hops, so 3 nodes max


def test_beam_search_budget_respected() -> None:
    """Cost budget should stop search when exceeded."""
    g = MultiStepGraph()
    for smi in [MOL_A, MOL_B, MOL_C]:
        g.add_node(smi)
    g.add_edge(make_edge(edge_id="e1", from_smiles=MOL_A, to_smiles=MOL_B))
    g.add_edge(make_edge(edge_id="e2", from_smiles=MOL_B, to_smiles=MOL_C, evidence_id="ev-2"))
    validator = MockEdgeTransformer(g)
    search = MultiStepSearch(graph=g, validator=validator)
    paths = search.search(
        start=MOL_A,
        config=SearchConfig(max_depth=5, budget=Budget(max_cost=0.5)),
    )
    # With cost=1.0 per edge and max_cost=0.5, no paths should be found
    # (or only depth-0 paths)
    for p in paths:
        assert len(p.nodes) <= 1  # only the start node


# ===========================================================================
# 4. Path dedup + path uncertainty + stop rules
# ===========================================================================


def test_path_dedup_same_path() -> None:
    """Same canonical path signature should deduplicate."""
    p1 = MultiStepPath(
        nodes=[MOL_A, MOL_B],
        edge_ids=["edge-1"],
        total_cost=1.0,
        total_risk=0.0,
    )
    p2 = MultiStepPath(
        nodes=[MOL_A, MOL_B],
        edge_ids=["edge-1"],
        total_cost=1.0,
        total_risk=0.0,
    )
    sig1 = canonical_path_signature(p1)
    sig2 = canonical_path_signature(p2)
    assert sig1 == sig2


def test_path_dedup_different_paths() -> None:
    """Different path signatures should not deduplicate."""
    p1 = MultiStepPath(
        nodes=[MOL_A, MOL_B],
        edge_ids=["edge-1"],
        total_cost=1.0,
        total_risk=0.0,
    )
    p2 = MultiStepPath(
        nodes=[MOL_A, MOL_C],
        edge_ids=["edge-2"],
        total_cost=1.0,
        total_risk=0.0,
    )
    sig1 = canonical_path_signature(p1)
    sig2 = canonical_path_signature(p2)
    assert sig1 != sig2


def test_path_uncertainty() -> None:
    """Multiple paths to the same target increase uncertainty."""
    p1 = MultiStepPath(nodes=[MOL_A, MOL_B], edge_ids=["e1"], total_cost=1.0, total_risk=0.0)
    p2 = MultiStepPath(nodes=[MOL_A, MOL_C, MOL_B], edge_ids=["e2", "e3"], total_cost=2.0, total_risk=0.0)
    # Both paths end at MOL_B, so uncertainty for MOL_B = 2
    # MOL_C is an intermediate node, not a target — it shouldn't be counted
    dedup = PathDedup()
    dedup.add(p1)
    dedup.add(p2)
    assert dedup.alternative_paths(MOL_B) == 2
    # MOL_C is an intermediate, not a target
    assert dedup.alternative_paths(MOL_C) == 0


def test_stop_rule_max_paths() -> None:
    """Stop rule: max_paths limits search output."""
    g = MultiStepGraph()
    for smi in [MOL_A, MOL_B, MOL_C, MOL_D]:
        g.add_node(smi)
    g.add_edge(make_edge(edge_id="e1", from_smiles=MOL_A, to_smiles=MOL_B))
    g.add_edge(make_edge(edge_id="e2", from_smiles=MOL_A, to_smiles=MOL_C, evidence_id="ev-2"))
    g.add_edge(make_edge(edge_id="e3", from_smiles=MOL_A, to_smiles=MOL_D, evidence_id="ev-3"))
    validator = MockEdgeTransformer(g)
    search = MultiStepSearch(graph=g, validator=validator)
    paths = search.search(
        start=MOL_A,
        config=SearchConfig(max_depth=1, stop_rules=[StopRule(type="max_paths", value=2)]),
    )
    assert len(paths) <= 2


# ===========================================================================
# 5. External evidence consumption via IngestPipeline.ingest
# ===========================================================================


def test_external_evidence_consumes_via_ingest() -> None:
    """External evidence used in multi-step must go through IngestPipeline."""
    source = ExternalEvidenceSource(
        source_id="pubchem-2024",
        source_name="PubChem 2024",
        license="CC-BY-4.0",
        source_version="2024.1",
        homepage="https://pubchem.ncbi.nlm.nih.gov",
    )
    al = SourceAllowlist()
    al.register(source)
    rec = ExternalEvidenceRecord(
        evidence_id="ext-ms-1",
        source_id="pubchem-2024",
        license="CC-BY-4.0",
        provenance=EvidenceProvenance(
            source_version="2024.1",
            retrieval_date="2026-08-01",
            content_hash="ext-hash",
        ),
        content="A multi-step reaction pathway: A->B->C is known",
    )
    pipeline = IngestPipeline()
    result = pipeline.ingest(
        record=rec,
        allowlist=al,
        cache=EvidenceCache(),
    )
    assert result.resolution == "accepted"
    assert result.suppressed is False
    # The ingested evidence can then be used to inform multi-step edge creation
    edge = make_edge(evidence_id="ext-ms-1")
    assert "ext-ms-1" in edge.evidence_ids


# ===========================================================================
# Helper: MockEdgeTransformer transforms a graph into mock validator
# ===========================================================================


class MockEdgeTransformer:
    """A mock edge validator that uses graph edges for validation."""

    def __init__(self, graph: MultiStepGraph) -> None:
        self._graph = graph

    def validate(self, from_smiles: str, ctx: dict | None = None) -> list[EdgeValidationResult]:
        results: list[EdgeValidationResult] = []
        for edge in self._graph.edges:
            if edge.from_node == from_smiles:
                results.append(EdgeValidationResult(
                    to_node=edge.to_node,
                    edge_id=edge.edge_id,
                    lane=edge.lane,
                    evidence_ids=edge.evidence_ids,
                    ledger_ids=edge.ledger_ids,
                    cost=1.0,
                    risk=0.0,
                ))
        return results