"""S3b 回修 r3 回归(Codex S3b-r2 复审唯一残余 P1 S3B-01 的**后段
锚定**;ppv1-runflow-3)。

覆盖(复审 R2 §4 最低收口,入口→行为→可执行断言):
- 两原反例翻转(reviewer recovery_specialist 的 B3/B4 自洽重封装):
  bundle 已写(B3)/事件已提交(B4)硬杀后,**只改 frozen_plan
  artifact**(加注入转换意图、重算该文件 plan_digest 与信封
  payload_hash;旧身份/root task plan_digest/数据库不变)⇒ public
  resume **省略 plan** 结构化拒(frozen_plan_binding_mismatch),
  业务表/event/commit/consume 零变化,原(被改)文件保全 ——
  anchor 覆盖 root retrieve 已 done 的后段(retrieve 执行层核验
  不可达);
- 自洽重封装 + 显式传入同新计划:同样拒(artifact 自洽摘要与
  传入计划互证不是原输入证书;r2 的 frozen_plan_mismatch 只比
  artifact,挡不住这一路径);
- 缺锚/坏锚:根 retrieve 行 plan_digest 被移除 ⇒
  frozen_plan_anchor_missing;锚行 payload plan_digest 被改而
  task_key 落账未动 ⇒ frozen_plan_anchor_corrupt(单一来源
  decision_task_key 重算不同源);均先于任何恢复消费(零变化);
- 正控(父 2bedfc0 亦绿):B3 省略 plan 合法恢复(事件/commit 幂等、
  重复 resume 无新增);合法**原计划**转换恢复(转换 done、followup
  用 phase-1 新上下文 —— 不全面禁转换);同计划显式传入恢复。

红绿分类约定:本文件对直接父基线 2bedfc0 同字节运行 —— 负控为
**行为红**(父上 resume 不拒:省略/显式新 plan 均完成并消费注入
转换/正常补账;缺锚/坏锚不构成拒绝),正控为父绿(r2 已交付行为)。
父上本文件不是 collection 红(全部模块在父已存在)。
"""

from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pathway_v43.config import resolve_config  # noqa: E402
from pathway_v43.domain.models import content_hash  # noqa: E402
from pathway_v43.pollutant.runflow import PPV1RunError  # noqa: E402
from pathway_v43.workflow.runner import resume_run  # noqa: E402

WORKER = str(Path(__file__).resolve().parent / "s3b_worker.py")
PY = sys.executable
ENV = {"PYTHONDONTWRITEBYTECODE": "1", "PATH": "/usr/bin:/bin"}

# reviewer 原反例的注入转换意图(自洽重封装的新计划唯一增量)
INJECTED_TRANSITION = [{
    "after_hypothesis_key": "B",
    "transition": {"source_ref": "injected:changed-plan",
                   "new_phase_id": "phase-injected",
                   "new_scenario_ref": "scenario-injected"}}]


def spec(key: str, product: str, tref: str, **overrides) -> dict:
    d = {
        "key": key, "product_smiles": product, "coefficient": 1,
        "transformation_ref": tref, "origin_group_key": f"donor-{key}",
        "edits": [{"op": "change_bond_order", "atom1": "S_C_2",
                   "atom2": "S_O_1", "from_order": "single",
                   "to_order": "double"}],
        "donor": {"center_atom_ids": ["S_C_2", "S_O_1"]},
        "alignment": {"status": "resolved",
                      "donor_to_current": {"S_C_2": "S_C_2",
                                           "S_O_1": "S_O_1"},
                      "ref": "align-A"},
        "expectation": {"target_smiles": product},
    }
    d.update(overrides)
    return d


def base_plan() -> dict:
    """与 tests/s3b_worker.py 的默认 plan() 同形(同字节语义)。"""
    return {"pools": {"CCO": [spec("B", "CC=O", "donor-B")]}}


def injected_plan() -> dict:
    """原计划 + 注入转换意图(重封装 artifact 的新计划)。"""
    plan = base_plan()
    plan["scenario_transitions"] = [
        dict(t) for t in INJECTED_TRANSITION]
    return plan


def run_worker(*args, timeout: int = 120) -> subprocess.CompletedProcess:
    return subprocess.run(
        [PY, "-B", WORKER, *args], capture_output=True, text=True,
        timeout=timeout, env=ENV)


def start_crash(runs_root: Path, run_id: str, *,
                crash_after: str) -> subprocess.CompletedProcess:
    return run_worker("start-crash", "--runs-root", str(runs_root),
                      "--run-id", run_id, "--crash-after", crash_after)


def plan_file(runs_root: Path, run_id: str) -> Path:
    return runs_root / run_id / "results" / "run-plan" / "frozen_plan.json"


def replace_frozen_plan_self_consistent(runs_root: Path, run_id: str,
                                        new_plan: dict) -> dict:
    """只改 plan artifact:重算该文件 plan_digest 与信封 payload_hash
    (reviewer 原反例的完整突变;不改身份/数据库/其他文件)。"""
    target = plan_file(runs_root, run_id)
    data = json.loads(target.read_text(encoding="utf-8"))
    data["payload"]["plan"] = new_plan
    data["payload"]["plan_digest"] = content_hash(new_plan)
    data["payload_hash"] = content_hash(data["payload"])
    target.write_text(json.dumps(data, ensure_ascii=False),
                      encoding="utf-8")
    return data


def db(runs_root: Path, run_id: str) -> sqlite3.Connection:
    conn = sqlite3.connect(str(runs_root / run_id / "pollutant.sqlite"))
    conn.row_factory = sqlite3.Row
    return conn


def root_retrieve_row(runs_root: Path, run_id: str) -> sqlite3.Row:
    conn = db(runs_root, run_id)
    row = conn.execute(
        "SELECT * FROM search_actions WHERE run_id = ? AND"
        " action_kind = 'retrieve' AND parent_search_revision = 0",
        (run_id,)).fetchone()
    conn.close()
    assert row is not None
    return row


def snapshot_tables(runs_root: Path, run_id: str) -> dict:
    """只读全表逻辑快照(载荷 JSON 解析后比较;reviewer 同口径)。"""
    uri = f"file:{runs_root / run_id / 'pollutant.sqlite'}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    out: dict = {}
    for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
            " ORDER BY name").fetchall():
        rows = []
        for row in conn.execute(f'SELECT * FROM "{r["name"]}"'):
            v = dict(row)
            for key, value in list(v.items()):
                if isinstance(value, str) and value[:1] in "[{":
                    try:
                        v[key] = json.loads(value)
                    except ValueError:
                        pass
            rows.append(v)
        out[str(r["name"])] = rows
    conn.close()
    return out


def public_resume(runs_root: Path, run_id: str, *, plan: dict | None):
    """公开入口 resume(workflow.runner.resume_run 的 PPV1 分流;
    plan=None 即省略 plan)。"""
    return resume_run(config=resolve_config(), runs_root=runs_root,
                      run_id=run_id, finder=object(), ppv1_plan=plan)


# ---------------------------------------------- 两原反例翻转(负控)


def test_s3b01r3_b3_self_consistent_replaced_plan_rejected(
        tmp_path) -> None:
    """B3(bundle 已写)硬杀后只改 frozen_plan artifact(加注入转换、
    重算该文件摘要/信封;旧身份/root task/数据库不变)⇒ public
    resume 省略 plan 结构化拒 frozen_plan_binding_mismatch;业务表/
    event/commit/consume 零变化;原(被改)文件保全。父基线:不拒,
    沿旧 action/attempt 恢复并消费新转换(行为红)。"""
    runs_root = tmp_path / "runs"
    proc = start_crash(runs_root, "r3b3", crash_after="after_bundle_written")
    assert json.loads(proc.stdout.strip().splitlines()[-1])["crashed"]
    root = root_retrieve_row(runs_root, "r3b3")
    root_payload = json.loads(root["payload"])
    root_digest = str(root_payload["plan_digest"])
    assert root["status"] == "done"  # root retrieve 已 done(后段锚定对象)
    replaced = replace_frozen_plan_self_consistent(
        runs_root, "r3b3", injected_plan())
    # 数据库/root task 未被突变触碰(锚摘要仍是原值)
    root2 = root_retrieve_row(runs_root, "r3b3")
    assert json.loads(root2["payload"])["plan_digest"] == root_digest
    assert root2["task_key"] == root["task_key"]
    before = snapshot_tables(runs_root, "r3b3")
    mutated_bytes = plan_file(runs_root, "r3b3").read_bytes()
    with pytest.raises(PPV1RunError) as ei:
        public_resume(runs_root, "r3b3", plan=None)
    detail = ei.value.detail
    assert detail["kind"] == "frozen_plan_binding_mismatch"
    assert detail["anchor_action_id"] == root["action_id"]
    assert detail["anchor_status"] == "done"
    assert detail["anchor_plan_digest"] == root_digest
    assert detail["frozen_plan_digest"] == replaced["payload"]["plan_digest"]
    # 零变化:业务表(含 event/commit/consume/新调度)逐表相等
    assert snapshot_tables(runs_root, "r3b3") == before
    # 原(被改)artifact 文件逐字节保全(不被恢复覆盖)
    assert plan_file(runs_root, "r3b3").read_bytes() == mutated_bytes
    # 拒绝先于 recover 的 bundle 消费:B3 时点 0 event、0 转换 action
    assert before["events"] == []
    assert not [a for a in before["search_actions"]
                if a["action_kind"] == "scenario_transition"]


def test_s3b01r3_b4_self_consistent_replaced_plan_rejected(
        tmp_path) -> None:
    """B4(事件已提交)硬杀后同样只改 artifact ⇒ 拒 + 零变化(事件已
    在,但补账/转换调度/consume 全不发生;原文件保全)。父基线:不拒,
    沿旧 action/event 恢复并新增原计划没有的转换(行为红)。"""
    runs_root = tmp_path / "runs"
    proc = start_crash(runs_root, "r3b4",
                       crash_after="after_event_submitted")
    assert json.loads(proc.stdout.strip().splitlines()[-1])["crashed"]
    root = root_retrieve_row(runs_root, "r3b4")
    root_digest = str(json.loads(root["payload"])["plan_digest"])
    assert root["status"] == "done"
    replaced = replace_frozen_plan_self_consistent(
        runs_root, "r3b4", injected_plan())
    before = snapshot_tables(runs_root, "r3b4")
    mutated_bytes = plan_file(runs_root, "r3b4").read_bytes()
    assert len(before["events"]) == 1  # B4:事件已提交
    with pytest.raises(PPV1RunError) as ei:
        public_resume(runs_root, "r3b4", plan=None)
    detail = ei.value.detail
    assert detail["kind"] == "frozen_plan_binding_mismatch"
    assert detail["anchor_plan_digest"] == root_digest
    assert detail["frozen_plan_digest"] == replaced["payload"]["plan_digest"]
    after = snapshot_tables(runs_root, "r3b4")
    assert after == before  # 补账/转换入队/consume 零新增
    assert plan_file(runs_root, "r3b4").read_bytes() == mutated_bytes


def test_s3b01r3_replaced_artifact_with_matching_new_plan_rejected(
        tmp_path) -> None:
    """自洽重封装 artifact + 显式传入**同新计划**:r2 的
    frozen_plan_mismatch 只与 artifact 比(此处相等、放行),后段锚定
    与根任务原绑定核对 ⇒ 仍拒(自洽证书+传入计划互证不是原输入)。
    父基线:接受并完成注入转换(行为红)。"""
    runs_root = tmp_path / "runs"
    proc = start_crash(runs_root, "r3np", crash_after="after_bundle_written")
    assert json.loads(proc.stdout.strip().splitlines()[-1])["crashed"]
    root = root_retrieve_row(runs_root, "r3np")
    root_digest = str(json.loads(root["payload"])["plan_digest"])
    replace_frozen_plan_self_consistent(runs_root, "r3np", injected_plan())
    before = snapshot_tables(runs_root, "r3np")
    with pytest.raises(PPV1RunError) as ei:
        public_resume(runs_root, "r3np", plan=injected_plan())
    detail = ei.value.detail
    # 传入比对侧(frozen_plan_mismatch)不触发:传入 == 被换 artifact
    assert detail["kind"] == "frozen_plan_binding_mismatch"
    assert detail["anchor_plan_digest"] == root_digest
    assert snapshot_tables(runs_root, "r3np") == before


# ---------------------------------------------- 缺锚/坏锚(负控)


def test_s3b01r3_anchor_missing_rejected(tmp_path) -> None:
    """缺锚:根 retrieve 行的 plan_digest 被移除(DB 侧权威被剥)⇒
    frozen_plan_anchor_missing 先拒(不以无锚状态继续消费冻结输入;
    零变化、原 artifact 保全)。父基线:不构成拒绝,正常恢复(行为红)。
    """
    runs_root = tmp_path / "runs"
    proc = start_crash(runs_root, "r3am", crash_after="after_bundle_written")
    assert json.loads(proc.stdout.strip().splitlines()[-1])["crashed"]
    root = root_retrieve_row(runs_root, "r3am")
    payload = json.loads(root["payload"])
    payload.pop("plan_digest")
    conn = db(runs_root, "r3am")
    conn.execute(
        "UPDATE search_actions SET payload = ? WHERE action_id = ?",
        (json.dumps(payload, ensure_ascii=False, sort_keys=True),
         root["action_id"]))
    conn.commit()
    conn.close()
    before = snapshot_tables(runs_root, "r3am")
    with pytest.raises(PPV1RunError) as ei:
        public_resume(runs_root, "r3am", plan=None)
    assert ei.value.detail["kind"] == "frozen_plan_anchor_missing"
    assert snapshot_tables(runs_root, "r3am") == before


def test_s3b01r3_anchor_corrupt_digest_edited_rejected(tmp_path) -> None:
    """坏锚:根行 payload 的 plan_digest 被改成(与被换 artifact 一致
    的)新值、行内落账 task_key 未动 ⇒ 单一来源 decision_task_key 按
    行内字段重算不同源 ⇒ frozen_plan_anchor_corrupt 先拒(零变化)。
    父基线:不构成拒绝,artifact 与 DB 载荷互证后完成注入转换
    (行为红)。"""
    runs_root = tmp_path / "runs"
    proc = start_crash(runs_root, "r3ac", crash_after="after_bundle_written")
    assert json.loads(proc.stdout.strip().splitlines()[-1])["crashed"]
    root = root_retrieve_row(runs_root, "r3ac")
    replaced = replace_frozen_plan_self_consistent(
        runs_root, "r3ac", injected_plan())
    payload = json.loads(root["payload"])
    payload["plan_digest"] = replaced["payload"]["plan_digest"]
    conn = db(runs_root, "r3ac")
    conn.execute(
        "UPDATE search_actions SET payload = ? WHERE action_id = ?",
        (json.dumps(payload, ensure_ascii=False, sort_keys=True),
         root["action_id"]))
    conn.commit()
    conn.close()
    before = snapshot_tables(runs_root, "r3ac")
    with pytest.raises(PPV1RunError) as ei:
        public_resume(runs_root, "r3ac", plan=None)
    assert ei.value.detail["kind"] == "frozen_plan_anchor_corrupt"
    assert ei.value.detail["action_id"] == root["action_id"]
    assert snapshot_tables(runs_root, "r3ac") == before


# ---------------------------------------------- 正控(父 2bedfc0 亦绿)


def test_s3b01r3_b3_omitted_plan_legal_resume_positive_control(
        tmp_path) -> None:
    """正控:B3 硬杀后省略 plan 合法恢复(事件恰一次、commit 4;
    重复 resume 无新增)。后段锚定不把恢复全面拒掉。"""
    runs_root = tmp_path / "runs"
    proc = start_crash(runs_root, "r3ok", crash_after="after_bundle_written")
    assert json.loads(proc.stdout.strip().splitlines()[-1])["crashed"]
    out = public_resume(runs_root, "r3ok", plan=None)
    assert out["counts"]["events"] == 1
    conn = db(runs_root, "r3ok")
    assert conn.execute(
        "SELECT COUNT(*) FROM search_commit_records").fetchone()[0] == 4
    # 重复完成无新增
    out2 = public_resume(runs_root, "r3ok", plan=None)
    assert out2["counts"]["events"] == 1
    conn = db(runs_root, "r3ok")
    assert conn.execute(
        "SELECT COUNT(*) FROM search_commit_records").fetchone()[0] == 4


def test_s3b01r3_same_plan_explicit_resume_positive_control(
        tmp_path) -> None:
    """正控:B3 硬杀后显式传入**同计划**恢复(合法;事件/commit 幂等)。
    传入比对侧与后段锚定同过。"""
    runs_root = tmp_path / "runs"
    proc = start_crash(runs_root, "r3sp", crash_after="after_bundle_written")
    assert json.loads(proc.stdout.strip().splitlines()[-1])["crashed"]
    out = public_resume(runs_root, "r3sp", plan=base_plan())
    assert out["counts"]["events"] == 1
    conn = db(runs_root, "r3sp")
    assert conn.execute(
        "SELECT COUNT(*) FROM search_commit_records").fetchone()[0] == 4


def test_s3b01r3_b4_legal_transition_new_context_positive_control(
        tmp_path) -> None:
    """正控:**合法原计划**转换(显式 source_ref)B4 恢复:转换 done、
    followup 用 phase-1 新上下文(旧边评估不动)。后段锚定只拒换计划,
    不禁转换。"""
    runs_root = tmp_path / "runs"
    legal_plan = base_plan()
    legal_plan["scenario_transitions"] = [{
        "after_hypothesis_key": "B",
        "transition": {"source_ref": "user:switch-anaerobic",
                       "new_phase_id": "phase-1",
                       "new_scenario_ref": "scenario-anaerobic"}}]
    proc = run_worker("start-crash", "--runs-root", str(runs_root),
                      "--run-id", "r3tr", "--crash-after",
                      "after_event_submitted", "--transitions")
    assert json.loads(proc.stdout.strip().splitlines()[-1])["crashed"]
    out = public_resume(runs_root, "r3tr", plan=None)
    assert out["counts"]["events"] == 1
    conn = db(runs_root, "r3tr")
    transitions = conn.execute(
        "SELECT * FROM search_actions WHERE action_kind ="
        " 'scenario_transition'").fetchall()
    assert len(transitions) == 1
    assert transitions[0]["status"] == "done"
    followups = [r for r in conn.execute(
        "SELECT * FROM search_actions WHERE action_kind = 'retrieve'"
        " ORDER BY created_at, action_id").fetchall()
        if json.loads(r["payload"]).get("source_event_id")]
    assert followups
    contexts = [json.loads(p.read_text(encoding="utf-8"))["payload"]
                for p in sorted(
                    (runs_root / "r3tr" / "results").rglob(
                        "path_context.json"))]
    new_ctx = [c for c in contexts if c["phase_id"] == "phase-1"]
    assert new_ctx
    assert {r["context_ref"] for r in followups} == \
        {new_ctx[0]["context_id"]}
