# P1-T9: Eligibility / Quarantine Engine

**Task:** P1-T9 — Eligibility / quarantine engine
**Status:** UNIT_CONTRACT_COMPLETE
**Engine version:** `p1-t9-1`
**Date:** 2026-07-30

## 1. Summary

Implemented `decide_eligibility(reaction_evidence, ledger, lineages)
-> EligibilityDecision` in `reaction_agent/eligibility/engine.py`. The engine
classifies a reaction evidence + source ledger + resolved lineages into one
of the 8 ADR-0004 matrix states, then **delegates** to
`policies.partial_eligibility.get_row(state)` — the ONLY policy authority
(§15.1) — to obtain the authoritative eligibility / bucket / quarantine /
warnings. **The engine does NOT duplicate the matrix or carry a second set of
eligibility strings.**

A helper `build_quarantine_record(decision, reaction_evidence) ->
QuarantineRecord | None` produces a `QuarantineRecord` for quarantine
decisions (returns `None` for non-quarantine; reason is always non-empty —
never silent quarantine).

**3 key disciplines enforced:**
1. **Policy reuse (§15.1)** — the engine calls `get_row(state)` and maps the
   row's fields to `EligibilityDecision`. No second eligibility string set.
2. **Fail-closed (§15.4)** — missing fields (None ledger, empty lineages,
   unknown direction) NEVER default to eligible. They route to quarantine or
   strict_prohibited per the priority ordering.
3. **Production index boundary (§15.5)** — enforced by the matrix row's
   `evaluation_bucket` and `quarantine_behavior`: quarantine → excluded,
   strict_prohibited → diagnostic, conditional → production (with warnings),
   strict_eligible → production. Diagnostic records remain auditable
   (`research_or_diagnostic_eligibility = eligible`).

## 2. Files

| File | Action | Purpose |
|------|--------|---------|
| `reaction_agent/eligibility/__init__.py` | Create | Package init; re-exports public API |
| `reaction_agent/eligibility/engine.py` | Create | Engine: `decide_eligibility` + `build_quarantine_record` |
| `tests/p1/test_eligibility_engine.py` | Create | 22 tests (8 matrix rows + fail-closed + boundary + reuse + priority) |
| `reports/p1/eligibility_matrix_execution.json` | Create | 8-row matrix execution evidence (positive + negative per row) |
| `reports/p1/P1_T9_ELIGIBILITY.md` | Create | This report |

## 3. Test results

### 3.1 RED → GREEN

```
RED:  ModuleNotFoundError: No module named 'reaction_agent.eligibility'
      (1 collection error — module did not exist)
GREEN: 22 passed in 0.23s
```

### 3.2 Full regression

```
.venv/bin/python -m pytest tests -q -p no:cacheprovider -ra
567 passed in 0.71s   (baseline 545 + 22 new T9; zero skip/xfail)
```

Breakdown:
- P0 contracts: 290 passed (baseline preserved, no regression)
- P1: 277 passed (255 baseline + 22 new T9)

### 3.3 P0 Gate

```
.venv/bin/python scripts/run_p0_gate.py
Result: 10/10 passed
Status: READY_FOR_CHATGPT_AUDIT
```

No regression. P0 baseline 290 + Gate 10/10 preserved.

## 4. T9 test inventory (22 tests)

| # | Test | Category / Discipline |
|---|------|----------------------|
| 1 | `test_matrix_row_1_fully_balanced_strict` | §15.3 Row 1: strict_eligible |
| 2 | `test_matrix_row_2_heavy_atom_implicit_he_conditional` | §15.3 Row 2: conditional (implicit_h_e_policy) |
| 3 | `test_matrix_row_3_missing_noncritical_cofactor_conditional` | §15.3 Row 3: conditional (partial_cofactor_stoichiometry) |
| 4 | `test_matrix_row_4_unknown_changed_heavy_atom_prohibited` | §15.3 Row 4: strict_prohibited (missing_atom_source) |
| 5 | `test_matrix_row_5_critical_contradiction_quarantine` | §15.3 Row 5: quarantine (critical_contradiction) |
| 6 | `test_matrix_row_6_role_ambiguity_lineage_local` | §15.3 Row 6: conditional (role_ambiguity) |
| 7 | `test_matrix_row_7_lineage_ambiguity_prohibited` | §15.3 Row 7: strict_prohibited (lineage_ambiguity) |
| 8 | `test_matrix_row_8_direction_unknown_prohibited` | §15.3 Row 8: strict_prohibited (unknown_direction) |
| 9 | `test_fail_closed_not_default_eligible` | §15.4 fail-closed (None ledger / empty lineages / unknown direction) |
| 10 | `test_quarantine_never_in_production_index` | §15.5 boundary: quarantine → excluded |
| 11 | `test_strict_prohibited_never_in_strict_index` | §15.5 boundary: strict_prohibited → diagnostic |
| 12 | `test_conditional_carries_required_warnings` | §15.5 boundary: conditional → non-empty warnings |
| 13 | `test_diagnostic_remains_auditable` | §15.5 boundary: diagnostic → research_eligible |
| 14 | `test_engine_classifies_all_eight_states` | Coverage: all 8 states reachable |
| 15 | `test_engine_reuses_policy_authority` | §15.1 reuse: decision matches `get_row(state)` |
| 16 | `test_build_quarantine_record_for_quarantine_decision` | QuarantineRecord helper (quarantine case) |
| 17 | `test_build_quarantine_record_returns_none_for_non_quarantine` | QuarantineRecord helper (non-quarantine → None) |
| 18 | `test_decide_eligibility_does_not_mutate_inputs` | Immutability |
| 19 | `test_decision_id_stable_and_content_addressed` | Stable hash (`ed_` prefix) |
| 20 | `test_decision_carries_evidence_ids_and_policy_version` | Evidence IDs + policy_version carried |
| 21 | `test_priority_charge_contradiction_overrides_unknown_source` | Priority: quarantine > strict_prohibited |
| 22 | `test_priority_lineage_ambiguity_overrides_role_ambiguity` | Priority: strict_prohibited > conditional |

## 5. 8-row matrix execution evidence

Source: `reports/p1/eligibility_matrix_execution.json`

Each row has a positive example (input triggering that state) and a negative
example (the row-1 perfect case, which does NOT trigger any severe state).
Every positive example's decision matches its matrix row authority:

| Row | State | Eligibility | Bucket | Quarantine | Warning |
|-----|-------|-------------|--------|------------|---------|
| 1 | `fully_balanced_reliable_mapping` | strict_eligible | production | not_quarantined | (none) |
| 2 | `heavy_atom_balanced_implicit_he` | conditional_eligible | production | not_quarantined | implicit_h_e_policy |
| 3 | `missing_noncritical_cofactor_stoich` | conditional_eligible | production | not_quarantined | partial_cofactor_stoichiometry |
| 4 | `unknown_changed_heavy_atom_source` | strict_prohibited | diagnostic | not_quarantined | missing_atom_source |
| 5 | `critical_element_charge_contradiction` | quarantine | excluded | quarantined | critical_contradiction |
| 6 | `role_ambiguity_not_affecting_lineage` | conditional_eligible | production | not_quarantined | role_ambiguity |
| 7 | `lineage_ambiguity_affecting_identity` | strict_prohibited | diagnostic | not_quarantined | lineage_ambiguity |
| 8 | `reaction_direction_unknown` | strict_prohibited | diagnostic | not_quarantined | unknown_direction |

**Verification:** all 8 positive examples' `eligibility`,
`evaluation_bucket`, and `quarantine_behavior` match
`get_row(state)` — the single policy authority. The engine introduces zero
new eligibility strings.

## 6. Fail-closed evidence (§15.4)

The engine NEVER defaults to eligible when strict-eligibility fields are
missing. Four fail-closed paths tested in `test_fail_closed_not_default_eligible`:

| Missing field | Classified state | Result | Never eligible |
|---------------|-----------------|--------|----------------|
| `ledger=None` | critical_element_charge_contradiction | quarantine, excluded | ✅ |
| `lineages=[]` | lineage_ambiguity_affecting_identity | strict_prohibited, diagnostic | ✅ |
| `direction="unknown"` | reaction_direction_unknown | strict_prohibited, diagnostic | ✅ |
| `direction="unknown"` + "perfect" ledger | reaction_direction_unknown | strict_prohibited, diagnostic | ✅ |

Additional fail-closed path: if `balance_status=partial_or_unbalanced_source`
but none of the specific severe conditions (charge mismatch, unknown source,
lineage ambiguity, direction unknown) match — e.g. source/mapping incomplete
or formal assignment ambiguous — the engine fails-closed to
`unknown_changed_heavy_atom_source` (not strict eligible). This is the
defensive default at the end of `_classify_state`.

## 7. Production index boundary evidence (§15.5)

| Boundary rule | Evidence |
|---------------|----------|
| Quarantine never in production | Matrix: every `quarantine` row has `evaluation_bucket=excluded`. Engine: `test_quarantine_never_in_production_index` |
| Strict_prohibited never in strict index | Matrix: every `strict_prohibited` row has `evaluation_bucket=diagnostic`. Engine: `test_strict_prohibited_never_in_strict_index` |
| Conditional carries required warnings | Matrix: every `conditional_eligible` row has non-empty `required_warnings`. Engine: `test_conditional_carries_required_warnings` |
| Diagnostic remains auditable | Matrix: every `diagnostic`-bucket row has `research_or_diagnostic_eligibility=eligible`. Engine: `test_diagnostic_remains_auditable` |

## 8. Classification priority (fail-closed: most severe wins)

The engine checks conditions in priority order — the first match wins, so the
most severe applicable condition always determines the state:

1. **critical_element_charge_contradiction** (quarantine) — ledger None OR
   `charge_balance != 0`. Most fundamental: charge conservation violated.
2. **lineage_ambiguity_affecting_identity** (strict_prohibited) — empty
   lineages OR any `ambiguity="critical"`. Identity uncertain.
3. **reaction_direction_unknown** (strict_prohibited) — direction is
   `"unknown"` or empty.
4. **unknown_changed_heavy_atom_source** (strict_prohibited) — any
   `AddedAtomSource` with `source_participant_id="unknown_source"`.
5. **role_ambiguity_not_affecting_lineage** (conditional) — any
   `RoleAssignment` with `role=unknown`, but lineages resolved.
6. **missing_noncritical_cofactor_stoich** (conditional) — cofactor changes
   with `direction="unknown"`.
7. **heavy_atom_balanced_implicit_he** (conditional) —
   `balance_status=heavy_atom_balanced_with_implicit_h_e_policy`.
8. **fully_balanced_reliable_mapping** (strict_eligible) —
   `balance_status=fully_balanced_explicit_reaction`.

Two priority tests verify the ordering:
- `test_priority_charge_contradiction_overrides_unknown_source`: when both
  charge mismatch (quarantine) and unknown source (strict_prohibited) are
  present, quarantine wins.
- `test_priority_lineage_ambiguity_overrides_role_ambiguity`: when both
  critical lineage ambiguity (strict_prohibited) and role ambiguity
  (conditional) are present, strict_prohibited wins.

## 9. Policy reuse — no second judgment set (§15.1)

The engine's source of truth is `policies.partial_eligibility.get_row(state)`.
The `EligibilityDecision` fields `eligibility`, `evaluation_bucket`, and
`quarantine_behavior` are set directly from the matrix row — NOT from a
duplicated set of strings in the engine. Verified by
`test_engine_reuses_policy_authority`:

```python
row = get_row("fully_balanced_reliable_mapping")
assert decision.eligibility is row.strict_eligibility       # same enum member
assert decision.evaluation_bucket is row.evaluation_bucket   # same enum member
assert decision.quarantine_behavior is row.quarantine_behavior  # same enum member
```

The engine's own code contains only **state-name strings** (the 8 canonical
state names used to look up the row) and **reason strings** (human-readable
descriptions). It contains zero eligibility/bucket/quarantine value strings
— those come exclusively from the matrix.

## 10. Signature note

**Brief signature:** `decide_eligibility(reaction_evidence, ledger, lineages) -> EligibilityDecision`

**Implemented signature:** `decide_eligibility(reaction_evidence, ledger, lineages) -> EligibilityDecision` — matches brief exactly.

**`participant_id` field:** `EligibilityDecision.participant_id` is set to
`reaction_evidence.reaction_id` (reaction-scoped decision). The §10.4
eligibility matrix is a reaction-level decision (can this reaction record
enter the production index?), so `reaction_id` is the natural scope
identifier. This is documented in the engine docstring.

## 11. Preflight BLOCKED note

Preflight BLOCKED (rdkit absent) does NOT affect T9. The engine reads the
ledger's already-computed fields (`balance_status`, `charge_balance`,
`added_atom_sources`, `cofactor_changes`, `role_assignments`) and the
reaction evidence's `direction` field. No new chemical computation. The
matrix classification is purely structural inspection. Zero-skip: no
`@pytest.mark.skipif`.

## 12. Verdict

UNIT_CONTRACT_COMPLETE. All 8 matrix rows executed. Fail-closed enforced
(4 missing-field paths + defensive default). Production index boundary
enforced (4 boundary tests). Policy authority reused (no second judgment
set). P0 baseline 290 + Gate 10/10 preserved. P1 277 passed (zero skip).
