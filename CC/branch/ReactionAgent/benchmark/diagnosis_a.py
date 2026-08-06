"""Disease A 诊断：精确编辑签名在库里但排后面 vs 训练库未覆盖。

回答 STATUS_OVERVIEW 里唯一悬而未决的问题：
  359 例 selection_failure 中，对的变法到底——
    A · 在训练库里，只是 Morgan top-5 排不进来 → 改检索能救
    B · 当前精确编辑签名在训练库中未覆盖 → 需继续区分真 novel 与签名错配

输出
  reports/diagnosis_a_<strategy>.json + 终端摘要。

口径纪律
  - Disease A 只统计 honest_eval 的 selection_failure：
    真产物未生成、测试编辑可抽取、top-5 donor 未带同一编辑签名。
  - “未覆盖”不直接叫“真 novel”。EditScript.key() 仍可能受多底物主片段配对影响。
"""
import json
import os
import sys
import time
from collections import Counter, defaultdict
from functools import lru_cache
from typing import Dict, List, Optional, Tuple

from rdkit import Chem
from rdkit.Chem import AllChem, DataStructs
from rdkit import RDLogger

RDLogger.DisableLog("rdApp.*")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "core"))
sys.path.insert(0, os.path.dirname(__file__))

import canonical_identity as ci
import edit_script as esmod
import honest_eval as he
import splits as sp


# ── 编辑签名索引 ─────────────────────────────────────────────────────────

@lru_cache(maxsize=50000)
def _edit_key_of(rxn: str):
    """反应 → 编辑签名；抽不出返回 None。"""
    tp = ci.transformed_pair(rxn)
    if tp is None:
        return None
    es = esmod.extract_edit(tp[0], tp[1])
    return es.key() if es is not None else None


def build_train_edit_index(train_rxns: List[str]) -> Dict[tuple, List[str]]:
    """训练折所有反应的编辑签名 → 反应列表。"""
    idx: Dict[tuple, List[str]] = defaultdict(list)
    for rxn in train_rxns:
        k = _edit_key_of(rxn)
        if k is not None:
            idx[k].append(rxn)
    return dict(idx)


def morgan_rank_of_match(query_x: str, match_rxns: List[str],
                         donor_index, exclude_group) -> Tuple[int, float]:
    """匹配的 donor 在 Morgan 全库排序里的最佳 rank 及其相似度。

    排序与 honest_eval.retrieve_donors 完全相同；相似度并列时保留训练索引顺序。
    返回 (best_rank, best_sim)。rank=-1 表示不可计算。
    """
    qm = Chem.MolFromSmiles(query_x)
    if qm is None:
        return (-1, 0.0)
    qfp = AllChem.GetMorganFingerprintAsBitVect(qm, 2, nBits=2048)
    reactions, fps, _subs = donor_index
    sims = DataStructs.BulkTanimotoSimilarity(qfp, fps)
    order = sorted(range(len(sims)), key=lambda i: sims[i], reverse=True)
    matches = set(match_rxns)
    rank = 0
    for i in order:
        rxn = reactions[i]
        if exclude_group is not None and ci.group_key(rxn) == exclude_group:
            continue
        rank += 1
        if rxn in matches:
            return (rank, float(sims[i]))
    return (-1, 0.0)


def _generation_status(donors, query_x: str, y_true: str) -> Tuple[bool, bool]:
    """复刻 honest_eval 的候选生成漏斗，返回 (has_candidate, generated_true)。"""
    seen = set()
    generated_true = False
    for donor_rxn, _sim in donors:
        for prod in he.generate_candidates(donor_rxn, query_x):
            key = ".".join(sorted(ci.canon_frags(prod)))
            if not key or key in seen:
                continue
            seen.add(key)
            if y_true in ci.canon_frags(prod):
                generated_true = True
    return (bool(seen), generated_true)


# ── 主诊断 ────────────────────────────────────────────────────────────────

def diagnose(strategy: str = "random", max_cases: Optional[int] = None) -> dict:
    """对 Disease A (selection_failure) 做全库搜索，切出 in_library vs not_in_library。"""
    t0 = time.time()
    split = sp.make_split(strategy)
    print(f"[{strategy}] {split.summary()}", flush=True)
    he.GENERATOR = "smarts"
    donor_index = he.build_donor_index(split.train_rxns)

    # 构建训练折编辑签名索引
    edit_idx = build_train_edit_index(split.train_rxns)
    n_edit_types = len(edit_idx)
    print(f"  训练 donor: {len(donor_index[0])}; 编辑签名类型数: {n_edit_types}", flush=True)

    results = []
    outcomes = Counter()
    rank_bins = Counter()  # 匹配 donor 的 Morgan rank 分布

    test_rxns = split.test_rxns[:max_cases] if max_cases else split.test_rxns

    for i, rxn in enumerate(test_rxns, 1):
        if i == 1 or i % 50 == 0:
            print(f"  进度: 开始 {i}/{len(test_rxns)}", flush=True)
        x = ci.main_substrate(rxn)
        y_true = ci.main_product(rxn)
        if x is None or y_true is None:
            outcomes["unparsable"] += 1
            continue

        exclude_group = ci.group_key(rxn)
        req_key = _edit_key_of(rxn)

        donors = he.retrieve_donors(x, donor_index, he.TOP_DONORS, exclude_group)
        if not donors:
            outcomes["no_donor"] += 1
            continue

        # 先复刻 honest_eval 的候选漏斗：no_candidate 单列，不并入病 A/B/C。
        has_candidate, generated_true = _generation_status(donors, x, y_true)
        if not has_candidate:
            outcomes["no_candidate"] += 1
            continue
        if generated_true:
            outcomes["generated_true"] += 1
            continue

        outcomes["not_generated"] += 1
        if req_key is None:
            outcomes["unextractable"] += 1
            results.append({
                "rxn": rxn, "x": x, "y_true": y_true,
                "category": "disease_c_unextractable",
            })
            continue

        top5_keys = {_edit_key_of(d) for d, _sim in donors}
        if req_key in top5_keys:
            outcomes["application_failure"] += 1
            continue

        # 到这里才是 honest_eval 的 Disease A / selection_failure。
        outcomes["selection_failure"] += 1
        match_rxns = [
            r for r in edit_idx.get(req_key, [])
            if ci.group_key(r) != exclude_group
        ]

        if not match_rxns:
            outcomes["signature_not_in_library"] += 1
            results.append({
                "rxn": rxn, "x": x, "y_true": y_true,
                "category": "signature_not_in_library",
                "edit_key": str(req_key),
            })
        else:
            rank, sim = morgan_rank_of_match(x, match_rxns, donor_index, exclude_group)
            outcomes["signature_in_library"] += 1

            if rank <= 5:
                # selection_failure 按定义不应进入这里；保留计数作为一致性报警。
                rank_bins["rank_1-5"] += 1
                sub_category = "signature_in_library_top5_inconsistency"
            elif rank <= 10:
                rank_bins["rank_6-10"] += 1
                sub_category = "signature_in_library_rank_6-10"
            elif rank <= 20:
                rank_bins["rank_11-20"] += 1
                sub_category = "signature_in_library_rank_11-20"
            elif rank <= 50:
                rank_bins["rank_21-50"] += 1
                sub_category = "signature_in_library_rank_21-50"
            else:
                rank_bins["rank_50+"] += 1
                sub_category = "signature_in_library_rank_50+"

            results.append({
                "rxn": rxn, "x": x, "y_true": y_true,
                "category": "signature_in_library",
                "sub_category": sub_category,
                "morgan_rank": rank,
                "morgan_sim": round(sim, 4),
                "n_matching_donors": len(match_rxns),
                "edit_key": str(req_key),
            })

    elapsed = round(time.time() - t0, 1)

    # ── 汇总 ──────────────────────────────────────────────────────────────
    n_test = len(test_rxns)
    n_not_in_lib = outcomes["signature_not_in_library"]
    n_in_lib = outcomes["signature_in_library"]
    n_selection = outcomes["selection_failure"]
    if n_selection != n_in_lib + n_not_in_lib:
        raise AssertionError("Disease A 子类计数不守恒")
    if rank_bins["rank_1-5"] != 0:
        raise AssertionError("selection_failure 中出现 top-5 同签名 donor，口径不一致")

    summary = {
        "strategy": strategy,
        "generator": he.GENERATOR,
        "top_donors": he.TOP_DONORS,
        "n_test": n_test,
        "elapsed_sec": elapsed,
        "n_edit_types_in_train": n_edit_types,
        "outcomes": dict(outcomes),
        "rank_distribution": dict(rank_bins),
        "disease_a_selection_failure": n_selection,
        "signature_in_library": n_in_lib,
        "signature_not_in_library": n_not_in_lib,
        "signature_in_library_pct": round(100 * n_in_lib / max(1, n_selection), 1),
        "signature_not_in_library_pct": round(100 * n_not_in_lib / max(1, n_selection), 1),
        # 按 rank 段分布
        "in_library_rank_1_5": rank_bins.get("rank_1-5", 0),
        "in_library_rank_6_10": rank_bins.get("rank_6-10", 0),
        "in_library_rank_11_20": rank_bins.get("rank_11-20", 0),
        "in_library_rank_21_50": rank_bins.get("rank_21-50", 0),
        "in_library_rank_50_plus": rank_bins.get("rank_50+", 0),
    }

    return {"summary": summary, "cases": results}


# ── 终端报告 ──────────────────────────────────────────────────────────────

def print_report(result: dict):
    s = result["summary"]
    print()
    print("=" * 65)
    print("  Disease A 诊断报告")
    print("=" * 65)
    print(f"  拆分策略:       {s['strategy']}")
    print(f"  测试集大小:     {s['n_test']}")
    print(f"  训练库编辑类型: {s['n_edit_types_in_train']}")
    print(f"  耗时:           {s['elapsed_sec']}s")
    print()
    print(f"  ┌─ Disease A / selection failure: {s['disease_a_selection_failure']}")
    print(f"  │  ├─ ✅ 精确签名在库 (改检索有机会救): "
          f"{s['signature_in_library']} ({s['signature_in_library_pct']}%)")
    print(f"  │  │     top-5 一致性异常: {s['in_library_rank_1_5']}")
    print(f"  │  │     rank 6-10:  {s['in_library_rank_6_10']}")
    print(f"  │  │     rank 11-20: {s['in_library_rank_11_20']}")
    print(f"  │  │     rank 21-50: {s['in_library_rank_21_50']}")
    print(f"  │  │     rank 50+:   {s['in_library_rank_50_plus']}")
    print(f"  │  └─ ⚠ 精确签名未覆盖: "
          f"{s['signature_not_in_library']} ({s['signature_not_in_library_pct']}%)")
    print("  │        注意: 仍混有多底物签名错配，不能直接等同真 novel")
    print(f"  ├─ Disease B / application failure: {s['outcomes'].get('application_failure', 0)}")
    print(f"  └─ Disease C / unextractable: {s['outcomes'].get('unextractable', 0)}")
    print()

    # 决策建议
    pct = s["signature_in_library_pct"]
    if pct >= 60:
        verdict = "检索改造 ROI 高！大多数变法在库里但排不上来"
    elif pct >= 30:
        verdict = "检索改造 + 泛化模型两手都要抓"
    else:
        verdict = "多数精确签名未覆盖；先审计签名错配，再决定泛化模型优先级"
    print(f"  📋 决策: {verdict}")
    print("=" * 65)


def main():
    strategy = os.environ.get("DIAG_STRATEGY", "random")
    max_cases = int(os.environ.get("DIAG_MAX_CASES", "0")) or None

    result = diagnose(strategy, max_cases)
    print_report(result)

    # 落盘
    out_dir = os.path.join(os.path.dirname(__file__), "..", "reports")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"diagnosis_a_{strategy}.json")
    with open(out_path, "w") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\n  结果已写入: {out_path}")


if __name__ == "__main__":
    main()
