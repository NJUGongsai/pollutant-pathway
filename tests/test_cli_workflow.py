"""CLI run/resume/inspect 契约(结构化输出;真实引擎 case 带 slow 标记)。"""

from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

from conftest import REPO_ROOT


def _cli(*args: str, env_extra: dict | None = None):
    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO_ROOT / "src")
    env["OMP_NUM_THREADS"] = "1"
    env.pop("PATHWAY_V43_DEBUG", None)
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        [sys.executable, "-m", "pathway_v43", *args],
        capture_output=True, text=True, timeout=600, env=env,
        cwd=str(REPO_ROOT),
    )


def _payload(proc) -> dict:
    """stdout 必须是纯净 JSON(引擎横幅已改道 stderr)。"""
    return json.loads(proc.stdout)


def test_inspect_missing_run(tmp_path):
    proc = _cli("inspect", "--run-id", "nope", "--runs-root", str(tmp_path))
    assert proc.returncode == 0
    payload = _payload(proc)
    assert payload["status"] == "no_report_yet"
    assert payload["exists"] is False


def test_resume_missing_run_structured_failure(tmp_path):
    proc = _cli("resume", "--run-id", "nope", "--runs-root", str(tmp_path))
    assert proc.returncode == 2
    payload = _payload(proc)
    assert payload["ok"] is False
    assert payload["error"]["type"] == "RunNotFound"


def test_resume_scripted_run_without_finder_structured_failure(tmp_path):
    """scripted 夹具 run 的 CLI resume 必须结构化拒绝(无法重建脚本检索器)。"""
    from pathway_v43.adapters.v3_engine import v3_code_identity
    from pathway_v43.config import resolve_config
    from pathway_v43.domain.identity import cn_identity
    from pathway_v43.domain.models import STRATEGY_VERSION
    from pathway_v43.storage.run_identity import (
        build_run_identity, scripted_asset_identity, write_run_identity)

    config = resolve_config()
    identity = build_run_identity(
        run_id="scr1", root_smiles="Oc1ccccc1O",
        root_cn=cn_identity("Oc1ccccc1O"),
        strategy={"version": STRATEGY_VERSION, "max_depth": 2,
                  "max_expansions": 3, "max_frontier_width": 1,
                  "max_llm_calls": 0, "max_proposals": 0},
        asset_identity=scripted_asset_identity(),
        v3_code_identity=v3_code_identity(config.v3_code_root),
    )
    write_run_identity(tmp_path, identity)
    proc = _cli("resume", "--run-id", "scr1", "--runs-root", str(tmp_path))
    assert proc.returncode == 2
    payload = _payload(proc)
    assert payload["ok"] is False
    assert payload["error"]["type"] == "RunError"


@pytest.mark.slow
def test_real_run_inspect_resume_smoke(tmp_path):
    """验收命令口径的真实烟测:catechol → 停在 awaiting_prediction。

    run/inspect/resume 全部走 CLI 子进程;stdout 必须为纯净 JSON
    (v3 引擎装载横幅不再污染 stdout —— 本断言即回归钉子)。
    """
    runs_root = tmp_path / "runs"
    proc = _cli("run", "--smiles", "Oc1ccccc1O", "--run-id", "v43-smoke",
                "--max-depth", "2", "--max-expansions", "3",
                "--runs-root", str(runs_root))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    summary = _payload(proc)
    assert summary["ok"] is True
    assert summary["stop_reason"] == "awaiting_prediction"
    assert summary["counts"]["reaction_events"] == 0
    assert summary["counts"]["path_instances"] == 1

    # inspect:区分待预测(而非异常停止)
    proc = _cli("inspect", "--run-id", "v43-smoke", "--runs-root",
                str(runs_root))
    assert proc.returncode == 0
    inspection = _payload(proc)
    assert inspection["status"] == "awaiting_prediction"
    assert inspection["summary"]["n_awaiting_prediction"] == 1

    # resume:已完成 run 幂等恢复,不新增任何事实
    proc = _cli("resume", "--run-id", "v43-smoke", "--runs-root",
                str(runs_root))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    resumed = _payload(proc)
    assert resumed["resumed"] is True
    assert resumed["counts"] == summary["counts"]
    assert resumed["graph_revision"] == summary["graph_revision"]

    # 重复 run 同 run-id → 结构化拒绝
    proc = _cli("run", "--smiles", "Oc1ccccc1O", "--run-id", "v43-smoke",
                "--runs-root", str(runs_root))
    assert proc.returncode == 2
    payload = _payload(proc)
    assert payload["error"]["type"] == "RunAlreadyExists"

    # 报告可读且含证据与资产身份;待预测路径同样报告 top-5 候选(P2 修复)
    report = json.loads(
        (runs_root / "v43-smoke" / "report" / "pathway.json").read_text())
    root = report["path_instances"][0]
    assert root["status"] == "awaiting_prediction"
    kinds = {c["kind"] for c in root["evidence"]["considered"]}
    assert "recorded_reaction" in kinds
    top5 = root["top5_candidates"]
    assert len(top5) == 5
    assert [c["retrieval_rank"] for c in top5] == [1, 2, 3, 4, 5]
    assert {c["kind"] for c in top5[:3]} == {"recorded_reaction"}
    assert report["summary"]["top5_reported_paths"], "待预测路径必须有 top-5 报告"
    # 逐卡溯源(P1 修复):检索产物中每张卡都有资产文件与清单一致哈希
    retrieval_files = list((runs_root / "v43-smoke" / "results")
                           .glob("*/retrieval.json"))
    manifest = dict(
        line.rsplit("  ", 1)[::-1]
        for line in (REPO_ROOT / "assets" / "MANIFEST.sha256")
        .read_text().splitlines() if line.strip()
    )
    envelope = json.loads(retrieval_files[0].read_text())
    for ev in envelope["payload"]["evidences"]:
        assert ev["asset_file"] in manifest
        assert manifest[ev["asset_file"]] == ev["asset_sha256"]
        # 组合来源逐成分溯源(P2 修复回归):每个成分的哈希与清单一致
        assert ev["asset_sources"]
        assert ev["asset_sources"][0]["asset_file"] == ev["asset_file"]
        for src in ev["asset_sources"]:
            assert src["asset_file"] in manifest
            assert manifest[src["asset_file"]] == src["asset_sha256"]
    # recorded 卡库名与实际文件同源(P2 修复回归)
    recorded_cards = [e for e in envelope["payload"]["evidences"]
                      if e["kind"] == "recorded_reaction"]
    assert all(c["source_record"]["library_file"] == c["asset_file"]
               for c in recorded_cards)
    assert all(c["source_record"]["library_file"].endswith("library_full.jsonl")
               for c in recorded_cards)
