# -*- coding: utf-8 -*-
"""s5_hybrid_choice.py — S1d + S5-all 混合候选池构建、化学先验多特征排序与 12 大类反应选择题引擎。

依据任务书：docs/tasks/active/TASK_S1D_S5_HYBRID_CHOICE_2026-11-09.md
红线约束：
1. 默认开关关闭时，现行 S0 候选池构建行为逐字节不变。
2. 严格复用 v4 身份函数 strict_identity_of，零 LLM 参与候选枚举、去重、分类与先验打分。
3. 支持按 12 受控反应大类进行类别均衡重排 (Class-Balanced Top-K) 及两阶段选择题卡片渲染。
"""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

from rdkit import Chem
from rdkit.Chem import AllChem

from pathway_v43.gold_health import HALOGENS, _analyze_side
from pathway_v43.pollutant.chemstate import strict_identity_of
from pathway_v43.domain.identity import cn_identity


# ============================================================================
# 1. 12 受控反应大类定义与确定性化学转化分类器
# ============================================================================

CONTROLLED_12_REACTION_CLASSES: tuple[tuple[str, str], ...] = (
    ("dehalogenation_or_halogenation", "脱卤/卤化反应 (Dehalogenation / Halogenation, ΔHal≠0)"),
    ("monooxygenation_hydroxylation", "单加氧/羟基化反应 (Monooxygenation / Hydroxylation, +1O)"),
    ("dioxygenation_dihydroxylation", "双加氧/二羟基化反应 (Dioxygenation / Dihydroxylation, +2O)"),
    ("dehydrogenation_oxidation", "脱氢/醇醛氧化反应 (Dehydrogenation / Oxidation, -2H or +O-2H)"),
    ("reduction_hydrogenation", "还原/加氢/脱氧反应 (Reduction / Hydrogenation, +2H or -O)"),
    ("hydration_or_dehydration", "水合/脱水裂合反应 (Hydration / Dehydration, ±H2O)"),
    ("ring_cleavage", "芳环/杂环开环裂解 (Ring Cleavage, ΔRing<0)"),
    ("decarboxylation_or_c1_cleavage", "脱羧/单碳裂解反应 (Decarboxylation / C1 Cleavage, ΔC=-1)"),
    ("beta_oxidation_or_c2_cleavage", "β-氧化/双碳裂解反应 (Beta-Oxidation / C2 Cleavage, ΔC=-2)"),
    ("hydrolysis_or_large_cleavage", "水解/C-O/C-N/C-C 骨架断裂 (Hydrolysis / Large Cleavage, ΔC≤-3)"),
    ("group_transfer_or_condensation", "基团转移/甲基化/糖基化/结合反应 (Group Transfer / Condensation, ΔC>0 or +N/P/S)"),
    ("isomerization_rearrangement", "异构化/互变异构/分子内重排 (Isomerization / Rearrangement, ΔFormula=0)"),
)

REACTION_CLASS_LABELS: dict[str, str] = dict(CONTROLLED_12_REACTION_CLASSES)

# T11:12 类**标准序**标签元组(路由提示词/解析校验/分层共享的单一来源;
# 只做索引与集合,不改变 CONTROLLED_12_REACTION_CLASSES 的定义序 —— 后者
# 是既有分类器/渲染的消费面,改动会漂移既有产物)。
REACTION_CLASS_12_LABELS: tuple[str, ...] = (
    "monooxygenation_hydroxylation",
    "dioxygenation_dihydroxylation",
    "dehydrogenation_oxidation",
    "reduction_hydrogenation",
    "dehalogenation_or_halogenation",
    "group_transfer_or_condensation",
    "decarboxylation_or_c1_cleavage",
    "beta_oxidation_or_c2_cleavage",
    "hydrolysis_or_large_cleavage",
    "hydration_or_dehydration",
    "ring_cleavage",
    "isomerization_rearrangement",
)
REACTION_CLASS_12_LABEL_SET: frozenset[str] = frozenset(
    REACTION_CLASS_12_LABELS)


def is_valid_reaction_class_12(label: str | None) -> bool:
    """标签是否属 12 类受控词表(严格小写原名;不做模糊归一)。"""
    return str(label or "") in REACTION_CLASS_12_LABEL_SET


@lru_cache(maxsize=65536)
def k_strict(smiles: str | None) -> str | None:
    if not smiles:
        return None
    try:
        return strict_identity_of(str(smiles))
    except Exception:
        return None


# ---- 论文消融 v1.4(2026-11-16,默认无调用者 ⇒ 零漂移)----
# 零金标 NoSelf 辅助:只消费题面底物 SMILES + 非金标题源反应标识
# 元数据(source reaction id / parent_reaction_ids / donor_smiles),
# 不读取 reference_graphs 或任何金标产物。
@lru_cache(maxsize=65536)
def _strip_atom_map_key(smiles: str | None) -> str | None:
    """去原子映射后的 canonical SMILES(strict/cn 身份比较前处理)。"""
    if not smiles:
        return None
    mol = Chem.MolFromSmiles(str(smiles))
    if mol is None:
        return None
    for atom in mol.GetAtoms():
        atom.SetAtomMapNum(0)
    try:
        return Chem.MolToSmiles(mol, isomericSmiles=True)
    except Exception:
        return None


def component_identity_sets(smiles: str | None) -> tuple[set[str], set[str]]:
    """(strict 组分身份集, cn 去质子组分身份集);零金标。"""
    text = str(smiles or "").strip()
    if not text:
        return set(), set()
    parts = [p for p in text.split(".") if p.strip()]
    strict: set[str] = set()
    cn: set[str] = set()
    for part in parts:
        stripped = _strip_atom_map_key(part) or part
        st = k_strict(stripped)
        if st:
            strict.add(st)
        try:
            cn_val = cn_identity(stripped)
        except Exception:
            cn_val = None
        if cn_val:
            cn.add(cn_val)
    return strict, cn


def question_source_ids(question_meta: dict | None) -> set[str]:
    """题源反应标识集合(非金标元数据;只用于 NoSelf 规则剔除)。"""
    meta = dict(question_meta or {})
    ids: set[str] = set()
    for key in ("reaction_id", "source_reaction_id", "source_id",
                "record_id"):
        value = meta.get(key)
        if value:
            ids.add(str(value))
    for key in ("source_reaction_ids", "reaction_ids"):
        raw = meta.get(key)
        if isinstance(raw, (list, tuple, set)):
            for item in raw:
                if item:
                    ids.add(str(item))
    return ids


def _same_component_set(smiles: str,
                        target_strict: set[str],
                        target_cn: set[str]) -> bool:
    """组分集合是否与目标(当前输入底物)严格或去质子身份全等。"""
    st, cn = component_identity_sets(smiles)
    if not st or not target_strict:
        return False
    return bool(st == target_strict or (cn and cn == target_cn))


def _shares_component(smiles: str,
                      target_strict: set[str],
                      target_cn: set[str]) -> bool:
    """左端组分是否包含当前输入底物(严格或去质子身份交集)。"""
    st, cn = component_identity_sets(smiles)
    if not st:
        return False
    return bool((st & target_strict) or (cn & target_cn))


def _parse_parent_reaction_ids(raw: Any) -> list[str]:
    """REACTIONS 列(逗号/分号分隔,可能含 URL)归一为标识列表。"""
    text = str(raw or "").strip()
    if not text:
        return []
    out: list[str] = []
    for token in text.replace(";", ",").split(","):
        token = token.strip()
        if not token:
            continue
        if "/reaction/" in token:
            token = token.rstrip("/").rsplit("/", 1)[-1]
        if token and token not in out:
            out.append(token)
    return out


def _env_rule_is_self(rule: dict, *, source_ids: set[str],
                      sub_strict: set[str],
                      sub_cn: set[str]) -> bool:
    """S5-env 单条规则的零金标自记录判定(EAWAG/enviPath)。"""
    rule_id = str(rule.get("rule_id") or "")
    if rule_id and rule_id in source_ids:
        return True
    family = str(rule.get("source_family") or "")
    if family == "eawag":
        reaction_id = str(rule.get("reaction_id") or "")
        if reaction_id and reaction_id in source_ids:
            return True
        donor = str(rule.get("donor_smiles") or "")
        if donor and _same_component_set(donor, sub_strict, sub_cn):
            return True
        return False
    parents = {str(x) for x in (rule.get("parent_reaction_ids") or [])}
    return bool(parents & source_ids)


def _rr_template_is_self(
        info: dict, *, source_ids: set[str],
        sub_strict: set[str], sub_cn: set[str]) -> bool:
    """S5-rr 单模板命中零金标自记录判定。

    判据(任务书 §1.2 DB-2 规则 4):parent_reaction_ids 命中题源反应
    ID;或所有支撑父反应的左端底物身份(严格/去质子组分集合)均等于
    当前输入底物(单样本特异规则)。
    """
    parents = {str(x) for x in (info.get("parent_reaction_ids") or [])}
    if parents & source_ids:
        return True
    lhs_list = [str(x) for x in (info.get("lhs_mapped_smiles") or [])
                if str(x).strip()]
    if not lhs_list:
        return False
    return all(_same_component_set(lhs, sub_strict, sub_cn)
               for lhs in lhs_list)


# ---- 论文消融 v1.4(2026-11-16):来源过滤参数化辅助(默认全 None ⇒ 零漂移)----
# 与上方 no_self/question_meta 旧接口并存:旧接口按"题源标识 + 组分身份"
# 自判定;新接口由调用方显式给 ``exclude_substrate_keys``(题卷底物严格
# 身份键)与 ``drop_rule_ids``(题源反应标识),便于池层统一归因计数。
# 两者默认 None ⇒ 不进入任何过滤分支,行为逐字节不变。


def _ablation_bump(stats: dict | None, key: str, n: int = 1) -> None:
    """过滤计数累加(stats=None ⇒ 无操作;零漂移)。"""
    if stats is None:
        return
    stats[key] = int(stats.get(key, 0)) + int(n)


def _split_strict_keys(smiles: str | None) -> set[str]:
    """映射/未映射 SMILES 的组分严格身份键集(不可解析 ⇒ 空集)。"""
    text = str(smiles or "").strip()
    if not text:
        return set()
    # 延迟导入:retro_source 依赖 retro_loader(numpy),只在过滤启用时加载。
    from pathway_v43.services.retro_source import _component_strict_keys

    return set(_component_strict_keys(text))


def _rule_lhs_strict_keys(
        lhs_values) -> tuple[set[str], bool]:
    """多值/单值 lhs SMILES ⇒ (组分严格键集, 是否至少有一条可用字段)。"""
    if isinstance(lhs_values, str):
        # 单字符串按**一条 SMILES**处理(不得逐字符迭代;resolver hit
        # 的 lhs_mapped_smiles 就是单字符串)。
        lhs_values = [lhs_values]
    keys: set[str] = set()
    available = False
    for value in lhs_values or ():
        text = str(value or "").strip()
        if not text:
            continue
        got = _split_strict_keys(text)
        if got:
            available = True
            keys |= got
    return keys, available


def _as_smiles_values(value) -> set[str]:
    """hit/规则字段 ⇒ SMILES 值集(字符串保整条,不拆字符)。"""
    if isinstance(value, str):
        return {value} if value.strip() else set()
    return {str(x) for x in (value or ()) if str(x).strip()}


def _env_rule_source_ids(rule: dict) -> set[str]:
    """S5-env 单规则的题源标识集合(非金标元数据字段)。"""
    ids: set[str] = set()
    for key in ("rule_id", "reaction_id", "btid"):
        value = str(rule.get(key) or "")
        if value:
            ids.add(value)
    for value in rule.get("parent_reaction_ids") or ():
        text = str(value or "")
        if text:
            ids.add(text)
    return ids


def _filter_rules_by_source(
        rules: list[dict[str, Any]], *,
        exclude_substrate_keys: set[str] | None = None,
        drop_rule_ids: set[str] | None = None,
        stats: dict | None = None,
        stats_prefix: str = "env",
        lhs_field: str = "donor_smiles",
        substrate_match: str = "equal") -> list[dict[str, Any]]:
    """规则级来源过滤(零金标;默认两个参数均 None ⇒ 原样返回)。

    - ``drop_rule_ids``:规则自身题源标识(rule_id/reaction_id/btid/
      parent_reaction_ids)命中 ⇒ 丢弃;
    - ``exclude_substrate_keys``:规则 ``lhs_field`` 的组分严格键集与
      题卷底物键集关系命中(``equal`` 全等 / ``superset`` 包含)⇒ 丢弃。
      字段不可得 ⇒ **不丢弃**,只累计 ``n_<prefix>_lhs_unavailable``,
      由调用方如实披露覆盖缺口(不得假装过滤)。
    """
    if not exclude_substrate_keys and not drop_rule_ids:
        return rules
    drop_ids = {str(x) for x in (drop_rule_ids or ()) if str(x)}
    sub_keys = {str(x) for x in (exclude_substrate_keys or ()) if str(x)}
    kept: list[dict[str, Any]] = []
    for rule in rules:
        if stats is not None:
            # 字段可得性覆盖(如实披露:有字段才可能按底物/父反应过滤)
            if rule.get("parent_reaction_ids"):
                _ablation_bump(
                    stats,
                    f"n_{stats_prefix}_parent_reaction_ids_available")
            if str(rule.get(lhs_field) or "").strip():
                _ablation_bump(
                    stats, f"n_{stats_prefix}_lhs_field_present")
        if drop_ids and (_env_rule_source_ids(rule) & drop_ids):
            _ablation_bump(stats, f"n_dropped_{stats_prefix}_rule_id")
            continue
        if sub_keys:
            raw_lhs = rule.get(lhs_field)
            lhs_values = (
                raw_lhs if isinstance(raw_lhs, (list, tuple, set))
                else [raw_lhs])
            lhs_keys, available = _rule_lhs_strict_keys(lhs_values)
            if not available:
                _ablation_bump(
                    stats, f"n_{stats_prefix}_lhs_unavailable")
            else:
                _ablation_bump(
                    stats, f"n_{stats_prefix}_lhs_available")
                hit = (lhs_keys == sub_keys
                       if substrate_match == "equal"
                       else sub_keys <= lhs_keys)
                if hit:
                    _ablation_bump(
                        stats, f"n_dropped_{stats_prefix}_substrate")
                    continue
        kept.append(rule)
    if stats is not None:
        stats[f"{stats_prefix}_lhs_field"] = str(lhs_field)
        stats[f"{stats_prefix}_substrate_match"] = str(substrate_match)
    return kept


def _filter_rr_template_agg(
        tpl_agg: dict[str, dict[str, Any]], *,
        exclude_substrate_keys: set[str] | None = None,
        drop_rule_ids: set[str] | None = None,
        stats: dict | None = None) -> dict[str, dict[str, Any]]:
    """S5-rr 模板聚合结果的来源过滤(零金标;默认 None ⇒ 原样返回)。

    索引 hit 只带**模板级** ``lhs_mapped_smiles``(父反应级 lhs 不在
    hit schema 内)⇒ 单样本特异判定按模板 lhs 组分键集包含题卷底物
    键集执行,并在 stats 如实标注 ``rr_per_parent_lhs_available``。
    """
    if not exclude_substrate_keys and not drop_rule_ids:
        return tpl_agg
    drop_ids = {str(x) for x in (drop_rule_ids or ()) if str(x)}
    sub_keys = {str(x) for x in (exclude_substrate_keys or ()) if str(x)}
    kept: dict[str, dict[str, Any]] = {}
    for tpl_str, info in tpl_agg.items():
        if stats is not None:
            if info.get("parent_reaction_ids"):
                _ablation_bump(
                    stats, "n_rr_parent_reaction_ids_available")
            if info.get("rule_ids"):
                _ablation_bump(stats, "n_rr_rule_ids_available")
            if info.get("lhs_mapped_smiles"):
                _ablation_bump(stats, "n_rr_lhs_field_present")
        if drop_ids:
            ids = {str(x) for x in (info.get("rule_ids") or ())}
            ids |= {str(x) for x in (
                info.get("parent_reaction_ids") or ())}
            if ids & drop_ids:
                _ablation_bump(stats, "n_dropped_rr_rule_id")
                continue
        if sub_keys:
            lhs_keys, available = _rule_lhs_strict_keys(
                info.get("lhs_mapped_smiles"))
            if not available:
                _ablation_bump(stats, "n_rr_lhs_unavailable")
            else:
                _ablation_bump(stats, "n_rr_lhs_available")
                if sub_keys <= lhs_keys:
                    _ablation_bump(stats, "n_dropped_rr_substrate")
                    continue
        kept[tpl_str] = info
    if stats is not None:
        stats["rr_lhs_scope"] = "template_level"
        stats["rr_template_lhs_available"] = True
        stats["rr_per_parent_lhs_available"] = False
    return kept


@lru_cache(maxsize=65536)
def _mol_profile(smiles: str) -> dict[str, Any] | None:
    if not smiles:
        return None
    parts = [p for p in str(smiles).split(".") if p]
    if not parts:
        return None
    side = _analyze_side(parts)
    if side["n_parse_fail"] > 0 or side["n_components"] == 0:
        return None
    m = Chem.MolFromSmiles(str(smiles))
    if m is None:
        return None
    return {
        "formula": dict(side["formula"]),
        "dou": side["dou"],
        "n_rings": m.GetRingInfo().NumRings(),
        "n_heavy": m.GetNumHeavyAtoms(),
        "n_atoms": m.GetNumAtoms(),
    }


def compute_formula_delta_str(sub_smiles: str, prod_smiles: str) -> str:
    """计算底物到候选主产物的可读原子变化字符串，如 '+O', '-Cl +O +H', '-C -2O'。"""
    sp = _mol_profile(sub_smiles)
    pp = _mol_profile(prod_smiles)
    if sp is None or pp is None:
        return "unknown"
    sf = sp["formula"]
    pf = pp["formula"]
    all_e = sorted(set(sf) | set(pf), key=lambda x: (0 if x == "C" else 1 if x == "H" else 2 if x == "O" else 3, x))
    tokens = []
    for e in all_e:
        d = pf.get(e, 0) - sf.get(e, 0)
        if d > 0:
            tokens.append(f"+{d if d > 1 else ''}{e}")
        elif d < 0:
            tokens.append(f"-{abs(d) if abs(d) > 1 else ''}{e}")
    return " ".join(tokens) if tokens else "Δ0(isomer)"


# ============================================================================
# 1b. v1.3 T13-A：Stage-1 引导的 w32 宽池抽池（`w32@20`）
# ============================================================================

# 桶配额默认档（只作用于**新增抽取**的尾部队列；``frozen_entries`` 是
# 保底全保留，不受配额限制）。分桶语义：
#   primary          = 条目 12 类 == 路由 primary_class
#   secondary        = 条目 12 类 ∈ 路由 secondary 类（且不等于 primary）
#   general_transform = 条目 12 类 == group_transfer_or_condensation
#                     （通用基团转移/结合类；非 primary/secondary 时单列）
#   other            = 其余（含类缺失/不可判）
STAGE1_GUIDED_POOL_DEFAULT_CAPS: dict[str, int] = {
    "primary": 6,
    "secondary": 3,
    "general_transform": 1,
    "other": 2,
}

_GENERAL_TRANSFORM_CLASS = "group_transfer_or_condensation"


def _guided_pool_entry_key(entry: dict) -> tuple[str, str]:
    """条目去重键：``(候选身份, 产物 SMILES)``（任务书口径）。

    候选身份优先 ``candidate_id``，退化到生产池 spec 的逻辑键 ``key``
    （``s5b_builder`` 池 spec 只带 ``key``，无 ``candidate_id`` —— 若
    只认前者，同产物的不同池条目会被误折叠，冻结池前缀保底即破）。
    产物侧优先 ``predicted_smiles``，其次 ``product_smiles``；两者都缺
    仍以空串参与键（同身份条目按原序各保留一条）。
    """
    ident = (entry.get("candidate_id") or entry.get("key")
             or entry.get("id") or entry.get("entry_id")
             or entry.get("transformation_ref") or "")
    return (
        str(ident),
        str(entry.get("predicted_smiles") or entry.get("product_smiles")
            or ""),
    )


def _guided_pool_bucket(entry: dict, primary: str,
                        secondary: frozenset[str]) -> str:
    """条目的桶归属（优先读既有 ``reaction_class_12``，缺省再分类）。

    分类需要底物；条目缺该类标签且未带底物字段时按 ``other`` 处理
    （不猜类别）。
    """
    label = str(entry.get("reaction_class_12") or "")
    if not is_valid_reaction_class_12(label):
        sub = str(entry.get("substrate_smiles")
                  or entry.get("substrate") or "")
        prod = str(entry.get("predicted_smiles")
                   or entry.get("product_smiles") or "")
        if sub and prod:
            try:
                label = str(classify_reaction_12class(sub, prod)[1])
            except Exception:  # noqa: BLE001 —— 不可判 ⇒ other（不猜）
                label = ""
        else:
            label = ""
    if primary and label == primary:
        return "primary"
    if label and label in secondary:
        return "secondary"
    if label == _GENERAL_TRANSFORM_CLASS:
        return "general_transform"
    return "other"


def select_stage1_guided_pool(
    w32_entries: list[dict],
    frozen_entries: list[dict],
    routing: dict | None,
    max_pool: int = 20,
    bucket_caps: dict[str, int] | None = None,
) -> list[dict]:
    """T13-A：从 ``w32`` 放大池 + 冻结参考池抽 ``w32@20`` 宽池。

    规则（零删除、确定性、不改输入对象）::

      1. ``frozen_entries`` **保底全保留**（按 ``(candidate_id, 产物)``
         去重，首次出现为准）—— 冻结池（@16）是生产口径基线，先占前
         缀 ⇒ ``@16`` 前缀与冻结池逐对象一致（GIP@16 零损失）。
      2. ``routing`` 含有效 primary/secondary 类时：在剩余槽位内按
         ``w32_entries`` **原序**逐条抽桶，每桶不超过 ``bucket_caps``
         （默认 ``{"primary": 6, "secondary": 3, "general_transform": 1,
         "other": 2}``）；桶归属优先读条目既有 ``reaction_class_12``，
         缺省再经 ``classify_reaction_12class``（条目须带底物字段）。
      3. 并集后仍不足 ``max_pool`` ⇒ 按 ``w32_entries`` 原序回填。
      4. ``routing`` 为 ``None`` 或无有效类（如 298 域）⇒ 退化：
         ``frozen_entries`` 保底 + 按 ``w32`` 原序回填至 ``max_pool``
         （等价 ``w32 ∪ frozen`` 截断至 ``max_pool``，冻结池优先）。
      5. 返回**新字典**列表，``pool_rank`` 重编号为 ``1..len(out)``；
         输入对象不修改。

    容量保证：``len(frozen_entries) <= max_pool`` 时 ``len(out) <=
    max_pool`` 且 ``frozen_entries`` 一条不丢；``frozen_entries`` 本身
    超宽（> ``max_pool``）时保守截断到 ``max_pool``（只披露、不越界）。
    配额只作用于**新增抽取**的尾部条目，不限制冻结池。
    """
    limit = int(max_pool)
    if limit <= 0:
        return []
    caps: dict[str, int] = dict(STAGE1_GUIDED_POOL_DEFAULT_CAPS)
    for key, value in (bucket_caps or {}).items():
        try:
            caps[str(key)] = max(0, int(value))
        except (TypeError, ValueError):
            continue

    has_pool_rank = any(
        isinstance(e, dict) and ("pool_rank" in e)
        for e in list(frozen_entries or []) + list(w32_entries or [])
    )

    def _finalize(items: list[dict]) -> list[dict]:
        out_rows: list[dict] = []
        for idx, entry in enumerate(items[:limit], 1):
            row = dict(entry)
            if has_pool_rank or "pool_rank" in row:
                row["pool_rank"] = idx
            out_rows.append(row)
        return out_rows

    frozen_out: list[dict] = []
    frozen_keys: set[tuple[str, str]] = set()
    for entry in (frozen_entries or []):
        if not isinstance(entry, dict):
            continue
        dedupe_key = _guided_pool_entry_key(entry)
        if dedupe_key in frozen_keys:
            continue
        frozen_keys.add(dedupe_key)
        frozen_out.append(dict(entry))
    if len(frozen_out) >= limit:
        # 冻结池本身已超宽：只保留前 limit 条（保守截断，不越界）。
        return _finalize(frozen_out)

    primary, secondary_tuple = _guided_routing_classes(routing)
    guided = bool(primary or secondary_tuple)
    secondary = frozenset(secondary_tuple)

    picked: list[dict] = []
    picked_keys: set[tuple[str, str]] = set(frozen_keys)
    bucket_used: dict[str, int] = {name: 0 for name in caps}
    gap = limit - len(frozen_out)

    if guided:
        for entry in (w32_entries or []):
            if len(picked) >= gap:
                break
            if not isinstance(entry, dict):
                continue
            dedupe_key = _guided_pool_entry_key(entry)
            if dedupe_key in picked_keys:
                continue
            bucket = _guided_pool_bucket(entry, primary, secondary)
            if bucket_used.get(bucket, 0) >= int(caps.get(bucket, 0)):
                continue
            bucket_used[bucket] = bucket_used.get(bucket, 0) + 1
            picked_keys.add(dedupe_key)
            picked.append(dict(entry))

    out = frozen_out + picked
    if len(out) < limit:
        # 回填：w32 原序（guided 分支里桶配额已用尽/可用条目不足时
        # 仍按原序补满；routing 缺失时本步即 w32 ∪ frozen 截断）。
        for entry in (w32_entries or []):
            if len(out) >= limit:
                break
            if not isinstance(entry, dict):
                continue
            dedupe_key = _guided_pool_entry_key(entry)
            if dedupe_key in picked_keys:
                continue
            picked_keys.add(dedupe_key)
            out.append(dict(entry))

    return _finalize(out)


def _guided_routing_classes(
        routing: dict | None) -> tuple[str, tuple[str, ...]]:
    """归一路由类（复用 T13-B 的 12 类校验；无效 ⇒ 空）。"""
    from .consensus_v13 import routing_classes

    return routing_classes(routing)


def classify_reaction_12class(sub_smiles: str, prod_smiles: str) -> tuple[str, str]:
    """确定性判定 (底物 -> 候选产物) 的 (coarse_6class, fine_12class)。"""
    sp = _mol_profile(sub_smiles)
    pp = _mol_profile(prod_smiles)
    if sp is None or pp is None:
        return ("other_unknown", "other_unknown")

    sf = sp["formula"]
    pf = pp["formula"]
    all_e = set(sf) | set(pf)
    delta = {e: pf.get(e, 0) - sf.get(e, 0) for e in all_e}

    dc = delta.get("C", 0)
    do = delta.get("O", 0)
    dh = delta.get("H", 0)
    dn = delta.get("N", 0)
    ds = delta.get("S", 0)
    dp = delta.get("P", 0)
    dhal = sum(delta.get(x, 0) for x in HALOGENS)
    d_other_heavy = sum(
        abs(v)
        for e, v in delta.items()
        if e not in ({"C", "H", "O"} | HALOGENS)
    )
    drings = pp["n_rings"] - sp["n_rings"]

    if dhal != 0:
        return ("halogenation_dehalogenation", "dehalogenation_or_halogenation")

    if all(v == 0 for v in delta.values()):
        if drings < 0:
            return ("isomerase_rearrangement", "ring_cleavage")
        return ("isomerase_rearrangement", "isomerization_rearrangement")

    if dc == 0 and d_other_heavy == 0:
        if (do == 1 and dh == 2) or (do == -1 and dh == -2):
            fine = "ring_cleavage" if drings < 0 else "hydration_or_dehydration"
            return ("lyase_hydration_decarboxylation", fine)
        if drings < 0:
            return ("oxidoreductase_oxygenation_redox", "ring_cleavage")
        if do == 1 and dh == 0:
            return ("oxidoreductase_oxygenation_redox", "monooxygenation_hydroxylation")
        if do == 2 and dh in (0, 2):
            return ("oxidoreductase_oxygenation_redox", "dioxygenation_dihydroxylation")
        if (do == 0 and dh < 0) or (do > 0 and dh < 0):
            return ("oxidoreductase_oxygenation_redox", "dehydrogenation_oxidation")
        if (do == 0 and dh > 0) or (do < 0 and dh >= 0):
            return ("oxidoreductase_oxygenation_redox", "reduction_hydrogenation")
        return ("oxidoreductase_oxygenation_redox", "dehydrogenation_oxidation")

    if dc > 0 or dn > 0 or dp > 0 or ds > 0:
        return ("transferase_group_transfer", "group_transfer_or_condensation")

    if dc == -1:
        if do == -2 and dh == 0 and d_other_heavy == 0:
            return ("lyase_hydration_decarboxylation", "decarboxylation_or_c1_cleavage")
        return ("hydrolase_cleavage", "decarboxylation_or_c1_cleavage")
    if dc == -2:
        return ("hydrolase_cleavage", "beta_oxidation_or_c2_cleavage")
    return ("hydrolase_cleavage", "hydrolysis_or_large_cleavage")


# ============================================================================
# 2. 统一候选数据结构与多特征化学先验打分器 (Chemical Prior Ranker)
# ============================================================================


@dataclass
class HybridCandidate:
    cand_strict: str
    cand_smiles: str
    sub_smiles: str
    outcome_sets: set[frozenset[str]] = field(default_factory=set)
    # 通道与来源统计
    source_families: set[str] = field(default_factory=set)  # {'recorded', 'corpus', 'analog', 'envipath', 'eawag', 'rr_rhea', 'rr_mnx'}
    s1d_best_rank: int | None = None
    s1d_best_sim: float = 0.0
    s1d_channels: set[str] = field(default_factory=set)
    s1d_is_self: bool = False
    # S5 规则统计
    env_rule_ids: set[str] = field(default_factory=set)
    env_freq_sum: int = 0
    env_non_self_count: int = 0
    rr_rule_ids: set[str] = field(default_factory=set)
    rr_max_radius: int = 0
    rr_radii: set[int] = field(default_factory=set)
    rr_datasets: set[str] = field(default_factory=set)
    rr_freq_sum: int = 0
    rr_max_freq: int = 0
    rr_non_self_count: int = 0
    all_sources_self_only: bool = True
    # 化学转化特征
    coarse_cat: str = "other_unknown"
    fine_cat: str = "other_unknown"
    formula_delta: str = ""
    heavy_atom_ratio: float = 1.0
    prior_score: float = 0.0
    prior_tier: str = "EXPLORATORY"


def compute_chemical_prior_score(
    cand: HybridCandidate,
    domain: str = "biosysmodb121",
    prefer_ex_self: bool = False,
) -> float:
    """计算零 LLM 化学先验多特征得分。

    设计原则：
    1. 跨源独立共识 (Multi-Source Consensus) 权重最高：当类比通道、环境规则、代谢规则中
       有 >=2 个独立家族指向同一严格化学产物时，几乎必为高置信主反应产物。
    2. 区分题域先验：
       - biosysmodb121（环境降解）：优先 enviPath/EAWAG 规则与高相似类比，其次 RetroRules r=6,4；
       - dev-298（通用酶学）：优先高相似类比/recorded 与 RetroRules r=6,4 高频代谢规则。
    3. 惩罚微小裂解碎片（如单碳/双原子脱离物被误选为主产物）与过小半径 r=2 的孤立噪声。
    """
    dom_norm = str(domain or "").strip().lower()
    if dom_norm in ("298", "dev-298", "dev298", "rhea"):
        domain_eff = "dev-298"
    else:
        domain_eff = "biosysmodb121"

    score = 0.0

    # 1. 独立来源家族共识数（把 rr_rhea 与 rr_mnx 归为 rr 家族，envipath 与 eawag 归为 env 家族）
    macro_families: set[str] = set()
    if "recorded" in cand.source_families and not prefer_ex_self:
        macro_families.add("recorded")
    if "corpus" in cand.source_families:
        macro_families.add("corpus")
    if "analog" in cand.source_families:
        macro_families.add("analog")
    if "envipath" in cand.source_families or "eawag" in cand.source_families:
        macro_families.add("s5_env")
    if "rr_rhea" in cand.source_families or "rr_mnx" in cand.source_families:
        macro_families.add("s5_rr")

    n_macro = len(macro_families)
    if n_macro >= 3:
        score += 65.0
    elif n_macro == 2:
        score += 38.0

    # 2. S1d 通道贡献（recorded / corpus / analog）
    if cand.s1d_channels:
        if "recorded" in cand.s1d_channels and not prefer_ex_self:
            score += 55.0
        if "analog" in cand.s1d_channels:
            sim = cand.s1d_best_sim
            if sim >= 0.70:
                score += 48.0 + 15.0 * sim
            elif sim >= 0.35:
                score += 34.0 + 15.0 * sim
            else:
                score += 24.0 + 15.0 * sim
        if "corpus" in cand.s1d_channels:
            score += 26.0
        if cand.s1d_best_rank is not None:
            score += max(0.0, 10.0 - 0.8 * (cand.s1d_best_rank - 1))

    # 3. S5-env 环境降解规则贡献
    if cand.env_rule_ids:
        env_base = 42.0 if domain_eff == "biosysmodb121" else 28.0
        n_env = len(cand.env_rule_ids)
        score += env_base + 4.5 * math.log1p(cand.env_freq_sum) + 3.0 * min(n_env, 5)
        if "eawag" in cand.source_families and "envipath" in cand.source_families:
            score += 12.0  # EAWAG 与 enviPath 双重环境规则印证

    # 4. S5-rr (RetroRules rhea + METANETX) 贡献
    if cand.rr_rule_ids:
        rmax = cand.rr_max_radius
        if rmax >= 6:
            rr_base = 44.0 if domain_eff == "dev-298" else 34.0
        elif rmax >= 4:
            rr_base = 30.0 if domain_eff == "dev-298" else 24.0
        else:
            # r=2 仅在高频或多规则支持时给中等分，抑制泛化噪声
            rr_base = 14.0 if domain_eff == "dev-298" else 10.0

        freq_val = cand.rr_freq_sum
        score += rr_base + 3.8 * math.log1p(freq_val) + 1.5 * math.log1p(len(cand.rr_rule_ids))
        if "rr_rhea" in cand.source_families and "rr_mnx" in cand.source_families:
            score += 6.0

    # 5. 骨架守恒与原子经济性先验
    hr = cand.heavy_atom_ratio
    if 0.65 <= hr <= 1.35:
        score += 10.0
    elif 0.45 <= hr < 0.65 or 1.35 < hr <= 1.60:
        score += 4.0
    elif hr < 0.25:
        score -= 25.0

    # 确定置信层级标签
    if n_macro >= 2 or score >= 75.0:
        cand.prior_tier = "HIGH_CONSENSUS"
    elif score >= 42.0:
        cand.prior_tier = "MEDIUM_PRIOR"
    else:
        cand.prior_tier = "EXPLORATORY"

    cand.prior_score = round(score, 4)
    return cand.prior_score


def rank_and_select_hybrid_pool(
    candidates: list[HybridCandidate],
    max_pool: int = 16,
    class_balanced: bool = True,
    max_per_class_pass1: int = 3,
    allowed_fine_classes: set[str] | None = None,
) -> list[HybridCandidate]:
    """对合并后的候选池按化学先验分排序，并执行 12 大类反应多样性均衡截断。"""
    pool = list(candidates)
    if allowed_fine_classes is not None:
        pool = [c for c in pool if c.fine_cat in allowed_fine_classes]

    # 按 prior_score 降序，同分按重原子比接近 1.0 及严格身份字典序稳定排序
    pool.sort(
        key=lambda c: (
            -c.prior_score,
            abs(1.0 - c.heavy_atom_ratio),
            c.cand_strict,
        )
    )

    if not class_balanced or len(pool) <= max_pool:
        return pool[:max_pool]

    selected: list[HybridCandidate] = []
    deferred: list[HybridCandidate] = []
    class_counts: Counter[str] = Counter()

    for c in pool:
        # 超高共识候选不受单类别配额限制
        if c.prior_tier == "HIGH_CONSENSUS" or class_counts[c.fine_cat] < max_per_class_pass1:
            selected.append(c)
            class_counts[c.fine_cat] += 1
            if len(selected) >= max_pool:
                break
        else:
            deferred.append(c)

    if len(selected) < max_pool and deferred:
        need = max_pool - len(selected)
        selected.extend(deferred[:need])

    return selected[:max_pool]


# ============================================================================
# 3. 底物官能团 -> 反应大类先验预测器 (Zero-LLM Top-M Class Prior)
# ============================================================================


def predict_top_reaction_classes_from_substrate(
    sub_smiles: str,
    candidates: list[HybridCandidate],
    top_m: int = 4,
) -> list[str]:
    """基于底物结构特征与候选集合的先验分布，零 LLM 预测最可能的 Top-M 个反应大类。"""
    class_scores: defaultdict[str, float] = defaultdict(float)
    for c in candidates:
        # 累加该反应大类下前 3 个最高分候选的得分
        class_scores[c.fine_cat] += c.prior_score

    # 结构特征加权
    sp = _mol_profile(sub_smiles)
    if sp is not None:
        sf = sp["formula"]
        if any(sf.get(h, 0) > 0 for h in HALOGENS):
            class_scores["dehalogenation_or_halogenation"] += 35.0
        if sp["n_rings"] >= 1:
            class_scores["monooxygenation_hydroxylation"] += 20.0
            class_scores["dioxygenation_dihydroxylation"] += 15.0
            class_scores["ring_cleavage"] += 15.0
        if sf.get("O", 0) >= 2:
            class_scores["hydrolysis_or_large_cleavage"] += 18.0
            class_scores["decarboxylation_or_c1_cleavage"] += 12.0
            class_scores["dehydrogenation_oxidation"] += 12.0

    ranked_classes = sorted(
        class_scores.keys(),
        key=lambda k: (-class_scores[k], k),
    )
    return ranked_classes[:top_m]


# ============================================================================
# 4. 两阶段「12 大类判断 + 候选选择题」提示词卡片渲染器
# ============================================================================


def render_hybrid_choice_card(
    sub_smiles: str,
    ranked_candidates: list[HybridCandidate],
) -> str:
    """将排序后的混合候选池渲染为结构化『12 反应大类 + 候选产物选择题』卡片。"""
    if not ranked_candidates:
        return (
            "=== 候选反应池 (Candidate Reaction Choice Menu) ===\n"
            "当前底物无规则枚举候选，请直接基于酶学机理推导主产物 SMILES。\n"
        )

    class_groups: defaultdict[str, list[tuple[int, HybridCandidate]]] = defaultdict(list)
    for idx, c in enumerate(ranked_candidates, 1):
        class_groups[c.fine_cat].append((idx, c))

    lines = [
        "=== 结构化候选产物选择题清单 (S1d + S5 本地规则枚举 & 12 反应大类先验) ===",
        f"底物 SMILES: {sub_smiles}",
        "说明：以下候选产物由本地酶反应模板库、enviPath/EAWAG 环境规则与 RetroRules 代谢规则直接作用于底物生成，并已按化学先验置信度排序（OPT-01 最高）。",
        "",
        "【第一步：当前底物可发生的反应大类概览】",
    ]
    for cat_key, items in class_groups.items():
        label = REACTION_CLASS_LABELS.get(cat_key, cat_key)
        opt_tags = ", ".join(f"OPT-{i:02d}" for i, _ in items)
        lines.append(f"  - [{cat_key}] {label} -> 对应选项: {opt_tags}")

    lines.append("")
    lines.append("【第二步：候选主产物选项明细（按化学先验从高到低排列）】")
    for idx, c in enumerate(ranked_candidates, 1):
        srcs = sorted(c.source_families)
        src_str = "+".join(srcs)
        sim_info = f", sim={c.s1d_best_sim:.2f}" if c.s1d_best_sim > 0 else ""
        rad_info = f", rr_r={c.rr_max_radius}" if c.rr_max_radius > 0 else ""
        lines.append(
            f"  [OPT-{idx:02d}] ({c.prior_tier}, score={c.prior_score:.1f}) "
            f"Product: {c.cand_smiles} | Class: {c.fine_cat} | Delta: {c.formula_delta} | "
            f"Sources: {src_str}{sim_info}{rad_info}"
        )

    lines.append("")
    lines.append(
        "【作答指引】：请先判断底物最可能发生的反应大类，优先从上述 [OPT-01]..[OPT-16] 中挑选化学机理最合理的主产物排在第 1 名；"
        "若确认正确产物不在清单中，可在后续顺位补充您自主推导的产物 SMILES。"
    )
    return "\n".join(lines)


# ============================================================================
# 5. 双轨槽位保留融合器 (Confidence-Gated Dual-Track Slot-Reserved Fusion)
# ============================================================================


def _cand_field(c: HybridCandidate | dict[str, Any], key: str, default: Any = None) -> Any:
    if isinstance(c, dict):
        return c.get(key, default)
    return getattr(c, key, default)


def _canonical_strict_key(smiles: str) -> str:
    try:
        mol = Chem.MolFromSmiles(str(smiles).strip())
        if mol is not None:
            return Chem.MolToSmiles(mol, canonical=True, isomericSmiles=True)
    except Exception:
        pass
    return str(smiles).strip()


def select_gated_s5_supplements(
    s1d_candidates: list[HybridCandidate | dict[str, Any]],
    hybrid_candidates: list[HybridCandidate | dict[str, Any]],
    *,
    max_s1d_for_supplement: int = 2,
    min_s5_prior_score: float = 70.0,
    super_consensus_score: float | None = None,
    max_supplements: int = 2,
) -> list[HybridCandidate | dict[str, Any]]:
    """置信度门控筛选器：仅当 S1d 候选池较稀缺 (<= max_s1d_for_supplement)
    且非 S1d 的 S5 候选具备高化学先验分 (>= min_s5_prior_score) 时（或启用 super_consensus_score
    且先验分 >= super_consensus_score 时），返回 Top-K 补位候选。
    """
    if max_supplements <= 0:
        return []
    if len(s1d_candidates) > max_s1d_for_supplement and super_consensus_score is None:
        return []

    s1d_stricts = {
        str(_cand_field(c, "cand_strict") or _canonical_strict_key(str(_cand_field(c, "cand_smiles", ""))))
        for c in s1d_candidates
    }

    supplements: list[HybridCandidate | dict[str, Any]] = []
    seen_st: set[str] = set(s1d_stricts)
    for c in hybrid_candidates:
        c_st = str(_cand_field(c, "cand_strict") or _canonical_strict_key(str(_cand_field(c, "cand_smiles", ""))))
        if not c_st or c_st in seen_st:
            continue
        score = float(_cand_field(c, "prior_score", 0.0) or 0.0)
        if len(s1d_candidates) <= max_s1d_for_supplement:
            if score < min_s5_prior_score:
                continue
        else:
            if super_consensus_score is None or score < super_consensus_score:
                continue
        seen_st.add(c_st)
        supplements.append(c)
        if len(supplements) >= max_supplements:
            break

    return supplements


def merge_dual_track_predictions(
    track1_smiles: list[str],
    s5_supplements: list[HybridCandidate | dict[str, Any] | str],
    *,
    total_slots: int = 5,
    max_supplements: int = 2,
    fallback_candidates: list[HybridCandidate | dict[str, Any] | str] | None = None,
    strict_key_fn=None,
) -> list[str]:
    """双轨槽位保留合并器：
    - Track-1 (S1d + 自由机理生成) 优先占据前 (total_slots - k) 个核心槽位；
    - Track-2 (通过置信度门控的 S5 Top-k 补位候选) 去重补入尾部槽位 Slots (total_slots - k + 1)..total_slots；
    - 若某条 S5 补位候选已被 Track-1 排进前序槽位，则不重复占槽，自动释放槽位给 Track-1 后续候选。
    """
    key_fn = strict_key_fn or _canonical_strict_key

    # 1. 规范化并去重 Track-1 预测
    t1_dedup: list[tuple[str, str]] = []
    seen_t1: set[str] = set()
    for smi in track1_smiles:
        s = str(smi or "").strip()
        if not s:
            continue
        st = str(key_fn(s) or s)
        if st not in seen_t1:
            seen_t1.add(st)
            t1_dedup.append((s, st))

    # 2. 规范化并提取 S5 补位候选
    s5_items: list[tuple[str, str]] = []
    seen_s5: set[str] = set()
    for item in s5_supplements:
        if isinstance(item, str):
            s = item.strip()
            st = str(key_fn(s) or s) if s else ""
        else:
            s = str(_cand_field(item, "cand_smiles", "") or "").strip()
            st = str(_cand_field(item, "cand_strict", "") or (key_fn(s) if s else ""))
        if not s or not st or st in seen_s5:
            continue
        seen_s5.add(st)
        s5_items.append((s, st))
        if len(s5_items) >= max_supplements:
            break

    if not s5_items:
        merged = [s for s, _ in t1_dedup[:total_slots]]
        kept_st = {st for _, st in t1_dedup[:total_slots]}
    else:
        # 3. 计算保留给 Track-1 的前序槽位数（至少保留 total_slots - len(s5_items) 槽）
        base_t1_slots = max(1, total_slots - len(s5_items))
        kept_t1 = list(t1_dedup[:base_t1_slots])
        kept_st = {st for _, st in kept_t1}

        # 过滤出尚未出现在 kept_t1 中的 S5 补位项
        novel_s5 = [(s, st) for s, st in s5_items if st not in kept_st]

        # 如果有 S5 补位项已在 kept_t1 中，则空出的槽位优先还给 Track-1 的第 4/5 槽
        remaining_t1_cursor = base_t1_slots
        while len(kept_t1) + len(novel_s5) < total_slots and remaining_t1_cursor < len(t1_dedup):
            cand_s, cand_st = t1_dedup[remaining_t1_cursor]
            remaining_t1_cursor += 1
            if cand_st not in kept_st and cand_st not in {st for _, st in novel_s5}:
                kept_t1.append((cand_s, cand_st))
                kept_st.add(cand_st)

        merged = [s for s, _ in kept_t1]
        for s, st in novel_s5:
            if len(merged) >= total_slots:
                break
            if st not in kept_st:
                merged.append(s)
                kept_st.add(st)

    # 4. 零损失空槽补位 (Empty-Slot Backfill)：若合并后仍不足 total_slots 且提供了 fallback_candidates，按序去重补齐空槽
    if len(merged) < total_slots and fallback_candidates:
        for fc in fallback_candidates:
            if len(merged) >= total_slots:
                break
            if isinstance(fc, str):
                fs = fc.strip()
                fst = str(key_fn(fs) or fs) if fs else ""
            else:
                fs = str(_cand_field(fc, "cand_smiles", "") or "").strip()
                fst = str(_cand_field(fc, "cand_strict", "") or (key_fn(fs) if fs else ""))
            if fs and fst and fst not in kept_st:
                merged.append(fs)
                kept_st.add(fst)

    return merged[:total_slots]


def render_dual_track_supplement_card(
    sub_smiles: str,
    s1d_candidates: list[HybridCandidate | dict[str, Any]],
    s5_supplements: list[HybridCandidate | dict[str, Any]],
) -> str:
    """渲染双轨槽位保留提示卡（Track-1: S1d + 自由机理生成；Track-2: 门控 Top-K S5 补充提示）。"""
    lines = [
        f"Substrate SMILES: {sub_smiles}",
        "",
        "=== [TRACK-1: Primary S1d Template Pool & Free Mechanistic Deduction (Slots 1..3)] ===",
    ]
    if s1d_candidates:
        for idx, c in enumerate(s1d_candidates, 1):
            c_smi = _cand_field(c, "cand_smiles", "")
            c_cat = _cand_field(c, "fine_cat", "")
            c_del = _cand_field(c, "formula_delta", "")
            srcs = "+".join(sorted(_cand_field(c, "sources", None) or _cand_field(c, "source_families", [])))
            lines.append(
                f"  [S1D-{idx:02d}] Product: {c_smi} | Class: {c_cat} | Delta: {c_del} | Sources: {srcs}"
            )
    else:
        lines.append("  (No S1d analog template matched; deduce primary products directly from enzymatic reaction mechanisms.)")

    if s5_supplements:
        lines.append("")
        lines.append("=== [TRACK-2: High-Prior Local S5 Rule Supplements (Reserved for Tail Slots 4..5)] ===")
        for idx, c in enumerate(s5_supplements, 1):
            c_smi = _cand_field(c, "cand_smiles", "")
            c_cat = _cand_field(c, "fine_cat", "")
            c_del = _cand_field(c, "formula_delta", "")
            c_sc = float(_cand_field(c, "prior_score", 0.0) or 0.0)
            srcs = "+".join(sorted(_cand_field(c, "sources", None) or _cand_field(c, "source_families", [])))
            lines.append(
                f"  [S5-SUPP-{idx:02d}] (prior_score={c_sc:.1f}) Product: {c_smi} | Class: {c_cat} | Delta: {c_del} | Sources: {srcs}"
            )

    return "\n".join(lines)


# ============================================================================
# 6. v44-Next 供给层正规管线入口 (Rule Enumeration + ReactionSpec Compilation)
# ============================================================================

_S5_ENV_RULES_CACHE: dict[str, list[dict[str, Any]]] = {}
_S5_RR_RULES_CACHE: dict[tuple[str, str, int], list[dict[str, Any]]] = {}


def _default_repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _strip_atom_maps(mol: Chem.Mol) -> Chem.Mol:
    rw = Chem.RWMol(mol)
    for a in rw.GetAtoms():
        a.SetAtomMapNum(0)
    return rw.GetMol()


def _compute_heavy_atom_ratio(sub_smiles: str, prod_smiles: str) -> float:
    sp = _mol_profile(sub_smiles)
    pp = _mol_profile(prod_smiles)
    if sp is None or pp is None:
        return 1.0
    sub_ha = max(1, int(sp.get("n_heavy", 1) or 1))
    prod_ha = int(pp.get("n_heavy", sub_ha) or sub_ha)
    return round(prod_ha / sub_ha, 4)


def load_s5_env_rules(repo_root: str | Path | None = None) -> list[dict[str, Any]]:
    """加载并缓存 S5-env 规则集（enviPath 287 + EAWAG 49 SMARTS 规则）。"""
    import gzip
    import json

    root = Path(repo_root).resolve() if repo_root is not None else _default_repo_root()
    cache_key = str(root)
    if cache_key in _S5_ENV_RULES_CACHE:
        return _S5_ENV_RULES_CACHE[cache_key]

    rules: list[dict[str, Any]] = []

    # 1. Primary v3_reactions assets (enviPath 287 + EAWAG 49)
    tsv_path = root / "assets/v3_reactions/envipath/templates.tsv.gz"
    jsonl_path = root / "assets/v3_reactions/envipath/templates_implicitH.jsonl"
    eawag_jsonl_path = root / "assets/v3_reactions/eawag/rules_new_clean.jsonl"

    tsv_meta: dict[str, dict[str, str]] = {}
    if tsv_path.exists():
        try:
            with gzip.open(tsv_path, "rt", encoding="utf-8") as fh:
                hdr = fh.readline().strip().split("\t")
                for line in fh:
                    if not line.strip():
                        continue
                    row = dict(zip(hdr, line.strip().split("\t")))
                    if "TEMPLATE_ID" in row:
                        tsv_meta[row["TEMPLATE_ID"]] = row
        except Exception:
            pass

    if jsonl_path.exists():
        with open(jsonl_path, encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                d = json.loads(line)
                tid = str(d.get("template_id") or "")
                smirks = str(d.get("reencoded_smirks") or d.get("original_smirks") or "")
                if not smirks:
                    continue
                meta = tsv_meta.get(tid, {})
                rc_str = str(meta.get("REACTIONS_COUNT") or "1")
                rc = int(rc_str) if rc_str.isdigit() else 1
                ecs = [
                    x.strip()
                    for x in str(meta.get("ECS") or "").replace(",", ";").split(";")
                    if x.strip()
                ]
                try:
                    rxn = AllChem.ReactionFromSmarts(smirks)
                    if rxn is not None and rxn.GetNumReactantTemplates() == 1:
                        rules.append(
                            {
                                "rule_id": tid or "envipath:unknown",
                                "source_family": "envipath",
                                "name": str(meta.get("NAME") or tid),
                                "ec_numbers": ecs,
                                "frequency": max(1, rc),
                                # 论文消融 v1.4(默认消费方零变化):非金标
                                # 题源标识元数据(NoSelf 判定用)
                                "parent_reaction_ids":
                                    _parse_parent_reaction_ids(
                                        meta.get("REACTIONS")),
                                "datasets": [
                                    x.strip() for x in str(
                                        meta.get("DATASETS") or "")
                                    .replace(",", ";").split(";")
                                    if x.strip()],
                                "rxn": rxn,
                                "rt": rxn.GetReactantTemplate(0),
                            }
                        )
                except Exception:
                    pass

    if eawag_jsonl_path.exists():
        with open(eawag_jsonl_path, encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                d = json.loads(line)
                btid = str(d.get("btid") or "")
                reac_id = str(d.get("reac_id") or "")
                tid = f"{btid}#{reac_id}" if (btid or reac_id) else "eawag:unknown"
                smirks = str(d.get("smirks") or d.get("skeleton") or "")
                if not smirks:
                    continue
                try:
                    rxn = AllChem.ReactionFromSmarts(smirks)
                    if rxn is not None and rxn.GetNumReactantTemplates() == 1:
                        rules.append(
                            {
                                "rule_id": tid,
                                "source_family": "eawag",
                                "name": tid,
                                "ec_numbers": [],
                                "frequency": 1,
                                # 论文消融 v1.4(默认消费方零变化):
                                # 非金标 donor/题源标识元数据(NoSelf)
                                "donor_smiles": str(
                                    d.get("donor_smiles") or ""),
                                "product_smiles": str(
                                    d.get("product_smiles") or ""),
                                "reaction_id": reac_id,
                                "btid": btid,
                                "rxn": rxn,
                                "rt": rxn.GetReactantTemplate(0),
                            }
                        )
                except Exception:
                    pass

    # 2. Optional lookup JSON fallback (if running against minimal fixture root)
    if not rules:
        env_path = root / "data/lookup/envipath_rules.json"
        if env_path.exists():
            with open(env_path, encoding="utf-8") as f:
                env_data = json.load(f)
            for r in env_data.get("rules", []):
                smarts = r.get("smarts", "")
                if not smarts:
                    continue
                try:
                    rxn = AllChem.ReactionFromSmarts(smarts)
                    if rxn is not None:
                        rules.append(
                            {
                                "rule_id": f"env:{r.get('bt_id', '')}",
                                "source_family": "envipath",
                                "name": r.get("name", ""),
                                "ec_numbers": r.get("ec_numbers", []),
                                "frequency": int(r.get("frequency", 1) or 1),
                                "rxn": rxn,
                            }
                        )
                except Exception:
                    pass

    _S5_ENV_RULES_CACHE[cache_key] = rules
    return rules


def load_s5_rr_rules(
    repo_root: str | Path | None = None,
    *,
    datasets: tuple[str, ...] = ("rhea", "mnx"),
    radii: tuple[int, ...] = (2, 4, 6),
    max_rules_per_file: int = 1500,
) -> list[dict[str, Any]]:
    """可选加载并缓存 S5-rr (RetroRules rhea/METANETX) 规则集。"""
    import csv

    root = Path(repo_root).resolve() if repo_root is not None else _default_repo_root()
    out: list[dict[str, Any]] = []
    radii_set = {int(r) for r in radii}
    for ds in datasets:
        ds_norm = str(ds).strip().lower()
        cache_key = (str(root), ds_norm, int(max_rules_per_file))
        if cache_key in _S5_RR_RULES_CACHE:
            for item in _S5_RR_RULES_CACHE[cache_key]:
                if int(item.get("diameter", 0)) in radii_set:
                    out.append(item)
            continue

        candidates = [
            root / f"data/retrorules/retrorules_rr02_rp2_flat_forward_{ds_norm}.tsv",
            root / f"data/lookup/retrorules_{ds_norm}.tsv",
        ]
        tsv_path = next((p for p in candidates if p.exists()), None)
        loaded_ds: list[dict[str, Any]] = []
        if tsv_path is not None:
            try:
                with open(tsv_path, encoding="utf-8") as f:
                    reader = csv.DictReader(f, delimiter="\t")
                    for idx, row in enumerate(reader):
                        if idx >= max_rules_per_file:
                            break
                        smarts = row.get("Rule_SMARTS") or row.get("Reaction_SMARTS") or row.get("smarts") or ""
                        if not smarts:
                            continue
                        diam = int(float(row.get("Diameter") or row.get("diameter") or 4))
                        try:
                            rxn = AllChem.ReactionFromSmarts(smarts)
                            if rxn is not None:
                                loaded_ds.append(
                                    {
                                        "rule_id": str(row.get("Rule_ID") or row.get("rule_id") or f"rr_{ds_norm}_{idx}"),
                                        "source_family": f"rr_{ds_norm}",
                                        "diameter": diam,
                                        "frequency": int(float(row.get("Score_normalized") or row.get("frequency") or 1)),
                                        "rxn": rxn,
                                    }
                                )
                        except Exception:
                            pass
            except Exception:
                pass
        _S5_RR_RULES_CACHE[cache_key] = loaded_ds
        for item in loaded_ds:
            if int(item.get("diameter", 0)) in radii_set:
                out.append(item)
    return out


_S5_RR_RESOLVERS_CACHE: dict[tuple[str, str], Any] = {}
_S5_RR_RXN_CACHE: dict[str, Any] = {}


def _enumerate_s5_rr_via_resolver(
    substrate_smiles: str,
    mol: Chem.Mol,
    sub_st: str,
    *,
    repo_root: str | Path | None = None,
    datasets: tuple[str, ...] = ("rhea", "mnx"),
    radii: tuple[int, ...] = (2, 4, 6),
    no_self: bool = False,
    question_meta: dict | None = None,
    exclude_substrate_keys: set[str] | None = None,
    drop_rule_ids: set[str] | None = None,
    filter_stats: dict | None = None,
) -> tuple[bool, dict[str, dict[str, Any]]]:
    """优先使用预构建的 PatternFingerprint 索引 (`RetroTemplateResolver`) 执行高速 S5-rr 子结构枚举。

    单题检索+枚举耗时 ~0.07s；若运行在无 RetroRules 索引资产的轻量环境（如公开快照仓单测），
    自动返回 `(False, {})` 并由上层优雅降级为 TSV 或仅 S5-env。
    """
    root = Path(repo_root).resolve() if repo_root is not None else _default_repo_root()
    radii_set = {int(r) for r in radii}
    tpl_agg: dict[str, dict[str, Any]] = {}
    used_any_resolver = False
    _ns_ids = question_source_ids(question_meta) if no_self else set()
    _ns_sub_strict, _ns_sub_cn = (
        component_identity_sets(substrate_smiles) if no_self
        else (set(), set()))

    for ds in datasets:
        ds_norm = str(ds).strip().lower()
        cache_key = (str(root), ds_norm)
        if cache_key not in _S5_RR_RESOLVERS_CACHE:
            npz_path = root / f"assets/retrorules/derived/{ds_norm}_retro_index.npz"
            if not npz_path.exists():
                _S5_RR_RESOLVERS_CACHE[cache_key] = None
            else:
                try:
                    from pathway_v43.config import resolve_config
                    from pathway_v43.services.retro_source import RetroTemplateResolver

                    cfg = resolve_config(None, root / "assets")
                    _S5_RR_RESOLVERS_CACHE[cache_key] = RetroTemplateResolver(
                        cfg,
                        dataset=ds_norm,
                        verify_artifacts=False,
                        verify_source=False,
                    )
                except Exception:
                    _S5_RR_RESOLVERS_CACHE[cache_key] = None

        resolver = _S5_RR_RESOLVERS_CACHE.get(cache_key)
        if resolver is None:
            continue
        used_any_resolver = True
        try:
            hits = resolver.library.search(
                substrate_smiles,
                mode="substruct",
                threshold=0.0,
                top_k=10000,
                allowed_radii=radii_set,
                dedupe_same_lhs=False,
                require_sanitized=False,
            )
        except Exception:
            continue

        for h in hits:
            tpl_str = str(h.get("template") or "")
            if not tpl_str:
                continue
            tid = str(h.get("template_id") or f"rr_{ds_norm}")
            rc = max(len(h.get("reactions") or []), 1)
            rads = {int(r) for r in (h.get("radii") or [])} & radii_set
            info = tpl_agg.get(tpl_str)
            if info is None:
                tpl_agg[tpl_str] = {
                    "datasets": {ds_norm},
                    "radii": set(rads),
                    "max_rc": rc,
                    "rule_ids": {f"{ds_norm}:{tid}"},
                    "primary_rule_id": f"{ds_norm}:{tid}",
                    # 论文消融 v1.4:非金标题源标识元数据(NoSelf)
                    "parent_reaction_ids": {
                        str(x) for x in (
                            h.get("parent_reaction_ids")
                            or h.get("reactions") or []) if str(x)},
                    "lhs_mapped_smiles": _as_smiles_values(
                        h.get("lhs_mapped_smiles")),
                }
            else:
                info["datasets"].add(ds_norm)
                info["radii"].update(rads)
                if rc > info["max_rc"]:
                    info["max_rc"] = rc
                info["rule_ids"].add(f"{ds_norm}:{tid}")
                info["parent_reaction_ids"].update(
                    str(x) for x in (h.get("parent_reaction_ids")
                                     or h.get("reactions") or [])
                    if str(x))
                info["lhs_mapped_smiles"].update(
                    _as_smiles_values(h.get("lhs_mapped_smiles")))

    if not used_any_resolver:
        return False, {}

    if no_self:
        # 论文消融 v1.4 DB-2 NoSelf:剔除题源反应 ID 命中与单样本特异
        # 模板(零金标;只读题面底物与规则元数据)。
        tpl_agg = {
            tpl_str: info for tpl_str, info in tpl_agg.items()
            if not _rr_template_is_self(
                info, source_ids=_ns_ids,
                sub_strict=_ns_sub_strict, sub_cn=_ns_sub_cn)}

    # ---- 论文消融 v1.4(默认 None ⇒ 不进入 ⇒ 逐字节零漂移)----
    if filter_stats is not None:
        filter_stats["n_rr_templates_scanned"] = int(
            filter_stats.get("n_rr_templates_scanned", 0)) + len(tpl_agg)
    tpl_agg = _filter_rr_template_agg(
        tpl_agg,
        exclude_substrate_keys=exclude_substrate_keys,
        drop_rule_ids=drop_rule_ids,
        stats=filter_stats)

    rr_prod_map: dict[str, dict[str, Any]] = {}
    for tpl_str, info in tpl_agg.items():
        try:
            rxn = _S5_RR_RXN_CACHE.get(tpl_str)
            if rxn is None and tpl_str not in _S5_RR_RXN_CACHE:
                rxn = AllChem.ReactionFromSmarts(tpl_str)
                _S5_RR_RXN_CACHE[tpl_str] = rxn
            if rxn is None or rxn.GetNumReactantTemplates() != 1:
                continue
            ps_list = rxn.RunReactants((mol,), maxProducts=100)
        except Exception:
            continue

        fams = {f"rr_{d}" for d in info["datasets"]}
        rads = info["radii"]
        rmax = max(rads) if rads else 2
        rc = int(info["max_rc"])
        rids = info["rule_ids"]
        primary_rid = str(info["primary_rule_id"])

        for ps in ps_list[:30]:
            valid_frags: list[tuple[int, str, str]] = []
            for p in ps:
                try:
                    p2 = _strip_atom_maps(p)
                    Chem.SanitizeMol(p2)
                    if any(a.GetAtomicNum() == 0 for a in p2.GetAtoms()):
                        continue
                    c_smi = Chem.MolToSmiles(p2, isomericSmiles=True)
                except Exception:
                    continue
                for frag in c_smi.split("."):
                    frag = frag.strip()
                    if not frag:
                        continue
                    fmol = Chem.MolFromSmiles(frag)
                    if fmol is None:
                        continue
                    ha = fmol.GetNumHeavyAtoms()
                    fst = k_strict(frag)
                    if fst and fst != sub_st:
                        valid_frags.append((ha, frag, fst))
            if not valid_frags:
                continue
            valid_frags.sort(key=lambda x: (-x[0], x[1]))
            _best_ha, best_prod, best_st = valid_frags[0]
            coproducts = [frag for _, frag, fst in valid_frags[1:] if fst != best_st]

            rec = rr_prod_map.get(best_st)
            if rec is None:
                rec = {
                    "cand_strict": best_st,
                    "cand_smiles": best_prod,
                    "source_families": set(),
                    "env_rule_ids": set(),
                    "env_freq_sum": 0,
                    "rr_rule_ids": set(),
                    "rr_max_radius": 0,
                    "rr_freq_sum": 0,
                    "primary_rule_id": primary_rid,
                    "coproduct_sets": [],
                    # 论文消融 v1.4:非金标题源标识(NoSelf 审计/披露)
                    "rr_parent_reaction_ids": set(
                        info.get("parent_reaction_ids") or set()),
                }
                rr_prod_map[best_st] = rec
            else:
                rec["rr_parent_reaction_ids"].update(
                    info.get("parent_reaction_ids") or set())
            rec["source_families"].update(fams)
            new_rids = rids - rec["rr_rule_ids"]
            if new_rids:
                rec["rr_rule_ids"].update(new_rids)
                rec["rr_freq_sum"] += max(1, rc)
            if rmax > rec["rr_max_radius"]:
                rec["rr_max_radius"] = rmax
            if coproducts and coproducts not in rec["coproduct_sets"]:
                rec["coproduct_sets"].append(coproducts)

    return True, rr_prod_map


def enumerate_s5_rules(
    substrate_smiles: str,
    *,
    repo_root: str | Path | None = None,
    include_env: bool = True,
    include_rr: bool = True,
    rr_datasets: tuple[str, ...] = ("rhea", "mnx"),
    rr_radii: tuple[int, ...] = (2, 4, 6),
    extra_rules: list[dict[str, Any]] | None = None,
    no_self: bool = False,
    question_meta: dict | None = None,
    exclude_substrate_keys: set[str] | None = None,
    drop_rule_ids: set[str] | None = None,
    filter_stats: dict | None = None,
) -> dict[str, dict[str, Any]]:
    """对底物执行 S5-env (enviPath + EAWAG) 与 S5-rr (RetroRules rhea + METANETX) 规则枚举。

    返回按 `cand_strict` 聚合的字典，每项包含 `cand_smiles`、触发规则集、来源家族与同规则副产物片段。
    """
    mol = Chem.MolFromSmiles(str(substrate_smiles or ""))
    if mol is None:
        return {}
    sub_st = k_strict(substrate_smiles)

    _ns_ids = question_source_ids(question_meta) if no_self else set()
    _ns_sub_strict, _ns_sub_cn = (
        component_identity_sets(substrate_smiles) if no_self
        else (set(), set()))

    rules: list[dict[str, Any]] = []
    if include_env:
        env_rules = load_s5_env_rules(repo_root)
        if no_self:
            # 论文消融 v1.4 DB-2 NoSelf(零金标):剔除题源反应 ID 命中
            # 与仅源自当前底物的单样本特异规则。
            env_rules = [
                r for r in env_rules
                if not _env_rule_is_self(
                    r, source_ids=_ns_ids,
                    sub_strict=_ns_sub_strict, sub_cn=_ns_sub_cn)]
        # ---- 论文消融 v1.4(默认 None ⇒ 原样;先于枚举执行)----
        if filter_stats is not None:
            filter_stats["n_env_rules_scanned"] = int(
                filter_stats.get("n_env_rules_scanned", 0)) + len(env_rules)
        env_rules = _filter_rules_by_source(
            env_rules,
            exclude_substrate_keys=exclude_substrate_keys,
            drop_rule_ids=drop_rule_ids,
            stats=filter_stats,
            stats_prefix="env",
            lhs_field="donor_smiles",
            substrate_match="equal")
        rules.extend(env_rules)

    rr_from_resolver: dict[str, dict[str, Any]] = {}
    used_rr_resolver = False
    if include_rr:
        used_rr_resolver, rr_from_resolver = _enumerate_s5_rr_via_resolver(
            substrate_smiles,
            mol,
            sub_st,
            repo_root=repo_root,
            datasets=rr_datasets,
            radii=rr_radii,
            no_self=no_self,
            question_meta=question_meta,
            exclude_substrate_keys=exclude_substrate_keys,
            drop_rule_ids=drop_rule_ids,
            filter_stats=filter_stats,
        )
        if not used_rr_resolver:
            # 降级 TSV 规则:只有 rule_id 可判(父反应/lhs 字段不在
            # 该 schema 内)⇒ 单样本特异过滤进覆盖缺口诊断,不假装。
            tsv_rules = load_s5_rr_rules(
                repo_root, datasets=rr_datasets, radii=rr_radii)
            if filter_stats is not None:
                filter_stats["n_rr_tsv_rules_scanned"] = int(
                    filter_stats.get("n_rr_tsv_rules_scanned", 0)) + len(
                    tsv_rules)
            tsv_rules = _filter_rules_by_source(
                tsv_rules,
                exclude_substrate_keys=exclude_substrate_keys,
                drop_rule_ids=drop_rule_ids,
                stats=filter_stats,
                stats_prefix="rr_tsv",
                lhs_field="lhs_mapped_smiles",
                substrate_match="superset")
            rules.extend(tsv_rules)

    if extra_rules:
        for r in extra_rules:
            rxn = r.get("rxn")
            if rxn is None and r.get("smarts"):
                try:
                    rxn = AllChem.ReactionFromSmarts(str(r["smarts"]))
                except Exception:
                    rxn = None
            if rxn is not None:
                item = dict(r)
                item["rxn"] = rxn
                rules.append(item)

    prod_map: dict[str, dict[str, Any]] = {}
    for r in rules:
        rxn = r["rxn"]
        rt = r.get("rt")
        src_fam = str(r.get("source_family") or "envipath")
        rule_id = str(r.get("rule_id") or "s5:unknown")
        freq = int(r.get("frequency", 1) or 1)
        diam = int(r.get("diameter", 0) or 0)
        try:
            if rt is not None and not mol.HasSubstructMatch(rt):
                continue
            ps_list = rxn.RunReactants((mol,), maxProducts=100)
        except Exception:
            continue
        for ps in ps_list[:30]:
            valid_frags: list[tuple[int, str, str]] = []
            for p in ps:
                try:
                    p2 = _strip_atom_maps(p)
                    Chem.SanitizeMol(p2)
                    if any(a.GetAtomicNum() == 0 for a in p2.GetAtoms()):
                        continue
                    c_smi = Chem.MolToSmiles(p2, isomericSmiles=True)
                except Exception:
                    continue
                for frag in c_smi.split("."):
                    frag = frag.strip()
                    if not frag:
                        continue
                    fmol = Chem.MolFromSmiles(frag)
                    if fmol is None:
                        continue
                    ha = fmol.GetNumHeavyAtoms()
                    fst = k_strict(frag)
                    if fst and fst != sub_st:
                        valid_frags.append((ha, frag, fst))
            if not valid_frags:
                continue
            valid_frags.sort(key=lambda x: (-x[0], x[1]))
            _best_ha, best_prod, best_st = valid_frags[0]
            coproducts = [frag for _, frag, fst in valid_frags[1:] if fst != best_st]

            rec = prod_map.get(best_st)
            if rec is None:
                rec = {
                    "cand_strict": best_st,
                    "cand_smiles": best_prod,
                    "source_families": set(),
                    "env_rule_ids": set(),
                    "env_freq_sum": 0,
                    "rr_rule_ids": set(),
                    "rr_max_radius": 0,
                    "rr_freq_sum": 0,
                    "primary_rule_id": rule_id,
                    "coproduct_sets": [],
                }
                prod_map[best_st] = rec
            rec["source_families"].add(src_fam)
            if src_fam in ("envipath", "eawag"):
                if rule_id not in rec["env_rule_ids"]:
                    rec["env_rule_ids"].add(rule_id)
                    rec["env_freq_sum"] += max(1, freq)
            else:
                if rule_id not in rec["rr_rule_ids"]:
                    rec["rr_rule_ids"].add(rule_id)
                    rec["rr_freq_sum"] += max(1, freq)
                if diam > rec["rr_max_radius"]:
                    rec["rr_max_radius"] = diam
            if coproducts and coproducts not in rec["coproduct_sets"]:
                rec["coproduct_sets"].append(coproducts)

    # 合并高速 RetroTemplateResolver 产出的 S5-rr 枚举结果
    for best_st, rr_rec in rr_from_resolver.items():
        rec = prod_map.get(best_st)
        if rec is None:
            prod_map[best_st] = rr_rec
        else:
            rec["source_families"].update(rr_rec["source_families"])
            rec["rr_rule_ids"].update(rr_rec["rr_rule_ids"])
            rec["rr_freq_sum"] += int(rr_rec["rr_freq_sum"])
            if int(rr_rec["rr_max_radius"]) > int(rec["rr_max_radius"]):
                rec["rr_max_radius"] = int(rr_rec["rr_max_radius"])
            for cops in rr_rec.get("coproduct_sets") or []:
                if cops and cops not in rec["coproduct_sets"]:
                    rec["coproduct_sets"].append(cops)
            # 论文消融 v1.4:非金标题源标识并集(默认路径键不出现
            # ⇒ 下游行为零变化)
            if rr_rec.get("rr_parent_reaction_ids"):
                rec.setdefault("rr_parent_reaction_ids", set()).update(
                    rr_rec["rr_parent_reaction_ids"])

    return prod_map


def infer_cleavage_coproducts(sub_smi: str, cand_smi: str) -> list[list[str]]:
    """针对底物碳数大于候选主产物的裂解反应（酯/有机磷/醚/酰胺/拟除虫菊酯水解等），
    基于 MCS 边界与 CIP 立体构型保持推导水解 (-OH 加成) 及消除 (-H) 的第二有机共产物片段。
    """
    from rdkit.Chem import rdFMCS

    sub_mol = Chem.MolFromSmiles(str(sub_smi or ""))
    cand_mol = Chem.MolFromSmiles(str(cand_smi or ""))
    if sub_mol is None or cand_mol is None:
        return []
    sub_c = sum(1 for a in sub_mol.GetAtoms() if a.GetSymbol() == "C")
    cand_c = sum(1 for a in cand_mol.GetAtoms() if a.GetSymbol() == "C")
    if sub_c <= cand_c:
        return []

    Chem.AssignStereochemistry(sub_mol, cleanIt=True, force=True)
    orig_cip: dict[int, str] = {}
    for a in sub_mol.GetAtoms():
        if a.HasProp("_CIPCode"):
            orig_cip[a.GetIdx()] = a.GetProp("_CIPCode")

    out: list[list[str]] = []
    if sub_c - cand_c == 1:
        sub_o = sum(1 for a in sub_mol.GetAtoms() if a.GetSymbol() == "O")
        cand_o = sum(1 for a in cand_mol.GetAtoms() if a.GetSymbol() == "O")
        if sub_o == cand_o:
            out.append(["CO"])
            out.append(["C=O"])
        elif sub_o - cand_o == 2:
            out.append(["O=C=O"])
            out.append(["C(=O)O"])
        elif sub_o - cand_o == 1:
            out.append(["C=O"])
            out.append(["CO"])

    try:
        mcs = rdFMCS.FindMCS(
            [sub_mol, cand_mol],
            bondCompare=rdFMCS.BondCompare.CompareAny,
            ringMatchesRingOnly=False,
            timeout=1,
        )
        if mcs and mcs.numAtoms >= 2 and mcs.smartsString:
            q = Chem.MolFromSmarts(mcs.smartsString)
            if q is not None:
                for match in sub_mol.GetSubstructMatches(q)[:6]:
                    mset = set(match)
                    rem_idxs = [i for i in range(sub_mol.GetNumAtoms()) if i not in mset]
                    if not rem_idxs:
                        continue
                    b_atoms: list[tuple[int, int]] = []
                    for r_i in rem_idxs:
                        for nb in sub_mol.GetAtomWithIdx(r_i).GetNeighbors():
                            if nb.GetIdx() in mset:
                                b_atoms.append((r_i, nb.GetIdx()))

                    for add_oh in (True, False):
                        if add_oh and len(b_atoms) != 1:
                            continue
                        rw = Chem.RWMol(sub_mol)
                        for a_i in range(sub_mol.GetNumAtoms()):
                            rw.GetAtomWithIdx(a_i).SetIntProp("_orig_idx", a_i)
                        if add_oh:
                            r_i, _ = b_atoms[0]
                            o_idx = rw.AddAtom(Chem.Atom(8))
                            rw.AddBond(r_i, o_idx, Chem.BondType.SINGLE)
                        for idx in sorted(mset, reverse=True):
                            rw.RemoveAtom(idx)
                        try:
                            m = rw.GetMol()
                            Chem.SanitizeMol(m)
                            Chem.AssignStereochemistry(m, cleanIt=True, force=True)
                            flipped = False
                            for a in m.GetAtoms():
                                if a.HasProp("_orig_idx") and a.GetIntProp("_orig_idx") in orig_cip:
                                    if a.HasProp("_CIPCode") and a.GetProp("_CIPCode") != orig_cip[a.GetIntProp("_orig_idx")]:
                                        a.InvertChirality()
                                        flipped = True
                            if flipped:
                                Chem.AssignStereochemistry(m, cleanIt=True, force=True)
                            frags = [
                                Chem.MolToSmiles(f, isomericSmiles=True)
                                for f in Chem.GetMolFrags(m, asMols=True)
                            ]
                            if frags and frags not in out:
                                out.append(frags)
                        except Exception:
                            pass
    except Exception:
        pass
    return out


_CLEAVAGE_UPGRADE_CACHE: dict[tuple[str, str], dict[str, Any] | None] = {}


def _smiles_has_carbon(smi: str) -> bool:
    if not smi:
        return False
    m = Chem.MolFromSmiles(str(smi))
    return bool(m is not None and any(a.GetSymbol() == "C" for a in m.GetAtoms()))


def try_upgrade_cleavage_spec(
    substrate_smiles: str,
    spec: dict[str, Any],
) -> dict[str, Any] | None:
    """对存在 `undeclared_coproducts` 且无含碳 `coproducts` 的单产物裂解 `ReactionSpec`（`s5-` 或 `novel-`），
    尝试用 `infer_cleavage_coproducts` 补齐双产物裂解 `coproducts` 并通过完整执行+11项审计核验。
    """
    from pathway_v43.pollutant.audit import audit_hypothesis, decide_admission
    from pathway_v43.pollutant.chemstate import build_chemical_state, strict_identity_of
    from pathway_v43.pollutant.path_context import build_path_context
    from pathway_v43.pollutant.production import (
        ADMISSION_SUBMITTABLE,
        execute_atomtool_expansion,
        prepare_hypothesis,
    )
    from pathway_v43.pollutant.recorded_source import compile_recorded_reaction

    sub_smi = str(substrate_smiles or "").strip()
    cand_smi = str((spec or {}).get("product_smiles") or "").strip()
    if not sub_smi or not cand_smi or len(sub_smi) > 85 or len(cand_smi) > 85:
        return None
    try:
        sub_iso = strict_identity_of(sub_smi)
        cand_iso = strict_identity_of(cand_smi)
    except Exception:
        return None
    if not sub_iso or not cand_iso or sub_iso == cand_iso:
        return None

    cache_key = (sub_iso, cand_iso)
    if cache_key in _CLEAVAGE_UPGRADE_CACHE:
        cached = _CLEAVAGE_UPGRADE_CACHE[cache_key]
        if cached is None:
            return None
        upgraded = dict(spec)
        upgraded["edits"] = list(cached["edits"])
        upgraded["coproducts"] = list(cached["coproducts"])
        if cached.get("undeclared_coproducts") is not None:
            upgraded["undeclared_coproducts"] = list(cached["undeclared_coproducts"])
        else:
            upgraded.pop("undeclared_coproducts", None)
        return upgraded

    sub_mol = Chem.MolFromSmiles(sub_iso)
    cand_mol = Chem.MolFromSmiles(cand_iso)
    if sub_mol is None or cand_mol is None or sub_mol.GetNumAtoms() > 38:
        _CLEAVAGE_UPGRADE_CACHE[cache_key] = None
        return None
    sub_c = sum(1 for a in sub_mol.GetAtoms() if a.GetSymbol() == "C")
    cand_c = sum(1 for a in cand_mol.GetAtoms() if a.GetSymbol() == "C")
    if sub_c <= cand_c or (sub_c - cand_c) > 15:
        _CLEAVAGE_UPGRADE_CACHE[cache_key] = None
        return None

    rec_id = str(spec.get("transformation_ref") or spec.get("key") or "s5-cleavage-upgrade")
    for cop_list in infer_cleavage_coproducts(sub_iso, cand_iso)[:4]:
        if not cop_list:
            continue
        try:
            res = compile_recorded_reaction(
                substrate_smiles=sub_iso,
                donor_smiles=sub_iso,
                products=[cand_iso, *cop_list],
                record_id=rec_id,
                novel_product_first_principal=cand_iso,
            )
            if res.get("status") != "compiled":
                continue
            cand_spec = dict(res["spec"])
            parts = [
                str(cand_spec.get("product_smiles") or ""),
                *[str(c) for c in (cand_spec.get("coproducts") or [])],
            ]
            non_principal = [
                strict_identity_of(p)
                for p in parts
                if p and strict_identity_of(p) != cand_iso
            ]
            if not non_principal:
                continue
            cand_spec["product_smiles"] = cand_iso
            cand_spec["coproducts"] = non_principal
            p1_gate = res.get("novel_p1_gate")
            if isinstance(p1_gate, dict) and p1_gate.get("gate_ok"):
                if p1_gate.get("undeclared_coproducts"):
                    cand_spec["undeclared_coproducts"] = list(p1_gate["undeclared_coproducts"])
                else:
                    cand_spec.pop("undeclared_coproducts", None)
            sub_st = build_chemical_state(sub_iso, "raw_input", [{"record": rec_id}])
            prep = prepare_hypothesis(
                cand_spec,
                parent_path_id="p0",
                substrate_state=sub_st,
                transformation_ref=rec_id,
            )
            ex = execute_atomtool_expansion(
                substrate_smiles=sub_iso,
                tool_inputs=prep["tool_inputs"],
            )
            if not ex.get("execution_ok"):
                continue
            aud = audit_hypothesis(
                prep["hypothesis"],
                run_id="s5-cleavage-upgrade-check",
                states=prep["states"],
                context=build_path_context(condition_facts=[], scenario_ref=""),
                center_evidence=ex["center_evidence"],
            )
            disp, _ = decide_admission(aud)
            if disp in ADMISSION_SUBMITTABLE:
                _CLEAVAGE_UPGRADE_CACHE[cache_key] = {
                    "edits": list(cand_spec.get("edits") or []),
                    "coproducts": list(non_principal),
                    "undeclared_coproducts": cand_spec.get("undeclared_coproducts"),
                }
                upgraded = dict(spec)
                upgraded["edits"] = list(cand_spec.get("edits") or [])
                upgraded["coproducts"] = list(non_principal)
                if cand_spec.get("undeclared_coproducts") is not None:
                    upgraded["undeclared_coproducts"] = list(cand_spec["undeclared_coproducts"])
                else:
                    upgraded.pop("undeclared_coproducts", None)
                return upgraded
        except Exception:
            continue

    _CLEAVAGE_UPGRADE_CACHE[cache_key] = None
    return None


def _infer_s5_leaving_coproduct_sets(sub_smi: str, cand_smi: str) -> list[list[str]]:
    """当单底物直编 compile_recorded_reaction(sub, sub, [cand]) 因缺离去基团/共产物映射失败时，
    基于元素差与最大公共子结构 (MCS) 自动推断候选离去组分集合（最大化 M2a -> M2b 池内 S5 编译率）。
    """
    sub_mol = Chem.MolFromSmiles(str(sub_smi or ""))
    cand_mol = Chem.MolFromSmiles(str(cand_smi or ""))
    if sub_mol is None or cand_mol is None:
        return []

    out_sets: list[list[str]] = []

    # 1. 重原子差推导常见小分子离去基团
    sub_counts: dict[str, int] = {}
    for a in sub_mol.GetAtoms():
        s = a.GetSymbol()
        if s != "H":
            sub_counts[s] = sub_counts.get(s, 0) + 1
    cand_counts: dict[str, int] = {}
    for a in cand_mol.GetAtoms():
        s = a.GetSymbol()
        if s != "H":
            cand_counts[s] = cand_counts.get(s, 0) + 1
    rem = {
        k: sub_counts[k] - cand_counts.get(k, 0)
        for k in sub_counts
        if sub_counts[k] > cand_counts.get(k, 0)
    }
    if rem:
        small_cops: list[str] = []
        rem_copy = dict(rem)
        for hal in ("Cl", "Br", "F", "I"):
            if rem_copy.get(hal, 0) > 0:
                small_cops.extend([hal] * rem_copy.pop(hal))
        if rem_copy == {"N": 1}:
            small_cops.append("N")
            rem_copy.clear()
        elif rem_copy == {"O": 1}:
            small_cops.append("O")
            rem_copy.clear()
        elif rem_copy == {"S": 1}:
            small_cops.append("S")
            rem_copy.clear()
        elif rem_copy == {"C": 1}:
            out_sets.append(small_cops + ["CO"])
            out_sets.append(small_cops + ["C=O"])
            out_sets.append(small_cops + ["O=C=O"])
            small_cops.append("C")
            rem_copy.clear()
        elif rem_copy == {"C": 1, "O": 1}:
            out_sets.append(small_cops + ["CO"])
            out_sets.append(small_cops + ["C=O"])
            small_cops.append("O=C=O")
            rem_copy.clear()
        elif rem_copy == {"C": 1, "O": 2}:
            out_sets.append(small_cops + ["O=C=O"])
            small_cops.append("C(=O)O")
            rem_copy.clear()
        elif rem_copy == {"N": 1, "O": 2}:
            small_cops.append("O=N[O-]")
            rem_copy.clear()
        if small_cops and not rem_copy and small_cops not in out_sets:
            out_sets.append(small_cops)

    # 2. 基于 MCS 抽取底物上被裂解脱离的连通分子片段（含水解 -OH 加成与 CIP 构型保持）
    for c_set in infer_cleavage_coproducts(sub_smi, cand_smi):
        if c_set and c_set not in out_sets:
            out_sets.append(c_set)

    # 3. 常见酶学小分子共产物兜底（如水合/取代伴随 -H2O、-NH3、-CO2、-CH3OH 等）
    for common in (
        ["O"],
        ["N"],
        ["O=C=O"],
        ["CO"],
        ["C=O"],
        ["C(=O)O"],
        ["Cl"],
        ["Br"],
        ["F"],
        ["I"],
        ["S"],
        ["O=P(O)(O)O"],
        ["O=S(=O)(O)O"],
        ["O", "O=C=O"],
        ["O", "N"],
    ):
        if common not in out_sets:
            out_sets.append(common)

    return out_sets


def compile_s5_candidate_to_spec(
    substrate_smiles: str,
    cand: HybridCandidate | dict[str, Any],
    *,
    index: int = 1,
    is_gated_supplement: bool = True,
    coproduct_sets: list[list[str]] | None = None,
    extended_stereo_dissolution: bool = False,
    stereo_edit_graceful_fallback: bool = False,
    allow_ring_cleavage_and_fused_dearomatization: bool = False,
    retained_tetrahedral_parity_check: bool = False,
    allow_aromatic_ring_closure: bool = False,
) -> dict[str, Any] | None:
    """将入选的 S5 候选产物通过 `compile_recorded_reaction` 编译为正规可执行的 `ReactionSpec`。

    同时执行 `prepare_hypothesis` + `execute_atomtool_expansion` + `audit_hypothesis` (`ADMISSION_SUBMITTABLE`)
    全链路预检，编译或审计不过的自动剔除。
    """
    from pathway_v43.pollutant.audit import audit_hypothesis, decide_admission
    from pathway_v43.pollutant.chemstate import build_chemical_state, strict_identity_of
    from pathway_v43.pollutant.path_context import build_path_context
    from pathway_v43.pollutant.production import (
        ADMISSION_SUBMITTABLE,
        execute_atomtool_expansion,
        prepare_hypothesis,
    )
    from pathway_v43.pollutant.recorded_source import compile_recorded_reaction

    cand_raw = str(_cand_field(cand, "cand_smiles", "") or _cand_field(cand, "product_smiles", "") or "").strip()
    if not cand_raw or not str(substrate_smiles or "").strip():
        return None
    try:
        sub_iso = strict_identity_of(str(substrate_smiles or "").strip())
        cand_iso = strict_identity_of(cand_raw)
    except Exception:
        return None
    if not sub_iso or not cand_iso or cand_iso == sub_iso:
        return None

    env_rules = sorted(_cand_field(cand, "env_rule_ids", None) or [])
    rr_rules = sorted(_cand_field(cand, "rr_rule_ids", None) or [])
    primary_rule = (env_rules[0] if env_rules else (rr_rules[0] if rr_rules else f"s5_{index:02d}"))
    record_id = f"s5-hybrid:{primary_rule}:{index:02d}"

    primary_attempts: list[tuple[str, list[str], str | None]] = [
        (sub_iso, [cand_iso], cand_iso),
    ]
    for cop_list in (coproduct_sets or [])[:2]:
        if cop_list:
            primary_attempts.append((sub_iso, [cand_iso, *cop_list], cand_iso))

    def _try_compile_batch(attempts: list[tuple[str, list[str], str | None]]) -> tuple[dict[str, Any] | None, str]:
        last_reason = ""
        for donor_smi, prod_list, novel_p1 in attempts:
            try:
                res = compile_recorded_reaction(
                    substrate_smiles=sub_iso,
                    donor_smiles=donor_smi,
                    products=prod_list,
                    record_id=record_id,
                    novel_product_first_principal=novel_p1,
                    extended_stereo_dissolution=extended_stereo_dissolution,
                    stereo_edit_graceful_fallback=(
                        stereo_edit_graceful_fallback),
                    allow_ring_cleavage_and_fused_dearomatization=(
                        allow_ring_cleavage_and_fused_dearomatization),
                    # v1.4 T14-4:编译器 v2 两开关(默认关 ⇒ 逐字节同)
                    retained_tetrahedral_parity_check=(
                        retained_tetrahedral_parity_check),
                    allow_aromatic_ring_closure=allow_aromatic_ring_closure,
                )
            except Exception:
                continue
            if res.get("status") != "compiled":
                last_reason = str(res.get("reason") or "")
                continue
            spec = dict(res["spec"])
            p1_gate = res.get("novel_p1_gate")
            if isinstance(p1_gate, dict) and p1_gate.get("gate_ok"):
                if p1_gate.get("compiled_coproducts") is not None:
                    spec["coproducts"] = list(p1_gate["compiled_coproducts"])
                if p1_gate.get("undeclared_coproducts"):
                    spec["undeclared_coproducts"] = list(p1_gate["undeclared_coproducts"])
            else:
                parts = [str(spec.get("product_smiles") or ""), *[str(c) for c in (spec.get("coproducts") or [])]]
                non_principal = [
                    p for p in parts if p and k_strict(p) != cand_iso
                ]
                if non_principal:
                    spec["coproducts"] = non_principal
            # 固定主产物为 cand_iso（避免记录侧 Uncharger 形式归一将离子态金标候选改写为中性分子导致主产物身份漂移）
            spec["product_smiles"] = cand_iso
            return spec, ""
        return None, last_reason

    compiled_spec, fail_reason = _try_compile_batch(primary_attempts)
    if compiled_spec is None and fail_reason in (
        "",
        "no_structure_correspondence",
        "new_atom_placement_incomplete",
        "product_set_mismatch",
        "no_alignment",
    ):
        inferred_sets = _infer_s5_leaving_coproduct_sets(sub_iso, cand_iso)
        secondary_attempts: list[tuple[str, list[str], str | None]] = [
            (sub_iso, [cand_iso], None),
        ]
        for inferred_cops in inferred_sets[:2]:
            if inferred_cops:
                secondary_attempts.append((sub_iso, [cand_iso, *inferred_cops], cand_iso))
        secondary_attempts.append((cand_iso, [cand_iso], cand_iso))
        compiled_spec, _ = _try_compile_batch(secondary_attempts)

    if compiled_spec is None:
        return None

    rule_slug = "".join(ch if ch.isalnum() else "_" for ch in primary_rule).strip("_") or f"r{index:02d}"
    prior_score = round(float(_cand_field(cand, "prior_score", 0.0) or _cand_field(cand, "s5_prior_score", 0.0) or 0.0), 4)
    prior_tier = str(_cand_field(cand, "prior_tier", "") or _cand_field(cand, "s5_prior_tier", "") or "MODERATE_SINGLE")
    rxn_class_12 = str(_cand_field(cand, "fine_cat", "") or _cand_field(cand, "reaction_class_12", "") or "other_transformation")
    src_fams = sorted(list(_cand_field(cand, "source_families", None) or _cand_field(cand, "sources", None) or ["envipath"]))

    compiled_spec["key"] = f"s5-{index:02d}-{rule_slug}"
    compiled_spec["transformation_ref"] = f"s5-rule:{primary_rule}"
    compiled_spec["origin_group_key"] = f"s5-hybrid:{cand_iso}"
    compiled_spec["coefficient"] = int(compiled_spec.get("coefficient", 1) or 1)
    compiled_spec["selection_channels"] = list(src_fams)
    compiled_spec["analog_rank"] = 100 + int(index)
    compiled_spec["s5_prior_score"] = prior_score
    compiled_spec["s5_prior_tier"] = prior_tier
    compiled_spec["reaction_class_12"] = rxn_class_12
    compiled_spec["source_families"] = list(src_fams)
    compiled_spec["is_gated_supplement"] = bool(is_gated_supplement)

    compile_meta = dict(compiled_spec.get("compile") or {})
    compile_meta.update(
        {
            "source_kind": "s5_hybrid_rule",
            "primary_rule_id": primary_rule,
            "s5_prior_score": prior_score,
            "s5_prior_tier": prior_tier,
            "reaction_class_12": rxn_class_12,
            "source_families": list(src_fams),
            "is_gated_supplement": bool(is_gated_supplement),
        }
    )
    compiled_spec["compile"] = compile_meta

    # 验证 RDKit 正规工具执行 + 11 项 audit_hypothesis 准入通过
    try:
        sub_state = build_chemical_state(
            sub_iso, "raw_input", [{"record": f"s5-hybrid:{primary_rule}"}]
        )
        prepared = prepare_hypothesis(
            compiled_spec,
            parent_path_id="p0",
            substrate_state=sub_state,
            transformation_ref=str(
                compiled_spec.get("transformation_ref")
                or f"s5-rule:{primary_rule}"
            ),
        )
        exec_in = str(
            prepared["tool_inputs"].get("execution_input_smiles") or sub_iso
        )
        exec_res = execute_atomtool_expansion(
            substrate_smiles=exec_in, tool_inputs=prepared["tool_inputs"]
        )
        if not exec_res.get("execution_ok"):
            return None
        audit_rep = audit_hypothesis(
            prepared["hypothesis"],
            run_id="s5-compile-check",
            states=prepared["states"],
            context=build_path_context(condition_facts=[], scenario_ref=""),
            center_evidence=exec_res["center_evidence"],
        )
        disp, _reasons = decide_admission(audit_rep)
        if disp not in ADMISSION_SUBMITTABLE:
            return None
        spec_principal = strict_identity_of(
            str(compiled_spec.get("product_smiles") or "")
        )
        prod_state_stricts = {
            strict_identity_of(str(st.smiles_isomeric))
            for st in (prepared.get("product_states") or [])
            if getattr(st, "smiles_isomeric", "")
        }
        if not spec_principal or spec_principal not in prod_state_stricts:
            return None
    except Exception:
        return None

    return compiled_spec


def _extract_s1d_channels_and_families(spec: dict[str, Any]) -> tuple[set[str], set[str]]:
    """从 S1d 预编译条目及其合并谱系键提取真实通道集合与来源家族集合。"""
    channels: set[str] = set()
    families: set[str] = set()
    raw_keys = [
        str(spec.get("key") or ""),
        *[str(k) for k in ((spec.get("compile") or {}).get("merged_source_keys") or [])],
    ]
    for rk in raw_keys:
        if not rk:
            continue
        if rk.startswith("rec-corpus"):
            channels.add("corpus")
            families.add("corpus")
        elif rk.startswith("rec-"):
            channels.add("recorded")
            families.add("recorded")
        elif rk.startswith("tpl-"):
            channels.add("analog")
            families.add("analog")
        elif rk.startswith("retro-"):
            channels.add("retrorules")
            families.add("rr_rhea")
    for ch in (spec.get("selection_channels") or []):
        ch_s = str(ch).strip().lower()
        if ch_s in ("recorded", "corpus", "analog"):
            channels.add(ch_s)
            families.add(ch_s)
        elif ch_s in ("envipath", "eawag", "rr_rhea", "rr_mnx"):
            families.add(ch_s)
    if not channels:
        channels.add("analog")
    if not families:
        families.add("analog")
    return channels, families


def build_s5_hybrid_pool_entries(
    substrate_smiles: str,
    *,
    s1d_specs: list[dict[str, Any]] | None = None,
    domain: str = "298",
    include_env: bool = True,
    include_rr: bool = True,
    rr_datasets: tuple[str, ...] = ("rhea", "mnx"),
    rr_radii: tuple[int, ...] = (2, 4, 6),
    extra_rules: list[dict[str, Any]] | None = None,
    s5_supplement_gate_max_s1d: int = 2,
    s5_supplement_min_prior_score: float = 70.0,
    s5_super_consensus_score: float = 115.0,
    s5_max_supplements: int = 2,
    max_pool: int = 16,
    include_s1d_in_return: bool = True,
    repo_root: str | Path | None = None,
    enumerated_injection_k: int = 0,
    enumerated_rule_priors: dict[str, int] | None = None,
    v14_compiler_ext: bool = False,
    v14_compiler_ext_2: bool = False,
    no_self: bool = False,
    question_meta: dict | None = None,
    exclude_substrate_keys: set[str] | None = None,
    drop_rule_ids: set[str] | None = None,
    filter_stats: dict | None = None,
) -> list[dict[str, Any]]:
    """管线级 S1d + S5 (enviPath + EAWAG + RetroRules) 12 大类均衡混合建池与化学先验编译入口。

    1. 对现有 S1d 模板条目与 S5 (`S5-env ∪ S5-rr`) 规则枚举产物统一计算 `compute_chemical_prior_score`
       与 12 反应大类标签 `classify_reaction_12class`；
    2. 为现有 S1d 条目补充跨源共识先验元数据（若某 S1d 产物同时被 S5 规则命中，自动升位为多源共识）；
    3. 按 `rank_and_select_hybrid_pool` (12 大类反应多样性均衡) 选取 Top-`max_pool` (默认 16) 混合候选池，
       并将排进 Top-16 的 S5 候选编译为正规 `ReactionSpec`（不再因 `len(s1d) > 2` 误挡 S5 入池或限死 2 条）；
    4. 将智能门控标记 `is_gated_supplement` 与 `s5_prior_score` 写入池条目元数据，仅供 `runflow.py`
       在模型回答后的未选中尾部槽位（Slots 4–5）回填时使用。
    """
    sub_smi = str(substrate_smiles or "").strip()
    if not sub_smi:
        return list(s1d_specs or []) if include_s1d_in_return else []

    s5_map = enumerate_s5_rules(
        sub_smi,
        repo_root=repo_root,
        include_env=include_env,
        include_rr=include_rr,
        rr_datasets=rr_datasets,
        rr_radii=rr_radii,
        extra_rules=extra_rules,
        no_self=no_self,
        question_meta=question_meta,
        exclude_substrate_keys=exclude_substrate_keys,
        drop_rule_ids=drop_rule_ids,
        filter_stats=filter_stats,
    )

    cand_by_strict: dict[str, HybridCandidate] = {}
    s1d_strict_set: set[str] = set()

    for rank_idx, spec in enumerate(s1d_specs or [], 1):
        prod_smi = str(spec.get("product_smiles") or "").strip()
        prod_st = k_strict(prod_smi)
        if not prod_st:
            continue
        s1d_strict_set.add(prod_st)
        channels, fams = _extract_s1d_channels_and_families(spec)
        raw_sim = (
            spec.get("best_similarity")
            if spec.get("best_similarity") is not None
            else (spec.get("compile") or {}).get("best_similarity")
        )
        if raw_sim is not None:
            sim_val = float(raw_sim)
        else:
            sim_val = 1.0 if ("recorded" in channels or "corpus" in channels) else 0.45

        existing_hc = cand_by_strict.get(prod_st)
        if existing_hc is None:
            coarse_6, fine_12 = classify_reaction_12class(sub_smi, prod_smi)
            f_delta = compute_formula_delta_str(sub_smi, prod_smi)
            ha_ratio = _compute_heavy_atom_ratio(sub_smi, prod_smi)
            hc = HybridCandidate(
                cand_strict=prod_st,
                cand_smiles=prod_smi,
                sub_smiles=sub_smi,
                source_families=set(fams),
                s1d_best_rank=rank_idx,
                s1d_best_sim=sim_val,
                s1d_channels=set(channels),
                coarse_cat=coarse_6,
                fine_cat=fine_12,
                formula_delta=f_delta,
                heavy_atom_ratio=ha_ratio,
            )
            cand_by_strict[prod_st] = hc
        else:
            existing_hc.source_families.update(fams)
            existing_hc.s1d_channels.update(channels)
            if sim_val > existing_hc.s1d_best_sim:
                existing_hc.s1d_best_sim = sim_val

    for prod_st, rec in s5_map.items():
        prod_smi = str(rec["cand_smiles"])
        hc = cand_by_strict.get(prod_st)
        if hc is None:
            coarse_6, fine_12 = classify_reaction_12class(sub_smi, prod_smi)
            f_delta = compute_formula_delta_str(sub_smi, prod_smi)
            ha_ratio = _compute_heavy_atom_ratio(sub_smi, prod_smi)
            hc = HybridCandidate(
                cand_strict=prod_st,
                cand_smiles=prod_smi,
                sub_smiles=sub_smi,
                source_families=set(rec["source_families"]),
                env_rule_ids=set(rec["env_rule_ids"]),
                env_freq_sum=int(rec["env_freq_sum"]),
                rr_rule_ids=set(rec["rr_rule_ids"]),
                rr_max_radius=int(rec["rr_max_radius"]),
                rr_freq_sum=int(rec["rr_freq_sum"]),
                coarse_cat=coarse_6,
                fine_cat=fine_12,
                formula_delta=f_delta,
                heavy_atom_ratio=ha_ratio,
            )
            cand_by_strict[prod_st] = hc
        else:
            hc.source_families.update(rec["source_families"])
            hc.env_rule_ids.update(rec["env_rule_ids"])
            hc.env_freq_sum += int(rec["env_freq_sum"])
            hc.rr_rule_ids.update(rec["rr_rule_ids"])
            hc.rr_max_radius = max(hc.rr_max_radius, int(rec["rr_max_radius"]))
            hc.rr_freq_sum += int(rec["rr_freq_sum"])

    for hc in cand_by_strict.values():
        compute_chemical_prior_score(hc, domain=domain)

    annotated_s1d: list[dict[str, Any]] = []
    s1d_specs_by_strict: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for spec in s1d_specs or []:
        spec_copy = dict(spec)
        prod_st = k_strict(str(spec_copy.get("product_smiles") or ""))
        hc = cand_by_strict.get(prod_st) if prod_st else None
        if hc is not None:
            prior_val = round(float(hc.prior_score), 4)
            src_fams = sorted(hc.source_families)
            spec_copy["s5_prior_score"] = prior_val
            spec_copy["s5_prior_tier"] = str(hc.prior_tier)
            spec_copy["reaction_class_12"] = str(hc.fine_cat)
            spec_copy["source_families"] = src_fams
            spec_copy["is_gated_supplement"] = False
            c_meta = dict(spec_copy.get("compile") or {})
            c_meta.update(
                {
                    "s5_prior_score": prior_val,
                    "s5_prior_tier": str(hc.prior_tier),
                    "reaction_class_12": str(hc.fine_cat),
                    "source_families": src_fams,
                    "is_gated_supplement": False,
                }
            )
            spec_copy["compile"] = c_meta
        annotated_s1d.append(spec_copy)
        if prod_st:
            s1d_specs_by_strict[prod_st].append(spec_copy)

    # 尾部回填门控标记（仅作用于 runflow.py 尾部空槽回填，不阻挡 S5 候选在建池阶段进入 Top-16 混合池）
    sparse_gate_open = len(annotated_s1d) <= int(s5_supplement_gate_max_s1d)

    all_cands = list(cand_by_strict.values())
    ranked_top = rank_and_select_hybrid_pool(
        all_cands,
        max_pool=int(max_pool),
        class_balanced=True,
        max_per_class_pass1=3,
    )
    ranked_top_stricts = {c.cand_strict for c in ranked_top}
    remaining_cands = sorted(
        [c for c in all_cands if c.cand_strict not in ranked_top_stricts],
        key=lambda c: (-c.prior_score, abs(1.0 - c.heavy_atom_ratio), c.cand_strict),
    )
    ordered_eval_cands = ranked_top + remaining_cands[:4]

    selected_pool_specs: list[dict[str, Any]] = []
    compiled_supplements: list[dict[str, Any]] = []
    s5_compile_idx = 0

    for hc in ordered_eval_cands:
        if include_s1d_in_return and len(selected_pool_specs) >= int(max_pool):
            break
        if not include_s1d_in_return and len(compiled_supplements) >= int(max_pool):
            break

        if hc.cand_strict in s1d_specs_by_strict:
            if include_s1d_in_return:
                primary_s1d = s1d_specs_by_strict[hc.cand_strict][0]
                if primary_s1d not in selected_pool_specs:
                    selected_pool_specs.append(primary_s1d)
            continue

        s5_compile_idx += 1
        rec = s5_map.get(hc.cand_strict, {})
        is_gated = bool(
            sparse_gate_open
            or float(hc.prior_score) >= float(s5_super_consensus_score)
        )
        spec = compile_s5_candidate_to_spec(
            sub_smi,
            hc,
            index=s5_compile_idx,
            is_gated_supplement=is_gated,
            coproduct_sets=rec.get("coproduct_sets"),
            extended_stereo_dissolution=bool(v14_compiler_ext),
            stereo_edit_graceful_fallback=bool(v14_compiler_ext),
            allow_ring_cleavage_and_fused_dearomatization=bool(
                v14_compiler_ext),
            # v1.4 T14-4:编译器 v2 两开关(默认关 ⇒ 调用参数逐字节同)
            retained_tetrahedral_parity_check=bool(v14_compiler_ext_2),
            allow_aromatic_ring_closure=bool(v14_compiler_ext_2),
        )
        if spec is not None:
            compiled_supplements.append(spec)
            if include_s1d_in_return:
                selected_pool_specs.append(spec)

    if not include_s1d_in_return:
        return compiled_supplements[: int(max_pool)]

    # 若 Top-16 仍有剩余空位，用尚未入选的其余 S1d 候选补足
    for s1d_sp in annotated_s1d:
        if len(selected_pool_specs) >= int(max_pool):
            break
        if s1d_sp not in selected_pool_specs:
            selected_pool_specs.append(s1d_sp)

    selected_pool_specs = selected_pool_specs[: int(max_pool)]
    if int(enumerated_injection_k) > 0 and enumerated_rule_priors:
        from .enumerated_injection import inject_enumerated_candidates

        selected_pool_specs, _injection_report = inject_enumerated_candidates(
            sub_smi,
            selected_pool_specs,
            k=int(enumerated_injection_k),
            rule_priors=dict(enumerated_rule_priors),
            max_pool=int(max_pool),
        )
    return selected_pool_specs


def _calibrated_prior_score(c: dict[str, Any]) -> float:
    p = float(c["prior"])
    if c["is_tpl"] and c["raw_sim"] < 0.65:
        p -= (0.65 - c["raw_sim"]) * 90.0
    if c["is_rec"] or c["raw_sim"] >= 0.98:
        p += 25.0
    elif c["raw_sim"] >= 0.85:
        p += 12.0
    if c["is_novel"] and c["cb"]:
        p += 35.0
    return p


def calibrate_submittable_ranking(
    *,
    selected_top_keys: list[str],
    prepared_entries: list[tuple[str, dict[str, Any], dict[str, Any]]],
    deduped_indices: list[int],
    pool_specs: list[dict[str, Any]],
    verified_by_key: dict[str, bool],
    prod_strict_by_key: dict[str, str],
    novel_entry_idx: set[int],
    target_slots: int = 5,
    v13_rank_rules: bool = False,
    v13_stage1_rank: bool = False,
    stage1_routing: dict[str, Any] | None = None,
    substrate_smiles: str = "",
    stage1_params: dict[str, Any] | None = None,
    stage1_debug_sink: dict[str, Any] | None = None,
    v13_multi_sample_consensus: bool = False,
    v13_consensus_params: dict[str, Any] | None = None,
    secondary_ranked_keys_list: list[list[str]] | None = None,
    v13_consensus_debug_sink: dict[str, Any] | None = None,
    consensus_pass_mode: str = "",
    collect_pass_debug: bool = False,
    secondary_eligible_keys_list: list[list[str] | None] | None = None,
    enable_v14_cross_pool_elig_norm: bool = False,
) -> list[str]:
    """DECISION-9 方向 3（v44-Next v1.2 候选排序器校准）：
    仅在已通过编译+执行+11项审计的合法候选集合上执行确定性校准：
    - Step A: 当尾部 Slot 5 为弱支撑项且存在未入选的 Pool[0..1] 精确底物/超强跨源共识锚点时，将其补入 Slot 5；
    - Step B: 基于来源类型、Tanimoto 相似度、跨源共识与化学先验分对 Slot 1..5 消解弱相似/低先验诱饵占优。

    v1.3 T12-B（默认关）：``v13_stage1_rank=True`` 且给出解析成功的
    ``stage1_routing`` ⇒ 在最末一步按 Stage-1 预测大类做零删除精排
    （``ranking_rules_v13.apply_stage1_class_calibration``）。关闭时
    本函数行为与改前逐字节一致。``stage1_debug_sink`` 只做研究期机读
    记录（调用方决定落盘位置），不参与任何判据。

    v1.3 T13-B（默认关）：``v13_multi_sample_consensus=True`` 且给出
    **非空**的 ``secondary_ranked_keys_list``（次级 pass 的模型排序键
    列表）⇒ 不用选定的 Stage-1 精排，而是把「主 pass + 每个次级 pass」
    各跑一遍上述单 pass 流水线（Step A + Step B + 尾部排序 +
    apply_v13_rank_rules），再用 ``consensus_v13.fuse_multi_sample_top5``
    做 RRF + Stage-1 加成的零删除位次融合。要点：

    - 每个 pass 的 ``order_keys`` 只决定该 pass 的 top-5 子集与位次；
      Step A/B 只在该子集 + 池其余合法候选内搬运，**不新增**候选；
    - 融合只对既有合法候选重排（零删除：未入选者仍在池内，只是位次
      更后），落账仍走既有调度/提交面；
    - 共识路径**不**再调用 ``apply_stage1_class_calibration``（Stage-1
      只作融合加项/保护，避免同一信号两次生效）；``v13_stage1_rank``
      与 ``v13_multi_sample_consensus`` 的互斥由 Driver 层 fail-closed；
    - ``v13_multi_sample_consensus=True`` 但没有次级 pass（或全为空
      列表）⇒ 退回默认单 pass 路径（逐字节同关闭态），只把
      ``skipped=no_secondary_passes`` 写进 debug sink；
    - ``v13_consensus_debug_sink`` 只在开关打开时写入；关闭时不触碰
      （零漂移）。

    v1.4 T14-1A（默认关）：``consensus_pass_mode``（显式参数，或
    ``v13_consensus_params["consensus_pass_mode"]``）控制**共识路径各
    pass** 是否在送入融合前被 v1.1 遗留启发式改写首位：

    - ``"calibrated"``（默认）：与改前逐位一致（Rule 1..7 全量）；
    - ``"raw_v13"``：各 pass 跳过 Rule 1..7 强制换首与 Slot 2..5 高位
      重排，只保留候选构建 + Step A 槽位 5 兜底 + ``apply_v13_rank_rules``
      ⇒ 送进共识的是模型原始合法序（单路规则不再提前扼杀跨路一致候选）；
    - ``"guarded_r2_r7"``：只收紧 Rule 2 与 Rule 7 —— Rule 2 仅当挑战者
      ``is_rec`` 或 ``raw_sim >= 0.80`` 才允许置换无共识背书的 ``novel``
      榜首；Rule 7 仅当 ``c1`` **不**匹配 Stage-1 ``primary_class`` /
      ``secondary_classes`` 时才允许置换。

    三个值都在**共识未参与时**退回默认路径（零漂移）；未知值 ⇒
    ``"calibrated"``（fail-safe，不静默扩权）。

    v1.4 T14-4（默认关）：``enable_v14_cross_pool_elig_norm=True`` 且给出
    ``secondary_eligible_keys_list``（与 ``secondary_ranked_keys_list``
    **1:1** 对齐的每 pass 资格键集合；``None`` = 该 pass 无资格信息）⇒

    - 共识融合对池候选的 RRF 乘跨池资格率因子
      ``(n_pool_passes+alpha)/(n_elig+alpha)``（只在
      ``min_elig <= n_elig < n_pool_passes`` 时），并启用资格感知全票锁
      （见 ``consensus_v13.fuse_multi_sample_top5``）；
    - 次级 pass 的 Step A 只从**该 pass 资格集内**的剩余候选里兜底补位
      （资格集外的池锚不再跨池搬运）。

    关闭时不读写这两个参数 ⇒ 与改前逐位一致。
    """
    pool_entries = [dict(pe) for pe in (pool_specs or [])]
    for idx, pe in enumerate(pool_entries):
        pe["_pool_idx"] = idx
    # v1.3 T12-B：Stage-1 精排是否激活（只依赖开关与底物；提前到候选
    # 构建前，供实例级 hypothesis id 标注使用，不改变任何判据）。
    stage1_active = bool(v13_stage1_rank) and bool(str(substrate_smiles or ""))
    consensus_lists: list[list[str]] = []
    consensus_elig_lists: list[set[str] | None] = []
    _elig_source = list(secondary_eligible_keys_list or [])
    for _pass_idx, keys in enumerate(secondary_ranked_keys_list or []):
        if not keys:
            # 与改前同一条过滤：空 pass 不进共识，资格集同位置一起丢
            # ⇒ 两列表始终 1:1。
            continue
        consensus_lists.append([str(key) for key in keys if str(key)])
        if _pass_idx < len(_elig_source):
            _eligible = _elig_source[_pass_idx]
            consensus_elig_lists.append(
                None if _eligible is None
                else {str(k) for k in _eligible if str(k)})
        else:
            consensus_elig_lists.append(None)
    consensus_engaged = bool(v13_multi_sample_consensus) and bool(
        consensus_lists)
    # v1.4 T14-4：跨池资格率归一化只在共识真正参与、且至少一个 pass 给出
    # 资格集时生效（开关关闭或全 None ⇒ 与改前逐位一致）。
    elig_norm_enabled = (
        bool(enable_v14_cross_pool_elig_norm)
        and bool(consensus_engaged)
        and any(el is not None for el in consensus_elig_lists))
    # v1.4 T14-1A：共识各 pass 的 Rule 1..7 处理模式（默认 "calibrated" =
    # 与改前逐位一致；共识未参与时恒为默认 ⇒ 零漂移）。
    _CONSENSUS_PASS_MODES = ("calibrated", "raw_v13", "guarded_r2_r7")
    _requested_pass_mode = str(consensus_pass_mode or "").strip().lower()
    if not _requested_pass_mode:
        _requested_pass_mode = str(
            (v13_consensus_params or {}).get("consensus_pass_mode") or ""
        ).strip().lower()
    if _requested_pass_mode not in _CONSENSUS_PASS_MODES:
        _requested_pass_mode = "calibrated"
    effective_pass_mode = (
        _requested_pass_mode if consensus_engaged else "calibrated")
    rule_primary, rule_secondary = "", ()
    if effective_pass_mode == "guarded_r2_r7":
        from .consensus_v13 import routing_classes as _routing_classes

        rule_primary, rule_secondary = _routing_classes(stage1_routing)
    # T13-B：共识路径需要 ``cls`` 标签（融合的 Stage-1 加项/保护）；
    # 只在共识真正参与时扩展标注面 ⇒ 默认路径零漂移。
    # v1.4 T14-0：研究期候选 dump 需要实例级 hyp id / 类别标签才能与
    # 冻结 flips 的金标事件对齐；dump sink 只在诊断重放（env 显式开启）
    # 时非 None ⇒ 生产路径零漂移。
    labeling_active = bool(str(substrate_smiles or "")) and (
        stage1_active or consensus_engaged
        or (collect_pass_debug and stage1_debug_sink is not None))
    pool_by_id = {
        str(pe.get("key") or pe.get("id") or pe.get("entry_id") or f"spec-{idx}"): pe
        for idx, pe in enumerate(pool_entries)
    }
    pool_p_stricts: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for pe in pool_entries:
        ps = str(pe.get("product_smiles") or (pe.get("reaction_spec") or {}).get("product_smiles") or "")
        if ps:
            st = k_strict(ps)
            if st:
                pool_p_stricts[st].append(pe)

    # ---- 候选行基线（与 pass 无关的身份/事实；位次字段由 _single_pass
    # 按各自 order_keys 写入副本）----
    base_rows: list[dict[str, Any]] = []

    for orig_idx, (key, spec, _prep) in zip(deduped_indices, prepared_entries):
        if not verified_by_key.get(key, False):
            continue
        src = str(key)
        pe = pool_by_id.get(src, {})
        c_meta = spec.get("compile") or pe.get("compile") or {}
        p_smi = str(spec.get("product_smiles") or pe.get("product_smiles") or "")
        p_st = prod_strict_by_key.get(key) or k_strict(p_smi)
        p_has_c = _smiles_has_carbon(p_smi)

        cb_list = pool_p_stricts.get(p_st, [])
        cb_max_prior = max(
            [
                float(x.get("s5_prior_score") or (x.get("compile") or {}).get("s5_prior_score") or 0.0)
                for x in cb_list
            ],
            default=0.0,
        )
        cb_max_sim = max(
            [
                float(x.get("best_similarity") or (x.get("compile") or {}).get("best_similarity") or 0.0)
                for x in cb_list
            ],
            default=0.0,
        )
        cb_min_pidx = min([int(x.get("_pool_idx", 99)) for x in cb_list], default=99)

        all_fams: set[str] = set(spec.get("source_families") or c_meta.get("source_families") or [])
        for x in cb_list:
            all_fams.update(x.get("source_families") or (x.get("compile") or {}).get("source_families") or [])

        raw_sim = float(
            pe.get("best_similarity")
            or c_meta.get("best_similarity")
            or (1.0 if src.startswith("rec-") else 0.0)
        )
        raw_prior = float(spec.get("s5_prior_score") or c_meta.get("s5_prior_score") or 0.0)
        is_novel = src.startswith("novel-") or (int(orig_idx) in novel_entry_idx)

        cand_row = {
            "src": src,
            "p_smi": p_smi,
            "p_st": p_st,
            "p_has_c": p_has_c,
            # 未进入该 pass top-5 时的既有确定性位次（原式：
            # 99 + 池序；非池条目 = 99 + 99）。
            "_off_eff_rk": 99 + int(pe.get("_pool_idx", 99)),
            "eff_rk": 0,
            "is_novel": is_novel,
            "is_rec": src.startswith("rec-"),
            "is_tpl": src.startswith("tpl-"),
            "is_s5": src.startswith("s5-"),
            "sim": max(raw_sim, cb_max_sim if is_novel else 0.0),
            "raw_sim": raw_sim,
            "prior": max(raw_prior, cb_max_prior),
            "raw_prior": raw_prior,
            "fams": sorted(all_fams),
            "n_fams": len(all_fams),
            "pidx": int(pe.get("_pool_idx", cb_min_pidx if is_novel else 99)),
            "cb": (len(cb_list) > 0) if is_novel else (len(cb_list) > 1 or len(all_fams) >= 2),
            "in_top5_v11": False,
            # v1.3 T1-C：机理规则消费的既有事实（共产物声明完整性）
            "undeclared": list(
                pe.get("undeclared_coproducts")
                or c_meta.get("undeclared_coproducts")
                or []
            ),
        }
        if labeling_active:
            # 实例级 hypothesis id（src 不是唯一键：同键可能对应不同池
            # 位置的多个实例；只供研究期 dump 关联事件，不参与排序）。
            cand_row["_hyp_id"] = str(_prep["hypothesis"].hypothesis_id)
        base_rows.append(cand_row)

    # ---- 候选确定性 12 类标注（Stage-1 精排或共识融合需要时计算）----
    if labeling_active:
        def _label(cand: dict[str, Any]) -> str:
            try:
                return str(classify_reaction_12class(
                    str(substrate_smiles),
                    str(cand.get("p_smi") or ""))[1])
            except Exception:  # noqa: BLE001 —— 如实 unknown，不猜类别
                return "other_unknown"

        _cls_cache: dict[str, str] = {}
        for cand in base_rows:
            key = str(cand.get("p_st") or cand.get("p_smi") or "")
            if key not in _cls_cache:
                _cls_cache[key] = _label(cand)
            cand["cls"] = _cls_cache[key]

    def _single_pass(order_keys: list[str], *, apply_stage1: bool,
                     rule_mode: str = "calibrated", pass_index: int = 0,
                     elig_keys: set[str] | None = None
                     ) -> tuple[list[dict[str, Any]], list[dict[str, Any]],
                                list[dict[str, Any]]]:
        """单 pass 校准流水线（改前 ``calibrate_submittable_ranking`` 主体
        等价搬移）：``order_keys`` = 该 pass 的模型排序键（1 基位次，截断
        至 ``target_slots``）。

        ``rule_mode``（v1.4 T14-1A，默认 ``"calibrated"`` = 改前逐位一致）：
        ``"raw_v13"`` 跳过 v1.1 Rule 1..7 强制换首与 Slot 2..5 重排；
        ``"guarded_r2_r7"`` 只收紧 Rule 2 / Rule 7（见函数 docstring）。

        ``pass_index``（v1.4 T14-0，默认 0）：只写进 debug sink 的 pass
        记录，不参与任何判据；``stage1_debug_sink is None`` 时零开销。

        ``elig_keys``（v1.4 T14-4，默认 ``None`` = 不限制）：该 pass 的
        资格键集合；非 ``None`` 时 Step A 只从集合内的剩余候选兜底补位
        （资格集外的池锚不再跨池搬运）。Step B/规则链不受影响。
        """
        def _debug_row(c: dict[str, Any]) -> dict[str, Any]:
            """候选行的机读快照（只进 debug sink；含未脱敏结构，只允许
            写入 gitignored 研究目录）。"""
            return {
                "src": str(c.get("src") or ""),
                "hyp_id": str(c.get("_hyp_id") or ""),
                "p_smi": str(c.get("p_smi") or ""),
                "p_st": str(c.get("p_st") or ""),
                "cls": str(c.get("cls") or ""),
                "is_rec": bool(c.get("is_rec")),
                "is_tpl": bool(c.get("is_tpl")),
                "is_s5": bool(c.get("is_s5")),
                "is_novel": bool(c.get("is_novel")),
                "raw_sim": float(c.get("raw_sim") or 0.0),
                "prior": float(c.get("prior") or 0.0),
                "n_fams": int(c.get("n_fams") or 0),
                "pidx": int(c.get("pidx") or 99),
                "cb": bool(c.get("cb")),
                "eff_rk": int(c.get("eff_rk") or 0),
                "undeclared": list(c.get("undeclared") or []),
                "in_top5": bool(c.get("in_top5_v11")),
            }

        def _record_pass(*, top5_now: list[dict[str, Any]],
                         head_pre_rules: str, rule_fires: list[dict[str, Any]],
                         top5_pre_rules: list[str]) -> None:
            """把本 pass 的规则账本写进 debug sink（未显式开启时零操作）。"""
            if not collect_pass_debug or stage1_debug_sink is None:
                return
            stage1_debug_sink.setdefault("pass_details", []).append({
                "pass_index": int(pass_index),
                "rule_mode": str(rule_mode),
                "n_candidates": len(rows),
                "head_pre_rules": str(head_pre_rules),
                "head_after": (
                    str(top5_now[0].get("src") or "") if top5_now else ""),
                "top5_pre_rules": list(top5_pre_rules),
                "top5_after": [str(c.get("src") or "") for c in top5_now],
                "rule_fires": list(rule_fires),
                "top5_candidates": [_debug_row(c) for c in top5_now],
                "rest_candidates": [_debug_row(c) for c in rest],
            })

        top_index_map = {
            str(k): i + 1
            for i, k in enumerate(
                (order_keys or [])[: max(0, int(target_slots))])
        }
        rows: list[dict[str, Any]] = []
        for base in base_rows:
            row = dict(base)
            src = str(row.get("src") or "")
            in_top5 = src in top_index_map
            row["in_top5_v11"] = in_top5
            row["eff_rk"] = (
                top_index_map[src] if in_top5
                else int(row.get("_off_eff_rk", 198)))
            row.pop("_off_eff_rk", None)
            rows.append(row)
        top5 = [c for c in sorted(rows, key=lambda x: x["eff_rk"])
                if c["in_top5_v11"]]
        rest = [c for c in rows if not c["in_top5_v11"]]
        seen_sts = {c["p_st"] for c in top5 if c["p_st"]}

        # Step A: Rescue unpicked super-consensus / exact-substrate pool anchors into Slot 5
        strong_unpicked = [
            c
            for c in rest
            if c["p_st"] not in seen_sts
            # v1.4 T14-4：跨池资格率归一化打开时，Step A 的兜底补位只允许
            # 本 pass 资格集内的候选（默认 None ⇒ 与改前逐位一致）。
            and (elig_keys is None or c["src"] in elig_keys)
            and (
                (c["pidx"] <= 1 and (c["is_rec"] or c["raw_sim"] >= 0.95) and c["prior"] >= 135.0)
                or (
                    c["pidx"] == 0
                    and c["n_fams"] >= 3
                    and c["prior"] >= 165.0
                    and (c["is_s5"] or c["raw_sim"] >= 0.70)
                )
            )
        ]
        strong_unpicked.sort(key=lambda c: (-_calibrated_prior_score(c), c["pidx"]))
        for anc in strong_unpicked[:1]:
            if len(top5) < int(target_slots):
                top5.append(anc)
                seen_sts.add(anc["p_st"])
            elif top5:
                tail = top5[-1]
                if (
                    not tail["is_rec"]
                    and tail["raw_sim"] < 0.85
                    and _calibrated_prior_score(tail) < 95.0
                    and not (tail["is_novel"] and tail["cb"])
                ):
                    top5[-1] = anc
                    seen_sts.add(anc["p_st"])

        if len(top5) <= 1:
            _record_pass(
                top5_now=top5,
                head_pre_rules=(str(top5[0].get("src") or "")
                                if top5 else ""),
                rule_fires=[],
                top5_pre_rules=[str(c.get("src") or "") for c in top5])
            return top5, rest, rows

        # v1.4 T14-0：规则前快照 + 逐规则账本（只进 debug sink）。
        _debug_on = collect_pass_debug and stage1_debug_sink is not None
        _head_pre_rules = str(top5[0].get("src") or "")
        _top5_pre_rules = [str(c.get("src") or "") for c in top5]
        _rule_fires: list[dict[str, Any]] = []

        c1 = top5[0]
        best_challenger: dict[str, Any] | None = None
        best_challenger_score = -1e9

        # v1.4 T14-1A：``raw_v13`` 不消费 v1.1 Rule 1..7（空区间 ⇒ 零换首），
        # 其余模式逐条判据不变（``guarded_r2_r7`` 只在 Rule 2/7 内收紧）。
        rule_indices = (range(1, len(top5))
                        if rule_mode != "raw_v13" else range(1, 1))
        for idx in rule_indices:
            cand = top5[idx]
            cand_cp = _calibrated_prior_score(cand)
            promote = False
            _rule_id = ""
            _guarded = False

            # Rule 1: Novel candidate at eff_rk == 2 with high-consensus pool backing (cb=True, prior>=140) when c1 is not recorded
            if (
                cand["is_novel"]
                and cand["cb"]
                and cand["eff_rk"] == 2
                and cand["prior"] >= 140.0
                and not c1["is_rec"]
            ):
                promote = True
                _rule_id = "R1"

            # Rule 2: c1 is an unbacked novel proposal (is_novel and not cb) when top5[1:] has a high-consensus pool anchor
            elif c1["is_novel"] and not c1["cb"]:
                if cand["prior"] >= 140.0 or cand["raw_sim"] >= 0.90:
                    # v1.4 guarded_r2_r7：挑战者须为 recorded 强锚点或
                    # raw_sim >= 0.80 的强相似同源候选，才允许置换 novel
                    # 榜首（prior 高但相似度低的通用规则不再盲踢）。
                    _rule_id = "R2"
                    if rule_mode == "guarded_r2_r7" and not (
                            cand["is_rec"] or cand["raw_sim"] >= 0.80):
                        promote = False
                        _guarded = True
                    else:
                        promote = True

            # Rule 3: c1 has an inorganic (0-carbon) principal product with low template similarity (raw_sim < 0.80) while cand at eff_rk == 2 has carbon
            elif (
                not c1["p_has_c"]
                and c1["raw_sim"] < 0.80
                and cand["p_has_c"]
                and cand["eff_rk"] == 2
                and cand["prior"] > c1["prior"]
            ):
                promote = True
                _rule_id = "R3"

            # Rule 4: c1 is a weak-similarity analog template (is_tpl and raw_sim < 0.45) at Pool[0..2]
            elif c1["is_tpl"] and c1["raw_sim"] < 0.45 and c1["pidx"] <= 2:
                if (cand["is_rec"] or cand["raw_sim"] >= 0.95) and cand["p_has_c"] and cand["prior"] >= 140.0:
                    promote = True
                    _rule_id = "R4"
                elif cand["is_s5"] and cand["pidx"] == 1 and cand["eff_rk"] == 2 and cand["prior"] >= 140.0:
                    promote = True
                    _rule_id = "R4"

            # Rule 5: c1 is a deep-pool low-prior decoy (pidx >= 4 and prior < 85.0)
            elif not c1["is_novel"] and c1["pidx"] >= 4 and c1["prior"] < 85.0 and c1["raw_sim"] < 0.85:
                if (
                    cand["pidx"] <= 1
                    and (cand["is_rec"] or cand["raw_sim"] >= 0.95)
                    and cand["prior"] >= 140.0
                    and not cand["src"].startswith("rec-rhea:")
                ):
                    promote = True
                    _rule_id = "R5"
                elif (
                    cand["pidx"] <= 2
                    and cand["is_s5"]
                    and cand["n_fams"] >= 3
                    and cand["prior"] >= 150.0
                    and c1["pidx"] >= 8
                ):
                    promote = True
                    _rule_id = "R5"

            # Rule 6: c1 is a low-prior S5 rule (is_s5, prior < 75.0, pidx >= 2) while cand is an exact-substrate Pool[0..1] template
            elif c1["is_s5"] and c1["prior"] < 75.0 and c1["pidx"] >= 2:
                if (
                    c1["n_fams"] == 1
                    and cand["pidx"] == 0
                    and (cand["is_rec"] or cand["raw_sim"] >= 0.98)
                    and cand["prior"] >= 140.0
                    and cand["eff_rk"] >= 3
                ):
                    promote = True
                    _rule_id = "R6"
                elif (
                    c1["prior"] < 68.0
                    and cand["pidx"] <= 1
                    and (cand["is_rec"] or cand["raw_sim"] >= 0.98)
                    and cand["prior"] >= 245.0
                    and not cand["src"].startswith("rec-rhea:")
                    and cand["eff_rk"] >= 3
                ):
                    promote = True
                    _rule_id = "R6"

            # Rule 7: c1 is a deeper-pool S5 rule (is_s5, pidx >= 3) while cand at eff_rk == 2 is the top S5 rule (pidx <= 1) with +15 prior
            elif (
                c1["is_s5"]
                and c1["pidx"] >= 3
                and cand["is_s5"]
                and cand["pidx"] <= 1
                and cand["eff_rk"] == 2
                and cand["prior"] >= c1["prior"] + 15.0
            ):
                # v1.4 guarded_r2_r7：c1 已匹配 Stage-1 primary/secondary
                # 大类时，pidx<=1 的通用 S5 不再无条件夺回首位的位次。
                _rule_id = "R7"
                _c1_cls = str(c1.get("cls") or "")
                _c1_stage1_match = bool(_c1_cls) and (
                    (_c1_cls == rule_primary) or (_c1_cls in rule_secondary))
                if rule_mode == "guarded_r2_r7" and _c1_stage1_match:
                    promote = False
                    _guarded = True
                else:
                    promote = True

            if _debug_on and _rule_id:
                _rule_fires.append({
                    "rule": _rule_id,
                    "src": str(cand.get("src") or ""),
                    "eff_rk": int(cand.get("eff_rk") or 0),
                    "promote": bool(promote),
                    "guarded": bool(_guarded),
                    "c1_src": str(c1.get("src") or ""),
                })

            if promote and cand_cp > best_challenger_score:
                best_challenger = cand
                best_challenger_score = cand_cp

        if best_challenger is not None:
            rem = [c for c in top5 if c is not best_challenger]
            top5 = [best_challenger] + rem

        # Sort Slots 2..5 to boost Hit@3 for high-consensus anchors
        if len(top5) > 2 and rule_mode != "raw_v13":
            slot1 = top5[0]
            rest_top5 = top5[1:]
            rest_top5.sort(
                key=lambda c: (
                    0
                    if (
                        _calibrated_prior_score(c) >= 145.0
                        and (
                            c["is_rec"]
                            or c["raw_sim"] >= 0.85
                            or c["n_fams"] >= 3
                            or (c["is_novel"] and c["cb"])
                        )
                    )
                    else 1,
                    c["eff_rk"],
                )
            )
            top5 = [slot1] + rest_top5

        if v13_rank_rules:
            from .ranking_rules_v13 import apply_v13_rank_rules

            top5, _rule_note = apply_v13_rank_rules(
                top5, enabled=True, target_slots=int(target_slots))

        if apply_stage1 and stage1_active and top5:
            # v1.3 T12-B：Stage-1 大类一致性精排（默认关；最后一步 ⇒ 不改
            # 既有校准结果，只在触发条件成立时把合规候选提到首位）。
            from .ranking_rules_v13 import apply_stage1_class_calibration

            _top5_pre = list(top5)
            _before = [str(c.get("src") or "") for c in _top5_pre]
            top5, _stage1_note = apply_stage1_class_calibration(
                top5, routing=stage1_routing, params=stage1_params,
                pool_rest=rest, target_slots=int(target_slots))
            if stage1_debug_sink is not None:
                stage1_debug_sink.update({
                    "routing": dict(stage1_routing or {}),
                    "stage1_params": dict(stage1_params or {}),
                    "substrate_smiles": str(substrate_smiles),
                    "stage1_note": dict(_stage1_note),
                    "top5_before": _before,
                    "top5_after": [str(c.get("src") or "") for c in top5],
                    # 规则前 top-5（按当时顺序）+ 池内其余可提交候选：离线
                    # 扫参用，与生产判据无关（只在 env 显式开启时落盘）。
                    "top5_candidates_before": [_debug_row(c) for c in _top5_pre],
                    "rest_candidates": [_debug_row(c) for c in rest],
                })

        _record_pass(
            top5_now=top5,
            head_pre_rules=_head_pre_rules,
            rule_fires=_rule_fires,
            top5_pre_rules=_top5_pre_rules)
        return top5, rest, rows

    if not consensus_engaged:
        if v13_multi_sample_consensus and \
                v13_consensus_debug_sink is not None:
            from .consensus_v13 import CONSENSUS_VERSION

            v13_consensus_debug_sink.update({
                "version": CONSENSUS_VERSION,
                "engaged": False,
                "pass_mode": effective_pass_mode,
                "skipped": ("no_secondary_passes"
                            if not consensus_lists else "disabled"),
            })
        top5, _rest, _rows = _single_pass(
            selected_top_keys, apply_stage1=True, pass_index=0)
        return [c["src"] for c in top5[: int(target_slots)]]

    # ---- T13-B：多 pass 融合（每个 pass 独立走单 pass 流水线；不叠加
    # Stage-1 精排 ⇒ 融合层的类加项/保护是唯一 Stage-1 消费面）----
    pass0_top5, _rest0, pass0_rows = _single_pass(
        selected_top_keys, apply_stage1=False,
        rule_mode=effective_pass_mode, pass_index=0)
    pass_top5_lists: list[list[dict[str, Any]]] = [pass0_top5]
    pass_key_debug: list[list[str]] = [
        [str(c.get("src") or "") for c in pass0_top5]]
    for _pi, keys in enumerate(consensus_lists, start=1):
        pass_top5, _rest_p, _rows_p = _single_pass(
            keys, apply_stage1=False, rule_mode=effective_pass_mode,
            pass_index=_pi,
            elig_keys=(consensus_elig_lists[_pi - 1]
                       if elig_norm_enabled else None))
        pass_top5_lists.append(pass_top5)
        pass_key_debug.append(
            [str(c.get("src") or "") for c in pass_top5])

    submittable_by_key: dict[str, dict[str, Any]] = {}
    for row in pass0_rows:
        src = str(row.get("src") or "")
        if src and src not in submittable_by_key:
            submittable_by_key[src] = row

    from .consensus_v13 import fuse_multi_sample_top5

    # v1.4 T14-4：跨池资格率归一化（主 pass 无资格信息 ⇒ None = 权重 1.0；
    # 次级 pass 按各自资格集归一化 + 资格感知全票锁）。参数只由
    # ``consensus_params_from_plan`` 按 plan 开关注入，此处不再隐式补参数。
    fuse_pass_elig: list[set[str] | None] | None = None
    if elig_norm_enabled:
        fuse_pass_elig = [None] + list(consensus_elig_lists)

    fused_rows, consensus_note = fuse_multi_sample_top5(
        pass_top5_lists, submittable_by_key, stage1_routing,
        v13_consensus_params, target_slots=int(target_slots),
        pass_eligible_keys=fuse_pass_elig)
    result_keys = [
        str(row.get("src") or "") for row in fused_rows
        if str(row.get("src") or "")]
    if not result_keys:
        # 兜底：融合空结果 ⇒ 原主 pass 顺序（保守，不引入新候选）。
        result_keys = [
            str(c.get("src") or "") for c in pass0_top5[: int(target_slots)]]
        consensus_note["skipped"] = (
            consensus_note.get("skipped") or "empty_fused_fallback_pass0")

    if v13_consensus_debug_sink is not None:
        v13_consensus_debug_sink.update({
            "version": str(consensus_note.get("version") or ""),
            "engaged": True,
            "stage1_routing": dict(stage1_routing or {}),
            "pass_mode": effective_pass_mode,
            "pass_top5_keys": pass_key_debug,
            "secondary_ranked_keys": [list(keys) for keys in consensus_lists],
            "note": consensus_note,
            "result_keys": list(result_keys),
        })
        if elig_norm_enabled:
            # v1.4 T14-4：只做研究期机读记录（键序稳定便于逐位比对）。
            v13_consensus_debug_sink.update({
                "cross_pool_elig_norm": True,
                "secondary_eligible_keys_list": [
                    (sorted(el) if el is not None else None)
                    for el in consensus_elig_lists],
            })

    return result_keys
