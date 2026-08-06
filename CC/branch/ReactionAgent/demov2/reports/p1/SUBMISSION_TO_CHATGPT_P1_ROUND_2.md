# Submission to ChatGPT — P1 Round 2 Read-Only Audit

> **Source task:** `CHATGPT_P1_REMEDIATION_PROMPT_ROUND_2.md`
> **Project root:** `/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2`
> **Date:** 2026-07-31
> **Prior verdict:** `REJECTED_REMEDIATION_REQUIRED`
> **Authorization boundary:** P1 remediation only. P2 BLOCKED. No frozen design/ADR modified.

---

## 0. Status cover (§11 — distinguished statuses)

| Status dimension | Result |
|---|---|
| Implementation remediation status | **COMPLETE** — Critical-1/2/3 fixed, 31 new tests, 25/25 mutations caught |
| Real source status | **BLOCKED** — not confirmed by user (§7.1); pickles inspected read-only, not promoted |
| Real mapper status | **BLOCKED** — rdkit installed + available, `RealMapperAdapter.map_reaction()` still skeleton |
| Real proline/2OG status | **BLOCKED** — source record missing; not in candidate pickle (0 keyword hits) |
| Manual audit status | **BLOCKED** — no independent second annotator (single LLM session) |
| Scientific Gate status | **BLOCKED** — 7/10 PASS, 3/10 BLOCKED, 0 FAIL |
| P2 status | **BLOCKED** pending ChatGPT re-audit |

---

## 1. Commit / working tree state (§12 item 1)

- Branch: `main`
- HEAD: `4eb4633 fix(p1): final review fix — EligibilityDecision §15.2 fields + ledger line numbers`
- Working tree: unmodified pre-existing user changes (`main.py`, `.env.example`,
  `.gitignore`, P0/P1 report JSON/MD) left untouched. New/modified files in this
  round listed in §3.
- No `git add/commit/push/reset/clean` performed (per §2.1).

## 2–5. Test statistics (§12 items 2–5)

| Suite | Collected | Passed | Failed | Errors | Skipped | Xfailed | Xpassed |
|---|---|---|---|---|---|---|---|
| `tests/contracts` | 290 | 290 | 0 | 0 | 0 | 0 | 0 |
| `tests/p1` | 379 | 379 | 0 | 0 | 0 | 0 | 0 |
| `tests` (full) | 669 | 669 | 0 | 0 | 0 | 0 | 0 |

- **P0 Gate (item 3):** 10/10 PASS — `READY_FOR_CHATGPT_AUDIT`. No regression.
- **P1 tests (item 4/5):** 379 passed, zero fail/error/skip/xfail/xpass.

## 3. Changed files (this round)

**Implementation:**
- `reaction_agent/snapshot/builder.py` — Critical-1: `_canonical_record_payload`
  covers complete nested evidence; `_record_content_hash` / `_record_to_jsonl`
  / `_source_content_hash` / `_ClassifiedRecord` updated.
- `reaction_agent/snapshot/loader.py` — Critical-1: `_recompute_record_hash`
  strips meta fields + recomputes from full content; index integrity check
  (dangling refs / lane mismatch / hash mismatch).
- `reaction_agent/eligibility/engine.py` — Critical-2: `_validate_strict_preconditions`
  (14 cross-invariants); `_classify_state` returns `(state, strict_detail)`.
- `scripts/run_p1_gate.py` — Critical-3: `_result` + `run_all` §5.1 status model;
  G03/G04/G06/G08/G09/G10 rewritten per §5.2–§5.7.
- `scripts/run_p1_mutations.py` — M9–M25 added (17 new mutations).
- `scripts/regenerate_snapshot_sample.py` — new helper to refresh G09 evidence.
- `requirements.lock.txt` — rdkit/numpy/networkx/scipy + pillow added.

**Tests:**
- `tests/p1/test_snapshot_nested_evidence.py` — new, 18 tests (Critical-1).
- `tests/p1/test_eligibility_fail_closed.py` — new, 13 tests (Critical-2).
- `tests/p1/test_snapshot_builder.py`, `tests/p1/test_eligibility_engine.py` —
  fixtures updated to attach compliant mapping_report (§4.2 preconditions).

**Evidence (regenerated):**
- `reports/p1/snapshot_build_sample.json` — G09 stored hash refreshed to new
  algorithm + fixture (`4e886ca2...`).
- `reports/p1/mutation_results.json` — 25/25 caught.
- `reports/p1/P1_GATE_REPORT.{md,json}` — final gate output.
- `reports/p1/P1_REMEDIATION_WORKLOG.md` — Round 2 appended.
- `reports/p1/P1_ROUND_2_AUDIT_EVIDENCE.json` — new (§11 suggested).
- `reports/p1/snapshot_nested_mutation_results.json` — new.
- `reports/p1/eligibility_fail_closed_results.json` — new.
- `reports/p1/gate_false_positive_mutation_results.json` — new.

**NOT modified (§2.2):** `plan/final_design.md`, `plan/final_plan.md`, ADRs,
`tests/contracts/`, `../benchmark/`, `../core/`, legacy sources.

---

## 4. Snapshot complete record payload schema (§12 item 6)

`_canonical_record_payload` (builder.py) — the ONE object used for record hash,
records.jsonl persistence, and loader tamper verification (§3.2):

```text
{
  reaction_id, source_record_id, source_name, source_version,
  raw_reaction, normalized_reaction, direction,
  participants: [ {participant_id, molecule_id, canonical_smiles, side,
      stoichiometry, formal_charge, atom_map_numbers, mapped_fraction,
      changed_atom_fraction, role_hypotheses, donor_eligibility, provenance} ],
  mapping_report: {mapper_name, mapper_version, mapper_parameters, input_hash,
      output_hash, mapping_status, mapped_heavy_atom_fraction,
      map_number_uniqueness, changed_atom_coverage,
      formal_mapped_source_assignment: {mapper_name, mapper_version,
          mapped_atom_pairs: [{reactant_participant_id, reactant_atom_map,
              product_participant_id, product_atom_map}],
          assignment_method, assignment_quality, assignment_ambiguity},
      mechanistic_atom_origin | null, fallback_method | null,
      symmetry_ambiguity, resonance_tautomer_ambiguity, quality_flags},
  source_ledger: {ledger_id, reaction_evidence_id, reactant_entries,
      product_entries, role_assignments, stoichiometry,
      formal_atom_transfer_assignments, mechanistic_origin_evidence,
      added_atom_sources, removed_atom_sinks, element_balance, charge_balance,
      hydrogen_policy, proton_policy, electron_policy, cofactor_changes,
      source_completeness, mapping_completeness, balance_status, unknowns,
      evidence_ids} | null,
  resolved_lineages: [ {lineage_id, reactant_participant_id,
      product_participant_id, evidence_ids, ambiguity, transformed_atom_maps,
      resolution_quality} ],
  decision_id, eligibility, evaluation_bucket, quarantine_behavior, reason,
  quarantine_record_id | null
}
```
Meta fields stored alongside but NOT hashed: `lane`, `record_content_hash`,
`quarantine_reason` (loader strips these before recompute).

## 5. Snapshot hash coverage (§12 items 7–11)

| Nested evidence (§12 item) | Mutation changes hash? | Loader rejects tamper? |
|---|---|---|
| participant (item 7) | YES | YES |
| participant provenance (item 7) | YES | YES |
| mapping report (item 8) | YES | YES |
| mapping pair (item 8) | YES | YES |
| source ledger (item 9) | YES | YES |
| lineage (item 10) | YES | YES |
| transformed atom maps (item 10) | YES | YES |
| lineage evidence IDs (item 10) | YES | YES |

Loader rejects all four nested tamper classes (item 12): participant /
mapping_report / source_ledger / lineage — verified by
`test_loader_rejects_tampered_*` (4 tests). Plus index integrity: dangling
reaction_id → rejected; lane mismatch → rejected.

## 6. Strict boundary (§12 items 13–15)

| Bad input (item) | Enters strict? |
|---|---|
| incomplete source (13) | NO — fail-closed |
| failed mapping (14) | NO |
| partial mapping (14) | NO |
| unmapped (14) | NO |
| MCS fallback (15) | NO |
| center_pair fallback (15) | NO |
| missing mapping_report (14) | NO |
| ledger/reaction id mismatch | NO |
| unknown lineage participant | NO |
| contradictory balance+mapping | NO |

Direct deserialization cannot bypass (item 15): `SnapshotEvidenceItem` with bad
ledger → lane != strict (verified by `test_direct_deserialization_cannot_bypass_strict_boundary`).

## 7. Gate false-positive mutations (§12 items 16–21)

| Mutation | Caught? | How |
|---|---|---|
| M9 G03 zero-record fake COMPLETE (16) | YES | impl failure: total_reactions=0 |
| M10 G03 empty source_ids (16) | YES | impl failure: source_ids empty |
| M11 G03 hash mismatch | YES | impl failure: hash mismatch |
| M12 G04 status-only promotion (17) | YES | live probe BLOCKED (no fake PASS) |
| M13 G04 unavailable+COMPLETE | YES | not PASS (contradictory JSON rejected) |
| M14 G06 missing proline (18) | YES | impl failure: proline missing |
| M15 G06 forbidden 2OG→hydroxyproline (19) | YES | impl failure: forbidden pairing |
| M22 G10 null annotation files (20) | YES | impl failure: null files |
| M23 G10 same annotator ID | YES | impl failure: non-independent |
| M24 G10 missing adjudication | YES | impl failure: adjudication missing |
| M25 blocked+impl failure (21) | YES | reported as FAIL not BLOCKED |

## 8. Real source / mapper / manual audit (§12 items 22–24)

**Item 22 — real source manifest/hash:** BLOCKED. No real source confirmed.
Read-only pickle inspection (§7.1):
- `rxn2enzyme_positives.pkl` (3.1 MB): `dict[reaction_smiles → list[(uniprot_id, ec_number)]]`,
  3601 atom-mapped reactions. Training positives only (no negatives). No source
  version/authority field. **Not promoted** — awaiting user confirmation.
- `reacting_center.pkl` (4.5 MB): `dict[reaction_smiles → tuple[list[atom_indices]]]`,
  4541 reactions. DERIVED feature (reacting-center atom indices), NOT ground
  truth. Per final_design §8.1 cannot be called complete atom mapping; leakage
  risk. **Not promoted.**

**Item 23 — real mapper backend/version/parameters:** BLOCKED. rdkit 2026.3.4,
numpy 2.4.6, networkx 3.6.1, scipy 1.17.1 installed in `.venv` (user-authorized).
`RealMapperAdapter(backend="rdkit").is_available()` = True (live probe).
`map_reaction()` still raises NotImplementedError (skeleton) → G04 BLOCKED.

**Item 24 — manual audit A/B/adjudication/agreement/catastrophic:** BLOCKED.
annotator_a/b/adjudication = NOT_PRODUCED. catastrophic_error_count = null.
No independent second annotator available in single LLM session. No fabricated
annotations.

## 9. P2 status (§12 item 25)

**P2 BLOCKED** pending ChatGPT P1 Round 2 re-audit.

---

## 10. Blocked items (§12 — for still-blocked items)

### Real source
```text
BLOCKED
reason: real reaction source not confirmed by user; candidate pickles inspected
        read-only but not promoted (training-derived / derived feature / no
        authority); proline/2OG source record missing (0 keyword hits)
required user input: confirm authoritative reaction source (with version +
        authority + source_record_id) OR explicitly authorize
        rxn2enzyme_positives.pkl as P1 source authority
what was safely completed: legacy audit structural integrity verified
        (counts/categories/source_ids/examples/legacy hash); G03 catches
        fake-COMPLETE mutations M9-M11
```

### Real mapper
```text
BLOCKED
reason: RealMapperAdapter.map_reaction() is a skeleton — rdkit installed and
        is_available()=True (live probe), but real mapping not wired
required user input: authorize implementation of real rdkit atom mapping in
        RealMapperAdapter._do_map (P2-scale) OR accept G04 BLOCKED
what was safely completed: rdkit/numpy/networkx/scipy installed in .venv,
        lock updated; FakeAtomMapper unit contract verified (8 quality dims,
        formal≠mechanism, MCS/center not strict); G04 live-probes (no fake PASS)
```

### Manual audit
```text
BLOCKED
reason: no independent second annotator in single LLM session; annotator A/B/
        adjudication NOT_PRODUCED; catastrophic_error_count null
required user input: second independent annotator (human or separate LLM
        session with distinct agent ID, no shared context) + independent
        adjudicator; ideally real source snapshot for sample manifest
what was safely completed: protocol + sample manifest + schema + contract
        tests produced; thresholds frozen H1-H7; no fabricated annotations;
        G10 catches fake-COMPLETE / same-annotator / missing-adjudication
        mutations M22-M24
```

---

## 11. Definition of Done (§14)

- [x] P0 contracts未回归 (290 passed)
- [x] P0 Gate 10/10
- [x] snapshot hash 覆盖完整 participant/mapping/ledger/lineage/provenance
- [x] 修改任一核心嵌套证据都会改变 hash (M18-M21 caught)
- [x] loader 拒绝核心嵌套证据 tampering (4 tamper tests)
- [x] 完整 evidence 可从 snapshot 审计/重放 (records.jsonl persists full payload)
- [x] incomplete source 不进入 strict
- [x] failed/partial/unmapped mapping 不进入 strict
- [x] MCS/center fallback 不进入 strict
- [x] ledger/evidence/lineage reference 全部验证
- [x] G03 零记录假 COMPLETE 不能通过 (M9)
- [x] G04 status-only promotion 不能通过 (M12)
- [x] G06 缺 proline case 不能通过 (M14)
- [x] G06 forbidden 2OG→hydroxyproline 不能通过 (M15)
- [x] G10 没有真实 A/B/adjudication 文件不能通过 (M22)
- [x] BLOCKED 不再覆盖 implementation FAIL (M25)
- [x] M1–M25 全部按正确语义 caught (25/25)
- [x] 全部 tests 零 fail/error/skip/xfail/xpass (669 passed)
- [x] 未用 fixture 冒充 real evidence
- [x] 未修改冻结设计/ADR 迁就实现
- [x] 未写 legacy source
- [x] 未删除或覆盖用户文件
- [x] 未经授权未安装依赖、未联网 (rdkit installed WITH authorization)
- [x] 提交统计与当前 HEAD 完全一致 (no git operations performed)
- [x] P2 保持 BLOCKED，等待 ChatGPT 复审

---

## 12. Conclusion (§13.1)

```text
READY_FOR_CHATGPT_P1_REMEDIATION_READ_ONLY_AUDIT
P1 SCIENTIFIC GATE BLOCKED — EXTERNAL INPUTS REQUIRED
P2 BLOCKED pending ChatGPT re-audit
```

Implementation remediation complete (Critical-1/2/3 fixed, 31 new tests, 25/25
mutations caught, 669 tests green, P0 10/10). Scientific Gate remains BLOCKED
on three external inputs that cannot be fabricated: (1) user-confirmed real
reaction source, (2) real mapper implementation, (3) independent second
annotator. Final acceptance belongs to ChatGPT read-only audit.
