"""LLM 客户端适配器 — 唯一允许发出外部模型请求的模块(REPO_DESIGN §3)。

三种提供者:

- ``off``:不配置模型。确定性流程照常,遇待预测明确停 awaiting_prediction
  (第一阶段语义,不谎称预测完成)。
- ``fake``:FakeLLMClient,剧本化响应 + 跨进程调用计数。测试与无凭证演示
  用;其输出与真实响应走**同一**确定性解析器,不得冒充在线模型验证。
- ``openai_compatible``:真实提供者(OpenAI 兼容 /chat/completions,
  urllib,零第三方依赖)。配置只从环境变量读取:
  ``V43_LLM_BASE_URL``、``V43_LLM_API_KEY``、``V43_LLM_MODEL``(可选
  ``V43_LLM_TIMEOUT_S``、``V43_LLM_REQUEST_PARAMS``、
  ``V43_LLM_MAX_HTTP_RETRIES``、``V43_LLM_RATE_GATE``);密钥绝不写入
  任何文件、日志或报告。提供者支持时随请求携带 ``Idempotency-Key``。

请求参数纪律(TASK_V43_EXPORT_DEV §3):请求体 = model + messages +
显式冻结的 ``request_params``;**缺省不发 temperature**(GLM-5.3-Flash
等仅思考模型按官方默认 temperature=1.0 运行,不发关闭思考的参数;
``reasoning_effort`` 等由批次身份显式冻结)。``request_params`` 进入
run_identity 的 prediction 块(模型身份的一部分,resume 逐字段核对)。

temperature 单通道纪律(S1 E2,HIT60):温度**只**经
``prediction_policy_overrides.temperature`` 表达(None=不发送,与历史
行为逐字节一致;数值=显式携带,取值进 run/batch identity)。env 的
``V43_LLM_REQUEST_PARAMS`` 与显式 ``request_params`` 一如既往禁止
temperature/enable_thinking/thinking;不支持温度参数的模型(如
kimi-k3,API 400 ``Parameter 'temperature' is not supported``,见
docs/CHENYU_ACCESS.md 坑清单)在装配期 fail-closed 报"该模型不支持
温度臂",不静默忽略、不带病发请求。

HTTP 语义:429 记录 status / Retry-After / 请求 ID 后做**有上限**的指数
退避 + 抖动重试(提供者不把 429 计费,重试不烧钱);401/403 与配额类
错误置全局闸门停止标志并返回结构化失败,停止一切新付费请求;其余 HTTP
错误一次的结构化传输失败(节点层重试,attempt 逐次落盘,悬空计入额度)。

预测纪律(任务书 §2):解析失败、超时、空响应是显式结果,由
services/prediction.parse_model_response 判定;本模块只负责传输与调用状态,
不做内容解释。
"""

from __future__ import annotations

import hashlib
import json
import os
import random
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

PROVIDER_OFF = "off"
PROVIDER_FAKE = "fake"
PROVIDER_REAL = "openai_compatible"

LLM_BASE_URL_ENV = "V43_LLM_BASE_URL"
LLM_API_KEY_ENV = "V43_LLM_API_KEY"
LLM_MODEL_ENV = "V43_LLM_MODEL"
LLM_TIMEOUT_ENV = "V43_LLM_TIMEOUT_S"
LLM_REQUEST_PARAMS_ENV = "V43_LLM_REQUEST_PARAMS"
LLM_MAX_HTTP_RETRIES_ENV = "V43_LLM_MAX_HTTP_RETRIES"
LLM_RATE_GATE_ENV = "V43_LLM_RATE_GATE"

DEFAULT_TIMEOUT_S = 60.0
DEFAULT_MAX_HTTP_RETRIES = 4     # 429 重试上限(有界;总计 ≤5 次 HTTP 尝试)
BACKOFF_BASE_S = 2.0             # 指数退避基值:2/4/8/16s + 抖动
BACKOFF_CAP_S = 60.0             # 单次等待封顶(Retry-After 一并封顶)

# 温度/思考类参数只许走 policy 通道(prediction_policy_overrides.temperature),
# env 与显式 request_params 一律拒绝(见 _request_params_from_env 与
# resolve_model_setup;单一表达通道 = 差异可预登记、身份可冻结)
FORBIDDEN_REQUEST_PARAM_KEYS = frozenset(
    {"temperature", "enable_thinking", "thinking"})

# 已知不接受 temperature 参数的模型(CHENYU_ACCESS 坑清单:远端 DashScope
# 的 kimi-k3 对 temperature 直接 API 400)。匹配 = 模型 ID 小写包含任一
# 子串;policy 设了 temperature 且模型命中 → 装配期 fail-closed(报
# "该模型不支持温度臂"),绝不静默忽略后让 20 路 worker 逐题吃 400。
MODELS_WITHOUT_TEMPERATURE_SUPPORT = ("kimi-k3",)


def model_supports_temperature(model_id: str) -> bool:
    """模型是否接受 temperature 参数(只做已知不支持名单的保守匹配)。"""
    m = (model_id or "").lower()
    return not any(pat in m for pat in MODELS_WITHOUT_TEMPERATURE_SUPPORT)


@dataclass
class LLMResponse:
    """一次(尝试)调用的传输结果;解析是下游的确定性步骤。

    ``http_attempts`` 逐条记录到达提供者的 HTTP 尝试(含 429 退避重试),
    供用量/费用账如实核算;空 = 调用未到达 HTTP 层(本地闸门拒绝等)。
    """

    ok: bool                     # 传输层是否拿到非空文本
    raw_text: str = ""
    error_kind: str = ""         # transport_error | timeout | empty_response |
                                 # rate_limited_exhausted | forbidden_permanent |
                                 # forbidden_stopped_by_gate |
                                 # batch_api_budget_exhausted
    error_message: str = ""
    elapsed_s: float = 0.0
    usage: dict = field(default_factory=dict)
    status: int | None = None
    http_attempts: list = field(default_factory=list)
    error_detail: dict = field(default_factory=dict)
    # epoch 墙钟时间戳(time.time();任务书 EC298 §3:以请求发出/响应结束的
    # 时间戳计算在途重叠数)。sent = 本尝试 HTTP 请求发出时刻,
    # done = 提供者响应结束时刻;闸门拒绝/未发到 HTTP 层时为 None。
    # 注意:单调时钟(time.monotonic())仅用于 elapsed_s 计时,不用于排序。
    sent_at_epoch: float | None = None
    done_at_epoch: float | None = None
    request_id: str | None = None

    def to_dict(self) -> dict:
        return dict(self.__dict__)


def normalize_usage(usage: dict) -> dict:
    """provider usage → 归一口径(缺席字段显式 None,不估算冒充实测)。"""
    if not usage:
        return {}
    u = dict(usage)
    details_in = u.get("prompt_tokens_details") or {}
    details_out = u.get("completion_tokens_details") or {}
    out = {
        "input_tokens": u.get("prompt_tokens"),
        "output_tokens": u.get("completion_tokens"),
        "cached_input_tokens": details_in.get("cached_tokens"),
        "reasoning_output_tokens": details_out.get("reasoning_tokens"),
        "total_tokens": u.get("total_tokens"),
    }
    return {k: v for k, v in out.items() if v is not None} | {"raw": u}


class ModelNotConfigured(RuntimeError):
    """请求模型但未配置/凭证缺失(fail-closed;detail 结构化,无密钥)。"""

    def __init__(self, message: str, detail: dict | None = None):
        super().__init__(message)
        self.detail = detail or {}


def prompt_versions(prompts_root: str | Path) -> dict[str, str]:
    """协议提示词的 SHA256 版本(内容变更即升版本;身份核对用)。

    S1 E1:新增常驻文件 ranker_v2.md(协议臂提示词),SHA 以
    "rank_candidates_v2" 键进本表 → 进 run/batch identity;装载哪个文件
    由 prediction_policy.rank_candidate_presentation 决定
    (workflow.nodes._prompt_for),文件常驻树内、两版 SHA 恒在身份里。
    """
    root = Path(prompts_root)
    out = {}
    for mode, fname in (
        ("rank_candidates", "ranker.md"),
        ("rank_candidates_v2", "ranker_v2.md"),
        ("analogy_edit", "analogy_editor.md"),
        ("novel_proposal", "novel_proposal.md"),
    ):
        path = root / fname
        if not path.is_file():
            raise ModelNotConfigured(
                f"提示词文件缺失:{path}", {"prompt": fname}
            )
        out[mode] = hashlib.sha256(path.read_bytes()).hexdigest()
    return out


def real_provider_env() -> dict:
    """探测真实提供者环境变量(**只报存在性,绝不返回密钥值**)。"""
    return {
        "base_url_set": bool(os.environ.get(LLM_BASE_URL_ENV)),
        "api_key_set": bool(os.environ.get(LLM_API_KEY_ENV)),
        "model_set": bool(os.environ.get(LLM_MODEL_ENV)),
        "timeout_s": float(os.environ.get(LLM_TIMEOUT_ENV) or DEFAULT_TIMEOUT_S),
        "request_params_set": bool(os.environ.get(LLM_REQUEST_PARAMS_ENV)),
        "rate_gate_set": bool(os.environ.get(LLM_RATE_GATE_ENV)),
    }


def _request_params_from_env() -> dict:
    raw = os.environ.get(LLM_REQUEST_PARAMS_ENV, "").strip()
    if not raw:
        return {}
    params = json.loads(raw)  # 格式错误 → 结构化失败,不静默丢弃
    if not isinstance(params, dict):
        raise ModelNotConfigured(
            f"{LLM_REQUEST_PARAMS_ENV} 必须是 JSON 对象", {"type": type(params).__name__})
    bad = FORBIDDEN_REQUEST_PARAM_KEYS & set(params)
    if bad:
        raise ModelNotConfigured(
            f"request_params 禁止包含 {sorted(bad)}:"
            "(仅思考模型不得发送关闭思考/温度参数;温度用官方默认,"
            "实验臂温度只走 prediction_policy_overrides.temperature 通道)",
            {"keys": sorted(bad)})
    return params


class OpenAICompatibleClient:
    """OpenAI 兼容 /chat/completions 客户端(urllib;密钥只在内存)。

    - ``request_params``:随请求体发送的显式参数(思考模型的
      reasoning_effort 等);**不含 temperature/enable_thinking**。
    - ``gate``:跨进程速率闸门(FileRateGate;批跑共享),每次 HTTP
      尝试前 acquire、响应后记账;闸门拒绝映射为结构化失败。
    - 429:有界指数退避 + 抖动,尊重 Retry-After(封顶);其余 HTTP
      错误一次结构化失败(节点层 attempt 重试并留痕)。
    """

    provider = PROVIDER_REAL

    def __init__(self, base_url: str, api_key: str, model: str,
                 timeout_s: float | None = None,
                 request_params: dict | None = None,
                 gate=None,
                 max_http_retries: int | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout_s = float(
            timeout_s or os.environ.get(LLM_TIMEOUT_ENV) or DEFAULT_TIMEOUT_S
        )
        env_params = _request_params_from_env()
        merged = dict(env_params)
        merged.update(request_params or {})
        self.request_params = merged
        self.max_http_retries = int(
            max_http_retries
            if max_http_retries is not None
            else os.environ.get(LLM_MAX_HTTP_RETRIES_ENV, DEFAULT_MAX_HTTP_RETRIES)
        )
        self.gate = gate
        if self.gate is None and os.environ.get(LLM_RATE_GATE_ENV):
            from .rate_gate import FileRateGate

            self.gate = FileRateGate(os.environ[LLM_RATE_GATE_ENV])

    @classmethod
    def from_env(cls) -> "OpenAICompatibleClient":
        env = real_provider_env()
        missing = [k for k, v in (
            (LLM_BASE_URL_ENV, env["base_url_set"]),
            (LLM_API_KEY_ENV, env["api_key_set"]),
            (LLM_MODEL_ENV, env["model_set"]),
        ) if not v]
        if missing:
            raise ModelNotConfigured(
                "真实提供者环境变量缺失(只从环境读取,不落盘):"
                + ",".join(missing),
                {"missing_env": missing},
            )
        return cls(
            base_url=os.environ[LLM_BASE_URL_ENV],
            api_key=os.environ[LLM_API_KEY_ENV],
            model=os.environ[LLM_MODEL_ENV],
        )

    # ------------------------------------------------------------ 请求体

    def _request_body(self, system_prompt: str, user_payload: str,
                      params: dict) -> bytes:
        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_payload},
            ],
        }
        body.update(params)  # 显式冻结参数;temperature 仅经 extra_params
        # (policy 通道,S1 E2)进入 —— request_params 本身永不含温度键
        return json.dumps(body, ensure_ascii=False).encode("utf-8")

    @staticmethod
    def _resp_headers(resp) -> dict:
        try:
            return dict(resp.headers or {})
        except Exception:
            return {}

    @staticmethod
    def _retry_after_s(headers: dict) -> float | None:
        raw = headers.get("Retry-After") or headers.get("retry-after")
        if raw is None:
            return None
        try:
            return float(raw)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _request_id(headers: dict) -> str | None:
        for key in ("x-dashscope-request-id", "X-Dashscope-Request-Id",
                    "Request-Id", "request-id", "x-request-id"):
            if headers.get(key):
                return headers[key]
        return None

    def _gate_block(self, exc: Exception) -> LLMResponse:
        """闸门拒绝(全局停止/批次预算耗尽)→ 结构化失败(不是化学失败)。"""
        from .rate_gate import GateBudgetExhausted, GateStopped

        if isinstance(exc, GateStopped):
            return LLMResponse(
                ok=False, error_kind="forbidden_stopped_by_gate",
                error_message="gate_stopped_no_new_paid_requests",
                error_detail=dict(getattr(exc, "detail", {}) or {}))
        if isinstance(exc, GateBudgetExhausted):
            return LLMResponse(
                ok=False, error_kind="batch_api_budget_exhausted",
                error_message="gate_max_calls_reached",
                error_detail=dict(getattr(exc, "detail", {}) or {}))
        raise exc

    # ------------------------------------------------------------ 主入口

    def complete(self, *, mode: str, system_prompt: str, user_payload: str,
                 idempotency_key: str | None = None,
                 extra_params: dict | None = None) -> LLMResponse:
        params = dict(self.request_params)
        if extra_params:
            params.update(extra_params)
        body = self._request_body(system_prompt, user_payload, params)
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        if idempotency_key:
            # 提供者是否兑现幂等键不可假设;调用审计沿用 issued/response/orphan
            headers["Idempotency-Key"] = idempotency_key
        t0 = time.monotonic()
        attempts: list[dict] = []
        max_attempts = max(0, self.max_http_retries) + 1

        for attempt_no in range(1, max_attempts + 1):
            if self.gate is not None:
                try:
                    self.gate.acquire()
                except RuntimeError as exc:
                    return self._gate_block(exc)
            try:
                req = urllib.request.Request(
                    f"{self.base_url}/chat/completions", data=body,
                    headers=headers, method="POST",
                )
                sent_at = time.time()
                with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                    status = int(resp.status)
                    headers_lo = self._resp_headers(resp)
                    payload = json.loads(resp.read().decode("utf-8"))
                done_at = time.time()
            except urllib.error.HTTPError as exc:
                status = int(exc.code)
                h = self._resp_headers(exc)
                req_id = self._request_id(h)
                retry_after = self._retry_after_s(h)
                attempts.append({
                    "attempt": attempt_no, "status": status,
                    "retry_after_s": retry_after, "request_id": req_id,
                    "waited_s": 0.0,
                })
                if status == 429:
                    # 限流:不是化学失败,也不是预算失败;有界退避 + 抖动
                    if self.gate is not None:
                        self.gate.record_response(
                            status=429, retry_after_s=retry_after,
                            request_id=req_id)
                    if attempt_no < max_attempts:
                        wait = retry_after if retry_after else (
                            BACKOFF_BASE_S * (2 ** (attempt_no - 1)))
                        wait = min(wait, BACKOFF_CAP_S)
                        wait += random.uniform(0, 0.2 * wait)
                        attempts[-1]["waited_s"] = round(wait, 3)
                        time.sleep(wait)
                        continue
                    return LLMResponse(
                        ok=False, error_kind="rate_limited_exhausted",
                        error_message=f"429 after {attempt_no} attempts",
                        elapsed_s=time.monotonic() - t0,
                        status=status, http_attempts=attempts)
                if status in (401, 403) or status == 402:
                    # 凭证/权限/余额类:停止一切新付费请求(全局闸门停止)
                    if self.gate is not None:
                        self.gate.record_response(
                            forbidden=True, status=status, request_id=req_id,
                            reason=f"http_{status}")
                    return LLMResponse(
                        ok=False, error_kind="forbidden_permanent",
                        error_message=f"http_{status}_no_new_paid_requests",
                        elapsed_s=time.monotonic() - t0,
                        status=status, http_attempts=attempts)
                # 其余 HTTP 错误(400/5xx 等):一次结构化传输失败,
                # 不在客户端层重试(节点层 attempt 重试会逐次落盘)
                return LLMResponse(
                    ok=False, error_kind="transport_error",
                    error_message=f"HTTPError:{status}",
                    elapsed_s=time.monotonic() - t0,
                    status=status, http_attempts=attempts)
            except TimeoutError:
                if self.gate is not None:
                    self.gate.record_response()
                return LLMResponse(
                    ok=False, error_kind="timeout",
                    elapsed_s=time.monotonic() - t0,
                    http_attempts=attempts)
            except urllib.error.URLError as exc:
                if self.gate is not None:
                    self.gate.record_response()
                reason = getattr(exc, "reason", exc)
                is_timeout = isinstance(reason, TimeoutError)
                return LLMResponse(
                    ok=False,
                    error_kind="timeout" if is_timeout else "transport_error",
                    error_message="" if is_timeout
                    else f"{type(reason).__name__}",
                    elapsed_s=time.monotonic() - t0,
                    http_attempts=attempts)
            except Exception as exc:  # 网络/HTTP 错误:显式传输失败
                if self.gate is not None:
                    self.gate.record_response()
                return LLMResponse(
                    ok=False, error_kind="transport_error",
                    error_message=f"{type(exc).__name__}",
                    elapsed_s=time.monotonic() - t0,
                    http_attempts=attempts)
            break  # 收到 HTTP 200

        elapsed = time.monotonic() - t0
        if self.gate is not None:
            self.gate.record_response(status=status,
                                      usage=payload.get("usage") or {},
                                      request_id=self._request_id(headers_lo))
        try:
            message = payload["choices"][0]["message"]
            text = message.get("content") or ""
        except Exception:
            return LLMResponse(ok=False, error_kind="empty_response",
                               elapsed_s=elapsed, status=status,
                               usage=payload.get("usage") or {},
                               http_attempts=attempts)
        # 仅思考模型的思考内容在 reasoning_content(按输出计费);
        # 解析候选只取最终 content —— 不把思考链当答卷
        usage = payload.get("usage") or {}
        return LLMResponse(
            ok=bool(text.strip()), raw_text=text,
            error_kind="" if text.strip() else "empty_response",
            elapsed_s=elapsed, usage=dict(usage),
            status=status, http_attempts=attempts,
            sent_at_epoch=sent_at, done_at_epoch=done_at,
            request_id=self._request_id(headers_lo))


class FakeLLMClient:
    """剧本化假模型:按 mode 依次消费响应;跨进程计数文件可选。

    - ``script``: {mode: [raw_text, ...]};耗尽后重复最后一条(缺省按 mode
      给确定性兜底响应,保证可重放);
    - ``counter_path``:每次真实调用追加计数(崩溃恢复测试的持久事实源);
    - ``system_prompt`` 与真实客户端同形:解析器不区分来源。
    """

    provider = PROVIDER_FAKE

    def __init__(self, script: dict[str, list[str]] | None = None,
                 counter_path: str | Path | None = None,
                 default_by_mode: dict[str, str] | None = None,
                 model_id: str = "fake-scripted-v1") -> None:
        self.script = {k: list(v) for k, v in (script or {}).items()}
        self.counter_path = counter_path
        self.model_id = model_id
        self.default_by_mode = default_by_mode or {}
        self.calls: list[dict] = []

    def _bump_counter(self) -> None:
        if self.counter_path is None:
            return
        p = Path(self.counter_path)
        n = int(p.read_text()) if p.exists() else 0
        p.write_text(str(n + 1))

    def complete(self, *, mode: str, system_prompt: str, user_payload: str,
                 idempotency_key: str | None = None,
                 extra_params: dict | None = None) -> LLMResponse:
        self._bump_counter()
        seq = self.script.get(mode) or []
        if seq:
            raw = seq.pop(0)
        else:
            raw = self.default_by_mode.get(mode, "")
        self.calls.append({
            "mode": mode, "idempotency_key": idempotency_key,
            "model_id": self.model_id,
            # S1 E2:记录温度臂会随请求发送的附加参数(仅当 policy 设了
            # temperature;None = 与真实缺省一致,不发送任何温度键)
            "extra_params": (dict(extra_params) if extra_params else None),
        })
        return LLMResponse(
            ok=bool(raw.strip()), raw_text=raw,
            error_kind="" if raw.strip() else "empty_response",
            elapsed_s=0.0, usage={"fake": True},
        )

    @property
    def call_count(self) -> int:
        return len(self.calls)


@dataclass
class ModelSetup:
    """一次运行的模型身份与适配器(run_identity.prediction 的来源)。"""

    provider: str                                  # off | fake | openai_compatible
    model_id: str = ""
    client: object | None = None                   # Fake/OpenAICompatible
    prompts_root: str | Path = ""
    prompt_versions: dict = field(default_factory=dict)
    policy: dict = field(default_factory=dict)     # 预测策略取值
    request_params: dict = field(default_factory=dict)  # 冻结的请求参数(无温度)
    timeout_s: float = 0.0

    def identity_block(self) -> dict:
        """进入 run_identity 的 prediction 块(不含 client/密钥)。

        ``request_params`` / ``timeout_s`` 属于模型身份:参数变化 =
        不同批次(resume 逐字段核对拒绝静默继续)。"""
        return {
            "enabled": self.provider != PROVIDER_OFF,
            "provider": self.provider,
            "model_id": self.model_id,
            "prompt_versions": dict(self.prompt_versions),
            "policy_version": self.policy.get("policy_version", ""),
            "policy": {k: v for k, v in self.policy.items()
                       if k != "policy_version"},
            "request_params": dict(self.request_params),
            "timeout_s": float(self.timeout_s),
        }


def resolve_model_setup(
    provider: str = PROVIDER_OFF,
    *,
    fake_script: dict | None = None,
    fake_counter_path: str | Path | None = None,
    fake_default_by_mode: dict[str, str] | None = None,
    prompts_root: str | Path | None = None,
    policy: dict | None = None,
    request_params: dict | None = None,
    timeout_s: float | None = None,
) -> ModelSetup:
    """按提供者装配 ModelSetup;真实提供者缺凭证 → ModelNotConfigured。

    ``request_params``:真实提供者的显式请求参数(如 reasoning_effort);
    与环境变量 ``V43_LLM_REQUEST_PARAMS`` 合并(显式 > env),最终值
    进入身份块。``timeout_s`` 缺省读 ``V43_LLM_TIMEOUT_S``。
    """
    from ..domain.policy import PREDICTION_POLICY_VERSION, prediction_policy

    pol = prediction_policy(policy)
    root = Path(prompts_root) if prompts_root else _default_prompts_root()
    if provider == PROVIDER_OFF:
        return ModelSetup(
            provider=PROVIDER_OFF, model_id="",
            prompts_root=root, prompt_versions=prompt_versions(root),
            policy=pol,
        )
    versions = prompt_versions(root)  # 提示词是身份的一部分,先核验
    if provider == PROVIDER_FAKE:
        client = FakeLLMClient(script=fake_script,
                               counter_path=fake_counter_path,
                               default_by_mode=fake_default_by_mode)
        return ModelSetup(
            provider=PROVIDER_FAKE, model_id=client.model_id, client=client,
            prompts_root=root, prompt_versions=versions, policy=pol,
            request_params=dict(request_params or {}),
            timeout_s=float(timeout_s or 0.0),
        )
    if provider in (PROVIDER_REAL, "real"):  # "real" 为 CLI 简称
        bad = FORBIDDEN_REQUEST_PARAM_KEYS & set(request_params or {})
        if bad:
            raise ModelNotConfigured(
                f"request_params 禁止包含 {sorted(bad)}:"
                "(温度/思考参数只走 prediction_policy_overrides."
                "temperature 通道,确保差异进身份、可预登记)",
                {"keys": sorted(bad)})
        client = OpenAICompatibleClient.from_env()
        if timeout_s is not None:
            client.timeout_s = float(timeout_s)
        if request_params:
            client.request_params = {
                **client.request_params, **request_params}
        # S1 E2:policy 设了 temperature 而模型不支持(kimi-k3 对该参数
        # 直接 API 400)→ 装配期 fail-closed,报"该模型不支持温度臂",
        # 不静默忽略(那会让整批在远端逐请求吃 400)
        temp = pol.get("temperature")
        if temp is not None and not model_supports_temperature(client.model):
            raise ModelNotConfigured(
                "该模型不支持温度臂:" f"{client.model} 不接受 temperature 参数"
                "(API 400: Parameter 'temperature' is not supported);"
                "请去掉 prediction_policy_overrides.temperature 或换用"
                "支持温度的模型",
                {"model_id": client.model, "temperature": temp,
                 "known_unsupported": list(MODELS_WITHOUT_TEMPERATURE_SUPPORT)})
        return ModelSetup(
            provider=PROVIDER_REAL, model_id=client.model, client=client,
            prompts_root=root, prompt_versions=versions, policy=pol,
            request_params=dict(client.request_params),
            timeout_s=float(client.timeout_s),
        )
    raise ModelNotConfigured(
        f"未知模型提供者:{provider}(允许 off|fake|openai_compatible)",
        {"provider": provider},
    )


def _default_prompts_root() -> Path:
    from ..config import repo_root

    return repo_root() / "configs" / "prompts"


def request_hash(payload: dict) -> str:
    """请求输入哈希(同键判定与审计引用;不含密钥)。"""
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True,
                   separators=(",", ":")).encode("utf-8")
    ).hexdigest()
