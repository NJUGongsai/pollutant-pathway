"""scripts/ec298_phase_a.py 输入清单与封存校验测试。

覆盖 review R1 P1-3 要求的三类失败:改一个输入字节、新增会被扫描的
结果文件、换资产库;以及"输入未受清单保护"与"清单已存在时禁止覆盖"。
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from pathway_v43.exam_v2 import ScorerV2Error

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "ec298_phase_a.py"
_spec = importlib.util.spec_from_file_location("ec298_phase_a_script",
                                               _SCRIPT)
script = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(script)


def _make_tree(tmp_path):
    run_dir = tmp_path / "runs" / "ec298_v43r1"
    (run_dir / "agent_batch" / "merged").mkdir(parents=True)
    (run_dir / "exam_inputs.jsonl").write_text('{"qid": "Q1"}\n',
                                               encoding="utf-8")
    (run_dir / "agent_batch" / "merged" / "predictions.jsonl").write_text(
        "{}\n", encoding="utf-8")
    gold = tmp_path / "gold.jsonl"
    gold.write_text('{"qid": "Q1"}\n', encoding="utf-8")
    asset = tmp_path / "library.jsonl"
    asset.write_text('{"btid": "bt0001"}\n', encoding="utf-8")
    return run_dir, gold, asset


def test_verify_passes_on_intact_tree(tmp_path):
    run_dir, gold, asset = _make_tree(tmp_path)
    manifest = script.build_input_manifest(run_dir, gold, None, None, asset)
    script.verify_input_manifest(manifest, run_dir, gold, None, None, asset)


def test_verify_fails_on_single_byte_change(tmp_path):
    run_dir, gold, asset = _make_tree(tmp_path)
    manifest = script.build_input_manifest(run_dir, gold, None, None, asset)
    gold.write_text('{"qid": "Q2"}\n', encoding="utf-8")
    with pytest.raises(ScorerV2Error):
        script.verify_input_manifest(manifest, run_dir, gold, None, None,
                                     asset)


def test_verify_fails_on_extra_scanned_file(tmp_path):
    run_dir, gold, asset = _make_tree(tmp_path)
    manifest = script.build_input_manifest(run_dir, gold, None, None, asset)
    (run_dir / "agent_batch" / "merged" / "predictions2.jsonl").write_text(
        "{}\n", encoding="utf-8")
    with pytest.raises(ScorerV2Error):
        script.verify_input_manifest(manifest, run_dir, gold, None, None,
                                     asset)


def test_verify_fails_on_missing_file(tmp_path):
    run_dir, gold, asset = _make_tree(tmp_path)
    manifest = script.build_input_manifest(run_dir, gold, None, None, asset)
    (run_dir / "agent_batch" / "merged" / "predictions.jsonl").unlink()
    with pytest.raises(ScorerV2Error):
        script.verify_input_manifest(manifest, run_dir, gold, None, None,
                                     asset)


def test_verify_fails_on_asset_library_swap(tmp_path):
    run_dir, gold, asset = _make_tree(tmp_path)
    manifest = script.build_input_manifest(run_dir, gold, None, None, asset)
    asset.write_text('{"btid": "bt0002"}\n', encoding="utf-8")
    with pytest.raises(ScorerV2Error):
        script.verify_input_manifest(manifest, run_dir, gold, None, None,
                                     asset)


def test_verify_fails_when_input_unprotected(tmp_path):
    run_dir, gold, asset = _make_tree(tmp_path)
    manifest = script.build_input_manifest(run_dir, gold, None, None, None)
    with pytest.raises(ScorerV2Error):
        script.verify_input_manifest(manifest, run_dir, gold, None, None,
                                     asset)


def test_init_refuses_to_overwrite_manifest(tmp_path):
    run_dir, gold, asset = _make_tree(tmp_path)
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    (out_dir / "input_manifest.json").write_text('{"groups": []}\n',
                                                 encoding="utf-8")
    with pytest.raises(ScorerV2Error):
        script.main([
            "--run-dir", str(run_dir), "--gold", str(gold),
            "--asset-library", str(asset), "--out-dir", str(out_dir),
            "--init-input-manifest",
        ])


def test_recompute_fails_without_manifest(tmp_path):
    run_dir, gold, asset = _make_tree(tmp_path)
    out_dir = tmp_path / "out2"
    with pytest.raises(ScorerV2Error):
        script.main([
            "--run-dir", str(run_dir), "--gold", str(gold),
            "--asset-library", str(asset), "--out-dir", str(out_dir),
        ])
    assert not (out_dir / "score_v2.json").exists()
