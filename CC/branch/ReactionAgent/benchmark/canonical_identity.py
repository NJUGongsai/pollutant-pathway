"""Canonical 身份层：反应/分子的规范化、主片段选取、分组键。

P0 诚实评估的地基。所有"去重、防泄漏、命中判定"都建立在一致的 canonical 表示上，
避免同一化学实体因 SMILES 写法不同被当成两条数据（虚高的样本量 / 训练测试泄漏）。

约定
  - 反应串格式: "A>>B"，A/B 各为 '.' 连接的多片段底物串。
  - 主片段(main fragment): 一侧中"最大"的那个片段，代表被转化的主分子 X / 主产物 Y。
    "最大"定义为重原子数最多；打平则比碳原子数；再打平取 canonical SMILES 字典序最小(稳定)。
  - 分组键(group_key): (canon(主底物), canon(主产物))，用于把同一化学转化的不同酶/写法归为一组。
    fold 划分与酶家族泄漏排除都以 group_key 为单位。
"""
from functools import lru_cache
from typing import FrozenSet, List, Optional, Tuple

from rdkit import Chem
from rdkit import RDLogger

RDLogger.logger().setLevel(RDLogger.ERROR)


@lru_cache(maxsize=200000)
def canon_smiles(smi: str) -> Optional[str]:
    """单片段 SMILES → canonical SMILES；不可解析返回 None。"""
    if not smi:
        return None
    m = Chem.MolFromSmiles(smi)
    if m is None:
        return None
    return Chem.MolToSmiles(m)


def _split_side(side: str) -> List[str]:
    return [s for s in side.split(".") if s]


def canon_frags(side: str) -> FrozenSet[str]:
    """一侧 SMILES(可多片段) → 该侧 canonical 片段的 frozenset。

    注意: 集合表示会丢失计量数与重复片段，仅用于"集合层面"的比较；
    命中判定用 pick_main 的单主产物匹配，不依赖此集合。
    """
    out = set()
    for f in _split_side(side):
        c = canon_smiles(f)
        if c is not None:
            out.add(c)
    return frozenset(out)


def _heavy_and_carbon(smi: str) -> Tuple[int, int]:
    m = Chem.MolFromSmiles(smi)
    if m is None:
        return (0, 0)
    heavy = m.GetNumHeavyAtoms()
    carbon = sum(1 for a in m.GetAtoms() if a.GetAtomicNum() == 6)
    return (heavy, carbon)


def pick_main(side: str) -> Optional[str]:
    """从一侧中选主片段并返回其 canonical SMILES；无可解析片段返回 None。

    排序键: (重原子数, 碳原子数, canonical 字典序取反的稳定性) —— 取重原子最多者，
    打平比碳数，再打平取 canonical SMILES 最小者(保证确定性)。
    """
    best = None
    best_key = None
    for f in _split_side(side):
        c = canon_smiles(f)
        if c is None:
            continue
        heavy, carbon = _heavy_and_carbon(c)
        # 主键降序: 重原子↑ 碳↑; 尾键升序: canonical 字典序↑ (取负号无法对 str, 单独处理)
        key = (heavy, carbon)
        if best is None or key > best_key or (key == best_key and c < best):
            best, best_key = c, key
    return best


@lru_cache(maxsize=100000)
def canonical_reaction(rxn: str) -> Optional[str]:
    """整条反应 "A>>B" → canonical "A'>>B'"（每侧片段各自 canonical 后按字典序排序重组）。

    用于反应级去重。不可解析(缺 '>>' 或任一侧无有效片段)返回 None。
    """
    if ">>" not in rxn:
        return None
    r_side, p_side = rxn.split(">>", 1)
    r_frags = sorted(c for c in (canon_smiles(f) for f in _split_side(r_side)) if c)
    p_frags = sorted(c for c in (canon_smiles(f) for f in _split_side(p_side)) if c)
    if not r_frags or not p_frags:
        return None
    return ".".join(r_frags) + ">>" + ".".join(p_frags)


# ── 辅酶/无机小分子字典 (canonical SMILES, 数据驱动地从本语料高频片段提取) ──────
# 目的: 语料 97% 是多底物/辅酶耦合反应, 守恒的大辅酶(NADH/CoA)会被"最大片段"误当主底物。
# 剥离这些"公认的辅酶/能量-氧化还原载体/无机物", 再用反应中心锚定真正被转化的有机片段。
# 刻意【不】收录会二义的代谢物共底物(2-酮戊二酸/谷氨酸/丙酮酸/乙酰-CoA 等)——它们在某些
# 反应里就是目标底物本身; 由"反应中心 + 最大非辅酶片段"来选择, 而非一刀切剥离。
COFACTORS = frozenset({
    # 无机/小分子
    "O", "O=O", "O=C=O", "OO", "N", "[Fe+2]",
    # 磷酸 / 焦磷酸
    "O=P(O)(O)O", "O=P(O)(O)OP(=O)(O)O",
    # 腺苷磷酸 AMP/ADP/ATP
    "Nc1ncnc2c1ncn2[C@@H]1O[C@H](COP(=O)(O)O)[C@@H](O)[C@H]1O",
    "Nc1ncnc2c1ncn2[C@@H]1O[C@H](COP(=O)(O)OP(=O)(O)O)[C@@H](O)[C@H]1O",
    "Nc1ncnc2c1ncn2[C@@H]1O[C@H](COP(=O)(O)OP(=O)(O)OP(=O)(O)O)[C@@H](O)[C@H]1O",
    # NAD+ / NADH
    "NC(=O)c1ccc[n+]([C@@H]2O[C@H](COP(=O)(O)OP(=O)(O)OC[C@H]3O[C@@H](n4cnc5c(N)ncnc54)[C@H](O)[C@@H]3O)[C@@H](O)[C@H]2O)c1",
    "NC(=O)C1=CN([C@@H]2O[C@H](COP(=O)(O)OP(=O)(O)OC[C@H]3O[C@@H](n4cnc5c(N)ncnc54)[C@H](O)[C@@H]3O)[C@@H](O)[C@H]2O)C=CC1",
    # NADP+ / NADPH
    "NC(=O)c1ccc[n+]([C@@H]2O[C@H](COP(=O)(O)OP(=O)(O)OC[C@H]3O[C@@H](n4cnc5c(N)ncnc54)[C@H](OP(=O)(O)O)[C@@H]3O)[C@@H](O)[C@H]2O)c1",
    "NC(=O)C1=CN([C@@H]2O[C@H](COP(=O)(O)OP(=O)(O)OC[C@H]3O[C@@H](n4cnc5c(N)ncnc54)[C@H](OP(=O)(O)O)[C@@H]3O)[C@@H](O)[C@H]2O)C=CC1",
    # 游离 CoA
    "CC(C)(COP(=O)(O)OP(=O)(O)OC[C@H]1O[C@@H](n2cnc3c(N)ncnc32)[C@H](O)[C@@H]1OP(=O)(O)O)[C@@H](O)C(=O)NCCC(=O)NCCS",
    # SAM / SAH
    "C[S+](CC[C@H](N)C(=O)O)C[C@H]1O[C@@H](n2cnc3c(N)ncnc32)[C@H](O)[C@@H]1O",
    "Nc1ncnc2c1ncn2[C@@H]1O[C@H](CSCC[C@H](N)C(=O)O)[C@@H](O)[C@H]1O",
    # FAD / FADH2, FMN / FMNH2
    "Cc1cc2nc3c(=O)[nH]c(=O)nc-3n(C[C@H](O)[C@H](O)[C@H](O)COP(=O)(O)OP(=O)(O)OC[C@H]3O[C@@H](n4cnc5c(N)ncnc54)[C@H](O)[C@@H]3O)c2cc1C",
    "Cc1cc2c(cc1C)N(C[C@H](O)[C@H](O)[C@H](O)COP(=O)(O)OP(=O)(O)OC[C@H]1O[C@@H](n3cnc4c(N)ncnc43)[C@H](O)[C@@H]1O)c1[nH]c(=O)[nH]c(=O)c1N2",
    "Cc1cc2nc3c(=O)[nH]c(=O)nc-3n(C[C@H](O)[C@H](O)[C@H](O)COP(=O)(O)O)c2cc1C",
    "Cc1cc2c(cc1C)N(C[C@H](O)[C@H](O)[C@H](O)COP(=O)(O)O)c1[nH]c(=O)[nH]c(=O)c1N2",
    # 铁硫簇
    "[S]1[Fe+][S][Fe+]1", "[S]1[Fe][S][Fe+]1",
})


def _pick_transformed(side_smiles: str, per_frag_center: Optional[List[List[int]]],
                      exclude: FrozenSet[str]) -> Optional[str]:
    """从一侧选出"被转化的有机主片段"的 canonical SMILES。

    规则: 剔除 exclude(辅酶+光谱片段) 后, 优先取带反应中心原子的片段; 其中/其外再取重原子最多者
    (打平取 canonical 字典序最小)。per_frag_center 与 GetMolFrags 顺序对齐。
    """
    mol = Chem.MolFromSmiles(side_smiles)
    if mol is None:
        return None
    frag_mols = Chem.GetMolFrags(mol, asMols=True, sanitizeFrags=False)
    cands = []  # (canon_smi, has_center, heavy)
    for i, fm in enumerate(frag_mols):
        try:
            smi = Chem.MolToSmiles(fm)
        except Exception:
            continue
        if not smi or smi in exclude:
            continue
        has_center = per_frag_center is not None and i < len(per_frag_center) and len(per_frag_center[i]) > 0
        cands.append((smi, has_center, fm.GetNumHeavyAtoms()))
    if not cands:
        return None
    center_cands = [c for c in cands if c[1]]
    pool = center_cands if center_cands else cands
    pool.sort(key=lambda c: (-c[2], c[0]))
    return pool[0][0]


@lru_cache(maxsize=100000)
def transformed_pair(rxn: str) -> Optional[Tuple[str, str]]:
    """反应 → (被转化主底物 X, 被转化主产物 Y) 的 canonical 对；无法确定返回 None。

    辅酶剥离 + 反应中心锚定。X/Y 是 agent 的输入与命中判定真值的唯一权威来源。
    """
    if ">>" not in rxn:
        return None
    r_side, p_side = rxn.split(">>", 1)
    # 光谱片段(两侧原样出现且不变)也一并剔除
    spectators = canon_frags(r_side) & canon_frags(p_side)
    exclude = COFACTORS | spectators
    # 反应中心(逐片段, GetMolFrags 顺序); 未命中则 per_frag=None, 退化为最大非辅酶片段
    r_center = p_center = None
    try:
        from chenyu_features import reaction_center_from_chenyu
        center = reaction_center_from_chenyu(rxn)
        if center is not None:
            r_center, p_center = center.reactant_indices, center.product_indices
    except Exception:
        pass
    x = _pick_transformed(r_side, r_center, exclude)
    y = _pick_transformed(p_side, p_center, exclude)
    if x is None or y is None:
        return None
    return (x, y)


def group_key(rxn: str) -> Optional[Tuple[str, str]]:
    """反应 → 分组键 (X, Y)；同一 group_key 视为"同一化学转化"，是 fold 划分与泄漏排除的最小单位。"""
    return transformed_pair(rxn)


def main_substrate(rxn: str) -> Optional[str]:
    """被转化主底物 X 的 canonical SMILES —— agent 的输入。"""
    tp = transformed_pair(rxn)
    return tp[0] if tp else None


def main_product(rxn: str) -> Optional[str]:
    """被转化主产物 Y 的 canonical SMILES —— 命中判定的真值。"""
    tp = transformed_pair(rxn)
    return tp[1] if tp else None
