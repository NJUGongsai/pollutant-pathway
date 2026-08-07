"""T2 RED tests — Generalized hypothesis (final_plan §11.3, final_design §12.3).

Round 2 covers audit findings R1-01..R1-06:
- R1-01: policy_version pin field (semver) + version mismatch rejection
- R1-02: lane/status Literal-typed (no bare str)
- R1-04: validation record carries policy content_hash + checks; builder writes
  checks after the chain passes
- R1-05: error type split — GeneralizedValidationError (validation) vs
  UnknownReferenceError (reference)
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from reaction_agent.schemas.common import Lane
from reaction_agent.p8.policy import (
    StrictCondition,
    OODPolicy,
    RelaxationPolicy,
    RelaxationRule,
)
from reaction_agent.p8.schemas import (
    GeneralizedHypothesis,
    GeneralizedValidation,
    GeneralizedPolicyContext,
    GeneralizedValidationError,
    SourceTransformRef,
    build_generalized_hypothesis,
    validate_generalized_hypothesis,
)
from reaction_agent.schemas.errors import UnknownReferenceError


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
        transform_lineage={
            "transform-a": ["lin1", "lin2"],
            "transform-b": ["lin3"],
        },
    )


def make_hypothesis(**overrides) -> GeneralizedHypothesis:
    policy = make_policy()
    kwargs = dict(
        hypothesis_id="g1",
        lane="generalized",
        relaxation_policy_id="p8-generalized-relaxation",
        policy_version="1.0.0",
        allowed_relaxation_ids=["relax_donor_site_precision"],
        failed_strict_conditions=[StrictCondition.donor_site_definite],
        generalization_distance=0.3,
        source_transforms=[
            SourceTransformRef(transform_id="transform-a", source_lineage_ids=["lin1"])
        ],
        validation=GeneralizedValidation(
            lane="generalized",
            status="validated",
            policy_content_hash=policy.content_hash,
        ),
    )
    kwargs.update(overrides)
    return GeneralizedHypothesis(**kwargs)


class TestSixFieldsAndLane:
    def test_six_fields_present(self):
        h = make_hypothesis()
        assert h.relaxation_policy_id == "p8-generalized-relaxation"
        assert h.policy_version == "1.0.0"
        assert h.allowed_relaxation_ids == ["relax_donor_site_precision"]
        assert h.failed_strict_conditions == [StrictCondition.donor_site_definite]
        assert h.generalization_distance == 0.3
        assert h.source_transforms[0].transform_id == "transform-a"
        assert h.validation.lane == "generalized"

    def test_lane_is_generalized(self):
        h = make_hypothesis()
        assert h.lane == Lane.generalized

    def test_cannot_put_generalized_output_in_strict_lane(self):
        with pytest.raises(ValidationError):
            make_hypothesis(lane="strict")  # strict lane is a different structure

    def test_validation_lane_is_generalized(self):
        with pytest.raises(ValidationError):
            make_hypothesis(
                validation=GeneralizedValidation(
                    lane="strict", status="validated", policy_content_hash="x"
                )
            )


class TestPolicyVersionPin:
    """R1-01: hypothesis must pin policy_version (semver) and match the policy."""

    def test_policy_version_field_present(self):
        h = make_hypothesis()
        assert h.policy_version == "1.0.0"

    def test_policy_version_must_be_semver(self):
        with pytest.raises(ValidationError):
            make_hypothesis(policy_version="1.0")  # not X.Y.Z

    def test_version_mismatch_rejected(self):
        # context registers policy v2.0.0; hypothesis pins v1.0.0 -> reject
        ctx = make_context(policy=make_policy(version="2.0.0"))
        h = make_hypothesis(
            policy_version="1.0.0",
            validation=GeneralizedValidation(
                lane="generalized",
                status="validated",
                policy_content_hash=make_policy(version="2.0.0").content_hash,
            ),
        )
        with pytest.raises(GeneralizedValidationError):
            validate_generalized_hypothesis(h, ctx)


class TestTypedLaneStatus:
    """R1-02: lane/status are Literal-typed, not bare str."""

    def test_status_is_literal_validated(self):
        h = make_hypothesis()
        assert h.validation.status == "validated"

    def test_arbitrary_status_rejected(self):
        with pytest.raises(ValidationError):
            make_hypothesis(
                validation=GeneralizedValidation(
                    lane="generalized", status="made_up", policy_content_hash="x"
                )
            )

    def test_arbitrary_lane_rejected(self):
        with pytest.raises(ValidationError):
            make_hypothesis(lane="agent_proposed")


class TestAntiMasquerade:
    def test_empty_failed_strict_conditions_rejected(self):
        # D5: a hypothesis with no failed strict condition is strict — masquerade
        with pytest.raises(ValidationError):
            make_hypothesis(failed_strict_conditions=[], allowed_relaxation_ids=[])

    def test_forbidden_hard_constraint_cannot_be_failed(self):
        # a broken mapped lineage can never be generalized into the lane
        with pytest.raises(ValidationError):
            make_hypothesis(
                failed_strict_conditions=[StrictCondition.trusted_mapped_lineage],
                allowed_relaxation_ids=[],
            )


class TestValidationTracing:
    """R1-04: validation record carries the policy content_hash it was done against."""

    def test_validation_carries_policy_content_hash(self):
        policy = make_policy()
        h = make_hypothesis()
        assert h.validation.policy_content_hash == policy.content_hash

    def test_validation_content_hash_mismatch_rejected(self):
        # record claims a content_hash that is not the registered policy's
        h = make_hypothesis(
            validation=GeneralizedValidation(
                lane="generalized",
                status="validated",
                policy_content_hash="deadbeef",
            )
        )
        with pytest.raises(GeneralizedValidationError):
            validate_generalized_hypothesis(h, make_context())


class TestValidationChain:
    def test_valid_hypothesis_passes(self):
        validate_generalized_hypothesis(make_hypothesis(), make_context())

    def test_relaxation_not_in_policy_registry_rejected(self):
        # D6: relaxation must come from the registered vocabulary (reference)
        h = make_hypothesis(
            allowed_relaxation_ids=["free_text_relaxation"],
            failed_strict_conditions=[StrictCondition.donor_site_definite],
            generalization_distance=0.3,
        )
        with pytest.raises(UnknownReferenceError):
            validate_generalized_hypothesis(h, make_context())

    def test_unknown_policy_rejected(self):
        h = make_hypothesis(relaxation_policy_id="ghost_policy")
        with pytest.raises(UnknownReferenceError):
            validate_generalized_hypothesis(h, make_context())

    def test_coverage_mismatch_raises_validation_error(self):
        # R1-05: coverage mismatch is a validation error, not a reference error
        h = make_hypothesis(
            allowed_relaxation_ids=["relax_ambiguity_margin"],
            failed_strict_conditions=[StrictCondition.donor_site_definite],
            generalization_distance=0.2,
        )
        with pytest.raises(GeneralizedValidationError):
            validate_generalized_hypothesis(h, make_context())

    def test_distance_mismatch_raises_validation_error(self):
        # R1-05: distance mismatch is a validation error, not a reference error
        h = make_hypothesis(generalization_distance=0.99)
        with pytest.raises(GeneralizedValidationError):
            validate_generalized_hypothesis(h, make_context())

    def test_source_transform_unknown_rejected(self):
        h = make_hypothesis(
            source_transforms=[SourceTransformRef(transform_id="ghost", source_lineage_ids=["lin1"])]
        )
        with pytest.raises(UnknownReferenceError):
            validate_generalized_hypothesis(h, make_context())

    def test_source_lineage_not_registered_for_transform_rejected(self):
        h = make_hypothesis(
            source_transforms=[SourceTransformRef(transform_id="transform-a", source_lineage_ids=["lin9"])]
        )
        with pytest.raises(UnknownReferenceError):
            validate_generalized_hypothesis(h, make_context())


class TestBuilder:
    def test_build_generalized_hypothesis_produces_validated(self):
        ctx = make_context()
        h = build_generalized_hypothesis(
            hypothesis_id="g2",
            policy=make_policy(),
            allowed_relaxation_ids=["relax_donor_site_precision", "relax_precondition_completeness"],
            failed_strict_conditions=[
                StrictCondition.donor_site_definite,
                StrictCondition.preconditions_complete,
            ],
            source_transforms=[SourceTransformRef(transform_id="transform-a", source_lineage_ids=["lin1"])],
            context=ctx,
        )
        assert h.lane == Lane.generalized
        assert h.policy_version == "1.0.0"
        assert h.validation.status == "validated"
        assert h.validation.policy_content_hash == make_policy().content_hash
        # R1-04: builder writes the post-chain checks into the record
        assert sorted(h.validation.checks) == sorted(
            [
                "registered_vocabulary",
                "anti_masquerade",
                "coverage_consistency",
                "distance_consistent",
                "ood_boundary",
                "source_lineage_traceable",
                "policy_version_pin",
                "validation_content_hash",
            ]
        )
        assert abs(h.generalization_distance - 0.8) < 1e-9