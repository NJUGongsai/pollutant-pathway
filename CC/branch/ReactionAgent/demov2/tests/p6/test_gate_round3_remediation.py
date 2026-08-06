"""Gate P6 Round 3 — remediation RED tests (GATE-P6-07 path sanitization).

Must FAIL (RED) until the three-layer fix lands, then PASS (GREEN).

GATE-P6-07 (P0): client-controlled identifiers (run_id / evidence_id /
idempotency_key / snapshot_id / client_request_id / tenant_id) reached the
filesystem path unsanitized → read-side traversal leaked a bare KeyError
on a shape-mismatched JSON, and write-side traversal let os.replace land a
.json outside the store root (arbitrary .json write → gate-evidence
integrity risk).

Three layers must all hold:
  1. schema  — pattern on identifier fields (reject '/', '\\', leading '.')
  2. store   — _run_path / _path resolve()+containment (defense in depth,
              does not rely on schema for internal callers)
  3. parse   — get_run catches KeyError/TypeError on shape mismatch → StorageError
Plus AccessContext.tenant_id / .principal pattern (they enter effective_key
→ file name).

Four RED groups (kimi's closure condition): read-traversal typed /
write-traversal typed / shape-mismatch typed / legal-identifier regression.
"""
from __future__ import annotations

import pytest

from reaction_agent.mcp.errors import (
    P6Error,
    SchemaError,
    StorageError,
    UnauthorizedError,
)
from reaction_agent.mcp.idempotency import IdempotencyStore
from reaction_agent.mcp.resources import AccessContext, RetentionPolicy
from reaction_agent.mcp.runs import RunStore
from reaction_agent.mcp.secured import SecuredKernel
from reaction_agent.mcp.tools import TOOL_GET_RUN, TOOL_PREDICT


def _predict_payload(smiles="CCO", key="k1", snap="s1"):
    return {"substrate_smiles": smiles, "idempotency_key": key, "snapshot_id": snap}


@pytest.fixture()
def secured(tmp_path):
    return SecuredKernel(
        run_store=RunStore(tmp_path / "runs"),
        idem_store=IdempotencyStore(tmp_path / "idem"),
        policy=RetentionPolicy(max_age_seconds=3600),
    )


# =====================================================================
# Group 1 — read-side traversal: typed rejection, no bare KeyError leak
# =====================================================================

class TestReadTraversal:
    def test_get_run_traversal_typed(self, tmp_path):
        runs = RunStore(tmp_path / "runs")
        with pytest.raises(StorageError):
            runs.get_run("../foreign")

    def test_get_run_traversal_no_bare_keyerror(self, tmp_path):
        # kimi's probe: a shape-mismatched JSON planted at a traversed path
        # must surface as a typed StorageError, not a bare KeyError('run_id').
        runs = RunStore(tmp_path / "runs")
        planted = tmp_path / "foreign.json"  # outside the runs root
        planted.write_text('{"not_a_run": true}', encoding="utf-8")
        with pytest.raises(StorageError):
            runs.get_run("../foreign")  # resolves to tmp_path/foreign.json


# =====================================================================
# Group 2 — write-side traversal: typed rejection, no file escapes the root
# =====================================================================

class TestWriteTraversal:
    def test_idem_record_traversal_typed(self, tmp_path):
        idem = IdempotencyStore(tmp_path / "idem")
        with pytest.raises(StorageError):
            idem.record(key="../escaped", request_hash="h", run_id="r-1")

    def test_idem_record_traversal_no_file_escape(self, tmp_path):
        idem = IdempotencyStore(tmp_path / "idem")
        try:
            idem.record(key="../escaped", request_hash="h", run_id="r-1")
        except Exception:
            pass
        # nothing may have landed outside the idem root
        assert not (tmp_path / "escaped.json").exists()
        assert not (tmp_path.parent / "escaped.json").exists()

    def test_predict_traversal_key_rejected_by_schema(self, secured):
        ctx = AccessContext(principal="a", tenant_id="t1")
        with pytest.raises(SchemaError):
            secured.handle(
                TOOL_PREDICT,
                _predict_payload(key="../x"),
                ctx=ctx,
            )

    def test_predict_traversal_snapshot_rejected_by_schema(self, secured):
        ctx = AccessContext(principal="a", tenant_id="t1")
        with pytest.raises(SchemaError):
            secured.handle(
                TOOL_PREDICT,
                _predict_payload(snap="../x"),
                ctx=ctx,
            )

    def test_get_run_traversal_run_id_rejected_by_schema(self, secured):
        ctx = AccessContext(principal="a", tenant_id="t1")
        with pytest.raises(SchemaError):
            secured.handle(TOOL_GET_RUN, {"run_id": "../x"}, ctx=ctx)


# =====================================================================
# Group 3 — shape-mismatch: typed StorageError, never bare KeyError/TypeError
# =====================================================================

class TestShapeMismatch:
    def test_get_run_shape_mismatch_typed(self, tmp_path):
        runs = RunStore(tmp_path / "runs")
        # plant a valid-JSON, shape-mismatched record INSIDE the root
        (runs.root / "bad.json").write_text("{}", encoding="utf-8")
        with pytest.raises(StorageError):
            runs.get_run("bad")

    def test_get_run_missing_required_field_typed(self, tmp_path):
        runs = RunStore(tmp_path / "runs")
        (runs.root / "bad.json").write_text(
            '{"tool": "predict"}', encoding="utf-8"
        )  # missing run_id/request_hash/snapshot_id
        with pytest.raises(StorageError):
            runs.get_run("bad")

    def test_get_run_wrong_type_field_typed(self, tmp_path):
        runs = RunStore(tmp_path / "runs")
        # JSON is a valid array, not an object → from_dict's data["run_id"]
        # raises TypeError → must surface as typed StorageError, not bare.
        (runs.root / "bad.json").write_text("[1, 2, 3]", encoding="utf-8")
        with pytest.raises(StorageError):
            runs.get_run("bad")


# =====================================================================
# Group 4 — legal identifiers still work (no false positives)
# =====================================================================

class TestLegalIdentifiersRegression:
    def test_legal_predict_and_get(self, secured):
        ctx = AccessContext(principal="a", tenant_id="t1")
        out = secured.handle(
            TOOL_PREDICT, _predict_payload(key="k-1.abc", snap="snap_2"), ctx=ctx
        )
        assert out["run_id"]
        got = secured.handle(TOOL_GET_RUN, {"run_id": out["run_id"]}, ctx=ctx)
        assert got["run_id"] == out["run_id"]

    def test_legal_dotted_run_id_resolvable(self, secured):
        ctx = AccessContext(principal="a", tenant_id="t1")
        out = secured.handle(TOOL_PREDICT, _predict_payload(), ctx=ctx)
        # the content-addressed run_id is hex + 'run-' prefix → always legal
        manifest = secured.resolve_resource(out["manifest_uri"], ctx=ctx)
        assert manifest["run_id"] == out["run_id"]

    def test_legal_access_context(self):
        ctx = AccessContext(principal="agent-1", tenant_id="tenant_a.b")
        assert ctx.tenant_id == "tenant_a.b"


# =====================================================================
# AccessContext identifier sanitization (tenant_id enters effective_key)
# =====================================================================

class TestAccessContextSanitization:
    def test_traversal_tenant_id_rejected(self):
        with pytest.raises(UnauthorizedError):
            AccessContext(principal="a", tenant_id="../etc")

    def test_slash_in_tenant_id_rejected(self):
        with pytest.raises(UnauthorizedError):
            AccessContext(principal="a", tenant_id="t/x")

    def test_backslash_in_tenant_id_rejected(self):
        with pytest.raises(UnauthorizedError):
            AccessContext(principal="a", tenant_id="t\\x")

    def test_leading_dot_tenant_id_rejected(self):
        with pytest.raises(UnauthorizedError):
            AccessContext(principal="a", tenant_id=".hidden")

    def test_traversal_principal_rejected(self):
        with pytest.raises(UnauthorizedError):
            AccessContext(principal="../p", tenant_id="t1")
