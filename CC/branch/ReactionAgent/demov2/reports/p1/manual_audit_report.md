# P1-T11: Manual Audit Protocol — Report

**Task:** P1-T11 — Manual audit protocol (L2 double-blind annotation + adjudication)
**Status:** `BLOCKED_MANUAL_AUDIT_INCOMPLETE`
**Date:** 2026-07-30
**Protocol version:** `p1-t11-1`

## 1. Summary

The manual audit protocol, stratified sample manifest, and contract tests are
produced. The double-blind annotation and adjudication are **BLOCKED** because
no independent second annotator is available in the current LLM session.

Per §17.1 (iron rule), a single LLM execution process MUST NOT duplicate its
answers to impersonate double annotation. Per §17.7, no fabricated annotations
are generated. The audit is transparently marked
`BLOCKED_MANUAL_AUDIT_INCOMPLETE`.

## 2. Files produced

| File | Status |
|------|--------|
| `docs/manual_audit_protocol.md` | PRODUCED — protocol + frozen thresholds (§17.1-§17.10) |
| `schemas/json/ManualAuditRecord.json` | PRODUCED — T2 schema export |
| `reports/p1/manual_audit_sample_manifest.json` | PRODUCED — census of T10 fixture snapshot (4 records) |
| `reports/p1/manual_audit_annotations_a.json` | NOT PRODUCED — BLOCKED (§17.1/§17.7) |
| `reports/p1/manual_audit_annotations_b.json` | NOT PRODUCED — BLOCKED (§17.1/§17.7) |
| `reports/p1/manual_audit_adjudication.json` | NOT PRODUCED — BLOCKED (no A/B pair) |
| `reports/p1/manual_audit_report.md` | PRODUCED (this file) |
| `reports/p1/manual_audit_report.json` | PRODUCED — machine-readable, status=BLOCKED |
| `tests/p1/test_manual_audit_contract.py` | PRODUCED — GREEN in BLOCKED state |

## 3. Protocol (§17) — frozen before results

The protocol document (`docs/manual_audit_protocol.md`) was written and its
thresholds frozen **before** any annotation results were observed. The protocol
covers:

- **§17.1** Double-blind independence (two distinct annotators, blind to each
  other; single process duplicating answers is forbidden)
- **§17.2** Stratification (7 dimensions: reaction class, participant count,
  mapping quality, cofactor pattern, source, ledger status, quarantine reason)
- **§17.3** Rubric (11 items: R1-R11 across mapping/role/lineage/ledger domains)
- **§17.4** Catastrophic errors (9 items: C1-C9)
- **§17.5** Agreement metrics (raw + per-field agreement; LLM self-confidence
  forbidden as audit confidence)
- **§17.6** Pass threshold — 7 hard conditions H1-H7 frozen before results
- **§17.7** No fabricated annotations when blocked
- **§17.8-§17.10** Workflow, files, unblock requirements

### Frozen hard conditions (§17.6)

| # | Hard condition | Frozen value |
|---|----------------|--------------|
| H1 | catastrophic errors in production index = 0 | `0` |
| H2 | proline-2OG correct or quarantined | `true` |
| H3 | critical tie silently selected = 0 | `0` |
| H4 | quarantine leakage = 0 | `0` |
| H5 | participant destructive loss = 0 | `0` |
| H6 | formal→mechanistic false upgrade = 0 | `0` |
| H7 | snapshot replay / hash failure = 0 | `0` |

These thresholds are NOT adjusted based on results. They will be applied when
the audit is unblocked.

## 4. Stratified sample manifest

**Sample source:** T10 fixture snapshot (`snap_21172a43f2d9`)
**Sample strategy:** census (4 records ≤ 50 → full audit, no sampling)
**Random seed:** `null` (no sampling performed)

| Sample ID | Reaction ID | Lane | Source |
|-----------|-------------|------|--------|
| audit_001 | rxn_strict_001 | strict | fixture_source_a |
| audit_002 | rxn_cond_001 | conditional | fixture_source_a |
| audit_003 | rxn_diag_001 | diagnostic | fixture_source_a |
| audit_004 | rxn_quar_001 | quarantine | fixture_source_a |

> **Fixture disclaimer:** The sample is a T10 FIXTURE snapshot (synthetic data,
> `source_name = "fixture_source_a"`). It is not real production data. When
> rdkit becomes available and the real-source snapshot is built, the manifest
> should be regenerated from real data.

## 5. Why BLOCKED

### 5.1 No independent second annotator

The protocol (§17.1) requires **two independent annotators** — distinct agent
IDs / distinct human reviewers, each blind to the other's output. The current
LLM session is a single execution process. Using it to produce both
`annotations_a.json` and `annotations_b.json` would violate §17.1 (single
process duplicating answers to impersonate double annotation).

Acceptable second annotators (§17.10):
- A human domain expert (chemistry / biochemistry)
- An independent LLM instance in a **separate session** (different agent ID, no
  shared context with Annotator A)

### 5.2 No fabricated annotations (§17.7)

Per §17.7, when the audit cannot be completed, no fabricated annotations are
generated. The `annotations_a.json`, `annotations_b.json`, and
`adjudication.json` files are NOT produced with fake content.

### 5.3 Catastrophic error count cannot be determined

`catastrophic_error_count` is `null` because inter-annotator cross-check is
required to distinguish true catastrophic errors from single-annotator
mistakes. Without double annotation, this metric is undefined.

## 6. Agreement metrics

| Metric | Value | Reason |
|--------|-------|--------|
| raw agreement | `null` | No double annotation |
| per-field agreement | `null` | No double annotation |
| disagreement count | `null` | No double annotation |
| catastrophic_error_count | `null` | No double annotation |
| mapping_rubric_score | `null` | No double annotation |
| role_rubric_score | `null` | No double annotation |
| lineage_rubric_score | `null` | No double annotation |
| ledger_rubric_score | `null` | No double annotation |

## 7. LLM self-confidence (§17.5)

No LLM self-assessment confidence is used as audit confidence. The audit report
contains no `llm_confidence` / `confidence` / `self_confidence` field. Audit
quality is expressed only via `agreement` and `catastrophic_error_count`, both
`null` in BLOCKED state.

## 8. Contract tests

`tests/p1/test_manual_audit_contract.py` verifies:
1. Protocol document exists and contains the frozen threshold string
2. Sample manifest exists with correct structure
3. Report status is `BLOCKED_MANUAL_AUDIT_INCOMPLETE`
4. No fabricated annotations files exist (§17.7)
5. No LLM self-confidence in the report (§17.5)
6. `catastrophic_error_count` field is present (as `null`)
7. `ManualAuditRecord` JSON schema is valid
8. When annotations exist (future unblock), annotator IDs must be distinct (§17.1)
9. When adjudication exists (future unblock), required fields are present

All tests PASS in the BLOCKED state. Tests 8-9 use conditional early-return
(not pytest skip) so the suite reports zero skip.

## 9. Preflight context

The P1 preflight is BLOCKED:
- `rdkit_absent` — rdkit not installed; T4 mapping / T6 lineage / T7 ledger
  balance require rdkit
- `real_reaction_source_not_confirmed` — no real reaction source configured
- `required_case_missing` — proline-2OG case not found in real source

**Impact on audit:**
- T10 real-source snapshot is BLOCKED; only fixture snapshot available
- Proline-2OG case (required by H2) is not present in the fixture snapshot
- H2 cannot be evaluated until real data is available
- The protocol and thresholds remain frozen regardless

## 10. Unblock requirements

To transition from `BLOCKED_MANUAL_AUDIT_INCOMPLETE` to `COMPLETE`:

1. Provide a second independent annotator (human or separate LLM session)
2. Provide an independent adjudicator (human or separate LLM session)
3. (Ideally) Unblock preflight: install rdkit, configure real reaction source,
   build T10 real-source snapshot containing the proline-2OG case
4. Regenerate the sample manifest from the real-source snapshot (when available)
5. Re-run Steps 5-9 of the protocol workflow
6. Verify all hard conditions H1-H7 against real double-annotation results

The frozen thresholds in `docs/manual_audit_protocol.md` §17.6 are NOT adjusted.

## 11. Deviations / concerns

1. **BLOCKED audit → P1 Gate G10 cannot pass.** G10 requires "double annotation
   complete / adjudication complete / catastrophic errors=0". With the audit
   BLOCKED, G10 is BLOCKED. This is the expected, honest outcome — not a
   silent failure.

2. **Fixture snapshot is not real data.** The 4 audited records are synthetic
   fixtures. Even if double annotation were performed, the audit would only
   validate the fixture pipeline, not real chemistry. Real-source snapshot
   unblock (rdkit + real source) is needed for a meaningful audit.

3. **Proline-2OG case absent from fixture.** Hard condition H2 cannot be
   evaluated against the fixture snapshot. This is documented in the report;
   H2 remains frozen and pending.

4. **No LLM confidence used.** The report explicitly avoids `llm_confidence`
   and any self-assessment score. This complies with §17.5 but means the
   BLOCKED report carries no quality estimate — only the blockage status.

## 12. Verdict

**`BLOCKED_MANUAL_AUDIT_INCOMPLETE`.** Protocol, manifest, schema, and contract
tests are produced. Double-blind annotation and adjudication are BLOCKED due to
the absence of an independent second annotator. No fabricated annotations are
generated (§17.1/§17.7). Thresholds remain frozen (§17.6). P0 baseline 290 +
Gate 10/10 preserved. P1 Gate G10 = BLOCKED (expected, honest outcome).
