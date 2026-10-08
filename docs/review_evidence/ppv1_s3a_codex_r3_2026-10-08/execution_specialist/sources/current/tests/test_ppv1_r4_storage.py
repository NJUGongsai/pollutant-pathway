"""R3 复审存储反例回归(R4 回修;先红后绿;全部合成夹具,无金标)。

覆盖 R3-09/10/11 + §4(空展开计划/同 hash 跳阶段)的审核反例,以**真实
公共 API**(put_state / put_hypothesis / submit_event / import_legacy_event
/ import_legacy_run / build_pool_audit)验收:

- R3-09 公共 writer 重推导:put/submit 对有结构 state 重推身份/电荷;
  raw_input 表示层身份核对;CN-only 保持未知;参与物工厂契约(含 entry_id
  指纹)与 event 派生身份在提交边界独立复核;hypothesis 载荷排序归一
  (同语义不同顺序 ⇒ 同 payload,put/submit 幂等);
- R3-10 重放校验内容:同参数重放从已存行复算(state 身份/电荷、
  hypothesis 行键/版本、event 语义 hash/列一致性/event_id、appearance
  行 hash 与本事件期望出现集合),不依赖调用者重复提供 dict;损坏 ⇒
  Ppv1LedgerCorrupt 结构化拒绝并保全,不静默补写;
- R3-11 旧导入引用核对:archive 来源指针内容与子底物声明身份矛盾 ⇒
  CN-only + 原因(不借错误结构);root_smiles 重算旧身份与声明根身份
  矛盾 ⇒ CN-only + 原因;所有公开导入入口守 store/run-identity 版本门;
- 导入管线不先 put 绕过:重放路径先校验已存记录完整性,缺/损 ⇒ 结构化
  错误,不补账;
- §4:事件有产物但 expansion entries=[](无 incomplete 声明)⇒ 契约拒绝;
  显式 plan_status=incomplete(带原因)合法;池审计同 hash 跳阶段同样
  须登记 transition_reason。

依赖契约说明:本轮 store 侧对 hypothesis_id/载荷排序采用**自建等价逻辑**
(事件 ID 重推导内嵌 hypothesis_id+参与物语义 + 参与物 entry_id 指纹 +
载荷/行键绑定 + canonical 载荷比较);条件线交付
canonical_hypothesis_payload/recompute_hypothesis_id 后由主会话接线,
本文件不依赖这两个函数存在。
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
    build_chemical_state_from_cn_only,
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
    LegacyStoreError,
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
from pathway_v43.pollutant.store import (  # noqa: E402
    Ppv1EventConflict,
    Ppv1LedgerCorrupt,
    Ppv1StateContractError,
    Ppv1SubmitContractError,
    PollutantPathwayStore,
)

ETHANOL = "CCO"
ACETALDEHYDE = "CC=O"
ACETIC_ACID = "CC(=O)O"
ACETONITRILE = "CCN"


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


def _simple_hyp(sub_state, prod_state, path="p1", origin_group="og",
                requirements=None):
    return build_hypothesis(
        parent_path_id=path, substrate_state_ref=sub_state.state_id,
        participants=[_sub(sub_state.state_id), _prod(prod_state.state_id)],
        participant_list_status=PARTICIPANT_LIST_PARTIAL,
        step_scope="net_reaction", origin_group_key=origin_group,
        requirements=requirements)


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


def _fixture(tmp_path, name):
    """合成合法提交夹具(乙醇→乙醛;与审核探针同构)。"""
    store = PollutantPathwayStore(tmp_path / (name + ".sqlite"))
    sub = _pstate(ETHANOL, STRUCTURE_ORIGIN_RAW_INPUT,
                  [{"record": "sub-A"}])
    prod = _pstate(ACETALDEHYDE, refs=[{"record": "prod-A"}])
    hyp = _simple_hyp(sub, prod, origin_group=name)
    event = build_pathway_event(hyp, run_id=name, context_hash="ctx")
    args = _valid_args(hyp, prod)
    states = [sub.to_dict(), prod.to_dict()]
    return store, sub, prod, hyp, event, args, states


def _make_legacy_run(tmp_path: Path, name: str, steps: list[list[str]]) -> Path:
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


# ================================================================ R3-09
# 公共 writer 重推导(反例:CCN 内容配 CCO state_id / formal_charge=99 /
# raw_input 配错 raw / 非法 smiles / submit 换产物内容 / 零系数 / 改参与物
# 保留原派生 ID —— 全部结构化拒绝、零写入)


def test_r4_09_put_state_forged_state_id_rejected(tmp_path) -> None:
    """R3-09 复现(put_forged_state_id):CCN 内容配 CCO 的 state_id ⇒
    重推严格身份不一致 ⇒ 结构化拒绝、零写入。"""
    store = PollutantPathwayStore(tmp_path / "f1.sqlite")
    ethanol = _pstate(ETHANOL)
    forged = _pstate(ACETONITRILE).to_dict()
    forged["state_id"] = ethanol.state_id
    with pytest.raises(Ppv1StateContractError) as exc_info:
        store.put_state(forged)
    assert exc_info.value.detail["kind"] == "state_fact_rederivation_mismatch"
    counts = store.counts()
    assert counts["states"] == 0 and counts["state_appearances"] == 0
    store.close()


def test_r4_09_put_state_forged_formal_charge_rejected(tmp_path) -> None:
    """R3-09 复现(put_forged_formal_charge):CCO 的 formal_charge=99 ⇒
    重算电荷不一致 ⇒ 结构化拒绝、零写入。"""
    store = PollutantPathwayStore(tmp_path / "f2.sqlite")
    forged = _pstate(ETHANOL).to_dict()
    forged["formal_charge"] = 99
    with pytest.raises(Ppv1StateContractError):
        store.put_state(forged)
    assert store.counts()["states"] == 0
    store.close()


def test_r4_09_put_state_raw_identity_mismatch_rejected(
        tmp_path) -> None:
    """R3-09 复现(put_forged_raw_structure,raw_input 变体):CCO 语义配
    CCN raw 且 origin=raw_input ⇒ 表示层身份核对不一致 ⇒ 拒绝。"""
    store = PollutantPathwayStore(tmp_path / "f3.sqlite")
    forged = _pstate(ETHANOL, STRUCTURE_ORIGIN_RAW_INPUT).to_dict()
    forged["structure_smiles_raw"] = ACETONITRILE
    with pytest.raises(Ppv1StateContractError) as exc_info:
        store.put_state(forged)
    assert exc_info.value.detail["kind"] == "raw_identity_mismatch"
    assert store.counts()["states"] == 0
    store.close()


def test_r4_09_put_state_unparseable_isomeric_rejected(tmp_path) -> None:
    """R3-09 复现(put_forged_isomeric_structure):非法 smiles_isomeric ⇒
    结构不可解析 ⇒ 结构化拒绝、零写入。"""
    store = PollutantPathwayStore(tmp_path / "f4.sqlite")
    forged = _pstate(ETHANOL).to_dict()
    forged["smiles_isomeric"] = "not-a-smiles"
    with pytest.raises(Ppv1StateContractError):
        store.put_state(forged)
    assert store.counts()["states"] == 0
    store.close()


def test_r4_09_put_state_cn_only_keeps_unknown(tmp_path) -> None:
    """R3-09 正例:CN-only(smiles 空、origin=legacy_cn_only)保持未知,
    不重推导、合法落账。"""
    store = PollutantPathwayStore(tmp_path / "f5.sqlite")
    cn_only = build_chemical_state_from_cn_only(
        _pstate(ETHANOL).cn_identity, source_refs=[{"role": "legacy"}])
    store.put_state(cn_only.to_dict())
    saved = store.get_state(cn_only.state_id)
    assert saved["formal_charge"] is None
    assert saved["structure_origin"] == "legacy_cn_only"
    store.close()


def test_r4_09_put_state_source_product_alternative_spelling_kept(
        tmp_path) -> None:
    """R3-09 边界控制:source_product 的 raw 允许同图不同拼写(R2-08 控制,
    如 OCC/CC=O);raw 不强制核身份(仅 raw_input 强制),出现原样保留。"""
    store = PollutantPathwayStore(tmp_path / "f6.sqlite")
    s = _pstate("OCC", STRUCTURE_ORIGIN_SOURCE_PRODUCT,
                [{"record": "archive"}], archive_recovered_fidelity())
    store.put_state(s.to_dict())
    appearances = store.state_appearances(s.state_id)
    assert len(appearances) == 1
    assert appearances[0]["structure_smiles_raw"] == "OCC"
    assert appearances[0]["structure_origin"] == STRUCTURE_ORIGIN_SOURCE_PRODUCT
    store.close()


def test_r4_09_submit_forged_state_zero_write(tmp_path) -> None:
    """R3-09 复现(submit_forged_state):合法 CCO→CC=O 事件仅替换提交产物
    state 内容为 CCN、保留乙醛 state_id ⇒ 事务内重推导 ⇒ 拒绝回滚。"""
    store, sub, prod, hyp, event, args, states = _fixture(tmp_path, "sf")
    wrong = _pstate(ACETONITRILE).to_dict()
    wrong["state_id"] = prod.state_id
    with pytest.raises(Ppv1StateContractError):
        store.submit_event(event, states=[states[0], wrong], **args)
    counts = store.counts()
    assert counts["events"] == 0 and counts["states"] == 0 \
        and counts["state_appearances"] == 0
    assert store.get_state(prod.state_id) is None
    store.close()


def test_r4_09_submit_zero_coefficient_rejected(tmp_path) -> None:
    """R3-09 复现(submit_zero_coefficient):参与物系数 '0'(known)同步改
    event/hypothesis、保留原派生 ID ⇒ 工厂契约在提交边界独立复核 ⇒ 拒。"""
    store, sub, prod, hyp, event, args, states = _fixture(tmp_path, "zc")
    event.participants[1]["coefficient"] = "0"
    event.participants[1]["coefficient_status"] = "known"
    args["hypothesis_dict"]["participants"] = json.loads(json.dumps(
        event.participants))
    with pytest.raises(Ppv1SubmitContractError) as exc_info:
        store.submit_event(event, states=states, **args)
    assert exc_info.value.detail["kind"] in (
        "participant_contract_violated", "event_id_rederivation_mismatch",
        "participant_entry_id_mismatch")
    counts = store.counts()
    assert counts["events"] == 0 and counts["states"] == 0
    store.close()


def test_r4_09_submit_participants_legal_tamper_kept_id_rejected(
        tmp_path) -> None:
    """R3-09:改参与物为**合法值**(系数 '2'、状态合法)但保留原派生
    event_id/hypothesis_id ⇒ 派生身份/指纹重推导 ⇒ 拒(零写入)。"""
    store, sub, prod, hyp, event, args, states = _fixture(tmp_path, "lt")
    event.participants[1]["coefficient"] = "2"
    event.participants[1]["coefficient_status"] = "known"
    args["hypothesis_dict"]["participants"] = json.loads(json.dumps(
        event.participants))
    with pytest.raises(Ppv1SubmitContractError):
        store.submit_event(event, states=states, **args)
    assert store.counts()["events"] == 0
    store.close()


def test_r4_09_put_hypothesis_reordered_requirements_idempotent(
        tmp_path) -> None:
    """R3-08/R3-09 存储侧:相同 oxygen/pH 要求仅调换顺序 ⇒ 同
    hypothesis_id ⇒ 第二次 put 不报冲突(载荷排序归一后再比较)。"""
    store = PollutantPathwayStore(tmp_path / "hr.sqlite")
    sub = _pstate(ETHANOL, STRUCTURE_ORIGIN_RAW_INPUT)
    prod = _pstate(ACETALDEHYDE)
    reqs = [{"key": "oxygen_regime", "level": "essential", "value": "aerobic"},
            {"key": "pH", "level": "preference", "value": 7}]
    hyp_a = _simple_hyp(sub, prod, requirements=list(reqs))
    hyp_b = _simple_hyp(sub, prod, requirements=list(reversed(reqs)))
    assert hyp_a.hypothesis_id == hyp_b.hypothesis_id  # id 侧已排序归一
    store.put_hypothesis(hyp_a.to_dict())
    store.put_hypothesis(hyp_b.to_dict())  # R3 反例:此处报冲突
    assert store.counts()["hypotheses"] == 1
    store.close()


def test_r4_09_submit_replay_reordered_requirements_idempotent(
        tmp_path) -> None:
    """R3-09/R3-10 存储侧:重放提供排序不同的同语义 hypothesis 载荷 ⇒
    canonical 比较 ⇒ 幂等成功(created=False),不报冲突。"""
    store, sub, prod, hyp, event, args, states = _fixture(tmp_path, "sr")
    reqs = [{"key": "oxygen_regime", "level": "essential", "value": "aerobic"},
            {"key": "pH", "level": "preference", "value": 7}]
    hyp_a = _simple_hyp(sub, prod, origin_group="sr",
                        requirements=list(reqs))
    hyp_b = _simple_hyp(sub, prod, origin_group="sr",
                        requirements=list(reversed(reqs)))
    event = build_pathway_event(hyp_a, run_id="sr", context_hash="ctx")
    args = _valid_args(hyp_a, prod)
    assert store.submit_event(event, states=states, **args)["created"]
    args["hypothesis_dict"] = hyp_b.to_dict()  # 同 id、requirements 反序
    again = store.submit_event(event, states=states, **args)
    assert again["created"] is False  # R3 反例:Ppv1EventConflict
    store.close()


# ================================================================ R3-10
# 重放校验内容(反例:替换 run/context 保留 event_id、删本事件 appearance、
# appearance/even/hypothesis/state 各类内容损坏、导入先 put 补账)


def test_r4_10_replay_run_context_swap_rejected(tmp_path) -> None:
    """R3-10 复现(replay_input_identity_mismatch):replace 输入 event 的
    run/context 但保留 event_id ⇒ 按请求重推导不一致 ⇒ 拒绝(非幂等成功)。"""
    store, sub, prod, hyp, event, args, states = _fixture(tmp_path, "rc")
    store.submit_event(event, states=states, **args)
    changed = replace(event, run_id="different-run",
                      context_hash="different-context")
    with pytest.raises(Ppv1SubmitContractError) as exc_info:
        store.submit_event(changed, states=states, **args)
    assert exc_info.value.detail["kind"] == "event_id_rederivation_mismatch"
    stored = store.get_event(event.event_id)
    assert stored["run_id"] == "rc" and stored["context_hash"] == "ctx"
    assert store.counts()["events"] == 1  # 保全,不静默改写
    store.close()


def test_r4_10_replay_missing_event_appearance_corrupt(tmp_path) -> None:
    """R3-10 复现(replay_one_appearance_missing):删本事件 prod-A 出现、
    只留无关 prod-B ⇒ 期望出现集合不完整 ⇒ Ppv1LedgerCorrupt。"""
    store, sub, prod, hyp, event, args, states = _fixture(tmp_path, "ma")
    store.submit_event(event, states=states, **args)
    alternate = _pstate("O=CC", refs=[{"record": "prod-B-unrelated"}])
    store.put_state(alternate.to_dict())
    first_hash = store.conn.execute(
        "SELECT appearance_hash FROM state_appearances WHERE state_id = ?"
        " ORDER BY rowid LIMIT 1", (prod.state_id,)).fetchone()[0]
    store.conn.execute(
        "DELETE FROM state_appearances WHERE state_id = ? AND"
        " appearance_hash = ?", (prod.state_id, first_hash))
    store.conn.commit()
    before = store.counts()
    with pytest.raises(Ppv1LedgerCorrupt) as exc_info:
        store.submit_event(event, states=states, **args)
    assert "appearance" in json.dumps(exc_info.value.detail)
    assert store.counts() == before  # 保全,不静默补写
    store.close()


def test_r4_10_replay_appearance_payload_tampered_corrupt(tmp_path) -> None:
    """R3-10 复现(replay_appearance_payload_tampered):appearance raw 改
    CCN 而 hash 未变 ⇒ 重算内容 hash ⇒ 损坏。"""
    store, sub, prod, hyp, event, args, states = _fixture(tmp_path, "at")
    store.submit_event(event, states=states, **args)
    row = store.conn.execute(
        "SELECT appearance_hash, payload FROM state_appearances WHERE"
        " state_id = ?", (prod.state_id,)).fetchone()
    payload = json.loads(row["payload"])
    payload["structure_smiles_raw"] = ACETONITRILE
    store.conn.execute(
        "UPDATE state_appearances SET payload = ? WHERE state_id = ? AND"
        " appearance_hash = ?",
        (json.dumps(payload), prod.state_id, row["appearance_hash"]))
    store.conn.commit()
    with pytest.raises(Ppv1LedgerCorrupt):
        store.submit_event(event, states=states, **args)
    store.close()


def test_r4_10_replay_event_participants_cleared_corrupt(tmp_path) -> None:
    """R3-10 复现(replay_event_payload_tampered):已存 event payload
    participants 被清空 ⇒ 重算语义 hash 不一致 ⇒ 损坏。"""
    store, sub, prod, hyp, event, args, states = _fixture(tmp_path, "ep")
    store.submit_event(event, states=states, **args)
    payload = json.loads(store.get_event(event.event_id)["payload"])
    payload["participants"] = []
    store.conn.execute("UPDATE events SET payload = ? WHERE event_id = ?",
                       (json.dumps(payload), event.event_id))
    store.conn.commit()
    with pytest.raises(Ppv1LedgerCorrupt):
        store.submit_event(event, states=states, **args)
    store.close()


def test_r4_10_replay_event_future_schema_corrupt(tmp_path) -> None:
    """R3-10 复现(replay_event_schema_tampered):已存 event payload 未来
    schema ⇒ 损坏。"""
    store, sub, prod, hyp, event, args, states = _fixture(tmp_path, "es")
    store.submit_event(event, states=states, **args)
    payload = json.loads(store.get_event(event.event_id)["payload"])
    payload["schema_version"] = "future-event-999"
    store.conn.execute("UPDATE events SET payload = ? WHERE event_id = ?",
                       (json.dumps(payload), event.event_id))
    store.conn.commit()
    with pytest.raises(Ppv1LedgerCorrupt):
        store.submit_event(event, states=states, **args)
    store.close()


def test_r4_10_replay_event_columns_tampered_corrupt(tmp_path) -> None:
    """R3-10 复现(replay_event_columns_tampered):event 身份列被改
    (run/parent/context)⇒ event_id 与列重推导不一致 ⇒ 损坏。"""
    store, sub, prod, hyp, event, args, states = _fixture(tmp_path, "ec")
    store.submit_event(event, states=states, **args)
    store.conn.execute(
        "UPDATE events SET run_id = 'wrong-run', parent_path_id ="
        " 'wrong-parent', context_hash = 'wrong-context'"
        " WHERE event_id = ?", (event.event_id,))
    store.conn.commit()
    with pytest.raises(Ppv1LedgerCorrupt):
        store.submit_event(event, states=states, **args)
    store.close()


def test_r4_10_replay_hypothesis_id_field_tampered_corrupt(
        tmp_path) -> None:
    """R3-10 复现(replay_hypothesis_id_tampered):已存 hypothesis payload
    内 ID 改错(不重复提供 dict)⇒ 载荷 ID 与行键不一致 ⇒ 损坏。"""
    store, sub, prod, hyp, event, args, states = _fixture(tmp_path, "hi")
    store.submit_event(event, states=states, **args)
    payload = store.get_hypothesis(hyp.hypothesis_id)
    payload["hypothesis_id"] = "hyp_unrelated"
    store.conn.execute("UPDATE hypotheses SET payload = ? WHERE"
                       " hypothesis_id = ?",
                       (json.dumps(payload), hyp.hypothesis_id))
    store.conn.commit()
    args["hypothesis_dict"] = None
    with pytest.raises(Ppv1LedgerCorrupt):
        store.submit_event(event, states=states, **args)
    store.close()


def test_r4_10_replay_hypothesis_future_schema_corrupt(tmp_path) -> None:
    """R3-10 复现(replay_hypothesis_schema_tampered):已存 hypothesis
    payload 未来 schema(不重复提供 dict)⇒ 损坏。"""
    store, sub, prod, hyp, event, args, states = _fixture(tmp_path, "hs")
    store.submit_event(event, states=states, **args)
    payload = store.get_hypothesis(hyp.hypothesis_id)
    payload["schema_version"] = "future-hypothesis-999"
    store.conn.execute("UPDATE hypotheses SET payload = ? WHERE"
                       " hypothesis_id = ?",
                       (json.dumps(payload), hyp.hypothesis_id))
    store.conn.commit()
    args["hypothesis_dict"] = None
    with pytest.raises(Ppv1LedgerCorrupt):
        store.submit_event(event, states=states, **args)
    store.close()


def test_r4_10_replay_state_charge_tampered_corrupt(tmp_path) -> None:
    """R3-10 复现(replay_state_semantic_tampered_no_provided_states):
    已存 state 行 charge 改错(states=[] 不重复提供)⇒ 重算 ⇒ 损坏。"""
    store, sub, prod, hyp, event, args, states = _fixture(tmp_path, "sc")
    store.submit_event(event, states=states, **args)
    payload = json.loads(store.conn.execute(
        "SELECT payload FROM states WHERE state_id = ?",
        (prod.state_id,)).fetchone()[0])
    payload["formal_charge"] = 99
    store.conn.execute("UPDATE states SET payload = ? WHERE state_id = ?",
                       (json.dumps(payload), prod.state_id))
    store.conn.commit()
    with pytest.raises(Ppv1LedgerCorrupt):
        store.submit_event(event, states=[], **args)
    store.close()


def test_r4_10_replay_state_future_schema_corrupt(tmp_path) -> None:
    """R3-10 复现(replay_state_schema_tampered_no_provided_states):
    已存 state 行未来 schema(states=[])⇒ 损坏。"""
    store, sub, prod, hyp, event, args, states = _fixture(tmp_path, "ss")
    store.submit_event(event, states=states, **args)
    payload = json.loads(store.conn.execute(
        "SELECT payload FROM states WHERE state_id = ?",
        (prod.state_id,)).fetchone()[0])
    payload["schema_version"] = "future-chemstate-999"
    store.conn.execute("UPDATE states SET payload = ? WHERE state_id = ?",
                       (json.dumps(payload), prod.state_id))
    store.conn.commit()
    with pytest.raises(Ppv1LedgerCorrupt):
        store.submit_event(event, states=[], **args)
    store.close()


def test_r4_10_replay_valid_idempotent_created_false(tmp_path) -> None:
    """R3-10 正例:合法提交后原参数重放,全部内容校验通过 ⇒ created=False。"""
    store, sub, prod, hyp, event, args, states = _fixture(tmp_path, "ok")
    first = store.submit_event(event, states=states, **args)
    again = store.submit_event(event, states=states, **args)
    assert first["created"] is True and again["created"] is False
    assert store.counts()["events"] == 1
    store.close()


def test_r4_10_import_replay_does_not_repair_missing_records(
        tmp_path) -> None:
    """R3-10 复现(legacy_import_replay_repairs_missing):导入重放路径
    不得先 put_state 补依赖再报 n_replayed —— 缺/损 ⇒ 结构化错误、不补账。"""
    run_dir = _make_legacy_run(tmp_path, "legacy_replay_repair", [
        [ACETALDEHYDE]])
    target = PollutantPathwayStore(
        tmp_path / "legacy_replay_repair_new.sqlite")
    first = import_legacy_run(run_dir, new_run_id="legacy-replay",
                              target_store=target)
    assert first["n_created"] == 1
    target.conn.execute("DELETE FROM states")
    target.conn.execute("DELETE FROM state_appearances")
    target.conn.execute("DELETE FROM hypotheses")
    target.conn.execute("DELETE FROM provenance_records")
    target.conn.commit()
    before = target.counts()
    with pytest.raises(Ppv1LedgerCorrupt):
        import_legacy_run(run_dir, new_run_id="legacy-replay",
                          target_store=target)
    assert target.counts() == before  # 不补账(states 仍为 0 等)
    target.close()


# ================================================================ R3-11
# 旧导入引用核对(反例:错但存在的 archive 指针、root_smiles 与声明根身份
# 矛盾、单事件入口绕过版本门)


def test_r4_11_import_event_rejects_future_store_schema(tmp_path) -> None:
    """R3-11 复现(unknown_schema_direct_import):旧库 meta
    future-legacy-store-999 时 import_legacy_event 也拒绝(公开入口守版本门)。"""
    run_dir = _make_legacy_run(tmp_path, "legacy_future_store", [
        [ACETALDEHYDE]])
    conn = sqlite3.connect(run_dir / "pathway.sqlite")
    conn.execute("UPDATE meta SET value = 'future-legacy-store-999'"
                 " WHERE key = 'schema_version'")
    conn.commit()
    conn.close()
    before = (run_dir / "pathway.sqlite").read_bytes()
    events = read_legacy_events(
        _make_legacy_run(tmp_path, "legacy_fs_prefetch", [[ACETALDEHYDE]]))
    with pytest.raises(LegacyStoreError):
        import_legacy_event(run_dir, events[0], new_run_id="new-fs")
    with pytest.raises(LegacyStoreError):
        read_legacy_events(run_dir)  # run 级入口同口径(基线行为保留)
    assert (run_dir / "pathway.sqlite").read_bytes() == before
    target = PollutantPathwayStore(tmp_path / "fs_target.sqlite")
    with pytest.raises(LegacyStoreError):
        import_legacy_run(run_dir, new_run_id="new-fs-run",
                          target_store=target)
    target.close()


def test_r4_11_import_event_rejects_future_run_identity_schema(
        tmp_path) -> None:
    """R3-11 复现(unknown_identity_schema):run_identity 显式未来版本 ⇒
    单事件入口同样拒绝(与 run 级口径一致)。"""
    run_dir = _make_legacy_run(tmp_path, "legacy_future_ident", [
        [ACETALDEHYDE]])
    ident = json.loads((run_dir / "run_identity.json").read_text())
    ident["schema_version"] = "future-identity-999"
    (run_dir / "run_identity.json").write_text(json.dumps(ident))
    events = read_legacy_events(run_dir)
    with pytest.raises(LegacyStoreError):
        import_legacy_event(run_dir, events[0], new_run_id="new-fi")
    target = PollutantPathwayStore(tmp_path / "fi_target.sqlite")
    with pytest.raises(LegacyStoreError):
        import_legacy_run(run_dir, new_run_id="new-fi-run",
                          target_store=target)
    target.close()


def test_r4_11_wrong_archive_pointer_degrades_cn_only(tmp_path) -> None:
    """R3-11 复现(wrong_archive_pointer):子底物声明 CN=CC=O、来源指针
    指向存在但错误的乙酸产物行 ⇒ 指针行身份与声明矛盾 ⇒ CN-only + 原因,
    不再把错误引用当完整结构。"""
    run_dir = _make_legacy_run(tmp_path, "legacy_wrong_ptr", [
        [ACETALDEHYDE], [ACETIC_ACID]])
    events = read_legacy_events(run_dir)
    second = next(e for e in events if e["substrate_identity"] ==
                  _pstate(ACETALDEHYDE).cn_identity)
    conn = sqlite3.connect(run_dir / "pathway.sqlite")
    conn.execute("UPDATE path_instances SET event_id = ? WHERE path_id = ?",
                 (second["event_id"], second["parent_path_id"]))
    conn.commit()
    conn.close()
    before = (run_dir / "pathway.sqlite").read_bytes()
    imported = import_legacy_event(run_dir, second, new_run_id="new-wp")
    sub_state = next(s for s in imported["states"]
                     if s["state_id"] ==
                     imported["hypothesis"].substrate_state_ref)
    assert sub_state["structure_origin"] == "legacy_cn_only"
    assert sub_state["representation_fidelity"]["formal_charge"] == "unknown"
    # 子底物状态的原串 = 声明 CN 本身,不是乙酸结构(不借错误结构冒充)
    assert sub_state["structure_smiles_raw"] == second["substrate_identity"]
    assert any("substrate_archive_identity_mismatch" in n
               for n in imported["uncertainty_notes"])
    assert (run_dir / "pathway.sqlite").read_bytes() == before


def test_r4_11_root_smiles_cn_mismatch_degrades_cn_only(tmp_path) -> None:
    """R3-11 复现(root_structure_cn_mismatch):库声明根 CN 为 CCO、
    root_smiles 为 CCN ⇒ 重算旧身份矛盾 ⇒ CN-only + 原因,不再把
    root_smiles 当 raw_input 无注记。"""
    run_dir = _make_legacy_run(tmp_path, "legacy_root_mismatch", [
        [ACETALDEHYDE]])
    ident = json.loads((run_dir / "run_identity.json").read_text())
    ident["inputs"]["root_smiles"] = ACETONITRILE
    (run_dir / "run_identity.json").write_text(json.dumps(ident))
    events = read_legacy_events(run_dir)
    imported = import_legacy_event(run_dir, events[0], new_run_id="new-rm")
    sub_state = next(s for s in imported["states"]
                     if s["state_id"] ==
                     imported["hypothesis"].substrate_state_ref)
    assert sub_state["structure_origin"] == "legacy_cn_only"
    assert sub_state["representation_fidelity"]["formal_charge"] == "unknown"
    assert any("root_smiles_identity_mismatch" in n
               for n in imported["uncertainty_notes"])
    assert sub_state["structure_smiles_raw"] != ACETONITRILE  # 不用 CCN 冒充


def test_r4_11_two_step_import_still_works(tmp_path) -> None:
    """R3-11 正控制:指针/根一致的合法两步导入不受影响;root 仍 raw_input。"""
    run_dir = _make_legacy_run(tmp_path, "legacy_ok_two_step", [
        [ACETALDEHYDE], [ACETIC_ACID]])
    target = PollutantPathwayStore(tmp_path / "ok_two_step_new.sqlite")
    result = import_legacy_run(run_dir, new_run_id="new-ok",
                               target_store=target)
    assert result["n_created"] == 2
    first_hyp = None
    for ev in target.list_events("new-ok"):
        hyp = target.get_hypothesis(ev["hypothesis_id"])
        state = target.get_state(hyp["substrate_state_ref"])
        if state["structure_origin"] == STRUCTURE_ORIGIN_RAW_INPUT:
            first_hyp = hyp
    assert first_hyp is not None
    target.close()


# ================================================================ §4
# 空展开计划契约 + 池审计同 hash 跳阶段留痕


def test_r4_s4_empty_expansion_plan_with_products_rejected(
        tmp_path) -> None:
    """§4 行 4 复现(missing_expansion_entries):事件有产物但
    entries=[] 且无 incomplete 声明 ⇒ 契约拒绝、零写入。"""
    store, sub, prod, hyp, event, args, states = _fixture(tmp_path, "me")
    args["expansion_plan"]["entries"] = []
    with pytest.raises(Ppv1SubmitContractError):
        store.submit_event(event, states=states, **args)
    assert store.counts()["events"] == 0
    store.close()


def test_r4_s4_explicit_incomplete_plan_accepted(tmp_path) -> None:
    """§4 行 4 边界:载荷显式 plan_status=incomplete(带原因)⇒ 合法
    (只补载荷契约,不实施 S3 队列)。"""
    store, sub, prod, hyp, event, args, states = _fixture(tmp_path, "ip")
    plan = build_expansion_plan(hyp, expanded=[], deferred=[],
                                not_tracked=[]).to_dict()
    plan["entries"] = []
    plan["plan_status"] = "incomplete"
    plan["incomplete_reason"] = "S3 队列未交付,展开决策延后(R4 只收紧契约)"
    args["expansion_plan"] = plan
    result = store.submit_event(event, states=states, **args)
    assert result["created"] is True
    stored = store.expansion_plan(event.event_id)
    assert stored["plan_status"] == "incomplete"
    store.close()


def test_r4_s4_pool_same_hash_skip_requires_reason() -> None:
    """§4 行 5 复现(pool_skipped_equal_hash_without_reason):跳过协议
    阶段且 hash 恰好连续(同 hash 跳阶段)⇒ 仍须登记 transition_reason。"""
    pool = [{"evidence_id": "A"}]
    stages = [record_pool_stage(stage="retrieved_raw", input_items=[],
                                output_items=pool),
              record_pool_stage(stage="structure_screened",
                                input_items=pool, output_items=pool)]
    with pytest.raises(PoolAuditError, match="transition_reason"):
        build_pool_audit(run_id="r", path_id="p", stages=stages,
                         input_preview_policy=INPUT_PREVIEW_OFF)
    # 登记跳过原因(即便 hash 连续)⇒ 合法留痕
    fixed = [stages[0],
             record_pool_stage(stage="structure_screened",
                               input_items=pool, output_items=pool,
                               transition_reason=(
                                   "typed_and_grouped_skipped:"
                                   "single_source_no_regroup"))]
    record = build_pool_audit(run_id="r", path_id="p", stages=fixed,
                              input_preview_policy=INPUT_PREVIEW_OFF)
    assert record.stages[1].transition_reason
    # 相邻协议阶段、无省略、hash 连续 ⇒ 无需 reason(不误伤正控制)
    adjacent = [stages[0],
                record_pool_stage(stage="typed_and_grouped",
                                  input_items=pool, output_items=pool)]
    record2 = build_pool_audit(run_id="r", path_id="p", stages=adjacent,
                               input_preview_policy=INPUT_PREVIEW_OFF)
    assert record2.stages[1].transition_reason == ""
