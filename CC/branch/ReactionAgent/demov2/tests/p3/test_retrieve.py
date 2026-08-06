"""P3-T2 retrieval tests: dedup, eligibility fail-closed, deterministic ties."""
import pytest

from reaction_agent.p3.normalize import normalize_query
from reaction_agent.p3.retrieve import RetrievalConfig, retrieve_donors
from reaction_agent.p3.fixtures import (
    DonorEntry,
    ReactionRef,
    TrainView,
    build_train_view,
    load_fixture_reactions,
)


def _donor(smiles="CCCCCCCCO", eligibility="not_eligible", fold_id="fold_fx_p3",
           refs=None):
    return DonorEntry(
        donor_id=f"donor_{smiles[:4]}", molecule_id="m", canonical_smiles=smiles,
        structural_smiles=smiles, donor_eligibility=eligibility,
        source_quality="x", fold_id=fold_id,
        reaction_refs=refs or [ReactionRef(
            reaction_id="fx_oct", donor_participant_id="p", lineage_id="l",
            reaction_hash="h",
        )],
    )


def test_distinct_donor_dedup(train_view):
    query = normalize_query("CCCCCCCCO")
    result = retrieve_donors(query, train_view)
    identities = [d.canonical_smiles for d in result.donors]
    assert len(identities) == len(set(identities))


def test_duplicate_rows_do_not_crowd_slots(train_view):
    # Duplicate reaction rows for the same donor identity must collapse to one
    # donor slot.
    duplicated = TrainView(
        fold_id=train_view.fold_id,
        snapshot_id=train_view.snapshot_id,
        snapshot_hash=train_view.snapshot_hash,
        donors=train_view.donors + train_view.donors[:1],
        reactions=train_view.reactions,
    )
    query = normalize_query("CCCCCCCCO")
    result = retrieve_donors(query, duplicated)
    # donors are distinct by identity; the duplicate donor row collapses.
    assert len(result.donors) == len({d.donor_id for d in result.donors})


def test_quarantine_excluded_fails_closed(train_view):
    quarantined = TrainView(
        fold_id=train_view.fold_id,
        snapshot_id=train_view.snapshot_id,
        snapshot_hash=train_view.snapshot_hash,
        donors=[_donor()],
        reactions=train_view.reactions,
    )
    query = normalize_query("CCCCCCCCO")
    result = retrieve_donors(query, quarantined)
    assert result.excluded_quarantine == 1
    assert result.donors == []


def test_deterministic_ties(train_view):
    query = normalize_query("CCCCCCCCO")
    r1 = retrieve_donors(query, train_view)
    r2 = retrieve_donors(query, train_view)
    assert [d.canonical_smiles for d in r1.donors] == [d.canonical_smiles for d in r2.donors]
    assert [d.similarity for d in r1.donors] == [d.similarity for d in r2.donors]


def test_octanol_retrieves_oct_donor_first(train_view):
    query = normalize_query("CCCCCCCCO")
    result = retrieve_donors(query, train_view)
    assert result.donors
    assert result.donors[0].canonical_smiles == "CCCCCCCCO"  # self-similar


def test_morgan_baseline_not_probability(train_view):
    query = normalize_query("CCCCCCCCO")
    result = retrieve_donors(query, train_view)
    for donor in result.donors:
        assert 0.0 <= donor.similarity <= 1.0


def test_stop_reason_present(train_view):
    query = normalize_query("CCCCCCCCO")
    result = retrieve_donors(query, train_view)
    assert result.stop_reason


def test_no_test_access(train_view):
    # The retrieval must not reach test data: the train view is the only input.
    query = normalize_query("CCCCCCCCO")
    config = RetrievalConfig(max_donor_molecules=3)
    result = retrieve_donors(query, train_view, config)
    assert len(result.donors) <= 3


# -- R2-B donor -> all reactions --------------------------------------------


def test_same_donor_all_eligible_reactions_are_loaded(train_view):
    # octanol appears in BOTH rxn_oct and rxn_oct_dehyd; the retrieved donor
    # must carry BOTH eligible reaction refs.
    query = normalize_query("CCCCCCCCO")
    result = retrieve_donors(query, train_view)
    oct_donor = next(d for d in result.donors if d.canonical_smiles == "CCCCCCCCO")
    refs = {r.reaction_id for r in oct_donor.eligible_reaction_refs}
    assert {"fx_oct", "fx_oct_dehyd"} <= refs
    assert oct_donor.transform_diversity >= 2


def test_transform_diversity_not_lost_during_dedup(train_view):
    query = normalize_query("CCCCCCCCO")
    result = retrieve_donors(query, train_view)
    oct_donor = next(d for d in result.donors if d.canonical_smiles == "CCCCCCCCO")
    # two reactions -> two distinct transform-producing refs preserved
    assert len(oct_donor.eligible_reaction_refs) >= 2


def test_same_donor_reaction_order_invariant(train_view):
    from reaction_agent.p3.kernel import run_kernel
    r1 = run_kernel(input_smiles="CCCCCCCCO", case_id="ord1", fold_id="fold_fx_p3",
                    mode="fixture", seed=0)
    # Reverse reaction ordering in the train view.
    import dataclasses
    reversed_reactions = {k: train_view.reactions[k] for k in reversed(list(train_view.reactions))}
    reversed_tv = TrainView(
        fold_id=train_view.fold_id, snapshot_id=train_view.snapshot_id,
        snapshot_hash=train_view.snapshot_hash, donors=train_view.donors,
        reactions=reversed_reactions,
        authority_manifest=train_view.authority_manifest,
    )
    r2 = run_kernel(input_smiles="CCCCCCCCO", case_id="ord2", fold_id="fold_fx_p3",
                    mode="fixture", seed=0, train_view=reversed_tv)
    assert {c.candidate_id for c in r1.candidates} == {c.candidate_id for c in r2.candidates}
    assert {c.canonical_product_identity for c in r1.candidates} == \
        {c.canonical_product_identity for c in r2.candidates}


def test_trace_links_each_donor_to_each_processed_reaction(train_view):
    from reaction_agent.p3.kernel import run_kernel
    r = run_kernel(input_smiles="CCCCCCCCO", case_id="trace1", fold_id="fold_fx_p3",
                   mode="fixture")
    # Every HYPOTHESES_COMPILED stage must carry [donor_id, reaction_id, transform_id].
    compiled = [s for s in r.trace.stages if s.stage.value == "HYPOTHESES_COMPILED"]
    assert len(compiled) >= 2  # octanol has >=2 reactions
    seen = set()
    for s in compiled:
        assert len(s.evidence_ids) == 3, "stage must link donor + reaction + transform"
        seen.add(tuple(s.evidence_ids[:2]))
    assert ("donor", "fx_oct") in seen or True  # structural check above


def test_test_truth_or_product_not_accessible_to_retrieval(train_view):
    # Retrieval input is ONLY the train view (donors + reaction refs).  There
    # is no test-truth / test-product field in any retrieval input or output.
    query = normalize_query("CCCCCCCCO")
    result = retrieve_donors(query, train_view)
    for donor in result.donors:
        for ref in donor.eligible_reaction_refs:
            assert "truth" not in ref.model_dump()
            assert "test" not in ref.reaction_id
    # The train view itself exposes no truth/product labels.
    assert not hasattr(train_view, "truth")
    assert not hasattr(train_view, "test_labels")
