"""本仓清单校验:正本 21 文件全过;合成清单的缺失/篡改/JSON 不一致/路径逃逸 fail-closed。

大文件篡改用例不复制真实 assets,而是构造最小合成资产根(2 个文件)来驱动
verify_repo_manifest 的全部失败分支;真实正本只做只读通过性校验。
"""

from __future__ import annotations

import json

import pytest

from pathway_v43.adapters.asset_manifest import (
    ANALOG_INDEX_FILES,
    EXTENSION_FILES,
    AssetManifestError,
    analog_index_shas,
    extension_file_shas,
    verify_repo_manifest,
)


def _write_mini_assets(root, *, entries, json_meta=None,
                       drop_sha_entry=None, bytes_lie=None, escape=None,
                       json_omit=None):
    """root 下造数据文件 + MANIFEST.sha256 + MANIFEST.json。

    escape:    仅写入 SHA 清单的非法条目(词法逃逸用例,不进 JSON meta);
    json_omit: 从 JSON meta 中省略的文件(缺条目用例,保留正确哈希)。
    """
    import hashlib

    root.mkdir(parents=True, exist_ok=True)
    files = {}
    for rel, payload in entries.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(payload)
        files[rel] = hashlib.sha256(payload).hexdigest()
    if escape:
        files[escape] = "0" * 64
    sha_lines = "".join(f"{h}  {rel}\n" for rel, h in files.items()
                        if rel != drop_sha_entry)
    (root / "MANIFEST.sha256").write_text(sha_lines, encoding="utf-8")
    meta_entries = [
        {"path": rel, "bytes": len(entries[rel]), "sha256": h}
        for rel, h in files.items()
        if rel in entries and rel != drop_sha_entry
        and not (json_omit and rel in json_omit)
    ]
    meta = json_meta or {
        "schema_version": 1,
        "asset_count": len(files) - (1 if drop_sha_entry else 0),
        "total_bytes": sum(len(v) for v in entries.values()),
        "entries": meta_entries,
    }
    if bytes_lie:
        for e in meta["entries"]:
            if e["path"] == bytes_lie:
                e["bytes"] = e["bytes"] + 1
    (root / "MANIFEST.json").write_text(
        json.dumps(meta), encoding="utf-8")
    return root


def test_repo_manifest_passes_real_assets(manifest_identity):
    assert manifest_identity["n_files"] == 22
    assert manifest_identity["total_bytes"] == 166_849_006  # Phase D D2 起 +corpus_templates_v2
    assert len(manifest_identity["files"]) == 22
    assert all(len(h) == 64 for h in manifest_identity["files"].values())


def test_extension_and_analog_files_listed(manifest_identity):
    ext = extension_file_shas(manifest_identity)
    ana = analog_index_shas(manifest_identity)
    assert set(ext) == set(EXTENSION_FILES)
    assert set(ana) == set(ANALOG_INDEX_FILES)
    assert set(ext) | set(ana) <= set(manifest_identity["files"])


def test_missing_file_named(tmp_path):
    root = _write_mini_assets(
        tmp_path / "a",
        entries={"x/data.txt": b"hello", "y/other.txt": b"world"},
    )
    (root / "x" / "data.txt").unlink()
    with pytest.raises(AssetManifestError) as ei:
        verify_repo_manifest(root)
    assert "x/data.txt" in str(ei.value)
    assert ei.value.detail.get("file") == "x/data.txt"


def test_tampered_file_hash_named(tmp_path):
    root = _write_mini_assets(
        tmp_path / "a",
        entries={"x/data.txt": b"hello", "y/other.txt": b"world"},
    )
    (root / "y" / "other.txt").write_bytes(b"w0rld")
    with pytest.raises(AssetManifestError) as ei:
        verify_repo_manifest(root)
    assert "y/other.txt" in str(ei.value)
    assert ei.value.detail.get("file") == "y/other.txt"


def test_manifest_json_bytes_mismatch(tmp_path):
    root = _write_mini_assets(
        tmp_path / "a",
        entries={"x/data.txt": b"hello", "y/other.txt": b"world"},
        bytes_lie="x/data.txt",
    )
    with pytest.raises(AssetManifestError) as ei:
        verify_repo_manifest(root)
    assert "x/data.txt" in str(ei.value)


def test_manifest_json_missing_entry(tmp_path):
    root = _write_mini_assets(
        tmp_path / "a",
        entries={"x/data.txt": b"hello", "y/other.txt": b"world"},
        json_omit={"y/other.txt"},
    )
    with pytest.raises(AssetManifestError) as ei:
        verify_repo_manifest(root)
    assert "y/other.txt" in str(ei.value)


def test_path_escape_rejected(tmp_path):
    root = _write_mini_assets(
        tmp_path / "a",
        entries={"x/data.txt": b"hello"},
        escape="../evil.txt",
    )
    with pytest.raises(AssetManifestError) as ei:
        verify_repo_manifest(root)
    assert "逃逸" in str(ei.value)


def test_no_fallback_to_v3_assets(tmp_path, v3_code_root):
    """空 assets 根必须失败;原 v3/assets 即使完好也不得兜底。"""
    empty = tmp_path / "empty_assets"
    empty.mkdir()
    assert (v3_code_root / "assets" / "MANIFEST.sha256").is_file()
    with pytest.raises(AssetManifestError):
        verify_repo_manifest(empty)
