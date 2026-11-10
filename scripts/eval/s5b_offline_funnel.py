#!/usr/bin/env python3
"""s5b_offline_funnel.py — S5B chain11/12 离线只读全链拼账工具（T2）。

题域标签：298 / RHEA 通用酶学 / 已见题。输出引用一律带此标签。

用途：对一批 s5b 已同步判分产物（synced/{metrics.json,batch_manifest.json,cases/,runs/}），
逐题从 native_export payload 重建候选招聘全链（池供给 → decide → 去重/预校验 → 调度 →
执行 → 准入 → 事件提交 → 题级匹配），并对 uncovered 题给互斥主因分桶（A–I，按最深
到达阶段），闭合到 uncovered 总数；对 strict/partial 给同口径供给面描述统计。

红线：零模型、零网络、零 LLM；只读 synced/；不跑评测器、不重算逐事件匹配（T3）；
拼不出标 unknown；qid↔run_id 映射双向核对，映射不一致只记录不修数据。

用法：
    python3 scripts/s5b_offline_funnel.py <batch_root> <out_dir> [--label NAME]

    <batch_root>  含 synced/ 的批根，如 reports/ppv1_s5b/chain12_s5b_298_v4b_20261012
    <out_dir>     输出目录（建议 reports/ppv1_s5b/<批>/analysis/，已 gitignored）
    --label       输出文件名标签（默认取批根目录名）

输出：funnel_<label>.json（逐题逐桶原始）+ funnel_<label>_summary.md（该批分桶表），
并同步复制到 /tmp/s5b_t2_funnel/。stdout 打印紧凑摘要。

主桶判据（互斥，按最深到达阶段；歧义进交集标志不硬归）：
  A 无候选           expansion_outcomes 有 no_local_candidate，或 (specs=0 且 parsed=0 且未选中)
  B 死在 decide 前    run 级失败（prepare/transport，cases.run_error）或 有候选但无 prepared/
                     调度痕迹（池编译全败 / novel 预校验全败且无 dedup）
  C 去重折叠损失      全部 parsed 候选被 dedup_rejections 折叠
  D 调度落选          候选止步 deferred(alternatives_budget/selection_cap)/blocked，未执行
  E 执行失败          selected 候选全部 method_failed（production status=method_failed）
  F 准入拒绝          admission disposition reject/defer 且未转正（枚举对齐
                      audit.py ADMISSION_REJECT/ADMISSION_DEFER；T7 修复前读
                      错枚举 rejected/deferred 且无分支，F 恒 0 不可作证据）
  G 预算截断          stop_reason=budget_limit 且 selected 候选未展开（selected > 提交+method_failed）
  H 已提交不匹配      有提交事件但题级 uncovered（逐事件归因=T3）
  I 其他/unknown      以上拼不出，诚实标注
"""

import argparse
import json
import os
import shutil
import sys
from collections import Counter
from statistics import median

TMP_DIR = "/tmp/s5b_t2_funnel"

BUCKET_DESC = {
    "A": "无候选(no_local_candidate/specs=0)",
    "B": "有候选但死在 decide 前(prepare/transport/池编译全败/novel 预校验全败)",
    "C": "去重折叠损失(dedup 吞全部)",
    "D": "调度落选(deferred alternatives_budget/selection_cap 或 blocked)",
    "E": "执行失败(method_failed)",
    "F": "准入拒绝(admission reject/defer 未转正)",
    "G": "预算截断(budget_limit 且 selected 未展开)",
    "H": "已提交但不匹配(逐事件归因=T3)",
    "I": "其他/unknown",
}

# metrics match_status → 简写
STATUS_SHORT = {
    "matched_strict": "strict",
    "matched_participant_coverage_partial": "partial",
    "unmatched_required_node_uncovered": "uncovered",
}


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def payload_path(synced, run_id, export_digest):
    return os.path.join(synced, "runs", run_id, "native_export",
                        (export_digest or "")[:24], "payload.json")


def extract_funnel(case, payload, man_entry, mrow):
    """从 case/payload/manifest entry/metrics 行拼单题全链事实。"""
    counts = case.get("counts") or {}
    run_error = case.get("run_error") or {}
    endpoint = case.get("endpoint") or {}

    f = {}
    f["qid"] = case["qid"]
    f["run_id"] = case.get("run_id")
    f["match_status"] = (mrow or {}).get("main", {}).get("match_status")
    f["match_short"] = STATUS_SHORT.get(f["match_status"], f["match_status"])
    f["rank"] = (mrow or {}).get("main", {}).get("rank")
    f["case_status"] = case.get("status")
    f["stop_reason"] = case.get("stop_reason")
    f["endpoint_execution_status"] = endpoint.get("execution_status")

    # ---- 池层（旧批只有聚合直方图：pool_layer_aggregate_only）----
    pd_ = (man_entry or {}).get("pool_diagnostics") or {}
    compile_hist = pd_.get("compile_failure_histogram") or {}
    f["pool_compile_fail_hist"] = dict(sorted(compile_hist.items()))
    f["pool_compile_fail_total"] = int(sum(compile_hist.values()))
    f["pool_compiled"] = int((man_entry or {}).get("pool_size") or 0)
    f["pool_size_payload"] = None
    f["specs_raw"] = f["pool_compiled"] + f["pool_compile_fail_total"]

    # ---- decide / 提案层 ----
    outcomes = []
    for eo in payload.get("expansion_outcomes", []):
        o = (eo.get("outcome_payload") or {}).get("outcome") or {}
        outcomes.append(o)
    f["outcome_kinds"] = Counter(o.get("kind") for o in outcomes)
    f["no_local_candidate"] = bool(f["outcome_kinds"].get("no_local_candidate"))
    f["method_failed_outcomes"] = int(f["outcome_kinds"].get("method_failed", 0))

    f["decide_actions"] = []
    for sa in payload.get("search_actions", []):
        if sa.get("action_kind") == "decide":
            f["decide_actions"].append({
                "action_id": sa.get("action_id"),
                "status": sa.get("status"),
            })
    sched = None
    for o in outcomes:
        if o.get("kind") == "scheduled":
            sched = o.get("detail") or {}
    f["has_scheduled_outcome"] = sched is not None
    model = (sched or {}).get("model") or {}
    f["model_abstained"] = bool(model.get("abstained"))
    rank_map = model.get("model_rank_by_id") or {}
    f["parsed"] = int(model.get("parsed_proposals") or len(rank_map))
    f["model_ranked"] = len(rank_map)
    f["novel_proposals"] = len(model.get("novel_proposals") or [])
    dedup = model.get("dedup_rejections") or []
    novel_rej = model.get("novel_rejections") or []
    f["dedup_rejections"] = len(dedup)
    f["novel_rejections"] = len(novel_rej)
    f["novel_rejection_kinds"] = dict(Counter(r.get("kind") for r in novel_rej))
    f["network_request_count"] = int(model.get("network_request_count") or 0)

    # ---- 调度层 ----
    f["selected"] = int((sched or {}).get("selected") or 0)
    f["deferred_decide"] = int((sched or {}).get("deferred") or 0)
    f["blocked_decide"] = int((sched or {}).get("blocked") or 0)

    defer_types = Counter()
    defer_reasons = Counter()
    deferred_root = 0  # 根路径候选级 defer（alternatives_budget/selection_cap 等）
    for de in payload.get("deferred_entries", []):
        t = de.get("deferred_type")
        r = de.get("reason")
        defer_types[t] += 1
        defer_reasons[r] += 1
        # coproduct_deferred/depth_limit 是提交后副产品深度语义，不算根候选落选
        if t != "coproduct_deferred":
            deferred_root += 1
    f["deferred_entry_types"] = dict(defer_types)
    f["deferred_entry_reasons"] = dict(defer_reasons)
    f["deferred_root"] = deferred_root
    f["depth_deferrals"] = int(defer_reasons.get("depth_limit", 0))
    f["alternatives_budget_deferrals"] = int(defer_reasons.get("alternatives_budget", 0))
    f["blocked_entries"] = len(payload.get("blocked_entries") or [])

    # alt statuses（alternatives 数组）
    alt_status = Counter()
    for alt in payload.get("alternatives", []):
        for st in alt.get("statuses", []):
            alt_status[st] += 1
    f["alternative_statuses"] = dict(alt_status)

    # ---- 执行/准入/提交层 ----
    f["hypotheses"] = len(payload.get("hypotheses") or [])
    f["events"] = len(payload.get("events") or [])
    f["paths"] = len(payload.get("paths") or [])
    f["states"] = len(payload.get("states") or [])

    dispositions = Counter()
    method_failed_productions = 0
    created_true = 0
    created_other = 0
    audit_unknown_checks = 0
    audit_checks_total = 0
    for apr in payload.get("audit_production_reports", []):
        pp = apr.get("production_payload") or {}
        adm = pp.get("admission") or {}
        dispositions[adm.get("disposition")] += 1
        if pp.get("status") == "method_failed":
            method_failed_productions += 1
        sub = pp.get("submitted") or {}
        if sub.get("created") is True:
            created_true += 1
        elif "created" in sub:
            created_other += 1
        audit = pp.get("audit") or {}
        for chk in audit.get("checks") or []:
            audit_checks_total += 1
            if chk.get("status") == "unknown":
                audit_unknown_checks += 1
    f["admission_dispositions"] = {str(k): v for k, v in dispositions.items()}
    # 准入枚举权威：audit.py ADMISSION_REJECT="reject"/ADMISSION_DEFER="defer"
    # （T7 勘误：原读 rejected/deferred 属另一层 production status，非准入枚举）
    f["admission_rejected_or_deferred"] = int(
        dispositions.get("reject", 0) + dispositions.get("defer", 0))
    f["method_failed_productions"] = method_failed_productions
    f["events_created_flag"] = created_true
    f["events_created_other"] = created_other
    f["audit_unknown_checks"] = audit_unknown_checks
    f["audit_checks_total"] = audit_checks_total

    # ---- run 级失败（prepare/transport：decide run 级失败，cases 判）----
    f["run_error"] = None if not run_error else {
        "error": run_error.get("error"),
        "kind": run_error.get("kind"),
        "message_head": (run_error.get("message") or "")[:160],
    }
    f["run_failed"] = bool(run_error) or case.get("status") != "completed" \
        or endpoint.get("execution_status") == "failed"
    f["failure_kind"] = run_error.get("kind") if run_error else None

    # ---- 预算对账（run_level 快照）----
    bs = ((payload.get("budget") or {}).get("budget_snapshot") or {}).get("run_level") or {}
    f["budget_run_level"] = {
        k: (v or {}).get("remaining") for k, v in bs.items()
        if isinstance(v, dict)
    }
    return f


def classify(f):
    """互斥主桶，按最深到达阶段。返回 (bucket, reason)。"""
    if f["events"] > 0:
        return "H", f"events={f['events']}"
    if f["run_failed"]:
        return "B", f"run_failed kind={f['failure_kind']}"
    if f["no_local_candidate"]:
        return "A", "outcome no_local_candidate"
    if f["selected"] > 0:
        # F（准入拒绝）按最深到达阶段插在 E 前：准入在执行之后，
        # 候选走到 reject/defer 即已过执行层；执行失败与准入拒并存的
        # 歧义由交集标志（has_method_failed / has_admission_reject_or_defer）
        # 承载，不在此硬归第二原因。
        if f["admission_rejected_or_deferred"] > 0 and f["events_created_flag"] == 0:
            return "F", (f"admission reject/defer={f['admission_rejected_or_deferred']}"
                         f" 未转正 (created={f['events_created_flag']})")
        if f["method_failed_productions"] > 0 and f["events_created_flag"] == 0:
            return "E", (f"method_failed productions={f['method_failed_productions']}"
                         f"/selected={f['selected']}")
        if f["events_created_flag"] == 0 and f["stop_reason"] == "budget_limit" \
                and f["selected"] > f["method_failed_productions"]:
            return "G", (f"selected={f['selected']} 未展开 "
                         f"(created=0, method_failed={f['method_failed_productions']}, "
                         f"stop={f['stop_reason']})")
        if f["events_created_flag"] == 0 and (f["deferred_root"] > 0 or f["blocked_entries"] > 0):
            return "D", f"deferred_root={f['deferred_root']} blocked={f['blocked_entries']}"
        return "I", (f"selected={f['selected']} 但 created=0 且无明确截断痕迹")
    # selected == 0
    if f["parsed"] == 0 and f["specs_raw"] == 0:
        return "A", f"specs=0 parsed=0 (abstained={f['model_abstained']})"
    if f["parsed"] == 0 and f["specs_raw"] > 0:
        return "B", f"池候选全灭于编译 pre-decide (compile_fail={f['pool_compile_fail_total']})"
    if f["dedup_rejections"] + f["novel_rejections"] >= f["parsed"]:
        if f["dedup_rejections"] > 0:
            return "C", (f"dedup={f['dedup_rejections']} novel_rej={f['novel_rejections']}"
                         f"/parsed={f['parsed']}")
        return "B", (f"novel 预校验全败 novel_rej={f['novel_rejections']}"
                     f"/parsed={f['parsed']} (decide 内,无 dedup)")
    if f["deferred_root"] > 0 or f["blocked_entries"] > 0 or f["deferred_decide"] > 0 \
            or f["blocked_decide"] > 0:
        return "D", (f"deferred_root={f['deferred_root']} blocked={f['blocked_entries']} "
                     f"decide_defer={f['deferred_decide']}")
    return "I", "拼不出（无候选丢失痕迹也无事件）"


def supply_view(rows):
    """供给面描述统计（不判分）。"""
    def agg(key):
        vals = [r[key] for r in rows]
        if not vals:
            return {"n": 0}
        return {
            "n": len(vals),
            "sum": int(sum(vals)),
            "mean": round(sum(vals) / len(vals), 2),
            "median": median(vals),
            "max": max(vals),
            "min": min(vals),
        }
    return {
        "n_qids": len(rows),
        "specs_raw": agg("specs_raw"),
        "pool_compiled": agg("pool_compiled"),
        "pool_compile_fail_total": agg("pool_compile_fail_total"),
        "parsed_candidates": agg("parsed"),
        "selected": agg("selected"),
        "events": agg("events"),
        "paths": agg("paths"),
        "states": agg("states"),
        "depth_deferrals": agg("depth_deferrals"),
        "audit_unknown_checks": agg("audit_unknown_checks"),
        "method_failed_productions": agg("method_failed_productions"),
        "dedup_rejections": agg("dedup_rejections"),
        "novel_rejections": agg("novel_rejections"),
        "n_with_events_gt0": sum(1 for r in rows if r["events"] > 0),
        "n_with_pool_compile_fail": sum(1 for r in rows if r["pool_compile_fail_total"] > 0),
        "n_with_dedup": sum(1 for r in rows if r["dedup_rejections"] > 0),
        "n_with_novel_rejections": sum(1 for r in rows if r["novel_rejections"] > 0),
        "n_with_method_failed": sum(1 for r in rows if r["method_failed_productions"] > 0
                                    or r["method_failed_outcomes"] > 0),
        "n_with_run_failed": sum(1 for r in rows if r["run_failed"]),
    }


def intersect_flags(f):
    """多原因交集标志（主桶单列，交集在此）。"""
    return {
        "has_pool_compile_fails": f["pool_compile_fail_total"] > 0,
        "has_dedup_rejections": f["dedup_rejections"] > 0,
        "has_novel_rejections": f["novel_rejections"] > 0,
        "has_method_failed": f["method_failed_outcomes"] > 0,
        "has_admission_reject_or_defer": f["admission_rejected_or_deferred"] > 0,
        "has_alternatives_budget_defer": f["alternatives_budget_deferrals"] > 0,
        "has_depth_deferrals": f["depth_deferrals"] > 0,
        "run_failed": f["run_failed"],
        "no_local_candidate": f["no_local_candidate"],
    }


def main():
    ap = argparse.ArgumentParser(description="S5B offline funnel (T2), read-only")
    ap.add_argument("batch_root")
    ap.add_argument("out_dir")
    ap.add_argument("--label", default=None)
    args = ap.parse_args()
    label = args.label or os.path.basename(os.path.normpath(args.batch_root))
    synced = os.path.join(args.batch_root, "synced")

    metrics = load_json(os.path.join(synced, "metrics.json"))
    manifest = load_json(os.path.join(synced, "batch_manifest.json"))
    mrows = {r["qid"]: r for r in metrics["per_qid"]}
    mentries = {e["qid"]: e for e in manifest["entries"]}

    # ---- qid↔run_id 映射双向核对 ----
    mapping_issues = []
    for qid, r in mrows.items():
        e = mentries.get(qid)
        if e is None:
            mapping_issues.append({"qid": qid, "issue": "metrics qid 不在 manifest"})
        elif e.get("run_id") != r.get("run_id"):
            mapping_issues.append({"qid": qid, "issue": "metrics.run_id != manifest.run_id",
                                   "metrics": r.get("run_id"), "manifest": e.get("run_id")})
    for qid, e in mentries.items():
        if qid not in mrows:
            mapping_issues.append({"qid": qid, "issue": "manifest qid 不在 metrics"})

    rows = []
    payload_missing = []
    qids = sorted(mrows.keys())
    for qid in qids:
        mrow = mrows[qid]
        case_path = os.path.join(synced, "cases", qid + ".json")
        if not os.path.exists(case_path):
            payload_missing.append({"qid": qid, "issue": "case 文件缺失"})
            continue
        case = load_json(case_path)
        # case.run_id 与 metrics 双向核对
        if case.get("run_id") != mrow.get("run_id"):
            mapping_issues.append({"qid": qid, "issue": "case.run_id != metrics.run_id",
                                   "case": case.get("run_id"), "metrics": mrow.get("run_id")})
        pp = payload_path(synced, case.get("run_id"), case.get("export_digest"))
        if not os.path.exists(pp):
            payload_missing.append({"qid": qid, "issue": "payload 文件缺失", "path": pp})
            continue
        payload = load_json(pp)
        f = extract_funnel(case, payload, mentries.get(qid), mrow)
        # payload 内 run_id 一致性
        if payload.get("run_id") != case.get("run_id"):
            mapping_issues.append({"qid": qid, "issue": "payload.run_id != case.run_id"})
        # case counts.events 与 payload events 对账
        if (case.get("counts") or {}).get("events") != f["events"]:
            mapping_issues.append({"qid": qid,
                                   "issue": "case.counts.events != payload.events",
                                   "case": (case.get("counts") or {}).get("events"),
                                   "payload": f["events"]})
        bucket, why = classify(f)
        f["bucket"] = bucket
        f["bucket_reason"] = why
        f["intersection_flags"] = intersect_flags(f)
        rows.append(f)

    # ---- 分桶闭合（对 uncovered）----
    uncovered = [r for r in rows if r["match_short"] == "uncovered"]
    bucket_counter = Counter(r["bucket"] for r in uncovered)
    closure = {
        "n_uncovered_metrics": metrics.get("buckets", {}).get(
            "unmatched_required_node_uncovered"),
        "n_uncovered_rows": len(uncovered),
        "bucket_counts": dict(sorted(bucket_counter.items())),
        "sum_buckets": sum(bucket_counter.values()),
        "closed": sum(bucket_counter.values()) == len(uncovered),
    }

    all_bucket_counter = Counter(r["bucket"] for r in rows)

    # ---- 供给面视图 ----
    supply = {
        "strict": supply_view([r for r in rows if r["match_short"] == "strict"]),
        "partial": supply_view([r for r in rows if r["match_short"] == "partial"]),
        "uncovered": supply_view(uncovered),
    }

    # ---- 交集表（uncovered 内多因并存计数）----
    inter = {
        "bucket_x_flag": {},
        "flag_counts_uncovered": {},
    }
    flags_all = ["has_pool_compile_fails", "has_dedup_rejections", "has_novel_rejections",
                 "has_method_failed", "has_admission_reject_or_defer",
                 "has_alternatives_budget_defer", "has_depth_deferrals",
                 "run_failed", "no_local_candidate"]
    for flag in flags_all:
        inter["flag_counts_uncovered"][flag] = sum(
            1 for r in uncovered if r["intersection_flags"][flag])
    for r in uncovered:
        b = r["bucket"]
        inter["bucket_x_flag"].setdefault(b, {})
        for flag in flags_all:
            if r["intersection_flags"][flag]:
                inter["bucket_x_flag"][b][flag] = inter["bucket_x_flag"][b].get(flag, 0) + 1

    result = {
        "meta": {
            "tool": "scripts/s5b_offline_funnel.py",
            "mode": "offline read-only; zero model/network/LLM; no evaluator rerun",
            "domain_tag": "298/RHEA 通用酶学/已见题",
            "batch_root": os.path.abspath(args.batch_root),
            "label": label,
            "metrics_domain_tag": metrics.get("domain_tag"),
            "main_caliber_hit": {k: metrics.get("main_caliber", {}).get(k)
                                 for k in ("hit@1", "hit@3", "hit@5")},
            "buckets_from_metrics": metrics.get("buckets"),
            "pool_layer_note": "pool_layer_aggregate_only: 旧批池层候选明细未同步，"
                               "池供给只有 manifest pool_diagnostics 聚合直方图 + pool_size",
        },
        "closure": closure,
        "bucket_counts_all_298": dict(sorted(all_bucket_counter.items())),
        "bucket_qids": {b: sorted(r["qid"] for r in uncovered if r["bucket"] == b)
                        for b in sorted(bucket_counter)},
        "supply_view": supply,
        "intersection": inter,
        "mapping_issues": mapping_issues,
        "payload_missing": payload_missing,
        "per_qid": rows,
    }

    os.makedirs(args.out_dir, exist_ok=True)
    os.makedirs(TMP_DIR, exist_ok=True)
    out_json = os.path.join(args.out_dir, f"funnel_{label}.json")
    with open(out_json, "w", encoding="utf-8") as fh:
        json.dump(result, fh, ensure_ascii=False, indent=1)
    shutil.copy2(out_json, os.path.join(TMP_DIR, f"funnel_{label}.json"))

    # ---- markdown 摘要（该批）----
    md = []
    md.append(f"# funnel 摘要 — {label}\n")
    md.append("题域标签：**298 / RHEA 通用酶学 / 已见题**；离线只读拼账，零模型零网络。\n")
    md.append(f"- metrics 桶：{metrics.get('buckets')}")
    md.append(f"- 行数（拼账覆盖）：{len(rows)} / {len(qids)}")
    if mapping_issues:
        md.append(f"- 映射核对问题：{len(mapping_issues)} 条（见 JSON mapping_issues）")
    else:
        md.append("- 映射核对：qid↔run_id（cases/metrics/manifest/payload 四方）全部一致")
    md.append("")
    md.append("## uncovered 主桶（互斥，按最深到达阶段）\n")
    md.append("| 主桶 | 判据摘要 | 题数 |")
    md.append("|---|---|---:|")
    for b in "ABCDEFGHI":
        n = bucket_counter.get(b, 0)
        md.append(f"| {b}. {BUCKET_DESC[b].split('(')[0]} | {BUCKET_DESC[b]} | {n} |")
    md.append(f"| **和** | | **{closure['sum_buckets']}** |")
    md.append("")
    md.append(f"闭合自检：sum={closure['sum_buckets']} vs uncovered={closure['n_uncovered_rows']}"
              f" → {'闭合' if closure['closed'] else '不闭合(查映射)'}\n")
    md.append("## 全 298 题同口径桶分布\n")
    md.append("| 主桶 | 题数 |")
    md.append("|---|---:|")
    for b in sorted(all_bucket_counter):
        md.append(f"| {b} | {all_bucket_counter[b]} |")
    md.append("")
    md.append("## 供给面描述统计（不判分）\n")
    for grp in ("strict", "partial", "uncovered"):
        sv = supply[grp]
        md.append(f"### {grp}（n={sv['n_qids']}）\n")
        md.append("| 指标 | sum | mean | median | max |")
        md.append("|---|---:|---:|---:|---:|")
        for k in ("specs_raw", "pool_compiled", "parsed_candidates", "selected",
                  "events", "paths", "states", "depth_deferrals", "audit_unknown_checks"):
            a = sv[k]
            md.append(f"| {k} | {a['sum']} | {a['mean']} | {a['median']} | {a['max']} |")
        md.append("")
        md.append(f"含标志题数：池编译失败 {sv['n_with_pool_compile_fail']}，dedup "
                  f"{sv['n_with_dedup']}，novel 预校验拒 {sv['n_with_novel_rejections']}，"
                  f"method_failed {sv['n_with_method_failed']}，run 失败 "
                  f"{sv['n_with_run_failed']}，有事件 {sv['n_with_events_gt0']}\n")
    out_md = os.path.join(args.out_dir, f"funnel_{label}_summary.md")
    with open(out_md, "w", encoding="utf-8") as fh:
        fh.write("\n".join(md) + "\n")
    shutil.copy2(out_md, os.path.join(TMP_DIR, f"funnel_{label}_summary.md"))

    # ---- stdout 紧凑摘要 ----
    print(f"[{label}] rows={len(rows)}/{len(qids)} mapping_issues={len(mapping_issues)} "
          f"payload_missing={len(payload_missing)}")
    print(f"[{label}] uncovered closure: {closure['bucket_counts']} "
          f"sum={closure['sum_buckets']} vs {closure['n_uncovered_rows']} "
          f"closed={closure['closed']}")
    print(f"[{label}] all-298 buckets: {dict(sorted(all_bucket_counter.items()))}")
    print(f"[{label}] out: {out_json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
