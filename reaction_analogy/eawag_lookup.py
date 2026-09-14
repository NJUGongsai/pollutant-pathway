#!/usr/bin/env python3
"""BBD P4.2 Engine D — EAWAG known-pathway lookup.

Engine D produces candidates by looking the parent up in the EAWAG-BBD public
reaction library (``donor_product.jsonl``, 1,066 curated reactions).  The
parent is canonicalized to its **charge-normalized + stereo-blind canonical**
identity (v3.3 convention: ``stereo_blind(normalize_charge_smiles(smi))``,
reusing ``bbd_v33_fusion.normalize_charge_smiles``) and looked up in the donor
index, which is keyed the same way.  When the parent *is* a recorded donor,
every recorded product of that donor becomes a candidate, ranked by descending
Tanimoto(parent, product) (Morgan r=2 / 2048-bit, identical to retrieval
Engine C).  Each candidate carries an ``eawag_reactions`` evidence list
(``btid#reac_id``) so a reviewer can trace it back to the EAWAG reaction page.

**2026-09-14 charge-key fix (§7 of the DBP hybrid rerun report):** EAWAG-BBD
stores many acid species as ANIONS (e.g. phthalic acid as
``O=C([O-])c1ccccc1C(=O)[O-]``) while the prediction layer emits the NEUTRAL
form.  Keying both sides by the charge-normalized identity closes that gap —
the anion-keyed donor records are now reachable from the neutral query (and
vice versa).  If ``bbd_v33_fusion`` is unavailable the module falls back to
the legacy raw stereo-blind keys (module flag ``KEY_MODE`` records which mode
is active) so Engine D keeps working in a standalone checkout.

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


def _load_charge_normalizer():
    """Locate ``bbd_v33_fusion`` (lazy/protected), or ``None`` if absent.

    Tries the file-based sibling load first (sys.path-independent), then the
    plain ``from bbd_v33_fusion import ...`` import.  ``None`` ⇒ Engine D
    falls back to legacy raw stereo-blind keys.
    """
    mod = None
    try:
        mod = _load_sibling("bbd_v33_fusion")
    except Exception:
        mod = None
    if mod is None or not hasattr(mod, "normalize_charge_smiles"):
        try:
            import bbd_v33_fusion as mod  # noqa: F811 — sys.path fallback
        except Exception:
            mod = None
    if mod is not None and hasattr(mod, "normalize_charge_smiles"):
        return mod
    return None


V33 = _load_charge_normalizer()
# Module-level flag: which donor-key mode is active (see build_index docstring).
KEY_MODE = "charge_normalized" if V33 is not None else "stereo_blind"


def stereo_blind(smi: str) -> str | None:
    m = Chem.MolFromSmiles(smi)
    return Chem.MolToSmiles(m, isomericSmiles=False) if m is not None else None


def _cn_identity(smi: str) -> str | None:
    """Charge-normalized + stereo-blind canonical identity (v3.3 convention).

    ``stereo_blind(normalize_charge_smiles(smi))`` — the same identity used by
    ``expand_bbd_routes._identity``, so the neutral acid and its anion map to
    one key.  Falls back to plain ``stereo_blind`` when the fusion module is
    absent (KEY_MODE == "stereo_blind") or on normalization failure, keeping
    Engine D fail-closed instead of crashy.
    """
    if V33 is None:
        return stereo_blind(smi)
    norm = V33.normalize_charge_smiles(smi)
    if norm is None:
        return stereo_blind(smi)
    return V33.stereo_blind(norm) or stereo_blind(smi)


def _fp(smi: str):
    m = Chem.MolFromSmiles(smi)
    return AllChem.GetMorganFingerprintAsBitVect(m, 2, nBits=2048) if m else None


def _tanimoto(a_smi: str, b_fp) -> float:
    af = _fp(a_smi)
    if af is None or b_fp is None:
        return 0.0
    return DataStructs.TanimotoSimilarity(af, b_fp)


def build_index(donor_product_path: str) -> dict[str, list[dict]]:
    """Index ``donor_product.jsonl`` by charge-normalized donor identity.

    Keys are ``stereo_blind(normalize_charge_smiles(donor_smiles))`` (v3.3
    identity convention), so an EAWAG anion donor (e.g. phthalate
    ``O=C([O-])c1ccccc1C(=O)[O-]``) and its neutral acid share one key and
    both query forms hit the same records.  If ``bbd_v33_fusion`` is absent
    (KEY_MODE == "stereo_blind") the legacy raw stereo-blind key is used.

    Returns ``{donor_key: [{product_sb, product_cn, product_smiles_full,
    btid, reac_id}, …]}`` where ``product_sb`` is the raw stereo-blind
    canonical product (unchanged — the emitted candidate identity) and
    ``product_cn`` is the charge-normalized product identity (for downstream
    merging, e.g. the hybrid route layer).  Parse failures are skipped
    (fail-closed); a ``_parse_fail`` counter is kept on the returned dict
    under key ``"__parse_fail__"`` for diagnostics.
    """
    index: dict[str, list[dict]] = defaultdict(list)
    parse_fail = 0
    with open(donor_product_path) as f:
        for line in f:
            r = json.loads(line)
            d = _cn_identity(r.get("donor_smiles", ""))
            p = stereo_blind(r.get("product_smiles", ""))
            if d is None or p is None:
                parse_fail += 1
                continue
            index[d].append({
                "product_sb": p,
                "product_cn": _cn_identity(r.get("product_smiles", "")),
                "product_smiles_full": r.get("product_smiles", p),
                "btid": r.get("btid", ""),
                "reac_id": r.get("reac_id", ""),
            })
    index["__parse_fail__"] = [{"count": parse_fail}]
    return dict(index)


def lookup(index: dict, parent_smiles: str) -> list[dict[str, Any]]:
    """Return Engine-D candidates for *parent_smiles*, or ``[]`` if no hit.

    The parent is canonicalized exactly like the index keys
    (``_cn_identity``: charge-normalized + stereo-blind) before the key
    match, so a neutral acid query hits anion-keyed EAWAG records and vice
    versa (2026-09-14 fix).  The in-block Tanimoto ranking, however, uses the
    RAW stereo-blind query fingerprint (pre-fix semantics): charge
    normalization is an identity/matching concern, not a similarity concern —
    the query-vs-recorded-product structural comparison is deliberately
    unchanged by the key fix.

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
    p = _cn_identity(parent_smiles)
    if p is None or p not in index:
        return []
    recs = index[p]
    pfp = _fp(stereo_blind(parent_smiles) or p)
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
    print(f"index: {len(idx)} donors (key_mode={KEY_MODE}), {pf} parse-fail")
    for parent in sys.argv[1:]:
        cands = lookup(idx, parent)
        print(f"\nparent={parent} -> {len(cands)} candidate(s):")
        for c in cands[:5]:
            print(f"  {c['product_smiles']:40s} t={c['tanimoto']:.3f}"
                  f" ion={c['ion_filtered']} cof={c['cofactor_filtered']}"
                  f" ev={c['eawag_reactions']}")
