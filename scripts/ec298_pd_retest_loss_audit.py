#!/usr/bin/env python
"""EC298 Phase D 复测丢分逐题归因(零 API、零预测重跑、零金标回灌)。

对复测两臂(``runs/ec298_pd_retest_{C0,D3}``,代码 ``eb3ba7f``)的 hit@1
未命中题做五层证据断点取证,方法与首跑归因
(``scripts/ec298_hit1_attribution.py``)同口径:

- 证据五层 raw_retrieval → task_candidate → selected →
  validated_reportable → reported 逐层独立取证,下层成立不推出上层;
- 断点标签由 ``classify_breakpoint`` 纯函数确定性指派(与首跑归因
  逐字一致的规则序),化学/模型因果推测不入标签;
- 金标只在本离线进程只读打开,任何运行侧/仓内产物不得含金标;
- 输入锚点 fail-closed:两臂 hit@1/@3/@5 与引擎 118/174/193/209 任一
  不符即停止(先写 anchor_mismatch.json),防止对错分行做归因;
- 只写 ``--out-dir``;两臂 run 根、引擎结果、金标一律只读。

与首跑归因的差异(如实登记):
- 输入是本复测批次根(顶层 ``merged/``、``runs/``,非首跑
  ``agent_batch/``、``agent_runs/``),loader 为本脚本新写,产物分派
  (decision/prediction/prediction_task/retrieval/validation/
  report_adjudication)与首跑 loader 同名同义;cardval.*/ *_draft /
  prediction_call|response 不进入证据层;
- reported 层读 ``report_adjudication.json`` 的
  ``products[reportable=true]``(report_rank 排序;与复测报告修订 v2
  同口径),cn 身份一律从 product_smiles 现算,忽略一切缓存身份。

用法(Chenyu,零 LLM)::

    cd /usrdata/EnzymeCAGE_data/workspaces/dependingv43 && \
    OMP_NUM_THREADS=1 PYTHONPATH=src .venv/bin/python \
      /tmp/ec298_pd_retest_loss_audit.py \
      --c0-root runs/ec298_pd_retest_C0 --d3-root runs/ec298_pd_retest_D3 \
      --engine-results runs/ec298_pd_retest_engine/engine_results.jsonl \
      --gold /usrdata/EnzymeCAGE_data/workspaces/ec298_gold_readonly/questions.jsonl \
      --out-dir reports/phase_d/retest/loss_audit

复算核对(同输入应逐字节一致;不重写产物)::

    …同上… --check
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from pathway_v43.domain.identity import cn_identity  # noqa: E402
from pathway_v43.exam_v2 import (  # noqa: E402
    load_gold, agent_candidates, first_hit_rank,
    engine_first_hit, _engine_rows)

SCRIPT_VERSION = "v43-ec298-pd-retest-loss-audit-1"

# 复测报告(修订 v2)正式锚点;任一不符即 fail-closed 停止
ANCHORS = {
    "n_questions": 298,
    "C0": {"hit1": 136, "hit3": 182, "hit5": 186, "n_empty": 12},
    "D3": {"hit1": 132, "hit3": 174, "hit5": 182, "n_empty": 13},
    "engine": {"hit1": 118, "hit3": 174, "hit5": 193, "hit10": 209},
    # 首位报告产物卡类型分布(复测报告 §4 修订 v2;软核对,不符只登记)
    "first_card_kind": {"C0": {"182": "recorded", "91": "novel",
                               "13": "analogy"},
                        "D3": {"182": "recorded", "86": "novel",
                               "17": "analogy"}},
}

LABELS = (
    "hit_at_1",
    "eligible_gold_not_selected",
    "selected_wrong_product",
    "validation_rejected_gold",
    "validated_but_not_reported",
    "reported_at_rank_2_to_5",
    "retrieval_absence_within_observed_scope",
    "empty_no_model_answer",
    "unknown",
)

DISPATCH_FILES = {"decision.json", "prediction.json", "prediction_task.json",
                  "retrieval.json", "validation.json",
                  "report_adjudication.json"}


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _trunc(text, limit: int = 260) -> str:
    text = " ".join(str(text or "").split())
    return text if len(text) <= limit else text[:limit] + "…[截断]"


def _b(v) -> str:
    return "unknown" if v is None else ("true" if v else "false")


# ---------------------------------------------------------------- 视图加载


def load_arm_view(root: Path) -> dict:
    """复测臂根只读视图(fail-closed;qid 集合三方一致)。"""
    for required in ("exam_inputs.jsonl", "merged/predictions.jsonl", "runs"):
        if not (root / required).exists():
            raise SystemExit(f"臂根缺核心输入: {root / required}")
    questions = [json.loads(l) for l in
                 (root / "exam_inputs.jsonl").read_text(encoding="utf-8")
                 .splitlines() if l.strip()]
    merged = {}
    for l in (root / "merged/predictions.jsonl").read_text(
            encoding="utf-8").splitlines():
        if l.strip():
            row = json.loads(l)
            merged[row["route_id"]] = row
    whitelist = {q["qid"] for q in questions}
    if len(whitelist) != len(questions):
        raise SystemExit("exam_inputs qid 重复")
    if set(merged) != whitelist:
        raise SystemExit("merged 答卷 qid 集合与白名单不一致")

    runs: dict[str, dict] = {}
    for run_dir in sorted((root / "runs").iterdir()):
        name = run_dir.name
        if not run_dir.is_dir() or "RXNG_" not in name:
            continue
        qid = "RXNG_" + name.split("RXNG_", 1)[1]
        if qid not in whitelist:
            raise SystemExit(f"run 目录 qid 不在白名单: {name}")
        art: dict = {"run_id": name,
                     "refs": {"decision": "", "prediction": "",
                              "prediction_task": "", "retrieval": "",
                              "report_adjudication": ""},
                     "validations": [], "validation_refs": []}
        for p in sorted((run_dir / "results").rglob("*.json")):
            if p.name not in DISPATCH_FILES:
                continue
            rel = str(p.relative_to(root))
            try:
                doc = json.loads(p.read_text(encoding="utf-8"))
            except Exception as exc:
                raise SystemExit(f"JSON 解析失败 {rel}: {exc}")
            payload = doc.get("payload", doc)
            role = p.name[:-5]
            if role == "validation":
                art["validations"].append(payload)
                art["validation_refs"].append(rel)
                continue
            if role == "prediction" and role in art:
                raise SystemExit(f"run 内多个 prediction.json: {name}")
            art[role] = payload
            art["refs"][role] = rel
        runs[qid] = art
    if set(runs) != whitelist:
        raise SystemExit("runs 目录 qid 集合与白名单不一致")
    workers: dict[str, dict] = {}
    wdir = root / "workers"
    if wdir.is_dir():
        for p in sorted(wdir.glob("*.status.json")):
            s = json.loads(p.read_text(encoding="utf-8"))
            rid = s.get("route_id") or s.get("qid")
            if rid:
                workers[rid] = s
    return {"root": root, "questions": questions, "merged": merged,
            "runs": runs, "workers": workers}


def mode_group(art: dict) -> tuple[str, str]:
    """与首跑 _mode_group 同义:按持久 decision/task 语义,不倒推。"""
    prediction = art.get("prediction") or {}
    decision = art.get("decision") or {}
    p_mode = prediction.get("mode", "")
    p_outcome = prediction.get("outcome", "")
    mode = p_mode or decision.get("prediction_mode", "") or "recorded_bypass"
    if mode == "recorded_bypass":
        return "recorded_direct", decision.get("outcome") or "commit_recorded"
    outcome = p_outcome or decision.get("outcome", "")
    if mode == "analogy_edit":
        sub = {"abstained": "analogy_abstained",
               "rejected": "analogy_rejected",
               "proposed": "analogy_proposed"}.get(outcome, outcome)
        return "analogy_edit", sub
    if mode == "rank_candidates":
        return "rank_candidates", "selected"
    if mode == "novel_proposal":
        return "novel_proposal", "proposed"
    return mode, outcome


# ---------------------------------------------------------------- 断点分类
# 规则序与首跑 classify_breakpoint 逐字一致(仅增 empty_no_model_answer
# 显式标签:首跑把无响应/弃答并入 unknown 的 residual 机制,本表单列)。


def classify_breakpoint(f: dict) -> dict:
    rank = f["agent_rank"]
    if rank is not None:
        return {"label": "reported_at_rank_2_to_5",
                "mechanism": f"formal_first_hit_at_rank_{rank}",
                "confidence": "deterministic_breakpoint"}
    if f["analogy_rejected"] and f["atomtool_target_ok"] is True \
            and f["target_whole_gold"]:
        return {"label": "validation_rejected_gold",
                "mechanism": "analogy_declared_gold_target_rejected_at_edit_gate",
                "confidence": "deterministic_breakpoint",
                "uncertainty": "声明目标运行时确定性解析且身份匹配金标;"
                               "编辑列表被确定性拒因拒绝,编辑从未执行"}
    if f["validation_gold_rejected"]:
        return {"label": "validation_rejected_gold",
                "mechanism": "gold_product_rejected_by_deterministic_validation",
                "confidence": "deterministic_breakpoint"}
    if f["validation_gold_accepted"] and not f["reported_gold"]:
        return {"label": "validated_but_not_reported",
                "mechanism": "validated_product_absent_from_final_adjudication",
                "confidence": "deterministic_breakpoint"}
    gold_cards = f["task_gold_cards"]
    if gold_cards:
        if any(c["eligible"] for c in gold_cards):
            pos = sorted(c["order_position"] for c in gold_cards
                         if c["eligible"] and c["order_position"])
            return {"label": "eligible_gold_not_selected",
                    "mechanism": "model_ranked_gold_card_lower"
                    + (f"_position_{'-'.join(map(str, pos))}" if pos
                       else "_position_not_in_order"),
                    "confidence": "deterministic_breakpoint"}
        return {"label": "unknown",
                "mechanism": "task_candidate_gold_card_ineligible",
                "confidence": "undetermined",
                "uncertainty": "任务候选含金标卡但未过当时可用资格"
                               "(condition_fit=conflict)"}
    if not f["any_gold_observed"]:
        return {"label": "retrieval_absence_within_observed_scope",
                "mechanism": "no_gold_in_any_observed_layer",
                "confidence": "deterministic_breakpoint",
                "uncertainty": "仅限已封存检索卡范围;缺完整候选池,不得称"
                               "「数据库没有正确反应」"}
    if f["selected_exists"] and not f["selected_gold"]:
        return {"label": "selected_wrong_product",
                "mechanism": f["mode"] + "_selected_product_not_gold",
                "confidence": "deterministic_breakpoint",
                "uncertainty": "选中记录/卡产物不含金标;金标仅见于其他层"
                               "(未进入任务/未被选中),是否可用未证实"}
    if f["mode"] in ("novel_proposal", "analogy_edit"):
        return {"label": "empty_no_model_answer" if f["empty_answer"]
                else "unknown",
                "mechanism": f"{f['mode']}_"
                + (f["prediction_outcome"] or "no_model_response"),
                "confidence": "deterministic_breakpoint"
                if f["empty_answer"] else "undetermined",
                "uncertainty": "" if f["empty_answer"]
                else "金标仅见于原始检索层,agent 产物链上从未出现;"
                     "候选形成/生成环节离线不可进一步判定"}
    return {"label": "unknown", "mechanism": f["residual_mechanism"],
            "confidence": "undetermined",
            "uncertainty": "未归入上述任一确定性断点"}


# ---------------------------------------------------------------- 逐题取证


def audit_question(qid: str, art: dict, merged_row: dict, gold_entry: dict,
                   agent_rank, engine_rank) -> dict:
    gold_ids = gold_entry["gold_ids"]
    cands = agent_candidates(merged_row)
    mode, sub = mode_group(art)
    prediction = art.get("prediction") or {}
    decision = art.get("decision") or {}
    parsed = prediction.get("parsed") or {}
    task = art.get("prediction_task") or {}
    checks = prediction.get("atomtool_checks") or {}
    order = parsed.get("order") or []
    selected = parsed.get("selected_evidence_id") \
        or decision.get("accepted_evidence_id") or ""

    # L1 raw_retrieval
    raw_refs = []
    for ev in (art.get("retrieval") or {}).get("evidences", []):
        for p in ev.get("products", []):
            if cn_identity(p.get("product_smiles", "")) in gold_ids:
                raw_refs.append(f"{ev.get('evidence_id', '?')}"
                                f"({ev.get('kind', '?')},"
                                f"r{ev.get('retrieval_rank', '?')})")
                break
    raw_gold = bool(raw_refs)

    # L2 task_candidate(可选择语义与首跑一致)
    task_cards, task_gold_recorded = [], False
    for c in task.get("candidates", []):
        hits = [p.get("position") for p in c.get("products", [])
                if cn_identity(p.get("product_smiles", "")) in gold_ids]
        if not hits:
            continue
        selectable = mode == "rank_candidates" \
            or c.get("kind") == "recorded_reaction"
        if c.get("kind") == "recorded_reaction":
            task_gold_recorded = True
        task_cards.append({
            "evidence_id": c.get("evidence_id", "?"),
            "kind": c.get("kind", "?"), "selectable": selectable,
            "eligible": c.get("condition_fit") != "conflict",
            "condition_fit": c.get("condition_fit", ""),
            "order_position": order.index(c.get("evidence_id")) + 1
            if c.get("evidence_id") in order else None,
            "n_gold_positions": len(hits),
        })
    task_gold = bool(task_cards)
    sel_cards = [c for c in task_cards if c["selectable"]]

    # L3 selected
    sel_products = []
    if selected:
        card = next((c for c in task.get("candidates", [])
                     if c.get("evidence_id") == selected), None)
        if card is None:
            ev = next((e for e in (art.get("retrieval") or {})
                       .get("evidences", [])
                       if e.get("evidence_id") == selected), None)
            card = ev
        sel_products = (card or {}).get("products", [])
    selected_gold = selected and any(
        cn_identity(p.get("product_smiles", "")) in gold_ids
        for p in sel_products)

    # L4 validated_reportable
    val_acc = val_rej = False
    val_refs, val_reasons = [], []
    for i, v0 in enumerate(art["validations"]):
        for v in v0.get("verdicts", []):
            ident = cn_identity(v.get("product_smiles", ""))
            if not ident or ident not in gold_ids:
                if not v.get("accepted"):
                    val_reasons.extend(v.get("reasons", []))
                continue
            val_refs.append(f"validation[{i}]:{v0.get('evidence_id', '?')}"
                            f":pos{v.get('position', '?')}")
            if v.get("accepted"):
                val_acc = True
            else:
                val_rej = True
                val_reasons.extend(v.get("reasons", []))

    # L5 reported(复测修订 v2 口径:products[reportable=true])
    rep_products = sorted(
        [p for p in ((art.get("report_adjudication") or {})
                     .get("products", [])) if p.get("reportable")],
        key=lambda p: (p.get("report_rank") is None,
                       p.get("report_rank") or 0))
    reported_gold = False
    gold_report_rank = None
    for p in rep_products:
        if cn_identity(p.get("product_smiles", "")) in gold_ids:
            reported_gold = True
            if p.get("report_rank") is not None:
                gold_report_rank = min(gold_report_rank or 10**9,
                                       p["report_rank"])
    first_prod = rep_products[0] if rep_products else {}

    # 类比目标(协议 v2 的 atomtool_checks 无 ledger target_smiles 键;
    # 与首跑 phase_c_target_recompute 同法,用运行时解析器重解析声明目标)
    is_analogy = mode == "analogy_edit"
    analogy_rejected = is_analogy and (
        prediction.get("outcome") == "rejected"
        or decision.get("outcome") == "rejected")
    tgt = (checks.get("target_molecode") or {})
    target_smiles = tgt.get("target_smiles", "") or ""
    target_ok = tgt.get("ok") if tgt else None
    if not target_smiles and is_analogy and parsed.get("target_molecode"):
        try:
            from pathway_v43.services.atom_tool import molecode_to_smiles
            target_smiles = molecode_to_smiles(parsed["target_molecode"]) \
                or ""
            target_ok = bool(target_smiles)
        except Exception:
            target_smiles, target_ok = "", False
    target_whole = bool(target_smiles) and \
        cn_identity(target_smiles) in gold_ids
    target_comp = bool(target_smiles) and any(
        cn_identity(pt) in gold_ids
        for pt in target_smiles.split(".") if cn_identity(pt))

    empty_answer = not cands
    facts = {
        "agent_rank": agent_rank,
        "analogy_rejected": analogy_rejected,
        "atomtool_target_ok": target_ok if is_analogy else None,
        "target_whole_gold": target_whole,
        "validation_gold_rejected": val_rej,
        "validation_gold_accepted": val_acc,
        "reported_gold": reported_gold,
        "task_gold_cards": sel_cards,
        "selected_exists": bool(selected) and not is_analogy,
        "selected_gold": bool(selected_gold),
        "raw_retrieval_gold": raw_gold,
        "any_gold_observed": raw_gold or task_gold or bool(selected_gold)
        or val_acc or reported_gold,
        "mode": mode,
        "empty_answer": empty_answer,
        "prediction_outcome": prediction.get("outcome", ""),
        "residual_mechanism": "unattributed",
    }
    bp = classify_breakpoint(facts)
    comp_rank = first_hit_rank(cands, gold_ids, component_mode=True)

    refs = art["refs"]
    return {
        "qid": qid,
        "n_gold_products": gold_entry["n_gold_products"],
        "category": gold_entry.get("category") or "",
        "mode": mode, "subgroup": sub,
        "prediction_outcome": prediction.get("outcome", "")
        or decision.get("outcome", ""),
        "n_reported": len(cands),
        "answer_kind": "empty" if empty_answer else "full",
        "agent_rank": agent_rank if agent_rank is not None else "",
        "component_rank": comp_rank if comp_rank is not None else "",
        "engine_rank": engine_rank if engine_rank is not None else "",
        "engine_bucket": ("e1" if engine_rank == 1 else
                          "e2_5" if engine_rank and engine_rank <= 5 else
                          "e6_10" if engine_rank else "e_none"),
        "raw_retrieval_gold": _b(raw_gold),
        "task_candidate_gold": _b(task_gold),
        "task_gold_recorded": _b(task_gold_recorded),
        "gold_card_eligible": _b(sel_cards[0]["eligible"])
        if sel_cards else ("no_selectable_gold_card" if task_cards
                           else "not_applicable"),
        "gold_card_order_position": sel_cards[0]["order_position"]
        if sel_cards and sel_cards[0]["order_position"]
        else ("not_in_order" if sel_cards else "not_applicable"),
        "selected_gold": _b(selected_gold) if selected else "not_applicable",
        "validated_reportable_gold": _b(val_acc),
        "reported_gold": _b(reported_gold),
        "gold_report_rank": gold_report_rank if gold_report_rank
        is not None else "",
        "first_product": _trunc(first_prod.get("product_smiles", ""), 110),
        "first_card_kind": first_prod.get("card_kind", ""),
        "breakpoint_label": bp["label"],
        "observed_mechanism": bp["mechanism"],
        "cause_confidence": bp.get("confidence", "deterministic_breakpoint"),
        "uncertainty_reason": _trunc(bp.get("uncertainty", "")),
        "raw_retrieval_gold_refs": ";".join(raw_refs[:4]),
        "task_candidate_gold_refs": ";".join(
            f"{c['evidence_id']}({c['kind']},cf={c['condition_fit'] or '?'})"
            for c in task_cards[:4]),
        "validation_reject_reasons": _trunc(";".join(
            str(r) for r in val_reasons)
            or ";".join(f"{k}:{';'.join(c.get('reasons', []))}"
                        for k, c in checks.items()
                        if isinstance(c, dict) and c.get("ok") is False)
            or str(prediction.get("fail_reason") or ""), 240),
        "selected_evidence_id": selected or "",
        "model_order": ";".join(order),
        "analogy_target_ok": _b(target_ok) if is_analogy
        else "not_applicable",
        "analogy_target_whole_gold": _b(target_whole)
        if analogy_rejected else "not_applicable",
        "analogy_target_component_gold": _b(target_comp)
        if analogy_rejected else "not_applicable",
        "evidence_refs": ";".join(
            r for r in (refs["decision"], refs["prediction_task"],
                        refs["prediction"], refs["retrieval"],
                        refs["report_adjudication"]) if r),
        "validation_refs": ";".join(art["validation_refs"][:3]),
    }


# ---------------------------------------------------------------- 主流程

ALL_COLUMNS = [
    "qid", "category", "n_gold_products", "mode", "subgroup",
    "prediction_outcome", "answer_kind", "n_reported", "agent_rank",
    "component_rank", "engine_rank", "engine_bucket",
    "raw_retrieval_gold", "task_candidate_gold", "task_gold_recorded",
    "gold_card_eligible", "gold_card_order_position", "selected_gold",
    "validated_reportable_gold", "reported_gold", "gold_report_rank",
    "first_product", "first_card_kind", "breakpoint_label",
    "observed_mechanism", "cause_confidence",
]
DETAIL_EXTRA = [
    "uncertainty_reason", "raw_retrieval_gold_refs",
    "task_candidate_gold_refs", "validation_reject_reasons",
    "selected_evidence_id", "model_order", "analogy_target_ok",
    "analogy_target_whole_gold", "analogy_target_component_gold",
    "evidence_refs", "validation_refs",
]


def audit_arm(arm: str, root: Path, gold: dict, engine: dict) -> dict:
    view = load_arm_view(root)
    rows, hits, empty = [], Counter(), 0
    for q in view["questions"]:
        qid = q["qid"]
        merged_row = view["merged"][qid]
        cands = agent_candidates(merged_row)
        if not cands:
            empty += 1
        g = gold[qid]
        rank = first_hit_rank(cands, g["gold_ids"])
        for k in (1, 3, 5):
            hits[f"hit{k}"] += 1 if rank is not None and rank <= k else 0
        eng = engine.get(qid)
        engine_rank = engine_first_hit(eng, g["gold_ids"])["rank"]
        rows.append(audit_question(qid, view["runs"][qid], merged_row, g,
                                   rank, engine_rank))
    checks = {"hit1": (hits["hit1"], ANCHORS[arm]["hit1"]),
              "hit3": (hits["hit3"], ANCHORS[arm]["hit3"]),
              "hit5": (hits["hit5"], ANCHORS[arm]["hit5"]),
              "n_empty": (empty, ANCHORS[arm]["n_empty"]),
              "n_questions": (len(rows), ANCHORS["n_questions"])}
    bad = {k: v for k, v in checks.items() if v[0] != v[1]}
    return {"arm": arm, "rows": rows, "checks": checks,
            "anchor_ok": not bad, "anchor_bad": bad, "view": view}


def summarize(arm_result: dict) -> dict:
    rows = arm_result["rows"]
    miss = [r for r in rows if r["agent_rank"] != 1]
    labels = Counter(r["breakpoint_label"] for r in rows)
    by_mode = {}
    for r in rows:
        key = r["mode"]
        d = by_mode.setdefault(key, {"n": 0, "hit1": 0})
        d["n"] += 1
        d["hit1"] += 1 if r["agent_rank"] == 1 else 0
    miss_label_mode = Counter((r["breakpoint_label"], r["mode"])
                              for r in miss)
    miss_engine = Counter((r["breakpoint_label"], r["engine_bucket"])
                          for r in miss)
    comp_flip = [r["qid"] for r in miss if r["component_rank"] == 1]
    return {
        "arm": arm_result["arm"],
        "labels_all": dict(labels),
        "labels_miss_only": dict(Counter(
            r["breakpoint_label"] for r in miss)),
        "hit_rate_by_mode": by_mode,
        "miss_label_x_mode": {f"{l}|{m}": n
                              for (l, m), n in sorted(miss_label_mode.items())},
        "miss_label_x_engine_bucket": {f"{l}|{e}": n for (l, e), n in
                                       sorted(miss_engine.items())},
        "miss_by_category": dict(Counter(r["category"] for r in miss)),
        "all_by_category": dict(Counter(r["category"] for r in rows)),
        "miss_multi_gold_products": dict(Counter(
            r["n_gold_products"] for r in miss)),
        "all_multi_gold_products": dict(Counter(
            r["n_gold_products"] for r in rows)),
        "component_flip_hit1_qids": comp_flip,
        "engine_miss_top10": sum(1 for r in miss if r["engine_rank"] == ""),
        "first_card_kind_all": dict(Counter(
            r["first_card_kind"] or "empty" for r in rows)),
    }


def render_outputs(results: list[dict], engine_ranks: dict,
                   gold: dict, inputs_sha: dict) -> dict:
    outs: dict[str, bytes] = {}

    def tsv(columns, data):
        import io
        buf = io.StringIO()
        buf.write("\t".join(columns) + "\n")
        for r in data:
            buf.write("\t".join(
                "" if r.get(c) is None else str(r.get(c, ""))
                for c in columns) + "\n")
        return buf.getvalue().encode("utf-8")

    for res in results:
        arm = res["arm"].lower()
        outs[f"loss_audit_298_{arm}.tsv"] = tsv(
            ALL_COLUMNS, res["rows"])
        outs[f"miss_hit1_detail_{arm}.tsv"] = tsv(
            ALL_COLUMNS + DETAIL_EXTRA,
            [r for r in res["rows"] if r["agent_rank"] != 1])
    # 两臂合并逐题速览(可读性视图;列取自两份 298 行表的等值联结)
    by_qid = {res["arm"]: {r["qid"]: r for r in res["rows"]}
              for res in results}
    combined = []
    for qid in by_qid["C0"]:
        a, b = by_qid["C0"][qid], by_qid["D3"][qid]
        combined.append({
            "qid": qid, "category": a["category"],
            "n_gold_products": a["n_gold_products"],
            "C0_mode": a["mode"], "C0_answer_kind": a["answer_kind"],
            "C0_rank": a["agent_rank"], "C0_label": a["breakpoint_label"],
            "D3_rank": b["agent_rank"], "D3_label": b["breakpoint_label"],
            "engine_rank": a["engine_rank"],
            "engine_bucket": a["engine_bucket"],
            "C0_component_rank": a["component_rank"],
            "C0_first_product": a["first_product"],
        })
    outs["paired_298_loss_labels.tsv"] = tsv(list(combined[0].keys()),
                                             combined)
    summary = {
        "script_version": SCRIPT_VERSION,
        "zero_api": True,
        "anchors": ANCHORS,
        "inputs_sha256": inputs_sha,
        "engine_summary": {
            "hit1": sum(1 for v in engine_ranks.values()
                        if v == 1),
            "hit3": sum(1 for v in engine_ranks.values()
                        if v and v <= 3),
            "hit5": sum(1 for v in engine_ranks.values()
                        if v and v <= 5),
            "hit10": sum(1 for v in engine_ranks.values() if v),
        },
        "arms": [summarize(res) for res in results],
    }
    outs["summary.json"] = (json.dumps(summary, ensure_ascii=False,
                                       indent=2, sort_keys=True)
                            + "\n").encode("utf-8")
    outs["input_sha256.json"] = (json.dumps(
        {"script_version": SCRIPT_VERSION, "zero_api": True,
         "gold_n_questions": len(gold), **inputs_sha},
        ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    return outs


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--c0-root", required=True)
    ap.add_argument("--d3-root", required=True)
    ap.add_argument("--engine-results", required=True)
    ap.add_argument("--gold", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--check", action="store_true",
                    help="复算并与既有输出逐字节比对,不写盘")
    args = ap.parse_args(argv)

    gold = load_gold(args.gold)
    if len(gold) != ANCHORS["n_questions"]:
        raise SystemExit(f"金标题数 {len(gold)} ≠ 298")
    engine = _engine_rows(args.engine_results)
    if set(engine) != set(gold):
        raise SystemExit("引擎结果 qid 集合与金标不一致")
    engine_ranks = {qid: engine_first_hit(engine[qid], g["gold_ids"])["rank"]
                    for qid, g in gold.items()}
    eng_hits = {
        "hit1": sum(1 for v in engine_ranks.values() if v == 1),
        "hit3": sum(1 for v in engine_ranks.values() if v and v <= 3),
        "hit5": sum(1 for v in engine_ranks.values() if v and v <= 5),
        "hit10": sum(1 for v in engine_ranks.values() if v),
    }
    if eng_hits != ANCHORS["engine"]:
        raise SystemExit(f"引擎锚点不符 {eng_hits} ≠ {ANCHORS['engine']}")

    inputs_sha = {
        "c0_root": str(args.c0_root),
        "d3_root": str(args.d3_root),
        "engine_results": _sha256(Path(args.engine_results)),
        "gold_questions": _sha256(Path(args.gold)),
    }
    results = [audit_arm("C0", Path(args.c0_root), gold, engine),
               audit_arm("D3", Path(args.d3_root), gold, engine)]
    for res in results:
        if not res["anchor_ok"]:
            (Path(args.out_dir)).mkdir(parents=True, exist_ok=True)
            (Path(args.out_dir) / "anchor_mismatch.json").write_text(
                json.dumps(res["anchor_bad"], ensure_ascii=False, indent=2),
                encoding="utf-8")
            print(json.dumps({"anchor_mismatch": res["arm"],
                              "bad": res["anchor_bad"]},
                             ensure_ascii=False), file=sys.stderr)
            return 1

    outs = render_outputs(results, engine_ranks, gold, inputs_sha)
    out_dir = Path(args.out_dir)
    if args.check:
        bad = [f"{n}: MISSING" if not (out_dir / n).is_file()
               else f"{n}: BYTES DIFFER"
               for n, data in sorted(outs.items())
               if not (out_dir / n).is_file()
               or (out_dir / n).read_bytes() != data]
        print(json.dumps({"check": "FAIL" if bad else "OK", "diffs": bad},
                         ensure_ascii=False))
        return 1 if bad else 0
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, data in outs.items():
        (out_dir / name).write_bytes(data)
    man = "\n".join(f"{_sha256(out_dir / n)}  {n}"
                    for n in sorted(outs)) + "\n"
    (out_dir / "output_manifest.sha256").write_text(man, encoding="utf-8")
    print(json.dumps({
        "script_version": SCRIPT_VERSION,
        "n_files": len(outs),
        "labels": {res["arm"]: dict(Counter(
            r["breakpoint_label"] for r in res["rows"]
            if r["agent_rank"] != 1)) for res in results},
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
