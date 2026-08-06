"""P3 schema strictness: unknown fields, type coercion, cross-field invariants."""
import pytest

from reaction_agent.p3.schemas import (
    CandidateTrace,
    ConditionedSite,
    EvidenceKind,
    KernelFailure,
    KernelResult,
    KernelRunManifest,
    KernelStage,
    KernelStatus,
    NormalizedQuery,
    StrictCandidate,
    StrictTransformation,
)


def test_unknown_field_rejected():
    with pytest.raises(Exception):
        NormalizedQuery(
            query_id="q", input_smiles="CCO", canonical_smiles="CCO",
            identity_hash="h", heavy_atom_count=3, formal_charge=0,
            fragment_count=1, normalization_policy={"version": "p3-1"},
            bogus_field="x",
        )


def test_no_type_coercion():
    # strict=True: string "3" is not int 3
    with pytest.raises(Exception):
        NormalizedQuery(
            query_id="q", input_smiles="CCO", canonical_smiles="CCO",
            identity_hash="h", heavy_atom_count="3", formal_charge=0,
            fragment_count=1, normalization_policy={"version": "p3-1"},
        )


def test_evidence_kind_enum_not_string():
    with pytest.raises(Exception):
        NormalizedQuery(
            query_id="q", input_smiles="CCO", canonical_smiles="CCO",
            identity_hash="h", heavy_atom_count=3, formal_charge=0,
            fragment_count=1, normalization_policy={"version": "p3-1"},
            evidence_kind="synthetic_fixture",  # string, not enum
        )


def test_completed_result_rejects_system_failure():
    trace = CandidateTrace(
        run_id="r", query_id="q", case_id="c", fold_id="f",
        stages=[], evidence_kind=EvidenceKind.synthetic_fixture,
    )
    with pytest.raises(Exception):
        KernelResult(
            run_id="r", status=KernelStatus.completed, query_id="q",
            case_id="c", fold_id="f", manifest=_manifest(), normalized_query=_query(),
            capability_status=_capability(), candidates=[], trace=trace,
            failures=[KernelFailure(
                failure_code="SNAPSHOT_UNAVAILABLE", category="system",
                reason="x",
            )],
        )


def test_failed_result_requires_system_failure():
    trace = CandidateTrace(
        run_id="r", query_id="q", case_id="c", fold_id="f",
        stages=[], evidence_kind=EvidenceKind.synthetic_fixture,
    )
    with pytest.raises(Exception):
        KernelResult(
            run_id="r", status=KernelStatus.failed, query_id="q",
            case_id="c", fold_id="f", manifest=_manifest(), normalized_query=_query(),
            capability_status=_capability(), candidates=[], trace=trace,
            failures=[KernelFailure(
                failure_code="NO_COMPATIBLE_SITE", category="scientific",
                reason="x",
            )],
        )


def test_blocked_result_requires_system_failure():
    trace = CandidateTrace(
        run_id="r", query_id="q", case_id="c", fold_id="f",
        stages=[], evidence_kind=EvidenceKind.blocked,
    )
    with pytest.raises(Exception):
        KernelResult(
            run_id="r", status=KernelStatus.blocked, query_id="q",
            case_id="c", fold_id="f", manifest=_manifest(), normalized_query=_query(),
            capability_status=_capability(), candidates=[], trace=trace,
            failures=[],
        )


def test_trace_stage_transition_violation():
    with pytest.raises(Exception):
        CandidateTrace(
            run_id="r", query_id="q", case_id="c", fold_id="f",
            stages=[
                _stage(KernelStage.CANDIDATES_VALIDATED),
                _stage(KernelStage.RECEIVED),
            ],
            evidence_kind=EvidenceKind.synthetic_fixture,
        )


def test_transform_edit_reference_consistency():
    from reaction_agent.p3.schemas import BondChange
    with pytest.raises(Exception):
        StrictTransformation(
            transformation_id="tr", source_lineage_ids=["l"],
            donor_reaction_id="rxn", mapped_atom_edits=[1, 2],
            bond_changes=[BondChange(atom_map_a=1, atom_map_b=9, operation="delete")],
            donor_site_atom_map_numbers=[1, 2],
            donor_site_smiles="CC", donor_site_pattern="[#6]",
            canonical_transform_hash="h",
        )


def test_candidate_failing_validation_rejected():
    from reaction_agent.p3.schemas import CandidateValidation
    from reaction_agent.schemas.ledger import CandidateAnalogyLedger
    with pytest.raises(Exception):
        StrictCandidate(
            candidate_id="cand", canonical_product_identity="C=O",
            lane="strict", origin="deterministic_kernel",
            generation_paths=[],
            support_lineage_ids=[], transformation_ids=[], site_ids=[],
            validation=CandidateValidation(
                valid_molecule=False, transform_fidelity=False,
                precondition_recheck=False, formal_source_accounting=False,
                candidate_ledger_valid=False,
            ),
            source_ledger_ids=[], candidate_analogy_ledger=CandidateAnalogyLedger(
                ledger_id="cal", source_ledger_id="srl", candidate_id="cand",
            ),
            provenance=[],
        )


# -- helpers ---------------------------------------------------------------


def _manifest() -> KernelRunManifest:
    return KernelRunManifest(
        run_id="r", request="q", request_hash="h", query_id="q",
        case_id="c", fold_id="f",
    )


def _query() -> NormalizedQuery:
    return NormalizedQuery(
        query_id="q", input_smiles="CCO", canonical_smiles="CCO",
        identity_hash="h", heavy_atom_count=3, formal_charge=0,
        fragment_count=1, normalization_policy={"version": "p3-1"},
    )


def _capability():
    from reaction_agent.p3.schemas import CapabilityStatus
    return CapabilityStatus(
        run_id="r", query_id="q", fold_id="f", case_id="c",
    )


def _stage(stage: KernelStage):
    from reaction_agent.p3.schemas import StageTraceEntry
    return StageTraceEntry(stage=stage)
