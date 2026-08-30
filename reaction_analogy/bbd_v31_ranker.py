#!/usr/bin/env python3
"""BBD v3.1 per-source ranker + selector: model loading, scoring, arbitration.

Single source of truth for the v3.1 ranking logic.  Used by both the
predictor (``predict_bbd_products_v31.py``) and the scorer's ablation modes.

Architecture (task §4.1-4.2):

  3 per-source LightGBM rankers (uspto / envipath / retrieval)
    → p_source(candidate)  (predict_proba, same-source-comparable)

  1 source-selector LightGBM (4-class: uspto / envipath / retrieval / none)
    → w = (w_uspto, w_env, w_ret)  (normalised; none mass redistributed)

  final(c) = max over c's sources of (w[source] * p_source(c))

Multi-source candidates are scored in each belonging source (shadow
mechanism); the max w*p across sources is the final score.

Answer-key isolation: this file NEVER reads the answer key.
"""
from __future__ import annotations

import os
import sys

import lightgbm as lgb

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

import bbd_v3_features as F  # noqa: E402

SOURCES = ("uspto", "envipath", "retrieval")
NONE_CLASS = 3  # 4th class in selector


class V31Ranker:
    """Loads 3 per-source rankers + 1 selector, scores candidates."""

    def __init__(self, model_dir: str):
        self.source_rankers: dict[str, lgb.Booster] = {}
        self.selector: lgb.Booster | None = None
        self.fallback_envipath = False  # if envipath ranker not trained

        for src in SOURCES:
            path = os.path.join(model_dir, f"{src}_ranker.txt")
            if os.path.exists(path):
                self.source_rankers[src] = lgb.Booster(model_file=path)
            elif src == "envipath":
                self.fallback_envipath = True  # §4.2 fail-safe

        sel_path = os.path.join(model_dir, "source_selector.txt")
        if os.path.exists(sel_path):
            self.selector = lgb.Booster(model_file=sel_path)

        if not self.source_rankers:
            raise RuntimeError("No per-source rankers found in " + model_dir)

    # ------------------------------------------------------------------ #
    def _source_proba(self, candidate: dict, source_key: str) -> float:
        """Score a candidate with the per-source ranker (shadow mechanism).

        Falls back to 0.0 if the source ranker is missing or the candidate
        has no features for this source.
        """
        if source_key not in self.source_rankers:
            if source_key == "envipath" and self.fallback_envipath:
                # fail-safe: return a simple heuristic score
                # (low priority — ranker didn't train)
                return 0.01
            return 0.0
        feats = candidate.get("_v31_features", {}).get(source_key)
        if feats is None:
            return 0.0
        return float(self.source_rankers[source_key].predict([feats])[0])

    # ------------------------------------------------------------------ #
    def _selector_weights(self, candidates: list[dict]) -> dict[str, float]:
        """Compute source weights w from the selector.

        Returns {uspto: w, envipath: w, retrieval: w} with sum ≤ 1.
        If selector is missing, return uniform weights.
        """
        if self.selector is None or not candidates:
            return {s: 1.0 / 3 for s in SOURCES}

        sel_feats = candidates[0].get("_v31_selector_features")
        if sel_feats is None:
            return {s: 1.0 / 3 for s in SOURCES}

        probs = self.selector.predict([sel_feats])[0]  # 4-class
        # redistribute none mass proportional to source prior
        w = {s: probs[i] for i, s in enumerate(SOURCES)}
        none_mass = probs[NONE_CLASS]
        if none_mass > 0:
            total = sum(w.values())
            if total > 0:
                for s in SOURCES:
                    w[s] += none_mass * (w[s] / total)
        # normalise
        total = sum(w.values())
        if total > 0:
            for s in SOURCES:
                w[s] /= total
        else:
            w = {s: 1.0 / 3 for s in SOURCES}
        return w

    # ------------------------------------------------------------------ #
    def score_candidates(self, candidates: list[dict], parent_smiles: str):
        """Score all candidates in-place: adds final_score, p_source, w_source.

        Assumes ``compute_v31_case_features`` has already been called on the
        candidates list (adds ``_v31_features`` and ``_v31_selector_features``).
        """
        w = self._selector_weights(candidates)

        for c in candidates:
            src = c.get("source", "")
            best_score = 0.0
            best_source = "uspto"
            best_p = 0.0

            for sk in SOURCES:
                belongs = sk in src or (sk in ("uspto", "envipath")
                                        and src == "both")
                if not belongs:
                    continue
                p = self._source_proba(c, sk)
                wp = w[sk] * p
                if wp > best_score:
                    best_score = wp
                    best_source = sk
                    best_p = p

            c["final_score"] = round(best_score, 6)
            c["p_source"] = round(best_p, 6)
            c["w_source"] = round(w[best_source], 6)
            c["v31_weights"] = {s: round(w[s], 6) for s in SOURCES}

        # deterministic sort: (-final_score, product_smiles)
        candidates.sort(key=lambda c: (-c["final_score"], c["product_smiles"]))
        return candidates


def load_ranker(model_dir: str) -> V31Ranker:
    """Convenience: load a V31Ranker from a model directory."""
    return V31Ranker(model_dir)
