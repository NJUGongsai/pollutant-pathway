"""dev 批跑协调器验收测试(TASK_V43_EXPORT_DEV §5.4)。

- 真实冻结清单:dev 恰 20 条、与 eval 100 条不相交、白名单字段、来源哈希。
- 屏障夹具:20 个 worker 同时处于运行态(20 个独立 OS 进程在真实
  start_run 的屏障钩子内互相等待,GO 后才继续)。
- 隔离:每个 worker 只写自己的 run 目录/SQLite;plan 不含 gold 字段。
- 恢复:杀掉 1 个 worker 后协调器只恢复未完成路线,最终行数完整、无重复。
- 归并顺序 = 冻结 route_id 顺序(与完成顺序无关);失败路线补显式空行。
- API 账目:issued/响应/用量计数;usage 缺失时费用 unknown 不估算。
"""

from __future__ import annotations

import json
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pathway_v43.batch import (  # noqa: E402
    BatchCoordinator,
    api_account,
    build_batch_identity,
    build_input_manifest,
    load_batch_config,
    load_input_manifest,
    merge_predictions,
    run_id_for_route,
    run_worker,
)
from pathway_v43.config import resolve_config  # noqa: E402
from pathway_v43.domain.identity import cn_identity  # noqa: E402
from pathway_v43.output.export_v3 import load_export_policy  # noqa: E402
from pathway_v43.services.reaction_finder import (  # noqa: E402
    ScriptedReactionFinder,
)

from wf_helpers import evidence  # noqa: E402

REPO = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------- 清单(真实 v3)


@pytest.mark.skipif(
    not (REPO.parent / "dependingv3" / "evaluation" / "pathway_benchmark"
         / "split_manifest.json").is_file(),
    reason="v3 冻结基准不可用")
def test_input_manifest_whitelist_from_frozen_v3(tmp_path):
    """真实冻结清单:dev 恰 20、与 eval 不相交、只含白名单字段。"""
    out = build_input_manifest(REPO.parent / "dependingv3", "dev",
                               tmp_path / "input_manifest.json")
    assert len(out["routes"]) == 20
    assert len(out["route_order"]) == 20
    assert out["gold_fields_excluded"] is True
    allowed = {"route_id", "root_smiles", "root_smiles_sha256"}
    for row in out["routes"]:
        assert set(row) == allowed, f"白名单外字段:{set(row) - allowed}"
        assert row["root_smiles_sha256"] and len(row["root_smiles_sha256"]) == 64
    # dev 与 eval 不相交(冻结清单同源核查)
    manifest = json.loads(
        (REPO.parent / "dependingv3" / "evaluation" / "pathway_benchmark"
         / "split_manifest.json").read_text())
    dev, ev = set(manifest["split"]["dev"]), set(manifest["split"]["eval"])
    assert not (dev & ev)
    assert {r["route_id"] for r in out["routes"]} == dev
    assert out["source"]["split_manifest_sha256"]
    assert out["source"]["gold_routes_sha256"]


# ---------------------------------------------------------------- 夹具


def _make_manifest(tmp_path: Path, n: int, substrates: list[str]) -> dict:
    routes = []
    for i in range(n):
        rid = f"pb_{i:04d}"
        smi = substrates[i % len(substrates)]
        routes.append({
            "route_id": rid, "root_smiles": smi,
            "root_smiles_sha256": __import__("hashlib").sha256(
                smi.encode()).hexdigest(),
        })
    return {
        "schema_version": "v43-batch-1", "kind": "batch_input_manifest",
        "split": "dev", "route_order": [r["route_id"] for r in routes],
        "source": {"split_manifest_sha256": "0" * 64,
                   "gold_routes_sha256": "1" * 64,
                   "v3_root": "fixtures://v3"},
        "routes": routes, "whitelist_fields": sorted(routes[0].keys()),
        "gold_fields_excluded": True,
    }


def _scripted_fixture(substrates: list[str]) -> dict:
    """每个底物一张单产物 recorded 卡;无模型 → 确定性直通提交。"""
    scripted = {}
    for smi in substrates:
        ident = cn_identity(smi)
        scripted[ident] = [evidence(f"rec-{smi}", "recorded_reaction",
                                    ident, ["CC=O"])]
    return scripted


def _batch_identity_for(tmp_path: Path, manifest: dict, manifest_path: Path):
    config = load_batch_config()
    export_policy = load_export_policy()
    (tmp_path / "input_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    identity = build_batch_identity(
        split="dev", input_manifest_path=manifest_path, config=config,
        provider="off", model_id="", request_params={}, timeout_s=0.0,
        export_policy=export_policy)
    return config, export_policy, identity


def _run_coordinator(tmp_path: Path, manifest: dict, config: dict,
                     export_policy: dict, identity: dict,
                     scripted_file: Path, *, barrier: bool = False,
                     poll_s: float = 0.2):
    """构造协调器并在线程里跑到全部终态(返回线程与协调器)。"""
    batch_root = tmp_path / "batch"
    batch_root.mkdir(parents=True, exist_ok=True)
    coord = BatchCoordinator(
        batch_root=batch_root, runs_root=batch_root / "runs",
        manifest=manifest, identity=identity, config=config,
        provider="off", model_id="", request_params={}, timeout_s=0.0,
        export_policy=export_policy, max_parallel=20,
        poll_interval_s=poll_s, worker_wall_clock_cap_s=300,
        max_worker_respawns=2, test_scripted=str(scripted_file),
    )
    if barrier:
        coord._worker_env_orig = coord._worker_env

        def env_with_barrier():
            env = coord._worker_env_orig()
            env["PATHWAY_V43_RUN_BARRIER_DIR"] = str(batch_root / "barrier")
            return env

        coord._worker_env = env_with_barrier

    def drive():
        coord.run_to_completion()

    thread = threading.Thread(target=drive, daemon=True)
    thread.start()
    return coord, thread, batch_root


# ---------------------------------------------------------------- 屏障


def test_barrier_20_workers_simultaneously_running(tmp_path):
    """20 个独立 OS 进程同时处于运行态:真实 start_run 屏障钩子内,
    20 个 ready 齐后主线程才放行 GO。"""
    n = 20
    substrates = ["CCO", "CCC", "CCCC", "CCO"]
    manifest = _make_manifest(tmp_path, n, substrates)
    config, export_policy, identity = _batch_identity_for(
        tmp_path, manifest, tmp_path / "input_manifest.json")
    fixture = tmp_path / "scripted.json"
    fixture.write_text(json.dumps(_scripted_fixture(substrates)))
    coord, thread, batch_root = _run_coordinator(
        tmp_path, manifest, config, export_policy, identity, fixture,
        barrier=True)
    barrier_dir = batch_root / "barrier"
    deadline = time.monotonic() + 180
    while time.monotonic() < deadline:
        ready = len(list(barrier_dir.glob("*.ready"))) \
            if barrier_dir.is_dir() else 0
        if ready == n:
            break
        time.sleep(0.2)
    ready = len(list(barrier_dir.glob("*.ready"))) \
        if barrier_dir.is_dir() else 0
    assert ready == n, (
        f"屏障未集齐:只有 {ready}/{n} 个 worker 同时处于运行态"
        "(协调器必须一次性分配 20 路并行)")
    # 20 个同时就绪 → 放行
    (barrier_dir / "GO").write_text("go\n")
    thread.join(timeout=300)
    assert not thread.is_alive()
    terminal = coord.terminal_states()
    assert len(terminal) == n
    assert all(t.get("finished_at") for t in terminal.values())
    # 归并:20 行、冻结顺序、route_id 恰一次
    merged = merge_predictions(
        batch_root=batch_root, runs_root=batch_root / "runs",
        manifest=manifest, identity=identity, export_policy=export_policy,
        terminal=terminal)
    lines = (batch_root / "merged" / "predictions.jsonl").read_text() \
        .strip().splitlines()
    assert len(lines) == 20
    rids = [json.loads(l)["route_id"] for l in lines]
    assert rids == manifest["route_order"], "归并按冻结顺序而非完成顺序"
    assert len(set(rids)) == 20


# ---------------------------------------------------------------- 隔离/恢复


def test_worker_isolation_and_plan_has_no_gold_fields(tmp_path):
    """每个 worker 只写自己的 run 目录;plan 不含任何 gold 字段。"""
    substrates = ["CCO", "CCC"]
    manifest = _make_manifest(tmp_path, 2, substrates)
    config, export_policy, identity = _batch_identity_for(
        tmp_path, manifest, tmp_path / "input_manifest.json")
    fixture = tmp_path / "scripted.json"
    fixture.write_text(json.dumps(_scripted_fixture(substrates)))
    coord, thread, batch_root = _run_coordinator(
        tmp_path, manifest, config, export_policy, identity, fixture)
    thread.join(timeout=180)
    assert not thread.is_alive()
    # 各 run 目录独立存在,各自有独立 pathway.sqlite
    for rid in manifest["route_order"]:
        run_dir = batch_root / "runs" / coord.run_id_of(rid)
        assert (run_dir / "pathway.sqlite").is_file()
        assert (run_dir / "predictions.jsonl").is_file()
    # plan 字段白名单:root_smiles/run_id/预算等,无 gold 痕迹
    for plan_path in (batch_root / "workers").glob("*.plan.json"):
        plan = json.loads(plan_path.read_text())
        assert "test_scripted" in plan  # 测试夹具键显式在场
        blob = json.dumps(plan)
        for bad in ("gold_leaves", '"edges"', "gold_routes",
                    "provenance", "coverage_meta"):
            assert bad not in blob, f"plan 出现金标痕迹:{bad}"


def test_kill_worker_then_recover_no_duplicate(tmp_path):
    """杀掉 1 个 worker(事件提交后、checkpoint 前硬杀)→ 协调器恢复,
    最终答卷完整、事件无重复。"""
    import os

    substrates = ["CCO", "CCC"]
    manifest = _make_manifest(tmp_path, 2, substrates)
    config, export_policy, identity = _batch_identity_for(
        tmp_path, manifest, tmp_path / "input_manifest.json")
    fixture = tmp_path / "scripted.json"
    fixture.write_text(json.dumps(_scripted_fixture(substrates)))
    batch_root = tmp_path / "batch"
    batch_root.mkdir(parents=True, exist_ok=True)
    coord = BatchCoordinator(
        batch_root=batch_root, runs_root=batch_root / "runs",
        manifest=manifest, identity=identity, config=config,
        provider="off", model_id="", request_params={}, timeout_s=0.0,
        export_policy=export_policy, max_parallel=2, poll_interval_s=0.2,
        worker_wall_clock_cap_s=300, max_worker_respawns=2,
        test_scripted=str(fixture),
    )
    victim = manifest["route_order"][0]
    victim_run = coord.run_id_of(victim)
    orig_spawn = coord._spawn
    injected = {"done": False}

    def spawn_with_kill(route_id):
        # 崩溃注入只对 victim 的**首次** spawn 生效:恢复性重spawn 必须
        # 在干净环境下 resume(否则同一崩溃点反复硬杀,永远无法恢复)
        do_inject = route_id == victim and not injected["done"]
        if do_inject:
            injected["done"] = True
            os.environ["PATHWAY_V43_CRASH_AFTER"] = "commit_pathway"
        proc = orig_spawn(route_id)
        if do_inject:
            os.environ.pop("PATHWAY_V43_CRASH_AFTER", None)
        return proc

    coord._spawn = spawn_with_kill
    coord.run_to_completion()
    terminal = coord.terminal_states()
    assert len(terminal) == 2
    assert all(t.get("finished_at") for t in terminal.values())
    # victim:恢复后事件恰好一次(无重复提交),答卷仍有已提交事实
    run_dir = batch_root / "runs" / victim_run
    report = json.loads(
        (run_dir / "report" / "pathway.json").read_text())
    assert report["counts"]["reaction_events"] == 1
    row = json.loads((run_dir / "predictions.jsonl").read_text())
    assert row["steps"], "恢复后 victim 仍有已提交事实"
    merged = merge_predictions(
        batch_root=batch_root, runs_root=batch_root / "runs",
        manifest=manifest, identity=identity, export_policy=export_policy,
        terminal=terminal)
    lines = (batch_root / "merged" / "predictions.jsonl").read_text() \
        .strip().splitlines()
    assert len(lines) == 2
    assert [json.loads(l)["route_id"] for l in lines] == \
        manifest["route_order"]


def test_merge_fallback_empty_for_failed_routes(tmp_path):
    """失败路线(无导出文件)→ 归并补显式空行,20→N 行完整计分。"""
    substrates = ["CCO", "CCC", "CCCC"]
    manifest = _make_manifest(tmp_path, 3, substrates)
    config, export_policy, identity = _batch_identity_for(
        tmp_path, manifest, tmp_path / "input_manifest.json")
    batch_root = tmp_path / "batch"
    terminal = {manifest["route_order"][0]: {"failed": "worker_dead",
                                             "finished_at": "t"}}
    merged = merge_predictions(
        batch_root=batch_root, runs_root=batch_root / "runs",
        manifest=manifest, identity=identity, export_policy=export_policy,
        terminal=terminal)
    lines = (batch_root / "merged" / "predictions.jsonl").read_text() \
        .strip().splitlines()
    assert len(lines) == 3
    rows = [json.loads(l) for l in lines]
    assert rows[0] == {"route_id": manifest["route_order"][0],
                       "root_smiles": substrates[0], "steps": []}
    kinds = {r["route_id"]: r["answer_kind"] for r in merged["per_route"]}
    assert kinds[manifest["route_order"][0]] == "fallback_empty"


def test_api_account_counts_and_unknown_cost(tmp_path):
    """API 账目:issued/响应/孤儿计数;usage 缺失 → 费用 unknown。"""
    runs_root = tmp_path / "runs"
    run_dir = runs_root / "r-a"
    (run_dir / "results" / "T1").mkdir(parents=True)
    call = {"schema_version": "v43-artifact-1", "payload": {"status": "issued"}}
    (run_dir / "results" / "T1" / "prediction_call.a1.json").write_text(
        json.dumps(call))
    resp = {"schema_version": "v43-artifact-1", "payload": {
        "status": "completed",
        "transport": {"ok": True, "elapsed_s": 1.5,
                      "usage": {"prompt_tokens": 100,
                                "completion_tokens": 200,
                                "total_tokens": 300}},
    }}
    (run_dir / "results" / "T1" / "prediction_response.a1.json").write_text(
        json.dumps(resp))
    orphan = {"schema_version": "v43-artifact-1",
              "payload": {"orphan": "x"}}
    (run_dir / "results" / "T1" / "prediction_orphan.a1.json").write_text(
        json.dumps(orphan))
    # 第二个 run:响应无 usage → 该路线 usage_missing
    run_b = runs_root / "r-b" / "results" / "T2"
    run_b.mkdir(parents=True)
    resp2 = {"schema_version": "v43-artifact-1", "payload": {
        "status": "completed", "transport": {"ok": True, "elapsed_s": 0.5}}}
    (run_b / "prediction_response.a1.json").write_text(json.dumps(resp2))
    account = api_account(runs_root, ["r-a", "r-b"],
                          price_snapshot={"input_cny_per_m": 0.8,
                                          "output_cny_per_m": 2.8,
                                          "cache_read_cny_per_m": 0.23})
    t = account["totals"]
    assert t["n_calls_issued"] == 1
    assert t["n_responses"] == 2
    assert t["n_orphaned"] == 1
    assert t["input_tokens"] == 100
    assert t["output_tokens"] == 200
    assert t["n_usage_missing"] == 1
    assert account["cost_estimate_cny"] == "unknown", \
        "usage 不完整时费用必须 unknown,不得估算冒充实测"


def test_run_id_stable_and_contains_batch_and_route():
    assert run_id_for_route("abc12345", "dev", "pb_0002") == \
        "dev_abc12345_pb_0002"
    assert run_id_for_route("abc12345", "dev", "pb_0002") == \
        run_id_for_route("abc12345", "dev", "pb_0002")


def test_identity_conflict_rejected(tmp_path):
    """同批次根不同身份 → 结构化冲突(不静默覆盖)。"""
    from pathway_v43.batch import BatchConflict, batch_identity_conflict_check

    batch_root = tmp_path / "batch"
    batch_root.mkdir()
    manifest = _make_manifest(tmp_path, 1, ["CCO"])
    config, export_policy, identity = _batch_identity_for(
        tmp_path, manifest, tmp_path / "input_manifest.json")
    (batch_root / "batch_identity.json").write_text(
        json.dumps({"sha256": "different"}) )
    with pytest.raises(BatchConflict):
        batch_identity_conflict_check(batch_root, identity)


def test_capacity_blocked_not_serialized(tmp_path, monkeypatch):
    """内存不足 → CapacityBlocked(明确容量阻塞,不暗改串行)。"""
    from pathway_v43.batch import CapacityBlocked, precheck_capacity

    config = load_batch_config()
    monkeypatch.setattr("pathway_v43.batch._total_memory_gb", lambda: 1.0)
    with pytest.raises(CapacityBlocked) as exc:
        precheck_capacity(tmp_path, config)
    assert "内存不足" in str(exc.value)


def test_in_process_worker_runs_and_exports(tmp_path):
    """run_worker(注入合成检索器):run → 导出 → 终态状态文件。"""
    substrates = ["CCO"]
    manifest = _make_manifest(tmp_path, 1, substrates)
    config, export_policy, identity = _batch_identity_for(
        tmp_path, manifest, tmp_path / "input_manifest.json")
    scripted = _scripted_fixture(substrates)
    finder = ScriptedReactionFinder(scripted)
    runs_root = tmp_path / "runs"
    status = run_worker(
        config=resolve_config(), runs_root=runs_root,
        run_id="dev_t_pb_0000", root_smiles="CCO", route_id="pb_0000",
        model_setup=None, budgets=config["budgets"],
        export_policy=export_policy,
        status_path=tmp_path / "workers" / "pb_0000.status.json",
        finder=finder,
    )
    assert status["stop_reason"] == "completed"
    assert status["export_ok"] is True
    line = json.loads(
        (runs_root / "dev_t_pb_0000" / "predictions.jsonl").read_text())
    assert line["route_id"] == "pb_0000"
    assert line["steps"][0]["predicted_products"] == ["CC=O"]
