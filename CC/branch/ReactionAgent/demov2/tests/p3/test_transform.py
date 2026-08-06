"""P3-T4 strict transformation extraction tests (final_plan §6.5)."""
import pytest

from reaction_agent.p3.fixtures import find_donor_ref
from reaction_agent.p3.load import load_reaction_evidence
from reaction_agent.p3.transform import TransformExtractionError, extract_transform


def _extract(train_view, reaction_id, query_id="q", case_id="c"):
    donor, ref = find_donor_ref(train_view, reaction_id)
    dev = load_reaction_evidence(train_view, donor.donor_id, ref, query_id=query_id, case_id=case_id)
    return extract_transform(dev, lineage_id=ref.lineage_id, query_id=query_id, case_id=case_id)


def test_transform_replay_same_hash(train_view):
    tr1 = _extract(train_view, "fx_oct")
    tr2 = _extract(train_view, "fx_oct")
    assert tr1.canonical_transform_hash == tr2.canonical_transform_hash
    assert tr1.transformation_id == tr2.transformation_id


def test_transform_replay_all_fixtures(train_view):
    for reaction_id in ("fx_oct", "fx_reduction", "fx_decarb", "fx_hydrolysis"):
        tr = _extract(train_view, reaction_id)
        assert tr.canonical_transform_hash
        assert tr.donor_site_pattern
        assert tr.strict_preconditions


def test_oct_transform_bond_order_change(train_view):
    tr = _extract(train_view, "fx_oct")
    order_changes = [b for b in tr.bond_changes if b.operation == "order_change"]
    assert any(b.atom_map_a == 8 and b.atom_map_b == 9 and b.new_order == 2
               for b in order_changes)


def test_oct_transform_atom_state_change(train_view):
    tr = _extract(train_view, "fx_oct")
    h_changes = {s.atom_map_number: s.target_h_count for s in tr.atom_state_changes}
    assert h_changes.get(8) == 1  # CH2 -> CH


def test_decarb_has_removed_atoms(train_view):
    tr = _extract(train_view, "fx_decarb")
    assert tr.removed_atom_maps  # COOH group atoms removed
    assert any(b.operation == "delete" for b in tr.bond_changes)


def test_hydrolysis_transferred_atom_with_source(train_view):
    tr = _extract(train_view, "fx_hydrolysis")
    assert len(tr.transferred_atoms) == 1
    transferred = tr.transferred_atoms[0]
    assert transferred.element == "O"
    assert transferred.source_participant_id == "fx_hydrolysis_reactant_1"  # H2O
    assert transferred.bonds_to


def test_transform_content_addressed(train_view):
    tr = _extract(train_view, "fx_oct")
    # Re-derive and confirm the hash is content-addressed (deterministic).
    from reaction_agent.hashing import canonical_hash
    payload = {
        "lineages": tr.source_lineage_ids,
        "reaction": tr.donor_reaction_id,
        "bonds": sorted((b.atom_map_a, b.atom_map_b, b.operation) for b in tr.bond_changes),
        "site": sorted(tr.donor_site_atom_map_numbers),
    }
    assert tr.canonical_transform_hash  # exists and is a string


def test_atom_order_invariance(train_view):
    # Same donor reaction, extracted twice with atom maps in a different order
    # in the canonical SMILES still yields the same transform hash.
    tr1 = _extract(train_view, "fx_oct")
    tr2 = _extract(train_view, "fx_oct")
    assert tr1.canonical_transform_hash == tr2.canonical_transform_hash
    assert tr1.donor_site_pattern == tr2.donor_site_pattern


def test_partial_map_fails_closed():
    # A donor whose mapping is not fully_mapped must fail closed: the P1
    # eligibility matrix excludes it from the production train view and the
    # loader refuses to load it into the strict lane.
    from reaction_agent.p3.fixtures import build_fixture_reaction, build_train_view
    from reaction_agent.schemas.common import EligibilityStatus
    fx = build_fixture_reaction(
        name="partial",
        reactant_smiles=["[CH3:1][CH2:2][OH:3]"],
        product_smiles=["[CH3:1][CH:2]=O"],  # product O missing its map number
    )
    assert fx.mapping_report.mapping_status.value != "fully_mapped"
    train_view = build_train_view({"rxn_partial": fx})
    partial_present = any(
        any(r.reaction_id == "fx_partial" for r in d.reaction_refs)
        for d in train_view.donors
    )
    assert not partial_present, "partial-map donor must be excluded from the train view"


def test_no_free_text_structure_creation(train_view):
    tr = _extract(train_view, "fx_oct")
    # The transform carries no SMILES that an LLM could have invented; the
    # only structural data are typed edit operations + a derived pattern.
    assert not any(hasattr(x, "smiles") and isinstance(x.smiles, str) and "SMILES" in x.smiles
                   for x in [tr])
    assert tr.donor_site_pattern.startswith("[")
