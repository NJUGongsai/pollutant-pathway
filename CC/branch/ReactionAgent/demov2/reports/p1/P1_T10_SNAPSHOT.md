# P1-T10: Immutable Snapshot Builder

**Task:** P1-T10 — Immutable content-addressed snapshot builder + read-only loader
**Status:** UNIT_CONTRACT_COMPLETE
**Builder version:** `p1-t10-1`
**Date:** 2026-07-30

## 1. Summary

Implemented `build_snapshot(config, evidence_iter) -> SnapshotManifest` in
`reaction_agent/snapshot/builder.py` and `load_snapshot(snapshot_id_or_path,
root=None) -> SnapshotRecord` in `reaction_agent/snapshot/loader.py`. The
builder runs the snapshot finalization pipeline on pre-computed T4-T8
artifacts (ReactionEvidence + SourceReactionLedger + ResolvedTransformedLineage),
runs the T9 eligibility decision to classify each record into one of the four
evaluation lanes (strict / conditional / diagnostic / quarantine), builds the
production / diagnostic / quarantine indices, computes a canonical content
hash, and atomically finalizes the snapshot to
`<output_snapshot_root>/<snapshot_id>/`.

**3 key disciplines enforced:**
1. **Atomicity (§16.4)** — temp dir → verify → `os.rename` (fails if target
   exists) → `complete=true` LAST. Interrupted build leaves no complete
   snapshot. Existing complete immutable snapshot is NEVER overwritten.
2. **Determinism (§16.6)** — same source + same versions + same config →
   identical snapshot hash. timestamp / run ID / temp path / unordered
   iteration are NOT in the canonical content hash. Record hashes are sorted
   before hashing.
3. **Loader read-only (§16.5)** — explicit ID/path required (no auto-latest),
   read-only (never opens for write), verifies manifest hash against recomputed
   content hash, rejects incomplete, rejects hash mismatch, rejects temp dirs.

## 2. Files

| File | Action | Purpose |
|------|--------|---------|
| `reaction_agent/snapshot/__init__.py` | Create | Package init; re-exports public API |
| `reaction_agent/snapshot/builder.py` | Create | Builder: `build_snapshot` + `compute_snapshot_hash` + `SnapshotEvidenceItem` |
| `reaction_agent/snapshot/loader.py` | Create | Loader: `load_snapshot` (read-only, verify hash) |
| `tests/p1/test_snapshot_builder.py` | Create | 22 tests (13 §16.7 + 4 contract + 2 security + 3 manifest) |
| `reports/p1/snapshot_build_sample.json` | Create | Build sample (fixture + real-source-separated) |
| `reports/p1/P1_T10_SNAPSHOT.md` | Create | This report |

## 3. Test results

### 3.1 RED → GREEN

```
RED:  ModuleNotFoundError: No module named 'reaction_agent.snapshot.builder'
      (1 collection error — module did not exist)
GREEN: 22 passed in 0.17s
```

### 3.2 Full regression

```
.venv/bin/python -m pytest tests -q -p no:cacheprovider -ra
589 passed in 0.57s   (baseline 567 + 22 new T10; zero skip/xfail)
```

Breakdown:
- P0 contracts: 290 passed (baseline preserved, no regression)
- P1: 299 passed (277 baseline + 22 new T10)

### 3.3 P0 Gate

```
.venv/bin/python scripts/run_p0_gate.py
Result: 10/10 passed
Status: READY_FOR_CHATGPT_AUDIT
```

No regression. P0 baseline 290 + Gate 10/10 preserved.

## 4. T10 test inventory (22 tests)

### §16.7 required tests (13)

| # | Test | §16.7 item |
|---|------|-----------|
| 1 | `test_deterministic_rebuild_same_hash` | deterministic rebuild same hash |
| 2 | `test_source_change_new_hash` | source change new hash |
| 3 | `test_policy_change_new_hash` | policy change new hash |
| 4 | `test_quarantine_in_manifest` | quarantine in manifest |
| 5 | `test_production_excludes_quarantine` | production excludes quarantine |
| 6 | `test_all_filters_counted` | all filters counted |
| 7 | `test_interrupted_build_not_complete` | interrupted build not complete |
| 8 | `test_hash_mismatch_rejected` | hash mismatch rejected |
| 9 | `test_read_only_load` | read-only load |
| 10 | `test_explicit_snapshot_required` | explicit snapshot required |
| 11 | `test_existing_snapshot_not_overwritten` | existing snapshot not overwritten |
| 12 | `test_input_record_ordering_stability` | input record ordering stability |
| 13 | `test_timestamp_not_in_canonical_hash` | timestamp not in canonical hash |

### Additional contract + security tests (9)

| # | Test | Category |
|---|------|---------|
| 14 | `test_compute_snapshot_hash_no_write` | Hash computation without disk write |
| 15 | `test_manifest_carries_versions_and_counts` | Manifest fields (T2 contract) |
| 16 | `test_on_disk_manifest_has_full_16_3_fields` | §16.3 full manifest fields |
| 17 | `test_load_snapshot_by_path` | Loader accepts explicit path |
| 18 | `test_load_snapshot_rejects_incomplete` | Loader rejects build_status=partial |
| 19 | `test_builder_does_not_mutate_inputs` | Immutability |
| 20 | `test_builder_version` | BUILDER_VERSION defined |
| 21 | `test_hash_mismatch_content_tamper_detected` | H2 fix: content tamper detected |
| 22 | `test_loader_rejects_temp_dir` | M1 fix: temp dirs rejected |

## 5. Determinism evidence (§16.6)

Three independent computations produce the same hash:

```
Build A (write to disk):   snapshot_hash = 21172a43f2d9501902e5d7883cf90fba78ed1b08a9ab3817751092973703edcf
Build B (write to disk):   snapshot_hash = 21172a43f2d9501902e5d7883cf90fba78ed1b08a9ab3817751092973703edcf
Hash-only (no disk write): snapshot_hash = 21172a43f2d9501902e5d7883cf90fba78ed1b08a9ab3817751092973703edcf
```

3-way match: `True`. Snapshot ID: `snap_21172a43f2d9`.

**Canonical content hash payload** (EXCLUDES timestamp/run ID/temp path):
- `schema_version`
- `build_config_hash` (excludes `output_snapshot_root` and `timeout`)
- `versions` (package, mapper, normalization, role_policy, lineage_resolver,
  ledger, eligibility_policy, eligibility_engine, builder)
- `source_content_hashes` (per-source, sorted)
- `record_count`
- `counts` (strict, conditional, diagnostic, quarantine)
- `record_content_hashes` (sorted list of per-record sha256)
- `production_index_hash`
- `quarantine_index_hash`
- `policy_version`

**Excluded from hash** (stored on disk for traceability only):
- `build_id` (run ID)
- `completed_at` (timestamp)
- `builder_version` (in the manifest, but also in canonical content — see below)

Test 13 (`test_timestamp_not_in_canonical_hash`): two builds with different
`build_id` ("run_001" vs "run_002") produce the same `snapshot_hash`. The
`build_id` is stored on disk but is NOT in the canonical content payload.

Test 12 (`test_input_record_ordering_stability`): same items in reversed order
produce the same `snapshot_hash` (record hashes are sorted before hashing).

## 6. Atomicity evidence (§16.4)

**Pipeline order** (builder.py):
1. Materialize `evidence_iter` (iterate once)
2. Run T9 eligibility decision on each item → classify into lane
3. Compute canonical snapshot hash + snapshot_id
4. Check for existing complete snapshot → `SnapshotExistsError` if found
5. Write all artifacts to temp dir (`.tmp_<snapshot_id>`)
6. Write manifest with `build_status="building"` to temp (NOT "complete")
7. Verify all artifacts (read back, check integrity)
8. `os.rename(temp_dir, final_dir)` — fails if target exists (H3 fix)
9. **`complete=true` LAST**: rewrite manifest with `build_status="complete"`
   + write COMPLETE marker in the final dir

**Interrupted build** (Test 7): iterator raises mid-iteration →
`SnapshotBuildError` → temp dir cleaned up → no final snapshot exists → loader
rejects. If interrupted between step 8 and 9 (rename succeeded, complete not
yet written): final dir has `build_status="building"` and no COMPLETE marker →
loader rejects (build_status != complete + marker missing) → next build removes
stale dir and rebuilds.

**Existing snapshot not overwritten** (Test 11): rebuild with same config +
same content → `SnapshotExistsError` raised → manifest file mtime unchanged →
content unchanged.

## 7. Loader read-only evidence (§16.5)

**Read-only** (Test 9): loader opens all files with default mode `"r"` (never
`"w"` or `"a"`). File sizes and mtimes are identical before and after load.

**Hash verification** (Tests 8, 21):
- Test 8: tampered production_index (extra record without
  `record_content_hash`) → `SnapshotHashMismatchError`
- Test 21 (H2 fix): tampered record content (modified `normalized_reaction`
  but kept stored `record_content_hash`) → loader recomputes per-record hash
  from fields → mismatch detected → `SnapshotHashMismatchError`

**Explicit snapshot required** (Test 10): empty string, None, nonexistent ID
all rejected. No auto-latest selection. Two snapshots built → loader does NOT
pick "latest"; requires explicit ID.

**Rejects incomplete** (Test 18): manually-created manifest with
`build_status="partial"` → `SnapshotIncompleteError`.

**Rejects temp dirs** (Test 22, M1 fix): `.tmp_*` directories rejected as
snapshots.

## 8. Real vs fixture snapshot separation

**Fixture snapshots** (used in all tests + sample):
- `source_name = "fixture_source_a"` / `"fixture_source_b"`
- Synthetic `ReactionEvidence` + `SourceReactionLedger` +
  `ResolvedTransformedLineage` constructed in test helpers
- No real chemical data; no rdkit dependency
- Clearly labeled in `snapshot_build_sample.json` under `fixture_snapshot`

**Real source snapshots** (blocked):
- `source_name = "<real_db_name>"` (e.g., `"brenda"`, `"rhea"`)
- Requires rdkit for T4 (atom mapping), T6 (lineage), T7 (source ledger
  balance computation)
- Builder API is ready — accepts pre-computed T4-T8 artifacts. When rdkit
  becomes available, the same `build_snapshot(config, evidence_iter)` call
  will produce real source snapshots from real `ReactionEvidence` records.
- No real data fabricated. Clearly labeled in `snapshot_build_sample.json`
  under `real_source_snapshot` with `status: "BLOCKED"`.

## 9. L2 security review (Step 5)

Security-reviewer audited `builder.py` and `loader.py` for atomicity and
read-only contracts. **No CRITICAL issues.** 3 HIGH issues found and fixed:

| ID | Issue | Fix |
|----|-------|-----|
| H1 | `build_status="complete"` written to temp BEFORE `os.replace` — interrupted build could leave complete-looking temp dir | Manifest written with `build_status="building"` to temp; `complete=true` + COMPLETE marker written AFTER `os.rename` succeeds in final dir |
| H2 | Loader trusted stored `record_content_hash` — content tamper (modify fields, keep hash) undetected | Loader recomputes each record's hash from its fields and compares with stored value before aggregating |
| H3 | TOCTOU between existing-snapshot check and `os.replace` — concurrent build could overwrite | Use `os.rename` (fails if target is non-empty dir) instead of `os.replace`; handle `EEXIST`/`ENOTEMPTY` |

Medium issues fixed:
- M1: Loader rejects `.tmp_*` directories as snapshots (Test 22)
- M4: Removed unused `assert_no_legacy_write` import from loader

Medium issues acknowledged (not blocking):
- M2: Manifest is the trust root for `schema_version`/`build_config_hash`/
  `versions`/`policy_version` (cannot be recomputed from artifacts alone).
  Documented in loader docstring.
- M3: Dead code in path resolution removed (simplified).

## 10. Pipeline (§16.1)

The builder accepts pre-computed T4-T8 artifacts and runs the T9 eligibility
step (which does NOT require rdkit). The full pipeline:

```
source load (evidence_iter yields SnapshotEvidenceItem)
→ raw preserve (ReactionEvidence.raw_reaction)
→ normalize (ReactionEvidence.normalized_reaction)
→ mapping (T4 MappingReport, pre-computed in evidence)
→ roles (T5 RoleAssignment, pre-computed in ledger)
→ lineage (T6 ResolvedTransformedLineage, pre-computed in item.lineages)
→ ledger (T7 SourceReactionLedger, pre-computed in item.source_ledger)
→ eligibility (T9 decide_eligibility — RUN by builder)
→ production/diagnostic/quarantine (lane classification)
→ manifest (§16.3 full on-disk manifest)
→ hash (canonical content hash, §16.6)
→ atomic finalize (§16.4)
```

## 11. Deviations / concerns

1. **`completed_at` uses wall-clock UTC** — not deterministic, but correctly
   excluded from the canonical content hash. Two builds at different times
   produce the same `snapshot_hash` (Test 13).

2. **`build_id` defaults to a deterministic value** based on
   `builder_version` + `random_seed`. This is for traceability only and is
   NOT in the canonical content hash. Callers can override with an explicit
   `build_id` (also excluded from hash).

3. **Manifest trust root (M2)**: `schema_version`, `build_config_hash`,
   `versions`, and `policy_version` are stored in `manifest.json` and used as
   inputs to the recomputed hash. An attacker who tampers both these fields
   and `snapshot_hash` simultaneously could bypass verification. This is a
   design limitation (these fields cannot be recomputed from artifacts alone).
  Mitigation: the COMPLETE marker file stores the `snapshot_hash` independently,
   providing a second source for cross-verification.

4. **Per-record hash verification (H2)**: the loader recomputes each record's
   content hash from its fields. This catches content tampering even when the
   stored `record_content_hash` is left unchanged. The recomputation payload
   matches the builder's `_record_content_hash` exactly.

5. **`_source_content_hash` calls `decide_eligibility` twice** (once in
   `_classify_all`, once in `_source_content_hash`). This is a performance
   concern (L3), not a correctness concern — the decisions are deterministic.
   Can be optimized by caching in a future refactor.

6. **Preflight BLOCKED (rdkit absent)**: the builder does NOT require rdkit.
  It accepts pre-computed T4-T8 artifacts. Real source snapshots require rdkit
  for T4/T6/T7 and are clearly separated from fixture snapshots. Zero-skip.

## 12. Verdict

**UNIT_CONTRACT_COMPLETE.** All 13 §16.7 tests pass + 9 additional contract/
security tests. Determinism proven (3-way hash match). Atomicity enforced
(complete=true LAST, `os.rename`, no overwrite). Loader read-only (verified by
mtime check). L2 security review: 0 CRITICAL, 3 HIGH fixed, 2 MEDIUM fixed.
P0 baseline 290 + Gate 10/10 preserved.
