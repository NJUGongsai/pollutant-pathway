"""口径 v3(component-aware,全主产物命中)注入测试 — 长期钉住。

任务书:docs/TASK_V43_HIT60_S15_DETERMINISTIC_FIX.md §B;
预注册:reports/phase_s15_hit60/PREREGISTRATION_V3.md §2。

teacher 条件②(假阳性分析义务)四类错配注入 + 已注册边界,全部合成
样例,**不含任何真实金标**。通过判据:全部"错答注入"样本 v3 主分
零命中(0 洗白);全部"完全命中"样本命中;partial/scattered 旗标
逐例正确;any-of 路径(v1/v2 整串与 component_mode)与 v3 的语义差
被显式钉住。
"""

from __future__ import annotations

import pytest

from pathway_v43.exam_v2 import (
    CALIBER_V3_DEF,
    CALIBER_V3_VERSION,
    ScorerV2Error,
    candidate_component_ids,
    component_coverage_profile,
    first_full_coverage_rank,
    first_hit_rank,
    gold_main_component_ids,
)

# 合成分子(与既有 test_exam_v2/test_s1_dev_score 夹具同风格,零真实金标):
A = "CCO"          # 乙醇
B = "CCC"          # 丙烷
C = "c1ccccc1"     # 苯
D = "CC(=O)O"      # 乙酸
X = "C1CCCCC1"     # 环己烷(干扰候选)

GOLD_AB = [A, B]   # 双主产物金标(水解/断裂型)


# ---------------------------------------------------------------- 构造函数

def test_gold_main_component_ids_basic():
    assert gold_main_component_ids([A]) == frozenset({A})
    assert gold_main_component_ids(GOLD_AB) == frozenset({A, B})
    # 点串条目为前瞻泛化(PREREGISTRATION_V3 §1.2):拆分后同集
    assert gold_main_component_ids([f"{A}.{B}"]) == frozenset({A, B})
    assert gold_main_component_ids([A, A]) == frozenset({A})


def test_gold_main_component_ids_fail_closed():
    with pytest.raises(ScorerV2Error):
        gold_main_component_ids(["this_is_NOT_smiles"])


def test_candidate_component_ids():
    assert candidate_component_ids(A) == frozenset({A})
    assert candidate_component_ids(f"{A}.{B}") == frozenset({A, B})
    # 组分顺序无关 + 不可解析组分贡献空
    assert candidate_component_ids(f"{B}.{A}") == frozenset({A, B})
    assert candidate_component_ids(f"junk.{A}") == frozenset({A})
    assert candidate_component_ids("junk") == frozenset()
    assert candidate_component_ids("") == frozenset()


# ------------------------------------------------- 注入四类(条件②核心)

def test_inject_complete_hit():
    """完全命中:全部主产物组分在同一候选 → 主分计,partial 否。"""
    gold = gold_main_component_ids(GOLD_AB)
    rank = first_full_coverage_rank([X, f"{A}.{B}"], gold)
    assert rank == 2
    profile = component_coverage_profile([X, f"{A}.{B}"], gold)
    assert profile["partial"] is False
    assert profile["scattered_full"] is False
    assert profile["hit_with_extra_components"] is False


def test_inject_missing_one_component():
    """缺一组分:只覆盖部分金标组分 → 主分不中、partial 是。

    同时钉住 any-of 修复:v1/v2 整串口径下单组分命中多产物金标之一
    判 rank=1(假阳性),v3 必须判 miss。
    """
    gold = gold_main_component_ids(GOLD_AB)
    # 注入形态 1:单组分候选只含金标之一
    assert first_full_coverage_rank([A], gold) is None
    # 旧口径 any-of 证据(整串 rank=1)
    assert first_hit_rank([A], set(gold)) == 1
    # 旧口径 any-of 证据(component_mode 任一组分命中)
    assert first_hit_rank([f"{A}.{D}"], set(gold), component_mode=True) == 1
    # v3:缺 B → miss + partial
    profile = component_coverage_profile([A], gold)
    assert profile["partial"] is True
    assert profile["n_covered"] == 1
    assert profile["scattered_full"] is False
    # 注入形态 2:多组分候选缺一组分、多一无关组分
    assert first_full_coverage_rank([f"{A}.{D}"], gold) is None
    assert component_coverage_profile([f"{A}.{D}"], gold)["partial"] is True


def test_inject_partial_hit_scattered():
    """部分命中(scattered):金标组分分散在不同候选、无单候选全覆盖。

    any-of 明令禁止的核心形态:两条单组分候选各自命中一个金标产物,
    v1/v2 判 rank=1,component_mode 亦判 rank=1,v3 必须判 miss。
    """
    gold = gold_main_component_ids(GOLD_AB)
    candidates = [A, B]
    assert first_hit_rank(candidates, set(gold)) == 1  # 旧整串 any-of
    assert first_hit_rank(candidates, set(gold),
                          component_mode=True) == 1   # 旧组分 any-of
    assert first_full_coverage_rank(candidates, gold) is None  # v3 miss
    profile = component_coverage_profile(candidates, gold)
    assert profile["partial"] is True
    assert profile["scattered_full"] is True   # 组分全被覆盖但分散
    assert profile["n_covered"] == 2


def test_inject_extra_wrong_component_on_wrong_answer():
    """多一错误组分:错误答追加错误组分不得洗成对答(0 洗白)。"""
    gold_ab = gold_main_component_ids(GOLD_AB)
    # 双金标题:全错候选 + 错误组分
    assert first_full_coverage_rank([f"{C}.{X}"], gold_ab) is None
    assert component_coverage_profile([f"{C}.{X}"], gold_ab)["partial"] is False
    # 单金标题:错误候选 + 两个错误组分
    gold_a = gold_main_component_ids([A])
    assert first_full_coverage_rank([f"{B}.{D}"], gold_a) is None
    assert first_full_coverage_rank([f"{C}.{X}.{D}"], gold_a) is None
    # 错误组分插在金标组分之间同样不救缺组分
    assert first_full_coverage_rank([f"{A}.{X}.{D}"], gold_ab) is None


def test_inject_registered_boundary_superset():
    """已注册边界(PREREGISTRATION_V3 §1.2):候选含全部金标组分
    外加一个额外组分仍判命中(包含语义)——钉住防口径漂移;
    配套 hit_with_extra_components 披露列必须亮起。
    """
    gold = gold_main_component_ids(GOLD_AB)
    candidates = [f"{A}.{B}.{D}"]
    assert first_full_coverage_rank(candidates, gold) == 1
    profile = component_coverage_profile(candidates, gold)
    assert profile["hit_with_extra_components"] is True
    assert profile["partial"] is False


# ---------------------------------------------------------------- 辅助语义

def test_unparseable_occupies_rank():
    """不可解析候选占名次但不命中(与 v2 整串口径一致)。"""
    gold = gold_main_component_ids(GOLD_AB)
    assert first_full_coverage_rank(
        ["this_is_NOT_smiles", f"{A}.{B}"], gold) == 2


def test_single_component_gold_equivalent_to_v2():
    """单组分金标 + 单组分候选:v3 与 v2 整串行为一致(勘误不改此处)。"""
    gold = gold_main_component_ids([A])
    assert first_full_coverage_rank([B, A], gold) == 2
    assert first_hit_rank([B, A], set(gold)) == 2
    # 电荷/立体差异同 cn 口径
    assert first_full_coverage_rank(["C[NH3+]"], gold_main_component_ids(["CN"])) == 1


def test_duplicate_and_order():
    gold = gold_main_component_ids(GOLD_AB)
    assert first_full_coverage_rank([f"{A}.{B}", f"{B}.{A}"], gold) == 1
    assert first_full_coverage_rank([f"{B}.{A}"], gold) == 1


def test_component_coverage_profile_miss():
    gold = gold_main_component_ids(GOLD_AB)
    profile = component_coverage_profile([C, X], gold)
    assert profile["rank"] is None
    assert profile["partial"] is False
    assert profile["n_covered"] == 0
    assert profile["n_gold_components"] == 2


def test_version_constants():
    assert CALIBER_V3_VERSION == "v43-exam-caliber-3"
    assert "全主产物命中" in CALIBER_V3_DEF
