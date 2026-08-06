"""P4-R1-A/B RED→GREEN: P3 consumer parses the frozen interface manifest and
verifies current-run artifacts; classification is a frozen enum with
cross-field invariants; caller-written capability can never become authority.

The frozen contract is P3=p3-p4-3 (``interfaces`` + string ``blocker_semantics``
+ ``evidence_kind_semantics``). An interface manifest alone NEVER grants
``capability_available``; only a verified current-run artifact (KernelResult)
that matches schema/hash/namespace/evidence-kind can.
"""
from __future__ import annotations

import json
import os

import pytest

from tests.fixtures.p4.p4_contract_fixture import (
    build_evidence_records,
    build_strict_candidate,
    build_query,
    POLICY_VERSION,
)

FROZEN_MANIFEST = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "fixtures", "p4", "p3_p4_interface_manifest_frozen.json")


def _frozen_manifest_dict() -> dict:
    with open(FROZEN_MANIFEST, encoding="utf-8") as f:
        d = json.load(f)
    # round-6 wrapper: {"manifest": {...}, "schema_hash": ...}
    return d.get("manifest", d)


# =====================================================================
# P4-R1-A — frozen manifest parsing
# =====================================================================

class TestFrozenManifestParsing:
    def test_parses_real_frozen_p3_p4_manifest(self):
        """The actual frozen p3-p4-3 manifest parses and reports its fields."""
        from reaction_agent.adapters.p3_consumer import P3InterfaceConsumer
        consumer = P3InterfaceConsumer(missing_path=FROZEN_MANIFEST)
        state = consumer.load()
        assert state.present is True
        assert state.manifest_version == "p3-p4-3"
        assert state.hash_algo == "sha256 (reaction_agent.hashing.canonical_hash)"
        assert isinstance(state.blocker_semantics, str)
        assert "KernelResult" in state.interfaces
        assert "StrictCandidate" in state.interfaces
        assert "CAPABILITY_UNAVAILABLE" in state.blocker_semantics
        assert state.evidence_kind_semantics["real"] == "real evidence"

    def test_manifest_version_must_be_frozen_supported(self):
        """Unknown manifest_version is rejected, not silently accepted."""
        from reaction_agent.adapters.p3_consumer import P3InterfaceConsumer
        d = dict(_frozen_manifest_dict())
        d["manifest_version"] = "p3-p4-99"
        path = _write_tmp(d)
        state = P3InterfaceConsumer(missing_path=path).load()
        assert state.present is False
        assert state.classification == "blocked"
        assert any("version" in r for r in state.blocked_reasons)

    def test_blocker_semantics_must_be_string(self):
        """blocker_semantics is a string in the frozen contract; dict is rejected."""
        from reaction_agent.adapters.p3_consumer import P3InterfaceConsumer
        d = dict(_frozen_manifest_dict())
        d["blocker_semantics"] = {"no_chemistry_backend": "typed_blocker"}
        path = _write_tmp(d)
        state = P3InterfaceConsumer(missing_path=path).load()
        assert state.present is False
        assert state.classification == "blocked"

    def test_malformed_json_is_typed_blocked_not_bare_exception(self):
        from reaction_agent.adapters.p3_consumer import P3InterfaceConsumer
        path = _write_tmp("{not json")
        state = P3InterfaceConsumer(missing_path=path).load()
        assert state.present is False
        assert state.classification == "blocked"
        assert state.blocked_reasons

    def test_missing_interfaces_rejected(self):
        from reaction_agent.adapters.p3_consumer import P3InterfaceConsumer
        d = dict(_frozen_manifest_dict())
        del d["interfaces"]
        path = _write_tmp(d)
        state = P3InterfaceConsumer(missing_path=path).load()
        assert state.present is False
        assert state.classification == "blocked"

    def test_interface_manifest_alone_never_grants_capability(self):
        """Interface manifest present + no current-run artifact => BLOCKED.

        The interface manifest proves the schema exists; it does NOT prove any
        run produced candidates. capability_available must stay False.
        """
        from reaction_agent.adapters.p3_consumer import P3InterfaceConsumer
        consumer = P3InterfaceConsumer(
            missing_path=FROZEN_MANIFEST,
            current_run_path="/nonexistent/current_run_artifact.json")
        state = consumer.load()
        assert state.present is True
        assert state.capability_available is False
        assert state.classification == "blocked"
        assert any("current_run" in r for r in state.blocked_reasons)


# =====================================================================
# P4-R1-A — current-run artifact verification
# =====================================================================

def _current_run_artifact(namespace: dict | None = None) -> dict:
    """A schema-correct KernelResult current-run artifact over the fixture."""
    ns = namespace or {
        "run_id": "run_abc", "case_id": "case_1", "query_id": "q_1",
        "fold_id": "fold_1", "snapshot_id": "snap_c589494081df",
        "snapshot_hash": "deadbeef" * 4,
    }
    cand = build_strict_candidate()
    return {
        "run_id": ns["run_id"], "status": "completed",
        "query_id": ns["query_id"], "case_id": ns["case_id"],
        "fold_id": ns["fold_id"], "snapshot_id": ns["snapshot_id"],
        "snapshot_hash": ns["snapshot_hash"],
        "manifest": {
            "run_id": ns["run_id"], "request": {"query_smiles": "CCO"},
            "request_hash": "req_hash", "query_id": ns["query_id"],
            "case_id": ns["case_id"], "fold_id": ns["fold_id"],
            "snapshot_id": ns["snapshot_id"], "snapshot_hash": ns["snapshot_hash"],
            "config": {}, "component_versions": {}, "seed": 0,
            "kernel_version": "p3-1", "schema_version": "p3-1",
            "manifest_hash": "manifest_hash",
        },
        "normalized_query": {
            "query_id": ns["query_id"], "run_id": ns["run_id"],
            "case_id": ns["case_id"], "fold_id": ns["fold_id"],
            "snapshot_id": ns["snapshot_id"], "snapshot_hash": ns["snapshot_hash"],
            "input_smiles": "CCO", "canonical_smiles": "CCO",
            "identity_hash": "id_hash", "heavy_atom_count": 3,
            "formal_charge": 0, "fragment_count": 1,
            "normalization_policy": "p1-1", "evidence_kind": "synthetic_fixture",
        },
        "capability_status": {
            "run_id": ns["run_id"], "query_id": ns["query_id"],
            "fold_id": ns["fold_id"], "case_id": ns["case_id"],
            "snapshot_id": ns["snapshot_id"], "snapshot_hash": ns["snapshot_hash"],
            "components": [], "chemistry_backend_available": False,
            "explicit_map_validator_available": False,
            "strict_atom_mapper_available": False,
            "mcs_diagnostic_available": False,
            "real_snapshot_available": False,
            "automatic_donor_available": False,
        },
        "candidates": [{
            "candidate_id": cand.candidate_id,
            "run_id": ns["run_id"], "case_id": ns["case_id"],
            "query_id": ns["query_id"], "fold_id": ns["fold_id"],
            "snapshot_id": ns["snapshot_id"], "snapshot_hash": ns["snapshot_hash"],
            "canonical_product_identity": cand.canonical_product,
            "lane": "strict", "origin": cand.origin,
            "generation_paths": cand.generation_paths,
            "support_lineage_ids": cand.support_lineage_ids,
            "transformation_ids": cand.transformation_ids,
            "site_ids": cand.site_ids,
            "validation": cand.validation,
            "source_ledger_ids": cand.source_ledger_ids,
            "candidate_analogy_ledger": cand.candidate_analogy_ledger_id,
            "candidate_evidence_paths": [],
            "provenance": cand.provenance,
            "evidence_kind": "synthetic_fixture",
        }],
        "trace": {
            "run_id": ns["run_id"], "query_id": ns["query_id"],
            "case_id": ns["case_id"], "fold_id": ns["fold_id"],
            "snapshot_id": ns["snapshot_id"], "snapshot_hash": ns["snapshot_hash"],
            "stages": [], "donor_ids": [], "transformation_ids": [],
            "site_ids": [], "generation_ids": [], "candidate_ids": [],
            "source_ledger_ids": [], "evidence_kind": "synthetic_fixture",
        },
        "failures": [],
        "evidence_kind": "synthetic_fixture",
    }


def _write_tmp(data, suffix=".json"):
    import tempfile
    fd, path = tempfile.mkstemp(suffix=suffix)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(data, f)
    return path


class TestCurrentRunArtifact:
    def test_verified_current_run_grants_capability_and_candidates(self):
        """A schema-correct current-run artifact with matching namespace unlocks
        capability_available and exposes the verified candidates."""
        from reaction_agent.adapters.p3_consumer import P3InterfaceConsumer
        from reaction_agent.schemas.p4.authority import P4Classification
        artifact = _write_tmp(_current_run_artifact())
        consumer = P3InterfaceConsumer(
            missing_path=FROZEN_MANIFEST, current_run_path=artifact)
        state = consumer.load()
        assert state.capability_available is True
        assert state.classification == P4Classification.synthetic_fixture
        assert state.candidate_ids == ["cand_ox_001"]
        run = consumer.load_current_run()
        assert run is not None
        assert run.namespace.run_id == "run_abc"
        assert run.candidates[0]["candidate_id"] == "cand_ox_001"

    def test_current_run_missing_namespace_field_rejected(self):
        """Malformed current-run artifact (missing capability_status) => typed
        BLOCKED, never a bare exception."""
        from reaction_agent.adapters.p3_consumer import P3InterfaceConsumer
        artifact = _current_run_artifact()
        del artifact["capability_status"]
        path = _write_tmp(artifact)
        consumer = P3InterfaceConsumer(
            missing_path=FROZEN_MANIFEST, current_run_path=path)
        state = consumer.load()
        assert state.present is True
        assert state.capability_available is False
        assert state.classification == "blocked"

    def test_current_run_snapshot_hash_mismatch_rejected(self):
        """The current-run artifact's snapshot_hash must match the run's own
        namespace; a mismatch is rejected (cross-snapshot smuggling)."""
        from reaction_agent.adapters.p3_consumer import P3InterfaceConsumer
        artifact = _current_run_artifact()
        # The artifact header claims a snapshot hash different from the one
        # its nested manifest/normalized-query records carry.
        artifact["snapshot_hash"] = "cafebabe" * 4
        path = _write_tmp(artifact)
        consumer = P3InterfaceConsumer(
            missing_path=FROZEN_MANIFEST, current_run_path=path)
        state = consumer.load()
        assert state.capability_available is False
        assert state.classification.value == "blocked"

    def test_current_run_evidence_kind_must_be_frozen(self):
        """evidence_kind outside the frozen enum is rejected."""
        from reaction_agent.adapters.p3_consumer import P3InterfaceConsumer
        artifact = _current_run_artifact()
        artifact["evidence_kind"] = "real_evidence_from_somewhere"
        path = _write_tmp(artifact)
        consumer = P3InterfaceConsumer(
            missing_path=FROZEN_MANIFEST, current_run_path=path)
        state = consumer.load()
        assert state.capability_available is False
        assert state.classification == "blocked"


# =====================================================================
# P4-R1-B — classification enum + cross-field invariants + typed authority
# =====================================================================

class TestClassificationAuthority:
    def test_classification_is_frozen_enum(self):
        """classification is a frozen enum, not a free string."""
        from reaction_agent.schemas.p4.decision import P4Classification
        assert {c.value for c in P4Classification} == {
            "real", "synthetic_fixture", "blocked", "diagnostic"}

    def test_real_requires_full_authority_cross_fields(self):
        """classification=real is impossible without verified P3 current-run
        artifact + real evidence + correct namespace + P2 authority."""
        from reaction_agent.schemas.p4.authority import P4Classification
        from reaction_agent.schemas.p4.decision import P4CapabilityStatus
        with pytest.raises(Exception):
            P4CapabilityStatus(
                capability_available=True,
                p3_interface_manifest_present=False,
                real_evidence_available=False,
                p2_truth_authority_available=False,
                classification=P4Classification.real,  # must be rejected
                blocked_reasons=[])

    def test_synthetic_cannot_relabel_real(self):
        """A synthetic-fixture authority cannot carry classification=real."""
        from reaction_agent.schemas.p4.authority import P4Classification
        from reaction_agent.schemas.p4.decision import P4CapabilityStatus
        with pytest.raises(Exception):
            P4CapabilityStatus(
                capability_available=True,
                p3_interface_manifest_present=True,
                real_evidence_available=False,
                p2_truth_authority_available=False,
                classification=P4Classification.real,
                blocked_reasons=[])

    def test_blocked_authority_cannot_run_completed_pipeline(self):
        """A blocked authority has capability_available=False."""
        from reaction_agent.schemas.p4.authority import P4Classification
        from reaction_agent.schemas.p4.decision import P4CapabilityStatus
        cap = P4CapabilityStatus(
            capability_available=False,
            p3_interface_manifest_present=False,
            real_evidence_available=False,
            p2_truth_authority_available=False,
            classification=P4Classification.blocked,
            blocked_reasons=["p3_interface_manifest_missing"])
        assert cap.capability_available is False

    def test_caller_written_capability_cannot_be_authority(self):
        """The pipeline must not accept a caller-written P4CapabilityStatus as
        authority; it needs a typed P3AuthorityHandle produced by the consumer."""
        from reaction_agent.adapters.p3_consumer import P3InterfaceConsumer
        from reaction_agent.inference.predictor import run_p4_pipeline
        from reaction_agent.schemas.p4.authority import P4Classification
        from reaction_agent.schemas.p4.decision import P4CapabilityStatus
        # A caller fabricates a capability claiming to be synthetic (valid
        # struct) — but it is NOT a P3AuthorityHandle, so the pipeline must
        # refuse it (TypeError = wrong argument type).
        fabricated = P4CapabilityStatus(
            capability_available=True,
            p3_interface_manifest_present=True,
            real_evidence_available=False,
            p2_truth_authority_available=False,
            classification=P4Classification.synthetic_fixture,
            blocked_reasons=[])
        with pytest.raises(TypeError):
            run_p4_pipeline(
                query=build_query(),
                evidence_records=build_evidence_records(),
                candidates=[build_strict_candidate()],
                structural_contexts={},
                capability=fabricated,  # not a P3AuthorityHandle
                top_k=3,
            )

    def test_consumer_produces_typed_authority_handle(self):
        """P3InterfaceConsumer.resolve_authority returns a P3AuthorityHandle
        whose source/evidence-kind are bound to the verified artifact."""
        from reaction_agent.adapters.p3_consumer import P3InterfaceConsumer
        from reaction_agent.schemas.p4.authority import (
            P3AuthorityHandle, AuthoritySource, P4Classification)
        artifact = _write_tmp(_current_run_artifact())
        consumer = P3InterfaceConsumer(
            missing_path=FROZEN_MANIFEST, current_run_path=artifact)
        handle = consumer.resolve_authority()
        assert isinstance(handle, P3AuthorityHandle)
        assert handle.source == AuthoritySource.p3_current_run
        assert handle.evidence_kind == P4Classification.synthetic_fixture
        assert handle.namespace.run_id == "run_abc"

    def test_blocked_authority_handle_when_no_current_run(self):
        """Without a current-run artifact the authority handle is blocked and
        cannot unlock a completed pipeline."""
        from reaction_agent.adapters.p3_consumer import P3InterfaceConsumer
        from reaction_agent.schemas.p4.authority import AuthoritySource
        consumer = P3InterfaceConsumer(
            missing_path=FROZEN_MANIFEST,
            current_run_path="/nonexistent/current_run_artifact.json")
        handle = consumer.resolve_authority()
        assert handle.source == AuthoritySource.blocked
        assert handle.blocked_reasons