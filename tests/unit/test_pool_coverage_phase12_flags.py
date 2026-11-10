"""Unit tests for Phase 1 & Phase 2 optional pool coverage flags.

Verifies:
1. Default flag values preserve S0_prime pool_specs and pool_diagnostics byte-for-byte
   (both with and without V43_RECORDED_CORPUS_CACHE_DIR memoization).
2. _center_keep_atoms(shell=1, 2, 3) preserves shell=1 and shell=2 exact sets/bonds
   and generalizes to shell=3.
3. Optional flags (recorded_channel, corpus_channel, analog_channel, uspto_channel,
   analog_retrieval_mode="fg" / "merge", center_shell=1 / 3) execute cleanly.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from rdkit import Chem

from pathway_v43.config import resolve_config
from pathway_v43.pollutant.s5b_builder import (
    build_run_input,
    default_pool_provider,
)
from pathway_v43.pollutant.s5b_cli import build_parser
from pathway_v43.pollutant.s5b_compiler import (
    _center_keep_atoms,
    compile_donor_template,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def _legacy_center_keep_atoms(lhs_mol, l1_idx, shell: int = 2):
    near = set(l1_idx)
    keep_atoms = set(l1_idx)
    if shell >= 2:
        d1 = set()
        for b in lhs_mol.GetBonds():
            i, j = b.GetBeginAtomIdx(), b.GetEndAtomIdx()
            if i in near or j in near:
                d1.add(i)
                d1.add(j)
        near |= d1
        for b in lhs_mol.GetBonds():
            i, j = b.GetBeginAtomIdx(), b.GetEndAtomIdx()
            if i in near or j in near:
                keep_atoms.add(i)
                keep_atoms.add(j)
    else:
        for b in lhs_mol.GetBonds():
            i, j = b.GetBeginAtomIdx(), b.GetEndAtomIdx()
            if i in near or j in near:
                keep_atoms.add(i)
                keep_atoms.add(j)
    keep_bonds = []
    for b in lhs_mol.GetBonds():
        i, j = b.GetBeginAtomIdx(), b.GetEndAtomIdx()
        if (i in near or j in near) and i in keep_atoms and j in keep_atoms:
            keep_bonds.append((i, j, b.GetBondType()))
    return near, keep_atoms, keep_bonds


def test_center_keep_atoms_shell_1_2_identical_and_shell_3_expands():
    mol = Chem.MolFromSmiles("CCCCC(=O)OCC")
    assert mol is not None
    l1_idx = {4, 5, 6}
    for shell in (1, 2):
        assert _center_keep_atoms(mol, l1_idx, shell=shell) == _legacy_center_keep_atoms(
            mol, l1_idx, shell=shell
        )
    near2, keep2, _ = _center_keep_atoms(mol, l1_idx, shell=2)
    near3, keep3, _ = _center_keep_atoms(mol, l1_idx, shell=3)
    assert keep2.issubset(keep3)
    assert len(keep3) > len(keep2)


def test_compile_donor_template_default_center_shell_byte_identical():
    lhs = "[CH3:1][CH2:2][C:3](=[O:4])[OH:5]"
    rhs = "[CH3:1][CH2:2][CH2:3][OH:4].[OH2:5]"
    sub = "CCCC(=O)O"
    out_default = compile_donor_template(
        mapped_lhs=lhs,
        mapped_rhs=rhs,
        center_atoms=[3, 4, 5],
        substrate_smiles=sub,
        record_id="syn-test-1",
    )
    out_s2 = compile_donor_template(
        mapped_lhs=lhs,
        mapped_rhs=rhs,
        center_atoms=[3, 4, 5],
        substrate_smiles=sub,
        record_id="syn-test-1",
        center_shell=2,
    )
    assert json.dumps(out_default, sort_keys=True) == json.dumps(out_s2, sort_keys=True)
    out_s1 = compile_donor_template(
        mapped_lhs=lhs,
        mapped_rhs=rhs,
        center_atoms=[3, 4, 5],
        substrate_smiles=sub,
        record_id="syn-test-1",
        center_shell=1,
    )
    out_s3 = compile_donor_template(
        mapped_lhs=lhs,
        mapped_rhs=rhs,
        center_atoms=[3, 4, 5],
        substrate_smiles=sub,
        record_id="syn-test-1",
        center_shell=3,
    )
    assert out_s1["status"] == "compiled"
    assert out_s3["status"] == "compiled"


def test_default_pool_provider_cached_matches_s0_prime_byte_for_byte(monkeypatch):
    s0_dir = REPO_ROOT / "reports/ppv1_s5b/pool_coverage_20261109/batch_298_s0_prime"
    cache_dir = REPO_ROOT / "reports/ppv1_s5b/pool_coverage_20261109/_rc_cache"
    if not (s0_dir / "batch_manifest.json").is_file() or not cache_dir.is_dir():
        return

    monkeypatch.setenv("V43_RECORDED_CORPUS_CACHE_DIR", str(cache_dir))
    monkeypatch.setenv("V43_ANALOG_CORPUS", "v1")
    cfg = resolve_config(None, str(REPO_ROOT / "assets"))
    dummy_engine = object()
    provider = default_pool_provider(cfg, max_pool=8, raw_top=24, threshold=0.45, engine=dummy_engine)

    manifest = json.loads((s0_dir / "batch_manifest.json").read_text(encoding="utf-8"))
    batch_tag = str(manifest.get("batch_tag") or "s0p-298")
    for entry in manifest["entries"][:5]:
        qid = str(entry["qid"])
        sub = entry["substrate_smiles"]
        raw_bytes = (s0_dir / entry["run_input_rel"]).read_bytes()
        expected_sha256 = hashlib.sha256(raw_bytes).hexdigest()
        ri = json.loads(raw_bytes.decode("utf-8"))
        expected_specs = ri["plan"]["pools"][sub]
        expected_diag = entry["pool_diagnostics"]

        actual_specs = provider(sub)
        actual_diag = dict(provider.last_diagnostics)
        # pool_builder_parallel adds n_pool_truncated to manifest pool_diagnostics
        actual_diag["n_pool_truncated"] = expected_diag.get("n_pool_truncated", 0)

        assert json.dumps(actual_specs, sort_keys=True) == json.dumps(expected_specs, sort_keys=True)
        assert json.dumps(actual_diag, sort_keys=True) == json.dumps(expected_diag, sort_keys=True)

        rebuilt_ri = build_run_input(
            {"qid": qid, "substrate_smiles": sub},
            batch_tag=batch_tag,
            pools={sub: actual_specs},
            provider_kind=str(ri.get("provider_kind") or "real"),
        )
        rebuilt_bytes = (
            json.dumps(rebuilt_ri, ensure_ascii=False, sort_keys=True, indent=1) + "\n"
        ).encode("utf-8")
        assert hashlib.sha256(rebuilt_bytes).hexdigest() == expected_sha256


def test_default_pool_provider_and_cli_defaults_byte_identical_to_fcd2707():
    parser = build_parser()
    args_default = parser.parse_args(
        ["build", "--questions", "q.jsonl", "--batch-root", "out"]
    )
    assert args_default.pool_profile == "s0"
    assert args_default.max_pool == 8
    assert args_default.pool_threshold == 0.45
    assert args_default.retro_channel is False
    assert args_default.retro_dataset == "rhea"
    assert args_default.retro_radii is None
    assert args_default.retro_ranking_mode == "append"

    args_rds = parser.parse_args(
        [
            "build",
            "--questions",
            "q.jsonl",
            "--batch-root",
            "out",
            "--retro-channel",
            "--retro-dataset",
            "mnx",
            "--retro-radii",
            "6",
            "--retro-ranking-mode",
            "append",
        ]
    )
    assert args_rds.retro_channel is True
    assert args_rds.retro_dataset == "mnx"
    assert args_rds.retro_radii == "6"
    assert args_rds.retro_ranking_mode == "append"

    cfg = resolve_config(None, str(REPO_ROOT / "assets"))
    sub = "CC(=O)Oc1ccccc1C(=O)O"
    prov_implicit = default_pool_provider(cfg, engine=None)
    prov_explicit_fcd2707 = default_pool_provider(
        cfg,
        max_pool=8,
        raw_top=24,
        threshold=0.45,
        fallback_threshold=0.40,
        min_unique_targets=3,
        engine=None,
        recorded_channel=True,
        corpus_channel=True,
        analog_channel=True,
        uspto_channel=False,
        analog_retrieval_mode="similarity",
        center_shell=2,
        retro_channel=False,
    )
    specs_imp = prov_implicit(sub)
    specs_exp = prov_explicit_fcd2707(sub)
    ri_imp = build_run_input(
        {"qid": "syn-q1", "substrate_smiles": sub},
        batch_tag="fcd2707-eq",
        pools={sub: specs_imp},
    )
    ri_exp = build_run_input(
        {"qid": "syn-q1", "substrate_smiles": sub},
        batch_tag="fcd2707-eq",
        pools={sub: specs_exp},
    )
    bytes_imp = (
        json.dumps(ri_imp, ensure_ascii=False, sort_keys=True, indent=1) + "\n"
    ).encode("utf-8")
    bytes_exp = (
        json.dumps(ri_exp, ensure_ascii=False, sort_keys=True, indent=1) + "\n"
    ).encode("utf-8")
    assert hashlib.sha256(bytes_imp).hexdigest() == hashlib.sha256(bytes_exp).hexdigest()
    assert json.dumps(prov_implicit.last_diagnostics, sort_keys=True) == json.dumps(
        prov_explicit_fcd2707.last_diagnostics, sort_keys=True
    )


def test_phase12_optional_modes_execute_cleanly(monkeypatch):
    cache_dir = REPO_ROOT / "reports/ppv1_s5b/pool_coverage_20261109/_rc_cache"
    monkeypatch.setenv("V43_RECORDED_CORPUS_CACHE_DIR", str(cache_dir))
    monkeypatch.setenv("V43_ANALOG_CORPUS", "v1")
    cfg = resolve_config(None, str(REPO_ROOT / "assets"))
    sub = "CC(=O)Oc1ccccc1C(=O)O"

    for kwargs in [
        {"recorded_channel": False},
        {"corpus_channel": False},
        {"analog_channel": False},
        {"uspto_channel": True},
        {"analog_retrieval_mode": "fg"},
        {"analog_retrieval_mode": "merge"},
        {"center_shell": 1},
        {"center_shell": 3},
        {"retro_channel": True, "retro_dataset": "rhea", "retro_radii": {4}, "retro_ranking_mode": "append"},
        {"retro_channel": True, "retro_dataset": "mnx+rhea", "retro_radii": {2, 4}, "retro_ranking_mode": "unified_score"},
    ]:
        prov = default_pool_provider(cfg, engine=None, **kwargs)
        specs = prov(sub)
        assert isinstance(specs, list)
        assert isinstance(prov.last_diagnostics, dict)
        if kwargs.get("retro_channel"):
            assert "retro_diagnostics" in prov.last_diagnostics
