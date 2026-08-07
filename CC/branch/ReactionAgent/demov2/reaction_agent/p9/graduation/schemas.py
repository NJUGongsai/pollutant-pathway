"""P9-T2: Graduation package schemas (final_plan §12.2, final_design §19.3,
ADR-0002 graduation gate).

The nine graduation-package components (§12.2):

    1. hypothesis class        — HypothesisClass
    2. allowlist               — HypothesisClassAllowlist (frozen + content-hashed)
    3. held-out results        — HeldOutResults (§19.3 nine metrics, probability-free)
    4. shift results           — ShiftResults (family/scaffold shift)
    5. risk/coverage           — RiskCoverage
    6. grounding               — GroundingRecord
    7. cost                    — CostRecord
    8. ADR                     — ADRRecord (frozen + content-hashed)
    9. human approval          — HumanApproval | None (None -> demo BLOCKED)

Plus ``VersionPin`` (§19.3 "policy/model/tool versions") and the lane-pinned
``GraduationOutcome`` / ``ProductionRankingAdmission``.

EVIDENCE-BASED, NOT DECLARATION-BASED (ADR-0002): the ``GraduationPackage``
carries NO ``status`` / ``graduated`` / ``approved`` self-declaration field —
the gate (``reaction_agent.p9.graduation.gate``) is the sole arbiter that
re-evaluates the evidence against thresholds.

PROBABILITY-FREE LANE (§19.3): the agent_proposed lane introduces no
probability, so ``HeldOutResults.probability_introduced`` is pinned
``Literal[False]`` and there are NO Brier/ECE/calibration fields (extra="forbid"
rejects them). "没有 probability 时不伪造 calibration".

Hard boundary (strict untouched): ADDITIVE only. Consumes the §19.2 hypothesis
schema and Phase B's report口径; never modifies the strict channel (P3-P6),
P7, P8, Phase B's agent_proposed lane, or deepseek's external/ package.
"""
from __future__ import annotations

import re
from enum import Enum
from typing import Literal

from pydantic import ConfigDict, Field, field_validator, model_validator

from reaction_agent.hashing import canonical_hash
from reaction_agent.schemas.common import NonEmptyStr, StrictModel
from reaction_agent.schemas.errors import ContractViolation


_SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")


def _validate_semver(v: str) -> str:
    if not _SEMVER_RE.match(v):
        raise ValueError(f"version must be semver X.Y.Z, got {v!r}")
    return v


# ---------------------------------------------------------------------------
# Controlled vocabularies (no free text — ADR-0002 "user semantics clear")
# ---------------------------------------------------------------------------


class GraduationStatus(str, Enum):
    """Outcome of the graduation gate (sole arbiter, evidence-based)."""

    graduated = "graduated"
    blocked = "blocked"


class BlockerReasonCode(str, Enum):
    """Why a graduation package was blocked (controlled vocabulary, no free text)."""

    missing_hypothesis_class = "missing_hypothesis_class"
    class_not_in_allowlist = "class_not_in_allowlist"
    incomplete_held_out_evaluation = "incomplete_held_out_evaluation"
    incremental_recall_unmeasured = "incremental_recall_unmeasured"
    incremental_recall_insufficient = "incremental_recall_insufficient"
    missing_shift_results = "missing_shift_results"
    excessive_family_scaffold_shift = "excessive_family_scaffold_shift"
    missing_risk_coverage = "missing_risk_coverage"
    risk_exceeds_threshold = "risk_exceeds_threshold"
    missing_grounding = "missing_grounding"
    grounding_insufficient = "grounding_insufficient"
    missing_cost = "missing_cost"
    missing_adr = "missing_adr"
    adr_not_accepted = "adr_not_accepted"
    missing_human_approval = "missing_human_approval"
    invented_id_or_structure_mutation_nonzero = "invented_id_or_structure_mutation_nonzero"
    repeated_run_agreement_below_threshold = "repeated_run_agreement_below_threshold"
    missing_version_pin = "missing_version_pin"


# ---------------------------------------------------------------------------
# Component 1: hypothesis class
# ---------------------------------------------------------------------------


class HypothesisClass(StrictModel):
    """The hypothesis class being graduated (component 1)."""

    class_id: NonEmptyStr
    description: NonEmptyStr
    transformation_family_ids: list[NonEmptyStr]
    chain_policy_version: NonEmptyStr  # links to Phase B chain policy

    @field_validator("chain_policy_version")
    @classmethod
    def _semver(cls, v: str) -> str:
        return _validate_semver(v)


# ---------------------------------------------------------------------------
# Component 2: hypothesis class allowlist (frozen + content-hashed)
# ---------------------------------------------------------------------------


class HypothesisClassAllowlist(StrictModel):
    """Registered allowlist of hypothesis classes (component 2).

    Frozen + content-hashed: a class not in this allowlist cannot graduate.
    """

    model_config = ConfigDict(**StrictModel.model_config, frozen=True)

    allowlist_id: NonEmptyStr
    version: NonEmptyStr
    registered_classes: list[HypothesisClass]
    content_hash: NonEmptyStr

    @field_validator("version")
    @classmethod
    def _semver_version(cls, v: str) -> str:
        return _validate_semver(v)

    @model_validator(mode="after")
    def _verify_content_hash(self) -> "HypothesisClassAllowlist":
        body = self.model_dump(exclude={"content_hash"})
        recomputed = canonical_hash(body)
        if self.content_hash != recomputed:
            raise ValueError(
                f"content_hash mismatch: expected {recomputed}, got {self.content_hash}"
            )
        return self

    @classmethod
    def create(
        cls,
        *,
        allowlist_id: str,
        version: str,
        registered_classes: list[HypothesisClass],
    ) -> "HypothesisClassAllowlist":
        body = {
            "allowlist_id": allowlist_id,
            "version": _validate_semver(version),
            "registered_classes": [c.model_dump() for c in registered_classes],
        }
        return cls(
            allowlist_id=allowlist_id,
            version=version,
            registered_classes=registered_classes,
            content_hash=canonical_hash(body),
        )


# ---------------------------------------------------------------------------
# Component 4: shift results (family/scaffold shift)
# ---------------------------------------------------------------------------


class ShiftResult(StrictModel):
    """Per-family/scaffold held-out shift result."""

    family_id: NonEmptyStr
    scaffold: NonEmptyStr
    recall: float | None = None
    risk: float = Field(ge=0.0)
    n_held_out: int = Field(ge=0)


class ShiftResults(StrictModel):
    """Family/scaffold shift evaluation (component 4)."""

    results: list[ShiftResult] = []
    max_recall_drop: float = Field(ge=0.0)


# ---------------------------------------------------------------------------
# Component 5: risk / coverage
# ---------------------------------------------------------------------------


class RiskCoverage(StrictModel):
    """Risk at fixed coverage + coverage curve (component 5)."""

    risk_at_fixed_coverage: float = Field(ge=0.0)
    fixed_coverage: float = Field(ge=0.0, le=1.0)
    coverage_curve: list[dict] = []


# ---------------------------------------------------------------------------
# Component 6: grounding
# ---------------------------------------------------------------------------


class GroundingRecord(StrictModel):
    """Grounding evidence (component 6)."""

    grounding_score: float = Field(ge=0.0, le=1.0)
    grounded_family_ids: list[NonEmptyStr] = []
    ungrounded_family_ids: list[NonEmptyStr] = []


# ---------------------------------------------------------------------------
# Component 7: cost
# ---------------------------------------------------------------------------


class CostRecord(StrictModel):
    """Cost/latency/tool calls (component 7). Mock provider values — never a real API burn."""

    llm_calls: int = 0
    tool_calls: int = 0
    latency_ms: int = 0


# ---------------------------------------------------------------------------
# Component 3: held-out results (§19.3 nine metrics, probability-free)
# ---------------------------------------------------------------------------


class HeldOutResults(StrictModel):
    """Held-out evaluation covering the §19.3 nine metrics (component 3).

    PROBABILITY-FREE LANE: ``probability_introduced`` is pinned ``Literal[False]``
    and there are NO Brier/ECE/calibration fields (extra="forbid" rejects them).
    §19.3: "没有 probability 时不伪造 calibration". A package that claims
    ``probability_introduced=True`` is rejected at construction; a consumer that
    attempts to attach ``brier`` / ``ece`` is rejected by extra="forbid".
    """

    # §19.3 nine metrics
    incremental_recall: float | None = None  # truth-set denominator (Phase B口径)
    added_incorrect: int = 0
    risk_at_fixed_coverage: float = Field(ge=0.0)
    abstention_impact: float = Field(ge=0.0)
    repeated_run_agreement: float = Field(ge=0.0, le=1.0)
    grounding_score: float = Field(ge=0.0, le=1.0)
    invented_id_or_structure_mutations: int = Field(ge=0)
    cost: CostRecord
    shift: ShiftResults

    # pinned probability-free (no fake calibration)
    probability_introduced: Literal[False] = False


# ---------------------------------------------------------------------------
# Component 8: ADR (frozen + content-hashed)
# ---------------------------------------------------------------------------


ADRStatus = Literal["proposed", "accepted", "superseded"]


class ADRRecord(StrictModel):
    """Decision record (component 8). Frozen + content-hashed.

    The demo uses ``status="proposed"`` (not accepted) — a non-accepted ADR is a
    graduation blocker, never a faked approval.
    """

    model_config = ConfigDict(**StrictModel.model_config, frozen=True)

    adr_id: NonEmptyStr
    title: NonEmptyStr
    status: ADRStatus
    rationale: NonEmptyStr
    content_hash: NonEmptyStr

    @model_validator(mode="after")
    def _verify_content_hash(self) -> "ADRRecord":
        body = self.model_dump(exclude={"content_hash"})
        recomputed = canonical_hash(body)
        if self.content_hash != recomputed:
            raise ValueError(
                f"content_hash mismatch: expected {recomputed}, got {self.content_hash}"
            )
        return self

    @classmethod
    def create(
        cls,
        *,
        adr_id: str,
        title: str,
        status: ADRStatus,
        rationale: str,
    ) -> "ADRRecord":
        body = {
            "adr_id": adr_id,
            "title": title,
            "status": status,
            "rationale": rationale,
        }
        return cls(
            adr_id=adr_id,
            title=title,
            status=status,
            rationale=rationale,
            content_hash=canonical_hash(body),
        )


# ---------------------------------------------------------------------------
# Component 9: human approval
# ---------------------------------------------------------------------------


class HumanApproval(StrictModel):
    """Human approval (component 9). The demo blocker — ``None`` when not approved.

    A real approval requires a signed ``approval_token``; the demo has no real
    approver, so the package is built with ``human_approval=None`` and the gate
    returns BLOCKED (expected terminal state, never a faked PASS).
    """

    approver_id: NonEmptyStr
    approved_at: NonEmptyStr  # RFC3339 timestamp
    approval_token: NonEmptyStr
    notes: str = ""


# ---------------------------------------------------------------------------
# Version pin (§19.3 "policy/model/tool versions")
# ---------------------------------------------------------------------------


class VersionPin(StrictModel):
    """policy/model/tool versions pinned for the graduation package (§19.3)."""

    policy_version: NonEmptyStr
    model_version: NonEmptyStr
    tool_version: NonEmptyStr
    chain_policy_content_hash: NonEmptyStr  # links to Phase B chain policy artifact

    @field_validator("policy_version")
    @classmethod
    def _semver_policy(cls, v: str) -> str:
        return _validate_semver(v)


# ---------------------------------------------------------------------------
# The 9-component package (content-hashed, NO self-declared status)
# ---------------------------------------------------------------------------


class GraduationPackage(StrictModel):
    """The nine-component graduation package (§12.2) + version pin.

    EVIDENCE-BASED, NOT DECLARATION-BASED (ADR-0002): this package carries NO
    ``status`` / ``graduated`` / ``approved`` self-declaration field — only
    evidence. The gate (``evaluate_graduation``) is the sole arbiter that
    re-evaluates this evidence against thresholds and emits a ``GraduationOutcome``.
    """

    package_id: NonEmptyStr
    hypothesis_class: HypothesisClass            # 1
    allowlist: HypothesisClassAllowlist          # 2
    held_out_results: HeldOutResults             # 3
    shift_results: ShiftResults                  # 4
    risk_coverage: RiskCoverage                  # 5
    grounding: GroundingRecord                   # 6
    cost: CostRecord                              # 7
    adr: ADRRecord                                # 8
    human_approval: HumanApproval | None          # 9 — None when not approved (demo BLOCKED)
    version_pin: VersionPin
    content_hash: NonEmptyStr

    @model_validator(mode="after")
    def _verify_content_hash(self) -> "GraduationPackage":
        body = self.model_dump(exclude={"content_hash"})
        recomputed = canonical_hash(body)
        if self.content_hash != recomputed:
            raise ValueError(
                f"content_hash mismatch: expected {recomputed}, got {self.content_hash}"
            )
        return self

    @classmethod
    def create(
        cls,
        *,
        package_id: str,
        hypothesis_class: HypothesisClass,
        allowlist: HypothesisClassAllowlist,
        held_out_results: HeldOutResults,
        shift_results: ShiftResults,
        risk_coverage: RiskCoverage,
        grounding: GroundingRecord,
        cost: CostRecord,
        adr: ADRRecord,
        human_approval: HumanApproval | None,
        version_pin: VersionPin,
    ) -> "GraduationPackage":
        body = {
            "package_id": package_id,
            "hypothesis_class": hypothesis_class.model_dump(),
            "allowlist": allowlist.model_dump(),
            "held_out_results": held_out_results.model_dump(),
            "shift_results": shift_results.model_dump(),
            "risk_coverage": risk_coverage.model_dump(),
            "grounding": grounding.model_dump(),
            "cost": cost.model_dump(),
            "adr": adr.model_dump(),
            "human_approval": human_approval.model_dump() if human_approval else None,
            "version_pin": version_pin.model_dump(),
        }
        return cls(
            package_id=package_id,
            hypothesis_class=hypothesis_class,
            allowlist=allowlist,
            held_out_results=held_out_results,
            shift_results=shift_results,
            risk_coverage=risk_coverage,
            grounding=grounding,
            cost=cost,
            adr=adr,
            human_approval=human_approval,
            version_pin=version_pin,
            content_hash=canonical_hash(body),
        )


# ---------------------------------------------------------------------------
# Gate outcome (lane-pinned, NOT a production rank)
# ---------------------------------------------------------------------------


class GraduationOutcome(StrictModel):
    """The gate's verdict on a graduation package. NOT a production rank.

    Lane is Literal-pinned to "agent_proposed"; ``output_semantics`` is pinned
    ``graduation_gate``. There is no ``ranking_score`` / ``run_id`` / ``decision``
    / ``canonical_product`` — structurally distinct from the strict
    ``PredictionResult`` / ``Candidate``.
    """

    lane: Literal["agent_proposed"] = "agent_proposed"
    output_semantics: Literal["graduation_gate"] = "graduation_gate"
    status: GraduationStatus
    blockers: list[BlockerReasonCode] = []
    package_content_hash: NonEmptyStr


# ---------------------------------------------------------------------------
# Production ranking admission (only constructable from a graduated outcome)
# ---------------------------------------------------------------------------


class ProductionRankingAdmission(StrictModel):
    """Proof that a hypothesis class graduated and may enter production ranking.

    Only constructable via ``admit_to_production_ranking`` from a ``graduated``
    outcome — a ``blocked`` outcome raises ``GraduationBlockedError``, so a
    non-graduated class is structurally barred from production ranking
    (§12.2 "未毕业不进入 production ranking").
    """

    lane: Literal["agent_proposed"] = "agent_proposed"
    admitted: Literal[True] = True
    graduated_package_hash: NonEmptyStr
    human_approval_id: NonEmptyStr
    adr_id: NonEmptyStr


# ---------------------------------------------------------------------------
# Error + thresholds
# ---------------------------------------------------------------------------


class GraduationBlockedError(ContractViolation):
    """Raised when a blocked outcome is admitted to production ranking."""


class GraduationThresholds(StrictModel):
    """Configurable thresholds for the evidence-based gate."""

    max_risk: float = 0.3
    min_repeated_run_agreement: float = 0.9
    min_grounding: float = 0.8
    min_incremental_recall: float = 0.1
    max_recall_drop: float = 0.2


DEFAULT_GRADUATION_THRESHOLDS = GraduationThresholds()


__all__ = [
    "GraduationStatus",
    "BlockerReasonCode",
    "HypothesisClass",
    "HypothesisClassAllowlist",
    "ShiftResult",
    "ShiftResults",
    "RiskCoverage",
    "GroundingRecord",
    "CostRecord",
    "HeldOutResults",
    "ADRStatus",
    "ADRRecord",
    "HumanApproval",
    "VersionPin",
    "GraduationPackage",
    "GraduationOutcome",
    "ProductionRankingAdmission",
    "GraduationBlockedError",
    "GraduationThresholds",
    "DEFAULT_GRADUATION_THRESHOLDS",
]
