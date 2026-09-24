"""CLI fail-closed 行为:任何失败都必须输出结构化 JSON 并以非零码退出,无 traceback。

(回归:__main__.py 曾误用 sys.environ 导致失败路径自身抛 AttributeError;
本组测试以子进程复现“缺资产根/缺 v3 代码根”场景钉死该契约。)
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from conftest import REPO_ROOT


def _run_cli(*args: str) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO_ROOT / "src")
    env.pop("PATHWAY_V43_DEBUG", None)
    return subprocess.run(
        [sys.executable, "-m", "pathway_v43", *args],
        capture_output=True, text=True, timeout=300, env=env,
    )


def _assert_structured_failure(proc: subprocess.CompletedProcess):
    assert proc.returncode == 2, proc.stdout + proc.stderr
    assert "Traceback" not in proc.stdout and "Traceback" not in proc.stderr, (
        proc.stdout + proc.stderr
    )
    payload = json.loads(proc.stdout)
    assert payload["ok"] is False
    assert payload["error"]["type"]
    assert payload["error"]["message"]
    return payload


def test_checkenv_missing_assets_root_structured_failure(tmp_path):
    proc = _run_cli("checkenv", "--assets-root", str(tmp_path / "nope"))
    payload = _assert_structured_failure(proc)
    assert payload["error"]["type"] == "AssetManifestError"
    assert "nope" in payload["error"]["message"]


def test_checkenv_missing_v3_code_root_structured_failure(assets_root):
    proc = _run_cli("checkenv", "--assets-root", str(assets_root),
                    "--v3-code-root", "/nonexistent_v3_root")
    payload = _assert_structured_failure(proc)
    assert payload["error"]["type"] == "FileNotFoundError"


def test_probe_missing_assets_root_fails_fast(assets_root):
    """probe 在坏资产根上不得加载引擎,直接结构化失败。"""
    proc = _run_cli("probe", "--smiles", "Oc1ccccc1O",
                    "--assets-root", "/nonexistent_root_xyz",
                    "--v3-code-root", str(assets_root.parent / "dependingv3"))
    payload = _assert_structured_failure(proc)
    assert payload["command"] == "probe"


def test_checkenv_success_json_contract(assets_root, v3_code_root):
    """成功路径契约:ok=true、清单摘要、核心文件与类比哈希齐备。"""
    proc = _run_cli("checkenv", "--assets-root", str(assets_root),
                    "--v3-code-root", str(v3_code_root))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["ok"] is True
    assert payload["repo_manifest"]["n_files"] == 21
    assert len(payload["v3_run_root"]["core_files"]) == 8
    assert len(payload["analog_index_files"]) == 2
