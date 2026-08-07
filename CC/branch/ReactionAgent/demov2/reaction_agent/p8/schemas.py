"""P8-T2: Generalized hypothesis — relaxed-structure hypothesis (final_plan §11.3,
final_design §12.3).

Six recorded fields:
  relaxation_policy_id / allowed_relaxation_ids[] / failed_strict_conditions[] /
  generalization_distance / source_transforms[] / validation

Anti-masquerade (leader D5): a generalized hypothesis MUST carry at least one
failed strict condition. A hypothesis that failed no strict condition is
strict and must never enter the generalized lane — this is enforced both at
schema construction and again at validation time.

Hard boundary (strict untouched): P8 does not modify the strict channel. This
module provides its own validation entry point; GeneralizedHypothesis is NOT
merged into the existing ``hypothesis_origin`` union (leader D3).
"""
from __future__ import annotations

from pydantic import Field, model_validator

from reaction_agent.schemas.common import NonEmptyStr, StrictModel
from reaction_agent.schemas.errors import UnknownReferenceError
from reaction_agent.p8.policy import (
    FORBIDDEN_HARD_CONSTRAINTS,
    RelaxationPolicy,
    StrictCondition,
)


# ---------------------------------------------------------------------------
# Source transform reference (traceable lineage)
# ---------------------------------------------------------------------------


class SourceTransformRef(StrictModel):
    """A source transform and the source lineages it derives from.

    Enables traceable lineage: the transform exists and its cited source
    lineages are registered for it.
    """

    transform_id: NonEmptyStr
    source_lineage_ids: list[NonEmptyStr]


# ---------------------------------------------------------------------------
# Validation record
# ---------------------------------------------------------------------------


class GeneralizedValidation(StrictModel):
    """Lane-tagged validation record for a generalized hypothesis.

    ``lane`` is pinned to "generalized" so no generalized output can claim a
    strict validation (leader D5 / no strict masquerade).
    """

    lane: str = "generalized"
    status: str = "validated"
    checks: list[NonEmptyStr] = []

    @model_validator(mode="after")
    def _lane_is_generalized(self) -> "GeneralizedValidation":
        if self.lane != "generalized":
            raise ValueError("GeneralizedValidation.lane must be 'generalized'")
        return self


# ---------------------------------------------------------------------------
# Generalized hypothesis
# ---------------------------------------------------------------------------


class GeneralizedHypothesis(StrictModel):
    """Generalized (exploratory) lane hypothesis.

    lane is pinned to "generalized" (constants.Lane.generalized). Any attempt
    to construct it in the strict lane is rejected at the schema level.
    """

    hypothesis_id: NonEmptyStr
    lane: str = "generalized"
    relaxation_policy_id: NonEmptyStr
    allowed_relaxation_ids: list[NonEmptyStr]
    failed_strict_conditions: list[StrictCondition]
    generalization_distance: float = Field(ge=0.0)
    source_transforms: list[SourceTransformRef]
    validation: GeneralizedValidation

    @model_validator(mode="after")
    def _anti_masquerade(self) -> "GeneralizedHypothesis":
        # D5: a hypothesis with no failed strict condition is strict — masquerade
        if not self.failed_strict_conditions:
            raise ValueError(
                "failed_strict_conditions must be non-empty "
                "(a hypothesis that failed no strict condition is strict, not generalized)"
            )
        # A forbidden hard constraint can never be generalized into this lane.
        for c in self.failed_strict_conditions:
            if c in FORBIDDEN_HARD_CONSTRAINTS:
                raise ValueError(
                    f"{c.value} is a forbidden hard constraint and cannot be generalized"
                )
        if self.lane != "generalized":
            raise ValueError("GeneralizedHypothesis.lane must be 'generalized'")
        if self.validation.lane != "generalized":
            raise ValueError("validation.lane must be 'generalized' (no strict masquerade)")
        return self


# ---------------------------------------------------------------------------
# Validation context
# ---------------------------------------------------------------------------


class GeneralizedPolicyContext(StrictModel):
    """Registered policies + source-transform lineage for generalized validation."""

    policies: dict[str, RelaxationPolicy]
    transform_lineage: dict[str, list[str]]


# ---------------------------------------------------------------------------
# Validation chain
# ---------------------------------------------------------------------------


def validate_generalized_hypothesis(
    hypothesis: GeneralizedHypothesis,
    context: GeneralizedPolicyContext,
) -> None:
    """Run the full generalized validation chain (leader D5/D6).

    Raises UnknownReferenceError on any violation:
    - unknown relaxation_policy_id
    - allowed_relaxation_ids not all in the policy's registered vocabulary (D6)
    - failed_strict_conditions empty (masquerade) or referencing a forbidden
      hard constraint
    - relaxation coverage mismatch (applied relaxations must cover exactly the
      failed conditions)
    - generalization_distance not recomputed consistently per policy
    - OOD: a cited relaxation outside the registered vocabulary
    - source transform references missing / untraceable lineage
    """
    policy = context.policies.get(hypothesis.relaxation_policy_id)
    if policy is None:
        raise UnknownReferenceError(
            f"unknown relaxation_policy_id: {hypothesis.relaxation_policy_id}"
        )

    errors: list[str] = []

    # D6: registered vocabulary only — every cited relaxation must be known
    known = policy.rule_ids()
    for rid in hypothesis.allowed_relaxation_ids:
        if rid not in known:
            errors.append(
                f"relaxation {rid} not in policy {policy.policy_id} registered vocabulary"
            )

    # D5: failed_strict_conditions non-empty and not referencing forbidden
    if not hypothesis.failed_strict_conditions:
        errors.append("failed_strict_conditions must be non-empty (no strict masquerade)")
    for c in hypothesis.failed_strict_conditions:
        if c in FORBIDDEN_HARD_CONSTRAINTS:
            errors.append(
                f"failed strict condition {c.value} is a forbidden hard constraint; cannot be generalized"
            )

    # coverage integrity: applied relaxations cover exactly the failed conditions
    relaxed_union: set[StrictCondition] = set()
    for rid in hypothesis.allowed_relaxation_ids:
        rule = next((r for r in policy.allowed_relaxations if r.rule_id == rid), None)
        if rule is not None:
            relaxed_union.update(rule.applies_to)
    failed_set = set(hypothesis.failed_strict_conditions)
    if relaxed_union != failed_set:
        errors.append(
            "relaxation coverage mismatch: applied relaxations cover "
            f"{sorted(c.value for c in relaxed_union)}, failed conditions are "
            f"{sorted(c.value for c in failed_set)}"
        )

    # distance consistency: recompute from the policy and compare
    recomputed = 0.0
    all_known = True
    for rid in hypothesis.allowed_relaxation_ids:
        rule = next((r for r in policy.allowed_relaxations if r.rule_id == rid), None)
        if rule is None:
            all_known = False
        else:
            recomputed += rule.distance_weight
    if all_known and abs(recomputed - hypothesis.generalization_distance) > 1e-9:
        errors.append(
            f"generalization_distance mismatch: expected {recomputed}, "
            f"got {hypothesis.generalization_distance}"
        )

    # OOD: citation outside the registered vocabulary
    if policy.is_ood(hypothesis.allowed_relaxation_ids):
        errors.append(
            "hypothesis cites relaxation(s) outside the policy registered vocabulary (OOD)"
        )

    # source transform references exist + lineage traceable
    for sr in hypothesis.source_transforms:
        if sr.transform_id not in context.transform_lineage:
            errors.append(f"unknown source transform_id: {sr.transform_id}")
            continue
        registered = set(context.transform_lineage[sr.transform_id])
        cited = set(sr.source_lineage_ids)
        if not (cited & registered):
            errors.append(
                f"source transform {sr.transform_id} cites no registered source lineage "
                f"in {sorted(registered)}"
            )
        for lid in sr.source_lineage_ids:
            if lid not in registered:
                errors.append(
                    f"source lineage {lid} not registered for transform {sr.transform_id}"
                )

    if errors:
        raise UnknownReferenceError("; ".join(errors))


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------


def build_generalized_hypothesis(
    *,
    hypothesis_id: str,
    policy: RelaxationPolicy,
    allowed_relaxation_ids: list[str],
    failed_strict_conditions: list[StrictCondition],
    source_transforms: list[SourceTransformRef],
    context: GeneralizedPolicyContext,
) -> GeneralizedHypothesis:
    """Run the full chain and produce a validated GeneralizedHypothesis.

    Raises UnknownReferenceError (via validate_generalized_hypothesis) or
    pydantic ValidationError on any violation — fail-closed.
    """
    distance = policy.distance(allowed_relaxation_ids)
    hypothesis = GeneralizedHypothesis(
        hypothesis_id=hypothesis_id,
        lane="generalized",
        relaxation_policy_id=policy.policy_id,
        allowed_relaxation_ids=allowed_relaxation_ids,
        failed_strict_conditions=failed_strict_conditions,
        generalization_distance=distance,
        source_transforms=source_transforms,
        validation=GeneralizedValidation(lane="generalized", status="validated"),
    )
    validate_generalized_hypothesis(hypothesis, context)
    return hypothesis


__all__ = [
    "SourceTransformRef",
    "GeneralizedValidation",
    "GeneralizedHypothesis",
    "GeneralizedPolicyContext",
    "validate_generalized_hypothesis",
    "build_generalized_hypothesis",
]