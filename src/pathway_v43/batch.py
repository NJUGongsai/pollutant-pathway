"""dev 批跑 — 20 路并行协调器、输入清单、批次身份与归并(TASK_V43_EXPORT_DEV §2)。

组成:

- **输入清单**(``build_input_manifest``):一次性、只读、白名单字段提取 ——
  从 v3 冻结 ``split_manifest.json`` 取 dev 的 20 个 route_id,从
  ``gold_routes.jsonl`` 只取 ``route_id`` + ``root_smiles`` 与来源哈希。
  金标 edges / gold_leaves / provenance 不进入运行侧任何文件;清单随
  批次保存并复核恰 20 条、与 eval 不相交。
- **批次身份**(``build_batch_identity``):代码/资产/提示词/模型身份
  (provider/model/request_params/timeout)/预算/限流/导出策略/输入清单
  SHA 全部冻结;run_id 由批次身份短哈希 + route_id 派生(稳定,含二者)。
  同一批次根重复执行:身份一致 → 已完成项只读复用、未完成项 resume;
  身份不同 → 结构化冲突(不静默覆盖)。
- **协调器**(``run_batch``):一次分配 20 个 route_id,启动 20 个独立
  OS 进程(每个 worker 只写自己的 run 目录与 SQLite;共享仅只读代码/
  资产与闸门/进度文件);记录 PID/route_id/启动时间/退出码/各自日志;
  崩溃 worker 只按未完成路线恢复(resume),不重发已持久化的模型请求;
  达到批次 API 预算或闸门全局停止时停止派发,保留 20 路部分答卷。
- **worker**(``run_worker``):单路线 run-or-resume + 导出 + 终态状态
  文件;恢复语义全部沿用既有 run/resume(task_id 幂等 + graph_revision
  对齐);首个 checkpoint 前中断的 run 隔离到 quarantine 后重跑。
- **归并**(``merge_predictions``):按冻结 dev route_id 顺序(输入清单
  顺序,非完成顺序)拼 20 行答卷;route_id 重复/缺失 → 结构化失败;
  失败路线补显式空行,保证 20 行且每个 route_id 恰一次。
- **API 账目**(``api_account``):汇总各 run 的 issued 调用、响应状态、
  429/退避、孤儿、token(响应提供时)与费用(价格快照冻结;不可得标
  ``unknown``,不估算冒充实测)。

红线:本模块不把任何金标字段写进 PredictionTask/模型请求;eval 切片
不在此处运行;fake 模式仅协议/恢复测试,不进模型效果表。
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import traceback
from pathlib import Path

from .adapters.rate_gate import FileRateGate
from .domain.models import canonical_json

BATCH_SCHEMA_VERSION = "v43-batch-1"

ROUTE_STATE_SCHEMA = "v43-route-state-1"

# run 级合法终态(policy.stop_reason 全集):awaiting_prediction /
# budget_exhausted 是**合法停留**(可产生空答卷),与异常失败不同。
LEGAL_RUN_TERMINALS = frozenset({
    "completed", "already_completed", "awaiting_prediction",
    "budget_exhausted", "invalid_input",
})


# ------------------------------------------------ 路线终态分类(R1-c)


def classify_route_state(status: dict | None) -> dict:
    """单路线终态分类(机器可读,§4.1 五类;判定只认 worker 状态文件
    的持久事实,不信批次报告汇总字段)。

    route_state:
      - ``success_completed``:run 正常完成且导出成功;
      - ``legal_stop``:合法停留(awaiting_prediction/budget_exhausted/
        invalid_input)且导出成功 —— 空答卷也是合法答卷;
      - ``failed``:worker 记录了异常失败(``failed`` 字段非空;
        ArtifactIntegrityError/TypeError/worker_failed_no_terminal 等);
      - ``export_failed``:run 未记失败但导出失败;
      - ``missing``:无终态状态文件或未终止(无 finished_at/stop_reason)。

    ``failed`` 即使 ``export_ok=true``(部分答卷已导出)也**不**是成功
    完成 —— 部分答卷只可诊断,不可计入发布型配对判定。
    """
    base = {"schema_version": ROUTE_STATE_SCHEMA}
    if not status or not status.get("finished_at"):
        return {**base, "route_state": "missing",
                "failure_class": None, "stop_reason": None,
                "export_ok": None, "failed": None}
    failed = status.get("failed")
    if failed:
        return {**base, "route_state": "failed",
                "failure_class": str(failed).split(":", 1)[0],
                "stop_reason": status.get("stop_reason", ""),
                "export_ok": bool(status.get("export_ok")),
                "failed": str(failed)[:300]}
    if not status.get("export_ok"):
        return {**base, "route_state": "export_failed",
                "failure_class": "ExportFailure",
                "stop_reason": status.get("stop_reason", ""),
                "export_ok": False,
                "failed": str(status.get("export_failed", ""))[:300]}
    sr = status.get("stop_reason") or ""
    if sr in ("completed", "already_completed"):
        return {**base, "route_state": "success_completed",
                "failure_class": None, "stop_reason": sr,
                "export_ok": True, "failed": None}
    if sr in LEGAL_RUN_TERMINALS:
        return {**base, "route_state": "legal_stop",
                "failure_class": None, "stop_reason": sr,
                "export_ok": True, "failed": None}
    return {**base, "route_state": "missing",
            "failure_class": "NoTerminalStopReason",
            "stop_reason": sr, "export_ok": True, "failed": None}


def batch_terminal_summary(route_ids: list[str],
                           terminal: dict[str, dict]) -> dict:
    """批次终态汇总:``completed`` / ``incomplete`` / ``failed``。

    - ``failed``:存在异常失败路线或导出失败路线(任一即阻断发布型
      配对;r1 四臂 `status="completed"` 却有 52 条失败路线的事故
      就是这个门要拦的形状);
    - ``incomplete``:存在缺失/未终止路线(无异常失败);
    - ``completed``:全部路线处于合法终态(成功完成或合法停留)。

    ``n_expected``/``n_valid_terminal``/``n_success_completed``/
    ``n_legal_stop``/``n_failed``/``n_export_failed``/``n_missing`` 与
    失败路线清单一并给出,语义见 docs/EC298_PHASE_D_R1_REPAIR_REPORT.md。
    """
    states = {rid: classify_route_state(terminal.get(rid))
              for rid in route_ids}
    failed_ids = sorted(r for r, s in states.items()
                        if s["route_state"] == "failed")
    export_failed_ids = sorted(r for r, s in states.items()
                               if s["route_state"] == "export_failed")
    missing_ids = sorted(r for r, s in states.items()
                         if s["route_state"] == "missing")
    if failed_ids or export_failed_ids:
        status = "failed"
    elif missing_ids:
        status = "incomplete"
    else:
        status = "completed"
    counts = {k: sum(1 for s in states.values() if s["route_state"] == k)
              for k in ("success_completed", "legal_stop", "failed",
                        "export_failed", "missing")}
    return {
        "schema_version": ROUTE_STATE_SCHEMA,
        "status": status,
        "n_expected": len(route_ids),
        "n_valid_terminal": counts["success_completed"] + counts["legal_stop"],
        **{f"n_{k}": v for k, v in counts.items()},
        "failed_route_ids": failed_ids,
        "export_failed_route_ids": export_failed_ids,
        "missing_route_ids": missing_ids,
        "route_states": states,
    }

SPLIT_EXPECTED_N = {"dev": 20, "eval": 100}

# ---------------------------------------------------------------- 输入清单


class BatchError(RuntimeError):
    def __init__(self, message: str, detail: dict | None = None):
        super().__init__(message)
        self.detail = detail or {}


class BatchConflict(BatchError):
    """同批次根、不同批次身份(不静默覆盖)。"""


class CapacityBlocked(BatchError):
    """资源预检不足以承载 20 路并行(不暗改串行)。"""


def split_paths(v3_root: str | Path) -> tuple[Path, Path]:
    root = Path(v3_root) / "evaluation" / "pathway_benchmark"
    return root / "split_manifest.json", root / "gold_routes.jsonl"


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_split_ids(v3_root: str | Path, split: str) -> tuple[list[str], dict]:
    """只读冻结清单 → (route_ids 顺序, 来源哈希块)。"""
    manifest_path, gold_path = split_paths(v3_root)
    for p in (manifest_path, gold_path):
        if not p.is_file():
            raise BatchError(f"v3 冻结基准文件缺失:{p}", {"path": str(p)})
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    ids = list(manifest.get("split", {}).get(split) or [])
    expected = SPLIT_EXPECTED_N.get(split)
    if expected and len(ids) != expected:
        raise BatchError(
            f"split {split} 应有 {expected} 条,清单实际 {len(ids)}",
            {"n": len(ids)})
    source = {
        "split_manifest_sha256": _sha256_file(manifest_path),
        "gold_routes_sha256": _sha256_file(gold_path),
        "v3_root": str(Path(v3_root).resolve()),
    }
    return ids, source


def build_input_manifest(v3_root: str | Path, split: str,
                         out_path: str | Path) -> dict:
    """一次性白名单提取:route_id + root_smiles + 哈希(不含任何金标字段)。

    提取动作是独立的一次性只读步骤;输出是批跑的唯一运行侧输入。
    """
    ids, source = load_split_ids(v3_root, split)
    _, gold_path = split_paths(v3_root)
    rows = []
    eval_ids: set[str] = set()
    if split == "dev":
        # 与 eval 不相交的核查在同一冻结清单上完成(不读 eval 金标内容)
        eval_list, _ = load_split_ids(v3_root, "eval")
        eval_ids = set(eval_list)
    overlap = sorted(set(ids) & eval_ids)
    if overlap:
        raise BatchError("dev 与 eval 切片相交(冻结清单损坏)",
                         {"overlap": overlap})
    allowed = {"route_id", "root_smiles"}
    for line in gold_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        if rec.get("route_id") not in set(ids):
            continue
        row = {k: rec[k] for k in allowed}
        row["root_smiles_sha256"] = hashlib.sha256(
            row["root_smiles"].encode("utf-8")).hexdigest()
        rows.append(row)
    got = [r["route_id"] for r in rows]
    if sorted(got) != sorted(ids):
        raise BatchError(
            "金标文件中未找齐 split 全部 route_id(冻结清单不一致)",
            {"missing": sorted(set(ids) - set(got))})
    out = {
        "schema_version": BATCH_SCHEMA_VERSION,
        "kind": "batch_input_manifest",
        "split": split,
        "route_order": ids,
        "source": source,
        "routes": rows,
        "whitelist_fields": sorted(allowed | {"root_smiles_sha256"}),
        "gold_fields_excluded": True,
    }
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8")
    return out


def load_input_manifest(path: str | Path) -> dict:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("kind") != "batch_input_manifest":
        raise BatchError(f"输入清单文件不正确:{path}", {"path": str(path)})
    if not data.get("gold_fields_excluded"):
        raise BatchError("输入清单缺少白名单声明", {"path": str(path)})
    return data


# ---------------------------------------------------------------- 批次身份

DEFAULT_DEV_BATCH_CONFIG: dict = {
    "budgets": {
        "max_depth": 6,
        "max_expansions": 40,
        "max_frontier_width": 3,
        "max_llm_calls": 42,
        "max_proposals": 40,
    },
    "model_request_params": {"reasoning_effort": "max"},
    "llm_timeout_s": 300.0,
    "max_http_retries": 4,
    "rate": {
        "rpm": 180,
        "tpm": 2_700_000,
        "max_calls": 1000,
        "cooldown_cap_s": 60.0,
        "acquire_timeout_s": 600.0,
    },
    "batch_cost_cap_cny": 30.0,
    "provider_price_snapshot": {
        "model_id": "ZHIPU/GLM-5.3-Flash",
        "region": "cn-beijing",
        "input_cny_per_m": 0.8,
        "output_cny_per_m": 2.8,
        "cache_read_cny_per_m": 0.23,
        "rpm": 200,
        "tpm": 3_000_000,
        "source": "help.aliyun.com/zh/model-studio/glm-5-3-flash-by-zhipu",
        "checked": "2026-09-25",
    },
    "export_policy_overrides": {},
    "prediction_policy_overrides": {},
    "capacity": {"memory_gb_per_worker": 3.0, "min_free_disk_gb": 20.0},
    "worker_wall_clock_cap_s": 8 * 3600,
    "max_worker_respawns": 2,
    "poll_interval_s": 10.0,
}


def load_batch_config(path: str | Path | None = None) -> dict:
    if path is None:
        root = Path(__file__).resolve().parents[2]
        candidate = root / "configs" / "dev_batch.json"
        path = candidate if candidate.is_file() else None
    if path is None:
        return json.loads(json.dumps(DEFAULT_DEV_BATCH_CONFIG))
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _code_identity_sha() -> str:
    from .storage.run_identity import code_identity

    return code_identity()["aggregate_sha256"]


def _asset_manifest_sha() -> str:
    from .adapters.asset_manifest import verify_repo_manifest
    from .config import resolve_config

    return verify_repo_manifest(resolve_config().assets_root)["manifest_sha256"]


def build_batch_identity(
    *, split: str, input_manifest_path: str | Path, config: dict,
    provider: str, model_id: str, request_params: dict, timeout_s: float,
    export_policy: dict, prediction_policy_block: dict | None = None,
) -> dict:
    """批次身份:全部影响答卷与费用的事实冻结(短哈希进 run_id)。"""
    manifest = load_input_manifest(input_manifest_path)
    from .adapters.llm_client import prompt_versions
    from .config import repo_root

    prompts = prompt_versions(repo_root() / "configs" / "prompts")
    body = {
        "schema_version": BATCH_SCHEMA_VERSION,
        "split": split,
        "input_manifest_sha256": _sha256_file(Path(input_manifest_path)),
        "source": manifest["source"],
        "config": config,
        "model": {
            "provider": provider,
            "model_id": model_id,
            "request_params": request_params,
            "timeout_s": float(timeout_s),
            "prompt_versions": prompts,
            "prediction_policy": prediction_policy_block
            or {"policy_version": "v43-predpol-default"},
        },
        "export_policy": export_policy,
        "code_aggregate_sha256": _code_identity_sha(),
        "asset_manifest_sha256": _asset_manifest_sha(),
    }
    digest = hashlib.sha256(canonical_json(body).encode("utf-8")).hexdigest()
    return {"identity": body, "sha256": digest,
            "short": digest[:8], "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}


def run_id_for_route(batch_short: str, split: str, route_id: str) -> str:
    """稳定 run_id:含批次身份短哈希与 route_id(同批次重跑不漂移)。"""
    return f"{split}_{batch_short}_{route_id}"


# ---------------------------------------------------------------- worker


def _engine_finder(config):
    from .adapters.v3_engine import get_engine
    from .services.analog_source import AnalogSourceResolver
    from .services.reaction_finder import EngineReactionFinder

    engine = get_engine(config)
    return EngineReactionFinder(engine, config,
                                analog_resolver=AnalogSourceResolver(config))


def run_worker(*, config, runs_root: Path, run_id: str, root_smiles: str,
               route_id: str, model_setup, budgets: dict,
               export_policy: dict, status_path: Path,
               quarantine_root: Path | None = None,
               finder=None) -> dict:
    """单路线 worker:run-or-resume → 导出 → 终态状态文件。

    恢复语义沿用既有 run/resume;首个 checkpoint 前中断(run_identity
    已写、图未启动)的 run 移入 quarantine 后重跑(此时不可能有已发出
    的模型请求:call_model 在检索之后)。``finder`` 仅供测试注入合成
    检索器;生产路径恒为真实引擎。"""
    from .workflow import resume_run, start_run
    from .workflow.runner import RunError

    status: dict = {"route_id": route_id, "run_id": run_id,
                    "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    runs_root = Path(runs_root)
    run_dir = runs_root / run_id

    def _finder():
        return finder if finder is not None else _engine_finder(config)

    # 测试钩子:与 cmd_run 同源(硬杀注入点仅供恢复测试)
    crash_after = os.environ.get("PATHWAY_V43_CRASH_AFTER") or None
    try:
        if not (run_dir / "run_identity.json").is_file():
            summary = start_run(
                config=config, runs_root=runs_root, run_id=run_id,
                smiles=root_smiles,
                max_depth=budgets["max_depth"],
                max_expansions=budgets["max_expansions"],
                max_frontier_width=budgets["max_frontier_width"],
                finder=_finder(), scripted=finder is not None,
                model=model_setup,
                max_llm_calls=budgets.get("max_llm_calls", 0),
                max_proposals=budgets.get("max_proposals", 0),
                crash_after=crash_after,
            )
        else:
            if (run_dir / "report" / "pathway.json").is_file():
                summary = {"stop_reason": "already_completed", "resumed": False}
            else:
                try:
                    summary = resume_run(
                        config=config, runs_root=runs_root, run_id=run_id,
                        finder=_finder(), model=model_setup,
                        crash_after=crash_after,
                    )
                except RunError as exc:
                    if "没有可恢复的检查点" not in str(exc):
                        raise
                    # 首个 checkpoint 前中断:隔离旧目录(保留审计)后重跑
                    quarantine_root = Path(quarantine_root or runs_root.parent
                                           / "quarantine")
                    quarantine_root.mkdir(parents=True, exist_ok=True)
                    dest = quarantine_root / f"{run_id}.{int(time.time())}"
                    shutil.move(str(run_dir), str(dest))
                    status["quarantined_from"] = str(dest)
                    summary = start_run(
                        config=config, runs_root=runs_root, run_id=run_id,
                        smiles=root_smiles,
                        max_depth=budgets["max_depth"],
                        max_expansions=budgets["max_expansions"],
                        max_frontier_width=budgets["max_frontier_width"],
                        finder=_finder(), scripted=finder is not None,
                        model=model_setup,
                        max_llm_calls=budgets.get("max_llm_calls", 0),
                        max_proposals=budgets.get("max_proposals", 0),
                        crash_after=crash_after,
                    )
        status["stop_reason"] = summary.get("stop_reason", "")
    except Exception as exc:
        status["failed"] = f"{type(exc).__name__}:{str(exc)[:300]}"
        status["failed_detail"] = dict(getattr(exc, "detail", {}) or {})
        # R1 教训(pb_0117):只记类型+消息不足以定位根因,worker 日志也
        # 没有落 traceback —— 现在随终态状态文件落盘完整调用栈
        status["failed_traceback"] = traceback.format_exc()[-4000:]
    # 无论 run 成败,尽量导出已提交事实(部分/空答卷也是答卷)
    try:
        from .output.export_v3 import export_run_v3

        result = export_run_v3(runs_root, run_id, route_id=route_id,
                               policy=export_policy)
        status["predictions_sha256"] = result["predictions_sha256"]
        status["export_ok"] = True
    except Exception as exc:
        status["export_ok"] = False
        status["export_failed"] = f"{type(exc).__name__}:{str(exc)[:200]}"
    status["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    status_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = status_path.with_suffix(".tmp")
    tmp.write_text(
        json.dumps(status, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8")
    os.replace(tmp, status_path)
    return status


def worker_main(argv: list[str] | None = None) -> int:
    """``pathway_v43 batch-worker --plan P``:协调器派生的单路线进程入口。"""
    import argparse

    ap = argparse.ArgumentParser(prog="pathway_v43 batch-worker")
    ap.add_argument("--plan", required=True)
    a = ap.parse_args(argv)
    plan = json.loads(Path(a.plan).read_text(encoding="utf-8"))
    from .adapters.llm_client import resolve_model_setup
    from .config import resolve_config

    config = resolve_config()
    provider = plan["model"]["provider"]
    model = None
    if provider != "off":
        from .domain.policy import prediction_policy

        model = resolve_model_setup(
            provider,
            request_params=plan["model"].get("request_params") or {},
            timeout_s=plan["model"].get("timeout_s") or None,
            policy=prediction_policy(
                plan["model"].get("policy_overrides")),
        )
    finder = None
    if plan.get("test_scripted"):
        # 测试驱动:合成检索器(协议/恢复/屏障夹具用;生产不设此键)
        from .services.reaction_finder import ScriptedReactionFinder

        scripted = json.loads(Path(plan["test_scripted"]).read_text(
            encoding="utf-8"))
        finder = ScriptedReactionFinder(scripted)
    status = run_worker(
        config=config, runs_root=Path(plan["runs_root"]),
        run_id=plan["run_id"], root_smiles=plan["root_smiles"],
        route_id=plan["route_id"], model_setup=model,
        budgets=plan["budgets"], export_policy=plan["export_policy"],
        status_path=Path(plan["status_path"]),
        quarantine_root=Path(plan["quarantine_root"])
        if plan.get("quarantine_root") else None,
        finder=finder,
    )
    ok = not status.get("failed")
    print(json.dumps({"ok": ok, **status}, ensure_ascii=False))
    return 0 if ok else 2


# ---------------------------------------------------------------- 批次入口


def load_env_file(path: str | Path) -> dict:
    """读 KEY=VALUE 环境文件;只取 V43_LLM_* 键,绝不打印/落盘值。"""
    env: dict[str, str] = {}
    p = Path(path)
    if not p.is_file():
        raise BatchError(f"环境文件不存在:{p}", {"path": str(p)})
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key.startswith("V43_LLM_"):
            env[key] = value
    return env


def batch_identity_conflict_check(batch_root: Path, identity: dict) -> None:
    """同批次根已有不同批次身份 → 结构化冲突(不静默覆盖)。"""
    path = Path(batch_root) / "batch_identity.json"
    if not path.is_file():
        return
    saved = json.loads(path.read_text(encoding="utf-8"))
    if saved.get("sha256") != identity["sha256"]:
        raise BatchConflict(
            "批次根已存在不同的批次身份(配置/代码/资产/清单之一变化);"
            "请使用新的批次根,不静默覆盖已有批跑",
            {"saved_sha256": saved.get("sha256"),
             "new_sha256": identity["sha256"]})


def _policy_block_for_identity(model_choice: str, config: dict) -> dict:
    """批次身份的预测策略块:与 worker 实际装配同源(冻结进批次哈希)。"""
    from .domain.policy import prediction_policy

    return prediction_policy(config.get("prediction_policy_overrides"))


def run_batch(
    *, split: str, batch_root: Path, runs_root: Path, manifest: dict,
    config: dict, export_policy: dict, model_choice: str,
    env_file: str | None, batch_config_path: str | None,
    v3_code_root: str | None, out: str | None = None,
) -> dict:
    """``batch run`` 编排:身份冻结 → 预检 → 20 路协调 → 归并 → 账目。"""
    import argparse

    from .adapters.llm_client import real_provider_env, resolve_model_setup

    batch_root.mkdir(parents=True, exist_ok=True)

    # ---- 模型装配与硬校验(real 凭证缺失 → not_run,不以 fake 代跑)----
    model_block: dict = {}
    if model_choice == "fake":
        model_block = {"provider": "fake", "model_id": "fake-scripted-v1",
                       "request_params": {}, "timeout_s": 0.0}
    elif model_choice == "off":
        model_block = {"provider": "off", "model_id": "",
                       "request_params": {}, "timeout_s": 0.0}
    else:
        if env_file:
            os.environ.update(load_env_file(env_file))
        env = real_provider_env()
        missing = [k for k, ok in (
            ("V43_LLM_BASE_URL", env["base_url_set"]),
            ("V43_LLM_API_KEY", env["api_key_set"]),
            ("V43_LLM_MODEL", env["model_set"]),
        ) if not ok]
        if missing:
            report = {
                "status": "not_run:no_credentials_or_access",
                "missing_env": missing,
                "note": "不以 fake 代跑;已完成事实(如有)原样保留",
            }
            (batch_root / "batch_report.json").write_text(
                json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8")
            print(json.dumps(report, ensure_ascii=False))
            raise SystemExit(2)
        from .domain.policy import prediction_policy

        setup = resolve_model_setup(
            "openai_compatible",
            request_params=config["model_request_params"],
            timeout_s=config["llm_timeout_s"],
            policy=prediction_policy(
                config.get("prediction_policy_overrides")),
        )
        required = config.get("provider_price_snapshot", {}).get("model_id")
        if required and setup.model_id != required:
            report = {
                "status": "not_run:model_id_mismatch",
                "required": required, "actual": setup.model_id,
                "note": "批次模型 ID 必须与冻结配置一致,20 路完全相同",
            }
            (batch_root / "batch_report.json").write_text(
                json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8")
            print(json.dumps(report, ensure_ascii=False))
            raise SystemExit(2)
        model_block = {"provider": "openai_compatible",
                       "model_id": setup.model_id,
                       "request_params": dict(setup.request_params),
                       "timeout_s": float(setup.timeout_s)}

    # ---- 批次身份(冲突检查 + 持久化)----
    identity = build_batch_identity(
        split=split,
        input_manifest_path=batch_root / "input_manifest.json",
        config=config, provider=model_block["provider"],
        model_id=model_block["model_id"],
        request_params=model_block["request_params"],
        timeout_s=model_block["timeout_s"],
        export_policy=export_policy,
        prediction_policy_block=(_policy_block_for_identity(
            model_choice, config)),
    )
    batch_identity_conflict_check(batch_root, identity)
    (batch_root / "batch_identity.json").write_text(
        json.dumps(identity, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n", encoding="utf-8")

    # ---- 资源预检(不足 → CapacityBlocked,不暗改串行)----
    capacity = precheck_capacity(batch_root, config)

    # ---- 协调器:20 路并行至全部终态 ----
    logf = open(batch_root / "coordinator_stdout.log", "a", encoding="utf-8")

    def _log(line: str) -> None:
        logf.write(line + "\n")
        logf.flush()

    coordinator = BatchCoordinator(
        batch_root=batch_root, runs_root=runs_root, manifest=manifest,
        identity=identity, config=config,
        provider=model_block["provider"], model_id=model_block["model_id"],
        request_params=model_block["request_params"],
        timeout_s=model_block["timeout_s"], export_policy=export_policy,
        max_parallel=int(config.get("max_parallel", 20)),
        poll_interval_s=float(config.get("poll_interval_s", 10.0)),
        worker_wall_clock_cap_s=float(
            config.get("worker_wall_clock_cap_s", 8 * 3600)),
        max_worker_respawns=int(config.get("max_worker_respawns", 2)),
        progress_log=_log,
    )
    terminal = coordinator.run_to_completion()

    # ---- 归并 + 账目 + 批次报告 ----
    run_ids = [run_id_for_route(identity["short"], split, rid)
               for rid in manifest["route_order"]]
    merged = merge_predictions(
        batch_root=batch_root, runs_root=runs_root, manifest=manifest,
        identity=identity, export_policy=export_policy, terminal=terminal)
    account = api_account(runs_root, run_ids,
                          price_snapshot=config.get("provider_price_snapshot"))
    # R1-c:批次终态由逐路线分类汇总(任一异常失败 → failed,不再无条件
    # completed;合法停留不算失败)
    terminal_summary = batch_terminal_summary(
        list(manifest["route_order"]), terminal)
    report = {
        "status": terminal_summary["status"],
        "terminal_summary": terminal_summary,
        "batch_sha256": identity["sha256"],
        "batch_short": identity["short"],
        "split": split,
        "model": {k: v for k, v in model_block.items() if k != "model_setup"},
        "capacity": capacity,
        "n_routes": len(manifest["route_order"]),
        "terminal_states": {rid: {k: v for k, v in (terminal.get(rid) or {}).items()
                                  if k in ("stop_reason", "failed",
                                           "exit_code", "export_ok",
                                           "predictions_sha256")}
                            for rid in manifest["route_order"]},
        "merged": {k: v for k, v in merged.items() if k != "per_route"},
        "api_account": account,
    }
    (batch_root / "batch_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n", encoding="utf-8")
    logf.close()
    return report


def merge_predictions_terminal(
    *, batch_root: Path, manifest: dict, config: dict,
    export_policy: dict,
) -> dict:
    """独立归并入口(读取已持久化的批次身份与 worker 终态;幂等可重复)。"""
    identity = json.loads(
        (Path(batch_root) / "batch_identity.json").read_text(
            encoding="utf-8"))
    terminal: dict[str, dict] = {}
    for rid in manifest["route_order"]:
        sp = Path(batch_root) / "workers" / f"{rid}.status.json"
        if sp.is_file():
            terminal[rid] = json.loads(sp.read_text(encoding="utf-8"))
    return merge_predictions(
        batch_root=batch_root,
        runs_root=Path(batch_root) / "runs", manifest=manifest,
        identity=identity, export_policy=export_policy, terminal=terminal)


# ---------------------------------------------------------------- 协调器


class BatchCoordinator:
    """20 路并行协调器(进程内长驻;SSH 短连接只读 status/progress)。"""

    def __init__(
        self, *, batch_root: Path, runs_root: Path, manifest: dict,
        identity: dict, config: dict, provider: str, model_id: str,
        request_params: dict, timeout_s: float, export_policy: dict,
        max_parallel: int = 20, poll_interval_s: float = 10.0,
        worker_wall_clock_cap_s: float = 8 * 3600,
        max_worker_respawns: int = 2,
        worker_cmd_builder=None, progress_log=None,
        test_scripted: str | None = None,
    ) -> None:
        self.batch_root = Path(batch_root)
        self.runs_root = Path(runs_root)
        self.manifest = manifest
        self.identity = identity
        self.config = config
        self.provider = provider
        self.model_id = model_id
        self.request_params = request_params
        self.timeout_s = timeout_s
        self.export_policy = export_policy
        self.max_parallel = max_parallel
        self.poll_interval_s = poll_interval_s
        self.wall_cap_s = worker_wall_clock_cap_s
        self.max_respawns = max_worker_respawns
        self.test_scripted = test_scripted
        self._worker_cmd_builder = worker_cmd_builder or self._default_worker_cmd
        self.progress: dict = {}
        self._log = progress_log
        self.gate = FileRateGate(
            self.batch_root / "gate",
            rpm=config["rate"]["rpm"], tpm=config["rate"]["tpm"],
            max_calls=config["rate"]["max_calls"],
            cooldown_cap_s=config["rate"]["cooldown_cap_s"],
            acquire_timeout_s=config["rate"]["acquire_timeout_s"],
            max_in_flight=int(config["rate"].get("max_in_flight", 0) or 0),
        )
        self.workers_dir = self.batch_root / "workers"
        self.logs_dir = self.batch_root / "logs"
        for d in (self.workers_dir, self.logs_dir, self.runs_root):
            d.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------ 基础

    def _default_worker_cmd(self, plan_path: Path) -> list[str]:
        env = dict(os.environ)
        python = env.get("PATHWAY_V43_PYTHON") or sys.executable
        return [python, "-m", "pathway_v43", "batch-worker",
                "--plan", str(plan_path)]

    @staticmethod
    def _repo_root() -> Path:
        from .config import repo_root

        return repo_root()

    def log(self, message: str) -> None:
        line = f"{time.strftime('%Y-%m-%dT%H:%M:%S%z')} {message}"
        if self._log:
            self._log(line)
        with open(self.batch_root / "coordinator.log", "a",
                  encoding="utf-8") as f:
            f.write(line + "\n")

    def route_ids(self) -> list[str]:
        return list(self.manifest["route_order"])

    def run_id_of(self, route_id: str) -> str:
        return run_id_for_route(self.identity["short"],
                                self.manifest["split"], route_id)

    def terminal_states(self) -> dict[str, dict]:
        out = {}
        for rid in self.route_ids():
            sp = self.workers_dir / f"{rid}.status.json"
            if sp.is_file():
                try:
                    out[rid] = json.loads(sp.read_text(encoding="utf-8"))
                except Exception:
                    pass
        return out

    def write_progress(self, running: dict[str, dict]) -> None:
        snap = {
            "batch_short": self.identity["short"],
            "split": self.manifest["split"],
            "n_routes": len(self.route_ids()),
            "n_terminal": len(self.terminal_states()),
            "running": {rid: {"pid": p["proc"].pid,
                              "started_at": p["started_at"],
                              "route_id": rid}
                        for rid, p in running.items()},
            "gate": {k: v for k, v in self.gate.snapshot().items()
                     if k in ("total_requests", "total_429",
                              "total_forbidden", "stopped",
                              "tokens_in_window")},
            "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        }
        tmp = self.batch_root / "progress.json.tmp"
        tmp.write_text(
            json.dumps(snap, ensure_ascii=False, indent=2, sort_keys=True)
            + "\n", encoding="utf-8")
        os.replace(tmp, self.batch_root / "progress.json")
        self.progress = snap

    def _spawn(self, route_id: str) -> dict:
        plan = {
            "route_id": route_id,
            "run_id": self.run_id_of(route_id),
            "root_smiles": self._root_of(route_id),
            "runs_root": str(self.runs_root),
            "quarantine_root": str(self.batch_root / "quarantine"),
            "model": {"provider": self.provider,
                      "model_id": self.model_id,
                      "request_params": self.request_params,
                      "timeout_s": self.timeout_s,
                      "policy_overrides": dict(
                          self.config.get("prediction_policy_overrides")
                          or {})},
            "budgets": self.config["budgets"],
            "export_policy": self.export_policy,
            "status_path": str(self.workers_dir / f"{route_id}.status.json"),
        }
        if self.test_scripted:
            plan["test_scripted"] = self.test_scripted
        plan_path = self.workers_dir / f"{route_id}.plan.json"
        plan_path.write_text(
            json.dumps(plan, ensure_ascii=False, indent=2, sort_keys=True)
            + "\n", encoding="utf-8")
        log_path = self.logs_dir / f"{route_id}.log"
        logf = open(log_path, "ab")
        env = self._worker_env()
        proc = subprocess.Popen(
            self._worker_cmd_builder(plan_path), stdout=logf, stderr=logf,
            env=env, cwd=str(self._repo_root()),
        )
        self.log(f"spawn {route_id} pid={proc.pid} run_id={plan['run_id']}")
        return {"proc": proc, "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                "started_monotonic": time.monotonic(), "logf": logf,
                "respawns": 0, "attempts": 1}

    def _root_of(self, route_id: str) -> str:
        for row in self.manifest["routes"]:
            if row["route_id"] == route_id:
                return row["root_smiles"]
        raise BatchError(f"route_id 不在输入清单:{route_id}",
                         {"route_id": route_id})

    def _worker_env(self) -> dict:
        """worker 环境:继承 + OMP 单线程 + 共享闸门路径。

        凭证只经环境传递,不落盘不打印;``V43_LLM_RATE_GATE`` 指向批次
        根下的共享闸门目录(20 个 worker 的 OpenAICompatibleClient 共同
        遵守同一 RPM/TPM/预算/停止状态)。"""
        env = dict(os.environ)
        env["OMP_NUM_THREADS"] = "1"
        env["PYTHONPATH"] = str(self._repo_root() / "src")
        env["V43_LLM_RATE_GATE"] = str(self.batch_root / "gate")
        return env

    # ------------------------------------------------------------ 主循环

    def run_to_completion(self) -> dict:
        running: dict[str, dict] = {}
        respawns: dict[str, int] = {}
        try:
            while True:
                # 回收退出的 worker(退出后重读该路线状态文件,不以旧快照判断)
                for rid, p in list(running.items()):
                    code = p["proc"].poll()
                    if code is None:
                        if (time.monotonic() - p["started_monotonic"]
                                > self.wall_cap_s):
                            p["proc"].kill()
                            self.log(f"kill {rid}: wall clock cap exceeded")
                        continue
                    p["logf"].close()
                    del running[rid]
                    status = self.terminal_states().get(rid) or {}
                    if status.get("finished_at"):
                        self.log(f"worker done {rid} exit={code} "
                                 f"stop={status.get('stop_reason', '')}")
                        continue
                    # worker 异常退出且无终态:恢复未完成路线(重试有上限)
                    gate_stopped = self.gate.is_stopped()
                    budget_capped = (self.gate.snapshot()["total_requests"]
                                     >= int(self.config["rate"]["max_calls"]))
                    if (gate_stopped or budget_capped
                            or respawns.get(rid, 0) >= self.max_respawns):
                        self.log(
                            f"worker failed {rid} exit={code}; no more respawn "
                            f"(stopped={gate_stopped} budget={budget_capped})")
                        self._write_failure_status(rid, code)
                        continue
                    respawns[rid] = respawns.get(rid, 0) + 1
                    self.log(f"respawn {rid} (attempt {respawns[rid] + 1})")
                terminal = self.terminal_states()
                gate_stopped = self.gate.is_stopped()
                budget_used = self.gate.snapshot()["total_requests"]
                budget_capped = budget_used >= int(self.config["rate"]["max_calls"])
                # 补位派发:保持 20 路同时运行
                if not (gate_stopped or budget_capped):
                    for rid in self.route_ids():
                        if len(running) >= self.max_parallel:
                            break
                        if rid in running or terminal.get(rid, {}).get(
                                "finished_at"):
                            continue
                        running[rid] = self._spawn(rid)
                self.write_progress(running)
                self._maybe_release_barrier()
                if (not running
                        and all(terminal.get(r, {}).get("finished_at")
                                for r in self.route_ids())):
                    break
                if not running and (gate_stopped or budget_capped):
                    # 闸门停止:未完成路线写显式失败终态,保证 20 个终态
                    for rid in self.route_ids():
                        if not terminal.get(rid, {}).get("finished_at"):
                            self._write_failure_status(
                                rid, None,
                                reason=("provider_stopped" if gate_stopped
                                        else "batch_api_budget_exhausted"))
                    continue
                time.sleep(self.poll_interval_s)
        finally:
            for p in running.values():
                if p["proc"].poll() is None:
                    p["proc"].terminate()
                p["logf"].close()
        return self.terminal_states()

    def _maybe_release_barrier(self) -> None:
        """测试钩子(PATHWAY_V43_RUN_BARRIER_DIR × PATHWAY_V43_BATCH_BARRIER):
        worker 在 start_run 身份落盘后写 ``<run_id>.ready`` 并等 GO;
        协调器在**全部预期 worker 都已 ready**(= 同时处于运行态)时写
        GO 放行,并留证据文件。生产环境不设置这两个变量。"""
        barrier_dir = os.environ.get("PATHWAY_V43_RUN_BARRIER_DIR")
        expected = int(os.environ.get("PATHWAY_V43_BATCH_BARRIER", "0"))
        if not barrier_dir or not expected:
            return
        bdir = Path(barrier_dir)
        bdir.mkdir(parents=True, exist_ok=True)
        go = bdir / "GO"
        if go.exists():
            return
        ready = sorted(p.name for p in bdir.glob("*.ready"))
        if len(ready) < expected:
            return
        go.write_text("go\n", encoding="utf-8")
        (bdir / "barrier_evidence.json").write_text(json.dumps({
            "expected": expected, "ready_files": ready,
            "released_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        }, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8")
        self.log(f"barrier_go ready={len(ready)}")

    def _write_failure_status(self, route_id: str, exit_code: int | None,
                              reason: str = "worker_failed_no_terminal") -> None:
        status_path = self.workers_dir / f"{route_id}.status.json"
        status = {"route_id": route_id, "run_id": self.run_id_of(route_id),
                  "failed": reason, "exit_code": exit_code,
                  "finished_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
        tmp = status_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n",
                       encoding="utf-8")
        os.replace(tmp, status_path)
        self.log(f"failure status written {route_id}: {reason}")


def precheck_capacity(batch_root: Path, config: dict,
                      n_workers: int = 20) -> dict:
    """远端内存/CPU/磁盘预检;不足 → CapacityBlocked(不暗改串行)。"""
    n_cpu = os.cpu_count() or 1
    mem_gb = _total_memory_gb()
    free_gb = shutil.disk_usage(str(batch_root)).free / 2**30
    need_mem = n_workers * float(config["capacity"]["memory_gb_per_worker"])
    facts = {
        "n_cpu": n_cpu, "total_memory_gb": round(mem_gb, 1),
        "free_disk_gb": round(free_gb, 1),
        "need_memory_gb": need_mem,
        "memory_gb_per_worker": config["capacity"]["memory_gb_per_worker"],
        "n_workers": n_workers,
    }
    if mem_gb < need_mem:
        raise CapacityBlocked(
            f"内存不足以承载 {n_workers} 路并行(需约 {need_mem:.0f}GB,"
            f"实测 {mem_gb:.0f}GB);明确容量阻塞,不暗改串行", facts)
    if free_gb < float(config["capacity"]["min_free_disk_gb"]):
        raise CapacityBlocked(
            f"磁盘剩余不足:{free_gb:.0f}GB < "
            f"{config['capacity']['min_free_disk_gb']}GB", facts)
    facts["ok"] = True
    return facts


def _total_memory_gb() -> float:
    try:
        out = subprocess.check_output(
            ["sysctl", "-n", "hw.memsize"], text=True)
        return int(out.strip()) / 2**30
    except Exception:
        pass
    try:
        text = Path("/proc/meminfo").read_text(encoding="utf-8")
        for line in text.splitlines():
            if line.startswith("MemTotal:"):
                return int(line.split()[1]) / 2**20
    except Exception:
        pass
    raise CapacityBlocked("无法读取机器内存(/proc/meminfo 与 sysctl 皆失败)", {})


# ---------------------------------------------------------------- 归并


def merge_predictions(*, batch_root: Path, runs_root: Path, manifest: dict,
                      identity: dict, export_policy: dict,
                      terminal: dict[str, dict]) -> dict:
    """按冻结 dev 顺序归并 20 行答卷;失败路线补显式空行(20 行且唯一)。"""
    from .output.export_v3 import export_run_v3, export_policy_hash

    split = manifest["split"]
    merged_dir = Path(batch_root) / "merged"
    merged_dir.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    per_route: list[dict] = []
    for rid in manifest["route_order"]:
        run_id = run_id_for_route(identity["short"], split, rid)
        run_dir = Path(runs_root) / run_id
        status = terminal.get(rid, {})
        answer_kind = "empty"
        failure = status.get("failed") or status.get("export_failed")
        line = None
        if (run_dir / "predictions.jsonl").is_file():
            try:
                # 归并时重建导出并核对新鲜度:导出是派生结果,旧文件
                # (revision/策略落后)在此显式重生成,不带着过期文件判分
                export_run_v3(runs_root, run_id, route_id=rid,
                              policy=export_policy)
                text = (run_dir / "predictions.jsonl").read_text(
                    encoding="utf-8").strip()
                row = json.loads(text)
                if row.get("route_id") != rid:
                    raise BatchError(
                        "答卷 route_id 与清单不一致",
                        {"route_id_file": row.get("route_id"),
                         "route_id_expected": rid})
                lines.append(json.dumps(
                    row, ensure_ascii=False, sort_keys=True,
                    separators=(",", ":")))
                n_steps = len(row.get("steps") or [])
                answer_kind = ("empty" if n_steps == 0 else "full")
                if status.get("stop_reason") not in (
                        "completed", "already_completed") and n_steps:
                    answer_kind = "partial"
                line = "ok"
            except Exception as exc:
                failure = f"export_verify_failed:{exc}"
        if line is None:
            # 显式空答卷(失败/预算耗尽/不可用路线也保持 20 行完整计分)
            row = {"route_id": rid,
                   "root_smiles": status.get("root_smiles")
                   or _root_from_manifest(manifest, rid), "steps": []}
            lines.append(json.dumps(row, ensure_ascii=False, sort_keys=True,
                                    separators=(",", ":")))
            answer_kind = "fallback_empty"
        per_route.append({
            "route_id": rid, "run_id": run_id,
            "stop_reason": status.get("stop_reason", ""),
            "answer_kind": answer_kind,
            "failure_reason": failure,
            "route_state": classify_route_state(status)["route_state"],
            "predictions_sha256": status.get("predictions_sha256"),
        })
    if len(lines) != len(manifest["route_order"]):
        raise BatchError("归并行数与清单不一致",
                         {"n_lines": len(lines)})
    text = "".join(l + "\n" for l in lines)
    out_path = merged_dir / "predictions.jsonl"
    tmp = out_path.with_suffix(".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, out_path)
    # R1-c:归并元数据保留批次终态与逐路线失败标志 —— 固定 20 行只是
    # 文件形制,部分/补空答卷不得被当作"有效完成"
    terminal_summary = batch_terminal_summary(
        list(manifest["route_order"]), terminal)
    meta = {
        "schema_version": BATCH_SCHEMA_VERSION,
        "kind": "batch_merged_predictions",
        "split": split,
        "batch_sha256": identity["sha256"],
        "export_policy_sha256": export_policy_hash(export_policy),
        "n_lines": len(lines),
        "n_unique_route_ids": len({json.loads(l)["route_id"] for l in lines}),
        "batch_terminal_status": terminal_summary["status"],
        "n_routes_failed": terminal_summary["n_failed"],
        "n_routes_export_failed": terminal_summary["n_export_failed"],
        "n_routes_missing": terminal_summary["n_missing"],
        "n_routes_valid_terminal": terminal_summary["n_valid_terminal"],
        "failed_route_ids": terminal_summary["failed_route_ids"],
        "missing_route_ids": terminal_summary["missing_route_ids"],
        "predictions_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "per_route": per_route,
    }
    (merged_dir / "export_metadata.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8")
    return meta


def _root_from_manifest(manifest: dict, route_id: str) -> str:
    for row in manifest["routes"]:
        if row["route_id"] == route_id:
            return row["root_smiles"]
    return ""


# ---------------------------------------------------------------- API 账目


def api_account(runs_root: Path, run_ids: list[str],
                price_snapshot: dict | None = None,
                *, conservative_missing_input: bool = True) -> dict:
    """逐条调用/孤儿/429/用量/费用账(R1-d;持久事实源 = results/ 产物)。

    每条调用一行明细(``calls``):task/attempt、issued、响应/超时/
    传输失败/孤儿、usage 是否存在、已知 token。费用口径:

    - ``cost_estimate_known_usage_cny``:有 usage 的响应按快照价格的小计
      (与既有语义一致);
    - ``cost_estimate_cny``:**只有零缺 usage 才给数**;有任何缺失 →
      ``unknown``;
    - ``conservative_reservation_cny``(usage 缺失的保守预留,上界口径):
      输入按**已发出的请求文本**实算字符数 ÷ 4 的 token 上界估算
      (请求侧事实可证明);输出侧**无请求级 max_tokens 上限** →
      无法证明上界,预留记 ``null`` 且 ``reservation_output_bound``=
      ``unprovable_no_request_output_cap``。运行结束后须以服务商
      用量/账单回填核对;未核实前**费用硬门不得报绿**。

    ``conservative_missing_input`` 关闭时跳过输入预留(仅审计已知部分)。
    """
    totals = {
        "n_calls_issued": 0, "n_responses": 0, "n_orphaned": 0,
        "n_transport_failed": 0, "n_http_429": 0,
        "n_empty_response": 0,
        "input_tokens": 0, "output_tokens": 0, "cached_input_tokens": 0,
        "reasoning_output_tokens": 0, "total_tokens": 0,
        "n_usage_records": 0, "n_usage_missing": 0,
        "elapsed_s_sum": 0.0,
    }
    per_route: dict[str, dict] = {}
    calls: list[dict] = []
    for run_id in run_ids:
        results = Path(runs_root) / run_id / "results"
        t = dict.fromkeys(totals, 0)
        t["elapsed_s_sum"] = 0.0
        if results.is_dir():
            for task_dir in sorted(results.iterdir()):
                if not task_dir.is_dir():
                    continue
                t["n_calls_issued"] += len(
                    list(task_dir.glob("prediction_call.*.json")))
                t["n_orphaned"] += len(
                    list(task_dir.glob("prediction_orphan.*.json")))
                for rp in sorted(task_dir.glob("prediction_response.*.json")):
                    try:
                        envp = json.loads(rp.read_text(encoding="utf-8"))
                    except Exception:
                        calls.append({"run_id": run_id,
                                      "artifact": rp.name,
                                      "read_error": "unreadable"})
                        continue
                    payload = envp.get("payload", {})
                    t["n_responses"] += 1
                    transport = payload.get("transport") or {}
                    if transport.get("error_kind") == "empty_response":
                        t["n_empty_response"] += 1
                    if payload.get("status") == "transport_failed":
                        t["n_transport_failed"] += 1
                    for att in transport.get("http_attempts") or []:
                        if att.get("status") == 429:
                            t["n_http_429"] += 1
                    usage = transport.get("usage") or {}
                    known_tokens: dict = {}
                    if usage:
                        from .adapters.llm_client import normalize_usage

                        norm = normalize_usage(usage)
                        for key in ("input_tokens", "output_tokens",
                                    "cached_input_tokens",
                                    "reasoning_output_tokens",
                                    "total_tokens"):
                            if norm.get(key) is not None:
                                t[key] += int(norm[key])
                                known_tokens[key] = int(norm[key])
                        t["n_usage_records"] += 1
                    else:
                        t["n_usage_missing"] += 1
                    t["elapsed_s_sum"] += float(
                        transport.get("elapsed_s") or 0)
                    calls.append({
                        "run_id": run_id, "task_id": task_dir.name,
                        "attempt": payload.get("attempt"),
                        "status": payload.get("status"),
                        "error_kind": transport.get("error_kind"),
                        "n_http_attempts": len(
                            transport.get("http_attempts") or []),
                        "usage_present": bool(usage),
                        "known_tokens": known_tokens or None,
                        "elapsed_s": transport.get("elapsed_s"),
                    })
        per_route[run_id] = t
        for key in totals:
            if key == "elapsed_s_sum":
                totals[key] += t[key]
            else:
                totals[key] += t.get(key, 0)
    account = {"per_route": per_route, "totals": totals, "calls": calls,
               "usage_basis": "response_provided_only_missing_marked"}
    if price_snapshot:
        p = price_snapshot
        known = (totals["n_usage_records"] > 0
                 and totals["n_usage_missing"] == 0)

        def _cost(inp: int, out: int, cache: int) -> float:
            return (inp / 1e6 * p["input_cny_per_m"]
                    + out / 1e6 * p["output_cny_per_m"]
                    + cache / 1e6 * p["cache_read_cny_per_m"])

        if known and totals["total_tokens"] > 0:
            account["cost_estimate_cny"] = round(_cost(
                totals["input_tokens"] - (totals["cached_input_tokens"] or 0),
                totals["output_tokens"], totals["cached_input_tokens"] or 0), 4)
            account["cost_basis"] = (
                f"snapshotted prices {p['source']} @ {p['checked']};"
                "reasoning billed as output")
        elif totals["n_usage_records"] > 0:
            # 部分 usage 已知:已知部分单列估算;残差(超时/传输失败/悬空
            # attempt,提供者可能已计费)保持 unknown —— 不把部分估算当总账
            account["cost_estimate_known_usage_cny"] = round(_cost(
                totals["input_tokens"] - (totals["cached_input_tokens"] or 0),
                totals["output_tokens"], totals["cached_input_tokens"] or 0), 4)
            account["cost_estimate_cny"] = "unknown"
            account["cost_basis"] = (
                f"known-usage portion priced at {p.get('source', 'unknown')}"
                f" @ {p.get('checked', 'unknown')};"
                f" {totals['n_usage_missing']} attempt(s) without usage "
                "(timeout/transport/orphan) remain unknown")
        else:
            account["cost_estimate_cny"] = "unknown"
            account["cost_basis"] = "usage incomplete; not estimated"
        # ---- R1-d:usage 缺失/孤儿的保守预留(仅当存在未核实调用) ----
        if totals["n_usage_missing"] > 0 or totals["n_orphaned"] > 0:
            if conservative_missing_input:
                reserved_input_tokens = 0
                for run_id in run_ids:
                    results = Path(runs_root) / run_id / "results"
                    if not results.is_dir():
                        continue
                    # 需要预留的 = 有响应但无 usage 的调用(超时后
                    # 成功重试/传输失败);孤儿调用只有 request_hash
                    # 无请求文本,单独计数不入文本预留
                    for rp in sorted(results.glob(
                            "*/prediction_response.*.json")):
                        try:
                            envp = json.loads(rp.read_text(encoding="utf-8"))
                        except Exception:
                            continue
                        payload = envp.get("payload", {})
                        transport = payload.get("transport") or {}
                        if transport.get("usage"):
                            continue
                        # 请求侧文本:从对应 call 产物取 request_hash
                        # 不可反推;请求体不含在产物中,字符上界
                        # 不可证明 → 以该 run 的 prediction_task
                        # 文本长度作为可证明的请求规模上界来源
                        task_dir = rp.parent
                        tp = task_dir / "prediction_task.json"
                        if not tp.is_file():
                            continue
                        try:
                            task_env = json.loads(
                                tp.read_text(encoding="utf-8"))
                            task_text = canonical_json(
                                task_env.get("payload", {}))
                        except Exception:
                            continue
                        reserved_input_tokens += max(1, len(task_text) // 4)
                # 输出上界:请求未设 max_tokens,输出规模不可证明 → 不臆造
                account["conservative_reservation"] = {
                    "input_tokens_upper": reserved_input_tokens,
                    "input_cost_upper_cny": round(
                        reserved_input_tokens / 1e6
                        * p["input_cny_per_m"], 4),
                    "output_bound": "unprovable_no_request_output_cap",
                    "output_cost_upper_cny": None,
                    "orphan_calls_not_reserved": totals["n_orphaned"],
                    "basis": (
                        "input: issued request text length // 4 chars"
                        " (request-side provable); output: no request"
                        "-level token cap -> no provable upper bound;"
                        " must reconcile with provider statement/billing"
                        " before cost gate can pass"),
                }
            else:
                account["conservative_reservation"] = {
                    "skipped": "conservative_missing_input=False"}
        account["price_snapshot"] = p
    return account
