# SUBMISSION TO CHATGPT — P1 Round 3 Read-Only Audit

> **Scope:** Response to `CHATGPT_P1_REMEDIATION_PROMPT_ROUND_3.md`
> (Round 2 verdict: `REJECTED_REMEDIATION_REQUIRED`, Critical-1 + Critical-2).
> **Nature of this document:** evidence package for a read-only re-audit.
> It does **not** claim P1 acceptance. All numbers below come from actual runs
> in the current working tree.

---

## 0. Cover summary (§12.3)

| # | Item | Value |
|---|------|-------|
| 1 | branch | `main` |
| 2 | HEAD | `4eb463368e38f2faa3d3656a05974c4b1c1211a6` (`4eb4633`) |
| 3 | working-tree | dirty (uncommitted P1 remediation; no commit performed) |
| 5 | tests/contracts | **290 passed**, 0 fail/error/skip/xfail |
| 6 | tests/p1 | **415 passed**, 0 fail/error/skip/xfail |
| 7 | full tests | **705 passed**, 0 fail/error/skip/xfail |
| 8 | P0 Gate | **10/10 PASS** — `READY_FOR_CHATGPT_AUDIT` |
| 9 | P1 Gate | **7/10 PASS, 3 BLOCKED** (G03/G04/G10) — `BLOCKED` |
| 10 | M1–M41 | **41/41 caught** |
| 28 | dependency install / network | **none this round** (see §11) |
| 30 | P2 status | **BLOCKED** pending ChatGPT read-only re-audit |

- Python: `3.11.15`
- Evidence timestamp (UTC): `2026-07-31T03:18Z`

---

## 1. Round 3 findings addressed

### Critical-1 — Snapshot was a lossy projection (hash did not cover complete evidence)
Round 2 froze a hand-picked whitelist, so many scientific/audit fields could be
mutated without changing the snapshot/record hash, and the complete decision /
quarantine record could not be replayed from the snapshot. Two source ledgers
(embedded `ReactionEvidence.source_reaction_ledger` vs external
`SnapshotEvidenceItem.source_ledger`) could silently disagree.

### Critical-2 — Unreliable / contradictory mapping + lineage still reached `strict_eligible`
Round 2's `_validate_strict_preconditions` accepted records whose formal mapping
did not support the resolved lineage, whose lineage was unresolved/partial, whose
mapping pairs referenced unknown participants/atom-maps or the wrong side, and the
`2OG→hydroxyproline` class (two reactants competing for one transformed product).

---

## 2. Critical-1 fix — complete-evidence canonical content

**Root cause:** hash payload was a curated subset, and builder/writer/loader did
not share one object; dual ledger authority was unresolved.

**Fix (single canonical content, §5.3):** `_canonical_record_payload` now freezes
the **complete typed objects** via `model_dump(mode="json")` and the *same* object
is used by builder-hash, records.jsonl writer, and loader tamper-verification.

Canonical frozen record schema (item 11):

```jsonc
{
  "reaction_evidence":   <complete ReactionEvidence minus EVIDENCE_HASH_EXCLUDED_FIELDS>,
  "source_ledger":       <complete external SourceReactionLedger | null>,
  "resolved_lineages":   [<complete ResolvedTransformedLineage>, ...],
  "eligibility_decision":<complete EligibilityDecision>,
  "quarantine_record":   <complete QuarantineRecord | null>,
  "lane":                "<production|research_diagnostic|quarantine>"
}
```

`reaction_evidence` covers provenance, source_uri_or_citation,
fragment_lineage_graph, ambiguity_sets, transformation_hypotheses, quality_report,
quarantine, participants (+ per-participant provenance), mapping_report (+ formal
mapped pairs), and the embedded source ledger. `eligibility_decision` covers
required_warnings, evidence_ids, research_diagnostic_eligibility, policy_version.

- **Item 12 — runtime/circular exclusions & reason:** the *only* excluded field is
  the centralized `EVIDENCE_HASH_EXCLUDED_FIELDS = {snapshot_id}` (a circular
  back-reference). Timestamp / temp path / run ID are excluded from the payload
  construction itself (§16.6). Exclusions are centralized, explicit, and covered by
  `test_snapshot_id_or_runtime_exclusion_policy_is_explicit`.
- **Item 16 — dual ledger authority:** `_resolve_ledger_authority` (§5.4) makes the
  external `SourceReactionLedger` the eligibility authority; if an embedded ledger
  is also present and disagrees, the builder raises `SnapshotBuildError`
  (fail-closed). Embedded-only likewise raises (authority must be explicit).
- **Item 24 — public API cannot bypass:** `build_snapshot(SnapshotEvidenceItem…)`
  re-runs the strict cross-validator and ledger authority; there is no code path
  that persists a strict record without them
  (`test_public_snapshot_api_cannot_bypass_new_cross_invariants`,
  `test_direct_deserialization_cannot_bypass_strict_boundary`).

**Item 13 — reaction-level mutation hash results** and
**Item 14 — complete decision/quarantine mutation hash results:**
`snapshot_complete_evidence_mutation_results.json` → **10/10 caught** (M18–M21,
M26–M31). Every scientific field change flips the hash.

**Item 15 — loader tamper rejection:** the loader recomputes the canonical hash and
rejects any nested tampering (participant provenance, mapping report, source ledger,
lineage, decision warnings/evidence_ids, quarantine record) — covered by the
`test_loader_rejects_tampered_*` tests.

---

## 3. Critical-2 fix — strict cross-invariants (fail-closed)

**Root cause:** strict preconditions checked fields in isolation, never the
*cross* relationship between formal mapping, resolved lineage, and participants.

**Fix:** `_validate_strict_preconditions` now enforces the full cross-invariant set
before `strict_eligible`; any violation fails closed to a non-strict lane.

**Item 17 — strict cross-invariant list** (each with a `never_strict` test and an
engine mutation):

| Invariant | Item | Test | Mutation |
|-----------|------|------|----------|
| mapped-heavy-atom fraction ≥ threshold | 18 | `test_low_mapped_heavy_atom_fraction_never_strict` | M32 |
| formal assignment ambiguity = False | 19 | `test_ambiguous_formal_assignment_never_strict` | M33 |
| formal assignment high quality / formal_mapped | — | `test_low_quality_formal_assignment_never_strict` | — |
| mapping pair participant exists | 20 | `test_formal_pair_unknown_*_participant_never_strict` | M34 |
| mapping pair correct side | 20 | `test_formal_pair_wrong_participant_side_never_strict` | M36 |
| mapping pair atom-map exists | 20 | `test_formal_pair_unknown_*_atom_map_never_strict` | M35 |
| no contradictory/duplicate pairs | — | `test_contradictory_or_duplicate_mapping_pairs_never_strict` | — |
| lineage resolved (not unresolved/failed/partial) | 21 | `test_unresolved_lineage_never_strict` / `test_failed_lineage_never_strict` / `test_partially_resolved_lineage_never_strict` | M37 |
| identity-relevant partial ambiguity rejected | 21 | `test_partial_identity_ambiguity_never_strict` | M38 |
| lineage supported by formal mapping | 22 | `test_lineage_pair_must_be_supported_by_formal_mapping` / `test_lineage_transformed_maps_must_be_supported_by_mapping` | M39 |
| two reactants → one transformed product | 23 | `test_two_reactants_claiming_same_transformed_product_fail_closed` | M40 |
| forbidden 2OG→hydroxyproline not in snapshot strict | — | `test_forbidden_2og_to_hydroxyproline_cannot_enter_snapshot_strict` | M15/M40 |
| embedded/external ledger mismatch | 16 | `test_embedded_external_ledger_mismatch_never_strict` | M41 |

Direct answers to the cover checklist:
- **18 low mapped fraction rejected from strict:** YES (M32 caught).
- **19 assignment ambiguity rejected from strict:** YES (M33 caught).
- **20 unknown participant / atom-map / wrong-side rejected:** YES (M34/M35/M36 caught).
- **21 unresolved / partial lineage rejected:** YES (M37/M38 caught).
- **22 unsupported lineage rejected:** YES (M39 caught).
- **23 two-reactants-to-one-product rejected:** YES (M40 caught).

**Cross-invariant evidence:** `eligibility_cross_invariant_results.json` →
**10/10 caught** (M32–M41).

---

## 4. Gate wiring (§7)

- **P1-G08** executes the new fail-closed / cross-invariant engine tests
  (`test_eligibility_fail_closed.py`, `test_eligibility_cross_invariants.py`).
- **P1-G09** cross-verifies an **independently rebuilt** snapshot hash against the
  stored hash over complete nested evidence
  (`test_snapshot_complete_evidence.py`, `test_snapshot_nested_evidence.py`);
  stored sample regenerated via `scripts/regenerate_snapshot_sample.py`.
- **Item 26 — G04 mapper/blocker:** still BLOCKED — `RealMapperAdapter.map_reaction()`
  is a skeleton (a scoped follow-up); the gate detects this via a **live probe**, so
  a status-only "COMPLETE" cannot fake a PASS (M12/M13 caught).
- **§5.1 aggregation (M25):** aggregation is now a **single authority**
  `aggregate_gate_status()` in `run_p1_gate.py`; `generate_report` calls it and M25
  calls the *same* function (not a copy). A BLOCKED gate that also has an
  implementation failure is reported as **FAIL**, never masked as BLOCKED.

**Gate false-positive evidence:** `gate_false_positive_mutation_results_round_3.json`
→ **11/11 caught** (M9–M15, M22–M25).

---

## 5. G03 stale `rdkit_absent` refresh (§13.1)

RDKit is installed at runtime (`rdkit 2026.03.4`). The legacy-lineage audit and the
P1 preflight both **probe rdkit at runtime**; regenerating them removed the stale
`rdkit_absent` blocker.

- **Item 25 — G03 current source/blocker:** BLOCKED on
  `real_reaction_source_not_confirmed` + `required_case_missing_proline_2og_source_record`.
  It no longer reports `rdkit_absent`. (The only remaining mention of the token in the
  gate JSON is an explicit deviation note stating rdkit is now available.)

```text
BLOCKED
reason:
  authoritative real reaction source not confirmed;
  required real proline/2OG record not located.
required user input:
  confirm source authority/version/path.
what was safely completed:
  read-only source inventory + structural audit (counts/categories/source_ids/
  examples/hash verified); rdkit runtime confirmed.
what was not fabricated:
  no synthetic row promoted to real source evidence.
```

---

## 6. M1–M41 (item 10)

`reports/p1/mutation_results.json` → **41/41 caught**. Every "caught" is the
mutation triggering its *specific* expected failure (not a pre-existing BLOCKED or
unrelated error). In particular, M16/M17's baseline is now a **genuinely strict**
item, so they are caught by their own failed-mapping / incomplete-source mutation
rather than vacuously.

- M1–M15, M22–M24: gate impl-failure / false-positive rejection.
- M16–M17: incomplete source / failed mapping never strict (fail-closed).
- M18–M21, M26–M31: complete-evidence hash coverage (tamper flips the hash).
- M25: real aggregation authority; BLOCKED never masks impl FAIL.
- M32–M40: strict cross-invariant violations rejected.
- M41: embedded/external ledger disagreement → builder fails closed
  (`SnapshotBuildError`); no strict snapshot produced.

---

## 7. Changed files (item 4)

**Engine / snapshot (source):**
- `reaction_agent/eligibility/engine.py` — strict cross-invariant validator (Critical-2)
- `reaction_agent/snapshot/builder.py` — complete canonical payload + dual-ledger authority (Critical-1)
- `reaction_agent/snapshot/loader.py` — tamper verification over canonical content

**Gate / mutation / evidence tooling:**
- `scripts/run_p1_gate.py` — `aggregate_gate_status` authority, G09 fixtures, refreshed context
- `scripts/run_p1_mutations.py` — M25 fixed, M26–M41 added, `_g08` baseline made genuinely strict
- `scripts/regenerate_snapshot_sample.py` — regenerate stored snapshot sample
- `scripts/generate_round3_evidence.py` *(new)* — derive Round 3 evidence JSONs from real runs

**Tests (new RED → GREEN):**
- `tests/p1/test_eligibility_cross_invariants.py` (20), `test_eligibility_fail_closed.py` (13),
  `test_snapshot_complete_evidence.py` (16), `test_snapshot_nested_evidence.py` (18)
- Updated: `tests/p1/test_eligibility_engine.py`, `tests/p1/test_snapshot_builder.py`

**Regenerated evidence:** `reports/p1/{mutation_results,P1_GATE_REPORT,P1_PREFLIGHT,
snapshot_build_sample}.json/.md`, `reports/data_audit/legacy_lineage_audit.json/.md`,
`reports/p0/P0_GATE_REPORT.*`, and the four Round 3 evidence JSONs (§8).

---

## 8. Structured audit evidence (§12.2)

| File | Result |
|------|--------|
| `reports/p1/P1_ROUND_3_AUDIT_EVIDENCE.json` | roll-up (41/41; P0 10/10; P1 7/10, 3 blocked) |
| `reports/p1/snapshot_complete_evidence_mutation_results.json` | 10/10 (M18–21, 26–31) |
| `reports/p1/eligibility_cross_invariant_results.json` | 10/10 (M32–41) |
| `reports/p1/gate_false_positive_mutation_results_round_3.json` | 11/11 (M9–15, 22–25) |

All are derived from actual execution artifacts; no hand-edited numbers.

---

## 9. External blockers (§13)

### G03 — see §5.

### G04
```text
BLOCKED
reason:
  RealMapperAdapter.map_reaction() remains a skeleton.
required user input:
  authorize/assign real mapper implementation in a separate scoped task,
  or accept G04 remains blocked.
what was safely completed:
  fake/curated mapping contracts and live skeleton detection.
what was not fabricated:
  no fake mapper output presented as real integration.
```

### G10 (item 27)
```text
BLOCKED
reason:
  independent annotator B and independent adjudicator not produced.
required user input:
  separate independent annotation/adjudication resources.
what was safely completed:
  protocol/schema/threshold checks.
what was not fabricated:
  no duplicated annotation presented as independent review.
```

---

## 10. Assumptions / deviations (item 29)

- Execution model: ChatGPT-designed P1 tasks implemented by a coding agent under
  the frozen design/ADRs (unchanged).
- The 4-record snapshot fixtures are synthetic and validate the pipeline contract,
  not real chemistry; no fixture is presented as real evidence.
- rdkit/numpy/networkx/scipy were installed in `.venv` in a **prior** authorized
  round (recorded in the worklog + `requirements.lock.txt`). See §11 for this
  round's dependency/network status.

---

## 11. Dependency install / network (item 28)

```text
No dependency installation performed.
No network access performed.
```

(rdkit being importable is the result of a previously authorized install; this
round only *probed* it read-only to refresh stale G03 evidence.)

---

## 12. Guardrails honored

- Frozen design / ADRs / `tests/contracts/` / `../benchmark/` / `../core/` — not modified.
- No user files deleted, moved, or overwritten.
- P0 contracts (290) and P0 Gate (10/10) — no regression.
- P2 remains BLOCKED.

---

READY_FOR_CHATGPT_P1_ROUND_3_READ_ONLY_AUDIT
P1 SCIENTIFIC GATE BLOCKED — EXTERNAL INPUTS REQUIRED
P2 BLOCKED pending ChatGPT re-audit
