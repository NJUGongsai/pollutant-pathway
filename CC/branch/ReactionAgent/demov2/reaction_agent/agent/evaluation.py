"""P7 T7 agent incremental evaluation (additive).

Three-way comparison (deterministic baseline / agent evidence expansion+
selection / fixed non-agent expansion) over 7 metrics, plus a scripted
provider that drives the agent loop with a deterministic action stream for
repeatable evaluation. Closes P7-T6-02 via the end-to-end induction pin in
``tests/p7/test_t7_evaluation.py`` (the loop's grounding + allowlist reject
every invention -> 6 HardGateCounters all-zero).

Full-path imports; does NOT touch ``grounding.py`` / ``policy.py`` /
``reporter.py`` / ``baseline.py`` / ``provider.py`` / ``__init__.py``.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass

from reaction_agent.agent.loop import AgentLoop, AgentRunResult
from reaction_agent.agent.provider import ProviderResponse, ProviderSpec
from reaction_agent.schemas.result import PredictionResult

__all__ = [
    "ScriptedProvider",
    "ThreeWayResult",
    "Metrics",
    "run_three_way",
    "compute_metrics",
    "write_report",
]


class ScriptedProvider:
    """Deterministic provider that returns one scripted action per call.

    ``content`` is the next action dict from the script; when the script is
    exhausted, an auto-``stop`` is returned (the loop ends cleanly).
    ``reset()`` rewinds the script for repeated deterministic runs (T7
    repeated-run agreement metric).
    """

    def __init__(self, spec: ProviderSpec, actions: list[dict]):
        self.spec = spec
        self._actions = list(actions)
        self._i = 0

    def reset(self) -> None:
        self._i = 0

    def call(self, request):  # noqa: ARG002 (Provider protocol)
        if self._i >= len(self._actions):
            return ProviderResponse(
                provider=self.spec.provider,
                model=self.spec.model,
                content={"tool": "stop"},
            )
        action = self._actions[self._i]
        self._i += 1
        return ProviderResponse(
            provider=self.spec.provider,
            model=self.spec.model,
            content=dict(action),
        )


@dataclass(frozen=True)
class ThreeWayResult:
    """Three-way comparison on one substrate.

    ``baseline`` = deterministic P3+P4 baseline. ``agent`` = the agent loop's
    final run (evidence expansion + selection). ``fixed`` = a deterministic
    non-agent expansion (all baseline candidates, no LLM). ``agent_runs`` =
    the N repeated agent runs (for repeated-run agreement).
    """

    baseline: PredictionResult
    agent: AgentRunResult
    fixed: AgentRunResult
    agent_runs: tuple[AgentRunResult, ...]


def _fixed_non_agent_expansion(baseline: PredictionResult) -> AgentRunResult:
    """Deterministic non-agent expansion: select ALL baseline candidates +
    ground ALL baseline evidence (no LLM, no selection). This is the
    ``fixed non-agent expansion`` arm of the three-way comparison.
    """
    cids = tuple(c.candidate_id for c in baseline.candidates)
    eids = (
        tuple(baseline.stage_summary.donor_evidence_ids)
        if baseline.stage_summary is not None
        else ()
    )
    return AgentRunResult(
        baseline=baseline,
        selected_candidate_ids=cids,
        actions=(),
        tool_calls=0,
        steps=0,
        abstained=(len(cids) == 0),
        grounded_evidence_ids=eids,
        rejections=(),
    )


def run_three_way(
    substrate: str,
    *,
    baseline_gate,
    agent_provider: ScriptedProvider,
    runs: int = 3,
) -> ThreeWayResult:
    """Run the three-way comparison on one substrate.

    The agent loop runs ``runs`` times (same scripted provider, reset each
    run) for the repeated-run agreement metric. The baseline is obtained via
    the gate (idempotent — same run_id across calls). The provider is the
    single source of truth for the agent's scripted action stream.
    """
    baseline = baseline_gate.obtain_baseline()
    agent_runs: list[AgentRunResult] = []
    for _ in range(max(1, runs)):
        agent_provider.reset()
        loop = AgentLoop(provider=agent_provider, baseline_gate=baseline_gate)
        agent_runs.append(loop.run(substrate, max_steps=100))
    fixed = _fixed_non_agent_expansion(baseline)
    return ThreeWayResult(
        baseline=baseline,
        agent=agent_runs[-1],
        fixed=fixed,
        agent_runs=tuple(agent_runs),
    )


@dataclass(frozen=True)
class Metrics:
    """The 7 T7 evaluation metrics (all sourced from typed results)."""

    candidate_recall: float  # |agent ∩ baseline| / |baseline candidates|
    ranking_risk: float  # top-K overlap (agent top-K vs baseline top-K)
    abstention: int  # 1 if agent abstained else 0
    evidence_quality: int  # # unique grounded evidence IDs agent referenced
    tool_calls: int  # agent tool-call count
    latency_token_cost: int  # provider call count (= agent steps)
    repeated_run_agreement: bool  # all N agent runs identical selection


def compute_metrics(three: ThreeWayResult) -> Metrics:
    """Compute the 7 metrics from a three-way result."""
    baseline_cids = [c.candidate_id for c in three.baseline.candidates]
    baseline_cid_set = set(baseline_cids)
    agent_sel = list(three.agent.selected_candidate_ids)
    agent_sel_set = set(agent_sel)

    # 1. candidate recall
    if baseline_cids:
        recall = len(agent_sel_set & baseline_cid_set) / len(baseline_cids)
    else:
        recall = 0.0

    # 2. ranking/risk — top-K overlap (baseline ranked by score vs agent order)
    baseline_ranked = [
        c.candidate_id
        for c in sorted(
            three.baseline.candidates,
            key=lambda c: (c.ranking_score is not None,
                           c.ranking_score if c.ranking_score is not None else -1.0),
            reverse=True,
        )
    ]
    k = min(3, len(baseline_ranked))
    if k > 0:
        top_overlap = len(set(baseline_ranked[:k]) & set(agent_sel[:k])) / k
    else:
        top_overlap = 0.0

    # 3. abstention
    abstention = 1 if three.agent.abstained else 0

    # 4. evidence quality
    evidence_quality = len(three.agent.grounded_evidence_ids)

    # 5. tool calls
    tool_calls = three.agent.tool_calls

    # 6. latency/token/cost (provider call count = steps)
    latency_token_cost = three.agent.steps

    # 7. repeated-run agreement
    selections = tuple(r.selected_candidate_ids for r in three.agent_runs)
    repeated_agreement = len(set(selections)) == 1

    return Metrics(
        candidate_recall=recall,
        ranking_risk=top_overlap,
        abstention=abstention,
        evidence_quality=evidence_quality,
        tool_calls=tool_calls,
        latency_token_cost=latency_token_cost,
        repeated_run_agreement=repeated_agreement,
    )


def write_report(three: ThreeWayResult, metrics: Metrics, path) -> None:
    """Write the T7 evaluation report as JSON.

    Data is traceable to the typed result (baseline run_id carried into the
    report; agent/fixed selections are grounded IDs from the typed run).
    """
    os.makedirs(os.path.dirname(str(path)) or ".", exist_ok=True)
    data = {
        "baseline": {
            "run_id": three.baseline.run_id,
            "status": three.baseline.status.value,
            "n_candidates": len(three.baseline.candidates),
            "normalized_query": three.baseline.normalized_query,
        },
        "agent": {
            "selected_candidate_ids": list(three.agent.selected_candidate_ids),
            "grounded_evidence_ids": list(three.agent.grounded_evidence_ids),
            "tool_calls": three.agent.tool_calls,
            "steps": three.agent.steps,
            "abstained": three.agent.abstained,
            "rejections": len(three.agent.rejections),
        },
        "fixed": {
            "selected_candidate_ids": list(three.fixed.selected_candidate_ids),
            "grounded_evidence_ids": list(three.fixed.grounded_evidence_ids),
        },
        "metrics": {
            "candidate_recall": metrics.candidate_recall,
            "ranking_risk": metrics.ranking_risk,
            "abstention": metrics.abstention,
            "evidence_quality": metrics.evidence_quality,
            "tool_calls": metrics.tool_calls,
            "latency_token_cost": metrics.latency_token_cost,
            "repeated_run_agreement": metrics.repeated_run_agreement,
        },
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
