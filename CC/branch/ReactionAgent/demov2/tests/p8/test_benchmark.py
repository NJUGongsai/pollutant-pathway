"""T4 RED tests — Generalized-lane benchmark (final_plan §11.5).

Stage B acceptance pins (leader Stage B 派单):
- metrics complete: incremental recall (new recalls vs strict baseline),
  false additions, risk-coverage, distance buckets (by generalization_distance),
  OOD ratio, cost.
- separate report: the benchmark report is written to ``reports/p8/`` and does
  NOT reuse the strict report structure (P5 gate / P7 three-way eval).
- OOD + distance are re-derived from the registered policy (no free text).

Must FAIL (RED) until ``reaction_agent/p8/benchmark.py`` exists.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from reaction_agent.agent.evaluation import Metrics as P7StrictMetrics
from reaction_agent.p8.policy import (
    OODPolicy,
    RelaxationPolicy,
    RelaxationRule,
    StrictCondition,
)
from reaction_agent.p8.schemas import (
    GeneralizedHypothesis,
    GeneralizedPolicyContext,
    SourceTransformRef,
    build_generalized_hypothesis,
)
from reaction_agent.p8.benchmark import (  # noqa: F401  (RED: module absent)
    DISTANCE_BUCKET_EDGES,
    CostReport,
    DistanceBucket,
    GeneralizedBenchmarkInput,
    GeneralizedBenchmarkMetrics,
    GeneralizedPrediction,
    RiskCoveragePoint,
    compute_benchmark,
    write_benchmark_report,
)


# ---------------------------------------------------------------------------
# Factories
# ---------------------------------------------------------------------------


def make_rules() -> list[RelaxationRule]:
    return [
        RelaxationRule(
            rule_id="relax_donor_site_precision",
            description="allow reduced donor-site precision",
            applies_to=[StrictCondition.donor_site_definite],
            distance_weight=0.3,
        ),
        RelaxationRule(
            rule_id="relax_precondition_completeness",
            description="allow relaxed precondition completeness",
            applies_to=[StrictCondition.preconditions_complete],
            distance_weight=0.5,
        ),
        RelaxationRule(
            rule_id="relax_ambiguity_margin",
            description="allow a wider ambiguity margin",
            applies_to=[StrictCondition.no_critical_ambiguity],
            distance_weight=0.2,
        ),
    ]


def make_policy(version: str = "1.0.0") -> RelaxationPolicy:
    return RelaxationPolicy.create(
        policy_id="p8-generalized-relaxation",
        version=version,
        description="P8 generalized lane relaxation policy",
        allowed_relaxations=make_rules(),
        ood=OODPolicy(
            declaration=(
                "generalized hypotheses that cite a relaxation outside the "
                "registered vocabulary are out-of-distribution and rejected"
            ),
        ),
    )


def make_context(policy: RelaxationPolicy | None = None) -> GeneralizedPolicyContext:
    return GeneralizedPolicyContext(
        policies={"p8-generalized-relaxation": policy or make_policy()},
        transform_lineage={"transform-a": ["lin1", "lin2"], "transform-b": ["lin3"]},
    )


def make_built(*, hypothesis_id: str = "g1",
               rule_id: str = "relax_donor_site_precision",
               failed: StrictCondition = StrictCondition.donor_site_definite) -> GeneralizedHypothesis:
    return build_generalized_hypothesis(
        hypothesis_id=hypothesis_id,
        policy=make_policy(),
        allowed_relaxation_ids=[rule_id],
        failed_strict_conditions=[failed],
        source_transforms=[SourceTransformRef(transform_id="transform-a", source_lineage_ids=["lin1"])],
        context=make_context(),
    )


def _cost() -> CostReport:
    return CostReport(provider_calls=12, token_count=4800, wall_clock_seconds=37.5)


# ---------------------------------------------------------------------------
# Input type — OOD + distance re-derived from the registered policy
# ---------------------------------------------------------------------------


class TestBenchmarkInput:
    def test_prediction_carries_policy_derivable_fields(self):
        p = GeneralizedPrediction(
            hypothesis_id="g1", predicted_id="cand-1",
            generalization_distance=0.3, is_ood=False,
        )
        assert p.hypothesis_id == "g1"
        assert p.predicted_id == "cand-1"
        assert p.generalization_distance == 0.3
        assert p.is_ood is False

    def test_input_rejects_mapping_for_unknown_hypothesis(self):
        # a predicted_id mapping must reference a hypothesis in the population
        h = make_built(hypothesis_id="g1")
        with pytest.raises(ValidationError):
            GeneralizedBenchmarkInput(
                truth_ids=frozenset({"cand-1"}),
                strict_baseline_ids=frozenset(),
                hypotheses=[h],
                predicted_id_by_hypothesis={"ghost": "cand-1"},
                policy=make_policy(),
                cost=_cost(),
            )


# ---------------------------------------------------------------------------
# Incremental recall — new recalls vs strict baseline
# ---------------------------------------------------------------------------


class TestIncrementalRecall:
    def test_recovers_part_of_what_strict_missed(self):
        # strict missed {cand-2, cand-3}; generalized recovered cand-2
        # incremental_recall = 1/2 = 0.5
        h1 = make_built(hypothesis_id="g1")  # predicts cand-2 (in truth, strict missed)
        h2 = make_built(hypothesis_id="g2",
                        rule_id="relax_ambiguity_margin",
                        failed=StrictCondition.no_critical_ambiguity)  # predicts cand-3 (in truth, strict missed) -- but we map g2->cand-99 (false)
        inp = GeneralizedBenchmarkInput(
            truth_ids=frozenset({"cand-1", "cand-2", "cand-3"}),
            strict_baseline_ids=frozenset({"cand-1"}),
            hypotheses=[h1, h2],
            predicted_id_by_hypothesis={"g1": "cand-2", "g2": "cand-99"},
            policy=make_policy(),
            cost=_cost(),
        )
        m = compute_benchmark(inp)
        assert abs(m.incremental_recall - 0.5) < 1e-9

    def test_zero_when_strict_already_complete(self):
        # truth \ strict = empty -> nothing to recover -> 0.0
        h = make_built(hypothesis_id="g1")
        inp = GeneralizedBenchmarkInput(
            truth_ids=frozenset({"cand-1"}),
            strict_baseline_ids=frozenset({"cand-1"}),
            hypotheses=[h],
            predicted_id_by_hypothesis={"g1": "cand-1"},
            policy=make_policy(),
            cost=_cost(),
        )
        assert m_incremental(inp) == 0.0

    def test_full_recall_of_missed(self):
        # strict missed 2, generalized recovered both -> 1.0
        h1 = make_built(hypothesis_id="g1")
        h2 = make_built(hypothesis_id="g2",
                        rule_id="relax_ambiguity_margin",
                        failed=StrictCondition.no_critical_ambiguity)
        inp = GeneralizedBenchmarkInput(
            truth_ids=frozenset({"cand-1", "cand-2", "cand-3"}),
            strict_baseline_ids=frozenset({"cand-1"}),
            hypotheses=[h1, h2],
            predicted_id_by_hypothesis={"g1": "cand-2", "g2": "cand-3"},
            policy=make_policy(),
            cost=_cost(),
        )
        assert abs(m_incremental(inp) - 1.0) < 1e-9


def m_incremental(inp: GeneralizedBenchmarkInput) -> float:
    return compute_benchmark(inp).incremental_recall


# ---------------------------------------------------------------------------
# False additions
# ---------------------------------------------------------------------------


class TestFalseAdditions:
    def test_counts_predictions_not_in_truth(self):
        h = make_built(hypothesis_id="g1")
        inp = GeneralizedBenchmarkInput(
            truth_ids=frozenset({"cand-1"}),
            strict_baseline_ids=frozenset({"cand-1"}),
            hypotheses=[h],
            predicted_id_by_hypothesis={"g1": "cand-bogus"},
            policy=make_policy(),
            cost=_cost(),
        )
        m = compute_benchmark(inp)
        assert m.false_additions == 1
        assert abs(m.false_addition_rate - 1.0) < 1e-9

    def test_zero_false_additions_when_all_in_truth(self):
        h = make_built(hypothesis_id="g1")
        inp = GeneralizedBenchmarkInput(
            truth_ids=frozenset({"cand-1"}),
            strict_baseline_ids=frozenset(),
            hypotheses=[h],
            predicted_id_by_hypothesis={"g1": "cand-1"},
            policy=make_policy(),
            cost=_cost(),
        )
        m = compute_benchmark(inp)
        assert m.false_additions == 0
        assert m.false_addition_rate == 0.0


# ---------------------------------------------------------------------------
# Coverage + risk-coverage
# ---------------------------------------------------------------------------


class TestRiskCoverage:
    def test_coverage_includes_strict_and_generalized(self):
        # strict found cand-1; generalized found cand-2; truth={cand-1,cand-2,cand-3}
        # coverage = 2/3
        h = make_built(hypothesis_id="g1")
        inp = GeneralizedBenchmarkInput(
            truth_ids=frozenset({"cand-1", "cand-2", "cand-3"}),
            strict_baseline_ids=frozenset({"cand-1"}),
            hypotheses=[h],
            predicted_id_by_hypothesis={"g1": "cand-2"},
            policy=make_policy(),
            cost=_cost(),
        )
        m = compute_benchmark(inp)
        assert abs(m.coverage - (2.0 / 3.0)) < 1e-9

    def test_risk_is_false_addition_rate(self):
        h = make_built(hypothesis_id="g1")
        inp = GeneralizedBenchmarkInput(
            truth_ids=frozenset({"cand-1"}),
            strict_baseline_ids=frozenset(),
            hypotheses=[h],
            predicted_id_by_hypothesis={"g1": "cand-bogus"},
            policy=make_policy(),
            cost=_cost(),
        )
        m = compute_benchmark(inp)
        assert abs(m.risk - 1.0) < 1e-9

    def test_risk_coverage_curve_present_and_monotonic_coverage(self):
        h1 = make_built(hypothesis_id="g1")
        h2 = make_built(hypothesis_id="g2",
                        rule_id="relax_ambiguity_margin",
                        failed=StrictCondition.no_critical_ambiguity)
        inp = GeneralizedBenchmarkInput(
            truth_ids=frozenset({"cand-1", "cand-2"}),
            strict_baseline_ids=frozenset(),
            hypotheses=[h1, h2],
            predicted_id_by_hypothesis={"g1": "cand-1", "g2": "cand-bogus"},
            policy=make_policy(),
            cost=_cost(),
        )
        m = compute_benchmark(inp)
        assert len(m.risk_coverage_curve) == 2
        coverages = [pt.coverage for pt in m.risk_coverage_curve]
        assert coverages == sorted(coverages)  # non-decreasing
        assert all(pt.k == i + 1 for i, pt in enumerate(m.risk_coverage_curve))

    def test_risk_at_90pct_coverage_present(self):
        h = make_built(hypothesis_id="g1")
        inp = GeneralizedBenchmarkInput(
            truth_ids=frozenset({"cand-1"}),
            strict_baseline_ids=frozenset(),
            hypotheses=[h],
            predicted_id_by_hypothesis={"g1": "cand-1"},
            policy=make_policy(),
            cost=_cost(),
        )
        m = compute_benchmark(inp)
        assert isinstance(m.risk_at_90pct_coverage, float)
        assert 0.0 <= m.risk_at_90pct_coverage <= 1.0


# ---------------------------------------------------------------------------
# Distance buckets — partition the population by generalization_distance
# ---------------------------------------------------------------------------


class TestDistanceBuckets:
    def test_bucket_edges_are_registered_and_ordered(self):
        # the bucket partition is a frozen registered constant (no free-text edges)
        assert isinstance(DISTANCE_BUCKET_EDGES, tuple)
        assert len(DISTANCE_BUCKET_EDGES) >= 3
        lowers = [e[0] for e in DISTANCE_BUCKET_EDGES]
        assert lowers[0] == 0.0
        assert lowers == sorted(lowers)
        # upper bounds strictly increase and the last is +inf
        uppers = [e[1] for e in DISTANCE_BUCKET_EDGES]
        assert uppers == sorted(uppers)
        assert uppers[-1] == float("inf")

    def test_buckets_partition_population(self):
        h1 = make_built(hypothesis_id="g1",
                        rule_id="relax_ambiguity_margin",
                        failed=StrictCondition.no_critical_ambiguity)  # d=0.2
        h2 = make_built(hypothesis_id="g2",
                        rule_id="relax_donor_site_precision",
                        failed=StrictCondition.donor_site_definite)    # d=0.3
        h3 = make_built(hypothesis_id="g3",
                        rule_id="relax_precondition_completeness",
                        failed=StrictCondition.preconditions_complete)  # d=0.5
        inp = GeneralizedBenchmarkInput(
            truth_ids=frozenset({"cand-1"}),
            strict_baseline_ids=frozenset(),
            hypotheses=[h1, h2, h3],
            predicted_id_by_hypothesis={"g1": "cand-1", "g2": "cand-x", "g3": "cand-y"},
            policy=make_policy(),
            cost=_cost(),
        )
        m = compute_benchmark(inp)
        assert sum(b.count for b in m.distance_buckets) == 3
        # correct + incorrect == count per bucket
        for b in m.distance_buckets:
            assert b.correct + b.incorrect == b.count

    def test_bucket_assigns_distance_correctly(self):
        # d=0.5 falls in the [0.5, 1.0) bucket, not [0.2, 0.5)
        h = make_built(hypothesis_id="g1",
                       rule_id="relax_precondition_completeness",
                       failed=StrictCondition.preconditions_complete)  # d=0.5
        inp = GeneralizedBenchmarkInput(
            truth_ids=frozenset({"cand-1"}),
            strict_baseline_ids=frozenset(),
            hypotheses=[h],
            predicted_id_by_hypothesis={"g1": "cand-1"},
            policy=make_policy(),
            cost=_cost(),
        )
        m = compute_benchmark(inp)
        # find the bucket containing d=0.5
        bucket = next(b for b in m.distance_buckets if b.lower <= 0.5 < b.upper)
        assert bucket.count == 1
        assert bucket.correct == 1
        assert bucket.incorrect == 0


# ---------------------------------------------------------------------------
# OOD ratio — re-derived from the registered policy
# ---------------------------------------------------------------------------


class TestOODRatio:
    def test_ood_ratio_counts_ood_predictions(self):
        # one OOD (free-text relaxation) + one in-vocab
        h_in = make_built(hypothesis_id="g_in")
        h_ood = make_built(hypothesis_id="g_ood").model_copy(
            update={"allowed_relaxation_ids": ["free_text_relaxation"]}
        )
        inp = GeneralizedBenchmarkInput(
            truth_ids=frozenset({"cand-1"}),
            strict_baseline_ids=frozenset(),
            hypotheses=[h_in, h_ood],
            predicted_id_by_hypothesis={"g_in": "cand-1", "g_ood": "cand-2"},
            policy=make_policy(),
            cost=_cost(),
        )
        m = compute_benchmark(inp)
        assert m.ood_count == 1
        assert abs(m.ood_ratio - 0.5) < 1e-9

    def test_ood_ratio_zero_when_all_in_vocab(self):
        h = make_built(hypothesis_id="g1")
        inp = GeneralizedBenchmarkInput(
            truth_ids=frozenset({"cand-1"}),
            strict_baseline_ids=frozenset(),
            hypotheses=[h],
            predicted_id_by_hypothesis={"g1": "cand-1"},
            policy=make_policy(),
            cost=_cost(),
        )
        m = compute_benchmark(inp)
        assert m.ood_count == 0
        assert m.ood_ratio == 0.0


# ---------------------------------------------------------------------------
# Cost
# ---------------------------------------------------------------------------


class TestCost:
    def test_cost_carried_through(self):
        h = make_built(hypothesis_id="g1")
        cost = CostReport(provider_calls=7, token_count=1234, wall_clock_seconds=9.25)
        inp = GeneralizedBenchmarkInput(
            truth_ids=frozenset({"cand-1"}),
            strict_baseline_ids=frozenset(),
            hypotheses=[h],
            predicted_id_by_hypothesis={"g1": "cand-1"},
            policy=make_policy(),
            cost=cost,
        )
        m = compute_benchmark(inp)
        assert m.cost.provider_calls == 7
        assert m.cost.token_count == 1234
        assert abs(m.cost.wall_clock_seconds - 9.25) < 1e-9


# ---------------------------------------------------------------------------
# Separate report — not the strict P5 / P7 structure
# ---------------------------------------------------------------------------


class TestSeparateReport:
    def test_metrics_not_strict_p7_metrics(self):
        assert GeneralizedBenchmarkMetrics is not P7StrictMetrics
        fields = set(GeneralizedBenchmarkMetrics.model_fields)
        # P7 Metrics uses candidate_recall / ranking_risk / abstention(int) — we do not
        assert "candidate_recall" not in fields
        assert "ranking_risk" not in fields
        assert "incremental_recall" in fields
        assert "distance_buckets" in fields
        assert "ood_ratio" in fields
        assert "false_additions" in fields

    def test_report_has_generalized_lane_semantics(self, tmp_path: Path):
        h = make_built(hypothesis_id="g1")
        inp = GeneralizedBenchmarkInput(
            truth_ids=frozenset({"cand-1"}),
            strict_baseline_ids=frozenset(),
            hypotheses=[h],
            predicted_id_by_hypothesis={"g1": "cand-1"},
            policy=make_policy(),
            cost=_cost(),
        )
        m = compute_benchmark(inp)
        md = tmp_path / "bench.md"
        js = tmp_path / "bench.json"
        write_benchmark_report(m, inp, md, js)
        assert md.exists() and js.exists()
        data = json.loads(js.read_text(encoding="utf-8"))
        # separate report structure: lane + output_semantics + population + metrics
        assert data["lane"] == "generalized"
        assert data["output_semantics"] == "exploratory_non_production"
        assert "metrics" in data
        assert "incremental_recall" in data["metrics"]
        assert "distance_buckets" in data["metrics"]
        # NOT the strict P7 three-way structure
        assert "baseline" not in data and "agent" not in data and "fixed" not in data
        text = md.read_text(encoding="utf-8")
        assert "exploratory" in text.lower()
        assert "incremental recall" in text.lower()
        assert "distance" in text.lower()
