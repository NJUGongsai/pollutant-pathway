"""Fragment-lineage graph (M2, MASTER_PLAN §5 / final_plan P1-T6).

Builds a bipartite fragment<->molecule graph over the M1 atom-mapped RHEA reactions
(data/aam/aam_sample.jsonl), carrying the "which structural changes are evidenced".

Concepts (P1-T6):
  * reactant->product graph  : a reaction edge links donor molecule + product molecule(s)
  * mapped overlap           : shared atom-map numbers between the two sides
  * retention / origin        : which product atoms trace back to the donor (retained)
  * changed-atom participation: the reaction-centre atoms (env-diff via the mapper's own
                                map-number bridge, + added/removed)
  * fragment                 : reaction-centre subgraph (+ radius-1 context) on both sides,
                                canonicalised so the same transform shares one node
  * transfer edges           : product-of-r1 == reactant-of-r2 (multi-step lineage)
  * split / merge            : 1->N products is split; N->1 reactants is merge
  * ambiguity sets           : mapper_confidence < CONF_THRESHOLD => ambiguous, never
                                claimed as certain lineage (fail-closed)
  * stable lineage IDs       : sha256 of the canonical content

Prohibited (P1-T6): independent side picking; tuple max tie; forced primary pair.
This builder never picks among competing correspondences: it uses the single map-number
bridge emitted by RXNMapper, and where confidence is low it marks ambiguity instead of
choosing.
"""
from __future__ import annotations

import hashlib
import json
from typing import Dict, List, Optional, Tuple

from rdkit import Chem

from ra.aam import _atom_env

CONF_THRESHOLD = 0.5
CONTEXT_RADIUS = 1
HASH_LEN = 12


# --------------------------------------------------------------------------- #
# stable ids
# --------------------------------------------------------------------------- #
def stable_id(prefix: str, *parts: str) -> str:
    h = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:HASH_LEN]
    return f"{prefix}-{h}"


def molecule_id(canonical_smiles: str) -> str:
    return stable_id("mol", canonical_smiles)


def fragment_id(reactant_fragment: str, product_fragment: str) -> str:
    return stable_id("frag", reactant_fragment, product_fragment)


# --------------------------------------------------------------------------- #
# parsing
# --------------------------------------------------------------------------- #
def canonical_component_smiles(smiles: str) -> Optional[str]:
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    return Chem.MolToSmiles(mol, canonical=True, isomericSmiles=True)


def parse_mapped_reaction(mapped_reaction_smiles: str):
    """Parse a mapped reaction into (reactant_mol, product_mols, product_merged).

    Returns None when either side fails to parse.
    """
    if ">>" not in mapped_reaction_smiles:
        return None
    lhs, rhs = mapped_reaction_smiles.split(">>", 1)
    r = Chem.MolFromSmiles(lhs)
    if r is None:
        return None
    p_parts = [p for p in rhs.split(".") if p.strip()]
    p_mols = [Chem.MolFromSmiles(p) for p in p_parts]
    if any(m is None for m in p_mols):
        return None
    p_merged = Chem.MolFromSmiles(rhs)
    if p_merged is None:
        return None
    return r, p_mols, p_merged


def mapnum_to_idx(mol) -> Dict[int, List[int]]:
    d: Dict[int, List[int]] = {}
    for a in mol.GetAtoms():
        d.setdefault(a.GetAtomMapNum(), []).append(a.GetIdx())
    return d


# --------------------------------------------------------------------------- #
# changed-atom participation (mapper's own correspondence)
# --------------------------------------------------------------------------- #
def _stereo_signature(mol, idx: int) -> tuple:
    """Atom chirality + incident double-bond stereochemistry (R/S, E/Z)."""
    a = mol.GetAtomWithIdx(idx)
    bonds = []
    for b in a.GetBonds():
        n = b.GetOtherAtomIdx(idx)
        bonds.append((int(b.GetStereo()), mol.GetAtomWithIdx(n).GetAtomicNum()))
    return (int(a.GetChiralTag()), tuple(sorted(bonds)))


def analyze_changed(r_mol, p_merged) -> Dict:
    r_map = mapnum_to_idx(r_mol)
    p_map = mapnum_to_idx(p_merged)
    r_keys = set(r_map) - {0}
    p_keys = set(p_map) - {0}

    removed = sorted(i for mn, idxs in r_map.items() if mn in (0,) or mn not in p_keys for i in idxs)
    added = sorted(j for mn, idxs in p_map.items() if mn in (0,) or mn not in r_keys for j in idxs)

    changed_r: List[int] = []
    changed_p: List[int] = []
    for mn in sorted(r_keys & p_keys):
        for ri in r_map[mn]:
            for pj in p_map[mn]:
                if (_atom_env(r_mol, ri) != _atom_env(p_merged, pj)
                        or _stereo_signature(r_mol, ri) != _stereo_signature(p_merged, pj)):
                    changed_r.append(ri)
                    changed_p.append(pj)

    center_r = sorted(set(changed_r) | set(removed))
    center_p = sorted(set(changed_p) | set(added))
    return {
        "removed": removed,
        "added": added,
        "changed_r": sorted(set(changed_r)),
        "changed_p": sorted(set(changed_p)),
        "center_r": center_r,
        "center_p": center_p,
        "n_shared": len(r_keys & p_keys),
    }


# --------------------------------------------------------------------------- #
# fragment extraction
# --------------------------------------------------------------------------- #
def _neighborhood(mol, idxs, radius: int) -> set:
    keep = set(idxs)
    for _ in range(radius):
        nxt = set(keep)
        for i in list(keep):
            a = mol.GetAtomWithIdx(i)
            for n in a.GetNeighbors():
                nxt.add(n.GetIdx())
        keep = nxt
    return keep


def _kekulized(mol):
    """Return a kekulized copy (aromatic bonds -> single/double); indices preserved."""
    k = Chem.Mol(mol)
    try:
        Chem.Kekulize(k, clearAromaticFlags=True)
    except Exception:  # noqa: BLE001
        return mol
    return k


def submol(mol, keep: set, kekulize: bool = True) -> Optional[Chem.Mol]:
    """Induced sub-molecule preserving element/charge/map/stereo/bonds.

    Fragments are extracted from a kekulized copy so partial rings do not leak stale
    aromatic flags (which trigger "non-ring atom marked aromatic" and corrupt the
    canonical form).
    """
    keep = set(int(i) for i in keep)
    if not keep:
        return None
    if kekulize:
        mol = _kekulized(mol)
    emol = Chem.RWMol()
    idx_map: Dict[int, int] = {}
    for a in mol.GetAtoms():
        if a.GetIdx() in keep:
            na = Chem.Atom(a.GetAtomicNum())
            na.SetFormalCharge(a.GetFormalCharge())
            na.SetAtomMapNum(a.GetAtomMapNum())
            na.SetIsotope(a.GetIsotope())
            na.SetNumExplicitHs(a.GetNumExplicitHs())
            na.SetNoImplicit(a.GetNoImplicit())
            na.SetChiralTag(a.GetChiralTag())
            idx_map[a.GetIdx()] = emol.AddAtom(na)
    for b in mol.GetBonds():
        i, j = b.GetBeginAtomIdx(), b.GetEndAtomIdx()
        if i in keep and j in keep:
            emol.AddBond(idx_map[i], idx_map[j], b.GetBondType())
    try:
        out = emol.GetMol()
        out.UpdatePropertyCache(strict=False)
        Chem.SanitizeMol(out)
        return out
    except Exception:  # noqa: BLE001 -- fragment may carry dangling valences
        return None


def _strip_mapnums(mol):
    c = Chem.RWMol(mol)
    for a in c.GetAtoms():
        a.SetAtomMapNum(0)
    return c.GetMol()


def normalize_fragment(r_frag, p_frag) -> Optional[Dict]:
    """Canonicalise a fragment pair to an order-independent mapped-string pair.

    Atom map numbers are renumbered 1..N using the reactant-side canonical ranking,
    so chemically-identical transforms from different reactions collide to one id.
    """
    r_rank = list(Chem.CanonicalRankAtoms(_strip_mapnums(r_frag), breakTies=True))
    orig2new: Dict[int, int] = {}
    for a in r_frag.GetAtoms():
        m = a.GetAtomMapNum()
        if m not in (0, None):
            orig2new[m] = r_rank[a.GetIdx()] + 1

    r_num = {}
    for a in r_frag.GetAtoms():
        r_num[a.GetIdx()] = orig2new.get(a.GetAtomMapNum())

    p_rank = list(Chem.CanonicalRankAtoms(_strip_mapnums(p_frag), breakTies=True))
    next_num = len(r_frag.GetAtoms()) + 1
    p_order = sorted(range(p_frag.GetNumAtoms()), key=lambda j: p_rank[j])
    p_num: Dict[int, int] = {}
    for j in p_order:
        m = p_frag.GetAtomWithIdx(j).GetAtomMapNum()
        if m in orig2new:
            p_num[j] = orig2new[m]
        else:
            p_num[j] = next_num
            next_num += 1

    r_out = Chem.RWMol(r_frag)
    for a in r_out.GetAtoms():
        a.SetAtomMapNum(r_num[a.GetIdx()] or 0)
    p_out = Chem.RWMol(p_frag)
    for a in p_out.GetAtoms():
        a.SetAtomMapNum(p_num[a.GetIdx()])

    try:
        r_smiles = Chem.MolToSmiles(r_out.GetMol(), canonical=True)
        p_smiles = Chem.MolToSmiles(p_out.GetMol(), canonical=True)
    except Exception:  # noqa: BLE001
        return None
    return {"reactant_fragment": r_smiles, "product_fragment": p_smiles,
            "renumber": {"orig2new": orig2new, "r_num": r_num, "p_num": p_num}}


# --------------------------------------------------------------------------- #
# per-reaction build
# --------------------------------------------------------------------------- #
def build_reaction(rec: dict) -> Dict:
    """Turn one aam_sample record into graph parts.

    Returns {"built": True, ...record...} on success, or {"built": False, "skip_reason": _}
    (fail-closed: never guesses; skips are explicit and tallied).
    """
    mapped = rec.get("mapped_reaction_smiles")
    if rec.get("status") != "ok" or not mapped:
        return {"built": False, "skip_reason": "not_mapped"}
    parsed = parse_mapped_reaction(mapped)
    if parsed is None:
        return {"built": False, "skip_reason": "parse_mapped_failed"}
    r_mol, p_mols, p_merged = parsed

    # donor / product molecule identities from the (unmapped) reaction SMILES
    rxn = rec.get("reaction_smiles") or ""
    if ">>" not in rxn:
        return {"built": False, "skip_reason": "no_arrow"}
    donor_smi = canonical_component_smiles(rxn.split(">>", 1)[0])
    prod_smis = [canonical_component_smiles(p) for p in rxn.split(">>", 1)[1].split(".") if p.strip()]
    if donor_smi is None or any(s is None for s in prod_smis):
        return {"built": False, "skip_reason": "molecule_parse_failed"}

    conf = rec.get("mapper_confidence")
    trusted = conf is not None and conf >= CONF_THRESHOLD
    anc = analyze_changed(r_mol, p_merged)

    # no-op gate: identical canonical molecule both sides => no transform to evidence
    if donor_smi == ".".join(sorted(prod_smis)):
        return {"built": False, "skip_reason": "noop"}

    # whole-molecule rearrangement fallback: no local centre detected but the molecule
    # genuinely changed => the whole molecule is the reaction centre (no local fragment).
    center_r = anc["center_r"]
    center_p = anc["center_p"]
    if not center_r and not center_p:
        center_r = list(range(r_mol.GetNumAtoms()))
        center_p = list(range(p_merged.GetNumAtoms()))

    r_keep = _neighborhood(r_mol, center_r, CONTEXT_RADIUS)
    p_keep = _neighborhood(p_merged, center_p, CONTEXT_RADIUS)
    r_frag = submol(r_mol, r_keep)
    p_frag = submol(p_merged, p_keep)
    norm = normalize_fragment(r_frag, p_frag) if (r_frag and p_frag) else None
    if not norm:
        return {"built": False, "skip_reason": "fragment_extract_failed"}

    fid = fragment_id(norm["reactant_fragment"], norm["product_fragment"])
    donor_id = molecule_id(donor_smi)
    prod_ids = [molecule_id(s) for s in prod_smis]

    n_reactant_atoms = r_mol.GetNumAtoms()
    n_product_atoms = p_merged.GetNumAtoms()
    n_shared = anc["n_shared"]

    return {
        "built": True,
        "reaction_id": rec.get("source_id") or rec.get("record_id"),
        "record_id": rec.get("record_id"),
        "donor_id": donor_id,
        "donor_smiles": donor_smi,
        "product_ids": prod_ids,
        "product_smiles": prod_smis,
        "fragment_id": fid,
        "reactant_fragment": norm["reactant_fragment"],
        "product_fragment": norm["product_fragment"],
        "confidence": conf,
        "conf_trusted": trusted,
        "lineage_status": "trusted" if trusted else "ambiguous",
        "n_reactants": 1,
        "n_products": len(prod_smis),
        "split": len(prod_smis) > 1,
        "merge": False,  # single-reactant corpus => never merge
        "element_conserved": rec.get("element_conserved"),
        "n_reactant_atoms": n_reactant_atoms,
        "n_product_atoms": n_product_atoms,
        "n_shared_mapnums": n_shared,
        "retained_fraction": (n_shared / n_product_atoms) if n_product_atoms else None,
        "overlap_reactant": (n_shared / n_reactant_atoms) if n_reactant_atoms else None,
        "changed_atoms": {
            "n_center_reactant": len(anc["center_r"]),
            "n_center_product": len(anc["center_p"]),
            "n_added": len(anc["added"]),
            "n_removed": len(anc["removed"]),
        },
    }


# --------------------------------------------------------------------------- #
# graph assembly
# --------------------------------------------------------------------------- #
def build_graph(aam_path: str) -> Dict:
    """Assemble the full bipartite fragment-lineage graph + stats from aam_sample.jsonl."""
    molecules: Dict[str, Dict] = {}
    fragments: Dict[str, Dict] = {}
    reactions: List[Dict] = []
    skip_reasons: Dict[str, int] = {}

    recs = []
    with open(aam_path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                recs.append(json.loads(line))
    # deterministic order already (aam_sample is record-order), but pin by id
    recs.sort(key=lambda r: (r.get("source_id") or "", r.get("record_id") or ""))

    for rec in recs:
        br = build_reaction(rec)
        if not br.get("built"):
            reason = br.get("skip_reason", "unknown")
            skip_reasons[reason] = skip_reasons.get(reason, 0) + 1
            continue
        # register molecules
        molecules.setdefault(br["donor_id"], {"id": br["donor_id"], "canonical_smiles": br["donor_smiles"],
                                             "formula": _formula(br["donor_smiles"])})
        for pid, psmi in zip(br["product_ids"], br["product_smiles"]):
            molecules.setdefault(pid, {"id": pid, "canonical_smiles": psmi, "formula": _formula(psmi)})
        # register fragment
        f = fragments.setdefault(br["fragment_id"], {
            "id": br["fragment_id"],
            "reactant_fragment": br["reactant_fragment"],
            "product_fragment": br["product_fragment"],
            "instances": [],
        })
        f["instances"].append({
            "reaction_id": br["reaction_id"],
            "confidence": br["confidence"],
            "conf_trusted": br["conf_trusted"],
        })
        reactions.append(br)

    # sort + dedup instance lists, aggregate fragment confidence
    for fid, f in fragments.items():
        f["instances"].sort(key=lambda x: (x["reaction_id"]))
        confs = [i["confidence"] for i in f["instances"] if i["confidence"] is not None]
        f["n_instances"] = len(f["instances"])
        f["min_confidence"] = min(confs) if confs else None
        f["median_confidence"] = _median(confs)
        f["max_confidence"] = max(confs) if confs else None
        f["n_trusted_instances"] = sum(1 for i in f["instances"] if i["conf_trusted"])
        f["n_ambiguous_instances"] = f["n_instances"] - f["n_trusted_instances"]

    # transfer edges: product of r1 == donor of r2
    donor_to_reaction: Dict[str, List[str]] = {}
    product_to_reactions: Dict[str, List[str]] = {}
    for br in reactions:
        donor_to_reaction.setdefault(br["donor_id"], []).append(br["reaction_id"])
        for pid in br["product_ids"]:
            product_to_reactions.setdefault(pid, []).append(br["reaction_id"])

    transfers: List[Dict] = []
    for br in reactions:
        for pid in br["product_ids"]:
            for downstream in donor_to_reaction.get(pid, []):
                if downstream == br["reaction_id"]:
                    continue  # self-loop (reversible pair maps to itself via same mol?) no
                transfers.append({
                    "id": stable_id("xfr", pid, br["reaction_id"], downstream),
                    "molecule_id": pid,
                    "molecule_smiles": molecules[pid]["canonical_smiles"],
                    "upstream_reaction": br["reaction_id"],
                    "downstream_reaction": downstream,
                    "upstream_fragment": br["fragment_id"],
                })
    # de-dupe transfers (same upstream/downstream/molecule)
    seen = set()
    transfers = [t for t in transfers if not (t["id"] in seen or seen.add(t["id"]))]
    transfers.sort(key=lambda t: t["id"])

    reactions.sort(key=lambda r: r["reaction_id"])
    ambiguous_reaction_ids = [r["reaction_id"] for r in reactions if not r["conf_trusted"]]
    trusted_reaction_ids = [r["reaction_id"] for r in reactions if r["conf_trusted"]]

    confs = [r["confidence"] for r in reactions if r["confidence"] is not None]
    stats = {
        "n_molecules": len(molecules),
        "n_fragments": len(fragments),
        "n_reactions": len(reactions),
        "n_reactions_trusted": len(trusted_reaction_ids),
        "n_reactions_ambiguous": len(ambiguous_reaction_ids),
        "n_skipped": sum(skip_reasons.values()),
        "skip_reasons": dict(sorted(skip_reasons.items())),
        "n_transfer_edges": len(transfers),
        "n_split_reactions": sum(1 for r in reactions if r["split"]),
        "n_merge_reactions": sum(1 for r in reactions if r["merge"]),
        "confidence_threshold": CONF_THRESHOLD,
        "confidence_distribution": {
            "min": min(confs) if confs else None,
            "median": _median(confs),
            "max": max(confs) if confs else None,
        },
        "fragment_instances_distribution": _freq_distribution([f["n_instances"] for f in fragments.values()]),
        "ambiguity_set": {
            "reaction_ids": ambiguous_reaction_ids,
            "n": len(ambiguous_reaction_ids),
            "note": "reactions with mapper_confidence < threshold; their lineage is NEVER claimed certain",
        },
    }
    return {"molecules": molecules, "fragments": fragments, "reactions": reactions,
            "transfers": transfers, "stats": stats}


def _formula(smiles: str) -> Optional[str]:
    from rdkit.Chem import rdMolDescriptors
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    return rdMolDescriptors.CalcMolFormula(mol)


def _median(vals) -> Optional[float]:
    if not vals:
        return None
    s = sorted(vals)
    n = len(s)
    if n % 2:
        return s[n // 2]
    return (s[n // 2 - 1] + s[n // 2]) / 2.0


def _freq_distribution(vals) -> Dict:
    from collections import Counter
    return {str(k): v for k, v in sorted(Counter(vals).items())}


# --------------------------------------------------------------------------- #
# serialization (deterministic)
# --------------------------------------------------------------------------- #
def graph_records(built: Dict) -> List[Dict]:
    mols = sorted(built["molecules"].values(), key=lambda m: m["id"])
    frags = sorted(built["fragments"].values(), key=lambda f: f["id"])
    out = []
    for m in mols:
        out.append({"type": "molecule", "id": m["id"], "canonical_smiles": m["canonical_smiles"],
                    "formula": m["formula"]})
    for f in frags:
        out.append({"type": "fragment", "id": f["id"],
                    "reactant_fragment": f["reactant_fragment"], "product_fragment": f["product_fragment"]})
    for r in built["reactions"]:
        out.append({"type": "reaction", "id": r["reaction_id"], "donor_id": r["donor_id"],
                    "product_ids": r["product_ids"], "fragment_id": r["fragment_id"],
                    "confidence": r["confidence"], "conf_trusted": r["conf_trusted"],
                    "lineage_status": r["lineage_status"], "split": r["split"], "merge": r["merge"],
                    "retained_fraction": r["retained_fraction"]})
    for t in built["transfers"]:
        out.append({"type": "transfer", "id": t["id"], "molecule_id": t["molecule_id"],
                    "upstream_reaction": t["upstream_reaction"],
                    "downstream_reaction": t["downstream_reaction"]})
    return out


def fragment_records(built: Dict) -> List[Dict]:
    out = []
    for f in sorted(built["fragments"].values(), key=lambda f: f["id"]):
        out.append({
            "id": f["id"],
            "reactant_fragment": f["reactant_fragment"],
            "product_fragment": f["product_fragment"],
            "n_instances": f["n_instances"],
            "n_trusted_instances": f["n_trusted_instances"],
            "n_ambiguous_instances": f["n_ambiguous_instances"],
            "min_confidence": f["min_confidence"],
            "median_confidence": f["median_confidence"],
            "max_confidence": f["max_confidence"],
            "instances": f["instances"],
        })
    return out