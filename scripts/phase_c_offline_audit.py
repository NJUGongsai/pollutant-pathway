#!/usr/bin/env python
"""Phase C 离线审计(零 API、只读封存、金标仅限离线诊断列)。

任务书 §2(C0 原路由审计)、§6.5(旧 23 条编辑拒绝的离线再分类 + 旧 15 条
接纳的抽样检查)、§7(关闭类比开关的路由变化)。

数据源(全部只读,命令行显式传入):
- 封存首跑 agent_runs:results/<T>/prediction_task.json(mode=analogy_edit
  的任务)+ 同目录 decision.json / prediction.json / retrieval.json;
- 金标 questions.jsonl:**仅**用于"目标是否匹配金标"的独立诊断列,
  不进入新协议判定,更不回灌任何模型。

输出(--out-dir,默认 reports/ec298/phase_c/,不写封存目录):
- analogy_route_audit.tsv        66 条类比任务的原路由画像(找回状态/
                                 对齐策略/中心原子数/结局分布)
- rejections_reclassified.tsv    23 条旧拒绝 × 新编辑协议逐题再分类
- accepted_gate_check.tsv        旧接纳提案 × 新适用性门禁抽查
- routing_ablation_offline.tsv   逐题旧路由 vs 新门禁路由 vs 开关关闭
- summary.json                   各臂计数 + 输入 SHA256

再分类判定(确定性,全部可复算):
- identity_drift(封存任务书原子 ID 与现渲染不一致)→ uncertain;
- validate/execute/target_consistency 任一失败 → not_executable(带拒因);
- 三段全过 → executable。
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

from pathway_v43.domain.identity import cn_identity  # noqa: E402
from pathway_v43.services.atom_tool import (  # noqa: E402
    check_target_consistency,
    execute_edits,
    render,
    validate_edits,
)
from pathway_v43.services.donor_applicability import (  # noqa: E402
    ApplicabilityPolicy,
    build_eligibility,
)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))["payload"]
    except Exception:
        return None


def _tsv_write(path: Path, rows: list[dict]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    cols = list(rows[0].keys())
    lines = ["\t".join(cols)]
    for r in rows:
        lines.append("\t".join(
            str(r.get(c, "")).replace("\t", " ").replace("\n", " ")
            for c in cols))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _norm_qid(name: str) -> str:
    """run 目录名与金标 qid 的同一规范形(含 ``RXNG_`` 前缀)。

    Phase C R3 修复:run 目录为 ``exam298_<batch>_RXNG_<hash>``,金标 qid
    为 ``RXNG_<hash>`` —— 此前脚本剥掉前缀而金标保留,逐题查找全部落空,
    金标诊断列假性归零(把 8/23 报成 0/23)。两侧同用本函数,杜绝再错位。
    """
    return name[name.index("RXNG_"):] if "RXNG_" in name else name


def _gold_index(gold_path: Path) -> tuple[dict[str, set], list[str]]:
    """qid → 金标产物 cn 身份集合(仅诊断列用)。

    返回 (索引, 重复 qid 列表)。金标行重复若不显式检出,dict 会静默
    覆盖(三审反例:同 qid 两行 → 审计 0 退出照常产出)—— 由 main
    fail-closed,不产出可被误读的诊断列。
    """
    out: dict[str, set] = {}
    seen: set[str] = set()
    dupes: set[str] = set()
    with open(gold_path, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            row = json.loads(line)
            qid = _norm_qid(str(row["qid"]))
            if qid in seen:
                dupes.add(qid)
            seen.add(qid)
            products = row.get("products_smiles") or "[]"
            try:
                smis = json.loads(products) if isinstance(products, str) \
                    else list(products)
            except Exception:
                smis = []
            out[qid] = {
                cn_identity(s) or s for s in smis if s}
    return out, sorted(dupes)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seal-run-dir", required=True,
                    help="封存首跑 ec298_v43r1 目录(只读)")
    ap.add_argument("--gold", required=True,
                    help="金标 questions.jsonl(只读;仅诊断列)")
    ap.add_argument("--out-dir", default=str(REPO_ROOT / "reports"
                                              / "ec298" / "phase_c"))
    args = ap.parse_args()
    seal = Path(args.seal_run_dir)
    agent_runs = seal / "agent_runs"
    if not agent_runs.is_dir():
        print(f"FAIL: agent_runs 不存在:{agent_runs}", file=sys.stderr)
        return 2
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    gold, gold_dupes = _gold_index(Path(args.gold))

    # ---- 扫描封存产物:预测任务 × 同题 run 内按路径索引的 retrieval
    tasks: list[dict] = []
    for run_dir in sorted(agent_runs.iterdir()):
        if not run_dir.is_dir():
            continue
        qid = _norm_qid(run_dir.name)
        results = run_dir / "results"
        if not results.is_dir():
            continue
        # 检索产物按 (path_id, substrate_identity) 索引:retrieval.json 存在
        # 自己的检索 task 目录,与 prediction_task 目录不同
        retrievals: dict[tuple, dict] = {}
        for task_dir in sorted(results.iterdir()):
            ret = _read_json(task_dir / "retrieval.json")
            if not ret:
                continue
            q = ret.get("query") or {}
            retrievals[(q.get("path_id"), q.get("substrate_identity"))] = ret
        for task_dir in sorted(results.iterdir()):
            pt = _read_json(task_dir / "prediction_task.json")
            if not pt or pt.get("mode") != "analogy_edit":
                continue
            cur = pt.get("current") or {}
            ret = retrievals.get((pt.get("path_id"),
                                  cur.get("identity"))) or {}
            tasks.append({
                "qid": qid, "run_name": run_dir.name,
                "task_dir": task_dir,
                "task": pt,
                "decision": _read_json(task_dir / "decision.json"),
                "prediction": _read_json(task_dir / "prediction.json"),
                "retrieval": ret,
            })
    if not tasks:
        print("FAIL: 未找到 analogy_edit 任务", file=sys.stderr)
        return 2
    # fail-closed 自检(Phase C R2 复核 + 三审补强):**所有**审计任务
    # qid 必须在金标中且唯一,**金标行自身也不得重复**。初版只拒"零交集",
    # 漏一题仍 0 退出;金标同 qid 两行会被 dict 静默覆盖(三审端到端反例)
    # —— 空金标/缺题/任务题号重复/金标行重复任一发生都直接失败,
    # 不产出可被误读的诊断列。
    task_qids = [t["qid"] for t in tasks]
    missing = sorted({q for q in task_qids if q not in gold})
    dupes = sorted({q for q in task_qids if task_qids.count(q) > 1})
    n_qid_in_gold = sum(1 for q in set(task_qids) if q in gold)
    if not gold:
        print("FAIL: 金标索引为空(文件为空或全部不可解析);"
              "拒绝产出无金标对照的诊断列", file=sys.stderr)
        return 2
    if gold_dupes:
        print(f"FAIL: 金标行重复(same qid multiple rows):{gold_dupes[:3]}"
              f"…共 {len(gold_dupes)} 个;重复行会被索引静默覆盖,"
              "拒绝产出诊断列", file=sys.stderr)
        return 2
    if missing or dupes:
        print(f"FAIL: 金标覆盖不完整:missing={len(missing)}"
              f" {missing[:2]}… duplicate_qids={len(dupes)}"
              f" {dupes[:2]}…;拒绝产出缺题诊断列", file=sys.stderr)
        return 2

    # ---- 1) 原路由画像(§2 C0 审计)
    route_rows: list[dict] = []
    for t in tasks:
        donor = (t["task"].get("donor") or {})
        d = donor.get("donor") or {}
        align = d.get("alignment") or {}
        card = next((c for c in t["task"].get("candidates", [])
                     if c.get("evidence_id") == donor.get("evidence_id")),
                    {})
        pred = t["prediction"] or {}
        route_rows.append({
            "qid": t["qid"],
            "task_id": t["task_dir"].name,
            "mapping_status": card.get("mapping_status", ""),
            "mapping_reason": card.get("mapping_reason", ""),
            "n_donor_refs": len(card.get("donor_refs", [])),
            "donor_record_id": d.get("record_id", ""),
            "donor_mapping_quality": d.get("mapping_quality", ""),
            "alignment_strategy": align.get("strategy", ""),
            "n_aligned": align.get("n_aligned", ""),
            "n_center_atoms": len(d.get("center_atoms") or []),
            "outcome": pred.get("outcome", ""),
            "fail_or_reason_head": str(
                pred.get("fail_reason") or pred.get("reason") or "")[:160],
        })
    _tsv_write(out_dir / "analogy_route_audit.tsv", route_rows)

    # ---- 2) 旧拒绝 × 新编辑协议再分类(§6.5)
    reclass_rows: list[dict] = []
    n_class = Counter()
    for t in tasks:
        pred = t["prediction"] or {}
        if pred.get("outcome") != "rejected":
            continue
        parsed = pred.get("parsed") or {}
        substrate = (t["task"].get("current") or {}).get(
            "smiles_canonical", "")
        sealed_ids = set((t["task"].get("current") or {}).get(
            "atom_ids", []))
        classification, reasons = "uncertain", []
        validate_ok = execute_ok = target_ok = None
        product = ""
        try:
            fresh = render(substrate, name="S")
            identity_drift = set(fresh.atom_ids) != sealed_ids
        except Exception:
            fresh = None
            identity_drift = True
        if identity_drift or fresh is None:
            reasons.append("identity_drift:封存原子 ID 与现渲染不一致")
        else:
            edits = parsed.get("edits") or []
            v = validate_edits(fresh, edits)
            validate_ok = v["ok"]
            if not v["ok"]:
                reasons.extend(v["reasons"][:4])
            else:
                e = execute_edits(fresh, edits)
                execute_ok = e["ok"]
                if not e["ok"]:
                    reasons.extend(e["reasons"][:4])
                else:
                    tg = check_target_consistency(
                        fresh, e, parsed.get("target_molecode", ""))
                    target_ok = tg["ok"]
                    product = e["product_smiles"]
                    if not tg["ok"]:
                        reasons.extend(tg["reasons"][:4])
                    else:
                        classification = "executable"
            if classification != "executable" and not reasons:
                reasons.append("protocol_failed:no_reason_captured")
            if classification != "executable" and \
                    not any(r.startswith("identity_drift") for r in reasons):
                classification = "not_executable"
        old_reason_head = str(pred.get("fail_reason", ""))[:120]
        old_category = ("bond_already_present"
                        if "bond_already_present" in old_reason_head
                        else ("unknown_atom"
                              if "unknown_atom" in old_reason_head
                              else "other"))
        # 金标诊断列(独立于可执行性):目标 MoleCode 文本独立解析求身份
        from pathway_v43.services.atom_tool import molecode_to_smiles

        target_smiles = molecode_to_smiles(parsed.get("target_molecode", ""))
        target_identity = cn_identity(target_smiles) if target_smiles else ""
        gold_match = ""
        if target_identity:
            gold_match = str(
                target_identity in gold.get(t["qid"], set())).lower()
        n_class[classification] += 1
        reclass_rows.append({
            "qid": t["qid"],
            "task_id": t["task_dir"].name,
            "old_reject_category": old_category,
            "old_fail_reason_head": old_reason_head,
            "old_target_molecode_ok": (pred.get("atomtool_checks", {})
                                       .get("target_molecode", {})
                                       .get("ok", "")),
            "n_edits": len(parsed.get("edits") or []),
            "ops": ";".join(
                str(x.get("op", "?"))
                for x in (parsed.get("edits") or [])),
            "new_validate_ok": validate_ok,
            "new_execute_ok": execute_ok,
            "new_target_ok": target_ok,
            "new_classification": classification,
            "new_reasons": ";".join(reasons)[:300],
            "new_product_smiles": product,
            "target_matches_gold_diagnostic": gold_match,
            "note": ("诊断列:金标仅用于离线对照,不构成模型成绩;"
                     "结果不回灌模型"),
        })
    _tsv_write(out_dir / "rejections_reclassified.tsv", reclass_rows)

    # ---- 3) 旧接纳提案 × 新适用性门禁抽查(§6.5)
    gate_rows: list[dict] = []
    gate_status_count = Counter()
    for t in tasks:
        pred = t["prediction"] or {}
        if pred.get("outcome") != "proposed":
            continue
        substrate = (t["task"].get("current") or {}).get(
            "smiles_canonical", "")
        retrieval = (t["retrieval"] or {})
        evidences = retrieval.get("evidences", [])
        el = build_eligibility(evidences, substrate, ApplicabilityPolicy())
        card_status = el["status"]
        unverified = sorted({
            c for card in el["cards"]
            for c in (card.get("unverified_conditions") or [])})
        proposed_products = [
            p.get("product_identity", "")
            for p in (pred.get("proposed_card", {}) or {}).get("products", [])
        ]
        gold_match = any(p in gold.get(t["qid"], set())
                         for p in proposed_products)
        gate_status_count[card_status] += 1
        gate_rows.append({
            "qid": t["qid"],
            "task_id": t["task_dir"].name,
            "old_outcome": pred.get("outcome", ""),
            "proposed_product_identity": ";".join(
                p for p in proposed_products if p),
            "new_gate_status": card_status,
            "new_gate_fallback": el.get("fallback_reason", ""),
            "unverified_conditions": ";".join(unverified)[:200],
            "n_gate_cards": el.get("n_cards_evaluated", 0),
            "proposed_matches_gold_diagnostic": str(gold_match).lower(),
            "note": ("抽查:新门禁能否识别旧接纳提案的风险;"
                     "金标列为离线诊断,不构成成绩"),
        })
    _tsv_write(out_dir / "accepted_gate_check.tsv", gate_rows)

    # ---- 4) 路由消融(§7:关闭开关 / 新门禁;零调用模拟)
    abl_rows: list[dict] = []
    route_change = Counter()
    for t in tasks:
        substrate = (t["task"].get("current") or {}).get(
            "smiles_canonical", "")
        retrieval = (t["retrieval"] or {})
        el = build_eligibility(retrieval.get("evidences", []), substrate,
                               ApplicabilityPolicy())
        old_mode = "analogy_edit"
        new_mode = ("analogy_edit" if el["status"] == "applicable"
                    else "novel_or_hold")
        switch_off = "novel_or_hold"
        route_change[f"{old_mode}->{new_mode}"] += 1
        abl_rows.append({
            "qid": t["qid"],
            "task_id": t["task_dir"].name,
            "sealed_route": old_mode,
            "route_with_new_gate": new_mode,
            "route_with_analogy_disabled": switch_off,
            "eligibility_status": el["status"],
            "eligibility_fallback": el.get("fallback_reason", ""),
        })
    _tsv_write(out_dir / "routing_ablation_offline.tsv", abl_rows)

    # ---- 5) 汇总
    outcomes = Counter(r["outcome"] for r in route_rows)
    center_align = Counter(
        "center_only" if r["alignment_strategy"] ==
        "reaction_center_substructure" else "full_donor"
        for r in route_rows if r["alignment_strategy"])
    small_centers = sum(
        1 for r in route_rows
        if isinstance(r["n_center_atoms"], int) and r["n_center_atoms"] <= 3)
    summary = {
        "schema_version": "v43-phase-c-offline-audit-1",
        "zero_api": True,
        "inputs": {
            "seal_run_dir": str(seal),
            "seal_run_dir_sha256_note": "只读;未写封存目录",
            "gold_sha256": sha256_file(Path(args.gold)),
        },
        "n_analogy_tasks": len(tasks),
        "n_questions_with_analogy": len({r["qid"] for r in route_rows}),
        "n_task_qids_found_in_gold": n_qid_in_gold,
        "n_task_qids_missing_from_gold": len(missing),
        "n_task_qids_duplicate": len(dupes),
        "n_gold_unique_qids": len(gold),
        "n_gold_duplicate_qids": len(gold_dupes),
        "gold_coverage_gate": "task_qids_covered_unique_and_gold_rows_unique",
        "analogy_outcomes": dict(outcomes),
        "alignment_strategy_distribution": dict(center_align),
        "n_tasks_with_center_atoms_le_3": small_centers,
        "rejections_reclassified": dict(n_class),
        "accepted_gate_check": dict(gate_status_count),
        "routing_ablation_transitions": dict(route_change),
        "outputs": [
            "analogy_route_audit.tsv", "rejections_reclassified.tsv",
            "accepted_gate_check.tsv", "routing_ablation_offline.tsv",
            "summary.json",
        ],
    }
    (out_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
