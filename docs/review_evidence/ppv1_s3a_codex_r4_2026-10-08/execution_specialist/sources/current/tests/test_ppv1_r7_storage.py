"""R7 存储与适配线回归(Codex R6 复审 R6-04/R6-05;v7)。

规则级合成夹具;临时 SQLite,无金标/封存材料。SQL UPDATE/DELETE
仅用于测试夹具在**新建合成库**中模拟损坏并观察公共 put/submit 入
口的零写入拒绝;先红后绿:红验证在基线 6d90201 工作树复跑本文件
(与 R6 同口径);v7 实现后全绿。

R6-04:首提复用既存 state/appearance 行立即共用重放同源校验 ——
先 public put 合法数据,仅在合成 SQLite 损坏单字段(CN/未来
schema/inner ID/appearance refs 不改 hash),再 states=[] 首提:
基线 created=True 写事件/投影/计划(重放才 LedgerCorrupt);v7
首提即 Ppv1LedgerCorrupt、零新增;合法先存/显式状态/正常首提与
重放保持。
R6-05:完整 event appearance 集合的独立完整性依据 —— 合法首提含
底物及同 SID 两个不同 raw/source_refs/hash 的 prod-A/prod-B(manifest
三项);删清单 A 留 B、或连实际 A 行也删:基线无输入重放仍
created=False;v7 与独立完整性表 event_appearance_links 双向失配
⇒ 损坏;保持原清单只删 A 行(entry_missing)既有拒绝;多来源/
排序幂等/正常无输入重放保持。
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pathway_v43.pollutant.chemstate import (  # noqa: E402
    build_chemical_state,
)
from pathway_v43.pollutant.events import (  # noqa: E402
    build_expansion_plan,
    build_pathway_event,
    build_report_projection,
)
from pathway_v43.pollutant.hypothesis import (  # noqa: E402
    Participant,
    build_hypothesis,
)
from pathway_v43.pollutant.store import (  # noqa: E402
    Ppv1LedgerCorrupt,
    PollutantPathwayStore,
)

ROOT = Path(tempfile.mkdtemp(prefix="r7_storage_"))


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


def observed(store, event, args):
    """公共 submit 观察:结果或结构化错误 + 计数前后(零写入断言)。"""
    before = store.counts()
    try:
        out = {"created": store.submit_event(event, **args)["created"]}
    except Exception as exc:  # noqa: BLE001
        out = {"error": type(exc).__name__,
               "kind": getattr(exc, "detail", {}).get("kind")}
    return out, store.counts() == before


def replay(store, event, args):
    return observed(store, event,
                    dict(args, states=[], hypothesis_dict=None))


# ------------------------------------------------- R6-04 首提复用校验

@pytest.mark.parametrize("field,kind", [
    ("cn_identity", "state_row_corrupt"),
    ("schema_version", "state_schema_corrupt"),
    ("state_id", "state_inner_id_corrupt"),
])
def test_r6_04_existing_state_corrupt_first_submit_rejected(
        field, kind) -> None:
    """R6 复审反例,基线 6d90201 红:先 public put 合法 CCO/CC=O,仅
    在合成库改 prod 单字段(CN→CCN、schema→未来版本、载荷内
    state_id 与行键不符),再 states=[] 首提 —— 基线 created=True
    写事件/投影/计划(重放才 state_*_corrupt);v7 首提即
    Ppv1LedgerCorrupt(kind)、零写入,不以"重放能发现"代替。"""
    store, sub, prod, hyp, event, args = fixture(
        "r6_04_state_" + field)
    for s in args["states"]:
        store.put_state(s)
    saved = json.loads(store.conn.execute(
        "SELECT payload FROM states WHERE state_id=?",
        (prod.state_id,)).fetchone()[0])
    saved[field] = {"cn_identity": "CCN",
                    "schema_version": "ppv1-chemstate-99",
                    "state_id": "fake:inner-state"}[field]
    store.conn.execute(
        "UPDATE states SET payload=? WHERE state_id=?",
        (json.dumps(saved), prod.state_id))
    store.conn.commit()
    outcome, preserved = observed(store, event, dict(args, states=[]))
    assert outcome == {"error": "Ppv1LedgerCorrupt", "kind": kind}
    assert preserved, "首提复用损坏行须零写入"


def test_r6_04_existing_appearance_corrupt_first_submit_rejected() -> None:
    """R6 复审反例,基线 6d90201 红:appearance payload 的
    source_refs 被改而 hash 列不动 —— 基线 states=[] 首提 created=
    True(重放才 appearance_hash_corrupt);v7 首提即拒、零写入。"""
    store, sub, prod, hyp, event, args = fixture(
        "r6_04_appearance")
    for s in args["states"]:
        store.put_state(s)
    row = store.conn.execute(
        "SELECT appearance_hash, payload FROM state_appearances"
        " WHERE state_id=?", (prod.state_id,)).fetchone()
    payload = json.loads(row["payload"])
    payload["source_refs"] = [{"record": "modified_without_hash"}]
    store.conn.execute(
        "UPDATE state_appearances SET payload=? WHERE state_id=? AND"
        " appearance_hash=?",
        (json.dumps(payload), prod.state_id, row["appearance_hash"]))
    store.conn.commit()
    outcome, preserved = observed(store, event, dict(args, states=[]))
    assert outcome == {"error": "Ppv1LedgerCorrupt",
                       "kind": "appearance_hash_corrupt"}
    assert preserved


def test_r6_04_valid_existing_first_submit_and_replay_control() -> None:
    """正控(基线亦绿):合法既存行(先 put 两 state)states=[] 首提
    created=True、清单覆盖两 ref;紧接无输入重放 created=False 幂等
    (R5-05 既有行为保持,新增校验不误拒合法先存)。"""
    store, sub, prod, hyp, event, args = fixture("r6_04_valid")
    for s in args["states"]:
        store.put_state(s)
    outcome, _ = observed(store, event, dict(args, states=[]))
    assert outcome == {"created": True}
    payload = json.loads(store.get_event(event.event_id)["payload"])
    assert {e["state_id"] for e in
            payload["event_appearance_manifest"]} == \
        {sub.state_id, prod.state_id}
    outcome, preserved = replay(store, event, args)
    assert outcome == {"created": False}
    assert preserved
    store.close()


def test_r6_04_partial_existing_explicit_states_control() -> None:
    """正控(基线亦绿):部分先存(put sub)+ 显式提供 prod 的首提
    created=True;既存 sub 行经新增同源校验幂等通过。"""
    store, sub, prod, hyp, event, args = fixture("r6_04_partial")
    store.put_state(args["states"][0])
    outcome, _ = observed(store, event, dict(
        args, states=[args["states"][1]]))
    assert outcome == {"created": True}
    outcome, preserved = replay(store, event, args)
    assert outcome == {"created": False}
    assert preserved
    store.close()


# ------------------------------------------- R6-05 完整出现集合完整性

def _multi_occurrence_fixture(name):
    """合法首提:底物 + 同 SID 两个不同 raw/source_refs/hash 的
    prod-A(CC=O/refs A)与 prod-B(O=CC/refs B)—— manifest 三项。"""
    store, sub, prod, hyp, event, args = fixture(name)
    other = state("O=CC", refs=[{"record": "prod-B"}])
    return store, sub, prod, other, hyp, event, args


def test_r6_05_multi_source_manifest_and_links_control() -> None:
    """正控(基线亦绿):同 SID 多来源出现各自保留(不合并);首提
    manifest 三项;v7 同时把完整 (sid, hash) 集合写入独立完整性表
    event_appearance_links(3 行);无输入重放 created=False 幂等;
    states 提供顺序不影响(links/manifest 为集合语义)。"""
    store, sub, prod, other, hyp, event, args = \
        _multi_occurrence_fixture("r6_05_control")
    outcome, _ = observed(store, event, dict(
        args, states=[sub.to_dict(), prod.to_dict(),
                      other.to_dict()]))
    assert outcome == {"created": True}
    payload = json.loads(store.get_event(event.event_id)["payload"])
    manifest = payload["event_appearance_manifest"]
    assert len(manifest) == 3
    assert len({e["appearance_hash"] for e in manifest
                if e["state_id"] == prod.state_id}) == 2
    links = store.conn.execute(
        "SELECT state_id, appearance_hash FROM event_appearance_links"
        " WHERE event_id=?", (event.event_id,)).fetchall()
    assert {(r["state_id"], r["appearance_hash"]) for r in links} == \
        {(e["state_id"], e["appearance_hash"]) for e in manifest}
    assert store.counts()["event_appearance_links"] == 3
    outcome, preserved = replay(store, event, args)
    assert outcome == {"created": False}
    assert preserved
    store.close()


def test_r6_05_delete_manifest_entry_leaving_other_corrupt() -> None:
    """R6 复审反例,基线 6d90201 红:删清单 A 项留 B(同 SID 的另一
    出现继续覆盖 product 状态)—— 基线无输入重放仍 created=False
    (state_id 集合恰好仍等);v7:清单与独立完整性表双向失配 ⇒
    Ppv1LedgerCorrupt(event_appearance_manifest_link_corrupt),
    同 state 另一出现不能冒充完整集合。"""
    store, sub, prod, other, hyp, event, args = \
        _multi_occurrence_fixture("r6_05_del_manifest")
    outcome, _ = observed(store, event, dict(
        args, states=[sub.to_dict(), prod.to_dict(),
                      other.to_dict()]))
    assert outcome == {"created": True}
    payload = json.loads(store.get_event(event.event_id)["payload"])
    a_hash = next(
        e["appearance_hash"] for e in payload["event_appearance_manifest"]
        if e["state_id"] == prod.state_id
        and _appearance_refs(store, prod.state_id,
                             e["appearance_hash"]) == [{"record":
                                                        "prod-A"}])
    payload["event_appearance_manifest"] = [
        e for e in payload["event_appearance_manifest"]
        if e["appearance_hash"] != a_hash]
    store.conn.execute(
        "UPDATE events SET payload=? WHERE event_id=?",
        (json.dumps(payload), event.event_id))
    store.conn.commit()
    outcome, preserved = replay(store, event, args)
    assert outcome == {"error": "Ppv1LedgerCorrupt",
                       "kind": "event_appearance_manifest_link_corrupt"}
    assert preserved
    store.close()


def test_r6_05_delete_manifest_entry_and_row_corrupt() -> None:
    """R6 复审反例,基线 6d90201 红:删清单 A 项**并**删实际 A 出现
    行 —— 基线无输入重放仍 created=False;v7:与 links 失配 ⇒
    损坏(完整性依据独立于事件 payload,event_semantics_hash 不含
    清单,payload 单点编辑+删行不再能洗掉该次出现)。"""
    store, sub, prod, other, hyp, event, args = \
        _multi_occurrence_fixture("r6_05_del_both")
    outcome, _ = observed(store, event, dict(
        args, states=[sub.to_dict(), prod.to_dict(),
                      other.to_dict()]))
    assert outcome == {"created": True}
    payload = json.loads(store.get_event(event.event_id)["payload"])
    a_hash = next(
        e["appearance_hash"] for e in payload["event_appearance_manifest"]
        if e["state_id"] == prod.state_id
        and _appearance_refs(store, prod.state_id,
                             e["appearance_hash"]) == [{"record":
                                                        "prod-A"}])
    payload["event_appearance_manifest"] = [
        e for e in payload["event_appearance_manifest"]
        if e["appearance_hash"] != a_hash]
    store.conn.execute(
        "UPDATE events SET payload=? WHERE event_id=?",
        (json.dumps(payload), event.event_id))
    store.conn.execute(
        "DELETE FROM state_appearances WHERE state_id=? AND"
        " appearance_hash=?", (prod.state_id, a_hash))
    store.conn.commit()
    outcome, preserved = replay(store, event, args)
    assert outcome == {"error": "Ppv1LedgerCorrupt",
                       "kind": "event_appearance_manifest_link_corrupt"}
    assert preserved
    store.close()


def test_r6_05_delete_row_only_keeps_entry_missing_control() -> None:
    """既有控制(基线亦绿,须保留):保持原清单、只删实际 A 行 ⇒
    entry_missing 拒绝(清单项引用的行不存在;v7 不以此代替、也不被
    links 校验替代)。"""
    store, sub, prod, other, hyp, event, args = \
        _multi_occurrence_fixture("r6_05_del_row")
    outcome, _ = observed(store, event, dict(
        args, states=[sub.to_dict(), prod.to_dict(),
                      other.to_dict()]))
    assert outcome == {"created": True}
    payload = json.loads(store.get_event(event.event_id)["payload"])
    a_hash = next(
        e["appearance_hash"] for e in payload["event_appearance_manifest"]
        if e["state_id"] == prod.state_id
        and _appearance_refs(store, prod.state_id,
                             e["appearance_hash"]) == [{"record":
                                                        "prod-A"}])
    store.conn.execute(
        "DELETE FROM state_appearances WHERE state_id=? AND"
        " appearance_hash=?", (prod.state_id, a_hash))
    store.conn.commit()
    outcome, preserved = replay(store, event, args)
    assert outcome == {"error": "Ppv1LedgerCorrupt",
                       "kind": "event_appearance_manifest_entry_missing"}
    assert preserved
    store.close()


def test_r6_05_delete_link_rows_only_corrupt() -> None:
    """v7 新控制:只删独立完整性表行(清单/出现行都保持)⇒ 双向
    失配同样损坏(两处同源依据须一致,删任一侧都不可)。"""
    store, sub, prod, other, hyp, event, args = \
        _multi_occurrence_fixture("r6_05_del_links")
    outcome, _ = observed(store, event, dict(
        args, states=[sub.to_dict(), prod.to_dict(),
                      other.to_dict()]))
    assert outcome == {"created": True}
    store.conn.execute(
        "DELETE FROM event_appearance_links WHERE event_id=? AND"
        " state_id=?", (event.event_id, prod.state_id))
    store.conn.commit()
    outcome, preserved = replay(store, event, args)
    assert outcome == {"error": "Ppv1LedgerCorrupt",
                       "kind": "event_appearance_manifest_link_corrupt"}
    assert preserved
    store.close()


def test_r6_05_order_idempotence_links_set_control() -> None:
    """正控(排序幂等):states 提供顺序不同 ⇒ 同一事件 manifest/
    links 集合一致(集合语义;重放 created=False)。"""
    store, sub, prod, other, hyp, event, args = \
        _multi_occurrence_fixture("r6_05_order_a")
    outcome, _ = observed(store, event, dict(
        args, states=[other.to_dict(), prod.to_dict(),
                      sub.to_dict()]))
    assert outcome == {"created": True}
    links_a = {(r["state_id"], r["appearance_hash"])
               for r in store.conn.execute(
                   "SELECT state_id, appearance_hash FROM"
                   " event_appearance_links WHERE event_id=?",
                   (event.event_id,)).fetchall()}
    outcome, preserved = replay(store, event, args)
    assert outcome == {"created": False}
    assert preserved
    links_b = {(r["state_id"], r["appearance_hash"])
               for r in store.conn.execute(
                   "SELECT state_id, appearance_hash FROM"
                   " event_appearance_links WHERE event_id=?",
                   (event.event_id,)).fetchall()}
    assert links_a == links_b and len(links_a) == 3
    store.close()


def _appearance_refs(store, sid, appearance_hash):
    row = store.conn.execute(
        "SELECT payload FROM state_appearances WHERE state_id=? AND"
        " appearance_hash=?", (sid, appearance_hash)).fetchone()
    return json.loads(row["payload"])["source_refs"]
