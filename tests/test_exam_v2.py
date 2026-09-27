"""exam_v2(Phase A 同口径重评分)单元测试。

锚点语义:引擎臂忽略缓存 product_identity、两臂统一从原始 SMILES 求
cn_identity;v1 引擎路径在缓存身份与原始 SMILES 冲突时必须失败、v2 通过。
"""

from __future__ import annotations

import json

import pytest

from pathway_v43.domain.identity import cn_identity
from pathway_v43.exam import score_exam as score_exam_v1
from pathway_v43.exam_v2 import (
    ScorerV2Error,
    first_hit_rank,
    multicomponent_sensitivity,
    score_exam_v2,
)


def _write_jsonl(path, rows):
    path.write_text(
        "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n"
                for r in rows), encoding="utf-8")


def _engine_row(qid, entries, status="ok", cache_from_raw=True):
    from pathway_v43.domain.identity import stereo_blind

    top10 = []
    for pos, raw in enumerate(entries, 1):
        top10.append({
            "engine_rank": pos,
            "product_smiles": raw,
            # 缓存身份字段:默认按"保留电荷的 canonical"伪造,复现 v1 口径差
            "product_identity": stereo_blind(raw) if cache_from_raw else raw,
            "cand_id": f"c{pos}", "source_id": "s", "kind": "k",
            "score": 1.0 / pos,
        })
    return {"qid": qid, "input_index": 0, "status": status,
            "top10": top10, "pool_identities": []}


def _agent_row(qid, products):
    return {"route_id": qid, "steps": [{"parent_smiles": "CCO",
                                        "predicted_products": products}]}


def _gold_row(qid, products, category="t"):
    return {"qid": qid, "category": category, "substrate_smiles": "CCO",
            "products_smiles": products}


@pytest.fixture()
def case(tmp_path):
    def build(*, gold, agent, engine):
        gold_p = tmp_path / "gold.jsonl"
        agent_p = tmp_path / "predictions.jsonl"
        engine_p = tmp_path / "engine_results.jsonl"
        _write_jsonl(gold_p, gold)
        _write_jsonl(agent_p, agent)
        _write_jsonl(engine_p, engine)
        return {"gold": gold_p, "agent": agent_p, "engine": engine_p}
    return build


def test_charged_neutral_same_identity():
    assert cn_identity("C[NH3+]") == cn_identity("CN")
    assert cn_identity("[O-]C=O") == cn_identity("OC=O")


def test_agent_hit_via_charged_candidate_and_v1_engine_fails_v2_passes(case,
                                                                       tmp_path):
    """缓存身份保留电荷时:v1 引擎路径漏检,v2 从原始 SMILES 重算命中。"""
    c = case(gold=[_gold_row("Q1", ["CN"])],
             agent=[_agent_row("Q1", ["C[NH3+]"])],
             engine=[_engine_row("Q1", ["C[NH3+]"])])
    v1 = score_exam_v1(agent_predictions_path=c["agent"],
                       engine_results_path=c["engine"],
                       gold_questions_path=c["gold"],
                       out_path=tmp_path / "v1.json")
    v2 = score_exam_v2(agent_predictions_path=c["agent"],
                       engine_results_path=c["engine"],
                       gold_questions_path=c["gold"],
                       out_path=tmp_path / "v2.json")
    q1 = next(q for q in v1["per_question"] if q["qid"] == "Q1")
    q2 = next(q for q in v2["per_question"] if q["qid"] == "Q1")
    assert q1["agent_rank"] == 1 and q2["agent_rank"] == 1
    assert q1["engine_rank"] is None      # v1:缓存身份未归一化 → 漏检
    assert q2["engine_rank"] == 1         # v2:原始 SMILES 重算 → 命中
    assert v2["summary"]["engine_top10"]["hit@1"] == 1


def test_wrong_cached_identity_cannot_create_hit(case, tmp_path):
    """缓存身份谎报命中而原始 SMILES 不含金标:v1 误检,v2 拒绝。"""
    c = case(gold=[_gold_row("Q1", ["CN"])],
             agent=[_agent_row("Q1", [])],
             engine=[{**_engine_row("Q1", ["CCC"]),
                      "top10": [{"engine_rank": 1, "product_smiles": "CCC",
                                 "product_identity": "CN"}]}])
    v1 = score_exam_v1(agent_predictions_path=c["agent"],
                       engine_results_path=c["engine"],
                       gold_questions_path=c["gold"],
                       out_path=tmp_path / "v1.json")
    v2 = score_exam_v2(agent_predictions_path=c["agent"],
                       engine_results_path=c["engine"],
                       gold_questions_path=c["gold"])
    assert next(q for q in v1["per_question"]
                if q["qid"] == "Q1")["engine_rank"] == 1  # v1 被缓存身份骗过
    assert next(q for q in v2["per_question"]
                if q["qid"] == "Q1")["engine_rank"] is None
    assert v2["summary"]["engine_top10"]["hit@1"] == 0


def test_multiple_gold_products_and_first_hit_rank(case):
    c = case(gold=[_gold_row("Q1", ["CCCC", "CCO"])],
             agent=[_agent_row("Q1", ["CCC", "CCO"])],
             engine=[_engine_row("Q1", ["CCC", "CCC(O)CC", "CCO"])])
    v2 = score_exam_v2(agent_predictions_path=c["agent"],
                       engine_results_path=c["engine"],
                       gold_questions_path=c["gold"])
    q = v2["per_question"][0]
    assert q["agent_rank"] == 2 and q["engine_rank"] == 3
    assert q["tier_v2"] == "engine_top10_hit"


def test_multicomponent_main_whole_string_sensitivity_any_component(case):
    c = case(gold=[_gold_row("Q1", ["CCO"])],
             agent=[_agent_row("Q1", ["CCO.CCO"])],
             engine=[_engine_row("Q1", ["CC.CCO"])])
    v2 = score_exam_v2(agent_predictions_path=c["agent"],
                       engine_results_path=c["engine"],
                       gold_questions_path=c["gold"])
    assert v2["per_question"][0]["agent_rank"] is None
    assert v2["per_question"][0]["engine_rank"] is None
    sens = multicomponent_sensitivity(agent_predictions_path=c["agent"],
                                      engine_results_path=c["engine"],
                                      gold_questions_path=c["gold"])
    row = sens["per_question"][0]
    assert row["agent_rank_sensitivity"] == 1
    assert row["engine_rank_sensitivity"] == 1
    assert sens["summary"]["exploratory"] is True
    assert sens["summary"]["n_affected_qids"] == 1


def test_duplicate_and_invalid_candidates_occupy_rank(case):
    c = case(gold=[_gold_row("Q1", ["CCO"])],
             agent=[_agent_row("Q1", ["C(", "CCO", "CCO"])],
             engine=[_engine_row("Q1", [])])
    v2 = score_exam_v2(agent_predictions_path=c["agent"],
                       engine_results_path=c["engine"],
                       gold_questions_path=c["gold"])
    # 不可解析候选占名次但不命中;命中按原始位置计数 → rank 2
    assert v2["per_question"][0]["agent_rank"] == 2
    assert v2["per_question"][0]["n_predicted"] == 3
    assert first_hit_rank(["CCO", "CCO"], {"CCO"}) == 1  # 重复候选首个命中


def test_k_boundaries_empty_answers_and_denominator(case):
    c = case(
        gold=[_gold_row("Q1", ["CCO"]), _gold_row("Q2", ["CCO"]),
              _gold_row("Q3", ["CCO"])],
        agent=[_agent_row("Q1", ["CCC", "CCC", "CCC", "CCC", "CCO"]),
               _agent_row("Q2", []), _agent_row("Q3", ["CCO"])],
        engine=[_engine_row("Q1", ["CCO"]),
                _engine_row("Q2", [], status="empty"),
                _engine_row("Q3", ["CCC"])])
    v2 = score_exam_v2(agent_predictions_path=c["agent"],
                       engine_results_path=c["engine"],
                       gold_questions_path=c["gold"])
    ranks = {q["qid"]: q for q in v2["per_question"]}
    assert ranks["Q1"]["agent_rank"] == 5      # 恰好第 5 位 → @5 计入
    assert ranks["Q2"]["agent_rank"] is None   # 空答计入分母
    assert ranks["Q2"]["engine_rank"] is None
    assert v2["summary"]["n_questions"] == 3
    assert v2["summary"]["agent"]["hit@3"] == 1
    assert v2["summary"]["agent"]["hit@5"] == 2
    assert v2["summary"]["agent"]["n_miss"] == 1
    assert v2["summary"]["tiers_v2"]["engine_top10_hit"] == 1
    assert v2["summary"]["tiers_v2"]["not_in_exported_top10"] == 2


def test_unknown_qid_fails_closed(case):
    c = case(gold=[_gold_row("Q1", ["CCO"])],
             agent=[_agent_row("Q9", ["CCO"])],
             engine=[_engine_row("Q1", [])])
    with pytest.raises(ScorerV2Error):
        score_exam_v2(agent_predictions_path=c["agent"],
                      engine_results_path=c["engine"],
                      gold_questions_path=c["gold"])


def test_duplicate_agent_qid_fails_closed(case):
    c = case(gold=[_gold_row("Q1", ["CCO"])],
             agent=[_agent_row("Q1", ["CCO"]), _agent_row("Q1", ["CCC"])],
             engine=[_engine_row("Q1", [])])
    with pytest.raises(ScorerV2Error):
        score_exam_v2(agent_predictions_path=c["agent"],
                      engine_results_path=c["engine"],
                      gold_questions_path=c["gold"])


def test_engine_qid_set_mismatch_fails_closed(case):
    c = case(gold=[_gold_row("Q1", ["CCO"]), _gold_row("Q2", ["CCO"])],
             agent=[_agent_row("Q1", ["CCO"]), _agent_row("Q2", ["CCO"])],
             engine=[_engine_row("Q1", ["CCO"])])  # 缺 Q2
    with pytest.raises(ScorerV2Error):
        score_exam_v2(agent_predictions_path=c["agent"],
                      engine_results_path=c["engine"],
                      gold_questions_path=c["gold"])


def test_score_v2_output_seals_inputs_sha(case, tmp_path):
    c = case(gold=[_gold_row("Q1", ["CCO"])],
             agent=[_agent_row("Q1", ["CCO"])],
             engine=[_engine_row("Q1", ["CCO"])])
    out = tmp_path / "score_v2.json"
    score_exam_v2(agent_predictions_path=c["agent"],
                  engine_results_path=c["engine"],
                  gold_questions_path=c["gold"],
                  out_path=out,
                  inputs_sha={"gold_questions": "abc123"})
    saved = json.loads(out.read_text(encoding="utf-8"))
    assert saved["summary"]["scorer_version"] == "v43-ec298-scorer-2"
    assert saved["inputs_sha256"] == {"gold_questions": "abc123"}
    assert len(saved["per_question"]) == 1


def test_diff_v1_v2_counts_and_trigger_fields(case, tmp_path):
    """v1↔v2 diff:v1 缓存口径漏检的题记 rank 变化,触发候选可回查。"""
    c = case(gold=[_gold_row("Q1", ["CN"]), _gold_row("Q2", ["CCO"])],
             agent=[_agent_row("Q1", ["C[NH3+]"]), _agent_row("Q2", ["CCO"])],
             engine=[_engine_row("Q1", ["C[NH3+]"]), _engine_row("Q2", ["CCO"])])
    v1_out = tmp_path / "v1.json"
    score_exam_v1(agent_predictions_path=c["agent"],
                  engine_results_path=c["engine"],
                  gold_questions_path=c["gold"], out_path=v1_out)
    v2 = score_exam_v2(agent_predictions_path=c["agent"],
                       engine_results_path=c["engine"],
                       gold_questions_path=c["gold"])
    from pathway_v43.exam_v2 import diff_v1_v2
    diff = diff_v1_v2(v1_scoring_path=v1_out, v2_result=v2,
                      engine_results_path=c["engine"],
                      agent_predictions_path=c["agent"])
    s = diff["summary"]
    assert s["n_questions"] == 2
    assert s["n_agent_rank_changed"] == 0     # 仅修引擎口径,agent 不变
    assert s["n_engine_rank_changed"] == 1
    assert s["n_engine_new_hit"] == 1 and s["n_engine_lost_hit"] == 0
    row = next(r for r in diff["rows"] if r["qid"] == "Q1")
    assert row["engine_rank_v1"] is None and row["engine_rank_v2"] == 1
    assert row["engine_trigger_smiles_raw"] == "C[NH3+]"
    assert row["engine_trigger_recomputed_identity"] == cn_identity("CN")
