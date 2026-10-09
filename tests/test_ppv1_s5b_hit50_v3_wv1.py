"""PPV1 S5b HIT50 v3 W-V1 —— 提交序贯彻调度序(s5b-submit-order-1)。

依据:v3 任务书 W-V1 + v2 尸检 §2.1(W-V0 独立复现已闭合:295/298
提交序=哈希序、反事实 hit@1 29→73)。修复 = enqueue 装配本 run 严格
单调递增微秒 created_at(方案 A),取任务序 ``ORDER BY created_at,
action_id`` 与原 scorer ``(created_at, event_id)`` 判据**一字不动**。

正负控(任务书 W-V1.3):
- 正控①:8 池 + 首位 novel,budget8 下 novel 首提交且**原 scorer 得
  rank1**(穿 store→native_export→原 score 主口径行);
- 正控②:首位 recorded 池候选首提交(对齐 47 题反例形态的合成版:
  模型显式首位的 recorded 候选不被 novel 哈希洗到后面);
- 负控:调度序≠提交序的旧形态(哈希 tie-break)在同一断言下必须
  红——用 v2 形态的合成重排(按 action_id 哈希序)验证检测器敏感;
  父基线(35727eb)红绿对照由主会话/交付书记录(新测试在父 HEAD
  应红)。

本文件零网络、零真实模型(scripted 桩);合成分子与真实 298 金标零
重叠(乙醇级小分子)。
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pathway_v43.config import resolve_config  # noqa: E402
from pathway_v43.pollutant.production import (  # noqa: E402
    prepare_hypothesis,
)
from pathway_v43.pollutant.real_model import (  # noqa: E402
    ScriptedRealModelAdapter,
)
from pathway_v43.pollutant.recorded_source import (  # noqa: E402
    compile_recorded_reaction,
    reset_library_cache,
)
from pathway_v43.pollutant.runflow import (  # noqa: E402
    start_ppv1_run,
)
from pathway_v43.pollutant.s5b_compiler import (  # noqa: E402
    compile_donor_template,
)

from test_ppv1_s5a_schema import (  # noqa: E402
    synth_evaluation_input,
    synth_reference_graph,
)

QID = "RXNG-SYNTH-WV1"

_PROFILE = {
    "search_limits": {
        "max_alternative_hypotheses_per_parent": 8,
        "max_attempts_per_hypothesis": 1,
        "max_product_expansion_width": 2,
        "max_search_depth": 1,
        "max_total_search_actions": 64,
        "max_scenario_transitions": 0,
        "max_reopens_per_hypothesis": 0,
        "max_real_model_requests": 4,
        "max_retrievals_per_parent": 1,
        "max_retrievals_total": 8,
    },
    "format_feedback_policy": {"max_format_feedback_rounds": 0},
}

# 8 个不同净反应的池条目(除 aldehyde 外各产物互异且不匹配金标
# CC=O;compiled 由共同编译器产出 —— 全部经公共链执行)
_POOL_PRODUCTS = [
    ("acid", "[CH3:1][C:2](=[O:4])[OH:3]", [2]),
    ("ether", "[CH3:1][CH2:2][O:3][CH3:4]", [3]),
    ("peroxide", "[CH3:1][CH2:2][O:3][OH:4]", [3]),
    ("propane", "[CH3:1][CH2:2][CH3:4]", [2]),
    ("glycol", "[OH:4][CH2:1][CH2:2][OH:3]", [2]),
    ("propanol", "[CH3:1][CH2:2][CH2:4][OH:3]", [2]),
    ("amine", "[CH3:1][CH2:2][NH2:4]", [2]),
    ("thiol", "[CH3:1][CH2:2][SH:4]", [2]),
]
_LHS = "[CH3:1][CH2:2][OH:3]"


def _compiled_pool() -> list[dict]:
    out = []
    for name, rhs, center in _POOL_PRODUCTS:
        compiled = compile_donor_template(
            mapped_lhs=_LHS, mapped_rhs=rhs, center_atoms=center,
            substrate_smiles="CCO", record_id=f"wv1-{name}")
        assert compiled["status"] == "compiled", compiled
        spec = dict(compiled["spec"])
        spec["key"] = f"pool-{name}"
        out.append(spec)
    return out


def _novel_spec(product: str = "CC=O", coproducts: list[str] | None = None,
                key: str = "novel-1") -> dict:
    """novel 池外提案的 reaction_spec(经共同 prevalidation/构建源)。

    product=CC=O:乙醇氧化(change_bond_order;coproducts 可带 [H][H]
    严中 e-alt-1);product=CCOO:加氧(add_atom,对齐 W3 测试 novel)。
    """
    if product == "CC=O":
        spec = {
            "product_smiles": product,
            "edits": [{
                "op": "change_bond_order", "atom1": "S_C_2",
                "atom2": "S_O_1", "from_order": "single",
                "to_order": "double"}],
            "donor": {"center_atom_ids": ["S_C_2", "S_O_1"]},
            "alignment": {
                "status": "resolved",
                "donor_to_current": {"S_C_2": "S_C_2", "S_O_1": "S_O_1"},
                "ref": "self"},
            "expectation": {"target_smiles": product},
        }
    elif product == "CCOO":
        spec = {
            "product_smiles": product,
            "edits": [{
                "op": "add_atom", "element": "O", "new_atom_id": "SN_O_1",
                "atom1": "S_O_1"}],
            "donor": {"center_atom_ids": ["S_O_1", "SN_O_1"]},
            "alignment": {
                "status": "resolved",
                "donor_to_current": {"S_O_1": "S_O_1", "SN_O_1": "SN_O_1"},
                "ref": "self"},
            "expectation": {"target_smiles": product},
        }
    else:
        raise ValueError(f"novel 产物形状未定义:{product}")
    if coproducts:
        spec["coproducts"] = list(coproducts)
    return {"hypothesis_id": key,
            "proposal_context": {"reference_hypothesis_ids": [],
                                 "output_origin": "novel_outside_pool"},
            "reaction_spec": spec}


def _model_response(pool_hyp_ids: list[str], novel_key: str,
                    ranked_first: list[str]) -> str:
    """scripted proposals 响应:rank_hypotheses 首位 = ranked_first[0]。

    ranked_first = 模型显式位次(novel 与/或池条目的 prepared
    hypothesis_id);池条目不经 proposals 重复提案(池在 plan.pools)。
    """
    proposals = [_novel_spec()]
    return json.dumps({
        "proposals": proposals,
        "rank_hypotheses": list(ranked_first)})


def _run(tmp_path: Path, run_id: str, plan: dict, model) -> dict:
    return start_ppv1_run(
        config=resolve_config(), runs_root=tmp_path / "runs",
        run_id=run_id, smiles="CCO", plan=plan, model=model,
        profile_policy=dict(
            _PROFILE, search_limits=dict(
                _PROFILE["search_limits"], max_real_model_requests=4)))


def _extract_order(runs_root: Path, run_id: str) -> dict:
    """读回 run 账本:expand action 次序 + 事件提交次序(只读)。

    返回 {action_order: [(created_at, action_id, eff_rank, lpid)],
          event_order: [(created_at, event_id, lpid, hyp)],
          payload_by_hyp: {hyp: payload}}。
    """
    conn = sqlite3.connect(
        str(runs_root / run_id / "pollutant.sqlite"))
    conn.row_factory = sqlite3.Row
    payload_by_hyp: dict[str, dict] = {}
    action_rows = []
    for r in conn.execute(
            "SELECT action_id, created_at, payload FROM search_actions"
            " WHERE action_kind='expand_hypothesis'"):
        pl = json.loads(r["payload"] or "{}")
        hyp = str(pl.get("prepared_hypothesis_id") or "")
        payload_by_hyp[hyp] = pl
        action_rows.append({
            "action_id": str(r["action_id"]),
            "created_at": str(r["created_at"]),
            "eff_rank": pl.get("effective_rank"),
            "lpid": str(pl.get("logical_proposal_id") or "")})
    conn.close()
    action_order = sorted(
        action_rows, key=lambda a: (a["created_at"], a["action_id"]))
    conn = sqlite3.connect(
        str(runs_root / run_id / "pollutant.sqlite"))
    conn.row_factory = sqlite3.Row
    events = []
    for r in conn.execute(
            "SELECT event_id, hypothesis_id, created_at FROM events"):
        events.append({
            "event_id": str(r["event_id"]),
            "hyp": str(r["hypothesis_id"] or ""),
            "created_at": str(r["created_at"] or "")})
    conn.close()
    events.sort(key=lambda e: (e["created_at"], e["event_id"]))
    event_order = [{
        **e,
        "lpid": payload_by_hyp.get(e["hyp"], {}).get(
            "logical_proposal_id", ""),
        "eff_rank": payload_by_hyp.get(e["hyp"], {}).get(
            "effective_rank")} for e in events]
    return {"action_order": action_order, "event_order": event_order,
            "payload_by_hyp": payload_by_hyp}


def _submission_follows_rank(event_order: list[dict]) -> bool:
    """检测器:事件提交序((created_at, event_id) 升序)= 调度序
    (effective_rank 升序)。正控须 True;v2 哈希形态须 False。"""
    ranks = [e["eff_rank"] for e in event_order]
    return all(
        ranks[i] is not None and ranks[i + 1] is not None
        and ranks[i] < ranks[i + 1]
        for i in range(len(ranks) - 1)) and bool(ranks)


def _qid_graph(graph_id: str, *, edges_first: str) -> dict:
    """合成参考图(root CCO→CC=O;edges_first 指定首边——主口径行取
    edge_matches[0],首边即判分边)。qid 声明入 root source_refs。"""
    graph = synth_reference_graph(graph_id)
    edges = {e["edge_id"]: e for e in graph["edges"]}
    first = edges.pop(edges_first)
    graph["edges"] = [first] + list(edges.values())
    refs = list(graph["root_entity"]["source_refs"])
    if QID not in refs:
        refs.insert(0, QID)
    graph["root_entity"]["source_refs"] = refs
    return graph


def _score_main_row(tmp_path: Path, run_id: str, digest: str,
                    graph: dict) -> tuple[dict, dict]:
    """原 score 主口径行(s5b_scoring._main_caliber_row:判据零改动的
    同一实现;候选序 = (created_at, event_id) 升序)。穿
    evaluate_scientific(含 qid_strict 配对)→ 主口径行。"""
    from pathway_v43.pollutant import preregistration
    from pathway_v43.pollutant.evaluation import (
        evaluate_scientific,
        native_export_reader_from_ledger,
    )
    from pathway_v43.pollutant.native_export import read_native_export
    from pathway_v43.pollutant.s5b_scoring import _main_caliber_row
    from pathway_v43.pollutant.search import SearchLedger
    from pathway_v43.pollutant.store import PollutantPathwayStore
    from pathway_v43.storage.artifact_store import ArtifactStore

    runs_root = tmp_path / "runs"
    store = PollutantPathwayStore(
        runs_root / run_id / "pollutant.sqlite")
    ledger = SearchLedger(
        store, ArtifactStore(runs_root, run_id), run_id)
    reader = native_export_reader_from_ledger(ledger, runs_root / run_id)
    payload = read_native_export(
        ledger, runs_root / run_id, digest)["payload"]
    exports = [{"run_id": run_id, "export_digest": digest, "qid": QID}]
    evaluation_input = synth_evaluation_input(
        graphs=[graph], exports=exports)
    entry = evaluation_input["reference_graph_manifest"][0]
    entry["qid"] = QID
    output = evaluate_scientific(
        evaluation_input, reference_graphs={
            graph["reference_graph_id"]: graph},
        native_export_reader=reader,
        preregistration=preregistration.build_preregistration_template())
    sample = output["sample_results"][0]
    assert sample["scoring_status"] == "scored"
    row = _main_caliber_row(sample, payload, graph)
    return row, sample


# ================================================================ 单元级

def test_wv1_monotonic_microsecond_created_at(tmp_path) -> None:
    """W-V1 单元:同 run 内 created_at 严格递增(微秒);幂等 unchanged
    不触碰;新 ledger 实例(B1 恢复)floor 续在已落账最大值之上。"""
    from pathlib import Path as _P

    from pathway_v43.pollutant.search import SearchLedger
    from pathway_v43.pollutant.store import PollutantPathwayStore

    db = tmp_path / "pollutant.sqlite"
    ledger = SearchLedger(PollutantPathwayStore(db), run_id="wv1mono")
    from pathway_v43.pollutant.profile import build_profile_identity_block

    policy = build_profile_identity_block(
        search_limits=_PROFILE["search_limits"],
        format_feedback_policy={"max_format_feedback_rounds": 0})
    ledger.register_search_run("wv1mono", policy)

    def _enqueue(i: int) -> str:
        out = ledger.enqueue_action(
            run_id="wv1mono", parent_path_id="pp", context_ref="ctx",
            subject_ref=f"subj-{i}", action_kind="decide",
            parent_search_revision=0, policy_version="pv",
            payload={"task_key": f"tk-{i}"})
        assert out["created"]
        return str(out["action_id"])

    ids = [_enqueue(i) for i in range(6)]
    rows = [dict(r) for r in ledger.conn.execute(
        "SELECT action_id, created_at FROM search_actions"
        " ORDER BY created_at, action_id")]
    stamps = [r["created_at"] for r in rows]
    # 微秒格式(定长 > 秒级 19 字符)且严格递增(字符串序=时间序)
    assert len(set(stamps)) == len(stamps) == 6
    for s in stamps:
        assert len(s) >= 20, s
    assert stamps == sorted(stamps)
    assert [r["action_id"] for r in rows] == ids  # FIFO = 入队序
    # 幂等 unchanged:重放同键不触碰 created_at
    again = ledger.enqueue_action(
        run_id="wv1mono", parent_path_id="pp", context_ref="ctx",
        subject_ref="subj-3", action_kind="decide",
        parent_search_revision=0, policy_version="pv",
        payload={"task_key": "tk-3"})
    assert not again["created"] and again["unchanged"]
    rows2 = [dict(r) for r in ledger.conn.execute(
        "SELECT created_at FROM search_actions"
        " ORDER BY created_at, action_id")]
    assert [r["created_at"] for r in rows2] == stamps
    # B1 恢复:新 ledger 实例(内存无 floor)续入队 ⇒ 时间戳 > 已落账
    # 最大值(崩溃中途重放保持相对次序)
    ledger_b = SearchLedger(PollutantPathwayStore(db), run_id="wv1mono")
    _enqueue_b = ledger_b.enqueue_action(
        run_id="wv1mono", parent_path_id="pp", context_ref="ctx",
        subject_ref="subj-99", action_kind="decide",
        parent_search_revision=0, policy_version="pv",
        payload={"task_key": "tk-99"})
    assert _enqueue_b["created"]
    stamps_b = [str(r["created_at"]) for r in ledger_b.conn.execute(
        "SELECT created_at FROM search_actions"
        " ORDER BY created_at, action_id")]
    assert len(stamps_b) == 7 and len(set(stamps_b)) == 7
    assert stamps_b == sorted(stamps_b)
    assert stamps_b[-1] > stamps[-1]


# ================================================================ 正控①

def test_wv1_novel_first_submitted_and_scorer_rank1(tmp_path) -> None:
    """正控①:8 池 + 首位 novel,budget8 ⇒ novel 首提交;提交序=调度序
    (action 层与事件层);原 scorer 主口径 rank1(穿 export→判分)。"""
    pool = _compiled_pool()
    # 模型显式首位 = novel-1(CC=O + [H][H],严中 e-alt-1 首边)
    response = json.dumps({
        "proposals": [_novel_spec("CC=O", coproducts=["[H][H]"])],
        "rank_hypotheses": ["novel-1"]})
    model = ScriptedRealModelAdapter(
        strategy="responses", responses=[response], model_id="wv1-model")
    summary = _run(tmp_path, "wv1-novel-first", {
        "pools": {"CCO": pool}, "model": {
            "provider_kind": "scripted", "responses": [response]}},
        model)
    assert summary["counts"]["events"] >= 2
    runs_root = tmp_path / "runs"
    out = _extract_order(runs_root, "wv1-novel-first")
    # ---- action 层:取任务序(ORDER BY created_at, action_id)=调度序
    ranks = [a["eff_rank"] for a in out["action_order"]]
    assert ranks == sorted(ranks) and len(set(ranks)) == len(ranks)
    # 8 备选预算:novel + 池都在调度内(第 9 条按预算 deferred/blocked)
    assert out["action_order"][0]["lpid"] == "novel-1"
    assert out["action_order"][0]["eff_rank"] == 1
    # created_at 互异(严格单调;同秒哈希 tie-break 形态消除)
    action_stamps = [a["created_at"] for a in out["action_order"]]
    assert len(set(action_stamps)) == len(action_stamps)
    # ---- 事件层:提交序 = 调度序(检测器;首个事件 = novel)
    events = out["event_order"]
    assert events[0]["lpid"] == "novel-1"
    assert _submission_follows_rank(events) is True
    # ---- export→原 score:novel 事件 rank1(matched_strict)
    digest = summary["native_export"]["export_digest"]
    graph = _qid_graph("rg-wv1-a", edges_first="e-alt-1")
    row, sample = _score_main_row(
        tmp_path, "wv1-novel-first", digest, graph)
    assert row["match_status"] == "matched_strict"
    assert row["rank"] == 1
    assert row["n_matched_events"] == 1
    assert sample["pairing"]["basis"] == "qid_strict"
    # 命中事件 = 首个提交事件(提交序=调度序 ⇒ 模型首位即 scorer 首位)
    matched_ids = [str(e["event_id"]) for e in
                   sample["predicted_edge_matches"][0]["matched_events"]]
    assert matched_ids == [events[0]["event_id"]]


# ================================================================ 正控②

def test_wv1_recorded_first_choice_submitted_first(tmp_path) -> None:
    """正控②(47 题反例形态合成版):模型显式首位的 recorded 池候选
    首提交且原 scorer rank1(novel 排第 2 不因哈希序洗到前面)。"""
    reset_library_cache()
    # 合成库:CCO → CC=O(r0001,recorded 直通源;与真实金标零重叠)
    lib = tmp_path / "library_full.jsonl"
    lib.write_text(json.dumps({
        "btid": "btW", "donor_id": "CCO", "donor_smiles": "CCO",
        "package": "SYNTH", "product_sb": "CC=O",
        "product_smiles": "CC=O", "reac_id": "r0001"}) + "\n",
        encoding="utf-8")
    import hashlib

    class _FakeEngine:
        identity_block = {
            "library_path": str(lib),
            "library_sha256": hashlib.sha256(
                lib.read_bytes()).hexdigest(),
        }

    compiled = compile_recorded_reaction(
        substrate_smiles="CCO", donor_smiles="CCO",
        products=["CC=O"], record_id="btW#r0001")
    assert compiled["status"] == "compiled", compiled
    rec_spec = dict(compiled["spec"])
    del _FakeEngine
    # 其余池 = 7 个不同净反应(不匹配金标)
    others = _compiled_pool()[:7]
    pool = [rec_spec] + others
    assert rec_spec["key"] == "rec-btW#r0001"
    # 模型显式首位 = recorded 池候选(prepared hypothesis_id);
    # novel(CC=O→[H][H] 之外的净反应)排第 2
    from pathway_v43.domain.models import stable_id
    from pathway_v43.pollutant.chemstate import build_chemical_state

    run_id = "wv1-rec-first"
    root_path = stable_id("spath", run_id, "root")
    substrate_state = build_chemical_state(
        "CCO", "raw_input", [{"record": f"ppv1-substrate:{run_id}"}])
    rec_prepared = prepare_hypothesis(
        rec_spec, parent_path_id=root_path,
        substrate_state=substrate_state,
        transformation_ref=str(rec_spec.get("transformation_ref") or ""))
    rec_hyp_id = rec_prepared["hypothesis"].hypothesis_id
    response = json.dumps({
        # 协议:rank 引用的 id 必须在提案集合内(池引用 = 裸
        # hypothesis_id 条目;novel = proposal_context+reaction_spec)
        "proposals": [
            {"hypothesis_id": rec_hyp_id},
            _novel_spec("CCOO")],
        "rank_hypotheses": [rec_hyp_id, "novel-1"]})
    model = ScriptedRealModelAdapter(
        strategy="responses", responses=[response], model_id="wv1-model")
    summary = _run(tmp_path, run_id, {
        "pools": {"CCO": pool}, "model": {
            "provider_kind": "scripted", "responses": [response]}},
        model)
    assert summary["counts"]["events"] >= 2
    out = _extract_order(tmp_path / "runs", run_id)
    # 首位提交事件 = recorded 候选(模型显式第 1 位不被洗后)
    events = out["event_order"]
    assert events[0]["lpid"] == "rec-btW#r0001"
    assert events[0]["eff_rank"] == 1
    assert out["action_order"][0]["lpid"] == "rec-btW#r0001"
    assert _submission_follows_rank(events) is True
    # ---- export→原 score:recorded 事件 rank1(首边 = e-alt-2:
    # CC=O 无共同产物边)
    digest = summary["native_export"]["export_digest"]
    graph = _qid_graph("rg-wv1-b", edges_first="e-alt-2")
    row, sample = _score_main_row(tmp_path, run_id, digest, graph)
    assert row["match_status"] == "matched_strict"
    assert row["rank"] == 1
    assert sample["pairing"]["basis"] == "qid_strict"


# ================================================================ 负控

def test_wv1_old_hash_tie_shape_detected_red(tmp_path) -> None:
    """负控:调度序≠提交序的旧形态(哈希 tie-break,v2 批形态)在
    W-V1 断言下必须红 —— 同一检测函数对哈希序重排返回 False
    (证明正控断言非空洞;父基线 35727eb 上正控测试即红,红绿对照
    见交付书)。"""
    # 用正控①的产物构造两种事件序:实际(新代码,单调 created_at
    # =调度序)vs 合成 v2 形态(事件按对应 action_id 哈希序重排,
    # 同秒 tie-break 的实际后果)。
    pool = _compiled_pool()
    response = json.dumps({
        "proposals": [_novel_spec("CC=O", coproducts=["[H][H]"])],
        "rank_hypotheses": ["novel-1"]})
    model = ScriptedRealModelAdapter(
        strategy="responses", responses=[response], model_id="wv1-model")
    summary = _run(tmp_path, "wv1-neg", {
        "pools": {"CCO": pool}, "model": {
            "provider_kind": "scripted", "responses": [response]}},
        model)
    assert summary["counts"]["events"] >= 2
    out = _extract_order(tmp_path / "runs", "wv1-neg")
    events = out["event_order"]
    assert _submission_follows_rank(events) is True
    # v2 形态合成:按 action_id 哈希序重排事件(action_order 的
    # created_at 在旧秒级实现下同值 ⇒ tie-break=action_id 字典序)
    action_id_by_hyp = {}
    conn = sqlite3.connect(
        str(tmp_path / "runs" / "wv1-neg" / "pollutant.sqlite"))
    conn.row_factory = sqlite3.Row
    for r in conn.execute(
            "SELECT action_id, payload FROM search_actions WHERE"
            " action_kind='expand_hypothesis'"):
        pl = json.loads(r["payload"] or "{}")
        action_id_by_hyp[str(pl.get("prepared_hypothesis_id") or "")] = \
            str(r["action_id"])
    conn.close()
    hash_order = sorted(
        events, key=lambda e: action_id_by_hyp.get(e["hyp"], "~"))
    hash_lpids = [e["lpid"] for e in hash_order]
    submit_lpids = [e["lpid"] for e in events]
    # 哈希序重排与调度序不同(合成池形态可证)且检测器判 False
    assert _submission_follows_rank(hash_order) is False
    assert hash_lpids != submit_lpids or not hash_lpids
    with pytest.raises(AssertionError):
        # 旧形态必须红:同样断言调度序(正控同句)在哈希序上失败
        assert _submission_follows_rank(hash_order) is True
