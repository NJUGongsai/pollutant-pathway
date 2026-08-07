"""P8-T4: Generalized-lane benchmark (final_plan §11.5).

Computes the six mandated metrics over a population of generalized
hypotheses evaluated against a strict baseline + held-out truth, and writes
an INDEPENDENT report to ``reports/p8/`` (not the strict P5 gate report nor
the P7 three-way evaluation structure).

Metrics (final_plan §11.5):
- incremental recall: new recalls vs the strict baseline (truth the strict
  lane missed that the generalized lane recovered)
- false additions: generalized predictions not in truth
- risk-coverage: a risk-coverage curve (risk = false-addition rate at each
  cumulative top-K) plus risk at 90% coverage
- distance buckets: population partitioned by generalization_distance
- OOD ratio: fraction of predictions citing relaxations outside the
  registered vocabulary (re-derived from the policy — no free text)
- cost: provider calls / tokens / wall-clock

Hard boundary (strict untouched): this module only ADDS new p8 code. It
imports the locked Stage A policy (``reaction_agent.p8.policy``) and schema
(``reaction_agent.p8.schemas``) for read-only vocabulary / OOD queries and
the validated hypothesis fields. It does NOT re-run the validation chain —
that is the T3 ranker's consumption gate; the benchmark is descriptive
statistics over a run's outputs.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator

from reaction_agent.schemas.common import NonEmptyStr, StrictModel
from reaction_agent.p8.policy import RelaxationPolicy
from reaction_agent.p8.schemas import GeneralizedHypothesis


# ---------------------------------------------------------------------------
# Distance-bucket edges (registered constant; exhaustive partition)
# ---------------------------------------------------------------------------

# Frozen bucket partition for generalization_distance. The last upper bound is
# +inf so every finite distance has a home. Edges are strictly increasing and
# the partition is exhaustive (no free-text buckets). A bucket [lo, hi) holds
# every prediction p with lo <= p.generalization_distance < hi.
DISTANCE_BUCKET_EDGES: tuple[tuple[float, float, str], ...] = (
    (0.0, 0.2, "0.0-0.2"),
    (0.2, 0.5, "0.2-0.5"),
    (0.5, 1.0, "0.5-1.0"),
    (1.0, float("inf"), "1.0+"),
)


# ---------------------------------------------------------------------------
# Cost
# ---------------------------------------------------------------------------


class CostReport(StrictModel):
    """Generalized-lane run cost (exploratory overhead)."""

    provider_calls: int = Field(ge=0)
    token_count: int = Field(ge=0)
    wall_clock_seconds: float = Field(ge=0.0)


# ---------------------------------------------------------------------------
# Resolved per-hypothesis prediction (policy-derived, not free text)
# ---------------------------------------------------------------------------


class GeneralizedPrediction(StrictModel):
    """A generalized hypothesis resolved to its predicted candidate id.

    ``generalization_distance`` comes from the validated hypothesis;
    ``is_ood`` is RE-DERIVED from the registered policy
    (``policy.is_ood(h.allowed_relaxation_ids)``) so the benchmark's OOD
    ratio is traceable to the policy vocabulary, not to free text on the run.
    """

    hypothesis_id: NonEmptyStr
    predicted_id: NonEmptyStr
    generalization_distance: float = Field(ge=0.0)
    is_ood: bool


# ---------------------------------------------------------------------------
# Benchmark input
# ---------------------------------------------------------------------------


class GeneralizedBenchmarkInput(StrictModel):
    """Population of generalized hypotheses vs a strict baseline + truth.

    ``hypotheses`` are the ranked generalized lane output (ranked order from
    T3). ``predicted_id_by_hypothesis`` maps each hypothesis to the candidate
    id it predicts; hypotheses without a mapping produced no candidate and are
    excluded from prediction-based metrics.
    """

    truth_ids: frozenset[str]
    strict_baseline_ids: frozenset[str]
    hypotheses: list[GeneralizedHypothesis]
    predicted_id_by_hypothesis: dict[str, str]
    policy: RelaxationPolicy
    cost: CostReport

    @model_validator(mode="after")
    def _mapping_references_known_hypotheses(self) -> "GeneralizedBenchmarkInput":
        known = {h.hypothesis_id for h in self.hypotheses}
        unknown = sorted(set(self.predicted_id_by_hypothesis) - known)
        if unknown:
            raise ValueError(
                f"predicted_id_by_hypothesis references unknown hypothesis id(s): "
                f"{unknown}; known ids: {sorted(known)}"
            )
        return self


# ---------------------------------------------------------------------------
# Metric records
# ---------------------------------------------------------------------------


class DistanceBucket(StrictModel):
    """One generalization_distance bucket of the population."""

    label: NonEmptyStr
    lower: float
    upper: float  # exclusive upper bound; +inf for the last bucket
    count: int = Field(ge=0)
    correct: int = Field(ge=0)
    incorrect: int = Field(ge=0)


class RiskCoveragePoint(StrictModel):
    """One point on the risk-coverage curve (cumulative top-K)."""

    k: int = Field(ge=1)
    coverage: float = Field(ge=0.0, le=1.0)
    risk: float = Field(ge=0.0, le=1.0)


class GeneralizedBenchmarkMetrics(StrictModel):
    """The six mandated T4 metrics. NOT the strict P7 ``Metrics`` class.

    P7 uses candidate_recall / ranking_risk / abstention(int); this class uses
    incremental_recall / false_additions / distance_buckets / ood_ratio — a
    separate, generalized-lane-specific metric set.
    """

    incremental_recall: float = Field(ge=0.0, le=1.0)
    false_additions: int = Field(ge=0)
    false_addition_rate: float = Field(ge=0.0, le=1.0)
    coverage: float = Field(ge=0.0, le=1.0)
    risk: float = Field(ge=0.0, le=1.0)
    risk_at_90pct_coverage: float = Field(ge=0.0, le=1.0)
    risk_coverage_curve: list[RiskCoveragePoint]
    distance_buckets: list[DistanceBucket]
    ood_ratio: float = Field(ge=0.0, le=1.0)
    ood_count: int = Field(ge=0)
    cost: CostReport


# ---------------------------------------------------------------------------
# Resolution: hypotheses -> predictions (policy-derived)
# ---------------------------------------------------------------------------


def _resolve_predictions(
    hypotheses: list[GeneralizedHypothesis],
    predicted_id_by_hypothesis: dict[str, str],
    policy: RelaxationPolicy,
) -> list[GeneralizedPrediction]:
    """Resolve each hypothesis that produced a candidate to a prediction.

    ``is_ood`` is re-derived from the registered policy (not free text).
    """
    predictions: list[GeneralizedPrediction] = []
    for h in hypotheses:
        predicted_id = predicted_id_by_hypothesis.get(h.hypothesis_id)
        if predicted_id is None:
            continue  # hypothesis produced no candidate (e.g. abstained)
        predictions.append(
            GeneralizedPrediction(
                hypothesis_id=h.hypothesis_id,
                predicted_id=predicted_id,
                generalization_distance=h.generalization_distance,
                is_ood=policy.is_ood(h.allowed_relaxation_ids),
            )
        )
    return predictions


# ---------------------------------------------------------------------------
# Metric computation
# ---------------------------------------------------------------------------


def compute_benchmark(inp: GeneralizedBenchmarkInput) -> GeneralizedBenchmarkMetrics:
    """Compute the six mandated generalized-lane benchmark metrics."""
    truth = set(inp.truth_ids)
    strict = set(inp.strict_baseline_ids)
    predictions = _resolve_predictions(
        inp.hypotheses, dict(inp.predicted_id_by_hypothesis), inp.policy
    )
    pred_ids = {p.predicted_id for p in predictions}

    # 1. incremental recall — of the truth the strict lane MISSED, the
    #    fraction the generalized lane recovered (new recalls vs strict).
    missed = truth - strict
    recovered = (pred_ids & truth) - strict
    incremental_recall = (len(recovered) / len(missed)) if missed else 0.0

    # 2. false additions — generalized predictions not in truth.
    false_additions_set = pred_ids - truth
    false_additions = len(false_additions_set)
    false_addition_rate = (false_additions / len(pred_ids)) if pred_ids else 0.0

    # 3. coverage — |(strict ∪ generalized) ∩ truth| / |truth|.
    combined_correct = (strict | pred_ids) & truth
    coverage = (len(combined_correct) / len(truth)) if truth else 0.0

    # 4. risk — false-addition rate over generalized predictions.
    risk = false_addition_rate

    # risk-coverage curve — cumulative top-K, strict coverage counted free.
    strict_correct = strict & truth
    curve: list[RiskCoveragePoint] = []
    seen_correct: set[str] = set(strict_correct)
    false_so_far = 0
    for k, p in enumerate(predictions, start=1):
        if p.predicted_id in truth:
            seen_correct.add(p.predicted_id)
        else:
            false_so_far += 1
        cov = (len(seen_correct) / len(truth)) if truth else 0.0
        rk = (false_so_far / k)
        curve.append(RiskCoveragePoint(k=k, coverage=cov, risk=rk))

    # risk at 90% coverage — the risk at the first k reaching >=0.9 coverage,
    # else the last point's risk (or 0.0 if the curve is empty).
    risk_at_90 = 0.0
    for pt in curve:
        if pt.coverage >= 0.9:
            risk_at_90 = pt.risk
            break
    else:
        risk_at_90 = curve[-1].risk if curve else 0.0

    # 5. distance buckets — partition predictions by generalization_distance.
    buckets: list[DistanceBucket] = []
    for lo, hi, label in DISTANCE_BUCKET_EDGES:
        in_bucket = [p for p in predictions if lo <= p.generalization_distance < hi]
        correct = sum(1 for p in in_bucket if p.predicted_id in truth)
        incorrect = len(in_bucket) - correct
        buckets.append(
            DistanceBucket(
                label=label, lower=lo, upper=hi,
                count=len(in_bucket), correct=correct, incorrect=incorrect,
            )
        )

    # 6. OOD ratio — re-derived from the registered policy.
    ood_count = sum(1 for p in predictions if p.is_ood)
    ood_ratio = (ood_count / len(predictions)) if predictions else 0.0

    return GeneralizedBenchmarkMetrics(
        incremental_recall=incremental_recall,
        false_additions=false_additions,
        false_addition_rate=false_addition_rate,
        coverage=coverage,
        risk=risk,
        risk_at_90pct_coverage=risk_at_90,
        risk_coverage_curve=curve,
        distance_buckets=buckets,
        ood_ratio=ood_ratio,
        ood_count=ood_count,
        cost=inp.cost,
    )


# ---------------------------------------------------------------------------
# Independent report (separate from strict P5 / P7 structures)
# ---------------------------------------------------------------------------


def _metrics_to_dict(m: GeneralizedBenchmarkMetrics) -> dict:
    return {
        "incremental_recall": m.incremental_recall,
        "false_additions": m.false_additions,
        "false_addition_rate": m.false_addition_rate,
        "coverage": m.coverage,
        "risk": m.risk,
        "risk_at_90pct_coverage": m.risk_at_90pct_coverage,
        "risk_coverage_curve": [
            {"k": pt.k, "coverage": pt.coverage, "risk": pt.risk}
            for pt in m.risk_coverage_curve
        ],
        "distance_buckets": [
            {
                "label": b.label, "lower": b.lower, "upper": b.upper,
                "count": b.count, "correct": b.correct, "incorrect": b.incorrect,
            }
            for b in m.distance_buckets
        ],
        "ood_ratio": m.ood_ratio,
        "ood_count": m.ood_count,
        "cost": {
            "provider_calls": m.cost.provider_calls,
            "token_count": m.cost.token_count,
            "wall_clock_seconds": m.cost.wall_clock_seconds,
        },
    }


def write_benchmark_report(
    metrics: GeneralizedBenchmarkMetrics,
    inp: GeneralizedBenchmarkInput,
    md_path: Path | str,
    json_path: Path | str,
) -> None:
    """Write the independent generalized-lane benchmark report.

    Produces a JSON artifact and a human-readable Markdown report. The
    structure is generalized-lane-specific (lane / output_semantics /
    population / metrics) and is NOT the strict P5 gate report (Summary /
    Upstream status / Gate items) nor the P7 three-way eval (baseline /
    agent / fixed).
    """
    md_path = Path(md_path)
    json_path = Path(json_path)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)

    n_predictions = sum(
        1 for h in inp.hypotheses if h.hypothesis_id in inp.predicted_id_by_hypothesis
    )
    report = {
        "lane": "generalized",
        "output_semantics": "exploratory_non_production",
        "policy": {
            "policy_id": inp.policy.policy_id,
            "version": inp.policy.version,
            "content_hash": inp.policy.content_hash,
        },
        "population": {
            "n_hypotheses": len(inp.hypotheses),
            "n_predictions": n_predictions,
            "n_truth": len(inp.truth_ids),
            "n_strict_baseline": len(inp.strict_baseline_ids),
        },
        "metrics": _metrics_to_dict(metrics),
    }
    with json_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
        f.write("\n")

    # Markdown — human-readable, explicitly exploratory / non-production.
    lines: list[str] = []
    lines.append("# P8 Generalized-Lane Benchmark Report")
    lines.append("")
    lines.append("> **Exploratory, NON-production lane.** Results here are not "
                 "production decisions; they quantify what the generalized "
                 "(relaxed-structure) lane adds beyond the strict baseline.")
    lines.append("")
    lines.append(f"- Lane: `{report['lane']}`")
    lines.append(f"- Output semantics: `{report['output_semantics']}`")
    lines.append(f"- Policy: `{inp.policy.policy_id}` v`{inp.policy.version}` "
                 f"(content_hash `{inp.policy.content_hash[:12]}…`)")
    lines.append("")
    lines.append("## Population")
    lines.append("")
    lines.append("| Item | Count |")
    lines.append("|------|-------|")
    lines.append(f"| Hypotheses | {report['population']['n_hypotheses']} |")
    lines.append(f"| Predictions | {report['population']['n_predictions']} |")
    lines.append(f"| Truth (held-out) | {report['population']['n_truth']} |")
    lines.append(f"| Strict baseline | {report['population']['n_strict_baseline']} |")
    lines.append("")
    lines.append("## Metrics")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    lines.append(f"| Incremental recall | {metrics.incremental_recall:.4f} |")
    lines.append(f"| False additions | {metrics.false_additions} "
                 f"(rate {metrics.false_addition_rate:.4f}) |")
    lines.append(f"| Coverage | {metrics.coverage:.4f} |")
    lines.append(f"| Risk | {metrics.risk:.4f} |")
    lines.append(f"| Risk @ 90% coverage | {metrics.risk_at_90pct_coverage:.4f} |")
    lines.append(f"| OOD ratio | {metrics.ood_ratio:.4f} "
                 f"(count {metrics.ood_count}) |")
    lines.append(f"| Cost | {metrics.cost.provider_calls} calls / "
                 f"{metrics.cost.token_count} tokens / "
                 f"{metrics.cost.wall_clock_seconds:.2f}s |")
    lines.append("")
    lines.append("## Risk–coverage curve")
    lines.append("")
    lines.append("| k | coverage | risk |")
    lines.append("|---|----------|------|")
    for pt in metrics.risk_coverage_curve:
        lines.append(f"| {pt.k} | {pt.coverage:.4f} | {pt.risk:.4f} |")
    lines.append("")
    lines.append("## Distance buckets")
    lines.append("")
    lines.append("| Bucket | Count | Correct | Incorrect |")
    lines.append("|--------|-------|---------|-----------|")
    for b in metrics.distance_buckets:
        upper = "inf" if b.upper == float("inf") else f"{b.upper}"
        lines.append(
            f"| `{b.label}` [{b.lower}, {upper}) | {b.count} | "
            f"{b.correct} | {b.incorrect} |"
        )
    lines.append("")
    lines.append("_This report is structurally independent of the strict P5 "
                 "gate report and the P7 three-way evaluation; it covers only "
                 "the generalized exploratory lane._")
    lines.append("")
    md_path.write_text("\n".join(lines), encoding="utf-8")


__all__ = [
    "DISTANCE_BUCKET_EDGES",
    "CostReport",
    "GeneralizedPrediction",
    "GeneralizedBenchmarkInput",
    "DistanceBucket",
    "RiskCoveragePoint",
    "GeneralizedBenchmarkMetrics",
    "compute_benchmark",
    "write_benchmark_report",
]
