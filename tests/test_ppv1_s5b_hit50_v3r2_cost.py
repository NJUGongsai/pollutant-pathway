"""PPV1 S5b HIT50 v3 回修 R2 —— S5B-V3-02 三个已证残余子案
(R1 正链复审 §4.2/4.3/4.4 + §8;基线 b502b75)。S5B-V3-01 已关闭不回退。

**残余 A(usage 完整性)**:rate_gate._cost_of_usage 缺轴不 `or 0` 补零
—— 完整合法拆分(含显式 0)结算、合法可核总计走既有保守总计口径、
只知一轴且无完整总计 ⇒ 不可计(预留按未知保守保留,不退)。公开
client/worker 的 prompt-only/output-only/空/完整/显式 0/total-only/
重复回执逐案;部分 usage 不得靠退款挤出第二次发送、合法低费用仍可发。

**残余 B(429 保守保留)**:无 usage/未计费依据的 429 归未知保守借记
(全额保留);槽位释放/429 冷却/HTTP 有界重试/HTTP 数量门不退保持;
重试每次先预留、余额不足先拒;含 body usage 的 429 不得被无依据归零
(客户端不读错误体作为计费依据 ⇒ 闸门侧保守保留;闸门直收完整 usage
则按保守计费路径结算 —— 同源完整性判据)。

**残余 C(存储配置首消费)**:gate.json cost_guard 冻结块已有派生
bound/hash 须对照同源 core 重算(verify_stored_cost_guard);错/缺派生
值、错哈希 ⇒ 结构化拒、保全坏记录、零新预留/发送;acquire 临界区
校验并消费同一重算规范对象(不消费 raw stored 金额);builder 原始
core 派生入口(normalize_cost_guard_config)与 stored 恢复入口区分。
主审反例复现:批根合法 bound=.046938/帽=.001、stored bound 改
.000001 ⇒ 先拒零发送。

全部合成假传输(urllib 打桩/127.0.0.1 假提供者),零真实模型/零外部
网络/零花费;不认证真实账单或提供者计费政策。
"""

from __future__ import annotations

import json
import urllib.error
from pathlib import Path

import pytest

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pathway_v43.adapters.rate_gate import (  # noqa: E402
    FileRateGate,
    GateCorrupt,
    normalize_cost_guard_config,
    verify_stored_cost_guard,
)
from pathway_v43.pollutant.s5b_orchestrator import (  # noqa: E402
    S5B_BUDGET_GUARD_FILE,
    S5B_DEFAULT_PROFILE_POLICY,
)
from pathway_v43.pollutant.s5b_worker import worker_main  # noqa: E402

from test_ppv1_s5b_hit50_v3r1_cost import (  # noqa: E402
    BOUND,
    CFG,
    USAGE_ACTUAL,
    _client,
    _gate,
    _ok_payload,
    _proposals_response,
    _write_budget,
)
from test_ppv1_s5b_runtime import (  # noqa: E402
    SYNTH_QUESTIONS,
    synth_pool_provider,
)

REPO_ROOT = Path(__file__).resolve().parents[1]

# ====================================================== 残余 A:usage 完整性

# (标签, usage, 期望 settled_cny, 期望 unsettled_cny)
# CFG 价格:输入 0.8 / 输出 2.8 元/Mtok;BOUND=.0064
USAGE_MATRIX = [
    ("prompt_only", {"prompt_tokens": 900}, 0.0, BOUND),
    ("output_only", {"completion_tokens": 500}, 0.0, BOUND),
    ("empty", {}, 0.0, BOUND),
    ("complete", {"prompt_tokens": 900, "completion_tokens": 1000,
                  "total_tokens": 1900}, 0.00352, 0.0),
    ("explicit_zero_split", {"prompt_tokens": 0, "completion_tokens": 0,
                             "total_tokens": 0}, 0.0, 0.0),
    ("explicit_zero_output", {"prompt_tokens": 1000,
                              "completion_tokens": 0,
                              "total_tokens": 1000}, 0.0008, 0.0),
    ("total_only", {"total_tokens": 3000}, 0.0084, 0.0),
    # 一轴 + 可核总计(缺另一轴)⇒ 走保守总计口径,不按 input-only 结算
    ("prompt_plus_total", {"prompt_tokens": 900, "total_tokens": 1900},
     0.00532, 0.0),
    # 字段显式存在但类型坏/负数 ⇒ 该轴不可用 ⇒ 不可计(保守保留)
    ("negative_prompt", {"prompt_tokens": -5, "completion_tokens": 1000},
     0.0, BOUND),
    ("string_prompt", {"prompt_tokens": "900", "completion_tokens": 1000},
     0.0, BOUND),
    ("bool_prompt", {"prompt_tokens": True, "completion_tokens": 1000},
     0.0, BOUND),
]


@pytest.mark.parametrize("label,usage,settled,unsettled", USAGE_MATRIX)
def test_usage_completeness_matrix_client(
        monkeypatch, tmp_path, label, usage, settled, unsettled) -> None:
    """残余 A 逐案:client→gate 公开链 —— 缺轴不补 0。完整拆分(含
    显式 0)结算;total-only/一轴+可核总计走保守总计口径;一轴缺席且
    无完整总计、字段类型坏/负数/bool ⇒ 不可计,预留全额保守保留。"""
    gate = _gate(tmp_path, cap=BOUND * 3)
    client, calls = _client(monkeypatch, gate=gate,
                            responses=[_ok_payload(usage=usage)])
    resp = client.complete(mode="proposals", system_prompt="s",
                           user_payload="u")
    assert resp.ok is True and calls["n"] == 1
    snap = FileRateGate(tmp_path / "gate").cost_snapshot()
    assert snap["settled_cny"] == pytest.approx(settled, abs=1e-9), label
    assert snap["unsettled_cny"] == pytest.approx(unsettled, abs=1e-9), label
    assert snap["reserved_cny"] == 0.0


def test_partial_usage_no_refund_squeeze_second_send(
        monkeypatch, tmp_path) -> None:
    """残余 A 主审反例(R1 §4.2):prompt-only usage 不得当完整计费
    证明 —— 帽=一次保守界时,第一次发送后预留全额保守保留,第二次
    发送先拒(旧口径 prompt-only 结算 input-only 金额退预留,挤出第二
    次发送)。"""
    gate = _gate(tmp_path, cap=BOUND)  # 恰一次尝试额度
    client, calls = _client(
        monkeypatch, gate=gate,
        responses=[_ok_payload(usage={"prompt_tokens": 900})] * 2)
    first = client.complete(mode="proposals", system_prompt="s",
                            user_payload="u")
    assert first.ok is True and calls["n"] == 1
    snap = FileRateGate(tmp_path / "gate").cost_snapshot()
    assert snap["unsettled_cny"] == pytest.approx(BOUND, abs=1e-9)
    assert snap["settled_cny"] == 0.0
    second = client.complete(mode="proposals", system_prompt="s",
                             user_payload="u")
    assert second.error_kind == "budget_cost_exhausted"
    assert calls["n"] == 1, "部分 usage 不得靠退款挤出第二次发送"


def test_low_complete_usage_still_sends(monkeypatch, tmp_path) -> None:
    """残余 A 正控:完整拆分的合法低费用结算退回差值,后续发送照常
    (不因保守口径误伤合法低费用)。"""
    low = {"prompt_tokens": 100, "completion_tokens": 100,
           "total_tokens": 200}  # 实际 0.00036 << BOUND
    gate = _gate(tmp_path, cap=BOUND * 1.1)
    client, calls = _client(monkeypatch, gate=gate,
                            responses=[_ok_payload(usage=low),
                                       _ok_payload(usage=low)])
    assert client.complete(mode="proposals", system_prompt="s",
                           user_payload="u").ok
    assert client.complete(mode="proposals", system_prompt="s",
                           user_payload="u").ok
    assert calls["n"] == 2
    snap = FileRateGate(tmp_path / "gate").cost_snapshot()
    assert snap["settled_cny"] == pytest.approx(0.00036 * 2, abs=1e-9)
    assert snap["unsettled_cny"] == 0.0


def test_partial_usage_duplicate_receipt_idempotent(tmp_path) -> None:
    """残余 A 重复回执:同一占位重复 record_response(部分 usage)⇒
    幂等 no-op —— 未知保守保留恰一次,不重退不重扣。"""
    gate = _gate(tmp_path, cap=BOUND * 3)
    acquired = gate.acquire()
    partial = {"prompt_tokens": 900}
    gate.record_response(status=200, usage=partial,
                         placeholder_id=acquired["placeholder_id"])
    gate.record_response(status=200, usage=partial,
                         placeholder_id=acquired["placeholder_id"])
    gate.record_response(status=200, usage=partial,
                         placeholder_id=acquired["placeholder_id"])
    snap = FileRateGate(tmp_path / "gate").cost_snapshot()
    assert snap["unsettled_cny"] == pytest.approx(BOUND, abs=1e-9)
    assert snap["settled_cny"] == 0.0
    assert snap["reserved_cny"] == 0.0


def test_worker_partial_usage_second_question_zero_send(
        monkeypatch, tmp_path) -> None:
    """残余 A worker 级(R1 §4.2 独立公开 worker 反例):两题批、假
    提供者返回 prompt-only usage、帽=一次保守界 + 容差 —— 第一题
    发送一次(预留保守保留不结算,committed=全额 bound),第二题零
    发送(run budget_limit 终态留分母);对照:完整 usage 合法低费用
    结算退回差值,第二题照常发送(旧口径 prompt-only 结算 input-only
    金额退预留,两题都发送)。"""
    from pathway_v43.pollutant.s5b_builder import build_question_batch

    bound = (10_000 * 0.8 + 20_000 * 2.8) / 1_000_000  # 0.064
    cap = bound + 0.006  # 容一次保守界,容不下第二次全额预留

    def _run_two_questions(label: str, usage: dict) -> dict:
        questions = tmp_path / f"q-{label}.jsonl"
        questions.write_text(
            "\n".join(json.dumps(q) for q in SYNTH_QUESTIONS[:2]) + "\n",
            encoding="utf-8")
        batch_root = tmp_path / f"batch-{label}"
        build_question_batch(
            questions, batch_root, batch_tag=f"r2-{label}",
            pool_provider=synth_pool_provider, provider_kind="real",
            synthetic_review=True)
        _write_budget(batch_root, cap=cap)
        (batch_root / "profile_policy.json").write_text(
            json.dumps(S5B_DEFAULT_PROFILE_POLICY), encoding="utf-8")
        FileRateGate(batch_root / "gate", rpm=10 ** 9, tpm=10 ** 9,
                     max_calls=50, cost_guard=normalize_cost_guard_config({
                         "cap_cny": cap, "input_per_mtok": 0.8,
                         "output_per_mtok": 2.8,
                         "input_tokens_conservative_bound": 10_000,
                         "max_output_tokens": 20_000, "currency": "CNY"}))
        calls = {"n": 0}

        def fake_urlopen(req, timeout=None):
            calls["n"] += 1
            body = json.loads(req.data.decode("utf-8"))
            import io

            resp = io.BytesIO(json.dumps(
                _proposals_response(body, usage=usage)).encode("utf-8"))
            resp.status = 200
            resp.headers = {"X-Dashscope-Request-Id": "req-r2"}
            return resp

        monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
        for key, value in (("V43_LLM_BASE_URL", "https://fake.example/v1"),
                           ("V43_LLM_API_KEY", "sk-r2-test"),
                           ("V43_LLM_MODEL", "r2-test-model")):
            monkeypatch.setenv(key, value)
        monkeypatch.setenv("V43_LLM_RATE_GATE",
                           str(batch_root / "gate"))
        monkeypatch.delenv("S5B_MODEL_STUB_SCRIPT", raising=False)
        for qid in ("SYNTH-Q001", "SYNTH-Q002"):
            rc = worker_main(["--batch-root", str(batch_root),
                              "--runs-root", str(batch_root / "runs"),
                              "--qid", qid])
            assert rc == 0
        return {"calls": calls, "batch_root": batch_root}

    # 反例:prompt-only ⇒ 第一题发送一次,第二题零发送留分母
    partial = _run_two_questions("partial", {"prompt_tokens": 900})
    assert partial["calls"]["n"] == 1, "部分 usage 不得挤出第二次发送"
    snap = FileRateGate(partial["batch_root"] / "gate").cost_snapshot()
    assert snap["unsettled_cny"] == pytest.approx(bound, abs=1e-9)
    assert snap["settled_cny"] == 0.0
    assert snap["send_rejections"] >= 1
    assert snap["committed_cny"] <= snap["cap_cny"] + 1e-9
    # 正控:完整 usage 合法低费用 ⇒ 两题都发送
    full = _run_two_questions(
        "full", {"prompt_tokens": 900, "completion_tokens": 1000,
                 "total_tokens": 1900})
    assert full["calls"]["n"] == 2


# ====================================================== 残余 B:429 保守保留

def test_429_no_usage_conservative_keep_client(
        monkeypatch, tmp_path) -> None:
    """残余 B:无 usage 的 429 ⇒ 预留全额保守保留(不退);槽位释放/
    冷却/HTTP 计数不退保持;预算内重试继续(每次先重新预留)。"""
    gate = _gate(tmp_path, cap=BOUND * 3)
    four29 = urllib.error.HTTPError(
        "https://llm.example/v1/chat/completions", 429, "err",
        {"Retry-After": "0"}, __import__("io").BytesIO(b""))
    client, calls = _client(monkeypatch, gate=gate,
                            responses=[four29, _ok_payload()],
                            max_retries=4)
    resp = client.complete(mode="proposals", system_prompt="s",
                           user_payload="u")
    assert resp.ok is True and calls["n"] == 2, "预算内重试继续"
    state = json.loads((tmp_path / "gate" / "gate.json").read_text())
    assert state["total_429"] == 1          # 冷却记账保持
    assert state["in_flight"] == 0          # 槽位释放保持
    assert state["total_requests"] == 2     # HTTP 数量门不退
    assert state["cooldown_until"] > 0
    snap = FileRateGate(tmp_path / "gate").cost_snapshot()
    # 第一次尝试(429)预留全额保守保留;第二次(成功)按完整 usage 结算
    assert snap["unsettled_cny"] == pytest.approx(BOUND, abs=1e-9)
    assert snap["settled_cny"] == pytest.approx(USAGE_ACTUAL, abs=1e-9)
    assert snap["reserved_cny"] == 0.0


def test_429_body_usage_not_zeroed_without_basis(
        monkeypatch, tmp_path) -> None:
    """残余 B(R1 §4.3 独立控制):429 body 含 usage —— 客户端不读
    HTTP 错误体作为计费依据(提供者对 429 的计费政策未核验),不得
    被忽略后无依据归零:预留保守保留。"""
    gate = _gate(tmp_path, cap=BOUND * 3)
    body_with_usage = json.dumps(
        {"error": "rate_limited", "usage": {
            "prompt_tokens": 1000, "completion_tokens": 2000,
            "total_tokens": 3000}}).encode("utf-8")
    four29 = urllib.error.HTTPError(
        "https://llm.example/v1/chat/completions", 429, "err",
        {"Retry-After": "0"}, __import__("io").BytesIO(body_with_usage))
    client, calls = _client(monkeypatch, gate=gate,
                            responses=[four29], max_retries=0)
    resp = client.complete(mode="proposals", system_prompt="s",
                           user_payload="u")
    assert resp.error_kind == "rate_limited_exhausted"
    assert calls["n"] == 1
    snap = FileRateGate(tmp_path / "gate").cost_snapshot()
    # 不读 body ⇒ 无可计 usage ⇒ 保守保留(金额不为 0,不归零)
    assert snap["unsettled_cny"] == pytest.approx(BOUND, abs=1e-9)
    assert snap["settled_cny"] == 0.0
    assert snap["reserved_cny"] == 0.0


def test_429_with_complete_usage_settles_gate_level(tmp_path) -> None:
    """残余 B 闸门直收:429 携带完整合法 usage(record_response 直接
    调用方,如未来实现读 body)⇒ 按同源完整性判据结算(已知完整
    usage 走保守计费路径);429 携带部分 usage ⇒ 保守保留。"""
    gate = _gate(tmp_path, cap=BOUND * 3)
    a = gate.acquire()
    gate.record_response(
        status=429, usage={"prompt_tokens": 1000, "completion_tokens": 2000,
                           "total_tokens": 3000},
        placeholder_id=a["placeholder_id"])
    snap = FileRateGate(tmp_path / "gate").cost_snapshot()
    assert snap["settled_cny"] == pytest.approx(USAGE_ACTUAL, abs=1e-9)
    assert snap["unsettled_cny"] == 0.0
    b = gate.acquire()
    gate.record_response(status=429, usage={"prompt_tokens": 900},
                         placeholder_id=b["placeholder_id"])
    snap2 = FileRateGate(tmp_path / "gate").cost_snapshot()
    assert snap2["settled_cny"] == pytest.approx(USAGE_ACTUAL, abs=1e-9)
    assert snap2["unsettled_cny"] == pytest.approx(BOUND, abs=1e-9)


def test_429_insufficient_balance_stops_retry_before_transmission(
        monkeypatch, tmp_path) -> None:
    """残余 B:重试每次先预留、余额不足先拒 —— 帽=一次保守界时,
    第一次 429 保守保留后,重试的第二次 acquire 先于传输拒。"""
    gate = _gate(tmp_path, cap=BOUND)
    four29 = urllib.error.HTTPError(
        "https://llm.example/v1/chat/completions", 429, "err",
        {"Retry-After": "0"}, __import__("io").BytesIO(b""))
    client, calls = _client(monkeypatch, gate=gate,
                            responses=[four29] * 5, max_retries=4)
    resp = client.complete(mode="proposals", system_prompt="s",
                           user_payload="u")
    assert resp.error_kind == "budget_cost_exhausted"
    assert calls["n"] == 1, "余额不足必须先于重试传输拒"
    snap = FileRateGate(tmp_path / "gate").cost_snapshot()
    assert snap["unsettled_cny"] == pytest.approx(BOUND, abs=1e-9)
    assert snap["send_rejections"] == 1


# ====================================================== 残余 C:存储冻结块

def test_verify_stored_cost_guard_unit() -> None:
    """残余 C 单元:stored 冻结块派生 bound/hash 对照同源重算 ——
    错/缺派生值、错哈希 ⇒ ValueError(结构化 detail);builder 原始
    core(无派生字段)是合法派生入口(normalize 派生,不拒)。"""
    raw = dict(CFG)  # builder 原始 core(无派生字段)
    canonical = normalize_cost_guard_config(raw)
    assert canonical["per_attempt_bound_cny"] == pytest.approx(
        BOUND, abs=1e-9)
    # 合法 stored(派生值与重算一致)⇒ 返回重算规范对象
    stored = {**raw, "per_attempt_bound_cny": canonical[
        "per_attempt_bound_cny"],
        "config_sha256": canonical["config_sha256"]}
    assert verify_stored_cost_guard(stored) == canonical
    # 派生 bound 错(主审反例形态:.000001)
    bad_bound = {**stored, "per_attempt_bound_cny": 0.000001}
    with pytest.raises(ValueError) as excinfo:
        verify_stored_cost_guard(bad_bound)
    detail = excinfo.value.args[0]
    assert detail["reason"] == "stored_derived_mismatch"
    assert detail["field"] == "per_attempt_bound_cny"
    assert detail["stored"] == 0.000001
    assert detail["recalculated"] == pytest.approx(BOUND, abs=1e-12)
    # 派生 bound 缺
    with pytest.raises(ValueError) as excinfo2:
        verify_stored_cost_guard(
            {k: v for k, v in stored.items()
             if k != "per_attempt_bound_cny"})
    assert "stored_derived_missing" in \
        excinfo2.value.args[0]["reason"]
    # sha 错(全 0)/缺
    with pytest.raises(ValueError) as excinfo3:
        verify_stored_cost_guard(
            {**stored, "config_sha256": "0" * 64})
    assert excinfo3.value.args[0]["field"] == "config_sha256"
    with pytest.raises(ValueError):
        verify_stored_cost_guard(
            {k: v for k, v in stored.items() if k != "config_sha256"})


def test_gate_reopen_same_value_and_verify_config(tmp_path) -> None:
    """残余 C 正控:同值恢复 —— 合法存储冻结块重开闸门正常装配
    (verify_config/摘要一致);旧未启用金额分支(无 cost_guard 块)
    行为不变。"""
    gate = _gate(tmp_path)
    gate.verify_config()
    gate2 = FileRateGate(tmp_path / "gate")
    gate2.verify_config()
    summary = gate2.cost_guard_summary()
    assert summary is not None
    assert summary["per_attempt_bound_cny"] == pytest.approx(
        BOUND, abs=1e-9)
    assert summary == normalize_cost_guard_config(dict(CFG))
    # 旧分支:无金额块的闸门照常(金额守卫未启用)
    plain_dir = tmp_path / "plain-gate"
    FileRateGate(plain_dir, rpm=10 ** 9, tpm=10 ** 9, max_calls=5)
    plain = FileRateGate(plain_dir)
    assert plain.cost_guard_summary() is None
    acquired = plain.acquire()
    assert acquired["placeholder_id"]
    plain.record_response(placeholder_id=acquired["placeholder_id"])


def test_gate_reopen_tampered_bound_rejects_and_preserves(
        tmp_path) -> None:
    """残余 C:恢复装配(stored 恢复入口)—— stored bound 与同源
    重算不一致 ⇒ 构造期 GateCorrupt 结构化拒;坏记录保全(gate.json
    原样保留篡改值,不清零/不修复)。"""
    gate = _gate(tmp_path)
    state_path = tmp_path / "gate" / "gate.json"
    state = json.loads(state_path.read_text())
    state["cost_guard"]["per_attempt_bound_cny"] = 0.000001
    state_path.write_text(json.dumps(state))
    with pytest.raises(GateCorrupt) as excinfo:
        FileRateGate(tmp_path / "gate")
    detail = excinfo.value.detail
    assert detail["kind"] == "cost_guard_config_invalid"
    assert detail["detail"]["reason"] == "stored_derived_mismatch"
    # 保全坏记录:篡改值原样在盘,未被重算值覆写
    preserved = json.loads(state_path.read_text())
    assert preserved["cost_guard"]["per_attempt_bound_cny"] == 0.000001


def test_acquire_tampered_state_rejects_zero_reservation(
        tmp_path) -> None:
    """残余 C:发送临界区 —— 闸门已构造(状态当时合法),状态文件
    之后被改坏 ⇒ acquire 先对照同源重算,错哈希 ⇒ GateCorrupt
    (零新预留/发送;拒发计数不增;坏记录保全不落盘)。"""
    gate = _gate(tmp_path)
    state_path = tmp_path / "gate" / "gate.json"
    state = json.loads(state_path.read_text())
    state["cost_guard"]["config_sha256"] = "0" * 64
    state_path.write_text(json.dumps(state))
    with pytest.raises(GateCorrupt) as excinfo:
        gate.acquire()
    detail = excinfo.value.detail
    assert detail["kind"] == "cost_guard_config_invalid"
    assert detail["detail"]["field"] == "config_sha256"
    state2 = json.loads(state_path.read_text())
    cost = state2["cost"]
    assert cost["reservations"] == {}      # 零新预留
    assert cost["send_rejections"] == 0    # 拒发计数不增(非金额拒)
    assert state2["cost_guard"]["config_sha256"] == "0" * 64  # 保全
    assert state2["total_requests"] == 0   # 零发送


def test_cost_guard_summary_tampered_rejects(tmp_path) -> None:
    """残余 C:摘要首消费(client/worker/身份同源)—— stored 派生值
    缺 ⇒ cost_guard_summary GateCorrupt,不返回"重算洗白"的规范值。"""
    gate = _gate(tmp_path)
    state_path = tmp_path / "gate" / "gate.json"
    state = json.loads(state_path.read_text())
    state["cost_guard"].pop("per_attempt_bound_cny")
    state_path.write_text(json.dumps(state))
    with pytest.raises(GateCorrupt) as excinfo:
        gate.cost_guard_summary()
    assert "stored_derived_missing" in json.dumps(excinfo.value.detail)


def test_client_stored_bad_block_refuses_before_transmission(
        monkeypatch, tmp_path) -> None:
    """残余 C(R1 §4.4"存储SHA改全0也不拒"控制):client complete 首消
    费 —— stored 派生 bound 坏 / sha 全 0 ⇒ budget_config_invalid
    结构化失败,零 urlopen 调用。"""
    mutations = {
        "bad-bound": lambda g: g.__setitem__(
            "per_attempt_bound_cny", 0.000001),
        "sha-zero": lambda g: g.__setitem__("config_sha256", "0" * 64),
    }
    for name, mutate in mutations.items():
        gate = _gate(tmp_path / f"gate-{name}")
        client, calls = _client(monkeypatch, gate=gate,
                                responses=[_ok_payload()])
        state_path = gate.dir / "gate.json"
        state = json.loads(state_path.read_text())
        mutate(state["cost_guard"])
        state_path.write_text(json.dumps(state))
        resp = client.complete(mode="proposals", system_prompt="s",
                               user_payload="u")
        assert resp.error_kind == "budget_config_invalid", name
        assert calls["n"] == 0, "坏存储块必须先于传输拒(零发送)"


def test_client_gate_block_maps_corrupt_to_budget_config_invalid(
        tmp_path) -> None:
    """残余 C:发送临界区 acquire 期 GateCorrupt ⇒ _gate_block 映射
    budget_config_invalid 结构化失败(不裸抛;与 summary 首消费同
    kind,调用方可机读)。"""
    from pathway_v43.adapters.llm_client import OpenAICompatibleClient

    gate = _gate(tmp_path)
    client = OpenAICompatibleClient(
        base_url="https://llm.example/v1", api_key="sk-test", model="m",
        timeout_s=5, gate=gate)
    resp = client._gate_block(GateCorrupt({
        "kind": "cost_guard_config_invalid",
        "detail": {"reason": "stored_derived_mismatch"}}))
    assert resp.error_kind == "budget_config_invalid"
    assert resp.error_detail["detail"]["reason"] == \
        "stored_derived_mismatch"


def test_settlement_with_tampered_guard_keeps_conservative(
        tmp_path) -> None:
    """残余 C 结算临界区:占位已原子预留(合法 acquire),之后状态
    块被改坏 ⇒ 结算不消费坏价格/坏块 —— 预留保守转未结算(账本
    事实 bound),token 记账照常,坏记录保全。"""
    gate = _gate(tmp_path, cap=BOUND * 3)
    acquired = gate.acquire()
    state_path = tmp_path / "gate" / "gate.json"
    state = json.loads(state_path.read_text())
    state["cost_guard"]["per_attempt_bound_cny"] = 0.000001
    state_path.write_text(json.dumps(state))
    gate.record_response(
        status=200, usage={"prompt_tokens": 1000, "completion_tokens": 2000,
                           "total_tokens": 3000},
        placeholder_id=acquired["placeholder_id"])
    state2 = json.loads(state_path.read_text())
    entry = state2["cost"]["reservations"][acquired["placeholder_id"]]
    assert entry["state"] == "unsettled"
    assert entry["note"] == "cost_guard_stored_invalid_settlement_kept"
    assert state2["cost"]["unsettled_cny"] == pytest.approx(
        BOUND, abs=1e-9)
    assert state2["cost"]["settled_cny"] == 0.0
    # 坏记录保全 + token 记账照常(TPM 滑窗是速率机制,不受金额块影响)
    assert state2["cost_guard"]["per_attempt_bound_cny"] == 0.000001
    assert state2["token_events"] and state2["token_events"][-1][1] == 3000


# 主审反例(R1 §4.4):合法 bound=.046938、帽=.001 ⇒ 本应零发送;
# stored bound 改 .000001 ⇒ 旧代码实际发送 1 次(settled .00352 超帽)。
COUNTER_BOUND = 0.046938  # (30000*0.8 + 8192*2.8)/1e6 四舍五入
COUNTER_CFG = {
    "schema": "s5b-budget-guard-1",
    "cap_cny": 0.001,
    "input_per_mtok": 0.8,
    "output_per_mtok": 2.8,
    "input_tokens_conservative_bound": 30_000,
    "max_output_tokens": 8192,
    "currency": "CNY",
}


def test_worker_stored_bound_tamper_main_audit_counterexample(
        monkeypatch, tmp_path) -> None:
    """残余 C 主审反例复现(worker 公开入口端到端):批根合法
    bound=.046938/帽=.001、gate.json stored bound 改 .000001(核心
    价格/界/原 SHA 不改)⇒ 先结构化拒、零发送、失败题留分母、坏记录
    保全;正控:同配置不篡改 ⇒ 余额不足先拒(budget_limit 终态),
    同样零发送。"""
    from pathway_v43.pollutant.s5b_builder import build_question_batch

    assert normalize_cost_guard_config(dict(COUNTER_CFG))[
        "per_attempt_bound_cny"] == pytest.approx(
        COUNTER_BOUND, abs=1e-12)
    questions = tmp_path / "q.jsonl"
    questions.write_text(
        "\n".join(json.dumps(q) for q in SYNTH_QUESTIONS[:2]) + "\n",
        encoding="utf-8")
    batch_root = tmp_path / "batch"
    build_question_batch(
        questions, batch_root, batch_tag="r2-counter",
        pool_provider=synth_pool_provider, provider_kind="real",
        synthetic_review=True)
    (batch_root / S5B_BUDGET_GUARD_FILE).write_text(
        json.dumps(dict(COUNTER_CFG)), encoding="utf-8")
    (batch_root / "profile_policy.json").write_text(
        json.dumps(S5B_DEFAULT_PROFILE_POLICY), encoding="utf-8")
    FileRateGate(batch_root / "gate", rpm=10 ** 9, tpm=10 ** 9,
                 max_calls=50, cost_guard=dict(COUNTER_CFG))
    calls = {"n": 0}

    def fake_urlopen(req, timeout=None):  # pragma: no cover —— 不应到达
        calls["n"] += 1
        raise AssertionError("反例口径下不得到达传输层")

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    for key, value in (("V43_LLM_BASE_URL", "https://fake.example/v1"),
                       ("V43_LLM_API_KEY", "sk-r2-counter"),
                       ("V43_LLM_MODEL", "r2-counter-model")):
        monkeypatch.setenv(key, value)
    monkeypatch.setenv("V43_LLM_RATE_GATE", str(batch_root / "gate"))
    monkeypatch.delenv("S5B_MODEL_STUB_SCRIPT", raising=False)
    # 正控:不篡改 ⇒ 合法 bound > 帽 ⇒ 余额不足先于传输拒
    rc = worker_main(["--batch-root", str(batch_root),
                      "--runs-root", str(batch_root / "runs"),
                      "--qid", "SYNTH-Q001"])
    assert rc == 0
    case = json.loads(
        (batch_root / "cases" / "SYNTH-Q001.json").read_text())
    assert case["status"] == "completed"
    assert case["stop_reason"] == "budget_limit"
    assert calls["n"] == 0
    state_path = batch_root / "gate" / "gate.json"
    state = json.loads(state_path.read_text())
    assert state["cost"]["send_rejections"] >= 1
    assert state["cost"]["reservations"] == {}
    # 反例:只把 stored bound 改 .000001(核心价格/界/SHA 不动)
    state["cost_guard"]["per_attempt_bound_cny"] = 0.000001
    state_path.write_text(json.dumps(state))
    rc2 = worker_main(["--batch-root", str(batch_root),
                       "--runs-root", str(batch_root / "runs"),
                       "--qid", "SYNTH-Q002"])
    assert rc2 == 5
    case2 = json.loads(
        (batch_root / "cases" / "SYNTH-Q002.json").read_text())
    assert case2["status"] == "failed"
    assert case2["failure_kind"] == "budget_guard_invalid"
    detail = case2["detail"]
    assert detail["kind"] == "cost_guard_config_invalid"
    assert detail["detail"]["reason"] == "stored_derived_mismatch"
    assert detail["detail"]["field"] == "per_attempt_bound_cny"
    # 零发送 + 零新预留 + 坏记录保全
    assert calls["n"] == 0
    state2 = json.loads(state_path.read_text())
    assert state2["cost_guard"]["per_attempt_bound_cny"] == 0.000001
    assert state2["cost"]["reservations"] == {}
    assert state2["cost"]["settled_cny"] == 0.0
