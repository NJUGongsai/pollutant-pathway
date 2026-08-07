# P8 Stage A — T1 Relaxation policy + T2 Generalized hypothesis

**Issued:** 2026-08-07 · **Branch:** `worktree-p8-generalized-lane` · **Status:** PASS

## Scope

Stage A of P8 Generalized Lane (final_plan §11.2–11.3, final_design §12.1–12.3 /
§18.1 / §19.2). Independent generalized lane, physically isolated from the
strict channel. **strict untouched**: only NEW files under `reaction_agent/p8/`,
`tests/p8/`, `reports/p8/` were added; no existing file was modified.

## Deliverables

| Artifact | Description |
|----------|-------------|
| `reaction_agent/p8/policy.py` | **T1** `RelaxationPolicy` (frozen, content-hashed, semver) |
| `reaction_agent/p8/schemas.py` | **T2** `GeneralizedHypothesis` + validation chain |
| `reaction_agent/p8/__init__.py` | Package re-exports |
| `tests/p8/test_policy.py` | T1 tests (14) |
| `tests/p8/test_generalized_hypothesis.py` | T2 tests (14) |
| `reports/p8/relaxation_policy_p8-generalized-relaxation_v1.0.0.json` | Frozen policy artifact |

## T1 — Relaxation policy (final_plan §11.2)

- **`policy_id` + semver `version` + `content_hash`**: `RelaxationPolicy` is a
  `frozen=True` StrictModel; `content_hash` is SHA-256 over the canonical
  serialized body and re-verified on load (tamper → `ValidationError`).
- **Registered vocabulary (D6)**: every relaxation is a typed `RelaxationRule`
  with `rule_id` / `description` / `applies_to[]` / `distance_weight`. No
  free-text relaxation rules.
- **Forbidden hard constraints (final_design §12.2)**: `trusted_mapped_lineage`,
  `graph_edit_replayable`, `changed_heavy_atom_conservation` can never be relaxed.
  The policy freezes exactly this set.
- **Distance**: `generalization_distance = Σ weight(relaxation)` over applied
  relaxations, derived from the failed/relaxed conditions.
- **OOD**: `OODPolicy` declares the boundary — a generalized hypothesis citing a
  relaxation outside the registered vocabulary is out-of-distribution and rejected.
- **Version pinning**: a hypothesis pins `policy_id + version`; any content change
  bumps `version` and yields a new `content_hash`.

## T2 — Generalized hypothesis (final_plan §11.3)

Six recorded fields: `relaxation_policy_id` / `allowed_relaxation_ids[]` /
`failed_strict_conditions[]` / `generalization_distance` / `source_transforms[]`
(traceable transform→lineage) / `validation`.

Validation chain (`validate_generalized_hypothesis`):
- `allowed_relaxation_ids` all ∈ policy registered vocabulary (D6)
- `failed_strict_conditions` non-empty **and** no forbidden hard constraint (D5)
- relaxation coverage: applied relaxations cover exactly the failed conditions
- `generalization_distance` recomputed per policy and matched
- OOD boundary check
- source transform references exist + lineage traceable

**Anti-masquerade (D5)**: `lane` is pinned to `generalized`; a hypothesis with
empty `failed_strict_conditions` is rejected at construction and at validation.
`GeneralizedHypothesis` is **not** merged into the strict `hypothesis_origin`
union (D3) — it has its own independent validation entry.

## RED → GREEN evidence

- **RED** `b7ec4fe` `test(p8): RED — T1 relaxation policy + T2 generalized hypothesis tests`
  — both test files failed collection (`ModuleNotFoundError: No module named
  'reaction_agent.p8'`).
- **GREEN** (next commit) — implementation added; `tests/p8/` = 28 passed.

## Test results

- `tests/p8/`: **28 passed** (14 T1 + 14 T2).
- Full suite (strict-untouched regression): **1877 passed, 1 pre-existing
  failure** — `tests/p1/test_p1_gate_contract.py::test_zero_skip_xfail_in_full_suite`,
  which fails only because the p5 real-data module is **deliberately skipped**
  (`known-missing: p1-design-quarantine` — the real P1 snapshot was quarantined
  and never generated; see `reports/p1/required_case_quarantine_evidence.json`).
  This is a documented, pre-existing fail-closed condition unrelated to P8;
  fabricating the quarantined data or editing existing tests is forbidden by D2.

## Run

```bash
python -m pytest tests/p8/ -q
python -m pytest -q                 # full suite
```

Virtualenv is external (not inside the worktree) to keep the submission
`.venv`-free per the P3 submission contract.