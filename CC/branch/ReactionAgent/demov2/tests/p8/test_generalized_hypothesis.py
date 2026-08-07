"""T2 RED tests — Generalized hypothesis (final_plan §11.3, final_design §12.3).

Must FAIL (RED) until ``reaction_agent/p8/schemas.py`` exists.

Six recorded fields:
  relaxation_policy_id / allowed_relaxation_ids[] / failed_strict_conditions[] /
  generalization_distance / source_transforms[] / validation

Anti-masquerade (leader D5): failed_strict_conditions must be non-empty and
must not reference a forbidden hard constraint; lane must be Lane.generalized
and no output may fall into a strict structure.
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


def make_policy() -> RelaxationPolicy:
    return RelaxationPolicy.create(
        policy_id="p8-generalized-relaxation",
        version="1.0.0",
        description="P8 generalized lane relaxation policy",
        allowed_relaxations=make_rules(),
        ood=OODPolicy(
            declaration=(
                "generalized hypotheses that cite a relaxation outside the "
                "registered vocabulary are out-of-distribution and rejected"
            ),
        ),
    )


def make_context() -> GeneralizedPolicyContext:
    return GeneralizedPolicyContext(
        policies={"p8-generalized-relaxation": make_policy()},
        transform_lineage={
            "transform-a": ["lin1", "lin2"],
            "transform-b": ["lin3"],
        },
    )


def make_hypothesis(**overrides) -> GeneralizedHypothesis:
    kwargs = dict(
        hypothesis_id="g1",
        lane="generalized",
        relaxation_policy_id="p8-generalized-relaxation",
        allowed_relaxation_ids=["relax_donor_site_precision"],
        failed_strict_conditions=[StrictCondition.donor_site_definite],
        generalization_distance=0.3,
        source_transforms=[
            SourceTransformRef(transform_id="transform-a", source_lineage_ids=["lin1"])
        ],
        validation=GeneralizedValidation(lane="generalized", status="validated"),
    )
    kwargs.update(overrides)
    return GeneralizedHypothesis(**kwargs)


class TestSixFieldsAndLane:
    def test_six_fields_present(self):
        h = make_hypothesis()
        assert h.relaxation_policy_id == "p8-generalized-relaxation"
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
            make_hypothesis(validation=GeneralizedValidation(lane="strict", status="validated"))


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


class TestValidationChain:
    def test_valid_hypothesis_passes(self):
        validate_generalized_hypothesis(make_hypothesis(), make_context())

    def test_relaxation_not_in_policy_registry_rejected(self):
        # D6: relaxation must come from the registered vocabulary
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

    def test_coverage_mismatch_rejected(self):
        # applied relaxation must cover exactly the failed conditions
        h = make_hypothesis(
            allowed_relaxation_ids=["relax_ambiguity_margin"],
            failed_strict_conditions=[StrictCondition.donor_site_definite],
            generalization_distance=0.2,
        )
        with pytest.raises(UnknownReferenceError):
            validate_generalized_hypothesis(h, make_context())

    def test_distance_mismatch_rejected(self):
        # distance must be recomputed per policy and match
        h = make_hypothesis(generalization_distance=0.99)
        with pytest.raises(UnknownReferenceError):
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
        assert h.validation.status == "validated"
        assert abs(h.generalization_distance - 0.8) < 1e-9