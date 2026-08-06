"""P3 — Strict One-Step Kernel (final_plan §6).

P3 implements the mandatory LLM-free deterministic baseline:

    X only
    -> normalize
    -> adaptive distinct donor retrieval
    -> complete reaction load
    -> formal mapped lineage
    -> strict transform extraction
    -> conditioned site enumeration
    -> deterministic graph-edit generation
    -> molecule/ledger/transform validation
    -> canonical strict candidates
    -> unranked candidate + trace

Boundaries (final_plan §6.11, §15.4):
- P3 does NOT do final ranking, applicability decision, or final typed
  abstention adjudication.  P4 consumes the frozen candidate/trace.
- P3 never creates structures from free text.  All structures come from the
  deterministic graph-edit compiler.
- Missing real capability (real snapshot / automatic donor / complete P1
  evidence) is reported as a typed BLOCKED outcome, never a fake PASS.

P3 consumes P1 authority (snapshot, mapping, lineage, ledgers, eligibility)
as read-only inputs and does NOT modify any P1 / P0 / final-docs / ADR file.
"""

from reaction_agent.p3.schemas import (  # noqa: F401
    # enums
    EvidenceKind,
    CapabilityState,
    KernelStage,
    KernelStatus,
    SiteEligibility,
    # capability
    ComponentCapability,
    CapabilityStatus,
    # manifest
    ComponentVersion,
    KernelRunManifest,
    # query
    NormalizationPolicy,
    NormalizedQuery,
    # donor evidence
    DonorContext,
    ResolvedDonorEvidence,
    # transform
    BondChange,
    AtomStateChange,
    TransferredAtom,
    SitePrecondition,
    StrictTransformation,
    # site
    ConditionedSite,
    # generation
    EditApplicationLog,
    GenerationReport,
    # candidate
    CandidateValidation,
    CandidateEvidencePath,
    StrictCandidate,
    # trace
    StageTraceEntry,
    CandidateTrace,
    # failure / result
    KernelFailure,
    KernelResult,
)

__all__ = [
    "EvidenceKind",
    "CapabilityState",
    "KernelStage",
    "KernelStatus",
    "SiteEligibility",
    "ComponentCapability",
    "CapabilityStatus",
    "ComponentVersion",
    "KernelRunManifest",
    "NormalizationPolicy",
    "NormalizedQuery",
    "DonorContext",
    "ResolvedDonorEvidence",
    "BondChange",
    "AtomStateChange",
    "TransferredAtom",
    "SitePrecondition",
    "StrictTransformation",
    "ConditionedSite",
    "EditApplicationLog",
    "GenerationReport",
    "CandidateValidation",
    "StrictCandidate",
    "StageTraceEntry",
    "CandidateTrace",
    "KernelFailure",
    "KernelResult",
]

P3_SCHEMA_VERSION = "p3-1"
P3_KERNEL_VERSION = "p3-1"
