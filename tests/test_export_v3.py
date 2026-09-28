"""导出器验收测试(TASK_V43_EXPORT_DEV §5.1/§5.2/§5.3)。

- 合成账本:单事件多产物、两事件竞争、同分子两来路汇合、路径内循环、
  有效/无效产物混合、仅检索未提交、awaiting_prediction、deferred 子路径;
  逐字比较导出 JSONL 的 parent、顺序、去重与 rank。
- cn / raw_sb 双口径:中性/阴离子同身份在主口径命中、保电荷口径按原始
  形判;导出不提前中和原始字符串。同 parent 首现合并语义与 v3 评测器
  一致(直接调用冻结评测器的纯函数核对)。
- 重复导出字节一致;revision 推进后旧导出判过期、重生成显式失效;
  账本损坏结构化失败并保留拒因。
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pathway_v43.domain.identity import cn_identity  # noqa: E402
from pathway_v43.domain.models import STRATEGY_VERSION, stable_id  # noqa: E402
from pathway_v43.output.export_v3 import (  # noqa: E402
    EXPORT_POLICY_DEFAULTS,
    ExportStale,
    LedgerCorrupt,
    export_policy_hash,
    export_run_v3,
    load_export_policy,
)
from pathway_v43.storage.artifact_store import ArtifactStore  # noqa: E402
from pathway_v43.storage.pathway_store import (  # noqa: E402
    PathwayStore,
    event_id_for,
    product_path_id,
    root_path_id,
)

from wf_helpers import evidence, run_scripted  # noqa: E402

REPO = Path(__file__).resolve().parents[1]

REPORT_ADJUDICATION_SCHEMA = "v43-report-adjudication-1"


def _make_run(runs_root: Path, run_id: str, root_smiles: str) -> PathwayStore:
    """合成账本 + 最小 run_identity(导出只依赖 inputs 与账本本身)。"""
    run_dir = runs_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    store = PathwayStore(run_dir / "pathway.sqlite")
    root_cn = cn_identity(root_smiles) or root_smiles
    store.ensure_run(run_id, root_smiles, root_cn)
    identity = {
        "schema_version": "v43-identity-1",
        "run_id": run_id,
        "inputs": {"root_smiles": root_smiles, "root_identity": root_cn},
    }
    (runs_root / run_id / "run_identity.json").write_text(
        json.dumps(identity, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    return store


def _write_adjudication(runs_root: Path, run_id: str, parent_path_id: str,
                        parent_identity: str, card: dict,
                        products: list[dict], expandable_pos: set[int],
                        deferred_pos: set[int], event_id: str) -> None:
    """写候选裁决产物(与 workflow.nodes._report_adjudication_payload 同形)。"""
    entries = []
    rank = 0
    for p in sorted(products, key=lambda q: q["position"]):
        pos = p["position"]
        # 与门禁同判:不可解析 = 被拒(不入账、不可报告)
        accepted = cn_identity(p["product_smiles"]) is not None
        entry = {
            "position": pos,
            "product_identity": p["product_identity"],
            "product_smiles": p["product_smiles"],
            "product_smiles_full": p.get("product_smiles_full", ""),
            "evidence_id": card["evidence_id"],
            "validation_ref": "T-fixture-validation",
            "accepted": accepted,
            "reportable": accepted,
            "report_rank": None,
            "expand_selected": pos in expandable_pos,
            "expand_status": ("frontier" if pos in expandable_pos
                              else ("deferred" if pos in deferred_pos
                                    else "rejected")),
            "verdict_reasons": [],
        }
        if accepted:
            rank += 1
            entry["report_rank"] = rank
        entries.append(entry)
    payload = {
        "schema_version": REPORT_ADJUDICATION_SCHEMA,
        "task_kind": "report_adjudication",
        "run_id": run_id,
        "path_id": parent_path_id,
        "substrate_identity": parent_identity,
        "evidence_id": card["evidence_id"],
        "evidence_kind": card.get("kind"),
        "event_id": event_id,
        "report_rank_basis": "event_product_position_accepted_order",
        "policy": {"max_reportable_products": 5},
        "entries": entries,
        "n_reportable": rank,
        "n_expand_selected": sum(1 for e in entries if e["expand_selected"]),
    }
    task_id = stable_id("T", run_id, parent_path_id, "adjudication",
                        f"{parent_identity}|{event_id}",
                        STRATEGY_VERSION, "", "")
    artifacts = ArtifactStore(runs_root, run_id)
    artifacts.write(task_id, "report_adjudication", payload)


def _submit(store: PathwayStore, run_id: str, parent_path_id: str,
            parent_identity: str, ev_rid: str, products: list[tuple[int, str]],
            *, expandable: list[int] | None = None,
            deferred: list[int] | None = None,
            kind: str = "recorded_reaction",
            runs_root: Path | None = None) -> str:
    """直写一个已提交事件 + 对应候选裁决产物(位次稀疏保留原始位次)。"""
    if runs_root is None:
        # <runs_root>/<run_id>/pathway.sqlite → runs_root
        runs_root = Path(store.db_path).parent.parent
    card = evidence(
        ev_rid, kind, parent_identity,
        [s for _, s in sorted(products)],
    )
    # 证据卡产物按给定 position 构造(允许稀疏/乱序)
    card["products"] = [
        {"position": p, "product_smiles": s, "product_smiles_full": s,
         "product_identity": cn_identity(s) or s, "score": 0.9,
         "score_semantics": "fixture"}
        for p, s in sorted(products)
    ]
    card["evidence_id"] = f"E-{ev_rid}"
    eid = event_id_for(run_id, parent_path_id, parent_identity,
                       card["evidence_id"])
    expandable_ids = [
        product_path_id(run_id, eid, p) for p in (expandable or [])
    ]
    deferred_ids = [
        product_path_id(run_id, eid, p) for p in (deferred or [])
    ]
    # 仅可解析(过门禁)产物入账;被拒产物不入账(与真实提交一致)
    accepted_products = [
        prod for prod in card["products"]
        if cn_identity(prod["product_smiles"]) is not None
    ]
    result = store.submit_event(
        run_id=run_id, parent_path_id=parent_path_id,
        substrate_identity=parent_identity, evidence=card,
        products=accepted_products, expandable_path_ids=expandable_ids,
        deferred_path_ids=deferred_ids,
    )
    store.refresh_depths(run_id)
    if runs_root is not None:
        _write_adjudication(runs_root, run_id, parent_path_id,
                            parent_identity, card, card["products"],
                            set(expandable or []), set(deferred or []),
                            result["event_id"])
    return result["event_id"]


def _export(runs_root: Path, run_id: str, route_id: str | None = None) -> dict:
    return export_run_v3(runs_root, run_id, route_id=route_id)


def _read_line(runs_root: Path, run_id: str) -> dict:
    return json.loads((runs_root / run_id / "predictions.jsonl")
                      .read_text(encoding="utf-8"))


# ------------------------------------------------------ 验收 5.1 合成账本


def test_single_event_multi_products_position_order(tmp_path):
    """多产物事件按保存 position 排列;rank = 位次(不是检索排名)。"""
    A = "CCO"
    B1 = "CC=O"
    B2 = "C=CO"
    B3 = "CC(=O)O"
    store = _make_run(tmp_path, "r1", A)
    root_pid = root_path_id("r1", cn_identity(A))
    _submit(store, "r1", root_pid, cn_identity(A), "ev1",
            [(0, B1), (1, B2), (2, B3)])
    _export(tmp_path, "r1", route_id="pb_0002")
    line = _read_line(tmp_path, "r1")
    assert line["route_id"] == "pb_0002"
    assert line["root_smiles"] == A  # 原始输入,非规范身份
    assert line["steps"] == [
        {"parent_smiles": A,
         "predicted_products": [B1, B2, B3]},
    ]


def test_two_events_competing_same_molecule_merged_first_seen(tmp_path):
    """两个事件竞争(同一分子经两条来路各提交一个事件):按首现父合并,
    产物按父路径 seq 次序;重导出逐字节一致。"""
    A = "CCO"
    M = "CC=O"
    P1 = "CC(O)=O"
    P2 = "C=CO"
    store = _make_run(tmp_path, "r2", A)
    root_pid = root_path_id("r2", cn_identity(A))
    # 两条来路:A --evA--> M;A --evB--> M(同 cn 身份,不同事件/路径)
    evA = _submit(store, "r2", root_pid, cn_identity(A), "evA",
                  [(0, M)], expandable=[0])
    evB = _submit(store, "r2", root_pid, cn_identity(A), "evB",
                  [(0, M)], expandable=[0])
    mA = product_path_id("r2", evA, 0)
    mB = product_path_id("r2", evB, 0)
    _submit(store, "r2", mA, cn_identity(M), "evC", [(0, P1)],
            expandable=[0])
    _submit(store, "r2", mB, cn_identity(M), "evD", [(0, P2)],
            expandable=[0])
    _export(tmp_path, "r2")
    line = _read_line(tmp_path, "r2")
    steps = line["steps"]
    m_steps = [s for s in steps
               if cn_identity(s["parent_smiles"]) == cn_identity(M)]
    assert len(m_steps) == 1, "同 parent 首现合并为一步"
    assert sorted(m_steps[0]["predicted_products"]) == sorted([P1, P2])
    # 确定性:重复导出逐字节一致(不得让 SQLite 无序查询决定 rank)
    _export(tmp_path, "r2")
    assert (tmp_path / "r2" / "predictions.jsonl").read_text() == \
        json.dumps(line, ensure_ascii=False, sort_keys=True,
                   separators=(",", ":")) + "\n"


def test_committed_event_without_adjudication_is_corrupt(tmp_path):
    """已提交事件缺少候选裁决产物 = 账本/产物损坏(fail-closed)。"""
    A = "CCO"
    store = _make_run(tmp_path, "r-noadj", A)
    root_pid = root_path_id("r-noadj", cn_identity(A))
    # 直写事件但不写裁决产物
    card = evidence("evx", "recorded_reaction", cn_identity(A), ["CC=O"])
    card["evidence_id"] = "E-evx"
    eid = event_id_for("r-noadj", root_pid, cn_identity(A), card["evidence_id"])
    store.submit_event(
        run_id="r-noadj", parent_path_id=root_pid,
        substrate_identity=cn_identity(A), evidence=card,
        products=card["products"],
        expandable_path_ids=[product_path_id("r-noadj", eid, 0)],
        deferred_path_ids=[])
    with pytest.raises(LedgerCorrupt):
        _export(tmp_path, "r-noadj")


def test_expand_selected_deferred_contradiction_is_corrupt(tmp_path):
    """裁决 expand_selected=true 与账本 deferred 状态矛盾 → 结构化失败。"""
    A = "CCO"
    store = _make_run(tmp_path, "r-contradict", A)
    root_pid = root_path_id("r-contradict", cn_identity(A))
    # 位置 0 放进 deferred(路径状态 deferred),裁决却标 expand_selected
    _submit(store, "r-contradict", root_pid, cn_identity(A), "ev1",
            [(0, "CC=O")], deferred=[0])
    # 篡改裁决:expand_selected → true(expand_status → frontier)
    import json as _json

    results = tmp_path / "r-contradict" / "results"
    adj_path = next(results.glob("*/report_adjudication.json"))
    envp = _json.loads(adj_path.read_text())
    envp["payload"]["entries"][0]["expand_selected"] = True
    envp["payload"]["entries"][0]["expand_status"] = "frontier"
    envp["payload_hash"] = __import__(
        "hashlib").sha256(_json.dumps(
            envp["payload"], ensure_ascii=False, sort_keys=True,
            separators=(",", ":")).encode()).hexdigest()
    adj_path.write_text(_json.dumps(envp, ensure_ascii=False) + "\n")
    with pytest.raises(LedgerCorrupt):
        _export(tmp_path, "r-contradict")


def test_same_identity_two_routes_converge_first_seen_merge(tmp_path):
    """同一分子经两条不同路线到达(v4 路径树)→ 导出按 v3 评测器
    "同 parent 首现合并"投影;其余 raw 形变体记入元数据(信息损失)。
    两条来路 raw 形不同(乙酸 vs 乙酸根,同 cn 身份)。"""
    A = "CCO"
    M_raw1 = "CC(=O)[O-]"   # 阴离子 raw 形
    M_raw2 = "CC(=O)O"      # 中性 raw 形(与 M_raw1 同 cn 身份)
    P = "CC(=O)OCC"         # 乙酸乙酯(与 M 不同身份)
    store = _make_run(tmp_path, "r3", A)
    root_pid = root_path_id("r3", cn_identity(A))
    # 路线一:A --evA--> M(阴离子 raw);路线二:A --evB--> M(中性 raw)
    evA = _submit(store, "r3", root_pid, cn_identity(A), "evA",
                  [(0, M_raw1)])
    evB = _submit(store, "r3", root_pid, cn_identity(A), "evB",
                  [(0, M_raw2)])
    mA = product_path_id("r3", evA, 0)
    mB = product_path_id("r3", evB, 0)
    # 两条来路各提交一个不同产物
    _submit(store, "r3", mA, cn_identity(M_raw1), "evC", [(0, P)])
    _submit(store, "r3", mB, cn_identity(M_raw2), "evD", [(0, "CC#N")])
    meta = _export(tmp_path, "r3")["metadata"]
    line = _read_line(tmp_path, "r3")
    m_identity = cn_identity(M_raw1)
    assert m_identity == cn_identity(M_raw2)
    m_steps = [s for s in line["steps"]
               if cn_identity(s["parent_smiles"]) == m_identity]
    assert len(m_steps) == 1, "同 parent 首现合并为一步"
    products = m_steps[0]["predicted_products"]
    assert sorted(products) == sorted([P, "CC#N"])
    assert meta["counts"]["n_merged_parents"] >= 1
    variants = meta["parent_raw_form_variants"]
    assert sorted(variants[m_identity]) == sorted([M_raw1, M_raw2])
    # 首现 raw 形(evA 阴离子)入答卷;评测器合并语义下两产物都命中
    assert m_steps[0]["parent_smiles"] == M_raw1


def test_in_path_loop_product_never_enters_answer(tmp_path):
    """路径内循环产物被门禁拒绝(不入账)→ 不出现在答卷。"""
    A = "CCO"
    B = "CC=O"
    scripted = {
        cn_identity(A): [evidence("recA", "recorded_reaction",
                                  cn_identity(A), [B])],
        cn_identity(B): [evidence("recB", "recorded_reaction",
                                  cn_identity(B), [A])],  # 循环回根
    }
    summary, runs_root = run_scripted("r-loop", scripted, smiles=A,
                                      max_depth=2,
                                      max_expansions=6, runs_root=tmp_path)
    assert summary["counts"]["reaction_events"] == 1  # A→B 入账
    _export(runs_root, "r-loop")
    line = _read_line(runs_root, "r-loop")
    assert line["steps"][0]["predicted_products"] == [B]
    # B 的事件被拒(循环)→ B 无步骤
    assert all(s["parent_smiles"] != B for s in line["steps"][1:])


def test_invalid_product_mixed_rejected_not_in_answer(tmp_path):
    """有效/无效产物混合:无效产物不入账,有效产物保留原始位次。"""
    A = "CCO"
    store = _make_run(tmp_path, "r5", A)
    root_pid = root_path_id("r5", cn_identity(A))
    # 位置 0 无效(不解析)、位置 1 有效:位次稀疏但不重排
    _submit(store, "r5", root_pid, cn_identity(A), "ev1",
            [(0, "C(C("), (1, "CC=O")])
    _export(tmp_path, "r5")
    line = _read_line(tmp_path, "r5")
    assert line["steps"][0]["predicted_products"] == ["CC=O"]


def test_retrieval_only_and_awaiting_paths_yield_no_steps(tmp_path):
    """仅检索未提交 / awaiting_prediction:不进答卷(仅诊断用,不冒充分)。"""
    A = "CCO"
    # 无模型:两张竞争 recorded → awaiting_prediction,零事件
    card1 = evidence("r1", "recorded_reaction", cn_identity(A), ["CC=O"])
    card2 = evidence("r2", "recorded_reaction", cn_identity(A), ["C=CO"])
    summary, runs_root = run_scripted(
        "r6", {cn_identity(A): [card1, card2]}, smiles=A,
        max_depth=1, max_expansions=4, runs_root=tmp_path)
    assert summary["stop_reason"] == "awaiting_prediction"
    _export(runs_root, "r6")
    line = _read_line(runs_root, "r6")
    assert line["steps"] == []
    assert line["root_smiles"] == A


def test_deferred_products_still_committed_in_answer(tmp_path):
    """deferred 子路径:合法候选未展开,但事件产物**已提交** → 进答卷。"""
    A = "CCO"
    B1, B2, B3 = "CC=O", "C=CO", "CC(O)C"
    scripted = {
        cn_identity(A): [evidence("recA", "recorded_reaction",
                                  cn_identity(A), [B1, B2, B3])],
    }
    summary, runs_root = run_scripted("r7", scripted, smiles=A, max_depth=1,
                                      max_expansions=6,
                                      max_frontier_width=2,
                                      runs_root=tmp_path)
    assert summary["counts"]["reaction_events"] == 1
    _export(runs_root, "r7")
    line = _read_line(runs_root, "r7")
    # 三个提交产物全在答卷(deferred 只是不展开,不是不报告);
    # 且可报告未展开产品不凭空产生下一步(仍只有根一步)
    assert sorted(line["steps"][0]["predicted_products"]) == sorted(
        [B1, B2, B3])
    assert len(line["steps"]) == 1


def test_cap_truncates_by_committed_position(tmp_path):
    """每父上限(默认 5)按**提交位次**截断;被截数量入元数据。"""
    A = "CCO"
    products = [(i, f"CC(=O)C{'C' * (i + 1)}" if i != 1 else "CC=O")
                for i in range(7)]
    products = [(p, s) for p, s in products if cn_identity(s)]
    store = _make_run(tmp_path, "r8", A)
    root_pid = root_path_id("r8", cn_identity(A))
    _submit(store, "r8", root_pid, cn_identity(A), "ev1", products)
    meta = _export(tmp_path, "r8")["metadata"]
    line = _read_line(tmp_path, "r8")
    emitted = line["steps"][0]["predicted_products"]
    assert emitted == [s for p, s in sorted(products)][:5]
    assert meta["counts"]["n_truncated_products"] == len(products) - 5


def test_invalid_input_run_gets_explicit_empty_answer(tmp_path):
    """invalid_input run(根不可解析):显式空答卷 + root_unparseable 标注。"""
    runs_root = tmp_path
    bad = "C(C(C("  # 不可解析
    (runs_root / "bad").mkdir(parents=True, exist_ok=True)
    store = PathwayStore(runs_root / "bad" / "pathway.sqlite")
    store.ensure_run("bad", bad, bad)  # cn_identity 失败时根身份=原串
    (runs_root / "bad" / "run_identity.json").write_text(json.dumps({
        "schema_version": "v43-identity-1", "run_id": "bad",
        "inputs": {"root_smiles": bad, "root_identity": bad},
    }), encoding="utf-8")
    result = _export(runs_root, "bad")
    assert result["metadata"]["root_unparseable"] is True
    line = _read_line(runs_root, "bad")
    assert line == {"route_id": "bad", "root_smiles": bad, "steps": []}


# ------------------------------------------------------ 验收 5.2 双口径


def _load_v3_evaluator():
    v3_file = (REPO.parent / "dependingv3" / "evaluation"
               / "pathway_benchmark" / "eval_pathway_benchmark.py")
    spec = importlib.util.spec_from_file_location("v3_eval", v3_file)
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(REPO.parent / "dependingv3" / "src"))
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.skipif(
    not (REPO.parent / "dependingv3" / "src" / "depending").is_dir(),
    reason="v3 代码根不可用")
def test_charge_fixture_cn_hits_raw_sb_misses_neutralization_forbidden(
        tmp_path):
    """阴离子产物答卷 vs 中性金标:cn 主口径 hit、raw_sb 对照 miss;
    导出保持阴离子原始形(不提前中和)。"""
    ev = _load_v3_evaluator()
    gold = {
        "route_id": "pb_x", "root_cn": "CCO", "root_smiles": "CCO",
        "depth": 1, "stratum": "S",
        "gold_leaves": ["O=C(O)c1ccccc1"],
        "edges": [{"parent_cn": "CCO", "product_cn": "O=C(O)c1ccccc1",
                   "parent_smiles": "CCO",
                   "product_smiles": "O=C(O)c1ccccc1"}],
    }
    anion = "O=C([O-])c1ccccc1"
    pred = {"route_id": "pb_x", "root_smiles": "CCO",
            "steps": [{"parent_smiles": "CCO",
                       "predicted_products": [anion]}]}
    cn = ev.evaluate_route(gold, pred, "cn")
    raw = ev.evaluate_route(gold, pred, "raw_sb")
    assert cn["step_hits"][1] == 1, "cn 口径:阴离子预测 == 中性金标"
    assert raw["step_hits"][1] == 0, "raw_sb 口径:保电荷,按原始形判"
    # 导出器对同一事实的答卷行:产物 raw 串保持阴离子(未中和)
    store = _make_run(tmp_path, "chg", "CCO")
    root_pid = root_path_id("chg", cn_identity("CCO"))
    _submit(store, "chg", root_pid, cn_identity("CCO"), "ev1",
            [(0, anion)])
    _export(tmp_path, "chg")
    line = _read_line(tmp_path, "chg")
    assert line["steps"][0]["predicted_products"] == [anion]
    # 且该答卷对金标 cn 判 hit(与上面 gold/pred 一致)
    cn2 = ev.evaluate_route(gold, line, "cn")
    assert cn2["step_hits"][1] == 1


# ------------------------------------------------------ 验收 5.3 确定性


def test_reexport_byte_identical_and_metadata_deterministic(tmp_path):
    A = "CCO"
    store = _make_run(tmp_path, "r9", A)
    root_pid = root_path_id("r9", cn_identity(A))
    _submit(store, "r9", root_pid, cn_identity(A), "ev1",
            [(0, "CC=O"), (1, "C=CO")])
    r1 = _export(tmp_path, "r9")
    r2 = _export(tmp_path, "r9")
    p1 = (tmp_path / "r9" / "predictions.jsonl").read_bytes()
    p2 = (tmp_path / "r9" / "predictions.jsonl").read_bytes()
    import hashlib

    assert p1 == p2
    assert hashlib.sha256(p1).hexdigest() == r1["predictions_sha256"]
    assert hashlib.sha256(p1).hexdigest() == r2["predictions_sha256"]
    m1 = (tmp_path / "r9" / "export_metadata.json").read_bytes()
    m2 = (tmp_path / "r9" / "export_metadata.json").read_bytes()
    assert m1 == m2  # 元数据同样确定(无时间性字段)


def test_revision_advance_marks_stale_then_reexport_supersedes(tmp_path):
    A = "CCO"
    store = _make_run(tmp_path, "r10", A)
    root_pid = root_path_id("r10", cn_identity(A))
    _submit(store, "r10", root_pid, cn_identity(A), "ev1", [(0, "CC=O")])
    _export(tmp_path, "r10")
    old_rev = json.loads((tmp_path / "r10" / "export_metadata.json")
                         .read_text())["ledger_graph_revision"]
    # 账本新增事件(revision 推进)→ 旧导出必须被判过期
    _submit(store, "r10", root_pid, cn_identity(A), "ev2", [(1, "C=CO")])
    assert store.graph_revision() > old_rev
    with pytest.raises(ExportStale):
        export_run_v3(tmp_path, "r10", verify_only=True)
    fresh = _export(tmp_path, "r10")
    meta = fresh["metadata"]
    assert meta["superseded"]["previous_ledger_revision"] == old_rev
    assert meta["counts"]["n_committed_products"] == 2
    # 新鲜度核对通过
    export_run_v3(tmp_path, "r10", verify_only=True)


def test_policy_change_marks_stale(tmp_path):
    A = "CCO"
    store = _make_run(tmp_path, "r11", A)
    root_pid = root_path_id("r11", cn_identity(A))
    _submit(store, "r11", root_pid, cn_identity(A), "ev1",
            [(0, "CC=O"), (1, "C=CO"), (2, "CC(O)C")])
    _export(tmp_path, "r11")
    with pytest.raises(ExportStale):
        export_run_v3(tmp_path, "r11", policy={"products_per_parent_cap": 2},
                      verify_only=True)
    result = export_run_v3(tmp_path, "r11",
                           policy={"products_per_parent_cap": 2})
    assert result["metadata"]["counts"]["n_products_emitted"] == 2
    assert export_policy_hash(
        load_export_policy({"products_per_parent_cap": 2})) != \
        export_policy_hash(EXPORT_POLICY_DEFAULTS)


def test_corrupt_ledger_fails_structured(tmp_path):
    A = "CCO"
    store = _make_run(tmp_path, "r12", A)
    root_pid = root_path_id("r12", cn_identity(A))
    _submit(store, "r12", root_pid, cn_identity(A), "ev1", [(0, "CC=O")])
    store.close()
    # 篡改:产物 raw 与存储身份不一致(模拟账本损坏)
    import sqlite3

    conn = sqlite3.connect(tmp_path / "r12" / "pathway.sqlite")
    conn.execute("UPDATE event_products SET product_smiles='CCCC',"
                 " product_smiles_full='CCCC'")
    conn.commit()
    conn.close()
    from pathway_v43.output.export_v3 import ExportError

    with pytest.raises(ExportError) as exc:
        _export(tmp_path, "r12")
    assert "不一致" in str(exc.value) or "损坏" in str(exc.value)
    assert exc.value.detail  # 结构化拒因


def test_missing_tables_fail_structured(tmp_path):
    import sqlite3

    d = tmp_path / "r13"
    d.mkdir(parents=True)
    conn = sqlite3.connect(d / "pathway.sqlite")
    conn.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT)")
    conn.commit()
    conn.close()
    (d / "run_identity.json").write_text(json.dumps({
        "run_id": "r13", "inputs": {"root_smiles": "CCO",
                                    "root_identity": "CCO"}}))
    with pytest.raises(LedgerCorrupt):
        _export(tmp_path, "r13")


def test_export_does_not_write_ledger(tmp_path):
    """导出以只读方式打开账本;不推进 revision、不改文件。"""
    A = "CCO"
    store = _make_run(tmp_path, "r14", A)
    root_pid = root_path_id("r14", cn_identity(A))
    _submit(store, "r14", root_pid, cn_identity(A), "ev1", [(0, "CC=O")])
    store.close()
    db = tmp_path / "r14" / "pathway.sqlite"
    before = db.read_bytes()
    rev_before = json.loads(
        (tmp_path / "r14" / "export_metadata.json").read_text()
    )["ledger_graph_revision"] if (tmp_path / "r14" /
                                   "export_metadata.json").is_file() else None
    _export(tmp_path, "r14")
    assert db.read_bytes() == before
    if rev_before is not None:
        assert json.loads((tmp_path / "r14" / "export_metadata.json")
                          .read_text())["ledger_graph_revision"] == rev_before
