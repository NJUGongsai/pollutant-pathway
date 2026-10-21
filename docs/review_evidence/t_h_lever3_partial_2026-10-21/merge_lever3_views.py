#!/usr/bin/env python3
"""Merge the two lever-3 53-row views into one teacher-facing table.

Primary view  : lever3_partial_table.json (structural four-class view,
                matching the teacher's wording: bookkeeping / cofactor /
                structural-near / other).
Crosswalk view: partial53_gap_table.json (metadata role view).

Read-only. This script only re-labels existing machine outputs; it does
not read reference graphs, structures, task text, or gold content.  It
writes table_53.md and summary.txt.  No conversion expectation is ever
written.
"""
from __future__ import annotations

import collections
import hashlib
import json
from pathlib import Path

EV = Path(__file__).resolve().parent
STRUCT = EV / "lever3_partial_table.json"
META = EV / "partial53_gap_table.json"

CLASS_ZH = {
    "bookkeeping_exempt": "簿记类（豁免族命中）",
    "cofactor": "辅因子类",
    "structural_near": "结构差一点",
    "other": "其他",
}
DEST_ZH = {
    "fixable": "可修",
    "pending_cofactor": "待裁定",
    "abandon": "放弃",
}
SUBTYPE_ZH = {
    "undeclared_coproduct": "其他·未声明副产物",
    "extra_principal_product": "其他·多声明主产物",
    "missing_other": "其他·缺主产物（无近结构）",
}
T1_SHORT = {
    "链未闭合（no_chain），T-1 无法判定": "no_chain",
    "主缺口为缺主产物；T-1 不能补缺失产物（覆盖层先挡）": "缺主产物阻断",
    "已有链但未全豁免（resolved，occurrence 仍 not_exempt）":
        "resolved 未全豁免",
    "混合状态（部分事件有链/已判定，部分无链）": "混合",
}


def sha12(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:12]


def main() -> None:
    meta = json.loads(META.read_text())
    struct = json.loads(STRUCT.read_text())
    meta_rows = {r["qid"]: r for r in meta["rows"]}
    struct_rows = {r["qid"]: r for r in struct["rows"]}
    assert len(meta_rows) == 53, len(meta_rows)
    assert len(struct_rows) == 53, len(struct_rows)
    assert set(meta_rows) == set(struct_rows), "qid sets differ"

    rows = sorted(meta_rows.values(), key=lambda r: r["row_id"])
    class_counts = collections.Counter()
    dest_counts = collections.Counter()
    subtype_counts = collections.Counter()
    lines = [
        "# T-H lever 3：53 题 partial 覆盖缺口分类表",
        "",
        "> 题域：298 = RHEA 通用酶学 / 已见题（post-hoc）。只读诊断；零模型调用、"
        "零新批次、零金标/题面内容出文档。",
        "> 主类按老师任务书 §三 的四类口径：**簿记类（豁免族命中）/ 辅因子类 / "
        "结构差一点 / 其他**。",
        "> 「其他」再分：未声明副产物（可修）、多声明主产物（放弃）、"
        "缺主产物且无近结构（放弃）。",
        "> reference graph 只由冻结评测器的匹配函数消费以定位缺口；本表不输出任何"
        "结构正文、SMILES 或金标内容。",
        "> 「可修」只表示下一批存在修复面，不是转化承诺；"
        "**任何转化题数/比例/收益区间一律不写**。",
        "",
        f"> 源：`lever3_partial_table.json` SHA256 `{sha12(STRUCT)}`；"
        f"`partial53_gap_table.json` SHA256 `{sha12(META)}`。",
        "",
        "| # | qid 前缀 | 主类（老师四类） | 去向 | 细分 | 覆盖形态 | 池 / remap | "
        "组分计数（豁免/辅因子/簿记/其他/缺/近） | T-1 | 备注 |",
        "|---:|---|---|---|---|---|---:|---|---|---|",
    ]

    for i, m in enumerate(rows, 1):
        s = struct_rows[m["qid"]]
        klass = s["component_class"]
        dest = s["destination"]
        assert class_counts[klass] >= 0
        class_counts[klass] += 1
        dest_counts[dest] += 1
        assert DEST_ZH[dest] == {
            "bookkeeping_exempt": "可修",
            "cofactor": "待裁定",
            "structural_near": "可修",
            "other": (
                "可修" if s.get("other_subtype") == "undeclared_coproduct"
                else "放弃"),
        }[klass], (m["qid"], klass, dest, s.get("other_subtype"))
        subtype = s.get("other_subtype") or ""
        if klass == "other":
            assert subtype in SUBTYPE_ZH, (m["qid"], subtype)
            subtype_counts[subtype] += 1
            subtype_label = SUBTYPE_ZH[subtype]
        else:
            subtype_label = m["gap_category_zh"]
        forms = "+".join(m["coverage_forms"]) or "—"
        comp = (
            f"{s['n_exempt_family_components']}/"
            f"{s['n_cofactor_components']}/"
            f"{s['n_bookkeeping_role_components']}/"
            f"{s['n_other_extra_components']}/"
            f"{s['n_missing_nodes']}/"
            f"{s['n_missing_near_components']}")
        pool_remap = f"{m['pool_size']} / {s['remap']}"
        t1 = T1_SHORT.get(m["t1_relation"], m["t1_relation"])
        note = s["notes"] or "—"
        if klass == "structural_near" and s["n_cofactor_components"]:
            note += "；另有辅因子组分，化学边界仍需裁定"
        lines.append(
            f"| {i} | `{m['qid_prefix']}` | {CLASS_ZH[klass]} | "
            f"**{DEST_ZH[dest]}** | {subtype_label} | {forms} | "
            f"{pool_remap} | {comp} | {t1} | {note} |")

    n = len(rows)
    lines += [
        "",
        f"**闭合：{n}/53。** 主类互斥，每题一行；细分保留元数据口径以便复核。",
        "",
        "| 主类（老师四类） | 题数 | 去向 | 标签 |",
        "|---|---:|---|---|",
        f"| 簿记类（豁免族命中） | {class_counts['bookkeeping_exempt']} | "
        "可修（补链/声明） | 已证（分类计数） |",
        f"| 辅因子类 | {class_counts['cofactor']} | 待裁定（化学评审） | "
        "已证（分类计数） |",
        f"| 结构差一点 | {class_counts['structural_near']} | 可修（身份归一/声明） | "
        "已证（分类计数） |",
        f"| 其他 | {class_counts['other']} | 可修 "
        f"{subtype_counts['undeclared_coproduct']} / 放弃 "
        f"{subtype_counts['extra_principal_product'] + subtype_counts['missing_other']} | "
        "已证（分类计数） |",
        f"| **合计** | **{n}** | — | 已证 |",
        "",
        "| 去向 | 题数 | 构成 | 标签 |",
        "|---|---:|---|---|",
        f"| **可修** | {dest_counts['fixable']} | 簿记类 "
        f"{class_counts['bookkeeping_exempt']} + 结构差一点 "
        f"{class_counts['structural_near']} + 其他·未声明副产物 "
        f"{subtype_counts['undeclared_coproduct']} | 已证（分类计数） |",
        f"| **待裁定** | {dest_counts['pending_cofactor']} | 辅因子类 "
        f"{class_counts['cofactor']} | 已证（分类计数） |",
        f"| **放弃** | {dest_counts['abandon']} | 其他·多声明主产物 "
        f"{subtype_counts['extra_principal_product']} + 其他·缺主产物（无近结构） "
        f"{subtype_counts['missing_other']} | 已证（分类计数） |",
        f"| **合计** | **{n}** | — | 已证 |",
        "",
        "**读法：**",
        "",
        "- 「结构差一点」= 缺失的参考产物节点在候选 payload 里存在 strict 匹配的"
        "代理状态，且事件侧参与物与其同分子式或同 Murcko 骨架（≥6 重原子）；"
        "属于身份归一候选，不是已证可兑现。",
        "- 「其他·未声明副产物」= 无豁免族的 coproduct 多余项；修复面是共产物声明/"
        "忽略档，**不得删真实副产物**，化学边界仍需评审。",
        "- 元数据口径对照：未声明副产物 21、簿记类未获豁免 16、缺主产物 8、"
        "辅因子 5、多声明主产物 3。结构核对把其中 7 题「缺主产物」判为同式/同骨架"
        "近似，归入「结构差一点」；两口径差异仅此 7 题。",
        "- 结构差一点中有 2 题同时含辅因子组分，修复动作仍需化学裁定。",
        "- **不写转化预期值**：可修 ≠ 会 strict；待裁定 ≠ 会转化；放弃 ≠ 永久无救。",
    ]
    (EV / "table_53.md").write_text("\n".join(lines) + "\n")

    summary = {
        "closed": n,
        "primary_classes": dict(class_counts),
        "other_subtypes": dict(subtype_counts),
        "destinations": dict(dest_counts),
        "metadata_categories": meta["summary"]["category_counts"],
        "coverage_forms": meta["summary"]["coverage_form_counts"],
        "t1_declaration_qids": meta["summary"]["t1_declaration_qid_counts"],
        "t1_all_exempt_qids": meta["summary"]["t1_all_exempt_qids"],
        "pool0_qids": meta["summary"]["pool_size_zero_qids"],
        "promoted_excluded": meta["summary"][
            "promoted_v1_partial_to_v2_strict"]["n"],
        "cofactor_overlap_in_structural_near": sum(
            1 for s in struct_rows.values()
            if s["component_class"] == "structural_near"
            and s["n_cofactor_components"]),
        "conversion_expectation": "not_written",
    }
    comp = struct["aggregates"]["component_totals"]
    txt = [
        "T-H teacher lever 3 — 53 partial coverage-gap classification "
        "(teacher four-class view)",
        "Domain: 298 (RHEA general enzymology, seen questions, post-hoc)",
        "Batch: t_h_s5b_298_20261020r2 (sealed, read-only)",
        "Date: 2026-10-21",
        "Set: lever3_partial_classify.py (structural view) + "
        "build_lever3_partial.py (metadata crosswalk) + "
        "merge_lever3_views.py (teacher-facing table)",
        "",
        f"Closure: {n}/53 rows; class/destination unknown = 0.",
        "",
        "Primary class (teacher wording):",
        f"  bookkeeping_exempt  {class_counts['bookkeeping_exempt']:>2}  "
        "(identity in H2O/H+/Pi/PPi family; the full v2 predicate gate "
        "did not pass inside the 53)",
        f"  cofactor            {class_counts['cofactor']:>2}  "
        "(non-exempt cosubstrate or >=30-heavy N+P/S species; chemistry "
        "to sister)",
        f"  structural_near     {class_counts['structural_near']:>2}  "
        "(missing reference principal product has same formula or same "
        ">=6-heavy scaffold as an event-side participant; "
        "identity-normalization candidate, not a proven conversion)",
        f"  other               {class_counts['other']:>2}  "
        f"({subtype_counts['undeclared_coproduct']} undeclared coproduct, "
        f"{subtype_counts['extra_principal_product']} extra principal "
        f"product, {subtype_counts['missing_other']} missing-other)",
        "  unknown              0",
        "",
        "Destination:",
        f"  fixable (可修)          {dest_counts['fixable']:>2} = "
        f"{class_counts['bookkeeping_exempt']} bookkeeping + "
        f"{class_counts['structural_near']} structural_near + "
        f"{subtype_counts['undeclared_coproduct']} undeclared coproduct",
        f"  pending_cofactor (待裁定) {dest_counts['pending_cofactor']:>2} = "
        f"{class_counts['cofactor']} cofactor",
        f"  abandon (放弃)           {dest_counts['abandon']:>2} = "
        f"{subtype_counts['extra_principal_product']} extra principal "
        f"product + {subtype_counts['missing_other']} missing-other",
        "  unknown                 0",
        "",
        "Metadata-role crosswalk (does not decide destinations):",
        f"  {meta['summary']['category_counts']}",
        "  The two views differ on exactly 7 qids; all other 46 agree.",
        "",
        f"Coverage forms: {meta['summary']['coverage_form_counts']}",
        f"Pool=0 partial qids: {meta['summary']['pool_size_zero_qids']}/53 "
        "(coverage events still come from novel proposals; partial is not "
        "the same as an empty pool).",
        "",
        "T-1 relation:",
        f"  all_exempt=true {meta['summary']['t1_all_exempt_qids']}/53; "
        f"declaration {meta['summary']['t1_declaration_qid_counts']}; "
        f"occurrence tiers {meta['summary']['t1_occurrence_tier_totals']}.",
        "  The five redeemed qids (metrics v1 partial -> v2 strict rank 1) "
        "are outside the 53. 16 rows remain in the bookkeeping family but "
        "did not pass the full v2 predicate gate.",
        "",
        "Component totals:",
        f"  exempt-family extras {comp['exempt_family_components']}; "
        f"cofactor/cosubstrate extras {comp['cofactor_components']}; "
        f"same-identity wrong-side extras "
        f"{comp['bookkeeping_role_components']}; other extras "
        f"{comp['other_extra_components']}; missing reference nodes "
        f"{comp['missing_nodes']} (near {comp['missing_near_components']} "
        f"/ other {comp['missing_other_components']} / unknown "
        f"{comp['missing_unknown']}).",
        "",
        "Conversion expectation: not written. 53 is a pool count; "
        "full-switch upper bound +53 is an upper bound only, not a "
        "promised conversion. \"Fixable\" means a next-batch fix surface "
        "exists, not that strict conversion is achieved. Cofactor "
        "chemistry is not adjudicated here.",
        "",
        "Evidence: table_53.md (teacher four-class rows), "
        "table_53_metadata.md (role crosswalk), lever3_partial_table.json, "
        "partial53_gap_table.json, partial53_meta.json, provenance.json, "
        "SHA256SUMS.",
    ]
    (EV / "summary.txt").write_text("\n".join(txt) + "\n")
    print("\n".join(txt))
    print("wrote", EV / "table_53.md")


if __name__ == "__main__":
    main()
