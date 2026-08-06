"""P4-T8 content-addressed immutable run manifest (final_design §23).

``request_hash`` and ``result_hash`` are recomputable (content-addressed).
Same request + same versions + same frozen evidence produce identical hashes.

P4-R1-E: there is a SINGLE hash preimage source. ``compute_request_hash`` is
the only request-hash implementation, and ``build_run_manifest`` is the only
place a result hash is computed. The result hash covers the final decision,
the full ranking/applicability, the support/counterevidence hashes, the
trace, the namespace, the versions and the classification.
"""
from __future__ import annotations

from reaction_agent.hashing import canonical_hash
from reaction_agent.schemas.result import StageSummary
from reaction_agent.schemas.p4.run import (
    ComponentVersions,
    ImmutableRunManifest,
    RunFreezeState,
)


def _canonical_query(query: dict) -> dict:
    return {k: v for k, v in sorted(query.items()) if v is not None}


def compute_request_hash(query: dict, snapshot_id: str, snapshot_hash: str,
                         versions: dict) -> str:
    """The ONLY request-hash implementation (P4-R1-E)."""
    return canonical_hash({
        "query": _canonical_query(query),
        "snapshot_id": snapshot_id,
        "snapshot_hash": snapshot_hash,
        "versions": {k: v for k, v in sorted(versions.items())},
    })


def compute_result_hash(
    *,
    request_hash: str,
    snapshot_hash: str,
    versions: dict,
    trace: StageSummary,
    evidence_ids: list[str],
    independent_group_ids: list[str],
    decision: dict,
    ranking: dict,
    applicability: dict,
    support_hashes: dict,
    counterevidence_hashes: dict,
    namespace: dict,
    classification: str,
) -> str:
    """Content-addressed result hash covering every decision-relevant input.

    P4-R1-E: the hash must change when the final decision, the ranking, the
    applicability, the support/counterevidence hashes, the trace, the
    namespace, the versions or the classification change.
    """
    return canonical_hash({
        "request_hash": request_hash,
        "snapshot_hash": snapshot_hash,
        "versions": {k: v for k, v in sorted(versions.items())},
        "trace": {
            "D": sorted(trace.donor_evidence_ids),
            "T": sorted(trace.transformation_hypothesis_ids),
            "S": sorted(trace.site_hypothesis_ids),
            "delta": sorted(trace.graph_edit_ids),
            "Y": sorted(trace.candidate_ids),
            "L": sorted(trace.ledger_ids),
            "R": dict(trace.rank_result),
            "A": dict(trace.decision_result),
        },
        "evidence_ids": sorted(evidence_ids),
        "independent_group_ids": sorted(independent_group_ids),
        "decision": decision,
        "ranking": ranking,
        "applicability": applicability,
        "support_hashes": support_hashes,
        "counterevidence_hashes": counterevidence_hashes,
        "namespace": namespace,
        "classification": classification,
    })


def build_run_manifest(
    *,
    run_id: str,
    parent_run_id: str | None,
    query: dict,
    snapshot_id: str,
    snapshot_hash: str,
    versions: dict,
    trace: StageSummary,
    evidence_ids: list[str],
    independent_group_ids: list[str],
    result_hash: str | None,
    freeze_state: str,
    capability_status: str,
    blocked_reasons: list[str],
    classification: str,
    fold_view_id: str = "",
    decision: dict | None = None,
    ranking: dict | None = None,
    applicability: dict | None = None,
    support_hashes: dict | None = None,
    counterevidence_hashes: dict | None = None,
    namespace: dict | None = None,
) -> ImmutableRunManifest:
    """Build a deterministic run manifest.

    The result hash is computed HERE from the full decision-relevant inputs;
    a provided ``result_hash`` is only used for replay/verification fixtures
    (integrity is checked by the run store). ``compute_request_hash`` is the
    single request-hash source.
    """
    request_hash = compute_request_hash(query, snapshot_id, snapshot_hash, versions)
    computed = compute_result_hash(
        request_hash=request_hash,
        snapshot_hash=snapshot_hash,
        versions=versions,
        trace=trace,
        evidence_ids=evidence_ids,
        independent_group_ids=independent_group_ids,
        decision=decision or {},
        ranking=ranking or {},
        applicability=applicability or {},
        support_hashes=support_hashes or {},
        counterevidence_hashes=counterevidence_hashes or {},
        namespace=namespace or {},
        classification=classification,
    )
    effective_result_hash = result_hash if result_hash is not None else computed

    return ImmutableRunManifest(
        run_id=run_id,
        parent_run_id=parent_run_id,
        request_hash=request_hash,
        snapshot_id=snapshot_id,
        snapshot_hash=snapshot_hash,
        fold_view_id=fold_view_id,
        versions=ComponentVersions(**versions),
        trace=trace,
        evidence_ids=list(evidence_ids),
        independent_group_ids=list(independent_group_ids),
        result_hash=effective_result_hash,
        freeze_state=RunFreezeState(freeze_state),
        capability_status=capability_status,
        blocked_reasons=list(blocked_reasons),
        classification=classification,
        decision=decision or {},
        ranking=ranking or {},
        applicability=applicability or {},
        support_hashes=support_hashes or {},
        counterevidence_hashes=counterevidence_hashes or {},
        namespace=namespace or {},
    )


def recompute_result_hash(manifest: ImmutableRunManifest) -> str:
    """Recompute the expected result hash for an existing manifest."""
    return compute_result_hash(
        request_hash=manifest.request_hash,
        snapshot_hash=manifest.snapshot_hash,
        versions=manifest.versions.model_dump(mode="json"),
        trace=manifest.trace,
        evidence_ids=manifest.evidence_ids,
        independent_group_ids=manifest.independent_group_ids,
        decision=manifest.decision,
        ranking=manifest.ranking,
        applicability=manifest.applicability,
        support_hashes=manifest.support_hashes,
        counterevidence_hashes=manifest.counterevidence_hashes,
        namespace=manifest.namespace,
        classification=manifest.classification,
    )