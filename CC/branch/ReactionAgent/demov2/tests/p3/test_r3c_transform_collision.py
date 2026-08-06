"""R3-C transform hash collision tests.

Round 2 defects:
- the transform preimage omitted transferred ``bonds_to`` common anchors and
  their bond orders;
- ``sorted(removed_sinks)`` hashed only dictionary KEYS and dropped the sink
  participant values;
- ``StrictTransformation`` did not preserve removed-sink assignments, and the
  stored hash/ID were never recomputed from the fields (a semantic mutation
  of the transform left hash + ID unchanged).

Round 3 contract: ONE canonical transform preimage used by both
``canonical_transform_hash`` and ``transformation_id``; it includes the
selected lineage + reaction authority binding, all bond/atom-state edits,
transferred element/charge/H/source participant, transferred bonds to common
anchors (atom map + bond order), internal transferred bonds, removed atom
maps + exact map-to-sink participant assignments, donor site, local
environment, preconditions, ledger requirements, versions and policies.
Every semantic change changes hash AND ID; reordering equivalent collections
does not.
"""
import pytest

from reaction_agent.p3 import transform as transform_mod
from reaction_agent.p3.fixtures import (
    build_fixture_reaction,
    build_train_view,
    find_donor_ref,
    load_fixture_reactions,
)
from reaction_agent.p3.load import load_reaction_evidence
from reaction_agent.p3.transform import (
    TransformBindingError,
    extract_transform,
    recompute_transform_preimage,
    verify_transform_binding,
)


def _extract(reaction_id, fixtures=None):
    tv = build_train_view(fixtures or load_fixture_reactions())
    donor, ref = find_donor_ref(tv, reaction_id)
    dev = load_reaction_evidence(tv, donor.donor_id, ref)
    return extract_transform(dev, lineage_id=ref.lineage_id)


# -- 1. Audit reproduction: anchor semantics vs stored hash ------------------


def _chlorination(anchor_map_product: str):
    return build_fixture_reaction(
        name="chlorination",
        reactant_smiles=["[c:1]1[c:2][c:3][c:4][c:5][c:6]1", "[Cl:7][Cl:8]"],
        product_smiles=[anchor_map_product, "[Cl:8][H:9]"],
    )


def test_transferred_anchor_bond_change_changes_hash_and_id():
    # Cl anchored to c:3 vs c:4 — transferred anchor semantics change.
    fx_a = _chlorination("[c:1]1[c:2][c:3]([Cl:7])[c:4][c:5][c:6]1")
    fx_b = _chlorination("[c:1]1[c:2][c:3][c:4]([Cl:7])[c:5][c:6]1")
    assert fx_a.mapping_report.mapping_status.value == "fully_mapped"
    assert fx_b.mapping_report.mapping_status.value == "fully_mapped"
    t_a = _extract("fx_chlorination", {"rxn_chlorination": fx_a})
    t_b = _extract("fx_chlorination", {"rxn_chlorination": fx_b})
    anchors_a = {b["atom_map"] for b in t_a.transferred_atoms[0].bonds_to}
    anchors_b = {b["atom_map"] for b in t_b.transferred_atoms[0].bonds_to}
    assert anchors_a != anchors_b, "mutation must change the anchor"
    assert t_a.canonical_transform_hash != t_b.canonical_transform_hash
    assert t_a.transformation_id != t_b.transformation_id


def test_forged_anchor_bonds_to_breaks_binding():
    # The audit reproduction: mutate the transferred anchor semantics on the
    # extracted transform — hash and ID must NOT remain valid.
    fx = _chlorination("[c:1]1[c:2][c:3]([Cl:7])[c:4][c:5][c:6]1")
    t = _extract("fx_chlorination", {"rxn_chlorination": fx})
    forged_atom = t.transferred_atoms[0].model_copy(update={
        "bonds_to": [{"atom_map": 5, "order": 1}],
    })
    forged = t.model_copy(update={"transferred_atoms": [forged_atom]})
    with pytest.raises(TransformBindingError) as excinfo:
        verify_transform_binding(forged)
    assert excinfo.value.failure_code == "TRANSFORM_HASH_COLLISION"


def test_forged_internal_bond_breaks_binding():
    fx = build_fixture_reaction(
        name="cyanohydrin",
        reactant_smiles=["[O:1]=[C:2][CH3:3]", "[C:4]#[N:5]"],
        product_smiles=["[O:1][C:2]([C:4]#[N:5])[CH3:3]"],
    )
    t = _extract("fx_cyanohydrin", {"rxn_cyanohydrin": fx})
    by_map = {a.transfer_map_number: a for a in t.transferred_atoms}
    forged_c4 = by_map[4].model_copy(update={
        "bonds_to_transferred": [{"atom_map": 5, "order": 1}],  # triple -> single
    })
    forged = t.model_copy(update={"transferred_atoms": [
        forged_c4, by_map[5],
    ]})
    with pytest.raises(TransformBindingError):
        verify_transform_binding(forged)


def test_forged_charge_and_h_count_break_binding():
    fx = build_fixture_reaction(
        name="chlorination",
        reactant_smiles=["[c:1]1[c:2][c:3][c:4][c:5][c:6]1", "[Cl:7][Cl:8]"],
        product_smiles=["[c:1]1[c:2][c:3]([Cl:7])[c:4][c:5][c:6]1", "[Cl:8][H:9]"],
    )
    t = _extract("fx_chlorination", {"rxn_chlorination": fx})
    atom = t.transferred_atoms[0]
    forged_charge = t.model_copy(update={"transferred_atoms": [
        atom.model_copy(update={"formal_charge": atom.formal_charge + 1}),
    ]})
    forged_h = t.model_copy(update={"transferred_atoms": [
        atom.model_copy(update={"h_count": atom.h_count + 1}),
    ]})
    with pytest.raises(TransformBindingError):
        verify_transform_binding(forged_charge)
    with pytest.raises(TransformBindingError):
        verify_transform_binding(forged_h)


def test_forged_source_participant_breaks_binding():
    fx = build_fixture_reaction(
        name="chlorination",
        reactant_smiles=["[c:1]1[c:2][c:3][c:4][c:5][c:6]1", "[Cl:7][Cl:8]"],
        product_smiles=["[c:1]1[c:2][c:3]([Cl:7])[c:4][c:5][c:6]1", "[Cl:8][H:9]"],
    )
    t = _extract("fx_chlorination", {"rxn_chlorination": fx})
    atom = t.transferred_atoms[0]
    forged = t.model_copy(update={"transferred_atoms": [
        atom.model_copy(update={"source_participant_id": "fx_chlorination_reactant_0"}),
    ]})
    with pytest.raises(TransformBindingError):
        verify_transform_binding(forged)


# -- 2. Removed-sink structure + value sensitivity ---------------------------


def test_strict_transform_has_removed_sink_assignments():
    t = _extract("fx_decarb")
    assert t.removed_atom_maps, "decarb must have removed atoms"
    sinks = {s.atom_map: s.sink_participant_id for s in t.removed_atom_sinks}
    # EXACT coverage: every removed atom map has one sink assignment.
    assert set(sinks) == set(t.removed_atom_maps)
    # The sink is the CO2 coproduct participant, never empty/unknown.
    assert all(pid and pid != "unknown_source" for pid in sinks.values())


def test_sink_participant_value_changes_hash(monkeypatch):
    # Same reaction, same removed maps — only the SINK PARTICIPANT differs.
    # The preimage must hash the map->sink pairs, not just the map keys.
    tv = build_train_view(load_fixture_reactions())
    baseline = _extract("fx_decarb")
    other_sink = next(
        p.participant_id for p in
        tv.reactions["rxn_decarb"].participants
        if p.side == "product"
        and p.participant_id not in set(baseline.removed_atom_sinks and
                                        [s.sink_participant_id for s in
                                         baseline.removed_atom_sinks] or [""])
    )
    original = transform_mod._find_participant_for_map

    def _redirect_sink(participants, map_number, side):
        if side == "product":
            return other_sink
        return original(participants, map_number, side)

    monkeypatch.setattr(transform_mod, "_find_participant_for_map", _redirect_sink)
    mutated = _extract("fx_decarb")
    assert baseline.canonical_transform_hash != mutated.canonical_transform_hash
    assert baseline.transformation_id != mutated.transformation_id


def test_removed_sink_coverage_enforced_by_validation():
    # A transform that claims removed atoms but lacks a sink assignment for
    # one of them must not pass candidate validation.
    from reaction_agent.p3.normalize import normalize_query
    from reaction_agent.p3.sites import enumerate_sites
    from reaction_agent.p3.generate import generate_product
    from reaction_agent.p3.validate import validate_candidate
    from reaction_agent.p3.schemas import SiteEligibility
    from reaction_agent.hashing import stable_id

    tv = build_train_view(load_fixture_reactions())
    donor, ref = find_donor_ref(tv, "fx_decarb")
    dev = load_reaction_evidence(tv, donor.donor_id, ref)
    tr = extract_transform(dev, lineage_id=ref.lineage_id)
    assert tr.removed_atom_maps and tr.removed_atom_sinks
    # Drop ONE sink assignment -> coverage incomplete.
    forged = tr.model_copy(update={
        "removed_atom_sinks": tr.removed_atom_sinks[:-1],
    })
    q = normalize_query("CCCC(=O)O")
    sites = [s for s in enumerate_sites(forged, q)
             if s.eligibility is SiteEligibility.eligible]
    if not sites:
        pytest.skip("no eligible site for decarb on butanoic acid query")
    report = generate_product(forged, sites[0], q)
    candidate_id = stable_id("cand", {
        "identity": report.canonical_product or "none", "version": "p3-1",
    })
    validation, _ = validate_candidate(
        dev, forged, sites[0], report, q,
        candidate_id=candidate_id,
        source_ledger_id=dev.context.source_ledger.ledger_id,
    )
    assert validation.failure_code is not None
    assert validation.formal_source_accounting is False


# -- 3. Binding verification on the production path --------------------------


def test_valid_transforms_verify_their_binding():
    for reaction_id in ("fx_oct", "fx_decarb", "fx_hydrolysis", "fx_reduction"):
        t = _extract(reaction_id)
        verify_transform_binding(t)  # must not raise
        assert recompute_transform_preimage(t)


def test_tampered_hash_field_breaks_binding():
    t = _extract("fx_oct")
    forged = t.model_copy(update={"canonical_transform_hash": "forged_hash"})
    with pytest.raises(TransformBindingError):
        verify_transform_binding(forged)
    forged_id = t.model_copy(update={"transformation_id": "tr_forged"})
    with pytest.raises(TransformBindingError):
        verify_transform_binding(forged_id)


# -- 4. Order invariance of equivalent collections ---------------------------


def test_reordering_equivalent_collections_does_not_change_preimage():
    from reaction_agent.p3.transform import canonical_transform_preimage
    t = _extract("fx_hydrolysis")
    base = recompute_transform_preimage(t)
    # Shuffle the preimage input collections; the canonical preimage is the
    # SAME because every collection is canonically sorted.
    shuffled = canonical_transform_preimage(
        selected_lineage_id=t.source_lineage_ids[0],
        source_lineage_hash=t.source_lineage_hash,
        donor_reaction_id=t.donor_reaction_id,
        reaction_authority_hash=t.reaction_authority_hash,
        mapped_edits=list(reversed(t.mapped_atom_edits)),
        bond_changes=list(reversed(t.bond_changes)),
        atom_state_changes=list(reversed(t.atom_state_changes)),
        transferred_atoms=list(reversed(t.transferred_atoms)),
        removed_atom_maps=list(reversed(t.removed_atom_maps)),
        removed_atom_sinks=list(reversed(t.removed_atom_sinks)),
        site_maps=list(reversed(t.donor_site_atom_map_numbers)),
        local_environment=list(reversed(t.local_environment)),
        preconditions=list(reversed(t.strict_preconditions)),
        ledger_requirements=list(reversed(t.ledger_requirements)),
        site_pattern=t.donor_site_pattern,
    )
    assert base == shuffled
