#!/usr/bin/env python
"""S1 HIT60 发车烟测(单路线,真实付费调用,独立烟测账,≤3 次 LLM 调用)。

设计:合成底物(pb_0002 root_smiles,v3 基准 dev 路线,Phase D 烟测 r2 已用,
其原串与 cn 身份均不在 298 题底物集;本脚本再核其不在 S1 dev 56 题底物集),
**E2 语义**(temperature=0.0)单路线跑 run_exam_agent —— 一次付费烟测同时验证:
连通/计费/usage 记账 + 温度通道真实可发(装配期 fail-closed 只拦已知不支持
名单,提供方是否接受 temperature 须实测;若 API 400,烟测即暴露,不带病发臂)。

烟测费用与 usage 单独立账,不入任何臂批次账本;烟测结果不用于调整臂配置
(发现问题即停,按 RUN_JOURNAL 处置规则上报)。

用法(远端 dependingv43_s1 内):
  OMP_NUM_THREADS=1 PYTHONPATH=src .venv/bin/python scripts/s1_dev_smoke.py \
      --smoke-root runs/s1_dev_smoke_<ts> \
      --base-config configs/s1_dev_E2.json \
      --dev-questions exam/dev_questions.jsonl \
      --env-file .env
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

SMOKE_ROUTE_ID = "SMOKE_pb_0002"
SMOKE_SMILES = "C#CC(C)(C)NC(=O)C1=CC(=CC(=C1)Cl)Cl"


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke-root", required=True)
    ap.add_argument("--base-config", required=True)
    ap.add_argument("--dev-questions", required=True)
    ap.add_argument("--env-file", required=True)
    args = ap.parse_args()

    from pathway_v43.domain.identity import cn_identity

    # 底物隔离核对:烟测底物原串与 cn 身份都不得出现在 dev 56 题
    dev_roots = []
    dev_cns = set()
    for line in Path(args.dev_questions).read_text(
            encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        dev_roots.append(rec["root_smiles"])
        ident = cn_identity(rec["root_smiles"])
        if ident:
            dev_cns.add(ident)
    smoke_cn = cn_identity(SMOKE_SMILES)
    if SMOKE_SMILES in dev_roots or smoke_cn in dev_cns:
        print(json.dumps({"ok": False,
                          "error": "烟测底物与 dev 题卷重叠(换底物)"},
                         ensure_ascii=False))
        return 2

    smoke_root = Path(args.smoke_root).resolve()
    smoke_root.mkdir(parents=True, exist_ok=True)
    exam_inputs = smoke_root / "exam_inputs.jsonl"
    row = {"input_index": 0, "qid": SMOKE_ROUTE_ID,
           "substrate_smiles": SMOKE_SMILES}
    exam_inputs.write_text(
        json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8")

    config = json.loads(Path(args.base_config).read_text(encoding="utf-8"))
    config["arm"] = "s1_dev_smoke"
    config["batch_root"] = smoke_root.name
    config.setdefault("prediction_policy_overrides", {})
    config["prediction_policy_overrides"]["temperature"] = 0.0

    from pathway_v43.exam import run_exam_agent
    summary = run_exam_agent(
        batch_root=smoke_root, exam_inputs_path=exam_inputs,
        runs_root=smoke_root / "runs", config=config, model_choice="real",
        env_file=args.env_file, workers=1, max_in_flight=1)
    (smoke_root / "_agent_run_result.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n", encoding="utf-8")
    if summary.get("status", "").startswith("not_run"):
        print(json.dumps({"ok": False, "status": summary.get("status")},
                         ensure_ascii=False))
        return 2

    from pathway_v43.batch import api_account
    identity = json.loads((smoke_root / "batch_identity.json").read_text(
        encoding="utf-8"))
    account = api_account(smoke_root / "runs", summary["run_ids"],
                          price_snapshot=config["provider_price_snapshot"])
    totals = account["totals"]

    # 温度通道逐调用留痕核对:E2 语义下每条 prediction_call 应带
    # "temperature": 0.0(节点层审计字段);响应应 transport ok
    n_calls_with_temp = 0
    n_calls_total = 0
    for rp in sorted((smoke_root / "runs").glob(
            "*/results/*/prediction_call.a*.json")):
        n_calls_total += 1
        payload = json.loads(rp.read_text(encoding="utf-8"))
        if payload.get("payload", payload).get("temperature") == 0.0:
            n_calls_with_temp += 1
    result = {
        "schema_version": "s1-dev-smoke-1",
        "ok": (totals["n_calls_issued"] <= 3
               and totals["n_usage_missing"] == 0
               and totals["n_orphaned"] == 0
               and (n_calls_with_temp == n_calls_total)),
        "smoke_root": str(smoke_root),
        "terminal_states": summary.get("terminal_states"),
        "n_calls_issued": totals["n_calls_issued"],
        "n_usage_missing": totals["n_usage_missing"],
        "n_orphaned": totals["n_orphaned"],
        "input_tokens": totals["input_tokens"],
        "output_tokens": totals["output_tokens"],
        "cost_estimate_cny": account.get("cost_estimate_cny"),
        "cost_estimate_known_usage_cny": account.get(
            "cost_estimate_known_usage_cny"),
        "temperature_audit": {"n_calls": n_calls_total,
                              "n_calls_with_temperature_0": n_calls_with_temp},
        "batch_short": identity["short"],
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    out = smoke_root / "_smoke_summary.json"
    out.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
