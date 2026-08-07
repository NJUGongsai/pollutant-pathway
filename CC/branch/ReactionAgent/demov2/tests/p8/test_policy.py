"""T1 RED tests — Relaxation policy (final_plan §11.2, final_design §12.3).

Must FAIL (RED) until ``reaction_agent/p8/policy.py`` exists.

Scope (final_plan §11.2 + leader D2/D5/D6):
- policy_id + semver version + content hash; policy is an immutable artifact
- allowed_relaxations: registered typed vocabulary (no free text)
- forbidden_hard_constraints: explicit enum of never-relaxable strict conditions
- distance: generalization_distance definition + computable implementation
- OOD: out-of-distribution judgment policy declaration
- version pinning: hypothesis pins policy_id+version; new version = new policy
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from reaction_agent.p8.policy import (
    FORBIDDEN_HARD_CONSTRAINTS,
    RELAXABLE_CONDITIONS,
    STRICT_CONDITION_VOCABULARY,
    OODPolicy,
    RelaxationPolicy,
    RelaxationRule,
    StrictCondition,
    load_policy,
    save_policy,
)


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


def make_policy(**overrides) -> RelaxationPolicy:
    kwargs = dict(
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
    kwargs.update(overrides)
    return RelaxationPolicy.create(**kwargs)


class TestPolicyPin:
    def test_policy_has_pin_fields(self):
        p = make_policy()
        assert p.policy_id == "p8-generalized-relaxation"
        assert p.version == "1.0.0"
        assert isinstance(p.content_hash, str) and len(p.content_hash) == 64

    def test_version_must_be_semver(self):
        with pytest.raises(ValidationError):
            make_policy(version="1.0")  # not X.Y.Z

    def test_policy_is_immutable_frozen(self):
        p = make_policy()
        with pytest.raises(ValueError):
            p.version = "2.0.0"  # frozen — assignment rejected

    def test_content_hash_detects_tamper(self):
        p = make_policy()
        # any change to the body must invalidate the declared content hash
        with pytest.raises(ValidationError):
            RelaxationPolicy.model_validate(
                {
                    **p.model_dump(),
                    "description": "tampered description",
                }
            )


class TestRegisteredVocabulary:
    def test_relaxation_rule_has_typed_fields(self):
        r = make_rules()[0]
        assert r.rule_id == "relax_donor_site_precision"
        assert isinstance(r.description, str) and r.description
        assert r.applies_to == [StrictCondition.donor_site_definite]
        assert r.distance_weight == 0.3

    def test_cannot_relax_forbidden_hard_constraint(self):
        # relaxing a forbidden hard constraint is rejected at rule construction
        with pytest.raises(ValidationError):
            RelaxationRule(
                rule_id="illegal_relax_lineage",
                description="relax mapped lineage credibility",
                applies_to=[StrictCondition.trusted_mapped_lineage],
                distance_weight=0.1,
            )

    def test_forbidden_hard_constraints_frozen_on_policy(self):
        p = make_policy()
        assert set(p.forbidden_hard_constraints) == FORBIDDEN_HARD_CONSTRAINTS

    def test_vocabulary_partition_is_exhaustive_and_disjoint(self):
        # relaxable + forbidden must exactly partition the strict vocabulary
        assert RELAXABLE_CONDITIONS & FORBIDDEN_HARD_CONSTRAINTS == frozenset()
        assert RELAXABLE_CONDITIONS | FORBIDDEN_HARD_CONSTRAINTS == STRICT_CONDITION_VOCABULARY
        # forbidden core (final_design §12.2): lineage credibility, replayability, mass conservation
        assert StrictCondition.trusted_mapped_lineage in FORBIDDEN_HARD_CONSTRAINTS
        assert StrictCondition.graph_edit_replayable in FORBIDDEN_HARD_CONSTRAINTS
        assert StrictCondition.changed_heavy_atom_conservation in FORBIDDEN_HARD_CONSTRAINTS


class TestDistance:
    def test_distance_is_sum_of_weights(self):
        p = make_policy()
        assert p.distance([]) == 0.0
        assert abs(p.distance(["relax_donor_site_precision"]) - 0.3) < 1e-9
        assert abs(
            p.distance(["relax_donor_site_precision", "relax_precondition_completeness"]) - 0.8
        ) < 1e-9

    def test_distance_unknown_rule_raises(self):
        p = make_policy()
        with pytest.raises(Exception):
            p.distance(["not_a_registered_rule"])


class TestOOD:
    def test_ood_declared(self):
        p = make_policy()
        assert p.ood.declaration
        assert p.ood.boundary == "outside_registered_vocabulary"

    def test_is_ood_flags_unknown_relaxation(self):
        p = make_policy()
        assert p.is_ood(["relax_donor_site_precision"]) is False
        assert p.is_ood(["not_a_registered_rule"]) is True


class TestArtifactIO:
    def test_save_load_roundtrip(self, tmp_path: Path):
        p = make_policy()
        path = tmp_path / "policy.json"
        save_policy(p, path)
        loaded = load_policy(path)
        assert loaded == p
        assert loaded.content_hash == p.content_hash

    def test_load_detects_tamper(self, tmp_path: Path):
        p = make_policy()
        path = tmp_path / "policy.json"
        save_policy(p, path)
        data = json.loads(path.read_text(encoding="utf-8"))
        data["description"] = "forged"
        path.write_text(json.dumps(data), encoding="utf-8")
        with pytest.raises(ValidationError):
            load_policy(path)