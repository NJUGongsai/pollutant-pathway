# P1-T2: Strict Domain Schemas — Checkpoint Report

**Task:** P1-T2 Strict domain schemas
**Status:** PASS
**Date:** 2026-07-30
**Execution model:** Claude Code subagent (deviation: original plan specified Qwen)

## 1. Summary

Extended the P0 frozen schema set with 8 new P1 domain entities in
`reaction_agent/schemas/p1_entities.py`, all inheriting `StrictModel`
(`extra="forbid"`, `strict=True`). No P0 frozen schema was modified —
P0 `evidence.py` / `mapping.py` / `lineage.py` / `ledger.py` already
implement `final_design` §7/§8/§9/§10 completely and were confirmed
field-complete during the Step 1 gap inventory.

**Test result:** 27 new contract tests, all green. P0 baseline unchanged.

## 2. Gap inventory (Step 1)

### 2.1 P0 frozen — already exist (NOT recreated)

| # | Object | File | final_design ref |
|---|--------|------|------------------|
| 1 | `MappingReport` | mapping.py | §8 |
| 2 | `FormalMappedAtomPair` | mapping.py | §11 |
| 3 | `MechanisticAtomOrigin` | mapping.py | §11 |
| 4 | `ReactionParticipant` | evidence.py | §7.3 |
| 5 | `ReactionEvidence` | evidence.py | §7.2 |
| 6 | `RoleHypothesis` | evidence.py | §7.3 |
| 7 | `LineageEdge` | lineage.py | §9.1 |
| 8 | `LineageHypothesis` | lineage.py | §9.2 |
| 9 | `LineageResolution` | lineage.py | §9.2 |
| 10 | `SourceReactionLedger` | ledger.py | §10.1 |
| 11 | `CandidateAnalogyLedger` | ledger.py | §10.2 |

### 2.2 T1 already built (NOT recreated)

| # | Object | File |
|---|--------|------|
| 12 | `SourceRecordProvenance` | provenance.py |
| 13 | `BuildConfig` | config.py |
| 14 | `BuildInfo` | config.py |

### 2.3 T2 new entities (created in `p1_entities.py`)

| # | Object | Field source |
|---|--------|--------------|
| 15 | `NormalizedReactionRecord` | §7.1 (raw+normalized kept), T4 test contract |
| 16 | `DonorEligibilityAssessment` | §8.2/§11.4 (4-value Literal, distinct from P0 enum) |
| 17 | `ResolvedTransformedLineage` | §9.2 (post-resolution lineage record) |
| 18 | `EligibilityDecision` | §10.4 (uses P0 `EligibilityStatus` enum) |
| 19 | `QuarantineRecord` | §10.4 (reason mandatory, fail-closed) |
| 20 | `SnapshotManifest` | §16.3 freeze + §7.1 (counts/hash/build_status) |
| 21 | `SnapshotRecord` | §7.1 (immutable, content-addressed) |
| 22 | `ManualAuditRecord` | final_plan §4.12 rubric (agreement, not confidence) |

### 2.4 Confirmed non-objects (brief Step 1 open questions)

- **`FragmentLineageGraph`**: NOT a standalone class in P0. The fragment-lineage
  graph is carried as `ReactionEvidence.fragment_lineage_graph: dict[str, str]`
  and `LineageResolution.graph: dict[str, str]`. No class to create.
- **`ParticipantRoleHypothesis`**: confirmed identical to P0 `RoleHypothesis`
  (`evidence.py` line 17: `role` + `evidence_codes`). No duplicate created.

## 3. Key design decisions

### 3.1 Two distinct eligibility vocabularies (critical)

The brief flags that `DonorEligibilityAssessment.eligibility` (§11.4) is
**NOT** the P0 `EligibilityStatus` enum. This is confirmed and enforced:

| Object | eligibility type | Values |
|--------|-----------------|--------|
| `DonorEligibilityAssessment` | `Literal[...]` | `eligible` / `conditionally_eligible` / `not_eligible` / `unknown` |
| `EligibilityDecision` | P0 `EligibilityStatus` enum | `strict_eligible` / `conditional_eligible` / `strict_prohibited` / `quarantine` |

`DonorEligibilityAssessment` is the donor-side assessment; `EligibilityDecision`
is the production-side decision. They must not be conflated.

### 3.2 ManualAuditRecord uses agreement, not confidence

Per final_plan §4.12 and brief constraint, `ManualAuditRecord` expresses
audit quality via:
- `agreement: float` (inter-annotator agreement, [0, 1])
- `catastrophic_error_count: int`
- `mapping_rubric_score` / `role_rubric_score` / `lineage_rubric_score` /
  `ledger_rubric_score` (each [0, 1])

No field uses any `FORBIDDEN_FIELD_NAMES` term. Verified by
`test_forbidden_fields_absent` (source scan) and
`test_manual_audit_record_no_confidence_field` (model_fields scan).

### 3.3 QuarantineRecord is fail-closed

`reason: NonEmptyStr` has no default — `QuarantineRecord(record_id="q1")`
raises `ValidationError`. Empty/whitespace reasons are rejected by
`StrictModel.str_strip_whitespace=True` + `NonEmptyStr` min_length=1.

## 4. Test results

### 4.1 RED (Step 3)
```
.venv/bin/python -m pytest tests/p1/test_domain_schemas.py -q -p no:cacheprovider -ra
→ 1 error during collection: ModuleNotFoundError: No module named 'reaction_agent.schemas.p1_entities'
```

### 4.2 GREEN (Step 5/8)
```
.venv/bin/python -m pytest tests/p1/test_domain_schemas.py -q -p no:cacheprovider -ra
→ 27 passed in 0.12s
```

Test breakdown:
- 5 brief Step 2 strictness tests (unknown field, forbidden fields, donor eligibility, quarantine reason, snapshot counts)
- 2 brief Step 7 stable_id/content_hash tests
- 20 additional contract tests (StrictModel inheritance, extra=forbid on all 8 classes, field types, enum usage, rubric scores, agreement bounds)

### 4.3 JSON schema export (Step 9)
```
.venv/bin/python scripts/export_json_schemas.py
→ Exported 12 JSON Schemas (P0 frozen set, unchanged)
.venv/bin/python -m pytest tests/contracts/test_json_schema_exports.py -q
→ 48 passed (12 objects × 4 contract checks)
```

### 4.4 Full regression (Step 10)
```
.venv/bin/python -m pytest tests -q -p no:cacheprovider -ra
→ 371 passed in 0.42s (P0 290 + P1 81)
.venv/bin/python scripts/run_p0_gate.py
→ 10/10 passed, READY_FOR_CHATGPT_AUDIT
```

Zero fail / error / skip / xfail / xpass.

## 5. P0 immutability evidence

- P0 contract tests: 290 passed (unchanged from baseline)
- P0 Gate: 10/10 passed (unchanged)
- P0 schema files NOT modified: `evidence.py`, `mapping.py`, `lineage.py`,
  `ledger.py`, `common.py`, `candidate.py`, `result.py`, `hypothesis.py`,
  `errors.py`
- JSON schema exports: same 12 frozen objects, freshness test green

## 6. Deviations

1. **JSON schema export scope (brief Step 9 vs Interfaces)**: brief Step 9
   says "确认含 P1 新对象" (confirm P1 new objects included), but Interfaces
   and the closing constraint say "schemas/json/ 导出仅冻结对象" (frozen
   objects only) + "不得把仍在探索的内部对象全部导出为公共 schema". The P1
   entities are still evolving (T3-T6 will consume them), so per the
   frozen-only constraint, `export_json_schemas.py` was NOT modified and P1
   entities are NOT exported to `schemas/json/`. The 12 P0 frozen exports
   remain fresh. This follows the worklog rule: when brief conflicts with
   P0 reality/constraints, the constraint wins.

2. **`NormalizedReactionRecord.provenance` typed as `object | None`**: to
   avoid an import cycle (`p1_entities` → `provenance` → `schemas.common` →
   ...), the field is typed `object | None` rather than
   `SourceRecordProvenance | None`. The runtime accepts a real
   `SourceRecordProvenance` instance (verified by
   `test_normalized_reaction_record_raw_and_provenance`). A future task may
   tighten this with a forward ref or protocol if needed.

3. **Test `test_eligibility_decision_string_value_accepted` removed**: under
   `StrictModel(strict=True)`, a `str`-subclassed `Enum` field rejects bare
   strings (`is_instance_of` error). The test expected string acceptance,
   which contradicts strict-mode semantics. Replaced with
   `test_eligibility_decision_quarantine_value` which passes an enum member.
   This is consistent with P0 enum field behavior.

## 7. Concerns / notes for downstream tasks

- **T3** consumes `NormalizedReactionRecord` + `ResolvedTransformedLineage`
  for legacy audit replay — both are ready.
- **T4** consumes `NormalizedReactionRecord(reaction_id, normalized_reaction,
  source_record_id)` — minimal constructor verified.
- **T5** consumes `DonorEligibilityAssessment` (returned by
  `assess_donor_eligibility`) — 4-value Literal is ready.
- **T6** consumes `ResolvedTransformedLineage` + `LineageEdge`/`LineageResolution`
  (P0) — ready.
- `EligibilityDecision` and `SnapshotRecord`/`SnapshotManifest` are defined
  but not yet consumed by an implementation task until T9/T10 (snapshot build).

## 8. Next task authorization

T2 exit criteria met:
- P1 new object set complete (8 entities in `p1_entities.py`)
- All inherit `StrictModel`, `extra="forbid"`, zero `FORBIDDEN_FIELD_NAMES`
- P0 baseline unchanged (290 + Gate 10/10)
- JSON schema freshness green
- Zero fail/error/skip/xfail/xpass

**T3 authorized.**
