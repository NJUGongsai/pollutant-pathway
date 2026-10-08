"""跨进程 API 请求闸门 — dev 批跑 20 个 worker 共享的发起速率与预算协调。

实现(TASK_V43_EXPORT_DEV §3):批跑的 API 额度是主账号/模型共享的,
单个 worker 无法感知其他 worker 的发起速率;协调器把闸门目录路径通过
``V43_LLM_RATE_GATE`` 注入每个 worker,所有真实 HTTP 请求(只发生在
``adapters.llm_client.OpenAICompatibleClient``)经此闸门:

- **RPM 滑窗**:发起前以 flock 独占更新闸门状态文件,60 秒滑动窗口内
  已发起请求数达到上限时阻塞等待;阻塞有总上限,超时结构化失败。
- **TPM 事后记账**:请求 token 数只有响应可知;响应后记录
  (ts, total_tokens),后续发起前检查窗口内累计 token,超限则等待
  (事后闸门,轻微超滑窗由提供者 429 兜底,如实记录)。
- **429 冷却**:记录 status / Retry-After / 请求 ID,设置全局冷却窗口
  (所有 worker 都遵守);冷却值封顶,不做无界退避。
- **付费停止**:401/403 或配额类错误置全局 ``stopped`` 标志,所有
  worker 停止发起新付费请求,已完成事实保留。
- **批次调用预算**:全局已发起请求数达到上限后拒绝新请求(持久原子
  计数在同一状态文件内,flock 串行化)。
- 状态文件与锁文件**不含密钥**;凭证只在 worker 进程内存。

状态文件是协调器/worker 间的共享事实源;损坏时 fail-closed(拒绝发起,
不静默清零计数)。

并发正确性(fable5 §3.1[问题2]/§7-1,P1a 修复):
- 所有读-改-写(total_requests / in_flight / peak_in_flight / 滑窗 /
  冷却 / 停止标志)都在 ``_locked()`` 的 flock 独占临界区内完成 —— 伴生
  锁文件 ``gate.lock`` 串行化全部 worker 进程,进程被杀内核自动释放锁;
- 状态文件以**临时文件 + os.replace 原子落盘**:进程在写入中途被杀也
  只会留下旧/新两个完整 JSON 之一,不会留下半截文件触发 GateCorrupt
  (旧实现 seek/write/truncate 直接写原文件,截断前被杀即损坏)。
  闸门文件**格式不变**(schema=v43-rate-gate-1),既有批次根 resume 不受
  影响。
"""

from __future__ import annotations

import fcntl
import json
import os
import random
import time
from contextlib import contextmanager
from pathlib import Path

GATE_STATE_FILE = "gate.json"
GATE_LOCK_FILE = "gate.lock"

DEFAULT_RPM = 180                 # 提供者快照 200 RPM,保守余量
DEFAULT_TPM = 2_700_000           # 提供者快照 3,000,000 TPM,保守余量
DEFAULT_WINDOW_S = 60.0
DEFAULT_MAX_CALLS = 600           # 整批最大 API 调用数(批次身份冻结)
DEFAULT_COOLDOWN_CAP_S = 60.0     # 单次 429 冷却封顶(有上限退避)
DEFAULT_ACQUIRE_TIMEOUT_S = 600.0  # 获取槽位总等待上限


class GateStopped(RuntimeError):
    """闸门已置全局停止(付费/权限错误);不得再发起新请求。"""

    def __init__(self, reason: str, detail: dict | None = None):
        super().__init__(f"API 闸门全局停止:{reason}")
        self.detail = detail or {}


class GateBudgetExhausted(RuntimeError):
    """批次 API 调用预算已用尽。"""

    def __init__(self, detail: dict | None = None):
        super().__init__("批次 API 调用预算已用尽,停止发起新请求")
        self.detail = detail or {}


class GateCorrupt(RuntimeError):
    """闸门状态文件损坏(fail-closed,不清零计数)。"""

    def __init__(self, detail: dict | None = None):
        super().__init__("闸门状态文件损坏;拒绝发起请求(fail-closed)")
        self.detail = detail or {}


class FileRateGate:
    """基于 flock + 单一 JSON 状态文件的跨进程闸门。"""

    def __init__(
        self,
        dir_path: str | Path,
        *,
        rpm: int = DEFAULT_RPM,
        tpm: int = DEFAULT_TPM,
        max_calls: int = DEFAULT_MAX_CALLS,
        window_s: float = DEFAULT_WINDOW_S,
        cooldown_cap_s: float = DEFAULT_COOLDOWN_CAP_S,
        acquire_timeout_s: float = DEFAULT_ACQUIRE_TIMEOUT_S,
        max_in_flight: int = 0,
    ) -> None:
        self.dir = Path(dir_path)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.state_path = self.dir / GATE_STATE_FILE
        self.lock_path = self.dir / GATE_LOCK_FILE
        self.rpm = int(rpm)
        self.tpm = int(tpm)
        self.max_calls = int(max_calls)
        self.window_s = float(window_s)
        self.cooldown_cap_s = float(cooldown_cap_s)
        self.acquire_timeout_s = float(acquire_timeout_s)
        # 同时在途请求硬上限(0 = 不限制,dev 语义;EC298 外考 = 40)
        self.max_in_flight = int(max_in_flight)
        self._init_state()

    # ------------------------------------------------------------ 状态文件

    def _init_state(self) -> None:
        self.state_path.touch(exist_ok=True)
        with self._locked() as f:
            text = f.read()
            if not text.strip():
                self._save(self._fresh_state())
                return
            try:
                json.loads(text)
            except Exception as exc:
                raise GateCorrupt({"path": str(self.state_path),
                                   "error": str(exc)[:200]}) from exc

    def _fresh_state(self) -> dict:
        return {
            "schema": "v43-rate-gate-1",
            "rpm": self.rpm,
            "tpm": self.tpm,
            "max_calls": self.max_calls,
            "max_in_flight": self.max_in_flight,   # 0 = 不限制
            "request_starts": [],          # [epoch_s ...] 滑窗内发起时刻
            "token_events": [],            # [[epoch_s, total_tokens] ...]
            "total_requests": 0,
            "total_429": 0,
            "total_forbidden": 0,
            "in_flight": 0,                # 当前在途请求计数(发起 +1,响应 -1)
            "peak_in_flight": 0,           # 历史峰值(持久证据)
            "cooldown_until": 0.0,
            "stopped": None,               # {"reason":..., "status":..., "at":...}
        }

    @contextmanager
    def _locked(self):
        lock = open(self.lock_path, "a+")
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            # r+ 读写:状态文件由构造函数 touch 确保存在;不用 "a+"
            # (O_APPEND 会让 seek(0)+write 追加到文件尾,破坏 JSON)
            f = open(self.state_path, "r+")
            f.seek(0)
            try:
                yield f
            finally:
                f.close()
        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
            lock.close()

    def _load(self, f) -> dict:
        try:
            state = json.loads(f.read() or "{}")
        except Exception as exc:
            raise GateCorrupt({"error": str(exc)[:200]}) from exc
        for key in ("request_starts", "token_events", "total_requests",
                    "cooldown_until", "stopped"):
            if key not in state:
                raise GateCorrupt({"missing_key": key})
        # in_flight/max_in_flight 为后加字段:旧状态文件缺省补 0(兼容),
        # 不破坏既有闸门语义
        state.setdefault("in_flight", 0)
        state.setdefault("max_in_flight", 0)
        state.setdefault("peak_in_flight", 0)
        return state

    def _save(self, state: dict) -> None:
        """原子落盘(必须在 ``_locked()`` 临界区内调用)。

        临时文件写全量后 ``os.replace`` 原名换入:进程在写入中途被杀,
        磁盘上只可能是完整的旧状态或完整的新状态,不会留下半截 JSON
        (半截文件会被 ``_load`` 判 GateCorrupt,fail-closed 拒绝整批
        发起)。replace 不影响 flock(锁在伴生 gate.lock 上);文件格式
        与旧实现完全一致,既有批次根 resume 不受影响。
        """
        tmp = self.dir / (GATE_STATE_FILE + ".tmp")
        with open(tmp, "w", encoding="utf-8") as out:
            out.write(json.dumps(state, ensure_ascii=False, indent=1))
        os.replace(tmp, self.state_path)

    @staticmethod
    def _purge(state: dict, now: float) -> None:
        horizon = now - DEFAULT_WINDOW_S
        state["request_starts"] = [
            t for t in state["request_starts"] if t > horizon]
        state["token_events"] = [
            [t, n] for t, n in state["token_events"] if t > horizon]

    # ------------------------------------------------------------ 发起闸门

    def acquire(self) -> dict:
        """阻塞直到允许发起新请求;返回放行时刻的闸门快照(审计用)。"""
        deadline = time.monotonic() + self.acquire_timeout_s
        while True:
            with self._locked() as f:
                state = self._load(f)
                self._purge(state, time.time())
                now = time.time()
                if state["stopped"]:
                    raise GateStopped(
                        state["stopped"].get("reason", "unknown"),
                        state["stopped"])
                if state["total_requests"] >= int(state["max_calls"]):
                    raise GateBudgetExhausted({
                        "total_requests": state["total_requests"],
                        "max_calls": state["max_calls"]})
                cooldown = float(state["cooldown_until"])
                window = state["request_starts"]
                tokens = sum(n for _, n in state["token_events"])
                max_if = int(state.get("max_in_flight", 0) or 0)
                wait = 0.0
                if cooldown > now:
                    wait = max(wait, cooldown - now)
                if len(window) >= int(state["rpm"]):
                    wait = max(wait, (window[0] + self.window_s) - now)
                if tokens >= int(state["tpm"]) and state["token_events"]:
                    wait = max(wait, (state["token_events"][0][0]
                                      + self.window_s) - now)
                if max_if > 0 and int(state.get("in_flight", 0)) >= max_if:
                    # 同时在途上限:必须等一个在途请求 record_response 释放
                    wait = max(wait, 0.05)
                if wait <= 0:
                    state["request_starts"].append(now)
                    state["total_requests"] += 1
                    state["in_flight"] = int(state.get("in_flight", 0)) + 1
                    state["peak_in_flight"] = max(
                        int(state.get("peak_in_flight", 0)),
                        int(state["in_flight"]))
                    self._save(state)
                    return {"acquired_at": now,
                            "total_requests": state["total_requests"],
                            "in_flight": state["in_flight"]}
            # 等待加抖动(0-10%),避免整组 worker 同步踩点
            if time.monotonic() > deadline:
                raise TimeoutError(
                    f"闸门获取槽位超时({self.acquire_timeout_s}s)")
            time.sleep(min(wait + random.uniform(0, 0.1 * max(wait, 0.5)),
                           5.0))

    # ------------------------------------------------------------ 响应记账

    def record_response(self, *, status: int | None = None,
                        usage: dict | None = None,
                        retry_after_s: float | None = None,
                        request_id: str | None = None,
                        forbidden: bool = False,
                        reason: str = "") -> None:
        """响应后记账:token 计入滑窗;429 设冷却;付费/权限错误置停止。"""
        with self._locked() as f:
            state = self._load(f)
            now = time.time()
            self._purge(state, now)
            # 一次 HTTP 尝试结束 = 一个在途槽位释放(与 acquire 的 +1 配对;
            # 429 重试的每次尝试各自 acquire/record,计数保持平衡)
            state["in_flight"] = max(0, int(state.get("in_flight", 0)) - 1)
            if usage:
                total = int(usage.get("total_tokens")
                            or (int(usage.get("prompt_tokens") or 0)
                                + int(usage.get("completion_tokens") or 0)))
                if total > 0:
                    state["token_events"].append([now, total])
            if status == 429:
                state["total_429"] += 1
                wait = retry_after_s if retry_after_s else 2.0
                state["cooldown_until"] = max(
                    state["cooldown_until"],
                    now + min(float(wait), self.cooldown_cap_s))
            if forbidden:
                state["total_forbidden"] += 1
                state["stopped"] = {
                    "reason": reason or "forbidden_or_quota",
                    "status": status,
                    "request_id": request_id,
                    "at": now,
                }
            self._save(state)

    # ------------------------------------------------------------ 只读快照

    def snapshot(self) -> dict:
        """协调器/报告用的当前计数快照(只读,不清理窗口)。"""
        try:
            with self._locked() as f:
                state = self._load(f)
        except GateCorrupt:
            raise
        state["request_starts_n"] = len(state["request_starts"])
        state["tokens_in_window"] = sum(
            n for _, n in state["token_events"])
        return state

    def is_stopped(self) -> bool:
        return self.snapshot()["stopped"] is not None
