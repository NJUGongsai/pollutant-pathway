"""崩溃恢复实测 —— 在检索落盘后 / 事件提交后硬杀进程,再于新进程恢复。

验收 5:事件/路径/检索调用不重复;同键不同内容报错(存储层在
test_pathway_store.py)。子进程真实中断(os._exit(70)),父进程断言。
"""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

from conftest import REPO_ROOT
from pathway_v43.domain.identity import cn_identity

from wf_helpers import CATECHOL

S = cn_identity(CATECHOL)
P1 = cn_identity("O=CCC=CO")
P2 = cn_identity("CC(O)=O")
DRIVER = REPO_ROOT / "tests" / "recovery_driver.py"


def _fixture(root_cn: str, p1: str, p2: str) -> dict:
    from wf_helpers import evidence

    def rec(rid, reactant, prods):
        return evidence(rid, "recorded_reaction", reactant, prods)

    def rule(rid, reactant, prods):
        return evidence(rid, "rule_application", reactant, prods,
                        match_type="rule_template")

    return {
        root_cn: [rec("btR1", root_cn, ["O=CCC=CO", "CC(O)=O"])],
        p1: [rule("btR2", p1, ["O=CC=CO"])],
        # p2 无证据 → dead_end
    }


def _driver(mode: str, runs_root: Path, run_id: str, scripted: Path,
            counter: Path, crash_after: str | None = None):
    env = dict(os.environ)
    env["OMP_NUM_THREADS"] = "1"
    cmd = [sys.executable, str(DRIVER), mode,
           "--runs-root", str(runs_root), "--run-id", run_id,
           "--smiles", CATECHOL, "--scripted", str(scripted),
           "--counter", str(counter), "--max-depth", "2",
           "--max-frontier-width", "2"]
    if crash_after:
        cmd += ["--crash-after", crash_after]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=600,
                          env=env)


def _summary(proc) -> dict:
    for line in proc.stdout.splitlines():
        if line.startswith("SUMMARY "):
            return json.loads(line[len("SUMMARY "):])
    raise AssertionError(f"驱动无 SUMMARY 输出:{proc.stdout} {proc.stderr}")


def _store_counts(runs_root: Path, run_id: str) -> dict:
    from pathway_v43.storage.pathway_store import PathwayStore

    st = PathwayStore(runs_root / run_id / "pathway.sqlite")
    try:
        return st.counts()
    finally:
        st.close()


def _write_scripted(tmp_path: Path, scripted: dict) -> Path:
    p = tmp_path / "scripted_fixture.json"
    p.write_text(json.dumps(scripted), encoding="utf-8")
    return p


def test_clean_run_baseline(tmp_path):
    """同夹具无崩溃基线:恢复测试以此为对照。"""
    runs_root = tmp_path / "runs"
    fixture = _write_scripted(tmp_path, _fixture(S, P1, P2))
    counter = tmp_path / "counter.txt"
    proc = _driver("run", runs_root, "base1", fixture, counter)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    summary = _summary(proc)
    assert summary["stop_reason"] == "awaiting_prediction"
    assert summary["counts"]["reaction_events"] == 1
    assert summary["counts"]["path_instances"] == 3
    # 真实检索调用 = 根 + P1 + P2(每个任务恰好一次)
    assert counter.read_text() == "3"


def test_crash_after_retrieval_persisted_then_resume(tmp_path):
    """检索落盘后硬杀:恢复后无重复检索、无重复事件、计数一致。"""
    runs_root = tmp_path / "runs"
    fixture = _write_scripted(tmp_path, _fixture(S, P1, P2))
    counter = tmp_path / "counter.txt"
    proc = _driver("run", runs_root, "rec1", fixture, counter,
                   crash_after="retrieve_reactions")
    assert proc.returncode == 70, proc.stdout + proc.stderr  # 硬杀,非异常
    assert int(counter.read_text()) == 1  # 根检索已执行并落盘
    # 检索产物已在盘上
    results = list((runs_root / "rec1" / "results").glob("*/retrieval.json"))
    assert len(results) == 1

    proc2 = _driver("resume", runs_root, "rec1", fixture, counter)
    assert proc2.returncode == 0, proc2.stdout + proc2.stderr
    summary = _summary(proc2)
    assert summary["resumed"] is True
    assert summary["stop_reason"] == "awaiting_prediction"
    counts = summary["counts"]
    assert counts["reaction_events"] == 1
    assert counts["event_products"] == 2
    assert counts["path_instances"] == 3
    # 检索调用不重复:根(崩溃前)+ P1 + P2(恢复后)= 3,根未重查
    assert counter.read_text() == "3"
    assert len(list((runs_root / "rec1" / "results").glob("*/retrieval.json"))) == 3
    # 与无崩溃基线一致(同一夹具的绝对计数)
    assert counts["compounds"] == 3  # S, P1, P2
    assert counts["graph_revision"] == 1


def test_crash_after_commit_then_resume_no_duplicate(tmp_path):
    """事件提交后、checkpoint 前硬杀:恢复重放 submit_event 不重复入账。"""
    runs_root = tmp_path / "runs"
    fixture = _write_scripted(tmp_path, _fixture(S, P1, P2))
    counter = tmp_path / "counter.txt"
    proc = _driver("run", runs_root, "rec2", fixture, counter,
                   crash_after="commit_pathway")
    assert proc.returncode == 70, proc.stdout + proc.stderr
    # 账本已提交(崩溃前):1 事件已入 SQLite
    counts_after_crash = _store_counts(runs_root, "rec2")
    assert counts_after_crash["reaction_events"] == 1
    assert counts_after_crash["event_products"] == 2

    proc2 = _driver("resume", runs_root, "rec2", fixture, counter)
    assert proc2.returncode == 0, proc2.stdout + proc2.stderr
    summary = _summary(proc2)
    counts = summary["counts"]
    # 幂等:事件/产物/路径/revision 无重复
    for key in ("reaction_events", "event_products", "path_instances"):
        assert counts[key] == counts_after_crash[key], key
    assert counts["graph_revision"] == counts_after_crash["graph_revision"]
    assert summary["stop_reason"] == "awaiting_prediction"
    # 检索计数:根 1(不重查)+ P1 + P2
    assert counter.read_text() == "3"


def test_resume_budget_respects_run_identity_limit(tmp_path):
    """P1 修复回归:max_expansions=1 时,无崩溃与崩溃恢复都停在 budget_exhausted。

    预算记账以持久事实(已落盘检索产物数)为准:检索落盘后中断再恢复,
    used_expansions 仍为 1,P1/P2 不被探索,不再突破展开预算。
    """
    runs_root = tmp_path / "runs"
    fixture = _write_scripted(tmp_path, _fixture(S, P1, P2))

    def _driver1(mode, run_id, crash=None):
        env = dict(os.environ)
        env["OMP_NUM_THREADS"] = "1"
        cmd = [sys.executable, str(DRIVER), mode,
               "--runs-root", str(runs_root), "--run-id", run_id,
               "--smiles", CATECHOL, "--scripted", str(fixture),
               "--counter", str(tmp_path / f"cnt_{run_id}.txt"),
               "--max-depth", "2", "--max-expansions", "1",
               "--max-frontier-width", "2"]
        if crash:
            cmd += ["--crash-after", crash]
        return subprocess.run(cmd, capture_output=True, text=True,
                              timeout=600, env=env)

    # 对照:无崩溃 → budget_exhausted,frontier 2,P1 未检索
    p1 = _driver1("run", "b1")
    assert p1.returncode == 0, p1.stdout + p1.stderr
    s1 = _summary(p1)
    assert s1["stop_reason"] == "budget_exhausted"
    assert s1["counts"]["frontier"] == 2
    assert s1["budget"]["used_expansions"] == 1
    assert (tmp_path / "cnt_b1.txt").read_text() == "1"
    # 崩溃恢复:检索落盘后杀 → resume → 同样 budget_exhausted,不突破预算
    p2 = _driver1("run", "b2", crash="retrieve_reactions")
    assert p2.returncode == 70, p2.stdout + p2.stderr
    p3 = _driver1("resume", "b2")
    assert p3.returncode == 0, p3.stdout + p3.stderr
    s2 = _summary(p3)
    assert s2["stop_reason"] == "budget_exhausted"
    assert s2["counts"]["frontier"] == 2
    assert s2["budget"]["used_expansions"] == 1
    # P1/P2 未被探索:检索计数停在 1(修复前恢复后会继续检索 P1 → 2)
    assert (tmp_path / "cnt_b2.txt").read_text() == "1"


def test_resume_rejects_identity_change(tmp_path):
    """身份变更后 resume 必须拒绝(任务书 §2)。

    模拟资产身份漂移:篡改已存 run_identity 的资产块,resume 重建的当前
    资产身份与之不符 → IdentityMismatch。策略/代码变更由 code_identity
    (含 STRATEGY_VERSION 与策略模块哈希)捕获。
    """
    runs_root = tmp_path / "runs"
    fixture = _write_scripted(tmp_path, _fixture(S, P1, P2))
    counter = tmp_path / "counter.txt"
    proc = _driver("run", runs_root, "sec1", fixture, counter)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    identity_path = runs_root / "sec1" / "run_identity.json"
    identity = json.loads(identity_path.read_text())
    identity["asset_identity"]["manifest_sha256"] = "tampered-sha"
    identity_path.write_text(json.dumps(identity, ensure_ascii=False,
                                        indent=2, sort_keys=True))
    proc2 = _driver("resume", runs_root, "sec1", fixture, counter)
    assert proc2.returncode == 2
    payload = json.loads(proc2.stdout.strip().splitlines()[-1])
    assert payload["ok"] is False
    assert payload["error"]["type"] == "IdentityMismatch"


def test_resume_without_checkpoint_reports_structured_error(tmp_path):
    """首个 checkpoint 前中断(无检查点)→ resume 结构化报错,不静默重跑。"""
    runs_root = tmp_path / "runs"
    # 手工构造只有 run_identity 的 run(模拟 checkpoint 前中断后残留)
    from pathway_v43.adapters.v3_engine import v3_code_identity
    from pathway_v43.config import resolve_config
    from pathway_v43.domain.models import STRATEGY_VERSION
    from pathway_v43.storage.run_identity import (
        build_run_identity, scripted_asset_identity, write_run_identity)

    identity = build_run_identity(
        run_id="nocp", root_smiles=CATECHOL, root_cn=S,
        strategy={"version": STRATEGY_VERSION, "max_depth": 2,
                  "max_expansions": 6, "max_frontier_width": 2,
                  "max_llm_calls": 0, "max_proposals": 0},
        asset_identity=scripted_asset_identity(),
        v3_code_identity=v3_code_identity(resolve_config().v3_code_root),
    )
    write_run_identity(runs_root, identity)
    fixture = _write_scripted(tmp_path, _fixture(S, P1, P2))
    counter = tmp_path / "counter.txt"
    proc = _driver("resume", runs_root, "nocp", fixture, counter)
    assert proc.returncode == 2
    payload = json.loads(proc.stdout.strip().splitlines()[-1])
    assert payload["ok"] is False
    assert "检查点" in payload["error"]["message"]
