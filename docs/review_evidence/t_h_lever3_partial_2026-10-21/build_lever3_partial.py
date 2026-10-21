#!/usr/bin/env python3
"""Teacher lever 3: per-question participant-coverage gap classification for the 53 partial qids.

Read-only. No model calls, no batch runs, no gold/reference-graph content.
Inputs carry only qid/status/pool/participant-role metadata; no SMILES, no
structure body, no question text.

Sources:
  * reports/ppv1_s5b/t_h_2026-10-20/r2/metrics.json      (v2 headline)
  * reports/ppv1_s5b/t_h_2026-10-20/r2/metrics.json.v1   (only to exclude the 5
    already-promoted v1 partial -> v2 strict qids from the 53 partial set)
  * partial53_meta.json  (compact metadata extracted from the read-only
    evaluator re-run; see provenance inside the file)

Usage:
    python3 build_lever3_partial.py
"""
from __future__ import annotations

import collections
import hashlib
import json
from pathlib import Path

EV = Path(__file__).resolve().parent
REPO = EV.parents[2]
METRICS = REPO / "reports/ppv1_s5b/t_h_2026-10-20/r2/metrics.json"
METRICS_V1 = REPO / "reports/ppv1_s5b/t_h_2026-10-20/r2/metrics.json.v1"
META = EV / "partial53_meta.json"

CATEGORY_ORDER = [
    "missing_principal_product",
    "extra_principal_product",
    "cofactor_extra",
    "undeclared_coproduct",
    "bookkeeping_unexempt",
    "other",
]

CATEGORY_ZH = {
    "missing_principal_product": "缺主产物",
    "extra_principal_product": "多声明主产物",
    "cofactor_extra": "辅因子类多余反应物",
    "undeclared_coproduct": "未声明副产物",
    "bookkeeping_unexempt": "簿记类未获豁免",
    "other": "其他",
}

DESTINATION = {
    "missing_principal_product": "放弃",
    "extra_principal_product": "放弃",
    "cofactor_extra": "待裁定",
    "undeclared_coproduct": "可修",
    "bookkeeping_unexempt": "可修",
    "other": "待裁定",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_per_qid(path: Path) -> dict:
    data = json.loads(path.read_text())
    return {row["qid"]: row for row in data["per_qid"]}


def as_role(value) -> str:
    if isinstance(value, dict):
        return str(value.get("role") or "")
    return str(value or "")


def classify(events: list[dict]) -> tuple[str, dict]:
    """Return the primary gap category with a mutually-exclusive priority.

    Priority is deliberate: a missing principal product is the most structural
    gap; an extra principal product is next; a blank (non-bookkeeping)
    cosubstrate is a chemistry/cofactor question; a blank coproduct is a
    declaration/generation gap; bookkeeping-family extras are last.
    """
    missing_pp = any(
        as_role(m) == "principal_product"
        for ev in events
        for m in ev.get("missing_roles", [])
    )
    extra_pp = any(
        o.get("role") == "principal_product"
        for ev in events
        for o in ev.get("extras", [])
    )
    extra_cos_blank = any(
        o.get("role") == "cosubstrate" and not o.get("exempt_family")
        for ev in events
        for o in ev.get("extras", [])
    )
    extra_cop_blank = any(
        o.get("role") == "coproduct" and not o.get("exempt_family")
        for ev in events
        for o in ev.get("extras", [])
    )
    extra_bookkeeping = any(
        bool(o.get("exempt_family"))
        for ev in events
        for o in ev.get("extras", [])
    )

    if missing_pp:
        return "missing_principal_product", {}
    if extra_pp:
        return "extra_principal_product", {}
    if extra_cos_blank:
        return "cofactor_extra", {}
    if extra_cop_blank:
        return "undeclared_coproduct", {}
    if extra_bookkeeping:
        return "bookkeeping_unexempt", {}
    return "other", {}


def t1_status(events: list[dict]) -> dict:
    """Summarize T-1 review status at question level (not event level)."""
    decls = []
    eligs = []
    all_exempts = []
    tiers = collections.Counter()
    families = collections.Counter()
    for ev in events:
        review = ev.get("t1_review") or {}
        decls.append(review.get("declaration_status"))
        eligs.append(review.get("eligible"))
        all_exempts.append(review.get("all_exempt"))
        for occ in review.get("occurrences", []):
            tiers[str(occ.get("tier"))] += 1
            fam = occ.get("exempt_family")
            if fam:
                families[str(fam)] += 1

    uniq_decls = sorted({str(d) for d in decls})
    if uniq_decls == ["None"]:
        decl_label = "none"
    elif len(uniq_decls) == 1:
        decl_label = uniq_decls[0]
    else:
        decl_label = "mixed(" + ",".join(uniq_decls) + ")"

    return {
        "declaration_status": decl_label,
        "eligible_any": any(bool(x) for x in eligs),
        "eligible_all": all(bool(x) for x in eligs),
        "all_exempt_any": any(bool(x) for x in all_exempts),
        "tier_counts": dict(sorted(tiers.items())),
        "exempt_families": dict(sorted(families.items())),
    }


def main() -> None:
    metrics = load_per_qid(METRICS)
    metrics_v1 = load_per_qid(METRICS_V1)
    meta = json.loads(META.read_text())
    per_qid = meta["per_qid"]

    # Exclusion check: the 5 v1 partial -> v2 strict qids must not be in the 53.
    promoted = [
        qid
        for qid, row in metrics.items()
        if metrics_v1[qid]["main"]["match_status"]
        == "matched_participant_coverage_partial"
        and row["main"]["match_status"] == "matched_strict"
    ]
    partial_qids = [row["qid"] for row in per_qid]
    overlap_promoted = sorted(set(promoted) & set(partial_qids))

    assert len(per_qid) == 53, len(per_qid)
    assert len(set(partial_qids)) == 53
    assert not overlap_promoted, overlap_promoted
    for row in per_qid:
        assert row["edge_status"] == "matched_participant_coverage_partial", row["qid"]
        assert metrics[row["qid"]]["main"]["match_status"] == (
            "matched_participant_coverage_partial"
        ), row["qid"]

    rows = []
    for i, row in enumerate(sorted(per_qid, key=lambda x: x["qid"]), 1):
        qid = row["qid"]
        events = row.get("coverage_mismatch_events") or []
        category, _ = classify(events)
        status = t1_status(events)

        forms = sorted({ev.get("participant_coverage") for ev in events})
        extras = []
        missing = []
        for ev in events:
            for o in ev.get("extras", []):
                extras.append(
                    (
                        o.get("side"),
                        o.get("role"),
                        o.get("exempt_family") or "",
                    )
                )
            for m in ev.get("missing_roles", []):
                missing.append(as_role(m))
        extras_counter = collections.Counter(extras)
        missing_counter = collections.Counter(missing)

        if category == "missing_principal_product":
            relation = "主缺口为缺主产物；T-1 不能补缺失产物（覆盖层先挡）"
        elif not status["eligible_any"]:
            relation = "T-1 不适用/未生成（覆盖层先挡）"
        elif status["declaration_status"] == "no_chain":
            relation = "链未闭合（no_chain），T-1 无法判定"
        elif status["declaration_status"].startswith("resolved"):
            relation = "已有链但未全豁免（resolved，occurrence 仍 not_exempt）"
        elif status["declaration_status"].startswith("mixed"):
            relation = "混合状态（部分事件有链/已判定，部分无链）"
        else:
            relation = "其他/未判定"

        rows.append(
            {
                "row_id": i,
                "qid": qid,
                "qid_prefix": qid[:18],
                "v2_status": row["edge_status"],
                "pool_size": row["pool_size"],
                "n_candidate_events": row["n_candidate_events"],
                "n_matched_events": row["n_matched_events"],
                "coverage_forms": forms,
                "n_coverage_events": len(events),
                "gap_category": category,
                "gap_category_zh": CATEGORY_ZH[category],
                "destination": DESTINATION[category],
                "extras": [
                    {"side": s, "role": r, "exempt_family": f, "n": n}
                    for (s, r, f), n in extras_counter.most_common()
                ],
                "missing_roles": [
                    {"role": r, "n": n} for r, n in missing_counter.most_common()
                ],
                "t1": status,
                "t1_relation": relation,
                "evidence_fields": [
                    "M.main.match_status",
                    "C.coverage_mismatch_events[].participant_coverage",
                    "C.coverage_mismatch_events[].extras[]",
                    "C.coverage_mismatch_events[].missing_roles[]",
                    "C.coverage_mismatch_events[].t1_review.{eligible,all_exempt,declaration_status}",
                    "C.coverage_mismatch_events[].t1_review.occurrences[].tier",
                ],
            }
        )

    # ---- summary ---------------------------------------------------------
    def count(key: str) -> dict:
        return dict(collections.Counter(r[key] for r in rows))

    by_cat = count("gap_category")
    by_dest = count("destination")
    forms = collections.Counter(tuple(r["coverage_forms"]) for r in rows)
    t1_decl = collections.Counter(
        ("none" if r["t1"]["declaration_status"] == "none" else
         "resolved" if r["t1"]["declaration_status"].startswith("resolved") else
         "no_chain" if r["t1"]["declaration_status"] == "no_chain" else
         "mixed")
        for r in rows
    )

    summary = {
        "closed": len(rows),
        "total_targets": 53,
        "category_counts": {k: by_cat.get(k, 0) for k in CATEGORY_ORDER},
        "destination_counts": by_dest,
        "coverage_form_counts": {"+".join(k): v for k, v in forms.items()},
        "t1_declaration_qid_counts": dict(t1_decl),
        "t1_any_status_qid_counts": {
            "any_no_chain": sum(
                1 for r in rows if "no_chain" in r["t1"]["declaration_status"]
            ),
            "any_resolved": sum(
                1 for r in rows if "resolved" in r["t1"]["declaration_status"]
            ),
            "any_none": sum(
                1 for r in rows if "None" in r["t1"]["declaration_status"]
                or r["t1"]["declaration_status"] == "none"
            ),
        },
        "t1_eligible_qid_counts": {
            "all_true": sum(1 for r in rows if r["t1"]["eligible_all"]),
            "any_true": sum(1 for r in rows if r["t1"]["eligible_any"]),
            "any_false": sum(1 for r in rows if not r["t1"]["eligible_all"]),
        },
        "t1_all_exempt_qids": sum(1 for r in rows if r["t1"]["all_exempt_any"]),
        "pool_size_zero_qids": sum(1 for r in rows if r["pool_size"] == 0),
        "promoted_v1_partial_to_v2_strict": {
            "n": len(promoted),
            "qid_prefixes": [q[:18] for q in sorted(promoted)],
            "overlap_with_partial53": overlap_promoted,
        },
        "unknown": [
            "转化题数 unknown：没有候选级/事件级金标匹配，也没有同题 A/B；本表只分类缺口面。",
            "可修 ≠ 可兑现：可修只表示存在下一批修复面，不承诺 strict 转化。",
            "缺主产物类的真实可修性 unknown：当前事件没有该主产物，无法从覆盖元数据判断是生成失败还是投影截断。",
            "辅因子类的化学必要性 unknown：需化学评审，本文不写判据结论。",
        ],
    }

    # Occurrence tier totals across all 53 qids (event-level, not qid-level).
    tier_totals = collections.Counter()
    for r in rows:
        for tier, n in r["t1"]["tier_counts"].items():
            tier_totals[tier] += n
    summary["t1_occurrence_tier_totals"] = dict(sorted(tier_totals.items()))

    out = {
        "provenance": {
            "batch_tag": "t_h_s5b_298_20261020r2",
            "domain_tag": "298=RHEA 通用酶学/已见题（post-hoc）；本表不外推",
            "nature": "只读诊断；零模型调用、零新批次、零金标/reference_graphs 内容、零结构正文输出",
            "source_sha256": {
                "reports/ppv1_s5b/t_h_2026-10-20/r2/metrics.json": sha256(METRICS),
                "reports/ppv1_s5b/t_h_2026-10-20/r2/metrics.json.v1": sha256(METRICS_V1),
                "partial53_meta.json": sha256(META),
            },
            "classification_rule": {
                "priority": CATEGORY_ORDER,
                "missing_principal_product": "任一覆盖事件 missing_roles 含 principal_product",
                "extra_principal_product": "任一事件 extras 含 principal_product",
                "cofactor_extra": "任一事件 extras 含无 exempt_family 的 cosubstrate",
                "undeclared_coproduct": "任一事件 extras 含无 exempt_family 的 coproduct",
                "bookkeeping_unexempt": "其余事件 extras 仅含带 exempt_family 的簿记类（H2O/H+/PPi 等），但 tier 仍 not_exempt",
                "destination": {
                    "可修": "存在下一批声明/补链修复面；不承诺转化题数",
                    "待裁定": "辅因子类，化学必要性需送师姐评审",
                    "放弃": "当前证据下不进入下一批修复面；不是永久否定",
                },
            },
        },
        "summary": summary,
        "rows": rows,
    }

    (EV / "partial53_gap_table.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1) + "\n"
    )

    # ---- markdown table --------------------------------------------------
    def extras_text(r):
        if not r["extras"]:
            return "—"
        parts = []
        for e in r["extras"]:
            fam = f" [{e['exempt_family']}]" if e["exempt_family"] else ""
            parts.append(f"{e['role']}×{e['n']}{fam}")
        return "；".join(parts)

    def missing_text(r):
        if not r["missing_roles"]:
            return "—"
        return "；".join(f"{m['role']}×{m['n']}" for m in r["missing_roles"])

    def t1_text(r):
        t = r["t1"]
        bits = [f"decl={t['declaration_status']}", f"elig={t['eligible_all']}"]
        if t["tier_counts"]:
            bits.append(
                "tier="
                + ",".join(f"{k}×{v}" for k, v in t["tier_counts"].items())
            )
        return "；".join(bits)

    lines = [
        "# T-H lever 3：53 题 partial 覆盖缺口分类表",
        "",
        "> 题域：298 = RHEA 通用酶学 / 已见题（post-hoc）。只读诊断；零模型调用、零新批次、",
        "> 零金标/reference_graphs 内容、零结构正文。分类计数为已证观察，不是转化预期。",
        "",
        "| # | qid 前缀 | 覆盖形态 | 事件数 | 池 | 缺口主类 | 多余组分（元数据） | 缺失组分 | T-1 状态 | 与 T-1 豁免档关系 | 去向 | 证据字段 |",
        "|---:|---|---|---:|---:|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(
            f"| {r['row_id']} | `{r['qid_prefix']}` | {'+'.join(r['coverage_forms'])} | "
            f"{r['n_coverage_events']} | {r['pool_size']} | **{r['gap_category_zh']}** | "
            f"{extras_text(r)} | {missing_text(r)} | {t1_text(r)} | {r['t1_relation']} | "
            f"**{r['destination']}** | `{'; '.join(r['evidence_fields'][:4])}` |"
        )
    lines += [
        "",
        "**读法：**",
        "",
        "- 一行一题；覆盖形态 `superset` = 候选参与物多于参考、`partial_subset` = 少于参考。",
        "- 「缺口主类」按互斥优先级取：缺主产物 > 多声明主产物 > 辅因子类多余反应物 >",
        "  未声明副产物 > 簿记类未获豁免；同一题有多个事件时取最高优先级。",
        "- 「T-1 状态」来自 `t1_review`；`none` = 未生成/不适用，`no_chain` = 链未闭合，",
        "  `resolved` = 有链但 occurrence 仍 `not_exempt_maintains_partial`。",
        "- 「去向」只表示下一批是否有修复面：可修 ≠ 可兑现；53 题转化题数一律 unknown。",
        "- 已兑现的 5 题（v1 partial → v2 strict）不在本表；用 `metrics.json.v1` 对 `metrics.json`",
        "  逐题比对，交集为 0。",
    ]
    (EV / "table_53_metadata.md").write_text("\n".join(lines) + "\n")

    txt = [
        "T-H lever3 partial-gap classification summary (metadata only)",
        f"closed: {summary['closed']}/{summary['total_targets']}",
        f"categories: {summary['category_counts']}",
        f"destinations: {summary['destination_counts']}",
        f"coverage_forms: {summary['coverage_form_counts']}",
        f"t1_declaration_qids: {summary['t1_declaration_qid_counts']}",
        f"t1_any_status_qids: {summary['t1_any_status_qid_counts']}",
        f"t1_eligible_qids: {summary['t1_eligible_qid_counts']}",
        f"t1_all_exempt_qids: {summary['t1_all_exempt_qids']}",
        f"t1_occurrence_tiers: {summary['t1_occurrence_tier_totals']}",
        f"pool0_qids: {summary['pool_size_zero_qids']}",
        f"promoted_excluded: {summary['promoted_v1_partial_to_v2_strict']['n']}",
    ]
    (EV / "summary_metadata.txt").write_text("\n".join(txt) + "\n")
    print("\n".join(txt))
    print("wrote", EV / "partial53_gap_table.json")
    print("wrote", EV / "table_53_metadata.md")


if __name__ == "__main__":
    main()
