"""P9-T4: Multi-step search — beam search with budgets and stop rules.

The search explores the multi-step graph starting from a molecule, using an
edge validator to find valid one-step reactions. Beam search limits branching,
and budgets constrain cost/risk. Stop rules define additional termination
conditions.

The external evidence consumption constraint: the search accepts only
previously-ingested evidence IDs (via ``EvidenceCache``). Un-ingested IDs are
rejected fail-closed (P9D-R1-01).
"""
from __future__ import annotations

from dataclasses import dataclass

from reaction_agent.p9.external.cache import EvidenceCache
from reaction_agent.p9.multistep.schemas import (
    MultiStepPath,
    SearchConfig,
    Step,
    StopRule,
)
from reaction_agent.p9.multistep.graph import MultiStepGraph
from reaction_agent.p9.multistep.validator import (
    EdgeValidator,
)


@dataclass(frozen=True)
class _SearchState:
    """Internal search state during beam search."""

    current_node: str
    nodes: tuple[str, ...]
    edge_ids: tuple[str, ...]
    steps: tuple[Step, ...]
    total_cost: float
    total_risk: float


class MultiStepSearch:
    """Beam search over a multi-step graph using an edge validator.

    Args:
        graph: the multi-step graph (nodes + edges, pre-populated).
        validator: the edge validator (implements ``EdgeValidator`` protocol).
    """

    def __init__(self, graph: MultiStepGraph, validator: EdgeValidator) -> None:
        self._graph = graph
        self._validator = validator

    def search(
        self,
        start: str,
        config: SearchConfig | None = None,
        external_evidence_ids: list[str] | None = None,
        evidence_cache: EvidenceCache | None = None,
    ) -> list[MultiStepPath]:
        """Run beam search from ``start`` molecule.

        Args:
            start: canonical SMILES of the starting molecule.
            config: search configuration (beam width, max depth, budget, stop rules).
            external_evidence_ids: ingested external evidence IDs (MUST have
                passed through ``IngestPipeline.ingest`` and exist in
                ``evidence_cache``). Un-ingested IDs are rejected (P9D-R1-01).
            evidence_cache: the EvidenceCache containing ingested external
                evidence records. Required when ``external_evidence_ids`` is
                provided.

        Returns:
            List of found paths, sorted by total_cost ascending.
        """
        cfg = config or SearchConfig()

        # Validate external evidence ids against the cache (P9D-R1-01)
        if external_evidence_ids:
            if evidence_cache is None:
                raise ValueError(
                    "evidence_cache is required when external_evidence_ids is provided"
                )
            for eid in external_evidence_ids:
                if not eid.strip():
                    raise ValueError("external_evidence_ids must be non-empty strings")
                if not evidence_cache.has_evidence_id(eid):
                    raise ValueError(
                        f"external_evidence_id {eid!r} has not been ingested "
                        "(must pass through IngestPipeline.ingest first)"
                    )

        # Initialize beam with the start node
        beam: list[_SearchState] = [
            _SearchState(
                current_node=start,
                nodes=(start,),
                edge_ids=(),
                steps=(),
                total_cost=0.0,
                total_risk=0.0,
            )
        ]

        paths: list[MultiStepPath] = []

        for depth in range(cfg.max_depth):
            if not beam:
                break

            candidates: list[_SearchState] = []

            for state in beam:
                # Get valid edges from the current node
                results = self._validator.validate(state.current_node)

                for result in results:
                    # Check cycle: don't revisit a molecule already in the path
                    if self._graph.has_cycle(list(state.nodes) + [result.to_node]):
                        continue

                    # Check budget: cost
                    new_cost = state.total_cost + result.cost
                    if new_cost > cfg.budget.max_cost:
                        continue

                    # Check risk budget
                    new_risk = state.total_risk + result.risk
                    if new_risk > cfg.budget.max_risk:
                        continue

                    # Build Step with full lineage (P9D-R1-03)
                    step = Step(
                        edge_id=result.edge_id,
                        from_node=state.current_node,
                        to_node=result.to_node,
                        lane=result.lane,
                        evidence_ids=result.evidence_ids,
                        ledger_ids=result.ledger_ids,
                        one_step_contract_hash=result.one_step_contract_hash,
                    )

                    # Build new state
                    new_state = _SearchState(
                        current_node=result.to_node,
                        nodes=state.nodes + (result.to_node,),
                        edge_ids=state.edge_ids + (result.edge_id,),
                        steps=state.steps + (step,),
                        total_cost=new_cost,
                        total_risk=new_risk,
                    )
                    candidates.append(new_state)

            # Sort by total_cost (ascending) and keep top beam_width
            candidates.sort(key=lambda s: s.total_cost)
            beam = candidates[: cfg.beam_width]

            # Convert to paths
            for state in beam:
                path = MultiStepPath(
                    nodes=list(state.nodes),
                    edge_ids=list(state.edge_ids),
                    steps=list(state.steps),
                    total_cost=state.total_cost,
                    total_risk=state.total_risk,
                )
                paths.append(path)

            # Check stop rules
            for rule in cfg.stop_rules:
                if rule.type == "max_paths" and len(paths) >= int(rule.value):
                    return _apply_stop(paths, rule)

        # Sort paths by total_cost (ascending) and return
        paths.sort(key=lambda p: p.total_cost)
        return paths


def _apply_stop(paths: list[MultiStepPath], rule: StopRule) -> list[MultiStepPath]:
    """Apply a stop rule to a list of paths."""
    if rule.type == "max_paths":
        return paths[: int(rule.value)]
    return paths