# P1-T4: Atom-mapping adapter — checkpoint

- timestamp: 2026-07-30T02:36Z (UTC)
- task: P1-T4 Atom-mapping adapter
- verdict: **UNIT_CONTRACT_COMPLETE / INTEGRATION_BLOCKED**
- preflight: BLOCKED (rdkit_absent, real_reaction_source_not_confirmed, required_case_missing)

## 1. Scope

Implements the minimal `AtomMapper` Protocol (§10.1) + deterministic
`FakeAtomMapper` (unit tests) + `compute_quality_flags` (§10.3) +
`RealMapperAdapter` skeleton (real mapper integration).

Formal mapping ONLY — never auto-generates `mechanistic_atom_origin` (§10.4).
MCS/center-pair fallback downgrades mapping status (§10.5).

## 2. Files

| file | purpose |
|------|---------|
| `reaction_agent/mapping/__init__.py` | package exports |
| `reaction_agent/mapping/base.py` | `AtomMapper` Protocol (§10.1) |
| `reaction_agent/mapping/adapter.py` | `FakeAtomMapper` + `compute_quality_flags` + `RealMapperAdapter` |
| `tests/p1/test_mapping_adapter.py` | 30 contract tests |
| `reports/p1/mapping_integration_sample.json` | integration sample (INTEGRATION_BLOCKED) |
| `reports/p1/P1_T4_MAPPING_ADAPTER.md` | this checkpoint |

NOT modified: P0 schemas (`schemas/mapping.py`, `schemas/common.py`),
`reports/p0/`, `../benchmark/`, `../core/`.

## 3. TDD evidence

### RED (Step 3)
```
.venv/bin/python -m pytest tests/p1/test_mapping_adapter.py -q -p no:cacheprovider -ra
→ 30 failed (ModuleNotFoundError: No module named 'reaction_agent.mapping')
```

### GREEN (Step 5)
```
.venv/bin/python -m pytest tests/p1/test_mapping_adapter.py -q -p no:cacheprovider -ra
→ 30 passed in 0.19s
```

Initial GREEN had 1 failure (`test_duplicate_map_ids_flagged` — the
`duplicate_map_ids` constructor flag was not wired through to
`map_number_uniqueness`). Fixed by overriding `map_uniqueness=False` when
`self._duplicate_map_ids` is set. Re-run: 30/30 passed.

## 4. Protocol + adapter contract

### AtomMapper Protocol (§10.1)
```python
class AtomMapper(Protocol):
    def map_reaction(self, reaction: NormalizedReactionRecord) -> MappingReport: ...
```
`@runtime_checkable` so structural typing works. The Protocol captures the
§10.1 capture list via MappingReport fields:
- `mapper_name` / `mapper_version` / `mapper_parameters` (typed)
- `input_hash` / `output_hash` (content-addressed, SHA-256 via `canonical_hash`)
- `mapping_status` (§10.2 frozen vocabulary)
- `quality_flags` (§10.3 8 dimensions)
- `fallback_method` (§10.5 — MCS/center-pair must be explicit)
- `timeout` / `runtime_ms` captured in `mapper_parameters`

### FakeAtomMapper (deterministic, unit-test only)
- `mapper_name = "fake"`, `mapper_version = "p1-fake-1"`
- Deterministic: same input record + same parameters → same `output_hash`
- Formal ONLY: `mechanistic_atom_origin = None` always (§10.4)
- `status` param controls `mapping_status` (§10.2 vocabulary)
- `fallback` param ("mcs" / "center_pair"): downgrades `fully_mapped` →
  `partially_mapped`, sets `fallback_method`, uses `formal_mcs` assignment
- `duplicate_map_ids=True`: sets `map_number_uniqueness=False`
- `symmetry_ambiguity` / `resonance_tautomer_ambiguity` flags
- Generates typed `FormalMappedAtomPair` objects (§11, not arbitrary dict)

### compute_quality_flags (§10.3)
Returns 8 quality dimension strings (`name=value` format):
1. `map_number_uniqueness=pass|fail`
2. `mapped_heavy_atom_fraction=<float>`
3. `changed_atom_coverage=<float>`
4. `reactant_product_map_consistency=pass|partial`
5. `duplicate_map_ids=none|detected`
6. `unmapped_changed_atoms=none|present`
7. `symmetry_ambiguity=none|detected`
8. `resonance_tautomer_ambiguity=none|detected`

### RealMapperAdapter (skeleton)
- `SUPPORTED_BACKENDS = ("rdkit", "rxnmapper", "rxn4chemistry")`
- `is_available()` probes backend importability on construction
- `map_reaction()` raises `NotImplementedError` with `INTEGRATION_BLOCKED`
  marker when backend unavailable (§10.7)
- All 3 backends probed: **all unavailable** (rdkit/numpy/networkx/scipy absent)

## 5. §10.4 formal ≠ mechanistic (verified)

| check | result |
|-------|--------|
| `mechanistic_atom_origin` always None | ✅ |
| `mechanistic_origin_evidence_ids` always [] | ✅ |
| `formal_mapped_source_assignment` typed object present | ✅ |
| typed/flat consistency enforced by MappingReport validator | ✅ |

## 6. §10.5 MCS/center-pair fallback (verified)

| scenario | status | fallback_method | assignment_method |
|----------|--------|-----------------|-------------------|
| fully_mapped, no fallback | fully_mapped | None | formal_mapped |
| fully_mapped + mcs | **partially_mapped** | mcs | formal_mcs |
| fully_mapped + center_pair | **partially_mapped** | center_pair | unknown |
| partially_mapped + mcs | partially_mapped | mcs | formal_mcs |

MCS/center-pair never produce `fully_mapped` — §10.5 "不伪装成 full atom
correspondence" enforced.

## 7. Real mapper integration status

| backend | available | status |
|---------|-----------|--------|
| rdkit | False | INTEGRATION_BLOCKED |
| rxnmapper | False | INTEGRATION_BLOCKED |
| rxn4chemistry | False | INTEGRATION_BLOCKED |

Integration test (`test_real_mapper_integration_handles_unavailable_backend`)
does NOT use `skipif`. When backend unavailable, the test verifies the adapter
raises `NotImplementedError` with `INTEGRATION_BLOCKED` marker — it passes
(no skip). This satisfies the zero-skip discipline while honestly reporting
the blocked state.

## 8. Regression

```
.venv/bin/python -m pytest tests -q -p no:cacheprovider -ra
→ 420 passed (290 P0 + 130 P1), 0 fail/error/skip/xfail/xpass
```

P1 breakdown: 26 (preflight) + 21 (T1 config+hashing) + 27 (T2 schemas) +
10 (T3 audit) + 30 (T4 mapping) + 16 (T2 domain extra) = 130.

Wait — actual P1 count: 420 - 290 = 130 P1 tests.

```
.venv/bin/python scripts/run_p0_gate.py
→ 10/10 passed (READY_FOR_CHATGPT_AUDIT), no regression
```

## 9. Deviations

- **execution model**: Qwen → Claude Code subagent (inherited from T1)
- **integration test approach**: brief Step 6 uses `@pytest.mark.skipif`.
  Replaced with a non-skip test that verifies `INTEGRATION_BLOCKED` behavior
  when backend unavailable (per user instruction: zero-skip discipline). The
  test still runs the real integration when `P1_REAL_MAPPER_AVAILABLE` env
  is set and the backend is importable — no coverage lost.
- **runtime capture**: §10.1 lists `runtime` in the capture list, but P0
  `MappingReport` has no `runtime` field (frozen, cannot modify). Captured
  `runtime_ms` in `mapper_parameters` instead (non-breaking, auditable).
- **timeout capture**: same — captured in `mapper_parameters["timeout"]`
  (string, per `dict[str, str]` schema).

## 10. Concerns

- **INTEGRATION_BLOCKED**: real mapper integration cannot run (rdkit absent).
  T4 is UNIT_CONTRACT_COMPLETE but NOT PASS. P1 Gate G04 (mapper integration)
  will not pass until rdkit/numpy/networkx/scipy are installed in `.venv`.
  To unblock: `uv pip install rdkit numpy networkx scipy` (or rxnmapper).
- **RealMapperAdapter skeleton**: even when a backend becomes available, the
  real mapping implementation (`_do_map`) is a skeleton. Wiring the real
  mapper is a follow-up task once the backend is installed.
- **FakeAtomMapper atom pairs are syntactic**: the deterministic atom pairs
  are not chemically correct — they are sufficient for contract testing
  (typed structure, determinism, formal/mechanistic separation) but do not
  validate real chemistry. This is intentional (fake mapper for unit tests).

## 11. To unblock T4 PASS

1. Install real mapper backend: `uv pip install rdkit numpy networkx scipy`
   (or `rxnmapper`, or `rxn4chemistry`)
2. Set `P1_REAL_MAPPER_AVAILABLE=rdkit` (or backend name)
3. Implement `RealMapperAdapter._do_map` (wire real backend → MappingReport)
4. Re-run integration test → verify `mapper_name != "fake"`
5. Re-generate `mapping_integration_sample.json` with real sample
6. Update verdict from INTEGRATION_BLOCKED to PASS
