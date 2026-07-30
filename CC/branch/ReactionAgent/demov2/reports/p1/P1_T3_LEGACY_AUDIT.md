# P1-T3: Legacy Lineage Audit — Checkpoint Report

**Task:** P1-T3 Legacy lineage audit (L2 independent, read-only)
**Status:** PARTIAL (P1 Gate = BLOCKED)
**Date:** 2026-07-30
**Execution model:** Claude Code subagent (deviation: original plan specified Qwen — inherited from T0/T1/T2)

## 1. Verdict: `PARTIAL`

The audit verdict is **PARTIAL**. Per task-3-brief §9.8 and the Preflight
BLOCKED status, this is the only honest verdict. The P1 Gate is BLOCKED
pending the missing inputs listed in §5 below.

### Verdict reasons

| # | Reason | Meaning |
|---|--------|---------|
| 1 | `real_reaction_source_not_confirmed` | No RHEA/BRENDA/MetaCyc source confirmed; no env vars set |
| 2 | `rdkit_absent_runtime_unable_to_execute_legacy_transformed_pair` | rdkit absent from `.venv`; legacy `transformed_pair` cannot be executed on any reaction row |
| 3 | `required_case_missing_proline_2og_source_record` | No source record (e.g. RHEA:10280) provided to bind the §9.3 canonical case |

## 2. What the audit DID do (honest, non-fabricated)

Because both the real source and rdkit are unavailable, the audit is a
**read-only static logic audit** of the legacy module — not a real-row
replay. It records:

1. **Legacy module fingerprint** — sha256 `6003f4bc…eb2d0` (matches Preflight
   §2 frozen reference), 8986 bytes, `read_only=True`, `modified_by_audit=False`.
   The sha is re-verified at script exit; any in-place mutation would fail the
   run.
2. **Five §9.4 mismatch categories** with full definitions
   (`cross_lineage_pair`, `cofactor_selected_as_main`, `mapping_missing`,
   `legacy_pair_supported`, `insufficient_evidence`).
3. **Six logic-level risks** inventoried per audited legacy function
   (`pick_main`, `COFACTORS`, `_pick_transformed`, `transformed_pair`,
   `group_key`/`main_substrate`/`main_product`, `canon_smiles`/`canon_frags`).
4. **Real-source availability probe** — rdkit/numpy import check, env-var
   scan, candidate pkl file inventory.
5. **Proline/2OG canonical case** recorded as `required_case_missing`
   (source_record_found=False).

## 3. What the audit did NOT do (§9.8 discipline)

- **Did NOT execute `transformed_pair` on real reaction rows** — rdkit is
  absent, so the legacy code cannot run. No partial/forced execution.
- **Did NOT fabricate examples** — `examples=[]` and `source_ids=[]` when
  verdict is PARTIAL. No fixture data is reported as a real audit.
- **Did NOT modify the legacy module** — `../benchmark/canonical_identity.py`
  and `../core/chenyu_features.py` are read-only; git status confirms
  `benchmark/` and `core/` are untracked and untouched.
- **Did NOT delete failed records or sample only successes** — there are no
  records to filter (zero rows audited), and the discipline is encoded in the
  JSON `discipline_notes` block.

## 4. Counts (§9.5 layered stats)

All counts are 0 because zero real reactions were audited. The denominator
`total_reactions = 0` is the honest partition — not a missing key.

| Category | Count |
|----------|-------|
| total_reactions (denominator) | 0 |
| audited_reactions | 0 |
| cross_lineage_pair | 0 |
| cofactor_selected_as_main | 0 |
| mapping_missing | 0 |
| legacy_pair_supported | 0 |
| insufficient_evidence | 0 |

## 5. Real source status

| Field | Value |
|-------|-------|
| rdkit_available | `False` |
| rdkit_info | `ModuleNotFoundError: No module named 'rdkit'` |
| numpy_available | `False` |
| env_keys_present | `{}` (no REACTION/RHEA/BRENDA/META/DATA_ROOT/ENZYMECAGE_DATA_ROOT set) |
| candidate_rxn_count | 3601 (`/Volumes/CC/Enzyme_Agent/depending/data/rxn2enzyme_positives.pkl`) |
| candidate_proline_keyword_hits | 0 |
| source_confirmed_by_env | `False` |
| real_reaction_source_found | `False` |
| usable_for_legacy_audit | `False` |

**Note on the candidate pkl:** A `rxn2enzyme_positives.pkl` file with 3601
reaction SMILES exists at the chenyu_features default data root. It was
probed (pickle-only, no rdkit) and recorded. It is **not** treated as a
confirmed complete-reaction-record source because:
- It maps reaction SMILES → enzyme lists, not full RHEA/BRENDA/MetaCyc
  records with stoichiometry/participant roles.
- rdkit is absent, so `transformed_pair` cannot be executed on these SMILES.
- A keyword scan found 0 proline-string hits (the §9.3 canonical case is
  absent).
- The user has not confirmed this as the intended T3 source.

## 6. Proline / 2-oxoglutarate case (§9.3)

| Field | Value |
|-------|-------|
| reaction | `2-oxoglutarate + proline + O2 -> succinate + hydroxyproline + CO2` |
| expected_lineages | `proline -> hydroxyproline`, `2-oxoglutarate -> succinate` |
| forbidden_lineage | `2-oxoglutarate -> hydroxyproline` |
| source_record_found | `False` |
| status | `required_case_missing` |

The case definition is encoded; no source record binds it to real data.

## 7. Legacy logic risks (static audit summary)

| Function | Lines | Risk (short) |
|----------|-------|--------------|
| `pick_main` | 60-77 | Size-contest picks cofactor as "main" when no reaction-center signal |
| `COFACTORS` | 96-128 | Exact-SMILES-match only; tautomers/protonation states bypass filter |
| `_pick_transformed` | 131-157 | Silent fallback to size-contest when center=None; not flagged in return |
| `transformed_pair` | 161-185 | Single (X,Y) pair cannot represent parallel lineages (§9.3 case); silent chenyu import degradation |
| `group_key`/`main_substrate`/`main_product` | 188-202 | All delegate to transformed_pair; inherit single-pair limitation; group splitting |
| `canon_smiles`/`canon_frags` | 23-48 | frozenset discards stoichiometry; spectator detection loses count info |

Full definitions in the JSON `legacy_logic_risks` array.

## 8. TDD evidence

- **RED:** `tests/p1/test_legacy_audit_contract.py` → 10 failed (audit JSON
  not generated) before implementation.
- **GREEN:** `tests/p1/test_legacy_audit_contract.py` → 10 passed after
  `scripts/legacy_lineage_audit.py` created.
- **Full suite regression:** 390 passed (290 P0 + 100 P1),
  0 fail/error/skip/xfail/xpass.
- **P0 Gate:** 10/10 passed (READY_FOR_CHATGPT_AUDIT), no regression.

## 9. Artifacts

| Artifact | Path |
|----------|------|
| Audit script | `scripts/legacy_lineage_audit.py` |
| Audit JSON | `reports/data_audit/legacy_lineage_audit.json` |
| Audit MD | `reports/data_audit/legacy_lineage_audit.md` |
| Contract tests | `tests/p1/test_legacy_audit_contract.py` |
| This report | `reports/p1/P1_T3_LEGACY_AUDIT.md` |

## 10. Deviations

1. **Execution model Qwen → Claude Code subagent** (inherited from T0/T1/T2;
   user decision).
2. **Contract test adjusted for PARTIAL (brief Step 6):** `test_proline_2og_included`
   in the brief unconditionally asserts a proline example exists. Per brief
   Step 6 ("若真实 source 缺，则 audit 标 PARTIAL，契约测试对应调整为允许
   PARTIAL 标记，但不得伪造 examples"), the test was replaced with
   `test_proline_2og_case_handled_honestly` which requires EITHER a real
   proline example (when verdict=PASS) OR an explicit `required_case_missing`
   marker (when verdict=PARTIAL). This does not weaken the test — it makes it
   context-aware and adds the §9.8 anti-fabrication guard
   (`test_no_fabricated_examples_when_partial`).
3. **Audit scope = static logic audit only.** The brief's Step 4 says "对每条
   reaction 记录 §9.3 的 audit record 字段". Because rdkit is absent and the
   real source is unconfirmed, there are no reaction rows to record per-row
   fields against. The audit instead records the logic-level risk inventory +
   mismatch category framework + source-status probe, which is the maximal
   honest output under BLOCKED conditions (§9.8).

## 11. What is needed to unblock (T3 → PASS, P1 Gate → unblocked)

1. **Real complete-reaction-record source** — a path/identifier for a
   RHEA/BRENDA/MetaCyc export, or explicit user confirmation that the legacy
   `rxn2enzyme_positives.pkl` (3601 reactions) is the intended T3 source.
2. **rdkit installed in `.venv`** — required to execute
   `transformed_pair`/`main_substrate`/`main_product`/`group_key` on real
   reaction SMILES. Also unblocks T4 (atom mapper) and T6 (lineage graph).
3. **Proline/2OG source record** — e.g. a RHEA ID (RHEA:10280 or equivalent)
   to bind the §9.3 canonical case to a real auditable row.

Once all three are supplied, re-run `scripts/legacy_lineage_audit.py`; the
script's real-audit branch will populate `counts`, `examples`, `source_ids`,
and flip `verdict` to `PASS` (or retain PARTIAL with honest reasons if the
data itself reveals mismatches).

## 12. P0 immutability evidence

- P0 contract tests: 290 passed (unchanged from baseline).
- P0 Gate: 10/10 passed (unchanged).
- `../benchmark/` and `../core/`: untracked, untouched (git status `??`, not `M`).
- P0 schema/contract files: not modified.
- `reports/p0/P0_GATE_REPORT.{json,md}`: regenerated by the P0 Gate runner
  itself (brief Step 7 requires running the gate); no manual edits.
