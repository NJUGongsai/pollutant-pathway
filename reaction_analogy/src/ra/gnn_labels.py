"""Route B Phase-1 label derivation — mapper-independent, deterministic.

Given an (UNMAPPED) reaction SMILES ``lhs>>rhs``, derive the per-substrate GNN
labels:

* ``reacted_atoms``  -- substrate atom indices whose bonding/valence/pH changes
* ``reaction_class`` -- deterministic coarse class from the SUBSTRATE's changed
  bonds (cofactor/agent changes are excluded)
* ``changed_bonds``  -- canonical broken/formed bond summary (for audit + class)

Correspondence across the arrow is FMCS (element + any-bond, 1s timeout), never
rxnmapper map numbers (rxnmapper numbers are not reliably consistent across the
arrow for symmetric/aromatic moieties, and produce spurious bond breakage).
rxnmapper is used only for ``mapped_reaction_smiles`` + confidence stratification.

Substrate = the reactant component (connected fragment) with the most reacted
atoms; size-tie-break, then ambiguous (genuine condensation) → skip honestly.

Reaction class is computed on SUBSTRATE-LOCAL events only: cofactor redox
(e.g. NAD+/NADH aromatic ring change) must not leak into the substrate's class.
"""
from __future__ import annotations

from collections import Counter
from typing import Dict, List, Optional, Tuple

from rdkit import Chem
from rdkit.Chem import rdFMCS, rdMolDescriptors

PERIODIC = Chem.GetPeriodicTable()
_ORDER_SYM = {1.0: "-", 1.5: ":", 2.0: "=", 3.0: "#"}
_HALOGENS = {9: "F", 17: "Cl", 35: "Br", 53: "I"}


def el(z: int) -> str:
    return PERIODIC.GetElementSymbol(z)


def bond_label(order: float, z1: int, z2: int) -> str:
    lo, hi = (z1, z2) if z1 <= z2 else (z2, z1)
    return f"{_ORDER_SYM.get(order, '~' + str(order))}{el(lo)}-{el(hi)}"


def _submol(mol: Chem.Mol, atom_indices) -> Chem.Mol:
    """Extract the sub-molecule over `atom_indices` (RWMol atom removal).

    NOT Chem.PathToSubmol (a bond-path extractor). Keeps ascending global order,
    so ``submol atom k`` corresponds to ``sorted(atom_indices)[k]``.
    """
    atoms = sorted(set(int(i) for i in atom_indices))
    rw = Chem.RWMol(mol)
    for idx in sorted(set(range(mol.GetNumAtoms())) - set(atoms), reverse=True):
        rw.RemoveAtom(idx)
    return rw.GetMol()


def _n_aromatic(mol: Chem.Mol) -> int:
    return sum(1 for b in mol.GetBonds() if b.GetIsAromatic())


# --------------------------------------------------------------------------- #
# env + correspondence
# --------------------------------------------------------------------------- #
def _atom_env(mol: Chem.Mol, idx: int) -> tuple:
    a = mol.GetAtomWithIdx(idx)
    bonds = sorted(
        (
            round(b.GetBondTypeAsDouble(), 2),
            mol.GetAtomWithIdx(b.GetOtherAtomIdx(idx)).GetAtomicNum(),
            int(b.GetStereo()),
        )
        for b in a.GetBonds()
    )
    return (
        a.GetAtomicNum(),
        int(a.GetFormalCharge()),
        int(a.GetIsAromatic()),
        int(a.GetTotalNumHs()),
        int(a.GetChiralTag()),
        tuple(bonds),
    )


def _bond_labels(a: Chem.Atom, mol: Chem.Mol) -> list:
    return [
        bond_label(round(b.GetBondTypeAsDouble(), 2), a.GetAtomicNum(),
                   mol.GetAtomWithIdx(b.GetOtherAtomIdx(a.GetIdx())).GetAtomicNum())
        for b in a.GetBonds()
    ]


def _fmcs_correspondence(r_mol, p_mol) -> Optional[List[Tuple[int, int]]]:
    mcs = rdFMCS.FindMCS(
        [r_mol, p_mol],
        atomCompare=rdFMCS.AtomCompare.CompareElements,
        bondCompare=rdFMCS.BondCompare.CompareAny,
        ringMatchesRingOnly=True,
        completeRingsOnly=False,
        timeout=1,
    )
    if mcs is None or getattr(mcs, "canceled", False) or mcs.numAtoms < 1:
        # fail-closed (1c): a timed-out MCS is a partial/unreliable correspondence
        return None
    q = Chem.MolFromSmarts(mcs.smartsString)
    if q is None:
        return None
    mr = r_mol.GetSubstructMatch(q)
    mp = p_mol.GetSubstructMatch(q)
    if not mr or not mp or len(mr) != len(mp):
        return None
    return list(zip(mr, mp))


def _correspondence(r_mol, p_mol) -> Optional[List[Tuple[int, int]]]:
    if r_mol.GetNumAtoms() == 0 or p_mol.GetNumAtoms() == 0:
        return None
    if r_mol.GetNumAtoms() > 300 or p_mol.GetNumAtoms() > 300:
        return None
    return _fmcs_correspondence(r_mol, p_mol)


def _match_by_element(rem_r: List[int], rem_p: List[int], r_mol, p_mol):
    """Pair leftover reactant/product atoms by atomic number (greedy, deterministic)."""
    from collections import defaultdict

    r_by = defaultdict(list)
    p_by = defaultdict(list)
    for i in rem_r:
        r_by[r_mol.GetAtomWithIdx(i).GetAtomicNum()].append(i)
    for j in rem_p:
        p_by[p_mol.GetAtomWithIdx(j).GetAtomicNum()].append(j)
    pairs: List[Tuple[int, int]] = []
    removed: set = set()
    added: set = set()
    for z in set(r_by) | set(p_by):
        rl = sorted(r_by.get(z, []), key=lambda i: _atom_env(r_mol, i))
        pl = sorted(p_by.get(z, []), key=lambda j: _atom_env(p_mol, j))
        n = min(len(rl), len(pl))
        pairs.extend((rl[k], pl[k]) for k in range(n))
        removed.update(rl[n:])
        added.update(pl[n:])
    return pairs, removed, added


# --------------------------------------------------------------------------- #
# full-reaction events (for substrate selection)
# --------------------------------------------------------------------------- #
def reaction_events(reaction_smiles: str) -> Optional[dict]:
    """Full-reaction reacted atoms + correspondence (mapper-independent)."""
    if ">>" not in reaction_smiles:
        return None
    lhs, rhs = reaction_smiles.split(">>", 1)
    r_mol = Chem.MolFromSmiles(lhs)
    p_mol = Chem.MolFromSmiles(rhs)
    if r_mol is None or p_mol is None:
        return None
    matches = _correspondence(r_mol, p_mol)
    if not matches:
        return None
    r_to_p = dict(matches)
    p_to_r = {p: r for r, p in matches}
    rem_r = [i for i in range(r_mol.GetNumAtoms()) if i not in r_to_p]
    rem_p = [j for j in range(p_mol.GetNumAtoms()) if j not in p_to_r]
    pairs, removed, added = _match_by_element(rem_r, rem_p, r_mol, p_mol)
    for i, j in pairs:
        r_to_p[i] = j
        p_to_r[j] = i
    reacted_r = {i for i, j in r_to_p.items() if _atom_env(r_mol, i) != _atom_env(p_mol, j)}
    reacted_r |= removed  # 1a: leaving-group atoms are reaction centres too
    return {
        "reacted_r": sorted(reacted_r),
        "removed_r": sorted(removed),
        "added_p": sorted(added),
        "r_to_p": r_to_p,
        "p_to_r": p_to_r,
    }


# --------------------------------------------------------------------------- #
# substrate selection
# --------------------------------------------------------------------------- #
def _pick_substrate(r_mol: Chem.Mol, reacted: set, cofactor_set=None):
    """Return (canonical_smiles, reacted_canon_indices, status, frag_global).

    Cofactor components (canonical SMILES in ``cofactor_set``) are excluded from
    substrate candidacy whenever a non-cofactor candidate has reacted atoms —
    this keeps NAD+/H2O/O2/ATP from being mis-read as the main substrate in
    coupled reactions. Fall back to the full pool only when every candidate is a
    cofactor.
    """
    frags = Chem.GetMolFrags(r_mol)
    if not frags:
        return None, None, "empty", None
    scored = []
    for frag in frags:
        sub = _submol(r_mol, frag)
        canon = Chem.MolToSmiles(sub)
        is_cof = bool(cofactor_set) and canon in cofactor_set
        scored.append((frag, len([i for i in frag if i in reacted]), canon, is_cof, sub))
    noncof = [s for s in scored if not s[3]]
    pool = noncof if noncof else scored
    max_r = max(s[1] for s in pool)
    if max_r == 0:
        return None, None, "no_reacted", None
    top = [s for s in pool if s[1] == max_r]
    if len(top) == 1:
        best = top[0]
    else:
        max_sz = max(len(s[0]) for s in top)
        top2 = [s for s in top if len(s[0]) == max_sz]
        if len(top2) == 1:
            best = top2[0]
        else:
            return None, None, "ambiguous", None

    frag, _, canon, _, sub_mol = best
    canon_mol = Chem.MolFromSmiles(canon)
    if canon_mol is None:
        return None, None, "align_failed", None
    frag_rank = list(Chem.CanonicalRankAtoms(sub_mol, breakTies=True))
    canon_rank = list(Chem.CanonicalRankAtoms(canon_mol, breakTies=True))
    rank_to_canon = {r: i for i, r in enumerate(canon_rank)}
    reacted_local = [k for k, g in enumerate(frag) if g in reacted]
    reacted_canon = sorted(rank_to_canon[frag_rank[k]] for k in reacted_local)
    return canon, reacted_canon, "ok", frag


def pick_substrate(reaction_smiles: str, events: dict) -> Tuple[Optional[str], Optional[list], str]:
    """Back-compat wrapper around _pick_substrate."""
    r_mol = Chem.MolFromSmiles(reaction_smiles.split(">>", 1)[0])
    if r_mol is None:
        return None, None, "empty"
    canon, indices, status, _ = _pick_substrate(r_mol, set(events.get("reacted_r", [])))
    return canon, indices, status


# --------------------------------------------------------------------------- #
# substrate-local events
# --------------------------------------------------------------------------- #
def _substrate_events(r_mol, p_mol, frag, r_to_p, p_to_r) -> dict:
    broken: Counter = Counter()
    formed: Counter = Counter()
    delta_H = 0
    removed_elems: List[str] = []
    for i in frag:
        ra = r_mol.GetAtomWithIdx(i)
        j = r_to_p.get(i)
        if j is None:
            removed_elems.append(el(ra.GetAtomicNum()))
            continue
        pa = p_mol.GetAtomWithIdx(j)
        delta_H += int(pa.GetTotalNumHs()) - int(ra.GetTotalNumHs())
        rb = Counter(_bond_labels(ra, r_mol))
        pb = Counter(_bond_labels(pa, p_mol))
        broken.update(rb - pb)
        formed.update(pb - rb)

    sub_img = {r_to_p[i] for i in frag if i in r_to_p}
    added_set: set = set()
    for j in sub_img:
        pa = p_mol.GetAtomWithIdx(j)
        for b in pa.GetBonds():
            o = b.GetOtherAtomIdx(j)
            if o in sub_img:
                continue
            if p_to_r.get(o) is None:  # no reactant preimage -> newly added
                added_set.add(o)
    added_elems = [el(p_mol.GetAtomWithIdx(o).GetAtomicNum()) for o in added_set]

    sub_r = _submol(r_mol, frag)
    sub_p = _submol(p_mol, sub_img | added_set)
    for m in (sub_r, sub_p):
        m.UpdatePropertyCache(strict=False)
        Chem.GetSymmSSSR(m)  # force ring perception (RWMol output lacks RingInfo)
    return {
        "broken": broken,
        "formed": formed,
        "delta_H": delta_H,
        "removed_elements": removed_elems,
        "added_elements": added_elems,
        "n_aromatic_bonds_reactant": _n_aromatic(sub_r),
        "n_aromatic_bonds_product": _n_aromatic(sub_p),
        "n_rings_reactant": rdMolDescriptors.CalcNumRings(sub_r),
        "n_rings_product": rdMolDescriptors.CalcNumRings(sub_p),
    }


# --------------------------------------------------------------------------- #
# coarse reaction classification
# --------------------------------------------------------------------------- #
def classify(events: dict) -> str:
    broken = events["broken"]
    formed = events["formed"]
    dh = events["delta_H"]
    rem = Counter(events["removed_elements"])
    add = Counter(events["added_elements"])
    ar_r = events.get("n_aromatic_bonds_reactant", 0)
    ar_p = events.get("n_aromatic_bonds_product", 0)
    rings_r = events.get("n_rings_reactant", 0)
    rings_p = events.get("n_rings_product", 0)

    c_o_broken = broken["-C-O"] + broken["=C-O"]
    c_o_formed = formed["-C-O"] + formed["=C-O"]
    c_n_broken = broken["-C-N"] + broken["=C-N"]
    c_x_broken = sum(broken.get(f"-C-{x}", 0) for x in _HALOGENS.values())
    n_o_broken = broken["-N-O"] + broken["=N-O"]

    # stereo-only change: no explicit bond/charge/H/ring change at all
    if (not broken and not formed and not rem and not add and dh == 0
            and ar_r == ar_p and rings_r == rings_p):
        return "stereoisomerization"

    if (broken["-C-C"] > 0 or broken["=C-C"] > 0) and rem["C"] >= 1 and rem["O"] >= 2:
        return "decarboxylation"
    if rings_r > rings_p:
        return "ring_opening"
    if rings_r < rings_p:
        return "ring_closure"
    if ar_r > ar_p:
        return "aromatic_hydrogenation"
    if ar_r < ar_p:
        return "aromatization"
    if broken["-C-O"] > 0 and formed["=C-O"] > 0:
        return "alcohol_oxidation"
    if broken["=C-O"] > 0 and formed["-C-O"] > 0:
        return "carbonyl_reduction"
    if c_x_broken > 0 and c_o_formed == 0 and dh > 0:
        return "reductive_dehalogenation"
    if c_x_broken > 0 and c_o_formed > 0:
        return "hydrolytic_dehalogenation"
    if c_n_broken > 0 and c_o_formed > 0:
        return "amide_hydrolysis"
    if c_n_broken > 0 and c_o_formed == 0 and dh > 0:
        return "deamination"
    if broken["-C-C"] > 0 and formed["=C-C"] > 0:
        return "dehydrogenation"
    if broken["=C-C"] > 0 and formed["-C-C"] > 0 and c_o_formed == 0:
        return "hydrogenation"
    if broken["=C-C"] > 0 and c_o_formed > 0:
        return "hydration"
    if formed["-C-O"] > 0 and broken["-C-O"] == 0 and add["O"] >= 1:
        return "hydroxylation"
    if broken["-C-O"] > 0 and c_o_formed == 0 and rem["C"] >= 1:
        return "demethylation"
    if c_o_broken > 0 and c_o_formed > 0:
        return "ether_ester_hydrolysis"
    if broken["-C-C"] > 0 or broken["=C-C"] > 0:
        return "C-C_cleavage"
    if formed["-C-C"] > 0:
        return "C-C_formation"
    if n_o_broken > 0 and dh > 0:
        return "nitro_reduction"
    if formed["=S-O"] > 0 or formed["-S-O"] > 0:
        return "sulfoxidation"
    if broken["-P-O"] > 0 or formed["-P-O"] > 0 or broken["=P-O"] > 0 or formed["=P-O"] > 0:
        return "phosphate_transfer"
    # coarse fallback: element-pair signature (bond order stripped) to keep the
    # class tail bounded
    sig = "+".join(sorted({k[1:] for k in (set(broken) | set(formed))})) or "none"
    return f"other:{sig[:80]}"


# --------------------------------------------------------------------------- #
# one-call label builder
# --------------------------------------------------------------------------- #
def build_label(reaction_smiles: str, mapped_rxn: Optional[str], confidence: Optional[float],
                cofactor_set=None) -> dict:
    if ">>" not in reaction_smiles:
        return {"status": "unusable"}
    lhs, rhs = reaction_smiles.split(">>", 1)
    r_mol = Chem.MolFromSmiles(lhs)
    p_mol = Chem.MolFromSmiles(rhs)
    if r_mol is None or p_mol is None:
        return {"status": "unusable"}
    matches = _correspondence(r_mol, p_mol)
    if not matches:
        return {"status": "unusable"}
    r_to_p = dict(matches)
    p_to_r = {p: r for r, p in matches}
    rem_r = [i for i in range(r_mol.GetNumAtoms()) if i not in r_to_p]
    rem_p = [j for j in range(p_mol.GetNumAtoms()) if j not in p_to_r]
    pairs, _removed, _added = _match_by_element(rem_r, rem_p, r_mol, p_mol)
    for i, j in pairs:
        r_to_p[i] = j
        p_to_r[j] = i
    reacted_r = {i for i, j in r_to_p.items() if _atom_env(r_mol, i) != _atom_env(p_mol, j)}
    reacted_r |= _removed  # 1a: leaving-group atoms are reaction centres too
    sub, indices, status, frag = _pick_substrate(r_mol, reacted_r, cofactor_set)
    if status != "ok":
        return {"status": status}

    sub_ev = _substrate_events(r_mol, p_mol, frag, r_to_p, p_to_r)
    n = Chem.MolFromSmiles(sub).GetNumAtoms()
    conf_norm = round(confidence ** (1.0 / n), 6) if n and confidence is not None else None
    return {
        "status": "ok",
        "substrate_smiles": sub,
        "reacted_atom_indices": indices,
        "reaction_class": classify(sub_ev),
        "broken_bonds": dict(sorted(sub_ev["broken"].items())),
        "formed_bonds": dict(sorted(sub_ev["formed"].items())),
        "delta_H": sub_ev["delta_H"],
        "removed_elements": sub_ev["removed_elements"],
        "added_elements": sub_ev["added_elements"],
        "conf_norm": conf_norm,
        "n_atoms": n,
    }