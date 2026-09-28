"""R1 修复端到端集成夹具(任务书 §6.1;无凭证无网络、零 LLM)。

一条链同时跨过:真实 worker 进程落盘 → 合法 resume → 批次终态
(completed)→ 归并导出 → 配对门禁(complete 放行);再对同一批注入
1 条异常失败路线,断言批次终态翻转为 failed 且配对门禁阻断发布判定
(diagnostic_incomplete)。

复用 test_batch_runner 的合成三路夹具(每底物一张 recorded 卡,
无模型确定性直通);不触碰真实资产与金标。
"""

from __future__ import annotations

import json
import shutil
import threading
from pathlib import Path

from pathway_v43.batch import (
    BatchCoordinator,
    batch_terminal_summary,
    merge_predictions,
)
from pathway_v43.output.pairing_gate import (
    paired_release_verdict,
    validate_arm,
)
from tests.test_batch_runner import (
    _batch_identity_for,
    _make_manifest,
    _scripted_fixture,
)


def _write_scripted(tmp_path: Path, scripted: dict) -> Path:
    p = tmp_path / "scripted.json"
    p.write_text(json.dumps(scripted), encoding="utf-8")
    return p


def _drive_coordinator(tmp_path: Path, manifest: dict, config: dict,
                       export_policy: dict, identity: dict,
                       scripted_file: Path) -> tuple[Path, dict]:
    """在线程里把协调器跑到全部终态;返回批次根与终态映射。"""
    batch_root = tmp_path / "batch"
    batch_root.mkdir(parents=True, exist_ok=True)
    (batch_root / "input_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    (batch_root / "batch_identity.json").write_text(
        json.dumps({"identity": identity["identity"],
                    "sha256": identity["sha256"]},
                   ensure_ascii=False), encoding="utf-8")
    coord = BatchCoordinator(
        batch_root=batch_root, runs_root=batch_root / "runs",
        manifest=manifest, identity=identity, config=config,
        provider="off", model_id="", request_params={}, timeout_s=0.0,
        export_policy=export_policy, max_parallel=20,
        poll_interval_s=0.2, worker_wall_clock_cap_s=300,
        max_worker_respawns=2, test_scripted=str(scripted_file))
    done = threading.Event()

    def drive():
        try:
            coord.run_to_completion()
        finally:
            done.set()

    t = threading.Thread(target=drive, daemon=True)
    t.start()
    assert done.wait(timeout=120), "协调器超时未收敛"
    t.join(timeout=10)
    return batch_root, coord.terminal_states()


def _terminal_of(arm: Path) -> dict[str, dict]:
    out = {}
    for sp in sorted((arm / "workers").glob("*.status.json")):
        out[sp.name.replace(".status.json", "")] = json.loads(
            sp.read_text(encoding="utf-8"))
    return out


def test_end_to_end_complete_then_failed_arm(tmp_path):
    """完整链(任务书 §6.1):落盘 → 崩溃 → 合法 resume → 批次终态 →
    导出 → 配对门禁放行;再注入失败路线 → 批次 failed + 门禁阻断。"""
    substrates = ["CCO", "CCC", "CCCC"]
    manifest = _make_manifest(tmp_path, 3, substrates)
    config, export_policy, identity = _batch_identity_for(
        tmp_path, manifest, tmp_path / "input_manifest.json")
    scripted = _write_scripted(tmp_path, _scripted_fixture(substrates))

    # ---- 0. 首路线先经崩溃 worker:run_identity 落盘后硬杀 ----
    from pathway_v43.batch import run_id_for_route, run_worker

    first = manifest["route_order"][0]
    first_smiles = substrates[0]
    crash_root = tmp_path / "crashprep"
    crash_root.mkdir(parents=True)
    env = dict(__import__("os").environ)
    env["PATHWAY_V43_CRASH_AFTER"] = "classify_evidence"
    import subprocess as sp
    import sys as _sys

    plan = {
        "route_id": first, "run_id": run_id_for_route(
            identity["short"], "dev", first),
        "root_smiles": first_smiles,
        "runs_root": str(tmp_path / "batch" / "runs"),
        "quarantine_root": str(tmp_path / "batch" / "quarantine"),
        "model": {"provider": "off", "model_id": "",
                  "request_params": {}, "timeout_s": 0.0},
        "budgets": config["budgets"],
        "export_policy": export_policy,
        "status_path": str(crash_root / f"{first}.status.json"),
        "test_scripted": str(scripted),
    }
    plan_path = crash_root / f"{first}.plan.json"
    plan_path.write_text(json.dumps(plan), encoding="utf-8")
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
    env["OMP_NUM_THREADS"] = "1"
    crashed = sp.run(
        [_sys.executable, "-m", "pathway_v43", "batch-worker",
         "--plan", str(plan_path)],
        capture_output=True, text=True, env=env, timeout=120)
    assert crashed.returncode == 70, "硬杀注入应 os._exit(70)"
    # run 已有产物落盘但无终态状态文件(崩溃 worker 不写终态)
    assert not (crash_root / f"{first}.status.json").exists()

    # ---- 1. 协调器接管:对无终态路线 respawn → run_worker 走
    #        resume 分支(合法 resume),三路全部到达合法终态 ----
    batch_root, terminal = _drive_coordinator(
        tmp_path, manifest, config, export_policy, identity, scripted)
    route_ids = manifest["route_order"]
    summary = batch_terminal_summary(route_ids, terminal)
    assert summary["status"] == "completed", summary
    assert summary["n_valid_terminal"] == 3
    # run 产物与决策块稳定落盘(指纹链)
    decisions = list((batch_root / "runs").glob("*/results/*/decision.json"))
    assert decisions, "decision 产物必须落盘"

    # ---- 2. 归并导出 + 配对门禁放行 ----
    merged = merge_predictions(
        batch_root=batch_root, runs_root=batch_root / "runs",
        manifest=manifest, identity=identity, export_policy=export_policy,
        terminal=terminal)
    assert merged["batch_terminal_status"] == "completed"
    assert merged["n_lines"] == 3
    for pr in merged["per_route"]:
        assert pr["route_state"] == "success_completed"
    res_ok = validate_arm(batch_root)
    assert res_ok["ok"], res_ok["violations"]
    verdict = paired_release_verdict({"C0": res_ok})
    assert verdict["verdict"] == "complete"
    assert verdict["release_eligible"] is True

    # ---- 3. 注入 1 条异常失败路线(r1 事故形状:failed + export_ok)----
    bad_root = tmp_path / "batch_bad"
    bad_root.mkdir(parents=True)
    for name in ("input_manifest.json", "batch_identity.json"):
        shutil.copy(batch_root / name, bad_root / name)
    shutil.copytree(batch_root / "runs", bad_root / "runs")
    workers = bad_root / "workers"
    workers.mkdir()
    for sp in (batch_root / "workers").glob("*.status.json"):
        shutil.copy(sp, workers / sp.name)
    # route[1] 篡改为事故形状:run 有导出但 worker 记录异常失败
    victim = route_ids[1]
    vsp = workers / f"{victim}.status.json"
    st = json.loads(vsp.read_text(encoding="utf-8"))
    st["failed"] = ("ArtifactIntegrityError:产物完整性校验失败"
                    "(注入的 r1 事故形状)")
    vsp.write_text(json.dumps(st, ensure_ascii=False), encoding="utf-8")
    shutil.copytree(batch_root / "merged", bad_root / "merged")

    res_bad = validate_arm(bad_root)
    assert not res_bad["ok"]
    codes = {v["code"] for v in res_bad["violations"]}
    assert "route_failed" in codes
    summary2 = batch_terminal_summary(route_ids, _terminal_of(bad_root))
    assert summary2["status"] == "failed"
    assert summary2["n_failed"] == 1
    assert summary2["failed_route_ids"] == [victim]

    # ---- 4. 配对门禁阻断发布判定 ----
    verdict2 = paired_release_verdict({"C0": res_ok, "D3": res_bad})
    assert verdict2["verdict"] == "diagnostic_incomplete"
    assert verdict2["release_eligible"] is False
