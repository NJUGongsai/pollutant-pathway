"""PPV1 S5b no-cap budget 运营壳 —— v44 P4c 批级正负控移植(2026-10-14)。

v44 支线 P4c(2026-10-12 用户决定)已评审实现按任务书
TASK_NOCAP_PORT_V43_2026-10-14 同构移植到 v43 主线;本文件 = 对应
测试移植(源:v44/tests/test_v44_p4_launch_gate.py 的批级 no-cap
四测:loader/CLI/run 入口/worker 侧;夹具同源照搬):

- **标记装载单判据**(load_budget_no_cap_marker):缺席 ⇒ None;
  合法 ⇒ 归一对象;坏 JSON/schema/mode/日期/marker/决定原文 ⇒
  fail-closed 拒(不当缺席,防标记成为绕守卫口子);
- **CLI budget --budget-mode**:落标记(不落价格快照);同决定幂等;
  改决定/与数值守卫互斥/数值参数同给/缺决定字段 ⇒ 拒;
- **编排器 run 入口**:real 批无守卫无标记 ⇒ 拒(原行为);
  合法标记 ⇒ 金额门放行(调用数门照常;批报告披露 budget_mode;
  闸门无金额块);标记+数值守卫并存 ⇒ 互斥拒;
- **worker 侧 _verify_budget_guard**(同判据):闸门无金额配置+
  合法标记 ⇒ 通过;无标记 ⇒ budget_guard_missing(原行为);数值
  闸门+标记 ⇒ mismatch;坏标记 ⇒ budget_guard_invalid。

run_s5b_batch no-cap 用例走真实 worker 子进程但无 V43_LLM 凭证 ⇒
model_not_configured 失败题留分母,构造客户端前 fail-closed,零网络。

运行(仓根):PYTHONPATH=src python -m pytest -q -p no:cacheprovider
tests/test_ppv1_s5b_no_cap_budget.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pathway_v43.adapters.rate_gate import (  # noqa: E402
    FileRateGate,
    normalize_cost_guard_config,
)
from pathway_v43.pollutant import s5b_cli  # noqa: E402
from pathway_v43.pollutant.s5b_orchestrator import (  # noqa: E402
    BUDGET_MODE_NO_CAP,
    S5B_BUDGET_NO_CAP_FILE,
    S5B_CASE_SCHEMA_VERSION,
    S5bOrchestratorError,
    load_budget_no_cap_marker,
    no_cap_marker_string,
)
from pathway_v43.pollutant.s5b_worker import (  # noqa: E402
    _verify_budget_guard,
)

# ---- P4c(2026-10-12 用户决定)no-cap 合成夹具 ----
# 用户决定原文(合成替身,语义同真实四项决定;测试不携带真实授权)
NO_CAP_USER_DECISION = (
    "用户 2026-10-12 主窗口四项决定(合成替身):1「本次没有预算帽」"
    " 2「不考虑价格的事情 只考虑性能」 3「模型你看看chenyu上 "
    "env都在chenyu上」 4「批准」")
NO_CAP_DECISION_DATE = "2026-10-12"


# ---------------------------------------------------------------- 夹具


@pytest.fixture()
def clean_llm_env(monkeypatch):
    """清掉环境中一切真实/遗留 LLM 键(含 stub 变量)——负控确定性。"""
    import os

    for name in list(os.environ):
        if name.startswith("V43_LLM_") or name in (
                "LLM_API_BASE_URL", "LLM_API_KEY", "LLM_MODEL"):
            monkeypatch.delenv(name, raising=False)
    monkeypatch.delenv("S5B_MODEL_STUB_SCRIPT", raising=False)
    return os.environ


def budget_guard_raw() -> dict:
    # 合成数值守卫(非真实报价;仅工程核验用)
    return {
        "schema": "s5b-budget-guard-1",
        "cap_cny": 4.0,
        "input_per_mtok": 2.0,
        "output_per_mtok": 8.0,
        "input_tokens_conservative_bound": 30000,
        "max_output_tokens": 8192,
        "currency": "CNY",
    }


def write_no_cap_marker(root: Path, *,
                        date: str = NO_CAP_DECISION_DATE,
                        record: str = NO_CAP_USER_DECISION,
                        malformed: str | None = None) -> Path:
    """直写合法(或指定坏形状)批级 no-cap 标记文件。"""
    payload = {
        "schema": "v44-budget-no-cap-1",
        "budget_mode": BUDGET_MODE_NO_CAP,
        "user_decision_date": date,
        "user_decision_record": record,
        "marker": no_cap_marker_string(date),
        "recorded_at": "2026-10-12T00:00:00+08:00",
    }
    if malformed is not None:
        payload[malformed] = payload.get(malformed)
        if malformed == "bad_json":
            text = "{not json"
        else:
            if malformed == "schema":
                payload["schema"] = "v44-budget-no-cap-0"
            elif malformed == "budget_mode":
                payload["budget_mode"] = "numeric"
            elif malformed == "user_decision_date":
                payload["user_decision_date"] = "2026/10/12"
            elif malformed == "marker":
                payload["marker"] = "no_cap_wrong_marker"
            elif malformed == "user_decision_record":
                payload["user_decision_record"] = ""
            text = json.dumps(payload, ensure_ascii=False)
    else:
        text = json.dumps(payload, ensure_ascii=False)
    path = root / S5B_BUDGET_NO_CAP_FILE
    path.write_text(text, encoding="utf-8")
    return path


# ---------------------------------------------------------------- 批级标记


def test_no_cap_marker_loader_validation(tmp_path):
    """批级 no-cap 标记单一判据源:缺席 ⇒ None;合法 ⇒ 归一对象;
    坏 JSON/schema/mode/日期/marker/原文 ⇒ fail-closed 拒(不当缺席)。"""
    root = tmp_path / "batch"
    root.mkdir()
    assert load_budget_no_cap_marker(root) is None
    marker = write_no_cap_marker(root)
    loaded = load_budget_no_cap_marker(root)
    assert loaded == {
        "schema": "v44-budget-no-cap-1",
        "budget_mode": BUDGET_MODE_NO_CAP,
        "user_decision_date": NO_CAP_DECISION_DATE,
        "user_decision_record": NO_CAP_USER_DECISION,
        "marker": no_cap_marker_string(NO_CAP_DECISION_DATE),
    }
    for field in ("bad_json", "schema", "budget_mode",
                  "user_decision_date", "marker",
                  "user_decision_record"):
        root2 = tmp_path / f"batch_bad_{field}"
        root2.mkdir()
        write_no_cap_marker(root2, malformed=field)
        with pytest.raises(S5bOrchestratorError) as exc:
            load_budget_no_cap_marker(root2)
        assert exc.value.detail["kind"] == \
            "s5b_budget_no_cap_marker_invalid"
    del marker


def test_cli_budget_no_cap_mode_write_idempotent_and_conflicts(
        tmp_path, capsys):
    """s5b_cli budget --budget-mode:落标记(不落价格快照);同决定幂等;
    改决定/与数值守卫互斥 ⇒ 拒;数值参数同给/缺决定字段 ⇒ 拒。"""
    root = tmp_path / "cli_batch"
    root.mkdir()
    code = s5b_cli.main([
        "budget", "--batch-root", str(root),
        "--budget-mode", BUDGET_MODE_NO_CAP,
        "--user-decision-date", NO_CAP_DECISION_DATE,
        "--user-decision-record", NO_CAP_USER_DECISION])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["budget_mode"] == BUDGET_MODE_NO_CAP
    assert payload["marker"] == no_cap_marker_string(
        NO_CAP_DECISION_DATE)
    marker_path = root / S5B_BUDGET_NO_CAP_FILE
    assert marker_path.is_file()
    # no-cap 不写价格快照(无价)
    assert not (root / "price_snapshot.json").exists()
    assert not (root / "budget_guard.json").exists()
    # 同决定幂等
    code = s5b_cli.main([
        "budget", "--batch-root", str(root),
        "--budget-mode", BUDGET_MODE_NO_CAP,
        "--user-decision-date", NO_CAP_DECISION_DATE,
        "--user-decision-record", NO_CAP_USER_DECISION])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload.get("idempotent") is True
    # 改决定 ⇒ 拒(须新批根)
    code = s5b_cli.main([
        "budget", "--batch-root", str(root),
        "--budget-mode", BUDGET_MODE_NO_CAP,
        "--user-decision-date", "2026-10-13",
        "--user-decision-record", NO_CAP_USER_DECISION])
    assert code == 3
    capsys.readouterr()
    # no-cap 模式给数值金额参数 ⇒ 模式矛盾拒
    root2 = tmp_path / "cli_batch2"
    root2.mkdir()
    code = s5b_cli.main([
        "budget", "--batch-root", str(root2),
        "--budget-mode", BUDGET_MODE_NO_CAP,
        "--user-decision-date", NO_CAP_DECISION_DATE,
        "--user-decision-record", NO_CAP_USER_DECISION,
        "--input-per-mtok", "0.8"])
    assert code == 2
    capsys.readouterr()
    # 缺决定字段 ⇒ 拒(用户决定是跳过金额守卫的合法性来源)
    code = s5b_cli.main([
        "budget", "--batch-root", str(tmp_path / "cli_batch3"),
        "--budget-mode", BUDGET_MODE_NO_CAP])
    assert code == 2
    capsys.readouterr()
    # 数值守卫在先,改 no-cap ⇒ 拒(模式不静默切换)
    root4 = tmp_path / "cli_batch4"
    root4.mkdir()
    s5b_cli.main(["budget", "--batch-root", str(root4),
                  "--input-per-mtok", "0.8",
                  "--output-per-mtok", "2.8"])
    capsys.readouterr()
    code = s5b_cli.main([
        "budget", "--batch-root", str(root4),
        "--budget-mode", BUDGET_MODE_NO_CAP,
        "--user-decision-date", NO_CAP_DECISION_DATE,
        "--user-decision-record", NO_CAP_USER_DECISION])
    assert code == 3


def test_run_s5b_batch_no_cap_marker_gates(tmp_path, clean_llm_env):
    """编排器金额守卫门:real 批无守卫无标记 ⇒ 拒(原行为);
    合法标记 ⇒ 放行(金额门跳过;调用数门照常;批报告披露
    budget_mode);标记+数值守卫并存 ⇒ 互斥拒。worker 子进程无
    V43_LLM 凭证 ⇒ model_not_configured 失败题留分母,零网络。"""
    from pathway_v43.pollutant.s5b_builder import build_question_batch
    from pathway_v43.pollutant.s5b_orchestrator import run_s5b_batch

    def _build(arm: str) -> Path:
        questions = tmp_path / f"q_{arm}.jsonl"
        questions.write_text(json.dumps({
            "qid": "SYNTH-NOCAP-Q1", "substrate_smiles": "CCO",
            "products_smiles": ["CC=O"]}) + "\n", encoding="utf-8")
        root = tmp_path / f"batch_{arm}"
        build_question_batch(
            questions, root, batch_tag=f"nocap-{arm}",
            pool_provider=None, provider_kind="real")
        return root

    # ① 原行为回归:real 批缺守卫且无标记 ⇒ s5b_budget_guard_missing
    root_missing = _build("missing")
    with pytest.raises(S5bOrchestratorError) as exc:
        run_s5b_batch(root_missing, runs_root=tmp_path / "runs_missing",
                      workers=1, poll_s=0.2)
    assert exc.value.detail["kind"] == "s5b_budget_guard_missing"
    # ② 互斥:数值守卫 + no-cap 标记并存 ⇒ 拒
    root_conflict = _build("conflict")
    write_no_cap_marker(root_conflict)
    (root_conflict / "budget_guard.json").write_text(
        json.dumps(budget_guard_raw()), encoding="utf-8")
    with pytest.raises(S5bOrchestratorError) as exc:
        run_s5b_batch(root_conflict,
                      runs_root=tmp_path / "runs_conflict",
                      workers=1, poll_s=0.2)
    assert exc.value.detail["kind"] == "s5b_budget_mode_conflict"
    # ③ no-cap 合法标记 ⇒ 金额门放行;批跑完(无凭证 ⇒ 失败题留
    # 分母,零 HTTP);批报告披露 budget_mode;闸门无金额块
    root_ok = _build("ok")
    write_no_cap_marker(root_ok)
    report = run_s5b_batch(root_ok, runs_root=tmp_path / "runs_ok",
                           workers=1, poll_s=0.2, gate_max_calls=10)
    assert report["budget_mode"] == BUDGET_MODE_NO_CAP
    assert report["n_failed"] == 1
    case = json.loads(
        (root_ok / "cases" / "SYNTH-NOCAP-Q1.json").read_text(
            encoding="utf-8"))
    assert case["status"] == "failed"
    assert case["failure_kind"] == "model_not_configured"
    gate_state = json.loads(
        (root_ok / "gate" / "gate.json").read_text(encoding="utf-8"))
    assert "cost_guard" not in gate_state  # 金额闸门未启用(显式跳过)
    assert gate_state["max_calls"] == 10   # 调用数门照常冻结


def test_worker_verify_budget_guard_no_cap_marker(tmp_path, clean_llm_env):
    """worker 侧守卫核对(同判据):闸门无金额配置 + 合法标记 ⇒ 通过;
    无标记 ⇒ budget_guard_missing(原行为);数值闸门 + 标记 ⇒ 冲突;
    坏标记 ⇒ budget_guard_invalid(不当缺席)。"""
    from types import SimpleNamespace

    root = tmp_path / "batch"
    root.mkdir()
    gate_nocap = FileRateGate(tmp_path / "gate_nocap", rpm=10,
                              tpm=100000, max_calls=10, max_in_flight=2,
                              cost_guard=None)
    model = SimpleNamespace(client=SimpleNamespace(gate=gate_nocap))
    # 无标记 ⇒ 原拒绝不变
    verdict = _verify_budget_guard(root, model, "real")
    assert verdict is not None
    assert verdict["failure_kind"] == "budget_guard_missing"
    # 合法标记 ⇒ 通过(None)
    write_no_cap_marker(root)
    assert _verify_budget_guard(root, model, "real") is None
    # 坏标记 ⇒ fail-closed 拒(标记不当缺席)
    write_no_cap_marker(root, malformed="marker")
    verdict = _verify_budget_guard(root, model, "real")
    assert verdict["failure_kind"] == "budget_guard_invalid"
    # 数值闸门 + 标记 ⇒ 互斥冲突(单一事实源破裂)
    write_no_cap_marker(root)
    gate_num = FileRateGate(tmp_path / "gate_num", rpm=10, tpm=100000,
                            max_calls=10, max_in_flight=2,
                            cost_guard=normalize_cost_guard_config(
                                budget_guard_raw()))
    model_num = SimpleNamespace(client=SimpleNamespace(gate=gate_num))
    verdict = _verify_budget_guard(root, model_num, "real")
    assert verdict["failure_kind"] == "budget_guard_mismatch"
    # scripted 桩路径不经核对(原行为)
    assert _verify_budget_guard(root, model, "scripted") is None
