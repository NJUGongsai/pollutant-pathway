"""S5b 编排器 —— 298 题逐 qid 驱动 PPV1 run(40 路并发;断点续跑;
契约登记 s5b-orchestrator-1)。

职责与边界:

- 逐 qid 驱动完整 PPV1 公共链(start→模型响应→…→endpoint/导出),
  每题一个独立 run 根 + 独立账本(run 目录 flock 互斥由 runflow 保证);
- **全局最多 40 个真实请求在途**:批级 FileRateGate(max_in_flight=40,
  RPM/TPM 滑窗、429 全局冷却、401/403/402 付费停止、批次调用数预算
  max_calls)+ 至多 40 个并发 worker 进程(每 worker OMP_NUM_THREADS=1,
  一题一进程,进程级崩溃隔离);
- **断点续跑**:已完成 qid(终态 case 文件)SKIP;无 case 文件的
  qid 复跑(run 已存在 ⇒ resume_ppv1_run 幂等续跑;不存在 ⇒ start);
- 逐题终态落盘 ``cases/<qid>.json``(stop_reason/endpoint/调用/usage/
  费用状态;合法终态补位到 298——失败题留分母、不剔题,失败有单独
  状态与原因);
- 凭证:父进程从 env 文件(沿 ``batch.load_env_file`` 只取 ``V43_LLM_*``
  键)或当前环境注入 worker 子进程 env;密钥不落盘不打印不入日志;
- 本模块不执行判分(判分在封存答卷后由 s5b_scoring 走
  evaluate_scientific;金标只在判分进程进入)。

冒烟/全量同一入口:``--limit N`` / ``--qids`` 取冻结注册序前 N 题
(段 1/2 冒烟 = 正式批次前缀,同一批根同一身份续跑,不借冒烟改配置)。
"""

from __future__ import annotations

import fcntl
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from ..adapters.rate_gate import FileRateGate
from ..domain.models import now_iso

S5B_ORCHESTRATOR_VERSION = "s5b-orchestrator-1"

# 批级缺省闸门参数(发车当日按提供者快照刷新;RPM 200/TPM 3M 快照的
# 保守余量沿老复测口径)
S5B_DEFAULT_GATE_RPM = 180
S5B_DEFAULT_GATE_TPM = 2_700_000
# R5(S5b W6):首批每 qid 最多 1 次 logical 请求 ×(初次 + 4 次 HTTP
# 重试)= 5 总 HTTP 尝试 ⇒ 298×1×5 = **1490** 理论 gate cap(不盲用
# 旧 894/600;新配置数值,不声称旧真实 env 也用 4)
S5B_DEFAULT_GATE_MAX_CALLS = 1490
S5B_DEFAULT_MAX_IN_FLIGHT = 40
S5B_DEFAULT_WORKERS = 40

# 预注册单步预算缺省(search_limits 十上限;P1 候选值,冒烟后定型)
# R5(S5b W6):max_real_model_requests 1(首批每 qid 1 logical;合法
# deterministic recorded 可 0)—— 题级/适配层新 logical retry 0;
# 仅 HTTP 429 走同一 request/idempotency key 的冻结有界传输重试;
# 格式反馈 0(format_feedback 0,不进反馈轮)
S5B_DEFAULT_PROFILE_POLICY = {
    "search_limits": {
        "max_alternative_hypotheses_per_parent": 8,
        "max_attempts_per_hypothesis": 1,
        "max_product_expansion_width": 2,
        "max_search_depth": 1,
        "max_total_search_actions": 48,
        "max_scenario_transitions": 0,
        "max_reopens_per_hypothesis": 0,
        "max_real_model_requests": 1,
        "max_retrievals_per_parent": 1,
        "max_retrievals_total": 8,
    },
    "format_feedback_policy": {
        "max_format_feedback_rounds": 0,
    },
}

TERMINAL_CASE_STATUSES = frozenset({"completed", "failed"})

# R5(S5b W6):worker 总时限纪律 —— 0 = 禁用(首批默认,沿现政策);
# 正值 = monotonic 总时限 + terminate/grace/kill;**负值配置拒**;
# 非正值不得隐式 kill 而少跑题
S5B_CASE_SCHEMA_VERSION = "s5b-case-1"


class S5bOrchestratorError(RuntimeError):
    """编排器契约违反(结构化 fail-closed)。"""

    def __init__(self, message: str, detail: dict | None = None):
        super().__init__(message)
        self.detail = detail or {}


# ---------------------------------------------------------------- 环境注入


def _model_env(env_file: str | Path | None) -> dict[str, str]:
    """worker env 的 V43_LLM_* 键(只取模型键;密钥不打印不落盘)。"""
    env: dict[str, str] = {}
    if env_file is not None:
        from ..batch import load_env_file

        loaded = load_env_file(env_file)
        env.update({k: str(v) for k, v in loaded.items()
                    if k.startswith("V43_LLM_")})
    for key, value in os.environ.items():
        if key.startswith("V43_LLM_"):
            env[key] = str(value)
    return env


def _worker_env(env_file: str | Path | None,
                gate_dir: str | Path) -> dict[str, str]:
    """worker 子进程 env(注入 V43_LLM_* 凭证键;密钥只在子进程内存,
    不打印不落盘;OMP_NUM_THREADS=1 每进程单线程;PYTHONPATH 含仓 src
    供 ``python -m pathway_v43.pollutant.s5b_worker`` 解析)。"""
    env = dict(os.environ)
    env.update(_model_env(env_file))
    env["OMP_NUM_THREADS"] = "1"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["V43_LLM_RATE_GATE"] = str(gate_dir)
    src = str(Path(__file__).resolve().parents[2])
    env["PYTHONPATH"] = (
        src + (os.pathsep + env["PYTHONPATH"]
               if env.get("PYTHONPATH") else ""))
    return env


# ---------------------------------------------------------------- case 状态


def case_path(batch_root: Path, qid: str) -> Path:
    return batch_root / "cases" / f"{qid}.json"


def read_case(batch_root: Path, qid: str) -> dict | None:
    path = case_path(batch_root, qid)
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None


def is_terminal(case: dict | None) -> bool:
    return bool(case) and str(case.get("status")) in TERMINAL_CASE_STATUSES


def validate_case(case: dict | None, qid: str, *,
                  expected_run_id: str = "") -> dict:
    """R4:validated case reader —— 校验后才可 SKIP/汇总/评分。

    校验面(坏 case ⇒ 结构化拒,不当终态消费):
    - qid 一致(case["qid"] 必须等于请求 qid;外 qid 拒);
    - run_id 一致(expected 给出时;错 identity 拒);
    - schema_version = s5b-case-1(worker 落盘时写入;缺/错 ⇒ 拒);
    - 终态合法性:status ∈ {completed, failed};completed 须携带
      stop_reason(空 stop_reason 的 completed 拒);**env_check_only
      不写正式 completed**(env check 落 ``cases/env_check/`` 另文件,
      主 cases/ 下的 env_check_only 行 ⇒ 拒,不算终态);
    - export_digest:completed 时须为字符串(可空 = 失败导出的诚实
      空串;非字符串类型拒)。
    返回 {ok, reasons, status}。
    """
    reasons: list[str] = []
    if not isinstance(case, dict) or not case:
        return {"ok": False, "reasons": ["case_missing_or_invalid"],
                "status": ""}
    status = str(case.get("status") or "")
    if str(case.get("qid") or "") != str(qid):
        reasons.append("qid_mismatch")
    if expected_run_id and str(case.get("run_id") or "") \
            and str(case.get("run_id")) != str(expected_run_id):
        reasons.append("run_id_mismatch")
    if str(case.get("case_schema_version") or "") != S5B_CASE_SCHEMA_VERSION:
        reasons.append("case_schema_version_missing_or_invalid")
    if status == "completed" and str(case.get("stop_reason") or "") == "":
        reasons.append("completed_without_stop_reason")
    if status == "completed" \
            and str(case.get("stop_reason") or "") == "env_check_only":
        reasons.append("env_check_only_is_not_official_completed")
    if status == "completed" and not isinstance(
            case.get("export_digest"), str):
        reasons.append("export_digest_not_string")
    return {"ok": not reasons, "reasons": reasons, "status": status}


def read_validated_case(batch_root: Path, qid: str, *,
                        expected_run_id: str = "",
                        strict: bool = True) -> dict | None:
    """读取 + R4 校验;strict=True 时坏 case ⇒ S5bOrchestratorError
    (fail-closed,SKIP/汇总/评分前拒);strict=False 返回 None(诊断
    场景)。合法终态返回 case dict;非终态/缺文件返回 None。"""
    case = read_case(batch_root, qid)
    if case is None:
        return None
    verdict = validate_case(case, qid, expected_run_id=expected_run_id)
    if not verdict["ok"]:
        if strict:
            raise S5bOrchestratorError(
                f"case 文件校验失败(qid={qid};SKIP/汇总/评分前拒,"
                f"不消费坏终态):{verdict['reasons']}", {
                    "kind": "s5b_case_validation_failed",
                    "qid": str(qid), "reasons": verdict["reasons"],
                    "status": verdict["status"]})
        return None
    if not is_terminal(case):
        return None
    return case


def write_case_atomic(path: Path, payload: dict) -> None:
    """case 原子 replace(R4:tmp + os.replace;半截文件不可见)。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True,
                   indent=1) + "\n", encoding="utf-8")
    os.replace(tmp, path)


# ---------------------------------------------------------------- 主入口


def run_s5b_batch(
    batch_root: str | Path,
    *,
    runs_root: str | Path,
    env_file: str | Path | None = None,
    workers: int = S5B_DEFAULT_WORKERS,
    max_in_flight: int = S5B_DEFAULT_MAX_IN_FLIGHT,
    gate_rpm: int = S5B_DEFAULT_GATE_RPM,
    gate_tpm: int = S5B_DEFAULT_GATE_TPM,
    gate_max_calls: int = S5B_DEFAULT_GATE_MAX_CALLS,
    profile_policy: dict | None = None,
    question_limit: int | None = None,
    qids: list[str] | None = None,
    poll_s: float = 10.0,
    python_bin: str | None = None,
    worker_timeout_s: float = 0.0,
) -> dict:
    """40 路编排主循环(父进程;子进程 = 一题一 worker)。

    - batch_root 必须已由 s5b_builder 构建(batch_manifest.json 在);
    - profile_policy / gate 参数在**发车时**写冻结副本
      (``orchestration.json``)——同批根续跑时原样复用(改参 ⇒ 拒,
      一致性沿预注册纪律);
    - **R4:单协调者 flock**(batch_root/coord.lock;双协调者结构化
      拒 —— 与 run 级 driver.lock 并存,不冲突);死亡未封存恢复只有
      一份最终 case、一次评分(评分在协调者锁内执行);
    - **R5:worker_total_timeout** 0=禁用(首批默认,沿现政策;非正值
      不得隐式 kill 而少跑题);正值 = monotonic 总时限 + terminate/
      grace/kill + 死亡占位对账;**负值配置拒**;stderr 独立有界日志/
      主动 drain(防 PIPE 阻塞);
    - 返回批报告 dict(同时落盘 batch_report.json + progress.json)。
    """
    batch_root = Path(batch_root)
    runs_root = Path(runs_root)
    if float(worker_timeout_s) < 0:
        raise S5bOrchestratorError(
            f"worker_timeout_s 非法:{worker_timeout_s}(0=禁用,正值="
            "monotonic 总时限;负值拒)", {
                "kind": "s5b_worker_timeout_invalid",
                "worker_timeout_s": float(worker_timeout_s)})
    worker_timeout_s = float(worker_timeout_s)
    manifest_path = batch_root / "batch_manifest.json"
    if not manifest_path.is_file():
        raise S5bOrchestratorError(
            f"批根缺 batch_manifest.json(先跑 s5b_builder):{batch_root}",
            {"kind": "s5b_batch_manifest_missing",
             "batch_root": str(batch_root)})
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    registration = list(manifest.get("registration_order") or [])
    if qids is not None:
        wanted = [str(q) for q in qids]
        unknown = [q for q in wanted if q not in registration]
        if unknown:
            raise S5bOrchestratorError(
                f"指定 qid 不在冻结注册序内:{unknown[:5]}(不猜题)",
                {"kind": "s5b_qid_not_registered", "unknown": unknown})
        order = wanted
    else:
        order = registration
    if question_limit is not None:
        order = order[:int(question_limit)]
    if not order:
        raise S5bOrchestratorError(
            "空执行清单(零题;fail-closed)", {
                "kind": "s5b_empty_question_list"})
    # ---- 发车参数冻结(同批根续跑复用;变更拒绝) ----
    frozen = {
        "orchestrator_version": S5B_ORCHESTRATOR_VERSION,
        "workers": int(workers),
        "max_in_flight": int(max_in_flight),
        "gate_rpm": int(gate_rpm),
        "gate_tpm": int(gate_tpm),
        "gate_max_calls": int(gate_max_calls),
        "profile_policy": profile_policy or S5B_DEFAULT_PROFILE_POLICY,
        "runs_root": str(runs_root),
        "frozen_at": now_iso(),
    }
    orch_path = batch_root / "orchestration.json"
    if orch_path.is_file():
        existing = json.loads(orch_path.read_text(encoding="utf-8"))
        comparable = {k: existing.get(k) for k in frozen
                      if k != "frozen_at"}
        if comparable != {k: frozen[k] for k in frozen
                          if k != "frozen_at"}:
            raise S5bOrchestratorError(
                "同批根的编排参数与既有冻结副本不一致(改参须新批根;"
                "预注册纪律:首跑不可因中途结果改写)", {
                    "kind": "s5b_orchestration_conflict",
                    "batch_root": str(batch_root)})
    else:
        orch_path.write_text(
            json.dumps(frozen, ensure_ascii=False, sort_keys=True,
                       indent=1) + "\n", encoding="utf-8")
    (batch_root / "profile_policy.json").write_text(
        json.dumps(frozen["profile_policy"], ensure_ascii=False,
                   sort_keys=True, indent=1) + "\n", encoding="utf-8")
    # ---- 批级闸门(状态文件持久;worker 客户端经 env 装载同门;
    # R2:参数首消费核对 —— 状态文件冻结参数与构造参数一致才可用) ----
    gate = FileRateGate(
        batch_root / "gate", rpm=int(gate_rpm), tpm=int(gate_tpm),
        max_calls=int(gate_max_calls),
        max_in_flight=int(max_in_flight))
    gate.verify_config()
    gate_dir = str(batch_root / "gate")
    # ---- R4:单协调者 flock(与 run 级 driver.lock 并存;双协调者拒) ----
    coord_lock_path = batch_root / "coord.lock"
    coord_lock_path.parent.mkdir(parents=True, exist_ok=True)
    coord_fh = open(coord_lock_path, "a+", encoding="utf-8")
    try:
        try:
            fcntl.flock(coord_fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise S5bOrchestratorError(
                "批根已有活动协调者(单协调者纪律:双协调者结构化拒 —— "
                "flock 是权威;崩溃 OS 自动释放,新协调者可接管;评分/"
                "汇总在协调者锁内执行,死亡未封存恢复只有一份最终 case)",
                {"kind": "s5b_coordinator_active",
                 "batch_root": str(batch_root),
                 "pid": os.getpid()}) from exc
        return _run_batch_loop(
            batch_root=batch_root, runs_root=runs_root, manifest=manifest,
            order=order, env_file=env_file, workers=workers,
            gate_dir=gate_dir, gate=gate, python_bin=python_bin,
            worker_timeout_s=worker_timeout_s, poll_s=poll_s,
            started_at_wall=time.time())
    finally:
        try:
            fcntl.flock(coord_fh.fileno(), fcntl.LOCK_UN)
        except OSError:
            pass
        coord_fh.close()


def _run_batch_loop(*, batch_root: Path, runs_root: Path,
                    manifest: dict, order: list, env_file,
                    workers: int, gate_dir: str, gate: FileRateGate,
                    python_bin, worker_timeout_s: float, poll_s: float,
                    started_at_wall: float) -> dict:
    """执行主循环(协调者锁内;R4 validated case / R5 超时纪律)。"""
    env = _worker_env(env_file, gate_dir)
    py = python_bin or sys.executable

    def _terminal_case(qid: str) -> dict | None:
        return read_validated_case(
            batch_root, qid, expected_run_id=_run_id_of(manifest, qid))

    pending = [q for q in order if _terminal_case(q) is None]
    skipped = len(order) - len(pending)
    running: dict[str, dict] = {}
    started_at = time.time()
    failures: list[str] = []
    while pending or running:
        # ---- 收割:进程退出 ⇒ case 文件由 worker 落盘(校验后消费);
        # 缺失/坏 case ⇒ 失败补位(R4:死亡未封存恢复只有一份最终 case) ----
        for qid in list(running):
            entry = running[qid]
            proc: subprocess.Popen = entry["proc"]
            # ---- R5:正值 worker 总时限(monotonic;terminate/grace/
            # kill;死亡占位对账;0 = 禁用不 kill) ----
            if proc.poll() is None and worker_timeout_s > 0 \
                    and time.monotonic() - entry["started_monotonic"] \
                    > worker_timeout_s:
                entry["timeout_killed"] = True
                proc.terminate()
                entry["terminated_at"] = time.monotonic()
            if proc.poll() is None and entry.get("timeout_killed") \
                    and "terminated_at" in entry \
                    and time.monotonic() - entry["terminated_at"] > 5.0:
                proc.kill()  # grace 5s 后强杀
            if proc.poll() is None:
                continue
            running.pop(qid)
            stderr_tail = _drain_stderr(entry)
            case = _terminal_case(qid)
            if case is not None:
                if str(case.get("status")) == "failed":
                    failures.append(qid)
            else:
                # worker 死亡/超时未落合法终态 case:失败补位(留分母;
                # 下次续跑可 resume 复原;死亡占位由 gate 对账回收)
                case = {
                    "qid": qid, "run_id": entry.get("run_id") or "",
                    "status": "failed",
                    "case_schema_version": S5B_CASE_SCHEMA_VERSION,
                    "failure_kind": (
                        "worker_timeout_killed"
                        if entry.get("timeout_killed")
                        else "worker_exit_without_case"),
                    "returncode": proc.returncode,
                    "stderr_tail": stderr_tail[-2000:],
                    "recorded_at": now_iso(),
                    "note": ("worker 进程退出未落合法终态 case(崩溃/被杀/"
                             "超时);失败题留 298 分母;重跑本批即 resume"
                             " 续跑"),
                }
                write_case_atomic(case_path(batch_root, qid), case)
                failures.append(qid)
        # ---- 派发:空槽 + 冻结注册序取下一题(stderr 主动 drain) ----
        while pending and len(running) < max(1, int(workers)):
            qid = pending.pop(0)
            if _terminal_case(qid) is not None:
                continue
            run_id = _run_id_of(manifest, qid)
            cmd = [
                py, "-B", "-m", "pathway_v43.pollutant.s5b_worker",
                "--batch-root", str(batch_root),
                "--runs-root", str(runs_root),
                "--qid", qid,
            ]
            proc = subprocess.Popen(
                cmd, env=env, stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE)
            # R5:stderr 独立有界日志/主动 drain(防 PIPE 写满阻塞
            # worker)
            running[qid] = {
                "proc": proc, "run_id": run_id,
                "started_at": now_iso(),
                "started_monotonic": time.monotonic(),
                "stderr_tail": []}
        _drain_all_stderr(running)
        # R2:父协调者只回收已确认死亡 owner 的占位(无 TTL)
        try:
            gate.reclaim_dead_placeholders()
        except Exception:  # noqa: BLE001 —— 回收失败不阻断主循环(下轮再试)
            pass
        _write_progress(batch_root, order, running, pending,
                        started_at)
        if running or pending:
            time.sleep(poll_s)
    _write_progress(batch_root, order, running, pending, started_at)
    # ---- 汇总(逐题 case + 闸门状态;协调者锁内单次评分由调用方
    # 在锁外显式执行 score 命令 —— 本函数只汇总,判分入口在 s5b_cli) ----
    gate_state = _read_gate_state(batch_root)
    report = summarize_batch(batch_root, order)
    report["skipped_already_terminal"] = skipped
    report["failed_qids"] = failures
    report["gate"] = gate_state
    report["worker_timeout_s"] = worker_timeout_s
    report["coordinator"] = {"pid": os.getpid(),
                             "lock": str(batch_root / "coord.lock")}
    report["wall_clock_s"] = round(time.time() - started_at, 1)
    _write_json(batch_root / "batch_report.json", report)
    return report


def _drain_stderr(entry: dict) -> str:
    """收割时读尽残留 stderr(有界;返回累计尾部)。"""
    proc: subprocess.Popen = entry["proc"]
    tail: list = entry.setdefault("stderr_tail", [])
    try:
        chunk = proc.stderr.read() if proc.poll() is not None else None
    except (OSError, ValueError):
        chunk = None
    if chunk:
        tail.append(chunk.decode("utf-8", errors="replace"))
    return "".join(tail[-50:])


def _drain_all_stderr(running: dict) -> None:
    """主动 drain 在途 worker 的 stderr(非阻塞;防 PIPE 满)。"""
    for entry in running.values():
        proc: subprocess.Popen = entry["proc"]
        try:
            import selectors

            sel = selectors.DefaultSelector()
            sel.register(proc.stderr, selectors.EVENT_READ)
            ready = sel.select(timeout=0)
            sel.close()
            if ready:
                chunk = proc.stderr.read1(65536) \
                    if hasattr(proc.stderr, "read1") else None
                if chunk:
                    entry.setdefault("stderr_tail", []).append(
                        chunk.decode("utf-8", errors="replace"))
                    if len(entry["stderr_tail"]) > 200:
                        entry["stderr_tail"] = \
                            entry["stderr_tail"][-100:]
        except (OSError, ValueError, AttributeError):
            continue


def _run_id_of(manifest: dict, qid: str) -> str:
    for entry in manifest.get("entries") or []:
        if str(entry.get("qid")) == str(qid):
            return str(entry.get("run_id") or "")
    return ""


def _read_gate_state(batch_root: Path) -> dict:
    path = batch_root / "gate" / "gate.json"
    if not path.is_file():
        return {}
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return {"unreadable": True}
    return {k: state.get(k) for k in (
        "total_requests", "total_429", "total_forbidden",
        "max_calls", "max_in_flight", "peak_in_flight", "stopped")}


def _write_progress(batch_root: Path, order: list[str],
                    running: dict, pending: list, started_at: float) -> None:
    cases = {q: read_case(batch_root, q) for q in order}
    done = sum(1 for c in cases.values() if is_terminal(c))
    failed = sum(1 for c in cases.values()
                 if c and str(c.get("status")) == "failed")
    _write_json(batch_root / "progress.json", {
        "n_total": len(order),
        "n_terminal": done,
        "n_failed": failed,
        "n_in_flight": len(running),
        "n_pending": len(pending),
        "in_flight_qids": sorted(running),
        "elapsed_s": round(time.time() - started_at, 1),
        "updated_at": now_iso(),
    })


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True,
                   indent=1) + "\n", encoding="utf-8")


# ---------------------------------------------------------------- 汇总


def summarize_batch(batch_root: str | Path,
                    order: list[str] | None = None) -> dict:
    """逐题 case 汇总(终态/停止原因/调用/usage/费用状态单列)。

    - **R4:validated case reader** —— 校验(qid/run_id/schema/终态/
      env_check-only 拒)后才汇总;坏 case ⇒ 结构化 fail-closed;
    - 合法终态补位到全集(order 缺省 = 注册序全集;失败题留分母);
    - usage 只合计已知(known_usage 小计);任何缺失 ⇒ 总额 unknown;
    - 价格快照存在(batch_root/price_snapshot.json)⇒ 算 known 小计
      费用;缺快照 ⇒ cost_status=no_snapshot(不计价,不冒充)。
    """
    batch_root = Path(batch_root)
    manifest = json.loads(
        (batch_root / "batch_manifest.json").read_text(encoding="utf-8"))
    if order is None:
        order = list(manifest.get("registration_order") or [])
    entries = {str(e.get("qid")): e
               for e in manifest.get("entries") or []}
    rows: list[dict] = []
    n_completed = n_failed = 0
    calls_total = 0
    usage_known = {"input_tokens": 0, "output_tokens": 0,
                   "total_tokens": 0}
    usage_missing_calls = 0
    for qid in order:
        # R4:汇总前校验(坏 case fail-closed,不静默计终态)
        case = read_validated_case(
            batch_root, qid, expected_run_id=_run_id_of(manifest, qid))
        if case is None and read_case(batch_root, qid) is not None:
            # 存在但校验失败/非终态:read_validated_case strict 已抛;
            # 到这里说明非终态(部分写入)—— 按 pending 处理
            case = None
        status = str((case or {}).get("status") or "pending")
        if status == "completed":
            n_completed += 1
        elif status == "failed":
            n_failed += 1
        calls = int((case or {}).get("model_calls") or 0)
        calls_total += calls
        usage = (case or {}).get("usage") or {}
        if usage.get("present"):
            usage_known["input_tokens"] += int(
                usage.get("input_tokens") or 0)
            usage_known["output_tokens"] += int(
                usage.get("output_tokens") or 0)
            usage_known["total_tokens"] += int(
                usage.get("total_tokens") or 0)
        elif calls:
            usage_missing_calls += calls
        rows.append({
            "qid": qid,
            "run_id": str((entries.get(qid) or {}).get("run_id") or
                          (case or {}).get("run_id") or ""),
            "status": status,
            "stop_reason": str((case or {}).get("stop_reason") or ""),
            "endpoint_status": str((case or {}).get("endpoint_status")
                                   or ""),
            "export_digest": str((case or {}).get("export_digest") or ""),
            "model_calls": calls,
            "failure_kind": str((case or {}).get("failure_kind") or ""),
        })
    price = _price_snapshot(batch_root)
    cost_known = None
    if price:
        cost_known = round(
            (usage_known["input_tokens"] * float(price["input_per_mtok"])
             + usage_known["output_tokens"] *
             float(price["output_per_mtok"])) / 1_000_000.0, 4)
    return {
        "s5b_orchestrator_version": S5B_ORCHESTRATOR_VERSION,
        "n_total": len(order),
        "n_completed": n_completed,
        "n_failed": n_failed,
        "n_pending": len(order) - n_completed - n_failed,
        "cases": rows,
        "account": {
            "model_calls_total": calls_total,
            "usage_known": dict(usage_known),
            "usage_missing_calls": usage_missing_calls,
            "usage_status": (
                "known" if calls_total and not usage_missing_calls
                else ("none" if not calls_total else "partial_unknown")),
            "cost_known_cny": cost_known,
            "cost_status": (
                "no_snapshot" if not price else
                ("known_usage_subtotal" if not usage_missing_calls
                 else "known_usage_subtotal_with_missing_unknown_total")),
        },
        "note": ("失败题留 298 分母、不剔题;usage 缺失保守预留"
                 "(known-usage 小计与总费用分开);账单回填后核对"),
        "generated_at": now_iso(),
    }


def _price_snapshot(batch_root: Path) -> dict | None:
    path = batch_root / "price_snapshot.json"
    if not path.is_file():
        return None
    try:
        snapshot = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None
    if not snapshot.get("input_per_mtok") or \
            not snapshot.get("output_per_mtok"):
        return None
    return snapshot
