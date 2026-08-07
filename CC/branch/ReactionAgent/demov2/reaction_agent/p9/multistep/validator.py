"""P9-T4: Edge validator — one-step contract interface (final_plan §12.4).

Each edge in the multi-step graph must satisfy the one-step contract. In
production, this would consume the P3 kernel (StrictCandidate) or P8 lane
(GeneralizedHypothesis) as the validator. For testing, we use a mock validator.

The ``EdgeValidator`` protocol defines the interface for validating a one-step
reaction from a molecule to its possible products. A ``MockEdgeValidator``
accepts a predefined set of valid edges.

The validator EMITS ``one_step_contract_hash`` — a deterministic fingerprint
of the contract version + endpoints. This hash is embedded in edges and paths
for provenance tracking (P9D-R1-02).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from reaction_agent.hashing import canonical_hash


@runtime_checkable
class EdgeValidator(Protocol):
    """Protocol for one-step reaction edge validation.

    A validator takes a molecule SMILES and returns zero or more
    ``EdgeValidationResult`` objects, each representing a valid one-step
    reaction from that molecule.
    """

    def validate(self, from_smiles: str, ctx: dict | None = None) -> list["EdgeValidationResult"]:
        ...


# Default contract version for deterministic hash computation.
_CONTRACT_VERSION = "p9-multistep-1"


@dataclass(frozen=True)
class EdgeValidationResult:
    """Result of validating a one-step reaction from a molecule.

    ``to_node`` is the canonical SMILES of the product molecule.
    ``edge_id`` is a unique identifier for this edge.
    ``lane`` indicates which lane (strict/generalized/agent_proposed) validated this edge.
    ``evidence_ids`` / ``ledger_ids`` carry the evidence and ledger context.
    ``one_step_contract_hash`` is the deterministic fingerprint of the contract
    version + endpoints, emitted by the validator (P9D-R1-02).
    ``cost`` and ``risk`` are the cost/risk of this edge (cost >= 0, risk in [0, 1]).
    """

    to_node: str
    edge_id: str
    lane: str
    evidence_ids: list[str]
    ledger_ids: list[str]
    one_step_contract_hash: str = ""
    cost: float = 1.0
    risk: float = 0.0

    def __post_init__(self) -> None:
        """Validate bounds and compute default contract hash."""
        if self.cost < 0:
            raise ValueError(f"cost must be >= 0, got {self.cost}")
        if not 0.0 <= self.risk <= 1.0:
            raise ValueError(f"risk must be in [0, 1], got {self.risk}")
        # Compute deterministic hash if not explicitly provided
        object.__setattr__(self, "one_step_contract_hash",
                           self.one_step_contract_hash or self._compute_hash())

    def _compute_hash(self) -> str:
        """Deterministic hash of contract version + endpoints."""
        return canonical_hash({
            "contract_version": _CONTRACT_VERSION,
            "edge_id": self.edge_id,
            "from_node": "",  # filled in by validate
            "to_node": self.to_node,
            "lane": self.lane,
            "evidence_ids": sorted(self.evidence_ids),
            "ledger_ids": sorted(self.ledger_ids),
        })


class MockEdgeValidator:
    """A mock edge validator that accepts a predefined set of valid edges.

    Usage::

        validator = MockEdgeValidator(valid_edges=[(MOL_A, MOL_B)])
        results = validator.validate(MOL_A)
        assert results[0].to_node == MOL_B
    """

    def __init__(
        self,
        valid_edges: list[tuple[str, str]] | None = None,
        lane: str = "strict",
    ) -> None:
        self._valid_edges: dict[str, list[EdgeValidationResult]] = {}
        self._lane = lane
        if valid_edges:
            for i, (from_smiles, to_smiles) in enumerate(valid_edges):
                self._add(from_smiles, to_smiles, f"mock-edge-{i}")

    def _add(self, from_smiles: str, to_smiles: str, edge_id: str) -> None:
        if from_smiles not in self._valid_edges:
            self._valid_edges[from_smiles] = []
        # Compute deterministic contract hash from the result
        result = EdgeValidationResult(
            to_node=to_smiles,
            edge_id=edge_id,
            lane=self._lane,
            evidence_ids=[f"ev-{edge_id}"],
            ledger_ids=[f"ledger-{edge_id}"],
            cost=1.0,
            risk=0.0,
        )
        self._valid_edges[from_smiles].append(result)

    def validate(self, from_smiles: str, ctx: dict | None = None) -> list[EdgeValidationResult]:
        """Return all valid edges from ``from_smiles``."""
        return list(self._valid_edges.get(from_smiles, []))

    def supports(self, from_smiles: str, to_smiles: str) -> bool:
        """Check if a specific edge is valid (convenience for tests)."""
        for result in self.validate(from_smiles):
            if result.to_node == to_smiles:
                return True
        return False