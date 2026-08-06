"""P7 T5 reporter (additive).

Projects a typed ``PredictionResult`` into a STRUCTURED report — data only;
the host renders structures / scores / IDs. Gate P7 prerequisite
"report matches result": every report field is sourced from a typed
``PredictionResult`` field (provenance map exposed for audit); report-only
values raise ``ReportError`` or are disclosed as explicit limitations —
nothing is fabricated.

- abstention / failure are presented HONESTLY (a typed failed/abstained result
  is reported as such, never sugar-coated as success; no fake candidates).
- limitations disclose scope gaps the typed result does not carry (e.g.,
  counterevidence is aggregated upstream in the P4 pipeline and is NOT
  projected onto ``PredictionResult`` — the reporter does not invent it).
- the report does NOT mutate the typed result: ``CandidateSummary`` carries
  only immutable scalars + tuples (no shared list references with the typed
  ``Candidate``).

Full-path imports only — does NOT touch ``agent/__init__.py`` (deepseek's
domain) and does not modify ``grounding.py`` / ``policy.py`` / ``provider.py``
/ ``loop.py`` / ``baseline.py``.
"""
from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping, Optional

from reaction_agent.schemas.candidate import Candidate
from reaction_agent.schemas.result import PredictionResult

__all__ = [
    "ReportError",
    "CandidateSummary",
    "StructuredReport",
    "build_report",
    "get_sourced_field",
]


class ReportError(ValueError):
    """Typed error: a requested report field is not sourced from the typed
    result (report-only value) — never fabricated, never a silent pass."""


@dataclass(frozen=True)
class CandidateSummary:
    """Immutable per-candidate summary (scalars + tuples only — no shared
    mutable references with the typed ``Candidate``)."""

    candidate_id: str
    canonical_product: str
    lane: str
    ranking_score: Optional[float]
    support_tier: Optional[str]
    applicability: str
    transformation_ids: tuple[str, ...]
    site_ids: tuple[str, ...]
    source_ledger_ids: tuple[str, ...]
    candidate_analogy_ledger_id: Optional[str]
    support_lineage_ids: tuple[str, ...]


def _candidate_summary(c: Candidate) -> CandidateSummary:
    return CandidateSummary(
        candidate_id=c.candidate_id,
        canonical_product=c.canonical_product,
        lane=c.lane.value,
        ranking_score=c.ranking_score,
        support_tier=c.support_tier,
        applicability=c.applicability.value,
        transformation_ids=tuple(c.transformation_ids),
        site_ids=tuple(c.site_ids),
        source_ledger_ids=tuple(c.source_ledger_ids),
        candidate_analogy_ledger_id=c.candidate_analogy_ledger_id,
        support_lineage_ids=tuple(c.support_lineage_ids),
    )


@dataclass(frozen=True)
class StructuredReport:
    """Frozen, typed, read-only structured projection of a ``PredictionResult``.

    Every data field is sourced from the typed result; ``field_provenance``
    maps each report field to its typed source path (audit trace).
    ``limitations`` discloses scope gaps the typed result does not carry.
    ``top_k_candidates`` is empty for abstained/failed results (no fake
    candidates). Dict fields are ``MappingProxyType`` (read-only).
    """

    run_id: str
    status: str
    decision: str
    normalized_query: str
    snapshot_id: str
    top_k_candidates: tuple[CandidateSummary, ...]
    donor_evidence_ids: tuple[str, ...]
    transformation_ids: tuple[str, ...]
    site_ids: tuple[str, ...]
    source_ledger_ids: tuple[str, ...]
    candidate_analogy_ledger_ids: tuple[str, ...]
    applicability: tuple[tuple[str, str], ...]
    support_tiers: tuple[tuple[str, str], ...]
    ranking_scores: tuple[tuple[str, Optional[float]], ...]
    rank_result: Mapping[str, Any]
    abstention: Optional[tuple[str, str, str]]  # (reason_code, stage, detail)
    failure: Optional[tuple[str, str]]  # (reason_code, detail)
    partial_reason: Optional[str]
    limitations: tuple[str, ...]
    field_provenance: Mapping[str, str]


def _abstention_tuple(result: PredictionResult) -> Optional[tuple[str, str, str]]:
    if result.abstention is None:
        return None
    a = result.abstention
    rc = a.reason_code.value if hasattr(a.reason_code, "value") else str(a.reason_code)
    return (rc, a.stage, a.detail)


def _failure_tuple(result: PredictionResult) -> Optional[tuple[str, str]]:
    if result.failure is None:
        return None
    f = result.failure
    rc = f.reason_code.value if hasattr(f.reason_code, "value") else str(f.reason_code)
    return (rc, f.detail)


def _limitations(result: PredictionResult) -> tuple[str, ...]:
    """Explicit disclosure of scope gaps the typed result does not carry."""
    lims: list[str] = [
        "structured data only — host renders structures/scores/IDs",
        "conflicts: not surfaced on typed PredictionResult "
        "(P4 counterevidence aggregated upstream, not projected to result)",
    ]
    if result.stage_summary is None:
        lims.append(
            "stage_summary absent — donor/ledger summaries empty (fail-closed)"
        )
    lims.append(
        "evidence_kind not carried on typed PredictionResult "
        "(scope follows the producing kernel, not the result)"
    )
    return tuple(lims)


def _provenance() -> Mapping[str, str]:
    """Map each report data field -> typed source path (audit trace)."""
    return MappingProxyType({
        "run_id": "result.run_id",
        "status": "result.status",
        "decision": "result.decision",
        "normalized_query": "result.normalized_query",
        "snapshot_id": "result.snapshot_id",
        "top_k_candidates": "result.candidates (top-K by ranking_score)",
        "donor_evidence_ids": "stage_summary.donor_evidence_ids",
        "transformation_ids": "candidate.transformation_ids (union)",
        "site_ids": "candidate.site_ids (union)",
        "source_ledger_ids": "stage_summary.ledger_ids",
        "candidate_analogy_ledger_ids": "candidate.candidate_analogy_ledger_id",
        "applicability": "candidate.applicability",
        "support_tiers": "candidate.support_tier",
        "ranking_scores": "candidate.ranking_score",
        "rank_result": "stage_summary.rank_result",
        "abstention": "result.abstention",
        "failure": "result.failure",
        "partial_reason": "result.partial_reason",
    })


def build_report(result: PredictionResult, *, top_k: int = 3) -> StructuredReport:
    """Build a structured report projected from a typed ``PredictionResult``.

    Every field is sourced from the typed result (see ``field_provenance``).
    Abstained/failed results are reported honestly — ``top_k_candidates`` is
    empty (no fake candidates). Limitations disclose scope gaps. The report
    does not mutate the typed result (immutable summaries).
    """
    ss = result.stage_summary
    donor_ids = tuple(ss.donor_evidence_ids) if ss is not None else ()
    source_ledger_ids = tuple(ss.ledger_ids) if ss is not None else ()
    rank_result = MappingProxyType(dict(ss.rank_result)) if ss is not None else MappingProxyType({})

    candidates = list(result.candidates)
    # Top-K strict by ranking_score desc (None scores sort last).
    ranked = sorted(
        candidates,
        key=lambda c: (c.ranking_score is not None, c.ranking_score if c.ranking_score is not None else -1.0),
        reverse=True,
    )
    top = ranked[:top_k] if top_k > 0 else []
    top_summaries = tuple(_candidate_summary(c) for c in top)

    # Union IDs across ALL typed candidates (not just top-K) — the report
    # reflects the full typed candidate set's evidence/structure IDs.
    all_t = tuple(dict.fromkeys(t for c in candidates for t in c.transformation_ids))
    all_s = tuple(dict.fromkeys(s for c in candidates for s in c.site_ids))
    all_cal = tuple(
        dict.fromkeys(
            c.candidate_analogy_ledger_id
            for c in candidates
            if c.candidate_analogy_ledger_id
        )
    )

    applicability = tuple(
        (c.candidate_id, c.applicability.value) for c in candidates
    )
    support_tiers = tuple((c.candidate_id, c.support_tier) for c in candidates)
    ranking_scores = tuple((c.candidate_id, c.ranking_score) for c in candidates)

    return StructuredReport(
        run_id=result.run_id,
        status=result.status.value if hasattr(result.status, "value") else str(result.status),
        decision=result.decision.value if hasattr(result.decision, "value") else str(result.decision),
        normalized_query=result.normalized_query,
        snapshot_id=result.snapshot_id,
        top_k_candidates=top_summaries,
        donor_evidence_ids=donor_ids,
        transformation_ids=all_t,
        site_ids=all_s,
        source_ledger_ids=source_ledger_ids,
        candidate_analogy_ledger_ids=all_cal,
        applicability=applicability,
        support_tiers=support_tiers,
        ranking_scores=ranking_scores,
        rank_result=rank_result,
        abstention=_abstention_tuple(result),
        failure=_failure_tuple(result),
        partial_reason=result.partial_reason,
        limitations=_limitations(result),
        field_provenance=_provenance(),
    )


def get_sourced_field(report: StructuredReport, name: str) -> Any:
    """Return the value of a report field sourced from the typed result.

    Raises ``ReportError`` if ``name`` is not a sourced field (report-only
    value) — never fabricated.
    """
    if name not in report.field_provenance:
        raise ReportError(
            f"report field {name!r} is not sourced from the typed result "
            f"(report-only value — not fabricated; available sourced fields: "
            f"{sorted(report.field_provenance)})"
        )
    return getattr(report, name)
