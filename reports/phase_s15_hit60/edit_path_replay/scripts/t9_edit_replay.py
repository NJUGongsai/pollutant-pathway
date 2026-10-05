#!/usr/bin/env python3
"""HIT60 T9 编辑路径修复后重放（零 LLM、零 API、确定性）。

对封存 run 的**编辑输入**（底物/编辑列表/声明目标/供体引用）用当前工作树
（含 T4 门禁修复）的确定性编辑执行与门禁链路重放，回答「编辑路径从全灭
能否活过来」。重放链 = workflow/nodes.py `_apply_analogy` 的五步确定性
门禁：①供体引用 → ②validate_edits → ③execute_edits →
④check_target_consistency → ⑤空编辑 no-op 策略（allow_noop_edit 默认
False）。不调模型、不重跑采样、不改任何既有判定与正式分数。

三批对象：
  批1  旧「8 题编辑重放」集（298 首跑 ec298_v43r1 封存镜像本地只读；
       修复前结论读 reports/ec298/phase_c/rejections_reclassified.tsv）；
  批2a Phase D 重测 C0 臂 12 道 edit_blocked 题（boundary_pools 口径：
       11 empty_no_model_answer + 1 validation_rejected_gold b978fd0b；
       原始输入由 t9_remote_extract.py 从远端只读抽取，存 raw_inputs/）；
  批2b dev 56 中走 analogy_edit 路由的题（S1 六批固定 3 qid × 6 批；
       S1 部署时已含 T4 修复，重放为确定性回归对照）。

金标红线：金标只读；比对结论以旗标（true/false）呈现，金标/产物 SMILES
一律不进发布层（发布 TSV 只放 SHA 摘要与旗标；全文落 gitignored
raw_inputs/）。封存 run 只读。

用法（零 API）：
  PYTHONPATH=src python reports/phase_s15_hit60/edit_path_replay/\
scripts/t9_edit_replay.py --out-dir <默认本目录>
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "src"))

from pathway_v43.domain.identity import cn_identity  # noqa: E402
from pathway_v43.services.atom_tool import (  # noqa: E402
    AtomToolError,
    check_target_consistency,
    execute_edits,
    molecode_to_smiles,
    render,
    roundtrip,
    validate_edits,
)
from pathway_v43.validation.gates import validate_event_products  # noqa: E402

BATCH1_QIDS = [
    "RXNG_7701b6993b95ebfde638f35a13f1abe8db8ff759bf02454fce1b1b2d85dfe290",
    "RXNG_4609b23a9a27f029353385400c8fdf50a19eef7bbd2491eb1f4fdfb4fbc622b3",
    "RXNG_208874cbe2e550f5885e5c562659d1c5134d67e4dcd560189dac53c6ecd83f27",
    "RXNG_30ab4108da3213983d12306acf49388d00f9fa00bf191bde5b67ed93ad5b58ca",
    "RXNG_cf89ba3622826560b8082880111fc252d7f37e9ed73228b6a98804e5a3f1f1c0",
    "RXNG_d7656c5f483c6fc47cf8bee05acb7584140c31471009aa6eff684ee389dcc6a0",
    "RXNG_6455b8da465a85681898b43b23ba043ab9ad2f782f0cc4513f798f2f0a5ee131",
    "RXNG_7d281486c756d2eade2bbfde663f03ffe85dbd8336b60fa8b7fcc149861d2e4b",
]


def sha256_file(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def sha12(s: str) -> str:
    return hashlib.sha256((s or "").encode()).hexdigest()[:12] if s else ""


def read_payload(p: Path):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))["payload"]
    except Exception:
        return None


def gold_index(path: Path) -> dict[str, set]:
    """qid → 金标产物 cn 身份集合（只读；旗标用，不外泄内容）。"""
    out: dict[str, set] = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            row = json.loads(line)
            qid = row["qid"]
            if "RXNG_" in str(qid) and "RXNG_" not in qid:
                qid = qid[qid.index("RXNG_"):]
            products = row.get("products_smiles") or []
            if isinstance(products, str):
                try:
                    products = json.loads(products)
                except Exception:
                    products = []
            out[qid] = {cn_identity(s) or s for s in products if s}
    return out


def collect_batch1(seal_run: Path) -> list[dict]:
    """批1：封存首跑的 analogy_edit 任务（只读本地镜像）。"""
    rows = []
    agent_runs = seal_run / "agent_runs"
    for qid in BATCH1_QIDS:
        found = False
        for run_dir in sorted(agent_runs.glob(f"*_{qid}")):
            for td in sorted((run_dir / "results").iterdir()):
                pt = read_payload(td / "prediction_task.json")
                if not pt or pt.get("mode") != "analogy_edit":
                    continue
                pred = read_payload(td / "prediction.json") or {}
                cur = pt.get("current") or {}
                donor = pt.get("donor") or {}
                parsed = pred.get("parsed") or {}
                rows.append({
                    "batch_label": "批1-旧8题(298首跑)",
                    "batch": "ec298_v43r1",
                    "qid": qid,
                    "run_name": run_dir.name,
                    "task_id": td.name,
                    "substrate": cur.get("identity")
                    or cur.get("smiles_canonical") or "",
                    "sealed_atom_ids": list(cur.get("atom_ids") or []),
                    "edits": list(parsed.get("edits") or []),
                    "target_molecode": parsed.get("target_molecode") or "",
                    "parsed_decision": parsed.get("decision"),
                    "referenced_evidence_id":
                        parsed.get("referenced_evidence_id"),
                    "donor_evidence_id": donor.get("evidence_id"),
                    "recorded_outcome": pred.get("outcome"),
                    "recorded_fail_reason": pred.get("fail_reason"),
                    "recorded_checks": pred.get("atomtool_checks") or {},
                })
                found = True
        if not found:
            rows.append({"batch_label": "批1-旧8题(298首跑)", "qid": qid,
                         "error": "seal_task_not_found"})
    return rows


def replay(row: dict) -> dict:
    """对单条编辑输入跑五步确定性门禁（当前工作树=修复后代码）。"""
    out = {
        "step1_donor_ref_ok": None,
        "step2_validate_ok": None,
        "step3_execute_ok": None,
        "step4_target_ok": None,
        "step5_noop_ok": None,
        "step6_product_validation_ok": None,
        "identity_drift": None,
        "render_mode": "",
        "reasons": [],
        "note": "",
        "product_smiles": "",
        "product_mapped_smiles_present": None,
        "fail_stage": "",
        "classification": "",
    }
    # 模型主动弃答（parsed.decision=abstain）：无提案，门禁链不适用
    if row.get("parsed_decision") == "abstain" or str(
            row.get("recorded_outcome") or "") == "abstained":
        out["fail_stage"] = "not_applicable"
        out["classification"] = "abstained_no_proposal"
        return out
    substrate = row.get("substrate") or ""
    edits = row.get("edits") or []
    target = row.get("target_molecode") or ""
    if not substrate:
        out["reasons"] = ["input_missing:substrate"]
        out["fail_stage"] = "input"
        out["classification"] = "not_replayable"
        return out
    # ① 供体引用（工作流第 1 步；与 T4 修复无关，但完整复现链路）
    ref, donor_ev = row.get("referenced_evidence_id"), \
        row.get("donor_evidence_id")
    if ref is None and donor_ev is None:
        out["step1_donor_ref_ok"] = "not_applicable"
    else:
        out["step1_donor_ref_ok"] = bool(ref == donor_ev) \
            if (ref is not None and donor_ev is not None) else False
        if out["step1_donor_ref_ok"] is False:
            out["reasons"].append(
                f"donor_reference_mismatch:model={ref!r}_selected={donor_ev!r}")
            out["fail_stage"] = "step1_donor_ref"
            out["classification"] = "not_executable"
            return out
    # 底物渲染（工作流 _real_render 用 roundtrip；失败回退 render 并记录）
    try:
        fresh = roundtrip(substrate, name="S")
        out["render_mode"] = "roundtrip"
    except AtomToolError:
        try:
            fresh = render(substrate, name="S")
            out["render_mode"] = "render_fallback"
        except AtomToolError as e:
            out["reasons"].append(f"substrate_unrenderable:{e.kind}")
            out["fail_stage"] = "render"
            out["classification"] = "not_replayable"
            return out
    sealed = set(row.get("sealed_atom_ids") or [])
    out["identity_drift"] = bool(sealed) and set(fresh.atom_ids) != sealed
    if out["identity_drift"]:
        out["reasons"].append("identity_drift:封存原子ID与现渲染不一致")
        out["fail_stage"] = "render"
        out["classification"] = "not_replayable_drift"
        return out
    # ② 结构化校验
    v = validate_edits(fresh, edits)
    out["step2_validate_ok"] = v["ok"]
    if not v["ok"]:
        out["reasons"].extend(v["reasons"][:6])
        out["fail_stage"] = "step2_validate"
        out["classification"] = "not_executable"
        return out
    # ③ 顺序执行
    e = execute_edits(fresh, edits)
    out["step3_execute_ok"] = e["ok"]
    if not e["ok"]:
        out["reasons"].extend(e["reasons"][:6])
        out["fail_stage"] = "step3_execute"
        out["classification"] = "not_executable"
        return out
    out["product_smiles"] = e.get("product_smiles", "")
    out["product_mapped_smiles_present"] = bool(
        e.get("product_mapped_smiles"))
    # ④ 目标对账（T4 修复主战场：canonical 双口径短路 + 统一索引空间）
    tg = check_target_consistency(fresh, e, target)
    out["step4_target_ok"] = tg["ok"]
    out["note"] = tg.get("note", "")
    if not tg["ok"]:
        out["reasons"].extend(tg["reasons"][:6])
        out["fail_stage"] = "step4_target_consistency"
        out["classification"] = "not_executable"
        return out
    # ⑤ 空编辑 no-op 策略（allow_noop_edit 默认 False）
    if not edits:
        out["step5_noop_ok"] = False
        out["reasons"].append("noop_edit_not_allowed:empty_edits_rejected")
        out["fail_stage"] = "step5_noop_policy"
        out["classification"] = "not_executable_noop"
        return out
    out["step5_noop_ok"] = True
    # ⑥ 产物验证（validate_event_products；类比提案卡 =
    # analog_reaction + model_analogy_transfer → check_elements=True）。
    # 重放边界声明：ancestry 取 [底物 cn]（祖先链含当前底物即最保守
    # 环检）；既有兄弟路径集合未知 → 空（sibling_dedup 跨路径分支不在
    # 重放面）；方向/来源门禁需完整路径上下文，不在重放面（T4 修复
    # 不触这两处）。
    ev = {"products": [{
        "product_smiles": out["product_smiles"],
        "product_identity": cn_identity(out["product_smiles"]) or "",
    }]}
    verdicts = validate_event_products(
        evidence=ev,
        ancestry_cns=[cn_identity(substrate) or substrate],
        existing_sibling_cns=set(),
        substrate_smiles=substrate,
        check_elements=True,
    )
    out["step6_product_validation_ok"] = all(v.accepted for v in verdicts)
    if not out["step6_product_validation_ok"]:
        out["reasons"].extend(
            [r for v in verdicts for r in v.reasons][:6])
        out["fail_stage"] = "step6_product_validation"
        out["classification"] = "executable_gate_only_product_rejected"
        return out
    out["classification"] = "executable"
    return out


def pre_fix_view(row: dict, phase_c: dict, pools: dict) -> dict:
    """修复前结论（只读既有文档/封存产物，不重放旧代码）。"""
    if row["batch_label"].startswith("批1"):
        pc = phase_c.get(row["qid"]) or {}
        return {
            "source": "phase_c_offline_audit(rejections_reclassified.tsv)",
            "verdict": pc.get("new_classification", ""),
            "validate_ok": pc.get("new_validate_ok", ""),
            "execute_ok": pc.get("new_execute_ok", ""),
            "target_ok": pc.get("new_target_ok", ""),
            "reason_head": pc.get("new_reasons", "")[:120],
            "gold_label": ("target_matches_gold"
                           if str(pc.get("target_matches_gold_diagnostic")
                                  ).lower() == "true" else "no_gold_match"),
        }
    if row["batch_label"].startswith("批2a"):
        checks = row.get("recorded_checks") or {}
        tc = checks.get("target_consistency") or {}
        return {
            "source": "pd_retest_C0_run_record(atomtool_checks)",
            "verdict": "gate_rejected",
            "validate_ok": (checks.get("edit_validation") or {}).get("ok"),
            "execute_ok": (checks.get("edit_execution") or {}).get("ok"),
            "target_ok": tc.get("ok"),
            "reason_head": str(row.get("recorded_fail_reason") or "")[:120],
            "gold_label": pools.get(row["qid"], ""),
        }
    checks = row.get("recorded_checks") or {}
    tc = checks.get("target_consistency") or {}
    return {
        "source": "s1_dev_run_record(S1部署已含T4修复)",
        "verdict": row.get("recorded_outcome") or "",
        "validate_ok": (checks.get("edit_validation") or {}).get("ok"),
        "execute_ok": (checks.get("edit_execution") or {}).get("ok"),
        "target_ok": tc.get("ok"),
        "reason_head": str(row.get("recorded_fail_reason") or "")[:120],
        "gold_label": "",
    }


def main() -> int:
    here = Path(__file__).resolve().parent.parent
    ap = argparse.ArgumentParser()
    ap.add_argument("--seal-run-dir", default=str(
        Path("/Volumes/CC/Enzyme_Agent/ec298_phase_a_seal/"
             "dependingv43_dev/runs/ec298_v43r1")))
    ap.add_argument("--gold-298", default=str(
        Path("/Volumes/CC/Enzyme_Agent/ec298_phase_a_seal/"
             "ec298_gold_readonly/questions.jsonl")))
    ap.add_argument("--gold-dev", default=str(
        REPO / "reports/phase_s1_hit60/dev_gold/dev_gold.jsonl"))
    ap.add_argument("--remote-inputs", default=str(
        here / "raw_inputs/remote_edit_inputs.jsonl"))
    ap.add_argument("--phase-c-tsv", default=str(
        REPO / "reports/ec298/phase_c/rejections_reclassified.tsv"))
    ap.add_argument("--boundary-pools", default=str(
        REPO / "reports/phase_s0_hit60/boundary_pools.tsv"))
    ap.add_argument("--out-dir", default=str(here))
    args = ap.parse_args()
    out_dir = Path(args.out_dir)
    raw_dir = out_dir / "raw_inputs"
    raw_dir.mkdir(parents=True, exist_ok=True)

    # ---- 输入装载
    batch1 = collect_batch1(Path(args.seal_run_dir))
    remote = [json.loads(l) for l in open(args.remote_inputs)
              if l.strip()]
    batch2a = [r for r in remote if r.get("batch") == "ec298_pd_retest_C0"]
    batch2b = [r for r in remote if str(r.get("batch", "")).startswith("s1")]
    for r in batch2a:
        r["batch_label"] = "批2a-C0臂12题(298重测)"
    for r in batch2b:
        r["batch_label"] = "批2b-dev六批"
        t = r.get("task") or {}
        cur = t.get("current") or {}
        p = r.get("prediction") or {}
        parsed = p.get("parsed") or {}
        donor = t.get("donor") or {}
        r["substrate"] = cur.get("identity") or cur.get("smiles_canonical")
        r["sealed_atom_ids"] = cur.get("atom_ids") or []
        r["edits"] = parsed.get("edits") or []
        r["target_molecode"] = parsed.get("target_molecode") or ""
        r["parsed_decision"] = parsed.get("decision")
        r["referenced_evidence_id"] = parsed.get("referenced_evidence_id")
        r["donor_evidence_id"] = donor.get("evidence_id")
        r["recorded_outcome"] = p.get("outcome")
        r["recorded_fail_reason"] = p.get("fail_reason")
        r["recorded_checks"] = p.get("checks") or {}

    # 批2a 统一形状（远端抽取的字段名与 collect_batch1 对齐）
    for r in batch2a:
        t = r.get("task") or {}
        cur = t.get("current") or {}
        p = r.get("prediction") or {}
        parsed = p.get("parsed") or {}
        donor = t.get("donor") or {}
        r["substrate"] = cur.get("identity") or cur.get("smiles_canonical")
        r["sealed_atom_ids"] = cur.get("atom_ids") or []
        r["edits"] = parsed.get("edits") or []
        r["target_molecode"] = parsed.get("target_molecode") or ""
        r["parsed_decision"] = parsed.get("decision")
        r["referenced_evidence_id"] = parsed.get("referenced_evidence_id")
        r["donor_evidence_id"] = donor.get("evidence_id")
        r["recorded_outcome"] = p.get("outcome")
        r["recorded_fail_reason"] = p.get("fail_reason")
        r["recorded_checks"] = p.get("checks") or {}

    phase_c: dict[str, dict] = {}
    with open(args.phase_c_tsv, encoding="utf-8") as f:
        for r in csv.DictReader(f, delimiter="\t"):
            phase_c[r["qid"]] = r
    pools: dict[str, str] = {}
    with open(args.boundary_pools, encoding="utf-8") as f:
        for r in csv.DictReader(f, delimiter="\t"):
            if r.get("review_bucket") == "edit_blocked":
                pools[r["qid"]] = r.get("breakpoint_label", "")

    gold298 = gold_index(Path(args.gold_298))
    golddev = gold_index(Path(args.gold_dev))
    gold = {}
    gold.update({k: v for k, v in gold298.items()})
    gold.update(golddev)

    # ---- 重放
    all_rows = batch1 + batch2a + batch2b
    results = []
    for row in all_rows:
        if row.get("error"):
            results.append({"row": row, "replay": {
                "classification": "input_missing",
                "reasons": [row["error"]]}})
            continue
        rep = replay(row)
        pre = pre_fix_view(row, phase_c, pools)
        # 金标旗标（只读；旗标呈现，内容不外泄）
        tgt_smiles = molecode_to_smiles(row.get("target_molecode") or "")
        tgt_cn = cn_identity(tgt_smiles) if tgt_smiles else None
        prod_cn = cn_identity(rep.get("product_smiles") or "") or None
        gset = gold.get(row["qid"], set())
        rec_checks = row.get("recorded_checks") or {}
        rec_prod = ((rec_checks.get("edit_execution") or {})
                    .get("product_smiles")) or ""
        rec_cn = cn_identity(rec_prod) if rec_prod else None
        results.append({
            "row": row,
            "replay": rep,
            "pre_fix": pre,
            "gold_flags": {
                "target_matches_gold": bool(tgt_cn and tgt_cn in gset),
                "post_product_matches_gold": bool(
                    prod_cn and prod_cn in gset),
                "pre_product_matches_gold": bool(
                    rec_cn and rec_cn in gset),
            },
            "digests": {
                "substrate_sha12": sha12(row.get("substrate")),
                "post_product_sha12": sha12(rep.get("product_smiles")),
                "pre_product_sha12": sha12(rec_prod),
                "target_sha12": sha12(tgt_smiles or ""),
            },
        })

    # ---- 落盘 raw（gitignored，含 SMILES 原文）
    raw_path = raw_dir / "replay_raw_results.jsonl"
    with open(raw_path, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    # 批1 输入快照（含声明目标原文 → gitignored）
    with open(raw_dir / "batch1_sealed_inputs.jsonl", "w",
              encoding="utf-8") as f:
        for r in batch1:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # ---- 发布层 TSV（无 SMILES：旗标 + 摘要 + 拒因文本）
    tsv_path = out_dir / "replay_per_question.tsv"
    cols = [
        "batch_label", "qid", "task_id", "run_batch",
        "pre_fix_verdict", "pre_fix_validate_ok", "pre_fix_execute_ok",
        "pre_fix_target_ok", "pre_fix_reason_head", "pre_fix_gold_label",
        "post_validate_ok", "post_execute_ok", "post_target_ok",
        "post_noop_ok", "post_product_validation_ok",
        "post_short_circuit_note", "post_fail_stage",
        "post_classification", "post_reason_head",
        "delta_vs_pre_fix", "target_matches_gold",
        "post_product_matches_gold", "pre_product_matches_gold",
        "substrate_sha12", "post_product_sha12", "pre_product_sha12",
        "target_sha12", "render_mode", "product_mapped_smiles_present",
    ]

    def delta_of(r: dict) -> str:
        pre, rep = r["pre_fix"], r["replay"]
        if r["row"]["batch_label"].startswith("批2b"):
            rec = str(pre.get("verdict") or "")
            post_cls = rep.get("classification", "")
            if rec == "proposed":
                return ("consistent_with_run" if post_cls == "executable"
                        else "DIFFERS_from_run_record")
            if rec == "abstained":
                return ("abstained_no_proposal_not_replayable"
                        if r["replay"].get("classification")
                        == "abstained_no_proposal" else
                        "has_edits_replayed")
            if rec == "rejected":
                return ("consistent_with_run" if post_cls.startswith(
                    "not_executable") else "DIFFERS_from_run_record")
            return "unclassified_dev_delta"
        pre_ok = pre.get("target_ok")
        post_ok = rep.get("step4_target_ok")
        pre_exec = pre.get("verdict")
        if pre_exec in ("not_executable", "gate_rejected"):
            if post_ok is True:
                return "REVIVED_gate_pass"
            return ("still_blocked_at_" + (rep.get("fail_stage")
                                           or "unknown"))
        return "pre_fix_not_blocked"

    tsv_rows = []
    for r in results:
        row, rep, pre = r["row"], r["replay"], r["pre_fix"]
        gf = r["gold_flags"]
        tsv_rows.append({
            "batch_label": row.get("batch_label"),
            "qid": row.get("qid"),
            "task_id": row.get("task_id", ""),
            "run_batch": row.get("batch", ""),
            "pre_fix_verdict": pre.get("verdict"),
            "pre_fix_validate_ok": pre.get("validate_ok"),
            "pre_fix_execute_ok": pre.get("execute_ok"),
            "pre_fix_target_ok": pre.get("target_ok"),
            "pre_fix_reason_head": pre.get("reason_head"),
            "pre_fix_gold_label": pre.get("gold_label"),
            "post_validate_ok": rep.get("step2_validate_ok"),
            "post_execute_ok": rep.get("step3_execute_ok"),
            "post_target_ok": rep.get("step4_target_ok"),
            "post_noop_ok": rep.get("step5_noop_ok"),
            "post_product_validation_ok": rep.get(
                "step6_product_validation_ok"),
            "post_short_circuit_note": rep.get("note", ""),
            "post_fail_stage": rep.get("fail_stage"),
            "post_classification": rep.get("classification"),
            "post_reason_head": ";".join(rep.get("reasons", []))[:120],
            "delta_vs_pre_fix": delta_of(r),
            "target_matches_gold": gf["target_matches_gold"],
            "post_product_matches_gold": gf["post_product_matches_gold"],
            "pre_product_matches_gold": gf["pre_product_matches_gold"],
            "substrate_sha12": r["digests"]["substrate_sha12"],
            "post_product_sha12": r["digests"]["post_product_sha12"],
            "pre_product_sha12": r["digests"]["pre_product_sha12"],
            "target_sha12": r["digests"]["target_sha12"],
            "render_mode": rep.get("render_mode"),
            "product_mapped_smiles_present":
                rep.get("product_mapped_smiles_present"),
        })
    with open(tsv_path, "w", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, delimiter="\t")
        w.writeheader()
        w.writerows(tsv_rows)

    # ---- 汇总
    def count(label: str):
        rs = [r for r in results
              if r["row"].get("batch_label", "").startswith(label)]
        return {
            "n": len(rs),
            "revived_gate_pass": sum(
                1 for r in rs if "REVIVED" in delta_of(r)),
            "executable": sum(1 for r in rs if r["replay"].get(
                "classification") == "executable"),
            "still_blocked": sum(1 for r in rs if str(r["replay"].get(
                "classification", "")).startswith("not_executable")),
            "short_circuit_fired": sum(1 for r in rs if r["replay"].get(
                "note") == "canonical_equivalence_short_circuit"),
            "target_matches_gold": sum(1 for r in rs if r["gold_flags"][
                "target_matches_gold"]),
            "post_product_matches_gold": sum(1 for r in rs if r[
                "gold_flags"]["post_product_matches_gold"]),
        }
    b978 = next((r for r in results if "b978fd0b" in r["row"].get("qid", "")),
                None)
    src_files = sorted((REPO / "src/pathway_v43").rglob("*.py"))
    src_aggregate = hashlib.sha256(
        b"".join(f.read_bytes() for f in src_files)).hexdigest()
    summary = {
        "task": "HIT60 T9 edit-path replay (zero LLM, deterministic)",
        "code_identity": {
            "atom_tool_py_sha256":
                sha256_file(REPO / "src/pathway_v43/services/atom_tool.py"),
            "src_aggregate_sha256": src_aggregate,
            "n_src_files": len(src_files),
            "git_head": subprocess.run(
                ["git", "-C", str(REPO), "rev-parse", "HEAD"],
                capture_output=True, text=True).stdout.strip(),
            "note": "工作树含 T4 门禁修复(未提交);重放即该树行为",
        },
        "batch1_old8": count("批1"),
        "batch2a_c0_12": count("批2a"),
        "batch2b_dev_s1": {
            "n_task_instances": sum(
                1 for r in results if r["row"].get("batch_label", "")
                .startswith("批2b")),
            "n_unique_qids": len({r["row"].get("qid") for r in results
                                  if r["row"].get("batch_label", "")
                                  .startswith("批2b")}),
            "consistent_with_run_record": sum(
                1 for r in results
                if r["row"].get("batch_label", "").startswith("批2b")
                and delta_of(r) == "consistent_with_run"),
            "differs": sum(
                1 for r in results
                if r["row"].get("batch_label", "").startswith("批2b")
                and delta_of(r).startswith("DIFFERS")),
            "abstained_no_proposal": sum(
                1 for r in results
                if r["row"].get("batch_label", "").startswith("批2b")
                and delta_of(r).startswith("abstained")),
        },
        "b978fd0b_anchor": {
            "found": b978 is not None,
            "pre_fix_target_ok": (b978["pre_fix"].get("target_ok")
                                  if b978 else None),
            "post_fix_target_ok": (b978["replay"].get("step4_target_ok")
                                   if b978 else None),
            "short_circuit": (b978["replay"].get("note") if b978 else None),
            "post_product_matches_gold": (
                b978["gold_flags"]["post_product_matches_gold"]
                if b978 else None),
            "pre_product_matches_gold": (
                b978["gold_flags"]["pre_product_matches_gold"]
                if b978 else None),
        },
        "inputs": {
            "remote_edit_inputs_rows": len(remote),
            "gold_298_sha256": sha256_file(Path(args.gold_298)),
            "gold_dev_sha256": sha256_file(Path(args.gold_dev)),
            "phase_c_tsv_sha256": sha256_file(Path(args.phase_c_tsv)),
            "boundary_pools_sha256": sha256_file(Path(args.boundary_pools)),
        },
        "outputs": {
            "tsv": tsv_path.name,
            "raw_results_gitignored":
                "raw_inputs/replay_raw_results.jsonl",
            "raw_batch1_inputs_gitignored":
                "raw_inputs/batch1_sealed_inputs.jsonl",
        },
        "zero_llm": True,
    }
    (out_dir / "replay_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items()
                      if k != "code_identity"}, ensure_ascii=False,
                     indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
