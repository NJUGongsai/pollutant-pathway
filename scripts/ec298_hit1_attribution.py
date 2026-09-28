#!/usr/bin/env python
"""EC298 首跑 hit@1 失分逐题归因(零 API、零预测重跑、零金标回灌)。

阶段任务书:docs/TASK_V43_EC298_HIT1_ATTRIBUTION.md。对封存首跑
(``runs/ec298_v43r1``)中 agent hit@1 未命中的 182 题(正式口径
``v43-ec298-scorer-2``:116/128/130)做逐题离线审计:

- 复用 Phase A 只读 manifest 校验(``scripts/ec298_phase_a.py``)与
  scorer v2 身份函数(``pathway_v43.exam_v2`` / ``cn_identity``);
- 证据五层(raw_retrieval → task_candidate → selected →
  validated_reportable → reported)逐层独立取证,下层成立不推出上层;
- 断点标签按任务书 §2.1 证据条件确定性指派(规则见
  ``classify_breakpoint``,纯函数可单测);化学/模型因果推测单列
  ``causal_hypothesis``,不混入断点事实;
- 23 条被拒类比目标的金标匹配按四种口径独立重算(8/23 vs 0/23 分歧
  裁决,逐题行可回查,不预先采信任一数字);
- 输出只写 ``--out-dir``;不覆盖 Phase A/B/C、首跑或金标文件。

用法(全部路径显式传入;清单校验双向 fail-closed)::

    python scripts/ec298_hit1_attribution.py \
        --run-dir <sealed>/dependingv43_dev/runs/ec298_v43r1 \
        --gold <sealed>/ec298_gold_readonly/questions.jsonl \
        --v1-scoring <sealed>/dependingv43_dev/runs/ec298_v43r1/scoring/per_question_scoring.json \
        --v41-baseline <sealed>/dependingv4_v41/runs/exam298_agent/per_question_scoring.jsonl \
        --asset-library assets/v3_reactions/library/library_full.jsonl \
        --phase-a-dir reports/ec298/phase_a_v2 \
        --out-dir reports/ec298/hit1_attribution_v1

复算核对(同输入同仓库状态应逐字节一致)::

    python scripts/ec298_hit1_attribution.py … --out-dir <同目录> --check
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from pathway_v43.domain.identity import cn_identity  # noqa: E402
from pathway_v43.exam_v2 import (  # noqa: E402
    ScorerV2Error, agent_candidates, first_hit_rank, load_gold, write_tsv)
from pathway_v43.phase_a_attribution import (  # noqa: E402
    load_sealed_run_view)

SCRIPT_VERSION = "v43-ec298-hit1-attribution-1"

# ---------------------------------------------------------------- 正式锚点
ANCHORS = {
    "n_questions": 298,
    "agent_hit1": 116,
    "n_miss_hit1": 182,
    "group_recorded_direct": 48,
    "group_rank_candidates": 43,
    "group_analogy_edit": 66,
    "group_novel_proposal": 25,
    "n_rank_2_to_5": 14,
}

LABELS = (
    "eligible_gold_not_selected",
    "selected_wrong_product",
    "validation_rejected_gold",
    "validated_but_not_reported",
    "reported_at_rank_2_to_5",
    "retrieval_absence_within_observed_scope",
    "unknown",
)

# 布尔列取值:不许用空串同时表示"未查/无/不适用"
BOOL_NA = ("true", "false", "unknown", "not_applicable")

MISS_COLUMNS = [
    # 身份/评分
    "qid", "input_index", "run_id", "path_id",
    "agent_rank_v2", "engine_rank_v2", "tier_v2",
    "n_gold_products", "n_reported", "gold_ids_digest",
    "first_candidate_smiles", "first_candidate_identity",
    "first_candidate_matches_gold",
    # 路径/结局
    "group", "subgroup", "decision_mode", "prediction_mode", "outcome",
    "selected_evidence_id", "model_order_provided", "model_order",
    "model_order_len", "gold_card_order_position",
    "decision_ref", "task_ref", "prediction_ref", "validation_ref",
    "report_ref",
    # 证据五层(各层布尔 + 引用)
    "raw_retrieval_gold", "raw_retrieval_gold_refs",
    "task_candidate_gold", "task_candidate_gold_refs",
    "task_candidate_gold_recorded",
    "selected_gold", "selected_gold_refs",
    "validated_reportable_gold", "validated_reportable_gold_refs",
    "reported_gold", "reported_gold_refs", "gold_report_rank",
    # 候选与门禁
    "gold_card_in_task", "gold_card_in_model_order",
    "gold_card_eligible", "gold_card_condition_fit",
    "gold_card_model_reason", "selected_card_gates_ok",
    "validation_reject_reasons",
    # 首位断点
    "first_proven_loss_stage", "observed_mechanism", "cause_confidence",
    "uncertainty_reason", "causal_hypothesis", "breakpoint_source_refs",
    # 评分敏感性
    "multicomponent_candidate", "any_component_hit1", "component_rank",
    "formal_hit1",
]

# 类比专项(仅 analogy_edit 行有值,其余行 not_applicable)
ANALOGY_COLUMNS = [
    "analogy_outcome", "donor_mapping_status", "donor_alignment_strategy",
    "donor_alignment_n", "atomtool_target_ok", "target_smiles_present",
    "target_match_whole_cn", "target_match_any_component",
    "donor_product_matches_gold", "atomtool_edit_reject_reasons",
]


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _b(v: bool | None) -> str:
    """布尔 → true/false;None → unknown(禁止空串歧义)。"""
    if v is None:
        return "unknown"
    return "true" if v else "false"


def _na(v: str) -> str:
    return v if v else "not_applicable"


def _trunc(text, limit: int = 300) -> str:
    text = " ".join(str(text or "").split())
    return text if len(text) <= limit else text[:limit] + "…[截断]"


def _digest_identities(identities: set[str]) -> str:
    return hashlib.sha256(
        ";".join(sorted(identities)).encode("utf-8")).hexdigest()[:12]


# ---------------------------------------------------------------- 断点分类
# 纯函数:输入为逐题事实字典,输出断点;规则顺序即优先级,一题至多一个
# 主断点。事实键(全部由封存产物取证,见 audit_question):
#   agent_rank            正式 v2 首命中位次(None/2..5;本表恒 ≠1)
#   analogy_rejected      analogy_edit 且 outcome=rejected
#   atomtool_target_ok    target MoleCode 运行时解析 ok(bool/None)
#   target_whole_gold     声明目标整分子 cn 身份 ∈ 金标(bool)
#   validation_gold_rejected / validation_gold_reject_reasons
#   validation_gold_accepted
#   reported_gold / reported_ranks
#   task_gold_cards       [{eligible, condition_fit, order_position}]
#   selected_exists / selected_gold
#   raw_retrieval_gold / any_gold_observed


def classify_breakpoint(f: dict) -> dict:
    rank = f["agent_rank"]
    if rank is not None:
        return {
            "label": "reported_at_rank_2_to_5",
            "mechanism": f"formal_first_hit_at_rank_{rank}",
            "confidence": "deterministic_breakpoint",
            "uncertainty": "",
        }
    if f["analogy_rejected"] and f["atomtool_target_ok"] is True \
            and f["target_whole_gold"]:
        return {
            "label": "validation_rejected_gold",
            "mechanism": "analogy_declared_gold_target_rejected_at_edit_gate",
            "confidence": "deterministic_breakpoint",
            "uncertainty": "声明目标经运行时确定性解析且身份匹配金标;编辑"
                           "列表被 AtomTool 确定性拒因拒绝,编辑从未执行,"
                           "「执行后仍等于声明目标」未获证明",
        }
    if f["validation_gold_rejected"]:
        return {
            "label": "validation_rejected_gold",
            "mechanism": "gold_product_rejected_by_deterministic_validation",
            "confidence": "deterministic_breakpoint",
            "uncertainty": "",
        }
    if f["validation_gold_accepted"] and not f["reported_gold"]:
        return {
            "label": "validated_but_not_reported",
            "mechanism": "validated_product_absent_from_final_adjudication",
            "confidence": "deterministic_breakpoint",
            "uncertainty": "",
        }
    gold_cards = f["task_gold_cards"]
    if gold_cards:
        if any(c["eligible"] for c in gold_cards):
            pos = sorted(c["order_position"] for c in gold_cards
                         if c["eligible"] and c["order_position"])
            return {
                "label": "eligible_gold_not_selected",
                "mechanism": "model_ranked_gold_card_lower"
                + (f"_position_{'-'.join(map(str, pos))}" if pos
                   else "_position_not_in_order"),
                "confidence": "deterministic_breakpoint",
                "uncertainty": "",
            }
        return {
            "label": "unknown",
            "mechanism": "task_candidate_gold_card_ineligible",
            "confidence": "undetermined",
            "uncertainty": "任务候选含金标卡但未过当时可用资格"
                           "(condition_fit=conflict);不可标"
                           "eligible_gold_not_selected",
        }
    if not f["any_gold_observed"]:
        return {
            "label": "retrieval_absence_within_observed_scope",
            "mechanism": "no_gold_in_any_observed_layer",
            "confidence": "deterministic_breakpoint",
            "uncertainty": "仅限已封存检索卡范围;缺完整候选池,不得称"
                           "「数据库没有正确反应」。选中记录/卡产物亦不含"
                           "金标,但那是范围缺金的伴生结果,不是可选错。",
        }
    if f["selected_exists"] and not f["selected_gold"]:
        return {
            "label": "selected_wrong_product",
            "mechanism": f["mode"] + "_selected_product_not_gold",
            "confidence": "deterministic_breakpoint",
            "uncertainty": "选中记录/卡产物不含金标;金标仅见于原始检索层"
                           "其他卡(未进入任务/未被选中),是否可用未证实",
        }
    return {
        "label": "unknown",
        "mechanism": f["residual_mechanism"],
        "confidence": "undetermined",
        "uncertainty": "金标仅见于原始检索层,agent 产物链上从未出现;"
                       "断点发生在候选形成/生成阶段,具体环节不可离线判定",
    }


# ---------------------------------------------------------------- 逐题取证


def _match_refs(products: list[dict], gold_ids: set[str],
                prefix: str = "") -> list[str]:
    """返回含金标产物的条目引用标识(prefix:pos)。"""
    refs = []
    for p in products:
        ident = cn_identity(p.get("product_smiles", ""))
        if ident and ident in gold_ids:
            refs.append(f"{prefix}:{p.get('position', '?')}" if prefix
                        else str(p.get("position", "?")))
    return refs


def audit_question(qid: str, art, gold_entry: dict, score_row: dict,
                   view, run_root: Path, audits: list[dict],
                   merged_sha: str = "") -> tuple[dict, dict]:
    """逐题事实取证 + 断点分类。返回 (hit1_misses 行, evidence_trace 行)。"""
    from pathway_v43.exam_v2 import agent_candidates as _cands

    gold_ids = gold_entry["gold_ids"]
    merged_row = view.merged[qid]
    cands = _cands(merged_row)
    first = cands[0] if cands else ""
    first_ident = cn_identity(first) if first else None

    decision = art.decision or {}
    prediction = art.prediction or {}
    parsed = prediction.get("parsed") or {}
    task = art.prediction_task or {}
    mode, sub = _mode_group_pub(art)
    checks = prediction.get("atomtool_checks") or {}

    # 路径一致性(跨父/串线防护):已知 path_id 集合,裁决产物必须同链
    known_paths = {decision.get("path_id"), prediction.get("path_id"),
                   task.get("path_id")} - {None, ""}
    bad_adj = [a for a in art.adjudications
               if a.get("path_id") and a.get("path_id") not in known_paths]
    for a in bad_adj:
        audits.append({
            "qid": qid, "gap_type": "path_id_mismatch",
            "detail": f"adjudication path_id={a.get('path_id')} 不在已知"
                      f"路径集合 {sorted(known_paths)};其产物不计入本题主"
                      f"断点取证",
            "resolution": "excluded_from_layers",
        })
    adjs = [a for a in art.adjudications if a not in bad_adj]

    # 五层
    raw_refs, raw_kinds = [], []
    for ev in (art.retrieval or {}).get("evidences", []):
        if _match_refs(ev.get("products", []), gold_ids):
            raw_refs.append(f"{ev.get('evidence_id', '?')}"
                            f"({ev.get('kind', '?')},r{ev.get('retrieval_rank', '?')})")
            raw_kinds.append(ev.get("kind", "?"))
    raw_gold = bool(raw_refs)

    task_gold_cards = []
    task_gold_recorded = False
    order = parsed.get("order") or []
    selected = parsed.get("selected_evidence_id") \
        or decision.get("accepted_evidence_id") or ""
    for c in task.get("candidates", []):
        refs = _match_refs(c.get("products", []), gold_ids,
                           prefix=c.get("evidence_id", "?"))
        if not refs:
            continue
        # 可选择语义:rank 任务的候选卡(任一 kind)都是模型可选集
        # (§2.1「候选卡含金标且满足当时可用资格」);analogy 任务的
        # 供体/规则卡是类比源,不是答案候选,不进入 eligible 分支。
        selectable = mode == "rank_candidates"
        if c.get("kind") == "recorded_reaction":
            task_gold_recorded = True
            selectable = True
        task_gold_cards.append({
            "evidence_id": c.get("evidence_id", "?"), "kind": c.get("kind"),
            "selectable": selectable,
            "eligible": c.get("condition_fit") != "conflict",
            "condition_fit": c.get("condition_fit", ""),
            "order_position": order.index(c.get("evidence_id")) + 1
            if c.get("evidence_id") in order else None,
            "refs": refs,
        })
    task_gold = bool(task_gold_cards)

    sel_card = next((c for c in task.get("candidates", [])
                     if c.get("evidence_id") == selected), None)
    if sel_card is None:
        sel_card = next((e for e in (art.retrieval or {}).get("evidences", [])
                         if e.get("evidence_id") == selected), None)
    sel_products = sel_card.get("products", []) if sel_card else []
    selected_gold = bool(_match_refs(sel_products, gold_ids,
                                     prefix=selected))

    val_gold_rej, val_gold_acc, val_reasons = False, False, []
    val_refs = []
    for i, v0 in enumerate(art.validations):
        for v in v0.get("verdicts", []):
            ident = cn_identity(v.get("product_smiles", ""))
            if not ident or ident not in gold_ids:
                if not v.get("accepted"):
                    val_reasons.extend(v.get("reasons", []))
                continue
            val_refs.append(f"validation[{i}]:{v0.get('evidence_id', '?')}"
                            f":pos{v.get('position', '?')}")
            if v.get("accepted"):
                val_gold_acc = True
            else:
                val_gold_rej = True
                val_reasons.extend(v.get("reasons", []))
    val_gold = val_gold_acc  # validated_reportable_gold = 验证接受且匹配

    rep_refs, rep_ranks = [], []
    for a in adjs:
        for e in a.get("entries", []):
            ident = cn_identity(e.get("product_smiles", ""))
            if ident and ident in gold_ids:
                rep_refs.append(f"{a.get('evidence_id', '?')}"
                                f":{e.get('evidence_id', '?')}"
                                f":rank{e.get('report_rank', '?')}")
                if e.get("report_rank") is not None:
                    rep_ranks.append(e["report_rank"])
    reported_gold = bool(rep_refs)

    # 类比专项
    is_analogy = mode == "analogy_edit"
    analogy_rejected = is_analogy and \
        (prediction.get("outcome") == "rejected"
         or decision.get("outcome") == "rejected")
    tgt = (checks.get("target_molecode") or {})
    target_smiles = tgt.get("target_smiles", "") or ""
    target_ok = tgt.get("ok") if tgt else None
    target_whole = bool(target_smiles) and cn_identity(target_smiles) in gold_ids
    target_comp = bool(target_smiles) and any(
        (cn_identity(pt) in gold_ids)
        for pt in target_smiles.split(".") if cn_identity(pt))
    donor_card = next((c for c in task.get("candidates", [])
                       if c.get("kind") == "analog_reaction"), None) \
        if is_analogy else None
    donor_align = ((task.get("donor") or {}).get("donor") or {}) \
        .get("alignment") or {}

    gold_card_reason = ""
    if task_gold_cards:
        reasons = parsed.get("reasons") or {}
        gold_card_reason = _trunc(
            reasons.get(task_gold_cards[0]["evidence_id"], ""), 220)

    comp_rank = first_hit_rank(cands, gold_ids, component_mode=True)
    any_comp_hit1 = comp_rank == 1

    facts = {
        "agent_rank": score_row["agent_rank"],
        "analogy_rejected": analogy_rejected,
        "atomtool_target_ok": target_ok if is_analogy else None,
        "target_whole_gold": target_whole,
        "validation_gold_rejected": val_gold_rej,
        "validation_gold_accepted": val_gold_acc,
        "reported_gold": reported_gold,
        "task_gold_cards": [c for c in task_gold_cards if c["selectable"]],
        # 类比的 referenced/accepted 证据是供体类比源,不是答案候选卡;
        # 其产物≠金标不构成 selected_wrong_product 的语义(报告 §2.1 映射
        # 决策),故类比行不进入 selected 分支,落到 unknown+机制事实。
        "selected_exists": bool(selected) and not is_analogy,
        "selected_gold": selected_gold,
        "raw_retrieval_gold": raw_gold,
        "any_gold_observed": raw_gold or task_gold or selected_gold
        or val_gold or reported_gold,
        "selected_kind": (sel_card or {}).get("kind", "evidence")
        if selected else "none",
        "mode": mode,
        "residual_mechanism": (
            "analogy_" + (prediction.get("outcome") or "no_model_response")
            if is_analogy else
            "novel_generated_products_none_match_gold"
            if mode == "novel_proposal" else "unattributed"),
    }
    bp = classify_breakpoint(facts)

    # 因果假设(单列,不冒充断点事实)
    hypo = ""
    if bp["label"] == "eligible_gold_not_selected":
        hypo = _trunc("模型选择集内含金标 recorded 卡被排在后位;模型自述理由"
                      "见 gold_card_model_reason 列(首跑原文,非审计推断)。"
                      "参考:Phase A「模型选错 22」同集合。", 300)
    elif bp["label"] == "validation_rejected_gold" and analogy_rejected:
        hypo = ("Phase C 诊断假说(供体按产物身份找回/弱映射/编辑协议缺口)"
                "见 docs/EC298_PHASE_C_REPORT.md §6.1;本表不为该假说背书,"
                "仅登记断点事实。")
    elif bp["label"] == "selected_wrong_product":
        hypo = ("选中记录/卡与 benchmark 金标在产物化学上的相容性需人工化学"
                "复核;本表只记录选中产物身份与金标不匹配这一观察。")
    elif bp["label"] == "unknown":
        hypo = "undetermined"

    refs = []
    for ref in (art.decision_ref, art.prediction_task_ref, art.prediction_ref,
                art.retrieval_ref):
        if ref:
            refs.append(ref)
    refs.extend(art.validation_refs)
    refs.extend(art.adjudication_refs)

    sel_gold_cards = [c for c in task_gold_cards if c["selectable"]]
    gold_card = sel_gold_cards[0] if sel_gold_cards else None
    analog_gold = any(c["kind"] == "analog_reaction"
                      for c in task_gold_cards) if is_analogy else None
    sel_verdicts = [v for v0 in art.validations
                    for v in v0.get("verdicts", [])
                    if v0.get("evidence_id") == selected] \
        if selected else []
    row = {
        "qid": qid,
        "input_index": next(q["input_index"] for q in view.questions
                            if q["qid"] == qid),
        "run_id": art.run_id,
        "path_id": decision.get("path_id", "") or task.get("path_id", ""),
        "agent_rank_v2": score_row["agent_rank"]
        if score_row["agent_rank"] is not None else "null",
        "engine_rank_v2": score_row["engine_rank"],
        "tier_v2": score_row["tier_v2"],
        "n_gold_products": gold_entry["n_gold_products"],
        "n_reported": len(cands),
        "gold_ids_digest": _digest_identities(gold_ids),
        "first_candidate_smiles": _trunc(first, 120),
        "first_candidate_identity": first_ident or "unparseable",
        "first_candidate_matches_gold": _b(
            first_ident in gold_ids if first_ident else None),
        "group": mode, "subgroup": sub,
        "decision_mode": decision.get("prediction_mode", ""),
        "prediction_mode": prediction.get("mode", ""),
        "outcome": prediction.get("outcome")
        or decision.get("outcome", ""),
        "selected_evidence_id": _na(selected),
        "model_order_provided": bool(order),
        "model_order": _na(";".join(order)),
        "model_order_len": len(order),
        "gold_card_order_position": gold_card["order_position"]
        if gold_card else "not_applicable",
        "decision_ref": _na(art.decision_ref),
        "task_ref": _na(art.prediction_task_ref),
        "prediction_ref": _na(art.prediction_ref),
        "validation_ref": _na(";".join(art.validation_refs)),
        "report_ref": _na(";".join(art.adjudication_refs)),
        "raw_retrieval_gold": _b(raw_gold),
        "raw_retrieval_gold_refs": _na(";".join(raw_refs[:5])),
        "task_candidate_gold": _b(task_gold),
        "task_candidate_gold_refs": _na(";".join(
            f"{c['evidence_id']}({c['kind']},cf={c['condition_fit'] or '?'})"
            for c in task_gold_cards[:5])),
        "task_candidate_gold_recorded": _b(task_gold_recorded),
        "selected_gold": _b(selected_gold),
        "selected_gold_refs": _na(";".join(
            _match_refs(sel_products, gold_ids)[:5])),
        "validated_reportable_gold": _b(val_gold),
        "validated_reportable_gold_refs": _na(";".join(val_refs[:5])),
        "reported_gold": _b(reported_gold),
        "reported_gold_refs": _na(";".join(rep_refs[:5])),
        "gold_report_rank": min(rep_ranks) if rep_ranks else "not_applicable",
        "gold_card_in_task": _b(bool(sel_gold_cards)),
        "gold_card_in_model_order": _b(
            any(c["order_position"] for c in sel_gold_cards))
        if sel_gold_cards else "not_applicable",
        "gold_card_eligible": _b(gold_card["eligible"])
        if gold_card else "not_applicable",
        "gold_card_condition_fit": gold_card["condition_fit"]
        if gold_card else "not_applicable",
        "gold_card_model_reason": _na(gold_card_reason),
        "selected_card_gates_ok": (
            _b(all(v.get("accepted") for v in sel_verdicts))
            if sel_verdicts else
            "unknown" if selected and art.validations else
            "unknown" if selected else "not_applicable"),
        "validation_reject_reasons": _na(_trunc(
            ";".join(str(r) for r in val_reasons) or
            _atomtool_reasons(checks, prediction), 300)),
        "first_proven_loss_stage": bp["label"],
        "observed_mechanism": bp["mechanism"],
        "cause_confidence": bp["confidence"],
        "uncertainty_reason": _na(bp["uncertainty"]),
        "causal_hypothesis": _na(hypo),
        "breakpoint_source_refs": _na(";".join(refs[:6])),
        "multicomponent_candidate": _b(any("." in c for c in cands)),
        "any_component_hit1": _b(any_comp_hit1),
        "component_rank": comp_rank if comp_rank is not None else "null",
        "formal_hit1": "false",
    }
    if is_analogy:
        row.update({
            "analogy_outcome": prediction.get("outcome",
                                              "") or "no_model_response",
            "donor_mapping_status": (donor_card or {}).get(
                "mapping_status", "not_applicable"),
            "donor_alignment_strategy": donor_align.get("strategy",
                                                        "not_applicable"),
            "donor_alignment_n": donor_align.get("n_aligned",
                                                 "not_applicable"),
            "atomtool_target_ok": _b(target_ok),
            "target_smiles_present": _b(bool(target_smiles)),
            "target_match_whole_cn": _b(target_whole)
            if analogy_rejected else "not_applicable",
            "target_match_any_component": _b(target_comp)
            if analogy_rejected else "not_applicable",
            "donor_product_matches_gold": _b(analog_gold),
            "atomtool_edit_reject_reasons": _na(_trunc(
                ";".join((checks.get("edit_references") or {})
                         .get("reasons", [])), 240))
            if analogy_rejected else "not_applicable",
        })
    else:
        row.update({c: "not_applicable" for c in ANALOGY_COLUMNS})

    trace = {
        "qid": qid,
        "input_index": row["input_index"],
        "items": _trace_items(art, run_root, merged_row, view, merged_sha,
                              len(cands), first),
        "gold_summary": {
            "n_gold_products": gold_entry["n_gold_products"],
            "gold_ids_digest": row["gold_ids_digest"],
            "match_results": {
                "first_candidate_matches_gold": False,
                "raw_retrieval_gold": raw_gold,
                "task_candidate_gold": task_gold,
                "selected_gold": selected_gold,
                "validated_reportable_gold": val_gold,
                "reported_gold": reported_gold,
            },
        },
        "breakpoint": {"label": bp["label"],
                       "mechanism": bp["mechanism"]},
        "notes": "",
    }
    return row, trace


def _atomtool_reasons(checks: dict, prediction: dict) -> str:
    out = []
    for name, check in checks.items():
        if isinstance(check, dict) and check.get("ok") is False:
            out.append(f"{name}:{';'.join(check.get('reasons', []))}")
    if prediction.get("fail_reason"):
        out.append(str(prediction["fail_reason"]))
    return ";".join(out)


def _trace_items(art, run_root: Path, merged_row: dict, view,
                 merged_sha: str, n_cands: int, first: str) -> list[dict]:
    """有限证据清单:相对封存根路径 + 文件 SHA + 关键字段。"""
    items = []

    def add(role: str, rel: str, fields: dict):
        p = run_root / rel
        items.append({"role": role, "path": rel,
                      "sha256": _sha256(p) if p.is_file() else "MISSING",
                      "fields": fields})

    if art.decision_ref:
        d = art.decision or {}
        add("decision", art.decision_ref,
            {"outcome": d.get("outcome", ""),
             "prediction_mode": d.get("prediction_mode", ""),
             "accepted_evidence_id": d.get("accepted_evidence_id", "")})
    if art.prediction_task_ref:
        t = art.prediction_task or {}
        add("prediction_task", art.prediction_task_ref,
            {"task_kind": t.get("task_kind", ""),
             "n_candidates": len(t.get("candidates", [])),
             "mode": t.get("mode", "")})
    if art.prediction_ref:
        p = art.prediction or {}
        add("prediction", art.prediction_ref,
            {"mode": p.get("mode", ""), "outcome": p.get("outcome", ""),
             "selected_evidence_id": p.get("selected_evidence_id", ""),
             "order_len": len(p.get("parsed", {}).get("order", []))})
    if art.retrieval_ref:
        r = art.retrieval or {}
        add("retrieval", art.retrieval_ref,
            {"n_evidences": len(r.get("evidences", [])),
             "kinds": sorted({e.get("kind", "") for e in
                              r.get("evidences", [])})})
    for i, ref in enumerate(art.validation_refs):
        add("validation", ref,
            {"evidence_id": art.validations[i].get("evidence_id", ""),
             "n_accepted": art.validations[i].get("n_accepted", ""),
             "n_total": art.validations[i].get("n_total", "")})
    for i, ref in enumerate(art.adjudication_refs):
        add("report_adjudication", ref,
            {"evidence_kind": art.adjudications[i].get("evidence_kind", ""),
             "n_entries": len(art.adjudications[i].get("entries", []))})
    n_calls = len(art.calls)
    if n_calls:
        items.append({
            "role": "llm_calls", "path":
            f"{art.run_dir_rel}/results/(prediction_call/response)",
            "sha256": "see_prediction_files", "fields":
            {"n_calls": n_calls, "n_responses": len(art.responses)}})
    items.append({
        "role": "merged_predictions",
        "path": "agent_batch/merged/predictions.jsonl",
        "sha256": merged_sha or "MISSING",
        "fields": {"route_id": merged_row.get("route_id", ""),
                   "n_candidates": n_cands,
                   "first_candidate": first[:80]},
    })
    return items


def _mode_group_pub(art):
    from pathway_v43.phase_a_attribution import _mode_group
    return _mode_group(art)


# ---------------------------------------------------------------- 锚点对账


def reconcile_anchors(view, scores: dict, gold: dict) -> dict:
    per = scores["per_question"]
    by = {q["qid"]: q for q in per}
    report = {"ok": True, "checks": {}, "diffs": []}

    def check(name, actual, expected):
        ok = actual == expected
        report["checks"][name] = {"actual": actual, "expected": expected,
                                  "ok": ok}
        if not ok:
            report["ok"] = False
            report["diffs"].append(f"{name}: actual={actual} "
                                   f"expected={expected}")

    wl = {q["qid"] for q in view.questions}
    check("n_questions", len(per), ANCHORS["n_questions"])
    check("qid_set_matches_gold_and_view",
          set(by) == wl == set(gold), True)
    miss = [q for q in per if q["agent_rank"] != 1]
    check("n_miss_hit1", len(miss), ANCHORS["n_miss_hit1"])
    check("agent_hit1", ANCHORS["n_questions"] - len(miss),
          ANCHORS["agent_hit1"])
    gc = Counter()
    r25 = 0
    for q in miss:
        art = view.runs[q["qid"]]
        mode, _ = _mode_group_pub(art)
        gc[mode] += 1
        if q["agent_rank"] is not None:
            r25 += 1
    for key, label in (("group_recorded_direct", "recorded_direct"),
                       ("group_rank_candidates", "rank_candidates"),
                       ("group_analogy_edit", "analogy_edit"),
                       ("group_novel_proposal", "novel_proposal")):
        check(key, gc[label], ANCHORS[key])
    check("groups_sum", sum(gc.values()), ANCHORS["n_miss_hit1"])
    check("n_rank_2_to_5", r25, ANCHORS["n_rank_2_to_5"])
    return report


# ---------------------------------------------------------------- Phase C 对照


def phase_c_target_recompute(view, scores: dict, gold: dict,
                             audits: list[dict]) -> list[dict]:
    """23 条被拒类比目标 × 金标:四口径独立重算(§3.3)。"""
    rows = []
    for q in scores["per_question"]:
        art = view.runs[q["qid"]]
        if _mode_group_pub(art) != ("analogy_edit", "analogy_rejected"):
            continue
        pred = art.prediction or {}
        checks = pred.get("atomtool_checks") or {}
        tgt = (checks.get("target_molecode") or {})
        ts = tgt.get("target_smiles", "") or ""
        gids = gold[q["qid"]]["gold_ids"]
        gsmis = gold[q["qid"]]["products_smiles"]
        reparse = ""
        try:
            from pathway_v43.services.atom_tool import molecode_to_smiles
            reparse = molecode_to_smiles(
                (pred.get("parsed") or {}).get("target_molecode", "")) or ""
        except Exception as exc:  # 解析器异常如实记录,不静默
            audits.append({"qid": q["qid"], "gap_type": "reparse_error",
                           "detail": str(exc)[:200],
                           "resolution": "recorded"})
        whole = bool(ts) and cn_identity(ts) in gids
        comp = bool(ts) and any((cn_identity(pt) in gids)
                                for pt in ts.split(".") if cn_identity(pt))
        text = any(gs and gs in (pred.get("parsed") or {})
                   .get("target_molecode", "") for gs in gsmis)
        rows.append({
            "qid": q["qid"],
            "run_id": art.run_id,
            "atomtool_target_ok": _b(tgt.get("ok")),
            "ledger_target_smiles": _trunc(ts, 160),
            "reparse_target_smiles": _trunc(reparse, 160),
            "ledger_equals_reparse": _b(bool(ts) and ts == reparse
                                        if ts else None),
            "match_whole_cn": _b(whole),
            "match_any_component": _b(comp),
            "match_text_contains": _b(text),
            "n_gold_products": gold[q["qid"]]["n_gold_products"],
        })
    return rows


# ---------------------------------------------------------------- 改进对照
# 状态快照:2026-09-28 读取本仓文档与代码;文档 SHA 在运行时计算写入,
# 状态结论摘自文档原文(带出处),不以实施者自报为唯一依据。
COVERAGE_DOCS = [
    ("phase_a_report", "docs/EC298_PHASE_A_REPORT.md"),
    ("phase_a_review", "docs/EC298_PHASE_A_REVIEW.md"),
    ("phase_b_report", "docs/EC298_PHASE_B_REPORT.md"),
    ("phase_b_review", "docs/EC298_PHASE_B_REVIEW.md"),
    ("phase_c_report", "docs/EC298_PHASE_C_REPORT.md"),
    ("phase_c_review_r2", "docs/EC298_PHASE_C_REVIEW_R2.md"),
    ("phase_d_task", "docs/TASK_V43_EC298_PHASE_D.md"),
]

FIX_COVERAGE_COLUMNS = [
    "breakpoint_label", "n_affected", "affected_qids", "targeted_by",
    "change_refs", "implementation_status", "review_status", "test_level",
    "frozen_dev_real_model_comparison", "new_hit1_data",
    "status_vocabulary", "supported_conclusion", "remaining_risks",
]


def build_fix_coverage(rows: list[dict], repo_root: Path) -> list[dict]:
    doc_shas = {}
    for key, rel in COVERAGE_DOCS:
        p = repo_root / rel
        doc_shas[key] = _sha256(p)[:16] if p.is_file() else "ABSENT"
    by_label = {}
    for r in rows:
        by_label.setdefault(r["first_proven_loss_stage"], []).append(r["qid"])
    comp_flip = [r["qid"] for r in rows if r["any_component_hit1"] == "true"]

    def cov(label, n, qids, targeted, refs, impl, review, tests, dev, new1,
            vocab, conclusion, risks):
        return {
            "breakpoint_label": label, "n_affected": n,
            "affected_qids": ";".join(qids), "targeted_by": targeted,
            "change_refs": refs, "implementation_status": impl,
            "review_status": review, "test_level": tests,
            "frozen_dev_real_model_comparison": dev, "new_hit1_data": new1,
            "status_vocabulary": vocab, "supported_conclusion": conclusion,
            "remaining_risks": risks,
        }

    out = [
        cov("eligible_gold_not_selected", len(by_label.get(
            "eligible_gold_not_selected", [])),
            by_label.get("eligible_gold_not_selected", []),
            "Phase B(候选裁决/报告展开解耦)",
            "services/report_adjudication.py v43-repadj-1;workflow/"
            "nodes.py adjudicate_candidates;docs/EC298_PHASE_B_REPORT.md",
            "implemented(schema v2;R1 后 42 项新测试;R2 后复测)",
            "R1 review 暂不通过(两项 P1:选中卡绕过同底物资格门禁、"
            "validation_ref 全空)→已修复;R2 复核再提两项 P1(规则卡可经 "
            "rank 选中提交、verify 可删裁决绕过)+一项 P3→已修复复测"
            "(报告 §10;当前树 356 passed);未见最终通过结论",
            "unit+workflow(合成夹具);全仓回归过",
            "not_measured(dev_real_run_not_executed,离线 off-model 重放仅证"
            "结构行为)",
            "none",
            "observed_in_first_run; implemented; independently_reviewed(两"
            "轮问题已修,未见最终通过); measured_on_frozen_dev=否",
            "R1/R2 两轮 review 的 P1 均修复后,其冻结策略 v43-repadj-1 仍规定"
            " selected 恒排第一位,对本 22 题的 @1 无已测收益;报告展开改善属 "
            "@3/@5 叙事",
            "@1 排序不动;最终通过结论待下一轮 review;不得引用 Phase B 产物"
            "主张 @1 收益"),
        cov("validation_rejected_gold", len(by_label.get(
            "validation_rejected_gold", [])),
            by_label.get("validation_rejected_gold", []),
            "Phase C(编辑协议 v2+供体适用性门禁)",
            "services/atom_tool.py v43-editproto-2;services/donor_"
            "applicability.py v43-applicability-1;domain/policy.py "
            "v43-policy-3;docs/EC298_PHASE_C_REPORT.md §7(R3 更正)",
            "implemented(45 项新测试;路由资格块+编辑语言 v2;R3 后续修复"
            "含 qid 规范化与 kind 泄漏守卫)",
            "二轮独立复核(EC298_PHASE_C_REVIEW_R2.md,2026-09-28)暂不通"
            "过:三项 P1 已确认修复,新发现 P1——rank 可把原始 analog/rule "
            "卡选为已验证产物并提交;另有三项低优先级缺口",
            "unit+workflow(夹具+恢复);离线同输入重放",
            "not_measured(dev_real_run_not_executed)",
            "none",
            "observed_in_first_run; implemented; independently_reviewed(未通"
            "过); measured_on_frozen_dev=否",
            "8 题声明目标整分子匹配金标且被编辑门禁确定性拒绝=已被证实的"
            "@1 相关损失断点(本审计与 Phase C R3 修正后口径双向一致);"
            "Phase C 同输入重放显示 22/23 旧编辑列表在新协议下仍不可执行"
            "——协议修复是必要非充分",
            "「执行后等于声明目标」未证明;新协议下模型需重新产出正确编辑;"
            "8/23 不等于 8 个可修复 @1"),
        cov("reported_at_rank_2_to_5", len(by_label.get(
            "reported_at_rank_2_to_5", [])),
            by_label.get("reported_at_rank_2_to_5", []),
            "无(首位排序未被任何阶段直接瞄准;Phase B 只扩后位可报告性)",
            "策略 v43-repadj-1:order 合同 selected 恰一次且排第一",
            "not_implemented(针对 @1 排序的改动不存在)",
            "not_applicable",
            "not_applicable",
            "not_measured",
            "none",
            "observed_in_first_run",
            "14 题正确产物已报告于第 2–5 位;提高 @1 需改首位排序策略,"
            "目前无此实现",
            "不得将「提高 @5」表述为「提高 @1」"),
        cov("selected_wrong_product", len(by_label.get(
            "selected_wrong_product", [])),
            by_label.get("selected_wrong_product", []),
            "无直接瞄准(唯一 recorded 金标/条件冲突、多 recorded 首位选择"
            "均未被 Phase B/C/D 的 @1 语义覆盖)",
            "—",
            "not_implemented",
            "not_applicable",
            "not_applicable",
            "not_measured",
            "none",
            "observed_in_first_run",
            "44 题选中记录/卡产物不含金标为可复核观察;金标仅见于原始检索"
            "非 recorded 卡(31+13)或无金标",
            "后续验证建议:冻结 dev 或新外考做成对比较;不得用已见 298 选参;"
            "engine@5 命中不等于本系统可合法报告"),
        cov("retrieval_absence_within_observed_scope", len(by_label.get(
            "retrieval_absence_within_observed_scope", [])),
            by_label.get("retrieval_absence_within_observed_scope", []),
            "无(资产/检索覆盖类;Phase D1 供体找回属类比侧且为草案)",
            "docs/TASK_V43_EC298_PHASE_D.md D1(草稿)",
            "not_implemented(draft 待用户裁决)",
            "not_applicable",
            "not_applicable",
            "not_measured",
            "none",
            "observed_in_first_run",
            "33 题在已封存检索范围内无任何含金标层;完整候选池不存在,"
            "不能声称数据库无正确反应",
            "扩检索/资产属新外考问题;已见 298 不得用于检索调参"),
        cov("unknown", len(by_label.get("unknown", [])),
            by_label.get("unknown", []),
            "部分相关:Phase C 门禁改变类比进入率(23/66 路由资格模拟,"
            "非命中分数);Phase D1/D2/D3 为草案",
            "docs/EC298_PHASE_C_REPORT.md §6.1;docs/TASK_V43_EC298_PHASE_D.md",
            "implemented(门禁)/not_implemented(D1-D3)",
            "Phase C 二轮独立复核暂不通过(见 validation_rejected_gold 行);"
            "Phase D 未启动",
            "unit+workflow(Phase C 45 项)",
            "not_measured(dev 三臂对照未执行)",
            "none",
            "observed_in_first_run; implemented(部分); measured_on_frozen_dev=否",
            "61 题金标仅见于原始检索层而 agent 产物链从未出现(类比弃答/"
            "生成错误产物为主);具体断点环节离线不可判",
            "门禁减少类比进入率可能把题转向 novel/hold,不构成准确率提升;"
            "后验分析不得宣称泛化改善"),
        cov("multicomponent_formal_scoring_definition", len(comp_flip),
            comp_flip,
            "无(正式口径保持整条候选;敏感性两臂同法、仅探索)",
            "exam_v2.multicomponent_sensitivity;reports/ec298/phase_a_v2/"
            "multicomponent_sensitivity.json",
            "not_applicable(定义未改)",
            "not_applicable",
            "unit(exploratory 表)",
            "not_applicable",
            "none",
            "observed_in_first_run(敏感性口径)",
            f"{len(comp_flip)} 题在「任一组分命中」探索口径下 @1 可翻转;"
            "正式 116/298 不变",
            "组分口径若要转正须两臂同规则并重新外考;不得只改 agent 臂"),
    ]
    out.append({
        "breakpoint_label": "_cross_cutting_phase_c_0of23_divergence",
        "n_affected": 23,
        "affected_qids": "", "targeted_by": "本审计(独立重算)",
        "change_refs": "scripts/ec298_hit1_attribution.py "
                       "phase_c_target_recompute",
        "implementation_status": "audit_complete",
        "review_status": "本任务书 §3.3 要求的独立重算",
        "test_level": "unit(负例:可解析非金标不得标验证拒绝)",
        "frozen_dev_real_model_comparison": "not_applicable",
        "new_hit1_data": "none",
        "status_vocabulary": "observed_in_first_run",
        "supported_conclusion": "以首跑账本 target_smiles+正式金标+"
                               "cn_identity 独立重算:8/23 整分子匹配、"
                               "+1 任一组分、1 不可解析、13 无匹配;账本与"
                               "现解析器 22/22 逐字一致。与 Phase C R3 修正"
                               "后口径(初版 0/23 系其脚本题号 bug,已更正)"
                               "双向一致",
        "remaining_risks": f"文档 SHA 快照: " + ";".join(
            f"{k}={v}" for k, v in doc_shas.items()),
    })
    return out


# ---------------------------------------------------------------- 输出


def write_jsonl(path: Path, rows: list[dict]) -> None:
    lines = [json.dumps(r, ensure_ascii=False, sort_keys=True)
             for r in rows]
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text("\n".join(lines) + "\n", encoding="utf-8")
    tmp.replace(path)


def write_manifest(out_dir: Path, names: list[str]) -> None:
    lines = [f"{_sha256(out_dir / n)}  {n}"
             for n in sorted(names) if (out_dir / n).is_file()]
    (out_dir / "output_manifest.sha256").write_text(
        "\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------- main


def load_phase_a_script():
    spec = importlib.util.spec_from_file_location(
        "ec298_phase_a", REPO_ROOT / "scripts" / "ec298_phase_a.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="EC298 hit@1 失分逐题归因(零 API、零封存写入)")
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--gold", required=True)
    ap.add_argument("--v1-scoring", required=True)
    ap.add_argument("--v41-baseline", required=True)
    ap.add_argument("--asset-library", required=True)
    ap.add_argument("--phase-a-dir", required=True,
                    help="Phase A 输出目录(含 input_manifest.json 与 "
                         "score_v2.json)")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--check", action="store_true",
                    help="复算并与既有输出逐字节比对,不写盘")
    ap.add_argument("--skip-anchor-check", action="store_true",
                    help="仅限合成夹具测试;正式运行严禁")
    args = ap.parse_args(argv)

    run_dir, gold_path = Path(args.run_dir), Path(args.gold)
    phase_a_dir, out_dir = Path(args.phase_a_dir), Path(args.out_dir)

    # 1) Phase A 只读清单校验(双向 fail-closed;严禁重建清单)
    pa = load_phase_a_script()
    manifest_path = phase_a_dir / "input_manifest.json"
    if not manifest_path.is_file():
        raise ScorerV2Error("Phase A 输入清单缺失(不得重建)",
                            {"path": str(manifest_path)})
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    pa.verify_input_manifest(manifest, run_dir, gold_path,
                             Path(args.v1_scoring), Path(args.v41_baseline),
                             Path(args.asset_library))

    # 2) score_v2 及其输入 SHA 对账
    score_path = phase_a_dir / "score_v2.json"
    scores = json.loads(score_path.read_text(encoding="utf-8"))
    ins = scores.get("inputs_sha256") or {}
    expect = {
        "agent_predictions": run_dir / "agent_batch/merged/predictions.jsonl",
        "engine_results": run_dir / "engine_arm/engine_results.jsonl",
        "gold_questions": gold_path,
    }
    for role, p in expect.items():
        if role in ins and _sha256(p) != ins[role]:
            raise ScorerV2Error("score_v2 输入 SHA 与当前文件不一致",
                                {"role": role, "path": str(p)})

    # 3) 载入封存视图与金标(金标仅本离线进程读取)
    view = load_sealed_run_view(run_dir)
    gold = load_gold(gold_path)

    audits: list[dict] = []
    if not args.skip_anchor_check:
        report = reconcile_anchors(view, scores, gold)
        if not report["ok"]:
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / "anchor_mismatch.json").write_text(
                json.dumps(report, ensure_ascii=False, indent=2),
                encoding="utf-8")
            print("锚点不符,已写 anchor_mismatch.json 并停止正式报告",
                  file=sys.stderr)
            return 1

    # 4) 182 题逐题
    by_qid = {q["qid"]: q for q in scores["per_question"]}
    merged_sha = _sha256(run_dir / "agent_batch/merged/predictions.jsonl")
    rows, traces = [], []
    for q in view.questions:
        qid = q["qid"]
        sc = by_qid[qid]
        if sc["agent_rank"] == 1:
            continue
        row, trace = audit_question(qid, view.runs[qid], gold[qid], sc,
                                    view, run_dir, audits, merged_sha)
        rows.append(row)
        traces.append(trace)

    # 5) 类比目标 × 金标独立重算(23 条被拒)
    target_rows = phase_c_target_recompute(view, scores, gold, audits)

    # 6) 汇总
    group_summary = _group_summary(rows)
    inputs_sha = {
        "input_manifest": _sha256(manifest_path),
        "score_v2": _sha256(score_path),
        **{f"manifest_role_{g['role']}": g["entries"][0]["sha256"]
           if g["n_files"] == 1 else f"{g['n_files']} files verified"
           for g in manifest["groups"]},
    }

    if args.check:
        return _check_outputs(out_dir, rows, traces, group_summary,
                              target_rows, inputs_sha, audits)

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "input_sha256.json").write_text(
        json.dumps({
            "script_version": SCRIPT_VERSION,
            "zero_api": True,
            "verified": "scripts/ec298_phase_a.verify_input_manifest "
                        "(双向;任一字节不符即失败)",
            **inputs_sha,
        }, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8")
    write_tsv(out_dir / "hit1_misses.tsv",
              MISS_COLUMNS + ANALOGY_COLUMNS, rows)
    write_jsonl(out_dir / "evidence_trace.jsonl", traces)
    write_tsv(out_dir / "group_summary.tsv",
              ["group", "subgroup", "n_miss", "n_rank2_5",
               "raw_retrieval_gold", "task_candidate_gold", "selected_gold",
               "validated_reportable_gold", "reported_gold"]
              + list(LABELS) + ["component_flip_hit1"],
              group_summary)
    write_tsv(out_dir / "fix_coverage.tsv", FIX_COVERAGE_COLUMNS,
              build_fix_coverage(rows, REPO_ROOT))
    write_tsv(out_dir / "score_sensitivity.tsv",
              ["qid", "group", "subgroup", "agent_rank_v2", "component_rank",
               "multicomponent_candidate", "any_component_hit1",
               "formal_hit1", "n_gold_products"],
              [{"qid": r["qid"], "group": r["group"],
                "subgroup": r["subgroup"],
                "agent_rank_v2": r["agent_rank_v2"],
                "component_rank": r["component_rank"],
                "multicomponent_candidate": r["multicomponent_candidate"],
                "any_component_hit1": r["any_component_hit1"],
                "formal_hit1": "false",
                "n_gold_products": r["n_gold_products"]} for r in rows])
    write_tsv(out_dir / "analogy_target_gold_recompute.tsv",
              list(target_rows[0].keys()) if target_rows else
              ["qid", "note"], target_rows)
    write_tsv(out_dir / "audit_gaps.tsv",
              ["qid", "gap_type", "detail", "resolution"],
              audits)
    names = ["input_sha256.json", "hit1_misses.tsv", "evidence_trace.jsonl",
             "group_summary.tsv", "fix_coverage.tsv",
             "score_sensitivity.tsv", "analogy_target_gold_recompute.tsv",
             "audit_gaps.tsv"]
    write_manifest(out_dir, names)

    label_counts = Counter(r["first_proven_loss_stage"] for r in rows)
    print(json.dumps({
        "script_version": SCRIPT_VERSION,
        "n_miss_rows": len(rows),
        "label_counts": dict(label_counts),
        "n_unknown": label_counts["unknown"],
        "analogy_target_recompute": {
            "n_rejected": len(target_rows),
            "whole_cn": sum(1 for t in target_rows
                            if t["match_whole_cn"] == "true"),
            "any_component": sum(1 for t in target_rows
                                 if t["match_any_component"] == "true"),
        },
        "n_audit_gaps": len(audits),
    }, ensure_ascii=False))
    return 0


def _group_summary(rows: list[dict]) -> list[dict]:
    order = [("recorded_direct", "commit_recorded"),
             ("rank_candidates", "selected"),
             ("analogy_edit", "analogy_abstained"),
             ("analogy_edit", "analogy_rejected"),
             ("analogy_edit", "analogy_proposed"),
             ("novel_proposal", "proposed")]
    buckets: dict[tuple[str, str], list[dict]] = {}
    for r in rows:
        buckets.setdefault((r["group"], r["subgroup"]), []).append(r)
    for key in buckets:
        if key not in order:
            order.append(key)
    out = []
    for key in order:
        sub = buckets.get(key, [])
        if not sub:
            continue
        row = {
            "group": key[0], "subgroup": key[1], "n_miss": len(sub),
            "n_rank2_5": sum(1 for r in sub if r["agent_rank_v2"] != "null"),
        }
        for col in ("raw_retrieval_gold", "task_candidate_gold",
                    "selected_gold", "validated_reportable_gold",
                    "reported_gold"):
            row[col] = sum(1 for r in sub if r[col] == "true")
        for lab in LABELS:
            row[lab] = sum(1 for r in sub
                           if r["first_proven_loss_stage"] == lab)
        row["component_flip_hit1"] = sum(1 for r in sub
                                         if r["any_component_hit1"] == "true")
        out.append(row)
    total = {"group": "TOTAL", "subgroup": "", "n_miss": len(rows),
             "n_rank2_5": sum(1 for r in rows
                              if r["agent_rank_v2"] != "null")}
    for col in ("raw_retrieval_gold", "task_candidate_gold", "selected_gold",
                "validated_reportable_gold", "reported_gold"):
        total[col] = sum(1 for r in rows if r[col] == "true")
    for lab in LABELS:
        total[lab] = sum(1 for r in rows
                         if r["first_proven_loss_stage"] == lab)
    total["component_flip_hit1"] = sum(1 for r in rows
                                       if r["any_component_hit1"] == "true")
    out.append(total)
    return out


def _render_outputs(rows, traces, group_summary, target_rows, inputs_sha,
                    audits):
    """与 main 落盘完全一致的字节序列(供 --check 比对)。"""
    import io

    def tsv_bytes(columns, data):
        from pathway_v43.exam_v2 import _fmt
        buf = io.StringIO()
        buf.write("\t".join(columns) + "\n")
        for r in data:
            buf.write("\t".join(_fmt(r.get(c)) for c in columns) + "\n")
        return buf.getvalue().encode("utf-8")

    def json_bytes(payload):
        return (json.dumps(payload, ensure_ascii=False, indent=2,
                           sort_keys=True) + "\n").encode("utf-8")

    def jsonl_bytes(data):
        return ("\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True)
                          for r in data) + "\n").encode("utf-8")

    outs = {
        "input_sha256.json": json_bytes({
            "script_version": SCRIPT_VERSION, "zero_api": True,
            "verified": "scripts/ec298_phase_a.verify_input_manifest "
                        "(双向;任一字节不符即失败)",
            **inputs_sha}),
        "hit1_misses.tsv": tsv_bytes(MISS_COLUMNS + ANALOGY_COLUMNS, rows),
        "evidence_trace.jsonl": jsonl_bytes(traces),
        "group_summary.tsv": tsv_bytes(
            ["group", "subgroup", "n_miss", "n_rank2_5",
             "raw_retrieval_gold", "task_candidate_gold", "selected_gold",
             "validated_reportable_gold", "reported_gold"]
            + list(LABELS) + ["component_flip_hit1"], group_summary),
        "fix_coverage.tsv": tsv_bytes(
            FIX_COVERAGE_COLUMNS, build_fix_coverage(rows, REPO_ROOT)),
        "score_sensitivity.tsv": tsv_bytes(
            ["qid", "group", "subgroup", "agent_rank_v2", "component_rank",
             "multicomponent_candidate", "any_component_hit1",
             "formal_hit1", "n_gold_products"],
            [{"qid": r["qid"], "group": r["group"],
              "subgroup": r["subgroup"],
              "agent_rank_v2": r["agent_rank_v2"],
              "component_rank": r["component_rank"],
              "multicomponent_candidate": r["multicomponent_candidate"],
              "any_component_hit1": r["any_component_hit1"],
              "formal_hit1": "false",
              "n_gold_products": r["n_gold_products"]} for r in rows]),
        "analogy_target_gold_recompute.tsv": tsv_bytes(
            list(target_rows[0].keys()) if target_rows else
            ["qid", "note"], target_rows),
        "audit_gaps.tsv": tsv_bytes(
            ["qid", "gap_type", "detail", "resolution"], audits),
    }
    return outs


def _check_outputs(out_dir: Path, rows, traces, group_summary, target_rows,
                   inputs_sha, audits) -> int:
    outs = _render_outputs(rows, traces, group_summary, target_rows,
                           inputs_sha, audits)
    bad = []
    for name, data in sorted(outs.items()):
        p = out_dir / name
        if not p.is_file():
            bad.append(f"{name}: MISSING")
        elif p.read_bytes() != data:
            bad.append(f"{name}: BYTES DIFFER")
    man = out_dir / "output_manifest.sha256"
    if man.is_file():
        for line in man.read_text(encoding="utf-8").splitlines():
            sha, _, name = line.partition("  ")
            p = out_dir / name
            if p.is_file() and _sha256(p) != sha:
                bad.append(f"{name}: MANIFEST SHA DIFFER")
    if bad:
        print(json.dumps({"check": "FAIL", "diffs": bad},
                         ensure_ascii=False))
        return 1
    print(json.dumps({"check": "OK",
                      "files": sorted(outs)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
