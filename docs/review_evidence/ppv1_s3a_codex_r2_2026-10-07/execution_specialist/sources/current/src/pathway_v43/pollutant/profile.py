"""pollutant_pathway_v1 profile 注册与版本清单(S0 单一事实源)。

- 本模块只声明 profile 身份、契约版本与开关取值域,不含任何执行逻辑;
- run_identity 在 profile=pollutant_pathway_v1 时经
  ``build_profile_identity_block`` 延迟取用本模块(legacy 路径不 import);
- 全部版本常量只增不改值;取值域校验 fail-closed(未知值拒绝,不回退);
- P0-3 的搜索上限为**实际可执行版本 v3**(S3a 批次落地计数/恢复,
  由 pollutant/search.py 消费;S2 时期的 -2-proposed 草案从未放行执行,
  无历史产物迁移)。
"""

from __future__ import annotations

from ..storage.run_identity import (
    PROFILE_POLLUTANT_PATHWAY_V1,
)

PPV1_PROFILE_NAME = PROFILE_POLLUTANT_PATHWAY_V1

# ---- 契约版本清单(全部版本进入 profile 身份块;变更须升版本) ----
# v2(2026-10-05 回修):F01–F11/P2 回修涉及的契约全部升版;本 profile
# 从未放行执行流,无历史产物需要迁移(升版即兼容声明,见回修交付书)。
# v3(2026-10-06 R3 回修):R2-01~12 + P2(见 v2 注释下方)。
# v4(2026-10-06 R4 回修):Codex R3 复审 R3-01~12 + §4 涉及的契约全部
# 升版(证据绑定/手性感知联合映射/CIP 构型比较/CX 事实子集身份/
# 声明净效应模拟/路线快照消费/依赖并集/完整 input_hash/writer 重推导/
# 重放内容校验/导入引用核对/matrix unknown)。profile 仍未放行执行流,
# 无历史产物需要迁移。search-limits 为 proposed 草案,语义未变不动。
# v5(2026-10-07 R5 回修):Codex R4 复审 R4-01~11 + §4 涉及的契约全部
# 升版(证据证明链内部重算+产物集合覆盖/有限规则诊断入 hash/载荷
# 不可变+入口身份复算/单位未知不满足/快照签名覆盖+场景作用域/支持
# 分轴撤销/镜像活 ID 表+前置复核/键立体与非四面体公开载荷/DATA
# SGroup 剥离+未登记 CX 拒绝/writer 事实契约/事件出现清单/旧导入
# 关系核验)。gate_mapper(-3,未触碰)与 search-limits(proposed)不动。
# v7(2026-10-07 R7 回修):Codex R6 复审 R6-01~05 涉及的契约族升版
# (补全许可按严格结构身份注册/原始 CX 输入按真实类边界逐项词法+
# 供体诊断四个原始字符串入口同源守卫/上下文派生先验父对象+覆盖签名
# 须对应已记录评估行/首提复用既存行立即共用重放校验/事件出现集合
# 独立完整性表 event_appearance_links)。profile 仍未放行执行流,
# 无历史产物需要迁移;v6 载荷按未知版本既有门拒绝。
# v8(2026-10-07 R8 回修):Codex R7 复审两项 P1 涉及的契约族升版
# (R7-01:ChemicalState.from_dict 恢复与 audit 直接 states 首次消费
# 共用与公共 writer 同源的纯状态验证 —— raw 登记守卫 + raw→strict
# 身份一致 + 规范身份/结构事实重推导 + CN-only 专用契约,不只补
# from_dict 留 dataclass 绕路、不静默清洗信息再授 full;R7-02:首提
# 对 supplied SID 的既存同 (SID,hash) 出现行在收集阶段立即复算内容
# hash,损坏 ⇒ LedgerCorrupt 零新增,不延后到重放)。gate_mapper
# (-3,未触碰)与 search-limits(proposed)不动;profile 仍未放行
# 执行流,v7 载荷按未知版本既有门拒绝,无兼容迁移。
# v9(2026-10-07 S3a 批次):S3a 持久搜索底座交付 —— 新增 search
# 契约(ppv1-search-1:SearchAction/expansion_attempt/预算预约/模型
# 请求/提交记录/四崩溃恢复协议/停止原因主因优先级,见 pollutant/
# search.py)与 store(ppv1-store-9:六张搜索底座表);search-limits
# 由 proposed 草案 v2 升为**实际可执行版本 v3**(键/默认/范围/单位
# 全部沿用草案,不凭空重造;新增计数/预约/consume/release 规则);
# 其余 S0–S2 契约语义不动(chemstate/hypothesis/event/context/
# dependency/provenance/substrate_profile/audit/admission_policy/
# donor_diagnostic/pool_audit/pool_order/input_preview/condition_
# assessment 保持 -8;gate_mapper -3 不动)。delivered_stages 更新
# 为 S0-S2,S3a-base(底座;队列化学集成/生产链/runner 分流属 S3b,
# workflow.runner 对本 profile 继续 fail-closed)。profile 仍未放行
# 执行流,无历史产物需要迁移;v8 身份载荷按既有门拒绝。
# v10(2026-10-07 S3a 回修 r2,Codex S3a 复审 S3A-01~05):搜索消费
# 协议闭合升版 —— search 契约 ppv1-search-1 → ppv1-search-2(B3/
# write_bundle 与全部输出消费入口共用 action+attempt+task+event 完整
# 绑定;first complete/B4/done/已有提交结果复用接入公共 writer 重放
# 同源的完整事件账权威核验,并核 attempt/预约引用存在与归属;defer
# 先核"确实未执行"持久事实,已提交事件/已发送请求/已落账 attempt 不
# 得退还已用预算;模型请求同键异身份内容结构化冲突,登记/发送/响应/
# 失败核合法 run/action/attempt 执行引用与生命周期;停止报告披露
# claimed/open attempt,执行未完成不称 exhausted_search)。search_
# limits 保持 -3(十键/默认/范围/单位未动,注册/读取/恢复改为同源
# 复用 validate_search_limits 公开入口);store 保持 -9(表结构与
# writer 行为未改,权威核验从 search 层调用公共 submit_event,不在
# store 复制校验)。profile 仍未放行执行流,无历史产物需要迁移;
# v9 身份载荷按既有门拒绝。

PPV1_PROFILE_SCHEMA_VERSION = "ppv1-profile-10"
PPV1_CHEMSTATE_SCHEMA_VERSION = "ppv1-chemstate-8"
PPV1_HYPOTHESIS_SCHEMA_VERSION = "ppv1-hypothesis-8"
PPV1_EVENT_SCHEMA_VERSION = "ppv1-event-8"
PPV1_STORE_SCHEMA_VERSION = "ppv1-store-9"
PPV1_CONTEXT_SCHEMA_VERSION = "ppv1-context-8"
PPV1_DEPENDENCY_SCHEMA_VERSION = "ppv1-dependency-8"
PPV1_PROVENANCE_SCHEMA_VERSION = "ppv1-provenance-8"
PPV1_SUBSTRATE_PROFILE_SCHEMA_VERSION = "ppv1-substrate-profile-8"
PPV1_AUDIT_SCHEMA_VERSION = "ppv1-audit-8"
PPV1_ADMISSION_POLICY_VERSION = "ppv1-admission-8"
PPV1_DONOR_DIAGNOSTIC_VERSION = "ppv1-donor-diagnostic-8"
PPV1_POOL_AUDIT_SCHEMA_VERSION = "ppv1-pool-audit-8"
PPV1_POOL_ORDER_VERSION = "ppv1-pool-order-8"
PPV1_INPUT_PREVIEW_VERSION = "ppv1-input-preview-8"
PPV1_CONDITION_ASSESSMENT_VERSION = "ppv1-condition-assessment-8"
PPV1_GATE_MAPPER_VERSION = "ppv1-gate-mapper-3"
# S3a:持久搜索底座契约(SearchAction/attempt/预约/请求/提交记录/
# 恢复协议/停止原因优先级;pollutant/search.py)
# v2(S3a 回修 r2,2026-10-07,Codex S3a 复审 S3A-01~05):搜索消费
# 协议闭合 —— 输出消费入口(B3/write_bundle/首次 complete/B4/done/
# 已有提交结果复用)共用 action+attempt+task+event 完整绑定与公共
# writer 重放同源的完整事件账权威核验,并核 attempt/预约引用存在与
# 归属;defer 先核"确实未执行"持久事实(已提交事件/已发送请求/已
# 落账 attempt 不退已用预算);模型请求同键异身份内容结构化冲突,
# 登记/复用/发送/响应/失败核合法 run/action/attempt 执行引用与生命
# 周期;停止报告披露 claimed/open attempt,执行未完成不称
# exhausted_search。v1(S3a 首批)登记 SearchAction/expansion_attempt/
# 预算预约/模型请求/提交记录/四崩溃恢复协议/停止原因主因优先级。
PPV1_SEARCH_SCHEMA_VERSION = "ppv1-search-2"
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

# ---- P0-3 有界搜索上限(实际可执行版本 v3;S3a 落地计数/恢复) ----
# v2(proposed 草案):键拆分(父备选假设数 vs 单假设语义尝试数)、
# 下限放宽到 0(独立零预算夹具)、配置完整往返可重放。
# v3(S3a 实际可执行,2026-10-07):继承 v2 全部键/默认/范围/单位,
# 不凭空重造;由 pollutant/search.py 的 SearchLedger 落地实际计数
# (认领预约/consume/release/账表见该模块 docstring)、四崩溃恢复
# 与 E04 循环稳定停。S3a 回修 r2(2026-10-07):注册/读取/恢复改为
# 同源复用下方 validate_search_limits 公开入口(十键类型/范围/版本
# 校验单一实现,search 层不复制),计数语义本身未动、版本不升。
# 草案 v2 从未放行执行(无历史产物迁移),升版
# 即生效;旧 -2-proposed 配置按版本门拒绝。停止原因主因优先级
# (user_stop > budget_limit > depth_limit > no_local_candidate >
# awaiting_prediction > exhausted_search)随 search 契约在
# search.py 登记,多原因同时成立取主因并保留其余原因。
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
SEARCH_LIMITS_VERSION = "ppv1-search-limits-3"
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
        "search": PPV1_SEARCH_SCHEMA_VERSION,
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


def validate_search_limits(limits: dict | None) -> dict:
    """校验/归一搜索上限(实际可执行版本 v3;接受覆盖配置或完整
    序列化配置)。**单一实现**:profile 装配与 pollutant/search 的
    注册/读取/恢复消费同源共用(S3a 回修 r2:SearchLedger 注册、
    _limits 读视图、恢复策略核验都调用本函数,不在 search 层复制
    十键类型/范围/版本校验)。

    - "version" 是版本字符串键(非预算),仅校验值等于当前版本,
      不按整数预算校验(v1 的 KeyError 缺陷修复);
    - 输出恒为**完整**配置(缺省键补默认;可直接原样回灌本函数,
      round-trip 稳定);
    - 未知键/类型错误(含 bool)/越界 fail-closed。
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


# 内部名保留(装配路径历史引用;与 validate_search_limits 同一实现)
_validate_search_limits = validate_search_limits


def build_profile_identity_block(
    *,
    input_preview_policy: str = INPUT_PREVIEW_POLICY_DEFAULT,
    chemical_reproposal: str = CHEMICAL_REPROPOSAL_DEFAULT,
    search_intent: str | None = None,
    search_limits: dict | None = None,
) -> dict:
    """pollutant_pathway_v1 的 run 身份 profile 块(全部开关进身份)。

    未知取值 fail-closed(ValueError,装配期拒绝),不静默回退默认。
    search_limits 为实际可执行版本 v3(S3a 底座计数);S3b 公共链
    集成交付前 run 执行入口仍 fail-closed(见 workflow.runner)。
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
        # S0–S2 交付领域契约/上下文/固定诊断;S3a 交付持久搜索底座
        # (身份/预算/认领/恢复,测试入口用 pollutant.search 底座 API);
        # 公共执行流入口 workflow.runner 对本 profile 继续 fail-closed
        # (队列化学集成与生产链属 S3b,交付前拒绝运行)
        "delivered_stages": "S0-S2,S3a-base",
    }
