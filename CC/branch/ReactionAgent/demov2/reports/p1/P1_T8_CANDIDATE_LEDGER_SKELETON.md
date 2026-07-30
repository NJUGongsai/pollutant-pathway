# P1-T8: CandidateAnalogyLedger Skeleton

**Task:** P1-T8 — CandidateAnalogyLedger skeleton
**Status:** UNIT_CONTRACT_COMPLETE
**Builder version:** `p1-t8-1`
**Date:** 2026-07-30

## 1. Summary

Implemented
`build_candidate_skeleton(source_ledger, adaptation, *, candidate_id)`
`-> CandidateAnalogyLedger` in
`reaction_agent/ledgers/candidate_builder.py`. The builder constructs a
CandidateAnalogyLedger skeleton from a SourceReactionLedger +
QueryCandidateAdaptation + caller-provided candidate_id, inheriting donor
context as EXPLICIT ASSUMPTIONS and preserving unknowns.

**This is a skeleton + fixtures task only.** It does NOT implement the full
X→Y generator. It does NOT generate Y, rank candidates, or produce LLM
rationale (brief §14).

**5 key invariants enforced (§14):**
1. `donor_context_is_assumption = True` — `InheritedDonorContext.is_assumption`
   locked to True by schema (`Literal[True]`); builder populates contexts.
2. `source_ledger_link exists` — `source_ledger_id` mandatory, equals input
   `source_ledger.ledger_id`.
3. `candidate_id belongs current context` — caller-provided, echoed verbatim;
   builder does NOT generate candidate_id.
4. `donor cofactor != proven X→Y cofactor` — donor cofactors flow to
   `unknown_actual_cofactors`; no "proven cofactors" field exists.
5. `formal_balance_under_assumptions != observed balance` — separate object,
   labeled via `assumption_notes`; `candidate_balance_status` defaults to
   `partial_or_unbalanced_source`.

## 2. Files

| File | Action | Purpose |
|------|--------|---------|
| `reaction_agent/ledgers/candidate_builder.py` | Create | Skeleton builder (§14 invariants; no Y/ranking/rationale) |
| `reaction_agent/ledgers/__init__.py` | Modify | Export `build_candidate_skeleton` |
| `tests/p1/test_candidate_ledger_skeleton.py` | Create | 9 tests (5 invariants + no-Y + 3 edge) |
| `reports/p1/candidate_ledger_samples.json` | Create | 2 samples + invariant evidence |
| `reports/p1/P1_T8_CANDIDATE_LEDGER_SKELETON.md` | Create | This report |

## 3. Test results

### 3.1 RED → GREEN

```
RED:  ModuleNotFoundError: No module named 'reaction_agent.ledgers.candidate_builder'
      (1 collection error — module did not exist)
GREEN: 9 passed in 0.20s
```

### 3.2 Full regression

```
.venv/bin/python -m pytest tests -q -p no:cacheprovider -ra
545 passed in 0.49s   (baseline 536 + 9 new T8; zero skip/xfail)
```

Breakdown:
- P0 contracts: 290 passed (baseline preserved, no regression)
- P1: 255 passed (246 baseline + 9 new T8)

### 3.3 P0 Gate

```
.venv/bin/python scripts/run_p0_gate.py
Result: 10/10 passed
Status: READY_FOR_CHATGPT_AUDIT
```

No regression. P0 baseline 290 + Gate 10/10 preserved.

## 4. T8 test inventory (9 tests)

| # | Test | Invariant / Discipline |
|---|------|------------------------|
| 1 | `test_donor_context_is_assumption` | §14 Inv-1: is_assumption=True |
| 2 | `test_source_ledger_link_exists` | §14 Inv-2: source_ledger_id matches |
| 3 | `test_candidate_id_belongs_current_context` | §14 Inv-3: echoed verbatim; empty rejected |
| 4 | `test_donor_cofactor_not_proven_xy_cofactor` | §14 Inv-4: donor cofactors → unknown_actual_cofactors |
| 5 | `test_formal_balance_under_assumptions_not_observed` | §14 Inv-5: separate, labeled, partial default |
| 6 | `test_no_y_generated` | §14: no Y/ranking/rationale/Candidate |
| 7 | `test_builder_does_not_mutate_inputs` | Immutability |
| 8 | `test_donor_stoichiometry_flows_to_unknown` | No-fabrication: stoichiometry → unknown |
| 9 | `test_ledger_id_stable_and_content_addressed` | Stable hash (cal_ prefix) |

## 5. 5 invariant evidence (from `candidate_ledger_samples.json`)

```json
{
  "donor_context_is_assumption": [true],
  "source_ledger_link": true,
  "candidate_id_echoed": true,
  "donor_cofactor_to_unknown": ["p2"],
  "no_proven_cofactor_field": true,
  "formal_balance_assumption_notes": ["formal_balance_under_donor_assumptions:not_observed_for_xy"],
  "candidate_balance_not_observed": true
}
```

### 5.1 Invariant 1 — donor_context_is_assumption = True

`InheritedDonorContext.is_assumption` is locked to `Literal[True]` by the P0
schema. The builder populates `inherited_donor_context` with at least one
entry (donor_reaction_id, donor_participant_id, inherited_role from source
role_assignments). Every entry carries `is_assumption=True`.

### 5.2 Invariant 2 — source_ledger_link exists

`CandidateAnalogyLedger.source_ledger_id` is set to
`source_ledger.ledger_id` (mandatory `NonEmptyStr`). The link is never empty
or fabricated — it points to the real source ledger passed in.

### 5.3 Invariant 3 — candidate_id belongs current context

The builder does NOT generate `candidate_id` (generating one would be
generating a candidate, forbidden by §14). The caller provides
`candidate_id` from the current context; the builder echoes it back verbatim.
An empty `candidate_id` is rejected by the `NonEmptyStr` contract.

### 5.4 Invariant 4 — donor cofactor != proven X→Y cofactor

Donor cofactors from `source_ledger.cofactor_changes` flow to
`unknown_actual_cofactors` (inherited assumption). The
`CandidateAnalogyLedger` schema has NO field claiming cofactors are proven
for X→Y — only `unknown_actual_cofactors` exists. Verified:
`not hasattr(ledger, "proven_cofactors")` and
`not hasattr(ledger, "xy_cofactors")`.

### 5.5 Invariant 5 — formal_balance_under_assumptions != observed balance

`formal_balance_under_assumptions` is a separate
`FormalBalanceUnderAssumptions` object. It copies the source's
`element_balance` structure and `charge_balance` but labels them via
`assumption_notes=["formal_balance_under_donor_assumptions:not_observed_for_xy"]`.
`candidate_balance_status` defaults to `partial_or_unbalanced_source`
(assumption-based), which differs from the source's observed
`balance_status` (even when source is `heavy_atom_balanced...`).

## 6. No-Y evidence (§14)

The skeleton does NOT generate Y, rank candidates, or produce LLM rationale:

| Forbidden output | Evidence |
|------------------|----------|
| Y (product SMILES) | `CandidateAnalogyLedger` has no `canonical_product` / `generated_product_smiles` / `product_smiles` / `predicted_product` field |
| Candidate ranking | No `ranking_score` / `rank` field on ledger |
| LLM rationale | No `llm_rationale` / `rationale` / `explanation` field on ledger |
| Candidate object | No `candidate` field on ledger; `candidate_id` is a context handle, NOT a generated `Candidate` |
| Forbidden field names | `FORBIDDEN_FIELD_NAMES` scan: NONE hit on `CandidateAnalogyLedger` fields or builder source |

## 7. Signature deviation

**Brief signature:** `build_candidate_skeleton(source_ledger, adaptation) -> CandidateAnalogyLedger`

**Implemented signature:** `build_candidate_skeleton(source_ledger, adaptation, *, candidate_id) -> CandidateAnalogyLedger`

**Rationale:** `CandidateAnalogyLedger.candidate_id` is a mandatory
`NonEmptyStr` (P0 frozen schema). The builder must NOT generate candidate_id
(generating one would be generating a candidate, forbidden by §14). The
caller provides `candidate_id` from the current context as a keyword-only
argument. This is the minimal necessary deviation; the first two positional
arguments match the brief. Documented here and in the builder docstring.

## 8. Preflight BLOCKED note

Preflight BLOCKED (rdkit absent) does NOT affect T8. The skeleton inherits
donor context as assumptions and does not compute real element balance (that
is the source ledger's job in T7). `formal_balance_under_assumptions` copies
the source's already-computed structure but labels it as assumption-based —
no new chemical computation. Zero-skip: no `@pytest.mark.skipif`.

## 9. Verdict

UNIT_CONTRACT_COMPLETE. All 5 §14 invariants enforced. No Y/ranking/rationale
generated. P0 baseline 290 + Gate 10/10 preserved. P1 255 passed (zero skip).
