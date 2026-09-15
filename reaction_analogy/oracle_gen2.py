#!/usr/bin/env python3
"""DIAGNOSTIC TOOL — reads answer key; output NEVER enters prediction pipeline or submission.

BBD P4.1 Oracle Gen-2 ceiling diagnostic.

Expands the **answer key's true gen-1 products** (accepted_products) through
the same three-engine + v3.2 scoring pipeline (with `*`/ion fix) to depth 2,
then measures how well the gen-2 ranking finds the true gen-2 products
(reconstructed from donor_product.jsonl, same BFS as score_bbd_multistep.py).

This answers: "If gen-1 were perfect, what Hit@K does the gen-2 ranking achieve?"
The gap between this oracle ceiling and the actual gen-2 (from predicted gen-1)
tells whether the gen-2 collapse is driven by gen-1 error propagation or by
gen-2 ranking itself being weak.

Answer-key isolation: this script IS a legitimate reader of the answer key
(diagnostic only).  Its output (bbd_oracle_gen2_eval.json) is NEVER imported or
referenced by the prediction pipeline or the submission package.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import Counter, defaultdict

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(_HERE, "src"))

from rdkit import Chem, RDLogger
RDLogger.DisableLog("rdApp.*")

import expand_bbd_routes as E  # reuse _generate_candidates, _score_and_sort, globals
from ra import corpus, retrieval

ROOT = "/Volumes/CC/Enzyme_Agent/depending"
ANSWER_KEY = os.path.join(
    ROOT,
    "bbd83_answer_key_scoring_handoff_20260816/restricted"
    "/KNOWN_PATHWAY_POLLUTANT_RESTRICTED_ANSWER_KEY_V0_2.jsonl")
DONOR_PRODUCT = os.path.join(_HERE, "data/bbd_expand/donor_product.jsonl")
MODEL_DIR = os.path.join(ROOT, "data/bbd_v31")

KS = (1, 3, 5, 10, 20)


def _canon(smi: str) -> str | None:
    m = Chem.MolFromSmiles(smi)
    return Chem.MolToSmiles(m, isomericSmiles=False) if m is not None else None


def load_answer_key(path):
    """parent canonical → set of gen-1 true product canonicals (stereo-blind)."""
    out = {}
    with open(path) as f:
        for line in f:
            r = json.loads(line)
            pc = _canon(r.get("parent_smiles", ""))
            if not pc:
                continue
            prods = set()
            for ap in r.get("accepted_products", []):
                c = _canon(ap.get("product_smiles", ""))
                if c:
                    prods.add(c)
            out[pc] = out.get(pc, set()) | prods
    return out


def load_donor_graph(path):
    graph = defaultdict(set)
    with open(path) as f:
        for line in f:
            r = json.loads(line)
            d = _canon(r.get("donor_smiles", ""))
            p = _canon(r.get("product_smiles", ""))
            if d and p and d != p:
                graph[d].add(p)
    return graph


def build_gen2_truth(answer, donor_graph):
    """parent → set of gen-2 true product canonicals (same BFS as multistep scorer)."""
    out = {}
    for parent, gen1 in answer.items():
        gen2 = set()
        for p in gen1:
            gen2 |= donor_graph.get(p, set())
        gen2 -= gen1          # exclude gen-1 (trivial)
        gen2.discard(parent)  # exclude parent
        out[parent] = gen2
    return out


def init_expander_globals(args):
    """Populate expand_bbd_routes module globals (templates, rules, corpus, rankers)."""
    print("parsing USPTO templates...", flush=True)
    data = json.load(open(args.templates))
    parsed = []
    for tpl_str, freq in data["templates"].items():
        rf, pf = E.A.parse_template(tpl_str)
        if rf is None or pf is None:
            continue
        csm = Counter(E._sig(a) for a in rf.GetAtoms() if a.GetAtomMapNum() > 0)
        parsed.append((rf, pf, freq, csm, E.A.template_type(rf), rf.GetNumAtoms()))
    E._G_TPL_A = parsed
    print(f"  {len(parsed)} templates", flush=True)

    print("loading enviPath rules...", flush=True)
    E._G_RULES_B, _ = E.P2._load_envipath_rules(args.envipath_rules, args.envipath_tsv)
    print(f"  {len(E._G_RULES_B)} rules", flush=True)

    print("loading corpus...", flush=True)
    E._G_RECORDS = {r["record_id"]: r
                    for r in corpus.read_records(
                        os.path.join(args.corpus_dir, "corpus_v1.jsonl"))}
    donor_entries = corpus.load_donor_index(
        os.path.join(args.corpus_dir, "donor_index.jsonl"))
    donor_to_records = defaultdict(list)
    for e in donor_entries:
        donor_to_records[e["donor_smiles"]].append(e["donor_record_id"])
    for k in donor_to_records:
        donor_to_records[k] = sorted(set(donor_to_records[k]))
    E._G_DONOR_TO_RECORDS = donor_to_records
    donors = sorted(donor_to_records.keys())
    print(f"  {len(E._G_RECORDS)} records, {len(donors)} donors", flush=True)

    E._init_worker(args.model_dir)
    print(f"  rankers: {sorted(E._G_RANKERS.keys())}", flush=True)
    return donors


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--answer", default=ANSWER_KEY)
    ap.add_argument("--donor-product", default=DONOR_PRODUCT)
    ap.add_argument("--templates", default=E.TEMPLATES)
    ap.add_argument("--envipath-rules", default=E.ENVIPATH_RULES)
    ap.add_argument("--envipath-tsv", default=E.ENVIPATH_TSV)
    ap.add_argument("--corpus-dir", default=E.CORPUS_DIR)
    ap.add_argument("--model-dir", default=MODEL_DIR)
    ap.add_argument("--out", default=os.path.join(
        ROOT, "bbd_predictions/bbd_oracle_gen2_eval.json"))
    ap.add_argument("--debug", type=int, default=0,
                    help="limit to N parents for debugging")
    args = ap.parse_args()

    t0 = time.time()
    print("Loading answer key...", flush=True)
    answer = load_answer_key(args.answer)
    print(f"  {len(answer)} parents with gen-1 products", flush=True)

    print("Loading donor-product graph...", flush=True)
    donor_graph = load_donor_graph(args.donor_product)
    print(f"  {len(donor_graph)} donors", flush=True)

    gen2_truth = build_gen2_truth(answer, donor_graph)
    n_with_gen2 = sum(1 for v in gen2_truth.values() if v)
    n_gen2_products = sum(len(v) for v in gen2_truth.values())
    print(f"  {n_with_gen2} parents with gen-2 truth, {n_gen2_products} gen-2 products",
          flush=True)

    # Collect all unique gen-1 true product canonicals (oracle frontier)
    oracle_frontier = set()
    for prods in answer.values():
        oracle_frontier |= prods
    print(f"  oracle frontier: {len(oracle_frontier)} unique true products", flush=True)

    # Initialize expander globals
    donors = init_expander_globals(args)

    if args.debug > 0:
        parents = list(answer.keys())[:args.debug]
    else:
        parents = list(answer.keys())

    # Batch retrieval for all oracle frontier canonicals
    q_map = {c: c for c in oracle_frontier}
    print(f"Batch retrieval for {len(q_map)} oracle substrates...", flush=True)
    ranked = retrieval.rank_queries(q_map, donors, k=20)
    retrieval_map = {}
    for qs, topk in ranked.items():
        ev = []
        for hit in topk.get("topK", []):
            rec_ids = E._G_DONOR_TO_RECORDS.get(hit["donor_smiles"], [])
            ev.append({
                "donor_smiles": hit["donor_smiles"],
                "tanimoto": hit["tanimoto"],
                "donor_records": rec_ids,
            })
        retrieval_map[qs] = ev
    print(f"  retrieval done for {len(retrieval_map)} substrates", flush=True)

    # For each parent: generate depth-2 candidates from each true gen-1 product,
    # pool, sort (scorer口径: ion, -score, smiles), score Hit@K against gen-2 truth.
    hits = {k: 0 for k in KS}
    found = {k: 0 for k in KS}
    mrr = 0.0
    n_cases = 0
    n_true_total = 0
    n_parse_fail = 0
    per_case = []
    oracle_frontier_used = 0

    for parent in parents:
        gen1 = answer[parent]
        gen2_true = gen2_truth.get(parent, set())
        if not gen2_true:
            continue  # no gen-2 truth → not scored
        n_cases += 1
        n_true_total += len(gen2_true)

        all_cands = []
        for p in gen1:
            p_sb = E._stereo_blind(p)
            if p_sb is None:
                n_parse_fail += 1
                continue
            retr = retrieval_map.get(p, [])
            cands, _ = E._generate_candidates(p, p_sb, retr)
            if cands:
                E._score_and_sort(cands, p)
            all_cands.extend(cands)
            oracle_frontier_used += 1

        # Deduplicate by product canonical (keep best score)
        best_by_canon = {}
        for c in all_cands:
            pc = E._stereo_blind(c["product_smiles"])
            if pc is None:
                continue
            if pc not in best_by_canon or c["ns_score"] > best_by_canon[pc]["ns_score"]:
                best_by_canon[pc] = c
        pooled = list(best_by_canon.values())

        # Scorer口径 sort: (ion_filtered, -ns_score, product_smiles) — same as
        # score_bbd_multistep.py for direct comparability with actual gen-2.
        pooled.sort(key=lambda c: (c["ion_filtered"], -c["ns_score"],
                                   c["product_smiles"]))
        ranked_prods = [E._stereo_blind(c["product_smiles"]) for c in pooled]

        case_hit = {k: False for k in KS}
        case_found = {k: 0 for k in KS}
        for k in KS:
            topk_set = set(ranked_prods[:k])
            inter = gen2_true & topk_set
            if inter:
                hits[k] += 1
                case_hit[k] = True
            found[k] += len(inter)
            case_found[k] = len(inter)
        for i, p in enumerate(ranked_prods[:10]):
            if p in gen2_true:
                mrr += 1.0 / (i + 1)
                break

        per_case.append({
            "parent_canonical": parent,
            "n_gen1_products": len(gen1),
            "n_gen2_true": len(gen2_true),
            "n_candidates": len(pooled),
            "hit": case_hit,
            "found": case_found,
            "top10": ranked_prods[:10],
            "gen2_true": sorted(gen2_true),
        })

    nn = max(n_cases, 1)
    result = {
        "tool": "oracle_gen2 (DIAGNOSTIC — answer-key reader, output not for pipeline)",
        "method": "expand answer-key gen-1 products → depth-2 candidates; "
                  "Hit@K vs gen-2 truth (donor_product.jsonl BFS, same as multistep scorer)",
        "sort": "(ion_filtered, -ns_score, product_smiles) — matches score_bbd_multistep.py",
        "n_answer_key_parents": len(answer),
        "n_scored_cases": n_cases,
        "n_gen2_true_products": n_true_total,
        "oracle_frontier_size": len(oracle_frontier),
        "oracle_frontier_used": oracle_frontier_used,
        "oracle_parse_fail": n_parse_fail,
        "mrr_at_10": round(mrr / nn, 4),
    }
    for k in KS:
        result[f"hit@{k}"] = f"{hits[k]}/{n_cases} = {hits[k]/nn:.1%}"
        result[f"recall@{k}"] = f"{found[k]}/{n_true_total} = {found[k]/max(n_true_total,1):.1%}"

    # Decision matrix (task §3.2)
    hit10_pct = hits[10] / nn if nn else 0.0
    if hit10_pct >= 0.50:
        verdict = ("gen-2 ranking itself is adequate; the collapse is mostly "
                   "gen-1 error propagation → invest in gen-1 (P5 rules + ranking)")
    elif hit10_pct >= 0.25:
        verdict = ("mixed: both ranking and propagation contribute → dual-track, "
                   "but frontier tightening / K2 tuning first")
    else:
        verdict = ("gen-2 ranking itself is weak (distribution mismatch: ranker "
                   "trained on RHEA primary metabolites, depth-2 intermediates are "
                   "a different distribution) → need depth-specific ranker or P5 "
                   "rules; do NOT just tune K")
    result["oracle_gen2_hit_at_10_pct"] = round(hit10_pct, 4)
    result["verdict"] = verdict

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 70)
    print("ORACLE GEN-2 CEILING RESULTS")
    print("=" * 70)
    print(f"Scored cases (parents with gen-2 truth): {n_cases}")
    print(f"Gen-2 true products: {n_true_total}")
    print(f"Oracle frontier (unique gen-1 products): {len(oracle_frontier)}")
    for k in KS:
        print(f"  Hit@{k:<2}: {result[f'hit@{k}']}")
    print(f"  MRR@10: {result['mrr_at_10']}")
    print(f"\nVerdict (oracle Hit@10={hit10_pct:.1%}): {verdict}")
    print(f"\nSaved: {args.out}")
    print(f"Time: {time.time()-t0:.1f}s")

    # Debug: DCE detail
    for pc in per_case:
        if pc["parent_canonical"] == "ClCCCl":
            print("\n--- DCE (ClCCCl) oracle detail ---")
            print(f"  gen-1 products: {pc['n_gen1_products']}, gen-2 true: {pc['n_gen2_true']}")
            print(f"  gen-2 true set: {pc['gen2_true']}")
            print(f"  top-10 candidates:")
            for i, p in enumerate(pc["top10"]):
                mark = " ← TRUE" if p in set(pc["gen2_true"]) else ""
                print(f"    {i+1:2d}. {p}{mark}")
            break


if __name__ == "__main__":
    main()
