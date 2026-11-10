"""RA-M2 candidate generation: donor->product triples + transfer-to-X + UNION pool.

- Track (a) donor->product triples: rule applied to its own donor educts.
  Evidence layer: donor_A -> rule -> product_B, stored as compact triple records.
- Track (b) transfer-to-X: the same 286 atom-mapped rules applied DIRECTLY to a
  blind parent X. X substructure-matching a rule's reactant pattern == X carries
  that reaction centre ("compatible site") — the rule-based realisation of
  "transfer the change to X". Lineage here is direct: rule -> X -> Y.
- UNION pool = TRACK(a/b enviPath candidates) ∪ RA-M1 RHEA similar-donor products.
  All records are deterministic; lineage uses record-id refs, not duplicated
  molecule strings.
"""
import hashlib

from ra import envipath_rules as er
from ra.chem import canonical_smiles  # noqa: F401  (re-export for tests)
from ra.io import stable_json_text

_EMPTY_COUNTER = {"pairs": 0, "applied": 0, "clean": 0, "raised": 0, "sanitize_failed": 0, "nomatch": 0}


def _counter():
    return dict(_EMPTY_COUNTER)


def _digest(body: dict) -> str:
    return hashlib.sha256(stable_json_text(body).encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------
# track (a): donor -> product triples
# --------------------------------------------------------------------------

def build_triples(templates, substrates) -> tuple:
    """(triples, stats). One triple per (rule, donor, clean product)."""
    counter = _counter()
    triples = []
    for rule in templates:
        if rule.get("parse_error") is not None:
            continue
        for donor in substrates.get(rule["template_id"], []):
            for product in er.apply_rule(rule, donor, counter):
                body = {
                    "triple_id": None,  # assigned below from content
                    "template_id": rule["template_id"],
                    "rule_smarts": rule["smarts"],
                    "donor_smiles": donor,
                    "product_smiles": product,
                    "mapping_status": "in-smarts",
                    "provenance_sha256": None,
                    "lineage": None,  # filled below
                }
                triple_id = "triple:%s_%s_%s" % (
                    rule["template_id"].replace("envipath:", "ev"),
                    hashlib.sha256(donor.encode()).hexdigest()[:8],
                    hashlib.sha256(product.encode()).hexdigest()[:8],
                )
                body["triple_id"] = triple_id
                body["lineage"] = {
                    "donor_ref": donor,
                    "rule_ref": rule["template_id"],
                    "product_B_ref": product,
                }
                body["provenance_sha256"] = _digest(
                    {k: v for k, v in body.items() if k != "provenance_sha256"}
                )
                triples.append(body)
    triples.sort(key=lambda t: t["triple_id"])
    return triples, {k: counter[k] for k in _EMPTY_COUNTER}


# --------------------------------------------------------------------------
# track (b): transfer-to-X
# --------------------------------------------------------------------------

def _triple_index(triples) -> dict:
    """template_id -> {product_smiles: triple_id} for linking transfer lineage."""
    index = {}
    for t in triples:
        index.setdefault(t["template_id"], {})[t["product_smiles"]] = t["triple_id"]
    return index


def build_transfer(templates, queries: dict, triple_index: dict | None = None) -> list:
    """Apply rules directly to each X; sorted candidate records.

    queries: {case_id: canonical X smiles}. triple_index links products back
    to donor-triple lineage when the same product is derivable from a donor
    (compact refs).
    """
    triple_index = triple_index or {}
    counter = _counter()
    records = []
    for case_id in sorted(queries):
        x_smiles = queries[case_id]
        for rule in templates:
            if rule.get("parse_error") is not None:
                continue
            for candidate in er.apply_rule(rule, x_smiles, counter):
                link = triple_index.get(rule["template_id"], {}).get(candidate)
                body = {
                    "case_id": case_id,
                    "x_smiles": x_smiles,
                    "candidate_smiles": candidate,
                    "source_id": rule["template_id"],
                    "rule_smarts": rule["smarts"],
                    "donor_smiles": None,  # direct rule application on X: no donor
                    "mapping_status": "in-smarts",
                    "provenance_sha256": None,
                    "lineage": {
                        "donor_ref": link,         # triple_id ref when derivable
                        "rule_ref": rule["template_id"],
                        "product_B_ref": link,
                        "x_ref": case_id,
                    },
                }
                body["provenance_sha256"] = _digest(
                    {k: v for k, v in body.items() if k != "provenance_sha256"}
                )
                records.append(body)
    records.sort(
        key=lambda r: (r["case_id"], r["source_id"], r["candidate_smiles"])
    )
    return records


# --------------------------------------------------------------------------
# UNION pool
# --------------------------------------------------------------------------

def build_union_pool(rhea_cands: dict, envipath_cands: dict) -> tuple:
    """(rows, coverage). rhea_cands: {case_id: [canonical smiles]};
    envipath_cands: {case_id: [transfer record dicts]}."""
    rows = []
    all_cases = sorted(set(rhea_cands) | set(envipath_cands))
    stats_cases = []
    for case_id in all_cases:
        rhea = set(rhea_cands.get(case_id, []))
        env = {r["candidate_smiles"] for r in envipath_cands.get(case_id, [])}
        seen = set()
        case_rows = []
        for cand in sorted(rhea | env):
            if cand in seen:
                continue
            seen.add(cand)
            in_rhea = cand in rhea
            in_env = cand in env
            track = "rhea" if (in_rhea and not in_env) else "envipath" if (in_env and not in_rhea) else "rhea+envipath"
            case_rows.append({"case_id": case_id, "candidate_smiles": cand, "source_track": track})
        rows.extend(case_rows)
        stats_cases.append({"case_id": case_id, "candidates": [r["candidate_smiles"] for r in case_rows]})
    rows.sort(key=lambda r: (r["case_id"], r["candidate_smiles"]))
    from ra.retrieval import coverage_stats

    return rows, coverage_stats(stats_cases)