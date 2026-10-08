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
# v11(2026-10-07 S3a 回修 r3,Codex S3a 复审 R2 残余三组
# S3A-02/03/04):搜索权威/冻结策略/请求引用消费闭合升版 —— search
# 契约 ppv1-search-2 → ppv1-search-3(预约单位/合法状态/各 limit 所
# 需 scope-subject 与主体共享 alternatives 的行级内容核验,attempt
# 状态/hypothesis/task 同源交叉核验,提交记录归属/kind/适用 attempt
# 引用核验,done 四入口(first complete 复用/B4/claim/submit)一致
# 消费完整引用;附随投影/展开计划按首提同一判据做只读内容核验,不
# 从当前坏行取出再自比较;B3 在事件提交之前先核必要 attempt/预约
# 引用;done submit 只返回真实已完成 event 或明确冲突;S3A-03 区分
# 配置装配与已冻结对象消费 —— register 落账完整装配块,读取/恢复/
# 预算/认领消费先严格核类型/必需完整键/版本(validate_frozen_
# search_limits),null/缺版本/坏值消费前结构化拒、零执行预约;
# S3A-04 请求已有 row 复用对照 stored 与 incoming run/action/
# attempt/目的/payloaddigest/retry,发送/响应/失败核 run 绑定与
# expand 必要 attempt,恢复 pending 请求逐行同源守卫、坏引用结构化
# 披露不伪装普通合法 pending)。search-limits 保持 -3(键/默认/
# 范围/单位未动;装配与严格消费拆分是消费语义,按 r2 先例随 search
# 契约登记);store 保持 -9(表结构与 writer 行为未改;新增只读
# verify_event_attachment_content 共享判据入口,复用既有首提校验,
# 不另造判据)。profile 仍未放行执行流,无历史产物需要迁移;v10
# 身份载荷按既有门拒绝。
# v12(2026-10-08 S3a 回修 r4,Codex S3a 复审 R3 残余三组
# S3A-02/03/04):必要集合/状态口策略/生命周期来源闭合升版 —— search
# 契约 ppv1-search-3 → ppv1-search-4(_verify_action_references 先按
# claim/attempt 现有创建规则同源核必要预约集合完整性,必要行被删或
# 引用清单缺项即使剩余清单非空也先结构化拒,覆盖 first complete/B4/
# B3 事件提交前/B1/defer/done 四口,预约 ID 派生抽出 _reservation_id
# 与 _reserve 单一来源;record_request_sent/response/failed 在新
# status 写入之前消费同一严格冻结块校验,null/缺版本/坏值状态口先
# 结构化拒且无成功状态变化;mark_request_failed 正面限定 registered/
# sent 合法来源,枚举外未知来源结构化拒并保全不静默洗成 failed,
# register 同键复用核存储状态枚举,recover 报告结构化披露状态枚举外
# 请求行)。search-limits 保持 -3(键/默认/范围/单位/计数语义未动,
# 状态口接守卫是消费语义,按 r2/r3 先例随 search 契约登记);store
# 保持 -9(表结构与 writer 行为未改,核验全部复用既有函数)。profile
# 仍未放行执行流,无历史产物需要迁移;v11 身份载荷按既有门拒绝。
# v13(2026-10-08 S3b 批次):S3b 调度与生产链接线升版 —— search 契约
# ppv1-search-4 → ppv1-search-5(冻结池队列选择 schedule_hypotheses、
# record_expansion_outcome 持久尝试结论、两类 deferred(共同产物/
# 备选反应)的分别激活 activate_deferred(幂等/trigger/expected_
# parent_revision 校验、预算不足留独立未展开原因)、条件依赖/显式
# 场景转换进调度(转换独立 action/预算/记录、仅后效)、enqueue 支持
# initial_status=deferred 与 reactivate_deferred_action 状态迁移;
# 新增独立有界格式反馈策略块 ppv1-format-feedback-1(非 S2 十个
# 搜索上限的旧草案字段,默认 0 轮、范围 0-4、单位=同任务 JSON 格式
# 修复轮数,不把格式反馈轮数当 hypothesis 语义 attempt;反馈仅限
# JSON 字段/类型/允许 ID/语法契约错误,结构无法解析记结构失败,
# chemical_reproposal 首版保持 off);固定 AtomTool → check_edit_
# against_donor → center_evidence_from_donor_diagnostic → audit_
# hypothesis → decide_admission → 事件提交的生产调用链接入 runner
# PPV1 分流(公开 start_run/resume_run 开放,走独立严格状态/搜索
# ledger/事件账,不落 legacy CN/PathwayStore/预算派生)。search-
# limits 保持 -3(十键未动);store 保持 -9(无新表:两类 deferred
# 复用 search_actions 行 + defer_reason/payload,格式反馈轮次计数
# 复用 model_requests 行(purpose=format_feedback),context 持久化
# 走 artifact 存储并经 from_dict 内容身份首消费核验)。profile 仍未
# 有放行前的历史产物需要迁移;v12 身份载荷按既有门拒绝。
# v14(S3b 回修 r2,2026-10-08,Codex S3b 复审 S3B-01~06 六组 P1):
# search 契约 ppv1-search-5 → -6(调度 blocked 对象同源持久记录 +
# stop_report 派生 depth_limit 原因与 blocked_objects 清单;恢复
# 裁定的坏 artifact/缺权威 action 明确隔离 claimed → blocked,不猜
# 重算/不创建成功 event/commit/consume;转换 action 的 pending_
# followup 创建时一次冻结入载荷,消除两写窗口);模型协议
# ppv1-model-proposals-1 → -2(novel 池外提案必须携带完整
# reaction_spec 反应内容与 proposal_context 来源,缺内容不能授有效
# hypothesis,不得伪造来源;驱动消费 novel 为独立假设走固定工具→
# audit→admission→submit);run 执行流 ppv1-runflow-1 → -2(冻结
# 计划/池/必要输入首用与恢复共用持久来源 —— start 持久化冻结计划,
# resume 无 plan 沿冻结输入、传入计划内容不符结构化拒、decide 冻结
# pool_digest 与 retrieve 任务 plan_digest 同源核验;公开 start/resume
# 以 run 目录 flock 执行会话互斥,双进程只一方取得执行权,崩溃 OS
# 自动释放、新进程沿原 attempt/预约接管;空池仍组装底物档案并消费
# 模型 novel 响应)。search-limits 保持 -3;store 保持 -9(无新表)。
# S3b r3(2026-10-08,Codex S3b-r2 复审唯一残余 P1 S3B-01 后段锚定):
# run 执行流 ppv1-runflow-2 → -3 —— resume **首消费前**把读取的冻结
# 计划与独立既存 run/root/task 原绑定核对(start 落账的根 retrieve
# 行 payload.plan_digest 为独立权威;task_key 经同一 decision_task_key
# 单一来源按行内字段重算比对 —— artifact 文件内自算的信封 payload_
# hash/plan_digest 是自洽证书,不能单独证明仍是原输入);缺锚
# (frozen_plan_anchor_missing)/坏锚(frozen_plan_anchor_corrupt)/
# 摘要不符(frozen_plan_binding_mismatch)先结构化拒,先于 recover
# 补账/事件提交/新调度/预算 consume,业务表零新增、原资料保全;
# 覆盖 root retrieve 已 done 的 B3/B4(执行层 plan_digest 核验后段
# 不可达)。正常同计划/省略 plan/显式同计划恢复全保持。profile 保持
# -14;search 保持 -6;search-limits 保持 -3;store 保持 -9(核对读
# 既有 search_actions 行,无新表);生产化学链 production.py 不动。
# v15(S4a 批次,2026-10-08,S4 任务书 §7 S4a 边界):endpoint 分账
# 与原生结果底座 —— 新增 endpoint 契约(ppv1-endpoint-1:execution_
# status/search_stop_reason/chemical_endpoint_assessment/
# bookkeeping_status 四分账 + 终点证据字段 + F01/F02/F03 规则 +
# stop/endpoint 独立持久化与首消费/staleness 校验,见 pollutant/
# endpoint.py)、endpoint 派生策略(ppv1-endpoint-policy-1:固定规则,
# 无用户可配项)与原生结果对象契约(ppv1-native-result-1:完整字段
# 聚合 + canonical 确定性规范化,见 pollutant/native_result.py;
# 正式文件导出/v3 适配/S4b);store 升 -10(纯增量两张派生投影表
# stop_reason_records/endpoint_records,零既有列/行为改动);runflow
# 升 -4(公共 start/resume 在 drive 后派生 endpoint 四分账并独立
# 持久化;stop/endpoint 只读业务表,零 event/attempt/request/budget
# 新写入)。**本批不触碰冻结判据语义**:判据一–五(ppv1-*-8 族)
# 与 0d/0e 消费契约(search-6 语义/legacy 契约)全部保持;S0–S3
# 全量既有测试除 profile 版本字面量外零改动。
# v16(S4b 批次,2026-10-08,S4 任务书 §7 S4b 边界):正式文件导出
# 与 v3 有损适配 —— 新增原生正式导出契约(ppv1-native-export-1:
# 文件级 payload + manifest + 五类首消费拒拒(stale/corrupt/version/
# policy/reference),manifest 记录全部事实表内容 digest 作 graph
# revision 等价身份,见 pollutant/native_export.py)、导出策略
# (ppv1-native-export-policy-1:固定序列化/命名/无时间戳规则,无
# 用户可配项)与 v3 有损投影契约(ppv1-v3-projection-1:显式
# lossy_projection + 原生引用 + 信息损失清单 + 反向消费禁止,见
# pollutant/v3_projection.py);runflow 升 -5(公共 start/resume 在
# S4a 派生后立即正式导出 + v3 投影 + 首消费读回;零 event/attempt/
# request/budget 新写入)。store 保持 -10(导出为 run 目录文件,无
# 新表)。**本批不触碰冻结判据语义**:判据一–五与 0d/0e 消费契约
# 全部保持;legacy/export_v3/G2/AtomTool 逐字节零触碰(字节专项
# 回归见 S4b 交付书);S4a 既有测试除 profile 版本字面量外零改动。

PPV1_PROFILE_SCHEMA_VERSION = "ppv1-profile-16"
PPV1_CHEMSTATE_SCHEMA_VERSION = "ppv1-chemstate-8"
PPV1_HYPOTHESIS_SCHEMA_VERSION = "ppv1-hypothesis-8"
PPV1_EVENT_SCHEMA_VERSION = "ppv1-event-8"
PPV1_STORE_SCHEMA_VERSION = "ppv1-store-10"
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
# S4a:endpoint 分账契约(四分账/证据字段/F01-F03/独立持久化与首
# 消费;pollutant/endpoint.py)
PPV1_ENDPOINT_SCHEMA_VERSION = "ppv1-endpoint-1"
# S4a:endpoint 派生策略(固定规则;无用户可配项;变更须升版本)
PPV1_ENDPOINT_POLICY_VERSION = "ppv1-endpoint-policy-1"
# S4a:原生结果对象契约(完整字段 + 确定性规范化;正式导出/S4b;
# pollutant/native_result.py)
PPV1_NATIVE_RESULT_VERSION = "ppv1-native-result-1"
# S4b:原生正式导出契约(文件级 payload + manifest + 读取/过期/
# 完整性首消费;pollutant/native_export.py)
PPV1_NATIVE_EXPORT_VERSION = "ppv1-native-export-1"
# S4b:导出策略(固定序列化/命名/无时间戳规则;变更须升版本)
PPV1_NATIVE_EXPORT_POLICY_VERSION = "ppv1-native-export-policy-1"
# S4b:v3 有损投影适配契约(lossy_projection + 原生引用 + 信息损失
# 清单 + 反向消费禁止;pollutant/v3_projection.py)
PPV1_V3_PROJECTION_VERSION = "ppv1-v3-projection-1"
# S4b:run 执行流契约(S3b 起在 runflow.py 消费;v5 = S4b 正式导出
# 与 v3 投影接线。**单一事实源自本批起移入 profile**:runflow 与
# native_export manifest 的 contract_versions 共用本常量,避免
# native_export → runflow 的模块级循环导入)
PPV1_RUNFLOW_SCHEMA_VERSION = "ppv1-runflow-5"
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
# v3(S3a 回修 r3,2026-10-07,Codex S3a 复审 R2 残余 S3A-02/03/04):
# 完整搜索权威与附随语义 —— 预约/attempt 行级内容核验(单位/状态/
# scope-subject/主体共享 alternatives、attempt 状态/hypothesis/
# task),提交记录归属/kind/适用 attempt 引用,done 四入口与 first
# complete/B4 一致消费;附随投影/计划按首提同一判据只读内容核验;
# B3 事件提交前先核必要引用;done submit 返回真实已完成 event 或
# 明确冲突;冻结策略消费区分配置装配与已冻结对象(register 存完整
# 装配块;读取/恢复/预算/认领严格核必需完整键/版本,不补默认);
# 请求已有 row 复用对照 stored 与 incoming 全部身份内容,状态口核
# run 绑定与 expand 必要 attempt,恢复 pending 逐行同源守卫。
# v4(S3a 回修 r4,2026-10-08,Codex S3a 复审 R3 残余 S3A-02/03/04):
# 必要集合完整性 + 请求状态口策略守卫 + 生命周期来源闭合 ——
# _verify_action_references 先按 claim/attempt 现有创建规则同源核
# 必要预约集合(总 action 恒有/transition/expand alternatives+
# attempts+reopens/retrieve 行存在即必须被引用,cache_hit 合法不强
# 加),缺项即使剩余清单非空也先结构化拒,预约 ID 派生与 _reserve
# 单一来源;请求 sent/response/failed 状态口在新 status 写入前消费
# 同一严格冻结块校验(不补默认、无成功状态变化);mark_request_
# failed 正面限定 registered/sent 来源,未知来源结构化拒并保全,
# register 同键复用核存储状态枚举,recover 报告结构化披露枚举外行。
# v5(S3b 批次,2026-10-08):调度与生产链接线 —— 冻结池队列选择
# (schedule_hypotheses:selected/deferred/blocked+原因,池 digest/
# 排序/截断可重放)、record_expansion_outcome(非事件 outcome 持久
# 结论:unresolved_continuation/method_failed 等)、两类 deferred
# (共同产物 coproduct_deferred / 备选反应 alternative_reaction_
# deferred)分别激活(activate_deferred:幂等、trigger 与记录一致、
# expected_parent_revision 匹配、预算不足留独立未展开原因、不重复
# 安排同 action)、条件依赖/显式场景转换进调度(scenario_transition
# 独立 action/预算/记录,须显式 source_ref,仅后效不重写旧边评估)、
# enqueue 支持 initial_status=deferred 与 reactivate_deferred_action
# 状态迁移(消费语义,search_actions 行复用,无新表)。生产链契约见
# pollutant/production.py(固定 AtomTool→供体诊断→converter→audit→
# admission→事件提交,AuditContractError 中止本次 admission/提交,
# 不吞成 verified/R6/成功提交)。
# v6(S3b 回修 r2,2026-10-08,Codex S3b 复审 S3B-02/03/06):调度
# blocked 对象同源持久记录(record_blocked_hypothesis:search_actions
# 行 status=blocked + defer_reason;stop_report 从持久行派生
# depth_limit 停止原因与 blocked_objects 未探索对象清单,不再只存
# blocked 计数;blocked 不是可执行状态 —— reactivate/claim 均拒,
# 不强行执行、零预算预约);恢复裁定的坏 artifact/缺权威 action 明确
# 隔离(isolate_recovered_failure:claimed → blocked +
# defer_reason=recovery_failure:<kind>,claimed_by/attempt/预约行
# 原样保全,不猜重算、不创建成功 event/commit/consume;坏任务不再
# 以 claimed 旧收据授权重执行,合法独立任务继续);转换 action 的
# pending_followup 在创建时一次冻结入载荷(消除"入队后另一次 UPDATE
# 附加"的两写窗口,B4 恢复按冻结载荷幂等闭合)。store 保持 -9(无
# 新表:blocked/隔离复用 search_actions 行;转换附随复用 payload)。
PPV1_SEARCH_SCHEMA_VERSION = "ppv1-search-6"
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
# S3a 回修 r3(2026-10-07,S3A-03):区分**配置装配**与**已冻结对象
# 消费** —— 用户覆盖仍走 validate_search_limits(缺省键合法补默认,
# 输出恒为完整块);已登记存储块的读取/恢复/预算/认领消费改用
# validate_frozen_search_limits 严格核验(非 dict/缺 version/缺任一
# 必需键/未知键/坏类型/越界 ⇒ 拒,不补默认、不猜迁移),register
# 落账完整装配块使合法注册块天然满足严格判据。键/默认/范围/单位/
# 计数语义未动,版本不升(消费语义随 search 契约 ppv1-search-3
# 登记)。
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

# ---- S3b 独立有界格式反馈策略(任务书 §5.3;非 S2 十个搜索上限
# 的旧草案字段,不并入 SEARCH_LIMITS_VERSION) ----
# 适用范围:只有 JSON 字段/类型、允许 ID、语法契约错误可进格式反馈
# (重新请求同一任务的合法格式载荷);结构无法解析记结构失败,不能
# 以格式反馈改分子再试到通过;chemical_reproposal 首版保持 off(化学
# 重提案数 0/路径 unsupported 如实披露)。
# 计数单位:同任务的 JSON 格式修复轮数(**不是** hypothesis 语义
# attempt —— 不占用/不改写 max_attempts_per_hypothesis 语义);每轮
# 持久记录输入/错误类别/反馈版本/次数(model_requests 行,
# purpose=format_feedback,scripted/fake 恒 network 0)。默认 0 = 不
# 发生格式反馈轮(parse 失败即结构失败),范围 0-4。
FORMAT_FEEDBACK_POLICY_VERSION = "ppv1-format-feedback-1"
FORMAT_FEEDBACK_MAX_ROUNDS_RANGE = (0, 4)
FORMAT_FEEDBACK_DEFAULTS: dict = {
    "version": FORMAT_FEEDBACK_POLICY_VERSION,
    "max_format_feedback_rounds": 0,
}


def validate_format_feedback_policy(policy: dict | None) -> dict:
    """校验/归一格式反馈策略块(装配语义:缺省补默认,输出恒完整)。

    - 仅接受 dict 与已知键(version / max_format_feedback_rounds);
    - max_format_feedback_rounds 整数(拒 bool)、范围 [0, 4];
    - version 必须等于当前 FORMAT_FEEDBACK_POLICY_VERSION。
    与 validate_search_limits 同一装配/严格消费分界:已冻结存储块
    读取消费时用 validate_frozen_format_feedback_policy 严格核验
    (不补默认、不猜迁移)。
    """
    out = dict(FORMAT_FEEDBACK_DEFAULTS)
    for k, v in (policy or {}).items():
        if k == "version":
            if v != FORMAT_FEEDBACK_POLICY_VERSION:
                raise ValueError(
                    f"format_feedback_policy.version 非法:{v!r}(当前 "
                    f"{FORMAT_FEEDBACK_POLICY_VERSION})")
            out["version"] = v
            continue
        if k != "max_format_feedback_rounds":
            raise ValueError(
                f"未知格式反馈策略键:{k!r}(允许 "
                f"{sorted(FORMAT_FEEDBACK_DEFAULTS)})")
        if isinstance(v, bool) or not isinstance(v, int):
            raise ValueError(
                f"max_format_feedback_rounds 必须是整数,得到 {v!r}")
        lo, hi = FORMAT_FEEDBACK_MAX_ROUNDS_RANGE
        if not (lo <= v <= hi):
            raise ValueError(
                f"max_format_feedback_rounds={v} 超出允许范围 [{lo},{hi}]")
        out[k] = v
    return out


def validate_frozen_format_feedback_policy(policy: dict | None) -> dict:
    """严格校验**已冻结/已序列化**的完整格式反馈策略块(S3b)。

    与 validate_frozen_search_limits 同一边界:存储块必须是完整冻结
    对象(非 dict/缺 version/缺必需键/未知键/坏类型/越界 ⇒ 拒,不补
    默认)。返回浅拷贝。"""
    if not isinstance(policy, dict):
        raise ValueError(
            "冻结格式反馈策略块必须是完整对象,得到 "
            f"{type(policy).__name__}(不补默认、不猜迁移;消费前拒)")
    if policy.get("version") != FORMAT_FEEDBACK_POLICY_VERSION:
        raise ValueError(
            "冻结格式反馈策略块缺 version 或版本不符:"
            f"{policy.get('version')!r}(当前 {FORMAT_FEEDBACK_POLICY_VERSION};"
            "消费前拒)")
    required = [k for k in FORMAT_FEEDBACK_DEFAULTS if k != "version"]
    missing = sorted(k for k in required if k not in policy)
    if missing:
        raise ValueError(
            f"冻结格式反馈策略块缺必需键:{missing}(不补默认,消费前拒)")
    unknown = sorted(k for k in policy
                     if k not in FORMAT_FEEDBACK_DEFAULTS)
    if unknown:
        raise ValueError(f"冻结格式反馈策略块含未知键:{unknown}")
    out: dict = {"version": FORMAT_FEEDBACK_POLICY_VERSION}
    lo, hi = FORMAT_FEEDBACK_MAX_ROUNDS_RANGE
    for key in required:
        value = policy[key]
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(
                f"格式反馈策略 {key} 必须是整数,得到 {value!r}")
        if not (lo <= value <= hi):
            raise ValueError(
                f"格式反馈策略 {key}={value} 超出允许范围 [{lo},{hi}]")
        out[key] = value
    return out

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
        "format_feedback": FORMAT_FEEDBACK_POLICY_VERSION,
        "endpoint": PPV1_ENDPOINT_SCHEMA_VERSION,
        "endpoint_policy": PPV1_ENDPOINT_POLICY_VERSION,
        "native_result": PPV1_NATIVE_RESULT_VERSION,
        "native_export": PPV1_NATIVE_EXPORT_VERSION,
        "native_export_policy": PPV1_NATIVE_EXPORT_POLICY_VERSION,
        "v3_projection": PPV1_V3_PROJECTION_VERSION,
        "runflow": PPV1_RUNFLOW_SCHEMA_VERSION,
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


def validate_frozen_search_limits(limits: dict | None) -> dict:
    """严格校验**已冻结/已序列化**的完整搜索上限块(S3a 回修 r3,
    S3A-03:区分配置装配与已冻结对象消费)。

    与 validate_search_limits(用户覆盖装配,缺省键合法补默认)的
    边界:本函数用于**已登记存储块**的读取/恢复/预算/认领/请求消费
    —— 存储块必须是完整冻结对象:

    - 非 dict(含 None/null)⇒ 拒(不把缺失块装配成默认额度);
    - 缺 "version" 键或版本不符 ⇒ 拒(不做版本迁移猜测);
    - 缺任一必需预算键(十键)⇒ 拒(不补默认);
    - 未知键/类型错误(含 bool)/越界 ⇒ 拒(与装配期同一类型/范围
      判据,单一来源复用 SEARCH_LIMITS_RANGES)。

    消费方把 ValueError 包装为各自入口的结构化失败(零执行/零预约/
    零补账)。返回浅拷贝(不修改传入块)。合法用户 partial 覆盖本身
    不是坏输入 —— 它应在装配期(register/装配入口)经 validate_
    search_limits 补齐为完整块后再落账,本函数不用于该路径。
    """
    if not isinstance(limits, dict):
        raise ValueError(
            f"冻结搜索上限块必须是完整对象,得到 {type(limits).__name__}"
            "(不补默认、不猜迁移;消费前拒)")
    if limits.get("version") != SEARCH_LIMITS_VERSION:
        raise ValueError(
            f"冻结搜索上限块缺 version 或版本不符:{limits.get('version')!r}"
            f"(当前 {SEARCH_LIMITS_VERSION};消费前拒)")
    required = [k for k in SEARCH_LIMITS_DEFAULTS if k != "version"]
    missing = sorted(k for k in required if k not in limits)
    if missing:
        raise ValueError(
            f"冻结搜索上限块缺必需键:{missing}(已冻结对象不补默认,"
            "消费前拒)")
    unknown = sorted(k for k in limits if k not in SEARCH_LIMITS_DEFAULTS)
    if unknown:
        raise ValueError(f"冻结搜索上限块含未知键:{unknown}")
    out: dict = {"version": SEARCH_LIMITS_VERSION}
    for key, (lo, hi) in SEARCH_LIMITS_RANGES.items():
        value = limits[key]
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"搜索上限 {key} 必须是整数,得到 {value!r}")
        if not (lo <= value <= hi):
            raise ValueError(
                f"搜索上限 {key}={value} 超出允许范围 [{lo},{hi}]")
        out[key] = value
    return out


def build_profile_identity_block(
    *,
    input_preview_policy: str = INPUT_PREVIEW_POLICY_DEFAULT,
    chemical_reproposal: str = CHEMICAL_REPROPOSAL_DEFAULT,
    search_intent: str | None = None,
    search_limits: dict | None = None,
    format_feedback_policy: dict | None = None,
) -> dict:
    """pollutant_pathway_v1 的 run 身份 profile 块(全部开关进身份)。

    未知取值 fail-closed(ValueError,装配期拒绝),不静默回退默认。
    search_limits 为实际可执行版本 v3(S3a 底座计数);format_feedback_
    policy 为 S3b 独立有界格式反馈策略(缺省补默认 0 轮;不并入
    search_limits 十键、不当旧草案字段)。S3b 起 run 执行入口
    (workflow.runner start_run/resume_run)按 profile 分流到 PPV1
    独立执行/存储。
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
        "format_feedback_policy": validate_format_feedback_policy(
            format_feedback_policy),
        # S0–S2 交付领域契约/上下文/固定诊断;S3a 交付持久搜索底座
        # (身份/预算/认领/恢复);S3b 交付队列化学集成/生产中心证据链/
        # PPV1 runner 分流(公开 start_run/resume_run 开放 PPV1 路径);
        # S4a 交付 endpoint 四分账/证据/F01-F03/独立持久化与原生结果
        # 对象底座;S4b 交付正式文件导出/文件级 G02 过期识别/v3 有损
        # 投影与完整公共链(科学性能评测仍属 S5)
        "delivered_stages": "S0-S2,S3a-base,S3b,S4a-endpoint,S4b-export",
    }
