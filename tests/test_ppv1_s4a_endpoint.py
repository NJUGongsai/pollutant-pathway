"""S4a endpoint 分账回归(公共 start/resume → 驱动 → 停止 → endpoint
四分账派生 → 独立持久化 → 首消费 → 原生结果对象;F01/F02/F03、
根碳账、终点证据、终点条件、失败状态、stale/integrity、resume 幂等)。

覆盖(任务书 §7 S4a + §8 验收矩阵 S4a 行):
- endpoint 四分账:execution_status / search_stop_reason /
  chemical_endpoint_assessment / bookkeeping_status 四者独立存在、
  互不代替;stop_reason_records 与 endpoint_records 分表独立持久化;
- F01 停止非终点:六类停止原因(budget/depth/no_candidate/awaiting/
  exhausted/user_stop)均不产生终点;零预算/零深度/空池三类公共链
  夹具;停止不覆盖已有有效终点证据;unexplored/deferred 保留;
- F02 未知依赖不被 recorded 洗白:上游假设依赖 unresolved(事件已
  recorded)⇒ 终点保持 unknown,依赖继承披露;控制组(supported
  依赖)同证据可支持;
- F03 来源去重:同一观察多包装/同来源多声明不增独立支持;来路
  保留;模型预测不产生 supported_*;
- 根碳账:账平只表示核查范围(不自动矿化);未知系数 ⇒ unknown;
  不同备选 CO₂ 不相加(逐事件列示,运行级聚合不产生);
- 终点证据:direct/inferred/model/no_evidence 四类;claim 字段
  充分性缺失 ⇒ unknown + 逐字段披露(证据不丢);
- 终点条件:essential 冲突假设保留不提交 ⇒ 终点 unknown;
- 失败状态:run_error ⇒ execution failed(不被转成功);
- 原生结果对象:字段组完整 + 确定性(同事实同 digest)+ 不同来路/
  备选/共同产物保留;
- endpoint 首消费:合法消费;stale(输入漂移)/corrupt(篡改)/
  未知版本/引用断裂/缺记录结构化拒,原行保全;
- resume/replay:重复 resume 不重复写 event/attempt/request/budget,
  endpoint payload_hash 与原生 digest 幂等。

基线 adf0287 上本文件为 collection 红(pollutant.endpoint /
native_result 缺失)。
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pathway_v43.config import resolve_config  # noqa: E402
from pathway_v43.pollutant.endpoint import (  # noqa: E402
    EndpointContractError,
    consume_run_endpoint,
    derive_run_endpoint,
    read_run_endpoint,
)
from pathway_v43.pollutant.native_result import (  # noqa: E402
    build_native_result,
    read_native_result,
)
from pathway_v43.pollutant.search import (  # noqa: E402
    SearchCrashInjection,
    SearchLedger,
)
from pathway_v43.pollutant.store import PollutantPathwayStore  # noqa: E402
from pathway_v43.storage.artifact_store import ArtifactStore  # noqa: E402
from pathway_v43.storage.run_identity import (  # noqa: E402
    PROFILE_POLLUTANT_PATHWAY_V1,
)
from pathway_v43.workflow.runner import resume_run, start_run  # noqa: E402

PY = sys.executable
ENV = {"PYTHONDONTWRITEBYTECODE": "1", "PATH": "/usr/bin:/bin"}


def spec(key: str, product: str, tref: str, **overrides) -> dict:
    d = {
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
    d.update(overrides)
    return d


def oxygen_req():
    return [{"key": "oxygen_regime", "level": "essential",
             "value": "aerobic", "source_refs": ["src:synthetic"]}]


def cyclic_dep(initial_supply: str):
    return [{"dependency_id": "dep-NAD", "kind": "cosubstrate_supply",
             "statement": "NAD+ regeneration cycle", "cyclic": True,
             "initial_supply": initial_supply}]


def mineralization_evidence(source: str = "src:study-A") -> dict:
    """充分字段的来源层直报矿化证据(direct_observation + 全字段)。"""
    return {
        "evidence_basis": "direct_observation",
        "endpoint_claim": "supported_mineralization",
        "source_refs": [source],
        "source_support_scope": "root-substrate-mineralization-report",
        "conditions_environment": "aerobic activated sludge 20C pH 7",
        "observation_window": "28d incubation",
        "detection_range": "CO2 trap + LC-MS 0.1-100 uM",
        "necessary_dependencies": ["aerobic consortium acclimated"],
        "root_carbon_fate_check_scope":
            "14C-labelled root carbon balance 92% recovered as CO2",
        "unverified_axes": ["rate", "community composition"],
        "proof_scope": "source-reported; not verified by this repo",
    }


def start(tmp_path: Path, run_id: str, plan: dict, *,
          profile_policy: dict | None = None) -> dict:
    return start_run(
        config=resolve_config(), runs_root=tmp_path / "runs",
        run_id=run_id, smiles="CCO", max_depth=3, max_expansions=10,
        max_frontier_width=2, finder=object(), scripted=True,
        profile=PROFILE_POLLUTANT_PATHWAY_V1, ppv1_plan=plan,
        profile_policy=profile_policy)


def ledger_for(runs_root: Path, run_id: str) -> SearchLedger:
    store = PollutantPathwayStore(runs_root / run_id / "pollutant.sqlite")
    artifacts = ArtifactStore(runs_root, run_id)
    return SearchLedger(store, artifacts, run_id)


def endpoint_row(runs_root: Path, run_id: str) -> dict:
    conn = sqlite3.connect(str(runs_root / run_id / "pollutant.sqlite"))
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT payload, payload_hash, created_at, updated_at FROM"
        " endpoint_records WHERE run_id = ?", (run_id,)).fetchone()
    conn.close()
    return dict(row) if row is not None else {}


# ---------------------------------------------------- 四分账 + 公共链


def test_endpoint_four_way_split_public_chain(tmp_path: Path) -> None:
    """公共 start → 驱动 → 停止 → 四分账:四者独立存在、分表持久化、
    summary 字段断言;无证据 ⇒ unknown(搜索记录不是终点结论)。"""
    plan = {"pools": {"CCO": [spec("B", "CC=O", "donor-B")]}}
    runs_root = tmp_path / "runs"
    out = start(tmp_path, "s4a", plan)
    endpoint = out["endpoint"]
    assert endpoint["execution_status"] == "completed"
    assert endpoint["search_stop_reason"] is not None
    assert endpoint["chemical_endpoint_assessment"] == "unknown"
    assert endpoint["bookkeeping_status"] == "closed_within_declared_scope"
    assert endpoint["independent_source_support_count"] == 0
    assert endpoint["inherited_unresolved_dependencies"] == 0
    # 四分账独立持久化:stop_reason_records 与 endpoint_records 分表
    conn = sqlite3.connect(str(runs_root / "s4a" / "pollutant.sqlite"))
    conn.row_factory = sqlite3.Row
    stop_rows = conn.execute(
        "SELECT payload, payload_hash FROM stop_reason_records").fetchall()
    endpoint_rows = conn.execute(
        "SELECT payload FROM endpoint_records").fetchall()
    assert len(stop_rows) == 1
    assert len(endpoint_rows) == 1
    stop_payload = json.loads(stop_rows[0]["payload"])
    record = json.loads(endpoint_rows[0]["payload"])
    # 停止原因独立行;endpoint 记录按 hash 引用(不复制语义、不代替)
    assert stop_payload["stop_report"]["primary"] == \
        endpoint["search_stop_reason"]
    assert record["search_stop_reason"]["stop_record_payload_hash"] == \
        stop_rows[0]["payload_hash"]
    # 四字段独立:execution/stop/chemical/bookkeeping 互不派生自彼此
    assert record["execution_status"] != record["bookkeeping_status"]
    assert record["chemical_endpoint_assessment"] == "unknown"
    assert record["schema_version"] == "ppv1-endpoint-2"
    assert record["derived_from"]["endpoint_policy_version"] == \
        "ppv1-endpoint-policy-2"
    conn.close()


def test_endpoint_resume_idempotent_no_duplicate_writes(
        tmp_path: Path) -> None:
    """resume/replay:重复 resume 不重复写 event/attempt/request/
    budget/action/预约;stop 视图与 endpoint 记录在本夹具(停止视图
    会话无关:零深度阻断,无检索耗尽/无会话 refusals)下幂等 ——
    payload_hash 与原生 digest 不变(同事实同摘要)。"""
    plan = {"pools": {"CCO": [spec("B", "CC=O", "donor-B")]}}
    runs_root = tmp_path / "runs"
    first = start(tmp_path, "idem", plan, profile_policy={"search_limits": {
        "max_search_depth": 0, "max_retrievals_per_parent": 2}})
    counts_before = first["counts"]
    hash_before = first["endpoint_record_payload_hash"]
    digest_before = first["native_result"]["content_digest"]
    second = resume_run(config=resolve_config(), runs_root=runs_root,
                        run_id="idem")
    assert second["counts"] == counts_before
    assert second["endpoint_record_payload_hash"] == hash_before
    assert second["native_result"]["content_digest"] == digest_before
    # 再次 resume(第三次)同样幂等
    third = resume_run(config=resolve_config(), runs_root=runs_root,
                       run_id="idem")
    assert third["counts"] == counts_before
    assert third["endpoint_record_payload_hash"] == hash_before
    # 事件/尝试/请求/预约行零新增(派生层零业务写入)
    conn = sqlite3.connect(str(runs_root / "idem" / "pollutant.sqlite"))
    one = lambda sql: conn.execute(sql).fetchone()[0]  # noqa: E731
    assert one("SELECT COUNT(*) FROM events") == 0
    actions_before = one("SELECT COUNT(*) FROM search_actions")
    assert actions_before > 0
    assert one("SELECT COUNT(*) FROM model_requests") == 0
    reservations_before = one("SELECT COUNT(*) FROM budget_reservations")
    assert reservations_before > 0
    conn.close()
    resume_run(config=resolve_config(), runs_root=runs_root, run_id="idem")
    conn = sqlite3.connect(str(runs_root / "idem" / "pollutant.sqlite"))
    assert conn.execute("SELECT COUNT(*) FROM search_actions"
                        ).fetchone()[0] == actions_before
    assert conn.execute("SELECT COUNT(*) FROM budget_reservations"
                        ).fetchone()[0] == reservations_before
    conn.close()


def test_endpoint_after_crash_resume_derives_once(tmp_path: Path) -> None:
    """B4 崩溃(事件已提交、记账未闭合)→ 公共 resume 恢复 → endpoint
    派生;事件/attempt 不重复;二次 resume 四分账字段不变(停止视图
    为会话派生,允许记录行随会话视图更新 —— 事件/预算零新增是硬边界)。"""
    plan = {"pools": {"CCO": [spec("B", "CC=O", "donor-B")]}}
    runs_root = tmp_path / "runs"
    from pathway_v43.pollutant.runflow import start_ppv1_run
    with pytest.raises(SearchCrashInjection):
        start_ppv1_run(
            config=resolve_config(), runs_root=runs_root, run_id="b4e",
            smiles="CCO", plan=plan, scripted=True,
            crash_after="after_event_submitted")
    out = resume_run(config=resolve_config(), runs_root=runs_root,
                     run_id="b4e")
    assert out["counts"]["events"] == 1
    assert out["endpoint"]["execution_status"] == "completed"
    assert out["endpoint"]["chemical_endpoint_assessment"] == "unknown"
    out2 = resume_run(config=resolve_config(), runs_root=runs_root,
                      run_id="b4e")
    assert out2["counts"]["events"] == 1
    assert out2["endpoint"]["execution_status"] == "completed"
    assert out2["endpoint"]["chemical_endpoint_assessment"] == "unknown"
    conn = sqlite3.connect(str(runs_root / "b4e" / "pollutant.sqlite"))
    assert conn.execute("SELECT COUNT(*) FROM search_attempts"
                        ).fetchone()[0] == 1
    conn.close()


# ---------------------------------------------------------------- F01


@pytest.mark.parametrize("reason", [
    "budget_limit", "depth_limit", "no_local_candidate",
    "awaiting_prediction", "exhausted_search", "user_stop"])
def test_f01_stop_reasons_never_produce_endpoint(tmp_path: Path,
                                                 reason: str) -> None:
    """F01(单元六原因全覆盖):任何停止原因只产生搜索停止状态;
    无独立终点证据 ⇒ chemical_endpoint_assessment 恒 unknown;停止
    原因保留在分账字段(不互相覆盖)。"""
    plan = {"pools": {"CCO": [spec("B", "CC=O", "donor-B")]}}
    runs_root = tmp_path / "runs"
    start(tmp_path, "f01u", plan)
    ledger = ledger_for(runs_root, "f01u")
    stop_report = {
        "primary": reason, "other_reasons": [],
        "unexplored": {"pending_actions": 0, "deferred": 0, "blocked": 0,
                       "claimed_actions": 0, "open_attempts": 0,
                       "pending_requests": 0},
        "budget": ledger.budget_snapshot("f01u"),
        "budget_exhausted_keys": [],
    }
    record = derive_run_endpoint(ledger, stop_report=stop_report)
    assert record["chemical_endpoint_assessment"] == "unknown"
    assert record["search_stop_reason"]["primary"] == reason
    assert record["execution_status"] == "completed"
    assert record["bookkeeping_status"] == "closed_within_declared_scope"


def test_f01_zero_budget_stop_endpoint_unknown(tmp_path: Path) -> None:
    """F01 公共链夹具(零预算):claim 被预算拒 ⇒ budget_limit 停止;
    endpoint unknown;预算原因保留;未探索保留。"""
    plan = {"pools": {"CCO": [spec("B", "CC=O", "donor-B")]}}
    out = start(tmp_path, "zb", plan, profile_policy={"search_limits": {
        "max_total_search_actions": 0}})
    assert out["stop_reason"] == "budget_limit"
    assert out["endpoint"]["chemical_endpoint_assessment"] == "unknown"
    assert out["endpoint"]["execution_status"] == "completed"
    assert out["counts"]["events"] == 0
    record = json.loads(endpoint_row(tmp_path / "runs", "zb")["payload"])
    assert record["search_stop_reason"]["unexplored"]["pending_actions"] >= 1


def test_f01_zero_depth_stop_blocked_objects_kept(tmp_path: Path) -> None:
    """F01 公共链夹具(零深度):depth_limit 停止;blocked 对象/原因
    保留在 stop 记录;endpoint unknown;检索上限放宽避免复合成因。"""
    plan = {"pools": {"CCO": [spec("B", "CC=O", "donor-B")]}}
    out = start(tmp_path, "zd", plan, profile_policy={"search_limits": {
        "max_search_depth": 0, "max_retrievals_per_parent": 2}})
    assert out["stop_reason"] == "depth_limit"
    assert out["endpoint"]["chemical_endpoint_assessment"] == "unknown"
    record = json.loads(endpoint_row(tmp_path / "runs", "zd")["payload"])
    blocked = record["search_stop_reason"]["unexplored"]["blocked_objects"]
    assert blocked and blocked[0]["reason"] == "depth_limit"
    assert record["bookkeeping_status"] == "unknown"


def test_f01_empty_pool_no_candidate(tmp_path: Path) -> None:
    """F01 公共链夹具(空池):no_local_candidate;endpoint unknown;
    检索上限放宽避免复合成因。"""
    plan = {"pools": {"CCO": []}}
    out = start(tmp_path, "ep", plan, profile_policy={"search_limits": {
        "max_retrievals_per_parent": 2}})
    assert out["stop_reason"] == "no_local_candidate"
    assert out["endpoint"]["chemical_endpoint_assessment"] == "unknown"
    assert out["counts"]["events"] == 0


def test_f01_stop_does_not_overwrite_valid_evidence(
        tmp_path: Path) -> None:
    """F01 反向:有效直报证据存在时,搜索停止(budget_limit)不覆盖
    终点证据 —— 评估 supported_mineralization 与停止原因并存。"""
    plan = {"pools": {"CCO": [spec("B", "CC=O", "donor-B")]},
            "endpoint_evidence": [mineralization_evidence()]}
    out = start(tmp_path, "sov", plan, profile_policy={"search_limits": {
        "max_total_search_actions": 0}})
    assert out["stop_reason"] == "budget_limit"
    assert out["endpoint"]["chemical_endpoint_assessment"] == \
        "supported_mineralization"
    record = json.loads(endpoint_row(tmp_path / "runs", "sov")["payload"])
    assert len(record["endpoint_evidence"]) == 1
    assert record["endpoint_evidence"][0]["observation_window"] == \
        "28d incubation"


# ---------------------------------------------------------------- F02


def test_f02_unresolved_dependency_blocks_endpoint_recorded_not_washed(
        tmp_path: Path) -> None:
    """F02:上游假设依赖 unresolved(下游事件已 recorded)⇒ 终点保持
    unknown;未解决依赖沿途保留并继承到 endpoint 记录;证据保留;
    条件事实快照保留。"""
    plan = {
        "condition_facts": [{"key": "oxygen_regime", "value": "aerobic",
                             "status": "known_present",
                             "source_ref": "src:synthetic"}],
        "pools": {"CCO": [spec(
            "B", "CC=O", "donor-B", dependencies=cyclic_dep("missing"))]},
        "endpoint_evidence": [mineralization_evidence()],
    }
    out = start(tmp_path, "f02", plan)
    # 事件已提交(recorded 下游事实),但依赖 unresolved
    assert out["counts"]["events"] == 1
    assert out["endpoint"]["chemical_endpoint_assessment"] == "unknown"
    assert out["endpoint"]["inherited_unresolved_dependencies"] >= 1
    record = json.loads(endpoint_row(tmp_path / "runs", "f02")["payload"])
    inherited = record["inherited_unresolved_dependencies"]
    assert any(d["dependency_id"] == "dep-NAD" for d in inherited)
    assert "unresolved_dependencies_inherited" in \
        record["evidence_summary"]["blocked_reasons"]
    # recorded 不洗白:证据保留 + 未解决依赖/来源/条件/proof scope 保留
    assert len(record["endpoint_evidence"]) == 1
    assert record["inherited_unresolved_dependencies"][0]["status"] == \
        "unresolved"
    assert record["endpoint_evidence"][0]["proof_scope"]
    assert record["conditions_snapshot"]["condition_keys_known"] == [
        "oxygen_regime"]


def test_f02_control_supported_dependency_same_evidence_supported(
        tmp_path: Path) -> None:
    """F02 控制组:依赖 supported(有启动供应支持)⇒ 同证据可支持
    终点(不因循环依赖本身全拒)。"""
    plan = {
        "pools": {"CCO": [spec(
            "B", "CC=O", "donor-B", dependencies=cyclic_dep("supported"))]},
        "endpoint_evidence": [mineralization_evidence()],
    }
    out = start(tmp_path, "f02c", plan)
    assert out["counts"]["events"] == 1
    assert out["endpoint"]["chemical_endpoint_assessment"] == \
        "supported_mineralization"
    assert out["endpoint"]["inherited_unresolved_dependencies"] == 0


# ---------------------------------------------------------------- F03


def test_f03_duplicate_wrapped_evidence_not_independent(
        tmp_path: Path) -> None:
    """F03:同一观察的多个包装(相同来源/声明/窗口/检测)⇒ 独立支持
    计数 1;来路保留(全部原始条目在 endpoint_evidence)。"""
    entry = mineralization_evidence()
    plan = {"pools": {"CCO": [spec("B", "CC=O", "donor-B")]},
            "endpoint_evidence": [dict(entry), dict(entry)]}
    out = start(tmp_path, "f03d", plan)
    summary = out["endpoint"]
    assert summary["independent_source_support_count"] == 1
    record = json.loads(endpoint_row(tmp_path / "runs", "f03d")["payload"])
    assert len(record["endpoint_evidence"]) == 2  # 来路保留
    dup = record["evidence_summary"]["duplicate_evidence_disclosures"]
    assert dup and dup[0]["wrapped_references"] == 2
    assert record["evidence_summary"]["distinct_observation_claims"] == 1


def test_f03_same_source_two_claims_one_support(tmp_path: Path) -> None:
    """F03:同一来源的两条不同声明 ⇒ 声明各自保留、独立支持仍 1
    (同一来源的多个引用不增加独立支持)。"""
    first = mineralization_evidence()
    second = mineralization_evidence()
    second["endpoint_claim"] = "supported_terminal_transformation_product"
    plan = {"pools": {"CCO": [spec("B", "CC=O", "donor-B")]},
            "endpoint_evidence": [first, second]}
    out = start(tmp_path, "f03s", plan)
    record = json.loads(endpoint_row(tmp_path / "runs", "f03s")["payload"])
    assert record["evidence_summary"]["distinct_observation_claims"] == 2
    assert record["evidence_summary"]["independent_source_support_count"] \
        == 1
    # 同来源两条声明都保留(来路不删)
    assert len(record["endpoint_evidence"]) == 2


def test_f03_distinct_sources_two_independent_supports(
        tmp_path: Path) -> None:
    """F03 正控:不同来源的两条同声明 ⇒ 独立支持 2。"""
    plan = {"pools": {"CCO": [spec("B", "CC=O", "donor-B")]},
            "endpoint_evidence": [
                mineralization_evidence("src:study-A"),
                mineralization_evidence("src:study-B")]}
    out = start(tmp_path, "f03n", plan)
    assert out["endpoint"]["independent_source_support_count"] == 2


def test_f03_model_prediction_and_inference_never_supported(
        tmp_path: Path) -> None:
    """F03/终点证据边界:模型预测/路径推断不能单独产生 supported_*;
    证据保留作披露(basis_counts);评估 unknown。"""
    model_entry = mineralization_evidence()
    model_entry["evidence_basis"] = "model_prediction"
    inferred_entry = mineralization_evidence()
    inferred_entry["evidence_basis"] = "inferred_from_pathway"
    plan = {"pools": {"CCO": [spec("B", "CC=O", "donor-B")]},
            "endpoint_evidence": [model_entry, inferred_entry]}
    out = start(tmp_path, "f03m", plan)
    assert out["endpoint"]["chemical_endpoint_assessment"] == "unknown"
    record = json.loads(endpoint_row(tmp_path / "runs", "f03m")["payload"])
    assert record["evidence_summary"]["basis_counts"] == {
        "inferred_from_pathway": 1, "model_prediction": 1}
    assert len(record["endpoint_evidence"]) == 2
    assert record["evidence_summary"]["direct_observation_entries"] == 0


def test_f03_no_evidence_basis_unknown(tmp_path: Path) -> None:
    """no_evidence ⇒ unknown;条目保留。"""
    entry = mineralization_evidence()
    entry["evidence_basis"] = "no_evidence"
    plan = {"pools": {"CCO": [spec("B", "CC=O", "donor-B")]},
            "endpoint_evidence": [entry]}
    out = start(tmp_path, "f03n0", plan)
    assert out["endpoint"]["chemical_endpoint_assessment"] == "unknown"


def test_endpoint_evidence_contract_rejects_bad_entries(
        tmp_path: Path) -> None:
    """证据声明契约:坏 basis/claim/字段形状 ⇒ 结构化拒(不猜、不
    静默清洗);endpoint 记录零写入、无 summary 成功返回;已提交
    事件如实保留(契约异常中止本次 endpoint 消费,不吞成成功终点)。"""
    from pathway_v43.pollutant.endpoint import \
        validate_endpoint_evidence
    with pytest.raises(EndpointContractError):
        validate_endpoint_evidence([{"evidence_basis": "guess",
                                     "endpoint_claim":
                                     "metabolic_handoff"}])
    with pytest.raises(EndpointContractError):
        validate_endpoint_evidence([{
            "evidence_basis": "direct_observation",
            "endpoint_claim": "supported_mineralization",
            "source_refs": "not-a-list"}])
    plan = {"pools": {"CCO": [spec("B", "CC=O", "donor-B")]},
            "endpoint_evidence": [{"evidence_basis": "hunch",
                                   "endpoint_claim":
                                   "metabolic_handoff"}]}
    with pytest.raises(EndpointContractError) as excinfo:
        start(tmp_path, "bad-ev", plan)
    assert excinfo.value.detail["kind"] == "endpoint_evidence_basis_invalid"
    # endpoint 派生中止:零 endpoint/stop 记录、零原生结果;已提交
    # 事件如实保留(不回滚已成立事实,也不吞成成功终点)
    conn = sqlite3.connect(str(tmp_path / "runs" / "bad-ev" /
                               "pollutant.sqlite"))
    one = lambda sql: conn.execute(sql).fetchone()[0]  # noqa: E731
    assert one("SELECT COUNT(*) FROM endpoint_records") == 0
    assert one("SELECT COUNT(*) FROM stop_reason_records") == 0
    assert one("SELECT COUNT(*) FROM events") == 1
    conn.close()
    assert not list((tmp_path / "runs" / "bad-ev" / "results").rglob(
        "native_result.json"))


# ---------------------------------------------------------------- 根碳账


def test_bookkeeping_closed_but_not_mineralization(tmp_path: Path) -> None:
    """根碳账:账平(全部已知系数)只表示核查范围内账面闭合 ⇒
    bookkeeping closed + endpoint unknown(账平不当矿化);根碳去向
    状态不由账目推导。"""
    plan = {"pools": {"CCO": [spec("B", "CC=O", "donor-B")]}}
    out = start(tmp_path, "bk", plan)
    assert out["counts"]["events"] == 1
    assert out["endpoint"]["bookkeeping_status"] == \
        "closed_within_declared_scope"
    assert out["endpoint"]["chemical_endpoint_assessment"] == "unknown"
    record = json.loads(endpoint_row(tmp_path / "runs", "bk")["payload"])
    bookkeeping = record["bookkeeping"]
    assert bookkeeping["root_carbon_fate_status"] == "unknown"
    assert bookkeeping["root_carbon_fate_inferred_from_bookkeeping"] is False
    assert bookkeeping["root_carbon_accounting_coverage"] == \
        "declared_participants_of_submitted_events"


def test_bookkeeping_unknown_coefficients(tmp_path: Path) -> None:
    """缺口控:未知系数 ⇒ 账目 unknown(不猜数值);事件仍保留。"""
    plan = {"pools": {"CCO": [spec("B", "CC=O", "donor-B",
                                   coefficient=None)]}}
    out = start(tmp_path, "bku", plan)
    assert out["counts"]["events"] == 1
    record = json.loads(endpoint_row(tmp_path / "runs", "bku")["payload"])
    assert record["bookkeeping_status"] == "unknown"
    assert record["bookkeeping"]["events_with_unknown_coefficients"]
    assert record["bookkeeping"]["participants_total"] > \
        record["bookkeeping"]["participants_known_coefficient"]


def test_co2_alternatives_not_summed_single_not_mineralization(
        tmp_path: Path) -> None:
    """备选分支控:两条备选反应各生成一个 CO₂ 产物 ⇒ 逐事件列示、
    不相加(运行级聚合值不产生);单项/双项 CO₂ 均不自动解释为根
    污染物矿化(无证据 ⇒ unknown)。"""
    plan = {"pools": {"CCO": [spec("B", "O=C=O", "donor-B"),
                              spec("C", "O=C=O", "donor-C")]}}
    out = start(tmp_path, "co2", plan)
    assert out["counts"]["events"] == 2
    record = json.loads(endpoint_row(tmp_path / "runs", "co2")["payload"])
    bookkeeping = record["bookkeeping"]
    occurrences = bookkeeping["co2_product_occurrences"]
    assert len(occurrences) == 2
    # 不同备选(不同 hypothesis)各自列示;不相加
    assert len({o["hypothesis_id"] for o in occurrences}) == 2
    assert bookkeeping["co2_aggregated"] is False
    assert bookkeeping["co2_run_total"] is None
    # CO₂ 存在 ≠ 矿化
    assert record["chemical_endpoint_assessment"] == "unknown"


# ---------------------------------------------------------------- 终点条件


def test_essential_conflict_endpoint_unknown_hypothesis_kept(
        tmp_path: Path) -> None:
    """终点条件:essential 冲突 ⇒ 假设保留不提交(零事件)⇒ endpoint
    unknown;条件事实快照保留(未知/已知计数不重评估)。"""
    plan = {
        "scenario_ref": "scenario-anaerobic",
        "condition_facts": [{"key": "oxygen_regime", "value": "anaerobic",
                             "status": "known_present",
                             "source_ref": "src:synthetic"}],
        "pools": {"CCO": [spec(
            "B", "CC=O", "donor-B", requirements=oxygen_req())]},
    }
    out = start(tmp_path, "conf", plan)
    assert out["counts"]["events"] == 0
    assert out["endpoint"]["chemical_endpoint_assessment"] == "unknown"
    record = json.loads(endpoint_row(tmp_path / "runs", "conf")["payload"])
    assert "oxygen_regime" in \
        record["conditions_snapshot"]["condition_keys_known"]


# ---------------------------------------------------------------- 失败状态


def test_execution_failed_on_model_structure_failure(
        tmp_path: Path) -> None:
    """失败状态:模型结构失败(run_error)⇒ execution failed,不被
    转成功;endpoint 保持 unknown;失败披露保留。"""
    plan = {"pools": {"CCO": [spec("B", "CC=O", "donor-B")]},
            "model": {"provider_kind": "scripted",
                      "responses": ['{"proposals": "not-a-list"}']}}
    out = start(tmp_path, "fail", plan)
    assert out["endpoint"]["execution_status"] == "failed"
    assert out["endpoint"]["chemical_endpoint_assessment"] == "unknown"
    record = json.loads(endpoint_row(tmp_path / "runs", "fail")["payload"])
    assert record["run_error"]["kind"] == "model_structure_failure"
    assert out["stop"].get("run_error")


# ---------------------------------------------------- 原生结果对象


NATIVE_GROUPS = (
    "native_result_version", "states", "state_appearances", "paths",
    "hypotheses", "events", "report_projections", "expansion_plans",
    "alternatives", "coproducts", "contexts", "provenance_records",
    "audit_production_reports", "expansion_outcomes", "deferred_entries",
    "blocked_entries", "search_actions", "search_attempts",
    "search_commit_records", "model_requests", "budget",
    "endpoint_record", "content_digest")


def _native_fixture(tmp_path: Path):
    plan = {"pools": {"CCO": [
        spec("B", "CC=O", "donor-B", coproducts=["[H][H]"]),
        spec("C", "CC=O", "donor-C")]},
        "schedule_budget": {"max_select": 1},
        "endpoint_evidence": [mineralization_evidence()]}
    runs_root = tmp_path / "runs"
    out = start(tmp_path, "nat", plan)
    return runs_root, out


def _routes_fixture(tmp_path: Path):
    """B/C 双备选均展开(无 selection cap)—— 不同来路保留的夹具。"""
    plan = {"pools": {"CCO": [spec("B", "CC=O", "donor-B"),
                              spec("C", "CC=O", "donor-C")]}}
    runs_root = tmp_path / "runs"
    out = start(tmp_path, "routes", plan)
    return runs_root, out


def test_native_result_completeness(tmp_path: Path) -> None:
    """原生结果完整性:字段组齐全且非空(共同产物/备选/audit/
    deferred/budget/endpoint 均入对象);共同产物不被截断。"""
    runs_root, out = _native_fixture(tmp_path)
    ledger = ledger_for(runs_root, "nat")
    verified = read_run_endpoint(ledger, "nat")
    native = build_native_result(ledger, endpoint_record=verified)
    for group in NATIVE_GROUPS:
        assert group in native, group
    assert native["states"]  # ChemicalState 全量
    assert native["events"] and len(native["events"]) == 1  # B 事件
    assert native["hypotheses"]
    assert native["alternatives"] and \
        len(native["alternatives"][0]["alternative_hypotheses"]) == 2
    coproducts = native["coproducts"]
    assert coproducts and len(coproducts[0]["coproduct_state_refs"]) == 1
    assert native["report_projections"] and native["expansion_plans"]
    assert native["audit_production_reports"]  # audit/proof scope 入对象
    assert native["audit_production_reports"][0]["production_payload"][
        "audit"]
    # 备选 deferred(selection cap)入对象,两类字段完整
    assert native["deferred_entries"]
    deferred = native["deferred_entries"][0]
    assert deferred["deferred_type"] == "alternative_reaction_deferred"
    assert deferred["reason"] == "selection_cap"
    assert native["budget"]["budget_snapshot"]["run_level"]
    assert native["endpoint_record"]["chemical_endpoint_assessment"] == \
        "supported_mineralization"
    assert native["contexts"]  # 条件/依赖(上下文 artifact 首消费)
    assert native["search_actions"] and native["search_attempts"]
    assert native["search_commit_records"]


def test_native_result_deterministic_rebuild(tmp_path: Path) -> None:
    """确定性:同一事实库两次独立构建(新 ledger/连接)⇒ 同 digest;
    落盘 artifact 读回验证摘要一致。"""
    runs_root, out = _native_fixture(tmp_path)
    ledger = ledger_for(runs_root, "nat")
    verified = read_run_endpoint(ledger, "nat")
    first = build_native_result(ledger, endpoint_record=verified)
    ledger2 = ledger_for(runs_root, "nat")  # 新连接、新对象
    verified2 = read_run_endpoint(ledger2, "nat")
    second = build_native_result(ledger2, endpoint_record=verified2)
    assert first["content_digest"] == second["content_digest"]
    assert out["native_result"]["content_digest"] == first["content_digest"]
    # 读回验证(摘要复算一致)
    reread = read_native_result(
        ArtifactStore(runs_root, "nat"),
        out["native_result"]["task_key"])
    assert reread["content_digest"] == first["content_digest"]


def test_native_result_preserves_distinct_routes(tmp_path: Path) -> None:
    """不同来路:同 CN 的两条备选(B/C)不被合并 —— 两个事件/假设/
    子路径各自保留;状态语义块同 ID(严格结构身份),出现/事件层
    来路分开。"""
    runs_root, out = _routes_fixture(tmp_path)
    ledger = ledger_for(runs_root, "routes")
    verified = read_run_endpoint(ledger, "routes")
    native = build_native_result(ledger, endpoint_record=verified)
    assert len(native["events"]) == 2
    event_hypotheses = {e["hypothesis_id"] for e in native["events"]}
    assert len(event_hypotheses) == 2  # 不按 CN 合并成单反应
    paths = [p for p in native["paths"] if p["origin"] != "root"]
    assert len(paths) >= 2  # 子路径身份(父+事件+产物)各自保留
    assert len({p["path_id"] for p in paths}) == len(paths)
    # 同产物(CC=O)状态语义行唯一,但两条事件来路各自引用
    product_states = [s for s in native["states"]
                      if json.loads(s["payload"] if isinstance(
                          s["payload"], str) else json.dumps(
                          s["payload"])).get("smiles_isomeric") == "CC=O"]
    assert len(product_states) == 1
    refs_in_events = []
    for e in native["events"]:
        participants = e["payload"]["participants"]
        refs_in_events += [p["state_ref"] for p in participants
                           if p["side"] == "product"]
    assert refs_in_events.count(product_states[0]["state_id"]) == 2


# ---------------------------------------------------- 首消费/stale


def test_consume_valid_endpoint_record(tmp_path: Path) -> None:
    """首消费正控:合法记录消费成功(版本/hash/引用/staleness 全过)。"""
    runs_root, out = _native_fixture(tmp_path)
    ledger = ledger_for(runs_root, "nat")
    record = consume_run_endpoint(ledger, "nat")
    assert record["chemical_endpoint_assessment"] == \
        "supported_mineralization"
    assert record["execution_status"] == "completed"


def _raw_endpoint_row(runs_root: Path, run_id: str) -> tuple:
    conn = sqlite3.connect(str(runs_root / run_id / "pollutant.sqlite"))
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT payload, payload_hash FROM endpoint_records WHERE"
        " run_id = ?", (run_id,)).fetchone()
    conn.close()
    return dict(row)["payload"], dict(row)["payload_hash"]


def test_consume_refuses_stale_record(tmp_path: Path) -> None:
    """staleness 负控:输入事实漂移(动作行状态被改)⇒ 拒绝消费
    (endpoint_record_stale);原行保全(不重算新 hash 洗白)。"""
    runs_root, out = _native_fixture(tmp_path)
    conn = sqlite3.connect(str(runs_root / "nat" / "pollutant.sqlite"))
    conn.execute(
        "UPDATE search_actions SET status = 'done' WHERE run_id = 'nat'"
        " AND status = 'deferred'")
    conn.commit()
    conn.close()
    payload_before, hash_before = _raw_endpoint_row(runs_root, "nat")
    ledger = ledger_for(runs_root, "nat")
    with pytest.raises(EndpointContractError) as excinfo:
        consume_run_endpoint(ledger, "nat")
    assert excinfo.value.detail["kind"] == "endpoint_record_stale"
    assert "search_actions_digest" in \
        excinfo.value.detail["changed_inputs"]
    payload_after, hash_after = _raw_endpoint_row(runs_root, "nat")
    assert (payload_after, hash_after) == (payload_before, hash_before)


def test_consume_refuses_corrupt_record(tmp_path: Path) -> None:
    """integrity 负控:篡改 payload 不改 hash ⇒ 复算不一致拒;原行
    保全(不覆盖)。"""
    runs_root, out = _native_fixture(tmp_path)
    conn = sqlite3.connect(str(runs_root / "nat" / "pollutant.sqlite"))
    payload = json.loads(conn.execute(
        "SELECT payload FROM endpoint_records WHERE run_id = 'nat'"
    ).fetchone()[0])
    payload["chemical_endpoint_assessment"] = "supported_mineralization"
    payload["chemical_endpoint_assessment"] = "unknown"  # 篡改
    conn.execute(
        "UPDATE endpoint_records SET payload = ? WHERE run_id = 'nat'",
        (json.dumps(payload),))
    conn.commit()
    conn.close()
    ledger = ledger_for(runs_root, "nat")
    with pytest.raises(EndpointContractError) as excinfo:
        consume_run_endpoint(ledger, "nat")
    assert excinfo.value.detail["kind"] == "endpoint_record_corrupt"


def test_consume_refuses_unknown_version(tmp_path: Path) -> None:
    """版本门负控:自洽改写 schema_version(重算 hash)⇒ 未知版本拒
    (不猜迁移)。"""
    from pathway_v43.domain.models import content_hash
    runs_root, out = _native_fixture(tmp_path)
    conn = sqlite3.connect(str(runs_root / "nat" / "pollutant.sqlite"))
    payload = json.loads(conn.execute(
        "SELECT payload FROM endpoint_records WHERE run_id = 'nat'"
    ).fetchone()[0])
    payload["schema_version"] = "ppv1-endpoint-99"
    conn.execute(
        "UPDATE endpoint_records SET payload = ?, payload_hash = ? WHERE"
        " run_id = 'nat'",
        (json.dumps(payload, sort_keys=True), content_hash(payload)))
    conn.commit()
    conn.close()
    ledger = ledger_for(runs_root, "nat")
    with pytest.raises(EndpointContractError) as excinfo:
        consume_run_endpoint(ledger, "nat")
    assert excinfo.value.detail["kind"] == \
        "endpoint_record_version_unknown"


def test_consume_refuses_broken_stop_reference(tmp_path: Path) -> None:
    """跨表引用负控:stop 记录行被删 ⇒ 引用断裂拒(四分账独立
    持久化的一致性面)。"""
    runs_root, out = _native_fixture(tmp_path)
    conn = sqlite3.connect(str(runs_root / "nat" / "pollutant.sqlite"))
    conn.execute("DELETE FROM stop_reason_records WHERE run_id = 'nat'")
    conn.commit()
    conn.close()
    ledger = ledger_for(runs_root, "nat")
    with pytest.raises(EndpointContractError) as excinfo:
        consume_run_endpoint(ledger, "nat")
    assert excinfo.value.detail["kind"] == "endpoint_stop_reference_mismatch"


def test_consume_missing_record_refused_strict(tmp_path: Path) -> None:
    """缺记录:严格消费拒(不猜默认);非严格读取本 run 记录成功。"""
    plan = {"pools": {"CCO": []}}
    runs_root = tmp_path / "runs"
    start(tmp_path, "miss", plan)
    ledger = ledger_for(runs_root, "miss")
    assert read_run_endpoint(ledger, "miss", strict=False) is not None
    with pytest.raises(EndpointContractError) as excinfo:
        consume_run_endpoint(ledger, "no-such-run")
    assert excinfo.value.detail["kind"] == "endpoint_record_missing"
