"""T3 RED tests — Independent generalized-lane rank/abstain (final_plan §11.4,
final_design §18.1 / §19.2).

Stage B acceptance pins (leader Stage B 派单):
- lane-only ranking: only generalized hypotheses are ranked; the ranker never
  compares a generalized score against a strict candidate's raw score
  (no cross-lane raw score).
- consumption gate: the ranker MUST re-run ``validate_generalized_hypothesis``
  and MUST NOT trust the embedded ``validation.status`` / ``checks`` record
  (Stage A R1-04 / Round-2 OA-2 explicit Stage B pin).
- exploratory output semantics: every output is marked exploratory /
  non-production (Gate P8 "user semantics clear").
- no strict masquerade runtime pin: the rank output structures are NOT the
  strict ``Candidate`` / ``PredictionResult`` / ``Abstention``; lane is
  Literal-pinned to "generalized".
- abstain path: empty / all-rejected input produces a typed abstention with a
  controlled-vocabulary reason code.

Must FAIL (RED) until ``reaction_agent/p8/rank.py`` exists.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from reaction_agent.schemas.candidate import Candidate
from reaction_agent.schemas.common import Lane
from reaction_agent.schemas.result import Abstention as StrictAbstention
from reaction_agent.schemas.result import PredictionResult as StrictPredictionResult
from reaction_agent.p8.policy import (
    OODPolicy,
    RelaxationPolicy,
    RelaxationRule,
    StrictCondition,
)
from reaction_agent.p8.schemas import (
    GeneralizedHypothesis,
    GeneralizedPolicyContext,
    GeneralizedValidation,
    GeneralizedValidationError,
    SourceTransformRef,
    VALIDATED_CHECKS,
    build_generalized_hypothesis,
)
from reaction_agent.p8.rank import (  # noqa: F401  (RED: module absent)
    GeneralizedRankAbstention,
    GeneralizedRankEntry,
    GeneralizedRankReasonCode,
    GeneralizedRankResult,
    GeneralizedRankRejectReasonCode,
    generalized_score,
    rank_generalized,
)


# ---------------------------------------------------------------------------
# Factories (self-contained; mirror tests/p8/test_generalized_hypothesis.py)
# ---------------------------------------------------------------------------


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


def make_built(
    *,
    hypothesis_id: str = "g1",
    rule_id: str = "relax_donor_site_precision",
    failed: StrictCondition = StrictCondition.donor_site_definite,
) -> GeneralizedHypothesis:
    """A genuinely-validated hypothesis built through the Stage A builder."""
    policy = make_policy()
    return build_generalized_hypothesis(
        hypothesis_id=hypothesis_id,
        policy=policy,
        allowed_relaxation_ids=[rule_id],
        failed_strict_conditions=[failed],
        source_transforms=[
            SourceTransformRef(transform_id="transform-a", source_lineage_ids=["lin1"])
        ],
        context=make_context(policy),
    )


# ---------------------------------------------------------------------------
# Output type identity — no strict masquerade (runtime pin)
# ---------------------------------------------------------------------------


class TestOutputIdentityNoStrictMasquerade:
    def test_rank_entry_lane_is_literal_generalized(self):
        e = GeneralizedRankEntry(
            rank_position=1,
            hypothesis_id="g1",
            relaxation_policy_id="p8-generalized-relaxation",
            policy_version="1.0.0",
            generalization_distance=0.3,
            generalized_score=1.0 / 1.3,
        )
        assert e.lane == "generalized"
        assert e.lane == Lane.generalized

    def test_rank_entry_exploratory_is_pinned_true(self):
        e = GeneralizedRankEntry(
            rank_position=1,
            hypothesis_id="g1",
            relaxation_policy_id="p8-generalized-relaxation",
            policy_version="1.0.0",
            generalization_distance=0.3,
            generalized_score=1.0 / 1.3,
        )
        assert e.exploratory is True

    def test_rank_entry_is_not_a_strict_candidate(self):
        # no canonical_product / ranking_score / generation_paths — not a Candidate
        fields = set(GeneralizedRankEntry.model_fields)
        assert "canonical_product" not in fields
        assert "ranking_score" not in fields
        assert "generation_paths" not in fields
        e = GeneralizedRankEntry(
            rank_position=1,
            hypothesis_id="g1",
            relaxation_policy_id="p8-generalized-relaxation",
            policy_version="1.0.0",
            generalization_distance=0.3,
            generalized_score=1.0 / 1.3,
        )
        assert not isinstance(e, Candidate)

    def test_rank_entry_rejects_strict_candidate_fields(self):
        # extra="forbid": a strict Candidate's ranking_score cannot sneak in
        with pytest.raises(ValidationError):
            GeneralizedRankEntry(
                rank_position=1,
                hypothesis_id="g1",
                relaxation_policy_id="p8-generalized-relaxation",
                policy_version="1.0.0",
                generalization_distance=0.3,
                generalized_score=1.0 / 1.3,
                ranking_score=0.9,  # strict raw score — forbidden
            )

    def test_rank_result_is_not_strict_prediction_result(self):
        r = GeneralizedRankResult(
            abstention=GeneralizedRankAbstention(
                reason_code=GeneralizedRankReasonCode.no_hypotheses
            )
        )
        assert not isinstance(r, StrictPredictionResult)
        # none of the strict PredictionResult's required fields are present
        fields = set(GeneralizedRankResult.model_fields)
        for strict_field in ("run_id", "normalized_query", "snapshot_id", "decision"):
            assert strict_field not in fields

    def test_rank_result_lane_and_semantics_pinned(self):
        r = GeneralizedRankResult(
            abstention=GeneralizedRankAbstention(
                reason_code=GeneralizedRankReasonCode.no_hypotheses
            )
        )
        assert r.lane == "generalized"
        assert r.output_semantics == "exploratory_non_production"
        assert r.exploratory is True

    def test_abstention_is_not_strict_abstention(self):
        a = GeneralizedRankAbstention(
            reason_code=GeneralizedRankReasonCode.no_hypotheses,
        )
        assert a.lane == "generalized"
        assert not isinstance(a, StrictAbstention)
        # strict Abstention carries a `stage` field; the generalized abstention does not
        assert "stage" not in set(GeneralizedRankAbstention.model_fields)
        assert "lane" in set(GeneralizedRankAbstention.model_fields)

    def test_abstention_reason_code_is_controlled_vocab(self):
        # arbitrary string is rejected — user semantics clear
        with pytest.raises(ValidationError):
            GeneralizedRankAbstention(reason_code="made_up_reason")


# ---------------------------------------------------------------------------
# Consumption gate — re-run validate, never trust embedded validation (R1-04/OA-2)
# ---------------------------------------------------------------------------


class TestConsumptionGateRerunsValidation:
    def test_valid_built_hypothesis_is_ranked(self):
        h = make_built()
        r = rank_generalized([h], make_context())
        assert len(r.ranked) == 1
        assert r.ranked[0].hypothesis_id == "g1"
        assert r.abstention is None

    def test_does_not_trust_embedded_status_lie_distance(self):
        # The hypothesis was genuinely validated (status=validated, checks=full,
        # correct policy_content_hash). We mutate ONLY generalization_distance
        # after the build, leaving the embedded record still claiming "validated".
        # A ranker that trusted the embedded status would rank it; the gate must
        # re-run validate -> distance mismatch -> reject.
        h = make_built().model_copy(update={"generalization_distance": 0.99})
        assert h.validation.status == "validated"          # embedded record still lies
        assert h.validation.checks == list(VALIDATED_CHECKS)
        r = rank_generalized([h], make_context())
        assert r.ranked == []
        assert r.abstention is not None
        assert r.abstention.reason_code == GeneralizedRankReasonCode.no_validated_hypotheses
        assert len(r.rejected) == 1
        assert r.rejected[0].hypothesis_id == "g1"
        assert r.rejected[0].reason_code == GeneralizedRankRejectReasonCode.validation_failed
        # the reject detail must name the RE-RUN exception type (not the embedded status)
        assert "GeneralizedValidationError" in r.rejected[0].detail

    def test_does_not_trust_embedded_status_lie_ood(self):
        # Cite a relaxation outside the registered vocabulary while the embedded
        # record still claims validated. Re-run validate must reject (OOD).
        h = make_built().model_copy(update={"allowed_relaxation_ids": ["free_text_relaxation"]})
        assert h.validation.status == "validated"
        r = rank_generalized([h], make_context())
        assert r.ranked == []
        assert r.abstention is not None
        assert len(r.rejected) == 1
        assert r.rejected[0].reason_code == GeneralizedRankRejectReasonCode.validation_failed

    def test_does_not_trust_embedded_status_lie_version_pin(self):
        # Embedded record claims validated against v1.0.0, but the registered
        # policy is now v2.0.0 — version-pin mismatch must be re-caught.
        h = make_built()
        ctx = make_context(policy=make_policy(version="2.0.0"))
        assert h.validation.status == "validated"
        r = rank_generalized([h], ctx)
        assert r.ranked == []
        assert r.abstention is not None
        assert len(r.rejected) == 1
        assert "GeneralizedValidationError" in r.rejected[0].detail


# ---------------------------------------------------------------------------
# Lane-only ranking — no cross-lane raw score
# ---------------------------------------------------------------------------


class TestLaneOnlyRanking:
    def test_score_is_function_of_distance_only(self):
        # generalized_score is lane-internal; derived from generalization_distance
        assert abs(generalized_score(0.3) - (1.0 / 1.3)) < 1e-12
        assert generalized_score(0.0) == 1.0
        assert generalized_score(1.0) == 0.5

    def test_score_is_strictly_monotonic_decreasing_in_distance(self):
        assert generalized_score(0.2) > generalized_score(0.5) > generalized_score(1.0)

    def test_ranks_in_score_desc_order(self):
        near = make_built(hypothesis_id="near", rule_id="relax_ambiguity_margin",
                          failed=StrictCondition.no_critical_ambiguity)        # d=0.2
        mid = make_built(hypothesis_id="mid", rule_id="relax_donor_site_precision",
                         failed=StrictCondition.donor_site_definite)           # d=0.3
        far = make_built(hypothesis_id="far", rule_id="relax_precondition_completeness",
                         failed=StrictCondition.preconditions_complete)        # d=0.5
        r = rank_generalized([mid, far, near], make_context())
        assert [e.hypothesis_id for e in r.ranked] == ["near", "mid", "far"]
        assert [e.rank_position for e in r.ranked] == [1, 2, 3]
        assert r.ranked[0].generalized_score > r.ranked[1].generalized_score > r.ranked[2].generalized_score

    def test_deterministic_tiebreak_on_equal_distance(self):
        a = make_built(hypothesis_id="alpha",
                       rule_id="relax_donor_site_precision",
                       failed=StrictCondition.donor_site_definite)  # d=0.3
        b = make_built(hypothesis_id="beta",
                       rule_id="relax_donor_site_precision",
                       failed=StrictCondition.donor_site_definite)  # d=0.3
        r = rank_generalized([b, a], make_context())
        # equal score -> deterministic by hypothesis_id ascending
        assert [e.hypothesis_id for e in r.ranked] == ["alpha", "beta"]

    def test_rejects_strict_lane_input(self):
        # no strict masquerade on the INPUT side either: a strict Candidate
        # cannot be ranked in the generalized lane.
        strict_candidate = Candidate(
            candidate_id="c1",
            canonical_product="C",
            lane=Lane.strict,
            origin="strict_compiler",
        )
        with pytest.raises((GeneralizedValidationError, TypeError)):
            rank_generalized([strict_candidate], make_context())  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Abstain path — clear controlled-vocabulary semantics
# ---------------------------------------------------------------------------


class TestAbstainPath:
    def test_empty_input_abstains_no_hypotheses(self):
        r = rank_generalized([], make_context())
        assert r.ranked == []
        assert r.abstention is not None
        assert r.abstention.reason_code == GeneralizedRankReasonCode.no_hypotheses
        assert r.abstention.lane == "generalized"

    def test_all_rejected_abstains_no_validated_hypotheses(self):
        h = make_built().model_copy(update={"generalization_distance": 0.99})
        r = rank_generalized([h], make_context())
        assert r.ranked == []
        assert r.abstention is not None
        assert r.abstention.reason_code == GeneralizedRankReasonCode.no_validated_hypotheses
        assert len(r.rejected) == 1

    def test_all_beyond_max_distance_abstains_with_max_distance_reason(self):
        # all valid hypotheses but beyond the max-generalization-distance cap
        far = make_built(hypothesis_id="far",
                         rule_id="relax_precondition_completeness",
                         failed=StrictCondition.preconditions_complete)  # d=0.5
        r = rank_generalized([far], make_context(), max_generalization_distance=0.4)
        assert r.ranked == []
        assert r.abstention is not None
        assert r.abstention.reason_code == GeneralizedRankReasonCode.all_beyond_max_distance
        assert len(r.rejected) == 1
        assert r.rejected[0].reason_code == GeneralizedRankRejectReasonCode.beyond_max_distance

    def test_mixed_valid_and_rejected_only_ranks_valid(self):
        good = make_built(hypothesis_id="good")
        bad = make_built(hypothesis_id="bad").model_copy(update={"generalization_distance": 0.99})
        r = rank_generalized([good, bad], make_context())
        assert [e.hypothesis_id for e in r.ranked] == ["good"]
        assert len(r.rejected) == 1
        assert r.rejected[0].hypothesis_id == "bad"


# ---------------------------------------------------------------------------
# Result state-machine invariants
# ---------------------------------------------------------------------------


class TestResultStateMachine:
    def test_ranked_with_abstention_rejected(self):
        with pytest.raises(ValidationError):
            GeneralizedRankResult(
                ranked=[
                    GeneralizedRankEntry(
                        rank_position=1,
                        hypothesis_id="g1",
                        relaxation_policy_id="p8-generalized-relaxation",
                        policy_version="1.0.0",
                        generalization_distance=0.3,
                        generalized_score=1.0 / 1.3,
                    )
                ],
                abstention=GeneralizedRankAbstention(
                    reason_code=GeneralizedRankReasonCode.no_hypotheses,
                ),
            )

    def test_empty_ranked_requires_abstention(self):
        with pytest.raises(ValidationError):
            GeneralizedRankResult(ranked=[], abstention=None)

    def test_exploratory_cannot_be_turned_off(self):
        with pytest.raises(ValidationError):
            GeneralizedRankResult(exploratory=False)  # type: ignore[arg-type]
