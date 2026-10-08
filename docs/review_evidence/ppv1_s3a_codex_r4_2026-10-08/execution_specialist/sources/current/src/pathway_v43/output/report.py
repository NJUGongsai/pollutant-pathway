"""output/report — pathway.json 研究报告与 inspect 摘要。

报告是**派生视图**:从 PathwayStore + results/ 产物确定性重建,可重复生成
(原子覆盖,不适用 results 的不可变冲突规则)。报告分离「每步 top-5 候选」
(检索证据按 retrieval_rank)与「frontier 展开」(path_instances 状态)。
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from ..domain.models import (
    PATH_STATUS_AWAITING_PREDICTION,
    PATH_STATUS_DEAD_END,
    PATH_STATUS_DEFERRED,
    DOMAIN_SCHEMA_VERSION,
)
from ..domain.pathway import ancestry_chain, display_name

REPORT_SCHEMA_VERSION = "v43-report-1"


def _scan_results(run_dir: Path) -> dict:
    """results/<task_id>/{retrieval,decision,validation,prediction*}.json → 按 path_id 索引。"""
    index: dict[str, dict] = {}
    results_dir = Path(run_dir) / "results"
    if not results_dir.is_dir():
        return index
    for task_dir in sorted(results_dir.iterdir()):
        if not task_dir.is_dir():
            continue
        for name in ("retrieval", "decision", "validation",
                     "prediction_task", "prediction", "report_adjudication"):
            path = task_dir / f"{name}.json"
            if not path.is_file():
                continue
            envelope = json.loads(path.read_text(encoding="utf-8"))
            payload = envelope.get("payload", {})
            pid = None
            if name == "retrieval":
                pid = (payload.get("query") or {}).get("path_id")
            elif name == "prediction_task":
                pid = payload.get("path_id")
            elif name == "prediction":
                pid = payload.get("path_id")
            else:
                pid = payload.get("path_id")
            if pid is None:
                continue
            index.setdefault(pid, {})[name] = {
                "task_id": envelope.get("task_id"),
                "payload": payload,
            }
    return index


def _llm_call_stats(run_dir: Path) -> dict:
    """调用/孤儿统计(持久事实源;跨 attempt 汇总)。"""
    results_dir = Path(run_dir) / "results"
    calls = completed = orphaned = failed = 0
    orphan_records: list[dict] = []
    if results_dir.is_dir():
        for task_dir in sorted(results_dir.iterdir()):
            if not task_dir.is_dir():
                continue
            calls += len(list(task_dir.glob("prediction_call.*.json")))
            completed += len(list(task_dir.glob("prediction_response.*.json")))
            for op in sorted(task_dir.glob("prediction_orphan.*.json")):
                orphaned += 1
                try:
                    orphan_records.append(json.loads(
                        op.read_text(encoding="utf-8")).get("payload", {}))
                except Exception:
                    pass
            for rp in task_dir.glob("prediction_response.*.json"):
                try:
                    payload = json.loads(
                        rp.read_text(encoding="utf-8")).get("payload", {})
                except Exception:
                    continue
                if payload.get("status") == "transport_failed":
                    failed += 1
    return {"n_calls": calls, "n_responses": completed,
            "n_orphaned_calls": orphaned, "n_transport_failures": failed,
            "orphans": orphan_records}


def _top5_candidates(refs: dict) -> list[dict]:
    """路径检索证据的前 5 张卡(按引擎 retrieval_rank;与展开决策分离)。"""
    retrieval = refs.get("retrieval", {}).get("payload")
    if not retrieval:
        return []
    out = []
    for ev in sorted(
        retrieval.get("evidences", []),
        key=lambda e: (e.get("retrieval_rank", 0), e.get("evidence_id", "")),
    )[:5]:
        out.append({
            "evidence_id": ev.get("evidence_id"),
            "source_id": ev.get("source_id"),
            "kind": ev.get("kind"),
            "retrieval_rank": ev.get("retrieval_rank"),
            "products": [
                p.get("product_smiles") for p in ev.get("products", [])[:5]
            ],
        })
    return out


def _adjudication_entries(adj: dict) -> list[dict]:
    """兼容读取:v1 裁决的条目在 ``entries``,v2(Phase B)在 ``products``。"""
    if adj.get("schema_version") == "v43-report-adjudication-2":
        return adj.get("products", [])
    return adj.get("entries", [])


def _top5_reportable_products(refs: dict) -> list[dict]:
    """候选裁决产物 → 已校验可报告 top-5(按 report_rank;与展开分离)。

    这是 `top5_reportable_products` 视图(TASK_V43_EXPORT_DEV §1 /
    TASK_V43_EC298_PHASE_B §4):与 `top5_candidates`(检索卡视图)不同 ——
    只含已通过确定性门禁、被策略接纳为可报告的候选,并显式给出
    expand_selected 与是否已提交(committed_event_ref;v2:仅报告未提交
    候选可报告但不展开)。检索原始卡、模型原文与被拒产品不进本视图;
    草稿产物不进本视图。raw 取值与导出同规则(full 优先,回落 smiles)。
    """
    adj = refs.get("report_adjudication", {}).get("payload")
    if not adj:
        return []
    entries = sorted(
        (e for e in _adjudication_entries(adj) if e.get("reportable")),
        key=lambda e: (e.get("report_rank") or 0))
    out = []
    seen: set[str] = set()
    for e in entries[:5]:
        raw = (e.get("product_smiles_full") or "").strip() \
            or (e.get("product_smiles") or "").strip()
        ident = e.get("cn_identity") or e.get("product_identity") or ""
        if ident and ident in seen:
            continue
        seen.add(ident)
        out.append({
            "report_rank": e.get("report_rank"),
            "product_smiles": raw,
            "product_identity": ident,
            "evidence_id": e.get("evidence_id"),
            "validation_ref": e.get("validation_ref", ""),
            "expand_selected": bool(e.get("expand_selected")),
            "expand_status": e.get("expand_status"),
            "committed_event_ref": e.get("committed_event_ref"),
        })
    return out


def _prediction_view(refs: dict) -> dict:
    """路径的预测分支视图(任务/模式/结果/响应引用;无预测为空 dict)。"""
    task = refs.get("prediction_task", {}).get("payload")
    result = refs.get("prediction", {}).get("payload")
    if task is None and result is None:
        return {}
    view: dict = {}
    if task is not None:
        view.update({
            "task_id": refs.get("prediction_task", {}).get("task_id"),
            "mode": task.get("mode"),
            "model": task.get("model"),
            "input_hash": task.get("input_hash"),
            "ancestry_ids": [s.get("evidence_id")
                             for s in task.get("ancestry", [])],
            "n_candidates": len(task.get("candidates", [])),
        })
    if result is not None:
        view.update({
            "outcome": result.get("outcome"),
            "attempt": result.get("attempt"),
            "fail_reason": result.get("fail_reason") or result.get("reason"),
            "selected_evidence_id": result.get("selected_evidence_id"),
            "order": result.get("order"),
            "reasons": result.get("reasons"),
            "products_smiles": result.get("products_smiles"),
            "atomtool_checks": result.get("atomtool_checks"),
            "model_reason": (result.get("parsed") or {}).get("reason"),
        })
    return view


def build_report(store, run_dir: str | Path, run_id: str,
                 state: dict, stop_reason: str) -> dict:
    run_dir = Path(run_dir)
    results = _scan_results(run_dir)
    paths = store.list_paths(run_id)
    path_records = []
    by_status: dict[str, list] = {}
    for p in paths:
        chain = ancestry_chain(store, p["path_id"])
        name = display_name(chain)
        refs = results.get(p["path_id"], {})
        decision = refs.get("decision", {}).get("payload")
        adj_payload = refs.get("report_adjudication", {}).get("payload")
        adj_entries = _adjudication_entries(adj_payload) if adj_payload else []
        top5_reportable = _top5_reportable_products(refs)
        # 报告宽度与展开宽度分列(Phase B §4:不把报告宽度说成展开宽度)
        report_counts = {
            "n_reported": sum(1 for e in adj_entries if e.get("reportable")),
            "n_committed": sum(
                1 for e in adj_entries if e.get("committed_event_ref")),
            "n_report_only": sum(
                1 for e in adj_entries
                if e.get("reportable")
                and e.get("committed_event_ref") is None),
            "n_expand_selected": sum(
                1 for e in adj_entries if e.get("expand_selected")),
            "source_kinds": sorted({
                (e.get("card_kind") or (adj_payload or {}).get("evidence_kind")
                 or "unknown")
                for e in adj_entries if e.get("reportable")}),
        }
        record = {
            "path_id": p["path_id"],
            "display_name": name,
            "depth": p["depth"],
            "status": p["status"],
            "status_reason": p["status_reason"],
            "substrate_identity": p["substrate_identity"],
            "parent_path_id": p["parent_path_id"],
            "event_id": p["event_id"],
            "product_position": p["product_position"],
            "seq": p["seq"],
            "ancestry": [
                {"display_name": display_name(chain[: i + 1]),
                 "path_id": c.path_id, "substrate_identity": c.substrate_identity}
                for i, c in enumerate(chain)
            ],
            "evidence": {
                "decision_outcome": decision.get("outcome"),
                "decision_reason": decision.get("reason"),
                "considered": decision.get("considered", []),
            } if decision else {},
            # 预测分支引用(任务书 §4:任务/响应/解析结果可审计)
            "prediction": _prediction_view(refs),
            # 每步 top-5 候选报告(与 frontier 展开分离;待预测/死端路径同样输出)
            "top5_candidates": _top5_candidates(refs),
            # 已校验可报告 top-5(候选裁决产物视图;与检索卡视图分离)
            "top5_reportable_products": top5_reportable,
            # 报告/提交/仅报告/展开计数与来源等级(Phase B §4)
            "report": report_counts,
            "adjudication": {
                "schema_version": (adj_payload or {}).get("schema_version"),
                "stage": (adj_payload or {}).get("stage"),
                "rank_basis": (adj_payload or {}).get("rank_basis"),
                "task_id": refs.get("report_adjudication", {}).get("task_id"),
            },
            "report_adjudication_task_id":
                refs.get("report_adjudication", {}).get("task_id"),
            "retrieval_task_id": refs.get("retrieval", {}).get("task_id"),
            "validation_task_id": refs.get("validation", {}).get("task_id"),
        }
        path_records.append(record)
        by_status.setdefault(p["status"], []).append(record)

    events = []
    for ev in store.events(run_id):
        products = store.event_products(ev["event_id"])
        events.append({
            "event_id": ev["event_id"],
            "parent_path_id": ev["parent_path_id"],
            "substrate_identity": ev["substrate_identity"],
            "evidence_id": ev["evidence_id"],
            "source_id": ev["source_id"],
            "kind": ev["kind"],
            "condition_fit": ev["condition_fit"],
            "model_ref": ev.get("model_ref", ""),
            "products": [
                {"position": pr["position"],
                 "product_identity": pr["product_identity"],
                 "product_smiles": pr["product_smiles"],
                 "product_smiles_full": pr["product_smiles_full"]}
                for pr in products
            ],
            "created_at": ev["created_at"],
        })

    compounds = []
    row = store.conn.execute(
        "SELECT cn, example_smiles, first_path_id FROM compounds ORDER BY rowid"
    ).fetchall()
    for r in row:
        compounds.append(dict(r))

    budget = dict(state.get("budget", {}))
    llm_stats = _llm_call_stats(run_dir)
    n_proposal_events = sum(1 for e in events
                            if e.get("kind") == "novel_proposal")
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "domain_schema_version": DOMAIN_SCHEMA_VERSION,
        "run_id": run_id,
        "stop_reason": stop_reason,
        "phase": state.get("phase", ""),
        "error": state.get("error", {}),
        "inputs": {"root_smiles": state.get("root_smiles"),
                   "root_identity": state.get("root_cn")},
        "strategy": {"version": state.get("strategy_version", ""),
                     **{k: budget.get(k) for k in
                        ("max_depth", "max_expansions", "max_frontier_width",
                         "max_llm_calls", "max_proposals")}},
        "budget": budget,
        "llm_calls": llm_stats,
        "graph_revision": store.graph_revision(),
        "counts": store.counts(),
        "compounds": compounds,
        "reaction_events": events,
        "path_instances": path_records,
        "paths_by_status": {k: [p["path_id"] for p in v]
                            for k, v in sorted(by_status.items())},
        "summary": {
            "n_paths": len(path_records),
            "n_events": len(events),
            "n_awaiting_prediction": len(by_status.get(
                PATH_STATUS_AWAITING_PREDICTION, [])),
            "n_dead_end": len(by_status.get(PATH_STATUS_DEAD_END, [])),
            "n_deferred": len(by_status.get(PATH_STATUS_DEFERRED, [])),
            "n_prediction_tasks": sum(
                1 for p in path_records if p.get("prediction", {}).get("task_id")),
            "n_proposal_events": n_proposal_events,
            "llm_calls": {k: v for k, v in llm_stats.items() if k != "orphans"},
            "top5_reported_events": [
                {"event_id": e["event_id"],
                 "top5": [p["product_smiles"] for p in e["products"][:5]]}
                for e in events
            ],
            "top5_reported_paths": [
                {"display_name": p["display_name"], "status": p["status"],
                 "top5": p["top5_candidates"]}
                for p in path_records if p["top5_candidates"]
            ],
            # 已报告 top-5 与实际展开数量(任务书 §4 诊断列:两视图分离)
            "top5_reportable_paths": [
                {"display_name": p["display_name"], "status": p["status"],
                 "top5_reportable": p["top5_reportable_products"],
                 "n_reportable": len(p["top5_reportable_products"]),
                 "n_expand_selected": sum(
                     1 for e in p["top5_reportable_products"]
                     if e["expand_selected"])}
                for p in path_records if p["top5_reportable_products"]
            ],
            # 六层诊断合计(原始检索→任务候选→通过验证→可报告→已提交→
            # 已展开的下游四层;检索/候选层由逐路径 report/counts 细节给出)
            "report_vs_expansion": {
                "n_reported": sum(
                    p["report"]["n_reported"] for p in path_records),
                "n_committed": sum(
                    p["report"]["n_committed"] for p in path_records),
                "n_report_only": sum(
                    p["report"]["n_report_only"] for p in path_records),
                "n_expand_selected": sum(
                    p["report"]["n_expand_selected"] for p in path_records),
                "n_frontier_paths": len(by_status.get("frontier", [])),
            },
        },
    }


def write_report(store, run_dir: str | Path, run_id: str, state: dict,
                 stop_reason: str) -> Path:
    report = build_report(store, run_dir, run_id, state, stop_reason)
    path = Path(run_dir) / "report" / "pathway.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(tmp, path)
    return path


def inspect_payload(runs_root: str | Path, run_id: str) -> dict:
    """inspect 摘要:区分 完成/预算耗尽/待预测/异常停止/无报告。"""
    runs_dir = Path(runs_root) / run_id
    report_path = runs_dir / "report" / "pathway.json"
    if not report_path.is_file():
        return {
            "run_id": run_id,
            "exists": (runs_root and runs_dir.is_dir()),
            "status": "no_report_yet",
            "note": "无 pathway.json:run 中断或尚未导出",
        }
    report = json.loads(report_path.read_text(encoding="utf-8"))
    status = report.get("stop_reason", "")
    classification = {
        "completed": "completed",
        "budget_exhausted": "budget_exhausted",
        "awaiting_prediction": "awaiting_prediction",
        "invalid_input": "abnormal_stop",
    }.get(status, "abnormal_stop" if report.get("error") else status or "unknown")
    return {
        "run_id": run_id,
        "status": classification,
        "stop_reason": status,
        "phase": report.get("phase"),
        "graph_revision": report.get("graph_revision"),
        "counts": report.get("counts"),
        "summary": report.get("summary"),
        "paths": [
            {"display_name": p["display_name"], "status": p["status"],
             "substrate_identity": p["substrate_identity"],
             "status_reason": p["status_reason"]}
            for p in report.get("path_instances", [])
        ],
        "report_path": str(report_path),
    }
