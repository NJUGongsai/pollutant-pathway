#!/usr/bin/env python
"""金标体检 v2 规则全量打标(dev 56 + 298 全卷;零 LLM 零 API;金标只在本进程读)。

v2 改版规格:docs/MIMO_REVIEWS_ADOPTION_REGISTER.md §4.2 + docs/
mimo_gold_rules_review_response.md(R1'/R2'/R3'/R4');规则实现
src/pathway_v43/gold_health.py(v2 默认路径,v1 原样保留可复算)。

与封存 v1 轮的关系(红线):

- **v1 产物零覆写**:本脚本只写 v2/ 子目录,不触碰上级封存件
  (gold_health_labels_*.tsv / gold_health_summary.json /
  quarantine_proposal_dev.tsv / QUARANTINE_EFFECTIVE.md);
- **输出只有 qid/旗标/计数,无任何 SMILES**;
- 本轮 v2 打标是**提案**——待新冻结链(mimo 评审→人审→双人确认)
  采纳,**不追溯作废** QUARANTINE_EFFECTIVE(2026-09-30,dev 分母 56→51);
- 298 只诊断打标,不动分数不动金标。

输入:

- dev:题面 = dev_questions.jsonl 的 root_smiles;金标 = dev_gold.jsonl
  (gitignored,仅本进程打开);
- 298:题面/金标 = Chenyu 只读副本
  /usrdata/EnzymeCAGE_data/workspaces/ec298_gold_readonly/questions.jsonl
  (SHA 9f5955d4…,与 dual_track_rescore/work/questions_298.jsonl 逐字节
  一致;拉取:/tmp/cy_ssh.sh "cat <远端路径>" | grep -v "^spawn ssh\\|password:"
  > /tmp/q298_ec298_gold_readonly.jsonl,再 tr -d '\\r' 去 expect 管道 CR)。

对比:v1 vs v2 逐题规则级对比(v1 读封存 TSV,只读),含已生效 5 题
的旗标翻转检查(翻转=新证据,单列待新链,不静默改判)。
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "src"))

from pathway_v43.gold_health import (  # noqa: E402
    FLAG_R1,
    FLAG_R3,
    FLAG_R3_UNREACHABLE,
    FLAG_R4_FULL,
    FLAG_R4_MIXED,
    RULES_VERSION,
    gold_health_labels,
)

REPO = Path(__file__).resolve().parents[4]
DEV_QUESTIONS = REPO / "reports/phase_s1_hit60/dev_questions.jsonl"
DEV_GOLD = REPO / "reports/phase_s1_hit60/dev_gold/dev_gold.jsonl"
Q298_REMOTE_COPY = Path("/tmp/q298_ec298_gold_readonly.jsonl")
Q298_LOCAL_SEALED = (REPO / "reports/phase_s15_hit60/dual_track_rescore"
                     / "work/questions_298.jsonl")
# v1 封存产物(只读,用于逐题对比;绝不写)
V1_DEV_TSV = (REPO / "reports/phase_s15_hit60/gold_health_check"
              / "gold_health_labels_dev.tsv")
V1_298_TSV = (REPO / "reports/phase_s15_hit60/gold_health_check"
              / "gold_health_labels_298.tsv")
OUT = REPO / "reports/phase_s15_hit60/gold_health_check/v2"

# 已生效 quarantine 5 题(QUARANTINE_EFFECTIVE.md,2026-09-30;只读引用)
QUARANTINED_QIDS = [
    "b1_BIOPATH150_067__S03__BSY-r02126",
    "b1_BIOPATH150_114__S01__BSY-r01911",
    "b1_BIOPATH150_028__S04__BSY-r03812",
    "b1_BIOPATH150_149__S01__BSY-r01831",
    "b1_BIOPATH150_149__S06__BSY-r03410",
]

PROPOSAL_STATUS = (
    "提案:待新冻结链(mimo 评审→人审→双人确认)采纳;"
    "不追溯作废 QUARANTINE_EFFECTIVE(2026-09-30 已生效 5 题)"
)

FLAG_DISPOSITIONS = {
    FLAG_R1: "剔出分母入 quarantine(题面不可答:缺共底物元素)",
    FLAG_R3_UNREACHABLE: "剔出分母入 quarantine(题面不可答:缺碳供体共底物)",
    FLAG_R3: "金标数据错(碳增对不上可指认碎片):人审定夺(修金标或剔题)",
    FLAG_R4_FULL: "退化题(金标=题面):单列层+双轨报告处置",
    FLAG_R4_MIXED: "退化题(金标混入题面身份):单列层+双轨报告处置",
}

COLUMNS = [
    "qid", "rule_version", "flags", "manual_review", "r1", "r3", "r4",
    "r1_hit_elements", "new_elements", "delta_elements", "delta_c",
    "delta_o", "delta_h", "delta_dou", "r2_pattern", "r2_retained",
    "r3_gap", "r3_attribution", "salt_form", "salt_form_surface",
    "salt_form_gold", "salt_ions", "parse_fail",
    "n_parse_fail_surface_parts", "n_parse_fail_product_parts",
    "substrate_c", "gold_c", "n_products", "ribose_observed",
    "r4_full", "r4_mixed", "r4_axis", "r4_mixed_kind",
    "in_quarantine_v1",
]

PROPOSAL_COLUMNS = [
    "qid", "flags", "rule_hits", "manual_review", "delta_c", "delta_o",
    "delta_h", "r3_attribution", "r4_axis", "proposed_disposition", "status",
]

MANUAL_REVIEW_COLUMNS = ["qid", "manual_review", "flags", "delta_c",
                         "delta_dou", "status"]

FLIP_COLUMNS = ["qid", "v1_flags", "v2_flags", "v1_rule_level", "v2_rule_level",
                "flip_kind", "status"]

RULE_HITS_MAP = {
    FLAG_R1: "R1",
    FLAG_R3: "R3",
    FLAG_R3_UNREACHABLE: "R3",
    FLAG_R4_FULL: "R4",
    FLAG_R4_MIXED: "R4",
}


def _iter_jsonl(path: Path):
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            yield json.loads(line)


def _fmt(v) -> str:
    if v is None:
        return ""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, float):
        return f"{v:g}"
    if isinstance(v, dict):
        return ";".join(f"{k}:{val}" for k, val in sorted(v.items())) if v else ""
    if isinstance(v, (list, set)):
        return ";".join(sorted(str(x) for x in v)) if v else ""
    return str(v).replace("\t", " ").replace("\n", " ")


def _write_tsv(path: Path, columns: list[str], rows: list[dict]) -> None:
    lines = ["\t".join(columns)]
    for r in rows:
        lines.append("\t".join(_fmt(r.get(c)) for c in columns))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _read_v1_tsv(path: Path) -> dict[str, dict]:
    """读封存 v1 打标 TSV(只读):qid → {flags, r1, r3, r4}。"""
    rows: dict[str, dict] = {}
    lines = path.read_text(encoding="utf-8").splitlines()
    header = lines[0].split("\t")
    for line in lines[1:]:
        if not line.strip():
            continue
        rec = dict(zip(header, line.split("\t")))
        rows[rec["qid"]] = {
            "flags": [f for f in rec["flags"].split(";") if f],
            "r1": rec["r1"] == "true",
            "r3": rec["r3"] == "true",
            "r4": rec["r4"] == "true",
        }
    return rows


def _v1_rule_level(v1: dict) -> list[str]:
    rules = []
    if v1["r1"]:
        rules.append("R1")
    if v1["r3"]:
        rules.append("R3")
    if v1["r4"]:
        rules.append("R4")
    return rules


def _v2_rule_level(row: dict) -> list[str]:
    rules = []
    if row["r1"]:
        rules.append("R1")
    if row["r3"]:
        rules.append("R3")
    if row["r4"]:
        rules.append("R4")
    return rules


#: v2 拆旗对 v1 单旗的设计内改名(degenerate → full/mixed;登记 §4.2
#: 预期"R4 拆旗只改旗名不改命中"——改名不是翻转,不是新证据)。
R4_RENAME = {FLAG_R4_FULL: "degenerate", FLAG_R4_MIXED: "degenerate"}


def _effective_v2_flags(flags: list[str]) -> set[str]:
    """v2 旗标按设计内改名折叠回 v1 命名空间后比较。"""
    return {R4_RENAME.get(f, f) for f in flags}


def _flip_kind(v1: dict, row: dict) -> str:
    """翻转分档:none=规则级与旗标(折叠改名后)全同;attribution_change=
    规则级同但旗标语义变(如 conserv_violation→unreachable_cosubstrate,
    处置方向改变);rule_change=规则级命中面变化。后两档=新证据待新链。"""
    same_rule = set(_v1_rule_level(v1)) == set(_v2_rule_level(row))
    same_flags = set(v1["flags"]) == _effective_v2_flags(row["flags"])
    if same_rule and same_flags:
        return "none"
    if same_rule:
        return "attribution_change"
    return "rule_change"


def _rule_breakdown(rows: list[dict]) -> dict:
    def n(flag: str) -> int:
        return sum(1 for r in rows if flag in r["flags"])

    return {
        "n_questions": len(rows),
        "n_flagged_any": sum(1 for r in rows if r["flags"]),
        "n_manual_review_bucket": sum(1 for r in rows if r["manual_review"]),
        "rule_level": {
            "r1": sum(1 for r in rows if r["r1"]),
            "r3": sum(1 for r in rows if r["r3"]),
            "r3_unreachable": sum(
                1 for r in rows if FLAG_R3_UNREACHABLE in r["flags"]),
            "r3_violation": sum(1 for r in rows if FLAG_R3 in r["flags"]),
            "r4": sum(1 for r in rows if r["r4"]),
            "r4_full": sum(1 for r in rows if r["r4_full"]),
            "r4_mixed": sum(1 for r in rows if r["r4_mixed"]),
        },
        "flags": {f: n(f) for f in (
            FLAG_R1, FLAG_R3, FLAG_R3_UNREACHABLE, FLAG_R4_FULL, FLAG_R4_MIXED)},
        "manual_review_reasons": {
            reason: sum(1 for r in rows if reason in r["manual_review"])
            for reason in sorted({m for r in rows for m in r["manual_review"]})
        },
        "r2_pattern_distribution": {
            p: sum(1 for r in rows if r["r2_pattern"] == p)
            for p in sorted({r["r2_pattern"] for r in rows}) if p
        },
        "r3_gap_distribution": {
            g: sum(1 for r in rows if r["r3_gap"] == g)
            for g in sorted({r["r3_gap"] for r in rows}) if g
        },
        "r3_attribution_distribution": {
            a: sum(1 for r in rows if r["r3_attribution"] == a)
            for a in sorted({r["r3_attribution"] for r in rows}) if a
        },
        "n_salt_form": sum(1 for r in rows if r["salt_form"]),
        "n_parse_fail": sum(1 for r in rows if r["parse_fail"]),
        "n_ribose_observed": sum(1 for r in rows if r["ribose_observed"]),
    }


def _compare_v1_v2(rows: list[dict], v1_rows: dict[str, dict],
                   quarantined: set[str] | None = None) -> dict:
    """逐题规则级对比:v2 新增命中/命中消失/旗标翻转(分档)。"""
    new_hits: dict[str, list[str]] = {"R1": [], "R3": [], "R4": []}
    lost_hits: dict[str, list[str]] = {"R1": [], "R3": [], "R4": []}
    attribution_changes = []   # 规则级同但旗标语义变(新证据)
    rule_changes = []          # 规则级命中面变化(新证据)
    for r in rows:
        qid = r["qid"]
        v1 = v1_rows.get(qid)
        if v1 is None:
            raise SystemExit(f"v1 封存 TSV 缺 qid(fail-closed):{qid}")
        v1_rules = set(_v1_rule_level(v1))
        v2_rules = set(_v2_rule_level(r))
        for rule in ("R1", "R3", "R4"):
            if rule in v2_rules and rule not in v1_rules:
                new_hits[rule].append(qid)
            if rule in v1_rules and rule not in v2_rules:
                lost_hits[rule].append(qid)
        kind = _flip_kind(v1, r)
        if kind == "attribution_change":
            attribution_changes.append({
                "qid": qid, "v1_flags": v1["flags"], "v2_flags": r["flags"]})
        elif kind == "rule_change":
            rule_changes.append({
                "qid": qid, "v1_flags": v1["flags"], "v2_flags": r["flags"]})
    out = {
        "n_v1_flagged": sum(1 for q, v in v1_rows.items() if v["flags"]),
        "n_v2_flagged": sum(1 for r in rows if r["flags"]),
        "n_new_flagged_qids": sum(
            1 for r in rows
            if r["flags"] and not v1_rows[r["qid"]]["flags"]),
        "new_rule_hits": {k: sorted(v) for k, v in new_hits.items()},
        "lost_rule_hits": {k: sorted(v) for k, v in lost_hits.items()},
        "attribution_changes": attribution_changes,
        "rule_changes": rule_changes,
        "note": "R4 拆旗只改旗名(degenerate→full/mixed)属设计内改名,"
                "不算翻转;attribution_change/rule_change 才是新证据"
                "(单列待新冻结链,不静默改判)。",
    }
    if quarantined is not None:
        out["quarantined_v1_qids"] = sorted(quarantined)
        out["quarantined_flips_new_evidence"] = sorted(
            {c["qid"] for c in attribution_changes
             if c["qid"] in quarantined}
            | {c["qid"] for c in rule_changes
               if c["qid"] in quarantined})
    return out


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)

    # ---- dev 56(v2 全量打标,含已生效 5 题复核) ----
    dev_questions = [{"qid": r["qid"], "substrate_smiles": r["root_smiles"]}
                     for r in _iter_jsonl(DEV_QUESTIONS)]
    dev_gold = {r["qid"]: r.get("products_smiles", [])
                for r in _iter_jsonl(DEV_GOLD)}
    dev_rows = []
    for q in dev_questions:
        qid = q["qid"]
        if qid not in dev_gold:
            raise SystemExit(f"dev:题面 qid 无金标(fail-closed):{qid}")
        labels = gold_health_labels(
            substrate_smiles=q["substrate_smiles"],
            products_smiles=dev_gold[qid])
        dev_rows.append({"qid": qid, **labels,
                         "in_quarantine_v1": qid in QUARANTINED_QIDS})
    _write_tsv(OUT / "gold_health_labels_dev_v2.tsv", COLUMNS, dev_rows)

    quarantined = set(QUARANTINED_QIDS)
    dev51_rows = [r for r in dev_rows if not r["in_quarantine_v1"]]
    dev_quarantined_rows = [r for r in dev_rows if r["in_quarantine_v1"]]

    # dev quarantine 提案(仅 51 分母内新增;已生效 5 题不重复提案)
    proposal = []
    for r in dev51_rows:
        if r["flags"]:
            proposal.append({
                "qid": r["qid"],
                "flags": r["flags"],
                "rule_hits": "+".join(RULE_HITS_MAP[f] for f in r["flags"]),
                "manual_review": r["manual_review"],
                "delta_c": r["delta_c"], "delta_o": r["delta_o"],
                "delta_h": r["delta_h"],
                "r3_attribution": r["r3_attribution"],
                "r4_axis": r["r4_axis"],
                "proposed_disposition": "; ".join(
                    FLAG_DISPOSITIONS[f] for f in r["flags"]),
                "status": PROPOSAL_STATUS,
            })
    _write_tsv(OUT / "quarantine_proposal_dev_v2.tsv",
               PROPOSAL_COLUMNS, proposal)

    # 人审桶 TSV(parse_fail/羧化样式/缺口/ΔDoU/未归类 O/H 当量;不拦截)
    for name, rows in (("dev", dev_rows), ("ec298", None)):
        if rows is None:
            continue
        mr_rows = [{
            "qid": r["qid"], "manual_review": r["manual_review"],
            "flags": r["flags"], "delta_c": r["delta_c"],
            "delta_dou": r["delta_dou"], "status": PROPOSAL_STATUS,
        } for r in rows if r["manual_review"]]
        _write_tsv(OUT / f"manual_review_{name}_v2.tsv",
                   MANUAL_REVIEW_COLUMNS, mr_rows)

    # ---- 298 全卷(只打标不动分;金标 = Chenyu 只读副本) ----
    if not Q298_REMOTE_COPY.exists():
        raise SystemExit(
            "298 金标只读副本缺失(fail-closed):"
            f"{Q298_REMOTE_COPY}\n拉取:/tmp/cy_ssh.sh \"cat "
            "/usrdata/EnzymeCAGE_data/workspaces/ec298_gold_readonly/"
            "questions.jsonl\" | grep -v \"^spawn ssh\\|password:\" "
            "> /tmp/q298_ec298_gold_readonly.jsonl && tr -d '\\r' "
            "< /tmp/q298_ec298_gold_readonly.jsonl > /tmp/q.tmp && "
            "mv /tmp/q.tmp /tmp/q298_ec298_gold_readonly.jsonl")
    q298_raw = [
        {"qid": r["qid"], "substrate_smiles": r["substrate_smiles"],
         "products_smiles": r["products_smiles"],
         "nucleotide_fallback": r.get("nucleotide_fallback", False),
         "fallback_large": r.get("fallback_large", False),
         "ambiguous_substrate": r.get("ambiguous_substrate", False)}
        for r in _iter_jsonl(Q298_REMOTE_COPY)]
    rows298 = []
    for q in q298_raw:
        labels = gold_health_labels(
            substrate_smiles=q["substrate_smiles"],
            products_smiles=q["products_smiles"])
        rows298.append({"qid": q["qid"], **labels, "in_quarantine_v1": False})
    _write_tsv(OUT / "gold_health_labels_298_v2.tsv", COLUMNS, rows298)

    mr298 = [{
        "qid": r["qid"], "manual_review": r["manual_review"],
        "flags": r["flags"], "delta_c": r["delta_c"],
        "delta_dou": r["delta_dou"], "status": PROPOSAL_STATUS,
    } for r in rows298 if r["manual_review"]]
    _write_tsv(OUT / "manual_review_ec298_v2.tsv",
               MANUAL_REVIEW_COLUMNS, mr298)

    # 298 旗标交叉(与 v1 同口径:nucleotide_fallback / fallback_large /
    # ambiguous_substrate)
    cross = {}
    rows_by_qid = {r["qid"]: r for r in rows298}
    for key in ("nucleotide_fallback", "fallback_large",
                "ambiguous_substrate"):
        flagged = [q["qid"] for q in q298_raw
                   if q[key] and rows_by_qid[q["qid"]]["flags"]]
        cross[key] = {"n_true": sum(1 for q in q298_raw if q[key]),
                      "n_true_and_flagged": len(flagged),
                      "flagged_qids": flagged}

    # ---- v1 vs v2 逐题对比(读封存 TSV,只读) ----
    v1_dev = _read_v1_tsv(V1_DEV_TSV)
    v1_298 = _read_v1_tsv(V1_298_TSV)
    cmp_dev = _compare_v1_v2(dev_rows, v1_dev, quarantined)
    cmp_298 = _compare_v1_v2(rows298, v1_298)

    # 已生效 5 题旗标翻转明细(分档:none=设计内改名/全同;attribution/
    # rule_change=新证据待新链,不静默改判)
    flip_rows = []
    for r in dev_quarantined_rows:
        v1 = v1_dev[r["qid"]]
        kind = _flip_kind(v1, r)
        flip_rows.append({
            "qid": r["qid"],
            "v1_flags": v1["flags"],
            "v2_flags": r["flags"],
            "v1_rule_level": "+".join(_v1_rule_level(v1)),
            "v2_rule_level": "+".join(_v2_rule_level(r)),
            "flip_kind": kind,
            "status": ("无翻转:维持 QUARANTINE_EFFECTIVE 判定"
                       if kind == "none" else
                       "新证据待新链(mimo 评审→人审→双人确认),"
                       "不追溯作废已生效判定"),
        })
    _write_tsv(OUT / "flag_flips_effective5_v2.tsv", FLIP_COLUMNS, flip_rows)

    # ---- 汇总 ----
    summary = {
        "rules_version": RULES_VERSION,
        "status": PROPOSAL_STATUS,
        "redlines": [
            "零 LLM 零 API;金标 SMILES 零入仓(输出仅 qid+旗标+计数)",
            "v1 封存产物零覆写(本脚本只写 v2/ 子目录)",
            "298 只诊断打标不动分数不动金标",
            "不追溯作废 QUARANTINE_EFFECTIVE(2026-09-30)",
        ],
        "dev": _rule_breakdown(dev_rows),
        "dev_denominator_51": _rule_breakdown(dev51_rows),
        "dev_quarantined_5": _rule_breakdown(dev_quarantined_rows),
        "dev_quarantine_proposal_v2": {
            "n_proposed": len(proposal),
            "proposed_qids": [p["qid"] for p in proposal],
            "denominator_if_adopted": 51 - len(proposal),
            "note": "提案不生效:待新冻结链(mimo 评审→人审→双人确认);"
                    "当前生效分母仍为 51(QUARANTINE_EFFECTIVE)",
        },
        "dev_v1_v2_compare": cmp_dev,
        "ec298": _rule_breakdown(rows298),
        "ec298_v1_v2_compare": cmp_298,
        "ec298_question_flag_cross": cross,
        "inputs_sha256": {
            "dev_questions": hashlib.sha256(
                DEV_QUESTIONS.read_bytes()).hexdigest(),
            "dev_gold": hashlib.sha256(
                DEV_GOLD.read_bytes()).hexdigest(),
            "q298_chenyu_readonly": hashlib.sha256(
                Q298_REMOTE_COPY.read_bytes()).hexdigest(),
            "q298_local_sealed_copy": hashlib.sha256(
                Q298_LOCAL_SEALED.read_bytes()).hexdigest(),
        },
        "q298_gold_source": {
            "remote_path": ("/usrdata/Enzyme_CAGE_DATA/workspaces/"
                            "ec298_gold_readonly/questions.jsonl"),
            "remote_path_actual": ("/usrdata/EnzymeCAGE_data/workspaces/"
                                   "ec298_gold_readonly/questions.jsonl"),
            "note": "远端只读副本(任务书路径 Enzyme_CAGE_DATA 实机为 "
                    "EnzymeCAGE_data);拉取经 /tmp/cy_ssh.sh(expect 封装,"
                    "stdout 噪声 grep -v 过滤,CR 为管道伪影已 tr -d '\\r'"
                    " 剥离);SHA 与封存本地副本一致(9f5955d4…)",
        },
    }
    (OUT / "gold_health_summary_v2.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n", encoding="utf-8")
    print(json.dumps({
        "rules_version": RULES_VERSION,
        "dev": {"n_flagged": summary["dev"]["n_flagged_any"],
                "n_manual_review": summary["dev"]["n_manual_review_bucket"],
                "rule_level": summary["dev"]["rule_level"]},
        "dev51_new_proposal": len(proposal),
        "ec298": {"n_flagged": summary["ec298"]["n_flagged_any"],
                  "n_manual_review": summary["ec298"]["n_manual_review_bucket"],
                  "rule_level": summary["ec298"]["rule_level"]},
        "flips_effective5": [f["qid"] for f in flip_rows
                             if f["flip_kind"] != "none"],
    }, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
