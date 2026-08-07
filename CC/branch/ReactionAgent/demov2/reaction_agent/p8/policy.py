"""P8-T1: Relaxation policy — generalized lane (final_plan §11.2, final_design §12.3).

Freezes the registered vocabulary that governs how strict conditions may be
relaxed for generalized (exploratory) candidates. NO free-text relaxation
rules (§12.3): every relaxation must be a registered ``RelaxationRule``, and
the policy artifact is immutable (frozen + content-hashed) once created.

Hard boundary (strict untouched): this module only ADDS the generalized lane.
It never imports or modifies the strict channel (P3-P6) or its contracts.
"""
from __future__ import annotations

import json
import re
from enum import Enum
from pathlib import Path
from typing import Literal

from pydantic import ConfigDict, Field, field_validator, model_validator

from reaction_agent.hashing import canonical_hash
from reaction_agent.schemas.common import NonEmptyStr, StrictModel


# ---------------------------------------------------------------------------
# Strict condition vocabulary (final_design §12.2)
# ---------------------------------------------------------------------------


class StrictCondition(str, Enum):
    """Strict transform requirements (final_design §12.2)."""

    trusted_mapped_lineage = "trusted_mapped_lineage"
    graph_edit_replayable = "graph_edit_replayable"
    donor_site_definite = "donor_site_definite"
    preconditions_complete = "preconditions_complete"
    changed_heavy_atom_conservation = "changed_heavy_atom_conservation"
    no_critical_ambiguity = "no_critical_ambiguity"


STRICT_CONDITION_VOCABULARY = frozenset(StrictCondition)

# Hard constraints that can never be relaxed (final_design §12.2): a broken
# mapped lineage, a non-replayable graph edit, or broken heavy-atom mass
# conservation all destroy the transform's scientific foundation.
FORBIDDEN_HARD_CONSTRAINTS = frozenset({
    StrictCondition.trusted_mapped_lineage,
    StrictCondition.graph_edit_replayable,
    StrictCondition.changed_heavy_atom_conservation,
})

# Conditions that MAY be relaxed via the registered vocabulary.
RELAXABLE_CONDITIONS = frozenset(StrictCondition) - FORBIDDEN_HARD_CONSTRAINTS


# ---------------------------------------------------------------------------
# Semver validation
# ---------------------------------------------------------------------------

_SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")


def validate_semver(v: str) -> str:
    """Strict semver ``X.Y.Z`` (no prerelease/build tokens for the frozen pin)."""
    if not _SEMVER_RE.match(v):
        raise ValueError(f"version must be semver X.Y.Z, got {v!r}")
    return v


# ---------------------------------------------------------------------------
# Relaxation rule (registered vocabulary entry)
# ---------------------------------------------------------------------------


class RelaxationRule(StrictModel):
    """A registered relaxation — the ONLY way a strict condition may be relaxed.

    Typed fields (id / description / applicable conditions / distance weight)
    replace free-text rule creation (final_design §12.3, leader D6).
    """

    rule_id: NonEmptyStr
    description: NonEmptyStr
    applies_to: list[StrictCondition]
    distance_weight: float = Field(ge=0.0)

    @field_validator("applies_to", mode="before")
    @classmethod
    def _coerce_conditions(cls, v):
        """Normalize string values to enum instances (required for loading the
        JSON artifact, since strict typing forbids implicit coercion)."""
        if isinstance(v, list):
            return [c if isinstance(c, StrictCondition) else StrictCondition(c) for c in v]
        return v

    @model_validator(mode="after")
    def _only_relaxable_conditions(self) -> "RelaxationRule":
        for c in self.applies_to:
            if c not in RELAXABLE_CONDITIONS:
                raise ValueError(
                    f"{c.value} is a forbidden hard constraint and can never be relaxed"
                )
        return self


# ---------------------------------------------------------------------------
# OOD judgment policy (declaration)
# ---------------------------------------------------------------------------


class OODPolicy(StrictModel):
    """Out-of-distribution judgment strategy declaration (final_plan §11.2).

    The boundary is the registered vocabulary: a generalized hypothesis that
    cites a relaxation outside the policy's registered rules is
    out-of-distribution and rejected (fail-closed).
    """

    declaration: NonEmptyStr
    boundary: Literal["outside_registered_vocabulary"] = "outside_registered_vocabulary"
    behavior: Literal["reject"] = "reject"


# ---------------------------------------------------------------------------
# Relaxation policy (immutable, content-hashed artifact)
# ---------------------------------------------------------------------------


class RelaxationPolicy(StrictModel):
    """Frozen relaxation policy artifact.

    ``policy_id`` is the stable logical identity; ``version`` is semver; a
    content change bumps ``version`` and yields a new ``content_hash``. A
    generalized hypothesis pins ``policy_id + version`` (leader D2/D5).
    """

    model_config = ConfigDict(**StrictModel.model_config, frozen=True)

    policy_id: NonEmptyStr
    version: NonEmptyStr
    description: NonEmptyStr = "none"
    allowed_relaxations: list[RelaxationRule]
    forbidden_hard_constraints: list[StrictCondition]
    ood: OODPolicy
    content_hash: NonEmptyStr

    @field_validator("version")
    @classmethod
    def _semver_version(cls, v: str) -> str:
        return validate_semver(v)

    @field_validator("forbidden_hard_constraints", mode="before")
    @classmethod
    def _coerce_forbidden(cls, v):
        """Normalize string values to enum instances (JSON artifact load)."""
        if isinstance(v, list):
            return [c if isinstance(c, StrictCondition) else StrictCondition(c) for c in v]
        return v

    @field_validator("forbidden_hard_constraints")
    @classmethod
    def _exact_forbidden_set(cls, v: list) -> list:
        if not v:
            raise ValueError("forbidden_hard_constraints must be non-empty")
        declared = set(v)
        if declared != FORBIDDEN_HARD_CONSTRAINTS:
            expected = sorted(c.value for c in FORBIDDEN_HARD_CONSTRAINTS)
            raise ValueError(
                f"forbidden_hard_constraints must equal the design-set {expected}, "
                f"got {sorted(c.value for c in declared)}"
            )
        return v

    @model_validator(mode="after")
    def _verify_content_hash(self) -> "RelaxationPolicy":
        body = self.model_dump(exclude={"content_hash"})
        recomputed = canonical_hash(body)
        if self.content_hash != recomputed:
            raise ValueError(
                f"content_hash mismatch: expected {recomputed}, got {self.content_hash}"
            )
        return self

    # -- construction helper (computes the content hash) --

    @classmethod
    def create(
        cls,
        *,
        policy_id: str,
        version: str,
        description: str,
        allowed_relaxations: list[RelaxationRule],
        ood: OODPolicy,
    ) -> "RelaxationPolicy":
        """Build a policy, computing its content_hash over the frozen body.

        The hash is computed over the canonical *serialized* body (enums as
        their string values) so it matches ``model_dump``; the model is then
        constructed with enum instances so strict typing accepts it.
        """
        serialized = {
            "policy_id": policy_id,
            "version": version,
            "description": description,
            "allowed_relaxations": [r.model_dump() for r in allowed_relaxations],
            "forbidden_hard_constraints": sorted(
                c.value for c in FORBIDDEN_HARD_CONSTRAINTS
            ),
            "ood": ood.model_dump(),
        }
        content_hash = canonical_hash(serialized)
        body = {
            **serialized,
            "forbidden_hard_constraints": sorted(
                FORBIDDEN_HARD_CONSTRAINTS, key=lambda c: c.value
            ),
            "content_hash": content_hash,
        }
        return cls(**body)

    # -- registered vocabulary / distance / OOD --

    def rule_ids(self) -> frozenset[str]:
        return frozenset(r.rule_id for r in self.allowed_relaxations)

    def rule_by_id(self, rule_id: str) -> RelaxationRule:
        for r in self.allowed_relaxations:
            if r.rule_id == rule_id:
                return r
        raise KeyError(f"unknown relaxation rule_id: {rule_id}")

    def distance(self, allowed_relaxation_ids: list[str]) -> float:
        """generalization_distance = sum of weights of applied relaxations.

        Derived from the failed/relaxed conditions via the registered weights.
        Raises KeyError if any cited relaxation is not registered.
        """
        return sum(self.rule_by_id(rid).distance_weight for rid in allowed_relaxation_ids)

    def is_ood(self, allowed_relaxation_ids: list[str]) -> bool:
        """True iff any cited relaxation falls outside the registered vocabulary."""
        known = self.rule_ids()
        return any(rid not in known for rid in allowed_relaxation_ids)


# ---------------------------------------------------------------------------
# Artifact I/O
# ---------------------------------------------------------------------------


def save_policy(policy: RelaxationPolicy, path: Path) -> Path:
    """Persist the policy as canonical JSON (immutable artifact)."""
    path = Path(path)
    path.write_text(
        json.dumps(policy.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return path


def load_policy(path: Path) -> RelaxationPolicy:
    """Load and validate a policy artifact; content-hash is re-verified.

    Raises pydantic ValidationError on any tamper or schema violation.
    """
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return RelaxationPolicy.model_validate(data)


__all__ = [
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
]