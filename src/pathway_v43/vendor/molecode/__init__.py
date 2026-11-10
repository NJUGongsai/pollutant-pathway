"""pathway_v43.vendor.molecode — AtomFlow-AI/MoleCode 子集(见 PROVENANCE.md)。

本 __init__ 为本仓自写:只暴露 molecule 与 prompts 两个子包,不导入
markush(依赖 networkx,本环境未装)、polymer、llm。上游原版 __init__ 全文
在 PROVENANCE.md 第 4 节存档。
"""

from . import molecule, prompts  # noqa: F401
from .molecule import (  # noqa: F401
    mol_to_mermaid,
    mermaid_to_mol,
    mol_to_smiles,
)

__version__ = "0.1.0+v43.subset"  # 上游 0.1.0;+v43.subset 标记本仓子集封装

__all__ = [
    "molecule",
    "prompts",
    "mol_to_mermaid",
    "mermaid_to_mol",
    "mol_to_smiles",
    "__version__",
]
