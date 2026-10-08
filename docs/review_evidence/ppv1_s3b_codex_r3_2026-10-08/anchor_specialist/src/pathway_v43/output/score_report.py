"""冻结评测器只读接线与 dev 对照诊断(零 LLM;TASK_V43_EXPORT_DEV §4)。

- ``run_frozen_evaluator``:**只读调用** v3 冻结评测器
  ``evaluation/pathway_benchmark/eval_pathway_benchmark.py`` 子进程,
  ``--split dev --per-route``;不修改 v3 金标/评测器/切分,不另写
  "等价判分"。评测 JSON 原样保留;报告的 ``split`` 字段核对不符即拒绝
  (评测器默认 split=eval,误用即结构化失败,不静默产出 eval 数字)。
- ``diagnose_routes``:描述性诊断 —— 失分类型(候选未生成 / 检索池在
  但未提交 / 被门禁拒绝 / 模型弃权 / 提交但超出 top-5 / 父路径未展开 /
  预算停止)、来源构成(recorded/rule/analog/novel)、深度与停止原因、
  已报告 top-5 与实际展开数量。全部注明"v4.3 账本描述性切片,非冻结
  评测器原生指标"。
- ``retrieval_pool_diagnostic_hit``:gold 产物出现在检索卡池(top-5 /
  全池)的**诊断指标**,与答卷正式分数严格分开命名,不混入路径得分。
- 历史对照(同 dev 20 路、同冻结评测器、相同口径)由外部把历史答卷
  传入 ``score_predictions_file``;输入/配置口径不同时只并列、不补造。

读取 dev 金标仅发生在判分后的诊断层(评测器与失分归因),绝不进入
run 侧输入、提示词或检索查询。
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

DIAG_SCHEMA_VERSION = "v43-dev-diag-1"

# 失分类型(任务书 §4 指定的归因词表)
LOSS_BUCKETS = [
    "parent_never_reached",       # 父分子不在任何已到达路径上
    "parent_not_expanded",        # 父路径存在但未展开(含模型弃权/深度/待预测)
    "candidate_not_generated",    # 检索池中没有该 gold 产物
    "retrieved_not_committed",    # 检索池有,但未成为已提交产物(细分见下)
    "gate_rejected",              # 提交候选被校验门禁拒绝
    "model_not_committed",        # 模型裁决/弃权/失败导致未提交
    "committed_beyond_top5",      # 已提交但导出排名在 cap 之外
    "budget_stop",                # run 因预算停止,父路径停在 frontier
    "unclassified",
]


class EvaluatorRefusal(RuntimeError):
    """评测器调用被拒绝(切分不符/身份不符;fail-closed)。"""


def run_frozen_evaluator(
    v3_root: str | Path,
    predictions_path: str | Path,
    out_path: str | Path,
    *,
    split: str = "dev",
    python_exe: str | None = None,
    allow_missing: bool = False,
) -> dict:
    """只读执行 v3 冻结评测器;返回原始报告 JSON(原样保留)。

    ``allow_missing``:仅历史基线答卷允许缺行(缺行如实标注、按空计分);
    v4.3 主答卷恒为 False(归并层保证 20 行齐全)。"""
    if split != "dev":
        raise EvaluatorRefusal(
            f"本阶段仅允许 dev 切分(收到 {split});eval 为 run-once 冻结切片,"
            "不在本轮范围", {"split": split})
    script = (Path(v3_root) / "evaluation" / "pathway_benchmark"
              / "eval_pathway_benchmark.py")
    if not script.is_file():
        raise EvaluatorRefusal(f"v3 冻结评测器不存在:{script}",
                               {"path": str(script)})
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        python_exe or sys.executable, str(script),
        "--predictions", str(predictions_path),
        "--split", split, "--out", str(out_path), "--per-route",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise EvaluatorRefusal(
            f"冻结评测器退出码 {proc.returncode}:{proc.stderr[-500:]}",
            {"cmd": cmd[:2] + ["..."], "stderr_tail": proc.stderr[-500:]})
    report = json.loads(out_path.read_text(encoding="utf-8"))
    if report.get("split") != split:
        raise EvaluatorRefusal(
            "评测器报告 split 与请求不符(拒绝过账)",
            {"report_split": report.get("split"), "requested": split})
    if report.get("n_routes") != 20:
        raise EvaluatorRefusal(
            f"dev 切分应评 20 条路线,评测器报告 {report.get('n_routes')}",
            {"n_routes": report.get("n_routes")})
    if report.get("missing_predictions") and not allow_missing:
        raise EvaluatorRefusal(
            "评测器报告缺行(归并层应保证 20 行齐全)",
            {"missing": report["missing_predictions"][:5]})
    return report


# ---------------------------------------------------------------- 诊断


def _scan_results(run_dir: Path) -> dict:
    from .report import _scan_results as scan

    return scan(run_dir)


def _load_gold_dev(v3_root: str | Path) -> dict[str, dict]:
    manifest = json.loads((
        Path(v3_root) / "evaluation" / "pathway_benchmark"
        / "split_manifest.json").read_text(encoding="utf-8"))
    dev_ids = set(manifest["split"]["dev"])
    gold: dict[str, dict] = {}
    with open(Path(v3_root) / "evaluation" / "pathway_benchmark"
              / "gold_routes.jsonl", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            if rec["route_id"] in dev_ids:
                gold[rec["route_id"]] = rec
    return gold


def _emitted_rank_by_parent(pred_line: dict) -> dict[str, list[str]]:
    """评测器同语义的 parent→有序产物身份投影(诊断用;按 cn 身份)。"""
    from ..domain.identity import cn_identity

    by_parent: dict[str, list[str]] = {}
    for step in pred_line.get("steps", []):
        pid = cn_identity(step.get("parent_smiles") or "")
        if pid is None:
            continue
        lst = by_parent.setdefault(pid, [])
        for smi in step.get("predicted_products", []):
            q = cn_identity(smi or "")
            if q is not None and q not in lst:
                lst.append(q)
    return by_parent


def diagnose_route(gold_route: dict, pred_line: dict | None,
                   run_dir: Path) -> dict:
    """单路线失分归因 + 来源/深度/top-5 诊断(描述性;注明非评测器原生)。"""
    from ..domain.identity import cn_identity

    diag: dict = {
        "route_id": gold_route["route_id"],
        "diagnostic_kind": "v43_ledger_descriptive_not_frozen_evaluator_slice",
    }
    refs = _scan_results(run_dir)
    report_path = run_dir / "report" / "pathway.json"
    report = (json.loads(report_path.read_text(encoding="utf-8"))
              if report_path.is_file() else {})

    # ---- 来源构成 / 深度 / 停止原因 / 展开与 top-5 数量 ----
    events = report.get("reaction_events") or []
    kinds: dict[str, int] = {}
    for ev in events:
        kinds[ev.get("kind") or "?"] = kinds.get(ev.get("kind") or "?", 0) + 1
    n_retrievals = sum(
        1 for task in (run_dir / "results").glob("*/retrieval.json")
    ) if (run_dir / "results").is_dir() else 0
    diag["source_mix_events"] = kinds
    diag["n_committed_events"] = len(events)
    diag["n_expansions_retrieval_tasks"] = n_retrievals
    diag["stop_reason"] = report.get("stop_reason", "")
    diag["max_depth_reached"] = max(
        (p.get("depth", 0) for p in report.get("path_instances", [])),
        default=0)
    diag["n_top5_reported_paths"] = len(
        report.get("summary", {}).get("top5_reported_paths") or [])
    diag["llm_calls"] = report.get("summary", {}).get("llm_calls", {})

    if pred_line is None:
        pred_line = {}
    emitted = _emitted_rank_by_parent(pred_line)

    # 路径实例索引:身份 → [path records];path_id → record
    path_records = report.get("path_instances") or []
    paths_by_identity: dict[str, list[dict]] = {}
    for p in path_records:
        paths_by_identity.setdefault(p["substrate_identity"], []).append(p)

    # 事件产物(已提交事实):身份 → 该父全部事件有序产物身份
    committed_products: dict[str, list[str]] = {}
    for ev in events:
        parent_cn = next(
            (p["substrate_identity"] for p in path_records
             if p["path_id"] == ev["parent_path_id"]), None)
        if parent_cn is None:
            continue
        lst = committed_products.setdefault(parent_cn, [])
        for prod in ev.get("products", []):
            if prod["product_identity"] not in lst:
                lst.append(prod["product_identity"])

    # 门禁拒绝集合:validation verdicts 中 rejected 的产物身份
    rejected_ids: set[str] = set()
    for pid, r in refs.items():
        v = r.get("validation", {}).get("payload")
        if not v:
            continue
        for verdict in v.get("verdicts", []):
            if not verdict.get("accepted"):
                # verdict 只有 position;对应产物身份从 retrieval 卡反查
                retrieval = r.get("retrieval", {}).get("payload") or {}
                chosen = v.get("evidence_id")
                for ev in retrieval.get("evidences", []):
                    if ev["evidence_id"] != chosen:
                        continue
                    for prod in ev.get("products", []):
                        if prod.get("position") == verdict.get("position"):
                            if prod.get("product_identity"):
                                rejected_ids.add(prod["product_identity"])

    # 检索池(gold 产物是否在检索卡中):诊断指标,不混入正式分数
    pool_top5: dict[str, bool] = {}
    pool_all: dict[str, bool] = {}
    for p in path_records:
        retrieval = (refs.get(p["path_id"], {}).get("retrieval") or {}).get(
            "payload") or {}
        products = []
        for ev in retrieval.get("evidences", []):
            for prod in ev.get("products", []):
                ident = prod.get("product_identity") or cn_identity(
                    prod.get("product_smiles_full")
                    or prod.get("product_smiles") or "")
                if ident:
                    products.append(ident)
        products = list(dict.fromkeys(products))
        pool_all[p["substrate_identity"]] = pool_all.get(
            p["substrate_identity"], False)
        for ident in products:
            pool_all[ident] = True
        for ident in products[:5]:
            pool_top5[ident] = True

    # ---- 失分归因(逐条 gold 边) ----
    losses: list[dict] = []
    for edge in gold_route.get("edges", []):
        p_cn, q_cn = edge["parent_cn"], edge["product_cn"]
        if q_cn in emitted.get(p_cn, []):
            continue  # 命中,不归因
        bucket = "unclassified"
        detail = ""
        if p_cn not in paths_by_identity:
            bucket = "parent_never_reached"
        else:
            statuses = {p["status"] for p in paths_by_identity[p_cn]}
            expanded = [p for p in paths_by_identity[p_cn]
                        if p["status"] == "expanded"]
            if q_cn in committed_products.get(p_cn, []):
                rank = (emitted.get(p_cn, []).index(q_cn) + 1
                        if q_cn in emitted.get(p_cn, []) else None)
                if rank is None or rank > 5:
                    bucket = "committed_beyond_top5"
                    detail = f"emitted_rank={rank}"
                else:
                    bucket = "unclassified"
                    detail = f"committed_and_emitted_rank={rank} but not hit?"
            elif not expanded:
                if statuses & {"frontier"}:
                    bucket = "budget_stop"
                else:
                    bucket = "parent_not_expanded"
                reason = next(
                    (p.get("status_reason", "")
                     for p in paths_by_identity[p_cn] if p.get("status_reason")),
                    "")
                detail = f"statuses={sorted(statuses)};{reason[:120]}"
            elif q_cn in rejected_ids:
                bucket = "gate_rejected"
            elif pool_all.get(q_cn):
                bucket = "retrieved_not_committed"
                if pool_top5.get(q_cn):
                    detail = "in_retrieval_top5_of_some_path"
            else:
                bucket = "candidate_not_generated"
        losses.append({"parent_cn": p_cn, "product_cn": q_cn,
                       "bucket": bucket, "detail": detail[:200]})
    counts: dict[str, int] = {}
    for l in losses:
        counts[l["bucket"]] = counts.get(l["bucket"], 0) + 1
    diag["missed_gold_edges"] = {
        "n_total": len(gold_route.get("edges", [])),
        "n_missed": len(losses),
        "buckets": {k: counts[k] for k in sorted(counts)},
        "losses": losses,
    }
    # 检索池诊断命中率(单独命名,不混入路径正式分数)
    hits5 = hits_all = 0
    for edge in gold_route.get("edges", []):
        if pool_top5.get(edge["product_cn"]):
            hits5 += 1
        if pool_all.get(edge["product_cn"]):
            hits_all += 1
    n_edges = len(gold_route.get("edges", []))
    diag["retrieval_pool_diagnostic_hit"] = {
        "note": ("diagnostic only: gold product present in retrieval card "
                 "pool; NOT part of the frozen evaluator's pathway score"),
        "top5_of_any_path": {"hits": hits5, "n": n_edges},
        "any_rank_of_any_path": {"hits": hits_all, "n": n_edges},
    }
    return diag


def build_dev_diagnostic_report(
    *, eval_report: dict, v3_root: str | Path, runs_root: Path,
    route_run_ids: dict[str, str], merged_meta: dict,
    api_account_data: dict | None = None,
) -> dict:
    """判分后诊断汇总:逐路线失分归因 + 描述性切片(不冒充评测器指标)。"""
    gold = _load_gold_dev(v3_root)
    pred_lines: dict[str, dict] = {}
    for route_id, run_id in route_run_ids.items():
        p = Path(runs_root) / run_id / "predictions.jsonl"
        if p.is_file():
            pred_lines[route_id] = json.loads(
                p.read_text(encoding="utf-8"))
    per_route = {}
    for route_id, gold_route in sorted(gold.items()):
        run_dir = Path(runs_root) / route_run_ids[route_id]
        per_route[route_id] = diagnose_route(
            gold_route, pred_lines.get(route_id), run_dir)
    return {
        "schema_version": DIAG_SCHEMA_VERSION,
        "eval_report_ref": {
            "split": eval_report.get("split"),
            "n_routes": eval_report.get("n_routes"),
        },
        "merged_predictions": {
            "sha256": merged_meta.get("predictions_sha256"),
            "n_lines": merged_meta.get("n_lines"),
        },
        "per_route": per_route,
        "api_account": api_account_data,
    }


def score_predictions_file(
    *, predictions_path: str | Path, out_dir: str | Path,
    v3_root: str | Path, label: str,
) -> dict:
    """对任一 v3 格式答卷(含历史基线)以同一冻结评测器判分(dev 口径)。

    历史答卷与 v4.3 答卷同评测器同切分,数字方可并列;配置口径差异
    由调用方在报告中声明,本函数只保证"同评测器 + 同 split"。"""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"eval_{label}.json"
    report = run_frozen_evaluator(v3_root, predictions_path, out, split="dev")
    return {"label": label, "path": str(out), "report": report}
