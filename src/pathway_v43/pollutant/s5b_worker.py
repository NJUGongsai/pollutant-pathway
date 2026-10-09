"""S5b worker —— 一题一进程的 PPV1 run 执行入口(编排器子进程)。

``python -m pathway_v43.pollutant.s5b_worker --batch-root R --runs-root
D --qid Q``(由 s5b_orchestrator 派生;OMP_NUM_THREADS=1)。

职责:

- 装配批根冻结的 profile_policy(单步预算;十上限 + 格式反馈策略);
- 装配 RealModelAdapter(凭证只从 env ``V43_LLM_*``;调用账本落
  run 目录);
- run 不存在 ⇒ ``start_ppv1_run``;已存在 ⇒ ``resume_ppv1_run``
  (幂等续跑;身份核对/冻结计划/恢复全走公共链);
- 结束(成功或失败)落终态 case 文件 ``cases/<qid>.json``:
  stop_reason/endpoint 四分账/export_digest/模型调用与 usage 汇总
  (从 ledger model_requests 表与调用账本复算,不信内存);
- worker 自身不判分、不碰金标(金标只在 s5b_scoring 判分进程)。

崩溃语义:进程死亡 ⇒ 无 case 文件 ⇒ 编排器记失败补位(留分母);
重跑同批 ⇒ resume 续跑(B1–B4 公共恢复)。
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

S5B_WORKER_VERSION = "s5b-worker-1"


def worker_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="s5b_worker")
    parser.add_argument("--batch-root", required=True)
    parser.add_argument("--runs-root", required=True)
    parser.add_argument("--qid", required=True)
    parser.add_argument("--fail-fast-env-check", action="store_true",
                        help="只做凭证存在性检查(冒烟段 0 前置)")
    args = parser.parse_args(argv)
    batch_root = Path(args.batch_root)
    runs_root = Path(args.runs_root)
    qid = str(args.qid)
    sys.path.insert(0, str(_repo_src_path(batch_root)))

    from pathway_v43.config import resolve_config
    from pathway_v43.pollutant.real_model import (
        RealModelAdapter,
        RealModelNotConfigured,
        S5B_CALL_ACCOUNT_FILE,
    )
    from pathway_v43.pollutant.runflow import (
        PPV1RunError,  # noqa: F401 —— 失败包装的公共类型(文档性导入)
        resume_ppv1_run,
        start_ppv1_run,
    )
    from pathway_v43.workflow.runner import RunAlreadyExists  # noqa: F401

    run_input = json.loads(
        (batch_root / "run_inputs" / f"{qid}.json").read_text(
            encoding="utf-8"))
    run_id = str(run_input["run_id"])
    plan = dict(run_input.get("plan") or {})
    profile_policy = json.loads(
        (batch_root / "profile_policy.json").read_text(encoding="utf-8"))
    import os

    stub_path = os.environ.get("S5B_MODEL_STUB_SCRIPT")
    if stub_path:
        # scripted 模型桩(测试/冒烟:与真实适配器同一取响应调用序;
        # provider_kind 按 plan 注册 ⇒ scripted 网络 0、不占真实额度;
        # 不冒充在线模型验证)
        from pathway_v43.pollutant.real_model import (
            S5B_CALL_ACCOUNT_FILE,
            ScriptedRealModelAdapter,
        )

        stub = json.loads(Path(stub_path).read_text(encoding="utf-8"))
        model = ScriptedRealModelAdapter(
            strategy=str(stub.get("strategy") or "first_pool"),
            responses=[str(r) for r in (stub.get("responses") or [])],
            fail_with=dict(stub.get("fail_with") or {}),
            call_account_path=runs_root / run_id / S5B_CALL_ACCOUNT_FILE)
    else:
        from pathway_v43.pollutant.real_model import (
            RealModelAdapter,
            RealModelNotConfigured,
            S5B_CALL_ACCOUNT_FILE,
        )

        try:
            model = RealModelAdapter.from_env(
                call_account_path=runs_root / run_id /
                S5B_CALL_ACCOUNT_FILE)
        except RealModelNotConfigured as exc:
            _write_case(batch_root, {
                "qid": qid, "run_id": run_id, "status": "failed",
                "failure_kind": "model_not_configured",
                "error": str(exc), "detail": dict(exc.detail),
            })
            return 2
    if args.fail_fast_env_check:
        _write_case(batch_root, {
            "qid": qid, "run_id": run_id, "status": "completed",
            "stop_reason": "env_check_only",
            "note": "仅凭证存在性检查(worker --fail-fast-env-check)",
        })
        return 0
    config = resolve_config()
    run_dir = runs_root / run_id
    try:
        if (run_dir / "run_identity.json").is_file():
            summary = resume_ppv1_run(
                config=config, runs_root=runs_root, run_id=run_id,
                model=model, profile_policy=None)
        else:
            summary = start_ppv1_run(
                config=config, runs_root=runs_root, run_id=run_id,
                smiles=str(run_input["substrate_smiles"]), plan=plan,
                model=model, profile_policy=profile_policy)
    except RunAlreadyExists as exc:  # 并发同 run 罕见:失败补位
        _write_case(batch_root, {
            "qid": qid, "run_id": run_id, "status": "failed",
            "failure_kind": "run_already_exists",
            "error": str(exc)[:300],
        })
        return 3
    except Exception as exc:  # noqa: BLE001 —— 失败题留分母,如实记录
        # 任何 run 级失败:失败题留分母;如实记录结构化原因
        detail = dict(getattr(exc, "detail", {}) or {})
        _write_case(batch_root, {
            "qid": qid, "run_id": run_id, "status": "failed",
            "failure_kind": str(detail.get("kind") or
                                type(exc).__name__),
            "error": f"{type(exc).__name__}: {exc}"[:400],
            "model_calls": _count_model_calls(run_dir),
            "usage": _usage_summary(run_dir),
        })
        return 4
    _write_case(batch_root, {
        "qid": qid,
        "run_id": run_id,
        "status": "completed",
        "stop_reason": str(summary.get("stop_reason") or ""),
        "run_error": dict(
            (summary.get("stop") or {}).get("run_error") or {}),
        "endpoint": dict(summary.get("endpoint") or {}),
        "endpoint_status": str(
            (summary.get("endpoint") or {}).get("status") or ""),
        "export_digest": str(
            (summary.get("native_export") or {}).get("export_digest")
            or ""),
        "counts": dict(summary.get("counts") or {}),
        "model_calls": _count_model_calls(run_dir),
        "usage": _usage_summary(run_dir),
    })
    return 0


def _repo_src_path(batch_root: Path) -> Path:
    """仓 src 路径(worker 与 src 同仓部署;沿 tests 惯例插入)。"""
    return Path(__file__).resolve().parents[2]


def _count_model_calls(run_dir: Path) -> int:
    db = run_dir / "pollutant.sqlite"
    if not db.is_file():
        return 0
    try:
        conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        try:
            row = conn.execute(
                "SELECT COUNT(*) FROM model_requests").fetchone()
            return int(row[0] or 0)
        finally:
            conn.close()
    except sqlite3.Error:
        return 0


def _usage_summary(run_dir: Path) -> dict:
    """从逐调用账本复算 usage(known 小计;缺 usage 保守预留)。"""
    path = run_dir / "s5b_real_calls.jsonl"
    summary = {"present": False, "input_tokens": 0, "output_tokens": 0,
               "total_tokens": 0, "calls_with_usage": 0,
               "calls_without_usage": 0}
    if not path.is_file():
        return summary
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            text = line.strip()
            if not text:
                continue
            record = json.loads(text)
            status = str(record.get("status") or "")
            if status not in ("responded", "failed"):
                continue
            usage = record.get("usage") or {}
            if usage:
                summary["present"] = True
                summary["calls_with_usage"] += 1
                summary["input_tokens"] += int(
                    usage.get("input_tokens") or 0)
                summary["output_tokens"] += int(
                    usage.get("output_tokens") or 0)
                summary["total_tokens"] += int(
                    usage.get("total_tokens") or 0)
            else:
                summary["calls_without_usage"] += 1
    except (ValueError, OSError):
        return summary
    return summary


def _write_case(batch_root: Path, payload: dict) -> None:
    from pathway_v43.domain.models import now_iso

    path = batch_root / "cases" / f"{payload['qid']}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload["worker_version"] = S5B_WORKER_VERSION
    payload["recorded_at"] = now_iso()
    path.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True,
                   indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":  # pragma: no cover —— 子进程入口
    raise SystemExit(worker_main())
