"""P4 orchestrator: identity → support → counterevidence → rank →
applicability → typed abstention → immutable run (final_design §4 pipeline).

P4 never creates candidate structures; it only consumes validated strict
candidates produced upstream (P3) and adds support/rank/applicability/
abstention under the versioned decision policy.
"""
from __future__ import annotations

import json

from reaction_agent.hashing import canonical_hash
from reaction_agent.policies.p4_decision_policy import P4_POLICY_VERSION
from reaction_agent.schemas.common import (
    ResultStatus,
    DecisionKind,
    SystemFailureReason,
    ScientificAbstentionReason,
    ApplicabilityLabel,
)
from reaction_agent.inference.counterevidence import CONFLICT_TYPES
from reaction_agent.schemas.result import PredictionResult
from reaction_agent.schemas.p4.authority import P3AuthorityHandle
from reaction_agent.schemas.p4.decision import (
    AbstentionDecision,
    PredictionDecision,
)
from reaction_agent.schemas.p4.support import SupportTier
from reaction_agent.inference.evidence_identity import resolve_evidence_identity
from reaction_agent.inference.features import build_feature_vector
from reaction_agent.inference.support import aggregate_support
from reaction_agent.inference.counterevidence import collect_counterevidence
from reaction_agent.inference.ranker import rank_strict_candidates
from reaction_agent.inference.applicability import assess_applicability
from reaction_agent.inference.abstention import detect_abstention_conditions, decide_abstention
from reaction_agent.runtime.trace import build_stage_summary
from reaction_agent.runtime.manifest import build_run_manifest
from reaction_agent.runtime.run import ImmutableRunStore
from reaction_agent.adapters.prediction_result_adapter import PredictionResultAdapter
from reaction_agent.schemas.p4.run import RunFreezeState


class PipelineOutcome:
    """Everything produced by one P4 pipeline run."""

    def __init__(self, *, query, resolution, support_breakdowns,
                 counterevidence, ranking, applicability, decision,
                 manifest, capability, classification, run_store, run_id):
        self.query = query
        self.resolution = resolution
        self.support_breakdowns = support_breakdowns
        self.counterevidence = counterevidence
        self.ranking = ranking
        self.applicability = applicability
        self.decision = decision
        self.manifest = manifest
        self.capability = capability
        self.classification = classification
        self.run_store = run_store
        self.run_id = run_id

    def build_prediction_result(self) -> PredictionResult:
        adapter = PredictionResultAdapter(policy_version=P4_POLICY_VERSION)
        snapshot_id = self.query.get("snapshot_id", "snap_p4")
        return adapter.validate_and_build(
            decision=self.decision,
            candidate_map=self._enriched_candidates(),
            run_id=self.run_id,
            snapshot_id=snapshot_id,
            normalized_query=str(self.query.get("query_smiles", "query")),
        )

    def _enriched_candidates(self):
        out = {}
        for cand_id, breakdown in self.support_breakdowns.items():
            cand = getattr(breakdown, "_candidate", None)
            if cand is not None:
                assessment = self.applicability.get(cand_id)
                update = {"support_tier": breakdown.support_tier.value}
                if assessment is not None:
                    update["applicability"] = assessment.label
                out[cand_id] = cand.model_copy(update=update)
        return out


_QUERY_NS_FIELDS = ("run_id", "query_id", "case_id", "fold_id",
                    "snapshot_id", "snapshot_hash")


def _validate_namespace_binding(query: dict, evidence_records: list,
                                authority: P3AuthorityHandle) -> None:
    """P4-R1-D: the request, evidence and authority must share ONE namespace.

    - query 声明的 run/query/case/fold/snapshot ID/hash 必须与 authority 一致；
    - query 声明的 policy_version 必须与 authority 绑定的 policy 一致；
    - 每条 evidence 的 snapshot_id 必须与 authority 的 snapshot 一致
      （cross-snapshot smuggling 拒绝）。
    """
    ns = authority.namespace
    for field in _QUERY_NS_FIELDS:
        qv = query.get(field)
        if qv is not None and qv != getattr(ns, field):
            raise NamespaceMismatchError(
                f"query.{field}={qv!r} != authority.{field}={getattr(ns, field)!r}")
    qp = query.get("policy_version")
    if qp is not None and qp != ns.policy_version:
        raise NamespaceMismatchError(
            f"query.policy_version={qp!r} != authority.policy_version="
            f"{ns.policy_version!r}")
    for rec in evidence_records:
        sid = rec.snapshot_id if not isinstance(rec, dict) else rec.get("snapshot_id")
        if sid is not None and sid != ns.snapshot_id:
            raise NamespaceMismatchError(
                f"evidence snapshot_id={sid!r} != authority.snapshot_id="
                f"{ns.snapshot_id!r}")


def _evidence_ids(evidence_records) -> list[str]:
    out: list[str] = []
    for rec in evidence_records:
        rid = rec.reaction_id if not isinstance(rec, dict) else rec.get("reaction_id", "")
        if rid and rid not in out:
            out.append(rid)
    return out


def _run_id(query: dict, authority: P3AuthorityHandle | None = None) -> str:
    """Run identity is bound to the frozen namespace, not just the query.

    P4-R1-E: the same query under a different snapshot/evidence/version must
    NOT collide; the run id therefore includes the authority namespace.
    """
    preimage = {"query": query}
    if authority is not None:
        preimage["namespace"] = authority.namespace.model_dump()
    return f"run_{canonical_hash(preimage)[:12]}"


class NamespaceMismatchError(ValueError):
    """P4-R1-D: request/evidence/authority do not share one frozen namespace."""


def run_p4_pipeline(
    *,
    query: dict,
    evidence_records: list,
    candidates: list,
    structural_contexts: dict,
    authority: P3AuthorityHandle,
    top_k: int = 3,
    run_store: ImmutableRunStore | None = None,
    feature_evidence_ids: dict | None = None,
) -> PipelineOutcome:
    """Run the P4 pipeline over a query + P3-produced strict candidates.

    ``authority`` must be a typed ``P3AuthorityHandle`` produced by the
    verified P3 consumer (P4-R1-B) — a caller-written capability struct is
    NOT an authority. The authority's frozen namespace binds the run identity.

    ``feature_evidence_ids`` optionally maps candidate_id -> feature_key ->
    the evidence ids that genuinely produced that feature (P4-R1-G). Without
    a binding, an ordinal is observable but evidence-less and never becomes
    strong support / in-domain applicability.
    """
    store = run_store if run_store is not None else ImmutableRunStore()
    run_id = _run_id(query, authority)

    # -- capability gate: blocked / missing P3 => system failure ----------
    if not authority.capability_available:
        failure_reason = SystemFailureReason.SNAPSHOT_UNAVAILABLE
        trace = build_stage_summary(
            donor_evidence_ids=[], transformation_hypothesis_ids=[],
            site_hypothesis_ids=[], graph_edit_ids=[], candidate_ids=[],
            ledger_ids=[], rank_result={}, decision_result={})
        decision = PredictionDecision(
            decision=DecisionKind.failed,
            status=ResultStatus.failed,
            reason_code=failure_reason.value,
            reason_detail="; ".join(authority.blocked_reasons),
            trace=trace,
            policy_version=P4_POLICY_VERSION,
        )
        manifest = build_run_manifest(
            run_id=run_id, parent_run_id=None, query=query,
            snapshot_id=query.get("snapshot_id", "snap_p4"),
            snapshot_hash="blocked_no_snapshot", versions=_versions(),
            trace=trace, evidence_ids=[], independent_group_ids=[],
            result_hash=None, freeze_state=RunFreezeState.active.value,
            capability_status=authority.evidence_kind.value,
            blocked_reasons=authority.blocked_reasons,
            classification=authority.evidence_kind.value,
            fold_view_id=query.get("fold_view_id", ""),
            decision=_decision_dict(decision),
            ranking={},
            applicability={},
            support_hashes={},
            counterevidence_hashes={},
            namespace=authority.namespace.model_dump(),
        )
        store.create(manifest)
        return PipelineOutcome(
            query=query, resolution=None, support_breakdowns={},
            counterevidence={}, ranking=None, applicability=None,
            decision=decision, manifest=manifest, capability=authority,
            classification=authority.evidence_kind.value,
            run_store=store, run_id=run_id,
        )

    # -- namespace binding (P4-R1-D, fail-closed) -------------------------
    _validate_namespace_binding(query, evidence_records, authority)

    # -- evidence identity ------------------------------------------------
    resolution = resolve_evidence_identity(
        evidence_records, policy_version=P4_POLICY_VERSION)

    evidence_ids = _evidence_ids(evidence_records)
    independent_group_ids = resolution.group_ids_for(evidence_ids)

    # -- per-candidate support / counterevidence / applicability ----------
    support_breakdowns = {}
    counterevidence = {}
    applicability = {}
    feature_vectors = {}
    for cand in candidates:
        cand_id = cand.candidate_id
        ctx = structural_contexts.get(cand_id, {})
        fei = (feature_evidence_ids or {}).get(cand_id) or {}
        counter = collect_counterevidence(
            cand, evidence_records, resolution, context=ctx)
        counterevidence[cand_id] = counter
        # Only the conflict-class counterevidence types feed the ranking
        # conflict_penalty (aligned with the EVIDENCE_CONFLICT semantics).
        conflict_reasons = [
            r.counter_type.value for r in counter.records
            if r.counter_type in CONFLICT_TYPES
        ]
        support_breakdowns[cand_id] = aggregate_support(
            cand, evidence_records, resolution,
            structural_context=ctx, conflicts=conflict_reasons,
            feature_evidence_ids=fei)
        support_breakdowns[cand_id]._candidate = cand  # enrich later
        applicability[cand_id] = assess_applicability(
            cand, evidence_records, resolution,
            structural_context=ctx, conflicts=conflict_reasons,
            feature_evidence_ids=fei)
        feature_vectors[cand_id] = build_feature_vector(
            cand, resolution, structural_context=ctx, conflicts=conflict_reasons,
            feature_evidence_ids=fei)

    # -- trace base (D/T/S/Δ/Y/L) ----------------------------------------
    candidate_ids = [c.candidate_id for c in candidates]
    ledger_ids = []
    for c in candidates:
        ledger_ids.extend(getattr(c, "source_ledger_ids", []) or [])
    transform_ids = []
    for c in candidates:
        transform_ids.extend(getattr(c, "transformation_ids", []) or [])
    site_ids = []
    for c in candidates:
        site_ids.extend(getattr(c, "site_ids", []) or [])
    graph_edit_ids = []
    for c in candidates:
        for gp in (getattr(c, "generation_paths", None) or []):
            if isinstance(gp, dict) and gp.get("graph_edit_id"):
                graph_edit_ids.append(gp["graph_edit_id"])

    # -- per-candidate adjudication (P4-R1-H) -----------------------------
    # Weak / out-of-domain / unknown / candidate-local-conflict candidates are
    # moved OUT of the production ranking (with trace); they never abort the
    # whole candidate set. Only when the eligible set is empty does the
    # pipeline produce a global typed abstention.
    eligible: list = []
    disqualified: dict[str, list[str]] = {}
    for cand in candidates:
        cand_id = cand.candidate_id
        reasons: list[str] = []
        sup = support_breakdowns.get(cand_id)
        app = applicability.get(cand_id)
        ce = counterevidence.get(cand_id)
        if sup is None or sup.support_tier == SupportTier.none:
            reasons.append("insufficient_support")
        if app is not None and app.label in (
                ApplicabilityLabel.out_of_domain, ApplicabilityLabel.unknown):
            reasons.append(f"applicability_{app.label.value}")
        if ce is not None and ce.has_conflict:
            reasons.append("candidate_local_conflict")
        if reasons:
            disqualified[cand_id] = reasons
        else:
            eligible.append(cand)

    # -- decision: abstain vs complete ------------------------------------
    if not eligible:
        # Global abstention typing: all candidates disqualified for the SAME
        # reason collapse to that reason; otherwise the frozen precedence
        # decides (P4-R1-H: candidate-local vs global conflict are distinct).
        all_reasons = [r for rs in disqualified.values() for r in rs]
        if all_reasons and all(
                r == "candidate_local_conflict" for r in all_reasons):
            conditions = detect_abstention_conditions(
                invalid_input=not query.get("query_smiles"),
                no_in_domain_donor=len(evidence_ids) == 0,
                evidence_conflict=True,
            )
        elif all_reasons and all(
                r == "applicability_out_of_domain" for r in all_reasons):
            conditions = detect_abstention_conditions(
                invalid_input=not query.get("query_smiles"),
                no_in_domain_donor=len(evidence_ids) == 0,
                out_of_domain=True,
            )
        else:
            conditions = detect_abstention_conditions(
                invalid_input=not query.get("query_smiles"),
                no_in_domain_donor=len(evidence_ids) == 0,
                insufficient_support=len(eligible) == 0,
            )
        rank_result = {"decision": "abstained"}
        decision_result = {"decision": "abstained"}
        trace = build_stage_summary(
            donor_evidence_ids=evidence_ids,
            transformation_hypothesis_ids=transform_ids,
            site_hypothesis_ids=site_ids,
            graph_edit_ids=graph_edit_ids,
            candidate_ids=candidate_ids,
            ledger_ids=ledger_ids,
            rank_result=rank_result,
            decision_result=decision_result,
        )
        abstention = decide_abstention(
            conditions=conditions, trace=trace,
            policy_version=P4_POLICY_VERSION,
            source_evidence_scope=query.get("fold_view_id", "train_only"),
        )
        decision = PredictionDecision(
            decision=DecisionKind.abstained,
            status=ResultStatus.abstained,
            abstention=abstention,
            trace=trace,
            policy_version=P4_POLICY_VERSION,
        )
        ranked = None
    else:
        # -- strict ranking over the ELIGIBLE subset (P4-R1-H) -------------
        ranked = rank_strict_candidates(
            eligible, feature_vectors=feature_vectors,
            policy_version=P4_POLICY_VERSION)
        top = ranked.candidates[:top_k]
        # R trace commits to the actual ranked outcome (ids + scores + ranks)
        # and records the disqualified candidates (with per-candidate reason).
        ranked_json = json.dumps(
            sorted([{"candidate_id": c.candidate_id,
                     "score": c.ranking_score,
                     "rank": c.rank} for c in top],
                   key=lambda x: x["candidate_id"]),
            sort_keys=True)
        rank_result = {
            "rank_top_k": str(len(top)),
            "ranked": ranked_json,
            "disqualified": json.dumps(
                dict(sorted(disqualified.items())), sort_keys=True),
        }
        decision_result = {"decision": "predicted"}
        trace = build_stage_summary(
            donor_evidence_ids=evidence_ids,
            transformation_hypothesis_ids=transform_ids,
            site_hypothesis_ids=site_ids,
            graph_edit_ids=graph_edit_ids,
            candidate_ids=[c.candidate_id for c in eligible],
            ledger_ids=ledger_ids,
            rank_result=rank_result,
            decision_result=decision_result,
        )
        decision = PredictionDecision(
            decision=DecisionKind.predicted,
            status=ResultStatus.completed,
            ranked_candidates=top,
            trace=trace,
            policy_version=P4_POLICY_VERSION,
        )

    # -- immutable manifest (P4-R1-E: single hash preimage, builder computes) --
    manifest = build_run_manifest(
        run_id=run_id, parent_run_id=None, query=query,
        snapshot_id=query.get("snapshot_id", "snap_p4"),
        snapshot_hash=query.get("snapshot_hash", "snap_unknown"),
        versions=_versions(), trace=trace,
        evidence_ids=evidence_ids,
        independent_group_ids=independent_group_ids,
        result_hash=None,  # builder computes the single result hash
        freeze_state=RunFreezeState.active.value,
        capability_status=authority.evidence_kind.value,
        blocked_reasons=authority.blocked_reasons,
        classification=authority.evidence_kind.value,
        fold_view_id=query.get("fold_view_id", ""),
        decision=_decision_dict(decision),
        ranking=_ranking_dict(ranked),
        applicability=_applicability_dict(applicability),
        support_hashes=_support_hashes(support_breakdowns),
        counterevidence_hashes=_counterevidence_hashes(counterevidence),
        namespace=authority.namespace.model_dump(),
    )
    store.create(manifest)

    return PipelineOutcome(
        query=query, resolution=resolution,
        support_breakdowns=support_breakdowns,
        counterevidence=counterevidence,
        ranking=ranked,
        applicability=applicability,
        decision=decision,
        manifest=manifest,
        capability=authority,
        classification=authority.evidence_kind.value,
        run_store=store, run_id=run_id,
    )


def _versions() -> dict:
    return {
        "normalization_version": "p1-1",
        "config_version": "p1-1",
        "policy_version": P4_POLICY_VERSION,
        "kernel_version": "p3-blocked",
        "candidate_version": "p3-blocked",
        "ranker_version": "p4-ranker-1",
        "snapshot_builder_version": "p1-1",
    }


def _decision_dict(decision: PredictionDecision) -> dict:
    """Deterministic decision preimage for the result hash."""
    return {
        "decision": decision.decision.value,
        "status": decision.status.value,
        "reason_code": decision.reason_code,
        "ranked_candidates": [
            {"candidate_id": rc.candidate_id, "score": rc.ranking_score,
             "rank": rc.rank}
            for rc in decision.ranked_candidates
        ],
        "abstention": (
            decision.abstention.reason_code.value
            if decision.abstention is not None else None),
    }


def _ranking_dict(ranked) -> dict:
    if ranked is None:
        return {}
    return {
        "ranker_version": ranked.ranker_version,
        "candidates": [
            {"candidate_id": rc.candidate_id, "score": rc.ranking_score,
             "rank": rc.rank}
            for rc in ranked.candidates
        ],
    }


def _applicability_dict(applicability) -> dict:
    if not applicability:
        return {}
    return {
        cand_id: (a.label.value if a is not None else "unknown")
        for cand_id, a in sorted(applicability.items())
    }


def _support_hashes(support_breakdowns) -> dict:
    return {
        cand_id: getattr(b, "breakdown_hash", "")
        for cand_id, b in sorted(support_breakdowns.items())
    }


def _counterevidence_hashes(counterevidence) -> dict:
    return {
        cand_id: canonical_hash({
            "records": [
                {"record_id": r.record_id, "type": r.counter_type.value,
                 "evidence_ids": sorted(r.evidence_ids)}
                for r in sorted(c.records, key=lambda r: r.record_id)
            ],
            "has_conflict": c.has_conflict,
        })
        for cand_id, c in sorted(counterevidence.items())
    }
