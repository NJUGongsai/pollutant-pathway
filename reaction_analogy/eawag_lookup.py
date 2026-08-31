#!/usr/bin/env python3
"""BBD P4.2 Engine D — EAWAG known-pathway lookup.

Engine D produces candidates by looking the (stereo-blind canonical) parent up
in the EAWAG-BBD public reaction library (``donor_product.jsonl``, 1,066 curated
reactions).  When the parent *is* a recorded donor, every recorded product of
that donor becomes a candidate, ranked by descending Tanimoto(parent, product)
(Morgan r=2 / 2048-bit, identical to retrieval Engine C).  Each candidate
carries an ``eawag_reactions`` evidence list (``btid#reac_id``) so a reviewer
can trace it back to the EAWAG reaction page.

This is the curated-knowledge endpoint of the four-engine spectrum (synthesis
templates → generic rules → similar-reaction transfer → exact known pathway),
and is isomorphic to enviPath's documented "known-pathway lookup" baseline mode.

**Sink-not-delete for ions/cofactors:** ion fragments (``[Cl-]``, ``C=O``, …)
and cofactor conjugates (NAD⁺, …) recorded as co-products are *sunk* to the
bottom of the lookup block (flagged, not removed) so that a whitelisted species
which happens to be a legitimate accepted product (e.g. formaldehyde ``C=O``)
remains available for Hit@K.  Ranking key:
``(filtered, -tanimoto, product_smiles)`` where ``filtered`` = ion ∨ cofactor.

Answer-key isolation: this file NEVER reads the answer key.  It reads only
``donor_product.jsonl`` — public EAWAG-BBD library data, not the benchmark's
answer key (the two share provenance but are distinct artefacts; the three-
caliber disclosure in the scorer/report enforces the separation).
"""
from __future__ import annotations

import importlib.util
import json
import os
from collections import defaultdict
from typing import Any

from rdkit import Chem, RDLogger
from rdkit.Chem import AllChem, DataStructs

RDLogger.DisableLog("rdApp.*")

_HERE = os.path.dirname(os.path.abspath(__file__))


def _load_sibling(name: str):
    spec = importlib.util.spec_from_file_location(
        name, os.path.join(_HERE, f"{name}.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


IF = _load_sibling("bbd_v32_ion_filter")    # reuse ion white-list (single source)
CF = _load_sibling("bbd_cofactor_filter")  # cofactor skeleton filter


def stereo_blind(smi: str) -> str | None:
    m = Chem.MolFromSmiles(smi)
    return Chem.MolToSmiles(m, isomericSmiles=False) if m is not None else None


def _fp(smi: str):
    m = Chem.MolFromSmiles(smi)
    return AllChem.GetMorganFingerprintAsBitVect(m, 2, nBits=2048) if m else None


def _tanimoto(a_smi: str, b_fp) -> float:
    af = _fp(a_smi)
    if af is None or b_fp is None:
        return 0.0
    return DataStructs.TanimotoSimilarity(af, b_fp)


def build_index(donor_product_path: str) -> dict[str, list[dict]]:
    """Index ``donor_product.jsonl`` by stereo-blind canonical donor SMILES.

    Returns ``{donor_sb: [{product_sb, product_smiles_full, btid, reac_id}, …]}``.
    Parse failures are skipped (fail-closed); a ``_parse_fail`` counter is kept
    on the returned dict under key ``"__parse_fail__"`` for diagnostics.
    """
    index: dict[str, list[dict]] = defaultdict(list)
    parse_fail = 0
    with open(donor_product_path) as f:
        for line in f:
            r = json.loads(line)
            d = stereo_blind(r.get("donor_smiles", ""))
            p = stereo_blind(r.get("product_smiles", ""))
            if d is None or p is None:
                parse_fail += 1
                continue
            index[d].append({
                "product_sb": p,
                "product_smiles_full": r.get("product_smiles", p),
                "btid": r.get("btid", ""),
                "reac_id": r.get("reac_id", ""),
            })
    index["__parse_fail__"] = [{"count": parse_fail}]
    return dict(index)


def lookup(index: dict, parent_smiles: str) -> list[dict[str, Any]]:
    """Return Engine-D candidates for *parent_smiles*, or ``[]`` if no hit.

    Each candidate dict (stereo-blind canonical, ready for the hybrid merge):
        product_smiles      : stereo-blind canonical product
        product_smiles_full : original EAWAG product SMILES
        source              : "eawag_lookup"
        layer               : "lookup"
        eawag_reactions     : ["btid#reac_id", …]   (trace to EAWAG page)
        donor_exact_match   : True
        n_evidence          : number of EAWAG reactions for this donor
        tanimoto            : Tanimoto(parent, product)
        ion_filtered        : bool   (co-product ion, sunk)
        cofactor_filtered   : bool   (cofactor conjugate, sunk)
        filtered            : ion_filtered | cofactor_filtered
    Sorted by (filtered, -tanimoto, product_smiles).
    """
    p = stereo_blind(parent_smiles)
    if p is None or p not in index:
        return []
    recs = index[p]
    pfp = _fp(p)
    out: list[dict[str, Any]] = []
    seen_bt: set[tuple] = set()
    for rec in recs:
        key = (rec["btid"], rec["reac_id"])
        if key in seen_bt:
            continue
        seen_bt.add(key)
        prod = rec["product_sb"]
        ion = IF.is_ion_fragment(prod)
        cof = CF.is_cofactor_conjugate(prod)
        out.append({
            "product_smiles": prod,
            "product_smiles_full": rec["product_smiles_full"],
            "source": "eawag_lookup",
            "layer": "lookup",
            "eawag_reactions": [f'{rec["btid"]}#{rec["reac_id"]}'],
            "donor_exact_match": True,
            "n_evidence": len(recs),
            "tanimoto": round(_tanimoto(prod, pfp), 6),
            "ion_filtered": ion,
            "cofactor_filtered": cof,
            "filtered": bool(ion or cof),
        })
    out.sort(key=lambda c: (c["filtered"], -c["tanimoto"], c["product_smiles"]))
    return out


if __name__ == "__main__":
    import sys
    dp = os.path.join(_HERE, "data/bbd_expand/donor_product.jsonl")
    idx = build_index(dp)
    pf = idx.pop("__parse_fail__", [{"count": 0}])[0]["count"]
    print(f"index: {len(idx)} donors, {pf} parse-fail")
    for parent in sys.argv[1:]:
        cands = lookup(idx, parent)
        print(f"\nparent={parent} -> {len(cands)} candidate(s):")
        for c in cands[:5]:
            print(f"  {c['product_smiles']:40s} t={c['tanimoto']:.3f}"
                  f" ion={c['ion_filtered']} cof={c['cofactor_filtered']}"
                  f" ev={c['eawag_reactions']}")
