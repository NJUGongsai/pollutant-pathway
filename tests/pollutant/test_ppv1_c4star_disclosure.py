"""§5.2 C4*「按声明的非氢元素预算」合成验收(2026-11-05)。

规则权威 = ``docs/reviews/codex/CODEX_V5_COPRODUCT_TRACEABILITY_REVIEW_
2026-11-05.md`` 第一节(Codex 代 mimo,CC 采信);转录 = v5 预注册 v3 §5.2;
实施书 = ``docs/tasks/active/TASK_T4C2_C4STAR_DISCLOSURE_2026-11-05.md`` §2.3。

纪律:
- 全部夹具为合成规则级通用分子,**零金标、零真实 qid、零模型**;
- 本轴只作披露,永不进命中/位次/主成绩(本文件另一测试专门证明
  「披露轴开关不影响命中」);
- 不把 traceable 写成「来源已核」:只表示「按声明的非氢预算覆盖」;
- 不因未执行强制 unknown(声明式 coproduct 参与声明预算;执行覆盖
  独立保留 ``not_verified``)。

覆盖实施书 §2.3 的 11 条合成验收 + 披露轴开关不变性 + 判分层聚合。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rdkit import RDLogger  # noqa: E402

RDLogger.DisableLog("rdApp.*")

from pathway_v43.pollutant.evaluation import (  # noqa: E402
    CRITERIA_V5_C4STAR_REASON_AMBIGUOUS_DUPLICATE,
    CRITERIA_V5_C4STAR_REASON_COPRODUCT_HYDROGEN_ONLY,
    CRITERIA_V5_C4STAR_REASON_MANIFEST_PARTIAL,
    CRITERIA_V5_C4STAR_REASON_MANIFEST_UNKNOWN,
    CRITERIA_V5_C4STAR_REASON_PRINCIPAL_OVER_BUDGET,
    CRITERIA_V5_C4STAR_REASON_ROLE_PARTITION_INCOMPLETE,
    CRITERIA_V5_C4STAR_REASON_SIDE_UNDETERMINED,
    CRITERIA_V5_C4STAR_REASON_UNKNOWN_COEFFICIENT,
    CRITERIA_V5_C4STAR_REASON_UNQUANTIFIABLE_GROUP,
    CRITERIA_V5_C4STAR_REASON_STRUCTURE_UNPARSEABLE,
    CRITERIA_V5_C4STAR_RULE_VERSION,
    CRITERIA_V5_C4STAR_STATUSES,
    CRITERIA_V5_C4STAR_STATUS_NOT_APPLICABLE,
    CRITERIA_V5_C4STAR_STATUS_TRACEABLE,
    CRITERIA_V5_C4STAR_STATUS_UNKNOWN,
    CRITERIA_V5_C4STAR_STATUS_UNTRACEABLE,
    criteria_c4star_non_hydrogen_budget,
)
from pathway_v43.pollutant.s5b_scoring import (  # noqa: E402
    _role_bound_hit_caliber_block,
)

# ---- 通用分子(零金标):元素向量见注释 ----
GLYCEROL = "OCC(O)CO"        # C3 O3
ACETALDEHYDE = "CC=O"        # C2 O1
METHANOL = "CO"              # C1 O1
CO2 = "O=C=O"                # C1 O2
WATER = "O"                  # O1
AMMONIA = "N"                # N1
PHOSPHORIC = "OP(=O)(O)O"    # P1 O4
HYDROGEN = "[H][H]"          # 无非氢原子
ETHANE = "CC"                # C2
ETHENE = "C=C"               # C2
SODIUM_ACETATE = "CC(=O)[O-].[Na+]"   # C2 O2 Na1
WILDCARD = "*C=O"            # 通配基团(不可定量)

STRUCTURES = {
    "s-gly": GLYCEROL,
    "s-ald": ACETALDEHYDE,
    "s-meoh": METHANOL,
    "s-co2": CO2,
    "s-w": WATER,
    "s-nh3": AMMONIA,
    "s-pi": PHOSPHORIC,
    "s-h2": HYDROGEN,
    "s-eth": ETHANE,
    "s-ene": ETHENE,
    "s-naac": SODIUM_ACETATE,
    "s-wild": WILDCARD,
}


def _entry(ref: str, side: str, role, coefficient, status: str, *,
           parallel: bool = False, merged_from: list[str] | None = None,
           seq: int = 1) -> dict:
    return {
        "state_ref": ref, "side": side, "role": role,
        "coefficient": coefficient, "coefficient_status": status,
        "parallel_contribution": parallel,
        "merged_from": list(merged_from or []),
        "entry_id": f"pe-{seq}",
    }


def _budget(entries: list[dict], *,
            participant_list_status: str | None = "declared_complete",
            ambiguous: bool = False,
            structures: dict[str, str] | None = None) -> dict:
    return criteria_c4star_non_hydrogen_budget(
        entries,
        structure_by_state_ref=(STRUCTURES if structures is None
                                else structures),
        participant_list_status=participant_list_status,
        ambiguous_participants=ambiguous)


# ---------------------------------------------------------------- 版本与枚举


def test_c4star_rule_identity_and_enums() -> None:
    assert CRITERIA_V5_C4STAR_RULE_VERSION == (
        "c4star-declared-non-hydrogen-budget-1")
    assert set(CRITERIA_V5_C4STAR_STATUSES) == {
        "traceable", "untraceable", "unknown", "not_applicable"}


# ---------------------------------------------------------------- ① 联合共产物


def test_joint_coproduct_consumption_is_never_reused_per_coproduct() -> None:
    """① 两个共产物单看都不超剩余池,联合后超 ⇒ untraceable。

    R=甘油 C3O3,P=乙醛 C2O1 ⇒ 剩余 C1O2;水(O1)单看不超、
    CO₂(C1O2)单看恰好,联合 C=C1O3 ⇒ O 超 1 ⇒ untraceable。
    """
    result = _budget([
        _entry("s-gly", "reactant", "primary_substrate", "1", "known"),
        _entry("s-ald", "product", "principal_product", "1", "known"),
        _entry("s-w", "product", "coproduct", "1", "known", seq=2),
        _entry("s-co2", "product", "coproduct", "1", "known", seq=3),
    ])
    assert result["status"] == CRITERIA_V5_C4STAR_STATUS_UNTRACEABLE
    assert result["budget_account_computable"] is True
    assert result["dp_by_element"] == {"C": "0", "O": "0"}
    assert result["dt_by_element"] == {"C": "0", "O": "1"}
    assert result["dc_by_element"] == {"C": "0", "O": "1"}
    assert result["surplus_by_element"] == {"C": "0", "O": "-1"}
    assert result["n_elements_dt_positive"] == 1


# ---------------------------------------------------------------- ② 多主产物


def test_multiple_principal_products_jointly_consume_budget() -> None:
    """② 全部主产物先共同占用预算,共产物只能用剩下的。

    R=甘油 C3O3;P=乙醛 C2O1 + 甲醇 C1O1 ⇒ 剩余仅 O1;
    CO₂(C1O2)⇒ C/O 均超 ⇒ untraceable(只扣一个主产物会误判可覆盖)。
    """
    result = _budget([
        _entry("s-gly", "reactant", "primary_substrate", "1", "known"),
        _entry("s-ald", "product", "principal_product", "1", "known"),
        _entry("s-meoh", "product", "principal_product", "1", "known",
               seq=2),
        _entry("s-co2", "product", "coproduct", "1", "known", seq=3),
    ])
    assert result["status"] == CRITERIA_V5_C4STAR_STATUS_UNTRACEABLE
    assert result["dt_by_element"] == {"C": "1", "O": "1"}
    assert result["counts"]["n_principal_entries"] == 2


# ---------------------------------------------------------------- ③ 系数


def test_positive_fraction_coefficients_are_exact_rationals() -> None:
    """③a 正分数系数(3/2)按 Fraction 精确计算 ⇒ 预算恰好覆盖。"""
    result = _budget([
        _entry("s-gly", "reactant", "primary_substrate", "3/2", "known"),
        _entry("s-ald", "product", "principal_product", "3/2", "known"),
        _entry("s-co2", "product", "coproduct", "3/2", "known", seq=2),
    ])
    assert result["status"] == CRITERIA_V5_C4STAR_STATUS_TRACEABLE
    # R=C4.5 O4.5;P=C3 O1.5;C=C1.5 O3 ⇒ 剩余 C0 O0(恰好覆盖)
    assert result["dp_by_element"] == {"C": "0", "O": "0"}
    assert result["dt_by_element"] == {"C": "0", "O": "0"}
    assert result["surplus_by_element"] == {"C": "0", "O": "0"}


def test_unknown_coefficient_is_never_defaulted_to_one() -> None:
    """③b 非氢系数 unknown ⇒ 账不可算 ⇒ unknown(不补 1、不拟合)。"""
    defaulted = _budget([
        _entry("s-gly", "reactant", "primary_substrate", "1", "known"),
        _entry("s-ald", "product", "principal_product", "1", "known"),
        _entry("s-co2", "product", "coproduct", "1", "known", seq=2),
    ])
    unknown = _budget([
        _entry("s-gly", "reactant", "primary_substrate", "1", "known"),
        _entry("s-ald", "product", "principal_product", "1", "known"),
        _entry("s-co2", "product", "coproduct", None, "unknown", seq=2),
    ])
    assert defaulted["status"] == CRITERIA_V5_C4STAR_STATUS_TRACEABLE
    assert unknown["status"] == CRITERIA_V5_C4STAR_STATUS_UNKNOWN
    assert CRITERIA_V5_C4STAR_REASON_UNKNOWN_COEFFICIENT in \
        unknown["reason_codes"]
    assert unknown["budget_account_computable"] is False
    assert unknown["dp_by_element"] is None
    assert unknown["counts"]["n_unknown_coefficient_non_hydrogen_entries"] \
        == 1


def test_fraction_coefficient_below_one_can_show_principal_over_budget() -> \
        None:
    """③c 1/2 系数使主产物自身超预算 ⇒ unknown(Dp≠0),Dt 仍报告。"""
    result = _budget([
        _entry("s-gly", "reactant", "primary_substrate", "1/2", "known"),
        _entry("s-ald", "product", "principal_product", "1", "known"),
        _entry("s-w", "product", "coproduct", "1", "known", seq=2),
    ])
    assert result["status"] == CRITERIA_V5_C4STAR_STATUS_UNKNOWN
    assert result["reason_codes"] == [
        CRITERIA_V5_C4STAR_REASON_PRINCIPAL_OVER_BUDGET]
    # R=C1.5 O1.5;P=C2 O1 ⇒ Dp:C0.5,O0;Dt:C0.5,O0.5(共产物再占 1 个 O)
    assert result["dp_by_element"] == {"C": "1/2", "O": "0"}
    assert result["dt_by_element"] == {"C": "1/2", "O": "1/2"}


# ---------------------------------------------------------------- ④ 归并/歧义


def test_explicit_parallel_duplicates_are_summed_once() -> None:
    """④a 明确并列(parallel_contribution=True + known)求和一次。"""
    merged = _budget([
        _entry("s-gly", "reactant", "primary_substrate", "1", "known"),
        _entry("s-ald", "product", "principal_product", "1", "known"),
        _entry("s-co2", "product", "coproduct", "1", "known",
               parallel=True, seq=2),
        _entry("s-co2", "product", "coproduct", "1", "known",
               parallel=True, seq=3),
    ])
    single = _budget([
        _entry("s-gly", "reactant", "primary_substrate", "1", "known"),
        _entry("s-ald", "product", "principal_product", "1", "known"),
        _entry("s-co2", "product", "coproduct", "1", "known", seq=2),
    ])
    # 两条 CO₂ 合计 C2O4 > 剩余 C1O2 ⇒ untraceable;单条恰好覆盖。
    assert single["status"] == CRITERIA_V5_C4STAR_STATUS_TRACEABLE
    assert merged["status"] == CRITERIA_V5_C4STAR_STATUS_UNTRACEABLE
    assert merged["counts"]["n_merged_measurement_entries"] == 1


def test_already_merged_coefficient_is_used_once_not_per_merged_from() -> \
        None:
    """④b 已归并系数(merged_from 两条)只用一次,不能再乘条数。"""
    # 剩余 C1O2,C=1×CO₂ 恰好覆盖;若错乘 merged_from 条数(2)⇒ C2O4 超
    result = _budget([
        _entry("s-gly", "reactant", "primary_substrate", "1", "known"),
        _entry("s-ald", "product", "principal_product", "1", "known"),
        _entry("s-co2", "product", "coproduct", "1", "known",
               merged_from=["pe-a", "pe-b"], seq=2),
    ])
    assert result["status"] == CRITERIA_V5_C4STAR_STATUS_TRACEABLE
    assert result["counts"]["n_merged_measurement_entries"] == 1


def test_ambiguous_duplicate_measurement_is_unknown() -> None:
    """④c 重复计量含义不清(无并列声明)⇒ unknown,不静默去重/求和。"""
    result = _budget([
        _entry("s-gly", "reactant", "primary_substrate", "1", "known"),
        _entry("s-ald", "product", "principal_product", "1", "known"),
        _entry("s-w", "product", "coproduct", "1", "known", seq=2),
        _entry("s-w", "product", "coproduct", "1", "known", seq=3),
    ])
    assert result["status"] == CRITERIA_V5_C4STAR_STATUS_UNKNOWN
    assert CRITERIA_V5_C4STAR_REASON_AMBIGUOUS_DUPLICATE in \
        result["reason_codes"]
    assert result["budget_account_computable"] is False
    # hypothesis 层已标记 ambiguous 时同样 unknown
    flagged = _budget([
        _entry("s-gly", "reactant", "primary_substrate", "1", "known"),
        _entry("s-ald", "product", "principal_product", "1", "known"),
        _entry("s-w", "product", "coproduct", "1", "known", seq=2),
    ], ambiguous=True)
    assert flagged["status"] == CRITERIA_V5_C4STAR_STATUS_UNKNOWN
    assert CRITERIA_V5_C4STAR_REASON_AMBIGUOUS_DUPLICATE in \
        flagged["reason_codes"]


# ---------------------------------------------------------------- ⑤ 无共产物


def test_no_coproduct_with_complete_manifest_is_not_applicable() -> None:
    """⑤ 清单完整 + 角色分区明确 + 确无 coproduct ⇒ not_applicable。"""
    result = _budget([
        _entry("s-gly", "reactant", "primary_substrate", "1", "known"),
        _entry("s-ald", "product", "principal_product", "1", "known"),
    ])
    assert result["status"] == CRITERIA_V5_C4STAR_STATUS_NOT_APPLICABLE
    assert result["reason_codes"] == ["no_coproduct_participant"]
    assert result["dp_by_element"] is None  # 不冒充已完成计量运算
    assert result["counts"]["n_coproduct_entries"] == 0


def test_no_coproduct_but_partial_manifest_is_not_not_applicable() -> None:
    """⑤b 清单 partial ⇒ 不得冒充 not_applicable(C0 兜底:unknown)。"""
    result = _budget([
        _entry("s-gly", "reactant", "primary_substrate", "1", "known"),
        _entry("s-ald", "product", "principal_product", "1", "known"),
    ], participant_list_status="partial")
    assert result["status"] == CRITERIA_V5_C4STAR_STATUS_UNKNOWN
    assert CRITERIA_V5_C4STAR_REASON_MANIFEST_PARTIAL in \
        result["reason_codes"]
    missing = _budget([
        _entry("s-gly", "reactant", "primary_substrate", "1", "known"),
        _entry("s-ald", "product", "principal_product", "1", "known"),
    ], participant_list_status=None)
    assert missing["status"] == CRITERIA_V5_C4STAR_STATUS_UNKNOWN
    assert CRITERIA_V5_C4STAR_REASON_MANIFEST_UNKNOWN in \
        missing["reason_codes"]


# ---------------------------------------------------------------- ⑥ 角色分区


@pytest.mark.parametrize("role", [None, "", "unknown", "cosubstrate",
                                  "intermediate"])
def test_unpartitioned_product_role_is_unknown(role) -> None:
    """⑥ 产物角色缺失或既非 principal 也非 coproduct ⇒ unknown。"""
    result = _budget([
        _entry("s-gly", "reactant", "primary_substrate", "1", "known"),
        _entry("s-ald", "product", "principal_product", "1", "known"),
        _entry("s-w", "product", role, "1", "known", seq=2),
    ])
    assert result["status"] == CRITERIA_V5_C4STAR_STATUS_UNKNOWN
    assert CRITERIA_V5_C4STAR_REASON_ROLE_PARTITION_INCOMPLETE in \
        result["reason_codes"]
    # 有未分角色产物时不得因"无显式 coproduct"输出 not_applicable
    no_coproduct = _budget([
        _entry("s-gly", "reactant", "primary_substrate", "1", "known"),
        _entry("s-ald", "product", role, "1", "known"),
    ])
    assert no_coproduct["status"] != \
        CRITERIA_V5_C4STAR_STATUS_NOT_APPLICABLE


def test_side_undetermined_is_unknown() -> None:
    """⑥b side 不定 ⇒ unknown(side_undetermined)。"""
    result = _budget([
        _entry("s-gly", "reactant", "primary_substrate", "1", "known"),
        _entry("s-ald", "either", "principal_product", "1", "known"),
        _entry("s-w", "product", "coproduct", "1", "known", seq=2),
    ])
    assert result["status"] == CRITERIA_V5_C4STAR_STATUS_UNKNOWN
    assert CRITERIA_V5_C4STAR_REASON_SIDE_UNDETERMINED in \
        result["reason_codes"]


# ---------------------------------------------------------------- ⑦ 纯氢共产物


def test_pure_hydrogen_coproduct_is_unknown_but_account_is_kept() -> None:
    """⑦ 纯氢共产物 ⇒ unknown(无可核对象),但保留可算 Dp/Dt/Dc。"""
    result = _budget([
        _entry("s-gly", "reactant", "primary_substrate", "1", "known"),
        _entry("s-ald", "product", "principal_product", "1", "known"),
        _entry("s-h2", "product", "coproduct", "1", "known", seq=2),
    ])
    assert result["status"] == CRITERIA_V5_C4STAR_STATUS_UNKNOWN
    assert CRITERIA_V5_C4STAR_REASON_COPRODUCT_HYDROGEN_ONLY in \
        result["reason_codes"]
    assert result["budget_account_computable"] is True
    assert result["dp_by_element"] == {"C": "0", "O": "0"}
    assert result["counts"]["n_hydrogen_only_coproduct_entries"] == 1


def test_mixed_hydrogen_coproduct_keeps_computable_partial_account() -> None:
    """⑦b 混合(纯氢 + 有非氢对象)⇒ 仍 unknown,但可检部分账照报。"""
    result = _budget([
        _entry("s-gly", "reactant", "primary_substrate", "1", "known"),
        _entry("s-ald", "product", "principal_product", "1", "known"),
        _entry("s-w", "product", "coproduct", "1", "known", seq=2),
        _entry("s-h2", "product", "coproduct", "1", "known", seq=3),
    ])
    assert result["status"] == CRITERIA_V5_C4STAR_STATUS_UNKNOWN
    assert CRITERIA_V5_C4STAR_REASON_COPRODUCT_HYDROGEN_ONLY in \
        result["reason_codes"]
    # 剩余 C1O2;水 C=O1 ⇒ 不超
    assert result["dt_by_element"] == {"C": "0", "O": "0"}
    assert result["surplus_by_element"] == {"C": "1", "O": "1"}


def test_pure_hydrogen_reactant_unknown_coefficient_does_not_block() -> None:
    """⑦c 纯氢反应物的未知系数不影响非氢向量(两侧对称豁免)。"""
    result = _budget([
        _entry("s-gly", "reactant", "primary_substrate", "1", "known"),
        _entry("s-h2", "reactant", "cosubstrate", None, "unknown", seq=2),
        _entry("s-ald", "product", "principal_product", "1", "known"),
        _entry("s-w", "product", "coproduct", "1", "known", seq=3),
    ])
    assert result["status"] == CRITERIA_V5_C4STAR_STATUS_TRACEABLE
    assert CRITERIA_V5_C4STAR_REASON_UNKNOWN_COEFFICIENT not in \
        result["reason_codes"]
    assert result["counts"]["n_hydrogen_only_reactant_entries"] == 1


# ---------------------------------------------------------------- ⑧ Dp/Dt/Dc


def test_dp_dt_dc_are_listed_separately_with_positive_surplus() -> None:
    """⑧ 正剩余:Dp=Dt=Dc=0 且余量>0,不得称完整配平。"""
    result = _budget([
        _entry("s-gly", "reactant", "primary_substrate", "1", "known"),
        _entry("s-ald", "product", "principal_product", "1", "known"),
        _entry("s-w", "product", "coproduct", "1", "known", seq=2),
    ])
    assert result["status"] == CRITERIA_V5_C4STAR_STATUS_TRACEABLE
    assert result["dp_by_element"] == {"C": "0", "O": "0"}
    assert result["dt_by_element"] == {"C": "0", "O": "0"}
    assert result["dc_by_element"] == {"C": "0", "O": "0"}
    assert result["surplus_by_element"] == {"C": "1", "O": "1"}
    assert result["surplus_positive"] is True
    assert result["n_elements_surplus_positive"] == 2
    assert result["display_name"] == "按声明的非氢元素预算检查"


def test_dp_positive_forces_unknown_even_when_dc_is_zero() -> None:
    """⑧b 主产物本身已超预算(Dp≠0)⇒ unknown,Dt 仍报告。"""
    result = _budget([
        _entry("s-eth", "reactant", "primary_substrate", "1", "known"),
        _entry("s-gly", "product", "principal_product", "1", "known"),
        _entry("s-w", "product", "coproduct", "1", "known", seq=2),
    ])
    # R=C2;P=C3O3 ⇒ Dp:C1,O3;Dt:C1,O3
    assert result["status"] == CRITERIA_V5_C4STAR_STATUS_UNKNOWN
    assert CRITERIA_V5_C4STAR_REASON_PRINCIPAL_OVER_BUDGET in \
        result["reason_codes"]
    assert result["dp_by_element"]["C"] == "1"
    assert result["dt_by_element"]["C"] == "1"


# ---------------------------------------------------------------- ⑨ 小分子


@pytest.mark.parametrize("coproduct,element", [
    ("s-w", "O"),       # H₂O 计 O
    ("s-co2", "C"),     # CO₂ 计 C/O
    ("s-pi", "P"),      # Pi 计 P/O
])
def test_small_inorganic_coproducts_are_not_exempt(coproduct, element) -> \
        None:
    """⑨ 无任何分子/方向豁免:小无机物同样占用声明预算。"""
    # R=乙烷 C2;P=乙烯 C2 ⇒ 剩余 C0,O0;任何含 O/C/P 的共产物都超
    result = _budget([
        _entry("s-eth", "reactant", "primary_substrate", "1", "known"),
        _entry("s-ene", "product", "principal_product", "1", "known"),
        _entry(coproduct, "product", "coproduct", "1", "known", seq=2),
    ])
    assert result["status"] == CRITERIA_V5_C4STAR_STATUS_UNTRACEABLE
    assert result["dt_by_element"].get(element, "0") != "0"


def test_water_coproduct_consumes_oxygen_budget() -> None:
    """⑨b H₂O 计 O:O 预算不足 ⇒ untraceable(不因"补水惯例"豁免)。"""
    result = _budget([
        _entry("s-eth", "reactant", "primary_substrate", "1", "known"),
        _entry("s-ene", "product", "principal_product", "1", "known"),
        _entry("s-w", "product", "coproduct", "1", "known", seq=2),
    ])
    assert result["status"] == CRITERIA_V5_C4STAR_STATUS_UNTRACEABLE
    assert result["dt_by_element"] == {"C": "0", "O": "1"}


# ---------------------------------------------------------------- ⑩ 执行分离


def test_declared_copy_is_not_forced_unknown_by_missing_execution() -> None:
    """⑩ declared-copy 参与声明预算;执行覆盖独立为 ``not_verified``。"""
    result = _budget([
        _entry("s-gly", "reactant", "primary_substrate", "1", "known"),
        _entry("s-ald", "product", "principal_product", "1", "known"),
        _entry("s-naac", "product", "coproduct", "1", "known", seq=2),
    ])
    # R=C3O3;P=C2O1;剩余 C1O2;C=乙酸钠 C2O2Na1 ⇒ C/O/Na 均超
    assert result["status"] == CRITERIA_V5_C4STAR_STATUS_UNTRACEABLE
    assert result["execution_coverage_status"] == "not_verified"
    assert "未核执行" in result["execution_coverage_note"]
    # 元素账不因"未执行"被强制 unknown:盐按写入多组分整串计
    assert "Na" in result["dt_by_element"]
    assert result["budget_account_computable"] is True


# ---------------------------------------------------------------- ⑪ 合法正控


def test_positive_control_budget_sufficient_is_traceable() -> None:
    """⑪ 合法正控:预算足 ⇒ traceable(按声明的非氢预算覆盖)。"""
    result = _budget([
        _entry("s-gly", "reactant", "primary_substrate", "1", "known"),
        _entry("s-ald", "product", "principal_product", "1", "known"),
        _entry("s-co2", "product", "coproduct", "1", "known", seq=2),
    ])
    assert result["status"] == CRITERIA_V5_C4STAR_STATUS_TRACEABLE
    assert result["budget_account_computable"] is True


# ---------------------------------------------------------------- 结构不可解析


@pytest.mark.parametrize("structure,reason", [
    ("", CRITERIA_V5_C4STAR_REASON_STRUCTURE_UNPARSEABLE),
    ("not-a-smiles", CRITERIA_V5_C4STAR_REASON_STRUCTURE_UNPARSEABLE),
    (WILDCARD, CRITERIA_V5_C4STAR_REASON_UNQUANTIFIABLE_GROUP),
])
def test_unparseable_or_wildcard_structure_is_unknown(structure, reason) -> \
        None:
    structures = dict(STRUCTURES)
    structures["s-ald"] = structure
    result = _budget([
        _entry("s-gly", "reactant", "primary_substrate", "1", "known"),
        _entry("s-ald", "product", "principal_product", "1", "known"),
        _entry("s-w", "product", "coproduct", "1", "known", seq=2),
    ], structures=structures)
    assert result["status"] == CRITERIA_V5_C4STAR_STATUS_UNKNOWN
    assert reason in result["reason_codes"]
    assert result["budget_account_computable"] is False


# ---------------------------------------------------------------- 判分透传


def test_disclosure_switch_does_not_change_v5_hit() -> None:
    """披露轴开关不影响命中:关闭 C4*(退回占位 unknown 块)后
    hit/rank/bucket 与开启时逐字节一致。"""
    from test_ppv1_criteria_v5 import (
        PRODUCT_A, SUBSTRATE, WATER, _event, _payload, _single_graph,
    )
    from pathway_v43.pollutant import evaluation as evaluation_module
    from pathway_v43.pollutant.evaluation import (
        PPV1_CRITERIA_V5, match_reference_edges, match_reference_nodes,
    )

    graph = _single_graph()
    payload = _payload(
        {"cs-sub": SUBSTRATE, "cs-p1": PRODUCT_A, "cs-w": WATER},
        [_event("ev-1", [("cs-sub", "reactant", "primary_substrate"),
                         ("cs-p1", "product", "principal_product"),
                         ("cs-w", "product", "coproduct")])])
    node_matches = match_reference_nodes(
        graph, payload, criteria_version=PPV1_CRITERIA_V5)
    on = match_reference_edges(
        graph, payload, node_matches,
        criteria_version=PPV1_CRITERIA_V5)[0]["criteria_v5"]

    original = evaluation_module.criteria_c4star_non_hydrogen_budget

    def _placeholder(*_args, **_kwargs):
        return evaluation_module._criteria_c4star_unavailable_budget()

    evaluation_module.criteria_c4star_non_hydrogen_budget = _placeholder
    try:
        node_matches_off = match_reference_nodes(
            graph, payload, criteria_version=PPV1_CRITERIA_V5)
        off = match_reference_edges(
            graph, payload, node_matches_off,
            criteria_version=PPV1_CRITERIA_V5)[0]["criteria_v5"]
    finally:
        evaluation_module.criteria_c4star_non_hydrogen_budget = original

    def _hit_facts(block: dict) -> dict:
        return {
            "hit": block["role_bound_product_hit"],
            "bucket": block["bucket"],
            "hit_events": block["role_bound_hit_events"],
            "partial_events": block["partial_product_hit_events"],
            "eligible": block["eligible_event_count"],
            "event_flags": [
                (row["event_id"], row["eligible"],
                 row.get("role_bound_product_hit"),
                 row.get("substrate_identity_in_reactants"),
                 row.get("principal_products_matched_principal"))
                for row in block["events"]],
        }

    assert _hit_facts(on) == _hit_facts(off)
    # 披露块本身必须不同(证明开关真的切换了披露轴,而不是空转)
    assert on["events"][0]["c4star_budget"]["reason_codes"] != \
        off["events"][0]["c4star_budget"]["reason_codes"]


def test_caliber_block_aggregates_c4star_states_and_gaps() -> None:
    """判分层聚合:四状态计数 + reason code 分布 + Dp/Dt/Dc 非零计数。"""
    def _row(trace: str, reasons: list[str], *, dp: bool, dt: bool,
             dc: bool) -> dict:
        return {
            "rank": 1, "bucket": "role_bound_product_hit",
            "disclosure": {
                "event_id": "ev-1", "n_product_species_total": 2,
                "n_principal_species": 1, "n_coproduct_species": 1,
                "n_other_role_species": 0, "n_multirole_species": 0,
                "n_participant_entries": 2,
                "product_species_bucket": "2",
                "coproduct_traceability": trace,
                "coproduct_traceability_reason": ";".join(reasons),
                "c4star_budget": {
                    "status": trace, "reason_codes": reasons,
                    "budget_account_computable": dp or dt or dc
                    or trace in ("traceable", "untraceable"),
                    "dp_positive": dp, "dt_positive": dt,
                    "dc_positive": dc, "surplus_positive": not dp,
                },
            },
            "max_product_species_any_qualifying_event": 2,
            "matched_event_not_in_candidates": False,
        }

    rows = [
        _row("traceable", [], dp=False, dt=False, dc=False),
        _row("untraceable", [], dp=False, dt=True, dc=True),
        _row("unknown", ["unknown_coefficient"], dp=False, dt=False,
             dc=False),
        _row("unknown", ["manifest_partial"], dp=False, dt=False, dc=False),
    ]
    block = _role_bound_hit_caliber_block(rows, 4, domain_tag="298")
    axis = block["disclosure_axis_5_2"]
    assert axis["status"] == "implemented_c4star"
    assert axis["counts"] == {"traceable": 1, "unknown": 2,
                              "untraceable": 1}
    assert axis["reason_code_counts"] == {"manifest_partial": 1,
                                          "unknown_coefficient": 1}
    assert axis["dp_positive"] == 0
    assert axis["dt_positive"] == 1
    assert axis["dc_positive"] == 1
    assert axis["budget_account_computable"] == 2
    assert axis["budget_account_not_computable"] == 2
    assert axis["display_name"] == "按声明的非氢元素预算检查"


def test_c4star_block_is_json_serializable_and_has_no_structure_strings() \
        -> None:
    """证据落盘约束:块内零 SMILES(只有状态/计数/reason code/元素符号)。"""
    result = _budget([
        _entry("s-gly", "reactant", "primary_substrate", "1", "known"),
        _entry("s-ald", "product", "principal_product", "1", "known"),
        _entry("s-co2", "product", "coproduct", "1", "known", seq=2),
    ])
    text = json.dumps(result, ensure_ascii=False)
    for smiles in (GLYCEROL, ACETALDEHYDE, CO2):
        assert smiles not in text
    assert json.loads(text)["status"] == "traceable"