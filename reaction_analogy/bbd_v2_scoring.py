#!/usr/bin/env python3
"""BBD v2 composite ranking score (single source of truth).

Both the predictor (``predict_bbd_products_v2.py``) and the ablation re-scorer
(``score_bbd_hitk_v2.py --ablate``) import this module so that the ranking
formula lives in exactly one place.

Weight rationale (prior declarations, NOT fitted values — see task spec §4.5):

  enviPath source prior 0.40 vs USPTO 0.10
      enviPath rules are EAWAG-BBD curated biodegradation rules (domain-matched);
      USPTO templates come from a general organic-synthesis library.  The
      asymmetric prior lets strong USPTO candidates (high-freq templates) still
      overtake weak enviPath candidates (ceilings 0.95 vs 1.00), so it is not a
      hard layering.

  USPTO mpnn weight higher (0.35 vs 0.30)
      USPTO candidates carry no other site-chemistry signal besides MPNN
      atom probabilities, so the MPNN term gets more weight on that branch.

  spec (pattern-atom count of the rule/template)
      More context atoms → more specific → fewer false triggers.  Standard
      rule-systems heuristic.  enviPath's own REACTIONS_COUNT signal is weak
      (203/286 rules have only 1 supporting reaction), so ``spec`` supplements.

Red line: weights must NOT be tuned against the answer key.  If metrics miss
the gate, follow the §7 stop-and-diagnose flow — do not re-fit here.
"""
from __future__ import annotations

from math import log1p


def score_candidate(
    c: dict,
    mpnn_on: bool = True,
    src_on: bool = True,
    force_branch: str | None = None,
) -> float:
    """Composite ranking score for one candidate.

    Required fields on *c*:
        mpnn_site_mean     float  (0 if no MPNN probs available)
        mpnn_site_max      float
        pattern_atom_count int    (max context atoms among contributing rules/tpls)
        reactions_count    int    (enviPath rule support; 0 for USPTO-only)
        template_freq      int    (USPTO template frequency; 0 for enviPath-only)
        source             str    "envipath" | "uspto" | "both"

    Ablation switches:
        mpnn_on=False  → MPNN aggregate term set to 0.
        src_on=False   → both source priors (0.40, 0.10) set to 0.
        force_branch   → override source selection ("envipath"/"uspto"); used
                         by the envipath-only / uspto-only ablations.
    """
    mpnn_agg = (0.5 * c["mpnn_site_mean"] + 0.5 * c["mpnn_site_max"]) if mpnn_on else 0.0

    spec = min(1.0, log1p(c["pattern_atom_count"]) / log1p(25))
    rc   = min(1.0, log1p(c["reactions_count"]) / log1p(10))
    freq = min(1.0, log1p(c["template_freq"]) / log1p(50))

    env_prior = 0.40 if src_on else 0.0
    usp_prior = 0.10 if src_on else 0.0

    env_score = env_prior + 0.30 * mpnn_agg + 0.15 * rc   + 0.15 * spec
    usp_score = usp_prior + 0.35 * mpnn_agg + 0.35 * freq + 0.15 * spec

    branch = force_branch if force_branch is not None else c.get("source", "uspto")
    if branch == "envipath":
        return env_score
    if branch == "uspto":
        return usp_score
    return max(env_score, usp_score)  # "both"


def rank_candidates(cands: list[dict], **kw) -> list[dict]:
    """Return candidates sorted by (-score, product_smiles) — deterministic.

    Mutates each candidate by setting ``c['score']``.  Tie-break is the
    product SMILES ascending (NOT dict insertion order — see task spec §4.5
    and diagnosis #4 on why v1's insertion-order tie-break was arbitrary).
    """
    for c in cands:
        c["score"] = score_candidate(c, **kw)
    cands.sort(key=lambda c: (-c["score"], c["product_smiles"]))
    return cands


# --------------------------------------------------------------------------- #
# Self-test: DCE (ClCCCl) enviPath candidate — task spec §4.5 example
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    # envipath candidate for DCE, product OCCCl (true product), bt0334-like rule
    ex = {
        "product_smiles": "OCCCl",
        "mpnn_site_mean": 0.97,
        "mpnn_site_max": 0.99,
        "pattern_atom_count": 4,
        "reactions_count": 2,
        "template_freq": 0,
        "source": "envipath",
    }
    s = score_candidate(ex)
    # mpnn_agg = 0.5*0.97 + 0.5*0.99 = 0.98
    # spec     = log1p(4)/log1p(25)  ≈ 1.386/3.258 ≈ 0.4254
    # rc       = log1p(2)/log1p(10)  ≈ 1.099/2.398 ≈ 0.4581
    # env = 0.40 + 0.30*0.98 + 0.15*0.4581 + 0.15*0.4254
    #     = 0.40 + 0.294 + 0.0687 + 0.0638 = 0.8265
    expected = 0.40 + 0.30 * 0.98 + 0.15 * (log1p(2) / log1p(10)) + 0.15 * (log1p(4) / log1p(25))
    print(f"DCE candidate score = {s:.4f}  (expected ≈ {expected:.4f})")
    assert abs(s - expected) < 1e-9, "score mismatch"
    assert 0.83 < s < 0.84, f"score unexpectedly far from ~0.83: {s}"

    # ablation: mpnn off
    s_no_mpnn = score_candidate(ex, mpnn_on=False)
    # env = 0.40 + 0 + 0.15*rc + 0.15*spec
    assert abs(s_no_mpnn - (0.40 + 0.15 * (log1p(2) / log1p(10)) + 0.15 * (log1p(4) / log1p(25)))) < 1e-9

    # ablation: src off (priors zeroed)
    s_no_src = score_candidate(ex, src_on=False)
    assert abs(s_no_src - (0.30 * 0.98 + 0.15 * (log1p(2) / log1p(10)) + 0.15 * (log1p(4) / log1p(25)))) < 1e-9

    # both-source candidate takes max
    both = dict(ex, source="both", template_freq=50)
    sb = score_candidate(both)
    se = score_candidate(dict(ex, source="envipath"))
    su = score_candidate(dict(ex, source="uspto", template_freq=50))
    assert abs(sb - max(se, su)) < 1e-9

    print("All self-tests passed.")
