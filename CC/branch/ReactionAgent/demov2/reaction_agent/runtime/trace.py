"""P4-T8 D/T/S/Δ/Y/L/R/A trace (final_design §20).

The audit trace maps: D = donor/reaction evidence IDs, T = transformation
hypothesis IDs, S = site hypothesis IDs, Δ = graph-edit IDs, Y = candidate
IDs, L = SourceReactionLedger / CandidateAnalogyLedger IDs, R = ranking /
applicability, A = final decision / abstention.
"""
from __future__ import annotations

from reaction_agent.schemas.result import StageSummary


def build_stage_summary(
    *,
    donor_evidence_ids: list[str],
    transformation_hypothesis_ids: list[str],
    site_hypothesis_ids: list[str],
    graph_edit_ids: list[str],
    candidate_ids: list[str],
    ledger_ids: list[str],
    rank_result: dict[str, str],
    decision_result: dict[str, str],
) -> StageSummary:
    """Build a deterministic D→T→S→Δ→Y→L→R/A StageSummary."""
    return StageSummary(
        donor_evidence_ids=list(donor_evidence_ids),
        transformation_hypothesis_ids=list(transformation_hypothesis_ids),
        site_hypothesis_ids=list(site_hypothesis_ids),
        graph_edit_ids=list(graph_edit_ids),
        candidate_ids=list(candidate_ids),
        ledger_ids=list(ledger_ids),
        rank_result=dict(rank_result),
        decision_result=dict(decision_result),
    )
