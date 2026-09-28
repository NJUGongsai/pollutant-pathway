#!/usr/bin/env python
"""EC298 Phase B 离线结构诊断(无金标、零 LLM)。

对任意 run 目录按层统计(TASK_V43_EC298_PHASE_B §6 六层口径):

    原始检索 → 任务候选 → 通过验证 → 可报告 → 已提交 → 已展开

- 每父检索卡数 / 任务候选数 / 逐卡过门禁数 / 可报告宽度 / 已提交数 /
  已展开数 / 拒因分布 / 来源等级;
- schema 显式分派:v2 裁决给出全部六层;v1(旧 run)只能按旧口径读
  (仅选中卡过验证,无逐卡层),如实标注 `null`,不得把旧产物套新排序
  声称新版表现;
- 只读运行产物与账本;金标与评测器不进入本脚本;输出不含任何凭证。

用法:
    python scripts/phase_b_offline_diagnostics.py \
        --run-dir runs/<id> [--run-dir runs/<id2> ...] \
        [--out reports/ec298/phase_b/diagnostics.json]
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from pathway_v43.domain.models import content_hash  # noqa: E402

V2_SCHEMA = "v43-report-adjudication-2"
V1_SCHEMA = "v43-report-adjudication-1"


def _read_envelope(path: Path) -> dict | None:
    if not path.is_file():
        return None
    envelope = json.loads(path.read_text(encoding="utf-8"))
    payload = envelope.get("payload", {})
    stored = envelope.get("payload_hash")
    if stored and stored != content_hash(payload):
        raise SystemExit(f"产物哈希不符(损坏或被篡改):{path}")
    return payload


def _reason_key(reasons: list) -> str:
    for r in reasons or []:
        text = str(r)
        if ":" in text:
            return text.split(":", 1)[0]
        if text:
            return text[:40]
    return ""


def _ledger_facts(run_dir: Path) -> dict:
    db = run_dir / "pathway.sqlite"
    if not db.is_file():
        return {}
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        paths = [dict(r) for r in conn.execute(
            "SELECT * FROM path_instances ORDER BY seq").fetchall()]
        events = [dict(r) for r in conn.execute(
            "SELECT * FROM reaction_events").fetchall()]
        statuses: dict[str, dict] = {}
        for p in paths:
            parent = p.get("parent_path_id")
            if parent:
                agg = statuses.setdefault(parent, {"frontier": 0,
                                                   "expanded": 0,
                                                   "deferred": 0,
                                                   "other": 0})
                st = p.get("status", "")
                key = st if st in ("frontier", "expanded", "deferred") \
                    else "other"
                agg[key] += 1
        return {"n_paths": len(paths), "n_events": len(events),
                "product_path_status_by_parent": statuses}
    finally:
        conn.close()


def _diagnose_run(run_dir: Path) -> dict:
    results = run_dir / "results"
    identity_path = run_dir / "run_identity.json"
    out: dict = {
        "run_id": run_dir.name,
        "schema": None,
        "n_parents_with_adjudication": 0,
        "layers": {
            "n_retrieval_cards": 0, "n_task_candidates": 0,
            "n_cards_gate_passed": 0, "n_reported": 0,
            "n_committed": 0, "n_expanded": 0,
        },
        "reason_distribution": {},
        "source_levels_reported": {},
        "parents": [],
    }
    if identity_path.is_file():
        identity = json.loads(identity_path.read_text(encoding="utf-8"))
        out["root_smiles"] = (identity.get("inputs") or {}).get("root_smiles")
        out["strategy"] = identity.get("strategy")
    if not results.is_dir():
        out["note"] = "no results dir"
        return out

    per_path: dict[str, dict] = {}

    def row(pid: str) -> dict:
        return per_path.setdefault(pid, {
            "path_id": pid, "n_retrieval_cards": None,
            "n_task_candidates": None, "n_cards_gate_passed": None,
            "n_in_task": 0, "n_in_model_order": 0, "n_selected": 0,
            "n_task_not_in_order": 0,
            "n_reported": 0, "n_committed": 0, "n_expanded": 0,
            "card_kinds": {}, "reasons": {}, "schema": None, "stage": None,
        })

    for task_dir in sorted(results.iterdir()):
        retrieval = _read_envelope(task_dir / "retrieval.json")
        if retrieval is not None:
            pid = (retrieval.get("query") or {}).get("path_id")
            if pid:
                r = row(pid)
                n = len(retrieval.get("evidences", []))
                r["n_retrieval_cards"] = (r["n_retrieval_cards"] or 0) + n
        pred_task = _read_envelope(task_dir / "prediction_task.json")
        if pred_task is not None:
            pid = pred_task.get("path_id")
            if pid:
                r = row(pid)
                r["n_task_candidates"] = (r["n_task_candidates"] or 0) + len(
                    pred_task.get("candidates", []))
        adj = _read_envelope(task_dir / "report_adjudication.json")
        if adj is not None:
            schema = adj.get("schema_version")
            pid = adj.get("path_id")
            r = row(pid)
            r["schema"] = schema
            r["stage"] = adj.get("stage")
            out["schema"] = out["schema"] or schema
            if out["schema"] != schema:
                out["schema"] = f"mixed:{out['schema']}+{schema}"
            out["n_parents_with_adjudication"] += 1
            if schema == V2_SCHEMA:
                for card in adj.get("cards", []):
                    kind = card.get("kind") or "unknown"
                    ck = r["card_kinds"].setdefault(kind,
                                                    {"n_cards": 0,
                                                     "n_eligible": 0})
                    ck["n_cards"] += 1
                    if card.get("card_eligible"):
                        ck["n_eligible"] += 1
                # R1 修复:化学门禁通过数只看 card_eligible(模型排序出现
                # 本身不是门禁);任务/排序/选中层各自单独计数
                r["n_in_task"] = sum(1 for c in adj.get("cards", [])
                                     if c.get("in_task"))
                r["n_in_model_order"] = sum(
                    1 for c in adj.get("cards", [])
                    if c.get("in_model_order",
                             c.get("in_model_selection_set")))
                r["n_selected"] = sum(1 for c in adj.get("cards", [])
                                      if c.get("selected"))
                r["n_task_not_in_order"] = sum(
                    1 for c in adj.get("cards", [])
                    if c.get("in_task") and not c.get(
                        "in_model_order", c.get("in_model_selection_set")))
                r["n_cards_gate_passed"] = sum(
                    1 for c in adj.get("cards", []) if c.get("card_eligible"))
                for prod in adj.get("products", []):
                    if prod.get("reportable"):
                        r["n_reported"] += 1
                        kind = prod.get("card_kind") or "unknown"
                        out["source_levels_reported"][kind] = \
                            out["source_levels_reported"].get(kind, 0) + 1
                    if prod.get("committed_event_ref") is not None:
                        r["n_committed"] += 1
                    if prod.get("expand_selected"):
                        r["n_expanded"] += 1
                    for key in (_reason_key(prod.get("reasons")),
                                _reason_key([prod["dedup_reason"]])
                                if prod.get("dedup_reason") else ""):
                        if key:
                            out["reason_distribution"][key] = \
                                out["reason_distribution"].get(key, 0) + 1
            elif schema == V1_SCHEMA:
                # 旧口径:仅选中卡有验证;逐卡层不存在,如实 null
                for entry in adj.get("entries", []):
                    if entry.get("reportable"):
                        r["n_reported"] += 1
                    if entry.get("expand_selected"):
                        r["n_expanded"] += 1
                    for key in [_reason_key(entry.get("verdict_reasons"))]:
                        if key:
                            out["reason_distribution"][key] = \
                                out["reason_distribution"].get(key, 0) + 1

    ledger = _ledger_facts(run_dir)
    parents = [r for r in per_path.values()]
    for r in parents:
        st = (ledger.get("product_path_status_by_parent") or {}).get(
            r["path_id"])
        if st:
            r["n_expanded_ledger_frontier_or_expanded"] = (
                st["frontier"] + st["expanded"])
    for key in ("n_retrieval_cards", "n_task_candidates",
                "n_cards_gate_passed", "n_in_task", "n_in_model_order",
                "n_selected", "n_task_not_in_order",
                "n_reported", "n_committed", "n_expanded"):
        out["layers"][key] = sum(
            r[key] for r in parents if isinstance(r.get(key), int))
    out["parents"] = sorted(parents, key=lambda r: r["path_id"])
    out["ledger"] = {k: v for k, v in ledger.items()
                     if k != "product_path_status_by_parent"}
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run-dir", action="append", required=True)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    report = {
        "diagnostic": "phase_b_offline_structure",
        "gold_free": True,
        "llm_calls": 0,
        "runs": [_diagnose_run(Path(p).expanduser().resolve())
                 for p in args.run_dir],
    }
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
