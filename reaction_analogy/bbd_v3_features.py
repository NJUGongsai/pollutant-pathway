#!/usr/bin/env python3
"""BBD v3 candidate-level features (single source of truth).

Training (``train_bbd_v3_ranker.py``) and inference
(``predict_bbd_products_v3.py``) both call ``candidate_features`` so that the
feature definition lives in exactly one place.

Feature groups (22 total, no MPNN — see design note below):

  source       3 one-hot (is_uspto / is_envipath / is_retrieval) + source_id
  frequency    log1p(template_freq), log1p(reactions_count), log1p(n_evidence)
  similarity   max_tanimoto, mean_tanimoto, donor_exact_match
  specificity  spec = log1p(pattern_atom_count) / log1p(25)
  product-lvl  product_mw, n_atoms, n_rings, has_charge
  substrate    substrate_mw, n_atoms, n_rings, aromatic_ratio
  diff         mw_diff, n_atoms_diff, n_rings_diff

Design note — no MPNN features:
  v2 ablation showed MPNN atom probabilities have near-zero discriminative
  power on BBD substrates (mpnn-off Hit@10 = 57.0% = same as full v2).
  Computing MPNN probs for ~12k RHEA training educts requires a chenyu GPU
  step; per task §4.4 / §8 red-line 8, we choose "both sides without" and
  delete the MPNN feature columns entirely, avoiding train/inference
  distribution mismatch.

Answer-key isolation: this file NEVER reads the answer key.
"""
from __future__ import annotations

from math import log1p

from rdkit import Chem, RDLogger
from rdkit.Chem import Descriptors, rdMolDescriptors

RDLogger.DisableLog("rdApp.*")

# Source combination → integer ID (deterministic)
_SOURCE_IDS = {
    "uspto": 0, "envipath": 1, "retrieval": 2,
    "uspto+envipath": 3, "uspto+retrieval": 4,
    "envipath+retrieval": 5, "all": 6,
}

FEATURE_NAMES = [
    # source (4)
    "is_uspto", "is_envipath", "is_retrieval", "source_id",
    # frequency (3)
    "log1p_template_freq", "log1p_reactions_count", "log1p_n_evidence",
    # similarity (3)
    "max_tanimoto", "mean_tanimoto", "donor_exact_match",
    # specificity (1)
    "spec",
    # product-level (4)
    "product_mw", "product_n_atoms", "product_n_rings", "product_has_charge",
    # substrate-level (4)
    "substrate_mw", "substrate_n_atoms", "substrate_n_rings",
    "substrate_aromatic_ratio",
    # diff (3)
    "mw_diff", "n_atoms_diff", "n_rings_diff",
]
N_FEATURES = len(FEATURE_NAMES)


def _mol_props(smi: str) -> dict | None:
    """Compute molecular properties without AddHs (avoids atom-index shift)."""
    m = Chem.MolFromSmiles(smi)
    if m is None:
        return None
    n_atoms = m.GetNumHeavyAtoms()
    n_rings = rdMolDescriptors.CalcNumRings(m)
    mw = Descriptors.MolWt(m)
    has_charge = any(a.GetFormalCharge() != 0 for a in m.GetAtoms())
    n_aromatic = sum(1 for a in m.GetAtoms() if a.GetIsAromatic())
    aromatic_ratio = n_aromatic / n_atoms if n_atoms else 0.0
    return {
        "mw": mw, "n_atoms": n_atoms, "n_rings": n_rings,
        "has_charge": int(has_charge),
        "aromatic_ratio": round(aromatic_ratio, 6),
    }


def candidate_features(cand: dict, parent_smiles: str) -> list[float] | None:
    """Compute the feature vector for one candidate.

    *cand* must have: source, template_freq, reactions_count,
    pattern_atom_count, n_evidence, max_tanimoto, mean_tanimoto,
    donor_exact_match, product_smiles.
    *parent_smiles* is the substrate SMILES.

    Returns a list of N_FEATURES floats, or None if the product or parent
    cannot be parsed (fail-closed — the candidate is dropped).
    """
    src = cand.get("source", "")
    is_uspto = 1.0 if "uspto" in src else 0.0
    is_envipath = 1.0 if "envipath" in src else 0.0
    is_retrieval = 1.0 if "retrieval" in src else 0.0
    source_id = float(_SOURCE_IDS.get(src, 0))

    log1p_freq = log1p(cand.get("template_freq", 0))
    log1p_rc = log1p(cand.get("reactions_count", 0))
    log1p_ev = log1p(cand.get("n_evidence", 0))

    max_t = cand.get("max_tanimoto", 0.0)
    mean_t = cand.get("mean_tanimoto", 0.0)
    donor_exact = 1.0 if cand.get("donor_exact_match", False) else 0.0

    pac = cand.get("pattern_atom_count", 0)
    spec = min(1.0, log1p(pac) / log1p(25))

    prod_smi = cand.get("product_smiles", "")
    pprops = _mol_props(prod_smi)
    if pprops is None:
        return None

    sps = _mol_props(parent_smiles)
    if sps is None:
        return None

    return [
        # source
        is_uspto, is_envipath, is_retrieval, source_id,
        # frequency
        log1p_freq, log1p_rc, log1p_ev,
        # similarity
        max_t, mean_t, donor_exact,
        # specificity
        spec,
        # product-level
        pprops["mw"], pprops["n_atoms"], pprops["n_rings"],
        pprops["has_charge"],
        # substrate-level
        sps["mw"], sps["n_atoms"], sps["n_rings"],
        sps["aromatic_ratio"],
        # diff
        pprops["mw"] - sps["mw"],
        pprops["n_atoms"] - sps["n_atoms"],
        pprops["n_rings"] - sps["n_rings"],
    ]
