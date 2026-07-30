# P1-T7: SourceReactionLedger Builder

**Task:** P1-T7 — SourceReactionLedger
**Status:** UNIT_CONTRACT_COMPLETE
**Builder version:** `p1-t7-1`
**Date:** 2026-07-30

## 1. Summary

Implemented `build_source_ledger(reaction_evidence, lineages) -> SourceReactionLedger`
in `reaction_agent/ledgers/source_builder.py`. The builder constructs a
SourceReactionLedger from a ReactionEvidence + resolved transformed lineages,
filling all §10.1 fields.

**No-fabrication discipline enforced (brief §13.4 / §10.4 / ADR-0003):**
- Missing stoichiometry → unknown (detected via `model_fields_set`; pydantic
  default 1 is NOT asserted as fact).
- Missing H+/e− → explicit policy (never "balanced"; "unknown" or
  "implicit_heavy_atom_balanced_h_policy" / "cofactor_redox_implicit_e_policy").
- Formal mapper → formal assignment (`assignment_method="formal"`); NEVER
  promoted to mechanistic proof.
- Unknown atom source → explicit `unknown_source` (`formal_assignment=False`);
  blocks strict eligibility.
- Element balance NOT fabricated (rdkit absent → empty list +
  `element_balance_rdkit_absent_proxy` unknowns entry).
- Charge balance IS computed (from `formal_charge` fields, no rdkit needed).

## 2. Files

| File | Action | Purpose |
|------|--------|---------|
| `reaction_agent/ledgers/__init__.py` | Create | Package init, exports `build_source_ledger` |
| `reaction_agent/ledgers/source_builder.py` | Create | Builder implementation (§10.1 all fields) |
| `tests/p1/test_source_ledger.py` | Create | 24 contract tests (13 §13.5 + skeleton + edge + I1 gap) |
| `reports/p1/source_ledger_samples.json` | Create | 8 representative samples + no-fabrication evidence |
| `reports/p1/P1_T7_SOURCE_LEDGER.md` | Create | This report |

## 3. Test results

### 3.1 RED → GREEN

```
RED:  ModuleNotFoundError: No module named 'reaction_agent.ledgers'
      (1 collection error — module did not exist)
GREEN: 24 passed in 0.16s
```

### 3.2 Full regression

```
.venv/bin/python -m pytest tests -q -p no:cacheprovider -ra
536 passed in 0.45s   (baseline 535 + 1 new I1 gap test; zero skip/xfail)
```

### 3.3 P0 Gate

```
.venv/bin/python scripts/run_p0_gate.py
Result: 10/10 passed
Status: READY_FOR_CHATGPT_AUDIT
```

No regression. P0 baseline preserved.

## 4. Balance status distribution (§10.3)

From the 8 representative samples in `source_ledger_samples.json`:

| Status | Count | Samples |
|--------|-------|---------|
| `heavy_atom_balanced_with_implicit_h_e_policy` | 3 | o2_incorporation, complete_balanced, mechanistic_evidence_present |
| `partial_or_unbalanced_source` | 5 | charge_mismatch, missing_stoichiometry, unknown_atom_source, decarboxylation, empty |
| `fully_balanced_explicit_reaction` | 0 | (requires rdkit-computed element balance — not asserted without rdkit) |

**Note (fix round 1):** decarboxylation was downgraded from
`heavy_atom_balanced_with_implicit_h_e_policy` to
`partial_or_unbalanced_source` after the §10.4 gap fix. CO2 (unlineaged
coproduct with atoms [1, 2] but no formal mapping source) now correctly
gets `unknown_source` entries → not strict-eligible.

**Why no `fully_balanced_explicit_reaction`:** rdkit is absent (Preflight
BLOCKED). Real element balance requires molecular formula comparison (rdkit).
The builder does NOT fabricate element counts — it leaves `element_balance`
empty and records `element_balance_rdkit_absent_proxy` in unknowns. The
honest best-case status without rdkit is
`heavy_atom_balanced_with_implicit_h_e_policy` (heavy atoms tracked via
formal mapping, H+/e− balance implicit). When rdkit becomes available, this
can be upgraded to `fully_balanced_explicit_reaction` for reactions where
all elements balance.

## 5. No-fabrication evidence

### 5.1 Missing stoichiometry → unknown (not default 1)

Detection: `participant.model_fields_set`. If `stoichiometry` is NOT in the
set, the value (1) is the pydantic default, NOT a recorded fact.

Evidence from `missing_stoichiometry` sample:
```json
"unknowns": ["stoichiometry_unverified:p1", "stoichiometry_unverified:p2",
             "source_annotation_missing:p1", "source_annotation_missing:p2",
             "element_balance_rdkit_absent_proxy"]
```

The `StoichiometricEntry` still carries `coefficient=1` (lossless) but the
ledger explicitly flags it as unverified via unknowns — the value is
preserved but NOT asserted as a proven fact.

### 5.2 Missing H+/e− → explicit policy (not silent fill)

Policies are NEVER "balanced". They are "unknown" or an explicit
implicit-policy label:

| Condition | hydrogen_policy | proton_policy | electron_policy |
|-----------|-----------------|---------------|-----------------|
| No mapping | `unknown` | `unknown` | `unknown` |
| Mapping present | `implicit_heavy_atom_balanced_h_policy` | `unknown` | `unknown` |
| Redox cofactors present | `implicit_heavy_atom_balanced_h_policy` | `cofactor_redox_implicit_proton_policy` | `cofactor_redox_implicit_e_policy` |

### 5.3 Formal mapper ≠ mechanistic origin (ADR-0003)

- `formal_atom_transfer_assignments`: populated from
  `mapping_report.formal_mapped_source_assignment.mapped_atom_pairs`.
  All entries use `assignment_method="formal"`.
- `mechanistic_origin_evidence`: populated ONLY from
  `mapping_report.mechanistic_atom_origin` (which the mapper NEVER
  auto-populates). If `mechanistic_atom_origin is None` → empty list.

Evidence from `o2_incorporation` sample:
```json
"mechanistic_origin_evidence": []
"formal_atom_transfer_assignments": [
  {"assignment_method": "formal", ...}
]
```

### 5.4 Unknown atom source → explicit `unknown_source` (§10.4)

When a changed heavy atom in a product has NO formal source (not traced by
any mapping pair), the builder records:
```json
"added_atom_sources": [
  {"atom_map_number": 3, "source_participant_id": "unknown_source",
   "formal_assignment": false}
]
```
Plus an unknowns entry: `"unknown_atom_source:p2:atom_3"`.
This blocks strict eligibility → `partial_or_unbalanced_source`.

### 5.5 Element balance rdkit-absent proxy

Element balance (molecular formula comparison) requires rdkit. The builder
does NOT fabricate element counts. It leaves `element_balance` empty and
records `"element_balance_rdkit_absent_proxy"` in unknowns. Charge balance
IS computed (from `formal_charge` fields, no rdkit needed).

## 6. Participant preservation (§11.1/§11.5)

Every input participant appears in the ledger's `reactant_entries` or
`product_entries`. No participant is lost — including cofactors, carriers,
and small molecules (§11.3: COFACTORS is not destructive).

Evidence from `o2_incorporation` sample (3 participants → 3 entries):
```json
"reactant_entries": [{"participant_id": "p1"}, {"participant_id": "p2"}]
"product_entries": [{"participant_id": "p3"}]
```

## 7. 13 §13.5 test coverage

| # | Test | Scenario | Key assertion |
|---|------|----------|---------------|
| 1 | `test_redox_cofactor_change_recorded` | NAD+/NADH redox | cofactor_changes recorded; electron_policy != "balanced" |
| 2 | `test_o2_incorporation_formal_source` | O2 → product O atom | added_atom_sources formal; O2 preserved |
| 3 | `test_hydrolysis_h2o_preserved_and_sourced` | H2O hydrolysis | H2O preserved as reactant; atom contribution recorded |
| 4 | `test_decarboxylation_co2_coproduct_and_sink` | CO2 coproduct | CO2 preserved; removed_atom_sinks recorded |
| 5 | `test_transfer_formal_assignment_recorded` | Acyl transfer | formal_atom_transfer_assignments present; method="formal" |
| 6 | `test_charge_mismatch_yields_partial_balance` | Charge +2 → 0 | charge_balance != 0; partial_or_unbalanced_source |
| 7 | `test_missing_stoichiometry_is_unknown_not_default_1` | No stoichiometry | unknowns entry; source_completeness != "complete" |
| 8 | `test_incomplete_source_completeness` | No provenance | source_completeness in ("incomplete","unknown") |
| 9 | `test_ambiguous_formal_assignment_flagged` | Ambiguity flag | balance_status != fully_balanced |
| 10 | `test_unknown_atom_source_not_strict` | Unmapped atom | unknown_source entry; partial_or_unbalanced_source |
| 11 | `test_mechanistic_evidence_absent_formal_only` | No mechanism | mechanistic_origin_evidence == [] |
| 12 | `test_unbound_mechanistic_evidence_rejected` | Unbound evidence | MappingReport schema rejects (ADR-0003 §12) |
| 13 | `test_complete_participant_preservation` | 6 participants | ledger_pids == input_pids |

Plus 11 additional contract tests (balance typed, H+ policy, formal≠mechanism,
immutability, empty input, return type, ID stability, fully-balanced positive
case, mechanistic-present positive case, no-unknowns-when-complete, unlineaged
product atoms §10.4 gap).

**Total: 24 tests, all passing.**

## 8. Deviations / concerns

- **rdkit absent**: element balance NOT computed (left empty +
  `element_balance_rdkit_absent_proxy` unknowns entry). `fully_balanced_explicit_reaction`
  status is never asserted without rdkit (honest downgrade to
  `heavy_atom_balanced_with_implicit_h_e_policy`). Replace with real formula
  comparison when rdkit available.
- **cofactor direction**: `direction="unknown"` (structure comparison needed
  for oxidation vs reduction — rdkit absent, not fabricated). The
  `cofactor_changes` list records the presence of cofactor/carrier
  participants on each side but does not assert the redox direction.
- **stoichiometry detection via `model_fields_set`**: this is the cleanest
  signal available given the P0 schema (no separate "stoichiometry_recorded"
  flag). It correctly distinguishes "explicitly set to 1" from "defaulted to
  1". If a future schema revision adds an explicit stoichiometry_source field,
  the builder should prefer that.
- **added/removed atom detection**: uses `lineage.transformed_atom_maps` and
  `participant.atom_map_numbers` to compute set differences. Atoms not in any
  lineage's transformed set are treated as new/removed. This is conservative
  — when mapping is partial, unmapped atoms are correctly flagged as
  `unknown_source` (not fabricated).
- **§10.4 gap (fix round 1)**: products NOT in any lineage now have their atoms
  checked too. Previously, unlineaged products (e.g. decarboxylation CO2
  coproduct) were silently skipped → record incorrectly marked strict-eligible.
  Now their atoms get `unknown_source` entries when no formal mapping source
  traces them, and `balance_status` downgrades to `partial_or_unbalanced_source`.

## 9. Verdict

UNIT_CONTRACT_COMPLETE (fix round 1 applied). The builder fills all §10.1 fields,
enforces the no-fabrication discipline (§13.4), and preserves all participants
(§11.1). The §10.4 gap (unlineaged product atoms) is closed — all products now
have their atoms checked for formal mapping source, whether in a lineage or not.
rdkit absence does not block the unit contract — element balance is honestly
marked absent, and charge balance (computable without rdkit) is always computed.
P0 baseline (512 → 535 → 536) and Gate 10/10 preserved.

Next task authorization: T7 UNIT_CONTRACT_COMPLETE. T8 (CandidateAnalogyLedger)
may proceed.
