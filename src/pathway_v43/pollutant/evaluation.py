"""S5a 科学评测器接口(ppv1-evaluation-5;S5 任务书 §8/§9/§11/§12)。

S5a 边界(任务书 §15):本评测器是**接口与规则级程序行为交付** ——
消费 S4 公开入口(``read_native_export``;§3.1)、确定性零 LLM 判分、
输出结构化指标分轴;**不输出任何 dev/298 科学性能结论**:

- **零 LLM**(§4.3/S5-25):判分路径无任何模型调用;只消费冻结的
  结构化字段清单(见 ``_CONSUMED_EXPORT_FIELDS``/``_CONSUMED_INPUT_
  FIELDS``),自然语言字段不进任何判定 —— 输入里的自由文本/narrative
  不能改变程序结果;
- **收费 provider 默认关**(§13.5/S5-26):``model_provider_policy``
  默认 ``none``;``real`` 无用户逐次授权 ⇒ 结构化拒绝(本模块无任何
  网络代码,网络请求与费用为零;正式科学评测不启动);
- **确定性**(S5-24):输出无时间戳、canonical_json 键序 + 列表稳定
  排序;``output_sha256`` = 输出去掉自身后的内容哈希;同输入 ⇒
  字节级一致;
- **状态语义**(§12/S5-23):评测器只允许发 ``pending_*``/``interface_
  verified_only``/``blocked_*`` 族;``evaluated_*`` 永不由程序生成
  (§11 第 19 步:最终科学状态由用户/teacher 按预注册裁定);
- **防泄漏**(§6.3/S5-07/S5-08):split manifest + 同 source group 跨
  集合 + known/unseen 直接证据重叠检查;失败 ⇒ ``blocked_leakage``,
  不聚合;
- **金标写入守卫**(S5-27):含金标产物只能进授权 gitignored 根
  (``persist_evaluation_output``);普通目录拒绝;**S5A-04:核验与
  写入使用同一个解析后实际规范路径**(relative target 基准 = 相对
  cwd,出界/symlink 逃根先拒,零新文件;未声明根 ⇒ 含金标一律
  拒;禁止出界后回退原字符串授权);
- **S4 导出缺席**(S5-28):无导出 ⇒ 状态 ``pending_no_independent_
  data``,不运行正式科学评测。

匹配规则(严格结构身份 vs CN 旁证、step_scope 分轴、条件
conflict/unknown/compatible、endpoint/矿化声明检查、预算漏展开、
深度分桶)全部为 **proposed 规则级实现**(预注册模板中逐项标注
proposed;最终冻结属用户/teacher,§10.1)。阈值/样本量/分母/置信
区间全部 TBD(输出里逐项携带 ``TBD_USER_TEACHER_DECISION``)。

S5a 回修 r1(S5A-01/02/03/04;复审 §4 四组 P1,契约升
ppv1-evaluation-2):

- **S5A-01 参考身份 scope 先消费许可再授严格档**:参考节点声明
  ``structure_identity_scope ∈ {cn_only, partial, unknown}`` ⇒ 内容
  严格相等也封顶为 CN 旁证(机读 ``identity_scope_cap``),不授
  ``strict_structure``、不进 ``strict_by_node``/边严格候选/严格指标
  (节点→边→聚合逐层;合法 strict 与真实 CN 旁证控制保持);
- **S5A-02 条件分类沿冻结同源规则**:登记 ConditionScope → 冻结
  Requirement/事实映射(映射限定机读披露),消费 path_context 同一
  实现的事实侧单位三态/实体-数值-异值 absence/同键相反事实保守
  unknown/necessity 来源/适用场景阶段/声明 value_basis;缺表示
  能力 ⇒ unknown/unsupported 族机读披露;要求侧 ``status=known_
  absent`` 单列 ``requirement_status_not_representable``(不伪称
  冻结矛盾);
- **S5A-03 声明必要 from/to 节点空命中不被 union 吞**:每个必要
  节点须有许可严格命中才可完整 strict;空集合保持
  ``unmatched_required_node_uncovered`` + 逐节点
  ``required_node_gaps`` 机读披露;参与物覆盖消费完整声明集合;
- **S5A-04 persist 核验与写入同一实际规范路径**(见上)。

S5a 回修 r2(S5A-02 单位收口;复审 R2 §4 唯一残余 P1,契约升
ppv1-evaluation-3):

- **S5A-02 r2 要求侧单位首消费收口**:共同 ConditionScope → 冻结
  Requirement 映射处决定单位支持能力 —— 显式非规范单位(温度
  K/F)或无量纲键声明单位(物种键 mg/L)无合法冻结表示 ⇒ 分类
  ``condition_unknown`` + reason ``requirement_unit_not_
  representable``,机读披露保留原 key/unit/value/allowed_units/
  原因(不丢弃单位后授 compatible/conflict、不做换算、不猜测
  单位语义);空要求单位按键规范单位约定(canonical-by-key
  默认,合法不降档,披露 ``requirement_unit_not_declared``/
  reason ``requirement_unit_canonical_by_key``);显式规范单位
  (°C/C/celsius)合法;事实侧来源单位三态(canonical/source_
  unit_unknown/unit_mismatch)仍由冻结同源 ``_assess_requirement``
  裁决 —— 要求侧 canonical-by-key 默认与事实侧来源单位三态
  分立(事实侧 temperature 缺单位仍 unknown);公共单条分类、
  sample 分类与聚合同源消费(桶自动传导);
- **B2 文案纠错(与实现同真;S5a r3 复审 R3 §5 限定物种键并删
  合法链"顺序相关"尾巴)**:合法公共链的 unknown 事实经
  checked ``build_condition_fact`` 值清 None(不带身份)⇒ 同键
  **相反** present×absent 事实两序均 unknown;known×unknown 混合
  **仅物种键**(electron_acceptor/electron_donor/growth_
  substrate 等实体键)按冻结侧实体已知事实裁决(present ⇒
  compatible、absent ⇒ essential_conflict),**非物种键(数值/
  枚举/标签)任一适用 unknown 事实 ⇒ condition_unknown**;合法
  checked 链两序结果一致(实测 20 对照),无合法链顺序差异;
  直接 dataclass 绕过 checked 构造器或 restore 低层直构的次序
  语义是已登记支持边界 P2,不属本契约,不以文字宣称首消费绑定
  已通过(改冻结侧物种语义归用户/teacher 裁定)。

S5a 回修 r3 文字同步(复审 R3 §5 五处 P2 之一/之二,拟冻结前
修正,非语义变更,版本保持 ppv1-evaluation-3):

- 单位失败的具体枚举是 ``condition_unknown``(带机读 reason),
  不用 unknown/unsupported 族名冒充具体桶;
- 空要求 unit 的 canonical-by-key 约定有如实代价:作者实际想写
  298 K 而省略 unit 时,程序只能按 temperature_C 声明读 298 °C
  ——不猜作者意图,不把空单位全面降 unknown;
- 单位/事实披露的 value 是 ``repr(raw_value)`` 展示串,不是
  JSON 原生 value_raw 字段(value_raw 尚未实现;禁止 eval 展示
  串);
- 物种键实体事实只证实体**存在**,不证浓度/阈值达标;
- environment_conflict_rate 当前只分桶、无标量分母;未知桶独立
  披露,unknown ≠ 无冲突;正式分母属 TBD_USER_TEACHER_DECISION,
  不从桶数自行承诺冲突率。不作"所有声明越具体只能降档"或
  "分母已定包含 unknown"的宽泛承诺(仅固定其他输入、空 unit →
  显式不支持 unit 一组行为可证)。

S5b 启动批(evaluation-4,2026-10-09,mimo r25 ⚠️P1-9 G1 配对错位
修复;**仅样本↔导出配对语义变更**,匹配/条件/指标/守卫判定零触碰):

- **qid 感知样本↔导出配对**(G1 一题一图 + 53 重复底物下同根
  多题不得张冠李戴):图侧 qid = ``reference_graph_manifest`` 条目
  声明的 ``qid``(一致性核:必须出现在该图 ``root_entity.source_
  refs``——转换规则 §2.2;不一致 ⇒ 结构化拒);导出侧 qid =
  ``native_path_exports`` 条目声明的 ``qid``(其 ``run_id`` 与
  read_native_export 返回 payload 的 ``run_id`` 权威绑定核验,
  不一致 ⇒ 结构化拒);评测输入任一侧声明 qid ⇒ 全局进入严格
  qid 档——图只配同 qid 的可读导出;qid 无匹配导出 ⇒ 该样本
  ``not_evaluated`` 且 reason 明示 qid 未配到(**不再按根身份
  首中即 break 张冠李戴**);严格档下未声明 qid 的图同样不回退
  根身份(回退即重新引入错位),单独 reason 披露;
- qid 信息完全不可得(合成测试图不声明 qid 且导出不声明 qid)⇒
  回退既有根严格身份配对,机读披露 ``pairing_basis=
  root_identity_fallback``(不静默;S5b 真实图全带 qid 走严格
  路径);
- 同一 qid 多导出 ⇒ 配对清单按评测输入 ``native_path_exports``
  清单序(显式清单序),消费 digest = 首位并以
  ``consumed_export_digest`` 机读披露(确定性,不随机);
- 每个导出至多配到一个样本(两档同此约束);配不到的导出仍进
  ``coverage_report.unmatched_exports`` 披露;
- 新增消费的权威输入子字段仅两个:manifest 条目 ``qid`` 与导出
  条目 ``qid``(S5-25 结构化字段清单的条目级子字段扩展,仍非
  自然语言进判定;其余输入字段消费范围不变)。

S5b 启动批回修(S5B-L01,evaluation-5,2026-10-09,复审
POLLUTANT_PATHWAY_S5B_CODEX_REVIEW §4.1;**仅 real 档配对守卫
新增**,匹配/条件/指标/守卫判定零触碰):

- **real 首消费禁双无 qid / root_identity_fallback**:``
  evaluate_scientific`` 在配对计算后、样本评分/聚合/结果写入前,
  对 ``data_scope=real`` 且配对档为 ``root_identity_fallback``
  (评测输入两侧全部未声明 qid)抛结构化 ``EvaluationContractError``
  (``kind=real_data_root_identity_fallback_forbidden``,机读携带
  data_scope 与缺 qid 的图/导出条目范围)——真实样本身份边界
  fail-closed,不静默退成错误样本评分(复审公开合成反例:real
  标签+fake approved 形状+两侧全无 qid ⇒ 修前一图 scored 进聚合、
  另一图 not_evaluated;修后整评结构化拒,零样本评分/聚合);
- 合法控制全部保持:``synthetic_rule_level`` 双无 qid 回退(合成
  夹具正控,披露不变)、real 严格 qid 档正控、qid 缺配
  ``not_evaluated`` 与四个既有输入守卫、real+未批准预注册拒;
- 该门不是 criteria-v2 化学门:qid 不进化学结构判据(冻结判据
  正文/FREEZE_RECORD/path_context 逐字节不改);预注册发车侧
  同步落 ``bases_by_graph`` 全 ``qid_strict`` 核对(见预注册 §9)。

W-V6.2(v3 交付,mimo r27 判断面一附条件;配对唯一消费入口登记):

- ``_pair_exports_to_samples`` 的**全仓唯一活动消费入口 =
  ``evaluate_scientific``**(配对结果的 real 守卫/样本配对/覆盖
  披露都在该入口的首消费路径上;AGENTS 返工教训 #1 同规则列全
  消费入口)。入口矩阵登记:本入口消费 图清单(qid 声明+一致性)、
  导出条目(qid 声明+run↔qid 绑定)、导出 payload(根严格身份,
  仅回退档)—— 身份/版本/拒因与 ``PAIRING_BASIS_*`` 常量同源;
  任何新消费方(判分聚合/导出审计)必须经 ``evaluate_scientific``
  的产物(``coverage_report.pairing``/样本 ``pairing`` 字段)消费,
  不得另起直调。锁调用点回归:tests 断言全仓源码中该函数的
  活动调用恰一处(evaluate_scientific 内;def/注释/文档行除外),
  防未来绕过(新增第二调用点 ⇒ 测试红,须显式扩本登记)。

本模块不读取真实科学数据/金标/题面/封存 run;不写数据库;合成
规则级测试之外的数字一律 interface/pending。

S5b HIT50 v3 回修(S5B-V3-01,2026-10-10,正链复审
POLLUTANT_PATHWAY_S5B_HIT50_V3_CODEX_REVIEW §4.1;**仅 data_scope
首消费校验收紧**,real 门/配对/匹配/指标判定零触碰):

- **data_scope 严格校验(评测首消费)**:``resolve_data_scope`` 为
  评测(``validate_evaluation_input``/``evaluate_scientific``)与判分
  (``s5b_scoring.score_s5b_batch``,包装为 S5bScoringError)**共用
  同一判据**——显式空串/None/bool/数值/未知字符串(含 "Real" 等
  大小写/空白变体)⇒ 结构化拒(kind=data_scope_invalid),**不再用
  ``get(...) or synthetic_rule_level`` 的 truthiness 把显式坏值洗成
  synthetic**(旧路径显式空/None/False/0 被洗白后绕过 real 批准/
  配对门);**字段完全缺省的既有缺省语义保留**(评测侧缺省 =
  synthetic_rule_level;判分侧缺省经签名默认 = real),归一来源
  ``normalized_from`` 机读进 scoring_provenance;CLI choices 不代
  API 校验(本函数是公开 API 唯一权威判据);
- 适用入口矩阵:①``validate_evaluation_input``(校验首消费);
  ②``evaluate_scientific``(同源二次解析 + 输出披露);③
  ``score_s5b_batch``(判分首消费,同判据异常包装 s5b_data_scope_
  invalid);合法正控保持:显式 real(配 prereg 批准门)、显式
  synthetic、完全缺省(合成夹具默认语义)。

ppv1-criteria-v2(T-1 判分面参与物集合比较豁免,2026-10-13;预注册
docs/POLLUTANT_PATHWAY_CRITERIA_V2_PREREGISTRATION_2026-10-13.md,
状态 preregistration_pending_final_confirmation;上游 = teacher T-1
裁定 b 档 + mimo r36 九条件 + CS2c 补证 N1''=13 + 冻结拍板包):

- **作用轴唯一**:`match_reference_edges` 的逐侧参与物集合比较
  (reactants==from_states ∧ products==to_states);生成侧零改动;
- **豁免缺省关**:`criteria_version` keyword-only 参数缺省
  ``ppv1-criteria-v1`` ⇒ 豁免代码零执行、输出零新键(既有判分行为
  字节不变);显式传 ``ppv1-criteria-v2`` 才启用(新批次经预注册);
- **方向限定清单**:产物侧 H₂O/H⁺/Pi/PPi 四类全收,反应物侧仅
  H₂O/H⁺(磷酰化机制判别子保护;r28 A2 原裁维持非推翻);判定键 =
  cn 身份哈希集(sha256 前 16 位版本化);
- **三谓词 fail-closed**:①记录已声明(payload 内
  event→hypothesis→provenance_refs→provenance_records.record_equation
  声明链;判不了=unknown=不豁免)②元素可追溯(P/O 计数账照抄补证
  脚本口径,"无中生水"拦截)③cn 身份成员;任一不过/unknown ⇒ 该
  extras 维持比较;
- **完备二分+单归属**:每条 extras(身份+侧+角色)恰一个 tier
  (``v1_exempt`` / ``not_exempt_maintains_partial``);T1′ 档未实施
  ⇒ 未声明多余产物维持 partial(明字常量,不理解为"应实施 T1′");
- **机器挡板**:豁免变体零碳断言(含碳身份禁入豁免构造;CO₂/HCO₃⁻
  为登记的 v2 known gap)+ 辅因子硬拒绝表(正面清单语义,NAD(P)/
  ATP/CoA/FAD/THF/O₂/NH₃/T1′ 恒不忽略族绝不豁免)+ 豁免身份 ∩
  COMPLETION_LICENSED_IDENTITIES = ∅;
- **披露**:豁免发生时逐边机读 ``exempted_participants``;v2 批级
  ``criteria_v2`` 汇总块含参考侧 v1 身份监控(应为 0,非 0 = 退出
  条件信号)。v1 headline 口径不变直到新批次生效。

ppv1-criteria-v3(T-D-A/B 判分侧披露轴,2026-10-19;生效口径
``docs/POLLUTANT_PATHWAY_CRITERIA_FROZEN_V3_2026-10-19.md``):

- **档 A 只披露**:A 轴(互变异构归一;双臂:默认臂〔互变中心立体
  容忍,手性负控已实测 FAIL 的敏感性披露臂,不具 strict 准入〕与
  候选主臂〔sp3 立体保留;档 B 未来唯一候选,本轮未解锁〕)+ B 轴
  (质子化归一;默认单启用 Uncharger 臂,ChargeParent 臂仅并列
  敏感性披露)在参考节点 ``structure_identity_scope==
  "strict_structure"`` 的 cn_only 配对上**只产出披露**
  (``criteria_v3_normalized_identity``,节点级)与批级
  ``criteria_v3`` 汇总块;**不授 strict、不进 hit@1**;
  ``tautomer_promoted_nodes`` 恒空(档 B 未解锁,D03);
- **互变归一禁改判分**:``match_status``/严格档/S5A-01 许可门
  零改动;封顶节点如实给 ``applicable=false``(机读原因);
- **正交承载**:v3 承载 v2 参与物比较豁免判分路径(逐位不变;
  N3/N7);豁免缺省关仍旧(v1 零新键、字节不变);
- **fail-closed 无第三态**:任一侧不可解析/算子异常 ⇒ 不授归一
  相等 + 逐臂机读原因;单归属 A→B(``single_attribution``);
  B-6 碳酸体系闭集逐对象排除(``carbonate_system_exclusion``);
- **参数指纹**(§3 条 3/§8):分臂实际生效参数(含实测默认值)+
  双臂差异 diff + transforms 文件哈希(本构建以原子库 sha256 替代
  登记并披露)+ RDKit 版本串 → sha256;v3 请求而引擎/指纹不可得
  ⇒ 结构化拒(``criteria_v3_engine_unavailable``,不降级)。

ppv1-criteria-v4(matched_product_hit 主口径,2026-10-28;预注册草案
``docs/CRITERIA_V4_MATCHED_PRODUCT_HIT_PREREG_DRAFT_2026-10-28.md``
§1–§4;CC 2026-10-28 拍板机器名 ``matched_product_hit``、禁止叫 strict):

- **只加分支**:v1/v2/v3 的版本解析、节点/边匹配、coverage 三分、
  豁免与披露路径逐字节不改;criteria_version 缺省 v1 ⇒ v4 代码零
  执行、输出零新键;
- **判定公式(§1)**:hit ⇔ 存在**同一个**合法事件 E,底物严格身份
  S ∈ 反应物侧身份集合 R_E **且** 参考边声明的主产物身份集合
  P ⊆ 产物侧身份集合 T_E;身份函数 = ``strict_identity_of``(与 v2
  节点匹配同一函数、一字不改);P 只取该参考边产物侧
  ``principal_product`` 角色节点(不取其它 from/to 节点);
- **禁止跨事件拼答案**:底物与全部主产物必须同一事件全中;多主产物
  题不得由多个事件凑齐;
- **保留原 coverage 事实**:v4 不改写 exact/superset/partial_subset,
  ``matched_product_hit`` 与旧 ``match_status`` 分列(禁止把 superset
  写成 exact,禁止把本指标称为 strict);
- **v2 豁免旁路(§4)**:v4 不启用 v2 豁免逻辑;批级披露豁免计数 0
  (``exemption_bypassed``),不与 v2 读数混算;
- **与 v3 正交(§4)**:v3 是披露轴、v4 是主口径;同时启用(v4 +
  ``disclosure_criteria_versions=(ppv1-criteria-v3,)``)时两者各自
  输出、互不改写;
- **桶(§3)**:matched_product_hit / product_hit_partial /
  unmatched_no_event / unmatched_reference_invalid /
  unmatched_product_mismatch;分母固定(失败/无效题不剔除)。
"""

from __future__ import annotations

import hashlib
from fractions import Fraction
from functools import lru_cache
from pathlib import Path

from ..domain.models import canonical_json, content_hash
from .native_export import read_native_export
from .profile import (
    PPV1_EVALUATION_VERSION,
    PPV1_NATIVE_EXPORT_VERSION,
    PPV1_SPLIT_MANIFEST_VERSION,
)
from .reference_graph import (
    DOMAINS,
    ENDPOINT_ASSESSMENTS,
    SPLITS,
    TRACKS,
    ReferenceGraphContractError,
    load_reference_graph,
    reference_graph_sha256,
    validate_reference_graph,
)

try:  # chemstate 的严格身份/CN 旁证与生产同一事实源
    from .chemstate import ChemicalStateError, strict_identity_of
    from ..domain.identity import cn_identity
except ImportError:  # pragma: no cover —— 环境异常时 fail-closed
    strict_identity_of = None  # type: ignore[assignment]
    cn_identity = None  # type: ignore[assignment]
    ChemicalStateError = RuntimeError  # type: ignore[assignment]

try:  # S5A-02:条件分类与冻结判据四同一事实源(path_context)
    from .path_context import (
        CONDITION_KEYS,
        CONDITION_KEY_UNITS,
        CONFLICT,
        INTERVAL_CONDITION_KEYS,
        NOT_APPLICABLE,
        REQUIREMENT_ESSENTIAL,
        REQUIREMENT_PREFERENCE,
        SATISFIED,
        UNKNOWN,
        VALUE_BASIS_ENTITY,
        VALUE_BASIS_LABEL,
        VALUE_BASIS_POINT,
        VALUE_BASIS_RANGE,
        aggregate_environment_fit,
        build_condition_fact,
        build_requirement,
    )
except ImportError:  # pragma: no cover —— 环境异常时 fail-closed
    aggregate_environment_fit = None  # type: ignore[assignment]
    build_condition_fact = None  # type: ignore[assignment]
    build_requirement = None  # type: ignore[assignment]

try:  # ppv1-criteria-v2:判据三许可集交集守卫的事实源(audit 无环)
    from .audit import COMPLETION_LICENSED_IDENTITIES
except ImportError:  # pragma: no cover —— 环境异常时 fail-closed
    COMPLETION_LICENSED_IDENTITIES = frozenset()  # type: ignore[assignment]

# ---- §12 状态枚举与程序可发子集 ----

SCIENTIFIC_STATUSES = frozenset({
    "pending_no_independent_data",
    "pending_preregistration",
    "pending_user_teacher_decision",
    "interface_verified_only",
    "evaluated_not_passed",
    "evaluated_passed_with_scope",
    "blocked_data_integrity",
    "blocked_leakage",
    "blocked_scoring_contract",
})
# 评测器永不发 evaluated_*(§11 第 19 步:最终科学状态由用户/teacher
# 按预注册结果裁定后另行登记)
EMITTED_STATUSES = frozenset(SCIENTIFIC_STATUSES - {
    "evaluated_not_passed", "evaluated_passed_with_scope"})

DATA_SCOPES = frozenset({"synthetic_rule_level", "real"})
PROVIDER_KINDS = frozenset({"none", "scripted", "real"})


def resolve_data_scope(raw_value, *, field: str = "data_scope",
                       default: str,
                       present: bool) -> tuple[str, dict]:
    """严格 data_scope 解析(S5B-V3-01;评测/判分首消费共用同一判据)。

    - ``present=False``(字段完全缺省)⇒ **既有缺省语义保留**:返回
      ``(default, {"field", "value", "normalized_from":
      "missing_field_default"})``——缺省与坏值不混为一类,归一来源
      机读披露(评测侧缺省 = synthetic_rule_level;判分侧缺省经
      函数签名默认 = real,由调用方登记);
    - ``present=True``(字段显式提供)⇒ 必须是 ``DATA_SCOPES`` 内的
      非空字符串;显式空串/None/bool/数值/未知字符串(含大小写变体、
      带空白)⇒ ``EvaluationContractError``(kind=data_scope_invalid,
      detail 携带 value/value_type/allowed)——**不用 ``or`` truthiness
      把显式坏值洗成 synthetic**(旧实现 ``get(...) or
      synthetic_rule_level`` 曾使显式空/None/False/0 绕过 real 门);
    - CLI choices 不代 API 校验:本函数是公开 score/evaluate API 的
      唯一权威判据(CLI 层 choices 只是输入便利);
    - 不做 strip/大小写归一(未知拼写如实拒,不猜意图)。

    返回 ``(scope, provenance)``;score 侧消费时包装为本契约异常
    (kind 前缀 s5b_),判据同源不另写第二套。
    """
    if not present:
        return default, {
            "field": field,
            "value": default,
            "normalized_from": "missing_field_default",
        }
    if isinstance(raw_value, bool) or not isinstance(raw_value, str):
        raise EvaluationContractError(
            f"评测输入字段 {field} 显式提供时必须是字符串枚举 "
            f"{sorted(DATA_SCOPES)}(显式 null/bool/数值/列表一律拒,"
            f"不用 truthiness 洗成 synthetic;缺字段才走缺省语义;"
            f"got {type(raw_value).__name__}:{raw_value!r})", {
                "kind": "data_scope_invalid",
                "field": field,
                "value": raw_value,
                "value_type": type(raw_value).__name__,
                "allowed": sorted(DATA_SCOPES),
                "normalized_from": None,
            })
    if raw_value == "" or raw_value not in DATA_SCOPES:
        raise EvaluationContractError(
            f"评测输入字段 {field} 取值非法:{raw_value!r}(允许 "
            f"{sorted(DATA_SCOPES)};显式空串/未知字符串/大小写变体一律"
            "结构化拒,不静默归一;缺字段才走缺省语义)", {
                "kind": "data_scope_invalid",
                "field": field,
                "value": raw_value,
                "value_type": type(raw_value).__name__,
                "allowed": sorted(DATA_SCOPES),
                "normalized_from": None,
            })
    return raw_value, {
        "field": field,
        "value": raw_value,
        "normalized_from": "explicit",
    }
SPLITS_LIST = sorted(SPLITS)
STOP_REASONS = frozenset({"budget_limit", "depth_limit",
                          "no_local_candidate", "awaiting_prediction",
                          "exhausted_search", "user_stop"})

# 金标内容唯一允许的落盘根(镜像 .gitignore 的金标隔离目录;S5b 前
# 评测输出本身不含金标 —— 本守卫为接口级预置,S5-27)
GOLD_AUTHORIZED_ROOTS = frozenset({
    "reports/phase_s0_hit60/manual_review",
    "reports/phase_s1_hit60/dev_gold",
    "reports/phase_s15_hit60/edit_path_replay/raw_inputs",
})

# ---- evaluation-4:样本↔导出配对档位与消费 digest 选择规则(机读) ----
PAIRING_BASIS_QID_STRICT = "qid_strict"
PAIRING_BASIS_ROOT_IDENTITY_FALLBACK = "root_identity_fallback"
DIGEST_SELECTION_QID_LIST_ORDER = \
    "native_path_exports_list_order_first"
DIGEST_SELECTION_ROOT_FALLBACK = \
    "root_identity_first_match_sorted_digest_order"
PAIRING_BASIS_NOTE = (
    "qid_strict:评测输入任一侧声明 qid ⇒ 全局严格 qid 配对——图按"
    " manifest 声明 qid(须在 root_entity.source_refs)只配同 qid 的"
    "可读导出(输入清单序),qid 无匹配 ⇒ not_evaluated(reason qid "
    "未配到),不按根身份张冠李戴;root_identity_fallback:两侧均未"
    "声明 qid(合成夹具路径)⇒ 回退根严格身份首中配对并在此机读披露"
    "(evaluation-4;evaluation-3 该回退为隐式行为);evaluation-5:"
    "data_scope=real 的配对首次消费禁止 root_identity_fallback(结构化"
    "拒 real_data_root_identity_fallback_forbidden,先于样本评分/聚合/"
    "结果写入——合成夹具回退与 real 严格档保持合法)")

# 评测器实际消费的结构化字段(S5-25:自然语言/自由文本字段不进
# 判定;本清单之外的一切输入字段一律忽略,不参与任何匹配或计数)。
# 条目级子字段(evaluation-4 起如实登记):native_path_exports 条目
# 消费 run_id/export_digest/lossy_projection/native_reference/
# lost_fields/qid;reference_graph_manifest 条目消费 reference_
# graph_id/sha256/domain/track/path/qid;graph 的 root_entity.source_
# refs 用于 qid 一致性核(只做成员核,不参与化学判定)。
_CONSUMED_INPUT_FIELDS = (
    "evaluator_schema_version", "run_identity", "native_path_exports",
    "reference_graph_manifest", "split_manifest", "domain", "track",
    "metric_policy_version", "preregistration_id",
    "scoring_policy_version", "missingness_policy_version",
    "data_scope", "interface_verification", "model_provider_policy",
)
_CONSUMED_EXPORT_FIELDS = (
    "states", "state_appearances", "paths", "hypotheses", "events",
    "alternatives", "coproducts", "contexts", "provenance_records",
    "audit_production_reports", "expansion_outcomes",
    "deferred_entries", "blocked_entries", "search_actions",
    "model_requests", "budget", "endpoint_record", "event_ids",
    "run_id", "native_result_version",
)


class EvaluationContractError(RuntimeError):
    """评测契约违反(结构化 fail-closed;零写入、零网络)。"""

    def __init__(self, message: str, detail: dict | None = None):
        super().__init__(message)
        self.detail = detail or {}


# ---------------------------------------------------------------- 输入校验


def _req_str(value, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise EvaluationContractError(
            f"评测输入字段 {field} 必须是非空字符串(缺字段明确失败,"
            "不静默补全)", {"kind": "evaluation_input_field_invalid",
                         "field": field})
    return value


def _req_enum(value, field: str, allowed: frozenset) -> str:
    _req_str(value, field)
    if value not in allowed:
        raise EvaluationContractError(
            f"评测输入字段 {field} 取值非法:{value!r}(允许 "
            f"{sorted(allowed)})", {"kind": "evaluation_input_enum_invalid",
                                 "field": field, "value": value,
                                 "allowed": sorted(allowed)})
    return value


def validate_evaluation_input(evaluation_input: dict) -> dict:
    """校验评测输入(§8.1;缺字段/未知枚举/混合题域与轨道拒绝)。

    S5-21/S5-22:输入声明单一 (domain, track);manifest 中任何参考图
    的 domain/track 与之不符 ⇒ 结构化拒绝(不产生无题域标签总分)。
    损坏输入结构化拒、不静默删字段。
    """
    if not isinstance(evaluation_input, dict):
        raise EvaluationContractError(
            "评测输入必须是对象", {"kind":
                                   "evaluation_input_not_object",
                                   "value_type":
                                   type(evaluation_input).__name__})
    for field in _CONSUMED_INPUT_FIELDS:
        if field not in evaluation_input and field not in (
                "data_scope", "interface_verification",
                "model_provider_policy"):
            raise EvaluationContractError(
                f"评测输入缺必需字段:{field}(§8.1;缺字段明确失败)",
                {"kind": "evaluation_input_field_missing",
                 "field": field})
    declared_version = str(evaluation_input.get(
        "evaluator_schema_version") or "")
    if declared_version != PPV1_EVALUATION_VERSION:
        raise EvaluationContractError(
            f"评测器 schema 版本未知:{declared_version!r}(当前 "
            f"{PPV1_EVALUATION_VERSION};fail-closed 不猜迁移)", {
                "kind": "evaluation_version_unknown",
                "field": "evaluator_schema_version"})
    domain = _req_enum(evaluation_input.get("domain"), "domain", DOMAINS)
    track = _req_enum(evaluation_input.get("track"), "track", TRACKS)
    run_identity = evaluation_input.get("run_identity")
    if not isinstance(run_identity, dict):
        raise EvaluationContractError(
            "run_identity 必须是对象", {"kind":
                                       "evaluation_input_field_invalid",
                                       "field": "run_identity"})
    for key in ("run_id", "profile_version", "export_schema_version"):
        if key not in run_identity:
            raise EvaluationContractError(
                f"run_identity.{key} 缺失", {
                    "kind": "evaluation_input_field_missing",
                    "field": f"run_identity.{key}"})
        _req_str(run_identity.get(key), f"run_identity.{key}")
    if str(run_identity.get("export_schema_version")) != \
            PPV1_NATIVE_EXPORT_VERSION:
        raise EvaluationContractError(
            f"run_identity.export_schema_version 与当前登记源不符:"
            f"{run_identity.get('export_schema_version')!r}"
            f"(当前 {PPV1_NATIVE_EXPORT_VERSION};S4 导出契约绑定)",
            {"kind": "evaluation_export_version_mismatch",
             "field": "run_identity.export_schema_version"})
    for field in ("metric_policy_version", "preregistration_id",
                  "scoring_policy_version", "missingness_policy_version"):
        _req_str(evaluation_input.get(field), field)
    # S5B-V3-01:严格 data_scope 校验(显式空/None/bool/数值/未知值
    # 结构化拒;字段完全缺省 ⇒ 既有缺省语义保留,evaluate_scientific
    # 同源归一并机读披露 normalized_from;不用 truthiness 洗白)
    resolve_data_scope(
        evaluation_input.get("data_scope"),
        field="data_scope", default="synthetic_rule_level",
        present="data_scope" in evaluation_input)
    if not isinstance(evaluation_input.get("interface_verification") or
                      False, bool):
        raise EvaluationContractError(
            "interface_verification 必须是布尔", {
                "kind": "evaluation_input_field_invalid",
                "field": "interface_verification"})
    # ---- provider 策略(默认关;real 无授权拒绝在 evaluate 侧) ----
    provider = evaluation_input.get("model_provider_policy") or {}
    if not isinstance(provider, dict):
        raise EvaluationContractError(
            "model_provider_policy 必须是对象(默认 {'provider_kind':"
            " 'none'})", {"kind": "evaluation_input_field_invalid",
                        "field": "model_provider_policy"})
    declared_provider = str(provider.get("provider_kind") or "none")
    if declared_provider not in PROVIDER_KINDS:
        raise EvaluationContractError(
            f"model_provider_policy.provider_kind 非法:"
            f"{declared_provider!r}(允许 {sorted(PROVIDER_KINDS)};"
            "默认 none = 无网络请求、零费用)", {
                "kind": "evaluation_input_enum_invalid",
                "field": "model_provider_policy.provider_kind"})
    # ---- 导出条目(§8.1;lossy 投影显式标记) ----
    exports = evaluation_input.get("native_path_exports")
    if not isinstance(exports, list):
        raise EvaluationContractError(
            "native_path_exports 必须是列表", {
                "kind": "evaluation_input_field_invalid",
                "field": "native_path_exports"})
    export_digests: set[str] = set()
    for i, entry in enumerate(exports):
        field = f"native_path_exports[{i}]"
        if not isinstance(entry, dict):
            raise EvaluationContractError(
                f"{field} 必须是对象", {"kind":
                                       "evaluation_input_field_invalid",
                                       "field": field})
        _req_str(entry.get("run_id"), f"{field}.run_id")
        digest = _req_str(entry.get("export_digest"),
                          f"{field}.export_digest")
        if digest in export_digests:
            raise EvaluationContractError(
                f"export_digest 重复:{digest}", {
                    "kind": "evaluation_input_duplicate_export",
                    "export_digest": digest})
        export_digests.add(digest)
        # ---- evaluation-4:导出条目 qid(可选;声明时必须非空字符串,
        # 空值不静默当未声明)——导出侧 run↔qid 映射的声明点 ----
        if entry.get("qid") is not None:
            _req_str(entry.get("qid"), f"{field}.qid")
        lossy = bool(entry.get("lossy_projection") or False)
        if lossy:
            # §3.1:消费 v3 有损投影必须标记 lossy + 原生引用 + 已丢字段
            if not isinstance(entry.get("native_reference"), str) or \
                    not entry.get("native_reference"):
                raise EvaluationContractError(
                    f"{field}.native_reference 缺失(lossy 投影必须声明"
                    "原生结果引用)", {
                        "kind": "evaluation_input_field_missing",
                        "field": f"{field}.native_reference"})
            if not isinstance(entry.get("lost_fields"), list):
                raise EvaluationContractError(
                    f"{field}.lost_fields 缺失(lossy 投影必须声明已丢"
                    "字段;该投影不得用于完整路径语义科学指标)", {
                        "kind": "evaluation_input_field_missing",
                        "field": f"{field}.lost_fields"})
    # ---- 参考图 manifest(S5-21/22:题域/轨道一致性) ----
    manifest = evaluation_input.get("reference_graph_manifest")
    if not isinstance(manifest, list) or not manifest:
        raise EvaluationContractError(
            "reference_graph_manifest 必须是非空列表", {
                "kind": "evaluation_input_field_invalid",
                "field": "reference_graph_manifest"})
    graph_ids: set[str] = set()
    manifest_qids: dict[str, str] = {}  # evaluation-4:qid → graph_id
    for i, entry in enumerate(manifest):
        field = f"reference_graph_manifest[{i}]"
        if not isinstance(entry, dict):
            raise EvaluationContractError(
                f"{field} 必须是对象", {
                    "kind": "evaluation_input_field_invalid",
                    "field": field})
        graph_id = _req_str(entry.get("reference_graph_id"),
                            f"{field}.reference_graph_id")
        if graph_id in graph_ids:
            raise EvaluationContractError(
                f"reference_graph_id 重复:{graph_id}", {
                    "kind": "evaluation_input_duplicate_reference_graph",
                    "reference_graph_id": graph_id})
        graph_ids.add(graph_id)
        _req_str(entry.get("sha256"), f"{field}.sha256")
        # ---- evaluation-4:manifest 条目 qid(可选;声明时必须非空
        # 字符串,且跨条目唯一——一题一图 G1 下重复 qid 会使 qid 配对
        # 歧义,fail-closed 不猜归属) ----
        entry_qid = entry.get("qid")
        if entry_qid is not None:
            _req_str(entry_qid, f"{field}.qid")
            if entry_qid in manifest_qids:
                raise EvaluationContractError(
                    f"reference_graph_manifest 的 qid 重复:{entry_qid!r}"
                    "(G1 一题一图:qid 是样本↔导出配对键,重复即歧义;"
                    "fail-closed,不猜归属)", {
                        "kind": "evaluation_input_duplicate_qid",
                        "qid": entry_qid,
                        "reference_graph_ids": sorted(
                            (manifest_qids.get(entry_qid), graph_id))})
            manifest_qids[entry_qid] = graph_id
        entry_domain = str(entry.get("domain") or "")
        entry_track = str(entry.get("track") or "")
        if entry_domain != domain:
            raise EvaluationContractError(
                f"参考图 {graph_id} 题域 {entry_domain!r} 与评测输入 "
                f"{domain!r} 不符(混合题域拒绝;dev/298 必须分开评测,"
                "不产生无题域标签总分;S5-21)", {
                    "kind": "evaluation_domain_mismatch",
                    "reference_graph_id": graph_id,
                    "manifest_domain": entry_domain,
                    "input_domain": domain})
        if entry_track != track:
            raise EvaluationContractError(
                f"参考图 {graph_id} 轨道 {entry_track!r} 与评测输入 "
                f"{track!r} 不符(known/unseen 混合拒绝;两轨道不得合并"
                "单一总分;S5-22)", {
                    "kind": "evaluation_track_mismatch",
                    "reference_graph_id": graph_id,
                    "manifest_track": entry_track,
                    "input_track": track})
    if not isinstance(evaluation_input.get("split_manifest"), dict):
        raise EvaluationContractError(
            "split_manifest 必须是对象", {
                "kind": "evaluation_input_field_invalid",
                "field": "split_manifest"})
    return evaluation_input


def validate_split_manifest(manifest: dict) -> dict:
    """校验划分清单(§6.3;确定性;同 source group 跨集合由 leakage
    检查另核,本层先核 schema 完整性)。"""
    if not isinstance(manifest, dict):
        raise EvaluationContractError(
            "split manifest 必须是对象", {
                "kind": "split_manifest_not_object"})
    if str(manifest.get("schema_version") or "") != \
            PPV1_SPLIT_MANIFEST_VERSION:
        raise EvaluationContractError(
            f"split manifest 版本未知:{manifest.get('schema_version')!r}"
            f"(当前 {PPV1_SPLIT_MANIFEST_VERSION};fail-closed)", {
                "kind": "split_manifest_version_unknown",
                "schema_version": str(manifest.get("schema_version")
                                       or "")})
    _req_str(manifest.get("split_manifest_id"), "split_manifest_id")
    _req_str(manifest.get("split_rule_version"), "split_rule_version")
    _req_str(manifest.get("input_data_manifest_hash"),
             "split_manifest.input_data_manifest_hash")
    assignments = manifest.get("assignments")
    if not isinstance(assignments, list):
        raise EvaluationContractError(
            "split_manifest.assignments 必须是列表", {
                "kind": "split_manifest_field_invalid",
                "field": "assignments"})
    graph_assignments: dict[str, str] = {}
    for i, assignment in enumerate(assignments):
        field = f"split_manifest.assignments[{i}]"
        if not isinstance(assignment, dict):
            raise EvaluationContractError(
                f"{field} 必须是对象", {
                    "kind": "split_manifest_field_invalid",
                    "field": field})
        for key in ("reference_graph_id", "source_group_id", "split"):
            if key not in assignment:
                raise EvaluationContractError(
                    f"{field}.{key} 缺失", {
                        "kind": "split_manifest_field_missing",
                        "field": f"{field}.{key}"})
        graph_id = _req_str(assignment.get("reference_graph_id"),
                            f"{field}.reference_graph_id")
        split = _req_enum(assignment.get("split"), f"{field}.split", SPLITS)
        if graph_id in graph_assignments and \
                graph_assignments[graph_id] != split:
            raise EvaluationContractError(
                f"参考图 {graph_id} 被指到多个 split:"
                f"{graph_assignments[graph_id]}/{split}", {
                    "kind": "split_manifest_duplicate_assignment",
                    "reference_graph_id": graph_id})
        graph_assignments[graph_id] = split
        _req_str(assignment.get("source_group_id"),
                 f"{field}.source_group_id")
    exclusion = manifest.get("unseen_exclusion_manifest")
    if not isinstance(exclusion, dict):
        raise EvaluationContractError(
            "split_manifest.unseen_exclusion_manifest 必须是对象"
            "(即使 known 轨道也须显式声明空排除范围)", {
                "kind": "split_manifest_field_invalid",
                "field": "unseen_exclusion_manifest"})
    _req_enum(exclusion.get("track") or "unseen_path_inference",
              "unseen_exclusion_manifest.track", TRACKS)
    excluded = exclusion.get("excluded") or []
    if not isinstance(excluded, list):
        raise EvaluationContractError(
            "unseen_exclusion_manifest.excluded 必须是列表", {
                "kind": "split_manifest_field_invalid",
                "field": "unseen_exclusion_manifest.excluded"})
    for i, item in enumerate(excluded):
        field = f"unseen_exclusion_manifest.excluded[{i}]"
        if not isinstance(item, dict):
            raise EvaluationContractError(
                f"{field} 必须是对象", {
                    "kind": "split_manifest_field_invalid",
                    "field": field})
        for key in ("source_group_id", "scope", "reason"):
            if key not in item:
                raise EvaluationContractError(
                    f"{field}.{key} 缺失(未见排除范围必须显式:精确反应"
                    "/精确底物/精确边/整条研究路线 + 理由)", {
                        "kind": "split_manifest_field_missing",
                        "field": f"{field}.{key}"})
        _req_str(item.get("source_group_id"), f"{field}.source_group_id")
        _req_str(item.get("scope"), f"{field}.scope")
        _req_str(item.get("reason"), f"{field}.reason")
    return manifest


# ---------------------------------------------------------------- 泄漏检查


def check_leakage(split_manifest: dict,
                  reference_graphs: dict[str, dict]) -> dict:
    """防泄漏检查(§6.3;S5-07/S5-08;失败 ⇒ blocked_leakage,不聚合)。

    - 同一 source_group_id 跨 development/tuning/held_out/
      independent_confirmation 集合 ⇒ violation(S5-07);
    - 同一研究路线(route_group_key)跨集合 ⇒ violation(§6.3 同研究
      相邻边/高度相关路线不得拆到不同集合;proposed 规则);
    - unseen 排除范围与 known 评测集直接证据重叠 ⇒ violation(S5-08);
    - 同根对象跨 development 与 held_out/independent_confirmation ⇒
      violation(proposed:研究来源高度相关的根按 group split 整体划分);
    - 多数据库记录归并 source group 的记账(记录数 vs 组数)与
      independence unknown 组披露(S5-05/S5-06;披露非 violation)。
    """
    violations: list[dict] = []
    group_splits: dict[str, set[str]] = {}
    for assignment in split_manifest.get("assignments") or []:
        group_id = str(assignment.get("source_group_id"))
        split = str(assignment.get("split"))
        group_splits.setdefault(group_id, set()).add(split)
    for group_id, splits in sorted(group_splits.items()):
        if len(splits) > 1:
            violations.append({
                "check": "source_group_across_splits",
                "source_group_id": group_id,
                "splits": sorted(splits),
                "spec": "S5-07/§6.3:同一 source_group_id 不得跨开发/留出"
                        "/独立确证集合"})
    # ---- 路线/根对象跨集合(proposed 规则级) ----
    route_splits: dict[str, set[str]] = {}
    root_splits: dict[str, set[str]] = {}
    group_route: dict[str, str] = {}
    for graph_id, graph in sorted(reference_graphs.items()):
        assignment = graph.get("split_assignment") or {}
        split = str(assignment.get("split") or "")
        for route_key in assignment.get("route_group_keys") or []:
            route_splits.setdefault(str(route_key), set()).add(split)
        root_splits.setdefault(
            str((graph.get("root_entity") or {}).get("entity_id") or ""),
            set()).add(split)
        for group_ref in (graph.get("source_groups") or []):
            group_route.setdefault(
                str(group_ref.get("source_group_id")), split)
    for route_key, splits in sorted(route_splits.items()):
        if len(splits) > 1:
            violations.append({
                "check": "route_identity_across_splits",
                "route_group_key": route_key,
                "splits": sorted(splits),
                "spec": "§6.3:同一研究路线/相邻边不得拆到不同集合"
                        "(proposed)"})
    for root_id, splits in sorted(root_splits.items()):
        if len(splits) > 1 and ("development" in splits and (
                "held_out" in splits or "independent_confirmation"
                in splits)):
            violations.append({
                "check": "root_entity_across_development_and_held_out",
                "root_entity_id": root_id,
                "splits": sorted(splits),
                "spec": "§6.3:同根对象研究来源高度相关时按 group split "
                        "整体划分(proposed)"})
    # ---- known/unseen 直接证据重叠(S5-08) ----
    excluded_groups = sorted({
        str(item.get("source_group_id"))
        for item in ((split_manifest.get("unseen_exclusion_manifest")
                      or {}).get("excluded") or [])})
    known_groups = sorted(group_splits)
    overlap = sorted(set(excluded_groups) & set(known_groups))
    if overlap:
        violations.append({
            "check": "unseen_exclusion_overlaps_known_evaluation",
            "source_group_ids": overlap,
            "spec": "S5-08:known 与 unseen 直接证据重叠 ⇒ 未见轨道排除"
                    "检查失败,不继续聚合"})
    # ---- 记账与披露(非 violation) ----
    record_count = 0
    unknown_independence: list[str] = []
    for graph in reference_graphs.values():
        for group in graph.get("source_groups") or []:
            record_count += len(group.get("member_records") or [])
            if str(group.get("independence_status")) == "unknown":
                unknown_independence.append(
                    str(group.get("source_group_id")))
    return {
        "status": "failed" if violations else "passed",
        "violations": violations,
        "statistics": {
            "source_group_count": len(group_splits),
            "database_record_count": record_count,
            "record_to_group_ratio_note": (
                "同一来源组的多条数据库记录只计一个 source group"
                "(S5-05);不虚增独立支持"),
            "unknown_independence_groups": sorted(
                set(unknown_independence)),
            "unknown_independence_note": (
                "independence=unknown 的组不进入要求独立支持的指标分母"
                "(S5-06;除非预注册另有规定)"),
        },
    }


# ---------------------------------------------------------------- ppv1-criteria-v2:T-1 豁免常量与谓词
#
# 预注册:docs/POLLUTANT_PATHWAY_CRITERIA_V2_PREREGISTRATION_2026-10-13.md
# (§一 清单/§二 三谓词/§三 完备二分/§四 机器挡板/§五 披露/§六 版本)。
# 纪律:豁免缺省关(v1)⇒ 本节运行期函数零调用、输出零新键;判定键 =
# cn 身份(非族签名;补证已验签名≡cn 本批零漂移);fail-closed。

PPV1_CRITERIA_V1 = "ppv1-criteria-v1"
PPV1_CRITERIA_V2 = "ppv1-criteria-v2"
# ppv1-criteria-v3(T-D-A/B 判分侧披露轴;token 在此登记以便白名单前置
# 构造;语义权威 = FROZEN_V3,常量与实现见下文 criteria-v3 段)
PPV1_CRITERIA_V3 = "ppv1-criteria-v3"
# ppv1-criteria-v4(matched_product_hit 主口径;语义权威 = 预注册草案
# docs/CRITERIA_V4_MATCHED_PRODUCT_HIT_PREREG_DRAFT_2026-10-28.md;
# 常量与实现见下文 criteria-v4 段)
PPV1_CRITERIA_V4 = "ppv1-criteria-v4"
# ppv1-criteria-v5(role_bound_product_hit;语义权威 = 已签预注册草案
# docs/tasks/active/CRITERIA_V5_ROLE_BOUND_PREREG_DRAFT_2026-11-05.md;
# 常量与实现见下文 criteria-v5 段;v5 = v4 + 事件产物侧 role 约束)
PPV1_CRITERIA_V5 = "ppv1-criteria-v5"
PPV1_CRITERIA_VERSIONS = frozenset({PPV1_CRITERIA_V1, PPV1_CRITERIA_V2,
                                    PPV1_CRITERIA_V3, PPV1_CRITERIA_V4,
                                    PPV1_CRITERIA_V5})
PPV1_CRITERIA_V2_PREREGISTRATION_DOC = (
    "docs/POLLUTANT_PATHWAY_CRITERIA_V2_PREREGISTRATION_2026-10-13.md")

# ---- 完备二分的恰好两个 tier(mimo r36 条件 5;单归属断言见运行期) ----
CRITERIA_TIER_V1_EXEMPT = "v1_exempt"
CRITERIA_TIER_NOT_EXEMPT = "not_exempt_maintains_partial"
CRITERIA_TIERS = frozenset({CRITERIA_TIER_V1_EXEMPT,
                            CRITERIA_TIER_NOT_EXEMPT})
# T1′ 档未实施 ⇒ 未声明多余产物维持 partial(明字常量;mimo r36 M3.4:
# 不得理解为"应当实施 T1′ 以补齐二分")
CRITERIA_T1P_NOT_IMPLEMENTED_NOTE = (
    "T1'(coproduct_ignore_tier)未实施:未声明多余产物不进任何忽略档,"
    "恒维持 partial(not_exempt_maintains_partial);完备二分 = "
    "v1_exempt | not_exempt_maintains_partial,无第三态")

# ---- 方向限定版豁免清单(§一;变体组照抄 CS2c 补证脚本 V1_VARIANTS) ----
# 显式 SMILES 列名仅为裁定已列名的规则常量;判定键 = cn 身份收敛键。
_CRITERIA_V2_EXEMPT_VARIANTS = {
    "v1:H2O": ("O", "[OH-]", "[OH3+]"),
    "v1:H+": ("[H+]",),
    "v1:Pi": ("OP(=O)(O)O", "[O-]P(=O)(O)O", "[O-]P(=O)([O-])O",
              "[O-]P(=O)([O-])[O-]"),
    "v1:PPi": ("O=P(O)(O)OP(=O)(O)O", "[O-]P(=O)(O)OP(=O)(O)[O-]",
               "[O-]P(=O)([O-])OP(=O)([O-])[O-]",
               "O=P([O-])([O-])OP(=O)([O-])([O-])"),
}
# mimo r36 条件 1/M1:产物侧四类全收;反应物侧仅 H₂O/H⁺(Pi/PPi 作
# 反应物是磷酰化机制成分,A+PPi→A-P+Pi 与 A+Pi→A-P 不可塌缩)。
CRITERIA_V2_EXEMPT_FAMILIES_PRODUCT = ("v1:H2O", "v1:H+", "v1:Pi",
                                       "v1:PPi")
CRITERIA_V2_EXEMPT_FAMILIES_REACTANT = ("v1:H2O", "v1:H+")

# ---- 机器挡板:辅因子硬拒绝表(mimo r36 条件 1 附;正面清单语义 +
# 常量测试 + 合成负控钉死;进比较面绝不豁免) ----
CRITERIA_V2_NEVER_EXEMPT_FAMILIES = (
    "NAD(P)+/NAD(P)H", "ATP/ADP/AMP", "CoA", "FAD/FMN", "THF",
    "O2", "NH3", "CN-", "SCN-", "H2O2", "NH2OH", "NO",
)
# known gap(mimo r36 M1 末,预注册 §十.1):含碳身份构造非法断言把
# r28 A2 曾建议白名单的 CO₂/HCO₃⁻/CO₃²⁻ 挡在豁免面外 —— 登记为 v2
# 未来冲突点,不静默重开。


def _build_criteria_v2_identity_sets() -> dict:
    """导入期构建豁免身份集(收敛断言 + 零碳断言 + 许可集交集断言)。

    fail-closed:cn 身份工具缺席(identity 导入回退 None)⇒ 返回空集
    并置工具可用旗 False(resolve_criteria_version 对 v2 结构化拒);
    任何收敛/零碳/交集断言失败 ⇒ 导入期 RuntimeError(不静默带病
    上线)。变体组与判定口径 = CS2c 补证脚本 identity_checks 同源
    (其验证结论:四类各自收敛单一 cn 键、cn 幂等、Uncharger 往返
    稳定、与许可集交集 ∅)。"""
    empty = {
        "available": False,
        "by_family": {},
        "product": frozenset(),
        "reactant": frozenset(),
        "all": frozenset(),
        "sha256_16_by_cn": {},
        "family_by_cn": {},
    }
    if cn_identity is None:  # pragma: no cover —— 环境异常 fail-closed
        return empty
    try:
        from rdkit import Chem as _Chem, RDLogger as _RDLogger
        _RDLogger.DisableLog("rdApp.*")
    except ImportError:  # pragma: no cover —— 环境异常 fail-closed
        return empty
    by_family: dict[str, str] = {}
    for family, variants in _CRITERIA_V2_EXEMPT_VARIANTS.items():
        cns = {cn_identity(v) for v in variants}
        if len(cns) != 1 or None in cns:
            raise RuntimeError(
                f"ppv1-criteria-v2 豁免身份变体未收敛单一 cn 键:"
                f"{family}(导入期 fail-closed,不静默带病上线)")
        key = next(iter(cns))
        # 机器挡板:含碳身份禁入豁免构造(零碳断言;CO₂/HCO₃⁻ known gap)
        mol = _Chem.MolFromSmiles(key)
        if mol is None or any(a.GetSymbol() == "C" for a in mol.GetAtoms()):
            raise RuntimeError(
                f"ppv1-criteria-v2 豁免身份构造非法(含碳或不可解析):"
                f"{family} -> {key!r}(导入期 fail-closed)")
        by_family[family] = key
    product = frozenset(by_family[f] for f in
                        CRITERIA_V2_EXEMPT_FAMILIES_PRODUCT)
    reactant = frozenset(by_family[f] for f in
                         CRITERIA_V2_EXEMPT_FAMILIES_REACTANT)
    all_ids = product | reactant
    # 判据三边界:豁免身份与 completion-licensed 集合无交集
    # (H⁺ 不得与 [H]/[H][H] 合流;常量测试另行钉死)
    overlap = sorted(all_ids & set(COMPLETION_LICENSED_IDENTITIES))
    if overlap:
        raise RuntimeError(
            f"ppv1-criteria-v2 豁免身份与 COMPLETION_LICENSED_IDENTITIES "
            f"交集非空:{overlap}(导入期 fail-closed)")
    return {
        "available": True,
        "by_family": by_family,
        "product": product,
        "reactant": reactant,
        "all": all_ids,
        "sha256_16_by_cn": {
            key: hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]
            for key in all_ids},
        "family_by_cn": {v: k for k, v in by_family.items()},
    }


_CRITERIA_V2_IDENTITIES = _build_criteria_v2_identity_sets()


def resolve_criteria_version(raw_value: str) -> str:
    """判据版本严格解析(fail-closed;评测/判分入口共用同一判据)。

    非 {ppv1-criteria-v1, ppv1-criteria-v2, ppv1-criteria-v3,
    ppv1-criteria-v4, ppv1-criteria-v5} 一律结构化拒(不猜、不静默
    归一);v2/v4/v5 请求而身份工具缺席 ⇒ 拒(v2/v4/v5 均依赖同一严格
    身份事实源,无法判定时宁可不开);v3 请求而 RDKit 归一引擎/参数
    指纹不可得 ⇒ 拒(v3 判据无法评估且不得留空指纹上线)。"""
    if raw_value not in PPV1_CRITERIA_VERSIONS:
        raise EvaluationContractError(
            f"criteria_version 非法:{raw_value!r}(允许 "
            f"{sorted(PPV1_CRITERIA_VERSIONS)};缺省 {PPV1_CRITERIA_V1} = "
            "豁免关;ppv1-criteria-v2 为 teacher T-1 裁定豁免口径,"
            "ppv1-criteria-v3 为 T-D-A/B 披露轴口径,"
            "ppv1-criteria-v4 为 matched_product_hit 主口径,"
            "ppv1-criteria-v5 为 role_bound_product_hit 主口径候选,"
            "均显式启用)", {
                "kind": "criteria_version_invalid",
                "value": raw_value,
                "allowed": sorted(PPV1_CRITERIA_VERSIONS)})
    if raw_value == PPV1_CRITERIA_V2 and \
            not _CRITERIA_V2_IDENTITIES["available"]:
        raise EvaluationContractError(
            "criteria_version=ppv1-criteria-v2 而 cn 身份工具/身份集"
            "不可用(fail-closed:v2 判据无法评估,不降级不猜测)", {
                "kind": "criteria_v2_identity_tools_unavailable"})
    if raw_value == PPV1_CRITERIA_V4 and strict_identity_of is None:
        raise EvaluationContractError(
            "criteria_version=ppv1-criteria-v4 而严格身份工具不可用"
            "(fail-closed:v4 判据无法评估,不降级不猜测)", {
                "kind": "criteria_v4_identity_tools_unavailable"})
    if raw_value == PPV1_CRITERIA_V5 and strict_identity_of is None:
        # v5 = v4 + 事件侧 role 约束,共用同一严格身份事实源;
        # 无法判定时宁可不开启(fail-closed,不降级到 v4 角色盲)
        raise EvaluationContractError(
            "criteria_version=ppv1-criteria-v5 而严格身份工具不可用"
            "(fail-closed:v5 判据无法评估,不降级不猜测)", {
                "kind": "criteria_v5_identity_tools_unavailable"})
    if raw_value == PPV1_CRITERIA_V3:
        registry = _criteria_v3_arm_registry()
        if not registry.get("available"):
            raise EvaluationContractError(
                "criteria_version=ppv1-criteria-v3 而 RDKit 归一引擎/"
                "参数指纹不可得(fail-closed:v3 判据无法评估,不降级、"
                "不留空指纹、不猜测)", {
                    "kind": "criteria_v3_engine_unavailable",
                    "unavailable_reason": registry.get(
                        "unavailable_reason")})
    return raw_value


# ---------------------------------------------------------------- ppv1-criteria-v3:T-D-A/B 披露轴
#
# 生效口径(唯一语义权威):docs/POLLUTANT_PATHWAY_CRITERIA_FROZEN_V3_2026-10-19.md
# (§4.2 A-1..A-8 / §4.3 B-1..B-7 / §4.4 C1-C3 / §6 / §8 / §10 / §11)。
# 纪律(硬性):
# - **档 A 只披露**:A/B 轴归一相等只产出披露(不授 strict、不进
#   hit@1);`tautomer_promoted_nodes` 本轮恒空(档 B 未解锁,D03);
# - **判分侧互变归一禁改**:match_reference_nodes 的 match_status /
#   strict 判定与 S5A-01 许可门零改动;本轴不越过封顶节点;
# - **适用面(A-1)**:仅参考节点 `structure_identity_scope ==
#   "strict_structure"` 的 cn_only 配对;其余沿用 V1 封顶;
# - **无静默路径(B 轴)**:ChargeParent 臂仅并列敏感性披露;
#   碳酸体系闭集(B-6)逐对象排除并落机读原因;
# - **fail-closed 无第三态**:任一侧不可解析/算子异常 ⇒ 不授归一
#   相等 + 逐臂机读原因;单归属断言(A→B);
# - 缺省 v1/v2:本节运行期函数零调用、输出零新键(字节不变)。

PPV1_CRITERIA_V3_FROZEN_DOC = (
    "docs/POLLUTANT_PATHWAY_CRITERIA_FROZEN_V3_2026-10-19.md")

# 档位(A-4):本轮唯一启用档 = 披露档;档 B = 未来解锁门槛(本轮未解锁)
CRITERIA_V3_TIER_DISCLOSURE_ONLY = "disclosure_only"
CRITERIA_V3_TIER_B_STATUS = "locked_not_unlocked_this_round"
CRITERIA_V3_DISCLOSURE_ONLY_NOTE = (
    "档 A(仅披露轴,本轮唯一启用):A/B 轴归一相等只产出披露档,"
    "不授 strict、不进 hit@1;档 B(判据档提升)为未来解锁门槛,"
    "本轮未解锁(D03)——tautomer_promoted_nodes 恒无")

# A 轴双臂(A-2/A-3/A-6;双臂独立保存、分开报数,不得混报)
CRITERIA_V3_TAUTOMER_ARM_DEFAULT = "default"
CRITERIA_V3_TAUTOMER_ARM_STEREO_PRESERVING = "stereo_preserving"
CRITERIA_V3_TAUTOMER_ARMS = (CRITERIA_V3_TAUTOMER_ARM_DEFAULT,
                             CRITERIA_V3_TAUTOMER_ARM_STEREO_PRESERVING)
CRITERIA_V3_TAUTOMER_PRIMARY_ARM = \
    CRITERIA_V3_TAUTOMER_ARM_STEREO_PRESERVING
CRITERIA_V3_DEFAULT_ARM_STRICT_ELIGIBLE = False
CRITERIA_V3_DEFAULT_ARM_NOTE = (
    "默认臂 = 「互变归一(互变中心立体容忍)」:手性负控已实测 FAIL"
    "(合成对照),登记为敏感性披露臂,不具 strict 准入;其布尔无论"
    "如何都不进任何档 B 路径")
CRITERIA_V3_PRIMARY_ARM_NOTE = (
    "候选主臂(sp3 立体保留)= 档 B 未来唯一候选(本轮未解锁);"
    "removeBondStereo 保持默认 true ⇒ 键/E-Z 立体仍可能被擦除,"
    "属未核范围")

# B 轴(B-1/B-2/B-5):默认单启用 Uncharger 臂;ChargeParent 臂仅并列
# 敏感性披露(不作默认、无静默路径)
CRITERIA_V3_PROTONATION_ARM_UNCHARGER = "uncharger"
CRITERIA_V3_PROTONATION_ARM_CHARGE_PARENT = "charge_parent"
CRITERIA_V3_PROTONATION_ARMS = (CRITERIA_V3_PROTONATION_ARM_UNCHARGER,
                                CRITERIA_V3_PROTONATION_ARM_CHARGE_PARENT)
CRITERIA_V3_PROTONATION_ENABLED_ARM = \
    CRITERIA_V3_PROTONATION_ARM_UNCHARGER
CRITERIA_V3_CHARGE_PARENT_SENSITIVITY_NOTE = (
    "ChargeParent 臂仅并列敏感性披露(不合并判据;合并即掩两臂差异)")

# 归一来源字段(A-6;逐臂机读)
CRITERIA_V3_NORMALIZATION_SOURCES = {
    CRITERIA_V3_TAUTOMER_ARM_DEFAULT: "tautomer_enumerator_default_v1",
    CRITERIA_V3_TAUTOMER_ARM_STEREO_PRESERVING:
        "tautomer_enumerator_stereo_preserving_v1",
    CRITERIA_V3_PROTONATION_ARM_UNCHARGER: "uncharger_default_v1",
    CRITERIA_V3_PROTONATION_ARM_CHARGE_PARENT: "charge_parent_v1",
}

# B-6 碳酸体系特定物种(闭集;含仅质子化写法变异经同算子落回同集合者;
# 增删 = 判据版本升号,禁止静默扩围;非"所有含碳对")
CRITERIA_V3_CARBONATE_SYSTEM_SPECIES = ("O=C=O", "O=C(O)[O-]",
                                        "O=C([O-])[O-]")
CRITERIA_V3_CARBONATE_EXCLUSION_REASON = "carbonate_system_exclusion"
CRITERIA_V3_CARBONATE_SET_NOTE = (
    "B-6 硬边界:碳酸体系特定物种闭集(CO₂/HCO₃⁻/CO₃²⁻ 及仅质子化"
    "写法变异,经 B-1 同算子归一后落回同集合者);两侧均命中 ⇒ 该"
    "配对逐对象排除,机读原因 = carbonate_system_exclusion;"
    "非'所有含碳对',与 V2 零碳断言同向保守,不重开 V2 裁定")

# 叙事纪律(修订记录 v2 条 8 / §3.7):芳香 0 题固定句;单批不宣称稳定
CRITERIA_V3_AROMATIC_REPR_NOTE = (
    "AROMATIC-REPR 轴本轮未实施/未启用:该轴覆盖未证;对外表述"
    "必须附「本批 AROMATIC-REPR=0,该轴未启用、覆盖未证」,"
    "禁用「三类表示差已覆盖」类表述")
CRITERIA_V3_SINGLE_BATCH_NOTE = (
    "单批不宣称稳定:全部数字来自单批 post-hoc 已见题,不得据此"
    "宣称泛化能力或'机制成立'")
CRITERIA_V3_MEASUREMENT_NOTE = (
    "A/B 属判据修正类 ⇒ 只能表述「测量修正」,禁止表述为系统能力"
    "提升(§9 叙事纪律)")
CRITERIA_V3_PAIR_ATTRIBUTION_ORDER = ("tautomer", "protonation", "none")

# 失败原因(机读码;fail-closed 无第三态)
CRITERIA_V3_REASON_UNPARSEABLE = "structure_unparseable"
CRITERIA_V3_REASON_EMPTY_SIDE = "empty_side"
CRITERIA_V3_REASON_EMPTY_TAUTOMER = "tautomer_canonicalize_empty"

_CRITERIA_V3_ARM_ORDER = (
    CRITERIA_V3_TAUTOMER_ARM_DEFAULT,
    CRITERIA_V3_TAUTOMER_ARM_STEREO_PRESERVING,
    CRITERIA_V3_PROTONATION_ARM_UNCHARGER,
    CRITERIA_V3_PROTONATION_ARM_CHARGE_PARENT,
)


def _criteria_v3_sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _criteria_exemption_enabled(criteria_version: str) -> bool:
    """参与物集合比较豁免判分路径是否启用(单一事实源)。

    v2 = 豁免口径本身;v3 = **承载 v2 判分语义**(正交性:N3/N7 ——
    v3 启用时 V2 tier 计数同 payload 与 v2 逐位一致)并叠加 T-D-A/B
    披露轴;v1 = 豁免关(零新键、字节不变);**v4 = 豁免旁路**
    (预注册草案 §4:matched_product_hit 本就不要求集合相等)——
    返回 False,批级披露豁免计数 0。"""
    return criteria_version in (PPV1_CRITERIA_V2, PPV1_CRITERIA_V3)


# ---------------------------------------------------------------- ppv1-criteria-v4:matched_product_hit
#
# 语义权威(唯一):docs/CRITERIA_V4_MATCHED_PRODUCT_HIT_PREREG_DRAFT_2026-10-28.md
# (§1 定义 / §2 合法事件 / §3 桶 / §4 版本组合)。纪律见模块 docstring
# 「ppv1-criteria-v4」段:只加分支、身份函数不改、目标集合只取
# principal_product、禁止跨事件拼答案、保留原 coverage 事实、v2 豁免
# 旁路、与 v3 正交、命名不得称 strict。

PPV1_CRITERIA_V4_PREREG_DOC = (
    "docs/CRITERIA_V4_MATCHED_PRODUCT_HIT_PREREG_DRAFT_2026-10-28.md")
CRITERIA_V4_METRIC_NAME = "matched_product_hit"
CRITERIA_V4_HIT_MODE_SCOPE = (
    "declared_principal_products_and_substrate_identity")
CRITERIA_V4_BUCKET_MATCHED = "matched_product_hit"
CRITERIA_V4_BUCKET_PARTIAL = "product_hit_partial"
CRITERIA_V4_BUCKET_NO_EVENT = "unmatched_no_event"
CRITERIA_V4_BUCKET_REFERENCE_INVALID = "unmatched_reference_invalid"
CRITERIA_V4_BUCKET_PRODUCT_MISMATCH = "unmatched_product_mismatch"
CRITERIA_V4_BUCKETS = (
    CRITERIA_V4_BUCKET_MATCHED,
    CRITERIA_V4_BUCKET_PARTIAL,
    CRITERIA_V4_BUCKET_NO_EVENT,
    CRITERIA_V4_BUCKET_REFERENCE_INVALID,
    CRITERIA_V4_BUCKET_PRODUCT_MISMATCH,
)
CRITERIA_V4_REFERENCE_EVALUABLE = "evaluable"
CRITERIA_V4_REFERENCE_TARGET_EMPTY = "reference_target_empty"
CRITERIA_V4_REFERENCE_NODE_MISSING = "reference_node_missing"
CRITERIA_V4_REFERENCE_UNPARSEABLE = "reference_structure_unparseable"
CRITERIA_V4_REFERENCE_SCOPE_INSUFFICIENT = (
    "reference_identity_scope_insufficient")
CRITERIA_V4_METRIC_DISCIPLINE_NOTE = (
    "本指标机器名 matched_product_hit;不得称为 strict,与 v2 strict "
    "分列,禁止跨版本比较 strict 数;对外表述限「仅声明主产物身份"
    "命中」,不得写成「反应预测正确率」")
CRITERIA_V4_COVERAGE_PRESERVATION_NOTE = (
    "v4 只新增判定轴,不改写原 coverage 事实:exact/superset/"
    "partial_subset 保持判分器原值(superset 不得改写成 exact)")
CRITERIA_V4_EXEMPTION_BYPASS_NOTE = (
    "v4 旁路 ppv1-criteria-v2 参与物集合豁免(§4):豁免计数恒 0,"
    "不与 v2 读数混算;v2 豁免块不出现在 v4 输出中")


def _criteria_v3_disclosure_enabled(criteria_version: str,
                                    disclosure_criteria_versions
                                    ) -> bool:
    """v3 披露轴是否启用(主版本 v3,或 v4 + v3 并列披露)。

    缺省(空披露清单)时与既有行为逐位一致:v1/v2 零 v3 键,
    v3 主版本照旧启用。"""
    if criteria_version == PPV1_CRITERIA_V3:
        return True
    return PPV1_CRITERIA_V3 in tuple(disclosure_criteria_versions or ())


def _validate_disclosure_criteria_versions(disclosure_criteria_versions
                                           ) -> tuple[str, ...]:
    """披露轴版本白名单(仅 ppv1-criteria-v3;fail-closed)。

    v3 是唯一的披露轴;v1/v2/v4 都是判分主口径,不能作为并列披露轴
    (并列即两把主尺子,不允许)。v3 请求沿用 ``resolve_criteria_version``
    的引擎/指纹门(v3 请求而引擎不可得 ⇒ 结构化拒)。"""
    tokens = tuple(disclosure_criteria_versions or ())
    for token in tokens:
        if token not in PPV1_CRITERIA_VERSIONS:
            raise EvaluationContractError(
                f"disclosure_criteria_versions 非法:{token!r}(允许 "
                f"{sorted(PPV1_CRITERIA_VERSIONS)})", {
                    "kind": "criteria_disclosure_version_invalid",
                    "value": token,
                    "allowed": sorted(PPV1_CRITERIA_VERSIONS)})
        if token != PPV1_CRITERIA_V3:
            raise EvaluationContractError(
                f"disclosure_criteria_versions 只接受披露轴 "
                f"{PPV1_CRITERIA_V3}:收到 {token!r}(v1/v2/v4 是判分主"
                "口径,不是披露轴,不能并列)", {
                    "kind": "criteria_disclosure_version_not_disclosure_axis",
                    "value": token,
                    "allowed": [PPV1_CRITERIA_V3]})
        resolve_criteria_version(token)
    return tokens


def _criteria_v4_identity_sha256_16(identity: str) -> str:
    """身份键的 sha256 前 16 位(披露用;输出零 SMILES)。"""
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()[:16]


def _criteria_v3_canonical_fingerprint(payload: dict) -> str:
    """参数指纹(§3 条 3/R03/§8):sha256(canonical_json(env+params),
    ensure_ascii=True)——与前置 1 重算登记口径逐臂一致。"""
    import json as _json
    return _criteria_v3_sha256_text(_json.dumps(
        payload, ensure_ascii=True, sort_keys=True,
        separators=(",", ":")))


def _criteria_v3_sha256_file(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


@lru_cache(maxsize=1)
def _criteria_v3_arm_registry() -> dict:
    """V3 算子/参数登记 + 分臂指纹(fail-closed;不可自省面单列登记)。

    指纹口径(FROZEN_V3 §3 条 3/§8)=
    sha256(canonical_json({"env": 环境, "params": 该臂实际生效参数})):

    - 各臂**实际生效**参数(含未显式设置项的实测默认有效值:
      ``tautomerRemoveIsotopicHs`` / ``tautomerReassignStereo`` /
      ``maxRestarts``)——由 CleanupParameters/TautomerEnumerator
      getter 实测读出,不以文档语义替代;
    - 双臂差异逐项 diff(default vs stereo_preserving,单列登记);
    - ``transforms`` 文件哈希:本 RDKit 构建无 ``tautomerTransforms.in``
      (数据嵌于 libRDKitMolStandardize)⇒ 以原子库
      libRDKitMolStandardize / rdMolStandardize.so 的 sha256 **替代
      登记并披露**(存在真实文件时直接哈希该文件);
    - RDKit 版本串(含 build/python)。

    任一必需事实不可得 ⇒ ``available=False`` + 原因(不猜、不留空
    指纹;resolve_criteria_version 对 v3 结构化拒)。
    """
    try:
        import rdkit as _rdkit_pkg
        from rdkit import rdBase as _rdBase
        from rdkit.Chem.MolStandardize import rdMolStandardize as _rms
    except ImportError as exc:  # pragma: no cover —— 环境异常 fail-closed
        return {"available": False,
                "unavailable_reason": f"rdkit_import_error:{type(exc).__name__}",
                "environment": {}, "arms": {}, "dual_arm_diff": {},
                "carbonate_system": {}}
    import sys as _sys
    pkg = Path(_rdkit_pkg.__file__).parent
    # 引擎 C++ 库定位——平台化（T-H 部署轮修复,2026-10-20）:macOS wheel
    # 在 ``pkg/.dylibs/*.dylib``;Linux conda 在 ``$prefix/lib/*.so*``;
    # Linux pip wheel 在 ``site-packages/rdkit.libs/*.so*``。原版仅查
    # macOS 路径 ⇒ Linux 上 dylib_sha=None ⇒ v3 判据被 fail-closed
    # （HPC venv/rdkit 2026.03.5 实测）。语义不变:仍以引擎原子库
    # 实文件 sha256 替代登记 **tautomerTransformsFile 缺席** 之指纹。
    import glob as _glob
    import sysconfig as _sysconfig
    dylib_candidates = [
        pkg / ".dylibs" / "libRDKitMolStandardize.1.dylib",
    ]
    _roots = [Path(_sys.prefix) / "lib",
              Path(_sysconfig.get_paths().get("purelib") or "."),
              pkg.parent]
    # conda 布局锚:rdkit 包位在 ``<env>/lib/pythonX.Y/site-packages/rdkit``
    # ⇒ C++ 库在 ``<env>/lib/`` = pkg.parents[2](再兜一层 parents[3])
    if len(pkg.parents) >= 3:
        _roots.append(pkg.parents[2])
    if len(pkg.parents) >= 4:
        _roots.append(pkg.parents[3] / "lib")
    for _root in _roots:
        for _pat in ("libRDKitMolStandardize*.so*",
                     "rdkit.libs/libRDKitMolStandardize*.so*"):
            dylib_candidates += [Path(p) for p in
                                 sorted(_glob.glob(str(_root / _pat)))]
    dylib_sha, dylib_path = None, None
    for _cand in dylib_candidates:
        _s = _criteria_v3_sha256_file(_cand)
        if _s:
            dylib_sha, dylib_path = _s, str(_cand)
            break
    so_sha = _criteria_v3_sha256_file(
        pkg / "Chem" / "MolStandardize" / "rdMolStandardize.so")
    cp = _rms.CleanupParameters()
    cp.maxTransforms = 1000
    cp.maxTautomers = 1000
    cp.tautomerRemoveSp3Stereo = True
    cp.tautomerRemoveBondStereo = True
    enumerator_default = _rms.TautomerEnumerator(cp)
    cp_keep = _rms.CleanupParameters()
    cp_keep.maxTransforms = 1000
    cp_keep.maxTautomers = 1000
    cp_keep.tautomerRemoveSp3Stereo = False
    cp_keep.tautomerRemoveBondStereo = True
    enumerator_keep = _rms.TautomerEnumerator(cp_keep)
    transforms_file = str(getattr(cp, "tautomerTransformsFile", "") or "")
    if transforms_file and Path(transforms_file).is_file():
        transforms_descriptor = (
            f"sha256:{_criteria_v3_sha256_file(Path(transforms_file))}"
            f" (path={transforms_file})")
    elif dylib_sha and so_sha:
        transforms_descriptor = (
            f"absent (RDKit {_rdBase.rdkitVersion} 数据嵌于 "
            "libRDKitMolStandardize; CleanupParameters."
            f"tautomerTransformsFile={transforms_file!r})")
    else:  # pragma: no cover —— 环境异常 fail-closed
        return {"available": False,
                "unavailable_reason": "transforms_fingerprint_unavailable",
                "environment": {}, "arms": {}, "dual_arm_diff": {},
                "carbonate_system": {}}
    environment = {
        "rdkit_version": _rdBase.rdkitVersion,
        "rdkit_build": _rdBase.rdkitBuild,
        "python": _sys.version.split()[0],
        "tautomerTransforms_file": transforms_descriptor,
        "libRDKitMolStandardize_sha256": dylib_sha,
        "rdMolStandardize_so_sha256": so_sha,
    }
    arm_a_default_params = {
        "source": "FROZEN_V3 / 来源分类脚本同参",
        "write_path": ("CleanupParameters() + 显式写 maxTransforms/"
                       "maxTautomers/tautomerRemoveSp3Stereo/"
                       "tautomerRemoveBondStereo"),
        "maxTransforms": enumerator_default.GetMaxTransforms(),
        "maxTautomers": enumerator_default.GetMaxTautomers(),
        "tautomerRemoveSp3Stereo_effective":
            enumerator_default.GetRemoveSp3Stereo(),
        "tautomerRemoveBondStereo_effective":
            enumerator_default.GetRemoveBondStereo(),
        "tautomerRemoveIsotopicHs_effective": cp.tautomerRemoveIsotopicHs,
        "tautomerReassignStereo_effective":
            enumerator_default.GetReassignStereo(),
        "maxRestarts_effective": cp.maxRestarts,
        "tautomerScoreVersion": str(
            enumerator_default.tautomerScoreVersion),
        "compare": "Canonicalize() -> Chem.MolToSmiles (canonical isomeric)",
    }
    arm_a_keep_params = dict(arm_a_default_params)
    arm_a_keep_params.update({
        "tautomerRemoveSp3Stereo_effective":
            enumerator_keep.GetRemoveSp3Stereo(),
        "tautomerRemoveBondStereo_effective":
            enumerator_keep.GetRemoveBondStereo(),
        "note": "候选主臂: removeSp3Stereo=False; removeBondStereo "
                "保持默认 true（未核范围）",
    })
    arm_b_uncharger_params = {
        "source": "FROZEN_V3 / 来源分类脚本同参（protonation OR 之一）",
        "api": "rdMolStandardize.Uncharger() 默认构造；逐组分施加后点号重接",
        "neutralize": "default (构造未显式传参; 本 RDKit build 无 getter "
                      "可 introspection)",
        "compare": "canonical isomeric SMILES（保留立体）",
    }
    arm_b_charge_parent_params = {
        "source": "FROZEN_V3（仅敏感性披露）",
        "api": "rdMolStandardize.ChargeParent(mol, params=None, "
               "skipStandardize=False)；逐组分后点号重接",
        "compare": "canonical isomeric SMILES（保留立体）",
    }
    params_by_arm = {
        CRITERIA_V3_TAUTOMER_ARM_DEFAULT: arm_a_default_params,
        CRITERIA_V3_TAUTOMER_ARM_STEREO_PRESERVING: arm_a_keep_params,
        CRITERIA_V3_PROTONATION_ARM_UNCHARGER: arm_b_uncharger_params,
        CRITERIA_V3_PROTONATION_ARM_CHARGE_PARENT:
            arm_b_charge_parent_params,
    }
    arms: dict[str, dict] = {}
    for arm in _CRITERIA_V3_ARM_ORDER:
        params = params_by_arm[arm]
        arms[arm] = {
            "params": dict(params),
            "param_sha256": _criteria_v3_canonical_fingerprint(
                {"env": environment, "params": params}),
        }
    # 双臂差异逐项 diff(A 轴两臂;R03)
    keys = sorted(set(arm_a_default_params) | set(arm_a_keep_params))
    dual_arm_diff = {
        key: {"default": arm_a_default_params.get(key),
              "stereo_preserving": arm_a_keep_params.get(key)}
        for key in keys
        if arm_a_default_params.get(key) != arm_a_keep_params.get(key)
    }
    # B-6 闭集指纹:集合定义 + 识别算子参数纳入批级指纹
    carbonate = _criteria_v3_carbonate_system_forms()
    return {
        "available": True,
        "unavailable_reason": None,
        "environment": environment,
        "arms": arms,
        "dual_arm_diff": dual_arm_diff,
        "carbonate_system": carbonate,
    }


@lru_cache(maxsize=1)
def _criteria_v3_carbonate_system_forms() -> dict:
    """B-6 闭集机读形态:三物种经 B-1 同算子归一后的 canonical SMILES。

    三物种(CO₂/HCO₃⁻/CO₃²⁻)经 Uncharger 默认算子归一后落回两规范形
    (CO₂ 与碳酸),即"含其仅质子化写法变异落回同集合者"(*机读登记*)。"""
    try:
        from rdkit import Chem as _Chem
        from rdkit.Chem.MolStandardize import rdMolStandardize as _rms
    except ImportError:  # pragma: no cover —— 环境异常 fail-closed
        return {"available": False, "species": [],
                "normalized_forms_sorted": [], "sha256": None}
    uncharger = _rms.Uncharger()
    forms: set[str] = set()
    for species in CRITERIA_V3_CARBONATE_SYSTEM_SPECIES:
        mol = _Chem.MolFromSmiles(species)
        if mol is None:  # pragma: no cover —— 常量自身不可解析
            return {"available": False, "species": [],
                    "normalized_forms_sorted": [], "sha256": None}
        forms.add(_Chem.MolToSmiles(uncharger.uncharge(mol)))
    return {
        "available": True,
        "species": list(CRITERIA_V3_CARBONATE_SYSTEM_SPECIES),
        "normalized_forms_sorted": sorted(forms),
        "sha256": _criteria_v3_sha256_text("\n".join(sorted(forms))),
    }


@lru_cache(maxsize=1)
def _criteria_v3_enumerators() -> dict:
    """A 轴两臂枚举器 + B 轴算子(fail-closed:不可用 ⇒ available False)。"""
    try:
        from rdkit.Chem.MolStandardize import rdMolStandardize as _rms
    except ImportError:  # pragma: no cover —— 环境异常 fail-closed
        return {"available": False}
    cp_default = _rms.CleanupParameters()
    cp_default.maxTransforms = 1000
    cp_default.maxTautomers = 1000
    cp_default.tautomerRemoveSp3Stereo = True
    cp_default.tautomerRemoveBondStereo = True
    cp_keep = _rms.CleanupParameters()
    cp_keep.maxTransforms = 1000
    cp_keep.maxTautomers = 1000
    cp_keep.tautomerRemoveSp3Stereo = False
    cp_keep.tautomerRemoveBondStereo = True
    return {
        "available": True,
        "tautomer_default": _rms.TautomerEnumerator(cp_default),
        "tautomer_stereo_preserving": _rms.TautomerEnumerator(cp_keep),
        "uncharger": _rms.Uncharger(),
        "charge_parent": _rms.ChargeParent,
    }


def _criteria_v3_arm_param_sha256(arm: str) -> str | None:
    registry = _criteria_v3_arm_registry()
    entry = (registry.get("arms") or {}).get(arm) or {}
    return entry.get("param_sha256")


def _criteria_v3_tautomer_canonical(smi: str,
                                    arm: str) -> tuple[str | None,
                                                      str | None]:
    """A 轴单侧归一(逐臂):Canonicalize → canonical isomeric SMILES。

    fail-closed:不可解析/算子异常/空结果 ⇒ (None, 机读原因)。"""
    from rdkit import Chem as _Chem, RDLogger as _RDLogger
    _RDLogger.DisableLog("rdApp.*")
    if not smi:
        return None, CRITERIA_V3_REASON_UNPARSEABLE
    mol = _Chem.MolFromSmiles(smi)
    if mol is None:
        return None, CRITERIA_V3_REASON_UNPARSEABLE
    engines = _criteria_v3_enumerators()
    if not engines.get("available"):  # pragma: no cover —— fail-closed
        return None, "tautomer_enumerator_unavailable"
    key = ("tautomer_default" if arm == CRITERIA_V3_TAUTOMER_ARM_DEFAULT
           else "tautomer_stereo_preserving")
    enumerator = engines.get(key)
    try:
        out = enumerator.Canonicalize(mol)
    except Exception as exc:  # noqa: BLE001 —— fail-closed
        return None, f"tautomer_operator_error:{type(exc).__name__}"
    if out is None:
        return None, CRITERIA_V3_REASON_EMPTY_TAUTOMER
    try:
        return _Chem.MolToSmiles(out), None
    except Exception as exc:  # noqa: BLE001 —— fail-closed
        return None, f"smiles_serialization_error:{type(exc).__name__}"


def _criteria_v3_protonation_side(smi: str,
                                  arm: str) -> tuple[str | None,
                                                    str | None]:
    """B 轴单侧归一(逐组分 → 点号重接 → canonical isomeric,保留立体)。

    fail-closed:任一组分不可解析/算子异常 ⇒ (None, 机读原因);
    不使用 cn_identity 立体盲口径(B-1)。"""
    from rdkit import Chem as _Chem, RDLogger as _RDLogger
    _RDLogger.DisableLog("rdApp.*")
    components = [c for c in str(smi or "").split(".") if c]
    if not components:
        return None, CRITERIA_V3_REASON_EMPTY_SIDE
    engines = _criteria_v3_enumerators()
    if not engines.get("available"):  # pragma: no cover —— fail-closed
        return None, f"{arm}_operator_unavailable"
    out: list[str] = []
    for component in components:
        mol = _Chem.MolFromSmiles(component)
        if mol is None:
            return None, CRITERIA_V3_REASON_UNPARSEABLE
        try:
            if arm == CRITERIA_V3_PROTONATION_ARM_UNCHARGER:
                normalized = engines["uncharger"].uncharge(mol)
            else:
                normalized = engines["charge_parent"](mol)
        except Exception as exc:  # noqa: BLE001 —— fail-closed
            return None, f"{arm}_operator_error:{type(exc).__name__}"
        if normalized is None:  # pragma: no cover —— fail-closed
            return None, f"{arm}_empty_result"
        out.append(_Chem.MolToSmiles(normalized))
    return ".".join(out), None


def _criteria_v3_carbonate_hits(canonical: str | None) -> dict:
    """单侧是否命中 B-6 闭集(与 B-1 同算子归一后的 canonical SMILES)。

    tri-state:命中 True / 未命中 False / 不可判定(该侧归一失败)
    None —— 禁伪填 absent(§B-6/R05 机读规则)。"""
    if canonical is None:
        return {"hit": None, "status": "unknown"}
    forms = set(_criteria_v3_carbonate_system_forms()[
        "normalized_forms_sorted"] or [])
    if not forms:  # pragma: no cover —— 环境异常 fail-closed
        return {"hit": None, "status": "unknown"}
    hit = canonical in forms
    return {"hit": hit, "status": "in_set" if hit else "not_in_set"}


def criteria_v3_normalized_identity_pair(ref_smi: str,
                                         pred_smi: str) -> dict:
    """逐配对 A/B 双轴披露(纯函数;档 A 只披露;fail-closed 无第三态)。

    返回机读披露(零结构串:
    仅布尔/臂名/来源/指纹/原因码/计数——配对本体的结构串不落披露):

    - ``original_match_status``:原状态(本轴只在 cn_only 配对适用);
    - ``tautomer``:双臂各自布尔(``normalized_identity_axis_default``
      / ``normalized_identity_axis_stereo_preserving``)+ 逐臂
      ``tautomer_arm`` / ``normalization_source`` /
      ``tautomer_param_sha256`` / 失败原因(A-6);
    - ``protonation``:Uncharger 臂(默认启用)+ ChargeParent 臂
      (并列敏感性);B-6 闭集命中 ⇒ 两侧均命中时逐对象排除并落
      ``carbonate_system_exclusion``;
    - ``single_attribution``:A→B 单归属(tautomer/protonation/none);
      ``double_satisfied``:双轴布尔(任臂)*均* 为真(披露,不静默吞);
    - ``strict_promotion``:恒 False(档 A;档 B 未解锁)。
    """
    registry = _criteria_v3_arm_registry()
    arms_meta = registry.get("arms") or {}
    tautomer: dict = {"arms": {}, "any_arm_granted": False,
                      "primary_arm": CRITERIA_V3_TAUTOMER_PRIMARY_ARM,
                      "strict_promotion": False}
    for arm in CRITERIA_V3_TAUTOMER_ARMS:
        ref_canonical, ref_reason = _criteria_v3_tautomer_canonical(
            ref_smi, arm)
        pred_canonical, pred_reason = _criteria_v3_tautomer_canonical(
            pred_smi, arm)
        granted = (ref_canonical is not None and pred_canonical is not None
                   and ref_canonical == pred_canonical)
        reason = ref_reason or pred_reason or None
        if granted:
            reason = None
        arm_row = {
            "tautomer_arm": arm,
            "normalization_source":
                CRITERIA_V3_NORMALIZATION_SOURCES[arm],
            "tautomer_param_sha256":
                (arms_meta.get(arm) or {}).get("param_sha256"),
            "normalized_identity_axis": granted,
            "reason": reason,
            "strict_eligible": False,
        }
        if arm == CRITERIA_V3_TAUTOMER_ARM_DEFAULT:
            arm_row["strict_eligible"] = \
                CRITERIA_V3_DEFAULT_ARM_STRICT_ELIGIBLE
            arm_row["strict_eligible_note"] = CRITERIA_V3_DEFAULT_ARM_NOTE
            arm_row["normalized_identity_axis_default"] = granted
        else:
            arm_row["tier_b_candidate"] = True
            arm_row["tier_b_status"] = CRITERIA_V3_TIER_B_STATUS
            arm_row["strict_eligible_note"] = CRITERIA_V3_PRIMARY_ARM_NOTE
            arm_row["normalized_identity_axis_stereo_preserving"] = granted
        tautomer["arms"][arm] = arm_row
        tautomer["any_arm_granted"] = tautomer["any_arm_granted"] or granted
    tautomer["normalized_identity_axis_default"] = tautomer["arms"][
        CRITERIA_V3_TAUTOMER_ARM_DEFAULT]["normalized_identity_axis"]
    tautomer["normalized_identity_axis_stereo_preserving"] = \
        tautomer["arms"][CRITERIA_V3_TAUTOMER_ARM_STEREO_PRESERVING][
            "normalized_identity_axis"]
    tautomer["any_arm_granted"] = (
        tautomer["normalized_identity_axis_default"]
        or tautomer["normalized_identity_axis_stereo_preserving"])
    tautomer["strict_promotion"] = False
    tautomer["strict_promotion_note"] = CRITERIA_V3_DISCLOSURE_ONLY_NOTE

    protonation: dict = {
        "arms": {},
        "enabled_arm": CRITERIA_V3_PROTONATION_ENABLED_ARM,
        "carbonate_system_exclusion": False,
        "exclusion_reason": None,
        "strict_promotion": False,
    }
    uncharger_canonicals: dict[str, str | None] = {}
    for arm in CRITERIA_V3_PROTONATION_ARMS:
        ref_canonical, ref_reason = _criteria_v3_protonation_side(
            ref_smi, arm)
        pred_canonical, pred_reason = _criteria_v3_protonation_side(
            pred_smi, arm)
        if arm == CRITERIA_V3_PROTONATION_ARM_UNCHARGER:
            uncharger_canonicals = {"ref": ref_canonical,
                                    "pred": pred_canonical}
        granted = (ref_canonical is not None and pred_canonical is not None
                   and ref_canonical == pred_canonical)
        reason = ref_reason or pred_reason or None
        if granted:
            reason = None
        arm_row = {
            "enabled":
                arm == CRITERIA_V3_PROTONATION_ENABLED_ARM,
            "sensitivity_only":
                arm == CRITERIA_V3_PROTONATION_ARM_CHARGE_PARENT,
            "normalization_source":
                CRITERIA_V3_NORMALIZATION_SOURCES[arm],
            "param_sha256": (arms_meta.get(arm) or {}).get("param_sha256"),
            "normalized_identity_axis": granted,
            "reason": reason,
        }
        arm_row["normalized_identity_axis_" + arm] = granted
        if arm == CRITERIA_V3_PROTONATION_ARM_CHARGE_PARENT:
            arm_row["note"] = CRITERIA_V3_CHARGE_PARENT_SENSITIVITY_NOTE
        protonation["arms"][arm] = arm_row
    # B-6 碳酸体系闭集(同一 Uncharger 归一 canonical 复用;tri-state,
    # 不可判定如实 unknown,禁伪填)
    ref_carbonate = _criteria_v3_carbonate_hits(uncharger_canonicals["ref"])
    pred_carbonate = _criteria_v3_carbonate_hits(
        uncharger_canonicals["pred"])
    carbonate_excluded = bool(ref_carbonate["hit"] is True
                              and pred_carbonate["hit"] is True)
    protonation["carbonate_system_exclusion"] = carbonate_excluded
    if ref_carbonate["hit"] is None or pred_carbonate["hit"] is None:
        carbonate_status = "unknown"
    elif carbonate_excluded:
        carbonate_status = "excluded"
    else:
        carbonate_status = "not_excluded"
    protonation["carbonate_system_check"] = {
        "reference_side": ref_carbonate["status"],
        "predicted_side": pred_carbonate["status"],
        "status": carbonate_status,
    }
    if carbonate_excluded:
        # 逐对象排除:两臂全覆盖(含敏感性臂),机读原因
        protonation["exclusion_reason"] = \
            CRITERIA_V3_CARBONATE_EXCLUSION_REASON
        for arm, arm_row in protonation["arms"].items():
            arm_row["normalized_identity_axis"] = False
            arm_row["normalized_identity_axis_" + arm] = False
            arm_row["reason"] = CRITERIA_V3_CARBONATE_EXCLUSION_REASON
    protonation["any_arm_granted"] = any(
        row["normalized_identity_axis"]
        for row in protonation["arms"].values())

    # 单归属 A→B(B-5):一条配对最多挂一个归一轴标签;双满足按 A 取先
    if tautomer["any_arm_granted"]:
        single_attribution = "tautomer"
    elif protonation["any_arm_granted"]:
        single_attribution = "protonation"
    else:
        single_attribution = "none"
    return {
        "original_match_status": "cn_only",
        "tautomer": tautomer,
        "protonation": protonation,
        "single_attribution": single_attribution,
        "double_satisfied": bool(tautomer["any_arm_granted"]
                                 and protonation["any_arm_granted"]),
        "strict_promotion": False,
        "strict_promotion_note": CRITERIA_V3_DISCLOSURE_ONLY_NOTE,
    }


def criteria_v3_aggregate_pair_blocks(pair_blocks: list[dict]) -> dict:
    """逐配对披露块 → 批级分列计数(档 A;单归属 + 双满足披露)。"""
    counts = {
        "pairs_total": len(pair_blocks),
        "tautomer_normalized_pairs_default": 0,
        "tautomer_normalized_pairs_stereo_preserving": 0,
        "protonation_normalized_pairs_uncharger": 0,
        "protonation_normalized_pairs_charge_parent": 0,
        "single_attribution_counts": {"tautomer": 0, "protonation": 0,
                                      "none": 0},
        "double_satisfied_pairs": 0,
        "carbonate_system_excluded_pairs": 0,
        "fail_closed_pairs": 0,
        "strict_promoted_pairs": 0,
    }
    for block in pair_blocks:
        tautomer = block.get("tautomer") or {}
        protonation = block.get("protonation") or {}
        t_arms = tautomer.get("arms") or {}
        b_arms = protonation.get("arms") or {}
        if (t_arms.get(CRITERIA_V3_TAUTOMER_ARM_DEFAULT) or {}).get(
                "normalized_identity_axis"):
            counts["tautomer_normalized_pairs_default"] += 1
        if (t_arms.get(
                CRITERIA_V3_TAUTOMER_ARM_STEREO_PRESERVING) or {}).get(
                "normalized_identity_axis"):
            counts["tautomer_normalized_pairs_stereo_preserving"] += 1
        if (b_arms.get(CRITERIA_V3_PROTONATION_ARM_UNCHARGER) or {}).get(
                "normalized_identity_axis"):
            counts["protonation_normalized_pairs_uncharger"] += 1
        if (b_arms.get(
                CRITERIA_V3_PROTONATION_ARM_CHARGE_PARENT) or {}).get(
                "normalized_identity_axis"):
            counts["protonation_normalized_pairs_charge_parent"] += 1
        attribution = str(block.get("single_attribution") or "none")
        assert attribution in CRITERIA_V3_PAIR_ATTRIBUTION_ORDER, \
            (f"ppv1-criteria-v3 单归属标签非法:{attribution!r}"
             f"(A->B 无第三态;允许 {CRITERIA_V3_PAIR_ATTRIBUTION_ORDER})")
        counts["single_attribution_counts"][attribution] += 1
        if block.get("double_satisfied"):
            counts["double_satisfied_pairs"] += 1
        if protonation.get("carbonate_system_exclusion"):
            counts["carbonate_system_excluded_pairs"] += 1
        if block.get("strict_promotion"):
            counts["strict_promoted_pairs"] += 1
        if _criteria_v3_pair_failed(block):
            counts["fail_closed_pairs"] += 1
    # 单归属断言:三标签计数之和 == 配对数(无第三态)
    assert sum(counts["single_attribution_counts"].values()) == \
        counts["pairs_total"], \
        "ppv1-criteria-v3 单归属违例:标签计数之和 != 配对数(无第三态)"
    assert counts["strict_promoted_pairs"] == 0, \
        ("ppv1-criteria-v3 档 A 违例:出现 strict 提升(跃升档 B 未解锁)"
         )
    return counts


def _criteria_v3_pair_failed(block: dict) -> bool:
    """配对是否存在 fail-closed 原因(不可解析/算子异常)。"""
    for axis in ("tautomer", "protonation"):
        for row in ((block.get(axis) or {}).get("arms") or {}).values():
            reason = str(row.get("reason") or "")
            if reason and reason != CRITERIA_V3_CARBONATE_EXCLUSION_REASON:
                return True
    return False


def _criteria_v3_node_disclosure(node_entry: dict,
                                 states: dict[str, dict],
                                 reference_smiles: str) -> dict:
    """节点级 V3 披露块(match_reference_nodes 内消费;档 A 只披露)。

    适用面(A-1):仅 ``structure_identity_scope == "strict_structure"``
    参考节点的 cn_only 配对;其余如实给 ``applicable=false`` 机读原因
    (N4 负控:S5A-01 封顶不得越过)。"""
    scope_permits_strict = node_entry.get("reference_identity_scope") == \
        "strict_structure"
    pair_state_ids = list(node_entry.get("cn_only_state_ids") or [])
    reason: str | None = None
    applicable = True
    if node_entry.get("match_status") == "reference_structure_unparseable":
        applicable, reason = False, "reference_structure_unparseable"
    elif not scope_permits_strict:
        applicable, reason = False, "identity_scope_cap"
    elif node_entry.get("match_status") != "cn_only":
        applicable, reason = False, "match_status_not_cn_only"
    elif not pair_state_ids:
        applicable, reason = False, "no_cn_only_pair"
    block = {
        "criteria_version": PPV1_CRITERIA_V3,
        "tier": CRITERIA_V3_TIER_DISCLOSURE_ONLY,
        "original_match_status": node_entry.get("match_status"),
        "reference_identity_scope":
            node_entry.get("reference_identity_scope"),
        "applicable": applicable,
        "not_applicable_reason": reason,
        "strict_promotion": False,
        "strict_promotion_note": CRITERIA_V3_DISCLOSURE_ONLY_NOTE,
        "tautomer_promoted_nodes": [],
        "tautomer_promoted_nodes_note": (
            "档 B 未解锁(D03)⇒ 本轮恒无;仅档 A 披露"),
        "axis_pairs": [],
        "axis_pair_counts": {},
    }
    if not applicable:
        block["axis_pair_counts"] = criteria_v3_aggregate_pair_blocks([])
        return block
    pairs: list[dict] = []
    for state_id in sorted(pair_state_ids):
        state = states.get(state_id) or {}
        pair_block = criteria_v3_normalized_identity_pair(
            reference_smiles, str(state.get("smiles_isomeric") or ""))
        pair_block = {"state_id": state_id, **pair_block}
        pairs.append(pair_block)
    block["axis_pairs"] = pairs
    block["axis_pair_counts"] = criteria_v3_aggregate_pair_blocks(pairs)
    return block


def _criteria_v3_batch_block(sample_results: list[dict]) -> dict:
    """批级 V3 汇总块(评测器输出;§8 承载面)。

    聚合所有样本的节点级披露块:分臂计数 + 单归属 + 双满足 +
    碳酸体系排除 + 恒空 ``tautomer_promoted_nodes`` + 参数指纹登记
    (失败题留分母,其节点块缺席 = 未评,不伪填)。"""
    node_blocks: list[dict] = []
    for sample in sample_results or []:
        for entry in sample.get("predicted_node_matches") or []:
            block = entry.get("criteria_v3_normalized_identity")
            if isinstance(block, dict):
                node_blocks.append(block)
    pairs = [pair for block in node_blocks
             for pair in block.get("axis_pairs") or []]
    counts = criteria_v3_aggregate_pair_blocks(pairs)
    promoted: list[dict] = []
    for block in node_blocks:
        promoted.extend(block.get("tautomer_promoted_nodes") or [])
    registry = _criteria_v3_arm_registry()
    assert not promoted, \
        "ppv1-criteria-v3 档 A 违例:tautomer_promoted_nodes 非空(档 B 未解锁)"
    return {
        "criteria_version": PPV1_CRITERIA_V3,
        "frozen_doc": PPV1_CRITERIA_V3_FROZEN_DOC,
        "tier": CRITERIA_V3_TIER_DISCLOSURE_ONLY,
        "tier_b_status": CRITERIA_V3_TIER_B_STATUS,
        "disclosure_only_note": CRITERIA_V3_DISCLOSURE_ONLY_NOTE,
        "measurement_correction_note": CRITERIA_V3_MEASUREMENT_NOTE,
        "strict_promotion": False,
        "hit_at_1_effect": "none",
        "tautomer_normalized_pairs_default":
            counts["tautomer_normalized_pairs_default"],
        "tautomer_normalized_pairs_stereo_preserving":
            counts["tautomer_normalized_pairs_stereo_preserving"],
        "protonation_normalized_pairs_uncharger":
            counts["protonation_normalized_pairs_uncharger"],
        "protonation_normalized_pairs_charge_parent":
            counts["protonation_normalized_pairs_charge_parent"],
        "single_attribution_counts": counts["single_attribution_counts"],
        "double_satisfied_pairs": counts["double_satisfied_pairs"],
        "carbonate_system_excluded_pairs":
            counts["carbonate_system_excluded_pairs"],
        "carbonate_system_exclusion_reason":
            CRITERIA_V3_CARBONATE_EXCLUSION_REASON,
        "carbonate_system_set": CRITERIA_V3_CARBONATE_SET_NOTE,
        "carbonate_system_sha256": (
            registry.get("carbonate_system") or {}).get("sha256"),
        "axis_pairs_total": counts["pairs_total"],
        "fail_closed_pairs": counts["fail_closed_pairs"],
        "axis_nodes_total": len(node_blocks),
        "axis_nodes_not_applicable": sum(
            1 for block in node_blocks if not block.get("applicable")),
        "tautomer_promoted_nodes": promoted,
        "param_registry": {
            "environment": registry.get("environment"),
            "arms": {arm: (registry.get("arms") or {}).get(arm)
                     for arm in _CRITERIA_V3_ARM_ORDER},
            "dual_arm_diff": registry.get("dual_arm_diff"),
        },
        "aromatic_repr_note": CRITERIA_V3_AROMATIC_REPR_NOTE,
        "single_batch_note": CRITERIA_V3_SINGLE_BATCH_NOTE,
        "exemption_subsumption_note": (
            "V3 承载 V2 判分语义(参与物集合比较豁免路径不变;N3/N7 "
            "正交性断言:V2 tier 计数同 payload 与 v2 逐位一致)"),
        "dual_caliber_note": (
            "ppv1-criteria-v1(豁免关)恒为 headline;本块为 v3 口径"
            "敏感性披露,post-hoc;旧批零回写;判分侧互变归一不进 "
            "strict/hit@1"),
    }


def _criteria_state_cn(states: dict[str, dict], state_id: str) -> str | None:
    """状态 cn 身份:导出行声明值优先,缺失时同源工具重推导
    (与 match_reference_nodes 同一事实源);不可解析 ⇒ None。"""
    row = states.get(state_id)
    if not isinstance(row, dict):
        return None
    declared = str(row.get("cn_identity") or "")
    if declared:
        return declared
    try:
        return cn_identity(str(row.get("smiles_isomeric") or ""))
    except Exception:  # noqa: BLE001 —— 不可解析按 None(fail-closed)
        return None


def _criteria_element_count(smiles: str, element: str) -> int | None:
    """元素原子计数(补证脚本 elem_sig 的 O/P 轴;解析失败 ⇒ None)。"""
    if not smiles:
        return None
    try:
        from rdkit import Chem as _Chem, RDLogger as _RDLogger
    except ImportError:  # pragma: no cover —— 环境异常 fail-closed
        return None
    _RDLogger.DisableLog("rdApp.*")
    mol = _Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    return sum(1 for a in mol.GetAtoms() if a.GetSymbol() == element)


# pred1 声明链状态(v2 消费契约,预注册 §二.1;生成侧发射器未装配属
# known gap —— 链缺席/悬空/不可解析一律 unknown = 不豁免)
_CRITERIA_V2_DECLARATION_KEY = "record_equation"
_CRITERIA_V2_DECL_RESOLVED = "resolved"
_CRITERIA_V2_DECL_NO_CHAIN = "no_chain"
_CRITERIA_V2_DECL_UNRESOLVED = "unresolved"
_CRITERIA_V2_DECL_UNPARSEABLE = "unparseable"


def _criteria_declaration_sides(payload: dict, hypothesis_id: str) -> tuple[
        dict[str, set], dict[str, set], str]:
    """pred1 执法链:event→hypothesis→provenance_refs→
    provenance_records 行 payload 的 ``record_equation`` 声明。

    消费契约(判分侧定义,预注册 §二.1)::record_equation = 
    ``{"reactants": [{"smiles": str, "role": str?}…],
    "products": […]}``;逐条目 cn_identity。声明条目 role 缺省 =
    通配(记录方程通常无角色信息);带 role 时按身份+侧+角色绑定。

    返回 (反应物声明 {cn: roles}, 产物声明 {cn: roles}, status):
    status ∈ resolved | no_chain(无 refs)| unresolved(refs 存在但
    无可解析方程)| unparseable(任一段不可解析 —— 与补证脚本
    bad>0 ⇒ unknown 同口径,fail-closed)。"""
    import json as _json
    react_declared: dict[str, set] = {}
    prod_declared: dict[str, set] = {}
    hyp = _hypothesis_payloads(payload).get(str(hypothesis_id or "")) or {}
    refs = [str(x) for x in hyp.get("provenance_refs") or []]
    if not refs:
        return react_declared, prod_declared, _CRITERIA_V2_DECL_NO_CHAIN
    rows: dict[str, dict] = {}
    for row in payload.get("provenance_records") or []:
        body = row.get("payload")
        if isinstance(body, str):
            try:
                body = _json.loads(body)
            except (ValueError, TypeError):
                body = None
        if isinstance(body, dict):
            rows[str(row.get("record_id"))] = body
    resolved = False
    unparseable = False
    for ref in refs:
        body = rows.get(ref)
        if body is None:
            unparseable = True  # 悬空引用:链不可判(fail-closed)
            continue
        equation = body.get(_CRITERIA_V2_DECLARATION_KEY)
        if not isinstance(equation, dict):
            unparseable = True
            continue
        side_tables = (("reactants", react_declared),
                       ("products", prod_declared))
        ok = True
        for side_key, table in side_tables:
            entries = equation.get(side_key)
            if not isinstance(entries, list):
                ok = False
                break
            for entry in entries:
                if not isinstance(entry, dict):
                    ok = False
                    break
                smiles = str(entry.get("smiles") or "")
                role = entry.get("role")
                cn = cn_identity(smiles) if smiles else None
                if cn is None:
                    ok = False
                    break
                table.setdefault(cn, set()).add(
                    None if role in (None, "") else str(role))
            if not ok:
                break
        if ok:
            resolved = True
        else:
            unparseable = True
    if unparseable:
        return react_declared, prod_declared, _CRITERIA_V2_DECL_UNPARSEABLE
    if resolved:
        return react_declared, prod_declared, _CRITERIA_V2_DECL_RESOLVED
    return react_declared, prod_declared, _CRITERIA_V2_DECL_UNRESOLVED


def _pred1_record_declared(declared: dict[str, set], status: str,
                           cn: str | None, role) -> str:
    """①记录已声明(身份+侧+角色绑定;判不了=unknown,fail-closed)。"""
    if status != _CRITERIA_V2_DECL_RESOLVED:
        return "unknown"
    roles = declared.get(cn) if cn is not None else None
    if roles is None:
        return "false"
    if None in roles or (role is not None and str(role) in roles):
        return "true"
    return "false"  # 已声明但角色不符 ⇒ 该身份+侧+角色未声明


def evaluate_participant_exemption(payload: dict, event_body: dict,
                                   states: dict[str, dict], *,
                                   hypothesis_id: str,
                                   from_states: set[str],
                                   to_states: set[str]) -> dict:
    """ppv1-criteria-v2 三谓词评审(纯函数;测试/重算对照可复用)。

    对单个事件按预注册 §二/§三执行:逐 extra 实例(身份+侧+角色)
    单归属恰一个 tier;事件级元素账照抄补证脚本口径(P/O 计数级,
    "无中生水"拦截);**不完备豁免(任一 extras 非 v1_exempt)⇒
    维持 superset/partial**;partial_subset 形态不适用(缺物种豁免
    救不了,eligible=False)。

    返回::

        {"eligible": bool,           # superset 形态且存在 extras
         "all_exempt": bool,         # 全部 extras v1_exempt(可升 exact)
         "declaration_status": str,  # pred1 声明链状态(仅 eligible)
         "element_accounts": dict|None,  # P/O 三账(仅 eligible)
         "occurrences": [            # 逐实例(确定性排序;单归属)
             {"state_ref", "side", "role", "exempt_family",
              "identity_sha256_16"|None, "tier",
              "pred1_record_declared", "pred2_element_traceable",
              "pred3_cn_identity_member"}…],
         "exempted_participants": […],  # 披露子集(仅 v1_exempt 实例;
                                         # 身份仅披露族标签+版本化哈希,
                                         # 零结构外带)}
    """
    idents = _CRITERIA_V2_IDENTITIES
    participants = [p for p in (event_body or {}).get("participants") or []
                    if isinstance(p, dict)]
    reactants = {str(p.get("state_ref")) for p in participants
                 if str(p.get("side")) == "reactant"}
    products = {str(p.get("state_ref")) for p in participants
                if str(p.get("side")) == "product"}
    base = {
        "eligible": False, "all_exempt": False,
        "declaration_status": None, "element_accounts": None,
        "occurrences": [], "exempted_participants": [],
    }
    if not (from_states <= reactants and to_states <= products):
        return base  # 非 superset 形态(含 partial_subset):豁免不适用
    r_extra = sorted(reactants - from_states)
    p_extra = sorted(products - to_states)
    if not r_extra and not p_extra:
        return base  # 已 exact,豁免评审不适用
    # ---- pred1 声明链(事件→假设→provenance 回溯;一次解析双侧共用)
    # hypothesis_id 取自事件行顶层(导出行结构权威位,与匹配引擎的
    # hypothesis 反查同一来源,不另立判据) ----
    react_declared, prod_declared, decl_status = \
        _criteria_declaration_sides(payload, hypothesis_id)
    # ---- 事件级元素账(照抄补证脚本口径;O/P 计数级) ----
    # 非豁免侧 = 该侧参与物 cn 不在该侧豁免集(供给);豁免簿记需求 =
    # 该侧 extras 中落豁免集者的 O/P 合计。任一涉及状态不可解析 ⇒
    # 账 unknown(fail-closed,不造数)。
    account_unknown = False

    def _elem_total(state_ids: list[str], element: str) -> int | None:
        nonlocal account_unknown
        total = 0
        for sid in state_ids:
            row = states.get(sid) or {}
            smiles = str(row.get("smiles_isomeric") or "")
            n = _criteria_element_count(smiles, element)
            if n is None:
                account_unknown = True
                return None
            total += n
        return total

    react_nonexempt = [s for s in sorted(reactants)
                       if _criteria_state_cn(states, s)
                       not in idents["reactant"]]
    prod_nonexempt = [s for s in sorted(products)
                      if _criteria_state_cn(states, s)
                      not in idents["product"]]
    p_in = _elem_total(react_nonexempt, "P")
    o_in = _elem_total(react_nonexempt, "O")
    o_out = _elem_total(prod_nonexempt, "O")
    o_book_react = _elem_total(
        [s for s in r_extra
         if _criteria_state_cn(states, s) in idents["reactant"]], "O")
    o_book_prod = _elem_total(
        [s for s in p_extra
         if _criteria_state_cn(states, s) in idents["product"]], "O")
    p_book_prod = _elem_total(
        [s for s in p_extra
         if _criteria_state_cn(states, s) in idents["product"]], "P")
    if account_unknown:
        p_account = o_account_prod = o_account_react = "unknown"
    else:
        p_account = ("not_applicable" if p_book_prod == 0 else
                     ("pass" if p_in >= p_book_prod else "fail"))
        o_account_prod = ("not_applicable" if o_book_prod == 0 else
                          ("pass" if o_in >= o_book_prod else "fail"))
        o_account_react = ("not_applicable" if o_book_react == 0 else
                           ("pass" if o_out - o_in <= o_book_react
                            else "fail"))
    element_accounts = {
        "P": p_account, "O_product_side": o_account_prod,
        "O_reactant_side": o_account_react,
        "P_supply_nonexempt_react": p_in,
        "O_supply_nonexempt_react": o_in,
        "O_products_nonexempt": o_out,
        "O_demand_exempt_react_extras": o_book_react,
        "O_demand_exempt_prod_extras": o_book_prod,
        "P_demand_exempt_prod_extras": p_book_prod,
        "counting_basis": ("计数级追溯(供给≥需求),不证明键级机制来源;"
                           "照抄 CS2c 补证脚本口径;unknown=fail-closed"),
    }

    # ---- 逐实例三谓词 + 单归属 tier(身份+侧+角色;确定性排序) ----
    occurrences: list[dict] = []
    seen_keys: set[tuple] = set()
    ordered = sorted(participants,
                     key=lambda p: (str(p.get("state_ref")),
                                    str(p.get("side")),
                                    str(p.get("role"))))
    for p in ordered:
        state_ref = str(p.get("state_ref"))
        side = str(p.get("side"))
        role = p.get("role")
        role_key = None if role in (None, "") else str(role)
        if side not in ("reactant", "product"):
            continue  # 非 reactant/product 侧参与物不进集合比较轴
        if side == "reactant" and state_ref not in r_extra:
            continue
        if side == "product" and state_ref not in p_extra:
            continue
        key = (state_ref, side, role_key)
        if key in seen_keys:
            continue  # 同(身份+侧+角色)重复条目按单实例评审
        seen_keys.add(key)
        cn = _criteria_state_cn(states, state_ref)
        family = idents["family_by_cn"].get(cn)
        permitted = (idents["product"] if side == "product"
                     else idents["reactant"])
        member = cn is not None and cn in permitted
        if not member:
            # 方向不许可/身份不在豁免集 ⇒ 完备二分右侧,谓词不评审
            occurrences.append({
                "state_ref": state_ref, "side": side, "role": role_key,
                "exempt_family": None, "identity_sha256_16": None,
                "tier": CRITERIA_TIER_NOT_EXEMPT,
                "pred1_record_declared": None,
                "pred2_element_traceable": None,
                "pred3_cn_identity_member": False,
            })
            continue
        pred1 = _pred1_record_declared(
            react_declared if side == "reactant" else prod_declared,
            decl_status, cn, role_key)
        if family == "v1:H+":
            # H⁺ 无 O/P 涉及(预注册 §二.2:按"豁免实例涉及的 O/P"语义
            # not_applicable 记过;与补证脚本 inst_pass 字面差异已披露,
            # 本批 H⁺ 实例 0)
            pred2 = "not_applicable"
        elif side == "product":
            pred2 = ("pass" if p_account != "fail"
                     and o_account_prod == "pass" else "fail")
        else:
            pred2 = ("pass" if o_account_react == "pass" else "fail")
        pred3 = True  # cn ∈ 该侧豁免集即成员(判定键同源)
        tier = (CRITERIA_TIER_V1_EXEMPT
                if pred1 == "true" and pred2 in ("pass", "not_applicable")
                and pred3 else CRITERIA_TIER_NOT_EXEMPT)
        occurrences.append({
            "state_ref": state_ref, "side": side, "role": role_key,
            "exempt_family": family,
            "identity_sha256_16": idents["sha256_16_by_cn"].get(cn),
            "tier": tier,
            "pred1_record_declared": pred1,
            "pred2_element_traceable": pred2,
            "pred3_cn_identity_member": pred3,
        })
    # ---- 单归属断言:每实例恰一个合法 tier(结构性保证 + 显式断言) ----
    assert len(occurrences) == len(seen_keys), \
        "ppv1-criteria-v2 单归属违例:实例键去重后数量不一致"
    assert all(o["tier"] in CRITERIA_TIERS and
               sum(1 for t in CRITERIA_TIERS if t == o["tier"]) == 1
               for o in occurrences), \
        "ppv1-criteria-v2 单归属违例:tier 非法或缺标签"
    all_exempt = bool(occurrences) and all(
        o["tier"] == CRITERIA_TIER_V1_EXEMPT for o in occurrences) and \
        all(a in ("pass", "not_applicable")
            for a in (p_account, o_account_prod, o_account_react))
    exempted = [
        {k: o[k] for k in ("state_ref", "side", "role", "exempt_family",
                           "identity_sha256_16", "tier",
                           "pred1_record_declared",
                           "pred2_element_traceable",
                           "pred3_cn_identity_member")}
        for o in occurrences if o["tier"] == CRITERIA_TIER_V1_EXEMPT]
    return {
        "eligible": True,
        "all_exempt": all_exempt,
        "declaration_status": decl_status,
        "element_accounts": element_accounts,
        "occurrences": occurrences,
        "exempted_participants": exempted if all_exempt else [],
    }


# ---------------------------------------------------------------- 匹配引擎


def _export_states(payload: dict) -> dict[str, dict]:
    """导出 states 行 → {state_id: {smiles_isomeric, cn_identity, ...}}。"""
    out: dict[str, dict] = {}
    for row in payload.get("states") or []:
        state_id = str(row.get("state_id"))
        body = row.get("payload") or {}
        if isinstance(body, str):
            import json as _json
            try:
                body = _json.loads(body)
            except (ValueError, TypeError):
                body = {}
        out[state_id] = {
            "smiles_isomeric": str(body.get("smiles_isomeric") or ""),
            "cn_identity": str(body.get("cn_identity") or ""),
        }
    return out


def _event_participants(event_row: dict) -> list[dict]:
    body = event_row.get("payload")
    if isinstance(body, str):
        import json as _json
        try:
            body = _json.loads(body)
        except (ValueError, TypeError):
            body = {}
    return [p for p in (body or {}).get("participants") or []
            if isinstance(p, dict)]


def _event_payload_body(event_row: dict) -> dict:
    """事件行 payload 解析为 dict(ppv1-criteria-v2 评审消费;
    与 _event_participants 同一解析语义,不另立判据)。"""
    body = event_row.get("payload")
    if isinstance(body, str):
        import json as _json
        try:
            body = _json.loads(body)
        except (ValueError, TypeError):
            body = {}
    return body or {}


def _hypothesis_payloads(payload: dict) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for row in payload.get("hypotheses") or []:
        body = row.get("payload")
        if isinstance(body, str):
            import json as _json
            try:
                body = _json.loads(body)
            except (ValueError, TypeError):
                body = {}
        out[str(row.get("hypothesis_id"))] = body or {}
    return out


def _criteria_v4_edge_product_hit(edge: dict,
                                  nodes_by_id: dict[str, dict],
                                  payload: dict | None,
                                  legacy_match_status: str | None = None
                                  ) -> dict:
    """单参考边的 ppv1-criteria-v4 判定块(§1/§2/§3;纯函数)。

    - **目标集合 P** 只取该参考边产物侧 ``principal_product`` 角色
      节点(§2.5;不以其它 from/to 节点或全部节点替换);底物 S 取
      from 侧 ``root`` 角色节点(无 root 角色时回退全部 from 节点,
      机读披露 substrate_node_ids);
    - **合法事件(§2)**:同 run(事件 run_id 与 payload run_id 一致)、
      同受评步骤(``step_scope`` 与参考边一致)、已提交(payload
      ``events`` 即提交事件集合)、两侧参与物可解析(状态在场且
      ``smiles_isomeric`` 非空)、参考侧角色/侧别一致(此处只取
      principal_product 产物侧节点);
    - **同一事件判定(§1)**:S ∈ R_E 且 P ⊆ T_E;禁止跨事件拼答案
      (逐事件累加,不跨事件并集);
    - **身份函数**:``strict_identity_of`` 与 v2 节点匹配同一函数、
      一字不改;输出只落事件 id / 节点 id / 身份 sha256_16,零 SMILES;
    - 参考目标为空/不可解析/身份许可范围不足 ⇒ ``not_evaluable``
      (``unmatched_reference_invalid``;不真空通过、不称化学真错);
    - **桶与既有 coverage 轴的关系(§3 + 保留原 coverage 事实)**:
      ``product_hit_partial`` 只在既有 coverage 轴已判为
      ``matched_participant_coverage_partial`` 的边上成立(参考边
      两侧声明均可评、事件参与物覆盖不足);既有轴为
      ``unmatched_required_node_uncovered`` 的题(声明必要节点无严格
      命中)按 ``unmatched_product_mismatch`` 计 —— 它们的
      「部分主产物命中」另以 ``product_hit_partial_v4_sense`` /
      ``product_hit_partial_outside_legacy_partial`` 如实披露,不改桶。
      (预注册 §3 字面 trigger 与本批 §9 读数 2/140 的差异见交付报告
      §5;此处选择与冻结读数一致的轴归属,并零信息损失披露另一读数。)
    """
    edge_id = str(edge.get("edge_id"))
    from_ids = [str(x) for x in edge.get("from_node_ids") or []]
    to_ids = [str(x) for x in edge.get("to_node_ids") or []]
    role_by_id = {
        nid: str((nodes_by_id.get(nid) or {}).get("role") or "")
        for nid in set(from_ids) | set(to_ids)}
    substrate_ids = [nid for nid in from_ids
                     if role_by_id.get(nid) == "root"] or list(from_ids)
    principal_ids = [nid for nid in to_ids
                     if role_by_id.get(nid) == "principal_product"]
    reason: str | None = None
    if not substrate_ids or not principal_ids:
        reason = CRITERIA_V4_REFERENCE_TARGET_EMPTY
    elif any(nid not in nodes_by_id
             for nid in substrate_ids + principal_ids):
        reason = CRITERIA_V4_REFERENCE_NODE_MISSING
    elif any(str((nodes_by_id.get(nid) or {}).get(
            "structure_identity_scope") or "") != "strict_structure"
            for nid in substrate_ids + principal_ids):
        # S5A-01 许可范围不足 ⇒ 严格身份不可授(§3 reference_invalid)
        reason = CRITERIA_V4_REFERENCE_SCOPE_INSUFFICIENT
    identity_by_node: dict[str, str] = {}
    if reason is None:
        if strict_identity_of is None:  # pragma: no cover —— 环境异常
            reason = CRITERIA_V4_REFERENCE_UNPARSEABLE
        else:
            try:
                for nid in substrate_ids + principal_ids:
                    identity_by_node[nid] = strict_identity_of(
                        str((nodes_by_id[nid] or {}).get(
                            "structure_smiles")))
            except ChemicalStateError:
                identity_by_node = {}
                reason = CRITERIA_V4_REFERENCE_UNPARSEABLE
    substrate_identities = {identity_by_node[nid]
                            for nid in substrate_ids
                            if nid in identity_by_node}
    principal_identities = {identity_by_node[nid]
                            for nid in principal_ids
                            if nid in identity_by_node}
    if reason is None and (not substrate_identities
                           or not principal_identities):
        reason = CRITERIA_V4_REFERENCE_TARGET_EMPTY
    states = _export_states(payload or {})
    hypotheses = _hypothesis_payloads(payload or {})
    ref_scope = str(edge.get("step_scope") or "unknown")
    payload_run_id = str((payload or {}).get("run_id") or "")
    events = sorted((payload or {}).get("events") or [],
                    key=lambda e: str(e.get("event_id")))
    eligible = 0
    hit_events: list[str] = []
    partial_events: list[str] = []
    ineligible_reasons: dict[str, int] = {}
    event_rows: list[dict] = []
    for event in events:
        event_id = str(event.get("event_id") or "")
        row: dict = {"event_id": event_id}
        blocked: str | None = None
        if not event_id:
            blocked = "missing_event_id"
        elif payload_run_id and \
                str(event.get("run_id") or "") != payload_run_id:
            # 同题同 run(§2.1):payload run_id 已知时事件 run_id 必须
            # 逐字相同;事件缺 run_id 也按不合法处理(不静默放行)
            blocked = "run_id_mismatch"
        if blocked is None:
            hypothesis = hypotheses.get(
                str(event.get("hypothesis_id"))) or {}
            event_scope = str(hypothesis.get("step_scope") or "unknown")
            row["event_step_scope"] = event_scope
            row["reference_step_scope"] = ref_scope
            if event_scope != ref_scope:
                blocked = "step_scope_mismatch"
        participants = _event_participants(event) if blocked is None else []
        if blocked is None:
            refs = [str(p.get("state_ref") or "") for p in participants]
            if any(not ref or ref not in states
                   or not str(states[ref].get("smiles_isomeric") or "")
                   for ref in refs):
                blocked = "participant_unparseable"
        reactant_ids: set[str] = set()
        product_ids: set[str] = set()
        if blocked is None:
            if any(str(p.get("side")) not in ("reactant", "product")
                   for p in participants):
                blocked = "participant_side_unknown"
            else:
                reactant_ids = {
                    str(states[str(p.get("state_ref"))]["smiles_isomeric"])
                    for p in participants
                    if str(p.get("side")) == "reactant"}
                product_ids = {
                    str(states[str(p.get("state_ref"))]["smiles_isomeric"])
                    for p in participants
                    if str(p.get("side")) == "product"}
                if not reactant_ids or not product_ids:
                    blocked = "participant_side_empty"
        row["eligible"] = blocked is None
        if blocked is not None:
            row["ineligible_reason"] = blocked
            ineligible_reasons[blocked] = ineligible_reasons.get(
                blocked, 0) + 1
            event_rows.append(row)
            continue
        eligible += 1
        substrate_ok = bool(substrate_identities & reactant_ids)
        matched_principal = principal_identities & product_ids
        full_hit = bool(substrate_ok and principal_identities
                        and principal_identities <= product_ids)
        row.update({
            "substrate_identity_in_reactants": substrate_ok,
            "principal_products_total": len(principal_identities),
            "principal_products_matched": len(matched_principal),
            "matched_principal_identity_sha256_16": sorted(
                _criteria_v4_identity_sha256_16(identity)
                for identity in matched_principal),
            "matched_product_hit": full_hit,
        })
        if full_hit:
            hit_events.append(event_id)
        elif substrate_ok and matched_principal and \
                len(principal_identities) >= 2:
            # §3 product_hit_partial:无事件满足全部主产物,但存在合法
            # 事件命中部分主产物(多主产物题专用;不记为命中)
            partial_events.append(event_id)
        event_rows.append(row)
    if reason is not None:
        bucket = CRITERIA_V4_BUCKET_REFERENCE_INVALID
    elif hit_events:
        bucket = CRITERIA_V4_BUCKET_MATCHED
    elif legacy_match_status == \
            "matched_participant_coverage_partial":
        # 既有 coverage 轴已判 partial(参考边两侧可评、事件覆盖不足)
        # 且 v4 未命中 ⇒ product_hit_partial(§3;与 §9 读数 2 一致)
        bucket = CRITERIA_V4_BUCKET_PARTIAL
    elif eligible == 0:
        bucket = CRITERIA_V4_BUCKET_NO_EVENT
    else:
        bucket = CRITERIA_V4_BUCKET_PRODUCT_MISMATCH
    return {
        "criteria_version": PPV1_CRITERIA_V4,
        "edge_id": edge_id,
        "metric_name": CRITERIA_V4_METRIC_NAME,
        "hit_mode_scope": CRITERIA_V4_HIT_MODE_SCOPE,
        "reference_status": (CRITERIA_V4_REFERENCE_EVALUABLE
                             if reason is None else "not_evaluable"),
        "reference_invalid_reason": reason,
        "substrate_node_ids": substrate_ids,
        "principal_product_node_ids": principal_ids,
        "substrate_identity_sha256_16": sorted(
            _criteria_v4_identity_sha256_16(identity)
            for identity in substrate_identities),
        "principal_product_identity_sha256_16": sorted(
            _criteria_v4_identity_sha256_16(identity)
            for identity in principal_identities),
        "eligible_event_count": eligible,
        "event_count": len(events),
        "matched_product_hit": bool(hit_events),
        "product_hit_partial": bucket == CRITERIA_V4_BUCKET_PARTIAL,
        "product_hit_partial_v4_sense": bool(
            partial_events and not hit_events),
        "product_hit_partial_outside_legacy_partial": bool(
            partial_events and not hit_events
            and bucket != CRITERIA_V4_BUCKET_PARTIAL),
        "product_hit_events": sorted(hit_events),
        "partial_product_hit_events": sorted(partial_events),
        "bucket": bucket,
        "legacy_match_status": legacy_match_status,
        "ineligible_event_reasons": dict(sorted(
            ineligible_reasons.items())),
        "events": event_rows,
        "coverage_facts_preserved": True,
        "coverage_facts_note": CRITERIA_V4_COVERAGE_PRESERVATION_NOTE,
    }


def _criteria_v4_sample_block(edge_blocks: list[dict]) -> dict:
    """样本级 v4 汇总(逐边块 → 题级桶;§3 互斥桶,分母不剔题)。

    题级优先序:任一参考边命中 ⇒ ``matched_product_hit``;否则任一
    边 partial ⇒ ``product_hit_partial``;否则全部边参考无效 ⇒
    ``unmatched_reference_invalid``;否则有合法事件 ⇒
    ``unmatched_product_mismatch``;否则 ``unmatched_no_event``。
    """
    blocks: list[dict] = []
    for block in edge_blocks or []:
        if not isinstance(block, dict):
            continue
        # 边条目(含嵌套 ``criteria_v4``)与裸判定块两种输入都接受
        nested = block.get("criteria_v4")
        blocks.append(nested if isinstance(nested, dict) else block)
    hit_events = sorted({str(event) for block in blocks
                         for event in block.get("product_hit_events") or []})
    partial_events = sorted({str(event) for block in blocks
                             for event in
                             block.get("partial_product_hit_events") or []})
    reasons: dict[str, int] = {}
    for block in blocks:
        reason = block.get("reference_invalid_reason")
        if reason:
            reasons[str(reason)] = reasons.get(str(reason), 0) + 1
    eligible = sum(int(block.get("eligible_event_count") or 0)
                   for block in blocks)
    hit = any(bool(block.get("matched_product_hit")) for block in blocks)
    partial = any(block.get("bucket") == CRITERIA_V4_BUCKET_PARTIAL
                  for block in blocks)
    if hit:
        bucket = CRITERIA_V4_BUCKET_MATCHED
    elif partial:
        bucket = CRITERIA_V4_BUCKET_PARTIAL
    elif blocks and all(
            block.get("bucket") == CRITERIA_V4_BUCKET_REFERENCE_INVALID
            for block in blocks):
        bucket = CRITERIA_V4_BUCKET_REFERENCE_INVALID
    elif eligible:
        bucket = CRITERIA_V4_BUCKET_PRODUCT_MISMATCH
    else:
        bucket = CRITERIA_V4_BUCKET_NO_EVENT
    return {
        "criteria_version": PPV1_CRITERIA_V4,
        "metric_name": CRITERIA_V4_METRIC_NAME,
        "hit_mode_scope": CRITERIA_V4_HIT_MODE_SCOPE,
        "preregistration_doc": PPV1_CRITERIA_V4_PREREG_DOC,
        "matched_product_hit": hit,
        "product_hit_partial": partial,
        "product_hit_partial_v4_sense": bool(
            partial_events and not hit),
        "product_hit_partial_outside_legacy_partial": bool(
            partial_events and not hit
            and bucket != CRITERIA_V4_BUCKET_PARTIAL),
        "product_hit_events": hit_events,
        "partial_product_hit_events": partial_events,
        "bucket": bucket,
        "eligible_event_count": eligible,
        "per_edge_bucket": {
            str(block.get("edge_id")): str(block.get("bucket"))
            for block in blocks},
        "reference_invalid_reasons": dict(sorted(reasons.items())),
        "coverage_facts_preserved": True,
        "coverage_facts_note": CRITERIA_V4_COVERAGE_PRESERVATION_NOTE,
        "metric_name_discipline_note": CRITERIA_V4_METRIC_DISCIPLINE_NOTE,
    }


def _criteria_v4_batch_block(sample_results: list[dict]) -> dict:
    """批级 v4 汇总(§3 桶 + §4 豁免旁路披露 + 旧桶分列)。

    分母 = 样本数(失败/无效题留分母);逐题恰一 v4 桶,桶和 = 分母。
    旧 ``match_status`` 桶作为独立披露块并列(不得与本指标同名)。
    """
    counts = {bucket: 0 for bucket in CRITERIA_V4_BUCKETS}
    per_sample: dict[str, str] = {}
    reasons: dict[str, int] = {}
    legacy: dict[str, int] = {}
    hit_events_total = 0
    partial_v4_sense = 0
    partial_outside_legacy = 0
    for sample in sample_results or []:
        block = sample.get("criteria_v4") or {}
        bucket = str(block.get("bucket") or CRITERIA_V4_BUCKET_NO_EVENT)
        if bucket not in counts:
            bucket = CRITERIA_V4_BUCKET_NO_EVENT
        counts[bucket] += 1
        per_sample[str(sample.get("sample_id"))] = bucket
        hit_events_total += len(block.get("product_hit_events") or [])
        if block.get("product_hit_partial_v4_sense"):
            partial_v4_sense += 1
        if block.get("product_hit_partial_outside_legacy_partial"):
            partial_outside_legacy += 1
        for reason, n in (block.get("reference_invalid_reasons")
                          or {}).items():
            reasons[str(reason)] = reasons.get(str(reason), 0) + int(n)
        edges = sample.get("predicted_edge_matches") or []
        legacy_status = (str(edges[0].get("match_status")) if edges
                         else "not_evaluated_no_edges")
        legacy[legacy_status] = legacy.get(legacy_status, 0) + 1
    unmatched_total = (counts[CRITERIA_V4_BUCKET_NO_EVENT]
                       + counts[CRITERIA_V4_BUCKET_REFERENCE_INVALID]
                       + counts[CRITERIA_V4_BUCKET_PRODUCT_MISMATCH])
    denominator = len(sample_results or [])
    assert sum(counts.values()) == denominator, \
        "ppv1-criteria-v4 桶违背互斥闭合(桶和 != 分母;fail-closed)"
    return {
        "criteria_version": PPV1_CRITERIA_V4,
        "metric_name": CRITERIA_V4_METRIC_NAME,
        "metric_name_discipline": CRITERIA_V4_METRIC_DISCIPLINE_NOTE,
        "preregistration_doc": PPV1_CRITERIA_V4_PREREG_DOC,
        "hit_mode_scope": CRITERIA_V4_HIT_MODE_SCOPE,
        "denominator": denominator,
        "buckets": dict(sorted(counts.items())),
        "matched_product_hit": counts[CRITERIA_V4_BUCKET_MATCHED],
        "product_hit_partial": counts[CRITERIA_V4_BUCKET_PARTIAL],
        "product_hit_partial_v4_sense": partial_v4_sense,
        "product_hit_partial_outside_legacy_partial":
            partial_outside_legacy,
        "product_hit_partial_bucket_rule": (
            "product_hit_partial 沿既有 coverage 轴:仅当参考边旧状态"
            "为 matched_participant_coverage_partial 且 v4 未命中时"
            "计入;旧 unmatched_required_node_uncovered 题即使某个"
            "事件命中部分主产物也按 unmatched_product_mismatch 计,"
            "其「部分命中」另以 product_hit_partial_v4_sense / "
            "product_hit_partial_outside_legacy_partial 披露"
            "(§3 字面 trigger 与 §9 冻结读数 2/140 的差异见交付报告)"),
        "unmatched_total": unmatched_total,
        "product_hit_events_total": hit_events_total,
        "per_sample_bucket": dict(sorted(per_sample.items())),
        "reference_invalid_reasons": dict(sorted(reasons.items())),
        "exemption_bypassed": True,
        "exemption_bypass_note": CRITERIA_V4_EXEMPTION_BYPASS_NOTE,
        "exemption_counts": {
            "edges_with_exemption": 0,
            "events_exempted_strict": 0,
            "exempted_participant_occurrences": 0,
            "tier_counts": {CRITERIA_TIER_V1_EXEMPT: 0,
                            CRITERIA_TIER_NOT_EXEMPT: 0},
        },
        "coverage_facts_preserved": True,
        "coverage_facts_note": CRITERIA_V4_COVERAGE_PRESERVATION_NOTE,
        "legacy_bucket_separate": True,
        "legacy_match_status_bucket_counts": dict(sorted(legacy.items())),
        "v3_coexistence_note": (
            "v3 披露轴并列(criteria_version=v4 + "
            "disclosure_criteria_versions=(ppv1-criteria-v3,))时:v4 "
            "决定命中,v3 只产出归一披露,二者互不改写;v3 块内 "
            "exemption_subsumption_note 描述的是 v3 作主口径时的承载"
            "关系,在 v4 主口径下 v2 豁免已被旁路(本块 "
            "exemption_bypassed=true)"),
        "comparability_note": (
            "本块与 v1/v2/v3 的 strict/partial/unmatched 桶分列;"
            "禁止跨版本比较 strict 数,禁止把 matched_product_hit "
            "表述为 strict"),
    }


# ---------------------------------------------------------------- ppv1-criteria-v5:role_bound_product_hit
#
# 语义权威(唯一):docs/tasks/active/CRITERIA_V5_ROLE_BOUND_PREREG_DRAFT_2026-11-05.md
# (已签 v2:§1 判据 / §2 合法事件五条件与五桶 / §5 披露轴 / §7 负控
# 电池 / §8 翻转核对)。纪律:
#   * v5 = v4 的全部条件 + 事件产物侧集合从角色盲 ``T_E`` 收紧为
#     ``T_E^principal``(role 字符串**恰好**等于 ``"principal_product"``
#     才进集合);
#   * role 缺失/空/``unknown``/其它字符串 ⇒ 该参与物**不进**
#     ``T_E^principal``(fail-closed,不回退角色盲、不猜);
#   * 合法事件五条件与参考侧目标集合**逐字沿用 v4**:本段先调 v4
#     判定块拿参考侧节点集与逐事件合法性行(同一判据,不另立实现),
#     再只在事件产物侧加 role 过滤 ⇒ 事件集合不变、v4 命中集 ⊇ v5
#     命中集(单调性由构造保证,另由 §8.2 机器不变量核对);
#   * §5.2 共产物可追溯轴已升级为 **C4*(按声明的非氢元素预算;2026-11-05
#     CC 拍板采纳,规则权威 = Codex 代 mimo 评审第一节);只作披露,永不进
#     命中/位次/主成绩;
#   * v1/v2/v3/v4 判分路径一行不改(本段只新增常量/函数)。

PPV1_CRITERIA_V5_PREREG_DOC = (
    "docs/tasks/active/CRITERIA_V5_ROLE_BOUND_PREREG_DRAFT_2026-11-05.md")
CRITERIA_V5_METRIC_NAME = "role_bound_product_hit"
CRITERIA_V5_HIT_MODE_SCOPE = (
    "declared_principal_products_and_substrate_identity_role_bound")
CRITERIA_V5_EVENT_PRINCIPAL_ROLE = "principal_product"
CRITERIA_V5_EVENT_COPRODUCT_ROLE = "coproduct"
CRITERIA_V5_BUCKET_MATCHED = "role_bound_product_hit"
CRITERIA_V5_BUCKET_PARTIAL = "product_hit_partial"
CRITERIA_V5_BUCKET_NO_EVENT = "unmatched_no_event"
CRITERIA_V5_BUCKET_REFERENCE_INVALID = "unmatched_reference_invalid"
CRITERIA_V5_BUCKET_PRODUCT_MISMATCH = "unmatched_product_mismatch"
CRITERIA_V5_BUCKETS = (
    CRITERIA_V5_BUCKET_MATCHED,
    CRITERIA_V5_BUCKET_PARTIAL,
    CRITERIA_V5_BUCKET_NO_EVENT,
    CRITERIA_V5_BUCKET_REFERENCE_INVALID,
    CRITERIA_V5_BUCKET_PRODUCT_MISMATCH,
)
# 参考侧无效原因沿用 v4 同一枚举(§2.5 条件 5 与 v4 逐字相同)
CRITERIA_V5_REFERENCE_EVALUABLE = CRITERIA_V4_REFERENCE_EVALUABLE
CRITERIA_V5_REFERENCE_TARGET_EMPTY = CRITERIA_V4_REFERENCE_TARGET_EMPTY
CRITERIA_V5_REFERENCE_NODE_MISSING = CRITERIA_V4_REFERENCE_NODE_MISSING
CRITERIA_V5_REFERENCE_UNPARSEABLE = CRITERIA_V4_REFERENCE_UNPARSEABLE
CRITERIA_V5_REFERENCE_SCOPE_INSUFFICIENT = (
    CRITERIA_V4_REFERENCE_SCOPE_INSUFFICIENT)
CRITERIA_V5_METRIC_DISCIPLINE_NOTE = (
    "本指标机器名 role_bound_product_hit;不得称为 strict,与 v2 strict "
    "分列,禁止跨版本比较 strict 数;对外表述限「仅声明角色有界的主"
    "产物身份命中」,不得写成「反应预测正确率」")
CRITERIA_V5_ROLE_FILTER_NOTE = (
    "事件产物侧集合只收 role 字符串恰好等于 principal_product 的参与"
    "物;role 缺失/空/unknown/其它一律不进集合(fail-closed,不回退 "
    "v4 角色盲 T_E,不猜)")
CRITERIA_V5_EXEMPTION_BYPASS_NOTE = (
    "v5 沿 v4 旁路 ppv1-criteria-v2 参与物集合豁免(§9):豁免计数恒 "
    "0,不与 v2 读数混算")

# ---- §5.2 C4*:按声明的非氢元素预算(2026-11-05 CC 拍板采纳)----
# 规则权威全文 = docs/reviews/codex/CODEX_V5_COPRODUCT_TRACEABILITY_REVIEW_
# 2026-11-05.md 第一节;转录 = v5 预注册 v3 §5.2。本轴**只作披露**:
# 永不进命中、永不改位次、永不进主成绩。展示名不得裸称「来源已核」。
CRITERIA_V5_C4STAR_RULE_VERSION = "c4star-declared-non-hydrogen-budget-1"
CRITERIA_V5_C4STAR_DISPLAY_NAME = "按声明的非氢元素预算检查"
CRITERIA_V5_C4STAR_PROOF_SCOPE = (
    "按声明的非氢元素预算(仅事件声明参与物);未核:氢/同位素来源、"
    "形式电荷守恒、原子来源映射、键连接/立体、机理/生物可行性、"
    "反应物来源权威性、执行覆盖")
CRITERIA_V5_C4STAR_STATUS_TRACEABLE = "traceable"
CRITERIA_V5_C4STAR_STATUS_UNTRACEABLE = "untraceable"
CRITERIA_V5_C4STAR_STATUS_UNKNOWN = "unknown"
CRITERIA_V5_C4STAR_STATUS_NOT_APPLICABLE = "not_applicable"
CRITERIA_V5_C4STAR_STATUSES = (
    CRITERIA_V5_C4STAR_STATUS_TRACEABLE,
    CRITERIA_V5_C4STAR_STATUS_UNTRACEABLE,
    CRITERIA_V5_C4STAR_STATUS_UNKNOWN,
    CRITERIA_V5_C4STAR_STATUS_NOT_APPLICABLE,
)
CRITERIA_V5_C4STAR_REASON_MANIFEST_PARTIAL = "manifest_partial"
CRITERIA_V5_C4STAR_REASON_MANIFEST_UNKNOWN = "manifest_unknown"
CRITERIA_V5_C4STAR_REASON_ROLE_PARTITION_INCOMPLETE = (
    "role_partition_incomplete")
CRITERIA_V5_C4STAR_REASON_SIDE_UNDETERMINED = "side_undetermined"
CRITERIA_V5_C4STAR_REASON_AMBIGUOUS_DUPLICATE = (
    "ambiguous_duplicate_measurement")
CRITERIA_V5_C4STAR_REASON_STRUCTURE_UNPARSEABLE = "structure_unparseable"
CRITERIA_V5_C4STAR_REASON_UNQUANTIFIABLE_GROUP = (
    "unquantifiable_group_in_structure")
CRITERIA_V5_C4STAR_REASON_UNKNOWN_COEFFICIENT = "unknown_coefficient"
CRITERIA_V5_C4STAR_REASON_INVALID_COEFFICIENT = "invalid_coefficient"
CRITERIA_V5_C4STAR_REASON_COPRODUCT_HYDROGEN_ONLY = (
    "coproduct_hydrogen_only")
CRITERIA_V5_C4STAR_REASON_PRINCIPAL_OVER_BUDGET = (
    "principal_product_over_budget")
CRITERIA_V5_C4STAR_REASON_PARTICIPANT_INPUT_UNAVAILABLE = (
    "participant_input_unavailable")
CRITERIA_V5_C4STAR_REASON_CODES = (
    CRITERIA_V5_C4STAR_REASON_MANIFEST_PARTIAL,
    CRITERIA_V5_C4STAR_REASON_MANIFEST_UNKNOWN,
    CRITERIA_V5_C4STAR_REASON_ROLE_PARTITION_INCOMPLETE,
    CRITERIA_V5_C4STAR_REASON_SIDE_UNDETERMINED,
    CRITERIA_V5_C4STAR_REASON_AMBIGUOUS_DUPLICATE,
    CRITERIA_V5_C4STAR_REASON_STRUCTURE_UNPARSEABLE,
    CRITERIA_V5_C4STAR_REASON_UNQUANTIFIABLE_GROUP,
    CRITERIA_V5_C4STAR_REASON_UNKNOWN_COEFFICIENT,
    CRITERIA_V5_C4STAR_REASON_INVALID_COEFFICIENT,
    CRITERIA_V5_C4STAR_REASON_COPRODUCT_HYDROGEN_ONLY,
    CRITERIA_V5_C4STAR_REASON_PRINCIPAL_OVER_BUDGET,
    CRITERIA_V5_C4STAR_REASON_PARTICIPANT_INPUT_UNAVAILABLE,
)
# 清单完整度:沿用 hypothesis.participant_list_status 的两个完整值
# (audit.py 同一谓词;production.py:977–980 明示它只述清单完整,不述计量)
CRITERIA_V5_MANIFEST_COMPLETE_STATUSES = ("source_complete",
                                          "declared_complete")
CRITERIA_V5_C4STAR_EXECUTION_NOT_VERIFIED = "not_verified"
CRITERIA_V5_C4STAR_DISPLAY_DISCIPLINE_NOTE = (
    "traceable/untraceable 只是兼容枚举;展示必须写明「按声明的非氢预算"
    "覆盖/超支」,不得裸称「来源已核」;正剩余不等于完整配平,不得由预算"
    "状态推导生成/已执行")
CRITERIA_V5_C4STAR_SCOPE_NOTE = (
    "§5.2 C4* 只检查同一事件声明参与物的非氢元素预算(R/P/C 联合核算);"
    "排除氢及同位素与形式电荷,不假定统一 pH、不自动中和、不补水/质子/"
    "电子/辅因子/其它未声明参与物,无任何分子或方向豁免;只披露不判分")
# 兼容首轮字段名(coproduct_traceability):允许值即四状态全集
CRITERIA_V5_COPRODUCT_TRACEABILITY_ALLOWED = CRITERIA_V5_C4STAR_STATUSES


def _criteria_v5_product_species_bucket(n_species: int) -> str:
    """§5.1 ``product_species_bucket`` 分桶:1 / 2 / 3-4 / 5-8 / >8。

    ``n<=0`` 记 ``"0"``(合法事件产物侧恒非空;若出现即如实披露,
    不并入 1 桶)。"""
    if n_species <= 0:
        return "0"
    if n_species == 1:
        return "1"
    if n_species == 2:
        return "2"
    if n_species <= 4:
        return "3-4"
    if n_species <= 8:
        return "5-8"
    return ">8"


def _criteria_c4star_element_vector(structure: str) -> tuple[
        dict[str, int] | None, str | None]:
    """结构 → 非氢元素多重集(排除 H 及其同位素;形式电荷不进判定)。

    返回 ``(vector, error_reason)``。``vector`` 为 None 时:
    ``structure_unparseable``(缺失/不可解析/零原子)或
    ``unquantifiable_group_in_structure``(含原子序数 0 的通配基团,
    不能定量 ⇒ 不猜)。盐/溶剂化物按写入的多组分整串计,不剥离。
    """
    if not isinstance(structure, str) or not structure.strip():
        return None, CRITERIA_V5_C4STAR_REASON_STRUCTURE_UNPARSEABLE
    try:
        from rdkit import Chem as _Chem
        from rdkit import RDLogger as _RDLogger
    except ImportError:  # pragma: no cover —— 环境异常 fail-closed
        return None, CRITERIA_V5_C4STAR_REASON_STRUCTURE_UNPARSEABLE
    _RDLogger.DisableLog("rdApp.*")
    try:
        mol = _Chem.MolFromSmiles(structure)
    except Exception:  # noqa: BLE001 —— 不可解析按 unknown(不猜)
        mol = None
    if mol is None or mol.GetNumAtoms() == 0:
        return None, CRITERIA_V5_C4STAR_REASON_STRUCTURE_UNPARSEABLE
    vector: dict[str, int] = {}
    for atom in mol.GetAtoms():
        atomic_number = atom.GetAtomicNum()
        if atomic_number == 0:  # 通配基团/未定残基:不能定量
            return None, CRITERIA_V5_C4STAR_REASON_UNQUANTIFIABLE_GROUP
        if atomic_number == 1:  # H / D / T:本轴统一排除
            continue
        symbol = atom.GetSymbol()
        vector[symbol] = vector.get(symbol, 0) + 1
    return vector, None


def _criteria_c4star_coefficient(value) -> tuple[Fraction | None, str | None]:
    """系数 → 正有限 Fraction;None/invalid 分别返回原因(不补 1)。

    ``Fraction`` 精确支持正分数(如 ``"1/2"``/``0.5``);零/负/非有理/
    bool 一律 ``invalid``(沿 hypothesis.parse_coefficient 的输入契约)。
    """
    if value is None:
        return None, "unknown"
    if isinstance(value, bool):
        return None, "invalid"
    try:
        frac = value if isinstance(value, Fraction) else Fraction(str(value))
    except (ValueError, ZeroDivisionError, TypeError):
        return None, "invalid"
    if frac <= 0:
        return None, "invalid"
    return frac, None


def _criteria_c4star_unavailable_budget() -> dict:
    """无参与物输入时的兜底块(只在调用方未传 participants 时用)。"""
    return {
        "rule_version": CRITERIA_V5_C4STAR_RULE_VERSION,
        "display_name": CRITERIA_V5_C4STAR_DISPLAY_NAME,
        "proof_scope": CRITERIA_V5_C4STAR_PROOF_SCOPE,
        "status": CRITERIA_V5_C4STAR_STATUS_UNKNOWN,
        "reason_codes": [
            CRITERIA_V5_C4STAR_REASON_PARTICIPANT_INPUT_UNAVAILABLE],
        "budget_account_computable": False,
        "dp_by_element": None, "dt_by_element": None,
        "dc_by_element": None, "surplus_by_element": None,
        "n_elements": 0,
        "n_elements_dp_positive": 0, "n_elements_dt_positive": 0,
        "n_elements_dc_positive": 0, "n_elements_surplus_positive": 0,
        "completeness": {}, "counts": {},
        "execution_coverage_status":
            CRITERIA_V5_C4STAR_EXECUTION_NOT_VERIFIED,
        "execution_coverage_note": (
            "未核执行:执行覆盖须独立读取同批 production 报告,不得由"
            "预算状态推导生成或 verified"),
    }


def criteria_c4star_non_hydrogen_budget(
        participants: list[dict] | None, *,
        structure_by_state_ref: dict[str, str] | None = None,
        participant_list_status: str | None,
        ambiguous_participants: bool = False,
        execution_coverage_status: str = (
            CRITERIA_V5_C4STAR_EXECUTION_NOT_VERIFIED)) -> dict:
    """§5.2 **C4***:单事件「按声明的非氢元素预算」判定(纯函数、零 LLM)。

    规则权威 = Codex 代 mimo 评审
    ``docs/reviews/codex/CODEX_V5_COPRODUCT_TRACEABILITY_REVIEW_2026-11-05.md``
    第一节;转录 = v5 预注册 v3 §5.2。**只作披露:永不进命中、位次或主成绩。**

    - ``R`` = 反应物侧**全部**参与物(role 未分配不改变定义)计量和;
      ``P`` = 产物侧 ``principal_product`` 计量和;``C`` = 产物侧
      ``coproduct`` **联合**计量和(禁止逐个复用同一剩余池);
    - 元素维度排除全部氢(含同位素),形式电荷不进判定;无任何分子/
      方向豁免(H₂O 计 O、CO₂ 计 C/O、Pi 计 P/O…);
    - 系数必须已知且为正有限有理数(``Fraction``;支持 ``1/2`` 等正
      分数);unknown 不得补 1、不得用出现次数、不得拟合配平;
      ``parallel_contribution`` 明确的并列可求和,已归并系数只用一次,
      重复计量歧义 ⇒ unknown;
    - 纯氢参与物的未知系数不影响非氢向量(两侧对称);但它们作为
      共产物时本轴无「可核对象」⇒ 整体 unknown(保留可算账);
    - ``Dp=max(P−R,0)``、``Dt=max(P+C−R,0)``、``Dc=Dt−Dp``,逐元素
      遍历 R/P/C 并集(不只查 C 中出现的元素),另保留有符号余量
      ``R−P−C``;
    - 四状态(优先级):``not_applicable``(清单完整 + 角色分区明确 +
      确无 coproduct)⇒ ``unknown``(必要输入不全 / 纯氢共产物 /
      主产物已超预算 ``Dp≠0``)⇒ ``untraceable``(``Dp=0`` 但 C 联合
      占用后某元素超剩余)⇒ ``traceable``(``Dp=0`` 且 ``C≤R−P``)。
      ``traceable`` 只表示「按声明的非氢预算覆盖」,不表示来源已核。

    ``budget_account_computable`` 只表示 R/P/C 算术是否可完成(结构可
    解析、非氢系数已知、侧别可定、无计量歧义);清单 partial/unknown
    或产物角色分区不完整时算术仍可给描述量,但**主状态恒 unknown**。

    返回字段:``status`` / ``reason_codes`` / 逐元素 ``dp/dt/dc`` 与
    有符号余量 / 清单与计量完整度标志 / 角色与重复歧义计数 / 独立
    执行覆盖(恒 ``not_verified``,不由预算状态推导)。
    """
    reasons: list[str] = []

    def _add_reason(reason: str) -> None:
        if reason not in reasons:
            reasons.append(reason)

    structures = structure_by_state_ref or {}
    raw_status = str(participant_list_status or "")
    manifest_complete = raw_status in CRITERIA_V5_MANIFEST_COMPLETE_STATUSES
    if not manifest_complete:
        _add_reason(
            CRITERIA_V5_C4STAR_REASON_MANIFEST_PARTIAL
            if raw_status == "partial"
            else CRITERIA_V5_C4STAR_REASON_MANIFEST_UNKNOWN)
    if ambiguous_participants:
        _add_reason(CRITERIA_V5_C4STAR_REASON_AMBIGUOUS_DUPLICATE)

    counts = {
        "n_participant_entries": 0,
        "n_reactant_entries": 0,
        "n_principal_entries": 0,
        "n_coproduct_entries": 0,
        "n_other_product_role_entries": 0,
        "n_hydrogen_only_reactant_entries": 0,
        "n_hydrogen_only_coproduct_entries": 0,
        "n_merged_measurement_entries": 0,
        "n_unknown_coefficient_non_hydrogen_entries": 0,
    }
    role_partition_complete = True
    side_complete = True
    entries: list[dict] = []
    for participant in participants or []:
        if not isinstance(participant, dict):
            _add_reason(CRITERIA_V5_C4STAR_REASON_SIDE_UNDETERMINED)
            side_complete = False
            continue
        counts["n_participant_entries"] += 1
        side = str(participant.get("side") or "")
        raw_role = participant.get("role")
        role = "" if raw_role is None else str(raw_role)
        if side not in ("reactant", "product"):
            _add_reason(CRITERIA_V5_C4STAR_REASON_SIDE_UNDETERMINED)
            side_complete = False
        if side == "reactant":
            counts["n_reactant_entries"] += 1
        elif side == "product":
            if role == CRITERIA_V5_EVENT_PRINCIPAL_ROLE:
                counts["n_principal_entries"] += 1
            elif role == CRITERIA_V5_EVENT_COPRODUCT_ROLE:
                counts["n_coproduct_entries"] += 1
            else:
                counts["n_other_product_role_entries"] += 1
                _add_reason(
                    CRITERIA_V5_C4STAR_REASON_ROLE_PARTITION_INCOMPLETE)
                role_partition_complete = False
        entries.append({
            "side": side,
            "role": role,
            "state_ref": str(participant.get("state_ref") or ""),
            "coefficient": participant.get("coefficient"),
            "coefficient_status": str(
                participant.get("coefficient_status") or ""),
            "parallel_contribution": bool(
                participant.get("parallel_contribution")),
            "n_sources": max(1, len(participant.get("merged_from") or [])),
        })

    # ---- 多重集与归并轨迹:同 (side, state_ref, role) 的明确并列求和;
    # 歧义重复保留并置 unknown(不静默去重、不盲目累加)----
    groups: dict[tuple[str, str, str], list[dict]] = {}
    order: list[tuple[str, str, str]] = []
    for entry in entries:
        key = (entry["side"], entry["state_ref"], entry["role"])
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(entry)
    measurements: list[dict] = []
    # hypothesis 层已标 ambiguous(归一化时保留了重复)⇒ 计量口径不清,
    # 本轴不猜:账不可算,主状态 unknown。
    ambiguous_measurement = bool(ambiguous_participants)
    for key in order:
        group = groups[key]
        if len(group) == 1:
            measurements.append(dict(group[0]))
            continue
        mergeable = all(item["parallel_contribution"] for item in group) and all(
            _criteria_c4star_coefficient(item["coefficient"])[0] is not None
            for item in group)
        if not mergeable:
            ambiguous_measurement = True
            _add_reason(CRITERIA_V5_C4STAR_REASON_AMBIGUOUS_DUPLICATE)
            measurements.extend(dict(item) for item in group)
            continue
        combined = dict(group[0])
        combined["coefficient"] = sum(
            (_criteria_c4star_coefficient(item["coefficient"])[0]
             for item in group), Fraction(0))
        combined["n_sources"] = sum(item["n_sources"] for item in group)
        measurements.append(combined)
    counts["n_merged_measurement_entries"] = sum(
        1 for item in measurements if item["n_sources"] > 1)

    # ---- 非氢元素预算:R(全部反应物)/ P(principal)/ C(coproduct 联合)
    r_sum: dict[str, Fraction] = {}
    p_sum: dict[str, Fraction] = {}
    c_sum: dict[str, Fraction] = {}
    account_computable = side_complete and not ambiguous_measurement
    hydrogen_only_coproduct = 0
    for measurement in measurements:
        structure = structures.get(measurement["state_ref"])
        vector, error = _criteria_c4star_element_vector(
            structure if isinstance(structure, str) else "")
        if error is not None:
            _add_reason(error)
            account_computable = False
            continue
        if sum(vector.values()) == 0:
            # 纯氢物种:无非氢向量,未知系数不影响本轴(两侧对称)
            if measurement["side"] == "reactant":
                counts["n_hydrogen_only_reactant_entries"] += 1
            elif measurement["role"] == CRITERIA_V5_EVENT_COPRODUCT_ROLE:
                counts["n_hydrogen_only_coproduct_entries"] += 1
                hydrogen_only_coproduct += 1
            continue
        coefficient, coefficient_error = _criteria_c4star_coefficient(
            measurement["coefficient"])
        if coefficient is None:
            account_computable = False
            if coefficient_error == "unknown" or (
                    measurement["coefficient_status"] == "unknown"):
                counts["n_unknown_coefficient_non_hydrogen_entries"] += 1
                _add_reason(CRITERIA_V5_C4STAR_REASON_UNKNOWN_COEFFICIENT)
            else:
                _add_reason(CRITERIA_V5_C4STAR_REASON_INVALID_COEFFICIENT)
            continue
        if measurement["side"] == "reactant":
            target = r_sum
        elif measurement["role"] == CRITERIA_V5_EVENT_PRINCIPAL_ROLE:
            target = p_sum
        elif measurement["role"] == CRITERIA_V5_EVENT_COPRODUCT_ROLE:
            target = c_sum
        else:  # 其它产物角色:已判 role_partition_incomplete,不进 P/C
            continue
        for element, atom_count in vector.items():
            target[element] = (target.get(element, Fraction(0))
                               + coefficient * atom_count)

    no_coproduct = counts["n_coproduct_entries"] == 0
    dp_by_element = dt_by_element = dc_by_element = surplus_by_element = None
    n_dp = n_dt = n_dc = n_surplus = 0
    elements_checked: list[str] = []
    if account_computable and not (
            no_coproduct and manifest_complete and role_partition_complete):
        elements_checked = sorted(set(r_sum) | set(p_sum) | set(c_sum))
        dp_by_element = {}
        dt_by_element = {}
        dc_by_element = {}
        surplus_by_element = {}
        for element in elements_checked:
            r_value = r_sum.get(element, Fraction(0))
            p_value = p_sum.get(element, Fraction(0))
            c_value = c_sum.get(element, Fraction(0))
            dp_value = max(p_value - r_value, Fraction(0))
            dt_value = max(p_value + c_value - r_value, Fraction(0))
            dc_value = dt_value - dp_value
            surplus_value = r_value - p_value - c_value
            dp_by_element[element] = str(dp_value)
            dt_by_element[element] = str(dt_value)
            dc_by_element[element] = str(dc_value)
            surplus_by_element[element] = str(surplus_value)
            n_dp += int(dp_value > 0)
            n_dt += int(dt_value > 0)
            n_dc += int(dc_value > 0)
            n_surplus += int(surplus_value > 0)

    # ---- 四状态(优先级:not_applicable → unknown → untraceable →
    # traceable);条件型 reason(纯氢共产物、主产物已超预算)只要账可算
    # 就记录——即使主状态已因清单 partial/角色分区不全而 unknown,
    # 也如实披露可确定的缺口(reason code 不因主状态被吞掉)----
    if account_computable and n_dp:
        _add_reason(CRITERIA_V5_C4STAR_REASON_PRINCIPAL_OVER_BUDGET)
    if hydrogen_only_coproduct:
        _add_reason(CRITERIA_V5_C4STAR_REASON_COPRODUCT_HYDROGEN_ONLY)
    if no_coproduct:
        if manifest_complete and role_partition_complete:
            status = CRITERIA_V5_C4STAR_STATUS_NOT_APPLICABLE
            reasons = ["no_coproduct_participant"]
        else:
            status = CRITERIA_V5_C4STAR_STATUS_UNKNOWN
    elif not (manifest_complete and role_partition_complete
              and account_computable):
        status = CRITERIA_V5_C4STAR_STATUS_UNKNOWN
    elif hydrogen_only_coproduct or n_dp:
        status = CRITERIA_V5_C4STAR_STATUS_UNKNOWN
    elif n_dt:
        status = CRITERIA_V5_C4STAR_STATUS_UNTRACEABLE
    else:
        status = CRITERIA_V5_C4STAR_STATUS_TRACEABLE

    return {
        "rule_version": CRITERIA_V5_C4STAR_RULE_VERSION,
        "display_name": CRITERIA_V5_C4STAR_DISPLAY_NAME,
        "proof_scope": CRITERIA_V5_C4STAR_PROOF_SCOPE,
        "status": status,
        "reason_codes": list(reasons),
        "budget_account_computable": bool(account_computable),
        "elements_checked": elements_checked,
        "n_elements": len(elements_checked),
        "dp_by_element": dp_by_element,
        "dt_by_element": dt_by_element,
        "dc_by_element": dc_by_element,
        "surplus_by_element": surplus_by_element,
        "n_elements_dp_positive": n_dp,
        "n_elements_dt_positive": n_dt,
        "n_elements_dc_positive": n_dc,
        "n_elements_surplus_positive": n_surplus,
        "dp_positive": bool(n_dp),
        "dt_positive": bool(n_dt),
        "dc_positive": bool(n_dc),
        "surplus_positive": bool(n_surplus),
        "completeness": {
            "participant_list_status": raw_status or None,
            "manifest_complete": bool(manifest_complete),
            "role_partition_complete": bool(role_partition_complete),
            "side_assignments_complete": bool(side_complete),
            "ambiguous_duplicate_measurements": bool(
                ambiguous_measurement or ambiguous_participants),
            "non_hydrogen_coefficients_all_known": bool(
                counts["n_unknown_coefficient_non_hydrogen_entries"] == 0),
        },
        "counts": counts,
        "no_coproduct_participant": bool(no_coproduct),
        "execution_coverage_status": str(execution_coverage_status),
        "execution_coverage_note": (
            "未核执行:执行覆盖须独立读取同批 production 报告,不得由"
            "预算状态推导生成或 verified"),
        "scope_note": CRITERIA_V5_C4STAR_SCOPE_NOTE,
        "display_discipline_note":
            CRITERIA_V5_C4STAR_DISPLAY_DISCIPLINE_NOTE,
    }


def _criteria_v5_event_disclosure(product_participants: list[tuple[
        str, str]], c4star_budget: dict | None = None) -> dict:
    """§5.1 披露字段 + §5.2 C4* 预算块(单事件产物侧;不进命中/位次)。

    ``product_participants`` = [(严格身份串, role 串), ...],保序含重复。
    三个 role 种数按**定义字面**计数(同一身份多角色时可在多类各计一
    次),另给 ``n_multirole_species`` 供读者对账(三数和 − 多重身份数
    = ``n_product_species_total``)。``c4star_budget`` 为
    :func:`criteria_c4star_non_hydrogen_budget` 的输出;缺省(旧调用)
    退回 fail-closed 的 unknown 块,绝不冒充可判。
    """
    roles_by_species: dict[str, set[str]] = {}
    for identity, role in product_participants:
        roles_by_species.setdefault(identity, set()).add(role)
    n_total = len(roles_by_species)
    n_principal = sum(1 for roles in roles_by_species.values()
                      if CRITERIA_V5_EVENT_PRINCIPAL_ROLE in roles)
    n_coproduct = sum(1 for roles in roles_by_species.values()
                      if CRITERIA_V5_EVENT_COPRODUCT_ROLE in roles)
    n_other = sum(
        1 for roles in roles_by_species.values()
        if any(role not in (CRITERIA_V5_EVENT_PRINCIPAL_ROLE,
                            CRITERIA_V5_EVENT_COPRODUCT_ROLE)
               for role in roles))
    n_multirole = sum(1 for roles in roles_by_species.values()
                      if len(roles) > 1)
    # 角色缺失/未知的机器披露(PC-3):v5 不猜成 principal(fail-closed)
    n_role_missing = sum(1 for _identity, role in product_participants
                         if role == "")
    n_role_unknown = sum(1 for _identity, role in product_participants
                         if role.strip().lower() == "unknown")
    budget = (c4star_budget if isinstance(c4star_budget, dict)
              else _criteria_c4star_unavailable_budget())
    traceability = str(budget.get("status")
                       or CRITERIA_V5_C4STAR_STATUS_UNKNOWN)
    traceability_reason = ";".join(
        str(code) for code in (budget.get("reason_codes") or []))
    return {
        "n_product_species_total": n_total,
        "n_principal_species": n_principal,
        "n_coproduct_species": n_coproduct,
        "n_other_role_species": n_other,
        "n_multirole_species": n_multirole,
        "n_participant_entries": len(product_participants),
        "n_role_missing_entries": n_role_missing,
        "n_role_unknown_entries": n_role_unknown,
        "role_missing_or_unknown_present": bool(
            n_role_missing or n_role_unknown),
        "product_species_bucket":
            _criteria_v5_product_species_bucket(n_total),
        "coproduct_traceability": traceability,
        "coproduct_traceability_reason": traceability_reason,
        "c4star_budget": budget,
    }


def _criteria_v5_reference_identities(v4_block: dict,
                                      nodes_by_id: dict[str, dict]
                                      ) -> tuple[set[str], set[str]]:
    """由 v4 判定块已接受的参考节点集重算严格身份(同一函数)。

    v4 块对 ``reference_invalid_reason is None`` 的边已成功对同一节点
    集调用过 ``strict_identity_of`` ⇒ 此处失败只可能是实现不一致,
    直接结构化拒(fail-closed,不静默降级)。
    """
    identity_by_node: dict[str, str] = {}
    node_ids = list(v4_block.get("substrate_node_ids") or []) + list(
        v4_block.get("principal_product_node_ids") or [])
    try:
        for nid in node_ids:
            identity_by_node[nid] = strict_identity_of(
                str((nodes_by_id[nid] or {}).get("structure_smiles")))
    except (ChemicalStateError, KeyError) as exc:
        raise EvaluationContractError(
            "ppv1-criteria-v5 参考侧身份重算失败(v4 块已判可评,"
            "实现不一致;fail-closed)", {
                "kind": "criteria_v5_reference_identity_recompute_failed",
                "error": type(exc).__name__}) from exc
    substrate_identities = {
        identity_by_node[nid]
        for nid in v4_block.get("substrate_node_ids") or []
        if nid in identity_by_node}
    principal_identities = {
        identity_by_node[nid]
        for nid in v4_block.get("principal_product_node_ids") or []
        if nid in identity_by_node}
    return substrate_identities, principal_identities


def _criteria_v5_edge_product_hit(edge: dict,
                                  nodes_by_id: dict[str, dict],
                                  payload: dict | None,
                                  legacy_match_status: str | None = None
                                  ) -> dict:
    """单参考边的 ppv1-criteria-v5 判定块(§1/§2;纯函数)。

    - 参考侧(``S`` / ``P``)与逐事件合法性**全部取自 v4 判定块**
      (§2 条件 1–5 一字不改);本函数只在合法事件的产物侧加 role
      过滤;
    - ``T_E^principal`` 只收 role 恰好 ``principal_product`` 的产物侧
      参与物身份;``T_E`` 全角色集合与 ``coproduct``/其它角色集合
      同时保留,供 §5.1 披露与 v4→v5 翻转子类机器判定;
    - §2.2 五桶:命中桶 = ``role_bound_product_hit``;``partial`` 按
      预注册字面 trigger(多主产物题同一事件命中部分参考主产物,不记
      命中),**不继承** v4 的 2/140 定版数;v4 的旧 coverage 轴归属
      另以机读字段并列披露;
    - 输出零 SMILES(只事件 id/节点 id/身份 sha256_16/计数)。
    """
    v4_block = _criteria_v4_edge_product_hit(
        edge, nodes_by_id, payload,
        legacy_match_status=legacy_match_status)
    reason = v4_block.get("reference_invalid_reason")
    substrate_identities: set[str] = set()
    principal_identities: set[str] = set()
    if reason is None:
        substrate_identities, principal_identities = \
            _criteria_v5_reference_identities(v4_block, nodes_by_id)
    states = _export_states(payload or {})
    structure_by_state_ref = {
        ref: str(row.get("smiles_isomeric") or "")
        for ref, row in states.items()}
    hypothesis_bodies = _hypothesis_payloads(payload or {})
    events_sorted = sorted((payload or {}).get("events") or [],
                           key=lambda e: str(e.get("event_id")))
    v4_rows = v4_block.get("events") or []
    if len(events_sorted) != len(v4_rows):
        raise EvaluationContractError(
            "ppv1-criteria-v5 事件行与 v4 块不一致(实现不一致;"
            "fail-closed)", {
                "kind": "criteria_v5_event_row_count_mismatch",
                "n_events": len(events_sorted),
                "n_v4_rows": len(v4_rows)})
    eligible = 0
    hit_events: list[str] = []
    partial_events: list[str] = []
    ineligible_reasons: dict[str, int] = {}
    event_rows: list[dict] = []
    max_species_eligible = 0
    for event, v4_row in zip(events_sorted, v4_rows):
        event_id = str(v4_row.get("event_id") or "")
        if not v4_row.get("eligible"):
            row = {"event_id": event_id, "eligible": False,
                   "ineligible_reason": v4_row.get("ineligible_reason")}
            ineligible_reasons[str(row["ineligible_reason"])] = (
                ineligible_reasons.get(str(row["ineligible_reason"]), 0)
                + 1)
            event_rows.append(row)
            continue
        if event_id != str(event.get("event_id") or ""):
            raise EvaluationContractError(
                "ppv1-criteria-v5 事件序与 v4 块不一致(实现不一致;"
                "fail-closed)", {
                    "kind": "criteria_v5_event_order_mismatch"})
        eligible += 1
        participants = _event_participants(event)
        reactant_ids: set[str] = set()
        product_participants: list[tuple[str, str]] = []
        for participant in participants:
            ref = str(participant.get("state_ref") or "")
            if ref not in states:
                # v4 对合法事件已核"两侧参与物可解析" ⇒ 走到这里即不一致
                raise EvaluationContractError(
                    "ppv1-criteria-v5 合法事件参与物不可解析(v4 块已核;"
                    "实现不一致;fail-closed)", {
                        "kind": "criteria_v5_participant_unparseable"})
            identity = str(states[ref].get("smiles_isomeric") or "")
            side = str(participant.get("side"))
            if side == "reactant":
                reactant_ids.add(identity)
            elif side == "product":
                product_participants.append(
                    (identity, str(participant.get("role") or "")))
        product_all = {identity for identity, _role in product_participants}
        product_principal = {
            identity for identity, role in product_participants
            if role == CRITERIA_V5_EVENT_PRINCIPAL_ROLE}
        product_coproduct = {
            identity for identity, role in product_participants
            if role == CRITERIA_V5_EVENT_COPRODUCT_ROLE}
        substrate_ok = bool(substrate_identities & reactant_ids)
        matched_principal = principal_identities & product_principal
        full_hit = bool(substrate_ok and principal_identities
                        and principal_identities <= product_principal)
        # §5.2 C4*:声明非氢元素预算(只进披露,不改 hit/rank/bucket)
        hypothesis_body = hypothesis_bodies.get(
            str(event.get("hypothesis_id") or "")) or {}
        c4star_budget = criteria_c4star_non_hydrogen_budget(
            participants,
            structure_by_state_ref=structure_by_state_ref,
            participant_list_status=hypothesis_body.get(
                "participant_list_status"),
            ambiguous_participants=bool(
                hypothesis_body.get("ambiguous_participants")))
        disclosure = _criteria_v5_event_disclosure(
            product_participants, c4star_budget=c4star_budget)
        max_species_eligible = max(
            max_species_eligible, disclosure["n_product_species_total"])
        row = {
            "event_id": event_id,
            "eligible": True,
            "substrate_identity_in_reactants": substrate_ok,
            "principal_products_total": len(principal_identities),
            "principal_products_matched_principal": len(
                matched_principal),
            "principal_products_matched_coproduct": len(
                principal_identities & product_coproduct),
            "principal_products_matched_other_roles": len(
                principal_identities
                & (product_all - product_principal - product_coproduct)),
            "matched_principal_identity_sha256_16": sorted(
                _criteria_v4_identity_sha256_16(identity)
                for identity in matched_principal),
            "role_bound_product_hit": full_hit,
            **disclosure,
        }
        event_rows.append(row)
        if full_hit:
            hit_events.append(event_id)
        elif substrate_ok and matched_principal and \
                len(principal_identities) >= 2:
            # §2.2 product_hit_partial 字面 trigger:多主产物题、同一
            # 事件内只命中部分参考主产物(role 过滤后);不记为命中
            partial_events.append(event_id)
    hit = bool(hit_events)
    partial = bool(partial_events and not hit)
    legacy_partial_axis = bool(
        not hit and legacy_match_status
        == "matched_participant_coverage_partial")
    if reason is not None:
        bucket = CRITERIA_V5_BUCKET_REFERENCE_INVALID
    elif hit:
        bucket = CRITERIA_V5_BUCKET_MATCHED
    elif partial:
        bucket = CRITERIA_V5_BUCKET_PARTIAL
    elif eligible == 0:
        bucket = CRITERIA_V5_BUCKET_NO_EVENT
    else:
        bucket = CRITERIA_V5_BUCKET_PRODUCT_MISMATCH
    return {
        "criteria_version": PPV1_CRITERIA_V5,
        "edge_id": str(edge.get("edge_id")),
        "metric_name": CRITERIA_V5_METRIC_NAME,
        "hit_mode_scope": CRITERIA_V5_HIT_MODE_SCOPE,
        "preregistration_doc": PPV1_CRITERIA_V5_PREREG_DOC,
        "role_filter": CRITERIA_V5_EVENT_PRINCIPAL_ROLE,
        "role_filter_note": CRITERIA_V5_ROLE_FILTER_NOTE,
        "reference_status": (CRITERIA_V5_REFERENCE_EVALUABLE
                             if reason is None else "not_evaluable"),
        "reference_invalid_reason": reason,
        "substrate_node_ids": list(
            v4_block.get("substrate_node_ids") or []),
        "principal_product_node_ids": list(
            v4_block.get("principal_product_node_ids") or []),
        "substrate_identity_sha256_16": sorted(
            _criteria_v4_identity_sha256_16(identity)
            for identity in substrate_identities),
        "principal_product_identity_sha256_16": sorted(
            _criteria_v4_identity_sha256_16(identity)
            for identity in principal_identities),
        "eligible_event_count": eligible,
        "event_count": len(events_sorted),
        "role_bound_product_hit": hit,
        "product_hit_partial": partial,
        "role_bound_hit_events": sorted(hit_events),
        "partial_product_hit_events": sorted(partial_events),
        "bucket": bucket,
        "legacy_match_status": legacy_match_status,
        "product_hit_partial_legacy_coverage_axis": legacy_partial_axis,
        "max_product_species_any_qualifying_event": max_species_eligible,
        "ineligible_event_reasons": dict(sorted(ineligible_reasons.items())),
        "events": event_rows,
        "coverage_facts_preserved": True,
        "coverage_facts_note": CRITERIA_V4_COVERAGE_PRESERVATION_NOTE,
        "exemption_bypassed": True,
        "exemption_bypass_note": CRITERIA_V5_EXEMPTION_BYPASS_NOTE,
        "coproduct_traceability_scope_note":
            CRITERIA_V5_C4STAR_SCOPE_NOTE,
    }


def _criteria_v5_sample_block(edge_blocks: list[dict]) -> dict:
    """样本级 v5 汇总(逐边块 → 题级桶;§2.2 互斥桶,分母不剔题)。

    题级优先序(沿 v4 §3 结构,命中条件替换):任一参考边命中 ⇒
    ``role_bound_product_hit``;否则任一边 partial ⇒
    ``product_hit_partial``;否则全部边参考无效 ⇒
    ``unmatched_reference_invalid``;否则有合法事件 ⇒
    ``unmatched_product_mismatch``;否则 ``unmatched_no_event``。
    """
    blocks: list[dict] = []
    for block in edge_blocks or []:
        if not isinstance(block, dict):
            continue
        nested = block.get("criteria_v5")
        blocks.append(nested if isinstance(nested, dict) else block)
    hit_events = sorted({str(event) for block in blocks
                         for event in
                         block.get("role_bound_hit_events") or []})
    partial_events = sorted({str(event) for block in blocks
                             for event in
                             block.get("partial_product_hit_events") or []})
    reasons: dict[str, int] = {}
    for block in blocks:
        reason = block.get("reference_invalid_reason")
        if reason:
            reasons[str(reason)] = reasons.get(str(reason), 0) + 1
    eligible = sum(int(block.get("eligible_event_count") or 0)
                   for block in blocks)
    hit = any(bool(block.get("role_bound_product_hit")) for block in blocks)
    partial = any(block.get("bucket") == CRITERIA_V5_BUCKET_PARTIAL
                  for block in blocks)
    if hit:
        bucket = CRITERIA_V5_BUCKET_MATCHED
    elif partial:
        bucket = CRITERIA_V5_BUCKET_PARTIAL
    elif blocks and all(
            block.get("bucket") == CRITERIA_V5_BUCKET_REFERENCE_INVALID
            for block in blocks):
        bucket = CRITERIA_V5_BUCKET_REFERENCE_INVALID
    elif eligible:
        bucket = CRITERIA_V5_BUCKET_PRODUCT_MISMATCH
    else:
        bucket = CRITERIA_V5_BUCKET_NO_EVENT
    max_species = max(
        [int(block.get("max_product_species_any_qualifying_event") or 0)
         for block in blocks] or [0])
    return {
        "criteria_version": PPV1_CRITERIA_V5,
        "metric_name": CRITERIA_V5_METRIC_NAME,
        "hit_mode_scope": CRITERIA_V5_HIT_MODE_SCOPE,
        "preregistration_doc": PPV1_CRITERIA_V5_PREREG_DOC,
        "role_bound_product_hit": hit,
        "product_hit_partial": partial,
        "role_bound_hit_events": hit_events,
        "partial_product_hit_events": partial_events,
        "bucket": bucket,
        "eligible_event_count": eligible,
        "per_edge_bucket": {
            str(block.get("edge_id")): str(block.get("bucket"))
            for block in blocks},
        "reference_invalid_reasons": dict(sorted(reasons.items())),
        "max_product_species_any_qualifying_event": max_species,
        "coverage_facts_preserved": True,
        "coverage_facts_note": CRITERIA_V4_COVERAGE_PRESERVATION_NOTE,
        "metric_name_discipline_note": CRITERIA_V5_METRIC_DISCIPLINE_NOTE,
    }


def _criteria_v5_batch_block(sample_results: list[dict]) -> dict:
    """批级 v5 汇总(§2.2 五桶 + 豁免旁路披露 + 旧桶分列)。

    分母 = 样本数(失败/无效题留分母);逐题恰一 v5 桶,桶和 = 分母
    (断言 fail-closed)。§5.1/§5.2 的逐题首事件披露与分布聚合在判分
    层(``s5b_scoring._role_bound_hit_caliber_block``)完成,因为首事件
    选择必须用与 v4 位次同一条候选序。
    """
    counts = {bucket: 0 for bucket in CRITERIA_V5_BUCKETS}
    per_sample: dict[str, str] = {}
    reasons: dict[str, int] = {}
    legacy: dict[str, int] = {}
    hit_events_total = 0
    partial_legacy_axis = 0
    for sample in sample_results or []:
        block = sample.get("criteria_v5") or {}
        bucket = str(block.get("bucket") or CRITERIA_V5_BUCKET_NO_EVENT)
        if bucket not in counts:
            bucket = CRITERIA_V5_BUCKET_NO_EVENT
        counts[bucket] += 1
        per_sample[str(sample.get("sample_id"))] = bucket
        hit_events_total += len(block.get("role_bound_hit_events") or [])
        edges = sample.get("predicted_edge_matches") or []
        if any((edge.get("criteria_v5") or {}).get(
                "product_hit_partial_legacy_coverage_axis")
               and not (edge.get("criteria_v5") or {}).get(
                   "role_bound_product_hit")
               for edge in edges):
            partial_legacy_axis += 1
        for reason, n in (block.get("reference_invalid_reasons")
                          or {}).items():
            reasons[str(reason)] = reasons.get(str(reason), 0) + int(n)
        legacy_status = (str(edges[0].get("match_status")) if edges
                         else "not_evaluated_no_edges")
        legacy[legacy_status] = legacy.get(legacy_status, 0) + 1
    denominator = len(sample_results or [])
    assert sum(counts.values()) == denominator, \
        "ppv1-criteria-v5 桶违背互斥闭合(桶和 != 分母;fail-closed)"
    return {
        "criteria_version": PPV1_CRITERIA_V5,
        "metric_name": CRITERIA_V5_METRIC_NAME,
        "metric_name_discipline": CRITERIA_V5_METRIC_DISCIPLINE_NOTE,
        "preregistration_doc": PPV1_CRITERIA_V5_PREREG_DOC,
        "hit_mode_scope": CRITERIA_V5_HIT_MODE_SCOPE,
        "role_filter": CRITERIA_V5_EVENT_PRINCIPAL_ROLE,
        "role_filter_note": CRITERIA_V5_ROLE_FILTER_NOTE,
        "denominator": denominator,
        "buckets": dict(sorted(counts.items())),
        "role_bound_product_hit": counts[CRITERIA_V5_BUCKET_MATCHED],
        "product_hit_partial": counts[CRITERIA_V5_BUCKET_PARTIAL],
        "product_hit_partial_bucket_rule": (
            "product_hit_partial 按预注册 §2.2 字面 trigger:无事件命中"
            "全部参考主产物,但存在合法事件在同一事件内命中部分参考"
            "主产物(多主产物题专用);不继承 v4 的 2/140 定版数。"
            "v4 旧 coverage 轴归属另以 product_hit_partial_legacy_"
            "coverage_axis 逐边/批级并列披露"),
        "product_hit_partial_legacy_coverage_axis": partial_legacy_axis,
        "unmatched_total": (counts[CRITERIA_V5_BUCKET_NO_EVENT]
                            + counts[CRITERIA_V5_BUCKET_REFERENCE_INVALID]
                            + counts[CRITERIA_V5_BUCKET_PRODUCT_MISMATCH]),
        "role_bound_hit_events_total": hit_events_total,
        "per_sample_bucket": dict(sorted(per_sample.items())),
        "reference_invalid_reasons": dict(sorted(reasons.items())),
        "exemption_bypassed": True,
        "exemption_bypass_note": CRITERIA_V5_EXEMPTION_BYPASS_NOTE,
        "exemption_counts": {
            "edges_with_exemption": 0,
            "events_exempted_strict": 0,
            "exempted_participant_occurrences": 0,
            "tier_counts": {CRITERIA_TIER_V1_EXEMPT: 0,
                            CRITERIA_TIER_NOT_EXEMPT: 0},
        },
        "coverage_facts_preserved": True,
        "coverage_facts_note": CRITERIA_V4_COVERAGE_PRESERVATION_NOTE,
        "legacy_bucket_separate": True,
        "legacy_match_status_bucket_counts": dict(sorted(legacy.items())),
        "coproduct_traceability": {
            "status": "implemented_c4star",
            "rule_version": CRITERIA_V5_C4STAR_RULE_VERSION,
            "display_name": CRITERIA_V5_C4STAR_DISPLAY_NAME,
            "implemented_rules": ["c4star_declared_non_hydrogen_budget"],
            "allowed_outputs": list(
                CRITERIA_V5_COPRODUCT_TRACEABILITY_ALLOWED),
            "scope_note": CRITERIA_V5_C4STAR_SCOPE_NOTE,
            "display_discipline_note":
                CRITERIA_V5_C4STAR_DISPLAY_DISCIPLINE_NOTE,
            "aggregation_note": (
                "四状态/reason code/缺口的域级聚合在判分层 "
                "_role_bound_hit_caliber_block(disclosure_axis_5_2)与"
                "证据聚合脚本完成;本块只声明规则身份"),
        },
        "comparability_note": (
            "本块与 v1/v2/v3/v4 的桶分列;v4 是永久基线(不覆盖、不改写),"
            "v5 是角色有界主产物身份命中;禁止跨版本比较 strict 数,"
            "禁止把 role_bound_product_hit 表述为 strict 或「反应预测"
            "正确率」"),
    }


def match_reference_nodes(reference_graph: dict,
                          payload: dict, *,
                          criteria_version: str = PPV1_CRITERIA_V1,
                          disclosure_criteria_versions: tuple[
                              str, ...] = ()) -> list[
        dict]:
    """参考节点匹配(确定性;严格身份 vs CN 旁证分轴;distinct
    occurrence 不按 CN/首现合并)。

    返回逐 reference 节点条目:
    - ``match_status`` ∈ strict_structure | cn_only | unmatched |
      reference_structure_unparseable;
    - 严格结构命中要求双方严格身份相等;CN 相同但严格身份不同/未知
      ⇒ ``cn_only``(**不**计为严格结构命中,S5-10/S5-11);
    - **S5A-01(参考身份 scope 先消费许可,再授严格档)**:参考节点
      声明 ``structure_identity_scope ∈ {cn_only, partial, unknown}``
      ⇒ 许可范围封顶 —— 内容严格相等也只作 CN 旁证(``cn_only``),
      不授 ``strict_structure``、不进边严格匹配的 ``strict_by_node``
      与严格指标(冻结稿 §0 旁证不叠加升格;scope=strict_structure
      才允许严格档);封顶发生时机读披露附 ``identity_scope_cap``
      (机读);合法 strict 与真实 CN 旁证控制保持,不全面拒绝带
      标签或有限图;
    - 每条 occurrence 独立条目(同结构不同 occurrence 不合并,S5-04);
    - 预测侧 occurrence 计数(state_appearances/事件参与)如实披露
      (两档基数不同,不可跨档比较);
    - **ppv1-criteria-v3(T-D-A/B 披露轴,显式启用)**:v3 时对
      ``structure_identity_scope=="strict_structure"`` 参考节点的
      cn_only 配对**仅**追加披露块 ``criteria_v3_normalized_identity``
      (A 轴双臂布尔 / B 轴单启用臂 + 敏感性臂 / 单归属 / 碳酸体系
      排除;档 A **只披露**);``match_status``、严格档与 S5A-01 封顶
      **零改动**(不授 strict、不进 hit@1);缺省 v1/v2 零新键。
    """
    resolve_criteria_version(criteria_version)
    disclosure_versions = _validate_disclosure_criteria_versions(
        disclosure_criteria_versions)
    v3_disclosure = _criteria_v3_disclosure_enabled(
        criteria_version, disclosure_versions)
    states = _export_states(payload)
    appearance_counts: dict[str, int] = {}
    for row in payload.get("state_appearances") or []:
        appearance_counts[str(row.get("state_id"))] = \
            appearance_counts.get(str(row.get("state_id")), 0) + 1
    participation_counts: dict[str, int] = {}
    for event in payload.get("events") or []:
        for participant in _event_participants(event):
            ref = str(participant.get("state_ref") or "")
            participation_counts[ref] = participation_counts.get(ref, 0) + 1
    out: list[dict] = []
    for node in reference_graph.get("nodes") or []:
        entry = {
            "node_id": str(node.get("node_id")),
            "occurrence_id": str(node.get("occurrence_id")),
            "role": str(node.get("role")),
            "reference_identity_scope": str(
                node.get("structure_identity_scope")),
            "match_status": "unmatched",
            "matched_state_ids": [],
            "cn_only_state_ids": [],
            "predicted_occurrence_count": 0,
        }
        # S5A-01:先消费参考声明的许可范围,再决定严格档
        scope_permits_strict = entry["reference_identity_scope"] == \
            "strict_structure"
        try:
            ref_strict = strict_identity_of(
                str(node.get("structure_smiles")))
        except ChemicalStateError:
            entry["match_status"] = "reference_structure_unparseable"
            entry["match_status_note"] = (
                "参考图结构不可解析 ⇒ 该节点不参与匹配(样本按坏输入"
                "披露,不静默删除)")
            if v3_disclosure:
                entry["criteria_v3_normalized_identity"] = \
                    _criteria_v3_node_disclosure(
                        entry, states, str(node.get("structure_smiles")))
            out.append(entry)
            continue
        ref_cn = cn_identity(str(node.get("structure_smiles")))
        strict_ids: list[str] = []
        cn_ids: list[str] = []
        for state_id, state in sorted(states.items()):
            pred_strict = state["smiles_isomeric"]
            if pred_strict == ref_strict:
                strict_ids.append(state_id)
            elif ref_cn is not None and state["cn_identity"] == ref_cn:
                cn_ids.append(state_id)
        if strict_ids and scope_permits_strict:
            entry["match_status"] = "strict_structure"
            entry["matched_state_ids"] = sorted(strict_ids)
            entry["predicted_occurrence_count"] = max(
                appearance_counts.get(sid, 0) for sid in strict_ids)
        elif strict_ids or cn_ids:
            # CN 旁证档:CN 相同但严格身份不同/未知,或(S5A-01)参考
            # scope 声明 cn_only/partial/unknown 时内容严格相等也封顶
            # 为旁证 —— 均不计严格命中
            entry["match_status"] = "cn_only"
            entry["cn_only_state_ids"] = sorted(
                set(strict_ids) | set(cn_ids))
            entry["predicted_occurrence_count"] = max(
                participation_counts.get(sid, 0)
                for sid in entry["cn_only_state_ids"])
            if strict_ids and not scope_permits_strict:
                entry["identity_scope_cap"] = {
                    "reference_identity_scope":
                        entry["reference_identity_scope"],
                    "content_strict_equal_state_ids": sorted(strict_ids),
                    "capped_to": "cn_only",
                    "note": (
                        "参考声明 identity_scope=cn_only/partial/unknown"
                        " ⇒ 许可范围封顶:内容严格相等也只作 CN 旁证,"
                        "不授 strict_structure、不进边严格匹配与严格指标"
                        "(S5A-01;冻结稿 §0 旁证不叠加升格)"),
                }
        if v3_disclosure:
            # 档 A 披露轴(仅追加披露块;match_status 与封顶零改动)
            entry["criteria_v3_normalized_identity"] = \
                _criteria_v3_node_disclosure(
                    entry, states, str(node.get("structure_smiles")))
        out.append(entry)
    return out


def match_reference_edges(reference_graph: dict, payload: dict,
                          node_matches: list[dict], *,
                          criteria_version: str = PPV1_CRITERIA_V1) -> list[
        dict]:
    """参考边匹配(确定性;step_scope 分轴;备选不合并;共同产物不被
    报告 K 删除)。

    - 候选事件:反应物/产物侧状态分别命中 from/to 参考节点的严格
      匹配集合;
    - **S5A-03(声明必要 from/to 节点空命中不被 union 吞)**:每个
      声明的必要 from/to 参考节点都必须有**许可的严格命中**才可授
      完整 strict;任一必要节点严格命中集为空 ⇒ 该边不产生严格
      候选(空集合保持为未覆盖 ``unmatched_required_node_```
      ``uncovered``,逐节点机读披露 ``required_node_gaps``,不被
      整侧 union 删除;不能把缩小后的子集标 exact);参与物覆盖
      比较因此消费**完整的声明节点集合**(必要参与物完整清单
      同源闭合);仅 participants 新增而 from/to 未列的多视图案
      不进门禁(表示语义同步属后续 P2 裁定);
    - ``match_status`` ∈ matched_strict | matched_structure_only |
      matched_participant_coverage_partial | unmatched_required_
      node_uncovered | unmatched_reference_coverage |
      unmatched_budget_unexpanded | unmatched —— step_scope 不一致 ⇒
      ``matched_structure_only``(net reaction/elementary step/
      multistep summary 不混作同一边,S5-12);
    - 同父多备选事件逐条列示(A→B 与 A→C 不合并成 B+C 单一事件,
      S5-02);
    - 事件级共同产物参与物完整计数(报告 K/展开宽度不删 C,S5-03);
    - 合法 exact、superset/partial 覆盖披露、共同产物、独立备选
      保持(不新增角色/系数/计量门;系数状态由参考图声明、评测
      侧仅披露不比较);
    - **ppv1-criteria-v2(teacher T-1 裁定;缺省 v1 = 豁免关、本函数
      行为与 ppv1-evaluation-5 字节一致)**:``criteria_version=
      ppv1-criteria-v2`` 时对 superset 失配事件按预注册三谓词做参与
      物豁免评审 —— 全部 extras(两侧)v1_exempt ⇒ 该事件升 exact
      (进 matched_strict)并逐边机读 ``exempted_participants``;
      任一 extras 非 v1_exempt(T1′ 未实施 ⇒ 未声明多余产物恒
      partial)⇒ 维持 superset。豁免只在集合比较轴,身份键/节点
      匹配/step_scope 判定零触碰(**v3 承载同一条路径**:启用
      v3 时本函数行为与 v2 逐位一致,N3/N7 正交性断言)。
    - **ppv1-criteria-v4(§1–§4;只加分支)**:``criteria_version=
      ppv1-criteria-v4`` 时在既有 coverage 三分**之外**追加
      ``criteria_v4`` 判定块与四个新键(``hit_mode_scope`` /
      ``matched_product_hit`` / ``product_hit_partial`` /
      ``product_hit_events``):同一合法事件内 S ∈ R_E 且 P ⊆ T_E,
      P 只取产物侧 ``principal_product`` 节点;**不改写**
      exact/superset/partial_subset(**superset 不得改写为 exact**),
      不启用 v2 豁免(计数 0、批级披露);旧 ``match_status`` 与
      ``matched_events`` 逐位不变;缺省 v1/v2/v3 零新键。
    - **ppv1-criteria-v5(§1–§2;只加分支)**:``criteria_version=
      ppv1-criteria-v5`` 时追加 ``criteria_v5`` 判定块与四个新键
      (``hit_mode_scope`` / ``role_bound_product_hit`` /
      ``product_hit_partial`` / ``role_bound_hit_events``):v4 全部
      条件 + 事件产物侧集合从角色盲 ``T_E`` 收紧为
      ``T_E^principal``(role 恰好 ``principal_product`` 才进集合;
      role 缺失/其它 fail-closed)。合法事件五条件与参考侧目标集合
      逐字沿用 v4(复用 v4 判定块的参考侧与逐事件合法性行);
      v4 块不产生(两版本互不混写)。
    """
    resolve_criteria_version(criteria_version)
    v4_nodes_by_id = (
        {str(node.get("node_id")): node
         for node in reference_graph.get("nodes") or []}
        if criteria_version == PPV1_CRITERIA_V4 else None)
    # ppv1-criteria-v5:独立节点映射(不并入 v4 分支;v4 路径零改动)
    v5_nodes_by_id = (
        {str(node.get("node_id")): node
         for node in reference_graph.get("nodes") or []}
        if criteria_version == PPV1_CRITERIA_V5 else None)
    states = _export_states(payload)
    strict_by_node: dict[str, set[str]] = {}
    node_status_by_id: dict[str, str] = {}
    for entry in node_matches:
        node_status_by_id[entry["node_id"]] = entry["match_status"]
        if entry["match_status"] == "strict_structure":
            strict_by_node[entry["node_id"]] = set(
                entry["matched_state_ids"])
    hypotheses = _hypothesis_payloads(payload)
    events = payload.get("events") or []
    stop_reason = str(((payload.get("endpoint_record") or {}).get(
        "search_stop_reason") or {}).get("primary") or "")
    deferred_count = len(payload.get("deferred_entries") or [])
    coverage = reference_graph.get("coverage_statement") or {}
    not_evaluable_edges = set(
        str(x) for x in coverage.get("not_evaluable_edge_ids") or [])
    known_gaps = list(coverage.get("known_gaps") or [])
    out: list[dict] = []
    for edge in reference_graph.get("edges") or []:
        edge_id = str(edge.get("edge_id"))
        from_ids = [str(x) for x in edge.get("from_node_ids") or []]
        to_ids = [str(x) for x in edge.get("to_node_ids") or []]
        # ---- S5A-03:逐声明必要节点核严格命中;空集不并入 union ----
        required_node_gaps: list[dict] = []
        for side, node_id_list in (("reactant", from_ids),
                                   ("product", to_ids)):
            for node_id in node_id_list:
                if not strict_by_node.get(node_id):
                    required_node_gaps.append({
                        "node_id": node_id,
                        "side": side,
                        "node_match_status": node_status_by_id.get(
                            node_id, "unmatched"),
                        "note": (
                            "声明必要 from/to 参考节点无许可严格命中 ⇒ "
                            "该边不产生严格候选(空集合保持未覆盖,不被"
                            "union 吞掉;S5A-03)"),
                    })
        from_states = set().union(*(
            strict_by_node.get(n, set()) for n in from_ids)) if \
            from_ids else set()
        to_states = set().union(*(
            strict_by_node.get(n, set()) for n in to_ids)) if \
            to_ids else set()
        exact_events: list[dict] = []
        coverage_mismatch_events: list[dict] = []
        structure_only_events: list[dict] = []
        # 批级 tier 单归属计数的逐边累加器(仅 v2 随边披露;occurrences
        # 双 tier 只在本函数评审点完整存在,输出只保留 v1_exempt 披露
        # 子集 —— 批级两 tier 计数须从此处随边带出,P2 2026-10-14;
        # 双键恒在 = 完备二分,零计数也披露)
        edge_tier_counts: dict[str, int] = {
            CRITERIA_TIER_V1_EXEMPT: 0,
            CRITERIA_TIER_NOT_EXEMPT: 0}
        if not required_node_gaps and (not from_ids or from_states) \
                and (to_ids and to_states):
            # 参考侧声明了 from/to 节点但严格匹配集为空 ⇒ 不产生候选
            # (结构未命中不能借空集放行为"任意反应物");S5A-03 之后
            # 该分支只在全部必要节点均有严格命中时到达,from_states/
            # to_states 因此是完整声明集合(非缩小子集)
            for event in sorted(events,
                                key=lambda e: str(e.get("event_id"))):
                participants = _event_participants(event)
                reactants = {str(p.get("state_ref")) for p in participants
                             if str(p.get("side")) == "reactant"}
                products = {str(p.get("state_ref")) for p in participants
                            if str(p.get("side")) == "product"}
                if not (reactants & from_states or
                        (not from_states and reactants)):
                    continue
                if not products & to_states:
                    continue
                hypothesis = hypotheses.get(
                    str(event.get("hypothesis_id"))) or {}
                event_scope = str(hypothesis.get("step_scope")
                                  or "unknown")
                ref_scope = str(edge.get("step_scope") or "unknown")
                # 参与物覆盖(proposed 规则:参考声明完整清单时,
                # 精确 = 事件参与物集合与参考节点集合两侧相等;
                # 事件多出共同产物等 ⇒ 超集;缺声明参与物 ⇒ 部分
                # —— 两种非精确覆盖均单独披露,不计严格匹配)
                coverage = (
                    "exact" if reactants == from_states
                    and products == to_states
                    else ("superset" if
                          from_states <= reactants
                          and to_states <= products
                          else "partial_subset"))
                # ---- ppv1-criteria-v2 豁免评审(缺省 v1:本块零执行,
                # item 字段集与 ppv1-evaluation-5 完全一致=字节不变)----
                exempt_review = None
                if _criteria_exemption_enabled(criteria_version) and \
                        coverage == "superset":
                    exempt_review = evaluate_participant_exemption(
                        payload, _event_payload_body(event), states,
                        hypothesis_id=str(event.get("hypothesis_id") or ""),
                        from_states=from_states, to_states=to_states)
                    for occ in exempt_review["occurrences"]:
                        tier = str(occ.get("tier") or "")
                        edge_tier_counts[tier] = \
                            edge_tier_counts.get(tier, 0) + 1
                    if exempt_review["all_exempt"]:
                        # 全部 extras(两侧)v1_exempt ⇒ 升 exact;
                        # 逐边机读披露(预注册 §五);T1′ 未实施 ⇒
                        # 任一未声明多余产物即维持 partial(fail 方向
                        # 保守,完备二分右侧)
                        coverage = "exact"
                item = {
                    "event_id": str(event.get("event_id")),
                    "event_step_scope": event_scope,
                    "reference_step_scope": ref_scope,
                    "step_scope_consistent": event_scope == ref_scope,
                    "participant_state_refs": sorted({
                        str(p.get("state_ref"))
                        for p in _event_participants(event)}),
                    "coproduct_participants": sorted({
                        str(p.get("state_ref")) for p
                        in _event_participants(event)
                        if str(p.get("role")) == "coproduct"}),
                    "participant_coverage": coverage,
                }
                if exempt_review is not None and \
                        exempt_review["all_exempt"]:
                    item["exempted_participants"] = \
                        exempt_review["exempted_participants"]
                if item["step_scope_consistent"]:
                    if item["participant_coverage"] == "exact":
                        exact_events.append(item)
                    else:
                        coverage_mismatch_events.append(item)
                else:
                    structure_only_events.append(item)
        if exact_events:
            status = "matched_strict"
        elif coverage_mismatch_events:
            status = "matched_participant_coverage_partial"
        elif structure_only_events:
            status = "matched_structure_only"
        elif required_node_gaps:
            # S5A-03:必要参考节点未覆盖 ⇒ 未覆盖分桶(不判错、不冒充
            # 已匹配;逐节点缺口机读披露)
            status = "unmatched_required_node_uncovered"
        elif edge_id in not_evaluable_edges or known_gaps:
            status = "unmatched_reference_coverage"
        elif stop_reason in ("budget_limit", "depth_limit") or \
                deferred_count:
            status = "unmatched_budget_unexpanded"
        else:
            status = "unmatched"
        entry = {
            "edge_id": edge_id,
            "match_status": status,
            "matched_events": exact_events,
            "coverage_mismatch_events": coverage_mismatch_events,
            "structure_only_events": structure_only_events,
            "required_node_gaps": required_node_gaps,
            "reference_participant_node_ids": [
                str(p.get("node_id"))
                for p in edge.get("participants") or []],
            "coproduct_preserved_note": (
                "完整事件保留共同产物参与物(报告 K/展开宽度不删除;"
                "S5-03);同父备选反应各自独立(不合并为单反应,S5-02)"),
        }
        if v4_nodes_by_id is not None:
            # ppv1-criteria-v4:只追加新判定轴;coverage 三分与
            # match_status/matched_events 逐位不变(不改写 superset)
            v4_block = _criteria_v4_edge_product_hit(
                edge, v4_nodes_by_id, payload,
                legacy_match_status=status)
            entry["hit_mode_scope"] = CRITERIA_V4_HIT_MODE_SCOPE
            entry["matched_product_hit"] = v4_block["matched_product_hit"]
            entry["product_hit_partial"] = \
                v4_block["product_hit_partial"]
            entry["product_hit_events"] = v4_block["product_hit_events"]
            entry["criteria_v4"] = v4_block
        if v5_nodes_by_id is not None:
            # ppv1-criteria-v5:只追加新判定轴;coverage 三分、match_status
            # 与 matched_events 逐位不变(与 v4 同一 coverage 事实面)
            v5_block = _criteria_v5_edge_product_hit(
                edge, v5_nodes_by_id, payload,
                legacy_match_status=status)
            entry["hit_mode_scope"] = CRITERIA_V5_HIT_MODE_SCOPE
            entry["role_bound_product_hit"] = \
                v5_block["role_bound_product_hit"]
            entry["product_hit_partial"] = \
                v5_block["product_hit_partial"]
            entry["role_bound_hit_events"] = \
                v5_block["role_bound_hit_events"]
            entry["criteria_v5"] = v5_block
        if _criteria_exemption_enabled(criteria_version):
            # 逐边 tier 计数(机器披露;批级块由此汇总;v1 零新键)
            entry["criteria_v2_tier_counts"] = dict(
                sorted(edge_tier_counts.items()))
        out.append(entry)
    return out


def _parse_interval_literal(value) -> dict | None:
    """把 ``lo-hi`` 字符串(含负 lo,如 ``-5-10``)解析为区间 dict。

    解析失败(非两侧数值/多段)⇒ None(调用方按登记映射的定性标签
    路径处理,不发明换算)。注册的映射限定:与冻结 Requirement 的
    区间表示 ``{"lo", "hi"}`` 同形。
    """
    if isinstance(value, dict):
        return None
    text = str(value).strip()
    if not text:
        return None
    negative = text.startswith("-")
    if negative:
        text = text[1:]
    parts = text.split("-")
    if negative and parts:
        parts = ["-" + parts[0]] + parts[1:]
    if len(parts) != 2:
        return None
    try:
        lo, hi = float(parts[0]), float(parts[1])
    except (ValueError, TypeError):
        return None
    return {"lo": lo, "hi": hi}


def _parse_number_literal(value):
    """数值字符串 → int/float;否则 None(不做任何字符串语义猜测)。"""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return value
    text = str(value).strip()
    if not text:
        return None
    try:
        number = float(text)
    except (ValueError, TypeError):
        return None
    return int(number) if number.is_integer() else number


def _map_condition_scope_to_requirement(
        requirement: dict) -> tuple[dict | None, list[dict]]:
    """S5A-02 登记映射:ConditionScope → 冻结 ``Requirement`` 构造参数。

    登记的映射限定(与复审对照口径一致;原 ConditionScope 全文保存在
    参考图中不回写、不重解释):

    - key 必须在冻结条件键集(CONDITION_KEYS)内,否则**表示能力
      缺失**(机读披露 ``condition_key_not_representable``,分类进
      unknown/unsupported 族,不判冲突/相容);
    - 区间键(pH/temperature_C):``lo-hi`` 字符串规范为 ``{lo,hi}``
      区间(value_basis=range)、单个数值规范为点值(point)、其余
      字符串按定性标签(label;首版注册表为空 ⇒ 冻结侧 unknown);
    - 物种/枚举/matrix 键:字符串值按实体/枚举身份比对(entity);
      非字符串值不映射(表示能力缺失);
    - 声明单位参与消费(**S5A-02 r2:单位支持能力在本映射首消费处
      决定**;要求侧与事实侧分立):
      - 要求值恒为键规范单位(冻结 ``build_requirement`` 契约,无
        unit 形参):空 unit ⇒ 按键规范单位约定消费
        (canonical-by-key 默认,**合法不降档**,机读披露
        ``requirement_unit_not_declared``/reason=
        ``requirement_unit_canonical_by_key``);显式规范 unit
        (temperature_C 的 °C/C/celsius;pH 的 pH/dimensionless)
        ⇒ 合法;
      - 显式非规范 unit(温度给 K/F)或无量纲键声明 unit(物种/
        枚举/matrix 键给 mg/L)⇒ **无合法冻结表示** ⇒ 返回 None
        (沿既有不支持路线:分类进 unknown/unsupported 族),机读
        披露 ``requirement_unit_noncanonical``/
        ``requirement_unit_unexpected`` 保留原 key/unit/value/
        allowed_units/原因 —— 不丢弃单位后授 compatible/conflict、
        不做 K/F 换算、不猜测单位语义;
      - 事实侧来源单位三态(canonical/source_unit_unknown/unit_
        mismatch)由冻结同源 ``_assess_requirement`` 裁决,不在本
        映射(事实 unit 原样入 ``build_condition_fact``);
    - requirement.status=known_absent 无冻结负要求表示 ⇒ 单列
      ``requirement_status_not_representable``(不伪称冻结矛盾);
    - source_refs 原样映射(冻结侧:necessity 无来源 ⇒ unknown);
    - subject_scenario_ref → 评估场景(事实按冻结适用性规则过滤,
      场景/阶段不由字符串首条事实替代)。

    返回 (build_requirement 关键字参数 | None, 机读披露列表);
    None = 该 ConditionScope 在冻结契约下无合法表示。
    """
    key = str(requirement.get("key") or "")
    disclosures: list[dict] = []
    if key not in CONDITION_KEYS:
        disclosures.append({
            "kind": "condition_key_not_representable",
            "key": key,
            "frozen_condition_keys": sorted(CONDITION_KEYS),
            "note": ("冻结条件键集之外的条件键无冻结 Requirement 表示"
                     " ⇒ unknown/unsupported 族,不判冲突/相容"),
        })
        return None, disclosures
    level = str(requirement.get("required") or "essential")
    if level not in (REQUIREMENT_ESSENTIAL, REQUIREMENT_PREFERENCE):
        disclosures.append({
            "kind": "requirement_level_not_representable",
            "level": level,
        })
        return None, disclosures
    raw_value = requirement.get("value_or_interval")
    kwargs: dict = {
        "key": key,
        "level": level,
        "source_refs": [str(x) for x in
                        (requirement.get("source_refs") or [])],
    }
    if key in INTERVAL_CONDITION_KEYS:
        if isinstance(raw_value, dict):
            kwargs["value"] = raw_value
            kwargs["value_basis"] = VALUE_BASIS_RANGE
        elif (isinstance(raw_value, (int, float))
              and not isinstance(raw_value, bool)):
            kwargs["value"] = raw_value
            kwargs["value_basis"] = VALUE_BASIS_POINT
        else:
            interval = _parse_interval_literal(raw_value)
            if interval is not None:
                kwargs["value"] = interval
                kwargs["value_basis"] = VALUE_BASIS_RANGE
            elif _parse_number_literal(raw_value) is not None:
                kwargs["value"] = _parse_number_literal(raw_value)
                kwargs["value_basis"] = VALUE_BASIS_POINT
            else:
                kwargs["value"] = raw_value
                kwargs["value_basis"] = VALUE_BASIS_LABEL
    else:
        if isinstance(raw_value, str) and raw_value:
            kwargs["value"] = raw_value
            kwargs["value_basis"] = VALUE_BASIS_ENTITY
        else:
            disclosures.append({
                "kind": "requirement_value_not_representable",
                "key": key,
                "value": repr(raw_value),
                "note": ("非区间键的冻结 Requirement 只接受字符串实体"
                         "/枚举值;该值形状无冻结表示 ⇒ unknown 族"),
            })
            return None, disclosures
    # ---- S5A-02 r2:单位支持能力在映射首消费处决定(评审 R2 §4) ----
    # 显式非规范/无量纲键声明单位无法合法映射 ⇒ None(既有不支持
    # 路线);空单位 ⇒ canonical-by-key 默认合法(不降档)。
    unit = str(requirement.get("unit") or "")
    allowed_units = CONDITION_KEY_UNITS.get(key)
    if allowed_units is None:
        if unit:
            disclosures.append({
                "kind": "requirement_unit_unexpected",
                "key": key,
                "unit": unit,
                "value": repr(raw_value),
                "reason": "requirement_unit_unexpected",
                "note": ("该条件键无量纲(物种/枚举/matrix 键无单位"
                         "语义);显式声明单位 ⇒ 无合法冻结表示 ⇒"
                         " unknown/unsupported 族,机读保留原"
                         " unit/value/key(不猜测单位语义、不判"
                         " 相容/冲突)"),
            })
            return None, disclosures
    else:
        if unit and unit not in allowed_units:
            disclosures.append({
                "kind": "requirement_unit_noncanonical",
                "key": key,
                "unit": unit,
                "value": repr(raw_value),
                "allowed_units": sorted(allowed_units),
                "reason": "requirement_unit_noncanonical",
                "note": ("冻结要求值恒为键规范单位且首版无换算;显式"
                         "非规范单位(如温度给 K/F)无法合法映射 ⇒"
                         " unknown/unsupported 族,机读保留原"
                         " unit/value/key(不做换算、不按数值直比、"
                         "不判相容/冲突)"),
            })
            return None, disclosures
        if not unit and "" not in allowed_units:
            disclosures.append({
                "kind": "requirement_unit_not_declared",
                "key": key,
                "unit": unit,
                "value": repr(raw_value),
                "canonical_units": sorted(allowed_units),
                "reason": "requirement_unit_canonical_by_key",
                "note": ("要求值恒为键规范单位(冻结契约);空单位 ⇒"
                         " 按键规范单位约定消费(canonical-by-key"
                         " 默认,合法不降档;事实侧来源单位三态不受"
                         " 本约定影响)"),
            })
    return kwargs, disclosures


def _build_frozen_facts(facts: list[dict]) -> tuple[list, list[dict]]:
    """S5A-02 登记映射:导出/输入侧条件事实 → 冻结 ``ConditionFact``。

    逐条 ``build_condition_fact``(冻结构造器:键/枚举/区间形状/有限性
    fail-closed 校验);表示不了的条目**机读披露后跳过**(该条不参与
    评估 ⇒ 同键其余事实/缺事实按冻结侧语义保守处理,不静默删、不
    伪造)。origin/source_ref/scenario/phase 原样映射(适用场景/阶段
    由冻结侧 ``_applicable`` 过滤规则消费)。
    """
    frozen: list = []
    disclosures: list[dict] = []
    for fact in facts:
        if not isinstance(fact, dict):
            disclosures.append({
                "kind": "condition_fact_not_representable",
                "note": f"条件事实非对象:{type(fact).__name__}"})
            continue
        try:
            frozen.append(build_condition_fact(
                key=str(fact.get("key") or ""),
                value=fact.get("value"),
                unit=str(fact.get("unit") or ""),
                status=str(fact.get("status") or "unknown"),
                origin=str(fact.get("origin") or "user_input"),
                source_ref=str(fact.get("source_ref") or ""),
                subject_scenario_ref=str(
                    fact.get("subject_scenario_ref") or ""),
                phase_id=str(fact.get("phase_id") or "")))
        except Exception as exc:  # noqa: BLE001 —— 机读披露,不崩溃
            disclosures.append({
                "kind": "condition_fact_not_representable",
                "key": str(fact.get("key") or ""),
                "error": f"{type(exc).__name__}: {exc}"[:200],
                "note": ("该条件事实在冻结契约下无合法表示 ⇒ 跳过"
                         "(缺该事实 ⇒ 冻结侧按缺事实/未知保守处理)"),
            })
    return frozen, disclosures


def _classify_condition_requirement_detailed(
        requirement: dict, facts: list[dict]) -> dict:
    """S5A-02:ConditionScope × 条件事实 → 同源条件分类(详细结果)。

    消费**冻结同源规则**(path_context 的 ``aggregate_environment_``
    ``fit``/``_assess_requirement`` —— 事实侧单位三态、实体/数值/
    异值 absence、同键相反事实保守 unknown(B2 更正,S5a r3 复审
    R3 §5 限定:known×unknown 混合**仅物种键**按冻结侧实体已知
    事实裁决(present ⇒ compatible、absent ⇒ essential_conflict);
    **非物种键任一适用 unknown 事实 ⇒ condition_unknown**;合法
    公共链的 unknown 事实经 checked ``build_condition_fact`` 值清
    None 不带身份,两序结果一致(无合法链顺序差异);直接
    dataclass 绕过 checked 构造器或 restore 低层直构的次序语义是
    已登记支持边界 P2,另列不属本契约,不以文字宣称首消费绑定
    已通过)、necessity 来源、适用场景/阶段、声明
    value_basis 全部由同一实现裁决,评测侧不再另写字符串首条规则):

    - 冻结 satisfied → ``compatible``;conflict → ``essential_conflict``
      (essential)/``preference_unsatisfied``(preference,经同源值轴
      探针拷贝,preference 永不门禁);unknown → ``condition_unknown``
      (携带冻结 reason 码,机读);
    - **S5A-02 r2**:要求侧显式非规范单位/无量纲键声明单位在
      ConditionScope→Requirement 映射首消费处判**无合法表示** ⇒
      ``condition_unknown`` + reason ``requirement_unit_not_
      representable`` + 机读披露保留原 unit/value/key/原因(不丢弃
      单位后授 compatible/conflict);空要求单位按键规范单位约定
      (canonical-by-key 默认,合法不降档);
    - requirement.status=known_absent → 单列
      ``requirement_status_not_representable``(无冻结负要求表示,
      不伪称冻结矛盾);
    - 冻结键集外的键 → ``condition_unsupported_key``(unknown 族);
    - 要求/事实个别条目无冻结表示 ⇒ 机读披露,分类保守 unknown 族;
    - 适用场景轴:要求 subject_scenario_ref 非空且**全部**同键事实
      场景非空且不同 ⇒ ``scenario_transition_changed``(S5-15 披露
      桶保留;不再首条说了算);否则场景过滤交冻结侧规则。
    """
    key = str(requirement.get("key") or "")
    status = str(requirement.get("status") or "unknown")
    disclosures: list[dict] = []
    base = {"key": key,
            "required": str(requirement.get("required") or "essential")}
    if key not in CONDITION_KEYS:
        _, map_disc = _map_condition_scope_to_requirement(requirement)
        return {**base,
                "classification": "condition_unsupported_key",
                "frozen_status": None,
                "reason": "condition_key_not_representable",
                "mapping_disclosures": map_disc}
    if status == "known_absent":
        return {**base,
                "classification": "requirement_status_not_representable",
                "frozen_status": None,
                "reason": (
                    "requirement_status_known_absent_not_representable:"
                    "冻结 Requirement 无负要求表示(不推断负要求、"
                    "不伪称冻结矛盾;单列机读披露,S5A-02)"),
                "mapping_disclosures": [{
                    "kind": "requirement_status_not_representable",
                    "key": key,
                    "status": status,
                    "note": ("ConditionScope.status=known_absent 在冻结"
                             "契约下无直接映射;参考 schema 语义待用户/"
                             "teacher 裁定,评测侧不代定"),
                }]}
    if status != "known_present":
        return {**base,
                "classification": "condition_unknown",
                "frozen_status": None,
                "reason": "requirement_status_unknown",
                "mapping_disclosures": []}
    # ---- 场景轴(消费全部同键事实;S5-15 桶保留) ----
    matching = [f for f in facts
                if isinstance(f, dict) and str(f.get("key")) == key]
    ref_scenario = str(requirement.get("subject_scenario_ref") or "")
    if ref_scenario and matching and all(
            str(f.get("subject_scenario_ref") or "")
            and str(f.get("subject_scenario_ref") or "") != ref_scenario
            for f in matching):
        return {**base,
                "classification": "scenario_transition_changed",
                "frozen_status": None,
                "reason": "subject_scenario_mismatch_all_matching_facts",
                "mapping_disclosures": []}
    # ---- 登记映射 → 冻结 Requirement ----
    kwargs, disclosures = _map_condition_scope_to_requirement(requirement)
    if kwargs is None:
        # 无法合法映射 ⇒ 既有不支持路线(unknown 族);单位失败单独
        # 机读 reason 码(评审 R2 §4:不能丢 unit 后授相容/冲突)
        unit_kinds = ("requirement_unit_noncanonical",
                      "requirement_unit_unexpected")
        reason = ("requirement_unit_not_representable"
                  if any(d.get("kind") in unit_kinds
                         for d in disclosures)
                  else "requirement_not_representable")
        return {**base,
                "classification": "condition_unknown",
                "frozen_status": None,
                "reason": reason,
                "mapping_disclosures": disclosures}
    try:
        frozen_req = build_requirement(**kwargs)
    except Exception as exc:  # noqa: BLE001 —— 机读披露,不崩溃
        disclosures.append({
            "kind": "requirement_not_representable",
            "key": key,
            "error": f"{type(exc).__name__}: {exc}"[:200]})
        return {**base,
                "classification": "condition_unknown",
                "frozen_status": None,
                "reason": "requirement_not_representable",
                "mapping_disclosures": disclosures}
    frozen_facts, fact_disclosures = _build_frozen_facts(facts)
    disclosures.extend(fact_disclosures)
    level = kwargs["level"]
    if level == REQUIREMENT_PREFERENCE:
        # preference 永不门禁(冻结侧 N/A + note);满足轴经同一冻结
        # 值规则的同源探针拷贝(essential 拷贝仅用于读值轴状态,不改
        # 门禁语义):satisfied → compatible / conflict →
        # preference_unsatisfied / unknown → condition_unknown
        probe = build_requirement(
            key=kwargs["key"], level=REQUIREMENT_ESSENTIAL,
            value=kwargs.get("value"),
            value_basis=kwargs.get("value_basis"),
            source_refs=kwargs.get("source_refs"))
        assessment = aggregate_environment_fit(
            facts=frozen_facts, requirements=[probe],
            declared_scope=[key], scenario_ref=ref_scenario, phase_id="")
        row = assessment.per_requirement[0]
        if row["status"] == SATISFIED:
            classification = "compatible"
        elif row["status"] == CONFLICT:
            classification = "preference_unsatisfied"
        else:
            classification = "condition_unknown"
        return {**base,
                "classification": classification,
                "frozen_status": row["status"],
                "reason": str(row.get("reason") or ""),
                "mapping_disclosures": disclosures,
                "preference_not_gating": True}
    assessment = aggregate_environment_fit(
        facts=frozen_facts, requirements=[frozen_req],
        declared_scope=[key], scenario_ref=ref_scenario, phase_id="")
    row = assessment.per_requirement[0]
    if row["status"] == SATISFIED:
        classification = "compatible"
    elif row["status"] == CONFLICT:
        classification = "essential_conflict"
    elif row["status"] == NOT_APPLICABLE:
        classification = "condition_not_gating"
    elif row["status"] == UNKNOWN:
        classification = "condition_unknown"
    else:  # pragma: no cover —— 冻结状态枚举之外的防御
        classification = "condition_unknown"
    return {**base,
            "classification": classification,
            "frozen_status": row["status"],
            "reason": str(row.get("reason") or ""),
            "mapping_disclosures": disclosures}


def classify_condition_requirement(requirement: dict,
                                   facts: list[dict]) -> str:
    """条件分类(§9.5;conflict/unknown/compatible/分桶,不互相混算)。

    S5A-02:评测侧条件分类**沿冻结同源规则**裁决(不再另写字符串
    首条简化规则):

    - essential + 冻结侧 conflict(同值字符串 known_absent、封闭枚举
      不匹配、点/区间不相交)⇒ ``essential_conflict``(S5-14;unknown
      不混入冲突);
    - 数值/区间 known_absent、异值字符串 known_absent、异实体缺席、
      单位未知/不匹配、多事实矛盾、necessity 无来源、matrix 未注册
      标签 ⇒ 冻结侧 unknown ⇒ ``condition_unknown``(S5-13:必要项
      缺失/不可判报 unknown,不报 compatible 也不报 conflict);
    - 要求侧显式非规范单位(温度 K/F)或无量纲键声明单位(物种键
      mg/L)⇒ 映射首消费判无合法表示 ⇒ ``condition_unknown``
      (S5A-02 r2:reason=``requirement_unit_not_representable``,
      机读保留原 unit/value/key;空要求单位按键规范单位约定
      canonical-by-key 默认合法不降档);
    - preference 不满足 ⇒ ``preference_unsatisfied``(非冲突;经同源
      值轴探针,preference 永不门禁);
    - 冻结 satisfied ⇒ ``compatible``(相容是给定事实集的结论,不核
      事实真实性);
    - 要求挂接的 subject scenario 与事实场景不同 ⇒
      ``scenario_transition_changed``;
    - 冻结键集外的键 ⇒ ``condition_unsupported_key``;要求侧
      status=known_absent ⇒ ``requirement_status_not_representable``
      (单列,不伪称冻结矛盾);
    - 历史来源条件由 ``source_conditions_preserved`` 原样披露
      (S5-15,不改写为当前事实 —— 不在本分类器内)。
    """
    return _classify_condition_requirement_detailed(
        requirement, facts)["classification"]


def classify_sample_conditions(reference_graph: dict,
                               payload: dict) -> dict:
    """样本级条件轴:参考条件要求 × 预测条件事实(来自导出 contexts
    的 condition_facts;S4 公开字段)分桶 + 历史来源条件原样保留。

    S5A-02:逐条消费 ``_classify_condition_requirement_detailed``
    (ConditionScope → 冻结 Requirement 登记映射 + path_context 同源
    规则;携带冻结 reason 码与机读映射披露)。"""
    facts: list[dict] = []
    for context in payload.get("contexts") or []:
        body = context.get("payload") or {}
        if isinstance(body, dict):
            facts.extend(x for x in body.get("condition_facts") or []
                         if isinstance(x, dict))
    buckets: dict[str, int] = {}
    details: list[dict] = []
    disclosures: list[dict] = []
    requirements: list[dict] = []
    for node in reference_graph.get("nodes") or []:
        requirements.extend(node.get("condition_scope") or [])
    for edge in reference_graph.get("edges") or []:
        requirements.extend(edge.get("condition_requirements") or [])
    for requirement in requirements:
        result = _classify_condition_requirement_detailed(
            requirement, facts)
        status = result["classification"]
        buckets[status] = buckets.get(status, 0) + 1
        details.append({
            "key": result["key"],
            "required": result["required"],
            "classification": status,
            "frozen_status": result.get("frozen_status"),
            "reason": result.get("reason") or "",
        })
        for disclosure in result.get("mapping_disclosures") or []:
            disclosures.append({
                "key": result["key"],
                "required": result["required"],
                **disclosure})
    # S5-15:历史来源条件原样保留(不改写为当前场景事实)
    source_conditions_preserved: list[dict] = []
    for record in reference_graph.get("provenance_manifest") or []:
        if record.get("source_conditions"):
            source_conditions_preserved.append({
                "provenance_id": str(record.get("provenance_id")),
                "source_conditions": record.get("source_conditions"),
            })
    return {
        "buckets": dict(sorted(buckets.items())),
        "details": sorted(details, key=lambda d: (
            d["key"], d["required"], d["classification"])),
        "condition_facts_consumed": sorted(
            {str(f.get("key")) for f in facts}),
        "mapping_disclosures": sorted(
            disclosures, key=lambda d: (
                d.get("key") or "", d.get("kind") or "",
                str(d.get("error") or ""))),
        "source_conditions_preserved": source_conditions_preserved,
        "note": ("unknown 不计为冲突;满足不升级为全路径相容;"
                 "分类沿冻结同源规则(单位三态/absence 保守 unknown/"
                 "同键相反事实/necessity 来源;S5A-02);要求侧显式"
                 "非规范单位/无量纲键声明单位降 unknown/unsupported"
                 "族(S5A-02 r2:空单位按键规范单位约定合法);历史"
                 "来源条件保留原文"
                 "(S5-13/14/15)"),
    }


def check_endpoint_claims(endpoint_record: dict,
                          reference_annotations: list[dict]) -> dict:
    """终点/矿化声明检查(§9.6;消费 S4 四分账,分账独立不互推)。

    - ``search_stop_reason`` ≠ 终点:停止原因在场而评估却非 unknown
      且无证据 ⇒ ``stop_reason_mislabeled_as_endpoint``(S5-18);
    - 矿化声明须有根碳账核查范围 + 来源层直报证据
      (``mineralization_claim_without_root_carbon_account``,
      S5-17:仅提出 CO₂ 无根碳账不得判矿化);
    - ``metabolic_handoff`` ≠ 矿化(错叫 ⇒ 记误声明类型);
    - 上游 unresolved 依赖继承 ⇒ 末端不得升格为 supported_*
      (S5-19:recorded 不洗白);
    - 备选路线 CO₂ 不合并(``co2_aggregated`` 标记检查);
    - 模型推演不得声称已观察终点(``endpoint_evidence`` 空/模型
      来源 ⇒ ``observed_endpoint_claimed_from_model_only``)。
    """
    assessment = str(endpoint_record.get("chemical_endpoint_assessment")
                     or "unknown")
    stop_reason = str((endpoint_record.get("search_stop_reason") or {})
                      .get("primary") or "")
    evidence = endpoint_record.get("endpoint_evidence") or []
    bookkeeping = endpoint_record.get("bookkeeping") or {}
    inherited = endpoint_record.get("inherited_unresolved_dependencies") \
        or []
    misclaims: list[dict] = []
    if assessment != "unknown" and stop_reason in STOP_REASONS and \
            not evidence:
        misclaims.append({
            "type": "stop_reason_mislabeled_as_endpoint",
            "stop_reason": stop_reason,
            "assessment": assessment})
    if assessment == "supported_mineralization":
        root_scope = any(
            str((e or {}).get("root_carbon_fate_check_scope") or "")
            for e in evidence)
        if not root_scope or not evidence:
            misclaims.append({
                "type": "mineralization_claim_without_root_carbon_account",
                "note": "仅提出 CO₂、无根碳账与来源层终点证据 ⇒ 不得判"
                        "矿化(S5-17)"})
        if any(str((e or {}).get("evidence_basis") or "") ==
               "metabolic_handoff" for e in evidence):
            misclaims.append({
                "type": "metabolic_handoff_mislabeled_as_mineralization",
                "note": "metabolic_handoff 不等于矿化"})
    if assessment in ("supported_terminal_transformation_product",
                      "supported_mineralization") and inherited:
        unresolved = [d for d in inherited
                      if isinstance(d, dict) and str(
                          d.get("status") or "unresolved") == "unresolved"]
        if unresolved:
            misclaims.append({
                "type": "unresolved_dependency_promoted",
                "unresolved_count": len(unresolved),
                "note": "上游 unresolved 依赖继承到末端,不被 recorded "
                        "洗白(S5-19)"})
    if assessment in ("supported_terminal_transformation_product",
                      "supported_mineralization") and \
            all(str((e or {}).get("evidence_basis") or "")
                .startswith("model") for e in evidence) and evidence:
        misclaims.append({
            "type": "observed_endpoint_claimed_from_model_only",
            "note": "仅有模型推演不得声称已观察终点"})
    if bool(bookkeeping.get("co2_aggregated")):
        misclaims.append({
            "type": "co2_merged_across_alternative_routes",
            "note": "不同备选路线的 CO₂ 不得合并后声称同一路径矿化"})
    annotation_checks = []
    for annotation in reference_annotations or []:
        annotation_checks.append({
            "annotation_id": str(annotation.get("annotation_id")),
            "reference_assessment": str(
                annotation.get("endpoint_assessment")),
            "predicted_assessment": assessment,
            "agrees": str(annotation.get("endpoint_assessment"))
            == assessment,
        })
    return {
        "predicted_assessment": assessment,
        "search_stop_reason": stop_reason,
        "stop_endpoint_separated": (
            "search_stop_reason 与 chemical_endpoint_assessment 分账"
            "独立;停止原因永不映射为终点(S5-18)"),
        "misclaims": misclaims,
        "annotation_checks": sorted(
            annotation_checks, key=lambda a: a["annotation_id"]),
    }


def budget_omission_from_export(payload: dict) -> dict:
    """预算导致漏展开(§9.8;单独报告,不静默从分母删除,不计化学错误)。

    分桶:action_budget / depth_budget / product_expansion_width /
    per_parent_alternative_limit / retrieval_limit / model_request_
    limit / deferred_not_activated / blocked_objects / awaiting_
    prediction / other_explicit_stop。
    """
    stop_reason = str(((payload.get("endpoint_record") or {}).get(
        "search_stop_reason") or {}).get("primary") or "")
    buckets: dict[str, int] = {
        "action_budget": 1 if stop_reason == "budget_limit" else 0,
        "depth_budget": 1 if stop_reason == "depth_limit" else 0,
        "awaiting_prediction": 1 if stop_reason == "awaiting_prediction"
        else 0,
        "other_explicit_stop": 1 if stop_reason in (
            "no_local_candidate", "exhausted_search", "user_stop")
        else 0,
    }
    deferred = payload.get("deferred_entries") or []
    buckets["deferred_not_activated"] = len(deferred)
    buckets["blocked_objects"] = len(payload.get("blocked_entries") or [])
    budget = (payload.get("budget") or {}).get("budget_snapshot") or {}
    scoped = budget.get("scoped") or {}
    for scope_key, rows in sorted(scoped.items()):
        if not isinstance(rows, dict):
            continue
        for limit_key, info in sorted(rows.items()):
            if not isinstance(info, dict):
                continue
            if int(info.get("used") or 0) >= int(info.get("max") or 0) \
                    and int(info.get("max") or 0) >= 0 and \
                    str(scope_key) != "run_level":
                bucket = {
                    "max_product_expansion_width":
                        "product_expansion_width",
                    "max_alternative_hypotheses_per_parent":
                        "per_parent_alternative_limit",
                    "max_retrievals_per_parent": "retrieval_limit",
                    "max_attempts_per_hypothesis": "attempt_limit",
                }.get(str(limit_key), "scoped_limit_reached")
                buckets[bucket] = buckets.get(bucket, 0) + 1
    return {
        "buckets": dict(sorted(buckets.items())),
        "stop_reason": stop_reason,
        "deferred_entries": sorted(
            str(d.get("action_id")) for d in deferred),
        "note": ("预算漏展开单独报告;不计为模型化学错误,也不从科学"
                 "命中分母无声删除(分母定义 TBD 用户/teacher 裁定)"),
    }


def depth_metrics_from_export(payload: dict) -> dict:
    """按深度表现(§9.7:第 1/2/3+ 条反应边 + 超出深度预算未展开;
    样本量不足 ⇒ insufficient_sample,不合并成总分)。"""
    depths: dict[str, int] = {}
    unknown_depth_events: list[str] = []
    for report in payload.get("audit_production_reports") or []:
        body = report.get("production_payload") or {}
        submitted = body.get("submitted") or {}
        event_id = str(submitted.get("event_id") or "")
        if not event_id:
            continue
        depth = body.get("child_depth")
        if not isinstance(depth, int):
            unknown_depth_events.append(event_id)
            continue
        depths[event_id] = depth
    stop_reason = str(((payload.get("endpoint_record") or {}).get(
        "search_stop_reason") or {}).get("primary") or "")
    buckets = {
        "depth_1": sum(1 for d in depths.values() if d <= 1),
        "depth_2": sum(1 for d in depths.values() if d == 2),
        "depth_3_plus": sum(1 for d in depths.values() if d >= 3),
        "beyond_depth_budget": 1 if stop_reason == "depth_limit" else 0,
        "events_with_unknown_depth": len(unknown_depth_events),
    }
    insufficient = sorted(
        bucket for bucket, count in buckets.items() if count == 0)
    return {
        "buckets": dict(sorted(buckets.items())),
        "event_depths": dict(sorted(depths.items())),
        "insufficient_sample_buckets": insufficient,
        "note": ("样本量不足的桶标记 insufficient_sample,不合并成看似"
                 "稳定的总分;最低样本量 TBD 用户/teacher 裁定"),
    }


def unknown_partial_summary_from_export(payload: dict) -> dict:
    """unknown/partial/conditional 保留(§14.1/S5-16:不计 confirmed
    也不自动计错误)。"""
    conditional_events = 0
    unknown_checks = 0
    for report in payload.get("audit_production_reports") or []:
        body = report.get("production_payload") or {}
        admission = (body.get("admission") or {}).get("disposition") or ""
        if admission == "retain_conditional":
            conditional_events += 1
        audit = body.get("audit") or {}
        unknown_checks += sum(
            1 for check in audit.get("checks") or []
            if str(check.get("status")) == "unknown")
    unresolved_outcomes = sum(
        1 for outcome in payload.get("expansion_outcomes") or []
        if "unresolved" in str(
            (outcome.get("outcome_payload") or {}).get("outcome") or ""))
    return {
        "conditional_admission_events": conditional_events,
        "audit_unknown_checks": unknown_checks,
        "unresolved_outcomes": unresolved_outcomes,
        "note": ("unknown/partial/conditional 如实保留:不计 confirmed,"
                 "也不自动计为错误(S5-16);分母处理 TBD"),
    }


def outside_reference_edges_from_export(payload: dict,
                                         matched_event_ids: set[str]
                                         ) -> dict:
    """参考外未验证边(§9.4:拆分有依据/仅模型/无可审计依据)。"""
    buckets = {
        "outside_reference_with_allowed_inference_basis": 0,
        "outside_reference_model_only": 0,
        "outside_reference_no_auditable_basis": 0,
        "reference_coverage_indeterminate": 0,
    }
    events = payload.get("events") or []
    hypothesis_provenance = {}
    for row in payload.get("hypotheses") or []:
        body = row.get("payload")
        if isinstance(body, str):
            import json as _json
            try:
                body = _json.loads(body)
            except (ValueError, TypeError):
                body = {}
        hypothesis_provenance[str(row.get("hypothesis_id"))] = [
            str(x) for x in ((body or {}).get("provenance_refs")
                             or [])] + [
            str(x) for x in ((body or {}).get("support_group_refs")
                             or [])]
    audited_events = set()
    for report in payload.get("audit_production_reports") or []:
        body = report.get("production_payload") or {}
        event_id = str((body.get("submitted") or {}).get("event_id") or "")
        if event_id:
            audited_events.add(event_id)
    for event in events:
        event_id = str(event.get("event_id"))
        if event_id in matched_event_ids:
            continue
        refs = hypothesis_provenance.get(
            str(event.get("hypothesis_id")), [])
        if event_id not in audited_events:
            buckets["outside_reference_no_auditable_basis"] += 1
        elif refs:
            buckets["outside_reference_with_allowed_inference_basis"] += 1
        else:
            buckets["outside_reference_model_only"] += 1
    return {
        "buckets": buckets,
        "note": ("参考图可能不完备/unseen 轨道允许未见边:该指标不直接"
                 "等同错误率;参考覆盖不足无法判断的边在 coverage_report"
                 " 披露"),
    }


# ---------------------------------------------------------------- 评测主流程


def native_export_reader_from_ledger(ledger, run_dir: str | Path):
    """S4 公开入口消费契约(§3.1):返回导出条目读取器。

    读取器调用 ``read_native_export``(首消费:integrity → 版本门 →
    digest → 权威引用 → 策略 → staleness;fail-closed)。合成 run 的
    产物必须走真实链路生成,不得造假导出对象。
    """

    def reader(entry: dict) -> dict:
        return read_native_export(ledger, run_dir,
                                  str(entry.get("export_digest")))

    return reader


def _root_states_of_export(payload: dict) -> set[str]:
    """导出根状态(paths origin=root 的 product_state_ref)。"""
    roots: set[str] = set()
    for path in payload.get("paths") or []:
        if str(path.get("origin")) == "root":
            roots.add(str(path.get("product_state_ref") or ""))
    return roots


def _manifest_qid_map(evaluation_input: dict) -> dict[str, str]:
    """图侧 qid 声明(graph_id → qid;仅统计显式声明条目)。

    evaluation-4:qid 的图侧权威来源是 ``reference_graph_manifest`` 条目
    的 ``qid`` 子字段(声明时已过非空/唯一校验);一致性核(该 qid
    必须出现在图 ``root_entity.source_refs``,转换规则 §2.2)由
    ``evaluate_scientific`` 在图装载后统一执行。
    """
    out: dict[str, str] = {}
    for entry in evaluation_input.get("reference_graph_manifest") or []:
        qid = entry.get("qid")
        if qid is None:
            continue
        out[str(entry.get("reference_graph_id"))] = str(qid)
    return out


def _export_qid_map(evaluation_input: dict) -> dict[str, str]:
    """导出侧 qid 声明(digest → qid;仅统计显式声明条目)。

    evaluation-4:评测输入的 run↔qid 映射落点——导出条目同时声明
    ``qid`` 与 ``run_id``;``run_id`` 与 read_native_export 返回
    payload 的权威 ``run_id`` 的绑定核验在导出装载处执行。
    """
    out: dict[str, str] = {}
    for entry in evaluation_input.get("native_path_exports") or []:
        qid = entry.get("qid")
        if qid is None:
            continue
        out[str(entry.get("export_digest"))] = str(qid)
    return out


def _export_entry_order(evaluation_input: dict) -> list[str]:
    """导出 digest 的评测输入清单序(显式清单序;去重保序)。"""
    order: list[str] = []
    seen: set[str] = set()
    for entry in evaluation_input.get("native_path_exports") or []:
        digest = str(entry.get("export_digest"))
        if digest not in seen:
            seen.add(digest)
            order.append(digest)
    return order


def _pair_exports_to_samples(graphs: dict[str, dict],
                             export_payloads: dict[str, dict],
                             export_entry_order: list[str],
                             export_qids: dict[str, str],
                             manifest_qids: dict[str, str],
                             ) -> dict[str, dict]:
    """样本 ↔ 导出配对(evaluation-4:qid 感知;确定性)。

    - **严格 qid 档**(评测输入任一侧声明 qid 即全局生效):图按
      manifest 声明 qid 只配同 qid 的可读导出——配对清单按输入
      ``native_path_exports`` 清单序(显式清单序,同 qid 多导出时
      消费首位并以 ``consumed_export_digest`` 披露,不随机);qid
      无匹配导出 ⇒ 空配对(样本 not_evaluated + reason qid 未配到,
      **不再按根身份首中即 break 张冠李戴**);严格档下未声明 qid
      的图同样空配对(单独 reason 披露——回退根身份即重新引入
      evaluation-3 的同根多题错位);未声明 qid 的导出不配任何图
      (进 unmatched_exports 披露);
    - **回退档**(qid 信息完全不可得:无任何图声明 qid 且无任何
      导出声明 qid ⇒ 合成夹具路径):沿用 evaluation-3 根严格身份
      配对(根身份不同 ⇒ 不配;每个导出最多配到一个样本,首中即
      定;清单按 digest 字典序),机读披露 ``pairing_basis=
      root_identity_fallback``,不静默;
    - 两档均保持:每个导出至多配到一个样本;一个样本可配多个导出
      (同 qid 多 run);配不到的导出到 coverage_report 披露;
    - evaluation-5(S5B-L01):``data_scope=real`` 下本函数返回的
      回退档结果会在 ``evaluate_scientific`` 的配对首次消费处被
      结构化拒(``real_data_root_identity_fallback_forbidden``)——
      守卫在消费侧,配对函数本身不接收 data_scope(合成回退语义
      保持不变,由调用方按档拦截)。
    """
    pairing: dict[str, dict] = {graph_id: {
        "basis": PAIRING_BASIS_ROOT_IDENTITY_FALLBACK,
        "qid": None,
        "paired_export_digests": [],
        "consumed_export_digest": None,
        "digest_selection_rule": DIGEST_SELECTION_ROOT_FALLBACK,
    } for graph_id in sorted(graphs)}
    if not (manifest_qids or export_qids):
        # ---- 回退档:根严格身份首中配对(evaluation-3 语义原样) ----
        for digest, payload in sorted(export_payloads.items()):
            root_states = _root_states_of_export(payload)
            root_strict = set()
            states = _export_states(payload)
            for state_id in root_states:
                identity = states.get(state_id, {}).get("smiles_isomeric")
                if identity:
                    root_strict.add(identity)
            for graph_id, graph in sorted(graphs.items()):
                root_entity = graph.get("root_entity") or {}
                try:
                    ref_strict = strict_identity_of(
                        str(root_entity.get("structure_smiles_raw") or ""))
                except ChemicalStateError:
                    ref_strict = str(
                        root_entity.get("strict_structure_identity") or "")
                if ref_strict in root_strict:
                    pairing[graph_id]["paired_export_digests"].append(digest)
                    break
        for info in pairing.values():
            if info["paired_export_digests"]:
                info["consumed_export_digest"] = \
                    info["paired_export_digests"][0]
        return pairing
    # ---- 严格 qid 档:qid 精确身份配对(不消费根结构) ----
    for graph_id in sorted(graphs):
        qid = manifest_qids.get(graph_id)
        digests = [digest for digest in export_entry_order
                   if digest in export_payloads
                   and qid is not None
                   and export_qids.get(digest) == qid]
        pairing[graph_id] = {
            "basis": PAIRING_BASIS_QID_STRICT,
            "qid": qid,
            "paired_export_digests": digests,
            "consumed_export_digest": digests[0] if digests else None,
            "digest_selection_rule": DIGEST_SELECTION_QID_LIST_ORDER,
        }
    return pairing


_METRIC_SPECS = (
    ("reference_edge_recall", "S5-spec 9.1"),
    ("key_intermediate_recall", "S5-spec 9.2"),
    ("confirmed_error_rate", "S5-spec 9.3"),
    ("outside_reference_unverified_edges", "S5-spec 9.4"),
    ("environment_conflict_rate", "S5-spec 9.5"),
    ("endpoint_mineralization_misclaim_rate", "S5-spec 9.6"),
    ("depth_performance", "S5-spec 9.7"),
    ("budget_omission", "S5-spec 9.8"),
)


def _aggregate_metrics(domain: str, track: str, split: str,
                       sample_results: list[dict]) -> list[dict]:
    """按 §9.1–9.8 聚合接口指标(分轴桶 + 计数;分母/阈值 TBD;
    无科学通过线,无合并总分)。"""
    samples = [s for s in sample_results
               if s["scoring_status"] == "scored"]
    edge_buckets: dict[str, int] = {}
    for sample in samples:
        for entry in sample["predicted_edge_matches"]:
            status = entry["match_status"]
            edge_buckets[status] = edge_buckets.get(status, 0) + 1
    node_buckets: dict[str, int] = {}
    for sample in samples:
        for entry in sample["key_intermediate_matches"]:
            status = entry["match_status"]
            node_buckets[status] = node_buckets.get(status, 0) + 1
    outside_buckets: dict[str, int] = {}
    for sample in samples:
        for key, value in sorted(
                (sample["false_or_unverified_edges"] or {}).get(
                    "buckets", {}).items()):
            outside_buckets[key] = outside_buckets.get(key, 0) + value
    condition_buckets: dict[str, int] = {}
    for sample in samples:
        for key, value in sorted(
                sample["environment_conflicts"].get("buckets", {})
                .items()):
            condition_buckets[key] = condition_buckets.get(key, 0) + value
    misclaim_types: dict[str, int] = {}
    for sample in samples:
        for entry in (sample["endpoint_claim_checks"].get("misclaims")
                      or []) + (sample["mineralization_claim_checks"]
                                .get("misclaims") or []):
            misclaim_types[entry["type"]] = \
                misclaim_types.get(entry["type"], 0) + 1
    depth_buckets: dict[str, int] = {}
    for sample in samples:
        for key, value in sorted(
                sample["depth_metrics"].get("buckets", {}).items()):
            depth_buckets[key] = depth_buckets.get(key, 0) + value
    budget_buckets: dict[str, int] = {}
    for sample in samples:
        for key, value in sorted(
                (sample["budget_omission"] or {}).get("buckets", {})
                .items()):
            budget_buckets[key] = budget_buckets.get(key, 0) + value
    confirmed = sum(
        1 for sample in samples
        if sample["unknown_or_partial_summary"]
        ["conditional_admission_events"] == 0)
    metrics = [
        {"metric_id": "reference_edge_recall", "spec_ref": "S5-spec 9.1",
         "axis": {"domain": domain, "track": track, "split": split},
         "buckets": dict(sorted(edge_buckets.items())),
         "denominator_policy": "TBD_USER_TEACHER_DECISION",
         "status": "interface_only_synthetic",
         "note": ("严格反应边召回与结构身份/step scope/参考覆盖/预算"
                  "未展开分桶;分母与通过线 TBD")},
        {"metric_id": "key_intermediate_recall",
         "spec_ref": "S5-spec 9.2",
         "axis": {"domain": domain, "track": track, "split": split},
         "buckets": dict(sorted(node_buckets.items())),
         "key_intermediate_list_frozen": "TBD_USER_TEACHER_DECISION",
         "status": "interface_only_synthetic",
         "note": ("关键中间体清单须评测前冻结;不按预测结果动态决定;"
                  "严格身份与仅 CN 分轴;known/unseen 分轨")},
        {"metric_id": "confirmed_error_rate", "spec_ref": "S5-spec 9.3",
         "axis": {"domain": domain, "track": track, "split": split},
         "buckets": {"confirmed_claim_events": confirmed,
                     **dict(sorted(misclaim_types.items()))},
         "independent_review_subset": "TBD_USER_TEACHER_DECISION",
         "coverage_policy": "TBD_USER_TEACHER_DECISION",
         "status": "interface_only_synthetic",
         "note": ("仅在有独立正负复核依据的子集上报告;unknown/partial/"
                  "conditional 不计 confirmed(本接口只数程序可见的"
                  "误声明类型;独立复核 TBD)")},
        {"metric_id": "outside_reference_unverified_edges",
         "spec_ref": "S5-spec 9.4",
         "axis": {"domain": domain, "track": track, "split": split},
         "buckets": dict(sorted(outside_buckets.items())),
         "status": "interface_only_synthetic",
         "note": ("不直接等同错误率:参考图可能不完备;unseen 轨道允许"
                  "未见边;参考覆盖不足另在 coverage_report 披露")},
        {"metric_id": "environment_conflict_rate",
         "spec_ref": "S5-spec 9.5",
         "axis": {"domain": domain, "track": track, "split": split},
         "buckets": dict(sorted(condition_buckets.items())),
         "status": "interface_only_synthetic",
         "note": ("essential 冲突/条件未知/覆盖不足/preference 不满足/"
                  "来源条件不可映射分桶;要求侧显式非规范单位降"
                  " unknown/unsupported 族不判相容/冲突(S5A-02 r2);"
                  "unknown 不计冲突,满足不升级"
                  "为全路径相容")},
        {"metric_id": "endpoint_mineralization_misclaim_rate",
         "spec_ref": "S5-spec 9.6",
         "axis": {"domain": domain, "track": track, "split": split},
         "buckets": dict(sorted(misclaim_types.items())),
         "endpoint_taxonomy": sorted(ENDPOINT_ASSESSMENTS),
         "status": "interface_only_synthetic",
         "note": ("终点分类沿用 S4 四分账;bookkeeping_status 不单独"
                  "提升为矿化结论;停止原因不是终点")},
        {"metric_id": "depth_performance", "spec_ref": "S5-spec 9.7",
         "axis": {"domain": domain, "track": track, "split": split},
         "buckets": dict(sorted(depth_buckets.items())),
         "insufficient_sample_policy": "TBD_USER_TEACHER_DECISION",
         "status": "interface_only_synthetic",
         "note": ("按第 1/2/3+ 条反应边分桶;样本量不足 ⇒ "
                  "insufficient_sample,不合并总分")},
        {"metric_id": "budget_omission", "spec_ref": "S5-spec 9.8",
         "axis": {"domain": domain, "track": track, "split": split},
         "buckets": dict(sorted(budget_buckets.items())),
         "status": "interface_only_synthetic",
         "note": ("预算漏展开单独报告;不计化学错误,不从分母无声删除;"
                  "是否作性能指标/限制项/单独门槛 TBD")},
    ]
    return metrics


def evaluate_scientific(
    evaluation_input: dict,
    *,
    reference_graphs: dict[str, dict] | None = None,
    native_export_reader=None,
    preregistration: dict | None = None,
    criteria_version: str = PPV1_CRITERIA_V1,
    disclosure_criteria_versions: tuple[str, ...] = (),
) -> dict:
    """正式评测主流程(§11;确定性、可重放、零 LLM)。

    - 输入校验失败 ⇒ ``EvaluationContractError``(结构化,该评测不
      产出结果);
    - 泄漏检查失败 ⇒ 输出 ``status=blocked_leakage``,零聚合;
    - 导出缺席/读取失败 ⇒ 样本级 ``scoring_status`` 披露,不冒充
      已评(S5-28);
    - prereg TBD ⇒ ``pending_preregistration``(S5-23;评测器永不发
      evaluated_*);
    - **ppv1-criteria-v2**:`criteria_version` 缺省 v1 = 豁免关(既有
      行为字节不变,输出零新键);显式 v2 = T-1 判分面豁免启用
      (teacher 裁定;预注册
      ``docs/POLLUTANT_PATHWAY_CRITERIA_V2_PREREGISTRATION_2026-10-13.md``),
      输出附 ``criteria_v2`` 批级汇总块(豁免计数 + 参考侧 v1 身份
      监控,应为 0;非 0 = 退出条件信号);
    - **ppv1-criteria-v3**:显式 v3 = T-D-A/B 披露轴(档 A)启用并
      承载 v2 豁免判分语义;节点级附 ``criteria_v3_normalized_identity``
      披露块、批级附 ``criteria_v3`` 汇总块(分臂计数/单归属/双满足/
      碳酸体系排除/参数指纹/恒空 ``tautomer_promoted_nodes``);
      **不授 strict、不进 hit@1**;v1/v2 缺省零新键。
    - **ppv1-criteria-v4**:显式 v4 = ``matched_product_hit`` 主口径
      (§1–§4);样本级附 ``criteria_v4`` 块与四个新键(``
      hit_mode_scope`` / ``matched_product_hit`` / ``
      product_hit_partial`` / ``product_hit_events``),批级附
      ``criteria_v4`` 汇总块(§3 五桶 + 豁免旁路计数 0 + 旧桶分列);
      原 coverage 事实保留(不改写 superset);旧 ``match_status``
      与 v1/v2/v3 输出零改动;
    - **披露轴并列**:``disclosure_criteria_versions`` 只接受
      ``ppv1-criteria-v3``(v4 + v3 同时启用时 v4 决定命中、v3 归一
      披露照常输出,二者互不改写);缺省空 ⇒ 既有行为逐位不变。
    """
    resolve_criteria_version(criteria_version)
    disclosure_versions = _validate_disclosure_criteria_versions(
        disclosure_criteria_versions)
    v3_disclosure = _criteria_v3_disclosure_enabled(
        criteria_version, disclosure_versions)
    evaluation_input = validate_evaluation_input(evaluation_input)
    split_manifest = validate_split_manifest(
        evaluation_input.get("split_manifest"))
    domain = str(evaluation_input["domain"])
    track = str(evaluation_input["track"])
    interface_mode = bool(
        evaluation_input.get("interface_verification") or False)
    # S5B-V3-01:data_scope 与 validate_evaluation_input 首消费共用
    # resolve_data_scope 同一判据(显式坏值已在校验处拒;此处同源
    # 解析出 scope + 机读归一来源)
    data_scope, data_scope_provenance = resolve_data_scope(
        evaluation_input.get("data_scope"),
        field="data_scope", default="synthetic_rule_level",
        present="data_scope" in evaluation_input)
    provider = evaluation_input.get("model_provider_policy") or {}
    provider_kind = str(provider.get("provider_kind") or "none")
    authorization = str(provider.get("authorization") or "")
    # ---- S5-26:real provider 无用户逐次授权 ⇒ 拒绝(零网络零费用) ----
    if provider_kind == "real" and not authorization:
        raise EvaluationContractError(
            "model_provider_policy.provider_kind=real 而无用户逐次授权"
            "(收费 provider 默认关闭:无授权时网络请求为零、费用为零,"
            "正式科学评测不启动)", {
                "kind": "provider_not_authorized",
                "provider_kind": provider_kind})
    # ---- 真实数据须已批准预注册(S5b 前另有授权,本批一律拒绝) ----
    prereg = preregistration or {}
    prereg_approved = str(
        prereg.get("approval_status") or "") == "approved"
    if data_scope == "real" and not prereg_approved:
        raise EvaluationContractError(
            "data_scope=real 而预注册未批准(真实数据评测属 S5b;须"
            "用户/teacher 完成题源/金标/样本量/阈值/预算裁定后另行"
            "启动)", {"kind": "real_data_requires_approved_preregistration",
                   "preregistration_id": str(
                       evaluation_input.get("preregistration_id"))})
    # ---- 参考图装载与身份核对(§11 第 4 步) ----
    graphs: dict[str, dict] = {}
    if reference_graphs is not None:
        for graph_id, graph in reference_graphs.items():
            validate_reference_graph(graph)
            graphs[str(graph_id)] = graph
    for entry in evaluation_input.get(
            "reference_graph_manifest") or []:
        graph_id = str(entry.get("reference_graph_id"))
        if graph_id in graphs:
            continue
        if entry.get("path"):
            graphs[graph_id] = load_reference_graph(entry["path"])
    manifest_sha_mismatches: list[dict] = []
    for entry in evaluation_input.get(
            "reference_graph_manifest") or []:
        graph_id = str(entry.get("reference_graph_id"))
        if graph_id in graphs:
            actual = reference_graph_sha256(graphs[graph_id])
            if actual != str(entry.get("sha256")):
                manifest_sha_mismatches.append({
                    "reference_graph_id": graph_id,
                    "declared": str(entry.get("sha256"))[:12],
                    "actual": actual[:12]})
    if manifest_sha_mismatches:
        raise EvaluationContractError(
            f"参考图 manifest sha256 与实际内容不符:"
            f"{manifest_sha_mismatches}(数据完整性阻断;不冒充已评)",
            {"kind": "reference_graph_identity_mismatch",
             "mismatches": manifest_sha_mismatches})
    missing_graphs = sorted({
        str(entry.get("reference_graph_id"))
        for entry in evaluation_input.get(
            "reference_graph_manifest") or []} - set(graphs))
    if missing_graphs:
        raise EvaluationContractError(
            f"参考图未提供且 manifest 无 path:{missing_graphs}"
            "(fail-closed;不猜默认)", {
                "kind": "reference_graph_missing",
                "missing": missing_graphs})
    # ---- evaluation-4:图侧 qid 一致性核(manifest 声明 qid 必须出现
    # 在 root_entity.source_refs——转换规则 §2.2 图侧携带 qid;声明
    # 与图内容不一致 ⇒ fail-closed,不猜哪个是真) ----
    manifest_qids = _manifest_qid_map(evaluation_input)
    export_qids = _export_qid_map(evaluation_input)
    for graph_id, declared_qid in sorted(manifest_qids.items()):
        source_refs = {str(ref) for ref in (
            (graphs[graph_id].get("root_entity") or {}).get(
                "source_refs") or [])}
        if declared_qid not in source_refs:
            raise EvaluationContractError(
                f"参考图 {graph_id} 的 manifest 声明 qid={declared_qid!r}"
                "未出现在 root_entity.source_refs(图侧 qid 一致性核;"
                "qid 是样本↔导出配对键,声明与图内容不一致 ⇒ fail-closed,"
                "不猜归属;转换规则要求 source_refs 携带 qid)", {
                    "kind": "reference_graph_qid_not_in_source_refs",
                    "reference_graph_id": graph_id,
                    "qid": declared_qid,
                    "source_refs": sorted(source_refs)})
    # ---- 泄漏检查(§11 第 5 步) ----
    leakage = check_leakage(split_manifest, graphs)
    # ---- 导出装载(§11 第 3 步;S4 公开入口) ----
    export_payloads: dict[str, dict] = {}
    export_read_errors: list[dict] = []
    for entry in evaluation_input.get("native_path_exports") or []:
        digest = str(entry.get("export_digest"))
        if bool(entry.get("lossy_projection") or False):
            export_read_errors.append({
                "export_digest": digest,
                "kind": "lossy_projection_not_scorable",
                "note": ("v3 有损投影不得用于需要完整路径语义的科学"
                         "指标(§3.1);须消费原生导出")})
            continue
        if native_export_reader is None:
            continue  # 无读取通道 ⇒ 导出缺席(S5-28 pending 路径)
        try:
            read_back = native_export_reader(entry)
            export_payloads[digest] = read_back.get("payload") or {}
        except Exception as exc:  # noqa: BLE001 —— 结构化披露
            export_read_errors.append({
                "export_digest": digest,
                "kind": "native_export_unreadable",
                "error": f"{type(exc).__name__}: {exc}"[:200]})
            continue
        # ---- evaluation-4:qid↔run 权威绑定核验(声明 qid 的导出条目:
        # 其 run_id 必须与 read_native_export 返回 payload 的权威
        # run_id 一致——导出侧 run↔qid 映射的可信前提;不一致 ⇒ 该
        # qid 映射不可信,fail-closed 结构化拒,不用声明侧静默配对)
        # ----
        if entry.get("qid") is not None:
            payload_run_id = str(
                (export_payloads[digest].get("run_id")) or "")
            if payload_run_id != str(entry.get("run_id") or ""):
                raise EvaluationContractError(
                    f"导出条目 {digest[:12]} 声明 qid 的 run 绑定不符:"
                    f"entry.run_id={entry.get('run_id')!r} 而导出 payload "
                    f"的权威 run_id={payload_run_id!r}(qid↔run 映射与"
                    "read_native_export 的 run/identity 链断裂 ⇒ 该导出"
                    "条目的 qid 声明不可信,fail-closed)", {
                        "kind": "evaluation_export_run_binding_mismatch",
                        "export_digest": digest,
                        "qid": str(entry.get("qid")),
                        "entry_run_id": str(entry.get("run_id") or ""),
                        "payload_run_id": payload_run_id})
    pairing = _pair_exports_to_samples(
        graphs, export_payloads,
        _export_entry_order(evaluation_input), export_qids, manifest_qids)
    # ---- S5b 回修(S5B-L01,evaluation-5):real 首消费禁双无 qid/
    # root_identity_fallback —— data_scope=real 而配对档为根身份回退
    # (评测输入 manifest 条目与 native_path_exports 条目两侧全部未
    # 声明 qid)⇒ 结构化拒,落在配对首次消费处,先于任何样本评分/
    # 聚合/结果写入(fail-closed:这是既定样本身份边界的兑现,不是
    # criteria-v2 新化学门;qid 不进化学结构判据,化学匹配/条件/
    # 指标判定零触碰)。合法控制保持:synthetic_rule_level 双无 qid
    # 回退(合成夹具正控)、real 严格 qid 档、qid 缺配 not_evaluated
    # 与四个既有输入守卫。
    # ---- W-V6.3(mimo r27 判断面一附条件,随 v3 交付工程落地):
    # 触发条件等价性写死 —— 本守卫触发 ⇔ 两个 qid 映射皆空
    # (manifest_qids 与 export_qids 皆空 ⇒ _pair_exports_to_samples
    # 整批返回 root_identity_fallback 档)。当前配对档是**整批二档**
    # (严格 qid / 根回退,无逐图混合);配对档若改逐图混合,本守卫
    # 须同步改为逐图判定(任一图回退即拒),不得沿用整批判。
    if data_scope == "real" and any(
            info["basis"] == PAIRING_BASIS_ROOT_IDENTITY_FALLBACK
            for info in pairing.values()):
        raise EvaluationContractError(
            "data_scope=real 而样本↔导出配对落入 root_identity_fallback"
            "(评测输入两侧全部未声明 qid:reference_graph_manifest 条目与"
            " native_path_exports 条目均无 qid)——真实数据配对首次消费"
            "禁止根身份回退(53 重复底物/同根多题 G1 下会重新引入首中即"
            " break 张冠李戴;fail-closed,先于任何样本评分/聚合/结果"
            "写入;该门是样本身份边界,不是 criteria-v2 化学判据)", {
                "kind": "real_data_root_identity_fallback_forbidden",
                "data_scope": data_scope,
                "pairing_basis": PAIRING_BASIS_ROOT_IDENTITY_FALLBACK,
                # W-V6.3:触发等价性机读披露(触发 ⇔ 两个 qid 映射
                # 皆空;配对档为整批二档,改逐图混合须同步改逐图判)
                "trigger_equivalence": (
                    "data_scope=real AND (manifest_qids empty AND "
                    "export_qids empty) — 整批配对档判定;若配对档改"
                    "逐图混合,须同步改为逐图判定"),
                "graphs_without_declared_qid": sorted(graphs),
                "export_entries_without_declared_qid": sorted(
                    str(entry.get("export_digest"))
                    for entry in evaluation_input.get(
                        "native_path_exports") or []
                    if entry.get("qid") is None),
                "note": ("真实批两侧须声明 qid 走 qid_strict 配对;"
                         "预注册发车核对:coverage_report.pairing."
                         "bases_by_graph 须全为 qid_strict(任一"
                         " root_identity_fallback ⇒ 阻断判分)")})
    unmatched_exports = sorted(
        set(export_payloads) - {d for info in pairing.values()
                                for d in info["paired_export_digests"]})
    # ---- 样本级评分(§11 第 6–14 步) ----
    sample_results: list[dict] = []
    invalid_input_count = 0
    for entry in sorted(evaluation_input.get(
            "reference_graph_manifest") or [],
            key=lambda e: str(e.get("reference_graph_id"))):
        graph_id = str(entry.get("reference_graph_id"))
        graph = graphs[graph_id]
        root_entity = graph.get("root_entity") or {}
        sample_id = f"{domain}:{track}:{graph_id}"
        source_group_ids = sorted({
            str(g.get("source_group_id"))
            for g in graph.get("source_groups") or []})
        sample = {
            "sample_id": sample_id,
            "reference_graph_id": graph_id,
            "root_entity_id": str(root_entity.get("entity_id")),
            "source_group_ids": source_group_ids,
            "scoring_status": "scored",
            "scoring_errors": [],
            "predicted_node_matches": [],
            "predicted_edge_matches": [],
            "key_intermediate_matches": [],
            "false_or_unverified_edges": {},
            "environment_conflicts": {},
            "endpoint_claim_checks": {},
            "mineralization_claim_checks": {},
            "depth_metrics": {},
            "budget_omission": {},
            "unknown_or_partial_summary": {},
        }
        # ---- evaluation-4:样本级配对机读披露(两档均披露;不静默) ----
        pairing_info = pairing[graph_id]
        sample["pairing"] = {
            "basis": pairing_info["basis"],
            "qid": pairing_info["qid"],
            "paired_export_digests": list(
                pairing_info["paired_export_digests"]),
            "consumed_export_digest": pairing_info[
                "consumed_export_digest"],
            "digest_selection_rule": pairing_info["digest_selection_rule"],
        }
        digests = pairing_info["paired_export_digests"]
        if not digests:
            sample["scoring_status"] = "not_evaluated_export_missing"
            if pairing_info["basis"] == PAIRING_BASIS_QID_STRICT:
                if pairing_info["qid"] is not None:
                    # qid 已声明但未配到导出:reason 明示 qid 未配到,
                    # 不按根身份回退配对(不再张冠李戴;evaluation-4)
                    qid_declared_by_entry = pairing_info["qid"] in set(
                        export_qids.values())
                    sample["scoring_errors"] = [{
                        "kind": "sample_qid_unpaired",
                        "qid": pairing_info["qid"],
                        "qid_declared_by_export_entry": (
                            qid_declared_by_entry),
                        "note": (f"样本声明 qid={pairing_info['qid']!r} "
                                 "未配到任何可读导出 ⇒ not_evaluated"
                                 "(qid 未配到;不按根身份回退配对,"
                                 "同根多题不张冠李戴;evaluation-4)"),
                    }]
                else:
                    sample["scoring_errors"] = [{
                        "kind": "graph_qid_missing_in_strict_pairing",
                        "note": ("评测输入存在 qid 声明(严格 qid 配对档)"
                                 "而该图未声明 qid ⇒ 不回退根身份配对"
                                 "(回退即重新引入同根多题首中即 break 的"
                                 "错位);样本 not_evaluated,evaluation-4"),
                    }]
            else:
                sample["scoring_errors"] = [{
                    "kind": "native_export_missing",
                    "note": ("S4 native export 未交付 ⇒ 可验证接口,不运行"
                             "正式科学评测,状态 pending(S5-28)")}]
            if criteria_version == PPV1_CRITERIA_V4:
                # 无导出 ⇒ 无合法事件;参考有效性仍可从图声明判定
                # (不借缺席导出冒充已评;§3 留分母)
                v4_nodes_by_id = {
                    str(node.get("node_id")): node
                    for node in graph.get("nodes") or []}
                v4_block = _criteria_v4_sample_block([
                    _criteria_v4_edge_product_hit(
                        edge, v4_nodes_by_id, None)
                    for edge in graph.get("edges") or []])
                sample["criteria_v4"] = v4_block
                sample["hit_mode_scope"] = CRITERIA_V4_HIT_MODE_SCOPE
                sample["matched_product_hit"] = \
                    v4_block["matched_product_hit"]
                sample["product_hit_partial"] = \
                    v4_block["product_hit_partial"]
                sample["product_hit_events"] = \
                    v4_block["product_hit_events"]
            if criteria_version == PPV1_CRITERIA_V5:
                # 无导出 ⇒ 无合法事件;参考有效性仍可从图声明判定
                # (不借缺席导出冒充已评;§2.2 留分母)
                v5_nodes_by_id = {
                    str(node.get("node_id")): node
                    for node in graph.get("nodes") or []}
                v5_block = _criteria_v5_sample_block([
                    _criteria_v5_edge_product_hit(
                        edge, v5_nodes_by_id, None)
                    for edge in graph.get("edges") or []])
                sample["criteria_v5"] = v5_block
                sample["hit_mode_scope"] = CRITERIA_V5_HIT_MODE_SCOPE
                sample["role_bound_product_hit"] = \
                    v5_block["role_bound_product_hit"]
                sample["product_hit_partial"] = \
                    v5_block["product_hit_partial"]
                sample["role_bound_hit_events"] = \
                    v5_block["role_bound_hit_events"]
            invalid_input_count += 1
            sample_results.append(sample)
            continue
        payload = export_payloads[pairing_info["consumed_export_digest"]]
        node_matches = match_reference_nodes(
            graph, payload, criteria_version=criteria_version,
            disclosure_criteria_versions=disclosure_versions)
        edge_matches = match_reference_edges(
            graph, payload, node_matches,
            criteria_version=criteria_version)
        if criteria_version == PPV1_CRITERIA_V4:
            v4_block = _criteria_v4_sample_block(edge_matches)
            sample["criteria_v4"] = v4_block
            sample["hit_mode_scope"] = CRITERIA_V4_HIT_MODE_SCOPE
            sample["matched_product_hit"] = \
                v4_block["matched_product_hit"]
            sample["product_hit_partial"] = \
                v4_block["product_hit_partial"]
            sample["product_hit_events"] = \
                v4_block["product_hit_events"]
        if criteria_version == PPV1_CRITERIA_V5:
            v5_block = _criteria_v5_sample_block(edge_matches)
            sample["criteria_v5"] = v5_block
            sample["hit_mode_scope"] = CRITERIA_V5_HIT_MODE_SCOPE
            sample["role_bound_product_hit"] = \
                v5_block["role_bound_product_hit"]
            sample["product_hit_partial"] = \
                v5_block["product_hit_partial"]
            sample["role_bound_hit_events"] = \
                v5_block["role_bound_hit_events"]
        conditions = classify_sample_conditions(graph, payload)
        endpoint_checks = check_endpoint_claims(
            payload.get("endpoint_record") or {},
            graph.get("endpoint_annotations") or [])
        depth = depth_metrics_from_export(payload)
        budget = budget_omission_from_export(payload)
        unknown_partial = unknown_partial_summary_from_export(payload)
        matched_event_ids = {
            event_id for entry in edge_matches
            for event in entry["matched_events"]
            for event_id in [event["event_id"]]}
        outside = outside_reference_edges_from_export(
            payload, matched_event_ids)
        if any(entry["match_status"] ==
               "reference_structure_unparseable"
               for entry in node_matches):
            sample["scoring_status"] = "invalid_input"
            sample["scoring_errors"] = [{
                "kind": "reference_structure_unparseable",
                "note": "参考结构不可解析 ⇒ 停止该样本评测(不静默删)"}]
            invalid_input_count += 1
        sample["predicted_node_matches"] = node_matches
        sample["predicted_edge_matches"] = edge_matches
        sample["key_intermediate_matches"] = [
            entry for entry in node_matches
            if entry["role"] == "intermediate"]
        sample["false_or_unverified_edges"] = outside
        sample["environment_conflicts"] = conditions
        sample["endpoint_claim_checks"] = endpoint_checks
        sample["mineralization_claim_checks"] = {
            "misclaims": [m for m in endpoint_checks["misclaims"]
                          if "mineralization" in m["type"]
                          or "co2" in m["type"]],
            "predicted_assessment": endpoint_checks[
                "predicted_assessment"],
            "note": ("矿化证据最低口径:根碳账核查范围 + 来源层直报;"
                     "仅 CO₂ 产物/仅模型推演/bookkeeping 皆不构成矿化"
                     "结论"),
        }
        sample["depth_metrics"] = depth
        sample["budget_omission"] = budget
        sample["unknown_or_partial_summary"] = unknown_partial
        sample_results.append(sample)
    # ---- 聚合(§11 第 15 步;分层 TBD 时按 split 单层聚合) ----
    aggregates: list[dict] = []
    if leakage["status"] != "failed":
        split_of = {}
        for assignment in split_manifest.get("assignments") or []:
            split_of[str(assignment.get("reference_graph_id"))] = \
                str(assignment.get("split"))
        default_split = "development"
        for split in sorted(set(split_of.values()) or {default_split}):
            split_samples = [
                s for s in sample_results
                if split_of.get(s["reference_graph_id"], default_split)
                == split]
            aggregates.extend(_aggregate_metrics(
                domain, track, split, split_samples))
    # ---- 覆盖/缺失报告(§11 第 16–17 步) ----
    coverage_report = {
        "reference_graphs": sorted(graphs),
        "not_evaluable_edges_per_graph": {
            str(g): sorted((graphs[g].get("coverage_statement")
                            or {}).get("not_evaluable_edge_ids") or [])
            for g in sorted(graphs)},
        "known_gaps_per_graph": {
            str(g): sorted((graphs[g].get("coverage_statement")
                            or {}).get("known_gaps") or [])
            for g in sorted(graphs)},
        "unmatched_exports": unmatched_exports,
        "pairing": {
            "bases_by_graph": {g: pairing[g]["basis"]
                               for g in sorted(pairing)},
            "qids_by_graph": {g: pairing[g]["qid"]
                              for g in sorted(pairing)},
            "paired_export_digests_by_graph": {
                g: list(pairing[g]["paired_export_digests"])
                for g in sorted(pairing)},
            "consumed_export_digest_by_graph": {
                g: pairing[g]["consumed_export_digest"]
                for g in sorted(pairing)},
            "digest_selection_rule_by_graph": {
                g: pairing[g]["digest_selection_rule"]
                for g in sorted(pairing)},
            "note": PAIRING_BASIS_NOTE,
        },
        "note": ("未画出的参考边不自动判模型错误,计入参考覆盖限制"
                 "(S5-09);参考图不完备时如实披露覆盖范围"),
    }
    missingness_report = {
        "unknown_partial_summary_per_sample": {
            s["sample_id"]: s["unknown_or_partial_summary"]
            for s in sample_results
            if s["scoring_status"] == "scored"},
        "condition_unknown_note": ("条件未知/覆盖不足与冲突分桶;"
                                   "未知不计冲突"),
        "note": ("unknown/partial/conditional 保留;不用全面拒绝换通过"
                 "(§18 第 16 条)"),
    }
    network_requests = sum(
        int(row.get("network_request_count") or 0)
        for payload in export_payloads.values()
        for row in payload.get("model_requests") or [])
    # ---- 状态裁定(§12;程序永不发 evaluated_*) ----
    if leakage["status"] == "failed":
        status = "blocked_leakage"
    elif not export_payloads or all(s["scoring_status"] != "scored"
                                    for s in sample_results):
        # S5-28:S4 导出未交付/全部样本不可评 ⇒ 可验证接口,不运行
        # 正式科学评测,状态 pending(优先于接口验证模式)
        status = "pending_no_independent_data"
    elif interface_mode:
        status = "interface_verified_only"
    elif not prereg or str(prereg.get("approval_status") or "").startswith(
            "pending"):
        status = "pending_preregistration"
    else:
        status = "pending_user_teacher_decision"
    if status not in EMITTED_STATUSES:  # pragma: no cover —— 防御
        raise EvaluationContractError(
            f"状态裁定越界:{status}(评测器永不生成 evaluated_*;"
            "最终科学状态由用户/teacher 按预注册裁定)",
            {"kind": "evaluation_status_out_of_range",
             "status": status})
    output = {
        "evaluator_schema_version": PPV1_EVALUATION_VERSION,
        "evaluation_id": content_hash({
            "run_identity": evaluation_input.get("run_identity"),
            "reference_graph_manifest": evaluation_input.get(
                "reference_graph_manifest"),
            "split_manifest_id": split_manifest.get(
                "split_manifest_id"),
            "domain": domain, "track": track,
            "preregistration_id": evaluation_input.get(
                "preregistration_id"),
        }),
        "run_identity": evaluation_input.get("run_identity"),
        "domain": domain,
        "track": track,
        "split": {str(a.get("reference_graph_id")):
                  str(a.get("split"))
                  for a in sorted(
                      split_manifest.get("assignments") or [],
                      key=lambda a: str(a.get("reference_graph_id")))},
        "sample_results": sample_results,
        "aggregate_metrics": aggregates,
        "uncertainty_intervals": [{
            "method": "TBD_USER_TEACHER_DECISION",
            "status": "pending_preregistration",
            "note": ("置信区间方法/多重比较处理 TBD;接口仅预留分轴"
                     "结构,不产出区间数值")}],
        "coverage_report": coverage_report,
        "missingness_report": missingness_report,
        "budget_omission_report": {
            "per_sample": {s["sample_id"]: s["budget_omission"]
                           for s in sample_results},
            "note": ("预算漏展开单独报告,不静默从分母删除"
                     "(S5-20/§9.8)")},
        "leakage_checks": leakage,
        "invalid_input_count": invalid_input_count,
        "export_read_errors": export_read_errors,
        "scoring_provenance": {
            "evaluator_version": PPV1_EVALUATION_VERSION,
            "split_manifest_version": PPV1_SPLIT_MANIFEST_VERSION,
            "reference_graph_sha256s": {
                str(entry.get("reference_graph_id")):
                    str(entry.get("sha256"))
                for entry in sorted(
                    evaluation_input.get(
                        "reference_graph_manifest") or [],
                    key=lambda e: str(e.get("reference_graph_id")))},
            "split_manifest_sha256": content_hash(split_manifest),
            "preregistration_sha256": (
                content_hash(prereg) if prereg else ""),
            "llm_in_scoring": False,
            "network_request_count": network_requests,
            "provider_kind": provider_kind,
            "cost": 0,
            "consumed_field_policy": (
                "仅消费冻结结构化字段清单;自然语言字段不进判定"
                "(S5-25);evaluation-4 新增条目级子字段 manifest.qid /"
                " native_path_exports.qid 仅用于样本↔导出配对;"
                "evaluation-5 real 档配对禁 root_identity_fallback"
                "(守卫在配对消费侧,不新增消费字段)"),
            "data_scope": data_scope,
            # S5B-V3-01:机读归一来源(explicit | missing_field_default;
            # 显式坏值在 validate/evaluate 首消费处结构化拒,到不了这里)
            "data_scope_normalized_from":
                data_scope_provenance["normalized_from"],
            "scientific_metric_status": (
                "interface_only:合成规则级数字不外推 dev/298,不构成"
                "科学性能声明(§5.1 题域标签/§12 状态语义)"),
        },
        "status": status,
    }
    # ---- ppv1-criteria-v2 批级汇总(启用豁免口径时输出:v2 与 v3;
    # v1 缺省零新键=字节不变) ----
    # 豁免披露计数 + 两 tier 单归属计数(预注册 §五;failed/mixed review
    # 不保留在 matched-edge 输出,右侧计数无法从输出重建 ⇒ 由逐边
    # criteria_v2_tier_counts 随边带出汇总,P2 2026-10-14)+ 参考侧
    # v1 身份监控(mimo r36 条件 4:应为 0,非 0 = 退出条件信号)。
    # v3 = 承载 v2 判分语义(N3/N7 正交性;块内容逐位同 v2)。
    if _criteria_exemption_enabled(criteria_version):
        edges_with_exemption = 0
        events_exempted = 0
        occurrence_count = 0
        family_counts: dict[str, int] = {}
        criteria_tier_counts: dict[str, int] = {
            CRITERIA_TIER_V1_EXEMPT: 0,
            CRITERIA_TIER_NOT_EXEMPT: 0}
        for sample in sample_results:
            for entry in sample["predicted_edge_matches"]:
                exempted_events = [
                    ev for ev in entry.get("matched_events") or []
                    if ev.get("exempted_participants")]
                if exempted_events:
                    edges_with_exemption += 1
                for ev in exempted_events:
                    events_exempted += 1
                    for occ in ev["exempted_participants"]:
                        occurrence_count += 1
                        family = str(occ.get("exempt_family") or "")
                        family_counts[family] = \
                            family_counts.get(family, 0) + 1
                for tier, n in (entry.get("criteria_v2_tier_counts")
                                or {}).items():
                    assert tier in CRITERIA_TIERS, \
                        (f"ppv1-criteria-v2 批级 tier 单归属计数遇非法 "
                         f"tier:{tier!r}(完备二分恰两 tier)")
                    criteria_tier_counts[tier] += int(n)
        reference_v1_nodes = 0
        reference_v1_graphs: list[str] = []
        for graph_id, graph in sorted(graphs.items()):
            node_hits = 0
            for node in graph.get("nodes") or []:
                node_cn = cn_identity(str(node.get("structure_smiles")
                                          or ""))
                if node_cn is not None and node_cn in \
                        _CRITERIA_V2_IDENTITIES["all"]:
                    node_hits += 1
            if node_hits:
                reference_v1_graphs.append(graph_id)
            reference_v1_nodes += node_hits
        output["criteria_v2"] = {
            "criteria_version": PPV1_CRITERIA_V2,
            "preregistration_doc": PPV1_CRITERIA_V2_PREREGISTRATION_DOC,
            "exemption_enabled": True,
            "edges_with_exemption": edges_with_exemption,
            "events_exempted_strict": events_exempted,
            "tier_counts": dict(sorted(criteria_tier_counts.items())),
            "exempted_participant_occurrences": occurrence_count,
            "exempted_family_counts": dict(sorted(
                family_counts.items())),
            "reference_side_v1_identity_nodes": reference_v1_nodes,
            "reference_side_v1_identity_graphs": reference_v1_graphs,
            "reference_side_v1_identity_signal": (
                "EXIT_CONDITION_SIGNAL_nonzero" if reference_v1_nodes
                else "ok"),
            "t1p_tier_note": CRITERIA_T1P_NOT_IMPLEMENTED_NOTE,
            "dual_caliber_note": (
                "ppv1-criteria-v1(豁免关)恒为 headline 直到新批次按"
                "预注册以 v2 出数;本块为 v2 口径敏感性披露,post-hoc;"
                "旧批零回写"),
        }
    # ---- ppv1-criteria-v3 批级汇总(仅 v3;v1/v2 缺省零新键) ----
    # 分臂计数 + 单归属 + 双满足 + 碳酸体系排除 + 恒空
    # tautomer_promoted_nodes + 参数指纹登记(§8 承载面;档 A 只披露,
    # 不授 strict、不进 hit@1)。
    if v3_disclosure:
        output["criteria_v3"] = _criteria_v3_batch_block(sample_results)
    # ---- ppv1-criteria-v4 批级汇总(仅 v4;v1/v2/v3 缺省零新键) ----
    # §3 五桶(互斥、和=分母)+ §4 豁免旁路计数 0 披露 + 旧
    # match_status 桶分列(不得与本指标同名)。
    if criteria_version == PPV1_CRITERIA_V4:
        output["criteria_v4"] = _criteria_v4_batch_block(sample_results)
    # ---- ppv1-criteria-v5 批级汇总(仅 v5;v1/v2/v3/v4 缺省零新键) ----
    if criteria_version == PPV1_CRITERIA_V5:
        output["criteria_v5"] = _criteria_v5_batch_block(sample_results)
    output["output_sha256"] = hashlib.sha256(
        canonical_json(output).encode("utf-8")).hexdigest()
    return output


# ------------------------------------------------------- 输出落盘与金标守卫


def persist_evaluation_output(output: dict, target: str | Path, *,
                              contains_gold: bool = False,
                              repo_root: str | Path | None = None
                              ) -> dict:
    """评测输出落盘(S5-27:含金标产物只能进授权 gitignored 根)。

    ``contains_gold``:输出是否嵌入参考图/金标内容(真实评测时由
    调用方如实标注)。授权根镜像 .gitignore 的金标隔离目录;普通
    目录(含仓内非 gitignored 路径)写入拒绝。

    S5A-04:核验与写入使用**同一个解析后的实际规范路径**(``
    Path.resolve()`` 一次;授权判定、目录创建、写文件三处同一路径,
    禁止出界后回退原字符串授权):

    - 显式 ``repo_root``:relative target 基准 = **相对 cwd** 解析
      (声明根即核验根);解析后实际路径逃出声明根(错 cwd、绝对
      路径越界、任意一层 symlink 逃根)⇒ 结构化先拒
      (``gold_content_outside_declared_root``;零新文件/目录);
      根内路径再核 repo 相对路径是否为授权 gitignored 根
      (``gold_content_unauthorized_path``);
    - 未声明 ``repo_root``:含金标写入一律拒绝(``
      gold_content_root_required``)—— 授权判定必须有一个可核验
      的根,不做未解析路径名授权;
    - ``contains_gold=False`` 的普通非敏感写入保持原行为(写调用
      方给定路径;本守卫不新增内容 DLP、完整沙箱或敌意并发
      symlink-race 防御,S5A-04 范围仅为根规则闭合)。
    """
    target = Path(target)
    text = canonical_json(output) + "\n"
    if contains_gold:
        if repo_root is None:
            raise EvaluationContractError(
                f"含金标产物写入必须显式声明 repo_root(未声明根 ⇒ "
                f"一律拒绝:授权判定必须有一个可核验的根,不用未解析"
                f"路径名授权;S5A-04):{target}", {
                    "kind": "gold_content_root_required",
                    "target": str(target),
                    "authorized_roots": sorted(
                        GOLD_AUTHORIZED_ROOTS)})
        root = Path(repo_root).resolve()
        resolved = target.resolve()
        try:
            rel = resolved.relative_to(root).as_posix()
        except ValueError:
            rel = None
        if rel is None:
            # 解析后实际路径逃出声明根:错 cwd/绝对路径越界/任意层
            # symlink 逃根均在此先拒(零新文件/目录;不回退原字符串)
            raise EvaluationContractError(
                f"含金标的评测产物解析后实际路径逃出声明 repo_root:"
                f"{resolved}(声明根 {root};相对基准=相对 cwd,出界先"
                "拒;symlink 实际逃根先拒;零新文件/目录;禁止出界后"
                "按原字符串授权,S5A-04)", {
                    "kind": "gold_content_outside_declared_root",
                    "target": str(target),
                    "resolved_target": str(resolved),
                    "declared_repo_root": str(root)})
        authorized = any(
            rel == root_path or rel.startswith(root_path + "/")
            for root_path in sorted(GOLD_AUTHORIZED_ROOTS))
        if not authorized:
            raise EvaluationContractError(
                f"含金标的评测产物只能写入授权 gitignored 目录:"
                f"{resolved}(repo 相对路径 {rel};授权根 "
                f"{sorted(GOLD_AUTHORIZED_ROOTS)};普通目录写入拒绝,"
                "S5-27)", {
                    "kind": "gold_content_unauthorized_path",
                    "target": str(target),
                    "resolved_target": str(resolved),
                    "repo_relative_path": rel,
                    "authorized_roots": sorted(
                        GOLD_AUTHORIZED_ROOTS)})
        write_path = resolved
    else:
        write_path = target
    write_path.parent.mkdir(parents=True, exist_ok=True)
    write_path.write_text(text, encoding="utf-8")
    return {"path": str(write_path),
            "sha256": hashlib.sha256(
                text.encode("utf-8")).hexdigest()}
