"""RA-M4 deterministic ranker — pre-registered ranking key v1.

Reference: `reports/RA_M4_RANKING_KEY.md` (committed before any scoring).
The RED test suite `tests/test_ranking.py` is the truth-holding contract.

Ranking key (total order per case):
  tier(x)    = "envipath" iff source_track(x) in {"envipath","rhea+envipath"}
               else "rhea"
  donor_t(x) = max tanimoto over the candidate's RHEA donor evidence (from
               data/retrieval_v1/candidates.jsonl); 0.0 if none
  score(x)   = donor_t(x)
  order      = (tier desc) -> (score desc) -> (candidate_smiles asc)

Strict top-K (K=10): exactly min(K, |pool|) candidates; abstained cases emit
an empty ranked list (fail-closed; no fabrication).

Answer isolation: this module never references the restricted answer key and
never reads it. It consumes only the frozen pool/evidence artifacts.
"""
from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# pre-registered constants
# ---------------------------------------------------------------------------

RANKING_KEY_V1 = (
    "RANKING_KEY_V1: order = (tier desc) -> (score desc) -> (candidate_smiles asc); "
    "tier = 'envipath' iff source_track in {'envipath','rhea+envipath'} else 'rhea'; "
    "score = max donor tanimoto over RHEA donor evidence (0.0 if none); "
    "TOP_K = 10 strict; abstain no_candidate (empty pool) / low_evidence "
    "(best is rhea-tier and score < 0.20). See reports/RA_M4_RANKING_KEY.md."
)

TOP_K = 10
TANIMOTO_ABSTAIN_THRESHOLD = 0.20

TIER_ENVIPATH = "envipath"
TIER_RHEA = "rhea"
ENV_TRACKS = frozenset({"envipath", "rhea+envipath"})

STATUS_RANKED = "ranked"
ABSTAIN_NO_CANDIDATE = "no_candidate"
ABSTAIN_LOW_EVIDENCE = "low_evidence"

EVIDENCE_REF = "data/retrieval_v1/candidates.jsonl"   # RHEA donor evidence
TRANSFER_REF = "data/retrieval_v2/transfer_to_x.jsonl"  # enviPath rule lineage

# ---------------------------------------------------------------------------
# evidence lookups
# ---------------------------------------------------------------------------


def donor_max_tanimoto(case_id: str, candidate_smiles: str, evidence_index: dict) -> float:
    """Max donor Tanimoto over RHEA donor evidence; 0.0 when none."""
    ev = evidence_index.get((case_id, candidate_smiles), [])
    return round(max((e["tanimoto"] for e in ev), default=0.0), 6)


def _tier(source_track: str) -> str:
    return TIER_ENVIPATH if source_track in ENV_TRACKS else TIER_RHEA


# ---------------------------------------------------------------------------
# lineage (compact refs, no duplicated molecule strings)
# ---------------------------------------------------------------------------


def _rhea_lineage(case_id: str, candidate_smiles: str, evidence_index: dict) -> dict:
    ev = evidence_index.get((case_id, candidate_smiles), [])
    if not ev:
        return {"kind": "rhea-donor-similarity", "ref": EVIDENCE_REF,
                "max_tanimoto": 0.0, "top_donor_smiles": [], "n_donor_evidence": 0}
    t = round(max(e["tanimoto"] for e in ev), 6)
    top = sorted({e.get("donor_smiles") for e in ev if e["tanimoto"] == t and e.get("donor_smiles")})
    return {
        "kind": "rhea-donor-similarity",
        "ref": EVIDENCE_REF,
        "max_tanimoto": t,
        "top_donor_smiles": top,
        "n_donor_evidence": len(ev),
    }


def _envipath_lineage(case_id: str, candidate_smiles: str, transfer_index: dict) -> Optional[dict]:
    rec = transfer_index.get((case_id, candidate_smiles))
    if rec is None:
        return None
    return {
        "kind": "envipath-rule-transfer",
        "ref": TRANSFER_REF,
        "source_id": rec.get("source_id"),
        "mapping_status": rec.get("mapping_status"),
        "provenance_sha256": rec.get("provenance_sha256"),
        "lineage": rec.get("lineage"),
    }


# ---------------------------------------------------------------------------
# ranking
# ---------------------------------------------------------------------------


def _order_value(row: dict, donor_t: float):
    """Total-order sort key (ascending): (rhea-first flag, -score, smiles)."""
    is_rhea = 1 if _tier(row["source_track"]) == TIER_RHEA else 0
    return (is_rhea, -donor_t, row["candidate_smiles"])


def rank_case(
    case_id: str,
    pool_rows: List[dict],
    evidence_index: dict,
    transfer_index: dict,
    k: int = TOP_K,
    threshold: float = TANIMOTO_ABSTAIN_THRESHOLD,
) -> dict:
    """Rank one case's pool -> {'case_id', 'status', 'ranked', ...}.

    pool_rows: list of {'case_id', 'candidate_smiles', 'source_track'}.
    Returns ranked top-K or a typed abstention (empty ranked list).
    """
    pool = list(pool_rows)
    if not pool:
        return {
            "case_id": case_id,
            "status": ABSTAIN_NO_CANDIDATE,
            "n_pool": 0,
            "ranked": [],
            "abstention": {"type": ABSTAIN_NO_CANDIDATE,
                           "reason": "empty candidate pool"},
        }

    scored = []
    for row in pool:
        donor_t = donor_max_tanimoto(case_id, row["candidate_smiles"], evidence_index)
        scored.append((row, _tier(row["source_track"]), donor_t))
    scored.sort(key=lambda t: _order_value(t[0], t[2]))

    best_row, best_tier, best_donor_t = scored[0]

    # typed abstention: best candidate is rhea-tier and below the min-tanimoto
    # floor (no stronger evidence class exists for the case)
    if best_tier == TIER_RHEA and best_donor_t < threshold:
        return {
            "case_id": case_id,
            "status": ABSTAIN_LOW_EVIDENCE,
            "n_pool": len(pool),
            "ranked": [],
            "abstention": {
                "type": ABSTAIN_LOW_EVIDENCE,
                "reason": "best evidence below declared min-tanimoto threshold",
                "best_tier": best_tier,
                "best_score": best_donor_t,
                "threshold": threshold,
                "ranking_key": "v1",
            },
        }

    ranked = []
    for i, (row, tier, donor_t) in enumerate(scored[:k], start=1):
        lineage = {}
        if tier == TIER_ENVIPATH:
            env = _envipath_lineage(case_id, row["candidate_smiles"], transfer_index)
            if env is not None:
                lineage["envipath"] = env
            # dual candidates keep their RHEA donor evidence too
            rhea = _rhea_lineage(case_id, row["candidate_smiles"], evidence_index)
            if rhea["n_donor_evidence"]:
                lineage["rhea"] = rhea
        else:
            lineage["rhea"] = _rhea_lineage(case_id, row["candidate_smiles"], evidence_index)
        ranked.append(
            {
                "rank": i,
                "candidate_smiles": row["candidate_smiles"],
                "source_track": row["source_track"],
                "tier": tier,
                "donor_tanimoto": donor_t if donor_t > 0.0 else None,
                "score": donor_t,
                "lineage": lineage,
            }
        )

    return {
        "case_id": case_id,
        "status": STATUS_RANKED,
        "n_pool": len(pool),
        "best_tier": best_tier,
        "best_score": best_donor_t,
        "ranked": ranked,
    }


def coverage(case_results: List[dict], k: int = TOP_K) -> dict:
    """Aggregate coverage: non-abstained cases + abstention counts per type."""
    total = len(case_results)
    ranked = [r for r in case_results if r["status"] == STATUS_RANKED]
    abstained = [r for r in case_results if r["status"] != STATUS_RANKED]
    counts: Dict[str, int] = {}
    for r in abstained:
        counts[r["abstention"]["type"]] = counts.get(r["abstention"]["type"], 0) + 1
    return {
        "top_k": k,
        "cases_total": total,
        "cases_ranked": len(ranked),
        "cases_abstained": len(abstained),
        "abstention_by_type": counts,
        "non_abstained_coverage": round(len(ranked) / total, 6) if total else 0.0,
        "total_ranked_candidates": sum(len(r["ranked"]) for r in ranked),
        "ranking_key": RANKING_KEY_V1,
    }