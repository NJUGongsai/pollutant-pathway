"""P9-T2: Graduation package + evidence-based gate (final_plan §12.2,
final_design §19.3, ADR-0002).

The graduation gate is the sole arbiter of whether an agent-proposed
hypothesis class may enter production ranking. It re-evaluates a
``GraduationPackage`` (nine components + version pin) against thresholds and
emits a ``GraduationOutcome`` (graduated / blocked). The package carries no
self-declared status — the gate re-derives it from evidence every call.

Public API:
- schemas: GraduationStatus, BlockerReasonCode, HypothesisClass,
           HypothesisClassAllowlist, ShiftResult, ShiftResults, RiskCoverage,
           GroundingRecord, CostRecord, HeldOutResults, ADRRecord,
           HumanApproval, VersionPin, GraduationPackage, GraduationOutcome,
           ProductionRankingAdmission, GraduationBlockedError,
           GraduationThresholds, DEFAULT_GRADUATION_THRESHOLDS
- gate:   evaluate_graduation, admit_to_production_ranking,
          build_valid_graduation_package, build_demo_graduation_package
"""
from __future__ import annotations

from reaction_agent.p9.graduation.schemas import (
    ADRRecord,
    ADRStatus,
    BlockerReasonCode,
    CostRecord,
    DEFAULT_GRADUATION_THRESHOLDS,
    GraduationBlockedError,
    GraduationOutcome,
    GraduationPackage,
    GraduationStatus,
    GraduationThresholds,
    GroundingRecord,
    HeldOutResults,
    HumanApproval,
    HypothesisClass,
    HypothesisClassAllowlist,
    ProductionRankingAdmission,
    RiskCoverage,
    ShiftResult,
    ShiftResults,
    VersionPin,
)
from reaction_agent.p9.graduation.gate import (
    admit_to_production_ranking,
    build_demo_graduation_package,
    build_valid_graduation_package,
    evaluate_graduation,
)

__all__ = [
    # schemas
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
    # gate
    "evaluate_graduation",
    "admit_to_production_ranking",
    "build_valid_graduation_package",
    "build_demo_graduation_package",
]
