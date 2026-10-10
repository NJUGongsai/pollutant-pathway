"""PPV1 S5b HIT50 v3 回修 R3 —— S5B-V3-02 两个同规则残余
(R2 正链复审 §4.1/§4.2 + §8;基线 d08432c)。S5B-V3-01 保持关闭;
R2 已修部分(B 保守 429、缺轴不补 0、坏派生字段首消费拒)零回退。

**残余 A'(合法总计回退)**:rate_gate._cost_of_usage 的 total 回退
分支消费前核已知有效轴下界 —— 已有有效轴(如 prompt=900)与
total(=1)内部自矛盾时不得当"合法可核总计"低额结清未知费用;矛盾
⇒ None 不可计(预留保守保留)。R2 复审 §4.1 反例:prompt900/total1/
缺 output、cap=.00768/bound=.0064 ⇒ 旧口径两次 settled=.000003 退掉
预留、第二次发送照发;修后金额保守保留、第二次发送先拒。同规则适用
矩阵覆盖 output 轴下界与两轴情形;保持:无轴 total-only>0、兼容已知
轴的 total(prompt900+total1900)、完整双轴 900/1000(冗余矛盾 total
与缺轴回退分开处理,不全面拒绝)、重复回执幂等。

**残余 C'(已启用配置存在性)**:cost_guard 整块 null/删键在运行中
(首次发送后)不得降级"legacy 未启用"分支放行后续发送。四个运行中
消费入口(_load 共用验证 / _init_state 重开装配 / cost_guard_summary
摘要首消费 / acquire 发送临界区;record_response 结算临界区保守处理)
按既有启用事实(既存金额账本 cost 块、本进程已装配/构造配置;worker
冻结预算经 _verify_budget_guard 首消费)辨别"合法旧未启用"与"已启用
块消失";坏形态 ⇒ GateCorrupt 结构化拒(零新发送/零新预约、坏形态
保全、第一次已发账本保守保留不删除不假退款)。R2 复审 §4.2 反例:
公开 worker 第一次合法 HTTP429 后仅破坏 cost_guard(null/删键两形态,
cap=.056326/bound=.046938)⇒ 旧口径第二次假 urlopen 仍发生(新增 1
次发送、0 条金额预约);修后第二 HTTP 先拒。保持:真正无 guard 无
金额账本的旧分支合法、同值恢复/正常 builder/孤儿/幂等(既有 r1/r2
控制全绿)。

全部合成假传输(urllib 打桩),零真实模型/零外部网络/零花费;不认证
真实账单或提供者计费政策。
"""

from __future__ import annotations

import io
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
)
from pathway_v43.pollutant.s5b_orchestrator import (  # noqa: E402
    S5B_BUDGET_GUARD_FILE,
    S5B_DEFAULT_PROFILE_POLICY,
)
from pathway_v43.pollutant.s5b_worker import worker_main  # noqa: E402

from test_ppv1_s5b_hit50_v3r1_cost import (  # noqa: E402
    BOUND,
    CFG,
    _client,
    _gate,
    _ok_payload,
    _proposals_response,
)
from test_ppv1_s5b_runtime import (  # noqa: E402
    SYNTH_QUESTIONS,
    synth_pool_provider,
)

REPO_ROOT = Path(__file__).resolve().parents[1]

# ====================================================== 残余 A':总计下界

# (标签, usage, 期望 settled_cny, 期望 unsettled_cny)
# CFG 价格:输入 0.8 / 输出 2.8 元/Mtok;BOUND=.0064
CONTRADICT_MATRIX = [
    # R2 复审 §4.1 反例:prompt=900 有效轴在,缺输出轴,total=1 与该轴
    # 自矛盾 ⇒ 不可计,预留全额保守保留(旧口径 settled=1*2.8/1e6)
    ("incomplete_prompt_total_contradiction",
     {"prompt_tokens": 900, "total_tokens": 1}, 0.0, BOUND),
    # 同规则 output 轴下界:completion=500 有效轴在,total=1 矛盾 ⇒ 保留
    ("incomplete_output_total_contradiction",
     {"completion_tokens": 500, "total_tokens": 1}, 0.0, BOUND),
    # 两轴情形:完整双轴显式有效 ⇒ 精确结算,冗余矛盾 total 不参与该
    # 分支(与缺轴回退分开处理,不全面拒绝)
    ("complete_split_with_redundant_contradictory_total",
     {"prompt_tokens": 900, "completion_tokens": 1000, "total_tokens": 1},
     0.00352, 0.0),
    # 保持:兼容已知轴的 total(prompt900 + total1900)⇒ 保守总计口径
    ("prompt_plus_compatible_total",
     {"prompt_tokens": 900, "total_tokens": 1900}, 0.00532, 0.0),
    # 保持:兼容已知 output 轴的 total ⇒ 保守总计口径(1500*2.8/1e6)
    ("output_plus_compatible_total",
     {"completion_tokens": 1000, "total_tokens": 1500}, 0.0042, 0.0),
    # 边界:total 恰等于已知轴和(下界通过)⇒ 保守总计口径(900*2.8/1e6)
    ("total_equals_known_axis",
     {"prompt_tokens": 900, "total_tokens": 900}, 0.00252, 0.0),
    # 保持:无轴 total-only>0 ⇒ 保守总计口径(3000*2.8/1e6)
    ("total_only_positive", {"total_tokens": 3000}, 0.0084, 0.0),
]


@pytest.mark.parametrize("label,usage,settled,unsettled", CONTRADICT_MATRIX)
def test_contradictory_total_matrix_client(
        monkeypatch, tmp_path, label, usage, settled, unsettled) -> None:
    """残余 A' 逐案:总计回退分支核已知有效轴下界 —— 自矛盾 ⇒ 不可计
    (预留全额保守保留);兼容总计/完整双轴/无轴 total-only 保持既有
    口径。"""
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


def test_contradictory_total_no_refund_squeeze_second_send(
        monkeypatch, tmp_path) -> None:
    """残余 A' 主审反例复现(R2 复审 §4.1 数值):prompt900/total1/
    缺输出轴、cap=.00768/bound=.0064 —— 自矛盾总计不当"合法可核
    总计"低额结清未知费用:金额保守保留,第二次发送先拒(旧口径每次
    settled=.000003 退掉预留,两次均发送)。"""
    gate = _gate(tmp_path, cap=0.00768)  # = BOUND * 1.2
    contradictory = {"prompt_tokens": 900, "total_tokens": 1}
    client, calls = _client(
        monkeypatch, gate=gate,
        responses=[_ok_payload(usage=contradictory)] * 2)
    first = client.complete(mode="proposals", system_prompt="s",
                            user_payload="u")
    assert first.ok is True and calls["n"] == 1
    snap = FileRateGate(tmp_path / "gate").cost_snapshot()
    assert snap["unsettled_cny"] == pytest.approx(BOUND, abs=1e-9)
    assert snap["settled_cny"] == 0.0
    second = client.complete(mode="proposals", system_prompt="s",
                             user_payload="u")
    assert second.error_kind == "budget_cost_exhausted"
    assert calls["n"] == 1, "自矛盾总计不得低额结清未知费用挤出第二次发送"


def test_contradictory_total_duplicate_receipt_idempotent(
        tmp_path) -> None:
    """残余 A' 重复回执:同一占位重复 record_response(自矛盾总计
    usage)⇒ 幂等 no-op —— 未知保守保留恰一次,不重退不重扣。"""
    gate = _gate(tmp_path, cap=BOUND * 3)
    acquired = gate.acquire()
    contradictory = {"prompt_tokens": 900, "total_tokens": 1}
    for _ in range(3):
        gate.record_response(status=200, usage=contradictory,
                             placeholder_id=acquired["placeholder_id"])
    snap = FileRateGate(tmp_path / "gate").cost_snapshot()
    assert snap["unsettled_cny"] == pytest.approx(BOUND, abs=1e-9)
    assert snap["settled_cny"] == 0.0
    assert snap["reserved_cny"] == 0.0


# ================================================== 残余 C':已启用块存在性

# 两坏形态:整块置 null / 删键(R2 复审 §4.2 两形态;其余状态原样保留)
BLOCK_MISSING_FORMS = ["null", "deleted"]


def _mutate_block_missing(state_path: Path, form: str) -> None:
    """仅破坏 cost_guard 整块(原 cost 账本/预留及其余状态不动)。"""
    state = json.loads(state_path.read_text())
    if form == "null":
        state["cost_guard"] = None
    elif form == "deleted":
        state.pop("cost_guard")
    else:  # pragma: no cover —— 参数受控
        raise AssertionError(form)
    state_path.write_text(json.dumps(state))


@pytest.mark.parametrize("form", BLOCK_MISSING_FORMS)
def test_gate_entries_block_missing_after_enabled_reject(
        tmp_path, form) -> None:
    """残余 C' 闸门四入口(gate 级):已启用(装配+预留已发生)后块
    整体消失 ⇒ cost_guard_summary(acquire 同一 _load 共用验证)与
    acquire 均 GateCorrupt 结构化拒(kind=cost_guard_config_invalid/
    reason=cost_guard_block_missing_after_enabled),零新预留、坏形态
    保全;重开装配(_init_state,既存金额账本为证)同样拒。"""
    gate = _gate(tmp_path)
    acquired = gate.acquire()          # 第一次合法预留已发生
    placeholder = acquired["placeholder_id"]
    state_path = tmp_path / "gate" / "gate.json"
    before = json.loads(state_path.read_text())
    _mutate_block_missing(state_path, form)
    # 摘要首消费(summary/acquire/verify_config 共用 _load 验证)
    with pytest.raises(GateCorrupt) as excinfo:
        gate.cost_guard_summary()
    detail = excinfo.value.detail
    assert detail["reason"] == "cost_guard_block_missing_after_enabled"
    assert detail["kind"] == "cost_guard_config_invalid"
    # 发送临界区:先结构化拒,零新预留/零新发送/拒发计数不增/不落盘
    with pytest.raises(GateCorrupt) as excinfo2:
        gate.acquire()
    assert excinfo2.value.detail["reason"] == \
        "cost_guard_block_missing_after_enabled"
    after = json.loads(state_path.read_text())
    assert "cost_guard" not in after if form == "deleted" \
        else after["cost_guard"] is None, "坏形态保全(不重建配置)"
    cost = after["cost"]
    assert len(cost["reservations"]) == 1        # 只有第一次的预留
    assert cost["reservations"][placeholder]["state"] == "reserved"
    assert cost["send_rejections"] == 0
    assert cost["settled_cny"] == 0.0            # 已发账本保守保留不删除
    assert cost["reserved_cny"] == pytest.approx(BOUND, abs=1e-9)
    # 重开装配入口(_init_state):既存金额账本为证 ⇒ 构造期拒
    with pytest.raises(GateCorrupt) as excinfo3:
        FileRateGate(tmp_path / "gate")
    assert excinfo3.value.detail[
        "reason"] == "cost_guard_block_missing_after_enabled"
    preserved = json.loads(state_path.read_text())
    assert "cost_guard" not in preserved if form == "deleted" \
        else preserved["cost_guard"] is None


@pytest.mark.parametrize("form", BLOCK_MISSING_FORMS)
def test_record_response_block_missing_keeps_conservative(
        tmp_path, form) -> None:
    """残余 C' 结算临界区:已启用块消失 ⇒ 不降级 legacy、不结算、
    不假退款 —— 该占位预留保守转未结算(账本事实 bound + 结构化
    note),占位/token 记账照常,坏形态原样保全;下一次发送先拒。"""
    gate = _gate(tmp_path, cap=BOUND * 3)
    acquired = gate.acquire()
    placeholder = acquired["placeholder_id"]
    state_path = tmp_path / "gate" / "gate.json"
    _mutate_block_missing(state_path, form)
    # 结算入口不裸抛(429/成功路径的记账照常走完)
    gate.record_response(
        status=200, usage={"prompt_tokens": 900, "completion_tokens": 1000,
                           "total_tokens": 1900},
        placeholder_id=placeholder)
    state = json.loads(state_path.read_text())
    entry = state["cost"]["reservations"][placeholder]
    assert entry["state"] == "unsettled"
    assert entry["note"] == "cost_guard_block_missing_settlement_kept"
    assert state["cost"]["unsettled_cny"] == pytest.approx(BOUND, abs=1e-9)
    assert state["cost"]["settled_cny"] == 0.0
    assert state["cost"]["reserved_cny"] == 0.0
    # 记账照常:占位释放/token 滑窗;坏形态保全
    assert state["in_flight"] == 0
    assert state["token_events"] and state["token_events"][-1][1] == 1900
    assert "cost_guard" not in state if form == "deleted" \
        else state["cost_guard"] is None
    # 下一次发送先拒(结构化)
    with pytest.raises(GateCorrupt):
        gate.acquire()


@pytest.mark.parametrize("form", BLOCK_MISSING_FORMS)
def test_client_between_calls_block_missing_structural_reject(
        monkeypatch, tmp_path, form) -> None:
    """残余 C' client 首消费(complete 第一步=summary):第一次逻辑
    调用合法完成后块消失 ⇒ 第二次逻辑调用 budget_config_invalid
    结构化失败,零新增 urlopen。"""
    gate = _gate(tmp_path, cap=BOUND * 3)
    client, calls = _client(monkeypatch, gate=gate,
                            responses=[_ok_payload(),
                                       _ok_payload()])
    assert client.complete(mode="proposals", system_prompt="s",
                           user_payload="u").ok
    assert calls["n"] == 1
    _mutate_block_missing(tmp_path / "gate" / "gate.json", form)
    resp = client.complete(mode="proposals", system_prompt="s",
                           user_payload="u")
    assert resp.error_kind == "budget_config_invalid"
    assert resp.error_detail["reason"] == \
        "cost_guard_block_missing_after_enabled"
    assert calls["n"] == 1, "已启用块消失 ⇒ 零新增发送"


@pytest.mark.parametrize("form", BLOCK_MISSING_FORMS)
def test_client_retry_block_missing_second_http_rejected(
        monkeypatch, tmp_path, form) -> None:
    """残余 C' client retry(R2 复审 §4.2 场景的独立公开 client 面):
    第一次合法 HTTP 返回 429 且同时仅破坏 cost_guard ⇒ 重试的第二次
    HTTP 先于传输结构化拒(budget_config_invalid);第一次预留保守
    保留为未结算(不删除不假退款),坏形态保全。"""
    gate = _gate(tmp_path, cap=BOUND * 3)
    state_path = tmp_path / "gate" / "gate.json"
    calls = {"n": 0}

    def fake_urlopen(req, timeout=None):
        calls["n"] += 1
        if calls["n"] == 1:
            _mutate_block_missing(state_path, form)   # 第一次合法发送时破坏
            raise urllib.error.HTTPError(
                req.full_url, 429, "synthetic-rate-limit",
                {"Retry-After": "0.001"}, io.BytesIO(b"{}"))
        raise AssertionError("已启用块消失后第二 HTTP 不得到达传输层")

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    monkeypatch.setattr(
        "pathway_v43.adapters.llm_client.time.sleep", lambda _s: None)
    from pathway_v43.adapters.llm_client import OpenAICompatibleClient

    client = OpenAICompatibleClient(
        base_url="https://llm.example/v1", api_key="sk-test", model="m",
        timeout_s=5, gate=gate, max_http_retries=2)
    resp = client.complete(mode="proposals", system_prompt="s",
                           user_payload="u")
    assert resp.error_kind == "budget_config_invalid"
    assert resp.error_detail["reason"] == \
        "cost_guard_block_missing_after_enabled"
    assert calls["n"] == 1, "重试的第二次 HTTP 必须先拒(零新增发送)"
    state = json.loads(state_path.read_text())
    assert "cost_guard" not in state if form == "deleted" \
        else state["cost_guard"] is None
    cost = state["cost"]
    assert len(cost["reservations"]) == 1
    assert list(cost["reservations"].values())[0]["state"] == "unsettled"
    assert list(cost["reservations"].values())[0]["note"] == \
        "cost_guard_block_missing_settlement_kept"
    assert cost["unsettled_cny"] == pytest.approx(BOUND, abs=1e-9)
    assert cost["reserved_cny"] == 0.0
    assert state["total_429"] == 1            # 429 记账照常(冷却/槽位保持)
    assert state["in_flight"] == 0


def test_client_retry_intact_429_control_still_sends(
        monkeypatch, tmp_path) -> None:
    """残余 C' 正控(同构 429 不破坏):守卫完整时 429 重试照常
    (第二 HTTP 发生,每 attempt 先预留)—— 坏形态拒绝不是全面拒绝
    429 重试。"""
    gate = _gate(tmp_path, cap=BOUND * 3)
    four29 = urllib.error.HTTPError(
        "https://llm.example/v1/chat/completions", 429, "err",
        {"Retry-After": "0"}, io.BytesIO(b""))
    client, calls = _client(monkeypatch, gate=gate,
                            responses=[four29, _ok_payload()],
                            max_retries=2)
    resp = client.complete(mode="proposals", system_prompt="s",
                           user_payload="u")
    assert resp.ok is True and calls["n"] == 2, "守卫完整 ⇒ 重试照常"


def test_assembled_config_evidence_blocks_after_ledger_removed(
        tmp_path) -> None:
    """残余 C' 证据源②(已装配配置,同进程):块与金额账本同时被移除
    (部分协同改写)⇒ 同进程内已装配配置仍为启用证据 —— record_response
    不裸抛(记账照常),下一次 acquire 先结构化拒。新进程无账本无装配
    的辨别由 worker _verify_budget_guard 首消费兜底(不要求抵抗全库
    协同改写)。"""
    gate = _gate(tmp_path)
    acquired = gate.acquire()
    placeholder = acquired["placeholder_id"]
    state_path = tmp_path / "gate" / "gate.json"
    state = json.loads(state_path.read_text())
    state.pop("cost_guard")
    state.pop("cost")            # 块+账本同时移除(超出账本证据的部分改写)
    state_path.write_text(json.dumps(state))
    gate.record_response(status=200, usage={"prompt_tokens": 900},
                         placeholder_id=placeholder)     # 记账照常不裸抛
    with pytest.raises(GateCorrupt) as excinfo:
        gate.acquire()
    assert excinfo.value.detail["reason"] == \
        "cost_guard_block_missing_after_enabled"
    assert excinfo.value.detail["assembled_cost_guard_present"] is True


def test_legacy_no_guard_no_ledger_stays_legal(tmp_path) -> None:
    """残余 C' 合法旧未启用保持:真正无 guard、无金额账本的旧 dev
    批分支照常(acquire/记账/摘要 None;状态不新增 cost 块)。"""
    plain_dir = tmp_path / "plain-gate"
    FileRateGate(plain_dir, rpm=10 ** 9, tpm=10 ** 9, max_calls=5)
    plain = FileRateGate(plain_dir)
    assert plain.cost_guard_summary() is None
    acquired = plain.acquire()
    plain.record_response(placeholder_id=acquired["placeholder_id"])
    state = json.loads((plain_dir / "gate.json").read_text())
    assert "cost" not in state and "cost_guard" not in state
    reopen = FileRateGate(plain_dir)      # 重开同样合法
    assert reopen.cost_guard_summary() is None


# R2 复审 §4.2 反例数值:cap=.056326、bound=.046938(30000×0.8 +
# 8192×2.8)/1e6;第一次合法预留 .046938 后余额 .009388 < bound,
# 第二次发送本就必须先拒
CPRIME_CFG = {
    "schema": "s5b-budget-guard-1",
    "cap_cny": 0.056326,
    "input_per_mtok": 0.8,
    "output_per_mtok": 2.8,
    "input_tokens_conservative_bound": 30_000,
    "max_output_tokens": 8192,
    "currency": "CNY",
}
CPRIME_BOUND = 0.046938


@pytest.mark.parametrize("form", BLOCK_MISSING_FORMS)
def test_worker_retry_block_missing_second_http_rejected(
        monkeypatch, tmp_path, form) -> None:
    """残余 C' 主审反例复现(R2 复审 §4.2,worker 公开端到端、两
    形态分别 fresh 执行):公开 worker 第一次合法 HTTP429 时仅破坏
    cost_guard(整块 null/删键;原 cost 账本/预约与批根
    budget_guard.json 均不改,cap=.056326/bound=.046938)⇒ 重试的第
    二 HTTP 必须先结构化拒 —— 零新增发送/零新预约、第一次已发账本
    保守保留(预留转未结算,不删除不假退款)、坏形态保全、失败留分母
    (旧口径:第二次假 urlopen 照发,新增 1 次发送、0 条金额预约)。"""
    from pathway_v43.pollutant.s5b_builder import build_question_batch

    questions = tmp_path / "q.jsonl"
    questions.write_text(json.dumps(SYNTH_QUESTIONS[0]) + "\n",
                         encoding="utf-8")
    batch_root = tmp_path / "batch"
    build_question_batch(
        questions, batch_root, batch_tag=f"r3-cprime-{form}",
        pool_provider=synth_pool_provider, provider_kind="real",
        synthetic_review=True)
    (batch_root / S5B_BUDGET_GUARD_FILE).write_text(
        json.dumps(dict(CPRIME_CFG)), encoding="utf-8")
    (batch_root / "profile_policy.json").write_text(
        json.dumps(S5B_DEFAULT_PROFILE_POLICY), encoding="utf-8")
    FileRateGate(batch_root / "gate", rpm=10 ** 9, tpm=10 ** 9,
                 max_calls=50, cost_guard=dict(CPRIME_CFG))
    state_path = batch_root / "gate" / "gate.json"
    calls = {"n": 0}

    def fake_urlopen(req, timeout=None):
        calls["n"] += 1
        if calls["n"] == 1:
            # 第一次合法发送:429 + 仅破坏 cost_guard 整块(其余不动)
            _mutate_block_missing(state_path, form)
            raise urllib.error.HTTPError(
                req.full_url, 429, "synthetic-rate-limit",
                {"Retry-After": "0.001"}, io.BytesIO(b"{}"))
        raise AssertionError("已启用块消失后第二 HTTP 不得到达传输层")

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    monkeypatch.setattr(
        "pathway_v43.adapters.llm_client.time.sleep", lambda _s: None)
    for key, value in (("V43_LLM_BASE_URL", "https://fake.example/v1"),
                       ("V43_LLM_API_KEY", "sk-r3-cprime"),
                       ("V43_LLM_MODEL", "r3-cprime-model")):
        monkeypatch.setenv(key, value)
    monkeypatch.setenv("V43_LLM_RATE_GATE", str(batch_root / "gate"))
    monkeypatch.delenv("S5B_MODEL_STUB_SCRIPT", raising=False)
    rc = worker_main(["--batch-root", str(batch_root),
                      "--runs-root", str(batch_root / "runs"),
                      "--qid", "SYNTH-Q001"])
    # 失败题留分母:run 级结构化失败(case 终态落盘,endpoint 失败、
    # run_error 记 budget_config_invalid 传输失败;沿 R2 复审口径 ——
    # case 标签不单独证明成功,机器事实在下方断言)
    case = json.loads(
        (batch_root / "cases" / "SYNTH-Q001.json").read_text())
    assert rc == 0 and case["status"] == "completed"
    assert case["run_error"]["kind"] == "real_model_transport_failure"
    assert "budget_config_invalid" in case["run_error"]["message"]
    assert case["endpoint"]["execution_status"] == "failed"
    # 机器事实:第二 HTTP 先拒(零新增发送/零新预约)
    assert calls["n"] == 1, "重试的第二 HTTP 必须先拒"
    state = json.loads(state_path.read_text())
    assert "cost_guard" not in state if form == "deleted" \
        else state["cost_guard"] is None, "坏形态保全"
    assert state["total_requests"] == 1
    cost = state["cost"]
    assert len(cost["reservations"]) == 1      # 零新预约
    entry = list(cost["reservations"].values())[0]
    assert entry["state"] == "unsettled"       # 第一次已发账本保守保留
    assert entry["note"] == "cost_guard_block_missing_settlement_kept"
    assert entry["bound_cny"] == pytest.approx(CPRIME_BOUND, abs=1e-9)
    assert cost["unsettled_cny"] == pytest.approx(CPRIME_BOUND, abs=1e-9)
    assert cost["settled_cny"] == 0.0
    assert cost["reserved_cny"] == 0.0
    assert cost["send_rejections"] == 0
    # 批根 budget_guard.json 不被破坏/不重建(单一事实源仍在)
    batch_guard = json.loads(
        (batch_root / S5B_BUDGET_GUARD_FILE).read_text())
    assert normalize_cost_guard_config(batch_guard)[
        "per_attempt_bound_cny"] == pytest.approx(CPRIME_BOUND, abs=1e-9)


@pytest.mark.parametrize("form", BLOCK_MISSING_FORMS)
def test_worker_assembly_block_missing_with_ledger_rejects(
        monkeypatch, tmp_path, form) -> None:
    """残余 C' worker 装配入口:协调者已写闸门(金额账本已存在)后
    块整块消失 ⇒ 新 worker 进程装配期(_init_state,既存金额账本为证)
    GateCorrupt ⇒ budget_guard_invalid 失败 case(失败题留分母,
    零发送,坏形态保全)。"""
    from pathway_v43.pollutant.s5b_builder import build_question_batch

    questions = tmp_path / "q.jsonl"
    questions.write_text(json.dumps(SYNTH_QUESTIONS[0]) + "\n",
                         encoding="utf-8")
    batch_root = tmp_path / "batch"
    build_question_batch(
        questions, batch_root, batch_tag=f"r3-asm-{form}",
        pool_provider=synth_pool_provider, provider_kind="real",
        synthetic_review=True)
    (batch_root / S5B_BUDGET_GUARD_FILE).write_text(
        json.dumps(normalize_cost_guard_config(dict(CPRIME_CFG))),
        encoding="utf-8")
    (batch_root / "profile_policy.json").write_text(
        json.dumps(S5B_DEFAULT_PROFILE_POLICY), encoding="utf-8")
    FileRateGate(batch_root / "gate", rpm=10 ** 9, tpm=10 ** 9,
                 max_calls=50, cost_guard=dict(CPRIME_CFG))
    state_path = batch_root / "gate" / "gate.json"
    _mutate_block_missing(state_path, form)
    calls = {"n": 0}

    def fake_urlopen(req, timeout=None):  # pragma: no cover —— 不应到达
        calls["n"] += 1
        raise AssertionError("装配期坏形态不得到达传输层")

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    for key, value in (("V43_LLM_BASE_URL", "https://fake.example/v1"),
                       ("V43_LLM_API_KEY", "sk-r3-asm"),
                       ("V43_LLM_MODEL", "r3-asm-model")):
        monkeypatch.setenv(key, value)
    monkeypatch.setenv("V43_LLM_RATE_GATE", str(batch_root / "gate"))
    monkeypatch.delenv("S5B_MODEL_STUB_SCRIPT", raising=False)
    rc = worker_main(["--batch-root", str(batch_root),
                      "--runs-root", str(batch_root / "runs"),
                      "--qid", "SYNTH-Q001"])
    assert rc == 5
    case = json.loads(
        (batch_root / "cases" / "SYNTH-Q001.json").read_text())
    assert case["status"] == "failed"
    assert case["failure_kind"] == "budget_guard_invalid"
    assert calls["n"] == 0
    state = json.loads(state_path.read_text())
    assert "cost_guard" not in state if form == "deleted" \
        else state["cost_guard"] is None, "坏形态保全"


def test_worker_budget_guard_json_unchanged_intact_control(
        monkeypatch, tmp_path) -> None:
    """残余 C' 正控(不破坏,守卫完整):同配置批,假提供者 429 后
    重试继续 —— 第二 HTTP 照常发生(与 r1/r2 既有 429 语义一致;
    坏形态的拒绝不是对 429 重试的全面拒绝)。"""
    from pathway_v43.pollutant.s5b_builder import build_question_batch

    questions = tmp_path / "q.jsonl"
    questions.write_text(json.dumps(SYNTH_QUESTIONS[0]) + "\n",
                         encoding="utf-8")
    batch_root = tmp_path / "batch"
    build_question_batch(
        questions, batch_root, batch_tag="r3-intact",
        pool_provider=synth_pool_provider, provider_kind="real",
        synthetic_review=True)
    (batch_root / "profile_policy.json").write_text(
        json.dumps(S5B_DEFAULT_PROFILE_POLICY), encoding="utf-8")
    # cap 放宽到容两次保守界:429 重试可继续(批根与闸门同一配置)
    wide = dict(CPRIME_CFG, cap_cny=CPRIME_BOUND * 2.5)
    (batch_root / S5B_BUDGET_GUARD_FILE).write_text(
        json.dumps(normalize_cost_guard_config(wide)), encoding="utf-8")
    FileRateGate(batch_root / "gate", rpm=10 ** 9, tpm=10 ** 9,
                 max_calls=50, cost_guard=wide)
    calls = {"n": 0}

    def fake_urlopen(req, timeout=None):
        calls["n"] += 1
        body = json.loads(req.data.decode("utf-8"))
        if calls["n"] == 1:
            raise urllib.error.HTTPError(
                req.full_url, 429, "synthetic-rate-limit",
                {"Retry-After": "0.001"}, io.BytesIO(b"{}"))
        resp = io.BytesIO(json.dumps(
            _proposals_response(body, usage={
                "prompt_tokens": 900, "completion_tokens": 1000,
                "total_tokens": 1900})).encode("utf-8"))
        resp.status = 200
        resp.headers = {"X-Dashscope-Request-Id": "req-r3-intact"}
        return resp

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    monkeypatch.setattr(
        "pathway_v43.adapters.llm_client.time.sleep", lambda _s: None)
    for key, value in (("V43_LLM_BASE_URL", "https://fake.example/v1"),
                       ("V43_LLM_API_KEY", "sk-r3-intact"),
                       ("V43_LLM_MODEL", "r3-intact-model")):
        monkeypatch.setenv(key, value)
    monkeypatch.setenv("V43_LLM_RATE_GATE", str(batch_root / "gate"))
    monkeypatch.delenv("S5B_MODEL_STUB_SCRIPT", raising=False)
    rc = worker_main(["--batch-root", str(batch_root),
                      "--runs-root", str(batch_root / "runs"),
                      "--qid", "SYNTH-Q001"])
    assert rc == 0
    assert calls["n"] == 2, "守卫完整 ⇒ 429 重试照常(第二 HTTP 发生)"
    state = json.loads(
        (batch_root / "gate" / "gate.json").read_text())
    cost = state["cost"]
    assert cost["unsettled_cny"] == pytest.approx(CPRIME_BOUND, abs=1e-9)
    assert cost["settled_cny"] == pytest.approx(0.00352, abs=1e-9)
    assert cost["reserved_cny"] == 0.0
