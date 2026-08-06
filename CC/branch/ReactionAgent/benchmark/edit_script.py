"""编辑脚本层：把干净转化对 Xd>>Yd 抽成"可移植的键级图 diff"。

设计动机(对应 P0 诊断)：SMARTS 模板把 WHERE(定位) 与 WHAT(编辑) 耦合成一次精确
模式匹配，X≠donor 时不点火(72% not_generated)。本层把 WHAT 抽成与具体分子无关的
编辑签名(键级变化 / 原子增删)，供 align_transfer 做"模糊定位 + 编辑回放"，并给出一个
`EditScript.key()` —— 忽略具体原子编号、只保留"元素×键级变化"的可哈希签名，用于失败
归因：判定"检索到的 donor 里，有没有哪一个携带了与测试反应真值相同的变换"。

约定
  - 输入是 canonical 单片段对 (Xd, Yd)（来自 ci.transformed_pair，已剥离辅酶）。
  - 原子映射用 pipeline.mcs_atom_mapping(Xd>>Yd)，单反应物单产物 → 一份 r2p。
  - 键级用 GetBondTypeAsDouble(): 1.0/1.5(芳香)/2.0/3.0；无键记 0.0。
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from rdkit import Chem
from rdkit.Chem import rdFMCS
from rdkit import RDLogger

RDLogger.logger().setLevel(RDLogger.ERROR)

_ORDER2BT = {
    1.0: Chem.BondType.SINGLE,
    1.5: Chem.BondType.AROMATIC,
    2.0: Chem.BondType.DOUBLE,
    3.0: Chem.BondType.TRIPLE,
}


@dataclass
class BondDelta:
    a_idx: int           # Xd(反应物)原子编号
    b_idx: int
    a_elem: int
    b_elem: int
    order_from: float    # Xd 中键级(0=无键)
    order_to: float      # Yd 中键级(0=断键)


@dataclass
class AtomAdd:
    elem: int            # 新增原子元素(Yd 中相对 Xd 多出的原子)
    order: float         # 与锚点原子的键级
    attach_idx: int      # 锚点=Xd 反应物原子编号
    attach_elem: int


@dataclass
class EditScript:
    changed_atoms: List[int]              # Xd 中发生变化的反应物原子(键变端点 ∪ 增删锚点)
    bond_deltas: List[BondDelta] = field(default_factory=list)
    atom_adds: List[AtomAdd] = field(default_factory=list)
    atom_dels_idx: List[int] = field(default_factory=list)   # 离去原子(Xd 编号, 供回放定位删除)
    atom_dels_elem: List[int] = field(default_factory=list)  # 离去基团元素(用于签名)
    xd: str = ""
    yd: str = ""

    def is_empty(self) -> bool:
        return not (self.bond_deltas or self.atom_adds or self.atom_dels_elem)

    def key(self) -> Tuple:
        """与具体原子编号无关的变换签名(元素×键级变化)，用于'变换是否被检索到'的归因判定。"""
        bonds = tuple(sorted(
            (min(bd.a_elem, bd.b_elem), max(bd.a_elem, bd.b_elem), bd.order_from, bd.order_to)
            for bd in self.bond_deltas
        ))
        adds = tuple(sorted((a.elem, a.attach_elem, a.order) for a in self.atom_adds))
        dels = tuple(sorted(self.atom_dels_elem))
        return ("B", bonds, "A", adds, "D", dels)


def _diff_mapping(xm: Chem.Mol, ym: Chem.Mol) -> Dict[int, int]:
    """两个相似分子求最大原子对应(Xd idx -> Yd idx)；忽略键级(CompareAny)以便骨架尽量对齐，
    键级变化留给 delta 计算。元素必须一致(CompareElements)。"""
    try:
        mcs = rdFMCS.FindMCS(
            [xm, ym],
            atomCompare=rdFMCS.AtomCompare.CompareElements,
            bondCompare=rdFMCS.BondCompare.CompareAny,
            ringMatchesRingOnly=False,
            completeRingsOnly=False,
            matchValences=False,
            timeout=5,
        )
    except Exception:
        return {}
    if mcs.numAtoms < 2:
        return {}
    q = Chem.MolFromSmarts(mcs.smartsString)
    if q is None:
        return {}
    xmatch = xm.GetSubstructMatch(q)
    ymatch = ym.GetSubstructMatch(q)
    if not xmatch or not ymatch:
        return {}
    return {int(a): int(b) for a, b in zip(xmatch, ymatch)}


def extract_edit(xd: str, yd: str) -> Optional[EditScript]:
    """从干净转化对 (Xd, Yd) 抽取编辑脚本；无法解析/无变化返回 None。"""
    rmol = Chem.MolFromSmiles(xd)
    pmol = Chem.MolFromSmiles(yd)
    if rmol is None or pmol is None:
        return None
    r2p = _diff_mapping(rmol, pmol)
    if not r2p:
        return None
    p2r = {p: r for r, p in r2p.items()}

    es = EditScript(changed_atoms=[], xd=xd, yd=yd)
    changed = set()

    # 1) 键级变化 / 断键 / 成键(两端都被映射的原子对)
    mapped_r = sorted(r2p.keys())
    for i in range(len(mapped_r)):
        for j in range(i + 1, len(mapped_r)):
            a, b = mapped_r[i], mapped_r[j]
            bx = rmol.GetBondBetweenAtoms(a, b)
            by = pmol.GetBondBetweenAtoms(r2p[a], r2p[b])
            ox = bx.GetBondTypeAsDouble() if bx else 0.0
            oy = by.GetBondTypeAsDouble() if by else 0.0
            if ox != oy:
                es.bond_deltas.append(BondDelta(
                    a_idx=a, b_idx=b,
                    a_elem=rmol.GetAtomWithIdx(a).GetAtomicNum(),
                    b_elem=rmol.GetAtomWithIdx(b).GetAtomicNum(),
                    order_from=ox, order_to=oy))
                changed.update((a, b))

    # 2) 新增原子(Yd 中未被映射) —— 记录其挂到哪个(映射回 Xd 的)锚点原子
    for pa in range(pmol.GetNumAtoms()):
        if pa in p2r:
            continue
        for nb in pmol.GetAtomWithIdx(pa).GetNeighbors():
            if nb.GetIdx() in p2r:
                anchor_r = p2r[nb.GetIdx()]
                bd = pmol.GetBondBetweenAtoms(pa, nb.GetIdx())
                es.atom_adds.append(AtomAdd(
                    elem=pmol.GetAtomWithIdx(pa).GetAtomicNum(),
                    order=bd.GetBondTypeAsDouble() if bd else 1.0,
                    attach_idx=anchor_r,
                    attach_elem=rmol.GetAtomWithIdx(anchor_r).GetAtomicNum()))
                changed.add(anchor_r)

    # 3) 离去原子(Xd 中未映射到 Yd) —— 记编号(供回放删除)+元素(供签名)；锚点邻居计入变化
    for ra in range(rmol.GetNumAtoms()):
        if ra not in r2p:
            es.atom_dels_idx.append(ra)
            es.atom_dels_elem.append(rmol.GetAtomWithIdx(ra).GetAtomicNum())
            changed.add(ra)
            for nb in rmol.GetAtomWithIdx(ra).GetNeighbors():
                if nb.GetIdx() in r2p:
                    changed.add(nb.GetIdx())

    es.changed_atoms = sorted(changed)
    if es.is_empty():
        return None
    return es
