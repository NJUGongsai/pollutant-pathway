"""P4 test isolation for the combined P7 tree.

The ported P4 gate / mutation tests run ``scripts/run_p4_gate.py`` and
``scripts/run_p4_mutations.py`` as subprocesses. Those scripts WRITE their
results to canonical on-disk paths under ``reports/p4/``:

- ``run_p4_gate.py`` writes ``P4_GATE_REPORT.json`` AND ``P4_GATE_REPORT.md``
- ``run_p4_mutations.py`` writes ``P4_MUTATION_RESULTS.json``

In the P4 source branch those were the gate's own current output (regenerated
each run, 14/14 PASS when real P3 input existed). In the combined P7 tree the
committed ``P4_GATE_REPORT.{json,md}`` are the AUTHORITATIVE real P4 verdict
(14/14 PASS from the P4 branch's final real run) and ``P4_GATE_REPORT.json``
is read by the P5 overwrite-guard
(``tests/p5/test_p5_gate_overwrite_guard.py::TestP5ImmuneToP4GateOverwrite``).

Running the ported P4 gate test here honestly produces a BLOCKED report
(G12-G14 blocked: no real P3 current-run artifact in this worktree), which
would clobber the committed 14/14 PASS report and trip the P5 guard. The
mutations runner likewise creates an untracked ``P4_MUTATION_RESULTS.json``.

Snapshot + restore those canonical files around every tests/p4 test: existing
files are restored to their pre-test content; files created by the test that
did not exist before are removed. The test still observes whatever the
subprocess writes DURING the test body (restore is teardown-only).
"""
from __future__ import annotations

from pathlib import Path

import pytest

_DEMOV2_ROOT = Path(__file__).resolve().parents[2]
_REPORTS_P4 = _DEMOV2_ROOT / "reports" / "p4"
_GUARDED_FILES = (
    "P4_GATE_REPORT.json",
    "P4_GATE_REPORT.md",
    "P4_MUTATION_RESULTS.json",
)


@pytest.fixture(autouse=True)
def _isolate_p4_canonical_reports():
    """Snapshot canonical P4 report files before each test; restore after.

    Restores pre-test content for files that existed; removes files the test
    created that did not exist before. No-op for tests that do not touch those
    files.
    """
    snapshot: dict[Path, bytes] = {}
    for name in _GUARDED_FILES:
        path = _REPORTS_P4 / name
        if path.exists():
            snapshot[path] = path.read_bytes()
    yield
    for name in _GUARDED_FILES:
        path = _REPORTS_P4 / name
        if path in snapshot:
            path.write_bytes(snapshot[path])
        elif path.exists():
            path.unlink()
