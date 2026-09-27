"""EC298 外考工具验收(TASK_V43_EC298 §2/§4/§5.1)。

- 白名单一次性提取与金标隔离(存在拒绝重写;字段恰好三项);
- 冻结评分器:cn 身份、电荷双形态、多金标组件、重复候选、rank 边界、
  空/部分答卷计入分母、agent hit@10 == hit@5 标注;
- 闸门 max_in_flight:同时在途上限与峰值持久证据。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pathway_v43.adapters.rate_gate import FileRateGate  # noqa: E402
from pathway_v43.domain.identity import cn_identity  # noqa: E402
from pathway_v43.exam import (  # noqa: E402
    ExamError,
    build_exam_inputs,
    load_exam_inputs,
    score_exam,
)

QID = "RXNG_" + "a" * 60


def _questions_file(tmp_path: Path) -> Path:
    rows = [
        {"qid": QID, "category": "pharmaceutical",
         "substrate_smiles": "CCO",
         "products_smiles": ["CC=O", "O"],
         "raw_reaction": "CCO>>CC=O", "ambiguous_substrate": False},
        {"qid": "RXNG_" + "b" * 60, "category": "agrochemical",
         "substrate_smiles": "CCC(C)O",
         "products_smiles": ["CCC(C)=O"], "raw_reaction": "x>>y",
         "ambiguous_substrate": True},
    ]
    p = tmp_path / "questions.jsonl"
    p.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n"
                         for r in rows), encoding="utf-8")
    return p


# ------------------------------------------------------------ 输入隔离


def test_exam_whitelist_one_shot_and_isolated(tmp_path):
    q = _questions_file(tmp_path)
    out = tmp_path / "exam_inputs.jsonl"
    meta = build_exam_inputs(q, out)
    assert meta["n_questions"] == 2
    assert meta["n_unique_qids"] == 2
    rows = load_exam_inputs(out)
    assert rows[0]["input_index"] == 0
    assert set(rows[0]) == {"input_index", "qid", "substrate_smiles"}
    text = out.read_text(encoding="utf-8")
    assert "CC=O" not in text, "金标产物不得进入白名单"
    assert "category" not in text and "raw_reaction" not in text
    # 一次性:存在即拒绝重写
    with pytest.raises(ExamError):
        build_exam_inputs(q, out)


def test_exam_whitelist_rejects_duplicate_qids(tmp_path):
    p = tmp_path / "q.jsonl"
    row = {"qid": QID, "substrate_smiles": "CCO", "products_smiles": []}
    p.write_text(json.dumps(row) + "\n" + json.dumps(row) + "\n",
                 encoding="utf-8")
    with pytest.raises(ExamError):
        build_exam_inputs(p, tmp_path / "wl.jsonl")


# ------------------------------------------------------------ 评分器


def _pred_file(tmp_path: Path, rows: list[dict]) -> Path:
    p = tmp_path / "predictions.jsonl"
    p.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n"
                         for r in rows), encoding="utf-8")
    return p


def _gold_file(tmp_path: Path) -> Path:
    return _questions_file(tmp_path)


def test_scorer_cn_identity_charge_aware(tmp_path):
    """阴离子金标 vs 中性候选:cn 口径 hit;hit@K 边界正确。"""
    qid2 = "RXNG_" + "b" * 60
    rows = [
        {"route_id": QID, "root_smiles": "CCO", "steps": [
            {"parent_smiles": "CCO",
             "predicted_products": ["CC(=O)O", "CCC"]}]},
        {"route_id": qid2, "root_smiles": "CCC(C)O", "steps": []},
    ]
    # 金标改为阴离子产物:预测的中性形按 cn 口径同身份命中
    gold = tmp_path / "gold.jsonl"
    gold.write_text(json.dumps({
        "qid": QID, "category": "pharmaceutical", "substrate_smiles": "CCO",
        "products_smiles": ["CC(=O)[O-]"]}) + "\n" + json.dumps({
        "qid": qid2, "category": "agrochemical",
        "substrate_smiles": "CCC(C)O", "products_smiles": ["CCC(C)=O"]})
        + "\n", encoding="utf-8")
    pred = _pred_file(tmp_path, rows)
    result = score_exam(agent_predictions_path=pred,
                        engine_results_path=None,
                        gold_questions_path=gold,
                        out_path=tmp_path / "scored.json")
    assert result["per_question"][0]["agent_rank"] == 1
    s = result["summary"]
    assert s["n_questions"] == 2
    assert s["agent"]["hit@1"] == 1
    assert s["agent"]["hit@5"] == 1
    # 空答卷(qid2)计入分母:hit@1 = 1/2
    assert abs(s["agent"]["hit@1"] / s["n_questions"] - 0.5) < 1e-9


def test_scorer_rank_boundary_and_duplicates(tmp_path):
    """rank=6 不计 hit@5;重复候选保留首现排名;多金标任一命中即取首个。"""
    products = ["P1", "P2", "P3", "P4", "P5", "P6", "P2"]  # P2 重复于第 7
    pred_products = []
    for i, p in enumerate(products):
        pred_products.append(f"{'C' * (i + 2)}O" if p != "P2"
                             else "CCO")
    # 金标 = 第 6 位产物:hit@5 miss、hit@10(引擎侧)hit
    qid2 = "RXNG_" + "b" * 60
    gold = tmp_path / "gold.jsonl"
    gold.write_text(json.dumps({
        "qid": QID, "category": "x", "substrate_smiles": "CCO",
        "products_smiles": [pred_products[5]]}) + "\n" + json.dumps({
        "qid": qid2, "category": "y", "substrate_smiles": "CCC(C)O",
        "products_smiles": ["CCC(C)=O"]}) + "\n", encoding="utf-8")
    rows = [{"route_id": QID, "root_smiles": "CCO", "steps": [
        {"parent_smiles": "CCO", "predicted_products": pred_products}]},
        {"route_id": qid2, "root_smiles": "CCC(C)O", "steps": [
            {"parent_smiles": "CCC(C)O",
             "predicted_products": ["CCC(C)=O"]}]}]
    pred = _pred_file(tmp_path, rows)
    result = score_exam(agent_predictions_path=pred,
                        engine_results_path=None,
                        gold_questions_path=gold,
                        out_path=tmp_path / "scored.json")
    q0 = result["per_question"][0]
    assert q0["agent_rank"] == 6
    q1 = result["per_question"][1]
    assert q1["agent_rank"] == 1
    s = result["summary"]
    # hit@5 = 1(qid2),hit@1 = 1
    assert s["agent"]["hit@1"] == 1 and s["agent"]["hit@5"] == 1


def test_scorer_agent_hit10_equals_hit5_annotated(tmp_path):
    gold = _gold_file(tmp_path)
    step1 = {"parent_smiles": "CCO", "predicted_products": ["CC=O"]}
    step2 = {"parent_smiles": "CCC(C)O",
             "predicted_products": ["CCC(C)=O"]}
    rows = [
        {"route_id": QID, "root_smiles": "CCO", "steps": [step1]},
        {"route_id": "RXNG_" + "b" * 60, "root_smiles": "CCC(C)O",
         "steps": [step2]},
    ]
    pred = _pred_file(tmp_path, rows)
    result = score_exam(agent_predictions_path=pred,
                        engine_results_path=None, gold_questions_path=gold,
                        out_path=tmp_path / "scored.json")
    a = result["summary"]["agent"]
    assert a["hit@10"] == a["hit@5"]
    assert "输出宽度上限" in a["hit@10_note"]


def test_scorer_pool_tiers_by_engine_pool(tmp_path):
    """三档诊断:Top-10 内 / 池内 Top-10 外 / 池内无金标。"""
    gold = _gold_file(tmp_path)
    qid2 = "RXNG_" + "b" * 60
    engine_rows = [
        # qid1:top10 第 2 位含金标 CC=O
        {"qid": QID, "status": "ok",
         "top10": [{"engine_rank": 1, "product_identity": cn_identity("CCC"),
                    "product_smiles": "CCC"},
                   {"engine_rank": 2,
                    "product_identity": cn_identity("CC=O"),
                    "product_smiles": "CC=O"}],
         "pool_identities": [cn_identity("CCC"), cn_identity("CC=O")]},
        # qid2:top10 无金标,但池内第 11 位有
        {"qid": qid2, "status": "ok",
         "top10": [{"engine_rank": i + 1,
                    "product_identity": cn_identity(f"CC{'C' * (i + 2)}O"),
                    "product_smiles": f"CC{'C' * (i + 2)}O"}
                   for i in range(10)],
         "pool_identities": [cn_identity(f"CC{'C' * (i + 2)}O")
                             for i in range(11)]
         + [cn_identity("CCC(C)=O")]},
    ]
    eng = tmp_path / "engine_results.jsonl"
    eng.write_text("".join(json.dumps(r) + "\n" for r in engine_rows),
                   encoding="utf-8")
    rows = [
        {"route_id": QID, "root_smiles": "CCO",
         "steps": [{"parent_smiles": "CCO", "predicted_products": ["CCC"]}]},
        {"route_id": qid2, "root_smiles": "CCC(C)O", "steps": []},
    ]
    pred = _pred_file(tmp_path, rows)
    result = score_exam(agent_predictions_path=pred,
                        engine_results_path=eng, gold_questions_path=gold,
                        out_path=tmp_path / "scored.json")
    tiers = result["summary"]["pool_tiers"]
    assert tiers["gold_in_top10"] == 1
    assert tiers["gold_in_pool_beyond_top10"] == 1
    assert result["per_question"][0]["engine_rank"] == 2
    assert result["per_question"][1]["engine_rank"] is None


def test_scorer_rejects_unknown_qid(tmp_path):
    gold = _gold_file(tmp_path)
    rows = [{"route_id": "RXNG_unknown", "root_smiles": "CCO",
             "steps": []}]
    pred = _pred_file(tmp_path, rows)
    with pytest.raises(ExamError):
        score_exam(agent_predictions_path=pred, engine_results_path=None,
                   gold_questions_path=gold,
                   out_path=tmp_path / "scored.json")


# ------------------------------------------------------------ 在途上限


def test_gate_max_in_flight_blocks_and_records_peak(tmp_path):
    gate = FileRateGate(tmp_path / "gate", rpm=10_000, tpm=10**9,
                        max_calls=100, max_in_flight=2,
                        acquire_timeout_s=5.0)
    g1 = gate.acquire()
    g2 = gate.acquire()
    assert g1["in_flight"] == 1 and g2["in_flight"] == 2
    snap = gate.snapshot()
    assert snap["in_flight"] == 2 and snap["peak_in_flight"] == 2
    assert snap["max_in_flight"] == 2
    gate.record_response(status=200, usage={"total_tokens": 10})
    gate.record_response(status=200, usage={"total_tokens": 10})
    snap = gate.snapshot()
    assert snap["in_flight"] == 0 and snap["peak_in_flight"] == 2


def test_gate_default_backcompat_no_inflight_limit(tmp_path):
    gate = FileRateGate(tmp_path / "gate", rpm=10_000, tpm=10**9,
                        max_calls=100)
    assert gate.max_in_flight == 0
    g = gate.acquire()
    gate.record_response(status=200)
    assert gate.snapshot()["peak_in_flight"] == 1
