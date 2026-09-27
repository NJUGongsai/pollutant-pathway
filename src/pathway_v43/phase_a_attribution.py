"""EC298 Phase A — 离线归因构建器(A1–A6,全部基于 scorer-2 口径)。

阶段任务书:docs/TASK_V43_EC298_PHASE_A.md §3。所有推断都能沿封存的
run/task/decision/validation/adjudication 文件回查;金标只用于离线判定,
绝不进入预测、检索或模型请求。构建器是纯函数:输入为封存产物视图
(``SealedRunView``)与 v2 评分结果,输出行字典列表;TSV 落盘由调用方
(``scripts/ec298_phase_a.py``)用 ``exam_v2.write_tsv`` 完成。

- A1 ``agent_hits_by_engine_tier``:每题引擎 Top-10 内外两档 + agent 命中来源。
- A2 ``awaiting_prediction_fates``:50 条 awaiting_prediction 的命运,
  budget_exhausted 1 条单列汇总,51 条空答闭环;孤儿审计(调用↔响应配对)。
- A3 ``decision_path_contribution``:按持久 decision_log 与任务模式归组,
  另给逐题明细;不凭预测 SMILES 倒推模式。
- A4 ``hit5_paired_attribution``:298 题配对 + discordant(engine-only /
  agent-only)谨慎归因,一题一个主因并保留不确定。
- A5 ``v41_baseline_diff``:新引擎 vs 历史 v4.1 引擎逐题首命中 rank 差异。
- A6 ``llm_call_distribution``:298 题逐题调用账(issued/成功/失败/孤儿)。
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from .exam_v2 import TIER_NOT_IN_TOP10, TIER_TOP10_HIT, ScorerV2Error

PHASE_A_VERSION = "v43-ec298-phase-a-1"

ATtributionLabels = (
    "候选未检出(引擎已导出 Top-10)",  # 仅指已导出 Top-10;外池未知
    "候选检出但未报告",          # 金标在已验证/可报告层,未进入最终报告
    "模型选错",                # 任务候选(模型选择集)存在正确可选卡,模型未选
    "类比弃答",                # analogy_edit + abstained
    "编辑拒绝",                # analogy_edit + rejected
    "候选虽报告但身份不匹配",     # 已选证据产物含金标,报告产物身份均不匹配
    "证据不足以判断",           # 事实不足以支持上述任一标签(含仅原始检索含金标)
)

EVIDENCE_LAYER_NOTE = (
    "证据五层(逐层给来源与引用,不得从下层直接推出上层):"
    "raw_retrieval_gold=原始检索卡含金标(未经任何门禁);"
    "task_candidate_gold=预测任务候选(recorded 卡,模型选择集)含金标;"
    "selected_gold=被选中证据的产物含金标;"
    "validated_reportable_gold=validation 判 accepted 的产物含金标;"
    "reported_gold=最终裁决账本可报告产物含金标")


# ---------------------------------------------------------------- 封存产物视图


@dataclass
class RunArtifacts:
    qid: str
    run_id: str
    run_dir_rel: str
    decision: dict | None = None
    decision_ref: str = ""
    prediction: dict | None = None
    prediction_ref: str = ""
    prediction_task: dict | None = None
    prediction_task_ref: str = ""
    retrieval: dict | None = None
    retrieval_ref: str = ""
    calls: list[dict] = field(default_factory=list)      # {file, payload}
    responses: list[dict] = field(default_factory=list)  # {file, payload}
    validations: list[dict] = field(default_factory=list)
    validation_refs: list[str] = field(default_factory=list)
    adjudications: list[dict] = field(default_factory=list)
    adjudication_refs: list[str] = field(default_factory=list)
    run_identity: dict | None = None

    @property
    def prediction_outcome(self) -> str:
        return (self.prediction or {}).get("outcome", "")

    @property
    def prediction_mode(self) -> str:
        return (self.prediction or {}).get("mode", "")


@dataclass
class SealedRunView:
    run_root: Path
    questions: list[dict]            # exam_inputs.jsonl 冻结顺序
    worker_status: dict[str, dict]   # qid → workers/*.status.json
    merged: dict[str, dict]          # qid → merged predictions 行
    runs: dict[str, RunArtifacts]    # qid → 逐题产物

    def ordered_qids(self) -> list[str]:
        return [q["qid"] for q in self.questions]


def _iter_jsonl(path: Path):
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            yield json.loads(line)


def load_sealed_run_view(run_root: str | Path) -> SealedRunView:
    """读入封存首跑目录(只读);qid 与白名单一一对应,fail-closed。"""
    run_root = Path(run_root)
    for required in ("exam_inputs.jsonl",
                     "agent_batch/merged/predictions.jsonl",
                     "agent_batch/workers"):
        if not (run_root / required).exists():
            raise ScorerV2Error("封存首跑目录缺核心输入(fail-closed)",
                                {"path": str(run_root / required)})
    questions = [r for r in _iter_jsonl(run_root / "exam_inputs.jsonl")]
    worker_status: dict[str, dict] = {}
    workers_dir = run_root / "agent_batch" / "workers"
    for p in sorted(workers_dir.glob("*.status.json")):
        s = json.loads(p.read_text(encoding="utf-8"))
        worker_status[s["route_id"]] = s
    merged: dict[str, dict] = {}
    for r in _iter_jsonl(run_root / "agent_batch" / "merged"
                         / "predictions.jsonl"):
        merged[r["route_id"]] = r
    whitelist = {q["qid"] for q in questions}
    if set(worker_status) != whitelist or set(merged) != whitelist:
        raise ScorerV2Error("白名单/worker 状态/答卷 qid 集合不一致", {
            "n_whitelist": len(whitelist),
            "n_workers": len(worker_status), "n_merged": len(merged)})

    runs: dict[str, RunArtifacts] = {}
    for run_dir in sorted((run_root / "agent_runs").iterdir()):
        if not run_dir.is_dir():
            continue
        name = run_dir.name
        if "RXNG_" not in name:
            raise ScorerV2Error("run 目录名缺 RXNG_ 前缀,无法映射 qid",
                                {"run_dir": name})
        qid = "RXNG_" + name.split("RXNG_", 1)[1]
        if qid not in whitelist:
            raise ScorerV2Error("run 目录 qid 不在白名单", {"run_dir": name})
        art = RunArtifacts(qid=qid, run_id=name,
                           run_dir_rel=str(run_dir.relative_to(run_root)))
        for p in sorted((run_dir / "results").rglob("*.json")):
            rel = str(p.relative_to(run_root))
            fn = p.name
            try:
                doc = json.loads(p.read_text(encoding="utf-8"))
            except Exception as exc:
                raise ScorerV2Error("封存 JSON 解析失败",
                                    {"path": rel, "error": str(exc)})
            payload = doc.get("payload", doc)
            if fn == "decision.json":
                art.decision, art.decision_ref = payload, rel
            elif fn == "prediction.json":
                if art.prediction is not None:
                    raise ScorerV2Error("run 内多个 prediction.json",
                                        {"run": name})
                art.prediction, art.prediction_ref = payload, rel
            elif fn == "prediction_task.json":
                art.prediction_task, art.prediction_task_ref = payload, rel
            elif fn == "retrieval.json":
                art.retrieval, art.retrieval_ref = payload, rel
            elif fn == "validation.json":
                art.validations.append(payload)
                art.validation_refs.append(rel)
            elif fn == "report_adjudication.json":
                art.adjudications.append(payload)
                art.adjudication_refs.append(rel)
            elif fn.startswith("prediction_call."):
                art.calls.append({"file": rel, "payload": payload})
            elif fn.startswith("prediction_response."):
                art.responses.append({"file": rel, "payload": payload})
        rid_path = run_dir / "run_identity.json"
        if rid_path.is_file():
            art.run_identity = json.loads(
                rid_path.read_text(encoding="utf-8"))
        runs[qid] = art
    if set(runs) != whitelist:
        raise ScorerV2Error("run 目录与白名单 qid 不一致", {
            "missing": sorted(whitelist - set(runs))[:5],
            "extra": sorted(set(runs) - whitelist)[:5]})
    return SealedRunView(run_root=run_root, questions=questions,
                         worker_status=worker_status, merged=merged,
                         runs=runs)


# ---------------------------------------------------------------- 公共取数


def _gold_ids_fn(gold_questions_path: str | Path):
    from .exam_v2 import load_gold

    gold = load_gold(gold_questions_path)
    return lambda qid: gold[qid]["gold_ids"]


def _retrieval_products(art: RunArtifacts) -> list[str]:
    """原始检索证据的全部产物 SMILES(按卡序、卡内序拼接)。"""
    ret = art.retrieval or {}
    products: list[str] = []
    for ev in ret.get("evidences", []):
        for p in ev.get("products", []):
            products.append(p.get("product_smiles", ""))
    return products


def _retrieval_top5_products(art: RunArtifacts) -> list[str]:
    ret = art.retrieval or {}
    products: list[str] = []
    for ev in ret.get("evidences", [])[:5]:
        for p in ev.get("products", []):
            products.append(p.get("product_smiles", ""))
    return products


def _any_gold(products: list[str], gold_ids: set[str]) -> bool:
    from .domain.identity import cn_identity

    return any(cn_identity(p) in gold_ids for p in products)


def _paired_class(agent_rank: int | None, engine_rank: int | None,
                  k: int) -> str:
    a = agent_rank is not None and agent_rank <= k
    e = engine_rank is not None and engine_rank <= k
    return "both" if a and e else "agent_only" if a else \
        "engine_only" if e else "neither"


def _mode_group(art: RunArtifacts) -> tuple[str, str]:
    """(组, 子组):按持久 decision_log 与任务模式;不以预测 SMILES 倒推。"""
    p_mode = art.prediction_mode
    p_outcome = art.prediction_outcome
    if p_mode:
        mode = p_mode
    else:
        mode = (art.decision or {}).get("prediction_mode", "") \
            or "recorded_bypass"
        if mode == "recorded_bypass":
            return "recorded_direct", (art.decision or {}).get(
                "outcome") or "commit_recorded"
    outcome = p_outcome or (art.decision or {}).get("outcome", "")
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


def _mode_agrees(art: RunArtifacts) -> bool:
    d_mode = (art.decision or {}).get("prediction_mode")
    if not art.prediction_mode:
        return d_mode in (None, "", "recorded_bypass")
    return d_mode == art.prediction_mode


# ---------------------------------------------------------------- A1


A1_COLUMNS = [
    "qid", "input_index", "tier_v2", "agent_rank", "engine_rank",
    "agent_hit@1", "agent_hit@3", "agent_hit@5",
    "agent_hit_smiles_raw", "agent_hit_evidence_id",
    "agent_hit_report_rank", "agent_hit_evidence_kind",
    "agent_hit_source_ref", "agent_hit_ref_ok",
    "decision_mode", "decision_outcome", "decision_path_id",
    "decision_ref", "run_id",
    "novel_evidence_state", "gold_in_retrieval_any_card",
]

A1_SUMMARY_COLUMNS = ["tier_v2", "n_questions", "agent_hit@1",
                      "agent_hit@3", "agent_hit@5", "note"]


def _agent_hit_source(art: RunArtifacts, hit_smiles: str) -> dict:
    """命中候选 → 裁决账本来源(evidence_id/report_rank/kind);可回查。"""
    from .domain.identity import cn_identity

    if not hit_smiles or not art.adjudications:
        return {"evidence_id": "", "report_rank": "", "kind": "",
                "ref": "", "ok": False}
    ident = cn_identity(hit_smiles)
    best = None
    for adj, ref in zip(art.adjudications, art.adjudication_refs):
        for e in adj.get("entries", []):
            if cn_identity(e.get("product_smiles", "")) == ident:
                rank = e.get("report_rank")
                cand = (10**9 if rank is None else rank,
                        e.get("evidence_id", ""),
                        adj.get("evidence_kind", ""), ref)
                if best is None or cand[0] < best[0]:
                    best = cand
    if best is None:
        return {"evidence_id": "", "report_rank": "", "kind": "",
                "ref": "", "ok": False}
    return {"evidence_id": best[1], "report_rank": best[0],
            "kind": best[2], "ref": best[3], "ok": True}


def build_agent_hits_by_engine_tier(view: SealedRunView, scores_v2: dict,
                                    gold_ids_fn) -> tuple[list[dict],
                                                          list[dict]]:
    from .exam_v2 import agent_candidates

    by_qid = {q["qid"]: q for q in scores_v2["per_question"]}
    rows: list[dict] = []
    for q in view.questions:
        qid = q["qid"]
        sc = by_qid[qid]
        art = view.runs[qid]
        hit_rank = sc["agent_rank"]
        hit_smiles = ""
        if hit_rank is not None:
            cands = agent_candidates(view.merged[qid])
            if hit_rank <= len(cands):
                hit_smiles = cands[hit_rank - 1]
        src = _agent_hit_source(art, hit_smiles)
        mode, outcome = _mode_group(art)
        novel_state = ""
        if mode == "novel_proposal":
            novel_state = ("retrieval_products_present"
                           if _retrieval_products(art) else
                           "no_retrieval_products")
        rows.append({
            "qid": qid, "input_index": q["input_index"],
            "tier_v2": sc["tier_v2"],
            "agent_rank": hit_rank, "engine_rank": sc["engine_rank"],
            "agent_hit@1": hit_rank is not None and hit_rank <= 1,
            "agent_hit@3": hit_rank is not None and hit_rank <= 3,
            "agent_hit@5": hit_rank is not None and hit_rank <= 5,
            "agent_hit_smiles_raw": hit_smiles,
            "agent_hit_evidence_id": src["evidence_id"],
            "agent_hit_report_rank": src["report_rank"],
            "agent_hit_evidence_kind": src["kind"],
            "agent_hit_source_ref": src["ref"],
            "agent_hit_ref_ok": src["ok"],
            "decision_mode": mode, "decision_outcome": outcome,
            "decision_path_id": (art.decision or {}).get("path_id", ""),
            "decision_ref": art.decision_ref, "run_id": art.run_id,
            "novel_evidence_state": novel_state,
            "gold_in_retrieval_any_card": _any_gold(
                _retrieval_products(art), gold_ids_fn(qid)),
        })

    def agg(tier: str, note: str) -> dict:
        sub = [r for r in rows if r["tier_v2"] == tier]
        return {
            "tier_v2": tier, "n_questions": len(sub),
            "agent_hit@1": sum(1 for r in sub if r["agent_hit@1"]),
            "agent_hit@3": sum(1 for r in sub if r["agent_hit@3"]),
            "agent_hit@5": sum(1 for r in sub if r["agent_hit@5"]),
            "note": note,
        }

    summary = [
        agg(TIER_TOP10_HIT,
            "金标在已导出引擎 Top-10 内;档位描述不外推完整池"),
        agg(TIER_NOT_IN_TOP10,
            "已导出 Top-10 未命中;Top-10 外是否有引擎候选未知,不得称"
            "完整池真空;89 档中 agent 命中者来源见逐表列"),
    ]
    return rows, summary


# ---------------------------------------------------------------- A2


A2_COLUMNS = [
    "qid", "input_index", "stop_reason", "mode", "outcome",
    "n_issued", "n_provider_ok", "n_failed",
    "response_files", "request_ids", "parsed_present",
    "prediction_artifact_ref", "decision_ref",
    "atomtool_target_molecode_ok", "atomtool_edit_references_ok",
    "fail_or_abstain_reason", "submitted", "validation_state",
    "v2_agent_rank", "orphan_count", "run_id",
]

ORPHAN_AUDIT_NOTE = (
    "孤儿=同一 results/<task>/ 目录、同一 attempt 序号下 "
    "prediction_call.aN.json 无对应 prediction_response.aN.json(或反向);"
    "配对键=完整相对 task 目录 + payload/文件名 attempt,不按文件名全局抵消")


def _call_response_ledger(art: RunArtifacts) -> dict:
    calls = sorted(art.calls, key=lambda c: c["file"])
    responses = sorted(art.responses, key=lambda c: c["file"])

    def key_of(rel: str, kind: str) -> tuple[str, str]:
        p = Path(rel)
        # 同一 task 目录 + 同一 attempt 才配对;跨 task 的同名 attempt 不抵消
        return (str(p.parent), f"{kind}:{p.stem.split('.', 1)[-1]}")

    call_keys = {key_of(c["file"], "call") for c in calls}
    resp_keys = {key_of(r["file"], "response") for r in responses}
    orphans = 0
    for c in calls:
        if key_of(c["file"], "response") not in resp_keys:
            orphans += 1
    for r in responses:
        if key_of(r["file"], "call") not in call_keys:
            orphans += 1
    ok = failed = 0
    request_ids = []
    for r in responses:
        tr = (r["payload"] or {}).get("transport", {})
        if tr.get("ok") is True and tr.get("status") == 200:
            ok += 1
        else:
            failed += 1
        if tr.get("request_id"):
            request_ids.append(tr["request_id"])
    return {"n_issued": len(calls), "n_provider_ok": ok, "n_failed": failed,
            "response_files": ";".join(Path(r["file"]).name
                                       for r in responses),
            "request_ids": ";".join(request_ids), "orphan_count": orphans}


def _truncate(text: str, limit: int = 500) -> str:
    text = " ".join(str(text or "").split())
    return text if len(text) <= limit else text[:limit] + "…[截断,全文见引用文件]"


def build_awaiting_prediction_fates(view: SealedRunView, scores_v2: dict
                                    ) -> tuple[list[dict], list[dict], dict]:
    by_qid = {q["qid"]: q for q in scores_v2["per_question"]}
    rows: list[dict] = []
    extra: list[dict] = []

    def fate_row(qid: str) -> dict:
        art = view.runs[qid]
        sc = by_qid[qid]
        led = _call_response_ledger(art)
        p = art.prediction or {}
        parsed = p.get("parsed") or {}
        checks = p.get("atomtool_checks") or {}
        target = checks.get("target_molecode") or {}
        editrefs = checks.get("edit_references") or {}
        reason = parsed.get("reason") or p.get("reason") \
            or p.get("fail_reason") or ""
        stop = view.worker_status[qid].get("stop_reason", "")
        return {
            "qid": qid, "input_index": next(
                q["input_index"] for q in view.questions if q["qid"] == qid),
            "stop_reason": stop,
            "mode": p.get("mode") or "recorded_bypass",
            "outcome": p.get("outcome", ""),
            **led,
            "parsed_present": bool(p.get("parsed")),
            "prediction_artifact_ref": art.prediction_ref,
            "decision_ref": art.decision_ref,
            "atomtool_target_molecode_ok": target.get("ok", ""),
            "atomtool_edit_references_ok": editrefs.get("ok", ""),
            "fail_or_abstain_reason": _truncate(reason),
            "submitted": bool(art.adjudications),
            "validation_state": "absent_no_validation_json"
            if not art.validations else
            f"{len(art.validations)}_validation_files",
            "v2_agent_rank": sc["agent_rank"],
            "orphan_count": led["orphan_count"],
            "run_id": art.run_id,
        }

    for q in view.questions:
        qid = q["qid"]
        stop = view.worker_status[qid].get("stop_reason", "")
        if stop == "awaiting_prediction":
            rows.append(fate_row(qid))
        elif stop != "completed":
            extra.append(fate_row(qid))
    n_empty = sum(1 for sc in scores_v2["per_question"]
                  if sc["n_predicted"] == 0)
    audits = {
        "n_awaiting_prediction_rows": len(rows),
        "n_budget_exhausted_rows": len(extra),
        "n_empty_answers_v2": n_empty,
        "closed_loop_ok": len(rows) + len(extra) == n_empty,
        "outcomes": dict(Counter(r["outcome"] for r in rows + extra)),
        "total_issued": sum(r["n_issued"] for r in rows + extra),
        "total_provider_ok": sum(r["n_provider_ok"] for r in rows + extra),
        "total_failed": sum(r["n_failed"] for r in rows + extra),
        "total_orphans": sum(r["orphan_count"] for r in rows + extra),
        "orphan_audit": ORPHAN_AUDIT_NOTE,
        "note": "空答不反推'未调用模型';弃答/拒绝以持久 prediction/decision "
                "产物核验;atomtool 检查项来自 prediction payload,"
                "51 题无 validation.json 属预期(未产生可验证产物)",
    }
    return rows, extra, audits


# ---------------------------------------------------------------- A3


A3_GROUP_ORDER = [
    ("recorded_direct", "commit_recorded"),
    ("rank_candidates", "selected"),
    ("analogy_edit", "analogy_abstained"),
    ("analogy_edit", "analogy_rejected"),
    ("analogy_edit", "analogy_proposed"),
    ("novel_proposal", "proposed"),
]

A3_COLUMNS = [
    "group", "subgroup", "n_questions",
    "agent_hit@1", "agent_hit@3", "agent_hit@5",
    "engine_hit@1", "engine_hit@3", "engine_hit@5",
    "paired@1_both", "paired@1_agent_only", "paired@1_engine_only",
    "paired@1_neither",
    "paired@5_both", "paired@5_agent_only", "paired@5_engine_only",
    "paired@5_neither",
]

A3_DETAIL_COLUMNS = [
    "qid", "input_index", "group", "subgroup",
    "decision_mode", "prediction_mode", "mode_source_agrees",
    "decision_outcome", "prediction_outcome",
    "agent_rank", "engine_rank", "decision_ref", "prediction_ref",
    "run_id",
]


def build_decision_path_contribution(view: SealedRunView, scores_v2: dict
                                     ) -> tuple[list[dict], list[dict],
                                                dict]:
    by_qid = {q["qid"]: q for q in scores_v2["per_question"]}
    detail: list[dict] = []
    groups: dict[tuple[str, str], list[str]] = {}
    disagreements = []
    for q in view.questions:
        qid = q["qid"]
        art = view.runs[qid]
        group, sub = _mode_group(art)
        groups.setdefault((group, sub), []).append(qid)
        agrees = _mode_agrees(art)
        if not agrees:
            disagreements.append(qid)
        d = art.decision or {}
        p = art.prediction or {}
        detail.append({
            "qid": qid, "input_index": q["input_index"],
            "group": group, "subgroup": sub,
            "decision_mode": d.get("prediction_mode", ""),
            "prediction_mode": p.get("mode", ""),
            "mode_source_agrees": agrees,
            "decision_outcome": d.get("outcome", ""),
            "prediction_outcome": p.get("outcome", ""),
            "agent_rank": by_qid[qid]["agent_rank"],
            "engine_rank": by_qid[qid]["engine_rank"],
            "decision_ref": art.decision_ref,
            "prediction_ref": art.prediction_ref,
            "run_id": art.run_id,
        })
    rows = []
    for key in A3_GROUP_ORDER + [k for k in groups if k not in A3_GROUP_ORDER]:
        qids = groups.get(key, [])
        sub_rows = [by_qid[q] for q in qids]

        def hits(k, arm):
            return sum(1 for r in sub_rows
                       if r[f"{arm}_rank"] is not None and r[f"{arm}_rank"] <= k)

        p1 = Counter(_paired_class(r["agent_rank"], r["engine_rank"], 1)
                     for r in sub_rows)
        p5 = Counter(_paired_class(r["agent_rank"], r["engine_rank"], 5)
                     for r in sub_rows)
        rows.append({
            "group": key[0], "subgroup": key[1], "n_questions": len(qids),
            "agent_hit@1": hits(1, "agent"), "agent_hit@3": hits(3, "agent"),
            "agent_hit@5": hits(5, "agent"),
            "engine_hit@1": hits(1, "engine"),
            "engine_hit@3": hits(3, "engine"),
            "engine_hit@5": hits(5, "engine"),
            "paired@1_both": p1["both"], "paired@1_agent_only": p1["agent_only"],
            "paired@1_engine_only": p1["engine_only"],
            "paired@1_neither": p1["neither"],
            "paired@5_both": p5["both"], "paired@5_agent_only": p5["agent_only"],
            "paired@5_engine_only": p5["engine_only"],
            "paired@5_neither": p5["neither"],
        })
    audits = {
        "n_mode_source_disagreements": len(disagreements),
        "disagreement_qids": disagreements[:20],
        "note": "分组按持久 decision_log(prediction_mode)+ prediction "
                "payload 交叉核对;不以预测 SMILES 倒推模式",
    }
    return rows, detail, audits


# ---------------------------------------------------------------- A4


A4_COLUMNS = [
    "qid", "input_index", "paired_hit5", "agent_rank", "engine_rank",
    "n_predicted", "direction",
    "engine_gold_rank", "agent_reported_sources",
    "agent_selected_evidence_id", "model_order_provided",
    "model_order_len", "unselected_recorded_with_gold",
    "raw_retrieval_gold", "raw_retrieval_gold_refs",
    "task_candidate_gold", "task_candidate_gold_refs",
    "selected_gold", "validated_reportable_gold", "reported_gold",
    "validation_reject_reasons", "decision_mode", "outcome",
    "attribution_primary", "attribution_facts", "attribution_uncertainty",
]


def _agent_reported_sources(art: RunArtifacts) -> str:
    kinds = [a.get("evidence_kind", "") for a in art.adjudications]
    return ";".join(k for k in kinds if k)


def _unselected_recorded_with_gold(art: RunArtifacts,
                                   gold_ids: set[str]) -> str:
    from .domain.identity import cn_identity

    task = art.prediction_task or {}
    selected = ((art.prediction or {}).get("parsed") or {}) \
        .get("selected_evidence_id") or ""
    ids = []
    for c in task.get("candidates", []):
        if c.get("kind") != "recorded_reaction":
            continue
        eid = c.get("evidence_id", "")
        if eid == selected:
            continue
        prods = [p.get("product_smiles", "") for p in c.get("products", [])]
        if any(cn_identity(p) in gold_ids for p in prods):
            ids.append(eid)
    return ";".join(ids)


def _evidence_layers(art: RunArtifacts, gold_ids: set[str]) -> dict:
    """证据五层:原始检索 → 任务候选 → 选中 → 验证可报告 → 最终报告。

    每层独立取证,下层成立不推出上层;引用最多列 5 个 id,可回查封存件。
    """
    from .domain.identity import cn_identity

    ret_refs = []
    for ev in (art.retrieval or {}).get("evidences", []):
        prods = [p.get("product_smiles", "") for p in ev.get("products", [])]
        if any(cn_identity(p) in gold_ids for p in prods):
            ret_refs.append(ev.get("evidence_id", "?"))
    task = art.prediction_task or {}
    cand_refs = []
    for c in task.get("candidates", []):
        if c.get("kind") != "recorded_reaction":
            continue
        prods = [p.get("product_smiles", "") for p in c.get("products", [])]
        if any(cn_identity(p) in gold_ids for p in prods):
            cand_refs.append(c.get("evidence_id", "?"))
    selected = ((art.prediction or {}).get("parsed") or {}) \
        .get("selected_evidence_id") or \
        (art.decision or {}).get("accepted_evidence_id") or ""
    byid = {c.get("evidence_id"): c for c in task.get("candidates", [])}
    selected_gold = any(
        cn_identity(p.get("product_smiles", "")) in gold_ids
        for p in (byid.get(selected, {}).get("products", [])
                  if selected else []))
    if not selected_gold and selected:
        selected_gold = any(
            cn_identity(e.get("product_smiles", "")) in gold_ids
            for a in art.adjudications if a.get("evidence_id") == selected
            for e in a.get("entries", []))
    val_gold = any(
        v.get("accepted") and v.get("product_identity") in gold_ids
        for v0 in art.validations for v in v0.get("verdicts", []))
    reported_gold = any(
        cn_identity(e.get("product_smiles", "")) in gold_ids
        for a in art.adjudications for e in a.get("entries", []))
    return {
        "raw_retrieval_gold": bool(ret_refs),
        "raw_retrieval_gold_refs": ";".join(ret_refs[:5]),
        "task_candidate_gold": bool(cand_refs),
        "task_candidate_gold_refs": ";".join(cand_refs[:5]),
        "selected_gold": bool(selected_gold),
        "validated_reportable_gold": bool(val_gold),
        "reported_gold": bool(reported_gold),
    }


def _validation_reject_reasons(art: RunArtifacts) -> str:
    reasons = []
    for v in art.validations:
        for verdict in v.get("verdicts", []):
            if not verdict.get("accepted"):
                reasons.extend(verdict.get("reasons", []))
    if not reasons:
        p = art.prediction or {}
        checks = p.get("atomtool_checks") or {}
        for name, check in checks.items():
            if isinstance(check, dict) and check.get("ok") is False:
                reasons.append(f"{name}:{check.get('reason', '')}")
        if p.get("fail_reason"):
            reasons.append(str(p["fail_reason"]))
    return _truncate(";".join(str(r) for r in reasons), 300)


def attribute_discordant(view: SealedRunView, qid: str, direction: str,
                         gold_ids: set[str]) -> dict:
    """谨慎归因:证据五层 + 确定性规则 + 事实列 + 不确定列;一题一个主因。

    - "模型选错"仅当模型选择集(任务候选)中存在正确且可选卡、模型却未选;
    - 仅原始检索含金标不构成任何"可报告"断言 → "证据不足以判断";
    - "候选未检出"必须写全限定对象(引擎已导出 Top-10)。
    """
    art = view.runs[qid]
    outcome = art.prediction_outcome or \
        (art.decision or {}).get("outcome", "")
    n_predicted = sum(len(st.get("predicted_products", []))
                      for st in view.merged[qid].get("steps", []))
    facts: list[str] = []
    unc = ""
    mode, _ = _mode_group(art)
    layers = _evidence_layers(art, gold_ids)
    unselected = _unselected_recorded_with_gold(art, gold_ids)

    if direction == "engine_only":
        if n_predicted == 0:
            label = "类比弃答" if outcome == "abstained" else \
                "编辑拒绝" if outcome == "rejected" else "证据不足以判断"
            facts.append(f"empty_answer outcome={outcome} stop="
                         f"{view.worker_status[qid].get('stop_reason', '')}")
        elif layers["selected_gold"]:
            label = "候选虽报告但身份不匹配"
            facts.append("selected_evidence 产物含金标身份但报告候选无一匹配")
        elif layers["task_candidate_gold"]:
            label = "模型选错"
            facts.append(f"任务候选(模型选择集)存在含金标 recorded 卡未选:"
                         f"{unselected}")
        else:
            label = "证据不足以判断"
            if layers["raw_retrieval_gold"]:
                facts.append("原始检索含金标,是否可用未证实(未证明过结构"
                             "门禁/条件/进入任务/可报告)")
            else:
                facts.append("agent 离线可核视图(检索/任务候选)未见金标;"
                             "引擎 Top-10 含金标候选与 agent 视图的对应未核实")
        facts.append(f"layers: raw_retrieval={layers['raw_retrieval_gold']} "
                     f"task_candidate={layers['task_candidate_gold']} "
                     f"selected={layers['selected_gold']} "
                     f"validated={layers['validated_reportable_gold']} "
                     f"reported={layers['reported_gold']}")
        if mode == "recorded_direct":
            unc = "唯一 recorded 直通:其它引擎候选未进入 agent 任务,对应关系未核实"
    else:  # agent_only:引擎已导出 Top-10 未含金标
        label = "候选未检出(引擎已导出 Top-10)"
        facts.append("engine_exported_top10_no_gold")
        facts.append(f"agent_source={_agent_reported_sources(art) or 'unknown'}")
        if layers["raw_retrieval_gold"]:
            facts.append("agent 原始检索卡含金标,是否可用未证实;最终报告"
                         "产物来自模型生成而非该卡")
        unc = "引擎已导出 Top-10 外是否存在金标候选未知(封存件无真实全池)"
    return {
        "unselected_recorded_with_gold": unselected,
        **layers,
        "attribution_primary": label,
        "attribution_facts": _truncate(";".join(facts), 500),
        "attribution_uncertainty": _truncate(unc, 300),
    }


def build_hit5_paired_attribution(view: SealedRunView, scores_v2: dict,
                                  gold_ids_fn) -> tuple[list[dict],
                                                        dict]:
    by_qid = {q["qid"]: q for q in scores_v2["per_question"]}
    rows = []
    counts = Counter()
    for q in view.questions:
        qid = q["qid"]
        sc = by_qid[qid]
        cls = _paired_class(sc["agent_rank"], sc["engine_rank"], 5)
        counts[cls] += 1
        art = view.runs[qid]
        parsed = (art.prediction or {}).get("parsed") or {}
        row = {
            "qid": qid, "input_index": q["input_index"],
            "paired_hit5": cls,
            "agent_rank": sc["agent_rank"], "engine_rank": sc["engine_rank"],
            "n_predicted": sc["n_predicted"],
            "direction": "",
            "engine_gold_rank": "",
            "agent_reported_sources": "",
            "agent_selected_evidence_id": parsed.get("selected_evidence_id", ""),
            "model_order_provided": bool(parsed.get("order")),
            "model_order_len": len(parsed.get("order") or []),
            "unselected_recorded_with_gold": "",
            "raw_retrieval_gold": "", "raw_retrieval_gold_refs": "",
            "task_candidate_gold": "", "task_candidate_gold_refs": "",
            "selected_gold": "", "validated_reportable_gold": "",
            "reported_gold": "",
            "validation_reject_reasons": "",
            "decision_mode": _mode_group(art)[0],
            "outcome": art.prediction_outcome
            or (art.decision or {}).get("outcome", ""),
            "attribution_primary": "", "attribution_facts": "",
            "attribution_uncertainty": "",
        }
        if cls in ("engine_only", "agent_only"):
            row["direction"] = cls
            row["engine_gold_rank"] = sc["engine_rank"]
            row["agent_reported_sources"] = _agent_reported_sources(art)
            row["validation_reject_reasons"] = _validation_reject_reasons(art)
            row.update(attribute_discordant(view, qid, cls, gold_ids_fn(qid)))
        rows.append(row)
    label_counts = Counter(r["attribution_primary"] for r in rows
                           if r["attribution_primary"])
    audits = {
        "paired_hit5_counts": dict(counts),
        "expected_engine_only": 82, "expected_agent_only": 19,
        "label_counts": dict(label_counts),
        "label_vocabulary": list(ATtributionLabels),
        "evidence_layers": EVIDENCE_LAYER_NOTE,
        "note": "主因一题一个,规则确定性且五层证据列可回查;仅原始检索"
                "含金标不推出可报告;不确定时用'证据不足以判断'并保留 "
                "uncertainty",
    }
    return rows, audits


# ---------------------------------------------------------------- A5


A5_COLUMNS = ["qid", "input_index", "engine_rank_v2", "baseline_rank_v41",
              "changed", "note"]


def build_v41_baseline_diff(scores_v2: dict, v41_path: str | Path
                            ) -> tuple[list[dict], dict]:
    v41 = {r["qid"]: r for r in _iter_jsonl(Path(v41_path))}
    rows = []
    changed = 0
    for q in scores_v2["per_question"]:
        old = v41.get(q["qid"], {}).get("baseline_rank")
        new = q["engine_rank"]
        if old != new:
            changed += 1
        rows.append({"qid": q["qid"], "input_index": None,
                     "engine_rank_v2": new, "baseline_rank_v41": old,
                     "changed": old != new, "note": ""})

    def hist(ranks, k):
        return sum(1 for r in ranks if r is not None and r <= k)

    new_ranks = [q["engine_rank"] for q in scores_v2["per_question"]]
    old_ranks = [v41.get(q["qid"], {}).get("baseline_rank")
                 for q in scores_v2["per_question"]]
    summary = {
        "n_questions": len(rows),
        "v2_engine_hit@1/3/5/10": [hist(new_ranks, 1), hist(new_ranks, 3),
                                   hist(new_ranks, 5), hist(new_ranks, 10)],
        "v41_engine_hit@1/3/5/10": [hist(old_ranks, 1), hist(old_ranks, 3),
                                    hist(old_ranks, 5), hist(old_ranks, 10)],
        "n_rank_changed": changed,
        "note": "v41 为历史引擎逐题 baseline_rank,封存判分文件仅记录 ≤5 "
                "的首命中(@1/@3/@5 由该文件核验;@10=208 引用历史 v4.1 "
                "报告/R2,封存件无法离线复算 6–10 位);差异计数按 R2 同法:"
                "v2 首命中 rank(1–10)对 v41 baseline_rank(≤5);两引擎汇总"
                "接近不宣称等价;v41 agent_rank 列不与本表比较",
    }
    return rows, summary


# ---------------------------------------------------------------- A6


A6_COLUMNS = [
    "qid", "input_index", "n_issued", "n_provider_ok", "n_failed",
    "response_files", "request_ids", "orphan_count", "llm_remaining",
    "stop_reason", "run_id",
]


def build_llm_call_distribution(view: SealedRunView) -> tuple[list[dict],
                                                              dict]:
    rows = []
    hist = Counter()
    for q in view.questions:
        qid = q["qid"]
        art = view.runs[qid]
        led = _call_response_ledger(art)
        task = art.prediction_task or {}
        budget = (task.get("budget") or {}).get("llm_remaining")
        issued = led["n_issued"]
        hist[issued] += 1
        rows.append({
            "qid": qid, "input_index": q["input_index"],
            **{k: led[k] for k in ("n_issued", "n_provider_ok", "n_failed",
                                   "response_files", "request_ids",
                                   "orphan_count")},
            "llm_remaining": budget,
            "stop_reason": view.worker_status[qid].get("stop_reason", ""),
            "run_id": art.run_id,
        })
    touch_cap = [r["qid"] for r in rows if r["n_issued"] >= 3]
    summary = {
        "issued_histogram": {str(k): hist[k] for k in sorted(hist)},
        "total_issued": sum(r["n_issued"] for r in rows),
        "total_provider_ok": sum(r["n_provider_ok"] for r in rows),
        "total_failed": sum(r["n_failed"] for r in rows),
        "total_orphans": sum(r["orphan_count"] for r in rows),
        "touch_cap_qids": touch_cap,
        "touch_cap_note": "触顶=issued 达单任务尝试上限 3"
                          "(封存 task budget.llm_remaining 初始为 3;"
                          "无 llm_remaining 归零的题;budget_exhausted 唯一"
                          "一题耗尽的是 worker 预算,3 次调用均有响应)",
        "caliber_note": "issued=prediction_call.*.json(status=issued);"
                        "提供方口径=对应 prediction_response 的 transport "
                        "(ok=200 计成功,其余计失败);本次两口径总数一致;"
                        "调用分布按 qid 统计,不以 191/298 平均替代",
    }
    return rows, summary
