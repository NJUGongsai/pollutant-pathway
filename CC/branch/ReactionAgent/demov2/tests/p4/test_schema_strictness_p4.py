"""P4 schema strictness: unknown fields, strict types, forbidden names."""
from __future__ import annotations

import pytest

from reaction_agent.schemas.common import FORBIDDEN_FIELD_NAMES
from reaction_agent.schemas.p4.evidence import EvidenceIdentity
from reaction_agent.schemas.p4.support import SupportBreakdown
from reaction_agent.schemas.p4.counterevidence import CounterevidenceRecord
from reaction_agent.schemas.p4.ranking import RankedStrictCandidate
from reaction_agent.schemas.p4.applicability import ApplicabilityAssessment
from reaction_agent.schemas.p4.decision import AbstentionDecision, PredictionDecision
from reaction_agent.schemas.p4.run import ImmutableRunManifest


def test_unknown_field_rejected():
    """P4: extra='forbid' on every P4 schema."""
    with pytest.raises(Exception):
        EvidenceIdentity(
            evidence_id="e1", canonical_identity="c", independent_group_id="g",
            unexpected_extra="nope")
    with pytest.raises(Exception):
        ImmutableRunManifest(
            run_id="r", request_hash="h", snapshot_id="s", snapshot_hash="sh",
            versions={}, trace=None, evidence_ids=[], independent_group_ids=[],
            result_hash="rh", freeze_state="active", unexpected_extra="nope")


def test_forbidden_probability_names():
    """P4: forbidden probability/confidence names must be absent from P4 schemas."""
    schema_modules = [
        "reaction_agent.schemas.p4.evidence",
        "reaction_agent.schemas.p4.support",
        "reaction_agent.schemas.p4.counterevidence",
        "reaction_agent.schemas.p4.ranking",
        "reaction_agent.schemas.p4.applicability",
        "reaction_agent.schemas.p4.decision",
        "reaction_agent.schemas.p4.run",
    ]
    import importlib
    for mod_name in schema_modules:
        mod = importlib.import_module(mod_name)
        # Walk StrictModel subclasses defined in the module.
        for name, obj in vars(mod).items():
            if isinstance(obj, type) and hasattr(obj, "model_fields"):
                fields = set(obj.model_fields.keys())
                overlap = fields & FORBIDDEN_FIELD_NAMES
                assert not overlap, f"{mod_name}.{name} has forbidden fields {overlap}"
                # also check any candidate dict in defaults
                for fname in FORBIDDEN_FIELD_NAMES:
                    assert fname not in fields


def test_no_implicit_type_coercion():
    """P4: strict types — '1' is not 1."""
    with pytest.raises(Exception):
        EvidenceIdentity(
            evidence_id=123, canonical_identity="c", independent_group_id="g")


def test_support_breakdown_requires_candidate_id():
    with pytest.raises(Exception):
        SupportBreakdown(
            candidate_id="", features=[], support_tier="none",
            evidence_strength="none", independent_evidence_count=0,
            all_evidence_ids=[], policy_version="v")


def test_abstention_decision_requires_scientific_reason():
    """P4: abstention reason_code is a ScientificAbstentionReason."""
    with pytest.raises(Exception):
        AbstentionDecision(
            reason_code="NOT_A_REASON", primary_reason="x", candidate_count=0,
            trace=None, policy_version="v", source_evidence_scope="s")
