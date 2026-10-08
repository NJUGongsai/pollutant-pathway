"""S5a 预注册模板(ppv1-preregistration-template-3;§10.2/§14.3)。

模板交付边界(§14.3):

- 逐项标注哪些字段是**用户/teacher 裁定**(TBD_USER_TEACHER_DECISION);
- 逐项标注哪些规则只是 **proposed**(PROPOSED_NOT_FROZEN);
- 逐项标注哪些阈值**尚未冻结**;
- 逐项标注哪些指标只有**接口定义**(interface_definition_only);
- 标注哪些结果**不得在冻结前对外发布**。

S5a 回修 r1(2026-10-09,复审 §4 四组 P1):模板 -1 → -2,proposed
文字与实现证明范围同步(identity scope 许可封顶、必要节点闭合、
条件同源口径、写边界根规则、角色/系数与 unknown==unknown 的实现
证明范围如实标注;全部仍 proposed 不冻结,§10.1 全部 TBD 不变)。

S5a 回修 r2(2026-10-09,复审 R2 §4 唯一残余 P1):模板 -2 → -3,
condition_policy proposed 文字与实现同真 —— 要求侧单位首消费收口
(显式非规范/无量纲键声明单位 ⇒ unknown/unsupported 族 + 机读保留
原 unit/value/key;空单位 canonical-by-key 默认合法)与 B2 事实
更正(同键相反事实两序 unknown;known×unknown 按首条已知事实;
低层 dataclass 次序边界另列 P2);全部仍 proposed 不冻结。

S5a 只交付模板与装配/校验程序;**不冻结任何字段取值**(§10.1 全部
TBD 属用户/teacher 裁定,不得代定;不得从当前 dev 结果反推阈值或
样本量)。判分零 LLM;真实 provider 默认 off;对外数字必须带题域
标签(dev 与 298 双向不外推)。
"""

from __future__ import annotations

import hashlib

from ..domain.models import canonical_json
from .profile import PPV1_PREREGISTRATION_TEMPLATE_VERSION

TBD = "TBD_USER_TEACHER_DECISION"
PROPOSED = "PROPOSED_NOT_FROZEN"
INTERFACE_ONLY = "interface_definition_only"

# §10.1 必须由用户/teacher 裁定的 20 项(模板逐项占位,不得代定)
USER_TEACHER_DECISION_ITEMS = (
    ("topic_source_scope", "题源范围"),
    ("gold_standard_calibration", "金标口径"),
    ("scorable_reference_edges_nodes", "哪些反应边和节点属于可评分参考"),
    ("unknown_partial_conditional_denominator",
     "unknown/partial/conditional 的分母处理"),
    ("source_group_independence_calibration",
     "研究来源组的独立性口径"),
    ("sample_size_dev", "dev 题域样本量"),
    ("sample_size_298", "298 题域样本量"),
    ("sample_size_known", "known 轨道样本量"),
    ("sample_size_unseen", "unseen 轨道样本量"),
    ("reference_coverage_exclusion_rule",
     "参考图覆盖不足时的排除规则"),
    ("identity_matching_rules",
     "严格结构/CN/反应中心/step scope 的匹配规则"),
    ("pass_threshold", "通过线"),
    ("per_metric_thresholds", "单项指标最低线"),
    ("confidence_interval_method", "置信区间方法"),
    ("multiple_comparison_policy", "多重比较处理"),
    ("per_depth_threshold_required", "是否要求不同深度分别达线"),
    ("budget_omission_disposition",
     "预算漏展开作为性能指标/限制项/单独门槛"),
    ("allowed_evaluation_failure_rate", "允许的评测失败率"),
    ("model_call_budget_and_cost_limit", "模型调用预算和费用上限"),
    ("final_status_enumeration_and_release_semantics",
     "最终科学状态枚举和放行语义"),
)


def build_preregistration_template(*, note: str = "") -> dict:
    """预注册模板(§10.2 全字段;TBD/proposed/interface 逐项标注)。"""
    template = {
        "template_version": PPV1_PREREGISTRATION_TEMPLATE_VERSION,
        "preregistration_id": TBD,
        "approval_status": "pending_user_teacher_decision",
        "user_teacher_decision_items": {
            key: TBD for key, _ in USER_TEACHER_DECISION_ITEMS},
        "domain_definitions": {
            "dev": "B1 环境路径中间步骤题域(对外数字必须带题域标签)",
            "298": "RHEA 通用酶学题域(与 dev 双向不外推)"},
        "track_definitions": {
            "known_evidence_reconstruction": (
                "利用已公开研究来源/冻结支持重建路径;不等于泛化能力"),
            "unseen_path_inference": (
                "冻结排除范围内的有界未见推演;排除范围与允许背景"
                "知识必须评测前冻结")},
        "source_group_policy": {
            "status": PROPOSED,
            "rule": ("source_group_id 是独立性边界(不等于数据库记录 ID);"
                     "同一研究/实验系列/同菌株酶底物路线的重复记录归并"
                     "一组;原始研究身份未知 ⇒ independence=unknown,不计"
                     "独立支持,不进要求独立重复的分母")},
        "split_policy": {
            "status": PROPOSED,
            "rule": ("development/tuning/held_out/independent_confirm"
                     "ation + unseen_exclusion_manifest;划分在生成模型"
                     "输入和任何调参前完成并保存不可变清单;同 source "
                     "group 不跨集合;评测运行时只消费冻结划分清单")},
        "leakage_policy": {
            "status": PROPOSED,
            "rule": ("同 source group 跨集合 / known-unseen 直接证据"
                     "重叠 / 同研究相邻边跨集合 ⇒ 检查失败,终止,不生成"
                     "'近似无泄漏'结果")},
        "reference_graph_version": TBD,
        "identity_matching_policy": {
            "status": PROPOSED,
            "rule": ("严格结构身份=与生产同源 strict identity;CN 仅旁证"
                     "(CN 相同而严格身份不同不计严格命中);参考节点声明"
                     " identity_scope=cn_only/partial/unknown ⇒ 许可范围"
                     "封顶:内容严格相等也只作 CN 旁证,不授严格命中、"
                     "不进边严格匹配与严格指标(旁证不叠加升格;当前"
                     "实现已按此执行,最终冻结 TBD)")},
        "edge_matching_policy": {
            "status": PROPOSED,
            "rule": ("参与物**状态集合**覆盖匹配(当前实现证明范围:"
                     "不比较角色/系数,系数状态仅披露;共同产物不被"
                     "报告 K 删除;备选反应不合并;distinct occurrence"
                     " 不按 CN 合并;step_scope 不一致分轴);每个声明"
                     "必要 from/to 参考节点须有许可严格命中才可完整"
                     " strict,空命中保持未覆盖分桶不被 union 吞;"
                     "是否新增角色/系数/计量匹配轴属用户/teacher 裁定"
                     "(未裁定时按状态集合口径,最终冻结 TBD)")},
        "step_scope_policy": {
            "status": PROPOSED,
            "rule": ("net_reaction/elementary_step/multistep_summary/"
                     "unknown 不混作同一边;unknown 不冒充净反应(当前"
                     "实现披露限定:参考与事件双方均 unknown 时仍按"
                     "scope 一致计入严格档,是否单列 unknown_scope 桶"
                     "属冻结前须裁定的口径)")},
        "condition_policy": {
            "status": PROPOSED,
            "rule": ("essential 冲突/条件未知/preference 不满足/来源"
                     "条件不可映射分桶;未知不计冲突;历史来源条件保留"
                     "原文不改写;条件分类沿冻结同源规则(事实侧单位三态"
                     " canonical/source_unit_unknown/unit_mismatch、"
                     "实体/数值/异值 absence 保守语义、同键相反事实保守"
                     " unknown——known×unknown 混合按冻结侧首条已知"
                     "事实裁决(合法公共链的 unknown 事实经 checked 构造"
                     "器值清 None;直接 dataclass 绕过构造器的低层"
                     "次序差异另列 P2)、necessity 来源、适用场景阶段、"
                     "声明 value_basis 由同一实现裁决);ConditionScope →"
                     " 冻结 Requirement 的登记映射限定与缺表示能力披露"
                     "随评测契约登记;要求侧单位首消费收口:显式非规范"
                     "单位(温度 K/F)或无量纲键声明单位(物种键 mg/L)"
                     " ⇒ 无合法冻结表示 ⇒ unknown/unsupported 族并"
                     "机读保留原 unit/value/key(不做换算、不判相容或"
                     "冲突);空要求单位按键规范单位约定 canonical-"
                     "by-key 默认合法;要求侧 known_absent 无冻结"
                     "负要求表示 ⇒ 单列不判冲突(负要求语义属用户/"
                     "teacher 裁定)")},
        "unknown_partial_policy": {
            "status": PROPOSED,
            "rule": ("unknown/partial/conditional 不计 confirmed 也不"
                     "自动计错误;分母处理 TBD(用户/teacher)")},
        "endpoint_policy": {
            "status": PROPOSED,
            "rule": ("终点分类沿用 S4 四分账(unknown/metabolic_"
                     "handoff/supported_terminal_transformation_product/"
                     "supported_mineralization);bookkeeping 不单独提升"
                     "矿化;停止原因不是终点;矿化证据最低口径 TBD")},
        "denominator_policy": TBD,
        "sample_size": TBD,
        "threshold_policy": TBD,
        "confidence_interval_policy": TBD,
        "multiple_comparison_policy": TBD,
        "budget_policy": {
            "status": PROPOSED,
            "rule": ("预算漏展开单独报告,不计化学错误,不从分母无声"
                     "删除;作何处置 TBD")},
        "missing_data_policy": TBD,
        "failure_policy": TBD,
        "model_provider_policy": {
            "status": "PROPOSED_DEFAULT_OFF",
            "rule": ("真实 provider 默认关闭;无用户逐次授权时网络请求"
                     "为零、费用为零;判分零 LLM(评分程序不得调用 LLM/"
                     "不得以自然语言语义裁判/不得二次裁判覆盖程序结果)")},
        "output_write_boundary_policy": {
            "status": PROPOSED,
            "rule": ("评测输出落盘核验与写入使用同一解析后实际规范路径"
                     "(含金标产物:相对 target 基准=相对 cwd,解析后"
                     "逃出声明 repo_root/任意层 symlink 逃根 ⇒ 先拒"
                     "零新文件;未声明根 ⇒ 一律拒;仅授权 gitignored"
                     "根放行;普通非敏感写入不受限)——当前实现已按此"
                     "执行;是否追加内容 DLP/沙箱/并发防御属另行裁定")},
        "cost_limit": TBD,
        "stop_rule": TBD,
        "change_control": {
            "status": PROPOSED,
            "rule": ("冻结后任何判据/阈值/分母变更须新预注册版本 + "
                     "用户/teacher 裁定;不得据评测后结果改阈值")},
        "publication_restriction": (
            "no_release_before_freeze:冻结前不得对外发布任何 dev/298"
            "科学指标数值;对外数字必须带题域标签;工程绿数与接口验证"
            "不得写成科学性能通过(§12)"),
        "metric_interface_status": {
            metric_id: INTERFACE_ONLY for metric_id in (
                "reference_edge_recall", "key_intermediate_recall",
                "confirmed_error_rate",
                "outside_reference_unverified_edges",
                "environment_conflict_rate",
                "endpoint_mineralization_misclaim_rate",
                "depth_performance", "budget_omission")},
        "note": note or (
            "S5a 模板:全部 TBD 字段属用户/teacher 裁定;proposed 规则"
            "未冻结;接口级指标不产科学数值;冻结前不得对外发布"),
    }
    return template


def preregistration_frozen_fields(preregistration: dict) -> dict:
    """登记哪些字段已冻结/仍 TBD(§14.3 披露面;不裁定任何取值)。"""
    preregistration = preregistration or {}
    tbd_fields = sorted(
        key for key, value in preregistration.items()
        if value == TBD)
    tbd_decisions = sorted(
        key for key, value in
        (preregistration.get("user_teacher_decision_items") or {})
        .items() if value == TBD)
    proposed = sorted(
        key for key, value in preregistration.items()
        if isinstance(value, dict) and str(
            value.get("status", "")).startswith("PROPOSED"))
    return {
        "approval_status": str(
            preregistration.get("approval_status") or ""),
        "tbd_top_level_fields": tbd_fields,
        "tbd_user_teacher_decision_items": tbd_decisions,
        "proposed_rule_fields": proposed,
        "publication_restriction": str(
            preregistration.get("publication_restriction") or ""),
        "frozen": (
            not tbd_fields and not tbd_decisions
            and str(preregistration.get("approval_status") or "")
            == "approved"),
    }


def preregistration_sha256(preregistration: dict) -> str:
    """预注册文档内容 SHA-256(确定性)。"""
    return hashlib.sha256(
        canonical_json(preregistration or {}).encode("utf-8")
    ).hexdigest()


def validate_preregistration(preregistration: dict) -> dict:
    """校验预注册文档结构(不裁定取值;零冻结)。

    - template_version 未知 ⇒ 拒(fail-closed 不猜迁移);
    - approval_status 只允许 pending_user_teacher_decision /
      approved(由用户/teacher 记录,程序只核形状);
    - TBD 字段如实登记(preregistration_frozen_fields)。
    """
    if not isinstance(preregistration, dict):
        raise ValueError("预注册文档必须是对象")
    version = preregistration.get("template_version")
    if version != PPV1_PREREGISTRATION_TEMPLATE_VERSION:
        raise ValueError(
            f"预注册模板版本未知:{version!r}(当前 "
            f"{PPV1_PREREGISTRATION_TEMPLATE_VERSION};fail-closed)")
    status = str(preregistration.get("approval_status") or "")
    if status not in ("pending_user_teacher_decision", "approved"):
        raise ValueError(
            f"approval_status 非法:{status!r}(允许 "
            "pending_user_teacher_decision/approved;批准记录属用户/"
            "teacher,程序不代批)")
    return preregistration
