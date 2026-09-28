"""DashScope 客户端语义与跨进程速率闸门测试(TASK_V43_EXPORT_DEV §5.5)。

- 429:结构化 rate_limited、有界指数退避 + 抖动、Retry-After 封顶、
  退避后继续且不产生重复调用记录;不把 429 当化学失败。
- 401/403:forbidden_permanent + 全局闸门停止,停止一切新付费请求。
- 超时/URLError/HTTP 4xx/5xx:结构化传输失败(节点层 attempt 重试)。
- 仅思考模型:请求体无 temperature/enable_thinking;reasoning_effort
  显式锁定;最终 content 与 reasoning_content 分离(只取 content);
  usage 归一(思考 token 按输出计费口径透传)。
- 凭证脱敏:错误消息/闸门状态文件不含密钥。
- 跨进程闸门:两进程共享 RPM 滑窗/全局停止/批次调用预算(子进程实测)。
"""

from __future__ import annotations

import io
import json
import subprocess
import sys
import urllib.error
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pathway_v43.adapters import rate_gate as rg  # noqa: E402
from pathway_v43.adapters.llm_client import (  # noqa: E402
    LLMResponse,
    OpenAICompatibleClient,
    normalize_usage,
)
from pathway_v43.adapters.rate_gate import (  # noqa: E402
    FileRateGate,
    GateBudgetExhausted,
    GateStopped,
)


def _client(monkeypatch, *, responses, gate=None, max_retries=4,
            sleeps=None, request_params=None):
    """urlopen 打桩:按序返回 responses(HTTPError 异常 / 200 payload 字典)。"""
    calls = {"n": 0, "bodies": [], "headers": []}

    def fake_urlopen(req, timeout=None):
        idx = calls["n"]
        calls["n"] += 1
        calls["bodies"].append(json.loads(req.data.decode("utf-8")))
        headers = {k.lower(): v for k, v in req.header_items()}
        calls["headers"].append(headers)
        out = responses[min(idx, len(responses) - 1)]
        if isinstance(out, Exception):
            raise out
        resp = io.BytesIO(json.dumps(out).encode("utf-8"))
        resp.status = 200
        resp.headers = {"X-Dashscope-Request-Id": "req-42"}
        return resp

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    recorded_sleeps = []

    def fake_sleep(s):
        recorded_sleeps.append(round(float(s), 3))

    monkeypatch.setattr("pathway_v43.adapters.llm_client.time.sleep",
                        fake_sleep)
    client = OpenAICompatibleClient(
        base_url="https://llm.example/v1", api_key="sk-secret", model="m",
        timeout_s=5, gate=gate, max_http_retries=max_retries,
        request_params=request_params,
    )
    return client, calls, recorded_sleeps


def _ok_payload(content='{"decision": "select"}', usage=None):
    body = {
        "choices": [{"message": {"role": "assistant",
                                 "content": content}}],
    }
    if usage is not None:
        body["usage"] = usage
    return body


def _http_error(status, headers=None):
    return urllib.error.HTTPError(
        "https://llm.example/v1/chat/completions", status, "err", headers
        or {}, io.BytesIO(b""))


# ---------------------------------------------------------------- 请求参数


def test_thinking_model_request_body_has_no_temperature(monkeypatch):
    """仅思考模型:请求体不含 temperature/enable_thinking;reasoning_effort
    显式锁定;密钥只在 Authorization 头,不进请求体。"""
    client, calls, _ = _client(
        monkeypatch, responses=[_ok_payload()],
        request_params={"reasoning_effort": "max"})
    resp = client.complete(mode="rank_candidates", system_prompt="s",
                           user_payload="u", idempotency_key="ik")
    assert resp.ok
    body = calls["bodies"][0]
    assert "temperature" not in body
    assert "enable_thinking" not in body
    assert "thinking" not in body
    assert body["reasoning_effort"] == "max"
    assert body["model"] == "m"
    assert "sk-secret" not in json.dumps(body)


def test_request_params_reject_thinking_off_and_temperature():
    """request_params 禁止发送关闭思考/温度参数(仅思考模型红线)。"""
    from pathway_v43.adapters.llm_client import ModelNotConfigured, \
        _request_params_from_env

    import os

    for bad in ({"temperature": 0.0}, {"enable_thinking": False},
                {"thinking": {"type": "disabled"}}):
        os.environ["V43_LLM_REQUEST_PARAMS"] = json.dumps(bad)
        try:
            with pytest.raises(ModelNotConfigured):
                _request_params_from_env()
        finally:
            os.environ.pop("V43_LLM_REQUEST_PARAMS", None)


def test_content_vs_reasoning_content_separation(monkeypatch):
    """最终 content 与 reasoning_content 分离:解析候选只取最终 content,
    思考链不进答卷;usage 原样透传。"""
    payload = _ok_payload(content='{"decision": "select"}',
                          usage={"prompt_tokens": 120,
                                 "completion_tokens": 456,
                                 "total_tokens": 576,
                                 "completion_tokens_details": {
                                     "reasoning_tokens": 400}})
    payload["choices"][0]["message"]["reasoning_content"] = \
        "思考链:先分析候选 1……"
    client, calls, _ = _client(monkeypatch, responses=[payload])
    resp = client.complete(mode="rank_candidates", system_prompt="s",
                           user_payload="u")
    assert resp.ok
    assert resp.raw_text == '{"decision": "select"}'
    assert "思考链" not in resp.raw_text
    assert resp.usage["completion_tokens"] == 456


def test_usage_normalization_reasoning_billed_as_output():
    norm = normalize_usage({
        "prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150,
        "prompt_tokens_details": {"cached_tokens": 10},
        "completion_tokens_details": {"reasoning_tokens": 30}})
    assert norm["input_tokens"] == 100
    assert norm["output_tokens"] == 50  # 思考 token 已含在输出计费口径
    assert norm["cached_input_tokens"] == 10
    assert norm["reasoning_output_tokens"] == 30


def test_usage_missing_marked_not_estimated(monkeypatch):
    """usage 缺失:如实空 usage;账目层不得估算冒充实测(账目测试覆盖)。"""
    client, calls, _ = _client(monkeypatch,
                               responses=[_ok_payload(usage=None)])
    resp = client.complete(mode="rank_candidates", system_prompt="s",
                           user_payload="u")
    assert resp.usage == {}


# ---------------------------------------------------------------- 429


def test_429_bounded_backoff_then_success(monkeypatch):
    """429:退避后重试成功;等待有界(≤60s 封顶)+ 抖动;不抛异常。"""
    responses = [
        _http_error(429, {"Retry-After": "3"}),
        _http_error(429, {}),
        _ok_payload(),
    ]
    client, calls, sleeps = _client(monkeypatch, responses=responses)
    resp = client.complete(mode="rank_candidates", system_prompt="s",
                           user_payload="u")
    assert resp.ok, "429 退避后继续,不当作化学失败"
    assert calls["n"] == 3
    assert resp.error_kind == ""
    assert len(resp.http_attempts) == 2
    assert resp.http_attempts[0]["status"] == 429
    assert resp.http_attempts[0]["retry_after_s"] == 3.0
    assert all(0 < s <= 60 * 1.2 for s in sleeps), "有界退避 + 抖动"
    assert sleeps[0] >= 3.0, "尊重 Retry-After"
    assert sleeps[1] >= 2.0, "无 Retry-After 用指数退避基值"


def test_429_exhaustion_structured_no_unbounded_retry(monkeypatch):
    """429 重试上限:结构化 rate_limited_exhausted,不无界重试。"""
    responses = [_http_error(429)] * 10
    client, calls, _ = _client(monkeypatch, responses=responses,
                               max_retries=2)
    resp = client.complete(mode="rank_candidates", system_prompt="s",
                           user_payload="u")
    assert resp.ok is False
    assert resp.error_kind == "rate_limited_exhausted"
    assert calls["n"] == 3  # 1 + max_retries(2)
    assert [a["status"] for a in resp.http_attempts] == [429, 429, 429]


def test_429_records_request_id_and_gate_cooldown(monkeypatch):
    """429 记录请求 ID;闸门设全局冷却(其他 worker 都遵守)。"""
    gate = FileRateGate(Path("/tmp") / f"gate429-{id(object()):x}", rpm=100,
                        tpm=10**9, max_calls=100)
    responses = [
        _http_error(429, {"Retry-After": "2",
                          "X-Dashscope-Request-Id": "req-429"}),
        _ok_payload(),
    ]
    client, calls, _ = _client(monkeypatch, responses=responses, gate=gate)
    resp = client.complete(mode="rank_candidates", system_prompt="s",
                           user_payload="u")
    assert resp.ok
    snap = gate.snapshot()
    assert snap["total_429"] == 1
    assert snap["cooldown_until"] > 0
    assert snap["total_requests"] == 2  # 两次 HTTP 尝试都经闸门


# ---------------------------------------------------------------- 403/停止


def test_403_forbidden_stops_new_paid_requests(monkeypatch):
    """403:forbidden_permanent + 全局闸门停止;后续调用被闸门拒绝。"""
    gate = FileRateGate(Path("/tmp") / f"gate403-{id(object()):x}", rpm=100,
                        tpm=10**9, max_calls=100)
    client, calls, _ = _client(
        monkeypatch, responses=[_http_error(403, {"X-Dashscope-Request-Id":
                                                  "req-403"})], gate=gate)
    resp1 = client.complete(mode="rank_candidates", system_prompt="s",
                            user_payload="u")
    assert resp1.ok is False
    assert resp1.error_kind == "forbidden_permanent"
    assert resp1.http_attempts[0]["request_id"] == "req-403"
    assert gate.is_stopped()
    # 下一次调用:闸门直接拒绝,不再发 HTTP 请求
    resp2 = client.complete(mode="rank_candidates", system_prompt="s",
                            user_payload="u")
    assert resp2.ok is False
    assert resp2.error_kind == "forbidden_stopped_by_gate"
    assert calls["n"] == 1, "闸门停止后无新 HTTP 请求"


def test_401_also_forbidden(monkeypatch):
    client, _, _ = _client(monkeypatch, responses=[_http_error(401)])
    resp = client.complete(mode="rank_candidates", system_prompt="s",
                           user_payload="u")
    assert resp.error_kind == "forbidden_permanent"


# ---------------------------------------------------------------- 其他错误


def test_timeout_structured(monkeypatch):
    client, _, _ = _client(monkeypatch, responses=[TimeoutError()])
    resp = client.complete(mode="rank_candidates", system_prompt="s",
                           user_payload="u")
    assert resp.ok is False
    assert resp.error_kind == "timeout"


def test_http_400_single_structured_failure_no_client_retry(monkeypatch):
    """400:一次结构化传输失败,不在客户端层重试(节点层 attempt 重试)。"""
    client, calls, _ = _client(monkeypatch, responses=[_http_error(400)],
                               max_retries=4)
    resp = client.complete(mode="rank_candidates", system_prompt="s",
                           user_payload="u")
    assert resp.error_kind == "transport_error"
    assert calls["n"] == 1


def test_5xx_single_structured_failure(monkeypatch):
    client, calls, _ = _client(monkeypatch, responses=[_http_error(500)])
    resp = client.complete(mode="rank_candidates", system_prompt="s",
                           user_payload="u")
    assert resp.error_kind == "transport_error"
    assert calls["n"] == 1


def test_empty_response_with_usage(monkeypatch):
    """content 为空(只有思考)→ empty_response,usage 仍透传计费。"""
    payload = {"choices": [{"message": {"content": "",
                                        "reasoning_content": "只想不说"}}],
               "usage": {"prompt_tokens": 10, "completion_tokens": 99,
                         "total_tokens": 109}}
    client, _, _ = _client(monkeypatch, responses=[payload])
    resp = client.complete(mode="rank_candidates", system_prompt="s",
                           user_payload="u")
    assert resp.ok is False
    assert resp.error_kind == "empty_response"
    assert resp.usage["completion_tokens"] == 99


def test_credential_redaction_in_errors(monkeypatch):
    """错误消息不含密钥/base_url;只有类型名与状态码。"""
    for exc in (TimeoutError(), urllib.error.URLError(OSError("x")),
                _http_error(403), _http_error(429)):
        client, _, _ = _client(monkeypatch, responses=[exc])
        resp = client.complete(mode="rank_candidates", system_prompt="s",
                               user_payload="u")
        blob = json.dumps({k: v for k, v in resp.to_dict().items()
                           if k != "http_attempts"}, ensure_ascii=False)
        assert "sk-secret" not in blob
        assert "llm.example" not in blob
    # http_attempts 只含 status/retry_after/request_id/waited
    client, _, _ = _client(
        monkeypatch,
        responses=[_http_error(429, {"X-Dashscope-Request-Id": "r1"})],
        max_retries=0)
    resp = client.complete(mode="rank_candidates", system_prompt="s",
                           user_payload="u")
    assert set(resp.http_attempts[0]) == {
        "attempt", "status", "retry_after_s", "request_id", "waited_s"}


# ---------------------------------------------------------------- 闸门


def test_gate_rpm_window_blocks_shared_instances(tmp_path):
    """RPM 滑窗:同一闸门目录的多个客户端实例共享窗口(跨进程语义的
    进程内模拟);窗口滑动后放行。"""
    g = FileRateGate(tmp_path / "gate", rpm=2, tpm=10**9, max_calls=100,
                     window_s=0.5)
    g.acquire()
    g.acquire()
    t0 = time_monotonic()
    g.acquire()  # 第 3 个请求必须等窗口滑动
    assert time_monotonic() - t0 >= 0.4
    _g2 = FileRateGate(tmp_path / "gate", rpm=2, tpm=10**9, max_calls=100,
                       window_s=0.5)  # 同目录新实例共享同一状态文件


def time_monotonic() -> float:
    import time

    return time.monotonic()


def test_gate_global_stop_and_budget(tmp_path):
    """全局停止与批次预算:状态文件持久,新实例同样被拒。"""
    gate_dir = tmp_path / "gate"
    g1 = FileRateGate(gate_dir, rpm=100, tpm=10**9, max_calls=3)
    for _ in range(3):
        g1.acquire()
    with pytest.raises(GateBudgetExhausted):
        g1.acquire()
    g2 = FileRateGate(gate_dir, rpm=100, tpm=10**9, max_calls=3)
    with pytest.raises(GateBudgetExhausted):
        g2.acquire()
    g2.record_response(forbidden=True, status=403, reason="http_403")
    assert g2.is_stopped()
    with pytest.raises(GateStopped):
        g2.acquire()


def test_gate_state_file_never_contains_credentials(tmp_path):
    gate = FileRateGate(tmp_path / "gate")
    gate.acquire()
    gate.record_response(status=200, usage={"total_tokens": 123})
    text = (tmp_path / "gate" / "gate.json").read_text()
    assert "sk-" not in text and "api_key" not in text


def test_gate_budget_exhausted_maps_to_structured_response(monkeypatch,
                                                           tmp_path):
    """闸门预算耗尽 → 结构化 LLMResponse(不是异常炸节点)。"""
    gate = FileRateGate(tmp_path / "gate", max_calls=0)
    client, calls, _ = _client(monkeypatch, responses=[_ok_payload()],
                               gate=gate)
    resp = client.complete(mode="rank_candidates", system_prompt="s",
                           user_payload="u")
    assert resp.ok is False
    assert resp.error_kind == "batch_api_budget_exhausted"
    assert calls["n"] == 0


# ------------------------------------------------------- 跨进程(子进程)


_CROSS_PROC = """
import json, sys, time
sys.path.insert(0, {src!r})
from pathlib import Path
from pathway_v43.adapters.rate_gate import FileRateGate, GateStopped, \\
    GateBudgetExhausted

mode = sys.argv[1]
gate_dir = sys.argv[2]
out = Path(sys.argv[3])
gate = FileRateGate(gate_dir, rpm=int(sys.argv[4]), tpm=10**9,
                    max_calls=int(sys.argv[5]), window_s=0.8)
result = {{}}
try:
    if mode == "acquire2":
        gate.acquire(); gate.acquire()
        result = {{"ok": True}}
    elif mode == "acquire1":
        t0 = time.monotonic()
        gate.acquire()
        result = {{"ok": True, "waited": time.monotonic() - t0}}
    elif mode == "stop":
        gate.record_response(forbidden=True, status=403, reason="http_403")
        result = {{"ok": True}}
except Exception as exc:
    result = {{"ok": False, "type": type(exc).__name__}}
out.write_text(json.dumps(result))
"""


def test_gate_cross_process_rpm_and_stop(tmp_path):
    """子进程实测:两进程共享 RPM 滑窗;一进程置停止,另一进程被拒。"""
    src = Path(__file__).resolve().parents[1] / "src"
    script = tmp_path / "gp.py"
    script.write_text(_CROSS_PROC.format(src=str(src)))
    gate_dir = tmp_path / "gate"

    def run(mode, n):
        out = tmp_path / f"{mode}-{n}.json"
        subprocess.run(
            [sys.executable, str(script), mode, str(gate_dir), str(out),
             "2", "100"],
            check=True, capture_output=True,
            env={"OMP_NUM_THREADS": "1", "PATH": "/usr/bin:/bin"},
            timeout=60)
        return json.loads(out.read_text())

    r1 = run("acquire2", 1)   # 进程 A:占满 2 槽
    assert r1["ok"]
    r2 = run("acquire1", 2)   # 进程 B:第 3 槽必须等窗口滑动
    assert r2["ok"] and r2["waited"] >= 0.6, "跨进程 RPM 滑窗生效"
    r3 = run("stop", 3)
    assert r3["ok"]
    r4 = run("acquire1", 4)
    assert not r4["ok"] and r4["type"] == "GateStopped", \
        "跨进程全局停止生效"
