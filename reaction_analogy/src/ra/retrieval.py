"""RA-1 similarity-retrieval pilot — Morgan/Tanimoto top-K donor ranking.

NOTE (RA-M1 CORRECTION): source data carry no atom-atom mapping, so no mapped
transform is applied in this milestone. "Candidates" are the product components
of the full donor reactions whose donor molecules ranked in the top-K — raw
evidence for the auditor's donor-recall measurement. Mapped transfer (with
atom_mapping) is deferred to RA-2/RA-3.
"""
import logging

from rdkit import DataStructs

from ra.chem import ChemParseError, canonical_smiles, morgan_fp, tanimoto

logger = logging.getLogger(__name__)


def _fingerprints(smiles_list):
    fpus = []
    skipped = []
    for s in sorted(set(smiles_list)):
        try:
            fpus.append((s, morgan_fp(s)))
        except ChemParseError as exc:
            skipped.append({"smiles": s, "error": str(exc)})
    return fpus, skipped


def rank_queries(queries: dict, donor_smiles: list, k: int = 20) -> dict:
    """Top-K donors per query by Morgan/Tanimoto, deterministic ordering.

    queries: {query_id: canonical smiles}. Returns
      {query_id: {"topK": [{rank, donor_smiles, tanimoto}], "n_donors": N}}.
    Ties are broken lexicographically by donor smiles; only sim > 0 kept.
    """
    donor_fps, skipped = _fingerprints(donor_smiles)
    if len(donor_fps) == 0:
        raise ChemParseError("retrieval corpus has no parseable donors (fail-closed)")
    by_smiles = [s for s, _ in donor_fps]
    fps = [fp for _, fp in donor_fps]

    out = {}
    for qid in sorted(queries):
        try:
            q_fp = morgan_fp(queries[qid])
        except ChemParseError as exc:
            out[qid] = {"topK": [], "n_donors": len(donor_fps), "query_error": str(exc)}
            continue
        scores = list(DataStructs.BulkTanimotoSimilarity(q_fp, fps))
        ranked = sorted(zip(by_smiles, scores), key=lambda t: (-t[1], t[0]))
        top = []
        for i, (smi, sim) in enumerate(ranked[:k]):
            if sim <= 0.0:
                continue
            top.append({"rank": i + 1, "donor_smiles": smi, "tanimoto": round(sim, 6)})
        out[qid] = {"topK": top, "n_donors": len(donor_fps)}
    return out


def candidates_from_products(product_list) -> list:
    """Canonicalise, de-duplicate, and sort candidate product SMILES."""
    seen = set()
    for p in product_list:
        if not p:
            continue
        try:
            smi = canonical_smiles(p)
        except ChemParseError as exc:
            logger.warning("skip unparseable candidate %r: %s", p, exc)
            continue
        if smi not in seen:
            seen.add(smi)
    return sorted(seen)


def coverage_stats(cases: list) -> dict:
    """cases: list of {"candidates": [...]}. Returns coverage summary."""
    total = len(cases)
    with_cand = sum(1 for c in cases if c.get("candidates"))
    return {
        "cases_total": total,
        "cases_with_candidate": with_cand,
        "coverage": round(with_cand / total, 6) if total else 0.0,
    }