"""直接 curl kimi/kimi-k3 看 (S)-6-hydroxynicotine 案例的原始返回，
诊断 substrate_parser LLM 兜底 parse fail 到底是哪种失败：
  (a) content 空、答案全在 reasoning_content
  (b) max_tokens 截断（finish_reason=length）
  (c) 内容被 markdown/reasoning wrapper 包裹
  (d) 触发内容审核（finish_reason=content_filter）
"""
import os
import json
import httpx
from pathlib import Path

# 手动读 .env
env_path = Path(__file__).parent.parent / ".env"
for line in env_path.read_text().splitlines():
    if line.startswith("LLM_API_BASE_URL="):
        os.environ["LLM_API_BASE_URL"] = line.split("=", 1)[1].strip()
    elif line.startswith("LLM_API_KEY="):
        os.environ["LLM_API_KEY"] = line.split("=", 1)[1].strip()

base_url = os.environ["LLM_API_BASE_URL"].rstrip("/")
api_key = os.environ["LLM_API_KEY"]

SYSTEM_PROMPT = """你是一个专业的化学信息助手。你的任务是从用户的输入中提取底物分子的SMILES表示。

规则：
1. 如果用户直接提供了 SMILES，验证并返回
2. 如果用户提供了分子名称，将其转换为 SMILES
3. 如果用户提供了 InChI，将其转换为 SMILES
4. 你必须以 JSON 格式返回结果

输出格式（严格JSON，不要附加其他文字）：
{"smiles": "CCCCCC", "name": "hexane", "source": "user_smiles|user_inchi|llm_parsed"}

如果无法解析，返回：
{"smiles": null, "name": null, "source": null, "error": "无法识别底物"}
"""

user_prompt = "用户输入: 需要一个能作用于 (S)-6-hydroxynicotine 的酶"

payload = {
    "model": "kimi/kimi-k3",
    "messages": [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ],
    "temperature": 0.1,
    "max_tokens": 4000,
}

resp = httpx.post(
    f"{base_url}/chat/completions",
    json=payload,
    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
    timeout=120.0,
)

print(f"=== HTTP {resp.status_code} ===")
data = resp.json()
print(json.dumps(data, ensure_ascii=False, indent=2))
print()
print("=== 关键字段 ===")
try:
    choice = data["choices"][0]
    msg = choice["message"]
    print(f"finish_reason        = {choice.get('finish_reason')}")
    print(f"content              = {msg.get('content')!r}")
    print(f"reasoning_content    = {msg.get('reasoning_content')!r}")
    print(f"content type         = {type(msg.get('content'))}")
    print(f"content length       = {len(msg.get('content') or '')}")
    print(f"reasoning length     = {len(msg.get('reasoning_content') or '')}")
    usage = data.get("usage", {})
    print(f"usage                = {usage}")
except Exception as e:
    print(f"parse err: {e}")
