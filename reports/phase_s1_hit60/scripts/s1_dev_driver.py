"""S1 HIT60 dev 三臂 driver(C0 基线 / E2 温度 / E3 窗口)。

跑在 Chenyu 隔离工作区 dependingv43_s1 内;位于 src/ 之外(不进代码身份)。
复刻样板 runs/ec298_pd_retest_pre/ec298_pd_retest_driver.py,差异:

- 输入换 S1 冻结 dev 题卷(qid/root_smiles/root_smiles_sha256 三字段),
  运行侧先做**白名单口径转换** → exam_inputs.jsonl
  (input_index/qid/substrate_smiles 三字段,与 exam.load_exam_inputs
  的白名单校验逐字段一致;root_smiles_sha256 逐行核对后不随运行侧流转,
  由 _exam_manifest 自行重算);
- 装配带 prediction_policy(E2 温度开关进 worker 同一通道;不支持温度
  的模型装配期 fail-closed);
- workers/max_in_flight = 20(三臂同值,与配置 max_parallel 一致)。

三段:

  --phase identity : 转换白名单 + manifest + batch identity,零 API 调用。
  --phase run      : 身份一致性核验后 run_exam_agent 跑到全部终态
                     (幂等 resume;已持久化响应绝不重发)。
  --phase post     : 归并 + 终态分类 + API 账目 + 在途证据 + 配对门禁。

用法(远端 dependingv43_s1 内):
  OMP_NUM_THREADS=1 PYTHONPATH=src .venv/bin/python scripts/s1_dev_driver.py \
      --arm-root runs/s1_dev_C0_<UTC时间戳> \
      --config configs/s1_dev_C0.json \
      --dev-questions exam/dev_questions.jsonl \
      --env-file .env \
      --phase identity|run|post
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

FROZEN_DEV_QUESTIONS_SHA256 = (
    "8869cd05cea1a44220f3001f0b6415c6bf97eb5f0122ebc4609aa1c77ab0360c")

# 与 phase run 传给 run_exam_agent 的值一致(三臂同值,不得单独调;
# 该值随 config 进 batch identity,identity 段必须同值预置)
S1_WORKERS = 20
S1_MAX_IN_FLIGHT = 20


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _emit(obj: dict, out: str | None) -> None:
    text = json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True)
    if out and out != "-":
        Path(out).write_text(text + "\n", encoding="utf-8")
    print(text)


def _convert_dev_questions(dev_questions: Path, out_path: Path) -> dict:
    """冻结 dev 题卷 → 运行侧三字段白名单(一次性;fail-closed)。

    dev 行字段恰为 qid/root_smiles/root_smiles_sha256(无任何金标字段);
    输出行恰为 input_index/qid/substrate_smiles(exam.load_exam_inputs
    的白名单口径)。逐行核对 sha256(root_smiles) == root_smiles_sha256
    后,原 sha 字段不进运行侧文件(_exam_manifest 会自行重算同值)。
    """
    rows = []
    seen: set[str] = set()
    for idx, line in enumerate(dev_questions.read_text(
            encoding="utf-8").splitlines()):
        if not line.strip():
            continue
        rec = json.loads(line)
        if set(rec) != {"qid", "root_smiles", "root_smiles_sha256"}:
            raise SystemExit(json.dumps({
                "ok": False, "error": "dev 题卷行字段越界(fail-closed)",
                "index": idx, "row_keys": sorted(rec)}, ensure_ascii=False))
        qid = rec["qid"]
        if not qid or qid in seen:
            raise SystemExit(json.dumps({
                "ok": False, "error": "qid 缺失或重复", "index": idx,
                "qid": qid}, ensure_ascii=False))
        seen.add(qid)
        digest = hashlib.sha256(
            rec["root_smiles"].encode("utf-8")).hexdigest()
        if digest != rec["root_smiles_sha256"]:
            raise SystemExit(json.dumps({
                "ok": False, "error": "root_smiles_sha256 不符(fail-closed)",
                "index": idx, "qid": qid}, ensure_ascii=False))
        rows.append({"input_index": idx, "qid": qid,
                     "substrate_smiles": rec["root_smiles"]})
    if len(rows) != 56:
        raise SystemExit(json.dumps({
            "ok": False, "error": "dev 题卷非 56 行",
            "n": len(rows)}, ensure_ascii=False))
    tmp = out_path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
    tmp.replace(out_path)
    return {"n_rows": len(rows),
            "exam_inputs_sha256": _sha256_file(out_path)}


def phase_identity(args) -> int:
    from pathway_v43.batch import batch_identity_conflict_check, load_env_file
    from pathway_v43.adapters.llm_client import (
        real_provider_env, resolve_model_setup,
    )
    from pathway_v43.output.export_v3 import load_export_policy
    from pathway_v43.domain.policy import prediction_policy

    arm_root = Path(args.arm_root).resolve()
    arm_root.mkdir(parents=True, exist_ok=True)
    dev_questions = Path(args.dev_questions).resolve()
    actual = _sha256_file(dev_questions)
    if actual != FROZEN_DEV_QUESTIONS_SHA256:
        print(json.dumps({
            "ok": False, "phase": "identity",
            "error": "dev_questions SHA mismatch (fail-closed)",
            "expected": FROZEN_DEV_QUESTIONS_SHA256, "actual": actual,
        }, ensure_ascii=False))
        return 2
    exam_inputs = arm_root / "exam_inputs.jsonl"
    conv = {"n_rows": 56, "exam_inputs_sha256": _sha256_file(exam_inputs)} \
        if exam_inputs.is_file() else _convert_dev_questions(
            dev_questions, exam_inputs)

    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    if args.env_file:
        import os
        os.environ.update(load_env_file(args.env_file))
    env = real_provider_env()
    missing = [k for k, ok in (
        ("V43_LLM_BASE_URL", env["base_url_set"]),
        ("V43_LLM_API_KEY", env["api_key_set"]),
        ("V43_LLM_MODEL", env["model_set"]),
    ) if not ok]
    if missing:
        print(json.dumps({"ok": False, "phase": "identity",
                          "error": "missing env", "missing": missing},
                         ensure_ascii=False))
        return 2
    setup = resolve_model_setup(
        "openai_compatible",
        request_params=config["model_request_params"],
        timeout_s=config["llm_timeout_s"],
        policy=prediction_policy(config.get("prediction_policy_overrides")))
    required = (config.get("provider_price_snapshot") or {}).get("model_id")
    if not required:
        print(json.dumps({"ok": False, "phase": "identity",
                          "error": "provider_price_snapshot 未回填(不得发车)"},
                         ensure_ascii=False))
        return 2
    if setup.model_id != required:
        print(json.dumps({"ok": False, "phase": "identity",
                          "error": "model_id mismatch",
                          "required": required, "actual": setup.model_id},
                         ensure_ascii=False))
        return 2

    from pathway_v43.exam import EXAM_SPLIT_NAME, _exam_manifest, load_exam_inputs
    from pathway_v43.batch import build_batch_identity
    rows = load_exam_inputs(exam_inputs)
    manifest = _exam_manifest(rows, conv["exam_inputs_sha256"])
    manifest_path = arm_root / "input_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n", encoding="utf-8")
    export_policy = load_export_policy(
        config.get("export_policy_overrides") or {})
    config = json.loads(json.dumps(config))
    config["rate"]["max_in_flight"] = S1_MAX_IN_FLIGHT
    model_block = {"provider": "openai_compatible",
                   "model_id": setup.model_id,
                   "request_params": dict(setup.request_params),
                   "timeout_s": float(setup.timeout_s)}
    identity = build_batch_identity(
        split=EXAM_SPLIT_NAME, input_manifest_path=manifest_path,
        config=config, provider=model_block["provider"],
        model_id=model_block["model_id"],
        request_params=model_block["request_params"],
        timeout_s=model_block["timeout_s"],
        export_policy=export_policy)
    batch_identity_conflict_check(arm_root, identity)
    (arm_root / "batch_identity.json").write_text(
        json.dumps(identity, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n", encoding="utf-8")
    _emit({
        "ok": True, "phase": "identity", "arm_root": str(arm_root),
        "batch_sha256": identity["sha256"], "batch_short": identity["short"],
        "n_questions": len(rows),
        "dev_questions_sha256": actual,
        "exam_inputs_sha256": conv["exam_inputs_sha256"],
        "model_id": setup.model_id,
    }, str(arm_root / "_identity_phase.json"))
    return 0


def phase_run(args) -> int:
    from pathway_v43.exam import run_exam_agent

    arm_root = Path(args.arm_root).resolve()
    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    summary = run_exam_agent(
        batch_root=arm_root,
        exam_inputs_path=arm_root / "exam_inputs.jsonl",
        runs_root=arm_root / "runs",
        config=config, model_choice="real",
        env_file=args.env_file,
        workers=S1_WORKERS, max_in_flight=S1_MAX_IN_FLIGHT)
    _emit(summary, str(arm_root / "_agent_run_result.json"))
    return 0 if summary.get("status") not in (
        "not_run:no_credentials_or_access", "not_run:model_id_mismatch") else 2


def phase_post(args) -> int:
    from pathway_v43.batch import (
        api_account, batch_terminal_summary, load_input_manifest,
        merge_predictions_terminal, run_id_for_route,
    )
    from pathway_v43.exam import inflight_evidence
    from pathway_v43.output.export_v3 import load_export_policy
    from pathway_v43.output.pairing_gate import validate_arm

    arm_root = Path(args.arm_root).resolve()
    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    manifest = load_input_manifest(arm_root / "input_manifest.json")
    identity = json.loads(
        (arm_root / "batch_identity.json").read_text(encoding="utf-8"))
    export_policy = load_export_policy(
        config.get("export_policy_overrides") or {})

    merged = merge_predictions_terminal(
        batch_root=arm_root, manifest=manifest, config=config,
        export_policy=export_policy)
    route_ids = list(manifest["route_order"])
    run_ids = [run_id_for_route(identity["short"], manifest["split"], rid)
               for rid in route_ids]
    runs_root = arm_root / "runs"
    terminal = {}
    for rid in route_ids:
        sp = arm_root / "workers" / f"{rid}.status.json"
        if sp.is_file():
            terminal[rid] = json.loads(sp.read_text(encoding="utf-8"))
    terminal_summary = batch_terminal_summary(route_ids, terminal)
    account = api_account(
        runs_root, run_ids,
        price_snapshot=config.get("provider_price_snapshot"))
    inflight = inflight_evidence(runs_root, run_ids)
    gate = validate_arm(arm_root, expected_route_ids=route_ids)
    result = {
        "schema_version": "s1-dev-arm-summary-1",
        "arm_root": str(arm_root),
        "arm": config.get("arm"),
        "batch_sha256": identity["sha256"],
        "batch_short": identity["short"],
        "model_id": (config.get("provider_price_snapshot") or {})
        .get("model_id"),
        "n_routes": len(route_ids),
        "terminal_summary": terminal_summary,
        "merged": {k: v for k, v in merged.items() if k != "per_route"},
        "api_account_totals": account["totals"],
        "cost_estimate_cny": account.get("cost_estimate_cny"),
        "cost_estimate_known_usage_cny": account.get(
            "cost_estimate_known_usage_cny"),
        "conservative_reservation": account.get("conservative_reservation"),
        "price_snapshot_checked": (config.get("provider_price_snapshot")
                                   or {}).get("checked"),
        "inflight": {k: v for k, v in inflight.items() if k != "requests"},
        "pairing_gate": gate,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    out = arm_root / "_arm_summary.json"
    out.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n", encoding="utf-8")
    print(json.dumps({
        "ok": True, "phase": "post", "arm_root": str(arm_root),
        "arm": config.get("arm"),
        "batch_terminal_status": terminal_summary["status"],
        "n_valid_terminal": terminal_summary["n_valid_terminal"],
        "n_failed": terminal_summary["n_failed"],
        "n_export_failed": terminal_summary["n_export_failed"],
        "n_missing": terminal_summary["n_missing"],
        "pairing_gate_ok": gate["ok"],
        "cost_estimate_cny": result["cost_estimate_cny"],
        "n_calls_issued": account["totals"]["n_calls_issued"],
        "n_usage_missing": account["totals"]["n_usage_missing"],
        "n_orphaned": account["totals"]["n_orphaned"],
        "summary_path": str(out),
    }, ensure_ascii=False))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm-root", required=True)
    ap.add_argument("--config", required=True)
    ap.add_argument("--dev-questions", required=True)
    ap.add_argument("--env-file", default=None)
    ap.add_argument("--phase", required=True,
                    choices=["identity", "run", "post"])
    args = ap.parse_args()
    if args.phase == "identity":
        return phase_identity(args)
    if args.phase == "run":
        return phase_run(args)
    return phase_post(args)


if __name__ == "__main__":
    raise SystemExit(main())
