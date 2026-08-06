"""P4 versioned decision policy (final_design §18.3, §16.1-§16.4, §15.3).

The versioned deterministic decision policy is the SOLE authority for:
status, decision, reason_code, rank, lane, validation, applicability
(ADR-0005). P4 freezes here the pieces the authority documents leave open:

- abstention reason precedence (uses final_design §15.3 list order);
- support tier ordinal vocabulary (P4 deliverable, not probability);
- evidence strength ordinal vocabulary (P4 deliverable, not probability);
- applicability reason codes (P4 deliverable, structural only);
- counterevidence typed reason set (final_design §16.2 allowed list);
- strict ranker frozen weights (baseline weights, train/validation-tunable
  only via a NEW policy version, never runtime mutation);
- dedup dimensions (final_design §4.9, final_plan §7.1).

Immutability contract: every policy constant here is version-pinned. A change
to any weight/precedence/vocabulary MUST bump P4_POLICY_VERSION. Consumers
record the policy version in every output (support breakdown, ranking,
abstention, manifest).
"""
from __future__ import annotations

P4_POLICY_VERSION = "p4-policy-1"

# -- Abstention precedence (final_design §15.3 frozen list order) -----------
# Earliest reason in this order wins when multiple apply (P4-T6 mandate:
# "结果按照冻结顺序只选择最早 primary reason").
ABSTENTION_PRECEDENCE: tuple[str, ...] = (
    "INVALID_INPUT",
    "NO_IN_DOMAIN_DONOR",
    "NO_RESOLVED_LINEAGE",
    "NO_TRANSFERABLE_TRANSFORM",
    "NO_COMPATIBLE_SITE",
    "ALL_CANDIDATES_CHEMICALLY_INVALID",
    "EVIDENCE_CONFLICT",
    "INSUFFICIENT_SUPPORT",
    "OUT_OF_DOMAIN",
)

# -- Support tier ordinal vocabulary (P4 deliverable) ------------------------
# Ordinal, NOT a probability. "strong" means multiple independent,
# high-quality, structurally grounded evidence rows support the candidate.
SUPPORT_TIERS: tuple[str, ...] = ("none", "weak", "moderate", "strong")
SUPPORT_TIER_ORDINAL = {"none": 0, "weak": 1, "moderate": 2, "strong": 3}

# -- Evidence strength ordinal vocabulary (P4 deliverable) ------------------
EVIDENCE_STRENGTHS: tuple[str, ...] = (
    "none",
    "single_source",
    "multiple_independent_sources",
    "high_quality_multiple_independent",
)
EVIDENCE_STRENGTH_ORDINAL = {
    "none": 0,
    "single_source": 1,
    "multiple_independent_sources": 2,
    "high_quality_multiple_independent": 3,
}

# -- Support feature keys (final_design §16.1, final_plan §7.2) --------------
SUPPORT_FEATURES: tuple[str, ...] = (
    "donor_structural_similarity",
    "transform_recurrence",
    "site_compatibility",
    "mapping_lineage_quality",
    "source_quality",
    "ledger_completeness",
    "independent_support_count",
    "retrieval_stability",
)

# -- Ranking feature keys + frozen baseline weights (final_design §18.2) ----
RANKING_FEATURES: tuple[str, ...] = (
    "donor_similarity",
    "transform_support",
    "site_compatibility",
    "mapping_lineage_quality",
    "ledger_completeness",
    "evidence_independence",
    "source_quality",
    "conflict_penalty",
    "retrieval_stability",
)
# Baseline weights: ordinal contributions are {0,1,2,3} per feature; the
# score is the weighted average over OBSERVABLE features. conflict_penalty is
# subtracted. Weights are NOT probabilities.
RANKER_WEIGHTS: dict[str, float] = {
    "donor_similarity": 0.20,
    "transform_support": 0.20,
    "site_compatibility": 0.15,
    "mapping_lineage_quality": 0.15,
    "ledger_completeness": 0.10,
    "evidence_independence": 0.10,
    "source_quality": 0.05,
    "conflict_penalty": 0.05,
    "retrieval_stability": 0.05,
}

# -- Applicability reason codes (P4 deliverable, structural only) -----------
APPLICABILITY_REASON_CODES: tuple[str, ...] = (
    "IN_DOMAIN_DONOR",
    "NEAR_DOMAIN_SIMILARITY",
    "OUT_OF_DOMAIN_QUERY",
    "CONFLICTED_EVIDENCE",
    "NO_STRUCTURAL_EVIDENCE",
)

# -- Counterevidence typed reasons (final_design §16.2 allowed list) --------
ALLOWED_COUNTEREVIDENCE: tuple[str, ...] = (
    "COMPETING_TRANSFORM",
    "FAILED_TRANSFORM_PRECONDITIONS",
    "SITE_INCOMPATIBILITY",
    "INVALID_GENERATION",
    "LEDGER_CONTRADICTION",
    "PROVENANCE_DIRECTION_ROLE_CONFLICT",
    "STRICT_FAILURE_ONLY_RELAXATION",
    "ALL_SUPPORT_LOW_QUALITY_OR_SAME_SOURCE",
)

# -- Evidence dedup dimensions (final_design §4.9, final_plan §7.1) ----------
DEDUP_DIMENSIONS: tuple[str, ...] = (
    "source_lineage",
    "database_mirror",
    "same_publication",
    "same_normalized_reaction",
    "mapper_duplicate",
    "same_donor_transform",
)

# -- Forbidden field names enforced by P4 schemas (ADR-0005) ----------------
FORBIDDEN_PROBABILITY_FIELDS: frozenset[str] = frozenset({
    "confidence",
    "qualitative_confidence",
    "confidence_note",
    "llm_confidence",
    "llm_confidence_text",
    "biological_probability",
    "enzyme_activity_probability",
    "enzyme_feasibility",
    "enzyme_probability",
    "activity_probability",
})
