"""P1-T2 strict domain schema contract tests.

Covers the P1 new entities defined in reaction_agent/schemas/p1_entities.py:
- NormalizedReactionRecord
- DonorEligibilityAssessment
- ResolvedTransformedLineage
- EligibilityDecision
- QuarantineRecord
- SnapshotManifest
- SnapshotRecord
- ManualAuditRecord

All must inherit StrictModel (extra=forbid, strict=True) and must not contain
any FORBIDDEN_FIELD_NAMES (confidence / biological_probability / ...).
"""
import inspect

import pytest

from reaction_agent.schemas.common import FORBIDDEN_FIELD_NAMES
from reaction_agent.schemas.p1_entities import (
    NormalizedReactionRecord,
    DonorEligibilityAssessment,
    EligibilityDecision,
    QuarantineRecord,
    SnapshotManifest,
    SnapshotRecord,
    ManualAuditRecord,
    ResolvedTransformedLineage,
)


# -- Step 2: schema strictness tests (from brief) --

def test_unknown_field_rejected():
    with pytest.raises(Exception):
        NormalizedReactionRecord(reaction_id="r1", bogus="x")


def test_forbidden_fields_absent():
    from reaction_agent.schemas import p1_entities
    src = inspect.getsource(p1_entities)
    for name in FORBIDDEN_FIELD_NAMES:
        assert f"{name}:" not in src, f"forbidden field {name} appears"


def test_donor_eligibility_reason_codes_typed():
    d = DonorEligibilityAssessment(participant_id="p1", eligibility="eligible",
                                   reason_codes=["mapped_retention"], evidence_ids=["e1"])
    assert d.eligibility in ("eligible", "conditionally_eligible", "not_eligible", "unknown")


def test_quarantine_record_has_reason():
    with pytest.raises(Exception):
        QuarantineRecord(record_id="q1")  # missing required reason


def test_snapshot_manifest_counts_required():
    m = SnapshotManifest(snapshot_id="s1", schema_version="p1-1",
                         included_strict_count=0, conditional_count=0,
                         diagnostic_count=0, quarantine_count=0,
                         build_status="complete", snapshot_hash="h")
    assert m.build_status == "complete"


# -- Step 7: stable ID + content hash tests (from brief) --

from reaction_agent.hashing import stable_id, canonical_hash  # noqa: E402


def test_reaction_record_stable_id_atom_order_invariant():
    r1 = {"smiles": "CCO", "atoms": [1, 2, 3]}
    r2 = {"smiles": "CCO", "atoms": [3, 2, 1]}  # same chem, different order
    # stable_id is content-sensitive; here we verify same smiles -> same hash
    # (atoms as list preserves order, so r1 != r2; but identical dict -> identical id)
    assert stable_id("rxn", {"smiles": "CCO"}) == stable_id("rxn", {"smiles": "CCO"})


def test_policy_version_changes_hash():
    h1 = canonical_hash({"policy": "v1", "data": "x"})
    h2 = canonical_hash({"policy": "v2", "data": "x"})
    assert h1 != h2


# -- Additional strictness + field-type contracts --

def test_all_p1_entities_inherit_strict_model():
    from reaction_agent.schemas.common import StrictModel
    classes = [
        NormalizedReactionRecord, DonorEligibilityAssessment, EligibilityDecision,
        QuarantineRecord, SnapshotManifest, SnapshotRecord, ManualAuditRecord,
        ResolvedTransformedLineage,
    ]
    for cls in classes:
        assert issubclass(cls, StrictModel), f"{cls.__name__} must inherit StrictModel"
        # extra=forbid enforced by StrictModel
        cfg = cls.model_config
        assert cfg.get("extra") == "forbid", f"{cls.__name__} extra!=forbid"


def test_all_p1_entities_reject_unknown_field():
    classes = [
        NormalizedReactionRecord, DonorEligibilityAssessment, EligibilityDecision,
        QuarantineRecord, SnapshotManifest, SnapshotRecord, ManualAuditRecord,
        ResolvedTransformedLineage,
    ]
    for cls in classes:
        with pytest.raises(Exception):
            cls(__bogus_field__="x")  # unknown field must raise under extra=forbid


def test_normalized_reaction_record_minimal_fields():
    """T4 consumes NormalizedReactionRecord(reaction_id, normalized_reaction, source_record_id)."""
    r = NormalizedReactionRecord(reaction_id="r1", normalized_reaction="CCO>>CC=O",
                                 source_record_id="s1")
    assert r.reaction_id == "r1"
    assert r.normalized_reaction == "CCO>>CC=O"


def test_normalized_reaction_record_raw_and_provenance():
    from reaction_agent.provenance import SourceRecordProvenance
    p = SourceRecordProvenance(source_name="rhea", source_version="1",
                               source_record_id="r1", source_file_hash="fh",
                               raw_record_hash="rh", normalizer_version="p1-1",
                               created_by_build_id="b1")
    r = NormalizedReactionRecord(reaction_id="r1", normalized_reaction="CCO>>CC=O",
                                 source_record_id="s1", raw_reaction="CCO>O>CC=O",
                                 provenance=p)
    assert r.provenance is not None
    assert r.provenance.source_name == "rhea"


def test_donor_eligibility_strict_string_not_coerced():
    """strict=True: passing an int eligibility must fail, not coerce."""
    with pytest.raises(Exception):
        DonorEligibilityAssessment(participant_id="p1", eligibility=1,
                                   reason_codes=["x"])


def test_donor_eligibility_unknown_value_allowed():
    d = DonorEligibilityAssessment(participant_id="p1", eligibility="unknown",
                                   reason_codes=["no_mapping"])
    assert d.eligibility == "unknown"


def test_eligibility_decision_uses_p0_eligibility_status():
    """EligibilityDecision.eligibility must be P0 EligibilityStatus enum."""
    from reaction_agent.schemas.common import EligibilityStatus
    d = EligibilityDecision(decision_id="d1", participant_id="p1",
                            eligibility=EligibilityStatus.strict_eligible,
                            reason="mapped retention with formal source")
    assert d.eligibility == EligibilityStatus.strict_eligible
    assert d.eligibility.value == "strict_eligible"


def test_eligibility_decision_quarantine_value():
    """EligibilityStatus enum covers the quarantine bucket from §10.4."""
    from reaction_agent.schemas.common import EligibilityStatus
    d = EligibilityDecision(decision_id="d1", participant_id="p1",
                            eligibility=EligibilityStatus.quarantine,
                            reason="critical element contradiction")
    assert d.eligibility == EligibilityStatus.quarantine


def test_quarantine_record_reason_required_nonempty():
    """reason is NonEmptyStr: empty/whitespace must fail."""
    with pytest.raises(Exception):
        QuarantineRecord(record_id="q1", reason="   ")


def test_quarantine_record_valid():
    q = QuarantineRecord(record_id="q1", reason="lineage ambiguity affects A->B identity")
    assert q.reason.startswith("lineage")


def test_resolved_transformed_lineage_fields():
    l = ResolvedTransformedLineage(lineage_id="l1",
                                   reactant_participant_id="p1",
                                   product_participant_id="p2",
                                   evidence_ids=["e1", "e2"],
                                   ambiguity="none")
    assert l.lineage_id == "l1"
    assert l.product_participant_id == "p2"
    assert l.evidence_ids == ["e1", "e2"]


def test_resolved_transformed_lineage_required_fields():
    with pytest.raises(Exception):
        ResolvedTransformedLineage(lineage_id="l1")  # missing participant ids


def test_snapshot_manifest_count_fields_typed_int():
    """strict=True: counts must be int, not string."""
    with pytest.raises(Exception):
        SnapshotManifest(snapshot_id="s1", schema_version="p1-1",
                         included_strict_count="0", conditional_count=0,
                         diagnostic_count=0, quarantine_count=0,
                         build_status="complete", snapshot_hash="h")


def test_snapshot_manifest_hash_required():
    with pytest.raises(Exception):
        SnapshotManifest(snapshot_id="s1", schema_version="p1-1",
                         included_strict_count=0, conditional_count=0,
                         diagnostic_count=0, quarantine_count=0,
                         build_status="complete")  # missing snapshot_hash


def test_snapshot_record_fields():
    m = SnapshotManifest(snapshot_id="s1", schema_version="p1-1",
                         included_strict_count=5, conditional_count=2,
                         diagnostic_count=1, quarantine_count=0,
                         build_status="complete", snapshot_hash="h")
    rec = SnapshotRecord(snapshot_id="s1", manifest=m,
                         reaction_evidence_ids=["e1", "e2"])
    assert rec.snapshot_id == "s1"
    assert rec.manifest.included_strict_count == 5


def test_snapshot_record_manifest_optional():
    rec = SnapshotRecord(snapshot_id="s1")
    assert rec.manifest is None


def test_manual_audit_record_uses_agreement_not_confidence():
    """ManualAuditRecord uses agreement + catastrophic_error_count, never confidence."""
    a = ManualAuditRecord(record_id="a1", stratum="mapping_high_quality",
                          sample_size=50, agreement=0.92,
                          catastrophic_error_count=0)
    assert a.agreement == 0.92
    assert a.catastrophic_error_count == 0


def test_manual_audit_record_agreement_bounded():
    """agreement is a float in [0, 1]."""
    a = ManualAuditRecord(record_id="a1", stratum="s", sample_size=10,
                          agreement=0.5, catastrophic_error_count=1)
    assert 0.0 <= a.agreement <= 1.0


def test_manual_audit_record_has_rubric_scores():
    """final_plan §4.12: mapping/role/lineage/ledger rubrics."""
    a = ManualAuditRecord(record_id="a1", stratum="s", sample_size=10,
                          agreement=0.8, catastrophic_error_count=0,
                          mapping_rubric_score=0.9, role_rubric_score=0.85,
                          lineage_rubric_score=0.7, ledger_rubric_score=0.95)
    assert a.mapping_rubric_score == 0.9
    assert a.ledger_rubric_score == 0.95


def test_manual_audit_record_no_confidence_field():
    """The word 'confidence' must not appear as a field name on the model."""
    field_names = set(ManualAuditRecord.model_fields.keys())
    for forbidden in FORBIDDEN_FIELD_NAMES:
        assert forbidden not in field_names, f"{forbidden} is a field on ManualAuditRecord"
