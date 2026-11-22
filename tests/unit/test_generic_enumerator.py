"""v1.3 T1-D 通用枚举器单测（确定性、覆盖类型、吸附阈值、默认关闭）。"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from rdkit import Chem  # noqa: E402
from rdkit.Chem import rdMolDescriptors  # noqa: E402

from pathway_v43.services.generic_enumerator import (  # noqa: E402
    ENUMERATOR_VERSION,
    adsorb_to_enumeration,
    enumerate_candidates,
    enumerate_cleavage_fragments,
    enumerate_for_pool_injection,
    enumerate_one_step,
    generic_enumeration_enabled,
)


def _formulas(smiles_list):
    out = set()
    for smiles in smiles_list:
        mol = Chem.MolFromSmiles(smiles)
        if mol is not None:
            out.add(rdMolDescriptors.CalcMolFormula(mol))
    return out


def test_disabled_by_default():
    assert generic_enumeration_enabled(None) is False
    assert generic_enumeration_enabled({}) is False
    assert generic_enumeration_enabled({"enable_v13_generic_enumeration": True})
    injected = enumerate_for_pool_injection("CCO")
    assert injected.candidates == []


def test_alcohol_oxidation_and_acid_path():
    result = enumerate_one_step("CCO")
    assert result.candidates
    assert "alcohol_oxidation_carbonyl" in result.by_rule
    assert "C2H4O" in _formulas(result.candidates)  # 乙醛
    assert ENUMERATOR_VERSION


def test_aromatic_hydroxylation():
    result = enumerate_one_step("c1ccccc1")
    assert "c_h_hydroxylation_aromatic" in result.by_rule
    assert any(
        Chem.MolFromSmiles(s) is not None
        and rdMolDescriptors.CalcMolFormula(Chem.MolFromSmiles(s)) == "C6H6O"
        for s in result.candidates)


def test_decarboxylation_benzoic_acid():
    result = enumerate_one_step("OC(=O)c1ccccc1")
    assert "decarboxylation" in result.by_rule
    assert "C6H6" in _formulas(result.candidates)


def test_cleavage_fragments_ester():
    result = enumerate_cleavage_fragments("CCOC(C)=O")
    assert result.candidates
    formulas = _formulas(result.candidates)
    assert "C2H4O2" in formulas  # 乙酸（-OH 封端）
    assert "C2H6O" in formulas   # 乙醇（-H 封端）


def test_enumerate_candidates_merges_and_dedupes():
    merged = enumerate_candidates("CCO")
    assert merged.candidates == sorted(set(merged.candidates))
    one = set(enumerate_one_step("CCO").candidates)
    assert one <= set(merged.candidates)


def test_deterministic_output():
    a = enumerate_candidates("CC(=O)Oc1ccccc1C(=O)O")
    b = enumerate_candidates("CC(=O)Oc1ccccc1C(=O)O")
    assert a.candidates == b.candidates
    assert a.by_rule == b.by_rule


def test_adsorb_target_to_exact_enumeration_candidate():
    # 底物苯甲醛；枚举含苯甲酸（醛→酸），目标用同物异写
    result = adsorb_to_enumeration("O=Cc1ccccc1", "OC(=O)c1ccccc1")
    assert result is not None
    assert result["similarity"] >= 0.99
    mol = Chem.MolFromSmiles(result["adsorbed_smiles"])
    assert rdMolDescriptors.CalcMolFormula(mol) == "C7H6O2"


def test_adsorb_returns_none_for_invalid_target():
    assert adsorb_to_enumeration("CCO", "not-a-smiles##") is None


def test_adsorb_returns_none_below_threshold():
    # 底物乙醇的枚举项都很小；胆固醇与它们相似度低
    result = adsorb_to_enumeration(
        "CCO",
        "CC(C)CCCC(C)C1CCC2C1(CCC3C2CC=C4C3(CCC(C4)O)C)C",
        min_similarity=0.95)
    assert result is None