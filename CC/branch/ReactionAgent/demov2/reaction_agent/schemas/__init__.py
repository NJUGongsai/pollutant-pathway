"""Pydantic v2 schema skeletons for P0 contract freeze.

These schemas define data contracts only. No business logic, no chemical
algorithms, no retrieval, no generation. P1+ will add implementations.

FORBIDDEN field names across all schemas:
- confidence / qualitative_confidence
- biological_probability / enzyme_activity_probability
"""

from reaction_agent.schemas.common import (
    StrictModel,
    NonEmptyStr,
    FORBIDDEN_FIELD_NAMES,
    MappingStatus,
    MappingQualityClass,
    SourceAssignmentMethod,
    LedgerBalanceStatus,
    ScientificAbstentionReason,
    SystemFailureReason,
    ResultStatus,
    DecisionKind,
    HypothesisOrigin,
    ApplicabilityLabel,
    Lane,
    ParticipantRole,
    EligibilityStatus,
    EvaluationBucket,
    QuarantineBehavior,
    ResearchDiagnosticEligibility,
    LineageResolutionQuality,
    AdaptationVerificationStatus,
    TargetKind,
)
from reaction_agent.schemas.mapping import (
    FormalSourceAssignment,
    FormalMappedAtomPair,
    MechanisticAtomOrigin,
    MechanisticAtomPair,
    MappingReport,
)
from reaction_agent.schemas.evidence import (
    RoleHypothesis,
    ReactionParticipant,
    ReactionEvidence,
)
from reaction_agent.schemas.lineage import (
    LineageEdge,
    LineageHypothesis,
    LineageResolution,
)
from reaction_agent.schemas.ledger import (
    RoleAssignment,
    StoichiometricEntry,
    FormalAtomTransferAssignment,
    MechanisticOriginEvidence,
    AddedAtomSource,
    RemovedAtomSink,
    ElementBalance,
    CofactorChange,
    QueryCandidateAdaptation,
    InheritedDonorContext,
    FormalBalanceUnderAssumptions,
    SourceReactionLedger,
    CandidateAnalogyLedger,
    LedgerReferenceRegistry,
    validate_candidate_ledger_references,
)
from reaction_agent.schemas.hypothesis import (
    AtomTarget,
    BondTarget,
    TypedTarget,
    TransformationHypothesis,
    SiteHypothesis,
    HypothesisReferenceRegistry,
    HypothesisValidationContext,
    ProductionSelectionHypothesis,
    AgentProposedHypothesis,
    Hypothesis,
    validate_hypothesis_references,
    validate_hypothesis_against_context,
)
from reaction_agent.schemas.candidate import Candidate
from reaction_agent.schemas.result import (
    Abstention,
    Failure,
    StageSummary,
    PredictionResult,
)
from reaction_agent.schemas.errors import (
    ContractViolation,
    LaneMixingError,
    InvariantViolationError,
    UnknownReferenceError,
)

__all__ = [
    # common
    "StrictModel", "NonEmptyStr", "FORBIDDEN_FIELD_NAMES",
    "MappingStatus", "MappingQualityClass", "SourceAssignmentMethod",
    "LedgerBalanceStatus", "ScientificAbstentionReason", "SystemFailureReason",
    "ResultStatus", "DecisionKind", "HypothesisOrigin",
    "ApplicabilityLabel", "Lane", "ParticipantRole",
    "EligibilityStatus", "EvaluationBucket", "QuarantineBehavior",
    "ResearchDiagnosticEligibility", "LineageResolutionQuality",
    "AdaptationVerificationStatus", "TargetKind",
    # mapping
    "FormalSourceAssignment", "FormalMappedAtomPair",
    "MechanisticAtomOrigin", "MechanisticAtomPair", "MappingReport",
    # evidence
    "RoleHypothesis", "ReactionParticipant", "ReactionEvidence",
    # lineage
    "LineageEdge", "LineageHypothesis", "LineageResolution",
    # ledger
    "RoleAssignment", "StoichiometricEntry", "FormalAtomTransferAssignment",
    "MechanisticOriginEvidence", "AddedAtomSource", "RemovedAtomSink",
    "ElementBalance", "CofactorChange", "QueryCandidateAdaptation",
    "InheritedDonorContext", "FormalBalanceUnderAssumptions",
    "SourceReactionLedger", "CandidateAnalogyLedger",
    "LedgerReferenceRegistry", "validate_candidate_ledger_references",
    # hypothesis
    "AtomTarget", "BondTarget", "TypedTarget",
    "TransformationHypothesis", "SiteHypothesis",
    "HypothesisReferenceRegistry", "HypothesisValidationContext",
    "ProductionSelectionHypothesis", "AgentProposedHypothesis",
    "Hypothesis", "validate_hypothesis_references",
    "validate_hypothesis_against_context",
    # candidate
    "Candidate",
    # result
    "Abstention", "Failure", "StageSummary", "PredictionResult",
    # errors
    "ContractViolation", "LaneMixingError", "InvariantViolationError",
    "UnknownReferenceError",
]
