#!/usr/bin/env python
"""S1 HIT60 E1 发车烟测(单路线,真实付费调用,独立烟测账,≤3 次 LLM 调用)。

与 s1_dev_smoke.py 同底物(pb_0002,E2 烟测已验证该路线命中 rank_candidates
且不在 S1 dev 56 题底物集),但跑 **E1 语义**(rank_candidate_presentation=v2,
base-config = configs/s1_dev_E1.json,不注入 temperature)—— 一次付费烟测
同时验证:连通/计费/usage 记账 + v2 协议通道端到端真实可发:

- 任务书 schema v43-prediction-task-4、分层候选卡、candidate_set 存在;
- 调用产物 system_prompt_sha256 = ranker_v2.md 的 SHA(prompt 开关生效);
- 真实响应按 v2 契约解析成功(select 完整 order / hold 结构化理由;
  解析失败 = 烟测不 ok,不带病发臂 —— E1_DESIGN R1 的最前哨)。

烟测费用与 usage 单独立账,不入任何臂批次账本;烟测结果不用于调整臂配置
(发现问题即停,按 RUN_JOURNAL 处置规则上报)。

用法(远端 dependingv43_s1 内):
  OMP_NUM_THREADS=1 PYTHONPATH=src .venv/bin/python scripts/s1_dev_smoke_e1.py \
      --smoke-root runs/s1_dev_smoke_e1_<ts> \
      --base-config configs/s1_dev_E1.json \
      --dev-questions exam/dev_questions.jsonl \
      --env-file .env
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

SMOKE_ROUTE_ID = "SMOKE_pb_0002_E1"
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
    from pathway_v43.services.prediction import HOLD_KINDS

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
    config["arm"] = "s1_dev_smoke_e1"
    config["batch_root"] = smoke_root.name
    # E1 语义:v2 呈现开关随 base-config 进来;不注入 temperature
    pol = config.setdefault("prediction_policy_overrides", {})
    if pol.get("rank_candidate_presentation") != "v2":
        print(json.dumps({"ok": False,
                          "error": "base-config 非 v2 呈现(用错配置)",
                          "presentation": pol.get(
                              "rank_candidate_presentation")},
                         ensure_ascii=False))
        return 2

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

    # ---- v2 协议通道逐产物审计(烟测核心) ----
    ranker_v2_sha = _sha256_file(Path("configs/prompts/ranker_v2.md"))
    v2_audit = {"n_rank_tasks": 0, "n_v2_schema": 0, "n_layered_cards": 0,
                "n_candidate_set": 0, "n_prompt_sha_v2": 0,
                "n_parse_ok": 0, "parse_fail_kinds": [], "outcomes": []}
    for tp in sorted((smoke_root / "runs").glob(
            "*/results/*/prediction_task.json")):
        task = json.loads(tp.read_text(encoding="utf-8"))["payload"]
        if task.get("mode") != "rank_candidates":
            continue
        v2_audit["n_rank_tasks"] += 1
        if task.get("schema_version") == "v43-prediction-task-4":
            v2_audit["n_v2_schema"] += 1
        if task.get("candidates") and all(
                "engine" in c and "verification" in c
                for c in task["candidates"]):
            v2_audit["n_layered_cards"] += 1
        if (task.get("candidate_set") or {}).get("presentation") == "v2":
            v2_audit["n_candidate_set"] += 1
        d = tp.parent
        for cp in sorted(d.glob("prediction_call.a*.json")):
            payload = json.loads(cp.read_text(encoding="utf-8"))
            payload = payload.get("payload", payload)
            if payload.get("system_prompt_sha256") == ranker_v2_sha:
                v2_audit["n_prompt_sha_v2"] += 1
        pred_p = d / "prediction.json"
        if pred_p.is_file():
            pred = json.loads(pred_p.read_text(encoding="utf-8"))["payload"]
            v2_audit["outcomes"].append(pred.get("outcome", ""))
            if pred.get("outcome") in ("selected", "held"):
                v2_audit["n_parse_ok"] += 1
                if pred.get("outcome") == "held":
                    assert pred["parsed"].get("hold_kind") in HOLD_KINDS
            else:
                v2_audit["parse_fail_kinds"].append(
                    pred.get("fail_reason", "")[:120])

    result = {
        "schema_version": "s1-dev-smoke-e1-1",
        "ok": (totals["n_calls_issued"] <= 3
               and totals["n_usage_missing"] == 0
               and totals["n_orphaned"] == 0
               and v2_audit["n_rank_tasks"] > 0
               and v2_audit["n_v2_schema"] == v2_audit["n_rank_tasks"]
               and v2_audit["n_layered_cards"] == v2_audit["n_rank_tasks"]
               and v2_audit["n_candidate_set"] == v2_audit["n_rank_tasks"]
               and v2_audit["n_prompt_sha_v2"] >= totals["n_calls_issued"]
               and v2_audit["n_parse_ok"] == v2_audit["n_rank_tasks"]),
        "smoke_root": str(smoke_root),
        "terminal_states": summary.get("terminal_states"),
        "n_calls_issued": totals["n_calls_issued"],
        "n_usage_missing": totals["n_usage_missing"],
        "n_orphaned": totals["n_orphaned"],
        "input_tokens": totals["input_tokens"],
        "output_tokens": totals["output_tokens"],
        "cost_estimate_cny": account.get("cost_estimate_cny"),
        "v2_audit": v2_audit,
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
