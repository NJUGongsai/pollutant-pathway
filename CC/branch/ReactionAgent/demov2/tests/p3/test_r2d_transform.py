"""R2-D transformation content addressing tests."""
import pytest

from rdkit import Chem  # type: ignore

from reaction_agent.p3.fixtures import (
    build_fixture_reaction,
    build_train_view,
    find_donor_ref,
    load_fixture_reactions,
)
from reaction_agent.p3.load import load_reaction_evidence
from reaction_agent.p3.transform import (
    TransformExtractionError,
    _atom_by_map,
    extract_transform,
)
from reaction_agent.p3 import transform as transform_mod


def _extract(train_view, reaction_id):
    donor, ref = find_donor_ref(train_view, reaction_id)
    dev = load_reaction_evidence(train_view, donor.donor_id, ref)
    return extract_transform(dev, lineage_id=ref.lineage_id)


def test_selected_nonfirst_lineage_changes_transform_identity():
    # decarb has 2 resolved lineages (reactant->propane, reactant->CO2).
    # Extracting the NON-first lineage (CO2) must change the transform identity.
    tv = build_train_view(load_fixture_reactions())
    donor, ref = find_donor_ref(tv, "fx_decarb")
    dev = load_reaction_evidence(tv, donor.donor_id, ref)
    lineages = dev.context.resolved_lineages
    assert len(lineages) >= 2
    primary = extract_transform(dev, lineage_id=ref.lineage_id)
    other = next(l for l in lineages if l.lineage_id != ref.lineage_id)
    nonfirst = extract_transform(dev, lineage_id=other.lineage_id)
    assert primary.canonical_transform_hash != nonfirst.canonical_transform_hash
    assert primary.source_lineage_ids != nonfirst.source_lineage_ids


def test_transform_hash_covers_preconditions(monkeypatch):
    tv = build_train_view(load_fixture_reactions())
    baseline = _extract(tv, "fx_oct")
    original = transform_mod._site_preconditions

    # A different precondition set must change the content-addressed hash.
    def _extra_preconditions(a_mol, site_maps):
        pre = original(a_mol, site_maps)
        return pre + [transform_mod.SitePrecondition(
            precondition_id="pre_extra", kind="aromaticity",
            atom_map_number=8, params={"aromatic": False},
        )]

    monkeypatch.setattr(transform_mod, "_site_preconditions", _extra_preconditions)
    mutated = _extract(tv, "fx_oct")
    assert baseline.canonical_transform_hash != mutated.canonical_transform_hash


def test_transform_hash_covers_ledger_requirements(monkeypatch):
    tv = build_train_view(load_fixture_reactions())
    baseline = _extract(tv, "fx_oct")

    def _extra_reqs(context, transferred, removed_maps):
        return ["extra_ledger_requirement"]

    monkeypatch.setattr(transform_mod, "_ledger_requirements", _extra_reqs)
    mutated = _extract(tv, "fx_oct")
    assert baseline.canonical_transform_hash != mutated.canonical_transform_hash


def test_duplicate_atom_map_rejected():
    mol = Chem.MolFromSmiles("[CH3:1][CH2:1]")  # both atoms map 1
    assert mol is not None
    with pytest.raises(TransformExtractionError):
        _atom_by_map(mol)


def test_aromatic_bond_order_preserved():
    # 1,4-cyclohexadiene -> benzene: single bonds become aromatic (1.5).
    fx = build_fixture_reaction(
        name="aromat",
        reactant_smiles=["[C:1]1[C:2]=[C:3][C:4]=[C:5][C:6]1"],
        product_smiles=["[c:1]1[c:2][c:3][c:4][c:5][c:6]1"],
    )
    assert fx.mapping_report.mapping_status.value == "fully_mapped"
    tv = build_train_view({"rxn_aromat": fx})
    tr = _extract(tv, "fx_aromat")
    aromatic_orders = [
        b.new_order for b in tr.bond_changes
        if b.operation in ("add", "order_change")
    ]
    assert 1.5 in aromatic_orders, (
        "aromatic bond order (1.5) must be preserved, not truncated to single"
    )


def test_multiatom_transfer_internal_bonds_preserved():
    # Acetaldehyde + HCN -> cyanohydrin transfers a 2-atom CN group whose
    # internal triple bond must be preserved.
    fx = build_fixture_reaction(
        name="cyanohydrin",
        reactant_smiles=["[O:1]=[C:2][CH3:3]", "[C:4]#[N:5]"],
        product_smiles=["[O:1][C:2]([C:4]#[N:5])[CH3:3]"],
    )
    assert fx.mapping_report.mapping_status.value == "fully_mapped"
    tv = build_train_view({"rxn_cyanohydrin": fx})
    tr = _extract(tv, "fx_cyanohydrin")
    by_map = {t.transfer_map_number: t for t in tr.transferred_atoms}
    assert set(by_map) == {4, 5}
    c4 = by_map[4]
    n5 = by_map[5]
    # C4 bonds to common atom 2 (the carbonyl carbon).
    assert any(b["atom_map"] == 2 for b in c4.bonds_to)
    # Internal triple bond C4=N5 preserved on BOTH sides.
    assert any(b["atom_map"] == 5 and b["order"] == 3 for b in c4.bonds_to_transferred)
    assert any(b["atom_map"] == 4 and b["order"] == 3 for b in n5.bonds_to_transferred)


def test_removed_atom_sink_required(monkeypatch):
    # If a removed atom cannot resolve a formal sink, strict transform fails.
    tv = build_train_view(load_fixture_reactions())
    with pytest.raises(TransformExtractionError):
        monkeypatch.setattr(
            transform_mod, "_find_participant_for_map",
            lambda participants, map_number, side: "unknown_source",
        )
        _extract(tv, "fx_decarb")


def test_unknown_transfer_source_rejected(monkeypatch):
    # If a transferred atom has no formal source, strict transform fails.
    tv = build_train_view(load_fixture_reactions())
    with pytest.raises(TransformExtractionError):
        monkeypatch.setattr(
            transform_mod, "_find_participant_for_map",
            lambda participants, map_number, side: "unknown_source",
        )
        _extract(tv, "fx_hydrolysis")
