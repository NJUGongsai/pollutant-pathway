"""R8 存储线回归(Codex R7 复审 R7-02;v8)。

规则级合成夹具;临时 SQLite,无金标/封存材料。SQL UPDATE 仅用于
测试夹具在**新建合成库**中模拟损坏并观察公共 put/submit 入口的零
写入拒绝;先红后绿:红验证在基线 858dd94 工作树复跑本文件(与 R7
同口径);v8 实现后全绿。

R7-02:首提校验实际引用/复用的既存 appearance,包括 supplied SID 的
已存同 (SID,hash) 行 —— 先 public put 合法状态,仅在合成 SQLite 把
产物 appearance.source_refs 改掉而 hash 不动,再首提:
- states=[](复用路径)基线已拒(R6-04 修复保持);
- 显式重给有效 prod-only 或全量 states:基线仍 created=True 并新增
  event/projection/plan/links(重放才 appearance_hash_corrupt)——
  R7-02 反例;
- v8:复用校验统一到收集阶段(_collect_state_writes,首提/重放共
  用),实际复用的坏 appearance 在各 supply 路径立即
  Ppv1LedgerCorrupt、零新增,不延后、不自动覆盖修库。
正控:合法 none/partial/all 先存首提 created=True、无输入重放
created=False;语义冲突零写入拒绝保持;同图多来源/排序由 r7_storage
既有回归保持。
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

ROOT = Path(tempfile.mkdtemp(prefix="r8_storage_"))


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


def corrupt_prod_appearance(store, prod):
    """合成库损坏:仅改产物 appearance.source_refs,hash 列不动。"""
    row = store.conn.execute(
        "SELECT appearance_hash, payload FROM state_appearances"
        " WHERE state_id=?", (prod.state_id,)).fetchone()
    payload = json.loads(row["payload"])
    old_refs = payload["source_refs"]
    payload["source_refs"] = [{"record": "tampered-only-in-synthetic-db"}]
    store.conn.execute(
        "UPDATE state_appearances SET payload=? WHERE state_id=? AND"
        " appearance_hash=?",
        (json.dumps(payload), prod.state_id, row["appearance_hash"]))
    store.conn.commit()
    return row["appearance_hash"], old_refs


# ---------------------------------------------- R7-02 反例(supplied 路径)

def test_r7_02_prod_only_resupply_corrupt_first_submit_rejected() -> None:
    """R7 复审反例,基线 858dd94 红:先 public put 合法 sub/prod,仅
    在合成库改产物 appearance.source_refs(hash 不动),再首提**只重给
    原本有效的产物 payload** —— 基线 created=True 并新增 event/
    projection/plan 各 1、links 2(重放才 appearance_hash_corrupt);
    v8:实际复用的坏 appearance 在首提立即 Ppv1LedgerCorrupt(
    appearance_hash_corrupt)、零新增,不延后。"""
    store, sub, prod, hyp, event, args = fixture(
        "r7_02_prod_only_corrupt")
    for s in args["states"]:
        store.put_state(s)
    corrupt_prod_appearance(store, prod)
    outcome, preserved = observed(store, event,
                                  dict(args, states=[prod.to_dict()]))
    assert outcome == {"error": "Ppv1LedgerCorrupt",
                       "kind": "appearance_hash_corrupt"}
    assert preserved, "首提复用损坏出现行须零写入(事件/投影/计划/links)"
    assert store.get_event(event.event_id) is None  # 零新增事件
    store.close()


def test_r7_02_all_states_resupply_corrupt_first_submit_rejected() -> None:
    """R7 复审反例,基线 858dd94 红:同上损坏,**重给原本有效的全量
    states** —— 基线同样 created=True 并新增记录;v8:首提即
    LedgerCorrupt、零新增(supplied 不从复用校验豁免,不按
    supplied/unsupplied 两套规则授信)。"""
    store, sub, prod, hyp, event, args = fixture("r7_02_all_corrupt")
    for s in args["states"]:
        store.put_state(s)
    corrupt_prod_appearance(store, prod)
    outcome, preserved = observed(
        store, event,
        dict(args, states=[sub.to_dict(), prod.to_dict()]))
    assert outcome == {"error": "Ppv1LedgerCorrupt",
                       "kind": "appearance_hash_corrupt"}
    assert preserved
    assert store.get_event(event.event_id) is None
    store.close()


def test_r7_02_replay_with_supplied_states_shared_rule() -> None:
    """共享规则(收集/绑定/重放,基线亦拒、保持):合法首提落账后,
    仅在合成库损坏产物 appearance,再**带有效载荷重放**(重给 prod
    payload)同样 appearance_hash_corrupt 零写入 —— 与无输入重放同一
    验证源;v8 收集阶段同源校验只是把拒绝提前,不改变结论。"""
    store, sub, prod, hyp, event, args = fixture("r7_02_replay_supplied")
    outcome, _ = observed(store, event, args)
    assert outcome == {"created": True}  # 合法首提落账
    corrupt_prod_appearance(store, prod)
    outcome, preserved = observed(store, event,
                                  dict(args, states=[prod.to_dict()],
                                       hypothesis_dict=None))
    assert outcome == {"error": "Ppv1LedgerCorrupt",
                       "kind": "appearance_hash_corrupt"}
    assert preserved
    store.close()


# ---------------------------------------------- 既有反例保持(states=[])

def test_r7_02_none_supply_corrupt_first_submit_still_rejected() -> None:
    """既有控制(R6-04 修复保持,基线亦拒):同损坏、states=[] 首提
    ⇒ 首提即 appearance_hash_corrupt、零写入;v8 收集阶段新校验不
    替代/不破坏该路径。"""
    store, sub, prod, hyp, event, args = fixture("r7_02_none_corrupt")
    for s in args["states"]:
        store.put_state(s)
    corrupt_prod_appearance(store, prod)
    outcome, preserved = observed(store, event, dict(args, states=[]))
    assert outcome == {"error": "Ppv1LedgerCorrupt",
                       "kind": "appearance_hash_corrupt"}
    assert preserved
    store.close()


# ------------------------------------------------------- 正控(基线亦绿)

@pytest.mark.parametrize("supplied", ["none", "prod_only", "all"])
def test_r7_02_valid_existing_supply_first_and_replay_control(
        supplied) -> None:
    """正控(基线亦绿):无损坏时 none/prod_only/all 三种提供形状首提
    created=True;紧接无输入重放 created=False 幂等零写入 —— 新校验
    只核实际复用的既存行,不误拒合法先存/显式重给。"""
    store, sub, prod, hyp, event, args = fixture(
        "r7_02_valid_" + supplied)
    for s in args["states"]:
        store.put_state(s)
    provided = ([] if supplied == "none"
                else [prod.to_dict()] if supplied == "prod_only"
                else args["states"])
    outcome, _ = observed(store, event, dict(args, states=provided))
    assert outcome == {"created": True}
    payload = json.loads(store.get_event(event.event_id)["payload"])
    assert {e["state_id"] for e in payload["event_appearance_manifest"]} \
        == {sub.state_id, prod.state_id}
    outcome, preserved = replay(store, event, args)
    assert outcome == {"created": False}
    assert preserved
    store.close()


def test_r7_02_fresh_first_submit_with_states_control() -> None:
    """正控(基线亦绿):全新库(无先存 put)直接随事务提供 states
    首提 —— appearance 行不存在 ⇒ 收集阶段校验跳过(新增路径),
    created=True、links 两行;合法首提不受影响。"""
    store, sub, prod, hyp, event, args = fixture("r7_02_fresh")
    outcome, _ = observed(store, event, args)
    assert outcome == {"created": True}
    assert store.counts()["event_appearance_links"] == 2
    outcome, preserved = replay(store, event, args)
    assert outcome == {"created": False}
    assert preserved
    store.close()


def test_r7_02_state_semantic_conflict_zero_write_kept() -> None:
    """既有控制(基线亦绿,R7 复审明示保持):合成库改产物语义行
    CN(states 表),再显式重给有效 payload ⇒ 语义冲突零写入拒绝
    (不为改错误类型返工;states 表损坏路径与 appearance 路径分轴)。"""
    store, sub, prod, hyp, event, args = fixture("r7_02_semantic")
    for s in args["states"]:
        store.put_state(s)
    saved = json.loads(store.conn.execute(
        "SELECT payload FROM states WHERE state_id=?",
        (prod.state_id,)).fetchone()[0])
    saved["cn_identity"] = "CCN"
    store.conn.execute(
        "UPDATE states SET payload=? WHERE state_id=?",
        (json.dumps(saved), prod.state_id))
    store.conn.commit()
    before = store.counts()
    with pytest.raises(Exception) as ei:  # noqa: BLE001 (Ppv1EventConflict)
        store.submit_event(event, **dict(args, states=[prod.to_dict()]))
    assert type(ei.value).__name__ == "Ppv1EventConflict"
    assert ei.value.detail["kind"] == "state_semantic_conflict"
    assert store.counts() == before  # 零写入
    store.close()
