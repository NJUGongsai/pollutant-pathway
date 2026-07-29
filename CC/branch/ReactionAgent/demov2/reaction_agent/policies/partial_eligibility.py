"""Partial eligibility policy — single machine-readable source of truth.

This is the ONLY authoritative definition of the eligibility matrix.
ADR-0004 must be consistent with this file. Tests import from here.
"""

import json
import re

from reaction_agent.schemas.common import (
    StrictModel,
    NonEmptyStr,
    EligibilityStatus,
    EvaluationBucket,
    QuarantineBehavior,
    ResearchDiagnosticEligibility,
)


class EligibilityMatrixRow(StrictModel):
    """One row of the partial eligibility matrix."""
    state: NonEmptyStr
    strict_eligibility: EligibilityStatus
    required_warnings: list[NonEmptyStr]
    quarantine_behavior: QuarantineBehavior
    evaluation_bucket: EvaluationBucket
    research_or_diagnostic_eligibility: ResearchDiagnosticEligibility


# -- The 8-state matrix --

ELIGIBILITY_MATRIX: list[EligibilityMatrixRow] = [
    EligibilityMatrixRow(
        state="fully_balanced_reliable_mapping",
        strict_eligibility=EligibilityStatus.strict_eligible,
        required_warnings=[],
        quarantine_behavior=QuarantineBehavior.not_quarantined,
        evaluation_bucket=EvaluationBucket.production,
        research_or_diagnostic_eligibility=ResearchDiagnosticEligibility.eligible,
    ),
    EligibilityMatrixRow(
        state="heavy_atom_balanced_implicit_he",
        strict_eligibility=EligibilityStatus.conditional_eligible,
        required_warnings=["implicit_h_e_policy"],
        quarantine_behavior=QuarantineBehavior.not_quarantined,
        evaluation_bucket=EvaluationBucket.production,
        research_or_diagnostic_eligibility=ResearchDiagnosticEligibility.eligible,
    ),
    EligibilityMatrixRow(
        state="missing_noncritical_cofactor_stoich",
        strict_eligibility=EligibilityStatus.conditional_eligible,
        required_warnings=["partial_cofactor_stoichiometry"],
        quarantine_behavior=QuarantineBehavior.not_quarantined,
        evaluation_bucket=EvaluationBucket.production,
        research_or_diagnostic_eligibility=ResearchDiagnosticEligibility.eligible,
    ),
    EligibilityMatrixRow(
        state="unknown_changed_heavy_atom_source",
        strict_eligibility=EligibilityStatus.strict_prohibited,
        required_warnings=["missing_atom_source"],
        quarantine_behavior=QuarantineBehavior.not_quarantined,
        evaluation_bucket=EvaluationBucket.diagnostic,
        research_or_diagnostic_eligibility=ResearchDiagnosticEligibility.eligible,
    ),
    EligibilityMatrixRow(
        state="critical_element_charge_contradiction",
        strict_eligibility=EligibilityStatus.quarantine,
        required_warnings=["critical_contradiction"],
        quarantine_behavior=QuarantineBehavior.quarantined,
        evaluation_bucket=EvaluationBucket.excluded,
        research_or_diagnostic_eligibility=ResearchDiagnosticEligibility.not_eligible,
    ),
    EligibilityMatrixRow(
        state="role_ambiguity_not_affecting_lineage",
        strict_eligibility=EligibilityStatus.conditional_eligible,
        required_warnings=["role_ambiguity"],
        quarantine_behavior=QuarantineBehavior.not_quarantined,
        evaluation_bucket=EvaluationBucket.production,
        research_or_diagnostic_eligibility=ResearchDiagnosticEligibility.eligible,
    ),
    EligibilityMatrixRow(
        state="lineage_ambiguity_affecting_identity",
        strict_eligibility=EligibilityStatus.strict_prohibited,
        required_warnings=["lineage_ambiguity"],
        quarantine_behavior=QuarantineBehavior.not_quarantined,
        evaluation_bucket=EvaluationBucket.diagnostic,
        research_or_diagnostic_eligibility=ResearchDiagnosticEligibility.eligible,
    ),
    EligibilityMatrixRow(
        state="reaction_direction_unknown",
        strict_eligibility=EligibilityStatus.strict_prohibited,
        required_warnings=["unknown_direction"],
        quarantine_behavior=QuarantineBehavior.not_quarantined,
        evaluation_bucket=EvaluationBucket.diagnostic,
        research_or_diagnostic_eligibility=ResearchDiagnosticEligibility.eligible,
    ),
]


# -- Validation helpers --

EXPECTED_STATES = frozenset(row.state for row in ELIGIBILITY_MATRIX)


def get_row(state: str) -> EligibilityMatrixRow | None:
    """Get matrix row by state name."""
    for row in ELIGIBILITY_MATRIX:
        if row.state == state:
            return row
    return None


def validate_matrix_integrity() -> list[str]:
    """Validate matrix integrity. Returns list of issues (empty = valid)."""
    issues = []
    states = [row.state for row in ELIGIBILITY_MATRIX]

    if len(states) != 8:
        issues.append(f"Expected 8 states, got {len(states)}")
    if len(states) != len(set(states)):
        issues.append("Duplicate states found")

    for row in ELIGIBILITY_MATRIX:
        if row.strict_eligibility == EligibilityStatus.strict_prohibited:
            if row.evaluation_bucket == EvaluationBucket.production:
                issues.append(f"{row.state}: strict_prohibited in production bucket")
        if row.strict_eligibility == EligibilityStatus.quarantine:
            if row.quarantine_behavior != QuarantineBehavior.quarantined:
                issues.append(f"{row.state}: quarantine status but not quarantined")
            if row.evaluation_bucket != EvaluationBucket.excluded:
                issues.append(f"{row.state}: quarantine but not in excluded bucket")
        if row.strict_eligibility == EligibilityStatus.conditional_eligible:
            if not row.required_warnings:
                issues.append(f"{row.state}: conditional but no required warnings")

    return issues


def export_policy_manifest() -> list[dict]:
    """Export the eligibility matrix as a list of plain dicts.

    Used by the P0 Gate to verify structural equality with the ADR-0004
    machine-readable policy summary (Section 13 drift check). This is the
    canonical export; the ADR-0004 JSON block is a documentation copy that
    must match it.
    """
    return [
        {
            "state": row.state,
            "strict_eligibility": row.strict_eligibility.value,
            "required_warnings": list(row.required_warnings),
            "quarantine_behavior": row.quarantine_behavior.value,
            "evaluation_bucket": row.evaluation_bucket.value,
            "research_or_diagnostic_eligibility": row.research_or_diagnostic_eligibility.value,
        }
        for row in ELIGIBILITY_MATRIX
    ]


def parse_adr_manifest_json(adr_text: str) -> list[dict]:
    """Extract the JSON policy manifest from ADR-0004 markdown text.

    Returns the 'states' list. Raises ValueError if no valid json block found.
    """
    match = re.search(r"```json\s*\n(.*?)\n```", adr_text, re.DOTALL)
    if not match:
        raise ValueError("ADR-0004: no json manifest block found")
    data = json.loads(match.group(1))
    return data["states"]


def compare_manifests(
    adr_manifest: list[dict], policy_manifest: list[dict]
) -> list[str]:
    """Compare an ADR manifest with the canonical policy manifest.

    Returns a list of drift issues (empty = consistent). Detects row-count,
    state-set, and per-field drift — including warning ID mismatches.
    """
    issues: list[str] = []
    if len(adr_manifest) != len(policy_manifest):
        issues.append(
            f"row count drift: ADR={len(adr_manifest)}, policy={len(policy_manifest)}"
        )
    adr_by_state = {row["state"]: row for row in adr_manifest}
    policy_by_state = {row["state"]: row for row in policy_manifest}
    adr_states = set(adr_by_state)
    policy_states = set(policy_by_state)
    if adr_states != policy_states:
        issues.append(
            f"state set drift: ADR-only={sorted(adr_states - policy_states)}, "
            f"policy-only={sorted(policy_states - adr_states)}"
        )
    for state in adr_states & policy_states:
        adr_row = adr_by_state[state]
        policy_row = policy_by_state[state]
        for key in ("strict_eligibility", "quarantine_behavior",
                    "evaluation_bucket", "research_or_diagnostic_eligibility"):
            if adr_row.get(key) != policy_row.get(key):
                issues.append(
                    f"{state}: {key} drift: ADR={adr_row.get(key)}, "
                    f"policy={policy_row.get(key)}"
                )
        adr_warnings = sorted(adr_row.get("required_warnings", []))
        policy_warnings = sorted(policy_row.get("required_warnings", []))
        if adr_warnings != policy_warnings:
            issues.append(
                f"{state}: required_warnings drift: ADR={adr_warnings}, "
                f"policy={policy_warnings}"
            )
    return issues
