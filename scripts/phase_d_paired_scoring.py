"""Phase D D3.2/D3.3:四臂 dev 20 配对判分与预注册规则判定(零 LLM)。

对 Chenyu 上四个批次根(C0/D3/D5/D10,各 20 路 merged predictions)执行
冻结 v3 评测器(--split dev),产出:

1. 逐臂总体:cn@1/@3/@5、raw_sb 对照、leaf-reached、spurious;
2. 逐题配对表(vs C0):每 route 的 @1/@3/@5 命中、首个报告位次、
   报告/提交产品数、来源(analogy/novel/recorded)、缺题标记;
3. 配对净赢计数(@1 净赢题数 = 臂@1 命中数 - C0@1 命中数,按题配对);
4. 预注册规则判定(任务书 §4.3,仅硬门全过后才给 adopt 结论;本脚本
   打印判定输入,发布声明写在阶段报告)。

用法(Chenyu,零 LLM):
  OMP_NUM_THREADS=1 PYTHONPATH=src .venv/bin/python \
      scripts/phase_d_paired_scoring.py \
      --arms C0=runs/phase_d_C0 D3=runs/phase_d_D3 \
             D5=runs/phase_d_D5 D10=runs/phase_d_D10 \
      --v3-root /usrdata/EnzymeCAGE_data/workspaces/dependingv3 \
      --out-dir reports/phase_d/scoring
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path


def _score_one(v3_root: str, pred_path: Path, label: str, out_dir: Path):
    from pathway_v43.output.score_report import score_predictions_file

    result = score_predictions_file(
        predictions_path=str(pred_path),
        out_dir=str(out_dir), v3_root=v3_root, label=label)
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arms", nargs="+", required=True,
                    help="label=batch_root 列表(C0 必须在列)")
    ap.add_argument("--v3-root", required=True)
    ap.add_argument("--out-dir", required=True)
    a = ap.parse_args()

    arms = dict(kv.split("=", 1) for kv in a.arms)
    assert "C0" in arms, "配对基线臂 C0 必须在列"
    out_dir = Path(a.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    per_arm = {}
    for label, root in arms.items():
        pred = Path(root) / "merged" / "predictions.jsonl"
        if not pred.is_file():
            print(f"[{label}] merged predictions 缺失:{pred} → 跳过",
                  file=sys.stderr)
            continue
        res = _score_one(a.v3_root, pred, label, out_dir)
        per_arm[label] = res
        print(f"[{label}] cn overall:", json.dumps(
            res["report"]["calibers"]["cn"]["overall"], ensure_ascii=False))

    # ---- 逐题配对(评测器 per_route:list[{route_id, step_hits{1/3/5},...}]) ----
    paired = {}
    for label, res in per_arm.items():
        paired[label] = {rec["route_id"]: rec
                         for rec in res["report"]["calibers"]["cn"]
                         ["per_route"]}

    rows = []
    route_ids = sorted({r for recs in paired.values() for r in recs})
    for rid in route_ids:
        row = {"route_id": rid}
        for label in per_arm:
            rec = paired[label].get(rid)
            if rec is None:
                row[f"{label}_missing"] = True
                row[f"{label}_s1"] = None
                row[f"{label}_s5"] = None
            else:
                row[f"{label}_missing"] = False
                row[f"{label}_s1"] = int(rec["step_hits"]["1"])
                row[f"{label}_s3"] = int(rec["step_hits"]["3"])
                row[f"{label}_s5"] = int(rec["step_hits"]["5"])
                row[f"{label}_recall"] = round(
                    rec.get("route_recall", 0.0), 4)
                row[f"{label}_n_pred"] = rec.get("n_predicted_products")
                row[f"{label}_spurious"] = rec.get("spurious_rate")
        rows.append(row)

    # 配对净赢:题级 win/lose(step_hits@1 差 >0 / <0)+ 步级净差(参考)
    pair_summary = {}
    for label in per_arm:
        if label == "C0":
            continue
        both = [r for r in rows
                if not r.get(f"{label}_missing", True)
                and not r.get("C0_missing", True)]
        win1 = sum(1 for r in both if r[f"{label}_s1"] > r["C0_s1"])
        lose1 = sum(1 for r in both if r[f"{label}_s1"] < r["C0_s1"])
        win5 = sum(1 for r in both if r[f"{label}_s5"] > r["C0_s5"])
        lose5 = sum(1 for r in both if r[f"{label}_s5"] < r["C0_s5"])
        pair_summary[label] = {
            "n_paired": len(both),
            "complete_20_of_20": len(both) == 20,
            "win_at1": win1, "lose_at1": lose1,
            "net_win_at1_questions": win1 - lose1,
            "step_delta_at1": sum(r[f"{label}_s1"] for r in both)
            - sum(r["C0_s1"] for r in both),
            "step_delta_at5": sum(r[f"{label}_s5"] for r in both)
            - sum(r["C0_s5"] for r in both),
            "net_win_at5_questions": win5 - lose5,
        }

    out = {
        "schema_version": "pd-paired-1",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "arms": {k: str(v) for k, v in arms.items()},
        "overall": {label: per_arm[label]["report"]["calibers"]["cn"]
                    ["overall"] for label in per_arm},
        "pair_summary_vs_c0": pair_summary,
        "paired_rows": rows,
    }
    (out_dir / "paired_scoring.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    print(json.dumps(pair_summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
