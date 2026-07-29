"""Common base model and enumerations for P0 contract freeze.

All schema models inherit from StrictModel which enforces:
- extra="forbid" (unknown fields rejected at all nesting levels)
- strict=True (no implicit type coercion: "1" ≠ 1, "1.0" ≠ 1.0)
- validate_default=True (defaults are validated)
- validate_assignment=True (field assignment validated)
- str_strip_whitespace=True

FORBIDDEN across all schemas:
- confidence / qualitative_confidence
- biological_probability
- enzyme_activity_probability
"""

from enum import Enum
from typing import Annotated
from pydantic import BaseModel, ConfigDict, Field, field_validator


# -- Strict base class --

class StrictModel(BaseModel):
    """Base model: strict typing, no coercion, no unknown fields."""
    model_config = ConfigDict(
        extra="forbid",
        strict=True,
        str_strip_whitespace=True,
        validate_assignment=True,
        validate_default=True,
    )


# -- Non-empty string type --

NonEmptyStr = Annotated[str, Field(min_length=1)]


def _validate_non_empty(v: str) -> str:
    """Reject empty or whitespace-only strings."""
    if not v or not v.strip():
        raise ValueError("String must not be empty or whitespace-only")
    return v


# -- Enumerations --

class MappingStatus(str, Enum):
    """Atom mapping status."""
    fully_mapped = "fully_mapped"
    partially_mapped = "partially_mapped"
    unmapped = "unmapped"
    mapping_failed = "mapping_failed"
    mapping_ambiguous = "mapping_ambiguous"


class MappingQualityClass(str, Enum):
    """Controlled quality label for mapping (replaces free-text confidence)."""
    high_quality = "high_quality"
    acceptable = "acceptable"
    low_quality = "low_quality"
    unknown = "unknown"


class SourceAssignmentMethod(str, Enum):
    """How the source assignment was derived."""
    formal_mapped = "formal_mapped"
    formal_mcs = "formal_mcs"
    manual_curation = "manual_curation"
    unknown = "unknown"


class LedgerBalanceStatus(str, Enum):
    """Source reaction ledger balance status (final_design §10.3)."""
    fully_balanced_explicit_reaction = "fully_balanced_explicit_reaction"
    heavy_atom_balanced_with_implicit_h_e_policy = "heavy_atom_balanced_with_implicit_h_e_policy"
    partial_or_unbalanced_source = "partial_or_unbalanced_source"


class ScientificAbstentionReason(str, Enum):
    """Scientific abstention reasons (final_design §15.3)."""
    INVALID_INPUT = "INVALID_INPUT"
    NO_IN_DOMAIN_DONOR = "NO_IN_DOMAIN_DONOR"
    NO_RESOLVED_LINEAGE = "NO_RESOLVED_LINEAGE"
    NO_TRANSFERABLE_TRANSFORM = "NO_TRANSFERABLE_TRANSFORM"
    NO_COMPATIBLE_SITE = "NO_COMPATIBLE_SITE"
    ALL_CANDIDATES_CHEMICALLY_INVALID = "ALL_CANDIDATES_CHEMICALLY_INVALID"
    EVIDENCE_CONFLICT = "EVIDENCE_CONFLICT"
    INSUFFICIENT_SUPPORT = "INSUFFICIENT_SUPPORT"
    OUT_OF_DOMAIN = "OUT_OF_DOMAIN"


class SystemFailureReason(str, Enum):
    """System/infrastructure failure reasons (final_design §15.4).
    Must NEVER be reported as scientific abstention."""
    SNAPSHOT_UNAVAILABLE = "SNAPSHOT_UNAVAILABLE"
    MAPPER_UNAVAILABLE = "MAPPER_UNAVAILABLE"
    TOOL_PROTOCOL_ERROR = "TOOL_PROTOCOL_ERROR"
    STORAGE_FAILURE = "STORAGE_FAILURE"
    BUDGET_CONFIGURATION_ERROR = "BUDGET_CONFIGURATION_ERROR"


class ResultStatus(str, Enum):
    """Prediction result status (final_design §22.5)."""
    completed = "completed"
    abstained = "abstained"
    partial = "partial"
    failed = "failed"


class DecisionKind(str, Enum):
    """Decision authority kind (ADR-0005)."""
    predicted = "predicted"
    abstained = "abstained"
    partial = "partial"
    failed = "failed"


class HypothesisOrigin(str, Enum):
    """Hypothesis origin discriminator (final_design §19)."""
    agent_selected_from_evidence_space = "agent_selected_from_evidence_space"
    agent_proposed = "agent_proposed"


class ApplicabilityLabel(str, Enum):
    """Structural applicability domain (final_design §16.4)."""
    in_domain = "in_domain"
    near_domain = "near_domain"
    out_of_domain = "out_of_domain"
    conflicted = "conflicted"
    unknown = "unknown"


class Lane(str, Enum):
    """Evidence lane for candidates (final_design §4.8)."""
    strict = "strict"
    generalized = "generalized"
    agent_proposed = "agent_proposed"


class ParticipantRole(str, Enum):
    """Reaction participant role hypotheses (final_design §7.3)."""
    transformed_substrate = "transformed_substrate"
    transformed_product = "transformed_product"
    co_substrate = "co_substrate"
    cofactor = "cofactor"
    carrier = "carrier"
    coproduct = "coproduct"
    spectator = "spectator"
    catalytic_species = "catalytic_species"
    unknown = "unknown"


class EligibilityStatus(str, Enum):
    """Strict production eligibility (ADR-0004 matrix)."""
    strict_eligible = "strict_eligible"
    conditional_eligible = "conditional_eligible"
    strict_prohibited = "strict_prohibited"
    quarantine = "quarantine"


class EvaluationBucket(str, Enum):
    """Evaluation bucket for eligibility matrix rows (ADR-0004)."""
    production = "production"
    diagnostic = "diagnostic"
    excluded = "excluded"


class QuarantineBehavior(str, Enum):
    """Quarantine behavior for eligibility matrix."""
    not_quarantined = "not_quarantined"
    quarantined = "quarantined"


class ResearchDiagnosticEligibility(str, Enum):
    """Whether a record can enter non-production research/diagnostic flows."""
    eligible = "eligible"
    not_eligible = "not_eligible"


class LineageResolutionQuality(str, Enum):
    """Controlled quality label for lineage resolution (replaces free-text confidence)."""
    resolved = "resolved"
    partially_resolved = "partially_resolved"
    unresolved = "unresolved"
    failed = "failed"


class AdaptationVerificationStatus(str, Enum):
    """Controlled verification status for candidate adaptation (Section 9).

    Replaces free-text confidence_note. Does NOT imply enzyme activity
    probability or experimental success probability.
    """
    unverified_analogy = "unverified_analogy"
    formally_mapped = "formally_mapped"
    evidence_supported = "evidence_supported"


class TargetKind(str, Enum):
    """Discriminator for typed atom/bond target."""
    atom = "atom"
    bond = "bond"


# -- Forbidden field scanner --

FORBIDDEN_FIELD_NAMES = frozenset({
    "confidence",
    "qualitative_confidence",
    "confidence_note",
    "llm_confidence",
    "llm_confidence_text",
    "biological_probability",
    "enzyme_activity_probability",
    "enzyme_feasibility",
    "enzyme_probability",
})
