"""chain14 发车物测试(证据卡批级开关 + transport 重试 + 发车族冒烟;
任务书 TASK_CHAIN14_LAUNCH_2026-10-15 §三;预注册
CHAIN14_EVIDENCE_AB_PREREG_2026-10-15 已确认生效)。

三组验收(任务书 §三):
- **开关正负控**:off ⇒ decide 载荷与证据卡实施前四字段形状**逐字节
  相等**(重构旧形状字面断言);on/缺省 ⇒ evidence/substrate_evidence/
  schema 版本在位且与显式 on 字节全等;非法值 ⇒ 结构化拒;
  orchestration 冻结后改参即拒;worker 侧冻结副本缺键/坏值
  fail-closed(P1-4 回修:可信批上下文显式传预期 bool,冻结副本
  缺席=拒不回退;手动/测试直连缺席 = 显式手动模式披露);
- **重试正负控**(双臂共享):首败 transport_error ⇒ 重试 1 次成功
  (retry_of 链接 + http_attempts 两请求合计 2);两连败 ⇒ 现行失败
  语义(零静默吞);timeout/forbidden_permanent 不重试;每题预算拒不
  掩盖原失败(每题 max_real_model_requests 语义不变);格式反馈轮的
  传输重试不越 max_format_feedback_rounds;P1-1 回修:反馈轮沿实际
  provider_kind 登记,真实组合路径第 4 次发送前被每题预算拦截;
  P1-2 回修:重试成功的完整 blob 可崩溃重放(来源→唯一重试终态链,
  零新增调用),坏 blob/错身份仍拒;
- **发车物冒烟**:sbatch_chain14_{build,run,score}.sh 在位 + bash 语法
  + ARM→开关映射(本地零提交,只读校验)。

环境纪律:零模型零网络零金标零题面(scripted 桩同载荷路径;合成分子
与真实 298 零重叠);PYTHONDONTWRITEBYTECODE 由运行环境保证。
"""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pathway_v43.config import resolve_config  # noqa: E402
from pathway_v43.pollutant.chemstate import (  # noqa: E402
    build_chemical_state,
)
from pathway_v43.pollutant.model_protocol import (  # noqa: E402
    format_feedback_rounds_used,
)
from pathway_v43.pollutant.production import prepare_hypothesis  # noqa: E402
from pathway_v43.pollutant.real_model import (  # noqa: E402
    PROPOSALS_PROMPT_VERSION,
    S5B_TRANSPORT_RETRY_MAX,
    ScriptedRealModelAdapter,
    TRANSPORT_RETRY_KEY_SUFFIX,
    TRANSPORT_RETRYABLE_ERROR_KINDS,
    _PROPOSALS_SYSTEM_PROMPT,
    build_proposals_user_payload,
    execution_graph_payload,
    substrate_atom_id_map,
)
from pathway_v43.pollutant.runflow import (  # noqa: E402
    PPV1RunError,
    resume_ppv1_run,
    start_ppv1_run,
)
from pathway_v43.pollutant.s5b_builder import (  # noqa: E402
    build_question_batch,
)
from pathway_v43.pollutant.s5b_orchestrator import (  # noqa: E402
    S5B_CASE_SCHEMA_VERSION,
    S5B_DEFAULT_PROFILE_POLICY,
    load_evidence_card_flag,
    run_s5b_batch,
    summarize_batch,
    validate_case,
)
from pathway_v43.domain.models import stable_id  # noqa: E402

# 与真实 298 集合零重叠的合成池条目(沿 tests/test_ppv1_s5b_candidate_
# evidence.py 同款夹具;合成 record id 不指涉任何真实记录)
SYNTH_SPEC = {
    "key": "rec-SYNTH_REC_0001@L3", "product_smiles": "CC=O",
    "coefficient": 1,
    "transformation_ref": "SYNTH_REC_0001@L3",
    "origin_group_key": "rec-source:SYNTH_REC_0001@L3",
    "edits": [
        {"op": "change_bond_order", "atom1": "S_C_2",
         "atom2": "S_O_1", "from_order": "single",
         "to_order": "double"},
        {"op": "add_atom", "element": "O",
         "new_atom_id": "SN_O_1", "atom1": "S_C_2"},
    ],
    "donor": {"center_atom_ids": ["S_C_2", "S_O_1"]},
    "alignment": {
        "status": "resolved",
        "donor_to_current": {"S_C_2": "S_C_2", "S_O_1": "S_O_1"},
        "equivalence_classes": [],
        "ref": "recorded-inferred:SYNTH_REC_0001@L3"},
    "expectation": {"target_smiles": "CC=O"},
    "compile": {
        "compiler_version": "synthetic", "mapping_origin": "inferred",
        "n_alignments_total": 2, "n_equivalent_alignments": 2,
        "truncated": False, "template_center_maps": [1, 2]},
    "requirements": [
        {"key": "oxygen_regime", "level": "preference",
         "value": "aerobic", "basis": "observed_condition_reference"}],
}


def _profile(max_real: int = 3, feedback_rounds: int = 0) -> dict:
    """run 级策略(每题真实请求额度可调;格式反馈轮可调)。"""
    return {
        "search_limits": {
            **S5B_DEFAULT_PROFILE_POLICY["search_limits"],
            "max_real_model_requests": int(max_real),
        },
        "format_feedback_policy": {
            "max_format_feedback_rounds": int(feedback_rounds),
        },
    }


def _driver_inputs(run_id: str):
    """decide 载荷重构所需的同源输入(镜像 _run_decide 的装配口径)。"""
    root_path = stable_id("spath", run_id, "root")
    substrate = build_chemical_state(
        "CCO", "raw_input", [{"record": f"ppv1-substrate:{run_id}"}])
    prepared = prepare_hypothesis(
        dict(SYNTH_SPEC), parent_path_id=root_path,
        substrate_state=substrate,
        transformation_ref=str(SYNTH_SPEC.get("transformation_ref") or ""))
    return prepared["hypothesis"].hypothesis_id


class _SeqTransportStub(ScriptedRealModelAdapter):
    """complete 调用序 1..N 中指定序号按给定 error_kind 传输失败,其余
    按 responses 序列消费(耗尽 ⇒ 合法弃权)。**与真实适配器同一
    ppv1_real_fetch 取响应调用序** —— chain14 重试裁定在父类,桩内
    零重试逻辑(不冒充被测行为)。"""

    def __init__(self, *, fail_on_calls=(1,), fail_kind="transport_error",
                 responses=None, model_id="chain14-seq-stub", **kwargs):
        super().__init__(strategy="responses", responses=responses,
                         model_id=model_id, **kwargs)
        self.fail_on_calls = tuple(int(c) for c in fail_on_calls)
        self.fail_kind = str(fail_kind)
        self.complete_calls = 0

    def _complete(self, *, system_prompt, user_payload, idempotency_key):
        from pathway_v43.adapters.llm_client import LLMResponse

        self.complete_calls += 1
        if self.complete_calls in self.fail_on_calls:
            return LLMResponse(
                ok=False, error_kind=self.fail_kind,
                error_message="chain14-stub-transport-failure",
                http_attempts=[{"status": 502, "attempt": 1,
                                "error_kind": self.fail_kind}])
        response = super()._complete(
            system_prompt=system_prompt, user_payload=user_payload,
            idempotency_key=idempotency_key)
        # 成功尝试同样携带逐 HTTP 尝试留痕(每次到达提供者的尝试一条)
        response.http_attempts = [{"status": 200, "attempt": 1,
                                   "note": "chain14-stub-ok"}]
        return response


def _request_rows(runs_root: Path, run_id: str) -> list[tuple]:
    db = runs_root / run_id / "pollutant.sqlite"
    conn = sqlite3.connect(str(db))
    try:
        rows = conn.execute(
            "SELECT request_id, status, retry_of, purpose FROM"
            " model_requests").fetchall()
    finally:
        conn.close()
    # 确定序:来源行在前、重试行在后(created_at 秒级精度,同秒插入序
    # 不能作为判据;purpose 再排 = decide 先于 format_feedback)
    return sorted(rows, key=lambda r: (1 if r[2] else 0, r[3]))


def _account_records(runs_root: Path, run_id: str) -> list[dict]:
    path = runs_root / run_id / "s5b_real_calls.jsonl"
    if not path.is_file():
        return []
    return [json.loads(line) for line in
            path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _start_run(tmp_path: Path, run_id: str, model, *,
               evidence_card_enabled=None, profile=None,
               runs_subdir: str = "runs", provider_kind: str = "scripted",
               crash_after: str | None = None):
    return start_ppv1_run(
        config=resolve_config(), runs_root=tmp_path / runs_subdir,
        run_id=run_id, smiles="CCO",
        plan={"pools": {"CCO": [dict(SYNTH_SPEC)]},
              "model": {"provider_kind": provider_kind}},
        model=model, profile_policy=profile or _profile(),
        evidence_card_enabled=evidence_card_enabled, scripted=True,
        crash_after=crash_after)


# ================================================================ 开关


def test_evidence_flag_off_payload_byte_equal_pre_evidence_shape(
        tmp_path) -> None:
    """负控(A 臂):开关 off ⇒ decide 载荷与证据卡实施前四字段形状
    **逐字节相等**(重构旧形状字面断言;顶层/池条目键集精确)。"""
    run_id = "chain14-arm-a-bytes"
    model = _SeqTransportStub(
        responses=[json.dumps({"proposals": [], "rank_hypotheses": []})],
        model_id=run_id)
    out = _start_run(tmp_path, run_id, model, evidence_card_enabled=False)
    assert out["native_export"]["export_digest"]
    assert len(model.seen_user_payloads) == 1
    raw = model.seen_user_payloads[0]
    # 证据键零出现(载荷 = 实施前形状)
    assert '"evidence"' not in raw
    assert '"substrate_evidence"' not in raw
    assert "candidate_evidence_schema_version" not in raw
    # 重构证据卡实施前的四字段形状(同源输入 ⇒ 同 hypothesis_id)
    hyp_id = _driver_inputs(run_id)
    expected = json.dumps({
        "substrate_smiles": "CCO",
        "substrate_atom_id_map": substrate_atom_id_map("CCO"),
        "pool_hypotheses": [{
            "hypothesis_id": hyp_id,
            "product_smiles": SYNTH_SPEC["product_smiles"],
            "transformation_ref": SYNTH_SPEC["transformation_ref"],
            "coproducts": []}],
        "protocol_version": "s5b-real-model-1",
        "execution_graph": execution_graph_payload("CCO"),
    }, ensure_ascii=False, sort_keys=True)
    assert raw == expected, "A 臂载荷必须与实施前逐字节相等"
    payload = json.loads(raw)
    assert set(payload.keys()) == {
        "substrate_smiles", "substrate_atom_id_map", "pool_hypotheses",
        "protocol_version", "execution_graph"}
    assert set(payload["pool_hypotheses"][0].keys()) == {
        "hypothesis_id", "product_smiles", "transformation_ref",
        "coproducts"}


def test_evidence_flag_on_and_default_identical_payload(tmp_path) -> None:
    """正控(B 臂):显式 on 与缺省(None)载荷**字节全等**,且携带
    evidence/substrate_evidence/schema 版本(现行 candidate-evidence-2
    行为;缺省只为既有直连调用方兼容保留,值=现行行为 on)。"""
    payloads = {}
    for tag, flag in (("explicit-on", True), ("default", None)):
        # 同 run_id(内容派生假设 ID 同源)+ 不同 runs 根 ⇒ 载荷可逐字节比
        run_id = "chain14-arm-b"
        model = _SeqTransportStub(
            responses=[json.dumps(
                {"proposals": [], "rank_hypotheses": []})],
            model_id=f"chain14-b-{tag}")
        out = _start_run(tmp_path, run_id, model,
                         evidence_card_enabled=flag,
                         runs_subdir=f"runs-{tag}")
        assert out["native_export"]["export_digest"]
        assert out["evidence_card_enabled"] is True
        payloads[tag] = model.seen_user_payloads[0]
    assert payloads["explicit-on"] == payloads["default"], \
        "显式 on 与缺省载荷必须字节全等(缺省=现行行为)"
    payload = json.loads(payloads["explicit-on"])
    entry = payload["pool_hypotheses"][0]
    assert set(entry.keys()) == {
        "hypothesis_id", "product_smiles", "transformation_ref",
        "coproducts", "evidence"}
    assert entry["evidence"]["source"]["source_kind"] == "recorded_inferred"
    assert payload["candidate_evidence_schema_version"] == \
        "candidate-evidence-2"
    assert payload["substrate_evidence"]["molecular_formula"] == "C2H6O"


def test_prompt_and_identity_same_both_arms(tmp_path) -> None:
    """两臂提示词同版:PROPOSALS_PROMPT_VERSION 单一常量,开关不入
    提示词/模型身份块(A/B 唯一差分 = 用户载荷证据字段)。"""
    assert PROPOSALS_PROMPT_VERSION == __import__("hashlib").sha256(
        _PROPOSALS_SYSTEM_PROMPT.encode("utf-8")).hexdigest()
    assert "evidence_card_enabled" not in _PROPOSALS_SYSTEM_PROMPT
    for flag in (True, False):
        stub = _SeqTransportStub(responses=[], model_id="chain14-prompt")
        block = stub.identity_block()
        assert block["prompt_versions"]["proposals"] == \
            PROPOSALS_PROMPT_VERSION
        assert "evidence_card_enabled" not in json.dumps(block)


def test_evidence_flag_invalid_rejected_at_run_entry(tmp_path) -> None:
    """负控:开关非法值(非 bool)⇒ run 入口结构化拒(fail-closed)。"""
    model = _SeqTransportStub(responses=[], model_id="chain14-badflag")
    with pytest.raises(PPV1RunError) as excinfo:
        _start_run(tmp_path, "chain14-badflag", model,
                   evidence_card_enabled="false")
    assert excinfo.value.detail["kind"] == "evidence_card_flag_invalid"


def test_resume_evidence_flag_mismatch_rejected(tmp_path) -> None:
    """resume 开关核对:与 run 启动时不同臂 ⇒ 结构化拒;同臂幂等续跑。"""
    run_id = "chain14-resume-flag"
    start_model = _SeqTransportStub(
        responses=[json.dumps({"proposals": [], "rank_hypotheses": []})],
        model_id="chain14-resume-stub")
    _start_run(tmp_path, run_id, start_model, evidence_card_enabled=False)
    # 不同臂 resume ⇒ 拒(载荷口径中途换臂禁止)
    flip = _SeqTransportStub(responses=[], model_id="chain14-resume-stub")
    with pytest.raises(PPV1RunError) as excinfo:
        resume_ppv1_run(
            config=resolve_config(), runs_root=tmp_path / "runs",
            run_id=run_id, model=flip, evidence_card_enabled=True)
    assert excinfo.value.detail["kind"] == "evidence_card_flag_mismatch"
    # 同臂 resume ⇒ 幂等续跑(已完成 run 再驱动零新增)
    same = _SeqTransportStub(responses=[], model_id="chain14-resume-stub")
    out = resume_ppv1_run(
        config=resolve_config(), runs_root=tmp_path / "runs",
        run_id=run_id, model=same, evidence_card_enabled=False)
    assert out["evidence_card_enabled"] is False
    assert out["native_export"]["export_digest"]


# ------------------------------------------------- 批级(orchestrator)


def _scripted_batch(tmp_path: Path, tag: str) -> Path:
    questions = tmp_path / f"q-{tag}.jsonl"
    questions.write_text(json.dumps(
        {"qid": "SYNTH-C14-1", "substrate_smiles": "CCO",
         "products_smiles": ["CC=O"], "raw_reaction": "CCO>>CC=O"}) + "\n",
        encoding="utf-8")
    batch_root = tmp_path / f"batch-{tag}"
    build_question_batch(
        questions, batch_root, batch_tag=f"chain14-{tag}",
        pool_provider=lambda s: [dict(SYNTH_SPEC)],
        provider_kind="scripted", synthetic_review=True)
    return batch_root


def test_orchestrator_freezes_flag_and_rejects_change(tmp_path) -> None:
    """批级冻结:发车参数冻结进 orchestration.json + 批报告披露 +
    case 披露;同批根改参即拒;非法值结构化拒;缺省冻结 True。"""
    stub_path = tmp_path / "stub.json"
    stub_path.write_text(json.dumps({"strategy": "first_pool"}),
                         encoding="utf-8")
    old = os.environ.get("S5B_MODEL_STUB_SCRIPT")
    os.environ["S5B_MODEL_STUB_SCRIPT"] = str(stub_path)
    try:
        batch_root = _scripted_batch(tmp_path, "off")
        report = run_s5b_batch(
            batch_root, runs_root=tmp_path / "runs-off", workers=1,
            poll_s=0.2, gate_max_calls=50, evidence_card_enabled=False)
        # 冻结 + 双面披露
        frozen = json.loads(
            (batch_root / "orchestration.json").read_text())
        assert frozen["evidence_card_enabled"] is False
        assert report["evidence_card_enabled"] is False
        case = json.loads(
            (batch_root / "cases" / "SYNTH-C14-1.json").read_text())
        assert case["status"] == "completed"
        assert case["evidence_card_enabled"] is False
        # 同批根改参(换臂)即拒:改参须新批根(预注册纪律)
        with pytest.raises(Exception) as excinfo:  # noqa: B017
            run_s5b_batch(
                batch_root, runs_root=tmp_path / "runs-off", workers=1,
                poll_s=0.2, gate_max_calls=50, evidence_card_enabled=True)
        assert excinfo.value.detail["kind"] == "s5b_orchestration_conflict"
        # 非法值(非 bool)⇒ 结构化拒(fail-closed,不猜)
        bad_root = _scripted_batch(tmp_path, "bad")
        with pytest.raises(Exception) as excinfo:  # noqa: B017
            run_s5b_batch(
                bad_root, runs_root=tmp_path / "runs-bad", workers=1,
                poll_s=0.2, gate_max_calls=50,
                evidence_card_enabled="false")
        assert excinfo.value.detail["kind"] == \
            "s5b_evidence_card_flag_invalid"
        # 缺省(None)⇒ 冻结 True(现行行为;A/B 两臂发车恒显式传值)
        default_root = _scripted_batch(tmp_path, "default")
        run_s5b_batch(
            default_root, runs_root=tmp_path / "runs-default", workers=1,
            poll_s=0.2, gate_max_calls=50)
        frozen_default = json.loads(
            (default_root / "orchestration.json").read_text())
        assert frozen_default["evidence_card_enabled"] is True
    finally:
        if old is None:
            os.environ.pop("S5B_MODEL_STUB_SCRIPT", None)
        else:
            os.environ["S5B_MODEL_STUB_SCRIPT"] = old


def test_worker_fails_closed_on_frozen_flag_missing_or_bad(
        tmp_path, monkeypatch) -> None:
    """worker 侧同判据核对(沿 no-cap 先例):冻结副本缺键/坏值 ⇒
    结构化失败 case(零发送);副本缺席(手动/测试直连路径,未传预期
    值)⇒ 显式进手动模式(case 披露 on + manual_no_frozen_copy)。"""
    from pathway_v43.pollutant.s5b_worker import worker_main

    stub_path = tmp_path / "stub.json"
    stub_path.write_text(json.dumps({"strategy": "first_pool"}),
                         encoding="utf-8")
    monkeypatch.setenv("S5B_MODEL_STUB_SCRIPT", str(stub_path))
    for tag, orchestration in (
            ("nokey", {"orchestrator_version": "s5b-orchestrator-3"}),
            ("badvalue", {"evidence_card_enabled": "false"})):
        batch_root = _scripted_batch(tmp_path, f"worker-{tag}")
        (batch_root / "profile_policy.json").write_text(
            json.dumps(S5B_DEFAULT_PROFILE_POLICY), encoding="utf-8")
        (batch_root / "orchestration.json").write_text(
            json.dumps(orchestration), encoding="utf-8")
        rc = worker_main(["--batch-root", str(batch_root),
                          "--runs-root", str(tmp_path / f"runs-{tag}"),
                          "--qid", "SYNTH-C14-1"])
        assert rc == 5, tag
        case = json.loads(
            (batch_root / "cases" / "SYNTH-C14-1.json").read_text())
        assert case["status"] == "failed", tag
        assert case["failure_kind"] == "evidence_card_flag_invalid", tag
    # 副本缺席 + 未传预期值 ⇒ 显式手动模式(现行行为 on;case 披露)
    batch_root = _scripted_batch(tmp_path, "worker-absent")
    (batch_root / "profile_policy.json").write_text(
        json.dumps(S5B_DEFAULT_PROFILE_POLICY), encoding="utf-8")
    assert not (batch_root / "orchestration.json").exists()
    rc = worker_main(["--batch-root", str(batch_root),
                      "--runs-root", str(tmp_path / "runs-absent"),
                      "--qid", "SYNTH-C14-1"])
    assert rc == 0
    case = json.loads(
        (batch_root / "cases" / "SYNTH-C14-1.json").read_text())
    assert case["status"] == "completed"
    assert case["evidence_card_enabled"] is True
    assert case["evidence_card_mode"] == "manual_no_frozen_copy"


def test_load_evidence_card_flag_loader_contract(tmp_path) -> None:
    """单一验证源契约:缺席 ⇒ None;在场合法 ⇒ bool;不可解析/缺键/
    坏值 ⇒ 结构化拒(worker/orchestrator 共用,不各写一套)。"""
    root = tmp_path / "b"
    root.mkdir()
    assert load_evidence_card_flag(root) is None  # 缺席
    (root / "orchestration.json").write_text(
        json.dumps({"evidence_card_enabled": False}), encoding="utf-8")
    assert load_evidence_card_flag(root) is False
    for tag, text in (
            ("bad-json", "{not json"),
            ("missing-key", json.dumps({"workers": 1})),
            ("bad-type", json.dumps({"evidence_card_enabled": 1}))):
        (root / "orchestration.json").write_text(text, encoding="utf-8")
        with pytest.raises(Exception) as excinfo:  # noqa: B017
            load_evidence_card_flag(root)
        assert excinfo.value.detail["kind"] == \
            "s5b_evidence_card_flag_invalid", tag


# ================================================================ 重试


def test_transport_retry_first_fails_then_success(tmp_path) -> None:
    """正控:首发 transport_error 失败 ⇒ 自动重试 1 次成功 ⇒ 题成功;
    retry_of 链接 + 新 request_key;两请求 http_attempts 合计 2
    (每次 HTTP 尝试 = 一次 issued 请求,诚实计数)。"""
    run_id = "chain14-retry-ok"
    model = _SeqTransportStub(
        fail_on_calls=(1,), fail_kind="transport_error",
        responses=[json.dumps({"proposals": [], "rank_hypotheses": []})],
        model_id="chain14-retry-ok",
        call_account_path=tmp_path / "runs" / run_id /
        "s5b_real_calls.jsonl")
    out = _start_run(tmp_path, run_id, model, profile=_profile(max_real=3))
    assert out["native_export"]["export_digest"]
    assert model.complete_calls == 2  # 首发 + 重试(每逻辑调用至多 1 次)
    rows = _request_rows(tmp_path / "runs", run_id)
    assert len(rows) == 2
    (id1, status1, retry_of1, _), (id2, status2, retry_of2, _) = rows
    assert status1 == "failed" and retry_of1 == ""
    assert status2 == "responded"
    assert retry_of2 == id1  # 重试显式链接首发(retry_of 记来源)
    # 账本留痕:重试签发记录(新键 = 首键 + 重试后缀)+ 两请求
    # http_attempts 合计 2(每次 HTTP 尝试 = 一次 issued 请求)
    records = _account_records(tmp_path / "runs", run_id)
    statuses = [r["status"] for r in records]
    assert "transport_retry_issued" in statuses
    retry_marks = [r for r in records
                   if r["status"] == "transport_retry_issued"]
    assert retry_marks[0]["retry_of"] == id1
    assert retry_marks[0]["request_key"].endswith(
        TRANSPORT_RETRY_KEY_SUFFIX)
    http_total = sum(len(r.get("http_attempts") or [])
                     for r in records
                     if r["status"] in ("failed", "responded"))
    assert http_total == 2


def test_transport_retry_two_failures_terminate_with_failure(
        tmp_path) -> None:
    """负控:两连败 ⇒ 现行失败语义(第二次失败为终态,零静默吞;
    失败题留分母,导出仍产出)。"""
    run_id = "chain14-retry-both-fail"
    model = _SeqTransportStub(
        fail_on_calls=(1, 2), fail_kind="transport_error",
        responses=[], model_id="chain14-retry-both-fail",
        call_account_path=tmp_path / "runs" / run_id /
        "s5b_real_calls.jsonl")
    out = _start_run(tmp_path, run_id, model, profile=_profile(max_real=3))
    assert out["stop"].get("run_error", {}).get("kind") == \
        "real_model_transport_failure"
    assert out["native_export"]["export_digest"]
    assert model.complete_calls == 2
    rows = _request_rows(tmp_path / "runs", run_id)
    assert len(rows) == 2
    assert all(status == "failed" for _, status, _, _ in rows)
    assert rows[1][2] != ""  # 第二败 = 显式重试行(retry_of 链接在案)
    statuses = [r["status"] for r in
                _account_records(tmp_path / "runs", run_id)]
    assert statuses.count("failed") == 2  # 两败各自留痕,无静默吞


def test_transport_retry_not_triggered_for_non_retryable_kinds(
        tmp_path) -> None:
    """负控(取舍面):timeout / forbidden_permanent 不重试(一次失败
    即现行语义;单请求零重试行)。"""
    for kind in ("timeout", "forbidden_permanent"):
        run_id = f"chain14-noretry-{kind}"
        model = _SeqTransportStub(
            fail_on_calls=(1,), fail_kind=kind, responses=[],
            model_id=f"chain14-noretry-{kind}")
        out = _start_run(tmp_path, run_id, model,
                         profile=_profile(max_real=3))
        assert out["stop"].get("run_error", {}).get("kind") == \
            "real_model_transport_failure", kind
        rows = _request_rows(tmp_path / "runs", run_id)
        assert len(rows) == 1, f"{kind} 不得触发重试"
        statuses = [r["status"] for r in
                    _account_records(tmp_path / "runs", run_id)]
        assert "transport_retry_issued" not in statuses, kind


def test_transport_retry_budget_refused_keeps_original_failure(
        tmp_path) -> None:
    """负控:每题剩余额度不足以登记重试(provider_kind=real 占额 +
    max_real_model_requests=1 ⇒ 首发后 remaining=0)⇒ 原传输失败语义
    保持(预算拒不掩盖原失败、不升格;每题上限语义不变,零静默吞)。
    注:额度占面只在 provider_kind=real(scripted 桩网络 0 不占额)。"""
    run_id = "chain14-retry-budget"
    model = _SeqTransportStub(
        fail_on_calls=(1,), fail_kind="transport_error", responses=[],
        model_id="chain14-retry-budget",
        call_account_path=tmp_path / "runs" / run_id /
        "s5b_real_calls.jsonl")
    out = _start_run(tmp_path, run_id, model, profile=_profile(max_real=1),
                     provider_kind="real")
    assert out["stop"].get("run_error", {}).get("kind") == \
        "real_model_transport_failure"
    rows = _request_rows(tmp_path / "runs", run_id)
    assert len(rows) == 1  # 重试未登记(不越每题 1 请求语义)
    statuses = [r["status"] for r in
                _account_records(tmp_path / "runs", run_id)]
    assert "transport_retry_budget_refused" in statuses
    assert statuses.count("failed") == 1  # 原失败保持为终态


def test_transport_retry_feedback_round_does_not_consume_extra_round(
        tmp_path) -> None:
    """反馈轮重试:格式反馈请求 transport 失败 ⇒ 重试 1 次成功;
    retry_of 链接;重试行不计入反馈轮数(max_format_feedback_rounds
    语义不变 —— 重试是同轮的第二次尝试,不是新的一轮)。"""
    from pathway_v43.pollutant.search import SearchLedger
    from pathway_v43.pollutant.store import PollutantPathwayStore
    from pathway_v43.storage.artifact_store import ArtifactStore

    run_id = "chain14-fb-retry"
    hyp_id = _driver_inputs(run_id)
    model = _SeqTransportStub(
        fail_on_calls=(2,), fail_kind="transport_error",
        responses=[
            # decide 首发:可解析但缺 proposals 键 ⇒ json_field(可进反馈)
            json.dumps({"proposal": []}),
            # 反馈重试:合法提案
            json.dumps({"proposals": [{"hypothesis_id": hyp_id}],
                        "rank_hypotheses": [hyp_id]}),
        ],
        model_id="chain14-fb-retry",
        call_account_path=tmp_path / "runs" / run_id /
        "s5b_real_calls.jsonl")
    out = _start_run(tmp_path, run_id, model,
                     profile=_profile(max_real=3, feedback_rounds=2))
    assert out["native_export"]["export_digest"]
    rows = _request_rows(tmp_path / "runs", run_id)
    assert len(rows) == 3  # decide + 反馈轮 + 反馈轮重试
    by_role = {
        ("feedback", True): None, ("feedback", False): None,
        ("decide", False): None}
    for rid, status, retry_of, purpose in rows:
        if purpose == "format_feedback":
            by_role[("feedback", bool(retry_of))] = (rid, status, retry_of)
        else:
            by_role[("decide", False)] = (rid, status, retry_of)
    id1, s1, _ = by_role[("decide", False)]
    id2, s2, r2 = by_role[("feedback", False)]
    id3, s3, r3 = by_role[("feedback", True)]
    assert s1 == "responded"
    assert s2 == "failed" and r2 == ""  # 反馈轮首发传输失败
    assert s3 == "responded"
    assert r3 == id2  # 反馈轮重试显式链接该轮首发
    # 轮数判据(持久事实源复算;与 model_protocol.format_feedback_
    # rounds_used 同一 SQL):重试行排除 ⇒ 仍为 1 轮
    conn = sqlite3.connect(
        str(tmp_path / "runs" / run_id / "pollutant.sqlite"))
    try:
        action_id = conn.execute(
            "SELECT action_id FROM model_requests WHERE"
            " purpose = 'format_feedback' LIMIT 1").fetchone()[0]
        counted = conn.execute(
            "SELECT COUNT(*) FROM model_requests WHERE action_id = ?"
            " AND purpose = 'format_feedback' AND retry_of = ''",
            (action_id,)).fetchone()[0]
        unfiltered = conn.execute(
            "SELECT COUNT(*) FROM model_requests WHERE action_id = ?"
            " AND purpose = 'format_feedback'",
            (action_id,)).fetchone()[0]
    finally:
        conn.close()
    assert (counted, unfiltered) == (1, 2)
    # 公开入口同判据(函数内 SQL 与上面同一判据)
    store = PollutantPathwayStore(
        tmp_path / "runs" / run_id / "pollutant.sqlite")
    ledger = SearchLedger(
        store, ArtifactStore(tmp_path / "runs", run_id), run_id)
    assert format_feedback_rounds_used(ledger, action_id) == 1


def test_transport_retry_constants_are_registration_faced() -> None:
    """重试面登记:每逻辑调用至多 1 次;重试族=传输不稳
    (transport_error/empty_response);timeout/鉴权付费/资源拒不入族。"""
    assert S5B_TRANSPORT_RETRY_MAX == 1
    assert TRANSPORT_RETRYABLE_ERROR_KINDS == frozenset(
        {"transport_error", "empty_response"})
    for excluded in ("timeout", "rate_limited_exhausted",
                     "forbidden_permanent", "forbidden_stopped_by_gate",
                     "budget_cost_exhausted", "budget_config_invalid",
                     "orphan_sent_without_blob", "blob_persistence_failed"):
        assert excluded not in TRANSPORT_RETRYABLE_ERROR_KINDS


# ================================================================ 发车物


def test_chain14_launch_family_scripts_materialized() -> None:
    """发车物冒烟(本地零提交):三 sbatch 脚本在位 + bash 语法过 +
    ARM 参数化正确(环境变量前置 + 双臂批根样例 + wrapper 臂映射)。"""
    hpc = Path(__file__).resolve().parents[1] / "scripts" / "hpc"
    for name in ("sbatch_chain14_build.sh", "sbatch_chain14_run.sh",
                 "sbatch_chain14_score.sh", "chain14_run_wrapper.py"):
        assert (hpc / name).is_file(), name
    for name in ("sbatch_chain14_build.sh", "sbatch_chain14_run.sh",
                 "sbatch_chain14_score.sh"):
        proc = subprocess.run(["bash", "-n", str(hpc / name)],
                              capture_output=True, text=True)
        assert proc.returncode == 0, f"{name}: {proc.stderr}"
    sys.path.insert(0, str(hpc))
    try:
        import chain14_run_wrapper as wrapper

        assert wrapper.EVIDENCE_CARD_BY_ARM == {"a": False, "b": True}
        # profile 沿 chain13 单一来源复用(每题≤3 真实调用 + 2 反馈轮)
        assert wrapper.CHAIN13_PROFILE["search_limits"][
            "max_real_model_requests"] == 3
        assert wrapper.CHAIN13_PROFILE["format_feedback_policy"][
            "max_format_feedback_rounds"] == 2
    finally:
        sys.path.remove(str(hpc))
    run_sh = (hpc / "sbatch_chain14_run.sh").read_text(encoding="utf-8")
    build_sh = (hpc / "sbatch_chain14_build.sh").read_text(encoding="utf-8")
    score_sh = (hpc / "sbatch_chain14_score.sh").read_text(encoding="utf-8")
    # ARM 环境变量前置 + 非法值拒 + 双臂批根/runs 样例
    for text in (build_sh, run_sh, score_sh):
        assert 'ARM="${ARM:?' in text
        assert 'case "$ARM" in a|b)' in text
        assert "chain14${ARM}_s5b_20261015" in text
    assert run_sh.count("chain14${ARM}_s5b_20261015") >= 2, \
        "批根与 runs 根都必须按臂派生"
    assert '--arm "$ARM"' in run_sh
    assert "budget_no_cap.json" in run_sh  # no-cap 流程沿 chain13
    assert "chain13_gate.py" in run_sh and "chain13_gate.py" in score_sh
    assert "chain13_score_v2.py" in score_sh  # v2 headline 沿 chain13
    assert ".v1" in score_sh  # v1 改名敏感性口径
    # wrapper 臂映射样例(发车参数随臂冻结,worker 无选择权)
    wrapper_text = (hpc / "chain14_run_wrapper.py").read_text(
        encoding="utf-8")
    assert '"a": False, "b": True' in wrapper_text
    assert "evidence_card_enabled=evidence_card_enabled" in wrapper_text


# ================================================================ P1 回修轮
# (TASK_CHAIN14_P1FIX_2026-10-16;Codex 代审 CHAIN14_LAUNCH_CODEX_REVIEW_
# 2026-10-16 四项 P1。合成验证:零金标零题面零模型零网络 —— 真实
# client/gate 仅 urllib.urlopen 换本地桩。)


def _db_rows(runs_root: Path, run_id: str, sql: str,
             params: tuple = ()) -> list[dict]:
    db = runs_root / run_id / "pollutant.sqlite"
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()


def _db_exec(runs_root: Path, run_id: str, sql: str,
             params: tuple = ()) -> None:
    db = runs_root / run_id / "pollutant.sqlite"
    conn = sqlite3.connect(str(db))
    try:
        conn.execute(sql, params)
        conn.commit()
    finally:
        conn.close()


# ------------------------------------------------- P1-1(反馈预算)

_P1_1_GOOD = json.dumps({"proposals": [], "rank_hypotheses": []})
_P1_1_BAD = json.dumps({"proposal": []})


class _StubHTTPResponse:
    status = 200
    headers: dict = {}

    def __init__(self, content: str):
        self.content = content

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def read(self):
        return json.dumps(
            {"choices": [{"message": {"content": self.content}}],
             "usage": {"prompt_tokens": 12, "completion_tokens": 3,
                       "total_tokens": 15}}).encode()


def _real_http_case(tmp_path: Path, tag: str, sequence: list,
                    max_real: int, feedback_rounds: int = 2):
    """真实 RealModelAdapter+OpenAICompatibleClient+FileRateGate;仅
    urllib.urlopen 换本地桩(零网络;沿评审探针 probe_http_gate 手法)。"""
    import io
    import urllib.error
    from unittest.mock import patch

    from pathway_v43.adapters.llm_client import OpenAICompatibleClient
    from pathway_v43.adapters.rate_gate import FileRateGate
    from pathway_v43.pollutant.real_model import RealModelAdapter

    for key in ("V43_LLM_REQUEST_PARAMS", "V43_LLM_RATE_GATE",
                "V43_LLM_TIMEOUT_S"):
        os.environ.pop(key, None)
    outroot = tmp_path / f"pg-{tag}"
    runs = outroot / "runs"
    gate = FileRateGate(outroot / "gate", rpm=100000, tpm=10 ** 9,
                        max_calls=50, cooldown_cap_s=0, max_in_flight=8)
    client = OpenAICompatibleClient(
        base_url="https://synthetic.invalid", api_key="synthetic-key",
        model="audit-http-stub", timeout_s=1, request_params={}, gate=gate,
        max_http_retries=4)
    adapter = RealModelAdapter(
        client, call_account_path=runs / tag / "s5b_real_calls.jsonl")
    seq = list(sequence)
    http: list = []

    def fake_urlopen(req, timeout):
        item = seq.pop(0)
        http.append(item if isinstance(item, int) else 200)
        if isinstance(item, int):
            raise urllib.error.HTTPError(
                req.full_url, item, "synthetic HTTP error",
                {"Retry-After": "0.001"}, io.BytesIO(b""))
        return _StubHTTPResponse(item)

    with patch("pathway_v43.adapters.llm_client.urllib.request.urlopen",
               fake_urlopen):
        summary = start_ppv1_run(
            config=resolve_config(), runs_root=runs, run_id=tag,
            smiles="CCO",
            plan={"pools": {"CCO": [dict(SYNTH_SPEC)]},
                  "model": {"provider_kind": "real"}},
            model=adapter,
            profile_policy=_profile(max_real=max_real,
                                    feedback_rounds=feedback_rounds),
            scripted=True, evidence_card_enabled=False)
    requests = _db_rows(runs, tag, "SELECT rowid, request_id, status,"
                        " provider_kind, purpose, retry_of,"
                        " network_request_count FROM model_requests"
                        " ORDER BY rowid")
    reservations = _db_rows(
        runs, tag, "SELECT reservation_id FROM budget_reservations"
        " WHERE limit_key = 'max_real_model_requests'")
    account_path = runs / tag / "s5b_real_calls.jsonl"
    account = [json.loads(line) for line in
               account_path.read_text(encoding="utf-8").splitlines()
               if line.strip()] if account_path.is_file() else []
    return {"summary": summary, "http": http, "gate": gate.snapshot(),
            "requests": requests, "reservations": reservations,
            "account": account}


def test_real_combined_path_fourth_send_refused_by_budget(tmp_path) -> None:
    """P1-1 负控(评审组合路径反例修复):首发 503→重试坏字段 JSON→
    反馈首发 503 →反馈重试登记被**每题预算拒**(第 4 次发送前,拒绝
    优先于 HTTP)。反馈行沿实际 provider_kind=real 登记+占额+network=1。"""
    out = _real_http_case(tmp_path, "combined-cap3",
                          [503, _P1_1_BAD, 503], max_real=3)
    # 第 4 次发送被拒:HTTP 桩只见 3 次;gate/每题预约同 3(全诚实占额)
    assert out["http"] == [503, 200, 503]
    assert out["gate"]["total_requests"] == 3
    assert len(out["reservations"]) == 3
    # 请求行:decide(real,failed)+ decide 重试(real,responded)+ 反馈
    # 首发(**real**,failed;旧实现此处为 scripted/network=0)
    assert len(out["requests"]) == 3
    decide, retry, feedback = out["requests"]
    assert decide["provider_kind"] == "real" and decide["status"] == "failed"
    assert retry["provider_kind"] == "real" \
        and retry["status"] == "responded" and retry["retry_of"]
    assert feedback["provider_kind"] == "real", \
        "反馈首发必须沿实际 provider_kind 登记(P1-1)"
    assert feedback["network_request_count"] == 1
    assert feedback["status"] == "failed"
    # 反馈重试登记被每题预算拒(留痕),原传输失败语义保持为终态
    statuses = [r["status"] for r in out["account"]]
    assert "transport_retry_budget_refused" in statuses
    assert out["summary"]["stop"].get("run_error", {}).get("kind") == \
        "real_model_transport_failure"


def test_real_feedback_budget_normal_paths_positive_controls(tmp_path) -> None:
    """P1-1 正控:正常路径(1 发送)/单支重试(2 发送)/反馈轮正常
    (decide 坏字段→反馈首发成功)全部照常完成,预算如实占额。"""
    normal = _real_http_case(tmp_path, "pc-normal", [_P1_1_GOOD], max_real=3)
    assert normal["http"] == [200]
    assert len(normal["reservations"]) == 1
    assert not normal["summary"]["stop"].get("run_error")
    assert normal["summary"]["native_export"]["export_digest"]

    single_retry = _real_http_case(tmp_path, "pc-single-retry",
                                   [503, _P1_1_GOOD], max_real=3)
    assert single_retry["http"] == [503, 200]
    assert len(single_retry["reservations"]) == 2
    assert not single_retry["summary"]["stop"].get("run_error")

    feedback_ok = _real_http_case(tmp_path, "pc-feedback-ok",
                                  [_P1_1_BAD, _P1_1_GOOD], max_real=3)
    assert feedback_ok["http"] == [200, 200]
    assert len(feedback_ok["reservations"]) == 2
    assert not feedback_ok["summary"]["stop"].get("run_error")
    fb_rows = [r for r in feedback_ok["requests"]
               if r["purpose"] == "format_feedback"]
    assert len(fb_rows) == 1
    assert fb_rows[0]["provider_kind"] == "real"
    assert fb_rows[0]["network_request_count"] == 1
    assert fb_rows[0]["status"] == "responded"


# ------------------------------------------------- P1-2(重试重放)

def _crash_after_full_fetch(tmp_path: Path, run_id: str, *,
                            fail_on_calls: tuple):
    """公开 start(先败后重试成功/单次成功)+ fetch 结束解析前崩溃注入
    (既有 after_request_registered 钩);返回崩溃时模型(调用计数)。"""
    from pathway_v43.pollutant.search import SearchCrashInjection

    model = _SeqTransportStub(
        fail_on_calls=fail_on_calls, fail_kind="transport_error",
        responses=[json.dumps({"proposals": [], "rank_hypotheses": []})],
        model_id=f"chain14-p12-{run_id}",
        call_account_path=tmp_path / "runs" / run_id /
        "s5b_real_calls.jsonl")
    with pytest.raises(SearchCrashInjection):
        _start_run(tmp_path, run_id, model, provider_kind="real",
                   profile=_profile(max_real=3),
                   crash_after="after_request_registered")
    return model


def _resume_after_crash(tmp_path: Path, run_id: str, model) -> dict:
    # 与 _start_run 缺省臂一致(未显式传 ⇒ 现行行为 on)
    return resume_ppv1_run(
        config=resolve_config(), runs_root=tmp_path / "runs",
        run_id=run_id, model=model, evidence_card_enabled=None)


def test_retry_success_crash_replay_zero_new_calls(tmp_path) -> None:
    """P1-2 正控(评审反例修复):首发败→重试成功(完整 blob 已落盘)
    →崩溃注入→同配置 resume **零新增调用**恢复(来源→唯一重试终态
    链消费既有 responded blob;run 完成、非 request_not_consumable)。"""
    run_id = "chain14-p12-retry-replay"
    crashed = _crash_after_full_fetch(tmp_path, run_id, fail_on_calls=(1,))
    before = crashed.complete_calls
    assert before == 2  # 首发(败)+ 重试(成功)
    out = _resume_after_crash(tmp_path, run_id, crashed)
    assert crashed.complete_calls == before, "重放禁止新增付费调用"
    assert not out["stop"].get("run_error")
    assert out["native_export"]["export_digest"]
    rows = _request_rows(tmp_path / "runs", run_id)
    assert len(rows) == 2  # 零新增请求行
    assert any(status == "responded" and retry_of
               for _, status, retry_of, _ in rows)
    blobs = list((tmp_path / "runs" / run_id / "s5b_responses").glob(
        "*.json"))
    assert len(blobs) == 1  # 消费既有 blob,不新增
    account = _account_records(tmp_path / "runs", run_id)
    replays = [r for r in account if r["status"] == "replayed_from_blob"]
    assert len(replays) == 1 and replays[0]["retry_of"]
    assert "NO new paid call" in replays[0]["note"]


def test_single_success_same_point_crash_replay_control(tmp_path) -> None:
    """P1-2 正控(既有语义保持):单次成功同点崩溃 → resume 零新增调用
    恢复(responded + 有效 blob 既有 R3 重放路径)。"""
    run_id = "chain14-p12-single-control"
    crashed = _crash_after_full_fetch(tmp_path, run_id, fail_on_calls=())
    before = crashed.complete_calls
    assert before == 1
    out = _resume_after_crash(tmp_path, run_id, crashed)
    assert crashed.complete_calls == before
    assert not out["stop"].get("run_error")
    assert out["native_export"]["export_digest"]


def test_retry_replay_chain_negatives_still_rejected(tmp_path) -> None:
    """P1-2 负控:坏 blob/错身份/后继缺失/唯一性破坏 ⇒ resume 维持
    拒绝(replay_unavailable/request_not_consumable),零新增调用、
    坏记录保全不洗(不重算新键掩盖)。"""
    from pathway_v43.pollutant.real_model import (
        TRANSPORT_RETRY_KEY_SUFFIX,
    )

    # ---- 负控 1:重试成功 blob 被篡改(content 改动,sha 失配)----
    run_id = "chain14-p12-bad-blob"
    crashed = _crash_after_full_fetch(tmp_path, run_id, fail_on_calls=(1,))
    blob = next((tmp_path / "runs" / run_id / "s5b_responses").glob(
        "*.json"))
    tampered = json.loads(blob.read_text(encoding="utf-8"))
    tampered["content"] = '{"proposals": [{"hypothesis_id": "forged"}]}'
    blob.write_text(json.dumps(tampered, ensure_ascii=False),
                    encoding="utf-8")
    out = _resume_after_crash(tmp_path, run_id, crashed)
    assert crashed.complete_calls == 2, "坏 blob 不补调用"
    assert out["stop"]["run_error"]["kind"] == "replay_unavailable"
    assert blob.is_file(), "坏记录保全(不删除不重算)"

    # ---- 负控 2:重试后继行身份被改坏(purpose 篡改)----
    run_id = "chain14-p12-bad-identity"
    crashed = _crash_after_full_fetch(tmp_path, run_id, fail_on_calls=(1,))
    _db_exec(tmp_path / "runs", run_id,
             "UPDATE model_requests SET purpose = 'tampered'"
             " WHERE retry_of != ''")
    out = _resume_after_crash(tmp_path, run_id, crashed)
    assert crashed.complete_calls == 2
    assert out["stop"]["run_error"]["kind"] == "request_not_consumable"

    # ---- 负控 3:后继缺失(等价"failed 且从未重试成功")----
    run_id = "chain14-p12-no-successor"
    crashed = _crash_after_full_fetch(tmp_path, run_id, fail_on_calls=(1,))
    _db_exec(tmp_path / "runs", run_id,
             "DELETE FROM model_requests WHERE retry_of != ''")
    out = _resume_after_crash(tmp_path, run_id, crashed)
    assert crashed.complete_calls == 2
    assert out["stop"]["run_error"]["kind"] == "request_not_consumable"

    # ---- 负控 4:唯一性破坏(第二个重试后继)----
    run_id = "chain14-p12-two-successors"
    crashed = _crash_after_full_fetch(tmp_path, run_id, fail_on_calls=(1,))
    source = _db_rows(tmp_path / "runs", run_id,
                      "SELECT * FROM model_requests"
                      " WHERE retry_of = ''")[0]
    successor = _db_rows(tmp_path / "runs", run_id,
                         "SELECT * FROM model_requests"
                         " WHERE retry_of != ''")[0]
    _db_exec(
        tmp_path / "runs", run_id,
        "INSERT INTO model_requests (request_id, run_id, action_id,"
        " attempt_id, provider_kind, purpose, status,"
        " network_request_count, payload_hash, response_ref, retry_of,"
        " created_at) VALUES (?, ?, ?, ?, ?, ?, 'responded', 1, ?,"
        " ?, ?, ?)",
        ("chain14-fake-second-retry", source["run_id"],
         source["action_id"], source["attempt_id"],
         source["provider_kind"], source["purpose"],
         source["payload_hash"],
         f"s5b-blob:{successor['request_id']}"
         f"{TRANSPORT_RETRY_KEY_SUFFIX}", source["request_id"],
         source["created_at"]))
    out = _resume_after_crash(tmp_path, run_id, crashed)
    assert crashed.complete_calls == 2
    assert out["stop"]["run_error"]["kind"] == "request_not_consumable"


# ------------------------------------------------- P1-3(中断恢复)

def test_worker_resume_after_public_interruption_recovers(
        tmp_path, monkeypatch) -> None:
    """P1-3(评审反例修复):真实协调者冻结→公开 crash 注入造出
    「已有 run 身份、尚无正式 case」中断→公共 worker 恢复路径 resume
    **同臂成功**(旧实现传 profile_policy=None ⇒ TypeError 失败终态;
    修后删参数,resume 走公共链完成)。"""
    from pathway_v43.pollutant import s5b_orchestrator as orch
    from pathway_v43.pollutant.real_model import (
        S5B_CALL_ACCOUNT_FILE,
        ScriptedRealModelAdapter,
    )
    from pathway_v43.pollutant.search import SearchCrashInjection

    stub_path = tmp_path / "stub.json"
    stub_path.write_text(json.dumps(
        {"strategy": "responses",
         "responses": [json.dumps(
             {"proposals": [], "rank_hypotheses": []})]}),
        encoding="utf-8")
    monkeypatch.setenv("S5B_MODEL_STUB_SCRIPT", str(stub_path))
    batch_root = _scripted_batch(tmp_path, "interrupted")
    runs_root = tmp_path / "runs-interrupted"
    run_input = json.loads(
        (batch_root / "run_inputs" / "SYNTH-C14-1.json").read_text(
            encoding="utf-8"))
    run_id = str(run_input["run_id"])
    # 公开 crash 注入:中断 run(run 身份在、正式 case 无)
    crash_model = ScriptedRealModelAdapter(
        strategy="responses",
        responses=[json.dumps(
            {"proposals": [], "rank_hypotheses": []})],
        call_account_path=runs_root / run_id / S5B_CALL_ACCOUNT_FILE)
    with pytest.raises(SearchCrashInjection):
        start_ppv1_run(
            config=resolve_config(), runs_root=runs_root, run_id=run_id,
            smiles=str(run_input["substrate_smiles"]),
            plan=dict(run_input.get("plan") or {}),
            model=crash_model,
            profile_policy=S5B_DEFAULT_PROFILE_POLICY,
            evidence_card_enabled=False, scripted=True,
            crash_after="after_request_registered")
    assert (runs_root / run_id / "run_identity.json").is_file()
    assert not (batch_root / "cases" / "SYNTH-C14-1.json").exists()
    # 公共 worker 恢复路径:协调者派发 worker → resume 同臂续跑
    report = run_s5b_batch(
        batch_root, runs_root=runs_root, workers=1, poll_s=0.05,
        gate_max_calls=50, evidence_card_enabled=False)
    case = json.loads(
        (batch_root / "cases" / "SYNTH-C14-1.json").read_text())
    assert case["status"] == "completed", case
    assert case.get("failure_kind") != "TypeError"
    assert case["evidence_card_enabled"] is False  # 同臂
    assert case["evidence_card_mode"] == "frozen_batch"
    assert report["n_completed"] == 1 and report["n_failed"] == 0


# ------------------------------------------------- P1-4(副本丢失)

def test_worker_rejects_expected_flag_mismatch_with_frozen_copy(
        tmp_path, monkeypatch) -> None:
    """P1-4 负控(worker 层换臂拒):可信批上下文显式预期 bool 与冻结
    副本不一致 ⇒ 结构化失败 case(零发送,先于任何 run 启动)。"""
    from pathway_v43.pollutant.s5b_worker import worker_main

    stub_path = tmp_path / "stub.json"
    stub_path.write_text(json.dumps({"strategy": "first_pool"}),
                         encoding="utf-8")
    monkeypatch.setenv("S5B_MODEL_STUB_SCRIPT", str(stub_path))
    for tag, frozen, expected in (
            ("mismatch-a", False, True), ("mismatch-b", True, False)):
        batch_root = _scripted_batch(tmp_path, f"worker-{tag}")
        (batch_root / "profile_policy.json").write_text(
            json.dumps(S5B_DEFAULT_PROFILE_POLICY), encoding="utf-8")
        (batch_root / "orchestration.json").write_text(json.dumps(
            {"orchestrator_version": "s5b-orchestrator-3",
             "evidence_card_enabled": frozen}), encoding="utf-8")
        rc = worker_main([
            "--batch-root", str(batch_root),
            "--runs-root", str(tmp_path / f"runs-{tag}"),
            "--qid", "SYNTH-C14-1",
            "--evidence-card-flag", "true" if expected else "false"])
        assert rc == 5, tag
        case = json.loads(
            (batch_root / "cases" / "SYNTH-C14-1.json").read_text())
        assert case["status"] == "failed", tag
        assert case["failure_kind"] == "evidence_card_flag_mismatch", tag
        assert case["detail"]["expected_evidence_card_enabled"] \
            is expected, tag
        assert case["detail"]["frozen_evidence_card_enabled"] \
            is frozen, tag


def test_worker_rejects_missing_frozen_copy_in_trusted_context(
        tmp_path, monkeypatch) -> None:
    """P1-4 负控(worker 层):可信批上下文(显式预期 bool)而冻结副本
    缺席 ⇒ 拒不回退(evidence_card_frozen_copy_missing;旧实现
    None→True 让已冻结 A 丢副本静默变 B)。"""
    from pathway_v43.pollutant.s5b_worker import worker_main

    stub_path = tmp_path / "stub.json"
    stub_path.write_text(json.dumps({"strategy": "first_pool"}),
                         encoding="utf-8")
    monkeypatch.setenv("S5B_MODEL_STUB_SCRIPT", str(stub_path))
    batch_root = _scripted_batch(tmp_path, "worker-copy-missing")
    (batch_root / "profile_policy.json").write_text(
        json.dumps(S5B_DEFAULT_PROFILE_POLICY), encoding="utf-8")
    rc = worker_main([
        "--batch-root", str(batch_root),
        "--runs-root", str(tmp_path / "runs-copy-missing"),
        "--qid", "SYNTH-C14-1",
        "--evidence-card-flag", "false"])
    assert rc == 5
    case = json.loads(
        (batch_root / "cases" / "SYNTH-C14-1.json").read_text())
    assert case["status"] == "failed"
    assert case["failure_kind"] == "evidence_card_frozen_copy_missing"
    assert case["detail"]["expected_evidence_card_enabled"] is False


def test_coordinator_frozen_copy_lost_before_worker_rejected(
        tmp_path, monkeypatch) -> None:
    """P1-4 评审反例复现(修后必须拒绝):真实协调者冻 False → worker
    启动前移走冻结副本(Popen 拦截注入)→ worker 拒(失败 case,零
    发送零 run);批报告前同源核对 fail-closed(副本丢失不写错账报告,
    协调者结构化拒)。旧实现此处 rc=0/case completed on 而批报告 off。"""
    from pathway_v43.pollutant import s5b_orchestrator as orch

    stub_path = tmp_path / "stub.json"
    stub_path.write_text(json.dumps({"strategy": "first_pool"}),
                         encoding="utf-8")
    monkeypatch.setenv("S5B_MODEL_STUB_SCRIPT", str(stub_path))
    batch_root = _scripted_batch(tmp_path, "copylost")
    runs_root = tmp_path / "runs-copylost"
    real_popen = subprocess.Popen
    removed = {"done": False}

    def popen_remove_orchestration(*args, **kwargs):
        if not removed["done"]:
            (batch_root / "orchestration.json").unlink()  # 启动前移走副本
            removed["done"] = True
        return real_popen(*args, **kwargs)

    monkeypatch.setattr(
        "pathway_v43.pollutant.s5b_orchestrator.subprocess.Popen",
        popen_remove_orchestration)
    with pytest.raises(Exception) as excinfo:  # noqa: B017
        run_s5b_batch(batch_root, runs_root=runs_root, workers=1,
                      poll_s=0.05, gate_max_calls=50,
                      evidence_card_enabled=False)
    # 批报告前同源核对:副本丢失 ⇒ fail-closed 拒,不写错账报告
    assert excinfo.value.detail["kind"] == "s5b_evidence_card_flag_invalid"
    assert excinfo.value.detail["reason"] == \
        "frozen_copy_mismatch_at_report"
    # worker 侧拒绝:失败 case 留分母,零发送零 run
    case = json.loads(
        (batch_root / "cases" / "SYNTH-C14-1.json").read_text())
    assert case["status"] == "failed"
    assert case["failure_kind"] == "evidence_card_frozen_copy_missing"
    assert not runs_root.exists(), "worker 拒绝路径零 run 启动(零发送)"


def test_case_acceptance_rejects_flag_mismatch_before_skip_and_summary(
        tmp_path, monkeypatch) -> None:
    """P1-4 负控(接纳面):已完成 case 披露开关与批冻结开关不一致 ⇒
    skip/汇总接纳前结构化拒(evidence_card_flag_mismatch),错臂终态
    不进分母。"""
    stub_path = tmp_path / "stub.json"
    stub_path.write_text(json.dumps({"strategy": "first_pool"}),
                         encoding="utf-8")
    monkeypatch.setenv("S5B_MODEL_STUB_SCRIPT", str(stub_path))
    batch_root = _scripted_batch(tmp_path, "accept-mismatch")
    run_input = json.loads(
        (batch_root / "run_inputs" / "SYNTH-C14-1.json").read_text(
            encoding="utf-8"))
    forged = {
        "qid": "SYNTH-C14-1", "run_id": str(run_input["run_id"]),
        "case_schema_version": S5B_CASE_SCHEMA_VERSION,
        "status": "completed", "stop_reason": "budget_exhausted",
        "export_digest": "", "evidence_card_enabled": True,  # 错臂终态
    }
    (batch_root / "cases").mkdir(parents=True, exist_ok=True)
    (batch_root / "cases" / "SYNTH-C14-1.json").write_text(
        json.dumps(forged), encoding="utf-8")
    with pytest.raises(Exception) as excinfo:  # noqa: B017
        run_s5b_batch(batch_root, runs_root=tmp_path / "runs-accept",
                      workers=1, poll_s=0.05, gate_max_calls=50,
                      evidence_card_enabled=False)
    assert excinfo.value.detail["kind"] == "s5b_case_validation_failed"
    assert "evidence_card_flag_mismatch" in \
        excinfo.value.detail["reasons"]
    # 汇总入口同判据(评分前同拒)
    with pytest.raises(Exception) as excinfo2:  # noqa: B017
        summarize_batch(batch_root)
    assert "evidence_card_flag_mismatch" in \
        excinfo2.value.detail["reasons"]


# ------------------------------------------------- P1 余项回修轮
# (TASK_CHAIN14_P1_RESIDUAL_2026-10-16;Codex 同范围复核 CHAIN14_LAUNCH_
# CODEX_REREVIEW_2026-10-16 §⑤ 两项余项:①P1-2 反馈轮自身的崩溃重放
# —— 先复用既有反馈轮/原请求键/唯一重试终态再消费完整响应,不得先
# 分配新轮、禁新增付费请求、预算第 4 次发送前拒保持;②P1-4 completed
# 严格臂校验 —— expected 明确时必须有键+严格 bool+同值,失败 case
# 披露了也严格,合法 run 前早失败可缺字段。合成验证:零金标零题面
# 零模型零网络。)


def _crashed_after_feedback_fetch(tmp_path: Path, run_id: str, *,
                                  fail_on_calls: tuple,
                                  max_real: int = 3):
    """公开 start 打进「反馈成功响应已落盘、解析未执行」崩溃窗口
    (评审 retry 探针 v2 同手法:patch runflow.parse_model_proposals,
    第 2 次 parse(= 反馈响应解析)注入 SearchCrashInjection)。
    fail_on_calls=(2,) ⇒ 反馈首发传输失败+重试成功;() ⇒ 反馈首发
    一次成功。返回崩溃时模型(complete 调用计数)。"""
    from unittest.mock import patch

    from pathway_v43.pollutant import runflow
    from pathway_v43.pollutant.search import SearchCrashInjection

    good = json.dumps({"proposals": [], "rank_hypotheses": []})
    model = _SeqTransportStub(
        fail_on_calls=fail_on_calls, fail_kind="transport_error",
        responses=[json.dumps({"proposal": []}), good, good],
        model_id=f"chain14-p1r-{run_id}",
        call_account_path=tmp_path / "runs" / run_id /
        "s5b_real_calls.jsonl")
    real_parse = runflow.parse_model_proposals
    parse_calls = {"n": 0}

    def crash_before_feedback_parse(response_text, **kwargs):
        parse_calls["n"] += 1
        if parse_calls["n"] == 2:
            raise SearchCrashInjection(
                "合成崩溃:反馈成功响应已落盘、解析未执行",
                {"kind": "synthetic_crash_after_feedback_fetch"})
        return real_parse(response_text, **kwargs)

    with patch.object(runflow, "parse_model_proposals",
                      crash_before_feedback_parse):
        with pytest.raises(SearchCrashInjection):
            _start_run(tmp_path, run_id, model, provider_kind="real",
                       profile=_profile(max_real=max_real,
                                        feedback_rounds=2))
    return model


def _feedback_rows(runs_root: Path, run_id: str) -> tuple[list, list]:
    """(反馈轮首发行, 反馈重试行)按 retry_of 链拆分(各恰好一行)。"""
    rows = _request_rows(runs_root, run_id)
    first = [r for r in rows if r[3] == "format_feedback" and not r[2]]
    retry = [r for r in rows if r[3] == "format_feedback" and r[2]]
    assert len(first) == 1 and len(retry) == 1, rows
    assert retry[0][2] == first[0][0], "重试行必须显式链接该轮首发"
    return first, retry


def test_feedback_retry_success_crash_resume_budget3_completes(
        tmp_path) -> None:
    """P1-2 余项正控(评审反例修复):首提 BAD→反馈首发传输失败→反馈
    重试成功(完整 blob 已落盘)→解析前崩溃→同配置 resume **零新增
    调用/零新轮/零新行**消费既有成功响应(3→3 且 run 完成)。旧实现
    先登记新反馈轮 ⇒ 预算 3 先拒(model_structure_failure),成功
    blob 永不消费。"""
    run_id = "chain14-p1r-retry-ok"
    crashed = _crashed_after_feedback_fetch(tmp_path, run_id,
                                            fail_on_calls=(2,))
    before = crashed.complete_calls
    assert before == 3  # decide 首发 + 反馈首发(败) + 反馈重试(成)
    out = _resume_after_crash(tmp_path, run_id, crashed)
    assert crashed.complete_calls == before, "重放禁止新增付费调用(3→3)"
    assert not out["stop"].get("run_error"), out["stop"].get("run_error")
    assert out["native_export"]["export_digest"]
    rows = _request_rows(tmp_path / "runs", run_id)
    assert len(rows) == 3, "零新增请求行(不先分配新反馈轮)"
    first, retry = _feedback_rows(tmp_path / "runs", run_id)
    assert first[0][1] == "failed" and retry[0][1] == "responded"
    blobs = sorted(p.name for p in (
        tmp_path / "runs" / run_id / "s5b_responses").glob("*.json"))
    assert len(blobs) == 2  # decide BAD + 反馈重试 GOOD;零新增 blob
    account = _account_records(tmp_path / "runs", run_id)
    replays = [r for r in account if r["status"] == "replayed_from_blob"]
    chain_replays = [r for r in replays if r.get("retry_of")]
    assert len(chain_replays) == 1, "反馈轮重试终态经唯一链零调用重放"
    assert "NO new paid call" in chain_replays[0]["note"]
    # 预算面:3 次真实发送占 3 额度,第 4 次发送未发生(P1-1 保持)
    reservations = _db_rows(
        tmp_path / "runs", run_id,
        "SELECT reservation_id FROM budget_reservations WHERE"
        " limit_key = 'max_real_model_requests'")
    assert len(reservations) == 3


def test_feedback_single_success_crash_resume_zero_new_calls(
        tmp_path) -> None:
    """P1-2 余项正控(同入口缺口一并闭合):反馈首发一次成功→解析前
    崩溃→resume 零新增调用消费既有 responded blob(2→2 且完成)。
    旧实现 resume 另发第 2 轮(2→3;复核标注「既有入口缺口」)。"""
    run_id = "chain14-p1r-single-ok"
    crashed = _crashed_after_feedback_fetch(tmp_path, run_id,
                                            fail_on_calls=())
    before = crashed.complete_calls
    assert before == 2  # decide 首发(BAD) + 反馈首发(成功)
    out = _resume_after_crash(tmp_path, run_id, crashed)
    assert crashed.complete_calls == before, "重放禁止新增付费调用(2→2)"
    assert not out["stop"].get("run_error")
    assert out["native_export"]["export_digest"]
    rows = _request_rows(tmp_path / "runs", run_id)
    assert len(rows) == 2, "零新增请求行"
    fb = [r for r in rows if r[3] == "format_feedback"]
    assert len(fb) == 1 and fb[0][1] == "responded"
    account = _account_records(tmp_path / "runs", run_id)
    replays = [r for r in account if r["status"] == "replayed_from_blob"]
    assert len(replays) == 2  # decide 重放 + 反馈 R3 重放


def test_feedback_resume_rejects_bad_blob_and_wrong_identity(
        tmp_path) -> None:
    """P1-2 余项负控(同入口,零补调用、坏记录保全、零新行):
    坏 blob(重试终态 blob 篡改)⇒ replay_unavailable;错身份(重试
    后继行 purpose 篡改)⇒ request_not_consumable;反馈首发行 purpose
    篡改 ⇒ 同键重登记撞 S3A-04 身份冲突(request_identity_conflict,
    不以新轮登记掩盖);后继缺失 ⇒ request_not_consumable。"""
    # ---- 负控 1:重试成功 blob 被篡改(sha 失配)----
    run_id = "chain14-p1r-bad-blob"
    crashed = _crashed_after_feedback_fetch(tmp_path, run_id,
                                            fail_on_calls=(2,))
    blob = next((tmp_path / "runs" / run_id / "s5b_responses").glob(
        "*.json"))
    tampered = json.loads(blob.read_text(encoding="utf-8"))
    tampered["content"] = '{"proposals": [{"hypothesis_id": "forged"}]}'
    blob.write_text(json.dumps(tampered, ensure_ascii=False),
                    encoding="utf-8")
    out = _resume_after_crash(tmp_path, run_id, crashed)
    assert crashed.complete_calls == 3, "坏 blob 不补调用"
    assert out["stop"]["run_error"]["kind"] == "replay_unavailable"
    assert blob.is_file(), "坏记录保全(不删除不重算)"
    assert len(_request_rows(tmp_path / "runs", run_id)) == 3

    # ---- 负控 2:重试后继行身份被改坏(purpose 篡改)----
    run_id = "chain14-p1r-bad-identity"
    crashed = _crashed_after_feedback_fetch(tmp_path, run_id,
                                            fail_on_calls=(2,))
    _db_exec(tmp_path / "runs", run_id,
             "UPDATE model_requests SET purpose = 'tampered'"
             " WHERE retry_of != ''")
    out = _resume_after_crash(tmp_path, run_id, crashed)
    assert crashed.complete_calls == 3
    assert out["stop"]["run_error"]["kind"] == "request_not_consumable"
    assert len(_request_rows(tmp_path / "runs", run_id)) == 3

    # ---- 负控 3:反馈首发行 purpose 篡改 ⇒ 不分配新轮掩盖(同键
    # 重登记撞 S3A-04 同键身份冲突)----
    run_id = "chain14-p1r-bad-source"
    crashed = _crashed_after_feedback_fetch(tmp_path, run_id,
                                            fail_on_calls=(2,))
    _db_exec(tmp_path / "runs", run_id,
             "UPDATE model_requests SET purpose = 'tampered' WHERE"
             " retry_of = '' AND purpose = 'format_feedback'")
    out = _resume_after_crash(tmp_path, run_id, crashed)
    assert crashed.complete_calls == 3
    assert out["stop"]["run_error"]["kind"] == "request_identity_conflict"
    assert len(_request_rows(tmp_path / "runs", run_id)) == 3

    # ---- 负控 4:后继缺失(重试成功行被删;链不成立维持拒绝)----
    run_id = "chain14-p1r-no-successor"
    crashed = _crashed_after_feedback_fetch(tmp_path, run_id,
                                            fail_on_calls=(2,))
    _db_exec(tmp_path / "runs", run_id,
             "DELETE FROM model_requests WHERE retry_of != ''")
    out = _resume_after_crash(tmp_path, run_id, crashed)
    assert crashed.complete_calls == 3
    assert out["stop"]["run_error"]["kind"] == "request_not_consumable"
    assert len(_request_rows(tmp_path / "runs", run_id)) == 2


def test_feedback_resume_without_retry_terminal_no_new_send(
        tmp_path) -> None:
    """P1-2 余项负控(预算第 4 次发送前拒保持的 resume 面):反馈首发
    传输失败且重试从未发生(每题预算 3 满时重试登记被拒;P1-1 组合
    形状)→ resume 维持拒绝且**零补发**(不另发付费请求、零新行;
    旧实现 resume 先分配新轮)。"""
    run_id = "chain14-p1r-no-terminal"
    model = _SeqTransportStub(
        fail_on_calls=(1, 3), fail_kind="transport_error",
        responses=[json.dumps({"proposal": []})],
        model_id=f"chain14-p1r-{run_id}",
        call_account_path=tmp_path / "runs" / run_id /
        "s5b_real_calls.jsonl")
    first = _start_run(tmp_path, run_id, model, provider_kind="real",
                       profile=_profile(max_real=3, feedback_rounds=2))
    # 首发:decide 败→decide 重试成(BAD)→反馈首发败→反馈重试登记
    # 被每题预算拒(第 4 次发送前);原传输失败语义保持
    assert first["stop"].get("run_error", {}).get("kind") == \
        "real_model_transport_failure"
    assert model.complete_calls == 3
    rows_before = _request_rows(tmp_path / "runs", run_id)
    assert len(rows_before) == 3
    assert any(r[3] == "format_feedback" and r[1] == "failed" and not r[2]
               for r in rows_before)
    out = _resume_after_crash(tmp_path, run_id, model)
    assert model.complete_calls == 3, "恢复不另发付费请求(零补发)"
    assert len(_request_rows(tmp_path / "runs", run_id)) == 3, "零新行"
    assert out["stop"]["run_error"]["kind"] == "request_not_consumable"


# --------------------------------------- P1-2 收口轮(第四轮,2026-10-16)
# (TASK_CHAIN14_P1_FINAL_2026-10-16;Codex 复核2 findings:复用既有反
# 馈轮前统一核验原登记身份/内容/执行引用未闭合 —— 原行 run_id/
# attempt_id/provider_kind/payload_hash 被改坏仍被复用、计数>0 却查
# 不到应有原行(原行 request_id 被改坏)返回 None 走新登记 ⇒ 另发一
# 次。修法:latest_format_feedback_round 统一身份核验门(所有状态分
# 支共用;计数>0 无原行 ⇒ 结构化拒;payload_hash 同源确定性重算核
# 验 —— 登记载荷去 recorded_at,时间由 model_requests.created_at 承
# 载,不存在重算时间戳冒充面)。合成验证沿评审 probe 手法:公开
# start_ppv1_run(scripted=True, provider_kind=real)+合成 CCO+
# ScriptedRealModelAdapter 状态机+解析前崩溃注入+受控损坏权威 SQLite
# 原行+公开 resume_ppv1_run;零金标零题面零模型零网络。)


def _gate_case(tmp_path: Path, tag: str, *, fail_on_calls: tuple,
               sql: str, params: tuple) -> dict:
    """矩阵单场景:公开 start 打进反馈崩溃窗口 → 受控损坏反馈原行
    单一字段 → 公开 resume;返回调用/行数前后与恢复结果(坏行保全
    由调用方按 tamper 断言)。"""
    run_id = f"chain14-p1f-{tag}"
    crashed = _crashed_after_feedback_fetch(tmp_path, run_id,
                                            fail_on_calls=fail_on_calls)
    calls_before = crashed.complete_calls
    rows_before = _request_rows(tmp_path / "runs", run_id)
    _db_exec(tmp_path / "runs", run_id, sql, params)
    out = _resume_after_crash(tmp_path, run_id, crashed)
    return {
        "calls_before": calls_before,
        "calls_after": crashed.complete_calls,
        "rows_before": rows_before,
        "rows_after": _request_rows(tmp_path / "runs", run_id),
        "out": out,
        "run_id": run_id,
    }


def test_feedback_resume_unified_identity_gate_matrix(tmp_path) -> None:
    """P1-2 收口轮 8 场景矩阵(评审 findings result.json 对齐;负控
    ×6:任一原登记身份/内容字段改坏 ⇒ feedback_round_identity_
    corrupt 结构化拒 + 零新增调用 + 零新轮/新行 + 坏记录保全;
    正控×2:3→3 反馈重试成功恢复 / 2→2 单次成功恢复照常完成,由
    test_feedback_retry_success_crash_resume_budget3_completes 与
    test_feedback_single_success_crash_resume_zero_new_calls 承担,
    本矩阵另补两正控的坏字段*不*触碰断言面的完整性)。"""
    # ---- 负控 1-4:responded 原行单字段身份改坏 ----
    for tag, sql, params in [
        ("run-id", "UPDATE model_requests SET run_id = 'tampered-run'"
         " WHERE retry_of = '' AND purpose = 'format_feedback'", ()),
        ("attempt-id", "UPDATE model_requests SET attempt_id ="
         " 'tampered-attempt' WHERE retry_of = '' AND"
         " purpose = 'format_feedback'", ()),
        ("provider", "UPDATE model_requests SET provider_kind ="
         " 'scripted' WHERE retry_of = '' AND"
         " purpose = 'format_feedback'", ()),
        ("payload-hash", "UPDATE model_requests SET payload_hash ="
         " 'tampered-payload' WHERE retry_of = '' AND"
         " purpose = 'format_feedback'", ()),
    ]:
        case = _gate_case(tmp_path, f"resp-{tag}", fail_on_calls=(),
                          sql=sql, params=params)
        assert case["calls_before"] == 2 and case["calls_after"] == 2, \
            (tag, "坏身份不补调用(2→2)")
        assert len(case["rows_before"]) == len(case["rows_after"]) == 2, \
            (tag, "零新轮/新行(不分配新轮洗坏记录)")
        run_error = case["out"]["stop"].get("run_error") or {}
        assert run_error.get("kind") == "feedback_round_identity_corrupt", \
            (tag, run_error)
        # 坏记录保全:被改坏字段原样保留(不删除、不重算掩盖)
        tampered = _db_rows(
            tmp_path / "runs", case["run_id"],
            "SELECT * FROM model_requests WHERE"
            " retry_of = '' AND purpose = 'format_feedback'")[0]
        col = {"run-id": "run_id", "attempt-id": "attempt_id",
               "provider": "provider_kind",
               "payload-hash": "payload_hash"}[tag]
        assert str(tampered[col]).startswith("tampered") or \
            tampered[col] == "scripted", (tag, tampered[col])

    # ---- 负控 5:sent + provider 改坏(状态分支同规则,消费前已拒)----
    case = _gate_case(
        tmp_path, "sent-provider", fail_on_calls=(),
        sql="UPDATE model_requests SET provider_kind = 'scripted',"
            " status = 'sent' WHERE retry_of = '' AND"
            " purpose = 'format_feedback'", params=())
    assert case["calls_before"] == case["calls_after"] == 2, "sent 悬空面同拒(零补调用)"
    assert len(case["rows_after"]) == 2
    assert (case["out"]["stop"].get("run_error") or {}).get("kind") == \
        "feedback_round_identity_corrupt"

    # ---- 负控 6:registered + provider 改坏 ⇒ 结构化拒,**不分配
    # 新轮**(旧实现 2→3 另发一次并完成)----
    case = _gate_case(
        tmp_path, "reg-provider", fail_on_calls=(),
        sql="UPDATE model_requests SET provider_kind = 'scripted',"
            " status = 'registered' WHERE retry_of = '' AND"
            " purpose = 'format_feedback'", params=())
    assert case["calls_before"] == case["calls_after"] == 2, \
        "registered 面同拒:不补首发(2→2,旧实现另发 2→3)"
    assert len(case["rows_after"]) == 2, "不分配新轮(2 行保持)"
    assert (case["out"]["stop"].get("run_error") or {}).get("kind") == \
        "feedback_round_identity_corrupt"

    # ---- 负控 7:failed 原行 payload_hash 改坏(成功后继完整)----
    # ⇒ 结构化拒(唯一重试终态链不消费来源 payload 未核的行)
    case = _gate_case(
        tmp_path, "failed-source-payload", fail_on_calls=(2,),
        sql="UPDATE model_requests SET payload_hash = 'tampered-payload'"
            " WHERE retry_of = '' AND purpose = 'format_feedback'",
        params=())
    assert case["calls_before"] == case["calls_after"] == 3, \
        "来源 payload 未核不消费(3→3 零补调用)"
    assert len(case["rows_after"]) == 3, "后继完整也不洗(3 行保持)"
    assert (case["out"]["stop"].get("run_error") or {}).get("kind") == \
        "feedback_round_identity_corrupt"
    # 成功后继保全(retry 链未被改写)
    assert any(r[1] == "responded" and r[2] for r in case["rows_after"])

    # ---- 负控 8:原行 request_id 改坏(计数>0 却查不到应有原行)----
    # ⇒ 结构化拒(original_row_missing),**不返回 None 走新登记**
    # (旧实现 2→3 另建第 2 轮并完成;原坏行仍在)----
    case = _gate_case(
        tmp_path, "lost-key", fail_on_calls=(),
        sql="UPDATE model_requests SET request_id ="
            " 'sreq-tampered-authoritative-key' WHERE retry_of = '' AND"
            " purpose = 'format_feedback'", params=())
    assert case["calls_before"] == case["calls_after"] == 2, \
        "键缺失不另发(2→2,旧实现另建第 2 轮 2→3)"
    assert len(case["rows_after"]) == 2, \
        "计数>0 无原行 ⇒ 零新轮(不新登记第 2 轮)"
    run_error = case["out"]["stop"].get("run_error") or {}
    assert run_error.get("kind") == "feedback_round_identity_corrupt"
    assert "原行" in run_error.get("message", ""), run_error
    # 坏行保全(原样保留被改坏的 request_id,不删除不重算)
    assert any(r[0] == "sreq-tampered-authoritative-key"
               for r in case["rows_after"])


def test_case_acceptance_strict_flag_rule_matrix() -> None:
    """P1-4 余项矩阵(validate_case 纯函数面):expected 明确时
    completed 缺键/null/非 bool("on"/1/{}/0)/错臂 ⇒ 全拒(原因
    分列 missing/not_bool/mismatch);在位正确 bool ⇒ 过。失败 case
    披露了也须严格 bool/同值(错臂/null 拒);缺键豁免保留(合法
    run 前早失败可缺字段)。expected 双臂都核。"""
    def case(status: str, flag, *, failure_kind: str = "") -> dict:
        payload = {
            "qid": "SYNTH-C14-1", "run_id": "syn-case",
            "case_schema_version": S5B_CASE_SCHEMA_VERSION,
            "status": status,
            "stop_reason": ("budget_exhausted" if status == "completed"
                            else ""),
            "export_digest": ""}
        if status == "failed":
            payload["failure_kind"] = failure_kind or \
                "model_structure_failure"
        if flag != "MISSING":
            payload["evidence_card_enabled"] = flag
        return payload

    for expected in (False, True):
        other = not expected
        # completed:全负控形状拒 + 合法正控过
        verdicts = {}
        for label, flag in (("missing", "MISSING"), ("null", None),
                            ("str_on", "on"), ("int_one", 1),
                            ("empty_dict", {}), ("int_zero", 0),
                            ("wrong_bool", other), ("ok_bool", expected)):
            v = validate_case(case("completed", flag), "SYNTH-C14-1",
                              expected_run_id="syn-case",
                              expected_evidence_card=expected)
            verdicts[label] = v
        assert verdicts["missing"]["reasons"] == \
            ["evidence_card_flag_missing"]
        for label in ("null", "str_on", "int_one", "empty_dict",
                      "int_zero"):
            assert verdicts[label]["reasons"] == \
                ["evidence_card_flag_not_bool"], label
        assert verdicts["wrong_bool"]["reasons"] == \
            ["evidence_card_flag_mismatch"]
        assert verdicts["ok_bool"]["ok"] is True
        # failed:披露了才核(严格 bool + 同值);缺键豁免保留
        failed_missing = validate_case(case("failed", "MISSING"),
                                       "SYNTH-C14-1",
                                       expected_run_id="syn-case",
                                       expected_evidence_card=expected)
        assert failed_missing["ok"] is True, "早失败缺字段豁免保留"
        failed_wrong = validate_case(case("failed", other),
                                     "SYNTH-C14-1",
                                     expected_run_id="syn-case",
                                     expected_evidence_card=expected)
        assert failed_wrong["reasons"] == ["evidence_card_flag_mismatch"]
        failed_null = validate_case(case("failed", None), "SYNTH-C14-1",
                                    expected_run_id="syn-case",
                                    expected_evidence_card=expected)
        assert failed_null["reasons"] == ["evidence_card_flag_not_bool"]
        failed_ok = validate_case(case("failed", expected), "SYNTH-C14-1",
                                  expected_run_id="syn-case",
                                  expected_evidence_card=expected)
        assert failed_ok["ok"] is True
    # expected 缺席(手动批,冻结副本不在)⇒ 不核(现行豁免面不变)
    manual = validate_case(case("completed", "MISSING"), "SYNTH-C14-1",
                           expected_run_id="syn-case",
                           expected_evidence_card=None)
    assert manual["ok"] is True


def _forged_completed_case(tmp_path: Path, tag: str, *,
                           drop_flag: bool = False,
                           null_flag: bool = False,
                           flag_value=False) -> Path:
    """合法形状 completed case(除开关字段受控变异;run_id 与批
    run_inputs 同源;其余字段全合法 ⇒ 唯一校验失败原因 = 开关)。"""
    batch_root = _scripted_batch(tmp_path, tag)
    run_input = json.loads(
        (batch_root / "run_inputs" / "SYNTH-C14-1.json").read_text(
            encoding="utf-8"))
    forged = {
        "qid": "SYNTH-C14-1", "run_id": str(run_input["run_id"]),
        "case_schema_version": S5B_CASE_SCHEMA_VERSION,
        "status": "completed", "stop_reason": "budget_exhausted",
        "export_digest": "", "evidence_card_enabled": flag_value,
    }
    if drop_flag:
        forged.pop("evidence_card_enabled")
    if null_flag:
        forged["evidence_card_enabled"] = None
    (batch_root / "cases").mkdir(parents=True, exist_ok=True)
    (batch_root / "cases" / "SYNTH-C14-1.json").write_text(
        json.dumps(forged), encoding="utf-8")
    return batch_root


def test_public_acceptance_rejects_completed_flag_missing_or_null(
        tmp_path) -> None:
    """P1-4 余项负控(公共 skip/汇总接纳面,评审受控反例修复):
    completed 开关字段**删除/置 null** ⇒ 错账终态不再被接纳
    (skip/汇总双入口结构化拒;零 worker 派发零 run)。旧实现只核
    「有键且非 null」且先 bool() 强转 ⇒ 删字段/null 绕过接纳门
    (skip=1、completed=1、报告 false=错账)。"""
    for tag, kwargs in (("accept-missing", {"drop_flag": True}),
                        ("accept-null", {"null_flag": True})):
        batch_root = _forged_completed_case(tmp_path, tag, **kwargs)
        runs_root = tmp_path / f"runs-{tag}"
        with pytest.raises(Exception) as excinfo:  # noqa: B017
            run_s5b_batch(batch_root, runs_root=runs_root, workers=1,
                          poll_s=0.05, gate_max_calls=50,
                          evidence_card_enabled=False)
        assert excinfo.value.detail["kind"] == \
            "s5b_case_validation_failed", tag
        expected_reason = ("evidence_card_flag_missing" if
                           kwargs.get("drop_flag")
                           else "evidence_card_flag_not_bool")
        assert expected_reason in excinfo.value.detail["reasons"], tag
        assert not runs_root.exists(), \
            "接纳前拒:零 worker 派发(零发送)"
        # 汇总入口同判据(评分前同拒)
        with pytest.raises(Exception) as excinfo2:  # noqa: B017
            summarize_batch(batch_root)
        assert expected_reason in excinfo2.value.detail["reasons"], tag


def test_public_acceptance_positive_control_correct_flag_case(
        tmp_path) -> None:
    """P1-4 余项正控(公共接纳面):completed 在位**正确 bool 同值**
    ⇒ skip/汇总照常接纳(错误臂校验不误伤合法终态;skip 计数 +
    n_completed=1 + 报告开关 = 批冻结值)。"""
    batch_root = _forged_completed_case(tmp_path, "accept-ok",
                                        flag_value=False)
    report = run_s5b_batch(batch_root,
                           runs_root=tmp_path / "runs-accept-ok",
                           workers=1, poll_s=0.05, gate_max_calls=50,
                           evidence_card_enabled=False)
    assert report["n_completed"] == 1 and report["n_failed"] == 0
    assert report["evidence_card_enabled"] is False
    summary = summarize_batch(batch_root)
    assert summary["n_completed"] == 1 and summary["n_failed"] == 0
