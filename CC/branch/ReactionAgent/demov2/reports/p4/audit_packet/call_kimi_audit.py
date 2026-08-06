"""调用 kimi-k3 审核（两轮交互的通用客户端）。

用法:
  python3 scripts/call_kimi_audit.py <system_prompt_file> <user_prompt_file> <output_file> [max_tokens]

读取项目 .env 的 LLM_API_BASE_URL / LLM_API_KEY（不打印 key）。
"""
import json
import os
import sys
from pathlib import Path

import httpx

PROJECT_ROOT = Path("/Volumes/CC/Enzyme_Agent/depending")
ENV_PATH = PROJECT_ROOT / ".env"


def load_env() -> tuple[str, str]:
    env: dict[str, str] = {}
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("LLM_API_BASE_URL="):
            env["base"] = line.split("=", 1)[1].strip()
        elif line.startswith("LLM_API_KEY="):
            env["key"] = line.split("=", 1)[1].strip()
    if "base" not in env or "key" not in env:
        raise RuntimeError(".env 缺少 LLM_API_BASE_URL 或 LLM_API_KEY")
    return env["base"], env["key"]


def main() -> None:
    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit(1)
    system_file, user_file, out_file = sys.argv[1], sys.argv[2], sys.argv[3]
    max_tokens = int(sys.argv[4]) if len(sys.argv) > 4 else 8000

    base, key = load_env()
    system_prompt = Path(system_file).read_text(encoding="utf-8")
    user_prompt = Path(user_file).read_text(encoding="utf-8")

    payload = {
        "model": "kimi/kimi-k3",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.1,
        "max_tokens": max_tokens,
    }
    url = f"{base.rstrip('/')}/chat/completions"
    last_err = None
    for attempt in range(4):
        try:
            with httpx.Client(timeout=600) as client:
                resp = client.post(
                    url, json=payload,
                    headers={"Authorization": f"Bearer {key}"},
                )
            if resp.status_code == 200:
                break
            last_err = f"HTTP {resp.status_code}: {resp.text[:300]}"
        except Exception as e:  # noqa: BLE001 — transient network errors
            last_err = f"{type(e).__name__}: {e}"
        print(f"⚠️ 第 {attempt + 1} 次尝试失败: {last_err}", file=sys.stderr)
        import time
        time.sleep(10 * (attempt + 1))
    else:
        print(f"❌ 重试 4 次仍失败: {last_err}", file=sys.stderr)
        sys.exit(2)
    if resp.status_code != 200:
        print(f"HTTP {resp.status_code}: {resp.text[:500]}", file=sys.stderr)
        sys.exit(2)
    d = resp.json()
    msg = d["choices"][0]["message"]
    result = {
        "model": d.get("model"),
        "finish_reason": d["choices"][0].get("finish_reason"),
        "usage": d.get("usage"),
        "content": msg.get("content", ""),
        "reasoning_content": msg.get("reasoning_content", ""),
    }
    Path(out_file).write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ 已保存到 {out_file}")
    print(f"finish_reason={result['finish_reason']} "
          f"content_tokens≈{len(result['content'])} chars")
    if result["finish_reason"] == "length":
        print("⚠️ 输出被截断（max_tokens 不够），请增大后重试")


if __name__ == "__main__":
    main()