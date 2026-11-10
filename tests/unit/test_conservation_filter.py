"""T8 G2 守恒过滤 + 自排序夹具(PREREGISTRATION_G2 v2 判据验收)。

覆盖 mimo 评审风险清单 11 条(误杀防护)+ 迭代 2 两条硬约束(守恒只作
违规降位不作正向先验;纯重排硬验收)+ C0 等价性(开关 off 行为逐字节
不变)+ **mimo 终版评审 9 条必改**(docs/mimo_g2_rules_final_review_
response.md G 节:碎片可重构判据/②三条件+词边界/key2 化学矛盾+unclassified
中性/增侧惰性(a)/R1 加条件/编目对账+补全/DoU 电荷项+多原子去盐/档位
闭合+hold 分账)。全部合成 SMILES,零真实金标。

风险清单对照(mimo_conservation_rules_review_response §五):
R1 计数口径(脱羧/β-氧化硫解) R2 隐式供体未登记 R3 缀合双重触发
R4 整体矿化 R5 质子化/成盐形态 R6 金属配位 R7 减少侧碎片未列
R8 G3 编目覆盖不全 R9 按配比放行裂解(否决,键型判定) R10 剔空
R11 C1 释放只写主产物。
"""

from __future__ import annotations

import json

import pytest

from pathway_v43.domain.identity import cn_identity
from pathway_v43.domain.policy import prediction_policy
from pathway_v43.validation.conservation import (
    CONSERVATION_FILTER_VERSION,
    TIER_DOWNGRADE,
    TIER_EXCLUDE,
    TIER_PASS,
    analyze_side,
    conservation_filter_and_rank,
    declared_complete,
    registered_donors,
)

# ---------------------------------------------------------------- R1 计数口径


def test_r1_decarboxylation_co2_unlisted_not_killed():
    """脱羧只写主产物(金标主流形态):降位档都不进,pass+fragment_inferred。

    全物种口径下 R-COOH→R-H 为 ΔC=−1(C1 脱除族),不剔除不降位;
    CO2 未列按碎片重构反查(CO₂ ∈ 封闭碎片清单 + 羧基存在)放行
    (mimo 风险 #1/#11 保护对象;v2 R1 加碎片重构条件后仍放行)。
    """
    res = conservation_filter_and_rank(
        substrate_smiles="OC(=O)c1ccccc1",   # 苯甲酸
        candidates=[{"smiles": "c1ccccc1", "note": ""}])
    assert res.status == "ok"
    j = res.ranked[0]
    assert j.tier == TIER_PASS
    assert j.dC_main == -1
    assert j.flags.get("fragment_inferred") == "C1_family"
    assert j.flags.get("fragment_evidence") == "fragment_catalog:co2"
    assert j.g3b["transform_class"] == "decarboxylation"
    assert j.g3b["matched"] is True


def test_r1_decarboxylation_with_co2_listed_global_balance():
    """CO2 显式列出(多组分串):全局 ΔC=0,同分处理,无任何触发。"""
    res = conservation_filter_and_rank(
        substrate_smiles="OC(=O)c1ccccc1",
        candidates=[{"smiles": "c1ccccc1.O=C=O", "note": ""}])
    j = res.ranked[0]
    assert j.tier == TIER_PASS
    assert j.counts["delta"].get("C", 0) == 0
    assert not j.rules


def test_r1_beta_oxidation_thiolysis_c2_gap():
    """β-酮硫解型(1,3-二羰基底物):C2 缺口/大缺口按 motif 快路径放行。"""
    # 乙酰乙酸乙酯(C6,1,3-二羰基)→ 乙酸(C2):dC_main=−4,motif 命中
    res = conservation_filter_and_rank(
        substrate_smiles="CCOC(=O)CC(C)=O",
        candidates=[{"smiles": "CC(=O)O", "note": ""}])
    j = res.ranked[0]
    assert j.tier == TIER_PASS
    assert j.dC_main <= -3
    assert j.flags.get("cleavage_reconstructible") == "motif_cleavage"


def test_r1_cleavage_without_keytype_downgraded():
    """无键型位点的大缺口(非裂解族,碎片不可重构):降位不剔除。

    v2(D-2):正己烷 → 丙烷——底物无杂原子可断键、无 motif、无封闭
    碎片匹配,碎片不可重构 ⇒ 降位(烷烃任意 C–C 切不进通用切搜索)。
    """
    res = conservation_filter_and_rank(
        substrate_smiles="CCCCCC",
        candidates=[{"smiles": "CCC", "note": ""}])
    j = res.ranked[0]
    assert j.tier == TIER_DOWNGRADE
    assert any("G1b_fragment_not_reconstructible" in r for r in j.rules)


def test_r1_c1_release_without_reconstructible_fragment_downgraded():
    """R1 加碎片重构条件(A-6):ΔC=−1 但碎片不可重构 → 降位。

    甲苯 → 苯:缺口 CH2 无封闭碎片(母体无杂原子甲基/羰基)、无杂原子
    可断键 ⇒ "少一个碳"没有任何键能解释 ⇒ 降位(保留判别特征)。
    """
    res = conservation_filter_and_rank(
        substrate_smiles="Cc1ccccc1",
        candidates=[{"smiles": "c1ccccc1", "note": ""}])
    j = res.ranked[0]
    assert j.tier == TIER_DOWNGRADE
    assert any("G1b_fragment_not_reconstructible" in r for r in j.rules)


def test_r1_cross_element_inconsistent_gap_downgraded():
    """R1 四类应降位形态之二:跨元素不一致(A-6)。

    苄胺 → 苯(缺口 C1+N1,即"HCN 脱除"形):封闭清单 HCN 要求母体有
    腈/氰醇——苄胺没有;切搜索 C–N 切出的甲胺碎片留 C1 无法重构
    ⇒ 降位(不是脱羧族,不得被 C1 放行 + 脱氨白名单一并放过)。
    """
    res = conservation_filter_and_rank(
        substrate_smiles="NCc1ccccc1",
        candidates=[{"smiles": "c1ccccc1", "note": ""}])
    j = res.ranked[0]
    assert j.tier == TIER_DOWNGRADE
    assert any("G1b_fragment_not_reconstructible" in r for r in j.rules)


def test_r1_hcn_release_from_cyanohydrin_passes():
    """跨元素一致时的合法 HCN 释放:氰醇底物 → 羰基化合物,放行。"""
    # 苯乙酮氰醇 → 苯乙酮(HCN 未列):缺口 C1N1 = HCN,氰醇基团存在
    res = conservation_filter_and_rank(
        substrate_smiles="CC(O)(C#N)c1ccccc1",
        candidates=[{"smiles": "CC(=O)c1ccccc1", "note": ""}])
    j = res.ranked[0]
    assert j.tier == TIER_PASS
    assert j.flags.get("fragment_evidence") == "fragment_catalog:hcn"


def test_r1_ddou_anomaly_downgraded():
    """R1 四类应降位形态之三:ΔDoU 异常(|ΔDoU|≥2)。

    环己烷甲酸 → 苯(+CO₂ 未列):缺口 CO2 可重构,但 ΔDoU=+2
    (环收缩/脱氢跳变)提示骨架数错而非脱除 ⇒ 降位。
    """
    res = conservation_filter_and_rank(
        substrate_smiles="OC(=O)C1CCCCC1",
        candidates=[{"smiles": "c1ccccc1", "note": ""}])
    j = res.ranked[0]
    assert j.tier == TIER_DOWNGRADE
    assert any("G1b_ddou_anomaly" in r for r in j.rules)


# ------------------------------------------- 必改 1:碎片可重构(D-2 教科书类)


def test_v2_chlorpyrifos_like_organophosphate_cleavage_passes():
    """【最高误杀风险】有机磷水解(毒死蜱型,P–O 断键):碎片重构放行。

    毒死蜱(C9)→ 3,5,6-三氯吡啶-2-醇(C5,主产物),ΔC_main=−4,
    三 motif 一个不中——v1 落降位;v2 通用回退:P–O(芳基)单键切,
    硫代磷酸二乙酯碎片硬元素精确对账 ⇒ fragment_inferred 放行。
    """
    res = conservation_filter_and_rank(
        substrate_smiles="CCOP(=S)(OCC)Oc1cc(Cl)c(Cl)cc1Cl",
        candidates=[{"smiles": "Oc1cc(Cl)c(Cl)cc1Cl", "note": ""}])
    j = res.ranked[0]
    assert j.tier == TIER_PASS
    assert j.dC_main == -4
    assert j.flags.get("cleavage_reconstructible") == "bond_cut_search"


def test_v2_parathion_like_p_aryl_cleavage_passes():
    """对硫磷型(P–O 芳基断裂,主产物对硝基苯酚 ΔC=−4):放行。"""
    res = conservation_filter_and_rank(
        substrate_smiles="CCOP(=S)(OCC)Oc1ccc([N+](=O)[O-])cc1",
        candidates=[{"smiles": "Oc1ccc([N+](=O)[O-])cc1", "note": ""}])
    j = res.ranked[0]
    assert j.tier == TIER_PASS
    assert j.flags.get("cleavage_reconstructible") == "bond_cut_search"


def test_v2_pyrethroid_like_ester_hydrolysis_passes():
    """拟除虫菊酯水解(菊酯型,酯 C–O 断键,ΔC_main≤−3):放行。

    环丙烷菊酯骨架 → 两件水解产物都列出时全局 ΔC=0(水合签名、
    酯键型匹配);只列苄醇主产物时缺口 = 菊酸部分,单键切重构放行。
    """
    substrate = "CC1C(C(=O)OCc2ccccc2)C1C=C(Cl)Cl"
    # 两件都列出:全局 ΔC=0(水解 +H2O),酯键型匹配
    res_both = conservation_filter_and_rank(
        substrate_smiles=substrate,
        candidates=[{"smiles": "OCc1ccccc1.O=C(O)C1CC1C(Cl)=C(Cl)C",
                     "note": ""}])
    j = res_both.ranked[0]
    assert j.tier == TIER_PASS
    assert j.g3b["transform_class"] == "hydrolysis"
    assert j.g3b["matched"] is True
    # 只列苄醇主产物(菊酸未列):dC_main=−6,碎片重构放行
    res_main = conservation_filter_and_rank(
        substrate_smiles=substrate,
        candidates=[{"smiles": "OCc1ccccc1", "note": ""}])
    j2 = res_main.ranked[0]
    assert j2.tier == TIER_PASS
    assert j2.dC_main <= -3
    assert j2.flags.get("cleavage_reconstructible") == "bond_cut_search"


def test_v2_glycoside_hydrolysis_passes():
    """糖苷水解(苯基葡萄糖苷,糖苷 C–O 断键,ΔC_main=−6):放行。

    苷元(苯酚,C6)与糖基(C6)并列最大碳——A-5:对全部并列最大 C
    组分逐一施加 G1-b,两侧缺口都经 C–O 切重构 ⇒ 放行(减少侧白名单
    "脱糖基"与碳侧 G1-b 同一判据,修复三处互斥)。
    """
    res = conservation_filter_and_rank(
        substrate_smiles="OC1OC(O)C(O)C(O)C(O)C1Oc1ccccc1",
        candidates=[{"smiles": "Oc1ccccc1", "note": ""}])
    j = res.ranked[0]
    assert j.tier == TIER_PASS
    assert j.dC_main == -6
    assert j.flags.get("cleavage_reconstructible") == "bond_cut_search"


def test_v2_large_ester_and_peptide_hydrolysis_passes():
    """大离去基团酯/肽水解(ΔC_main≥3):同一类反应同一处置。

    - 大酯:氯苄基异丁酸酯(C11)→ 氯苄醇主产物(C7),缺口 = 酰基侧;
    - 三肽缩合形态:酰胺 C–N 断键,主产物氨基酸缺口 = 另一氨基酸侧;
    甲酯/乙酯(−1/−2)与大酯不再按离去基团碳数分成两套处置。
    """
    res_e = conservation_filter_and_rank(
        substrate_smiles="CC(C)C(=O)OCc1ccccc1Cl",
        candidates=[{"smiles": "OCc1ccccc1Cl", "note": ""}])
    je = res_e.ranked[0]
    assert je.tier == TIER_PASS
    assert je.dC_main <= -3
    assert je.flags.get("cleavage_reconstructible") == "bond_cut_search"
    # 二肽(异丙胺-苯丙氨酸形态)→ 苯丙氨酸主产物:酰胺 C–N 切重构
    res_p = conservation_filter_and_rank(
        substrate_smiles="CC(C)NC(=O)C(N)Cc1ccccc1",
        candidates=[{"smiles": "NC(Cc1ccccc1)C(=O)O", "note": ""}])
    jp = res_p.ranked[0]
    assert jp.tier == TIER_PASS
    assert jp.flags.get("cleavage_reconstructible") == "bond_cut_search"


def test_v2_triglyceride_like_three_cuts_passes():
    """三酰甘油型(需同时断 3 条酯键,脂肪酸主产物):有界多键切覆盖。"""
    # 三乙酸甘油酯 → 乙酸(主产物)+ 甘油:ΔC_main=−6,3 键切
    res = conservation_filter_and_rank(
        substrate_smiles="CC(=O)OCC(OC(C)=O)COC(C)=O",
        candidates=[{"smiles": "CC(=O)O", "note": ""}])
    j = res.ranked[0]
    assert j.tier == TIER_PASS
    assert j.flags.get("cleavage_reconstructible") == "bond_cut_search"


# ---------------------------------------------------------------- R2/R3 供体


def test_r2_r3_conjugation_double_trigger_excluded_without_donor():
    """缀合型单步(糖基/磺基/磷酸/甲基/乙酰)无登记供体:可证明违规,剔除。

    (A-1 惰性声明:答案路径上既有元素门先行,本分支不可达;单元级
    直调验证判据本身。)每组掺一个合规对照候选(羟化),验证剔除
    不放大为剔空 hold。
    """
    cases = [
        # (底物, 违规产物, 预期规则子串)
        ("Oc1ccccc1", "OC1C(O)C(O)C(O)C(O1)c1ccccc1",
         "G1a1_surplus_carbon"),          # 糖基化 +C
        ("Oc1ccccc1", "Oc1ccccc1S(=O)(=O)O",
         "G2a_alien_heteroatom"),         # 磺基转移 +S
        ("Oc1ccccc1", "Oc1ccccc1OP(=O)(O)O",
         "G2a_alien_heteroatom"),         # 磷酸化 +P
        ("Oc1ccccc1", "COc1ccccc1",
         "G1a1_surplus_carbon"),          # 甲基化 +C1
        ("Oc1ccccc1", "CC(=O)Oc1ccccc1",
         "G1a1_surplus_carbon"),          # 乙酰化 +C2
        ("CC(=O)C(=O)[O-]", "CC(N)C(=O)[O-]",
         "G2a_alien_heteroatom"),         # 转氨 +N
    ]
    for sub, prod, rule_frag in cases:
        res = conservation_filter_and_rank(
            substrate_smiles=sub,
            candidates=[{"smiles": prod, "note": ""},
                        {"smiles": _hydroxylation_control(sub), "note": ""}])
        assert res.status == "ok", (sub, prod, res.status)
        assert len(res.excluded) == 1, (sub, prod)
        assert any(rule_frag in r for r in res.excluded[0].rules), (
            sub, prod, res.excluded[0].rules)


def _hydroxylation_control(substrate: str) -> str:
    """合规对照候选(羟化/同分族,按底物元素集构造)。"""
    return {
        "Oc1ccccc1": "Oc1ccccc1O",
        "CC(=O)C(=O)[O-]": "CC(O)C(=O)[O-]",   # 丙酮酸→乳酸(+2H 还原)
    }[substrate]


def test_r2_donor_registry_releases_conjugation():
    """题面显式登记供体(封闭关键词表)→ 同一批缀合放行(供体例外制)。

    B-1:按关键词分别定值——乙酰 +C2(不再按 C4 上限一刀切)。
    """
    cases = [
        ("Oc1ccccc1", "OC1C(O)C(O)C(O)C(O1)c1ccccc1",
         "with UDP-glucose as donor", {"C": 6}),
        ("Oc1ccccc1", "Oc1ccccc1S(=O)(=O)O",
         "PAPS 供体", {"S": 1}),
        ("Oc1ccccc1", "Oc1ccccc1OP(=O)(O)O",
         "ATP", {"P": 1}),
        ("Oc1ccccc1", "COc1ccccc1",
         "SAM 供体", {"C": 1}),
        ("Oc1ccccc1", "CC(=O)Oc1ccccc1",
         "乙酰-CoA", {"C": 2}),
        ("CC(=O)C(=O)[O-]", "CC(N)C(=O)[O-]",
         "谷氨酸 amino donor", {"N": 1}),
    ]
    for sub, prod, surface, expected_donor in cases:
        res = conservation_filter_and_rank(
            substrate_smiles=sub, candidates=[{"smiles": prod, "note": ""}],
            surface_text=surface)
        assert res.status == "ok", (sub, prod)
        assert res.donors == expected_donor, (surface, res.donors)
        assert not res.excluded, (sub, prod, res.excluded)
        assert res.ranked[0].tier == TIER_PASS


def test_r2_donor_registry_closed_keyword_table():
    """登记表为封闭表:未登记同义词不放行(默认集每放宽一项=拆一角)。"""
    donors = registered_donors("加一点谷氨酸盐")  # "谷氨酸" 命中
    assert donors == {"N": 1}
    assert registered_donors("碳酸氢钠存在") == {"C": 1}   # hco3/碳酸氢 命中
    assert registered_donors("核苷酸糖") == {}             # 未登记变体:无
    assert registered_donors("") == {}                     # dev 题面:无
    # note 文本不作为供体登记源(登记语义 = 题面显式登记)
    res = conservation_filter_and_rank(
        substrate_smiles="CC(=O)C(=O)[O-]",
        candidates=[{"smiles": "CC(N)C(=O)[O-]",
                     "note": "用的是谷氨酸转氨"}],
        surface_text="")
    assert len(res.excluded) == 1


def test_r2_donor_registry_v2_word_boundary_and_values():
    """v43-donor-registry-2(B 节):词边界 / 按关键词分别定值 / 删裸词 coa。"""
    assert registered_donors("with acetyl-CoA as donor") == {"C": 2}
    assert registered_donors("malonyl-CoA 延伸") == {"C": 3}
    assert registered_donors("succinyl-CoA / butyryl-CoA") == {"C": 4}
    # 裸词 coa 已删:requires CoA 不构成任何碳转移登记
    assert registered_donors("requires CoA") == {}
    # 词边界:coa 不命中 coal/coast;sam 不命中 sample;aps 不命中 perhaps
    assert registered_donors("on the coast, same sample, perhaps") == {}
    # 同元素取 max(乙酰+丙二酰同时命中 → C 预算 = 3,不求和)
    assert registered_donors("acetyl-CoA and malonyl-CoA") == {"C": 3}
    # 跨元素天然并存(氨甲酰磷酸 = C1+N1)
    assert registered_donors("carbamoyl phosphate") == {"C": 1, "N": 1}
    # CO₂ Unicode 归一
    assert registered_donors("CO₂ fixation") == {"C": 1}
    # ThDP 行已删(B-4:+C 非可判定值;本题域几乎不出现)
    assert registered_donors("thiamine diphosphate acyloin") == {}


def test_r2_default_implicit_donors_only_water_oxygen():
    """默认隐式供体恒为 {H2O, O2}:增 O/换 H 不触发任何档。"""
    res = conservation_filter_and_rank(
        substrate_smiles="c1ccccc1",
        candidates=[{"smiles": "Oc1ccccc1O", "note": ""}])  # 双羟化 +2O
    assert res.ranked[0].tier == TIER_PASS
    assert not res.ranked[0].rules


# ---------------------------------------------------------------- R4 矿化


def test_r4_mineralization_downgraded_not_excluded():
    """整体矿化答案(超口径):降位(不是违规,不声明完整不剔除)。"""
    # 苯丙氨酸 → CO2 + H2O + NH3:dC_main=−8,碎片不可重构
    res = conservation_filter_and_rank(
        substrate_smiles="NC(Cc1ccccc1)C(=O)O",
        candidates=[{"smiles": "O=C=O.O.N", "note": ""}])
    j = res.ranked[0]
    assert j.tier == TIER_DOWNGRADE
    assert any("G1b_fragment_not_reconstructible" in r for r in j.rules)


# ---------------------------------------------------------------- R5 形态差


def test_r5_salt_and_protonation_form_differences():
    """质子化态/成盐形态差异:去盐+电荷归一后同计数,不触发(mimo 风险 #5)。"""
    # 苯甲酸钠盐产物(带 Na spectator)vs 苯甲酸底物:计数一致
    res = conservation_filter_and_rank(
        substrate_smiles="OC(=O)c1ccccc1",
        candidates=[{"smiles": "O=C([O-])c1ccccc1.[Na+]", "note": ""}])
    j = res.ranked[0]
    assert j.tier == TIER_PASS
    assert not j.rules
    assert "Na" not in j.counts["delta"]
    # 羧酸根(质子化态差)产物:同分
    res2 = conservation_filter_and_rank(
        substrate_smiles="OC(=O)c1ccccc1",
        candidates=[{"smiles": "O=C([O-])c1ccccc1", "note": ""}])
    j2 = res2.ranked[0]
    assert j2.tier == TIER_PASS
    assert j2.counts["delta"].get("H", 0) == 0
    assert j2.counts["delta"].get("C", 0) == 0


def test_r5_multiatomic_counterion_desalt():
    """必改 7(F-3/C-2):去盐扩展到多原子反离子。

    formate/acetate/sulfate/Tris/TEA/HCO₃⁻ 型带电多原子抗衡离子
    (带电 ∧ 独立组分 ∧ 碳数严格小于主体)被剥离,不再进硬门元素
    计数与主产物判定。
    """
    # 丙氨酸铵 + 甲酸根:甲酸根(C1 < 丙氨酸 C3)剥离
    side = analyze_side("O=C[O-].CC([NH3+])C(=O)O")
    assert side.parse_ok is True
    assert side.formula["C"] == 3            # 只剩丙氨酸的碳
    assert len(side.salt_stripped) == 1      # 甲酸根已剥
    # 苯甲酸盐 + 质子化三乙胺:TEA(C6 < 苯甲酸 C7)剥离
    side2 = analyze_side("O=C([O-])c1ccccc1.CC[NH+](CC)CC")
    assert side2.formula["C"] == 7
    assert "N" not in side2.formula
    # 硫酸根(不含碳):剥离
    side3 = analyze_side("O=S(=O)([O-])[O-].CC([NH3+])C(=O)O")
    assert side3.formula["C"] == 3
    assert "S" not in side3.formula
    # 工作流级:多原子反离子产物不再被读成增 N/增 S
    res = conservation_filter_and_rank(
        substrate_smiles="CC(N)C(=O)O",
        candidates=[{"smiles": "O=C[O-].CC([NH3+])C(=O)O", "note": ""}])
    j = res.ranked[0]
    assert j.tier == TIER_PASS
    assert not j.rules


# ---------------------------------------------------------------- R6 金属


def test_r6_metal_coordination_vs_covalent():
    """金属 spectator/配位缔合不按新增金属剔除;共价金属新增计违规。

    C 节 1(共价金属 → G2-a 硬剔,写死)/ C 节 6(配位不可判形态 →
    不可审计降位+标注,不 hold)。
    """
    # 两侧均为金属盐形态(spectator 剥离后计数一致)
    res = conservation_filter_and_rank(
        substrate_smiles="O=C([O-])c1ccccc1.[Na+]",
        candidates=[{"smiles": "O=C([O-])c1ccccc1.[K+]", "note": ""}])
    assert res.ranked[0].tier == TIER_PASS
    assert not res.ranked[0].rules
    # 共价键合金属新增(苯基汞):无登记供体 → 剔除(G2-a 归属档写死)
    res2 = conservation_filter_and_rank(
        substrate_smiles="c1ccccc1",
        candidates=[{"smiles": "[Hg]c1ccccc1", "note": ""}])
    assert any("G2a_alien_heteroatom" in r for r in res2.excluded[0].rules)
    # 配位不可判形态(金属计数不变而共价态翻转):降位+标注,不剔除不 hold
    # 底物 = 共价锌苯甲酸(中性单组分,去盐不剥离);产物 = 苯甲酸 + 中性
    # 游离锌原子(不带电 → 不剥离)→ Zn 计数不变、共价态翻转
    res3 = conservation_filter_and_rank(
        substrate_smiles="[Zn]OC(=O)c1ccccc1",
        candidates=[{"smiles": "OC(=O)c1ccccc1.[Zn]", "note": ""}])
    assert res3.status == "ok"
    j3 = res3.ranked[0]
    assert j3.tier == TIER_DOWNGRADE
    assert any("metal_coordination_shift" in r for r in j3.rules)


# ---------------------------------------------------------------- R7 碎片未列


def test_r7_reduction_side_fragments_unlisted():
    """减少侧碎片未列(X⁻/NH₃/Pi):白名单族放行+标注,不降位。"""
    cases = [
        ("Oc1ccc(Cl)cc1", "Oc1ccccc1", "Cl"),   # 脱卤(X⁻ 未列)
        ("Nc1ccccc1", "c1ccccc1", "N"),          # 脱氨(NH₃ 未列)
        ("OP(=O)(O)Oc1ccccc1", "Oc1ccccc1", "P"),  # 脱磷酸(Pi 未列)
    ]
    for sub, prod, el in cases:
        res = conservation_filter_and_rank(
            substrate_smiles=sub, candidates=[{"smiles": prod, "note": ""}])
        j = res.ranked[0]
        assert j.tier == TIER_PASS, (sub, j.rules)
        assert j.flags.get("reduction_whitelist") == el
        assert not [r for r in j.rules if "not_reconstructible" in r]


# ---------------------------------------------------------------- R8/R9 编目


def test_r8_unclassified_transform_is_neutral():
    """必改 3(E-2/D-3):unclassified 归中性(落 key 3),不受 key 2 惩罚。

    苯酚 → 苯氧自由基(ΔH−1 → ΔDoU 非整数 → DoU 不可审计 →
    unclassified):v1 会按"编目外"降位排序分量垫后;v2 中性——
    在 pass 档内仍按提案原位次排在 matched 候选之前(位次 0 保持)。
    """
    res = conservation_filter_and_rank(
        substrate_smiles="Oc1ccccc1",
        candidates=[{"smiles": "[O]c1ccccc1", "note": ""},    # 0 中性
                    {"smiles": "Oc1ccccc1O", "note": ""}])    # 1 matched
    assert [j.index for j in res.ranked] == [0, 1]   # 中性不被 matched 压后
    j0 = res.ranked[0]
    assert j0.g3b["transform_class"] == "unclassified"
    assert j0.g3b["neutral"] is True
    assert j0.g3b["contradiction"] is False
    assert not [r for r in j0.rules if "g3b" in r]


def test_r8_chemical_contradiction_still_penalized():
    """必改 3:key 2 只对化学矛盾生效(底物具备可进攻基团而变换类矛盾)。

    苯酚 → 苯(还原脱氧):底物有羟基/芳环可进攻类,候选变换类
    reductive_deoxygenation 不在其列 → 化学矛盾,排序分量靠后。
    """
    res = conservation_filter_and_rank(
        substrate_smiles="Oc1ccccc1",
        candidates=[{"smiles": "c1ccccc1", "note": ""},        # 0 矛盾
                    {"smiles": "Oc1ccccc1O", "note": ""}])    # 1 matched
    assert [j.index for j in res.ranked] == [1, 0]
    j0 = res.ranked[1]
    assert j0.g3b["contradiction"] is True
    assert any("g3b_chemical_contradiction" in r for r in j0.rules)


def test_r8_new_oxygenation_classes_epoxidation_s_n_oxidation():
    """必改 3(D-3):补变换类环氧化/S-氧化/N-氧化(+O 非羟化类)。"""
    # 环氧化:丙烯 → 环氧丙烷(+O,ΔH=0,产物环氧子结构)
    res_e = conservation_filter_and_rank(
        substrate_smiles="CC=C",
        candidates=[{"smiles": "CC1CO1", "note": ""}])
    je = res_e.ranked[0]
    assert je.g3b["transform_class"] == "epoxidation"
    assert je.g3b["matched"] is True
    # S-氧化:茴香硫醚 → 亚砜
    res_s = conservation_filter_and_rank(
        substrate_smiles="CSc1ccccc1",
        candidates=[{"smiles": "C[S](=O)c1ccccc1", "note": ""}])
    js = res_s.ranked[0]
    assert js.g3b["transform_class"] == "s_oxidation"
    assert js.g3b["matched"] is True
    # N-氧化:N,N-二甲基苯胺 → N-氧化物
    res_n = conservation_filter_and_rank(
        substrate_smiles="CN(C)c1ccccc1",
        candidates=[{"smiles": "C[N+](C)([O-])c1ccccc1", "note": ""}])
    jn = res_n.ranked[0]
    assert jn.g3b["transform_class"] == "n_oxidation"
    assert jn.g3b["matched"] is True
    # 对照:羟化(+O,ΔH=0,无上述产物子结构)仍归 oxygenation
    res_h = conservation_filter_and_rank(
        substrate_smiles="c1ccccc1",
        candidates=[{"smiles": "Oc1ccccc1", "note": ""}])
    assert res_h.ranked[0].g3b["transform_class"] == "oxygenation"


def test_r8_catalog_gap_patterns_registered():
    """必改 6(D-5):编目缺口补全——氨基甲酸酯/脲/磺酰胺/膦酸酯 C–P/
    季铵/过氧化物/1,2-二羰基/五元杂芳环全部入册(34 条对账一致)。"""
    from pathway_v43.validation.conservation import ATTACKABLE_PATTERNS
    assert len(ATTACKABLE_PATTERNS) == 34   # D-4:数字与清单一致
    cases = {
        "O=C(OCC)Nc1ccccc1": "carbamate",       # 氨基甲酸酯(酰胺不专 cover)
        "NC(=O)N(C)C": "urea",                   # 脲(敌草隆型骨架)
        "CS(=O)(=O)Nc1ccccc1": "sulfonamide",   # 磺酰胺(磺胺类)
        "CP(=O)(O)O": "phosphonate_cp",         # 膦酸酯/C–P(草甘膦型)
        "C[N+](C)(C)C": "quaternary_ammonium",  # 季铵(百草枯/胆碱型)
        "COOC": "peroxide",                      # 过氧化物
        "O=C(C=O)c1ccccc1": "alpha_dicarbonyl",  # 1,2-二羰基(α-二酮)
        "c1ccoc1": "heteroaromatic_5",           # 五元杂芳环(呋喃)
        "CC(=O)OCC1OC(=O)C1": "ester",          # 内酯(酯条目无环限制)
    }
    for smi, expected in cases.items():
        side = analyze_side(smi)
        assert expected in side.pattern_names, (smi, side.pattern_names)
    # 覆盖声明:糖苷端基碳由缩醛条目覆盖
    assert "acetal" in analyze_side(
        "OC1OC(O)C(O)C(O)C1Oc1ccccc1").pattern_names


# ---------------------------------------------------------------- R10 剔空


def test_r10_all_excluded_triggers_hold():
    """剔空即 hold(诚实弃权)+ hold 分账(C 节 4)。"""
    res = conservation_filter_and_rank(
        substrate_smiles="Oc1ccccc1",
        candidates=[{"smiles": "Nc1ccccc1", "note": ""},
                    {"smiles": "Oc1ccccc1N", "note": ""},
                    {"smiles": "Sc1ccccc1", "note": ""}])
    assert res.status == "hold"
    assert res.hold_reason == "all_rejected"
    assert res.hold_detail == "all_excluded"
    assert res.reject_count == 3
    assert len(res.excluded) == 3
    assert not res.ranked


def test_r10_undecidable_substrate_hold():
    """底物不可判定 → 整题 hold(输入侧子类,与剔空分账)。"""
    res = conservation_filter_and_rank(
        substrate_smiles="not_a_smiles",
        candidates=[{"smiles": "c1ccccc1", "note": ""}])
    assert res.status == "hold"
    assert res.hold_reason == "substrate_undecidable"
    assert res.hold_detail == "substrate_unparseable"
    assert res.reject_count == 0
    assert res.substrate_parse_ok is False


# ---------------------------------------------------------------- R11 C1 释放


def test_r11_c1_release_main_product_only():
    """脱甲基只写主产物(苯甲醚→苯酚):C1 族归因,pass 不降位。"""
    res = conservation_filter_and_rank(
        substrate_smiles="COc1ccccc1",
        candidates=[{"smiles": "Oc1ccccc1", "note": ""}])
    j = res.ranked[0]
    assert j.tier == TIER_PASS
    assert j.dC_main == -1
    assert j.flags.get("fragment_inferred") == "C1_family"
    assert j.flags.get("fragment_evidence") == "fragment_catalog:ch2o"
    assert j.g3b["transform_class"] == "c1_release"
    assert j.g3b["matched"] is True


# ---------------------------------------------------------------- 声明完整


def test_declared_complete_atom_loss_excluded():
    """②三条件硬剔(A-3):声明完整 ∧ 原子消失 ∧ 缺失不可重构。"""
    res = conservation_filter_and_rank(
        substrate_smiles="NC(Cc1ccccc1)C(=O)O",
        candidates=[{"smiles": "c1ccccc1",
                     "note": "complete, sole product"}])
    assert len(res.excluded) == 1
    assert any("G1a2_declared_complete_atom_loss" in r
               for r in res.excluded[0].rules)


def test_declared_complete_reconstructible_loss_downgraded_not_excluded():
    """②三条件(A-3):声明完整但缺失可重构(CO₂)→ 降位不硬剔。

    苯甲酸 → 苯 + "complete":缺口 = CO₂(羧基存在)——判分口径若
    省略 CO₂ 组分,该候选仍可命中金标,不可逆硬剔会误杀(A-3 的
    CO₂/H₂O 接口:可重构缺失永不硬剔)。
    """
    res = conservation_filter_and_rank(
        substrate_smiles="OC(=O)c1ccccc1",
        candidates=[{"smiles": "c1ccccc1",
                     "note": "complete, sole product"}])
    assert res.status == "ok"
    j = res.ranked[0]
    assert j.tier == TIER_DOWNGRADE
    assert any("declared_complete_loss_reconstructible" in r
               for r in j.rules)


def test_declared_complete_word_boundary_and_negation():
    """v43-cons-kw-2(A-3):词边界 + 否定前缀排除(子串陷阱修复)。"""
    assert declared_complete("COMPLETE list") is True
    assert declared_complete("产物完整") is True
    # 子串陷阱:complete 不再命中 incomplete;not completely 不算声明
    assert declared_complete("incomplete degradation pathway") is False
    assert declared_complete("not completely degraded") is False
    assert declared_complete("可能还有其他产物") is False
    assert declared_complete("") is False


def test_declared_complete_mineralization_wording_family():
    """v43-cons-kw-2(A-3):封闭表补矿化措辞族(R2 声明侧防线)。"""
    assert declared_complete("completely mineralized to CO2 and H2O") is True
    assert declared_complete("fully degraded") is True
    assert declared_complete("quantitatively converted") is True
    assert declared_complete("the compound was mineralization product") is True
    assert declared_complete("彻底降解,矿化完全") is True
    assert declared_complete("矿化") is True
    assert declared_complete("完全转化") is True
    # 否定前缀
    assert declared_complete("不完全降解") is False
    assert declared_complete("未完全转化") is False


def test_mineralized_declared_complete_atom_loss_path():
    """矿化声明 + 不可重构缺失 → ②硬剔路径(声明侧防线闭合)。"""
    res = conservation_filter_and_rank(
        substrate_smiles="NC(Cc1ccccc1)C(=O)O",
        candidates=[{"smiles": "c1ccccc1",
                     "note": "completely mineralized, sole product"}])
    assert len(res.excluded) == 1
    assert any("G1a2_declared_complete_atom_loss" in r
               for r in res.excluded[0].rules)


# ------------------------------------------------- 必改 7:DoU 电荷项(F-2)


def test_dou_with_charge_term_quaternary_ammonium():
    """DoU 带电荷项(F-2):季铵(永久正电,Uncharger 中和不了)整数化。

    胆碱 C5H14NO+:DoU=(2×5+2+1−14+1)/2=0;v1 按中性式算得 −0.5
    (非整数 → ΔDoU 签名错 → 变换类错 → 被 key 2 沉底)。
    """
    side = analyze_side("C[N+](C)(C)CCO")
    assert side.parse_ok is True
    assert side.dou == 0
    # 甜菜碱型两性离子(净电荷 0,Uncharger 后 N+ 残留 → q 项入账)
    side_b = analyze_side("C[N+](C)(C)CC(=O)[O-]")
    assert side_b.dou is not None
    # 五价磷(P=S)整数入账:毒死蜠型底物 DoU=5(环 4 + P=S 1)——
    # v1 中性式算法对此类读出半整数(实现缺陷,F-2 修复对象)
    side_p = analyze_side("CCOP(=S)(OCC)Oc1cc(Cl)c(Cl)cc1Cl")
    assert side_p.dou == 5


# ------------------------------------------------- 迭代 2 硬约束(降位制)


def test_conservation_not_positive_prior():
    """守恒不作正向排序先验:同 pass 档内 cons=0 与 ΔC<0 候选原序不变。

    (迭代 2 s3x 回撤教训:22 题金标 11 题 cons>1,守恒升序是反向先验。)
    """
    # 0 位:苯酚(ΔC=0 同分异构级);1 位:苯(脱羧族 ΔC=−1 合规)
    res = conservation_filter_and_rank(
        substrate_smiles="Oc1ccccc1",
        candidates=[{"smiles": "Oc1ccccc1", "note": ""},
                    {"smiles": "c1ccccc1", "note": ""}])
    assert [j.index for j in res.ranked] == [0, 1]   # 原序保持


def test_pure_reorder_no_exclusion_set_unchanged():
    """纯重排硬验收:无剔除时候选集合(多重集)与 @5 逐题不变。

    含 +C1 剔除项的混合集:kept ∪ excluded 恰等于原集合(无丢失无新增),
    集合变化只允许来自剔除与 hold。
    """
    cands = [
        {"smiles": "COc1ccccc1", "note": ""},   # +C1 无供体 → 剔除
        {"smiles": "Oc1ccccc1O", "note": ""},   # 羟化 pass
        {"smiles": "c1ccccc1", "note": ""},     # ΔO=−1 pass(去酚,矛盾分量)
        {"smiles": "Oc1ccccc1F", "note": ""},   # +F 无供体 → 剔除
    ]
    res = conservation_filter_and_rank(
        substrate_smiles="Oc1ccccc1", candidates=cands)
    kept = sorted(j.smiles for j in res.ranked)
    excluded = sorted(j.smiles for j in res.excluded)
    all_c = sorted(c["smiles"] for c in cands)
    assert sorted(kept + excluded) == all_c      # 无丢失无新增
    assert len(res.ranked) + len(res.excluded) == len(cands)
    assert len(res.ranked) == 2                   # @5 不变(剔除例外)


def test_rank_key_order_tier_then_g3b_then_original():
    """冻结键序:①处置档 ②G3-b 化学矛盾 ③提案原位次(稳定)。"""
    # 底物甲苯;候选:0 苯(ΔC=−1 不可重构 → 降位 + 化学矛盾),
    # 1 乙烷(ΔC=−5 不可重构 → 降位,unclassified 中性),2/3 羟化
    # (pass/matched)→ 期望序 2,3,1,0(降位档内:中性在前、矛盾垫底、
    # 同组按原位次)
    cands = [
        {"smiles": "c1ccccc1", "note": ""},
        {"smiles": "CC", "note": ""},
        {"smiles": "Cc1ccccc1O", "note": ""},    # 羟化 pass/matched
        {"smiles": "Cc1ccc(O)cc1", "note": ""},  # 对甲酚 pass/matched
    ]
    res = conservation_filter_and_rank(
        substrate_smiles="Cc1ccccc1", candidates=cands)
    assert [j.index for j in res.ranked] == [2, 3, 1, 0]
    assert res.n_downgraded == 2
    assert res.ranked[0].g3b["matched"] is True
    assert res.ranked[2].g3b["neutral"] is True      # 乙烷:unclassified 中性
    assert res.ranked[3].g3b["contradiction"] is True  # 苯:化学矛盾垫底


def test_stable_within_tier_and_match():
    """同档同匹配组内按原位次稳定序(防实现者自由发挥)。"""
    cands = [
        {"smiles": "Cc1ccccc1O", "note": ""},    # 邻甲酚
        {"smiles": "Cc1cc(O)ccc1", "note": ""},  # 间甲酚
        {"smiles": "Cc1ccc(O)cc1", "note": ""},  # 对甲酚
    ]
    res = conservation_filter_and_rank(
        substrate_smiles="Cc1ccccc1", candidates=cands)
    tiers = [j.tier for j in res.ranked]
    assert all(t == TIER_PASS for t in tiers)
    assert [j.index for j in res.ranked] == [0, 1, 2]   # 原序保持
    assert sorted(j.smiles for j in res.ranked) == sorted(
        c["smiles"] for c in cands)


def test_downgrade_empty_reports_original_order():
    """C 节 5:降位全空(无剔除)时按原位次照常报出(G2 no-op,无害)。

    键 2 在降位档内仍生效(中性在前、矛盾垫底)——本题乙烷(中性)
    在苯(化学矛盾)之前;全部按降位档报出、不入 hold。
    """
    cands = [
        {"smiles": "c1ccccc1", "note": ""},   # 甲苯→苯:不可重构,降位+矛盾
        {"smiles": "CC", "note": ""},         # 降位,unclassified 中性
    ]
    res = conservation_filter_and_rank(
        substrate_smiles="Cc1ccccc1", candidates=cands)
    assert res.status == "ok"
    assert res.n_downgraded == 2
    assert [j.index for j in res.ranked] == [1, 0]   # 照常报出,不入 hold


# ---------------------------------------------------------------- 规范化单元


def test_analyze_side_desalt_and_formula():
    """计数单元:去盐/电荷归一/含 H 计数/解析失败不按零。"""
    side = analyze_side("O=C([O-])c1ccccc1.[Na+]")
    assert side.parse_ok is True
    assert side.formula["C"] == 7
    assert side.formula["O"] == 2
    assert "Na" not in side.formula
    assert side.salt_stripped  # Na spectator 已剥离
    bad = analyze_side("not_a_smiles")
    assert bad.parse_ok is False
    assert bad.formula is None   # 不按零


def test_analyze_side_tied_main_components():
    """A-5:并列最大 C 组分全部登记(逐一施加 G1-b 的数据面)。"""
    # 乙酸酐(C4)与丁酸(C4)并列最大碳 → 两个 main_formulas
    side = analyze_side("CC(=O)OC(C)=O.O=C(O)CCC")
    assert len(side.main_formulas) == 2


def test_versions_registered():
    """版本三元组随结果落账(进 run identity 的同一取值;v2 全量升版)。"""
    res = conservation_filter_and_rank(
        substrate_smiles="c1ccccc1", candidates=[{"smiles": "Oc1ccccc1",
                                                  "note": ""}])
    v = res.versions
    assert v["cons_filter"] == CONSERVATION_FILTER_VERSION
    assert v["normalization"] == "v43-norm-2"
    assert v["self_rank"] == "v43-selfrank-2"
    assert v["g3b_catalog"] == "v43-g3b-catalog-2"
    assert v["donor_registry"] == "v43-donor-registry-2"
    assert v["completeness_keywords"] == "v43-cons-kw-2"
    assert v["fragment_catalog"] == "v43-cons-frag-1"


# ---------------------------------------------------------------- 开关与 off


def test_policy_switch_validation():
    """开关值域 fail-closed:非法取值装配期拒绝,默认 off = C0。"""
    assert prediction_policy()["novel_conservation_filter"] == "off"
    assert prediction_policy(
        {"novel_conservation_filter": "on"})["novel_conservation_filter"] == "on"
    with pytest.raises(ValueError):
        prediction_policy({"novel_conservation_filter": "ON"})
    with pytest.raises(ValueError):
        prediction_policy({"novel_conservation_filter": True})


def test_apply_novel_off_byte_identical():
    """C0 等价性:开关 off(或缺席)时 _apply_novel 行为逐字节不变。

    以同输入分别用 None/off/on 策略调用:off 与 None 的提案卡与 base
    逐字节一致(无 conservation 键、原始位次);on 时结构不同。
    """
    from pathlib import Path
    import tempfile

    from pathway_v43.services.prediction import (
        ParsedPrediction,
        build_proposed_card,
    )
    from pathway_v43.workflow.nodes import _apply_novel

    state = {
        "run_id": "r-cons", "path_id": "p1", "active_path_id": "p1",
        "active_substrate_identity": cn_identity("Oc1ccccc1"),
    }
    task = {"task_ref": "t1", "model": {}, "policy_version": "x",
            "conditions": {}}
    parsed = ParsedPrediction(
        ok=True, mode="novel_proposal", decision="propose",
        products=[{"smiles": "Oc1ccccc1O", "note": "羟化"},
                  {"smiles": "c1ccccc1", "note": "脱"}])

    out_none, base_none = _apply_novel(state, task, "t1", parsed, 1, {})
    out_off, base_off = _apply_novel(state, task, "t1", parsed, 1, {},
                                     policy={"novel_conservation_filter":
                                             "off"})

    # off ≡ 缺席:逐字节(确定性序列化)一致
    assert json.dumps(base_none, sort_keys=True, ensure_ascii=False) == \
        json.dumps(base_off, sort_keys=True, ensure_ascii=False)
    card_off = base_off["proposed_card"]
    assert [p["position"] for p in card_off["products"]] == [0, 1]
    assert all("conservation" not in p for p in card_off["products"])
    assert "conservation_filter" not in base_off
    # 与历史构造路径一致(legacy 直构对照)
    legacy_products = []
    for pos, p in enumerate(parsed.products):
        smi = p["smiles"]
        legacy_products.append({
            "position": pos, "product_smiles": smi,
            "product_smiles_full": smi,
            "product_identity": cn_identity(smi) or smi,
            "note": p.get("note", ""), "score": 0.0,
            "score_semantics": "model_proposal_qualitative_only_"
                               "no_calibrated_probability",
        })
    legacy_card = build_proposed_card(
        run_id=state["run_id"], path_id=state["path_id"],
        substrate_identity=state["active_substrate_identity"],
        mode="novel_proposal", parsed=parsed, task=task, task_id="t1",
        products=legacy_products)
    assert json.dumps(card_off, sort_keys=True, ensure_ascii=False) == \
        json.dumps(legacy_card, sort_keys=True, ensure_ascii=False)

    # on:同输入结构不同(conservation 块 + 环境块;纯重排无剔除)
    out_on, base_on = _apply_novel(state, task, "t1", parsed, 1, {},
                                   policy={"novel_conservation_filter": "on"})
    assert out_none == out_off == out_on == "proposed"
    assert "conservation_filter" in base_on
    on_card = base_on["proposed_card"]
    assert all("conservation" in p for p in on_card["products"])
    # 纯重排:集合不变(无剔除时)
    assert sorted(p["product_smiles"] for p in on_card["products"]) == \
        sorted(p["product_smiles"] for p in card_off["products"])


def test_apply_novel_on_hold_when_all_excluded():
    """开关 on + 剔空 → held(诚实弃权),结构化拒因随 prediction 落账。"""
    from pathway_v43.services.prediction import ParsedPrediction
    from pathway_v43.workflow.nodes import _apply_novel

    state = {
        "run_id": "r-cons", "path_id": "p1", "active_path_id": "p1",
        "active_substrate_identity": cn_identity("Oc1ccccc1"),
    }
    task = {"task_ref": "t1", "model": {}, "policy_version": "x"}
    parsed = ParsedPrediction(
        ok=True, mode="novel_proposal", decision="propose",
        products=[{"smiles": "Nc1ccccc1", "note": ""},
                  {"smiles": "Oc1ccccc1N", "note": ""}])
    out, base = _apply_novel(state, task, "t1", parsed, 1, {},
                             policy={"novel_conservation_filter": "on"})
    assert out == "held"
    assert base["outcome"] == "held"
    assert "conservation_filter_hold" in base["reason"]
    assert base["conservation_filter"]["status"] == "hold"
    assert base["conservation_filter"]["n_excluded"] == 2
    assert base["conservation_filter"]["hold_reason"] == "all_rejected"
    assert "proposed_card" not in base


# ---------------------------------------------------------------- e2e(假模型)


def _model_with_switch(on: bool, default_novel: str):
    """fake ModelSetup + novel_conservation_filter 开关(进 policy/身份)。"""
    from pathway_v43.adapters.llm_client import resolve_model_setup

    return resolve_model_setup(
        "fake", fake_default_by_mode={"novel_proposal": default_novel},
        policy={"novel_conservation_filter": "on" if on else "off"})


def test_novel_e2e_on_switch_reorders_report(tmp_path):
    """e2e(开关 on):novel 提案经守恒过滤+自排序,报告位次按新序;

    prediction.json 落 conservation_filter 环境块;提案卡产物带
    conservation 结构化判定。off 对照 = 原位次(逐字节 C0 行为)。
    """
    import sys

    sys.path.insert(0, "tests")
    from wf_helpers import (
        CATECHOL,
        evidence,
        load_report,
        run_scripted,
    )

    S = cn_identity(CATECHOL)
    # 儿茶酚底物:0 位编外(脱 O 族,化学矛盾),1 位开环氧化(matched)
    # → on 序 = [开环氧化, 脱氧];off 序 = 原序。
    products = [
        {"smiles": "Oc1ccccc1", "note": "脱氧"},
        {"smiles": "O=C1C=CC(=O)C=C1", "note": "开环氧化"},
    ]
    scripted = {S: [evidence("btR1", "rule_application", CATECHOL,
                             ["O=C1C=CC(=O)C=C1"],
                             match_type="rule_template")]}
    model_on = _model_with_switch(True, novel_response_json(products))
    summary_on, runs_on = run_scripted(
        "consOn", scripted, smiles=CATECHOL, max_depth=1,
        runs_root=tmp_path / "on", model=model_on, max_llm_calls=3,
        max_proposals=1)
    assert summary_on["counts"]["reaction_events"] == 1
    report_on = load_report(runs_on, "consOn")
    ev = report_on["reaction_events"][0]
    # 提案产物按冻结键序进入事件(位次重排)
    assert [p["product_smiles"] for p in ev["products"]] == [
        products[1]["smiles"], products[0]["smiles"]]
    # prediction.json 落结构化环境块
    pred = _read_prediction(runs_on, "consOn")
    cons = pred["conservation_filter"]
    assert cons["status"] == "ok"
    assert cons["n_candidates"] == 2
    assert [r["original_position"] for r in cons["ranked"]] == [1, 0]
    # 提案卡产物带 conservation 块(结构化拒因/降位标记进产物)
    card = pred["proposed_card"]
    assert all("conservation" in p for p in card["products"])
    assert card["products"][0]["conservation"]["tier"] == TIER_PASS

    # off 对照:原位次、无 conservation 块(C0 逐字节行为)
    model_off = _model_with_switch(False, novel_response_json(products))
    summary_off, runs_off = run_scripted(
        "consOff", scripted, smiles=CATECHOL, max_depth=1,
        runs_root=tmp_path / "off", model=model_off, max_llm_calls=3,
        max_proposals=1)
    report_off = load_report(runs_off, "consOff")
    ev_off = report_off["reaction_events"][0]
    assert [p["product_smiles"] for p in ev_off["products"]] == [
        p["smiles"] for p in products]
    pred_off = _read_prediction(runs_off, "consOff")
    assert "conservation_filter" not in pred_off
    assert all("conservation" not in p
               for p in pred_off["proposed_card"]["products"])


def test_novel_e2e_on_switch_all_excluded_hold(tmp_path):
    """e2e(开关 on):全部提案可证明违规 → held(诚实弃权,零事件)。

    off 对照 = 提案照常(其后被既有元素门禁拒,同为零事件不同终态)。
    """
    import sys

    sys.path.insert(0, "tests")
    from wf_helpers import CATECHOL, evidence, load_report, run_scripted

    S = cn_identity(CATECHOL)
    products = [
        {"smiles": "Nc1ccccc1", "note": "加氨"},       # +N 无供体 → 剔除
        {"smiles": "Oc1ccccc1N", "note": "氨基化"},   # +N 无供体 → 剔除
    ]
    scripted = {S: [evidence("btR1", "rule_application", CATECHOL,
                             ["O=C1C=CC(=O)C=C1"],
                             match_type="rule_template")]}
    model_on = _model_with_switch(True, novel_response_json(products))
    summary_on, runs_on = run_scripted(
        "consHold", scripted, smiles=CATECHOL, max_depth=1,
        runs_root=tmp_path / "on", model=model_on, max_llm_calls=3,
        max_proposals=1)
    assert summary_on["counts"]["reaction_events"] == 0
    report_on = load_report(runs_on, "consHold")
    root = report_on["path_instances"][0]
    assert root["status"] in ("awaiting_prediction", "dead_end")
    assert "conservation_filter_hold" in root["status_reason"]
    pred = _read_prediction(runs_on, "consHold")
    assert pred["outcome"] == "held"
    assert pred["conservation_filter"]["status"] == "hold"
    assert pred["conservation_filter"]["n_excluded"] == 2
    assert pred["conservation_filter"]["hold_reason"] == "all_rejected"
    assert "proposed_card" not in pred


def novel_response_json(products: list[dict]) -> str:
    return json.dumps({
        "decision": "propose", "products": products,
        "uncertainty": "high", "reason": "受约束提案",
    }, ensure_ascii=False)


def _read_prediction(runs_root, run_id) -> dict:
    base = runs_root / run_id / "results"
    for d in sorted(base.iterdir()):
        p = d / "prediction.json"
        if p.is_file():
            return json.loads(p.read_text(encoding="utf-8"))["payload"]
    raise AssertionError("prediction.json 未找到")
