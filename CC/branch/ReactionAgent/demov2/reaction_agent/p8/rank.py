"""P8-T3: Independent generalized-lane rank/abstain (final_plan §11.4,
final_design §18.1 / §19.2).

The generalized lane is a physically isolated, exploratory, NON-production
lane. This module ranks generalized hypotheses **within the lane only** and
produces a typed rank / abstain result that can never masquerade as a strict
``Candidate`` / ``PredictionResult`` / ``Abstention``.

Stage B acceptance pins (leader Stage B 派单):

- **lane-only ranking**: the ranker accepts only ``GeneralizedHypothesis``
  inputs and computes a lane-internal ``generalized_score`` from
  ``generalization_distance`` alone. It never reads a strict candidate's
  ``ranking_score`` and never compares across lanes (no cross-lane raw score).
  An upfront lane guard rejects any input whose lane is not "generalized"
  (a strict ``Candidate`` with ``lane=strict`` is rejected here).

- **consumption gate**: the ranker MUST re-run
  ``validate_generalized_hypothesis`` on every hypothesis and MUST NOT trust
  the embedded ``validation.status`` / ``checks`` record (Stage A R1-04 /
  Round-2 OA-2 explicit Stage B pin). A hypothesis whose embedded record
  claims "validated" but fails the re-run is recorded as rejected with the
  re-run exception type — never silently dropped, never trusted.

- **exploratory output semantics**: every output type carries
  ``exploratory: Literal[True]`` and the result carries
  ``output_semantics: Literal["exploratory_non_production"]`` (Gate P8
  "user semantics clear").

- **no strict masquerade runtime pin**: ``GeneralizedRankEntry`` /
  ``GeneralizedRankResult`` / ``GeneralizedRankAbstention`` are fresh
  StrictModels, lane-pinned via ``Literal["generalized"]``, with none of the
  strict ``Candidate`` / ``PredictionResult`` fields (no ``canonical_product``,
  no ``ranking_score``, no ``run_id``/``decision``). They are structurally
  incompatible with the strict channel types.

- **abstain path**: empty input -> ``no_hypotheses``; all hypotheses rejected
  by the re-run gate -> ``no_validated_hypotheses``; all valid but beyond the
  optional ``max_generalization_distance`` cap -> ``all_beyond_max_distance``.

Hard boundary (strict untouched): this module only ADDS new p8 code; it never
imports or modifies the strict channel (P3-P6), the shared hypothesis union,
or P7. It imports the locked Stage A schema (``reaction_agent.p8.schemas``)
and re-runs its public validation entry point.
"""
from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import Field, model_validator

from reaction_agent.schemas.common import NonEmptyStr, StrictModel
from reaction_agent.p8.policy import RelaxationPolicy  # noqa: F401  (re-exported)
from reaction_agent.p8.schemas import (
    GeneralizedHypothesis,
    GeneralizedPolicyContext,
    GeneralizedValidationError,
    validate_generalized_hypothesis,
)
from reaction_agent.schemas.errors import UnknownReferenceError


# ---------------------------------------------------------------------------
# Controlled vocabularies
# ---------------------------------------------------------------------------


class GeneralizedRankReasonCode(str, Enum):
    """Why the generalized lane abstained (controlled vocabulary, not free text)."""

    no_hypotheses = "no_hypotheses"
    no_validated_hypotheses = "no_validated_hypotheses"
    all_beyond_max_distance = "all_beyond_max_distance"


class GeneralizedRankRejectReasonCode(str, Enum):
    """Why a single hypothesis was rejected from ranking (re-run outcome)."""

    validation_failed = "validation_failed"  # re-run chain raised
    beyond_max_distance = "beyond_max_distance"  # beyond the configured cap


# ---------------------------------------------------------------------------
# Output types — fresh, lane-pinned, NOT strict channel types
# ---------------------------------------------------------------------------


class GeneralizedRankEntry(StrictModel):
    """A ranked generalized hypothesis. NOT a strict ``Candidate``.

    Carries a lane-internal ``generalized_score`` (derived from
    ``generalization_distance`` only) — never a strict ``ranking_score``.
    Lane is Literal-pinned to "generalized"; ``exploratory`` is pinned True.
    """

    rank_position: int = Field(ge=1)  # 1-based position within the generalized lane
    hypothesis_id: NonEmptyStr
    lane: Literal["generalized"] = "generalized"
    relaxation_policy_id: NonEmptyStr
    policy_version: NonEmptyStr
    generalization_distance: float = Field(ge=0.0)
    generalized_score: float  # lane-internal only; NOT comparable to strict ranking_score
    exploratory: Literal[True] = True


class GeneralizedRankAbstention(StrictModel):
    """Generalized-lane abstention. NOT the strict ``Abstention``.

    Lane is Literal-pinned to "generalized"; reason_code is a controlled
    vocabulary word (no free text — Gate P8 "user semantics clear").
    """

    lane: Literal["generalized"] = "generalized"
    reason_code: GeneralizedRankReasonCode
    detail: str = ""


class GeneralizedRankRejectRecord(StrictModel):
    """A hypothesis rejected from ranking.

    Records the RE-RUN outcome (never the embedded ``validation.status``):
    the ranker re-ran ``validate_generalized_hypothesis`` and recorded which
    controlled-vocabulary reason and exception type it raised.
    """

    hypothesis_id: NonEmptyStr
    lane: Literal["generalized"] = "generalized"
    reason_code: GeneralizedRankRejectReasonCode
    detail: str = ""


class GeneralizedRankResult(StrictModel):
    """Exploratory, NON-production rank result for the generalized lane.

    NOT a strict ``PredictionResult``: no ``run_id`` / ``status`` / ``decision``
    / ``snapshot_id``. Lane is Literal-pinned to "generalized" and the output
    semantics are pinned ``exploratory_non_production``.
    """

    lane: Literal["generalized"] = "generalized"
    output_semantics: Literal["exploratory_non_production"] = "exploratory_non_production"
    exploratory: Literal[True] = True
    ranked: list[GeneralizedRankEntry] = []
    abstention: GeneralizedRankAbstention | None = None
    rejected: list[GeneralizedRankRejectRecord] = []

    @model_validator(mode="after")
    def _enforce_state_machine(self) -> "GeneralizedRankResult":
        # ranked set present -> must NOT abstain (a ranked lane is a result)
        if self.ranked and self.abstention is not None:
            raise ValueError(
                "generalized rank result with a non-empty ranked set must not "
                "carry an abstention"
            )
        # ranked set empty -> must abstain (no silent empty result)
        if not self.ranked and self.abstention is None:
            raise ValueError(
                "generalized rank result with an empty ranked set must carry "
                "an abstention (no silent empty ranking)"
            )
        return self


# ---------------------------------------------------------------------------
# Lane-internal score (no cross-lane raw score)
# ---------------------------------------------------------------------------


def generalized_score(generalization_distance: float) -> float:
    """Lane-internal exploratory priority, monotonic decreasing in distance.

    This is NOT a strict raw score and is NOT comparable to a strict
    ``Candidate.ranking_score`` (a weighted feature average over the strict
    ranking features). It is derived solely from ``generalization_distance``
    (the registered relaxation weights) so the generalized lane never compares
    its scores against strict scores.

    Returns 1.0 at distance 0 and tends to 0 as distance grows; always in
    (0.0, 1.0] for any non-negative distance.
    """
    return 1.0 / (1.0 + generalization_distance)


# ---------------------------------------------------------------------------
# Reject helpers
# ---------------------------------------------------------------------------


def _reject(
    h: GeneralizedHypothesis,
    reason_code: GeneralizedRankRejectReasonCode,
    detail: str,
) -> GeneralizedRankRejectRecord:
    return GeneralizedRankRejectRecord(
        hypothesis_id=h.hypothesis_id,
        lane="generalized",
        reason_code=reason_code,
        detail=detail,
    )


def _validate_or_reject(
    h: GeneralizedHypothesis,
    context: GeneralizedPolicyContext,
) -> tuple[bool, GeneralizedRankRejectRecord | None]:
    """Consumption gate: RE-RUN the validation chain (never trust embedded).

    Returns (ok, reject_record). A hypothesis whose embedded
    ``validation.status="validated"`` LIES is caught here by the re-run.
    """
    try:
        validate_generalized_hypothesis(h, context)
    except (UnknownReferenceError, GeneralizedValidationError) as exc:
        # the re-run raised — record the re-run exception type as evidence
        return False, _reject(
            h,
            GeneralizedRankRejectReasonCode.validation_failed,
            f"{type(exc).__name__}: {exc}",
        )
    return True, None


# ---------------------------------------------------------------------------
# Public ranker
# ---------------------------------------------------------------------------


def rank_generalized(
    hypotheses: list[GeneralizedHypothesis],
    context: GeneralizedPolicyContext,
    *,
    max_generalization_distance: float | None = None,
) -> GeneralizedRankResult:
    """Independent lane-only rank/abstain for the generalized lane.

    Consumption gate (R1-04 / OA-2): re-runs ``validate_generalized_hypothesis``
    on every hypothesis; never trusts the embedded ``validation`` record.

    Lane-only: ranks ONLY generalized hypotheses; computes a lane-internal
    ``generalized_score`` from ``generalization_distance``; never compares to a
    strict candidate's raw score (no cross-lane raw score).

    No strict masquerade: the output is lane-pinned ``Literal["generalized"]``
    and structurally distinct from ``Candidate`` / ``PredictionResult``.

    Abstain path: empty input -> ``no_hypotheses``; all rejected by the gate ->
    ``no_validated_hypotheses``; all valid but beyond ``max_generalization_distance``
    -> ``all_beyond_max_distance``.
    """
    # empty input -> clean abstention (no silent empty result)
    if not hypotheses:
        return GeneralizedRankResult(
            abstention=GeneralizedRankAbstention(
                reason_code=GeneralizedRankReasonCode.no_hypotheses,
                detail="no generalized hypotheses supplied to the ranker",
            )
        )

    # no-cross-lane / no-strict-masquerade INPUT guard: every input must be a
    # generalized-lane hypothesis. A strict Candidate (lane=strict) is rejected.
    for h in hypotheses:
        if getattr(h, "lane", None) != "generalized":
            raise GeneralizedValidationError(
                "rank_generalized only accepts generalized-lane hypotheses; "
                f"input {getattr(h, 'hypothesis_id', getattr(h, 'candidate_id', '?'))} "
                f"has lane={getattr(h, 'lane', None)!r} (strict inputs are rejected "
                "to prevent cross-lane raw-score mixing and strict masquerade)"
            )

    accepted: list[GeneralizedHypothesis] = []
    rejected: list[GeneralizedRankRejectRecord] = []
    for h in hypotheses:
        ok, reject = _validate_or_reject(h, context)
        if reject is not None:
            rejected.append(reject)
            continue
        if (
            max_generalization_distance is not None
            and h.generalization_distance > max_generalization_distance
        ):
            rejected.append(
                _reject(
                    h,
                    GeneralizedRankRejectReasonCode.beyond_max_distance,
                    f"generalization_distance {h.generalization_distance} exceeds "
                    f"max_generalization_distance {max_generalization_distance}",
                )
            )
            continue
        accepted.append(h)

    if not accepted:
        # distinguish "all too far" from "all failed re-validation"
        if rejected and all(
            r.reason_code == GeneralizedRankRejectReasonCode.beyond_max_distance
            for r in rejected
        ):
            code = GeneralizedRankReasonCode.all_beyond_max_distance
        else:
            code = GeneralizedRankReasonCode.no_validated_hypotheses
        return GeneralizedRankResult(
            abstention=GeneralizedRankAbstention(
                reason_code=code,
                detail=f"{len(rejected)} hypothesis(ies) rejected; none ranked",
            ),
            rejected=rejected,
        )

    # lane-only ordering: score desc, then distance asc, then id for determinism
    accepted.sort(
        key=lambda h: (
            -generalized_score(h.generalization_distance),
            h.generalization_distance,
            h.hypothesis_id,
        )
    )
    ranked = [
        GeneralizedRankEntry(
            rank_position=i + 1,
            hypothesis_id=h.hypothesis_id,
            lane="generalized",
            relaxation_policy_id=h.relaxation_policy_id,
            policy_version=h.policy_version,
            generalization_distance=h.generalization_distance,
            generalized_score=generalized_score(h.generalization_distance),
        )
        for i, h in enumerate(accepted)
    ]
    return GeneralizedRankResult(ranked=ranked, rejected=rejected)


__all__ = [
    "GeneralizedRankReasonCode",
    "GeneralizedRankRejectReasonCode",
    "GeneralizedRankEntry",
    "GeneralizedRankAbstention",
    "GeneralizedRankRejectRecord",
    "GeneralizedRankResult",
    "generalized_score",
    "rank_generalized",
]
