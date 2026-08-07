"""P9-T4: Multi-step candidate graph schemas (final_plan §12.4).

Data model for the multi-step candidate graph:
- MultiStepNode: a canonical molecule node (SMILES identity, RDKit-normalized)
- MultiStepEdge: a validated one-step reaction edge (from → to, with evidence/lane/ledger)
- Step: per-edge lineage in a path (edge_id + lane + evidence/ledger + contract hash)
- MultiStepPath: a path through the graph (sequence of nodes + steps)
- SearchConfig, Budget, StopRule: search configuration
- PathUncertainty: uncertainty tracking per target molecule

Each edge satisfies the one-step contract (P3 kernel or P8 lane as validator).
"""
from __future__ import annotations

from typing import Literal

from pydantic import Field, field_validator, model_validator

from reaction_agent.hashing import stable_id
from reaction_agent.schemas.common import StrictModel, NonEmptyStr


class MultiStepNode(StrictModel):
    """A canonical molecule node in the multi-step graph.

    ``node_id`` is content-addressed from the canonical SMILES, so the same
    molecule always maps to the same node. If not provided explicitly, it is
    computed from ``canonical_smiles``.
    """

    node_id: NonEmptyStr = ""
    canonical_smiles: NonEmptyStr

    @model_validator(mode="before")
    @classmethod
    def _compute_default_id(cls, values: dict) -> dict:
        if isinstance(values, dict):
            node_id = values.get("node_id", "")
            smiles = values.get("canonical_smiles", "")
            if not node_id and smiles:
                values["node_id"] = stable_id("msn", smiles)
        return values

    @field_validator("node_id")
    @classmethod
    def _node_id_non_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("node_id must not be empty")
        return v


class Step(StrictModel):
    """Per-edge lineage in a multi-step path.

    Carries the full evidence, lane, dual-ledger, and contract provenance
    for a single edge traversal, enabling auditability of each step.
    """

    edge_id: NonEmptyStr
    from_node: NonEmptyStr
    to_node: NonEmptyStr
    lane: NonEmptyStr
    evidence_ids: list[NonEmptyStr]
    ledger_ids: list[NonEmptyStr]
    one_step_contract_hash: NonEmptyStr


class MultiStepEdge(StrictModel):
    """A validated one-step reaction edge in the multi-step graph.

    ``edge_id`` is unique. ``from_node`` and ``to_node`` are canonical SMILES
    strings (referencing ``MultiStepNode.canonical_smiles``). Each edge carries
    evidence, lane, dual-ledger info, and the one-step contract hash that
    validates it.
    """

    edge_id: NonEmptyStr
    from_node: NonEmptyStr
    to_node: NonEmptyStr
    lane: NonEmptyStr
    evidence_ids: list[NonEmptyStr]
    ledger_ids: list[NonEmptyStr]
    one_step_contract_hash: NonEmptyStr
    cost: float = Field(default=1.0, ge=0.0)
    risk: float = Field(default=0.0, ge=0.0, le=1.0)


class MultiStepPath(StrictModel):
    """A path through the multi-step graph.

    ``nodes`` is the ordered sequence of canonical SMILES visited.
    ``edge_ids`` is the ordered sequence of edges traversed (same length - 1).
    ``steps`` is the per-edge lineage (Step objects with full evidence/lane/ledger).
    ``total_cost`` and ``total_risk`` are accumulated along the path.
    """

    nodes: list[NonEmptyStr]
    edge_ids: list[NonEmptyStr]
    steps: list[Step] = []
    total_cost: float = Field(ge=0.0)
    total_risk: float = Field(ge=0.0, le=1.0)

    @field_validator("nodes")
    @classmethod
    def _at_least_one_node(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("path must have at least one node")
        return v

    @field_validator("nodes")
    @classmethod
    def _nodes_non_empty(cls, v: list[str]) -> list[str]:
        for n in v:
            if not n.strip():
                raise ValueError("node SMILES must not be empty")
        return v


class Budget(StrictModel):
    """Search budget constraints for multi-step exploration."""

    max_cost: float = Field(default=10.0, ge=0.0)
    max_risk: float = Field(default=1.0, ge=0.0, le=1.0)
    max_paths: int = Field(default=100, ge=1)


class StopRule(StrictModel):
    """A single stop rule: type + value.

    ``type`` is a controlled vocabulary: only "max_paths" is supported.
    Unknown types are rejected at construction (fail-closed, P9D-R1-05).
    """

    type: Literal["max_paths"]
    value: float = 0.0


class SearchConfig(StrictModel):
    """Configuration for multi-step search.

    ``beam_width`` controls branching (how many candidates to explore from each
    node). ``max_depth`` limits the path length. ``budget`` constrains the
    search cost/risk. ``stop_rules`` define additional termination conditions.
    """

    beam_width: int = Field(default=5, ge=1)
    max_depth: int = Field(default=5, ge=1)
    budget: Budget = Field(default_factory=Budget)
    stop_rules: list[StopRule] = []


class PathUncertainty(StrictModel):
    """Uncertainty metadata for a target molecule in a multi-step search.

    ``alternative_paths`` counts how many distinct paths reach this target.
    Higher count = more uncertainty about which path is correct.
    """

    target_molecule: NonEmptyStr
    alternative_paths: int = Field(ge=0)