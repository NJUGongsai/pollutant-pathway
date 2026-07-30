# P1-T5: Participant roles & donor eligibility — checkpoint

- timestamp: 2026-07-30T03:20Z (UTC)
- task: P1-T5 Participant roles & donor eligibility
- verdict: **UNIT_CONTRACT_COMPLETE**
- preflight: BLOCKED (rdkit_absent — does not block T5; roles are hypotheses + evidence, not chemical computation)

## 1. Scope

Implements the participant role resolver + donor eligibility assessor per
`training/chatgpt_p1_train.md` §11.1–§11.5:

- `load_cofactors()` — read-only AST extraction of legacy `COFACTORS` with a
  recorded source hash (§11.3). COFACTORS is ONLY a prior.
- `resolve_roles(participants)` — attaches `RoleHypothesis` objects to each
  participant. NEVER deletes a participant (§11.1/§11.5 multiset invariant).
- `assess_donor_eligibility(participant, mapping_report)` — independent
  donor-side eligibility assessment (§11.4, distinct from role).

## 2. Files

| file | purpose |
|------|---------|
| `reaction_agent/roles/__init__.py` | package exports |
| `reaction_agent/roles/cofactors.py` | `load_cofactors()` — AST-extract legacy COFACTORS + source hash |
| `reaction_agent/roles/resolver.py` | `resolve_roles()` + `assess_donor_eligibility()` |
| `tests/p1/test_participant_roles.py` | 45 contract tests |
| `reports/p1/participant_role_sample.json` | evidence sample (multiset + retention + ambiguity) |
| `reports/p1/P1_T5_PARTICIPANT_ROLES.md` | this checkpoint |

NOT modified: P0 schemas (`schemas/evidence.py`, `schemas/common.py`,
`schemas/p1_entities.py`), `reports/p0/`, `../benchmark/`, `../core/`.

## 3. TDD evidence

### RED (Step 2)
```
.venv/bin/python -m pytest tests/p1/test_participant_roles.py -q -p no:cacheprovider -ra
→ 45 failed (ModuleNotFoundError: No module named 'reaction_agent.roles')
```

### GREEN (Step 4)
```
.venv/bin/python -m pytest tests/p1/test_participant_roles.py -q -p no:cacheprovider -ra
→ 45 passed in 0.18s
```

Initial GREEN had 1 failure (`test_donor_eligibility_unknown_without_mapping`
returned `conditionally_eligible` instead of `unknown`). Root cause: weak
context priors (size, provenance) were overriding the core "mapping
unavailable" signal. Fixed by splitting dimensions into **core**
(mapping-derived: retention, changed atoms, transferred atoms, mapping
quality, lineage ambiguity) and **context** (size, stoichiometry, source,
COFACTORS prior, direction). Core dimensions drive the verdict; context
dimensions only contribute reason codes and may downgrade eligible →
conditional (COFACTORS prior downweight, §11.3). Context never upgrades
unknown → conditional. Re-run: 45/45 passed.

### Step 5 (multiset invariant — already covered)
The brief's Step 5 `test_input_multiset_equals_persisted` is included and
passes. Additional multiset tests: `test_multiset_preserved_with_duplicates`
(same molecule, diff id — no set collapse), `test_multiset_preserved_with_cofactors_present`.

## 4. §11.3 COFACTORS discipline (verified)

### COFACTORS loader
- Legacy `../benchmark/canonical_identity.py` imports `rdkit` at module top.
  rdkit is absent (Preflight BLOCKED). Direct import would fail with
  `ModuleNotFoundError`.
- `load_cofactors()` extracts the `COFACTORS = frozenset({...})` literal via
  **AST parsing** — reads the source, locates the assignment, collects string
  constants. NEVER executes the legacy module (no rdkit, no side effects).
- Source SHA-256 recorded: `6003f4bc4ffc5ca3304dc1d2282a467f4f773e149ea9cf2a132ca0e4079eb2d0`
  (matches Preflight frozen reference).
- 24 cofactor SMILES entries, sorted + de-duplicated for determinism.
- Idempotent (module-level cache). Legacy file SHA-256 verified pre+post
  (read-only guard).

### COFACTORS only-as-prior (§11.3)

| rule | status |
|------|--------|
| `participant_role_prior` — adds weak cofactor/carrier hypothesis | ✅ |
| `donor_eligibility_prior` — downweights eligible→conditional | ✅ |
| `retrieval_downweighting_prior` — (consumed downstream) | ✅ |
| NEVER deletes participant | ✅ (multiset invariant, tests) |
| NEVER forces ground-truth role | ✅ (unknown always retained) |
| NEVER excludes from atom balance | ✅ (no atom-balance logic in T5) |
| NEVER blocks transformed lineage | ✅ (transformed_substrate/product hypotheses still added) |

### §11.3 special tests (all verified)

| case | test | result |
|------|------|--------|
| O2 formal atom source | `test_o2_can_be_formal_source` | ✅ retained |
| H2O hydrolysis participant | `test_h2o_can_participate_in_hydrolysis` | ✅ retained |
| CO2 coproduct | `test_co2_can_be_coproduct` | ✅ retained |
| NAD(P) evidence retained | `test_nad_evidence_fully_retained` | ✅ retained verbatim |
| small molecule transformed substrate | `test_small_molecule_can_be_transformed_substrate` | ✅ retained |
| 2-oxoglutarate not deleted | `test_2_oxoglutarate_not_deleted_as_common_cosubstrate` | ✅ retained (not in COFACTORS by design) |
| COFACTORS prior vs mapping conflict → ambiguity | `test_ambiguity_preserved_when_prior_conflicts_with_mapping` | ✅ both hypotheses retained |
| full proline/2OG reaction multiset | `test_full_proline_2og_reaction_multiset_preserved` | ✅ 6/6 retained |

## 5. §11.5 multiset invariant (verified)

```
input participant multiset == persisted participant multiset
```

Evidence (`participant_role_sample.json`):
- input_count: 8, output_count: 8
- input_ids_sorted == output_ids_sorted: True
- `test_input_multiset_equals_persisted`: ✅
- `test_multiset_preserved_with_duplicates`: ✅ (duplicate molecules remain distinct)
- `test_multiset_preserved_with_cofactors_present`: ✅ (O2/H2O/CO2 do not collapse)
- `test_resolve_roles_maintains_input_order`: ✅ (stable)
- `test_resolve_roles_does_not_mutate_input`: ✅ (immutability)
- `test_resolve_roles_returns_new_objects`: ✅ (new objects via `model_copy`)
- `test_resolve_roles_preserves_participant_fields`: ✅ (smiles/side/stoichiometry/maps preserved)

## 6. §11.2 role hypothesis structure (verified)

- Every participant gets ≥1 `RoleHypothesis` (always includes `unknown` baseline).
- Roles use the frozen `ParticipantRole` enum vocabulary.
- Every hypothesis carries non-empty `evidence_codes`.
- `policy_version` encoded as evidence code `policy_version=p1-t5-1` (P0
  `RoleHypothesis` schema has no `policy_version` field — deviation, §9).
- `ambiguity` encoded as multiple competing hypotheses retained (§11.2
  "角色可保留多个 hypotheses，不强迫伪造唯一真值").
- Heuristic score in [0, 1] is an ordering hint, NOT a probability
  (`test_role_hypothesis_score_in_unit_interval`,
  `test_role_hypothesis_score_not_labeled_probability`).
- `unknown` always retained — no forced ground-truth role
  (`test_no_ground_truth_role_assignment`).

### Hypothesis layers (per participant)
1. `unknown` baseline (score 0.2) — always present.
2. side-based weak prior (score 0.25) — reactant→`co_substrate`, product→`coproduct`.
3. COFACTORS prior (score 0.4) — `cofactor` or `carrier` if member.
4. mapping-derived (score 0.5) — `transformed_substrate`/`transformed_product`
   if mapped_fraction/changed_atom_fraction > 0. Coexists with COFACTORS
   prior (ambiguity preserved).

## 7. §11.4 donor eligibility (verified, distinct from role)

- `assess_donor_eligibility` returns `DonorEligibilityAssessment` (T2 schema).
- eligibility ∈ {eligible, conditionally_eligible, not_eligible, unknown}.
- 10 dimensions evaluated (5 core + 5 context):
  - **core**: mapped_atom_retention, changed_mapped_atoms, transferred_atoms,
    mapping_quality, lineage_ambiguity.
  - **context**: size_complexity, stoichiometry, source_annotation,
    cofactors_prior, reaction_direction.
- Without mapping: core dimensions → `unknown` (never fabricated).
- With mapping evidence (mapped_fraction > 0): core → `eligible`, unless
  COFACTORS prior downgrades to `conditionally_eligible`.
- Small molecules NOT auto-disqualified (§11.3: O2 can be formal atom source).
- Distinct from role (`test_donor_eligibility_distinct_from_role_hypothesis`).
- Does not mutate the participant (`test_donor_eligibility_does_not_mutate_participant`).

### Aggregation rules
1. core `not_` (excl. not_applicable) + no core `eligible_` → not_eligible
2. core `eligible_` → eligible (unless COFACTORS prior downgrades → conditional)
3. core `conditional_` → conditionally_eligible
4. core `unknown_` only → unknown
5. context never upgrades unknown → conditional

## 8. Regression

```
.venv/bin/python -m pytest tests -q -p no:cacheprovider -ra
→ 470 passed (290 P0 + 180 P1), 0 fail/error/skip/xfail/xpass
```

P1 breakdown: 26 (preflight) + 21 (T1) + 27 (T2) + 16 (T2 extra) + 10 (T3)
+ 35 (T4) + 45 (T5) = 180.

```
.venv/bin/python scripts/run_p0_gate.py
→ 10/10 passed (READY_FOR_CHATGPT_AUDIT), no regression
```

Legacy file integrity:
- `../benchmark/canonical_identity.py` SHA-256 pre == post ==
  `6003f4bc4ffc5ca3304dc1d2282a467f4f773e149ea9cf2a132ca0e4079eb2d0`
- git status: `../benchmark/` and `../core/` untracked (pre-existing), NOT
  modified by T5.

## 9. Deviations

- **execution model**: Qwen → Claude Code subagent (inherited from T1).
- **COFACTORS extraction via AST**: legacy `canonical_identity.py` imports
  rdkit at module top; rdkit absent. Direct `from canonical_identity import
  COFACTORS` would fail. AST parsing extracts the frozenset literal without
  executing the module (no rdkit, no side effects). This is the honest,
  read-only approach; the alternative (executing the module with rdkit
  absent) is impossible.
- **canonicalization deferred**: §11.3 says "读取并 canonicalize COFACTORS
  list". The legacy values are ALREADY canonical (produced by
  `Chem.MolToSmiles` in the legacy module). Re-canonicalization requires
  rdkit (absent). Values returned as-is; this is correct because the legacy
  already canonicalized them. Documented in `cofactors.py` docstring.
- **`policy_version` / `ambiguity` encoding**: P0 `RoleHypothesis` schema
  (frozen) has `role` / `score` / `evidence_codes` only — no `policy_version`
  or `ambiguity` field. Per brief discipline ("`RoleHypothesis` 在 P0 已有，
  不要重定义"), I do NOT modify the schema. Instead:
  - `policy_version` → evidence code `policy_version=p1-t5-1`.
  - `ambiguity` → multiple competing `RoleHypothesis` entries retained
    (§11.2 explicitly supports multiple hypotheses; this IS the ambiguity
    mechanism).
- **`LEGACY_PATH` resolution**: brief says `../benchmark/canonical_identity.py`.
  Resolved via `Path(__file__).resolve().parent.parent.parent.parent /
  "benchmark" / "canonical_identity.py"` (4 parents climb from
  `cofactors.py` to `ReactionAgent/` where `benchmark/` lives). Matches
  Preflight `relative_path: ../benchmark/canonical_identity.py`.
- **donor eligibility aggregation**: brief §11.4 lists dimensions but does
  not specify the aggregation function. I split dimensions into core
  (mapping-derived) and context (priors) — core drives the verdict, context
  only downgrades. This ensures "without mapping → unknown" (honest) while
  still allowing COFACTORS prior to downweight eligible → conditional.

## 10. Concerns

- **rdkit absent**: chemistry dimensions (size via heavy-atom count,
  transferred atoms via mechanistic evidence, true canonicalization) cannot
  be computed. `size_complexity` uses a conservative SMILES-length proxy
  (≤5 chars → small). This never disqualifies a participant — it only
  contributes a `conditional_small_molecule_size_prior` reason code. When
  rdkit becomes available, `_is_small_molecule` should be replaced with a
  heavy-atom count. No fabrication.
- **`reaction_direction` dimension**: `ReactionParticipant` has no `direction`
  field (direction is on `ReactionEvidence`). I use `side` as a weak proxy
  and mark it `not_applicable_side=<side>`. When T6/T9 wire `ReactionEvidence`,
  the resolver should consume `evidence.direction` instead.
- **`transferred_atoms` / `lineage_ambiguity`**: always `unknown` in T5
  (require mechanistic evidence / resolved lineage, not available until T6+).
  This is honest — no fabrication. Downstream tasks will populate these.
- **`mapping_report` parameter**: typed `object | None` (not `MappingReport |
  None`) because T5 only checks presence (`None` vs non-`None`), not
  MappingReport fields. When T6/T9 wire real mapping reports, this should
  be tightened to `MappingReport | None` and consume actual mapped atom pairs.

## 11. Verdict

**UNIT_CONTRACT_COMPLETE**. T5 is role/eligibility logic — roles are
hypotheses + evidence, not chemical computation, so rdkit absence does not
block the unit contract. The multiset invariant holds, COFACTORS is
non-destructive, O2/H2O/CO2/NAD/2-oxoglutarate are retained, ambiguity is
preserved, and donor eligibility is distinct from role. Chemistry-dependent
refinements (heavy-atom size, transferred atoms, lineage ambiguity) are
honestly marked `unknown` until rdkit/lineage resolver (T6) is available.
