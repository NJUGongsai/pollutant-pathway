"""Phase C 工作流接线、回退语义与崩溃恢复(验收 §6.3/§6.4)。

- 路由:``mapping_status=resolved`` 单独不再触发类比;适用性失败按具体
  拒因转受约束 novel 或显式停留;``analogy_enabled=false`` 消融开关不影响
  recorded/rank;多供体只选有资格者(其余留拒因摘要)。
- 编辑接线:模型引用与选定供体不一致 → 结构化拒绝;空 edits 违反策略 →
  拒绝;不串线(referenced_evidence_id 必须等于 donor.evidence_id)。
- 恢复:供体裁决(资格块)落盘后硬杀 → resume 的供体选择、AtomTool
  verdict、模型调用数、最终事件与答卷一致(子进程实测)。
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from pathway_v43.domain.identity import cn_identity
from pathway_v43.domain.models import PATH_STATUS_AWAITING_PREDICTION

from conftest import REPO_ROOT
from wf_helpers import (
    CATECHOL,
    evidence,
    fake_model,
    load_report,
    novel_response,
    run_scripted,
)

ALCOHOL = "CCCCCO"
A = cn_identity(ALCOHOL)
ALDEHYDE = "CCCCC=O"
B = cn_identity(ALDEHYDE)
REAL_DONOR_RECORD = "env:EAWAG-BBD:bt0001#r0022"
CATECHOL_ID = cn_identity(CATECHOL)


def _fake_model(script=None, default_by_mode=None, policy=None):
    """fake ModelSetup(可带策略覆盖;策略取值进入 run 身份)。"""
    from pathway_v43.adapters.llm_client import resolve_model_setup

    return resolve_model_setup(
        "fake", fake_script=script or {},
        fake_default_by_mode=default_by_mode or {}, policy=policy)


def _donor_card(substrate_identity: str) -> dict:
    """通过适用性门禁的真实供体卡(中心 CH2-OH 氧化)。"""
    from pathway_v43.config import resolve_config
    from pathway_v43.services.analog_source import AnalogSourceResolver

    resolver = AnalogSourceResolver(resolve_config())
    ref = resolver.resolve_template(REAL_DONOR_RECORD)
    ref = resolver.align(ref, ALCOHOL)
    assert ref.alignment is not None
    return evidence("src-analog", "analog_reaction", substrate_identity,
                    [ALDEHYDE], match_type="retrieval_neighbor_transfer",
                    extra={"donor_refs": [ref.to_dict()],
                           "mapping_status": "resolved",
                           "mapping_reason":
                               "unique_mapped_template_aligned"})


def _inapplicable_card(substrate_identity: str) -> dict:
    """resolved 但门禁失配:酮还原模板,底物无酮中心。"""
    donor = {
        "record_id": "synthetic:reduce_ketone", "index": "synthetic",
        "asset_file": "synthetic", "asset_sha256": "0" * 64, "line_no": 3,
        "mapping_quality": "mapped_bijection",
        "reactant_smiles": "CC(=O)C",
        "mapped_lhs": "[CH3:1][C:2](=[O:3])[CH3:4]",
        "mapped_rhs": "[CH3:1][CH:2]([OH:3])[CH3:4]",
        "center_atoms": [2, 3],
    }
    return evidence("src-analog-weak", "analog_reaction",
                    substrate_identity, ["CCC(O)C"],
                    match_type="retrieval_neighbor_transfer",
                    extra={"donor_refs": [donor],
                           "mapping_status": "resolved",
                           "mapping_reason":
                               "unique_mapped_template_aligned"})


def _decision(runs: Path, run_id: str) -> dict:
    """父路径 decision(带资格块的那份;novel 子路径的 decision 无键)。"""
    candidates = []
    for f in sorted((runs / run_id / "results").glob("*/decision.json")):
        payload = json.loads(f.read_text())["payload"]
        candidates.append(payload)
        if "analogy_eligibility" in payload:
            return payload
    raise AssertionError(f"无带资格块的 decision:{[c.keys() for c in candidates]}")


def _prediction_payload(runs: Path, run_id: str) -> list[dict]:
    out = []
    for f in sorted((runs / run_id / "results").glob("*/prediction.json")):
        out.append(json.loads(f.read_text())["payload"])
    return out


def _analogy_response(eid: str, edits: list, target_text: str) -> str:
    return json.dumps({"decision": "apply", "target_molecode": target_text,
                       "edits": edits, "referenced_evidence_id": eid,
                       "reason": "迁移供体氧化"})


def test_weak_resolved_routes_novel_with_structured_reason(tmp_path):
    """弱映射 resolved 不再单独触发类比:门禁失配 → 受约束 novel,
    decision 持久化资格块与具体拒因(applicability_failed)。"""
    scripted = {A: [_inapplicable_card(A)]}
    model = fake_model(default_by_mode={
        "novel_proposal": novel_response(
            [{"smiles": "CCC(O)C", "note": "受约束提案"}])})
    summary, runs = run_scripted("pc-weak", scripted, max_depth=1,
                                 max_expansions=2, runs_root=tmp_path,
                                 model=model, smiles=ALCOHOL)
    preds = _prediction_payload(runs, "pc-weak")
    assert all(p["mode"] != "analogy_edit" for p in preds)
    assert preds and preds[0]["mode"] == "novel_proposal"
    decision = _decision(runs, "pc-weak")
    el = decision["analogy_eligibility"]
    assert el["status"] == "inapplicable"
    assert el["fallback_reason"] == "applicability_failed"
    assert decision["prediction_reason"].startswith("applicability_failed")


def test_eligibility_failure_holds_when_novel_disabled(tmp_path):
    scripted = {A: [_inapplicable_card(A)]}
    model = _fake_model(default_by_mode={
        "novel_proposal": novel_response([{"smiles": "CCC(O)C"}])},
        policy={"allow_novel_on_mapping_failure": False})
    summary, runs = run_scripted(
        "pc-hold", scripted, max_depth=1, max_expansions=2,
        runs_root=tmp_path, model=model, smiles=ALCOHOL)
    report = load_report(runs, "pc-hold")
    path = report["path_instances"][0]
    assert path["status"] == PATH_STATUS_AWAITING_PREDICTION
    assert "applicability_failed" in path["status_reason"]
    assert summary["counts"]["reaction_events"] == 0


def test_analogy_disabled_switch_keeps_recorded_and_routes_novel(tmp_path):
    """消融开关:analogy_enabled=false 时资格适用也不进类比;
    唯一 recorded 直通语义不受开关影响。"""
    scripted = {
        CATECHOL_ID: [evidence("btR1", "recorded_reaction", CATECHOL_ID,
                               [ALCOHOL])],
        A: [_donor_card(A)],
    }
    model = _fake_model(default_by_mode={
        "novel_proposal": novel_response([{"smiles": "CCCCC=O"}])},
        policy={"analogy_enabled": False})
    summary, runs = run_scripted(
        "pc-off", scripted, max_depth=2, max_expansions=3,
        runs_root=tmp_path, model=model)
    preds = _prediction_payload(runs, "pc-off")
    assert all(p["mode"] != "analogy_edit" for p in preds)
    decision = _decision(runs, "pc-off")
    # 资格块仍如实计算落盘(只是路由不采用)
    assert decision["analogy_eligibility"]["status"] == "applicable"
    assert "analogy_disabled" in decision["prediction_reason"]


def test_multiple_donors_only_eligible_selected_in_task(tmp_path):
    """多供体卡:门禁只选有资格者;其余评估过的供体留拒因摘要
    (alternatives_considered)。"""
    from pathway_v43.services.atom_tool import render

    resolver_card = _donor_card(A)
    weak = _inapplicable_card(A)
    combined = dict(resolver_card)
    combined["evidence_id"] = "E-multi"
    combined["donor_refs"] = (
        weak["donor_refs"] + resolver_card["donor_refs"])
    scripted = {A: [combined]}
    render_a = render(ALCOHOL, name="S")
    c_end = max((i for aid, i in render_a.atom_id_map.items()
                 if "_C_" in aid))
    c_end_id = next(a for a, i in render_a.atom_id_map.items() if i == c_end)
    o_id = next(a for a in render_a.atom_ids if "_O_" in a)
    target = render(ALDEHYDE, name="S").molecode
    model = fake_model(script={"analogy_edit": [_analogy_response(
        "E-multi", [{"op": "change_bond_order", "atom1": c_end_id,
                     "atom2": o_id, "from_order": "single",
                     "to_order": "double"}], target)]},
        default_by_mode={"novel_proposal": novel_response(
            [{"smiles": "CCCCC=O"}])})
    summary, runs = run_scripted("pc-multi", scripted, max_depth=1,
                                 max_expansions=2, runs_root=tmp_path,
                                 model=model, smiles=ALCOHOL)
    task = json.loads(next(
        (runs / "pc-multi" / "results").glob("*/prediction_task.json")
    ).read_text())["payload"]
    donor_block = task["donor"]
    assert donor_block["donor"]["record_id"] == REAL_DONOR_RECORD
    alts = donor_block["alternatives_considered"]
    assert alts and alts[0]["status"] == "inapplicable"
    assert summary["counts"]["reaction_events"] == 1


def test_referenced_evidence_id_mismatch_rejected(tmp_path):
    """模型引用与选定供体不一致 → 结构化 rejected(donor_reference_mismatch),
    不产生提案卡、不提交事件。"""
    from pathway_v43.services.atom_tool import render

    scripted = {A: [_donor_card(A)]}
    target = render(ALDEHYDE, name="S").molecode
    model = fake_model(script={"analogy_edit": [_analogy_response(
        "E-forged", [], target)]})
    summary, runs = run_scripted("pc-ref", scripted, max_depth=1,
                                 max_expansions=2, runs_root=tmp_path,
                                 model=model, smiles=ALCOHOL)
    preds = _prediction_payload(runs, "pc-ref")
    assert preds[0]["outcome"] == "rejected"
    assert "donor_reference_mismatch" in preds[0]["fail_reason"]
    checks = preds[0]["atomtool_checks"]
    assert checks["donor_reference"]["task_evidence_id"] == "E-src-analog"
    assert checks["donor_reference"]["mismatch"]["model_referenced"] == \
        "E-forged"
    assert summary["counts"]["reaction_events"] == 0


def test_noop_edits_rejected_by_default_policy(tmp_path):
    """空 edits 仅当目标图==当前图且策略允许 no-op;默认策略拒绝。"""
    from pathway_v43.services.atom_tool import render

    scripted = {A: [_donor_card(A)]}
    model = fake_model(script={"analogy_edit": [_analogy_response(
        "E-src-analog", [], render(ALCOHOL, name="S").molecode)]})
    summary, runs = run_scripted("pc-noop", scripted, max_depth=1,
                                 max_expansions=2, runs_root=tmp_path,
                                 model=model, smiles=ALCOHOL)
    preds = _prediction_payload(runs, "pc-noop")
    assert preds[0]["outcome"] == "rejected"
    assert "noop_edit_not_allowed" in preds[0]["fail_reason"]
    assert summary["counts"]["reaction_events"] == 0


# ------------------------------------------------------------ 恢复(§6.4)

DRIVER = REPO_ROOT / "tests" / "recovery_driver.py"
NOVEL_ABSTAIN = json.dumps({"decision": "abstain",
                            "reason": "恢复测试弃权"})


def _recovery_fixture() -> dict:
    return {A: [_donor_card(A)]}


def _recovery_fake_script() -> dict:
    from pathway_v43.services.atom_tool import render

    r = render(ALCOHOL, name="S")
    c_end_idx = max(i for aid, i in r.atom_id_map.items() if "_C_" in aid)
    c_end = next(a for a, i in r.atom_id_map.items() if i == c_end_idx)
    o = next(a for a in r.atom_ids if "_O_" in a)
    target = render(ALDEHYDE, name="S").molecode
    return {"analogy_edit": [_analogy_response(
        "E-src-analog",
        [{"op": "change_bond_order", "atom1": c_end, "atom2": o,
          "from_order": "single", "to_order": "double"}], target)],
        "novel_proposal": [NOVEL_ABSTAIN]}


def _driver(mode: str, runs_root: Path, run_id: str, tmp_path: Path,
            crash_after: str | None = None):
    env = dict(os.environ)
    env["OMP_NUM_THREADS"] = "1"
    cmd = [sys.executable, str(DRIVER), mode,
           "--runs-root", str(runs_root), "--run-id", run_id,
           "--smiles", ALCOHOL,
           "--scripted", str(tmp_path / "fx.json"),
           "--fake-script", str(tmp_path / "fake.json"),
           "--llm-counter", str(tmp_path / f"llm_{run_id}.txt"),
           "--max-depth", "1", "--max-expansions", "2",
           "--max-frontier-width", "2", "--model", "fake"]
    if crash_after:
        cmd += ["--crash-after", crash_after]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=600,
                          env=env)


def _write_fixtures(tmp_path: Path) -> None:
    (tmp_path / "fx.json").write_text(
        json.dumps(_recovery_fixture()), encoding="utf-8")
    (tmp_path / "fake.json").write_text(
        json.dumps(_recovery_fake_script()), encoding="utf-8")


def _eligibility_of(runs_root: Path, run_id: str) -> dict:
    task_dir = next((runs_root / run_id / "results").glob("*/decision.json"))
    return json.loads(task_dir.read_text())["payload"]["analogy_eligibility"]


def test_crash_after_classify_resume_consistent(tmp_path):
    """供体裁决(资格块)落盘后硬杀 → resume:同一供体选择、同一 AtomTool
    verdict、同一调用数与最终事件(§6.4)。"""
    _write_fixtures(tmp_path)
    runs_root = tmp_path / "runs"
    proc = _driver("run", runs_root, "pc-crash", tmp_path,
                   crash_after="classify_evidence")
    assert proc.returncode == 70, proc.stdout + proc.stderr
    # 资格块已落盘(供体裁决持久)
    el_before = _eligibility_of(runs_root, "pc-crash")
    assert el_before["status"] == "applicable"
    proc2 = _driver("resume", runs_root, "pc-crash", tmp_path)
    assert proc2.returncode == 0, proc2.stdout + proc2.stderr
    el_after = _eligibility_of(runs_root, "pc-crash")
    assert el_after == el_before  # 恢复不重算不改判
    summary = None
    for line in proc2.stdout.splitlines():
        if line.startswith("SUMMARY "):
            summary = json.loads(line[len("SUMMARY "):])
    assert summary is not None
    assert summary["counts"]["reaction_events"] == 1
    # 调用数:崩溃进程零调用,恢复进程一次(计数文件跨进程累加)
    llm_counter = tmp_path / "llm_pc-crash.txt"
    assert llm_counter.read_text().strip() == "1"
    # AtomTool verdict 与提案卡一致
    pred = json.loads(next(
        (runs_root / "pc-crash" / "results").glob("*/prediction.json")
    ).read_text())["payload"]
    assert pred["outcome"] == "proposed"
    checks = pred["atomtool_checks"]
    assert checks["edit_execution"]["product_smiles"] == ALDEHYDE
    assert checks["target_consistency"]["ok"]


# ------------------------------------------------- R2 复核 P1:analog 卡镜像


def test_analog_card_selected_via_rank_zero_commit(tmp_path):
    """R2 P1 端到端(analog 镜像):两张合格 recorded 进入 rank + 一张
    **原始 analog 卡**(不伪造 recorded 挂牌)混在检索;fake 模型选它且
    order 排第一 → 引用非法 ID → 有界重试 → 停留。零提交、零报告该卡、
    账本无 kind=analog_reaction 事件。"""
    a = evidence("btA", "recorded_reaction", CATECHOL_ID, ["O=CCC=CO"],
                 rank=1)
    b = evidence("btB", "recorded_reaction", CATECHOL_ID, ["CC=CC=O"],
                 rank=2)
    an = evidence("btAN", "analog_reaction", CATECHOL_ID, ["CC#N"], rank=3,
                  match_type="analog_similarity")
    resp = json.dumps({"decision": "select", "evidence_id": "E-btAN",
                       "order": ["E-btAN", "E-btA", "E-btB"],
                       "reasons": {}, "reason": "选类比卡"})
    model = _fake_model({"rank_candidates": [resp]})
    summary, runs_root = run_scripted(
        "r2analog", {CATECHOL_ID: [a, b, an]}, smiles=CATECHOL,
        max_depth=1, max_expansions=6, max_frontier_width=3,
        runs_root=tmp_path, model=model)
    assert summary["counts"]["reaction_events"] == 0
    results = runs_root / "r2analog" / "results"
    assert not list(results.glob("*/report_adjudication*.json"))
    # 防线①:原始 analog 卡不进 rank 任务候选(可选择集 = 合格 recorded)
    task_env = json.loads(next(results.glob("*/prediction_task.json"))
                          .read_text())["payload"]
    task_ids = {c["evidence_id"] for c in task_env["candidates"]}
    assert "E-btAN" not in task_ids
    assert task_ids == {"E-btA", "E-btB"}
    assert summary["stop_reason"] == "awaiting_prediction"
    assert len(list(results.glob("*/prediction_call.*.json"))) == 3


def test_analog_card_rank_guard_at_adjudication_layer():
    """R2 P1 防线②(analog 镜像):绕过任务筛选直接构造"选中检索层
    原始 analog 卡"的裁决 → card_eligible=false、产物零占位、带
    not_validated_for_reporting 拒因;order 内合格 recorded 正常占位。"""
    from pathway_v43.services.report_adjudication import (
        adjudicate_parent, validate_card_for_reporting)

    a = evidence("btA", "recorded_reaction", CATECHOL_ID, ["O=CCC=CO"],
                 rank=1)
    an = evidence("btAN", "analog_reaction", CATECHOL_ID, ["CC#N"], rank=3,
                  match_type="analog_similarity")
    result = {"outcome": "selected", "mode": "rank_candidates",
              "selected_evidence_id": "E-btAN",
              "order": ["E-btAN", "E-btA"], "task_id": "T-x", "attempt": 1}
    card_validations = {"E-btA": validate_card_for_reporting(
        card=a, substrate_identity=CATECHOL_ID, ancestry_cns=[CATECHOL_ID],
        entry_layer="retrieval")}
    payload = adjudicate_parent(
        run_id="r", path_id="p-root", substrate_identity=CATECHOL_ID,
        retrieval_payload={"query": {"substrate_identity": CATECHOL_ID},
                           "evidences": [a, an]},
        decision_payload={"accepted_evidence_id": None},
        prediction_task={"candidates": [
            {"evidence_id": "E-btAN"}, {"evidence_id": "E-btA"}]},
        prediction_result=result,
        selected_evidence_id="E-btAN", selected_card=an,
        selected_validation={
            "evidence_id": "E-btAN",
            "gates": {"direction_source": {"ok": True, "reason": ""},
                      "atom_mapping": {"ok": True, "reason": ""}},
            "verdicts": [{"position": 0, "product_smiles": "CC#N",
                          "product_identity": cn_identity("CC#N"),
                          "accepted": True, "reasons": []}],
            "n_accepted": 1, "n_total": 1},
        card_validations=card_validations,
        validation_refs={
            "E-btAN": {"task_id": "T-val", "artifact": "validation",
                       "payload_sha256": "0" * 64},
            "E-btA": {"task_id": "T-adj", "artifact": "cardval.E-btA",
                      "payload_sha256": "1" * 64}},
        stage="draft")
    an_entry = next(r for r in payload["products"]
                    if r["evidence_id"] == "E-btAN")
    assert not an_entry["reportable"] and an_entry["report_rank"] is None
    assert any("not_validated_for_reporting" in r
               for r in an_entry["reasons"])
    an_card = next(c for c in payload["cards"] if c["evidence_id"] == "E-btAN")
    assert an_card["selected"] and not an_card["card_eligible"]
    # 原始卡被选中也不得标成"已验证可报告"(R2 复核反例的字段)
    assert an_card["not_validated_for_reporting"] is True
    ranked = [r["evidence_id"] for r in payload["products"]
              if r["reportable"]]
    assert ranked == ["E-btA"]
