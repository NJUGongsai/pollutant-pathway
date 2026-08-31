#!/usr/bin/env python3
"""BBD P4: multi-step degradation route expansion (BFS).

Recursively expands predicted products as new substrates through the three-engine
candidate generation + v3.2 scoring pipeline (ns_score + ion filter), up to
depth D=3.  Depth 1 reuses the v3.2 pool directly (guarantees generation-1
consistency); depth ≥ 2 runs the engines fresh.

Outputs: edge table (senior's 9-field format + extensions) + node table.

Answer-key isolation: this file NEVER reads the answer key.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
import time
from collections import Counter, defaultdict
from typing import Any

import multiprocessing as mp
import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(_HERE, "src"))

from rdkit import Chem, RDLogger
from rdkit.Chem import AllChem
RDLogger.DisableLog("rdApp.*")

import gnn_phase6_apply as A  # noqa: E402
import bbd_v3_features as F  # noqa: E402
import bbd_v32_ion_filter as IF  # noqa: E402
import predict_bbd_products_v2 as P2  # noqa: E402
import lightgbm as lgb
from ra import corpus, retrieval  # noqa: E402
from ra.chem import canonical_smiles  # noqa: E402

ROOT = "/Volumes/CC/Enzyme_Agent/depending"
V3_POOL = os.path.join(ROOT, "bbd_predictions/bbd_product_pool_v32.jsonl")
TEMPLATES = os.path.join(_HERE, "templates.json")
ENVIPATH_RULES = os.path.join(ROOT, "data/hfix/templates_implicitH.jsonl")
ENVIPATH_TSV = os.path.join(ROOT, "reaction_v3/data/lib_envipath/templates.tsv.gz")
CORPUS_DIR = os.path.join(_HERE, "data/corpus_v1")
MODEL_DIR = os.path.join(ROOT, "data/bbd_v31")
BLIND_CSV = os.path.join(
    ROOT,
    "bbd_known_pathway_full_route_v0_3_candidate_v3_1_strict_blind_fix_20260821"
    "/blind/BBD_KNOWN_PATHWAY_FULL_ROUTE_V0_3_V3_1_BLIND_PARENT_INPUTS_FOR_PREDICTION_STRICT.csv")

K1 = 5       # frontier size at depth 1
K2 = 5       # frontier size at depth ≥ 2
MAX_DEPTH = 3
RXN_BUDGET_D2 = 30.0  # engine A budget for depth ≥ 2 (vs 60 in v2)
POOL_CAP_D2 = 500     # candidate cap per substrate at depth ≥ 2
GLOBAL_NODE_LIMIT = 50000
GLOBAL_TIME_LIMIT_S = 7200  # 2 hours

SOURCES = ("uspto", "envipath", "retrieval")

# Globals for fork workers
_G_TPL_A: list | None = None
_G_RULES_B: list | None = None
_G_RECORDS: dict | None = None
_G_DONOR_TO_RECORDS: dict | None = None
_G_RANKERS: dict | None = None  # per-source rankers (loaded via initializer)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _stereo_blind(smi: str) -> str | None:
    m = Chem.MolFromSmiles(smi)
    return Chem.MolToSmiles(m, isomericSmiles=False) if m is not None else None


def _canon_iso(smi: str) -> str | None:
    try:
        return canonical_smiles(smi)
    except Exception:
        return None


def _node_id(case_id: str, depth: int, canonical_smi: str) -> str:
    """Content-hash node ID: {case_id}:{depth}:{sha1[:12]}."""
    h = hashlib.sha1(canonical_smi.encode()).hexdigest()[:12]
    return f"{case_id}:{depth}:{h}"


def _sig(a):
    return (a.GetSymbol(), a.GetIsAromatic(), a.GetFormalCharge())


def _belongs(src: str, sk: str) -> bool:
    return sk in src or (sk in ("uspto", "envipath") and src == "both")


# --------------------------------------------------------------------------- #
# Engine A + B + C candidate generation for a single substrate (depth ≥ 2)
# --------------------------------------------------------------------------- #
def _generate_candidates(substrate_smi: str, parent_sb: str,
                         retrieval_results: list) -> list[dict]:
    """Run three engines for a substrate, return merged candidate list.

    *retrieval_results* is the pre-computed top-K donor list for this substrate.
    """
    mol = Chem.MolFromSmiles(substrate_smi)
    if mol is None:
        return []
    n_atoms = mol.GetNumAtoms()
    cands: dict[str, dict] = {}

    # ---- Engine A: USPTO templates (30s budget) ----
    msigm = Counter(_sig(a) for a in mol.GetAtoms())
    t0 = time.time()
    budget_cut = False
    for rf, pf, freq, csm, rtype, n_rfrag in _G_TPL_A:
        if time.time() - t0 > RXN_BUDGET_D2:
            budget_cut = True
            break
        if any(csm[s] > msigm.get(s, 0) for s in csm):
            continue
        for prod_smi, site in A.apply_to(mol, rf, pf).items():
            iso = _canon_iso(prod_smi)
            if iso is None:
                continue
            if _stereo_blind(iso) == parent_sb:
                continue
            if iso not in cands:
                cands[iso] = {
                    "product_smiles": iso, "product_smiles_full": iso,
                    "source": "uspto", "template_freq": freq,
                    "reactions_count": 0, "pattern_atom_count": n_rfrag,
                    "n_evidence": 0, "max_tanimoto": 0.0,
                    "mean_tanimoto": 0.0, "donor_exact_match": False,
                }
            else:
                c = cands[iso]
                c["template_freq"] += freq
                if n_rfrag > c["pattern_atom_count"]:
                    c["pattern_atom_count"] = n_rfrag

    # ---- Engine B: enviPath rules ----
    for rule in _G_RULES_B:
        rt = rule["rt"]
        rxn = rule["rxn"]
        try:
            matches = mol.GetSubstructMatches(rt, maxMatches=1000)
        except Exception:
            continue
        if not matches:
            continue
        try:
            outs = rxn.RunReactants([mol])
        except Exception:
            continue
        if not outs:
            continue
        for prod_tuple in outs:
            clean_mols = []
            bad = False
            for p in prod_tuple:
                p2 = P2._strip_maps(p)
                try:
                    Chem.SanitizeMol(p2)
                except Exception:
                    bad = True
                    break
                if any(a.GetAtomicNum() == 0 for a in p2.GetAtoms()):
                    bad = True
                    break
                clean_mols.append(p2)
            if bad:
                continue
            all_frags = []
            for cm in clean_mols:
                all_frags.extend(Chem.GetMolFrags(cm, asMols=True))
            if not all_frags:
                continue
            frag_scored = [(f.GetNumAtoms(),
                            Chem.MolToSmiles(f, isomericSmiles=True), f)
                           for f in all_frags]
            frag_scored.sort(key=lambda x: (-x[0], x[1]))
            max_smi = frag_scored[0][1]
            if _stereo_blind(max_smi) == parent_sb:
                continue
            if max_smi not in cands:
                cands[max_smi] = {
                    "product_smiles": max_smi,
                    "product_smiles_full": ".".join(sorted(s for _, s, _ in frag_scored)),
                    "source": "envipath", "template_freq": 0,
                    "reactions_count": rule["reactions_count"],
                    "pattern_atom_count": rule["n_mapped"],
                    "n_evidence": 0, "max_tanimoto": 0.0,
                    "mean_tanimoto": 0.0, "donor_exact_match": False,
                }
            else:
                c = cands[max_smi]
                if "envipath" not in c["source"] and "uspto" in c["source"]:
                    c["source"] = "uspto+envipath"
                if rule["reactions_count"] > c["reactions_count"]:
                    c["reactions_count"] = rule["reactions_count"]
                if rule["n_mapped"] > c["pattern_atom_count"]:
                    c["pattern_atom_count"] = rule["n_mapped"]

    # ---- Engine C: retrieval ----
    for entry in retrieval_results:
        donor_smi = entry["donor_smiles"]
        tanimoto = entry["tanimoto"]
        donor_sb = _stereo_blind(donor_smi)
        is_exact = (donor_sb == parent_sb) if donor_sb and parent_sb else False
        for rid in entry.get("donor_records", []):
            rec = _G_RECORDS.get(rid)
            if rec is None:
                continue
            for prod_frag in rec.get("product_components", []):
                c_smi = _canon_iso(prod_frag)
                if not c_smi:
                    continue
                if _stereo_blind(c_smi) == parent_sb:
                    continue
                if c_smi not in cands:
                    cands[c_smi] = {
                        "product_smiles": c_smi, "product_smiles_full": c_smi,
                        "source": "retrieval", "template_freq": 0,
                        "reactions_count": 0, "pattern_atom_count": 0,
                        "n_evidence": 1, "max_tanimoto": tanimoto,
                        "mean_tanimoto": tanimoto,
                        "donor_exact_match": is_exact,
                    }
                else:
                    c = cands[c_smi]
                    if "retrieval" not in c["source"]:
                        if c["source"] == "uspto":
                            c["source"] = "uspto+retrieval"
                        elif c["source"] == "envipath":
                            c["source"] = "envipath+retrieval"
                        elif "uspto" in c["source"] and "envipath" in c["source"]:
                            c["source"] = "all"
                    c["n_evidence"] += 1
                    if tanimoto > c["max_tanimoto"]:
                        c["max_tanimoto"] = tanimoto
                    c["mean_tanimoto"] = ((c["mean_tanimoto"] * (c["n_evidence"] - 1)
                                           + tanimoto) / c["n_evidence"])
                    if is_exact:
                        c["donor_exact_match"] = True

    return list(cands.values()), budget_cut


# --------------------------------------------------------------------------- #
# v3.2 scoring pipeline (no-selector + ion filter)
# --------------------------------------------------------------------------- #
def _score_and_sort(candidates: list[dict], substrate_smi: str) -> list[dict]:
    """Compute v3.1 features, score with per-source rankers, ion filter, sort."""
    F.compute_v31_case_features(candidates, substrate_smi)

    for c in candidates:
        src = c.get("source", "")
        best_p = 0.0
        best_source = "uspto"
        for sk in SOURCES:
            if not _belongs(src, sk):
                continue
            feats = c.get("_v31_features", {}).get(sk)
            if feats is None or sk not in _G_RANKERS:
                continue
            p = float(_G_RANKERS[sk].predict([feats])[0])
            c[f"p_{sk}"] = p
            if p > best_p:
                best_p = p
                best_source = sk
        c["ns_score"] = best_p / 3.0
        c["ns_best_source"] = best_source
        c["ion_filtered"] = IF.is_ion_fragment(c["product_smiles"])
        # ensure all p fields exist
        for sk in SOURCES:
            c.setdefault(f"p_{sk}", 0.0)

    candidates.sort(key=lambda c: (c["ion_filtered"], -c["ns_score"],
                                    c["product_smiles"]))
    return candidates


# --------------------------------------------------------------------------- #
# Worker: process one frontier node
# --------------------------------------------------------------------------- #
def _init_worker(model_dir: str):
    """Load per-source rankers fresh in each worker (not fork-inherited)."""
    global _G_RANKERS
    _G_RANKERS = {}
    for sk in SOURCES:
        path = os.path.join(model_dir, f"{sk}_ranker.txt")
        if os.path.exists(path):
            _G_RANKERS[sk] = lgb.Booster(model_file=path)


def _process_frontier_node(node: dict) -> dict:
    """Generate candidates for one frontier node, score, sort, return results."""
    smi = node["smiles"]
    parent_sb = node["canonical_smiles"]
    retrieval = node.get("_retrieval", [])

    cands, budget_cut = _generate_candidates(smi, parent_sb, retrieval)
    if cands:
        cands = _score_and_sort(cands, smi)

    # pool cap
    pool_capped = False
    if len(cands) > POOL_CAP_D2:
        cands = cands[:POOL_CAP_D2]
        pool_capped = True

    # build edge data
    edges = []
    for rank, c in enumerate(cands):
        prod_canon = _stereo_blind(c["product_smiles"])
        is_cycle = prod_canon in node["ancestor_canons"] if prod_canon else False
        in_frontier = (not c["ion_filtered"] and not is_cycle
                       and rank < K2)  # top-K2 non-ion non-cycle
        edges.append({
            "product_smiles": c["product_smiles"],
            "product_canonical": prod_canon or "",
            "edge_score": round(c["ns_score"], 6),
            "rank": rank + 1,
            "source": c["source"],
            "p_uspto": round(c.get("p_uspto", 0.0), 6),
            "p_envipath": round(c.get("p_envipath", 0.0), 6),
            "p_retrieval": round(c.get("p_retrieval", 0.0), 6),
            "ion_filtered": c["ion_filtered"],
            "cycle": is_cycle,
            "product_in_frontier": in_frontier,
            "n_candidates_at_source": len(cands),
        })

    return {
        "source_node_id": node["node_id"],
        "source_case_id": node["case_id"],
        "source_depth": node["depth"],
        "source_smiles": smi,
        "edges": edges,
        "budget_cut": budget_cut,
        "pool_capped": pool_capped,
        "ancestor_canons": node["ancestor_canons"],
    }


# --------------------------------------------------------------------------- #
# Main expander
# --------------------------------------------------------------------------- #
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--v3-pool", default=V3_POOL)
    ap.add_argument("--blind-csv", required=True)
    ap.add_argument("--templates", default=TEMPLATES)
    ap.add_argument("--envipath-rules", default=ENVIPATH_RULES)
    ap.add_argument("--envipath-tsv", default=ENVIPATH_TSV)
    ap.add_argument("--corpus-dir", default=CORPUS_DIR)
    ap.add_argument("--model-dir", default=MODEL_DIR)
    ap.add_argument("--out-edges", required=True)
    ap.add_argument("--out-nodes", required=True)
    ap.add_argument("--out-report", required=True)
    ap.add_argument("--procs", type=int, default=min(8, os.cpu_count() or 4))
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    t_start = time.time()
    os.makedirs(os.path.dirname(args.out_edges), exist_ok=True)

    # ---- Step 1: Load v3.2 pool (depth 1) ----
    print("loading v3.2 pool...", flush=True)
    pool_cases = []
    with open(args.v3_pool) as f:
        for line in f:
            pool_cases.append(json.loads(line))
    if args.limit > 0:
        pool_cases = pool_cases[:args.limit]
    print(f"  {len(pool_cases)} cases", flush=True)

    # ---- Step 2: Parse templates + load rules ----
    print("parsing USPTO templates...", flush=True)
    global _G_TPL_A
    data = json.load(open(args.templates))
    parsed = []
    for tpl_str, freq in data["templates"].items():
        rf, pf = A.parse_template(tpl_str)
        if rf is None or pf is None:
            continue
        csm = Counter(_sig(a) for a in rf.GetAtoms() if a.GetAtomMapNum() > 0)
        rtype = A.template_type(rf)
        parsed.append((rf, pf, freq, csm, rtype, rf.GetNumAtoms()))
    _G_TPL_A = parsed
    print(f"  {len(parsed)} templates", flush=True)

    print("loading enviPath rules...", flush=True)
    global _G_RULES_B
    _G_RULES_B, _ = P2._load_envipath_rules(args.envipath_rules, args.envipath_tsv)
    print(f"  {len(_G_RULES_B)} rules", flush=True)

    # ---- Step 3: Load corpus for retrieval ----
    print("loading corpus...", flush=True)
    global _G_RECORDS, _G_DONOR_TO_RECORDS
    _G_RECORDS = {r["record_id"]: r
                  for r in corpus.read_records(os.path.join(args.corpus_dir, "corpus_v1.jsonl"))}
    donor_entries = corpus.load_donor_index(os.path.join(args.corpus_dir, "donor_index.jsonl"))
    donor_to_records: dict[str, list[str]] = defaultdict(list)
    for e in donor_entries:
        donor_to_records[e["donor_smiles"]].append(e["donor_record_id"])
    for k in donor_to_records:
        donor_to_records[k] = sorted(set(donor_to_records[k]))
    _G_DONOR_TO_RECORDS = donor_to_records
    donors = sorted(donor_to_records.keys())
    print(f"  {len(_G_RECORDS)} records, {len(donors)} donors", flush=True)

    # ---- Step 4: Build depth-1 from v3.2 pool ----
    print("building depth-1 from v3.2 pool...", flush=True)
    all_nodes = []  # node dicts
    all_edges = []  # edge dicts
    frontier = []  # nodes to expand next

    for r in pool_cases:
        cid = r["case_id"]
        smi = r["smiles"]
        parent_canon = _stereo_blind(smi) or smi
        root_node_id = _node_id(cid, 0, parent_canon)
        root_node = {
            "node_id": root_node_id, "case_id": cid, "depth": 0,
            "smiles": smi, "canonical_smiles": parent_canon,
            "is_root": True, "ancestor_canons": set(),
        }
        all_nodes.append(root_node)

        cands = r.get("all_candidates", [])
        # v3.2 pool is already sorted by (ion_filtered, -ns_score, product_smiles)
        for rank, c in enumerate(cands):
            prod_canon = _stereo_blind(c["product_smiles"]) or ""
            is_cycle = prod_canon == parent_canon  # parent-copy is a "cycle"
            in_frontier = (not c.get("ion_filtered", False)
                           and not is_cycle and rank < K1)
            edge = {
                "source_smiles": smi,
                "product_smiles": c["product_smiles"],
                "source_node_id": root_node_id,
                "product_node_id": _node_id(cid, 1, prod_canon),
                "edge_score": c.get("ns_score", 0.0),
                "rank": rank + 1,
                "depth": 1,
                "parent_case_id": cid,
                "parent_copy_filtered": is_cycle,
                "cycle": is_cycle,
                "product_in_frontier": in_frontier,
                "product_ion_filtered": c.get("ion_filtered", False),
                "source": c.get("source", ""),
                "p_uspto": c.get("p_uspto", 0.0),
                "p_envipath": c.get("p_envipath", 0.0),
                "p_retrieval": c.get("p_retrieval", 0.0),
                "n_candidates_at_source": len(cands),
            }
            all_edges.append(edge)

            if in_frontier:
                child_node = {
                    "node_id": edge["product_node_id"],
                    "case_id": cid, "depth": 1,
                    "smiles": c["product_smiles"],
                    "canonical_smiles": prod_canon,
                    "is_root": False,
                    "ancestor_canons": {parent_canon},
                    "path_score": c.get("ns_score", 0.0),
                }
                all_nodes.append(child_node)
                frontier.append(child_node)

    print(f"  depth-1: {len(frontier)} frontier nodes, {len(all_edges)} edges", flush=True)

    # ---- Step 5: BFS expansion (depth 2 to MAX_DEPTH) ----
    stats = {
        "depth_1_frontier": len(frontier),
        "depth_1_edges": len(all_edges),
        "budget_cuts": 0,
        "pool_capped": 0,
        "cycle_edges": 0,
    }

    for depth in range(2, MAX_DEPTH + 1):
        if not frontier:
            print(f"  depth {depth}: frontier empty, stopping", flush=True)
            break
        if len(all_nodes) > GLOBAL_NODE_LIMIT:
            print(f"  GLOBAL NODE LIMIT reached ({len(all_nodes)}), aborting", flush=True)
            break
        if time.time() - t_start > GLOBAL_TIME_LIMIT_S:
            print(f"  GLOBAL TIME LIMIT reached, aborting", flush=True)
            break

        print(f"depth {depth}: {len(frontier)} frontier nodes", flush=True)

        # Batch retrieval for all frontier SMILES
        q_map = {}
        for node in frontier:
            cs = node["canonical_smiles"]
            if cs not in q_map:
                q_map[cs] = cs
        print(f"  batch retrieval for {len(q_map)} unique substrates...", flush=True)
        ranked = retrieval.rank_queries(q_map, donors, k=20)
        retrieval_map = {}  # canonical_smi -> [{donor_smiles, tanimoto, donor_records}]
        for qs, topk in ranked.items():
            ev = []
            for hit in topk.get("topK", []):
                rec_ids = donor_to_records.get(hit["donor_smiles"], [])
                ev.append({
                    "donor_smiles": hit["donor_smiles"],
                    "tanimoto": hit["tanimoto"],
                    "donor_records": rec_ids,
                })
            retrieval_map[qs] = ev

        # Attach retrieval results to frontier nodes
        for node in frontier:
            node["_retrieval"] = retrieval_map.get(node["canonical_smiles"], [])

        # Process frontier in parallel
        ctx = mp.get_context("fork")
        with ctx.Pool(args.procs, initializer=_init_worker,
                      initargs=(args.model_dir,)) as pool:
            results = pool.map(_process_frontier_node, frontier, chunksize=10)

        # Collect results
        new_frontier = []
        for result in results:
            src_node_id = result["source_node_id"]
            src_case_id = result["source_case_id"]
            src_depth = result["source_depth"]
            src_smi = result["source_smiles"]
            ancestor_canons = result["ancestor_canons"]
            src_canon = _stereo_blind(src_smi) or src_smi

            if result["budget_cut"]:
                stats["budget_cuts"] += 1
            if result["pool_capped"]:
                stats["pool_capped"] += 1

            for edge_data in result["edges"]:
                prod_canon = edge_data["product_canonical"]
                is_cycle = edge_data["cycle"]
                if is_cycle:
                    stats["cycle_edges"] += 1

                prod_node_id = _node_id(src_case_id, depth, prod_canon)
                edge = {
                    "source_smiles": src_smi,
                    "product_smiles": edge_data["product_smiles"],
                    "source_node_id": src_node_id,
                    "product_node_id": prod_node_id,
                    "edge_score": edge_data["edge_score"],
                    "rank": edge_data["rank"],
                    "depth": depth,
                    "parent_case_id": src_case_id,
                    "parent_copy_filtered": prod_canon == src_canon,
                    "cycle": is_cycle,
                    "product_in_frontier": edge_data["product_in_frontier"],
                    "product_ion_filtered": edge_data["ion_filtered"],
                    "source": edge_data["source"],
                    "p_uspto": edge_data["p_uspto"],
                    "p_envipath": edge_data["p_envipath"],
                    "p_retrieval": edge_data["p_retrieval"],
                    "n_candidates_at_source": edge_data["n_candidates_at_source"],
                }
                all_edges.append(edge)

                if edge_data["product_in_frontier"]:
                    child_ancestors = ancestor_canons | {src_canon}
                    child_node = {
                        "node_id": prod_node_id,
                        "case_id": src_case_id, "depth": depth,
                        "smiles": edge_data["product_smiles"],
                        "canonical_smiles": prod_canon,
                        "is_root": False,
                        "ancestor_canons": child_ancestors,
                        "path_score": result["edges"][0]["edge_score"] if result["edges"] else 0.0,
                    }
                    # compute path_score = parent path_score × edge_score
                    parent_node = next(n for n in frontier
                                       if n["node_id"] == src_node_id)
                    child_node["path_score"] = round(
                        parent_node.get("path_score", 1.0) * edge_data["edge_score"], 6)
                    all_nodes.append(child_node)
                    new_frontier.append(child_node)

        stats[f"depth_{depth}_frontier"] = len(new_frontier)
        stats[f"depth_{depth}_edges"] = sum(1 for e in all_edges if e["depth"] == depth)
        frontier = new_frontier
        print(f"  depth {depth}: {len(new_frontier)} new frontier, "
              f"{stats[f'depth_{depth}_edges']} edges", flush=True)

    # ---- Step 6: Write output ----
    print("writing output...", flush=True)

    # Sort edges: (parent_case_id, depth, source_node_id, rank)
    all_edges.sort(key=lambda e: (e["parent_case_id"], e["depth"],
                                   e["source_node_id"], e["rank"]))

    with open(args.out_edges, "w") as f:
        for e in all_edges:
            f.write(json.dumps(e, ensure_ascii=False, sort_keys=True) + "\n")

    # Sort nodes: (parent_case_id, depth, node_id)
    all_nodes.sort(key=lambda n: (n["case_id"], n["depth"], n["node_id"]))

    with open(args.out_nodes, "w") as f:
        for n in all_nodes:
            out = {
                "node_id": n["node_id"],
                "case_id": n["case_id"],
                "depth": n["depth"],
                "smiles": n["smiles"],
                "canonical_smiles": n["canonical_smiles"],
                "is_root": n["is_root"],
                "n_children": sum(1 for e in all_edges
                                  if e["source_node_id"] == n["node_id"]),
                "path_score": n.get("path_score", 1.0 if n["is_root"] else 0.0),
            }
            f.write(json.dumps(out, ensure_ascii=False, sort_keys=True) + "\n")

    # Run report
    stats["total_nodes"] = len(all_nodes)
    stats["total_edges"] = len(all_edges)
    stats["total_time_s"] = round(time.time() - t_start, 2)
    stats["params"] = {"K1": K1, "K2": K2, "MAX_DEPTH": MAX_DEPTH,
                        "RXN_BUDGET_D2": RXN_BUDGET_D2,
                        "POOL_CAP_D2": POOL_CAP_D2}
    with open(args.out_report, "w") as f:
        json.dump(stats, f, indent=2, sort_keys=True)

    print(f"DONE: {len(all_nodes)} nodes, {len(all_edges)} edges, "
          f"{time.time()-t_start:.1f}s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
