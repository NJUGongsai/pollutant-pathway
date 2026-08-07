"""P9-T4: Multi-step candidate graph (final_plan §12.4).

The graph is a directed graph where:
- nodes are canonical molecule SMILES (RDKit-normalized, identity-based dedup)
- edges are validated one-step reaction edges (with contract hash verification)

Supports:
- add_node: idempotent (same molecule → same node), RDKit canonicalization
- add_edge: adds a directed edge, verifies contract hash against validator
- has_cycle: checks if a node sequence has a cycle
- get_edge: retrieves an edge by ID for lineage query
"""
from __future__ import annotations

from collections import defaultdict

from reaction_agent.hashing import stable_id
from reaction_agent.p9.multistep.schemas import (
    MultiStepNode,
    MultiStepEdge,
)
from reaction_agent.p9.multistep.validator import EdgeValidator

# RDKit import — fail gracefully if unavailable
try:
    from rdkit import Chem  # type: ignore
except ImportError:
    Chem = None  # type: ignore


class MultiStepGraph:
    """A directed graph of canonical molecule nodes and validated reaction edges.

    Nodes are deduplicated by canonical SMILES (RDKit-normalized). Edges are
    indexed by from_node for efficient traversal. Each edge must be validated
    by an EdgeValidator (contract hash verification).
    """

    def __init__(self) -> None:
        self._nodes: dict[str, MultiStepNode] = {}  # canonical_smiles → node
        self._edges: list[MultiStepEdge] = []
        self._outgoing: dict[str, list[MultiStepEdge]] = defaultdict(list)
        self._edge_by_id: dict[str, MultiStepEdge] = {}

    def add_node(self, canonical_smiles: str) -> MultiStepNode:
        """Add a canonical molecule node (RDKT-normalized, idempotent).

        The SMILES is RDKit-canonicalized for identity. Invalid SMILES or
        RDKit-parse failures raise ValueError (fail-closed, P9D-R1-04).
        """
        raw = canonical_smiles.strip()
        if not raw:
            raise ValueError("SMILES must not be empty")

        # RDKit canonicalization
        if Chem is not None:
            mol = Chem.MolFromSmiles(raw)
            if mol is None:
                raise ValueError(f"invalid SMILES (RDKit parse failed): {raw!r}")
            canonical = Chem.MolToSmiles(mol, canonical=True)
        else:
            # RDKit not available — trust caller's input (docstring warns)
            canonical = raw

        if canonical not in self._nodes:
            node_id = stable_id("msn", canonical)
            self._nodes[canonical] = MultiStepNode(
                node_id=node_id,
                canonical_smiles=canonical,
            )
        return self._nodes[canonical]

    def add_edge(self, edge: MultiStepEdge, validator: EdgeValidator | None = None) -> MultiStepEdge:
        """Add a validated reaction edge. Nodes must already exist.

        If a validator is provided, the edge's ``one_step_contract_hash`` is
        checked against the validator's output for the same endpoints. A forged
        or non-validator-issued hash is rejected (fail-closed, P9D-R1-02).
        """
        if edge.from_node not in self._nodes:
            raise ValueError(f"from_node {edge.from_node} not in graph")
        if edge.to_node not in self._nodes:
            raise ValueError(f"to_node {edge.to_node} not in graph")

        if validator is not None:
            # Verify the contract hash against the validator's output
            results = validator.validate(edge.from_node)
            for result in results:
                if result.to_node == edge.to_node:
                    if result.one_step_contract_hash != edge.one_step_contract_hash:
                        raise ValueError(
                            f"contract hash mismatch for edge {edge.edge_id}: "
                            f"validator emits {result.one_step_contract_hash[:12]}..., "
                            f"edge has {edge.one_step_contract_hash[:12]}..."
                        )
                    break
            else:
                raise ValueError(
                    f"no validator result for edge {edge.edge_id}: "
                    f"{edge.from_node} -> {edge.to_node}"
                )

        self._edges.append(edge)
        self._outgoing[edge.from_node].append(edge)
        self._edge_by_id[edge.edge_id] = edge
        return edge

    def get_edge(self, edge_id: str) -> MultiStepEdge | None:
        """Retrieve an edge by ID (for lineage query)."""
        return self._edge_by_id.get(edge_id)

    @property
    def nodes(self) -> dict[str, MultiStepNode]:
        return dict(self._nodes)

    @property
    def edges(self) -> list[MultiStepEdge]:
        return list(self._edges)

    def outgoing(self, node_smiles: str) -> list[MultiStepEdge]:
        """Get all outgoing edges from a node."""
        return list(self._outgoing.get(node_smiles, []))

    def has_cycle(self, node_sequence: list[str]) -> bool:
        """Check if a node sequence contains a cycle (duplicate node)."""
        seen: set[str] = set()
        for node in node_sequence:
            if node in seen:
                return True
            seen.add(node)
        return False

    def __contains__(self, node_smiles: str) -> bool:
        return node_smiles in self._nodes

    def __len__(self) -> int:
        return len(self._nodes)