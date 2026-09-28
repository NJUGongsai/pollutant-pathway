"""批跑协调器验收(TASK_V43_EXPORT_DEV §5.4)。

- 屏障夹具:证明 N 个 worker **同时处于运行态**(各 worker 在 start_run
  身份落盘后写 ``<run_id>.ready`` 并等 GO;协调器全部到齐才放行,证据
  文件 ``barrier_evidence.json``);并验证 per-worker SQLite/目录隔离与
  归并冻结顺序。
- 单 worker 崩溃恢复:commit_pathway 落账后硬杀(无 checkpoint)→ 协调器
  resume 重放 → 终态唯一、事件不重复、裁决产物不冲突。

worker 数默认 4(本地 16GB 内存承载 20 路真实引擎并行会超卖);
Chenyu 上以 ``V43_BATCH_TEST_WORKERS=20`` 复跑本文件取得 20 路证据
(dev 正式批跑的 coordinator progress/日志提供第二重 20 路同跑证据)。
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pathway_v43.batch import (  # noqa: E402
    DEFAULT_DEV_BATCH_CONFIG,
    BatchCoordinator,
    merge_predictions,
)
from pathway_v43.output.export_v3 import load_export_policy  # noqa: E402

REPO = Path(__file__).resolve().parents[1]

SMALL_MOLECULES = ["CCO", "CCC(C)O", "CCCO", "Oc1ccccc1O"]


def _make_manifest(route_ids: list[str]) -> dict:
    routes = [
        {"route_id": rid,
         "root_smiles": SMALL_MOLECULES[i % len(SMALL_MOLECULES)],
         "root_smiles_sha256": f"fixture-{rid}"}
        for i, rid in enumerate(route_ids)
    ]
    return {
        "schema_version": "v43-batch-1",
        "kind": "batch_input_manifest",
        "split": "dev",
        "route_order": list(route_ids),
        "routes": routes,
        "source": {"fixture": "test_batch_dev"},
        "whitelist_fields": ["root_smiles", "root_smiles_sha256",
                             "route_id"],
        "gold_fields_excluded": True,
    }


def _tiny_config() -> dict:
    config = json.loads(json.dumps(DEFAULT_DEV_BATCH_CONFIG))
    config["budgets"] = {"max_depth": 2, "max_expansions": 2,
                         "max_frontier_width": 3, "max_llm_calls": 4,
                         "max_proposals": 2}
    config["poll_interval_s"] = 0.2
    config["rate"]["max_calls"] = 10_000
    return config


def _route_ids(n: int) -> list[str]:
    return [f"pb_t{i:03d}" for i in range(n)]


def _merge(batch_root: Path, runs_root: Path, manifest: dict,
           terminal: dict) -> dict:
    identity = json.loads((batch_root / "batch_identity.json")
                          .read_text(encoding="utf-8")) \
        if (batch_root / "batch_identity.json").is_file() \
        else {"short": "btest", "sha256": "fixture"}
    return merge_predictions(
        batch_root=batch_root, runs_root=runs_root, manifest=manifest,
        identity=identity, export_policy=load_export_policy(),
        terminal=terminal)


# ---------------------------------------------------- §5.4 屏障/隔离/归并


def test_workers_run_simultaneously_isolated_and_merge_in_order(tmp_path):
    n = int(os.environ.get("V43_BATCH_TEST_WORKERS", "4"))
    ids = _route_ids(n)
    manifest = _make_manifest(ids)
    barrier_dir = tmp_path / "barrier"
    barrier_dir.mkdir()
    (tmp_path / "batch" / "gate").mkdir(parents=True)
    config = _tiny_config()
    coordinator = BatchCoordinator(
        batch_root=tmp_path / "batch", runs_root=tmp_path / "runs",
        manifest=manifest, identity={"short": "btest", "sha256": "fixture"},
        config=config, provider="off", model_id="", request_params={},
        timeout_s=0.0, export_policy=load_export_policy(),
        max_parallel=n, poll_interval_s=0.2, worker_wall_clock_cap_s=900,
        max_worker_respawns=1,
    )
    os.environ["PATHWAY_V43_RUN_BARRIER_DIR"] = str(barrier_dir)
    os.environ["PATHWAY_V43_BATCH_BARRIER"] = str(n)
    try:
        terminal = coordinator.run_to_completion()
    finally:
        os.environ.pop("PATHWAY_V43_RUN_BARRIER_DIR", None)
        os.environ.pop("PATHWAY_V43_BATCH_BARRIER", None)

    # 屏障证据:GO 放行前全部 n 个 worker 已 ready(同处运行态)
    evidence = json.loads(
        (barrier_dir / "barrier_evidence.json").read_text(encoding="utf-8"))
    assert evidence["expected"] == n
    assert len(evidence["ready_files"]) == n

    # 全部终态且无失败
    assert all(terminal.get(r, {}).get("finished_at") for r in ids)
    assert all(not terminal.get(r, {}).get("failed") for r in ids), terminal

    # 隔离:每 worker 独立 run 目录 + 独立 SQLite(互不共写)
    runs_root = tmp_path / "runs"
    for r in ids:
        run_dir = runs_root / f"dev_btest_{r}"
        assert (run_dir / "pathway.sqlite").is_file(), run_dir
        assert (run_dir / "run_identity.json").is_file()

    # 归并:冻结顺序、行数 = n、route_id 唯一
    meta = _merge(tmp_path / "batch", runs_root, manifest, terminal)
    lines = (tmp_path / "batch" / "merged" / "predictions.jsonl") \
        .read_text(encoding="utf-8").splitlines()
    assert len(lines) == n
    got_order = [json.loads(l)["route_id"] for l in lines]
    assert got_order == ids, "归并必须按冻结 route_id 顺序"
    assert meta["n_unique_route_ids"] == n
    assert meta["predictions_sha256"]


# ---------------------------------------------------- §5.4 杀掉恢复


def test_worker_crash_after_commit_recovers_no_duplicate(tmp_path,
                                                         monkeypatch):
    n = 3
    ids = _route_ids(n)
    doomed = ids[0]
    # 根分子必须有库精确命中(recorded 证据)→ 模型 off 也会确定性 commit,
    # 保证崩溃注入点 commit_pathway 真实到达
    manifest = _make_manifest(ids)
    for row in manifest["routes"]:
        row["root_smiles"] = "BrCC(Br)CBr"
        row["root_smiles_sha256"] = f"fixture-{row['route_id']}"
    (tmp_path / "batch" / "gate").mkdir(parents=True)
    config = _tiny_config()
    marker = tmp_path / "crash_injected.marker"

    def builder(plan_path: Path) -> list[str]:
        plan = json.loads(Path(plan_path).read_text(encoding="utf-8"))
        cmd = [sys.executable, "-m", "pathway_v43", "batch-worker",
               "--plan", str(plan_path)]
        if plan["route_id"] == doomed and not marker.exists():
            marker.write_text("1", encoding="utf-8")
            # 硬杀注入:副作用落盘后 os._exit(70),checkpoint 未写
            return ["/usr/bin/env", "PATHWAY_V43_CRASH_AFTER=commit_pathway",
                    *cmd]
        return cmd

    coordinator = BatchCoordinator(
        batch_root=tmp_path / "batch", runs_root=tmp_path / "runs",
        manifest=manifest, identity={"short": "btest2", "sha256": "fixture"},
        config=config, provider="off", model_id="", request_params={},
        timeout_s=0.0, export_policy=load_export_policy(),
        max_parallel=n, poll_interval_s=0.2, worker_wall_clock_cap_s=900,
        max_worker_respawns=2, worker_cmd_builder=builder,
    )
    terminal = coordinator.run_to_completion()

    assert marker.exists(), "崩溃注入必须真实发生"
    assert all(terminal.get(r, {}).get("finished_at") for r in ids), terminal
    assert not any(terminal.get(r, {}).get("failed") for r in ids)
    # 协调器日志含 respawn 记录
    log = (tmp_path / "batch" / "coordinator.log").read_text(encoding="utf-8")
    assert f"respawn {doomed}" in log

    # 恢复后:每父路径事件恰一次(不重复入账),每事件一份裁决产物
    doomed_run = tmp_path / "runs" / f"dev_btest2_{doomed}"
    rep = json.loads((doomed_run / "report" / "pathway.json")
                     .read_text(encoding="utf-8"))
    assert rep["counts"]["reaction_events"] >= 1, rep["counts"]
    parents = [e["parent_path_id"] for e in rep["reaction_events"]]
    assert len(parents) == len(set(parents)), "同一父路径不得重复入账"
    adjs = list((doomed_run / "results").glob("*/report_adjudication.json"))
    assert len(adjs) == rep["counts"]["reaction_events"], \
        "每事件恰一份裁决产物(恢复重放幂等)"

    # 全批归并仍每路线恰一行
    meta = _merge(tmp_path / "batch", tmp_path / "runs", manifest, terminal)
    lines = (tmp_path / "batch" / "merged" / "predictions.jsonl") \
        .read_text(encoding="utf-8").splitlines()
    assert len(lines) == n
    assert [json.loads(l)["route_id"] for l in lines] == ids
