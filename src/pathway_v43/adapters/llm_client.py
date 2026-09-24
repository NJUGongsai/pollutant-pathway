"""LLM 客户端适配器 — 唯一允许发出外部模型请求的模块(REPO_DESIGN §3)。

三种提供者:

- ``off``:不配置模型。确定性流程照常,遇待预测明确停 awaiting_prediction
  (第一阶段语义,不谎称预测完成)。
- ``fake``:FakeLLMClient,剧本化响应 + 跨进程调用计数。测试与无凭证演示
  用;其输出与真实响应走**同一**确定性解析器,不得冒充在线模型验证。
- ``openai_compatible``:真实提供者(OpenAI 兼容 /chat/completions,
  urllib,零第三方依赖)。配置只从环境变量读取:
  ``V43_LLM_BASE_URL``、``V43_LLM_API_KEY``、``V43_LLM_MODEL``(可选
  ``V43_LLM_TIMEOUT_S``);密钥绝不写入任何文件、日志或报告。提供者支持
  时随请求携带 ``Idempotency-Key``(预测调用的请求幂等键)。

预测纪律(任务书 §2):解析失败、超时、空响应是显式结果,由
services/prediction.parse_model_response 判定;本模块只负责传输与调用状态,
不做内容解释。
"""

from __future__ import annotations

import hashlib
import json
import os
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

DEFAULT_TIMEOUT_S = 60.0


@dataclass
class LLMResponse:
    """一次(尝试)调用的传输结果;解析是下游的确定性步骤。"""

    ok: bool                     # 传输层是否拿到非空文本
    raw_text: str = ""
    error_kind: str = ""         # transport_error | timeout | empty_response
    error_message: str = ""
    elapsed_s: float = 0.0
    usage: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return dict(self.__dict__)


class ModelNotConfigured(RuntimeError):
    """请求模型但未配置/凭证缺失(fail-closed;detail 结构化,无密钥)。"""

    def __init__(self, message: str, detail: dict | None = None):
        super().__init__(message)
        self.detail = detail or {}


def prompt_versions(prompts_root: str | Path) -> dict[str, str]:
    """三协议提示词的 SHA256 版本(内容变更即升版本;身份核对用)。"""
    root = Path(prompts_root)
    out = {}
    for mode, fname in (
        ("rank_candidates", "ranker.md"),
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
    }


class OpenAICompatibleClient:
    """OpenAI 兼容 /chat/completions 客户端(urllib;密钥只在内存)。"""

    provider = PROVIDER_REAL

    def __init__(self, base_url: str, api_key: str, model: str,
                 timeout_s: float | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout_s = float(
            timeout_s or os.environ.get(LLM_TIMEOUT_ENV) or DEFAULT_TIMEOUT_S
        )

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

    def complete(self, *, mode: str, system_prompt: str, user_payload: str,
                 idempotency_key: str | None = None,
                 temperature: float = 0.0) -> LLMResponse:
        body = json.dumps({
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_payload},
            ],
            "temperature": temperature,
        }).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        if idempotency_key:
            # 提供者支持时传入请求幂等键(任务书 §4);不支持的头会被忽略
            headers["Idempotency-Key"] = idempotency_key
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions", data=body, headers=headers,
            method="POST",
        )
        t0 = time.monotonic()
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            # HTTPError 是 URLError 子类,先分出来:其 reason 是消息字符串,
            # 落入下面的 reason 分类只会得到无意义的 "str"
            return LLMResponse(ok=False, error_kind="transport_error",
                               error_message=f"{type(exc).__name__}",
                               elapsed_s=time.monotonic() - t0)
        except TimeoutError:
            # Python 3.10+ socket.timeout 的别名;urllib.error 没有
            # TimeoutExpired(修复前引用它会 AttributeError 吞掉原始异常)
            return LLMResponse(ok=False, error_kind="timeout",
                               elapsed_s=time.monotonic() - t0)
        except urllib.error.URLError as exc:
            reason = getattr(exc, "reason", exc)
            is_timeout = isinstance(reason, TimeoutError)
            return LLMResponse(
                ok=False,
                error_kind="timeout" if is_timeout else "transport_error",
                error_message="" if is_timeout else f"{type(reason).__name__}",
                elapsed_s=time.monotonic() - t0,
            )
        except Exception as exc:  # 网络/HTTP 错误:显式传输失败
            return LLMResponse(
                ok=False, error_kind="transport_error",
                error_message=f"{type(exc).__name__}",
                elapsed_s=time.monotonic() - t0,
            )
        elapsed = time.monotonic() - t0
        try:
            text = payload["choices"][0]["message"]["content"] or ""
        except Exception:
            return LLMResponse(ok=False, error_kind="empty_response",
                               elapsed_s=elapsed)
        usage = payload.get("usage") or {}
        return LLMResponse(
            ok=bool(text.strip()), raw_text=text,
            error_kind="" if text.strip() else "empty_response",
            elapsed_s=elapsed, usage=dict(usage),
        )


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
                 temperature: float = 0.0) -> LLMResponse:
        self._bump_counter()
        seq = self.script.get(mode) or []
        if seq:
            raw = seq.pop(0)
        else:
            raw = self.default_by_mode.get(mode, "")
        self.calls.append({
            "mode": mode, "idempotency_key": idempotency_key,
            "model_id": self.model_id,
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

    def identity_block(self) -> dict:
        """进入 run_identity 的 prediction 块(不含 client/密钥)。"""
        return {
            "enabled": self.provider != PROVIDER_OFF,
            "provider": self.provider,
            "model_id": self.model_id,
            "prompt_versions": dict(self.prompt_versions),
            "policy_version": self.policy.get("policy_version", ""),
            "policy": {k: v for k, v in self.policy.items()
                       if k != "policy_version"},
        }


def resolve_model_setup(
    provider: str = PROVIDER_OFF,
    *,
    fake_script: dict | None = None,
    fake_counter_path: str | Path | None = None,
    fake_default_by_mode: dict[str, str] | None = None,
    prompts_root: str | Path | None = None,
    policy: dict | None = None,
) -> ModelSetup:
    """按提供者装配 ModelSetup;真实提供者缺凭证 → ModelNotConfigured。"""
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
        )
    if provider in (PROVIDER_REAL, "real"):  # "real" 为 CLI 简称
        client = OpenAICompatibleClient.from_env()
        return ModelSetup(
            provider=PROVIDER_REAL, model_id=client.model, client=client,
            prompts_root=root, prompt_versions=versions, policy=pol,
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
