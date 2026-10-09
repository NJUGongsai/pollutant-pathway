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
- **批级金额硬帽(S5B-V3-02,发送前原子预留)**:批根冻结的机器配置
  ``budget_guard.json``(60 CNY 帽 + 当日价 + 输入保守界 + 输出上限)由
  协调者写入闸门状态文件 ``cost_guard`` 块;**每次可能付费的发送尝试
  (含 HTTP retry)在 acquire 的同一 flock 临界区内先原子预留**:
  ``已结算借记 settled + 未结算未知占用 unsettled + 在途预留 reserved +
  单次尝试保守上界 bound ≤ 硬帽 cap`` 才放行,否则
  ``GateCostBudgetExhausted`` 结构化拒(余额不足先于传输,不自动升帽)。
  结算语义:响应带 usage ⇒ 按冻结价结算实际金额(预留差值退回恰一次,
  幂等);**显式 429 之外的一切无 usage 结局(失败/超时/401/402/403/
  5xx/空响应/未知)不释放可能已付金额** —— 预留全额转为未结算借记;
  429 是提供者明示未处理未计费的确定性结局(沿 llm_client 既有口径
  "提供者不把 429 计费"),预留退回;孤儿/崩溃(死亡 owner 占位回收)
  只退在途槽位,**金额预留保守保留为未结算借记**;重复结算幂等,不重
  退不重扣。结算后 committed 超帽 ⇒ 记录 overrun 披露(实际已付事实,
  不回滚)。
- 状态文件与锁文件**不含密钥**;凭证只在 worker 进程内存。

状态文件是协调器/worker 间的共享事实源;损坏时 fail-closed(拒绝发起,
不静默清零计数)。金额守卫配置坏/缺(fresh 状态无 ``cost_guard`` 的旧
语义批除外)在构造/首消费/恢复核对处结构化拒,不猜默认价格。

并发正确性(fable5 §3.1[问题2]/§7-1,P1a 修复):
- 所有读-改-写(total_requests / in_flight / peak_in_flight / 滑窗 /
  冷却 / 停止标志 / 金额预留-结算)都在 ``_locked()`` 的 flock 独占
  临界区内完成 —— 伴生锁文件 ``gate.lock`` 串行化全部 worker 进程,
  进程被杀内核自动释放锁(金额预留已原子落盘,不因进程死亡丢失);
- 状态文件以**临时文件 + os.replace 原子落盘**:进程在写入中途被杀也
  只会留下旧/新两个完整 JSON 之一,不会留下半截文件触发 GateCorrupt
  (旧实现 seek/write/truncate 直接写原文件,截断前被杀即损坏)。
  闸门文件**格式不变**(schema=v43-rate-gate-1,新增 cost_guard/cost
  为可选后加块,旧状态缺省不启用金额守卫),既有批次根 resume 不受
  影响;金额守卫仅对新批(协调者写冻结配置)生效。
"""

from __future__ import annotations

import fcntl
import hashlib
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

# ---- S5B-V3-02:批级金额硬帽机器配置(单一判据源) ----
# 金额守卫机器配置 schema(批根 budget_guard.json / 闸门状态 cost_guard 块
# 同一形状;协调者 CLI 落盘,发车/恢复核对逐字段一致才可用)
COST_GUARD_SCHEMA = "s5b-budget-guard-1"
# 金额一律四舍五入到 1e-6 CNY 存储;帽比较容差 1e-9(防浮点毛刺误拒)
COST_MONEY_DECIMALS = 6
COST_EPSILON = 1e-9
COST_GUARD_NUMERIC_FIELDS = (
    "cap_cny", "input_per_mtok", "output_per_mtok",
    "input_tokens_conservative_bound", "max_output_tokens")
# usage 缺 input/output 拆分而只有 total 时,全额按较贵单价计(保守口径;
# 与"未知不释放"同一保守方向,冻结进配置披露)
COST_USAGE_SPLIT_POLICY = "unknown_split_all_at_max_price"


class GateCostBudgetExhausted(RuntimeError):
    """批级金额硬帽已达(发送前原子预留失败;余额不足先于传输)。

    语义与 GateBudgetExhausted(请求数预算)分开:本异常只由金额守卫
    抛出,detail 携带 cap/committed/bound/构成(settled+unsettled+
    reserved)机读字段;调用方不得借重试自动提高帽。"""

    def __init__(self, detail: dict | None = None):
        super().__init__("批级金额预算(硬帽)已达,停止发起新的付费请求")
        self.detail = detail or {}


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


# ------------------------------------------------------------ 金额守卫配置


def normalize_cost_guard_config(config: dict | None) -> dict:
    """金额守卫机器配置归一/校验(S5B-V3-02;orchestrator/CLI/gate/
    worker 共用同一判据,不各写一套)。

    输入:批根 ``budget_guard.json`` 的 JSON 对象(或闸门状态块)。
    输出(冻结进闸门状态与 run 身份的规范形状):
    - ``schema`` = s5b-budget-guard-1(其他值拒,fail-closed 不猜迁移);
    - ``currency`` 缺省 ``CNY``(非 CNY 拒 —— 60 CNY 帽口径冻结);
    - 五个数值字段必须为正有限数:``cap_cny``(硬帽,如 60.0)、
      ``input_per_mtok`` / ``output_per_mtok``(当日价,元/Mtok)、
      ``input_tokens_conservative_bound``(输入保守界,须 ≥ 实际输入
      tokens)、``max_output_tokens``(请求体输出上限,随请求发送);
    - 派生 ``per_attempt_bound_cny`` = (输入界×入价 + 输出上限×出价)
      /1e6(四舍六入 1e-6)—— 每次可能付费的发送尝试(含 HTTP retry)
      的原子预留金额;
    - 派生 ``config_sha256``:五字段+货币+schema 的规范化内容哈希
      (机器配置可核验;新批登记引用);
    - ``usage_split_policy`` 固定保守口径(见常量)。

    坏/缺配置 ⇒ ValueError(detail 结构化;调用方包装为各自契约异常,
    先于传输拒,不静默补默认价格)。``None`` ⇒ ValueError(金额守卫
    启用路径必须显式给配置;不启用路径由调用方决定)。
    """
    if not isinstance(config, dict):
        raise ValueError({"kind": "cost_guard_config_invalid",
                          "reason": "not_an_object",
                          "value_type": type(config).__name__})
    cfg = dict(config)
    schema = str(cfg.get("schema") or COST_GUARD_SCHEMA)
    if schema != COST_GUARD_SCHEMA:
        raise ValueError({"kind": "cost_guard_config_invalid",
                          "reason": "schema_unknown",
                          "schema": schema,
                          "expected": COST_GUARD_SCHEMA})
    currency = str(cfg.get("currency") or "CNY")
    if currency != "CNY":
        raise ValueError({"kind": "cost_guard_config_invalid",
                          "reason": "currency_not_cny",
                          "currency": currency})
    values: dict[str, float] = {}
    for field in COST_GUARD_NUMERIC_FIELDS:
        raw = cfg.get(field)
        if isinstance(raw, bool) or not isinstance(raw, (int, float)):
            raise ValueError({"kind": "cost_guard_config_invalid",
                              "reason": "field_not_positive_number",
                              "field": field, "value": repr(raw)})
        value = float(raw)
        if not (value > 0.0 and value == value and value != float("inf")):
            raise ValueError({"kind": "cost_guard_config_invalid",
                              "reason": "field_not_positive_number",
                              "field": field, "value": value})
        values[field] = value
    core = {
        "schema": schema,
        "currency": currency,
        **{k: values[k] for k in COST_GUARD_NUMERIC_FIELDS},
        "usage_split_policy": COST_USAGE_SPLIT_POLICY,
    }
    bound = round(
        (values["input_tokens_conservative_bound"]
         * values["input_per_mtok"]
         + values["max_output_tokens"] * values["output_per_mtok"])
        / 1_000_000.0, COST_MONEY_DECIMALS)
    if bound <= 0.0:
        raise ValueError({"kind": "cost_guard_config_invalid",
                          "reason": "per_attempt_bound_not_positive",
                          "per_attempt_bound_cny": bound})
    core["per_attempt_bound_cny"] = bound
    core["config_sha256"] = hashlib.sha256(
        json.dumps(core, ensure_ascii=False, sort_keys=True)
        .encode("utf-8")).hexdigest()
    for passthrough in ("frozen_at", "note", "recorded_at"):
        if cfg.get(passthrough) is not None:
            core[passthrough] = cfg[passthrough]
    return core


def _round_money(value: float) -> float:
    return round(float(value), COST_MONEY_DECIMALS)


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
        cost_guard: dict | None = None,
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
        # S5B-V3-02:批级金额硬帽配置(None = 不启用;旧 dev 语义批与
        # 金额守卫并存不冲突——旧批状态无 cost_guard 块,行为不变)
        if cost_guard is None:
            self.cost_guard = None
        else:
            try:
                self.cost_guard = normalize_cost_guard_config(cost_guard)
            except ValueError as exc:
                raise GateCorrupt({
                    "kind": "cost_guard_config_invalid",
                    "detail": exc.args[0] if exc.args else {},
                    "note": ("金额守卫配置坏/缺先于传输拒(fail-closed;"
                             "不猜默认价格/帽")}) from exc
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
                state = json.loads(text)
            except Exception as exc:
                raise GateCorrupt({"path": str(self.state_path),
                                   "error": str(exc)[:200]}) from exc
            # R2:worker 从**冻结值装配** —— 打开既有批根状态文件时,
            # rpm/tpm/max_calls/max_in_flight 采纳状态文件冻结值(协调
            # 者发车写入),不与本地构造默认/环境冲突混用;新状态才用
            # 构造参数。首消费核对见 verify_config。
            if isinstance(state, dict) and state.get("max_calls") is not None:
                try:
                    self.rpm = int(state.get("rpm", self.rpm))
                    self.tpm = int(state.get("tpm", self.tpm))
                    self.max_calls = int(state.get("max_calls",
                                                   self.max_calls))
                    self.max_in_flight = int(
                        state.get("max_in_flight", 0) or 0)
                except (TypeError, ValueError):
                    pass
            # S5B-V3-02:金额守卫同样从冻结值装配(协调者写入
            # cost_guard 块;worker 侧构造缺省 ⇒ 采纳冻结配置;状态块
            # 坏形状 ⇒ GateCorrupt,先于任何发起)。构造显式给了
            # cost_guard 而状态无块(新状态)⇒ 用构造值(首跑写盘);
            # 两侧都有 ⇒ 校验一致性(verify_config 全量核对)。
            state_cost_guard = (state.get("cost_guard")
                                if isinstance(state, dict) else None)
            if state_cost_guard is not None:
                try:
                    self.cost_guard = normalize_cost_guard_config(
                        state_cost_guard)
                except ValueError as exc:
                    raise GateCorrupt({
                        "kind": "cost_guard_config_invalid",
                        "detail": exc.args[0] if exc.args else {},
                        "note": ("冻结金额守卫配置坏形状 ⇒ fail-closed "
                                 "拒绝发起(不清零计数、不猜价格)")}) from exc
            elif self.cost_guard is not None and \
                    isinstance(state, dict) and state.get("max_calls") \
                    is not None:
                # 既有状态(非 fresh)但无金额块:构造侧给了配置 ⇒ 冲突
                # (协调者参数与既有批根冻结不一致;改参须新批根)
                raise GateCorrupt({
                    "kind": "cost_guard_config_mismatch",
                    "note": ("既有闸门状态无金额守卫块而构造参数启用了"
                             "金额守卫(改参须新批根;预注册纪律)")})

    def _fresh_state(self) -> dict:
        state = {
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
            # R2(S5b W6):每次 acquire 的占位 ID(存活 owner 集合;
            # 释放恰一次、重复幂等;父协调者只回收已确认死亡 owner 的
            # 占位 —— 无 TTL,活长请求不因超时被释放)
            "placeholders": {},            # {placeholder_id: {pid, issued_at}}
            "placeholder_seq": 0,
            "reclaimed_dead": 0,           # 已回收的死亡 owner 占位数(披露)
        }
        if self.cost_guard is not None:
            # S5B-V3-02:金额守卫冻结配置 + 金额账本(新批才有;旧批
            # 状态无这两块,行为不变)
            state["cost_guard"] = dict(self.cost_guard)
            state["cost"] = self._fresh_cost_ledger()
        return state

    def _fresh_cost_ledger(self) -> dict:
        return {
            "settled_cny": 0.0,        # 已知 usage 结算的实际借记
            "unsettled_cny": 0.0,      # 无 usage/孤儿保守保留的预留全额
            "reserved_cny": 0.0,       # 在途预留(每次可能付费发送尝试)
            "send_rejections": 0,      # 金额硬帽拒发次数(披露)
            "overrun": None,           # 结算后发现超帽的事后披露(不回滚)
            # {placeholder_id: {bound_cny, state, settled_cny, pid, at}}
            # state: reserved | settled | unsettled | released_unbilled
            "reservations": {},
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
        # in_flight/max_in_flight/placeholders 为后加字段:旧状态文件
        # 缺省补 0/空(兼容,不破坏既有闸门语义;新批从 _fresh_state
        # 带全量字段 —— R2 占位语义仅新批生效)
        state.setdefault("in_flight", 0)
        state.setdefault("max_in_flight", 0)
        state.setdefault("peak_in_flight", 0)
        state.setdefault("placeholders", {})
        state.setdefault("placeholder_seq", 0)
        state.setdefault("reclaimed_dead", 0)
        # S5B-V3-02:cost_guard 块存在而 cost 账本缺键 ⇒ 状态半截
        # (旧版本写盘/外部篡改)⇒ fail-closed;cost_guard 不存在 ⇒
        # 金额守卫未启用(旧 dev 批语义,零金额状态)
        if state.get("cost_guard") is not None:
            cost = state.setdefault("cost", {})
            for key in ("settled_cny", "unsettled_cny", "reserved_cny",
                        "send_rejections", "reservations"):
                if key not in cost:
                    raise GateCorrupt({
                        "missing_key": f"cost.{key}",
                        "note": "金额守卫状态半截;拒绝发起(fail-closed)"})
            cost.setdefault("overrun", None)
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

    def _cost_committed_cny(self, state: dict) -> float:
        cost = state.get("cost") or {}
        return _round_money(
            float(cost.get("settled_cny") or 0.0)
            + float(cost.get("unsettled_cny") or 0.0)
            + float(cost.get("reserved_cny") or 0.0))

    def acquire(self) -> dict:
        """阻塞直到允许发起新请求;返回放行时刻的闸门快照(审计用)。

        R2:每次 acquire 分配**占位 ID**(placeholder_id);调用方在
        一次 HTTP 尝试结束(成功/429/鉴权/超时/传输失败/解码失败)时以
        ``record_response(placeholder_id=...)`` 恰一次释放;未 acquire
        不 release(未知占位 no-op);重复 release 幂等(占位已移除 ⇒
        no-op,不重复扣 in_flight)。

        S5B-V3-02:金额守卫启用(状态含 cost_guard 块)时,本方法在
        同一 flock 临界区内完成**发送前原子预留**:committed
        (settled+unsettled+reserved)+ per_attempt_bound ≤ cap 才放行,
        预留金额与占位绑定落盘;余额不足 ⇒ GateCostBudgetExhausted
        (不等待 —— 金额不会因等待改善;先于传输,不自动升帽)。"""
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
                # ---- S5B-V3-02:金额硬帽原子预留(先于传输) ----
                cost_guard = state.get("cost_guard")
                cost_bound = None
                if cost_guard is not None:
                    cost_bound = _round_money(
                        cost_guard.get("per_attempt_bound_cny") or 0.0)
                    cap = _round_money(cost_guard.get("cap_cny"))
                    committed = self._cost_committed_cny(state)
                    if cost_bound <= 0.0:
                        # 冻结块缺派生字段(坏形状)⇒ fail-closed
                        raise GateCorrupt({
                            "kind": "cost_guard_config_invalid",
                            "reason": "per_attempt_bound_missing"})
                    if committed + cost_bound > cap + COST_EPSILON:
                        cost = state["cost"]
                        cost["send_rejections"] = int(
                            cost.get("send_rejections") or 0) + 1
                        self._save(state)
                        raise GateCostBudgetExhausted({
                            "kind": "cost_budget_exhausted",
                            "cap_cny": cap,
                            "committed_cny": committed,
                            "per_attempt_bound_cny": cost_bound,
                            "settled_cny": float(
                                (state.get("cost") or {}).get(
                                    "settled_cny") or 0.0),
                            "unsettled_cny": float(
                                (state.get("cost") or {}).get(
                                    "unsettled_cny") or 0.0),
                            "reserved_cny": float(
                                (state.get("cost") or {}).get(
                                    "reserved_cny") or 0.0),
                            "config_sha256": str(
                                cost_guard.get("config_sha256") or ""),
                            "note": ("批级金额硬帽(冻结机器配置,不自动"
                                     "升帽):已知借记+在途预留+缺 usage "
                                     "未结算预留+单次保守上界 ≤ 帽才发;"
                                     "余额不足先于传输拒")})
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
                    # (或父协调者回收已确认死亡 owner 的占位)
                    wait = max(wait, 0.05)
                if wait <= 0:
                    state["request_starts"].append(now)
                    state["total_requests"] += 1
                    state["in_flight"] = int(state.get("in_flight", 0)) + 1
                    state["peak_in_flight"] = max(
                        int(state.get("peak_in_flight", 0)),
                        int(state["in_flight"]))
                    # ---- R2:占位 ID 分配 ----
                    state["placeholder_seq"] = \
                        int(state.get("placeholder_seq", 0)) + 1
                    placeholder_id = "g{0}-{1}-{2}".format(
                        state["placeholder_seq"], os.getpid(),
                        int(now * 1000))
                    state.setdefault("placeholders", {})[placeholder_id] = {
                        "pid": os.getpid(), "issued_at": now}
                    # ---- S5B-V3-02:金额预留与占位原子绑定落盘 ----
                    if cost_bound is not None:
                        cost = state["cost"]
                        cost["reserved_cny"] = _round_money(
                            float(cost.get("reserved_cny") or 0.0)
                            + cost_bound)
                        cost.setdefault("reservations", {})[placeholder_id] = {
                            "bound_cny": cost_bound,
                            "state": "reserved",
                            "settled_cny": None,
                            "pid": os.getpid(), "at": now}
                    self._save(state)
                    return {"acquired_at": now,
                            "total_requests": state["total_requests"],
                            "in_flight": state["in_flight"],
                            "placeholder_id": placeholder_id}
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
                        reason: str = "",
                        placeholder_id: str | None = None) -> None:
        """响应后记账:token 计入滑窗;429 设冷却;付费/权限错误置停止。

        R2 释放语义(占位):
        - ``placeholder_id`` 给出且仍存活 ⇒ 移除占位并 -1 in_flight
          (恰一次);占位未知/已移除 ⇒ **不扣减**(未 acquire 不
          release;重复 release 幂等);
        - ``placeholder_id`` 缺省(旧调用方/旧批根)⇒ 维持旧行为直接
          -1(兼容;新批一律带占位)。
        其余记账(token/429/停止标志)与占位无关,照常执行。

        S5B-V3-02 金额结算(金额守卫启用且该占位有在途预留时):
        - 响应带可计 usage ⇒ **按冻结价结算实际金额**(预留全额撤出
          in_flight 账、实际入 settled;差值退回恰一次;重复/幂等结算
          no-op,不重退不重扣);结算后 committed 超帽 ⇒ 记 overrun
          (事后披露,不回滚已付事实,后续发送被拒);
        - 显式 429 ⇒ 预留退回(提供者明示未处理未计费;llm_client
          既有口径"提供者不把 429 计费");
        - **其余一切无 usage 结局(失败/超时/401/402/403/5xx/空响应/
          未知)⇒ 预留全额转 unsettled 不释放**(可能已付,保守保留);
        - 占位无预留记录(未 acquire/旧调用方/已结算)⇒ 金额侧 no-op。"""
        with self._locked() as f:
            state = self._load(f)
            now = time.time()
            self._purge(state, now)
            placeholders = state.setdefault("placeholders", {})
            if placeholder_id is None:
                # 旧语义(兼容):一次 HTTP 尝试结束 = 一个在途槽位释放
                state["in_flight"] = max(
                    0, int(state.get("in_flight", 0)) - 1)
            elif placeholder_id in placeholders:
                placeholders.pop(placeholder_id)
                state["in_flight"] = max(
                    0, int(state.get("in_flight", 0)) - 1)
            # 未知/已释放占位:no-op(未 acquire 不 release;幂等)
            # ---- S5B-V3-02:金额结算(幂等;见方法 docstring) ----
            if state.get("cost_guard") is not None \
                    and placeholder_id is not None:
                cost = state["cost"]
                reservations = cost.setdefault("reservations", {})
                entry = reservations.get(placeholder_id)
                if entry is not None and entry.get("state") == "reserved":
                    guard = state["cost_guard"]
                    bound = _round_money(entry.get("bound_cny"))
                    actual = self._cost_of_usage(guard, usage)
                    if actual is not None:
                        entry["state"] = "settled"
                        entry["settled_cny"] = actual
                        cost["reserved_cny"] = _round_money(
                            float(cost.get("reserved_cny") or 0.0) - bound)
                        cost["settled_cny"] = _round_money(
                            float(cost.get("settled_cny") or 0.0) + actual)
                    elif status == 429:
                        # 提供者明示未处理未计费(429):预留退回
                        entry["state"] = "released_unbilled"
                        cost["reserved_cny"] = _round_money(
                            float(cost.get("reserved_cny") or 0.0) - bound)
                    else:
                        # 失败/超时/未知 usage/付费类错误:可能已付 ⇒
                        # 预留全额保守保留为未结算借记,不释放
                        entry["state"] = "unsettled"
                        cost["reserved_cny"] = _round_money(
                            float(cost.get("reserved_cny") or 0.0) - bound)
                        cost["unsettled_cny"] = _round_money(
                            float(cost.get("unsettled_cny") or 0.0) + bound)
                    cap = _round_money(guard.get("cap_cny"))
                    committed = self._cost_committed_cny(state)
                    if committed > cap + COST_EPSILON and \
                            not cost.get("overrun"):
                        cost["overrun"] = {
                            "kind": "cost_guard_overrun",
                            "committed_cny": committed,
                            "cap_cny": cap,
                            "at": now,
                            "note": ("结算后发现已知借记+未知占用超帽(实际"
                                     "已付事实,不回滚);新发送被硬帽拒,"
                                     "不自动升帽")}
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

    @staticmethod
    def _cost_of_usage(guard: dict, usage: dict | None) -> float | None:
        """按冻结价把 provider usage 结算为实际金额(CNY;None = 不可计)。

        - input/output 拆分齐 ⇒ 按各自单价精确结算;
        - 只有 total ⇒ 保守口径:全额按较贵单价计(usage_split_policy
          冻结进配置披露,不猜拆分);
        - 无 usage/无可计 token ⇒ None(调用方按未知保守保留预留)。"""
        if not usage:
            return None
        try:
            prompt = int(usage.get("prompt_tokens") or 0)
            completion = int(usage.get("completion_tokens") or 0)
            total = int(usage.get("total_tokens") or 0)
        except (TypeError, ValueError):
            return None
        input_price = float(guard.get("input_per_mtok") or 0.0)
        output_price = float(guard.get("output_per_mtok") or 0.0)
        if prompt > 0 and completion > 0:
            tokens_cny = (prompt * input_price
                          + completion * output_price) / 1_000_000.0
        elif total > 0:
            tokens_cny = total * max(input_price, output_price) \
                / 1_000_000.0
        elif prompt > 0 or completion > 0:
            tokens_cny = (prompt * input_price
                          + completion * output_price) / 1_000_000.0
        else:
            return None
        return _round_money(tokens_cny)

    # ------------------------------------------------------------ 死亡占位回收

    def reclaim_dead_placeholders(self, *, pid_alive=None) -> dict:
        """父协调者回收**已确认死亡 owner** 的占位(R2)。

        - 判死 = ``pid_alive(pid)`` 回调(缺省 = 本机 os.kill(pid,0)
          抛 ProcessLookupError);**无 TTL** —— 活长请求不因超时被
          释放;owner 活着 ⇒ 占位保留(即使看起来"很久");
        - 回收只减 in_flight,**total_requests 不退**(发起事实保留);
          unknown 活跃状态不清零后继续付费;
        - S5B-V3-02:死亡 owner 的**金额在途预留不释放** —— 保守转
          未结算借记(可能已付:请求可能已到提供者;孤儿不退款);
        - 幂等:重复调用对已移除占位 no-op。返回回收摘要(披露)。
        """
        if pid_alive is None:
            def pid_alive(pid: int) -> bool:
                try:
                    os.kill(int(pid), 0)
                    return True
                except ProcessLookupError:
                    return False
                except PermissionError:
                    return True   # 存在但属他人:视为活
                except OSError:
                    return True  # 无法判定:保守视为活(不误回收)
        with self._locked() as f:
            state = self._load(f)
            placeholders = state.setdefault("placeholders", {})
            dead = [pid_key for pid_key, entry in placeholders.items()
                    if not pid_alive(int(entry.get("pid", 0)))]
            for pid_key in dead:
                placeholders.pop(pid_key)
                state["in_flight"] = max(
                    0, int(state.get("in_flight", 0)) - 1)
                # S5B-V3-02:金额预留保守保留(孤儿可能已付费,不退)
                if state.get("cost_guard") is not None:
                    cost = state["cost"]
                    reservations = cost.setdefault("reservations", {})
                    entry = reservations.get(pid_key)
                    if entry is not None and entry.get("state") \
                            == "reserved":
                        bound = _round_money(entry.get("bound_cny"))
                        entry["state"] = "unsettled"
                        entry["note"] = "owner_dead_reservation_kept"
                        cost["reserved_cny"] = _round_money(
                            float(cost.get("reserved_cny") or 0.0) - bound)
                        cost["unsettled_cny"] = _round_money(
                            float(cost.get("unsettled_cny") or 0.0) + bound)
            state["reclaimed_dead"] = int(
                state.get("reclaimed_dead", 0)) + len(dead)
            self._save(state)
            return {"reclaimed": len(dead),
                    "reclaimed_ids": dead,
                    "in_flight": int(state.get("in_flight", 0)),
                    "total_requests": int(state.get("total_requests", 0))}

    # ------------------------------------------------------------ 参数核对

    def verify_config(self) -> dict:
        """gate 参数首消费/恢复核对(R2):构造参数与状态文件冻结值
        一致才可用(rpm/tpm/max_calls/max_in_flight/金额守卫配置任一
        不符 ⇒ 拒,不静默混用)。返回冻结参数摘要。"""
        with self._locked() as f:
            state = self._load(f)
        frozen = {
            "rpm": int(state.get("rpm", 0)),
            "tpm": int(state.get("tpm", 0)),
            "max_calls": int(state.get("max_calls", 0)),
            "max_in_flight": int(state.get("max_in_flight", 0) or 0),
            "cost_guard": (state.get("cost_guard") or None),
        }
        current = {
            "rpm": int(self.rpm),
            "tpm": int(self.tpm),
            "max_calls": int(self.max_calls),
            "max_in_flight": int(self.max_in_flight),
            "cost_guard": (self.cost_guard or None),
        }
        if frozen != current:
            raise GateCorrupt({
                "kind": "gate_config_mismatch",
                "frozen": frozen,
                "current": current,
                "note": ("gate 参数与批根冻结副本不一致(worker 从"
                         "冻结值装配并拒 env 冲突;不静默混用)")})
        return frozen

    # ------------------------------------------------------------ 金额摘要

    def cost_guard_summary(self) -> dict | None:
        """冻结金额守卫配置的校验快照(未启用 ⇒ None;坏形状 ⇒
        GateCorrupt —— 发送侧先于传输拒,身份装配同源消费)。"""
        with self._locked() as f:
            state = self._load(f)
        guard = state.get("cost_guard")
        if guard is None:
            return None
        try:
            return normalize_cost_guard_config(guard)
        except ValueError as exc:
            raise GateCorrupt({
                "kind": "cost_guard_config_invalid",
                "detail": exc.args[0] if exc.args else {},
                "note": "金额守卫配置坏形状;拒绝发起(fail-closed)"}) \
                from exc

    def cost_snapshot(self) -> dict:
        """金额账本只读快照(协调器/报告披露用:committed 构成 +
        超帽/拒发计数;不清理窗口、不结算)。"""
        with self._locked() as f:
            state = self._load(f)
        if state.get("cost_guard") is None:
            return {"enabled": False}
        cost = state.get("cost") or {}
        return {
            "enabled": True,
            "cap_cny": _round_money(
                (state.get("cost_guard") or {}).get("cap_cny")),
            "committed_cny": self._cost_committed_cny(state),
            "settled_cny": _round_money(cost.get("settled_cny") or 0.0),
            "unsettled_cny": _round_money(
                cost.get("unsettled_cny") or 0.0),
            "reserved_cny": _round_money(cost.get("reserved_cny") or 0.0),
            "per_attempt_bound_cny": _round_money(
                (state.get("cost_guard") or {}).get(
                    "per_attempt_bound_cny")),
            "send_rejections": int(cost.get("send_rejections") or 0),
            "overrun": cost.get("overrun") or None,
            "n_reservations": len(cost.get("reservations") or {}),
        }

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
