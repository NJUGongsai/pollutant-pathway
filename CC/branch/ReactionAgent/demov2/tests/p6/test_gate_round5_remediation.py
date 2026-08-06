"""Gate P6 Round 5 — remediation RED tests (GATE-P6-09 field type confusion).

Must FAIL (RED) until RunRecord.from_dict validates field types, then PASS.

GATE-P6-09 (P1): from_dict validated shape (missing keys / non-object via
G7) but not field TYPES. A run file with a legit shape but a mistyped
``expires_at`` (e.g. a string — chaos cat 5 bit-rot / cross-version drift
form) flowed into ``RetentionPolicy.is_expired``'s ``>`` comparison and
raised a bare ``TypeError`` through resolve() and sweep(). Same family as
G7/G8 but the "post-load field-type confusion" subclass.

kimi's exhaustive enumeration: ``expires_at`` is the ONLY RunRecord field
that flows into arithmetic/sort comparison (is_expired + sweep sort).
Idem fields have no arithmetic sites (G8 closed shape). guards spent/
requested are isinstance-filtered. ⇒ fixing the expires_at load-boundary
type check structurally closes the whole family — no sixth subclass.

Four RED pin groups (kimi's closure condition):
- expires_at string → resolve typed + sweep survives
- expires_at bool → load typed
- mixed-type survivors sort does not crash
- legal numeric/None regression
"""
from __future__ import annotations

import json

import pytest

from reaction_agent.mcp.errors import StorageError
from reaction_agent.mcp.idempotency import IdempotencyStore
from reaction_agent.mcp.resources import AccessContext, RetentionPolicy
from reaction_agent.mcp.runs import RunStore
from reaction_agent.mcp.secured import SecuredKernel


def _secured(tmp_path, **kw):
    return SecuredKernel(
        run_store=RunStore(tmp_path / "runs"),
        idem_store=IdempotencyStore(tmp_path / "idem"),
        policy=RetentionPolicy(max_age_seconds=3600, **kw),
    )


def _plant_run(runs, run_id, overrides=None):
    rec = {
        "run_id": run_id, "tool": "predict", "request_hash": "h",
        "snapshot_id": "s1", "payload": {}, "freeze_state": "frozen",
        "created_at": "1970-01-01T00:00:00Z", "tenant_id": "t1",
        "expires_at": None,
    }
    if overrides:
        rec.update(overrides)
    (runs.root / f"{run_id}.json").write_text(json.dumps(rec), encoding="utf-8")


# =====================================================================
# Group 1 — expires_at string: resolve typed + sweep survives
# =====================================================================

class TestG9ExpiresAtString:
    def test_resolve_typed(self, tmp_path):
        runs = RunStore(tmp_path / "runs")
        _plant_run(runs, "r1", {"expires_at": "not-a-float"})
        sec = _secured(tmp_path)
        ctx = AccessContext(principal="a", tenant_id="t1")
        with pytest.raises(StorageError):
            sec.resolve_resource("reactionagent://runs/r1/manifest", ctx=ctx)

    def test_sweep_no_crash_and_cleans(self, tmp_path):
        runs = RunStore(tmp_path / "runs")
        _plant_run(runs, "r1", {"expires_at": "not-a-float"})
        sec = _secured(tmp_path)
        sec.sweep()  # must not raise TypeError
        assert "r1" not in runs.list_runs()


# =====================================================================
# Group 2 — expires_at bool: load typed (bool is int subclass, must reject)
# =====================================================================

class TestG9ExpiresAtBool:
    def test_load_typed(self, tmp_path):
        runs = RunStore(tmp_path / "runs")
        _plant_run(runs, "r1", {"expires_at": True})
        with pytest.raises(StorageError):
            runs.get_run("r1")


# =====================================================================
# Group 3 — mixed-type survivors: sweep sort must not crash
# =====================================================================

class TestG9MixedTypeSort:
    def test_sort_no_crash(self, tmp_path):
        runs = RunStore(tmp_path / "runs")
        _plant_run(runs, "r0", {"expires_at": 1000.0})
        _plant_run(runs, "r1", {"expires_at": "bad"})
        _plant_run(runs, "r2", {"expires_at": None})
        sec = _secured(tmp_path)
        sec.sweep()  # must not raise TypeError on is_expired or sort
        assert "r1" not in runs.list_runs()  # bad record cleared


# =====================================================================
# Group 4 — legal numeric / None regression
# =====================================================================

class TestG9LegalRegression:
    def test_legal_numeric_expires_at(self, tmp_path):
        runs = RunStore(tmp_path / "runs")
        _plant_run(runs, "r1", {"expires_at": 1000.0})
        rec = runs.get_run("r1")
        assert rec.expires_at == 1000.0

    def test_legal_none_expires_at(self, tmp_path):
        runs = RunStore(tmp_path / "runs")
        _plant_run(runs, "r1", {"expires_at": None})
        rec = runs.get_run("r1")
        assert rec.expires_at is None

    def test_legal_resolve_fresh_run(self, tmp_path):
        runs = RunStore(tmp_path / "runs")
        _plant_run(runs, "r1", {"expires_at": 9999999999.0})  # far future
        sec = _secured(tmp_path)
        ctx = AccessContext(principal="a", tenant_id="t1")
        out = sec.resolve_resource("reactionagent://runs/r1/manifest", ctx=ctx)
        assert out["run_id"] == "r1"
