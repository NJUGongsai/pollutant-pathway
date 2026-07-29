"""Candidate schema (final_design §14).

Candidates are produced ONLY by deterministic graph-edit compiler.
LLM cannot create or modify candidate structures.
"""

from reaction_agent.schemas.common import (
    StrictModel,
    NonEmptyStr,
    Lane,
    ApplicabilityLabel,
)


class Candidate(StrictModel):
    """A validated candidate product (final_design §14).

    candidate_id is assigned only after passing validation.
    origin tracks which lane produced this candidate.
    """
    candidate_id: NonEmptyStr
    canonical_product: NonEmptyStr  # SMILES
    lane: Lane
    origin: NonEmptyStr  # hypothesis_origin that generated this
    generation_paths: list[dict] = []
    support_lineage_ids: list[NonEmptyStr] = []
    transformation_ids: list[NonEmptyStr] = []
    site_ids: list[NonEmptyStr] = []
    validation: dict = {}
    source_ledger_ids: list[NonEmptyStr] = []
    candidate_analogy_ledger_id: str | None = None
    ranking_score: float | None = None
    support_tier: str | None = None
    applicability: ApplicabilityLabel = ApplicabilityLabel.unknown
    provenance: list[NonEmptyStr] = []
