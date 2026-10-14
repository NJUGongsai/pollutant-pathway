"""S4b 正式导出/v3 有损投影回归(公共 start/resume → endpoint 分账 →
原生正式导出 → 首消费/过期/完整性 → v3 有损投影 → 再次读取/replay;
G02 七测矩阵;legacy/export_v3 冻结零触碰)。

覆盖(任务书 §7 S4b + §8 验收矩阵 S4b 行 + §4.4 G02):

- 正式文件导出:payload(全量事实:共同产物/备选/不同来路/条件/
  依赖/audit/未展开集合/预算/停止/endpoint)+ manifest(graph facts
  digest 新鲜度锚 + 权威引用 + 策略 hash);
- G02 七测:①同 run 同 revision 重复导出(含独立子进程)字节一致;
  ②恢复后重复导出字节一致;③导出再读取;④源图变化 ⇒ 过期拒;
  ⑤导出策略变化 ⇒ 过期拒;⑥内容 hash/引用不一致 ⇒ 结构化失败;
  ⑦自洽重写(重算内部 hash)不能洗成当前结果;
- v3 有损投影:lossy_projection 标记/原生引用/适配版本/信息损失
  清单/不可投影摘要;不合并同父备选;不编造终点/矿化;CO₂ 不相加;
- 反向污染负控:投影载荷不能进原生消费入口;消费投影零 DB 写入;
- 完整公共链:crash → resume → endpoint → 导出 → 投影 → 读取 →
  再 resume(replay)不重复写 event/attempt/request/budget,导出
  字节不变;scripted 网络请求 0;
- endpoint 与搜索状态不一致(stop 行删除)⇒ 引用断裂拒。

基线 fc40605 上本文件为 collection 红(pollutant.native_export /
v3_projection 缺失)。
"""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pathway_v43.config import resolve_config  # noqa: E402
from pathway_v43.domain.models import canonical_json, content_hash  # noqa: E402
from pathway_v43.pollutant.endpoint import (  # noqa: E402
    EndpointContractError,
    read_run_endpoint,
)
from pathway_v43.pollutant.native_export import (  # noqa: E402
    NativeExportConflict,
    NativeExportContractError,
    export_native_result,
    list_native_exports,
    native_export_policy,
    read_native_export,
)
from pathway_v43.pollutant.native_result import (  # noqa: E402
    build_native_result,
    read_native_result,
)
from pathway_v43.pollutant.runflow import start_ppv1_run  # noqa: E402
from pathway_v43.pollutant.search import (  # noqa: E402
    SearchCrashInjection,
    SearchLedger,
)
from pathway_v43.pollutant.store import PollutantPathwayStore  # noqa: E402
from pathway_v43.pollutant.v3_projection import (  # noqa: E402
    V3ProjectionContractError,
    build_v3_projection,
    list_v3_projections_for_native,
    persist_v3_projection,
    read_v3_projection,
)
from pathway_v43.storage.artifact_store import ArtifactStore  # noqa: E402
from pathway_v43.storage.run_identity import (  # noqa: E402
    PROFILE_POLLUTANT_PATHWAY_V1,
)
from pathway_v43.workflow.runner import resume_run, start_run  # noqa: E402

from test_ppv1_s4a_endpoint import (  # noqa: E402
    mineralization_evidence,
    spec,
)

REPO = Path(__file__).resolve().parents[1]
PY = sys.executable
ENV = {"PYTHONDONTWRITEBYTECODE": "1", "PATH": "/usr/bin:/bin"}

GRAPH_FACT_TABLES = (
    "states", "state_appearances", "hypotheses", "events",
    "report_projections", "expansion_plans", "event_appearance_links",
    "provenance_records", "search_actions", "search_attempts",
    "budget_reservations", "model_requests", "search_commit_records",
    "stop_reason_records", "endpoint_records")

REQUIRED_LOSS_AXES = (
    "route_origins", "coproducts", "alternative_reactions",
    "conditions_dependencies", "audit_proof_scope", "deferred_unexpanded",
    "endpoint_evidence_level", "budget_stop_reason", "unknown_partial_axes")


def start(tmp_path: Path, run_id: str, plan: dict, *,
          profile_policy: dict | None = None) -> dict:
    return start_run(
        config=resolve_config(), runs_root=tmp_path / "runs",
        run_id=run_id, smiles="CCO", max_depth=3, max_expansions=10,
        max_frontier_width=2, finder=object(), scripted=True,
        profile=PROFILE_POLLUTANT_PATHWAY_V1, ppv1_plan=plan,
        profile_policy=profile_policy)


def ledger_for(runs_root: Path, run_id: str) -> SearchLedger:
    store = PollutantPathwayStore(runs_root / run_id / "pollutant.sqlite")
    artifacts = ArtifactStore(runs_root, run_id)
    return SearchLedger(store, artifacts, run_id)


def counts_of(runs_root: Path, run_id: str) -> dict:
    conn = sqlite3.connect(str(runs_root / run_id / "pollutant.sqlite"))
    one = lambda sql: conn.execute(sql).fetchone()[0]  # noqa: E731
    out = {
        "events": one("SELECT COUNT(*) FROM events"),
        "search_attempts": one("SELECT COUNT(*) FROM search_attempts"),
        "model_requests": one("SELECT COUNT(*) FROM model_requests"),
        "search_actions": one("SELECT COUNT(*) FROM search_actions"),
        "budget_reservations": one(
            "SELECT COUNT(*) FROM budget_reservations"),
        "network_requests": one(
            "SELECT COALESCE(SUM(network_request_count), 0) FROM"
            " model_requests"),
    }
    conn.close()
    return out


def export_dir_of(runs_root: Path, run_id: str, export_digest: str) -> Path:
    return runs_root / run_id / "native_export" / export_digest[:24]


def projection_path_of(runs_root: Path, run_id: str,
                       projection_digest: str) -> Path:
    return (runs_root / run_id / "v3_projection"
            / projection_digest[:24] / "projection.json")


def _full_fixture(tmp_path: Path, run_id: str = "s4b"):
    """完整事实夹具:双备选 + 共同产物 + 终点证据(全字段)。"""
    plan = {"pools": {"CCO": [
        spec("B", "CC=O", "donor-B", coproducts=["[H][H]"]),
        spec("C", "CC=O", "donor-C")]},
        "schedule_budget": {"max_select": 1},
        "endpoint_evidence": [mineralization_evidence()]}
    runs_root = tmp_path / "runs"
    out = start(tmp_path, run_id, plan)
    return runs_root, out


# ------------------------------------------------ 正式导出公共链 + 全量

def test_native_export_public_chain_files_and_manifest(
        tmp_path: Path) -> None:
    """公共 start → endpoint → 正式导出:summary 字段、payload/manifest
    文件落位、manifest 结构(版本/策略/事实 digest/引用);导出后立即
    首消费读回(链内自校验)。"""
    runs_root, out = _full_fixture(tmp_path)
    digest = out["native_export"]["export_digest"]
    out_dir = export_dir_of(runs_root, "s4b", digest)
    assert (out_dir / "payload.json").is_file()
    assert (out_dir / "manifest.json").is_file()
    manifest = json.loads(
        (out_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["schema_version"] == "ppv1-native-export-3"
    assert manifest["run_id"] == "s4b"
    assert manifest["content_digest"] == out["native_result"][
        "content_digest"]
    assert manifest["export_policy"]["version"] == \
        "ppv1-native-export-policy-3"
    assert manifest["contract_versions"]["runflow"] == "ppv1-runflow-5"
    # S5a 回修 r1:profile-20 → -21(evaluation-2 注册进身份块);
    # S5a 回修 r2:profile-21 → -22(evaluation-3 单位收口);
    # S5a 回修 r3:profile-22 → -23(S5A-05 消费侧引用绑定 + 五处
    # P2 文案;evaluation-3/template-3 版本号不变);
    # S5b 启动批:profile-23 → -24(evaluation-4 qid 感知配对);
    # S5b 启动批回修:profile-24 → -25(evaluation-5 real 档配对禁
    # root_identity_fallback,S5B-L01)
    assert manifest["contract_versions"]["profile"] == "ppv1-profile-25"
    assert manifest["payload_sha256"] == \
        out["native_export"]["payload_sha256"]
    # 无时间戳(G02 确定性面)
    assert "created_at" not in manifest and "generated_at" not in manifest
    payload = json.loads(
        (out_dir / "payload.json").read_text(encoding="utf-8"))
    assert "created_at" not in payload
    # 首消费读回(链内已执行;此处独立复证)
    ledger = ledger_for(runs_root, "s4b")
    verified = read_native_export(ledger, runs_root / "s4b", digest)
    assert verified["payload"]["content_digest"] == \
        manifest["content_digest"]


def test_native_export_full_fact_coverage(tmp_path: Path) -> None:
    """全量导出:共同产物/备选/不同来路/条件/依赖/audit/未展开集合/
    预算/停止原因/endpoint 分账全部进 payload;manifest graph facts
    覆盖 15 张事实表;artifact 引用含 contexts/reports/outcomes/
    冻结计划。"""
    runs_root, out = _full_fixture(tmp_path)
    digest = out["native_export"]["export_digest"]
    payload = json.loads(
        (export_dir_of(runs_root, "s4b", digest) / "payload.json")
        .read_text(encoding="utf-8"))
    # 共同产物(不被报告宽度截断)
    assert payload["coproducts"] and \
        len(payload["coproducts"][0]["coproduct_state_refs"]) == 1
    # 备选反应 + 不同来路
    assert payload["alternatives"] and \
        len(payload["alternatives"][0]["alternative_hypotheses"]) == 2
    # 条件/依赖(上下文)与 audit/proof scope
    assert payload["contexts"]
    assert payload["audit_production_reports"] and \
        payload["audit_production_reports"][0]["production_payload"][
            "audit"]
    # 未展开集合(deferred 两类字段完整)
    assert payload["deferred_entries"]
    assert payload["deferred_entries"][0]["deferred_type"] == \
        "alternative_reaction_deferred"
    # 预算预约/实际消耗 + 停止原因 + endpoint 分账
    assert payload["budget"]["budget_snapshot"]["run_level"]
    assert payload["endpoint_record"]["search_stop_reason"]["primary"]
    assert payload["endpoint_record"]["execution_status"] == "completed"
    manifest = json.loads(
        (export_dir_of(runs_root, "s4b", digest) / "manifest.json")
        .read_text(encoding="utf-8"))
    for table in GRAPH_FACT_TABLES:
        assert table in manifest["graph_facts"], table
    refs = manifest["artifact_references"]
    assert any("/path_context" in k for k in refs)
    assert any("/production_report" in k for k in refs)
    assert any("/expansion_outcome" in k for k in refs)
    assert any("run-plan/frozen_plan" in k for k in refs)


# ---------------------------------------------------------------- G02

def test_g02_repeat_export_same_bytes_including_subprocess(
        tmp_path: Path) -> None:
    """G02-①:同一 run、同一事实 revision,重复导出(同进程重建导出 +
    独立子进程重新构建导出)⇒ 相同 digest、逐字节相同、单目录幂等。"""
    runs_root, out = _full_fixture(tmp_path)
    digest = out["native_export"]["export_digest"]
    before = (export_dir_of(runs_root, "s4b", digest) /
              "payload.json").read_bytes()
    manifest_before = (export_dir_of(runs_root, "s4b", digest) /
                       "manifest.json").read_bytes()
    # 同进程重建(新 ledger/新连接;事实未动)
    ledger = ledger_for(runs_root, "s4b")
    native = build_native_result(
        ledger, endpoint_record=read_run_endpoint(ledger, "s4b"))
    repeat = export_native_result(ledger, native, runs_root / "s4b")
    assert repeat["export_digest"] == digest
    assert repeat["created"] == {"payload": False, "manifest": False}
    assert (export_dir_of(runs_root, "s4b", digest) /
            "payload.json").read_bytes() == before
    assert (export_dir_of(runs_root, "s4b", digest) /
            "manifest.json").read_bytes() == manifest_before
    assert len(list_native_exports(runs_root / "s4b")) == 1
    # 独立子进程:全新解释器、重新构建原生结果并导出
    code = (
        "import json, sys\n"
        "from pathway_v43.pollutant.store import PollutantPathwayStore\n"
        "from pathway_v43.storage.artifact_store import ArtifactStore\n"
        "from pathway_v43.pollutant.search import SearchLedger\n"
        "from pathway_v43.pollutant.endpoint import read_run_endpoint\n"
        "from pathway_v43.pollutant.native_result import"
        " build_native_result\n"
        "from pathway_v43.pollutant.native_export import"
        " export_native_result\n"
        f"store = PollutantPathwayStore({str(runs_root / 's4b' / 'pollutant.sqlite')!r})\n"
        f"ledger = SearchLedger(store, ArtifactStore({str(runs_root)!r}, 's4b'), 's4b')\n"
        "native = build_native_result(ledger, endpoint_record="
        " read_run_endpoint(ledger, 's4b'))\n"
        f"out = export_native_result(ledger, native, {str(runs_root / 's4b')!r})\n"
        "print(json.dumps({'export_digest': out['export_digest'],"
        " 'payload_sha256': out['payload_sha256']}))\n")
    env = dict(ENV)
    env["PYTHONPATH"] = str(REPO / "src")
    proc = subprocess.run([PY, "-B", "-c", code], env=env,
                          cwd=str(tmp_path),
                          capture_output=True, text=True, timeout=120)
    assert proc.returncode == 0, proc.stderr
    result = json.loads(proc.stdout.strip().splitlines()[-1])
    assert result["export_digest"] == digest
    assert result["payload_sha256"] == \
        out["native_export"]["payload_sha256"]
    assert (export_dir_of(runs_root, "s4b", digest) /
            "payload.json").read_bytes() == before
    assert len(list_native_exports(runs_root / "s4b")) == 1


def test_g02_export_after_crash_resume_repeat_identical(
        tmp_path: Path) -> None:
    """G02-②:恢复后重复导出字节一致。崩溃(B4)→ resume#1(恢复 +
    驱动至结算)→ resume#2 派生导出 → resume#3(replay)⇒ 同 digest、
    字节不变、单目录。
    (resume#1→#2 的停止视图含**会话成分**(session refusals 进
    budget_exhausted_keys、events_submitted_session),驱动未结算的
    相邻会话允许 stop/endpoint 权威行合法更新 ⇒ 新 digest —— S4a
    既有披露;事件/预算零新增是硬边界,由 E2E 测试断言。)
    """
    plan = {"pools": {"CCO": [spec("B", "CC=O", "donor-B")]}}
    runs_root = tmp_path / "runs"
    with pytest.raises(SearchCrashInjection):
        start_ppv1_run(
            config=resolve_config(), runs_root=runs_root, run_id="g02b",
            smiles="CCO", plan=plan, scripted=True,
            crash_after="after_event_submitted")
    resume_run(config=resolve_config(), runs_root=runs_root, run_id="g02b")
    second = resume_run(config=resolve_config(), runs_root=runs_root,
                        run_id="g02b")
    digest = second["native_export"]["export_digest"]
    payload_bytes = (export_dir_of(runs_root, "g02b", digest) /
                     "payload.json").read_bytes()
    manifest_bytes = (export_dir_of(runs_root, "g02b", digest) /
                      "manifest.json").read_bytes()
    third = resume_run(config=resolve_config(), runs_root=runs_root,
                       run_id="g02b")
    assert third["native_export"]["export_digest"] == digest
    assert (export_dir_of(runs_root, "g02b", digest) /
            "payload.json").read_bytes() == payload_bytes
    assert (export_dir_of(runs_root, "g02b", digest) /
            "manifest.json").read_bytes() == manifest_bytes
    assert len(list_native_exports(runs_root / "g02b")) == 2


def test_g02_export_read_back_matches_native_authority(
        tmp_path: Path) -> None:
    """G02-③:导出再读取 = 原生权威(payload == S4a 原生结果 artifact
    载荷;endpoint 行 hash 与公共 summary 一致)。"""
    runs_root, out = _full_fixture(tmp_path)
    digest = out["native_export"]["export_digest"]
    ledger = ledger_for(runs_root, "s4b")
    verified = read_native_export(ledger, runs_root / "s4b", digest)
    native = read_native_result(
        ledger.artifact_store, out["native_result"]["task_key"])
    assert verified["payload"] == native
    assert verified["manifest"]["authority_references"][
        "endpoint_record_payload_hash"] == \
        out["endpoint_record_payload_hash"]


def test_g02_stale_after_graph_change(tmp_path: Path) -> None:
    """G02-④:源图 revision 变化 ⇒ 旧导出拒。两条负控(各自独立夹具):
    (a) 改动作行状态 ⇒ endpoint 首消费先拒(endpoint_record_stale,
    优先级如实披露 —— 四分账权威先行);
    (b) 新增事实行(provenance)⇒ export_stale(graph facts digest
    重算不符);重导出 ⇒ 新 digest 新目录,旧导出文件保全字节不变。"""
    # (a) 动作行状态漂移 ⇒ endpoint 权威先拒
    runs_root, out = _full_fixture(tmp_path)
    digest = out["native_export"]["export_digest"]
    conn = sqlite3.connect(str(runs_root / "s4b" / "pollutant.sqlite"))
    conn.execute(
        "UPDATE search_actions SET status = 'done' WHERE run_id = 's4b'"
        " AND status = 'deferred'")
    conn.commit()
    conn.close()
    ledger = ledger_for(runs_root, "s4b")
    with pytest.raises(EndpointContractError) as excinfo:
        read_native_export(ledger, runs_root / "s4b", digest)
    assert excinfo.value.detail["kind"] == "endpoint_record_stale"
    # (b) 独立夹具:新增事实行(endpoint 摘要不覆盖 provenance ⇒
    # 导出面浮出)
    runs_root2, out2 = _full_fixture(tmp_path, "s4bb")
    digest2 = out2["native_export"]["export_digest"]
    conn = sqlite3.connect(str(runs_root2 / "s4bb" / "pollutant.sqlite"))
    conn.execute(
        "INSERT INTO provenance_records (record_id, run_id, payload,"
        " created_at) VALUES ('probe-x', 's4bb', '{}',"
        " '2026-10-08T00:00:00')")
    conn.commit()
    conn.close()
    ledger2 = ledger_for(runs_root2, "s4bb")
    with pytest.raises(NativeExportContractError) as excinfo:
        read_native_export(ledger2, runs_root2 / "s4bb", digest2)
    assert excinfo.value.detail["kind"] == "export_stale"
    assert "provenance_records" in excinfo.value.detail["changed_facts"]
    # 旧文件保全 + 重导出新 digest 新目录(不覆盖)
    old_bytes = (export_dir_of(runs_root2, "s4bb", digest2) /
                 "payload.json").read_bytes()
    native = build_native_result(
        ledger2, endpoint_record=read_run_endpoint(ledger2, "s4bb"))
    from pathway_v43.pollutant.native_result import persist_native_result
    persist_native_result(ledger2, native)
    new_out = export_native_result(ledger2, native, runs_root2 / "s4bb")
    assert new_out["export_digest"] != digest2
    assert len(list_native_exports(runs_root2 / "s4bb")) == 2
    assert (export_dir_of(runs_root2, "s4bb", digest2) /
            "payload.json").read_bytes() == old_bytes
    # 新导出可读且不再 stale
    read_native_export(
        ledger2, runs_root2 / "s4bb", new_out["export_digest"])


def test_g02_stale_after_policy_change(tmp_path: Path) -> None:
    """G02-⑤:导出策略/版本变化 ⇒ 旧导出按策略过期拒(不静默消费)。"""
    runs_root, out = _full_fixture(tmp_path)
    digest = out["native_export"]["export_digest"]
    ledger = ledger_for(runs_root, "s4b")
    # 未来策略(回修 r2 后当前策略版本为 -3,未来版本取 -4)
    future_policy = dict(native_export_policy())
    future_policy["version"] = "ppv1-native-export-policy-4"
    with pytest.raises(NativeExportContractError) as excinfo:
        read_native_export(ledger, runs_root / "s4b", digest,
                           policy=future_policy)
    assert excinfo.value.detail["kind"] == "export_policy_stale"
    # 当前策略读取不受影响(正控)
    read_native_export(ledger, runs_root / "s4b", digest)


def test_g02_integrity_structured_failures(tmp_path: Path) -> None:
    """G02-⑥:内容 hash/引用不一致 ⇒ 结构化失败(保全原文件):
    payload 字节篡改 / manifest 损坏 / 原生结果 artifact 缺失 /
    导出文件缺失。"""
    runs_root, out = _full_fixture(tmp_path)
    digest = out["native_export"]["export_digest"]
    out_dir = export_dir_of(runs_root, "s4b", digest)
    ledger = ledger_for(runs_root, "s4b")
    # payload 字节篡改(manifest sha 不符)
    payload_path = out_dir / "payload.json"
    original = payload_path.read_bytes()
    payload_path.write_bytes(original[:-2] + b"\n")
    with pytest.raises(NativeExportContractError) as excinfo:
        read_native_export(ledger, runs_root / "s4b", digest)
    assert excinfo.value.detail["kind"] == "export_payload_corrupt"
    payload_path.write_bytes(original)  # 还原
    # manifest 损坏(不可解析)
    manifest_path = out_dir / "manifest.json"
    manifest_original = manifest_path.read_bytes()
    manifest_path.write_bytes(b"{not json")
    with pytest.raises(NativeExportContractError) as excinfo:
        read_native_export(ledger, runs_root / "s4b", digest)
    assert excinfo.value.detail["kind"] == "export_manifest_corrupt"
    manifest_path.write_bytes(manifest_original)
    # 原生结果 artifact 缺失(引用断裂)
    task_key = out["native_result"]["task_key"]
    artifact_path = (runs_root / "s4b" / "results" / task_key /
                     "native_result.json")
    backup = tmp_path / "artifact_backup.json"
    shutil.move(str(artifact_path), backup)
    with pytest.raises(NativeExportContractError) as excinfo:
        read_native_export(ledger, runs_root / "s4b", digest)
    assert excinfo.value.detail["kind"] == "export_reference_mismatch"
    shutil.move(str(backup), artifact_path)
    # 正控:还原后读取恢复
    read_native_export(ledger, runs_root / "s4b", digest)
    # 文件缺失
    with pytest.raises(NativeExportContractError) as excinfo:
        read_native_export(ledger, runs_root / "s4b", "0" * 64)
    assert excinfo.value.detail["kind"] == "export_missing"


def test_g02_self_consistent_rewrite_not_laundered(tmp_path: Path) -> None:
    """G02-⑦:自洽重写(重算 payload sha/内容 digest/export digest 全
    部内部 hash 的"新 ID"导出)不能洗成当前结果 —— 权威引用(原生
    结果 artifact/DB 行)与 graph facts 从独立权威重算,不信 manifest
    自声明。"""
    runs_root, out = _full_fixture(tmp_path)
    digest = out["native_export"]["export_digest"]
    out_dir = export_dir_of(runs_root, "s4b", digest)
    ledger = ledger_for(runs_root, "s4b")
    # 构造自洽重写:拷贝旧导出,篡改 payload(删一条 deferred 披露),
    # 重算内容 digest/payload sha/manifest/export digest —— 洗成"新结果"
    payload = json.loads(
        (out_dir / "payload.json").read_text(encoding="utf-8"))
    payload["deferred_entries"] = []
    payload.pop("content_digest", None)
    payload["content_digest"] = content_hash(payload)
    payload_text = canonical_json(payload) + "\n"
    manifest = json.loads(
        (out_dir / "manifest.json").read_text(encoding="utf-8"))
    import hashlib
    manifest["content_digest"] = payload["content_digest"]
    manifest["payload_sha256"] = hashlib.sha256(
        payload_text.encode("utf-8")).hexdigest()
    manifest.pop("export_digest", None)
    fake_digest = content_hash(manifest)
    manifest["export_digest"] = fake_digest
    fake_dir = runs_root / "s4b" / "native_export" / fake_digest[:24]
    fake_dir.mkdir(parents=True)
    (fake_dir / "payload.json").write_text(payload_text, encoding="utf-8")
    (fake_dir / "manifest.json").write_text(
        canonical_json(manifest) + "\n", encoding="utf-8")
    # 自洽(内部 hash 全对)但权威引用/事实 digest 不符 ⇒ 拒
    with pytest.raises(NativeExportContractError) as excinfo:
        read_native_export(ledger, runs_root / "s4b", fake_digest)
    assert excinfo.value.detail["kind"] in (
        "export_reference_mismatch", "export_stale")
    # 原导出不受影响(保全)
    read_native_export(ledger, runs_root / "s4b", digest)


def test_tampered_export_refuses_overwrite(tmp_path: Path) -> None:
    """不可变导出:同 digest 路径已有不同字节 ⇒ 重导出拒(保全原文件,
    不覆盖;篡改文件须显式清除,不能靠重导出静默洗掉)。"""
    runs_root, out = _full_fixture(tmp_path)
    digest = out["native_export"]["export_digest"]
    out_dir = export_dir_of(runs_root, "s4b", digest)
    payload_path = out_dir / "payload.json"
    original = payload_path.read_bytes()
    payload_path.write_bytes(b"{}\n")
    ledger = ledger_for(runs_root, "s4b")
    native = build_native_result(
        ledger, endpoint_record=read_run_endpoint(ledger, "s4b"))
    with pytest.raises(NativeExportConflict):
        export_native_result(ledger, native, runs_root / "s4b")
    assert payload_path.read_bytes() == b"{}\n"  # 保全(不覆盖)
    payload_path.write_bytes(original)


# ---------------------------------------------------------------- v3 投影

def test_v3_projection_lossy_marker_reference_and_losses(
        tmp_path: Path) -> None:
    """v3 有损投影:lossy_projection 标记、适配版本、原生引用(可解析
    回原生导出)、信息损失清单覆盖任务书要求的损失轴、不可投影摘要
    (引用/计数,不展开全文)。"""
    runs_root, out = _full_fixture(tmp_path)
    digest = out["v3_projection"]["projection_digest"]
    payload = read_v3_projection(runs_root / "s4b", digest)
    assert payload["lossy_projection"] is True
    assert payload["schema_version"] == "ppv1-v3-projection-3"
    assert payload["adapter_version"] == "ppv1-v3-projection-3"
    ref = payload["native_reference"]
    assert ref["native_export_digest"] == \
        out["native_export"]["export_digest"]
    assert ref["native_result_content_digest"] == \
        out["native_result"]["content_digest"]
    assert ref["native_result_task_key"] == \
        out["native_result"]["task_key"]
    axes = {loss["axis"] for loss in payload["information_losses"]}
    for axis in REQUIRED_LOSS_AXES:
        assert axis in axes, axis
    summaries = payload["unprojectable_summaries"]
    assert summaries["endpoint_assessment"] == "supported_mineralization"
    assert summaries["independent_source_support_count"] == 1
    assert summaries["deferred_entry_count"] >= 1
    assert summaries["condition_keys_known"] == []  # 夹具无条件事实(确定)
    assert summaries["note"].startswith("全部值为摘要")
    # 原生图修订与来源 identity
    assert payload["native_graph_revision"]["aggregate_digest"]
    assert payload["native_graph_revision"]["contract_versions"][
        "runflow"] == "ppv1-runflow-5"
    # 边界声明
    assert payload["boundary"]["reverse_consumption"] == "forbidden"
    assert payload["boundary"]["not_counted_as_extra_path"] is True


def test_v3_projection_steps_per_event_no_cn_merge_no_fabrication(
        tmp_path: Path) -> None:
    """投影步骤 = 逐事件(同父双备选不合并为单反应;共同产物入产物
    列表但角色列为损失);root_smiles 为真实输入;endpoint unknown 时
    投影不得编造终点;CO₂ 备选不相加(逐事件步骤保留)。"""
    # 双备选各生成 CO₂(不同 hypothesis;W3 去重契约下须不同净反应
    # —— C 带不同共同产物集合)⇒ 无证据 ⇒ unknown
    plan = {"pools": {"CCO": [spec("B", "O=C=O", "donor-B"),
                              spec("C", "O=C=O", "donor-C",
                                   coproducts=["[H][H]"])]}}
    runs_root = tmp_path / "runs"
    out = start(tmp_path, "v3co2", plan)
    digest = out["v3_projection"]["projection_digest"]
    payload = read_v3_projection(runs_root / "v3co2", digest)
    steps = payload["route"]["steps"]
    assert len(steps) == 2  # 两个备选事件各自一步(不按 CN/父合并)
    assert all(s["parent_smiles"] == "CCO" for s in steps)
    assert payload["route"]["root_smiles"] == "CCO"
    # 不编造终点:无证据 ⇒ endpoint unknown 披露在不可投影摘要
    assert payload["unprojectable_summaries"][
        "endpoint_assessment"] == "unknown"
    # CO₂ 备选不相加:逐事件列示、无聚合
    assert payload["unprojectable_summaries"][
        "co2_product_occurrences"] == 2
    assert payload["unprojectable_summaries"]["co2_aggregated"] is False
    # v3 字段形状冻结:步骤只含 parent_smiles/predicted_products
    assert set(steps[0]) == {"parent_smiles", "predicted_products"}


def test_v3_projection_deterministic_and_reverse_lookup(
        tmp_path: Path) -> None:
    """投影确定性(两次独立构建同 digest;子进程导出确定性见 G02-①);
    反查(native → 投影)按原生引用只读匹配;原生 manifest 缺失 ⇒
    投影读取拒(正向引用核对)。"""
    runs_root, out = _full_fixture(tmp_path)
    digest = out["v3_projection"]["projection_digest"]
    ledger = ledger_for(runs_root, "s4b")
    native = build_native_result(
        ledger, endpoint_record=read_run_endpoint(ledger, "s4b"))
    again = build_v3_projection(
        ledger, native, native_export=out["native_export"],
        run_dir=runs_root / "s4b")
    assert again["projection_digest"] == digest
    found = list_v3_projections_for_native(
        runs_root / "s4b",
        native_export_digest=out["native_export"]["export_digest"])
    assert len(found) == 1 and found[0]["lossy_projection"] is True
    # 正向引用核对:删原生 manifest ⇒ 投影读取拒
    manifest_path = (export_dir_of(
        runs_root, "s4b", out["native_export"]["export_digest"]) /
        "manifest.json")
    backup = tmp_path / "manifest_backup.json"
    shutil.move(str(manifest_path), backup)
    with pytest.raises(V3ProjectionContractError) as excinfo:
        read_v3_projection(runs_root / "s4b", digest)
    assert excinfo.value.detail["kind"] == "v3_native_reference_missing"
    shutil.move(str(backup), manifest_path)
    read_v3_projection(runs_root / "s4b", digest)  # 还原后恢复


def test_v3_projection_reverse_consumption_refused_zero_writes(
        tmp_path: Path) -> None:
    """反向污染负控:v3 投影载荷不能进原生消费入口(原生导出读取拒/
    原生结果 artifact 读取拒);消费投影零 DB 写入(事件/状态/动作/
    预算不变);模块不暴露任何投影 → 原生事实写入入口(结构性边界)。"""
    runs_root, out = _full_fixture(tmp_path)
    digest = out["v3_projection"]["projection_digest"]
    ledger = ledger_for(runs_root, "s4b")
    before = counts_of(runs_root, "s4b")
    payload = read_v3_projection(runs_root / "s4b", digest)
    assert read_v3_projection(runs_root / "s4b", digest) == payload
    assert counts_of(runs_root, "s4b") == before  # 零写入
    # 投影 digest 不是导出 digest:原生导出入口拒(不是原生结果)
    with pytest.raises(NativeExportContractError) as excinfo:
        read_native_export(ledger, runs_root / "s4b", digest)
    assert excinfo.value.detail["kind"] == "export_missing"
    # 投影载荷不含原生结果身份:喂给原生结果读取 ⇒ 拒(缺 artifact,
    # 不猜默认)
    from pathway_v43.pollutant.native_result import \
        NativeResultContractError
    with pytest.raises(NativeResultContractError):
        read_native_result(
            ledger.artifact_store,
            payload["native_reference"]["native_result_task_key"] + "x")
    # 结构性边界:v3_projection 模块不暴露任何 ledger/store 写入口
    # (投影 → 原生事实/事件/状态的转换函数不存在;反向消费在契约上
    # 禁止)
    import pathway_v43.pollutant.v3_projection as vp_module
    write_like = [
        name for name in dir(vp_module)
        if name.startswith(("put_", "submit_", "write_"))
        or "insert" in name or "update" in name]
    assert write_like == []
    assert vp_module.V3_REVERSE_CONSUMPTION == "forbidden"
    assert counts_of(runs_root, "s4b") == before


# ---------------------------------------------------- 完整公共链(E2E)

def test_full_public_chain_crash_resume_export_replay(tmp_path: Path) -> None:
    """完整公共链:scripted start(崩溃注入)→ resume(驱动 → 停止 →
    endpoint 分账 → 原生导出 → v3 投影,全链首消费)→ 读取两产物 →
    再 resume(replay)零新写(event/attempt/request/budget/network)。
    本夹具停止视图含会话成分(events_submitted_session):replay 后
    stop/endpoint 权威行合法更新 ⇒ 当前导出换新 digest(旧导出文件
    保全字节不变;字节级跨 resume 稳定性由 G02-②会话无关夹具证明,
    沿 S4a 既有披露)。网络请求 0;scripted provider。"""
    plan = {"pools": {"CCO": [
        spec("B", "CC=O", "donor-B", coproducts=["[H][H]"])]},
        "endpoint_evidence": [mineralization_evidence()]}
    runs_root = tmp_path / "runs"
    with pytest.raises(SearchCrashInjection):
        start_ppv1_run(
            config=resolve_config(), runs_root=runs_root, run_id="e2e",
            smiles="CCO", plan=plan, scripted=True,
            crash_after="after_event_submitted")
    out = resume_run(config=resolve_config(), runs_root=runs_root,
                     run_id="e2e")
    # 驱动 → 停止 → endpoint 四分账 → 原生导出 → v3 投影
    assert out["counts"]["events"] == 1
    assert out["endpoint"]["chemical_endpoint_assessment"] == \
        "supported_mineralization"
    export_digest = out["native_export"]["export_digest"]
    projection_digest = out["v3_projection"]["projection_digest"]
    first_payload_bytes = (export_dir_of(runs_root, "e2e", export_digest) /
                           "payload.json").read_bytes()
    # 读取两产物(再次读取/消费)
    ledger = ledger_for(runs_root, "e2e")
    verified = read_native_export(ledger, runs_root / "e2e", export_digest)
    assert verified["payload"]["endpoint_record"]["execution_status"] == \
        "completed"
    projection = read_v3_projection(runs_root / "e2e", projection_digest)
    assert projection["route"]["steps"][0]["parent_smiles"] == "CCO"
    assert projection["route"]["steps"][0]["predicted_products"] == [
        "CC=O", "[H][H]"]
    # replay:再 resume 不重复写业务账(硬边界:事件/尝试/请求/预约)
    before = counts_of(runs_root, "e2e")
    assert before["events"] == 1 and before["network_requests"] == 0
    out2 = resume_run(config=resolve_config(), runs_root=runs_root,
                      run_id="e2e")
    assert counts_of(runs_root, "e2e") == before
    # 旧导出文件保全(字节不变);replay 后当前导出/投影可读、事实同
    assert (export_dir_of(runs_root, "e2e", export_digest) /
            "payload.json").read_bytes() == first_payload_bytes
    current_digest = out2["native_export"]["export_digest"]
    current_projection = out2["v3_projection"]["projection_digest"]
    verified2 = read_native_export(
        ledger_for(runs_root, "e2e"), runs_root / "e2e", current_digest)
    assert verified2["payload"]["endpoint_record"]["execution_status"] == \
        "completed"
    assert verified2["payload"]["events"] == verified["payload"]["events"]
    projection2 = read_v3_projection(runs_root / "e2e", current_projection)
    assert projection2["route"]["steps"] == projection["route"]["steps"]
    assert projection2["unprojectable_summaries"][
        "endpoint_assessment"] == "supported_mineralization"
    # scripted/off:模型请求登记 0,网络 0
    conn = sqlite3.connect(str(runs_root / "e2e" / "pollutant.sqlite"))
    kinds = [r[0] for r in conn.execute(
        "SELECT DISTINCT provider_kind FROM model_requests").fetchall()]
    conn.close()
    assert kinds == []


def test_endpoint_stop_reference_broken_refuses_export(
        tmp_path: Path) -> None:
    """endpoint 与搜索状态不一致(stop 权威行删除)⇒ 导出消费拒
    (四分账独立持久化的一致性面;原行/文件保全)。"""
    runs_root, out = _full_fixture(tmp_path)
    digest = out["native_export"]["export_digest"]
    conn = sqlite3.connect(str(runs_root / "s4b" / "pollutant.sqlite"))
    conn.execute("DELETE FROM stop_reason_records WHERE run_id = 's4b'")
    conn.commit()
    conn.close()
    ledger = ledger_for(runs_root, "s4b")
    with pytest.raises(EndpointContractError) as excinfo:
        read_native_export(ledger, runs_root / "s4b", digest)
    assert excinfo.value.detail["kind"] == \
        "endpoint_stop_reference_mismatch"


def test_empty_pool_run_exports_and_projects(tmp_path: Path) -> None:
    """空池(零事件)run:导出与投影仍生成(payload 完整、v3 答卷为
    空步骤;空答卷不是终点结论 —— 信息损失条目披露)。"""
    plan = {"pools": {"CCO": []}}
    runs_root = tmp_path / "runs"
    out = start(tmp_path, "empty", plan,
                profile_policy={"search_limits": {
                    "max_retrievals_per_parent": 2}})
    assert out["counts"]["events"] == 0
    digest = out["native_export"]["export_digest"]
    ledger = ledger_for(runs_root, "empty")
    verified = read_native_export(
        ledger, runs_root / "empty", digest)
    assert verified["payload"]["endpoint_record"][
        "chemical_endpoint_assessment"] == "unknown"
    projection = read_v3_projection(
        runs_root / "empty", out["v3_projection"]["projection_digest"])
    assert projection["route"]["steps"] == []
    axes = {loss["axis"] for loss in projection["information_losses"]}
    assert "no_committed_events_empty_answer" in axes
    assert projection["route"]["root_smiles"] == "CCO"


def test_native_export_v3_projection_conflict_preserves(
        tmp_path: Path) -> None:
    """投影不可变:同 digest 路径不同字节 ⇒ 重落盘拒(保全)。"""
    runs_root, out = _full_fixture(tmp_path)
    digest = out["v3_projection"]["projection_digest"]
    path = projection_path_of(runs_root, "s4b", digest)
    original = path.read_bytes()
    path.write_bytes(b"{}\n")
    with pytest.raises(V3ProjectionContractError) as excinfo:
        persist_v3_projection(
            runs_root / "s4b", {"projection_digest": digest})
    assert excinfo.value.detail["kind"] == "v3_projection_conflict"
    assert path.read_bytes() == b"{}\n"  # 保全(不覆盖)
    path.write_bytes(original)


# ------------------------------------------------ 状态身份闭合(P1 回修,
# criteria-v2 复审 2026-10-14:官方链对持久 states 权威的首次消费)

def test_native_build_rejects_source_corrupted_state_cn(
        tmp_path: Path) -> None:
    """P1 负控(与 Codex 探针同构):合法 O₂ state 落账后,SQLite
    states.payload 的 cn_identity 单点腐蚀(O=O→O;结构/state_id/
    schema 不动)—— 官方链首次消费(原生构建 build_native_result)
    共用 ChemicalState.from_dict 事实重算拒绝(kind=
    native_result_state_corrupt,底层 state_fact_rederivation_mismatch
    原样保全),不再被重新包装为正式结果;恢复入口 from_dict 同拒
    (既有行为对照)。合法正控:同链不腐蚀时构建通过且 state 进
    聚合载荷(digest 可复现)。"""
    from pathway_v43.pollutant.chemstate import (
        STRUCTURE_ORIGIN_SOURCE_PRODUCT,
        ChemicalState,
        ChemicalStateError,
        build_chemical_state,
    )
    from pathway_v43.pollutant.native_result import NativeResultContractError

    runs_root, out = _full_fixture(tmp_path, "p1fix")
    ledger = ledger_for(runs_root, "p1fix")
    endpoint = read_run_endpoint(ledger, ledger.run_id)

    # ---- 合法正控:当前权威构建通过(O₂ 未落账时);digest 可复现 ----
    native_pos = build_native_result(ledger, endpoint_record=endpoint)
    native_pos2 = build_native_result(ledger, endpoint_record=endpoint)
    assert native_pos["content_digest"] == native_pos2["content_digest"]

    # ---- 落合法 O₂ state(出现层齐全)并进聚合载荷 ----
    state = build_chemical_state(
        "O=O", STRUCTURE_ORIGIN_SOURCE_PRODUCT).to_dict()
    ledger.store.put_state(state)
    native_with = build_native_result(ledger, endpoint_record=endpoint)
    assert any(row["state_id"] == state["state_id"]
               for row in native_with["states"])

    # ---- 恢复入口对照:from_dict 对腐蚀载荷同源拒绝(既有行为) ----
    with pytest.raises(ChemicalStateError) as exc_fd:
        ChemicalState.from_dict(dict(state, cn_identity="O"))
    assert exc_fd.value.detail["kind"] == \
        "state_fact_rederivation_mismatch"

    # ---- 单点腐蚀:只改 SQLite 语义块 cn_identity(O=O→O) ----
    row = ledger.conn.execute(
        "SELECT payload FROM states WHERE state_id = ?",
        (state["state_id"],)).fetchone()
    semantic = json.loads(row["payload"])
    assert semantic["cn_identity"] == "O=O"
    semantic["cn_identity"] = "O"
    ledger.conn.execute(
        "UPDATE states SET payload = ? WHERE state_id = ?",
        (json.dumps(semantic, sort_keys=True), state["state_id"]))
    ledger.conn.commit()

    # ---- 官方链首次消费(原生构建)拒绝;底层结构化 detail 保全 ----
    with pytest.raises(NativeResultContractError) as exc:
        build_native_result(ledger, endpoint_record=endpoint)
    assert exc.value.detail["kind"] == "native_result_state_corrupt"
    assert exc.value.detail["state_id"] == state["state_id"]
    assert exc.value.detail["state_error_kind"] == \
        "state_fact_rederivation_mismatch"
    assert exc.value.detail["state_error_detail"]["mismatches"][
        "cn_identity"]["provided"] == "O"


def test_native_build_rejects_state_without_appearances(
        tmp_path: Path) -> None:
    """P1 边界:store 无合法路径只写语义块不写出现;直接 SQL 注入的
    零出现 state 在首次消费 fail-closed 拒绝(不可验证即不授信)。"""
    from pathway_v43.pollutant.native_result import NativeResultContractError

    runs_root, out = _full_fixture(tmp_path, "p1noapp")
    ledger = ledger_for(runs_root, "p1noapp")
    endpoint = read_run_endpoint(ledger, ledger.run_id)
    ledger.conn.execute(
        "INSERT INTO states (state_id, payload, created_at)"
        " VALUES (?, ?, ?)",
        ("cs-ghost", json.dumps({"state_id": "cs-ghost"}), "2026-01-01"))
    ledger.conn.commit()
    with pytest.raises(NativeResultContractError) as exc:
        build_native_result(ledger, endpoint_record=endpoint)
    assert exc.value.detail["kind"] == "native_result_state_unverifiable"
    assert exc.value.detail["state_id"] == "cs-ghost"
