#!/usr/bin/env python3
"""MPNN 域微调试水 — Phase 1：从 aam_sample.jsonl 派生微调训练集。

每条 RHEA 映射反应 mapped_reaction_smiles = lhs>>rhs，用 atom-map 号将 lhs
与 rhs 原子配对，比对 (a) 形式电荷 (b) 总 H 数 (c) 对 mapped 邻居的键序签名，
任一变化即记该 lhs 原子为 reacted。substrate_smiles 保留 lhs 的 atom-map（与
USPTO 训练集口径一致，保证 mol_to_tensor 解析序与 reacted_atom_indices 对齐）。

红线 §5.1：训练 substrate（stereo-blind canonical）∩ 93 blind parent = 0。
"""
import argparse
import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
from rdkit import Chem  # noqa: E402
from rdkit import RDLogger  # noqa: E402
RDLogger.DisableLog("rdApp.*")

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(REPO, "reaction_analogy", "data")
AAM = os.path.join(DATA, "aam", "aam_sample.jsonl")
OUT_DIR = os.path.join(DATA, "bbd_mpnn_trial")
OUT = os.path.join(OUT_DIR, "finetune_train.jsonl")
STATS = os.path.join(OUT_DIR, "finetune_train_stats.json")
BLIND_CSV = os.path.join(
    REPO,
    "bbd_known_pathway_full_route_v0_3_candidate_v3_1_strict_blind_fix_20260821",
    "blind",
    "BBD_KNOWN_PATHWAY_FULL_ROUTE_V0_3_V3_1_BLIND_PARENT_INPUTS_FOR_PREDICTION_STRICT.csv",
)


def stereo_blind_canon(smiles):
    """strip atom map → stereo-blind canonical（v3 泄漏纪律同口径）。"""
    m = Chem.MolFromSmiles(smiles)
    if m is None:
        return None
    for a in m.GetAtoms():
        a.SetAtomMapNum(0)
    return Chem.MolToSmiles(m, canonical=True, isomericSmiles=False)


def bond_sig(atom):
    """{邻居 atom-map 号: 键序 double}，只含非零 map 邻居。"""
    sig = {}
    for n in atom.GetNeighbors():
        mn = n.GetAtomMapNum()
        if mn == 0:
            continue
        b = atom.GetOwningMol().GetBondBetweenAtoms(atom.GetIdx(), n.GetIdx())
        sig[mn] = round(b.GetBondTypeAsDouble(), 3)
    return sig


def derive_reacted(mapped_rxn):
    """mapped_reaction_smiles -> (substrate_smiles, reacted_atom_indices, ok)。"""
    if ">>" not in mapped_rxn:
        return None, None, False
    lhs, rhs = mapped_rxn.split(">>", 1)
    lm = Chem.MolFromSmiles(lhs)
    rm = Chem.MolFromSmiles(rhs)
    if lm is None or rm is None:
        return None, None, False
    l_map = {a.GetAtomMapNum(): a for a in lm.GetAtoms() if a.GetAtomMapNum() != 0}
    r_map = {a.GetAtomMapNum(): a for a in rm.GetAtoms() if a.GetAtomMapNum() != 0}
    reacted = set()
    for mn, la in l_map.items():
        if mn not in r_map:
            # lhs 原子在 rhs 消失（被消耗）→ reacted
            reacted.add(la.GetIdx())
            continue
        ra = r_map[mn]
        if la.GetFormalCharge() != ra.GetFormalCharge():
            reacted.add(la.GetIdx())
        elif la.GetTotalNumHs() != ra.GetTotalNumHs():
            reacted.add(la.GetIdx())
        elif bond_sig(la) != bond_sig(ra):
            reacted.add(la.GetIdx())
    return lhs, sorted(reacted), True


def load_blind_canon_set():
    """93 blind parent 的 stereo-blind canonical 集合。"""
    out = set()
    import csv
    with open(BLIND_CSV, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            for col in ("parent_canonical_smiles", "parent_smiles"):
                v = row.get(col, "")
                if not v:
                    continue
                c = stereo_blind_canon(v)
                if c:
                    out.add(c)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--aam", default=AAM)
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--stats", default=STATS)
    ap.add_argument("--blind-csv", default=BLIND_CSV)
    ap.add_argument("--spotcheck", type=int, default=3)
    args = ap.parse_args()

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    blind_set = load_blind_canon_set()
    print(f"blind stereo-blind canonical set: {len(blind_set)} entries", flush=True)

    n_total = n_ok_roundtrip = n_parse_fail = n_no_reacted = n_multi_frag = n_leak = 0
    kept = []
    reacted_count_dist = Counter()
    spot_checks = []

    with open(args.aam, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            n_total += 1
            r = json.loads(line)
            if not (r.get("status") == "ok" and r.get("roundtrip_pass")):
                continue
            n_ok_roundtrip += 1
            mapped = r.get("mapped_reaction_smiles", "")
            lhs, reacted, ok = derive_reacted(mapped)
            if not ok:
                n_parse_fail += 1
                continue
            if "." in lhs:
                n_multi_frag += 1
                continue
            if not reacted:
                n_no_reacted += 1
                continue
            canon = stereo_blind_canon(lhs)
            if canon is None:
                n_parse_fail += 1
                continue
            if canon in blind_set:
                n_leak += 1
                continue
            rec = {
                "status": "ok",
                "substrate_smiles": lhs,
                "reacted_atom_indices": reacted,
                "source": "rhea_aam_trial",
                "record_id": r.get("record_id"),
                "mapper_confidence": r.get("mapper_confidence"),
                "n_atoms": Chem.MolFromSmiles(lhs).GetNumAtoms(),
                "changed_reactant_from_detail": r.get("changed_atom_detail", {}).get("changed_reactant"),
            }
            kept.append(rec)
            reacted_count_dist[len(reacted)] += 1
            if len(spot_checks) < args.spotcheck:
                spot_checks.append({
                    "record_id": rec["record_id"],
                    "derived_n_reacted": len(reacted),
                    "derived_reacted_idx": reacted,
                    "aam_changed_reactant": rec["changed_reactant_from_detail"],
                    "mapped_reaction_smiles": mapped,
                    "match": len(reacted) == rec["changed_reactant_from_detail"],
                })

    with open(args.out, "w", encoding="utf-8") as fh:
        for rec in kept:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    # 泄漏断言（红线 §5.1）：最终训练集 ∩ blind = 0
    train_canons = {stereo_blind_canon(r["substrate_smiles"]) for r in kept}
    train_canons.discard(None)
    leak_intersect = train_canons & blind_set
    assert not leak_intersect, f"LEAK: {len(leak_intersect)} train substrates overlap blind: {list(leak_intersect)[:5]}"

    stats = {
        "n_total": n_total,
        "n_ok_roundtrip": n_ok_roundtrip,
        "n_parse_fail": n_parse_fail,
        "n_no_reacted": n_no_reacted,
        "n_multi_fragment": n_multi_frag,
        "n_leak": n_leak,
        "n_kept": len(kept),
        "reacted_count_distribution": dict(sorted(reacted_count_dist.items())),
        "leak_assertion_passed": True,
        "leak_intersect_count": 0,
        "spot_checks": spot_checks,
    }
    with open(args.stats, "w", encoding="utf-8") as fh:
        json.dump(stats, fh, indent=2, ensure_ascii=False)

    print("=== Phase 1 派生统计 ===", flush=True)
    print(json.dumps(stats, indent=2, ensure_ascii=False), flush=True)
    print(f"\n写入 {args.out} ({len(kept)} 行)", flush=True)
    print("=== 抽查（派生 n_reacted vs aam changed_reactant）===", flush=True)
    for sc in spot_checks:
        print(f"  {sc['record_id']}: derived={sc['derived_n_reacted']} "
              f"aam={sc['aam_changed_reactant']} match={sc['match']}", flush=True)


if __name__ == "__main__":
    main()
