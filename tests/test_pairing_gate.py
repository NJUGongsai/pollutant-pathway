"""R1-c 配对门禁与批次终态测试(任务书 §4/§4.5;无凭证无网络)。

七类失败夹具各断言**发布判定被阻断或放行**(不只核对计数):
1 行 failed 且 export_ok=true;失败后部分答卷;失败后空答卷;合法
awaiting_prediction 空答卷;少 route_id;重 route_id;答卷 SHA 与元数据
不一致;以及全部合法终态的放行对照。
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from pathway_v43.batch import batch_terminal_summary, classify_route_state
from pathway_v43.domain.models import canonical_json
from pathway_v43.output.pairing_gate import (
    paired_release_verdict,
    validate_arm,
)

ROUTES = ["pb_0001", "pb_0002", "pb_0003"]


# ------------------------------------------------ 夹具构造


def _write_arm(root: Path, *, statuses: dict[str, dict | None],
               answer_rows: dict[str, list] | None = None,
               meta_patch: dict | None = None,
               drop_routes_from_merged: list[str] | None = None,
               duplicate_route_in_merged: str | None = None,
               sha_override: dict[str, str] | None = None,
               manifest_route_order: list[str] | None = None) -> Path:
    """造一个最小批次根(workers/merged/runs/身份/清单),全 JSON 文件。"""
    root.mkdir(parents=True, exist_ok=True)
    order = manifest_route_order or ROUTES
    (root / "input_manifest.json").write_text(json.dumps({
        "kind": "batch_input_manifest", "split": "dev",
        "route_order": order,
        "routes": [{"route_id": r, "root_smiles": "C"} for r in order],
        "gold_fields_excluded": True,
    }, ensure_ascii=False))
    body = {"schema_version": "v43-batch-1", "split": "dev",
            "config": {"smoke": True}}
    (root / "batch_identity.json").write_text(json.dumps({
        "identity": body,
        "sha256": hashlib.sha256(
            canonical_json(body).encode("utf-8")).hexdigest(),
    }, ensure_ascii=False))

    per_route = []
    for rid in order:
        st = statuses.get(rid, {"stop_reason": "completed"})
        run_id = f"dev_smoke_{rid}"
        sp = root / "workers" / f"{rid}.status.json"
        if st is not None:
            sp.parent.mkdir(parents=True, exist_ok=True)
            sp.write_text(json.dumps({
                "route_id": rid, "run_id": run_id, "finished_at": "t",
                "stop_reason": st.get("stop_reason", ""),
                "failed": st.get("failed"),
                "export_ok": st.get("export_ok", True),
                "predictions_sha256": st.get("predictions_sha256"),
            }, ensure_ascii=False))
        pj = root / "runs" / run_id / "predictions.jsonl"
        pj.parent.mkdir(parents=True, exist_ok=True)
        steps = (answer_rows or {}).get(rid, [])
        row = {"route_id": rid, "root_smiles": "C", "steps": steps}
        pj.write_text(json.dumps(row, sort_keys=True) + "\n")
        per_route.append({
            "route_id": rid, "run_id": run_id,
            "stop_reason": st.get("stop_reason", "") if st else "",
            "answer_kind": ("full" if steps else
                            ("empty" if (st or {}).get("stop_reason")
                             in ("completed", "awaiting_prediction",
                                 "budget_exhausted") else "fallback_empty")),
            "failure_reason": (st or {}).get("failed"),
            "route_state": classify_route_state(st)["route_state"],
            "predictions_sha256": (sha_override or {}).get(
                rid) or hashlib.sha256(
                (json.dumps(row, sort_keys=True) + "\n").encode()
            ).hexdigest(),
        })

    lines = []
    for pr in per_route:
        if drop_routes_from_merged and pr["route_id"] in drop_routes_from_merged:
            continue
        rid_field = (duplicate_route_in_merged
                     if pr["route_id"] == duplicate_route_in_merged
                     else pr["route_id"])
        steps = (answer_rows or {}).get(pr["route_id"], [])
        lines.append(json.dumps(
            {"route_id": rid_field, "root_smiles": "C", "steps": steps},
            sort_keys=True))
    if duplicate_route_in_merged:
        first = next(l for l in lines if json.loads(l)["route_id"]
                     == duplicate_route_in_merged)
        lines.append(first)
    merged = root / "merged"
    merged.mkdir(parents=True, exist_ok=True)
    text = "".join(l + "\n" for l in lines)
    (merged / "predictions.jsonl").write_text(text)
    states = batch_terminal_summary(order, {
        rid: ({"finished_at": "t", "export_ok": True, **st}
              if st is not None else {})
        for rid, st in statuses.items()} | {
        rid: {"finished_at": "t", "export_ok": True,
              "stop_reason": "completed"}
        for rid in order if rid not in statuses})
    meta = {
        "kind": "batch_merged_predictions", "n_lines": len(lines),
        "n_unique_route_ids": len({json.loads(l)["route_id"]
                                   for l in lines}),
        "batch_terminal_status": states["status"],
        "n_routes_failed": states["n_failed"],
        "failed_route_ids": states["failed_route_ids"],
        "per_route": per_route,
    }
    meta.update(meta_patch or {})
    (merged / "export_metadata.json").write_text(
        json.dumps(meta, ensure_ascii=False))
    return root


def _ok_status(stop="completed"):
    return {"stop_reason": stop, "export_ok": True}


# ------------------------------------------------ 单元:路线/批次分类


def test_classify_route_state_five_kinds():
    assert classify_route_state(None)["route_state"] == "missing"
    assert classify_route_state({})["route_state"] == "missing"
    ok = classify_route_state({"finished_at": "t", "stop_reason":
                               "completed", "export_ok": True})
    assert ok["route_state"] == "success_completed"
    hold = classify_route_state({"finished_at": "t", "stop_reason":
                                 "awaiting_prediction", "export_ok": True})
    assert hold["route_state"] == "legal_stop"
    budget = classify_route_state({"finished_at": "t", "stop_reason":
                                   "budget_exhausted", "export_ok": True})
    assert budget["route_state"] == "legal_stop"
    # 事故形状:failed 但 export_ok=True(部分答卷已导出)仍算异常失败
    failed = classify_route_state({
        "finished_at": "t", "stop_reason": None, "export_ok": True,
        "failed": "ArtifactIntegrityError:产物完整性校验失败"})
    assert failed["route_state"] == "failed"
    assert failed["failure_class"] == "ArtifactIntegrityError"
    te = classify_route_state({
        "finished_at": "t", "stop_reason": None, "export_ok": True,
        "failed": "TypeError:'NoneType' object is not subscriptable"})
    assert te["route_state"] == "failed"
    assert te["failure_class"] == "TypeError"
    exp = classify_route_state({"finished_at": "t", "stop_reason":
                                "completed", "export_ok": False})
    assert exp["route_state"] == "export_failed"


def test_batch_terminal_summary_statuses():
    terminal = {
        "a": {"finished_at": "t", "stop_reason": "completed",
              "export_ok": True},
        "b": {"finished_at": "t", "stop_reason": "awaiting_prediction",
              "export_ok": True},
        "c": {"finished_at": "t", "export_ok": True,
              "failed": "TypeError:x"},
    }
    s = batch_terminal_summary(["a", "b", "c"], terminal)
    assert s["status"] == "failed"
    assert s["n_expected"] == 3 and s["n_valid_terminal"] == 2
    assert s["n_failed"] == 1 and s["failed_route_ids"] == ["c"]
    ok = batch_terminal_summary(["a", "b"], {k: terminal[k]
                                             for k in ("a", "b")})
    assert ok["status"] == "completed"
    inc = batch_terminal_summary(["a", "b", "z"], {
        "a": terminal["a"], "b": terminal["b"], "z": {}})
    assert inc["status"] == "incomplete"
    assert inc["missing_route_ids"] == ["z"]


# ------------------------------------------------ 门禁:七情形


def test_gate_all_legal_passes(tmp_path):
    arm = _write_arm(tmp_path / "arm", statuses={
        r: _ok_status() for r in ROUTES[:2]} | {
        ROUTES[2]: _ok_status("awaiting_prediction")})
    res = validate_arm(arm)
    assert res["ok"], res["violations"]
    v = paired_release_verdict({"C0": res})
    assert v["verdict"] == "complete" and v["release_eligible"]


def test_gate_one_failed_export_ok_blocks(tmp_path):
    """情形 1:20 行全在、1 行 failed 且 export_ok=true → 发布阻断。"""
    statuses = {r: _ok_status() for r in ROUTES}
    statuses[ROUTES[1]] = {"stop_reason": None, "export_ok": True,
                           "failed": "ArtifactIntegrityError:x"}
    arm = _write_arm(tmp_path / "arm", statuses=statuses)
    res = validate_arm(arm)
    assert not res["ok"]
    assert any(v["code"] == "route_failed" and v["route_id"] == ROUTES[1]
               for v in res["violations"])
    v = paired_release_verdict({"C0": validate_arm(
        _write_arm(tmp_path / "c0", statuses={
            r: _ok_status() for r in ROUTES})), "D3": res})
    assert v["verdict"] == "diagnostic_incomplete"
    assert v["release_eligible"] is False


def test_gate_failed_with_partial_answer_blocks(tmp_path):
    """情形 2:失败路线有部分答卷(甚至命中)→ 仍阻断(只可诊断)。"""
    statuses = {r: _ok_status() for r in ROUTES}
    statuses[ROUTES[0]] = {"stop_reason": None, "export_ok": True,
                           "failed": "TypeError:'NoneType' x"}
    arm = _write_arm(tmp_path / "arm", statuses=statuses,
                     answer_rows={ROUTES[0]: [{"smiles": "CCO"}]})
    res = validate_arm(arm)
    assert not res["ok"]
    codes = [v["code"] for v in res["violations"]]
    assert "route_failed" in codes


def test_gate_failed_with_empty_answer_blocks(tmp_path):
    """情形 3:失败路线空答卷 → 阻断。"""
    statuses = {r: _ok_status() for r in ROUTES}
    statuses[ROUTES[2]] = {"stop_reason": None, "export_ok": True,
                           "failed": "worker_failed_no_terminal"}
    arm = _write_arm(tmp_path / "arm", statuses=statuses)
    assert not validate_arm(arm)["ok"]


def test_gate_legal_awaiting_empty_passes(tmp_path):
    """情形 4:合法 awaiting_prediction 空答卷 → 放行。"""
    statuses = {r: _ok_status() for r in ROUTES}
    statuses[ROUTES[0]] = _ok_status("awaiting_prediction")
    statuses[ROUTES[1]] = _ok_status("budget_exhausted")
    arm = _write_arm(tmp_path / "arm", statuses=statuses)
    res = validate_arm(arm)
    assert res["ok"], res["violations"]
    assert res["route_states"][ROUTES[0]] == "legal_stop"


def test_gate_missing_route_blocks(tmp_path):
    """情形 5:少 route_id(worker 状态与归并行都缺)→ 阻断。"""
    statuses = {r: _ok_status() for r in ROUTES}
    statuses[ROUTES[1]] = None  # 无终态文件
    arm = _write_arm(tmp_path / "arm", statuses=statuses,
                     drop_routes_from_merged=[ROUTES[1]])
    res = validate_arm(arm)
    assert not res["ok"]
    codes = [v["code"] for v in res["violations"]]
    assert "route_missing_terminal" in codes
    assert "merged_row_count" in codes


def test_gate_duplicate_route_blocks(tmp_path):
    """情形 6:重 route_id → 阻断。"""
    arm = _write_arm(tmp_path / "arm",
                     statuses={r: _ok_status() for r in ROUTES},
                     duplicate_route_in_merged=ROUTES[0])
    res = validate_arm(arm)
    assert not res["ok"]
    codes = [v["code"] for v in res["violations"]]
    assert "merged_route_id_duplicates" in codes


def test_gate_predictions_sha_mismatch_blocks(tmp_path):
    """情形 7:答卷 SHA 与元数据不一致 → 阻断。"""
    arm = _write_arm(tmp_path / "arm",
                     statuses={r: _ok_status() for r in ROUTES},
                     sha_override={ROUTES[0]: "0" * 64})
    res = validate_arm(arm)
    assert not res["ok"]
    assert any(v["code"] == "route_predictions_sha_mismatch"
               and v["route_id"] == ROUTES[0] for v in res["violations"])


def test_gate_identity_tamper_blocks(tmp_path):
    """批次身份不自洽(体哈希对不上)→ 阻断。"""
    arm = _write_arm(tmp_path / "arm",
                     statuses={r: _ok_status() for r in ROUTES})
    ip = arm / "batch_identity.json"
    ident = json.loads(ip.read_text())
    ident["identity"]["config"]["smoke"] = False  # 篡改体不重算哈希
    ip.write_text(json.dumps(ident, ensure_ascii=False))
    res = validate_arm(arm)
    assert not res["ok"]
    assert any(v["code"] == "batch_identity_hash_mismatch"
               for v in res["violations"])


def test_gate_route_order_mismatch_blocks(tmp_path):
    """臂清单与冻结清单(C0)不一致 → 阻断。"""
    arm = _write_arm(tmp_path / "arm",
                     statuses={r: _ok_status() for r in ROUTES},
                     manifest_route_order=ROUTES[:2])
    res = validate_arm(arm, expected_route_ids=ROUTES)
    assert not res["ok"]
    assert any(v["code"] == "route_order_mismatch"
               for v in res["violations"])
