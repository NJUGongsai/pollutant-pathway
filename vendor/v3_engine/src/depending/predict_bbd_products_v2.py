#!/usr/bin/env python3
"""BBD v2: dual-engine candidate generation + composite ranking.

Engine A — USPTO 188,725 templates via graph-edit (``gnn_phase6_apply.apply_to``).
Engine B — enviPath 286 implicit-H rules via RDKit ``RunReactants``.

Candidates from both engines are merged (dedup by isomeric canonical product
SMILES), parent-filtered, and ranked by the composite score in
``bbd_v2_scoring.score_candidate``.  Output: top-20 predictions, full candidate
pool, and a run report.

Answer-key isolation: this file NEVER reads the restricted answer key or
``route_a_audit``.  Only ``score_bbd_hitk_v2.py`` touches the answer key.

Determinism: candidates are sorted by ``(-score, product_smiles)``; cases are
sorted by ``case_id`` before writing.  Two runs must be byte-identical.

Usage::

    python predict_bbd_products_v2.py [--limit N] [--procs P] \
        --blind <csv> --mpnn <jsonl> --templates <json> \
        --envipath-rules <jsonl> --envipath-tsv <tsv.gz> \
        --out-preds <jsonl> --out-pool <jsonl> --out-report <json>
"""
from __future__ import annotations

import argparse
import csv
import gzip
import json
import os
import sys
import time
from collections import Counter
from typing import Any

import multiprocessing as mp

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(_HERE, "src"))
from rdkit import Chem, RDLogger
from rdkit.Chem import AllChem

RDLogger.DisableLog("rdApp.*")

import gnn_phase6_apply as A  # noqa: E402
import bbd_v2_scoring as S  # noqa: E402

# --------------------------------------------------------------------------- #
# Constants
# --------------------------------------------------------------------------- #
RXN_BUDGET = 60.0       # per-case wall-clock budget for Engine A (seconds)
POOL_CAP = 2000         # max candidates per case in the pool file
TOP_K = 20              # top-K predictions written to the predictions file

# --------------------------------------------------------------------------- #
# Module globals — set ONCE in the parent before forking the pool.
# With fork (default on this machine), children inherit these via COW.
# --------------------------------------------------------------------------- #
_G_TPL_A: list | None = None     # parsed USPTO templates
_G_RULES_B: list | None = None   # parsed enviPath rules
_G_MPNN: dict | None = None      # SMILES -> atom_probs list


# --------------------------------------------------------------------------- #
# Canonicalisation helpers
# --------------------------------------------------------------------------- #
def _sig(a):
    """Element signature for the USPTO pre-filter (symbol, aromaticity, charge)."""
    return (a.GetSymbol(), a.GetIsAromatic(), a.GetFormalCharge())


def _strip_maps(mol: Chem.Mol) -> Chem.Mol:
    """Return a RWMol copy with all atom maps zeroed (in-place on the copy)."""
    rw = Chem.RWMol(mol)
    for a in rw.GetAtoms():
        a.SetAtomMapNum(0)
    return rw.GetMol()


def _max_frag_canon(mol: Chem.Mol, isomeric: bool = True) -> str | None:
    """Isomeric canonical SMILES of the largest fragment.

    Ties broken by canonical SMILES ascending (deterministic).  Atom maps are
    stripped first.  This mirrors ``gnn_phase6_apply.canon_nomap`` but with
    ``isomericSmiles=True`` and deterministic tie-breaking.
    """
    m = _strip_maps(mol)
    frags = Chem.GetMolFrags(m, asMols=True)
    if len(frags) <= 1:
        return Chem.MolToSmiles(m, isomericSmiles=isomeric)
    scored = sorted(
        frags,
        key=lambda f: (-f.GetNumAtoms(), Chem.MolToSmiles(f, isomericSmiles=isomeric)),
    )
    return Chem.MolToSmiles(scored[0], isomericSmiles=isomeric)


def _full_frag_canon(mol: Chem.Mol, isomeric: bool = True) -> str | None:
    """Canonical SMILES of the *entire* product (all fragments sorted, joined
    by '.').  Atom maps stripped.  Deterministic."""
    m = _strip_maps(mol)
    frags = Chem.GetMolFrags(m, asMols=True)
    smis = sorted(Chem.MolToSmiles(f, isomericSmiles=isomeric) for f in frags)
    return ".".join(smis)


def _stereo_blind(smi: str) -> str | None:
    """Canonical SMILES with isomericSmiles=False (stereo-blind口径)."""
    m = Chem.MolFromSmiles(smi)
    if m is None:
        return None
    return Chem.MolToSmiles(m, isomericSmiles=False)


def _to_isomeric(smi: str) -> str | None:
    """Re-canonicalise a SMILES string to isomeric form."""
    m = Chem.MolFromSmiles(smi)
    if m is None:
        return None
    return Chem.MolToSmiles(m, isomericSmiles=True)


# --------------------------------------------------------------------------- #
# MPNN site-feature helper
# --------------------------------------------------------------------------- #
def _mpnn_site(site, atom_probs, n_atoms):
    """(mean, max) of atom_probs at the given atom indices.

    Returns (0.0, 0.0) when probs are missing or the length mismatches
    ``n_atoms`` (e.g. if Hs were added mid-pipeline — must never happen here).
    """
    if not atom_probs or len(atom_probs) != n_atoms:
        return (0.0, 0.0)
    probs = [atom_probs[i] for i in site if 0 <= i < len(atom_probs)]
    if not probs:
        return (0.0, 0.0)
    return (sum(probs) / len(probs), max(probs))


def _better_mpnn(mean_a, max_a, mean_b, max_b) -> bool:
    """True if site A's combined MPNN score (0.5*mean+0.5*max) exceeds B's."""
    return (0.5 * mean_a + 0.5 * max_a) > (0.5 * mean_b + 0.5 * max_b)


# --------------------------------------------------------------------------- #
# Engine A — USPTO graph-edit
# --------------------------------------------------------------------------- #
def _parse_templates_a(templates_path: str) -> list:
    """Pre-parse all USPTO templates in the parent process (done once).

    Returns a list of ``(r_frag, p_frag, freq, sig_counter, rtype,
    n_rfrag_atoms)``.
    """
    data = json.load(open(templates_path))
    parsed = []
    for tpl_str, freq in data["templates"].items():
        rf, pf = A.parse_template(tpl_str)
        if rf is None or pf is None:
            continue
        csm = Counter(_sig(a) for a in rf.GetAtoms() if a.GetAtomMapNum() > 0)
        rtype = A.template_type(rf)
        parsed.append((rf, pf, freq, csm, rtype, rf.GetNumAtoms()))
    return parsed


def _run_engine_a(mol, atom_probs, n_atoms, counters):
    """USPTO graph-edit candidate generation.

    Returns ``{product_smiles: {fields}}``  (after parent filter).
    """
    msigm = Counter(_sig(a) for a in mol.GetAtoms())
    parent_sb = Chem.MolToSmiles(mol, isomericSmiles=False)
    cands = {}
    t0 = time.time()
    budget_cut = False
    for rf, pf, freq, csm, rtype, n_rfrag in _G_TPL_A:
        if time.time() - t0 > RXN_BUDGET:
            budget_cut = True
            break
        # quick element-signature pre-filter
        if any(csm[s] > msigm.get(s, 0) for s in csm):
            continue
        for prod_nomap, site in A.apply_to(mol, rf, pf).items():
            # prod_nomap is canon_nomap (non-isomeric, max-fragment, map-stripped)
            iso = _to_isomeric(prod_nomap)
            if iso is None:
                continue
            # parent filter (stereo-blind口径)
            if _stereo_blind(iso) == parent_sb:
                counters["parent_filtered_a"] += 1
                continue
            mean_p, max_p = _mpnn_site(list(site), atom_probs, n_atoms)
            if iso not in cands:
                cands[iso] = {
                    "product_smiles": iso,
                    "product_smiles_full": iso,  # Engine A: single fragment
                    "template_freq": freq,
                    "reactions_count": 0,
                    "pattern_atom_count": n_rfrag,
                    "mpnn_site_mean": mean_p,
                    "mpnn_site_max": max_p,
                    "site_atoms": sorted(site),
                    "rule_ids": [],
                    "sources": {"uspto"},
                }
            else:
                c = cands[iso]
                c["template_freq"] += freq
                if n_rfrag > c["pattern_atom_count"]:
                    c["pattern_atom_count"] = n_rfrag
                if _better_mpnn(mean_p, max_p, c["mpnn_site_mean"], c["mpnn_site_max"]):
                    c["mpnn_site_mean"] = mean_p
                    c["mpnn_site_max"] = max_p
                    c["site_atoms"] = sorted(site)
    counters["budget_cut_a"] = 1 if budget_cut else 0
    return cands


# --------------------------------------------------------------------------- #
# Engine B — enviPath RunReactants
# --------------------------------------------------------------------------- #
def _load_envipath_rules(rules_path: str, tsv_path: str) -> list:
    """Load and pre-parse the 286 enviPath rules.

    Returns a list of dicts with keys: ``tid, rxn, rt, mapped_idx,
    reactions_count, n_mapped``.  Multi-fragment reactant rules are kept here
    but flagged at run time (the skip is counted per case so the count is
    visible in the report).  Actually, multi-fragment rules are skipped once
    here and counted in ``skip_multi_fragment_rule_global``.
    """
    # reactions_count from TSV, keyed by template_id
    rc_map = {}
    with gzip.open(tsv_path, "rt", encoding="utf-8") as f:
        raw = f.read()
    lines = [ln for ln in raw.split("\n") if ln.strip()]
    header = lines[0].split("\t")
    tid_idx = header.index("TEMPLATE_ID")
    rc_idx = header.index("REACTIONS_COUNT")
    for ln in lines[1:]:
        flds = ln.split("\t")
        if len(flds) <= max(tid_idx, rc_idx):
            continue
        tid = flds[tid_idx]
        rc_s = flds[rc_idx]
        rc_map[tid] = int(rc_s) if rc_s.isdigit() else 0

    rules = []
    skip_multi = 0
    with open(rules_path, encoding="utf-8") as f:
        for line in f:
            d = json.loads(line)
            tid = d["template_id"]
            smirks = d["reencoded_smirks"]
            rxn = AllChem.ReactionFromSmarts(smirks)
            if rxn is None:
                skip_multi += 1  # unparseable; count as skip
                continue
            if rxn.GetNumReactantTemplates() != 1:
                skip_multi += 1
                continue
            rt = rxn.GetReactantTemplate(0)
            mapped_idx = [a.GetIdx() for a in rt.GetAtoms() if a.GetAtomMapNum() > 0]
            if not mapped_idx:
                skip_multi += 1
                continue
            rules.append({
                "tid": tid,
                "rxn": rxn,
                "rt": rt,
                "mapped_idx": mapped_idx,
                "reactions_count": rc_map.get(tid, 0),
                "n_mapped": len(mapped_idx),
            })
    return rules, skip_multi


def _run_engine_b(mol, atom_probs, n_atoms, counters):
    """enviPath RunReactants candidate generation.

    Returns ``{product_smiles: {fields}}`` (after parent filter).
    """
    parent_sb = Chem.MolToSmiles(mol, isomericSmiles=False)
    mpnn_ok = bool(atom_probs) and len(atom_probs) == n_atoms
    if not mpnn_ok:
        counters["mpnn_index_mismatch"] += 1

    cands = {}
    for rule in _G_RULES_B:
        rt = rule["rt"]
        rxn = rule["rxn"]
        mapped_idx = rule["mapped_idx"]

        # enumerate all substructure matches → site_sets for MPNN features
        try:
            matches = mol.GetSubstructMatches(rt, maxMatches=1000)
        except Exception:
            counters["skip_match_error"] += 1
            matches = ()
        if not matches:
            continue

        # best MPNN site across all matches (approximate: RunReactants internal
        # matches don't 1:1 correspond to GetSubstructMatches; take aggregate max)
        best_mean, best_max = 0.0, 0.0
        best_site: list[int] = []
        for m in matches:
            site = [m[i] for i in mapped_idx]
            mean_p, max_p = _mpnn_site(site, atom_probs, n_atoms)
            if _better_mpnn(mean_p, max_p, best_mean, best_max):
                best_mean, best_max = mean_p, max_p
                best_site = sorted(site)

        # apply reaction
        try:
            outs = rxn.RunReactants([mol])
        except Exception:
            counters["skip_runreactants_error"] += 1
            continue
        if not outs:
            continue

        for prod_tuple in outs:
            # ---- 1. strip maps + sanitize each fragment (fail-closed) ----
            clean_mols = []
            bad = False
            for p in prod_tuple:
                p2 = _strip_maps(p)
                try:
                    Chem.SanitizeMol(p2)
                except Exception:
                    counters["skip_unsanitizable"] += 1
                    bad = True
                    break
                if any(a.GetAtomicNum() == 0 for a in p2.GetAtoms()):
                    counters["skip_wildcard"] += 1
                    bad = True
                    break
                clean_mols.append(p2)
            if bad:
                continue

            # ---- 2. collect all fragments across the product tuple ----
            all_frags = []
            for cm in clean_mols:
                frags = Chem.GetMolFrags(cm, asMols=True)
                all_frags.extend(frags)
            if not all_frags:
                continue

            frag_scored = [
                (f.GetNumAtoms(), Chem.MolToSmiles(f, isomericSmiles=True), f)
                for f in all_frags
            ]

            # ---- 3. product_smiles_full: all fragments sorted, joined by '.' ----
            full_smi = ".".join(sorted(s for _, s, _ in frag_scored))

            # ---- 4. product_smiles: max fragment (tie: canonical sort) ----
            frag_scored.sort(key=lambda x: (-x[0], x[1]))
            max_smi = frag_scored[0][1]

            # ---- 5. parent filter (stereo-blind口径) ----
            if _stereo_blind(max_smi) == parent_sb:
                counters["parent_filtered_b"] += 1
                continue

            # ---- record candidate ----
            if max_smi not in cands:
                cands[max_smi] = {
                    "product_smiles": max_smi,
                    "product_smiles_full": full_smi,
                    "template_freq": 0,
                    "reactions_count": rule["reactions_count"],
                    "pattern_atom_count": rule["n_mapped"],
                    "mpnn_site_mean": best_mean,
                    "mpnn_site_max": best_max,
                    "site_atoms": best_site,
                    "rule_ids": [rule["tid"]],
                    "sources": {"envipath"},
                }
            else:
                c = cands[max_smi]
                if rule["tid"] not in c["rule_ids"]:
                    c["rule_ids"].append(rule["tid"])
                if rule["reactions_count"] > c["reactions_count"]:
                    c["reactions_count"] = rule["reactions_count"]
                if rule["n_mapped"] > c["pattern_atom_count"]:
                    c["pattern_atom_count"] = rule["n_mapped"]
                if _better_mpnn(best_mean, best_max, c["mpnn_site_mean"], c["mpnn_site_max"]):
                    c["mpnn_site_mean"] = best_mean
                    c["mpnn_site_max"] = best_max
                    c["site_atoms"] = best_site
                # prefer the full SMILES with more fragments (enviPath may split)
                if full_smi.count(".") > c["product_smiles_full"].count("."):
                    c["product_smiles_full"] = full_smi

    return cands


# --------------------------------------------------------------------------- #
# Merge + score + rank
# --------------------------------------------------------------------------- #
def _merge_cands(cands_a: dict, cands_b: dict, counters: dict) -> list[dict]:
    """Merge the two engines' candidate dicts, score, and rank.

    Dedup key is ``product_smiles`` (isomeric, max-fragment).  When both engines
    produce the same product, ``source`` becomes ``"both"`` and each engine's
    fields coexist (template_freq from A, reactions_count from B, etc.).
    """
    merged: dict[str, dict] = {}
    for src_label, cands in (("uspto", cands_a), ("envipath", cands_b)):
        for smi, c in cands.items():
            if smi not in merged:
                merged[smi] = dict(c)
                merged[smi]["sources"] = set(c["sources"])
            else:
                mc = merged[smi]
                mc["sources"].update(c["sources"])
                # take max of numeric fields
                if c["pattern_atom_count"] > mc["pattern_atom_count"]:
                    mc["pattern_atom_count"] = c["pattern_atom_count"]
                if c["template_freq"] > mc["template_freq"]:
                    mc["template_freq"] = c["template_freq"]
                if c["reactions_count"] > mc["reactions_count"]:
                    mc["reactions_count"] = c["reactions_count"]
                if _better_mpnn(c["mpnn_site_mean"], c["mpnn_site_max"],
                                mc["mpnn_site_mean"], mc["mpnn_site_max"]):
                    mc["mpnn_site_mean"] = c["mpnn_site_mean"]
                    mc["mpnn_site_max"] = c["mpnn_site_max"]
                    mc["site_atoms"] = c["site_atoms"]
                # rule_ids from enviPath
                for tid in c.get("rule_ids", []):
                    if tid not in mc["rule_ids"]:
                        mc["rule_ids"].append(tid)
                # prefer fuller product_smiles_full
                if c["product_smiles_full"].count(".") > mc["product_smiles_full"].count("."):
                    mc["product_smiles_full"] = c["product_smiles_full"]

    # finalise source + rank
    out = []
    for smi, c in merged.items():
        srcs = c.pop("sources")
        if "uspto" in srcs and "envipath" in srcs:
            c["source"] = "both"
        elif "envipath" in srcs:
            c["source"] = "envipath"
        else:
            c["source"] = "uspto"
        c["rule_ids"] = sorted(c["rule_ids"])
        out.append(c)

    S.rank_candidates(out)
    return out


# --------------------------------------------------------------------------- #
# Per-case processing (worker function)
# --------------------------------------------------------------------------- #
def _process_case(row: dict) -> dict:
    case_id = row.get("full_route_case_id", "")
    smi = row.get("parent_smiles", "")
    mol = Chem.MolFromSmiles(smi)
    if mol is None:
        return {
            "case_id": case_id, "smiles": smi, "n_atoms": 0,
            "error": "parse_fail",
            "n_cand_uspto": 0, "n_cand_envipath": 0,
            "n_cand_union": 0, "parent_filtered": 0,
            "top_products": [], "all_candidates": [],
            "pool_truncated": False, "counters": {},
        }

    n_atoms = mol.GetNumAtoms()
    atom_probs = _G_MPNN.get(smi, [])

    counters: dict[str, int] = Counter()
    cands_a = _run_engine_a(mol, atom_probs, n_atoms, counters)
    cands_b = _run_engine_b(mol, atom_probs, n_atoms, counters)

    n_a = len(cands_a)
    n_b = len(cands_b)
    pf = counters.get("parent_filtered_a", 0) + counters.get("parent_filtered_b", 0)

    ranked = _merge_cands(cands_a, cands_b, counters)
    n_union = len(ranked)

    # pool cap
    pool_truncated = False
    pool = ranked
    if len(ranked) > POOL_CAP:
        pool = ranked[:POOL_CAP]
        pool_truncated = True

    top = ranked[:TOP_K]

    def _serialize(c: dict) -> dict:
        return {
            "product_smiles": c["product_smiles"],
            "product_smiles_full": c["product_smiles_full"],
            "source": c["source"],
            "rule_ids": c["rule_ids"],
            "template_freq": c["template_freq"],
            "reactions_count": c["reactions_count"],
            "pattern_atom_count": c["pattern_atom_count"],
            "mpnn_site_mean": round(c["mpnn_site_mean"], 6),
            "mpnn_site_max": round(c["mpnn_site_max"], 6),
            "score": round(c["score"], 6),
            "site_atoms": c["site_atoms"],
        }

    return {
        "case_id": case_id,
        "smiles": smi,
        "n_atoms": n_atoms,
        "n_cand_uspto": n_a,
        "n_cand_envipath": n_b,
        "n_cand_union": n_union,
        "parent_filtered": pf,
        "top_products": [_serialize(c) for c in top],
        "all_candidates": [_serialize(c) for c in pool],
        "pool_truncated": pool_truncated,
        "counters": dict(counters),
    }


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--blind", required=True, help="blind CSV (93 parents)")
    ap.add_argument("--mpnn", required=True, help="MPNN predictions jsonl")
    ap.add_argument("--templates", required=True, help="USPTO templates.json")
    ap.add_argument("--envipath-rules", required=True,
                    help="templates_implicitH.jsonl (286 re-encoded rules)")
    ap.add_argument("--envipath-tsv", required=True,
                    help="enviPath templates.tsv.gz (for REACTIONS_COUNT)")
    ap.add_argument("--out-preds", required=True, help="output predictions jsonl")
    ap.add_argument("--out-pool", required=True, help="output pool jsonl")
    ap.add_argument("--out-report", required=True, help="output run report json")
    ap.add_argument("--limit", type=int, default=0, help="limit N cases (0=all)")
    ap.add_argument("--procs", type=int,
                    default=min(8, os.cpu_count() or 4), help="number of processes")
    args = ap.parse_args()

    t_start = time.time()

    # ---- load MPNN predictions ----
    print("loading MPNN predictions...", flush=True)
    mpnn = {}
    with open(args.mpnn) as f:
        for line in f:
            r = json.loads(line)
            mpnn[r["smiles"]] = r["atom_probs"]
    print(f"  {len(mpnn)} substrates", flush=True)

    # ---- parse USPTO templates (parent process, once) ----
    print("parsing USPTO templates...", flush=True)
    tpl_a = _parse_templates_a(args.templates)
    print(f"  {len(tpl_a)} templates parsed", flush=True)

    # ---- load enviPath rules ----
    print("loading enviPath rules...", flush=True)
    rules_b, skip_multi_global = _load_envipath_rules(args.envipath_rules,
                                                       args.envipath_tsv)
    print(f"  {len(rules_b)} rules loaded "
          f"({skip_multi_global} skipped multi-fragment/unparseable)", flush=True)

    # ---- load blind CSV ----
    with open(args.blind, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if args.limit > 0:
        rows = rows[:args.limit]
    print(f"  {len(rows)} cases to process", flush=True)

    # ---- set globals for fork workers ----
    global _G_TPL_A, _G_RULES_B, _G_MPNN
    _G_TPL_A = tpl_a
    _G_RULES_B = rules_b
    _G_MPNN = mpnn

    # ---- run (multiprocessing or single-process for --limit) ----
    if args.limit > 0 and args.limit <= 5:
        # single-process for debugging (easier tracebacks)
        results = [_process_case(r) for r in rows]
    else:
        ctx = mp.get_context("fork")
        with ctx.Pool(args.procs) as pool:
            results = pool.map(_process_case, rows, chunksize=1)

    # ---- sort by case_id (deterministic) ----
    results.sort(key=lambda r: r["case_id"])

    # ---- write predictions + pool ----
    with open(args.out_preds, "w") as f:
        for r in results:
            out = {k: v for k, v in r.items()
                   if k not in ("all_candidates", "counters")}
            f.write(json.dumps(out, ensure_ascii=False) + "\n")

    with open(args.out_pool, "w") as f:
        for r in results:
            out = {k: v for k, v in r.items()
                   if k not in ("top_products", "counters")}
            f.write(json.dumps(out, ensure_ascii=False) + "\n")

    # ---- run report ----
    total_cands_a = sum(r.get("n_cand_uspto", 0) for r in results)
    total_cands_b = sum(r.get("n_cand_envipath", 0) for r in results)
    total_union = sum(r.get("n_cand_union", 0) for r in results)
    total_pf = sum(r.get("parent_filtered", 0) for r in results)

    # aggregate all counters
    agg_counters: dict[str, int] = Counter()
    for r in results:
        for k, v in r.get("counters", {}).items():
            agg_counters[k] += v

    report = {
        "run_params": {
            "blind_csv": args.blind,
            "mpnn_preds": args.mpnn,
            "templates": args.templates,
            "envipath_rules": args.envipath_rules,
            "envipath_tsv": args.envipath_tsv,
            "limit": args.limit,
            "procs": args.procs,
            "rxn_budget": RXN_BUDGET,
            "pool_cap": POOL_CAP,
            "top_k": TOP_K,
        },
        "n_cases": len(results),
        "total_time_s": round(time.time() - t_start, 2),
        "n_templates_uspto": len(tpl_a),
        "n_rules_envipath": len(rules_b),
        "skip_multi_fragment_global": skip_multi_global,
        "candidate_counts": {
            "total_uspto": total_cands_a,
            "total_envipath": total_cands_b,
            "total_union": total_union,
            "total_parent_filtered": total_pf,
            "mean_uspto": round(total_cands_a / max(len(results), 1), 1),
            "mean_envipath": round(total_cands_b / max(len(results), 1), 1),
            "mean_union": round(total_union / max(len(results), 1), 1),
        },
        "skip_counters": dict(sorted(agg_counters.items())),
        "cases_with_zero_candidates": [
            r["case_id"] for r in results if r.get("n_cand_union", 0) == 0
        ],
        "pool_truncated_cases": [
            r["case_id"] for r in results if r.get("pool_truncated")
        ],
    }
    with open(args.out_report, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"DONE: {len(results)} cases, {total_union} total candidates "
          f"({total_cands_a} uspto + {total_cands_b} envipath), "
          f"{total_pf} parent-filtered, {time.time() - t_start:.1f}s", flush=True)
    print(f"  predictions → {args.out_preds}", flush=True)
    print(f"  pool        → {args.out_pool}", flush=True)
    print(f"  report      → {args.out_report}", flush=True)
    zero = report["cases_with_zero_candidates"]
    if zero:
        print(f"  zero-candidate cases: {zero}", flush=True)


if __name__ == "__main__":
    main()
