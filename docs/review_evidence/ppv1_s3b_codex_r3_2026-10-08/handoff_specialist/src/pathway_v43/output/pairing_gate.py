"""配对评分完整性门禁(R1-c;任务书 §4.3)。

发布型配对结论的前置校验:**先校验完整性、再读答卷**。校验事实源
独立于被审查的汇总字段 —— 不信 ``batch_report.json`` 的 ``status``
(r1 四臂全部无条件写 ``completed`` 而实际 52 条路线异常失败的事故
形状),逐条重读 worker 终态状态文件与归并元数据:

1. 冻结输入清单存在、白名单声明完整、route_order 恰为预期集合;
2. 批次身份自洽(重算 identity 体哈希 == 记录 sha256);
3. 逐路线 worker 状态分类:异常失败/导出失败/缺失 → 违规;
   合法停留(awaiting_prediction/budget_exhausted)不是违规;
4. 归并元数据:行数/唯一 route_id 集与清单一致、失败标志与逐路线
   分类一致;
5. 逐路线答卷 SHA(元数据记录 vs 答卷文件实算)一致;
6. 归并 predictions.jsonl 逐行 route_id 唯一且恰为清单集合。

任一臂不完整 → ``diagnostic_incomplete``(可出部分诊断,不可发布);
全臂完整 → ``complete``。``release_eligible`` 仅在 complete 时为真。
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ..batch import classify_route_state
from ..domain.models import canonical_json

PAIRING_GATE_SCHEMA = "v43-pairing-gate-1"


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_arm(batch_root: str | Path, *,
                 expected_route_ids: list[str] | None = None) -> dict:
    """单臂完整性校验(只读)。返回机器可读结果,不抛业务异常。"""
    root = Path(batch_root)
    violations: list[dict] = []

    def _v(code: str, detail: dict) -> None:
        violations.append({"code": code, **detail})

    # ---- 1. 冻结输入清单 ----
    manifest_path = root / "input_manifest.json"
    manifest: dict = {}
    if not manifest_path.is_file():
        _v("input_manifest_missing", {"path": str(manifest_path)})
    else:
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception as exc:
            _v("input_manifest_unreadable", {"error": str(exc)[:200]})
        else:
            if manifest.get("kind") != "batch_input_manifest" \
                    or not manifest.get("gold_fields_excluded"):
                _v("input_manifest_bad_shape",
                   {"kind": manifest.get("kind", "")})
            order = list(manifest.get("route_order") or [])
            if expected_route_ids is not None and order != list(
                    expected_route_ids):
                _v("route_order_mismatch",
                   {"expected_n": len(expected_route_ids),
                    "actual_n": len(order),
                    "missing": sorted(set(expected_route_ids) - set(order)),
                    "extra": sorted(set(order) - set(expected_route_ids))})
            if len(set(order)) != len(order):
                _v("route_order_duplicates", {})

    # ---- 2. 批次身份自洽 ----
    identity_path = root / "batch_identity.json"
    identity: dict = {}
    if not identity_path.is_file():
        _v("batch_identity_missing", {})
    else:
        try:
            identity = json.loads(identity_path.read_text(encoding="utf-8"))
            body = identity.get("identity") or {}
            recomputed = hashlib.sha256(
                canonical_json(body).encode("utf-8")).hexdigest()
            if not body or recomputed != identity.get("sha256"):
                _v("batch_identity_hash_mismatch",
                   {"recorded": (identity.get("sha256") or "")[:16],
                    "recomputed": recomputed[:16]})
        except Exception as exc:
            _v("batch_identity_unreadable", {"error": str(exc)[:200]})

    # ---- 3. 逐路线 worker 终态分类(独立事实源) ----
    route_ids = list(manifest.get("route_order") or
                     (expected_route_ids or []))
    route_states: dict[str, dict] = {}
    for rid in route_ids:
        sp = root / "workers" / f"{rid}.status.json"
        status: dict = {}
        if sp.is_file():
            try:
                status = json.loads(sp.read_text(encoding="utf-8"))
            except Exception:
                status = {}
        route_states[rid] = classify_route_state(status or None)
    for rid, st in route_states.items():
        if st["route_state"] == "failed":
            _v("route_failed", {"route_id": rid,
                                "failure_class": st["failure_class"]})
        elif st["route_state"] == "export_failed":
            _v("route_export_failed", {"route_id": rid})
        elif st["route_state"] == "missing":
            _v("route_missing_terminal", {"route_id": rid})

    # ---- 4/5. 归并元数据与逐路线答卷 SHA ----
    meta_path = root / "merged" / "export_metadata.json"
    preds_path = root / "merged" / "predictions.jsonl"
    per_route: dict[str, dict] = {}
    if not meta_path.is_file() or not preds_path.is_file():
        _v("merged_artifacts_missing",
           {"meta": meta_path.is_file(), "preds": preds_path.is_file()})
    else:
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception as exc:
            _v("merged_meta_unreadable", {"error": str(exc)[:200]})
            meta = {}
        per_route = {r.get("route_id"): r
                     for r in meta.get("per_route") or []}
        for rid in route_ids:
            pr = per_route.get(rid)
            if pr is None:
                _v("merged_per_route_missing", {"route_id": rid})
                continue
            st = route_states.get(rid) or {}
            # 失败标志与独立分类交叉核对:汇总被篡改/漂移 → 违规
            if st.get("route_state") == "failed" \
                    and not pr.get("failure_reason"):
                _v("merged_failure_flag_inconsistent", {"route_id": rid})
        # 行级:逐行 route_id 唯一且恰为清单集合
        rows_ids: list[str] = []
        try:
            for line in preds_path.read_text(
                    encoding="utf-8").splitlines():
                if line.strip():
                    rows_ids.append(json.loads(line)["route_id"])
        except Exception as exc:
            _v("merged_predictions_unreadable", {"error": str(exc)[:200]})
        if len(rows_ids) != len(route_ids):
            _v("merged_row_count", {"expected": len(route_ids),
                                    "actual": len(rows_ids)})
        if sorted(set(rows_ids)) != sorted(set(route_ids)):
            _v("merged_route_id_set",
               {"missing": sorted(set(route_ids) - set(rows_ids)),
                "extra": sorted(set(rows_ids) - set(route_ids))})
        if len(set(rows_ids)) != len(rows_ids):
            _v("merged_route_id_duplicates",
               {"duplicates": sorted({r for r in rows_ids
                                       if rows_ids.count(r) > 1})})
        # 逐路线答卷文件 SHA 与元数据记录核对(需要 run 目录)
        runs_root = root / "runs"
        for rid in route_ids:
            pr = per_route.get(rid) or {}
            run_id = pr.get("run_id") or ""
            declared = pr.get("predictions_sha256")
            pj = runs_root / run_id / "predictions.jsonl"
            if not run_id or not pj.is_file():
                _v("route_predictions_file_missing",
                   {"route_id": rid, "run_id": run_id})
                continue
            actual = _sha256_file(pj)
            if declared and declared != actual:
                _v("route_predictions_sha_mismatch",
                   {"route_id": rid, "declared": declared[:16],
                    "actual": actual[:16]})

    # 交叉核对:归并元数据若记录了批次终态,须与独立汇总一致
    if meta_path.is_file() and per_route:
        try:
            meta_all = json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception:
            meta_all = {}
        recorded = meta_all.get("batch_terminal_status")
        if recorded:
            n_failed = sum(1 for s in route_states.values()
                           if s["route_state"] == "failed")
            expect = "failed" if n_failed else (
                "incomplete" if any(
                    s["route_state"] in ("missing", "export_failed")
                    for s in route_states.values()) else "completed")
            if recorded != expect:
                _v("merged_terminal_status_inconsistent",
                   {"recorded": recorded, "recomputed": expect})

    return {
        "schema_version": PAIRING_GATE_SCHEMA,
        "ok": not violations,
        "n_violations": len(violations),
        "violations": violations,
        "n_routes": len(route_ids),
        "route_states": {rid: st["route_state"]
                         for rid, st in route_states.items()},
        "batch_sha256": identity.get("sha256", ""),
    }


def paired_release_verdict(arm_results: dict[str, dict]) -> dict:
    """全臂汇总:complete(可发布) vs diagnostic_incomplete(仅诊断)。"""
    per_arm = {}
    for label, res in arm_results.items():
        per_arm[label] = {
            "ok": bool(res.get("ok")),
            "n_violations": res.get("n_violations", 0),
            "violations": res.get("violations", [])[:20],
            "n_routes": res.get("n_routes", 0),
            "route_states": res.get("route_states", {}),
        }
    ok = all(a["ok"] for a in per_arm.values()) and bool(per_arm)
    return {
        "schema_version": PAIRING_GATE_SCHEMA,
        "verdict": "complete" if ok else "diagnostic_incomplete",
        "release_eligible": ok,
        "per_arm": per_arm,
    }
