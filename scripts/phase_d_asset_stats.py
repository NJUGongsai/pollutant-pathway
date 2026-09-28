"""Phase D D1 参数卡依据:corpus_templates_v1 反应物指纹的无标签分布统计。

只读资产、零网络、零金标(不看 dev 20 / EC298 任何输入或答案)。
输出 reports/phase_d/asset_similarity_stats.json:

- 资产规模与可解析率(索引构建口径与运行时一致);
- 固定种子抽样的"资产内最近邻相似度"分布(分位数)—— 支撑阈值选择:
  阈值应高于"随机碰撞"水平、低于"近同物"水平,使召回量适中;
- 指纹唯一反应物数(同 SMILES 多记录 => 去重键必须含 record_id/line_no);
- 索引构建与单查询耗时(性能成本)。

用法:
  OMP_NUM_THREADS=1 PYTHONPATH=src python scripts/phase_d_asset_stats.py \
      [--sample 2000] [--seed 20260928]
"""

from __future__ import annotations

import argparse
import json
import random
import time
from collections import Counter
from pathlib import Path

from rdkit import Chem, DataStructs, RDLogger
from rdkit.Chem import rdMolDescriptors

RDLogger.DisableLog("rdApp.*")

from pathway_v43.services.analog_source import (  # noqa: E402
    SIMILARITY_FP_BITS,
    SIMILARITY_FP_CHIRALITY,
    SIMILARITY_FP_RADIUS,
    SIMILARITY_VERSION,
    _lhs_rhs,
    _strip_map,
)

ASSET = Path("assets/analog/corpus_templates_v1.jsonl")
OUT = Path("reports/phase_d/asset_similarity_stats.json")


def fp_of(smiles: str):
    mol = Chem.MolFromSmiles(smiles) if smiles else None
    if mol is None:
        return None
    try:
        return rdMolDescriptors.GetMorganFingerprintAsBitVect(
            mol, SIMILARITY_FP_RADIUS, nBits=SIMILARITY_FP_BITS,
            useChirality=SIMILARITY_FP_CHIRALITY)
    except Exception:
        return None


def quantiles(sorted_vals: list[float]) -> dict:
    def pct(p: float) -> float:
        if not sorted_vals:
            return 0.0
        i = min(len(sorted_vals) - 1, max(0, round(p * (len(sorted_vals) - 1))))
        return round(sorted_vals[i], 4)

    return {f"p{int(p*100)}": pct(p)
            for p in (0.0, 0.05, 0.25, 0.5, 0.75, 0.9, 0.95, 0.99, 1.0)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=20260928)
    args = ap.parse_args()

    t0 = time.time()
    rows = []
    with open(ASSET, encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            lhs, _ = _lhs_rhs(row)
            reactant = _strip_map(lhs)
            rows.append((line_no, str(row.get("record_id", "")), reactant))
    t_load = time.time() - t0

    t0 = time.time()
    fps, unparseable = [], 0
    for ln, rid, smi in rows:
        fp = fp_of(smi)
        if fp is None:
            unparseable += 1
        else:
            fps.append(fp)
    t_index = time.time() - t0

    unique_reactants = len({smi for _ln, _rid, smi in rows})
    smi_counts = Counter(smi for _ln, _rid, smi in rows)
    dup_groups = sum(1 for c in smi_counts.values() if c > 1)

    # 固定种子抽样:每个抽中反应物与资产内**其它**指纹的最近邻相似度
    rng = random.Random(args.seed)
    n = len(fps)
    idxs = sorted(rng.sample(range(n), min(args.sample, n)))
    t0 = time.time()
    nn_sims = []
    kth5_sims = []
    for i in idxs:
        sims = DataStructs.BulkTanimotoSimilarity(fps[i], fps)
        sims[i] = -1.0  # 排除自身
        best = max(sims)
        nn_sims.append(best)
        top5 = sorted(sims, reverse=True)[:5]
        kth5_sims.append(top5[-1])
    t_query = (time.time() - t0) / max(1, len(idxs))

    nn_sorted = sorted(nn_sims)
    k5_sorted = sorted(kth5_sims)

    # 召回量曲线:抽样底物在各阈值下的平均召回数(资产内、含自身)
    thresholds = [0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70]
    yield_curve = {}
    for th in thresholds:
        counts = []
        for i in idxs[:500]:  # 500 个抽样底物足够估召回量
            sims = DataStructs.BulkTanimotoSimilarity(fps[i], fps)
            counts.append(sum(1 for s in sims if s >= th) - 1)  # 去自身
        counts.sort()
        yield_curve[str(th)] = {
            "mean": round(sum(counts) / len(counts), 1),
            "median": counts[len(counts) // 2],
            "p90": counts[int(0.9 * (len(counts) - 1))],
            "max": counts[-1],
            "frac_zero": round(
                sum(1 for c in counts if c == 0) / len(counts), 3),
        }

    out = {
        "asset_file": str(ASSET),
        "similarity_version": SIMILARITY_VERSION,
        "fingerprint": {
            "kind": "morgan", "radius": SIMILARITY_FP_RADIUS,
            "bits": SIMILARITY_FP_BITS, "use_chirality": SIMILARITY_FP_CHIRALITY,
            "metric": "tanimoto", "threshold_cmp": ">=",
        },
        "n_rows": len(rows),
        "n_unparseable_reactants": unparseable,
        "n_unique_reactants": unique_reactants,
        "n_reactant_smiles_groups": len(smi_counts),
        "n_duplicate_smiles_groups": dup_groups,
        "max_records_per_smiles": max(smi_counts.values()),
        "nearest_neighbor_similarity": quantiles(nn_sorted),
        "kth_of_top5_similarity": quantiles(k5_sorted),
        "recall_yield_curve": yield_curve,
        "timing_s": {
            "load": round(t_load, 2),
            "fingerprint_index_build": round(t_index, 2),
            "per_query_bulk_scan": round(t_query, 4),
        },
        "sample": {"n": len(idxs), "seed": args.seed},
        "gold_contact": "none (asset-only, label-free)",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
