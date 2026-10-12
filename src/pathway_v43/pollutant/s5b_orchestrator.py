"""S5b 编排器 —— 298 题逐 qid 驱动 PPV1 run(40 路并发;断点续跑;
契约登记 s5b-orchestrator-3)。

职责与边界:

- 逐 qid 驱动完整 PPV1 公共链(start→模型响应→…→endpoint/导出),
  每题一个独立 run 根 + 独立账本(run 目录 flock 互斥由 runflow 保证);
- **全局最多 40 个真实请求在途**:批级 FileRateGate(max_in_flight=40,
  RPM/TPM 滑窗、429 全局冷却、401/403/402 付费停止、批次调用数预算
  max_calls)+ 至多 40 个并发 worker 进程(每 worker OMP_NUM_THREADS=1,
  一题一进程,进程级崩溃隔离);
- **S5B-V3-02 批级金额硬帽(发送前原子预留)**:real 批(付费 HTTP
  发送)发车前必须已冻结批根 ``budget_guard.json``(60 CNY 帽默认 +
  当日价 + 输入保守界 + 输出上限;缺席/坏形状 ⇒ 结构化拒,先于任何
  worker 派发);配置冻结进 ``orchestration.json`` 与闸门状态文件,
  实际发送链(worker→RealModelAdapter→OpenAICompatibleClient→
  FileRateGate)每次可能付费的发送尝试(含 HTTP retry)在闸门临界
  区内先原子预留,余额不足先于传输拒;失败/超时/未知 usage/孤儿不
  释放可能已付金额;结算幂等;不自动升帽。HTTP1490/1logical/
  format0/40 在途等其他门保持不变;
- **断点续跑**:已完成 qid(终态 case 文件)SKIP;无 case 文件的
  qid 复跑(run 已存在 ⇒ resume_ppv1_run 幂等续跑;不存在 ⇒ start);
- 逐题终态落盘 ``cases/<qid>.json``(stop_reason/endpoint/调用/usage/
  费用状态;合法终态补位到 298——失败题留分母、不剔题,失败有单独
  状态与原因;预算耗尽未作答题同样留分母);
- 凭证:父进程从 env 文件(沿 ``batch.load_env_file`` 只取 ``V43_LLM_*``
  键)或当前环境注入 worker 子进程 env;密钥不落盘不打印不入日志;
- 本模块不执行判分(判分在封存答卷后由 s5b_scoring 走
  evaluate_scientific;金标只在判分进程进入)。

冒烟/全量同一入口:``--limit N`` / ``--qids`` 取冻结注册序前 N 题
(段 1/2 冒烟 = 正式批次前缀,同一批根同一身份续跑,不借冒烟改配置)。

**s5b-orchestrator-3(2026-10-12,HPC 多作业分片适配)**:R4 单协调者
flock 从"整批根一把锁"改为**白名单域锁**(``batch_root/coord/`` 下逐
qid 一把 flock;同 qid 双协调者结构化拒、不相交 qid 白名单多协调者
并发放行)——同一批根上多个 sbatch 分片作业各持不相交 qids 白名单
并发执行,批级闸门(RPM/TPM/max_calls/在途/金额帽)仍经
``FileRateGate`` 跨进程共享。并发写盘加两道保守硬化:orchestration
冻结副本的"读-比对-写"在短 flock(``orchestration.lock``)内串行
(关首写竞态:分片同时首跑不同参时后到者必读到先到者副本 ⇒ 冲突拒,
不再有静默双写窗口);progress/batch_report/orchestration/profile_
policy 落盘改原子 replace(tmp 名含 pid,分片并发写同一文件不互踩
半截)。**版本语义**:协调契约变化由版本承载;既有 s5b-orchestrator-2
批根(如 chenyu s5b_298_20261009_batch2)的 orchestration.json
``orchestrator_version`` 与本版不一致 ⇒ 续跑按预注册纪律拒(改参
须新批根);HPC 首批本来就是新批根,不受影响。**跨节点部署注意**:
qid 白名单锁/闸门锁/driver.lock 全部依赖 flock;死亡占位回收
(``reclaim_dead_placeholders``)按本机 pid 判死,分片作业跨节点时
他节点在途 worker 会被误判死(在途帽放松、金额侧保守不漏)——
首批分片建议约束到同一节点(scripts/hpc/ 部署 runbook 同口径)。
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import resource
import subprocess
import sys
import threading
import time
from contextlib import contextmanager
from pathlib import Path

from ..adapters.rate_gate import FileRateGate, normalize_cost_guard_config
from ..domain.models import now_iso

S5B_ORCHESTRATOR_VERSION = "s5b-orchestrator-3"

# 批根金额守卫机器配置文件(S5B-V3-02;由 s5b_cli budget 落盘,
# 发车时冻结进 orchestration.json 与闸门状态;60 CNY 帽默认)
S5B_BUDGET_GUARD_FILE = "budget_guard.json"
S5B_DEFAULT_BUDGET_CAP_CNY = 60.0

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


# ---------------------------------------------------------------- 白名单域锁


def _qid_lock_name(qid: str) -> str:
    """qid → 协调锁文件名(消毒 + 短哈希;qid→文件名单射)。

    - 文件名安全字符集消毒(``[^A-Za-z0-9._-]`` → ``_``,截 60);
    - 追加 qid 原值的 sha256 前 8 位 ⇒ 不同 qid 必得不同文件名
      (消毒碰撞被哈希区分;同 qid 必同名,锁域判定不依赖消毒)。
    """
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", str(qid))[:60] or "qid"
    digest = hashlib.sha256(str(qid).encode("utf-8")).hexdigest()[:8]
    return f"{safe}-{digest}.lock"


class _WhitelistCoordinatorLocks:
    """R4(v3):白名单域协调者锁 —— 逐 qid 一把 flock。

    语义(s5b-orchestrator-3;替代 v2 的整批根单把 coord.lock):

    - **同 qid 互斥**:另一协调者已持某 qid 的锁 ⇒ 本次获取在该 qid
      处结构化拒(kind=s5b_coordinator_active;先到先得,fail-fast
      先于任何 worker 派发),已获部分全部释放(不留半套锁);
    - **不同 qid 放行**:不相交 qid 白名单的多个协调者并发持有各自
      的锁(HPC sbatch 分片;批级闸门仍跨进程共享);
    - flock 是权威(崩溃 OS 自动释放,新协调者可接管);锁文件内容
      只写持有者 pid/时间披露,写失败不影响锁;
    - 获取按 qid 排序序进行(确定性;LOCK_NB 无死锁环:失败即回滚
      全部已获取锁)。

    v2 兼容:旧批根的遗留 ``coord.lock`` 空文件不再被读写(锁域
    迁移;旧批根本就按 orchestration.json 版本比对拒续跑)。
    """

    def __init__(self, batch_root: Path, qids: list[str]):
        self.batch_root = Path(batch_root)
        # 去重(保序):同 qid 重复进白名单 ⇒ flock 同文件二次打开
        # 自冲突,必须去重后锁;执行语义同集合
        self.qids = list(dict.fromkeys(str(q) for q in qids))
        self.lock_dir = self.batch_root / "coord"
        self._handles: dict[str, object] = {}

    def acquire(self) -> None:
        if not self.qids:
            return  # 空白名单不取锁(上游空清单已拒;防御保持)
        self.lock_dir.mkdir(parents=True, exist_ok=True)
        for qid in sorted(self.qids):
            path = self.lock_dir / _qid_lock_name(qid)
            fh = open(path, "a+", encoding="utf-8")
            try:
                fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as exc:
                fh.close()
                self.release()
                raise S5bOrchestratorError(
                    "qid 已被另一活动协调者持有(白名单域单协调者纪律:"
                    "同 qid 双协调者结构化拒;不相交 qid 分片放行;"
                    "flock 是权威,崩溃 OS 自动释放,新协调者可接管)",
                    {"kind": "s5b_coordinator_active",
                     "batch_root": str(self.batch_root),
                     "conflicting_qid": qid,
                     "requested_qids": sorted(self.qids),
                     "acquired_qids": sorted(self._handles),
                     "pid": os.getpid()}) from exc
            self._handles[qid] = fh
            try:  # 披露写失败不影响锁(锁域只认 flock)
                fh.seek(0)
                fh.truncate()
                fh.write(f"pid={os.getpid()} qid={qid} "
                         f"acquired_at={now_iso()}\n")
                fh.flush()
            except OSError:
                pass

    def release(self) -> None:
        for qid, fh in list(self._handles.items()):
            try:
                fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass
            try:
                fh.close()
            except OSError:
                pass
            self._handles.pop(qid, None)

    def __enter__(self) -> "_WhitelistCoordinatorLocks":
        self.acquire()
        return self

    def __exit__(self, *exc) -> None:
        self.release()


@contextmanager
def _short_flock(path: Path):
    """短临界区互斥(阻塞 flock;用于 orchestration.json 读-比对-写
    的串行化)。持有时长毫秒级,阻塞等待无饥饿风险;无其他锁嵌套。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    fh = open(path, "a+", encoding="utf-8")
    try:
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
        yield fh
    finally:
        try:
            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
        except OSError:
            pass
        fh.close()


def _check_lock_fd_headroom(n_locks: int, workers: int) -> None:
    """qid 锁 fd 余量预检(fail-closed:不足 ⇒ 结构化拒,不在获取
    中途裸抛 OSError(EMFILE))。逐 qid 一把锁 fd + worker 管道
    (每 worker ~3 fd)+ 常规开销。Linux 缺省软限 1024 对 298 题
    + 40 worker 够用;更小软限(如 macOS 256 跑全量)给出可行动
    的 ulimit 提示(HPC 作业脚本已设 ulimit -n 4096)。"""
    soft, _ = resource.getrlimit(resource.RLIMIT_NOFILE)
    needed = int(n_locks) + 3 * max(1, int(workers)) + 16
    if needed > int(soft):
        raise S5bOrchestratorError(
            f"qid 白名单锁 fd 余量不足:需 ~{needed}(锁 {n_locks} + "
            f"worker 管道 + 开销)> RLIMIT_NOFILE 软限 {soft};先 "
            f"ulimit -n 4096 再发车(fail-closed,不中途裸崩)",
            {"kind": "s5b_lock_fd_headroom_insufficient",
             "n_locks": int(n_locks), "workers": int(workers),
             "rlimit_nofile_soft": int(soft),
             "needed_estimate": needed})


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


# ---------------------------------------------------------------- 金额守卫


def load_budget_guard(batch_root: str | Path) -> dict | None:
    """装载并校验批根金额守卫机器配置(S5B-V3-02)。

    - 文件缺席 ⇒ None(scripted 批合法;real 批由 run_s5b_batch 先拒);
    - 坏 JSON/坏形状(非对象、schema 未知、非 CNY、数值字段缺失或
      非正数)⇒ S5bOrchestratorError(kind=s5b_budget_guard_invalid,
      先于任何 worker 派发/传输;不猜默认价格)。

    归一/派生(per_attempt_bound_cny、config_sha256)与闸门/CLI/worker
    同源(rate_gate.normalize_cost_guard_config,单一判据)。"""
    path = Path(batch_root) / S5B_BUDGET_GUARD_FILE
    if not path.is_file():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError) as exc:
        raise S5bOrchestratorError(
            f"批根金额守卫配置不可读:{path}({exc};发车前 fail-closed,"
            "不猜默认价格)", {
                "kind": "s5b_budget_guard_invalid",
                "reason": "unreadable_json",
                "path": str(path)}) from exc
    try:
        return normalize_cost_guard_config(raw)
    except ValueError as exc:
        detail = exc.args[0] if exc.args else {}
        raise S5bOrchestratorError(
            f"批根金额守卫配置坏形状:{path}(五数值字段须为正:CNY 帽"
            "/入价/出价/输入保守界/输出上限;fail-closed,不猜默认)",
            {"kind": "s5b_budget_guard_invalid",
             "reason": "invalid_shape",
             "path": str(path),
             "detail": detail}) from exc


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
      一致性沿预注册纪律);**v3:读-比对-写在 orchestration.lock
      短临界区内串行**(分片同时首跑时后到者必读到先到者副本,无静默
      双写窗口);``qids``/``question_limit`` 不进冻结副本(分片白
      名单属于执行域,不属于冻结参数域——**所有分片仍须同参发车**,
      不同参后到者按冲突拒);
    - **R4(v3):白名单域 flock**(``batch_root/coord/`` 逐 qid 一锁;
      同 qid 双协调者结构化拒,不相交 qid 白名单分片并发放行 ——
      与 run 级 driver.lock 并存,不冲突);死亡未封存恢复只有一份
      最终 case(每 qid 的终态 case 由 worker 原子落盘;汇总在各自
      协调者锁内执行,全批判分由调用方在全部分片终态后单次 score);
    - **R5:worker_total_timeout** 0=禁用(首批默认,沿现政策;非正值
      不得隐式 kill 而少跑题);正值 = monotonic 总时限 + terminate/
      grace/kill + 死亡占位对账;**负值配置拒**;stderr 独立有界日志/
      主动 drain(防 PIPE 阻塞);
    - 返回批报告 dict(同时落盘 batch_report.json + progress.json;
      分片模式下两文件为**最后写盘分片的视角**,全批视角用
      ``summarize_batch``/score,progress 轮询同理)。
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
        # v3:白名单去重(保序)—— qid 锁按集合域互斥,重复项即同 qid
        # 自冲突;执行/报告按唯一 qid 集合(旧行为重复项会产生重复
        # 报告行,顺带消除)
        order = list(dict.fromkeys(wanted))
    else:
        order = registration
    if question_limit is not None:
        order = order[:int(question_limit)]
    if not order:
        raise S5bOrchestratorError(
            "空执行清单(零题;fail-closed)", {
                "kind": "s5b_empty_question_list"})
    # ---- S5B-V3-02:金额守卫机器配置(先于任何 worker 派发/传输) ----
    # real 批(将产生付费 HTTP 发送)必须已冻结 budget_guard.json:
    # 60 CNY 帽 + 当日价 + 输入保守界 + 输出上限;缺席/坏形状 ⇒
    # 结构化拒(余额守卫不能事后补);scripted 批网络 0,配置可选
    # (存在则同样冻结生效)。
    provider_kind = str(manifest.get("provider_kind") or "real")
    budget_guard = load_budget_guard(batch_root)
    if provider_kind == "real" and budget_guard is None:
        raise S5bOrchestratorError(
            f"real 批缺金额守卫机器配置 {batch_root / S5B_BUDGET_GUARD_FILE}"
            "(S5B-V3-02:60 CNY 硬帽 + 当日价 + 输入保守界 + 输出上限"
            "先于传输冻结;先用 s5b_cli budget 落盘,不猜默认价格、"
            "不自动升帽)", {
                "kind": "s5b_budget_guard_missing",
                "batch_root": str(batch_root),
                "expected_file": S5B_BUDGET_GUARD_FILE,
                "default_cap_cny": S5B_DEFAULT_BUDGET_CAP_CNY})
    # ---- 发车参数冻结(同批根续跑复用;变更拒绝) ----
    frozen = {
        "orchestrator_version": S5B_ORCHESTRATOR_VERSION,
        "workers": int(workers),
        "max_in_flight": int(max_in_flight),
        "gate_rpm": int(gate_rpm),
        "gate_tpm": int(gate_tpm),
        "gate_max_calls": int(gate_max_calls),
        "budget_guard": budget_guard,
        "profile_policy": profile_policy or S5B_DEFAULT_PROFILE_POLICY,
        "runs_root": str(runs_root),
        "frozen_at": now_iso(),
    }
    orch_path = batch_root / "orchestration.json"
    # v3:读-比对-写在短 flock 内串行(分片同时首跑:后到者必读到
    # 先到者副本再比对 ⇒ 参数不一致按冲突拒,无"双双见缺文件双写"
    # 的静默窗口);落盘原子 replace(tmp 含 pid,分片并发写不互踩)
    with _short_flock(batch_root / "orchestration.lock"):
        if orch_path.is_file():
            existing = json.loads(orch_path.read_text(encoding="utf-8"))
            comparable = {k: existing.get(k) for k in frozen
                          if k != "frozen_at"}
            if comparable != {k: frozen[k] for k in frozen
                              if k != "frozen_at"}:
                raise S5bOrchestratorError(
                    "同批根的编排参数与既有冻结副本不一致(改参须新批根;"
                    "预注册纪律:首跑不可因中途结果改写;分片须同参发车)",
                    {"kind": "s5b_orchestration_conflict",
                     "batch_root": str(batch_root)})
        else:
            _write_json(orch_path, frozen)
        _write_json(batch_root / "profile_policy.json",
                    frozen["profile_policy"])
    # ---- 批级闸门(状态文件持久;worker 客户端经 env 装载同门;
    # R2:参数首消费核对 —— 状态文件冻结参数与构造参数一致才可用;
    # S5B-V3-02:金额守卫配置随闸门冻结,worker 侧从状态文件装配) ----
    gate = FileRateGate(
        batch_root / "gate", rpm=int(gate_rpm), tpm=int(gate_tpm),
        max_calls=int(gate_max_calls),
        max_in_flight=int(max_in_flight),
        cost_guard=budget_guard)
    gate.verify_config()
    gate_dir = str(batch_root / "gate")
    # ---- R4(v3):白名单域 flock(逐 qid 一锁;同 qid 双协调者拒、
    # 不相交白名单分片放行;与 run 级 driver.lock 并存不冲突) ----
    _check_lock_fd_headroom(len(order), workers)
    locks = _WhitelistCoordinatorLocks(batch_root, order)
    locks.acquire()
    try:
        return _run_batch_loop(
            batch_root=batch_root, runs_root=runs_root, manifest=manifest,
            order=order, env_file=env_file, workers=workers,
            gate_dir=gate_dir, gate=gate, python_bin=python_bin,
            worker_timeout_s=worker_timeout_s, poll_s=poll_s,
            started_at_wall=time.time())
    finally:
        locks.release()


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
                             "lock_domain": str(batch_root / "coord"),
                             "qids_n": len(order)}
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
    out = {k: state.get(k) for k in (
        "total_requests", "total_429", "total_forbidden",
        "max_calls", "max_in_flight", "peak_in_flight", "stopped")}
    # S5B-V3-02:金额守卫账本摘要进批报告(已结算/未结算/在途预留/
    # committed/超帽与拒发计数;只读披露,不改判)
    if state.get("cost_guard") is not None:
        cost = state.get("cost") or {}
        guard = state.get("cost_guard") or {}
        out["cost_guard"] = {
            "enabled": True,
            "cap_cny": guard.get("cap_cny"),
            "config_sha256": guard.get("config_sha256"),
            "settled_cny": cost.get("settled_cny"),
            "unsettled_cny": cost.get("unsettled_cny"),
            "reserved_cny": cost.get("reserved_cny"),
            "committed_cny": _round(
                (cost.get("settled_cny") or 0.0)
                + (cost.get("unsettled_cny") or 0.0)
                + (cost.get("reserved_cny") or 0.0)),
            "send_rejections": cost.get("send_rejections"),
            "overrun": cost.get("overrun") or None,
        }
    return out


def _round(value) -> float:
    return round(float(value or 0.0), 6)


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
    """原子落盘 JSON(v3:tmp 名含 pid+线程标识 + os.replace)。

    分片协调者并发写同一信息文件(progress/batch_report/
    orchestration/profile_policy)时:tmp 互不重名、replace 原子换入
    ⇒ 磁盘上只见完整旧/新 JSON 之一,不互踩半截(单协调者语义
    不变,只是并发硬化;跨进程分片靠 pid 区分,同进程多线程
    分片靠线程标识区分);进程被杀留下的 ``*.tmp`` 是无害残片
    (下一次写盘不读它)。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(
        f"{path.name}.{os.getpid()}-{threading.get_ident()}.tmp")
    tmp.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True,
                   indent=1) + "\n", encoding="utf-8")
    os.replace(tmp, path)


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
