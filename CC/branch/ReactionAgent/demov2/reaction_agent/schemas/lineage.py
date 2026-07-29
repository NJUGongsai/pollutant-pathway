"""Fragment-lineage graph schemas (final_design §9).

Replaces legacy tuple-max() picking that caused proline/2-oxoglutarate mismatch.
Uses controlled quality enum, NOT free-text confidence.
"""

from reaction_agent.schemas.common import (
    StrictModel,
    NonEmptyStr,
    LineageResolutionQuality,
)


class LineageEdge(StrictModel):
    """Edge in bipartite fragment-lineage graph."""
    edge_id: NonEmptyStr
    reactant_participant_id: NonEmptyStr
    product_participant_id: NonEmptyStr
    shared_mapped_heavy_atoms: int = 0
    reactant_retention_fraction: float = 0.0
    product_origin_fraction: float = 0.0
    changed_mapped_atoms: list[int] = []
    bond_edit_participation: bool = False
    transferred_atom_sets: list[list[int]] = []
    scaffold_continuity: float = 0.0
    role_compatibility: bool = False
    mapping_quality: float = 0.0


class LineageHypothesis(StrictModel):
    """A single resolved transformed lineage hypothesis.

    Uses LineageResolutionQuality enum, NOT free-text confidence.
    """
    lineage_id: NonEmptyStr
    substrate_participant_id: NonEmptyStr
    product_participant_id: NonEmptyStr
    edge_ids: list[NonEmptyStr] = []
    transformed_atom_maps: list[int] = []
    resolution_quality: LineageResolutionQuality = LineageResolutionQuality.unresolved
    is_primary: bool = False


class LineageResolution(StrictModel):
    """Output of fragment-lineage graph resolution (final_design §9.2).

    Rules:
    - No independent side picking
    - No tuple max() silent tie-breaking
    - Multiple resolved lineages may coexist
    - Critical ambiguity → quarantine or non-strict
    """
    resolution_id: NonEmptyStr
    reaction_evidence_id: NonEmptyStr
    graph: dict[str, str] = {}
    resolved_transformed_lineages: list[LineageHypothesis] = []
    split_hypotheses: list[dict[str, str]] = []
    merge_hypotheses: list[dict[str, str]] = []
    atom_transfer_edges: list[dict[str, str]] = []
    ambiguity_sets: list[dict[str, str]] = []
    quality: LineageResolutionQuality = LineageResolutionQuality.unresolved
    failure_reason: str | None = None
