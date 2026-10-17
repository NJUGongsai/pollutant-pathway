#!/usr/bin/env python3
"""T-F 位次传递核查 · 只读独立复算探针（在隔离临时目录里执行）。

背景（自包含）
--------------
chain13 批（298 题域 = RHEA 通用酶学/已见题）的 P0② rank 审计得出三项背景结论：
  ① 折叠丢位 = 0 题；② hit@1 掉出第一的 8 题 + strict rank>1 的 32 题「模型第一名
  已是首事件」；③ 微秒碰撞 = 0。本探针**不复用** rank_audit.py 的任何函数，直接从
  synced 一手产物独立复算同一批事实，用于核对「判据同源 / 覆盖是否包含被核分支」。

复算四组：
  P1 去重折叠事件逐条明细（被折叠者/幸存者声明位次、幸存者 effective_rank/rank_basis）
  P2 模型首位 vs 提交序首事件（判据 = (created_at, event_id) 升序，与 scorer 同判据）
  P3 同题内 created_at 逐字节相同的事件对（微秒碰撞，聚合计数）
  P4 重点两组覆盖：lost_to_rank_gt1 8 题（attr JSON 清单）+ strict 且 rank>1 全集

只读：零网络、零模型、不读题面/参考图/gold、不写任何仓库文件。
输出：JSON（--out）+ 控制台摘要。
"""
from __future__ import annotations

import argparse
import collections
import glob
import hashlib
import json
import os
import sys


def load_json(path: str):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def scheduled_outcomes(payload: dict) -> list[dict]:
    """全部 decide 完成态（kind=scheduled）的 outcome，按出现序。"""
    out = []
    for rec in payload.get("expansion_outcomes") or []:
        outcome = ((rec.get("outcome_payload") or {}).get("outcome") or {})
        if outcome.get("kind") == "scheduled":
            out.append(outcome)
    return out


def payload_path(sync: str, case: dict) -> str:
    return os.path.join(sync, "runs", str(case["run_id"]), "native_export",
                        str(case["export_digest"])[:24], "payload.json")


def analyse_question(qid: str, case: dict, sync: str) -> dict:
    row: dict = {
        "qid": qid,
        "run_id": case.get("run_id"),
        "payload_found": False,
        "notes": [],
    }
    ppath = payload_path(sync, case)
    if not os.path.isfile(ppath):
        row["payload_missing"] = True
        return row
    row["payload_found"] = True
    payload = load_json(ppath)

    events = list(payload.get("events") or [])
    actions = list(payload.get("search_actions") or [])
    expands = [a for a in actions
               if a.get("action_kind") == "expand_hypothesis"]

    # 逐题口径：审计算法取「最后一个 scheduled」（多 decide 时只留一条）。
    # 本探针同时记录 scheduled 条数，用于披露口径折叠。
    scheds = scheduled_outcomes(payload)
    row["n_scheduled_decide_outcomes"] = len(scheds)
    sched = scheds[-1] if scheds else None

    model: dict = {}
    dedup_rejections: list[dict] = []
    novel_keys: set[str] = set()
    if sched is not None:
        model = (sched.get("detail") or {}).get("model") or {}
        dedup_rejections = list(model.get("dedup_rejections") or [])
        novel_keys = {str(p.get("hypothesis_id") or "")
                      for p in (model.get("novel_proposals") or [])}
    declared = {str(k): int(v)
                for k, v in (model.get("model_rank_by_id") or {}).items()}
    novel_rejections = list(model.get("novel_rejections") or [])

    # 展开条目视图（冻结任务载荷里的位次事实）
    entries: dict[str, dict] = {}
    prepared_to_logical: dict[str, str] = {}
    for a in expands:
        pl = a.get("payload") or {}
        logical = str(pl.get("logical_proposal_id") or "")
        if not logical:
            continue
        entries[logical] = {
            "logical_proposal_id": logical,
            "prepared_hypothesis_id": str(
                pl.get("prepared_hypothesis_id") or ""),
            "model_rank": pl.get("model_rank"),
            "effective_rank": pl.get("effective_rank"),
            "rank_basis": pl.get("rank_basis"),
            "status": str(a.get("status") or ""),
        }
        if pl.get("prepared_hypothesis_id"):
            prepared_to_logical[str(pl["prepared_hypothesis_id"])] = logical

    def resolve(declared_id: str) -> str | None:
        """声明 ID → 逻辑候选键（池 prepared id / novel 自报 id 两个命名空间）。"""
        if declared_id in prepared_to_logical:
            return prepared_to_logical[declared_id]
        if declared_id in entries:
            return declared_id
        return None

    def entry_of(declared_id: str) -> dict | None:
        key = resolve(declared_id)
        return entries.get(key) if key else None

    # ---- 模型首位（rank=1）----
    ranked = sorted(declared.items(), key=lambda kv: (kv[1], kv[0]))
    model_first_declared = ranked[0][0] if ranked else None
    model_first_logical = (resolve(model_first_declared)
                           if model_first_declared else None)
    row["model_first_declared_id"] = model_first_declared
    row["model_first_logical"] = model_first_logical
    row["model_first_entry"] = (entries.get(model_first_logical)
                                if model_first_logical else None)

    # ---- 未解析的声明位次 ID 的去向闭合 ----
    # 模型对「池条目」是按 prepared_hypothesis_id 报位次的,对 novel 是按自报 id。
    # 因此某条被 rank 的条目若既无 expand 条目、又不在 novel_rejections / dedup
    # 表里,就是「位次事实说不清去向」——必须单列,不能用「首位被折叠=0」盖过。
    novel_rejection_ids = {str(r.get("hypothesis_id") or "")
                           for r in novel_rejections}
    folded_ids = {str(d.get("logical_proposal_id") or "")
                  for d in dedup_rejections}
    unresolved = sorted(d for d in declared if resolve(d) is None)
    row["unresolved_declared_ids"] = unresolved

    def _fate(d: str) -> str:
        if d in novel_rejection_ids:
            return "novel_prevalidation_failed"
        if d in folded_ids:
            return "dedup_folded"
        return "unexplained"

    row["unresolved_declared_class_by_id"] = {d: _fate(d) for d in unresolved}
    row["unresolved_declared_class"] = sorted(
        set(row["unresolved_declared_class_by_id"].values()))

    # ---- 去重折叠：逐条明细 ----
    folds = []
    for d in dedup_rejections:
        folded_key = str(d.get("logical_proposal_id") or "")
        survivor_key = str(d.get("merged_into") or "")
        folded_entry = entries.get(folded_key)          # 被折叠者无展开条目
        surv_entry = entries.get(survivor_key)
        folds.append({
            "folded_logical_proposal_id": folded_key,
            "merged_into": survivor_key,
            "folded_declared_rank": declared.get(folded_key),
            "folded_has_expand_action": folded_entry is not None,
            "survivor_declared_rank": declared.get(survivor_key),
            "survivor_effective_rank": (surv_entry or {}).get("effective_rank"),
            "survivor_rank_basis": (surv_entry or {}).get("rank_basis"),
            "survivor_has_expand_action": surv_entry is not None,
            "folded_is_model_first": (model_first_declared is not None
                                      and folded_key == model_first_declared),
            "folded_is_rank1_in_declared_table": (
                declared.get(folded_key) == 1),
        })
    row["dedup_folds"] = folds

    # ---- fallback 候选（未被显式 rank 的池条目）----
    # ---- 池装配(build)侧折叠痕迹:幸存 spec 上的 compile.merged_source_keys ----
    # 口径:s5b_builder 池通道融合把同净反应签名的后到 spec 折叠进先生效 spec,
    # 并在幸存 spec 的 compile.merged_source_keys 里留痕;该 spec 随冻结任务
    # 载荷进入 expand action 的 payload.spec。
    build_merges = []
    for a in expands:
        pl = a.get("payload") or {}
        spec = pl.get("spec") or {}
        merged_keys = ((spec.get("compile") or {})
                       .get("merged_source_keys") or [])
        if merged_keys:
            build_merges.append({
                "logical_proposal_id": str(
                    pl.get("logical_proposal_id") or ""),
                "merged_source_keys": [str(x) for x in merged_keys],
            })
    row["build_side_merges"] = build_merges

    # ---- 报告投影面(product_ranks/report_rank + dedup_notes)----
    # 第二个「位次事实面」:非模型 rank,来自 build_report_projection 的
    # declared_rank_order + 报告宽度 K;旧口径 scorer 按 report_rank 序消费。
    projs = list(payload.get("report_projections") or [])
    row["report_projection_surface"] = {
        "n_projections": len(projs),
        "n_with_dedup_notes": sum(
            1 for r in projs if (r.get("dedup_notes") or [])),
        "n_report_rank_none_slots": sum(
            1 for r in projs
            for e in ((r.get("payload") or {}).get("product_ranks") or [])
            if e.get("report_rank") is None),
    }

    row["n_fallback_entries"] = sum(
        1 for e in entries.values()
        if e["rank_basis"] == "deterministic_fallback")
    row["fallback_keys"] = sorted(
        k for k, e in entries.items()
        if e["rank_basis"] == "deterministic_fallback")

    # ---- 折叠题的全部展开条目:声明位次 vs 生效位次（看紧凑化传递）----
    # 只在有折叠的题上落这份明细（限长,避免大产物）。
    if dedup_rejections:
        row["entries_declared_vs_effective"] = sorted(
            ({
                "logical_proposal_id": e["logical_proposal_id"],
                "declared_rank": declared.get(e["logical_proposal_id"]),
                "effective_rank": e["effective_rank"],
                "rank_basis": e["rank_basis"],
                "status": e["status"],
            } for e in entries.values()),
            key=lambda d: (d["effective_rank"] is None,
                           d["effective_rank"] or 0))

    # ---- 提交序首事件（判据与 scorer 相同：created_at, event_id 升序）----
    ev_rows = [{
        "event_id": str(e.get("event_id") or ""),
        "created_at": str(e.get("created_at") or ""),
        "hypothesis_id": str(e.get("hypothesis_id") or ""),
    } for e in events]
    ev_rows.sort(key=lambda e: (e["created_at"], e["event_id"]))
    row["n_events"] = len(ev_rows)
    first_ev = ev_rows[0] if ev_rows else None
    row["first_event"] = first_ev
    mf_entry = entries.get(model_first_logical) if model_first_logical else None
    if first_ev is None:
        row["transfer"] = "no_first_event"
    elif mf_entry and first_ev["hypothesis_id"] == \
            mf_entry["prepared_hypothesis_id"]:
        row["transfer"] = "model_first_is_first_event"
    elif mf_entry is None:
        row["transfer"] = "no_model_first_entry_in_pool"
    else:
        row["transfer"] = "first_event_is_other_candidate"

    # ---- 微秒碰撞（同题内 created_at 逐字节相同的事件对）----
    by_ts = collections.defaultdict(list)
    for e in ev_rows:
        by_ts[e["created_at"]].append(e["event_id"])
    collide = {ts: ids for ts, ids in by_ts.items() if len(ids) > 1}
    row["microsecond_collisions"] = {
        "n_pairs": sum(len(v) * (len(v) - 1) // 2 for v in collide.values()),
        "detail": collide,
    }
    return row


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sync", required=True, help="synced 目录（只读）")
    ap.add_argument("--attr", required=True, help="attr_chain13_c.json（只读）")
    ap.add_argument("--audit", required=True,
                    help="P0② rank_audit_data.json（只读；仅作对照）")
    ap.add_argument("--out", required=True, help="输出 JSON 路径")
    args = ap.parse_args()

    cases = {}
    for path in sorted(glob.glob(os.path.join(args.sync, "cases", "*.json"))):
        c = load_json(path)
        cases[str(c["qid"])] = c

    metrics = load_json(os.path.join(args.sync, "metrics.json"))
    attr = load_json(args.attr)
    audit = load_json(args.audit)

    rows = [analyse_question(qid, cases[qid], args.sync)
            for qid in sorted(cases)]
    by_qid = {r["qid"]: r for r in rows}

    # ---------------- 聚合 ----------------
    folds_all = [f for r in rows for f in r.get("dedup_folds") or []]
    agg = {
        "n_questions": len(rows),
        "n_payload_found": sum(1 for r in rows if r["payload_found"]),
        "n_payload_missing": sum(1 for r in rows if not r["payload_found"]),
        "n_questions_with_dedup": sum(
            1 for r in rows if r.get("dedup_folds")),
        "n_dedup_fold_events": len(folds_all),
        "n_folds_of_model_first": sum(
            1 for f in folds_all if f["folded_is_model_first"]),
        "n_folds_where_folded_is_rank1": sum(
            1 for f in folds_all if f["folded_is_rank1_in_declared_table"]),
        "n_folds_with_unranked_survivor": sum(
            1 for f in folds_all if f["survivor_declared_rank"] is None),
        "n_folds_with_fallback_survivor": sum(
            1 for f in folds_all
            if f["survivor_rank_basis"] == "deterministic_fallback"),
        "n_folds_survivor_effective_rank_gt_folded_rank": sum(
            1 for f in folds_all
            if f["survivor_declared_rank"] is not None
            and f["folded_declared_rank"] is not None
            and f["survivor_declared_rank"] < f["folded_declared_rank"]),
        "n_questions_with_fallback_entries": sum(
            1 for r in rows if r.get("n_fallback_entries")),
        "n_fallback_entries": sum(r.get("n_fallback_entries", 0)
                                  for r in rows),
        "n_questions_with_gt1_scheduled_decide": sum(
            1 for r in rows if r.get("n_scheduled_decide_outcomes", 0) > 1),
        "unresolved_declared_ids": {
            "n_questions_with_unresolved": sum(
                1 for r in rows if r.get("unresolved_declared_ids")),
            "n_ids": sum(len(r.get("unresolved_declared_ids") or [])
                         for r in rows),
            "class_tally": dict(collections.Counter(
                c for r in rows
                for c in (r.get("unresolved_declared_class") or []))),
            "id_class_tally": dict(collections.Counter(
                c for r in rows
                for c in (r.get("unresolved_declared_class_by_id")
                          or {}).values())),
            "n_unexplained_ids": sum(
                1 for r in rows
                for c in (r.get("unresolved_declared_class_by_id")
                          or {}).values() if c == "unexplained"),
            "detail": [{"qid": r["qid"],
                        "ids": r["unresolved_declared_ids"],
                        "classes": r["unresolved_declared_class"]}
                       for r in rows if r.get("unresolved_declared_ids")],
        },
        "transfer_tally": dict(collections.Counter(
            r.get("transfer") for r in rows)),
        "microsecond_collision": {
            "total_events": sum(r.get("n_events", 0) for r in rows),
            "n_pairs": sum(r["microsecond_collisions"]["n_pairs"]
                           for r in rows if r.get("microsecond_collisions")),
            "n_questions_with_collision": sum(
                1 for r in rows if r.get("microsecond_collisions")
                and r["microsecond_collisions"]["n_pairs"] > 0),
        },
    }
    agg["fold_detail"] = folds_all
    # 紧凑化传递：折叠题的展开条目里，生效位次 ≠ 声明位次的分布
    e_rows = [e for r in rows
              for e in (r.get("entries_declared_vs_effective") or [])]
    agg["compaction_shifts"] = {
        "n_entries_in_fold_questions": len(e_rows),
        "n_effective_lt_declared": sum(
            1 for e in e_rows if e["declared_rank"] is not None
            and e["effective_rank"] is not None
            and e["effective_rank"] < e["declared_rank"]),
        "n_effective_eq_declared": sum(
            1 for e in e_rows if e["declared_rank"] is not None
            and e["effective_rank"] is not None
            and e["effective_rank"] == e["declared_rank"]),
        "n_effective_gt_declared": sum(
            1 for e in e_rows if e["declared_rank"] is not None
            and e["effective_rank"] is not None
            and e["effective_rank"] > e["declared_rank"]),
    }
    # 池装配(build)侧折叠:题数 / 折叠事件数 / 与 decide 侧折叠共现
    b_rows = [r for r in rows if r.get("build_side_merges")]
    agg["build_side_merges"] = {
        "n_questions_with_build_side_merge": len(b_rows),
        "n_build_side_merge_events": sum(len(r["build_side_merges"])
                                         for r in b_rows),
        "n_questions_with_both_sides": sum(
            1 for r in b_rows if r.get("dedup_folds")),
        "detail": [{"qid": r["qid"],
                    "merges": r["build_side_merges"]} for r in b_rows],
    }
    ps_rows = [r.get("report_projection_surface") or {} for r in rows]
    agg["report_projection_surface"] = {
        "n_projections": sum(p.get("n_projections", 0) for p in ps_rows),
        "n_with_dedup_notes": sum(p.get("n_with_dedup_notes", 0)
                                  for p in ps_rows),
        "n_report_rank_none_slots": sum(p.get("n_report_rank_none_slots", 0)
                                        for p in ps_rows),
    }

    # ---------------- 重点两组 ----------------
    dec = (attr.get("C1") or {}).get("hit1_v2_decomposition") or {}
    lost8 = [str(q) for q in (dec.get("lost_to_rank_gt1_qids") or [])]
    m2 = {r["qid"]: (r.get("main") or {}) for r in metrics["per_qid"]}
    strict32 = sorted(
        qid for qid, m in m2.items()
        if m.get("match_status") == "matched_strict"
        and isinstance(m.get("rank"), int) and m["rank"] > 1)

    def group(qids: list[str]) -> dict:
        missing = [q for q in qids if q not in by_qid]
        return {
            "n": len(qids),
            "n_missing_payload": len(missing),
            "n_model_first_is_first_event": sum(
                1 for q in qids if q in by_qid
                and by_qid[q].get("transfer") == "model_first_is_first_event"),
            "transfer_tally": dict(collections.Counter(
                by_qid[q].get("transfer") for q in qids if q in by_qid)),
            "n_model_first_folded": sum(
                1 for q in qids if q in by_qid
                and any(f["folded_is_model_first"]
                        for f in (by_qid[q].get("dedup_folds") or []))),
        }

    groups = {
        "lost_to_rank_gt1_8": group(lost8),
        "strict_rank_gt1": group(strict32),
        "strict_rank_gt1_qids": strict32,
    }

    # strict / hit@1 复算（口径自 metrics v2 主口径）
    recalc = {
        "hit1_v2": sum(1 for m in m2.values() if m.get("rank") == 1),
        "strict_v2": sum(1 for m in m2.values()
                         if m.get("match_status") == "matched_strict"),
    }

    # ---------------- 与 P0② 审计产物对照 ----------------
    a_agg = audit.get("aggregation") or {}
    a_fold = audit.get("fold_rank_loss_verdict") or {}
    a_micro = audit.get("microsecond_collision") or {}
    a_f1 = audit.get("focus_group_1_lost_to_rank_gt1") or []
    a_f2 = audit.get("focus_group_2_rerank_space") or {}
    a_rows = {r["qid"]: r for r in (audit.get("rows") or [])}

    compare = {
        "audit_meta_head_expected": (audit.get("meta") or {}).get(
            "repo_head_expected"),
        "closure_table_sum_298": ((a_agg.get("closure") or {})
                                  .get("sum_298")),
        "n_dedup_fold_events": {
            "probe": agg["n_dedup_fold_events"],
            "audit": a_fold.get("n_dedup_fold_events")},
        "n_dedup_fold_of_model_first": {
            "probe": agg["n_folds_of_model_first"],
            "audit": a_fold.get("n_dedup_fold_of_model_first")},
        "n_questions_with_dedup_rejections": {
            "probe": agg["n_questions_with_dedup"],
            "audit": (a_agg.get("supplementary_facts") or {})
            .get("n_questions_with_dedup_rejections")},
        "microsecond_collision": {
            "probe": agg["microsecond_collision"],
            "audit": {"total_events": a_micro.get("total_events"),
                      "n_pairs": a_micro.get("n_collision_pairs"),
                      "n_questions_with_collision": a_micro.get(
                          "n_questions_with_collision")}},
        "focus1_n": {"probe": groups["lost_to_rank_gt1_8"]["n"],
                     "audit": len(a_f1)},
        "focus1_all_first": {
            "probe": groups["lost_to_rank_gt1_8"][
                "n_model_first_is_first_event"],
            "audit": sum(1 for r in a_f1
                         if r.get("transfer") == "model_first_is_first_event")},
        "focus2_n": {"probe": groups["strict_rank_gt1"]["n"],
                     "audit": a_f2.get("n")},
        "focus2_all_first": {
            "probe": groups["strict_rank_gt1"]["n_model_first_is_first_event"],
            "audit": (a_f2.get("tally_reorder_headroom") or {}).get(
                "none(模型首位已居首)")},
        "audit_qid_set_vs_probe": {
            "audit_rows": len(a_rows), "probe_rows": len(by_qid),
            "same_set": set(a_rows) == set(by_qid)},
        "strict_v2_recalc": {"probe": recalc["strict_v2"],
                             "audit": (((audit.get("anchors") or {})
                                        .get("A2_metrics") or {})
                                       .get("strict_v2"))},
        "hit1_v2_recalc": {"probe": recalc["hit1_v2"],
                           "audit": (((audit.get("anchors") or {})
                                      .get("A2_metrics") or {})
                                     .get("hit1_v2"))},
    }

    out = {
        "probe": "tf_probe_rank_transfer.py",
        "domain_tag": "298=RHEA 通用酶学/已见题",
        "scope": ("只读独立复算：synced 一手 payload/metrics + attr JSON；"
                  "不复用 rank_audit.py；零金标零题面零模型零网络"),
        "inputs": {
            "sync": os.path.abspath(args.sync),
            "attr_sha256": sha256_file(args.attr),
            "audit_sha256": sha256_file(args.audit),
            "metrics_sha256": sha256_file(
                os.path.join(args.sync, "metrics.json")),
        },
        "aggregates": agg,
        "groups": groups,
        "recalc_from_metrics": recalc,
        "compare_with_p0_audit": compare,
        "fold_detail": folds_all,
    }
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)

    # ---------------- 控制台摘要 ----------------
    print("== T-F 位次传递核查 · 只读独立复算 ==")
    print("题数 %d(payload 命中 %d / 缺失 %d)" % (
        agg["n_questions"], agg["n_payload_found"], agg["n_payload_missing"]))
    print("fold: 题数=%d 事件数=%d 其中被折叠者=模型首位 %d / =rank1 %d" % (
        agg["n_questions_with_dedup"], agg["n_dedup_fold_events"],
        agg["n_folds_of_model_first"], agg["n_folds_where_folded_is_rank1"]))
    print("fold 幸存者: 无声明 rank %d / fallback %d / 声明位次优于被折叠者 %d" % (
        agg["n_folds_with_unranked_survivor"],
        agg["n_folds_with_fallback_survivor"],
        agg["n_folds_survivor_effective_rank_gt_folded_rank"]))
    print("fallback 候选: 题数=%d 条目数=%d" % (
        agg["n_questions_with_fallback_entries"], agg["n_fallback_entries"]))
    print("折叠题内条目位次紧凑化: %s" % json.dumps(
        agg["compaction_shifts"], ensure_ascii=False))
    print("池装配(build)侧折叠: %s" % json.dumps(
        {k: v for k, v in agg["build_side_merges"].items() if k != "detail"},
        ensure_ascii=False))
    print("报告投影面: %s" % json.dumps(
        agg["report_projection_surface"], ensure_ascii=False))
    for r in rows:
        if r.get("entries_declared_vs_effective"):
            print("  qid=%s 条目(声明→生效): %s" % (
                r["qid"][:16], [(e["logical_proposal_id"], e["declared_rank"],
                                 e["effective_rank"], e["rank_basis"])
                                for e in r["entries_declared_vs_effective"]]))
    print("多 scheduled decide 的题数 %d" % agg[
        "n_questions_with_gt1_scheduled_decide"])
    print("声明位次 ID 去向闭合: %s" % json.dumps(
        {k: v for k, v in agg["unresolved_declared_ids"].items()
         if k != "detail"}, ensure_ascii=False))
    print("transfer tally %s" % agg["transfer_tally"])
    print("微秒碰撞 %s" % agg["microsecond_collision"])
    print("组① lost_to_rank_gt1 %s" % {
        k: v for k, v in groups["lost_to_rank_gt1_8"].items()
        if k != "transfer_tally"})
    print("组② strict rank>1 %s" % {
        k: v for k, v in groups["strict_rank_gt1"].items()
        if k not in ("transfer_tally", "strict_rank_gt1_qids")})
    print("metrics 复算 hit@1=%d strict=%d" % (
        recalc["hit1_v2"], recalc["strict_v2"]))
    print("-- 与 P0② 审计产物对照 --")
    for k, v in compare.items():
        flag = ""
        if isinstance(v, dict) and "probe" in v and "audit" in v:
            flag = "MATCH" if v["probe"] == v["audit"] else "DIFF"
        print("  %-38s %s %s" % (k, flag, json.dumps(
            v, ensure_ascii=False, default=str)[:220]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
