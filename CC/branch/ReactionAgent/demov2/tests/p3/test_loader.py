"""P3-T3 complete reaction loader tests (final_plan §6.4, R2-B/R2-C)."""
import pytest

from reaction_agent.p3.load import (
    FoldIsolationError,
    IncompleteReactionError,
    load_reaction_evidence,
)
from reaction_agent.p3.fixtures import (
    DonorEntry,
    ReactionRef,
    TrainView,
    build_train_view,
    find_donor_ref,
    load_fixture_reactions,
)


def _load(train_view, reaction_id, query_id="q", case_id="c"):
    donor, ref = find_donor_ref(train_view, reaction_id)
    return load_reaction_evidence(
        train_view, donor.donor_id, ref, query_id=query_id, case_id=case_id
    )


def test_complete_reaction_loaded(train_view):
    dev = _load(train_view, "fx_oct")
    ctx = dev.context
    assert ctx.donor_participant_id
    assert ctx.reaction_evidence.reaction_id == "fx_oct"
    assert ctx.mapping_report.mapping_status.value == "fully_mapped"
    assert ctx.resolved_lineages
    assert ctx.source_ledger.ledger_id
    assert ctx.eligibility_decision.eligibility.value in (
        "strict_eligible", "conditional_eligible",
    )
    assert dev.evidence_kind.value == "synthetic_fixture"


def test_cofactor_participants_preserved(train_view):
    # Hydrolysis has H2O as a co-substrate participant; it must be preserved.
    dev = _load(train_view, "fx_hydrolysis")
    participant_ids = [p.participant_id for p in dev.context.reaction_evidence.participants]
    assert any("reactant_1" in pid for pid in participant_ids)  # H2O kept


def test_incomplete_ab_only_rejected(train_view):
    # A train view with a stripped "A>>B only" record must fail closed (fold
    # authority hash mismatch OR missing reaction -> typed rejection).
    stripped = TrainView(
        fold_id=train_view.fold_id,
        snapshot_id=train_view.snapshot_id,
        snapshot_hash="tampered_hash",
        donors=[
            DonorEntry(
                donor_id="donor_x", molecule_id="A",
                canonical_smiles="CCCCCCCCO", structural_smiles="CCCCCCCCO",
                donor_eligibility="eligible", source_quality="x",
                fold_id=train_view.fold_id,
                reaction_refs=[ReactionRef(
                    reaction_id="fx_oct", donor_participant_id="fx_oct_reactant_0",
                    lineage_id="l", reaction_hash="h",
                )],
            )
        ],
        reactions={},
    )
    with pytest.raises(FoldIsolationError):
        _load(stripped, "fx_oct")


def test_unknown_donor_rejected(train_view):
    with pytest.raises(FoldIsolationError):
        load_reaction_evidence(
            train_view, "donor_missing", _any_ref(train_view, "fx_oct")
        )


def test_unknown_reaction_ref_rejected(train_view):
    donor, ref = find_donor_ref(train_view, "fx_oct")
    from reaction_agent.p3.fixtures import ReactionRef as FRef
    bad_ref = FRef(
        reaction_id="fx_nonexistent", donor_participant_id=ref.donor_participant_id,
        lineage_id=ref.lineage_id, reaction_hash="h",
    )
    with pytest.raises(IncompleteReactionError):
        load_reaction_evidence(train_view, donor.donor_id, bad_ref)


def test_loaded_snapshot_identity_consistent(train_view):
    dev = _load(train_view, "fx_oct")
    assert dev.snapshot_id == train_view.snapshot_id
    assert dev.snapshot_hash == train_view.snapshot_hash


def _any_ref(train_view, reaction_id):
    donor, ref = find_donor_ref(train_view, reaction_id)
    return ref


# -- R2-C cross-consistency ------------------------------------------------


def test_reaction_evidence_participant_deleted_rejected(train_view):
    donor, ref = find_donor_ref(train_view, "fx_oct")
    fixture = train_view.reactions["rxn_oct"]
    # Drop a participant from the evidence -> loader must reject.
    mutated_evidence = fixture.evidence.model_copy(update={
        "participants": fixture.evidence.participants[:1],
    })
    mutated_fixture = _mutate_fixture(fixture, evidence=mutated_evidence)
    mutated_tv = _mutate_train_view(train_view, "rxn_oct", mutated_fixture)
    with pytest.raises(IncompleteReactionError):
        load_reaction_evidence(mutated_tv, donor.donor_id, ref)


def test_participant_multiset_mismatch_rejected(train_view):
    donor, ref = find_donor_ref(train_view, "fx_oct")
    fixture = train_view.reactions["rxn_oct"]
    mutated_evidence = fixture.evidence.model_copy(update={
        "participants": fixture.evidence.participants + [fixture.evidence.participants[0]],
    })
    mutated_fixture = _mutate_fixture(fixture, evidence=mutated_evidence)
    mutated_tv = _mutate_train_view(train_view, "rxn_oct", mutated_fixture)
    with pytest.raises(IncompleteReactionError):
        load_reaction_evidence(mutated_tv, donor.donor_id, ref)


def test_participant_side_mismatch_rejected(train_view):
    donor, ref = find_donor_ref(train_view, "fx_oct")
    fixture = train_view.reactions["rxn_oct"]
    bad = fixture.participants[0].model_copy(update={"side": "bogus_side"})
    mutated_fixture = _mutate_fixture(fixture, participants=[bad] + fixture.participants[1:])
    mutated_tv = _mutate_train_view(train_view, "rxn_oct", mutated_fixture)
    with pytest.raises(IncompleteReactionError):
        load_reaction_evidence(mutated_tv, donor.donor_id, ref)


def test_cofactor_and_cosubstrate_multiset_preserved(train_view):
    dev = _load(train_view, "fx_hydrolysis")
    # Both ester reactant (fragment 0) and H2O co-substrate (fragment 1)
    # must be present.
    ids = [p.participant_id for p in dev.context.reaction_evidence.participants]
    assert any("reactant_0" in i for i in ids)
    assert any("reactant_1" in i for i in ids)
    assert any("product_0" in i for i in ids)
    assert any("product_1" in i for i in ids)


def test_unresolved_conditional_eligibility_rejected():
    from reaction_agent.p3.fixtures import build_fixture_reaction
    # A reaction that is not production-eligible must be excluded from the
    # train view (fail closed).
    fx = build_fixture_reaction(
        name="quarantine",
        reactant_smiles=["[CH3:1][CH2:2][OH:3]"],
        product_smiles=["[CH3:1][CH:2]=O"],
    )
    tv = build_train_view({"rxn_quarantine": fx})
    present = any(
        any(r.reaction_id == "fx_quarantine" for r in d.reaction_refs)
        for d in tv.donors
    )
    assert not present, "non-eligible fixture must be excluded from train view"


def _mutate_fixture(fixture, **updates):
    from dataclasses import replace
    return replace(fixture, **updates)


def _mutate_train_view(train_view, name, fixture):
    reactions = dict(train_view.reactions)
    reactions[name] = fixture
    return TrainView(
        fold_id=train_view.fold_id, snapshot_id=train_view.snapshot_id,
        snapshot_hash=train_view.snapshot_hash, donors=train_view.donors,
        reactions=reactions,
        authority_manifest=train_view.authority_manifest,
    )


# -- R2-B fold authority -----------------------------------------------------


def test_requested_fold_must_equal_train_view_fold(train_view):
    from reaction_agent.p3.kernel import run_kernel
    with pytest.raises(FoldIsolationError):
        run_kernel(
            input_smiles="CCCCCCCCO", case_id="c", fold_id="WRONG_FOLD",
            mode="fixture", train_view=train_view,
        )


def test_test_fold_donor_rejected(train_view):
    # A donor whose fold_id differs from the train view fold is rejected.
    donor, ref = find_donor_ref(train_view, "fx_oct")
    from dataclasses import replace
    donor_test = replace(donor, fold_id="fold_test")
    polluted = TrainView(
        fold_id=train_view.fold_id, snapshot_id=train_view.snapshot_id,
        snapshot_hash=train_view.snapshot_hash,
        donors=[donor_test], reactions=train_view.reactions,
    )
    with pytest.raises(FoldIsolationError):
        load_reaction_evidence(polluted, donor.donor_id, ref)
