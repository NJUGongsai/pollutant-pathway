"""pollutant_pathway_v1 profile 注册与版本清单(S0 单一事实源)。

- 本模块只声明 profile 身份、契约版本与开关取值域,不含任何执行逻辑;
- run_identity 在 profile=pollutant_pathway_v1 时经
  ``build_profile_identity_block`` 延迟取用本模块(legacy 路径不 import);
- 全部版本常量只增不改值;取值域校验 fail-closed(未知值拒绝,不回退);
- P0-3 的搜索上限为 **proposed 草案**(实施书 §17.1:S2 交设计草案,
  S3 才有实际计数/恢复代码);此处只冻结键名、默认值、允许范围、
  计数单位与优先级,不据此运行任何搜索。
"""

from __future__ import annotations

from ..storage.run_identity import (
    PROFILE_POLLUTANT_PATHWAY_V1,
)

PPV1_PROFILE_NAME = PROFILE_POLLUTANT_PATHWAY_V1

# ---- 契约版本清单(全部版本进入 profile 身份块;变更须升版本) ----
# v2(2026-10-05 回修):F01–F11/P2 回修涉及的契约全部升版;本 profile
# 从未放行执行流,无历史产物需要迁移(升版即兼容声明,见回修交付书)。

PPV1_PROFILE_SCHEMA_VERSION = "ppv1-profile-2"
PPV1_CHEMSTATE_SCHEMA_VERSION = "ppv1-chemstate-2"
PPV1_HYPOTHESIS_SCHEMA_VERSION = "ppv1-hypothesis-2"
PPV1_EVENT_SCHEMA_VERSION = "ppv1-event-2"
PPV1_STORE_SCHEMA_VERSION = "ppv1-store-2"
PPV1_CONTEXT_SCHEMA_VERSION = "ppv1-context-2"
PPV1_DEPENDENCY_SCHEMA_VERSION = "ppv1-dependency-2"
PPV1_PROVENANCE_SCHEMA_VERSION = "ppv1-provenance-2"
PPV1_SUBSTRATE_PROFILE_SCHEMA_VERSION = "ppv1-substrate-profile-2"
PPV1_AUDIT_SCHEMA_VERSION = "ppv1-audit-2"
PPV1_ADMISSION_POLICY_VERSION = "ppv1-admission-2"
PPV1_DONOR_DIAGNOSTIC_VERSION = "ppv1-donor-diagnostic-2"
PPV1_POOL_AUDIT_SCHEMA_VERSION = "ppv1-pool-audit-2"
PPV1_POOL_ORDER_VERSION = "ppv1-pool-order-2"
PPV1_INPUT_PREVIEW_VERSION = "ppv1-input-preview-2"
PPV1_CONDITION_ASSESSMENT_VERSION = "ppv1-condition-assessment-2"
PPV1_GATE_MAPPER_VERSION = "ppv1-gate-mapper-1"
# 复用的既有冻结判据(只引用,不修改;覆盖限制见各模块 docstring)
LEGACY_GATE_PROFILE_REF = "frozen_hit60_gate"  # legacy 门禁族(v43 gates/G2)
LEGACY_G2_FAMILY_REF = "v43-cons-2"            # 有限规则诊断复用族(conservation.py)

# ---- 输入侧 preview 开关(实施书 §17.2:off | diagnostic,进策略身份) ----

INPUT_PREVIEW_OFF = "off"
INPUT_PREVIEW_DIAGNOSTIC = "diagnostic"
INPUT_PREVIEW_VALUES = frozenset({INPUT_PREVIEW_OFF, INPUT_PREVIEW_DIAGNOSTIC})
INPUT_PREVIEW_POLICY_DEFAULT = INPUT_PREVIEW_OFF

# SMILES 解析失败后的重新提案策略(实施书 §7.2:首版默认关闭)
CHEMICAL_REPROPOSAL_OFF = "off"
CHEMICAL_REPROPOSAL_ON = "on"
CHEMICAL_REPROPOSAL_VALUES = frozenset({CHEMICAL_REPROPOSAL_OFF,
                                         CHEMICAL_REPROPOSAL_ON})
CHEMICAL_REPROPOSAL_DEFAULT = CHEMICAL_REPROPOSAL_OFF

# ---- 搜索意图(实施书 §17.3.4:首版仅说明字段,不隐含任何策略变化) ----

SEARCH_INTENT_EXPLORATION = "exploration"
SEARCH_INTENT_VERIFICATION = "verification"
SEARCH_INTENT_GAP_FILLING = "gap_filling"
SEARCH_INTENTS = frozenset({SEARCH_INTENT_EXPLORATION,
                            SEARCH_INTENT_VERIFICATION,
                            SEARCH_INTENT_GAP_FILLING})

# ---- P0-3 有界搜索上限(proposed 草案 v2;S3 才实施计数/恢复/E04) ----
# v2(P2-3/P2-4 回修):
# - 键拆分:父路径**备选假设数**与单假设**语义尝试次数**独立计数,
#   不得相互代替(v1 的 max_hypotheses_per_parent_alternative 把两个
#   单位混在一个键里,已废除);
# - 下限放宽到 0:S3 需要独立的零深度/零预算验收夹具(0 = 该维度
#   零预算,立即停),不再用"其他零预算已覆盖"搪塞;
# - 配置往返:build_profile_identity_block 接受覆盖配置或完整序列化
#   配置(version 字符串键不按预算校验),输出可原样回灌(P2-4)。
# 计数单位与语义(全部来自持久记录,不取内存状态):
# - max_alternative_hypotheses_per_parent:同一父路径上并行备选反应
#   **假设**的数量(假设数)
# - max_attempts_per_hypothesis:单个假设的**语义尝试**次数(含首次;
#   attempt 数,重开是其中的子类,由 max_reopens_per_hypothesis 单独
#   限制"无新信息重开")
# - max_product_expansion_width:单个事件产物继续展开的宽度(产物宽度)
# - max_search_depth:搜索深度(路径边数;0 = 不展开任何产物)
# - max_total_search_actions:run 级 SearchAction 总数(含
#   scenario_transition;0 = 不执行任何搜索动作)
# - max_scenario_transitions:阶段转换次数(不是反应边,单独计数)
# - max_reopens_per_hypothesis:同一假设无新信息时的重开次数上限
# - max_real_model_requests:真实模型请求登记数(0 = 默认不发出付费
#   请求;悬空请求也计额度)
# - max_retrievals_per_parent:每父路径实际检索次数(复用产物不重复
#   计数;0 = 不检索)
# - max_retrievals_total:run 级实际检索总数(0 = 不检索)
# 优先级(多原因同时发生时的主因次序,S3 冻结;user_stop 恒最优先):
#   user_stop > budget_limit > depth_limit > no_local_candidate >
#   awaiting_prediction > exhausted_search
SEARCH_LIMITS_VERSION = "ppv1-search-limits-2-proposed"
SEARCH_LIMITS_DEFAULTS: dict = {
    "version": SEARCH_LIMITS_VERSION,
    "max_alternative_hypotheses_per_parent": 2,
    "max_attempts_per_hypothesis": 2,
    "max_product_expansion_width": 2,
    "max_search_depth": 3,
    "max_total_search_actions": 10,
    "max_scenario_transitions": 2,
    "max_reopens_per_hypothesis": 1,
    "max_real_model_requests": 0,
    "max_retrievals_per_parent": 1,
    "max_retrievals_total": 64,
}
SEARCH_LIMITS_RANGES: dict = {
    # 键 → (下限, 上限);超出装配期拒绝。下限 0 = 零预算验收夹具合法
    # (测试小值在允许范围内)
    "max_alternative_hypotheses_per_parent": (0, 8),
    "max_attempts_per_hypothesis": (0, 8),
    "max_product_expansion_width": (0, 8),
    "max_search_depth": (0, 10),
    "max_total_search_actions": (0, 1000),
    "max_scenario_transitions": (0, 4),
    "max_reopens_per_hypothesis": (0, 3),
    "max_real_model_requests": (0, 10000),
    "max_retrievals_per_parent": (0, 4),
    "max_retrievals_total": (0, 4096),
}


def contract_versions() -> dict:
    """S0–S2 契约版本清单(进入 profile 身份块;S3 起在本表追加)。"""
    return {
        "profile": PPV1_PROFILE_SCHEMA_VERSION,
        "chemstate": PPV1_CHEMSTATE_SCHEMA_VERSION,
        "hypothesis": PPV1_HYPOTHESIS_SCHEMA_VERSION,
        "event": PPV1_EVENT_SCHEMA_VERSION,
        "store": PPV1_STORE_SCHEMA_VERSION,
        "context": PPV1_CONTEXT_SCHEMA_VERSION,
        "dependency": PPV1_DEPENDENCY_SCHEMA_VERSION,
        "provenance": PPV1_PROVENANCE_SCHEMA_VERSION,
        "substrate_profile": PPV1_SUBSTRATE_PROFILE_SCHEMA_VERSION,
        "audit": PPV1_AUDIT_SCHEMA_VERSION,
        "admission_policy": PPV1_ADMISSION_POLICY_VERSION,
        "donor_diagnostic": PPV1_DONOR_DIAGNOSTIC_VERSION,
        "pool_audit": PPV1_POOL_AUDIT_SCHEMA_VERSION,
        "pool_order": PPV1_POOL_ORDER_VERSION,
        "input_preview": PPV1_INPUT_PREVIEW_VERSION,
        "condition_assessment": PPV1_CONDITION_ASSESSMENT_VERSION,
        "gate_mapper": PPV1_GATE_MAPPER_VERSION,
        "legacy_gate_ref": LEGACY_GATE_PROFILE_REF,
        "legacy_g2_family_ref": LEGACY_G2_FAMILY_REF,
    }


def _validate_input_preview(value) -> str:
    v = "" if value is None else str(value)
    if v not in INPUT_PREVIEW_VALUES:
        raise ValueError(
            f"input_preview_policy 非法取值:{value!r}(允许 "
            f"{'/'.join(sorted(INPUT_PREVIEW_VALUES))};off=不执行并如实"
            "记录,diagnostic=只附有限规则诊断,不改池成员/档位/顺序)")
    return v


def _validate_chemical_reproposal(value) -> str:
    v = "" if value is None else str(value)
    if v not in CHEMICAL_REPROPOSAL_VALUES:
        raise ValueError(
            f"chemical_reproposal 非法取值:{value!r}(允许 "
            f"{'/'.join(sorted(CHEMICAL_REPROPOSAL_VALUES))};首版默认 off:"
            "SMILES 解析失败记结构失败,不重试到产物通过门禁)")
    return v


def _validate_search_intent(value) -> str:
    if value is None:
        return SEARCH_INTENT_EXPLORATION
    v = str(value)
    if v not in SEARCH_INTENTS:
        raise ValueError(
            f"search_intent 非法取值:{value!r}(允许 "
            f"{'/'.join(sorted(SEARCH_INTENTS))};首版为说明字段,"
            "verification/gap_filling 不隐含放宽门禁/排序/预算,"
            "对应意图策略未实现即 unsupported)")
    return v


def _validate_search_limits(limits: dict | None) -> dict:
    """校验/归一搜索上限(P2-4:接受覆盖配置或完整序列化配置)。

    - "version" 是版本字符串键(非预算),仅校验值等于当前版本,
      不按整数预算校验(v1 的 KeyError 缺陷修复);
    - 输出恒为**完整**配置(缺省键补默认;可直接原样回灌本函数,
      round-trip 稳定);
    - 未知键/类型错误/越界 fail-closed。
    """
    out = dict(SEARCH_LIMITS_DEFAULTS)
    for k, v in (limits or {}).items():
        if k == "version":
            if v != SEARCH_LIMITS_VERSION:
                raise ValueError(
                    f"search_limits.version 非法:{v!r}(当前 "
                    f"{SEARCH_LIMITS_VERSION})")
            out["version"] = v
            continue
        if k not in SEARCH_LIMITS_RANGES:
            allowed = sorted(SEARCH_LIMITS_RANGES)
            raise ValueError(
                f"未知搜索上限键:{k!r}(允许 {allowed})")
        if isinstance(v, bool) or not isinstance(v, int):
            raise ValueError(f"搜索上限 {k} 必须是整数,得到 {v!r}")
        lo, hi = SEARCH_LIMITS_RANGES[k]
        if not (lo <= v <= hi):
            raise ValueError(
                f"搜索上限 {k}={v} 超出允许范围 [{lo},{hi}]")
        out[k] = v
    return out


def build_profile_identity_block(
    *,
    input_preview_policy: str = INPUT_PREVIEW_POLICY_DEFAULT,
    chemical_reproposal: str = CHEMICAL_REPROPOSAL_DEFAULT,
    search_intent: str | None = None,
    search_limits: dict | None = None,
) -> dict:
    """pollutant_pathway_v1 的 run 身份 profile 块(全部开关进身份)。

    未知取值 fail-closed(ValueError,装配期拒绝),不静默回退默认。
    search_limits 为 P0-3 proposed 草案,S3 交付实际计数前仅作身份
    冻结与配置校验。
    """
    return {
        "name": PPV1_PROFILE_NAME,
        "schema_version": PPV1_PROFILE_SCHEMA_VERSION,
        "contracts": contract_versions(),
        "input_preview_policy": _validate_input_preview(input_preview_policy),
        "input_preview_version": PPV1_INPUT_PREVIEW_VERSION,
        "chemical_reproposal": _validate_chemical_reproposal(
            chemical_reproposal),
        "search_intent": _validate_search_intent(search_intent),
        "search_limits": _validate_search_limits(search_limits),
        # S0–S2 只交付领域契约与固定诊断;执行流未交付前 run 入口
        # fail-closed(见 workflow.runner),此处身份如实声明交付阶段
        "delivered_stages": "S0-S2",
    }
