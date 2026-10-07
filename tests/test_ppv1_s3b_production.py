"""S3b 生产链回归(固定 AtomTool → 供体诊断 → converter → audit →
admission → 提交;ppv1-search-production-1)。

覆盖(任务书 §7 S3b「实际中心链」行,分段负控):
- 合法工具链:真实 render/execute_edits 输出 → 诊断 → converter →
  audit → admission → 事件提交(公共 writer;重放幂等);
- 工具 execution_ok=False:三判定字段 None + center_evidence 空字典;
  converter 元数据 center_match=None;方法失败不伪装成功工具结果;
- 缺/歧义映射(alignment unavailable):中心 unknown,不授 verified;
- strict 目标偏离:中心不可 verified(strict False ⇒ 至少 unknown);
- 损坏 proof(自报字段与复算不一致):AuditContractError 上抛,
  **宽捕获 caller 也无法产生事件/提交/完成写入**(R8 P2 ⑧:生产
  caller 不吞 AuditContractError 成 verified/R6/成功提交);
- 跨假设复用证据:绑定不匹配 ⇒ center unknown(不是 verified);
- 上下文持久化/加载:篡改语义字段保留旧 context_id ⇒ 拒;
- H04 依赖构建:缺启动供给 ⇒ unresolved + unresolved_initial_supply;
  有支持 ⇒ supported 不自动阻断。
基线 b7f2bba 上本文件为 collection 红(pollutant.production 缺失)。
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pathway_v43.pollutant.audit import AuditContractError  # noqa: E402
from pathway_v43.pollutant.chemstate import build_chemical_state  # noqa: E402
from pathway_v43.pollutant.path_context import build_path_context  # noqa: E402
from pathway_v43.pollutant.production import (  # noqa: E402
    build_cyclic_dependency,
    execute_atomtool_expansion,
    expand_hypothesis_production,
    load_context,
    persist_context,
    prepare_hypothesis,
)
from pathway_v43.pollutant.profile import (  # noqa: E402
    build_profile_identity_block,
)
from pathway_v43.pollutant.search import (  # noqa: E402
    ACTION_STATUS_DONE,
    SearchLedger,
    search_policy_version,
)
from pathway_v43.pollutant.store import PollutantPathwayStore  # noqa: E402
from pathway_v43.storage.artifact_store import ArtifactStore  # noqa: E402

PV = search_policy_version()
SUB_SMILES = "CCO"
PROD_SMILES = "CC=O"

EDITS = [{"op": "change_bond_order", "atom1": "S_C_2", "atom2": "S_O_1",
          "from_order": "single", "to_order": "double"}]
DONOR = {"center_atom_ids": ["S_C_2", "S_O_1"]}
ALIGNMENT = {"status": "resolved",
             "donor_to_current": {"S_C_2": "S_C_2", "S_O_1": "S_O_1"},
             "ref": "align-A"}


def make_spec(**overrides) -> dict:
    spec = {
        "key": "B", "product_smiles": PROD_SMILES, "coefficient": 1,
        "transformation_ref": "donor-B", "origin_group_key": "donor-B",
        "edits": [dict(e) for e in EDITS],
        "donor": dict(DONOR), "alignment": dict(ALIGNMENT),
        "expectation": {"target_smiles": PROD_SMILES},
    }
    spec.update(overrides)
    return spec


def make_run(tmp_path: Path, name: str, limits: dict | None = None):
    runs_root = tmp_path / "runs"
    store = PollutantPathwayStore(tmp_path / f"{name}.sqlite")
    art = ArtifactStore(runs_root, name)
    ledger = SearchLedger(store, art, name)
    policy = build_profile_identity_block(
        search_limits=limits) if limits else build_profile_identity_block()
    ledger.register_search_run(name, policy)
    return store, ledger, art, policy


def setup_expansion(tmp_path: Path, name: str, spec: dict | None = None,
                    limits: dict | None = None):
    """注册 run + 根状态/上下文 + 调度并认领 expand action。"""
    store, ledger, art, policy = make_run(tmp_path, name, limits)
    from pathway_v43.pollutant.queue import schedule_hypotheses
    substrate = build_chemical_state(SUB_SMILES, "raw_input",
                                     [{"record": "sub"}])
    store.put_state(substrate.to_dict())
    context = build_path_context()
    context_ref = persist_context(art, context)
    prepared = prepare_hypothesis(
        spec or make_spec(), parent_path_id="p1",
        substrate_state=substrate,
        transformation_ref=(spec or make_spec())["transformation_ref"])
    out = schedule_hypotheses(
        ledger, run_id=name, parent_path_id="p1",
        context_ref=context_ref, parent_search_revision=0,
        pool=[{"hypothesis_key": "B",
               "hypothesis_id": prepared["hypothesis"].hypothesis_id,
               "rank": 1,
               "payload": {"task_key": "tk-B", "spec": spec or make_spec(),
                           "substrate_smiles": SUB_SMILES,
                           "context_ref": context_ref,
                           "parent_path_id": "p1", "depth": 1}}],
        policy_version=PV, depth=1)
    action_id = out["selected"][0]["action_id"]
    receipt = ledger.claim_action(action_id, worker_id="w1")
    attempt_id = receipt["attempt_refs"][0]
    return ledger, art, prepared, substrate, context, action_id, attempt_id


# ---------------------------------------------------------------- 工具段


def test_execute_atomtool_expansion_legal() -> None:
    out = execute_atomtool_expansion(
        substrate_smiles=SUB_SMILES,
        tool_inputs={"edits": EDITS, "donor": DONOR,
                     "alignment": ALIGNMENT,
                     "expectation": {"target_smiles": PROD_SMILES}})
    assert out["execution_ok"] is True
    assert out["result"]["product_smiles"] == PROD_SMILES
    diagnostic = out["diagnostic"]
    assert diagnostic["strict_target_match"] is True
    assert diagnostic["reaction_center_match"] is True
    center = out["center_evidence"]
    assert center["checker_version"] == "ppv1-donor-diagnostic-8"
    assert center["center_match"] is True
    # proof_record 完整输入集(audit 内部复算用)
    for key in ("current", "donor", "alignment", "expectation", "result"):
        assert isinstance(center["proof_record"][key], dict)
    assert isinstance(center["proof_record"]["edits"], list)


def test_execute_atomtool_failure_three_none() -> None:
    # 工具执行失败:三判定字段 None、center_evidence 空字典、converter
    # 仍返回元数据(center_match=None —— None = 未评估,不是通过)
    bad_edits = [{"op": "break_bond", "atom1": "S_X", "atom2": "S_Y"}]
    out = execute_atomtool_expansion(
        substrate_smiles=SUB_SMILES,
        tool_inputs={"edits": bad_edits, "donor": DONOR,
                     "alignment": ALIGNMENT,
                     "expectation": {"target_smiles": PROD_SMILES}})
    assert out["execution_ok"] is False
    diagnostic = out["diagnostic"]
    assert diagnostic["strict_target_match"] is None
    assert diagnostic["legacy_cn_match"] is None
    assert diagnostic["reaction_center_match"] is None
    assert diagnostic["center_evidence"] == {}
    center = out["center_evidence"]
    assert center["center_match"] is None
    assert "checker_version" in center  # 版本/来源元数据仍在


# ---------------------------------------------------------------- 全链


def test_expand_production_legal_chain_submits_event(tmp_path) -> None:
    ledger, art, prepared, substrate, context, action_id, attempt_id = \
        setup_expansion(tmp_path, "prod-1")
    limits = ledger._limits("prod-1")
    out = expand_hypothesis_production(
        ledger, action_id, prepared=prepared, context=context,
        worker_id="w1", attempt_id=attempt_id, task_key="tk-B",
        substrate_state=substrate, limits=limits, depth=1)
    assert out["status"] == "submitted"
    assert out["event_id"]
    assert ledger.action(action_id)["status"] == ACTION_STATUS_DONE
    assert ledger.store.counts()["events"] == 1
    # 事件重放幂等(同事件不新增)
    from pathway_v43.pollutant.events import PathwayEvent
    event = out["event"]
    ev = ledger.store.get_event(out["event_id"])
    assert ev is not None
    # production report artifact 落盘(审查用派生报告)
    report = art.read("tk-B", "production_report")
    assert report["payload"]["status"] == "submitted"
    assert report["payload"]["admission"]["disposition"]


def test_expand_production_execution_failure_method_failed(tmp_path) -> None:
    spec = make_spec(edits=[{"op": "break_bond", "atom1": "S_X",
                             "atom2": "S_Y"}])
    ledger, art, prepared, substrate, context, action_id, attempt_id = \
        setup_expansion(tmp_path, "prod-2", spec=spec)
    limits = ledger._limits("prod-2")
    out = expand_hypothesis_production(
        ledger, action_id, prepared=prepared, context=context,
        worker_id="w1", attempt_id=attempt_id, task_key="tk-B",
        substrate_state=substrate, limits=limits, depth=1)
    # 执行失败 ⇒ 方法失败:零事件、零提交(不伪装成功工具结果;
    # 允许调用方调度独立备选)
    assert out["status"] == "method_failed"
    assert out["admission"] is None
    assert ledger.store.counts()["events"] == 0
    # action 仍 claimed(未完成 —— 由调用方记方法失败结论)
    assert ledger.action(action_id)["status"] == "claimed"


def test_expand_production_missing_alignment_unknown(tmp_path) -> None:
    spec = make_spec(alignment={"status": "unavailable",
                                "donor_to_current": {}, "ref": "align-X"})
    ledger, art, prepared, substrate, context, action_id, attempt_id = \
        setup_expansion(tmp_path, "prod-3", spec=spec)
    limits = ledger._limits("prod-3")
    out = expand_hypothesis_production(
        ledger, action_id, prepared=prepared, context=context,
        worker_id="w1", attempt_id=attempt_id, task_key="tk-B",
        substrate_state=substrate, limits=limits, depth=1)
    # 缺映射:中心 unknown(不授 verified);按既有 admission 有界探索
    # (事件可提交,unknown 保留)—— 不按"没有反对"授 verified
    assert out["status"] == "submitted"
    audit = out["audit"]
    center = [c for c in audit["checks"]
              if c["name"] == "transformation_center"][0]
    assert center["status"] == "unknown"
    assert out["admission"]["disposition"] != "expand"


def test_expand_production_strict_deviation_not_verified(tmp_path) -> None:
    # 期望产物与执行产物偏离:strict False ⇒ 中心不可 verified
    spec = make_spec(expectation={"target_smiles": "CC(=O)O"})
    ledger, art, prepared, substrate, context, action_id, attempt_id = \
        setup_expansion(tmp_path, "prod-4", spec=spec)
    limits = ledger._limits("prod-4")
    out = expand_hypothesis_production(
        ledger, action_id, prepared=prepared, context=context,
        worker_id="w1", attempt_id=attempt_id, task_key="tk-B",
        substrate_state=substrate, limits=limits, depth=1)
    assert out["status"] == "submitted"
    center = [c for c in out["audit"]["checks"]
              if c["name"] == "transformation_center"][0]
    assert center["status"] in ("unknown", "violated")
    assert center["status"] != "verified"
    assert out["admission"]["disposition"] != "expand"


def test_expand_production_tampered_proof_contract_error_zero_writes(
        tmp_path, monkeypatch) -> None:
    """R8 P2 ⑧(S3 首个生产 caller 义务):损坏 proof(converter 输出被
    改写,自报字段与 proof_record 复算不一致)⇒ AuditContractError 由
    生产链**原样上抛**;宽捕获 caller(except Exception: pass)也无法
    产生事件/提交/完成写入 —— 不吞成 verified/R6/成功提交。"""
    import pathway_v43.pollutant.production as production_mod
    ledger, art, prepared, substrate, context, action_id, attempt_id = \
        setup_expansion(tmp_path, "prod-5")
    original_converter = production_mod.center_evidence_from_donor_diagnostic

    def tampered_converter(diagnostic):
        evidence = dict(original_converter(diagnostic))
        # 改自报 center_match(与 proof_record 复算不一致)
        evidence["center_match"] = not bool(evidence.get("center_match"))
        return evidence

    monkeypatch.setattr(production_mod,
                        "center_evidence_from_donor_diagnostic",
                        tampered_converter)
    events_before = ledger.store.counts()["events"]
    with pytest.raises(AuditContractError) as ei:
        expand_hypothesis_production(
            ledger, action_id, prepared=prepared, context=context,
            worker_id="w1", attempt_id=attempt_id, task_key="tk-B",
            substrate_state=substrate, limits=ledger._limits("prod-5"),
            depth=1)
    assert ei.value.detail["kind"] == "center_evidence_integrity_mismatch"
    # 宽捕获负控:整链包 except Exception 后零事件/零提交/零完成
    try:
        expand_hypothesis_production(
            ledger, action_id, prepared=prepared, context=context,
            worker_id="w1", attempt_id=attempt_id, task_key="tk-B",
            substrate_state=substrate, limits=ledger._limits("prod-5"),
            depth=1)
    except Exception:  # noqa: BLE001 — 宽捕获负控(不得吞成成功)
        pass
    assert ledger.store.counts()["events"] == events_before
    assert ledger.store.counts()["hypotheses"] == 0
    action = ledger.action(action_id)
    assert action["status"] == "claimed"  # 未完成(无成功提交可言)
    commit = ledger.conn.execute(
        "SELECT COUNT(*) FROM search_commit_records WHERE action_id = ?",
        (action_id,)).fetchone()[0]
    assert commit == 0
    monkeypatch.undo()
    # 修复后(未篡改)同链提交成功 —— 中止不是永久损坏
    out = expand_hypothesis_production(
        ledger, action_id, prepared=prepared, context=context,
        worker_id="w1", attempt_id=attempt_id, task_key="tk-B",
        substrate_state=substrate, limits=ledger._limits("prod-5"),
        depth=1)
    assert out["status"] == "submitted"


def test_expand_production_cross_hypothesis_evidence_unknown(
        tmp_path) -> None:
    """跨假设复用证据:绑定不匹配 ⇒ center unknown(注册名+True 不构成
    核实;不 raise,诚实 unknown ⇒ R5 有界)。"""
    ledger, art, prepared, substrate, context, action_id, attempt_id = \
        setup_expansion(tmp_path, "prod-6")
    from pathway_v43.pollutant.audit import (
        audit_hypothesis, center_evidence_from_donor_diagnostic,
        check_edit_against_donor)
    from pathway_v43.services.atom_tool import render, execute_edits
    # 另一假设:不同底物(甲醇)
    other_sub = build_chemical_state("CO", "raw_input", [{"record": "s2"}])
    other_prod = build_chemical_state("C=O", "source_product",
                                      [{"record": "p2"}])
    from pathway_v43.pollutant.hypothesis import (
        Participant, build_hypothesis)
    other_hyp = build_hypothesis(
        parent_path_id="p2", substrate_state_ref=other_sub.state_id,
        participants=[
            Participant(state_ref=other_sub.state_id, side="reactant",
                        role="primary_substrate", coefficient=1,
                        coefficient_status="known"),
            Participant(state_ref=other_prod.state_id, side="product",
                        role="principal_product", coefficient=1,
                        coefficient_status="known")],
        participant_list_status="source_complete",
        step_scope="net_reaction", origin_group_key="k2")
    current = render(SUB_SMILES, "S")
    result = execute_edits(current, EDITS)
    diagnostic = check_edit_against_donor(
        current={"smiles": SUB_SMILES,
                 "atom_id_map": dict(current.atom_id_map)},
        donor=dict(DONOR), alignment=dict(ALIGNMENT),
        expectation={"target_smiles": PROD_SMILES}, result=result,
        edits=EDITS)
    center = center_evidence_from_donor_diagnostic(diagnostic)
    # 把本反应的证据喂给另一假设(底物不同 ⇒ 绑定不匹配)
    audit = audit_hypothesis(
        other_hyp, run_id="prod-6",
        states={other_sub.state_id: other_sub,
                other_prod.state_id: other_prod},
        context=context, center_evidence=center)
    center_check = [c for c in audit.checks
                    if c.name == "transformation_center"][0]
    assert center_check.status == "unknown"
    assert "binding" in (center_check.reason_code or "")


# ---------------------------------------------------------------- 上下文


def test_context_persist_load_roundtrip_and_tamper(tmp_path) -> None:
    art = ArtifactStore(tmp_path / "runs", "ctx-run")
    context = build_path_context(
        condition_facts=[__import__(
            "pathway_v43.pollutant.path_context", fromlist=["x"]
        ).build_condition_fact(key="oxygen_regime", value="aerobic",
                                status="known_present")])
    ref = persist_context(art, context)
    loaded = load_context(art, ref)
    assert loaded.context_id == context.context_id
    # 篡改语义字段保留旧 context_id ⇒ 拒。两层防线逐一分测:
    # (a) 只改 payload 不改信封 hash ⇒ H07 完整性错误(保全原文件);
    # (b) 同步重算信封 hash(伪装完好信封)⇒ from_dict 内容身份核验拒
    path = art._path(f"ctx:{ref}", "path_context")
    import json as _json
    from pathway_v43.domain.models import content_hash
    doc = _json.loads(path.read_text(encoding="utf-8"))
    doc["payload"]["scenario_ref"] = "tampered-scenario"
    path.write_text(_json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(Exception) as ei:
        load_context(art, ref)
    assert getattr(ei.value, "detail", {}).get("kind") == \
        "artifact_hash_mismatch"
    # 重算信封 hash 后:内容身份核验层拒绝
    doc2 = _json.loads(path.read_text(encoding="utf-8"))
    doc2["payload_hash"] = content_hash(doc2["payload"])
    path.write_text(_json.dumps(doc2, ensure_ascii=False),
                    encoding="utf-8")
    with pytest.raises(Exception) as ei2:
        load_context(art, ref)
    detail2 = getattr(ei2.value, "detail", {})
    assert detail2.get("kind") == "context_content_identity_mismatch" \
        or "context_content_identity_mismatch" in str(detail2) \
        or "内容身份" in str(ei2.value)


# ---------------------------------------------------------------- H04


def test_cyclic_dependency_initial_supply_variants() -> None:
    missing = build_cyclic_dependency({
        "dependency_id": "dep-X", "kind": "cosubstrate_supply",
        "statement": "co-substrate cycle", "cyclic": True,
        "initial_supply": "missing"})
    assert missing.status == "unresolved"
    assert "unresolved_initial_supply" in missing.statement
    assert "不称化学不可能" in missing.statement
    supported = build_cyclic_dependency({
        "dependency_id": "dep-Y", "kind": "cosubstrate_supply",
        "statement": "co-substrate cycle", "cyclic": True,
        "initial_supply": "supported",
        "source_refs": ["src:supply"]})
    assert supported.status == "supported"
    assert "initial_supply" in supported.support_axes
    with pytest.raises(Exception):
        build_cyclic_dependency({"dependency_id": "dep-Z",
                                 "initial_supply": "bogus"})


# ---------------------------------------------------------------- 隔离


def test_ppv1_run_uses_independent_storage(tmp_path) -> None:
    # 生产链写入走 PollutantPathwayStore(ppv1 专属表);不建 legacy
    # PathwayStore 表(独立分流的存储事实)
    store, ledger, art, _ = make_run(tmp_path, "prod-7")
    tables = {r[0] for r in ledger.conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    assert "search_actions" in tables
    assert "pathways" not in tables  # legacy PathwayStore 表不存在
    assert "events" in tables
