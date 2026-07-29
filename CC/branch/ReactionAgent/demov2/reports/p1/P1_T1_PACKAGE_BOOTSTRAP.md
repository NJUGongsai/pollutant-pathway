# P1-T1 Package Bootstrap — Checkpoint Report

**Task:** P1-T1 Package bootstrap
**Status:** DONE_WITH_CONCERNS
**Date (UTC):** 2026-07-29
**Execution model:** Claude Code subagent (deviation: docs specify Qwen)

## Summary

P1-T1 extends the P0 schema skeleton into an installable, configurable, replayable P1
package: `BuildConfig` / `BuildInfo` (explicit config contract), `canonical_hash` /
`stable_id` (deterministic content addressing), `SourceRecordProvenance` + no-legacy-write
guard (provenance + write containment). No P2 business logic introduced.

## Deliverables

| File | Kind | Purpose |
|------|------|---------|
| `reaction_agent/config.py` | new | `BuildConfig`, `BuildInfo`, `get_build_info()` |
| `reaction_agent/hashing.py` | new | `canonical_hash()`, `stable_id()` |
| `reaction_agent/provenance.py` | new | `SourceRecordProvenance`, `assert_no_legacy_write()` |
| `reaction_agent/__init__.py` | modified | re-exports `get_build_info` / `BuildInfo` |
| `pyproject.toml` | modified | version 0.1.0 → 0.2.0, P1 dependency comment |
| `requirements.lock.txt` | new | `uv pip freeze` of `.venv` |
| `tests/p1/test_config.py` | new | 16 tests (config + provenance + security regression) |
| `tests/p1/test_hashing_ids.py` | new | 5 tests (hash determinism + stable ID) |

## Dependency Lock

**Decision:** Preflight (2026-07-29) judged BLOCKED — `rdkit` / `numpy` / `networkx` /
`scipy` all absent in `.venv`. Per user instruction, rdkit was NOT force-installed. T1
code requires only `pydantic` + stdlib (`json`, `hashlib`, `sys`, `os`), so no new runtime
dependencies were added.

**`pyproject.toml` dependencies:**
```toml
dependencies = [
    "pydantic>=2.8,<3",
    # P1: 按需添加，与 Python 3.11 兼容。未确认可装前不加。
    # Preflight (2026-07-29) 判 BLOCKED: rdkit/numpy/networkx/scipy 全 absent。
]
```

**`requirements.lock.txt`** generated via `uv pip freeze --python .venv/bin/python`
(`.venv` has no `pip`; `uv` is the equivalent manager). Contents (12 packages):

```
annotated-types==0.8.0
iniconfig==2.3.0
packaging==26.2
pluggy==1.6.0
pydantic==2.13.4
pydantic-core==2.46.4
pygments==2.20.0
pytest==9.1.1
pytest-json-report==1.5.0
pytest-metadata==3.1.1
typing-extensions==4.16.0
typing-inspection==0.4.2
```

**BLOCKED_DEPENDENCY_INSTALLATION:** `rdkit` / `numpy` / `networkx` / `scipy` absent.
User must supply these before T4 (atom mapper) and T6+ (graph/lineage) can proceed.
Recorded in worklog.

## no-legacy-write Guard

`assert_no_legacy_write(path)` in `reaction_agent/provenance.py` refuses writes to
`../benchmark`, `../core`, `../reports/p0`.

**Implementation (hardened after L2 security review):**
- Resolves input path to absolute real path via `os.path.realpath` (closes symlink
  bypass H1, path-traversal `../x/../x` normalization, double-slash `..//x`).
- Relative paths resolve against project root `demov2/` (not CWD) — closes CWD-relative
  bypass M4.
- Explicit `.lower()` on both resolved input and pre-resolved legacy dirs — closes
  macOS APFS case-insensitivity bypass H2. (`os.path.normcase` is a no-op on POSIX, so
  it alone does not fix H2; explicit lowercasing is conservative but safe for a guard.)
- Directory-boundary check `resolved == legacy or resolved.startswith(legacy + os.sep)`
  — eliminates substring false positives M3 (e.g. `reports/p1/benchmark_comparison.json`
  is no longer falsely blocked).

**Regression tests** (`tests/p1/test_config.py`):
- `test_legacy_write_refused` (happy path `../benchmark/...`)
- `test_legacy_write_bypass_vectors_refused` (parametrized: `../benchmark/../benchmark/...`,
  `..//benchmark/...`, `../core/x.json`, `../reports/p0/anything.json`)
- `test_legacy_write_case_variant_refused` (`../Benchmark/...` — H2)
- `test_legacy_write_substring_false_positive_allowed` (`reports/p1/benchmark_comparison.json` — M3)
- `test_legacy_write_demov2_reports_p1_allowed` (`reports/p1/P1_T1_PACKAGE_BOOTSTRAP.md`)
- `test_demov2_write_allowed` (`reports/p1/x.json`)

## Redaction / Secret Safety

- No `logging`, no `print`, no API-key/token fields in `config.py` / `hashing.py` /
  `provenance.py`. Confirmed by L2 security-reviewer.
- `BuildConfig.canonical_json()` emits `model_dump(mode="json")` with `sort_keys=True` —
  deterministic, no timestamp, no temp-path fields on the model. Cross-run stable.
- `canonical_hash()` does not inject timestamps or temp paths; it canonicalizes the
  caller-supplied object only.
- No hardcoded absolute paths or credentials. Only hardcoded strings are version
  constants in `get_build_info()` and relative legacy prefixes in `provenance.py`.

## Version Endpoint (实测)

```
>>> import reaction_agent
>>> reaction_agent.get_build_info().model_dump()
{'package_version': '0.2.0',
 'schema_version': 'p1-1',
 'mapper_resolver_version': 'p1-1',
 'ledger_version': 'p1-1',
 'policy_version': 'p1-1',
 'python_version': '3.11.15'}
```

`reaction_agent.get_build_info` (re-exported from `__init__.py`) and
`reaction_agent.config.get_build_info` both resolve to the same function.

## Test Results

| Suite | Count | Status |
|-------|-------|--------|
| `tests/contracts` (P0) | 290 | passed |
| `tests/p1/test_p1_preflight.py` (Task 0) | 26 | passed |
| `tests/p1/test_config.py` (T1 new) | 16 | passed |
| `tests/p1/test_hashing_ids.py` (T1 new) | 5 | passed |
| **Total** | **337** | **passed, 0 fail/skip/xfail/xpass** |

**P0 Gate:** 10/10 passed (`READY_FOR_CHATGPT_AUDIT`). No regression.

## TDD Evidence

| Step | RED | GREEN |
|------|-----|-------|
| config | 1 error (ModuleNotFoundError: reaction_agent.config) | 5 passed |
| hashing | 1 error (ModuleNotFoundError: reaction_agent.hashing) | 5 passed |
| provenance | 1 error (ModuleNotFoundError: reaction_agent.provenance) | 16 passed (incl. 7 security regression) |

## Deviations

1. **`get_build_info` python_version fix:** brief code `".".join(sys.version_info[:3])`
   raises `TypeError` (tuple of ints). Fixed to `".".join(str(x) for x in sys.version_info[:3])`.
   Test contract unchanged.
2. **Strict TDD reorder:** brief Step 9 implements `provenance.py` before Step 10 appends
   tests; user instruction mandates test-first. Reordered: tests appended → RED → impl → GREEN.
3. **Security hardening of `assert_no_legacy_write`:** brief's string-prefix matching was
   vulnerable to symlink (H1), case (H2), CWD-relative (M4) bypass and substring
   false-positive (M3). Replaced with resolved-realpath + explicit-lowercase directory
   boundary check. Added 7 regression tests. (CRITICAL/HIGH must-fix per brief Step 13.)
4. **`__init__.py` re-export:** brief file list says "extend `__init__.py`, add
   `get_build_info`"; brief Step 3 defines it in `config.py`. Both satisfied: defined in
   `config.py`, re-exported from `__init__.py`.
5. **Execution model:** Claude Code (docs specify Qwen). Recorded per user instruction.
6. **`pyproject.toml` version bump:** 0.1.0 → 0.2.0 to align with
   `BuildInfo.package_version="0.2.0"`. Gate does not check pyproject version; no regression.

## Concerns (deferred, non-blocking for T2)

- **M1 (mapper_parameters):** `BuildConfig.mapper_parameters: dict[str, str]` is
  unconstrained — a caller could store API keys, which would flow into `canonical_json`.
  No secret-key rejection at schema level. T2+ should add a `@field_validator` rejecting
  `*_key` / `*_token` / `password` / `authorization` keys, or split into a typed submodel.
  Low risk for T1 (no caller yet).
- **M2 (canonical_hash `default=str`):** `json.dumps(..., default=str)` silently
  stringifies `datetime` / `pathlib.Path` / custom objects, which could let temp paths or
  timestamps into a content-addressed hash without error. Kept per brief's design (needed
  for robustness with Enums/pydantic models). T2+ should consider scoping allowed types or
  removing `default=str` if callers are expected to pre-serialize.
- **L1 (stable_id 48-bit):** `stable_id` truncates SHA-256 to 12 hex chars (48 bits).
  Collision probability rises at ~16M items. Acceptable for P1; revisit if the evidence
  space grows beyond millions of records.

## Next Authorization

T1 exit criteria met (dependency lock + no-legacy-write guard in place). T2 may proceed.
T4 (atom mapper) and T6+ (graph/lineage) remain blocked on `rdkit` / `networkx` install
(BLOCKED_DEPENDENCY_INSTALLATION).
