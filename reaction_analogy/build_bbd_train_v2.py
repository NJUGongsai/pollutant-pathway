#!/usr/bin/env python3
"""BBD v5 training-set builder: merge RHEA cache + EAWAG-donor candidates.

Task §4.1 (component A).  Produces the mixed RHEA+EAWAG training cache
``data/bbd_v5/train_candidates_v5.jsonl`` and the EAWAG leak list.

  RHEA part: reuse ``data/bbd_v31/train_candidates.jsonl`` (1.88M rows) AS-IS
             (no re-run of candidate generation) — tagged is_eawag_domain=0.
  EAWAG part (879 reactions / 775 donors after leak filter):
      educt = donor (stereo-blind canonical; the 84 blind-parent donors are
              removed — RED LINE 1, §5.1),
      candidate generation = the SAME three engines as
              ``train_bbd_v31_ranker._process_educt_raw`` (engine A USPTO
              top-2k templates + engine B enviPath 286 rules AND the 49 EAWAG
              rules + engine C retrieval), by setting the shared T3 globals
              and extending ``_G_RULES_B`` with the EAWAG rules,
      label = candidate stereo-blind canonical ∈ that donor's true products,
      is_eawag_domain = 1.

EAWAG-rule candidates are emitted with source="envipath" (the engine-B block
in _process_educt_raw sets source="envipath"), so they fold into the envipath
per-source ranker via the existing substring routing — unchanged matching
logic. rule_family provenance is a predict-time concern only (set by
eawag_rules_engine.apply_eawag_rules), not needed at training time.

Determinism: RHEA rows streamed in file order; EAWAG donors processed in
sorted order via pool.map (preserves input order); candidates written with
sort_keys=True. Double-run byte-diff is asserted by Phase 4.

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

import multiprocessing as mp

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(_HERE, "src"))

from rdkit import Chem, RDLogger  # noqa: E402
RDLogger.DisableLog("rdApp.*")

import train_bbd_v3_ranker as T3  # noqa: E402 — pipeline + globals
import train_bbd_v31_ranker as T31  # noqa: E402 — _process_educt_raw + _init_worker
import predict_bbd_products_v2 as P2  # noqa: E402 — _load_envipath_rules
import eawag_rules_engine as ERE  # noqa: E402 — load_eawag_rules
import io_retry as IOR  # noqa: E402 — robust I/O for flaky external drive

ROOT = "/Volumes/CC/Enzyme_Agent/depending"
OUT_DIR = os.path.join(ROOT, "data/bbd_v5")
RHEA_CACHE = os.path.join(ROOT, "data/bbd_v31/train_candidates.jsonl")
DONOR_PRODUCT = os.path.join(ROOT,
    "reaction_analogy/data/bbd_expand/donor_product.jsonl")
EAWAG_RULES = os.path.join(ROOT,
    "reaction_analogy/data/bbd_expand/rules_new_clean.jsonl")
BLIND_CSV = os.path.join(ROOT,
    "bbd_known_pathway_full_route_v0_3_candidate_v3_1_strict_blind_fix_20260821/blind/"
    "BBD_KNOWN_PATHWAY_FULL_ROUTE_V0_3_V3_1_BLIND_PARENT_INPUTS_FOR_PREDICTION_STRICT.csv")
V3_MODEL = os.path.join(ROOT, "data/bbd_v3/ranker_model.txt")


def _sb(smi: str) -> str | None:
    m = Chem.MolFromSmiles(smi)
    return Chem.MolToSmiles(m, isomericSmiles=False) if m is not None else None


def load_eawag_educts(donor_product_path: str, blind_parents: set[str]):
    """Build EAWAG educt dicts from donor_product.jsonl, dropping blind parents.

    Returns (educts, leak_donors, stats) where educts is a sorted list of
    {educt_sb, true_products_sb: set} and leak_donors is the set of
    blind-parent EAWAG donors removed (RED LINE 1).
    """
    donor_map: dict[str, set[str]] = {}
    n_rxn = 0
    with open(donor_product_path) as f:
        for line in f:
            r = json.loads(line)
            n_rxn += 1
            d = _sb(r.get("donor_smiles", ""))
            p = _sb(r.get("product_smiles", ""))
            if not d or not p:
                continue
            donor_map.setdefault(d, set()).add(p)
    all_donors = set(donor_map)
    leak_donors = all_donors & blind_parents
    kept_donors = all_donors - leak_donors
    educts = [{"educt_sb": d, "true_products_sb": donor_map[d]}
              for d in sorted(kept_donors)]
    n_rxn_kept = sum(len(donor_map[d]) for d in kept_donors)
    stats = {
        "n_reactions_total": n_rxn,
        "n_donors_total": len(all_donors),
        "n_blind_leak_donors": len(leak_donors),
        "n_donors_kept": len(kept_donors),
        "n_reactions_kept": n_rxn_kept,
    }
    return educts, sorted(leak_donors), stats


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--corpus-dir", default=T3.CORPUS_DIR)
    ap.add_argument("--templates", default=T3.USPTO_TEMPLATES)
    ap.add_argument("--envipath-rules", default=T3.ENVIPATH_RULES)
    ap.add_argument("--envipath-tsv", default=T3.ENVIPATH_TSV)
    ap.add_argument("--eawag-rules", default=EAWAG_RULES)
    ap.add_argument("--donor-product", default=DONOR_PRODUCT)
    ap.add_argument("--blind-csv", default=BLIND_CSV)
    ap.add_argument("--v3-model", default=V3_MODEL)
    ap.add_argument("--rhea-cache", default=RHEA_CACHE)
    ap.add_argument("--top-n", type=int, default=T3.TRAIN_TOP_N)
    ap.add_argument("--procs", type=int, default=min(8, os.cpu_count() or 4))
    ap.add_argument("--out-dir", default=OUT_DIR)
    ap.add_argument("--limit", type=int, default=0,
                    help="limit EAWAG educts (debug)")
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    t0 = time.time()

    # ---- blind parents (for leak filter + assert) ----
    blind_parents = T3.load_blind_parents(args.blind_csv)
    print(f"blind parents: {len(blind_parents)}", flush=True)

    # ---- EAWAG educts (leak-filtered) ----
    print("loading EAWAG donors + leak filter...", flush=True)
    educts, leak_donors, eawag_stats = load_eawag_educts(
        args.donor_product, blind_parents)
    print(f"  {eawag_stats}", flush=True)
    # RED LINE 1: EAWAG train educts ∩ blind == 0
    eawag_educt_sbs = {e["educt_sb"] for e in educts}
    assert not (eawag_educt_sbs & blind_parents), "LEAK: EAWAG educt ∩ blind"
    assert len(leak_donors) == 84, f"expected 84 leak donors, got {len(leak_donors)}"
    print(f"  leak filter passed: 84 donors removed, "
          f"{len(educts)} kept, 0 overlap", flush=True)

    if args.limit > 0:
        educts = educts[:args.limit]
        print(f"  limited to {len(educts)} EAWAG educts", flush=True)

    # ---- setup shared globals (engine A templates + engine B rules + retrieval) ----
    print(f"parsing USPTO top-{args.top_n} templates...", flush=True)
    tpl_a = T3.parse_top_templates(args.templates, args.top_n)
    rules_b_envipath, skip_env = P2._load_envipath_rules(
        args.envipath_rules, args.envipath_tsv)
    rules_b_eawag = ERE.load_eawag_rules(args.eawag_rules)
    rules_b = rules_b_envipath + rules_b_eawag
    print(f"  engine B: {len(rules_b_envipath)} envipath + "
          f"{len(rules_b_eawag)} eawag = {len(rules_b)} rules", flush=True)

    print("batch retrieval (EAWAG educts)...", flush=True)
    retrieval_results = T3.batch_retrieval(educts, args.corpus_dir)
    print(f"  retrieval for {len(retrieval_results)} educts", flush=True)

    # set globals for fork workers (T3.* used inside _process_educt_raw)
    T3._G_TPL_A = tpl_a
    T3._G_RULES_B = rules_b
    T3._G_RETRIEVAL = retrieval_results
    # _G_RECORDS set inside batch_retrieval

    # ---- generate EAWAG candidates (multiprocessing, reuse _process_educt_raw) ----
    print(f"generating EAWAG candidates ({args.procs} procs)...", flush=True)
    ctx = mp.get_context("fork")
    with ctx.Pool(args.procs, initializer=T31._init_worker,
                  initargs=(args.v3_model,)) as pool:
        results = pool.map(T31._process_educt_raw, educts, chunksize=10)

    # tag EAWAG candidates with is_eawag_domain=1
    eawag_cands = 0
    eawag_pos = 0
    for esb, cands in results:
        for c in cands:
            c["is_eawag_domain"] = 1
            eawag_cands += 1
            if c.get("label"):
                eawag_pos += 1
    print(f"  EAWAG: {eawag_cands} candidates ({eawag_pos} pos) in "
          f"{time.time()-t0:.0f}s", flush=True)

    # ---- write EAWAG-only candidate cache (small; ~tens of MB) ----
    # The 1 GB RHEA cache is NOT rewritten here — train_bbd_ranker_v2 reads the
    # existing data/bbd_v31/train_candidates.jsonl (is_eawag_domain=0 implicit)
    # and merges this EAWAG-only cache (is_eawag_domain=1) IN MEMORY. This
    # avoids any ~1 GB write to the flaky external /Volumes/CC drive, which
    # raises EIO/ENXIO under sustained large-file writes.
    print("writing EAWAG-only candidate cache...", flush=True)
    eawag_cache_path = os.path.join(args.out_dir, "eawag_candidates.jsonl")
    eawag_lines = [json.dumps(c, ensure_ascii=False, sort_keys=True) + "\n"
                   for esb, cands in results for c in cands]
    IOR.robust_writelines(eawag_cache_path, eawag_lines)
    print(f"  wrote {eawag_cands} EAWAG candidates ({eawag_pos} pos) to "
          f"{eawag_cache_path}", flush=True)

    total_rhea_rows = len(IOR.robust_readlines(args.rhea_cache))

    # ---- leak list + combined train_educts manifest ----
    # combined RHEA + EAWAG educt manifest (for predict-time leak assertion)
    rhea_te_path = os.path.join(ROOT, "data/bbd_v3/train_educts.json")
    rhea_educts = []
    if os.path.exists(rhea_te_path):
        rhea_educts = json.load(open(rhea_te_path))["train_educts_sb"]
    combined_educts = sorted(set(rhea_educts) | eawag_educt_sbs)
    te_path = os.path.join(args.out_dir, "train_educts_v5.json")
    IOR.robust_json_dump(te_path, {"train_educts_sb": combined_educts,
                                   "n_rhea": len(rhea_educts),
                                   "n_eawag": len(eawag_educt_sbs),
                                   "n_total": len(combined_educts)})
    # RED LINE 1 assert: combined train educts ∩ blind == 0
    assert not (set(combined_educts) & blind_parents), "LEAK: combined ∩ blind"
    print(f"  combined train educts: {len(combined_educts)} "
          f"({len(rhea_educts)} RHEA + {len(eawag_educt_sbs)} EAWAG), "
          f"0 overlap with blind", flush=True)

    leak_path = os.path.join(args.out_dir, "eawag_leak_list.json")
    IOR.robust_json_dump(leak_path, {"leak_donors_sb": leak_donors,
                                      "n_leak": len(leak_donors),
                                      "eawag_stats": eawag_stats})

    report = {
        "rhea_cache_rows": total_rhea_rows,
        "eawag_educts": len(educts),
        "eawag_candidates": eawag_cands,
        "eawag_positives": eawag_pos,
        "total_train_rows": total_rhea_rows + eawag_cands,
        "n_envipath_rules": len(rules_b_envipath),
        "n_eawag_rules": len(rules_b_eawag),
        "n_skip_envipath_multi": skip_env,
        "leak_donors_removed": len(leak_donors),
        "combined_train_educts": len(combined_educts),
        "total_time_s": round(time.time() - t0, 1),
    }
    with IOR.robust_open(os.path.join(args.out_dir, "build_train_v5_report.json"), "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"DONE: {eawag_cands} EAWAG candidates ({eawag_pos} pos); "
          f"RHEA cache {total_rhea_rows} rows reused in-memory by trainer; "
          f"{time.time()-t0:.0f}s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
