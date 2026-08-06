"""诊断: selection_failure 里"对的变换"到底在不在训练库。

复用 honest_eval 的同一套编辑签名口径(transformed_pair→extract_edit→key), 只读、不改评估。
对每个测试反应, 把它切成:
  unparsable                 : 主底物解析不出
  unextractable              : 反应自身抽不出编辑(多底物/退化, 内在难例)
  retrieved                  : 对的变换已在 top-K donor 里(非 selection failure)
  A1_in_library_ranked_out   : top-K 没带回, 但全 train 库里存在 → 改检索能救(扩K/换钥匙/多底物召回)
  A2_absent_truly_novel      : 全 train 库里也没有 → 真 novel, 检索无解, 需泛化模型

A1 : A2 的比例, 就是"检索改造的天花板"。A1 多 → 值得砸检索; A2 多 → 转向 B 模型。
"""
import argparse
import json
import time
from collections import Counter

import canonical_identity as ci
import splits as sp
import honest_eval as he


def diagnose(strategy: str, seed: int = 42, max_cases=None) -> dict:
    split = sp.make_split(strategy, seed=seed)
    index = he.build_donor_index(split.train_rxns)

    # 全 train 库的编辑签名集(A1/A2 判定的"库存")
    train_keys = set()
    for r in split.train_rxns:
        k = he._reaction_edit_key(r)
        if k is not None:
            train_keys.add(k)

    test = split.test_rxns[:max_cases] if max_cases else split.test_rxns
    print(f"[{strategy}] train={len(index[0])} train_keys={len(train_keys)} test={len(test)}", flush=True)

    c = Counter()
    t0 = time.time()
    for i, rxn in enumerate(test, 1):
        x = ci.main_substrate(rxn)
        if x is None:
            c["unparsable"] += 1
        else:
            req_key = he._reaction_edit_key(rxn)
            if req_key is None:
                c["unextractable"] += 1
            else:
                exclude = ci.group_key(rxn)
                donors = he.retrieve_donors(x, index, he.TOP_DONORS, exclude)
                donor_keys = {k for k in (he._reaction_edit_key(d) for d, _s in donors) if k is not None}
                if req_key in donor_keys:
                    c["retrieved"] += 1
                elif req_key in train_keys:
                    c["A1_in_library_ranked_out"] += 1
                else:
                    c["A2_absent_truly_novel"] += 1
        if i % 100 == 0 or i == len(test):
            print(f"  {i}/{len(test)} ({time.time()-t0:.0f}s)", flush=True)

    sel = c["A1_in_library_ranked_out"] + c["A2_absent_truly_novel"]
    out = {
        "strategy": strategy,
        "counts": dict(c),
        "selection_failure_like": sel,
        "A1_ratio_within_selection": round(c["A1_in_library_ranked_out"] / sel, 4) if sel else None,
        "A2_ratio_within_selection": round(c["A2_absent_truly_novel"] / sel, 4) if sel else None,
    }
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--strategies", nargs="+",
                    default=["random", "scaffold", "reaction_family"])
    ap.add_argument("--max-cases", type=int, default=None)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    results = [diagnose(s, max_cases=args.max_cases) for s in args.strategies]
    print(json.dumps(results, ensure_ascii=False, indent=2))
    if args.out:
        with open(args.out, "w") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
