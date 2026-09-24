"""路径隔离:缺核心文件/改扩展规则/缺类比索引/改索引哈希 → 全部 fail-closed 并点名文件。

四个失败用例只做静态校验(不加载引擎);engine 用例真实加载一次,断言全部
实际装载路径落在本仓 v3_reactions 下、第二套资产身份被进程守卫拒绝、同身份
重复初始化复用同一实例。原 v3/assets 在所有用例中保持完好,失败不得由旧仓
兜底。
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys

import pytest

from conftest import (
    REPO_ROOT,
    ANALOG_INDEX_FOR_DELETE,
    ANALOG_INDEX_FOR_TAMPER,
    CORE_FILE_FOR_TAMPER,
    EXTENSION_FILE_FOR_TAMPER,
)

from pathway_v43.adapters.asset_manifest import AssetManifestError, verify_repo_manifest
from pathway_v43.adapters.analog_index import AnalogAssetError, AnalogAssets
from pathway_v43.config import resolve_config


def _assert_v3_assets_intact(v3_code_root):
    """失败用例的前提:旧 v3/assets 完好存在(证明失败并非资产本就缺失)。"""
    assert (v3_code_root / "assets" / "MANIFEST.sha256").is_file()
    assert (v3_code_root / "assets" / "corpus_env" / "corpus_v1.jsonl").is_file()


def test_missing_core_file_fails(v3_code_root, make_assets_copy):
    _assert_v3_assets_intact(v3_code_root)
    copy = make_assets_copy(drop=CORE_FILE_FOR_TAMPER)
    with pytest.raises(AssetManifestError) as ei:
        verify_repo_manifest(copy)
    assert CORE_FILE_FOR_TAMPER in str(ei.value)


def test_missing_core_file_rejected_by_original_resolver(
    v3_code_root, make_assets_copy
):
    """原版 env_asset_root.resolve_and_verify 显式传被篡改根,也必须失败。"""
    copy = make_assets_copy(drop=CORE_FILE_FOR_TAMPER)
    import sys

    depending = str(v3_code_root / "src" / "depending")
    if depending not in sys.path:
        sys.path.insert(0, depending)
    import env_asset_root as EAR

    with pytest.raises(EAR.EnvAssetError) as ei:
        EAR.resolve_and_verify(str(copy / "v3_reactions"))
    assert "donor_index" in str(ei.value)


def test_tampered_extension_rule_file_fails(v3_code_root, make_assets_copy):
    """扩展规则不在 v3 核心校验范围,只能由本仓总清单抓出。"""
    _assert_v3_assets_intact(v3_code_root)
    copy = make_assets_copy(tamper=EXTENSION_FILE_FOR_TAMPER)
    with pytest.raises(AssetManifestError) as ei:
        verify_repo_manifest(copy)
    assert EXTENSION_FILE_FOR_TAMPER in str(ei.value)


def test_missing_analog_index_fails(v3_code_root, make_assets_copy,
                                    manifest_identity):
    _assert_v3_assets_intact(v3_code_root)
    copy = make_assets_copy(drop=ANALOG_INDEX_FOR_DELETE)
    with pytest.raises(AssetManifestError):
        verify_repo_manifest(copy)
    with pytest.raises(AnalogAssetError) as ei:
        AnalogAssets(copy, require_complete=True,
                     manifest_identity=manifest_identity)
    assert ANALOG_INDEX_FOR_DELETE in str(ei.value)


def test_tampered_analog_index_hash_fails(v3_code_root, make_assets_copy):
    _assert_v3_assets_intact(v3_code_root)
    copy = make_assets_copy(tamper=ANALOG_INDEX_FOR_TAMPER)
    with pytest.raises(AssetManifestError) as ei:
        verify_repo_manifest(copy)
    assert ANALOG_INDEX_FOR_TAMPER in str(ei.value)


def test_v3_reactions_symlink_escape_rejected(v3_code_root, make_assets_copy):
    """回归(P1):把副本的 v3_reactions 整体 symlink 到旧仓 dependingv3/assets。

    字节与清单哈希逐一对得上,但配置 assets 根为物理边界 —— 清单校验必须以
    “文件物理路径逃逸”拒绝,checkenv/引擎入口同样 fail-closed,
    且不得把旧仓文件路径当作核心文件报告。
    """
    _assert_v3_assets_intact(v3_code_root)
    copy = make_assets_copy()  # 全物理复制,仅 v3_reactions 换成指向旧仓的 symlink
    shutil.rmtree(copy / "v3_reactions")
    (copy / "v3_reactions").symlink_to(
        v3_code_root / "assets", target_is_directory=True)

    with pytest.raises(AssetManifestError) as ei:
        verify_repo_manifest(copy)
    assert "逃逸" in str(ei.value)
    assert ei.value.detail.get("physical")
    assert "dependingv3" in str(ei.value.detail["physical"])

    # 引擎入口同样拒绝(get_engine 先做清单校验,不加载引擎)
    from pathway_v43.adapters.v3_engine import get_engine, reset_engine

    config_bad = resolve_config(str(v3_code_root), str(copy))
    with pytest.raises(AssetManifestError):
        get_engine(config_bad)


def test_checkenv_rejects_v3_reactions_symlink_escape(
    v3_code_root, make_assets_copy
):
    """回归(P1,review 复现路径):checkenv 对 symlink 逃逸必须 exit 2 + JSON。"""
    copy = make_assets_copy()  # 全物理复制,仅 v3_reactions 换成指向旧仓的 symlink
    shutil.rmtree(copy / "v3_reactions")
    (copy / "v3_reactions").symlink_to(
        v3_code_root / "assets", target_is_directory=True)
    env = dict(os.environ, PYTHONPATH=str(REPO_ROOT / "src"))
    proc = subprocess.run(
        [sys.executable, "-m", "pathway_v43", "checkenv",
         "--assets-root", str(copy), "--v3-code-root", str(v3_code_root)],
        capture_output=True, text=True, timeout=300, env=env,
    )
    assert proc.returncode == 2, proc.stdout + proc.stderr
    assert "Traceback" not in proc.stdout
    payload = json.loads(proc.stdout)
    assert payload["ok"] is False
    assert "逃逸" in payload["error"]["message"]
    assert "dependingv3" in payload["error"]["message"]


@pytest.mark.slow
def test_engine_load_isolation_and_reinit(assets_root, v3_code_root,
                                          make_assets_copy):
    """实测装载 + 路径断言 + 第二套身份拒绝 + 同身份复用(单次引擎加载)。"""
    from pathway_v43.adapters.v3_engine import (
        EngineBootstrapError,
        get_engine,
        reset_engine,
    )

    config_a = resolve_config(str(v3_code_root), str(assets_root))
    engine = get_engine(config_a)
    try:
        # ---- 1. 实测装载路径全部落在本仓 v3_reactions 下 ----
        X = engine._X
        run_root = config_a.v3_run_root.resolve()
        checked = {
            "templates": X.TEMPLATES,
            "envipath_rules": X.ENVIPATH_RULES,
            "envipath_tsv": X.ENVIPATH_TSV,
            "corpus_dir": X.CORPUS_DIR,
            "model_dir": X.MODEL_DIR,
            "calibrator": X._G_V34_CALIB_PATH,
            "library": engine.identity_block["library_path"],
            "corpus_v1": engine.identity_block["corpus_v1_path"],
        }
        v3_code = config_a.v3_code_root.resolve()
        from pathlib import Path as _P

        for name, path in checked.items():
            p = _P(str(path)).resolve()
            assert run_root in p.parents or p == run_root, f"{name} 越界:{p}"
            assert v3_code not in p.parents, f"{name} 指向 v3 代码仓:{p}"
            assert "dependingv3/assets" not in str(p), f"{name} 指向旧仓 assets:{p}"

        # ---- 2. 第二套资产身份(清单完好但根不同)→ 进程守卫拒绝 ----
        copy = make_assets_copy()  # 纯镜像副本:校验可通过,身份不同
        config_b = resolve_config(str(v3_code_root), str(copy))
        with pytest.raises(EngineBootstrapError) as ei:
            get_engine(config_b)
        assert ei.value.detail.get("bound") is not None

        # ---- 3. 同身份重复初始化:复用同一实例,不串资产 ----
        assert get_engine(config_a) is engine
    finally:
        reset_engine()
