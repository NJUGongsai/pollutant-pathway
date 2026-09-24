"""规范分子身份:电荷归一化 + 立体盲;与冻结引擎 cn 口径对拍(slow)。"""

from __future__ import annotations

import pytest

from pathway_v43.domain.identity import cn_identity, normalize_charge_smiles


def test_charge_normalized_identity_acids_and_anions():
    neutral = cn_identity("OC(=O)c1ccccc1")
    anion = cn_identity("O=C([O-])c1ccccc1")
    assert neutral is not None and neutral == anion


def test_stereo_blind_identity():
    a = cn_identity("C[C@H](O)C")
    b = cn_identity("C[C@@H](O)C")
    assert a is not None and a == b


def test_unparseable_returns_none():
    assert cn_identity("C(C)(C)(C)(C)C") is None
    assert cn_identity("not_a_smiles") is None
    assert normalize_charge_smiles("not_a_smiles") is None


@pytest.mark.slow
def test_identity_parity_with_frozen_engine():
    """与 V43Engine.cn_identity(v3 X._identity 口径)逐分子对拍。"""
    from pathway_v43.adapters.v3_engine import get_engine
    from pathway_v43.config import resolve_config

    engine = get_engine(resolve_config())
    samples = [
        "Oc1ccccc1O",
        "OC(=O)c1ccccc1",
        "O=C([O-])c1ccccc1",
        "O=C([O-])C=CC=CC(=O)[O-]",   # muconate 阴离子
        "O=CC=CC=C(O)C(=O)[O-]",
        "C[C@H](O)C",
        "CCO",
        "O",
    ]
    for smi in samples:
        assert cn_identity(smi) == engine.cn_identity(smi), smi
