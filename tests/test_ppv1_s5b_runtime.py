"""PPV1 S5b 运行时批测试(客户端/构建器/编排器/判分;零网络)。

覆盖(任务书验收四件):
- 真模型客户端:请求构造/env 装配(v43 主名 + v41 回退)/身份块/
  传输失败记账(超时 ⇒ failed 占额、失败题留分母)/调用账本零密钥;
- 构建器:合成夹具端到端(题卷 → 参考图 + run 输入 + 清单;冻结
  注册序;qid 进 source_refs;重复底物 related;输出根守卫);
- 编排器:3 题合成夹具、并发 2 路(scripted 模型桩子进程)resume
  (已完成 qid SKIP);失败题失败补位留分母;
- 判分:合成端到端(构建→跑→score_s5b_batch 含 data_scope 门;
  real 门无批准 ⇒ 拒、有批准 ⇒ qid_strict 配对 + pending 状态)、
  双口径聚合、报告生成(数字带题域标签 298);
- runflow 钩子回归:无模型对象/无方法的旧行为逐字节不变。

环境纪律:零网络(scripted 桩与真实客户端桩测试只验构造/记账,
不发起任何 HTTP);密钥不落任何文件/日志;合成 qid/分子与真实
298 集合零重叠(已对本地金标只读核验后选用,核验值不入仓)。
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pathway_v43.config import resolve_config  # noqa: E402
from pathway_v43.pollutant.real_model import (  # noqa: E402
    PROPOSALS_PROMPT_VERSION,
    RealModelAdapter,
    RealModelNotConfigured,
    ScriptedRealModelAdapter,
    build_proposals_user_payload,
)
from pathway_v43.pollutant.runflow import start_ppv1_run  # noqa: E402
from pathway_v43.pollutant.s5b_builder import (  # noqa: E402
    S5B_KNOWN_GAPS,
    S5bBuilderError,
    build_question_batch,
    check_output_root,
    load_questions,
)
from pathway_v43.pollutant.s5b_orchestrator import (  # noqa: E402
    S5B_DEFAULT_PROFILE_POLICY,
    read_case,
    run_s5b_batch,
)
from pathway_v43.pollutant.s5b_scoring import (  # noqa: E402
    S5bScoringError,
    score_s5b_batch,
)
from pathway_v43.pollutant.reference_graph import (  # noqa: E402
    validate_reference_graph,
)


# ---------------------------------------------------------------- 合成夹具

# 与真实 298 金标集合零重叠的合成分子(本地只读核验后选用;不入仓)
SYNTH_QUESTIONS = [
    {"qid": "SYNTH-Q001", "substrate_smiles": "CCO",
     "products_smiles": ["CC=O"], "raw_reaction": "CCO>>CC=O"},
    {"qid": "SYNTH-Q002", "substrate_smiles": "CCO",
     "products_smiles": ["CC(O)C"], "raw_reaction": "CCO>>CC(O)C"},
    {"qid": "SYNTH-Q003", "substrate_smiles": "CCOCC",
     "products_smiles": ["CCO"], "raw_reaction": "CCOCC>>CCO"},
]


def synth_spec(key: str, product: str, tref: str) -> dict:
    """池条目(形状沿 tests/test_ppv1_s4a_endpoint.spec 契约)。"""
    return {
        "key": key, "product_smiles": product, "coefficient": 1,
        "transformation_ref": tref, "origin_group_key": f"donor-{key}",
        "edits": [{"op": "change_bond_order", "atom1": "S_C_2",
                   "atom2": "S_O_1", "from_order": "single",
                   "to_order": "double"}],
        "donor": {"center_atom_ids": ["S_C_2", "S_O_1"]},
        "alignment": {"status": "resolved",
                      "donor_to_current": {"S_C_2": "S_C_2",
                                           "S_O_1": "S_O_1"},
                      "ref": "align-A"},
        "expectation": {"target_smiles": product},
    }


SYNTH_POOL = {
    "CCO": [synth_spec("B", "CC=O", "donor-B"),
            synth_spec("C", "CC(O)C", "donor-C")],
    "CCOCC": [synth_spec("E", "CCO", "donor-E")],
}


def synth_pool_provider(substrate: str) -> list[dict]:
    return [dict(s) for s in SYNTH_POOL.get(substrate, [])]


@pytest.fixture(scope="module")
def synth_batch(tmp_path_factory):
    """合成批:题卷 + 构建产物 + 3 题跑完(编排器 2 路 stub 子进程)。"""
    root = tmp_path_factory.mktemp("s5b_synth_batch")
    questions_path = root / "questions.jsonl"
    questions_path.write_text(
        "\n".join(json.dumps(q) for q in SYNTH_QUESTIONS) + "\n",
        encoding="utf-8")
    batch_root = root / "batch"
    manifest = build_question_batch(
        questions_path, batch_root, batch_tag="s5bsynth",
        pool_provider=synth_pool_provider,
        provider_kind="scripted", synthetic_review=True)
    stub_path = root / "stub.json"
    stub_path.write_text(json.dumps({"strategy": "first_pool"}),
                         encoding="utf-8")
    old = os.environ.get("S5B_MODEL_STUB_SCRIPT")
    os.environ["S5B_MODEL_STUB_SCRIPT"] = str(stub_path)
    try:
        report = run_s5b_batch(
            batch_root, runs_root=root / "runs", workers=2,
            poll_s=0.2, gate_max_calls=50)
    finally:
        if old is None:
            os.environ.pop("S5B_MODEL_STUB_SCRIPT", None)
        else:
            os.environ["S5B_MODEL_STUB_SCRIPT"] = old
    return {
        "root": root, "questions_path": questions_path,
        "batch_root": batch_root, "manifest": manifest,
        "runs_root": root / "runs", "report": report,
    }


# ---------------------------------------------------------------- 客户端


def test_real_model_env_missing_fails_closed(monkeypatch) -> None:
    """凭证缺失 ⇒ fail-closed;detail 只报缺失名,零密钥。"""
    for key in ("V43_LLM_BASE_URL", "V43_LLM_API_KEY", "V43_LLM_MODEL",
                "LLM_API_BASE_URL", "LLM_API_KEY", "LLM_MODEL"):
        monkeypatch.delenv(key, raising=False)
    with pytest.raises(RealModelNotConfigured) as excinfo:
        RealModelAdapter.from_env()
    assert excinfo.value.detail["missing_env"] == [
        "V43_LLM_BASE_URL", "V43_LLM_API_KEY", "V43_LLM_MODEL"]


def test_real_model_env_v43_primary_and_v41_fallback(
        monkeypatch, tmp_path) -> None:
    """主名 V43_LLM_*;缺席时回退 v41 老名(值不进任何 detail)。"""
    for key in ("V43_LLM_BASE_URL", "V43_LLM_API_KEY", "V43_LLM_MODEL",
                "LLM_API_BASE_URL", "LLM_API_KEY", "LLM_MODEL"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("LLM_API_BASE_URL", "https://v41.example/api")
    monkeypatch.setenv("LLM_API_KEY", "v41-secret")
    monkeypatch.setenv("LLM_MODEL", "v41-model")
    adapter = RealModelAdapter.from_env(
        call_account_path=tmp_path / "calls.jsonl")
    assert adapter.model_id == "v41-model"
    assert adapter.client.base_url == "https://v41.example/api"
    assert adapter.timeout_s == 3600.0
    assert "v41-secret" not in json.dumps(adapter.identity_block())
    monkeypatch.setenv("V43_LLM_MODEL", "v43-model")
    adapter2 = RealModelAdapter.from_env()
    assert adapter2.model_id == "v43-model"


def test_real_model_identity_block_shape() -> None:
    """身份块:prompt 版本/request_params/timeout(进 run identity)。"""
    from pathway_v43.adapters.llm_client import OpenAICompatibleClient

    adapter = RealModelAdapter(OpenAICompatibleClient(
        base_url="https://example.invalid/api", api_key="k",
        model="m1", request_params={"reasoning_effort": "max"},
        timeout_s=3600.0, max_http_retries=4))
    block = adapter.identity_block()
    assert block["prompt_versions"]["proposals"] == \
        PROPOSALS_PROMPT_VERSION
    assert block["provider"] == "openai_compatible"
    assert block["model_id"] == "m1"
    assert block["request_params"] == {"reasoning_effort": "max"}
    assert block["timeout_s"] == 3600.0
    assert "k" not in json.dumps(block)


def test_proposals_user_payload_shape() -> None:
    """提示词载荷:底物/原子映射/池/反馈(零金标;确定性)。"""
    payload = build_proposals_user_payload(
        substrate_smiles="CCO",
        atom_id_map={"S_C_1": "C", "S_O_1": "O"},
        pool_entries=[{"hypothesis_id": "h1", "product_smiles": "CC=O",
                       "transformation_ref": "t1", "coproducts": []}],
        feedback_error={"kind": "json_field_error",
                        "response_excerpt": "x"})
    parsed = json.loads(payload)
    assert parsed["substrate_smiles"] == "CCO"
    assert parsed["substrate_atom_id_map"] == {"S_C_1": "C", "S_O_1": "O"}
    assert parsed["pool_hypotheses"][0]["hypothesis_id"] == "h1"
    assert parsed["format_feedback"]["error_kind"] == "json_field_error"
    assert build_proposals_user_payload(
        substrate_smiles="CCO", atom_id_map={}, pool_entries=[]) == \
        build_proposals_user_payload(
            substrate_smiles="CCO", atom_id_map={}, pool_entries=[])


def test_scripted_adapter_full_chain_in_process(tmp_path) -> None:
    """scripted 桩同一取响应调用序:register(scripted)→sent(网络 0)→
    responded;调用账本落 run 目录;响应进同一确定性解析器。"""
    questions_path = tmp_path / "q.jsonl"
    questions_path.write_text(
        json.dumps(SYNTH_QUESTIONS[0]) + "\n", encoding="utf-8")
    manifest = build_question_batch(
        questions_path, tmp_path / "batch", batch_tag="s5binproc",
        pool_provider=synth_pool_provider,
        provider_kind="scripted", synthetic_review=True)
    run_input = json.loads(
        (tmp_path / "batch/run_inputs/SYNTH-Q001.json").read_text(
            encoding="utf-8"))
    model = ScriptedRealModelAdapter(
        strategy="first_pool",
        call_account_path=tmp_path / "runs" / run_input["run_id"] /
        "s5b_real_calls.jsonl")
    out = start_ppv1_run(
        config=resolve_config(), runs_root=tmp_path / "runs",
        run_id=run_input["run_id"],
        smiles=run_input["substrate_smiles"],
        plan=run_input["plan"], model=model,
        profile_policy=S5B_DEFAULT_PROFILE_POLICY)
    assert out["native_export"]["export_digest"]
    conn = sqlite3.connect(
        str(tmp_path / "runs" / run_input["run_id"] / "pollutant.sqlite"))
    rows = conn.execute(
        "SELECT provider_kind, status, network_request_count,"
        " purpose FROM model_requests").fetchall()
    assert rows == [("scripted", "responded", 0, "proposals")]
    account = (tmp_path / "runs" / run_input["run_id"] /
               "s5b_real_calls.jsonl").read_text(encoding="utf-8")
    statuses = [json.loads(line)["status"]
                for line in account.splitlines()]
    assert "issued" in statuses and "responded" in statuses
    # 账本零密钥:只有存在性布尔,绝无密钥值
    assert '"api_key_set": true' not in account
    for line in account.splitlines():
        record = json.loads(line)
        assert record["provider_env"]["api_key_set"] is False
        assert "secret" not in line
    # 身份块进 run identity(prediction 块含 prompt 版本)
    identity = json.loads(
        (tmp_path / "runs" / run_input["run_id"] / "run_identity.json")
        .read_text(encoding="utf-8"))
    assert identity["prediction"]["prompt_versions"]["proposals"] == \
        PROPOSALS_PROMPT_VERSION
    assert identity["prediction"]["model_id"] == "s5b-scripted-stub-v1"


def test_real_transport_failure_marks_failed_and_stops(tmp_path) -> None:
    """传输失败(超时):mark_request_failed(占额不释放)+ 结构化
    run 失败(失败题留分母,导出仍产出)。"""
    questions_path = tmp_path / "q.jsonl"
    questions_path.write_text(
        json.dumps(SYNTH_QUESTIONS[0]) + "\n", encoding="utf-8")
    manifest = build_question_batch(
        questions_path, tmp_path / "batch", batch_tag="s5bfail",
        pool_provider=synth_pool_provider,
        provider_kind="scripted", synthetic_review=True)
    run_input = json.loads(
        (tmp_path / "batch/run_inputs/SYNTH-Q001.json").read_text(
            encoding="utf-8"))
    model = ScriptedRealModelAdapter(
        strategy="responses", fail_with={"error_kind": "timeout"},
        call_account_path=tmp_path / "runs" / run_input["run_id"] /
        "s5b_real_calls.jsonl")
    out = start_ppv1_run(
        config=resolve_config(), runs_root=tmp_path / "runs",
        run_id=run_input["run_id"],
        smiles=run_input["substrate_smiles"],
        plan=run_input["plan"], model=model,
        profile_policy=S5B_DEFAULT_PROFILE_POLICY)
    # drive 循环按既有语义把 run 级错误记进停止报告(不吞);导出仍
    # 产出(失败题留分母,判分按未命中计)
    assert out["stop"].get("run_error", {}).get("kind") == \
        "real_model_transport_failure"
    assert out["native_export"]["export_digest"]
    conn = sqlite3.connect(
        str(tmp_path / "runs" / run_input["run_id"] / "pollutant.sqlite"))
    rows = conn.execute(
        "SELECT provider_kind, status FROM model_requests").fetchall()
    assert ("scripted", "failed") in rows
    account = (tmp_path / "runs" / run_input["run_id"] /
               "s5b_real_calls.jsonl").read_text(encoding="utf-8")
    assert "failed" in account


def test_real_budget_zero_blocks_registration(tmp_path) -> None:
    """max_real_model_requests=0(默认)⇒ real 登记被拒 ⇒ 网络发送被
    阻止(传模型对象不自动补预算;S5-26 纪律)。"""
    questions_path = tmp_path / "q.jsonl"
    questions_path.write_text(
        json.dumps(SYNTH_QUESTIONS[0]) + "\n", encoding="utf-8")
    manifest = build_question_batch(
        questions_path, tmp_path / "batch", batch_tag="s5bnoquota",
        pool_provider=synth_pool_provider,
        provider_kind="real", synthetic_review=True)
    run_input = json.loads(
        (tmp_path / "batch/run_inputs/SYNTH-Q001.json").read_text(
            encoding="utf-8"))
    model = ScriptedRealModelAdapter(strategy="first_pool")
    out = start_ppv1_run(
        config=resolve_config(), runs_root=tmp_path / "runs",
        run_id=run_input["run_id"],
        smiles=run_input["substrate_smiles"],
        plan=run_input["plan"], model=model)  # 默认额度 0
    assert out["stop_reason"] == "budget_limit"
    conn = sqlite3.connect(
        str(tmp_path / "runs" / run_input["run_id"] / "pollutant.sqlite"))
    network = conn.execute(
        "SELECT SUM(network_request_count) FROM model_requests"
    ).fetchone()[0] or 0
    assert network == 0


def test_runflow_scripted_plan_without_model_object_unchanged(
        tmp_path) -> None:
    """钩子回归:无模型对象(或对象无 ppv1_real_fetch)⇒ 旧行为
    (plan.model.responses 脚本响应逐字节不变)。"""
    plan = {
        "pools": {"CCO": [synth_spec("B", "CC=O", "donor-B")]},
        "model": {"provider_kind": "scripted",
                  "responses": [json.dumps(
                      {"proposals": [], "rank_hypotheses": []})]},
    }

    class LegacyFakeModel:
        def identity_block(self):
            return {"enabled": True, "provider": "fake",
                    "model_id": "fake-1", "prompt_versions": {},
                    "policy_version": "p", "policy": {}}

    out = start_ppv1_run(
        config=resolve_config(), runs_root=tmp_path / "runs",
        run_id="legacy-shape", smiles="CCO", plan=plan,
        model=LegacyFakeModel(), scripted=True,
        profile_policy={"search_limits": {"max_real_model_requests": 0}})
    conn = sqlite3.connect(
        str(tmp_path / "runs/legacy-shape/pollutant.sqlite"))
    network = conn.execute(
        "SELECT SUM(network_request_count) FROM model_requests"
    ).fetchone()[0] or 0
    assert network == 0
    assert out["stop_reason"]  # 合法停止(弃权路径)


# ---------------------------------------------------------------- 构建器


def test_builder_end_to_end_synthetic(synth_batch) -> None:
    manifest = synth_batch["manifest"]
    assert manifest["n_questions"] == 3
    assert manifest["registration_order"] == [
        "SYNTH-Q001", "SYNTH-Q002", "SYNTH-Q003"]
    assert manifest["questions_source_sha256"]
    assert "products_smiles" not in json.dumps(manifest)
    for entry in manifest["entries"]:
        graph = json.loads(
            (synth_batch["batch_root"] / entry["graph_rel"]).read_text(
                encoding="utf-8"))
        validate_reference_graph(graph)
        qid = entry["qid"]
        # qid 进 root_entity.source_refs(evaluation-4 图侧一致性核)
        assert qid in graph["root_entity"]["source_refs"]
        # 一题一条参考边:根 → 全部金标产物
        assert len(graph["edges"]) == 1
        edge = graph["edges"][0]
        assert edge["step_scope"] == "net_reaction"
        assert edge["participant_list_status"] == "partial"
        assert edge["edge_status"] == "reference_only"
        assert edge["coefficient_status"] == "unknown"
        assert edge["condition_requirements"] == []
        roles = {p["role"] for p in edge["participants"]
                 if p["side"] == "product"}
        assert roles == {"principal_product"}
        # known_gaps 固定清单仅披露,不豁免分母(§4)
        assert set(S5B_KNOWN_GAPS) <= set(
            graph["coverage_statement"]["known_gaps"])
        assert graph["coverage_statement"]["not_evaluable_edge_ids"] == []
        # S1 一题一组;独立性永不 independent
        group = graph["source_groups"][0]
        assert group["independence_status"] in ("related", "unknown")
    entries = {e["qid"]: e for e in manifest["entries"]}
    # 重复底物(两题 CCO)⇒ related;单出现 ⇒ unknown
    assert entries["SYNTH-Q001"]["repeated_substrate"] is True
    assert entries["SYNTH-Q003"]["repeated_substrate"] is False
    graph1 = json.loads(
        (synth_batch["batch_root"] / entries["SYNTH-Q001"]["graph_rel"])
        .read_text(encoding="utf-8"))
    graph3 = json.loads(
        (synth_batch["batch_root"] / entries["SYNTH-Q003"]["graph_rel"])
        .read_text(encoding="utf-8"))
    assert graph1["source_groups"][0]["independence_status"] == "related"
    assert graph3["source_groups"][0]["independence_status"] == "unknown"
    # run 输入:根底物=substrate、池 = 底物侧供给、provider 声明
    run_input = json.loads(
        (synth_batch["batch_root"] / entries["SYNTH-Q001"]["run_input_rel"])
        .read_text(encoding="utf-8"))
    assert run_input["substrate_smiles"] == "CCO"
    assert run_input["plan"]["model"]["provider_kind"] == "scripted"
    assert len(run_input["plan"]["pools"]["CCO"]) == 2
    # split 清单:298 全卷 held_out
    split = json.loads(
        (synth_batch["batch_root"] / "split_manifest.json").read_text(
            encoding="utf-8"))
    assert {a["split"] for a in split["assignments"]} == {"held_out"}


def test_builder_output_root_guard(tmp_path) -> None:
    """仓内只许 gitignored 授权根;其它仓内路径零写入拒。"""
    repo = tmp_path / "repo"
    (repo / "reports").mkdir(parents=True)
    # 仓外合法
    assert check_output_root(
        tmp_path / "outside", repo_root=repo) == \
        (tmp_path / "outside").resolve()
    # 授权根(仓内 gitignored)合法
    assert check_output_root(
        repo / "reports/ppv1_s5b/x", repo_root=repo)
    # 仓内其它路径 ⇒ 拒
    with pytest.raises(S5bBuilderError) as excinfo:
        check_output_root(repo / "reports/other", repo_root=repo)
    assert excinfo.value.detail["kind"] == \
        "s5b_output_root_unauthorized"
    # 构建入口同样受守卫(零写入)
    questions_path = tmp_path / "q.jsonl"
    questions_path.write_text(
        json.dumps(SYNTH_QUESTIONS[0]) + "\n", encoding="utf-8")
    with pytest.raises(S5bBuilderError):
        build_question_batch(
            questions_path, repo / "reports/other",
            pool_provider=synth_pool_provider, repo_root=repo,
            synthetic_review=True)
    assert not (repo / "reports/other").exists()


def test_builder_question_validation(tmp_path) -> None:
    """qid 重复/坏行/缺字段 ⇒ 结构化拒;空卷拒。"""
    dup = tmp_path / "dup.jsonl"
    dup.write_text(
        json.dumps(SYNTH_QUESTIONS[0]) + "\n" +
        json.dumps(SYNTH_QUESTIONS[0]) + "\n", encoding="utf-8")
    with pytest.raises(S5bBuilderError) as excinfo:
        load_questions(dup)
    assert excinfo.value.detail["kind"] == "s5b_questions_duplicate_qid"
    bad = tmp_path / "bad.jsonl"
    bad.write_text("{not json\n", encoding="utf-8")
    with pytest.raises(S5bBuilderError):
        load_questions(bad)
    missing = tmp_path / "missing.jsonl"
    missing.write_text(
        json.dumps({"qid": "X", "substrate_smiles": "CCO"}) + "\n",
        encoding="utf-8")
    with pytest.raises(S5bBuilderError) as excinfo:
        load_questions(missing)
    assert excinfo.value.detail["kind"] == "s5b_questions_field_missing"
    empty = tmp_path / "empty.jsonl"
    empty.write_text("\n", encoding="utf-8")
    with pytest.raises(S5bBuilderError):
        load_questions(empty)
    with pytest.raises(S5bBuilderError):
        load_questions(tmp_path / "nonexistent.jsonl")


# ---------------------------------------------------------------- 编排器


def test_orchestrator_three_questions_two_workers_and_resume(
        synth_batch) -> None:
    report = synth_batch["report"]
    assert report["n_completed"] == 3
    assert report["n_failed"] == 0
    assert report["n_total"] == 3
    # 每题独立 run 根 + 终态 case 文件
    for entry in synth_batch["manifest"]["entries"]:
        run_dir = synth_batch["runs_root"] / entry["run_id"]
        assert (run_dir / "run_identity.json").is_file()
        assert (run_dir / "pollutant.sqlite").is_file()
        case = read_case(synth_batch["batch_root"], entry["qid"])
        assert case["status"] == "completed"
        assert case["export_digest"]
        assert case["model_calls"] >= 1
    # 闸门状态落盘(scripted 桩零真实请求)
    gate = json.loads(
        (synth_batch["batch_root"] / "gate" / "gate.json").read_text(
            encoding="utf-8"))
    assert gate["max_in_flight"] == 40
    assert gate["max_calls"] == 50
    # resume:已完成 qid SKIP(不发 worker、case 不改写)
    case_before = {
        qid: read_case(synth_batch["batch_root"], qid)
        for qid in synth_batch["manifest"]["registration_order"]}
    report2 = run_s5b_batch(
        synth_batch["batch_root"], runs_root=synth_batch["runs_root"],
        workers=2, poll_s=0.2, gate_max_calls=50)
    assert report2["n_completed"] == 3
    assert report2["skipped_already_terminal"] == 3
    for qid, case in case_before.items():
        assert read_case(synth_batch["batch_root"], qid) == case
    # 费用/usage 账:scripted 桩零 usage ⇒ 状态如实
    assert report2["account"]["model_calls_total"] >= 3
    assert report2["account"]["usage_status"] in (
        "none", "partial_unknown")


def test_orchestrator_failed_question_stays_in_denominator(
        tmp_path) -> None:
    """传输失败题:run 记 run_error、导出仍产出;case 披露失败原因;
    判分留分母算未命中(不剔题)。"""
    questions_path = tmp_path / "q.jsonl"
    questions_path.write_text(
        json.dumps(SYNTH_QUESTIONS[0]) + "\n", encoding="utf-8")
    batch_root = tmp_path / "batch"
    build_question_batch(
        questions_path, batch_root, batch_tag="s5bfailcase",
        pool_provider=synth_pool_provider,
        provider_kind="scripted", synthetic_review=True)
    stub_path = tmp_path / "stub.json"
    stub_path.write_text(json.dumps(
        {"strategy": "responses",
         "fail_with": {"error_kind": "timeout"}}), encoding="utf-8")
    old = os.environ.get("S5B_MODEL_STUB_SCRIPT")
    os.environ["S5B_MODEL_STUB_SCRIPT"] = str(stub_path)
    try:
        report = run_s5b_batch(
            batch_root, runs_root=tmp_path / "runs", workers=1,
            poll_s=0.2, gate_max_calls=10)
    finally:
        if old is None:
            os.environ.pop("S5B_MODEL_STUB_SCRIPT", None)
        else:
            os.environ["S5B_MODEL_STUB_SCRIPT"] = old
    case = read_case(batch_root, "SYNTH-Q001")
    # 导出产出 ⇒ 终态 completed;失败原因在 case 单列披露
    assert case["status"] == "completed"
    assert case["run_error"]["kind"] == "real_model_transport_failure"
    # 判分留分母:未命中(不剔题)
    agg = score_s5b_batch(
        batch_root, runs_root=tmp_path / "runs",
        data_scope="synthetic_rule_level")
    assert agg["denominator"] == 1
    assert agg["main_caliber"]["hit@1"] == 0
    assert agg["old_caliber_sensitivity"]["hit@1"] == 0


def test_orchestrator_rejects_unknown_qids_and_parameter_change(
        synth_batch) -> None:
    """指定 qid 不在冻结注册序 ⇒ 拒;同批根改编排参数 ⇒ 拒。"""
    with pytest.raises(Exception) as excinfo:  # noqa: B017
        run_s5b_batch(synth_batch["batch_root"],
                      runs_root=synth_batch["runs_root"],
                      qids=["NOT-A-QID"])
    assert "qid" in str(excinfo.value) or "not_registered" in \
        getattr(excinfo.value, "detail", {}).get("kind", "")
    with pytest.raises(Exception) as excinfo:  # noqa: B017
        run_s5b_batch(synth_batch["batch_root"],
                      runs_root=synth_batch["runs_root"],
                      gate_max_calls=999)
    assert getattr(excinfo.value, "detail", {}).get("kind") == \
        "s5b_orchestration_conflict"


# ---------------------------------------------------------------- 判分


def test_scoring_end_to_end_synthetic(synth_batch) -> None:
    agg = score_s5b_batch(
        synth_batch["batch_root"], runs_root=synth_batch["runs_root"],
        data_scope="synthetic_rule_level")
    assert agg["denominator"] == 3
    # 主口径:两题严格命中(Q003 池 spec 对 CCOCC 不适用 ⇒ 未命中)。
    # 命中事件在候选序列的位次受同 run 两个事件 (created_at,event_id)
    # 排序影响(两事件位次 ∈{1,2})⇒ hit@1 可能 0/1/2(冻结报告序的
    # 确定性以 run 为单位,不跨 run 断言);hit@3/@5 稳定为 2
    assert agg["main_caliber"]["hit@3"] == 2
    assert agg["main_caliber"]["hit@5"] == 2
    assert 0 <= agg["main_caliber"]["hit@1"] <= 2
    # 老口径敏感性(官方整串 any-one):同一两题命中(首中位次 ≤2)
    assert agg["old_caliber_sensitivity"]["hit@3"] == 2
    assert agg["old_caliber_sensitivity"]["hit@5"] == 2
    assert 0 <= agg["old_caliber_sensitivity"]["hit@1"] <= 2
    assert agg["old_caliber_anyof_multicomponent"]["hit@3"] == 2
    # 分桶单列(matched_strict / required node uncovered)
    assert agg["buckets"].get("matched_strict") == 2
    assert agg["buckets"].get("unmatched_required_node_uncovered") == 1
    # per-qid:命中题 rank ∈ {1,2};未命中题 rank=None
    by_qid = {row["qid"]: row for row in agg["per_qid"]}
    assert by_qid["SYNTH-Q001"]["main"]["rank"] in (1, 2)
    assert by_qid["SYNTH-Q001"]["old"]["rank"] in (1, 2)
    assert by_qid["SYNTH-Q003"]["main"]["rank"] is None
    assert by_qid["SYNTH-Q003"]["old"]["rank"] is None
    # CI 三档(S1 bootstrap / S2 按底物 / Wilson)
    for key in ("hit@1", "hit@3", "hit@5"):
        block = agg["confidence_intervals"][key]
        assert block["bootstrap_s1_by_source_group"]["low"] is not None
        assert block["bootstrap_s2_by_substrate"]["low"] is not None
        assert block["wilson_per_question"]["low"] is not None
    # 报告产物 + 题域标签
    for name in ("metrics.json", "report.md", "report_plain.md"):
        assert (synth_batch["batch_root"] / name).is_file()
    technical = (synth_batch["batch_root"] / "report.md").read_text(
        encoding="utf-8")
    plain = (synth_batch["batch_root"] / "report_plain.md").read_text(
        encoding="utf-8")
    assert "298" in technical and "298" in plain
    assert "hit@1" in technical
    assert "分母" in plain
    assert "dev" in technical  # 不外推 dev 声明
    # metrics 不含金标 SMILES 取值(判分结论非金标内容)
    metrics_text = (synth_batch["batch_root"] / "metrics.json").read_text(
        encoding="utf-8")
    assert "CC=O" not in metrics_text


def test_scoring_real_gate_requires_approved_prereg(synth_batch) -> None:
    """data_scope=real:显式 pending ⇒ 拒(评测器既有门);批准记录
    (approved / preregistration_confirmed 均可)⇒ 通过(qid_strict
    配对;程序只发 pending 族)。"""
    with pytest.raises(S5bScoringError) as excinfo:
        score_s5b_batch(synth_batch["batch_root"],
                        runs_root=synth_batch["runs_root"],
                        data_scope="real",
                        preregistration={
                            "approval_status":
                                "preregistration_pending_final_confirmation",
                            "preregistration_id": "prereg-x"})
    assert excinfo.value.detail["kind"] == \
        "s5b_preregistration_not_approved"
    approval = {
        "preregistration_id": "prereg-s5b-synth-test",
        "approval_status": "preregistration_confirmed",
        "approved_at": "2026-10-09T00:00:00+00:00",
        "user_authorization": "test-authorization-record",
    }
    (synth_batch["batch_root"] / "preregistration_approval.json"
     ).write_text(json.dumps(approval), encoding="utf-8")
    agg = score_s5b_batch(synth_batch["batch_root"],
                          runs_root=synth_batch["runs_root"],
                          data_scope="real")
    assert agg["denominator"] == 3
    # real 档全 qid_strict(evaluation-4/5:不落入 root_identity_fallback)
    assert set(agg["evaluator_pairing_bases"].values()) == {"qid_strict"}
    assert agg["evaluator_output_status"] == "pending_user_teacher_decision"
    assert agg["main_caliber"]["hit@3"] == 2
    assert agg["main_caliber"]["hit@5"] == 2
    # 清理批准记录(不影响后续测试)
    (synth_batch["batch_root"] / "preregistration_approval.json").unlink()


def test_preregistration_approval_helpers() -> None:
    """批准判定/归一/冻结稿状态行解析(升格 confirmed 兼容)。"""
    from pathway_v43.pollutant.s5b_scoring import (
        normalize_preregistration,
        preregistration_approved,
        preregistration_from_doc,
    )

    assert not preregistration_approved(None)
    assert not preregistration_approved({})
    assert not preregistration_approved(
        {"approval_status": "preregistration_pending_final_confirmation"})
    for status in ("approved", "confirmed", "preregistration_confirmed"):
        assert preregistration_approved({"approval_status": status})
    assert normalize_preregistration(
        {"approval_status": "preregistration_confirmed",
         "preregistration_id": "p1"})["approval_status"] == "approved"
    # 状态行解析:缺席文件 ⇒ None(不猜);confirmed 行 ⇒ 已批准
    assert preregistration_from_doc("/nonexistent/doc.md") is None
    doc = Path("/tmp/s5b_test_prereg_doc.md")
    doc.write_text(
        "x\n**状态行(机读)**:`preregistration_status = "
        "preregistration_confirmed`\n", encoding="utf-8")
    parsed = preregistration_from_doc(doc)
    assert parsed is not None
    assert parsed["approval_status"] == "preregistration_confirmed"
    assert preregistration_approved(parsed)
    doc.write_text(
        "x\n**状态行(机读)**:`preregistration_status = "
        "preregistration_pending_final_confirmation`\n", encoding="utf-8")
    parsed_pending = preregistration_from_doc(doc)
    assert parsed_pending is not None
    assert not preregistration_approved(parsed_pending)
    doc.unlink(missing_ok=True)


def test_scoring_synthetic_scope_uses_root_identity_fallback_allowed(
        synth_batch) -> None:
    """合成档(qid 两侧声明)qids strict;判分零 LLM 零网络声明。"""
    agg = score_s5b_batch(
        synth_batch["batch_root"], runs_root=synth_batch["runs_root"],
        data_scope="synthetic_rule_level")
    assert set(agg["evaluator_pairing_bases"].values()) == {"qid_strict"}
    assert agg["data_scope"] == "synthetic_rule_level"


def test_scoring_report_pass_line_semantics(synth_batch) -> None:
    """通过线语义:老口径历史锚;主口径系统性更严声明;不单报。"""
    agg = score_s5b_batch(
        synth_batch["batch_root"], runs_root=synth_batch["runs_root"],
        data_scope="synthetic_rule_level")
    assert agg["main_caliber"]["pass_lines"] == {
        "hit@1": 116, "hit@3": 128, "hit@5": 130}
    technical = (synth_batch["batch_root"] / "report.md").read_text(
        encoding="utf-8")
    assert "参照" in technical
    assert "两口径" in technical or "双口径" in technical
