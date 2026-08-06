"""P7 T4 grounding guard (additive).

Validates the agent's claims (``ProductionSelectionHypothesis`` + agent-
selected candidate/evidence IDs) against the TYPED baseline
``PredictionResult``, enforcing the no-invention boundary at the grounding
layer:

- **IDs belong to run**: every candidate / evidence / lineage /
  transformation / site / source_ledger id the agent references must exist in
  the typed ``PredictionResult``. Unknown id -> typed ``GroundingError``.
- **structures from typed result**: any structure (canonical_product SMILES)
  the agent claims must come from a typed candidate (not invented). Invented
  SMILES -> ``GroundingError``.
- **rank/lane/ledger immutable**: ``GroundedRun`` is a frozen dataclass with
  no setters for rank/lane/ledger; ``frozen_candidate_view`` returns a
  defensive ``model_copy()`` so an agent cannot mutate the typed result via
  the view. Agents read typed values, never write.
- **unsupported claims rejected**: a hypothesis whose transform+site both
  resolve but never co-occur in a single typed candidate is rejected
  (the agent cannot synthesize a new candidate from loose ids).
- **unknown IDs -> typed error** throughout.

This module is additive and uses full-path imports only; it does NOT touch
``agent/__init__.py`` (deepseek's exclusive domain in Phase 2) and does not
modify ``policy.py`` / ``provider.py`` / ``loop.py`` / ``baseline.py``.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from reaction_agent.schemas.candidate import Candidate
from reaction_agent.schemas.hypothesis import ProductionSelectionHypothesis
from reaction_agent.schemas.result import PredictionResult

__all__ = [
    "GroundingError",
    "GroundedRun",
    "build_grounded_run",
    "assert_id_belongs_to_run",
    "assert_structure_from_result",
    "validate_hypothesis",
    "frozen_candidate_view",
]


class GroundingError(ValueError):
    """Typed error: an agent claim references an ID/structure not in the run,
    or attempts an unsupported (non-co-occurring) claim. Never a bare
    exception, never a fabricated PASS."""


@dataclass(frozen=True)
class GroundedRun:
    """Frozen, typed, read-only view of the baseline run.

    Exposes only read-only ID sets + the typed candidates (as an immutable
    tuple). There are NO setters for rank/lane/ledger — immutability by
    construction. Agents ground against this view; they cannot mutate it.
    """

    run_id: str
    candidate_ids: frozenset[str]
    evidence_ids: frozenset[str]
    lineage_ids: frozenset[str]
    transformation_ids: frozenset[str]
    site_ids: frozenset[str]
    source_ledger_ids: frozenset[str]
    candidate_analogy_ledger_ids: frozenset[str]
    canonical_products: frozenset[str]
    candidates: tuple[Candidate, ...]


def _collect_evidence_ids(result: PredictionResult) -> frozenset[str]:
    """Evidence reaction IDs observable in the typed result (stage_summary
    donor_evidence_ids). Empty when no stage_summary — any agent-claimed
    evidence id then fails grounding (typed error, not a silent pass)."""
    ids: set[str] = set()
    if result.stage_summary is not None:
        ids.update(result.stage_summary.donor_evidence_ids or [])
    return frozenset(ids)


def build_grounded_run(result: PredictionResult) -> GroundedRun:
    """Construct the frozen grounding view from a typed ``PredictionResult``."""
    cands = tuple(result.candidates)
    return GroundedRun(
        run_id=result.run_id,
        candidate_ids=frozenset(c.candidate_id for c in cands),
        evidence_ids=_collect_evidence_ids(result),
        lineage_ids=frozenset(l for c in cands for l in c.support_lineage_ids),
        transformation_ids=frozenset(t for c in cands for t in c.transformation_ids),
        site_ids=frozenset(s for c in cands for s in c.site_ids),
        source_ledger_ids=frozenset(sl for c in cands for sl in c.source_ledger_ids),
        candidate_analogy_ledger_ids=frozenset(
            c.candidate_analogy_ledger_id
            for c in cands
            if c.candidate_analogy_ledger_id
        ),
        canonical_products=frozenset(c.canonical_product for c in cands),
        candidates=cands,
    )


_ID_TABLE: Mapping[str, str] = {
    "candidate": "candidate_ids",
    "evidence": "evidence_ids",
    "lineage": "lineage_ids",
    "transformation": "transformation_ids",
    "site": "site_ids",
    "source_ledger": "source_ledger_ids",
    "candidate_analogy_ledger": "candidate_analogy_ledger_ids",
}


def assert_id_belongs_to_run(grounded: GroundedRun, *, kind: str, id_: str) -> None:
    """Typed error if the given id does not belong to the run."""
    attr = _ID_TABLE.get(kind)
    if attr is None:
        raise GroundingError(f"unknown id kind {kind!r}")
    allowed: frozenset[str] = getattr(grounded, attr)
    if id_ not in allowed:
        raise GroundingError(
            f"{kind} id {id_!r} does not belong to run {grounded.run_id!r}"
        )


def assert_structure_from_result(grounded: GroundedRun, smiles: str) -> None:
    """Typed error if the SMILES is not a typed candidate's canonical_product
    (invention check — no fabrication)."""
    if smiles not in grounded.canonical_products:
        raise GroundingError(
            f"structure {smiles!r} not in run {grounded.run_id!r} "
            f"(invention — not a typed candidate canonical_product)"
        )


def validate_hypothesis(grounded: GroundedRun, hyp: ProductionSelectionHypothesis) -> None:
    """Validate every ID in the hypothesis belongs to the run, and reject
    unsupported claims.

    Raises ``GroundingError`` on:
    - unknown evidence / lineage / transformation / site id (not in run);
    - an unsupported claim: ``transformation_id`` + ``site_id`` that resolve
      but never co-occur in a single typed candidate (the agent cannot
      synthesize a new candidate from loose ids).
    """
    for rid in hyp.support_reaction_ids:
        assert_id_belongs_to_run(grounded, kind="evidence", id_=rid)
    for lid in hyp.support_lineage_ids:
        assert_id_belongs_to_run(grounded, kind="lineage", id_=lid)
    assert_id_belongs_to_run(grounded, kind="transformation", id_=hyp.transformation_id)
    assert_id_belongs_to_run(grounded, kind="site", id_=hyp.site_id)
    # Unsupported-claim check: transform+site must co-occur in >=1 typed
    # candidate. Loose ids that never co-occur = synthesized candidate = reject.
    supporting = [
        c for c in grounded.candidates
        if hyp.transformation_id in c.transformation_ids
        and hyp.site_id in c.site_ids
    ]
    if not supporting:
        raise GroundingError(
            f"hypothesis {hyp.hypothesis_id!r}: transform "
            f"{hyp.transformation_id!r} + site {hyp.site_id!r} do not co-occur "
            f"in any typed candidate of run {grounded.run_id!r} "
            f"(unsupported claim — cannot synthesize a candidate from loose ids)"
        )


def frozen_candidate_view(grounded: GroundedRun, cand_id: str) -> Candidate:
    """Return a read-only view of a typed candidate; raises ``GroundingError``
    if the candidate id is unknown.

    The returned ``Candidate`` is a defensive ``model_copy()`` so an agent
    cannot mutate the typed result through the view. The rank / lane / support
    tier / applicability / ledger id are the typed values — agents read,
    never write. There is no setter.
    """
    for c in grounded.candidates:
        if c.candidate_id == cand_id:
            return c.model_copy()
    raise GroundingError(
        f"candidate {cand_id!r} not in run {grounded.run_id!r}"
    )
