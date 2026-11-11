"""单元测试：确定性完全矿化与中心碳代谢终点判定器 (ppv1-mineralization-sink-v1)。"""

import pytest
from pathway_v43.pollutant.mineralization_sink import (
    classify_mineralization_sink,
    CENTRAL_CARBON_SINK_CANONICAL_SPECS,
    MINERALIZATION_POLICY_VERSION,
)


def test_policy_version():
    assert MINERALIZATION_POLICY_VERSION == "ppv1-mineralization-sink-v1"


# =========================================================================
# 正控测试 (Positive Controls)
# =========================================================================

def test_a0_noncarbon_inorganic():
    """A0 档：无碳无机物一律闭合为终点。"""
    species = [
        "[Cl-]", "[Br-]", "[F-]", "[I-]",
        "O", "[OH-]",  # H2O / OH-
        "N", "[NH4+]",  # NH3 / NH4+
        "O=S(=O)([O-])[O-]", "OS(=O)(=O)O",  # SO4^2- / H2SO4
        "S", "[SH-]",  # H2S / HS-
        "OP(=O)(O)O", "O=P([O-])([O-])[O-]",  # PO4^3- / H3PO4
        "[N+](=O)([O-])[O-]", "O=N[O-]",  # NO3- / NO2-
        "O=O",  # O2
    ]
    for smi in species:
        res = classify_mineralization_sink(smi)
        assert res.is_terminal_sink, f"Expected terminal sink for {smi}"
        assert res.sink_tier == "A0_noncarbon_inorganic", f"Wrong tier for {smi}"
        assert not res.track_branch
        assert res.carbon_count == 0


def test_a_inorganic_carbon():
    """A 档：直接无机碳 (CO2 与碳酸/碳酸氢根/碳酸根) 闭合为终点。"""
    species = [
        "O=C=O",  # CO2
        "O=C(O)O",  # H2CO3
        "O=C([O-])O",  # HCO3-
        "[O-]C(=O)[O-]",  # CO3^2-
    ]
    for smi in species:
        res = classify_mineralization_sink(smi)
        assert res.is_terminal_sink, f"Expected terminal sink for {smi}"
        assert res.sink_tier == "A_inorganic_carbon", f"Wrong tier for {smi}"
        assert not res.track_branch
        assert res.carbon_count == 1


def test_b_central_carbon_sink_all_23():
    """B 档：23 个中心碳代谢核心白名单分子全覆盖放行。"""
    for name, smi in CENTRAL_CARBON_SINK_CANONICAL_SPECS.items():
        res = classify_mineralization_sink(smi)
        assert res.is_terminal_sink, f"Expected terminal sink for {name}: {smi}"
        assert res.sink_tier == "B_central_carbon_sink", f"Wrong tier for {name}: {smi}"
        assert not res.track_branch


def test_b_central_carbon_sink_charged_variants():
    """B 档：去质子化/离子态能正确归一放行。"""
    variants = [
        ("pyruvate_anion", "CC(=O)C([O-])=O"),
        ("acetate_anion", "CC(=O)[O-]"),
        ("succinate_dianion", "[O-]C(=O)CCC(=O)[O-]"),
        ("fumarate_dianion", "[O-]C(=O)/C=C/C(=O)[O-]"),
        ("fumarate_flat", "O=C(O)C=CC(=O)O"),  # 未指定立体的富马酸放行
        ("malate_dianion", "[O-]C(=O)CC(O)C(=O)[O-]"),
        ("glyoxylate_anion", "O=CC(=O)[O-]"),
        ("oxaloacetate_dianion", "[O-]C(=O)CC(=O)C(=O)[O-]"),
    ]
    for label, smi in variants:
        res = classify_mineralization_sink(smi)
        assert res.is_terminal_sink, f"Expected terminal sink for {label}: {smi}"
        assert res.sink_tier == "B_central_carbon_sink"
        assert not res.track_branch


def test_currency_cofactors_as_coproduct():
    """内源货币辅因子仅在 role == 'coproduct' 时排除。"""
    cofactors = [
        "BAWFJGJZGIEFAR",  # NAD+
        "NC(=O)C1=CN(C=CC1)C1OC(COP(=O)(O)OP(=O)(O)OCC2OC(n3cnc4c(N)ncnc34)C(O)C2O)C(O)C1O",  # NADH
        "Nc1ncnc2c1ncn2C1OC(COP(=O)(O)OP(=O)(O)O)C(O)C1O",  # ADP
        "CC(C)(COP(=O)(O)OP(=O)(O)OCC1OC(n2cnc3c(N)ncnc32)C(O)C1OP(=O)(O)O)C(O)C(=O)NCCC(=O)NCCS",  # free CoA-SH
    ]
    for smi in cofactors[1:]:
        res = classify_mineralization_sink(smi, role="coproduct")
        assert res.is_terminal_sink, f"Expected cofactor exclusion for {smi}"
        assert res.sink_tier == "ENDOGENOUS_CURRENCY_COFACTOR"
        assert not res.track_branch

    # 但如果 role == 'principal_product'，则绝不能当作辅因子排除！
    for smi in cofactors[1:]:
        res_princ = classify_mineralization_sink(smi, role="principal_product")
        assert res_princ.sink_tier != "ENDOGENOUS_CURRENCY_COFACTOR"


# =========================================================================
# 负控测试 (Negative Controls - 严禁误判为终点)
# =========================================================================

def test_c1_organic_negatives():
    """一碳有机/还原态物种严禁停机，必须继续氧化到 CO2。"""
    c1_negatives = [
        ("methanol", "CO"),
        ("formaldehyde", "C=O"),
        ("formate", "O=CO"),
        ("formate_anion", "O=C[O-]"),
        ("carbon_monoxide", "[C-]#[O+]"),
        ("cyanide", "C#N"),
        ("cyanide_anion", "[C-]#N"),
        ("urea", "NC(N)=O"),
        ("methylamine", "CN"),
        ("methane", "C"),
        ("carbon_disulfide", "S=C=S"),
        ("formamide", "NC=O"),
    ]
    for label, smi in c1_negatives:
        res = classify_mineralization_sink(smi)
        assert not res.is_terminal_sink, f"C1 species {label} must not be terminal sink!"
        assert res.track_branch, f"C1 species {label} must be tracked!"
        assert res.reason == "c1_organic_must_oxidize_to_co2"


def test_acetaldehyde_negative():
    """乙醛 CC=O 严禁停机，必须继续氧化至乙酸或乙酰-CoA。"""
    res = classify_mineralization_sink("CC=O")
    assert not res.is_terminal_sink, "Acetaldehyde must NOT be terminal sink!"
    assert res.track_branch


def test_cis_maleate_negative():
    """显式顺式马来酸严禁停机，必须异构化或水合。"""
    res = classify_mineralization_sink("O=C(O)/C=C\\C(=O)O")
    assert not res.is_terminal_sink, "cis-maleate must NOT be terminal sink!"
    assert res.reason == "cis_maleate_must_isomerize_to_fumarate"
    assert res.track_branch


def test_trans_aconitate_negative():
    """显式反乌头酸严禁停机，必须异构化为顺乌头酸。"""
    res = classify_mineralization_sink("O=C(O)C/C(=C/C(=O)O)C(=O)O")
    assert not res.is_terminal_sink, "trans-aconitate must NOT be terminal sink!"
    assert res.reason == "trans_aconitate_must_isomerize_to_cis"
    assert res.track_branch


def test_xenobiotic_negatives():
    """外源毒害基团（卤素/硝基/膦酸/磺酸等）一票否决。"""
    negatives = [
        ("fluoroacetate", "FCC(=O)O"),
        ("2_chlorosuccinate", "O=C(O)CC(Cl)C(=O)O"),
        ("bromoacetate", "BrCC(=O)O"),
        ("4_nitrocatechol", "Oc1ccc([N+](=O)[O-])cc1O"),
        ("methanesulfonic_acid", "CS(=O)(=O)O"),
        ("methylphosphonate", "CP(=O)(O)O"),
        ("dimethyl_phosphorothioate", "COP(=S)(OC)O"),
    ]
    for label, smi in negatives:
        res = classify_mineralization_sink(smi)
        assert not res.is_terminal_sink, f"{label} must NOT be terminal sink!"
        assert res.track_branch
        assert "xenobiotic" in res.reason


def test_aromatic_funnel_intermediates_negatives():
    """未开环的芳环漏斗中间体与开环中段未裂解物严禁停机。"""
    negatives = [
        ("catechol", "Oc1ccccc1O"),
        ("protocatechuate", "Oc1ccc(C(=O)O)cc1O"),
        ("gentisate", "Oc1ccc(O)c(C(=O)O)c1"),
        ("benzoate", "O=C(O)c1ccccc1"),
        ("salicylate", "Oc1ccccc1C(=O)O"),
        ("phenylacetate", "O=C(O)Cc1ccccc1"),
        ("cis_cis_muconate", "O=C(O)/C=C\\C=C/C(=O)O"),
        ("3_oxoadipate", "O=C(O)CC(=O)CCC(=O)O"),
        ("benzoyl_coa", "O=C(c1ccccc1)SCCNC(=O)CCNC(=O)C(O)C(C)(C)COP(=O)(O)OP(=O)(O)OCC1OC(n2cnc3c(N)ncnc32)C(O)C1OP(=O)(O)O"),
    ]
    for label, smi in negatives:
        res = classify_mineralization_sink(smi)
        assert not res.is_terminal_sink, f"Funnel intermediate {label} must NOT be terminal sink!"
        assert res.track_branch


def test_free_nucleobase_guard():
    """游离碱基（腺嘌呤、尿嘧啶等）绝不能误当作货币辅因子排除！"""
    bases = [
        ("adenine", "Nc1ncnc2[nH]cnc12"),
        ("uracil", "O=c1cc[nH]c(=O)[nH]1"),
        ("guanine", "Nc1nc2c(c(=O)[nH]1)[nH]cn2"),
        ("cytosine", "Nc1cc[nH]c(=O)n1"),
    ]
    for label, smi in bases:
        res = classify_mineralization_sink(smi, role="coproduct")
        assert not res.is_terminal_sink, f"Free base {label} must NOT be excluded as cofactor!"
        assert res.track_branch


# =========================================================================
# 禁祖先倒车 (Non-Backtracking B=1) 选择器单元测试
# =========================================================================

from pathway_v43.pollutant.mineralization_sink import (
    check_event_backtracking,
    select_event_non_backtracking,
)
from pathway_v43.pollutant.chemstate import strict_identity_of


def test_non_backtracking_positive_control():
    """正控：Event #1 为父子一步逆反应 (B -> A)，Event #2 为前进反应 (B -> C)，自动顺延选用 #2。"""
    smi_a = "O=C(O)c1ccccc1"  # 苯甲酸 (祖先 A)
    smi_b = "Oc1ccccc1O"      # 儿茶酚 (当前底物 B)
    smi_c = "O=C(O)/C=C\\C=C/C(=O)O"  # 粘康酸 (前进中间体 C)

    sid_a = strict_identity_of(smi_a)
    sid_b = strict_identity_of(smi_b)
    history = (sid_a, sid_b)

    ev1 = {
        "event_id": "ev_001_reverse",
        "rank": 1,
        "principal_products": [{"smiles": smi_a, "role": "principal_product"}],
        "coproducts": [],
    }
    ev2 = {
        "event_id": "ev_002_forward",
        "rank": 2,
        "principal_products": [{"smiles": smi_c, "role": "principal_product"}],
        "coproducts": [],
    }

    # 1. Non-Backtracking 策略：跳过 ev1，选用 ev2
    res_nb = select_event_non_backtracking([ev1, ev2], history, policy="non_backtracking_b1")
    assert res_nb.status == "SELECTED"
    assert res_nb.selected_rank == 2
    assert res_nb.selected_event["event_id"] == "ev_002_forward"
    assert len(res_nb.skipped_events) == 1
    assert res_nb.skipped_events[0]["rank"] == 1
    assert res_nb.skipped_events[0]["collisions"][0]["lag"] == 2
    assert res_nb.skipped_events[0]["collisions"][0]["strict_id"] == sid_a

    # 2. Naive B=1 策略：盲取 ev1
    res_naive = select_event_non_backtracking([ev1, ev2], history, policy="naive_b1")
    assert res_naive.status == "SELECTED"
    assert res_naive.selected_rank == 1
    assert res_naive.selected_event["event_id"] == "ev_001_reverse"
    assert len(res_naive.skipped_events) == 0


def test_non_backtracking_negative_control_all_backtrack():
    """负控：全部候选事件均倒车回祖先时，诚实返回 ALL_CANDIDATES_BACKTRACK。"""
    smi_root = "c1ccccc1"     # 苯 (根节点 R)
    smi_a = "Oc1ccccc1"       # 苯酚 (中间体 A)
    smi_b = "Oc1ccccc1O"      # 儿茶酚 (当前底物 B)

    sid_root = strict_identity_of(smi_root)
    sid_a = strict_identity_of(smi_a)
    sid_b = strict_identity_of(smi_b)
    history = (sid_root, sid_a, sid_b)

    ev1 = {
        "event_id": "ev_back_a",
        "rank": 1,
        "principal_products": [{"smiles": smi_a, "role": "principal_product"}],
        "coproducts": [],
    }
    ev2 = {
        "event_id": "ev_back_root",
        "rank": 2,
        "principal_products": [{"smiles": smi_root, "role": "principal_product"}],
        "coproducts": [],
    }

    res = select_event_non_backtracking([ev1, ev2], history, policy="non_backtracking_b1")
    assert res.status == "ALL_CANDIDATES_BACKTRACK"
    assert res.selected_event is None
    assert len(res.skipped_events) == 2
    assert res.skipped_events[0]["collisions"][0]["lag"] == 2  # B -> A (lag 2)
    assert res.skipped_events[1]["collisions"][0]["lag"] == 3  # B -> root (lag 3)


def test_non_backtracking_cleavage_multi_product_collision():
    """裂解多含碳产物分支场景下的祖先碰撞检测。"""
    smi_a = "O=C(O)c1ccccc1"  # 祖先 A
    smi_b = "CC(=O)C(=O)O"    # 终点 B (丙酮酸)
    smi_x = "Oc1ccccc1O"      # 当前底物 X

    sid_a = strict_identity_of(smi_a)
    sid_x = strict_identity_of(smi_x)
    history = (sid_a, sid_x)

    # 裂解产物含一个终点分子 (丙酮酸) + 一个祖先非终点分子 (苯甲酸)
    ev_cleavage = {
        "event_id": "ev_cleave_collision",
        "rank": 1,
        "principal_products": [{"smiles": smi_a, "role": "principal_product"}],
        "coproducts": [{"smiles": smi_b, "role": "coproduct"}],
    }

    chk = check_event_backtracking(ev_cleavage, history)
    assert chk.has_backtrack
    assert len(chk.collisions) == 1
    assert chk.collisions[0]["strict_id"] == sid_a
    assert chk.collisions[0]["lag"] == 2


def test_non_backtracking_terminal_sink_does_not_collide():
    """产物全为终点矿化物或货币辅因子时，不触发倒车碰撞。"""
    smi_x = "Oc1ccccc1O"
    sid_x = strict_identity_of(smi_x)
    history = (sid_x,)

    # 产物全为终点池分子 (CO2 + 琥珀酸)
    ev_mineralized = {
        "event_id": "ev_sink",
        "rank": 1,
        "principal_products": [{"smiles": "O=C=O", "role": "principal_product"}],
        "coproducts": [{"smiles": "O=C(O)CCC(=O)O", "role": "coproduct"}],
    }

    chk = check_event_backtracking(ev_mineralized, history)
    assert not chk.has_backtrack
    assert len(chk.collisions) == 0

