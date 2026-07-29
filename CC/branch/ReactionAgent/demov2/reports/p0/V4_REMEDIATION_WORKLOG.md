# V4 Remediation Worklog — Fail-Closed Context Validation

> **Task:** P0-G03 fail-closed remediation (round 4)
> **Working directory:** `/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2`
> **Scope:** Convert hypothesis/context validation from fail-open skip-when-absent ("validate only when context provided") to fail-closed ("missing relation evidence is a rejection") on the production acceptance path.
> **Status:** READY_FOR_CHATGPT_ROUND_4_AUDIT
> **P1:** BLOCKED pending ChatGPT audit

This worklog follows spec §11.3. All command outputs below were re-captured fresh on 2026-07-29 by Task 4 (read-only runs; no implementation or tests were changed by this task).

---

## 1. Baseline (OLD-state round-3 starting point)

Captured verbatim by Task 1 BEFORE any implementation change. This was the round-3 starting point that ChatGPT rejected: the gate was green but G03 was a false positive (fail-open behavior was accepted).

### Contract tests (OLD)
```
$ PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest tests/contracts -q -p no:cacheprovider -ra
270 passed in 0.38s
```

### Reproduce script (OLD — 8 original false positives)
```
$ PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/reproduce_v3_false_positives.py
======================================================================
V3 Remediation: 8 False Positives — post-remediation verification
======================================================================
  site_transform_mismatch                       REJECTED (UnknownReferenceError)
  target_not_in_query                           REJECTED (UnknownReferenceError)
  unknown_source_ledger_reference               REJECTED (UnknownReferenceError)
  donor_context_not_assumption                  REJECTED (ValidationError)
  qualitative_confidence_note                   REJECTED (ValidationError)
  self_bond_target                              REJECTED (ValidationError)
  mechanistic_evidence_mismatch                 REJECTED (ValidationError)
  formal_assignment_method_mismatch             REJECTED (ValidationError)

ACCEPTED: 0/8
REJECTED: 8/8

STATUS: all 8 false positives eliminated — remediation successful
```

### P0 gate (OLD — G03 was a false positive)
```
$ .venv/bin/python scripts/run_p0_gate.py
============================================================
P0 GATE v3 — Strict Contract Freeze Verification
============================================================

  ✅ PASS  P0-G01: Six ADRs complete and approved
  ✅ PASS  P0-G02: Authority consistency (README + ADR-0001)
  ✅ PASS  P0-G03: Hypothesis lanes + relation validation
  ✅ PASS  P0-G04: Dual ledger boundary
  ✅ PASS  P0-G05: Eligibility policy + ADR drift check
  ✅ PASS  P0-G06: Mapping/mechanism consistency
  ✅ PASS  P0-G07: Decision state machine + recursive forbidden scan
  ✅ PASS  P0-G08: MCP side-effect policy
  ✅ PASS  P0-G09: Legacy metrics provisional
  ✅ PASS  P0-G10: Contract tests + JSON freshness + env

Result: 10/10 passed
Status: READY_FOR_CHATGPT_AUDIT
```

**Baseline interpretation:** 270 contracts pass, 8/8 reproduce REJECTED, gate 10/10 — but G03 was a false positive because the 15 new fail-open negatives (Task 1) were all ACCEPTED on this OLD implementation. This is the round-3 starting point.

---

## 2. RED phase — 15 new negatives RED on OLD implementation

**File created (Task 1):** `tests/contracts/test_v4_fail_closed_context.py` (20 tests: 15 negatives + 5 positives)

**RED command (on OLD / unchanged implementation):**
```
$ PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest tests/contracts/test_v4_fail_closed_context.py -q -p no:cacheprovider -ra
15 failed, 5 passed in 0.17s
```

### Per-case RED outcome and mechanism

| # | Test | RED outcome | RED mechanism |
|---|------|-------------|---------------|
| Neg 1 | `test_all_ids_exist_but_relation_maps_empty` | RED ✗ | `Failed: DID NOT RAISE UnknownReferenceError` — OLD skips relation checks when maps empty → ACCEPTS |
| Neg 2 | `test_relation_maps_present_but_site_uncovered` | RED ✗ | `Failed: DID NOT RAISE` — `if sid in registry.site_to_transformation_id:` skip on uncovered site → ACCEPTS |
| Neg 3 | `test_relation_maps_present_but_transformation_uncovered` | RED ✗ | `Failed: DID NOT RAISE` — `if tid in ...:` skip on uncovered transformation → ACCEPTS |
| Neg 4 | `test_cited_lineage_has_no_lineage_to_reaction_mapping` | RED ✗ | `Failed: DID NOT RAISE` — `if lid in registry.lineage_to_reaction_id:` skip on unmapped lineage → ACCEPTS |
| Neg 5 | `test_production_support_reactions_empty` | RED ✗ | `AssertionError: Regex pattern did not match` — OLD raises a different relation error whose message lacks "empty" |
| Neg 6 | `test_production_support_lineages_empty` | RED ✗ | `AssertionError: Regex pattern did not match` — OLD raises a different relation error whose message lacks "empty" |
| Neg 7 | `test_agent_target_present_but_query_context_not_provided` | RED ✗ | `pydantic_core.ValidationError` at context construction (OLD field is `frozenset` not `None`-able) — not `UnknownReferenceError` |
| Neg 8 | `test_bond_target_present_but_query_bond_pairs_none` | RED ✗ | `pydantic_core.ValidationError` at context construction — not `UnknownReferenceError` |
| Neg 9 | `test_bond_target_endpoint_not_in_query_atoms` | RED ✗ | `Failed: DID NOT RAISE` — OLD checks only bond *pair* membership, not *endpoint* atom membership → ACCEPTS |
| Neg 10 | `test_relaxation_non_empty_but_policy_null` | RED ✗ | `Failed: DID NOT RAISE` — OLD relaxation block is fail-open (skips when policy null) → ACCEPTS |
| Neg 11 | `test_policy_non_empty_but_not_covered_by_map` | RED ✗ | `Failed: DID NOT RAISE` — OLD does not require policy→map coverage → ACCEPTS |
| Neg 12 | `test_registry_site_map_value_not_in_transformation_ids` | RED ✗ | `Failed: DID NOT RAISE ValidationError` — OLD registry has no `model_validator` → construction succeeds with self-contradicting map |
| Neg 13 | `test_registry_transformation_map_references_unknown_lineage` | RED ✗ | `Failed: DID NOT RAISE ValidationError` — same: no registry internal-consistency validator |
| Neg 14 | `test_registry_lineage_map_references_unknown_reaction` | RED ✗ | `Failed: DID NOT RAISE ValidationError` — same |
| Neg 15 | `test_registry_relaxation_policy_map_references_unknown_relaxation` | RED ✗ | `Failed: DID NOT RAISE ValidationError` — same |
| P1 | `test_full_production_selection_accepted` | GREEN ✓ | OLD ACCEPTS the legal hypothesis (positive guard) |
| P2 | `test_legal_atom_target_accepted` | GREEN ✓ | OLD ACCEPTS |
| P3 | `test_legal_bond_target_accepted` | GREEN ✓ | OLD ACCEPTS |
| P4 | `test_explicit_empty_bond_set_accepted` | GREEN ✓ | OLD ACCEPTS (cannot distinguish omitted vs explicit-empty, but this positive uses explicit-empty which OLD accepts) |
| P5 | `test_legal_relaxation_accepted` | GREEN ✓ | OLD ACCEPTS |

**Result: 15 negatives RED, 5 positives GREEN — exactly as required by TDD.**

RED mechanism summary (three failure shapes):
- **No-raise (Neg 1, 2, 3, 4, 9, 10, 11, 12, 13, 14, 15):** OLD validator is fail-open — when a relation map / policy / query context is absent or empty, OLD skips the check and ACCEPTS, so `pytest.raises(UnknownReferenceError|ValidationError)` sees no exception.
- **Message-mismatch (Neg 5, 6):** OLD does raise `UnknownReferenceError`, but for a different reason (a downstream relation check fires on the fully-consistent P1 registry), and the message lacks the substring "empty" that the NEW test's `match=` regex requires. Still RED.
- **Construction-ValidationError (Neg 7, 8):** OLD `HypothesisValidationContext` schema declares `query_atom_ids: frozenset[int] = frozenset()` (not `| None`), so passing `None` raises `ValidationError` at context construction inside the `with pytest.raises(UnknownReferenceError)` block; the wrong exception type propagates. Still RED.

Reference: full per-case detail in `.superpowers/sdd/p0-v4-fail-closed/task-1-report.md`.

---

## 3. Root cause — the 4 fail-open points in OLD `hypothesis.py`

The OLD implementation treated relation/context evidence as conditional (skip-when-absent). Four distinct fail-open points were identified and fixed in Task 2.

### Fail-open point 1 — map-absent skip in ProductionSelection relation checks
OLD `validate_hypothesis_references` (ProductionSelection branch) guarded every relation check with an `if X in map:` test, so an absent/empty map meant the check was skipped and the hypothesis accepted:

```python
# OLD pattern (spec §4):
if lid in registry.lineage_to_reaction_id:
    ...   # only checks when mapping present

if tid in registry.transformation_to_lineage_ids:
    ...

if sid in registry.site_to_transformation_id:
    ...
```

With all relation maps defaulting to empty (`lineage_to_reaction_id = {}` etc.), a ProductionSelection whose IDs merely existed was accepted without any relation evidence.

### Fail-open point 2 — policy-null skip in relaxation
OLD `validate_hypothesis_references` (AgentProposed branch) only enforced relaxation membership when a policy was non-null, so `allowed_relaxation_ids=["r1"]` with `relaxation_policy_id=None` was accepted (only the global existence of `r1` was checked, not that it belonged to any selected policy).

### Fail-open point 3 — both-empty skip in target membership
OLD `validate_hypothesis_against_context` guarded the entire target-membership block with:

```python
# OLD pattern (spec §3.2 B):
if context.query_atom_ids or context.query_bond_pairs:
    validate_targets()
```

When both sets were empty (the default), the whole target membership validation was skipped, so an `AtomTarget(999999)` with empty query context was accepted. OLD could not distinguish "context omitted" from "explicitly empty" because the fields defaulted to `frozenset()` rather than `None`.

### Fail-open point 4 — no registry `model_validator`
OLD `HypothesisReferenceRegistry` had no construction-time internal-consistency check. A registry could be built with `site_to_transformation_id={"s1": "t_unknown"}` where `"t_unknown"` was not in `transformation_ids`, and construction succeeded — the contradiction only surfaced (or not) at validate time.

---

## 4. Files changed & purpose (Tasks 1–3)

| File | Task | Purpose |
|------|------|---------|
| `tests/contracts/test_v4_fail_closed_context.py` | 1 (new) | 20 fail-closed tests: 15 negatives (RED on OLD) + 5 positives (guard against over-rejection) |
| `reaction_agent/schemas/hypothesis.py` | 2 | 6 fail-closed fixes: registry `model_validator`; ProductionSelection fail-closed relation chain; AgentProposed relaxation pairwise invariant; `HypothesisValidationContext` three-state query fields; target-membership fail-closed; docstrings (§11.1 wording removal) |
| `tests/contracts/test_hypothesis_lanes.py` | 2 | 1 positive-completion change: `test_reference_validation_passes_with_known_ids` registry gained the complete consistent lineage chain (`lineage_to_reaction_id`, `transformation_to_lineage_ids`, `site_to_transformation_id`) to reflect the new stricter positive contract. No assertion removed or weakened. |
| `scripts/run_p0_gate.py` | 3 | G03 upgrade: complete-relation-chain positive; 5 direct fail-closed negatives (empty maps, uncovered site, missing query context, relaxation+policy-null, inconsistent registry); `p1_status` → round-4; §11.1 banned wording removed from report assumptions/risks |
| `scripts/reproduce_v3_false_positives.py` | 3 | Added 4 new counterexamples c9–c12 (production empty maps, agent empty query context, relaxation without policy, registry internal contradiction); header/counts 8→12 |
| `reports/p0/P0_GATE_REPORT.md` | 3 (regenerated by gate) | Regenerated by `run_p0_gate.py`: G03 evidence now "fail-closed relations verified"; `p1_status` round-4; fail-closed assumptions/risks |
| `reports/p0/P0_GATE_REPORT.json` | 3 (regenerated by gate) | Regenerated by gate: `p1_status`, `assumptions`, `known_risks`, `deviations` fields all fail-closed |

---

## 5. Schema semantics decisions

- **Plan A (reuse `UnknownReferenceError`):** Chose to reuse the existing canonical `UnknownReferenceError` (subclass of `ContractViolation`) rather than introduce a new exception class. `errors.py` and `__init__.py` were NOT modified. The single exception type carries 5 distinct message categories: `unknown ID`, `missing relation coverage`, `relation mismatch`, `missing query context`, `relaxation policy missing`. (Plan B's `IncompleteValidationContextError` was not needed.)
- **Three-state query context:** `HypothesisValidationContext.query_atom_ids` and `query_bond_pairs` changed from `frozenset[...] = frozenset()` to `frozenset[...] | None = None`. Semantics: `None` = context not provided (a rejection when a target requires that context); `frozenset()` = explicitly empty (legal when the query's bond set is genuinely empty). `candidate_ids` unchanged (`frozenset[str] = frozenset()`).
- **Registry construction-time `ValidationError` vs validate-time `UnknownReferenceError`:** Internal map consistency (key/value ∈ corresponding ID sets) is enforced at registry construction by a pydantic `@model_validator(mode="after")` raising `ValueError` (pydantic wraps as `ValidationError`). Relation coverage for a specific hypothesis is enforced at validate time by `validate_hypothesis_references` raising `UnknownReferenceError`. This split keeps "registry is self-consistent" (a structural property) separate from "hypothesis cites a relation the registry covers" (a contextual property).
- **`HypothesisValidationContext` NOT in JSON export list:** The three-state field change does not alter any `model_json_schema()` property set that is exported. `HypothesisValidationContext` is not among the frozen JSON export contracts, so JSON freshness is unaffected (verified: full suite including `test_json_schema_exports.py` and `test_regression_chatgpt_audit.py::test_json_schema_freshness` passes; fresh=12/12).

---

## 6. Targeted tests result (fresh run, Task 4)

Command:
```
$ PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest \
    tests/contracts/test_v3_hypothesis_relations.py \
    tests/contracts/test_hypothesis_lanes.py \
    tests/contracts/test_v4_fail_closed_context.py \
    -q -p no:cacheprovider -ra
```
Verbatim result:
```
45 passed in 0.12s
EXIT_CODE=0
```
Breakdown: v3 relations + hypothesis lanes + v4 fail-closed = 45 passed, 0 fail / 0 error / 0 skip / 0 xfail / 0 xpass.

---

## 7. Full contract tests result (fresh run, Task 4)

Command:
```
$ PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest tests/contracts -q -p no:cacheprovider -ra
```
Verbatim result:
```
290 passed in 0.33s
EXIT_CODE=0
```
Stats: collected=290, passed=290, failed=0, errors=0, skipped=0, xfailed=0, xpassed=0. (270 pre-existing + 20 new v4 = 290.)

---

## 8. Gate result (fresh run, Task 4)

Command:
```
$ .venv/bin/python scripts/run_p0_gate.py
```
Verbatim result:
```
============================================================
P0 GATE v3 — Strict Contract Freeze Verification
============================================================

  ✅ PASS  P0-G01: Six ADRs complete and approved
  ✅ PASS  P0-G02: Authority consistency (README + ADR-0001)
  ✅ PASS  P0-G03: Hypothesis lanes + relation validation
  ✅ PASS  P0-G04: Dual ledger boundary
  ✅ PASS  P0-G05: Eligibility policy + ADR drift check
  ✅ PASS  P0-G06: Mapping/mechanism consistency
  ✅ PASS  P0-G07: Decision state machine + recursive forbidden scan
  ✅ PASS  P0-G08: MCP side-effect policy
  ✅ PASS  P0-G09: Legacy metrics provisional
  ✅ PASS  P0-G10: Contract tests + JSON freshness + env

Report: /Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p0/P0_GATE_REPORT.md
JSON:   /Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p0/P0_GATE_REPORT.json

Result: 10/10 passed
Status: READY_FOR_CHATGPT_AUDIT
EXIT_CODE=0
```

G03 evidence in `P0_GATE_REPORT.md`:
```
### P0-G03: Hypothesis lanes + relation validation
**Status:** ✅ PASS
**Evidence:** lanes + fail-closed relations verified (1 positive, 5+ negatives)
```

Gate result: 10/10 PASS, `READY_FOR_CHATGPT_AUDIT`, exit code 0. G03 evidence is fail-closed (1 complete-relation-chain positive + 5 direct negatives executed by the gate itself).

---

## 9. Independent counterexample results (fresh run, Task 4)

Command:
```
$ PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/reproduce_v3_false_positives.py
```
Verbatim result:
```
======================================================================
V3 Remediation: 12 False Positives — post-remediation verification
======================================================================
  original 8 (c1-c8) + new 4 fail-open counterexamples (c9-c12)
----------------------------------------------------------------------
  site_transform_mismatch                       REJECTED (UnknownReferenceError)
  target_not_in_query                           REJECTED (UnknownReferenceError)
  unknown_source_ledger_reference               REJECTED (UnknownReferenceError)
  donor_context_not_assumption                  REJECTED (ValidationError)
  qualitative_confidence_note                   REJECTED (ValidationError)
  self_bond_target                              REJECTED (ValidationError)
  mechanistic_evidence_mismatch                 REJECTED (ValidationError)
  formal_assignment_method_mismatch             REJECTED (ValidationError)
  production_empty_relation_maps_mismatch       REJECTED (UnknownReferenceError)
  agent_empty_query_context_target              REJECTED (UnknownReferenceError)
  relaxation_without_selected_policy            REJECTED (UnknownReferenceError)
  registry_internal_contradiction               REJECTED (ValidationError)

ACCEPTED: 0/12
REJECTED: 12/12

STATUS: all 12 false positives eliminated — remediation successful
EXIT_CODE=0
```

All 12 counterexamples (8 original + 4 new fail-open) are REJECTED. None are accepted.

---

## 10. Behavior matrix (spec §13) — ACTUAL results

All 20 cases run against the current (fail-closed) implementation. Each row shows the ACTUAL ACCEPT/REJECT outcome and the evidence (test name that passed, or reproduce case that was REJECTED, or gate negative that passed). All 20 ACTUAL outcomes match the Expected outcome.

| # | Case | Expected | Actual | Evidence |
|---|------|----------|--------|----------|
| 1 | 完整、关系一致的 ProductionSelection | ACCEPT | ACCEPT ✓ | `test_v4_fail_closed_context.py::test_full_production_selection_accepted` PASSED (no raise) |
| 2 | 所有 ID 单独存在，但 relation maps 为空 | REJECT | REJECT ✓ | `test_v4::test_all_ids_exist_but_relation_maps_empty` PASSED (raises `UnknownReferenceError`); reproduce c9 `production_empty_relation_maps_mismatch` REJECTED; gate G03 neg1 `empty relation maps not rejected` NOT triggered |
| 3 | site ID 存在，但 site relation 未覆盖当前 site | REJECT | REJECT ✓ | `test_v4::test_relation_maps_present_but_site_uncovered` PASSED (raises `UnknownReferenceError`); gate G03 neg2 `uncovered site not rejected` NOT triggered |
| 4 | site 属于另一 transformation | REJECT | REJECT ✓ | `test_v3_hypothesis_relations.py::test_site_belongs_to_another_transformation_rejected` PASSED; reproduce c1 `site_transform_mismatch` REJECTED; gate G03 orig-neg `site-transform mismatch not rejected` NOT triggered |
| 5 | transformation relation 未覆盖当前 transformation | REJECT | REJECT ✓ | `test_v4::test_relation_maps_present_but_transformation_uncovered` PASSED (raises `UnknownReferenceError`) |
| 6 | transformation 不来源于 cited lineage | REJECT | REJECT ✓ | `test_v3::test_transformation_not_from_cited_lineage_rejected` PASSED |
| 7 | lineage relation 未覆盖 cited lineage | REJECT | REJECT ✓ | `test_v4::test_cited_lineage_has_no_lineage_to_reaction_mapping` PASSED (raises `UnknownReferenceError`) |
| 8 | lineage 属于另一 reaction | REJECT | REJECT ✓ | `test_v3::test_lineage_belongs_to_another_reaction_rejected` PASSED |
| 9 | registry relation 指向未知 ID | REJECT | REJECT ✓ | `test_v4::test_registry_site_map_value_not_in_transformation_ids` + 3 sibling cases (`test_registry_transformation_map_references_unknown_lineage`, `test_registry_lineage_map_references_unknown_reaction`, `test_registry_relaxation_policy_map_references_unknown_relaxation`) all PASSED (raise `ValidationError` at construction); reproduce c12 `registry_internal_contradiction` REJECTED; gate G03 neg5 `inconsistent registry relation not rejected at construction` NOT triggered |
| 10 | AgentProposed AtomTarget 属于 query | ACCEPT | ACCEPT ✓ | `test_v4::test_legal_atom_target_accepted` PASSED (no raise) |
| 11 | AgentProposed AtomTarget 不属于 query | REJECT | REJECT ✓ | `test_v3::test_atom_target_not_in_query_rejected` PASSED; reproduce c2 `target_not_in_query` REJECTED |
| 12 | AgentProposed target 存在，但 query context 未提供 | REJECT | REJECT ✓ | `test_v4::test_agent_target_present_but_query_context_not_provided` PASSED (raises `UnknownReferenceError`); reproduce c10 `agent_empty_query_context_target` REJECTED; gate G03 neg3 `missing query context not rejected` NOT triggered |
| 13 | 合法 BondTarget 属于 query | ACCEPT | ACCEPT ✓ | `test_v4::test_legal_bond_target_accepted` PASSED (no raise) |
| 14 | BondTarget 不属于 query | REJECT | REJECT ✓ | `test_v3::test_bond_target_not_in_query_rejected` PASSED |
| 15 | BondTarget context 未提供 | REJECT | REJECT ✓ | `test_v4::test_bond_target_present_but_query_bond_pairs_none` PASSED (raises `UnknownReferenceError`) |
| 16 | 无 policy 且无 relaxation | ACCEPT | ACCEPT ✓ | `test_v4::test_legal_atom_target_accepted` PASSED — AgentProposed default `relaxation_policy_id=None`, `allowed_relaxation_ids=[]` accepts |
| 17 | 无 policy 但有 relaxation | REJECT | REJECT ✓ | `test_v4::test_relaxation_non_empty_but_policy_null` PASSED (raises `UnknownReferenceError`); reproduce c11 `relaxation_without_selected_policy` REJECTED; gate G03 neg4 `relaxation non-empty + policy null not rejected` NOT triggered |
| 18 | policy 存在且 relaxation 被允许 | ACCEPT | ACCEPT ✓ | `test_v4::test_legal_relaxation_accepted` PASSED (no raise) |
| 19 | policy 存在但 relation map 未覆盖 policy | REJECT | REJECT ✓ | `test_v4::test_policy_non_empty_but_not_covered_by_map` PASSED (raises `UnknownReferenceError`) |
| 20 | relaxation 全局存在但不属于所选 policy | REJECT | REJECT ✓ | `test_v3::test_relaxation_not_under_selected_policy_rejected` PASSED |

**Matrix result: 20/20 ACTUAL outcomes match Expected.** 5 ACCEPT (cases 1, 10, 13, 16, 18) and 15 REJECT (all others). Evidence sources: v4 tests passed (45/45 targeted), v3 tests passed (290/290 full), 6 reproduce cases (c1, c2, c9, c10, c11, c12) all REJECTED, 5 gate G03 negatives all passed (i.e. fail-open NOT detected).

---

## 11. Remaining deviations / risks

**None that allow fail-open.** The production acceptance path is fail-closed: missing relation evidence, missing query context, missing policy coverage, and registry internal contradictions are all rejections. No conditional skip-when-absent wording remains in the report or docstrings.

Four parked minor observations (non-blocking, none permit acceptance on missing context):

1. **Task 2 — function length/nesting (spec-attributed):** `validate_hypothesis_references` is longer and more nested than the coding-style guideline (<50 lines / ≤4 levels) because the spec §5.1 rules 1–13 and §5.5 pairwise invariant chain require an explicit sequential invariant ladder. This is spec-attributed (the frozen spec mandates the ladder), not an implementation choice. Non-blocking; does not affect fail-closed behavior.
2. **Task 2 — existence-check placement:** The shared `support_reaction_ids` / `support_lineage_ids` existence checks are placed before the `isinstance` branch so both lanes get them without duplication (authorized by the brief's NOTE). Functionally equivalent to placing them inside each branch. Non-blocking.
3. **Task 3 — reproduce exit-code:** `scripts/reproduce_v3_false_positives.py` exits 0 regardless of the ACCEPTED count (it prints `ACCEPTED: x/12` but does not `sys.exit` non-zero when ACCEPTED > 0). Non-blocking: the gate (G03/G10) does not depend on the reproduce script's exit code; the reproduce script is a human-readable diagnostic, and the gate's own negatives are the authoritative enforcement. The 12/12 REJECTED result was verified by reading the printed counts.
4. **Task 3 — G03 outer try/except diagnostic:** Each G03 negative is wrapped in a `try/except` that appends to `issues` if the expected exception is NOT raised (e.g. `issues.append("empty relation maps not rejected")`). This is a diagnostic pattern (detect fail-open by observing that rejection did NOT happen), not a fail-open risk. The gate still exits non-zero on any `issues` entry (`return 0 if all_passed else 1`). Non-blocking.

None of these four minors permit acceptance on missing context. The fail-closed contract is enforced by `hypothesis.py` (the production acceptance path) and independently re-verified by the gate's own 5 negatives and the 12 reproduce counterexamples.

---

## 12. Declarations

- **P1 remains BLOCKED, awaiting ChatGPT round-4 read-only audit.** Gate 10/10 is only the precondition for submitting to ChatGPT; it does not authorize P1.
- **No git add/commit/push/reset/clean executed.** Only read-only git inspection (`git status`) was used.
- **No user files deleted, moved, or overwritten.** The only file created by Task 4 is this worklog (`reports/p0/V4_REMEDIATION_WORKLOG.md`). Task 4 did not modify `P0_GATE_REPORT.md` / `.json`, `hypothesis.py`, `run_p0_gate.py`, `reproduce_v3_false_positives.py`, any test, any `plan/*.md`, any ADR, or `schemas/json/*.json`.
- **No authoritative design (plan/final_*.md, ADRs) modified to accommodate the implementation.** The fail-closed semantics were implemented to match the existing spec; no design document was weakened.
- **Status: READY_FOR_CHATGPT_ROUND_4_AUDIT.**
- **P1 BLOCKED pending ChatGPT audit.**

---

## Appendix — P0_GATE_REPORT consistency check (Task 4)

Verified by grep on `reports/p0/P0_GATE_REPORT.md` and `.json` (read-only; no edits):

| Check | Expected | Result |
|-------|----------|--------|
| §11.1 banned phrases (spec list — relation-validation-as-conditional / empty-map-cannot-detect / caller-must-supply-context / silently-passes) in `.md` | no matches | no matches (grep exit 1) ✓ |
| `p1_status` contains `round-4` in `.md` | match | line 128: `BLOCKED — P0 only, awaiting ChatGPT round-4 read-only audit` ✓ |
| `p1_status` contains `round-4` in `.json` | match | line 341: `"p1_status": "BLOCKED — P0 only, awaiting ChatGPT round-4 read-only audit"` ✓ |
| G03 evidence mentions `fail-closed` in `.md` | match | line 28: `lanes + fail-closed relations verified (1 positive, 5+ negatives)` ✓ |
| `.json` `assumptions` contains fail-closed wording | match | `Relation validation is fail-closed: missing relation evidence is a rejection, not a skip` ✓ |
| `.json` `known_risks` is `None: ...` (not fail-open) | match | `None: validation is fail-closed; missing relation evidence rejects the hypothesis` ✓ |
| §11.2 contradiction (`Deviations: none` + simultaneous fail-open description) | must NOT co-exist | `Deviations: none` present; NO conditional / `cannot detect` / skip-when-absent wording anywhere in report ✓ |

**Consistency result: report is consistent.** No §11.1 banned wording, `p1_status` is round-4, G03 evidence is fail-closed, and `deviations: none` does not co-exist with any fail-open description. The report files were generated by the gate in Task 3 and were NOT edited by Task 4.
