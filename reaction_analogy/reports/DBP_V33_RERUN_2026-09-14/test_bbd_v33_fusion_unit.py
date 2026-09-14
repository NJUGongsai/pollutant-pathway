#!/usr/bin/env python3
"""Unit tests for bbd_v33_fusion (DBP acceptance + generic chemistry sanity)."""
import sys, os
RA = "/Volumes/CC/Enzyme_Agent/depending/reaction_analogy"
sys.path.insert(0, RA)

from bbd_v33_fusion import (assess_skeleton_change, merge_charge_variants,
                            normalize_charge_smiles, fused_ns33, source_set)

fails = []
def check(name, cond, extra=""):
    status = "PASS" if cond else "FAIL"
    print(f"[{status}] {name} {extra}")
    if not cond:
        fails.append(name)

DBP = "CCCCOC(=O)c1ccccc1C(=O)OCCCC"
MBP_NEUTRAL = "CCCCOC(=O)c1ccccc1C(=O)O"
MBP_ION = "CCCCOC(=O)c1ccccc1C(=O)[O-]"
BOGUS = "CCCCOC(=O)c1ccccc1C"          # butyl 2-methylbenzoate (Rank-1 error)

# --- 1. charge normalization ---
check("uncharge MBP ion -> neutral",
      normalize_charge_smiles(MBP_ION) == MBP_NEUTRAL,
      normalize_charge_smiles(MBP_ION))
check("neutral form stable", normalize_charge_smiles(MBP_NEUTRAL) == MBP_NEUTRAL)

# --- 2. skeleton plausibility ---
r = assess_skeleton_change(DBP, MBP_NEUTRAL)
check("MBP hydrolysis loss attributed (no flag)", not r["unexplained"], r["reason"])
r = assess_skeleton_change(DBP, BOGUS)
check("bogus aryl-CH3 rearrangement flagged", r["unexplained"], f"lost={r['n_heavy_lost']} {r['reason']}")
r = assess_skeleton_change(DBP, DBP)
check("identity no flag", not r["unexplained"], r["reason"])
r = assess_skeleton_change(DBP, "CCCCOC(=O)c1ccccc1C(=O)OC(C)CC")
check("isobutyl isomer (pure gain-ish/swap) no crash", isinstance(r, dict), r["reason"])

# decarboxylation: phthalic acid -> benzoic acid (real biodegradation step)
r = assess_skeleton_change("OC(=O)c1ccccc1C(=O)O", "OC(=O)c1ccccc1")
check("decarboxylation attributed", not r["unexplained"], r["reason"])

# O-dealkylation: anisole -> phenol
r = assess_skeleton_change("COc1ccccc1", "Oc1ccccc1")
check("O-dealkylation attributed", not r["unexplained"], r["reason"])

# dehalogenation
r = assess_skeleton_change("Clc1ccccc1", "c1ccccc1")
check("dehalogenation attributed", not r["unexplained"], r["reason"])

# N-dealkylation
r = assess_skeleton_change("CN(C)c1ccccc1", "CNc1ccccc1")
check("N-dealkylation attributed", not r["unexplained"], r["reason"])

# epoxidation (gain only) must NOT flag
r = assess_skeleton_change("CCCCCC", "CCC1CC1CC")
check("epoxidation (gain) no flag", not r["unexplained"], r["reason"])

# unattributed big loss: DBP -> phthalic acid (loses BOTH butyls in one step = 2 events)
r = assess_skeleton_change(DBP, "OC(=O)c1ccccc1C(=O)O")
print("       info: DBP->PTA double loss:", r["reason"][:80], "unexplained =", r["unexplained"])

# --- 3. merge + fusion ---
cands = [
    {"product_smiles": BOGUS, "source": "uspto", "p_uspto": 0.791706,
     "p_envipath": 0.0, "p_retrieval": 0.0},
    {"product_smiles": MBP_ION, "source": "uspto+envipath",
     "p_uspto": 0.0760, "p_envipath": 0.5522, "p_retrieval": 0.0},
    {"product_smiles": MBP_NEUTRAL, "source": "uspto",
     "p_uspto": 0.005060, "p_envipath": 0.0, "p_retrieval": 0.0},
    {"product_smiles": "CCCCOC(=O)c1ccccc1C(O)OCCCC", "source": "uspto",
     "p_uspto": 0.4384, "p_envipath": 0.0, "p_retrieval": 0.0},
]
merged = merge_charge_variants(cands)
check("MBP ion+neutral merged to 1 identity",
      sum(1 for m in merged if m["product_smiles"] == MBP_NEUTRAL) == 1)
mbp = [m for m in merged if m["product_smiles"] == MBP_NEUTRAL][0]
check("merged MBP has 2 sources", mbp["source"] == "uspto+envipath", mbp["source"])
check("merged MBP p_envipath = max over members", abs(mbp["p_envipath"] - 0.5522) < 1e-6,
      str(mbp["p_envipath"]))
check("charge_variants preserved", len(mbp["charge_variants"]) == 2)

ns, det = fused_ns33({"uspto": 0.791706}, {"uspto"}, True)
check("bogus fused below 0.20 after penalty", ns < 0.20, f"{ns:.6f}")
ns2, _ = fused_ns33({"uspto": 0.0760, "envipath": 0.5522}, {"uspto", "envipath"}, False)
check("MBP fused above bogus", ns2 > ns, f"{ns2:.6f} vs {ns:.6f}")

print()
print("FAILED:", fails if fails else "none — all pass")
sys.exit(1 if fails else 0)
