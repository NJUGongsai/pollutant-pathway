"""Gate P6 Round 2 — remediation RED tests.

Must FAIL (RED) until the G1–G6 fixes land, then PASS (GREEN).

These are the adversarial probes kimi used to fail Gate Round 1, turned
into pinned regression tests so the perimeter cannot silently regress.

Findings (see kimi's Gate Round 1 report):
- GATE-P6-01 (P1) unbound run readable cross-tenant in secured mode  → G1
- GATE-P6-02 (P1) idempotency key namespace shared cross-tenant     → G2
- GATE-P6-03 (P2) predict response `reused` always True              → G3
- GATE-P6-04 (P2) sweep leaves zombie idem → replay RunNotFoundError → G4
- GATE-P6-06 (P2) manifest URI tolerates a trailing segment           → G6
(GATE-P6-05 is the gate-report refresh — handled by a clean full-suite
 run + commit, not a unit test.)
"""
from __future__ import annotations

import pytest

from reaction_agent.mcp.errors import (
    ForbiddenError,
    IdempotencyConflictError,
    P6Error,
    RunNotFoundError,
)
from reaction_agent.mcp.idempotency import IdempotencyStore
from reaction_agent.mcp.resources import (
    AccessContext,
    ResourceURI,
    RetentionPolicy,
)
from reaction_agent.mcp.runs import RunStore
from reaction_agent.mcp.secured import SecuredKernel
from reaction_agent.mcp.tools import (
    TOOL_GET_RUN,
    TOOL_PREDICT,
    ReactionMCPKernel,
)


def _predict_payload(smiles="CCO", key="k1", snap="s1"):
    return {"substrate_smiles": smiles, "idempotency_key": key, "snapshot_id": snap}


def _ctx(tenant, principal="a"):
    return AccessContext(principal=principal, tenant_id=tenant)


@pytest.fixture()
def secured(tmp_path):
    return SecuredKernel(
        run_store=RunStore(tmp_path / "runs"),
        idem_store=IdempotencyStore(tmp_path / "idem"),
        policy=RetentionPolicy(max_age_seconds=3600),
    )


# =====================================================================
# G1 — secured mode must deny unbound (tenant_id=None) runs to ANY ctx
# =====================================================================

class TestG1UnboundRunBypass:
    """A legacy/Phase-A run (tenant_id=None) mixed into a secured store
    must NOT be readable by any tenant ctx — fail-closed, not open."""

    def _legacy_store(self, tmp_path):
        runs = RunStore(tmp_path / "runs")
        idem = IdempotencyStore(tmp_path / "idem")
        legacy = ReactionMCPKernel(run_store=runs, idem_store=idem)  # no policy
        created = legacy.handle(TOOL_PREDICT, _predict_payload())
        assert runs.get_run(created["run_id"]).tenant_id is None  # legacy unbound
        return runs, idem, created

    def test_unbound_cross_tenant_get_run_forbidden(self, tmp_path):
        runs, idem, created = self._legacy_store(tmp_path)
        sec = SecuredKernel(
            run_store=runs, idem_store=idem, policy=RetentionPolicy(max_age_seconds=3600)
        )
        with pytest.raises(ForbiddenError):
            sec.handle(
                TOOL_GET_RUN, {"run_id": created["run_id"]}, ctx=_ctx("t2")
            )

    def test_unbound_resolve_manifest_forbidden(self, tmp_path):
        runs, idem, created = self._legacy_store(tmp_path)
        sec = SecuredKernel(
            run_store=runs, idem_store=idem, policy=RetentionPolicy(max_age_seconds=3600)
        )
        with pytest.raises(ForbiddenError):
            sec.resolve_resource(created["manifest_uri"], ctx=_ctx("t2"))

    def test_unbound_even_owner_tenant_denied(self, tmp_path):
        runs, idem, created = self._legacy_store(tmp_path)
        sec = SecuredKernel(
            run_store=runs, idem_store=idem, policy=RetentionPolicy(max_age_seconds=3600)
        )
        # no legitimate owner for an unbound run; every ctx must be denied
        with pytest.raises(ForbiddenError):
            sec.handle(
                TOOL_GET_RUN, {"run_id": created["run_id"]}, ctx=_ctx("t1")
            )

    def test_unbound_expand_parent_forbidden(self, tmp_path):
        runs, idem, created = self._legacy_store(tmp_path)
        sec = SecuredKernel(
            run_store=runs, idem_store=idem, policy=RetentionPolicy(max_age_seconds=3600)
        )
        with pytest.raises(ForbiddenError):
            sec.handle(
                "reaction.expand_evidence_v1",
                {
                    "run_id": created["run_id"],
                    "evidence_id": "ev-1",
                    "idempotency_key": "exp-1",
                    "snapshot_id": "s1",
                },
                ctx=_ctx("t2"),
            )


# =====================================================================
# G2 — idempotency keys are namespaced per tenant in secured mode
# =====================================================================

class TestG2IdempotencyTenantNamespace:
    def test_cross_tenant_same_key_same_payload_independent(self, tmp_path):
        sec = SecuredKernel(
            run_store=RunStore(tmp_path / "runs"),
            idem_store=IdempotencyStore(tmp_path / "idem"),
            policy=RetentionPolicy(max_age_seconds=3600),
        )
        a, b = _ctx("ta"), _ctx("tb")
        p = _predict_payload(key="shared", smiles="CCO")
        ra = sec.handle(TOOL_PREDICT, p, ctx=a)
        rb = sec.handle(TOOL_PREDICT, p, ctx=b)
        assert ra["run_id"] != rb["run_id"], "cross-tenant silently reused same run"
        assert len(sec._kernel.runs.list_runs()) == 2

    def test_cross_tenant_same_key_diff_payload_no_conflict(self, tmp_path):
        sec = SecuredKernel(
            run_store=RunStore(tmp_path / "runs"),
            idem_store=IdempotencyStore(tmp_path / "idem"),
            policy=RetentionPolicy(max_age_seconds=3600),
        )
        a, b = _ctx("ta"), _ctx("tb")
        sec.handle(TOOL_PREDICT, _predict_payload(key="k", smiles="CCO"), ctx=a)
        # same key, different payload, DIFFERENT tenant — must NOT raise conflict
        out = sec.handle(TOOL_PREDICT, _predict_payload(key="k", smiles="CCC"), ctx=b)
        assert out["run_id"]

    def test_same_tenant_same_key_diff_payload_conflicts(self, tmp_path):
        sec = SecuredKernel(
            run_store=RunStore(tmp_path / "runs"),
            idem_store=IdempotencyStore(tmp_path / "idem"),
            policy=RetentionPolicy(max_age_seconds=3600),
        )
        a = _ctx("ta")
        sec.handle(TOOL_PREDICT, _predict_payload(key="k", smiles="CCO"), ctx=a)
        with pytest.raises(IdempotencyConflictError):
            sec.handle(TOOL_PREDICT, _predict_payload(key="k", smiles="CCC"), ctx=a)

    def test_cross_tenant_reuse_does_not_leak_existence(self, tmp_path):
        # tenant B must not learn whether tenant A already issued a key
        sec = SecuredKernel(
            run_store=RunStore(tmp_path / "runs"),
            idem_store=IdempotencyStore(tmp_path / "idem"),
            policy=RetentionPolicy(max_age_seconds=3600),
        )
        a, b = _ctx("ta"), _ctx("tb")
        ra = sec.handle(TOOL_PREDICT, _predict_payload(key="probe", smiles="CCO"), ctx=a)
        # B uses same key+payload — must get its OWN run, not A's run_id
        rb = sec.handle(TOOL_PREDICT, _predict_payload(key="probe", smiles="CCO"), ctx=b)
        assert rb["run_id"] != ra["run_id"]
        # and B cannot read A's run
        with pytest.raises(ForbiddenError):
            sec.resolve_resource(ra["manifest_uri"], ctx=b)


# =====================================================================
# G3 — predict response `reused` reflects actual reuse, not always True
# =====================================================================

class TestG3ReusedField:
    def test_first_call_reused_false(self, secured):
        out = secured.handle(TOOL_PREDICT, _predict_payload(), ctx=_ctx("t1"))
        assert out["reused"] is False

    def test_repeat_reused_true(self, secured):
        ctx = _ctx("t1")
        secured.handle(TOOL_PREDICT, _predict_payload(), ctx=ctx)
        out = secured.handle(TOOL_PREDICT, _predict_payload(), ctx=ctx)
        assert out["reused"] is True

    def test_different_key_first_call_reused_false(self, secured):
        ctx = _ctx("t1")
        secured.handle(TOOL_PREDICT, _predict_payload(key="k1"), ctx=ctx)
        out = secured.handle(TOOL_PREDICT, _predict_payload(key="k2"), ctx=ctx)
        assert out["reused"] is False


# =====================================================================
# G4 — retention sweep must not leave zombie idem records
# =====================================================================

class TestG4SweepZombieIdem:
    def test_sweep_then_replay_transparent_rebuild(self, tmp_path):
        clock = {"now": 1000.0}
        runs = RunStore(tmp_path / "runs")
        idem = IdempotencyStore(tmp_path / "idem")
        sec = SecuredKernel(
            run_store=runs,
            idem_store=idem,
            policy=RetentionPolicy(max_age_seconds=10, clock=lambda: clock["now"]),
        )
        ctx = _ctx("t1")
        sec.handle(TOOL_PREDICT, _predict_payload(key="k1"), ctx=ctx)
        clock["now"] += 100  # expire the run
        sec.sweep()  # must purge the run AND its idem record

        # replay same key+payload → transparent rebuild, NOT RunNotFoundError
        out = sec.handle(TOOL_PREDICT, _predict_payload(key="k1"), ctx=ctx)
        assert out["run_id"]
        assert out["reused"] is False  # rebuilt, not reused

    def test_sweep_removes_orphaned_idem_records(self, tmp_path):
        clock = {"now": 1000.0}
        runs = RunStore(tmp_path / "runs")
        idem = IdempotencyStore(tmp_path / "idem")
        sec = SecuredKernel(
            run_store=runs,
            idem_store=idem,
            policy=RetentionPolicy(max_age_seconds=10, clock=lambda: clock["now"]),
        )
        ctx = _ctx("t1")
        sec.handle(TOOL_PREDICT, _predict_payload(key="k1"), ctx=ctx)
        rid_before = runs.list_runs()
        idem_keys_before = idem.list_keys()
        assert len(idem_keys_before) >= 1
        clock["now"] += 100
        sec.sweep()
        # run file gone
        assert runs.list_runs() != rid_before or runs.list_runs() == []
        # idem record for the swept run is also gone
        assert idem.list_keys() == []


# =====================================================================
# G6 — manifest URI must reject a trailing segment
# =====================================================================

class TestG6ManifestTailReject:
    def test_manifest_with_tail_segment_rejected(self):
        with pytest.raises(P6Error):
            ResourceURI.parse("reactionagent://runs/run-1/manifest/garbage")

    def test_manifest_no_tail_ok(self):
        u = ResourceURI.parse("reactionagent://runs/run-1/manifest")
        assert u.kind == "manifest"
        assert u.evidence_id is None

    def test_evidence_with_tail_rejected(self):
        with pytest.raises(P6Error):
            ResourceURI.parse("reactionagent://runs/run-1/evidence/ev-1/extra")

    def test_manifest_constructor_rejects_evidence_id(self):
        with pytest.raises(P6Error):
            ResourceURI(run_id="r", kind="manifest", evidence_id="ev-1")
