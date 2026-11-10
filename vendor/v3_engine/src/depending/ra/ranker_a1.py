"""RA-A1 learned ranker — pre-registered spec v1 (deterministic, dev-44 only).

Spec: reports/RA_A1_MODEL_SPEC.md; RED contract: tests/test_ranker_a1.py.

Linear pairwise logistic ranker over a small explicit feature set. The model
is a SINGLE frozen logistic coefficient vector learned on dev-44 pair labels;
ranking is a deterministic linear scoring per candidate + tiebreak by
candidate_smiles asc. No GBM / deep model / model shopping.

Answer isolation: this module never opens, imports, or references the
restricted accepted-products file. dev labels are consumed only by fit_a1()
to build pair labels; the returned object is the coefficient vector (and
metadata), not the label file.
"""
import json
import math
import os

from ra import chem  # noqa: F401  (shared deterministic helpers)

# ---------------------------------------------------------------------------
# pre-registered constants
# ---------------------------------------------------------------------------

RANKER_A1_SPEC_V1 = (
    "RANKER_A1_SPEC_V1: pairwise L2 logistic (fit_intercept=False, C=1.0, "
    "liblinear, random_state=0) over 6 explicit features [tier, "
    "donor_tanimoto, donor_n, reactions_count(clamped log10(1+n)), "
    "ec_present, envipath_mapped]; score = linear combination + tiebreak "
    "candidate_smiles asc; TOP_K=10 strict; abstain no_candidate "
    "(empty pool) / low_evidence (best rhea-tier and score<0.20); "
    "dev-44 labels only, test-39 never read. See "
    "reports/RA_A1_MODEL_SPEC.md."
)

TOP_K = 10
A1_ABSTAIN_THRESHOLD = 0.20
FEATURE_KEYS = (
    "tier",
    "donor_tanimoto",
    "donor_n",
    "reactions_count",
    "ec_present",
    "envipath_mapped",
)

STATUS_RANKED = "ranked"
ABSTAIN_NO_CANDIDATE = "no_candidate"
ABSTAIN_LOW_EVIDENCE = "low_evidence"

EVIDENCE_REF = "data/retrieval_v1/candidates.jsonl"      # RHEA donor evidence
TRANSFER_REF = "data/retrieval_v2/transfer_to_x.jsonl"   # enviPath rule lineage

LOG_CLAMP = 4.0
ENV_TRACKS = frozenset({"envipath", "rhea+envipath"})


# ---------------------------------------------------------------------------
# corpus-derived features (deterministic, frozen artifacts only)
# ---------------------------------------------------------------------------

def build_corpus_features(donor_index_path: str, corpus_path: str):
    """Return (donor_counts, ec_records).

    donor_counts: {donor_smiles: number of corpus records containing it}
      (the frozen RA-M1 donor index — deterministic input; this is the
      'reactions_count' literature-support proxy).
    ec_records: set of corpus record_ids with a non-null `ec` field.
    """
    donor_counts: dict = {}
    with open(donor_index_path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            donor_counts[r["donor_smiles"]] = donor_counts.get(r["donor_smiles"], 0) + 1

    ec_records = set()
    with open(corpus_path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            if r.get("ec"):
                ec_records.add(r["record_id"])
    return donor_counts, ec_records


def _nearest_donor(evidence: list):
    """Max-tanimoto evidence entry; ties -> smallest donor_smiles. None if none."""
    if not evidence:
        return None
    best = None
    for e in evidence:
        key = (e.get("tanimoto", 0.0), e.get("donor_smiles", ""))
        if best is None or key > (best[0], best[1]):
            best = (e.get("tanimoto", 0.0), e.get("donor_smiles", ""), e.get("donor_record_id"))
    return best


def candidate_features(row: dict, evidence_index: dict, transfer_index: dict,
                       donor_counts: dict, ec_records: set) -> dict:
    """Deterministic 6-feature vector (floats) for one pool candidate."""
    case_id = row["case_id"]
    smi = row["candidate_smiles"]
    ev = evidence_index.get((case_id, smi), [])
    donor_t = max((e["tanimoto"] for e in ev), default=0.0)
    donor_n = float(len(ev))
    nearest = _nearest_donor(ev)
    if nearest is not None:
        _t, donor_smi, donor_record_id = nearest
        reactions_count = min(math.log10(1.0 + donor_counts.get(donor_smi, 0)), LOG_CLAMP)
        ec_present = 1.0 if donor_record_id in ec_records else 0.0
    else:
        reactions_count = 0.0
        ec_present = 0.0
    return {
        "tier": 1.0 if row["source_track"] in ENV_TRACKS else 0.0,
        "donor_tanimoto": float(donor_t),
        "donor_n": donor_n,
        "reactions_count": float(reactions_count),
        "ec_present": ec_present,
        "envipath_mapped": 1.0 if transfer_index.get((case_id, smi)) else 0.0,
    }


# ---------------------------------------------------------------------------
# scoring + ranking (deterministic)
# ---------------------------------------------------------------------------

def score_candidate(features: dict, coefficients: list) -> float:
    """Linear score b0 + sum(b_i * f_i); floats rounded for stability."""
    return round(
        coefficients[0] + sum(
            b * features[k] for b, k in zip(coefficients[1:], FEATURE_KEYS)
        ),
        8,
    )


def _envipath_lineage(case_id: str, candidate_smiles: str, transfer_rows: dict) -> dict:
    """Compact lineage from transfer_to_x.jsonl (rule/donor refs).

    Accepts either full transfer records (CLI passes `transfer`, the raw
    index) or pre-extracted bools — the enrichment path uses the raw index.
    """
    rec = transfer_rows.get((case_id, candidate_smiles))
    if rec is None:
        return {}
    if isinstance(rec, dict):
        return {
            "kind": "envipath-rule-transfer",
            "ref": TRANSFER_REF,
            "source_id": rec.get("source_id"),
            "lineage": rec.get("lineage"),
        }
    # bool form: mapping_status == "in-smarts" — no extra geometry
    return {
        "kind": "envipath-rule-transfer",
        "ref": TRANSFER_REF,
        "source_id": None,
        "lineage": None,
    }


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


def rank_case(case_id: str, pool_rows: list, evidence_index: dict,
              transfer_index: dict, donor_counts: dict, ec_records: set,
              coefficients: list, k: int = TOP_K,
              threshold: float = A1_ABSTAIN_THRESHOLD) -> dict:
    """Rank one case -> {'case_id', 'status', 'ranked', ...} (deterministic)."""
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
        f = candidate_features(row, evidence_index, transfer_index,
                               donor_counts, ec_records)
        s = score_candidate(f, coefficients)
        scored.append((row, f, s))
    # deterministic total order: score desc -> candidate_smiles asc
    scored.sort(key=lambda t: (-t[2], t[0]["candidate_smiles"]))

    best_row, best_f, best_s = scored[0]

    if best_f["tier"] == 0.0 and best_f["donor_tanimoto"] < threshold:
        return {
            "case_id": case_id,
            "status": ABSTAIN_LOW_EVIDENCE,
            "n_pool": len(pool),
            "ranked": [],
            "abstention": {
                "type": ABSTAIN_LOW_EVIDENCE,
                "reason": "best evidence below declared min-score threshold",
                "best_tier": "rhea",
                "best_score": best_f["donor_tanimoto"],
                "threshold": threshold,
                "ranking_key": "a1-v1",
            },
        }

    ranked = []
    for i, (row, f, s) in enumerate(scored[:k], start=1):
        tier = "envipath" if f["tier"] == 1.0 else "rhea"
        lineage = {}
        if tier == "envipath":
            env = _envipath_lineage(row["case_id"], row["candidate_smiles"], transfer_index)
            if env.get("source_id"):
                lineage["envipath"] = env
        rhea = _rhea_lineage(row["case_id"], row["candidate_smiles"], evidence_index)
        if rhea["n_donor_evidence"]:
            lineage["rhea"] = rhea
        ranked.append({
            "rank": i,
            "candidate_smiles": row["candidate_smiles"],
            "source_track": row["source_track"],
            "tier": tier,
            "donor_tanimoto": f["donor_tanimoto"] if f["donor_tanimoto"] > 0.0 else None,
            "score": s,
            "lineage": lineage,
        })

    return {
        "case_id": case_id,
        "status": STATUS_RANKED,
        "n_pool": len(pool),
        "best_tier": "envipath" if best_f["tier"] == 1.0 else "rhea",
        "best_score": best_s,
        "ranked": ranked,
    }


def rank_all(pool_by_case: dict, evidence_index: dict, transfer_index: dict,
             donor_counts: dict, ec_records: set, coefficients: list,
             k: int = TOP_K) -> list:
    """Rank every case (deterministic: ascending case_id) -> list of case dicts."""
    out = []
    for cid in sorted(pool_by_case):
        out.append(rank_case(cid, pool_by_case[cid], evidence_index,
                             transfer_index, donor_counts, ec_records,
                             coefficients, k=k))
    return out


# ---------------------------------------------------------------------------
# fit (dev-44 labels ONLY; test-39 never opened)
# ---------------------------------------------------------------------------

def _canon_set(smiles_list: list) -> set:
    """Canonical (InChI-key-level) accepted set; unparseable entries dropped."""
    out = set()
    for s in smiles_list:
        try:
            mol = chem.parse_mol(s)
        except chem.ChemParseError:
            continue
        from rdkit.Chem import inchi
        ik = inchi.MolToInchiKey(mol)
        if ik:
            out.add(ik)
    return out


def fit_a1(labels_path: str, pool_by_case: dict, evidence_index: dict,
           transfer_index: dict, donor_counts: dict, ec_records: set) -> tuple:
    """Fit the pre-registered pairwise logistic ranker on dev-44 labels.

    Returns (coefficients: list[float] len 7, meta: dict). Deterministic
    (random_state=0, liblinear). Never touches held-out cases.
    """
    with open(labels_path, "r", encoding="utf-8") as fh:
        labels = json.load(fh)["labels"]

    X, y = [], []
    n_cases = 0
    n_pairs = 0
    n_dropped = 0
    for cid in sorted(pool_by_case):
        if cid not in labels:
            continue
        n_cases += 1
        acc = _canon_set(labels[cid])
        if not acc:
            continue
        rows = pool_by_case[cid]
        # feature vectors once per candidate
        fv = {}
        for row in rows:
            f = candidate_features(row, evidence_index, transfer_index,
                                   donor_counts, ec_records)
            fv[row["candidate_smiles"]] = [f[k] for k in FEATURE_KEYS]
        cands = list(fv)
        for i in range(len(cands)):
            for j in range(i + 1, len(cands)):
                a, b = cands[i], cands[j]
                if a == b:
                    continue
                acc_a = _in_accept(a, acc)
                acc_b = _in_accept(b, acc)
                if acc_a == acc_b:
                    n_dropped += 1
                    continue
                # positive pair: accepted candidate ranks before non-accepted
                d = [x - y for x, y in zip(fv[a], fv[b])]
                X.append(d)
                y.append(1.0 if acc_a and not acc_b else 0.0)
                n_pairs += 1

    from sklearn.linear_model import LogisticRegression

    clf = LogisticRegression(
        C=1.0, fit_intercept=False, solver="liblinear", random_state=0,
        max_iter=1000,
    )
    import numpy as np
    Xa = np.asarray(X, dtype=float)
    ya = np.asarray(y, dtype=float)
    clf.fit(Xa, ya)
    coeffs = [0.0] + [float(v) for v in clf.coef_[0]]  # b0=0 (fit_intercept=False)

    meta = {
        "n_cases": n_cases,
        "n_pairs": n_pairs,
        "n_pairs_dropped": n_dropped,
        "labels_file": os.path.basename(labels_path),
        "feature_keys": list(FEATURE_KEYS),
        "model": "pairwise L2 logistic, fit_intercept=False, C=1.0, liblinear, random_state=0, max_iter=1000",
        "spec_ref": "reports/RA_A1_MODEL_SPEC.md",
        "spec_v1": RANKER_A1_SPEC_V1,
    }
    return coeffs, meta


def _in_accept(smiles: str, acc_iks: set) -> bool:
    try:
        mol = chem.parse_mol(smiles)
    except chem.ChemParseError:
        return False
    from rdkit.Chem import inchi
    ik = inchi.MolToInchiKey(mol)
    return bool(ik and ik in acc_iks)


# ---------------------------------------------------------------------------
# model I/O
# ---------------------------------------------------------------------------

def load_model(out_dir: str) -> dict:
    """Load model_a1.json (coefficients + meta)."""
    with open(os.path.join(out_dir, "model_a1.json"), "r", encoding="utf-8") as fh:
        return json.load(fh)


# ---------------------------------------------------------------------------
# coverage
# ---------------------------------------------------------------------------

def coverage(case_results: list, k: int = TOP_K) -> dict:
    total = len(case_results)
    ranked = [r for r in case_results if r["status"] == STATUS_RANKED]
    abstained = [r for r in case_results if r["status"] != STATUS_RANKED]
    counts: dict = {}
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
        "ranking_key": RANKER_A1_SPEC_V1,
    }