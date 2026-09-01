#!/usr/bin/env python3
"""M4-A: explicit-H -> implicit-H re-encoding for enviPath SMIRKS templates.

The enviPath/EAWAG-BBD rule library writes explicit hydrogen atoms `[H]`/`[#1]`
(and mapped `[H:n]`) in its reactant SMARTS. RDKit SMARTS `[#6][H]` matches only
molecules with an *explicit* hydrogen neighbour, so it never matches implicit-H
SMILES substrates. This module strips those explicit H atoms from BOTH sides of
each SMIRKS so RDKit's implicit-H model takes over, while keeping atom maps
aligned and the transfer semantics intact.

Strategy (per task spec):
  1. unmapped spectator/leaving `[H]`  -> delete the H node + its bond.
  2. mapped `[H:n]`                    -> delete on BOTH sides (atom map dies with
                                          the H node); the implicit H count on the
                                          parent atom is recomputed by RDKit.
  3. never delete an educt H without its product counterpart; never change the
     hydrogen-transfer semantics.

Implementation uses RDKit ReactionFromSmarts (not text regex): parse both sides,
remove every atomic-number-1 atom from every reactant/product mol, rebuild the
SMIRKS with MolToSmarts.
"""
from __future__ import annotations

import gzip
import json
from typing import Iterable

from rdkit import Chem
from rdkit.Chem import AllChem
from rdkit import RDLogger

RDLogger.DisableLog("rdApp.*")

TSV_PATH = ("/Volumes/CC/Enzyme_Agent/depending/"
            "reaction_v3/data/lib_envipath/templates.tsv.gz")
SUBSTRATE_PATH = ("/Volumes/CC/Enzyme_Agent/depending/"
                  "reaction_v3/data/lib_envipath/source_substrates.json")
HEADER = [
    "TEMPLATE_ID", "SCORE", "TEMPLATE", "REACTIONS", "RADII", "REACTIONS_COUNT",
    "ECS", "ECS_COUNT", "RADIUS_MIN", "RADIUS_MAX", "VALID", "DATASETS",
]


def load_templates(path: str = TSV_PATH) -> list[dict]:
    """Return the 286 templates as dicts (TSV header-mapped)."""
    with gzip.open(path, "rt", encoding="utf-8") as f:
        raw = f.read()
    lines = [ln for ln in raw.split("\n") if ln.strip()]
    header = lines[0].split("\t")
    out = []
    for ln in lines[1:]:
        flds = ln.split("\t")
        if len(flds) < 3:
            continue
        d = dict(zip(header, flds))
        if d.get("TEMPLATE"):
            out.append(d)
    return out


def load_substrates(path: str = SUBSTRATE_PATH) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def mol_explicit_h(mol: Chem.Mol) -> list[int]:
    """Atom indices of explicit hydrogen atoms (atomic number 1) in `mol`."""
    return [a.GetIdx() for a in mol.GetAtoms() if a.GetAtomicNum() == 1]


def has_explicit_h(mol: Chem.Mol) -> bool:
    return any(a.GetAtomicNum() == 1 for a in mol.GetAtoms())


def strip_explicit_h(mol: Chem.Mol) -> Chem.Mol:
    """Return a copy of `mol` with all explicit-H atoms removed."""
    rw = Chem.RWMol(mol)
    for idx in sorted([a.GetIdx() for a in rw.GetAtoms()
                       if a.GetAtomicNum() == 1], reverse=True):
        rw.RemoveAtom(idx)
    return rw.GetMol()


def count_side_h(rxn) -> tuple[int, int, int, int]:
    """(lhs_total_H, rhs_total_H, lhs_mapped_H, rhs_mapped_H)."""
    lt = sum(1 for m in rxn.GetReactants() for a in m.GetAtoms()
             if a.GetAtomicNum() == 1)
    rt = sum(1 for m in rxn.GetProducts() for a in m.GetAtoms()
             if a.GetAtomicNum() == 1)
    lm = sum(1 for m in rxn.GetReactants() for a in m.GetAtoms()
             if a.GetAtomicNum() == 1 and a.GetAtomMapNum() != 0)
    rm = sum(1 for m in rxn.GetProducts() for a in m.GetAtoms()
             if a.GetAtomicNum() == 1 and a.GetAtomMapNum() != 0)
    return lt, rt, lm, rm


def reencode_smirks(smirks: str) -> tuple[str | None, dict]:
    """Re-encode one SMIRKS to implicit-H form.

    Returns (new_smirks_or_None, info). info = {changed, lhs_h, rhs_h,
    lhs_mapped_h, rhs_mapped_h, parse_ok}. If the reaction is unparseable,
    returns (None, info).
    """
    info = {"changed": False, "lhs_h": 0, "rhs_h": 0,
            "lhs_mapped_h": 0, "rhs_mapped_h": 0, "parse_ok": False}
    rxn = AllChem.ReactionFromSmarts(smirks)
    if rxn is None:
        return None, info
    info["parse_ok"] = True
    lt, rt, lm, rm = count_side_h(rxn)
    info["lhs_h"], info["rhs_h"], info["lhs_mapped_h"], info["rhs_mapped_h"] = \
        lt, rt, lm, rm
    if lt == 0 and rt == 0:
        return smirks, info  # already implicit-H
    info["changed"] = True
    lhs = [Chem.MolToSmarts(strip_explicit_h(m)) for m in rxn.GetReactants()]
    rhs = [Chem.MolToSmarts(strip_explicit_h(m)) for m in rxn.GetProducts()]
    return ".".join(lhs) + ">>" + ".".join(rhs), info


def canon(smiles: str) -> str | None:
    m = Chem.MolFromSmiles(smiles)
    return Chem.MolToSmiles(m) if m is not None else None


def apply_rule(rxn, smiles: str) -> set[str]:
    """Apply a reaction to one smiles; return canonical products (all mols)."""
    m = Chem.MolFromSmiles(smiles)
    if m is None:
        return set()
    if not m.HasSubstructMatch(rxn.GetReactants()[0]):
        return set()
    out: set[str] = set()
    for ps in rxn.RunReactants((m,)):
        for p in ps:
            try:
                Chem.SanitizeMol(p)
                out.add(Chem.MolToSmiles(p))
            except Exception:
                pass
    return out


def apply_rule_explicit_ref(rxn, smiles: str) -> set[str]:
    """Reference: run the ORIGINAL (explicit-H) rule on an AddHs'd molecule,
    then RemoveHs the products. Yields the ground-truth product set for
    round-trip verification (independent of the implicit-H re-encoding)."""
    m = Chem.MolFromSmiles(smiles)
    if m is None:
        return set()
    mh = Chem.AddHs(m)
    if not mh.HasSubstructMatch(rxn.GetReactants()[0]):
        return set()
    out: set[str] = set()
    for ps in rxn.RunReactants((mh,)):
        for p in ps:
            try:
                Chem.SanitizeMol(p)
                p2 = Chem.RemoveHs(p)
                out.add(Chem.MolToSmiles(p2))
            except Exception:
                pass
    return out


def reactant_matches(rxn, smiles: str) -> bool:
    m = Chem.MolFromSmiles(smiles)
    if m is None:
        return False
    return m.HasSubstructMatch(rxn.GetReactants()[0])