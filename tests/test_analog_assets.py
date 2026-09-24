"""类比索引适配器:两份索引齐备、行数与 SHA 与 v4 原版一致、缺一即 fail-closed。"""

from __future__ import annotations

import pytest

from conftest import ANALOG_INDEX_FOR_DELETE

from pathway_v43.adapters.analog_index import AnalogAssetError, AnalogAssets
from pathway_v43.config import resolve_config

# 行数钉死(资产受本仓清单保护,漂移即失败);与 v4 原版装载口径一致。
EXPECTED_USPTO_ROWS = 188_725
EXPECTED_CORPUS_ROWS = 17_183


def test_both_indexes_load_with_pinned_rows(assets_root, manifest_identity):
    assets = AnalogAssets(assets_root, manifest_identity=manifest_identity)
    assert assets.available
    assert len(assets.uspto.rows) == EXPECTED_USPTO_ROWS
    assert len(assets.corpus.rows) == EXPECTED_CORPUS_ROWS
    assert assets.uspto.n_bad_forms == 0
    status = assets.status()
    assert status["available"] and status["enabled"]
    assert status["uspto_index"]["rows"] == EXPECTED_USPTO_ROWS
    assert status["corpus_index"]["rows"] == EXPECTED_CORPUS_ROWS


def test_index_sha_matches_repo_manifest(assets_root, manifest_identity):
    assets = AnalogAssets(assets_root, manifest_identity=manifest_identity)
    files = manifest_identity["files"]
    assert assets.uspto.sha256 == files["analog/uspto_relaxed_index_v1.jsonl"]
    assert assets.corpus.sha256 == files["analog/corpus_templates_v1.jsonl"]


def test_paths_under_analog_root(assets_root, manifest_identity):
    assets = AnalogAssets(assets_root, manifest_identity=manifest_identity)
    analog_root = resolve_config(None, str(assets_root)).analog_root.resolve()
    for path in (assets.uspto.path.resolve(), assets.corpus.path.resolve()):
        assert analog_root in path.parents


def test_missing_index_fails_when_enabled(assets_root, make_assets_copy,
                                          manifest_identity):
    """启用类比桥时缺任一索引 → fail-closed(v4 旧版缺一份仍可用的行为被收紧)。

    传入真实 manifest_identity 以隔离“清单校验先行失败”路径,专测装载器
    自身的齐备性守卫。
    """
    copy = make_assets_copy(drop=ANALOG_INDEX_FOR_DELETE)
    with pytest.raises(AnalogAssetError) as ei:
        AnalogAssets(copy, require_complete=True,
                     manifest_identity=manifest_identity)
    assert ANALOG_INDEX_FOR_DELETE in str(ei.value)


def test_missing_index_reported_honestly_when_not_required(
    assets_root, make_assets_copy, manifest_identity
):
    """require_complete=False(仅报告模式):缺索引如实落 None,不臆造可用。

    用真实 manifest_identity 模拟“清单曾校验通过、随后文件消失”的运行态:
    不重新做磁盘清单校验,装载器自身仍要如实报告不可用。
    """
    copy = make_assets_copy(drop=ANALOG_INDEX_FOR_DELETE)
    assets = AnalogAssets(copy, require_complete=False,
                          manifest_identity=manifest_identity)
    assert not assets.available
    assert assets.uspto is None or assets.corpus is None
    assert assets.status()["available"] is False
    status = assets.status()
    missing_block = status["uspto_index"]
    other_block = status["corpus_index"]
    unavailable = [b for b in (missing_block, other_block)
                   if b["available"] is False]
    assert len(unavailable) == 1
    assert ANALOG_INDEX_FOR_DELETE in unavailable[0]["path"]


def test_analog_symlink_escape_rejected(assets_root, make_assets_copy,
                                        manifest_identity):
    """类比索引的 symlink 指向本仓 assets 根之外(物理路径在仓外)→ 拒绝。

    纯 symlink 镜像副本:文件字节与正本一致(哈希校验可通过),但解析后的
    物理读取路径不在副本 assets 根内,装载器必须以“路径逃逸”fail-closed。
    """
    copy = make_assets_copy(symlink_all=True)
    with pytest.raises(AnalogAssetError) as ei:
        AnalogAssets(copy, require_complete=True,
                     manifest_identity=manifest_identity)
    assert "逃逸" in str(ei.value)
    assert ei.value.detail.get("physical")


def test_row_counts_match_v4_parser(assets_root, manifest_identity, v4_code_root):
    """与 v4 原版 UsptoIndex/CorpusIndex 对同一文件逐项一致(行数 + SHA)。"""
    import sys

    v4_src = str(v4_code_root / "src")
    if v4_src not in sys.path:
        sys.path.insert(0, v4_src)
    from pathway_agent.analog import CorpusIndex, UsptoIndex  # type: ignore

    assets = AnalogAssets(assets_root, manifest_identity=manifest_identity)
    u4 = UsptoIndex(assets.uspto.path)
    c4 = CorpusIndex(assets.corpus.path)
    assert len(u4.rows) == len(assets.uspto.rows)
    assert u4.sha256 == assets.uspto.sha256
    assert u4.n_bad_forms == assets.uspto.n_bad_forms
    assert len(c4.rows) == len(assets.corpus.rows)
    assert c4.sha256 == assets.corpus.sha256
