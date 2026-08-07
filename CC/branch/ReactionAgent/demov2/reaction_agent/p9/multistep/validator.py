"""P9-T4: Edge validator — one-step contract interface (final_plan §12.4).

Each edge in the multi-step graph must satisfy the one-step contract. In
production, this would consume the P3 kernel (StrictCandidate) or P8 lane
(GeneralizedHypothesis) as the validator. For testing, we use a mock validator.

The ``EdgeValidator`` protocol defines the interface for validating a one-step
reaction from a molecule to its possible products. A ``MockEdgeValidator``
accepts a predefined set of valid edges.
"""
from __future__ import annotations

from dataclasses import dataclass, field as dc_field

from reaction_agent.hashing import canonical_hash


@dataclass(frozen=True)
class EdgeValidationResult:
    """Result of validating a one-step reaction from a molecule.

    ``to_node`` is the canonical SMILES of the product molecule.
    ``edge_id`` is a unique identifier for this edge.
    ``lane`` indicates which lane (strict/generalized/agent_proposed) validated this edge.
    ``evidence_ids`` / ``ledger_ids`` carry the evidence and ledger context.
    ``cost`` and ``risk`` are the cost/risk of this edge.
    """

    to_node: str
    edge_id: str
    lane: str
    evidence_ids: list[str]
    ledger_ids: list[str]
    cost: float = 1.0
    risk: float = 0.0


class MockEdgeValidator:
    """A mock edge validator that accepts a predefined set of valid edges.

    Usage::

        validator = MockEdgeValidator(valid_edges=[(MOL_A, MOL_B)])
        results = validator.validate(MOL_A)
        assert results[0].to_node == MOL_B
    """

    def __init__(self, valid_edges: list[tuple[str, str]] | None = None) -> None:
        self._valid_edges: dict[str, list[EdgeValidationResult]] = {}
        if valid_edges:
            for i, (from_smiles, to_smiles) in enumerate(valid_edges):
                self._add(from_smiles, to_smiles, f"mock-edge-{i}")

    def _add(self, from_smiles: str, to_smiles: str, edge_id: str) -> None:
        if from_smiles not in self._valid_edges:
            self._valid_edges[from_smiles] = []
        self._valid_edges[from_smiles].append(
            EdgeValidationResult(
                to_node=to_smiles,
                edge_id=edge_id,
                lane="strict",
                evidence_ids=[f"ev-{edge_id}"],
                ledger_ids=[f"ledger-{edge_id}"],
                cost=1.0,
                risk=0.0,
            )
        )

    def validate(self, from_smiles: str, ctx: dict | None = None) -> list[EdgeValidationResult]:
        """Return all valid edges from ``from_smiles``."""
        return list(self._valid_edges.get(from_smiles, []))