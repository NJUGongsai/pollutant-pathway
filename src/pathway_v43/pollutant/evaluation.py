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
"""

from __future__ import annotations

import hashlib
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
PPV1_CRITERIA_VERSIONS = frozenset({PPV1_CRITERIA_V1, PPV1_CRITERIA_V2})
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

    非 {ppv1-criteria-v1, ppv1-criteria-v2} 一律结构化拒(不猜、不
    静默归一);v2 请求而身份工具缺席 ⇒ 拒(v2 无法判定,宁可不开)。"""
    if raw_value not in PPV1_CRITERIA_VERSIONS:
        raise EvaluationContractError(
            f"criteria_version 非法:{raw_value!r}(允许 "
            f"{sorted(PPV1_CRITERIA_VERSIONS)};缺省 {PPV1_CRITERIA_V1} = "
            "豁免关;ppv1-criteria-v2 为 teacher T-1 裁定豁免口径,"
            "显式启用)", {"kind": "criteria_version_invalid",
                         "value": raw_value,
                         "allowed": sorted(PPV1_CRITERIA_VERSIONS)})
    if raw_value == PPV1_CRITERIA_V2 and \
            not _CRITERIA_V2_IDENTITIES["available"]:
        raise EvaluationContractError(
            "criteria_version=ppv1-criteria-v2 而 cn 身份工具/身份集"
            "不可用(fail-closed:v2 判据无法评估,不降级不猜测)", {
                "kind": "criteria_v2_identity_tools_unavailable"})
    return raw_value


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


def match_reference_nodes(reference_graph: dict,
                          payload: dict) -> list[dict]:
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
      (两档基数不同,不可跨档比较)。
    """
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
      匹配/step_scope 判定零触碰。
    """
    resolve_criteria_version(criteria_version)
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
                if criteria_version == PPV1_CRITERIA_V2 and \
                        coverage == "superset":
                    exempt_review = evaluate_participant_exemption(
                        payload, _event_payload_body(event), states,
                        hypothesis_id=str(event.get("hypothesis_id") or ""),
                        from_states=from_states, to_states=to_states)
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
      监控,应为 0;非 0 = 退出条件信号)。
    """
    resolve_criteria_version(criteria_version)
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
            invalid_input_count += 1
            sample_results.append(sample)
            continue
        payload = export_payloads[pairing_info["consumed_export_digest"]]
        node_matches = match_reference_nodes(graph, payload)
        edge_matches = match_reference_edges(
            graph, payload, node_matches,
            criteria_version=criteria_version)
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
    # ---- ppv1-criteria-v2 批级汇总(仅 v2;v1 缺省零新键=字节不变) ----
    # 豁免披露计数 + 参考侧 v1 身份监控(mimo r36 条件 4:应为 0,
    # 非 0 = 退出条件信号;预注册 §五)。
    if criteria_version == PPV1_CRITERIA_V2:
        edges_with_exemption = 0
        events_exempted = 0
        occurrence_count = 0
        family_counts: dict[str, int] = {}
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
