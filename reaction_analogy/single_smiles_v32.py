#!/usr/bin/env python3
"""BBD single-SMILES route prediction entry (v3.2 engines + v3.3 fusion).

Created after the DBP post-freeze diagnostic (2026-09-12) so that model
developers and the test department run the SAME single-compound harness:

    python single_smiles_v32.py --smiles "CCCCOC(=O)c1ccccc1C(=O)OCCCC" \
        --top-k 10 --max-depth 3 --out-prefix /tmp/dbp

What it does
  depth 1     three engines (USPTO templates / enviPath rules / retrieval
              corpus) generate candidates for the input substrate, scored by
              the v3.1 per-source rankers and fused by bbd_v33_fusion
              (charge-normalized identity, source agreement, skeleton
              plausibility).
  depth 2..D  BFS route expansion: top frontier products become new substrates
              (engine invocations counted per depth in depth_engine_invocations).
  routes      all frontier paths assembled; PRIMARY = greedy rank-1 cascade
              (pre-registered downstream rule); TOP3 = best path_score routes
              sent downstream as diagnostics (report recommendation #6).

Outputs (frozen-chain compatible names, prefixed with --out-prefix):
  *_RAW_STDOUT.json        full candidate table + edges + routes + stats
  *_ALL_NORMALIZED_PREDICTIONS.csv  ranked one-row-per-candidate table
  *_RUN_META.json          params, library counts, score semantics
  *_TOP3_DIAGNOSTIC_ROUTES.jsonl    charge-normalized top-3 routes

Answer-key isolation: this file NEVER reads the answer key.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from collections import defaultdict

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(_HERE, "src"))

from rdkit import Chem, RDLogger
RDLogger.DisableLog("rdApp.*")

import expand_bbd_routes as X  # noqa: E402
from ra import corpus, retrieval  # noqa: E402
import lightgbm as lgb  # noqa: E402


def load_engines() -> dict:
    """Load templates, enviPath rules, corpus and rankers (module globals)."""
    t0 = time.time()
    import gnn_phase6_apply as A

    data = json.load(open(X.TEMPLATES))
    parsed = []
    for tpl_str, freq in data["templates"].items():
        rf, pf = A.parse_template(tpl_str)
        if rf is None or pf is None:
            continue
        from collections import Counter
        csm = Counter(X._sig(a) for a in rf.GetAtoms() if a.GetAtomMapNum() > 0)
        rtype = A.template_type(rf)
        parsed.append((rf, pf, freq, csm, rtype, rf.GetNumAtoms()))
    X._G_TPL_A = parsed

    X._G_RULES_B, _ = X.P2._load_envipath_rules(X.ENVIPATH_RULES, X.ENVIPATH_TSV)

    X._G_RECORDS = {r["record_id"]: r for r in corpus.read_records(
        os.path.join(X.CORPUS_DIR, "corpus_v1.jsonl"))}
    donor_entries = corpus.load_donor_index(
        os.path.join(X.CORPUS_DIR, "donor_index.jsonl"))
    donor_to_records: dict[str, list[str]] = defaultdict(list)
    for e in donor_entries:
        donor_to_records[e["donor_smiles"]].append(e["donor_record_id"])
    for k in donor_to_records:
        donor_to_records[k] = sorted(set(donor_to_records[k]))
    X._G_DONOR_TO_RECORDS = donor_to_records

    X._G_RANKERS = {}
    for sk in X.SOURCES:
        p = os.path.join(X.MODEL_DIR, f"{sk}_ranker.txt")
        if os.path.exists(p):
            X._G_RANKERS[sk] = lgb.Booster(model_file=p)

    return {
        "n_templates": len(parsed),
        "n_envipath_rules": len(X._G_RULES_B),
        "n_corpus_records": len(X._G_RECORDS),
        "n_donors": len(donor_to_records),
        "n_rankers": len(X._G_RANKERS),
        "load_time_s": round(time.time() - t0, 1),
    }


def attach_retrieval(frontier: list[dict], k: int = 20) -> None:
    donors = sorted(X._G_DONOR_TO_RECORDS.keys())
    q_map = {n["canonical_smiles"]: n["canonical_smiles"] for n in frontier}
    ranked = retrieval.rank_queries(q_map, donors, k=k)
    for n in frontier:
        ev = []
        for hit in ranked.get(n["canonical_smiles"], {}).get("topK", []):
            ev.append({
                "donor_smiles": hit["donor_smiles"],
                "tanimoto": hit["tanimoto"],
                "donor_records": X._G_DONOR_TO_RECORDS.get(hit["donor_smiles"], []),
            })
        n["_retrieval"] = ev


def expand_node(node: dict) -> dict:
    """Fresh candidate generation + scoring for one frontier node."""
    return X._process_frontier_node(node)


def assemble_routes(depth1_edges: list[dict], children_by_node: dict,
                    root_node_id: str, max_depth: int) -> list[dict]:
    """Enumerate frontier paths (DFS, bounded by K1/K2 pruning) as routes.

    Each route: ordered edges with product identity, ns_score, source;
    path_score = product of edge ns_scores (v3.2/v3.3 convention).
    """
    routes = []

    def walk(edge: dict, path: list[dict], depth: int):
        path = path + [edge]
        target = edge.get("product_node_id")
        kids = children_by_node.get(target, [])
        if depth >= max_depth or not kids:
            routes.append({"edges": path,
                           "path_score": round(_prod_scores(path), 6),
                           "n_edges": len(path)})
            return
        for ke in kids:
            walk(ke, path, depth + 1)

    for e in depth1_edges:
        walk(e, [], 1)
    return routes


def _prod_scores(path: list[dict]) -> float:
    s = 1.0
    for e in path:
        s *= e["edge_score"]
    return s


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--smiles", required=True, help="pollutant substrate SMILES")
    ap.add_argument("--top-k", type=int, default=10)
    ap.add_argument("--max-depth", type=int, default=3)
    ap.add_argument("--k1", type=int, default=X.K1, help="depth-1 frontier size")
    ap.add_argument("--k2", type=int, default=X.K2, help="depth>=2 frontier size")
    ap.add_argument("--scoring", default="v33", choices=["v33", "v32"])
    ap.add_argument("--case-id", default=None)
    ap.add_argument("--out-prefix", default=None,
                    help="output file prefix (default: ./single_<canon8>)")
    args = ap.parse_args()

    smi = args.smiles.strip()
    mol = Chem.MolFromSmiles(smi)
    if mol is None:
        print(f"FATAL: unparseable SMILES: {smi!r}", file=sys.stderr)
        return 2
    X._G_SCORING = args.scoring

    case_id = args.case_id or "SINGLE"
    cid = case_id
    t_start = time.time()
    libs = load_engines()
    print(f"engines loaded: {libs}", flush=True)

    root_identity = X._identity(smi) or smi
    root_node_id = X._node_id(cid, 0, root_identity)
    root_node = {
        "node_id": root_node_id, "case_id": cid, "depth": 0,
        "smiles": smi, "canonical_smiles": root_identity,
        "is_root": True, "ancestor_canons": set(),
        "path_score": 1.0,
    }

    # ---- depth 1: fresh generation (engine invocation #1) ----
    attach_retrieval([root_node])
    engine_invocations = {"1": 1}
    res = expand_node(root_node)
    all_edges: list[dict] = []
    nodes_by_id: dict[str, dict] = {root_node_id: root_node}
    parent_of: dict[str, str] = {}
    edge_of_child: dict[str, dict] = {}
    children_by_node: dict[str, list[dict]] = defaultdict(list)
    frontier: list[dict] = []

    for e in res["edges"]:
        e["depth"] = 1
        e["source_node_id"] = root_node_id
        e["source_smiles"] = smi
        e["parent_case_id"] = cid
        prod_identity = X._identity(e["product_smiles"]) or ""
        e["product_node_id"] = X._node_id(cid, 1, prod_identity)
        e["parent_copy_filtered"] = (prod_identity == root_identity)
        e["cycle"] = e["parent_copy_filtered"]
        # depth-1 frontier uses K1
        e["product_in_frontier"] = (
            not e["ion_filtered"] and not e["wildcard_filtered"]
            and not e["cycle"] and e["rank"] <= args.k1)
        all_edges.append(e)
        if e["product_in_frontier"]:
            child = {
                "node_id": e["product_node_id"], "case_id": cid, "depth": 1,
                "smiles": e["product_smiles"], "canonical_smiles": prod_identity,
                "is_root": False, "ancestor_canons": {root_identity},
                "path_score": e["edge_score"],
            }
            nodes_by_id[child["node_id"]] = child
            parent_of[child["node_id"]] = root_node_id
            edge_of_child[child["node_id"]] = e
            children_by_node[root_node_id].append(e)
            frontier.append(child)
    print(f"depth 1: {len(res['edges'])} edges, {len(frontier)} frontier", flush=True)

    # ---- BFS depth 2..max_depth ----
    for depth in range(2, args.max_depth + 1):
        if not frontier:
            print(f"depth {depth}: frontier empty, stopping", flush=True)
            break
        attach_retrieval(frontier)
        engine_invocations[str(depth)] = len(frontier)
        new_frontier = []
        for node in frontier:
            r = expand_node(node)
            for e in r["edges"]:
                e["depth"] = depth
                e["source_node_id"] = node["node_id"]
                e["source_smiles"] = node["smiles"]
                e["parent_case_id"] = cid
                prod_identity = X._identity(e["product_smiles"]) or ""
                e["product_node_id"] = X._node_id(cid, depth, prod_identity)
                e["parent_copy_filtered"] = (prod_identity == node["canonical_smiles"])
                all_edges.append(e)
                if e["product_in_frontier"]:
                    child = {
                        "node_id": e["product_node_id"], "case_id": cid,
                        "depth": depth,
                        "smiles": e["product_smiles"],
                        "canonical_smiles": prod_identity,
                        "is_root": False,
                        "ancestor_canons": node["ancestor_canons"] | {node["canonical_smiles"]},
                        "path_score": round(node["path_score"] * e["edge_score"], 9),
                    }
                    if child["node_id"] in nodes_by_id:
                        continue  # already reached (same identity, same/better path)
                    nodes_by_id[child["node_id"]] = child
                    parent_of[child["node_id"]] = node["node_id"]
                    edge_of_child[child["node_id"]] = e
                    children_by_node[node["node_id"]].append(e)
                    new_frontier.append(child)
        print(f"depth {depth}: {len(new_frontier)} new frontier", flush=True)
        frontier = new_frontier

    # ---- routes ----
    depth1_ranked = [e for e in all_edges if e["depth"] == 1]
    routes = assemble_routes(depth1_ranked, children_by_node,
                             root_node_id, args.max_depth)
    # diagnostics show the most COMPLETE routes first (degradation routes
    # should reach depth), tie-broken by path_score
    routes.sort(key=lambda r: (-r["n_edges"], -r["path_score"],
                               r["edges"][0]["product_smiles"]))
    # PRIMARY: pre-registered greedy rank-1 cascade (native rank=1 rule)
    primary = []
    node = root_node
    for d in range(1, args.max_depth + 1):
        kids = children_by_node.get(node["node_id"], [])
        if not kids:
            break
        best = min(kids, key=lambda e: e["rank"])
        primary.append(best)
        node = nodes_by_id.get(best["product_node_id"])
        if node is None:
            break

    # ---- outputs ----
    import hashlib
    prefix = args.out_prefix or f"single_{hashlib.sha1(smi.encode()).hexdigest()[:8]}"
    os.makedirs(os.path.dirname(os.path.abspath(prefix)), exist_ok=True)
    sem = ("ns33_max_source_x_agreement_x_skeleton_over_3" if args.scoring == "v33"
           else "ns_score_max_per_source_probability_over_3")

    top_rows = []
    for e in depth1_ranked[:args.top_k]:
        row = {
            "rank": e["rank"],
            "product_smiles": e["product_smiles"],
            "product_identity": X._identity(e["product_smiles"]),
            "source": e["source"],
            "score": e["edge_score"],
            "p_uspto": e["p_uspto"], "p_envipath": e["p_envipath"],
            "p_retrieval": e["p_retrieval"],
            "ion_filtered": e["ion_filtered"],
            "wildcard_filtered": e["wildcard_filtered"],
            "n_independent_sources": e.get("n_independent_sources", ""),
            "skeleton_unexplained": e.get("skeleton_unexplained", ""),
            "skeleton_reason": e.get("skeleton_reason", ""),
            "charge_variants": ";".join(e.get("charge_variants", [])
                                        or [e["product_smiles"]]),
            "score_semantics": sem,
            "is_calibrated_probability": False,
            "depth": 1,
        }
        top_rows.append(row)

    raw_stdout = {
        "case_id": cid,
        "input_smiles": smi,
        "input_identity": root_identity,
        "params": {"top_k": args.top_k, "max_depth": args.max_depth,
                   "K1": args.k1, "K2": args.k2, "scoring": args.scoring},
        "score_semantics": sem,
        "is_calibrated_probability": False,
        "depth_engine_invocations": engine_invocations,
        "top_predictions": top_rows,
        "n_edges": len(all_edges),
        "edges": [{k: e.get(k) for k in (
            "source_smiles", "product_smiles", "source_node_id",
            "product_node_id", "edge_score", "rank", "depth", "source",
            "p_uspto", "p_envipath", "p_retrieval", "ion_filtered",
            "wildcard_filtered", "cycle", "product_in_frontier",
            "n_independent_sources", "skeleton_unexplained",
            "skeleton_reason", "charge_variants")}
            for e in all_edges],
        "routes": [{"path_score": r["path_score"], "n_edges": r["n_edges"],
                    "steps": [{"depth": e["depth"], "rank": e["rank"],
                               "product_smiles": e["product_smiles"],
                               "score": e["edge_score"], "source": e["source"],
                               "skeleton_unexplained": e.get("skeleton_unexplained", False)}
                              for e in r["edges"]]}
                   for r in routes[:50]],
        "primary_route": {"rule": "greedy native rank=1 cascade",
                          "steps": [{"depth": e["depth"], "rank": e["rank"],
                                     "product_smiles": e["product_smiles"],
                                     "score": e["edge_score"], "source": e["source"]}
                                    for e in primary]},
        "budget_cut": res.get("budget_cut", False),
        "total_time_s": round(time.time() - t_start, 1),
    }
    with open(f"{prefix}_RAW_STDOUT.json", "w") as f:
        json.dump(raw_stdout, f, indent=1, ensure_ascii=False)

    with open(f"{prefix}_ALL_NORMALIZED_PREDICTIONS.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(top_rows[0].keys()))
        w.writeheader()
        w.writerows(top_rows)

    meta = {
        "case_id": cid,
        "input_smiles": smi,
        "input_canonical": Chem.MolToSmiles(mol),
        "input_formula": Chem.rdMolDescriptors.CalcMolFormula(mol),
        "libraries": libs,
        "params": raw_stdout["params"],
        "score_semantics": sem,
        "is_calibrated_probability": False,
        "depth_engine_invocations": engine_invocations,
        "total_time_s": round(time.time() - t_start, 1),
    }
    with open(f"{prefix}_RUN_META.json", "w") as f:
        json.dump(meta, f, indent=1, ensure_ascii=False)

    with open(f"{prefix}_TOP3_DIAGNOSTIC_ROUTES.jsonl", "w") as f:
        for r in routes[:3]:
            f.write(json.dumps({
                "path_score": r["path_score"], "n_edges": r["n_edges"],
                "steps": [{"depth": e["depth"], "rank": e["rank"],
                           "product_smiles": e["product_smiles"],
                           "identity": X._identity(e["product_smiles"]),
                           "score": e["edge_score"], "source": e["source"]}
                          for e in r["edges"]],
            }, ensure_ascii=False) + "\n")

    # ---- console summary ----
    print("\n=== TOP-{k} (scoring={s}) ===".format(k=args.top_k, s=args.scoring))
    for row in top_rows:
        print(f"  #{row['rank']:<2} {row['product_smiles']:<50} score={row['score']:.6f} "
              f"src={row['source']:<18} skel_flag={row['skeleton_unexplained']}")
    print(f"\ndepth_engine_invocations: {engine_invocations}")
    if routes:
        print(f"best route (path_score={routes[0]['path_score']:.6f}, "
              f"{routes[0]['n_edges']} steps):")
        for e in routes[0]["edges"]:
            print(f"   d{e['depth']} #{e['rank']} {e['product_smiles']}")
    if primary:
        print(f"PRIMARY (rank-1 cascade): {' -> '.join(e['product_smiles'] for e in primary)}")
    print(f"\noutputs: {prefix}_*.json / .csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
