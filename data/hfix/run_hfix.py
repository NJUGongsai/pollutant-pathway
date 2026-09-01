#!/usr/bin/env python3
"""M4-A orchestrator: re-encode enviPath explicit-H templates to implicit H and
emit every deliverable under data/hfix/.

Produces (deterministic, sorted output):
  templates_implicitH.jsonl   - 286 re-encoded rules (+metadata)
  match_report.json           - matching unlock before/after (donor + cross-parent)
  roundtrip_report.json       - round-trip canary classification
  candidates_hfix.json        - re-encoded rules on 83 parents, union old RA-M1 pool
  MANIFEST.sha256             - sha256 of the 4 artifacts above

Answer-key isolation: this pipeline NEVER reads the restricted answer key or
route_a_audit/recall.py. It only reads reaction_v3 (templates + sidecar),
demov3 (blind parents), and reaction_analogy/data/retrieval_v1 (old candidate pool).

Determinism: all Python set/dict output is sorted; run twice -> byte-identical.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import sys

from rdkit import Chem
from rdkit.Chem import AllChem
from rdkit import RDLogger

RDLogger.DisableLog("rdApp.*")

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from reencode import (  # noqa: E402
    TSV_PATH, SUBSTRATE_PATH, load_templates, load_substrates,
    reencode_smirks, apply_rule, apply_rule_explicit_ref, reactant_matches,
)

ROOT = "/Volumes/CC/Enzyme_Agent/depending"
PARENTS = os.path.join(ROOT, "demov3/data/bbd83_blind_inputs/"
                       "KNOWN_PATHWAY_POLLUTANT_BLIND_PARENT_INPUTS_V0_2.csv")
OLD_POOL = os.path.join(ROOT, "reaction_analogy/data/retrieval_v1/queries.jsonl")


def canon(smiles: str) -> str | None:
    m = Chem.MolFromSmiles(smiles)
    return Chem.MolToSmiles(m) if m is not None else None


def load_parents(path: str = PARENTS) -> dict:
    out = {}
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            out[row["benchmark_case_id"]] = row["parent_smiles"]
    return out


def load_old_pool(path: str = OLD_POOL) -> dict:
    out = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            if "case_id" in d and "candidates" in d:
                out[d["case_id"]] = d["candidates"]
    return out


def sha256_of_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    templates = load_templates()
    substrates = load_substrates()
    parents = load_parents()
    old_pool = load_old_pool()

    # ---- 1) re-encode all 286 --------------------------------------------
    encoded = {}
    for d in sorted(templates, key=lambda x: x["TEMPLATE_ID"]):
        tid = d["TEMPLATE_ID"]
        new_smirk, info = reencode_smirks(d["TEMPLATE"])
        encoded[tid] = {
            "template_id": tid,
            "original_smirks": d["TEMPLATE"],
            "reencoded_smirks": new_smirk,
            "changed": info["changed"],
            "lhs_explicit_h": info["lhs_h"],
            "rhs_explicit_h": info["rhs_h"],
            "lhs_mapped_h": info["lhs_mapped_h"],
            "rhs_mapped_h": info["rhs_mapped_h"],
            "parse_ok": info["parse_ok"],
        }

    with open(os.path.join(HERE, "templates_implicitH.jsonl"), "w",
              encoding="utf-8") as f:
        for tid in sorted(encoded):
            f.write(json.dumps(encoded[tid], ensure_ascii=True) + "\n")

    # ---- 2) match_report --------------------------------------------------
    n_changed = sum(1 for e in encoded.values() if e["changed"])
    donor_ids = sorted(t for t, e in encoded.items()
                       if substrates.get(t, {}).get("substrates"))

    match_before, match_after = [], []
    for tid in sorted(encoded):
        donors = substrates.get(tid, {}).get("substrates", [])
        if not donors:
            continue
        r_orig = AllChem.ReactionFromSmarts(encoded[tid]["original_smirks"])
        r_enc = AllChem.ReactionFromSmarts(encoded[tid]["reencoded_smirks"])
        b = any(reactant_matches(r_orig, s) for s in donors)
        a = any(reactant_matches(r_enc, s) for s in donors)
        if b:
            match_before.append(tid)
        if a:
            match_after.append(tid)

    not_after = [tid for tid in donor_ids if tid not in match_after]

    def match_parents(smirks: str) -> set:
        out = set()
        r = AllChem.ReactionFromSmarts(smirks)
        if r is None:
            return out
        pat = r.GetReactants()[0]
        for cid, smi in parents.items():
            m = Chem.MolFromSmiles(smi)
            if m is not None and m.HasSubstructMatch(pat):
                out.add(cid)
        return out

    cross_before = {}
    cross_after = {}
    for tid in sorted(encoded):
        b = match_parents(encoded[tid]["original_smirks"])
        a = match_parents(encoded[tid]["reencoded_smirks"])
        cross_before[tid] = sorted(b)
        cross_after[tid] = sorted(a)

    match_report = {
        "total_templates": len(templates),
        "changed_templates": n_changed,
        "unchanged_templates": len(templates) - n_changed,
        "rules_with_donor": len(donor_ids),
        "rules_matching_any_donor_before": len(match_before),
        "rules_matching_any_donor_after": len(match_after),
        "rules_matching_any_donor_delta": len(match_after) - len(match_before),
        "match_before_ids": match_before,
        "match_after_ids": match_after,
        "rules_still_not_matching_donor": not_after,
        "cross_parent_rules_matching_before": sum(
            1 for t in cross_before if cross_before[t]),
        "cross_parent_rules_matching_after": sum(
            1 for t in cross_after if cross_after[t]),
        "cross_parent_cases_matched_before": len(
            {p for t in cross_before for p in cross_before[t]}),
        "cross_parent_cases_matched_after": len(
            {p for t in cross_after for p in cross_after[t]}),
        "parents": len(parents),
    }

    # ---- 3) roundtrip_report ---------------------------------------------
    def residual_h_query(smarts: str) -> bool:
        """Does the re-encoded reactant STILL carry a hydrogen query that the
        top-level H-strip does not remove: a `[#1,...]` list element or an
        explicit `[H]` inside a recursive `$(...)`? These cannot match an
        implicit-H molecule and are a SEPARATE latent issue."""
        react = smarts.split(">>")[0]
        if re.search(r"#1(?=[,\]])", react):
            return True
        if re.search(r"\[H(?::\d+)?\]", react):
            return True
        return False

    pair_cats = {"ok": 0, "ok_extra": 0, "orig_no_match": 0,
                 "residual_H_query": 0, "reencode_gen_failure": 0}
    pair_rows = []
    for tid in sorted(encoded):
        donors = substrates.get(tid, {}).get("substrates", [])
        if not donors:
            pair_rows.append({"template_id": tid, "verdict": "no_donor",
                              "changed": encoded[tid]["changed"]})
            continue
        r_orig = AllChem.ReactionFromSmarts(encoded[tid]["original_smirks"])
        r_enc = AllChem.ReactionFromSmarts(encoded[tid]["reencoded_smirks"])
        residual = residual_h_query(encoded[tid]["reencoded_smirks"])
        for s in donors:
            ref = sorted(apply_rule_explicit_ref(r_orig, s))
            enc = sorted(apply_rule(r_enc, s))
            if not ref:
                verdict = "orig_no_match"
                pair_cats["orig_no_match"] += 1
            elif not enc and residual:
                verdict = "residual_H_query"
                pair_cats["residual_H_query"] += 1
            elif not enc:
                verdict = "reencode_gen_failure"
                pair_cats["reencode_gen_failure"] += 1
            else:
                missing = [p for p in ref if p not in set(enc)]
                if missing:
                    verdict = "reencode_gen_failure"
                    pair_cats["reencode_gen_failure"] += 1
                elif any(p not in set(ref) for p in enc):
                    verdict = "ok_extra"
                    pair_cats["ok_extra"] += 1
                else:
                    verdict = "ok"
                    pair_cats["ok"] += 1
            pair_rows.append({"template_id": tid, "donor": s,
                              "verdict": verdict,
                              "changed": encoded[tid]["changed"],
                              "residual_h_query": residual})

    # rule-level summary of every non-OK verdict
    from collections import Counter, defaultdict
    rule_issues = defaultdict(lambda: {"pairs": 0, "donors": []})
    for r in pair_rows:
        if r.get("verdict") in ("orig_no_match", "residual_H_query",
                                "reencode_gen_failure"):
            rule_issues[r["template_id"]]["pairs"] += 1
            rule_issues[r["template_id"]]["donors"].append(r.get("donor"))
    rule_issue_summary = {
        tid: {"pairs": v["pairs"], "donors": v["donors"],
              "lhs_mapped_h": encoded[tid]["lhs_mapped_h"],
              "rhs_mapped_h": encoded[tid]["rhs_mapped_h"]}
        for tid, v in sorted(rule_issues.items())
    }

    n_checked = pair_cats["ok"] + pair_cats["ok_extra"] + \
        pair_cats["residual_H_query"] + pair_cats["reencode_gen_failure"]
    roundtrip_report = {
        "method": ("reference = original SMIRKS applied to AddHs(donor) then "
                   "RemoveHs+canonical; candidate = re-encoded SMIRKS applied "
                   "to implicit donor; fidelity = reference products are a "
                   "subset of candidate products (no loss)."),
        "pair_counts": pair_cats,
        "pairs_checked": n_checked,
        "fidelity_rate_checked": \
            round((pair_cats["ok"] + pair_cats["ok_extra"]) / n_checked, 4)
            if n_checked else None,
        "known_limitations": [
            "orig_no_match: original rule cannot match even the explicitly-"
            "hydrogenated donor (pre-existing aromatic/kekule, charge, or "
            "chain-length impedance; unaffected by re-encoding).",
            "residual_H_query: reactant still holds a [#1,...] list element or "
            "a recursive $(...[H]) query that the H-node strip does not remove; "
            "these cannot match implicit H (separate latent issue, out of scope "
            "for the H-node re-encoding).",
            "reencode_gen_failure: minority of rules lose a product or fail "
            "product generation (RDKit RunReactants implicit-H/chiral-stereo "
            "interaction at the reaction center, and mapped-H hydrogen-transfer "
            "semantics needing explicit Hn-equivalence). Failed products are "
            "dropped (fail-closed), never emitted with wrong valence.",
        ],
        "per_pair": pair_rows,
        "rules_with_issues": rule_issue_summary,
    }

    # ---- 4) candidates_hfix.json -----------------------------------------
    # products of all 286 re-encoded rules on the 83 parents, union old pool.
    rxns = {}
    for tid in sorted(encoded):
        r = AllChem.ReactionFromSmarts(encoded[tid]["reencoded_smirks"])
        if r is not None and r.GetNumReactantTemplates() == 1:
            rxns[tid] = r

    candidates = {}
    for cid in sorted(parents):
        xs = canon(parents[cid])
        prods = set()
        if xs:
            for tid in sorted(rxns):
                try:
                    prods |= apply_rule(rxns[tid], xs)
                except Exception:
                    pass
        # union old RA-M1 pool
        for s in old_pool.get(cid, []):
            c = canon(s)
            if c:
                prods.add(c)
        candidates[cid] = sorted(prods)

    with open(os.path.join(HERE, "candidates_hfix.json"), "w",
              encoding="utf-8") as f:
        json.dump(candidates, f, ensure_ascii=True, sort_keys=True, indent=0)

    # ---- 5) write the three reports --------------------------------------
    with open(os.path.join(HERE, "match_report.json"), "w", encoding="utf-8") as f:
        json.dump(match_report, f, ensure_ascii=True, sort_keys=True, indent=1)
    with open(os.path.join(HERE, "roundtrip_report.json"), "w",
              encoding="utf-8") as f:
        json.dump(roundtrip_report, f, ensure_ascii=True, sort_keys=True, indent=1)

    # ---- 6) MANIFEST.sha256 ----------------------------------------------
    # hash every file in data/hfix (data + code + test + README), following the
    # repo's regenerate_manifest.py convention (hash-of-hashes, self-excluded).
    here_files = [n for n in sorted(os.listdir(HERE))
                  if os.path.isfile(os.path.join(HERE, n))
                  and n not in ("MANIFEST.sha256",)]
    lines = sorted(f"{sha256_of_file(os.path.join(HERE, n))}  {n}\n"
                   for n in here_files)
    content = "".join(lines)
    lines.append(f"{hashlib.sha256(content.encode()).hexdigest()}  "
                 "MANIFEST.sha256\n")
    with open(os.path.join(HERE, "MANIFEST.sha256"), "w", encoding="utf-8") as f:
        f.writelines(lines)

    # ---- summary to stdout -----------------------------------------------
    print("templates:", len(templates), " changed:", n_changed)
    print("donor match before/after:", len(match_before), "->", len(match_after),
          f"(of {len(donor_ids)} rules with donors)")
    print("cross-parent rules matching before/after:",
          match_report["cross_parent_rules_matching_before"], "->",
          match_report["cross_parent_rules_matching_after"],
          f"(of {len(templates)})")
    print("roundtrip pair_counts:", pair_cats)
    print("candidates cases:", len(candidates),
          " total candidates:",
          sum(len(v) for v in candidates.values()))
    print("MANIFEST:")
    for ln in lines:
        print("  " + ln.strip())


if __name__ == "__main__":
    main()