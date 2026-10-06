"""R2 复审存储反例回归(R3 回修;先红后绿;全部合成夹具,无金标)。

覆盖 R2-08/09/10/11 与指定 P2(处理池哈希链/study_map 下界/legacy
provenance 引用解析)的审核反例,以**真实公共 API**(submit_event /
put_state / import_legacy_run / build_pool_audit)验收,不只测 helper:

- R2-08:representation_fidelity 移出 state 不可变语义载荷;同图不同
  来源 fidelity 共存;导入先保留全部 occurrence 再归并分子身份;
  root 循环再出现正常导入;严格语义冲突仍拒;
- R2-09:participant_state_refs 从 event.participants 实际派生;事务内
  校验事件↔假设内容关系、投影产物范围、展开互斥;首次违约零写入;
  重放核验**全部**必要记录(删任一 → Ppv1LedgerCorrupt);
- R2-10:写入前对象 schema 版本门(states/hypothesis/event/投影/计划);
  event 持久 payload 保存 schema_version;store 关闭重开自洽;
- R2-11:根身份须依据实际父关系 + 身份一致确认;子路径指针损坏退
  CN-only 并保留原因,绝不借根结构;
- P2:池审计哈希链核**相邻实际记录**(跳阶段须 from_previous=False+
  transition_reason);study_map 部分映射时独立支持数是已知下界
  (count_basis 分轴);导入的 hypothesis.provenance_refs 在新账本可解析。
"""

from __future__ import annotations

import json
import sqlite3
import sys
from dataclasses import replace
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pathway_v43.pollutant.chemstate import (  # noqa: E402
    STRUCTURE_ORIGIN_RAW_INPUT,
    STRUCTURE_ORIGIN_SOURCE_PRODUCT,
    archive_recovered_fidelity,
    build_chemical_state,
)
from pathway_v43.pollutant.events import (  # noqa: E402
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
    Participant,
    build_hypothesis,
)
from pathway_v43.pollutant.legacy_reader import (  # noqa: E402
    import_legacy_event,
    import_legacy_run,
    read_legacy_events,
)
from pathway_v43.pollutant.pool_audit import (  # noqa: E402
    INPUT_PREVIEW_OFF,
    PoolAuditError,
    build_pool_audit,
    record_pool_stage,
)
from pathway_v43.pollutant.profile import (  # noqa: E402
    PPV1_EVENT_SCHEMA_VERSION,
)
from pathway_v43.pollutant.provenance import build_support_groups  # noqa: E402
from pathway_v43.pollutant.store import (  # noqa: E402
    Ppv1EventConflict,
    Ppv1LedgerCorrupt,
    Ppv1SubmitContractError,
    Ppv1ObjectSchemaError,
    PollutantPathwayStore,
)

ETHANOL = "CCO"
ACETALDEHYDE = "CC=O"
ACETIC_ACID = "CC(=O)O"


def _pstate(smiles, origin=STRUCTURE_ORIGIN_SOURCE_PRODUCT, refs=None,
            fidelity=None):
    return build_chemical_state(smiles, origin, refs, fidelity=fidelity)


def _sub(ref):
    return Participant(state_ref=ref, side=PARTICIPANT_SIDE_REACTANT,
                       role=PARTICIPANT_ROLE_PRIMARY_SUBSTRATE,
                       coefficient=None, coefficient_status=COEFFICIENT_UNKNOWN)


def _prod(ref):
    return Participant(state_ref=ref, side=PARTICIPANT_SIDE_PRODUCT,
                       role=PARTICIPANT_ROLE_PRINCIPAL_PRODUCT,
                       coefficient=None, coefficient_status=COEFFICIENT_UNKNOWN)


def _simple_hyp(sub_state, prod_state, path="p1", origin_group="og"):
    return build_hypothesis(
        parent_path_id=path, substrate_state_ref=sub_state.state_id,
        participants=[_sub(sub_state.state_id), _prod(prod_state.state_id)],
        participant_list_status=PARTICIPANT_LIST_PARTIAL,
        step_scope="net_reaction", origin_group_key=origin_group)


def _valid_args(hyp, prod_state):
    return {
        "report_projection": build_report_projection(
            hyp, max_reportable=1,
            ranked_state_refs=[prod_state.state_id]).to_dict(),
        "expansion_plan": build_expansion_plan(
            hyp, expanded=[prod_state.state_id], deferred=[],
            not_tracked=[]).to_dict(),
        "hypothesis_dict": hyp.to_dict(),
    }


def _make_legacy_run(tmp_path: Path, name: str, steps: list[list[str]]):
    """合成旧 v43 run(真实 PathwayStore 公共 API;零金标)。"""
    from pathway_v43.storage.pathway_store import PathwayStore

    run_dir = tmp_path / name
    run_dir.mkdir(parents=True)
    store = PathwayStore(run_dir / "pathway.sqlite")
    root_cn = _pstate(ETHANOL).cn_identity
    root_pid = store.ensure_run(name, ETHANOL, root_cn)
    (run_dir / "run_identity.json").write_text(json.dumps({
        "schema_version": "v43-identity-1",
        "inputs": {"root_smiles": ETHANOL, "root_identity": root_cn}},
    ), encoding="utf-8")
    pid, cn = root_pid, root_cn
    for i, smis in enumerate(steps):
        products = [{"position": j, "product_smiles": s,
                     "product_smiles_full": s,
                     "product_identity": _pstate(s).cn_identity}
                    for j, s in enumerate(smis)]
        evidence = {"evidence_id": f"{name}-e{i}", "source_id": f"{name}-e{i}",
                    "kind": "recorded_reaction", "condition_fit": "unknown",
                    "products": products}
        result = store.submit_event(
            run_id=name, parent_path_id=pid, substrate_identity=cn,
            evidence=evidence, products=products,
            expandable_path_ids=[], deferred_path_ids=[])
        pid, cn = result["path_ids"][0], products[0]["product_identity"]
    store.close()
    return run_dir


# ================================================================ R2-08


def test_r2_08_same_graph_source_fidelity_coexist(tmp_path) -> None:
    """R2-08 复现:同图 CCO(raw_input/full)与 OCC(archive)→ 同一
    state_id、各自 appearance;fidelity 不是语义载荷,不冲突、不升级。"""
    store = PollutantPathwayStore(tmp_path / "fidelity.sqlite")
    s1 = _pstate(ETHANOL, STRUCTURE_ORIGIN_RAW_INPUT,
                 [{"source": "root"}])
    s2 = _pstate("OCC", STRUCTURE_ORIGIN_SOURCE_PRODUCT,
                 [{"source": "archive"}], archive_recovered_fidelity())
    assert s1.state_id == s2.state_id
    store.put_state(s1.to_dict())
    store.put_state(s2.to_dict())  # v2 在此抛 fidelity 语义冲突
    appearances = store.state_appearances(s1.state_id)
    assert len(appearances) == 2
    by_raw = {a["structure_smiles_raw"]: a for a in appearances}
    assert by_raw[ETHANOL]["representation_fidelity"]["stereo"] == \
        "as_written"
    assert by_raw["OCC"]["representation_fidelity"]["stereo"] == \
        "absent_in_archive"  # 不把 archive 的 absent 升级成 full
    got = store.get_state(s1.state_id)
    # get_state 兼容形状:语义事实 + appearances;首出现保真仅作镜像
    assert got["appearances"][0]["structure_smiles_raw"] == ETHANOL
    assert got["formal_charge"] == 0
    store.close()


def test_r2_08_fidelity_only_difference_is_not_semantic_conflict(
        tmp_path) -> None:
    """R2-08:同一结构、仅 representation_fidelity 不同(同来源)→
    出现记录分立,不构成身份冲突;篡改严格事实仍拒。"""
    store = PollutantPathwayStore(tmp_path / "fid2.sqlite")
    full = _pstate(ACETALDEHYDE, refs=[{"role": "r1"}]).to_dict()
    archived = _pstate(ACETALDEHYDE, refs=[{"role": "r2"}],
                       fidelity=archive_recovered_fidelity()).to_dict()
    store.put_state(full)
    store.put_state(archived)  # v2: fidelity 属语义 → 冲突(反例)
    assert len(store.state_appearances(
        _pstate(ACETALDEHYDE).state_id)) == 2
    forged = dict(full)
    forged["formal_charge"] = 99  # 严格分子事实不同 ⇒ 仍拒
    with pytest.raises(Ppv1EventConflict):
        store.put_state(forged)
    store.close()


def test_r2_08_legacy_cycle_import_root_reappears(tmp_path) -> None:
    """R2-08 复现:CCO→CC=O→CCO 循环路径导入成功;第二处 CCO 是
    source_product 出现,不是 raw_input;旧库字节不变。"""
    run_dir = _make_legacy_run(tmp_path, "legacy_cycle",
                               [[ACETALDEHYDE], [ETHANOL]])
    before = (run_dir / "pathway.sqlite").read_bytes()
    store = PollutantPathwayStore(tmp_path / "cycle_new.sqlite")
    result = import_legacy_run(run_dir, new_run_id="new-cycle",
                               target_store=store)  # v2 在此抛冲突
    assert result["n_created"] == 2
    root_state = _pstate(ETHANOL)
    appearances = store.state_appearances(root_state.state_id)
    origins = {a["structure_origin"] for a in appearances}
    assert origins == {STRUCTURE_ORIGIN_RAW_INPUT,
                       STRUCTURE_ORIGIN_SOURCE_PRODUCT}
    # 根出现仍是 raw_input;第二处是产物出现(可追溯到来源事件)
    prod_apps = [a for a in appearances
                 if a["structure_origin"] == STRUCTURE_ORIGIN_SOURCE_PRODUCT]
    assert prod_apps and all(
        "event_id" in (a.get("source_refs") or [{}])[0] for a in prod_apps)
    assert (run_dir / "pathway.sqlite").read_bytes() == before
    store.close()


def test_r2_08_legacy_same_structure_two_positions(tmp_path) -> None:
    """R2-08 复现:同事件产物 position 0="CC=O"、position 1="O=CC" →
    两个原串/来源出现都保留(先保留 occurrence 再归并身份)。"""
    run_dir = _make_legacy_run(tmp_path, "legacy_two_spellings",
                               [[ACETALDEHYDE, "O=CC"]])
    store = PollutantPathwayStore(tmp_path / "dup_new.sqlite")
    import_legacy_run(run_dir, new_run_id="new-dup", target_store=store)
    appearances = store.state_appearances(_pstate(ACETALDEHYDE).state_id)
    by_pos = {a["source_refs"][0].get("position"): a
              for a in appearances}
    # v2 只保留 position 1(O=CC),position 0 被覆盖(反例)
    assert set(by_pos) == {0, 1}
    assert by_pos[0]["structure_smiles_raw"] == ACETALDEHYDE
    assert by_pos[1]["structure_smiles_raw"] == "O=CC"
    store.close()


# ================================================================ R2-09


def test_r2_09_participant_refs_derived_from_participants(tmp_path) -> None:
    """R2-09 复现(event_refs_omit_real_product):participants 含产物但
    participant_state_refs 少报产物、事务只给底物 state ⇒ 拒绝 + 零写入。"""
    store = PollutantPathwayStore(tmp_path / "omit.sqlite")
    sub = _pstate(ETHANOL, STRUCTURE_ORIGIN_RAW_INPUT)
    prod = _pstate(ACETALDEHYDE)
    hyp = _simple_hyp(sub, prod)
    event = replace(build_pathway_event(hyp, run_id="omit",
                                        context_hash="ctx"),
                    participant_state_refs=[sub.state_id])
    args = _valid_args(hyp, prod)
    with pytest.raises((Ppv1SubmitContractError, Ppv1LedgerCorrupt)):
        store.submit_event(event, states=[sub.to_dict()], **args)
    counts = store.counts()
    assert counts["events"] == 0
    assert counts["states"] == 0  # 零写入(产物 state 不存在)
    assert store.get_state(prod.state_id) is None
    store.close()


def test_r2_09_hypothesis_relation_mismatch_rejected(tmp_path) -> None:
    """R2-09 复现(event_hypothesis_mismatch):同 ID hypothesis 内容与
    事件矛盾(异父路径/错误底物锚点/participants=[])⇒ 拒绝 + 零写入。"""
    store = PollutantPathwayStore(tmp_path / "mismatch.sqlite")
    sub = _pstate(ETHANOL, STRUCTURE_ORIGIN_RAW_INPUT)
    prod = _pstate(ACETALDEHYDE)
    hyp = _simple_hyp(sub, prod)
    event = build_pathway_event(hyp, run_id="mm", context_hash="ctx")
    args = _valid_args(hyp, prod)
    args["hypothesis_dict"] = json.loads(json.dumps(hyp.to_dict()))
    args["hypothesis_dict"]["parent_path_id"] = "different_parent"
    args["hypothesis_dict"]["substrate_state_ref"] = prod.state_id
    args["hypothesis_dict"]["participants"] = []
    with pytest.raises(Ppv1SubmitContractError):
        store.submit_event(event, states=[sub.to_dict(), prod.to_dict()],
                           **args)
    assert store.counts()["events"] == 0
    assert store.get_hypothesis(hyp.hypothesis_id) is None
    store.close()


def test_r2_09_existing_hypothesis_payload_mismatch_rejected(
        tmp_path) -> None:
    """R2-09 复现(existing_hypothesis_payload_ignored):库中已有同 ID
    假设,随事务提交不同内容 ⇒ 冲突拒绝,不静默忽略。"""
    store = PollutantPathwayStore(tmp_path / "preexist.sqlite")
    sub = _pstate(ETHANOL, STRUCTURE_ORIGIN_RAW_INPUT)
    prod = _pstate(ACETALDEHYDE)
    hyp = _simple_hyp(sub, prod)
    store.put_hypothesis(hyp.to_dict(), context_hash="different_context")
    event = build_pathway_event(hyp, run_id="pe", context_hash="ctx")
    args = _valid_args(hyp, prod)
    args["hypothesis_dict"] = json.loads(json.dumps(hyp.to_dict()))
    args["hypothesis_dict"]["participants"] = []
    with pytest.raises((Ppv1EventConflict, Ppv1SubmitContractError)):
        store.submit_event(event, states=[sub.to_dict(), prod.to_dict()],
                           **args)
    assert store.counts()["events"] == 0
    store.close()


def test_r2_09_projection_and_expansion_scope_validated(tmp_path) -> None:
    """R2-09 复现(commit_invalid_projection_and_expansion):投影指向
    非产物、展开同产物双状态 + 悬空引用 ⇒ 拒绝 + 零写入。"""
    store = PollutantPathwayStore(tmp_path / "badproj.sqlite")
    sub = _pstate(ETHANOL, STRUCTURE_ORIGIN_RAW_INPUT)
    prod = _pstate(ACETALDEHYDE)
    hyp = _simple_hyp(sub, prod)
    event = build_pathway_event(hyp, run_id="bp", context_hash="ctx")
    args = _valid_args(hyp, prod)
    args["report_projection"]["product_ranks"][0]["state_ref"] = \
        "cs_missing_nonproduct"
    args["expansion_plan"]["entries"].append(
        {"state_ref": prod.state_id, "status": "deferred",
         "reason": "conflicting_status"})
    args["expansion_plan"]["entries"].append(
        {"state_ref": "cs_missing_nonproduct", "status": "expanded",
         "reason": "dangling"})
    with pytest.raises(Ppv1SubmitContractError):
        store.submit_event(event, states=[sub.to_dict(), prod.to_dict()],
                           **args)
    assert store.counts()["events"] == 0
    assert store.report_projection(event.event_id) is None
    assert store.expansion_plan(event.event_id) is None
    store.close()


@pytest.mark.parametrize("table", [
    "states", "hypotheses", "state_appearances",
    "report_projections", "expansion_plans",
])
def test_r2_09_replay_missing_necessary_record_reports_corrupt(
        tmp_path, table) -> None:
    """R2-09 复现(replay_missing_*):删任一必要记录后重放 ⇒
    Ppv1LedgerCorrupt,不静默 created=False 成功。"""
    store = PollutantPathwayStore(tmp_path / f"replay_{table}.sqlite")
    sub = _pstate(ETHANOL, STRUCTURE_ORIGIN_RAW_INPUT)
    prod = _pstate(ACETALDEHYDE)
    hyp = _simple_hyp(sub, prod)
    event = build_pathway_event(hyp, run_id="rp", context_hash="ctx")
    args = _valid_args(hyp, prod)
    states = [sub.to_dict(), prod.to_dict()]
    assert store.submit_event(event, states=states, **args)["created"]
    store.conn.execute(f"DELETE FROM {table}")
    store.conn.commit()
    with pytest.raises(Ppv1LedgerCorrupt):
        store.submit_event(event, states=states, **args)  # v2: created=False
    store.close()


def test_r2_09_valid_submit_then_replay_created_false(tmp_path) -> None:
    """正例:合法提交 created=True;原参数重放核验全部记录后
    created=False(幂等)。"""
    store = PollutantPathwayStore(tmp_path / "happy.sqlite")
    sub = _pstate(ETHANOL, STRUCTURE_ORIGIN_RAW_INPUT)
    prod = _pstate(ACETALDEHYDE)
    hyp = _simple_hyp(sub, prod)
    event = build_pathway_event(hyp, run_id="hp", context_hash="ctx")
    args = _valid_args(hyp, prod)
    states = [sub.to_dict(), prod.to_dict()]
    first = store.submit_event(event, states=states, **args)
    again = store.submit_event(event, states=states, **args)
    assert first["created"] is True and again["created"] is False
    assert store.counts()["events"] == 1
    store.close()


# ================================================================ R2-10


def test_r2_10_future_object_schemas_rejected_zero_write(tmp_path) -> None:
    """R2-10 复现(future_object_schemas_written):future-chemstate-999 /
    future-hypothesis-999 / future-event-999 ⇒ 写入前拒绝,零写入。"""
    store = PollutantPathwayStore(tmp_path / "future.sqlite")
    sub = _pstate(ETHANOL, STRUCTURE_ORIGIN_RAW_INPUT)
    prod = _pstate(ACETALDEHYDE)
    hyp = _simple_hyp(sub, prod)
    event = build_pathway_event(hyp, run_id="fu", context_hash="ctx")
    args = _valid_args(hyp, prod)
    states = [sub.to_dict(), prod.to_dict()]
    states[0]["schema_version"] = "future-chemstate-999"
    args["hypothesis_dict"]["schema_version"] = "future-hypothesis-999"
    event = replace(event, schema_version="future-event-999")
    with pytest.raises(Ppv1ObjectSchemaError):
        store.submit_event(event, states=states, **args)  # v2: created=True
    assert all(v == 0 for v in store.counts().values())
    store.close()


def test_r2_10_future_projection_and_plan_versions_rejected(
        tmp_path) -> None:
    """R2-10:投影/计划版本未知 ⇒ 同样写前拒绝(对象 dict 全覆盖)。"""
    store = PollutantPathwayStore(tmp_path / "futureproj.sqlite")
    sub = _pstate(ETHANOL, STRUCTURE_ORIGIN_RAW_INPUT)
    prod = _pstate(ACETALDEHYDE)
    hyp = _simple_hyp(sub, prod)
    event = build_pathway_event(hyp, run_id="fp", context_hash="ctx")
    args = _valid_args(hyp, prod)
    states = [sub.to_dict(), prod.to_dict()]
    bad_projection = json.loads(json.dumps(args["report_projection"]))
    bad_projection["projection_version"] = "future-projection-999"
    with pytest.raises(Ppv1ObjectSchemaError):
        store.submit_event(event, states=states,
                           report_projection=bad_projection,
                           expansion_plan=args["expansion_plan"],
                           hypothesis_dict=args["hypothesis_dict"])
    bad_plan = json.loads(json.dumps(args["expansion_plan"]))
    bad_plan["policy_version"] = "future-expansion-999"
    with pytest.raises(Ppv1ObjectSchemaError):
        store.submit_event(event, states=states,
                           report_projection=args["report_projection"],
                           expansion_plan=bad_plan,
                           hypothesis_dict=args["hypothesis_dict"])
    assert store.counts()["events"] == 0
    store.close()


def test_r2_10_event_payload_persists_schema_version(tmp_path) -> None:
    """R2-10 复现:event 持久 payload 保存 schema_version(v2 丢失)。"""
    store = PollutantPathwayStore(tmp_path / "evver.sqlite")
    sub = _pstate(ETHANOL, STRUCTURE_ORIGIN_RAW_INPUT)
    prod = _pstate(ACETALDEHYDE)
    hyp = _simple_hyp(sub, prod)
    event = build_pathway_event(hyp, run_id="ev", context_hash="ctx")
    args = _valid_args(hyp, prod)
    store.submit_event(event, states=[sub.to_dict(), prod.to_dict()], **args)
    stored = store.get_event(event.event_id)
    payload = json.loads(stored["payload"])
    assert payload["schema_version"] == PPV1_EVENT_SCHEMA_VERSION
    store.close()


def test_r2_10_store_reopen_roundtrip(tmp_path) -> None:
    """R2-10:store 创建→关闭→重开自洽(版本门与写入版本一致)。"""
    path = tmp_path / "reopen.sqlite"
    store = PollutantPathwayStore(path)
    sub = _pstate(ETHANOL, STRUCTURE_ORIGIN_RAW_INPUT)
    store.put_state(sub.to_dict())
    store.close()
    reopened = PollutantPathwayStore(path)  # v2 基座在此自拒
    assert reopened.get_state(sub.state_id) is not None
    reopened.close()


def test_r2_10_missing_object_version_rejected(tmp_path) -> None:
    """R2-10:对象 dict 缺 schema_version ⇒ 显式拒绝(不静默当当前版本)。
    ppv1 对象字典无"无版本历史格式",缺键即非法形状(与 legacy 旧库
    的版本化兼容路径分开,后者走 legacy_reader 的显式版本名单)。"""
    store = PollutantPathwayStore(tmp_path / "nover.sqlite")
    sub = _pstate(ETHANOL, STRUCTURE_ORIGIN_RAW_INPUT)
    stripped = {k: v for k, v in sub.to_dict().items()
                if k != "schema_version"}
    with pytest.raises(Ppv1ObjectSchemaError):
        store.put_state(stripped)
    store.close()


# ================================================================ R2-11


def _broken_pointer_child_run(tmp_path: Path, name: str) -> Path:
    """子路径 parent_path_id 完好、event/product_position 指针被清空的
    合成旧库(真实 API 写入后物理破坏指针;模拟账本损坏)。"""
    run_dir = _make_legacy_run(tmp_path, name,
                               [[ACETALDEHYDE], [ACETIC_ACID]])
    conn = sqlite3.connect(run_dir / "pathway.sqlite")
    row = conn.execute(
        "SELECT parent_path_id FROM reaction_events WHERE "
        "substrate_identity = ?",
        (_pstate(ACETALDEHYDE).cn_identity,)).fetchone()
    sub_path = row[0]
    conn.execute(
        "UPDATE path_instances SET event_id = NULL, product_position = NULL"
        " WHERE path_id = ?", (sub_path,))
    conn.commit()
    conn.close()
    return run_dir


def test_r2_11_child_missing_archive_pointers_not_root(tmp_path) -> None:
    """R2-11 复现(child_missing_archive_pointers_as_root):parent 非空
    但 event/position 指针损坏 ⇒ CN-only + 原因说明,绝不借根结构。"""
    run_dir = _broken_pointer_child_run(tmp_path, "legacy_child_broken")
    before = (run_dir / "pathway.sqlite").read_bytes()
    events = read_legacy_events(run_dir)
    event2 = next(e for e in events
                  if e["substrate_identity"] ==
                  _pstate(ACETALDEHYDE).cn_identity)
    imported = import_legacy_event(run_dir, event2, new_run_id="new-brk")
    sub_state = next(s for s in imported["states"]
                     if s["state_id"] ==
                     imported["hypothesis"].substrate_state_ref)
    # v2 反例:被当 root,拿 CCO raw_input + 全 as_written 冒充
    assert sub_state["structure_origin"] == "legacy_cn_only"
    assert sub_state["representation_fidelity"]["formal_charge"] == "unknown"
    assert sub_state["structure_smiles_raw"] != ETHANOL  # 不借根结构
    assert any("substrate_structure_legacy_cn_only" in n
               for n in imported["uncertainty_notes"])
    assert any("child_missing_archive_pointers" in n
               for n in imported["uncertainty_notes"])  # 保留原因
    assert (run_dir / "pathway.sqlite").read_bytes() == before


def test_r2_11_root_identity_must_match_run_root(tmp_path) -> None:
    """R2-11:指针全空但 substrate_identity 与 run 根身份不一致 ⇒
    不确认 root,CN-only 降级(root 身份须实际父关系+身份一致确认)。"""
    run_dir = _make_legacy_run(tmp_path, "legacy_ident_mismatch",
                               [[ACETALDEHYDE]])
    # 篡改 run_identity 的根身份,使根路径身份无法确认一致
    ident = json.loads((run_dir / "run_identity.json").read_text())
    ident["inputs"]["root_identity"] = "C#N"
    (run_dir / "run_identity.json").write_text(json.dumps(ident))
    events = read_legacy_events(run_dir)
    imported = import_legacy_event(run_dir, events[0],
                                   new_run_id="new-ident")
    sub_state = next(s for s in imported["states"]
                     if s["state_id"] ==
                     imported["hypothesis"].substrate_state_ref)
    assert sub_state["structure_origin"] == "legacy_cn_only"
    assert any("root_identity_unconfirmed" in n
               for n in imported["uncertainty_notes"])


def test_r2_11_true_root_still_uses_root_smiles(tmp_path) -> None:
    """R2-11 正例:真实根事件(parent/指针全空 + 身份一致)仍恢复
    root_smiles(raw_input)。"""
    run_dir = _make_legacy_run(tmp_path, "legacy_root_ok",
                               [[ACETALDEHYDE]])
    events = read_legacy_events(run_dir)
    imported = import_legacy_event(run_dir, events[0], new_run_id="new-r")
    sub_state = next(s for s in imported["states"]
                     if s["state_id"] ==
                     imported["hypothesis"].substrate_state_ref)
    assert sub_state["structure_origin"] == STRUCTURE_ORIGIN_RAW_INPUT
    assert sub_state["structure_smiles_raw"] == ETHANOL


# ================================================================ P2


def test_p2_pool_skipped_stage_breaks_hash_rejected() -> None:
    """P2 复现(skipped_pool_stage_breaks_hash_without_reason):
    retrieved_raw→structure_screened 跳协议阶段、hash 不同、无 reason ⇒
    拒绝;相邻**实际记录**必须 hash 连续。"""
    a, b = [{"evidence_id": "A"}], [{"evidence_id": "B"}]
    stages = [record_pool_stage(stage="retrieved_raw", input_items=[],
                                output_items=a),
              record_pool_stage(stage="structure_screened",
                                input_items=b, output_items=b)]
    with pytest.raises(PoolAuditError, match="哈希链断裂"):
        build_pool_audit(run_id="r", path_id="p", stages=stages,
                         input_preview_policy=INPUT_PREVIEW_OFF)
    # 显式登记跳过/注入(from_previous=False + transition_reason)⇒ 合法
    fixed = [stages[0],
             record_pool_stage(stage="structure_screened",
                               input_items=b, output_items=b,
                               from_previous=False,
                               transition_reason="stage_skipped_screen_off")]
    record = build_pool_audit(run_id="r", path_id="p", stages=fixed,
                              input_preview_policy=INPUT_PREVIEW_OFF)
    assert record.stages[1].transition_reason == "stage_skipped_screen_off"


def test_p2_pool_actual_adjacent_records_hash_checked() -> None:
    """P2:非协议相邻的两条**实际**记录(retrieved_raw→deduped)同样
    必须连续(v2 只核协议索引相邻,反例漏洞)。"""
    out = [{"evidence_id": "A"}]
    other = [{"evidence_id": "Z"}]
    stages = [record_pool_stage(stage="retrieved_raw", input_items=[],
                                output_items=out),
              record_pool_stage(stage="deduped", input_items=other,
                                output_items=other)]
    with pytest.raises(PoolAuditError, match="哈希链断裂"):
        build_pool_audit(run_id="r", path_id="p", stages=stages,
                         input_preview_policy=INPUT_PREVIEW_OFF)


def test_p2_study_map_count_basis_axes() -> None:
    """P2 复现(partial_study_map):一条已知 + 一条未知 ⇒ count 是
    **已知下界**,count_basis=known_lower_bound + unresolved 计数;
    全知 ⇒ exact;无 study_map ⇒ None + unknown_study_identity。"""
    cards = [
        {"evidence_id": "K1", "kind": "recorded_reaction",
         "source_id": "db#1"},
        {"evidence_id": "U1", "kind": "recorded_reaction",
         "source_id": "db#2"},
    ]
    partial = build_support_groups(
        cards, study_map={"recorded_reaction:db#1": "doi:10.x/a"})
    assert all(g.count_basis == "known_lower_bound" for g in partial)
    assert all(g.independent_support_count == 1 for g in partial)
    assert all(g.n_unresolved_study_identity == 1 for g in partial)
    full = build_support_groups(
        cards, study_map={"recorded_reaction:db#1": "doi:10.x/a",
                          "recorded_reaction:db#2": "doi:10.x/b"})
    assert all(g.count_basis == "exact" for g in full)
    assert all(g.independent_support_count == 2 for g in full)
    assert all(g.n_unresolved_study_identity == 0 for g in full)
    none_map = build_support_groups(cards)
    assert all(g.count_basis == "unknown_study_identity"
               for g in none_map)
    assert all(g.independent_support_count is None for g in none_map)


def test_p2_legacy_provenance_refs_resolvable(tmp_path) -> None:
    """P2 复现(legacy_provenance_ref_resolution):导入的 hypothesis
    provenance_refs 在新账本可解析(get_provenance 非 None)。"""
    run_dir = _make_legacy_run(tmp_path, "legacy_prov",
                               [[ACETALDEHYDE, "O=CC"]])
    store = PollutantPathwayStore(tmp_path / "prov_new.sqlite")
    import_legacy_run(run_dir, new_run_id="new-prov", target_store=store)
    for ev in store.list_events("new-prov"):
        hyp = store.get_hypothesis(ev["hypothesis_id"])
        assert hyp["provenance_refs"]
        for ref in hyp["provenance_refs"]:
            assert store.get_provenance(ref) is not None, (
                f"provenance ref {ref} 不可解析(v2 反例:get_provenance"
                "=None)")
    store.close()
