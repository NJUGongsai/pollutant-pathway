# P8 Stage A — T1 Relaxation policy + T2 Generalized hypothesis

**Issued:** 2026-08-07 · **Branch:** `worktree-p8-generalized-lane`
**Status:** PASS (Round 2 remediation applied per `P8_STAGE_A_ROUND_1_READ_ONLY_AUDIT`)

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
| `tests/p8/test_policy.py` | T1 tests (16) |
| `tests/p8/test_generalized_hypothesis.py` | T2 tests (22) |
| `reports/p8/relaxation_policy_p8-generalized-relaxation_v1.0.0.json` | Frozen policy artifact |

## T1 — Relaxation policy (final_plan §11.2)

- **`policy_id` + semver `version` + `content_hash`**: `RelaxationPolicy` is a
  `frozen=True` StrictModel; `content_hash` is SHA-256 over the canonical
  serialized body and re-verified on load (tamper → `ValidationError`).
- **Registered vocabulary (D6)**: every relaxation is a typed `RelaxationRule`
  with `rule_id` / `description` / `applies_to[]` / `distance_weight`. `rule_id`
  must be unique within a policy (R1-03). No free-text relaxation rules.
- **Forbidden hard constraints (final_design §12.2)**: `trusted_mapped_lineage`,
  `graph_edit_replayable`, `changed_heavy_atom_conservation` can never be relaxed.
  The policy freezes exactly this set.
- **Distance**: `generalization_distance = Σ weight(relaxation)` over applied
  relaxations, derived from the failed/relaxed conditions. `distance_weight` is
  strictly positive (`> 0`) so distance buckets stay well-defined (R1-06).
- **OOD**: `OODPolicy` declares the boundary — a generalized hypothesis citing a
  relaxation outside the registered vocabulary is out-of-distribution and rejected.
- **Version pinning**: a hypothesis pins `policy_id + version`; any content change
  bumps `version` and yields a new `content_hash`.

## T2 — Generalized hypothesis (final_plan §11.3)

Six recorded fields: `relaxation_policy_id` / `allowed_relaxation_ids[]` /
`failed_strict_conditions[]` / `generalization_distance` / `source_transforms[]`
(traceable transform→lineage) / `validation`.

Validation chain (`validate_generalized_hypothesis`):
- `policy_version` pin matches the registered policy version (R1-01)
- `allowed_relaxation_ids` all ∈ policy registered vocabulary (D6)
- `failed_strict_conditions` non-empty **and** no forbidden hard constraint (D5)
- relaxation coverage: applied relaxations cover exactly the failed conditions
- `generalization_distance` recomputed per policy and matched
- OOD boundary check
- `validation.policy_content_hash` matches the policy's content hash (R1-04)
- source transform references exist + lineage traceable

Error typing (R1-05): reference violations → `UnknownReferenceError`;
non-reference violations (version pin, masquerade, coverage, distance, OOD,
content-hash trace) → `GeneralizedValidationError`.

**Anti-masquerade (D5)**: `lane` is Literal-typed to `generalized` (R1-02); a
hypothesis with empty `failed_strict_conditions` is rejected at construction and
at validation. The `validation` record is `status`-Literal and carries the
`policy_content_hash` it was verified against (R1-04) — a consumer never trusts
an embedded status without the matching policy fingerprint.
`GeneralizedHypothesis` is **not** merged into the strict `hypothesis_origin`
union (D3) — it has its own independent validation entry.

## Round 2 remediation (per Round 1 audit)

| Finding | Severity | Closure |
|---------|----------|---------|
| R1-01 policy_version pin missing | P1 | `policy_version` field (semver) added; chain forces `policy.version == hypothesis.policy_version`; RED tests + report corrected |
| R1-02 lane/status bare str | P2 | `lane`/`status` now `Literal["generalized"]`/`Literal["validated"]` |
| R1-03 rule_id non-unique | P2 | `RelaxationPolicy` uniqueness validator + RED test |
| R1-04 validation self-asserting | P2 | builder burns in `checks` + `policy_content_hash` immutably after chain passes; chain verifies hash trace |
| R1-05 error type mixing | P2 | `GeneralizedValidationError` for validation; `UnknownReferenceError` reserved for references |
| R1-06 distance_weight allows 0 | P2 | `distance_weight` now `> 0` |

## RED → GREEN evidence

- **RED** `b7ec4fe` `test(p8): RED — T1 relaxation policy + T2 generalized hypothesis tests`
  — both test files failed collection (`ModuleNotFoundError: No module named
  'reaction_agent.p8'`).
- **GREEN** `129c0a7` — implementation added; `tests/p8/` = 28 passed.
- **RED** `794e237` `test(p8): RED — Round 2 R1-01..R1-06 remediation tests`
  — failed on `ImportError: GeneralizedValidationError` (missing field/type).
- **GREEN** (next commit) — R1 fixes; `tests/p8/` = 38 passed.

## Test results

- `tests/p8/`: **38 passed** (16 T1 + 22 T2).
- Full suite (strict-untouched regression): **1918 passed, 1 pre-existing
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