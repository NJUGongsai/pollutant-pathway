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


# --------------------------------------------------------------------------- #
# v3.1 features — per-source ranker + selector (new, does not modify v3)
# --------------------------------------------------------------------------- #
# Per-source ranker candidate-level: 27 dims (22 v3 + 5 new)
#   source_freq_rank      percentile of template_freq within case×source
#   source_evidence_rank  percentile of n_evidence*max_tanimoto within case×source
#   prob_gap_to_best      v3_proba - max(v3_proba in same case×source)
#   n_sources             1/2/3
#   is_multi_source       0/1
#
# Selector group-level: 17 dims (substrate props + per-source counts +
#   v3_proba stats + chemistry flags)

FEATURE_NAMES_V31 = FEATURE_NAMES + [
    "source_freq_rank", "source_evidence_rank", "prob_gap_to_best",
    "n_sources", "is_multi_source",
]
N_FEATURES_V31 = len(FEATURE_NAMES_V31)  # 27

SELECTOR_FEATURE_NAMES = [
    # substrate (4)
    "substrate_mw", "substrate_n_atoms", "substrate_aromatic_ratio",
    "substrate_has_charge",
    # per-source counts (3)
    "n_cands_uspto", "n_cands_envipath", "n_cands_retrieval",
    # v3 proba per-source stats (6)
    "v3_proba_max_uspto", "v3_proba_max_envipath", "v3_proba_max_retrieval",
    "v3_proba_top3mean_uspto", "v3_proba_top3mean_envipath",
    "v3_proba_top3mean_retrieval",
    # chemistry flags (4)
    "substrate_has_halogen", "substrate_has_sulfur",
    "substrate_has_phosphorus", "substrate_has_nitro",
]
N_SELECTOR_FEATURES = len(SELECTOR_FEATURE_NAMES)  # 17


def _percentile_rank(values: list[float], idx: int) -> float:
    """Percentile rank of values[idx] within values (0-1)."""
    if len(values) <= 1:
        return 0.5
    v = values[idx]
    n_below = sum(1 for x in values if x < v)
    return n_below / (len(values) - 1)


def _substrate_chem_flags(smi: str) -> dict:
    """One-hot chemistry flags: halogen, sulfur, phosphorus, nitro."""
    m = Chem.MolFromSmiles(smi)
    if m is None:
        return {"has_halogen": 0, "has_sulfur": 0, "has_phosphorus": 0,
                "has_nitro": 0}
    syms = {a.GetSymbol() for a in m.GetAtoms()}
    has_nitro = 0
    try:
        has_nitro = 1 if m.HasSubstructMatch(
            Chem.MolFromSmarts("[N+](=O)[O-]")) else 0
    except Exception:
        pass
    return {
        "has_halogen": int(bool(syms & {"F", "Cl", "Br", "I"})),
        "has_sulfur": int("S" in syms),
        "has_phosphorus": int("P" in syms),
        "has_nitro": has_nitro,
    }


def compute_v31_case_features(candidates: list[dict], parent_smiles: str):
    """Compute v3.1 features for all candidates in a case.

    Adds to each candidate dict (in-place):
      - ``_v31_features``: dict {source_key: [27 floats]} for each source
        the candidate belongs to (shadow mechanism).
      - ``_v31_selector_features``: [17 floats] (same for all candidates in
        the case — stored on the first candidate).

    *candidates* must have: source, template_freq, reactions_count,
    pattern_atom_count, n_evidence, max_tanimoto, mean_tanimoto,
    donor_exact_match, product_smiles, and optionally ranker_proba (v3 proba).
    """
    # ---- group candidates by source ----
    source_groups: dict[str, list[int]] = {"uspto": [], "envipath": [], "retrieval": []}
    for i, c in enumerate(candidates):
        src = c.get("source", "")
        for sk in source_groups:
            if sk in src or (sk == "uspto" and src == "both") or \
               (sk == "envipath" and src == "both"):
                source_groups[sk].append(i)

    # ---- compute source-internal rankings ----
    for sk, indices in source_groups.items():
        if not indices:
            continue
        freqs = [candidates[i].get("template_freq", 0) for i in indices]
        evids = [candidates[i].get("n_evidence", 0) * candidates[i].get("max_tanimoto", 0.0)
                 for i in indices]
        probas = [candidates[i].get("ranker_proba", 0.0) for i in indices]
        max_proba = max(probas) if probas else 0.0
        for j, i in enumerate(indices):
            c = candidates[i]
            freq_rank = _percentile_rank(freqs, j)
            evid_rank = _percentile_rank(evids, j)
            prob_gap = c.get("ranker_proba", 0.0) - max_proba
            c.setdefault("_source_ranks", {})[sk] = {
                "freq_rank": freq_rank,
                "evid_rank": evid_rank,
                "prob_gap": prob_gap,
            }

    # ---- compute per-(candidate, source) features ----
    for c in candidates:
        src = c.get("source", "")
        n_sources = sum(1 for sk in ("uspto", "envipath", "retrieval")
                        if sk in src or (sk in ("uspto", "envipath") and src == "both"))
        is_multi = 1.0 if n_sources > 1 else 0.0

        base = candidate_features(c, parent_smiles)
        if base is None:
            c["_v31_features"] = {}
            continue

        c["_v31_features"] = {}
        for sk in ("uspto", "envipath", "retrieval"):
            belongs = sk in src or (sk in ("uspto", "envipath") and src == "both")
            if not belongs:
                continue
            ranks = c.get("_source_ranks", {}).get(sk, {})
            c["_v31_features"][sk] = base + [
                ranks.get("freq_rank", 0.5),
                ranks.get("evid_rank", 0.5),
                ranks.get("prob_gap", 0.0),
                float(n_sources),
                is_multi,
            ]

    # ---- compute selector features ----
    sps = _mol_props(parent_smiles)
    chem = _substrate_chem_flags(parent_smiles)
    src_counts = {}
    src_proba_max = {}
    src_proba_top3 = {}
    for sk in ("uspto", "envipath", "retrieval"):
        idxs = source_groups[sk]
        src_counts[sk] = len(idxs)
        probas = sorted([candidates[i].get("ranker_proba", 0.0)
                         for i in idxs], reverse=True)
        src_proba_max[sk] = probas[0] if probas else 0.0
        src_proba_top3[sk] = (sum(probas[:3]) / 3) if probas else 0.0

    sel_feats = [
        sps["mw"], sps["n_atoms"], sps["aromatic_ratio"], sps["has_charge"],
        src_counts["uspto"], src_counts["envipath"], src_counts["retrieval"],
        src_proba_max["uspto"], src_proba_max["envipath"],
        src_proba_max["retrieval"],
        src_proba_top3["uspto"], src_proba_top3["envipath"],
        src_proba_top3["retrieval"],
        chem["has_halogen"], chem["has_sulfur"],
        chem["has_phosphorus"], chem["has_nitro"],
    ]
    for c in candidates:
        c["_v31_selector_features"] = sel_feats
