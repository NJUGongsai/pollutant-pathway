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
