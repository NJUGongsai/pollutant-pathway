# pollutant_pathway_v1:S3b 批次交付书(2026-10-08)

- 基线:直接父 `b7f2bba02ca49edd0a45a13bc9b8434909d99175`
  (S3a 回修 r4,S3a 复审 R4 放行:P1 清零,S3b 可启动);
  本批 = S3 第二批(完整 S3 收尾批),按任务书
  `POLLUTANT_PATHWAY_S3_IMPLEMENTATION_TASK_2026-10-07.md` §2.3 b 行
  + §5/§6 规格 + 复审 R4 §8 交接五条实施。
- 范围:S3b 全部(队列选择/两类 deferred 分别激活/条件依赖与
  显式场景转换进调度/proposals[] 模型协议与有界格式反馈/固定
  AtomTool→供体诊断→converter→audit→admission→事件提交生产
  调用链/PPV1 独立 runner start_run/resume_run 分流/全 S3 集成
  验收);不做 S4/S5、不加化学判据或机制库、判据未冻结。
- 证据根:`docs/review_evidence/ppv1_s3_impl_2026-10-08/s3b_r1/`
  (README+manifest.json+SHA256SUMS;所有执行在仓外新 tmp)。

## 0. 结论一句话

S3b 全部交付并接进公开入口:PPV1 全量 **851 passed/0 skip**
(787 存量 + 64 新),新测试在直接父基线 b7f2bba 同字节对照
**4 行为红(均为有意翻转)+ 4 collection 红(新模块缺失)**,
G01 安全隔离 **1453/8/17 exit 0(286 输入)**;生产链成为 S3
首个 audit_hypothesis 生产 caller,AuditContractError 不吞成
成功(宽捕获零写入负控);四崩溃经**独立子进程硬杀 + 新进程
resume** 实证;legacy 运行时行为零改变(共享 runner.py 文字变更
使 legacy code_identity 聚合变化,逐项披露)。

## 1. 任务书 §7 S3b 行逐项:行为 → 源码 → 证据

### 1.1 队列选择 + record_expansion_outcome + activate_deferred(E01/E02)

**入口矩阵**:`pollutant/queue.py`(`schedule_hypotheses`
:150-316 / `record_expansion_outcome`:317-396 /
`activate_deferred`:397-475 / `enqueue_scenario_transition`
:476-526 / `enqueue_coproduct_followups`:527-640;child_path_id
:101-107;frozen_pool_digest:109-118);底座增量
`pollutant/search.py`(`enqueue_action` initial_status=deferred
:778-902;`reactivate_deferred_action`:956-1087;
`pending_action_ids`/`actions_with_status`:929-955)。

- **schedule_hypotheses(parent, frozen_pool, context, budget)**:
  产 selected/deferred/blocked+原因;池 digest(条目身份+声明次序)
  进冻结任务输入;剩余 alternatives 从预约行派生(快照不是事实源);
  选中受剩余额度与调用方 `budget.max_select` 双重限制;深度超限整池
  blocked 不入队;同键异内容拒(池变化须新 revision 重排,不改写
  旧 action);同身份已 done ⇒ blocked already_expanded(无新信息
  不再安排)。
- **record_expansion_outcome(attempt_id, outcome, evidence_refs)**:
  attempt 存在/归属/open + action claimed + 认领者核验;outcome
  kind 枚举(method 类失败 ⇒ attempt failed,其余 recorded);
  结论 artifact 先写(不可覆盖);结算走 complete_action
  (S3A-02 完整权威核验)。
- **activate_deferred(parent, trigger, expected_parent_revision,
  budget)**:两类 deferred(alternative_reaction_deferred/
  coproduct_deferred)分别激活(按 payload deferred_type 过滤,
  不混队);`reactivate_deferred_action` 同一判据:pending/
  claimed/done ⇒ unchanged already_active(重复触发幂等)、旧
  revision ⇒ unchanged stale_parent_revision、trigger 与冻结激活
  条件不一致 ⇒ 逐项结构化冲突、预算预检(总 action/转换/expand
  的 alternatives)不足 ⇒ unchanged budget_exhausted(**独立未展开
  原因**,不改状态;claim 才是权威预约);不重建任务输入、不覆盖
  冻结身份列。
- **E01(公开 start_run 端到端)**:
  `tests/test_ppv1_s3b_runner.py::test_e01_preferred_downstream_
  no_candidate_alternatives_continue` —— B/C 两备选,各自事件与
  attempt recorded 保留;B 与 C 的下游 followup 池空 ⇒ 两条
  no_local_candidate + unresolved_continuation(引用来源事件,
  不反证上游);C 在上限内继续。
- **E02(公开 start_run 端到端)**:
  `test_e02_two_deferred_types_activation_and_idempotence`
  (备选激活后 C 提交事件;[H][H] 共同产物完整入事件不截断;
  coproduct deferred 留 product_width_limit 原因;旧 revision
  unchanged)/ `test_e02_budget_insufficient_keeps_unexpanded_
  reason`(alternatives 耗尽 ⇒ 激活 unchanged budget_exhausted,
  deferred 保持)。

### 1.2 条件依赖/显式场景转换进调度(C06/H04/分支隔离)

**入口矩阵**:分支上下文派生 `runflow.py:511-532`
(`_derive_branch_context`:带自身要求/依赖的假设经
derive_child_context 派生专属上下文,persist_context 落 artifact);
转换执行 `runflow.py:831-875`(`_run_transition`:derive_child_
context(scenario_transition) 冻结旧阶段快照,只后效;followup
用新上下文);转换入队 `queue.py:476-526`(source_ref 必需);
H04 依赖构建 `production.py:98-144`(`build_cyclic_dependency`
:initial_supply=missing ⇒ unresolved + unresolved_initial_supply
标记(不称化学不可能);supported ⇒ resolution_log initial_supply
轴 supported,不自动阻断)。

- **C06**:`test_c06_h04_unknown_bounded_exploration_and_
  initial_supply` —— 调度→audit→admission→提交→子路径:事件
  提交(admission retain_conditional,R5 unknown 保留不升格);
  分支上下文依赖 dep-NAD unresolved + unresolved_initial_supply;
  生产报告 artifact 落盘(审查用派生报告)。
- **H04**:`test_h04_supported_initial_supply_not_blocked`
  (supported 不自动阻断,事件提交)+ 上一条(missing ⇒
  unresolved_initial_supply,不 reject)。
- **essential conflict**:`test_essential_conflict_blocks_current_
  scenario_hypothesis_kept` —— 冲突阻当前场景(零事件),假设
  put_hypothesis 留痕(R3 defer;可展示为需不同条件的备选)。
- **分支隔离**:`test_branch_isolation_two_contexts` —— 带要求
  分支派生专属上下文,无要求分支用根上下文,互不污染。
- **场景转换**:`test_scenario_transition_explicit_only_effect_
  future` —— 显式 source_ref(缺失 ⇒ 契约失败如实停止
  run_error=transition_source_ref_missing,不自行换场景);独立
  action/预算(max_scenario_transitions 预约=1,与反应边分账);
  只后效(新上下文 phase-1/anaerobic;followup retrieve 用新
  context_ref;旧边评估冻结于 phase_history)。

### 1.3 proposals[] 模型协议与有界格式反馈

**入口矩阵**:`pollutant/model_protocol.py`(`parse_model_
proposals`:76-230 / 错误分类 FORMAT_ERROR_*:43-52 /
`register_format_feedback_round`:241-310 / `format_feedback_
rounds_used`:231-240);策略 `profile.py`(FORMAT_FEEDBACK_
POLICY_VERSION ppv1-format-feedback-1,默认 0 轮、范围 0-4、
validate/validate_frozen 双入口:289-360);驱动消费
`runflow.py:533-605`(`_model_proposals`:登记→解析→(可反馈
错误)有界反馈轮→重试;结构失败如实停止)。

- **协议**(`test_ppv1_s3b_model.py`):proposals[] 每项一条独立
  假设;rank 引稳定 ID(模型选择不升成 recorded —— 解析结果只是
  提案引用);空列表/弃权合法;池外 ID 必须走 novel 有界
  proposal_context(reference_hypothesis_ids ∈ 池、output_origin
  明示,不伪造来源);共同产物是假设内部声明,不作为独立提案
  (备选与共同产物不混);重复提案/未知 rank ⇒ 结构化拒。
- **有界反馈**:独立策略键(非 S2 十上限旧字段);只有 JSON
  字段/类型/允许 ID/语法错误可进反馈(FEEDBACK_ELIGIBLE);
  not_json ⇒ structure_unparseable 记结构失败(**不进反馈、不能
  以反馈改分子再试到通过**);每轮持久记录(model_requests 行
  purpose=format_feedback:输入/错误类别/反馈版本/次数;轮数从
  持久行复算);超上限 ⇒ SearchBudgetExhausted(结构失败保持);
  默认 0 轮 ⇒ 可反馈错误同样升级结构失败;chemical_reproposal
  首版 off(路径 unsupported 如实披露)。
- **真实默认 off/0**:`test_real_provider_feedback_registration_
  refused`(real + 额度 0 ⇒ 登记被拒,网络发送被阻止)+
  runner 级 `test_model_object_does_not_derive_real_request_
  budget`(传 model 对象:max_real_model_requests 恒 0、网络 0、
  decide 记方法失败);scripted 恒 network_request_count=0。

### 1.4 固定生产调用链(R8 P2 ⑧ 义务闭合)

**入口矩阵**:`pollutant/production.py`(`execute_atomtool_
expansion`:263-313(冻结 AtomTool render/execute_edits 真实调用
→ check_edit_against_donor → center_evidence_from_donor_
diagnostic,零写账)/ `expand_hypothesis_production`:341-505
(audit → decide_admission → build/submit_event → complete;
生产报告 artifact)/ `persist_context`/`load_context`:315-339
(H07 包装 + from_dict 内容身份核验)/ `prepare_hypothesis`
:145-209(单一构建源:调度取 hypothesis_id 与执行重建同对象));
驱动窄捕获 `runflow.py:641-660`(except AuditContractError)。

- **合法链**:`test_ppv1_s3b_production.py::test_expand_production_
  legal_chain_submits_event` —— 真工具输出产生可复算绑定证据
  (diagnostic.center_evidence 带 proof_record 完整输入集;audit
  内部复算);事件经公共 writer 提交;production_report artifact
  落盘。
- **三个 None**:`test_execute_atomtool_failure_three_none` +
  `test_expand_production_execution_failure_method_failed` ——
  execution_ok=False ⇒ 三判定字段 None、center_evidence 空字典、
  converter 元数据 center_match=None;方法失败零事件/零提交
  (attempt 由调用方落 failed;不伪装成功工具结果)。
- **缺映射**:`test_expand_production_missing_alignment_unknown`
  —— alignment unavailable ⇒ 中心 unknown;按既有 admission
  R5 有界探索(事件可提交,unknown 保留),不授 verified。
- **偏离**:`test_expand_production_strict_deviation_not_
  verified` —— 期望产物 ≠ 执行产物 ⇒ 中心不可 verified(strict
  False ⇒ 至少 unknown)。
- **损坏 proof(宽捕获负控,R8 P2 ⑧)**:
  `test_expand_production_tampered_proof_contract_error_zero_
  writes` —— converter 输出被篡改(自报 center_match 与
  proof_record 复算不一致)⇒ AuditContractError 由生产链原样
  上抛;**宽捕获(except Exception: pass)下零事件/零提交/零
  完成/零假设写入,action 保持 claimed**;修复后同链正常提交
  (中止不是永久损坏)。
- **跨假设复用**:`test_expand_production_cross_hypothesis_
  evidence_unknown` —— 证据绑定不匹配 ⇒ 中心 unknown(注册名+
  True 不构成核实)。
- **上下文持久化/篡改**:`test_context_persist_load_roundtrip_
  and_tamper` —— 两层防线逐一分测(信封 hash ⇒ H07;同步重算
  hash 伪装 ⇒ from_dict 内容身份核验拒)。

### 1.5 PPV1 独立 runner 分流(公开 start_run/resume_run)

**入口矩阵**:`workflow/runner.py:215-228(start 分流:ppv1_plan
参数 + start_ppv1_run 派发)+ 305-320(resume 分流)+
134-150(_refuse_undelivered_profile 改为分流后口径)`;执行流 `pollutant/runflow.py`(start_ppv1_
run:921-975 / resume_ppv1_run:1004-1065 / _Driver 驱动循环
:267-346 / _inflight_action_ids:255-268(B1 同 worker 幂等
reclaim 续跑)/ reconcile_followups:205-254(B4 事件已提交、
followup 未调度的权威补调度)/ 原子独占 run 目录:952-953
(并发 start 单胜者))。

- **PPV1 独立存储**:`test_ppv1_independent_storage_and_no_
  legacy` —— pollutant.sqlite;无 legacy pathway.sqlite/
  checkpoint.sqlite;公开入口不落 legacy CN/PathwayStore/LangGraph。
- **身份/分流**:`test_duplicate_start_rejected`(原子独占目录
  创建,并发单胜者)/ `test_unknown_profile_rejected` /
  `test_resume_identity_mismatch_rejected`(prediction 身份变动
  ⇒ IdentityMismatch,不原地切换)/ `test_resume_legacy_profile_
  run_refused_by_ppv1_path`(legacy 身份不走 PPV1 resume)。
- **四崩溃(子进程硬杀 + 新进程 resume)**:
  `test_crash_recovery_subprocess_hard_kill[after_claim|
  after_request_registered|after_bundle_written|
  after_event_submitted]` —— 真实进程崩溃(os._exit,连接不
  清理)→ 新进程 resume:身份核对 + recover_run(B4 幂等补账/
  B3 消费同一 output/B1 同 worker 续跑/B2 pending 披露)+ 继续
  驱动;事件仅一次、commit 恰好 4 条(retrieve/decide/expand/
  followup,不重复扣);B2 场景网络恒 0、不默发第二请求(
  `test_b2_pending_request_disclosed_not_resent`)。
- **并发(双进程 barrier)**:
  `test_concurrent_barrier_start_single_winner` —— 双进程
  barrier 同时 start 同一 run:一方 RunAlreadyExists;事件恰一。
- **模型预算纪律**:见 1.3;start 的 legacy 预算参数(max_depth
  等)对 PPV1 不生效(搜索预算事实源是 search_limits)。

### 1.6 全 S3 集成验收与继承控制

- E01–E04:E01/E02 见 1.1(公开 start_run 端到端);E03(身份/
  attempt 不复用旧 decision)与 E04(预算账表)由 S3a r4 全量
  继续覆盖(787 存量全绿,action/attempt 任务键、预算复算、
  零预算/循环稳定停不动);S3b 集成层 `test_ppv1_s3b_queue.py`
  的调度幂等/池 digest/任务输入冻结继续按同键异内容拒。
- C06/H04–H08:C06/H04 见 1.2;H05(停止主因优先级/未探索
  集合)由 stop_report 消费(S3a 存量 + `test_stop_report_
  deferred_blocks_exhausted_search_claim`:deferred 存在时不称
  exhausted_search);H06(并发认领)S3a 双连接 barrier 全绿 +
  runner 级 barrier 单胜者;H07(artifact 完整性)S3a 存量 +
  上下文两层防线;H08(提交事实与 ledger 不一致)S3a 存量全绿。
- R8 继承:restore/direct/context derive/首提/replay 的 R7/R6
  反例保持拒绝(S3a r4 契约族未动:chemstate/hypothesis/event/
  context/audit 契约保持 -8);本批不改 store(-9)/search-limits
  (-3)。

## 2. 版本/身份/Hash 影响(逐项披露)

- `PPV1_SEARCH_SCHEMA_VERSION`:ppv1-search-4 → **ppv1-search-5**
  (调度/两类 deferred/转换/生产链消费语义;计数键/默认/范围/
  单位未动);`PPV1_PROFILE_SCHEMA_VERSION`:-12 → **-13**
  (contracts 登记 + format_feedback-1 + delivered_stages
  S0-S2,S3a-base,S3b);新增 **FORMAT_FEEDBACK_POLICY_VERSION
  = ppv1-format-feedback-1**(独立有界策略,非 search_limits
  字段);store 保持 **ppv1-store-9**(无新表:两类 deferred
  复用 search_actions 行 + defer_reason/payload;格式反馈轮计数
  复用 model_requests 行;context 持久化走 artifact + from_dict
  内容身份核验);search-limits 保持 **-3**。
- **legacy code_identity(重要披露)**:共享 `workflow/runner.py`
  文字变更(PPV1 分流)⇒ legacy code_identity 聚合
  `4ea99b69…07c29ae` → `18007e6a…f1374d6`(旧 run 跨此变更的
  resume 按既有身份门槛拒绝,是设计行为;legacy 运行时行为零
  改变 —— G01 内 legacy 回归全绿;PPV1 分流代码全部在
  pollutant/ 新包,legacy 身份不绑定)。PPV1 code_identity 哈希
  全树(见证据 code_identity_after.txt)。
- 更新的既有测试仅 2 文件:`tests/test_ppv1_profile.py`(版本
  字面量 -12→-13/search-4→-5 + format_feedback 断言 +
  delivered_stages + runner 分流断言翻转)与
  `tests/test_ppv1_s3a_search.py`(runner 拒绝测试翻转为分流
  测试);其余 S3a/S0-S2 测试零改动全绿。

## 3. 独立执行数字(depending43 Python 3.11.16 / RDKit
2026.03.6 / SQLite 3.53.4;PYTHONDONTWRITEBYTECODE=1、-B、
pytest -p no:cacheprovider)

| 执行 | 结果 | 证据 |
| --- | --- | --- |
| PPV1 全量(31 文件 = 26 存量 + 5 新) | **851 passed / 0 skipped / 0 failed**,exit 0,pytest 16.04s | `current/ppv1_full/`(junit+summary) |
| 新 S3b 测试(4 文件) | **64 passed**,exit 0,7.17s | `current/s3b_new/` |
| 父 b7f2bba detached worktree 同字节更新的 2 既有文件 | **4 failed / 64 passed**(2 版本字面量红 + 2 runner 分流翻转红) | `baseline/updated_existing_*` |
| 父 b7f2bba 同字节 4 个新 S3b 文件 | **4 collection errors**(queue/model_protocol/production/runflow 模块缺失) | `baseline/s3b_new_*` |
| 四崩溃(独立子进程硬杀 B1–B4 + 新进程 resume)/B2 网络不默发/双进程 barrier | **6 passed**(参数化 4 + b2 + barrier) | `current/s3b_new/junit.xml` |
| 安全隔离 G01(s3b_r1 控制器 = s3a_r4 控制器 + S3b 输入) | **1453 passed / 8 skipped / 17 deselected**,exit 0,pytest 202.40s | `g01/`(preparation/execution/junit/stdout) |

G01:286 输入 = r4 277 + 9 新增(4 新 src 模块(queue/
model_protocol/production/runflow)+ 4 新测试 + s3b_worker.py;
runner.py/profile.py 为 277 内已有路径的更新副本,非新增);
fresh SHA256、实际 HEAD+脏状态记录;8 skip =
5 真实评价 + 1 v4 对照 + 2 phase_d 派生 metadata;17 deselect =
16 slow + 1 显式排除 export 用例;零金标/题面/封存/v4/真实
provider,网络 0;1453 = r4 1389 + 64。历史 R7 1110/R8 1138/
S3a 首批 1196/r2 1250/r3 1299/r4 1389 各自单列不混计。全部
工程数字不外推 dev(B1 环境中间步骤)或 298(RHEA 通用酶学)
科学性能。

## 4. 复审 R4 §8 交接五条逐项对照

1. **先列生产消费入口再接链**:入口矩阵见 §1 各节(调度 5 入口/
  模型协议 3 入口/生产链 5 入口/runner 分流 2 入口 + reconcile);
  首消费 state/context/hypothesis/ledger 守卫继续消费(上下文
  load 走 from_dict 内容身份;假设/状态经公共 writer;put_state
  不当 ledger 证书;只读收据不代替完整证明)✓。
2. **化学中心接真实调用链并测异常**:固定链 + 宽捕获负控 +
  三个 None + 分段负控(§1.4);R2b 映射与构造拒绝分别落字
  (mimo v13 0c-v13 第 5 条;R2b 由调用方 contract_violation
  触发,AuditContractError 中止而非降级 R 行)✓;不改冻结
  legacy/G2/AtomTool(只调用)✓。
3. **保留真实预算与恢复语义**:预算预约/consume/release 不重扣、
  悬空不默发(B2 网络 0)、身份幂等(run 目录原子独占 + 同
  worker reclaim)、并发认领(双进程 barrier)✓;cache 来源/
  认领分支不持久化的已登记限制保持(S3a R4 §5 边界原样,本批
  未扩大历史保证;claim 的 cache_hit 语义未改)✓;不宣称外部
  provider exactly-once 或任意 SQL 并发安全 ✓。
4. **runner 放开以接线验收为条件**:分流先于拒绝解除(先建
  runflow 再删 _refuse;legacy 分支行为保持);接线验收 = §1.5
  全部真实公共链测试;legacy 行为(G01 全绿)与 identity 变化
  (§2 聚合哈希逐项披露)✓。
5. **交付同步 P2 落字**:11+1 父绿精度、各入口 kind/reason 层次、
  未知系数账、omission 及声明清单边界、R2b/R1 对象范围、条件
  事实真实性、异常不当 R 行 —— 七条落进 mimo v13 请求 0c-v13
  节(§5);新行为对直接基线如实分行为红/字段红/collection 红/
  保持控制(§3)✓。

## 5. mimo v13 请求与外送边界

- `docs/mimo_ppv1_chem_review_request.md` 升级 **v13(S3b)**:
  新增 0d 节(S3b 生产链与调度消费契约八条:固定链与顺序/
  caller 异常义务/三个 None/分段负控/两类 deferred/条件场景/
  模型协议与格式反馈/runner 分流)与 0c-v13 节(R4 §8.5 七条
  P2 落字);判据一–五正文与 v12 相同(无新化学机制);§6 数字
  与契约版本更新(含 legacy code_identity 披露)。v12 送审快照
  存 `s3b_r1/mimo/`。
- 本批实施 agent 未调用任何外部模型;请求由主会话按通道 A 送审,
  回应落盘后按互证原则采信。

## 6. 自查未闭合残留(诚实清单)

1. **判据未冻结、科学性能 pending**:全部数字为工程合成规则级
  契约结果,不代表 dev/298 科学性能;S4(终点推断/原生导出)与
  S5(评测器/真实数据/阈值)未启动。
2. **计划(plan)是合成/规则级驱动输入**:PPV1 的真实检索/池
  来源(检索 provider、真实冻结池构建)属后续阶段;当前驱动
  循环消费合成计划池(scripted),网络 0。这不影响契约面(调度/
  预算/恢复/生产链全部经真实公共入口验证)。
3. **cache_hit 同构边界(S3a R4 §5 已接受 P2)保持**:本批未
  持久化 cache 分支标记,未扩大历史保证;S3b 驱动的 retrieve
  claim 未使用 cache_hit 路径(池来自计划,无缓存复用场景)。
4. **两事务间窗口与外部 SQL 并发**(S3a 已登记边界,保持):
  complete 只读预核验与写事务之间不持锁;顺序单消费者/合法公共
  writer 模型内无窗口。
5. **B4 followup 补调度的转换交互边界**:`reconcile_followups`
  按事件引用幂等补调度;若崩溃点恰在转换 action 入队之后、
  followup 附加之前,恢复后 followup 以事件 action 的(转换前)
  上下文调度 —— 事件权威与预算不受影响,转换对后续阶段的
  "只后效"以转换 action 的实际执行时点为准。该窗口在测试矩阵
  未单独注入(登记为已知窄边界)。
6. **模型格式反馈的 scripted 重试语义**:反馈轮的"重试响应"
  来自计划响应队列(scripted),不发起网络;真实 provider 的
  反馈重试属付费请求路径,默认 off/0 下不可达(登记)。
7. **mimo v13 与 Codex 复审待跑**:由主会话按通道接力;本批
   实施未联系审核方。

## 7. 提交

- v4.3 本地提交(不 push;git add 仅显式路径):
  `src/pathway_v43/pollutant/{profile,search,queue,model_protocol,
  production,runflow}.py`、`src/pathway_v43/workflow/runner.py`、
  `tests/test_ppv1_s3b_{queue,model,production,runner}.py`、
  `tests/s3b_worker.py`、`tests/test_ppv1_profile.py`、
  `tests/test_ppv1_s3a_search.py`、
  `docs/POLLUTANT_PATHWAY_S3B_DELIVERY_2026-10-08.md`、
  `docs/mimo_ppv1_chem_review_request.md`、
  `docs/review_evidence/ppv1_s3_impl_2026-10-08/s3b_r1/`;
  提交哈希见 `git log -1`。既存 AGENTS.md 用户差异与旧未跟踪
  评审材料不纳入提交;store.py 未改不提交。
