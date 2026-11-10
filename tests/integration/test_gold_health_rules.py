"""金标体检确定性规则(R1–R4)合成夹具 — 钉 v1(封存复算)与 v2(改版)判据。

任务书:docs/TASK_V43_HIT60_S15_DETERMINISTIC_FIX.md §D;v2 改版规格:
docs/MIMO_REVIEWS_ADOPTION_REGISTER.md §4.2 + docs/mimo_gold_rules_review_response.md
(R1'/R2'/R3'/R4' 建议改写)。全部合成样例,**零真实金标**。

两段结构:

- **v1 段**:调 ``gold_health_labels_v1``(原样保留的 v1 路径)——钉封存轮
  判据不变,确保已生效 5 题的 v1 证据链可用同仓代码复算;
- **v2 段**:调 ``gold_health_labels``(v2 新默认)——逐项钉七条改版:
  计数差可见/去盐前置/parse_fail 人审/含 H 分子式+ΔDoU/R4 双轴/
  R1 白名单补集/R3 缺口分子式表+归因分流/RIBOSE 降级;多处同时断言
  v1 行为作 A/B 对照(钉"v1 盲区→v2 可见"的修复方向)。
"""

from __future__ import annotations

import pytest

from pathway_v43.gold_health import (
    FLAG_R1,
    FLAG_R3,
    FLAG_R3_UNREACHABLE,
    FLAG_R4,
    FLAG_R4_FULL,
    FLAG_R4_MIXED,
    RULE_VERSION_TAG,
    gold_health_labels,
    gold_health_labels_v1,
)

# 乙酰辅酶 A 硫酯的极简合成替身(含 S、P 的 CoA 骨架样分子;
# 不用真实 CoA SMILES,规则测试只需要元素构成):
SYNTH_COA_LIKE = "CC(=O)SCCOP(=O)(O)O"          # 含 S、P
SYNTH_PHOSPHO = "CCOP(=O)(O)O"                  # 含 P
# 葡萄糖吡喃/呋喃书写差异(同分子 C6H12O6,环型不同;非立体写法):
GLUCO_PYRANOSE = "OCC1OC(O)C(O)C(O)C1O"         # 6 元环,不匹配核糖代理
GLUCO_FURANOSE = "OCC(O)C1OC(O)C(O)C1O"         # 5 元环,匹配核糖代理


# ===========================================================================
# v1 段(封存轮判据复算——gold_health_labels_v1 原样保留)
# ===========================================================================


def test_r3_carbon_conservation_pass():
    """v1 碳守恒通过:金标碳数 ≤ 题面(减少/相等均合法)。"""
    # 相等:乙醇氧化成乙醛(C2 → C2)
    labels = gold_health_labels_v1(substrate_smiles="CCO",
                                   products_smiles=["CC=O"])
    assert labels["flags"] == []
    # 裂解减少:己烷裂成两半(C6 → C3+C3,总和 = 题面)
    labels = gold_health_labels_v1(substrate_smiles="CCCCCC",
                                   products_smiles=["CCC", "CCC"])
    assert labels["flags"] == []
    # 脱羧 −1(C3 → C2 + CO2 计入金标亦守恒)
    labels = gold_health_labels_v1(substrate_smiles="CCC(=O)O",
                                   products_smiles=["CC", "O=C=O"])
    assert FLAG_R3 not in labels["flags"]


def test_r3_carbon_plus_one_violation():
    """v1 碳数 +1:金标碳数 > 题面且无共底物 → gold_conserv_violation。"""
    labels = gold_health_labels_v1(substrate_smiles="CCO",   # 2C
                                   products_smiles=["CCCO"])  # 3C
    assert labels["flags"] == [FLAG_R3]
    assert labels["gold_c"] == 3 and labels["substrate_c"] == 2
    # 多条目总和超题面同样命中
    labels = gold_health_labels_v1(substrate_smiles="CCC",    # 3C
                                   products_smiles=["CC", "CCC"])  # 2+3=5C
    assert FLAG_R3 in labels["flags"]


def test_r4_degenerate():
    """v1 退化:金标产物条目 cn 身份 = 题面 cn 身份(单旗)。"""
    labels = gold_health_labels_v1(substrate_smiles="CCO",
                                   products_smiles=["CCO"])
    assert labels["flags"] == [FLAG_R4]
    # 立体/电荷书写差异同 cn → 仍退化
    labels = gold_health_labels_v1(substrate_smiles="C[NH3+]",
                                   products_smiles=["CN"])
    assert labels["flags"] == [FLAG_R4]
    # 多产物中混一条与题面相同 → 退化(该样例碳数总和同时超题面,
    # R3 并发是规则独立性,断言用 in)
    labels = gold_health_labels_v1(substrate_smiles="CCO",
                                   products_smiles=["CC=O", "CCO"])
    assert FLAG_R4 in labels["flags"]


def test_r1_new_elements_unreachable():
    """v1 R1:金标引入题面没有的 P/S(无共底物)→ 不可达。"""
    labels = gold_health_labels_v1(substrate_smiles="CC(=O)O",   # C,H,O
                                   products_smiles=[SYNTH_COA_LIKE])
    assert FLAG_R1 in labels["flags"]
    assert "P" in labels["r1_hit_elements"]
    assert "S" in labels["r1_hit_elements"]
    # 单 P(磷酸化,碳数相等 → 仅 R1)
    labels = gold_health_labels_v1(substrate_smiles="CCO",
                                   products_smiles=[SYNTH_PHOSPHO])
    assert labels["flags"] == [FLAG_R1]
    assert labels["r1_hit_elements"] == ["P"]
    # 单 S(硫酸酯,碳数相等 → 仅 R1)
    labels = gold_health_labels_v1(substrate_smiles="CCO",
                                   products_smiles=["CCOS(=O)(=O)O"])
    assert labels["flags"] == [FLAG_R1]
    assert labels["r1_hit_elements"] == ["S"]


def test_r1_coa_exception_cosubstrate_in_surface():
    """v1 CoA 例外:题面本身含共底物(多组分底物)→ P/S 不算新元素。"""
    labels = gold_health_labels_v1(
        substrate_smiles=f"CC(=O)O.{SYNTH_COA_LIKE}",   # 底物 + 游离 CoA
        products_smiles=[SYNTH_COA_LIKE.replace("CC(=O)S", "CCS", 1)])
    assert labels["flags"] == []
    assert labels["new_elements"] == []
    # 碳数侧同理:共底物碳并入题面碳数
    labels = gold_health_labels_v1(
        substrate_smiles=f"CC(=O)O.{SYNTH_COA_LIKE}",
        products_smiles=["CC(=O)O", "CCSCCOP(=O)(O)O"])
    assert FLAG_R1 not in labels["flags"]
    assert FLAG_R3 not in labels["flags"]


def test_r2_new_elements_only_oh_retained():
    """v1 R2:新增元素仅 {O,H} → 保留不打标(注:v1 隐式 H 永不新增)。"""
    labels = gold_health_labels_v1(substrate_smiles="CC",       # C,H
                                   products_smiles=["CCO"])     # +O
    assert labels["flags"] == []
    assert labels["r2_retained"] is True
    # 水合(丙烯 + H2O → 异丙醇,碳数守恒)
    labels = gold_health_labels_v1(substrate_smiles="C=CC",
                                   products_smiles=["CC(O)C"])
    assert labels["flags"] == []
    assert labels["r2_retained"] is True


def test_unlisted_new_elements_observed_not_flagged():
    """v1 N 等非白名单元素:不打标、进观察列(v2 已改为拦截,N 并入)。"""
    labels = gold_health_labels_v1(substrate_smiles="CCO",
                                   products_smiles=["CCN"])
    assert labels["flags"] == []
    assert labels["unlisted_new_elements"] == ["N"]
    assert labels["r2_retained"] is False


def test_elements_of_and_multi_component_surface():
    # RDKit 隐式氢不入原子集合(v1 口径;v2 含 H 分子式另算)
    from pathway_v43.gold_health import elements_of
    assert elements_of("CCO") == {"C", "O"}
    assert elements_of("CCO.CC(=O)O") == {"C", "O"}
    assert elements_of("junk") == set()


def test_rules_do_not_flag_clean_question():
    """v1 干净题:苯 → 苯酚(新增 O,R2 保留),碳数守恒,无旗标。"""
    labels = gold_health_labels_v1(substrate_smiles="c1ccccc1",
                                   products_smiles=["C1=CC=CC=C1O"])
    assert labels["flags"] == []
    assert labels["new_elements"] == ["O"]
    assert labels["r2_retained"] is True


def test_v1_schema_keys_preserved():
    """v1 输出 schema 与封存轮一致(复算证据链的键集钉死)。"""
    labels = gold_health_labels_v1(substrate_smiles="CCO",
                                   products_smiles=["CC=O"])
    assert set(labels) == {
        "flags", "r1_hit_elements", "new_elements",
        "unlisted_new_elements", "r2_retained", "substrate_c",
        "gold_c", "n_products", "n_parse_fail_products",
        "r4", "r3", "r1",
    }


# ===========================================================================
# v2 段(七项改版逐项钉;多处带 v1 A/B 对照)
# ===========================================================================


def test_v2_counting_diff_second_s_visible():
    """改版 1 计数差:题面自带 S、金标再挂一个 S(ΔS=+1)。

    v1 集合差:元素集不变 → 全盲(评审断言 1 复现);v2 计数差:R1 命中 S。
    """
    v2 = gold_health_labels(substrate_smiles="CSCC",      # C3H8S(1×S)
                            products_smiles=["CSCSC"])    # C3H8S2(2×S)
    v1 = gold_health_labels_v1(substrate_smiles="CSCC",
                               products_smiles=["CSCSC"])
    assert v1["flags"] == []                       # v1 盲区(钉方向)
    assert v2["flags"] == [FLAG_R1]
    assert v2["r1_hit_elements"] == ["S"]
    assert v2["delta_elements"] == {"S": 1}


def test_v2_h_deadcode_fixed_dou_flag():
    """改版 4 含 H 分子式 + ΔDoU:苯 → 环己烷(+6H,ΔDoU=−3)。

    v1 隐式 H 不可见 → 四条全放(评审断言 2 复现);v2 出
    ΔDoU 观察旗(|ΔDoU|≥2 且无合法 Δ 模式 → 人审桶,不拦截)。
    """
    v2 = gold_health_labels(substrate_smiles="c1ccccc1",    # C6H6, DoU=4
                            products_smiles=["C1CCCCC1"])   # C6H12, DoU=1
    v1 = gold_health_labels_v1(substrate_smiles="c1ccccc1",
                               products_smiles=["C1CCCCC1"])
    assert v1["flags"] == []                       # H 死代码(钉方向)
    assert v2["flags"] == []                       # 观察列,不是硬旗标
    assert "dou_anomaly" in v2["manual_review"]
    assert "unclassified_oh_equivalents" in v2["manual_review"]
    assert v2["delta_elements"] == {"H": 6}
    assert v2["delta_h"] == 6
    assert v2["delta_dou"] == -3.0


def test_v2_salt_stripping_no_false_r1():
    """改版 2 去盐前置:钠盐登记不误报 R1,salt_form 标记落表。"""
    # 金标登记成钠盐(表示法),题面游离酸:
    v2 = gold_health_labels(substrate_smiles="CCC(=O)O",
                            products_smiles=["CCC(=O)[O-].[Na+]"])
    v1 = gold_health_labels_v1(substrate_smiles="CCC(=O)O",
                               products_smiles=["CCC(=O)[O-].[Na+]"])
    assert FLAG_R1 in v1["flags"] and "Na" in v1["r1_hit_elements"]  # v1 误报
    assert FLAG_R1 not in v2["flags"]              # Na 剥离后不算新增元素
    assert v2["salt_form"] is True
    assert v2["salt_form_gold"] is True and v2["salt_form_surface"] is False
    assert v2["salt_ions"] == ["Na"]
    assert v2["delta_elements"] == {}
    # 题面侧同样剥(盐写在题面;去盐后与金标同分子 → 退化旗,与 R1 无关):
    v2 = gold_health_labels(substrate_smiles="CC(=O)[O-].[Na+]",
                            products_smiles=["CC(=O)O"])
    assert v2["salt_form_surface"] is True
    assert v2["delta_elements"] == {}
    assert v2["flags"] == [FLAG_R4_FULL]           # 同分子仅退化旗,无 R1
    # 卤盐(盐酸甲铵)同理,Cl- 剥离:
    v2 = gold_health_labels(substrate_smiles="CN",
                            products_smiles=["C[NH3+].[Cl-]"])
    assert v2["salt_ions"] == ["Cl"]
    assert v2["delta_elements"] == {}
    assert FLAG_R1 not in v2["flags"]


def test_v2_parse_fail_manual_review_bucket():
    """改版 3 parse_fail 转人审桶:不可解析按"未知"非"零"。"""
    # junk 金标条目 → 人审桶非假通过(v1:碳贡献 0 → 无旗标"假通过")
    v2 = gold_health_labels(substrate_smiles="CCO",
                            products_smiles=["junk"])
    v1 = gold_health_labels_v1(substrate_smiles="CCO",
                               products_smiles=["junk"])
    assert v1["flags"] == []                       # v1 假通过(钉方向)
    assert v2["flags"] == []                       # 不做自动判定
    assert v2["parse_fail"] is True
    assert v2["n_parse_fail_product_parts"] == 1
    assert v2["manual_review"] == ["parse_fail"]   # 整题人审,单一原因
    # junk 题面 → 人审桶非全面误报(v1:元素并集为空 → P 全"新增"误报 R1)
    v2 = gold_health_labels(substrate_smiles="junk",
                            products_smiles=[SYNTH_PHOSPHO])
    v1 = gold_health_labels_v1(substrate_smiles="junk",
                               products_smiles=[SYNTH_PHOSPHO])
    assert FLAG_R1 in v1["flags"]                  # v1 全面误报(钉方向)
    assert v2["flags"] == []
    assert v2["n_parse_fail_surface_parts"] == 1
    assert v2["manual_review"] == ["parse_fail"]


def test_v2_r4_double_axis_four_combinations():
    """改版 5 R4 双轴:full/mixed × raw/cn 四组合分开输出。"""
    # full + raw(原始 canonical 相同≈构造自环,R4a):
    v2 = gold_health_labels(substrate_smiles="CCO",
                            products_smiles=["CCO"])
    assert v2["flags"] == [FLAG_R4_FULL]
    assert v2["r4_full"] is True and v2["r4_mixed"] is False
    assert v2["r4_axis"] == ["raw"]
    # full + cn(仅电荷/立体被 cn 抹平≈真实不可判,R4b):
    v2 = gold_health_labels(substrate_smiles="C[NH3+]",
                            products_smiles=["CN"])
    assert v2["flags"] == [FLAG_R4_FULL]
    assert v2["r4_axis"] == ["cn"]
    # mixed + raw(金标混入题面身份 + 原样复读;碳增 R3 并发是规则独立性):
    v2 = gold_health_labels(substrate_smiles="CCO",
                            products_smiles=["CC=O", "CCO"])
    assert FLAG_R4_MIXED in v2["flags"]
    assert v2["r4_mixed_kind"] == "superset"
    assert v2["r4_axis"] == ["raw"]
    # mixed + cn(混入的题面身份仅 cn 相同;额外 O2 走 R2 双加氧模式):
    v2 = gold_health_labels(substrate_smiles="C[NH3+]",
                            products_smiles=["CN", "O=O"])
    assert v2["flags"] == [FLAG_R4_MIXED]
    assert v2["r4_axis"] == ["cn"]
    assert v2["r2_pattern"] == "dioxygenation"


def test_v2_r3_gap_formula_table():
    """改版 7 缺口分子式表:−1/−2 命中放行并标缺口;≤−3 人审桶。"""
    # 脱羧 −1,缺口 CO2(未列全):
    v2 = gold_health_labels(substrate_smiles="CCC(=O)O",   # C3H6O2
                            products_smiles=["CC"])        # C2H6,缺 C1O2
    assert v2["flags"] == [] and v2["manual_review"] == []
    assert v2["delta_c"] == -1
    assert v2["r3_gap"] == "CO2"
    # −2,C2 碎片(乙醛样式;1,3-丁二醇逆醛缩,乙醛未列全):
    v2 = gold_health_labels(substrate_smiles="C(O)CC(O)C",  # C4H10O2
                            products_smiles=["CCO"])        # C2H6O,缺 C2H4O
    assert v2["flags"] == [] and v2["manual_review"] == []
    assert v2["delta_c"] == -2
    assert v2["r3_gap"] == "acetaldehyde"
    # ≤−3 多事件/未列全嫌疑 → 人审桶(不判错):
    v2 = gold_health_labels(substrate_smiles="CCCCCCCC(=O)O",
                            products_smiles=["CC"])
    assert v2["flags"] == []
    assert "r3_gap_leq_minus3" in v2["manual_review"]
    # −1 缺口不在白名单(如 O-脱甲基缺 CH2)→ 人审桶
    # (任务口径白名单不含 CH2;评审例外清单提到 O-脱甲基,留人审定夺)
    v2 = gold_health_labels(substrate_smiles="COc1ccccc1",
                            products_smiles=["Oc1ccccc1"])
    assert v2["flags"] == []
    assert "r3_gap_unlisted" in v2["manual_review"]


def test_v2_plus_c_attribution_split():
    """改版 7 +C 归因分流:甲基化样式→不可达;对不上→数据错;羧化→人审。"""
    # SAM 甲基化样式(ΔC=+1,ΔH=+2,仅 C/H 变):
    v2 = gold_health_labels(substrate_smiles="CCO",    # C2H6O
                            products_smiles=["CCOC"])  # C3H8O
    v1 = gold_health_labels_v1(substrate_smiles="CCO",
                               products_smiles=["CCOC"])
    assert v1["flags"] == [FLAG_R3]                # v1 归因错(钉方向)
    assert v2["flags"] == [FLAG_R3_UNREACHABLE]    # 共底物缺失(补共底物/剔题)
    assert v2["r3_attribution"] == "methylation"
    assert FLAG_R3 not in v2["flags"]
    # 对不上任何可指认碎片 → 数据错:
    v2 = gold_health_labels(substrate_smiles="CC",
                            products_smiles=["CCCC"])
    assert v2["flags"] == [FLAG_R3]
    assert v2["r3_attribution"] == "unattributed"
    # 羧化样式(ΔC=+1,ΔO=+2)→ 单列人审桶(CO₂ 环境默认,不硬判):
    v2 = gold_health_labels(substrate_smiles="CC",
                            products_smiles=["CCC(=O)O"])
    v1 = gold_health_labels_v1(substrate_smiles="CC",
                               products_smiles=["CCC(=O)O"])
    assert v1["flags"] == [FLAG_R3]                # v1 一律数据错(钉方向)
    assert v2["flags"] == []
    assert v2["r3_attribution"] == "carboxylation"
    assert "carboxylation_style" in v2["manual_review"]


def test_v2_ribose_downgraded_to_observation():
    """改版 6 RIBOSE 降级:葡萄糖呋喃/吡喃书写差异不再误拦。"""
    v2 = gold_health_labels(substrate_smiles=GLUCO_PYRANOSE,
                            products_smiles=[GLUCO_FURANOSE])
    v1 = gold_health_labels_v1(substrate_smiles=GLUCO_PYRANOSE,
                               products_smiles=[GLUCO_FURANOSE])
    assert FLAG_R1 in v1["flags"] and "RIBOSE" in v1["r1_hit_elements"]
    assert v2["flags"] == []                       # 不再触发拦截
    assert v2["ribose_observed"] is True           # 观察标签列留痕
    assert v2["delta_elements"] == {}              # 同分子式 C6H12O6


def test_v2_r1_whitelist_complement():
    """改版 6 R1 白名单补集:非 {C,O,H} 元素新增一律拦(N/卤素并入)。"""
    # N 并入(题面无 N 的胺化):
    v2 = gold_health_labels(substrate_smiles="CCO",
                            products_smiles=["CCN"])
    v1 = gold_health_labels_v1(substrate_smiles="CCO",
                               products_smiles=["CCN"])
    assert v1["flags"] == [] and v1["unlisted_new_elements"] == ["N"]
    assert v2["flags"] == [FLAG_R1]
    assert v2["r1_hit_elements"] == ["N"]
    # 卤素并入:
    v2 = gold_health_labels(substrate_smiles="CC",
                            products_smiles=["CCCl"])
    assert v2["flags"] == [FLAG_R1]
    assert v2["r1_hit_elements"] == ["Cl"]
    # O 仍白名单(R2' 保留):
    v2 = gold_health_labels(substrate_smiles="CC",
                            products_smiles=["CCO"])
    assert v2["flags"] == []
    assert v2["r2_retained"] is True
    assert v2["r2_pattern"] == "monooxygenation"
    # 题面自带该元素(计数 Δ≤0)→ 天然不触发(共底物解释口径不变):
    v2 = gold_health_labels(substrate_smiles="CCN",
                            products_smiles=["CCN"])
    assert v2["flags"] == [FLAG_R4_FULL]           # 仅退化旗,无 R1


def test_v2_r2_pattern_labels():
    """R2' 来源指认改模式打标(留痕不作门槛)。"""
    # 水合:
    v2 = gold_health_labels(substrate_smiles="C=CC",
                            products_smiles=["CC(O)C"])
    assert v2["flags"] == [] and v2["manual_review"] == []
    assert v2["r2_pattern"] == "hydration"
    # 脱氢(−2H):
    v2 = gold_health_labels(substrate_smiles="CCO",
                            products_smiles=["CC=O"])
    assert v2["flags"] == []
    assert v2["r2_pattern"] == "dehydrogenation"
    assert v2["delta_h"] == -2


def test_v2_coa_style_rule_level_stable():
    """CoA 样式(067/114 同型):v2 规则级命中面与 v1 一致(R1+R3)。"""
    v2 = gold_health_labels(substrate_smiles="CC(=O)O",
                            products_smiles=[SYNTH_COA_LIKE])
    v1 = gold_health_labels_v1(substrate_smiles="CC(=O)O",
                               products_smiles=[SYNTH_COA_LIKE])
    assert v1["flags"] == [FLAG_R1, FLAG_R3]
    assert v2["r1"] is True and v2["r3"] is True   # 规则级不翻转
    assert v2["flags"] == [FLAG_R1, FLAG_R3]
    assert set(v2["r1_hit_elements"]) == {"P", "S"}


def test_v2_fail_closed_on_empty_sides():
    """空题面/空金标:fail-closed 人审(v1 静默通过)。"""
    v2 = gold_health_labels(substrate_smiles="CCO",
                            products_smiles=[])
    assert v2["flags"] == []
    assert v2["manual_review"] == ["gold_empty"]
    v2 = gold_health_labels(substrate_smiles="",
                            products_smiles=["CCO"])
    assert v2["flags"] == []
    assert v2["manual_review"] == ["surface_empty"]


def test_version_dispatch():
    """版本开关:默认 v2;version="v1" 走保留路径;未知版本报错。"""
    kwargs = dict(substrate_smiles="CCO", products_smiles=["CCOC"])
    assert gold_health_labels(**kwargs)["rule_version"] == RULE_VERSION_TAG
    v1_direct = gold_health_labels_v1(**kwargs)
    v1_switch = gold_health_labels(**kwargs, version="v1")
    assert v1_direct == v1_switch
    assert v1_direct["flags"] == [FLAG_R3]
    with pytest.raises(ValueError):
        gold_health_labels(**kwargs, version="v9")
