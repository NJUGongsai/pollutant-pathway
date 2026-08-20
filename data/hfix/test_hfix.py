#!/usr/bin/env python3
"""RED -> GREEN tests for M4-A explicit-H -> implicit-H re-encoding.

These tests encode the observed defect (explicit [H] in the reactant SMARTS
never matches an implicit-H SMILES molecule) and assert the re-encoding fix:

  RED   (pre-fix observable): `[#6][H]` matches `CCO` zero times, and the
        original explicit-H SMIRKS cannot match its donor.
  GREEN (post-fix): the re-encoded SMIRKS matches the donor AND preserves the
        round-trip product (hydrogen transfer intact).

No network, no answer key: only reaction_v3 template data + RDKit.
Run:  /opt/anaconda3/bin/python3 -m pytest test_hfix.py -q
"""
from __future__ import annotations

import json
import os

from rdkit import Chem
from rdkit.Chem import AllChem
from rdkit import RDLogger

RDLogger.DisableLog("rdApp.*")

HERE = os.path.dirname(os.path.abspath(__file__))
import sys  # noqa: E402
sys.path.insert(0, HERE)

from reencode import (  # noqa: E402
    load_templates, load_substrates, reencode_smirks,
    apply_rule, apply_rule_explicit_ref,
)


def _canon(smiles):
    m = Chem.MolFromSmiles(smiles)
    return Chem.MolToSmiles(m) if m is not None else None


# ---- RED: the defect ------------------------------------------------------
def test_explicit_H_does_not_match_implicit_molecule():
    """The root cause: `[#6][H]` requires an explicit hydrogen neighbour."""
    cco = Chem.MolFromSmiles("CCO")
    assert len(cco.GetSubstructMatches(Chem.MolFromSmarts("[#6][H]"))) == 0
    assert len(cco.GetSubstructMatches(Chem.MolFromSmarts("[#6]"))) == 2


def test_original_explicit_H_rule_does_not_match_donor():
    """Original alcohol->aldehyde SMIRKS (explicit H) cannot match ethanol."""
    orig = "[H][#8:2][C:1]([H:5])([H])[#1,#6:6]>>[H:5][#6:1](-[#1,#6:6])=[O:2]"
    m = Chem.MolFromSmiles("CCO")
    r = AllChem.ReactionFromSmarts(orig)
    assert not m.HasSubstructMatch(r.GetReactants()[0])


# ---- GREEN: the fix --------------------------------------------------------
def test_reencode_strips_all_explicit_H_both_sides():
    """Re-encoding removes every explicit-H atom from BOTH sides."""
    ns, info = reencode_smirks(
        "[H][#8:2][C:1]([H:5])([H])[#1,#6:6]>>[H:5][#6:1](-[#1,#6:6])=[O:2]")
    assert info["changed"] is True
    assert info["lhs_h"] == 3 and info["rhs_h"] == 1
    assert info["lhs_mapped_h"] == 1  # [H:5] on the educt carbon
    r = AllChem.ReactionFromSmarts(ns)
    for mol in list(r.GetReactants()) + list(r.GetProducts()):
        assert not any(a.GetAtomicNum() == 1 for a in mol.GetAtoms())


def test_reencoded_rule_matches_donor():
    """After re-encoding, the alcohol->aldehyde rule matches its donor."""
    orig = "[H][#8:2][C:1]([H:5])([H])[#1,#6:6]>>[H:5][#6:1](-[#1,#6:6])=[O:2]"
    ns, _ = reencode_smirks(orig)
    m = Chem.MolFromSmiles("CCO")
    r = AllChem.ReactionFromSmarts(ns)
    assert m.HasSubstructMatch(r.GetReactants()[0])


def test_roundtrip_mapped_H_preserves_product():
    """Mapped-H (methyl->hydroxymethyl) round-trip fidelity on tert-butanol."""
    orig = ("[H][C:3]([H:4])([H:5])[#6;$([C]([CH3])-1=[C]-[C]-[C]-[C]-[C]-1),"
            "$([C]([CH3])(-[#6;H3])(-[#6;a])-[#6;a]),"
            "$([C]([CH3])(-[#9,#17,#35,#53])(-[#9,#17,#35,#53])-[#9,#17,#35,#53]),"
            "$([C]([CH3])(-[#6H3])(-[C])-[#6,#8]),"
            "$([C]([CH3])(-[C])=O):6]>>[H:4][C:3]([H:5])([#6:6])O")
    ns, _ = reencode_smirks(orig)
    r_enc = AllChem.ReactionFromSmarts(ns)
    r_orig = AllChem.ReactionFromSmarts(orig)
    donor = "CC(C)(C)O"
    enc = apply_rule(r_enc, donor)
    ref = apply_rule_explicit_ref(r_orig, donor)
    assert "CC(C)(O)CO" in enc
    assert ref == {"CC(C)(O)CO"}


def test_all_286_reencode_parseable_single_reactant():
    """Every re-encoded SMIRKS parses and keeps atom-map core intact."""
    templates = load_templates()
    assert len(templates) == 286
    for d in templates:
        ns, info = reencode_smirks(d["TEMPLATE"])
        assert info["parse_ok"], d["TEMPLATE_ID"]
        r = AllChem.ReactionFromSmarts(ns)
        assert r is not None, d["TEMPLATE_ID"]
        assert r.GetNumReactantTemplates() == 1, d["TEMPLATE_ID"]
        # no explicit H remains on any side
        for mol in list(r.GetReactants()) + list(r.GetProducts()):
            assert not any(a.GetAtomicNum() == 1 for a in mol.GetAtoms()), \
                d["TEMPLATE_ID"]


def test_match_unlock_increases():
    """Matching unlock: strictly more rules match their donor after re-encoding."""
    templates = load_templates()
    subs = load_substrates()
    before = after = 0
    for d in templates:
        donors = subs.get(d["TEMPLATE_ID"], {}).get("substrates", [])
        if not donors:
            continue
        ns, _ = reencode_smirks(d["TEMPLATE"])
        r0 = AllChem.ReactionFromSmarts(d["TEMPLATE"])
        r1 = AllChem.ReactionFromSmarts(ns)
        b = any(Chem.MolFromSmiles(s).HasSubstructMatch(r0.GetReactants()[0])
                for s in donors if Chem.MolFromSmiles(s))
        a = any(Chem.MolFromSmiles(s).HasSubstructMatch(r1.GetReactants()[0])
                for s in donors if Chem.MolFromSmiles(s))
        before += int(b)
        after += int(a)
    assert after > before
    assert after >= 130  # expect strong unlock (52 -> 137)


def test_candidates_hfix_covers_all_83_parents():
    """candidates_hfix.json has all 83 parents with non-empty pools."""
    path = os.path.join(HERE, "candidates_hfix.json")
    assert os.path.exists(path)
    with open(path) as f:
        cands = json.load(f)
    assert len(cands) == 83
    for cid, prods in cands.items():
        assert isinstance(prods, list) and prods, cid