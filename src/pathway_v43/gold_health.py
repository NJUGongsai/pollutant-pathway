"""金标体检确定性规则(R1–R4)— HIT60 S1.5;v2 改版(mimo 评审采纳)。

判据沿革:

- **v1**(RULES_VERSION_V1,原默认):黑名单 R1(P/S/金属/核糖代理)+
  集合差 + R3 碳增一律 ``gold_conserv_violation`` + R4 单旗
  ``degenerate``。已全量跑 dev56/298 并经"程序→mimo→人审"生效
  (reports/phase_s15_hit60/gold_health_check/QUARANTINE_EFFECTIVE.md,
  dev 分母 56→51)。**v1 路径原样保留**:
  ``gold_health_labels_v1(...)`` 或 ``gold_health_labels(..., version="v1")``
  ——封存 v1 打标可用本仓同代码复算;v1 产物零覆写。
- **v2**(RULES_VERSION_V2,**新默认**):mimo 评审
  (docs/mimo_gold_rules_review_response.md 的 R1'/R2'/R3'/R4' 建议改写)
  + 采纳登记(docs/MIMO_REVIEWS_ADOPTION_REGISTER.md §1/§4.2)七项改版:

  1. **计数差替代集合差**:元素比较改逐元素计数(两侧全组分求和)——
     题面自带某元素时金标再挂载可见(断言 1);
  2. **去盐前置**:比较前剥离带电单原子金属/卤素 spectator 反离子
     (两侧都剥),另出 salt_form 表示法标记(评审漏网 #5);
  3. **parse_fail 转人审桶**:任一侧解析失败不做自动判定(不可解析按
     "未知"非"零"),整题入人审桶;补题面侧 parse-fail 计数字段
     (断言 3);
  4. **含 H 分子式 + ΔDoU**:比较改含总氢的元素计数(电荷归一后,
     P1 与 cn_identity 同口径),加不饱和度差观察列;|ΔDoU|≥2 且无
     合法 Δ 模式 → 观察列人审(断言 2,H 死代码修复);
  5. **R4 拆双轴旗**:degenerate_full(金标=题面) vs degenerate_mixed
     (金标混入题面身份)× raw canonical 相同(R4a≈构造自环) vs
     仅 cn 相同(R4b≈真实不可判),两轴分开输出(断言 5);
  6. **R1 白名单补集版**:存在 e∉{C,O,H} 使 Δe>0 →
     ``gold_cosubstrate_unreachable``(N 并入;RIBOSE 呋喃糖代理
     降级为观察标签列不再触发拦截——断言 4);
  7. **R3 缺口分子式表 + 归因分流**:ΔC=0 放行(列全即守恒);
     ΔC=−1 缺口∈{CO₂,CH₂O,CO,甲酰基}放行并标缺口;ΔC=−2 缺口∈
     {乙酰基/乙醛/乙酸(C2 碎片)};ΔC≤−3 人审桶;**+C 归因分流**:
     甲基化(ΔC=+1,ΔH=+2)/乙酰化(ΔC=+2,ΔO=+1)样式 →
     ``gold_unreachable_cosubstrate``(共底物缺失提案);羧化样式
     (ΔC=+1,ΔO=+2)单列人审桶;对不上任何碎片 →
     ``gold_conserv_violation``(数据错提案)。R2' 同步:来源指认改
     (ΔC,ΔO,ΔH) 模式打标(单加氧/双加氧/水合/还原/脱氢…,留痕不作
     门槛),归不上 → "未归类 O/H 当量"人审不拦。

实现注记(评审 R1' 元素宇宙的一处字面歧义):任务书/评审代码块字面
为 e∉{O,H};但评审 R3' 节明确"SAM 甲基化在题面无 S/N 时 **R1 看不见
(元素差为空)**,全靠这条(R3 分流)拦"——计数口径下若 C 入 R1 宇宙,
ΔC=+1 直接命中 R1,该句不成立(且 +C 全部归 R3' 分流)。故 v2 取
**e∉{C,O,H}**(C 归 R3',O/H 归 R2');备选字面口径只需改
``R1_UNIVERSE_EXEMPT`` 常量一处。

零 LLM;输出只有 qid/旗标/计数,不含 SMILES。v2 打标为**提案**,
走新冻结链(mimo 评审→人审→双人确认)采纳,不追溯作废已生效的
QUARANTINE_EFFECTIVE(2026-09-30)。
"""

from __future__ import annotations

from collections import Counter

from rdkit import Chem, RDLogger

RDLogger.DisableLog("rdApp.*")

# ---------------------------------------------------------------------------
# 版本与旗标常量
# ---------------------------------------------------------------------------

RULES_VERSION_V1 = "v43-gold-health-1 (判据待 mimo 评审冻结)"
RULES_VERSION_V2 = (
    "v43-gold-health-2 (mimo 评审采纳 v2 改版:计数差/去盐前置/parse_fail"
    " 人审/含H分子式+ΔDoU/R4双轴/R1白名单补集/R3缺口分子式表+归因分流;"
    "打标为提案,待新冻结链[人审+双人确认]采纳,不追溯作废 v1 生效登记)"
)
RULES_VERSION = RULES_VERSION_V2  # v2 为默认路径
RULE_VERSION_TAG = "v2"

#: R1 旗标(v1/v2 同名;v2 语义=白名单补集版)。
FLAG_R1 = "gold_cosubstrate_unreachable"
#: R3 旗标(v1/v2 同名;v2 语义收窄为"+C 对不上任何可指认碎片")。
FLAG_R3 = "gold_conserv_violation"
#: R4 单旗(v1)。
FLAG_R4 = "degenerate"
#: R3 归因分流新旗(v2):+C 恰构成可指认碎片(甲基化/乙酰化样式)→
#: 共底物缺失(题面不可答)提案。
FLAG_R3_UNREACHABLE = "gold_unreachable_cosubstrate"
#: R4 双旗(v2):金标(规范化集)= 题面集(真"无需反应")。
FLAG_R4_FULL = "degenerate_full"
#: R4 双旗(v2):金标混入题面身份(含未反应底物;含部分覆盖形态)。
FLAG_R4_MIXED = "degenerate_mixed"

# 人审桶原因(v2;观察列,不拦截、不入 quarantine 提案)
MR_PARSE_FAIL = "parse_fail"                  # 任一侧解析失败(不做自动判定)
MR_SURFACE_EMPTY = "surface_empty"            # 题面无可用组分(空/全盐)
MR_GOLD_EMPTY = "gold_empty"                  # 金标无可用组分(空/全盐)
MR_CARBOXYLATION = "carboxylation_style"      # +C 羧化样式(ΔC=+1,ΔO=+2)
MR_R3_GAP_GE3 = "r3_gap_leq_minus3"           # ΔC≤−3(未列全/多事件嫌疑)
MR_R3_GAP_UNLISTED = "r3_gap_unlisted"        # −1/−2 缺口对不上白名单
MR_DOU_ANOMALY = "dou_anomaly"                # |ΔDoU|≥2 且无合法 Δ 模式
MR_R2_UNCLASSIFIED = "unclassified_oh_equivalents"  # O/H 当量新增归不上类

# ---------------------------------------------------------------------------
# v1 常量(保留:gold_health_labels_v1 与既有夹具使用)
# ---------------------------------------------------------------------------

#: R1 默认不可供给的非金属元素(CoA/ATP/FAD/SAM 类共底物特征元素)。
R1_ELEMENTS = {"P", "S"}
#: R1 金属集合(生物学常见金属 + 常见污染金属;卤素/类金属不在内,
#: 属"unlisted"观察类,交评审)。
R1_METALS = {
    "Li", "Be", "Na", "Mg", "Al", "K", "Ca", "Sc", "Ti", "V", "Cr", "Mn",
    "Fe", "Co", "Ni", "Cu", "Zn", "Ga", "Rb", "Sr", "Y", "Zr", "Nb", "Mo",
    "Tc", "Ru", "Rh", "Pd", "Ag", "Cd", "In", "Sn", "Cs", "Ba", "La", "Ce",
    "Pr", "Nd", "Sm", "Eu", "Gd", "Tb", "Dy", "Ho", "Er", "Tm", "Yb", "Lu",
    "Hf", "Ta", "W", "Re", "Os", "Ir", "Pt", "Au", "Hg", "Tl", "Pb", "Bi",
}
#: R2 可默认供给元素白名单(O₂/H₂O)。
R2_WHITELIST = {"O", "H"}
#: 核糖/核苷酸骨架代理判据:立体盲呋喃核糖骨架 SMARTS(与 cn 立体盲
#: 口径一致;含 CH2OH + 2×OH 的呋喃糖,葡萄糖呋喃型亦可匹配——
#: 代理判据,v2 降级为观察标签列,不再触发拦截)。
RIBOSE_SMARTS = "C1OC(CO)C(O)C1O"

# ---------------------------------------------------------------------------
# v2 常量
# ---------------------------------------------------------------------------

#: 卤素集合(spectator 反离子剥离 + DoU 计算按 H 计)。
HALOGENS = {"F", "Cl", "Br", "I", "At"}
#: spectator 反离子元素:带电单原子金属/卤素(成盐表示法,非化学)。
SPECTATOR_ELEMENTS = R1_METALS | HALOGENS
#: R1' 元素宇宙豁免(白名单补集的补):C 归 R3' 碳守恒分流、O/H 归
#: R2' 可默认供给(O₂/H₂O/NAD(P)H)。字面歧义见模块 docstring。
R1_UNIVERSE_EXEMPT = {"C", "O", "H"}

#: R2' (ΔC, ΔO, ΔH) 模式表(来源指认留痕,不作门槛;ΔDoU 影响≤1)。
R2_PATTERNS: list[tuple[tuple[int, int, int], str]] = [
    ((0, 1, 0), "monooxygenation"),    # 单加氧/环氧化(O₂ 单加氧酶)
    ((0, 2, 0), "dioxygenation"),      # 双加氧顺二醇(O₂ 双加氧酶)
    ((0, 1, 2), "hydration"),          # 水合(+H₂O)
    ((0, 2, 2), "dihydroxylation"),    # 双羟化
    ((0, 0, 2), "reduction"),          # 还原(+2H,源 NAD(P)H)
    ((0, 0, -2), "dehydrogenation"),   # 脱氢(−2H)
    ((0, -1, -2), "dehydration"),      # 脱水(−H₂O)
]

#: ΔC=−1 放行缺口分子式(C/H/O 键格式,其他元素必须零)。
C1_GAPS = {
    "C1H0O2": "CO2",
    "C1H2O1": "CH2O",
    "C1H0O1": "CO",
    "C1H1O1": "formyl",
}
#: ΔC=−2 放行缺口分子式(C2 碎片:乙酰-CoA 单元类)。
C2_GAPS = {
    "C2H3O1": "acetyl",
    "C2H4O1": "acetaldehyde",
    "C2H4O2": "acetic",
}


# ---------------------------------------------------------------------------
# 基础解析(v1/v2 共用,行为不变)
# ---------------------------------------------------------------------------


def _mol(smiles: str):
    return Chem.MolFromSmiles(smiles) if smiles else None


def component_smiles_list(smiles: str) -> list[str]:
    """SMILES 按 '.' 拆分(空串/None → 空列表)。"""
    if not smiles:
        return []
    return [part for part in smiles.split(".") if part]


def elements_of(smiles: str) -> set[str]:
    """整条 SMILES(全部组分)元素集合;不可解析 → 空集合。

    (v1 口径:隐式 H 不入集合;v2 含 H 分子式见 _formula_counts。)
    """
    m = _mol(smiles)
    if m is None:
        return set()
    return {a.GetSymbol() for a in m.GetAtoms()}


def carbons_of(smiles: str) -> int:
    """整条 SMILES(全部组分)碳原子总数;不可解析 → 0。"""
    m = _mol(smiles)
    if m is None:
        return 0
    return sum(1 for a in m.GetAtoms() if a.GetSymbol() == "C")


def has_ribose_backbone(smiles: str) -> bool:
    """含呋喃核糖骨架(代理 SMARTS,立体盲);不可解析 → False。

    v2 降级为观察标签列(葡萄糖呋喃/吡喃书写差异误拦风险,评审断言 4)。
    """
    m = _mol(smiles)
    if m is None:
        return False
    patt = Chem.MolFromSmarts(RIBOSE_SMARTS)
    return bool(m.HasSubstructMatch(patt))


def _cn(smiles: str) -> str | None:
    from .domain.identity import cn_identity
    return cn_identity(smiles)


# ---------------------------------------------------------------------------
# v1 规则路径(原样保留——封存 v1 打标可用同仓代码复算)
# ---------------------------------------------------------------------------


def gold_health_labels_v1(*, substrate_smiles: str,
                          products_smiles: list[str]) -> dict:
    """v1 单题体检(逻辑与生效封存轮完全一致,零改动保留)。

    输出 schema 同封存轮:flags/new_elements/unlisted_new_elements/
    r2_retained/substrate_c/gold_c/n_products/n_parse_fail_products/
    r1/r3/r4。注:v1 判据已知六处实现缺陷(集合差/H 死代码/parse_fail
    按零/RIBOSE 误匹配/R4 交集单旗/碳增归因不分流),mimo 评审断言
    6/6 成立——见 docs/MIMO_REVIEWS_ADOPTION_REGISTER.md §1.2;
    v2 修复见 ``gold_health_labels``。
    """
    surface_parts = component_smiles_list(substrate_smiles)
    surface_elements: set[str] = set()
    for part in surface_parts:
        surface_elements |= elements_of(part)
    surface_c = sum(carbons_of(part) for part in surface_parts)
    surface_ids = {_cn(part) for part in surface_parts}
    surface_ids.discard(None)

    gold_elements: set[str] = set()
    gold_c = 0
    gold_ids: set[str] = set()
    gold_ribose = False
    parse_fail = 0
    for product in products_smiles:
        parts = component_smiles_list(product)
        if not parts or all(_mol(part) is None for part in parts):
            parse_fail += 1
        for part in parts:
            gold_elements |= elements_of(part)
            gold_c += carbons_of(part)
            ident = _cn(part)
            if ident:
                gold_ids.add(ident)
            if has_ribose_backbone(part):
                gold_ribose = True

    new_elements = gold_elements - surface_elements
    substrate_ribose = any(has_ribose_backbone(p) for p in surface_parts)

    flags: list[str] = []
    r1_hit = sorted(
        (new_elements & (R1_ELEMENTS | R1_METALS))
        | ({"RIBOSE"} if (gold_ribose and not substrate_ribose) else set()))
    if r1_hit:
        flags.append(FLAG_R1)
    if gold_c > surface_c and surface_c > 0:
        flags.append(FLAG_R3)
    if gold_ids & surface_ids:
        flags.append(FLAG_R4)

    unlisted = new_elements - R1_ELEMENTS - R1_METALS - R2_WHITELIST
    return {
        "flags": flags,
        "r1_hit_elements": r1_hit,
        "new_elements": sorted(new_elements),
        "unlisted_new_elements": sorted(unlisted),
        "r2_retained": bool(new_elements) and new_elements <= R2_WHITELIST,
        "substrate_c": surface_c,
        "gold_c": gold_c,
        "n_products": len(products_smiles),
        "n_parse_fail_products": parse_fail,
        "r4": FLAG_R4 in flags,
        "r3": FLAG_R3 in flags,
        "r1": FLAG_R1 in flags,
    }


# ---------------------------------------------------------------------------
# v2 规则路径(新默认)
# ---------------------------------------------------------------------------


def _is_spectator_ion(mol) -> bool:
    """带电单原子金属/卤素 spectator 反离子(盐表示法)。"""
    if mol.GetNumAtoms() != 1:
        return False
    atom = mol.GetAtomWithIdx(0)
    return atom.GetFormalCharge() != 0 and atom.GetSymbol() in SPECTATOR_ELEMENTS


def _formula_counts(mol) -> Counter:
    """元素计数(含总 H):重原子上的隐式 H + 括号显式 H + 显式 H 原子。

    H 死代码修复(评审断言 2):v1 ``elements_of`` 走原子符号,隐式氢
    不可见;本函数按 RDKit ``GetTotalNumHs()`` 补隐式/括号显式氢,
    显式写的 [H] 原子逐个数。
    """
    counts: Counter = Counter()
    for atom in mol.GetAtoms():
        sym = atom.GetSymbol()
        if sym == "H":
            counts["H"] += 1
        else:
            counts[sym] += 1
            counts["H"] += atom.GetTotalNumHs()
    return counts


def _dou(counts: Counter) -> float:
    """单组分不饱和度 DoU=(2C+2+N−H−X)/2(卤素按 H 计;仅含碳组分,
    无碳组分(O₂/H₂O/NH₃…)记 0)。纯算术,零 LLM。"""
    if counts.get("C", 0) == 0:
        return 0.0
    x = sum(counts.get(e, 0) for e in HALOGENS)
    return (2 * counts["C"] + 2 + counts.get("N", 0)
            - counts.get("H", 0) - x) / 2.0


def _charge_normalized_mol(part: str, mol):
    """P1 电荷归一(与 cn_identity 同口径的 Uncharger),失败回退原始。"""
    from .domain.identity import normalize_charge_smiles
    norm = normalize_charge_smiles(part)
    if norm:
        m = _mol(norm)
        if m is not None:
            return m
    return mol


def _analyze_side(parts: list[str]) -> dict:
    """单侧(题面/金标)规范化分析:去盐 → 电荷归一 → 含 H 分子式计数
    + DoU + raw canonical/cn 身份对 + RIBOSE 观察盐检查。

    不可解析 part 按"未知"计(只进 n_parse_fail,不贡献计数;
    上层据此转人审桶,不做自动判定)。spectator 反离子剥离后计入
    salt_ions,不进分子式。
    """
    formula: Counter = Counter()
    dou_total = 0.0
    pairs: list[tuple[str, str | None]] = []
    salt_ions: Counter = Counter()
    n_parse_fail = 0
    ribose = False
    for part in parts:
        mol = _mol(part)
        if mol is None:
            n_parse_fail += 1
            continue
        if _is_spectator_ion(mol):
            salt_ions[mol.GetAtomWithIdx(0).GetSymbol()] += 1
            continue
        # R4 轴:raw canonical(规范化前,保留立体与电荷)与 cn 身份
        pairs.append((Chem.MolToSmiles(mol), _cn(part)))
        if has_ribose_backbone(part):
            ribose = True
        norm = _charge_normalized_mol(part, mol)
        counts = _formula_counts(norm)
        formula += counts
        dou_total += _dou(counts)
    return {
        "formula": formula,
        "dou": dou_total,
        "pairs": pairs,
        "salt_ions": salt_ions,
        "n_parse_fail": n_parse_fail,
        "n_components": len(pairs),
        "ribose": ribose,
    }


def _gap_key(gap: Counter) -> str | None:
    """缺口分子式键(仅 C/H/O;缺口含其他元素 → None=对不上白名单)。"""
    if any(v for e, v in gap.items() if e not in ("C", "H", "O")):
        return None
    return (f"C{gap.get('C', 0)}H{gap.get('H', 0)}"
            f"O{gap.get('O', 0)}")


def _plus_c_attribution(delta: dict[str, int]) -> str:
    """+C 归因分流(ΔC>0 时;确定性,模式级不含结构判定)。

    - 甲基化样式(ΔC=+1,ΔH=+2,ΔO=0,其余元素 Δ=0)→ FLAG_R3_UNREACHABLE
      (SAM 类 C1 供体缺失,题面不可答提案;评审:排在归因第一位,
      别当数据错);
    - 乙酰化/缩合样式(ΔC=+2,ΔO=+1,其余非 C/O/H 元素 Δ=0)→
      FLAG_R3_UNREACHABLE(乙酰-CoA 类 C2 供体缺失);
    - 羧化样式(ΔC=+1,ΔO=+2,其余非 C/O/H 元素 Δ=0)→ MR_CARBOXYLATION
      单列人审桶(CO₂/HCO₃⁻ 环境默认碳源,最可能是被出题者接受的
      环境羧化,不硬判);
    - 对不上任何可指认碎片 → FLAG_R3(gold_conserv_violation,数据错)。
    """
    others_zero = all(
        v == 0 for e, v in delta.items() if e not in ("C", "O", "H"))
    if (delta.get("C", 0) == 1 and delta.get("H", 0) == 2
            and delta.get("O", 0) == 0
            and all(v == 0 for e, v in delta.items() if e not in ("C", "H"))):
        return "methylation"
    if delta.get("C", 0) == 2 and delta.get("O", 0) == 1 and others_zero:
        return "acetylation"
    if delta.get("C", 0) == 1 and delta.get("O", 0) == 2 and others_zero:
        return "carboxylation"
    return "unattributed"


def _gold_health_labels_v2(*, substrate_smiles: str,
                           products_smiles: list[str]) -> dict:
    products = products_smiles or []
    surface_parts = component_smiles_list(substrate_smiles or "")
    # 金标全部条目展平成 part 列表;空条目记为不可解析(未知,非零)
    gold_parts: list[str] = []
    for product in products:
        entry_parts = component_smiles_list(product)
        if not entry_parts:
            gold_parts.append("")
            continue
        gold_parts.extend(entry_parts)

    surface = _analyze_side(surface_parts)
    gold = _analyze_side(gold_parts)

    # ---- P3 parse_fail / 侧可用性 → 不做自动判定 ----
    parse_fail = surface["n_parse_fail"] > 0 or gold["n_parse_fail"] > 0
    manual_review: list[str] = []
    no_auto = False
    if parse_fail:
        manual_review.append(MR_PARSE_FAIL)
        no_auto = True
    if surface["n_components"] == 0 and surface["n_parse_fail"] == 0:
        manual_review.append(MR_SURFACE_EMPTY)
        no_auto = True
    if gold["n_components"] == 0 and gold["n_parse_fail"] == 0:
        manual_review.append(MR_GOLD_EMPTY)
        no_auto = True

    # ---- 计数差(含总 H,去盐+电荷归一后) ----
    all_elements = set(surface["formula"]) | set(gold["formula"])
    delta = {e: gold["formula"].get(e, 0) - surface["formula"].get(e, 0)
             for e in all_elements}
    delta = {e: v for e, v in delta.items() if v != 0}
    delta_c = delta.get("C", 0)
    delta_o = delta.get("O", 0)
    delta_h = delta.get("H", 0)
    delta_dou = round(gold["dou"] - surface["dou"], 1)

    new_elements = sorted(e for e, v in delta.items() if v > 0)
    r1_hit = sorted(
        e for e, v in delta.items()
        if v > 0 and e not in R1_UNIVERSE_EXEMPT)

    # ---- R2' 模式打标(留痕不作门槛) ----
    r2_pattern = ""
    for (dc, do, dh), name in R2_PATTERNS:
        if (delta_c, delta_o, delta_h) == (dc, do, dh):
            r2_pattern = name
            break

    # ---- R3 缺口分子式 / +C 归因(计数照算;不做自动判定时不进人审桶) ----
    r3_gap = ""
    r3_attribution = ""
    if delta_c < 0:
        gap = Counter({e: -v for e, v in delta.items() if v < 0})
        if delta_c <= -3:
            r3_bucket = MR_R3_GAP_GE3
        else:
            key = _gap_key(gap)
            table = C1_GAPS if delta_c == -1 else C2_GAPS
            if key is not None and key in table:
                r3_bucket = ""
                r3_gap = table[key]
            else:
                r3_bucket = MR_R3_GAP_UNLISTED
        if r3_bucket and not no_auto:
            manual_review.append(r3_bucket)
    elif delta_c > 0:
        r3_attribution = _plus_c_attribution(delta)

    # ---- 观察列(仅 ΔC=0 时有意义:碳在动时碳侧已分流;
    # 不做自动判定时不进人审桶,parse_fail 已整题入桶) ----
    if delta_c == 0 and not no_auto:
        if (delta_o > 0 or delta_h > 0) and not r2_pattern:
            manual_review.append(MR_R2_UNCLASSIFIED)
        if abs(delta_dou) >= 2 and not r2_pattern:
            manual_review.append(MR_DOU_ANOMALY)

    # ---- R4 双轴 ----
    surface_ids = {cn for _, cn in surface["pairs"] if cn}
    gold_ids = {cn for _, cn in gold["pairs"] if cn}
    r4_full = False
    r4_mixed = False
    r4_axis: list[str] = []
    r4_mixed_kind = ""
    overlap = surface_ids & gold_ids
    if overlap:
        if surface_ids == gold_ids:
            r4_full = True
        else:
            # 评审口径:金标⊋题面(混入未反应底物);部分覆盖形态
            # (金标含部分题面身份但未全覆盖)同入 mixed 旗并单列
            # kind,避免 v1 交集语义覆盖面回退。
            r4_mixed = True
            r4_mixed_kind = ("superset" if surface_ids < gold_ids
                             else "partial_overlap")
        surface_raw_by_cn = {cn: raw for raw, cn in surface["pairs"] if cn}
        gold_raw_by_cn: dict[str, set[str]] = {}
        for raw, cn in gold["pairs"]:
            if cn:
                gold_raw_by_cn.setdefault(cn, set()).add(raw)
        axes: set[str] = set()
        for cn in overlap:
            if surface_raw_by_cn.get(cn) in gold_raw_by_cn.get(cn, set()):
                axes.add("raw")   # R4a:raw canonical 也相同≈构造自环
            else:
                axes.add("cn")    # R4b:仅 cn 相同≈真实不可判(立体/电荷抹平)
        r4_axis = sorted(axes)

    # ---- 旗标(不做自动判定时全部抑制) ----
    flags: list[str] = []
    if not no_auto:
        if r1_hit:
            flags.append(FLAG_R1)
        if r3_attribution == "methylation" or r3_attribution == "acetylation":
            flags.append(FLAG_R3_UNREACHABLE)
        elif r3_attribution == "carboxylation":
            manual_review.append(MR_CARBOXYLATION)
        elif r3_attribution == "unattributed":
            flags.append(FLAG_R3)
        if r4_full:
            flags.append(FLAG_R4_FULL)
        if r4_mixed:
            flags.append(FLAG_R4_MIXED)

    salt_form_surface = bool(surface["salt_ions"])
    salt_form_gold = bool(gold["salt_ions"])
    salt_ions = sorted(set(surface["salt_ions"]) | set(gold["salt_ions"]))
    ribose_observed = bool(gold["ribose"] and not surface["ribose"])

    return {
        "rule_version": RULE_VERSION_TAG,
        "flags": flags,
        "manual_review": sorted(set(manual_review)),
        "r1_hit_elements": r1_hit,
        "new_elements": new_elements,
        "delta_elements": delta,
        "delta_c": delta_c,
        "delta_o": delta_o,
        "delta_h": delta_h,
        "delta_dou": delta_dou,
        "r2_retained": bool(new_elements) and set(new_elements) <= R2_WHITELIST,
        "r2_pattern": r2_pattern,
        "r3_gap": r3_gap,
        "r3_attribution": (r3_attribution if not no_auto and delta_c > 0
                           else ""),
        "salt_form": salt_form_surface or salt_form_gold,
        "salt_form_surface": salt_form_surface,
        "salt_form_gold": salt_form_gold,
        "salt_ions": salt_ions,
        "parse_fail": parse_fail,
        "n_parse_fail_surface_parts": surface["n_parse_fail"],
        "n_parse_fail_product_parts": gold["n_parse_fail"],
        "substrate_c": surface["formula"].get("C", 0),
        "gold_c": gold["formula"].get("C", 0),
        "n_products": len(products),
        "ribose_observed": ribose_observed,
        "r4_full": FLAG_R4_FULL in flags,
        "r4_mixed": FLAG_R4_MIXED in flags,
        "r4_axis": r4_axis,
        "r4_mixed_kind": r4_mixed_kind,
        "r1": FLAG_R1 in flags,
        "r3": FLAG_R3 in flags or FLAG_R3_UNREACHABLE in flags,
        "r4": FLAG_R4_FULL in flags or FLAG_R4_MIXED in flags,
    }


def gold_health_labels(*, substrate_smiles: str,
                       products_smiles: list[str],
                       version: str = "v2") -> dict:
    """单题体检(**v2 默认**;``version="v1"`` 走保留的 v1 路径)。

    v2 输出要点(详见模块 docstring):

    - ``flags``:硬旗标(quarantine 提案候选)——R1'
      ``gold_cosubstrate_unreachable``;R3' 归因分流
      ``gold_unreachable_cosubstrate``/``gold_conserv_violation``;
      R4' 双旗 ``degenerate_full``/``degenerate_mixed``;
    - ``manual_review``:人审桶原因(不拦截);
    - ``delta_elements``/``delta_c``/``delta_o``/``delta_h``:逐元素
      计数差(金标−题面;去盐+电荷归一后,含总氢);
    - ``delta_dou``:不饱和度差;``r2_pattern``:R2' 模式标签;
    - ``r3_gap``:缺口分子式标签;``r3_attribution``:+C 归因;
    - salt/parse/ribose 观察字段;``r1``/``r3``/``r4`` 规则级布尔
      (v1 对比口径)。

    任一侧解析失败或无可用组分 → 不做自动判定:``flags`` 为空、
    整题入人审桶,计数照落表(不可解析按"未知"非"零")。
    """
    if version == "v1":
        return gold_health_labels_v1(
            substrate_smiles=substrate_smiles,
            products_smiles=products_smiles)
    if version != "v2":
        raise ValueError(f"unknown rules version: {version!r}")
    return _gold_health_labels_v2(
        substrate_smiles=substrate_smiles,
        products_smiles=products_smiles)
