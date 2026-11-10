"""Atom-atom mapping (AAM) for single-reactant RHEA reactions.

M1 (MASTER_PLAN §5): prove RHEA reactions CAN be atom-mapped before any transfer.

Two acceptance checks, computed here with NO answer-key access:

1. round-trip gate          -- structural bijection of map numbers (reactant <-> product):
   every non-zero product map id appears in reactants, no dangling map, no atom left
   at map 0, no duplicate map ids within a side.

2. changed-atom coverage     -- SELF-FLAG heuristic (official chemical verdict is CC's
   independent spot-check). The persistent reaction-centre atoms are located
   mapper-independently (rdRascalMCES + local-bond-environment diff). Coverage =
   fraction of those centre atoms whose RXNMapper map number is non-zero and matched
   across the arrow to an atom of the same element. Atoms that are genuinely added or
   removed (no counterpart across the arrow) are reported separately and excluded from
   the denominator, because a missing counterpart is not a mapping error. A value < 1
   flags "mapper mapped the backbone but missed/blemished the centre". It does NOT
   catch permutation errors among same-element atoms; that is exactly what CC's manual
   spot-check owns.

Determinism: CPU inference, torch single-threaded, fixed seed, dropout forced off via
``model.eval()``. The double-run byte-identity is reported by the driver, not promised here.
"""
from __future__ import annotations

import json
import logging
from typing import Dict, List, Optional, Set, Tuple

from rdkit import Chem
from rdkit.Chem import rdRascalMCES

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# sampling (deterministic)
# --------------------------------------------------------------------------- #
def sample_single_reactant_rows(
    corpus_path: str, n: int = 500, source_type: str = "rhea"
) -> List[dict]:
    """First-N single-reactant `source_type` records by (source_id, record_id).

    Deterministic by construction: fixed sort, no randomness. Rows are the raw
    corpus dicts (reaction_smiles is the field RXNMapper consumes).
    """
    rows: List[dict] = []
    with open(corpus_path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            if rec.get("source_type") != source_type:
                continue
            if len(rec.get("donor_components") or []) != 1:
                continue
            if not rec.get("reaction_smiles"):
                continue
            rows.append(rec)
    rows.sort(key=lambda r: (r.get("source_id") or "", r.get("record_id") or ""))
    return rows[:n]


def is_element_conserved(reaction_smiles: str) -> Optional[bool]:
    """True iff the reactant and product carry the same heavy-atom element counts."""
    if ">>" not in reaction_smiles:
        return None
    lhs, rhs = reaction_smiles.split(">>", 1)
    m1, m2 = Chem.MolFromSmiles(lhs), Chem.MolFromSmiles(rhs)
    if m1 is None or m2 is None:
        return None

    def counts(mol):
        c: dict = {}
        for a in mol.GetAtoms():
            c[a.GetAtomicNum()] = c.get(a.GetAtomicNum(), 0) + 1
        return c

    return counts(m1) == counts(m2)


# --------------------------------------------------------------------------- #
# round-trip gate
# --------------------------------------------------------------------------- #
def _side_map_numbers(smiles: str) -> Optional[Tuple[List[int], object]]:
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    return [a.GetAtomMapNum() for a in mol.GetAtoms()], mol


def roundtrip_check(mapped_reaction_smiles: str) -> Tuple[bool, dict]:
    """Structural round-trip gate over a mapped reaction SMILES.

    Returns (pass, detail). Pass requires:
      * both sides parse,
      * no atom left at map 0 on either side,
      * the SET of non-zero map ids is identical across the arrow (no dangling id),
      * no duplicate non-zero map id within either side.
    """
    if ">>" not in mapped_reaction_smiles:
        return False, {"error": "no_arrow"}
    lhs, rhs = mapped_reaction_smiles.split(">>", 1)
    parsed = _side_map_numbers(lhs)
    parsed_p = _side_map_numbers(rhs)
    if parsed is None or parsed_p is None:
        return False, {"error": "unparseable_side"}
    rmap, _ = parsed
    pmap, _ = parsed_p
    r_nonzero = [m for m in rmap if m != 0]
    p_nonzero = [m for m in pmap if m != 0]
    rset, pset = set(r_nonzero), set(p_nonzero)
    dangling = sorted((pset - rset) | (rset - pset))
    n_reactant_unmapped = sum(1 for m in rmap if m == 0)
    n_product_unmapped = sum(1 for m in pmap if m == 0)
    n_reactant_dup = len(r_nonzero) - len(rset)
    n_product_dup = len(p_nonzero) - len(pset)
    ok = (
        n_reactant_unmapped == 0
        and n_product_unmapped == 0
        and not dangling
        and n_reactant_dup == 0
        and n_product_dup == 0
        and rset == pset
    )
    detail = {
        "n_reactant_atoms": len(rmap),
        "n_product_atoms": len(pmap),
        "n_reactant_unmapped": n_reactant_unmapped,
        "n_product_unmapped": n_product_unmapped,
        "n_reactant_dup_map_ids": n_reactant_dup,
        "n_product_dup_map_ids": n_product_dup,
        "dangling_map_ids": dangling,
    }
    return ok, detail


# --------------------------------------------------------------------------- #
# changed-atom coverage (self-flag)
# --------------------------------------------------------------------------- #
def _atom_env(mol, idx: int) -> tuple:
    a = mol.GetAtomWithIdx(idx)
    bonds = sorted(
        (
            round(b.GetBondTypeAsDouble(), 1),
            mol.GetAtomWithIdx(b.GetOtherAtomIdx(idx)).GetAtomicNum(),
        )
        for b in a.GetBonds()
    )
    return (
        a.GetAtomicNum(),
        a.GetFormalCharge(),
        int(a.GetIsAromatic()),
        a.GetTotalNumHs(),
        tuple(bonds),
    )


def _match_by_element(rem_r, rem_p, r_mol, p_mol) -> Tuple[List[Tuple[int, int]], Set[int], Set[int]]:
    """Pair leftover reactant atoms to leftover product atoms by atomic number.

    Greedy, deterministic (both lists sorted by local environment). Atoms that stay
    unpaired (no same-element counterpart) are genuinely removed/added.
    """
    from collections import defaultdict

    r_by_el = defaultdict(list)
    p_by_el = defaultdict(list)
    for i in rem_r:
        r_by_el[r_mol.GetAtomWithIdx(i).GetAtomicNum()].append(i)
    for j in rem_p:
        p_by_el[p_mol.GetAtomWithIdx(j).GetAtomicNum()].append(j)
    pairs: List[Tuple[int, int]] = []
    removed: Set[int] = set()
    added: Set[int] = set()
    for el in set(r_by_el) | set(p_by_el):
        rl = sorted(r_by_el.get(el, []), key=lambda i: _atom_env(r_mol, i))
        pl = sorted(p_by_el.get(el, []), key=lambda j: _atom_env(p_mol, j))
        n = min(len(rl), len(pl))
        pairs.extend((rl[k], pl[k]) for k in range(n))
        removed.update(rl[n:])
        added.update(pl[n:])
    return pairs, removed, added


def _fmcs_correspondence(r_mol, p_mol) -> Optional[List[Tuple[int, int]]]:
    """Element+any-bond MCS atom correspondence (fallback when MCES fails)."""
    from rdkit.Chem import rdFMCS

    mcs = rdFMCS.FindMCS(
        [r_mol, p_mol],
        atomCompare=rdFMCS.AtomCompare.CompareElements,
        bondCompare=rdFMCS.BondCompare.CompareAny,
        ringMatchesRingOnly=True,
        completeRingsOnly=False,
        timeout=10,
    )
    if mcs is None or mcs.numAtoms < 1:
        return None
    query = Chem.MolFromSmarts(mcs.smartsString)
    if query is None:
        return None
    match_r = r_mol.GetSubstructMatch(query)
    match_p = p_mol.GetSubstructMatch(query)
    if not match_r or not match_p or len(match_r) != len(match_p):
        return None
    return list(zip(match_r, match_p))


def reaction_center(r_mol, p_mol) -> Tuple[Set[int], Set[int], Set[int], Set[int], str]:
    """Reaction centre located mapper-independently.

    Returns (center_r, center_p, removed_r, added_p, status):
      * center_* -- atoms that persist across the arrow but whose local bond
        environment (element, formal charge, aromaticity, total H, sorted
        (bond-order, neighbour-element) multiset) differs.
      * removed_r -- reactant atoms with no same-element counterpart.
      * added_p   -- product atoms with no same-element counterpart.

    Two-stage reference:
      1. rdRascalMCES aligns the unchanged backbone (common edge subgraph). If MCES
         yields nothing / times out (large symmetric polyenes), fall back to an
         element+any-bond rdFMCS correspondence. Matched atoms whose environment
         differs, plus unmatched-but-persistent atoms, are the centre.
      2. Atoms unmatched by the backbone correspondence (e.g. the N=C=S -> N#C-S
         1,3-rearrangement where the whole terminal group's edges change) are re-paired
         by atomic number, so a pure rearrangement is read as 'centre', not add/remove.
    """
    if r_mol.GetNumAtoms() == 0 or p_mol.GetNumAtoms() == 0:
        return set(), set(), set(), set(), "empty_mol"
    if r_mol.GetNumAtoms() > 300 or p_mol.GetNumAtoms() > 300:
        return set(), set(), set(), set(), "too_large"

    atom_matches: Optional[List[Tuple[int, int]]] = None
    try:
        solutions = rdRascalMCES.FindMCES(r_mol, p_mol)
        if solutions:
            result = solutions[0]
            if not getattr(result, "timedOut", False):
                atom_matches = result.atomMatches()
    except Exception as exc:  # noqa: BLE001 -- fail-closed ledger
        atom_matches = None
    if not atom_matches:
        try:
            atom_matches = _fmcs_correspondence(r_mol, p_mol)
        except Exception:  # noqa: BLE001
            atom_matches = None
    if not atom_matches:
        return set(), set(), set(), set(), "no_correspondence"

    matched_r = {i for i, _ in atom_matches}
    matched_p = {j for _, j in atom_matches}
    center_r: Set[int] = set()
    center_p: Set[int] = set()
    for i, j in atom_matches:
        if _atom_env(r_mol, i) != _atom_env(p_mol, j):
            center_r.add(i)
            center_p.add(j)

    rem_r = {i for i in range(r_mol.GetNumAtoms()) if i not in matched_r}
    rem_p = {j for j in range(p_mol.GetNumAtoms()) if j not in matched_p}
    pairs, removed_r, added_p = _match_by_element(rem_r, rem_p, r_mol, p_mol)
    for i, j in pairs:
        center_r.add(i)
        center_p.add(j)
    return center_r, center_p, removed_r, added_p, "ok"


def _strip_mapnums(mol):
    stripped = Chem.Mol(mol)
    for a in stripped.GetAtoms():
        a.SetAtomMapNum(0)
    return stripped


def _align_atoms(ref_mol, stripped_mapped_mol) -> Dict[int, int]:
    """Map {ref_atom_idx: mapped_atom_idx} by canonical ranking (same molecule)."""
    r_ref = list(Chem.CanonicalRankAtoms(ref_mol, breakTies=True))
    r_map = list(Chem.CanonicalRankAtoms(stripped_mapped_mol, breakTies=True))
    rank_to_mapped = {rank: idx for idx, rank in enumerate(r_map)}
    return {i: rank_to_mapped[r_ref[i]] for i in range(ref_mol.GetNumAtoms())}


def changed_atom_coverage(reaction_smiles: str, mapped_reaction_smiles: str) -> dict:
    """Coverage of the persistent reaction centre by RXNMapper map numbers.

    Returns dict with ``coverage`` (None if not computable), ``status``,
    ``changed_reactant``, ``changed_product``, ``covered``, ``removed_atoms``,
    ``added_atoms``, ``center_status``.
    """
    empty = {
        "coverage": None,
        "status": "failed",
        "changed_reactant": None,
        "changed_product": None,
        "covered": None,
        "removed_atoms": None,
        "added_atoms": None,
        "center_status": None,
    }
    try:
        if ">>" not in reaction_smiles or ">>" not in mapped_reaction_smiles:
            return dict(empty, status="no_arrow")
        r = Chem.MolFromSmiles(reaction_smiles.split(">>", 1)[0])
        p = Chem.MolFromSmiles(reaction_smiles.split(">>", 1)[1])
        mr = Chem.MolFromSmiles(mapped_reaction_smiles.split(">>", 1)[0])
        mp = Chem.MolFromSmiles(mapped_reaction_smiles.split(">>", 1)[1])
    except Exception:  # noqa: BLE001
        return dict(empty, status="split_error")
    if any(m is None for m in (r, p, mr, mp)):
        return dict(empty, status="parse_error")

    center_r, center_p, removed_r, added_p, cstatus = reaction_center(r, p)
    if cstatus != "ok":
        return dict(empty, status=cstatus)

    stripped_r = _strip_mapnums(mr)
    stripped_p = _strip_mapnums(mp)
    mapnum_r = {i: mr.GetAtomWithIdx(i).GetAtomMapNum() for i in range(mr.GetNumAtoms())}
    mapnum_p = {i: mp.GetAtomWithIdx(i).GetAtomMapNum() for i in range(mp.GetNumAtoms())}
    try:
        align_r = _align_atoms(r, stripped_r)
        align_p = _align_atoms(p, stripped_p)
    except Exception:  # noqa: BLE001
        return dict(empty, status="align_error")

    def counterpart_is_same_element(mapped_mol, own_idx, other_mol, other_mapnums):
        m = mapped_mol.GetAtomWithIdx(own_idx).GetAtomMapNum()
        if m is None or m <= 0 or m not in other_mapnums:
            return False
        own_el = mapped_mol.GetAtomWithIdx(own_idx).GetAtomicNum()
        for j in range(other_mol.GetNumAtoms()):
            if other_mol.GetAtomWithIdx(j).GetAtomMapNum() == m:
                return other_mol.GetAtomWithIdx(j).GetAtomicNum() == own_el
        return False

    covered = 0
    for i in center_r:
        if counterpart_is_same_element(mr, align_r[i], mp, set(mapnum_p.values())):
            covered += 1
    for j in center_p:
        if counterpart_is_same_element(mp, align_p[j], mr, set(mapnum_r.values())):
            covered += 1

    total = len(center_r) + len(center_p)
    coverage = (covered / total) if total else None
    status = "ok" if coverage is not None else "no_center"
    return {
        "coverage": coverage,
        "status": status,
        "changed_reactant": len(center_r),
        "changed_product": len(center_p),
        "covered": covered,
        "removed_atoms": len(removed_r),
        "added_atoms": len(added_p),
        "center_status": cstatus,
    }


# --------------------------------------------------------------------------- #
# RXNMapper runner (lazy import -> module importable without torch)
# --------------------------------------------------------------------------- #
class Mapper:
    """Thin, deterministic wrapper around ``rxnmapper.RXNMapper`` (CPU)."""

    def __init__(self, seed: int = 0, model_eval: bool = True):
        import numpy as np
        import torch

        torch.set_num_threads(1)
        torch.manual_seed(seed)
        np.random.seed(seed)
        from rxnmapper import RXNMapper

        self._mapper = RXNMapper()
        self._mapper.logger.setLevel(logging.ERROR)
        if model_eval:
            # force dropout off -> deterministic forward-pass (see module docstring)
            self._mapper.model.eval()

    def map(self, reaction_smiles: str) -> Tuple[str, float]:
        out = self._mapper.get_attention_guided_atom_maps(
            [reaction_smiles], canonicalize_rxns=True
        )[0]
        return out["mapped_rxn"], float(out["confidence"])


def map_row(row: dict, mapper: Mapper) -> dict:
    """Map one corpus row; return the per-reaction AAM record (fail-closed)."""
    rec = {
        "record_id": row.get("record_id"),
        "source_id": row.get("source_id"),
        "reaction_smiles": row.get("reaction_smiles"),
        "element_conserved": is_element_conserved(row.get("reaction_smiles") or ""),
        "status": "failed",
        "mapped_reaction_smiles": None,
        "mapper_confidence": None,
        "error": None,
        "roundtrip_pass": None,
        "roundtrip_detail": None,
        "changed_atom_coverage": None,
        "changed_atom_detail": None,
    }
    rxn = row.get("reaction_smiles")
    try:
        mapped_rxn, confidence = mapper.map(rxn)
        rec["mapped_reaction_smiles"] = mapped_rxn
        rec["mapper_confidence"] = confidence
        rec["status"] = "ok"
    except Exception as exc:  # noqa: BLE001 -- fail-closed, honest error
        rec["error"] = f"{type(exc).__name__}: {str(exc)[:300]}"
        return rec

    # round-trip gate
    ok, detail = roundtrip_check(mapped_rxn)
    rec["roundtrip_pass"] = ok
    rec["roundtrip_detail"] = detail

    # changed-atom coverage (self-flag)
    cov = changed_atom_coverage(rxn, mapped_rxn)
    rec["changed_atom_coverage"] = cov["coverage"]
    rec["changed_atom_detail"] = {
        k: cov[k]
        for k in (
            "status",
            "changed_reactant",
            "changed_product",
            "covered",
            "removed_atoms",
            "added_atoms",
        )
    }
    return rec