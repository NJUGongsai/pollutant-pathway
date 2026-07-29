"""Reaction evidence and participant schemas (final_design §7).

ReactionEvidence is the primary fact unit. A→B is a resolved
transformed lineage within it, not two independently picked molecules.
COFACTORS are role/retrieval priors, never destructive stripping rules.
"""

from reaction_agent.schemas.common import (
    StrictModel,
    NonEmptyStr,
    ParticipantRole,
)
from reaction_agent.schemas.mapping import MappingReport
from reaction_agent.schemas.ledger import SourceReactionLedger


class RoleHypothesis(StrictModel):
    """A single role hypothesis for a participant."""
    role: ParticipantRole
    score: float = 0.0
    evidence_codes: list[NonEmptyStr] = []


class ReactionParticipant(StrictModel):
    """A single participant in a complete reaction (final_design §7.3)."""
    participant_id: NonEmptyStr
    molecule_id: NonEmptyStr
    canonical_smiles: NonEmptyStr
    side: NonEmptyStr  # "reactant" or "product"
    stoichiometry: int = 1
    formal_charge: int = 0
    atom_map_numbers: list[int] = []
    mapped_fraction: float = 0.0
    changed_atom_fraction: float = 0.0
    role_hypotheses: list[RoleHypothesis] = []
    donor_eligibility: bool = False
    provenance: list[NonEmptyStr] = []


class ReactionEvidence(StrictModel):
    """Complete reaction evidence record (final_design §7.2).

    No default primary_substrate/primary_product — those are legacy
    projections only.
    """
    reaction_id: NonEmptyStr
    source_record_id: NonEmptyStr
    source_name: NonEmptyStr
    source_version: NonEmptyStr = "unknown"
    source_uri_or_citation: str = ""
    raw_reaction: NonEmptyStr
    normalized_reaction: NonEmptyStr
    direction: NonEmptyStr = "unknown"
    participants: list[ReactionParticipant] = []
    mapping_report: MappingReport | None = None
    fragment_lineage_graph: dict[str, str] = {}
    resolved_transformed_lineages: list[NonEmptyStr] = []
    ambiguity_sets: list[dict[str, str]] = []
    transformation_hypotheses: list[NonEmptyStr] = []
    source_reaction_ledger: SourceReactionLedger | None = None
    quality_report: dict[str, str] = {}
    provenance: list[NonEmptyStr] = []
    snapshot_id: NonEmptyStr = "pending"
    quarantine: str | None = None
