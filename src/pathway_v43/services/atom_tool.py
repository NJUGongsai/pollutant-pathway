"""AtomTool — SMILES ↔ MoleCode 往返与受限编辑核验(确定性,零模型)。

表示基础是本仓 vendored 的 MoleCode molecule 子集(来源/许可见
``vendor/molecode/PROVENANCE.md``;初始化时逐文件核验哈希,fail-closed)。

职责(任务书 §3):
- SMILES → 带稳定原子标识(MoleCode 原子 ID)的编辑视图;渲染期保留
  ``atom_id_map``(RDKit atom idx ↔ MoleCode ID),映射/编辑核验据此进行;
- MoleCode → SMILES;往返身份核对:canonical SMILES(含立体)逐字符一致,
  不一致即判定表示有损 → 拒绝并给原因(如实探测,不做悄悄替代);
- 编辑引用核验:模型编辑引用的原子 ID 必须存在于当前 MoleCode;目标
  MoleCode 不得丢失既有原子 ID(原子守恒的表示层检查);
- 明确测试过的表示能力边界(手性/电荷/芳香/多组分可无损;同位素有损 →
  拒)由 tests/test_atom_tool.py 固定,任何回归都会被往返核对当场拒绝。

MoleCode 只是编辑视图;化学状态以可解析分子图及其 canonical SMILES 为准
(ARCHITECTURE §4)。本工具零模型、零网络。
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from rdkit import Chem, RDLogger

RDLogger.DisableLog("rdApp.*")

from ..domain.identity import cn_identity  # noqa: E402

_VENDOR_ROOT = Path(__file__).resolve().parents[1] / "vendor" / "molecode"

# vendored 子集逐文件 SHA256(与 vendor/molecode/MANIFEST.sha256 一致;
# 换上游版本必须同步改这里并记录 PROVENANCE, resume 身份随之变化)
VENDOR_FILES: dict[str, str] = {
    "molecule/__init__.py":
        "0dd0d21d18bd181117fbf4418dbcaf09336303ba350d1ea235266aefc4ee223a",
    "molecule/rdkit_to_mermaid.py":
        "195a65e84fd77bb20f0aae61b256620b2489a68d146aa0b9f0909e1e94f37299",
    "molecule/mermaid_to_rdkit.py":
        "561ce966ba1195ed750ed66fc4023d9f501a9e580a509f4723506a270789b12c",
    "prompts/__init__.py":
        "f8160966acc0126d36121a02a0d3d0a2375c4d1010e9177fed32039e5b3bcf5d",
    "prompts/molecule_system_prompt.py":
        "ed4c654143c1802153377ec6de6f77c3d2d4845b4e107d1d0cf239cd34322e8e",
    "prompts/markush_system_prompt.py":
        "1377960f68d86ce7f3d946a9304aebd705887795593da184da6ce527b2617d58",
    "LICENSE":
        "d768cb92822c0e97bb6c0f9efab6a5f0a093f58a439959b02db687abfedc980e",
}

VENDOR_UPSTREAM_COMMIT = "a4df3b04552b829ff816467b9620757a5dad765b"

# MoleCode 原子 ID 形如 <Name>_<Symbol>_<n>[_R|_S];Symbol 是元素符号
ATOM_ID_RE = re.compile(
    r"\b(?P<name>[A-Za-z][A-Za-z0-9]*)_(?P<elem>[A-Za-z]{1,2})_(?P<n>\d+)"
    r"(?:_(?P<cip>[RS]))?\b"
)

ATOMTOOL_VERSION = "v43-atomtool-1"


class AtomToolError(ValueError):
    """结构/表示/编辑核验失败(fail-closed)。reason 为稳定机读码。"""

    def __init__(self, reason: str, message: str, detail: dict | None = None):
        super().__init__(f"{reason}:{message}")
        self.reason = reason
        self.detail = detail or {}


@dataclass
class MoleculeRender:
    """SMILES 的 MoleCode 渲染结果(编辑视图 + 原子 ID 对照表)。"""

    smiles: str                 # 输入 SMILES(原样)
    canonical_smiles: str       # RDKit canonical(含立体)
    molecode: str               # Mermaid 文本
    atom_id_map: dict[str, int] = field(default_factory=dict)  # ID → atom idx
    idx_atom_map: dict[int, str] = field(default_factory=dict)  # idx → ID

    @property
    def atom_ids(self) -> list[str]:
        return sorted(self.atom_id_map, key=lambda a: self.atom_id_map[a])


def verify_vendor_integrity() -> dict:
    """核验 vendored MoleCode 子集哈希(任务书 §3:记录来源并锁定实现)。

    任何文件缺失/被改 → AtomToolError(fail-closed;MoleCode 实现是 run
    身份的一部分,被改即不得运行)。
    """
    for rel, expected in VENDOR_FILES.items():
        path = _VENDOR_ROOT / rel
        if not path.is_file():
            raise AtomToolError(
                "vendor_integrity",
                f"vendored MoleCode 文件缺失:{rel}",
                {"file": rel, "vendor_root": str(_VENDOR_ROOT)},
            )
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            raise AtomToolError(
                "vendor_integrity",
                f"vendored MoleCode 哈希不符:{rel}",
                {"file": rel, "expected": expected[:12], "actual": actual[:12]},
            )
    return {
        "implementation": "molecode",
        "upstream_commit": VENDOR_UPSTREAM_COMMIT,
        "vendor_root": str(_VENDOR_ROOT),
        "files": dict(VENDOR_FILES),
        "manifest_sha256": hashlib.sha256(
            "\n".join(f"{v}  {k}" for k, v in sorted(VENDOR_FILES.items()))
            .encode()
        ).hexdigest(),
    }


@lru_cache(maxsize=1)
def _verified_vendor() -> tuple:
    verify_vendor_integrity()
    from pathway_v43.vendor.molecode.molecule import (  # noqa: F401
        MolToMermaidConverter,
        mermaid_to_mol,
    )
    return MolToMermaidConverter, mermaid_to_mol


def _canonical(mol) -> str:
    return Chem.MolToSmiles(mol)


def render(smiles: str, name: str = "M") -> MoleculeRender:
    """SMILES → MoleCode 渲染(带原子 ID 对照)。不可解析 → fail-closed。"""
    _MolToMermaidConverter, _ = _verified_vendor()
    mol = Chem.MolFromSmiles(smiles or "")
    if mol is None:
        raise AtomToolError(
            "unparseable_smiles", f"SMILES 不可解析:{smiles!r}",
            {"smiles": smiles},
        )
    conv = _MolToMermaidConverter(subgraph_name=name)
    text = conv.convert(mol)
    id_to_idx = {aid: idx for idx, aid in conv.atom_id_map.items()}
    return MoleculeRender(
        smiles=smiles, canonical_smiles=_canonical(mol), molecode=text,
        atom_id_map=id_to_idx, idx_atom_map=dict(conv.atom_id_map),
    )


def molecode_to_mol(text: str):
    """MoleCode → RDKit Mol;解析失败返回 None(如实,不抛不猜)。"""
    _, mermaid_to_mol = _verified_vendor()
    try:
        return mermaid_to_mol(text or "")
    except Exception:
        return None


def molecode_to_smiles(text: str) -> str | None:
    mol = molecode_to_mol(text)
    return _canonical(mol) if mol is not None else None


def roundtrip(smiles: str, name: str = "M") -> MoleculeRender:
    """SMILES → MoleCode → SMILES 并核对身份;有损即拒(representation_lossy)。

    身份核对 = canonical SMILES(含立体/电荷)逐字符一致;探明的有损情形
    (如同位素)在此被拒绝,绝不以未经验证的 SMILES 替代。
    """
    render_ = render(smiles, name)
    back = molecode_to_mol(render_.molecode)
    if back is None:
        raise AtomToolError(
            "molecode_unparseable",
            "MoleCode 回读失败(往返断裂)",
            {"smiles": smiles},
        )
    back_can = _canonical(back)
    if back_can != render_.canonical_smiles:
        raise AtomToolError(
            "representation_lossy",
            f"MoleCode 往返身份不一致:渲染前={render_.canonical_smiles!r} "
            f"回读={back_can!r};表示能力边界(如同位素/不支持特征)必须拒绝",
            {"before": render_.canonical_smiles, "after": back_can},
        )
    return render_


def parse_atom_ids(text: str) -> set[str]:
    """从 MoleCode 文本提取原子 ID 集合(节点行+键行都覆盖)。"""
    return {m.group(0) for m in ATOM_ID_RE.finditer(text or "")}


def check_target_molecode(current: MoleculeRender, target_text: str) -> dict:
    """核验模型给出的目标 MoleCode(受限编辑结果)。

    确定性检查(表示层;化学门禁在 validation/gates):
    - 目标可解析(否则 molecode_unparseable);
    - 目标原子 ID ⊇ 当前原子 ID(编辑不得使既有原子凭空消失;
      mapping_inconsistent:atom_removed 点名缺失 ID);
    - 同名 ID 元素一致(ID 内嵌元素符号;不一致说明模型改写了标识体系,
      mapping_inconsistent:element_mismatch)。
    返回 {ok, target_smiles, added_atom_ids, removed_atom_ids, reasons}。
    """
    reasons: list[str] = []
    target_mol = molecode_to_mol(target_text)
    if target_mol is None:
        return {"ok": False, "reasons": ["molecode_unparseable:目标 MoleCode 无法解析"]}
    cur_ids = set(current.atom_id_map)
    tgt_ids = parse_atom_ids(target_text)
    missing = sorted(cur_ids - tgt_ids)
    for aid in missing:
        reasons.append(f"mapping_inconsistent:atom_removed:{aid}")
    # 元素一致性:同名 ID 的元素符号必须一致
    for aid in sorted(cur_ids & tgt_ids):
        cur_elem = _id_element(aid)
        tgt_elem = _id_element(aid)
        if cur_elem and tgt_elem and cur_elem != tgt_elem:
            reasons.append(
                f"mapping_inconsistent:element_mismatch:{aid}"
                f"({cur_elem}->{tgt_elem})"
            )
    added = sorted(tgt_ids - cur_ids)
    return {
        "ok": not reasons,
        "reasons": reasons,
        "target_smiles": _canonical(target_mol),
        "added_atom_ids": added,
        "removed_atom_ids": missing,
    }


def _id_element(atom_id: str) -> str | None:
    m = ATOM_ID_RE.match(atom_id)
    return m.group("elem") if m else None


def check_edit_references(current: MoleculeRender,
                          edits: list[dict]) -> tuple[bool, list[str]]:
    """核验模型编辑列表引用的原子/键是否存在于当前 MoleCode(任务书 §3)。

    编辑形状(宽松接受,引用核验从严):
      {"op": "break_bond"|"remove_bond", "atom1": ID, "atom2": ID}
      {"op": "form_bond"|"add_bond", "atom1": ID, "atom2": ID}
      {"op": "remove_atom"|"delete_atom", "atom": ID}
      {"op": "add_atom", "element": "O", "atom1": ID}   # 新原子挂到既有原子
    """
    reasons: list[str] = []
    ids = set(current.atom_id_map)
    bonds = {
        frozenset((current.idx_atom_map[b.GetBeginAtomIdx()],
                   current.idx_atom_map[b.GetEndAtomIdx()]))
        for b in Chem.MolFromSmiles(current.smiles).GetBonds()
    } if Chem.MolFromSmiles(current.smiles) is not None else set()
    for i, edit in enumerate(edits or []):
        op = str(edit.get("op", "")).lower()
        a1, a2 = edit.get("atom1"), edit.get("atom2")
        single = edit.get("atom")
        referenced = [x for x in (a1, a2, single) if x is not None]
        if not referenced:
            reasons.append(f"edit_invalid:missing_atom_reference:edit[{i}]")
            continue
        for ref in referenced:
            if ref not in ids:
                reasons.append(f"edit_invalid:unknown_atom:{ref}")
        if op in ("break_bond", "remove_bond", "form_bond", "add_bond"):
            if a1 in ids and a2 in ids:
                pair = frozenset((a1, a2))
                if op in ("break_bond", "remove_bond") and pair not in bonds:
                    reasons.append(
                        f"edit_invalid:bond_not_present:{a1}~{a2}")
                if op in ("form_bond", "add_bond") and pair in bonds:
                    reasons.append(f"edit_invalid:bond_already_present:{a1}~{a2}")
    return (not reasons), reasons


def align_donor_mapping(donor_mol, current_mol, center_map_nums=None,
                        center_only: bool = False):
    """供体分子 → 当前分子的确定性原子对齐(类比映射找回的对齐步)。

    - center_only=False:全供体子结构匹配(full_donor_substructure);
    - center_only=True:只取反应中心子图(reaction_center_substructure)。
      中心原子 = ``AtomMapNum ∈ center_map_nums``(corpus 索引的
      ``center_atoms`` 即映射编号;缺席时退化为全部带映射原子,
      中心原子数 <2 拒绝)。
    取 RDKit GetSubstructMatches 的首个确定性匹配。
    返回 (match_map | None, strategy):match_map = {query_idx: current_idx}。
    """
    if donor_mol is None or current_mol is None:
        return None, None
    query = donor_mol
    if center_only:
        if center_map_nums:
            center_idx = [a.GetIdx() for a in donor_mol.GetAtoms()
                          if a.GetAtomMapNum() in set(center_map_nums)]
        else:
            center_idx = [a.GetIdx() for a in donor_mol.GetAtoms()
                          if a.GetAtomMapNum() > 0]
        if len(center_idx) < 2:
            return None, None
        query = Chem.RWMol()
        idx_map = {}
        for i in center_idx:
            idx_map[i] = query.AddAtom(Chem.Atom(donor_mol.GetAtomWithIdx(i)))
        for bond in donor_mol.GetBonds():
            bi, ei = bond.GetBeginAtomIdx(), bond.GetEndAtomIdx()
            if bi in idx_map and ei in idx_map:
                query.AddBond(idx_map[bi], idx_map[ei], bond.GetBondType())
        query = query.GetMol()
    matches = current_mol.GetSubstructMatches(query, uniquify=False,
                                              useChirality=False)
    if not matches:
        return None, None
    match = matches[0]  # RDKit 确定性顺序
    if center_only:
        # query 是重建子图:按构造位置回译为**原始供体原子 idx**
        orig_of_pos = {pos: orig for orig, pos in idx_map.items()}
        return ({orig_of_pos[pos]: cur for pos, cur in enumerate(match)},
                "deterministic_first_match")
    return ({d: c for d, c in enumerate(match)}, "deterministic_first_match")


def element_delta(substrate_smiles: str, product_smiles: str) -> dict:
    """重原子元素计数差 product - substrate(氢不计;多组分取并)。"""

    def heavy(smi: str) -> dict[str, int]:
        mol = Chem.MolFromSmiles(smi) if smi else None
        counts: dict[str, int] = {}
        if mol:
            for a in mol.GetAtoms():
                if a.GetSymbol() == "H":
                    continue
                counts[a.GetSymbol()] = counts.get(a.GetSymbol(), 0) + 1
        return counts

    sub, prod = heavy(substrate_smiles), heavy(product_smiles)
    delta: dict[str, int] = {}
    for el in sorted(set(sub) | set(prod)):
        d = prod.get(el, 0) - sub.get(el, 0)
        if d:
            delta[el] = d
    return delta


def identity_of(smiles: str) -> str | None:
    return cn_identity(smiles)
