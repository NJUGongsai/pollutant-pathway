"""PPV1 S5b HIT50 W0/W2/W3/W4/W5/W6 —— 合成正/负控(公共链;零网络)。

- W0:聚合诊断 U/H5/L 单调性断言 + 判分互斥桶总/运行状态表总 298;
  批准状态 R1 白名单;
- W2:recorded 精确源(strict/cn 分层、完整净产物集合、推断映射、
  产物多重集核对、源 hash 校验、负控族);
- W3:统一 effective_rank(显式 rank 先于 fallback;novel 不因来源
  排后;未 rank 池不抢前)+ 事件高分辨率 created_at 忠实记录 +
  原 scorer (created_at, event_id) 排序贯穿 store→export;
- W4:池供给 raw24/pool8/保检索序/失败补位/同签名去重/阈值降档;
- W5:同一执行图载荷(与编译器同源)+ novel 逐条容错(一坏一合法);
- W6:R2 gate 占位恰一次释放/死亡回收;R3 blob 原子保存与 responded
  零调用重放;R5 孤儿禁新 logical 请求。
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pathway_v43.config import resolve_config  # noqa: E402
from pathway_v43.pollutant.production import (  # noqa: E402
    execute_atomtool_expansion,
)
from pathway_v43.pollutant.recorded_source import (  # noqa: E402
    RECORDED_SOURCE_VERSION,
    compile_recorded_reaction,
    infer_reaction_mapping,
    reset_library_cache,
)
from pathway_v43.pollutant.real_model import (  # noqa: E402
    PROPOSALS_PROMPT_VERSION,
    RealModelAdapter,
    RealModelTransportFailure,
    ScriptedRealModelAdapter,
    execution_graph_payload,
)
from pathway_v43.pollutant.runflow import (  # noqa: E402
    S5B_RANK_POLICY_VERSION,
    start_ppv1_run,
)
from pathway_v43.pollutant.s5b_builder import (  # noqa: E402
    S5B_POOL_POLICY_VERSION,
    S5B_POOL_RAW_TOP,
    default_pool_provider,
)
from pathway_v43.pollutant.s5b_compiler import (  # noqa: E402
    compile_donor_template,
    net_reaction_signature,
)
from pathway_v43.pollutant.s5b_scoring import (  # noqa: E402
    PREREG_APPROVAL_APPROVED_STATUSES,
    S5bScoringError,
    normalize_preregistration,
    preregistration_approved,
)

_PROFILE = {
    "search_limits": {
        "max_alternative_hypotheses_per_parent": 8,
        "max_attempts_per_hypothesis": 1,
        "max_product_expansion_width": 2,
        "max_search_depth": 1,
        "max_total_search_actions": 48,
        "max_scenario_transitions": 0,
        "max_reopens_per_hypothesis": 0,
        "max_real_model_requests": 0,
        "max_retrievals_per_parent": 1,
        "max_retrievals_total": 8,
    },
    "format_feedback_policy": {"max_format_feedback_rounds": 0},
}




def _claimed_decide_action(ledger, run_id: str) -> str:
    """登记并认领一个 decide action(register_model_request 契约)。"""
    from pathway_v43.pollutant.search import search_policy_version

    out = ledger.enqueue_action(
        run_id=run_id, parent_path_id="pp1", context_ref="ctx",
        subject_ref="subj", action_kind="decide",
        parent_search_revision=0,
        policy_version=search_policy_version(),
        payload={"task_key": "tk-" + run_id})
    action_id = str(out["action_id"])
    ledger.claim_action(action_id, worker_id="w-" + run_id)
    return action_id


def _policy_block(real_requests: int = 4) -> dict:
    """经 profile 校验的 search policy 块(register_search_run 契约)。"""
    from pathway_v43.pollutant.profile import build_profile_identity_block

    return build_profile_identity_block(
        search_limits=dict(_PROFILE["search_limits"],
                           max_real_model_requests=real_requests),
        format_feedback_policy={
            "max_format_feedback_rounds": 0})


def _spec(substrate: str = "CCO", record_id: str = "t",
          product: str = "CC=O") -> dict:
    out = compile_donor_template(
        mapped_lhs="[CH3:1][CH2:2][OH:3]",
        mapped_rhs="[CH3:1][CH:2]=[O:3]",
        center_atoms=[2, 3], substrate_smiles=substrate,
        record_id=record_id)
    assert out["status"] == "compiled", out
    return out["spec"]


# ================================================================ W0

def test_w0_prereg_approval_whitelist_r1() -> None:
    """R1:approved/confirmed/preregistration_confirmed 过;
    rejected/not_approved/pending/空/未知拒(旧"非 pending 即过"
    会放行 rejected)。"""
    for status in ("approved", "confirmed",
                   "preregistration_confirmed"):
        assert preregistration_approved({"approval_status": status})
    for status in ("rejected", "not_approved", "pending", "",
                   "preregistration_pending_final_confirmation",
                   "withdrawn", "unknown_status"):
        assert not preregistration_approved({"approval_status": status})
    assert not preregistration_approved(None)
    # 归一入口同样验证(不静默洗白)
    assert normalize_preregistration(
        {"approval_status": "confirmed"})["approval_status"] == "approved"
    with pytest.raises(S5bScoringError):
        normalize_preregistration({"approval_status": "rejected"})
    with pytest.raises(S5bScoringError):
        normalize_preregistration({"approval_status": ""})


def test_w0_aggregate_diagnosis_monotonicity_closure(tmp_path) -> None:
    """W0:聚合诊断 U/H5/L 断言 + 判分互斥桶总/运行状态表总 = 分母
    (score_s5b_batch 合成端到端)。"""
    from pathway_v43.pollutant.s5b_builder import build_question_batch
    from pathway_v43.pollutant.s5b_orchestrator import run_s5b_batch
    from pathway_v43.pollutant.s5b_scoring import score_s5b_batch

    root = tmp_path / "w0"
    root.mkdir()
    questions = [
        {"qid": "SYN-QA", "substrate_smiles": "CCO",
         "products_smiles": ["CC=O"], "raw": "x"},
        {"qid": "SYN-QB", "substrate_smiles": "CCO",
         "products_smiles": ["CC=O"], "raw": "x"},
        {"qid": "SYN-QC", "substrate_smiles": "CCOCC",
         "products_smiles": ["CCO"], "raw": "x"},
    ]
    qpath = root / "questions.jsonl"
    qpath.write_text(
        "\n".join(json.dumps(q) for q in questions) + "\n",
        encoding="utf-8")
    batch_root = root / "batch"

    def pool_provider(substrate: str) -> list[dict]:
        if substrate == "CCO":
            return [_spec(substrate, "w0a"), _spec(substrate, "w0b")]
        return []

    build_question_batch(
        qpath, batch_root, batch_tag="w0", pool_provider=pool_provider,
        provider_kind="scripted", synthetic_review=True)
    stub = root / "stub.json"
    stub.write_text(json.dumps({"strategy": "first_pool"}),
                    encoding="utf-8")
    old = os.environ.get("S5B_MODEL_STUB_SCRIPT")
    os.environ["S5B_MODEL_STUB_SCRIPT"] = str(stub)
    try:
        report = run_s5b_batch(
            batch_root, runs_root=root / "runs", workers=2,
            profile_policy={
                "search_limits": dict(
                    _PROFILE["search_limits"],
                    max_real_model_requests=4),
                "format_feedback_policy": {
                    "max_format_feedback_rounds": 0}})
    finally:
        if old is None:
            os.environ.pop("S5B_MODEL_STUB_SCRIPT", None)
        else:
            os.environ["S5B_MODEL_STUB_SCRIPT"] = old
    agg = score_s5b_batch(
        batch_root, runs_root=root / "runs",
        data_scope="synthetic_rule_level")
    diagnosis = agg["aggregate_diagnosis"]
    h5 = agg["main_caliber"]["hit@5"]
    assert 0 <= agg["main_caliber"]["hit@1"] <= h5 <= \
        diagnosis["U_strict_matched_questions"] <= agg["denominator"]
    assert diagnosis["L_below_k"] == \
        diagnosis["U_strict_matched_questions"] - h5
    # 判分互斥桶总 = 分母;运行状态附表总 = 分母(两表分开)
    assert sum(v for k, v in agg["buckets"].items()
               if not k.startswith("run_")) == agg["denominator"]
    assert sum(agg["run_status_table"].values()) == agg["denominator"]


# ================================================================ W2

class _FakeEngine:
    """W2 测试桩:identity_block(library 路径/哈希)+ expand_raw。

    合成库行与真实 298 金标零重叠(乙醇/乙醛级合成小分子)。"""

    def __init__(self, tmp: Path, rows: list[dict] | None = None):
        lib = tmp / "library_full.jsonl"
        lib.write_text(
            "\n".join(json.dumps(r) for r in (rows or [
                {"btid": "btX", "donor_id": "CCO",
                 "donor_smiles": "CCO", "package": "SYNTH",
                 "product_sb": "CC=O", "product_smiles": "CC=O",
                 "reac_id": "r0001"},
                {"btid": "btX", "donor_id": "CCO",
                 "donor_smiles": "CCO", "package": "SYNTH",
                 "product_sb": "CC(=O)O", "product_smiles": "CC(=O)O",
                 "reac_id": "r0002"},
            ])) + "\n", encoding="utf-8")
        import hashlib

        self.identity_block = {
            "library_path": str(lib),
            "library_sha256": hashlib.sha256(
                lib.read_bytes()).hexdigest(),
        }
        self._rows = rows

    def expand_raw(self, smiles: str, case_id: str = "c") -> dict:
        rows = []
        seen = set()
        for line in Path(
                self.identity_block["library_path"]).read_text(
                encoding="utf-8").splitlines():
            record = json.loads(line)
            if record["donor_smiles"] != smiles:
                continue
            rid = f"{record['btid']}#{record['reac_id']}"
            if rid in seen:
                continue
            seen.add(rid)
            rows.append({
                "product_smiles": record["product_smiles"],
                "product_smiles_full": record["product_smiles"],
                "source": "eawag_lookup", "layer": "lookup",
                "eawag_reactions": [rid], "donor_exact_match": True,
                "n_evidence": 1, "tanimoto": 1.0,
                "ion_filtered": False, "cofactor_filtered": False,
                "filtered": False,
            })
        return {"lookup": rows, "pred_edges": [], "merged_edges": rows,
                "n_pred_candidates": 0, "n_lookup": len(rows),
                "budget_cut": False, "pool_capped": False,
                "canonical_smiles": smiles}


def test_w2_recorded_strict_exact_compiles(tmp_path) -> None:
    """W2 正控:strict exact(同严格身份)分层 + 完整净产物核对。"""
    reset_library_cache()
    engine = _FakeEngine(tmp_path)
    out = compile_recorded_reaction(
        substrate_smiles="CCO", donor_smiles="CCO",
        products=["CC=O"], record_id="btX#r0001")
    assert out["status"] == "compiled", out
    spec = out["spec"]
    assert spec["key"] == "rec-btX#r0001"
    assert spec["product_smiles"] == "CC=O"
    assert spec["expectation"]["target_smiles"] == "CC=O"
    assert spec["compile"]["mapping_origin"] == "inferred"
    assert spec["compile"]["verified_product_set"] is True
    # 系数未知(库记录无配平)⇒ spec 不携带 coefficient
    assert "coefficient" not in spec
    # 推断映射不是原生/机制证据:标注如实
    assert spec["alignment"]["ref"] == "recorded-inferred:btX#r0001"
    # 未知条件不授机制 verified:经公共链执行,center 只到 direct
    execution = execute_atomtool_expansion(
        substrate_smiles="CCO", tool_inputs={
            "edits": spec["edits"], "donor": spec["donor"],
            "alignment": spec["alignment"],
            "expectation": spec["expectation"]})
    assert execution["diagnostic"]["reaction_center_match"] is True
    assert execution["diagnostic"]["strict_target_match"] is True


def test_w2_recorded_full_product_set_and_negatives(tmp_path) -> None:
    """W2:完整净产物集合(同反应多产品)+ 负控族(缺产物/另一底物/
    CN 同而 strict 异不升格)。"""
    reset_library_cache()
    # 双产物反应(裂解):完整集合核对通过,主/共产物入参与物
    out = compile_recorded_reaction(
        substrate_smiles="CCOCC", donor_smiles="CCOCC",
        products=["CCO", "CC"], record_id="btX#r0003")
    assert out["status"] == "compiled", out
    spec = out["spec"]
    assert {spec["product_smiles"], *spec["coproducts"]} == \
        {"CCO", "CC"}
    # 负控:缺产物(filtered 单产品卡冒完整)⇒ product_set_mismatch
    out = compile_recorded_reaction(
        substrate_smiles="CCOCC", donor_smiles="CCOCC",
        products=["CCO"], record_id="btX#r0003")
    assert out["status"] == "unsupported"
    assert out["reason"] == "product_set_mismatch"
    # 负控:另一底物(方向/底物不符)⇒ 不能按记录核对通过
    out = compile_recorded_reaction(
        substrate_smiles="CCCO", donor_smiles="CCO",
        products=["CC=O"], record_id="btX#r0001")
    assert out["status"] == "unsupported"
    assert out["reason"] == "product_set_mismatch"
    # 负控:CN 同而电荷不同(中性底物 vs 负离子 donor)⇒ 不升格
    # strict(编译层如实拒:对齐失败或电荷编辑不支持)
    out = compile_recorded_reaction(
        substrate_smiles="OCCCCC(=O)O",
        donor_smiles="OCCCCCC([O-])=O",
        products=["[O-]C(=O)CCCCC=O"], record_id="btX#r0004")
    assert out["status"] == "unsupported"


def test_w2_find_recorded_exact_tiering(tmp_path) -> None:
    """W2:find_recorded_exact 分层(strict/cn 计数、库回读完整性、
    哈希校验)。"""
    reset_library_cache()
    engine = _FakeEngine(tmp_path)
    from pathway_v43.pollutant.recorded_source import find_recorded_exact

    out = find_recorded_exact(
        substrate_smiles="CCO", engine=engine)
    tiers = [c["tier"] for c in out["candidates"]]
    assert "recorded_strict_exact" in tiers
    assert out["diagnostics"]["n_strict_exact"] >= 1
    compiled = [c for c in out["candidates"] if c["compile"]]
    assert compiled
    # 检索序保留:strict 在前
    assert out["candidates"][0]["tier"] == "recorded_strict_exact"


def test_w2_source_hash_tamper_rejected(tmp_path) -> None:
    """W2 负控:库文件哈希与引擎身份不符(篡改)⇒ fail-closed。"""
    reset_library_cache()
    engine = _FakeEngine(tmp_path)
    from pathway_v43.pollutant.recorded_source import (
        RecordedSourceError,
        load_library_index,
    )

    # 篡改库内容(不更新 identity 哈希)
    path = Path(engine.identity_block["library_path"])
    path.write_text(path.read_text() + json.dumps({
        "btid": "btX", "donor_id": "CCO", "donor_smiles": "CCO",
        "package": "SYNTH", "product_sb": "CCCO",
        "product_smiles": "CCCO", "reac_id": "r0009"}) + "\n",
        encoding="utf-8")
    with pytest.raises(RecordedSourceError) as excinfo:
        load_library_index(engine)
    assert excinfo.value.detail["kind"] == "library_hash_mismatch"


def test_w2_infer_mapping_ambiguity_disclosure() -> None:
    """W2:结构同构枚举有界 + 对称多解(丁烷裂解两解)。"""
    mappings = infer_reaction_mapping("CCCC", ["CCC", "C"])
    assert len(mappings) >= 2  # 对称多解如实枚举
    # 完整同构(乙醇→乙醛):唯一/等价解
    mappings = infer_reaction_mapping("CCO", ["CC=O"])
    assert mappings


# ================================================================ W3

def test_w3_effective_rank_model_selection_precedes_fallback(tmp_path) -> None:
    """W3:显式模型 rank 全部先于未 rank fallback;novel 排第 1(
    不因来源被排后);未 rank 池不抢前。公共链:rank 字段落冻结
    任务载荷,事件按 effective_rank 顺序调度提交。"""
    # 三条不同净反应池条目 + 一条同净反应重复(pool4=pool1 签名):
    # pool1=CC=O(氧化),pool2=CC(=O)O(酸化),pool3=CCOC(醚化);
    # novel-1=CCOO(氢过氧化物;唯一净反应)
    spec_aldehyde = _spec("CCO", "p1")
    spec_acid = compile_donor_template(
        mapped_lhs="[CH3:1][CH2:2][OH:3]",
        mapped_rhs="[CH3:1][C:2](=[O:4])[OH:3]",
        center_atoms=[2], substrate_smiles="CCO",
        record_id="pa")["spec"]
    spec_ether = compile_donor_template(
        mapped_lhs="[CH3:1][CH2:2][OH:3]",
        mapped_rhs="[CH3:1][CH2:2][O:3][CH3:4]",
        center_atoms=[3], substrate_smiles="CCO",
        record_id="pe")["spec"]
    pool = [
        dict(spec_aldehyde, key="pool1"),
        dict(spec_acid, key="pool2"),
        dict(spec_ether, key="pool3"),
        dict(spec_aldehyde, key="pool4"),  # 同净反应(去重负位)
    ]
    novel_spec = compile_donor_template(
        mapped_lhs="[CH3:1][CH2:2][OH:3]",
        mapped_rhs="[CH3:1][CH2:2][O:3][OH:4]",
        center_atoms=[3], substrate_smiles="CCO",
        record_id="n1")["spec"]
    assert novel_spec["product_smiles"] == "CCOO"
    # 模型响应:只 rank pool3(位次 1);pool1/pool2 未 rank;
    # novel CC=O 提案(反应内容合法)。rank/池引用须用 prepared
    # hypothesis_id(哈希 ID —— 提示词载荷携带的稳定 ID),不是池 key
    from pathway_v43.domain.models import stable_id
    from pathway_v43.pollutant.chemstate import build_chemical_state
    from pathway_v43.pollutant.production import prepare_hypothesis

    run_id = "w3rank"
    root_path = stable_id("spath", run_id, "root")
    substrate_state = build_chemical_state(
        "CCO", "raw_input", [{"record": f"ppv1-substrate:{run_id}"}])
    hyp_ids = {}
    for spec in pool:
        prepared = prepare_hypothesis(
            spec, parent_path_id=root_path,
            substrate_state=substrate_state,
            transformation_ref=str(spec.get("transformation_ref") or ""))
        hyp_ids[spec["key"]] = prepared["hypothesis"].hypothesis_id
    novel_response = json.dumps({
        "proposals": [
            {"hypothesis_id": hyp_ids["pool3"]},
            {"hypothesis_id": "novel-1",
             "proposal_context": {"reference_hypothesis_ids": [],
                                  "output_origin": "novel_outside_pool"},
             "reaction_spec": {
                 "product_smiles": "CCOO",
                 "edits": [{"op": "add_atom", "element": "O",
                            "new_atom_id": "SN_O_1", "atom1": "S_O_1"}],
                 "donor": {"center_atom_ids": ["S_O_1", "SN_O_1"]},
                 "alignment": {"status": "resolved",
                               "donor_to_current": {"S_O_1": "S_O_1",
                                                    "SN_O_1": "SN_O_1"},
                               "ref": "self"},
                 "expectation": {"target_smiles": "CCOO"}}}],
        "rank_hypotheses": ["novel-1", hyp_ids["pool3"]]})
    model = ScriptedRealModelAdapter(
        strategy="responses", responses=[novel_response],
        model_id="w3-model")
    summary = start_ppv1_run(
        config=resolve_config(), runs_root=tmp_path / "runs",
        run_id=run_id, smiles="CCO",
        plan={"pools": {"CCO": pool},
              "model": {"provider_kind": "scripted",
                        "responses": [novel_response]}},
        model=model, profile_policy=dict(
            _PROFILE, search_limits=dict(
                _PROFILE["search_limits"], max_real_model_requests=4)))
    assert summary["counts"]["events"] >= 1
    # 冻结任务载荷:显式 rank 先于 fallback + rank_basis 版本化
    conn = sqlite3.connect(
        str(tmp_path / "runs" / run_id / "pollutant.sqlite"))
    payloads = [json.loads(r[0]) for r in conn.execute(
        "SELECT payload FROM search_actions WHERE action_kind ="
        " 'expand_hypothesis' AND run_id = ?", (run_id,)).fetchall()]
    conn.close()
    assert payloads
    by_key = {p["logical_proposal_id"]: p for p in payloads}
    # novel-1(model rank 1)与 pool3(model rank 2)先于未 rank 条目
    assert by_key["novel-1"]["model_rank"] == 1
    assert by_key["novel-1"]["rank_basis"] == "model_selection"
    assert by_key["pool3"]["model_rank"] == 2
    assert by_key["pool3"]["rank_basis"] == "model_selection"
    for key in ("pool1", "pool2"):
        assert by_key[key]["model_rank"] is None
        assert by_key[key]["rank_basis"] == "deterministic_fallback"
        # 未 rank 池不抢前:effective_rank 严格大于一切显式 rank
        assert by_key[key]["effective_rank"] > \
            by_key["pool3"]["effective_rank"]
    for p in payloads:
        assert p["rank_policy_version"] == S5B_RANK_POLICY_VERSION
        assert p["prepared_hypothesis_id"]
        assert isinstance(p["net_reaction_signature"], list)
    # 去重:pool4 与 pool1 同净反应签名 ⇒ 折叠(pool4 不入调度)
    assert "pool4" not in by_key
    sigs = {tuple(p["net_reaction_signature"]) for p in payloads}
    assert len(sigs) == len(payloads) == 4


def test_w3_events_created_at_high_resolution_faithful(tmp_path) -> None:
    """W3:公共 writer 忠实记录首提高分辨率 created_at(行 = 载荷;
    重放不刷新);原 scorer (created_at, event_id) 序贯穿 export。"""
    from pathway_v43.pollutant.native_export import read_native_export
    from pathway_v43.pollutant.search import SearchLedger
    from pathway_v43.pollutant.store import PollutantPathwayStore
    from pathway_v43.storage.artifact_store import ArtifactStore

    spec_a = _spec("CCO", "ta")
    spec_b = compile_donor_template(
        mapped_lhs="[CH3:1][CH2:2][OH:3]",
        mapped_rhs="[CH3:1][CH2:2][O:3][OH:4]",
        center_atoms=[3], substrate_smiles="CCO",
        record_id="tb")["spec"]
    summary = start_ppv1_run(
        config=resolve_config(), runs_root=tmp_path / "runs",
        run_id="w3time", smiles="CCO",
        plan={"pools": {"CCO": [spec_a, spec_b]}},
        profile_policy=_PROFILE)
    events = summary["counts"]["events"]
    assert events >= 2
    store = PollutantPathwayStore(
        tmp_path / "runs" / "w3time" / "pollutant.sqlite")
    rows = [dict(r) for r in store.conn.execute(
        "SELECT event_id, payload, created_at FROM events").fetchall()]
    assert len(rows) == events
    for row in rows:
        # 高分辨率:微秒级时间戳(长度 > 秒级 19 字符)
        assert len(str(row["created_at"])) >= 20, row["created_at"]
        # 行 created_at 与事件载荷 created_at 同源一致(忠实记录)
        payload = json.loads(row["payload"])
        assert payload.get("created_at") == row["created_at"]
    # 同秒提交的两个事件:created_at 互异(提交序可辨;旧秒级下
    # 两事件必然同秒 ⇒ event_id hash 字典序重排)
    stamps = sorted(r["created_at"] for r in rows)
    assert len(set(stamps)) == len(stamps)
    # export 读回:事件行与 created_at 一致(供原 scorer 排序)
    ledger = SearchLedger(store, ArtifactStore(
        tmp_path / "runs", "w3time"), "w3time")
    digest = summary["native_export"]["export_digest"]
    out = read_native_export(ledger, tmp_path / "runs" / "w3time",
                             digest)
    exported = {str(e.get("event_id")): str(e.get("created_at"))
                for e in out["payload"]["events"]}
    for row in rows:
        assert exported[row["event_id"]] == row["created_at"]


def test_w3_dedup_by_net_reaction_signature() -> None:
    """W3:同净产物集合(严格身份)去重;不同反应(组分/立体差异)
    不误并。"""
    spec_same = _spec("CCO", "same1")
    assert net_reaction_signature(spec_same) == \
        net_reaction_signature(_spec("CCO", "same2"))
    # 不同净反应:加氧产物 vs 氧化产物
    spec_other = compile_donor_template(
        mapped_lhs="[CH3:1][CH2:2][OH:3]",
        mapped_rhs="[CH3:1][CH2:2][O:3][OH:4]",
        center_atoms=[3], substrate_smiles="CCO",
        record_id="other")["spec"]
    assert net_reaction_signature(spec_same) != \
        net_reaction_signature(spec_other)


# ================================================================ W4

def test_w4_pool_provider_backfill_and_order(tmp_path) -> None:
    """W4:失败补位(raw 前 N unsupported 而第 N+1 合法 ⇒ 入池)、
    检索序保留(不按 key 字典序)、同签名去重、池宽截断。"""
    class _Ref:
        def __init__(self, rid, lhs, rhs, sim):
            self.record_id = rid
            self.mapped_lhs = lhs
            self.mapped_rhs = rhs
            self.center_atoms = [2, 3]
            self.similarity = sim

    class _Resolver:
        """模板检索桩:前 3 条全坏(charge-only 模板),第 4 条合法。"""
        def __init__(self, config):
            pass

        def templates_similar_to(self, substrate, *, threshold,
                                 top_k):
            refs = [
                # 3 条编译必败(charge-only)
                _Ref("bad1", "[CH3:1][CH2:2][OH:3]",
                     "[CH3:1][CH2:2][O-:3]", 0.9),
                _Ref("bad2", "[CH3:1][CH2:2][OH:3]",
                     "[CH3:1][CH2:2][O-:3]", 0.8),
                _Ref("bad3", "[CH3:1][CH2:2][OH:3]",
                     "[CH3:1][CH2:2][O-:3]", 0.7),
                # 第 4 条合法(旧 top_k=池宽实现会漏)
                _Ref("good1", "[CH3:1][CH2:2][OH:3]",
                     "[CH3:1][CH:2]=[O:3]", 0.6),
                # 第 5 条与第 4 条同净反应(去重)
                _Ref("good2", "[CH3:1][CH2:2][OH:3]",
                     "[CH3:1][CH:2]=[O:3]", 0.5),
            ]
            return refs[:top_k]

    import pathway_v43.services.analog_source as analog_source

    provider = default_pool_provider(
        object(), max_pool=8, raw_top=24, threshold=0.45,
        fallback_threshold=0.40, min_unique_targets=3)
    # 注入 resolver 桩(config 走 analog 通道 —— monkeypatch 覆盖
    # AnalogSourceResolver 构造;s5b_builder 内为调用期 deferred
    # import,patch 模块属性即生效)
    original = analog_source.AnalogSourceResolver

    class _Patched(_Resolver, original):  # type: ignore[misc]
        def __init__(self, config):
            _Resolver.__init__(self, config)

    analog_source.AnalogSourceResolver = _Patched
    try:
        specs = provider("CCO")
    finally:
        analog_source.AnalogSourceResolver = original
    # 失败补位:good1 编译成功入池(前 3 全 unsupported 不占槽)
    assert [s["key"] for s in specs] == ["tpl-good1"]
    assert specs[0]["product_smiles"] == "CC=O"
    # 去重:good2 同签名折叠,合并 provenance 留痕
    assert specs[0]["compile"]["merged_source_keys"] == ["tpl-good2"]
    diag = provider.last_diagnostics
    assert diag["pool_policy_version"] == S5B_POOL_POLICY_VERSION
    # W-V4.1-R1:s5b-pool-policy-3(corpus 通道许可收缩升版;EAWAG
    # 面不变;池融合/补位语义不变)
    assert diag["compile_failure_histogram"].get(
        "charge_edit_unsupported") == 3
    assert diag["n_unique_net_reactions"] == 1
    # 检索序保留:输出序 = 编译成功序(相似度降序),非 key 字典序


def test_w4_pool_provider_empty_without_config() -> None:
    """W4:无 config/engine ⇒ 空池(novel 合法,如实诊断)。"""
    provider = default_pool_provider(None)
    assert provider("CCO") == []
    assert provider.last_diagnostics["channels"] == []


# ================================================================ W5

def test_w5_execution_graph_payload_same_source() -> None:
    """W5:执行图载荷与编译器/render 同一事实源(ID/键级/mapped
    SMILES/图 hash/能力版本;kekulé 执行空间)。"""
    payload = execution_graph_payload("CCO")
    assert set(payload["atoms"]) == {"S_C_1", "S_C_2", "S_O_1"}
    assert payload["atoms"]["S_O_1"]["element"] == "O"
    assert payload["atoms"]["S_C_1"]["formal_charge"] == 0
    bonds = {(b["atom1"], b["atom2"]): b["order"] for b in
             payload["bonds"]}
    assert bonds[("S_C_1", "S_C_2")] == "single"
    assert bonds[("S_C_2", "S_O_1")] == "single"
    assert payload["mapped_smiles"]
    assert len(payload["graph_hash"]) == 64
    assert payload["capability"]["edit_protocol_version"]
    # 同底物同图 hash(确定性);不同底物不同 hash
    assert execution_graph_payload("CCO")["graph_hash"] == \
        payload["graph_hash"]
    assert execution_graph_payload("CCCO")["graph_hash"] != \
        payload["graph_hash"]
    # 芳香底物:键表 kekulé 落位(order ∈ single/double/triple)
    arom = execution_graph_payload("c1ccccc1")
    assert all(b["order"] in ("single", "double", "triple")
               for b in arom["bonds"])
    # 用户载荷携带执行图(公共链 real fetch 提示词)
    from pathway_v43.pollutant.real_model import (
        build_proposals_user_payload,
    )

    text = build_proposals_user_payload(
        substrate_smiles="CCO", atom_id_map={"S_C_1": "C"},
        pool_entries=[], execution_graph=payload)
    loaded = json.loads(text)
    assert loaded["execution_graph"]["graph_hash"] == \
        payload["graph_hash"]


def test_w5_neovel_itemwise_tolerance_one_bad_one_legal(tmp_path) -> None:
    """W5:单条 novel 非法 ⇒ 逐条拒并保留合法候选(一坏一合法正控);
    全坏 ⇒ 如实 empty(不 run 拒;非 catch-all)。"""
    good = {"hypothesis_id": "novel-good",
            "proposal_context": {"reference_hypothesis_ids": [],
                                 "output_origin": "novel_outside_pool"},
            "reaction_spec": {
                "product_smiles": "CC(=O)O",
                "edits": [
                    {"op": "change_bond_order", "atom1": "S_C_2",
                     "atom2": "S_O_1", "from_order": "single",
                     "to_order": "double"},
                    {"op": "add_atom", "element": "O",
                     "new_atom_id": "SN_O_1", "atom1": "S_C_2"}],
                "donor": {"center_atom_ids": ["S_C_2", "S_O_1"]},
                "alignment": {"status": "resolved",
                              "donor_to_current": {"S_C_2": "S_C_2",
                                                   "S_O_1": "S_O_1"},
                              "ref": "self"},
                "expectation": {"target_smiles": "CC(=O)O"}}}
    bad = {"hypothesis_id": "novel-bad",
           "proposal_context": {"reference_hypothesis_ids": [],
                                "output_origin": "novel_outside_pool"},
           "reaction_spec": {
               # 非法:引用未知原子
               "product_smiles": "CC=O",
               "edits": [{"op": "change_bond_order", "atom1": "NOPE_9",
                          "atom2": "S_O_1", "from_order": "single",
                          "to_order": "double"}],
               "donor": {"center_atom_ids": ["S_C_2"]},
               "alignment": {"status": "resolved",
                             "donor_to_current": {"S_C_2": "S_C_2"},
                             "ref": "self"},
               "expectation": {"target_smiles": "CC=O"}}}
    response = json.dumps({"proposals": [bad, good],
                           "rank_hypotheses": ["novel-good"]})
    model = ScriptedRealModelAdapter(
        strategy="responses", responses=[response], model_id="w5")
    summary = start_ppv1_run(
        config=resolve_config(), runs_root=tmp_path / "runs",
        run_id="w5tol", smiles="CCO",
        plan={"pools": {},
              "model": {"provider_kind": "scripted",
                        "responses": [response]}},
        model=model, profile_policy=dict(
            _PROFILE, search_limits=dict(
                _PROFILE["search_limits"], max_real_model_requests=4)))
    # 合法 novel 保留:事件提交(乙酸);坏条目逐条拒
    assert summary["counts"]["events"] == 1
    # 坏条目逐条拒:decide 的 outcome artifact 披露 novel_rejections
    import glob

    outcome_files = glob.glob(
        str(tmp_path / "runs" / "w5tol" / "results" / "*" /
            "expansion_outcome.json"))
    rejections = None
    for ofile in outcome_files:
        payload = json.loads(
            Path(ofile).read_text(encoding="utf-8"))["payload"]
        outcome = payload.get("outcome") or {}
        if outcome.get("kind") == "scheduled":
            model_note = (outcome.get("detail") or {}).get("model") or {}
            if "novel_rejections" in model_note:
                rejections = model_note["novel_rejections"]
    assert rejections, "decide outcome 未披露 novel_rejections"
    assert rejections[0]["hypothesis_id"] == "novel-bad"


def test_w5_neutral_prompt_single_step() -> None:
    """W5:任务中性(酶促单步转化;不偏 degradation);至多 8 净反应;
    提示词版本随内容变化(身份冻结)。"""
    from pathway_v43.pollutant import real_model

    prompt = real_model._PROPOSALS_SYSTEM_PROMPT
    assert "single-step" in prompt
    assert "enzymatic" in prompt
    assert "degradation" not in prompt.split("Rules:")[0]
    assert "at most 8" in prompt
    assert "abstention is legal" in prompt
    import hashlib

    assert PROPOSALS_PROMPT_VERSION == hashlib.sha256(
        prompt.encode("utf-8")).hexdigest()


# ================================================================ W6

def test_w6_r2_gate_placeholder_exactly_once_release(tmp_path) -> None:
    """R2:acquire 占位;恰一次 release;未 acquire 不 release;重复
    release 幂等;死亡 owner 回收(无 TTL);total_requests 不退。"""
    from pathway_v43.adapters.rate_gate import FileRateGate

    gate = FileRateGate(tmp_path / "gate", rpm=10000, tpm=10 ** 9,
                        max_calls=100, max_in_flight=8)
    acquired = gate.acquire()
    assert acquired["placeholder_id"]
    assert gate.snapshot()["in_flight"] == 1
    # 未 acquire 不 release:未知占位 no-op
    gate.record_response(placeholder_id="not-a-placeholder")
    assert gate.snapshot()["in_flight"] == 1
    # 恰一次 release
    gate.record_response(placeholder_id=acquired["placeholder_id"])
    assert gate.snapshot()["in_flight"] == 0
    # 重复 release 幂等(不再扣减;in_flight 不为负)
    gate.record_response(placeholder_id=acquired["placeholder_id"])
    assert gate.snapshot()["in_flight"] == 0
    # 死亡 owner 回收:伪造死亡 pid 占位
    with gate._locked() as f:
        state = gate._load(f)
        state["placeholders"]["g9-dead-1"] = {"pid": 99999999,
                                             "issued_at": time.time()}
        state["in_flight"] = 1
        gate._save(state)
    out = gate.reclaim_dead_placeholders()
    assert out["reclaimed"] == 1
    assert gate.snapshot()["in_flight"] == 0
    assert gate.snapshot()["total_requests"] == 1  # 不退
    # 活 owner 不回收(本进程 pid)
    acq2 = gate.acquire()
    out = gate.reclaim_dead_placeholders()
    assert out["reclaimed"] == 0
    gate.record_response(placeholder_id=acq2["placeholder_id"])
    # 参数核对:打开既有状态 ⇒ 采纳冻结参数(worker 从冻结值装配);
    # 冻结参数被篡改(与运行中 gate 不一致)⇒ GateCorrupt
    assert gate.verify_config()["max_in_flight"] == 8
    from pathway_v43.adapters.rate_gate import GateCorrupt

    gate2 = FileRateGate(tmp_path / "gate", rpm=10000, tpm=10 ** 9,
                         max_calls=100, max_in_flight=4)
    assert gate2.verify_config()["max_in_flight"] == 8  # 采纳冻结值
    with gate._locked() as f:  # 篡改冻结参数(参数漂移负控)
        state = gate._load(f)
        state["max_in_flight"] = 4
        gate._save(state)
    with pytest.raises(GateCorrupt):
        gate.verify_config()


def test_w6_r3_blob_save_and_responded_zero_call_replay(tmp_path) -> None:
    """R3:成功响应先原子 blob 保存(SHA/字节/字符)再 responded;
    responded+有效 blob ⇒ 零调用消费(同 1logical resume);blob 缺
    失/篡改 ⇒ replay_unavailable(不补调用)。"""
    from pathway_v43.pollutant.search import SearchLedger
    from pathway_v43.pollutant.store import PollutantPathwayStore
    from pathway_v43.storage.artifact_store import ArtifactStore

    runs_root = tmp_path / "runs"
    run_id = "w6blob"
    account = runs_root / run_id / "s5b_real_calls.jsonl"
    response_text = json.dumps(
        {"proposals": [], "rank_hypotheses": []})
    model = ScriptedRealModelAdapter(
        strategy="responses", responses=[response_text],
        model_id="w6", call_account_path=account)
    store = PollutantPathwayStore(runs_root / run_id / "pollutant.sqlite")
    ledger = SearchLedger(store, ArtifactStore(runs_root, run_id),
                          run_id)
    ledger.register_search_run(run_id, _policy_block(4))
    action_id = _claimed_decide_action(ledger, run_id)
    request_key = f"decide:{action_id}"
    out = model.ppv1_real_fetch(
        ledger=ledger, run_id=run_id, action_id=action_id,
        attempt_id="",
        prompt_payload={"substrate_smiles": "CCO", "atom_id_map": {},
                        "pool_entries": []},
        request_key=request_key, purpose="proposals",
        provider_kind="scripted")
    assert out["response_text"] == response_text
    blob_path = runs_root / run_id / "s5b_responses" / \
        f"{out['request']['request_id']}.json"
    assert blob_path.is_file()
    blob = json.loads(blob_path.read_text(encoding="utf-8"))
    assert blob["content"] == response_text
    assert blob["bytes"] == len(response_text.encode("utf-8"))
    # responded + 有效 blob ⇒ 零调用重放(scripted 桩 responses 已耗
    # 尽:若走新调用将得空响应 —— 重放返回原文本证明零调用)
    replay = model.ppv1_real_fetch(
        ledger=ledger, run_id=run_id, action_id=action_id,
        attempt_id="",
        prompt_payload={"substrate_smiles": "CCO", "atom_id_map": {},
                        "pool_entries": []},
        request_key=request_key, purpose="proposals",
        provider_kind="scripted")
    assert replay["response_text"] == response_text
    assert replay["call"].get("replayed") is True
    # blob 篡改 ⇒ replay_unavailable(不补调用)
    blob["content"] = json.dumps({"proposals": [], "tampered": True})
    blob_path.write_text(json.dumps(blob, ensure_ascii=False,
                                    sort_keys=True), encoding="utf-8")
    with pytest.raises(Exception) as excinfo:  # noqa: B017
        model.ppv1_real_fetch(
            ledger=ledger, run_id=run_id, action_id=action_id,
            attempt_id="",
            prompt_payload={"substrate_smiles": "CCO",
                            "atom_id_map": {}, "pool_entries": []},
            request_key=request_key, purpose="proposals",
            provider_kind="scripted")
    assert getattr(excinfo.value, "detail", {}).get("kind") == \
        "replay_unavailable"


def test_w6_r5_orphan_sent_no_blob_no_new_logical(tmp_path) -> None:
    """R5:sent 且无完整 blob ⇒ failed 占额 + **不新 logical 请求**
    (旧孤儿自动 retry_of 新请求的反例);模型身份含 retry 参数。"""
    from pathway_v43.pollutant.search import SearchLedger
    from pathway_v43.pollutant.store import PollutantPathwayStore
    from pathway_v43.storage.artifact_store import ArtifactStore

    runs_root = tmp_path / "runs"
    run_id = "w6orphan"
    account = runs_root / run_id / "s5b_real_calls.jsonl"
    model = ScriptedRealModelAdapter(
        strategy="responses", responses=['{"proposals": []}'],
        model_id="w6o", call_account_path=account)
    store = PollutantPathwayStore(
        runs_root / run_id / "pollutant.sqlite")
    ledger = SearchLedger(store, ArtifactStore(runs_root, run_id),
                          run_id)
    ledger.register_search_run(run_id, _policy_block(8))
    action_id = _claimed_decide_action(ledger, run_id)
    request_key = f"decide:{action_id}"
    request = ledger.register_model_request(
        run_id=run_id, action_id=action_id, attempt_id="",
        provider_kind="scripted", request_key=request_key,
        purpose="proposals", payload={"prompt_digest": "x"})
    ledger.record_request_sent(str(request["request_id"]))
    with pytest.raises(RealModelTransportFailure):
        model.ppv1_real_fetch(
            ledger=ledger, run_id=run_id, action_id=action_id,
            attempt_id="",
            prompt_payload={"substrate_smiles": "CCO",
                            "atom_id_map": {}, "pool_entries": []},
            request_key=request_key, purpose="proposals",
            provider_kind="scripted", request=request)
    # 无 retry_of 新请求(总请求数不变)
    count = ledger.conn.execute(
        "SELECT COUNT(*) FROM model_requests WHERE run_id = ?",
        (run_id,)).fetchone()[0]
    assert int(count) == 1
    # 账本披露:orphan failed,无新 logical
    lines = [json.loads(x) for x in
             account.read_text(encoding="utf-8").splitlines() if x]
    assert any("orphan_marked_failed" in str(l.get("status"))
               for l in lines)
    # 模型身份含 retry/timeout 参数(R5)
    block = model.identity_block()
    assert "max_http_retries" in block
    assert "timeout_s" in block


def test_w6_r4_case_reader_validation(tmp_path) -> None:
    """R4:validated case reader —— 坏 completed(外 qid/错 run_id/
    缺 schema/env_check_only 冒正式)拒;合法终态过;原子写。"""
    from pathway_v43.pollutant.s5b_orchestrator import (
        read_case,
        read_validated_case,
        validate_case,
        write_case_atomic,
    )

    batch_root = tmp_path / "batch"
    good = {"qid": "Q1", "run_id": "r1", "status": "completed",
            "case_schema_version": "s5b-case-1",
            "stop_reason": "exhausted_search", "export_digest": "d"}
    write_case_atomic(batch_root / "cases" / "Q1.json", good)
    assert read_validated_case(
        batch_root, "Q1", expected_run_id="r1") is not None
    # 外 qid
    assert validate_case(good, "Q2")["ok"] is False
    # 错 run_id
    assert validate_case(good, "Q1", expected_run_id="other")["ok"] \
        is False
    # 缺 schema
    assert validate_case({**good, "case_schema_version": ""}, "Q1")[
        "ok"] is False
    # completed 无 stop_reason
    assert validate_case({**good, "stop_reason": ""}, "Q1")["ok"] \
        is False
    # env_check_only 不算正式 completed(另一文件语义)
    assert validate_case({**good, "stop_reason": "env_check_only"},
                         "Q1")["ok"] is False
    # 坏 case strict 拒(fail-closed)
    write_case_atomic(batch_root / "cases" / "Q2.json",
                      {**good, "qid": "Q2", "run_id": "other-run"})
    with pytest.raises(Exception) as excinfo:  # noqa: B017
        read_validated_case(batch_root, "Q2", expected_run_id="r1")
    assert getattr(excinfo.value, "detail", {}).get("kind") == \
        "s5b_case_validation_failed"
    # 非终态(pending)返回 None 不抛
    write_case_atomic(batch_root / "cases" / "Q3.json",
                      {**good, "qid": "Q3", "status": "pending"})
    assert read_validated_case(batch_root, "Q3") is None


def test_w6_r5_worker_timeout_negative_rejected(tmp_path) -> None:
    """R5:worker_timeout_s 负值 ⇒ 结构化拒(0=禁用;正值=monotonic
    总时限)。"""
    from pathway_v43.pollutant.s5b_orchestrator import (
        S5bOrchestratorError,
        run_s5b_batch,
    )

    manifest = tmp_path / "batch"
    manifest.mkdir()
    (manifest / "batch_manifest.json").write_text(json.dumps({
        "registration_order": [], "entries": []}),
        encoding="utf-8")
    with pytest.raises(S5bOrchestratorError) as excinfo:
        run_s5b_batch(manifest, runs_root=tmp_path / "runs",
                      worker_timeout_s=-1.0)
    assert excinfo.value.detail["kind"] == "s5b_worker_timeout_invalid"


def test_w6_r5_defaults_one_logical_and_1490_cap() -> None:
    """R5:缺省配置 = 1 logical/qid、format_feedback 0、gate cap
    1490(298×1×5 理论上限;新配置数值)。"""
    from pathway_v43.pollutant.s5b_orchestrator import (
        S5B_DEFAULT_GATE_MAX_CALLS,
        S5B_DEFAULT_PROFILE_POLICY,
    )

    assert S5B_DEFAULT_PROFILE_POLICY["search_limits"][
        "max_real_model_requests"] == 1
    assert S5B_DEFAULT_PROFILE_POLICY["format_feedback_policy"][
        "max_format_feedback_rounds"] == 0
    assert S5B_DEFAULT_GATE_MAX_CALLS == 1490


# ================================================================ 版本

def test_versions_registered() -> None:
    # W-V4b:s5b-recorded-source-2(推断映射预算/枚举面扩展)
    assert RECORDED_SOURCE_VERSION == "s5b-recorded-source-2"
    # W-V4b:池策略升版(池成员变化:recorded 两通道编译面扩大;
    # 配置本身零变化;s5b-pool-policy-4)
    assert S5B_POOL_POLICY_VERSION == "s5b-pool-policy-4"
    assert S5B_RANK_POLICY_VERSION == "s5b-rank-policy-1"
    assert S5B_POOL_RAW_TOP == 24
    assert "approved" in PREREG_APPROVAL_APPROVED_STATUSES
