"""R2-E conditioned-site + graph-edit fail-closed tests."""
import pytest

from reaction_agent.p3.fixtures import (
    build_train_view,
    find_donor_ref,
    load_fixture_reactions,
)
from reaction_agent.p3.load import load_reaction_evidence
from reaction_agent.p3.normalize import normalize_query
from reaction_agent.p3.sites import enumerate_sites
from reaction_agent.p3.transform import extract_transform
from reaction_agent.p3.generate import (
    ATOM_STATE_TARGET_MISSING,
    EXPECTED_BOND_ABSENT,
    MISSING_EDIT_ENDPOINT,
    QUERY_SITE_ID_MISMATCH,
    REMOVAL_TARGET_MISSING,
    TRANSFER_ANCHOR_MISSING,
    TRANSFORM_SITE_ID_MISMATCH,
    UNEXPECTED_EXISTING_BOND,
    generate_product,
)
from reaction_agent.p3.schemas import BondChange, SiteEligibility


def _oct_ctx():
    tv = build_train_view(load_fixture_reactions())
    donor, ref = find_donor_ref(tv, "fx_oct")
    dev = load_reaction_evidence(tv, donor.donor_id, ref)
    tr = extract_transform(dev, lineage_id=ref.lineage_id)
    return tv, dev, tr


def _oct_site(tr, smiles="CCCCCCCCO"):
    q = normalize_query(smiles)
    site = [s for s in enumerate_sites(tr, q) if s.eligibility is SiteEligibility.eligible][0]
    return q, site


def test_mismatched_transform_site_rejected():
    _, _, tr = _oct_ctx()
    q, site = _oct_site(tr)
    wrong_site = site.model_copy(update={"transformation_id": "tr_WRONG"})
    rep = generate_product(tr, wrong_site, q)
    assert rep.failure_code == TRANSFORM_SITE_ID_MISMATCH


def test_mismatched_query_site_rejected():
    _, _, tr = _oct_ctx()
    q, site = _oct_site(tr)
    wrong_site = site.model_copy(update={"query_id": "query_WRONG"})
    rep = generate_product(tr, wrong_site, q)
    assert rep.failure_code == QUERY_SITE_ID_MISMATCH


def test_missing_bond_endpoint_is_typed_failure():
    _, _, tr = _oct_ctx()
    q, site = _oct_site(tr)
    # Drop map 9 (O) from the correspondence -> bond order-change endpoint missing.
    corr = {k: v for k, v in site.atom_map_correspondence.items() if k != "9"}
    bad_site = site.model_copy(update={"atom_map_correspondence": corr})
    rep = generate_product(tr, bad_site, q)
    assert rep.failure_code == MISSING_EDIT_ENDPOINT


def test_expected_bond_absent_is_typed_failure():
    _, _, tr = _oct_ctx()
    q, site = _oct_site(tr)
    # Map 8->atom 0, map 9->atom 5 (distant atoms, no bond) -> the required
    # C-O order change has no bond to modify.
    corr = {"8": 0, "9": 5}
    bad_site = site.model_copy(update={"atom_map_correspondence": corr})
    rep = generate_product(tr, bad_site, q)
    assert rep.failure_code == EXPECTED_BOND_ABSENT


def test_existing_add_bond_is_typed_failure():
    _, _, tr = _oct_ctx()
    q, site = _oct_site(tr)
    # Change the transform to ADD bond 8-9 (already present on octanol).
    add_tr = tr.model_copy(update={
        "bond_changes": [BondChange(atom_map_a=8, atom_map_b=9, operation="add", new_order=2)],
    })
    rep = generate_product(add_tr, site, q)
    assert rep.failure_code == UNEXPECTED_EXISTING_BOND


def _synthetic_site(tr, q, correspondence=None):
    from reaction_agent.p3.schemas import ConditionedSite, SiteEligibility
    return ConditionedSite(
        site_id="site_syn", run_id=tr.run_id, case_id="c", fold_id=tr.fold_id,
        query_id=q.query_id, transformation_id=tr.transformation_id,
        query_atom_ids=list((correspondence or {}).values()),
        query_bond_ids=[],
        atom_map_correspondence=correspondence or {},
        matched_preconditions=[], failed_preconditions=[],
        symmetry_class="x", ambiguity_group=0,
        eligibility=SiteEligibility.eligible,
    )


def _synthetic_transform(**overrides):
    from reaction_agent.p3.schemas import StrictTransformation
    base = dict(
        transformation_id="tr_syn", run_id="run_syn", case_id="c",
        query_id="q", fold_id="fold_syn",
        source_lineage_ids=["l"], donor_reaction_id="r", mapped_atom_edits=[],
        bond_changes=[], atom_state_changes=[], transferred_atoms=[],
        removed_atom_maps=[], donor_site_atom_map_numbers=[],
        donor_site_smiles="C", donor_site_pattern="[#6]",
        strict_preconditions=[], ledger_requirements=[],
        canonical_transform_hash="h",
    )
    base.update(overrides)
    return StrictTransformation(**base)


def test_missing_atom_state_target_is_typed_failure():
    from reaction_agent.p3.schemas import AtomStateChange
    tr = _synthetic_transform(
        mapped_atom_edits=[8],
        atom_state_changes=[AtomStateChange(atom_map_number=8, target_h_count=1)],
        donor_site_atom_map_numbers=[8],
    )
    q = normalize_query("CCCCCCCCO")
    site = _synthetic_site(tr, q)  # empty correspondence -> target missing
    rep = generate_product(tr, site, q)
    assert rep.failure_code == ATOM_STATE_TARGET_MISSING


def test_missing_removed_atom_is_typed_failure():
    tr = _synthetic_transform(removed_atom_maps=[4], mapped_atom_edits=[4],
                              donor_site_atom_map_numbers=[4])
    q = normalize_query("CCCCCCCCO")
    site = _synthetic_site(tr, q)  # empty correspondence -> removed target missing
    rep = generate_product(tr, site, q)
    assert rep.failure_code == REMOVAL_TARGET_MISSING


def test_missing_transfer_anchor_is_typed_failure():
    from reaction_agent.p3.schemas import TransferredAtom
    tr = _synthetic_transform(
        mapped_atom_edits=[7], donor_site_atom_map_numbers=[7],
        transferred_atoms=[TransferredAtom(
            transfer_map_number=7, element="O", h_count=1,
            source_participant_id="h2o", bonds_to=[{"atom_map": 2, "order": 1}],
        )],
    )
    q = normalize_query("CCCCCCCCO")
    site = _synthetic_site(tr, q)  # anchor map 2 missing -> TRANSFER_ANCHOR_MISSING
    rep = generate_product(tr, site, q)
    assert rep.failure_code == TRANSFER_ANCHOR_MISSING


def test_ring_and_aromatic_site_preconditions():
    # Aromatic reaction: benzene + Cl2 -> chlorobenzene + HCl (donor bonds are
    # aromatic).  The site pattern must use aromatic bond queries (`:`) so an
    # aromatic query ring matches.
    from reaction_agent.p3.fixtures import build_fixture_reaction
    fx = build_fixture_reaction(
        name="chlorination",
        reactant_smiles=["[c:1]1[c:2][c:3][c:4][c:5][c:6]1", "[Cl:7][Cl:8]"],
        product_smiles=["[c:1]1[c:2][c:3]([Cl:7])[c:4][c:5][c:6]1", "[Cl:8][H:9]"],
    )
    assert fx.mapping_report.mapping_status.value == "fully_mapped"
    tv = build_train_view({"rxn_chlorination": fx})
    donor, ref = find_donor_ref(tv, "fx_chlorination")
    dev = load_reaction_evidence(tv, donor.donor_id, ref)
    tr = extract_transform(dev, lineage_id=ref.lineage_id)
    # Transferred chlorine anchored to aromatic carbon 3.
    assert {t.transfer_map_number for t in tr.transferred_atoms} == {7}
    assert any(b["atom_map"] == 3 for b in tr.transferred_atoms[0].bonds_to)
    assert ":" in tr.donor_site_pattern, "aromatic site pattern must use ':'"
    q = normalize_query("c1ccccc1")  # benzene
    sites = enumerate_sites(tr, q)
    # The aromatic site pattern must match an aromatic query ring.
    assert len(sites) >= 1
