"""P8 — Generalized Lane (Stage A: T1 Relaxation policy + T2 Generalized hypothesis).

P8 is an independent generalized (exploratory) lane, physically isolated from
the strict channel. This package only ADDS new files; it never modifies the
strict contracts (P3-P6), the shared hypothesis union, or P7.

- policy.py  (T1): Frozen RelaxationPolicy — registered relaxation vocabulary,
  forbidden hard constraints, generalization distance, OOD declaration, semver
  version + content hash, immutable JSON artifact.
- schemas.py (T2): GeneralizedHypothesis with six recorded fields, anti-
  masquerade lane pinning, and an independent validation chain.
"""
from __future__ import annotations

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
    validate_semver,
)
from reaction_agent.p8.schemas import (
    GeneralizedHypothesis,
    GeneralizedPolicyContext,
    GeneralizedValidation,
    SourceTransformRef,
    build_generalized_hypothesis,
    validate_generalized_hypothesis,
)

__all__ = [
    # policy (T1)
    "StrictCondition",
    "STRICT_CONDITION_VOCABULARY",
    "FORBIDDEN_HARD_CONSTRAINTS",
    "RELAXABLE_CONDITIONS",
    "validate_semver",
    "RelaxationRule",
    "OODPolicy",
    "RelaxationPolicy",
    "save_policy",
    "load_policy",
    # schemas (T2)
    "SourceTransformRef",
    "GeneralizedValidation",
    "GeneralizedHypothesis",
    "GeneralizedPolicyContext",
    "validate_generalized_hypothesis",
    "build_generalized_hypothesis",
]