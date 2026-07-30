"""P1-T2 strict domain schemas — new entities for the P1 data foundation.

All classes inherit ``StrictModel`` (extra="forbid", strict=True,
str_strip_whitespace=True). No field uses any of the forbidden bias terms
listed in ``FORBIDDEN_FIELD_NAMES``; audit quality is expressed via
``agreement`` / ``catastrophic_error_count`` / rubric scores instead.

Field sources:
- final_design §7.1 (snapshot requirements), §7.2 (ReactionEvidence shape),
  §9.2 (LineageResolution), §10.4 (strict eligibility matrix)
- final_plan §4.12 (manual audit rubric: stratification, double annotation,
  disagreement, catastrophic error, mapping/role/lineage/ledger rubrics,
  pass threshold)
- chatgpt-reaction-analogy-agent-design-v2 §8.2 (donor eligibility criteria),
  §16.3 (freeze manifest)
- task-2-brief test code (field names verified verbatim)
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from pydantic import field_validator

from reaction_agent.schemas.common import (
    StrictModel,
    NonEmptyStr,
    EligibilityStatus,
    EvaluationBucket,
    QuarantineBehavior,
    ResearchDiagnosticEligibility,
    LineageResolutionQuality,
)

if TYPE_CHECKING:
    # Static-only import: type checkers see SourceRecordProvenance for the
    # ``provenance`` annotation. Runtime resolution is deferred to the bottom
    # of this module (after the class is defined) + the field_validator below,
    # so no import cycle is triggered during class construction.
    from reaction_agent.provenance import SourceRecordProvenance


# -- Normalized reaction record (final_design §7.1: raw + normalized kept) --


class NormalizedReactionRecord(StrictModel):
    """A normalized reaction record ready for evidence snapshot ingestion.

    Consumed by T4 (AtomMapper.map_reaction) and T3 (legacy audit replay).
    Keeps both the raw source reaction and the normalized reaction SMILES so
    that the snapshot is lossless and deterministic rebuild is possible.
    """

    reaction_id: NonEmptyStr
    source_record_id: NonEmptyStr
    normalized_reaction: NonEmptyStr
    raw_reaction: str = ""
    direction: str = "unknown"
    record_hash: str = ""
    normalization_version: str = "p1-1"
    # Typed as SourceRecordProvenance | None for static analysis (TYPE_CHECKING
    # import above). At runtime, the field_validator enforces isinstance, so a
    # bare dict like {'bogus':'dict'} is rejected instead of being silently
    # accepted as it was under the old ``object | None`` annotation.
    provenance: "SourceRecordProvenance | None" = None

    @field_validator("provenance", mode="before")
    @classmethod
    def _validate_provenance(cls, v):
        """Reject any value that is not a SourceRecordProvenance instance.

        Lazy import inside the validator avoids any import cycle
        (provenance.py imports only from schemas.common, never from this
        module, so the cycle is impossible — but the lazy import keeps the
        dependency direction explicit and defensive).
        """
        if v is None:
            return v
        from reaction_agent.provenance import SourceRecordProvenance
        if not isinstance(v, SourceRecordProvenance):
            raise ValueError(
                f"provenance must be a SourceRecordProvenance instance, "
                f"got {type(v).__name__}"
            )
        return v


# -- Donor eligibility (chatgpt v2 §8.2: donor molecule eligibility criteria) --


class DonorEligibilityAssessment(StrictModel):
    """Per-participant donor eligibility assessment (final_design §11.4 matrix).

    ``eligibility`` uses the §11.4 four-value vocabulary which is DISTINCT
    from the P0 ``EligibilityStatus`` enum (strict_eligible /
    conditional_eligible / strict_prohibited / quarantine) used by
    ``EligibilityDecision``. This object is the donor-side assessment fed
    into the strict eligibility matrix; ``EligibilityDecision`` is the
    production-side decision.
    """

    participant_id: NonEmptyStr
    eligibility: Literal["eligible", "conditionally_eligible", "not_eligible", "unknown"]
    reason_codes: list[NonEmptyStr]
    evidence_ids: list[NonEmptyStr] = []
    assessment_notes: str = ""


# -- Resolved transformed lineage (final_design §9.2 output) --


class ResolvedTransformedLineage(StrictModel):
    """A single resolved transformed A->B lineage within a reaction.

    Distinct from the P0 ``LineageHypothesis`` (which is a hypothesis skeleton
    inside ``LineageResolution``): this object is the post-resolution
    transformed lineage record emitted by the lineage resolver (T6), carrying
    the ambiguity verdict and supporting evidence IDs.
    """

    lineage_id: NonEmptyStr
    reactant_participant_id: NonEmptyStr
    product_participant_id: NonEmptyStr
    evidence_ids: list[NonEmptyStr] = []
    ambiguity: Literal["none", "partial", "critical"] = "none"
    transformed_atom_maps: list[int] = []
    resolution_quality: LineageResolutionQuality = LineageResolutionQuality.unresolved


# -- Eligibility decision (final_design §10.4 strict eligibility matrix) --


class EligibilityDecision(StrictModel):
    """Production-side eligibility decision for a participant.

    Uses the P0 ``EligibilityStatus`` enum (strict_eligible /
    conditional_eligible / strict_prohibited / quarantine) — this is the
    authoritative production decision, NOT the donor-side assessment.

    §15.2: the decision carries ``required_warnings`` and
    ``research_diagnostic_eligibility`` from the policy authority
    (``EligibilityMatrixRow``) so that §15.5 'conditional records carry
    required warnings' holds at the per-record level, not only via the row
    lookup. The engine populates these from ``get_row(state)``; they are NOT
    a second copied judgment set.
    """

    decision_id: NonEmptyStr
    participant_id: NonEmptyStr
    eligibility: EligibilityStatus
    evaluation_bucket: EvaluationBucket = EvaluationBucket.excluded
    quarantine_behavior: QuarantineBehavior = QuarantineBehavior.not_quarantined
    reason: NonEmptyStr
    evidence_ids: list[NonEmptyStr] = []
    required_warnings: list[NonEmptyStr] = []
    research_diagnostic_eligibility: ResearchDiagnosticEligibility = ResearchDiagnosticEligibility.eligible
    policy_version: str = "p1-1"


# -- Quarantine record (final_design §10.4: critical contradiction -> quarantine) --


class QuarantineRecord(StrictModel):
    """A quarantine record. ``reason`` is mandatory — never quarantine silently."""

    record_id: NonEmptyStr
    reason: NonEmptyStr  # required, no default — fail-closed
    category: str = "unspecified"
    evidence_ids: list[NonEmptyStr] = []
    source_record_id: str | None = None
    quarantine_behavior: QuarantineBehavior = QuarantineBehavior.quarantined
    notes: str = ""


# -- Snapshot manifest (chatgpt v2 §16.3 freeze + final_design §7.1) --


class SnapshotManifest(StrictModel):
    """Snapshot manifest: frozen counts + content hash + build status.

    Once a snapshot is FROZEN (§16.3) the manifest is immutable and
    replayable. Counts cover the four evaluation lanes (strict / conditional /
    diagnostic / quarantine) so that filtering before/after is auditable.
    """

    snapshot_id: NonEmptyStr
    schema_version: NonEmptyStr
    included_strict_count: int
    conditional_count: int
    diagnostic_count: int
    quarantine_count: int
    build_status: Literal["complete", "partial", "failed"]
    snapshot_hash: NonEmptyStr
    build_id: str = ""
    source_counts: dict[str, int] = {}
    policy_version: str = "p1-1"

    @field_validator("included_strict_count", "conditional_count",
                     "diagnostic_count", "quarantine_count")
    @classmethod
    def _counts_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError(f"count must be non-negative, got {v}")
        return v


# -- Snapshot record (final_design §7.1: immutable, content-addressed) --


class SnapshotRecord(StrictModel):
    """A frozen evidence snapshot record.

    References its manifest and the reaction evidence IDs it contains.
    ``freeze_status`` tracks the §16.1 lifecycle (pending -> frozen).
    """

    snapshot_id: NonEmptyStr
    manifest: SnapshotManifest | None = None
    reaction_evidence_ids: list[NonEmptyStr] = []
    build_config_hash: str = ""
    freeze_status: Literal["pending", "frozen"] = "pending"
    resources: dict[str, str] = {}


# -- Manual audit record (final_plan §4.12: manual audit protocol rubric) --


class ManualAuditRecord(StrictModel):
    """A manual audit record following the §4.12 rubric.

    Stratified sample with double annotation. Quality is expressed via
    ``agreement`` (inter-annotator agreement in [0, 1]) and
    ``catastrophic_error_count``; the four domain rubrics
    (mapping / role / lineage / ledger) each carry a score in [0, 1].
    No field uses the forbidden bias vocabulary.
    """

    record_id: NonEmptyStr
    stratum: NonEmptyStr
    sample_size: int
    annotator_count: int = 2  # double annotation
    agreement: float
    disagreement_count: int = 0
    catastrophic_error_count: int = 0
    mapping_rubric_score: float = 0.0
    role_rubric_score: float = 0.0
    lineage_rubric_score: float = 0.0
    ledger_rubric_score: float = 0.0
    pass_threshold: float = 0.0
    pass_status: bool = False
    notes: str = ""

    @field_validator("agreement", "mapping_rubric_score", "role_rubric_score",
                     "lineage_rubric_score", "ledger_rubric_score", "pass_threshold")
    @classmethod
    def _score_in_unit_interval(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError(f"score must be in [0, 1], got {v}")
        return v

    @field_validator("sample_size", "annotator_count", "disagreement_count",
                     "catastrophic_error_count")
    @classmethod
    def _non_negative_int(cls, v: int) -> int:
        if v < 0:
            raise ValueError(f"must be non-negative, got {v}")
        return v


# -- Forward-reference resolution for NormalizedReactionRecord.provenance --
#
# The ``provenance`` field is annotated as ``"SourceRecordProvenance | None"``
# (string forward ref) so that static type checkers resolve it via the
# TYPE_CHECKING import at the top of this module. Pydantic also needs to
# resolve the name at runtime to build the field schema. This import is
# deferred to the END of the module (after all classes are defined) so it
# cannot trigger an import cycle during class construction.
#
# Cycle safety proof: ``reaction_agent.provenance`` imports ONLY from
# ``reaction_agent.schemas.common`` (StrictModel, NonEmptyStr) — it does NOT
# import from ``reaction_agent.schemas.p1_entities`` or any other P1 module.
# Therefore importing it here is acyclic regardless of import order.
from reaction_agent.provenance import SourceRecordProvenance  # noqa: E402

NormalizedReactionRecord.model_rebuild()
