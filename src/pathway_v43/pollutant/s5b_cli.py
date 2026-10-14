"""S5b 运行时 CLI —— 构建/发车/判分的远端操作入口(主会话/运维用)。

用法(Chenyu 部署;详见交付书 runbook):

```
python -m pathway_v43.pollutant.s5b_cli build \
    --questions <questions.jsonl> --batch-root <批根> [--pool-mode template]
python -m pathway_v43.pollutant.s5b_cli approve \
    --batch-root <批根> --preregistration-id prereg-s5b-2026-10-09
python -m pathway_v43.pollutant.s5b_cli price \
    --batch-root <批根> --input-per-mtok 0.8 --output-per-mtok 2.8
python -m pathway_v43.pollutant.s5b_cli budget \
    --batch-root <批根> --input-per-mtok 0.8 --output-per-mtok 2.8 \
    [--cap-cny 60] [--input-tokens-bound 30000] [--max-output-tokens 8192]
python -m pathway_v43.pollutant.s5b_cli run \
    --batch-root <批根> --runs-root <run根> [--env-file <env>] \
    [--workers 40] [--limit 10] [--gate-max-calls 1490]
python -m pathway_v43.pollutant.s5b_cli score \
    --batch-root <批根> --runs-root <run根>
```

- build:题卷 → 参考图 + run 输入 + 清单(金标承载物只进 gitignored
  根,由 s5b_builder.check_output_root 守卫);
- approve:落预注册批准记录(发车硬门:主会话在用户确认读后执行;
  状态行已 confirmed 的冻结稿可免本步——score 侧按状态行兜底);
- price:落当日价格快照(元/Mtok;缺快照 ⇒ 费用不计价,如实报);
- budget:**S5B-V3-02 冻结批级金额硬帽机器配置**(60 CNY 帽默认 +
  当日价 + 输入保守界 + 输出上限;real 批 run 前必须已落盘——发送前
  原子预留、余额不足先于传输拒、失败/未知 usage 不释放、不自动升帽;
  同价同步写 price_snapshot.json 保持单一价格来源);
  **P4c:--budget-mode no_monetary_cap_user_decision** = 显式登记
  用户"无金额帽"决定(落 budget_no_cap.json 标记,带决定原文/日期;
  与数值守卫互斥)——金额检查跳过,调用数门/速率门照常,费用不计价
  如实报;
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

from pathway_v43.adapters.rate_gate import (  # noqa: E402
    normalize_cost_guard_config,
)
from pathway_v43.pollutant.s5b_builder import (  # noqa: E402
    build_question_batch,
    default_pool_provider,
)
from pathway_v43.pollutant.s5b_orchestrator import (  # noqa: E402
    S5B_BUDGET_GUARD_FILE,
    S5B_BUDGET_NO_CAP_FILE,
    S5B_BUDGET_NO_CAP_SCHEMA,
    S5B_DEFAULT_BUDGET_CAP_CNY,
    S5B_DEFAULT_GATE_MAX_CALLS,
    S5B_DEFAULT_WORKERS,
    BUDGET_MODE_NO_CAP,
    load_budget_guard,
    load_budget_no_cap_marker,
    no_cap_marker_string,
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
        config = resolve_config(args.v3_code_root, args.assets_root)
        engine = None
        if args.recorded_source:
            # W2:recorded 精确源通道(公共 get_engine 身份守卫;库
            # hash 由 recorded_source 校验)
            from pathway_v43.adapters.v3_engine import get_engine

            engine = get_engine(config)
        pool_provider = default_pool_provider(
            config, max_pool=args.max_pool, threshold=args.pool_threshold,
            engine=engine)
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


def cmd_budget(args: argparse.Namespace) -> int:
    """S5B-V3-02:落盘批级金额硬帽机器配置(budget_guard.json)。

    - 五数值字段(cap/input 价/output 价/输入保守界/输出上限)冻结
      进机器配置;派生 per_attempt_bound_cny 与 config_sha256 可核验;
    - 同值重复执行幂等;**改值拒绝**(改参须新批根,预注册纪律);
    - 同价同步写 price_snapshot.json(汇总口径单一来源,防两价源漂移);
    - **P4c no-cap 模式**(``--budget-mode no_monetary_cap_user_decision
      --user-decision-date YYYY-MM-DD --user-decision-record <用户决定
      原文>``):落 ``budget_no_cap.json`` 显式标记(与 budget_guard.json
      互斥;数值金额参数不得同给;同决定幂等、改决定须新批根);金额
      检查跳过、**调用数门/速率门照常**;不写 price_snapshot(无价)。
    """
    root = Path(args.batch_root)
    if str(args.budget_mode or "") == BUDGET_MODE_NO_CAP:
        return _cmd_budget_no_cap(args, root)
    if args.input_per_mtok is None or args.output_per_mtok is None:
        _emit({
            "command": "budget", "ok": False,
            "error": ("数值模式必填 --input-per-mtok / --output-per-mtok"
                      "(当日价,元/Mtok;或改用 --budget-mode "
                      f"{BUDGET_MODE_NO_CAP} 显式登记用户无金额帽决定)"),
        })
        return 2
    cap_cny = (S5B_DEFAULT_BUDGET_CAP_CNY if args.cap_cny is None
               else float(args.cap_cny))
    input_tokens_bound = (30000 if args.input_tokens_bound is None
                          else int(args.input_tokens_bound))
    max_output_tokens = (8192 if args.max_output_tokens is None
                         else int(args.max_output_tokens))
    raw = {
        "schema": "s5b-budget-guard-1",
        "cap_cny": cap_cny,
        "input_per_mtok": float(args.input_per_mtok),
        "output_per_mtok": float(args.output_per_mtok),
        "input_tokens_conservative_bound": input_tokens_bound,
        "max_output_tokens": max_output_tokens,
        "currency": args.currency,
        "recorded_at": _now_iso(),
        "note": ("S5B-V3-02 批级金额硬帽机器配置:每次可能付费的发送"
                 "尝试(含 HTTP retry)先原子预留;失败/超时/未知 usage/"
                 "孤儿不释放可能已付金额;不自动升帽"),
    }
    try:
        config = normalize_cost_guard_config(raw)
    except ValueError as exc:
        detail = exc.args[0] if exc.args else {}
        _emit({"command": "budget", "ok": False,
               "error": "金额守卫配置坏形状(五数值字段须为正)",
               "detail": detail})
        return 2
    path = root / S5B_BUDGET_GUARD_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file():
        try:
            existing = load_budget_guard(root)
        except Exception:  # noqa: BLE001 —— 坏既有文件按冲突处理
            existing = None
        if existing is not None and \
                existing.get("config_sha256") != \
                config["config_sha256"]:
            _emit({
                "command": "budget", "ok": False,
                "error": ("批根已有不同金额守卫配置(改值须新批根;"
                          "预注册纪律:不自动升帽/改价)"),
                "existing_config_sha256":
                    existing.get("config_sha256"),
                "new_config_sha256": config["config_sha256"],
            })
            return 3
    payload = dict(raw)
    payload.update({k: config[k] for k in (
        "per_attempt_bound_cny", "config_sha256",
        "usage_split_policy")})
    path.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True,
                               indent=1) + "\n", encoding="utf-8")
    # 同价快照(汇总 cost_known 与守卫结算单一价格来源)
    snapshot = {
        "input_per_mtok": float(args.input_per_mtok),
        "output_per_mtok": float(args.output_per_mtok),
        "currency": args.currency,
        "recorded_at": _now_iso(),
        "note": ("与 budget_guard.json 同一次落盘(单一价格来源;"
                 "汇总 known-usage 小计与发送前预留共用当日价)"),
    }
    (root / "price_snapshot.json").write_text(
        json.dumps(snapshot, ensure_ascii=False, sort_keys=True,
                   indent=1) + "\n", encoding="utf-8")
    _emit({
        "command": "budget", "ok": True, "path": str(path),
        "config": {k: payload.get(k) for k in (
            "cap_cny", "input_per_mtok", "output_per_mtok",
            "input_tokens_conservative_bound", "max_output_tokens",
            "per_attempt_bound_cny", "config_sha256")},
    })
    return 0


def _cmd_budget_no_cap(args: argparse.Namespace, root: Path) -> int:
    """P4c:落盘批级金额守卫显式 no-cap 标记(用户决定;互斥守卫)。"""
    import re

    date = str(args.user_decision_date or "").strip()
    record = str(args.user_decision_record or "").strip()
    if not record or not date:
        _emit({
            "command": "budget", "ok": False,
            "error": ("no-cap 模式必填 --user-decision-record(用户决定"
                      "原文)与 --user-decision-date(YYYY-MM-DD;用户决定"
                      "是跳过金额守卫的合法性来源,不凭空缺省)"),
        })
        return 2
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", date):
        _emit({"command": "budget", "ok": False,
               "error": f"--user-decision-date 非法:{date!r}(须 YYYY-MM-DD)"})
        return 2
    for flag, value in (
            ("--cap-cny", args.cap_cny),
            ("--input-per-mtok", args.input_per_mtok),
            ("--output-per-mtok", args.output_per_mtok),
            ("--input-tokens-bound", args.input_tokens_bound),
            ("--max-output-tokens", args.max_output_tokens)):
        if value is not None:
            _emit({
                "command": "budget", "ok": False,
                "error": (f"no-cap 模式不接收数值金额参数({flag}={value};"
                          "有数值就该走数值模式,模式矛盾拒)"),
            })
            return 2
    marker_path = root / S5B_BUDGET_NO_CAP_FILE
    marker_path.parent.mkdir(parents=True, exist_ok=True)
    # 互斥:既有数值守卫 ⇒ 模式变更须新批根(不静默切换)
    if (root / S5B_BUDGET_GUARD_FILE).is_file():
        _emit({
            "command": "budget", "ok": False,
            "error": (f"批根已有数值金额守卫 {S5B_BUDGET_GUARD_FILE}"
                      "(改 no-cap 模式须新批根;预注册纪律:模式不静默"
                      "切换)"),
        })
        return 3
    try:
        existing = load_budget_no_cap_marker(root)
    except Exception as exc:  # noqa: BLE001 —— 坏标记按冲突处理
        _emit({"command": "budget", "ok": False,
               "error": f"既有 no-cap 标记坏形状:{exc}"[:300]})
        return 2
    if existing is not None:
        if str(existing.get("user_decision_date")) != date or \
                str(existing.get("user_decision_record")) != record:
            _emit({
                "command": "budget", "ok": False,
                "error": ("批根已有不同 no-cap 决定记录(用户决定原文/"
                          "日期首写冻结,不可改;改决定须新批根)"),
                "existing_user_decision_date":
                    existing.get("user_decision_date"),
                "requested_user_decision_date": date,
            })
            return 3
        _emit({
            "command": "budget", "ok": True, "path": str(marker_path),
            "budget_mode": BUDGET_MODE_NO_CAP,
            "marker": existing.get("marker"),
            "idempotent": True,
            "note": ("同决定幂等:标记已在案(金额检查跳过;调用数门"
                     "gate_max_calls/速率门照常;不写价格快照)"),
        })
        return 0
    payload = {
        "schema": S5B_BUDGET_NO_CAP_SCHEMA,
        "budget_mode": BUDGET_MODE_NO_CAP,
        "user_decision_date": date,
        "user_decision_record": record,
        "marker": no_cap_marker_string(date),
        "recorded_at": _now_iso(),
        "note": ("P4c(2026-10-12 用户决定)批级金额守卫显式 no-cap 标记:"
                 "金额检查跳过、金额预约/结算不启用;调用数门"
                 "(gate_max_calls)/速率门(RPM/TPM)/并发门照常生效;"
                 "known usage(token/调用数)照记;无帽≠无限制;与 "
                 "budget_guard.json 互斥,不写价格快照(无价)"),
    }
    marker_path.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=1)
        + "\n", encoding="utf-8")
    _emit({
        "command": "budget", "ok": True, "path": str(marker_path),
        "budget_mode": BUDGET_MODE_NO_CAP,
        "marker": payload["marker"],
        "user_decision_date": date,
        "note": ("no-cap 标记落盘:金额检查跳过(用户决定原文在案);"
                 "调用数门/速率门照常;费用不计价如实报;不写价格快照"),
    })
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
    p.add_argument("--recorded-source", action="store_true",
                   help="W2:recorded 精确源通道(exact strict/cn 分层,"
                        "推断映射编译;经公共 get_engine 身份守卫)")
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

    p = sub.add_parser(
        "budget", help="冻结批级金额硬帽机器配置(S5B-V3-02 发车硬门;"
                       "或 --budget-mode 显式登记用户 no-cap 决定)")
    p.add_argument("--batch-root", required=True)
    p.add_argument("--cap-cny", type=float, default=None,
                   help="批级金额硬帽(CNY;缺省 60;不自动升帽)")
    p.add_argument("--input-per-mtok", type=float, default=None,
                   help="当日输入价(元/Mtok;数值模式必填;与 price 同源)")
    p.add_argument("--output-per-mtok", type=float, default=None,
                   help="当日输出价(元/Mtok;数值模式必填;与 price 同源)")
    p.add_argument("--input-tokens-bound", type=int, default=None,
                   help="单次请求输入 tokens 保守上界(发车当日定稿;"
                        "缺省 30000)")
    p.add_argument("--max-output-tokens", type=int, default=None,
                   help="请求体输出 token 上限(随请求发送,提供者侧可核;"
                        "缺省 8192)")
    p.add_argument("--currency", default="CNY")
    p.add_argument("--budget-mode", default=None,
                   choices=(BUDGET_MODE_NO_CAP,),
                   help=("P4c:显式 no-cap 模式(用户决定无金额帽)—— 落 "
                         f"{S5B_BUDGET_NO_CAP_FILE} 标记;金额检查跳过,"
                         "调用数门/速率门照常;须给 --user-decision-date"
                         "/--user-decision-record;与数值参数互斥"))
    p.add_argument("--user-decision-date", default=None,
                   help="no-cap 模式:用户决定日期(YYYY-MM-DD)")
    p.add_argument("--user-decision-record", default=None,
                   help="no-cap 模式:用户决定原文(逐字登记,不凭空缺省)")
    p.set_defaults(func=cmd_budget)

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
