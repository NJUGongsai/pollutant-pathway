"""phase_a_attribution(A1–A6 归因构建器)单元测试。

用合成封存树驱动加载器与构建器;锚点算术(分组、配对、孤儿、调用账)
与真实数据核对逻辑同源。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pathway_v43.exam_v2 import ScorerV2Error
from pathway_v43.phase_a_attribution import (
    build_agent_hits_by_engine_tier,
    build_awaiting_prediction_fates,
    build_decision_path_contribution,
    build_hit5_paired_attribution,
    build_llm_call_distribution,
    build_v41_baseline_diff,
    load_sealed_run_view,
)

RUN_PREFIX = "exam298_1328faf9_"


def _doc(payload):
    return {"schema_version": "t", "name": "t", "payload": payload}


def _make_run(root: Path, qid: str, *, stop: str, merged_products,
              decision=None, prediction=None, task=None, retrieval=None,
              adjudications=None, validations=None, calls=0, responses=0,
              orphan_call=False):
    run_id = RUN_PREFIX + qid
    rd = root / "agent_runs" / run_id
    res = rd / "results" / "T_1"
    res.mkdir(parents=True, exist_ok=True)
    (root / "agent_batch" / "workers").mkdir(parents=True, exist_ok=True)
    (root / "agent_batch" / "merged").mkdir(parents=True, exist_ok=True)
    (rd / "run_identity.json").write_text(json.dumps({"run_id": run_id}),
                                          encoding="utf-8")
    (root / "agent_batch" / "workers" / f"{qid}.status.json").write_text(
        json.dumps({"route_id": qid, "stop_reason": stop, "status": None}),
        encoding="utf-8")
    (res / "decision.json").write_text(
        json.dumps(_doc(decision or {})), encoding="utf-8")
    if prediction is not None:
        (res / "prediction.json").write_text(
            json.dumps(_doc(prediction)), encoding="utf-8")
    if task is not None:
        (res / "prediction_task.json").write_text(
            json.dumps(_doc(task)), encoding="utf-8")
    if retrieval is not None:
        (res / "retrieval.json").write_text(
            json.dumps(_doc(retrieval)), encoding="utf-8")
    for i, adj in enumerate(adjudications or []):
        (res / f"report_adjudication.json").write_text(
            json.dumps(_doc(adj)), encoding="utf-8")
    for i, val in enumerate(validations or []):
        (res / f"validation.json").write_text(
            json.dumps(_doc(val)), encoding="utf-8")
    for i in range(calls):
        (res / f"prediction_call.a{i + 1}.json").write_text(
            json.dumps(_doc({"attempt": i + 1, "status": "issued"})),
            encoding="utf-8")
        if not (orphan_call and i == calls - 1):
            (res / f"prediction_response.a{i + 1}.json").write_text(
                json.dumps(_doc({"attempt": i + 1,
                                 "transport": {"ok": True, "status": 200,
                                               "request_id": f"req{i + 1}"}})),
                encoding="utf-8")
    with (root / "agent_batch" / "merged" / "predictions.jsonl") \
            .open("a", encoding="utf-8") as f:
        f.write(json.dumps({"route_id": qid, "steps": [
            {"parent_smiles": "CCO", "predicted_products": merged_products}
        ]}) + "\n")


@pytest.fixture()
def view(tmp_path):
    root = tmp_path / "seal" / "runs" / "ec298_v43r1"
    root.mkdir(parents=True)
    questions = [{"input_index": i, "qid": f"RXNG_{i:04d}",
                  "substrate_smiles": "CCO"} for i in range(5)]
    (root / "exam_inputs.jsonl").write_text(
        "".join(json.dumps(q) + "\n" for q in questions), encoding="utf-8")

    # Q1 bypass:agent_only(引擎 Top-10 无金标),命中来源=裁决 E_A
    _make_run(root, "RXNG_0000", stop="completed", merged_products=["CCO"],
              decision={"prediction_mode": "", "outcome": "commit_recorded",
                        "accepted_evidence_id": "E_A"},
              adjudications=[{"evidence_kind": "recorded_reaction",
                              "entries": [{"evidence_id": "E_A",
                                           "product_smiles": "CCO",
                                           "report_rank": 1}]}],
              retrieval={"evidences": [
                  {"products": [{"product_smiles": "CCC"}]}]})
    # Q2 rank_candidates:engine_only,未选中 recorded 卡含金标 E_B
    _make_run(root, "RXNG_0001", stop="completed", merged_products=["CCC"],
              decision={"prediction_mode": "rank_candidates",
                        "outcome": "awaiting_prediction"},
              prediction={"mode": "rank_candidates", "outcome": "selected",
                          "parsed": {"selected_evidence_id": "E_A",
                                     "order": ["E_A", "E_B"],
                                     "products": ["CCC"]}},
              task={"mode": "rank_candidates", "candidates": [
                  {"evidence_id": "E_A", "kind": "recorded_reaction",
                   "products": [{"product_smiles": "CCC"}]},
                  {"evidence_id": "E_B", "kind": "recorded_reaction",
                   "products": [{"product_smiles": "CCO"}]}]},
              retrieval={"evidences": [
                  {"products": [{"product_smiles": "CCC"}]},
                  {"products": [{"product_smiles": "CCO"}]}]},
              adjudications=[{"evidence_kind": "recorded_reaction",
                              "entries": [{"evidence_id": "E_A",
                                           "product_smiles": "CCC",
                                           "report_rank": 1}]}],
              calls=1, responses=1)
    # Q3 analogy 弃答:engine_only,空答,awaiting_prediction
    _make_run(root, "RXNG_0002", stop="awaiting_prediction", merged_products=[],
              decision={"prediction_mode": "analogy_edit",
                        "outcome": "awaiting_prediction"},
              prediction={"mode": "analogy_edit", "outcome": "abstained",
                          "parsed": {"decision": "abstain", "reason": "骨架不匹配",
                                     "products": []}},
              calls=1, responses=1)
    # Q4 novel_proposal:agent_only,命中,检索有产物
    _make_run(root, "RXNG_0003", stop="completed", merged_products=["CCO"],
              decision={"prediction_mode": "novel_proposal",
                        "outcome": "awaiting_prediction"},
              prediction={"mode": "novel_proposal", "outcome": "proposed",
                          "parsed": {"products": ["CCO"],
                                     "selected_evidence_id": None}},
              task={"mode": "novel_proposal", "candidates": []},
              retrieval={"evidences": [
                  {"products": [{"product_smiles": "CCC"}]}]},
              adjudications=[{"evidence_kind": "novel_proposal",
                              "entries": [{"evidence_id": "E_N",
                                           "product_smiles": "CCO",
                                           "report_rank": 1}]}],
              calls=1, responses=1)
    # Q5 analogy 拒绝:budget_exhausted,孤儿调用(有 call 无 response)
    _make_run(root, "RXNG_0004", stop="budget_exhausted", merged_products=[],
              decision={"prediction_mode": "analogy_edit",
                        "outcome": "awaiting_prediction"},
              prediction={"mode": "analogy_edit", "outcome": "rejected",
                          "fail_reason": "bond_already_present",
                          "atomtool_checks": {
                              "target_molecode": {"ok": True},
                              "edit_references": {"ok": False}},
                          "parsed": {"reason": "键已存在"}},
              task={"mode": "analogy_edit", "budget": {"llm_remaining": 3}},
              calls=3, responses=2, orphan_call=True)
    merged_lines = (root / "agent_batch" / "merged"
                    / "predictions.jsonl").read_text().splitlines()
    (root / "agent_batch" / "merged" / "predictions.jsonl").write_text(
        "".join(l + "\n" for l in merged_lines), encoding="utf-8")
    gold = tmp_path / "gold.jsonl"
    gold.write_text("".join(json.dumps({
        "qid": f"RXNG_{i:04d}", "category": "t",
        "substrate_smiles": "CCO", "products_smiles": ["CCO"]}) + "\n"
        for i in range(5)), encoding="utf-8")
    scores = {"per_question": [
        {"qid": "RXNG_0000", "agent_rank": 1, "engine_rank": None,
         "n_predicted": 1, "tier_v2": "not_in_exported_top10"},
        {"qid": "RXNG_0001", "agent_rank": None, "engine_rank": 1,
         "n_predicted": 1, "tier_v2": "engine_top10_hit"},
        {"qid": "RXNG_0002", "agent_rank": None, "engine_rank": 2,
         "n_predicted": 0, "tier_v2": "engine_top10_hit"},
        {"qid": "RXNG_0003", "agent_rank": 1, "engine_rank": None,
         "n_predicted": 1, "tier_v2": "not_in_exported_top10"},
        {"qid": "RXNG_0004", "agent_rank": None, "engine_rank": 3,
         "n_predicted": 0, "tier_v2": "engine_top10_hit"},
    ]}
    return {"root": root, "gold": gold, "scores": scores}


def _gold_fn(view):
    from pathway_v43.exam_v2 import load_gold

    gold = load_gold(view["gold"])
    return lambda qid: gold[qid]["gold_ids"]


def test_loader_maps_runs_and_fails_closed(view, tmp_path):
    v = load_sealed_run_view(view["root"])
    assert len(v.runs) == 5 and len(v.questions) == 5
    assert v.runs["RXNG_0000"].decision_ref.endswith("decision.json")
    # 白名单缺 run → fail-closed
    bad = tmp_path / "bad"
    bad.mkdir()
    (bad / "exam_inputs.jsonl").write_text(json.dumps(
        {"input_index": 0, "qid": "RXNG_9999",
         "substrate_smiles": "CCO"}) + "\n", encoding="utf-8")
    with pytest.raises(ScorerV2Error):
        load_sealed_run_view(bad)


def test_a1_tier_and_hit_source(view):
    v = load_sealed_run_view(view["root"])
    rows, summary = build_agent_hits_by_engine_tier(
        v, view["scores"], _gold_fn(view))
    assert len(rows) == 5
    by = {r["qid"]: r for r in rows}
    assert by["RXNG_0000"]["tier_v2"] == "not_in_exported_top10"
    assert by["RXNG_0000"]["agent_hit_evidence_id"] == "E_A"
    assert by["RXNG_0000"]["agent_hit_ref_ok"] is True
    assert by["RXNG_0000"]["decision_mode"] == "recorded_direct"
    assert by["RXNG_0003"]["novel_evidence_state"] == \
        "retrieval_products_present"
    assert by["RXNG_0001"]["gold_in_retrieval_any_card"] is True
    tiers = {s["tier_v2"]: s["n_questions"] for s in summary}
    assert tiers == {"engine_top10_hit": 3, "not_in_exported_top10": 2}


def test_a2_fates_ledger_and_orphans(view):
    v = load_sealed_run_view(view["root"])
    rows, extra, audits = build_awaiting_prediction_fates(
        v, view["scores"])
    assert len(rows) == 1 and len(extra) == 1
    assert rows[0]["qid"] == "RXNG_0002"
    assert rows[0]["outcome"] == "abstained"
    assert rows[0]["n_issued"] == 1 and rows[0]["n_provider_ok"] == 1
    assert extra[0]["qid"] == "RXNG_0004"
    assert extra[0]["outcome"] == "rejected"
    assert extra[0]["orphan_count"] == 1
    assert extra[0]["atomtool_edit_references_ok"] is False
    assert audits["closed_loop_ok"] is True
    assert audits["outcomes"] == {"abstained": 1, "rejected": 1}
    assert audits["total_issued"] == 4 and audits["total_orphans"] == 1


def test_a3_groups_and_mode_agreement(view):
    v = load_sealed_run_view(view["root"])
    rows, detail, audits = build_decision_path_contribution(
        v, view["scores"])
    sizes = {(r["group"], r["subgroup"]): r["n_questions"] for r in rows}
    assert sizes[("recorded_direct", "commit_recorded")] == 1
    assert sizes[("rank_candidates", "selected")] == 1
    assert sizes[("analogy_edit", "analogy_abstained")] == 1
    assert sizes[("novel_proposal", "proposed")] == 1
    assert audits["n_mode_source_disagreements"] == 0
    rank_row = next(r for r in rows if r["group"] == "rank_candidates")
    assert rank_row["agent_hit@1"] == 0 and rank_row["engine_hit@1"] == 1
    assert rank_row["paired@5_engine_only"] == 1
    novel = next(r for r in rows if r["group"] == "novel_proposal")
    assert novel["agent_hit@5"] == 1 and novel["paired@5_agent_only"] == 1


def test_a4_discordant_labels(view):
    v = load_sealed_run_view(view["root"])
    rows, audits = build_hit5_paired_attribution(v, view["scores"],
                                                 _gold_fn(view))
    assert len(rows) == 5
    by = {r["qid"]: r for r in rows}
    assert by["RXNG_0001"]["direction"] == "engine_only"
    assert by["RXNG_0001"]["attribution_primary"] == "候选检出但未报告"
    assert "E_B" in by["RXNG_0001"]["unselected_recorded_with_gold"]
    assert by["RXNG_0002"]["attribution_primary"] == "类比弃答"
    assert by["RXNG_0004"]["attribution_primary"] == "编辑拒绝"
    assert by["RXNG_0000"]["direction"] == "agent_only"
    assert by["RXNG_0000"]["attribution_primary"] == "候选未检出"
    assert "未知" in by["RXNG_0000"]["attribution_uncertainty"]
    assert audits["paired_hit5_counts"]["engine_only"] == 3
    assert audits["paired_hit5_counts"]["agent_only"] == 2


def test_a5_baseline_diff(view, tmp_path):
    v41 = tmp_path / "v41.jsonl"
    v41.write_text("".join(json.dumps({
        "qid": f"RXNG_{i:04d}", "baseline_rank": 1 if i != 1 else None,
        "agent_rank": None}) + "\n" for i in range(5)), encoding="utf-8")
    rows, summary = build_v41_baseline_diff(view["scores"], v41)
    assert len(rows) == 5
    assert summary["v41_engine_hit@1/3/5/10"] == [4, 4, 4, 4]
    assert summary["n_rank_changed"] == 5  # 五题 v41 全为 rank1(除 Q1),v2 各异
    assert summary["v2_engine_hit@1/3/5/10"][0] == 1


def test_a6_call_distribution(view):
    v = load_sealed_run_view(view["root"])
    rows, summary = build_llm_call_distribution(v)
    assert summary["total_issued"] == 6
    assert summary["total_provider_ok"] == 5
    assert summary["total_failed"] == 0
    assert summary["total_orphans"] == 1
    assert summary["issued_histogram"] == {"0": 1, "1": 3, "3": 1}
    assert summary["touch_cap_qids"] == ["RXNG_0004"]
    by = {r["qid"]: r for r in rows}
    assert by["RXNG_0000"]["n_issued"] == 0
