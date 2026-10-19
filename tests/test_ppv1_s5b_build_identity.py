"""PPV1 S5b T-E/E1a —— build_identity 首消费绑定测试族
(s5b-build-identity-1;零网络、零金标、合成夹具)。

依据:设计稿 v2 §3.6 + Codex 二轮复审 §4.1(最终口径)。断言族:

- 指纹口径:排除清单仅顶层 3 项(自身哈希键 + created_at +
  display_note);实际身份事实(版本/参数/RDKit/逐输入 sha)不得排除;
- 批构建:旁块写入批根(唯一权威)+ manifest 只放引用/摘要;
  逐 qid 输入原始字节 sha;
- 首消费四拒例:missing / corrupt / version / content mismatch;
- 输入字节不匹配拒(run_inputs 文件被改 ⇒ run_input_bytes_mismatch);
- 来源持久化:唯一不可覆盖(O_EXCL)/首启 persisted_new / 重复核
  一致 verified_existing / 恢复缺 ⇒ 拒并保全原记录 / 坏 ⇒ 拒 /
  不符 ⇒ 拒(原记录不被覆盖)/ 落盘失败 ⇒ 拒(write_failed);
- legacy 旧批(无旁块)⇒ 显式 legacy 模式披露(不冒充受控批)。
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pathway_v43.storage.build_identity import (  # noqa: E402
    BUILD_IDENTITY_FILE,
    BUILD_IDENTITY_SCHEMA_VERSION,
    BuildIdentityError,
    build_identity_fingerprint,
    load_build_identity,
    prepare_build_origin,
    verify_batch_build_identity,
    write_batch_build_identity,
)


def _mini_batch(tmp_path: Path, qid: str = "q1",
                run_id: str = "b1-abc") -> Path:
    """合成受控批:run_inputs + manifest(build_identity_ref)+ 旁块。"""
    root = tmp_path / "batch"
    (root / "run_inputs").mkdir(parents=True)
    run_input = {"qid": qid, "run_id": run_id,
                 "substrate_smiles": "CCO", "plan": {"pools": {}},
                 "note": "synthetic"}
    path = root / "run_inputs" / f"{qid}.json"
    path.write_text(json.dumps(run_input, sort_keys=True) + "\n",
                    encoding="utf-8")
    payload = write_batch_build_identity(
        root, run_input_paths={qid: (run_id, path)})
    (root / "batch_manifest.json").write_text(json.dumps({
        "batch_tag": "b1", "provider_kind": "scripted",
        "entries": [{"qid": qid, "run_id": run_id}],
        "build_identity_ref": {
            "file": BUILD_IDENTITY_FILE,
            "build_identity_fingerprint":
                payload["build_identity_fingerprint"]},
    }, sort_keys=True), encoding="utf-8")
    return root


def _facts() -> dict:
    from pathway_v43.storage.build_identity import (
        current_build_identity_facts,
    )
    return current_build_identity_facts()


def _read_input(root: Path, qid: str = "q1") -> bytes:
    return (root / "run_inputs" / f"{qid}.json").read_bytes()


def _rewrite_block(root: Path, mutate) -> dict:
    path = root / BUILD_IDENTITY_FILE
    payload = json.loads(path.read_text(encoding="utf-8"))
    mutate(payload)
    payload["build_identity_fingerprint"] = build_identity_fingerprint(
        payload)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return payload


# ================================================================ 指纹口径


def test_fingerprint_exclusions_are_exactly_three() -> None:
    base = {"a": 1, "run_inputs": [{"qid": "q1",
                                    "run_input_sha256": "0" * 64}]}
    assert build_identity_fingerprint(base) == build_identity_fingerprint(
        {**base, "created_at": "2026-01-01", "display_note": "x",
         "build_identity_fingerprint": "ff"})
    # 实际身份事实不得排除
    assert build_identity_fingerprint(base) != build_identity_fingerprint(
        {**base, "rdkit_version": "2099.01.1"})
    assert build_identity_fingerprint(base) != build_identity_fingerprint(
        {**base, "run_inputs": [{"qid": "q1",
                                 "run_input_sha256": "1" * 64}]})
    assert build_identity_fingerprint(base) != build_identity_fingerprint(
        {**base, "pool_policy_version": "s5b-pool-policy-99"})


def test_batch_block_written_and_manifest_reference(tmp_path) -> None:
    from pathway_v43.storage.build_identity import (
        FINGERPRINT_EXCLUSIONS,
    )
    root = _mini_batch(tmp_path)
    payload = load_build_identity(root)
    assert FINGERPRINT_EXCLUSIONS == (
        "build_identity_fingerprint", "created_at", "display_note")
    schema = payload["schema"]
    assert schema["schema_version"] == BUILD_IDENTITY_SCHEMA_VERSION
    assert set(schema["fingerprint_exclusions"]) == set(
        FINGERPRINT_EXCLUSIONS)
    # 身份事实在位(代码聚合/版本/指纹/RDKit/资产/逐输入 sha)
    for key in ("code_identity_aggregate_sha256", "pool_policy_version",
                "recorded_source_version", "corpus_retrieval_version",
                "formnorm_version", "formnorm_param_sha256",
                "route_version", "compiler_version", "rdkit_version",
                "asset_identity", "run_inputs"):
        assert key in payload, key
    entry = payload["run_inputs"][0]
    assert entry["qid"] == "q1" and entry["run_id"] == "b1-abc"
    assert entry["run_input_sha256"] == hashlib.sha256(
        _read_input(root)).hexdigest()
    manifest = json.loads(
        (root / "batch_manifest.json").read_text(encoding="utf-8"))
    ref = manifest["build_identity_ref"]
    assert ref["file"] == BUILD_IDENTITY_FILE
    assert ref["build_identity_fingerprint"] == payload[
        "build_identity_fingerprint"]


# ================================================================ 四拒例


def test_verify_pass_and_legacy_mode(tmp_path) -> None:
    root = _mini_batch(tmp_path)
    out = verify_batch_build_identity(
        batch_root=root, qid="q1", run_id="b1-abc",
        run_input_bytes=_read_input(root))
    assert out["mode"] == "verified"
    assert out["build_identity_fingerprint"] == load_build_identity(
        root)["build_identity_fingerprint"]
    # legacy:无旁块且 manifest 未声明引用 ⇒ 显式披露(不冒充受控批)
    legacy = tmp_path / "legacy"
    (legacy / "run_inputs").mkdir(parents=True)
    (legacy / "run_inputs" / "q1.json").write_bytes(_read_input(root))
    (legacy / "batch_manifest.json").write_text(json.dumps({
        "batch_tag": "old", "entries": [{"qid": "q1"}]}),
        encoding="utf-8")
    out2 = verify_batch_build_identity(
        batch_root=legacy, qid="q1", run_id="b1-abc",
        run_input_bytes=_read_input(root))
    assert out2["mode"] == "legacy_absent_disclosed"


def test_verify_missing_block_refused(tmp_path) -> None:
    root = _mini_batch(tmp_path)
    (root / BUILD_IDENTITY_FILE).unlink()
    with pytest.raises(BuildIdentityError) as ei:
        verify_batch_build_identity(
            batch_root=root, qid="q1", run_id="b1-abc",
            run_input_bytes=_read_input(root))
    assert ei.value.failure_kind == "build_identity_invalid"
    assert ei.value.detail["kind"] == "missing"


def test_verify_corrupt_block_refused(tmp_path) -> None:
    root = _mini_batch(tmp_path)
    (root / BUILD_IDENTITY_FILE).write_text("{not json", encoding="utf-8")
    with pytest.raises(BuildIdentityError) as ei:
        verify_batch_build_identity(
            batch_root=root, qid="q1", run_id="b1-abc",
            run_input_bytes=_read_input(root))
    assert ei.value.detail["kind"] == "corrupt"
    # 指纹重算不符(内容被改而未同步哈希)⇒ corrupt
    root2 = _mini_batch(tmp_path / "r2")
    block = json.loads((root2 / BUILD_IDENTITY_FILE).read_text())
    block["pool_policy_version"] = "tampered"
    (root2 / BUILD_IDENTITY_FILE).write_text(
        json.dumps(block), encoding="utf-8")
    with pytest.raises(BuildIdentityError) as ei2:
        verify_batch_build_identity(
            batch_root=root2, qid="q1", run_id="b1-abc",
            run_input_bytes=_read_input(root2))
    assert ei2.value.detail["kind"] == "corrupt"
    assert ei2.value.detail["detail"] == "fingerprint_recompute_mismatch"


def test_verify_version_mismatch_refused(tmp_path) -> None:
    root = _mini_batch(tmp_path)
    _rewrite_block(root, lambda p: p["schema"].__setitem__(
        "schema_version", "s5b-build-identity-999"))
    with pytest.raises(BuildIdentityError) as ei:
        verify_batch_build_identity(
            batch_root=root, qid="q1", run_id="b1-abc",
            run_input_bytes=_read_input(root))
    assert ei.value.detail["kind"] == "version"


def test_verify_content_mismatch_refused(tmp_path) -> None:
    """内容不符(指纹同步重算后仍拒;字段清单机读)。"""
    root = _mini_batch(tmp_path)
    _rewrite_block(root, lambda p: p.__setitem__(
        "record_side_form_norm_version"
        if "record_side_form_norm_version" in p else "formnorm_version",
        "record-side-formnorm-999"))
    with pytest.raises(BuildIdentityError) as ei:
        verify_batch_build_identity(
            batch_root=root, qid="q1", run_id="b1-abc",
            run_input_bytes=_read_input(root))
    assert ei.value.failure_kind == "build_identity_invalid"
    assert ei.value.detail["kind"] == "content_mismatch"
    assert "formnorm_version" in ei.value.detail["fields"]


def test_verify_run_input_bytes_mismatch_refused(tmp_path) -> None:
    root = _mini_batch(tmp_path)
    path = root / "run_inputs" / "q1.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["note"] = "tampered bytes"
    path.write_text(json.dumps(data, sort_keys=True) + "\n",
                    encoding="utf-8")
    with pytest.raises(BuildIdentityError) as ei:
        verify_batch_build_identity(
            batch_root=root, qid="q1", run_id="b1-abc",
            run_input_bytes=_read_input(root))
    assert ei.value.failure_kind == "run_input_bytes_mismatch"
    assert ei.value.detail["kind"] == "sha256_mismatch"
    # 缺条目/run_id 不符同面拒
    with pytest.raises(BuildIdentityError) as ei2:
        verify_batch_build_identity(
            batch_root=root, qid="q-missing", run_id="b1-abc",
            run_input_bytes=b"{}")
    assert ei2.value.detail["kind"] == "missing_entry"


# ================================================================ 来源持久化


def test_origin_persist_unique_and_verify(tmp_path) -> None:
    root = _mini_batch(tmp_path)
    verified = verify_batch_build_identity(
        batch_root=root, qid="q1", run_id="b1-abc",
        run_input_bytes=_read_input(root))
    out = prepare_build_origin(batch_root=root, qid="q1",
                               run_id="b1-abc", verified=verified,
                               resume=False)
    assert out["mode"] == "persisted_new"
    ledger = root / "build_origin" / "q1.json"
    assert ledger.is_file()
    saved = json.loads(ledger.read_text(encoding="utf-8"))
    assert saved["build_identity_fingerprint"] == verified[
        "build_identity_fingerprint"]
    assert saved["run_input_sha256"] == verified["run_input_sha256"]
    # 重复(首启重试/并发)⇒ 核一致 verified_existing,原记录不改
    before = ledger.read_bytes()
    out2 = prepare_build_origin(batch_root=root, qid="q1",
                                run_id="b1-abc", verified=verified,
                                resume=False)
    assert out2["mode"] == "verified_existing"
    assert ledger.read_bytes() == before
    # 恢复路径同核 ⇒ verified_existing
    out3 = prepare_build_origin(batch_root=root, qid="q1",
                                run_id="b1-abc", verified=verified,
                                resume=True)
    assert out3["mode"] == "verified_existing"


def test_origin_resume_missing_refused_and_not_written(tmp_path) -> None:
    root = _mini_batch(tmp_path)
    verified = verify_batch_build_identity(
        batch_root=root, qid="q1", run_id="b1-abc",
        run_input_bytes=_read_input(root))
    with pytest.raises(BuildIdentityError) as ei:
        prepare_build_origin(batch_root=root, qid="q1", run_id="b1-abc",
                             verified=verified, resume=True)
    assert ei.value.failure_kind == "run_build_origin_mismatch"
    assert ei.value.detail["kind"] == "missing"
    assert not (root / "build_origin" / "q1.json").exists()


def test_origin_corrupt_and_mismatch_refused_preserving(tmp_path) -> None:
    root = _mini_batch(tmp_path)
    verified = verify_batch_build_identity(
        batch_root=root, qid="q1", run_id="b1-abc",
        run_input_bytes=_read_input(root))
    ledger = root / "build_origin" / "q1.json"
    ledger.parent.mkdir(parents=True, exist_ok=True)
    ledger.write_text("{bad json", encoding="utf-8")
    with pytest.raises(BuildIdentityError) as ei:
        prepare_build_origin(batch_root=root, qid="q1", run_id="b1-abc",
                             verified=verified, resume=True)
    assert ei.value.detail["kind"] == "corrupt"
    assert ledger.read_text(encoding="utf-8") == "{bad json"  # 保全原记录
    ledger.write_text(json.dumps({
        "schema": "s5b-build-origin-1", "qid": "q1",
        "run_id": "b1-abc",
        "build_identity_fingerprint": "0" * 64,
        "run_input_sha256": "1" * 64}), encoding="utf-8")
    before = ledger.read_bytes()
    with pytest.raises(BuildIdentityError) as ei2:
        prepare_build_origin(batch_root=root, qid="q1", run_id="b1-abc",
                             verified=verified, resume=True)
    assert ei2.value.detail["kind"] == "mismatch"
    assert ledger.read_bytes() == before  # 不被覆盖、不补造旧出处


def test_origin_write_failed_refused(tmp_path) -> None:
    """来源落盘失败 ⇒ 拒(write_failed;不得继续调用)。"""
    root = _mini_batch(tmp_path)
    verified = verify_batch_build_identity(
        batch_root=root, qid="q1", run_id="b1-abc",
        run_input_bytes=_read_input(root))
    (root / "build_origin").write_text("i am a file",
                                       encoding="utf-8")
    with pytest.raises(BuildIdentityError) as ei:
        prepare_build_origin(batch_root=root, qid="q1", run_id="b1-abc",
                             verified=verified, resume=False)
    assert ei.value.failure_kind == "run_build_origin_mismatch"
    assert ei.value.detail["kind"] == "write_failed"


def test_origin_legacy_mode_writes_nothing(tmp_path) -> None:
    legacy = tmp_path / "legacy"
    legacy.mkdir()
    out = prepare_build_origin(
        batch_root=legacy, qid="q1", run_id="r1",
        verified={"mode": "legacy_absent_disclosed"}, resume=False)
    assert out["mode"] == "legacy_absent_disclosed"
    assert not (legacy / "build_origin").exists()


# ================================================================ worker 端到端


def _scripted_batch(tmp_path: Path, tag: str) -> Path:
    """合成 scripted 批(chain14 harness 同款;零网络)。"""
    import os

    from pathway_v43.pollutant.s5b_builder import build_question_batch
    from pathway_v43.pollutant.s5b_orchestrator import (
        S5B_DEFAULT_PROFILE_POLICY,
    )

    questions = tmp_path / f"q-{tag}.jsonl"
    questions.write_text(json.dumps(
        {"qid": f"SYNTH-BI-{tag}", "substrate_smiles": "CCO",
         "products_smiles": ["CC=O"], "raw_reaction": "CCO>>CC=O"}) + "\n",
        encoding="utf-8")
    batch_root = tmp_path / f"batch-{tag}"
    build_question_batch(
        questions, batch_root, batch_tag=f"bi-{tag}",
        pool_provider=lambda s: [], provider_kind="scripted",
        synthetic_review=True)
    (batch_root / "profile_policy.json").write_text(
        json.dumps(S5B_DEFAULT_PROFILE_POLICY), encoding="utf-8")
    return batch_root


def _stub_env(tmp_path: Path, monkeypatch) -> None:
    stub_path = tmp_path / "stub.json"
    stub_path.write_text(json.dumps({"strategy": "first_pool"}),
                         encoding="utf-8")
    monkeypatch.setenv("S5B_MODEL_STUB_SCRIPT", str(stub_path))


def test_worker_refuses_missing_block_no_run(tmp_path, monkeypatch) -> None:
    """首启核对失败不建 run:旁块缺失(manifest 声明引用)⇒ 失败 case,
    零发送、runs_root 无该 run 目录。"""
    from pathway_v43.pollutant.s5b_worker import worker_main

    _stub_env(tmp_path, monkeypatch)
    qid = "SYNTH-BI-missing"
    batch_root = _scripted_batch(tmp_path, "missing")
    (batch_root / BUILD_IDENTITY_FILE).unlink()
    runs_root = tmp_path / "runs-missing"
    rc = worker_main(["--batch-root", str(batch_root),
                      "--runs-root", str(runs_root), "--qid", qid])
    assert rc == 5
    case = json.loads(
        (batch_root / "cases" / f"{qid}.json").read_text(encoding="utf-8"))
    assert case["status"] == "failed"
    assert case["failure_kind"] == "build_identity_invalid"
    assert case["detail"]["kind"] == "missing"
    assert list(runs_root.glob("*")) == []
    assert case["model_calls"] == 0 if "model_calls" in case else True


def test_worker_refuses_tampered_input_bytes(tmp_path, monkeypatch) -> None:
    from pathway_v43.pollutant.s5b_worker import worker_main

    _stub_env(tmp_path, monkeypatch)
    qid = "SYNTH-BI-bytes"
    batch_root = _scripted_batch(tmp_path, "bytes")
    path = batch_root / "run_inputs" / f"{qid}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["note"] = "tampered"
    path.write_text(json.dumps(data, sort_keys=True) + "\n",
                    encoding="utf-8")
    runs_root = tmp_path / "runs-bytes"
    rc = worker_main(["--batch-root", str(batch_root),
                      "--runs-root", str(runs_root), "--qid", qid])
    assert rc == 5
    case = json.loads(
        (batch_root / "cases" / f"{qid}.json").read_text(encoding="utf-8"))
    assert case["failure_kind"] == "run_input_bytes_mismatch"
    assert case["detail"]["kind"] == "sha256_mismatch"
    assert list(runs_root.glob("*")) == []


def test_worker_success_persists_origin_and_case_summary(
        tmp_path, monkeypatch) -> None:
    """首启通过 ⇒ run 创建 + 来源 ledger 持久化(唯一不可覆盖)+
    case 只作摘要;再跑(恢复)⇒ 同核 verified_existing 并正常续跑。"""
    from pathway_v43.pollutant.s5b_worker import worker_main

    _stub_env(tmp_path, monkeypatch)
    qid = "SYNTH-BI-ok"
    batch_root = _scripted_batch(tmp_path, "ok")
    runs_root = tmp_path / "runs-ok"
    rc = worker_main(["--batch-root", str(batch_root),
                      "--runs-root", str(runs_root), "--qid", qid])
    assert rc == 0
    case = json.loads(
        (batch_root / "cases" / f"{qid}.json").read_text(encoding="utf-8"))
    assert case["status"] == "completed"
    assert case["build_identity_mode"] == "verified"
    assert case["build_origin_mode"] == "persisted_new"
    assert len(case["build_identity_fingerprint"]) == 64
    ledger = batch_root / "build_origin" / f"{qid}.json"
    assert ledger.is_file()
    saved = json.loads(ledger.read_text(encoding="utf-8"))
    assert saved["build_identity_fingerprint"] == case[
        "build_identity_fingerprint"]
    before = ledger.read_bytes()
    # 恢复:同核 + 原记录不被改写
    rc2 = worker_main(["--batch-root", str(batch_root),
                       "--runs-root", str(runs_root), "--qid", qid])
    assert rc2 == 0
    case2 = json.loads(
        (batch_root / "cases" / f"{qid}.json").read_text(encoding="utf-8"))
    assert case2["build_origin_mode"] == "verified_existing"
    assert ledger.read_bytes() == before


def test_worker_resume_missing_origin_refused_run_preserved(
        tmp_path, monkeypatch) -> None:
    """恢复失败不改既存 run:ledger 缺失 ⇒ 拒绝;run_identity.json
    原样保全。"""
    from pathway_v43.pollutant.s5b_worker import worker_main

    _stub_env(tmp_path, monkeypatch)
    qid = "SYNTH-BI-rsm"
    batch_root = _scripted_batch(tmp_path, "rsm")
    runs_root = tmp_path / "runs-rsm"
    assert worker_main(["--batch-root", str(batch_root),
                        "--runs-root", str(runs_root),
                        "--qid", qid]) == 0
    run_id = json.loads(
        (batch_root / "run_inputs" / f"{qid}.json").read_text(
            encoding="utf-8"))["run_id"]
    identity_path = runs_root / run_id / "run_identity.json"
    before = identity_path.read_bytes()
    (batch_root / "build_origin" / f"{qid}.json").unlink()
    rc = worker_main(["--batch-root", str(batch_root),
                      "--runs-root", str(runs_root), "--qid", qid])
    assert rc == 5
    case = json.loads(
        (batch_root / "cases" / f"{qid}.json").read_text(encoding="utf-8"))
    assert case["failure_kind"] == "run_build_origin_mismatch"
    assert case["detail"]["kind"] == "missing"
    assert identity_path.read_bytes() == before  # 既存 run 零改写