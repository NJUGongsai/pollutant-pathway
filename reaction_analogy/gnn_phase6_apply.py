#!/usr/bin/env python3
"""USPTO forward prediction: template APPLICATION via graph-edit (not RunReactants).

Replaces the RunReactants round-trip (which emits spurious `*` and mis-handles
spectators / leaving groups). Match reactant-side SMARTS -> edit bonds / H /
charge on the reactant graph per product-side template -> sanitize -> keep the
component containing a surviving center atom (drops spectator + leaving frags)
-> strip atom-maps -> canonical (non-chiral).

Based on attachments/poc_graph_edit.py, extended:
 1. GetSubstructMatches (enumerate ALL matches, one candidate each, dedup).
 2. Wildcard-neighbor disambiguation by bond type + AddBond branch.
 3. Sanitize failures -> candidate dropped (caller counts no-cand).
 4. Returns set[canonical]; comparison = strip atom-map + non-chiral canonical.
"""
from collections import Counter

from rdkit import Chem, RDLogger
from rdkit.Chem import AllChem

RDLogger.DisableLog("rdApp.*")


def strip_maps(mol):
    m = Chem.RWMol(mol)
    for a in m.GetAtoms():
        a.SetAtomMapNum(0)
    try:
        Chem.SanitizeMol(m)
    except Exception:
        pass
    return m.GetMol()


def canon_nomap(smi):
    """Map-stripped, non-chiral canonical SMILES of the LARGEST connected
    component. Both candidate and true product go through this, so spectator
    salts / small ions (e.g. `ClH`, `K`) are dropped on both sides consistently —
    the candidate already keeps the center-containing component, this mirrors it
    on the truth side."""
    m = Chem.MolFromSmiles(smi)
    if m is None:
        return None
    m = strip_maps(m)
    frags = Chem.GetMolFrags(m, asMols=True)
    if len(frags) > 1:
        m = max(frags, key=lambda f: f.GetNumAtoms())
    return Chem.MolToSmiles(m, isomericSmiles=False)


def _keyed(m):
    return {a.GetAtomMapNum(): a.GetIdx() for a in m.GetAtoms() if a.GetAtomMapNum()}


def _loosen_query(r_frag):
    """Relax each atom query to atomic-number-only (no aromaticity/charge/H
    constraint), preserving atom-map numbers and all bonds. Used as a fallback
    when the strict r_frag fails to match — typically because build_frag_wildcard
    emits aromatic center atoms as aliphatic `C`/`N`, which can't match aromatic
    atoms in the target. ReplaceAtom keeps idx stable, so edit logic (which uses
    r_frag for bond info) is unaffected."""
    from rdkit.Chem import rdqueries
    rw = Chem.RWMol(r_frag)
    for a in rw.GetAtoms():
        z = a.GetAtomicNum()
        if z > 0:
            q = rdqueries.AtomNumEqualsQueryAtom(z)
            q.SetAtomMapNum(a.GetAtomMapNum())
            rw.ReplaceAtom(a.GetIdx(), q)
    return rw.GetMol()


def apply_one_match(mol, r_frag, p_frag, match):
    """Apply template edits for one substructure match -> canonical SMILES or None."""
    f2m = {fi: match[fi] for fi in range(r_frag.GetNumAtoms())}
    rw = Chem.RWMol(mol)

    r_by_map = _keyed(r_frag)
    p_by_map = _keyed(p_frag)
    pf2m = {pi: f2m[r_by_map[mp]] for mp, pi in p_by_map.items() if mp in r_by_map}

    maps = list(r_by_map)
    # ---- center-center bond edits: break / form / re-order (order from product side) ----
    for ai in range(len(maps)):
        for bi in range(ai + 1, len(maps)):
            ma, mb = maps[ai], maps[bi]
            ri, rj = r_by_map[ma], r_by_map[mb]
            rb = r_frag.GetBondBetweenAtoms(ri, rj)
            pb = None
            if ma in p_by_map and mb in p_by_map:
                pb = p_frag.GetBondBetweenAtoms(p_by_map[ma], p_by_map[mb])
            mi, mj = f2m[ri], f2m[rj]
            cur = rw.GetBondBetweenAtoms(mi, mj)
            if rb is not None and pb is None:
                if cur is not None:
                    rw.RemoveBond(mi, mj)
            elif rb is None and pb is not None:
                if cur is None:
                    rw.AddBond(mi, mj, pb.GetBondType())
            elif rb is not None and pb is not None and cur is not None:
                if cur.GetBondType() != pb.GetBondType():
                    cur.SetBondType(pb.GetBondType())

    # ---- wildcard bonds on product side: center-to-outer-neighbor edits ----
    used_outer = set()
    for pb in p_frag.GetBonds():
        a1, a2 = pb.GetBeginAtom(), pb.GetEndAtom()
        if a1.GetAtomMapNum() and not a2.GetAtomMapNum():
            center_pi, _wild_pi = a1.GetIdx(), a2.GetIdx()
        elif a2.GetAtomMapNum() and not a1.GetAtomMapNum():
            center_pi, _wild_pi = a2.GetIdx(), a1.GetIdx()
        else:
            continue
        cm = pf2m.get(center_pi)
        if cm is None:
            continue
        rmap = p_frag.GetAtomWithIdx(center_pi).GetAtomMapNum()
        ridx = r_by_map.get(rmap)
        if ridx is None:
            continue
        want = pb.GetBondType()
        # candidate outer neighbors: reactant-side center's non-mapped neighbors
        candidates = []
        for nb in r_frag.GetAtomWithIdx(ridx).GetNeighbors():
            if nb.GetAtomMapNum():
                continue
            mi = f2m.get(nb.GetIdx())
            if mi is None or mi in used_outer:
                continue
            candidates.append((mi, rw.GetBondBetweenAtoms(cm, mi)))
        # disambiguate: prefer a neighbor whose current bond type already == want
        # (corresponds to an unchanged context bond); else one with an existing
        # bond (re-order); else first (add-bond). Getting this backwards (preferring
        # "differs") mis-pairs e.g. =O<->aryl and corrupts the molecule (sanitize fails).
        outer_mi = None
        for mi, b in candidates:
            if b is not None and b.GetBondType() == want:
                outer_mi = mi
                break
        if outer_mi is None:
            for mi, b in candidates:
                if b is not None:
                    outer_mi = mi
                    break
        if outer_mi is None and candidates:
            outer_mi = candidates[0][0]
        if outer_mi is None:
            continue
        used_outer.add(outer_mi)
        b = rw.GetBondBetweenAtoms(cm, outer_mi)
        if b is None:
            rw.AddBond(cm, outer_mi, want)
        elif b.GetBondType() != want:
            # only re-order non-aromatic bonds; an aromatic-vs-single mismatch
            # comes from build_frag_wildcard's round-trip (a fat `*` next to an
            # aromatic center parses as SINGLE), not a real bond change — editing
            # it would corrupt aromaticity and fail sanitize.
            if not b.GetIsAromatic() and want != Chem.BondType.AROMATIC:
                b.SetBondType(want)

    # ---- atom property edits (charge, explicit H) for surviving center atoms ----
    for pi_, mi in pf2m.items():
        pa = p_frag.GetAtomWithIdx(pi_)
        ta = rw.GetAtomWithIdx(mi)
        ta.SetFormalCharge(pa.GetFormalCharge())
        ta.SetNumExplicitHs(pa.GetNumExplicitHs())

    try:
        Chem.SanitizeMol(rw)
    except Exception:
        return None
    full = rw.GetMol()
    # keep the connected component containing a surviving center atom
    atom_frags = Chem.GetMolFrags(full)
    keep = None
    for frag in atom_frags:
        if any(pi_ in pf2m and pf2m[pi_] in frag for pi_ in pf2m):
            keep = frag
            break
    if keep is None:
        keep = max(atom_frags, key=len)
    sub = Chem.MolFragmentToSmiles(full, atomsToUse=keep)
    m2 = Chem.MolFromSmiles(sub)
    if m2 is None:
        return None
    site = frozenset(f2m[ri] for ri in r_by_map.values())  # 底物反应位点原子 idx
    return Chem.MolToSmiles(strip_maps(m2), isomericSmiles=False), site


def parse_template(tpl):
    """Pre-parse a template string into (r_frag, p_frag) for reuse across reactants."""
    if tpl is None or ">>" not in tpl:
        return None, None
    r_smi, p_smi = tpl.split(">>", 1)
    r_frag = Chem.MolFromSmarts(r_smi)
    p_frag = Chem.MolFromSmiles(p_smi)
    if p_frag is None:
        # aromatic center atoms appear as lowercase `c`/`n` in p_smi but aren't
        # in a full aromatic ring, so MolFromSmiles can't kekulize -> parse as SMARTS.
        p_frag = Chem.MolFromSmarts(p_smi)
    return r_frag, p_frag


def apply_to(mol, r_frag, p_frag, max_matches=100000):
    """Apply a pre-parsed template to a pre-parsed reactant mol; return
    {canonical: site_atom_idx} (site = frozenset of reactant center atom idx,
    for regioselectivity features). Avoids re-parsing the template per pair."""
    if r_frag is None or p_frag is None or mol is None:
        return {}
    cands = {}  # canonical -> site (first match's)
    for match in mol.GetSubstructMatches(r_frag, maxMatches=max_matches):
        out = apply_one_match(mol, r_frag, p_frag, match)
        if out:
            smi, site = out
            if smi not in cands:
                cands[smi] = site
    return cands


def apply_to_smi(mol, r_frag, p_smi, max_matches=100000):
    """Like apply_to, but p_frag is parsed on-demand from p_smi only AFTER r_frag
    matches. Halves resident memory (only r_frag pre-parsed; p_frag not held), so
    64 procs don't OOM on a 256GB node that previously died at 144GB."""
    if r_frag is None or mol is None or not p_smi:
        return set()
    matches = mol.GetSubstructMatches(r_frag, maxMatches=max_matches)
    if not matches:
        return set()
    p_frag = Chem.MolFromSmiles(p_smi)
    if p_frag is None:
        p_frag = Chem.MolFromSmarts(p_smi)
    if p_frag is None:
        return set()
    cands = set()
    for match in matches:
        out = apply_one_match(mol, r_frag, p_frag, match)
        if out:
            cands.add(out)
    return cands


def apply_template(reactant_smi, tpl, max_matches=100000):
    """Apply template to reactant; return {canonical: site_atom_idx}."""
    r_frag, p_frag = parse_template(tpl)
    mol = Chem.MolFromSmiles(reactant_smi)
    return apply_to(mol, r_frag, p_frag, max_matches=max_matches)


SITE_ELEMS = ["C", "N", "O", "S", "P", "F", "Cl", "Br", "I"]


def site_features(mol, site_idx):
    """反应位点(底物 center 原子 idx 集合)的固定长度特征向量，供排序器区分
    regioselectivity（哪个位点反应）。含 1-hop + 2-hop 邻居元素，区分同元素
    不同环境的位点（如多氟芳环的 3 个氟）。"""
    n_feat = 1 + 3 * len(SITE_ELEMS) + 4 + 64
    if not site_idx:
        return [0.0] * n_feat
    atoms = [mol.GetAtomWithIdx(i) for i in site_idx if 0 <= i < mol.GetNumAtoms()]
    if not atoms:
        return [0.0] * n_feat
    site_set = set(site_idx)
    elems = Counter(a.GetSymbol() for a in atoms)
    nb_elems = Counter()
    nb2_elems = Counter()
    for a in atoms:
        for nb in a.GetNeighbors():
            nb_elems[nb.GetSymbol()] += 1
            for nb2 in nb.GetNeighbors():
                if nb2.GetIdx() not in site_set:
                    nb2_elems[nb2.GetSymbol()] += 1
    degs = [a.GetDegree() for a in atoms]
    feats = [len(atoms)]
    feats += [1 if e in elems else 0 for e in SITE_ELEMS]       # site 元素 one-hot
    feats += [nb_elems.get(e, 0) for e in SITE_ELEMS]           # 1-hop 邻居元素计数
    feats += [nb2_elems.get(e, 0) for e in SITE_ELEMS]          # 2-hop 邻居元素计数
    feats += [sum(degs) / len(degs), max(degs)]                 # 平均/最大度数
    feats.append(sum(1 for a in atoms if a.GetIsAromatic()))    # 芳香原子数
    feats.append(sum(a.GetFormalCharge() for a in atoms))       # 总电荷
    # Morgan 子图（site 原子局部环境指纹，区分同元素不同环境的位点）
    try:
        site_fp = AllChem.GetMorganFingerprintAsBitVect(mol, 2, nBits=64,
                                                        fromAtoms=list(site_idx))
        feats += [int(site_fp.GetBit(i)) for i in range(64)]
    except Exception:
        feats += [0] * 64
    return feats


def template_type(r_frag):
    """模板反应类型 = sorted(center 原子元素 tuple)。粗分 ~10-20 大类
    (如 ('C','N')=胺化, ('C','O')=酯化/水解, ('C','C')=偶联)。"""
    elems = sorted(a.GetSymbol() for a in r_frag.GetAtoms() if a.GetAtomMapNum() > 0)
    return tuple(elems)
