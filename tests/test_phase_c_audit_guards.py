"""Phase C 离线审计守卫(R2 复核):金标覆盖门禁的端到端夹具。

最小假封存(tmp_path,零 API、不触真实封存)直接驱动
``scripts/phase_c_offline_audit.py`` 子进程:
- 全部任务 qid ∈ 金标且唯一 → 0 退出,summary 记录覆盖事实;
- 金标缺一题 → 非 0 退出(R2 反例:初版只拒零交集,缺一题仍 0 退出,
  缺题的诊断匹配被静默当成 false);
- 任务 qid 重复(两任务同题)→ 非 0 退出。
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "phase_c_offline_audit.py"

_SMI = "CCO"


def _make_task_dir(agent: Path, qid: str, tag: str = "1") -> None:
    run_dir = agent / f"exam298_batch{tag}_{qid}"
    task = run_dir / "results" / "t_pred"
    task.mkdir(parents=True)
    (task / "prediction_task.json").write_text(json.dumps({"payload": {
        "mode": "analogy_edit",
        "path_id": "p1",
        "current": {"smiles_canonical": _SMI,
                    "atom_ids": ["S_C_1", "S_C_2", "S_O_1"]},
        "candidates": [],
        "donor": None,
    }}, ensure_ascii=False))
    (task / "prediction.json").write_text(json.dumps({"payload": {
        "outcome": "abstained", "reason": "fixture"}}))
    ret = run_dir / "results" / "t_ret"
    ret.mkdir(parents=True)
    (ret / "retrieval.json").write_text(json.dumps({"payload": {
        "query": {"path_id": "p1", "substrate_identity": _SMI},
        "evidences": []}}))


def _build_seal(root: Path, qids: list[str], gold_qids: list[str]) -> \
        tuple[Path, Path, Path]:
    agent = root / "agent_runs"
    agent.mkdir(parents=True)
    for q in qids:
        _make_task_dir(agent, q)
    gold = root / "gold.jsonl"
    gold.write_text("".join(
        json.dumps({"qid": q, "products_smiles": [_SMI]}) + "\n"
        for q in gold_qids), encoding="utf-8")
    out = root / "out"
    return agent, gold, out


def _run_audit(agent: Path, gold: Path, out: Path) -> subprocess.CompletedProcess:
    env = dict(os.environ, OMP_NUM_THREADS="1")
    return subprocess.run(
        [sys.executable, str(SCRIPT),
         "--seal-run-dir", str(agent.parent),
         "--gold", str(gold),
         "--out-dir", str(out)],
        capture_output=True, text=True, env=env, timeout=120)


def test_audit_passes_when_all_task_qids_in_gold_and_unique(tmp_path):
    qid = "RXNG_" + "a" * 64
    agent, gold, out = _build_seal(tmp_path, [qid], [qid])
    r = _run_audit(agent, gold, out)
    assert r.returncode == 0, r.stderr
    summary = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    assert summary["n_analogy_tasks"] == 1
    assert summary["n_task_qids_found_in_gold"] == 1
    assert summary["n_task_qids_missing_from_gold"] == 0
    assert summary["n_task_qids_duplicate"] == 0
    assert summary["n_gold_duplicate_qids"] == 0
    assert summary["gold_coverage_gate"] == \
        "task_qids_covered_unique_and_gold_rows_unique"


def test_audit_fails_when_gold_missing_one_qid(tmp_path):
    """R2 反例夹具:金标缺一题 → 审计必须失败,不产出缺题诊断列。"""
    q1, q2 = "RXNG_" + "a" * 64, "RXNG_" + "b" * 64
    agent, gold, out = _build_seal(tmp_path, [q1, q2], [q1, q2])
    # 从金标只删去一题
    lines = gold.read_text(encoding="utf-8").splitlines(keepends=True)
    gold.write_text("".join(l for l in lines if q1 in l), encoding="utf-8")
    r = _run_audit(agent, gold, out)
    assert r.returncode == 2, (r.returncode, r.stdout, r.stderr)
    assert "FAIL" in r.stderr
    assert not (out / "summary.json").exists()


def test_audit_fails_on_empty_gold(tmp_path):
    qid = "RXNG_" + "a" * 64
    agent, gold, out = _build_seal(tmp_path, [qid], [qid])
    gold.write_text("", encoding="utf-8")
    r = _run_audit(agent, gold, out)
    assert r.returncode == 2
    assert "FAIL" in r.stderr


def test_audit_fails_on_duplicate_task_qids(tmp_path):
    """两任务同题(qid 重复)→ 唯一性门禁失败。"""
    qid = "RXNG_" + "a" * 64
    agent, gold, out = _build_seal(tmp_path, [qid], [qid])
    _make_task_dir(agent, qid, tag="2")  # 第二个 run 目录,同 qid
    r = _run_audit(agent, gold, out)
    assert r.returncode == 2, (r.returncode, r.stdout, r.stderr)
    assert "FAIL" in r.stderr


def test_audit_fails_on_duplicate_gold_rows(tmp_path):
    """三审反例:金标**同一 qid 写两行** → 索引会被 dict 静默覆盖,
    门禁必须失败,不得照常产出 summary(此前只测了任务 qid 重复)。"""
    qid = "RXNG_" + "a" * 64
    agent, gold, out = _build_seal(tmp_path, [qid], [qid])
    with open(gold, "a", encoding="utf-8") as f:
        f.write(json.dumps({"qid": qid, "products_smiles": ["CCC"]}) + "\n")
    r = _run_audit(agent, gold, out)
    assert r.returncode == 2, (r.returncode, r.stdout, r.stderr)
    assert "FAIL" in r.stderr and "金标行重复" in r.stderr
    assert not (out / "summary.json").exists()
