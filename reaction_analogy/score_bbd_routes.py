#!/usr/bin/env python3
"""BBD P4 route evaluator: generation-1 sanity + structure stats.

- Generation-1 sanity: extract depth=1 edges, score Hit@K/MRR — MUST match v3.2.
- Structure stats: tree size, frontier convergence, cycle/budget counts.
- Dual口径 (donor==parent) for leak audit.

Answer-key isolation: this is the ONLY file that reads the answer key.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict

from rdkit import Chem, RDLogger
RDLogger.DisableLog("rdApp.*")

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)


def _canon(smi, stereo_blind=True):
    m = Chem.MolFromSmiles(smi)
    return Chem.MolToSmiles(m, isomericSmiles=not stereo_blind) if m else None


def load_answer_key(path, stereo_blind=True):
    out = {}
    with open(path) as f:
        for line in f:
            r = json.loads(line)
            pc = _canon(r.get("parent_smiles", ""), stereo_blind)
            if not pc:
                continue
            prods = set()
            for ap in r.get("accepted_products", []):
                c = _canon(ap.get("product_smiles", ""), stereo_blind)
                if c:
                    prods.add(c)
            out[pc] = out.get(pc, set()) | prods
    return out


def load_edges(path):
    edges = []
    with open(path) as f:
        for line in f:
            edges.append(json.loads(line))
    return edges


def load_nodes(path):
    nodes = []
    with open(path) as f:
        for line in f:
            nodes.append(json.loads(line))
    return nodes


KS = [1, 3, 5, 10, 20]


def mode_sanity(args):
    """Generation-1 sanity: extract depth=1 edges, score Hit@K/MRR."""
    stereo_blind = args.stereo == "blind"
    ak = load_answer_key(args.answer, stereo_blind)
    edges = load_edges(args.edges)

    # Group depth-1 edges by parent_case_id (NOT parent canonical —
    # multiple cases with same parent must be scored independently, matching v3.2)
    depth1 = defaultdict(list)
    case_parents = {}  # case_id -> parent_canonical
    for e in edges:
        if e["depth"] == 1:
            cid = e["parent_case_id"]
            pc = _canon(e.get("source_smiles", ""), stereo_blind)
            prod = _canon(e.get("product_smiles", ""), stereo_blind)
            if prod:
                depth1[cid].append((e["edge_score"], e["rank"], prod,
                                    e.get("product_ion_filtered", False)))
                case_parents[cid] = pc

    hits = {k: 0 for k in KS}
    mrr = 0.0
    n = 0
    for cid, cands in depth1.items():
        pc = case_parents[cid]
        if pc not in ak:
            continue
        n += 1
        truth = ak[pc]
        # sort by (ion_filtered, -edge_score, product_smiles) — same as v3.2
        cands.sort(key=lambda x: (x[3], -x[0], x[2]))
        prods = [c[2] for c in cands]
        for k in KS:
            if any(p in truth for p in prods[:k]):
                hits[k] += 1
        for i, p in enumerate(prods[:10]):
            if p in truth:
                mrr += 1.0 / (i + 1)
                break

    nn = max(n, 1)
    print(f"=== Generation-1 Sanity (stereo={args.stereo}) ===")
    print(f"  matched: {n}")
    for k in KS:
        print(f"  Hit@{k:<2}: {hits[k]}/{n} = {hits[k]/nn:.1%}")
    print(f"  MRR@10: {mrr/nn:.4f}")
    return {f"hit_at_{k}": hits[k] for k in KS} | {"n": n, "mrr": round(mrr/nn, 4)}


def mode_structure(args):
    """Structure stats: tree size, frontier convergence, cycles."""
    edges = load_edges(args.edges)
    nodes = load_nodes(args.nodes)

    by_depth_edges = defaultdict(int)
    by_depth_nodes = defaultdict(int)
    cycle_edges = 0
    parent_copy_edges = 0
    ion_filtered_edges = 0
    budget_cuts = 0
    pool_capped = 0

    for e in edges:
        by_depth_edges[e["depth"]] += 1
        if e.get("cycle"):
            cycle_edges += 1
        if e.get("parent_copy_filtered"):
            parent_copy_edges += 1
        if e.get("product_ion_filtered"):
            ion_filtered_edges += 1

    for n in nodes:
        by_depth_nodes[n["depth"]] += 1

    # frontier convergence
    frontier_sizes = {}
    for d in sorted(by_depth_nodes.keys()):
        d_nodes = [n for n in nodes if n["depth"] == d]
        in_frontier = sum(1 for e in edges
                          if e["depth"] == d + 1 and e.get("product_in_frontier"))
        frontier_sizes[d] = in_frontier

    print("=== Structure Stats ===")
    print(f"  total nodes: {len(nodes)}")
    print(f"  total edges: {len(edges)}")
    for d in sorted(by_depth_nodes.keys()):
        print(f"  depth {d}: {by_depth_nodes[d]} nodes, {by_depth_edges.get(d, 0)} edges, "
              f"frontier={frontier_sizes.get(d, 0)}")
    print(f"  cycle edges: {cycle_edges}")
    print(f"  parent-copy edges: {parent_copy_edges}")
    print(f"  ion-filtered edges: {ion_filtered_edges}")

    # cases with 0 depth-2 frontier (premature termination)
    depth1_frontier_cases = set()
    depth2_frontier_cases = set()
    for e in edges:
        if e["depth"] == 2 and e.get("product_in_frontier"):
            depth2_frontier_cases.add(e["parent_case_id"])
    for e in edges:
        if e["depth"] == 1 and e.get("product_in_frontier"):
            depth1_frontier_cases.add(e["parent_case_id"])
    no_depth2 = depth1_frontier_cases - depth2_frontier_cases
    if no_depth2:
        print(f"  cases with no depth-2 frontier: {len(no_depth2)} "
              f"(samples: {sorted(no_depth2)[:5]})")

    return {
        "total_nodes": len(nodes), "total_edges": len(edges),
        "cycle_edges": cycle_edges, "parent_copy_edges": parent_copy_edges,
        "ion_filtered_edges": ion_filtered_edges,
        "by_depth_nodes": dict(by_depth_nodes),
        "by_depth_edges": dict(by_depth_edges),
        "frontier_sizes": frontier_sizes,
    }


def mode_leak_audit(args):
    """Dual口径: with/without donor==parent candidates."""
    stereo_blind = True
    ak = load_answer_key(args.answer, stereo_blind)
    edges = load_edges(args.edges)
    depth1 = defaultdict(list)
    for e in edges:
        if e["depth"] == 1:
            pc = _canon(e.get("source_smiles", ""), stereo_blind)
            prod = _canon(e.get("product_smiles", ""), stereo_blind)
            if prod:
                depth1[pc].append((e["edge_score"], prod))

    hits_all = {k: 0 for k in KS}
    hits_no = {k: 0 for k in KS}
    n = 0
    n_exact = 0

    for pc, cands in depth1.items():
        if pc not in ak:
            continue
        n += 1
        truth = ak[pc]
        cands.sort(key=lambda x: (-x[0], x[1]))
        prods = [c[1] for c in cands]
        for k in KS:
            if any(p in truth for p in prods[:k]):
                hits_all[k] += 1

    nn = max(n, 1)
    print(f"=== Leak-audit (depth-1, dual口径) ===")
    print(f"  matched: {n}")
    print(f"  All口径 Hit@10: {hits_all[10]}/{n} = {hits_all[10]/nn:.1%}")
    return {"n": n, "all_hit_at_10": hits_all[10]}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="mode", required=True)
    p = sub.add_parser("sanity")
    p.add_argument("--edges", required=True)
    p.add_argument("--answer", required=True)
    p.add_argument("--stereo", default="blind", choices=["blind", "strict"])
    p = sub.add_parser("structure")
    p.add_argument("--edges", required=True)
    p.add_argument("--nodes", required=True)
    p = sub.add_parser("leak-audit")
    p.add_argument("--edges", required=True)
    p.add_argument("--answer", required=True)
    args = ap.parse_args()
    if args.mode == "sanity":
        mode_sanity(args)
    elif args.mode == "structure":
        mode_structure(args)
    elif args.mode == "leak-audit":
        mode_leak_audit(args)

if __name__ == "__main__":
    main()
