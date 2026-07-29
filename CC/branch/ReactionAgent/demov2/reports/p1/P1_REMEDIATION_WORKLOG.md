# P1 Remediation Worklog

## Preflight (Task 0)
- timestamp: 2026-07-29T12:25:37.508203+00:00
- assumptions:
  - P0 baseline green (290 passed + Gate 10/10, see `P1_BASELINE.json`)
  - P0 baseline commit `a96b763` is HEAD and unmodified
  - execution model = Claude Code subagent (deviation, originally Qwen per docs)
- input files/hashes:
  - `tests/contracts/` (290 contract tests, P0 frozen)
  - `scripts/run_p0_gate.py` (P0 Gate v3 runner)
  - `../benchmark/canonical_identity.py` sha256=`6003f4bc4ffc5ca3304dc1d2282a467f4f773e149ea9cf2a132ca0e4079eb2d0` (read-only legacy)
- deviations:
  - execution model Qwen → Claude Code subagent (user decision, recorded per brief)
  - `legacy_inventory()` path resolution: brief uses 3 `dirname()` calls for `root`
    which resolves to `.../branch/` (contradicts its own comment
    `# CC/branch/ReactionAgent`). Fixed to 2 `dirname()` calls so `parent`
    correctly resolves to `.../ReactionAgent/` where `../benchmark` and `../core`
    actually live. All data values (PROLINE_2OG_CASE, status names, stop-condition
    logic) are verbatim from the brief.
- preflight status: BLOCKED
- blockers:
  - `rdkit_absent` — rdkit/numpy/networkx/scipy all absent in `.venv`
  - `real_reaction_source_not_confirmed` — no RHEA/BRENDA/MetaCyc source configured
  - `required_case_missing` — proline/2OG source record not provided
- next task authorization: BLOCKED — T1 implementation NOT authorized for real-data work.
  Only read-only scaffolding + fixture unit tests may proceed. User must supply:
  1. Real reaction data source (path/ID for RHEA/BRENDA/MetaCyc, or legacy-data confirmation)
  2. Atom mapper package name (decides `mapper_backend` + T4 viability)
  3. Second annotator (if T6 inter-annotator agreement required)
  4. Proline/2OG source record (e.g. RHEA ID) to bind the canonical case

## TDD evidence
- RED: `tests/p1/test_p1_preflight.py` → 26 errors (ModuleNotFoundError) before implementation
- GREEN: `tests/p1/test_p1_preflight.py` → 26 passed after `scripts/p1_preflight.py` created
- Full suite regression: 316 passed (290 P0 + 26 P1), 0 failed/skipped

## T1: Package bootstrap
- timestamp: 2026-07-29T12:50:43Z (UTC)
- assumptions:
  - P0 baseline green and locked (290 passed + Gate 10/10, commit `a96b763`)
  - Preflight BLOCKED: rdkit/numpy/networkx/scipy absent; only pydantic + pytest available
  - T1 code requires only pydantic + stdlib (json/hashlib/sys/os); no new runtime deps needed
  - `.venv` has no `pip`; use `uv pip freeze` as equivalent for lock generation
  - All new schemas inherit `StrictModel` (extra="forbid", strict=True) per P0 freeze
- RED:
  - `tests/p1/test_config.py` → 1 error (ModuleNotFoundError: reaction_agent.config)
  - `tests/p1/test_hashing_ids.py` → 1 error (ModuleNotFoundError: reaction_agent.hashing)
  - provenance tests (appended to test_config.py) → 1 error (ModuleNotFoundError: reaction_agent.provenance)
- impl:
  - `reaction_agent/config.py`: `BuildConfig` (12 fields, `canonical_json()`), `BuildInfo`, `get_build_info()`
  - `reaction_agent/hashing.py`: `canonical_hash()` (SHA-256, sorted keys, _canonicalize), `stable_id()` (`<prefix>_<hash12>`)
  - `reaction_agent/provenance.py`: `SourceRecordProvenance` (7 required fields), `assert_no_legacy_write()` (hardened)
  - `reaction_agent/__init__.py`: re-exports `get_build_info`, `BuildInfo`
  - `pyproject.toml`: version 0.1.0 → 0.2.0; deps unchanged (pydantic only); P1 comment added
  - `requirements.lock.txt`: `uv pip freeze` (12 packages, no rdkit/numpy/networkx/scipy)
- GREEN:
  - `tests/p1/test_config.py` → 16 passed (5 config + 4 provenance + 7 security regression)
  - `tests/p1/test_hashing_ids.py` → 5 passed
- regression:
  - `tests/contracts tests/p1` → 337 passed (290 P0 + 47 P1), 0 fail/error/skip/xfail/xpass
  - P0 Gate → 10/10 passed (READY_FOR_CHATGPT_AUDIT), no regression
- L2 security-review:
  - 0 CRITICAL, 2 HIGH (H1 symlink bypass, H2 macOS case bypass), 5 MEDIUM, 3 LOW
  - H1/H2/M3/M4 fixed: replaced string-prefix matching with realpath + explicit `.lower()`
    + directory-boundary check; `os.path.normcase` is no-op on POSIX so explicit lowercasing
    required for H2. Added 7 regression tests.
  - M1 (mapper_parameters unconstrained), M2 (canonical_hash default=str), L1 (stable_id 48-bit)
    deferred as non-blocking concerns; documented in checkpoint report.
- deviations:
  - execution model Qwen → Claude Code subagent (user decision)
  - `get_build_info` python_version: brief code `".".join(sys.version_info[:3])` raises
    TypeError (tuple of ints); fixed to `".".join(str(x) for x in sys.version_info[:3])`
  - strict TDD reorder: provenance tests appended before impl (brief Step 9 impl before
    Step 10 tests; user instruction mandates test-first)
  - `assert_no_legacy_write` hardened beyond brief's string matching (CRITICAL/HIGH must-fix)
  - `__init__.py` re-exports `get_build_info` (brief file list says extend; Step 3 defines
    in config.py — both satisfied)
  - pyproject version bumped 0.1.0 → 0.2.0 to align with BuildInfo.package_version
  - `requirements.lock.txt` generated via `uv pip freeze` (not `pip freeze` — `.venv` has no pip)
- BLOCKED_DEPENDENCY_INSTALLATION: rdkit/numpy/networkx/scipy absent. Not force-installed
  per user instruction. Blocks T4 (atom mapper) and T6+ (graph/lineage). T2 may proceed.
- next task authorization: T2 authorized (T1 exit criteria met: dependency lock +
  no-legacy-write guard in place)
