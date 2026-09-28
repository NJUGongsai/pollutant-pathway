#!/usr/bin/env python
"""dev 对照判分与报告组装(TASK_V43_EXPORT_DEV §4/§6;远端执行,零 LLM)。

步骤:
1. 对 v4.3 批跑归并答卷执行冻结评测器(--split dev --per-route);
2. 对历史基线(v4.1/v4.2 dev 臂)的 per-route predictions.jsonl **复制**
   到新文件、回填 route_id(原答卷 route_id=null,目录名内嵌 route_id),
   以同一冻结评测器判分(不修改历史仓任何文件);
3. 组装对照报告 JSON + Markdown(cn 主口径 + raw_sb 对照、S/M/D 分层、
   逐路线状态、API/费用账、失分归因、基线可比性限定、协议两项披露)。

用法:
    OMP_NUM_THREADS=1 PYTHONPATH=src python scripts/build_dev_report.py \
        --batch-root <batch_root> --v3-root <dependingv3> \
        --baseline hyb_v42fix=<path/to/dev_hybrid_v42fix> \
        --baseline llm_mc_v41=<path/to/dev_llm_mc_v41> \
        --out-dir <batch_root>/report
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch-root", required=True)
    ap.add_argument("--v3-root", required=True)
    ap.add_argument("--baseline", action="append", default=[],
                    help="label=path/to/dev_runs_dir(可多次)")
    ap.add_argument("--out-dir", required=True)
    a = ap.parse_args()

    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    from pathway_v43.batch import api_account
    from pathway_v43.output.score_report import (
        build_dev_diagnostic_report,
        run_frozen_evaluator,
        score_predictions_file,
    )

    batch_root = Path(a.batch_root)
    out_dir = Path(a.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    merged = batch_root / "merged" / "predictions.jsonl"
    identity = json.loads((batch_root / "batch_identity.json").read_text())
    config = identity["identity"]["config"]

    # ---- 1. v4.3 主答卷判分 ----
    eval_v43 = run_frozen_evaluator(
        a.v3_root, merged, out_dir / "eval_v43_dev.json", split="dev")

    # ---- 2. 历史基线判分(同评测器同 split;回填 route_id)----
    baselines = {}
    for spec in a.baseline:
        label, _, src = spec.partition("=")
        src_dir = Path(src)
        rows = []
        for run_dir in sorted(src_dir.iterdir()):
            pf = run_dir / "predictions.jsonl"
            if not pf.is_file():
                continue
            m = re.search(r"(pb_\d+)$", run_dir.name)
            if not m:
                continue
            try:
                rec = json.loads(pf.read_text(encoding="utf-8"))
            except Exception:
                continue
            rec["route_id"] = m.group(1)
            rows.append(rec)
        if not rows:
            baselines[label] = {"status": "not_available",
                                "note": f"no per-route predictions in {src}"}
            continue
        bl_path = out_dir / f"baseline_{label}.predictions.jsonl"
        bl_path.write_text("".join(
            json.dumps(r, ensure_ascii=False, sort_keys=True,
                       separators=(",", ":")) + "\n" for r in rows),
            encoding="utf-8")
        report = run_frozen_evaluator(
            a.v3_root, bl_path, out_dir / f"eval_baseline_{label}.json",
            split="dev", allow_missing=True)
        if label.startswith("v43_"):
            note = ("v4.3 supplementary ablation: same model/architecture, "
                    "smaller budget regime (max_depth=3/max_expansions=24)")
        else:
            note = ("historical arm: different model/architecture/budget "
                    "regime; reference only, NOT directly comparable")
        baselines[label] = {
            "status": "scored_with_caveats",
            "n_answer_lines": len(rows),
            "n_dev_routes": 20,
            "missing": report.get("missing_predictions", []),
            "note": note,
            "cn_overall": report["calibers"]["cn"]["overall"],
            "raw_sb_overall": report["calibers"]["raw_sb"]["overall"],
        }

    # ---- 3. 诊断 + 账目 + worker 进程证据 ----
    manifest = json.loads((batch_root / "input_manifest.json").read_text())
    route_run_ids = {}
    for rid in manifest["route_order"]:
        run_id = f"dev_{identity['short']}_{rid}"
        route_run_ids[rid] = run_id
    merged_meta = json.loads((batch_root / "merged" / "export_metadata.json")
                             .read_text())
    account = api_account(
        batch_root / "runs", list(route_run_ids.values()),
        price_snapshot=config.get("provider_price_snapshot"))
    diag = build_dev_diagnostic_report(
        eval_report=eval_v43, v3_root=a.v3_root, runs_root=batch_root / "runs",
        route_run_ids=route_run_ids, merged_meta=merged_meta,
        api_account_data=account)

    # worker 进程与时间证据(协调器日志;PID/route_id/启停)
    worker_events = []
    clog = batch_root / "coordinator.log"
    if clog.is_file():
        for line in clog.read_text(encoding="utf-8").splitlines():
            if "spawn " in line or "worker done" in line or \
                    "respawn" in line or "failure status" in line:
                worker_events.append(line)
    report = {
        "schema_version": "v43-export-dev-report-1",
        "batch": {"sha256": identity["sha256"], "short": identity["short"],
                  "config": config, "model": identity["identity"]["model"]},
        "eval_v43": {
            "cn_overall": eval_v43["calibers"]["cn"]["overall"],
            "raw_sb_overall": eval_v43["calibers"]["raw_sb"]["overall"],
            "cn_by_stratum": eval_v43["calibers"]["cn"]["by_stratum"],
            "raw_sb_by_stratum": eval_v43["calibers"]["raw_sb"]["by_stratum"],
            "n_routes": eval_v43["n_routes"],
        },
        "per_route_status": merged_meta.get("per_route", []),
        "worker_evidence": {
            "n_spawn_events": sum(1 for e in worker_events
                                  if " spawn " in e),
            "events": worker_events,
        },
        "baselines": baselines,
        "diagnostics": diag,
        "api_account": account,
        "protocol_caveats": [
            "Corpus-graph assembly: every gold edge carries its own "
            "btid#reac_id evidence, but whole-route experimental validity is "
            "NOT verified (A->B and B->C may come from different "
            "experiments). Mirrors how the engine consumes the same data.",
            "Public EAWAG/enviPath data may be in the model's pretraining "
            "corpus, and the v4.3 retrieval assets share provenance with the "
            "dev gold routes; dev metrics measure path/ranking performance "
            "on this benchmark, NOT environmental generalization.",
            "External 298 single-step results are a different metric class "
            "and must not be merged into pathway percentages.",
        ],
    }
    (out_dir / "export_dev_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "report": str(out_dir / "export_dev_report.json"),
                      "cn_overall": report["eval_v43"]["cn_overall"]},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
