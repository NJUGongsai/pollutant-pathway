"""ChemicalAudit — 检查范围明确,未知不可冒充核实(v8 回修,S2)。

v9(ppv1-donor-diagnostic-9,2026-10-08 S4 回修 r3,复审 R3 唯一
阻塞 PPV1-ISO-01)相对 v8 的变化:
- **同位素变化并入实际净变化集**:冻结判据五 §5 早已把实际净变化
  定义为"键 diff ∪ 电荷/立体/同位素变化集"(冻结正文 394–396 行),
  实现缺口是 _atom_property_diffs 从未比较同位素 —— 本轮**兑现既有
  冻结承诺,不改冻结正文/判定规则**:逐原子 isotope diff 入 deltas
  (机读码 "isotope")、逐原子记录 records["isotope"]=[before,after]、
  入 changed atoms 与中心外 extra_changes/中心属性披露,audit 复算
  链(_rerun_proof_record 重跑同一 checker)自动同轴;中心外同位素
  变化按既有规则"中心外变化 ⇒ center False"处理(不再是漏核后
  verified/full/R6);
- **net_change_only_in_stereo_representation 排他理由自 v9 起为真**:
  同位素轴入图变化集后,"身份键不同而图轴无差异"的残余只能是立体
  表示差异(非四面体等 unsupported 立体轴)—— v8 前纯同位素曾被
  该码误标"仅立体"(身份轴混谈),v9 起纯同位素走真实轴(isotope
  delta + 中心范围判定),不再冒用立体码;
- 声明–执行对账(_declaration_accounting)仍只对账键变化/原子增删:
  ops 声明语言没有同位素操作(冻结 AtomTool 协议无该 op),同位素
  检出走属性 diff 披露 + 中心范围判定(strict 轴/区域轴分轴保留,
  mimo 5.3(3) 先例一致);不新增科学门、不认证实验/机制/来源真实
  性。audit/admission 决策表与理由码不变(语义变化全部由 donor-
  diagnostic-9 承载;profile 身份块随登记升 -19)。

v8(ppv1-audit-8 / ppv1-admission-8 / ppv1-donor-diagnostic-8,
2026-10-07 R8 回修)相对 v7 的变化(Codex R7 复审 R7-01):
- **直接 states 首次消费同源验证**:audit_hypothesis 对每个被消费的
  ChemicalState 对象(直接 dataclass 与 raw_structures 构建)调用
  chemstate.validate_state_object(与公共 writer 同源:raw 登记守卫 +
  raw→strict 身份一致 + 规范身份/结构事实重推导 + CN-only 专用契约)
  —— 调用方直传的 dataclass 不再绕过工厂输入守卫,篡改 raw(如
  CCO |r|、H2 挂 CC=O)的对象不再送 verified/full/R6;非法对象结构化
  拒绝,不静默清洗信息再授 full,不认证来源真伪/历史执行/机制。

v7(ppv1-audit-7 / ppv1-admission-7 / ppv1-donor-diagnostic-7,
2026-10-07 R7 回修)相对 v6 的变化(Codex R6 复审 R6-01 + R6-02B):
- **补全许可按严格结构身份注册(R6-01)**:注册计量补全规则新增许可
  边界 COMPLETION_LICENSE= composition_only_hydrogen_equivalents
  (H2/[H] 按 2[H] 组成型氢当量;按严格结构身份登记,不按名称免审);
  未登记身份的未覆盖参与物即使数值全配平 ⇒ partial(
  completion_license_unregistered_identity),不得 full/R6 —— 元素/
  电荷配平只证明组成贡献,不证明共底物初始图的键变化/连接贡献已
  核实(真实 AtomTool C→CCCO 只依次新增 C/C/O,不载入任何共底物
  初始图);detail 披露 completion_license/scope/未登记身份;正常
  氧化/还原计量补全(H2)、比例缩放、真实断裂分列/合并正控保持;
- **供体诊断原始字符串入口同源守卫(R6-02B)**:check_edit_against_
  donor 的 current/mapped/plain/target 四个原始串在解析前统一过
  chemstate 的 _guard_input_cx_classes(与工厂/strict 同源);未登记
  /并列未知 CX 项 ⇒ AuditContractError(kind=raw_input_cx_class_
  unregistered,带字段名),不再剥掉 |r| 等标记后以同 id/as_written
  参与 verified 证据(audit 复算链同守卫,proof_record 内含未登记
  项同样拒绝)。

v6(ppv1-audit-6 / ppv1-admission-6,2026-10-07 R6 回修)相对 v5 的
变化(Codex R5 复审 R5-01/08 + §4 披露项 1):
- **覆盖绑定系数/贡献 + 注册计量补全规则(R5-01)**:_center_
  evidence_binding 由"物种身份集合 + 单侧空即 full"升级为:
  λ_s(底物规模)= 反应物侧 identity==s 的系数和;覆盖产物集
  whole_molecule/fragments 两级映射;每个 covered identity 的产物侧
  声明系数总和 == λ_s × 重数(系数绑定);未覆盖参与物的元素账与
  λ_s×Δ⁺ / λ_s×(−Δ)⁺ **各自精确相等**(注册补全规则
  COVERAGE_COMPLETION_RULE = "atom_delta_stoichiometric_completion",
  不许盈余/亏空互相抵消;整类 H2/水/共底物不按名称免审);未知系数
  ⇒ coverage unknown_coefficients(中心 unknown);违反 ⇒ partial
  (前缀 partial_coverage_unchecked_transformation 保持)+ detail
  披露 coverage_rule/substrate_scale/atom_delta/两侧未覆盖元素/
  coverage_violations(系数不匹配/补全盈余/亏空,带数值);
- **镜像终态与冻结执行器同一归一(R5-08)**:_simulate_declared_
  edits 末尾把镜像终态经 MolToSmiles 序列化再 MolFromSmiles 重解析
  (映射号随序列化穿越)—— 执行器产物是被序列化后消费的,内存镜像
  残留陈旧键立体(断邻位 σ 键后双键端烯化,重解析 STEREONONE 而内存
  STEREOE)曾产生伪 undeclared_bond_change;镜像同走写出/重解析后
  与实际一致;失败/None 按原内存图(如实失配);不改冻结执行器;
- **proof_scope 与 center_match_basis 披露(§4-1/P2)**:
  check_edit_against_donor 的 evidence_payload 增 center_match_basis
  (direct|symmetric_equivalent)与 proof_scope=
  "self_contained_recompute"(自包含输入集重算可复现;不含"编辑曾
  被执行"的运行事实);audit 复算分支的 detail 增同源披露,verified
  理由码的 basis= 不再空串;_evidence_integrity_mismatches 增
  center_match_basis 比对(自报 ≠ 复算 ⇒ integrity 拒)。

v5(ppv1-audit-5 / ppv1-admission-5,2026-10-07 R5 回修)相对 v4 的
变化(Codex R4 复审 R4-01/02/06/07 + §4):
- **证据证明链内部重算(R4-01)**:center_evidence 携带 proof_record
  (诊断完整输入集)⇒ audit **复跑**确定性 checker,自报轴/绑定
  字段须与复算值一致(不一致 ⇒ 结构化拒绝,kind=center_evidence_
  integrity_mismatch);类型契约(Center_match/strict 须 bool|None
  等)违约 ⇒ 结构化拒绝(kind=center_evidence_type_violation)——
  字符串'false'/整数 0/空容器不再绕过 is False/is None;无
  proof_record ⇒ unknown(两条身份字符串/六条自报字段不构成证明);
- **产物集合覆盖(R4-01)**:绑定核验按复算的底物/产物身份做**整
  分子或碎片**两级映射(真实断裂的分列产物正确绑定);未覆盖产物
  与未覆盖共底物同时存在 ⇒ 部分覆盖 ⇒ unknown(额外未核实转化
  不得借一个产物达 all_verified);区域与 strict 分轴保留;
- **input_hash 补有限规则诊断与证明记录哈希(R4-02)**:
  finite_rule_diagnostic(实际审核入参)与 proof_record/bound_
  inputs 的 content_hash 入 fingerprint —— not_run(合法 NA)与
  diagnostic_only(unknown/retain)不再同 hash;
- **audit.scope 遮蔽修复(§4)**:证据门的局部 checker scope 变量
  不再覆盖函数 scope 参数(audit.scope/audit_id 如实反映调用方
  范围,如 'synthetic:review-scope');
- **镜像活 ID 表 + 前置复核(R4-06)**:_simulate_declared_edits
  维护顺序执行后的 ID 状态(先增后引合法,与执行器一致)并逐操作
  复核协议前置(键存在/不存在、from_order == 时点键级)——失败为
  结构化机读码(declared_precondition_violated:*),错误 from_order
  不再零失配通过;不改冻结执行器;
- **键级立体入变化集(R4-07)**:_bond_changes 增 bond_stereo_change
  (映射原子对的 E/Z 几何 diff;入声明对账签名——ops 声明语言无
  E/Z ⇒ 执行图带未声明立体变化即失配);身份不同而图轴空 ⇒ 理由
  net_change_only_in_stereo_representation,不得称"实际净变化为空";
- **非四面体公开列项(R4-07)**:_stereo_config_delta 先判标签类型
  (非四面体 ⇒ unsupported,不再返回"构型保持");stereo_
  comparison_unsupported_atoms 公开清单;中心外存在 unsupported
  立体轴 ⇒ center 不可判 True;联合映射对增强组与非四面体标签
  均 unsupported(useChirality 只覆盖四面体标签);
- 声明对账支持的立体范围声明扩为三类(全指定/无手性骨架/部分或
  全未指定——按所写表示,mimo probe3);一个 useChirality 开关
  不证明全范围。

v3(ppv1-audit-3 / ppv1-admission-3,2026-10-06 R3 回修)相对 v2 的变化
(Codex R2 复审 R2-01/02/03/12 + mimo R2 §3/5 采纳边界):
- **必需检查覆盖(R2-01)**:admission 的 R6"全部核实"要求全部必需
  适用检查被实际执行且 verified —— 窄 audit_scope 只是诊断(缺覆盖
  ⇒ R5c 不 expand);真正语义不适用的项(如关闭的有限规则诊断、
  multistep 汇总边)可 NA 但须带理由;**因缺输入而未执行的检查记
  unknown(reason=*_not_run),不得记 not_applicable**(context 缺失 ⇒
  condition_check=unknown(condition_assessment_not_run),mimo 3.2(1));
- **缺参与物 state 不崩溃(R2-01)**:悬空 state 引用单列
  participant_state_refs 检查(violated/participant_state_missing),
  parse 检查记 unknown(不能核),受影响后续项 unknown +
  prerequisite_failed_not_run;admission 走 **R1b** 拒绝(账本/引用
  完整性问题,不压平成 R1"结构不可解析",mimo 3.2(2));
- **变换中心不采信自报签名(R2-01/5.3)**:
  transformation_signature_status=verified 只是声明;检查 verified 须
  供 center_evidence(注册版本化确定性 checker 的输出,如供体诊断),
  缺证据 ⇒ unknown(center_evidence_missing)——"verified 不得靠模型
  或调用方字符串";
- **R5d 触发集合显式限定**(mimo 3.2(4)):{element_accounting,
  formal_charge_accounting};其他 violated 走 R5v declared_violated_
  other,不冒称"声明账不一致";
- **input_hash 覆盖实际科学输入**(R2-07):hypothesis 完整语义载荷
  (含 requirements/assumptions/dependency_refs)、参与物 state 身份、
  context 身份、audit_scope、checker 版本 —— 不把一个引用 ID 当完整
  输入证明;
- **供体诊断实际净变化**(R2-03):判定基础 = 实际变化集(键 diff ∪
  原子增删 ∪ 逐原子形式电荷/氢数/立体 diff),声明的编辑原子单独列
  declaration_only 不参与判定;零净变化 ⇒ center=unknown
  (no_executed_change) 永不 True;声明–执行一致性对账
  (declaration_mismatches);symmetric_equivalent 须由**联合图映射**
  (整个中心集合存在单一自同构像)证明,单原子对称轨道不冒充;
  extra_changes 补 ΔH 与 Δ立体;plain 产物与 mapped 图对账;
- **冻结门禁逐产物拒绝真实消费(R2-12)**:decide_admission 消费
  mapper 的 per_product_verdicts —— 全部共同产物被拒 ⇒ reject,
  部分 ⇒ retain_conditional(被拒产物保留拒因、不可展开),不删除
  被拒共同产物凑合法事件,不改冻结门禁真假;消费开关由策略显式
  版本化(per_product_gate_consumption);
- **身份保真分轴呈现**(mimo 1.4(4)):参与物任一保真轴非
  as_written ⇒ identity_fidelity=unknown(列轴),不再
  verified+reason 注记混读;
- **元素账口径注记**(mimo 2.2(a)):D/T 并入元素 H(同位素不入
  本账)、自由基电子不入账;verified 仅指元素与形式电荷数值闭合;
  radical 保真轴为已知缺口(身份层区分自由基,本轴未实现);
- **omission 模式结构化**(mimo 2.3(2)):omission_pattern_matches
  为结构化字段 {pattern, excess_on, missing_from, element_delta};
  H+ 模式输出名 H+_count1(仅 H 计数 1 的模式名,不含质子/电子计量)。

未落地条款(contract clause, implementation pending,不得当已检查):
local_delta(局部结构差,S3/展示层)、edge_kind(互变/质子化边,S3)、
cn_identity 的 basis: scoring_key 标记(S3)。完整供体变换模板的
供体侧预期键变化对比留 S3 接线;当前诊断命名:**实际净变化区域
诊断**,不冒充完整变换一致。

v2(ppv1-audit-2,2026-10-05 回修)的变化:全氢元素账(F01);电荷账
fidelity 前提(F05);CN-only 非结构非法(F05);结构化差值(F01);
ambiguous 参与物阻止完整账(F01);violated/unknown 分码(P2-1);
R2b(mimo 3.2(1));旧门禁版本化 mapper(P2-2)。

既有不变量(§8):必需分项;依赖解析的后续项 unknown +
prerequisite_failed_not_run;完整已知参与物和系数才核全账;不先
中和再验;不自动补水/氧/辅酶;元素及电荷账核实 ≠ 机制/电子转移/
热力学/速率已核实(biological_support_status 另轴);G2 仅旧规则
诊断(unclassified=覆盖未知不惩罚);诊断状态与展开决定分开;
unknown 不自动 reject。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction

from rdkit import Chem, RDLogger

from ..domain.models import content_hash, stable_id
from .chemstate import (
    FIDELITY_AS_WRITTEN,
    STRUCTURE_ORIGIN_LEGACY_CN_ONLY,
    ChemicalState,
    ChemicalStateError,
    _guard_input_cx_classes,
    build_chemical_state,
    strict_identity_of,
    validate_state_object,
)
from .hypothesis import (
    COEFFICIENT_KNOWN,
    PARTICIPANT_SIDE_PRODUCT,
    PARTICIPANT_SIDE_REACTANT,
    ReactionHypothesis,
)
from .path_context import (
    PathContext,
    assess_candidate_conditions,
    validate_context_object,
)
from .profile import (
    LEGACY_G2_FAMILY_REF,
    PPV1_ADMISSION_POLICY_VERSION,
    PPV1_AUDIT_SCHEMA_VERSION,
    PPV1_CHEMSTATE_SCHEMA_VERSION,
    PPV1_CONDITION_ASSESSMENT_VERSION,
    PPV1_DONOR_DIAGNOSTIC_VERSION,
    PPV1_GATE_MAPPER_VERSION,
    PPV1_HYPOTHESIS_SCHEMA_VERSION,
)

RDLogger.DisableLog("rdApp.*")

CHECK_STRUCTURE_PARSE_VALENCE = "structure_parse_valence"
CHECK_IDENTITY_FIDELITY = "identity_fidelity"
CHECK_FINITE_RULE_DIAGNOSTIC = "finite_rule_diagnostic"
CHECK_PARTICIPANT_COMPLETENESS = "participant_completeness"
CHECK_PARTICIPANT_STATE_REFS = "participant_state_refs"
CHECK_ELEMENT_ACCOUNTING = "element_accounting"
CHECK_FORMAL_CHARGE_ACCOUNTING = "formal_charge_accounting"
CHECK_TRANSFORMATION_CENTER = "transformation_center"
CHECK_STEP_SCOPE = "step_scope_check"
CHECK_CONDITION_CHECK = "condition_check"
CHECK_PROVENANCE_DEPENDENCY = "provenance_dependency"
REQUIRED_CHECK_NAMES = (
    CHECK_STRUCTURE_PARSE_VALENCE, CHECK_IDENTITY_FIDELITY,
    CHECK_FINITE_RULE_DIAGNOSTIC, CHECK_PARTICIPANT_COMPLETENESS,
    CHECK_PARTICIPANT_STATE_REFS, CHECK_ELEMENT_ACCOUNTING,
    CHECK_FORMAL_CHARGE_ACCOUNTING, CHECK_TRANSFORMATION_CENTER,
    CHECK_STEP_SCOPE, CHECK_CONDITION_CHECK,
    CHECK_PROVENANCE_DEPENDENCY,
)
# R5d(声明账 violated)的显式触发集合(mimo 3.2(4):其他 violated
# 用 R5v 独立码,防止将来新增检查静默挂进"声明账不一致")
R5D_TRIGGER_CHECKS = frozenset({CHECK_ELEMENT_ACCOUNTING,
                                CHECK_FORMAL_CHARGE_ACCOUNTING})
# 语义 NA 白名单(真不适用,允许在 R6 覆盖核算中缺席;缺输入未执行
# 不在此列 —— 那些必须 unknown)。键:检查名;值:允许的 reason 片段。
SEMANTIC_NA_ALLOWED = {
    CHECK_FINITE_RULE_DIAGNOSTIC: (
        "not_provided", "legacy_g2_diagnostic_reference",
        "input_preview_diagnostic_only_coverage_limited",
        "input_preview_off"),
    CHECK_STEP_SCOPE: ("multistep_summary_kept_as_summary_edge",),
}

# 变换中心检查接受证据的注册确定性 checker 版本(R2-01:自报签名/
# 模型字符串不是检查结果;其他注册 checker 须独立列项评审后加入)
CENTER_CHECKER_REGISTRY = frozenset({PPV1_DONOR_DIAGNOSTIC_VERSION})
# 注册 checker 的已声明检查范围(R3-01:限定区域 checker 不冒充完整
# 供体变换模板验证 —— full_template 预留 S3 独立注册)
CENTER_CHECKER_SCOPES = frozenset({
    # 区域级:实际净变化是否局限于对齐中心(或其保手性联合对称像);
    # 含声明–执行净效应对账与 strict 产物比对轴 —— 不是完整模板一致
    "region_net_change",
})

# R6(R5-01):证据覆盖绑定的**注册计量补全规则**(detail 的
# coverage_rule 字段披露此名)。语义:设 s=复算底物身份、p=复算产物
# 身份(可为点分碎片串)、λ_s=反应物侧 identity==s 的参与物系数和、
# Δ=elements(s)−elements(p)(逐元素 Fraction):
# - Σ 未覆盖产物元素(系数加权)== λ_s × Δ⁺(被核实转化释放的原子);
# - Σ 未覆盖反应物元素 == λ_s × (−Δ)⁺(被核实转化消耗的原子);
# - 两侧各自精确相等,不许盈余/亏空互相抵消。未覆盖参与物/贡献由此
#   规则核实后才能计入覆盖;元素账整体平衡仍归 element_accounting
#   独立轴,不在此重复。整类共底物/共产物(如 H2、水)不按名称免审。
COVERAGE_COMPLETION_RULE = "atom_delta_stoichiometric_completion"
# R7(R6-01):补全规则的**许可范围**按严格结构身份注册 —— 数值配平
# (元素/形式电荷账闭合)只证明参与物的**组成**贡献,不证明其初始分子
# 图的键变化/连接贡献已核实(真实 AtomTool C→CCCO 只依次新增 C/C/O,
# 不载入任何共底物初始图;C+CC=O/C+C1CO1/C+C=C O→CCCO 三个 C2H4O
# 异构体数值上都能补足同一 Δ,补全规则不区分 ⇒ 不得据此授 full/R6)。
# 登记许可:组合型氢当量(H2 对 2[H] 的 composition-only 作用域说明;
# 含 [H] 原子氢 —— radical 保真轴为已登记缺口,氢当量作用域内不因此
# 另拒,亦不新增电子/自由基轴)。按**严格结构身份**(smiles_isomeric)
# 登记,不按整类名称免审;未登记身份的未覆盖参与物(即使数值配平)
# ⇒ partial(completion_license_unregistered_identity),机器披露实际
# 证明范围;正常氧化/还原明确计量补全(H2)、比例缩放、真实断裂
# 分列/合并的正控保持。许可边界变化待审(mimo v7 请求判据三)。
COMPLETION_LICENSE = "composition_only_hydrogen_equivalents"
COMPLETION_LICENSED_IDENTITIES = frozenset({
    "[H][H]",        # H2 —— 2[H] 组成型氢当量
    "[H] |^1:0|",    # 原子氢(基)—— 同上;不新增自由基保真轴
})
# 覆盖绑定结论中"部分覆盖/覆盖不可算"两族理由前缀(区别于"证据未
# 绑定本假设"族):partial ⇒ 未核实转化存在;unknown_coefficients ⇒
# 覆盖规模不可算 —— 两者都进中心 unknown、不 R6,但理由不冒充绑定失败
_COVERAGE_PARTIAL_PREFIX = "center_evidence_partial_coverage"
_COVERAGE_UNKNOWN_COEFF_PREFIX = "center_evidence_coverage_unknown_"

CHECK_VERIFIED = "verified"
CHECK_VIOLATED = "violated"
CHECK_UNKNOWN = "unknown"
CHECK_NOT_APPLICABLE = "not_applicable"
PREREQUISITE_FAILED = "prerequisite_failed_not_run"
STRUCTURE_UNAVAILABLE = "structure_unavailable_not_run"

ADMISSION_EXPAND = "expand"
ADMISSION_RETAIN_CONDITIONAL = "retain_conditional"
ADMISSION_DEFER = "defer"
ADMISSION_REJECT = "reject"
ADMISSION_DISPOSITIONS = frozenset({ADMISSION_EXPAND,
                                    ADMISSION_RETAIN_CONDITIONAL,
                                    ADMISSION_DEFER, ADMISSION_REJECT})

# admission 决策表里的活动门禁名(引用 frozen_hit60_gate,不修改其真假)
GATE_NAME_DIRECTION_SOURCE = "gate_direction_source"
GATE_NAME_RECORDED_ELIGIBILITY = "gate_recorded_eligibility"
GATE_NAME_SMILES = "gate_smiles"
DEFAULT_REJECT_GATES = frozenset({GATE_NAME_DIRECTION_SOURCE,
                                  GATE_NAME_RECORDED_ELIGIBILITY,
                                  GATE_NAME_SMILES})

# 元素缺口与常见漏项模式的数值相符(Codex 收紧版:仅数值相符,
# 不证明缺项原因,不含电子/质子计量推断)
COMMON_OMISSION_PATTERNS: dict[str, dict[str, Fraction]] = {
    "H2O": {"H": Fraction(2), "O": Fraction(1)},
    "H+": {"H": Fraction(1)},
    "O2": {"O": Fraction(2)},
    "2H": {"H": Fraction(2)},
}


class AuditContractError(RuntimeError):
    """审计输入/策略契约违反(结构化 fail-closed)。"""

    def __init__(self, message: str, detail: dict | None = None):
        super().__init__(message)
        self.detail = detail or {}


# ---------------------------------------------------------------- 检查对象


@dataclass
class AuditCheck:
    """单项检查(name/status/reason_code/evidence/coverage/detail)。

    detail(v2):机器可读的结构化输出 —— 元素/电荷账的逐元素 Δ 向量、
    缺口模式数值相符、核算范围等(F01 验收"可机器读取的差值")。
    """

    name: str
    status: str                 # verified | violated | unknown | not_applicable
    reason_code: str = ""
    evidence_refs: list[str] = field(default_factory=list)
    coverage: str = ""          # 覆盖说明(如 only_legacy_rules)
    detail: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return dict(self.__dict__)


@dataclass
class ChemicalAudit:
    """§8 全字段;audit_id 由内容派生(幂等)。"""

    audit_id: str
    scope: str
    input_hash: str
    checks: list[AuditCheck] = field(default_factory=list)
    legacy_gate_result_ref: str = ""
    participant_accounting_status: str = "unknown"   # full|partial|unknown
    biological_support_status: str = "unknown"       # supported|inferred|unknown
    admission_disposition: str = ""
    admission_policy_ref: str = PPV1_ADMISSION_POLICY_VERSION
    admission_reasons: list[str] = field(default_factory=list)
    checker_versions: dict = field(default_factory=dict)
    schema_version: str = PPV1_AUDIT_SCHEMA_VERSION

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "audit_id": self.audit_id,
            "scope": self.scope,
            "input_hash": self.input_hash,
            "checks": [c.to_dict() for c in self.checks],
            "legacy_gate_result_ref": self.legacy_gate_result_ref,
            "participant_accounting_status":
                self.participant_accounting_status,
            "biological_support_status": self.biological_support_status,
            "admission_disposition": self.admission_disposition,
            "admission_policy_ref": self.admission_policy_ref,
            "admission_reasons": list(self.admission_reasons),
            "checker_versions": dict(self.checker_versions),
        }

    def check_status(self, name: str) -> str:
        for c in self.checks:
            if c.name == name:
                return c.status
        return CHECK_NOT_APPLICABLE

    def violated_checks(self) -> list[AuditCheck]:
        return [c for c in self.checks if c.status == CHECK_VIOLATED]


def _mol_of(state: ChemicalState | None):
    if state is None or not state.smiles_isomeric:
        return None
    return Chem.MolFromSmiles(state.smiles_isomeric)


def element_counts_full(mol: Chem.Mol) -> dict[str, Fraction]:
    """全部氢计入的元素组成(F01:隐式/显式属性氢/独立氢顶点不重不漏)。

    - 重原子按 symbol 计数;其氢 = GetTotalNumHs()(隐式+显式属性,
      不含独立顶点邻居氢,避免与独立 [H] 顶点重复);
    - 独立氢顶点([H])自身按 H 计数。
    """
    counts: dict[str, Fraction] = {}
    for atom in mol.GetAtoms():
        symbol = atom.GetSymbol()
        counts[symbol] = counts.get(symbol, Fraction(0)) + Fraction(1)
        if symbol != "H":
            n_h = atom.GetTotalNumHs()  # 隐式+显式属性氢
            if n_h:
                counts["H"] = counts.get("H", Fraction(0)) + Fraction(n_h)
    return {k: v for k, v in counts.items() if v != 0}


# ---------------------------------------------------------------- 审计函数


def audit_hypothesis(
    hypothesis: ReactionHypothesis,
    *,
    run_id: str = "",
    scope: str = "hypothesis_admission",
    states: dict[str, ChemicalState] | None = None,
    raw_structures: dict[str, str] | None = None,
    context: PathContext | None = None,
    audit_scope: set[str] | None = None,
    legacy_gate_result: dict | None = None,
    finite_rule_diagnostic: dict | None = None,
    unresolved_dependency_ids: list[str] | None = None,
    center_evidence: dict | None = None,
) -> ChemicalAudit:
    """§7.1 固定接口:hypothesis × audit_scope × policy → ChemicalAudit。

    - states 优先;缺项时从 raw_structures 现场构建(F07:state_ref 与
      构建出的实际身份不一致即拒绝);
    - 参与物 state 引用悬空(**账本/引用完整性问题,非结构非法**,
      R2-01):单列 participant_state_refs 检查 violated
      (participant_state_missing),parse 检查记 unknown(不能核),
      受影响后续项 unknown + prerequisite_failed_not_run,不崩溃;
    - CN-only 状态(F05)不判结构非法:parse 检查 unknown +
      structure_unavailable_legacy_cn_only;
    - context 缺失 ⇒ condition_check=unknown
      (condition_assessment_not_run)—— 缺输入未执行不是语义不适用
      (R2-01/mimo 3.2(1)),不得记 not_applicable;context 提供时经
      **候选级评估**(assess_candidate_conditions:旧边路线快照 +
      本候选新增要求在当前作用域,R3-06),不再拿当前事实重评全部
      累积要求;
    - center_evidence(R2-01/R3-01):注册版本化确定性 checker(见
      CENTER_CHECKER_REGISTRY/CENTER_CHECKER_SCOPES)的变换中心
      证据,**须绑定本假设**(bound_inputs 的底物/产物身份与被审
      参与物核对);自报 transformation_signature_status 不是检查
      结果;strict 轴(False ⇒ violated;未核实 ⇒ unknown)一并
      消费,适用失败不消失于 all_verified;
    - admission 不在此决定(见 decide_admission;状态与展开分开)。
    """
    if context is not None:
        # R3-08:直接对象的缺/未来 context 版本 ⇒ 结构化拒绝
        # (from_dict 门早已存在;此处覆盖"直接对象到 R6"的绕过)
        validate_context_object(context)
    states = dict(states or {})
    for ref, structure in (raw_structures or {}).items():
        if ref not in states:
            built = build_chemical_state(structure, "source_product")
            if built.state_id != ref:
                raise AuditContractError(
                    "raw_structures 的 state_ref 与结构实际身份不一致"
                    "(不得以其他分子冒充)",
                    {"state_ref": ref, "actual_state_id": built.state_id})
            states[ref] = built
    # R7-01/R8:直接 dataclass 对象与恢复对象共用与公共 writer 同源的
    # 纯状态验证(与 from_dict 同一验证源)—— 工厂入口的输入守卫不因
    # "对象已构造"而豁免;篡改 raw(未登记 CX 项/跨分子)的对象在首次
    # 消费即结构化拒绝(ChemicalStateError),不再进入 verified/R6;
    # 不静默清洗信息再授 full。CN-only 合法未知保持诚实 unknown。
    for ref in sorted(states):
        validate_state_object(states[ref])
    requested = set(audit_scope or REQUIRED_CHECK_NAMES)

    checks: list[AuditCheck] = []
    versions = {
        "audit": PPV1_AUDIT_SCHEMA_VERSION,
        "chemstate": PPV1_CHEMSTATE_SCHEMA_VERSION,
        "hypothesis": PPV1_HYPOTHESIS_SCHEMA_VERSION,
        "condition_assessment": PPV1_CONDITION_ASSESSMENT_VERSION,
        "donor_diagnostic": PPV1_DONOR_DIAGNOSTIC_VERSION,
        "legacy_g2_family": LEGACY_G2_FAMILY_REF,
    }
    # ---- ① 结构解析/价态(CN-only ≠ 非法,F05;悬空引用 ≠ 语法非法) ----
    parse_ok = True
    structure_unavailable = False  # CN-only 等合法缺结构:unknown 不是 violated
    missing_state_refs: list[str] = []
    for p in hypothesis.participants:
        if p.state_ref not in states:
            missing_state_refs.append(p.state_ref)
    if missing_state_refs:
        # 悬空 state 引用:账本/引用完整性问题(R2-01)。parse 检查不能
        # 核(unknown),单列 violated 检查供 admission R1b 拒绝;后续
        # 依赖结构的检查 unknown + prerequisite_failed_not_run。
        parse_ok = False
        checks.append(AuditCheck(
            name=CHECK_STRUCTURE_PARSE_VALENCE, status=CHECK_UNKNOWN,
            reason_code="participant_state_missing"
                        "(引用悬空,结构无法核,非语法非法)",
            evidence_refs=sorted(missing_state_refs)[:10],
            coverage="participants_with_state"))
        checks.append(AuditCheck(
            name=CHECK_PARTICIPANT_STATE_REFS, status=CHECK_VIOLATED,
            reason_code="participant_state_missing",
            evidence_refs=sorted(missing_state_refs)[:10],
            coverage="state_ledger_references"))
    else:
        unparseable = [p.state_ref for p in hypothesis.participants
                       if states[p.state_ref].smiles_isomeric == ""
                       and states[p.state_ref].structure_origin
                       != STRUCTURE_ORIGIN_LEGACY_CN_ONLY]
        cn_only = [p.state_ref for p in hypothesis.participants
                   if states[p.state_ref].structure_origin
                   == STRUCTURE_ORIGIN_LEGACY_CN_ONLY]
        if unparseable:
            parse_ok = False
            checks.append(AuditCheck(
                name=CHECK_STRUCTURE_PARSE_VALENCE, status=CHECK_VIOLATED,
                reason_code="unparseable_smiles",
                evidence_refs=sorted(unparseable)[:10],
                coverage="participants_with_state"))
        elif cn_only:
            structure_unavailable = True
            checks.append(AuditCheck(
                name=CHECK_STRUCTURE_PARSE_VALENCE, status=CHECK_UNKNOWN,
                reason_code="structure_unavailable_legacy_cn_only"
                "(合法投影缺原始结构,非结构化学非法)",
                evidence_refs=sorted(cn_only)[:10],
                coverage="participants_with_state"))
        else:
            checks.append(AuditCheck(
                name=CHECK_STRUCTURE_PARSE_VALENCE, status=CHECK_VERIFIED,
                reason_code="all_participants_parse",
                coverage="participants_with_state"))
        # 引用齐全时,状态引用检查 verified(账本完整性轴,与 parse
        # 分轴;同 parse ①不进 scope 门 —— 纯账本检查,不可被窄 scope
        # 诊断跳过)
        checks.append(AuditCheck(
            name=CHECK_PARTICIPANT_STATE_REFS, status=CHECK_VERIFIED,
            reason_code="all_participant_states_resolved",
            coverage="state_ledger_references"))

    prerequisite_failed = not parse_ok  # violated:后续 not_run

    def _dependent(name: str, coverage: str) -> AuditCheck:
        reason = (PREREQUISITE_FAILED if prerequisite_failed
                  else STRUCTURE_UNAVAILABLE)
        return AuditCheck(name=name, status=CHECK_UNKNOWN,
                          reason_code=reason, evidence_refs=[],
                          coverage=coverage)

    # ---- ② 身份信息保真(分轴呈现,mimo 1.4(4)) ----
    if CHECK_IDENTITY_FIDELITY in requested:
        if prerequisite_failed or structure_unavailable:
            checks.append(_dependent(CHECK_IDENTITY_FIDELITY, "state_ids"))
        else:
            axis_notes = []
            for p in hypothesis.participants:
                st = states.get(p.state_ref)
                if st is None:
                    continue
                if st.structure_origin == STRUCTURE_ORIGIN_LEGACY_CN_ONLY:
                    axis_notes.append(f"cn_only:{p.state_ref}")
                fidelity = st.representation_fidelity or {}
                for axis, value in sorted(fidelity.items()):
                    if value != FIDELITY_AS_WRITTEN:
                        axis_notes.append(
                            f"{p.state_ref}:{axis}={value}")
            checks.append(AuditCheck(
                name=CHECK_IDENTITY_FIDELITY,
                status=(CHECK_UNKNOWN if axis_notes
                        else CHECK_VERIFIED),
                reason_code=("identity_fidelity_axes_not_as_written:"
                             + ";".join(axis_notes[:20])
                             if axis_notes
                             else "identity_states_consistent"),
                coverage="state_ids",
                detail={"fidelity_axis_notes": axis_notes[:50]}))

    # ---- ③ 冻结有限规则诊断(真正语义 NA:关闭/未提供的旧诊断) ----
    if CHECK_FINITE_RULE_DIAGNOSTIC in requested:
        diag = finite_rule_diagnostic or {"status": "not_run",
                                          "reason": "not_provided"}
        status = CHECK_NOT_APPLICABLE if diag.get("status") == "not_run" \
            else CHECK_UNKNOWN
        reason = diag.get("reason", "")
        if diag.get("status") in ("diagnostic_only", "hold_reported"):
            reason = "input_preview_diagnostic_only_coverage_limited"
        checks.append(AuditCheck(
            name=CHECK_FINITE_RULE_DIAGNOSTIC, status=status,
            reason_code=reason or "legacy_g2_diagnostic_reference",
            evidence_refs=[LEGACY_G2_FAMILY_REF],
            coverage="only_legacy_rules_H_O_free_fragment_counts"))

    # ---- ④ 参与物完整度(ambiguous 阻止 full,F01) ----
    status_list = hypothesis.participant_list_status
    all_known_coeffs = all(p.coefficient_status == COEFFICIENT_KNOWN
                           for p in hypothesis.participants)
    if CHECK_PARTICIPANT_COMPLETENESS in requested:
        if prerequisite_failed or structure_unavailable:
            checks.append(_dependent(CHECK_PARTICIPANT_COMPLETENESS,
                                     "participant_list"))
        elif hypothesis.ambiguous_participants:
            checks.append(AuditCheck(
                name=CHECK_PARTICIPANT_COMPLETENESS, status=CHECK_UNKNOWN,
                reason_code="ambiguous_duplicate_participants_not_summed"
                "(未确认并列计量的重复参与物不得授予完整账)",
                coverage="participant_list"))
        elif status_list in ("source_complete", "declared_complete"):
            checks.append(AuditCheck(
                name=CHECK_PARTICIPANT_COMPLETENESS,
                status=(CHECK_UNKNOWN if not all_known_coeffs
                        else CHECK_VERIFIED),
                reason_code=("coefficients_unknown_declared_complete"
                             if not all_known_coeffs
                             else "declared_complete_with_known_coefficients"),
                coverage="participant_list"))
        else:
            checks.append(AuditCheck(
                name=CHECK_PARTICIPANT_COMPLETENESS, status=CHECK_UNKNOWN,
                reason_code=f"participant_list_status:{status_list}",
                coverage="participant_list"))

    # ---- ⑤⑥ 元素/形式电荷核算(全氢 + 电荷轴前提 + 结构化差值) ----
    full_known = (
        hypothesis.participant_list_status in ("source_complete",
                                               "declared_complete")
        and all_known_coeffs
        and not hypothesis.ambiguous_participants)
    reactant_side = [p for p in hypothesis.participants
                     if p.side == PARTICIPANT_SIDE_REACTANT]
    product_side = [p for p in hypothesis.participants
                    if p.side == PARTICIPANT_SIDE_PRODUCT]
    if CHECK_ELEMENT_ACCOUNTING in requested:
        if prerequisite_failed or structure_unavailable:
            checks.append(_dependent(CHECK_ELEMENT_ACCOUNTING,
                                     "full_balance"))
        elif full_known:
            elem_check = _element_accounting(
                reactant_side, product_side, states)
            checks.append(elem_check)
        else:
            checks.append(AuditCheck(
                name=CHECK_ELEMENT_ACCOUNTING, status=CHECK_UNKNOWN,
                reason_code="partial_or_unknown_participants_full_balance"
                            "_unknown",
                coverage="full_balance",
                detail={"accounting_scope": "not_run_incomplete_list"}))
    if CHECK_FORMAL_CHARGE_ACCOUNTING in requested:
        # 电荷轴前提(F05/mimo C1)优先:参与物原始电荷不可知(含 CN-only
        # 的中和形)⇒ unknown(original_charge_unavailable),不拿中和后
        # 电荷算假通过 —— 该判定先于"结构不可用"笼统归因。
        # R2-01:悬空引用不在此崩溃(states.get 可为 None),账本轴由
        # participant_state_refs 检查承接。
        charge_unavailable = [
            p.state_ref for p in hypothesis.participants
            if (states.get(p.state_ref) is not None
                and (states[p.state_ref].representation_fidelity or {})
                .get("formal_charge") != FIDELITY_AS_WRITTEN)]
        if full_known and charge_unavailable:
            checks.append(AuditCheck(
                name=CHECK_FORMAL_CHARGE_ACCOUNTING, status=CHECK_UNKNOWN,
                reason_code="original_charge_unavailable"
                "(CN/中和形输入的电荷账不可算,不得拿中和后电荷算)",
                evidence_refs=charge_unavailable[:10],
                coverage="full_balance"))
        elif prerequisite_failed or structure_unavailable:
            checks.append(_dependent(
                CHECK_FORMAL_CHARGE_ACCOUNTING, "full_balance"))
        elif full_known:
            checks.append(_charge_accounting(
                reactant_side, product_side, states))
        else:
            checks.append(AuditCheck(
                name=CHECK_FORMAL_CHARGE_ACCOUNTING, status=CHECK_UNKNOWN,
                reason_code="partial_or_unknown_participants_full_balance"
                            "_unknown",
                coverage="full_balance"))

    # ---- ⑦ 映射/变换中心(证据门:自报签名不是检查结果,R2-01;
    # v4 证据绑定本反应 + strict 轴消费 + checker scope,R3-01;
    # v5 证明链内部重算 + 类型契约 + 产物集合覆盖,R4-01) ----
    def _evidence_binding_detail(evidence: dict, problem: str) -> dict:
        bound = evidence.get("bound_inputs") or {}
        return {"problem": problem,
                "substrate_identity": bound.get("substrate_identity", ""),
                "product_identity": bound.get("product_identity", ""),
                "edits_signature": bound.get("edits_signature", ""),
                "checker_scope": evidence.get("checker_scope", "")}

    def _evidence_type_violation(evidence: dict) -> str:
        """证据载荷类型契约(R4-01:字符串'false'/整数0/空容器绕过
        is False/is None ⇒ 曾直达 R6;表示违约结构化拒绝,不是化学
        未知)。返回违约描述或空串。"""
        for field_name in ("center_match", "strict_target_match"):
            value = evidence.get(field_name)
            if value is not None and not isinstance(value, bool):
                return f"{field_name}:{type(value).__name__}={value!r}"
        if not isinstance(evidence.get("declaration_mismatch", False),
                          bool):
            return (f"declaration_mismatch:"
                    f"{type(evidence.get('declaration_mismatch')).__name__}")
        bound = evidence.get("bound_inputs")
        if bound is None:
            return ""
        if not isinstance(bound, dict):
            return f"bound_inputs:{type(bound).__name__}"
        for key in ("substrate_identity", "product_identity",
                    "edits_signature", "alignment_ref",
                    "execution_fingerprint"):
            value = bound.get(key)
            if value is not None and not isinstance(value, str):
                return f"bound_inputs.{key}:{type(value).__name__}"
        centers = bound.get("donor_centers")
        if centers is not None and (
                not isinstance(centers, list)
                or not all(isinstance(x, str) for x in centers)):
            return f"bound_inputs.donor_centers:{type(centers).__name__}"
        record = evidence.get("proof_record")
        if record is not None and not isinstance(record, dict):
            return f"proof_record:{type(record).__name__}"
        return ""

    def _rerun_proof_record(proof: dict) -> DonorConsistencyDiagnostic:
        """证明记录 → 复跑确定性诊断(R4-01:内部重算建立证明链)。

        proof_record 是 check_edit_against_donor 的完整输入集
        (current/donor/alignment/expectation/result/edits)——audit
        在此**重跑**同一确定性 checker,得到可核验的轴结论与绑定
        输入;诊断对契约违约的 AuditContractError 原样上抛(结构化)。
        """
        missing_keys = [key for key in ("current", "donor", "alignment",
                                        "expectation", "result")
                        if not isinstance(proof.get(key), dict)]
        if missing_keys or not isinstance(proof.get("edits"), list):
            raise AuditContractError(
                "center_evidence 的 proof_record 形状不完整(须携带"
                "current/donor/alignment/expectation/result 全部 dict"
                "与 edits list —— 诊断完整输入集)",
                {"kind": "center_evidence_proof_record_invalid",
                 "missing": missing_keys,
                 "edits_type": type(proof.get("edits")).__name__})
        return check_edit_against_donor(
            current=dict(proof["current"]), donor=dict(proof["donor"]),
            alignment=dict(proof["alignment"]),
            expectation=dict(proof["expectation"]),
            result=dict(proof["result"]),
            edits=list(proof["edits"]))

    def _evidence_integrity_mismatches(
            evidence: dict, recomputed: dict) -> list[str]:
        """自报轴/绑定字段 vs 复算值(R4-01:改真实诊断的任一绑定
        字段不得仅换 input_hash 后照常 verified;R6/P2:自报 basis ≠
        复算 basis(如声称 direct 实为 symmetric_equivalent)同样拒绝)。"""
        out: list[str] = []
        for key in ("center_match", "strict_target_match"):
            if key not in evidence or \
                    evidence.get(key) is not recomputed.get(key):
                out.append(f"{key}:claimed={evidence.get(key)!r}"
                           f":recomputed={recomputed.get(key)!r}")
        claimed_basis = str(evidence.get("center_match_basis", "") or "")
        recomputed_basis = str(
            recomputed.get("center_match_basis", "") or "")
        if claimed_basis != recomputed_basis:
            out.append("center_match_basis:claimed="
                       f"{claimed_basis!r}:recomputed="
                       f"{recomputed_basis!r}")
        if evidence.get("declaration_mismatch", None) != \
                recomputed.get("declaration_mismatch"):
            out.append("declaration_mismatch:claimed="
                       f"{evidence.get('declaration_mismatch')!r}"
                       f":recomputed="
                       f"{recomputed.get('declaration_mismatch')!r}")
        bound = evidence.get("bound_inputs")
        if bound is None:
            out.append("bound_inputs:missing")
            return out
        rbound = recomputed.get("bound_inputs") or {}
        for key in ("substrate_identity", "product_identity",
                    "edits_signature", "alignment_ref",
                    "execution_fingerprint"):
            if key not in bound:
                out.append(f"bound_inputs.{key}:missing")
            elif bound[key] != rbound.get(key):
                out.append(f"bound_inputs.{key}:claimed≠recomputed")
        if "donor_centers" not in bound:
            out.append("bound_inputs.donor_centers:missing")
        elif sorted(str(x) for x in bound["donor_centers"]) != \
                sorted(str(x) for x in (rbound.get("donor_centers")
                                        or [])):
            out.append("bound_inputs.donor_centers:claimed≠recomputed")
        return out

    def _center_evidence_binding(
            recomputed_bound: dict) -> tuple[bool, str, dict]:
        """R6(R5-01)覆盖绑定参与物**系数/贡献** + 注册计量补全规则。

        设 s=复算 bound_inputs.substrate_identity、p=product_identity
        (可为点分碎片串,如 "C.CO")。参与物取 hypothesis.participants
        (coefficient 为 Fraction,coefficient_status known/unknown):

        1. 底物绑定(保留):证据底物身份 == 本假设底物状态身份;
        2. λ_s(底物规模)= Σ 反应物侧 identity==s 的参与物系数
           (须全部 known,否则覆盖结果 unknown);
        3. 覆盖产物集:p ∈ 产物 identity 集合 ⇒ whole_molecule
           (covered={p},重数 1);否则 p 按 "." 拆碎片、全部碎片须
           ∈ 产物 identity 集合(否则维持 undeclared_product_fragment
           拒绝)⇒ fragments(covered = 碎片 identity 多重集);
        4. 系数绑定:每个 covered identity 的产物侧声明系数总和
           == λ_s × 其在 p 中的重数("1/2 乙醛 + 1/2 环氧乙烷"反例的
           关断点:声明 1/2 ≠ λ_s=1);
        5. 注册补全规则 COVERAGE_COMPLETION_RULE:Δ = elements(s) −
           elements(p);未覆盖产物/反应物元素账与 λ_s×Δ⁺/λ_s×(−Δ)⁺
           **各自精确相等**,不许盈余/亏空互相抵消("环丙烷→丙烯同式
           量异构"反例的关断点);无未覆盖参与物 ⇒ full(假设只声明了
           被覆盖转化本身;元素账是否平归 element_accounting 独立轴,
           不在此重复);
        6. 未知系数 ⇒ coverage unknown_coefficients(中心 unknown,不
           R6:覆盖规模/贡献不可算,不冒充已覆盖);
        7. 违反 ⇒ binding_ok=False + 前缀
           center_evidence_partial_coverage_unchecked_transformation
           (部分覆盖,不 R6);detail 披露 coverage_rule/substrate_scale/
           atom_delta/两侧未覆盖元素/逐条 coverage_violations。
        """
        substrate_state = states.get(hypothesis.substrate_state_ref)
        if substrate_state is None or not \
                substrate_state.smiles_isomeric:
            return False, \
                "center_evidence_binding_unverifiable_substrate", {}
        s = str(recomputed_bound.get("substrate_identity", ""))
        if s != substrate_state.smiles_isomeric:
            return False, "center_evidence_binding_mismatch:substrate", {}
        p = str(recomputed_bound.get("product_identity", ""))
        if not p:
            return False, \
                "center_evidence_binding_unverifiable:product", {}
        reactant_parts = [pp for pp in hypothesis.participants
                          if pp.side == PARTICIPANT_SIDE_REACTANT]
        product_parts = [pp for pp in hypothesis.participants
                         if pp.side == PARTICIPANT_SIDE_PRODUCT]

        def _identity_of(pp) -> str:
            st = states.get(pp.state_ref)
            return st.smiles_isomeric if st is not None else ""

        product_identities = {_identity_of(pp) for pp in product_parts}
        product_identities.discard("")
        if p in product_identities:
            covered_multiplicity: dict[str, int] = {p: 1}
            coverage_mode = "whole_molecule"
        else:
            fragment_identities: list[str] = []
            for fragment in p.split("."):
                try:
                    fragment_identities.append(
                        strict_identity_of(fragment))
                except ChemicalStateError:
                    return False, (
                        "center_evidence_binding_unverifiable:fragment"), {}
            undeclared = sorted({f for f in fragment_identities
                                 if f not in product_identities})
            if undeclared:
                return False, (
                    "center_evidence_binding_mismatch:"
                    "undeclared_product_fragment"), {
                        "undeclared_fragments": undeclared}
            covered_multiplicity = {}
            for fragment in fragment_identities:
                covered_multiplicity[fragment] = \
                    covered_multiplicity.get(fragment, 0) + 1
            coverage_mode = "fragments"
        covered_identities = set(covered_multiplicity)
        uncovered_reactants = [pp for pp in reactant_parts
                               if _identity_of(pp) != s]
        uncovered_products = [pp for pp in product_parts
                              if _identity_of(pp) not in covered_identities]
        base_coverage_detail = {
            "coverage_mode": coverage_mode,
            "covered_product_identities": sorted(covered_identities),
            "uncovered_product_refs": sorted(
                pp.state_ref for pp in uncovered_products),
            "uncovered_reactant_refs": sorted(
                pp.state_ref for pp in uncovered_reactants),
        }
        # 6. 未知系数 ⇒ 覆盖规模/贡献不可算(诚实 unknown,不 R6)
        if any(pp.coefficient_status != COEFFICIENT_KNOWN
               for pp in reactant_parts + product_parts):
            return False, (
                _COVERAGE_UNKNOWN_COEFF_PREFIX + "coefficients"
                "(参与物系数未知:覆盖与贡献规模不可算,不得计入全部"
                "核实;系数须已知或另行补全,不冒充已覆盖)"), {
                **base_coverage_detail,
                "product_coverage": "unknown_coefficients",
                "coverage_rule": COVERAGE_COMPLETION_RULE}

        def _elements_of(identity: str) -> dict[str, Fraction] | None:
            mol = Chem.MolFromSmiles(identity) if identity else None
            if mol is None:
                return None
            return element_counts_full(mol)

        elem_s = _elements_of(s)
        elem_p = _elements_of(p)
        if elem_s is None or elem_p is None:
            return False, (
                "center_evidence_binding_unverifiable:element_"
                "composition"), dict(base_coverage_detail)
        lambda_s = sum((pp.coefficient for pp in reactant_parts
                        if _identity_of(pp) == s), Fraction(0))
        delta: dict[str, Fraction] = {}
        for element in set(elem_s) | set(elem_p):
            d = elem_s.get(element, Fraction(0)) \
                - elem_p.get(element, Fraction(0))
            if d != 0:
                delta[element] = d
        delta_pos = {el: v for el, v in delta.items() if v > 0}
        delta_neg = {el: -v for el, v in delta.items() if v < 0}
        violations: list[dict] = []
        # 4. 系数绑定:产物侧声明贡献 == λ_s × 重数
        for identity, multiplicity in sorted(covered_multiplicity.items()):
            declared = sum((pp.coefficient for pp in product_parts
                            if _identity_of(pp) == identity), Fraction(0))
            required = lambda_s * multiplicity
            if declared != required:
                violations.append({
                    "kind": "coefficient_binding_mismatch",
                    "identity": identity,
                    "declared_total": str(declared),
                    "required": str(required),
                    "multiplicity_in_bound_product": multiplicity})
        # 5. 注册补全规则:两侧各自精确相等
        uncovered_reactant_elements: dict[str, Fraction] = {}
        uncovered_product_elements: dict[str, Fraction] = {}
        composition_unverifiable = False
        for pp, bucket in ([(pp, uncovered_reactant_elements)
                            for pp in uncovered_reactants]
                           + [(pp, uncovered_product_elements)
                              for pp in uncovered_products]):
            elements = _elements_of(_identity_of(pp))
            if elements is None:
                composition_unverifiable = True
                continue
            for element, count in elements.items():
                bucket[element] = bucket.get(element, Fraction(0)) \
                    + count * pp.coefficient
        if composition_unverifiable:
            return False, (
                "center_evidence_binding_unverifiable:element_"
                "composition"), dict(base_coverage_detail)

        def _completion_violations(actual, required, side):
            out = []
            for element in sorted(set(actual) | set(required)):
                have = actual.get(element, Fraction(0))
                need = required.get(element, Fraction(0))
                if have == need:
                    continue
                out.append({
                    "kind": ("completion_surplus" if have > need
                             else "completion_deficit"),
                    "side": side,
                    "element": element,
                    "declared_total": str(have),
                    "required": str(need)})
            return out

        if uncovered_reactants or uncovered_products:
            # 无未覆盖参与物 ⇒ full(补全规则不重复元素账独立轴);
            # 有未覆盖参与物 ⇒ 两侧各自与注册规则精确对账
            violations += _completion_violations(
                uncovered_product_elements,
                {el: lambda_s * v for el, v in delta_pos.items()},
                "product")
            violations += _completion_violations(
                uncovered_reactant_elements,
                {el: lambda_s * v for el, v in delta_neg.items()},
                "reactant")
            # R6-01(R7):补全许可范围 —— 未覆盖参与物的严格结构身份
            # 须在注册许可集(组合型氢当量)内;未登记身份即使数值
            # 全配平,其初始分子图的键变化/连接贡献仍未核实(元素配平
            # ≠ 结构贡献已核实),不得据此 full/R6
            unlicensed_identities = sorted({
                identity for identity in
                (_identity_of(pp) for pp in
                 uncovered_reactants + uncovered_products)
                if identity and identity
                not in COMPLETION_LICENSED_IDENTITIES})
            if unlicensed_identities:
                violations.append({
                    "kind": "completion_license_unregistered_identity",
                    "identities": unlicensed_identities,
                    "completion_license": COMPLETION_LICENSE,
                    "note": ("未覆盖参与物的严格结构身份未登记补全许可"
                             f"({COMPLETION_LICENSE}=组合型氢当量);"
                             "数值配平只证明组成贡献,不证明其初始图"
                             "的键变化/连接贡献已核实")})
        else:
            unlicensed_identities = []
        detail = {
            **base_coverage_detail,
            "product_coverage": ("partial_unchecked_transformation"
                                 if violations else "full"),
            "coverage_rule": COVERAGE_COMPLETION_RULE,
            # R6-01:许可范围/依据机器披露(登记许可=组成型氢当量;
            # 未登记身份即使数值配平也 partial,见 coverage_violations)
            "completion_license": COMPLETION_LICENSE,
            "completion_license_scope": (
                "registered:composition_only_hydrogen_equivalents("
                "H2/[H] 按 2[H] 氢当量;数值配平不证明未登记多原子"
                "共底物初始图的结构贡献)"),
            "unlicensed_uncovered_identities": list(
                unlicensed_identities),
            "substrate_scale": str(lambda_s),
            "atom_delta": {element: str(value) for element, value
                           in sorted(delta.items())},
            "uncovered_reactant_elements": {
                element: str(value) for element, value
                in sorted(uncovered_reactant_elements.items())},
            "uncovered_product_elements": {
                element: str(value) for element, value
                in sorted(uncovered_product_elements.items())},
            "coverage_violations": violations,
        }
        if violations:
            return False, (
                _COVERAGE_PARTIAL_PREFIX + "_unchecked_transformation"
                "(证据覆盖须绑定被审参与物及贡献/系数:系数绑定、注册"
                f"补全规则 {COVERAGE_COMPLETION_RULE} 数值不符,或未"
                "覆盖参与物严格结构身份未登记补全许可("
                f"{COMPLETION_LICENSE}:数值配平不证明初始图结构贡献已"
                "核实)= 存在额外未核实转化/未核实结构贡献,不得计入"
                "全部核实;可明确部分覆盖而 retain)"), detail
        return True, "", detail

    if CHECK_TRANSFORMATION_CENTER in requested:
        sig = hypothesis.transformation_signature_status
        if prerequisite_failed or structure_unavailable:
            checks.append(_dependent(CHECK_TRANSFORMATION_CENTER,
                                     "mapping_dependent"))
        elif center_evidence is None:
            # 无确定性证据:自报 verified 不授信(mimo 5.3/R2-01);
            # declared 状态保留在 detail,不当作检查结果
            checks.append(AuditCheck(
                name=CHECK_TRANSFORMATION_CENTER, status=CHECK_UNKNOWN,
                reason_code="center_evidence_missing"
                "(自报 transformation_signature_status 不是检查结果;"
                f"declared={sig or 'unavailable'})",
                coverage="mapping_dependent",
                detail={"declared_signature_status": sig or ""}))
        else:
            checker = str(center_evidence.get("checker_version", ""))
            ev_scope = str(center_evidence.get("checker_scope", ""))
            if checker not in CENTER_CHECKER_REGISTRY:
                checks.append(AuditCheck(
                    name=CHECK_TRANSFORMATION_CENTER, status=CHECK_UNKNOWN,
                    reason_code=f"center_checker_not_registered:{checker}"
                    "(确定性中心 checker 须注册并独立列项评审)",
                    coverage="mapping_dependent",
                    detail={"declared_signature_status": sig or "",
                            "checker_version": checker}))
            elif ev_scope not in CENTER_CHECKER_SCOPES:
                checks.append(AuditCheck(
                    name=CHECK_TRANSFORMATION_CENTER, status=CHECK_UNKNOWN,
                    reason_code=f"center_checker_scope_unknown:{ev_scope}"
                    "(checker 检查范围未声明/未登记:限定区域证据不得"
                    "冒充完整变换验证)",
                    coverage="mapping_dependent",
                    detail={"checker_version": checker}))
            else:
                type_violation = _evidence_type_violation(center_evidence)
                if type_violation:
                    # R4-01:表示违约 ⇒ 结构化拒绝(不是化学"未知就拒绝")
                    raise AuditContractError(
                        "center_evidence 载荷类型违约:"
                        f"{type_violation}(轴字段须为 bool|None;"
                        "字符串'false'/整数0/空容器不得绕过类型契约"
                        "直达 R6)",
                        {"kind": "center_evidence_type_violation",
                         "violation": type_violation,
                         "checker_version": checker})
                proof = center_evidence.get("proof_record")
                if not proof:
                    # 无可复算证明记录:两条身份字符串或六条自报字段
                    # 不构成核实(R4-01 反例)⇒ unknown,不授信
                    checks.append(AuditCheck(
                        name=CHECK_TRANSFORMATION_CENTER,
                        status=CHECK_UNKNOWN,
                        reason_code=(
                            "center_evidence_proof_missing"
                            "(证据未携带 proof_record:不可内部复算的"
                            "自报字段/身份字符串不构成 checker 曾对"
                            "本次输入执行的证明;诚实 unknown,不改"
                            "文字收窄)"),
                        coverage="mapping_dependent",
                        detail={**_evidence_binding_detail(
                            center_evidence, "proof_record_missing"),
                            "checker_version": checker,
                            "checker_scope": ev_scope,
                            "declared_signature_status": sig or ""}))
                else:
                    # ---- 内部重算(R4-01):复跑诊断,自报字段须一致 ----
                    rerun = _rerun_proof_record(dict(proof))
                    recomputed = rerun.center_evidence
                    integrity = _evidence_integrity_mismatches(
                        center_evidence, recomputed)
                    if integrity:
                        raise AuditContractError(
                            "center_evidence 自报字段与证明记录复算值"
                            "不一致(证据被改写/拼接;结构化拒绝,不改"
                            "输入即不改结论):" + ";".join(integrity[:6]),
                            {"kind": "center_evidence_integrity_mismatch",
                             "mismatches": integrity[:20],
                             "checker_version": checker})
                    refs = [str(r) for r in center_evidence.get(
                        "evidence_refs", [])][:10]
                    base_detail = {
                        "declared_signature_status": sig or "",
                        "checker_version": checker,
                        "checker_scope": ev_scope,
                        # P2(R5 §4-1):proof 的命题范围如实披露 —— 本
                        # 结论是自包含输入集的确定性重算(可复现),
                        # 不含"编辑曾被执行"的运行事实(运行事实归执行
                        # 器通道,如 execution_fingerprint 绑定)
                        "proof_scope": "self_contained_recompute"}
                    binding_ok, binding_reason, coverage_detail = \
                        _center_evidence_binding(
                            recomputed.get("bound_inputs") or {})
                    if not binding_ok and not (
                            binding_reason.startswith(
                                _COVERAGE_PARTIAL_PREFIX)
                            or binding_reason.startswith(
                                _COVERAGE_UNKNOWN_COEFF_PREFIX)):
                        # 跨反应复用/改产物/未申报碎片 ⇒ 不得认证
                        checks.append(AuditCheck(
                            name=CHECK_TRANSFORMATION_CENTER,
                            status=CHECK_UNKNOWN,
                            reason_code=binding_reason
                            + "(证据未绑定本假设的底物/产物集合;复算"
                            "证明链对不上,注册名+True 不构成核实)",
                            evidence_refs=refs,
                            coverage="mapping_dependent",
                            detail={**base_detail,
                                    **_evidence_binding_detail(
                                        center_evidence, binding_reason),
                                    **coverage_detail}))
                    else:
                        mismatch = bool(recomputed.get(
                            "declaration_mismatch"))
                        center_match = recomputed.get("center_match")
                        strict_axis = recomputed.get("strict_target_match")
                        # P2(R5 §4-1):basis 从复算读(diagnostic 载荷
                        # v6 起携带;direct | symmetric_equivalent,仅
                        # center_match=True 时非空)—— 不再空串伪装依据
                        basis_str = str(recomputed.get(
                            "center_match_basis", ""))
                        axis_detail = {**base_detail,
                                       "center_match": center_match,
                                       "center_match_basis": basis_str,
                                       "strict_target_match": strict_axis,
                                       **coverage_detail}
                        if not binding_ok:
                            # 部分覆盖(额外未核实转化/未核实贡献)或
                            # 覆盖不可算(未知系数)⇒ 不可 verified
                            # (可明确部分覆盖而 retain,R4-01/R5-01 验收)
                            checks.append(AuditCheck(
                                name=CHECK_TRANSFORMATION_CENTER,
                                status=CHECK_UNKNOWN,
                                reason_code=binding_reason,
                                evidence_refs=refs,
                                coverage="mapping_dependent",
                                detail=axis_detail))
                        elif mismatch or center_match is None:
                            checks.append(AuditCheck(
                                name=CHECK_TRANSFORMATION_CENTER,
                                status=CHECK_UNKNOWN,
                                reason_code=(
                                    "center_evidence_inconclusive"
                                    + ("_declaration_mismatch" if mismatch
                                       else "")
                                    + ("_center_unknown"
                                       if center_match is None else "")),
                                evidence_refs=refs,
                                coverage="mapping_dependent",
                                detail=axis_detail))
                        elif strict_axis is False:
                            # R3-01/mimo 3.3(3):确定性 checker 发现产物
                            # 偏离预期(strict=False)——适用失败轴不得在
                            # all_verified 语义下消失;区域 True 与 strict
                            # False 分别保留在 detail,各轴不互相覆盖
                            checks.append(AuditCheck(
                                name=CHECK_TRANSFORMATION_CENTER,
                                status=CHECK_VIOLATED,
                                reason_code=(
                                    "center_evidence_strict_target_mismatch"
                                    "(产物与声明位点预期不同:区域轴与"
                                    "strict 轴分别报告,完整核实不忽略"
                                    "适用失败)"),
                                evidence_refs=refs,
                                coverage="mapping_dependent",
                                detail=axis_detail))
                        elif strict_axis is None:
                            # 适用的未核实轴同样阻断 all_verified
                            checks.append(AuditCheck(
                                name=CHECK_TRANSFORMATION_CENTER,
                                status=CHECK_UNKNOWN,
                                reason_code="center_evidence_strict_unknown"
                                "(产物比对轴未核实:不得计入全部核实)",
                                evidence_refs=refs,
                                coverage="mapping_dependent",
                                detail=axis_detail))
                        elif center_match is True:
                            checks.append(AuditCheck(
                                name=CHECK_TRANSFORMATION_CENTER,
                                status=CHECK_VERIFIED,
                                reason_code=(
                                    "center_evidence_verified"
                                    f":{checker}(scope={ev_scope};basis="
                                    f"{basis_str})"),
                                evidence_refs=refs,
                                coverage="mapping_dependent",
                                detail=axis_detail))
                        else:  # center_match is False:声明中心与实际偏离
                            checks.append(AuditCheck(
                                name=CHECK_TRANSFORMATION_CENTER,
                                status=CHECK_VIOLATED,
                                reason_code=(
                                    f"center_mismatch_per_deterministic_"
                                    f"checker:{checker}"),
                                evidence_refs=refs,
                                coverage="mapping_dependent",
                                detail=axis_detail))

    # ---- ⑧ step_scope ----
    if CHECK_STEP_SCOPE in requested:
        if hypothesis.step_scope == "unknown":
            checks.append(AuditCheck(
                name=CHECK_STEP_SCOPE, status=CHECK_UNKNOWN,
                reason_code="step_scope_unknown(汇总边不冒充净反应)",
                coverage="step_scope"))
        elif hypothesis.step_scope == "multistep_summary":
            checks.append(AuditCheck(
                name=CHECK_STEP_SCOPE, status=CHECK_NOT_APPLICABLE,
                reason_code="multistep_summary_kept_as_summary_edge",
                coverage="step_scope"))
        else:
            checks.append(AuditCheck(
                name=CHECK_STEP_SCOPE, status=CHECK_VERIFIED,
                reason_code=f"step_scope:{hypothesis.step_scope}",
                evidence_refs=list(hypothesis.step_scope_evidence_refs),
                coverage="step_scope"))

    # ---- ⑨ 条件检查(缺输入未执行 = unknown;提供时走候选级评估) ----
    if CHECK_CONDITION_CHECK in requested:
        if context is None:
            checks.append(AuditCheck(
                name=CHECK_CONDITION_CHECK, status=CHECK_UNKNOWN,
                reason_code="condition_assessment_not_run"
                "(缺 context 未执行;不得以无冲突措辞呈现)",
                coverage="declared_dimensions"))
        elif prerequisite_failed:
            checks.append(_dependent(CHECK_CONDITION_CHECK,
                                     "declared_dimensions"))
        else:
            # R3-06:候选级评估 —— 旧边路线快照(phase_history 记录值
            # 合取,不重评)+ 本候选新增要求在当前 scenario+phase
            # 作用域;audit 直接消费快照,不再重评全部累积要求(旧
            # 边冲突不得被洗掉、合法分阶段路线不得被错杀)
            assessment = assess_candidate_conditions(context, hypothesis)
            status_map = {
                "conflict": CHECK_VIOLATED,
                "compatible": CHECK_VERIFIED,
                "unknown": CHECK_UNKNOWN,
            }
            checks.append(AuditCheck(
                name=CHECK_CONDITION_CHECK,
                status=status_map[assessment.environment_fit],
                reason_code=(
                    f"environment_fit:{assessment.environment_fit}"
                    f";coverage:{';'.join(assessment.assessment_scope)}"),
                coverage="declared_dimensions",
                detail={"unassessed_dimensions":
                        list(assessment.unassessed_dimensions),
                        "assessment_scope":
                            list(assessment.assessment_scope)}))

    # ---- ⑩ 来源依赖(R3-07:审计 context 与 hypothesis 引用**并集**;
    # 缺解析 ≠ 没有依赖;F06 引用存在但状态未提供 ⇒ 不得视为已解决) ----
    if CHECK_PROVENANCE_DEPENDENCY in requested:
        hyp_refs = [str(r) for r in
                    (getattr(hypothesis, "dependency_refs", []) or [])]
        ctx_states: dict[str, dict] = {}
        if context is not None:
            ctx_states = context.dependency_states()
        all_refs = sorted(set(hyp_refs) | set(ctx_states))
        explicit_unresolved: set[str] = set()
        if unresolved_dependency_ids is not None:
            # None = 未提供(从 context 推导);[] = 显式断言无未解决
            # (两者语义不混同,R3-08)
            explicit_unresolved = {str(u) for u in unresolved_dependency_ids}
        unresolved_list: list[str] = []
        unknown_list: list[str] = []
        for ref in all_refs:
            ctx_info = ctx_states.get(ref)
            if ctx_info is not None and ctx_info.get("status") \
                    != "supported":
                # context 侧权威状态未解决(含 unresolved/contradicted)
                unresolved_list.append(ref)
            elif ref in explicit_unresolved:
                unresolved_list.append(ref)
            elif ctx_info is not None:
                pass  # context 侧 supported
            elif unresolved_dependency_ids is not None:
                pass  # 调用方显式断言(含空列表)已解决
            else:
                # 解析未提供 ≠ 引用不存在(F06/R3-07)
                unknown_list.append(ref)
        if unresolved_list:
            checks.append(AuditCheck(
                name=CHECK_PROVENANCE_DEPENDENCY, status=CHECK_UNKNOWN,
                reason_code="unresolved_dependencies_inherited"
                "(含 context 继承依赖;下游命中不自动解决上游)",
                evidence_refs=unresolved_list[:10],
                coverage="dependency_set",
                detail={"context_only": [r for r in unresolved_list
                                         if r not in hyp_refs]}))
        elif unknown_list:
            checks.append(AuditCheck(
                name=CHECK_PROVENANCE_DEPENDENCY, status=CHECK_UNKNOWN,
                reason_code="dependency_resolution_not_provided"
                "(引用存在但解析状态未提供;缺解析≠没有依赖)",
                evidence_refs=unknown_list[:10], coverage="dependency_set"))
        elif all_refs:
            checks.append(AuditCheck(
                name=CHECK_PROVENANCE_DEPENDENCY, status=CHECK_VERIFIED,
                reason_code="all_dependency_refs_reported_resolved",
                evidence_refs=all_refs[:10], coverage="dependency_set"))
        else:
            checks.append(AuditCheck(
                name=CHECK_PROVENANCE_DEPENDENCY, status=CHECK_VERIFIED,
                reason_code="no_unresolved_dependencies",
                coverage="dependency_set"))

    audit_id = stable_id(
        "audit", hypothesis.hypothesis_id, scope,
        content_hash([c.to_dict() for c in checks]))
    participant_accounting = (
        "full" if full_known and not prerequisite_failed
        and not structure_unavailable
        else "partial" if not prerequisite_failed
        and not structure_unavailable
        else "unknown")
    # input_hash 覆盖**实际科学输入**(R2-07/R3-08):hypothesis 完整
    # 语义载荷、参与物 state 的**完整内容**(含 fidelity/appearance 层
    # —— 同 state_id 的 raw/archive fidelity 是不同科学输入)、
    # context **全科学载荷** content_hash(phase_history/依赖解析
    # 状态/要求/事实 —— context_id 可被嵌套修改而不变,内容哈希不可)、
    # audit_scope、checker 版本、**center_evidence 规范化摘要**(含
    # 各轴结论与绑定输入)、**依赖解析状态**(unresolved 列表)。
    # 依赖已解决 vs unresolved、中心证据 True vs False、state fidelity
    # 差异 ⇒ 不同 input_hash(调用前已存在的输入,不以"判定前输入"
    # 改名免责,R3-08);相同实际输入重放幂等同 hash。
    input_fingerprint = {
        "audit_schema": PPV1_AUDIT_SCHEMA_VERSION,
        "hypothesis": hypothesis.to_dict(),
        "participant_states": {
            ref: state.to_dict() for ref, state in sorted(states.items())
        },
        "context_content": (content_hash(context.to_dict())
                            if context is not None else None),
        "audit_scope": sorted(requested),
        "checker_versions": versions,
        # R4-02:实际消费的全部审核入参入 hash —— 有限规则诊断
        # (默认 not_run 合法 NA、admission expand 与 diagnostic_only 的
        # unknown/retain 是不同输入状态,不得同 hash:复审
        # finite_rule_diagnostic_active 反例两次 input_hash 相同)
        "finite_rule_diagnostic": (
            content_hash(finite_rule_diagnostic)
            if finite_rule_diagnostic is not None else None),
        "center_evidence": (
            {k: v for k, v in sorted(
                (center_evidence or {}).items())
            if k not in ("bound_inputs", "proof_record")}
            | {"bound_inputs_hash": content_hash(
                (center_evidence or {}).get("bound_inputs") or {}),
               "proof_record_hash": content_hash(
                (center_evidence or {}).get("proof_record") or {})}
            if center_evidence is not None else None),
        "unresolved_dependency_ids": (
            [str(u) for u in sorted(unresolved_dependency_ids)]
            if unresolved_dependency_ids is not None else None),
        "legacy_gate_result_ref": (
            (legacy_gate_result or {}).get("gate_ref", "")),
    }
    return ChemicalAudit(
        audit_id=audit_id, scope=scope, input_hash=stable_id(
            "ain", content_hash(input_fingerprint)),
        checks=checks,
        legacy_gate_result_ref=(
            (legacy_gate_result or {}).get("gate_ref", "")),
        participant_accounting_status=participant_accounting,
        biological_support_status="unknown",
        checker_versions=versions,
    )


def _element_accounting(reactant_side, product_side, states) -> AuditCheck:
    """全量元素账(F01:全部氢;系数加权;不补水/氧/辅酶凑平)。

    输出逐元素 Δ = Σ(反应物) − Σ(产物) 与常见漏项模式的结构化数值
    相符标注(mimo 2.3(2):{pattern, excess_on, missing_from,
    element_delta};仅数值相符:不证明缺项原因,不含电子/质子计量,
    H+ 模式名 H+_count1 仅表示 H 计数)。

    口径注记(mimo 2.2(a)):D/T 并入元素 H(同位素差异只在身份/同位素
    轴体现,不入本账);自由基未配对电子不入账;本账 verified 仅指元素
    与形式电荷的数值闭合,不指同位素计量、电子转移或机制。radical 保真
    轴为已知缺口(身份层区分自由基;本轴未实现)。
    """
    totals: dict[str, Fraction] = {}
    for p, sign in [(p, 1) for p in reactant_side] + [
            (p, -1) for p in product_side]:
        mol = _mol_of(states.get(p.state_ref))
        if mol is None:
            return AuditCheck(
                name=CHECK_ELEMENT_ACCOUNTING, status=CHECK_UNKNOWN,
                reason_code=f"state_unavailable:{p.state_ref}",
                coverage="full_balance")
        coeff = p.coefficient if p.coefficient is not None else Fraction(0)
        for sym, n in element_counts_full(mol).items():
            totals[sym] = totals.get(sym, Fraction(0)) + sign * n * coeff
    diffs = {sym: v for sym, v in totals.items() if v != 0}
    detail = {
        "element_delta": {sym: str(v) for sym, v in sorted(diffs.items())},
        "accounting_scope": "full_balance_all_hydrogen",
        "accounting_notes": (
            "isotopes_D_T_counted_as_H; radical_electrons_not_counted; "
            "verified_only_element_and_formal_charge_closure"),
        "omission_pattern_matches": [],
        "omission_pattern_semantics": (
            "omission_pattern_matches 仅表示缺口向量与该常见模式逐元素"
            "数值相符(excess_on=多出侧,missing_from=缺写侧;不证明"
            "实际缺该物质、不推断遗漏原因、不含电子/质子计量;"
            "H+_count1 仅表示 H 计数为 1 的模式名)"),
    }
    if diffs:
        for name, pattern in COMMON_OMISSION_PATTERNS.items():
            for excess_on, sign in (("reactant_side", 1),
                                    ("product_side", -1)):
                signed = {k: sign * v for k, v in pattern.items()}
                if diffs == signed:
                    detail["omission_pattern_matches"].append({
                        "pattern": ("H+_count1" if name == "H+" else name),
                        "excess_on": excess_on,
                        "missing_from": ("product_side"
                                         if excess_on == "reactant_side"
                                         else "reactant_side"),
                        "element_delta": {k: str(v)
                                          for k, v in sorted(signed.items())},
                    })
        detail_str = ";".join(
            f"{sym}:{v}" for sym, v in sorted(diffs.items()))
        return AuditCheck(
            name=CHECK_ELEMENT_ACCOUNTING, status=CHECK_VIOLATED,
            reason_code=f"declared_account_violated:element_imbalance:"
                        f"{detail_str}",
            coverage="full_balance", detail=detail)
    return AuditCheck(
        name=CHECK_ELEMENT_ACCOUNTING, status=CHECK_VERIFIED,
        reason_code="elements_balanced_all_hydrogen",
        coverage="full_balance", detail=detail)


def _charge_accounting(reactant_side, product_side, states) -> AuditCheck:
    """形式电荷账(原始 formal_charge;不先中和;结构化差值输出)。"""
    total = Fraction(0)
    for p, sign in [(p, 1) for p in reactant_side] + [
            (p, -1) for p in product_side]:
        st = states.get(p.state_ref)
        if st is None or st.formal_charge is None:
            return AuditCheck(
                name=CHECK_FORMAL_CHARGE_ACCOUNTING, status=CHECK_UNKNOWN,
                reason_code=f"charge_unavailable:{p.state_ref}",
                coverage="full_balance")
        coeff = p.coefficient if p.coefficient is not None else Fraction(0)
        total += sign * st.formal_charge * coeff
    detail = {
        "charge_delta": str(total),
        "accounting_scope": "full_balance_original_formal_charge",
    }
    if total != 0:
        return AuditCheck(
            name=CHECK_FORMAL_CHARGE_ACCOUNTING, status=CHECK_VIOLATED,
            reason_code=f"declared_account_violated:charge_imbalance:"
                        f"{total}",
            coverage="full_balance", detail=detail)
    return AuditCheck(
        name=CHECK_FORMAL_CHARGE_ACCOUNTING, status=CHECK_VERIFIED,
        reason_code="formal_charge_balanced",
        coverage="full_balance", detail=detail)


# ---------------------------------------------------------------- admission


@dataclass
class AdmissionPolicy:
    """P0-4:admission 策略(schema + 完整决策表;v3 +R1b +R5v +R5c
    +逐产物门禁消费)。

    规则(评估顺序固定,首中即决):
    R1  structure_unparseable      → reject  (实际输入语法非法;CN-only
        等合法缺结构走 unknown,悬空引用走 R1b,不进本行)
    R1b participant_state_missing  → reject  (参与物 state 引用悬空 =
        账本/引用完整性问题,理由码保留,不压平成"结构不可解析",
        R2-01/mimo 3.2(2))
    R2  active_gate_rejected       → reject  (活动门禁显式拒绝;仅
        reject_gates 名单内 —— 不暗改冻结判据,新门禁须独立评审)
    R2p per_product_gate_rejected  → reject(全部共同产物被拒)/
        retain_conditional(部分被拒:被拒产物保留拒因、不可展开,
        不删除被拒共同产物凑合法事件)(R2-12;消费开关
        per_product_gate_consumption 由策略显式版本化)
    R2b contract_violated_       → reject  (表示契约违反:零/负/非有限
        representation                  系数、酶计入净计量、结构性违约;
        理由码写死 representation = 非化学,mimo 3.2(1) 采纳)
    R3  current_scenario_conflict  → defer   (有来源 essential 条件与当前
        场景已知事实冲突;action=blocked,假设保留不在此场景展开)
    R4  budget_or_wait             → defer   (独立原因)
    R5d declared_account_violated  → retain_conditional(触发集合显式限定
        {element_accounting, formal_charge_accounting},mimo 3.2(4);
        账不平只证明声明内部矛盾,不证明反应不存在;绝不进入 R6)
    R5v declared_violated_other    → retain_conditional(其他检查 violated
        的独立码 —— 如确定性 checker 的中心偏离;不冒称"声明账不一致")
    R5c required_check_coverage_   → retain_conditional(必需适用检查未
        missing                        被执行/不在审计内:窄 audit_scope 只
                                       能作诊断,R6 覆盖核算不通过,R2-01)
    R5  unknown_checks_present     → retain_conditional(检查 unknown/
        因缺输入未执行;继承未解决依赖)
    R6  default_all_verified       → expand(全部必需适用检查覆盖且
        verified,无 unknown/violated/缺输入未执行;语义 NA 白名单
        除外)
    R7  no_applicable_checks       → retain_conditional(无适用检查:
        保守保留,不冒充核实;理由与 R5 分开)

    任何 unknown 不自动 reject;新增"诊断转拒绝"必须扩本表并升版本。
    chemical_reproposal 首版 off。
    """

    policy_version: str = PPV1_ADMISSION_POLICY_VERSION
    reject_gates: frozenset = frozenset(DEFAULT_REJECT_GATES)
    chemical_reproposal: str = "off"
    per_product_gate_consumption: str = "on"
    rules: tuple = (
        ("R1", "structure_unparseable", ADMISSION_REJECT),
        ("R1b", "participant_state_missing", ADMISSION_REJECT),
        ("R2", "active_gate_rejected", ADMISSION_REJECT),
        ("R2p", "per_product_gate_rejected",
         ADMISSION_REJECT + "|" + ADMISSION_RETAIN_CONDITIONAL),
        ("R2b", "contract_violated_representation", ADMISSION_REJECT),
        ("R3", "current_scenario_conflict", ADMISSION_DEFER),
        ("R4", "budget_or_wait", ADMISSION_DEFER),
        ("R5d", "declared_account_violated", ADMISSION_RETAIN_CONDITIONAL),
        ("R5v", "declared_violated_other", ADMISSION_RETAIN_CONDITIONAL),
        ("R5c", "required_check_coverage_missing",
         ADMISSION_RETAIN_CONDITIONAL),
        ("R5", "unknown_checks_present", ADMISSION_RETAIN_CONDITIONAL),
        ("R6", "default_all_verified", ADMISSION_EXPAND),
        ("R7", "no_applicable_checks", ADMISSION_RETAIN_CONDITIONAL),
    )

    def to_dict(self) -> dict:
        return {
            "policy_version": self.policy_version,
            "reject_gates": sorted(self.reject_gates),
            "chemical_reproposal": self.chemical_reproposal,
            "per_product_gate_consumption":
                self.per_product_gate_consumption,
            "rules": [
                {"rule_id": rid, "condition": cond, "disposition": disp}
                for rid, cond, disp in self.rules],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "AdmissionPolicy":
        version = d.get("policy_version", "")
        if version != PPV1_ADMISSION_POLICY_VERSION:
            raise AuditContractError(
                f"admission policy 版本未知:{version!r}(支持 "
                f"{PPV1_ADMISSION_POLICY_VERSION})",
                {"policy_version": version})
        gates = frozenset(d.get("reject_gates", DEFAULT_REJECT_GATES))
        unknown_gates = gates - DEFAULT_REJECT_GATES
        if unknown_gates:
            raise AuditContractError(
                "reject_gates 含未知门禁(新增门禁须独立列项评审,不暗改;"
                "mapper 的 gate_atom_mapping_declared 为只读旁证,启用为"
                "拒绝门禁须扩 DEFAULT_REJECT_GATES 并升策略版本)",
                {"unknown_gates": sorted(unknown_gates)})
        repro = d.get("chemical_reproposal", "off")
        if repro not in ("off", "on"):
            raise AuditContractError(
                f"chemical_reproposal 非法:{repro!r}", {"value": repro})
        per_product = d.get("per_product_gate_consumption", "on")
        if per_product not in ("on", "off"):
            raise AuditContractError(
                f"per_product_gate_consumption 非法:{per_product!r}",
                {"value": per_product})
        return cls(reject_gates=gates, chemical_reproposal=repro,
                   per_product_gate_consumption=per_product)


DEFAULT_ADMISSION_POLICY = AdmissionPolicy()


def _semantic_na_allowed(check: AuditCheck) -> bool:
    """真实语义不适用(允许缺席 R6 覆盖核算);缺输入未执行不算。"""
    allowed = SEMANTIC_NA_ALLOWED.get(check.name, ())
    reason = check.reason_code or ""
    return any(fragment in reason for fragment in allowed)


def _required_coverage_gaps(audit: ChemicalAudit) -> list[str]:
    """必需适用检查的覆盖缺口(R2-01:窄 scope 只是诊断)。

    缺口 = REQUIRED_CHECK_NAMES 中:审计内不存在,或状态 NA 但不在
    语义 NA 白名单(reason 不匹配)。verified/violated/unknown 都算
    已覆盖(它们进入对应决策行),只有"没执行"不算。
    """
    present = {c.name: c for c in audit.checks}
    gaps = []
    for name in REQUIRED_CHECK_NAMES:
        check = present.get(name)
        if check is None:
            gaps.append(name)
        elif check.status == CHECK_NOT_APPLICABLE \
                and not _semantic_na_allowed(check):
            gaps.append(name)
    return gaps


def decide_admission(
    audit: ChemicalAudit,
    *,
    policy: AdmissionPolicy | None = None,
    gate_decisions: dict[str, dict] | None = None,
    budget_state: dict | None = None,
    contract_violation: dict | None = None,
    product_state_refs: list[str] | None = None,
) -> tuple[str, list[str]]:
    """audit × 策略 → (admission_disposition, reasons)(纯函数)。

    gate_decisions:legacy_validation_to_gate_decisions 的输出(或手工
    同形状)。门禁键为 dict 且在 policy.reject_gates 内者参与 R2;
    per_product_verdicts(逐产物 verdict,含 position/accepted/reasons)
    被 R2p **真实消费** —— 全部共同产物被拒 ⇒ reject;部分 ⇒
    retain_conditional,被拒产物保留拒因、不可展开(R2-12:不删除被拒
    共同产物凑合法事件、不改冻结门禁真假、不把明确拒绝降成普通
    unknown)。gate_ref 为原产物引用,不参与判定。
    product_state_refs:共同产物 state_ref 按位次顺序(可选,用于把
    逐产物拒因落到具体产物引用;缺省用 position 表述)。
    budget_state:{"exhausted": bool, "waiting": bool, "reason": str}。
    contract_violation(R2b):表示契约违反的调用方报告(如 Hypothesis-
    ContractError 的 detail)→ reject + contract_violated_representation
    —— 不冒称结构不可解析或化学不可能。构造期异常 detail 必须由调用
    方映射传入(接口契约条款:不传则 R2b 不可达)。
    """
    pol = policy or DEFAULT_ADMISSION_POLICY
    reasons: list[str] = []

    # R1:实际输入语法非法 → reject(悬空引用走 R1b,CN-only 是 unknown)
    parse_check = next(
        (c for c in audit.checks
         if c.name == CHECK_STRUCTURE_PARSE_VALENCE), None)
    if parse_check is not None and parse_check.status == CHECK_VIOLATED:
        return ADMISSION_REJECT, ["R1:structure_unparseable"]

    # R1b:参与物 state 引用悬空(账本/引用完整性,非结构非法,R2-01)
    refs_check = next(
        (c for c in audit.checks
         if c.name == CHECK_PARTICIPANT_STATE_REFS), None)
    if refs_check is not None and refs_check.status == CHECK_VIOLATED:
        return ADMISSION_REJECT, [
            "R1b:participant_state_missing(账本/引用完整性问题,悬空"
            " state 引用;非结构不可解析):"
            + (refs_check.reason_code or "participant_state_missing")]

    # R2/R2p:活动门禁拒绝 + 逐产物门禁拒绝真实消费(R2-12)
    for gate_name, decision in (gate_decisions or {}).items():
        if not isinstance(decision, dict):
            continue  # per_product_verdicts(list)/gate_ref(dict 引用块)
        if gate_name in pol.reject_gates and not decision.get("ok", True):
            reasons.append(
                f"R2:active_gate_rejected:{gate_name}:"
                f"{decision.get('reason', '')[:120]}")
    if any(r.startswith("R2:") for r in reasons):
        return ADMISSION_REJECT, reasons

    if pol.per_product_gate_consumption == "on":
        per_product = (gate_decisions or {}).get("per_product_verdicts")
        per_product = per_product if isinstance(per_product, list) else []
        if per_product:
            rejected = [v for v in per_product
                        if not bool(v.get("accepted", False))]
            if rejected:
                def _product_label(v: dict) -> str:
                    pos = v.get("position")
                    if product_state_refs is not None \
                            and isinstance(pos, int) \
                            and 0 <= pos < len(product_state_refs):
                        return (f"position:{pos}:"
                                f"{product_state_refs[pos]}")
                    return f"position:{pos}"

                detail = ";".join(
                    f"{_product_label(v)}:"
                    + ",".join(str(r) for r in v.get("reasons", []))[:120]
                    for v in rejected)
                if len(rejected) == len(per_product):
                    return ADMISSION_REJECT, [
                        "R2p:per_product_gate_rejected:"
                        "all_products_gate_rejected(全部共同产物被活动"
                        "门禁拒绝;不改冻结门禁真假):" + detail]
                return ADMISSION_RETAIN_CONDITIONAL, [
                    "R2p:per_product_gate_rejected:some_products_gate_"
                    "rejected(部分共同产物被活动门禁拒绝:被拒产物保留"
                    "在事件中、拒因可追溯、不可展开;不删除被拒共同产物"
                    "凑合法事件):" + detail]
    elif pol.per_product_gate_consumption == "off":
        # §4(per-product off 披露):off 是显式版本化的 diagnostic 策略
        # —— 只关闭消费/阻断,**不关闭披露**;决策可为 expand,但被拒
        # 产物与未消费范围必须留痕(不得以干净理由码冒充全过)
        per_product = (gate_decisions or {}).get("per_product_verdicts")
        if isinstance(per_product, list):
            rejected = [v for v in per_product
                        if not bool(v.get("accepted", False))]
            if rejected:
                reasons.append(
                    "R2p_disclosure:per_product_gate_rejected:not_consumed"
                    "(策略显式 off:逐产物门禁拒绝未参与阻断,仅披露;"
                    "结果与未消费范围保留):"
                    + ";".join(
                        f"position:{v.get('position')}:"
                        + ",".join(str(r) for r in v.get("reasons", []))
                        [:80] for v in rejected))

    # R2b:表示契约违反(构造层报告;非化学)
    if contract_violation is not None:
        detail_code = str(contract_violation.get(
            "kind", contract_violation.get("reason_code", ""))[:120])
        return ADMISSION_REJECT, reasons + [
            "R2b:contract_violated_representation:"
            f"{detail_code}(输入表示违反契约,非结构不可解析、"
            "非化学不可能)"]

    # R3:当前场景有来源必要条件冲突 → defer(blocked)
    if audit.check_status(CHECK_CONDITION_CHECK) == CHECK_VIOLATED:
        return ADMISSION_DEFER, reasons + [
            "R3:current_scenario_conflict(当前环境相容路线不展开;"
            "假设保留,留原因,可展示为需不同条件的备选)"]

    # R4:预算/等待 → defer(独立原因)
    bs = budget_state or {}
    if bs.get("exhausted") or bs.get("waiting"):
        return ADMISSION_DEFER, reasons + [
            f"R4:budget_or_wait:{bs.get('reason', 'budget_or_waiting')}"]

    # R5d:声明账 violated(触发集合显式限定 {元素,电荷},mimo 3.2(4))
    violated = audit.violated_checks()
    account_violated = [c for c in violated
                        if c.name in R5D_TRIGGER_CHECKS]
    if account_violated:
        return ADMISSION_RETAIN_CONDITIONAL, reasons + [
            "R5d:declared_account_violated(声明与结构不一致,有证据的"
            "发现;不 reject —— 账不平不证明反应不存在;绝不计入"
            "'全部核实'):" + ",".join(c.name for c in account_violated)]

    # R5v:其他检查 violated(独立码,不冒称声明账不一致)
    other_violated = [c for c in violated
                      if c.name not in R5D_TRIGGER_CHECKS]
    if other_violated:
        return ADMISSION_RETAIN_CONDITIONAL, reasons + [
            "R5v:declared_violated_other(确定性检查发现的不一致,"
            "非元素/电荷声明账;不 reject):"
            + ",".join(c.name for c in other_violated)]

    # R5c:必需适用检查覆盖缺口(窄 audit_scope 只能作诊断,R2-01)
    coverage_gaps = _required_coverage_gaps(audit)
    if coverage_gaps:
        return ADMISSION_RETAIN_CONDITIONAL, reasons + [
            "R5c:required_check_coverage_missing(必需适用检查未执行/"
            "不在审计内;窄 scope 只是诊断,不满足 admission 覆盖核算):"
            + ",".join(coverage_gaps)]

    # R5:存在 unknown 检查(含因缺输入未执行)→ retain_conditional
    unknown_names = [c.name for c in audit.checks
                     if c.status == CHECK_UNKNOWN]
    if unknown_names:
        return ADMISSION_RETAIN_CONDITIONAL, reasons + [
            "R5:unknown_checks_present(不自动拒绝;可有界探索可能路径,"
            f"继承未解决依赖;未知步长不进确认单步指标):"
            + ",".join(unknown_names)]

    # R6:全部必需适用检查覆盖且 verified,无 unknown/violated/缺输入未执行
    # (语义 NA 白名单内的检查不阻塞)→ expand
    all_verified_or_semantic_na = all(
        c.status == CHECK_VERIFIED
        or (c.status == CHECK_NOT_APPLICABLE and _semantic_na_allowed(c))
        for c in audit.checks)
    if audit.checks and all_verified_or_semantic_na \
            and not coverage_gaps:
        return ADMISSION_EXPAND, reasons + ["R6:all_verified_no_conflict"]

    # R7:无适用检查:保守 retain(理由与 R5 分开,不冒充核实)
    return ADMISSION_RETAIN_CONDITIONAL, reasons + [
        "R7:no_applicable_checks_conservative_retain(无适用检查证据,"
        "不默认 expand,不以无证据冒充核实)"]


# ---------------------------------------------------- 旧门禁 → 新 admission(P2-2)


LEGACY_GATE_MAPPER_VERSION = PPV1_GATE_MAPPER_VERSION


def legacy_validation_to_gate_decisions(
    validation_payload: dict,
) -> dict:
    """旧 validation 产物 → 新 admission 的 gate_decisions 形状(版本化)。

    旧产物(nodes.validate_products 的 validation.json payload)结构:
    {"evidence_id", "gates": {"direction_source": {ok, reason},
     "atom_mapping": {ok, reason, value},
     "recorded_eligibility": {ok, reason}},
     "verdicts": [{position, accepted, reasons, ...}], ...}。

    映射:
    - gate_direction_source / gate_recorded_eligibility 进入默认
      reject 名单形状({"ok", "reason"} 原样透传,不改判);
    - gate_atom_mapping_declared 附带(不在默认 reject 名单,供策略
      显式消费);
    - **逐产物 verdicts 全量保留**(每共同产物的 accepted/拒因),
      不把总体 gates 摘要当作全量结果(元素门禁体现在逐产物 verdict);
    - gate_ref:原产物引用(调用方传 task_id/artifact hash)。
    """
    gates = validation_payload.get("gates") or {}
    out: dict[str, dict] = {}
    if "direction_source" in gates:
        out[GATE_NAME_DIRECTION_SOURCE] = {
            "ok": bool(gates["direction_source"].get("ok", False)),
            "reason": str(gates["direction_source"].get("reason", ""))[:300]}
    if "recorded_eligibility" in gates:
        out[GATE_NAME_RECORDED_ELIGIBILITY] = {
            "ok": bool(gates["recorded_eligibility"].get("ok", False)),
            "reason": str(gates["recorded_eligibility"].get(
                "reason", ""))[:300]}
    if "atom_mapping" in gates:
        out["gate_atom_mapping_declared"] = {
            "ok": bool(gates["atom_mapping"].get("ok", False)),
            "reason": str(gates["atom_mapping"].get("reason", ""))[:300],
            "value": gates["atom_mapping"].get("value")}
    out["per_product_verdicts"] = [
        {"position": v.get("position"),
         "accepted": bool(v.get("accepted", False)),
         "reasons": list(v.get("reasons", []))}
        for v in validation_payload.get("verdicts", [])]
    out["gate_ref"] = {
        "evidence_id": validation_payload.get("evidence_id", ""),
        "mapper_version": LEGACY_GATE_MAPPER_VERSION,
    }
    return out


# ---------------------------------------------------------------- 供体诊断


@dataclass
class DonorConsistencyDiagnostic:
    """§8 供体诊断(v3:实际净变化判定 + 声明–执行对账 + 联合中心映射)。

    本诊断的**命名与范围**:供体迁移的**实际净变化区域诊断** —— 核验
    (i)执行前后结构的真实净变化集合(键 diff ∪ 原子增删 ∪ 逐原子
    形式电荷/氢数/立体 diff),(ii)声明编辑与实际执行是否对账,
    (iii)实际变化是否局限于对齐后的供体中心区域(**或其联合对称像**)。
    **不**核验供体反应自身的变换模板(供体侧预期键变化对比,S3 接线);
    图等价 ≠ 酶识别/机制等价(symmetric_equivalent 只是拓扑对称证据)。

    strict 轴使用与 ChemicalState 同一事实源的严格表示(含增强立体与
    v3 规范化:ABS/整组反转归一);legacy_cn_match 仅旁证,不进计数。
    center_match_basis ∈ {direct, symmetric_equivalent},仅 True 时
    非空;symmetric_equivalent 由**联合图映射**证明(存在单一自同构把
    整个中心集合映到实际变化集合),单原子对称轨道不冒充联合等价
    (R2-03)。
    """

    strict_target_match: bool | None
    legacy_cn_match: bool | None       # 旁证(corroborating),不进计数
    reaction_center_match: bool | None
    center_match_basis: str = ""       # direct | symmetric_equivalent(仅 True)
    extra_changes: list[dict] = field(default_factory=list)  # 逐原子 Δ 摘要
    alignment_ref: str = ""
    missing_info_reasons: list[str] = field(default_factory=list)
    executed_bond_changes: list[dict] = field(default_factory=list)
    # v3(R2-03):
    declaration_only: list[str] = field(default_factory=list)
        # 声明触及但实际未变化的原子(不参与 center 判定)
    declaration_mismatches: list[str] = field(default_factory=list)
        # 声明–执行净效应失配明细
    equivalence_basis: str = ""        # 等价类验证口径(提供类时)
    joint_mapping: dict = field(default_factory=dict)
        # symmetric_equivalent 的联合映射证据(中心像/自同构数)
    net_change_empty: bool = False     # 执行前后结构身份一致(零净变化)
    # v4(R3-01/03/05):
    center_property_deltas: list[dict] = field(default_factory=list)
        # **中心原子**的属性 Δ(电荷/ΔH/构型/准确 CIP 标签)披露 ——
        # ops 对账不覆盖属性,未声明的中心属性变化经此可见(E-iii);
        # 只披露不判 center(区域归属由 changed 集合判定)
    center_evidence: dict = field(default_factory=dict)
        # 绑定本诊断全部输入的证据载荷(checker scope/各轴结论/
        # bound_inputs/**proof_record 完整输入集**),供 audit 的
        # transformation_center 证据门消费(R3-01/R4-01:跨反应复用/
        # 改产物/无依据 True/自报字段拼接均不得认证 —— audit 内部
        # 复跑本确定性 checker 复核)
    # v5(R4-07):
    stereo_comparison_unsupported_atoms: list[str] = field(
        default_factory=list)
        # 立体轴**比较支持范围外**的原子清单(非四面体手性标签/
        # 配体集合改变后不可比)—— 公开列项,不静默缺席;中心外
        # 存在此类原子 ⇒ center 不可判 True(区域约束对该轴不可核)
    schema_version: str = PPV1_DONOR_DIAGNOSTIC_VERSION

    def to_dict(self) -> dict:
        return dict(self.__dict__)


def _edit_atom_ids(edits: list[dict]) -> set[str]:
    """真实编辑协议(v43-editproto-2)中出现的原子标识(atom1/atom2)。"""
    out: set[str] = set()
    for edit in edits or []:
        for key in ("atom1", "atom2", "new_atom_id"):
            if edit.get(key) is not None:
                out.add(str(edit[key]))
    return out


_MAX_AUTOMORPHISM_MATCHES = 1024


def _kekulized(mol: Chem.Mol) -> Chem.Mol:
    """芳香表示归一副本(Kekulé 化;失败原样返回 —— 同一分子图)。"""
    try:
        m = Chem.Mol(mol)
        Chem.Kekulize(m, clearAromaticFlags=True)
        return m
    except Exception:
        return Chem.Mol(mol)


def _bond_changes(before: Chem.Mol, after_mapped: Chem.Mol,
                  id_to_idx_after: dict[str, int]) -> list[dict]:
    """执行前后结构的实际键变化集合(键级/成断键/**键级立体**;原子
    增删另列)。

    before/after 均按 Kekulé 归一后再比较(芳香/kekulé 表示差异不是
    化学变化)。after_mapped:带映射号的执行图产物(映射号 = 执行图
    原子 idx+1);id_to_idx_after:MoleCode ID → 执行图 idx。
    返回 [{atom1_id, atom2_id, kind: order_change|bond_formed|
    bond_broken|bond_stereo_change, from_order, to_order}]。

    R4-07:键级立体(cis/trans,E/Z)按**映射原子对的几何**入 diff
    (同一原子对前后 GetStereo 不同 ⇒ bond_stereo_change,from/to 为
    立体名)——身份键不同而图轴全空时不得称"实际净变化为空"(复审
    interface_ez_only/off_center 反例);kind 与 from/to 进入声明对账
    签名(ops 声明语言无法表达 E/Z ⇒ 执行图若带未声明立体变化即为
    失配,接口合成不得冒充执行器结果)。
    """
    before_k = _kekulized(before)
    after_k = _kekulized(after_mapped)
    before_bonds: dict[frozenset, tuple[str, str]] = {}
    for bond in before_k.GetBonds():
        key = frozenset((bond.GetBeginAtomIdx(), bond.GetEndAtomIdx()))
        before_bonds[key] = (_bond_order_name(bond.GetBondType()),
                             str(bond.GetStereo()))
    after_bonds: dict[frozenset, tuple[str, str]] = {}
    for bond in after_k.GetBonds():
        a = bond.GetBeginAtom().GetAtomMapNum() - 1
        b = bond.GetEndAtom().GetAtomMapNum() - 1
        after_bonds[frozenset((a, b))] = (
            _bond_order_name(bond.GetBondType()), str(bond.GetStereo()))

    def idx_to_id(idx: int) -> str:
        for aid, i in id_to_idx_after.items():
            if i == idx:
                return aid
        return f"idx:{idx}"

    changes: list[dict] = []
    for key, (order_after, stereo_after) in after_bonds.items():
        prior = before_bonds.get(key)
        a, b = tuple(key)
        if prior is None:
            changes.append({"atom1_id": idx_to_id(a),
                            "atom2_id": idx_to_id(b),
                            "kind": "bond_formed",
                            "from_order": "", "to_order": order_after})
        elif prior[0] != order_after:
            changes.append({"atom1_id": idx_to_id(a),
                            "atom2_id": idx_to_id(b),
                            "kind": "order_change",
                            "from_order": prior[0],
                            "to_order": order_after})
        elif prior[1] != stereo_after:
            # R4-07:同键同键级而立体几何不同 ⇒ 键级立体变化
            changes.append({"atom1_id": idx_to_id(a),
                            "atom2_id": idx_to_id(b),
                            "kind": "bond_stereo_change",
                            "from_order": prior[1],
                            "to_order": stereo_after})
    for key, (order_before, _stereo_before) in before_bonds.items():
        if key not in after_bonds:
            a, b = tuple(key)
            changes.append({"atom1_id": idx_to_id(a),
                            "atom2_id": idx_to_id(b),
                            "kind": "bond_broken",
                            "from_order": order_before, "to_order": ""})
    changes.sort(key=lambda c: (c["atom1_id"], c["atom2_id"], c["kind"]))
    return changes


def _bond_order_name(bond_type) -> str:
    return {Chem.BondType.SINGLE: "single",
            Chem.BondType.DOUBLE: "double",
            Chem.BondType.TRIPLE: "triple"}.get(bond_type, str(bond_type))


def _cip_labels(mol: Chem.Mol) -> dict[int, str]:
    """准确 CIP 标签(rdCIPLabeler;仅用于**披露**,不作变化判据)。

    R3-03:legacy AssignStereochemistry 在自由基/配体重排产物上会伪造
    远端 CIP 翻转;准确标签器修正标签本身,但**任何** R/S 标签 diff 都
    不能当构型变化证明(配体优先级重排也会翻转标签)——构型比较用
    映射配体下的奇偶法(_stereo_config_delta)。
    """
    out: dict[int, str] = {}
    try:
        from rdkit.Chem.rdCIPLabeler import AssignCIPLabels

        m = Chem.Mol(mol)
        AssignCIPLabels(m)
        for atom in m.GetAtoms():
            if atom.HasProp("_CIPCode"):
                out[atom.GetIdx()] = atom.GetProp("_CIPCode")
    except Exception:
        pass
    return out


_TET_CHIRAL = (Chem.ChiralType.CHI_TETRAHEDRAL_CW,
               Chem.ChiralType.CHI_TETRAHEDRAL_CCW)


def _stereo_config_delta(before_atom, after_atom) -> str | None:
    """映射配体下的四面体构型比较(R3-03,奇偶法)。

    对前后**配体集合相同**(按构造 idx 映射)的原子:构型由
    (手性标签, 邻居序)共同决定;两 mol 的邻居序经配体映射成置换,
    偶置换要求标签相同、奇置换要求标签相反才表示**同一构型**。
    返回:
    - "":构型保持(无变化);
    - "stereo":构型反转(真实翻转);
    - "stereo_lost"/"stereo_created":一侧有指定手性另一侧没有;
    - None:**不支持比较**(非四面体手性标签,或配体集合改变 ——
      后者按 changed 处理由键 diff/增删承载,不在此伪造判定)。
    CIP 标签(legacy 或准确)不参与本判定 —— 邻居序变化时直接比较
    @/@@ 或 R/S 都会把优先级重排误报成构型变化(复审 R3-03 两组
    真实反例的根因)。
    """
    b_tag, a_tag = before_atom.GetChiralTag(), after_atom.GetChiralTag()
    b_chiral = b_tag in _TET_CHIRAL
    a_chiral = a_tag in _TET_CHIRAL
    # R4-07/mimo 5.2(a) 条件 1:**非四面体手性标签先判 unsupported**
    # (标签类型是判据,不是"是否四面体指定")——两侧同为非四面体
    # (平面/四方/八面/三角双锥,金属配合物常见)甚至一侧非四面体
    # 另一侧 UNSPECIFIED,都不得返回"构型保持"的肯定结论
    if b_tag not in _TET_CHIRAL and b_tag != \
            Chem.ChiralType.CHI_UNSPECIFIED:
        return None  # 非四面体手性(如平面手性):不支持
    if a_tag not in _TET_CHIRAL and a_tag != \
            Chem.ChiralType.CHI_UNSPECIFIED:
        return None
    if not b_chiral and not a_chiral:
        return ""
    if not (b_chiral and a_chiral):
        return "stereo_created" if a_chiral else "stereo_lost"
    # 邻居按构造 idx 映射(after 用映射号-1;before 用自身 idx)
    b_nbrs = [n.GetIdx() for n in before_atom.GetNeighbors()]
    a_nbrs = [n.GetAtomMapNum() - 1 if n.GetAtomMapNum() else -1
              for n in after_atom.GetNeighbors()]
    if sorted(b_nbrs) != sorted(a_nbrs):
        return None  # 配体集合改变:键 diff/增删承载,不在此判定
    perm = [a_nbrs.index(x) for x in b_nbrs]  # before 序 → after 序置换
    inversions = sum(1 for i in range(len(perm))
                     for j in range(i + 1, len(perm))
                     if perm[i] > perm[j])
    same_config = ((inversions % 2 == 0) == (b_tag == a_tag))
    return "" if same_config else "stereo"


def _atom_property_diffs(
        before: Chem.Mol, after_mapped: Chem.Mol,
        id_to_idx_before: dict[str, int],
        id_to_idx_after: dict[str, int]) -> tuple[set[str], dict[str, dict]]:
    """逐原子属性 diff(形式电荷/ΔH/构型/Δ同位素)∪ 原子增删(R3-03 v4)。

    - 立体用**映射配体下的奇偶构型比较**(_stereo_config_delta);
      CIP 标签(rdCIPLabeler 准确口径)仅入披露记录 —— 标签 R→S
      可能只是配体优先级重排,不是构型变化;非四面体手性 ⇒ 该原子
      立体轴记 unknown(stereo_comparison_unsupported),不入变化集;
    - **同位素 diff(S4 回修 r3,PPV1-ISO-01,方案 A 兑现冻结判据五
      §5 既有承诺)**:逐原子 GetIsotope() 比较,deltas 机读码
      "isotope",记录 isotope=[before,after] —— 入 changed atoms、
      中心外 extra_changes、中心属性披露与 audit 公开重算(复跑本
      checker 同轴);身份键(chemstate)本就保留同位素,零净变化
      分支与同位素轴自洽(身份相同 ⇒ 同位素必相同);
    - after 按映射号对齐(idx+1);属性不变但被键变化触及的原子不在
      本 diff 集(由键 diff 承接)。
    """
    after_by_mapnum = {atom.GetAtomMapNum() - 1: atom
                       for atom in after_mapped.GetAtoms()}
    before_cip = _cip_labels(before)
    # after 标签按映射号(构造 idx)对齐:解析序 ≠ 构造序
    after_cip: dict[int, str] = {}
    for parse_idx, label in _cip_labels(after_mapped).items():
        mapnum = after_mapped.GetAtomWithIdx(parse_idx).GetAtomMapNum()
        if mapnum:
            after_cip[mapnum - 1] = label

    changed: set[str] = set()
    records: dict[str, dict] = {}
    all_ids = set(id_to_idx_before) | set(id_to_idx_after)
    for aid in sorted(all_ids):
        bi = id_to_idx_before.get(aid)
        ai = id_to_idx_after.get(aid)
        if bi is None and ai is not None:
            records[aid] = {"presence": "atom_added",
                            "element": after_by_mapnum[ai].GetSymbol()
                            if ai in after_by_mapnum else ""}
            changed.add(aid)
        elif ai is None and bi is not None:
            records[aid] = {"presence": "atom_removed",
                            "element": before.GetAtomWithIdx(bi).GetSymbol()}
            changed.add(aid)
        else:
            b_atom = before.GetAtomWithIdx(bi)
            a_atom = after_by_mapnum.get(ai)
            if a_atom is None:
                continue  # 映射号缺失,无法对齐(中心判定按未解析处理)
            b_charge, a_charge = (b_atom.GetFormalCharge(),
                                  a_atom.GetFormalCharge())
            b_h, a_h = b_atom.GetTotalNumHs(), a_atom.GetTotalNumHs()
            # S4 回修 r3(PPV1-ISO-01):同位素 diff 入实际净变化集
            # (冻结判据五 §5 现义兑现;身份键含同位素,故该轴与
            # 零净变化分支自洽)
            b_iso, a_iso = b_atom.GetIsotope(), a_atom.GetIsotope()
            deltas: list[str] = []
            unsupported = False
            if b_charge != a_charge:
                deltas.append("formal_charge")
            if b_h != a_h:
                deltas.append("h_count")
            if b_iso != a_iso:
                deltas.append("isotope")
            stereo_delta = _stereo_config_delta(b_atom, a_atom)
            if stereo_delta is None:
                unsupported = True
            elif stereo_delta:
                deltas.append(stereo_delta)
            if deltas:
                changed.add(aid)
            records[aid] = {
                "element": b_atom.GetSymbol(),
                "formal_charge": [b_charge, a_charge],
                "h_count": [b_h, a_h],
                # 同位素轴披露(before/after;元素不变的核素变化)
                "isotope": [b_iso, a_iso],
                # 准确 CIP 标签(披露;标签 diff ≠ 构型变化)
                "cip_labels": [before_cip.get(bi, ""),
                               after_cip.get(ai, "")],
                "property_delta": ";".join(deltas)}
            if unsupported:
                records[aid]["stereo_comparison_unsupported"] = True
    return changed, records


def _simulate_declared_edits(
        before: Chem.Mol, edits: list[dict],
        id_to_idx_before: dict[str, int],
        id_to_idx_after: dict[str, int]) -> tuple[Chem.Mol | None,
                                                   list[str]]:
    """按冻结执行器语义(v43-editproto-2)模拟**声明的有序编辑序列**。

    返回 (带映射号的声明终态图, 前置违约列表);违约非空时图为 None。
    映射号 = 构造 idx+1;新增原子沿用执行图的构造 idx+1(与实际执行
    同一索引空间)。**不改冻结执行器**(services/atom_tool.py)——
    本函数是净效应与前置条件的镜像重推导(v5,R4-06):
    - **活 ID 表**:先增后引合法(与执行器一致)——add_atom 声明的
      新 ID **立即**进入 id→idx 映射,后续操作(含 anchor 引用新
      原子、change_bond_order 作用于新键)按列表时点解析(复审
      real_add_then_add/change 反例:引用先前新增原子/新键曾被误报
      declared_edits_not_simulable);
    - **逐操作前置条件**(与 execute_edits 同语义):break_bond 键须
      存在;form_bond 键须不存在;change_bond_order 须键存在**且
      from_order == 当前键级**(错误 from_order 被冻结执行器拒绝,
      镜像同样拒 —— 复审 interface_wrong_from_order 反例:错误声明
      曾零失配通过);
    - add_atom 隐含 anchor–新原子单键(执行器协议行为,atom_tool.py
      的 add_atom 自动形成,不需要多余 form_bond 声明,R3-05);
    - 有序操作按净效应结算:中间态不留痕(s→d→s→d 终态=double)。
    """
    failures: list[str] = []
    # 执行器路径的第一步(atom_tool.py:417):编辑前先
    # Kekulize(clearAromaticFlags=True) —— 芳香底物以显式键级进入
    # 编辑序列;模拟必须镜像(否则芳香标志残留产生不同 Kekulé 指派)
    mol = Chem.Mol(before)
    try:
        Chem.Kekulize(mol, clearAromaticFlags=True)
    except Exception:
        pass  # 少数结构无法 kekulize:按芳香形式继续(将如实失配)
    rw = Chem.RWMol(mol)
    for atom in rw.GetAtoms():
        atom.SetAtomMapNum(atom.GetIdx() + 1)
    # R4-06:活 ID 表 —— 先增后引(执行器 validate_edits/execute_edits
    # 的列表时点语义);新原子用执行图最终构造 idx(与实际执行同空间)
    live_idx: dict[str, int] = dict(id_to_idx_before)
    for i, edit in enumerate(edits or []):
        tag = f"edit[{i}]"
        op = str(edit.get("op", "")).lower()
        a1 = str(edit.get("atom1")) if edit.get("atom1") is not None \
            else None
        if op == "add_atom":
            new_id = str(edit.get("new_atom_id", ""))
            element = str(edit.get("element", ""))
            anchor_idx = live_idx.get(a1) if a1 else None
            new_idx = id_to_idx_after.get(new_id)
            if anchor_idx is None:
                failures.append(
                    f"declared_precondition_violated:unknown_atom:"
                    f"{a1}:{tag}(镜像复核:anchor 原子按列表时点未声明)")
                continue
            if new_idx is None or not element:
                failures.append(
                    f"declared_precondition_violated:bad_add_atom:"
                    f"{new_id!r}:{element!r}:{tag}(镜像复核:new_atom_id"
                    " 不在执行图索引空间或元素缺失)")
                continue
            added = rw.AddAtom(Chem.Atom(element))
            rw.GetAtomWithIdx(added).SetAtomMapNum(new_idx + 1)
            rw.AddBond(anchor_idx, added, Chem.BondType.SINGLE)
            live_idx[new_id] = added
            continue
        a2 = str(edit.get("atom2")) if edit.get("atom2") is not None \
            else None
        i1 = live_idx.get(a1) if a1 else None
        i2 = live_idx.get(a2) if a2 else None
        if i1 is None or i2 is None:
            unknown = [x for x in (a1, a2)
                       if x is not None and x not in live_idx]
            failures.append(
                f"declared_precondition_violated:unknown_atom:"
                f"{','.join(str(u) for u in unknown)}:{tag}"
                "(镜像复核:引用原子按列表时点不在活 ID 表)")
            continue
        bond = rw.GetBondBetweenAtoms(i1, i2)
        if op == "break_bond":
            if bond is None:
                failures.append(
                    f"declared_precondition_violated:bond_not_present:"
                    f"{a1}~{a2}:{tag}(镜像复核:断不存在的键)")
                continue
            rw.RemoveBond(i1, i2)
        elif op == "form_bond":
            if bond is not None:
                failures.append(
                    f"declared_precondition_violated:bond_already_present:"
                    f"{a1}~{a2}:{tag}(镜像复核:对已有键 form_bond)")
                continue
            rw.AddBond(i1, i2, Chem.BondType.SINGLE)
        elif op == "change_bond_order":
            to_order = str(edit.get("to_order", "")).lower()
            from_order = str(edit.get("from_order", "")).lower()
            bond_type = {"single": Chem.BondType.SINGLE,
                         "double": Chem.BondType.DOUBLE,
                         "triple": Chem.BondType.TRIPLE}.get(to_order)
            if bond_type is None or bond is None:
                reason = ("bad_bond_order:"
                          f"{to_order!r}") if bond is not None \
                    else ("bond_not_present:"
                          f"{a1}~{a2}")
                failures.append(
                    f"declared_precondition_violated:{reason}:{tag}"
                    "(镜像复核:键级声明不可达)")
                continue
            have = {Chem.BondType.SINGLE: "single",
                    Chem.BondType.DOUBLE: "double",
                    Chem.BondType.TRIPLE: "triple"}.get(
                        bond.GetBondType(), str(bond.GetBondType()))
            if have != from_order:
                # R4-06:from_order 是协议显式前置条件 —— 冻结执行器
                # 拒绝错误 from_order(bond_order_mismatch),镜像同拒;
                # 声明不得零失配通过
                failures.append(
                    f"declared_precondition_violated:bond_order_mismatch:"
                    f"{a1}~{a2}:expected_{from_order}_have_{have}:{tag}"
                    "(镜像复核:声明前置键级与列表时点实际键级不符;"
                    "冻结执行器拒绝该声明)")
                continue
            rw.GetBondBetweenAtoms(i1, i2).SetBondType(bond_type)
        else:
            failures.append(
                f"declared_precondition_violated:unknown_op:{op}:{tag}"
                "(镜像复核:未知操作,执行器会拒)")
    if failures:
        return None, failures
    out = rw.GetMol()
    # 执行器路径的最后一步:SanitizeMol(失败 ⇒ 执行器本会报
    # sanitize_failed;此处失败按原样比较,由失配/unknown 检出)
    try:
        Chem.SanitizeMol(out)
    except Exception:
        pass
    # R6(R5-08):镜像终态与冻结执行器同一归一 —— 执行器产物
    # (product_mapped_smiles)是 MolToSmiles 序列化后被消费的(映射号
    # 以 [C:1] 形式随序列化穿越),实际比较对象是重解析图;内存镜像
    # 不走序列化会残留陈旧键立体(断邻位 σ 键后双键端烯化,重解析
    # STEREONONE 而内存 STEREOE)⇒ 伪 undeclared_bond_change。镜像
    # 同走写出/重解析后,键变化集合与实际一致,已声明断键的自然立体
    # 后果不再称漏申报;序列化/重解析失败或 None ⇒ 按原内存图
    # (如实失配)。不改冻结执行器。
    try:
        serialized = Chem.MolToSmiles(out)
        reparsed = Chem.MolFromSmiles(serialized) if serialized else None
        if reparsed is not None:
            out = reparsed
    except Exception:
        pass
    return out, []


def _bond_change_signature(changes: list[dict]) -> list[tuple]:
    """键变化集合的规范签名(排序比较用)。"""
    return sorted(
        (tuple(sorted((c["atom1_id"], c["atom2_id"]))), c["kind"],
         str(c.get("from_order", "")), str(c.get("to_order", "")))
        for c in changes)


def _declaration_accounting(
        mol_before: Chem.Mol, edits: list[dict],
        id_to_idx_before: dict[str, int],
        id_to_idx_after: dict[int, int] | dict[str, int],
        actual_bond_changes: list[dict],
        actual_added_ids: list[str]) -> tuple[list[str], list[dict]]:
    """声明–执行**净效应**对账(R3-05,ops 级)。

    把声明编辑序列按冻结执行器语义模拟到终态,比较:
    - 键变化集合(成/断/键级,kekulé 归一):声明终态 vs 实际执行
      的 before→actual diff;**中间操作不必留在终态 diff**
      (s→d→s→d 净效应 = double,不再逐条要求中间态相等);
    - 原子增删集合:add_atom 的隐含 anchor 键由模拟自然形成,不是
      undeclared_bond_change(执行器协议行为)。
    原子属性(电荷/ΔH/构型)**不在对账范围**(ops 声明语言没有对应
    操作;其检出走属性 diff 披露 + strict 轴,mimo 5.3(3))。
    返回 (失配明细, 声明终态键变化)。
    """
    mismatches: list[str] = []
    declared_final, precondition_failures = _simulate_declared_edits(
        mol_before, edits, id_to_idx_before, id_to_idx_after)
    if declared_final is None:
        # R4-06:前置违约/不可模拟,机读码镜像执行器语义(结构化,
        # 不再笼统 declared_edits_not_simulable)
        mismatches.extend(precondition_failures or [
            "declared_edits_not_simulable(引用未知原子/键或未知操作;"
            "执行器语义下声明不可达)"])
        return mismatches, []
    declared_bond_changes = _bond_changes(
        mol_before, declared_final, id_to_idx_after)
    declared_sig = _bond_change_signature(declared_bond_changes)
    actual_sig = _bond_change_signature(actual_bond_changes)
    if declared_sig != actual_sig:
        declared_pairs = {tuple(sorted((c["atom1_id"], c["atom2_id"])))
                          for c in declared_bond_changes}
        actual_pairs = {tuple(sorted((c["atom1_id"], c["atom2_id"])))
                        for c in actual_bond_changes}
        for pair in sorted(declared_pairs - actual_pairs):
            mismatches.append(
                f"declared_change_not_executed:{sorted(pair)}"
                "(净效应:该键变化未实际发生)")
        for pair in sorted(actual_pairs - declared_pairs):
            mismatches.append(
                f"undeclared_bond_change:{sorted(pair)}"
                "(净效应:实际发生了未声明的键变化)")
        common = declared_pairs & actual_pairs
        for pair in sorted(common):
            d = next(c for c in declared_bond_changes
                     if tuple(sorted((c["atom1_id"], c["atom2_id"])))
                     == pair)
            a = next(c for c in actual_bond_changes
                     if tuple(sorted((c["atom1_id"], c["atom2_id"])))
                     == pair)
            if (d["kind"], d.get("from_order"), d.get("to_order")) != \
                    (a["kind"], a.get("from_order"), a.get("to_order")):
                mismatches.append(
                    f"declared_to_order_mismatch:{sorted(pair)}:"
                    f"declared:{d['kind']}:{d.get('from_order')}"
                    f"->{d.get('to_order')}:actual:{a['kind']}:"
                    f"{a.get('from_order')}->{a.get('to_order')}")
    declared_added = {str(e.get("new_atom_id", "")) for e in edits or []
                      if str(e.get("op", "")).lower() == "add_atom"
                      and str(e.get("new_atom_id", ""))}
    actual_added = set(actual_added_ids)
    for new_id in sorted(declared_added - actual_added):
        mismatches.append(f"declared_atom_not_added:{new_id}")
    for new_id in sorted(actual_added - declared_added):
        mismatches.append(f"undeclared_atom_added:{new_id}")
    return mismatches, declared_bond_changes


def _validate_equivalence_classes(equivalence_classes: list,
                                  current_mol: Chem.Mol,
                                  id_to_idx: dict[str, int]) -> tuple[
                                      dict[str, set[str]], list[list[str]]]:
    """等价类从分子图验证(F11:不采信自报任意集合)。

    仅当等价类成员在当前分子图上对称等价(RDKit 无 tie-breaking 的
    canonical rank 同类;口径 equivalence_basis=
    canonical_rank_breakTies_false,拓扑对称的实现近似,非完整自同构
    群枚举)时采信;含非等价成员或未知原子的类整体弃用并记入
    rejected(不部分采用)。返回 (采信的等价展开 dict, 被拒的类列表)。

    v3 注意:等价类**不再参与 center 判定**(由联合图映射取代,
    R2-03);本验证仅作披露 —— 自报类的采信/拒用状态进
    missing_info_reasons。
    """
    if current_mol is None:
        return {}, [list(c) for c in (equivalence_classes or [])]
    symmetry_classes = list(Chem.CanonicalRankAtoms(
        current_mol, breakTies=False))
    out: dict[str, set[str]] = {}
    rejected: list[list[str]] = []
    for eq_class in equivalence_classes or []:
        members = [str(a) for a in eq_class]
        idxs = [id_to_idx.get(m) for m in members]
        if any(i is None for i in idxs):
            rejected.append(members)
            continue
        ranks = {symmetry_classes[i] for i in idxs}
        if len(ranks) == 1:
            for m in members:
                out.setdefault(m, set()).update(members)
        else:
            rejected.append(members)
    return out, rejected


def _joint_symmetric_image(
        before: Chem.Mol, center_idxs: set[int],
        changed_idxs: set[int]) -> dict | None | str:
    """联合中心对称(v4 手性感知;v5 R4-07 非四面体门):存在**单一
    保手性图自同构**把**整个**中心集合映到实际变化集合。

    - useChirality=True(R3-02):忽略指定手性会把立体可区分位点判
    等价(实测 meso 底物 blind=2/aware=1——两端的严格身份不同);
    无手性/非指定骨架不受影响(butane/cyclohexane blind=aware);
    真对称正例保留((2S,4S)-戊二醇 C2 互换 aware=2);
    - 支持范围(v5 声明为三类,R4-07/mimo probe3):①绝对四面体
    **全部指定**;②**无手性骨架**(无任何四面体中心);③**部分
    指定/全未指定**四面体中心——按所写表示参与保手性匹配(指定↔
    未指定互换被拒,全未指定两端产物同一身份时可判 True);
    - **增强立体组(AND/OR)⇒ unsupported ⇒ unknown**(R3-02);
      **非四面体手性标签 ⇒ unsupported ⇒ unknown**(R4-07:
      useChirality 只覆盖四面体标签,平面/四方/八面/三角双锥中心
      被其忽略 ⇒ 自同构会把非四面体可区分位点判等价,联合映射
      不可信 —— 复审 non_tetra_joint 反例:非四面体底物 center
      被误授 True);
    - 返回 dict(找到,含中心像与自同构数)/ None(确定不存在)/
      "truncated"(搜索截断)/ "unsupported_stereo"(上述立体范围
      外)。单原子各自可替换不等于整个中心存在一致替换(R2-03)。
    """
    if not center_idxs or not changed_idxs:
        return None
    if len(center_idxs) != len(changed_idxs):
        return None
    if before.GetStereoGroups():
        return "unsupported_stereo"
    for atom in before.GetAtoms():
        tag = atom.GetChiralTag()
        if tag not in _TET_CHIRAL and tag != \
                Chem.ChiralType.CHI_UNSPECIFIED:
            return "unsupported_stereo"  # 非四面体手性:范围外
    try:
        matches = before.GetSubstructMatches(
            before, uniquify=False, useChirality=True,
            maxMatches=_MAX_AUTOMORPHISM_MATCHES)
    except Exception:
        return "truncated"
    if len(matches) >= _MAX_AUTOMORPHISM_MATCHES:
        return "truncated"
    for match in matches:
        image = {match[i] for i in center_idxs if i < len(match)}
        if image == set(changed_idxs):
            return {"center_image": sorted(image),
                    "n_automorphisms": len(matches),
                    "chirality_aware": True}
    return None


def check_edit_against_donor(
    *,
    current: dict,
    donor: dict,
    alignment: dict,
    expectation: dict,
    result: dict,
    edits: list[dict],
) -> DonorConsistencyDiagnostic:
    """§7.1 固定接口(v3):消费**真实 AtomTool 编辑协议**的诊断。

    输入(与 v43-editproto-2 / execute_edits 输出对接):
    - current: {"smiles": str, "atom_id_map": {id: idx}}(编辑前
      MoleculeRender 的渲染事实);
    - donor: {"center_atom_ids": [...]}(供体反应变换中心的供体侧原子);
    - alignment: {"status": resolved|ambiguous|unavailable,
      "donor_to_current": {donor_atom: current_atom},
      "equivalence_classes": [[atom, ...]](验证后仅披露,不参与判定),
      "ref": str};
    - expectation: {"target_smiles": str}(供体迁移预期产物);
    - result: execute_edits 的输出 dict(ok/product_smiles/
      product_mapped_smiles/atom_id_map);ok=False ⇒ 全轴 unknown +
      execution_failed;
    - edits: 真实协议编辑列表(break_bond/form_bond/change_bond_order/
      add_atom,含 atom1/atom2/new_atom_id)。

    v3 判定基础 = **实际净变化集合**(R2-03):
    - 结构身份一致(执行前后同一分子)⇒ 零净变化 ⇒ center=
      unknown(no_executed_change),永不 True —— 声明的编辑原子单独
      列 declaration_only,不并入变化集(v2 的"声明触及即命中"废除);
    - 声明–执行对账(_declaration_accounting):不一致 ⇒
      declaration_mismatches,strict/center 不得 verified(unknown);
    - plain 产物与 mapped 执行图对账:不一致 ⇒ 两轴 unknown +
      plain_product_mapped_product_disagreement;
    - center:实际变化 ⊆ 对齐中心(direct)或存在联合自同构像
      (symmetric_equivalent)⇒ True;中心外变化 ⇒ False +
      extra_changes(逐原子 element/形式电荷/ΔH/Δ立体 before/after);
    - 全部供体中心原子必须有映射(部分缺 ⇒ unknown,不部分判定);
      自同构搜索截断 ⇒ unknown(automorphism_search_truncated)。
    """
    missing: list[str] = []
    alignment_status = str(alignment.get("status", "unavailable"))
    if alignment_status not in ("resolved", "ambiguous", "unavailable"):
        raise AuditContractError(
            f"alignment.status 非法:{alignment_status!r}",
            {"status": alignment_status})
    alignment_ref = str(alignment.get("ref", "") or stable_id(
        "align", str(alignment.get("donor_to_current", ""))))

    execution_ok = bool(result.get("ok"))
    if not execution_ok:
        return DonorConsistencyDiagnostic(
            strict_target_match=None, legacy_cn_match=None,
            reaction_center_match=None, center_match_basis="",
            alignment_ref=alignment_ref,
            missing_info_reasons=[
                "execution_failed:" +
                ";".join(result.get("reasons", []) or [])[:200]],
            executed_bond_changes=[])

    # ---- R6-02(R7):供体诊断全部原始字符串入口与工厂/strict 同源守卫 ----
    # current/mapped/plain/target 的原始串此前直接 MolFromSmiles 解析,
    # 绕过工厂/strict 的输入侧注册感知校验:RDKit 静默丢弃 |r| 等未
    # 登记项后,绑定身份来自剥标记的解析串而 proof 保留原串 —— 原始
    # 标记事实静默丢失仍 True/True/verified/R6。四个入口统一在解析前
    # 过同一 _guard_input_cx_classes(build_chemical_state /
    # strict_identity_of 同一守卫);未登记/并列未知项 ⇒ 结构化拒绝
    # (不剥身份后当 verified 证据;clean 输入不受影响)。
    for _field, _raw in (
            ("current.smiles", current.get("smiles")),
            ("result.product_mapped_smiles",
             result.get("product_mapped_smiles")),
            ("result.product_smiles", result.get("product_smiles")),
            ("expectation.target_smiles",
             expectation.get("target_smiles"))):
        if _raw is None or str(_raw) == "":
            continue
        try:
            _guard_input_cx_classes(str(_raw))
        except ChemicalStateError as exc:
            raise AuditContractError(
                f"供体诊断原始输入字段 {_field} 含未登记 CX 项:"
                f"{exc}(与工厂/strict 同源的输入侧注册感知校验:解析器"
                "会静默丢弃该项,丢弃后不得以剥标记身份参与 verified"
                "证据;拒绝该诊断输入,不改冻结执行器)",
                {"kind": "raw_input_cx_class_unregistered",
                 "field": _field,
                 **{k: v for k, v in (exc.detail or {}).items()
                    if k != "kind"}}) from exc

    # ---- 执行图事实 ----
    current_smiles = current.get("smiles", "")
    mol_before = Chem.MolFromSmiles(str(current_smiles)) \
        if current_smiles else None
    product_mapped = result.get("product_mapped_smiles", "")
    mol_after = Chem.MolFromSmiles(str(product_mapped)) \
        if product_mapped else None
    id_to_idx_after = {
        str(k): int(v) for k, v in (result.get("atom_id_map") or {}).items()}
    if mol_before is None or mol_after is None:
        return DonorConsistencyDiagnostic(
            strict_target_match=None, legacy_cn_match=None,
            reaction_center_match=None, alignment_ref=alignment_ref,
            missing_info_reasons=["before_or_after_structure_unparseable"],
            executed_bond_changes=[])
    id_to_idx_before = {
        str(k): int(v) for k, v in (current.get("atom_id_map") or {}).items()}

    # ---- plain 产物 vs mapped 执行图对账(R2-03) ----
    representation_disagreement = False
    result_smiles = result.get("product_smiles")
    plain_mol = Chem.MolFromSmiles(str(result_smiles)) \
        if result_smiles else None
    if result_smiles and product_mapped:
        from .chemstate import normalized_structure_smiles

        if plain_mol is None:
            representation_disagreement = True
            missing.append("plain_product_unparseable")
        elif normalized_structure_smiles(plain_mol) != \
                normalized_structure_smiles(mol_after):
            representation_disagreement = True
            missing.append(
                "plain_product_mapped_product_disagreement(执行图与"
                "对外产物不一致,两轴不可判)")

    # ---- 实际净变化集合 ----
    # 结构身份一致 ⇒ 零净变化(所有表示差异都被规范化吸收)
    from .chemstate import normalized_structure_smiles as _norm_smiles

    net_change_empty = (_norm_smiles(mol_before)
                        == _norm_smiles(mol_after))
    if net_change_empty:
        missing.append(
            "no_executed_change(实际净变化为空:声明触及≠已发生;"
            "center 不可判 True)")
    if net_change_empty:
        bond_changes: list[dict] = []
        atom_changed: set[str] = set()
        atom_records: dict[str, dict] = {}
    else:
        bond_changes = _bond_changes(mol_before, mol_after,
                                     id_to_idx_after)
        atom_changed, atom_records = _atom_property_diffs(
            mol_before, mol_after, id_to_idx_before, id_to_idx_after)
    added_atom_ids = [aid for aid in id_to_idx_after
                      if aid not in id_to_idx_before]
    changed_atoms = ({c["atom1_id"] for c in bond_changes}
                     | {c["atom2_id"] for c in bond_changes}
                     | atom_changed)
    declaration_only = sorted(_edit_atom_ids(edits) - changed_atoms)

    # ---- 声明–执行净效应对账(R3-05:模拟声明序列到终态,比较净效应) ----
    declaration_mismatches, _declared_changes = _declaration_accounting(
        mol_before, edits, id_to_idx_before, id_to_idx_after,
        bond_changes, added_atom_ids)

    # ---- strict(与 ChemicalState 同源规范化严格表示;含对账前提) ----
    strict = None
    cn_match = None
    expected_smiles = expectation.get("target_smiles")
    if representation_disagreement:
        strict = None
    elif declaration_mismatches:
        # 声明与执行不一致 ⇒ strict 至少 unknown(mimo 5.2(a):该轴
        # 不得 verified —— 产物碰巧等于预期不能掩盖对账失败)
        strict = None
    elif result_smiles and expected_smiles:
        # (strict_identity_of/ChemicalStateError 已在模块顶导入;此处
        # 不再局部重导入 —— 局部 import 会把名字变成本函数局部变量,
        # 使上方 R6-02 守卫的 except 提前引用未绑定名)
        try:
            strict = (strict_identity_of(str(result_smiles))
                      == strict_identity_of(str(expected_smiles)))
        except ChemicalStateError:
            strict = None
            missing.append("target_or_result_unparseable")
        from ..domain.identity import cn_identity as _cn

        cn_a = _cn(str(result_smiles))
        cn_b = _cn(str(expected_smiles))
        if cn_a is not None and cn_b is not None:
            cn_match = cn_a == cn_b
    elif not representation_disagreement:
        missing.append("target_or_result_smiles_missing")

    # ---- reaction center(实际净变化 + 对齐映射 + 联合对称) ----
    center_match = None
    basis = ""
    extra_changes: list[dict] = []
    joint_mapping: dict = {}
    equivalence_basis = ""
    center_direct_ids: set[str] = set()
    donor_centers = [str(a) for a in (donor.get("center_atom_ids") or [])]

    if declaration_mismatches:
        # 声明与执行不一致 ⇒ 中心不可判(至少 unknown,mimo 5.2(a))
        center_match = None
        missing.extend(declaration_mismatches[:10])
    elif representation_disagreement:
        center_match = None  # 执行图不可信(与对外产物不一致)
    elif alignment_status != "resolved":
        center_match = None
        missing.append(f"alignment_{alignment_status}_center_unknown")
    elif not donor_centers:
        center_match = None
        missing.append("center_or_edits_unavailable")
    elif not changed_atoms:
        # 零图轴变化:身份相同(上方 net_change_empty 已记 no_executed_
        # change)或**身份不同而图轴空** —— v9(S4 回修 r3)起同位素轴
        # 已入图变化集(_atom_property_diffs 比较 GetIsotope),残余的
        # "身份不同而图轴空"只能是图变化集未承载的立体表示差异(非
        # 四面体等 unsupported 立体轴,R4-07):不得称"实际净变化为空"
        # (理由码断言一件身份轴已证伪的事);纯同位素差异不再落入本
        # 分支(v8 前曾以本码误标"仅立体",PPV1-ISO-01),走真实轴
        # (isotope delta + 中心范围判定)
        center_match = None
        if not net_change_empty:
            missing.append(
                "net_change_only_in_stereo_representation(身份键不同而"
                "图轴无差异:残余差异属未比较/未承载的立体表示轴(非"
                "四面体等,见 stereo_comparison_unsupported_atoms;同位素"
                "轴已入图变化集,不在此列);center "
                "不可判,不得称实际净变化为空)")
        else:
            missing.append(
                "no_executed_change(实际净变化为空:声明触及≠已发生;"
                "center 不可判 True)")
    else:
        mapping = {
            str(k): str(v)
            for k, v in (alignment.get("donor_to_current") or {}).items()}
        # 等价类验证(仅披露;v3 不再参与判定,由联合映射取代)
        _, rejected_classes = _validate_equivalence_classes(
            alignment.get("equivalence_classes") or [],
            mol_before, id_to_idx_before)
        equivalence_basis = "canonical_rank_breakTies_false"
        if rejected_classes:
            missing.append(
                "equivalence_class_rejected_by_graph_automorphism:"
                + ";".join(",".join(c) for c in rejected_classes)[:160]
                + "(非等价成员的类不被采信;等价类不参与 v3 center 判定)")
        # 全部供体中心原子必须有映射(部分缺映射 ⇒ unknown)
        unmapped = [d for d in donor_centers if d not in mapping]
        if unmapped:
            center_match = None
            missing.append(
                "donor_centers_partially_unmapped:" + ",".join(unmapped))
        else:
            center_direct = {mapping[d] for d in donor_centers}
            center_direct_ids = set(center_direct)
            outside = changed_atoms - center_direct
            if not outside:
                center_match = True
                basis = "direct"
                extra_changes = []
            else:
                # 联合对称:单一自同构把整个中心集合映到实际变化集合
                center_idxs = {id_to_idx_before[a] for a in center_direct
                               if a in id_to_idx_before}
                changed_idxs = {id_to_idx_before[a] for a in changed_atoms
                                if a in id_to_idx_before}
                if len(changed_idxs) != len(changed_atoms):
                    # 变化集含新增原子等无 before 索引的原子:
                    # 联合映射不可能 ⇒ 偏离(新增原子须在中心声明内)
                    center_match = False
                    basis = ""
                    extra_changes = _atom_change_summary(
                        outside, mol_before, mol_after, id_to_idx_after,
                        atom_records)
                else:
                    joint = _joint_symmetric_image(
                        mol_before, center_idxs, changed_idxs)
                    if joint == "truncated":
                        center_match = None
                        basis = ""
                        missing.append(
                            "automorphism_search_truncated(联合映射搜索"
                            "截断,中心不可判)")
                    elif joint == "unsupported_stereo":
                        center_match = None
                        basis = ""
                        missing.append(
                            "joint_mapping_stereo_unsupported"
                            "(底物带增强立体组或非四面体手性标签:联合"
                            "映射的手性感知范围未覆盖 —— useChirality 只"
                            "覆盖四面体标签,增强组/非四面体中心被其忽略"
                            "会将可区分位点判等价;中心不可判,不冒称"
                            "全范围解决,R4-07)")
                    elif isinstance(joint, dict):
                        center_match = True
                        basis = "symmetric_equivalent"
                        joint_mapping = dict(joint)
                        joint_mapping["equivalence_note"] = (
                            "图等价≠酶识别/机制等价(保手性图自同构的"
                            "拓扑证据)")
                        extra_changes = []
                    else:
                        center_match = False  # 联合映射不存在 ⇒ 偏离
                        basis = ""
                        extra_changes = _atom_change_summary(
                            outside, mol_before, mol_after, id_to_idx_after,
                            atom_records)

    # ---- R4-07:中心外存在立体轴 unsupported 的原子 ⇒ 区域约束不可核
    # (该原子的立体可能已变但比较范围外 ⇒ "变化局限于中心"不可证;
    # 中心内的 unsupported 不阻断 —— 中心内立体变化本就允许) ----
    stereo_unsupported_atoms = sorted(
        aid for aid, rec in atom_records.items()
        if rec.get("stereo_comparison_unsupported"))
    stereo_unsupported_outside = [
        aid for aid in stereo_unsupported_atoms
        if aid not in center_direct_ids]
    if center_match is True and stereo_unsupported_outside:
        center_match = None
        basis = ""
        missing.append(
            "stereo_comparison_unsupported_outside_center:"
            + ",".join(stereo_unsupported_outside[:10])
            + "(中心外原子的立体轴在比较支持范围外(非四面体/配体集合"
            "改变后不可比):区域约束对该轴不可核 ⇒ center 不可判 True;"
            "unsupported 原子清单公开于 stereo_comparison_unsupported_"
            "atoms)")

    # ---- 中心原子属性披露(R3-01/05:ops 对账不覆盖属性,E-iii;
    # R4-07:unsupported 立体轴同通道公开,不静默缺席;
    # v9/S4 回修 r3:isotope 轴同通道公开(records["isotope"],
    # 中心内同位素变化随 property_delta 的 "isotope" 机读码披露) ----
    center_property_deltas: list[dict] = []
    for aid in sorted(center_direct_ids):
        rec = atom_records.get(aid)
        if rec and (rec.get("property_delta") or "presence" in rec
                    or rec.get("stereo_comparison_unsupported")):
            entry = {"atom_id": aid}
            entry.update(rec)
            center_property_deltas.append(entry)

    # ---- 证据载荷(R3-01 + R4-01:绑定本诊断全部输入 + 各轴结论 +
    # scope + **完整证明记录** proof_record 供 audit 内部重算) ----
    normalized_edits = sorted(
        {f"{str(e.get('op', ''))}|{str(e.get('atom1', ''))}|"
         f"{str(e.get('atom2', ''))}|{str(e.get('from_order', ''))}|"
         f"{str(e.get('to_order', ''))}|{str(e.get('new_atom_id', ''))}|"
         f"{str(e.get('element', ''))}"
         for e in (edits or [])})
    evidence_payload = {
        "checker_version": PPV1_DONOR_DIAGNOSTIC_VERSION,
        "checker_scope": "region_net_change",
        "center_match": center_match,
        "center_match_basis": basis,
        "declaration_mismatch": bool(declaration_mismatches),
        "strict_target_match": strict,
        # P2(R5 §4-1):proof 的命题与范围如实披露 —— 本载荷证明的是
        # 自包含输入集(current/donor/alignment/expectation/result/
        # edits)的确定性重算自洽,可由任何人复算复现;**不**证明"编辑
        # 曾被执行"的运行事实(运行事实由执行器通道的 result/指纹绑定)
        "proof_scope": "self_contained_recompute",
        "evidence_refs": [alignment_ref],
        "bound_inputs": {
            "substrate_identity": _norm_smiles(mol_before),
            "product_identity": ("" if representation_disagreement
                                 else (_norm_smiles(plain_mol)
                                       if plain_mol is not None else "")),
            "edits_signature": content_hash(normalized_edits),
            "donor_centers": sorted(donor_centers),
            "alignment_ref": alignment_ref,
            "execution_fingerprint": content_hash({
                "product_mapped_smiles": str(product_mapped),
                "atom_id_map": {str(k): int(v) for k, v in
                                id_to_idx_after.items()},
            }),
        },
        # R4-01:证明记录 = 本诊断的完整输入集(check_edit_against_
        # donor 的入参原样);audit 证据门复跑本确定性 checker 复核
        # 自报字段与绑定 —— 两条身份字符串/六条自报字段不构成证明
        "proof_record": {
            "current": {"smiles": str(current_smiles),
                        "atom_id_map": dict(id_to_idx_before)},
            "donor": {"center_atom_ids": list(donor_centers)},
            "alignment": {"status": alignment_status,
                          "donor_to_current": {
                              str(k): str(v) for k, v in
                              (alignment.get("donor_to_current")
                               or {}).items()},
                          "equivalence_classes": [
                              list(c) for c in
                              (alignment.get("equivalence_classes")
                               or [])],
                          "ref": alignment_ref},
            "expectation": {"target_smiles":
                            ("" if expected_smiles is None
                             else str(expected_smiles))},
            "result": dict(result),
            "edits": [dict(e) for e in (edits or [])],
        },
    }

    return DonorConsistencyDiagnostic(
        strict_target_match=strict, legacy_cn_match=cn_match,
        reaction_center_match=center_match, center_match_basis=basis,
        extra_changes=extra_changes, alignment_ref=alignment_ref,
        missing_info_reasons=missing,
        executed_bond_changes=bond_changes,
        declaration_only=declaration_only,
        declaration_mismatches=declaration_mismatches,
        equivalence_basis=(equivalence_basis
                           if alignment.get("equivalence_classes")
                           else ""),
        joint_mapping=joint_mapping,
        net_change_empty=net_change_empty,
        center_property_deltas=center_property_deltas,
        stereo_comparison_unsupported_atoms=stereo_unsupported_atoms,
        center_evidence=evidence_payload)


def _atom_change_summary(atoms: set[str], before: Chem.Mol,
                         after: Chem.Mol, id_to_idx_after: dict,
                         atom_records: dict[str, dict] | None = None,
                         ) -> list[dict]:
    """中心区域外变化原子的逐原子 Δ 摘要(element/电荷/ΔH/Δ同位素/Δ立体)。

    v3(mimo 5.2(a)):补 ΔH 与 Δ立体;电荷输出 before/after 而非
    仅产物值;atom_records 提供 _atom_property_diffs 的逐 id 记录。
    v9(S4 回修 r3,PPV1-ISO-01):补 Δ同位素披露(records["isotope"]
    的 before/after;"isotope" 机读码已在 delta 列表)。
    """
    out: list[dict] = []
    records = atom_records or {}
    for aid in sorted(atoms):
        rec = dict(records.get(aid) or {})
        entry = {"atom_id": aid, "delta": []}
        idx = id_to_idx_after.get(aid)
        if "presence" in rec:
            entry["delta"].append(rec["presence"])
            entry["element"] = rec.get("element", "")
            if "formal_charge" in rec:
                entry["formal_charge"] = rec["formal_charge"]
            if "h_count" in rec:
                entry["h_count"] = rec["h_count"]
            if "isotope" in rec:
                entry["isotope"] = rec["isotope"]
            if "cip" in rec:
                entry["stereo"] = rec["cip"]
            out.append(entry)
            continue
        if idx is not None:
            after_atom = None
            for atom in after.GetAtoms():
                if atom.GetAtomMapNum() - 1 == idx:
                    after_atom = atom
                    break
        else:
            after_atom = None
        entry["element"] = rec.get("element", "")
        if "formal_charge" in rec:
            entry["formal_charge"] = {
                "before": rec["formal_charge"][0],
                "after": rec["formal_charge"][1]}
        if "h_count" in rec:
            entry["h_count"] = {
                "before": rec["h_count"][0],
                "after": rec["h_count"][1]}
        if "isotope" in rec:
            # 同位素轴 before/after(核素变化;与 element 不变并存合法)
            entry["isotope"] = {
                "before": rec["isotope"][0],
                "after": rec["isotope"][1]}
        if "cip_labels" in rec:
            # 准确 CIP 标签(rdCIPLabeler)——仅披露;标签 diff ≠ 构型
            # 变化(构型判定用奇偶法,见 property_delta 中的 stereo 项)
            entry["stereo"] = {
                "before_cip": rec["cip_labels"][0] or None,
                "after_cip": rec["cip_labels"][1] or None}
        if rec.get("property_delta"):
            entry["delta"].extend(
                d for d in str(rec["property_delta"]).split(";") if d)
        if after_atom is not None:
            entry["delta"].append("present_in_product")
        else:
            entry["delta"].append("absent_in_product_or_unmapped")
        out.append(entry)
    return out


def center_evidence_from_donor_diagnostic(
        diagnostic: DonorConsistencyDiagnostic) -> dict:
    """供体诊断 → audit 的 center_evidence(R3-01 证据门接线助手)。

    v4:直接透传诊断内嵌的**绑定证据载荷**(v3 只回
    checker_version+center_match,丢失 strict 轴/绑定输入/检查范围,
    造成跨反应复用与无依据 True 可达 R6 —— 复审 R3-01)。绑定核验
    (底物/产物身份 vs 被审假设参与物)由 audit_hypothesis 执行;
    strict_target_match=False ⇒ 该证据不得构成 verified(至少
    unknown,mimo 3.3(3))。
    """
    if diagnostic.center_evidence:
        return dict(diagnostic.center_evidence)
    # 兼容路径:旧形状(无绑定)——audit 侧将按 binding 缺失记
    # unknown,不授予 verified(诚实降级)
    return {
        "checker_version": PPV1_DONOR_DIAGNOSTIC_VERSION,
        "center_match": diagnostic.reaction_center_match,
        "declaration_mismatch": bool(diagnostic.declaration_mismatches),
        "center_match_basis": diagnostic.center_match_basis,
        "evidence_refs": [diagnostic.alignment_ref],
    }
