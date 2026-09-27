#!/usr/bin/env python
"""EC298 Phase A 编排:同口径重评分 v2 + A1–A6 归因表(零 LLM、零网络)。

阶段任务书:docs/TASK_V43_EC298_PHASE_A.md。所有输入路径显式传入;脚本不
包含任何环境地址或凭证。封存输入只读;衍生输出仅写入 --out-dir。

用法(本地镜像或 Chenyu 封存根均可,相对布局一致)::

    # 一次性初始化(仅在核验过的封存副本上;已存在时严禁覆盖)
    python scripts/ec298_phase_a.py --run-dir <sealed>/.../ec298_v43r1 \
        --gold <sealed>/ec298_gold_readonly/questions.jsonl \
        --v1-scoring <sealed>/.../scoring/per_question_scoring.json \
        --v41-baseline <sealed>/.../per_question_scoring.jsonl \
        --asset-library assets/v3_reactions/library/library_full.jsonl \
        --out-dir reports/ec298/phase_a_v2 --init-input-manifest

    # 正常复算(不带初始化标志;清单缺失、文件集合变化或任一字节变化即失败)
    python scripts/ec298_phase_a.py --run-dir <sealed>/.../ec298_v43r1 \
        --gold <sealed>/ec298_gold_readonly/questions.jsonl \
        --v1-scoring <sealed>/.../scoring/per_question_scoring.json \
        --v41-baseline <sealed>/.../per_question_scoring.jsonl \
        --asset-library assets/v3_reactions/library/library_full.jsonl \
        --out-dir reports/ec298/phase_a_v2

行为:
- 输入清单(input_manifest.json,含 run_dir 完整文件集合与 gold/v1_scoring/
  v41_baseline/asset_library 各角色)是复算前提:缺失即失败;已有清单时
  严禁覆盖;校验为双向——磁盘文件集合与清单不一致(缺/增/改)立即失败;
- 生成 score_v2.json(正式逐题评分,含输入 SHA)/ v1↔v2 diff / 多组分
  敏感性 / A1–A6 TSV / 锚点对账 / output_manifest.sha256;
- 锚点(任务书 §0/§2/§3 验收值)不一致时逐项写入 anchor_reconciliation.json
  并以退出码 1 结束。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from pathway_v43.exam_v2 import (  # noqa: E402
    DIFF_COLUMNS,
    ScorerV2Error,
    diff_v1_v2,
    multicomponent_sensitivity,
    score_exam_v2,
    write_tsv,
)
from pathway_v43.phase_a_attribution import (  # noqa: E402
    A1_COLUMNS,
    A1_SUMMARY_COLUMNS,
    A2_COLUMNS,
    A3_COLUMNS,
    A3_DETAIL_COLUMNS,
    A4_COLUMNS,
    A5_COLUMNS,
    A6_COLUMNS,
    build_agent_hits_by_engine_tier,
    build_awaiting_prediction_fates,
    build_decision_path_contribution,
    build_hit5_paired_attribution,
    build_llm_call_distribution,
    build_v41_baseline_diff,
    load_sealed_run_view,
)

MANIFEST_VERSION = "v43-ec298-phase-a-input-manifest-1"

ANCHORS = {
    "n_questions": 298,
    "agent_hit@1": 116, "agent_hit@3": 128, "agent_hit@5": 130,
    "engine_hit@1": 118, "engine_hit@3": 174,
    "engine_hit@5": 193, "engine_hit@10": 209,
    "tier_engine_top10_hit": 209, "tier_not_in_exported_top10": 89,
    "v1v2_agent_rank_changed": 0, "v1v2_engine_rank_changed": 68,
    "mc_agent_hit@1": 129, "mc_agent_hit@3": 141, "mc_agent_hit@5": 143,
    "mc_engine_hit@1": 132, "mc_engine_hit@3": 184, "mc_engine_hit@5": 199,
    "a2_awaiting_rows": 50, "a2_budget_rows": 1,
    "a2_outcome_abstained": 28, "a2_outcome_rejected": 23,
    "a3_recorded_direct": 112, "a3_rank_candidates": 70,
    "a3_analogy_abstained": 28, "a3_analogy_rejected": 23,
    "a3_analogy_proposed": 15, "a3_novel_proposal": 50,
    "a3_agent@1_sum": 116, "a3_agent@5_sum": 130,
    "a4_engine_only": 82, "a4_agent_only": 19,
    "width_0": 51, "width_1": 197, "width_2": 1,
    "width_3": 1, "width_4": 5, "width_5": 43,
    "a6_total_issued": 191, "a6_total_provider_ok": 186,
    "a6_total_failed": 5, "a6_total_orphans": 0,
}


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------- 输入清单

MANIFEST_ROLES = ("run_dir", "gold", "v1_scoring", "v41_baseline",
                  "asset_library")


def build_input_manifest(run_dir: Path, gold: Path, v1_scoring: Path | None,
                         v41: Path | None, asset_library: Path | None) -> dict:
    """逐文件 SHA256 清单(路径按角色内相对路径,跨机器可核)。

    仅在 ``--init-input-manifest`` 的显式初始化时调用一次;此后严禁覆盖。
    """
    groups = []
    files = sorted(p for p in run_dir.rglob("*") if p.is_file())
    groups.append({"role": "run_dir", "root": str(run_dir),
                   "n_files": len(files),
                   "entries": [{"relpath": str(p.relative_to(run_dir)),
                                "sha256": _sha256(p)} for p in files]})
    for role, path in (("gold", gold), ("v1_scoring", v1_scoring),
                       ("v41_baseline", v41), ("asset_library", asset_library)):
        if path is None:
            continue
        groups.append({"role": role, "root": str(path), "n_files": 1,
                       "entries": [{"relpath": path.name,
                                    "sha256": _sha256(path)}]})
    return {"schema_version": MANIFEST_VERSION, "groups": groups}


def verify_input_manifest(manifest: dict, run_dir: Path, gold: Path,
                          v1_scoring: Path | None, v41: Path | None,
                          asset_library: Path | None) -> None:
    """封存校验(复算必经):完整文件集合 + 逐文件 SHA,双向 fail-closed。

    - run_dir:磁盘文件集合必须与清单一一对应——少了、多了(包括新增的
      会被扫描的结果文件)、任一字节变化都立即失败;
    - 其余角色:清单里有角色则输入必须提供且 SHA 一致;输入提供了而清单
      没有对应角色,同样失败(不受保护=拒绝运行)。
    """
    roots = {"run_dir": run_dir, "gold": gold, "v1_scoring": v1_scoring,
             "v41_baseline": v41, "asset_library": asset_library}
    by_role = {g["role"]: g for g in manifest["groups"]}
    unknown = sorted(set(by_role) - set(MANIFEST_ROLES))
    if unknown:
        raise ScorerV2Error("清单含未知角色", {"roles": unknown})
    # 输入已提供而清单缺角色 → 拒绝(不受保护的输入)
    for role, path in roots.items():
        if path is not None and role not in by_role:
            raise ScorerV2Error("输入未受清单保护(清单缺角色),拒绝运行",
                                {"role": role, "path": str(path)})
    for role, group in by_role.items():
        root = roots.get(role)
        if root is None:
            raise ScorerV2Error("清单角色未提供对应输入", {"role": role})
        if len(group["entries"]) != group["n_files"]:
            raise ScorerV2Error("清单 n_files 与条目数不符", {"role": role})
        if role == "run_dir":
            disk = {str(p.relative_to(root)): p
                    for p in root.rglob("*") if p.is_file()}
            listed = {e["relpath"] for e in group["entries"]}
            missing = sorted(listed - set(disk))
            extra = sorted(set(disk) - listed)
            if missing or extra:
                raise ScorerV2Error(
                    "封存 run 目录文件集合与清单不一致(改动或新增文件)",
                    {"n_missing": len(missing), "missing": missing[:5],
                     "n_extra": len(extra), "extra": extra[:5]})
            for entry in group["entries"]:
                actual = _sha256(disk[entry["relpath"]])
                if actual != entry["sha256"]:
                    raise ScorerV2Error(
                        "输入 SHA256 不符(封存性被破坏或版本不一致)",
                        {"role": role, "path": entry["relpath"],
                         "expected": entry["sha256"], "actual": actual})
        else:
            p = root
            if not p.is_file():
                raise ScorerV2Error("清单文件缺失",
                                    {"role": role, "path": str(p)})
            actual = _sha256(p)
            if actual != group["entries"][0]["sha256"]:
                raise ScorerV2Error(
                    "输入 SHA256 不符(封存性被破坏或版本不一致)",
                    {"role": role, "path": str(p),
                     "expected": group["entries"][0]["sha256"],
                     "actual": actual})


# ---------------------------------------------------------------- A5 资产重叠


def build_asset_exam_overlap(view, scores_v2: dict, gold_questions: Path,
                             library_path: Path) -> tuple[list[dict], dict]:
    """底物身份重叠与底物-金标产物对重叠(描述统计,非因果)。"""
    from pathway_v43.domain.identity import cn_identity
    from pathway_v43.exam_v2 import load_gold

    gold = load_gold(gold_questions)
    records = []
    for line in library_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            records.append(json.loads(line))
    lib_sub: dict[str, list[str]] = {}
    lib_pairs: dict[str, list[tuple[str, str]]] = {}
    n_unparseable = 0
    for rec in records:
        s = cn_identity(rec.get("donor_smiles", ""))
        p = cn_identity(rec.get("product_smiles", ""))
        if s is None:
            n_unparseable += 1
            continue
        ref = f"{rec.get('btid', '')}#{rec.get('reac_id', '')}"
        lib_sub.setdefault(s, []).append(ref)
        if p is not None:
            lib_pairs.setdefault(s, []).append((p, ref))
    rows = []
    n_sub = n_pair = 0
    for q in view.questions:
        qid = q["qid"]
        substrate_id = cn_identity(q["substrate_smiles"])
        refs = lib_sub.get(substrate_id, []) if substrate_id else []
        gold_ids = gold[qid]["gold_ids"]
        pair_in = False
        pair_refs: list[str] = []
        if substrate_id:
            for p, ref in lib_pairs.get(substrate_id, []):
                if p in gold_ids:
                    pair_in = True
                    pair_refs.append(ref)
        if refs:
            n_sub += 1
        if pair_in:
            n_pair += 1
        rows.append({"qid": qid, "input_index": q["input_index"],
                     "substrate_identity": substrate_id or "",
                     "substrate_in_library": bool(refs),
                     "n_library_records_for_substrate": len(refs),
                     "gold_pair_in_library": pair_in,
                     "pair_record_refs": ";".join(sorted(pair_refs)[:5])})
    summary = {
        "library_path": str(library_path),
        "library_sha256": _sha256(library_path),
        "n_library_records": len(records),
        "n_library_unparseable_substrate": n_unparseable,
        "n_questions_substrate_overlap": n_sub,
        "n_questions_gold_pair_overlap": n_pair,
        "definition": ("底物身份重叠=exam 底物 cn 身份出现在 library_full "
                       "donor_smiles cn 身份;底物-产物对重叠=同一 cn 底物下"
                       "任一记录产物 cn 身份等于该题金标产物 cn 身份"),
        "rule_coverage": "not_assessed(规则资产匹配语义未在本阶段核实)",
        "note": "重叠率是描述统计,不能单凭它证明性能差异的因果来源;"
                "检索/引擎对 library 的实际使用方式未在此核实",
    }
    return rows, summary


# ---------------------------------------------------------------- 主流程


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--gold", required=True)
    ap.add_argument("--v1-scoring", default=None)
    ap.add_argument("--v41-baseline", default=None)
    ap.add_argument("--asset-library", default=None)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--input-manifest", default=None,
                    help="默认 <out-dir>/input_manifest.json;复算必经,缺失即失败")
    ap.add_argument("--init-input-manifest", action="store_true",
                    help="一次性初始化清单(仅在核验过的封存副本上使用);"
                         "已存在时严禁覆盖,正常复算不得携带本标志")
    ap.add_argument("--no-anchor-gate", action="store_true",
                    help="锚点不一致仍写全部产物(仅诊断用),退出码仍为 1")
    args = ap.parse_args(argv)

    run_dir = Path(args.run_dir)
    gold = Path(args.gold)
    v1 = Path(args.v1_scoring) if args.v1_scoring else None
    v41 = Path(args.v41_baseline) if args.v41_baseline else None
    assets = Path(args.asset_library) if args.asset_library else None
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = Path(args.input_manifest) if args.input_manifest \
        else out_dir / "input_manifest.json"

    if args.init_input_manifest:
        if manifest_path.is_file():
            raise ScorerV2Error(
                "输入清单已存在,严禁覆盖(初始化只能进行一次;若封存输入"
                "确已变更,应另立目录并重新走初始化+核验流程)",
                {"path": str(manifest_path)})
        manifest_path.write_text(
            json.dumps(build_input_manifest(run_dir, gold, v1, v41, assets),
                       ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8")
    if not manifest_path.is_file():
        raise ScorerV2Error(
            "输入清单缺失,拒绝复算(应先在核验过的封存副本上用 "
            "--init-input-manifest 一次性初始化;复算命令不得重建清单)",
            {"path": str(manifest_path)})
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    verify_input_manifest(manifest, run_dir, gold, v1, v41, assets)

    recon: dict = {"anchors": {}, "ok": True}
    recon["inputs"] = {
        "run_dir": str(run_dir), "gold": str(gold),
        "v1_scoring": str(v1) if v1 else None,
        "v41_baseline": str(v41) if v41 else None,
        "asset_library": str(assets) if assets else None,
        "input_manifest": str(manifest_path),
        "n_manifest_files": sum(g["n_files"] for g in manifest["groups"]),
    }

    # ---- A0:同口径重评分 v2(正式逐题评分文件,含输入 SHA)
    agent_pred_path = run_dir / "agent_batch" / "merged" / "predictions.jsonl"
    engine_res_path = run_dir / "engine_arm" / "engine_results.jsonl"
    scores = score_exam_v2(
        agent_predictions_path=agent_pred_path,
        engine_results_path=engine_res_path,
        gold_questions_path=gold,
        out_path=out_dir / "score_v2.json",
        inputs_sha={
            "agent_predictions": _sha256(agent_pred_path),
            "engine_results": _sha256(engine_res_path),
            "gold_questions": _sha256(gold),
        })
    # 回读对账:正式评分文件必须与后续各 TSV 同源同值
    sealed_scores = json.loads(
        (out_dir / "score_v2.json").read_text(encoding="utf-8"))
    _check = {(q["qid"]): (q["agent_rank"], q["engine_rank"])
              for q in sealed_scores["per_question"]}
    if len(_check) != len(sealed_scores["per_question"]) \
            or len(_check) != sealed_scores["summary"]["n_questions"]:
        raise ScorerV2Error("score_v2.json qid 缺失或重复", {})
    if sealed_scores["summary"].get("scorer_version") != "v43-ec298-scorer-2":
        raise ScorerV2Error("score_v2.json 版本不符", {})
    if {q["qid"]: (q["agent_rank"], q["engine_rank"])
            for q in scores["per_question"]} != _check:
        raise ScorerV2Error("score_v2.json 与内存评分逐题不一致(回读失败)", {})
    s = scores["summary"]
    diff = diff_v1_v2(v1_scoring_path=v1, v2_result=scores,
                      engine_results_path=run_dir / "engine_arm"
                      / "engine_results.jsonl",
                      agent_predictions_path=run_dir / "agent_batch"
                      / "merged" / "predictions.jsonl")
    mc = multicomponent_sensitivity(
        agent_predictions_path=run_dir / "agent_batch" / "merged"
        / "predictions.jsonl",
        engine_results_path=run_dir / "engine_arm" / "engine_results.jsonl",
        gold_questions_path=gold)
    write_tsv(out_dir / "score_v1_v2_diff.tsv", DIFF_COLUMNS, diff["rows"])
    mc_cols = ["qid", "category", "agent_rank_main",
               "agent_rank_sensitivity", "engine_rank_main",
               "engine_rank_sensitivity", "changed"]
    write_tsv(out_dir / "multicomponent_sensitivity.tsv", mc_cols,
              mc["per_question"])

    for key, actual in [
        ("n_questions", s["n_questions"]),
        ("agent_hit@1", s["agent"]["hit@1"]),
        ("agent_hit@3", s["agent"]["hit@3"]),
        ("agent_hit@5", s["agent"]["hit@5"]),
        ("engine_hit@1", s["engine_top10"]["hit@1"]),
        ("engine_hit@3", s["engine_top10"]["hit@3"]),
        ("engine_hit@5", s["engine_top10"]["hit@5"]),
        ("engine_hit@10", s["engine_top10"]["hit@10"]),
        ("tier_engine_top10_hit", s["tiers_v2"]["engine_top10_hit"]),
        ("tier_not_in_exported_top10",
         s["tiers_v2"]["not_in_exported_top10"]),
        ("v1v2_agent_rank_changed", diff["summary"]["n_agent_rank_changed"]),
        ("v1v2_engine_rank_changed", diff["summary"]["n_engine_rank_changed"]),
        ("mc_agent_hit@1", mc["summary"]["agent"]["hit@1"]),
        ("mc_agent_hit@3", mc["summary"]["agent"]["hit@3"]),
        ("mc_agent_hit@5", mc["summary"]["agent"]["hit@5"]),
        ("mc_engine_hit@1", mc["summary"]["engine_top10"]["hit@1"]),
        ("mc_engine_hit@3", mc["summary"]["engine_top10"]["hit@3"]),
        ("mc_engine_hit@5", mc["summary"]["engine_top10"]["hit@5"]),
    ]:
        recon["anchors"][key] = {"expected": ANCHORS[key], "actual": actual,
                                 "ok": actual == ANCHORS[key]}

    # ---- 封存视图 + A1–A6
    view = load_sealed_run_view(run_dir)
    gold_ids_fn = _gold_ids_fn(gold)

    a1_rows, a1_summary = build_agent_hits_by_engine_tier(
        view, scores, gold_ids_fn)
    write_tsv(out_dir / "agent_hits_by_engine_tier.tsv", A1_COLUMNS, a1_rows)
    write_tsv(out_dir / "agent_hits_by_engine_tier_summary.tsv",
              A1_SUMMARY_COLUMNS, a1_summary)

    a2_rows, a2_extra, a2_audits = build_awaiting_prediction_fates(
        view, scores)
    write_tsv(out_dir / "awaiting_prediction_fates.tsv", A2_COLUMNS, a2_rows)
    write_tsv(out_dir / "awaiting_prediction_fates_summary.tsv", A2_COLUMNS,
              a2_extra)
    recon["awaiting_prediction_audit"] = a2_audits
    recon["anchors"]["a2_awaiting_rows"] = {
        "expected": ANCHORS["a2_awaiting_rows"], "actual": len(a2_rows),
        "ok": len(a2_rows) == ANCHORS["a2_awaiting_rows"]}
    recon["anchors"]["a2_budget_rows"] = {
        "expected": ANCHORS["a2_budget_rows"], "actual": len(a2_extra),
        "ok": len(a2_extra) == ANCHORS["a2_budget_rows"]}
    for outcome, key in (("abstained", "a2_outcome_abstained"),
                         ("rejected", "a2_outcome_rejected")):
        actual = a2_audits["outcomes"].get(outcome, 0)
        recon["anchors"][key] = {"expected": ANCHORS[key], "actual": actual,
                                 "ok": actual == ANCHORS[key]}

    a3_rows, a3_detail, a3_audits = build_decision_path_contribution(
        view, scores)
    write_tsv(out_dir / "decision_path_contribution.tsv", A3_COLUMNS, a3_rows)
    write_tsv(out_dir / "decision_path_contribution_detail.tsv",
              A3_DETAIL_COLUMNS, a3_detail)
    recon["decision_path_audit"] = a3_audits
    by_group = {(r["group"], r["subgroup"]): r for r in a3_rows}
    for (grp, sub), key in [
        (("recorded_direct", "commit_recorded"), "a3_recorded_direct"),
        (("rank_candidates", "selected"), "a3_rank_candidates"),
        (("analogy_edit", "analogy_abstained"), "a3_analogy_abstained"),
        (("analogy_edit", "analogy_rejected"), "a3_analogy_rejected"),
        (("analogy_edit", "analogy_proposed"), "a3_analogy_proposed"),
        (("novel_proposal", "proposed"), "a3_novel_proposal"),
    ]:
        actual = by_group.get((grp, sub), {}).get("n_questions", 0)
        recon["anchors"][key] = {"expected": ANCHORS[key], "actual": actual,
                                 "ok": actual == ANCHORS[key]}
    sum1 = sum(r["agent_hit@1"] for r in a3_rows)
    sum5 = sum(r["agent_hit@5"] for r in a3_rows)
    recon["anchors"]["a3_agent@1_sum"] = {
        "expected": ANCHORS["a3_agent@1_sum"], "actual": sum1,
        "ok": sum1 == ANCHORS["a3_agent@1_sum"]}
    recon["anchors"]["a3_agent@5_sum"] = {
        "expected": ANCHORS["a3_agent@5_sum"], "actual": sum5,
        "ok": sum5 == ANCHORS["a3_agent@5_sum"]}

    a4_rows, a4_audits = build_hit5_paired_attribution(view, scores,
                                                       gold_ids_fn)
    write_tsv(out_dir / "hit5_paired_attribution.tsv", A4_COLUMNS, a4_rows)
    engine_only = [r for r in a4_rows if r["direction"] == "engine_only"]
    agent_only = [r for r in a4_rows if r["direction"] == "agent_only"]
    write_tsv(out_dir / "hit5_engine_only.tsv", A4_COLUMNS, engine_only)
    write_tsv(out_dir / "hit5_agent_only.tsv", A4_COLUMNS, agent_only)
    recon["hit5_audit"] = a4_audits
    recon["anchors"]["a4_engine_only"] = {
        "expected": ANCHORS["a4_engine_only"], "actual": len(engine_only),
        "ok": len(engine_only) == ANCHORS["a4_engine_only"]}
    recon["anchors"]["a4_agent_only"] = {
        "expected": ANCHORS["a4_agent_only"], "actual": len(agent_only),
        "ok": len(agent_only) == ANCHORS["a4_agent_only"]}
    width = Counter(q["n_predicted"] for q in scores["per_question"])
    for w in range(6):
        key = f"width_{w}"
        recon["anchors"][key] = {"expected": ANCHORS[key],
                                 "actual": width.get(w, 0),
                                 "ok": width.get(w, 0) == ANCHORS[key]}

    if v41 is not None:
        a5_rows, a5_summary = build_v41_baseline_diff(scores, v41)
        write_tsv(out_dir / "v41_baseline_diff.tsv", A5_COLUMNS, a5_rows)
        recon["v41_baseline"] = a5_summary
    if assets is not None:
        ao_rows, ao_summary = build_asset_exam_overlap(
            view, scores, gold, assets)
        ao_cols = ["qid", "input_index", "substrate_identity",
                   "substrate_in_library", "n_library_records_for_substrate",
                   "gold_pair_in_library", "pair_record_refs"]
        write_tsv(out_dir / "asset_exam_overlap.tsv", ao_cols, ao_rows)
        recon["asset_overlap"] = ao_summary

    a6_rows, a6_summary = build_llm_call_distribution(view)
    write_tsv(out_dir / "llm_call_distribution.tsv", A6_COLUMNS, a6_rows)
    recon["llm_call_audit"] = a6_summary
    for key, actual in [("a6_total_issued", a6_summary["total_issued"]),
                        ("a6_total_provider_ok",
                         a6_summary["total_provider_ok"]),
                        ("a6_total_failed", a6_summary["total_failed"]),
                        ("a6_total_orphans", a6_summary["total_orphans"])]:
        recon["anchors"][key] = {"expected": ANCHORS[key], "actual": actual,
                                 "ok": actual == ANCHORS[key]}

    # ---- 收尾:锚点对账 + 输出清单
    recon["ok"] = all(a["ok"] for a in recon["anchors"].values())
    recon_path = out_dir / "anchor_reconciliation.json"
    recon_path.write_text(
        json.dumps(recon, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n", encoding="utf-8")
    outputs = sorted(p for p in out_dir.rglob("*")
                     if p.is_file() and p.name != "output_manifest.sha256")
    (out_dir / "output_manifest.sha256").write_text(
        "".join(f"{_sha256(p)}  {p.relative_to(out_dir)}\n" for p in outputs),
        encoding="utf-8")

    failed = [k for k, a in recon["anchors"].items() if not a["ok"]]
    print(json.dumps({"anchors_ok": recon["ok"], "failed_anchors": failed,
                      "out_dir": str(out_dir)}, ensure_ascii=False))
    return 0 if recon["ok"] else 1


def _gold_ids_fn(gold_questions: Path):
    from pathway_v43.exam_v2 import load_gold

    gold = load_gold(gold_questions)
    return lambda qid: gold[qid]["gold_ids"]


if __name__ == "__main__":
    sys.exit(main())
