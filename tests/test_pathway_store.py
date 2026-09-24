"""PathwayStore — 幂等提交、同键冲突、单事务、汇合共享 Compound、深度。"""

from __future__ import annotations

import pytest

from pathway_v43.domain.identity import cn_identity
from pathway_v43.domain.models import (
    PATH_STATUS_DEFERRED,
    PATH_STATUS_EXPANDED,
    PATH_STATUS_FRONTIER,
)
from pathway_v43.storage.pathway_store import EventConflict, PathwayStore

from wf_helpers import evidence

S = cn_identity("Oc1ccccc1O")
P1 = cn_identity("O=CCC=CO")
P2 = cn_identity("CC(O)=O")
Q = cn_identity("O=CCO")


def _store(tmp_path):
    return PathwayStore(tmp_path / "pathway.sqlite")


def test_ensure_run_root_idempotent(tmp_path):
    st = _store(tmp_path)
    rid1 = st.ensure_run("r1", "Oc1ccccc1O", S)
    rid2 = st.ensure_run("r1", "Oc1ccccc1O", S)
    assert rid1 == rid2
    assert st.get_path(rid1).status == PATH_STATUS_FRONTIER
    assert st.get_path(rid1).depth == 0
    assert st.counts()["path_instances"] == 1


def _submit(st, run_id, parent, substrate, ev, products, expandable, deferred):
    return st.submit_event(
        run_id=run_id, parent_path_id=parent, substrate_identity=substrate,
        evidence=ev, products=products, expandable_path_ids=expandable,
        deferred_path_ids=deferred,
    )


def test_submit_event_idempotent_and_transactional(tmp_path):
    st = _store(tmp_path)
    root = st.ensure_run("r1", "Oc1ccccc1O", S)
    ev = evidence("bt0001#r0001", "recorded_reaction", S, ["O=CCC=CO", "CC(O)=O"])
    products = ev["products"]
    from pathway_v43.storage.pathway_store import event_id_for, product_path_id

    eid = event_id_for("r1", root, S, ev["evidence_id"])
    pids = [product_path_id("r1", eid, i) for i in range(2)]
    r1 = _submit(st, "r1", root, S, ev, products, pids, [])
    assert r1["created"] is True
    # 同键同内容重放:返回已提交结果,不再入账
    r2 = _submit(st, "r1", root, S, ev, products, pids, [])
    assert r2["created"] is False and r2["event_id"] == r1["event_id"]
    assert st.counts()["reaction_events"] == 1
    assert st.counts()["event_products"] == 2
    assert st.counts()["path_instances"] == 3
    # 有序产物:position 顺序保持
    prods = st.event_products(eid)
    assert [p["position"] for p in prods] == [0, 1]
    assert prods[0]["product_identity"] == P1
    assert prods[1]["product_identity"] == P2
    # 父路径已展开,产物路径 frontier,graph_revision 推进
    assert st.get_path(root).status == PATH_STATUS_EXPANDED
    assert st.get_path(pids[0]).status == PATH_STATUS_FRONTIER
    assert st.counts()["graph_revision"] == 1


def test_same_key_different_evidence_conflicts(tmp_path):
    st = _store(tmp_path)
    root = st.ensure_run("r1", "Oc1ccccc1O", S)
    ev = evidence("bt0001#r0001", "recorded_reaction", S, ["CC(O)=O"])
    r1 = _submit(st, "r1", root, S, ev, ev["products"], [], [])
    assert r1["created"] is True
    # 同幂等键、不同证据内容 → 冲突,不静默覆盖
    ev2 = evidence("bt0001#r0001", "recorded_reaction", S, ["CC=O"])
    with pytest.raises(EventConflict):
        _submit(st, "r1", root, S, ev2, ev2["products"], [], [])


def test_junction_two_paths_share_one_compound(tmp_path):
    """同一分子经两条路线到达:两个 PathInstance、一个 Compound、各自父链。"""
    st = _store(tmp_path)
    root = st.ensure_run("r1", "Oc1ccccc1O", S)
    evA = evidence("bt0001#r0001", "recorded_reaction", S, ["O=CCC=CO"])
    evB = evidence("bt0002#r0002", "recorded_reaction", S, ["CC(O)=O"])
    from pathway_v43.storage.pathway_store import event_id_for, product_path_id

    def one_event(ev, prod_cn):
        eid = event_id_for("r1", root, S, ev["evidence_id"])
        pid = product_path_id("r1", eid, 0)
        r = _submit(st, "r1", root, S, ev, ev["products"], [pid], [])
        return r, pid

    rA, pidA = one_event(evA, P1)
    rB, pidB = one_event(evB, P2)
    # A、B 各自再走到同一分子 Q(两条路线汇合)
    evQ1 = evidence("bt0003#r0003", "recorded_reaction", P1, ["O=CCO"])
    evQ2 = evidence("bt0004#r0004", "recorded_reaction", P2, ["O=CCO"])
    for parent, ev in ((pidA, evQ1), (pidB, evQ2)):
        eid = event_id_for("r1", parent, cn_identity(ev["reactant_smiles"]),
                           ev["evidence_id"])
        _submit(st, "r1", parent, ev["reactant_identity"], ev, ev["products"],
                [product_path_id("r1", eid, 0)], [])
    st.refresh_depths("r1")
    # Q 是一个 Compound、两个 PathInstance(不同父路径)
    compounds = st.conn.execute("SELECT cn FROM compounds").fetchall()
    assert len(compounds) == 4  # S, P1, P2, Q
    q_paths = [p for p in st.list_paths("r1")
               if p["substrate_identity"] == Q]
    assert len(q_paths) == 2
    assert {p["parent_path_id"] for p in q_paths} == {pidA, pidB}
    assert {p["depth"] for p in q_paths} == {2}


def test_set_path_status_unknown_path(tmp_path):
    st = _store(tmp_path)
    with pytest.raises(KeyError):
        st.set_path_status("p_nonexistent", PATH_STATUS_DEFERRED)
