"""P9-T4: Multi-step candidate graph (final_plan §12.4).

The graph is a directed graph where:
- nodes are canonical molecule SMILES (identity-based dedup)
- edges are validated one-step reaction edges

Supports:
- add_node: idempotent (same SMILES → same node)
- add_edge: adds a directed edge
- has_cycle: checks if a node sequence has a cycle
"""
from __future__ import annotations

from collections import defaultdict

from reaction_agent.hashing import stable_id
from reaction_agent.p9.multistep.schemas import (
    MultiStepNode,
    MultiStepEdge,
    MultiStepPath,
)


class MultiStepGraph:
    """A directed graph of canonical molecule nodes and validated reaction edges.

    Nodes are deduplicated by canonical SMILES. Edges are indexed by from_node
    for efficient traversal.
    """

    def __init__(self) -> None:
        self._nodes: dict[str, MultiStepNode] = {}  # canonical_smiles → node
        self._edges: list[MultiStepEdge] = []
        self._outgoing: dict[str, list[MultiStepEdge]] = defaultdict(list)

    def add_node(self, canonical_smiles: str) -> MultiStepNode:
        """Add a canonical molecule node (idempotent: same SMILES → same node)."""
        if canonical_smiles not in self._nodes:
            node_id = stable_id("msn", canonical_smiles)
            self._nodes[canonical_smiles] = MultiStepNode(
                node_id=node_id,
                canonical_smiles=canonical_smiles,
            )
        return self._nodes[canonical_smiles]

    def add_edge(self, edge: MultiStepEdge) -> MultiStepEdge:
        """Add a validated reaction edge. Nodes must already exist."""
        if edge.from_node not in self._nodes:
            raise ValueError(f"from_node {edge.from_node} not in graph")
        if edge.to_node not in self._nodes:
            raise ValueError(f"to_node {edge.to_node} not in graph")
        self._edges.append(edge)
        self._outgoing[edge.from_node].append(edge)
        return edge

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