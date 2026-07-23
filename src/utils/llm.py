"""LLM 统一调用封装（OpenAI-compat 客户端）

历史：M3-P1 初版直调 dashscope.Generation SDK；2026-07-22 改为 OpenAI-compat
HTTPX 客户端，走内部 MaaS 网关，支持 kimi-k3 等模型。函数名 `call_dashscope`
保留以兼容调用点，实际后端由 .env 的 LLM_API_BASE_URL / LLM_API_KEY 决定。

环境变量：
  LLM_API_BASE_URL   OpenAI-compat endpoint，形如 https://.../compatible-mode/v1
  LLM_API_KEY        Bearer token

每个 node 的 model 名由 config/llm_config.yaml 决定。
"""

import os
import time
import yaml
import logging
from pathlib import Path
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


def load_llm_config(node_name: str, config_path: Optional[Path] = None) -> dict:
    """加载指定节点的 LLM 配置"""
    if config_path is None:
        config_path = Path(__file__).parent.parent.parent / "config" / "llm_config.yaml"
    with open(config_path, "r") as f:
        cfg = yaml.safe_load(f)
    node_cfg = cfg.get("nodes", {}).get(node_name, {})
    if not node_cfg or node_cfg.get("provider") == "none":
        raise ValueError(f"LLM config for node '{node_name}' not found or disabled")
    return node_cfg


def call_dashscope(
    prompt: str,
    system_prompt: str = "",
    node_name: str = "substrate_node",
    config_path: Optional[Path] = None,
) -> str:
    """OpenAI-compat chat/completions 调用，返回 message.content 纯文本。

    函数名保留 `call_dashscope` 以避免全项目 refactor；实际后端由 env
    LLM_API_BASE_URL / LLM_API_KEY 决定。
    """
    cfg = load_llm_config(node_name, config_path)

    base_url = os.environ.get("LLM_API_BASE_URL", "").rstrip("/")
    api_key = os.environ.get("LLM_API_KEY", "")
    if not base_url or not api_key:
        raise RuntimeError(
            "LLM API 未配置：请在 .env 里设置 LLM_API_BASE_URL 与 LLM_API_KEY"
        )

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": cfg["model"],
        "messages": messages,
        "temperature": cfg.get("temperature", 0.1),
        "max_tokens": cfg.get("max_tokens", 500),
    }

    url = f"{base_url}/chat/completions"
    # 针对 MaaS 网关 429 EngineOverloadedError 的 exponential backoff retry
    max_retries = 3
    backoff = 2.0
    for attempt in range(max_retries):
        try:
            resp = httpx.post(
                url,
                json=payload,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                timeout=cfg.get("timeout", 60.0),
            )
        except httpx.HTTPError as e:
            if attempt == max_retries - 1:
                raise RuntimeError(f"LLM API network error: {e}") from e
            logger.warning(f"LLM 网络异常 attempt={attempt+1}/{max_retries}: {e}")
            time.sleep(backoff * (2 ** attempt))
            continue

        if resp.status_code == 429 and attempt < max_retries - 1:
            logger.warning(f"LLM 429 overloaded attempt={attempt+1}/{max_retries}, backoff={backoff*(2**attempt)}s")
            time.sleep(backoff * (2 ** attempt))
            continue
        break

    if resp.status_code != 200:
        # 保留 "API error: {code}" 措辞，与既有测试匹配（case_3 verdict 里的 stage 判断）
        raise RuntimeError(
            f"LLM API error: {resp.status_code} - {resp.text[:300]}"
        )

    data = resp.json()
    try:
        choice = data["choices"][0]
        msg = choice["message"]
        content = msg.get("content") or ""
        # kimi-k3 等 reasoning 模型：若 max_tokens 抢完了都没走到 content 阶段，
        # finish_reason 会是 length 且 content 空，reasoning_content 里存的是思考过程，
        # 不能当正式输出使用。这时报明确错便上层升调 max_tokens。
        if not content.strip():
            finish_reason = choice.get("finish_reason")
            reasoning_len = len(msg.get("reasoning_content") or "")
            raise RuntimeError(
                f"LLM 返回 content 为空（finish_reason={finish_reason}，"
                f"reasoning_content 长度={reasoning_len}）；"
                f"若 finish_reason=length，请提高当前节点的 max_tokens"
            )
        return content
    except (KeyError, IndexError) as e:
        raise RuntimeError(f"LLM API 响应结构异常: {data}") from e
