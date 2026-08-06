"""R3-I P3->P4 manifest completeness tests.

Round 2 defect: the manifest omitted nested records P4 actually consumes
(``CandidateEvidencePath``, ``GenerationReport``, ``CandidateValidation``,
``CandidateAnalogyLedger``).

Round 3 contract: the manifest is generated from the LIVE Pydantic models,
includes every P4-consumed model with fields / required fields / JSON schema
hashes / namespace contract / evidence-kind semantics / ID+hash preimage
contract, and declares the explicit nested-record contract (option 2:
nested records are content-addressedly bound to the parent namespace and
path hash).  Manifest tampering and live-schema drift must be detected.
"""
import pytest

from reaction_agent.hashing import canonical_hash
from reaction_agent.p3.manifest import (
    NESTED_RECORD_CONTRACT,
    build_interface_manifest,
    manifest_schema_hash,
    model_fields_of,
    model_required_fields_of,
    model_schema_hash,
)
from reaction_agent.p3.schemas import (
    CandidateEvidencePath,
    CandidateValidation,
    GenerationReport,
    KernelResult,
    StrictCandidate,
)
from reaction_agent.schemas.ledger import CandidateAnalogyLedger

P4_CONSUMED = [
    "KernelResult",
    "KernelRunManifest",
    "NormalizedQuery",
    "ResolvedDonorEvidence",
    "StrictTransformation",
    "ConditionedSite",
    "StrictCandidate",
    "CandidateTrace",
    "KernelFailure",
    "CapabilityStatus",
    # the nested records Round 2 omitted:
    "CandidateEvidencePath",
    "GenerationReport",
    "CandidateValidation",
    "CandidateAnalogyLedger",
]


def test_manifest_includes_every_p4_consumed_model():
    manifest = build_interface_manifest()
    for name in P4_CONSUMED:
        assert name in manifest["interfaces"], f"manifest missing {name}"


def test_manifest_fields_match_live_models():
    manifest = build_interface_manifest()
    live = {
        "CandidateEvidencePath": CandidateEvidencePath,
        "GenerationReport": GenerationReport,
        "CandidateValidation": CandidateValidation,
        "CandidateAnalogyLedger": CandidateAnalogyLedger,
        "KernelResult": KernelResult,
        "StrictCandidate": StrictCandidate,
    }
    for name, cls in live.items():
        assert manifest["interfaces"][name]["fields"] == model_fields_of(cls)


def test_manifest_schema_hashes_are_live():
    manifest = build_interface_manifest()
    for name, cls in (
        ("CandidateEvidencePath", CandidateEvidencePath),
        ("GenerationReport", GenerationReport),
        ("CandidateValidation", CandidateValidation),
        ("CandidateAnalogyLedger", CandidateAnalogyLedger),
    ):
        assert manifest["interfaces"][name]["schema_hash"] == model_schema_hash(cls)
        assert manifest["interfaces"][name]["schema_hash"] == canonical_hash(
            cls.model_json_schema()
        )


def test_required_fields_recorded():
    manifest = build_interface_manifest()
    path_required = manifest["interfaces"]["CandidateEvidencePath"]["required_fields"]
    for field in ("donor_id", "reaction_id", "lineage_id", "transformation_id",
                  "site_id", "generation_report", "source_ledger_id",
                  "candidate_analogy_ledger", "validation",
                  "path_id", "path_hash"):
        assert field in path_required, f"path missing required {field}"
    candidate_required = manifest["interfaces"]["StrictCandidate"]["required_fields"]
    assert "candidate_id" in candidate_required


def test_nested_record_contract_declared_option_2():
    manifest = build_interface_manifest()
    contract = manifest["nested_record_contract"]
    assert contract["mode"] == "parent_namespace_content_binding"
    assert "path_id" in contract["binding_fields"]
    assert "path_hash" in contract["binding_fields"]
    for key in ("run_id", "case_id", "query_id", "fold_id", "snapshot_id",
                "snapshot_hash"):
        assert key in contract["preimage_includes"]
    # nested models declare the binding, not a direct namespace
    manifest_nested = manifest["interfaces"]["CandidateEvidencePath"]
    assert manifest_nested["run_namespace_fields"] == []
    assert "path_hash" in manifest_nested["namespace_binding"]


def test_evidence_kind_and_namespace_contracts_present():
    manifest = build_interface_manifest()
    assert set(manifest["evidence_kind_semantics"]) == {
        "real", "synthetic_fixture", "blocked", "diagnostic",
    }
    assert manifest["run_namespace_required"] == [
        "run_id", "case_id", "query_id", "fold_id", "snapshot_id",
        "snapshot_hash",
    ]
    assert manifest["id_preimage_contract"]


def test_manifest_recomputable():
    m1 = build_interface_manifest()
    m2 = build_interface_manifest()
    assert manifest_schema_hash(m1) == manifest_schema_hash(m2)


def test_manifest_tampering_detected():
    manifest = build_interface_manifest()
    original = manifest_schema_hash(manifest)
    tampered = build_interface_manifest()
    tampered["interfaces"]["StrictCandidate"]["fields"] += ["bogus_field"]
    assert manifest_schema_hash(tampered) != original
    tampered2 = build_interface_manifest()
    tampered2["interfaces"]["GenerationReport"]["schema_hash"] = "forged"
    assert manifest_schema_hash(tampered2) != original


def test_live_schema_drift_changes_hash():
    manifest = build_interface_manifest()
    original = manifest_schema_hash(manifest)
    drifted = build_interface_manifest()
    drifted["interfaces"]["CandidateEvidencePath"]["required_fields"] = []
    assert manifest_schema_hash(drifted) != original
