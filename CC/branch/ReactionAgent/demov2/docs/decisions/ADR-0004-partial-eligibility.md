# ADR-0004: Partial Eligibility

**Status:** Approved
**Date:** 2026-07-29

## Background

Not all source reactions are fully balanced with complete cofactor/stoichiometry information. A binary "accept all / quarantine all" approach is insufficient. We need a structured eligibility matrix that determines which source reactions can enter strict production, under what conditions, and which must be quarantined.

## Decision

### Eligibility Matrix

| Source/Ledger State | Strict Eligibility | Warnings | Quarantine | Eval Bucket | Research/Diagnostic |
|---|---|---|---|---|---|
| fully_balanced + reliable mapping/lineage | `strict_eligible` | none | no | production | eligible |
| heavy_atom_balanced, H+/e− policy incomplete | `conditional_eligible` | implicit_h_e_policy | no | production | eligible |
| missing noncritical cofactor stoichiometry, changed heavy atoms traceable | `conditional_eligible` | partial_cofactor_stoichiometry | no | production | eligible |
| changed heavy atom has no formal source/sink | `strict_prohibited` | missing_atom_source | no | diagnostic | eligible |
| critical element/charge contradiction | `quarantine` | critical_contradiction | yes | excluded | not_eligible |
| role ambiguity not affecting resolved lineage | `conditional_eligible` (lineage only) | role_ambiguity | no | production | eligible |
| lineage ambiguity affecting A→B identity | `strict_prohibited` | lineage_ambiguity | no | diagnostic | eligible |
| reaction direction unknown | `strict_prohibited` (directional) | unknown_direction | no | diagnostic | eligible |

### Canonical Machine Policy (Section 13)

The canonical machine-readable eligibility matrix lives in
`reaction_agent/policies/partial_eligibility.py` (`ELIGIBILITY_MATRIX`).
The JSON summary below is a documentation copy that MUST stay structurally
consistent with that file; the P0 Gate verifies equality to detect ADR/policy
drift (not just policy-internal self-consistency).

```json
{
  "states": [
    {"state": "fully_balanced_reliable_mapping", "strict_eligibility": "strict_eligible", "required_warnings": [], "quarantine_behavior": "not_quarantined", "evaluation_bucket": "production", "research_or_diagnostic_eligibility": "eligible"},
    {"state": "heavy_atom_balanced_implicit_he", "strict_eligibility": "conditional_eligible", "required_warnings": ["implicit_h_e_policy"], "quarantine_behavior": "not_quarantined", "evaluation_bucket": "production", "research_or_diagnostic_eligibility": "eligible"},
    {"state": "missing_noncritical_cofactor_stoich", "strict_eligibility": "conditional_eligible", "required_warnings": ["partial_cofactor_stoichiometry"], "quarantine_behavior": "not_quarantined", "evaluation_bucket": "production", "research_or_diagnostic_eligibility": "eligible"},
    {"state": "unknown_changed_heavy_atom_source", "strict_eligibility": "strict_prohibited", "required_warnings": ["missing_atom_source"], "quarantine_behavior": "not_quarantined", "evaluation_bucket": "diagnostic", "research_or_diagnostic_eligibility": "eligible"},
    {"state": "critical_element_charge_contradiction", "strict_eligibility": "quarantine", "required_warnings": ["critical_contradiction"], "quarantine_behavior": "quarantined", "evaluation_bucket": "excluded", "research_or_diagnostic_eligibility": "not_eligible"},
    {"state": "role_ambiguity_not_affecting_lineage", "strict_eligibility": "conditional_eligible", "required_warnings": ["role_ambiguity"], "quarantine_behavior": "not_quarantined", "evaluation_bucket": "production", "research_or_diagnostic_eligibility": "eligible"},
    {"state": "lineage_ambiguity_affecting_identity", "strict_eligibility": "strict_prohibited", "required_warnings": ["lineage_ambiguity"], "quarantine_behavior": "not_quarantined", "evaluation_bucket": "diagnostic", "research_or_diagnostic_eligibility": "eligible"},
    {"state": "reaction_direction_unknown", "strict_eligibility": "strict_prohibited", "required_warnings": ["unknown_direction"], "quarantine_behavior": "not_quarantined", "evaluation_bucket": "diagnostic", "research_or_diagnostic_eligibility": "eligible"}
  ]
}
```

### Ledger Balance Status

Source reactions use exactly three status values:

1. `fully_balanced_explicit_reaction` — all elements, charges, and stoichiometry accounted
2. `heavy_atom_balanced_with_implicit_h_e_policy` — heavy atoms balanced, H+/e− by policy
3. `partial_or_unbalanced_source` — missing information, explicitly labeled

### Rules

- Each matrix row has explicit eligibility, warnings, quarantine, and evaluation bucket
- No "it depends" without structured criteria
- Conditional eligibility requires warnings to be propagated to candidate ledger
- Quarantined records appear in snapshot manifest but not production index
- Diagnostic records are available for research but not production ranking

## What This ADR Does Not Do

- Does not define the algorithm for computing eligibility (P1)
- Does not define the audit protocol (P1)
- Does not define which cofactors are "noncritical"

## Failure Behavior

- Matrix row missing any of: eligibility, warnings, quarantine, eval bucket → ADR incomplete
- Duplicate or missing status values → schema violation
- Quarantined record in production index → data integrity violation

## Consequences

- Eligibility matrix is machine-readable and testable
- Every source reaction gets explicit classification
- Partial sources are usable with explicit warnings, not silently dropped or silently trusted

## Acceptance Criteria

- [x] All 8 matrix rows defined with all 4 columns
- [x] Three ledger balance statuses defined
- [x] No ambiguous "it depends" entries
- [x] Matrix is testable via contract tests

## Traceability

- final_design.md §10.4
- final_discussion.md §ChatGPT 6.3
