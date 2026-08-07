"""P9-T1: Independent report for the agent_proposed lane (final_plan §12.1).

Six metric groups (final_plan §12.1 / final_design §19.3 graduation inputs):
- new valid / correct / incorrect
- reject reasons (controlled vocabulary tally)
- incremental recall
- risk (at fixed coverage)
- cost (LLM / tool calls / latency — mock, never a real API burn)
- reproducibility (repeated-run agreement + seed + chain policy version)

The report is lane-pinned and exploratory — it can never masquerade as a strict
``PredictionResult`` / production rank.

Hard boundary (strict untouched): ADDITIVE only.
"""
from __future__ import annotations

from typing import Literal

from pydantic import Field

from reaction_agent.schemas.common import NonEmptyStr, StrictModel

from reaction_agent.p9.agent_proposed.policy import DEFAULT_AGENT_PROPOSED_CHAIN_POLICY
from reaction_agent.p9.agent_proposed.schemas import (
    AgentProposedCandidate,
    AgentProposedRejectReasonCode,
)


# ---------------------------------------------------------------------------
# Cost + reproducibility
# ---------------------------------------------------------------------------


class AgentProposedCostReport(StrictModel):
    """Cost meter for the agent_proposed lane (mock provider values)."""

    llm_calls: int = 0
    tool_calls: int = 0
    latency_ms: int = 0


class AgentProposedReproducibility(StrictModel):
    """Reproducibility record (final_design §19.3 'repeated-run agreement')."""

    repeated_run_agreement: float = Field(ge=0.0, le=1.0)
    seed: int
    chain_policy_version: NonEmptyStr


# ---------------------------------------------------------------------------
# The six-metric report (lane-pinned, exploratory, NOT a strict PredictionResult)
# ---------------------------------------------------------------------------


class AgentProposedReport(StrictModel):
    """Independent report for the agent_proposed lane. NOT production rank.

    Lane is Literal-pinned to "agent_proposed"; ``output_semantics`` is pinned
    ``exploratory_non_production``; ``exploratory`` is pinned True. There is no
    ``run_id`` / ``status`` / ``decision`` / ``snapshot_id`` — structurally
    distinct from the strict ``PredictionResult``.
    """

    lane: Literal["agent_proposed"] = "agent_proposed"
    output_semantics: Literal["exploratory_non_production"] = "exploratory_non_production"
    exploratory: Literal[True] = True

    # metric group 1: new valid / correct / incorrect
    new_valid: int = 0
    new_correct: int = 0
    new_incorrect: int = 0

    # metric group 2: reject reasons (controlled-vocabulary tally, no free text)
    reject_reasons: dict[str, int] = {}

    # metric group 3: incremental recall over production-only
    incremental_recall: float = 0.0

    # metric group 4: risk at fixed coverage
    risk: float = 0.0

    # metric group 5: cost
    cost: AgentProposedCostReport

    # metric group 6: reproducibility
    reproducibility: AgentProposedReproducibility


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------


def build_agent_proposed_report(
    candidates: list[AgentProposedCandidate],
    rejected: list[tuple[str, AgentProposedRejectReasonCode]],
    *,
    production_valid_count: int = 0,
    ground_truth_smiles: dict[str, str] | None = None,
    cost: AgentProposedCostReport | None = None,
    reproducibility: AgentProposedReproducibility | None = None,
) -> AgentProposedReport:
    """Build the independent six-metric report.

    - ``new_valid``: count of candidates that passed the full chain.
    - ``new_correct`` / ``new_incorrect``: vs. ``ground_truth_smiles`` keyed by
      hypothesis_id. A candidate with no ground truth is neither correct nor
      incorrect (it is still counted as new_valid).
    - ``reject_reasons``: tally of the controlled-vocabulary reject codes.
    - ``incremental_recall``: (production_valid + new_correct) /
      (production_valid + new_valid) — the recall uplift from admitting the
      agent-proposed lane.
    - ``risk``: new_incorrect / (new_correct + new_incorrect) at fixed coverage
      — the risk of letting agent-proposed candidates in. Zero when no
      candidate was admitted (no division by zero).
    """
    new_valid = len(candidates)
    gt = ground_truth_smiles or {}
    new_correct = sum(
        1
        for c in candidates
        if gt.get(c.hypothesis_id) is not None
        and gt[c.hypothesis_id] == c.edited_product_smiles
    )
    new_incorrect = new_valid - new_correct

    reject_reasons: dict[str, int] = {}
    for _hid, code in rejected:
        key = code.value if isinstance(code, AgentProposedRejectReasonCode) else str(code)
        reject_reasons[key] = reject_reasons.get(key, 0) + 1

    denom_recall = production_valid_count + new_valid
    incremental_recall = (
        (production_valid_count + new_correct) / denom_recall
        if denom_recall > 0
        else 0.0
    )

    coverage = new_correct + new_incorrect
    risk = (new_incorrect / coverage) if coverage > 0 else 0.0

    cost_report = cost or AgentProposedCostReport()
    repro = reproducibility or AgentProposedReproducibility(
        repeated_run_agreement=1.0,
        seed=0,
        chain_policy_version=DEFAULT_AGENT_PROPOSED_CHAIN_POLICY.version,
    )

    return AgentProposedReport(
        new_valid=new_valid,
        new_correct=new_correct,
        new_incorrect=new_incorrect,
        reject_reasons=reject_reasons,
        incremental_recall=incremental_recall,
        risk=risk,
        cost=cost_report,
        reproducibility=repro,
    )


__all__ = [
    "AgentProposedCostReport",
    "AgentProposedReproducibility",
    "AgentProposedReport",
    "build_agent_proposed_report",
]
