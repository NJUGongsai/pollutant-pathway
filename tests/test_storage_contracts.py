"""ArtifactStore 原子写/幂等/冲突 与 run_identity resume 核对。"""

from __future__ import annotations

import pytest

from pathway_v43.config import resolve_config
from pathway_v43.storage.artifact_store import (
    ArtifactConflict,
    ArtifactIntegrityError,
    ArtifactStore,
)
from pathway_v43.storage.run_identity import (
    IdentityMismatch,
    build_run_identity,
    check_resume_identity,
    identity_fingerprint,
    retrieval_asset_identity,
    scripted_asset_identity,
)


def test_artifact_write_read_idempotent_conflict(tmp_path):
    st = ArtifactStore(tmp_path, "r1")
    env1 = st.write("T1", "retrieval", {"k": 1, "list": [1, 2]})
    assert env1["created"] is True
    # 同键同内容:幂等返回,不新建
    env2 = st.write("T1", "retrieval", {"list": [1, 2], "k": 1})
    assert env2["created"] is False
    assert st.read("T1", "retrieval")["payload"]["k"] == 1
    # 同键不同内容:冲突,不覆盖
    with pytest.raises(ArtifactConflict):
        st.write("T1", "retrieval", {"k": 2})
    # 无 .tmp 残留
    leftovers = list((tmp_path / "r1" / "results").rglob("*.tmp"))
    assert leftovers == []


def test_artifact_read_detects_tampering(tmp_path):
    """P2 修复回归:payload 被篡改后读取必须 fail-closed,不返回脏数据。"""
    import json

    st = ArtifactStore(tmp_path, "r1")
    st.write("T1", "retrieval", {"k": 1})
    path = tmp_path / "r1" / "results" / "T1" / "retrieval.json"
    envelope = json.loads(path.read_text())
    envelope["payload"]["k"] = 999  # 篡改内容,哈希不再匹配
    path.write_text(json.dumps(envelope), encoding="utf-8")
    with pytest.raises(ArtifactIntegrityError):
        st.read("T1", "retrieval")


def test_artifact_concurrent_write_no_overwrite(tmp_path):
    """P2 修复回归:os.link 原子占位 —— 已有产物永不被并发写入覆盖。"""
    import json

    st = ArtifactStore(tmp_path, "r1")
    st.write("T1", "retrieval", {"k": "first"})
    # 绕过存在性检查直接模拟并发占位:link 到已存在目标必须失败
    path = tmp_path / "r1" / "results" / "T1" / "retrieval.json"
    import os

    tmp = path.with_name("retrieval.race.tmp")
    tmp.write_text("{}\n", encoding="utf-8")
    try:
        os.link(tmp, path)
        raise AssertionError("link 到已存在产物应当失败")
    except FileExistsError:
        pass
    finally:
        tmp.unlink(missing_ok=True)
    # 原产物未被触碰
    assert st.read("T1", "retrieval")["payload"] == {"k": "first"}


def test_retrieval_asset_identity_real_and_scripted():
    real = retrieval_asset_identity(resolve_config())
    assert real["mode"] == "repo_assets"
    assert real["n_manifest_files"] == 22   # Phase D D2 起 +corpus_templates_v2
    assert real["analog_corpus"] == "v1"     # 默认装载 v1(显式选择进身份)
    assert real["analog_corpus_file"] == \
        "analog/corpus_templates_v1.jsonl"
    # v35 资产集的实际环境 lookup 库(v3 identity block "library")
    assert real["source_file"] == "v3_reactions/library/library_full.jsonl"
    assert real["source_file_sha256"] == \
        "042e9e2c2afccdd83088eb0b50d75619261fb096728a17ab108da06cb54667f3"
    scripted = scripted_asset_identity()
    assert scripted["mode"] == "scripted_fixture"


def _make_identity(strategy=None, asset=None):
    return build_run_identity(
        run_id="r1", root_smiles="Oc1ccccc1O", root_cn="Oc1ccccc1O",
        strategy=strategy or {"version": "v43-policy-1", "max_depth": 2,
                              "max_expansions": 3, "max_frontier_width": 1},
        asset_identity=asset or scripted_asset_identity(),
        v3_code_identity={"git_commit": "x"},
    )


def test_resume_identity_accepts_same():
    saved = _make_identity()
    check_resume_identity(saved, _make_identity())  # 不抛即通过


def test_resume_identity_rejects_strategy_change():
    saved = _make_identity()
    current = _make_identity(
        strategy={"version": "v43-policy-1", "max_depth": 9,
                  "max_expansions": 3, "max_frontier_width": 1})
    with pytest.raises(IdentityMismatch) as ei:
        check_resume_identity(saved, current)
    assert "strategy" in ei.value.detail["differences"]


def test_resume_identity_rejects_asset_change():
    saved = _make_identity()
    current = _make_identity(asset=retrieval_asset_identity(resolve_config()))
    with pytest.raises(IdentityMismatch):
        check_resume_identity(saved, current)


def test_fingerprint_ignores_created_at():
    a = _make_identity()
    b = _make_identity()
    b["created_at"] = "2099-01-01T00:00:00+00:00"
    assert identity_fingerprint(a) == identity_fingerprint(b)
