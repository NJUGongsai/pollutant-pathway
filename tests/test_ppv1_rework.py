"""S0–S2 回修反例回归测试(Codex 复核 §5 边界证据的仓库化;无金标)。

覆盖 F01–F11/P2 中未被 domain/s2 文件覆盖的存储与导入反例:
- F04 同结构不同来源不冲突(语义/出现拆分)、两步连续路径导入;
- F07 事件事务参照完整性(缺产物状态回滚、state_ref 欺骗、重放缺
  附随记录报损坏、展开互斥、假设关联缺失);
- F08 未知 schema 写前拒绝(store 构造不修改未知库;identity 未知
  版本拒绝;v1 兼容不扩展为任意未知);
- F09 子路径缺存档退 CN-only(不借根结构);
- F10 provenance 映射修正 + model_ref 导入保留 + 持久化。
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pathway_v43.pollutant.chemstate import (  # noqa: E402
    STRUCTURE_ORIGIN_RAW_INPUT,
    STRUCTURE_ORIGIN_SOURCE_PRODUCT,
    build_chemical_state,
)
from pathway_v43.pollutant.events import (  # noqa: E402
    EventContractError,
    ParticipantStateError,
    build_event_states,
    build_expansion_plan,
    build_pathway_event,
    build_report_projection,
)
from pathway_v43.pollutant.hypothesis import (  # noqa: E402
    COEFFICIENT_UNKNOWN,
    PARTICIPANT_LIST_PARTIAL,
    PARTICIPANT_ROLE_PRIMARY_SUBSTRATE,
    PARTICIPANT_ROLE_PRINCIPAL_PRODUCT,
    PARTICIPANT_SIDE_PRODUCT,
    PARTICIPANT_SIDE_REACTANT,
    HypothesisContractError,
    Participant,
    build_hypothesis,
)
from pathway_v43.pollutant.legacy_reader import (  # noqa: E402
    import_legacy_run,
)
from pathway_v43.pollutant.provenance import (  # noqa: E402
    build_support_groups,
    map_legacy_card,
)
from pathway_v43.pollutant.store import (  # noqa: E402
    Ppv1EventConflict,
    Ppv1LedgerCorrupt,
    Ppv1StoreSchemaError,
    PollutantPathwayStore,
)

ETHANOL = "CCO"
ACETALDEHYDE = "CC=O"
ACETIC_ACID = "CC(=O)O"


def _pstate(smiles, origin=STRUCTURE_ORIGIN_SOURCE_PRODUCT, refs=None):
    return build_chemical_state(smiles, origin, refs)


def _sub(ref):
    return Participant(state_ref=ref, side=PARTICIPANT_SIDE_REACTANT,
                       role=PARTICIPANT_ROLE_PRIMARY_SUBSTRATE,
                       coefficient=None,
                       coefficient_status=COEFFICIENT_UNKNOWN)


def _prod(ref):
    return Participant(state_ref=ref, side=PARTICIPANT_SIDE_PRODUCT,
                       role=PARTICIPANT_ROLE_PRINCIPAL_PRODUCT,
                       coefficient=None,
                       coefficient_status=COEFFICIENT_UNKNOWN)


def _simple_hypothesis(substrate_state, product_state, path="p1",
                       origin_group="og"):
    return build_hypothesis(
        parent_path_id=path, substrate_state_ref=substrate_state.state_id,
        participants=[_sub(substrate_state.state_id),
                      _prod(product_state.state_id)],
        participant_list_status=PARTICIPANT_LIST_PARTIAL,
        step_scope="net_reaction", origin_group_key=origin_group)


# ---------------------------------------------------------------- F04


def test_f04_same_structure_different_sources_no_conflict(tmp_path) -> None:
    """F04 复现:同一 CCO、不同 source_refs,第二次 put_state 不再冲突;
    语义复用,出现记录全部保留。"""
    store = PollutantPathwayStore(tmp_path / "ppv1.sqlite")
    s1 = _pstate(ETHANOL, refs=[{"role": "root_input"}])
    s2 = _pstate(ETHANOL, refs=[{"role": "legacy_event_product",
                                 "event_id": "e1"}])
    assert s1.state_id == s2.state_id
    store.put_state(s1.to_dict())
    store.put_state(s2.to_dict())  # v1 在此抛 Ppv1EventConflict
    appearances = store.state_appearances(s1.state_id)
    assert len(appearances) == 2  # 两个来源都保留(不覆盖、不丢失)
    counts = store.counts()
    assert counts["states"] == 1
    assert counts["state_appearances"] == 2
    store.close()


def test_f04_true_semantic_conflict_still_rejected(tmp_path) -> None:
    """语义冲突(同 state_id 不同结构事实)仍然拒绝(fail-closed)。"""
    store = PollutantPathwayStore(tmp_path / "ppv1.sqlite")
    good = _pstate(ETHANOL).to_dict()
    store.put_state(good)
    forged = dict(good)
    forged["formal_charge"] = 99  # 篡改结构语义
    with pytest.raises(Ppv1EventConflict):
        store.put_state(forged)
    store.close()


def test_f04_two_step_legacy_path_imports(tmp_path) -> None:
    """F04 复现:两步旧路径(共享中间物乙醛)连续导入不再失败。"""
    from pathway_v43.storage.pathway_store import PathwayStore

    run_dir = tmp_path / "legacy_run"
    run_dir.mkdir(parents=True)
    store = PathwayStore(run_dir / "pathway.sqlite")
    root_pid = store.ensure_run("r2", ETHANOL, _pstate(ETHANOL).cn_identity)
    (run_dir / "run_identity.json").write_text(json.dumps({
        "schema_version": "v43-identity-1",
        "inputs": {"root_smiles": ETHANOL,
                   "root_identity": _pstate(ETHANOL).cn_identity}}),
        encoding="utf-8")
    cn_acetal = _pstate(ACETALDEHYDE).cn_identity
    cn_acetic = _pstate(ACETIC_ACID).cn_identity

    def _card(eid, kind, products):
        return {"evidence_id": eid, "kind": kind, "source_id": eid,
                "condition_fit": "unknown", "_content_hash": eid * 64,
                "products": products}

    # 步骤 1:CCO → CC=O(recorded)
    r1 = store.submit_event(
        run_id="r2", parent_path_id=root_pid,
        substrate_identity=_pstate(ETHANOL).cn_identity,
        evidence=_card("E1", "recorded_reaction", [
            {"position": 0, "product_smiles": ACETALDEHYDE,
             "product_smiles_full": ACETALDEHYDE,
             "product_identity": cn_acetal}]),
        products=[{"position": 0, "product_smiles": ACETALDEHYDE,
                   "product_smiles_full": ACETALDEHYDE,
                   "product_identity": cn_acetal}],
        expandable_path_ids=[
            __import__("pathway_v43.storage.pathway_store",
                       fromlist=["product_path_id"]).product_path_id(
                "r2",
                __import__("pathway_v43.storage.pathway_store",
                           fromlist=["event_id_for"]).event_id_for(
                    "r2", root_pid,
                    _pstate(ETHANOL).cn_identity, "E1"), 0)],
        deferred_path_ids=[])
    step1_event = r1["event_id"]
    child_pid = r1["path_ids"][0]
    # 步骤 2:CC=O → CC(=O)O(recorded;底物 = 步骤 1 的中间物)
    store.submit_event(
        run_id="r2", parent_path_id=child_pid,
        substrate_identity=cn_acetal,
        evidence=_card("E2", "recorded_reaction", [
            {"position": 0, "product_smiles": ACETIC_ACID,
             "product_smiles_full": ACETIC_ACID,
             "product_identity": cn_acetic}]),
        products=[{"position": 0, "product_smiles": ACETIC_ACID,
                   "product_smiles_full": ACETIC_ACID,
                   "product_identity": cn_acetic}],
        expandable_path_ids=[], deferred_path_ids=[])
    store.close()
    assert step1_event

    new_store = PollutantPathwayStore(tmp_path / "new" / "ppv1.sqlite")
    result = import_legacy_run(run_dir, new_run_id="r-new",
                               target_store=new_store)
    assert result["n_created"] == 2  # v1 在共享中间物处失败,只留 1 事件
    assert new_store.counts()["events"] == 2
    # 中间物乙醛:两种出现记录(步骤 1 产物 + 步骤 2 底物)全部保留
    acetal_state = _pstate(ACETALDEHYDE)
    appearances = new_store.state_appearances(acetal_state.state_id)
    assert len(appearances) == 2
    store_roles = {a.get("structure_origin") for a in appearances}
    assert store_roles == {STRUCTURE_ORIGIN_SOURCE_PRODUCT}
    new_store.close()


# ---------------------------------------------------------------- F07


def test_f07_submit_missing_product_state_rolls_back(tmp_path) -> None:
    """F07 复现:只提交底物 state(缺产物 state)⇒ 事务回滚,不产生
    悬空引用事件。"""
    store = PollutantPathwayStore(tmp_path / "ppv1.sqlite")
    sub = _pstate(ETHANOL, STRUCTURE_ORIGIN_RAW_INPUT)
    prod = _pstate(ACETALDEHYDE)
    hyp = _simple_hypothesis(sub, prod)
    event = build_pathway_event(hyp, run_id="r7", context_hash="ctx")
    with pytest.raises(Ppv1LedgerCorrupt, match="状态缺失"):
        store.submit_event(
            event,
            report_projection=build_report_projection(
                hyp, max_reportable=1,
                ranked_state_refs=[prod.state_id]).to_dict(),
            expansion_plan=build_expansion_plan(
                hyp, expanded=[prod.state_id], deferred=[],
                not_tracked=[]).to_dict(),
            states=[sub.to_dict()],  # 只给底物:v1 返回 created=True
            hypothesis_dict=hyp.to_dict())
    assert store.counts()["events"] == 0  # 回滚:零事件
    store.close()


def test_f07_state_ref_spoof_rejected() -> None:
    """F07 复现:为某 state_ref 提供另一分子结构 ⇒ 拒绝(不返回
    张冠李戴的状态集)。"""
    sub = _pstate(ETHANOL, STRUCTURE_ORIGIN_RAW_INPUT)
    prod = _pstate(ACETALDEHYDE)
    hyp = _simple_hypothesis(sub, prod)
    with pytest.raises(ParticipantStateError, match="state_ref"):
        build_event_states(
            hyp, raw_structures={
                sub.state_id: ETHANOL,
                prod.state_id: ETHANOL})  # 用乙醇冒充乙醛的 state_ref


def test_f07_substrate_anchor_violation_rejected() -> None:
    """F07 复现:substrate_state_ref 不属于反应物锚点 ⇒ 构造期拒绝。"""
    sub = _pstate(ETHANOL, STRUCTURE_ORIGIN_RAW_INPUT)
    prod = _pstate(ACETALDEHYDE)
    with pytest.raises(HypothesisContractError,
                       match="底物锚点违约"):
        build_hypothesis(
            parent_path_id="p1", substrate_state_ref="cs_someone_else",
            participants=[_sub(sub.state_id), _prod(prod.state_id)],
            participant_list_status=PARTICIPANT_LIST_PARTIAL,
            step_scope="net_reaction", origin_group_key="og")


def test_f07_replay_with_missing_projection_reports_corrupt(tmp_path) -> None:
    """F07 复现:删除已提交事件的投影后重放 ⇒ 账本损坏,不默默成功。"""
    store = PollutantPathwayStore(tmp_path / "ppv1.sqlite")
    sub = _pstate(ETHANOL, STRUCTURE_ORIGIN_RAW_INPUT)
    prod = _pstate(ACETALDEHYDE)
    hyp = _simple_hypothesis(sub, prod)
    event = build_pathway_event(hyp, run_id="r7b", context_hash="ctx")
    report = build_report_projection(
        hyp, max_reportable=1, ranked_state_refs=[prod.state_id])
    plan = build_expansion_plan(hyp, expanded=[prod.state_id], deferred=[],
                                not_tracked=[])
    states = [sub.to_dict(), prod.to_dict()]
    store.submit_event(event, report_projection=report.to_dict(),
                       expansion_plan=plan.to_dict(), states=states,
                       hypothesis_dict=hyp.to_dict())
    # 模拟损坏:直接删投影行(绕过 API 的物理破坏)
    store.conn.execute(
        "DELETE FROM report_projections WHERE event_id = ?",
        (event.event_id,))
    store.conn.commit()
    with pytest.raises(Ppv1LedgerCorrupt, match="缺少附随记录"):
        store.submit_event(event, report_projection=report.to_dict(),
                           expansion_plan=plan.to_dict(), states=states,
                           hypothesis_dict=hyp.to_dict())
    store.close()


def test_f07_expansion_status_mutex() -> None:
    """F07 复现:同一产物同时 expanded 与 deferred ⇒ 拒绝。"""
    sub = _pstate(ETHANOL, STRUCTURE_ORIGIN_RAW_INPUT)
    prod = _pstate(ACETALDEHYDE)
    hyp = _simple_hypothesis(sub, prod)
    with pytest.raises(EventContractError, match="互斥"):
        build_expansion_plan(hyp, expanded=[prod.state_id],
                             deferred=[prod.state_id], not_tracked=[])


def test_f07_missing_hypothesis_association_rolls_back(tmp_path) -> None:
    """F07:事件提交缺假设关联(未提供且不在库)⇒ 回滚。"""
    store = PollutantPathwayStore(tmp_path / "ppv1.sqlite")
    sub = _pstate(ETHANOL, STRUCTURE_ORIGIN_RAW_INPUT)
    prod = _pstate(ACETALDEHYDE)
    hyp = _simple_hypothesis(sub, prod)
    event = build_pathway_event(hyp, run_id="r7c", context_hash="ctx")
    with pytest.raises(Ppv1LedgerCorrupt, match="关联假设"):
        store.submit_event(
            event,
            report_projection=build_report_projection(
                hyp, max_reportable=1,
                ranked_state_refs=[prod.state_id]).to_dict(),
            expansion_plan=build_expansion_plan(
                hyp, expanded=[prod.state_id], deferred=[],
                not_tracked=[]).to_dict(),
            states=[sub.to_dict(), prod.to_dict()])
    assert store.counts()["events"] == 0
    store.close()


# ---------------------------------------------------------------- F08


def test_f08_unknown_store_schema_rejected_before_write(tmp_path) -> None:
    """F08 复现:含 future-store-999 的已有库,构造函数在 DDL/写入之前
    拒绝,文件字节不变。"""
    foreign = tmp_path / "foreign.sqlite"
    conn = sqlite3.connect(str(foreign))
    conn.execute(
        "CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    conn.execute(
        "INSERT INTO meta (key, value) VALUES ('schema_version', "
        "'future-store-999')")
    conn.execute(
        "CREATE TABLE states (state_id TEXT PRIMARY KEY, payload TEXT)")
    conn.commit()
    conn.close()
    before = foreign.read_bytes()
    with pytest.raises(Ppv1StoreSchemaError, match="future-store-999"):
        PollutantPathwayStore(foreign)
    assert foreign.read_bytes() == before  # 字节不变(v1 会被建表改写)
    # 新文件正常初始化
    fresh = PollutantPathwayStore(tmp_path / "fresh" / "new.sqlite")
    assert fresh.counts()["events"] == 0
    fresh.close()


def test_f08_identity_schema_version_gate() -> None:
    """F08 复现:future-identity-999 身份在 resume 比较被拒(v1 兼容
    不扩展为任意未知版本)。"""
    from pathway_v43.storage import run_identity as ri

    saved = {
        "schema_version": "future-identity-999",
        "domain_schema_version": "v43-domain-1",
        "inputs": {"root_smiles": "CCO", "root_identity": "CCO"},
        "strategy": {}, "asset_identity": {}, "v3_engine_code": {},
        "prediction": {}, "adjudication": {}, "molecode": {},
        "code_identity": {}, "dependency_versions": {},
    }
    current = dict(saved)
    current["schema_version"] = ri.IDENTITY_SCHEMA_VERSION
    with pytest.raises(ri.IdentityMismatch):
        ri.check_resume_identity(saved, current)


# ---------------------------------------------------------------- F09


def test_f09_child_missing_archive_falls_back_cn_only_not_root(tmp_path):
    """F09 复现:子路径存档产物行被删 ⇒ 导入底物退 CN-only,绝不
    借根污染物 CCO 冒充;旧库字节不变。"""
    from pathway_v43.storage.pathway_store import (
        PathwayStore, event_id_for, product_path_id,
    )

    run_dir = tmp_path / "legacy_missing"
    run_dir.mkdir(parents=True)
    store = PathwayStore(run_dir / "pathway.sqlite")
    root_pid = store.ensure_run("r9", ETHANOL,
                                _pstate(ETHANOL).cn_identity)
    (run_dir / "run_identity.json").write_text(json.dumps({
        "schema_version": "v43-identity-1",
        "inputs": {"root_smiles": ETHANOL,
                   "root_identity": _pstate(ETHANOL).cn_identity}}),
        encoding="utf-8")
    cn_acetal = _pstate(ACETALDEHYDE).cn_identity
    cn_acetic = _pstate(ACETIC_ACID).cn_identity
    card1 = {"evidence_id": "E9", "kind": "recorded_reaction",
             "source_id": "E9", "condition_fit": "unknown",
             "_content_hash": "E9" * 64,
             "products": [{"position": 0, "product_smiles": ACETALDEHYDE,
                           "product_smiles_full": ACETALDEHYDE,
                           "product_identity": cn_acetal}]}
    r1 = store.submit_event(
        run_id="r9", parent_path_id=root_pid,
        substrate_identity=_pstate(ETHANOL).cn_identity, evidence=card1,
        products=card1["products"],
        expandable_path_ids=[
            product_path_id("r9", event_id_for(
                "r9", root_pid, _pstate(ETHANOL).cn_identity, "E9"), 0)],
        deferred_path_ids=[])
    child_pid = r1["path_ids"][0]
    # 步骤 2:乙醛 → 乙酸(其底物 = 子路径,存档在步骤 1 的产物行)
    card2 = {"evidence_id": "E92", "kind": "recorded_reaction",
             "source_id": "E92", "condition_fit": "unknown",
             "_content_hash": "E92" * 32,
             "products": [{"position": 0, "product_smiles": ACETIC_ACID,
                           "product_smiles_full": ACETIC_ACID,
                           "product_identity": cn_acetic}]}
    store.submit_event(
        run_id="r9", parent_path_id=child_pid,
        substrate_identity=cn_acetal, evidence=card2,
        products=card2["products"], expandable_path_ids=[],
        deferred_path_ids=[])
    store.close()
    # 物理删除存档产物行(乙醛的档案没了;子底物只剩 CN)
    db = run_dir / "pathway.sqlite"
    conn = sqlite3.connect(str(db))
    conn.execute("DELETE FROM event_products WHERE position = 0"
                 " AND event_id IN (SELECT event_id FROM reaction_events"
                 " WHERE evidence_id = 'E9')")
    conn.commit()
    conn.close()
    db_before = db.read_bytes()

    new_store = PollutantPathwayStore(tmp_path / "new9" / "ppv1.sqlite")
    imported = import_legacy_run(run_dir, new_run_id="r9n",
                                 target_store=new_store)
    assert imported["n_created"] == 2  # 导入完成(结构化降级,不失败)
    assert any("substrate_structure_legacy_cn_only" in n
               for n in imported["uncertainty_notes"])
    # 步骤 2 事件的假设底物状态:CN-only,绝不是 raw_input/根结构 CCO
    hyps = [new_store.get_hypothesis(e["hypothesis_id"])
            for e in new_store.list_events("r9n")]
    cn_only_subs = [h for h in hyps if new_store.get_state(
        h["substrate_state_ref"])["structure_origin"]
        == "legacy_cn_only"]
    assert len(cn_only_subs) == 1
    sub_state = new_store.get_state(cn_only_subs[0]["substrate_state_ref"])
    assert sub_state["representation_fidelity"]["formal_charge"] == \
        "unknown"
    # 根底物仍从 root_smiles 恢复(raw_input),未被 cn_only 污染
    root_subs = [h for h in hyps if new_store.get_state(
        h["substrate_state_ref"])["structure_origin"] == "raw_input"]
    assert len(root_subs) == 1
    assert db.read_bytes() == db_before  # 旧库零写回
    new_store.close()


# ---------------------------------------------------------------- F10


def test_f10_unidentified_rule_maps_unknown() -> None:
    """F10 复现:无标识来源的 rule ⇒ unknown(不默认生物转化规则)。"""
    info = map_legacy_card({"kind": "rule_application",
                            "source_id": "engine_pred",
                            "match_type": "rule_template_application",
                            "asset_sources": []})
    assert info.source_origin == "unknown"
    assert info.evidence_basis == "rule_derived"
    # 显式标识照常映射
    info2 = map_legacy_card({"kind": "rule_application",
                             "source_id": "uspto_batch",
                             "match_type": "rule_template_application",
                             "asset_sources": []})
    assert info2.source_origin == "patent_template"


def test_f10_composite_source_retrieval_component_analog() -> None:
    """F10 复现:组合来源的 retrieval/corpus 成分 ⇒ analog_transfer
    (不是生物转化规则)。"""
    info = map_legacy_card({
        "kind": "rule_application",
        "source_id": "envipath+retrieval",
        "match_type": "rule_template_application",
        "asset_sources": [
            {"role": "envipath", "asset_file": "a.jsonl",
             "asset_sha256": "x"},
            {"role": "retrieval", "asset_file": "b.jsonl",
             "asset_sha256": "y"},
        ]})
    by_role = {c.role: c.source_origin for c in info.components}
    assert by_role["envipath"] == "biotransformation_rule"
    assert by_role["retrieval"] == "analog_transfer"


def test_f10_study_map_not_boolean_switch() -> None:
    """F10 复现:同一论文的两个库 ID;study_map 归并 ⇒ 1 个独立支持;
    无 study_map ⇒ None(不用布尔开关冒充研究身份)。"""
    cards = [
        {"evidence_id": "E1", "kind": "recorded_reaction",
         "source_id": "dbA#1", "asset_file": "f", "asset_sha256": "s"},
        {"evidence_id": "E2", "kind": "recorded_reaction",
         "source_id": "dbB#7", "asset_file": "f", "asset_sha256": "s"},
    ]
    groups = build_support_groups(cards)
    assert len(groups) == 2  # 记录去重:两条不同库记录 = 两组
    assert all(g.independent_support_count is None
               for g in groups)  # 研究身份未知 ⇒ None
    groups2 = build_support_groups(
        cards, study_map={"recorded_reaction:dbA#1": "doi:10.x/paper",
                          "recorded_reaction:dbB#7": "doi:10.x/paper"})
    assert all(g.independent_support_count == 1 for g in groups2)
    assert all(g.origin_study_ref == "doi:10.x/paper" for g in groups2)


def test_f10_legacy_model_ref_preserved_and_provenance_persisted(
        tmp_path) -> None:
    """F10 复现:旧模型类比事件的 model_ref ⇒ 导入标 model_proposal,
    provenance 持久保存到新账本。"""
    from pathway_v43.storage.pathway_store import PathwayStore

    run_dir = tmp_path / "legacy_model"
    run_dir.mkdir(parents=True)
    store = PathwayStore(run_dir / "pathway.sqlite")
    root_pid = store.ensure_run("rm", ETHANOL,
                                _pstate(ETHANOL).cn_identity)
    (run_dir / "run_identity.json").write_text(json.dumps({
        "schema_version": "v43-identity-1",
        "inputs": {"root_smiles": ETHANOL,
                   "root_identity": _pstate(ETHANOL).cn_identity}}),
        encoding="utf-8")
    cn_acetal = _pstate(ACETALDEHYDE).cn_identity
    card = {"evidence_id": "EM", "kind": "analog_reaction",
            "source_id": "donor|via:analogy_edit",
            "condition_fit": "unknown", "_content_hash": "EM" * 64,
            "products": [{"position": 0, "product_smiles": ACETALDEHYDE,
                          "product_smiles_full": ACETALDEHYDE,
                          "product_identity": cn_acetal}]}
    store.submit_event(
        run_id="rm", parent_path_id=root_pid,
        substrate_identity=_pstate(ETHANOL).cn_identity, evidence=card,
        products=card["products"], expandable_path_ids=[],
        deferred_path_ids=[], model_ref="prediction:T1#a1")
    store.close()

    new_store = PollutantPathwayStore(tmp_path / "nm" / "ppv1.sqlite")
    import_legacy_run(run_dir, new_run_id="rmn", target_store=new_store)
    event = new_store.list_events("rmn")[0]
    hyp = new_store.get_hypothesis(event["hypothesis_id"])
    assert hyp["model_decision_ref"] == "prediction:T1#a1"  # 不丢
    # provenance 持久化且可解析
    prov = new_store.get_provenance(event["event_id"].replace(
        "ppev_", "ppprov_")) or None
    # record_id 由 legacy event_id 派生:直接查表
    rows = new_store.conn.execute(
        "SELECT record_id, payload FROM provenance_records").fetchall()
    assert len(rows) == 1
    payload = json.loads(rows[0]["payload"])
    assert payload["source_origin"] == "model_proposal"
    assert payload["evidence_basis"] == "model_proposed"
    new_store.close()
