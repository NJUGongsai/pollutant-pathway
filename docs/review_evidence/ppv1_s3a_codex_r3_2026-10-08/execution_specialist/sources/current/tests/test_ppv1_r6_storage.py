"""R6 存储与适配线回归(Codex R5 复审 R5-05/R5-06/R5-07;v6)。

规则级合成夹具;临时 SQLite,无金标/封存材料。SQL UPDATE/DELETE
仅用于测试夹具模拟损坏;旧库只读(字节不变断言)。先红后绿:红
验证在基线 293bc62 工作树复跑本文件;v6 实现后全绿。

R5-05:事件出现清单首提绑定先存/部分先存 + 重放覆盖完整性(全
先存 states=[] 不再产空清单而使正常重放报损坏;删实际出现留无关
同物种出现、清单缩成非空子集均损坏;多既存出现不能替调用方猜
出处;先存全量首提 → 重放幂等)。
R5-06:首次复用既存 hypothesis 行也做同源 ID 重推(篡改已存前提
保留 ID ⇒ 首提即拒零写入,不以"下次重放能发现"代替;正常先存
假设与排序幂等保持)。
R5-07:旧同父同 CN 兄弟来源用独立路径身份锚(product_path_id)
核验,不再查同一张 path_instances 表循环自证;错指针降 CN-only
+ 原因 + 不导入相反立体 raw;正控制/多位置/旧库字节不变保持。
"""

from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pathway_v43.pollutant.chemstate import (  # noqa: E402
    build_chemical_state,
    build_chemical_state_from_cn_only,
)
from pathway_v43.pollutant.events import (  # noqa: E402
    build_expansion_plan,
    build_pathway_event,
    build_report_projection,
)
from pathway_v43.pollutant.hypothesis import (  # noqa: E402
    Participant,
    build_hypothesis,
    recompute_hypothesis_id,
)
from pathway_v43.pollutant.legacy_reader import (  # noqa: E402
    import_legacy_event,
    read_legacy_events,
)
from pathway_v43.pollutant.store import (  # noqa: E402
    Ppv1LedgerCorrupt,
    Ppv1SubmitContractError,
    PollutantPathwayStore,
)
from pathway_v43.storage.pathway_store import PathwayStore  # noqa: E402

ROOT = Path(tempfile.mkdtemp(prefix="r6_storage_"))


def state(smi, origin="source_product", refs=None):
    return build_chemical_state(smi, origin, refs)


def fixture(name):
    sub = state("CCO", "raw_input", [{"record": "sub-A"}])
    prod = state("CC=O", refs=[{"record": "prod-A"}])
    hyp = build_hypothesis(
        parent_path_id="p1", substrate_state_ref=sub.state_id,
        participants=[
            Participant(state_ref=sub.state_id, side="reactant",
                        role="primary_substrate", coefficient=None,
                        coefficient_status="unknown"),
            Participant(state_ref=prod.state_id, side="product",
                        role="principal_product", coefficient=None,
                        coefficient_status="unknown")],
        participant_list_status="partial", step_scope="net_reaction",
        origin_group_key=name)
    event = build_pathway_event(hyp, run_id=name, context_hash="ctx")
    args = {"report_projection": build_report_projection(
                hyp, max_reportable=1,
                ranked_state_refs=[prod.state_id]).to_dict(),
            "expansion_plan": build_expansion_plan(
                hyp, expanded=[prod.state_id], deferred=[],
                not_tracked=[]).to_dict(),
            "states": [sub.to_dict(), prod.to_dict()],
            "hypothesis_dict": hyp.to_dict()}
    return PollutantPathwayStore(ROOT / (name + ".sqlite")), sub, prod, \
        hyp, event, args


# ==================================================== R5-05 出现清单


def test_r5_05_pre_stored_all_binds_manifest_replay_idempotent() -> None:
    """R5 复审反例,基线 293bc62 红:全先存(put 两 state 后
    states=[] 首提)⇒ 首提 created=True 且清单覆盖两 ref,正常重放
    created=False 幂等(基线:首提 manifest=[] ⇒ 重放报
    event_appearance_manifest_missing)。"""
    store, sub, prod, hyp, event, args = fixture("r6_pre_all")
    store.put_state(args["states"][0])
    store.put_state(args["states"][1])
    result = store.submit_event(event, **dict(args, states=[]))
    assert result["created"] is True
    payload = json.loads(store.get_event(event.event_id)["payload"])
    manifest = payload["event_appearance_manifest"]
    assert manifest, "全先存首提不得产出空出现清单"
    assert {e["state_id"] for e in manifest} == {sub.state_id, prod.state_id}
    for sid in (sub.state_id, prod.state_id):
        row = store.conn.execute(
            "SELECT appearance_hash FROM state_appearances WHERE state_id=?",
            (sid,)).fetchone()
        assert {"state_id": sid,
                "appearance_hash": row["appearance_hash"]} in manifest
    before = store.counts()
    replayed = store.submit_event(event, **dict(args, states=[],
                                                hypothesis_dict=None))
    assert replayed["created"] is False  # 基线:此处 Ppv1LedgerCorrupt
    assert store.counts() == before  # 幂等:零新增
    store.close()


def test_r5_05_pre_stored_partial_actual_source_deleted_corrupt() -> None:
    """R5 复审反例,基线 293bc62 红:部分先存(事务只供底物、产物
    先存绑定)后删实际产物出现、留同物种无关出现 ⇒ 重放
    Ppv1LedgerCorrupt(基线:created=False 静默成功)。"""
    store, sub, prod, hyp, event, args = fixture("r6_pre_partial")
    store.put_state(prod.to_dict())
    actual_hash = store.conn.execute(
        "SELECT appearance_hash FROM state_appearances WHERE state_id=?",
        (prod.state_id,)).fetchone()["appearance_hash"]
    result = store.submit_event(event, **dict(args, states=[sub.to_dict()]))
    assert result["created"] is True
    payload = json.loads(store.get_event(event.event_id)["payload"])
    manifest = payload["event_appearance_manifest"]
    assert {e["state_id"] for e in manifest} == {sub.state_id, prod.state_id}
    assert {"state_id": prod.state_id,
            "appearance_hash": actual_hash} in manifest  # 绑定实际来源
    # 删实际来源出现,只留同物种无关出现(同图异拼写)
    store.put_state(state("O=CC", refs=[{"record": "unrelated-prod-B"}]).to_dict())
    store.conn.execute(
        "DELETE FROM state_appearances WHERE state_id=? AND appearance_hash=?",
        (prod.state_id, actual_hash))
    store.conn.commit()
    with pytest.raises(Ppv1LedgerCorrupt) as ei:
        store.submit_event(event, **dict(args, states=[],
                                         hypothesis_dict=None))
    assert ei.value.detail["kind"] == "event_appearance_manifest_entry_missing"
    store.close()


def test_r5_05_manifest_shrunk_to_nonempty_subset_corrupt() -> None:
    """R5 复审反例,基线 293bc62 红:完整清单 SQL 缩成非空子集 ⇒
    重放损坏(基线:清单子集仍逐项合法 ⇒ created=False 成功)。"""
    store, sub, prod, hyp, event, args = fixture("r6_subset")
    store.submit_event(event, **args)
    payload = json.loads(store.get_event(event.event_id)["payload"])
    manifest = payload["event_appearance_manifest"]
    payload["event_appearance_manifest"] = [
        e for e in manifest if e["state_id"] != prod.state_id]
    assert payload["event_appearance_manifest"]  # 非空子集
    store.conn.execute(
        "UPDATE events SET payload=? WHERE event_id=?",
        (json.dumps(payload), event.event_id))
    store.conn.commit()
    with pytest.raises(Ppv1LedgerCorrupt) as ei:
        store.submit_event(event, **dict(args, states=[],
                                         hypothesis_dict=None))
    assert ei.value.detail["kind"] == \
        "event_appearance_manifest_coverage_corrupt"
    assert ei.value.detail["missing_state_refs"] == [prod.state_id]
    store.close()


def test_r5_05_ambiguous_existing_appearances_first_submit_rejected() \
        -> None:
    """R5 反例(歧义拒绝):同 state 两条既存出现 + states=[] 首提 ⇒
    appearance_source_ambiguous 结构化拒绝零写入(多个既存出现不能
    替调用方猜出处;须随事务显式提供载荷或先在唯一出现下提交)。"""
    store, sub, prod, hyp, event, args = fixture("r6_ambiguous")
    store.put_state(sub.to_dict())
    store.put_state(state("CCO", "raw_input",
                          [{"record": "sub-A-OTHER-SOURCE"}]).to_dict())
    store.put_state(prod.to_dict())
    before = store.counts()
    with pytest.raises(Ppv1SubmitContractError) as ei:
        store.submit_event(event, **dict(args, states=[]))
    assert ei.value.detail["kind"] == "appearance_source_ambiguous"
    assert len(ei.value.detail["candidate_appearance_hashes"]) == 2
    assert store.counts() == before  # 零写入(无事件/投影/计划)
    store.close()


def test_r5_05_binding_without_any_appearance_row_corrupt() -> None:
    """R5 边界:参与物状态行存在但出现记录全缺(模拟损坏)⇒ 首提
    绑定无依据 ⇒ Ppv1LedgerCorrupt(账本不完整,不补账)。"""
    store, sub, prod, hyp, event, args = fixture("r6_no_appearance")
    store.put_state(sub.to_dict())
    store.put_state(prod.to_dict())
    store.conn.execute(
        "DELETE FROM state_appearances WHERE state_id=?", (prod.state_id,))
    store.conn.commit()
    with pytest.raises(Ppv1LedgerCorrupt) as ei:
        store.submit_event(event, **dict(args, states=[]))
    assert ei.value.detail["kind"] == "appearance_row_missing_for_binding"
    assert store.counts()["events"] == 0
    store.close()


def test_r5_05_supplied_all_delete_appearance_replay_corrupt_control() \
        -> None:
    """控制(保持绿):全量提交后删已列产物出现、留无关同物种出现
    ⇒ 重放损坏(基线已绿,R6 覆盖校验不放松逐项存在性)。"""
    store, sub, prod, hyp, event, args = fixture("r6_supplied_ctl")
    store.submit_event(event, **args)
    row = store.conn.execute(
        "SELECT appearance_hash FROM state_appearances WHERE state_id=?",
        (prod.state_id,)).fetchone()
    store.put_state(state("O=CC", refs=[{"record": "unrelated-prod-B"}]).to_dict())
    store.conn.execute(
        "DELETE FROM state_appearances WHERE state_id=? AND appearance_hash=?",
        (prod.state_id, row["appearance_hash"]))
    store.conn.commit()
    with pytest.raises(Ppv1LedgerCorrupt) as ei:
        store.submit_event(event, **dict(args, states=[],
                                         hypothesis_dict=None))
    assert ei.value.detail["kind"] == "event_appearance_manifest_entry_missing"
    store.close()


def test_r5_05_normal_replay_idempotent_control() -> None:
    """控制(保持绿):完整且一致的正常重放(不重复提供 dict)⇒
    created=False 幂等、counts 不变。"""
    store, sub, prod, hyp, event, args = fixture("r6_normal_ctl")
    assert store.submit_event(event, **args)["created"] is True
    before = store.counts()
    result = store.submit_event(event, **dict(args, states=[],
                                              hypothesis_dict=None))
    assert result["created"] is False
    assert store.counts() == before
    store.close()


def test_r5_05_cn_only_valid_control() -> None:
    """控制(保持绿):CN-only 状态合法落账,未知事实契约不误伤。"""
    store = PollutantPathwayStore(ROOT / "r6_cn_only.sqlite")
    cn_state = build_chemical_state_from_cn_only("CCO")
    store.put_state(cn_state.to_dict())
    saved = store.get_state(cn_state.state_id)
    assert saved is not None
    assert saved["formal_charge"] is None
    assert saved["structure_origin"] == "legacy_cn_only"
    store.close()


# ==================================================== R5-06 既存假设首提


def test_r5_06_existing_hypothesis_tampered_first_submit_rejected() -> None:
    """R5 复审反例,基线 293bc62 红:put 合法行 → SQL 改 assumptions
    保留 ID → submit hypothesis_dict=None ⇒ 首提即
    Ppv1LedgerCorrupt(hypothesis_payload_id_corrupt)、counts 不变零
    写入(基线:created=True,下次重放才拒绝)。"""
    store, sub, prod, hyp, event, args = fixture("r6_hyp_tamper")
    store.put_hypothesis(hyp.to_dict())
    mutated = json.loads(json.dumps(args["hypothesis_dict"]))
    mutated["assumptions"] = ["changed premise after initial put"]
    assert recompute_hypothesis_id(mutated) != hyp.hypothesis_id
    store.conn.execute(
        "UPDATE hypotheses SET payload=? WHERE hypothesis_id=?",
        (json.dumps(mutated), hyp.hypothesis_id))
    store.conn.commit()
    before = store.counts()
    with pytest.raises(Ppv1LedgerCorrupt) as ei:
        store.submit_event(event, **dict(args, hypothesis_dict=None))
    assert ei.value.detail["kind"] == "hypothesis_payload_id_corrupt"
    assert store.counts() == before  # 零新增事件/投影/计划
    assert store.get_event(event.event_id) is None
    store.close()


def test_r5_06_pre_stored_valid_hypothesis_first_submit_control() -> None:
    """控制(保持绿):先存合法假设 → submit(hypothesis_dict=None)⇒
    created=True(首提复用既存行的合法路径不被重推误伤)。"""
    store, sub, prod, hyp, event, args = fixture("r6_hyp_legal")
    store.put_hypothesis(hyp.to_dict())
    result = store.submit_event(event, **dict(args, hypothesis_dict=None))
    assert result["created"] is True
    assert store.counts()["events"] == 1
    store.close()


@pytest.mark.parametrize(
    "mutate,kind",
    [(lambda d: d.update(
        {"assumptions": ["changed premise after initial put"]}),
      "hypothesis_payload_id_corrupt"),
     (lambda d: d.update({"hypothesis_id": "fake:inner-id"}),
      "hypothesis_id_corrupt"),
     (lambda d: d.update({"schema_version": "ppv1-hypothesis-99"}),
      "hypothesis_schema_corrupt")])
def test_r5_06_existing_hypothesis_row_first_use_full_same_source(
        mutate, kind) -> None:
    """R5-06 验收补齐(同源契约三项):首提复用既存行与重放同一验证
    源——SQL 只篡改载荷内 hypothesis_id 字段或 schema 版本(内容重推
    恰好仍可得行键 ID 的形状)也在首提即拒,零写入,不等下次重放。"""
    store, sub, prod, hyp, event, args = fixture("r6_hyp_" + kind)
    store.put_hypothesis(hyp.to_dict())
    mutated = json.loads(json.dumps(args["hypothesis_dict"]))
    mutate(mutated)
    store.conn.execute(
        "UPDATE hypotheses SET payload=? WHERE hypothesis_id=?",
        (json.dumps(mutated), hyp.hypothesis_id))
    store.conn.commit()
    before = store.counts()
    with pytest.raises(Ppv1LedgerCorrupt) as ei:
        store.submit_event(event, **dict(args, hypothesis_dict=None))
    assert ei.value.detail["kind"] == kind
    assert store.counts() == before
    assert store.get_event(event.event_id) is None
    store.close()


def test_r5_06_reordered_requirements_same_payload_idempotent() -> None:
    """控制(保持绿):同语义不同顺序 requirements ⇒ 同 ID 同 payload;
    先存(反序)→ 首提(正序)→ 重放(正序)均幂等,不报冲突。"""
    store = PollutantPathwayStore(ROOT / "r6_hyp_order.sqlite")
    sub = state("CCO", "raw_input", [{"record": "sub-A"}])
    prod = state("CC=O", refs=[{"record": "prod-A"}])
    participants = [
        Participant(state_ref=sub.state_id, side="reactant",
                    role="primary_substrate", coefficient=None,
                    coefficient_status="unknown"),
        Participant(state_ref=prod.state_id, side="product",
                    role="principal_product", coefficient=None,
                    coefficient_status="unknown")]
    reqs = [{"key": "oxygen_regime", "level": "essential", "value": "aerobic"},
            {"key": "pH", "level": "preference", "value": 7}]
    hyp_a = build_hypothesis(
        parent_path_id="p1", substrate_state_ref=sub.state_id,
        participants=participants, participant_list_status="partial",
        step_scope="net_reaction", origin_group_key="r6_hyp_order",
        requirements=list(reqs))
    hyp_b = build_hypothesis(
        parent_path_id="p1", substrate_state_ref=sub.state_id,
        participants=participants, participant_list_status="partial",
        step_scope="net_reaction", origin_group_key="r6_hyp_order",
        requirements=list(reversed(reqs)))
    assert hyp_a.hypothesis_id == hyp_b.hypothesis_id  # id 侧已排序归一
    event = build_pathway_event(hyp_a, run_id="r6_hyp_order",
                                context_hash="ctx")
    args = {"report_projection": build_report_projection(
                hyp_a, max_reportable=1,
                ranked_state_refs=[prod.state_id]).to_dict(),
            "expansion_plan": build_expansion_plan(
                hyp_a, expanded=[prod.state_id], deferred=[],
                not_tracked=[]).to_dict(),
            "states": [sub.to_dict(), prod.to_dict()],
            "hypothesis_dict": hyp_a.to_dict()}
    store.put_hypothesis(hyp_b.to_dict())  # 先存:反序同语义载荷
    first = store.submit_event(event, **args)  # 首提:正序载荷
    assert first["created"] is True
    again = store.submit_event(event, **args)
    assert again["created"] is False
    assert store.counts()["hypotheses"] == 1
    store.close()


# ==================================================== R5-07 旧兄弟来源


def make_sibling_legacy(name):
    """同父两分支(同 CN 相反立体)+ A 支后续消费事件(探针同构)。"""
    rd = ROOT / name
    rd.mkdir(exist_ok=True)
    old = PathwayStore(rd / "pathway.sqlite")
    root_cn = state("CCO").cn_identity
    root = old.ensure_run(name, "CCO", root_cn)
    (rd / "run_identity.json").write_text(json.dumps({
        "schema_version": "v43-identity-1",
        "inputs": {"root_smiles": "CCO", "root_identity": root_cn}}))
    left, right = "C[C@H](O)CC", "C[C@@H](O)CC"

    def submit(label, pid, cn, smi):
        products = [{"position": 0, "product_smiles": smi,
                     "product_smiles_full": smi,
                     "product_identity": state(smi).cn_identity}]
        evidence = {"evidence_id": name + "-" + label,
                    "source_id": name + "-" + label,
                    "kind": "recorded_reaction",
                    "condition_fit": "unknown", "products": products}
        return old.submit_event(
            run_id=name, parent_path_id=pid, substrate_identity=cn,
            evidence=evidence, products=products,
            expandable_path_ids=[], deferred_path_ids=[])

    branch_a = submit("branch-a", root, root_cn, left)
    branch_b = submit("branch-b", root, root_cn, right)
    consumer = submit("consume-a", branch_a["path_ids"][0],
                      state(left).cn_identity, "CC=O")
    old.close()
    return rd, branch_a, branch_b, consumer, left, right


def test_r5_07_same_parent_wrong_sibling_source_degraded() -> None:
    """R5 复审反例,基线 293bc62 红:A 路径来源指针 SQL 改指同父 B
    事件(产物同 CN 相反立体)⇒ 导入底物降 CN-only、uncertainty 含
    substrate_source_event_relation_mismatch、不导入 B 的相反立体
    raw(基线:child_paths 循环自证 ⇒ 接受 B 的 raw 无注记);旧库
    字节不变。"""
    rd, branch_a, branch_b, consumer, left, right = make_sibling_legacy(
        "legacy_r6_wrong_sibling")
    # 同 CN、不同严格身份(立体相反):错误来源不可用 CN 顶替
    assert state(left).cn_identity == state(right).cn_identity
    assert state(left).state_id != state(right).state_id
    conn = sqlite3.connect(rd / "pathway.sqlite")
    conn.execute("UPDATE path_instances SET event_id=? WHERE path_id=?",
                 (branch_b["event_id"], branch_a["path_ids"][0]))
    conn.commit()
    conn.close()
    events = read_legacy_events(rd)
    ev = next(e for e in events if e["event_id"] == consumer["event_id"])
    before = (rd / "pathway.sqlite").read_bytes()
    imported = import_legacy_event(rd, ev, new_run_id="r6-wrong-sibling")
    sub = next(s for s in imported["states"]
               if s["state_id"] == imported["hypothesis"].substrate_state_ref)
    assert any("substrate_source_event_relation_mismatch" in note
               for note in imported["uncertainty_notes"])
    assert sub["structure_origin"] == "legacy_cn_only"
    assert sub["structure_smiles_raw"] != right  # 不是 B 的 raw(相反立体)
    assert sub["structure_smiles_raw"] != left  # 也不是 A 的 raw(CN-only)
    assert (rd / "pathway.sqlite").read_bytes() == before  # 旧库只读


def test_r5_07_correct_sibling_source_control() -> None:
    """控制(保持绿):合法兄弟来源(指针未改,身份锚匹配)⇒ archive
    恢复 A 的结构,无关系降级注记;旧库字节不变。"""
    rd, branch_a, branch_b, consumer, left, right = make_sibling_legacy(
        "legacy_r6_correct_sibling")
    events = read_legacy_events(rd)
    ev = next(e for e in events if e["event_id"] == consumer["event_id"])
    before = (rd / "pathway.sqlite").read_bytes()
    imported = import_legacy_event(rd, ev, new_run_id="r6-correct-sibling")
    sub = next(s for s in imported["states"]
               if s["state_id"] == imported["hypothesis"].substrate_state_ref)
    assert sub["structure_origin"] == "source_product"
    assert sub["structure_smiles_raw"] == left
    assert not any("relation_mismatch" in note
                   for note in imported["uncertainty_notes"])
    assert (rd / "pathway.sqlite").read_bytes() == before


def test_r5_07_multi_position_identity_anchor_control() -> None:
    """控制(保持绿):多位次产物路径的身份锚按位次派生
    (product_path_id(run, event, position)),position=1 的合法消费
    不被身份锚误伤。"""
    name = "legacy_r6_multipos"
    rd = ROOT / name
    rd.mkdir(exist_ok=True)
    old = PathwayStore(rd / "pathway.sqlite")
    root_cn = state("CCO").cn_identity
    root = old.ensure_run(name, "CCO", root_cn)
    (rd / "run_identity.json").write_text(json.dumps({
        "schema_version": "v43-identity-1",
        "inputs": {"root_smiles": "CCO", "root_identity": root_cn}}))
    products = [
        {"position": 0, "product_smiles": "C[C@H](O)CC",
         "product_smiles_full": "C[C@H](O)CC",
         "product_identity": state("C[C@H](O)CC").cn_identity},
        {"position": 1, "product_smiles": "CC=O",
         "product_smiles_full": "CC=O",
         "product_identity": state("CC=O").cn_identity}]
    evidence = {"evidence_id": name + "-e0", "source_id": name + "-e0",
                "kind": "recorded_reaction", "condition_fit": "unknown",
                "products": products}
    result = old.submit_event(run_id=name, parent_path_id=root,
                              substrate_identity=root_cn, evidence=evidence,
                              products=products, expandable_path_ids=[],
                              deferred_path_ids=[])
    consumer_products = [
        {"position": 0, "product_smiles": "CC(=O)O",
         "product_smiles_full": "CC(=O)O",
         "product_identity": state("CC(=O)O").cn_identity}]
    consumer = old.submit_event(
        run_id=name, parent_path_id=result["path_ids"][1],
        substrate_identity=state("CC=O").cn_identity,
        evidence={"evidence_id": name + "-e1", "source_id": name + "-e1",
                  "kind": "recorded_reaction", "condition_fit": "unknown",
                  "products": consumer_products},
        products=consumer_products, expandable_path_ids=[],
        deferred_path_ids=[])
    old.close()
    events = read_legacy_events(rd)
    ev = next(e for e in events if e["event_id"] == consumer["event_id"])
    before = (rd / "pathway.sqlite").read_bytes()
    imported = import_legacy_event(rd, ev, new_run_id="r6-multipos")
    sub = next(s for s in imported["states"]
               if s["state_id"] == imported["hypothesis"].substrate_state_ref)
    assert sub["structure_origin"] == "source_product"
    assert sub["structure_smiles_raw"] == "CC=O"  # position 1 的产物
    assert not any("relation_mismatch" in note
                   for note in imported["uncertainty_notes"])
    assert (rd / "pathway.sqlite").read_bytes() == before
