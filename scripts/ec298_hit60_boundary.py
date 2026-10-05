#!/usr/bin/env python
"""HIT60 T0：EC298 复测 C0 失分池 L1–L5 精确边界表（零 API、零第三方依赖）。

依据 reports/phase_s0_hit60/registry_pool_definitions.md（先于计算冻结）：
主池按优先序互斥指派（L1 排序 / L2 选错 / L3 引擎有 agent 无[K=10 主口径，
K=5 辅助] / L4 真空区[子带 pure_vacuum | retrieval_saw_gold]），hit@1 命中
136 题不进池；L5 仅在提供 --pool-check 全池核验输入时才可标注，否则一律
维持 L4 + scope_limited。

输入锚点 fail-closed：298/136/50/44/24/44/17/31/13 及路由交叉（详见
ANCHORS）任一不符即写 anchor_mismatch.json 并退出码 2。

盲性纪律：金标只在本离线进程只读打开，仅写入 gitignored 的
manual_review/ 产物；boundary_pools.tsv、pool_summary.md、
review_checklist_goldfree.tsv 不含金标、不含底物、不含任何模型输出列。
--check 复算逐字节一致，不重写产物。

用法（本地，仅边界表）::

    python3 scripts/ec298_hit60_boundary.py \
      --audit-tsv reports/phase_d/retest/loss_audit/loss_audit_298_c0.tsv \
      --loss-audit-dir reports/phase_d/retest/loss_audit \
      --out-dir reports/phase_s0_hit60

用法（远端 Chenyu，含复核工作簿）::

    python3 /tmp/ec298_hit60_boundary.py \
      --audit-tsv reports/phase_d/retest/loss_audit/loss_audit_298_c0.tsv \
      --detail-tsv reports/phase_d/retest/loss_audit/miss_hit1_detail_c0.tsv \
      --loss-audit-dir reports/phase_d/retest/loss_audit \
      --gold /usrdata/EnzymeCAGE_data/workspaces/ec298_gold_readonly/questions.jsonl \
      --out-dir reports/phase_s0_hit60
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

SCRIPT_VERSION = "v43-hit60-s0-boundary-1"

# 归因报告 §2 已发布数字（防错行断言，非新统计）
ANCHORS = {
    "n_questions": 298,
    "hit1": 136,
    "pools": {"L1": 50, "L2": 44, "L3": 24, "L4": 44},
    "l3_k5": 17,
    "l4_subbands": {"l4_pure_vacuum": 31, "l4_retrieval_saw_gold": 13},
    "hits_by_mode": {"recorded_direct": 64, "rank_candidates": 26,
                     "analogy_edit": 8, "novel_proposal": 38},
    "l1_by_mode": {"novel_proposal": 27, "rank_candidates": 23,
                   "recorded_direct": 0, "analogy_edit": 0},
    "workbook": {"rank_selected": 13, "recorded_direct": 31, "edit_blocked": 12},
}

REST_LABELS = ("retrieval_absence_within_observed_scope", "unknown",
               "empty_no_model_answer", "validation_rejected_gold")
ENGINE_HAS_K10 = ("e1", "e2_5", "e6_10")
ENGINE_HAS_K5 = ("e1", "e2_5")

HINTS = {
    "rank_selected": (
        "rank 排序任务里有含金标的候选卡，最终选了别的卡。复核：金标产物是否唯一"
        "正确？是否存在多个同样合法的产物（多解）？金标口径是否有歧义？"),
    "recorded_direct": (
        "recorded 直通确定性提交了非金标的记录。复核：金标是否正确/唯一？多条 "
        "recorded 并存时金标的条件/方向是否更优？金标是否至少应为可接受答案之一？"),
    "edit_blocked": (
        "类比编辑被确定性门禁拒绝后无产物。复核：从该底物出发，金标产物是否确实"
        "可由常见生物降解步达成（金标本身合理）？还是金标存疑/不可达？"),
}


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _read_tsv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def _write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def _verify_against_loss_audit_manifest(loss_audit_dir: Path, audit_sha: str,
                                        detail_sha: str | None) -> None:
    """对账 loss_audit 封存 manifest，确保在封存产物上计算。"""
    manifest = {}
    for line in (loss_audit_dir / "output_manifest.sha256").read_text(
            encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) == 2:
            manifest[parts[1]] = parts[0]
    if manifest.get("loss_audit_298_c0.tsv") != audit_sha:
        raise SystemExit("loss_audit_298_c0.tsv SHA 与封存 manifest 不符")
    if detail_sha is not None and manifest.get("miss_hit1_detail_c0.tsv") != detail_sha:
        raise SystemExit("miss_hit1_detail_c0.tsv SHA 与封存 manifest 不符")


def assign_pools(rows: list[dict]) -> list[dict]:
    """纯函数：按登记文件 §2 优先序指派主池；不改输入行。"""
    out = []
    for r in rows:
        label = r["breakpoint_label"]
        reported_gold = r["reported_gold"] == "true"
        rank = r["gold_report_rank"]
        hit1 = reported_gold and rank == "1"
        if hit1:
            pool, pool_k5, l4_sub = "HIT1", "HIT1", ""
        elif reported_gold and rank in ("2", "3", "4", "5"):
            pool, pool_k5, l4_sub = "L1", "L1", ""
        elif label == "selected_wrong_product":
            pool, pool_k5, l4_sub = "L2", "L2", ""
        elif r["engine_bucket"] in ENGINE_HAS_K10:
            pool = "L3"
            pool_k5 = "L3" if r["engine_bucket"] in ENGINE_HAS_K5 else "L4"
            l4_sub = ""
        elif r["engine_bucket"] == "e_none":
            pool = pool_k5 = "L4"
            l4_sub = ("l4_pure_vacuum"
                      if label == "retrieval_absence_within_observed_scope"
                      else "l4_retrieval_saw_gold")
        else:
            raise SystemExit(f"无法指派池：qid={r['qid']} label={label} "
                             f"engine_bucket={r['engine_bucket']}")
        if label == "selected_wrong_product":
            bucket = ("rank_selected" if r["mode"] == "rank_candidates"
                      else "recorded_direct")
        elif label in ("empty_no_model_answer", "validation_rejected_gold"):
            bucket = "edit_blocked"
        else:
            bucket = ""
        out.append({
            "qid": r["qid"], "category": r["category"],
            "n_gold_products": r["n_gold_products"],
            "multi_gold": "true" if int(r["n_gold_products"] or 0) >= 2 else "false",
            "mode": r["mode"], "agent_rank": r["agent_rank"],
            "engine_rank": r["engine_rank"], "engine_bucket": r["engine_bucket"],
            "breakpoint_label": label, "hit1": "true" if hit1 else "false",
            "pool": pool, "pool_k5": pool_k5, "l4_subband": l4_sub,
            "scope_limited": "true" if pool == "L4" else "false",
            "retrieval_scope_gold": r["raw_retrieval_gold"],
            "review_bucket": bucket,
        })
    return sorted(out, key=lambda x: x["qid"])


def check_anchors(pools: list[dict]) -> dict:
    """守恒断言；返回汇总计数，不符即抛错。"""
    misses = [p for p in pools if p["hit1"] == "false"]
    cnt = lambda key, rows: Counter(p[key] for p in rows)  # noqa: E731
    pool_cnt = cnt("pool", misses)
    problems = []
    if len(pools) != ANCHORS["n_questions"]:
        problems.append(f"总数 {len(pools)} != 298")
    hits = [p for p in pools if p["hit1"] == "true"]
    if len(hits) != ANCHORS["hit1"]:
        problems.append(f"hit1 {len(hits)} != 136")
    for name, want in ANCHORS["pools"].items():
        if pool_cnt.get(name, 0) != want:
            problems.append(f"{name} {pool_cnt.get(name, 0)} != {want}")
    if sum(pool_cnt.values()) != len(misses):
        problems.append(f"主池未守恒：{dict(pool_cnt)} vs 失分 {len(misses)}")
    if cnt("pool_k5", misses).get("L3", 0) != ANCHORS["l3_k5"]:
        problems.append(f"L3@5 {cnt('pool_k5', misses).get('L3', 0)} != 17")
    sub = cnt("l4_subband", misses)
    for name, want in ANCHORS["l4_subbands"].items():
        if sub.get(name, 0) != want:
            problems.append(f"{name} {sub.get(name, 0)} != {want}")
    hb = cnt("mode", hits)
    for name, want in ANCHORS["hits_by_mode"].items():
        if hb.get(name, 0) != want:
            problems.append(f"hit/{name} {hb.get(name, 0)} != {want}")
    l1 = [p for p in misses if p["pool"] == "L1"]
    for name, want in ANCHORS["l1_by_mode"].items():
        got = sum(1 for p in l1 if p["mode"] == name)
        if got != want:
            problems.append(f"L1/{name} {got} != {want}")
    wb = Counter(p["review_bucket"] for p in misses if p["review_bucket"])
    for name, want in ANCHORS["workbook"].items():
        if wb.get(name, 0) != want:
            problems.append(f"workbook/{name} {wb.get(name, 0)} != {want}")
    if problems:
        return {"ok": False, "problems": problems}
    return {"ok": True, "n_misses": len(misses),
            "pools": dict(pool_cnt),
            "workbook": dict(wb)}


def build_outputs(audit_rows, detail_rows, gold, out_dir: Path,
                  audit_sha: str, detail_sha: str | None, gold_sha: str | None
                  ) -> dict[str, bytes]:
    pools = assign_pools(audit_rows)
    ac = check_anchors(pools)
    if not ac["ok"]:
        _write_bytes(out_dir / "anchor_mismatch.json",
                     json.dumps(ac, ensure_ascii=False, indent=2).encode())
        raise SystemExit(f"锚点不符(fail-closed)：{ac['problems']}")

    # boundary_pools.tsv（无金标、无底物、无模型输出）
    cols = ["qid", "category", "n_gold_products", "multi_gold", "mode",
            "agent_rank", "engine_rank", "engine_bucket", "breakpoint_label",
            "hit1", "pool", "pool_k5", "l4_subband", "scope_limited",
            "retrieval_scope_gold", "review_bucket"]
    lines = ["\t".join(cols)]
    for p in pools:
        lines.append("\t".join(str(p[c]) for c in cols))
    outputs = {"boundary_pools.tsv": ("\n".join(lines) + "\n").encode()}

    # pool_summary.md
    misses = [p for p in pools if p["hit1"] == "false"]
    mode_cross = Counter((p["pool"], p["mode"]) for p in misses)
    eng_cross = Counter((p["pool"], p["engine_bucket"]) for p in misses)
    md = ["# HIT60 S0 边界表汇总（C0 臂，零 API）", "",
          f"- 脚本版本 `{SCRIPT_VERSION}`；定义见 registry_pool_definitions.md（冻结）。",
          f"- 总数 298 / hit@1 136 / 失分 {len(misses)}；主池互斥守恒全过。", "",
          "| 池 | 题数 | 含义 |", "|---|---:|---|",
          "| L1 排序池 | 50 | 金标在答卷 2–5 位（novel 27 / rank 23） |",
          "| L2 选错池 | 44 | selected_wrong（recorded 直通 31 / rank 选卡 13） |",
          "| L3 引擎有 agent 无（K=10 主） | 24 | unknown 17 + empty 7；K=5 辅助口径 17 |",
          "| L4 真空区 | 44 | pure_vacuum 31（retrieval_absence）+ retrieval_saw_gold 13 |",
          "", "L5（v1 全池确无金标）本轮未核验（无 --pool-check 输入），L4 全部"
          "维持 scope_limited；L5 候选 = l4_pure_vacuum 31 题。", "",
          "## 与 teacher 指导书 §3 近似数的对账", "",
          "| 指导书 | 本表 | 差异说明 |", "|---|---|---|",
          "| L1 50 | 50 | 一致 |",
          "| L2 ~39 | 44 | 指导书取首跑口径；复测 selected_wrong=44 |",
          "| L3 23 | 24（K=10） | 指导书引 209 为引擎 hit@10；K=5 口径为 17 |",
          "| L4 89 | 44 | 指导书 89 = 112(@5 未中) − 23(引擎@5 有)的粗切；本表 L4 "
          "不含 L2 44，且把「引擎无但检索层见过金标」的 13 题单列子带 |",
          "| L5 ~33 | 待核验 | 对应本表 l4_pure_vacuum 31 题（范围限定口径） |",
          "", "## 主池 × 路由", ""]
    md += ["| 池 | recorded | rank | analogy | novel |", "|---|---:|---:|---:|---:|"]
    for pool in ("L1", "L2", "L3", "L4"):
        md.append("| {} | {} | {} | {} | {} |".format(
            pool,
            mode_cross.get((pool, "recorded_direct"), 0),
            mode_cross.get((pool, "rank_candidates"), 0),
            mode_cross.get((pool, "analogy_edit"), 0),
            mode_cross.get((pool, "novel_proposal"), 0)))
    md += ["", "## 主池 × 引擎位次", "",
           "| 池 | e1 | e2_5 | e6_10 | e_none |", "|---|---:|---:|---:|---:|"]
    for pool in ("L1", "L2", "L3", "L4"):
        md.append("| {} | {} | {} | {} | {} |".format(
            pool,
            eng_cross.get((pool, "e1"), 0), eng_cross.get((pool, "e2_5"), 0),
            eng_cross.get((pool, "e6_10"), 0), eng_cross.get((pool, "e_none"), 0)))
    outputs["pool_summary.md"] = ("\n".join(md) + "\n").encode()

    # 复核清单（金标无关部分；工作簿桶 56 题）
    detail_by_qid = {d["qid"]: d for d in detail_rows} if detail_rows else {}
    review = [p for p in pools if p["review_bucket"]]
    ck_cols = ["qid", "category", "n_gold_products", "mode", "engine_bucket",
               "breakpoint_label", "review_bucket", "review_hint",
               "raw_retrieval_gold_refs", "evidence_refs"]
    lines = ["\t".join(ck_cols)]
    for p in sorted(review, key=lambda x: (x["review_bucket"], x["qid"])):
        d = detail_by_qid.get(p["qid"], {})
        lines.append("\t".join([
            p["qid"], p["category"], p["n_gold_products"], p["mode"],
            p["engine_bucket"], p["breakpoint_label"], p["review_bucket"],
            HINTS[p["review_bucket"]],
            d.get("raw_retrieval_gold_refs", ""),
            d.get("evidence_refs", "")]))
    outputs["review_checklist_goldfree.tsv"] = ("\n".join(lines) + "\n").encode()

    # 复核工作簿（含底物+金标；仅 gitignored manual_review/）
    if gold is not None:
        if not detail_rows:
            raise SystemExit("工作簿需要 --detail-tsv")
        wb_cols = ["qid", "category", "substrate_smiles", "gold_products_smiles",
                   "n_gold_products", "multi_gold", "review_bucket", "review_hint",
                   "mode", "engine_bucket", "raw_retrieval_gold_refs",
                   "evidence_refs", "verdict", "rationale", "second_confirmer"]
        lines = ["\t".join(wb_cols)]
        for p in sorted(review, key=lambda x: (x["review_bucket"], x["qid"])):
            g = gold[p["qid"]]
            d = detail_by_qid[p["qid"]]
            lines.append("\t".join([
                p["qid"], g["category"], g["substrate_smiles"],
                "; ".join(g["products_smiles"]), p["n_gold_products"],
                p["multi_gold"], p["review_bucket"],
                HINTS[p["review_bucket"]], p["mode"], p["engine_bucket"],
                d.get("raw_retrieval_gold_refs", ""),
                d.get("evidence_refs", ""), "", "", ""]))
        outputs["manual_review/review_workbook_56.tsv"] = (
            "\n".join(lines) + "\n").encode()

        # 非盲人审附页：validation_rejected_gold 的 1 题（任务书单列人审）
        special = [p for p in pools
                   if p["breakpoint_label"] == "validation_rejected_gold"]
        if len(special) != 1:
            raise SystemExit(f"validation_rejected_gold 应恰 1 题，实得 {len(special)}")
        sp = special[0]
        d = detail_by_qid[sp["qid"]]
        g = gold[sp["qid"]]
        rows = [
            ["字段", "值"],
            ["qid", sp["qid"]],
            ["说明", "非盲人审专用：本题为「声明目标重解析=金标被一致性门禁拒绝」案，"
                     "按任务书单列人审，允许查看模型声明目标相关字段"],
            ["substrate_smiles", g["substrate_smiles"]],
            ["gold_products_smiles", "; ".join(g["products_smiles"])],
            ["analogy_target_ok", d.get("analogy_target_ok", "")],
            ["analogy_target_whole_gold", d.get("analogy_target_whole_gold", "")],
            ["analogy_target_component_gold", d.get("analogy_target_component_gold", "")],
            ["validation_reject_reasons", d.get("validation_reject_reasons", "")],
            ["evidence_refs", d.get("evidence_refs", "")],
        ]
        outputs["manual_review/special_case_nonblind.tsv"] = (
            "\n".join("\t".join(r) for r in rows) + "\n").encode()

    meta = {"script_version": SCRIPT_VERSION,
            "loss_audit_298_c0.tsv": audit_sha}
    if detail_sha:
        meta["miss_hit1_detail_c0.tsv"] = detail_sha
    if gold_sha:
        meta["questions.jsonl"] = gold_sha
    outputs["input_sha256.json"] = (
        json.dumps(meta, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n").encode()
    return outputs


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--audit-tsv", required=True)
    ap.add_argument("--detail-tsv")
    ap.add_argument("--loss-audit-dir", required=True)
    ap.add_argument("--gold")
    ap.add_argument("--pool-check", help="预留：qid→全池有无金标 jsonl；未提供不标 L5")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--check", action="store_true",
                    help="复算并逐字节比对，不重写产物")
    args = ap.parse_args()

    if args.pool_check:
        raise SystemExit("--pool-check 本轮未实现（L5 待远端全池核验）")

    audit_tsv, detail_tsv = Path(args.audit_tsv), (
        Path(args.detail_tsv) if args.detail_tsv else None)
    out_dir = Path(args.out_dir)
    audit_sha, detail_sha = _sha256(audit_tsv), (
        _sha256(detail_tsv) if detail_tsv else None)
    _verify_against_loss_audit_manifest(Path(args.loss_audit_dir), audit_sha,
                                        detail_sha)

    audit_rows = _read_tsv(audit_tsv)
    detail_rows = _read_tsv(detail_tsv) if detail_tsv else []
    gold, gold_sha = None, None
    if args.gold:
        gold_path = Path(args.gold)
        gold_sha = _sha256(gold_path)
        gold = {}
        for line in gold_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            qid = rec.get("qid")
            if not qid or qid in gold:
                raise SystemExit(f"金标行缺 qid 或重复：{qid}")
            gold[qid] = {"category": rec.get("category"),
                       "substrate_smiles": rec.get("substrate_smiles", ""),
                       "products_smiles": rec.get("products_smiles", [])}
        missing = {p["qid"] for p in audit_rows} - set(gold)
        if missing:
            raise SystemExit(f"金标缺 {len(missing)} 个 qid，如 {sorted(missing)[:3]}")

    outputs = build_outputs(audit_rows, detail_rows, gold, out_dir,
                            audit_sha, detail_sha, gold_sha)

    if args.check:
        bad = []
        for name, data in sorted(outputs.items()):
            path = out_dir / name
            if not path.exists() or path.read_bytes() != data:
                bad.append(name)
        if bad:
            print(f"CHECK FAIL: {bad}")
            return 2
        print(f"CHECK PASS: {len(outputs)} 个产物逐字节一致")
        return 0

    for name, data in sorted(outputs.items()):
        _write_bytes(out_dir / name, data)
    manifest = []
    for name in sorted(outputs):
        manifest.append(f"{_sha256(out_dir / name)}  {name}")
    _write_bytes(out_dir / "output_manifest.sha256",
                 ("\n".join(manifest) + "\n").encode())
    print(f"OK: 写出 {len(outputs)} 个产物 → {out_dir} "
          f"(checklist={len([p for p in outputs if 'checklist' in p])})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
