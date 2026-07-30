# Manual Audit Protocol (§17)

**Task:** P1-T11 — Manual audit protocol (L2 double-blind annotation + adjudication)
**Status:** FROZEN — thresholds frozen BEFORE any results (§17.6)
**Frozen at:** 2026-07-30T00:00:00+00:00 (protocol mtime precedes any audit report)
**Protocol version:** `p1-t11-1`
**Authority:** `final_plan.md` §4.12 + `docs/superpowers/plans/2026-07-29-p1-data-foundation.md` Task 11

> **§17.1 Iron rule (命根子):** The audit must use **two independent annotators**
> (distinct agent IDs / distinct human reviewers), each blind to the other's
> output. **A single execution process MUST NOT duplicate its answers to
> impersonate double annotation.** If a second independent annotator is
> unavailable, the audit is `BLOCKED_MANUAL_AUDIT_INCOMPLETE` — no fake
> annotations are generated (§17.1/§17.7).

---

## §17.1 Double-blind independence

| Requirement | Enforcement |
|-------------|-------------|
| Two annotators (A, B) | Distinct `annotator_id`; distinct process / agent instance |
| Blind to each other | Annotator A cannot read B's output file and vice versa |
| Same sample manifest | Both annotate the identical `manual_audit_sample_manifest.json` |
| Same rubric | Both score against the 11 rubric items in §17.3 |
| No cross-contamination | Orchestrator dispatches A ∥ B in parallel; neither sees the other's annotations |
| Third-party adjudicator | Adjudicator is a third independent instance; reads A + B only after both complete |

**Forbidden (§17.1 violation):**
- One LLM execution copies its answers into both `annotations_a.json` and `annotations_b.json`.
- One annotator reads the other's file before submitting.
- Annotator B = Annotator A with trivial perturbations (same reasoning, different wording).

**Blocked condition:** If only one annotator is available (e.g. a single LLM
session with no independent second reviewer), the audit is
`BLOCKED_MANUAL_AUDIT_INCOMPLETE`. No `annotations_a.json` /
`annotations_b.json` / `adjudication.json` with fabricated content is produced.
The report records the blockage and the unblock requirement.

---

## §17.2 Stratification

The audit sample is drawn from the T10 snapshot, stratified across the seven
dimensions required by `final_plan.md` §4.12 ("覆盖"):

| # | Stratum dimension | Values sampled |
|---|-------------------|----------------|
| 1 | Reaction class | oxidation / reduction / hydroxylation / hydrolysis / transfer / cleavage |
| 2 | Participant count | single-reactant / multi-reactant / single-product / multi-product |
| 3 | Mapping quality | strict / conditional / diagnostic / quarantine |
| 4 | Cofactor pattern | with-cofactor / no-cofactor |
| 5 | Source | per `source_name` in snapshot |
| 6 | Ledger status | balanced / unbalanced / unknown |
| 7 | Quarantine reason | per `failure_counts_by_reason` key |

**Sample size rule:**
- **Small dataset (≤ 50 records):** full census — every record in the snapshot
  is audited. No sampling, no random seed needed.
- **Large dataset (> 50 records):** stratified random sample with a documented
  sample-size justification (e.g. Wilson interval half-width ≤ 0.1 at 95%
  confidence per stratum) and a fixed `random_seed` recorded in the manifest.

**Current snapshot:** T10 fixture snapshot has **4 records** (strict=1,
conditional=1, diagnostic=1, quarantine=1). This is a small dataset → **full
census** (all 4 records audited). The manifest records `sample_strategy:
"census"` and `random_seed: null` (no sampling performed).

> **Fixture labeling:** The T10 snapshot is a **fixture** snapshot
> (`source_name = "fixture_source_a"`), not real data. The manifest and report
> carry `sample_source: "fixture_snapshot_t10"` so no auditor mistakes fixture
> cases for real production data.

---

## §17.3 Rubric (11 items)

Each sampled record is scored against the following 11 rubric items. Each item
is binary (pass / fail). The per-domain score is the fraction of items passed
within that domain.

| # | Rubric item | Domain | What "pass" means |
|---|-------------|--------|-------------------|
| R1 | Mapping correctness | mapping | Atom mapping correctly reflects the chemical transformation (heavy-atom lineage consistent with reaction) |
| R2 | Role assignment correctness | role | Each participant role (substrate / product / cofactor / byproduct) is correctly assigned |
| R3 | Lineage resolution correctness | lineage | Source→product heavy-atom lineage is correct; no independent picking; split-merge-transfer handled |
| R4 | Ledger balance correctness | ledger | Source ledger is atom/charge balanced OR correctly flagged unbalanced/unknown |
| R5 | Formal vs mechanistic label | mapping | Formal mapping is NOT labeled as mechanistic; formal and mechanistic are separated |
| R6 | Participant completeness | role | No participant destructive loss — COFACTORS does not delete participants; small molecules can be substrate/source |
| R7 | Quarantine reason correctness | ledger | If quarantined, the reason is correctly typed (matches a `failure_counts_by_reason` key) |
| R8 | Eligibility lane correctness | ledger | Lane classification (strict / conditional / diagnostic / quarantine) matches the eligibility matrix decision |
| R9 | Production index exclusion | ledger | Quarantine records do NOT appear in the production index; production excludes quarantine |
| R10 | Snapshot determinism | ledger | Same source + same config + same versions → identical snapshot hash (replayable) |
| R11 | Proline-2OG specific case | lineage | Proline→hydroxyproline AND 2-oxoglutarate→succinate lineages are correct OR the case is quarantined; forbidden lineage 2-OG→hydroxyproline does NOT appear |

**Per-domain score aggregation:**
- `mapping_rubric_score` = mean(R1, R5)  — 2 items
- `role_rubric_score` = mean(R2, R6)  — 2 items
- `lineage_rubric_score` = mean(R3, R11)  — 2 items
- `ledger_rubric_score` = mean(R4, R7, R8, R9, R10)  — 5 items

Each score is in [0, 1]. The `ManualAuditRecord` schema (T2) stores these four
scores; no `confidence` field exists (§17.5).

---

## §17.4 Catastrophic errors (9 items)

A catastrophic error is a defect so severe that **any single occurrence** fails
the entire audit, regardless of agreement or rubric scores. The following 9
catastrophic errors are defined:

| # | Catastrophic error | Detection |
|---|--------------------|-----------|
| C1 | Catastrophic mismatch indexed in production index | A record with a known-correct mismatch classification appears in `production_index` |
| C2 | Proline-2OG incorrectly resolved | Proline/2OG case is neither correctly resolved nor quarantined (e.g. forbidden lineage 2-OG→hydroxyproline appears) |
| C3 | Critical tie silently selected | A critical tie (multiple equally-ranked candidates) is resolved by silent selection rather than explicit adjudication |
| C4 | Quarantine leakage | A quarantine-lane record appears in the production index |
| C5 | Participant destructive loss | COFACTORS processing deletes a participant from the multiset |
| C6 | Formal→mechanistic false upgrade | A formal mapping is presented / labeled as a mechanistic mapping |
| C7 | Snapshot replay / hash failure | Rebuilding the snapshot from the same inputs produces a different hash, or the loader rejects a valid snapshot (hash mismatch) |
| C8 | Source / candidate ledger mixed | A source-ledger record appears in the candidate ledger or vice versa |
| C9 | Partial source presented as fully balanced | A source ledger with unknown atoms/charge is presented as fully balanced (unknowns silently dropped) |

**Catastrophic error count:** The total number of distinct catastrophic errors
observed across the audited sample. This is an integer ≥ 0 stored in
`ManualAuditRecord.catastrophic_error_count` and in the audit report.

---

## §17.5 Agreement metrics

**Raw agreement:** fraction of rubric items where Annotator A and Annotator B
agree (both pass or both fail), averaged over all items × all sampled records.

```
raw_agreement = (# agreed items) / (11 × sample_size)
```

**Per-field agreement:** for each of the 11 rubric items, the fraction of
sampled records where A and B agree on that item.

**Disagreement count:** number of items where A and B disagree.

**Adjudication:** the Adjudicator (third independent instance) resolves each
disagreement by reviewing the evidence and selecting A or B (or a third
option). The adjudication outcome is recorded per disagreement.

**Forbidden — LLM self-confidence (§17.5):**
- The audit report JSON MUST NOT contain any of the forbidden substrings
  `llm_confidence`, `self_confidence`, or `confidence` anywhere in its text
  — not just as field names. The contract test
  `test_no_llm_self_confidence_as_audit` performs a full-string scan of the
  report JSON for all three substrings. This catches disguised variants like
  `llm_self_confidence_present` (where the `self_` infix breaks the narrower
  `llm_confidence` substring match) that a field-name-only check would miss.
- Audit confidence is expressed **only** via `agreement` (inter-annotator
  agreement) and `catastrophic_error_count`. These are objective, observable
  metrics — not the annotator's opinion of its own correctness.
- An LLM annotator's claim "I am 95% sure this mapping is correct" is **not**
  audit evidence and is discarded.

---

## §17.6 Pass threshold (FROZEN — precedes results)

> **The following thresholds are frozen BEFORE any audit results are observed.
> They MUST NOT be adjusted after seeing the results.** The protocol file's
> modification time precedes the audit report's modification time (enforced by
> the Orchestrator and verified by `test_threshold_frozen_before_results`).

### Hard conditions (all must hold — any failure → audit FAIL)

| # | Hard condition | Frozen value |
|---|----------------|--------------|
| H1 | catastrophic errors in production index = 0 | `0` |
| H2 | proline-2OG correct or quarantined | `true` |
| H3 | critical tie silently selected = 0 | `0` |
| H4 | quarantine leakage = 0 | `0` |
| H5 | participant destructive loss = 0 | `0` |
| H6 | formal→mechanistic false upgrade = 0 | `0` |
| H7 | snapshot replay / hash failure = 0 | `0` |

### Additional quality gates

| # | Quality gate | Threshold |
|---|--------------|-----------|
| Q1 | raw inter-annotator agreement | ≥ 0.90 |
| Q2 | catastrophic error count (total, all lanes) | `0` |
| Q3 | all domain rubric scores | ≥ 0.80 |
| Q4 | adjudication completed (all disagreements resolved) | `true` |

> **Note on H1:** "catastrophic errors in production index = 0" means zero
> records in the production index exhibit any of the 9 catastrophic error
> types. This is the hardest gate — a single catastrophic error in production
> fails the audit unconditionally.

> **Note on BLOCKED state:** If the audit is `BLOCKED_MANUAL_AUDIT_INCOMPLETE`
> (no second independent annotator), the pass threshold cannot be evaluated —
> `catastrophic_error_count` is `null` (cannot be computed without a second
> annotator to cross-check), and `pass_status` is `false` (blocked ≠ passed).
> The hard conditions H1-H7 remain frozen and will be applied when the audit
> is unblocked.

---

## §17.7 No fabricated annotations

> **§17.7:** If the audit cannot be completed (e.g. missing second annotator),
> **no fabricated annotations are generated.** The `annotations_a.json`,
> `annotations_b.json`, and `adjudication.json` files are NOT produced with
> fake content. The report transparently records the blockage.

**Forbidden:**
- Generating `annotations_a.json` / `annotations_b.json` with LLM-generated
  content labeled as if a second independent annotator produced it.
- Copying one annotator's output into both files with a different `annotator_id`.
- Generating `adjudication.json` with fabricated agreement/disagreement numbers
  when no real A/B pair exists.

**Required when blocked:**
- `manual_audit_report.{md,json}` with `status: "BLOCKED_MANUAL_AUDIT_INCOMPLETE"`.
- `catastrophic_error_count: null` (cannot be determined without double annotation).
- `pass_status: false`.
- `block_reason` documenting what is missing (e.g. "no independent second annotator available in current LLM session").
- `unblock_requirement` documenting what is needed to complete the audit.

---

## §17.8 Audit workflow

```
Step 1: Freeze protocol + thresholds (this document) — BEFORE results
Step 2: Generate stratified sample manifest from T10 snapshot (§17.2)
Step 3: RED — write contract tests (tests/p1/test_manual_audit_contract.py)
Step 4: Run RED — expected FAIL (annotations not generated)
Step 5: Double-blind annotation (Annotator A ∥ B, independent instances)
         → if no second annotator: BLOCKED_MANUAL_AUDIT_INCOMPLETE (§17.1/§17.7)
Step 6: Adjudicator resolves disagreements (third independent instance)
         → skipped if BLOCKED
Step 7: Generate audit report + GREEN
Step 8: P0/P1 regression (290 + all P1 green + Gate 10/10)
Step 9: Checkpoint report + worklog
```

---

## §17.9 Files produced

| File | Status (current cycle) |
|------|----------------------|
| `docs/manual_audit_protocol.md` | PRODUCED (this file, frozen) |
| `schemas/json/ManualAuditRecord.json` | PRODUCED (T2 schema export) |
| `reports/p1/manual_audit_sample_manifest.json` | PRODUCED (census of T10 fixture) |
| `reports/p1/manual_audit_annotations_a.json` | NOT PRODUCED (BLOCKED — no second annotator) |
| `reports/p1/manual_audit_annotations_b.json` | NOT PRODUCED (BLOCKED — no second annotator) |
| `reports/p1/manual_audit_adjudication.json` | NOT PRODUCED (BLOCKED — no A/B pair) |
| `reports/p1/manual_audit_report.md` | PRODUCED (status: BLOCKED_MANUAL_AUDIT_INCOMPLETE) |
| `reports/p1/manual_audit_report.json` | PRODUCED (status: BLOCKED_MANUAL_AUDIT_INCOMPLETE) |
| `tests/p1/test_manual_audit_contract.py` | PRODUCED (GREEN in BLOCKED state) |

---

## §17.10 Unblock requirements

To transition the audit from `BLOCKED_MANUAL_AUDIT_INCOMPLETE` to `COMPLETE`:

1. **Provide a second independent annotator.** Acceptable options:
   - A human domain expert (chemistry / biochemistry) who reviews each sampled
     record against the 11-item rubric without seeing Annotator A's output.
   - An independent LLM instance in a **separate session** (different agent ID,
     no shared context with Annotator A) that reviews each record against the
     rubric. The two LLM sessions must not share conversation history.
2. **Provide an independent adjudicator** (human or separate LLM instance) to
   resolve disagreements between A and B.
3. **Re-run Steps 5-9** of the workflow with the independent annotators.
4. **Verify all hard conditions H1-H7** against the real double-annotation
   results. The thresholds in this document remain frozen — do not adjust them.

> When rdkit becomes available and the T10 real-source snapshot is built, the
> audit sample manifest should be regenerated from the real-source snapshot
> (replacing the fixture census). The protocol and thresholds do not change.
