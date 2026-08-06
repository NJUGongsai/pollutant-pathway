"""Gate P6 Round 4 — remediation RED tests (GATE-P6-08 idem shape mismatch).

Must FAIL (RED) until _read's except tuple gains TypeError, then PASS.

GATE-P6-08 (P1): ``idempotency._read`` caught ``(JSONDecodeError, OSError,
KeyError)`` but NOT ``TypeError``. A corrupt idem record that is valid JSON
but not an object (e.g. an array ``[1,2,3]`` — chaos cat 5 storage-
interruption form) made ``data["key"]`` raise a bare ``TypeError`` that
leaked through ``handle()`` (replay path) and ``sweep()``. Same defect class
as G7's ``runs.get_run`` fix, missed in Round 3 on the adjacent function.

Two RED pin groups (kimi's closure condition):
- replay: array / string idem file → typed StorageError (no bare TypeError)
- sweep: does not crash and clears the bad record
"""
from __future__ import annotations

import pytest

from reaction_agent.mcp.errors import StorageError
from reaction_agent.mcp.idempotency import IdempotencyStore
from reaction_agent.mcp.resources import AccessContext, RetentionPolicy
from reaction_agent.mcp.runs import RunStore
from reaction_agent.mcp.secured import SecuredKernel
from reaction_agent.mcp.tools import TOOL_PREDICT


def _predict_payload(smiles="CCO", key="k1", snap="s1"):
    return {"substrate_smiles": smiles, "idempotency_key": key, "snapshot_id": snap}


def _secured(tmp_path):
    return SecuredKernel(
        run_store=RunStore(tmp_path / "runs"),
        idem_store=IdempotencyStore(tmp_path / "idem"),
        policy=RetentionPolicy(max_age_seconds=3600),
    )


def _corrupt_idem(sec, key, body):
    """Overwrite the persisted idem record for ``key`` (tenant t1) with ``body``."""
    idem = sec._kernel.idem
    path = idem._path(f"t1:{key}")  # effective_key in secured mode
    path.write_text(body, encoding="utf-8")


class TestG8IdemShapeMismatchReplay:
    """Replay path: record_if_absent fast-path _read must not leak TypeError."""

    def test_replay_array_idem_typed(self, tmp_path):
        sec = _secured(tmp_path)
        ctx = AccessContext(principal="a", tenant_id="t1")
        sec.handle(TOOL_PREDICT, _predict_payload(key="k1"), ctx=ctx)
        _corrupt_idem(sec, "k1", "[1, 2, 3]")
        with pytest.raises(StorageError):
            sec.handle(TOOL_PREDICT, _predict_payload(key="k1"), ctx=ctx)

    def test_replay_string_idem_typed(self, tmp_path):
        sec = _secured(tmp_path)
        ctx = AccessContext(principal="a", tenant_id="t1")
        sec.handle(TOOL_PREDICT, _predict_payload(key="k1"), ctx=ctx)
        _corrupt_idem(sec, "k1", '"not-an-object"')
        with pytest.raises(StorageError):
            sec.handle(TOOL_PREDICT, _predict_payload(key="k1"), ctx=ctx)


class TestG8IdemShapeMismatchSweep:
    """Sweep path: must not crash on a bad idem record, and must clear it."""

    def test_sweep_array_idem_no_crash_and_cleans(self, tmp_path):
        sec = _secured(tmp_path)
        ctx = AccessContext(principal="a", tenant_id="t1")
        sec.handle(TOOL_PREDICT, _predict_payload(key="k1"), ctx=ctx)
        _corrupt_idem(sec, "k1", "[1, 2, 3]")
        sec.sweep()  # must not raise TypeError
        assert "t1:k1" not in sec._kernel.idem.list_keys()

    def test_sweep_string_idem_no_crash_and_cleans(self, tmp_path):
        sec = _secured(tmp_path)
        ctx = AccessContext(principal="a", tenant_id="t1")
        sec.handle(TOOL_PREDICT, _predict_payload(key="k1"), ctx=ctx)
        _corrupt_idem(sec, "k1", '"not-an-object"')
        sec.sweep()
        assert "t1:k1" not in sec._kernel.idem.list_keys()
