#!/usr/bin/env python3
"""BBD P4.2 submission rebuild — depth-1 hybrid edges + P4.1 depth≥2 (verbatim).

Replaces only depth-1 edges in the P4.1 submission package with the hybrid
merged candidates (Layer 1 lookup-pinned + Layer 2 prediction, full-precision
+ cofactor filter).  Depth ≥ 2 edges/nodes are kept VERBATIM from the P4.1
submission (task §2 non-goal: "不做多步展开的 lookup" — multi-depth hybrid
expansion is P5 scope).  Node IDs are content-hashed so P4.1 depth-2 references
to depth-1 frontier nodes still resolve.

New on lookup edges: ``source = "eawag_lookup"`` and ``eawag_reactions``
evidence field (``btid#reac_id``), so a reviewer can trace each lookup hit to
its EAWAG reaction page.

Answer-key isolation: this file NEVER reads the answer key.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

from rdkit import Chem, RDLogger  # noqa: E402
RDLogger.DisableLog("rdApp.*")

import bbd_v32_ion_filter as IF  # noqa: E402
import bbd_cofactor_filter as CF  # noqa: E402
import expand_bbd_routes as EX  # noqa: E402  (helpers: _stereo_blind, _node_id, _is_wildcard, K1)

ROOT = "/Volumes/CC/Enzyme_Agent/depending"
HYBRID_POOL = os.path.join(ROOT, "bbd_predictions/bbd_hybrid_pool.jsonl")
P41_SUBMISSION = os.path.join(ROOT, "bbd_predictions/bbd_route_submission")
OUT_DIR = os.path.join(ROOT, "bbd_predictions/bbd_route_submission")


def _sb(smi):
    return EX._stereo_blind(smi)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--hybrid-pool", default=HYBRID_POOL)
    ap.add_argument("--p41-submission", default=P41_SUBMISSION)
    ap.add_argument("--out-dir", default=OUT_DIR)
    args = ap.parse_args()

    t0 = time.time()
    os.makedirs(args.out_dir, exist_ok=True)

    # ---- load hybrid pool (merged candidates per case) ----
    print("loading hybrid pool...", flush=True)
    hcases = []
    with open(args.hybrid_pool) as f:
        for line in f:
            hcases.append(json.loads(line))
    print(f"  {len(hcases)} cases", flush=True)

    # ---- load P4.1 submission: depth≥2 edges + depth≥2 nodes (keep verbatim) ----
    p41_edges_path = os.path.join(args.p41_submission, "edges.jsonl")
    p41_nodes_path = os.path.join(args.p41_submission, "nodes.jsonl")
    print("loading P4.1 depth≥2 edges/nodes (verbatim)...", flush=True)
    depth_ge2_edges = []
    depth_ge2_nodes = []
    with open(p41_edges_path) as f:
        for line in f:
            e = json.loads(line)
            if e.get("depth", 1) >= 2:
                depth_ge2_edges.append(e)
    with open(p41_nodes_path) as f:
        for line in f:
            n = json.loads(line)
            if n.get("depth", 0) >= 2:
                depth_ge2_nodes.append(n)
    print(f"  depth≥2: {len(depth_ge2_edges)} edges, {len(depth_ge2_nodes)} nodes",
          flush=True)

    # ---- rebuild depth-1 edges + depth-0/1 nodes from hybrid pool ----
    print("building depth-1 hybrid edges...", flush=True)
    d1_edges = []
    d0_d1_nodes = []
    n_lookup_edges = 0

    for r in hcases:
        cid = r["case_id"]
        smi = r["smiles"]
        parent_canon = _sb(smi) or smi
        root_id = EX._node_id(cid, 0, parent_canon)
        # depth-0 root node
        d0_d1_nodes.append({
            "node_id": root_id, "case_id": cid, "depth": 0,
            "smiles": smi, "canonical_smiles": parent_canon,
            "is_root": True, "n_children": 0, "path_score": 1.0,
        })
        cands = r.get("all_candidates", [])
        for rank, c in enumerate(cands):
            prod = c.get("product_smiles", "")
            prod_canon = _sb(prod) or ""
            is_cycle = prod_canon == parent_canon
            wc = EX._is_wildcard(prod)
            ion = c.get("ion_filtered", IF.is_ion_fragment(prod))
            cof = c.get("cofactor_filtered", CF.is_cofactor_conjugate(prod))
            in_frontier = (not ion and not wc and not cof and not is_cycle
                           and rank < EX.K1)
            is_lookup = (c.get("layer") == "lookup"
                          or c.get("source") == "eawag_lookup")
            edge = {
                "source_smiles": smi,
                "product_smiles": prod,
                "source_node_id": root_id,
                "product_node_id": EX._node_id(cid, 1, prod_canon),
                "edge_score": (c.get("tanimoto", 0.0) if is_lookup
                               else c.get("ns_score", 0.0)),
                "rank": rank + 1,
                "depth": 1,
                "parent_case_id": cid,
                "parent_copy_filtered": is_cycle,
                "cycle": is_cycle,
                "product_in_frontier": in_frontier,
                "product_ion_filtered": ion,
                "product_wildcard_filtered": wc,
                "source": ("eawag_lookup" if is_lookup else c.get("source", "")),
                "p_uspto": c.get("p_uspto", 0.0),
                "p_envipath": c.get("p_envipath", 0.0),
                "p_retrieval": c.get("p_retrieval", 0.0),
                "n_candidates_at_source": len(cands),
                "cofactor_filtered": cof,
                "layer": c.get("layer", "prediction"),
            }
            if is_lookup:
                edge["eawag_reactions"] = c.get("eawag_reactions", [])
                edge["tanimoto"] = c.get("tanimoto", 0.0)
                n_lookup_edges += 1
            d1_edges.append(edge)

            # depth-1 node (non-root); path_score = edge_score
            if True:  # emit a node per depth-1 candidate (frontier + non-frontier)
                d0_d1_nodes.append({
                    "node_id": edge["product_node_id"],
                    "case_id": cid, "depth": 1,
                    "smiles": prod, "canonical_smiles": prod_canon,
                    "is_root": False, "n_children": 0,
                    "path_score": round(edge["edge_score"], 6),
                })

    print(f"  depth-1: {len(d1_edges)} edges ({n_lookup_edges} lookup), "
          f"{len(d0_d1_nodes)} depth-0/1 nodes", flush=True)

    # ---- merge + sort ----
    all_edges = d1_edges + depth_ge2_edges
    all_nodes = d0_d1_nodes + depth_ge2_nodes
    all_edges.sort(key=lambda e: (e["parent_case_id"], e["depth"],
                                   e["source_node_id"], e["rank"]))
    all_nodes.sort(key=lambda n: (n["case_id"], n["depth"], n["node_id"]))

    # recompute n_children for depth-0 and depth-1 nodes
    children_count = {}
    for e in all_edges:
        children_count[e["source_node_id"]] = children_count.get(
            e["source_node_id"], 0) + 1
    for n in all_nodes:
        n["n_children"] = children_count.get(n["node_id"], 0)

    # ---- write ----
    out_edges = os.path.join(args.out_dir, "edges.jsonl")
    out_nodes = os.path.join(args.out_dir, "nodes.jsonl")
    with open(out_edges, "w") as f:
        for e in all_edges:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    with open(out_nodes, "w") as f:
        for n in all_nodes:
            f.write(json.dumps(n, ensure_ascii=False) + "\n")

    # ---- MANIFEST ----
    manifest = os.path.join(args.out_dir, "MANIFEST.sha256")
    files = ["README_SUBMISSION.md", "edges.jsonl", "nodes.jsonl", "MANIFEST.sha256"]
    lines = []
    for fn in files:
        p = os.path.join(args.out_dir, fn)
        if os.path.exists(p) and fn != "MANIFEST.sha256":
            h = hashlib.sha256(open(p, "rb").read()).hexdigest()
            lines.append(f"{h}  {fn}")
    # MANIFEST self-hash last (standard sha256sum recursive convention)
    with open(manifest, "w") as f:
        f.write("\n".join(lines) + "\n")
    # append self hash
    self_h = hashlib.sha256(open(manifest, "rb").read()).hexdigest()
    with open(manifest, "a") as f:
        f.write(f"{self_h}  MANIFEST.sha256\n")

    print(f"DONE: {len(all_edges)} edges, {len(all_nodes)} nodes, "
          f"{n_lookup_edges} lookup edges w/ evidence, {time.time()-t0:.1f}s",
          flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
