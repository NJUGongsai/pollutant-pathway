"""T6 RED tests — Contract/chaos: 10 failure categories, no uncaught leak.

Must FAIL (RED) until ``reaction_agent.mcp.secured`` / ``guards`` exist,
then PASS (GREEN).

final_plan §9.7 (T6 Contract/chaos) — ten categories:
  1. malformed          — non-dict / missing-required / bad-type payload
  2. unknown            — unknown tool / unknown field / unknown resource kind
  3. stale snapshot     — snapshot was available, then revoked
  4. missing resource   — run_id / evidence_id does not exist
  5. storage interruption — corrupt/half-written run file (atomic-write guard)
  6. budgets            — per-tenant cumulative budget exceeded
  7. concurrency        — identical dedup + cross-tenant isolation, no leak
  8. protocol mismatch  — wrong protocolVersion
  9. large payload      — payload above byte cap
 10. partial tool failure — create_run fails mid-path → no orphan idem record

Invariant for EVERY category: the failure surfaces as a typed ``P6Error``
subclass — never a raw uncaught exception, never a silent wrong-PASS.
"""
from __future__ import annotations

import threading

import pytest

from reaction_agent.mcp.errors import (
    BudgetExceededError,
    ForbiddenError,
    P6Error,
    PayloadTooLargeError,
    ProtocolError,
    ProtocolVersionMismatchError,
    RunNotFoundError,
    SchemaError,
    SnapshotUnavailableError,
    StorageError,
    UnauthorizedError,
)
from reaction_agent.mcp.guards import BudgetGuard
from reaction_agent.mcp.idempotency import IdempotencyStore
from reaction_agent.mcp.resources import AccessContext, ResourceURI, RetentionPolicy
from reaction_agent.mcp.runs import RunStore
from reaction_agent.mcp.secured import SecuredKernel
from reaction_agent.mcp.tools import (
    TOOL_EXPAND,
    TOOL_GET_EVIDENCE,
    TOOL_GET_RUN,
    TOOL_PREDICT,
)


def _predict_payload(smiles="CCO", key="k1", snap="s1"):
    return {"substrate_smiles": smiles, "idempotency_key": key, "snapshot_id": snap}


@pytest.fixture()
def secured(tmp_path):
    """Default chaos target: payload cap + protocol pin + permissive budget."""
    return SecuredKernel(
        run_store=RunStore(tmp_path / "runs"),
        idem_store=IdempotencyStore(tmp_path / "idem"),
        policy=RetentionPolicy(max_age_seconds=3600),
        payload_max_bytes=4096,
        protocol_version="p6-1",
        budget_guard=BudgetGuard(per_tenant_cap=1000),
    )


CTX = AccessContext(principal="a", tenant_id="t1")


# =====================================================================
# 1. malformed
# =====================================================================

class TestMalformed:
    def test_non_dict_payload_typed(self, secured):
        with pytest.raises(P6Error):
            secured.handle(TOOL_PREDICT, "not-a-dict", ctx=CTX)

    def test_missing_required_field_typed(self, secured):
        with pytest.raises(SchemaError):
            secured.handle(TOOL_PREDICT, {"substrate_smiles": "CCO"}, ctx=CTX)

    def test_bad_type_typed(self, secured):
        p = _predict_payload()
        p["substrate_smiles"] = 123
        with pytest.raises(SchemaError):
            secured.handle(TOOL_PREDICT, p, ctx=CTX)

    def test_empty_string_rejected(self, secured):
        p = _predict_payload()
        p["substrate_smiles"] = ""
        with pytest.raises(SchemaError):
            secured.handle(TOOL_PREDICT, p, ctx=CTX)


# =====================================================================
# 2. unknown
# =====================================================================

class TestUnknown:
    def test_unknown_tool_typed(self, secured):
        with pytest.raises((ProtocolError, P6Error)):
            secured.handle("reaction.bogus_v1", {}, ctx=CTX)

    def test_unknown_field_typed(self, secured):
        p = _predict_payload()
        p["mystery_field"] = "x"
        with pytest.raises(SchemaError):
            secured.handle(TOOL_PREDICT, p, ctx=CTX)

    def test_unknown_resource_kind_typed(self):
        with pytest.raises(P6Error):
            ResourceURI.parse("reactionagent://runs/run-1/secret")


# =====================================================================
# 3. stale snapshot
# =====================================================================

class TestStaleSnapshot:
    def test_snapshot_revoked_after_first_use(self, tmp_path):
        available = {"s1"}

        def snapshots(sid):
            return sid in available

        k = SecuredKernel(
            run_store=RunStore(tmp_path / "runs"),
            idem_store=IdempotencyStore(tmp_path / "idem"),
            policy=RetentionPolicy(max_age_seconds=3600),
            snapshots=snapshots,
        )
        # fresh snapshot → predict succeeds
        r1 = k.handle(TOOL_PREDICT, _predict_payload(snap="s1"), ctx=CTX)
        assert r1["run_id"]
        # snapshot goes stale → typed error, not a crash
        available.discard("s1")
        with pytest.raises(SnapshotUnavailableError):
            k.handle(TOOL_PREDICT, _predict_payload(snap="s1", key="k2"), ctx=CTX)

    def test_never_available_snapshot_typed(self, tmp_path):
        def snapshots(sid):
            return sid == "s1"

        k = SecuredKernel(
            run_store=RunStore(tmp_path / "runs"),
            idem_store=IdempotencyStore(tmp_path / "idem"),
            policy=RetentionPolicy(max_age_seconds=3600),
            snapshots=snapshots,
        )
        with pytest.raises(SnapshotUnavailableError):
            k.handle(TOOL_PREDICT, _predict_payload(snap="never"), ctx=CTX)


# =====================================================================
# 4. missing resource
# =====================================================================

class TestMissingResource:
    def test_get_run_missing_typed(self, secured):
        with pytest.raises(RunNotFoundError):
            secured.handle(TOOL_GET_RUN, {"run_id": "run-missing"}, ctx=CTX)

    def test_get_evidence_missing_run_typed(self, secured):
        with pytest.raises(RunNotFoundError):
            secured.handle(
                TOOL_GET_EVIDENCE,
                {"run_id": "run-missing", "evidence_id": "ev-1"},
                ctx=CTX,
            )

    def test_resolve_missing_uri_typed(self, secured):
        with pytest.raises(RunNotFoundError):
            secured.resolve_resource(
                "reactionagent://runs/run-missing/manifest", ctx=CTX
            )

    def test_expand_missing_parent_typed(self, secured):
        with pytest.raises(RunNotFoundError):
            secured.handle(
                TOOL_EXPAND,
                {
                    "run_id": "run-missing",
                    "evidence_id": "ev-1",
                    "idempotency_key": "exp-1",
                    "snapshot_id": "s1",
                },
                ctx=CTX,
            )


# =====================================================================
# 5. storage interruption
# =====================================================================

class TestStorageInterruption:
    def test_corrupt_run_file_typed(self, secured):
        run = secured.handle(TOOL_PREDICT, _predict_payload(), ctx=CTX)
        # corrupt the persisted run file (simulate interrupted write)
        path = secured._kernel.runs._run_path(run["run_id"])
        path.write_text("{broken", encoding="utf-8")
        with pytest.raises(StorageError):
            secured.handle(TOOL_GET_RUN, {"run_id": run["run_id"]}, ctx=CTX)

    def test_partial_tmp_file_never_read_as_valid(self, secured):
        run = secured.handle(TOOL_PREDICT, _predict_payload(), ctx=CTX)
        # a crashed writer leaves a .tmp file behind — must not surface as a run
        (secured._kernel.runs.root / "junk.tmp").write_text("partial", encoding="utf-8")
        ids = secured._kernel.runs.list_runs()
        assert "junk" not in ids
        assert run["run_id"] in ids

    def test_corrupt_resolve_typed(self, secured):
        run = secured.handle(TOOL_PREDICT, _predict_payload(), ctx=CTX)
        path = secured._kernel.runs._run_path(run["run_id"])
        path.write_text("not json", encoding="utf-8")
        with pytest.raises(StorageError):
            secured.resolve_resource(run["manifest_uri"], ctx=CTX)


# =====================================================================
# 6. budgets
# =====================================================================

class TestBudgets:
    def test_max_candidates_above_schema_limit_typed(self, secured):
        p = _predict_payload()
        p["budgets"] = {"max_candidates": 10000}  # schema max is 200
        with pytest.raises(SchemaError):
            secured.handle(TOOL_PREDICT, p, ctx=CTX)

    def test_cumulative_budget_exceeded(self, tmp_path):
        guard = BudgetGuard(per_tenant_cap=10)
        k = SecuredKernel(
            run_store=RunStore(tmp_path / "runs"),
            idem_store=IdempotencyStore(tmp_path / "idem"),
            policy=RetentionPolicy(max_age_seconds=3600),
            budget_guard=guard,
        )
        p1 = _predict_payload(key="k1")
        p1["budgets"] = {"max_candidates": 8}
        k.handle(TOOL_PREDICT, p1, ctx=CTX)  # spent 8
        p2 = _predict_payload(key="k2")
        p2["budgets"] = {"max_candidates": 5}  # 8 + 5 = 13 > 10
        with pytest.raises(BudgetExceededError):
            k.handle(TOOL_PREDICT, p2, ctx=CTX)

    def test_budget_exceeded_is_typed(self):
        assert issubclass(BudgetExceededError, P6Error)

    def test_budget_not_charged_on_idempotent_reuse(self, tmp_path):
        guard = BudgetGuard(per_tenant_cap=10)
        k = SecuredKernel(
            run_store=RunStore(tmp_path / "runs"),
            idem_store=IdempotencyStore(tmp_path / "idem"),
            policy=RetentionPolicy(max_age_seconds=3600),
            budget_guard=guard,
        )
        p = _predict_payload(key="k1")
        p["budgets"] = {"max_candidates": 6}
        k.handle(TOOL_PREDICT, p, ctx=CTX)  # spent 6
        # repeat identical → reuse, no new budget charge
        k.handle(TOOL_PREDICT, p, ctx=CTX)
        # now a different request that would push 6+5 over 10 must still be
        # rejected (reuse didn't silently charge 6 again to 12)
        p3 = _predict_payload(key="k2")
        p3["budgets"] = {"max_candidates": 5}
        with pytest.raises(BudgetExceededError):
            k.handle(TOOL_PREDICT, p3, ctx=CTX)


# =====================================================================
# 7. concurrency
# =====================================================================

class TestConcurrency:
    def test_concurrent_identical_one_run(self, secured):
        results = []
        lock = threading.Lock()

        def worker():
            r = secured.handle(TOOL_PREDICT, _predict_payload(), ctx=CTX)
            with lock:
                results.append(r)

        ts = [threading.Thread(target=worker) for _ in range(8)]
        for t in ts:
            t.start()
        for t in ts:
            t.join()
        ids = {r["run_id"] for r in results}
        assert len(ids) == 1
        assert len(secured._kernel.runs.list_runs()) == 1

    def test_concurrent_cross_tenant_isolated(self, secured):
        ctx_a = AccessContext(principal="a", tenant_id="ta")
        ctx_b = AccessContext(principal="b", tenant_id="tb")
        out = []
        lock = threading.Lock()

        def w(ctx, key):
            r = secured.handle(TOOL_PREDICT, _predict_payload(key=key), ctx=ctx)
            with lock:
                out.append((ctx.tenant_id, r["run_id"]))

        ts = [
            threading.Thread(target=w, args=(ctx_a, "ka")),
            threading.Thread(target=w, args=(ctx_b, "kb")),
        ]
        for t in ts:
            t.start()
        for t in ts:
            t.join()
        a_run = [r for t, r in out if t == "ta"][0]
        b_run = [r for t, r in out if t == "tb"][0]
        assert a_run != b_run
        # tenant a cannot resolve tenant b's manifest
        with pytest.raises(ForbiddenError):
            secured.resolve_resource(
                f"reactionagent://runs/{b_run}/manifest", ctx=ctx_a
            )


# =====================================================================
# 8. protocol mismatch
# =====================================================================

class TestProtocolMismatch:
    def test_wrong_protocol_version_typed(self, secured):
        with pytest.raises(ProtocolVersionMismatchError):
            secured.handle(
                TOOL_PREDICT, _predict_payload(), ctx=CTX, protocol_version="p6-0"
            )

    def test_protocol_mismatch_is_typed(self):
        assert issubclass(ProtocolVersionMismatchError, P6Error)

    def test_matching_protocol_ok(self, secured):
        out = secured.handle(
            TOOL_PREDICT, _predict_payload(), ctx=CTX, protocol_version="p6-1"
        )
        assert out["run_id"]


# =====================================================================
# 9. large payload
# =====================================================================

class TestLargePayload:
    def test_oversized_payload_typed(self, secured):
        p = _predict_payload()
        p["substrate_smiles"] = "C" * 5000  # payload cap is 4096 bytes
        with pytest.raises(PayloadTooLargeError):
            secured.handle(TOOL_PREDICT, p, ctx=CTX)

    def test_large_payload_is_typed(self):
        assert issubclass(PayloadTooLargeError, P6Error)


# =====================================================================
# 10. partial tool failure
# =====================================================================

class TestPartialToolFailure:
    def test_failed_create_run_leaves_no_orphan_idem(self, tmp_path):
        """create_run runs BEFORE the idem record is written (record_if_absent),
        so a mid-run failure cannot leave a committed idempotency record."""
        idem = IdempotencyStore(tmp_path / "idem")

        class PoisonedStore(RunStore):
            def create_run(self, *a, **k):
                raise StorageError("simulated mid-run failure")

        k = SecuredKernel(
            run_store=PoisonedStore(tmp_path / "poison"),
            idem_store=idem,
            policy=RetentionPolicy(max_age_seconds=3600),
        )
        with pytest.raises(StorageError):
            k.handle(TOOL_PREDICT, _predict_payload(), ctx=CTX)
        # no orphan idem record committed
        assert idem._read("k1") is None

    def test_no_uncaught_exception_any_chaos(self, secured):
        """Blanket: every chaos input raises a typed P6Error, never raw."""
        chaos = [
            (TOOL_PREDICT, "not-a-dict"),
            (TOOL_PREDICT, {"substrate_smiles": "CCO"}),  # missing idem
            ("reaction.bogus", {}),
            (TOOL_GET_RUN, {"run_id": "nope"}),
            (TOOL_EXPAND, {"run_id": "nope", "evidence_id": "e",
                           "idempotency_key": "x", "snapshot_id": "s1"}),
        ]
        for tool, payload in chaos:
            with pytest.raises(P6Error):
                secured.handle(tool, payload, ctx=CTX)

    def test_no_silent_open_access_when_secured(self, secured):
        # missing ctx on a read in secured mode → UnauthorizedError, not a leak
        run = secured.handle(TOOL_PREDICT, _predict_payload(), ctx=CTX)
        with pytest.raises(UnauthorizedError):
            secured.handle(TOOL_GET_RUN, {"run_id": run["run_id"]}, ctx=None)
