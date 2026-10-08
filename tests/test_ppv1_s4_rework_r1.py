"""S4 回修 r1 回归(确认复核 POLLUTANT_PATHWAY_S4_CODEX_CONFIRM_REVIEW_
2026-10-08 §4 四组 P1:S4-C01/S4-C02/S4-C03/S4-C04)。

本文件只钉住确认复核给出的公开反例(修好后必须拒)与对应正控
(修好后必须保持);既有正常链/幂等/八 kind/12 轴等由
test_ppv1_s4a_endpoint.py / test_ppv1_s4b_export.py 继续覆盖。

- S4-C01(必要条件同源限制):充分矿化声明 + 有来源 essential
  oxygen_regime=aerobic requirement,当前事实缺失/显式 unknown ⇒
  endpoint 保持 unknown(start/resume/首消费/native 导出/v3 摘要
  一致);已知 aerobic/无必要条件正控保持 supported;已知
  anaerobic 冲突 ⇒ conflict 阻断;上下文损坏 ⇒ 首消费拒。
- S4-C02(manifest 绑定 + 必要集合闭合):manifest-only 改坏
  (run_id/契约版本/策略正文/引用,保持原 digest)⇒ core 复算拒;
  自洽新 digest 漏单项必要 production_report 引用 ⇒ 集合闭合拒;
  自洽换 run_id/契约版本/策略正文 ⇒ 绑定拒;原文件保全 + 正控读回。
- S4-C03(空 task_key 的 soutc 聚合):child retrieve 合法空
  task_key 的 no_local_candidate/unresolved_continuation 全文进
  原生输出与 manifest 引用;坏必要 soutc ⇒ build 与导出读取都拒
  (不静默略过);缺键不产空 task_key 引用。
- S4-C04(投影真实原生来源绑定):假 native(删 events/deferred +
  自洽重算 digest)配真 export 引用 ⇒ 构建拒;projection-only
  自洽改内容(重算 projection_digest 换新目录)配真 reference ⇒
  读取拒;真实投影无/有 ledger 均可读;原文件保全。

基线 8735601 上本文件为 collection 红(仅当模块存在;本批新增)。
"""

from __future__ import annotations

import json
import shutil
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pathway_v43.config import resolve_config  # noqa: E402
from pathway_v43.domain.models import (  # noqa: E402
    canonical_json,
    content_hash,
    stable_id,
)
from pathway_v43.pollutant.endpoint import (  # noqa: E402
    EndpointContractError,
    consume_run_endpoint,
    read_run_endpoint,
)
from pathway_v43.pollutant.native_export import (  # noqa: E402
    NativeExportContractError,
    read_native_export,
)
from pathway_v43.pollutant.native_result import (  # noqa: E402
    NativeResultContractError,
    artifact_reference_index,
    build_native_result,
)
from pathway_v43.pollutant.search import SearchLedger  # noqa: E402
from pathway_v43.pollutant.store import PollutantPathwayStore  # noqa: E402
from pathway_v43.pollutant.v3_projection import (  # noqa: E402
    V3ProjectionContractError,
    build_v3_projection,
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
    oxygen_req,
    spec,
)


def start(tmp_path: Path, run_id: str, plan: dict) -> dict:
    return start_run(
        config=resolve_config(), runs_root=tmp_path / "runs",
        run_id=run_id, smiles="CCO", max_depth=3, max_expansions=10,
        max_frontier_width=2, finder=object(), scripted=True,
        profile=PROFILE_POLLUTANT_PATHWAY_V1, ppv1_plan=plan)


def ledger_for(runs_root: Path, run_id: str) -> SearchLedger:
    store = PollutantPathwayStore(runs_root / run_id / "pollutant.sqlite")
    artifacts = ArtifactStore(runs_root, run_id)
    return SearchLedger(store, artifacts, run_id)


def endpoint_record(runs_root: Path, run_id: str) -> dict:
    ledger = ledger_for(runs_root, run_id)
    return read_run_endpoint(ledger, run_id)


def _full_fixture(tmp_path: Path, run_id: str = "s4r1") -> tuple:
    """双备选 + 共同产物 + 充分矿化声明(确认复核反例同源夹具)。"""
    plan = {"pools": {"CCO": [
        spec("B", "CC=O", "donor-B", coproducts=["[H][H]"]),
        spec("C", "CC=O", "donor-C")]},
        "schedule_budget": {"max_select": 1},
        "endpoint_evidence": [mineralization_evidence()]}
    runs_root = tmp_path / "runs"
    out = start(tmp_path, run_id, plan)
    return runs_root, out


def child_retrieve_soutc_keys(ledger) -> list[str]:
    """空 task_key child retrieve 的 soutc 键(确认复核反例定位)。"""
    rows = ledger.conn.execute(
        "SELECT action_id FROM search_actions WHERE run_id = ?"
        " AND task_key = '' AND action_kind = 'retrieve'"
        " ORDER BY action_id", (ledger.run_id,)).fetchall()
    return [stable_id("soutc", str(r["action_id"])) for r in rows]


# ================================================================ S4-C01


@pytest.mark.parametrize("facts", [
    pytest.param([], id="fact_missing"),
    pytest.param([{"key": "oxygen_regime", "value": None,
                   "status": "unknown", "source_ref": "src:synthetic"}],
                 id="fact_explicit_unknown"),
])
def test_c01_unknown_essential_condition_blocks_mineralization(
        tmp_path: Path, facts: list) -> None:
    """C01 主反例(确认复核 §4):充分矿化声明 + 有来源 essential
    oxygen_regime=aerobic,当前事实缺失/显式 unknown ⇒ endpoint 保持
    unknown(event=1);证据全文保留;阻断原因与必要未知键披露;
    derived_from 含 route_conditions_digest;首消费通过(同源重算);
    native 导出与 v3 摘要同值。"""
    plan = {"condition_facts": facts,
            "pools": {"CCO": [spec("B", "CC=O", "donor-B",
                                   requirements=oxygen_req())]},
            "endpoint_evidence": [mineralization_evidence()]}
    runs_root = tmp_path / "runs"
    out = start(tmp_path, "c01u", plan)
    assert out["counts"]["events"] == 1
    endpoint = out["endpoint"]
    assert endpoint["chemical_endpoint_assessment"] == "unknown"
    assert endpoint["necessary_condition_unknown_keys"] == ["oxygen_regime"]
    assert endpoint["necessary_condition_conflict_keys"] == []
    # resume 同值(公共入口全覆盖)
    second = resume_run(config=resolve_config(), runs_root=runs_root,
                        run_id="c01u")
    assert second["endpoint"]["chemical_endpoint_assessment"] == "unknown"
    assert second["endpoint"]["necessary_condition_unknown_keys"] == \
        ["oxygen_regime"]
    # 记录全文:阻断原因 + 逐条必要评估行 + 证据不删
    record = endpoint_record(runs_root, "c01u")
    assert "necessary_conditions_unknown" in \
        record["evidence_summary"]["blocked_reasons"]
    route = record["route_condition_assessment"]
    assert route["necessary_condition_unknown_keys"] == ["oxygen_regime"]
    rows = [row for c in route["contexts"]
            for row in c["necessary_unmet_per_requirement"]]
    assert rows and rows[0]["key"] == "oxygen_regime"
    assert rows[0]["status"] == "unknown"
    assert "no_applicable_fact" in rows[0]["reason"] or \
        "fact_unknown" in rows[0]["reason"]
    assert len(record["endpoint_evidence"]) == 1  # 证据全文保留
    assert "route_conditions_digest" in record["derived_from"]
    # 首消费(严格)同源重算通过
    ledger = ledger_for(runs_root, "c01u")
    assert consume_run_endpoint(ledger, "c01u")[
        "chemical_endpoint_assessment"] == "unknown"
    # native 导出载荷与 v3 摘要同值(resume 后停止视图含会话成分可
    # 合法更新 ⇒ 消费 resume 后的当前导出/投影;事件/预算零新增是
    # 硬边界,由 E2E 测试断言)
    digest = second["native_export"]["export_digest"]
    verified = read_native_export(ledger, runs_root / "c01u", digest)
    assert verified["payload"]["endpoint_record"][
        "chemical_endpoint_assessment"] == "unknown"
    assert verified["payload"]["endpoint_record"][
        "route_condition_assessment"]["necessary_condition_unknown_keys"] \
        == ["oxygen_regime"]
    projection = read_v3_projection(
        runs_root / "c01u", second["v3_projection"]["projection_digest"])
    assert projection["unprojectable_summaries"][
        "endpoint_assessment"] == "unknown"
    assert projection["unprojectable_summaries"][
        "necessary_condition_unknown_keys"] == ["oxygen_regime"]


def test_c01_known_condition_legal_and_no_requirements_supported(
        tmp_path: Path) -> None:
    """C01 正控:已知 aerobic 满足必要条件 / 无必要条件 ⇒ 同证据
    保持 supported(不全拒);v3 摘要同步。"""
    plan = {"condition_facts": [
        {"key": "oxygen_regime", "value": "aerobic",
         "status": "known_present", "source_ref": "src:synthetic"}],
        "pools": {"CCO": [spec("B", "CC=O", "donor-B",
                               requirements=oxygen_req())]},
        "endpoint_evidence": [mineralization_evidence()]}
    runs_root = tmp_path / "runs"
    out = start(tmp_path, "c01k", plan)
    assert out["endpoint"]["chemical_endpoint_assessment"] == \
        "supported_mineralization"
    assert out["endpoint"]["necessary_condition_unknown_keys"] == []
    record = endpoint_record(runs_root, "c01k")
    assert record["evidence_summary"]["blocked_reasons"] == []
    # 无必要条件(确认复核 legal_supported_source 对照)
    plan2 = {"pools": {"CCO": [spec("B", "CC=O", "donor-B")]},
             "endpoint_evidence": [mineralization_evidence()]}
    out2 = start(tmp_path, "c01l", plan2)
    assert out2["endpoint"]["chemical_endpoint_assessment"] == \
        "supported_mineralization"
    assert out2["endpoint"]["necessary_condition_unknown_keys"] == []


def test_c01_conflict_essential_condition_blocks_with_evidence(
        tmp_path: Path) -> None:
    """C01 冲突反例(确认复核补充观察):已知 anaerobic 与 essential
    aerobic 冲突 ⇒ conflict 阻断,证据保留。"""
    plan = {"condition_facts": [
        {"key": "oxygen_regime", "value": "anaerobic",
         "status": "known_present", "source_ref": "src:synthetic"}],
        "pools": {"CCO": [spec("B", "CC=O", "donor-B",
                               requirements=oxygen_req())]},
        "endpoint_evidence": [mineralization_evidence()]}
    out = start(tmp_path, "c01c", plan)
    assert out["endpoint"]["chemical_endpoint_assessment"] == "unknown"
    assert out["endpoint"]["necessary_condition_conflict_keys"] == \
        ["oxygen_regime"]
    record = endpoint_record(tmp_path / "runs", "c01c")
    assert "necessary_conditions_conflict" in \
        record["evidence_summary"]["blocked_reasons"]
    assert len(record["endpoint_evidence"]) == 1


def test_c01_corrupt_context_refuses_first_consumption(
        tmp_path: Path) -> None:
    """C01 消费同源:route_conditions_digest 的重算消费上下文权威 ——
    上下文 artifact 损坏 ⇒ 首消费拒(endpoint_context_consumption_
    failed),不清洗后继续。"""
    plan = {"pools": {"CCO": [spec("B", "CC=O", "donor-B",
                                   requirements=oxygen_req())]},
            "endpoint_evidence": [mineralization_evidence()]}
    runs_root = tmp_path / "runs"
    out = start(tmp_path, "c01x", plan)
    ledger = ledger_for(runs_root, "c01x")
    refs = ledger.conn.execute(
        "SELECT DISTINCT context_ref FROM search_actions WHERE run_id = ?"
        " AND context_ref != ''", ("c01x",)).fetchall()
    ctx_ref = str(refs[0]["context_ref"])
    ctx_path = runs_root / "c01x" / "results" / f"ctx:{ctx_ref}" / \
        "path_context.json"
    backup = ctx_path.read_bytes()
    envelope = json.loads(backup)
    # 注入新事实(任何上下文都必然改变载荷内容 ⇒ payload_hash 失配)
    envelope["payload"]["condition_facts"] = [
        {"key": "oxygen_regime", "value": "aerobic",
         "status": "known_present", "source_ref": "tampered"}]
    ctx_path.write_text(canonical_json(envelope) + "\n", encoding="utf-8")
    with pytest.raises(EndpointContractError) as excinfo:
        read_run_endpoint(ledger, "c01x")
    assert excinfo.value.detail["kind"] == \
        "endpoint_context_consumption_failed"
    ctx_path.write_bytes(backup)
    assert read_run_endpoint(ledger, "c01x")[
        "chemical_endpoint_assessment"] == "unknown"


# ================================================================ S4-C03


def test_c03_child_retrieve_soutc_aggregated_full_text(
        tmp_path: Path) -> None:
    """C03 主反例:child retrieve 合法空 task_key 的
    no_local_candidate/unresolved_continuation 全文进原生输出与
    manifest 引用;无空 task_key 引用。"""
    runs_root, out = _full_fixture(tmp_path, "c03a")
    ledger = ledger_for(runs_root, "c03a")
    keys = child_retrieve_soutc_keys(ledger)
    assert len(keys) == 2  # 双备选/共同产物夹具的两个 child retrieve
    # 索引:空 task_key 不产空引用;soutc 键独立枚举
    index = artifact_reference_index(ledger)
    assert all(e["task_key"] for e in index)
    assert set(keys) <= {e["task_key"] for e in index}
    # 原生对象:child soutc 全文(no_local_candidate + unresolved_
    # continuation=True)
    native = build_native_result(
        ledger, endpoint_record=read_run_endpoint(ledger, "c03a"))
    by_key = {o["task_key"]: o["outcome_payload"]
              for o in native["expansion_outcomes"]}
    for key in keys:
        assert key in by_key, key
        outcome = by_key[key].get("outcome") or {}
        assert outcome.get("kind") == "no_local_candidate"
        assert (outcome.get("detail") or {}).get(
            "unresolved_continuation") is True
    # manifest 引用集合(同一索引)且导出读取通过
    digest = out["native_export"]["export_digest"]
    manifest = json.loads(
        (runs_root / "c03a" / "native_export" / digest[:24] /
         "manifest.json").read_text(encoding="utf-8"))
    for key in keys:
        assert f"{key}/expansion_outcome" in manifest["artifact_references"]
    read_native_export(ledger, runs_root / "c03a", digest)


def test_c03_corrupt_child_soutc_refused_by_build_and_read(
        tmp_path: Path) -> None:
    """C03 首消费:坏必要 soutc(H07 损坏)不能被跳过 —— build_native_
    result 与 read_native_export 都拒;还原正控通过。"""
    runs_root, out = _full_fixture(tmp_path, "c03b")
    ledger = ledger_for(runs_root, "c03b")
    key = child_retrieve_soutc_keys(ledger)[0]
    path = runs_root / "c03b" / "results" / key / "expansion_outcome.json"
    backup = path.read_bytes()
    envelope = json.loads(backup)
    envelope["payload"]["outcome"] = {"kind": "tampered"}
    path.write_text(canonical_json(envelope) + "\n", encoding="utf-8")
    with pytest.raises(NativeResultContractError) as excinfo:
        build_native_result(
            ledger, endpoint_record=read_run_endpoint(ledger, "c03b"))
    assert excinfo.value.detail["kind"] == "native_result_artifact_corrupt"
    with pytest.raises(NativeExportContractError) as excinfo:
        read_native_export(
            ledger, runs_root / "c03b", out["native_export"]["export_digest"])
    assert excinfo.value.detail["kind"] == "export_reference_mismatch"
    path.write_bytes(backup)
    build_native_result(
        ledger, endpoint_record=read_run_endpoint(ledger, "c03b"))
    read_native_export(
        ledger, runs_root / "c03b", out["native_export"]["export_digest"])


# ================================================================ S4-C02


@pytest.mark.parametrize("field,mutate", [
    pytest.param("run_id",
                 lambda m: m.update({"run_id": "other-run"}),
                 id="run_id"),
    pytest.param("contract_profile",
                 lambda m: m["contract_versions"].update(
                     {"profile": "ppv1-profile-99"}),
                 id="contract_profile"),
    pytest.param("policy_body",
                 lambda m: m["export_policy"].update(
                     {"overwrite": "allowed"}),
                 id="policy_body"),
    pytest.param("artifact_references",
                 lambda m: m["artifact_references"].popitem(),
                 id="artifact_references"),
])
def test_c02_manifest_only_edits_refused_by_core_digest(
        tmp_path: Path, field: str, mutate) -> None:
    """C02 反例 A:仅改 manifest 单字段保持原 export_digest ⇒ manifest
    core 自身 digest 复算拒(export_manifest_corrupt);原字节保全,
    还原后正控读回。"""
    runs_root, out = _full_fixture(tmp_path, "c02a")
    ledger = ledger_for(runs_root, "c02a")
    digest = out["native_export"]["export_digest"]
    manifest_path = (runs_root / "c02a" / "native_export" /
                     digest[:24] / "manifest.json")
    original = manifest_path.read_bytes()
    manifest = json.loads(original)
    mutate(manifest)
    manifest_path.write_text(canonical_json(manifest) + "\n",
                             encoding="utf-8")
    with pytest.raises(NativeExportContractError) as excinfo:
        read_native_export(ledger, runs_root / "c02a", digest)
    assert excinfo.value.detail["kind"] == "export_manifest_corrupt"
    assert excinfo.value.detail["check"] == "manifest_core_digest"
    manifest_path.write_bytes(original)
    read_native_export(ledger, runs_root / "c02a", digest)  # 正控


def _resealed_manifest(manifest: dict, drop_pred) -> tuple:
    """自洽重封:删满足谓词的引用,重算 export_digest(新目录新身份)。"""
    mutated = json.loads(json.dumps(manifest))
    for k in [k for k in mutated["artifact_references"] if drop_pred(k)]:
        del mutated["artifact_references"][k]
    mutated.pop("export_digest", None)
    new_digest = content_hash(mutated)
    mutated["export_digest"] = new_digest
    return mutated, new_digest


def test_c02_self_consistent_reseal_missing_necessary_ref(
        tmp_path: Path) -> None:
    """C02 反例 B:自洽重封(重算 manifest core/export_digest、复制
    原 payload、新目录)漏单项必要 production_report 引用 ⇒ 必要
    集合闭合拒;原导出不受影响(保全);坏/缺 H07 由逐行校验拒
    (C03 测试覆盖坏 H07)。"""
    runs_root, out = _full_fixture(tmp_path, "c02b")
    ledger = ledger_for(runs_root, "c02b")
    digest = out["native_export"]["export_digest"]
    out_dir = runs_root / "c02b" / "native_export" / digest[:24]
    manifest = json.loads(
        (out_dir / "manifest.json").read_text(encoding="utf-8"))
    mutated, new_digest = _resealed_manifest(
        manifest, lambda k: "/production_report" in k)
    assert new_digest != digest
    new_dir = runs_root / "c02b" / "native_export" / new_digest[:24]
    new_dir.mkdir(parents=True)
    shutil.copy(str(out_dir / "payload.json"),
                str(new_dir / "payload.json"))
    (new_dir / "manifest.json").write_text(
        canonical_json(mutated) + "\n", encoding="utf-8")
    with pytest.raises(NativeExportContractError) as excinfo:
        read_native_export(ledger, runs_root / "c02b", new_digest)
    assert excinfo.value.detail["kind"] == "export_reference_mismatch"
    assert excinfo.value.detail["check"] == \
        "necessary_artifact_reference_set_closure"
    assert excinfo.value.detail["omitted_necessary_refs"]
    # 复合案:全删 soutc 引用同样拒
    mutated2, new_digest2 = _resealed_manifest(
        manifest, lambda k: k.startswith("soutc_"))
    new_dir2 = runs_root / "c02b" / "native_export" / new_digest2[:24]
    new_dir2.mkdir(parents=True)
    shutil.copy(str(out_dir / "payload.json"),
                str(new_dir2 / "payload.json"))
    (new_dir2 / "manifest.json").write_text(
        canonical_json(mutated2) + "\n", encoding="utf-8")
    with pytest.raises(NativeExportContractError) as excinfo:
        read_native_export(ledger, runs_root / "c02b", new_digest2)
    assert excinfo.value.detail["kind"] == "export_reference_mismatch"
    assert len(excinfo.value.detail["omitted_necessary_refs"]) >= 2
    # 原导出不受影响(保全 + 正控读回)
    read_native_export(ledger, runs_root / "c02b", digest)


def test_c02_self_consistent_run_and_contract_and_policy_binding(
        tmp_path: Path) -> None:
    """C02 绑定:自洽重封(重算 export_digest)换 run_id/契约版本/
    策略正文 ⇒ run 绑定/版本门/策略正文绑定拒(不是仅 core 自比较)。"""
    runs_root, out = _full_fixture(tmp_path, "c02c")
    ledger = ledger_for(runs_root, "c02c")
    digest = out["native_export"]["export_digest"]
    out_dir = runs_root / "c02c" / "native_export" / digest[:24]
    manifest = json.loads(
        (out_dir / "manifest.json").read_text(encoding="utf-8"))
    payload_bytes = (out_dir / "payload.json").read_bytes()

    def reseal(mutate) -> str:
        mutated = json.loads(json.dumps(manifest))
        mutate(mutated)
        mutated.pop("export_digest", None)
        new_digest = content_hash(mutated)
        mutated["export_digest"] = new_digest
        new_dir = runs_root / "c02c" / "native_export" / new_digest[:24]
        new_dir.mkdir(parents=True)
        (new_dir / "payload.json").write_bytes(payload_bytes)
        (new_dir / "manifest.json").write_text(
            canonical_json(mutated) + "\n", encoding="utf-8")
        return new_digest

    # 换 run_id(其余自洽)⇒ run 绑定拒
    with pytest.raises(NativeExportContractError) as excinfo:
        read_native_export(ledger, runs_root / "c02c",
                           reseal(lambda m: m.update({"run_id": "zz"})))
    assert excinfo.value.detail["kind"] == "export_reference_mismatch"
    assert excinfo.value.detail["check"] == "run_binding"
    # 换契约版本(其余自洽)⇒ 版本门拒
    with pytest.raises(NativeExportContractError) as excinfo:
        read_native_export(
            ledger, runs_root / "c02c",
            reseal(lambda m: m["contract_versions"].update(
                {"store": "ppv1-store-99"})))
    assert excinfo.value.detail["kind"] == "export_version_unknown"
    assert "store" in excinfo.value.detail["changed_contracts"]
    # 改策略正文、保持自记 export_policy_sha256(其余自洽)⇒ 策略
    # 正文与 hash 绑定拒
    with pytest.raises(NativeExportContractError) as excinfo:
        read_native_export(
            ledger, runs_root / "c02c",
            reseal(lambda m: m["export_policy"].update(
                {"overwrite": "allowed"})))
    assert excinfo.value.detail["kind"] == "export_policy_stale"
    # 原导出正控
    read_native_export(ledger, runs_root / "c02c", digest)


def test_c02_dangling_recorded_ref_refused(tmp_path: Path) -> None:
    """C02 缺 H07:manifest 记录的必要 artifact 被删 ⇒ 逐行校验拒
    (保全;还原正控)。"""
    runs_root, out = _full_fixture(tmp_path, "c02d")
    ledger = ledger_for(runs_root, "c02d")
    digest = out["native_export"]["export_digest"]
    key = child_retrieve_soutc_keys(ledger)[0]
    path = runs_root / "c02d" / "results" / key / "expansion_outcome.json"
    backup = tmp_path / "soutc_backup.json"
    shutil.move(str(path), backup)
    with pytest.raises(NativeExportContractError) as excinfo:
        read_native_export(ledger, runs_root / "c02d", digest)
    assert excinfo.value.detail["kind"] == "export_reference_mismatch"
    assert excinfo.value.detail["artifact"] == \
        f"{key}/expansion_outcome"
    shutil.move(str(backup), str(path))
    read_native_export(ledger, runs_root / "c02d", digest)


# ================================================================ S4-C04


def test_c04_fake_native_with_real_export_ref_refused_at_build(
        tmp_path: Path) -> None:
    """C04 反例 A:复制真 native 删 events/deferred 后自洽重算
    content_digest,配真 export 引用 ⇒ build_v3_projection 拒(构建
    侧消费已验证原生来源);不落任何投影文件。"""
    runs_root, out = _full_fixture(tmp_path, "c04a")
    ledger = ledger_for(runs_root, "c04a")
    digest = out["native_export"]["export_digest"]
    verified = read_native_export(ledger, runs_root / "c04a", digest)
    fake = json.loads(json.dumps(verified["payload"]))
    fake["events"] = []
    fake["deferred_entries"] = []
    fake.pop("content_digest", None)
    fake["content_digest"] = content_hash(fake)
    export_summary = {"export_digest": digest,
                      "payload_sha256": verified["payload_sha256"]}
    before = sorted(p.name for p in
                    (runs_root / "c04a" / "v3_projection").iterdir())
    with pytest.raises(V3ProjectionContractError) as excinfo:
        build_v3_projection(ledger, fake, native_export=export_summary,
                            run_dir=runs_root / "c04a")
    assert excinfo.value.detail["kind"] == \
        "v3_projection_source_binding_mismatch"
    after = sorted(p.name for p in
                   (runs_root / "c04a" / "v3_projection").iterdir())
    assert after == before  # 零新投影目录(构建失败不落盘)


def test_c04_projection_only_tamper_refused_at_read(tmp_path: Path) -> None:
    """C04 反例 B:只改投影已表达字段(steps/deferred 计数)并自洽
    重算 projection_digest 换新目录,native_reference 全真 ⇒
    read_v3_projection 拒(adapter 同源复算);真原生/真投影不受影响;
    反向消费禁止面(零 DB 写)保持。"""
    runs_root, out = _full_fixture(tmp_path, "c04b")
    ledger = ledger_for(runs_root, "c04b")
    export_digest = out["native_export"]["export_digest"]
    projection_digest = out["v3_projection"]["projection_digest"]
    proj_path = (runs_root / "c04b" / "v3_projection" /
                 projection_digest[:24] / "projection.json")
    projection = json.loads(proj_path.read_text(encoding="utf-8"))
    steps_before = projection["route"]["steps"]
    assert steps_before  # 夹具有已提交事件
    tampered = json.loads(json.dumps(projection))
    tampered["route"]["steps"] = []
    tampered["unprojectable_summaries"]["deferred_entry_count"] = 0
    tampered.pop("projection_digest", None)
    tampered["projection_digest"] = content_hash(tampered)
    tampered_dir = runs_root / "c04b" / "v3_projection" / \
        tampered["projection_digest"][:24]
    tampered_dir.mkdir(parents=True)
    (tampered_dir / "projection.json").write_text(
        canonical_json(tampered) + "\n", encoding="utf-8")
    with pytest.raises(V3ProjectionContractError) as excinfo:
        read_v3_projection(
            runs_root / "c04b", tampered["projection_digest"])
    assert excinfo.value.detail["kind"] == \
        "v3_projection_source_binding_mismatch"
    assert excinfo.value.detail["check"] == "adapter_derived_content"
    assert "route.steps" in excinfo.value.detail["mismatched_fields"]
    # 真原生/真投影不受影响(保全;无/有 ledger 均可读)
    read_native_export(ledger, runs_root / "c04b", export_digest)
    assert read_v3_projection(
        runs_root / "c04b", projection_digest)["route"]["steps"] == \
        steps_before
    assert read_v3_projection(
        runs_root / "c04b", projection_digest, ledger=ledger)[
        "route"]["steps"] == steps_before


def test_c04_mixed_native_reference_refused_at_read(
        tmp_path: Path) -> None:
    """C04 混搭:投影自洽重算后换 native_reference 的 content_digest/
    task_key(真 export digest 保留)⇒ 引用内部一致拒(已验证原生
    存在/投影自 hash 不是投影证书)。"""
    runs_root, out = _full_fixture(tmp_path, "c04c")
    projection_digest = out["v3_projection"]["projection_digest"]
    proj_path = (runs_root / "c04c" / "v3_projection" /
                 projection_digest[:24] / "projection.json")
    projection = json.loads(proj_path.read_text(encoding="utf-8"))
    tampered = json.loads(json.dumps(projection))
    tampered["native_reference"]["native_result_content_digest"] = \
        "f" * 64
    tampered["native_reference"]["native_result_task_key"] = \
        "run-native-result:" + "f" * 24
    tampered.pop("projection_digest", None)
    tampered["projection_digest"] = content_hash(tampered)
    tampered_dir = runs_root / "c04c" / "v3_projection" / \
        tampered["projection_digest"][:24]
    tampered_dir.mkdir(parents=True)
    (tampered_dir / "projection.json").write_text(
        canonical_json(tampered) + "\n", encoding="utf-8")
    with pytest.raises(V3ProjectionContractError) as excinfo:
        read_v3_projection(
            runs_root / "c04c", tampered["projection_digest"])
    assert excinfo.value.detail["kind"] == \
        "v3_projection_source_binding_mismatch"
    assert excinfo.value.detail["check"] == \
        "native_reference_internal_consistency"
    assert "reference_content_digest" in \
        excinfo.value.detail["binding_failures"]


def test_c04_projection_read_with_ledger_consumes_native_first(
        tmp_path: Path) -> None:
    """C04 正控 + 原生首消费联动:read_v3_projection(ledger=...) 先走
    read_native_export 完整首消费 —— 原生导出文件缺失 ⇒ 投影读取拒
    (不吞成成功);还原后通过。"""
    runs_root, out = _full_fixture(tmp_path, "c04d")
    ledger = ledger_for(runs_root, "c04d")
    export_digest = out["native_export"]["export_digest"]
    projection_digest = out["v3_projection"]["projection_digest"]
    manifest_path = (runs_root / "c04d" / "native_export" /
                     export_digest[:24] / "manifest.json")
    backup = tmp_path / "manifest_backup.json"
    shutil.move(str(manifest_path), backup)
    with pytest.raises(V3ProjectionContractError) as excinfo:
        read_v3_projection(runs_root / "c04d", projection_digest,
                           ledger=ledger)
    assert excinfo.value.detail["kind"] == \
        "v3_projection_source_binding_mismatch"
    shutil.move(str(backup), str(manifest_path))
    read_v3_projection(runs_root / "c04d", projection_digest,
                       ledger=ledger)


# ------------------------------------------------ 公共链一致性(E2E 面)


def test_rework_full_public_chain_consistency(tmp_path: Path) -> None:
    """回修后完整公共链:start → 四分账/导出/投影/双首消费 → resume
    幂等(事件/预算零新增)→ 三处消费一致(记录/native/v3 摘要)。"""
    runs_root, out = _full_fixture(tmp_path, "e2er")
    ledger = ledger_for(runs_root, "e2er")
    counts_before = out["counts"]
    record = read_run_endpoint(ledger, "e2er")
    verified = read_native_export(
        ledger, runs_root / "e2er", out["native_export"]["export_digest"])
    projection = read_v3_projection(
        runs_root / "e2er", out["v3_projection"]["projection_digest"],
        ledger=ledger)
    # 三处一致(native 载荷的 endpoint 记录 = 首消费读回的记录;
    # DB 行 hash 与公共 summary 一致)
    assert verified["payload"]["endpoint_record"] == record
    assert verified["manifest"]["authority_references"][
        "endpoint_record_payload_hash"] == \
        out["endpoint_record_payload_hash"]
    assert projection["unprojectable_summaries"]["endpoint_assessment"] \
        == record["chemical_endpoint_assessment"]
    second = resume_run(config=resolve_config(), runs_root=runs_root,
                        run_id="e2er")
    assert second["counts"] == counts_before  # 幂等硬边界
    conn = sqlite3.connect(
        str(runs_root / "e2er" / "pollutant.sqlite"))
    assert conn.execute("SELECT COUNT(*) FROM model_requests"
                        ).fetchone()[0] == 0
    conn.close()
