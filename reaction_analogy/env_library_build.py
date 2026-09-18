#!/usr/bin/env python3
"""Build the expanded environmental lookup library + retrieval corpus
(soil/sludge repair round 2, 2026-09-18).

Inputs:
  reaction_analogy/data/bbd_expand/donor_product.jsonl   EAWAG-BBD (859 donors)
  reaction_analogy/data/env_expand/env_reactions.jsonl   enviPath
    EAWAG-SOIL / EAWAG-SLUDGE / EAWAG-SEDIMENT crawled pairs

Outputs (data/env_expand/ + data/corpus_env*/):
  library_full.jsonl     deployment lookup library (all packages) —
                         donor_product.jsonl schema (donor_smiles,
                         product_smiles, btid, reac_id + provenance fields),
                         directly loadable by eawag_lookup.build_index
  library_eval.jsonl     same minus the HELD-OUT parents' reactions
  holdout_parents.json   the held-out parent list (20% of unique
                         SOIL/SLUDGE educt parents, deterministic hash split)
  holdout_truth.jsonl    {parent, accepted_products} for local honest eval

  data/corpus_env/       retrieval corpus for DEPLOYMENT =
                         corpus_v1 + env records (all packages)
  data/corpus_env_eval/  retrieval corpus for LOCAL EVAL =
                         corpus_v1 + env records minus held-out parents

Split discipline: held-out parents are chosen by sha1(parent identity) mod 5
== 0 (deterministic, no tuning); ALL reactions of a held-out parent are
excluded from library_eval and corpus_env_eval so the honest-generalization
eval cannot see them via lookup OR retrieval.  soil/sludge gold of the
colleague is never read (not present locally).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections import defaultdict

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

from rdkit import Chem, RDLogger  # noqa: E402
RDLogger.DisableLog("rdApp.*")

import bbd_v33_fusion as V33  # noqa: E402

ROOT = "/Volumes/CC/Enzyme_Agent/depending"
BBD_DONOR = os.path.join(_HERE, "data/bbd_expand/donor_product.jsonl")
ENV_REACTIONS = os.path.join(_HERE, "data/env_expand/env_reactions.jsonl")
ENV_OUT = os.path.join(_HERE, "data/env_expand")
CORPUS_SRC = os.path.join(_HERE, "data/corpus_v1")


def sb(smi: str) -> str | None:
    m = Chem.MolFromSmiles(smi)
    return Chem.MolToSmiles(m, isomericSmiles=False) if m is not None else None


def cn_id(smi: str) -> str | None:
    norm = V33.normalize_charge_smiles(smi)
    return sb(norm) if norm else sb(smi)


def first_gen_products(env_rows):
    """Per-parent FIRST-GENERATION products (mirrors the colleague's
    ``strict_single_parent_single_product_first_generation`` curation):
    for each pathway, roots = educts never produced inside the pathway;
    a parent's first-gen products = products of its reactions where the
    parent is a root of that pathway.  Returns {parent_id: set(product_sb)}.
    Also returns all_products {parent_id: set(product_sb)} (any depth)."""
    # per pathway: educts, products, edges
    pw_educts: dict[str, set[str]] = defaultdict(set)
    pw_products: dict[str, set[str]] = defaultdict(set)
    pw_edges: dict[str, list] = defaultdict(list)
    for r in env_rows:
        pid = cn_id(r["educt_smiles"])
        psb = sb(r["product_smiles"])
        if pid is None or psb is None:
            continue
        pw = (r["package"], r["pathway_id"])
        pw_educts[pw].add(pid)
        pw_products[pw].add(psb)
        pw_edges[pw].append((pid, psb))
    fg: dict[str, set[str]] = defaultdict(set)
    allp: dict[str, set[str]] = defaultdict(set)
    root_status: set[str] = set()
    for pw, edges in pw_edges.items():
        roots = pw_educts[pw] - pw_products[pw]
        root_status |= roots
        for pid, psb in edges:
            allp[pid].add(psb)
            if pid in roots:
                fg[pid].add(psb)
    # parents with no root-status anywhere (pure intermediates): fall back
    # to all products so they remain evaluable (flagged is_root_parent=False)
    for pid, prods in allp.items():
        if pid not in fg:
            fg[pid] = set(prods)
    return fg, allp, root_status


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--holdout-mod", type=int, default=5,
                    help="hold out parents with sha1 % mod == 0")
    args = ap.parse_args()

    # ---- 1. load pairs ----
    pairs = []  # (donor_smiles, product_smiles, package, pathway, reaction)
    with open(BBD_DONOR) as f:
        for line in f:
            r = json.loads(line)
            pairs.append((r["donor_smiles"], r["product_smiles"],
                          "EAWAG-BBD", r.get("btid", ""), r.get("reac_id", "")))
    n_bbd = len(pairs)
    with open(ENV_REACTIONS) as f:
        for line in f:
            r = json.loads(line)
            pairs.append((r["educt_smiles"], r["product_smiles"],
                          r["package"], r["pathway_id"], r["reaction_id"]))
    print(f"pairs: {n_bbd} EAWAG-BBD + {len(pairs)-n_bbd} enviPath "
          f"= {len(pairs)}", flush=True)

    # ---- 2. unique parents (soil/sludge only for the holdout split) ----
    parent_ids = {}   # parent identity -> raw parent smiles
    for d, p, pkg, pw, rid in pairs:
        if pkg not in ("EAWAG-SOIL", "EAWAG-SLUDGE"):
            continue
        pid = cn_id(d)
        if pid and pid not in parent_ids:
            parent_ids[pid] = d
    held = {pid for pid in parent_ids
            if int(hashlib.sha1(pid.encode()).hexdigest(), 16) % args.holdout_mod == 0}
    print(f"unique soil/sludge parents: {len(parent_ids)}, held out: "
          f"{len(held)}", flush=True)

    # ---- 3. write libraries (dedup by (donor_id, product sb)) ----
    seen = set()
    n_full = n_eval = 0
    with open(os.path.join(ENV_OUT, "library_full.jsonl"), "w") as ff, \
            open(os.path.join(ENV_OUT, "library_eval.jsonl"), "w") as fe:
        for d, p, pkg, pw, rid in pairs:
            did, psb = cn_id(d), sb(p)
            if did is None or psb is None:
                continue
            key = (did, psb)
            if key in seen:
                continue
            seen.add(key)
            row = {
                "donor_smiles": d, "product_smiles": p,
                "btid": f"{pkg}:{pw}" if pkg != "EAWAG-BBD" else pw,
                "reac_id": rid, "package": pkg,
                "donor_id": did, "product_sb": psb,
            }
            ff.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
            n_full += 1
            if did not in held:
                fe.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
                n_eval += 1
    print(f"library_full rows: {n_full}, library_eval rows: {n_eval}",
          flush=True)

    # ---- 4. holdout truth (first-generation caliber, see
    #         first_gen_products docstring) ----
    env_rows = [json.loads(line) for line in open(ENV_REACTIONS)]
    fg, allp, root_status = first_gen_products(env_rows)
    with open(os.path.join(ENV_OUT, "holdout_truth.jsonl"), "w") as f:
        for pid in sorted(held):
            prods = fg.get(pid) or allp.get(pid)
            if not prods:
                continue
            f.write(json.dumps({
                "parent": parent_ids.get(pid, pid),
                "parent_id": pid,
                "is_root_parent": pid in root_status,
                "accepted_products_sb": sorted(prods),
                "all_products_sb": sorted(allp.get(pid, prods))},
                ensure_ascii=False, sort_keys=True) + "\n")
    with open(os.path.join(ENV_OUT, "holdout_parents.json"), "w") as f:
        json.dump({"n_held": len(held), "holdout_mod": args.holdout_mod,
                   "parents": sorted(held)}, f, indent=1)
    # full first-gen truth (all parents — for the library-covered caliber B)
    with open(os.path.join(ENV_OUT, "first_gen_truth_all.jsonl"), "w") as f:
        for pid in sorted(fg):
            f.write(json.dumps({
                "parent_id": pid,
                "is_root_parent": pid in root_status,
                "accepted_products_sb": sorted(fg[pid]),
                "all_products_sb": sorted(allp.get(pid, fg[pid]))},
                ensure_ascii=False, sort_keys=True) + "\n")
    n_truth = sum(1 for pid in held if fg.get(pid) or allp.get(pid))
    print(f"holdout truth (first-gen): {n_truth} parents; "
          f"first-gen truth rows: {len(fg)}", flush=True)

    # ---- 5. retrieval corpus variants (corpus_v1 + env packages + BBD) ----
    all_recs = []  # (educt, product, package, record_id, source_id, ec)
    for r in env_rows:
        did = cn_id(r["educt_smiles"])
        if did is None:
            continue
        all_recs.append((r["educt_smiles"], r["product_smiles"],
                         r["package"],
                         f"env:{r['package']}:{r['reaction_id']}",
                         r["pathway_id"],
                         (r.get("ec_numbers") or [None])[0]))
    with open(BBD_DONOR) as f:
        for line in f:
            r = json.loads(line)
            did = cn_id(r["donor_smiles"])
            if did is None or sb(r["product_smiles"]) is None:
                continue
            all_recs.append((r["donor_smiles"], r["product_smiles"],
                             "EAWAG-BBD",
                             f"env:EAWAG-BBD:{r.get('btid','')}#"
                             f"{r.get('reac_id','')}",
                             r.get("btid", ""), None))
    print(f"corpus source records: {len(all_recs)} "
          f"(enviPath packages + EAWAG-BBD)", flush=True)

    for out_dir, exclude_held in (("corpus_env", False),
                                   ("corpus_env_eval", True)):
        out_dir = os.path.join(_HERE, "data", out_dir)
        os.makedirs(out_dir, exist_ok=True)
        n_env = 0
        with open(os.path.join(CORPUS_SRC, "corpus_v1.jsonl")) as src, \
                open(os.path.join(out_dir, "corpus_v1.jsonl"), "w") as dst:
            for line in src:
                dst.write(line)
            for e_smiles, p_smiles, pkg, rec_id, src_id, ec in all_recs:
                did = cn_id(e_smiles)
                if did is None:
                    continue
                if exclude_held and did in held:
                    continue
                rec = {
                    "atom_mapping": None, "direction": None,
                    "donor_A_smiles": e_smiles,
                    "donor_components": [e_smiles],
                    "ec": ec,
                    "mapping_status": "absent",
                    "master_id": None,
                    "parse_note": f"envipath-{pkg.lower()}",
                    "product_B_smiles": p_smiles,
                    "product_components": [p_smiles],
                    "provenance_sha256": None,
                    "reaction_smiles": None,
                    "record_id": rec_id,
                    "source_id": src_id,
                    "source_type": "envipath",
                }
                dst.write(json.dumps(rec, ensure_ascii=False,
                                     sort_keys=True) + "\n")
                n_env += 1
        # donor index: original + env/BBD donors
        n_env_di = 0
        with open(os.path.join(CORPUS_SRC, "donor_index.jsonl")) as src, \
                open(os.path.join(out_dir, "donor_index.jsonl"), "w") as dst:
            for line in src:
                dst.write(line)
            seen_di = set()
            for e_smiles, p_smiles, pkg, rec_id, src_id, ec in all_recs:
                did = cn_id(e_smiles)
                if did is None:
                    continue
                if exclude_held and did in held:
                    continue
                key = (did, rec_id)
                if key in seen_di:
                    continue
                seen_di.add(key)
                dst.write(json.dumps({
                    "donor_smiles": e_smiles,
                    "donor_id": did,
                    "donor_record_id": rec_id,
                    "source_type": "envipath",
                    "package": pkg},
                    ensure_ascii=False, sort_keys=True) + "\n")
                n_env_di += 1
        print(f"{out_dir}: +{n_env} corpus records, +{n_env_di} donor index",
              flush=True)
    print("DONE", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
