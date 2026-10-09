"""S5b 真实模型适配层 —— PPV1 proposals 协议的 real provider 接线
(prep §3.2 设计落地;契约登记 s5b-real-model-1)。

范围(本模块只做传输与调用状态,不做内容解释、不碰判分):

- 复用 legacy ``adapters/llm_client.OpenAICompatibleClient`` 整套传输
  语义(429 有界退避/401/403/402 付费停止/usage 归一/Idempotency-Key/
  FileRateGate 批级闸门),**不重写**;
- 凭证只从环境变量读取(``V43_LLM_BASE_URL`` / ``V43_LLM_API_KEY`` /
  ``V43_LLM_MODEL``,可选 ``V43_LLM_TIMEOUT_S`` /
  ``V43_LLM_REQUEST_PARAMS`` / ``V43_LLM_MAX_HTTP_RETRIES`` /
  ``V43_LLM_RATE_GATE``);密钥只在内存,不落盘不入仓不入日志
  (account 文件只记存在性布尔);
- S5b 缺省:timeout 3600s、HTTP 重试 4(沿老 298 复测参数);
- 逐调用记账:issued/response/timeout/传输失败/孤儿 + usage(缺 usage
  保守预留,known-usage 小计与总费用分开);逐调用落盘
  ``<run_dir>/s5b_real_calls.jsonl``(追加;零密钥零凭证);
- 调用序(prep §3.2):``register_model_request(provider_kind="real")``
  (预算在 ``max_real_model_requests`` 上,额度 0 ⇒ 登记被拒 ⇒ 网络发送
  被阻止)→ ``record_request_sent``(real 计 network=1)→
  ``OpenAICompatibleClient.complete`` → ``record_request_response`` /
  ``mark_request_failed`` → 响应文本交 runflow 既有确定性解析器
  (``parse_model_proposals``;JSON 失败走既有 format_feedback 轮逻辑,
  real 反馈轮同样占额度);
- 崩溃恢复:登记后未发(process death)⇒ resume 复用同 request 行
  首发发送;已发无响应(悬空)⇒ 记 failed(孤儿,占额不释放)+ 显式
  新 request(retry_of 记来源)——B2 pending 披露语义保持,不默发
  第二请求;
- ``identity_block()``:进入 PPV1 run identity 的 prediction 块
  (模型 ID/request_params/timeout/prompt 版本;resume 逐字段核对)。

模型只出假设(proposals),不碰判分;判分零 LLM 不变。
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path

from ..adapters.llm_client import (
    DEFAULT_MAX_HTTP_RETRIES,
    LLM_BASE_URL_ENV,
    LLM_API_KEY_ENV,
    LLM_MODEL_ENV,
    LLM_TIMEOUT_ENV,
    OpenAICompatibleClient,
    real_provider_env,
)
from ..domain.models import now_iso, stable_id
from .search import PROVIDER_KIND_REAL

S5B_REAL_MODEL_VERSION = "s5b-real-model-1"

# S5b 缺省超时/重试(沿老 298 复测:llm_timeout_s=3600、retries=4)
S5B_DEFAULT_TIMEOUT_S = 3600.0
S5B_DEFAULT_MAX_HTTP_RETRIES = DEFAULT_MAX_HTTP_RETRIES

# 逐调用账本文件名(run 目录内;gitignored runs 根)
S5B_CALL_ACCOUNT_FILE = "s5b_real_calls.jsonl"


class RealModelNotConfigured(RuntimeError):
    """真实模型装配失败(fail-closed;detail 结构化,零密钥)。"""

    def __init__(self, message: str, detail: dict | None = None):
        super().__init__(message)
        self.detail = detail or {}


# ---------------------------------------------------------------- 提示词

# proposals 协议提示词(冻结模板;内容变更 ⇒ 升 PROPOSALS_PROMPT_VERSION
# ⇒ 身份变化 ⇒ resume 拒)。规则级表述,不含金标不含题面。
_PROPOSALS_SYSTEM_PROMPT = """You are a hypothesis proposer for a deterministic enzyme-degradation pathway search system (PPV1).

Your ONLY job: return ONE JSON object proposing reaction hypotheses for one substrate. You never write databases, never claim recorded status, never score anything. Downstream deterministic code parses, audits and scores your proposals.

Output contract (strict JSON, no markdown fences, no commentary):
{
  "proposals": [
    {
      "hypothesis_id": "<one of the provided pool hypothesis ids>",
      ... optionally "coproducts": ["SMILES", ...]
    }
    OR (novel, outside the pool):
    {
      "hypothesis_id": "<new stable id you invent, e.g. novel-1>",
      "proposal_context": {
        "reference_hypothesis_ids": ["<pool ids you relied on; may be empty>"],
        "output_origin": "novel_outside_pool"
      },
      "reaction_spec": {
        "product_smiles": "<main product SMILES>",
        "coproducts": ["<coproduct SMILES; optional>"],
        "edits": [
          {"op": "break_bond", "atom1": "<id>", "atom2": "<id>"}
          | {"op": "form_bond", "atom1": "<id>", "atom2": "<id>"}
          | {"op": "change_bond_order", "atom1": "<id>", "atom2": "<id>",
             "from_order": "single|double|triple",
             "to_order": "single|double|triple"}
          | {"op": "add_atom", "element": "<element symbol>",
             "new_atom_id": "<id>", "atom1": "<anchor id>"}
        ],
        "donor": {"center_atom_ids": ["<atom ids of the reaction center, donor side>"]},
        "alignment": {
          "status": "resolved",
          "donor_to_current": {"<donor atom id>": "<current atom id>"},
          "ref": "<your alignment reference, e.g. a source reaction id or self-declared>"
        },
        "expectation": {"target_smiles": "<expected product SMILES>"}
      }
    }
  ],
  "rank_hypotheses": ["<hypothesis_id in your preference order, best first>"]
}

Rules:
- pool proposals: "hypothesis_id" MUST be one of the provided pool ids; do not invent pool ids.
- novel proposals MUST carry "proposal_context" and a complete "reaction_spec" (all five fields: product_smiles, edits, donor, alignment, expectation). Incomplete novel proposals are rejected by the parser (a bounded format-feedback round may ask you to fix the JSON shape only).
- "edits" operate on the current substrate atom ids provided in the user message (the atom_id_map). Every edit must reference ids that exist in that map (or a new_atom_id you declare for add_atom, which must not collide).
- "rank_hypotheses" may only reference hypothesis ids present in your proposals.
- abstention is legal and honest: {"proposals": [], "rank_hypotheses": []}.
- one JSON object only; no extra keys that are not in the contract above.
"""

PROPOSALS_PROMPT_VERSION = hashlib.sha256(
    _PROPOSALS_SYSTEM_PROMPT.encode("utf-8")).hexdigest()


def build_proposals_user_payload(
    *, substrate_smiles: str, atom_id_map: dict[str, str],
    pool_entries: list[dict], feedback_error: dict | None = None,
) -> str:
    """组 proposals 请求的用户载荷(JSON 文本;确定性,零金标)。

    - substrate_smiles:题面底物;
    - atom_id_map:当前底物渲染的原子 ID → 元素(供 novel edits 引用);
    - pool_entries:[{hypothesis_id, product_smiles, transformation_ref,
      coproducts}]——冻结池候选(检索来源,不含金标);
    - feedback_error:格式反馈轮携带上一轮错误类别与摘录(有界修复)。
    """
    payload = {
        "substrate_smiles": str(substrate_smiles),
        "substrate_atom_id_map": {
            str(k): str(v) for k, v in sorted(atom_id_map.items())},
        "pool_hypotheses": [
            {"hypothesis_id": str(e.get("hypothesis_id")),
             "product_smiles": str(e.get("product_smiles")),
             "transformation_ref": str(e.get("transformation_ref")),
             "coproducts": [str(c) for c in (e.get("coproducts") or [])]}
            for e in (pool_entries or [])],
        "protocol_version": S5B_REAL_MODEL_VERSION,
    }
    if feedback_error:
        payload["format_feedback"] = {
            "error_kind": str(feedback_error.get("kind") or ""),
            "response_excerpt": str(
                feedback_error.get("response_excerpt") or "")[:800],
            "note": ("Your previous response violated the JSON contract "
                     "above. Return a corrected single JSON object."),
        }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def substrate_atom_id_map(substrate_smiles: str) -> dict[str, str]:
    """底物渲染的原子 ID → 元素(确定性;novel edits 的 ID 空间)。

    渲染失败 ⇒ 空 dict(提示词如实携带空映射;模型 novel 提案引用
    未知 ID 会在执行侧结构化拒,不伪造映射)。
    """
    from ..services.atom_tool import _id_element, render

    try:
        current = render(str(substrate_smiles), "S")
    except Exception:
        return {}
    out: dict[str, str] = {}
    for atom_id, _idx in current.atom_id_map.items():
        element = _id_element(str(atom_id))
        if element:
            out[str(atom_id)] = str(element)
    return out


# ---------------------------------------------------------------- 适配器


class RealModelAdapter:
    """PPV1 proposals 的 real provider 适配器(传输层;身份可冻结)。

    - ``client``:legacy ``OpenAICompatibleClient``(复用,不重写);
    - ``call_account_path``:逐调用账本(JSONL 追加;None ⇒ 不落盘
      账本,调用状态仍在 ledger model_requests 表);
    - ``identity_block()`` 供 runflow ``_prediction_block`` 消费
      (resume 逐字段核对拒绝静默继续)。
    """

    provider = "openai_compatible"

    def __init__(self, client: OpenAICompatibleClient, *,
                 call_account_path: str | Path | None = None) -> None:
        self.client = client
        self.call_account_path = (
            Path(call_account_path) if call_account_path else None)
        self.model_id = client.model
        self.request_params = dict(client.request_params)
        self.timeout_s = float(client.timeout_s)
        self.max_http_retries = int(client.max_http_retries)

    # ------------------------------------------------------------ 装配

    @classmethod
    def from_env(cls, *, timeout_s: float | None = None,
                 request_params: dict | None = None,
                 max_http_retries: int | None = None,
                 call_account_path: str | Path | None = None,
                 ) -> "RealModelAdapter":
        """从环境装配(缺凭证 ⇒ RealModelNotConfigured,零密钥 detail)。

        凭证读取(部署定案 2026-10-09):主名 ``V43_LLM_BASE_URL`` /
        ``V43_LLM_API_KEY`` / ``V43_LLM_MODEL``(受限专用文件
        ``.dependingv43-dashscope.env`` 注入);v41 老名
        ``LLM_API_BASE_URL`` / ``LLM_API_KEY`` / ``LLM_MODEL`` 只作
        只读回退(值只进内存,不打印不落盘不写入任何 detail)。
        """
        base_url = os.environ.get(LLM_BASE_URL_ENV) or os.environ.get(
            "LLM_API_BASE_URL") or ""
        api_key = os.environ.get(LLM_API_KEY_ENV) or os.environ.get(
            "LLM_API_KEY") or ""
        model = os.environ.get(LLM_MODEL_ENV) or os.environ.get(
            "LLM_MODEL") or ""
        missing = [name for name, value in (
            (LLM_BASE_URL_ENV, base_url),
            (LLM_API_KEY_ENV, api_key),
            (LLM_MODEL_ENV, model),
        ) if not value]
        if missing:
            raise RealModelNotConfigured(
                "真实提供者环境变量缺失(主名 V43_LLM_* 与 v41 老名均"
                "缺席;凭证只从环境读取,不落盘):" + ",".join(missing),
                {"missing_env": missing})
        client = OpenAICompatibleClient(
            base_url=base_url, api_key=api_key, model=model)
        client.timeout_s = float(
            timeout_s if timeout_s is not None
            else (os.environ.get(LLM_TIMEOUT_ENV) or
                  S5B_DEFAULT_TIMEOUT_S))
        if request_params:
            merged = dict(client.request_params)
            merged.update(request_params)
            client.request_params = merged
        client.max_http_retries = int(
            max_http_retries if max_http_retries is not None
            else (os.environ.get("V43_LLM_MAX_HTTP_RETRIES")
                  or S5B_DEFAULT_MAX_HTTP_RETRIES))
        return cls(client, call_account_path=call_account_path)

    # ------------------------------------------------------------ 身份

    def identity_block(self) -> dict:
        """进入 run_identity 的 prediction 块(不含 client/密钥)。"""
        from ..domain.policy import PREDICTION_POLICY_VERSION

        return {
            "enabled": True,
            "provider": self.provider,
            "model_id": self.model_id,
            "prompt_versions": {"proposals": PROPOSALS_PROMPT_VERSION},
            "policy_version": PREDICTION_POLICY_VERSION,
            "policy": {},
            "request_params": dict(self.request_params),
            "timeout_s": float(self.timeout_s),
        }

    # ------------------------------------------------------------ 账本

    def _append_account(self, record: dict) -> None:
        if self.call_account_path is None:
            return
        path = Path(self.call_account_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(
            {**record, "provider_env": real_provider_env(),
             "recorded_at": now_iso()},
            ensure_ascii=False, sort_keys=True)
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")

    # ------------------------------------------------------------ 取响应

    def _complete(self, *, system_prompt: str, user_payload: str,
                  idempotency_key: str):
        """传输入口(真实 = legacy 客户端;scripted 桩子类覆写)。"""
        return self.client.complete(
            mode="proposals", system_prompt=system_prompt,
            user_payload=user_payload,
            idempotency_key=idempotency_key)

    def ppv1_real_fetch(self, *, ledger, run_id: str, action_id: str,
                        attempt_id: str, prompt_payload: dict,
                        request_key: str, purpose: str = "proposals",
                        request: dict | None = None,
                        feedback_error: dict | None = None,
                        provider_kind: str = PROVIDER_KIND_REAL) -> dict:
        """登记 → 发送 → 传输 → 记账,返回响应与请求行(runflow 消费)。

        调用序(prep §3.2;失败/超时/悬空均占额,永不释放):
        1. request 行已给(格式反馈轮:``register_format_feedback_round``
           已登记)⇒ 直接消费;否则 ``register_model_request`` 登记
           (``provider_kind`` 沿 plan:real ⇒ 占 max_real_model_requests
           额度,额度 0 ⇒ SearchBudgetExhausted 上抛,网络发送被阻止;
           scripted 桩 ⇒ 网络 0、不占真实额度);
        2. 既有行状态 registered ⇒ 首发;sent ⇒ 悬空孤儿(记 failed
           + 显式新 request,retry_of 记来源;不默发第二请求);
        3. ``record_request_sent`` → ``complete``(Idempotency-Key=请求
           稳定 ID;429/闸门/付费停止语义全在客户端内);
        4. ok ⇒ ``record_request_response``;传输失败/超时/空响应 ⇒
           ``mark_request_failed`` + 结构化失败上抛(失败题留分母);
        5. 逐调用记账(usage 归一;缺 usage 保守预留)。
        """
        if request is None:
            request = ledger.register_model_request(
                run_id=run_id, action_id=action_id, attempt_id=attempt_id,
                provider_kind=provider_kind, request_key=request_key,
                purpose=purpose, payload={
                    "prompt_digest": hashlib.sha256(
                        json.dumps(prompt_payload, ensure_ascii=False,
                                   sort_keys=True).encode("utf-8")
                    ).hexdigest(),
                    "purpose": purpose,
                    "feedback": bool(feedback_error),
                })
        request_id = str(request["request_id"])
        row = ledger.conn.execute(
            "SELECT * FROM model_requests WHERE request_id = ?",
            (request_id,)).fetchone()
        status = str(row["status"]) if row is not None else ""
        if status == "sent":
            # 悬空(crash 后 resume):孤儿如实记 failed(占额);显式新
            # request 承载本次发送(retry_of 记来源;B2 披露语义保持)
            ledger.mark_request_failed(request_id)
            self._append_account({
                "request_id": request_id, "request_key": request_key,
                "purpose": purpose, "status": "orphan_marked_failed",
                "note": "sent-without-response (B2): failed, quota kept",
            })
            request = ledger.register_model_request(
                run_id=run_id, action_id=action_id, attempt_id=attempt_id,
                provider_kind=provider_kind,
                request_key=f"{request_key}:r{int(time.time())}",
                purpose=purpose,
                payload={"prompt_digest": hashlib.sha256(
                    json.dumps(prompt_payload, ensure_ascii=False,
                               sort_keys=True).encode("utf-8")
                ).hexdigest(), "purpose": purpose,
                    "feedback": bool(feedback_error)},
                retry_of=request_id)
            request_id = str(request["request_id"])
        elif status not in ("registered", ""):
            raise RealModelNotConfigured(
                f"请求 {request_id} 状态 {status} 不可消费(生命周期拒绝;"
                "同键幂等复用须 registered)", {
                    "request_id": request_id, "status": status,
                    "kind": "request_not_consumable"})
        ledger.record_request_sent(request_id)
        self._append_account({
            "request_id": request_id, "request_key": request_key,
            "purpose": purpose, "status": "issued",
        })
        response = self._complete(
            system_prompt=_PROPOSALS_SYSTEM_PROMPT,
            user_payload=build_proposals_user_payload(
                substrate_smiles=str(prompt_payload.get(
                    "substrate_smiles") or ""),
                atom_id_map=dict(
                    prompt_payload.get("atom_id_map") or {}),
                pool_entries=list(
                    prompt_payload.get("pool_entries") or []),
                feedback_error=feedback_error),
            idempotency_key=stable_id(
                "s5b", run_id, action_id, request_key),
        )
        call_record = {
            "request_id": request_id, "request_key": request_key,
            "purpose": purpose,
            "ok": bool(response.ok),
            "error_kind": str(response.error_kind or ""),
            "elapsed_s": round(float(response.elapsed_s or 0.0), 3),
            "http_attempts": [
                {k: v for k, v in (a or {}).items()}
                for a in (response.http_attempts or [])],
            "usage": _normalized_usage(response.usage),
            "provider_request_id": response.request_id or "",
            "sent_at_epoch": response.sent_at_epoch,
            "done_at_epoch": response.done_at_epoch,
            "response_chars": len(response.raw_text or ""),
        }
        if response.ok:
            ledger.record_request_response(
                request_id,
                response_ref=f"s5b-call:{request_id}")
            self._append_account({
                **call_record, "status": "responded",
                "response_text": str(response.raw_text or "")[:20000],
            })
        else:
            ledger.mark_request_failed(request_id)
            self._append_account({
                **call_record, "status": "failed",
                "response_text": str(response.raw_text or "")[:20000],
            })
            raise RealModelTransportFailure(
                f"真实模型调用失败({response.error_kind or 'unknown'};"
                "失败/超时/悬空占额,失败题留 298 分母;传输层 429 重试"
                "已在客户端内有界完成)", {
                    "request_id": request_id, "request_key": request_key,
                    "error_kind": str(response.error_kind or ""),
                    "error_message": str(response.error_message or ""),
                    "kind": "real_model_transport_failure"})
        return {"request": dict(request), "response_text":
                str(response.raw_text or ""), "call": call_record}


class RealModelTransportFailure(RuntimeError):
    """真实模型传输失败/超时/空响应(结构化;失败题留分母)。"""

    def __init__(self, message: str, detail: dict | None = None):
        super().__init__(message)
        self.detail = detail or {}


def _normalized_usage(usage: dict) -> dict:
    """provider usage → 归一口径(缺席字段显式缺,不估算冒充实测)。"""
    from ..adapters.llm_client import normalize_usage

    normalized = normalize_usage(dict(usage or {}))
    out = {k: v for k, v in normalized.items() if k != "raw"}
    return out


# ---------------------------------------------------------------- scripted 桩


class ScriptedRealModelAdapter(RealModelAdapter):
    """scripted 模型桩(测试/冒烟;与真实适配器**同一**取响应调用序
    与同一确定性解析器,provider_kind 按 plan 注册(scripted ⇒ 网络 0、
    不占真实额度);不冒充在线模型验证)。

    - ``strategy="first_pool"``:从提示词载荷里解析冻结池,提案首个
      池条目(确定性;完整链验收用——不预知 hypothesis_id);
    - ``strategy="responses"``:按序消费 ``responses`` 列表(耗尽 ⇒
      合法弃权 ``{"proposals": []}``);
    - ``fail_with``:可选 {error_kind, error_message}(传输失败桩)。
    """

    provider = "scripted-stub"

    def __init__(self, *, strategy: str = "first_pool",
                 responses: list[str] | None = None,
                 fail_with: dict | None = None,
                 model_id: str = "s5b-scripted-stub-v1",
                 call_account_path: str | Path | None = None) -> None:
        self.strategy = str(strategy)
        self.responses = [str(r) for r in (responses or [])]
        self.fail_with = dict(fail_with or {})
        self.model_id = model_id
        self.request_params: dict = {}
        self.timeout_s = 0.0
        self.max_http_retries = 0
        self.client = None  # type: ignore[assignment]
        self.call_account_path = (
            Path(call_account_path) if call_account_path else None)
        self.seen_user_payloads: list[str] = []

    def identity_block(self) -> dict:
        from ..domain.policy import PREDICTION_POLICY_VERSION

        return {
            "enabled": True,
            "provider": self.provider,
            "model_id": self.model_id,
            "prompt_versions": {"proposals": PROPOSALS_PROMPT_VERSION},
            "policy_version": PREDICTION_POLICY_VERSION,
            "policy": {"strategy": self.strategy},
            "request_params": {},
            "timeout_s": 0.0,
        }

    def _complete(self, *, system_prompt: str, user_payload: str,
                  idempotency_key: str):
        from ..adapters.llm_client import LLMResponse

        self.seen_user_payloads.append(str(user_payload))
        if self.fail_with:
            return LLMResponse(
                ok=False,
                error_kind=str(self.fail_with.get("error_kind")
                               or "transport_error"),
                error_message=str(
                    self.fail_with.get("error_message") or "stub-failure"))
        if self.strategy == "responses" and self.responses:
            raw = self.responses.pop(0)
        elif self.strategy == "responses":
            raw = '{"proposals": []}'
        else:  # first_pool:从载荷解析冻结池,提案首个池条目
            try:
                payload = json.loads(user_payload)
                pool = payload.get("pool_hypotheses") or []
            except (ValueError, TypeError):
                pool = []
            if pool:
                first = str(pool[0].get("hypothesis_id") or "")
                raw = json.dumps(
                    {"proposals": [{"hypothesis_id": first}],
                     "rank_hypotheses": [first]},
                    ensure_ascii=False)
            else:
                raw = '{"proposals": []}'
        return LLMResponse(
            ok=bool(raw.strip()), raw_text=raw,
            error_kind="" if raw.strip() else "empty_response",
            elapsed_s=0.0, usage={"fake": True})
