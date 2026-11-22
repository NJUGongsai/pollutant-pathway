"""v44-Next v1.3 通用一步枚举器 + 断键碎片枚举器（T1-D，默认关闭）。

来源与边界
----------
参考 ``通用键型反应枚举器参考实现``
的 probe2（18 条通用一步 SMARTS）与 probe3（非环单键断裂 + -OH/-H 封端），
重写为可复用模块：

- **零 LLM / 零外部数据**：只用 RDKit 对底物做确定性枚举；
- **默认关闭**：仅当计划键 ``enable_v13_generic_enumeration`` 为真时，
  runflow 的 novel 编译失败回退才调用吸附（``adsorb_to_enumeration``）；
- **枚举清单不进提示词**（提示词零变化），因此吸附可在零调用下重放评估；
- **注入候选池**只保留开关语义（``enumerate_for_pool_injection``），
  本阶段不接入、不评估（会改变提示词，留待 T2 付费验证）。

候选来源
--------
1. ``ONE_STEP_RULES``：芳香/脂肪族 C-H 羟基化、醇→醛/酮、醛→酸、羰基
   还原、脱卤（水解/还原）、O-/N-/S-脱甲基、烯烃水合、环氧化、硝基还原、
   脱羧、硫醚/亚砜氧化、酯/酰胺水解；
2. ``enumerate_cleavage_fragments``：非环单键（酯/酰胺/醚/糖苷/C-N/C-S/
   C-C）断裂，两端分别补 ``-OH`` / ``-H``（含不对称组合）。

对外 API
--------
- :func:`enumerate_one_step` — 一步规则枚举（按规则分组）；
- :func:`enumerate_cleavage_fragments` — 断键碎片枚举；
- :func:`enumerate_candidates` — 合并去重（默认含断键）；
- :func:`adsorb_to_enumeration` — novel 目标产物吸附到最相近的合法枚举项；
- :func:`generic_enumeration_enabled` — 计划开关读取（默认 False）。
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Iterable

from rdkit import Chem, RDLogger
from rdkit.Chem import AllChem, DataStructs, rdMolDescriptors

RDLogger.DisableLog("rdApp.*")

ENUMERATOR_VERSION = "v13-generic-enumerator-1"
PLAN_FLAG = "enable_v13_generic_enumeration"

#: 18 条通用一步反应 SMARTS（probe2 原始清单，名称保持可追溯）。
ONE_STEP_RULES: tuple[tuple[str, str], ...] = (
    ("c_h_hydroxylation_aliphatic", "[C;H1,H2,H3:1]>>[C:1][OH]"),
    ("c_h_hydroxylation_aromatic", "[c;H1:1]>>[c:1][OH]"),
    ("alcohol_oxidation_carbonyl", "[C:1][OH]>>[C:1]=O"),
    ("aldehyde_oxidation_acid", "[CH1:1]=O>>[C:1](=O)[OH]"),
    ("dehalogenation_hydrolysis", "[c,C:1][Cl,Br,I:2]>>[C:1][OH]"),
    ("dehalogenation_reductive", "[c,C:1][Cl,Br,I:2]>>[#6:1]"),
    ("o_demethylation", "[O:1][CH3:2]>>[OH:1]"),
    ("n_demethylation", "[N:1][CH3:2]>>[NH:1]"),
    ("s_demethylation", "[S:1][CH3:2]>>[SH:1]"),
    ("olefin_hydration", "[C:1]=[C:2]>>[C:1]([OH])[C:2]"),
    ("olefin_epoxidation", "[C:1]=[C:2]>>[C:1]1O[C:2]1"),
    ("nitro_reduction", "[N+:1](=[O:2])[O-:3]>>[N:1]"),
    ("carbonyl_reduction", "[C:1](=[O:2])>>[C:1]([OH])"),
    ("decarboxylation", "[c,C:1][C:2](=O)[OH]>>[#6:1]"),
    ("ester_hydrolysis",
     "[c,C:1](=O)[O:2][c,C:3]>>[C:1](=O)[OH].[O:2][C:3]"),
    ("amide_hydrolysis",
     "[c,C:1](=O)[N:2][c,C:3]>>[C:1](=O)[OH].[N:2][C:3]"),
    ("sulfide_oxidation", "[S;D2:1]>>[S:1]=O"),
    ("sulfoxide_oxidation", "[S:1]=O>>[S:1](=O)=O"),
)

MAX_CANDIDATES_PER_QUESTION = 400
ADSORPTION_MIN_SIMILARITY = 0.55


@dataclass
class EnumerationResult:
    """单题枚举结果（候选为 isomeric canonical SMILES，确定性排序）。"""

    substrate_smiles: str
    candidates: list[str] = field(default_factory=list)
    by_rule: dict[str, list[str]] = field(default_factory=dict)
    truncated: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "substrate_smiles": self.substrate_smiles,
            "candidates": list(self.candidates),
            "by_rule": {k: list(v) for k, v in self.by_rule.items()},
            "truncated": bool(self.truncated),
            "version": ENUMERATOR_VERSION,
        }


def generic_enumeration_enabled(plan: dict | None) -> bool:
    """计划开关（默认关闭）。"""
    return bool((plan or {}).get(PLAN_FLAG, False))


def _canonical(mol: Chem.Mol) -> str:
    return Chem.MolToSmiles(mol, isomericSmiles=True)


def _safe_mol(smiles: str):
    if not smiles:
        return None
    try:
        mol = Chem.MolFromSmiles(smiles)
    except Exception:  # noqa: BLE001 —— 坏 SMILES 一律当不可枚举
        return None
    if mol is None:
        return None
    try:
        Chem.SanitizeMol(mol)
    except Exception:  # noqa: BLE001
        return None
    return mol


def _compiled_rules():
    rules = []
    for name, smarts in ONE_STEP_RULES:
        try:
            rules.append((name, AllChem.ReactionFromSmarts(smarts)))
        except Exception:  # noqa: BLE001 —— 单条规则坏不拖垮整表
            continue
    return rules


_RULES_CACHE = None


def _rules():
    global _RULES_CACHE
    if _RULES_CACHE is None:
        _RULES_CACHE = _compiled_rules()
    return _RULES_CACHE


def enumerate_one_step(
    substrate_smiles: str, *, max_candidates: int = MAX_CANDIDATES_PER_QUESTION
) -> EnumerationResult:
    """一步规则枚举；按规则名分组，输出 isomeric canonical SMILES。"""
    result = EnumerationResult(substrate_smiles=str(substrate_smiles or ""))
    mol = _safe_mol(result.substrate_smiles)
    if mol is None:
        return result
    seen: set[str] = set()
    for name, rxn in _rules():
        out: set[str] = set()
        try:
            product_sets = rxn.RunReactants((mol,))
        except Exception:  # noqa: BLE001
            product_sets = ()
        for products in product_sets:
            for product in products:
                try:
                    Chem.SanitizeMol(product)
                    smiles = _canonical(product)
                except Exception:  # noqa: BLE001
                    continue
                if not smiles or smiles == result.substrate_smiles:
                    continue
                out.add(smiles)
                if len(seen | out) >= max_candidates:
                    result.truncated = True
                    break
            if result.truncated:
                break
        if out:
            result.by_rule[name] = sorted(out)
            seen.update(out)
        if result.truncated:
            break
    result.candidates = sorted(seen)
    return result


def _cap_fragment(fragment: Chem.Mol, dummy_idx: int, cap: str):
    """把 dummy 原子替换为 -H / -OH；返回 SMILES 或 None。"""
    rw = Chem.RWMol(fragment)
    atom = rw.GetAtomWithIdx(dummy_idx)
    if atom.GetAtomicNum() != 0:
        return None
    neighbors = list(atom.GetNeighbors())
    if not neighbors:
        return None
    if cap == "H":
        rw.RemoveAtom(dummy_idx)
    elif cap == "OH":
        atom.SetAtomicNum(8)
        atom.SetFormalCharge(0)
        atom.SetIsotope(0)
        atom.SetNumExplicitHs(1)
        atom.SetNoImplicit(False)
    else:  # pragma: no cover - 调用方只传两种
        return None
    try:
        mol = rw.GetMol()
        Chem.SanitizeMol(mol)
        return _canonical(mol)
    except Exception:  # noqa: BLE001
        return None


def enumerate_cleavage_fragments(
    substrate_smiles: str, *, max_candidates: int = MAX_CANDIDATES_PER_QUESTION
) -> EnumerationResult:
    """非环单键断裂：两端分别补 -OH / -H（含不对称组合）。"""
    result = EnumerationResult(substrate_smiles=str(substrate_smiles or ""))
    mol = _safe_mol(result.substrate_smiles)
    if mol is None:
        return result
    bonds = []
    for bond in mol.GetBonds():
        if bond.IsInRing() or bond.GetBondType() != Chem.BondType.SINGLE:
            continue
        begin, end = bond.GetBeginAtom(), bond.GetEndAtom()
        if begin.GetAtomicNum() > 1 and end.GetAtomicNum() > 1:
            bonds.append(bond.GetIdx())
    fragments: set[str] = set()
    for bond_idx in bonds:
        try:
            broken = Chem.FragmentOnBonds(
                mol, [bond_idx], addDummies=True, dummyLabels=[(1, 1)])
            parts = Chem.GetMolFrags(broken, asMols=True)
        except Exception:  # noqa: BLE001
            continue
        for part in parts:
            dummy_indices = [
                a.GetIdx() for a in part.GetAtoms() if a.GetAtomicNum() == 0
            ]
            if len(dummy_indices) != 1:
                continue
            for cap in ("H", "OH"):
                smiles = _cap_fragment(part, dummy_indices[0], cap)
                if not smiles or smiles == result.substrate_smiles:
                    continue
                fragments.add(smiles)
                if len(fragments) >= max_candidates:
                    result.truncated = True
                    break
            if result.truncated:
                break
        if result.truncated:
            break
    result.candidates = sorted(fragments)
    if fragments:
        result.by_rule["bond_cleavage_hydrolysis_caps"] = sorted(fragments)
    return result


def enumerate_candidates(
    substrate_smiles: str,
    *,
    include_cleavage: bool = True,
    max_candidates: int = MAX_CANDIDATES_PER_QUESTION,
) -> EnumerationResult:
    """合并一步规则 + 断键碎片（去重、确定性排序）。"""
    one = enumerate_one_step(substrate_smiles, max_candidates=max_candidates)
    merged = dict(one.by_rule)
    candidates = set(one.candidates)
    truncated = bool(one.truncated)
    if include_cleavage:
        cleavage = enumerate_cleavage_fragments(
            substrate_smiles, max_candidates=max_candidates)
        candidates.update(cleavage.candidates)
        if cleavage.candidates:
            merged["bond_cleavage_hydrolysis_caps"] = list(
                cleavage.candidates)
        truncated = truncated or bool(cleavage.truncated)
    ordered = sorted(candidates)[: int(max_candidates)]
    return EnumerationResult(
        substrate_smiles=str(substrate_smiles or ""),
        candidates=ordered,
        by_rule=merged,
        truncated=truncated or len(candidates) > len(ordered),
    )


def _morgan(mol: Chem.Mol):
    return AllChem.GetMorganFingerprintAsBitVect(mol, 2, nBits=2048)


def tanimoto(mol_a: Chem.Mol, mol_b: Chem.Mol) -> float:
    return float(DataStructs.TanimotoSimilarity(
        _morgan(mol_a), _morgan(mol_b)))


def _formula(smiles: str) -> str:
    mol = _safe_mol(smiles)
    return rdMolDescriptors.CalcMolFormula(mol) if mol is not None else ""


def adsorb_to_enumeration(
    substrate_smiles: str,
    target_smiles: str,
    *,
    min_similarity: float = ADSORPTION_MIN_SIMILARITY,
    include_cleavage: bool = True,
    max_candidates: int = MAX_CANDIDATES_PER_QUESTION,
) -> dict[str, Any] | None:
    """把 novel 目标产物吸附到枚举清单中最相近的合法产物。

    判据：与目标产物的 Morgan(r=2, 2048) Tanimoto 最大者；低于
    ``min_similarity`` 返回 ``None``（宁缺毋滥，不做强行改写）。
    同分时按 SMILES 字典序取小，保证确定性。
    """
    target = _safe_mol(str(target_smiles or ""))
    if target is None:
        return None
    enumerated = enumerate_candidates(
        substrate_smiles,
        include_cleavage=include_cleavage,
        max_candidates=max_candidates,
    )
    best = None
    best_key = None
    for smiles in enumerated.candidates:
        mol = _safe_mol(smiles)
        if mol is None:
            continue
        similarity = tanimoto(mol, target)
        if not math.isfinite(similarity):
            continue
        key = (similarity, smiles)
        if best_key is None or key > best_key:
            best_key, best = key, smiles
    if best is None or best_key[0] < float(min_similarity):
        return None
    return {
        "adsorbed_smiles": best,
        "similarity": round(best_key[0], 6),
        "target_smiles": str(target_smiles or ""),
        "target_formula": _formula(str(target_smiles or "")),
        "adsorbed_formula": _formula(best),
        "version": ENUMERATOR_VERSION,
    }


def enumerate_for_pool_injection(
    substrate_smiles: str, *, enabled: bool = False, **kw: Any
) -> EnumerationResult:
    """“注入候选池”开关占位：本阶段不接入（会改提示词），留待 T2。"""
    if not enabled:
        return EnumerationResult(substrate_smiles=str(substrate_smiles or ""))
    return enumerate_candidates(substrate_smiles, **kw)