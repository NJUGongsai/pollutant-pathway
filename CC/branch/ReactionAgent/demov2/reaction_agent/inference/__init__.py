"""P4 inference modules (evidence identity, support, counterevidence,
features, ranker, applicability, abstention, predictor).

P4 consumes validated strict candidates produced upstream (P3/P1). It never
creates or modifies chemical structures.
"""
from __future__ import annotations

from reaction_agent.inference.evidence_identity import resolve_evidence_identity
from reaction_agent.inference.support import aggregate_support
from reaction_agent.inference.counterevidence import collect_counterevidence
from reaction_agent.inference.features import build_feature_vector, build_support_feature_vector
from reaction_agent.inference.ranker import rank_strict_candidates
from reaction_agent.inference.applicability import assess_applicability
from reaction_agent.inference.abstention import (
    decide_abstention,
    detect_abstention_conditions,
)
from reaction_agent.inference.predictor import run_p4_pipeline, PipelineOutcome

__all__ = [
    "resolve_evidence_identity",
    "aggregate_support",
    "collect_counterevidence",
    "build_feature_vector",
    "build_support_feature_vector",
    "rank_strict_candidates",
    "assess_applicability",
    "decide_abstention",
    "detect_abstention_conditions",
    "run_p4_pipeline",
    "PipelineOutcome",
]
