"""R3-B: snapshot / reaction authority tests.

Round 2 defect: ``recompute_train_view_hash`` covered fold, donor structural
identity and reaction IDs only — it omitted ``ReactionRef.reaction_hash`` and
the actual reaction content, and the loader never recomputed/compared the
reaction hash.  Forged refs and silently changed reaction content were
accepted:

    train_hash_unchanged_after_reaction_hash_forge=True
    forged_reaction_hash_accepted=True

Round 3 contract: a canonical reaction authority preimage (reaction ID +
normalized reaction, participants + mapped structures, mapping report,
resolved lineages, source ledger, eligibility + donor eligibility, donor
participant binding, component/schema versions) derives every
``ReactionRef.reaction_hash``; the train-view snapshot preimage includes the
complete sorted reaction references and hashes; and the loader RECOMPUTES the
actual reaction hash and compares it with the reference (typed failures
REACTION_HASH_MISMATCH / REACTION_REF_BINDING_MISMATCH).
"""
from dataclasses import replace

import pytest

from reaction_agent.p3.fixtures import (
    ReactionRef,
    TrainView,
    build_train_view,
    canonical_reaction_hash,
    find_donor_ref,
    load_fixture_reactions,
    recompute_train_view_hash,
)
from reaction_agent.p3.load import (
    ReactionAuthorityError,
    load_reaction_evidence,
)


def _tv():
    return build_train_view(load_fixture_reactions())


def _tv_with_fixture(tv, name, fixture):
    reactions = dict(tv.reactions)
    reactions[name] = fixture
    return TrainView(
        fold_id=tv.fold_id, snapshot_id=tv.snapshot_id,
        snapshot_hash=tv.snapshot_hash, donors=tv.donors,
        reactions=reactions,
        authority_manifest=tv.authority_manifest,
    )


# -- 1. Forged ReactionRef.reaction_hash ------------------------------------


def test_snapshot_hash_changes_when_reaction_hash_forged():
    tv = _tv()
    donor, ref = find_donor_ref(tv, "fx_oct")
    original = recompute_train_view_hash(tv)
    ref.reaction_hash = "forged_" + ref.reaction_hash[6:]
    assert recompute_train_view_hash(tv) != original, (
        "train-view snapshot hash must cover every ReactionRef.reaction_hash"
    )


def test_forged_reaction_hash_rejected_on_load():
    tv = _tv()
    donor, ref = find_donor_ref(tv, "fx_oct")
    forged = ReactionRef(
        reaction_id=ref.reaction_id,
        donor_participant_id=ref.donor_participant_id,
        lineage_id=ref.lineage_id,
        reaction_hash="forged_reaction_hash_value",
    )
    with pytest.raises(ReactionAuthorityError) as excinfo:
        load_reaction_evidence(tv, donor.donor_id, forged)
    assert excinfo.value.failure_code == "REACTION_HASH_MISMATCH"


# -- 2. Same reaction ID with changed content --------------------------------


def _assert_content_mutation_rejected(mutate):
    tv = _tv()
    donor, ref = find_donor_ref(tv, "fx_oct")
    fixture = tv.reactions["rxn_oct"]
    mutated = mutate(fixture)
    mutated_tv = _tv_with_fixture(tv, "rxn_oct", mutated)
    with pytest.raises(ReactionAuthorityError) as excinfo:
        load_reaction_evidence(mutated_tv, donor.donor_id, ref)
    assert excinfo.value.failure_code == "REACTION_HASH_MISMATCH"


def test_mutation_participant_deleted_rejected():
    def mutate(fx):
        evidence = fx.evidence.model_copy(update={
            "participants": fx.evidence.participants[:1],
        })
        return replace(fx, evidence=evidence,
                       participants=fx.participants[:1])
    _assert_content_mutation_rejected(mutate)


def test_mutation_mapped_structure_changed_rejected():
    # Same reaction ID, same participants — but one mapped structure differs.
    def mutate(fx):
        p0 = fx.participants[0]
        forged_smiles = p0.canonical_smiles.replace("[CH3:1]", "[CH2:1][H:10]") \
            if "[CH3:1]" in p0.canonical_smiles else p0.canonical_smiles + "[H:10]"
        new_p0 = p0.model_copy(update={"canonical_smiles": forged_smiles})
        participants = [new_p0] + fx.participants[1:]
        evidence = fx.evidence.model_copy(update={"participants": participants})
        return replace(fx, participants=participants, evidence=evidence)
    _assert_content_mutation_rejected(mutate)


def test_mutation_mapping_report_changed_rejected():
    def mutate(fx):
        mapping = fx.mapping_report.model_copy(update={"input_hash": "forged_input"})
        return replace(fx, mapping_report=mapping)
    _assert_content_mutation_rejected(mutate)


def test_mutation_lineage_changed_rejected():
    def mutate(fx):
        lineage = fx.lineages[0]
        forged = lineage.model_copy(update={
            "transformed_atom_maps": sorted(lineage.transformed_atom_maps) + [99],
        })
        return replace(fx, lineages=[forged] + fx.lineages[1:])
    _assert_content_mutation_rejected(mutate)


def test_mutation_source_ledger_changed_rejected():
    def mutate(fx):
        ledger = fx.source_ledger.model_copy(update={"charge_balance": 7})
        return replace(fx, source_ledger=ledger)
    _assert_content_mutation_rejected(mutate)


def test_mutation_eligibility_changed_rejected():
    def mutate(fx):
        eligibility = fx.eligibility.model_copy(
            update={"reason": fx.eligibility.reason + " (tampered)"}
        )
        return replace(fx, eligibility=eligibility)
    _assert_content_mutation_rejected(mutate)


def test_mutation_reaction_string_changed_rejected():
    def mutate(fx):
        evidence = fx.evidence.model_copy(update={
            "normalized_reaction": fx.evidence.normalized_reaction + ".forged",
        })
        return replace(fx, evidence=evidence)
    _assert_content_mutation_rejected(mutate)


# -- 3. Ref binding -----------------------------------------------------------


def test_ref_bound_to_wrong_donor_participant_rejected():
    tv = _tv()
    donor, ref = find_donor_ref(tv, "fx_oct")
    fixture = tv.reactions["rxn_oct"]
    other = next(
        p.participant_id for p in fixture.participants
        if p.participant_id != fixture.donor_participant_id
    )
    forged = ReactionRef(
        reaction_id=ref.reaction_id,
        donor_participant_id=other,  # not the fixture's designated donor
        lineage_id=ref.lineage_id,
        reaction_hash=ref.reaction_hash,  # content hash is correct
    )
    with pytest.raises(ReactionAuthorityError) as excinfo:
        load_reaction_evidence(tv, donor.donor_id, forged)
    assert excinfo.value.failure_code == "REACTION_REF_BINDING_MISMATCH"


# -- 4. Canonical authority properties ----------------------------------------


def test_reaction_hash_covers_authority_preimage():
    tv = _tv()
    fixture = tv.reactions["rxn_oct"]
    from reaction_agent.p3.fixtures import reaction_authority_preimage
    preimage = reaction_authority_preimage(fixture)
    # R4-B: the preimage carries the COMPLETE reaction evidence — every
    # ReactionEvidence audit field must be present (never silently excluded).
    assert {
        "reaction_id", "mapping_report", "resolved_lineages", "source_ledger",
        "eligibility", "donor_eligibility", "donor_participant_id",
    } <= set(preimage), (
        f"reaction authority preimage missing top-level keys: "
        f"{sorted(set(preimage))}"
    )
    assert "schema_version" in preimage and "reaction_authority_version" in preimage
    evidence = preimage["evidence"]
    for field in (
        "reaction_id", "source_record_id", "source_name", "source_version",
        "source_uri_or_citation", "raw_reaction", "normalized_reaction",
        "direction", "participants", "mapping_report",
        "fragment_lineage_graph", "resolved_transformed_lineages",
        "ambiguity_sets", "transformation_hypotheses",
        "source_reaction_ledger", "quality_report", "provenance",
        "snapshot_id", "quarantine",
    ):
        assert field in evidence, f"evidence preimage missing {field!r}"
    assert canonical_reaction_hash(fixture)


def test_snapshot_hash_covers_reaction_content():
    # Rebuilding from content-mutated fixtures must change the snapshot hash
    # (the snapshot preimage carries complete sorted refs + hashes).
    tv1 = _tv()
    fixtures = load_fixture_reactions()
    fx = fixtures["rxn_oct"]
    p0 = fx.participants[0]
    new_p0 = p0.model_copy(update={
        "canonical_smiles": p0.canonical_smiles + "[H:10]",
    })
    participants = [new_p0] + fx.participants[1:]
    evidence = fx.evidence.model_copy(update={"participants": participants})
    fixtures["rxn_oct"] = replace(fx, participants=participants, evidence=evidence)
    tv2 = build_train_view(fixtures)
    assert tv1.snapshot_hash != tv2.snapshot_hash


def test_reaction_hash_invariant_to_semantically_irrelevant_ordering():
    fixtures = load_fixture_reactions()
    fx = fixtures["rxn_oct"]
    baseline = canonical_reaction_hash(fx)
    # Participant and lineage collection ORDER is semantically irrelevant.
    evidence = fx.evidence.model_copy(update={
        "participants": list(reversed(fx.evidence.participants)),
    })
    shuffled = replace(
        fx,
        participants=list(reversed(fx.participants)),
        lineages=list(reversed(fx.lineages)),
        evidence=evidence,
    )
    assert canonical_reaction_hash(shuffled) == baseline


def test_clean_load_still_works():
    tv = _tv()
    donor, ref = find_donor_ref(tv, "fx_oct")
    dev = load_reaction_evidence(tv, donor.donor_id, ref)
    assert dev.context.reaction_id == "fx_oct"
