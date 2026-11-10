"""BBD rule reconstruction (RA-S8): donor->product SMILES -> atom-mapped SMIRKS.

The EAWAG-BBD SMARTS patterns are published only as PNG images (not machine
readable), so the atom-mapped SMIRKS is reconstructed from CONCRETE
donor->product structure pairs harvested from BBD compound pages.

Two mapping paths, gated by a round-trip test:
  1. RXNMapper (primary)  - handles redox / rearrangement / ring cleavage.
  2. MCS (fallback)       - handles substitution (dehalogenation) & hydrolysis.
     (RXNMapper treats a replaced hetero-atom as "remove+add" with no atom-map
      correspondence, which hides the leaving group; MCS with strict element
      comparison makes the removed/added atoms explicit.)

`extract_smirks` keeps only the reaction centre (atoms whose bonds/charge/
H-count change between donor and the WHOLE product side). Atom maps are kept for
atoms present on both sides; removed atoms are mapped on the reactant side only;
added atoms are left unmapped on the product side and attach to the shared
centre. Bonds from the centre to the unchanged surroundings are not encoded, so
the reactant pattern is a substructure query that matches any molecule carrying
the same centre (RDKit carries the unchanged remainder into the products).

Fail-closed: anything unparseable / unmappable is recorded as error and never
fabricated.
"""
import logging

from rdkit import Chem

logger = logging.getLogger(__name__)

# NOTE: `AllChem` / `rdFMCS` are imported lazily inside the functions that need
# them.  Importing them at module top perturbs RDKit's process-wide import order
# and flips the borderline MMFF-geometry vdW heuristic in the M3 site-compat
# module (chlorobenzene->phenol sits exactly at the 0.8 x Bondi threshold), which
# would make an unrelated test suite verdict depend on this module being imported.

_MAPPER = None


def get_mapper():
    global _MAPPER
    if _MAPPER is None:
        from rxnmapper import RXNMapper

        _MAPPER = RXNMapper()
    return _MAPPER


def map_reaction(rxn_smiles: str) -> dict | None:
    """Map one 'A>>B' (multi-component allowed) reaction with RXNMapper."""
    try:
        res = get_mapper().get_attention_guided_atom_maps([rxn_smiles])
    except Exception as exc:  # noqa: BLE001
        logger.warning("rxnmapper failed on %r: %s", rxn_smiles, exc)
        return None
    if not res:
        return None
    r = res[0]
    if not r.get("mapped_rxn"):
        return None
    return {"mapped_rxn": r["mapped_rxn"], "confidence": float(r.get("confidence", 0.0))}


# ---------------------------------------------------------------------------
# molecule / mapping helpers
# ---------------------------------------------------------------------------

def _map_index(mol):
    out = {}
    for i, a in enumerate(mol.GetAtoms()):
        n = a.GetAtomMapNum()
        if n:
            out[n] = i
    return out


def _combine(mols):
    """Merge a list of RDKit mols into one (disconnected) mol, preserving maps."""
    if not mols:
        return None
    if len(mols) == 1:
        return mols[0]
    return Chem.CombineMols(*mols)


def _bond_orders(mol):
    out = set()
    for b in mol.GetBonds():
        m1 = b.GetBeginAtom().GetAtomMapNum()
        m2 = b.GetEndAtom().GetAtomMapNum()
        if m1 and m2:
            out.add((min(m1, m2), max(m1, m2), b.GetBondTypeAsDouble()))
    return out


def changed_maps(rmol, ptotal):
    """Set of atom-map numbers whose environment changes reactant -> (combined)
    product side.  Multi-product reactions are handled by passing the WHOLE
    product side as one mol so a map is only 'removed' when absent from every
    product."""
    rmi = _map_index(rmol)
    pmi = _map_index(ptotal)
    changed = set()

    rb = _bond_orders(rmol)
    pb = _bond_orders(ptotal)
    for (a, b) in {(x, y) for (x, y, _t) in rb | pb}:
        r_ord = next((o for (x, y, o) in rb if (min(x, y), max(x, y)) == (a, b)), None)
        p_ord = next((o for (x, y, o) in pb if (min(x, y), max(x, y)) == (a, b)), None)
        if r_ord != p_ord:
            changed.add(a)
            changed.add(b)
    for m in set(rmi) & set(pmi):
        ra = rmol.GetAtomWithIdx(rmi[m])
        pa = ptotal.GetAtomWithIdx(pmi[m])
        if ra.GetFormalCharge() != pa.GetFormalCharge():
            changed.add(m)
        if ra.GetTotalNumHs() != pa.GetTotalNumHs():
            changed.add(m)
    for m in set(rmi) ^ set(pmi):
        changed.add(m)
    return changed


# ---------------------------------------------------------------------------
# SMIRKS building
# ---------------------------------------------------------------------------

def _query_atom(src_atom, map_num):
    q = Chem.Atom(src_atom.GetSymbol())
    q.SetFormalCharge(src_atom.GetFormalCharge())
    q.SetIsAromatic(src_atom.GetIsAromatic())
    if map_num is not None:
        q.SetAtomMapNum(map_num)
    return q


def _generalize(mol, core_maps, has_map):
    """Query mol with only the core atoms (mapped iff `has_map`); internal core
    bonds preserved, external bonds not encoded."""
    mi = _map_index(mol)
    core_idxs = [mi[m] for m in sorted(core_maps) if m in mi]
    if not core_idxs:
        return None
    core_set = set(core_idxs)
    rw = Chem.RWMol()
    idxmap = {}
    for i in core_idxs:
        a = mol.GetAtomWithIdx(i)
        mn = a.GetAtomMapNum() if a.GetAtomMapNum() in has_map else None
        idxmap[i] = rw.AddAtom(_query_atom(a, mn))
    added = set()
    for i in core_idxs:
        a = mol.GetAtomWithIdx(i)
        for b in a.GetBonds():
            j = b.GetOtherAtomIdx(i)
            if j in core_set:
                key = (min(i, j), max(i, j))
                if key in added:
                    continue
                added.add(key)
                rw.AddBond(idxmap[i], idxmap[j], b.GetBondType())
    return rw.GetMol()


def _build_smirks(rmol, pmols):
    """Build a single-reactant reaction SMARTS from mapped reactant + products.

    `changed` is computed against the COMBINED product side (a map is 'removed'
    only when it is absent from every product), so multi-product reactions
    (e.g. hydrolysis) do not wrongly flag conserved atoms as removed."""
    from rdkit.Chem import AllChem

    if rmol is None or not pmols:
        return None
    ptotal = _combine(pmols)
    if ptotal is None:
        return None
    changed = changed_maps(rmol, ptotal)
    if not changed:
        return None
    rmi = _map_index(rmol)
    shared_maps = {m for m in changed if m in rmi}  # mapped on reactant side

    out = AllChem.ChemicalReaction()
    rt_query = _generalize(rmol, shared_maps, shared_maps)
    if rt_query is None:
        return None
    out.AddReactantTemplate(rt_query)
    for pt in pmols:
        pmi = _map_index(pt)
        p_core = {m for m in changed if m in pmi}  # changed maps present in this product
        has_map = {m for m in p_core if m in rmi}  # mapped only if shared w/ reactant
        ptq = _generalize(pt, p_core, has_map)
        if ptq is None:
            continue
        out.AddProductTemplate(ptq)
    if out.GetNumProductTemplates() == 0:
        return None
    try:
        return AllChem.ReactionToSmarts(out)
    except Exception as exc:  # noqa: BLE001
        logger.warning("ReactionToSmarts failed: %s", exc)
        return None


def extract_smirks(mapped_rxn: str) -> str | None:
    """RXNMapper path: generalise a mapped reaction into a reaction SMARTS."""
    from rdkit.Chem import AllChem

    try:
        rxn = AllChem.ReactionFromSmarts(mapped_rxn, useSmiles=True)
    except Exception as exc:  # noqa: BLE001
        logger.warning("unparseable mapped reaction %r: %s", mapped_rxn, exc)
        return None
    if rxn.GetNumReactantTemplates() != 1:
        return None
    rmol = rxn.GetReactantTemplate(0)
    pmols = [rxn.GetProductTemplate(k) for k in range(rxn.GetNumProductTemplates())]
    return _build_smirks(rmol, pmols)


# ---------------------------------------------------------------------------
# MCS fallback path (substitution / hydrolysis)
# ---------------------------------------------------------------------------

def _mcs_atom_map(donor, products):
    """Map donor atoms -> product atoms via rdFMCS (strict element compare).

    Returns (d2p dict, core_donor set) where d2p maps donor atom idx -> (product
    mol idx, atom idx) for MCS-matched atoms, or None on failure."""
    from rdkit.Chem import rdFMCS

    pmols = [Chem.MolFromSmiles(p) for p in products]
    if any(m is None for m in pmols):
        return None, None
    mcs = rdFMCS.FindMCS(
        [donor] + pmols,
        atomCompare=rdFMCS.AtomCompare.CompareElements,
        bondCompare=rdFMCS.BondCompare.CompareOrder,
        ringMatchesRingOnly=True,
        completeRingsOnly=False,
        maximizeBonds=True,
        timeout=20,
    )
    q = Chem.MolFromSmarts(mcs.smartsString)
    if q is None:
        return None, None
    dm = donor.GetSubstructMatches(q, uniquify=True)
    if not dm:
        return None, None
    d_match = dm[0]
    d2p = {}
    for prod_idx, pmol in enumerate(pmols):
        pm = pmol.GetSubstructMatches(q, uniquify=True)
        if not pm:
            continue
        p_match = pm[0]
        for k, di in enumerate(d_match):
            # q atom order k -> donor atom d_match[k] -> pmol atom p_match[k]
            if k < len(p_match):
                d2p.setdefault(di, []).append((prod_idx, p_match[k]))
    core_donor = set(d_match)
    return d2p, core_donor


def _assign_maps_from_mcs(donor, products):
    """Build (donor_mapped, product_mols_mapped) with self-assigned atom maps.

    Shared (MCS) atoms share a map number; donor atoms removed get a fresh map;
    product atoms added get a fresh map (present only on the product side).
    """
    d2p, core_donor = _mcs_atom_map(donor, products)
    if d2p is None:
        return None, None
    pmols = [Chem.MolFromSmiles(p) for p in products]

    next_map = 1000
    d_mapped = Chem.RWMol(donor)
    p_mapped = [Chem.RWMol(m) for m in pmols]

    d_map = {}  # donor idx -> map num
    # MCS correspondence: one shared map per connected MCS component-pair. To
    # keep it simple and correct we assign a shared map to EACH pair of
    # corresponding atoms (MCS atoms are in bijection across structures here).
    for di, pairs in d2p.items():
        m = next_map
        next_map += 1
        d_mapped.GetAtomWithIdx(di).SetAtomMapNum(m)
        d_map[di] = m
        for (pi, ai) in pairs:
            p_mapped[pi].GetAtomWithIdx(ai).SetAtomMapNum(m)

    # removed donor atoms (not in MCS): fresh map on donor only
    for ai in range(donor.GetNumAtoms()):
        if ai not in d_map:
            m = next_map
            next_map += 1
            d_mapped.GetAtomWithIdx(ai).SetAtomMapNum(m)
            d_map[ai] = m

    # added product atoms (no map yet): fresh map on product only
    p_have = [set(a.GetAtomMapNum() for a in pm.GetAtoms()) for pm in p_mapped]
    for pi, pm in enumerate(p_mapped):
        for ai in range(pm.GetNumAtoms()):
            if pm.GetAtomWithIdx(ai).GetAtomMapNum() == 0:
                m = next_map
                next_map += 1
                pm.GetAtomWithIdx(ai).SetAtomMapNum(m)
                p_have[pi].add(m)

    return d_mapped.GetMol(), [pm.GetMol() for pm in p_mapped]


def extract_smirks_mcs(donor_smiles, product_smiles_list):
    """MCS path: donor + product(s) -> reaction SMARTS via self-assigned maps."""
    donor = Chem.MolFromSmiles(donor_smiles)
    if donor is None:
        return None
    d_mapped, p_mapped = _assign_maps_from_mcs(donor, product_smiles_list)
    if d_mapped is None:
        return None
    # restrict: MCS path only builds single-reactant (donor) rules
    return _build_smirks(d_mapped, p_mapped)


# ---------------------------------------------------------------------------
# public reconstruction API
# ---------------------------------------------------------------------------

def reconstruct(donor_smiles: str, product_smiles: str) -> dict:
    """Reconstruct a SMIRKS from one donor->product pair (both multi-component ok).

    Result keys: smirks (str|None), path ('rxnmapper'|'mcs'|None), confidence
    (float|None), roundtrip (bool), error (str|None).
    """
    out = {"smirks": None, "path": None, "confidence": None, "roundtrip": False, "error": None}
    d = Chem.MolFromSmiles(donor_smiles)
    if d is None:
        out["error"] = "unparseable donor"
        return out
    prods = [Chem.MolFromSmiles(p) for p in product_smiles.split(".") if p.strip()]
    if not prods or any(m is None for m in prods):
        out["error"] = "unparseable product(s)"
        return out
    products = product_smiles

    # path 1: rxnmapper
    m = map_reaction(f"{donor_smiles}>>{products}")
    rx_smirks = None
    if m:
        rx_smirks = extract_smirks(m["mapped_rxn"])
        if rx_smirks:
            out["smirks"] = rx_smirks
            out["path"] = "rxnmapper"
            out["confidence"] = m["confidence"]
            out["roundtrip"] = round_trip(rx_smirks, donor_smiles, products)
            if out["roundtrip"]:
                return out
    # path 2: mcs
    mcs_smirks = extract_smirks_mcs(donor_smiles, product_smiles.split("."))
    if mcs_smirks:
        rt = round_trip(mcs_smirks, donor_smiles, products)
        if rt or not out["smirks"]:
            out["smirks"] = mcs_smirks
            out["path"] = "mcs"
            out["roundtrip"] = rt
            if rt:
                return out
    if out["smirks"] is None:
        out["error"] = "no reconstructable rule"
    elif not out["roundtrip"]:
        out["error"] = "reconstructed rule fails round-trip on its own example"
    return out


def round_trip(smirks: str, donor_smiles: str, product_smiles: str) -> bool:
    """True iff applying smirks to donor yields every product (canonical)."""
    from rdkit.Chem import AllChem

    try:
        rxn = AllChem.ReactionFromSmarts(smirks)
    except Exception:  # noqa: BLE001
        return False
    d = Chem.MolFromSmiles(donor_smiles)
    if d is None or not d.HasSubstructMatch(rxn.GetReactants()[0]):
        return False
    try:
        outs = rxn.RunReactants((d,))
    except Exception:  # noqa: BLE001
        return False
    targets = {Chem.MolToSmiles(Chem.MolFromSmiles(p)) for p in product_smiles.split(".") if Chem.MolFromSmiles(p)}
    if not targets:
        return False
    for ps in outs:
        got = set()
        for p in ps:
            try:
                Chem.SanitizeMol(p)
                got.add(Chem.MolToSmiles(p))
            except Exception:  # noqa: BLE001
                continue
        if targets.issubset(got):
            return True
    return False