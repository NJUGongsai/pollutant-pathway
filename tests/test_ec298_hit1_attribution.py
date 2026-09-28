"""EC298 hit@1 失分归因脚本测试(任务书 §5.3:负例必须能抓证据越层)。

全部基于合成夹具(临时目录),零网络、不依赖封存镜像与金标文件。
覆盖:
- classify_breakpoint 纯函数的标签规则与互斥性;
- 迷你封存布局端到端(命中题排除/五层取证/断点指派/汇总/清单);
- 负例:原始检索含金标但不在任务(不得标 eligible)、脏 recorded 卡
  (condition 冲突不得标 eligible)、可解析目标非金标(不得标验证拒绝)、
  rank 2 正确 rank 1 错(必须标 rank2_5)、跨父 path_id 串线(排除+audit
  gap)、清单 SHA 篡改(fail-closed)、产物篡改(--check 失败)。
"""

from __future__ import annotations

import csv
import json
import shutil
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "scripts"))

import ec298_hit1_attribution as attr  # noqa: E402
from pathway_v43.exam_v2 import ScorerV2Error  # noqa: E402
from pathway_v43.services.atom_tool import render  # noqa: E402


# ---------------------------------------------------------------- 纯函数


def test_classify_rank2_5_reported():
    bp = attr.classify_breakpoint({
        "agent_rank": 2, "analogy_rejected": False,
        "atomtool_target_ok": None, "target_whole_gold": False,
        "validation_gold_rejected": True, "validation_gold_accepted": True,
        "reported_gold": True, "task_gold_cards": [],
        "selected_exists": True, "selected_gold": False,
        "raw_retrieval_gold": True, "any_gold_observed": True,
        "selected_kind": "recorded_reaction", "mode": "novel_proposal",
        "residual_mechanism": "x",
    })
    assert bp["label"] == "reported_at_rank_2_to_5"


def test_classify_eligible_and_ineligible_gold_card():
    base = {"agent_rank": None, "analogy_rejected": False,
            "atomtool_target_ok": None, "target_whole_gold": False,
            "validation_gold_rejected": False,
            "validation_gold_accepted": False, "reported_gold": False,
            "selected_exists": True, "selected_gold": False,
            "raw_retrieval_gold": True, "any_gold_observed": True,
            "selected_kind": "recorded_reaction", "mode": "rank_candidates",
            "residual_mechanism": "x"}
    ok = attr.classify_breakpoint({**base, "task_gold_cards": [
        {"eligible": True, "condition_fit": "unknown", "order_position": 2}]})
    assert ok["label"] == "eligible_gold_not_selected"
    dirty = attr.classify_breakpoint({**base, "task_gold_cards": [
        {"eligible": False, "condition_fit": "conflict",
         "order_position": None}]})
    assert dirty["label"] == "unknown"
    assert dirty["mechanism"] == "task_candidate_gold_card_ineligible"


def test_classify_validation_paths():
    base = {"agent_rank": None, "analogy_rejected": False,
            "atomtool_target_ok": None, "target_whole_gold": False,
            "task_gold_cards": [], "selected_exists": True,
            "selected_gold": True, "raw_retrieval_gold": True,
            "any_gold_observed": True, "selected_kind": "recorded_reaction",
            "mode": "rank_candidates", "residual_mechanism": "x"}
    rej = attr.classify_breakpoint({**base, "validation_gold_rejected": True,
                                    "validation_gold_accepted": False,
                                    "reported_gold": False})
    assert rej["label"] == "validation_rejected_gold"
    missed = attr.classify_breakpoint({**base, "validation_gold_rejected":
                                       False,
                                       "validation_gold_accepted": True,
                                       "reported_gold": False})
    assert missed["label"] == "validated_but_not_reported"


def test_classify_analogy_target_gold_vs_not_gold():
    """§5.3 负例:可解析目标非金标 → 不得标 validation_rejected_gold。"""
    base = {"agent_rank": None, "analogy_rejected": True,
            "validation_gold_rejected": False, "validation_gold_accepted":
            False, "reported_gold": False, "task_gold_cards": [],
            "selected_exists": False, "selected_gold": False,
            "raw_retrieval_gold": True, "any_gold_observed": True,
            "selected_kind": "none", "mode": "analogy_edit",
            "residual_mechanism": "analogy_rejected"}
    hit = attr.classify_breakpoint({**base, "atomtool_target_ok": True,
                                    "target_whole_gold": True})
    assert hit["label"] == "validation_rejected_gold"
    miss = attr.classify_breakpoint({**base, "atomtool_target_ok": True,
                                     "target_whole_gold": False})
    assert miss["label"] == "unknown"


def test_classify_scope_absence_beats_selected_wrong():
    """范围无金标时,选中卡不含金标只是伴生结果,不得抢断点。"""
    bp = attr.classify_breakpoint({
        "agent_rank": None, "analogy_rejected": False,
        "atomtool_target_ok": None, "target_whole_gold": False,
        "validation_gold_rejected": False, "validation_gold_accepted": False,
        "reported_gold": False, "task_gold_cards": [],
        "selected_exists": True, "selected_gold": False,
        "raw_retrieval_gold": False, "any_gold_observed": False,
        "selected_kind": "recorded_reaction", "mode": "recorded_direct",
        "residual_mechanism": "x",
    })
    assert bp["label"] == "retrieval_absence_within_observed_scope"


# ---------------------------------------------------------------- 夹具构建

GOLD = "CCO"


def _dump(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _decision(mode="", outcome="", accepted="", path_id="p_x"):
    return {"name": "decision", "created_at": "2026-09-24T00:00:00+00:00",
            "path_id": path_id, "prediction_mode": mode, "outcome": outcome,
            "accepted_evidence_id": accepted, "considered": [],
            "run_id": "r", "strategy_version": "t"}


def _pred(mode, outcome, parsed=None, selected="", checks=None):
    return {"mode": mode, "outcome": outcome, "parsed": parsed or {},
            "selected_evidence_id": selected, "order":
            (parsed or {}).get("order", []),
            "atomtool_checks": checks or {}, "reasons": [], "attempt": 1,
            "task_id": "T", "task_kind": "prediction_task", "path_id":
            "p_x", "run_id": "r", "schema_version": "t",
            "policy_version": "t"}


def _task(candidates, mode="rank_candidates"):
    return {"task_kind": "prediction_task", "mode": mode,
            "candidates": candidates, "path_id": "p_x", "run_id": "r",
            "donor": {}, "budget": {}, "current": {}}


def _card(eid, kind, prods, **kw):
    return {"evidence_id": eid, "kind": kind, "condition_fit": "unknown",
            "products": [{"position": i, "product_smiles": p,
                          "product_identity": p}
                         for i, p in enumerate(prods)],
            "mapping_status": kw.get("mapping_status", "unavailable"),
            "match_type": "exact_donor_cn_match", "retrieval_rank": 1,
            "source_id": "src#r1", "asset_sources": [], "donor_refs": []}


def _retrieval(evidences):
    return {"schema_version": "t", "query": {}, "conditions": None,
            "evidences": evidences, "retrieval_assets": [], "engine_meta":
            {}, "created_at": "t"}


def _ev(eid, kind, prods, **kw):
    return {**_card(eid, kind, prods, **kw), "path_id": "p_x",
            "query_identity": "C", "reactant_identity": "C",
            "reactant_smiles": "C", "_content_hash": "h",
            "mapping_reason": "m", "atom_mapping": "unavailable",
            "score": 0.5, "score_semantics": "t", "created_at": "t"}


def _validation(eid, verdicts):
    return {"evidence_id": eid, "evidence_kind": "recorded_reaction",
            "gates": [], "n_accepted": sum(1 for v in verdicts
                                           if v["accepted"]),
            "n_total": len(verdicts), "predicted_by_model": True,
            "verdicts": verdicts}


def _verdict(smiles, accepted=True, position=0):
    return {"accepted": accepted, "position": position,
            "product_smiles": smiles, "product_identity": smiles,
            "reasons": []}


def _adjudication(entries, kind="recorded_reaction", path_id="p_x",
                  evidence_id="E_x"):
    return {"schema_version": "v43-report-adjudication-1", "event_id": "e",
            "evidence_id": evidence_id, "evidence_kind": kind,
            "n_expand_selected": 1, "n_reportable": len(entries),
            "path_id": path_id, "policy": {}, "report_rank_basis": "t",
            "run_id": "r", "substrate_identity": "C", "task_kind": "t",
            "entries": [{"accepted": True, "evidence_id": evidence_id,
                         "expand_selected": True, "expand_status": "frontier",
                         "position": i, "product_smiles": s,
                         "product_identity": s, "product_smiles_full": s,
                         "report_rank": i + 1, "reportable": True,
                         "validation_ref": "T_v", "verdict_reasons": []}
                        for i, s in enumerate(entries)]}


# 六题:1 命中(应被排除)+ 5 类断点未命中
SPECS = {
    "RXNG_t_hit1": "hit",
    "RXNG_t_rec": "rec_raw_gold",
    "RXNG_t_rank": "rank_eligible",
    "RXNG_t_ana": "analogy_gold_target",
    "RXNG_t_nov": "novel_rank2",
    "RXNG_t_abs": "absent",
}


def _artifacts_for(qid: str, spec: str, tmp: Path) -> None:
    rd = tmp / "agent_runs" / f"exam298_seal_{qid}" / "results"
    if spec == "hit":
        _dump(rd / "T_a/decision.json", _decision("rank_candidates",
                                                  "selected", "E_h"))
        _dump(rd / "T_b/retrieval.json", _retrieval(
            [_ev("E_h", "recorded_reaction", [GOLD])]))
        _dump(rd / "T_c/prediction_task.json", _task(
            [_card("E_h", "recorded_reaction", [GOLD])]))
        _dump(rd / "T_c/prediction.json", _pred(
            "rank_candidates", "selected",
            parsed={"ok": True, "mode": "rank_candidates",
                    "order": ["E_h"], "reasons": {},
                    "selected_evidence_id": "E_h"}, selected="E_h"))
        _dump(rd / "T_d/validation.json",
              _validation("E_h", [_verdict(GOLD)]))
        _dump(rd / "T_e/report_adjudication.json",
              _adjudication([GOLD], evidence_id="E_h"))
    elif spec == "rec_raw_gold":
        _dump(rd / "T_a/decision.json", _decision(
            "", "commit_recorded", "E_rec", path_id="p_m1"))
        _dump(rd / "T_b/retrieval.json", _retrieval([
            _ev("E_rec", "recorded_reaction", ["CCC"]),
            _ev("E_raw", "rule_application", [GOLD])]))
        _dump(rd / "T_d/validation.json",
              _validation("E_rec", [_verdict("CCC")]))
        _dump(rd / "T_e/report_adjudication.json",
              _adjudication(["CCC"], evidence_id="E_rec", path_id="p_m1"))
    elif spec == "rank_eligible":
        _dump(rd / "T_a/decision.json", _decision("rank_candidates",
                                                  "awaiting_prediction",
                                                  "E_x1"))
        _dump(rd / "T_b/retrieval.json", _retrieval([
            _ev("E_g1", "recorded_reaction", [GOLD]),
            _ev("E_x1", "recorded_reaction", ["CCC"])]))
        _dump(rd / "T_c/prediction_task.json", _task([
            _card("E_g1", "recorded_reaction", [GOLD]),
            _card("E_x1", "recorded_reaction", ["CCC"])]))
        _dump(rd / "T_c/prediction.json", _pred(
            "rank_candidates", "selected",
            parsed={"ok": True, "mode": "rank_candidates",
                    "order": ["E_x1", "E_g1"],
                    "reasons": {"E_g1": "model prefers x1 chemistry"},
                    "selected_evidence_id": "E_x1"}, selected="E_x1"))
        _dump(rd / "T_d/validation.json",
              _validation("E_x1", [_verdict("CCC")]))
        _dump(rd / "T_e/report_adjudication.json",
              _adjudication(["CCC"], evidence_id="E_x1"))
    elif spec == "analogy_gold_target":
        _dump(rd / "T_a/decision.json", _decision("analogy_edit",
                                                  "rejected", ""))
        _dump(rd / "T_b/retrieval.json", _retrieval([
            _ev("E_d1", "analog_reaction", ["ZZZ"],
                mapping_status="resolved")]))
        _dump(rd / "T_c/prediction_task.json", _task(
            [_card("E_d1", "analog_reaction", ["ZZZ"])], mode="analogy_edit"))
        _dump(rd / "T_c/prediction.json", _pred(
            "analogy_edit", "rejected",
            parsed={"ok": True, "decision": "apply", "mode": "analogy_edit",
                    "target_molecode": render(GOLD, name="S").molecode,
                    "edits": [{"op": "form_bond", "atom1": "S_C_1",
                               "atom2": "S_O_1"}]},
            checks={"target_molecode": {"ok": True, "reasons": [],
                                        "target_smiles": GOLD,
                                        "added_atom_ids": [],
                                        "removed_atom_ids": []},
                    "edit_references": {"ok": False, "reasons": [
                        "edit_invalid:bond_already_present:S_O_1~S_C_1"]}}))
    elif spec == "novel_rank2":
        _dump(rd / "T_a/decision.json", _decision("novel_proposal",
                                                  "awaiting_prediction"))
        _dump(rd / "T_b/retrieval.json", _retrieval(
            [_ev("E_r1", "rule_application", ["QQQ"])]))
        _dump(rd / "T_c/prediction_task.json", _task([], mode="novel"))
        _dump(rd / "T_c/prediction.json", _pred(
            "novel_proposal", "proposed",
            parsed={"ok": True, "mode": "novel_proposal",
                    "products": ["ZZZ", GOLD]}))
        _dump(rd / "T_d/validation.json",
              _validation("E_n1", [_verdict("ZZZ", position=0),
                                   _verdict(GOLD, position=1)]))
        _dump(rd / "T_e/report_adjudication.json", _adjudication(
            ["ZZZ", GOLD], kind="novel_proposal", evidence_id="E_n1"))
    elif spec == "absent":
        _dump(rd / "T_a/decision.json", _decision("analogy_edit",
                                                  "abstained"))
        _dump(rd / "T_b/retrieval.json", _retrieval(
            [_ev("E_q1", "analog_reaction", ["CCC"])]))
        _dump(rd / "T_c/prediction_task.json", _task(
            [_card("E_q1", "analog_reaction", ["CCC"])], mode="analogy_edit"))
        _dump(rd / "T_c/prediction.json", _pred(
            "analogy_edit", "abstained", parsed={}))


def build_seal(tmp: Path) -> dict:
    run_dir = tmp / "seal" / "runs" / "r1"
    for qid, spec in SPECS.items():
        _artifacts_for(qid, spec, run_dir)
        (run_dir / "agent_runs" / f"exam298_seal_{qid}" /
         "run_identity.json").write_text("{}", encoding="utf-8")
    _dump(run_dir / "exam_inputs.jsonl", None)  # placeholder,改写为 jsonl
    lines = [{"input_index": i, "qid": q, "substrate_smiles": "C"}
             for i, q in enumerate(SPECS)]
    (run_dir / "exam_inputs.jsonl").write_text(
        "\n".join(json.dumps(x) for x in lines) + "\n", encoding="utf-8")
    merged = [{"route_id": q, "root_smiles": "C",
               "steps": [{"parent_smiles": "C",
                          "predicted_products": (
                              [GOLD] if s == "hit" else
                              ["CCC"] if s == "rec_raw_gold" else
                              ["CCC"] if s == "rank_eligible" else
                              [] if s == "analogy_gold_target" else
                              ["ZZZ", GOLD] if s == "novel_rank2" else [])}]
               } for q, s in SPECS.items()]
    (run_dir / "agent_batch" / "merged").mkdir(parents=True, exist_ok=True)
    (run_dir / "agent_batch" / "merged" / "predictions.jsonl").write_text(
        "\n".join(json.dumps(x) for x in merged) + "\n", encoding="utf-8")
    wdir = run_dir / "agent_batch" / "workers"
    wdir.mkdir(parents=True, exist_ok=True)
    for i, q in enumerate(SPECS):
        _dump(wdir / f"w{i}.status.json", {"route_id": q,
                                           "stop_reason": "completed"})
    (run_dir / "engine_arm").mkdir(parents=True, exist_ok=True)
    (run_dir / "engine_arm" / "engine_results.jsonl").write_text(
        "\n".join(json.dumps({"qid": q, "status": "ok", "top10": []})
                  for q in SPECS) + "\n", encoding="utf-8")
    (run_dir / "scoring").mkdir(parents=True, exist_ok=True)
    (run_dir / "scoring" / "per_question_scoring.json").write_text(
        "{}\n", encoding="utf-8")
    gold = tmp / "gold"
    gold.mkdir(parents=True, exist_ok=True)
    (gold / "questions.jsonl").write_text(
        "\n".join(json.dumps({"qid": q, "category": "t",
                              "products_smiles": [GOLD]})
                  for q in SPECS) + "\n", encoding="utf-8")
    v41 = tmp / "v41.jsonl"
    v41.write_text("\n".join(json.dumps({"qid": q, "baseline_rank": None})
                             for q in SPECS) + "\n", encoding="utf-8")
    assets = tmp / "assets.jsonl"
    assets.write_text("{}\n", encoding="utf-8")

    import ec298_phase_a as pa
    pa_manifest = pa.build_input_manifest(run_dir, gold / "questions.jsonl",
                                          run_dir / "scoring"
                                          / "per_question_scoring.json",
                                          v41, assets)
    phase_a = tmp / "phase_a"
    phase_a.mkdir(parents=True, exist_ok=True)
    agent_pred = run_dir / "agent_batch/merged/predictions.jsonl"
    engine = run_dir / "engine_arm/engine_results.jsonl"
    gpath = gold / "questions.jsonl"

    def sha(p: Path) -> str:
        import hashlib
        return hashlib.sha256(p.read_bytes()).hexdigest()

    score = {"summary": {"scorer_version": "t"},
             "per_question": [
                 {"qid": q, "category": "t", "n_gold_products": 1,
                  "agent_rank": (1 if s == "hit" else
                                 None if s in ("rec_raw_gold",
                                               "rank_eligible",
                                               "analogy_gold_target",
                                               "absent") else 2),
                  "engine_rank": None, "n_predicted": 1,
                  "tier_v2": "not_in_exported_top10"}
                 for q, s in SPECS.items()],
             "inputs_sha256": {"agent_predictions": sha(agent_pred),
                               "engine_results": sha(engine),
                               "gold_questions": sha(gpath)}}
    (phase_a / "input_manifest.json").write_text(
        json.dumps(pa_manifest), encoding="utf-8")
    (phase_a / "score_v2.json").write_text(
        json.dumps(score), encoding="utf-8")
    return {"run_dir": run_dir, "gold": gpath, "v1": run_dir / "scoring"
            / "per_question_scoring.json", "v41": v41, "assets": assets,
            "phase_a": phase_a}


def run_main(paths: dict, out: Path, extra: list[str] | None = None) -> int:
    return attr.main([
        "--run-dir", str(paths["run_dir"]),
        "--gold", str(paths["gold"]),
        "--v1-scoring", str(paths["v1"]),
        "--v41-baseline", str(paths["v41"]),
        "--asset-library", str(paths["assets"]),
        "--phase-a-dir", str(paths["phase_a"]),
        "--out-dir", str(out),
        "--skip-anchor-check",
        *(extra or []),
    ])


def read_tsv(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter="\t"))


# ---------------------------------------------------------------- 端到端


@pytest.fixture()
def seal(tmp_path):
    return build_seal(tmp_path)


def test_end_to_end_labels_and_exclusions(seal, tmp_path):
    out = tmp_path / "out"
    assert run_main(seal, out) == 0
    rows = {r["qid"]: r for r in read_tsv(out / "hit1_misses.tsv")}
    assert set(rows) == set(SPECS) - {"RXNG_t_hit1"}   # 命中题被排除
    expect = {
        "RXNG_t_rec": "selected_wrong_product",
        "RXNG_t_rank": "eligible_gold_not_selected",
        "RXNG_t_ana": "validation_rejected_gold",
        "RXNG_t_nov": "reported_at_rank_2_to_5",
        "RXNG_t_abs": "retrieval_absence_within_observed_scope",
    }
    for qid, label in expect.items():
        assert rows[qid]["first_proven_loss_stage"] == label, qid
    # 原始检索含金标但不在任务 → 不得标 eligible(§5.3 负例)
    assert rows["RXNG_t_rec"]["task_candidate_gold"] == "false"
    assert rows["RXNG_t_rec"]["raw_retrieval_gold"] == "true"
    # rank 金标卡位次与模型自述理由
    assert rows["RXNG_t_rank"]["gold_card_order_position"] == "2"
    assert "model prefers x1" in rows["RXNG_t_rank"]["gold_card_model_reason"]
    # 类比目标:整分子匹配 + 拒因可回查
    assert rows["RXNG_t_ana"]["target_match_whole_cn"] == "true"
    assert "bond_already_present" in \
        rows["RXNG_t_ana"]["atomtool_edit_reject_reasons"]
    # rank 2 正确但 rank 1 错(§5.3 负例)
    assert rows["RXNG_t_nov"]["gold_report_rank"] == "2"
    assert rows["RXNG_t_nov"]["reported_gold"] == "true"
    assert rows["RXNG_t_nov"]["any_component_hit1"] == "false"
    # 布尔词汇纪律
    boolish = {"true", "false", "unknown", "not_applicable"}
    for r in rows.values():
        for col in ("raw_retrieval_gold", "task_candidate_gold",
                    "selected_gold", "validated_reportable_gold",
                    "reported_gold", "gold_card_in_task",
                    "first_candidate_matches_gold"):
            assert r[col] in boolish, (r["qid"], col, r[col])
    # 逐题证据链与汇总
    traces = [json.loads(l)
              for l in (out / "evidence_trace.jsonl")
              .read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(traces) == 5
    for t in traces:
        assert t["items"], t["qid"]
        for item in t["items"]:
            if item["role"] != "llm_calls":
                assert item["sha256"] != "MISSING", item
    summary = read_tsv(out / "group_summary.tsv")
    total = next(r for r in summary if r["group"] == "TOTAL")
    assert total["n_miss"] == "5"
    assert total["eligible_gold_not_selected"] == "1"
    assert total["validation_rejected_gold"] == "1"
    # 类比目标重算表
    tgt = read_tsv(out / "analogy_target_gold_recompute.tsv")
    assert len(tgt) == 1 and tgt[0]["match_whole_cn"] == "true"
    assert tgt[0]["ledger_equals_reparse"] == "true"
    # 审计缺口文件存在且有表头(可为空)
    assert (out / "audit_gaps.tsv").is_file()
    assert read_tsv(out / "audit_gaps.tsv") == []
    # 输出清单
    man = (out / "output_manifest.sha256").read_text(encoding="utf-8")
    assert "hit1_misses.tsv" in man and "fix_coverage.tsv" in man


def test_recompute_byte_identical_and_check(seal, tmp_path):
    out1, out2 = tmp_path / "o1", tmp_path / "o2"
    assert run_main(seal, out1) == 0
    assert run_main(seal, out2) == 0
    for p in sorted(out1.iterdir()):
        assert p.read_bytes() == (out2 / p.name).read_bytes(), p.name
    assert run_main(seal, out1, extra=["--check"]) == 0
    # 篡改一个衍生文件 → --check 必须失败(fail-closed)
    (out1 / "score_sensitivity.tsv").write_text("tampered\n",
                                                encoding="utf-8")
    assert run_main(seal, out1, extra=["--check"]) == 1


def test_manifest_tamper_fail_closed(seal, tmp_path):
    bad = tmp_path / "bad_phase_a"
    shutil.copytree(seal["phase_a"], bad)
    manifest = json.loads((bad / "input_manifest.json").read_text())
    for g in manifest["groups"]:
        if g["role"] == "gold":
            g["entries"][0]["sha256"] = "0" * 64
    (bad / "input_manifest.json").write_text(json.dumps(manifest),
                                             encoding="utf-8")
    tampered = dict(seal, phase_a=bad)
    with pytest.raises(ScorerV2Error):
        run_main(tampered, tmp_path / "out")


def test_path_id_cross_contamination_excluded(seal, tmp_path):
    """§5.3 负例:不同父路径相同 SMILES——串线裁决产物必须被排除并留痕。"""
    rd = seal["run_dir"] / "agent_runs" / "exam298_seal_RXNG_t_rank" / "results"
    _dump(rd / "T_z/report_adjudication.json",
          _adjudication([GOLD], evidence_id="E_ghost", path_id="p_other"))
    # 新增文件必须走清单重建(fail-closed 会拒绝清单外新文件)
    import ec298_phase_a as pa
    manifest = pa.build_input_manifest(seal["run_dir"], seal["gold"],
                                       seal["v1"], seal["v41"],
                                       seal["assets"])
    (seal["phase_a"] / "input_manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8")
    out = tmp_path / "out_cross"
    assert run_main(seal, out) == 0
    rows = {r["qid"]: r for r in read_tsv(out / "hit1_misses.tsv")}
    r = rows["RXNG_t_rank"]
    assert r["reported_gold"] == "false"          # 串线产物不计入本题
    assert r["first_proven_loss_stage"] == "eligible_gold_not_selected"
    gaps = read_tsv(out / "audit_gaps.tsv")
    assert any(g["gap_type"] == "path_id_mismatch"
               and g["qid"] == "RXNG_t_rank" for g in gaps)


def test_dirty_gold_card_in_task_not_eligible(seal, tmp_path):
    """§5.3 负例:任务内金标卡带 condition 冲突 → 不得标 eligible。"""
    rd = seal["run_dir"] / "agent_runs" / "exam298_seal_RXNG_t_rank" / "results"
    task = json.loads((rd / "T_c/prediction_task.json").read_text())
    task["candidates"][0]["condition_fit"] = "conflict"
    (rd / "T_c/prediction_task.json").write_text(json.dumps(task),
                                                 encoding="utf-8")
    import hashlib
    # score_v2 的 agent_predictions SHA 与清单都会因 merged 未变而仍一致;
    # 但 prediction_task 在清单 run_dir 全集内 → 必须重建清单才能合法复算。
    # 此处按 fail-closed 语义直接期待清单校验失败。
    with pytest.raises(ScorerV2Error):
        run_main(seal, tmp_path / "out_dirty")


def test_dirty_gold_card_ineligible_label(tmp_path):
    """同上,但走合法路径:重建清单后断言标签降级为 unknown。"""
    paths = build_seal(tmp_path)
    rd = paths["run_dir"] / "agent_runs" / "exam298_seal_RXNG_t_rank" \
        / "results"
    task = json.loads((rd / "T_c/prediction_task.json").read_text())
    task["candidates"][0]["condition_fit"] = "conflict"
    (rd / "T_c/prediction_task.json").write_text(json.dumps(task),
                                                 encoding="utf-8")
    import ec298_phase_a as pa
    manifest = pa.build_input_manifest(paths["run_dir"], paths["gold"],
                                       paths["v1"], paths["v41"],
                                       paths["assets"])
    (paths["phase_a"] / "input_manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8")
    out = tmp_path / "out_dirty2"
    assert run_main(paths, out) == 0
    rows = {r["qid"]: r for r in read_tsv(out / "hit1_misses.tsv")}
    assert rows["RXNG_t_rank"]["first_proven_loss_stage"] == "unknown"
    assert rows["RXNG_t_rank"]["observed_mechanism"] == \
        "task_candidate_gold_card_ineligible"
