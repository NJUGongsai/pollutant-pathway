"""P3 anti-false-positive mutation tests (CHATGPT_P3 prompt §7, R2).

Each mutation violates a strict invariant; the kernel / loader / schema /
Gate must FAIL CLOSED with a TYPED failure (no `pytest.raises(Exception)`).
Mutations never weaken the production code — they run against mutated copies
of fixtures/data in the test.
"""
import pytest
from pydantic import ValidationError

from reaction_agent.p3.fixtures import (
    DonorEntry,
    FixtureReaction,
    ReactionRef,
    TrainView,
    build_train_view,
    find_donor_ref,
    load_fixture_reactions,
)
from reaction_agent.p3.load import (
    FoldIsolationError,
    IncompleteReactionError,
    load_reaction_evidence,
)
from reaction_agent.p3.kernel import run_kernel
from reaction_agent.p3.schemas import (
    CandidateValidation,
    EvidenceKind,
    KernelFailure,
    KernelResult,
    KernelStatus,
    SiteEligibility,
)
from reaction_agent.p3.transform import TransformExtractionError, extract_transform


def _base_train_view():
    return build_train_view(load_fixture_reactions())


def _oct_ref(train_view):
    return find_donor_ref(train_view, "fx_oct")


# -- 1. Only A/B (cofactors stripped) --------------------------------------


def test_mutation_only_ab_rejected():
    # R5-C: a fully-synchronized A/B-only STRIPPED reaction (every
    # representation stripped, hashes recomputed so the caller view is
    # self-consistent) must be rejected by the FROZEN authority root via the
    # real loader path — typed FROZEN_REACTION_HASH_MISMATCH, never a
    # shallow hash failure.
    from reaction_agent.p3.mutations_round3 import case_ab_only_mutated
    status, code, artifact = case_ab_only_mutated()
    assert status == "FAIL"
    assert code == "FROZEN_REACTION_HASH_MISMATCH"
    assert artifact == {"rejected": "ab_only_stripped"}


def test_ab_only_baseline_complete_reaction_loads():
    from reaction_agent.p3.mutations_round3 import case_ab_only_baseline
    status, code, artifact = case_ab_only_baseline()
    assert status == "PASS", (status, code, artifact)
    assert artifact["participants"] == 4


# -- 2. Deleted participants ------------------------------------------------


def test_mutation_deleted_participant_rejected():
    tv = _base_train_view()
    donor, ref = _oct_ref(tv)
    fixture = tv.reactions["rxn_oct"]
    mutated_evidence = fixture.evidence.model_copy(update={
        "participants": fixture.evidence.participants[:1],  # drop the product
    })
    mutated = _replace(fixture, evidence=mutated_evidence)
    mutated_tv = _mutate_tv(tv, "rxn_oct", mutated)
    with pytest.raises(IncompleteReactionError):
        load_reaction_evidence(mutated_tv, donor.donor_id, ref)


# -- 3. Changed mapping (partial) -------------------------------------------


def test_mutation_partial_mapping_excluded():
    from reaction_agent.p3.fixtures import build_fixture_reaction
    fx = build_fixture_reaction(
        name="partial_map",
        reactant_smiles=["[CH3:1][CH2:2][OH:3]"],
        product_smiles=["[CH3:1][CH:2]=O"],  # product O unmapped -> partial
    )
    assert fx.mapping_report.mapping_status.value != "fully_mapped"
    tv = build_train_view({"rxn_partial_map": fx})
    present = any(
        any(r.reaction_id == "fx_partial_map" for r in d.reaction_refs)
        for d in tv.donors
    )
    assert not present, "partial-map donor must be excluded from the train view"


# -- 4. Missing lineage -----------------------------------------------------


def test_mutation_missing_lineage_rejected():
    tv = _base_train_view()
    donor, ref = _oct_ref(tv)
    fixture = tv.reactions["rxn_oct"]
    evidence = fixture.evidence.model_copy(update={
        "resolved_transformed_lineages": [],
    })
    mutated = _replace(fixture, evidence=evidence, lineages=[])
    mutated_tv = _mutate_tv(tv, "rxn_oct", mutated)
    with pytest.raises(IncompleteReactionError):
        load_reaction_evidence(mutated_tv, donor.donor_id, ref)


# -- 5. Skipped preconditions produce NO false candidate --------------------


def test_mutation_skipped_preconditions_not_false_positive(oct_transform):
    # The REAL transform carries strict preconditions.  A secondary alcohol
    # must NOT yield an eligible site or a candidate.
    from reaction_agent.p3.normalize import normalize_query
    from reaction_agent.p3.sites import enumerate_sites
    query = normalize_query("CC(C)O")
    sites = enumerate_sites(oct_transform, query)
    assert all(s.eligibility is not SiteEligibility.eligible for s in sites)


# -- 6. Forged ledger rejected ----------------------------------------------


def test_mutation_forged_candidate_ledger_rejected():
    from reaction_agent.schemas.ledger import CandidateAnalogyLedger
    from reaction_agent.schemas.ledger import LedgerReferenceRegistry
    from reaction_agent.schemas.errors import UnknownReferenceError
    forged = CandidateAnalogyLedger(
        ledger_id="cal_forged", source_ledger_id="srl_missing", candidate_id="cand_x",
    )
    registry = LedgerReferenceRegistry(
        source_ledger_ids=frozenset(["srl_real"]),
        candidate_ids=frozenset(["cand_real"]),
    )
    from reaction_agent.schemas.ledger import validate_candidate_ledger_references
    with pytest.raises(UnknownReferenceError):
        validate_candidate_ledger_references(forged, registry)


# -- 7. Fold pollution rejected (R2-B) --------------------------------------


def test_mutation_test_view_pollution_rejected():
    # A train view whose donors belong to a different fold must be rejected
    # by the fold authority (typed FoldIsolationError), not silently loaded.
    tv = _base_train_view()
    polluted = TrainView(
        fold_id="fold_test",  # wrong fold
        snapshot_id=tv.snapshot_id, snapshot_hash=tv.snapshot_hash,
        donors=tv.donors, reactions=tv.reactions,
    )
    donor, ref = _oct_ref(tv)
    with pytest.raises(FoldIsolationError):
        load_reaction_evidence(polluted, donor.donor_id, ref)


# -- 8. Relaxed edit must not enter strict ----------------------------------


def test_mutation_relaxed_edit_rejected_in_strict():
    from reaction_agent.schemas.ledger import CandidateAnalogyLedger
    from reaction_agent.p3.schemas import StrictCandidate
    with pytest.raises(ValidationError):
        StrictCandidate(
            candidate_id="cand_relaxed", canonical_product_identity="CCC=O",
            lane="strict", origin="deterministic_kernel", generation_paths=[],
            support_lineage_ids=[], transformation_ids=[], site_ids=[],
            validation=CandidateValidation(
                valid_molecule=True, transform_fidelity=True,
                precondition_recheck=True, formal_source_accounting=True,
                candidate_ledger_valid=True, relaxation_used=True,  # forbidden
            ),
            source_ledger_ids=[],
            candidate_analogy_ledger=CandidateAnalogyLedger(
                ledger_id="cal", source_ledger_id="srl", candidate_id="cand_relaxed",
            ),
            provenance=[],
        )


# -- 9. System failure NOT reported as scientific abstention ----------------


def test_mutation_system_failure_as_abstention_rejected():
    from reaction_agent.p3.schemas import CandidateTrace
    trace = CandidateTrace(
        run_id="r", query_id="q", case_id="c", fold_id="f",
        stages=[], evidence_kind=EvidenceKind.blocked,
    )
    with pytest.raises(ValidationError):
        KernelResult(
            run_id="r", status=KernelStatus.failed, query_id="q",
            case_id="c", fold_id="f", manifest=None,
            normalized_query=None, capability_status=None, candidates=[],
            trace=trace,
            failures=[KernelFailure(
                failure_code="NO_COMPATIBLE_SITE", category="scientific",
                reason="fake abstention", component="decide",
            )],
        )


# -- helpers ----------------------------------------------------------------


def _replace(fixture, **updates):
    from dataclasses import replace
    return replace(fixture, **updates)


def _mutate_tv(tv, name, fixture):
    reactions = dict(tv.reactions)
    reactions[name] = fixture
    return TrainView(
        fold_id=tv.fold_id, snapshot_id=tv.snapshot_id,
        snapshot_hash=tv.snapshot_hash, donors=tv.donors,
        reactions=reactions,
        authority_manifest=tv.authority_manifest,
    )


# -- 10. Forged PASS status not trusted (Gate derives from artifacts) --------


def test_mutation_forged_pass_status_not_trusted():
    from reaction_agent.p3.gate import evaluate_gate_from_artifacts
    forged = {"status": "PASS", "items": {f"G{i:02d}": "PASS" for i in range(1, 11)}}
    assert evaluate_gate_from_artifacts(forged) != "PASS"
