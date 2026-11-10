"""RA-MG ranker — Route A ranking with the **de-transductive generalized
specificity** (see ``src/ra/specificity.py``) in place of the transductive
``log2(83 / support)`` specificity of ``rank_relevance``.

Everything else is identical to RA-RREF and reused verbatim from
``rank_relevance`` (tier-first ordering, hand chemistry-prior relevance table,
frozen M3 site compatibility, provenance reconstruction, deterministic output):

    score(rule)  = w_rel*relevance(rule) + w_spec*specificity_gen(rule) + w_site*site(rule)
    specificity_gen(rule) = log1p(constraint) + 0.50*n_hetero                  (pure fn)
    score(y)     = max over producing rules r of score(r)
    order        = tier desc -> score desc -> candidate_smiles asc
    TOP_K        = 10 strict.

``specificity_gen`` is computed only from the rule's own SMARTS — **no** blind
parents, **no** answer key.  ``rank_relevance`` stays untouched as the archived
old-signal ranker (old numbers in ``reports/RA_RREF_REPORT.md``).
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from ra import rank_relevance as rr
from ra import specificity as gs

# --------------------------------------------------------------------------- #
# pre-registered constants (see reports/RA_MG_RANKING_KEY.md)
# --------------------------------------------------------------------------- #

RANKING_KEY = (
    "MG_V1: order = (tier desc) -> (score desc) -> (candidate_smiles asc); "
    "tier = 'envipath' iff candidate produced by >=1 enviPath SMARTS rule else "
    "'rhea'; score = max over producing rules r of "
    "(w_rel*relevance(r) + w_spec*specificity_gen(r) + w_site*site(r)); "
    "relevance = hand chemistry-prior family priority; "
    "specificity_gen = log1p(constraint) + 0.50*n_hetero "
    "(pure function of the rule SMARTS; constraint = n_rec + 2*n_hal + n_hcnt "
    "+ 2*n_conn + 2*n_charge; complexity is computed for audit but weight 0); "
    "site = sitecompat_v1 per-rule penalty (0/-0.25/-1.0); "
    "TOP_K = 10 strict."
)

TOP_K = rr.TOP_K
TIER_ENVIPATH = rr.TIER_ENVIPATH
TIER_RHEA = rr.TIER_RHEA
STATUS_RANKED = rr.STATUS_RANKED
ABSTAIN_NO_CANDIDATE = rr.ABSTAIN_NO_CANDIDATE

W_REL = rr.W_REL      # 0.20
W_SPEC = 1.00          # specificity remains the dominant signal
W_SITE = rr.W_SITE    # 0.10


# --------------------------------------------------------------------------- #
# rule data (specificity scalar + features), computed from the rules only
# --------------------------------------------------------------------------- #

def build_rule_data(templates: Dict[str, str]) -> Dict[str, dict]:
    """template_id -> {"specificity": float, "features": dict}.

    The transductive ``build_rule_support`` (83 parents) is NOT used.  A rule that
    fails to parse contributes specificity 0.0 (neutral, fail-closed); in practice
    such a rule was already dropped by ``build_reactions`` and generates nothing.
    """
    out: Dict[str, dict] = {}
    for tid in sorted(templates):
        feats = gs.smarts_specificity_features(templates[tid])
        if "error" in feats:
            spec = 0.0
        else:
            spec = gs.specificity(templates[tid])
            spec = 0.0 if spec is None else round(spec, 6)
        out[tid] = {"specificity": spec, "features": feats}
    return out


# --------------------------------------------------------------------------- #
# ranking (mirrors rank_relevance.rank_* with the new specificity signal)
# --------------------------------------------------------------------------- #

def _rule_score(tid: str, rule_data: Dict[str, dict], verdicts: Dict[str, str],
                bbd: Dict[str, dict]) -> Tuple[float, dict]:
    bt = rr.bt_of(tid)
    fam = rr.family_of(bt)
    rel = rr.relevance_priority(bt)
    rd = rule_data.get(tid, {"specificity": 0.0, "features": {}})
    spec = rd["specificity"]
    feats = rd["features"]
    site = rr.site_penalty(tid, verdicts)
    score = round(W_REL * rel + W_SPEC * spec + W_SITE * site, 8)
    meta = {
        "source_id": tid,
        "bt_rule": bt,
        "family": fam,
        "relevance": rel,
        "specificity_gen": spec,
        "constraint": feats.get("constraint"),
        "n_hetero": feats.get("n_hetero"),
        "complexity": feats.get("complexity"),
        "n_atoms": feats.get("n_atoms"),
        "site_penalty": site,
    }
    if bbd and bt and bt in bbd:
        meta["description"] = bbd[bt].get("description")
    return score, meta


def rank_case(case_id: str, pool: List[str],
              prov: Dict[str, List[str]],
              rule_data: Dict[str, dict], verdicts: Dict[str, str],
              bbd: Dict[str, dict], k: int = TOP_K) -> dict:
    """Rank one case's pool (plain SMILES) -> {'case_id','status','ranked',...}."""
    if not pool:
        return {
            "case_id": case_id,
            "status": ABSTAIN_NO_CANDIDATE,
            "n_pool": 0,
            "ranked": [],
            "abstention": {"type": ABSTAIN_NO_CANDIDATE,
                           "reason": "empty candidate pool"},
        }

    prov_map = prov.get(case_id, {})
    scored: List[Tuple[float, str, str, Optional[dict]]] = []
    for smi in pool:
        tids = prov_map.get(smi, [])
        if tids:
            tier = TIER_ENVIPATH
            best = None
            best_score = None
            for tid in tids:
                sc, meta = _rule_score(tid, rule_data, verdicts, bbd)
                if best_score is None or sc > best_score:
                    best_score = sc
                    best = meta
            scored.append((best_score, smi, tier, best))
        else:
            scored.append((float("-inf"), smi, TIER_RHEA, None))

    def key(t):
        sc, smi, tier, _ = t
        tier_num = 0 if tier == TIER_ENVIPATH else 1
        return (tier_num, -sc, smi)

    scored.sort(key=key)

    ranked = []
    for i, (sc, smi, tier, meta) in enumerate(scored[:k], start=1):
        rec = {
            "rank": i,
            "candidate_smiles": smi,
            "tier": tier,
        }
        if tier == TIER_ENVIPATH:
            rec["score"] = sc
            rec["reaction_class"] = meta
        ranked.append(rec)

    return {
        "case_id": case_id,
        "status": STATUS_RANKED,
        "n_pool": len(pool),
        "n_envipath": len(prov_map),
        "ranked": ranked,
    }


def rank_all(pool: Dict[str, List[str]], prov: Dict[str, Dict[str, List[str]]],
             rule_data: Dict[str, dict], verdicts: Dict[str, str],
             bbd: Dict[str, dict], k: int = TOP_K) -> list:
    out = []
    for cid in sorted(pool):
        out.append(rank_case(cid, pool[cid], prov, rule_data, verdicts, bbd, k=k))
    return out


def coverage(case_results: list, k: int = TOP_K) -> dict:
    """Same shape as rank_relevance.coverage but with the MG ranking key."""
    cov = rr.coverage(case_results, k=k)
    cov["ranking_key"] = RANKING_KEY
    return cov