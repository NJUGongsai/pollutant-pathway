"""P4-R1-G RED→GREEN: per-feature evidence grounding.

- a high ordinal scalar without real evidence must NOT produce in_domain/
  strong support — it is unknown/fail-closed;
- each support feature binds ONLY the evidence that genuinely supports it
  (never the full evidence set);
- counterevidence never fabricates ``unresolved:*`` evidence ids and never
  emits a record with an unknown source identity;
- evidence ids must exist in the verified resolution and share the namespace;
  orphan ids are rejected.
"""
from __future__ import annotations

import pytest

from tests.fixtures.p4.p4_contract_fixture import (
    build_evidence_records,
    build_strict_candidate,
    build_structural_context,
    POLICY_VERSION,
)
from reaction_agent.schemas.common import ApplicabilityLabel
from reaction_agent.schemas.p4.support import SupportTier
from reaction_agent.inference.evidence_identity import resolve_evidence_identity
from reaction_agent.inference.support import aggregate_support
from reaction_agent.inference.applicability import assess_applicability
from reaction_agent.inference.counterevidence import collect_counterevidence
from reaction_agent.inference.features import build_feature_vector


def _resolution():
    return resolve_evidence_identity(
        build_evidence_records(), policy_version=POLICY_VERSION)


class TestApplicabilityGrounding:
    def test_high_donor_similarity_without_evidence_is_unknown(self):
        """donor_similarity=3 with zero evidence can never be in_domain."""
        cand = build_strict_candidate()
        a = assess_applicability(cand, [], _resolution(),
                                 structural_context={"donor_similarity": 3})
        assert a.label == ApplicabilityLabel.unknown
        assert any(rc.value == "NO_STRUCTURAL_EVIDENCE" for rc in a.reason_codes)

    def test_in_domain_label_requires_evidence_ids(self):
        """A non-unknown applicability label must carry non-empty evidence ids."""
        cand = build_strict_candidate()
        a = assess_applicability(
            cand, build_evidence_records(), _resolution(),
            structural_context={"donor_similarity": 3},
            feature_evidence_ids={"donor_similarity": ["ev_d1", "ev_d2"]})
        assert a.label == ApplicabilityLabel.in_domain
        assert a.evidence_ids, "in_domain applicability must bind evidence ids"

    def test_evidence_ids_are_true_subset(self):
        """Applicability evidence ids must be a subset of the bound evidence,
        never the full evidence set."""
        cand = build_strict_candidate()
        records = build_evidence_records()
        a = assess_applicability(
            cand, records, _resolution(),
            structural_context={"donor_similarity": 3},
            feature_evidence_ids={"donor_similarity": ["ev_d1"]})
        assert set(a.evidence_ids) == {"ev_d1"}


class TestSupportGrounding:
    def test_feature_binds_only_its_own_evidence(self):
        """Each support feature binds the evidence that supports it — never
        the full evidence set."""
        cand = build_strict_candidate()
        records = build_evidence_records()
        binding = {
            "donor_structural_similarity": ["ev_d1", "ev_d2"],
            "transform_recurrence": ["ev_d1"],
        }
        sup = aggregate_support(
            cand, records, _resolution(),
            structural_context=build_structural_context(),
            feature_evidence_ids=binding)
        for f in sup.features:
            if f.feature_key == "independent_support_count":
                continue  # aggregate-derived: binds the full resolved set
            if f.feature_key in binding:
                assert set(f.evidence_ids) == set(binding[f.feature_key]), \
                    f"{f.feature_key} bound {f.evidence_ids} != {binding[f.feature_key]}"
            elif f.is_observable and f.feature_key not in binding:
                assert f.evidence_ids == [], \
                    f"{f.feature_key} observable but no per-feature binding"

    def test_high_ordinal_without_evidence_not_strong(self):
        """Structural ordinals with no evidence binding cannot yield strong
        support (no silent support from thin air)."""
        cand = build_strict_candidate()
        records = build_evidence_records()
        sup = aggregate_support(
            cand, records, _resolution(),
            structural_context=build_structural_context(),
            feature_evidence_ids={})  # no evidence bound to any feature
        assert sup.support_tier != SupportTier.strong


class TestCounterevidenceGrounding:
    def test_no_unresolved_pseudo_evidence_ids(self):
        """Counterevidence must never fabricate unresolved:* evidence ids."""
        cand = build_strict_candidate()
        coll = collect_counterevidence(
            cand, build_evidence_records(), _resolution(),
            context={"failed_preconditions": ["t_missing"]})
        for r in coll.records:
            assert not any(eid.startswith("unresolved:") for eid in r.evidence_ids), \
                f"unresolved pseudo id leaked: {r.evidence_ids}"

    def test_empty_source_evidence_no_record(self):
        """Counterevidence with no source evidence produces no record (or a
        typed unknown reason), never a record with unknown identity."""
        cand = build_strict_candidate()
        coll = collect_counterevidence(
            cand, [], _resolution(),
            context={"failed_preconditions": ["t_missing"]})
        for r in coll.records:
            assert r.source_identity != "unknown", \
                f"record with unknown source identity: {r.record_id}"
            assert r.evidence_ids, "record must bind real evidence ids"

    def test_unknown_evidence_ids_rejected(self):
        """Feature-bound evidence ids that do not exist in the verified
        resolution are rejected (orphan ids), never silently dropped."""
        from reaction_agent.inference.evidence_identity import (
            EvidenceIdentityValidationError)
        cand = build_strict_candidate()
        with pytest.raises(EvidenceIdentityValidationError):
            aggregate_support(
                cand, build_evidence_records(), _resolution(),
                structural_context=build_structural_context(),
                feature_evidence_ids={"donor_similarity": ["orphan_ev_999"]})

    def test_missing_snapshot_binding_rejected(self):
        """An evidence record without a snapshot binding cannot be resolved."""
        from reaction_agent.inference.evidence_identity import (
            EvidenceIdentityValidationError)
        records = [r.model_copy(update={"snapshot_id": ""})
                   for r in build_evidence_records()]
        with pytest.raises(EvidenceIdentityValidationError):
            resolve_evidence_identity(records, policy_version=POLICY_VERSION)

    def test_input_order_invariance(self):
        """Evidence input order does not change the resolution or support."""
        records = build_evidence_records()
        r1 = resolve_evidence_identity(records, policy_version=POLICY_VERSION)
        r2 = resolve_evidence_identity(list(reversed(records)),
                                       policy_version=POLICY_VERSION)
        assert r1.resolution_hash == r2.resolution_hash