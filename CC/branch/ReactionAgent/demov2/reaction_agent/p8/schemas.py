"""P8-T2: Generalized hypothesis — relaxed-structure hypothesis (final_plan §11.3,
final_design §12.3).

Six recorded fields:
  relaxation_policy_id / policy_version / allowed_relaxation_ids[] /
  failed_strict_conditions[] / generalization_distance / source_transforms[] /
  validation

Anti-masquerade (leader D5): a generalized hypothesis MUST carry at least one
failed strict condition. A hypothesis that failed no strict condition is
strict and must never enter the generalized lane — this is enforced both at
schema construction and again at validation time.

Version pin (R1-01): the hypothesis records ``policy_version`` (semver) and the
validation chain requires the registered policy's version to match — a
hypothesis built against v1.0.0 is never re-validated against v2.0.0.

Error typing (R1-05): reference violations raise ``UnknownReferenceError``;
non-reference validation violations raise ``GeneralizedValidationError``.

Hard boundary (strict untouched): P8 does not modify the strict channel. This
module provides its own validation entry point; GeneralizedHypothesis is NOT
merged into the existing ``hypothesis_origin`` union (leader D3).
"""
from __future__ import annotations

from typing import Literal

from pydantic import Field, field_validator, model_validator

from reaction_agent.schemas.common import NonEmptyStr, StrictModel
from reaction_agent.schemas.errors import ContractViolation, UnknownReferenceError
from reaction_agent.p8.policy import (
    FORBIDDEN_HARD_CONSTRAINTS,
    RelaxationPolicy,
    StrictCondition,
    validate_semver,
)


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class GeneralizedValidationError(ContractViolation):
    """Raised when a generalized hypothesis fails a non-reference validation rule.

    Reference violations (unknown IDs / missing relations) keep using
    ``UnknownReferenceError``; this type is reserved for validation failures
    such as masquerade, coverage mismatch, distance mismatch, OOD, or a
    version-pin / content_hash trace mismatch (R1-05).
    """


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

    ``lane`` is pinned to "generalized" (R1-02) so no generalized output can
    claim a strict validation (leader D5 / no strict masquerade). ``status`` is
    a controlled vocabulary word. ``policy_content_hash`` records the exact
    policy artifact the hypothesis was validated against (R1-04), so a consumer
    never trusts an embedded status without the matching policy fingerprint.
    """

    lane: Literal["generalized"] = "generalized"
    status: Literal["validated"] = "validated"
    checks: list[NonEmptyStr] = []
    policy_content_hash: NonEmptyStr


# ---------------------------------------------------------------------------
# Generalized hypothesis
# ---------------------------------------------------------------------------


class GeneralizedHypothesis(StrictModel):
    """Generalized (exploratory) lane hypothesis.

    ``lane`` is Literal-typed to "generalized". ``policy_version`` pins the
    exact policy version the hypothesis was constructed against (R1-01); the
    validation chain rejects any version mismatch.
    """

    hypothesis_id: NonEmptyStr
    lane: Literal["generalized"] = "generalized"
    relaxation_policy_id: NonEmptyStr
    policy_version: NonEmptyStr
    allowed_relaxation_ids: list[NonEmptyStr]
    failed_strict_conditions: list[StrictCondition]
    generalization_distance: float = Field(ge=0.0)
    source_transforms: list[SourceTransformRef]
    validation: GeneralizedValidation

    @field_validator("policy_version")
    @classmethod
    def _semver_policy_version(cls, v: str) -> str:
        return validate_semver(v)

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
    """Run the full generalized validation chain (leader D5/D6, R1-01/R1-04/R1-05).

    Raises:
    - ``UnknownReferenceError`` for reference violations (unknown policy,
      unknown relaxation, unknown source transform / lineage).
    - ``GeneralizedValidationError`` for non-reference violations (version pin
      mismatch, masquerade, coverage mismatch, distance mismatch, OOD,
      validation content-hash trace mismatch).
    """
    policy = context.policies.get(hypothesis.relaxation_policy_id)
    if policy is None:
        raise UnknownReferenceError(
            f"unknown relaxation_policy_id: {hypothesis.relaxation_policy_id}"
        )

    # R1-01: version pin — the registered policy version must match the pin
    if policy.version != hypothesis.policy_version:
        raise GeneralizedValidationError(
            f"policy version pin mismatch: hypothesis pins {hypothesis.policy_version}, "
            f"registered policy {policy.policy_id} is {policy.version}"
        )

    ref_errors: list[str] = []
    val_errors: list[str] = []

    # D6: registered vocabulary only — every cited relaxation must be known
    known = policy.rule_ids()
    for rid in hypothesis.allowed_relaxation_ids:
        if rid not in known:
            ref_errors.append(
                f"relaxation {rid} not in policy {policy.policy_id} registered vocabulary"
            )

    # D5: failed_strict_conditions non-empty and not referencing forbidden
    if not hypothesis.failed_strict_conditions:
        val_errors.append("failed_strict_conditions must be non-empty (no strict masquerade)")
    for c in hypothesis.failed_strict_conditions:
        if c in FORBIDDEN_HARD_CONSTRAINTS:
            val_errors.append(
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
        val_errors.append(
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
        val_errors.append(
            f"generalization_distance mismatch: expected {recomputed}, "
            f"got {hypothesis.generalization_distance}"
        )

    # OOD: citation outside the registered vocabulary
    if policy.is_ood(hypothesis.allowed_relaxation_ids):
        val_errors.append(
            "hypothesis cites relaxation(s) outside the policy registered vocabulary (OOD)"
        )

    # R1-04: the validation record must name the exact policy artifact verified
    if hypothesis.validation.policy_content_hash != policy.content_hash:
        val_errors.append(
            f"validation.policy_content_hash {hypothesis.validation.policy_content_hash} "
            f"does not match policy {policy.policy_id} content_hash {policy.content_hash}"
        )

    # source transform references exist + lineage traceable
    for sr in hypothesis.source_transforms:
        if sr.transform_id not in context.transform_lineage:
            ref_errors.append(f"unknown source transform_id: {sr.transform_id}")
            continue
        registered = set(context.transform_lineage[sr.transform_id])
        cited = set(sr.source_lineage_ids)
        if not (cited & registered):
            ref_errors.append(
                f"source transform {sr.transform_id} cites no registered source lineage "
                f"in {sorted(registered)}"
            )
        for lid in sr.source_lineage_ids:
            if lid not in registered:
                ref_errors.append(
                    f"source lineage {lid} not registered for transform {sr.transform_id}"
                )

    if ref_errors:
        raise UnknownReferenceError("; ".join(ref_errors))
    if val_errors:
        raise GeneralizedValidationError("; ".join(val_errors))


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------


VALIDATED_CHECKS = [
    "registered_vocabulary",
    "anti_masquerade",
    "coverage_consistency",
    "distance_consistent",
    "ood_boundary",
    "source_lineage_traceable",
    "policy_version_pin",
    "validation_content_hash",
]


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

    Raises UnknownReferenceError / GeneralizedValidationError (via
    validate_generalized_hypothesis) or pydantic ValidationError on any
    violation — fail-closed.

    R1-04: the post-chain ``checks`` list and the policy ``content_hash`` are
    burned into the validation record immutably ONLY after the chain passes.
    """
    distance = policy.distance(allowed_relaxation_ids)
    base_validation = GeneralizedValidation(
        lane="generalized",
        status="validated",
        checks=[],
        policy_content_hash=policy.content_hash,
    )
    hypothesis = GeneralizedHypothesis(
        hypothesis_id=hypothesis_id,
        lane="generalized",
        relaxation_policy_id=policy.policy_id,
        policy_version=policy.version,
        allowed_relaxation_ids=allowed_relaxation_ids,
        failed_strict_conditions=failed_strict_conditions,
        generalization_distance=distance,
        source_transforms=source_transforms,
        validation=base_validation,
    )
    validate_generalized_hypothesis(hypothesis, context)
    # chain passed — record the checks immutably
    return hypothesis.model_copy(
        update={"validation": base_validation.model_copy(update={"checks": VALIDATED_CHECKS})}
    )


__all__ = [
    "GeneralizedValidationError",
    "SourceTransformRef",
    "GeneralizedValidation",
    "GeneralizedHypothesis",
    "GeneralizedPolicyContext",
    "validate_generalized_hypothesis",
    "build_generalized_hypothesis",
    "VALIDATED_CHECKS",
]