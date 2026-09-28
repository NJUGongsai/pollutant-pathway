"""预测工作流 e2e(假模型,无凭证)— 验收 §5.2/§5.3/§5.4。

- rank_candidates:模型只能选择既有反应;多产物同一事件;未选候选+理由留痕;
  唯一 recorded 不触发 LLM;
- analogy_edit:可核对供体映射 + MoleCode 往返;缺映射不得假成功;
- novel_proposal:受约束提案;无效产物逐个拒因,不污染账本;
- 解析失败/非法证据 ID/预算:显式结果与停留,不谎称预测完成。
"""

from __future__ import annotations

import json

from pathway_v43.domain.identity import cn_identity
from pathway_v43.services.prediction import PREDICTION_MODE_ANALOGY

from wf_helpers import (
    CATECHOL,
    evidence,
    fake_model,
    load_report,
    novel_response,
    rank_response,
    run_scripted,
)

S = cn_identity(CATECHOL)
P1 = cn_identity("O=CCC=CO")
Q = cn_identity("O=CCO")
ALCOHOL = "CCCCCO"
A = cn_identity(ALCOHOL)
ALDEHYDE = "CCCCC=O"
B = cn_identity(ALDEHYDE)
REAL_DONOR_RECORD = "env:EAWAG-BBD:bt0001#r0022"  # 辛醇→辛醛(mapped_bijection)


def rec(rid, reactant, prods, **kw):
    return evidence(rid, "recorded_reaction", reactant, prods, **kw)


def rule(rid, reactant, prods):
    return evidence(rid, "rule_application", reactant, prods,
                    match_type="rule_template")


def _prediction_payload(runs_root, run_id):
    out = []
    base = runs_root / run_id / "results"
    for d in sorted(base.iterdir()):
        p = d / "prediction.json"
        if p.is_file():
            out.append(json.loads(p.read_text(encoding="utf-8"))["payload"])
    return out


# --------------------------------------------------------------- §5.2


def test_rank_selects_recorded_multi_product_one_event(tmp_path):
    """验收 5.2:竞争裁决——选中的反应多产物同一事件;未选候选与理由留痕。"""
    scripted = {
        S: [rec("bt0001#r0001", S, ["O=CCC=CO", "CC(O)=O"]),
            rec("bt0002#r0002", S, ["O=C=O"])],
        P1: [],   # 产物路径无证据 → dead_end(确定性检索,不进模型)
    }
    model = fake_model(script={
        "rank_candidates": [rank_response(
            "E-bt0001#r0001",
            reasons={"E-bt0002#r0002": "证据较少,暂不选用"},
            reason="选 1 号:证据更充分")],
    })
    summary, runs = run_scripted("rank1", scripted, max_depth=1,
                                 runs_root=tmp_path, model=model)
    assert summary["counts"]["reaction_events"] == 1
    assert summary["counts"]["event_products"] == 2  # 多产物同一事件
    report = load_report(runs, "rank1")
    ev = report["reaction_events"][0]
    assert [p["product_smiles"] for p in ev["products"]] == [
        "O=CCC=CO", "CC(O)=O"]
    assert [p["position"] for p in ev["products"]] == [0, 1]
    # 模型决策引用入事件(可审计)
    assert ev["model_ref"].startswith("prediction:")
    # 未选候选与理由在 prediction.json 与报告中
    preds = _prediction_payload(runs, "rank1")
    assert preds[0]["outcome"] == "selected"
    assert preds[0]["reasons"]["E-bt0002#r0002"] == "证据较少,暂不选用"
    view = report["path_instances"][0]["prediction"]
    assert view["selected_evidence_id"] == "E-bt0001#r0001"
    assert view["reasons"]["E-bt0002#r0002"]


def test_single_recorded_never_calls_model(tmp_path):
    """验收 5.2:唯一已记录反应确定性直通,LLM 计数为零(max_depth=1 使
    子路径不探索;novel 提案通路由此不被触发)。"""
    counter = tmp_path / "llm_counter.txt"
    scripted = {S: [rec("btR1", S, [P1])]}
    model = fake_model(script={}, counter_path=counter)
    summary, _ = run_scripted("rank2", scripted, max_depth=1,
                              runs_root=tmp_path, model=model)
    assert summary["stop_reason"] == "completed"
    assert summary["counts"]["reaction_events"] == 1
    assert not counter.exists(), "唯一 recorded 不得触发任何模型调用"
    assert summary["budget"]["used_llm_calls"] == 0


# --------------------------------------------------------------- §5.3


def _donor_fixture_card(substrate_identity: str) -> dict:
    """带真实可追溯供体的类比卡(供体来自 analog corpus 稳定 record_id)。"""
    from pathway_v43.config import resolve_config
    from pathway_v43.services.analog_source import AnalogSourceResolver

    resolver = AnalogSourceResolver(resolve_config())
    ref = resolver.resolve_template(REAL_DONOR_RECORD)
    ref = resolver.align(ref, ALCOHOL)  # 全供体失败 → 反应中心(CH2-OH)对齐
    assert ref.alignment is not None
    return evidence("src-analog", "analog_reaction", substrate_identity,
                    [ALDEHYDE], match_type="retrieval_neighbor_transfer",
                    extra={"donor_refs": [ref.to_dict()],
                           "mapping_status": "resolved",
                           "mapping_reason":
                               "unique_mapped_template_aligned"})


def test_analogy_edit_end_to_end_with_roundtrip(tmp_path):
    """验收 5.3a(Phase C):门禁适用的供体 → analogy_edit;编辑在图上
    顺序执行并与目标 MoleCode 逐项对账。"""
    scripted = {
        S: [rec("btR1", S, [ALCOHOL])],  # 唯一 recorded → 确定性直通到 S11(A)
        A: [_donor_fixture_card(A)],
    }
    # 供体转换 = 伯醇氧化为醛;模型给出显式键级编辑(端 C–O single→double)
    from pathway_v43.services.atom_tool import render

    render_a = render(ALCOHOL, name="S")
    c_end = next(a for a in render_a.atom_ids if "_C_" in a
                 and render_a.atom_id_map[a] == max(
                     i for aid, i in render_a.atom_id_map.items()
                     if "_C_" in aid))
    o_end = next(a for a in render_a.atom_ids if "_O_" in a)
    target = render(ALDEHYDE, name="S").molecode
    model = fake_model(script={
        "analogy_edit": [json.dumps({
            "decision": "apply", "target_molecode": target,
            "edits": [{"op": "change_bond_order", "atom1": c_end,
                       "atom2": o_end, "from_order": "single",
                       "to_order": "double"}],
            "referenced_evidence_id": "E-src-analog",
            "reason": "把供体的醇氧化迁移到当前分子",
        })],
    }, default_by_mode={
        # 类比产物路径继续探索时:模型弃权(合法结果,聚焦本用例)
        "novel_proposal": json.dumps({
            "decision": "abstain", "reason": "无进一步可说转换"}),
    })
    summary, runs = run_scripted(
        "ana1", scripted, max_depth=2, max_expansions=4,
        runs_root=tmp_path, model=model)
    assert summary["counts"]["reaction_events"] == 2  # 根 recorded + 类比提案
    report = load_report(runs, "ana1")
    ev = next(e for e in report["reaction_events"]
              if e["kind"] == "analog_reaction")  # S11 上的类比事件
    # 预测挂牌:kind=analog_reaction + model_ref + score_semantics 非校准
    assert ev["model_ref"].startswith("prediction:")
    assert ev["products"][0]["product_identity"] == B
    preds = _prediction_payload(runs, "ana1")
    card = preds[0]["proposed_card"]
    assert card["score_semantics"] == (
        "model_proposal_qualitative_only_no_calibrated_probability")
    assert card["source_record"]["donor"]["record_id"] == REAL_DONOR_RECORD
    assert card["source_record"]["donor"]["asset_sha256"]
    # AtomTool 核验结果随卡留痕:结构校验/执行/目标对账三段全过
    checks = card["source_record"]["atomtool_checks"]
    assert checks["edit_validation"]["ok"]
    assert checks["edit_execution"]["ok"]
    assert checks["edit_execution"]["product_smiles"] == ALDEHYDE
    assert checks["target_consistency"]["ok"]
    # donor 块携带资格与变换表(任务书 v3)
    assert card["source_record"]["donor"]["alignment"]["strategy"]
    task = json.loads(next(
        (runs / "ana1" / "results").glob("*/prediction_task.json")
    ).read_text())["payload"]
    assert task["donor"]["applicability"]["status"] == "applicable"
    assert task["donor"]["transform"]["bond_changes"]
    assert task["schema_version"] == "v43-prediction-task-3"


def test_analogy_missing_mapping_cannot_fake_success(tmp_path):
    """验收 5.3b:不可映射类比不得进入类比编辑;策略路由 novel 并留拒因。"""
    unmapped = evidence("src-analog-bad", "analog_reaction", P1, [Q],
                        match_type="retrieval_neighbor_transfer",
                        extra={"mapping_status": "unavailable",
                               "mapping_reason":
                                   "no_mapped_template:traceability_only"})
    scripted = {S: [rec("btR1", S, [P1])], P1: [unmapped]}
    model = fake_model(script={
        # 即使模型想装作类比编辑,也拿不到类比任务:路由走 novel
        "analogy_edit": [json.dumps({"decision": "apply",
                                     "target_molecode": "graph TB",
                                     "reason": "假成功企图"})],
    }, default_by_mode={
        "novel_proposal": novel_response(
            [{"smiles": "O=CCO", "note": "氧化"}], reason="受约束提案"),
    })
    summary, runs = run_scripted("ana2", scripted, max_depth=2,
                                 max_expansions=4, runs_root=tmp_path,
                                 model=model)
    preds = _prediction_payload(runs, "ana2")
    assert all(p["mode"] != PREDICTION_MODE_ANALOGY for p in preds), \
        "缺映射不得进入 analogy_edit"
    assert preds and preds[0]["mode"] == "novel_proposal"
    assert summary["counts"]["reaction_events"] == 2  # 根 + novel 提案
    task = json.loads(next(
        (runs / "ana2" / "results").glob("*/prediction_task.json")
    ).read_text())["payload"]
    assert task["policy_version"]


def test_hold_stays_awaiting_with_model_reason(tmp_path):
    """rank 模型 hold → 显式停留待预测,理由入账,不产生事件。"""
    scripted = {
        S: [rec("bt1", S, [P1]), rec("bt2", S, [Q])],
    }
    model = fake_model(script={
        "rank_candidates": [json.dumps({
            "decision": "hold",
            "reason": "两条记录条件都不明,暂不选择"})],
    })
    summary, runs = run_scripted("rank3", scripted, runs_root=tmp_path,
                                 model=model)
    assert summary["counts"]["reaction_events"] == 0
    report = load_report(runs, "rank3")
    root = report["path_instances"][0]
    assert root["status"] == "awaiting_prediction"
    assert "model_hold" in root["status_reason"]
    assert "暂不选择" in root["status_reason"]


# --------------------------------------------------------------- §5.4


def test_novel_invalid_products_rejected_with_reasons(tmp_path):
    """验收 5.4:提案中无效产物逐个拒因(价态/凭空元素/循环/重复),
    有效产物保留来源入账;位次稀疏不重排。"""
    bad_valence = "C(C)(C)(C)(C)C"       # 价态非法
    new_cl = "ClCCCCCO"                  # 凭空 +Cl(不在白名单)
    cycle = ALCOHOL                      # 回到当前底物(祖先)
    dup = ALDEHYDE                       # 与产物 0 重复
    scripted = {A: [rule("btR1", A, [ALDEHYDE])]}  # 仅规则 → 映射不可用 → novel
    model = fake_model(default_by_mode={
        "novel_proposal": novel_response([
            {"smiles": ALDEHYDE, "note": "氧化"},      # pos0 有效
            {"smiles": bad_valence, "note": "价态坏"},  # pos1 拒
            {"smiles": new_cl, "note": "凭空 Cl"},      # pos2 拒
            {"smiles": cycle, "note": "回底物"},        # pos3 拒
            {"smiles": dup, "note": "重复"},            # pos4 拒
        ]),
    })
    summary, runs = run_scripted("nov1", scripted, smiles=ALCOHOL,
                                 max_depth=1, runs_root=tmp_path, model=model)
    assert summary["counts"]["reaction_events"] == 1
    assert summary["counts"]["event_products"] == 1
    report = load_report(runs, "nov1")
    ev = report["reaction_events"][0]
    # 有效产物保持原始位次 0;被拒位次稀疏不重排
    assert [p["position"] for p in ev["products"]] == [0]
    assert ev["kind"] == "novel_proposal"
    child = [p for p in report["path_instances"] if p["depth"] == 1][0]
    assert child["status"] == "depth_limit"  # max_depth=1:产物路径不再探索
    # 拒因逐条留痕在 validation 产物
    vtask = next((runs / "nov1" / "results").glob("*/validation.json"))
    verdicts = json.loads(vtask.read_text())["payload"]["verdicts"]
    reasons = {v["position"]: v["reasons"] for v in verdicts}
    assert any("unparseable" in r for r in reasons[1])
    assert any("element_change_not_justified:Cl" in r for r in reasons[2])
    assert any("in_path_cycle" in r for r in reasons[3])
    assert any("sibling_dedup" in r for r in reasons[4])
    # 元素 delta 例外依据随校验留痕
    assert verdicts[2]["exceptions"]["element_delta"] == {"Cl": 1}


def test_parse_failure_retries_then_explicit_stop(tmp_path):
    """解析失败重试有上限;失败后显式停留(不假成功),拒因留痕。"""
    counter = tmp_path / "llm_counter.txt"
    scripted = {S: [rule("btR1", S, [P1])], P1: []}
    model = fake_model(script={
        "novel_proposal": ["这不是 JSON", "也不是", "{\"decision\": \"propose\""],
    }, counter_path=counter)
    summary, runs = run_scripted("pf1", scripted, runs_root=tmp_path,
                                 model=model)
    assert counter.read_text() == "3"  # 首次 + 2 次重试(上限)
    assert summary["counts"]["reaction_events"] == 0
    report = load_report(runs, "pf1")
    root = report["path_instances"][0]
    assert root["status"] == "awaiting_prediction"
    assert "prediction_failed" in root["status_reason"]


def test_invalid_evidence_id_never_commits(tmp_path):
    """模型引用不存在的证据 ID → 解析显式失败 → 重试后停留,零事件。"""
    scripted = {S: [rec("bt1", S, [P1]), rec("bt2", S, [Q])]}
    model = fake_model(script={
        "rank_candidates": [rank_response("E-fabricated"),
                            rank_response("E-also-fake")],
    })
    summary, _ = run_scripted("pf2", scripted, runs_root=tmp_path, model=model)
    assert summary["counts"]["reaction_events"] == 0
    assert summary["stop_reason"] == "awaiting_prediction"


def test_novel_abstain_is_a_valid_dead_end(tmp_path):
    """无证据且模型弃权(合法结果)→ dead_end,理由为模型说明。"""
    scripted = {S: []}
    model = fake_model(default_by_mode={
        "novel_proposal": json.dumps({
            "decision": "abstain",
            "reason": "当前分子没有说得通的下一步"}),
    })
    summary, runs = run_scripted("abst1", scripted, runs_root=tmp_path,
                                 model=model)
    assert summary["counts"]["reaction_events"] == 0
    report = load_report(runs, "abst1")
    root = report["path_instances"][0]
    assert root["status"] == "dead_end"
    assert "没有说得通的下一步" in root["status_reason"]


def test_llm_budget_exhaustion_stops_run(tmp_path):
    """LLM 预算耗尽 → run 明确停在 budget_exhausted,不再调用。"""
    counter = tmp_path / "llm_counter.txt"
    scripted = {S: [rule("btR1", S, [P1])], P1: []}
    model = fake_model(counter_path=counter)  # 无剧本:每次调用空响应
    summary, runs = run_scripted(
        "lb1", scripted, max_expansions=5, max_llm_calls=1,
        runs_root=tmp_path, model=model)
    assert counter.read_text() == "1"
    assert summary["stop_reason"] == "budget_exhausted"
    assert summary["budget"]["used_llm_calls"] == 1
    assert summary["counts"]["reaction_events"] == 0
