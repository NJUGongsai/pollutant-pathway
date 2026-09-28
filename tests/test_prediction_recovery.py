"""预测分支崩溃恢复实测(子进程硬杀 + 新进程恢复)— 验收 §5.5。

覆盖:响应落盘后恢复(不重复调用/不重复事件)、事件提交后恢复(幂等重放)、
"请求已发出但响应未落盘"的悬空状态(孤儿审计卡 + 显式重试,不声称恰好
一次)、预测身份漂移拒绝、无模型 resume 拒绝。全部用 fake 模型(计数文件
跨进程累加),无凭证可跑。
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from pathway_v43.domain.identity import cn_identity

from conftest import REPO_ROOT
from wf_helpers import CATECHOL, load_report

S = cn_identity(CATECHOL)
P1 = cn_identity("O=CCC=CO")
P2 = cn_identity("CC(O)=O")
DRIVER = REPO_ROOT / "tests" / "recovery_driver.py"

NOVEL_OK = json.dumps({
    "decision": "propose",
    "products": [{"smiles": "O=CCC=CO", "note": "氧化"},
                 {"smiles": "CC(O)=O", "note": "水解"}],
    "uncertainty": "high", "reason": "恢复测试固定提案",
})

NOVEL_ABSTAIN = json.dumps({
    "decision": "abstain", "reason": "无证据路径,模型弃权(恢复测试)"})


def _fixture() -> dict:
    from wf_helpers import evidence

    return {S: [evidence("btR1", "rule_application", S, [],
                         match_type="rule_template")]}


def _dead_end_fixture() -> dict:
    """检索零证据 → 决策 dead_end → 路由 novel_proposal
    (报告 §12.5"novel 弃权=dead_end"判据的前半)。"""
    return {S: []}


def _write(tmp_path: Path, name: str, obj: dict) -> Path:
    p = tmp_path / name
    p.write_text(json.dumps(obj), encoding="utf-8")
    return p


def _driver(mode: str, runs_root: Path, run_id: str, tmp_path: Path,
            crash_after: str | None = None, model: str = "fake",
            migrate_from: str | None = None, fixture: dict | None = None,
            fake_script: dict | None = None):
    env = dict(os.environ)
    env["OMP_NUM_THREADS"] = "1"
    cmd = [sys.executable, str(DRIVER), mode,
           "--runs-root", str(runs_root), "--run-id", run_id,
           "--smiles", CATECHOL,
           "--scripted", str(_write(tmp_path, f"fx_{run_id}.json",
                                    fixture if fixture is not None
                                    else _fixture())),
           "--fake-script",
           str(_write(tmp_path, "fake.json",
                      fake_script if fake_script is not None
                      else {"novel_proposal": [NOVEL_OK]})),
           "--llm-counter", str(tmp_path / f"llm_{run_id}.txt"),
           "--max-depth", "1", "--max-expansions", "2",
           "--max-frontier-width", "2",
           "--model", model]
    if crash_after:
        cmd += ["--crash-after", crash_after]
    if migrate_from:
        cmd += ["--migrate-from", migrate_from]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=600,
                          env=env)


def _summary(proc) -> dict:
    for line in proc.stdout.splitlines():
        if line.startswith("SUMMARY "):
            return json.loads(line[len("SUMMARY "):])
    raise AssertionError(f"驱动无 SUMMARY 输出:{proc.stdout} {proc.stderr}")


def _task_results(runs_root: Path, run_id: str, name: str) -> list:
    """读取 results/<task_id>/ 下产物:name 精确("prediction.json")或
    前缀("prediction_call" → 全部 .aN 变体)。"""
    out = []
    results = runs_root / run_id / "results"
    if not results.is_dir():
        return out
    for task_dir in sorted(results.iterdir()):
        if not task_dir.is_dir():
            continue
        pattern = name if name.endswith(".json") else f"{name}.a*.json"
        for p in sorted(task_dir.glob(pattern)):
            out.append(json.loads(p.read_text(encoding="utf-8"))["payload"])
    return out


def test_crash_after_response_persisted_no_recall_no_duplicate(tmp_path):
    """响应落盘后、prediction.json 前硬杀:恢复不重复调用、不重复事件。"""
    runs_root = tmp_path / "runs"
    proc = _driver("run", runs_root, "pr1", tmp_path,
                   crash_after="call_model_response")
    assert proc.returncode == 70, proc.stdout + proc.stderr
    llm_counter = tmp_path / "llm_pr1.txt"
    assert llm_counter.read_text() == "1"  # 恰好一次调用
    # prediction.json 尚未写(崩溃点在响应落盘后)
    assert _task_results(runs_root, "pr1", "prediction.json") == []

    proc2 = _driver("resume", runs_root, "pr1", tmp_path)
    assert proc2.returncode == 0, proc2.stdout + proc2.stderr
    summary = _summary(proc2)
    assert llm_counter.read_text() == "1", "恢复不得重复调用模型"
    preds = _task_results(runs_root, "pr1", "prediction.json")
    assert len(preds) == 1 and preds[0]["outcome"] == "proposed"
    # 事件恰好一条(2 产物),无重复
    assert summary["counts"]["reaction_events"] == 1
    assert summary["counts"]["event_products"] == 2
    assert summary["counts"]["path_instances"] == 3
    assert summary["budget"]["used_llm_calls"] == 1
    assert summary["budget"]["used_proposals"] == 1
    # 无孤儿(响应在,请求不悬空)
    assert _task_results(runs_root, "pr1", "prediction_orphan") == []


def test_crash_after_commit_resume_replays_prediction_idempotently(tmp_path):
    """事件提交后硬杀:恢复重放 prediction→validate→submit 幂等,无重复。"""
    runs_root = tmp_path / "runs"
    proc = _driver("run", runs_root, "pr2", tmp_path,
                   crash_after="commit_pathway")
    assert proc.returncode == 70, proc.stdout + proc.stderr
    llm_counter = tmp_path / "llm_pr2.txt"
    assert llm_counter.read_text() == "1"
    counts_after = _store_counts(runs_root, "pr2")
    assert counts_after["reaction_events"] == 1

    proc2 = _driver("resume", runs_root, "pr2", tmp_path)
    assert proc2.returncode == 0, proc2.stdout + proc2.stderr
    summary = _summary(proc2)
    assert llm_counter.read_text() == "1", "重放不得再次调用模型"
    counts = summary["counts"]
    for key in ("reaction_events", "event_products", "path_instances",
                "graph_revision"):
        assert counts[key] == counts_after[key], key
    assert summary["budget"]["used_llm_calls"] == 1


def test_crash_after_prediction_recorded_novel_abstain_resumes_dead_end(tmp_path):
    """novel 弃权 + prediction_recorded 后硬杀:恢复重放经 apply_prediction
    落账,与正常路径同判据(novel 弃权=dead_end,报告 §12.5),不再错标
    awaiting_prediction(修复前 _novel_route 恒空 → 两种账本状态)。"""
    runs_root = tmp_path / "runs"
    proc = _driver("run", runs_root, "pr6", tmp_path,
                   crash_after="prediction_recorded",
                   fixture=_dead_end_fixture(),
                   fake_script={"novel_proposal": [NOVEL_ABSTAIN]})
    assert proc.returncode == 70, proc.stdout + proc.stderr
    preds = _task_results(runs_root, "pr6", "prediction.json")
    assert len(preds) == 1
    assert preds[0]["outcome"] == "abstained"
    assert preds[0]["mode"] == "novel_proposal"
    assert (tmp_path / "llm_pr6.txt").read_text() == "1"

    proc2 = _driver("resume", runs_root, "pr6", tmp_path)
    assert proc2.returncode == 0, proc2.stdout + proc2.stderr
    summary = _summary(proc2)
    assert summary["stop_reason"] != "awaiting_prediction"
    assert summary["stop_reason"] == "completed"
    root = load_report(runs_root, "pr6")["path_instances"][0]
    assert root["status"] == "dead_end"
    assert "model_abstain" in root["status_reason"]
    assert (tmp_path / "llm_pr6.txt").read_text() == "1", "恢复不得重复调用"


def test_crash_after_prediction_recorded_novel_failure_resumes_dead_end(tmp_path):
    """novel 解析失败(空响应剧本,重试上限内全败)+ 同崩溃点:恢复后同样
    dead_end,不重复调用;run 不停在 awaiting_prediction。"""
    runs_root = tmp_path / "runs"
    proc = _driver("run", runs_root, "pr7", tmp_path,
                   crash_after="prediction_recorded",
                   fixture=_dead_end_fixture(),
                   fake_script={"novel_proposal": ["", "", ""]})
    assert proc.returncode == 70, proc.stdout + proc.stderr
    preds = _task_results(runs_root, "pr7", "prediction.json")
    assert len(preds) == 1 and preds[0]["outcome"] == "failed"
    counter = tmp_path / "llm_pr7.txt"
    assert counter.read_text() == "3"  # 首次 + 2 次重试(上限)

    proc2 = _driver("resume", runs_root, "pr7", tmp_path)
    assert proc2.returncode == 0, proc2.stdout + proc2.stderr
    summary = _summary(proc2)
    assert summary["stop_reason"] != "awaiting_prediction"
    assert counter.read_text() == "3", "恢复重放不得再次调用模型"
    root = load_report(runs_root, "pr7")["path_instances"][0]
    assert root["status"] == "dead_end"
    assert "prediction_failed" in root["status_reason"]


def test_dangling_request_orphan_audited_then_retried_once(tmp_path):
    """悬空调用:请求已登记、响应未落盘 → 孤儿审计卡 + 恰好一次重试。"""
    runs_root = tmp_path / "runs"
    proc = _driver("run", runs_root, "pr3", tmp_path,
                   crash_after="call_model")
    assert proc.returncode == 70, proc.stdout + proc.stderr
    llm_counter = tmp_path / "llm_pr3.txt"
    # 崩溃点在调用记录落盘后、模型调用前:counter 尚为 0,
    # 但请求**可能**已发出 —— 恢复侧不得假定没有,必须按悬空处置
    calls = _task_results(runs_root, "pr3", "prediction_call")
    assert len(calls) == 1 and calls[0]["status"] == "issued"

    proc2 = _driver("resume", runs_root, "pr3", tmp_path)
    assert proc2.returncode == 0, proc2.stdout + proc2.stderr
    summary = _summary(proc2)
    # 孤儿审计卡:记录悬空请求与处置方式
    orphans = _task_results(runs_root, "pr3", "prediction_orphan")
    assert len(orphans) == 1
    assert orphans[0]["orphan"] == "request_issued_no_response"
    assert orphans[0]["disposition"] == "retried_as_attempt_2"
    # 重试恰好一次新调用(计数文件 = 新进程真实调用数),不声称恰好一次
    assert llm_counter.read_text() == "1"
    calls = _task_results(runs_root, "pr3", "prediction_call")
    assert len(calls) == 2  # a1(悬空)+ a2(重试)
    assert calls[1]["attempt"] == 2
    assert summary["counts"]["reaction_events"] == 1
    assert summary["budget"]["used_llm_calls"] == 2  # 悬空也计费,如实记账


def test_prediction_identity_drift_rejected_on_resume(tmp_path):
    """预测身份漂移(模型/提示词块被改)→ resume 结构化拒绝。"""
    runs_root = tmp_path / "runs"
    proc = _driver("run", runs_root, "pr4", tmp_path)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    identity_path = runs_root / "pr4" / "run_identity.json"
    identity = json.loads(identity_path.read_text())
    assert identity["prediction"]["enabled"] is True
    assert identity["prediction"]["provider"] == "fake"
    assert identity["molecode"]["upstream_commit"]
    identity["prediction"]["model_id"] = "tampered-model"
    identity_path.write_text(json.dumps(identity, ensure_ascii=False,
                                        indent=2, sort_keys=True))
    proc2 = _driver("resume", runs_root, "pr4", tmp_path)
    assert proc2.returncode == 2
    payload = json.loads(proc2.stdout.strip().splitlines()[-1])
    assert payload["ok"] is False
    assert payload["error"]["type"] == "IdentityMismatch"


def test_resume_with_model_off_rejected_when_prediction_enabled(tmp_path):
    """已启用模型的 run 用无模型 resume → 结构化拒绝,不静默降级。"""
    runs_root = tmp_path / "runs"
    proc = _driver("run", runs_root, "pr5", tmp_path)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    proc2 = _driver("resume", runs_root, "pr5", tmp_path, model="off")
    assert proc2.returncode == 2
    payload = json.loads(proc2.stdout.strip().splitlines()[-1])
    assert payload["ok"] is False
    assert "相同身份重建模型" in payload["error"]["message"]


def test_phase1_style_run_resume_rejected_then_migrate_from_works(tmp_path):
    """第一阶段式旧 run:直接 resume 被身份门槛拒绝(显式、fail-closed);
    --migrate-from 显式迁移开新 run,旧目录逐字节未动。"""
    runs_root = tmp_path / "runs"
    # 1) 用当前代码跑一个无模型 run,再剥去 prediction/molecode 身份块,
    #    模拟"第一阶段旧代码写下的 run_identity.json"
    proc = _driver("run", runs_root, "legacy", tmp_path, model="off")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    identity_path = runs_root / "legacy" / "run_identity.json"
    identity = json.loads(identity_path.read_text())
    for key in ("prediction", "molecode"):
        identity.pop(key, None)
    identity_path.write_text(json.dumps(identity, ensure_ascii=False,
                                        indent=2, sort_keys=True))
    def _snapshot(run_dir: Path) -> dict:
        return {
            str(p.relative_to(run_dir)): p.read_bytes()
            for p in sorted(run_dir.rglob("*")) if p.is_file()
        }

    before = _snapshot(runs_root / "legacy")

    proc2 = _driver("resume", runs_root, "legacy", tmp_path, model="off")
    assert proc2.returncode == 2
    payload = json.loads(proc2.stdout.strip().splitlines()[-1])
    assert payload["error"]["type"] == "IdentityMismatch"

    # 2) 显式迁移:新 run 继承输入/策略,旧目录零改动
    proc3 = _driver("run", runs_root, "legacy-migrated", tmp_path,
                    model="off", migrate_from="legacy")
    assert proc3.returncode == 0, proc3.stdout + proc3.stderr
    assert before == _snapshot(runs_root / "legacy"), "迁移不得改动旧 run 目录"
    new_identity = json.loads(
        (runs_root / "legacy-migrated" / "run_identity.json").read_text())
    assert new_identity["migrated_from"]["from_run_id"] == "legacy"
    assert new_identity["inputs"]["root_smiles"] == CATECHOL
    assert new_identity["prediction"] == {
        "enabled": False, "provider": "off", "model_id": "",
        "prompt_versions": {}, "policy_version": "v43-predpol-3",
        "policy": {},
    }
    # 旧 run 自身仍不可 resume(不改写旧身份)
    proc4 = _driver("resume", runs_root, "legacy", tmp_path, model="off")
    assert proc4.returncode == 2


def _store_counts(runs_root: Path, run_id: str) -> dict:
    from pathway_v43.storage.pathway_store import PathwayStore

    st = PathwayStore(runs_root / run_id / "pathway.sqlite")
    try:
        return st.counts()
    finally:
        st.close()
