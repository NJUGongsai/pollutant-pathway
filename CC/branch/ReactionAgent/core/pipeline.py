"""
反应特征提取流水线：从已知反应中提取反应模板，应用到新底物上预测产物。

核心步骤：
  1. MCS 原子映射   — 建立底物原子 ↔ 产物原子的对应关系
  2. 反应中心提取   — 识别哪些原子在反应中发生了变化
  3. 反应模板提取   — 以反应中心为核心构建 SMARTS 反应规则
  4. 模板应用       — 在查询分子 X 上搜索匹配位点，生成候选产物

关键设计决策：
  - 仅对 MCS 中有双向对应的原子分配映射编号（RDKit 要求）
  - 单向独有的原子（消失/新生）保留为无编号的上下文模式
  - 非环境原子从 fragment 中删除以增强泛化能力
"""

import os
import pickle as pkl
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from rdkit import Chem
from rdkit.Chem import AllChem, rdFMCS, rdChemReactions
from rdkit import RDLogger

RDLogger.logger().setLevel(RDLogger.ERROR)


# ═══════════════════════════════════════════════════════════════════════════════
# Data classes
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class AtomMapping:
    reactant_idx: int
    product_idx: int
    r2p: Dict[int, int]
    mcs_smarts: str = ""
    mcs_num_atoms: int = 0


@dataclass
class ReactionCenter:
    reactant_indices: List[List[int]]
    product_indices: List[List[int]]


@dataclass
class TemplateResult:
    reaction_smarts: str
    reaction_obj: object = field(default=None)
    reactant_frags: List[str] = field(default_factory=list)
    product_frags: List[str] = field(default_factory=list)


@dataclass
class CandidateProduct:
    rank: int
    product_smiles: str
    matched_atoms: List[int] = field(default_factory=list)
    template_used: str = ""
    score: float = 0.0
    n_atoms: int = 0  # 候选产物原子总数(跨片段), 供 Phase3 逐候选打分


@dataclass
class PipelineResult:
    known_reaction: str
    atom_mappings: List[AtomMapping]
    reaction_center: ReactionCenter
    template: TemplateResult
    query_smiles: str
    candidates: List[CandidateProduct]


# ═══════════════════════════════════════════════════════════════════════════════
# 1. MCS 原子映射
# ═══════════════════════════════════════════════════════════════════════════════

def mcs_atom_mapping(rxn_smiles: str) -> List[AtomMapping]:
    """使用最大公共子结构 (MCS) 建立底物与产物间的原子映射。"""
    parts = rxn_smiles.split(">")
    if len(parts) < 3:
        raise ValueError(f"不是有效的反应 SMILES: {rxn_smiles}")

    reactant_smiles = [s for s in parts[0].split(".") if s]
    product_smiles = [s for s in parts[2].split(".") if s]
    reactant_mols = [Chem.MolFromSmiles(s) for s in reactant_smiles]
    product_mols = [Chem.MolFromSmiles(s) for s in product_smiles]

    mappings = []
    for i, r_mol in enumerate(reactant_mols):
        if r_mol is None:
            continue
        best_mapping, best_num, best_j, best_smarts = None, 0, -1, ""
        for j, p_mol in enumerate(product_mols):
            if p_mol is None:
                continue
            try:
                mcs = rdFMCS.FindMCS(
                    [r_mol, p_mol],
                    matchValences=True,
                    ringMatchesRingOnly=True,
                    completeRingsOnly=True,
                    timeout=5,
                )
            except Exception:
                continue
            if mcs.numAtoms < 3:
                continue
            mcs_mol = Chem.MolFromSmarts(mcs.smartsString)
            if mcs_mol is None:
                continue
            r_match = r_mol.GetSubstructMatch(mcs_mol)
            p_match = p_mol.GetSubstructMatch(mcs_mol)
            if not r_match or not p_match:
                continue
            r2p = {int(r_a): int(p_a) for r_a, p_a in zip(r_match, p_match)}
            if mcs.numAtoms > best_num:
                best_num, best_mapping, best_j, best_smarts = mcs.numAtoms, r2p, j, mcs.smartsString

        if best_mapping:
            mappings.append(AtomMapping(i, best_j, best_mapping, best_smarts, best_num))

    return mappings


# ═══════════════════════════════════════════════════════════════════════════════
# 2. 反应中心提取
# ═══════════════════════════════════════════════════════════════════════════════

def _atoms_are_different(atom1: Chem.Atom, atom2: Chem.Atom) -> bool:
    if atom1.GetAtomicNum() != atom2.GetAtomicNum(): return True
    if atom1.GetTotalNumHs() != atom2.GetTotalNumHs(): return True
    if atom1.GetFormalCharge() != atom2.GetFormalCharge(): return True
    if atom1.GetDegree() != atom2.GetDegree(): return True
    if atom1.GetIsAromatic() != atom2.GetIsAromatic(): return True

    def _neighbor_sigs(atom):
        sigs = []
        for bond in atom.GetBonds():
            other = bond.GetOtherAtom(atom)
            sigs.append((other.GetAtomicNum(), int(bond.GetBondType())))
        return sorted(sigs)

    return _neighbor_sigs(atom1) != _neighbor_sigs(atom2)


def extract_reaction_center(
    rxn_smiles: str, atom_mappings: List[AtomMapping]
) -> ReactionCenter:
    """从原子映射中提取反应中心（在反应中发生变化的原子）。"""
    parts = rxn_smiles.split(">")
    reactant_smiles = [s for s in parts[0].split(".") if s]
    product_smiles = [s for s in parts[2].split(".") if s]
    reactant_mols = [Chem.MolFromSmiles(s) for s in reactant_smiles]
    product_mols = [Chem.MolFromSmiles(s) for s in product_smiles]

    n_r, n_p = len(reactant_mols), len(product_mols)
    center_r = [set() for _ in range(n_r)]
    center_p = [set() for _ in range(n_p)]
    mapped_r = defaultdict(set)
    mapped_p = defaultdict(set)

    for am in atom_mappings:
        r_mol = reactant_mols[am.reactant_idx]
        p_mol = product_mols[am.product_idx]
        for r_idx, p_idx in am.r2p.items():
            mapped_r[am.reactant_idx].add(r_idx)
            mapped_p[am.product_idx].add(p_idx)
            if _atoms_are_different(r_mol.GetAtomWithIdx(r_idx), p_mol.GetAtomWithIdx(p_idx)):
                center_r[am.reactant_idx].add(r_idx)
                center_p[am.product_idx].add(p_idx)

    # 未映射（消失/新生）的原子
    for i, r_mol in enumerate(reactant_mols):
        if r_mol is not None:
            center_r[i].update(set(range(r_mol.GetNumAtoms())) - mapped_r.get(i, set()))
    for j, p_mol in enumerate(product_mols):
        if p_mol is not None:
            center_p[j].update(set(range(p_mol.GetNumAtoms())) - mapped_p.get(j, set()))

    return ReactionCenter(
        reactant_indices=[sorted(list(s)) for s in center_r],
        product_indices=[sorted(list(s)) for s in center_p],
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 3. 反应模板提取
# ═══════════════════════════════════════════════════════════════════════════════

def _get_env_atoms(mol: Chem.Mol, center: Set[int], radius: int) -> Set[int]:
    """获取反应中心周围 radius 层邻居原子。"""
    if radius <= 0:
        return set(center)
    env = set(center)
    frontier = set(center)
    for _ in range(radius):
        new_frontier = set()
        for idx in frontier:
            for nb in mol.GetAtomWithIdx(idx).GetNeighbors():
                if nb.GetIdx() not in env:
                    new_frontier.add(nb.GetIdx())
                    env.add(nb.GetIdx())
        frontier = new_frontier
        if not frontier:
            break
    return env


def _atom_query_smarts(atom: Chem.Atom) -> str:
    """把片段原子转成放宽 SMARTS 查询原子字符串。

    仅保留 元素 + 芳香性 + 形式电荷 + map 编号，去掉显式 H 数与度约束——
    因为片段是从整分子截断而来，切口原子会被 RDKit 补上错误的隐式 H，
    若照搬 H 计数（MolToSmiles 的行为）会导致模板匹配不上母分子（Phase2 不点火根因）。
    """
    z = atom.GetAtomicNum()
    if z == 0:
        base = "*"
    else:
        base = f"#{z}" + (";a" if atom.GetIsAromatic() else ";A")
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


def extract_template(
    rxn_smiles: str,
    reaction_center: ReactionCenter,
    radius: int = 1,
) -> TemplateResult:
    """
    从反应中心构建 SMARTS 反应模板。

    关键规则（遵循 RDKit reaction SMARTS 要求）：
      1. 仅对 MCS 中有双向对应的原子赋予映射编号（map number）
      2. 单向独有的原子（消失/新生）保留为无编号模式原子 → 泛化匹配
      3. 从分子中删除非环境原子 → fragment 模板
    """
    parts = rxn_smiles.split(">")
    reactant_smiles = [s for s in parts[0].split(".") if s]
    product_smiles = [s for s in parts[2].split(".") if s]
    reactant_mols = [Chem.MolFromSmiles(s) for s in reactant_smiles]
    product_mols = [Chem.MolFromSmiles(s) for s in product_smiles]

    mappings = mcs_atom_mapping(rxn_smiles)

    # Step A: 确定哪些原子需要分配映射编号
    # 规则：仅在 reactant 和 product 两侧都有对应（通过 MCS）时才编号
    r_has_map = {}  # (mol_idx, atom_idx) → map_number
    p_has_map = {}  # (mol_idx, atom_idx) → map_number
    map_counter = 1

    # 从 MCS 获取双向对应的原子对
    for am in mappings:
        for r_idx, p_idx in am.r2p.items():
            num = map_counter
            r_has_map[(am.reactant_idx, r_idx)] = num
            p_has_map[(am.product_idx, p_idx)] = num
            map_counter += 1

    # Step B: 确定每个分子中需要保留的环境原子（反应中心 + radius 邻居）
    kept_r = {}  # mol_idx → set of atom indices to keep
    for i, r_mol in enumerate(reactant_mols):
        if r_mol is None: continue
        r_center = set(reaction_center.reactant_indices[i]) if i < len(reaction_center.reactant_indices) else set()
        kept_r[i] = _get_env_atoms(r_mol, r_center, radius)

    kept_p = {}
    for j, p_mol in enumerate(product_mols):
        if p_mol is None: continue
        p_center = set(reaction_center.product_indices[j]) if j < len(reaction_center.product_indices) else set()
        kept_p[j] = _get_env_atoms(p_mol, p_center, radius)

    # Step C: 构建 fragment SMARTS（放宽查询原子）
    def _build_fragment(mols, kept_dict, map_dict, n_total):
        frags = []
        for i in range(n_total):
            if i >= len(mols) or mols[i] is None or i not in kept_dict:
                continue
            mol = Chem.RWMol(mols[i])
            n_atoms = mol.GetNumAtoms()
            keep = kept_dict[i]

            # 为保留的原子设置映射编号（如果有的话）
            for idx in range(n_atoms):
                if idx in keep and (i, idx) in map_dict:
                    mol.GetAtomWithIdx(idx).SetAtomMapNum(map_dict[(i, idx)])

            # 删除不保留的原子（逆序）
            for idx in sorted([a for a in range(n_atoms) if a not in keep], reverse=True):
                mol.RemoveAtom(idx)

            # 将每个原子替换为放宽 SMARTS 查询原子（去掉截断切口的 H 计数伪影，
            # 修复模板匹配不上母分子导致 Phase2 不点火的缺陷）
            for idx in range(mol.GetNumAtoms()):
                qa = Chem.AtomFromSmarts(_atom_query_smarts(mol.GetAtomWithIdx(idx)))
                if qa is not None:
                    mol.ReplaceAtom(idx, qa)
            try:
                frags.append(Chem.MolToSmarts(mol))
            except Exception as e:
                print(f"      [Warning] fragment SMARTS failed: {e}")
        return ".".join(frags)

    r_mapped = _build_fragment(reactant_mols, kept_r, r_has_map, len(reactant_mols))
    p_mapped = _build_fragment(product_mols, kept_p, p_has_map, len(product_mols))

    if not r_mapped or not p_mapped:
        raise ValueError("无法构建反应模板：反应物或产物侧为空")

    rxn_smarts = f"{r_mapped}>>{p_mapped}"
    try:
        rxn_obj = AllChem.ReactionFromSmarts(rxn_smarts)
        rxn_obj.Initialize()
    except Exception as e:
        print(f"      [Warning] SMARTS 创建失败: {e}")
        rxn_obj = None

    return TemplateResult(
        reaction_smarts=rxn_smarts,
        reaction_obj=rxn_obj,
        reactant_frags=r_mapped.split("."),
        product_frags=p_mapped.split("."),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 4. 模板应用
# ═══════════════════════════════════════════════════════════════════════════════

def apply_template_to_molecule(
    template: TemplateResult,
    query_smiles: str,
    co_reactants: Optional[List[str]] = None,
) -> List[CandidateProduct]:
    """将反应模板应用到查询分子 X 上，生成候选产物。"""
    if template.reaction_obj is None:
        return []

    mol = Chem.MolFromSmiles(query_smiles)
    if mol is None:
        raise ValueError(f"无效 SMILES: {query_smiles}")

    n_reactant_templates = template.reaction_obj.GetNumReactantTemplates()
    reactants = [mol]
    if co_reactants:
        for smi in co_reactants:
            co_mol = Chem.MolFromSmiles(smi)
            reactants.append(co_mol if co_mol is not None else Chem.MolFromSmiles("O"))

    while len(reactants) < n_reactant_templates:
        reactants.append(template.reaction_obj.GetReactantTemplate(len(reactants)))

    candidates = []
    try:
        results = template.reaction_obj.RunReactants(tuple(reactants))
    except Exception as e:
        print(f"      [Warning] RunReactants 失败: {e}")
        return []

    seen = set()
    for rank, prod_tuple in enumerate(results):
        smis = []
        reacting_atoms = []   # 该候选产物的反应中心原子(模板核心), 跨片段全局编号
        n_atoms_total = 0
        for p in prod_tuple:
            try:
                Chem.SanitizeMol(p)
                smis.append(Chem.MolToSmiles(p, isomericSmiles=True))
            except Exception:
                smis.append(Chem.MolToSmiles(p, isomericSmiles=False))
            # RunReactants 会给源自模板映射原子的产物原子打上 'old_mapno' → 视为反应中心
            for atom in p.GetAtoms():
                if atom.HasProp("old_mapno"):
                    reacting_atoms.append(n_atoms_total + atom.GetIdx())
            n_atoms_total += p.GetNumAtoms()
        ps = ".".join(sorted(smis))
        if ps not in seen:
            seen.add(ps)
            candidates.append(CandidateProduct(
                rank=rank + 1, product_smiles=ps,
                matched_atoms=reacting_atoms, n_atoms=n_atoms_total,
                template_used=template.reaction_smarts[:80] + "..."))
    return candidates


# ═══════════════════════════════════════════════════════════════════════════════
# 5. 完整流水线
# ═══════════════════════════════════════════════════════════════════════════════

def predict_products(
    known_reaction: str,
    query_smiles: str,
    co_reactants: Optional[List[str]] = None,
    template_radius: int = 1,
    verbose: bool = True,
    center_source: str = "auto",
) -> PipelineResult:
    """完整流水线：已知反应 A>>B + 查询分子 X → 预测 X 的可能产物。

    center_source: "auto" 优先晨羽真值否则回退 MCS; "chenyu" 只用晨羽真值(未命中则 None→报错回退);
                   "mcs" 强制用 MCS 反应中心。用于 A/B 对比 P0-b 影响。
    """
    if verbose:
        print("=" * 70)
        print("🔬 反应特征提取 & 产物预测流水线")
        print("=" * 70)

    if verbose:
        print(f"\n📌 Step 1/4: MCS 原子映射\n   已知反应: {known_reaction}")
    mappings = mcs_atom_mapping(known_reaction)
    if verbose:
        print(f"   找到 {len(mappings)} 个底物→产物映射")
        for am in mappings:
            print(f"     底物[{am.reactant_idx}] → 产物[{am.product_idx}]: "
                  f"{len(am.r2p)} atoms (MCS={am.mcs_num_atoms})")

    if verbose:
        print(f"\n📌 Step 2/4: 反应中心提取")
    # center_source 控制来源: auto=优先晨羽真值否则回退MCS; chenyu=只用真值; mcs=强制MCS
    center = None
    if center_source in ("auto", "chenyu"):
        try:
            from chenyu_features import reaction_center_from_chenyu
            center = reaction_center_from_chenyu(known_reaction)
            if center is not None and verbose:
                print(f"   ✅ 命中晨羽 reacting_center.pkl (真值反应中心)")
        except Exception:
            center = None
    if center is None:
        center = extract_reaction_center(known_reaction, mappings)
        if verbose:
            print(f"   ↩︎ {'强制' if center_source=='mcs' else '回退'} MCS 反应中心")
    if verbose:
        for i, idxs in enumerate(center.reactant_indices):
            if idxs: print(f"   底物[{i}] 反应中心原子: {idxs}")
        for j, idxs in enumerate(center.product_indices):
            if idxs: print(f"   产物[{j}] 反应中心原子: {idxs}")

    if verbose:
        print(f"\n📌 Step 3/4: 反应模板提取 (radius={template_radius})")
    template = extract_template(known_reaction, center, radius=template_radius)
    if verbose:
        print(f"   SMARTS: {template.reaction_smarts}")

    if verbose:
        print(f"\n📌 Step 4/4: 模板应用到 X\n   X = {query_smiles}")
    candidates = apply_template_to_molecule(template, query_smiles, co_reactants)
    if verbose:
        if candidates:
            print(f"   ✅ 找到 {len(candidates)} 个候选产物:")
            for c in candidates:
                print(f"     [{c.rank}] {c.product_smiles}")
        else:
            print(f"   ⚠️  未匹配（模板在 X 上找不到反应位点）")

    result = PipelineResult(known_reaction, mappings, center, template, query_smiles, candidates)
    if verbose:
        print("\n" + "=" * 70 + "\n✅ 流水线完成\n" + "=" * 70)
    return result
