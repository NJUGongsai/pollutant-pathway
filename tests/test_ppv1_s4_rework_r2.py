"""S4 回修 r2 回归(复审 R2 POLLUTANT_PATHWAY_S4_CODEX_REVIEW_R2_
2026-10-08 §4 剩余两组 P1:S4-C02 必要集合不由文件存在决定、S4-C04
无 ledger 投影首读核父来源版本)。

本文件只钉住复审 R2 给出的公开反例(修好后必须拒)与对应正控
(修好后必须保持);既有正常链/幂等/八 kind/12 轴/B4 恢复/确定性
由 test_ppv1_s4a_endpoint.py / test_ppv1_s4b_export.py /
test_ppv1_s4_rework_r1.py 继续覆盖。

- S4-C02(single_ref_missing 主反例 + 三变体):删已完成任务
  production_report 文件 + 删 manifest 同引用 + 自洽重算新 digest
  (DB/native 均不改)⇒ 必要集合闭合先结构化拒(依据 = 原生实际
  消费 payload 引用;必要性独立证据:done expand + 提交记录 +
  事件 + payload audit 同 task/action);零业务写、缺席形态保全、
  原导出不受影响、还原正控通过。仅删引用(文件在)/文件坏 +
  引用删同样拒。导出侧写入前对必要项缺文件(实际必需 soutc)同样
  先拒(零新导出目录);**B4 恢复补账合法不产 production_report
  保持可导出**(行闭合不强加"done expand 必有报告"—— submitted
  报告在 complete 之后落盘,B4 幂等补账不重放生产链)。
- S4-C04(无 ledger 父来源版本门):真实引用来源 manifest 的
  schema_version / contract_versions.profile 改为 UNKNOWN、native
  payload 的 native_result_version 改为 UNKNOWN/缺失,均自洽重封
  (payload 字节/DB/steps 不变)并让投影 reference 指向新文件 ⇒
  无 ledger 投影首读先拒(v3_native_source_version_unknown,先于
  当前 adapter 解释内容);有 ledger 经原生首消费拒;原生读取拒。
  版本组缺失(contract_versions 整块删)与投影自记版本组冲突同
  拒。合法无/有 ledger 读取、12 损失轴/空答卷、零写保持。

基线 0dd35d1 上本文件为新增;C02 文件+引用同删案与 C04 全部
版本门案为行为红(父上未发生预期拒绝),三变体正控、B4 合法
缺席与合法读取为绿。
"""

from __future__ import annotations

import hashlib
import json
import shutil
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
from pathway_v43.pollutant.endpoint import read_run_endpoint  # noqa: E402
from pathway_v43.pollutant.native_export import (  # noqa: E402
    NativeExportContractError,
    export_native_result,
    list_native_exports,
    read_native_export,
)
from pathway_v43.pollutant.native_result import build_native_result  # noqa: E402
from pathway_v43.pollutant.runflow import start_ppv1_run  # noqa: E402
from pathway_v43.pollutant.search import (  # noqa: E402
    SearchCrashInjection,
    SearchLedger,
)
from pathway_v43.pollutant.store import PollutantPathwayStore  # noqa: E402
from pathway_v43.pollutant.v3_projection import (  # noqa: E402
    V3ProjectionContractError,
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


def start(tmp_path: Path, run_id: str, plan: dict, **kwargs) -> dict:
    return start_run(
        config=resolve_config(), runs_root=tmp_path / "runs",
        run_id=run_id, smiles="CCO", max_depth=3, max_expansions=10,
        max_frontier_width=2, finder=object(), scripted=True,
        profile=PROFILE_POLLUTANT_PATHWAY_V1, ppv1_plan=plan, **kwargs)


def ledger_for(runs_root: Path, run_id: str) -> SearchLedger:
    store = PollutantPathwayStore(runs_root / run_id / "pollutant.sqlite")
    artifacts = ArtifactStore(runs_root, run_id)
    return SearchLedger(store, artifacts, run_id)


def _full_fixture(tmp_path: Path, run_id: str) -> tuple:
    """双备选 + 共同产物 + 充分矿化声明(复审 R2 反例同源夹具)。"""
    plan = {"pools": {"CCO": [
        spec("B", "CC=O", "donor-B", coproducts=["[H][H]"]),
        spec("C", "CC=O", "donor-C")]},
        "schedule_budget": {"max_select": 1},
        "endpoint_evidence": [mineralization_evidence()]}
    runs_root = tmp_path / "runs"
    out = start(tmp_path, run_id, plan)
    return runs_root, out


def child_retrieve_soutc_keys(ledger) -> list[str]:
    """空 task_key child retrieve 的 soutc 键(C03 同源定位)。"""
    rows = ledger.conn.execute(
        "SELECT action_id FROM search_actions WHERE run_id = ?"
        " AND task_key = '' AND action_kind = 'retrieve'"
        " ORDER BY action_id", (ledger.run_id,)).fetchall()
    return [stable_id("soutc", str(r["action_id"])) for r in rows]


def table_hashes(ledger) -> dict:
    """全部持久表的内容 digest 快照(零业务写断言用;全行稳定排序)。"""
    out = {}
    names = [r[0] for r in ledger.conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
        " AND name NOT LIKE 'sqlite_%' ORDER BY name")]
    for name in names:
        rows = [dict(r) for r in ledger.conn.execute(
            f"SELECT * FROM {name}")]
        out[name] = content_hash(sorted(
            (json.dumps(r, sort_keys=True, ensure_ascii=False)
             for r in rows)))
    return out


def _repackage(run_dir: Path, manifest: dict,
               payload_bytes: bytes) -> tuple:
    """自洽重封:重算 manifest core/export_digest,新目录,复制 payload。"""
    mutated = json.loads(json.dumps(manifest))
    mutated.pop("export_digest", None)
    digest = content_hash(mutated)
    mutated["export_digest"] = digest
    new_dir = run_dir / "native_export" / digest[:24]
    new_dir.mkdir(parents=True, exist_ok=True)
    (new_dir / "payload.json").write_bytes(payload_bytes)
    (new_dir / "manifest.json").write_text(
        canonical_json(mutated) + "\n", encoding="utf-8")
    return digest, new_dir


def _resealed_projection(run_dir: Path, projection: dict,
                         *, export_digest: str,
                         content_digest: str | None = None,
                         payload_sha: str | None = None,
                         mutate=None) -> str:
    """自洽重封投影:更新 native_reference(默认指向给定 export),
    可选再改载荷(mutate),重算 projection_digest 落新目录。"""
    tampered = json.loads(json.dumps(projection))
    tampered["native_reference"]["native_export_digest"] = export_digest
    if content_digest is not None:
        tampered["native_reference"][
            "native_result_content_digest"] = content_digest
    if payload_sha is not None:
        tampered["native_reference"][
            "native_export_payload_sha256"] = payload_sha
    if mutate is not None:
        mutate(tampered)
    tampered.pop("projection_digest", None)
    tampered["projection_digest"] = content_hash(tampered)
    new_dir = run_dir / "v3_projection" / \
        tampered["projection_digest"][:24]
    new_dir.mkdir(parents=True, exist_ok=True)
    (new_dir / "projection.json").write_text(
        canonical_json(tampered) + "\n", encoding="utf-8")
    return tampered["projection_digest"]


# ================================================================ S4-C02


@pytest.mark.parametrize("mode", [
    pytest.param("intact", id="ref_only_file_intact"),
    pytest.param("corrupt", id="file_corrupt_ref_dropped"),
    pytest.param("missing", id="file_and_ref_deleted_selfconsistent"),
])
def test_c02_single_ref_variants_refused(tmp_path: Path, mode: str) -> None:
    """C02 主反例(复审 R2 §4 single_ref_missing 三变体):对已完成
    expand 任务的 production_report —— ①仅删 manifest 引用(文件在);
    ②文件改坏 + 删引用;③**文件与引用一起删 + 自洽重算新 digest**
    (DB/native 均不改)⇒ 读取一律先结构化拒(必要集合闭合;③由
    原生实际消费闭合捕获,不再被"枚举时文件不存在=合法缺席"放过);
    零业务写、原 payload/native 权威/缺席形态保全、还原正控通过。"""
    run_id = f"c02r2-{mode}"
    runs_root, out = _full_fixture(tmp_path, run_id)
    ledger = ledger_for(runs_root, run_id)
    digest = out["native_export"]["export_digest"]
    out_dir = runs_root / run_id / "native_export" / digest[:24]
    manifest = json.loads(
        (out_dir / "manifest.json").read_text(encoding="utf-8"))
    payload_bytes = (out_dir / "payload.json").read_bytes()
    before = table_hashes(ledger)
    ref = next(k for k in manifest["artifact_references"]
               if k.endswith("/production_report"))
    task, name = ref.rsplit("/", 1)
    path = runs_root / run_id / "results" / task / (name + ".json")
    raw = path.read_bytes()
    # ---- 必要性独立证据(复审 necessary_report_basis.json 同源):
    # done expand + 已登记提交记录 + 事件 + 原生 payload 实际消费 ----
    row = ledger.conn.execute(
        "SELECT action_id, action_kind, status FROM search_actions"
        " WHERE run_id = ? AND task_key = ?",
        (run_id, task)).fetchone()
    assert row is not None and row["action_kind"] == "expand_hypothesis"
    assert row["status"] == "done"
    commit = ledger.conn.execute(
        "SELECT commit_kind, event_id FROM search_commit_records"
        " WHERE action_id = ?", (row["action_id"],)).fetchone()
    assert commit is not None and commit["commit_kind"] == "event_committed"
    assert commit["event_id"]
    payload = json.loads(payload_bytes)
    assert any(r.get("task_key") == task
               for r in payload["audit_production_reports"])
    native_key = manifest["authority_references"]["native_result_task_key"]
    native_path = runs_root / run_id / "results" / native_key / \
        "native_result.json"
    native_sha_before = hashlib.sha256(
        native_path.read_bytes()).hexdigest()
    # ---- 变体注入 ----
    if mode == "corrupt":
        bad = json.loads(raw)
        bad["payload"]["codex_corrupt_dependency"] = True
        path.write_text(canonical_json(bad) + "\n", encoding="utf-8")
    if mode == "missing":
        path.unlink()
    # 原 digest 读:引用仍在 ⇒ 逐行校验拒(坏/缺);intact 则通过
    if mode == "intact":
        read_native_export(ledger, runs_root / run_id, digest)
    else:
        with pytest.raises(NativeExportContractError) as excinfo:
            read_native_export(ledger, runs_root / run_id, digest)
        assert excinfo.value.detail["kind"] == "export_reference_mismatch"
        assert excinfo.value.detail["artifact"] == ref
    # ---- 删 manifest 同引用 + 自洽重算新 digest(DB/native 不改) ----
    mutated = json.loads(json.dumps(manifest))
    mutated["artifact_references"].pop(ref)
    new_digest, new_dir = _repackage(
        runs_root / run_id, mutated, payload_bytes)
    assert new_digest != digest
    with pytest.raises(NativeExportContractError) as excinfo:
        read_native_export(ledger, runs_root / run_id, new_digest)
    detail = excinfo.value.detail
    assert detail["kind"] == "export_reference_mismatch"
    if mode == "corrupt":
        # 坏文件在集合闭合枚举侧先撞 H07 完整性拒(artifact 级;
        # 先于集合比对 —— 与旧语义一致:坏必要 artifact 不静默跳过)
        assert detail.get("artifact") == ref
        assert detail.get("artifact_error_kind")
    else:
        assert detail["check"] == "necessary_artifact_reference_set_closure"
        assert ref in detail["omitted_necessary_refs"]
        assert detail["necessary_basis"][ref] == \
            "payload_audit_production_report_consumed"
    # ---- 零业务写 / 原 payload / native 权威 / 缺席形态保全 ----
    assert table_hashes(ledger) == before
    assert (out_dir / "payload.json").read_bytes() == payload_bytes
    assert (new_dir / "payload.json").read_bytes() == payload_bytes
    native_key = manifest["authority_references"]["native_result_task_key"]
    native_path = runs_root / run_id / "results" / native_key / \
        "native_result.json"
    assert hashlib.sha256(native_path.read_bytes()).hexdigest() == \
        native_sha_before
    if mode == "corrupt":
        assert path.read_bytes() != raw  # 坏字节形态保全(未清洗)
    if mode == "missing":
        assert not path.exists()  # 缺席形态保全(未补写)
    # ---- 还原正控 ----
    path.write_bytes(raw)
    read_native_export(ledger, runs_root / run_id, digest)


def test_c02_export_write_side_refuses_missing_necessary_soutc(
        tmp_path: Path) -> None:
    """C02 写入侧同规则:实际必需的 soutc(done outcome 提交,先写
    后完成)文件缺席时,export_native_result **先结构化拒**(不封
    不完整 manifest;零新导出目录、零业务写);还原后重导出幂等
    (同 digest,目录数不变)。"""
    run_id = "c02w"
    runs_root, out = _full_fixture(tmp_path, run_id)
    ledger = ledger_for(runs_root, run_id)
    key = child_retrieve_soutc_keys(ledger)[0]
    path = runs_root / run_id / "results" / key / "expansion_outcome.json"
    backup = tmp_path / "soutc_backup.json"
    before = table_hashes(ledger)
    dirs_before = set(list_native_exports(runs_root / run_id))
    shutil.move(str(path), backup)
    # build 合法跳过缺席文件(消费侧合法缺席语义不变)
    native = build_native_result(
        ledger, endpoint_record=read_run_endpoint(ledger, run_id))
    assert all(o.get("task_key") != key
               for o in native["expansion_outcomes"])
    with pytest.raises(NativeExportContractError) as excinfo:
        export_native_result(ledger, native, runs_root / run_id)
    detail = excinfo.value.detail
    assert detail["kind"] == "export_reference_mismatch"
    assert detail["check"] == "necessary_artifact_reference_set_closure"
    assert f"{key}/expansion_outcome" in detail["missing_necessary_files"]
    assert detail["necessary_basis"][f"{key}/expansion_outcome"] == \
        "done_outcome_completion_soutc"
    # 零新导出目录(写入前先拒)、零业务写、原文件形态(仍缺席)
    assert set(list_native_exports(runs_root / run_id)) == dirs_before
    assert table_hashes(ledger) == before
    assert not path.exists()
    # ---- 还原正控:重导出幂等(同 digest、目录数不变) ----
    shutil.move(str(backup), str(path))
    native2 = build_native_result(
        ledger, endpoint_record=read_run_endpoint(ledger, run_id))
    result = export_native_result(ledger, native2, runs_root / run_id)
    assert result["export_digest"] == \
        out["native_export"]["export_digest"]
    assert set(list_native_exports(runs_root / run_id)) == dirs_before
    read_native_export(ledger, runs_root / run_id,
                       result["export_digest"])


def test_c02_b4_recovered_expand_without_report_still_exports(
        tmp_path: Path) -> None:
    """C02 合法边界正控(复审 R2 最低收口"合法未生产保持"):B4 崩溃
    (事件已提交、记账未闭合)⇒ resume 幂等补账完成 action ——
    submitted 报告在 complete 之后落盘,**B4 恢复合法不产
    production_report**;done expand 无报告不是"应有项缺文件",
    导出/读取照常通过(行闭合不强加新科学门)。"""
    plan = {"pools": {"CCO": [spec("B", "CC=O", "donor-B")]}}
    runs_root = tmp_path / "runs"
    with pytest.raises(SearchCrashInjection):
        start_ppv1_run(
            config=resolve_config(), runs_root=runs_root, run_id="c02b4",
            smiles="CCO", plan=plan, scripted=True,
            crash_after="after_event_submitted")
    out = resume_run(config=resolve_config(), runs_root=runs_root,
                     run_id="c02b4")
    assert out["counts"]["events"] == 1
    ledger = ledger_for(runs_root, "c02b4")
    rows = ledger.conn.execute(
        "SELECT task_key FROM search_actions WHERE run_id = ?"
        " AND action_kind = 'expand_hypothesis' AND status = 'done'",
        ("c02b4",)).fetchall()
    task_keys = [str(r["task_key"]) for r in rows]
    assert task_keys
    reports = [runs_root / "c02b4" / "results" / tk /
               "production_report.json" for tk in task_keys]
    assert not any(p.exists() for p in reports)  # B4 补账合法不产报告
    digest = out["native_export"]["export_digest"]
    read_native_export(ledger, runs_root / "c02b4", digest)
    read_v3_projection(runs_root / "c02b4",
                       out["v3_projection"]["projection_digest"])


# ================================================================ S4-C04


@pytest.mark.parametrize("mode", [
    pytest.param("export_schema", id="unknown_export_schema"),
    pytest.param("contract_profile", id="unknown_contract_profile"),
    pytest.param("native_result", id="unknown_native_result"),
    pytest.param("native_result_missing", id="missing_native_result"),
])
def test_c04_unknown_source_version_no_ledger_refused(
        tmp_path: Path, mode: str) -> None:
    """C04 主反例(复审 R2 §4 两最小案 + native_result 版本变体):
    只改真实引用来源 manifest 的 schema_version / contract_versions.
    profile,或 native payload 的 native_result_version(UNKNOWN/
    缺失 + 自洽重算 content_digest),payload 其余字节/DB/steps 均
    不变 ⇒ **无 ledger 投影首读先拒**(v3_native_source_version_
    unknown,先于当前 adapter 解释内容,与有 ledger/构建共用登记
    源);有 ledger 经原生首消费拒;原生读取拒;原文件保全。"""
    run_id = f"c04r2-{mode}"
    runs_root, out = _full_fixture(tmp_path, run_id)
    ledger = ledger_for(runs_root, run_id)
    run_dir = runs_root / run_id
    digest = out["native_export"]["export_digest"]
    projection_digest = out["v3_projection"]["projection_digest"]
    out_dir = run_dir / "native_export" / digest[:24]
    manifest = json.loads(
        (out_dir / "manifest.json").read_text(encoding="utf-8"))
    projection = json.loads(
        (run_dir / "v3_projection" / projection_digest[:24] /
         "projection.json").read_text(encoding="utf-8"))
    steps_before = projection["route"]["steps"]
    before = table_hashes(ledger)
    verified = read_native_export(ledger, run_dir, digest)
    original_payload_bytes = (out_dir / "payload.json").read_bytes()
    original_manifest_bytes = (out_dir / "manifest.json").read_bytes()
    native = verified["payload"]
    source_payload = json.loads(json.dumps(native))
    mutated_manifest = json.loads(json.dumps(manifest))
    expected_problem = {
        "export_schema": "manifest_schema_version",
        "contract_profile": "contract_versions:profile",
        "native_result": "payload_native_result_version",
        "native_result_missing": "payload_native_result_version",
    }[mode]
    if mode == "export_schema":
        mutated_manifest["schema_version"] = "ppv1-native-export-UNKNOWN"
    if mode == "contract_profile":
        mutated_manifest["contract_versions"]["profile"] = \
            "ppv1-profile-UNKNOWN"
    if mode in ("native_result", "native_result_missing"):
        if mode == "native_result":
            source_payload["native_result_version"] = \
                "ppv1-native-result-UNKNOWN"
        else:
            source_payload.pop("native_result_version", None)
        source_payload.pop("content_digest", None)
        source_payload["content_digest"] = content_hash(source_payload)
        mutated_manifest["content_digest"] = \
            source_payload["content_digest"]
    source_bytes = (canonical_json(source_payload) + "\n").encode("utf-8")
    mutated_manifest["payload_sha256"] = \
        hashlib.sha256(source_bytes).hexdigest()
    new_digest, _ = _repackage(run_dir, mutated_manifest, source_bytes)
    new_projection_digest = _resealed_projection(
        run_dir, projection, export_digest=new_digest,
        content_digest=source_payload["content_digest"],
        payload_sha=mutated_manifest["payload_sha256"])
    # ---- 无 ledger 首读:先拒(父来源版本门,先于 adapter 解释) ----
    with pytest.raises(V3ProjectionContractError) as excinfo:
        read_v3_projection(run_dir, new_projection_digest)
    detail = excinfo.value.detail
    assert detail["kind"] == "v3_native_source_version_unknown"
    assert expected_problem in detail["version_problems"]
    # ---- 有 ledger:经原生首消费拒(包装,不吞成成功) ----
    with pytest.raises(V3ProjectionContractError) as excinfo:
        read_v3_projection(run_dir, new_projection_digest, ledger=ledger)
    assert excinfo.value.detail["kind"] == \
        "v3_projection_source_binding_mismatch"
    assert excinfo.value.detail["check"] == "native_export_first_consumption"
    # ---- 原生读取同样拒(版本门;payload/DB 不变) ----
    with pytest.raises(NativeExportContractError) as excinfo:
        read_native_export(ledger, run_dir, new_digest)
    native_detail = excinfo.value.detail
    if mode in ("export_schema", "contract_profile"):
        assert native_detail["kind"] == "export_version_unknown"
    else:
        assert native_detail["kind"] == "export_version_unknown"
        assert native_detail["check"] == "payload_native_result_version_binding"
    # ---- payload 其余字节/DB/steps 均不变(两最小案钉定) ----
    assert table_hashes(ledger) == before
    tampered = json.loads(
        (run_dir / "v3_projection" / new_projection_digest[:24] /
         "projection.json").read_text(encoding="utf-8"))
    assert tampered["route"]["steps"] == steps_before
    excluded = {"content_digest"}
    if mode in ("native_result", "native_result_missing"):
        excluded.add("native_result_version")
    assert {k: v for k, v in source_payload.items()
            if k not in excluded} == \
        {k: v for k, v in native.items() if k not in excluded}
    # ---- 原文件保全 + 正控(真 export/投影无/有 ledger 均可读) ----
    assert (out_dir / "payload.json").read_bytes() == \
        original_payload_bytes
    assert (out_dir / "manifest.json").read_bytes() == \
        original_manifest_bytes
    read_native_export(ledger, run_dir, digest)
    assert read_v3_projection(run_dir, projection_digest)[
        "route"]["steps"] == steps_before
    read_v3_projection(run_dir, projection_digest, ledger=ledger)


def test_c04_version_group_missing_and_projection_conflict_refused(
        tmp_path: Path) -> None:
    """C04 版本组缺失/冲突(复审 R2 §4"native_result 版本与版本组
    缺失/冲突覆盖"):manifest contract_versions 整块删除的自洽重封
    ⇒ 无 ledger 拒(manifest_contract_versions_missing);投影自记
    native_graph_revision.contract_versions 与登记源冲突(自洽重算
    projection_digest)⇒ 无 ledger 拒(projection_contract_versions:
    profile)。原文件保全。"""
    run_id = "c04vg"
    runs_root, out = _full_fixture(tmp_path, run_id)
    ledger = ledger_for(runs_root, run_id)
    run_dir = runs_root / run_id
    digest = out["native_export"]["export_digest"]
    projection_digest = out["v3_projection"]["projection_digest"]
    out_dir = run_dir / "native_export" / digest[:24]
    manifest = json.loads(
        (out_dir / "manifest.json").read_text(encoding="utf-8"))
    projection = json.loads(
        (run_dir / "v3_projection" / projection_digest[:24] /
         "projection.json").read_text(encoding="utf-8"))
    payload_bytes = (out_dir / "payload.json").read_bytes()
    before = table_hashes(ledger)
    # ---- (a) contract_versions 整块缺失 ----
    mutated = json.loads(json.dumps(manifest))
    mutated.pop("contract_versions", None)
    new_digest, _ = _repackage(run_dir, mutated, payload_bytes)
    pd_a = _resealed_projection(
        run_dir, projection, export_digest=new_digest)
    with pytest.raises(V3ProjectionContractError) as excinfo:
        read_v3_projection(run_dir, pd_a)
    assert excinfo.value.detail["kind"] == "v3_native_source_version_unknown"
    assert "manifest_contract_versions_missing" in \
        excinfo.value.detail["version_problems"]
    # ---- (b) 投影自记版本组与登记源冲突 ----
    def _conflict(p: dict) -> None:
        p["native_graph_revision"]["contract_versions"]["profile"] = \
            "ppv1-profile-17"
    pd_b = _resealed_projection(
        run_dir, projection, export_digest=digest, mutate=_conflict)
    with pytest.raises(V3ProjectionContractError) as excinfo:
        read_v3_projection(run_dir, pd_b)
    assert excinfo.value.detail["kind"] == "v3_native_source_version_unknown"
    assert "projection_contract_versions:profile" in \
        excinfo.value.detail["version_problems"]
    # ---- 零业务写 + 原文件保全 + 正控 ----
    assert table_hashes(ledger) == before
    read_native_export(ledger, run_dir, digest)
    read_v3_projection(run_dir, projection_digest)
    read_v3_projection(run_dir, projection_digest, ledger=ledger)


def test_c04_legal_reads_with_version_gates_and_empty_pool(
        tmp_path: Path) -> None:
    """C04 合法正控:已登记来源版本的无/有 ledger 投影读取均通过
    (12 损失轴/空答卷保持;无 ledger 读取零业务写)。"""
    run_id = "c04l"
    runs_root, out = _full_fixture(tmp_path, run_id)
    ledger = ledger_for(runs_root, run_id)
    before = table_hashes(ledger)
    projection_digest = out["v3_projection"]["projection_digest"]
    no_ledger = read_v3_projection(runs_root / run_id, projection_digest)
    with_ledger = read_v3_projection(
        runs_root / run_id, projection_digest, ledger=ledger)
    assert no_ledger == with_ledger
    assert no_ledger["route"]["steps"]
    axes = {loss["axis"] for loss in no_ledger["information_losses"]}
    assert len(axes) >= 12
    assert table_hashes(ledger) == before  # 投影读取零业务写
    # 空池(零事件)答卷:空步骤 + 空答卷轴保持
    plan = {"pools": {"CCO": []}}
    runs_root2 = tmp_path / "runs2"
    out2 = start_run(
        config=resolve_config(), runs_root=runs_root2, run_id="c04e",
        smiles="CCO", max_depth=3, max_expansions=10, max_frontier_width=2,
        finder=object(), scripted=True, profile=PROFILE_POLLUTANT_PATHWAY_V1,
        ppv1_plan=plan,
        profile_policy={"search_limits": {
            "max_retrievals_per_parent": 2}})
    assert out2["counts"]["events"] == 0
    empty = read_v3_projection(
        runs_root2 / "c04e", out2["v3_projection"]["projection_digest"])
    assert empty["route"]["steps"] == []
    axes2 = {loss["axis"] for loss in empty["information_losses"]}
    assert "no_committed_events_empty_answer" in axes2
