"""P7 T5 reporter pin tests (RED first).

The reporter (``reaction_agent/agent/reporter.py``) projects a typed
``PredictionResult`` into a STRUCTURED report (data only — the host renders
structures / scores / IDs). Gate P7 prerequisite "report matches result":
every report field is sourced from a typed result field (provenance map);
report-only values raise ``ReportError`` or are disclosed as limitations.

Pins:
- every report field sourced from typed result (field_provenance traceable);
- top-K strict candidates sorted by ranking_score;
- donor/reaction/transform/site from stage_summary + candidates;
- Source/Candidate ledger summaries from candidates + stage_summary;
- applicability/support/ranking from candidates;
- abstention/failure honest (no sugar-coat as success);
- limitations disclose scope gaps (fixture scope, conflicts-not-surfaced);
- unsourced field request -> ReportError;
- reporter does not mutate the typed result.

RED until ``reporter.py`` is implemented (ImportError); GREEN after.
"""
from __future__ import annotations

import pytest

from reaction_agent.adapters.p3_p4_bridge import run_deterministic_predict


@pytest.fixture(scope="module")
def baseline_result():
    return run_deterministic_predict(
        {"substrate_smiles": "CCCCCCCCO", "idempotency_key": "k_r5",
         "snapshot_id": "snap_r5"},
        current_run_path="/tmp/_t5_reporter_cra.json",
    )


class TestReportFieldsSourced:
    def test_scalar_fields_match_typed(self, baseline_result):
        from reaction_agent.agent.reporter import build_report

        rep = build_report(baseline_result)
        assert rep.run_id == baseline_result.run_id
        assert rep.status == baseline_result.status.value
        assert rep.decision == baseline_result.decision.value
        assert rep.normalized_query == baseline_result.normalized_query
        assert rep.snapshot_id == baseline_result.snapshot_id

    def test_every_report_field_has_provenance(self, baseline_result):
        from reaction_agent.agent.reporter import build_report

        rep = build_report(baseline_result)
        assert rep.field_provenance, "provenance map must be non-empty"
        # every provenance source path must reference a real typed attribute
        for report_field, source_path in rep.field_provenance.items():
            assert source_path, f"{report_field}: empty source path"
            assert source_path.startswith("result.") or source_path.startswith("stage_summary.") or source_path.startswith("candidate."), (
                f"{report_field}: source {source_path!r} not a typed-result path"
            )

    def test_unsourced_field_request_raises(self, baseline_result):
        from reaction_agent.agent.reporter import (
            ReportError,
            build_report,
            get_sourced_field,
        )

        rep = build_report(baseline_result)
        # "confidence" is not a typed-result field -> report-only -> ReportError
        with pytest.raises(ReportError):
            get_sourced_field(rep, "confidence")


class TestTopKStrictCandidates:
    def test_top_k_sorted_by_score_strict_lane(self, baseline_result):
        from reaction_agent.agent.reporter import build_report

        rep = build_report(baseline_result, top_k=3)
        scores = [c.ranking_score for c in rep.top_k_candidates]
        assert scores == sorted(scores, reverse=True), "top-K must be score-desc"
        assert len(rep.top_k_candidates) <= 3
        for c in rep.top_k_candidates:
            assert c.lane == "strict"


class TestEvidenceAndLedgerSummaries:
    def test_donor_transform_site_from_typed(self, baseline_result):
        from reaction_agent.agent.reporter import build_report

        rep = build_report(baseline_result)
        assert set(rep.donor_evidence_ids) == set(
            baseline_result.stage_summary.donor_evidence_ids
        )
        typed_t = {t for c in baseline_result.candidates for t in c.transformation_ids}
        typed_s = {s for c in baseline_result.candidates for s in c.site_ids}
        assert set(rep.transformation_ids) == typed_t
        assert set(rep.site_ids) == typed_s

    def test_source_and_candidate_ledger_summaries(self, baseline_result):
        from reaction_agent.agent.reporter import build_report

        rep = build_report(baseline_result)
        assert set(rep.source_ledger_ids) == set(
            baseline_result.stage_summary.ledger_ids
        )
        typed_cal = {
            c.candidate_analogy_ledger_id
            for c in baseline_result.candidates
            if c.candidate_analogy_ledger_id
        }
        assert set(rep.candidate_analogy_ledger_ids) == typed_cal

    def test_applicability_support_ranking_from_typed(self, baseline_result):
        from reaction_agent.agent.reporter import build_report

        rep = build_report(baseline_result)
        app = dict(rep.applicability)
        sup = dict(rep.support_tiers)
        rk = dict(rep.ranking_scores)
        for c in baseline_result.candidates:
            assert app[c.candidate_id] == c.applicability.value
            assert sup[c.candidate_id] == c.support_tier
            assert rk[c.candidate_id] == c.ranking_score


class TestAbstentionFailureHonest:
    def _abstained_result(self, baseline_result):
        from reaction_agent.schemas.common import (
            DecisionKind,
            ResultStatus,
            ScientificAbstentionReason,
        )
        from reaction_agent.schemas.result import Abstention

        abst = Abstention(
            reason_code=ScientificAbstentionReason.INSUFFICIENT_SUPPORT,
            stage="support", detail="not enough independent evidence",
        )
        return baseline_result.model_copy(update={
            "status": ResultStatus.abstained,
            "decision": DecisionKind.abstained,
            "abstention": abst,
            "candidates": [],
        })

    def _failed_result(self, baseline_result):
        from reaction_agent.schemas.common import (
            DecisionKind,
            ResultStatus,
            SystemFailureReason,
        )
        from reaction_agent.schemas.result import Failure

        fail = Failure(
            reason_code=SystemFailureReason.SNAPSHOT_UNAVAILABLE,
            detail="blocked kernel",
        )
        return baseline_result.model_copy(update={
            "status": ResultStatus.failed,
            "decision": DecisionKind.failed,
            "failure": fail,
            "candidates": [],
        })

    def test_completed_has_no_abstension_or_failure(self, baseline_result):
        from reaction_agent.agent.reporter import build_report

        rep = build_report(baseline_result)
        assert rep.abstention is None
        assert rep.failure is None
        assert rep.status == "completed"

    def test_abstained_presented_honestly(self, baseline_result):
        from reaction_agent.agent.reporter import build_report

        rep = build_report(self._abstained_result(baseline_result))
        assert rep.status == "abstained"
        assert rep.decision == "abstained"
        assert rep.abstention is not None  # not sugar-coated as success
        reason_code, stage, detail = rep.abstention
        assert reason_code  # non-empty typed reason
        assert rep.top_k_candidates == ()  # no fake candidates

    def test_failed_presented_honestly(self, baseline_result):
        from reaction_agent.agent.reporter import build_report

        rep = build_report(self._failed_result(baseline_result))
        assert rep.status == "failed"
        assert rep.decision == "failed"
        assert rep.failure is not None  # not sugar-coated as success
        reason_code, detail = rep.failure
        assert reason_code
        assert rep.top_k_candidates == ()


class TestLimitations:
    def test_limitations_disclose_scope_gaps(self, baseline_result):
        from reaction_agent.agent.reporter import build_report

        rep = build_report(baseline_result)
        assert rep.limitations, "limitations must disclose scope gaps"
        joined = " ".join(rep.limitations).lower()
        # conflicts not surfaced on typed result -> disclosed (not fabricated)
        assert "conflict" in joined or "not surfaced" in joined


class TestImmutability:
    def test_report_does_not_mutate_typed_result(self, baseline_result):
        from reaction_agent.agent.reporter import build_report

        typed_before = list(baseline_result.candidates[0].transformation_ids)
        rep = build_report(baseline_result)
        # Mutate the report's candidate summary (if it exposed list refs) ->
        # must not leak into the typed result.
        # CandidateSummary fields are tuples (immutable); confirm no shared list.
        for cs in rep.top_k_candidates:
            assert isinstance(cs.transformation_ids, tuple)
        assert baseline_result.candidates[0].transformation_ids == typed_before
