"""A 生成器：模糊位点对齐 + 编辑回放。

对应用户框架第⑤⑥步、并针对 P0 诊断(72% not_generated 源于 SMARTS 精确匹配不点火)：
  WHERE(定位): 不用精确 SMARTS 反应模板, 而是把 donor 反应中心的"变化原子+radius环境"
               做成【放宽原子查询】(元素+芳香+电荷, 去 H/度约束, 复用 pipeline._atom_query_smarts
               的思路)在 X 上做子结构匹配 → 得到 donor原子 ↔ X原子 的对应(可多位点)。
  WHAT(编辑):  把 edit_script 抽出的键级图 diff(键级变化/断键/成键/加原子/删离去基团)
               用 RWMol 直接【回放】到 X 对齐到的原子上, 而非 RunReactants。

好处: 定位靠"相似"而非"精确", X≠donor 时更易点火; 编辑是局部图操作, 绕开 SMARTS 显式H伪影;
      产物可解释(编辑脚本可打印)。失败/异常一律返回 [], 绝不让评估崩。
"""
from functools import lru_cache
from typing import Dict, List, Optional

from rdkit import Chem
from rdkit import RDLogger

RDLogger.DisableLog("rdApp.*")

import canonical_identity as ci
import edit_script as esmod
from edit_script import EditScript, _ORDER2BT

MAX_SITES = 4           # 每个 donor 在 X 上最多回放的对齐位点数(控组合爆炸)
LOC_RADIUS = 1          # 定位模式: 变化原子外扩的环境半径


def _atom_query(atom: Chem.Atom) -> str:
    """放宽原子查询: 元素(+芳香)+形式电荷, 去 H 数与度约束; 保留原子 map 号=donor 编号。"""
    z = atom.GetAtomicNum()
    base = "*" if z == 0 else (f"#{z}" + (";a" if atom.GetIsAromatic() else ";A"))
    chg = atom.GetFormalCharge()
    if chg == 1:
        base += ";+"
    elif chg > 1:
        base += f";+{chg}"
    elif chg == -1:
        base += ";-"
    elif chg < -1:
        base += f";-{abs(chg)}"
    mapno = atom.GetAtomMapNum()
    return "[" + base + (f":{mapno}" if mapno else "") + "]"


def _env_atoms(mol: Chem.Mol, seed, radius: int):
    env = set(seed)
    frontier = set(seed)
    for _ in range(radius):
        nxt = set()
        for idx in frontier:
            for nb in mol.GetAtomWithIdx(idx).GetNeighbors():
                if nb.GetIdx() not in env:
                    nxt.add(nb.GetIdx())
                    env.add(nb.GetIdx())
        frontier = nxt
        if not frontier:
            break
    return env


def _build_locator(xd: str, es: EditScript):
    """从 donor Xd 的(变化原子+环境)构建放宽 SMARTS 定位查询; 原子 map 号=donor Xd 编号。

    返回 (query_mol, mapnum→donor_idx)。失败返回 (None, None)。
    """
    rmol = Chem.MolFromSmiles(xd)
    if rmol is None or not es.changed_atoms:
        return None, None
    keep = _env_atoms(rmol, es.changed_atoms, LOC_RADIUS)
    rw = Chem.RWMol(rmol)
    # 打 map 号(= donor 原子编号+1, 避开 0)以便匹配后回溯对应关系
    for idx in range(rw.GetNumAtoms()):
        if idx in keep:
            rw.GetAtomWithIdx(idx).SetAtomMapNum(idx + 1)
    for idx in sorted([a for a in range(rw.GetNumAtoms()) if a not in keep], reverse=True):
        rw.RemoveAtom(idx)
    # 逐原子换成放宽查询原子
    frag = Chem.RWMol(rw)
    for idx in range(frag.GetNumAtoms()):
        qa = Chem.AtomFromSmarts(_atom_query(frag.GetAtomWithIdx(idx)))
        if qa is not None:
            frag.ReplaceAtom(idx, qa)
    try:
        smarts = Chem.MolToSmarts(frag)
        q = Chem.MolFromSmarts(smarts)
    except Exception:
        return None, None
    if q is None:
        return None, None
    map2donor = {}
    for qa in q.GetAtoms():
        mn = qa.GetAtomMapNum()
        if mn:
            map2donor[qa.GetIdx()] = mn - 1  # query原子序 → donor Xd 编号
    return q, map2donor


@lru_cache(maxsize=20000)
def _donor_edit(donor_rxn: str):
    """donor → (EditScript, locator_query, qidx→donor_idx); 缓存。任何失败返回 None。"""
    tp = ci.transformed_pair(donor_rxn)
    if tp is None:
        return None
    es = esmod.extract_edit(tp[0], tp[1])
    if es is None:
        return None
    q, m = _build_locator(tp[0], es)
    if q is None:
        return None
    return (es, q, m)


def _replay(x_mol: Chem.Mol, es: EditScript, donor2x: Dict[int, int]) -> Optional[str]:
    """把编辑脚本回放到 X 的对齐原子上, 返回产物 canonical SMILES; 失败返回 None。"""
    rw = Chem.RWMol(x_mol)
    # 1) 键级变化 / 断键 / 成键
    for bd in es.bond_deltas:
        if bd.a_idx not in donor2x or bd.b_idx not in donor2x:
            return None  # 端点未对齐 → 该位点无法忠实回放
        xa, xb = donor2x[bd.a_idx], donor2x[bd.b_idx]
        b = rw.GetBondBetweenAtoms(xa, xb)
        if bd.order_to == 0.0:
            if b is not None:
                rw.RemoveBond(xa, xb)
        elif bd.order_from == 0.0:
            if b is None:
                rw.AddBond(xa, xb, _ORDER2BT.get(bd.order_to, Chem.BondType.SINGLE))
        else:
            if b is not None:
                b.SetBondType(_ORDER2BT.get(bd.order_to, Chem.BondType.SINGLE))
    # 2) 加原子(挂到对齐锚点)
    for a in es.atom_adds:
        if a.attach_idx not in donor2x:
            return None
        new_idx = rw.AddAtom(Chem.Atom(a.elem))
        rw.AddBond(donor2x[a.attach_idx], new_idx, _ORDER2BT.get(a.order, Chem.BondType.SINGLE))
    # 3) 删离去原子(倒序删, 避免索引移位; 仅删对齐到的)
    del_x = sorted((donor2x[d] for d in es.atom_dels_idx if d in donor2x), reverse=True)
    for xi in del_x:
        rw.RemoveAtom(xi)
    # 收尾
    try:
        m = rw.GetMol()
        Chem.SanitizeMol(m)
        return Chem.MolToSmiles(m)
    except Exception:
        return None


def transfer(donor_rxn: str, query_x: str) -> List[str]:
    """A 生成器主入口: donor 反应的转化 → 施加到 X, 返回候选产物 SMILES(去重)。左侧只有 X。"""
    de = _donor_edit(donor_rxn)
    if de is None:
        return []
    es, q, map2donor = de
    xm = Chem.MolFromSmiles(query_x)
    if xm is None:
        return []
    try:
        matches = xm.GetSubstructMatches(q, uniquify=True, maxMatches=MAX_SITES * 3)
    except Exception:
        return []
    out, seen = [], set()
    for match in matches[:MAX_SITES * 3]:
        # match[i] = X 原子编号(对齐到 query 第 i 个原子); 借 map2donor 转成 donor→X
        donor2x = {}
        ok = True
        for qi, dai in map2donor.items():
            if qi >= len(match):
                ok = False
                break
            donor2x[dai] = match[qi]
        if not ok:
            continue
        prod = _replay(xm, es, donor2x)
        if prod is None:
            continue
        key = ".".join(sorted(ci.canon_frags(prod)))
        if key and key not in seen:
            seen.add(key)
            out.append(prod)
        if len(out) >= MAX_SITES:
            break
    return out
