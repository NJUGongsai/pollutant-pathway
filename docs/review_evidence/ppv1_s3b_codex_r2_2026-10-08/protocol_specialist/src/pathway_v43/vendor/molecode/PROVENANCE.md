# vendored: AtomFlow-AI/MoleCode(molecule + prompts 子集)

> 本文件是本仓(`dependingv43`)对 vendored MoleCode 的来源与许可记录。
> 迁移链:上游 GitHub → `dependingv4/vendor/molecode`(零 diff 审计)→
> 本仓 `src/pathway_v43/vendor/molecode`(子集拷贝)。

## 1. 上游来源

- **上游**: https://github.com/AtomFlow-AI/MoleCode
- **commit**: `a4df3b04552b829ff816467b9620757a5dad765b`(2026-06-04,"Update README.zh-CN.md")
- **许可证**: MIT(AtomFlow-AI, 2026)——见本目录 `LICENSE`,允许复制/修改/再分发
- **论文**: arXiv 2605.16480(MoleCode: 图显式分子语言)
- **中转来源**: `/Volumes/CC/Enzyme_Agent/dependingv4/vendor/molecode/`
  (v4 仓 2026-09-21 入仓审计,`molecule/` 六文件与上游零 diff,
  见 v4 `vendor/PROVENANCE.md` 与 `vendor/MANIFEST.sha256`)
- **本仓拷贝日期**: 2026-09-24;`molecule/__init__.py`、
  `molecule/rdkit_to_mermaid.py`、`molecule/mermaid_to_rdkit.py`、
  `prompts/__init__.py`、`prompts/molecule_system_prompt.py`、
  `prompts/markush_system_prompt.py` 与中转来源**逐字节一致**
  (拷贝后 `diff` 逐文件核对),`MANIFEST.sha256` 记录七个文件哈希。

## 2. 与上游包的差异(全部显式记录)

| 差异 | 原因 |
|---|---|
| 未 vendored `markush/` | markush 子包 `import networkx`;本仓运行环境未安装 networkx,且 v4.3 AtomTool 只需要小分子转换(任务书 §3 范围)。上游审计亦确认 networkx 仅 markush 使用 |
| 未 vendored `polymer/` | v4.3 降解路径分子为小分子,不用重复单元语法 |
| 未 vendored `llm.py` | 上游自带的 OpenAI 客户端;本仓模型请求统一走 `pathway_v43/adapters/llm_client.py`(REPO_DESIGN §3 依赖方向) |
| 顶层 `__init__.py` 为本仓自写 | 上游 `__init__` 顶层 `from . import molecule, polymer, markush, prompts` 会连带导入 markush → networkx。本仓 init 只 re-export molecule 与 prompts;上游原文见下节存档 |
| `prompts/` 含 `markush_system_prompt.py` | 该文件是纯文本常量(无 networkx 依赖),为保持 `prompts/` 目录与上游逐字节一致而整体保留 |

## 3. 用途边界

MoleCode 只作为 v4.3 AtomTool 的**编辑视图表示**(SMILES ↔ Mermaid 图语法
往返、原子稳定 ID、受限编辑核验);化学状态以可解析分子图及其 canonical
SMILES 为准(ARCHITECTURE §4)。不接入 v3 冻结引擎运行时,不参与检索排序。

## 4. 上游顶层 `__init__.py` 原文存档

```python
"""MoleCode — an LLM-native, graph-explicit molecular language.

MoleCode serializes molecules as Mermaid graphs in which every atom and bond is
a typed declaration with a persistent identifier, so molecular topology is
directly readable, editable, and auditable inside an LLM context window. It is
deterministically and losslessly inter-convertible with SMILES / MOL via RDKit
(no learned model). The same Subgraph–Node–Edge grammar spans three domains:

    molecode.molecule  — small molecules
    molecode.polymer   — polymers (explicit repeat unit + ``×n``)
    molecode.markush   — Markush structures (``{}`` abbreviation nodes)
    molecode.prompts   — LLM system prompts for each grammar

Quick start::

    from molecode import mol_to_mermaid, mermaid_to_mol, mol_to_smiles
    from rdkit import Chem

    mermaid = mol_to_mermaid(Chem.MolFromSmiles("CC(=O)Oc1ccccc1C(=O)O"),
                             name="Aspirin")
    print(mermaid)
    assert mol_to_smiles(mermaid_to_mol(mermaid))  # round-trips
"""

from . import molecule, polymer, markush, prompts

# Small molecules are the default top-level converters.
from .molecule import (
    mol_to_mermaid,
    mermaid_to_mol,
    mol_to_smiles,
    mol_to_inchi,
)

# Optional, dependency-free OpenAI-compatible client for driving LLM tasks.
from .llm import LLMClient

__version__ = "0.1.0"

__all__ = [
    "molecule",
    "polymer",
    "markush",
    "prompts",
    "LLMClient",
    "mol_to_mermaid",
    "mermaid_to_mol",
    "mol_to_smiles",
    "mol_to_inchi",
    "__version__",
]
```

## 5. 完整性复核

```sh
cd src/pathway_v43/vendor/molecode && shasum -a 256 -c MANIFEST.sha256
```

七条全 PASS 即当前 vendored 文件与本记录一致;AtomTool 初始化时会以代码
复核 `molecule/`+`prompts/` 六文件哈希(见 `services/atom_tool.py` 的
`verify_vendor_integrity`),不符即 fail-closed 拒绝运行。
