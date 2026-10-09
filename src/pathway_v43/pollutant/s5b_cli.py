"""S5b 运行时 CLI —— 构建/发车/判分的远端操作入口(主会话/运维用)。

用法(Chenyu 部署;详见交付书 runbook):

```
python -m pathway_v43.pollutant.s5b_cli build \
    --questions <questions.jsonl> --batch-root <批根> [--pool-mode template]
python -m pathway_v43.pollutant.s5b_cli approve \
    --batch-root <批根> --preregistration-id prereg-s5b-2026-10-09
python -m pathway_v43.pollutant.s5b_cli price \
    --batch-root <批根> --input-per-mtok 0.8 --output-per-mtok 2.8
python -m pathway_v43.pollutant.s5b_cli run \
    --batch-root <批根> --runs-root <run根> [--env-file <env>] \
    [--workers 40] [--limit 10] [--gate-max-calls 894]
python -m pathway_v43.pollutant.s5b_cli score \
    --batch-root <批根> --runs-root <run根>
```

- build:题卷 → 参考图 + run 输入 + 清单(金标承载物只进 gitignored
  根,由 s5b_builder.check_output_root 守卫);
- approve:落预注册批准记录(发车硬门:主会话在用户确认读后执行;
  状态行已 confirmed 的冻结稿可免本步——score 侧按状态行兜底);
- price:落当日价格快照(元/Mtok;缺快照 ⇒ 费用不计价,如实报);
- run:40 路编排(断点续跑;已完成 qid SKIP;进度轮询看
  <批根>/progress.json);
- score:封存答卷后的零 LLM 判分(金标此时进判分进程;双口径报告)。

全部子命令的输出 JSON 都不含密钥/金标取值。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from pathway_v43.pollutant.s5b_builder import (  # noqa: E402
    build_question_batch,
    default_pool_provider,
)
from pathway_v43.pollutant.s5b_orchestrator import (  # noqa: E402
    S5B_DEFAULT_GATE_MAX_CALLS,
    S5B_DEFAULT_WORKERS,
    run_s5b_batch,
    summarize_batch,
)
from pathway_v43.pollutant.s5b_scoring import (  # noqa: E402
    preregistration_from_doc,
    score_s5b_batch,
)


def _emit(payload: dict) -> None:
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))


def cmd_build(args: argparse.Namespace) -> int:
    from pathway_v43.config import resolve_config

    pool_provider = None
    if args.pool_mode == "template":
        pool_provider = default_pool_provider(
            resolve_config(args.v3_code_root, args.assets_root),
            max_pool=args.max_pool, threshold=args.pool_threshold)
    manifest = build_question_batch(
        args.questions, args.batch_root, batch_tag=args.batch_tag,
        pool_provider=pool_provider,
        provider_kind=args.provider_kind,
        question_limit=args.limit)
    _emit({
        "command": "build", "ok": True,
        "batch_root": str(Path(args.batch_root).resolve()),
        "n_questions": manifest["n_questions"],
        "questions_source_sha256": manifest["questions_source_sha256"],
        "registration_order_head": manifest["registration_order"][:5],
        "pool_mode": args.pool_mode,
    })
    return 0


def cmd_approve(args: argparse.Namespace) -> int:
    doc = preregistration_from_doc()
    record = {
        "preregistration_id": args.preregistration_id,
        "approval_status": args.approval_status,
        "approved_at": _now_iso(),
        "user_authorization": args.user_authorization,
        "preregistration_doc_status": (
            doc or {}).get("approval_status") or "doc_not_found",
    }
    path = Path(args.batch_root) / "preregistration_approval.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, ensure_ascii=False, sort_keys=True,
                                indent=1) + "\n", encoding="utf-8")
    _emit({"command": "approve", "ok": True, "path": str(path),
           "record": {k: v for k, v in record.items()}})
    return 0


def cmd_price(args: argparse.Namespace) -> int:
    path = Path(args.batch_root) / "price_snapshot.json"
    record = {
        "input_per_mtok": float(args.input_per_mtok),
        "output_per_mtok": float(args.output_per_mtok),
        "cached_input_per_mtok": (
            float(args.cached_input_per_mtok)
            if args.cached_input_per_mtok is not None else None),
        "currency": args.currency,
        "recorded_at": _now_iso(),
        "note": ("发车当日价格快照(预注册 #16:价格用发车当日值;"
                 "缺快照 ⇒ 费用不计价,如实报)"),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, ensure_ascii=False, sort_keys=True,
                                indent=1) + "\n", encoding="utf-8")
    _emit({"command": "price", "ok": True, "path": str(path)})
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    report = run_s5b_batch(
        args.batch_root, runs_root=args.runs_root,
        env_file=args.env_file, workers=args.workers,
        max_in_flight=args.max_in_flight,
        gate_rpm=args.gate_rpm, gate_tpm=args.gate_tpm,
        gate_max_calls=args.gate_max_calls,
        question_limit=args.limit,
        qids=[q for q in args.qids.split(",") if q] if args.qids else None,
        poll_s=args.poll_s, python_bin=args.python_bin)
    _emit({
        "command": "run", "ok": True,
        "n_total": report["n_total"], "n_completed": report["n_completed"],
        "n_failed": report["n_failed"],
        "n_pending": report["n_pending"],
        "gate": report.get("gate"),
        "account": report.get("account"),
        "batch_report": str(Path(args.batch_root) / "batch_report.json"),
    })
    return 0


def cmd_score(args: argparse.Namespace) -> int:
    aggregate = score_s5b_batch(
        args.batch_root, runs_root=args.runs_root,
        data_scope=args.data_scope)
    _emit({
        "command": "score", "ok": True,
        "status": aggregate.get("evaluator_output_status"),
        "denominator": aggregate["denominator"],
        "main_caliber": {k: aggregate["main_caliber"][k]
                         for k in ("hit@1", "hit@3", "hit@5")},
        "old_caliber_sensitivity": {
            k: aggregate["old_caliber_sensitivity"][k]
            for k in ("hit@1", "hit@3", "hit@5")},
        "buckets": aggregate["buckets"],
        "reports": aggregate.get("report_paths"),
    })
    return 0


def cmd_envcheck(args: argparse.Namespace) -> int:
    from pathway_v43.pollutant.real_model import RealModelAdapter
    from pathway_v43.pollutant.s5b_orchestrator import _model_env

    env = _model_env(args.env_file)
    present = {k: bool(v) for k, v in env.items()
               if k != "V43_LLM_API_KEY"}
    try:
        RealModelAdapter.from_env()
        configured = True
    except Exception as exc:  # noqa: BLE001 —— 存在性检查,不抛
        configured = False
        _emit({"command": "envcheck", "ok": False, "configured": False,
               "error": str(exc)[:200], "env_keys_present": present,
               "note": "凭证只从环境/env 文件读取;密钥值不打印"})
        return 2
    _emit({"command": "envcheck", "ok": True, "configured": True,
           "env_keys_present": present,
           "note": "凭证存在性核过;密钥值不打印不落盘"})
    return 0


def cmd_summary(args: argparse.Namespace) -> int:
    report = summarize_batch(args.batch_root)
    _emit({
        "command": "summary", "ok": True,
        "n_total": report["n_total"],
        "n_completed": report["n_completed"],
        "n_failed": report["n_failed"],
        "n_pending": report["n_pending"],
        "account": report["account"],
        "progress": _read_json(Path(args.batch_root) / "progress.json"),
    })
    return 0


def _read_json(path: Path):
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None


def _now_iso() -> str:
    from pathway_v43.domain.models import now_iso

    return now_iso()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="s5b_cli", description="PPV1 S5b 运行时 CLI(298 全量批)")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("build", help="题卷 → 参考图/run 输入/清单")
    p.add_argument("--questions", required=True,
                   help="questions.jsonl 路径(含金标;输出根须 gitignored)")
    p.add_argument("--batch-root", required=True)
    p.add_argument("--batch-tag", default="s5b-298")
    p.add_argument("--pool-mode", choices=("template", "empty"),
                   default="template",
                   help="template=类比模板底物侧相似检索(缺省);"
                        "empty=空池(模型 novel 提案)")
    p.add_argument("--provider-kind", choices=("real", "scripted"),
                   default="real")
    p.add_argument("--max-pool", type=int, default=8)
    p.add_argument("--pool-threshold", type=float, default=0.45)
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--v3-code-root", default=None)
    p.add_argument("--assets-root", default=None)
    p.set_defaults(func=cmd_build)

    p = sub.add_parser("approve", help="落预注册批准记录(发车硬门)")
    p.add_argument("--batch-root", required=True)
    p.add_argument("--preregistration-id", default="prereg-s5b-2026-10-09")
    p.add_argument("--approval-status",
                   default="preregistration_confirmed")
    p.add_argument("--user-authorization", required=True,
                   help="用户授权记录(如 launch-authorized-2026-10-09)")
    p.set_defaults(func=cmd_approve)

    p = sub.add_parser("price", help="落当日价格快照(元/Mtok)")
    p.add_argument("--batch-root", required=True)
    p.add_argument("--input-per-mtok", type=float, required=True)
    p.add_argument("--output-per-mtok", type=float, required=True)
    p.add_argument("--cached-input-per-mtok", type=float, default=None)
    p.add_argument("--currency", default="CNY")
    p.set_defaults(func=cmd_price)

    p = sub.add_parser("run", help="40 路编排(断点续跑)")
    p.add_argument("--batch-root", required=True)
    p.add_argument("--runs-root", required=True)
    p.add_argument("--env-file", default=None,
                   help="凭证 env 文件(只取 V43_LLM_* 键;密钥不落盘)")
    p.add_argument("--workers", type=int, default=S5B_DEFAULT_WORKERS)
    p.add_argument("--max-in-flight", type=int, default=40)
    p.add_argument("--gate-rpm", type=int, default=180)
    p.add_argument("--gate-tpm", type=int, default=2_700_000)
    p.add_argument("--gate-max-calls", type=int,
                   default=S5B_DEFAULT_GATE_MAX_CALLS)
    p.add_argument("--limit", type=int, default=None,
                   help="取冻结注册序前 N 题(冒烟段 1/2 并入正式批)")
    p.add_argument("--qids", default=None, help="逗号分隔 qid 白名单")
    p.add_argument("--poll-s", type=float, default=10.0)
    p.add_argument("--python-bin", default=None,
                   help="worker python(Chenyu 用 dev venv python)")
    p.set_defaults(func=cmd_run)

    p = sub.add_parser("score", help="封存答卷后判分(零 LLM)")
    p.add_argument("--batch-root", required=True)
    p.add_argument("--runs-root", required=True)
    p.add_argument("--data-scope", choices=("real", "synthetic_rule_level"),
                   default="real")
    p.set_defaults(func=cmd_score)

    p = sub.add_parser("envcheck", help="凭证存在性检查(密钥值不打印)")
    p.add_argument("--env-file", default=None)
    p.set_defaults(func=cmd_envcheck)

    p = sub.add_parser("summary", help="批进度/账目汇总(短连接轮询用)")
    p.add_argument("--batch-root", required=True)
    p.set_defaults(func=cmd_summary)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover —— CLI 入口
    raise SystemExit(main())
