"""规范分子身份 — 电荷归一化 + 立体盲 canonical(v3.3 引擎/评测器口径)。

口径镜像 v3 ``bbd_v33_fusion.normalize_charge_smiles`` / ``eawag_lookup._cn_identity``
与 v4 ``pathway_agent/state.py::cn_identity``(后者与 v3 引擎 ``X._identity``
有对拍断言)。本模块为纯 RDKit 实现,domain 层不导入 v3/v4 代码;
与 V43Engine.cn_identity 的一致性由 tests/test_domain_identity.py 对拍断言。
"""

from __future__ import annotations

from functools import lru_cache

from rdkit import Chem, RDLogger
from rdkit.Chem.MolStandardize import rdMolStandardize

RDLogger.DisableLog("rdApp.*")

IDENTITY_VERSION = "cn-v1"  # 电荷归一化+立体盲 canonical;口径变更须升版本


@lru_cache(maxsize=100_000)
def _uncharger() -> rdMolStandardize.Uncharger:
    return rdMolStandardize.Uncharger()


@lru_cache(maxsize=100_000)
def normalize_charge_smiles(smi: str) -> str | None:
    """电荷归一化 canonical(镜像 v3 bbd_v33_fusion.normalize_charge_smiles)。"""
    m = Chem.MolFromSmiles(smi)
    if m is None:
        return None
    try:
        m2 = _uncharger().uncharge(m)
        Chem.SanitizeMol(m2)
    except Exception:
        m2 = m
    return Chem.MolToSmiles(m2)


@lru_cache(maxsize=100_000)
def stereo_blind(smi: str) -> str | None:
    m = Chem.MolFromSmiles(smi)
    return Chem.MolToSmiles(m, isomericSmiles=False) if m is not None else None


def cn_identity(smi: str) -> str | None:
    """cn 身份:stereo_blind(normalize_charge_smiles(smi));失败逐级回退。

    与 v3 ``eawag_lookup._cn_identity`` / 引擎 ``X._identity`` 同口径;
    解析失败返回 None(调用方 fail-closed)。
    """
    norm = normalize_charge_smiles(smi)
    if norm is None:
        return stereo_blind(smi)
    return stereo_blind(norm) or stereo_blind(smi)


def parseable(smiles: str) -> bool:
    """SMILES 可解析且价态合法(RDKit 默认 sanitize 含价态检查)。"""
    return Chem.MolFromSmiles(smiles) is not None
