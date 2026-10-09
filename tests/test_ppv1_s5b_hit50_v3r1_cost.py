"""PPV1 S5b HIT50 v3 回修 S5B-V3-02 —— 批级金额硬帽:发送前原子预留
(正链复审 §4.2;60 CNY 帽消费公开实际发送链 worker→adapter→client→
gate,不只测独立 helper)。

合成控制清单(§4.2 逐条;全部假传输,零真实模型/零外部网络/零
花费;urllib 打桩或 localhost 假提供者):

1. 零/不足预算 ⇒ 零发送(urlopen 从未被调用);
2. 恰好额度(committed+bound == cap)⇒ 放行恰一次;
3. 已知超帽(结算后 committed > cap)⇒ 下次发送拒 + overrun 披露;
4. 双进程 barrier 抢最后额度 ⇒ 恰一进程成功(flock 原子性);
5. 未知 usage(200 无 usage/失败/超时)⇒ 预留全额保守保留;
6. 重试/崩溃恢复/幂等结算:每次 HTTP retry 先预留;429 无可靠未计费
   证据 ⇒ 保守保留不退(v3-R2 按 R1 复审 §4.3 裁定改口径;槽位释放/
   冷却/有界重试保持);孤儿(owner 死亡)只退在途槽位、金额保留;
   重复结算 no-op 不重退不重扣;
7. 配置坏/缺先于传输拒:闸门/批根/编排器三层;
8. 公开链端到端:worker_main(进程内,urllib 打桩)+ run_s5b_batch
   (子进程 worker → 真客户端 → localhost 假提供者)消费同一守卫;
   预算耗尽未作答题留分母(run 以 budget_limit 终态收口、run_error
   结构化披露);合法低费用请求照常完成;
9. 其余门保持:HTTP max_calls/在途门不受金额守卫影响;请求体携带
   冻结输出上限 max_tokens;身份块含 budget_guard(配置哈希可核)。
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.error
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pathway_v43.adapters.llm_client import (  # noqa: E402
    OpenAICompatibleClient,
)
from pathway_v43.adapters.rate_gate import (  # noqa: E402
    FileRateGate,
    GateBudgetExhausted,
    GateCostBudgetExhausted,
    GateCorrupt,
    normalize_cost_guard_config,
)
from pathway_v43.pollutant.real_model import (  # noqa: E402
    RealModelAdapter,
)
from pathway_v43.pollutant.s5b_orchestrator import (  # noqa: E402
    S5B_BUDGET_GUARD_FILE,
    S5B_DEFAULT_PROFILE_POLICY,
    S5B_ORCHESTRATOR_VERSION,
    S5bOrchestratorError,
    load_budget_guard,
    read_case,
    run_s5b_batch,
)
from pathway_v43.pollutant.s5b_worker import worker_main  # noqa: E402

from test_ppv1_s5b_runtime import (  # noqa: E402
    SYNTH_QUESTIONS,
    synth_pool_provider,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"

# ---- 合成价格/界(测试值;真实发车当日定稿) ----
CFG = {
    "schema": "s5b-budget-guard-1",
    "cap_cny": 0.02,
    "input_per_mtok": 0.8,
    "output_per_mtok": 2.8,
    "input_tokens_conservative_bound": 1000,
    "max_output_tokens": 2000,
    "currency": "CNY",
}
BOUND = 0.0064  # (1000*0.8 + 2000*2.8)/1e6
USAGE_FULL = {"prompt_tokens": 1000, "completion_tokens": 2000,
              "total_tokens": 3000}
USAGE_ACTUAL = 0.0064  # 恰好等于 bound(价格同构)


def _gate(tmp_path, *, cap=CFG["cap_cny"], **overrides) -> FileRateGate:
    cfg = dict(CFG)
    cfg["cap_cny"] = cap
    cfg.update(overrides)
    return FileRateGate(tmp_path / "gate", rpm=10 ** 9, tpm=10 ** 9,
                        max_calls=100, cost_guard=cfg)


def _client(monkeypatch, *, gate, responses, max_retries=4,
            request_params=None, calls=None):
    """urllib 打桩客户端(沿 test_rate_gate 模式;零网络)。"""
    if calls is None:
        calls = {"n": 0, "bodies": []}

    def fake_urlopen(req, timeout=None):
        idx = calls["n"]
        calls["n"] += 1
        calls["bodies"].append(json.loads(req.data.decode("utf-8")))
        out = responses[min(idx, len(responses) - 1)]
        if isinstance(out, Exception):
            raise out
        import io

        resp = io.BytesIO(json.dumps(out).encode("utf-8"))
        resp.status = 200
        resp.headers = {"X-Dashscope-Request-Id": "req-42"}
        return resp

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    def fake_sleep(_s):
        pass

    monkeypatch.setattr("pathway_v43.adapters.llm_client.time.sleep",
                        fake_sleep)
    client = OpenAICompatibleClient(
        base_url="https://llm.example/v1", api_key="sk-test", model="m",
        timeout_s=5, gate=gate, max_http_retries=max_retries,
        request_params=request_params)
    return client, calls


def _ok_payload(content='{"decision":"select"}',
                usage=USAGE_FULL) -> dict:
    return {"choices": [{"message": {"role": "assistant",
                                     "content": content}}],
            "usage": usage}


# ============================================================ 1-3 预算额度

def test_zero_insufficient_budget_zero_sends(monkeypatch, tmp_path) -> None:
    """控制 1:零/不足预算 ⇒ 零发送(cap < 单次保守上界 ⇒ acquire 拒,
    urlopen 从未被调;拒发计数机读;结构化失败 kind 机读)。"""
    gate = _gate(tmp_path, cap=BOUND / 2)  # 不足一次尝试
    client, calls = _client(monkeypatch, gate=gate,
                            responses=[_ok_payload()])
    resp = client.complete(mode="proposals", system_prompt="s",
                           user_payload="u")
    assert resp.ok is False
    assert resp.error_kind == "budget_cost_exhausted"
    assert resp.error_detail["kind"] == "cost_budget_exhausted"
    assert resp.error_detail["per_attempt_bound_cny"] == BOUND
    assert calls["n"] == 0, "余额不足必须先于传输(零 HTTP 发送)"
    snap = FileRateGate(tmp_path / "gate").cost_snapshot()
    assert snap["send_rejections"] == 1
    assert snap["reserved_cny"] == 0.0


def test_exact_last_budget_admitted_once(monkeypatch, tmp_path) -> None:
    """控制 2:恰好额度(committed == cap)⇒ 最后一次放行;下一次拒。
    用满额 usage 结算(committed == bound == cap)后,第二次 acquire
    被拒 —— 精确边界(浮点容差 1e-9 内不误拒)。"""
    gate = _gate(tmp_path, cap=BOUND)  # 恰好一次尝试
    client, calls = _client(monkeypatch, gate=gate,
                            responses=[_ok_payload(), _ok_payload()])
    first = client.complete(mode="proposals", system_prompt="s",
                            user_payload="u")
    assert first.ok is True and calls["n"] == 1
    snap = FileRateGate(tmp_path / "gate").cost_snapshot()
    assert snap["committed_cny"] == pytest.approx(BOUND, abs=1e-9)
    second = client.complete(mode="proposals", system_prompt="s",
                             user_payload="u")
    assert second.ok is False
    assert second.error_kind == "budget_cost_exhausted"
    assert calls["n"] == 1, "第二次不得再发送"


def test_known_over_cap_blocks_and_discloses_overrun(
        monkeypatch, tmp_path) -> None:
    """控制 3:已知超帽 —— 实际结算超过冻结保守界(实际输入 tokens
    > 输入保守界)⇒ committed > cap:不回滚已付事实,记录 overrun
    (机读),后续发送一律拒。"""
    gate = _gate(tmp_path, cap=BOUND)
    over_usage = {"prompt_tokens": 5000, "completion_tokens": 2000,
                  "total_tokens": 7000}  # 实际 0.0096 > bound 0.0064
    client, _ = _client(monkeypatch, gate=gate,
                        responses=[_ok_payload(usage=over_usage)])
    first = client.complete(mode="proposals", system_prompt="s",
                            user_payload="u")
    assert first.ok is True
    gate2 = FileRateGate(tmp_path / "gate")
    snap = gate2.cost_snapshot()
    assert snap["settled_cny"] == pytest.approx(0.0096, abs=1e-9)
    assert snap["overrun"] is not None
    assert snap["overrun"]["committed_cny"] > snap["cap_cny"]
    # 已知超帽 ⇒ 下次发送先拒(不自动升帽)
    client2, calls2 = _client(monkeypatch, gate=gate2,
                              responses=[_ok_payload()])
    resp = client2.complete(mode="proposals", system_prompt="s",
                            user_payload="u")
    assert resp.error_kind == "budget_cost_exhausted"
    assert calls2["n"] == 0


# ============================================================ 4 双进程竞争

_BARRIER_WORKER = """
import json, sys, time
sys.path.insert(0, {src!r})
from pathlib import Path
from pathway_v43.adapters.rate_gate import FileRateGate, \\
    GateCostBudgetExhausted

gate_dir, my_marker, other_marker, out_path = sys.argv[1:5]
gate = FileRateGate(gate_dir)
Path(my_marker).write_text("ready")
deadline = time.time() + 30
while not Path(other_marker).exists() and time.time() < deadline:
    time.sleep(0.01)
result = {{}}
try:
    acquired = gate.acquire()
    result = {{"ok": True, "placeholder_id": acquired["placeholder_id"]}}
except GateCostBudgetExhausted as exc:
    result = {{"ok": False, "type": "GateCostBudgetExhausted",
               "detail": exc.detail}}
Path(out_path).write_text(json.dumps(result))
"""


def test_two_process_barrier_last_budget(tmp_path) -> None:
    """控制 4:双进程 barrier 抢最后额度 —— 预置一个未结算占用后剩余
    额度恰容一次尝试;两进程同时(互相见 marker 后)acquire ⇒ 恰一
    成功一拒(flock 临界区内原子预留),committed 不超帽。"""
    gate = _gate(tmp_path, cap=BOUND * 2)
    seeded = gate.acquire()
    gate.record_response(status=500, placeholder_id=seeded["placeholder_id"])
    # committed = BOUND(未结算);剩余恰容一次尝试
    gate_dir = tmp_path / "gate"
    script = tmp_path / "barrier.py"
    script.write_text(_BARRIER_WORKER.format(src=str(SRC)))
    env = {"OMP_NUM_THREADS": "1", "PATH": os.environ.get("PATH", "")}
    procs = []
    for name in ("A", "B"):
        out = tmp_path / f"barrier-{name}.json"
        procs.append((name, out, subprocess.Popen(
            [sys.executable, str(script), str(gate_dir),
             str(tmp_path / f"marker-{name}.json"),
             str(tmp_path / f"marker-{'B' if name == 'A' else 'A'}.json"),
             str(out)],
            env=env, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL)))
    results = {}
    for name, out, proc in procs:
        assert proc.wait(timeout=60) == 0
        results[name] = json.loads(out.read_text())
    winners = [n for n, r in results.items() if r["ok"]]
    losers = [n for n, r in results.items() if not r["ok"]]
    assert len(winners) == 1 and len(losers) == 1, results
    assert results[losers[0]]["type"] == "GateCostBudgetExhausted"
    gate2 = FileRateGate(gate_dir)
    snap = gate2.cost_snapshot()
    assert snap["committed_cny"] == pytest.approx(
        BOUND * 2, abs=1e-9)  # 未结算 1 + 在途/结算 1,恰在帽上
    assert snap["send_rejections"] == 1
    assert snap["settled_cny"] + snap["unsettled_cny"] \
        + snap["reserved_cny"] <= snap["cap_cny"] + 1e-9


# ============================================================ 5-6 未知/恢复

def test_unknown_usage_reservation_kept(monkeypatch, tmp_path) -> None:
    """控制 5:未知 usage(200 响应无 usage)⇒ 预留全额保守保留为
    未结算借记(committed 计入);失败/超时同语义。"""
    gate = _gate(tmp_path, cap=BOUND * 3)
    client, calls = _client(
        monkeypatch, gate=gate,
        responses=[_ok_payload(usage={}),
                   _ok_payload(usage={}),
                   _ok_payload(usage={})])
    assert client.complete(mode="proposals", system_prompt="s",
                           user_payload="u").ok
    assert client.complete(mode="proposals", system_prompt="s",
                           user_payload="u").ok
    snap = FileRateGate(tmp_path / "gate").cost_snapshot()
    assert snap["unsettled_cny"] == pytest.approx(BOUND * 2, abs=1e-9)
    assert snap["reserved_cny"] == 0.0
    # 两次未知占用 + 第三次预留 = 3*BOUND ⇒ 超帽(3*BOUND > 3*BOUND
    # 不成立,恰等;再无余额 —— 第三个请求在恰等时放行,结算后无
    # 余额):直接验证下一次 acquire 拒
    third = client.complete(mode="proposals", system_prompt="s",
                            user_payload="u")
    assert third.ok is True  # 恰好额度放行(控制 2 边界)
    fourth = client.complete(mode="proposals", system_prompt="s",
                             user_payload="u")
    assert fourth.error_kind == "budget_cost_exhausted"
    assert calls["n"] == 3


def test_http_retry_each_attempt_reserves_429_kept_conservatively(
        monkeypatch, tmp_path) -> None:
    """控制 6a(v3-R2 按 R1 复审 §4.3 改口径):HTTP retry 同样先
    预留 —— 每次尝试各绑定一个预留(reservations 逐尝试留痕);显式
    429 无可靠未计费证据 ⇒ 预留全额保守保留为未结算借记(槽位释放/
    冷却/有界重试照常);余额内重试可继续;余额耗尽先于重试拒。"""
    gate = _gate(tmp_path, cap=BOUND * 3)  # 恰容 2 次 429 保留 + 1 成功
    four29 = urllib.error.HTTPError(
        "https://llm.example/v1/chat/completions", 429, "err",
        {"Retry-After": "0"}, __import__("io").BytesIO(b""))
    client, calls = _client(
        monkeypatch, gate=gate,
        responses=[four29, four29, _ok_payload()], max_retries=4)
    resp = client.complete(mode="proposals", system_prompt="s",
                           user_payload="u")
    assert resp.ok is True
    assert calls["n"] == 3, "429 退避后重试到达成功响应"
    state = json.loads((tmp_path / "gate" / "gate.json").read_text())
    reservations = state["cost"]["reservations"]
    # 每次尝试(含 retry)各自原子预留:3 条留痕
    assert len(reservations) == 3
    states = sorted(e["state"] for e in reservations.values())
    # 429 保守保留(不退);成功尝试按完整 usage 结算
    assert states == ["settled", "unsettled", "unsettled"]
    snap = FileRateGate(tmp_path / "gate").cost_snapshot()
    assert snap["settled_cny"] == pytest.approx(USAGE_ACTUAL, abs=1e-9)
    assert snap["unsettled_cny"] == pytest.approx(BOUND * 2, abs=1e-9)
    assert snap["reserved_cny"] == 0.0
    # 429 冷却/槽位释放保持(计数机读)
    assert state["total_429"] == 2
    assert state["in_flight"] == 0
    # committed = 2 未知 + 1 结算 = 3*BOUND = 帽 ⇒ 重试/新发送先拒
    fourth = client.complete(mode="proposals", system_prompt="s",
                             user_payload="u")
    assert fourth.error_kind == "budget_cost_exhausted"
    assert calls["n"] == 3, "余额不足必须先于重试传输拒"


def test_failure_and_timeout_keep_full_bound(monkeypatch, tmp_path) -> None:
    """控制 6b:失败(4xx/5xx)/超时 ⇒ 预留全额保守保留(可能已
    付费不释放);与 429 退回形成对照。"""
    err500 = urllib.error.HTTPError(
        "https://llm.example/v1/chat/completions", 500, "err", {},
        __import__("io").BytesIO(b""))
    gate = _gate(tmp_path, cap=BOUND * 2)
    client, _ = _client(monkeypatch, gate=gate, responses=[err500],
                        max_retries=0)
    resp = client.complete(mode="proposals", system_prompt="s",
                           user_payload="u")
    assert resp.error_kind == "transport_error"
    snap = FileRateGate(tmp_path / "gate").cost_snapshot()
    assert snap["unsettled_cny"] == pytest.approx(BOUND, abs=1e-9)
    # 超时(URLError(TimeoutError))同语义
    gate2_dir = tmp_path / "gate2"
    cfg = dict(CFG)
    FileRateGate(gate2_dir, rpm=10 ** 9, tpm=10 ** 9, max_calls=100,
                 cost_guard=cfg)
    gate2 = FileRateGate(gate2_dir)
    client2, _ = _client(
        monkeypatch, gate=gate2,
        responses=[urllib.error.URLError(TimeoutError())],
        max_retries=0)
    resp2 = client2.complete(mode="proposals", system_prompt="s",
                             user_payload="u")
    assert resp2.error_kind == "timeout"
    snap2 = FileRateGate(gate2_dir).cost_snapshot()
    assert snap2["unsettled_cny"] == pytest.approx(BOUND, abs=1e-9)


_CRASH_WORKER = """
import json, sys, time
sys.path.insert(0, {src!r})
from pathlib import Path
from pathway_v43.adapters.rate_gate import FileRateGate

mode = sys.argv[1]
gate_dir, out_path = sys.argv[2], sys.argv[3]
gate = FileRateGate(gate_dir)
acquired = gate.acquire()
if mode == "settle":
    gate.record_response(
        status=200, usage={{"prompt_tokens": 1000,
                            "completion_tokens": 2000,
                            "total_tokens": 3000}},
        placeholder_id=acquired["placeholder_id"])
Path(out_path).write_text(json.dumps(
    {{"placeholder_id": acquired["placeholder_id"], "mode": mode}}))
time.sleep(120)
"""


def test_crash_recovery_reclaim_keeps_money(tmp_path) -> None:
    """控制 6c:崩溃恢复 —— worker acquire 后被 SIGKILL(孤儿):
    父协调者 reclaim_dead_placeholders 只回收在途占位,**金额预留
    保守保留为未结算**(可能已发送付费,不凭空退款)。"""
    gate = _gate(tmp_path, cap=BOUND * 3)
    script = tmp_path / "crash.py"
    script.write_text(_CRASH_WORKER.format(src=str(SRC)))
    out = tmp_path / "crash-out.json"
    env = {"OMP_NUM_THREADS": "1", "PATH": os.environ.get("PATH", "")}
    proc = subprocess.Popen(
        [sys.executable, str(script), "reserve",
         str(tmp_path / "gate"), str(out)],
        env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(200):  # 最多 20s 等预留落盘
            if out.exists():
                break
            time.sleep(0.1)
        assert out.exists(), "子进程未能完成原子预留"
    finally:
        proc.kill()
        proc.wait(timeout=30)
    gate2 = FileRateGate(tmp_path / "gate")
    before = gate2.cost_snapshot()
    assert before["reserved_cny"] == pytest.approx(BOUND, abs=1e-9)
    summary = gate2.reclaim_dead_placeholders()
    assert summary["reclaimed"] == 1
    assert summary["in_flight"] == 0  # 在途槽位回收
    after = gate2.cost_snapshot()
    # 金额不释放:预留 → 未结算借记(committed 不变)
    assert after["reserved_cny"] == 0.0
    assert after["unsettled_cny"] == pytest.approx(BOUND, abs=1e-9)
    assert after["committed_cny"] == pytest.approx(
        before["committed_cny"], abs=1e-9)


def test_settled_then_dead_owner_reclaim_no_double_count(
        tmp_path) -> None:
    """控制 6d:幂等结算不重退不重扣 —— 先结算后 owner 死亡回收:
    settled 状态不受 reclaim 影响(不重扣);重复 record_response
    no-op(不重退差值)。"""
    gate = _gate(tmp_path, cap=BOUND * 3)
    script = tmp_path / "crash.py"
    script.write_text(_CRASH_WORKER.format(src=str(SRC)))
    out = tmp_path / "settle-out.json"
    env = {"OMP_NUM_THREADS": "1", "PATH": os.environ.get("PATH", "")}
    proc = subprocess.Popen(
        [sys.executable, str(script), "settle",
         str(tmp_path / "gate"), str(out)],
        env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(200):
            if out.exists():
                break
            time.sleep(0.1)
        assert out.exists()
    finally:
        proc.kill()
        proc.wait(timeout=30)
    placeholder = json.loads(out.read_text())["placeholder_id"]
    gate2 = FileRateGate(tmp_path / "gate")
    snap = gate2.cost_snapshot()
    assert snap["settled_cny"] == pytest.approx(USAGE_ACTUAL, abs=1e-9)
    # 重复结算(同占位同 usage)⇒ no-op,不重退不重扣
    gate2.record_response(status=200, usage=USAGE_FULL,
                          placeholder_id=placeholder)
    gate2.record_response(status=200, usage=USAGE_FULL,
                          placeholder_id=placeholder)
    snap2 = gate2.cost_snapshot()
    assert snap2["settled_cny"] == pytest.approx(USAGE_ACTUAL, abs=1e-9)
    # owner 已死 ⇒ reclaim 不触碰 settled(金额既不退也不重扣)
    gate2.reclaim_dead_placeholders()
    snap3 = gate2.cost_snapshot()
    assert snap3["settled_cny"] == pytest.approx(USAGE_ACTUAL, abs=1e-9)
    assert snap3["unsettled_cny"] == 0.0
    state = json.loads((tmp_path / "gate" / "gate.json").read_text())
    assert state["cost"]["reservations"][placeholder]["state"] == \
        "settled"


# ============================================================ 7 配置坏/缺

def test_corrupt_cost_config_refuses_before_transmission(
        monkeypatch, tmp_path) -> None:
    """控制 7a:闸门金额配置坏形状(状态文件被改坏)⇒ 发送前结构化拒
    (budget_config_invalid;urlopen 零调用;不清零既有计数)。"""
    gate = _gate(tmp_path)
    client, calls = _client(monkeypatch, gate=gate,
                            responses=[_ok_payload()])
    # 构造后破坏状态文件的 cost_guard 块(模拟坏配置/篡改)
    state_path = tmp_path / "gate" / "gate.json"
    state = json.loads(state_path.read_text())
    state["cost_guard"].pop("cap_cny")
    state_path.write_text(json.dumps(state))
    resp = client.complete(mode="proposals", system_prompt="s",
                           user_payload="u")
    assert resp.ok is False
    assert resp.error_kind == "budget_config_invalid"
    assert calls["n"] == 0


def test_orchestrator_real_batch_requires_budget_config(tmp_path) -> None:
    """控制 7b:real 批缺/坏 budget_guard.json ⇒ 发车先拒(先于任何
    worker 派发:无 cases/无 orchestration.json);坏形状同拒。"""
    from pathway_v43.pollutant.s5b_builder import build_question_batch

    questions = tmp_path / "q.jsonl"
    questions.write_text(json.dumps(SYNTH_QUESTIONS[0]) + "\n",
                         encoding="utf-8")
    batch_root = tmp_path / "batch"
    build_question_batch(
        questions, batch_root, batch_tag="costguard",
        pool_provider=synth_pool_provider, provider_kind="real",
        synthetic_review=True)
    # 缺配置
    with pytest.raises(S5bOrchestratorError) as excinfo:
        run_s5b_batch(batch_root, runs_root=tmp_path / "runs", workers=1,
                      poll_s=0.1)
    assert excinfo.value.detail["kind"] == "s5b_budget_guard_missing"
    assert not (batch_root / "orchestration.json").exists()
    assert not (batch_root / "cases").exists(), "先于 worker 派发"
    # 坏配置(数值字段缺)
    (batch_root / S5B_BUDGET_GUARD_FILE).write_text(
        json.dumps({"schema": "s5b-budget-guard-1", "cap_cny": -1}),
        encoding="utf-8")
    with pytest.raises(S5bOrchestratorError) as excinfo2:
        run_s5b_batch(batch_root, runs_root=tmp_path / "runs", workers=1,
                      poll_s=0.1)
    assert excinfo2.value.detail["kind"] == "s5b_budget_guard_invalid"
    # 非法 currency/schema 同拒
    for bad in ({"cap_cny": 1, "input_per_mtok": 1,
                 "output_per_mtok": 1,
                 "input_tokens_conservative_bound": 1,
                 "max_output_tokens": 1, "currency": "USD"},
                {"cap_cny": 1, "input_per_mtok": 1, "output_per_mtok": 1,
                 "input_tokens_conservative_bound": 1,
                 "max_output_tokens": 1, "schema": "old-schema"}):
        (batch_root / S5B_BUDGET_GUARD_FILE).write_text(
            json.dumps(bad), encoding="utf-8")
        with pytest.raises(S5bOrchestratorError) as excinfo3:
            run_s5b_batch(batch_root, runs_root=tmp_path / "runs",
                          workers=1, poll_s=0.1)
        assert excinfo3.value.detail["kind"] == "s5b_budget_guard_invalid"


def test_orchestrator_budget_frozen_and_change_rejected(tmp_path) -> None:
    """控制 7c:金额配置冻结进 orchestration.json;同批根改值 ⇒
    s5b_orchestration_conflict(先于 worker 派发;不自动升帽)。"""
    from pathway_v43.pollutant.s5b_builder import build_question_batch

    questions = tmp_path / "q.jsonl"
    questions.write_text(json.dumps(SYNTH_QUESTIONS[0]) + "\n",
                         encoding="utf-8")
    batch_root = tmp_path / "batch"
    build_question_batch(
        questions, batch_root, batch_tag="frozenbudget",
        pool_provider=synth_pool_provider, provider_kind="scripted",
        synthetic_review=True)
    config = normalize_cost_guard_config(dict(CFG))
    (batch_root / S5B_BUDGET_GUARD_FILE).write_text(
        json.dumps({**CFG, **{k: config[k] for k in (
            "per_attempt_bound_cny", "config_sha256",
            "usage_split_policy")}}), encoding="utf-8")
    runs_root = tmp_path / "runs"
    # 预写一份不同预算的冻结副本 ⇒ 同批根改值被拒
    existing = {
        "orchestrator_version": S5B_ORCHESTRATOR_VERSION,
        "workers": 1, "max_in_flight": 40, "gate_rpm": 180,
        "gate_tpm": 2_700_000, "gate_max_calls": 50,
        "budget_guard": normalize_cost_guard_config(
            {**CFG, "cap_cny": 999.0}),
        "profile_policy": S5B_DEFAULT_PROFILE_POLICY,
        "runs_root": str(runs_root),
        "frozen_at": "2026-10-10T00:00:00",
    }
    (batch_root / "orchestration.json").write_text(
        json.dumps(existing), encoding="utf-8")
    with pytest.raises(S5bOrchestratorError) as excinfo:
        run_s5b_batch(batch_root, runs_root=runs_root, workers=1,
                      gate_max_calls=50, poll_s=0.1)
    assert excinfo.value.detail["kind"] == "s5b_orchestration_conflict"


def test_cli_budget_writes_machine_config(tmp_path, capsys) -> None:
    """CLI budget:机器配置落盘(派生 bound/config_sha256 可核验);
    同值幂等;改值拒(不自动升帽);同价 price_snapshot 单一价格源。"""
    from pathway_v43.pollutant.s5b_cli import main as cli_main

    batch_root = tmp_path / "batch"
    batch_root.mkdir()
    rc = cli_main(["budget", "--batch-root", str(batch_root),
                   "--input-per-mtok", "0.8", "--output-per-mtok", "2.8",
                   "--cap-cny", "60", "--input-tokens-bound", "1000",
                   "--max-output-tokens", "2000"])
    assert rc == 0
    payload = json.loads(
        (batch_root / S5B_BUDGET_GUARD_FILE).read_text())
    assert payload["cap_cny"] == 60.0
    assert payload["config_sha256"] == \
        normalize_cost_guard_config(
            {**CFG, "cap_cny": 60.0})["config_sha256"]
    assert (batch_root / "price_snapshot.json").is_file()
    # 同值幂等
    rc2 = cli_main(["budget", "--batch-root", str(batch_root),
                    "--input-per-mtok", "0.8", "--output-per-mtok", "2.8",
                    "--cap-cny", "60", "--input-tokens-bound", "1000",
                    "--max-output-tokens", "2000"])
    assert rc2 == 0
    # 改值(升帽)拒
    rc3 = cli_main(["budget", "--batch-root", str(batch_root),
                    "--input-per-mtok", "0.8", "--output-per-mtok", "2.8",
                    "--cap-cny", "120", "--input-tokens-bound", "1000",
                    "--max-output-tokens", "2000"])
    assert rc3 == 3
    # load_budget_guard 与 CLI 同源判据
    loaded = load_budget_guard(batch_root)
    assert loaded["config_sha256"] == payload["config_sha256"]


# ============================================================ 9 客户端/身份

def test_request_body_carries_frozen_output_cap(monkeypatch, tmp_path) -> None:
    """输出上限冻结进请求体(max_tokens = 冻结 max_output_tokens);
    显式 request_params 携带不同 max_tokens ⇒ 冲突先拒(单一事实源)。"""
    gate = _gate(tmp_path)
    client, calls = _client(monkeypatch, gate=gate,
                            responses=[_ok_payload()])
    resp = client.complete(mode="proposals", system_prompt="s",
                           user_payload="u")
    assert resp.ok
    assert calls["bodies"][0]["max_tokens"] == 2000
    # 冲突:显式 max_tokens ≠ 冻结输出上限 ⇒ 先于传输拒
    conflicting, calls2 = _client(
        monkeypatch, gate=FileRateGate(tmp_path / "gate"),
        responses=[_ok_payload()], request_params={"max_tokens": 999})
    resp2 = conflicting.complete(mode="proposals", system_prompt="s",
                                 user_payload="u")
    assert resp2.error_kind == "budget_output_cap_conflict"
    assert calls2["n"] == 0


def test_identity_block_includes_budget_guard(tmp_path) -> None:
    """身份块:金额守卫配置入 run 身份(帽/价格/界/输出上限/配置
    哈希;resume 逐字段核对的机器配置凭证);无密钥泄漏。"""
    gate = _gate(tmp_path)
    client = OpenAICompatibleClient(
        base_url="https://llm.example/v1", api_key="sk-secret",
        model="m", gate=gate)
    adapter = RealModelAdapter(client)
    block = adapter.identity_block()
    guard = block["budget_guard"]
    assert guard["cap_cny"] == CFG["cap_cny"]
    assert guard["max_output_tokens"] == CFG["max_output_tokens"]
    assert guard["input_tokens_conservative_bound"] == 1000
    assert guard["per_attempt_bound_cny"] == BOUND
    assert guard["config_sha256"] == \
        normalize_cost_guard_config(dict(CFG))["config_sha256"]
    assert "sk-secret" not in json.dumps(block)


def test_other_gates_untouched_with_cost_guard(tmp_path) -> None:
    """其余门保持:HTTP 请求数预算(max_calls)独立生效(与金额门
    分开的结构化异常);在途上限语义不变。"""
    gate = FileRateGate(tmp_path / "gate", rpm=10 ** 9, tpm=10 ** 9,
                        max_calls=1, cost_guard=dict(CFG))
    acquired = gate.acquire()
    with pytest.raises(GateBudgetExhausted):
        gate.acquire()  # 请求数门先于金额语义拒(金额仍充足)
    # 金额预留随第一次 acquire 正常落盘
    snap = FileRateGate(tmp_path / "gate").cost_snapshot()
    assert snap["reserved_cny"] == pytest.approx(BOUND, abs=1e-9)
    gate.record_response(status=200, usage=USAGE_FULL,
                         placeholder_id=acquired["placeholder_id"])


# ============================================================ 8 端到端

def _write_budget(batch_root: Path, *, cap: float) -> dict:
    config = normalize_cost_guard_config({
        "cap_cny": cap, "input_per_mtok": 0.8, "output_per_mtok": 2.8,
        "input_tokens_conservative_bound": 10_000,
        "max_output_tokens": 20_000, "currency": "CNY"})
    payload = {
        "cap_cny": cap, "input_per_mtok": 0.8, "output_per_mtok": 2.8,
        "input_tokens_conservative_bound": 10_000,
        "max_output_tokens": 20_000, "currency": "CNY",
        "per_attempt_bound_cny": config["per_attempt_bound_cny"],
        "config_sha256": config["config_sha256"],
        "usage_split_policy": config["usage_split_policy"],
        "schema": "s5b-budget-guard-1",
    }
    (batch_root / S5B_BUDGET_GUARD_FILE).write_text(
        json.dumps(payload), encoding="utf-8")
    return config


def _proposals_response(request_body: dict, *, usage: dict) -> dict:
    """假提供者响应:按请求体载荷解析冻结池,提案首个池条目
    (first_pool 确定性剧本;与 scripted 桩同一解析器消费)。"""
    user_content = request_body["messages"][1]["content"]
    try:
        payload = json.loads(user_content)
        pool = payload.get("pool_hypotheses") or []
    except (ValueError, TypeError):
        pool = []
    if pool:
        first = str(pool[0].get("hypothesis_id") or "")
        content = json.dumps(
            {"proposals": [{"hypothesis_id": first}],
             "rank_hypotheses": [first]}, ensure_ascii=False)
    else:
        content = '{"proposals": [], "rank_hypotheses": []}'
    return {"choices": [{"message": {"role": "assistant",
                                     "content": content}}],
            "usage": usage}


E2E_USAGE = {"prompt_tokens": 900, "completion_tokens": 1000,
             "total_tokens": 1900}
# (900*0.8 + 1000*2.8)/1e6
E2E_ACTUAL = 0.00352


def test_worker_real_client_fake_transport_end_to_end(
        monkeypatch, tmp_path) -> None:
    """控制 8a:公开 worker 入口端到端(进程内)—— worker_main →
    RealModelAdapter(真实客户端)→ OpenAICompatibleClient → 批级
    闸门(金额原子预留)→ urllib 假传输 → 结算;case 终态 completed、
    闸门结算 = 冻结价 × 假 usage、请求体携带冻结输出上限。"""
    from pathway_v43.pollutant.s5b_builder import build_question_batch

    questions = tmp_path / "q.jsonl"
    questions.write_text(json.dumps(SYNTH_QUESTIONS[0]) + "\n",
                         encoding="utf-8")
    batch_root = tmp_path / "batch"
    build_question_batch(
        questions, batch_root, batch_tag="e2e-real",
        pool_provider=synth_pool_provider, provider_kind="real",
        synthetic_review=True)
    config = _write_budget(batch_root, cap=0.5)
    (batch_root / "profile_policy.json").write_text(
        json.dumps(S5B_DEFAULT_PROFILE_POLICY), encoding="utf-8")
    # 协调者侧闸门(冻结金额配置;worker 经 env 装载同一状态文件)
    FileRateGate(batch_root / "gate", rpm=10 ** 9, tpm=10 ** 9,
                 max_calls=50, cost_guard=config)
    qid = "SYNTH-Q001"
    runs_root = tmp_path / "runs"
    for key in ("V43_LLM_BASE_URL", "V43_LLM_API_KEY", "V43_LLM_MODEL"):
        monkeypatch.setenv(key, {"V43_LLM_BASE_URL":
                                 "https://fake.example/v1",
                                 "V43_LLM_API_KEY": "sk-e2e-test",
                                 "V43_LLM_MODEL": "e2e-test-model"}[key])
    monkeypatch.setenv("V43_LLM_RATE_GATE", str(batch_root / "gate"))
    monkeypatch.delenv("S5B_MODEL_STUB_SCRIPT", raising=False)
    calls = {"n": 0, "bodies": []}

    def fake_urlopen(req, timeout=None):
        calls["n"] += 1
        body = json.loads(req.data.decode("utf-8"))
        calls["bodies"].append(body)
        import io

        resp = io.BytesIO(json.dumps(
            _proposals_response(body, usage=E2E_USAGE)).encode("utf-8"))
        resp.status = 200
        resp.headers = {"X-Dashscope-Request-Id": "req-e2e-1"}
        return resp

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    rc = worker_main(["--batch-root", str(batch_root),
                      "--runs-root", str(runs_root), "--qid", qid])
    assert rc == 0
    case = read_case(batch_root, qid)
    assert case is not None and case["status"] == "completed", case
    assert case["export_digest"]
    assert case["model_calls"] == 1
    # 请求体携带冻结输出上限;一次发送;金额按冻结价结算
    assert calls["n"] == 1
    assert calls["bodies"][0]["max_tokens"] == 20_000
    gate = FileRateGate(batch_root / "gate")
    snap = gate.cost_snapshot()
    assert snap["settled_cny"] == pytest.approx(E2E_ACTUAL, abs=1e-9)
    assert snap["committed_cny"] <= snap["cap_cny"] + 1e-9
    assert snap["send_rejections"] == 0
    # 身份块含 budget_guard(机器配置入 run 身份)
    identity = json.loads(
        (runs_root / json.loads(
            (batch_root / "run_inputs" / f"{qid}.json").read_text())
         ["run_id"] / "run_identity.json").read_text())
    guard = (identity.get("prediction") or {}).get("budget_guard") or {}
    assert guard.get("config_sha256") == config["config_sha256"]


def test_worker_insufficient_budget_stays_in_denominator(
        monkeypatch, tmp_path) -> None:
    """控制 8b:预算不足 ⇒ 未作答题留分母 —— worker 公开入口端到端:
    零 HTTP 发送(假传输计数 0),case 终态 failed(结构化失败因),
    批汇总分母不剔题。"""
    from pathway_v43.pollutant.s5b_builder import build_question_batch

    questions = tmp_path / "q.jsonl"
    questions.write_text(json.dumps(SYNTH_QUESTIONS[0]) + "\n",
                         encoding="utf-8")
    batch_root = tmp_path / "batch"
    build_question_batch(
        questions, batch_root, batch_tag="e2e-broke",
        pool_provider=synth_pool_provider, provider_kind="real",
        synthetic_review=True)
    config = _write_budget(batch_root, cap=0.000001)  # 不足一次尝试
    (batch_root / "profile_policy.json").write_text(
        json.dumps(S5B_DEFAULT_PROFILE_POLICY), encoding="utf-8")
    FileRateGate(batch_root / "gate", rpm=10 ** 9, tpm=10 ** 9,
                 max_calls=50, cost_guard=config)
    qid = "SYNTH-Q001"
    runs_root = tmp_path / "runs"
    for key, value in (("V43_LLM_BASE_URL", "https://fake.example/v1"),
                       ("V43_LLM_API_KEY", "sk-e2e-test"),
                       ("V43_LLM_MODEL", "e2e-test-model")):
        monkeypatch.setenv(key, value)
    monkeypatch.setenv("V43_LLM_RATE_GATE", str(batch_root / "gate"))
    monkeypatch.delenv("S5B_MODEL_STUB_SCRIPT", raising=False)
    calls = {"n": 0}

    def fake_urlopen(req, timeout=None):  # pragma: no cover —— 不应到达
        calls["n"] += 1
        raise AssertionError("预算不足不得到达传输层")

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    rc = worker_main(["--batch-root", str(batch_root),
                      "--runs-root", str(runs_root), "--qid", qid])
    # 运行级语义:预算耗尽先于传输 ⇒ run 以 stop_reason=budget_limit
    # 终态收口(失败题留分母:case 落盘、请求登记为 failed 占额、
    # run_error 结构化披露 budget_cost_exhausted;零 HTTP 发送)
    assert rc == 0
    case = read_case(batch_root, qid)
    assert case is not None and case["status"] == "completed", case
    assert case["stop_reason"] == "budget_limit"
    run_error = json.dumps(case.get("run_error") or {},
                           ensure_ascii=False)
    assert "budget_cost_exhausted" in run_error
    assert calls["n"] == 0, "预算不足不得到达传输层"
    snap = FileRateGate(batch_root / "gate").cost_snapshot()
    assert snap["send_rejections"] >= 1
    assert snap["reserved_cny"] == 0.0
    assert snap["settled_cny"] == 0.0
    # worker 旁路守卫核对负控:无闸门 ⇒ budget_guard_missing(零发送)
    batch_root2 = tmp_path / "batch2"
    build_question_batch(
        questions, batch_root2, batch_tag="e2e-nogate",
        pool_provider=synth_pool_provider, provider_kind="real",
        synthetic_review=True)
    _write_budget(batch_root2, cap=0.5)
    (batch_root2 / "profile_policy.json").write_text(
        json.dumps(S5B_DEFAULT_PROFILE_POLICY), encoding="utf-8")
    monkeypatch.setenv("V43_LLM_RATE_GATE", str(tmp_path / "no-such-gate"))
    rc2 = worker_main(["--batch-root", str(batch_root2),
                       "--runs-root", str(tmp_path / "runs2"),
                       "--qid", qid])
    assert rc2 == 5
    case2 = read_case(batch_root2, qid)
    assert case2["status"] == "failed"
    assert case2["failure_kind"] == "budget_guard_missing"
    assert calls["n"] == 0


def _make_fake_provider_server(counter: dict):
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    usage = dict(E2E_USAGE)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):  # pragma: no cover —— 静默
            pass

        def do_POST(self):  # noqa: N802 —— http.server 约定
            length = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(length) or b"{}")
            counter["n"] += 1
            counter["bodies"].append(body)
            counter["max_tokens"].append(body.get("max_tokens"))
            payload = json.dumps(
                _proposals_response(body, usage=usage)).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    return server


def test_orchestrator_subprocess_real_chain_end_to_end(
        monkeypatch, tmp_path) -> None:
    """控制 8c:公开实际发送链全链端到端(子进程)—— run_s5b_batch
    (协调者冻结预算配置入 orchestration.json 与闸门)→ worker 子进程
    → RealModelAdapter(真实客户端)→ 闸门原子预留 → urllib →
    localhost 假提供者(127.0.0.1;零外部网络/零花费)。两题完成、
    金额按冻结价结算、批报告带 cost_guard 账本;预算帽不越。"""
    from pathway_v43.pollutant.s5b_builder import build_question_batch

    counter = {"n": 0, "bodies": [], "max_tokens": []}
    server = _make_fake_provider_server(counter)
    port = server.server_address[1]
    import threading

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        questions = tmp_path / "q.jsonl"
        questions.write_text(
            "\n".join(json.dumps(q) for q in SYNTH_QUESTIONS[:2]) + "\n",
            encoding="utf-8")
        batch_root = tmp_path / "batch"
        build_question_batch(
            questions, batch_root, batch_tag="e2e-subproc",
            pool_provider=synth_pool_provider, provider_kind="real",
            synthetic_review=True)
        _write_budget(batch_root, cap=0.5)
        runs_root = tmp_path / "runs"
        for key, value in (
                ("V43_LLM_BASE_URL", f"http://127.0.0.1:{port}/v1"),
                ("V43_LLM_API_KEY", "sk-subproc-test"),
                ("V43_LLM_MODEL", "subproc-test-model")):
            monkeypatch.setenv(key, value)
        monkeypatch.delenv("S5B_MODEL_STUB_SCRIPT", raising=False)
        report = run_s5b_batch(
            batch_root, runs_root=runs_root, workers=2,
            gate_max_calls=50, poll_s=0.2)
        assert report["n_completed"] == 2, report
        assert report["n_failed"] == 0 and report["n_pending"] == 0
        # 两次真实 HTTP 尝试(一题一 logical),请求体带冻结输出上限
        assert counter["n"] == 2, counter
        assert counter["max_tokens"] == [20_000, 20_000]
        # 冻结副本含金额配置(机器配置入 orchestration.json)
        frozen = json.loads(
            (batch_root / "orchestration.json").read_text())
        assert frozen["budget_guard"]["cap_cny"] == 0.5
        assert frozen["budget_guard"]["max_output_tokens"] == 20_000
        # 闸门账本:结算 = 冻结价 × 假 usage;committed ≤ 帽
        gate = FileRateGate(batch_root / "gate")
        snap = gate.cost_snapshot()
        assert snap["settled_cny"] == pytest.approx(
            E2E_ACTUAL * 2, abs=1e-9)
        assert snap["committed_cny"] <= snap["cap_cny"] + 1e-9
        assert snap["send_rejections"] == 0
        assert snap["unsettled_cny"] == 0.0
        # 批报告披露 cost_guard 账本
        assert report["gate"]["cost_guard"]["enabled"] is True
        assert report["gate"]["cost_guard"]["settled_cny"] == \
            pytest.approx(E2E_ACTUAL * 2, abs=1e-9)
        # 判分侧数据_scope 严格门与本轮无关(不在此断言判分)
    finally:
        server.shutdown()
        server.server_close()
