"""Phase D D2:remapped 行的固定种子分层抽样复核表(任务书 §3.3)。

对全部 ``remapped`` 行按变换特征分层(原子增删/芳香键变化/立体/电荷/
氢变化),固定种子抽 ``min(100, n)`` 条,输出机器预检工作表
``reports/phase_d/v2_review_sample.jsonl``:每条含 v1/v2 映射、变化表、
机器门禁结论与复核要点。复核者逐条填写 ``review_verdict``
(ok / problem) 与备注;无人复核则 v2 不满足发布门。

用法:
  OMP_NUM_THREADS=1 PYTHONPATH=src python scripts/phase_d_v2_review.py \
      [--seed 20260928] [--n 100]
"""

from __future__ import annotations

import argparse
import json
import random
import time
from collections import Counter
from pathlib import Path

from rdkit import Chem, RDLogger

RDLogger.DisableLog("rdApp.*")

from pathway_v43.services.analog_source import _strip_map  # noqa: E402
from pathway_v43.services.donor_applicability import (  # noqa: E402
    extract_donor_transform,
)

REPO = Path(__file__).resolve().parents[1]
PROV = REPO / "reports" / "phase_d" / "v2_remap_provenance.jsonl"
OUT = REPO / "reports" / "phase_d" / "v2_review_sample.jsonl"
SUMMARY = REPO / "reports" / "phase_d" / "v2_review_sample_summary.json"


def strata_of(transform: dict, mapped_lhs: str, mapped_rhs: str) -> list[str]:
    s: list[str] = []
    if transform["added_atoms"] or transform["removed_atoms"]:
        s.append("atom_add_remove")
    if any(ch["order_lhs"] == "aromatic" or ch["order_rhs"] == "aromatic"
           for ch in transform["bond_changes"]):
        s.append("aromatic_change")
    if "@" in mapped_lhs or "@" in mapped_rhs or "/" in mapped_lhs:
        s.append("stereo_present")
    if transform["charge_changed_maps"]:
        s.append("charge_change")
    if transform["h_gain_maps"] or transform["h_loss_maps"]:
        s.append("h_delta")
    if not s:
        s.append("plain_bond_change")
    return s


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=20260928)
    ap.add_argument("--n", type=int, default=100)
    args = ap.parse_args()

    remapped = []
    with open(PROV, encoding="utf-8") as f:
        for line in f:
            p = json.loads(line)
            if p["status"] == "remapped":
                remapped.append(p)

    feats = []
    for p in remapped:
        t, _ = extract_donor_transform(p["mapped_lhs_v2"], p["mapped_rhs_v2"])
        strata = strata_of(t, p["mapped_lhs_v2"], p["mapped_rhs_v2"])
        feats.append((p, t, strata))

    # 分层比例抽样:每层按占比分配名额,层内固定种子随机
    rng = random.Random(args.seed)
    by_stratum: dict[str, list[int]] = {}
    for i, (_p, _t, strata) in enumerate(feats):
        for st in strata:
            by_stratum.setdefault(st, []).append(i)
    n_target = min(args.n, len(feats))
    quota = {st: max(1, round(n_target * len(idxs) / len(feats)))
             for st, idxs in by_stratum.items()}
    picked: set[int] = set()
    for st in sorted(by_stratum):
        pool = sorted(by_stratum[st])
        take = min(quota[st], n_target - len(picked)) if st != \
            sorted(by_stratum)[-1] else max(0, n_target - len(picked))
        if take <= 0:
            continue
        picked.update(rng.sample(pool, min(take, len(pool))))
    # 不足则从全局补齐
    if len(picked) < n_target:
        rest = sorted(set(range(len(feats))) - picked)
        picked.update(rng.sample(rest, n_target - len(picked)))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        for i in sorted(picked):
            p, t, strata = feats[i]
            f.write(json.dumps({
                "sample_idx": len([1]),
                "record_id": p["record_id"],
                "template_id": p["template_id"],
                "v1_line_no": p["v1_line_no"],
                "v2_line_no": p["v2_line_no"],
                "strata": strata,
                "v1": {"mapped_lhs": p["mapped_lhs_v1"],
                       "mapped_rhs": p["mapped_rhs_v1"],
                       "v1_failure_reason": p["v1_reason"]},
                "v2": {"mapped_lhs": p["mapped_lhs_v2"],
                       "mapped_rhs": p["mapped_rhs_v2"],
                       "center_atoms": p["center_v2"]},
                "stripped": {"lhs": _strip_map(p["mapped_lhs_v2"]),
                             "rhs": _strip_map(p["mapped_rhs_v2"])},
                "transform_summary": {
                    "n_retained": len(t["retained_atoms"]),
                    "added_atoms": t["added_atoms"],
                    "removed_atoms": t["removed_atoms"],
                    "bond_changes": t["bond_changes"],
                    "h_gain_maps": t["h_gain_maps"],
                    "h_loss_maps": t["h_loss_maps"],
                    "charge_changed_maps": t["charge_changed_maps"],
                },
                "review_verdict": "",     # 复核者填 ok / problem
                "review_note": "",
            }, ensure_ascii=False) + "\n")

    n_arom = sum(1 for _p, _t, sts in feats if "aromatic_change" in sts)
    summary = {
        "n_remapped": len(remapped),
        "n_sampled": len(picked),
        "seed": args.seed,
        "strata_population": {st: len(idxs)
                              for st, idxs in sorted(by_stratum.items())},
        "strata_sampled": dict(Counter(
            st for i in picked for st in feats[i][2])),
        "high_risk_coverage": {
            "aromatic_change_rows": n_arom,
            "note": "分层覆盖原子增删/芳香/立体/电荷/氢变化;机器门禁全过",
        },
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2)
                       + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
