"""T5 RED tests — Resources: opaque URI, access control, tenant binding, retention.

Must FAIL (RED) until ``reaction_agent.mcp.resources`` / ``secured`` /
``guards`` exist, then PASS (GREEN).

final_plan §9.6 (T5 Resources):
- Opaque URI (``reactionagent://runs/...``) — agents must NOT derive URIs
  (RUN_INVARIANT ``resource_uris_opaque``); resolution goes through an
  access-control layer that parses the URI and authorizes the caller.
- Access control — every resource read requires an ``AccessContext``;
  no/invalid context → ``UnauthorizedError`` (fail-closed, never silent open).
- Tenant binding — runs are scoped to a tenant; cross-tenant reads/writes →
  ``ForbiddenError``.
- Retention — runs carry ``expires_at``; expired → ``ResourceExpiredError``;
  ``sweep()`` purges expired/over-cap runs.

Layered design: ``SecuredKernel`` wraps the Phase-A ``ReactionMCPKernel``
with an optional ``RetentionPolicy``; when a policy is configured the kernel
runs in *secured mode* (ctx required, tenant stamped/checked). Phase A's 53
tests use no policy → unchanged behavior.
"""
from __future__ import annotations

import threading

import pytest

from reaction_agent.mcp.errors import (
    ForbiddenError,
    P6Error,
    ResourceExpiredError,
    RunNotFoundError,
    UnauthorizedError,
)
from reaction_agent.mcp.idempotency import IdempotencyStore
from reaction_agent.mcp.resources import (
    AccessContext,
    ResourceManager,
    ResourceURI,
    RetentionPolicy,
)
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
    """Secured kernel with a permissive time-based retention policy."""
    return SecuredKernel(
        run_store=RunStore(tmp_path / "runs"),
        idem_store=IdempotencyStore(tmp_path / "idem"),
        policy=RetentionPolicy(max_age_seconds=3600),
        protocol_version="p6-1",
    )


def _ctx(tenant="t1", principal="a"):
    return AccessContext(principal=principal, tenant_id=tenant)


# =====================================================================
# Opaque URI — parse / render / reject
# =====================================================================

class TestOpaqueURI:
    def test_manifest_uri_roundtrip(self):
        uri = ResourceURI(run_id="run-abc", kind="manifest")
        s = uri.render()
        assert s == "reactionagent://runs/run-abc/manifest"
        parsed = ResourceURI.parse(s)
        assert parsed.run_id == "run-abc"
        assert parsed.kind == "manifest"
        assert parsed.evidence_id is None

    def test_evidence_uri_roundtrip(self):
        uri = ResourceURI(run_id="run-abc", kind="evidence", evidence_id="ev-1")
        s = uri.render()
        assert s == "reactionagent://runs/run-abc/evidence/ev-1"
        parsed = ResourceURI.parse(s)
        assert parsed.run_id == "run-abc"
        assert parsed.kind == "evidence"
        assert parsed.evidence_id == "ev-1"

    def test_unknown_scheme_rejected(self):
        with pytest.raises(P6Error):
            ResourceURI.parse("https://example.com/runs/run-1/manifest")

    def test_malformed_path_rejected(self):
        with pytest.raises(P6Error):
            ResourceURI.parse("reactionagent://not-runs/run-1/manifest")

    def test_unknown_resource_kind_rejected(self):
        with pytest.raises(P6Error):
            ResourceURI.parse("reactionagent://runs/run-1/secret")

    def test_truncated_uri_rejected(self):
        with pytest.raises(P6Error):
            ResourceURI.parse("reactionagent://runs/run-1")

    def test_uri_is_opaque_no_external_derivation(self):
        # A caller cannot mint a valid URI for an arbitrary run_id by string
        # construction alone — resolution still requires authorization.
        # (URI possession is NOT a capability.)
        uri = ResourceURI(run_id="run-x", kind="manifest")
        assert uri.render().startswith("reactionagent://runs/run-x/manifest")


# =====================================================================
# Access control — fail-closed
# =====================================================================

class TestAccessControl:
    def test_resolve_without_context_unauthorized(self, secured):
        run = secured.handle(TOOL_PREDICT, _predict_payload(), ctx=_ctx())
        with pytest.raises(UnauthorizedError):
            secured.resolve_resource(run["manifest_uri"], ctx=None)

    def test_owner_tenant_can_read(self, secured):
        ctx = _ctx()
        run = secured.handle(TOOL_PREDICT, _predict_payload(), ctx=ctx)
        out = secured.resolve_resource(run["manifest_uri"], ctx=ctx)
        assert out["run_id"] == run["run_id"]

    def test_cross_tenant_resolve_forbidden(self, secured):
        owner = _ctx(tenant="t1")
        intruder = _ctx(tenant="t2")
        run = secured.handle(TOOL_PREDICT, _predict_payload(), ctx=owner)
        with pytest.raises(ForbiddenError):
            secured.resolve_resource(run["manifest_uri"], ctx=intruder)

    def test_get_run_cross_tenant_forbidden(self, secured):
        owner = _ctx(tenant="t1")
        intruder = _ctx(tenant="t2")
        run = secured.handle(TOOL_PREDICT, _predict_payload(), ctx=owner)
        with pytest.raises(ForbiddenError):
            secured.handle(TOOL_GET_RUN, {"run_id": run["run_id"]}, ctx=intruder)

    def test_get_evidence_cross_tenant_forbidden(self, secured):
        owner = _ctx(tenant="t1")
        intruder = _ctx(tenant="t2")
        run = secured.handle(TOOL_PREDICT, _predict_payload(), ctx=owner)
        with pytest.raises(ForbiddenError):
            secured.handle(
                TOOL_GET_EVIDENCE,
                {"run_id": run["run_id"], "evidence_id": "ev-1"},
                ctx=intruder,
            )

    def test_secured_mode_requires_ctx(self, secured):
        # policy configured → ctx required (fail-closed), never silent open
        with pytest.raises(UnauthorizedError):
            secured.handle(TOOL_PREDICT, _predict_payload(), ctx=None)

    def test_resolve_evidence_owner_ok(self, secured):
        ctx = _ctx()
        run = secured.handle(TOOL_PREDICT, _predict_payload(), ctx=ctx)
        uri = f"reactionagent://runs/{run['run_id']}/evidence/ev-1"
        out = secured.resolve_resource(uri, ctx=ctx)
        assert out["evidence_id"] == "ev-1"


# =====================================================================
# Tenant binding — mutations stamp, reads enforce
# =====================================================================

class TestTenantBinding:
    def test_predict_stamps_tenant(self, secured):
        ctx = _ctx()
        run = secured.handle(TOOL_PREDICT, _predict_payload(), ctx=ctx)
        rec = secured._kernel.runs.get_run(run["run_id"])
        assert rec.tenant_id == "t1"

    def test_expand_cross_tenant_denied(self, secured):
        owner = _ctx(tenant="t1")
        intruder = _ctx(tenant="t2")
        parent = secured.handle(TOOL_PREDICT, _predict_payload(), ctx=owner)
        with pytest.raises(ForbiddenError):
            secured.handle(
                TOOL_EXPAND,
                {
                    "run_id": parent["run_id"],
                    "evidence_id": "ev-1",
                    "idempotency_key": "exp-1",
                    "snapshot_id": "s1",
                },
                ctx=intruder,
            )

    def test_expand_child_inherits_tenant(self, secured):
        ctx = _ctx()
        parent = secured.handle(TOOL_PREDICT, _predict_payload(), ctx=ctx)
        child = secured.handle(
            TOOL_EXPAND,
            {
                "run_id": parent["run_id"],
                "evidence_id": "ev-1",
                "idempotency_key": "exp-1",
                "snapshot_id": "s1",
            },
            ctx=ctx,
        )
        crec = secured._kernel.runs.get_run(child["child_run_id"])
        assert crec.tenant_id == "t1"
        assert crec.parent_run_id == parent["run_id"]

    def test_two_tenants_isolated_runs(self, secured):
        a = _ctx(tenant="ta")
        b = _ctx(tenant="tb")
        ra = secured.handle(TOOL_PREDICT, _predict_payload(key="ka"), ctx=a)
        rb = secured.handle(TOOL_PREDICT, _predict_payload(key="kb", smiles="CCC"), ctx=b)
        assert ra["run_id"] != rb["run_id"]
        # tenant a cannot resolve b's manifest
        with pytest.raises(ForbiddenError):
            secured.resolve_resource(rb["manifest_uri"], ctx=a)


# =====================================================================
# Retention — time-based expiry + sweep
# =====================================================================

class TestRetention:
    def test_expired_run_resolve_denied(self, tmp_path):
        clock = {"now": 1000.0}
        policy = RetentionPolicy(max_age_seconds=10, clock=lambda: clock["now"])
        k = SecuredKernel(
            run_store=RunStore(tmp_path / "runs"),
            idem_store=IdempotencyStore(tmp_path / "idem"),
            policy=policy,
        )
        ctx = _ctx()
        run = k.handle(TOOL_PREDICT, _predict_payload(), ctx=ctx)
        clock["now"] += 100  # past TTL
        with pytest.raises(ResourceExpiredError):
            k.resolve_resource(run["manifest_uri"], ctx=ctx)

    def test_sweep_removes_expired(self, tmp_path):
        clock = {"now": 1000.0}
        policy = RetentionPolicy(max_age_seconds=10, clock=lambda: clock["now"])
        k = SecuredKernel(
            run_store=RunStore(tmp_path / "runs"),
            idem_store=IdempotencyStore(tmp_path / "idem"),
            policy=policy,
        )
        ctx = _ctx()
        k.handle(TOOL_PREDICT, _predict_payload(key="k1"), ctx=ctx)
        k.handle(TOOL_PREDICT, _predict_payload(key="k2", smiles="CCC"), ctx=ctx)
        clock["now"] += 100
        removed = k.sweep()
        assert removed == 2
        assert k._kernel.runs.list_runs() == []

    def test_count_cap_sweep_removes_oldest(self, tmp_path):
        clock = {"now": 1000.0}
        policy = RetentionPolicy(max_age_seconds=100, max_runs=2, clock=lambda: clock["now"])
        k = SecuredKernel(
            run_store=RunStore(tmp_path / "runs"),
            idem_store=IdempotencyStore(tmp_path / "idem"),
            policy=policy,
        )
        ctx = _ctx()
        for i in range(3):
            k.handle(TOOL_PREDICT, _predict_payload(key=f"k{i}", smiles=f"C{i}"), ctx=ctx)
            clock["now"] += 1  # distinct expires_at → deterministic oldest-first
        removed = k.sweep()
        assert removed == 1
        assert len(k._kernel.runs.list_runs()) == 2

    def test_fresh_run_resolves_ok(self, tmp_path):
        clock = {"now": 1000.0}
        policy = RetentionPolicy(max_age_seconds=100, clock=lambda: clock["now"])
        k = SecuredKernel(
            run_store=RunStore(tmp_path / "runs"),
            idem_store=IdempotencyStore(tmp_path / "idem"),
            policy=policy,
        )
        ctx = _ctx()
        run = k.handle(TOOL_PREDICT, _predict_payload(), ctx=ctx)
        clock["now"] += 10  # within TTL
        out = k.resolve_resource(run["manifest_uri"], ctx=ctx)
        assert out["run_id"] == run["run_id"]

    def test_sweep_noop_without_policy(self, tmp_path):
        k = SecuredKernel(
            run_store=RunStore(tmp_path / "runs"),
            idem_store=IdempotencyStore(tmp_path / "idem"),
        )
        ctx = _ctx()
        k.handle(TOOL_PREDICT, _predict_payload(), ctx=ctx)
        assert k.sweep() == 0


# =====================================================================
# ResourceManager — missing resource
# =====================================================================

class TestResourceMissing:
    def test_resolve_missing_run_typed(self, secured):
        with pytest.raises(RunNotFoundError):
            secured.resolve_resource(
                "reactionagent://runs/run-missing/manifest", ctx=_ctx()
            )


# =====================================================================
# Side-effect matrix holds through the secured layer (F3 unchanged)
# =====================================================================

class TestSecuredSideEffects:
    def test_predict_immutable_run(self, secured):
        out = secured.handle(TOOL_PREDICT, _predict_payload(), ctx=_ctx())
        assert out["status"] == "frozen"
        assert out["manifest_uri"].startswith("reactionagent://runs/")

    def test_get_run_writes_nothing(self, secured):
        ctx = _ctx()
        run = secured.handle(TOOL_PREDICT, _predict_payload(), ctx=ctx)
        before = secured._kernel.runs.list_runs()
        secured.handle(TOOL_GET_RUN, {"run_id": run["run_id"]}, ctx=ctx)
        after = secured._kernel.runs.list_runs()
        assert before == after  # read-only: no new runs

    def test_expand_child_run_parent_preserved(self, secured):
        ctx = _ctx()
        parent = secured.handle(TOOL_PREDICT, _predict_payload(), ctx=ctx)
        child = secured.handle(
            TOOL_EXPAND,
            {
                "run_id": parent["run_id"],
                "evidence_id": "ev-1",
                "idempotency_key": "exp-1",
                "snapshot_id": "s1",
            },
            ctx=ctx,
        )
        assert child["parent_run_id"] == parent["run_id"]
        assert child["child_run_id"] != parent["run_id"]
        # parent unchanged
        p = secured._kernel.runs.get_run(parent["run_id"])
        assert p.tool == "predict"

    def test_resource_manager_mints_consistent_uris(self, secured):
        ctx = _ctx()
        run = secured.handle(TOOL_PREDICT, _predict_payload(), ctx=ctx)
        rm = secured._resources
        assert rm.mint_manifest_uri(run["run_id"]) == run["manifest_uri"]
        ev = rm.mint_evidence_uri(run["run_id"], "ev-1")
        assert ev.endswith(f"/runs/{run['run_id']}/evidence/ev-1")
