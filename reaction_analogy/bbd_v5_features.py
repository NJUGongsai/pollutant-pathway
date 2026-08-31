#!/usr/bin/env python3
"""BBD v5 candidate-level features: 28-dim (27 v3.1 + is_eawag_domain).

Additive wrapper over ``bbd_v3_features`` — does NOT modify
``compute_v31_case_features``.  The single new feature ``is_eawag_domain``
(1.0 for candidates of EAWAG-donor educts at training time, 0.0 for RHEA
candidates and for ALL BBD blind parents at predict time) lets the
per-source rankers learn the BBD-domain evidence distribution without
conflating the two domains (task §5.2).

At predict time the column is all-0 (leak-filter-guaranteed — the 84
blind-parent EAWAG donors are excluded from training, and no BBD blind
parent is an EAWAG training educt), so it carries no discriminative power
at inference; it only shapes training-time evidence weighting per domain.
This design is documented in the P5 REPORT.

The feature vectors are stored on the same in-place ``_v31_features[sk]``
key produced by ``compute_v31_case_features`` (the key name is unchanged;
only the list length grows from 27 to 28), so every downstream consumer
(``train_bbd_ranker_v2`` training, ``predict_bbd_hybrid`` v5 re-scoring)
reads ``c["_v31_features"][sk]`` exactly as before.

Answer-key isolation: this file NEVER reads the answer key.
"""
from __future__ import annotations

import bbd_v3_features as F

FEATURE_NAMES_V5 = F.FEATURE_NAMES_V31 + ["is_eawag_domain"]
N_FEATURES_V5 = len(FEATURE_NAMES_V5)  # 28


def compute_v5_case_features(candidates: list[dict], parent_smiles: str,
                             is_eawag_domain: bool | int | float) -> None:
    """Compute 28-dim v5 features for all candidates in a case (in-place).

    Calls ``F.compute_v31_case_features`` (27-dim) then appends
    ``is_eawag_domain`` to each candidate's ``_v31_features[sk]`` list.
    ``is_eawag_domain`` is case-level (constant for all candidates of one
    educt): 1.0 for EAWAG-donor educts at training, 0.0 for RHEA educts and
    for every BBD blind parent at predict time.
    """
    F.compute_v31_case_features(candidates, parent_smiles)
    dom = float(is_eawag_domain)
    for c in candidates:
        feats = c.get("_v31_features")
        if not feats:
            continue
        for sk in list(feats.keys()):
            feats[sk] = feats[sk] + [dom]
