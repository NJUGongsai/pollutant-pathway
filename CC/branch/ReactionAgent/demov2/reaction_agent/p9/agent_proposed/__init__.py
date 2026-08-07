"""P9-T1: AgentProposedHypothesis lane (final_plan §12.1, final_design §19.2).

Physically isolated, exploratory, NON-production lane. An
``AgentProposedHypothesis`` must pass the eight-step validation chain before
receiving an ``agent_proposed`` lane candidate. The lane is ADDITIVE only — it
never modifies the strict channel (P3-P6), P7, or P8.

Public API:
- policy:      AgentProposedChainPolicy, DEFAULT_AGENT_PROPOSED_CHAIN_POLICY,
               CHAIN_STEPS, CHAIN_CHECK_NAMES
- schemas:     CompiledGraphEdit, EditedMolecule, AgentProposedValidation,
               AgentProposedCandidate, QueryMoleculeContext,
               LaneScopedCandidateLedger, AgentProposedValidationContext,
               AgentProposedValidationError, AgentProposedRejectReasonCode,
               compile_typed_targets, apply_graph_edit, validate_molecule,
               validate_dual_ledger, validate_grounding,
               validate_agent_proposed_hypothesis, build_agent_proposed_candidate,
               revalidate_agent_proposed_candidate
- report:      AgentProposedCostReport, AgentProposedReproducibility,
               AgentProposedReport, build_agent_proposed_report
"""
from __future__ import annotations

from reaction_agent.p9.agent_proposed.policy import (
    CHAIN_CHECK_NAMES,
    CHAIN_STEPS,
    AgentProposedChainPolicy,
    DEFAULT_AGENT_PROPOSED_CHAIN_POLICY,
)
from reaction_agent.p9.agent_proposed.schemas import (
    AgentProposedCandidate,
    AgentProposedRejectReasonCode,
    AgentProposedValidationError,
    AgentProposedValidation,
    AgentProposedValidationContext,
    CompiledGraphEdit,
    EditedMolecule,
    LaneScopedCandidateLedger,
    QueryMoleculeContext,
    apply_graph_edit,
    build_agent_proposed_candidate,
    compile_typed_targets,
    revalidate_agent_proposed_candidate,
    validate_agent_proposed_hypothesis,
    validate_dual_ledger,
    validate_grounding,
    validate_molecule,
)
from reaction_agent.p9.agent_proposed.report import (
    AgentProposedCostReport,
    AgentProposedReport,
    AgentProposedReproducibility,
    build_agent_proposed_report,
)

__all__ = [
    # policy
    "CHAIN_STEPS",
    "CHAIN_CHECK_NAMES",
    "AgentProposedChainPolicy",
    "DEFAULT_AGENT_PROPOSED_CHAIN_POLICY",
    # schemas / chain
    "AgentProposedValidationError",
    "AgentProposedRejectReasonCode",
    "CompiledGraphEdit",
    "EditedMolecule",
    "AgentProposedValidation",
    "AgentProposedCandidate",
    "QueryMoleculeContext",
    "LaneScopedCandidateLedger",
    "AgentProposedValidationContext",
    "compile_typed_targets",
    "apply_graph_edit",
    "validate_molecule",
    "validate_dual_ledger",
    "validate_grounding",
    "validate_agent_proposed_hypothesis",
    "build_agent_proposed_candidate",
    "revalidate_agent_proposed_candidate",
    # report
    "AgentProposedCostReport",
    "AgentProposedReproducibility",
    "AgentProposedReport",
    "build_agent_proposed_report",
]
