#!/usr/bin/env python
"""DashScope 按量 API 低额度烟测(TASK_V43_EXPORT_DEV §3)。

以生产 ``OpenAICompatibleClient`` 发起**一次**真实最小调用,验证:
1. 该工作区 Key/模型(ZHIPU/GLM-5.3-Flash)已开通且参数可用;
2. 仅思考参数(request_params:reasoning_effort=max,无 temperature);
3. 最终 content 与 reasoning_content 分离(解析只取 content);
4. usage 可解析(思考 token 按输出计费口径)。

凭证只经环境变量(V43_LLM_*)读取,不打印、不落盘;烟测与正式批次的
调用和用量分开记录(本脚本把请求/响应审计写入 --out JSON,不含密钥)。

用法(Chenyu):
    set -a; . /usrdata/EnzymeCAGE_data/workspaces/.dependingv43-dashscope.env; set +a
    OMP_NUM_THREADS=1 PYTHONPATH=src python scripts/dashscope_smoke.py \
        --out smoke/dashscope_smoke.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="smoke/dashscope_smoke.json")
    ap.add_argument("--request-params", default='{"reasoning_effort": "max"}',
                    help="冻结请求参数 JSON(默认 reasoning_effort=max)")
    ap.add_argument("--max-http-retries", type=int, default=2)
    a = ap.parse_args()

    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    from pathway_v43.adapters.llm_client import (
        OpenAICompatibleClient,
        normalize_usage,
        real_provider_env,
        request_hash,
    )

    env = real_provider_env()
    if not (env["base_url_set"] and env["api_key_set"] and env["model_set"]):
        print(json.dumps({"ok": False,
                          "status": "not_run:no_credentials_or_access",
                          "missing": [k for k, v in (
                              ("V43_LLM_BASE_URL", env["base_url_set"]),
                              ("V43_LLM_API_KEY", env["api_key_set"]),
                              ("V43_LLM_MODEL", env["model_set"])) if not v]}))
        return 2

    import os

    client = OpenAICompatibleClient(
        base_url=os.environ["V43_LLM_BASE_URL"],
        api_key=os.environ["V43_LLM_API_KEY"],
        model=os.environ["V43_LLM_MODEL"],
        request_params=json.loads(a.request_params),
        max_http_retries=a.max_http_retries,
    )
    user_payload = json.dumps({
        "task": "smoke",
        "instruction": "回复 JSON:{\"decision\":\"ok\",\"note\":\"<5字以内>\"},不要输出其他内容",
    }, ensure_ascii=False)
    t0 = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    resp = client.complete(
        mode="smoke", system_prompt="你是协议冒烟测试器,只输出合法 JSON。",
        user_payload=user_payload,
        idempotency_key=f"v43-smoke-{int(time.time())}",
    )
    record = {
        "schema_version": "v43-dashscope-smoke-1",
        "started_at": t0,
        "model_id": client.model,
        "base_url_host": client.base_url.split("/")[2] if "//" in client.base_url
        else client.base_url,
        "request_params": dict(client.request_params),
        "timeout_s": client.timeout_s,
        "user_payload_sha256": hashlib.sha256(
            user_payload.encode()).hexdigest(),
        "request_hash": request_hash({"user_payload": user_payload}),
        "ok": resp.ok,
        "error_kind": resp.error_kind,
        "error_message": resp.error_message,
        "status": resp.status,
        "http_attempts": resp.http_attempts,
        "elapsed_s": round(resp.elapsed_s, 2),
        "raw_text_preview": resp.raw_text[:400],
        "parsed_json_ok": False,
        "usage_normalized": normalize_usage(resp.usage),
        "usage_raw": resp.usage,
        "note": ("smoke call is recorded separately from the formal batch; "
                 "no API key stored in this file"),
    }
    try:
        parsed = json.loads(resp.raw_text)
        record["parsed_json_ok"] = isinstance(parsed, dict)
        record["parsed_decision"] = parsed.get("decision")
    except Exception:
        pass
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n",
                   encoding="utf-8")
    blob = json.dumps(record, ensure_ascii=False)
    assert "sk-" not in blob or not os.environ.get("V43_LLM_API_KEY", "").startswith("sk-") \
        or os.environ["V43_LLM_API_KEY"] not in blob, "凭证脱敏检查失败"
    print(json.dumps({"ok": resp.ok, "out": str(out),
                      "error_kind": resp.error_kind,
                      "elapsed_s": record["elapsed_s"],
                      "usage": record["usage_normalized"]},
                     ensure_ascii=False))
    return 0 if resp.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
