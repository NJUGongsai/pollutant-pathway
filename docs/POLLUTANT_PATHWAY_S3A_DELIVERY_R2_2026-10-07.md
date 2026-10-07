# pollutant_pathway_v1:S3a 回修轮(r2)交付书

日期:2026-10-07,Asia/Shanghai。仓库 `/Volumes/CC/Enzyme_Agent/dependingv43`,
v4.3 分支,直接父基线(实施前 HEAD)`9b78f4279cc6fa50b3b51c31a5c8e07abbeda207`。

**结论:本回修轮按 Codex S3a 复审 §4/§8 闭合五组 P1(S3A-01~05),不实施
S3b、不加机制库/科学性能门/外部 exactly-once。** PPV1 全量
**648 passed / 0 skipped / 0 failed**(594 存量 + 54 r2 新回归);r2 新回归在
直接父基线 9b78f42 detached worktree 同字节运行 **52 行为红 / 2 正控绿**
(坏案按预期失败 = 修前缺口;合法正控在两侧均绿);安全隔离 G01
**1250 passed / 8 skipped / 17 deselected**(1196 + 54;8 项缺席依赖与
17 排除逐项披露)。runner 双入口对 PPV1 继续 fail-closed;S3b 未交付项
逐条诚实列出(§9)。数字为工程契约结果,不代表 dev(B1 环境中间步骤)
或 298(RHEA 通用酶学)科学性能;判据未冻结。

- 复审报告:`docs/POLLUTANT_PATHWAY_S3A_CODEX_REVIEW_2026-10-07.md`(§4
  证据与最低验收、§8 有限回修提示词;其永久证据
  `docs/review_evidence/ppv1_s3a_codex_2026-10-07/` 只读,本轮未在原地
  执行探针);
- 本轮证据:`docs/review_evidence/ppv1_s3_impl_2026-10-07/s3a_r2/`
  (README/manifest/SHA256SUMS + 全部 stdout/stderr/JUnit/前后账与哈希);
- mimo v10 请求:`docs/mimo_ppv1_chem_review_request.md`(自包含展开;
  v9 快照在本批证据;**由主会话送审,实施 agent 未调用外部模型**)。

## 1. 入口矩阵(回修 r2;每处消费对象/身份/版本/权威及校验来源)

全部位于 `src/pathway_v43/pollutant/search.py`(行号为本次交付后),
`profile.py` 为单一十键校验实现,`store.py` 未改(公共 writer 冻结语义
不动,权威核验复用其公开 `submit_event` 重放分支,不在 search 层复制):

| # | 入口(file:line) | 消费对象 | 权威/校验来源(r2 后) |
| --- | --- | --- | --- |
| 1 | register_search_run(:533) | profile 身份块 search_limits | 十键类型/范围/版本同源校验(profile.validate_search_limits;四非法块零写入拒);幂等/异块冲突保持 |
| 2 | _limits(:584) | 存储策略块(读取) | 同一 validate_search_limits(存储块被改坏 ⇒ 消费前 search_policy_block_corrupt 拒) |
| 3 | enqueue_action(:622) | 任务身份输入 | 幂等/同键异内容冲突/深度/宽度结构性拒绝(未动) |
| 4 | claim_action(:779) | 冻结 action 行+预算 | BEGIN IMMEDIATE 单赢家;done 复用分支经 _verify_done_action_authority(:1730)完整权威核验 |
| 5 | register_model_request(:984) | 请求载荷+执行引用 | action 存在/属本 run/claimed;attempt 存在/归属/open(expand 必须绑 attempt,非 expand 合法空);同键异 action/purpose/payload_hash/retry_of ⇒ SearchIdentityConflict 零写入;real 登记即时占额 |
| 6 | _verify_request_execution(:1170)+ sent/response/failed(:1237/:1270/:1297) | 请求状态迁移 | 状态机 + 执行引用闭合(action 仍 claimed、attempt 仍 open;已释放执行权不可继续发送/记响应/记失败) |
| 7 | submit_action_event(:1331) | PathwayEvent | owner + _verify_event_frozen_to_action(:1379,判据经共用 _event_identity_mismatch:354)+ 公共 store.submit_event;done 复用分支同 4 |
| 8 | write_commit_bundle(:1394) | 事件+投影+计划+states+假设 | 新增:action 须 claimed、事件身份冻结(同 7 同一判据)、task_key 绑定(双方非空须一致);写侧先拒,artifact 不可覆盖保持 |
| 9 | complete_action(:1747) | 认领所有权+事件/引用权威 | _preverify_completion(:1691)写事务前只读权威:事件类 outcome ⇒ _verify_event_outcome(:1623,非空/存在/身份列冻结/完整账权威)+ 已有记录的幂等复用同样核验+_verify_commit_record_hash(:1670);写事务内 _verify_action_references(:1461,预约/attempt 行存在/归属,主体作用域 alternatives 按设计共享并核 scope/subject);非事件 outcome(COMMIT_KIND_OUTCOME)按适用契约保留不强加 event |
| 10 | defer_action(:1884) | 认领所有权+未执行事实 | 先核:提交记录/冻结身份下未归因他人的已提交事件/sent·responded·failed 请求/recorded·failed attempt ⇒ defer_after_execution 拒;合法未执行:释放 reserved、abandon open attempt、registered 请求转 abandoned(真实请求占额不释放);引用行核验 |
| 11 | recover_run(:2159) | 持久权威记录 | done 分支 _verify_commit_event(:2334,身份列+记录哈希+完整事件账权威);B4 经 complete_action 全套核验;B3 先验 read(hash/反序列化)+ _verify_bundle_identity(:2376,事件完整身份冻结+task_key 绑定)再消费,失败与 H07 同样按单 action 保全处置不中断其余;B1 引用行核验;B2 悬空只披露不默发 |
| 12 | budget_snapshot(:2027)/stop_report(:2059) | 持久记录派生值 | 快照从预约行复算(未动);停止报告新增 claimed_actions/open_attempts 披露并阻止 exhausted_search |

完整事件账权威核验 `_verify_event_ledger_authority`(:1557)的强度来源:
重建事件后调用公共 `store.submit_event` 的**重放分支**——同源校验
states/出现/假设/投影/计划/事件清单/links 行齐全且内容一致(12 类坏
事件账逐类覆盖);`get_event/find_event` 读视图只用于身份列比较,不再
当完整性证书。核验只读零写入(重放路径事务结尾回滚),在 complete 的
写事务**之前**执行;写事务内对预约/attempt 引用行重读核验。核验与写
事务之间的极端并发窗口按顺序消费模型如实披露(单进程消费链内无窗口;
并发写期间 SQLite busy 以 SearchConcurrencyError 可见,不当化学拒绝)。

## 2. 逐 P1:入口 → 行为(前/后)→ 证据

### S3A-01:B3 消费有效但属于别的身份的事件

- **修前行为(9b78f42)**:B3 恢复(recover_run:1515-1585 旧行号)只验
  bundle 的 action/条件性 attempt 引用与事件自推导 ID;事件 run/parent/
  context/hypothesis 与当前 action 的闭合缺失 —— 四类异身份有效事件
  (仅 run/parent/context/hypothesis 之一不同)经 `write_commit_bundle →
  recover_run` 全部插入:event 0→1、commit 0→1、A claimed→done;
  同一事件经正常 submit_action_event 却被拒(零写入)。
- **修后行为**:共判据 `_event_identity_mismatch`(:354,判 run/parent/
  context + expand 的 hypothesis)被 submit(:1379)、**写侧**
  write_commit_bundle(:1394,先于 art.write)、**消费侧**
  _verify_bundle_identity(:2376,含 task_key 绑定)三处共用;B3 身份
  失败与 H07 字节损坏同样按单 action 完整性处置(保全原文件、零
  event/commit/consume、恢复不中断其他 action)。
- **证据**:`tests/test_ppv1_s3a_rework_r2.py`
  `test_b3_wrong_identity_event_rejected_before_consume[run|parent|context|hypothesis]`
  (四分案:disposition kind=bundle_event_identity_not_frozen、events=0、
  commits=0、action 仍 claimed、artifact 字节保全、二次恢复同样拒绝;
  同一 B 经正常提交拒)、`test_write_bundle_rejects_wrong_identity_event`
  (写侧零落盘 + task_key 错绑拒)。基线:4 红。
- **保持**:合法 B3 同一 output/attempt 一次落 event、二次恢复零新增
  (既有 test_b3 全绿);hash/反序列化负控保全(既有 test_b3_corrupt);
  合法不同 parent/context 新 action(既有 test_context_change…)。

### S3A-02:首次完成与 B4/done 恢复只信索引

- **修前行为**:complete_action 在消费预约/写 done 前不核事件存在/
  适配/完整;B4 `find_event` 命中即补;done/已有 commit 的
  `_verify_commit_event` 只看 get_event 四个身份列 —— 首次 complete 指向
  不存在/另父事件先写 done/commit/consume 成功(下次恢复才拒);删
  预约/attempt 行 UPDATE 0 行仍补 done;事件 payload 损坏仍补账;
  继承专项 12×2 坏事件账 24/24 recover 成功(正常 writer 重放 24/24 拒)。
- **修后行为**:complete_action 阶段 1(_preverify_completion:1691,写
  事务前只读)—— 事件类 outcome 须 event_id 非空(commit_event_id_
  empty)、事件行存在(commit_event_missing)、身份列冻结
  (commit_event_identity_mismatch)、完整账权威(event_ledger_
  authority_failed / commit_attached_record_missing,公共 writer 重放
  同源);**已有提交记录的幂等复用**同样核验(记录引用事件 + 记录
  哈希复算 commit_record_hash_mismatch);阶段 2(写事务内)
  _verify_action_references:claim 必留预约引用、expand 必留 attempt
  引用、逐行存在/归属(主体作用域 alternatives 按设计共享,核
  scope=parent/subject=hypothesis)、认领链下已释放预约 ⇒ 不变量破坏。
  非事件 outcome 走显式 COMMIT_KIND_OUTCOME,不给 decide/retrieve
  强加 event。
- **复用入口同闸**:claim 的 done 分支(:779 内)与 submit 的 done 分支
  (:1331 内)经 `_verify_done_action_authority`(:1730);recover_run
  done 分支经 `_verify_commit_event`(:2334,身份列保持旧 kinds +
  记录哈希 + 完整权威)。
- **证据**:r2 回归 `test_first_complete_event_outcome_requires_real_event`
  (空/不存在/异父三案零写账)、`test_b4_recovery_missing_reference_
  rows_refused[reservation|attempt]`、`test_bad_event_ledger_authority_
  refused_before_consume[mode|kind]`(**12 类 × B4/done 两模式 = 24 案**,
  每案零补账、action 状态不被"修复")、`test_done_reuse_entries_verify_
  full_authority`(claim/complete/submit 三个复用入口)。基线:1+2+24+1
  = 28 红。
- **保持**:合法首次完成/B4 幂等补账/done 重放幂等一次(既有
  test_b4/test_b3/test_h06 全绿);12×2 案同库正常 writer 重放拒
  (R8 存量契约,不改);raw 正常首提拒(既有
  test_search_layer_composes_with_frozen_validation)。
- **既有测试更新(3 处,语义收紧伴随)**:非事件完成(retrieve/decide/
  transition/failed-attempt/stale-worker 案)显式传
  `outcome_kind=COMMIT_KIND_OUTCOME`;`test_h08_commit_record_tampered_
  event_id` 期望 kind 从 commit_record_event_missing 收紧为
  commit_record_hash_mismatch(记录哈希复算先行;纯删事件行的 h8a 案
  仍报 event_missing,h8c 案仍报 identity_mismatch)。

### S3A-03:已执行额度可退还;策略首消费未验

- **修前行为**:defer 把 claimed 直接当未执行,释放全部 reserved、
  abandon attempt,不查执行事实 —— 上限 1 连用:提交事件→defer 三个
  不同合法备选,最终 event=3、attempt=3 而两项预算 used=0;
  register_search_run 全收非法块(越界 1001/bool True/未知键/负 -1),
  bool 被 int 强转为 1、越界入账。
- **修后行为**:defer 先核未执行事实 —— 本 action 提交记录、冻结身份
  下的已提交事件(无其他 action 提交记录归因 ⇒ 视为本 action 执行
  证据)、sent/responded/failed 请求、recorded/failed attempt 均拒
  (defer_after_execution,消费任何释放前);合法未执行路径保持
  (释放/abandon),registered 请求转 abandoned(真实请求
  max_real_model_requests 预约不在 action 引用内,悬空/失败继续占额)。
  策略校验:register(:533)与读取 _limits(:584)共用 profile
  `validate_search_limits`(单一实现;`_validate_search_limits` 公开化,
  装配/注册/读取/恢复四处同源)。
- **证据**:r2 回归 `test_defer_cannot_refund_submitted_event_budget`
  (上限 1 连用反例:defer 拒、used=1、第二备选 claim 被预算拒)、
  `test_defer_after_sent_request_refused`、`test_defer_unexecuted_
  releases_legal_control`(正控:released/abandoned/deferred、used=0)、
  `test_defer_abandons_registered_request_real_quota_kept`(registered
  请求转 abandoned、真实占额保留、发送被生命周期拒)、
  `test_register_rejects_illegal_policy_blocks[4 案]`(零写入)、
  `test_stored_policy_block_corrupt_rejected_on_read`。基线:1+1+1+1+4+1
  = 9 红(其中 defer-abandon 案的红含新生命周期语义),正控 1 绿。
- **保持**:十上限单位/默认/范围/逐步复算/循环稳定停/内存重置复算/
  缓存检索不重复计(既有 E04 矩阵全绿);零预算只挡该资源
  (real=0/检索=0/转换=0/深度=0/总 action=0 五独立夹具复跑绿,
  `current/crash_barrier_budget/`)。

### S3A-04:请求同键异内容成功复用,未核执行引用

- **修前行为**:register_model_request 同 request_id 立即 unchanged,
  不比 payload_hash/purpose/action/retry_of;不核新请求的 action/attempt
  存在/归属/状态 —— 同键换载荷/换 purpose/换 action 复用旧请求、
  未 claim/不存在 action/foreign attempt 均可登记 real 请求并占额;
  存储 payload_hash 被改 64 个 0 后原载荷注册仍 unchanged;scripted 请求
  注册后 action defer/退预约仍可 record sent。
- **修后行为**:登记/复用前核执行引用(登记路径);同键复用比
  action_id/purpose/payload_hash/retry_of,任一不同 ⇒
  SearchIdentityConflict(request_identity_conflict,零写入,不以"键相同"
  当幂等证书);sent/response/failed 三个状态消费口经
  _verify_request_execution(:1170)核 action 仍 claimed、attempt(若绑)
  仍 open —— 已释放执行权(defer 后/attempt abandoned)不可继续消费。
- **证据**:r2 回归 `test_request_same_key_conflicts[payload|purpose|
  action|tampered_hash]`、`test_request_registration_execution_reference_
  closed[unclaimed|missing_action|foreign_attempt|missing_attempt|
  expand_empty_attempt]`(五案请求与真实额度预约零写入)、
  `test_request_state_consumption_after_execution_released`(状态机
  abandoned + 执行引用双闸;直改库拨回状态后执行引用闸仍拒)、
  `test_request_empty_attempt_on_decide_positive_control`(非 expand
  合法空 attempt 正控)。基线:4+5+1 = 10 红,正控 1 绿。
- **保持**:合法同键重复零新增、合法 scoped 完整链、显式 retry 新
  request_key 新 ID 占剩余额度、悬空不默发(B2)、真实请求预算 0 拒
  且零写入、scripted 网络 0(既有 test_request_lifecycle/
  test_zero_real_requests/test_real_request_dangling 与 B2 全绿)。

### S3A-05:停止报告漏掉正在执行的动作

- **修前行为**:stop_report 只计 pending/deferred/blocked/悬空请求 ——
  默认预算有余、只 claim 一个 action、无请求时,恢复明示 B1 awaiting
  completion,stop_report 却 primary=exhausted_search、unexplored 全 0。
- **修后行为**:claimed_actions 与 open_attempts 计入 unexplored 集合
  并阻止 exhausted_search(执行未完成不得称"所有路线都探索完");
  仍执行中且无其他成因 ⇒ primary=None(未停止,六原因顺序保持、
  不新增原因)。
- **证据**:r2 回归 `test_stop_report_claimed_actions_not_exhausted`
  (claimed=1/open=1、primary != exhausted 且为 None;user_stop 支配;
  完成后合法 exhausted;空 run 正控)。基线:1 红。
- **保持**:六原因优先级、独立零总预算/零深度/空池夹具、复合主因
  保留其他原因、deferred 不称探索完、awaiting_prediction(既有 H05
  矩阵全绿;含在 648/1250 内)。

## 3. 红绿分类汇总

| 执行 | 当前源(修后) | 基线 9b78f42(修前,同字节) |
| --- | --- | --- |
| r2 新回归(54 项) | **54 绿** | **52 行为红 + 2 正控绿**(正控=合法未执行 defer 释放、非 expand 空 attempt 请求;其余坏案按预期失败,即修前缺口;**无 collection 红** —— 新回归只用公开 API) |
| 更新后的既有 s3a_search/s3a_recover/profile(81 项) | **81 绿** | **79 绿 + 2 红**(1 行为红:记录 event_id 篡改在基线仅报事件缺失,r2 记录哈希层先拒;1 版本红:profile-10/search-2 断言) |
| PPV1 全量 24 文件 | **648 passed / 0 skipped**(594+54) | -(基线全量非本轮要求;00e509a 首批 collection 红历史保留在 s3a_r1,不用它替代本轮行为红) |
| G01 安全隔离 | **1250 passed / 8 skipped / 17 deselected**(1196+54) | -(G01 只按当前源/白名单口径) |

基线红按 P1 归组:S3A-01=5(4 B3 分案 + 写侧)、S3A-02=28(空/缺失/
异父 1 + 缺引用 2 + 12×2 坏账 24 + 复用入口 1)、S3A-03=9(退款 2 +
abandon 生命周期 1 + 策略 5 + 读取 1)、S3A-04=10(同键 4 + 执行引用 5 +
已释放消费 1)、S3A-05=1 —— 合计 53?与 52 的差:52+2=54 为新回归
文件内计数,`test_register_rejects_illegal_policy_blocks` 4 案与
`test_defer_abandons…` 等按上表逐案展开即 52(其中
first_complete 一案覆盖三子断言);准确逐 nodeid 见
`docs/review_evidence/ppv1_s3_impl_2026-10-07/s3a_r2/baseline/rework_r2/
failed_nodeids.txt`。基线执行均记录 JUnit/stdout/退出码(基线
worktree 建立与清理日志在 `meta/`)。

## 4. 预算账(十上限;与实现一致的 r2 语义)

| limit_key | scope | 预约 | consume | release |
| --- | --- | --- | --- | --- |
| max_total_search_actions | run | claim 每 action 1 | 完成/失败(执行过) | defer **仅未执行**(S3A-03) |
| max_alternative_hypotheses_per_parent | parent | claim 首选该假设(主体幂等) | 随 action | defer 仅未执行 |
| max_attempts_per_hypothesis | hypothesis | claim 建 attempt(含首次) | attempt recorded/failed | abandon 仅未执行 defer |
| max_reopens_per_hypothesis | hypothesis | claim 重开 | 随 attempt | abandon |
| max_product_expansion_width / max_search_depth | 队列级 | enqueue 结构上限(不算已用) | — | — |
| max_scenario_transitions | run | claim(transition 另加 1) | 完成 | defer 仅未执行 |
| max_real_model_requests | run | **登记即时占额**(失败/悬空均占) | — | **永不释放** |
| max_retrievals_per_parent / max_retrievals_total | parent/run | claim(非缓存) | 完成 | defer 仅未执行 |

上限 1 连用反例验证:已执行 event 经 defer 无法退额(used 恒 ≥ 已执行
action 数);执行次数与预算源记录逐步复算保持(既有 E04 夹具)。
策略读取同源校验后,越界/bool/未知键/负数块在注册与读取消费前均拒。

## 5. 语义 / version / 身份影响

- `PPV1_SEARCH_SCHEMA_VERSION` ppv1-search-1 → **ppv1-search-2**;
  `PPV1_PROFILE_SCHEMA_VERSION` ppv1-profile-9 → **ppv1-profile-10**
  (contracts.search 登记 -2;`test_ppv1_profile.py` 断言更新,基线上为
  1 版本红);`PPV1_STORE_SCHEMA_VERSION` 保持 **ppv1-store-9**(六张
  搜索表与 writer 行为未改);`SEARCH_LIMITS_VERSION` 保持
  **ppv1-search-limits-3**(计数语义未动)。PPV1 从未放行执行流,无
  历史产物迁移;旧 -9/-1 身份载荷按既有版本门拒绝。
- profile.py 新增公开 `validate_search_limits`(原
  `_validate_search_limits` 单一实现的公开名;装配/注册/读取/恢复同源)。
- **workflow/runner.py 未修改**:PPV1 双入口继续 fail-closed(既有
  runner 拒绝测试在 648 内全绿);本批不触碰共享 runner 文件,legacy
  code_identity 聚合哈希相对 9b78f42 不变(污染物专属包变更不进
  legacy 身份,`test_code_identity_excludes_pollutant_for_legacy` 绿)。
- 冻结 legacy/G2/AtomTool 行为未改;chemstate/audit/path_context/
  hypothesis/events 五源字节未改(相对 9b78f42,`git diff` 可核);
  R8 认可的 R6 五组与 R7 两项、正常 raw 守卫、合法不同 parent/context、
  unknown/partial 控制保持(648/1250 内全绿)。

## 6. 复审 §5/§6 P2 精度合并落字

- **mimo⑤(键断裂/电子去向句归属)**:已在 v9 判据三规则正文;v10 请求
  明确"**不再要求改代码 scope 字面**"(复审 §5:已落地,勿再当未闭合
  项),composition-only 不升级机制证明边界不变。
- **mimo⑥(判负口径精度)**:v10 判据三新增 v10 精度更正 ——
  (a) 实际枚举 `partial_unchecked_transformation` 非裸 partial;
  (b) uncovered+partial 的 coverage_violations 可能是
  coefficient_binding_mismatch/补全数值不符,与许可登记无关,不能一律
  称"许可本身判负";(c) unknown_coefficients 早退未使用许可;
  (d) 仅 completion_license_unregistered_identity 直接关联"数值配平
  不证明未登记多原子共底物初始图结构贡献"句。
- **mimo④(v9 全称被反驳)**:v9"搜索不存在绕过验证"全称被 B4/done
  证据反驳;r2 修复后 v10 0b 节改为实际入口证据表述(全部事件消费入口
  经公共 writer 同一验证源;同源复用非独立双算),24 个坏事件账反例
  逐案恢复前拒支持。
- **mimo①②③⑦⑧⑨**:v9 已落字条目(内因读法/r 不反推/同源非双算/
  两种不可变分写/三个 None + converter 元数据/caller 义务披露)在 v10
  自包含文本中原样保持并请求确认;⑨ caller 义务仍留 S3b(本批未新增
  生产 caller,静态证据不是动态安全通用证明)。
- **复审 §6 交付一致性更正**:首批交付书"B3 验身份后消费"只验自洽、
  "B4 完整权威/done 验证"实际只看索引、defer"未执行预约释放"未先核
  未执行、停止"耗尽"漏 claimed —— 上述过度声明由本批代码修复兑现
  (§2 各 P1 的修后行为即准确口径);旧交付书与旧证据只读不改。
- **复审 §6 其他 P2 摘要**:v9 缩写自包含不足 → v10 全文展开;
  reopen trigger 语义留 S3b(r2 只保留 trusted caller 标记边界,未凭
  未传 trigger 断言);生产 caller/机制认证/科学性能仍后续。

## 7. 四崩溃 / H06 / 零预算 / 幂等自审(同矩阵复跑)

- B1(认领+预约落账硬杀 os._exit 后新进程恢复)、B2(登记无响应悬空、
  显式 retry 新键)、B3(合法同 output 一次落账、字节/hash 负控保全)、
  B4(合法幂等补账 + 12×2 坏账拒)、H06 双连接 barrier 与双进程
  文件 barrier 单赢家、零真实请求/零检索/零转换/零深度/零总 action
  独立夹具、dangling 真实请求占额 —— 复跑 **23 passed**
  (`current/crash_barrier_budget/`)+ r2 新回归 54 + 既有全量,全部在
  648/1250 内;不声称"同进程 raise 冒充进程崩溃"(worker 子进程
  os._exit 驱动保持)。

## 8. 交付物与证据

- 源码:`src/pathway_v43/pollutant/search.py`(五组 P1 修复 + 入口矩阵
  docstring 更新)、`src/pathway_v43/pollutant/profile.py`(v10/search-2
  升位 + validate_search_limits 公开);
- 测试:`tests/test_ppv1_s3a_rework_r2.py`(新,54 项)、
  `tests/test_ppv1_s3a_search.py`/`tests/test_ppv1_s3a_recover.py`/
  `tests/test_ppv1_profile.py`(语义收紧伴随的显式 OUTCOME 声明、
  期望 kind 收紧、版本断言);
- 文档:`docs/mimo_ppv1_chem_review_request.md`(v10,自包含)、本交付书;
- 证据:`docs/review_evidence/ppv1_s3_impl_2026-10-07/s3a_r2/`
  (README/manifest.json/SHA256SUMS[31 附件];current/ppv1_full、
  current/rework_r2、current/crash_barrier_budget、baseline/rework_r2、
  baseline/updated_existing、g01/(preparation/execution_result/junit/
  stdout/stderr + 275 输入 SHA)、mimo/(v9 快照 + v10 送审快照)、
  scripts/safe_g01_s3a_r2.py、meta/(HEAD/dirty/runtime/契约版本/
  worktree 建立清理));不覆盖旧目录、不在永久证据原地执行。
- 本地提交:dependingv43/v4.3,git add 显式路径(上述 src/tests/docs/
  证据目录),不 push;既存用户 AGENTS.md 未提交差异、未跟踪评审
  文件/旧证据不带入。

## 9. 完成 / 未完成清单(诚实)

**完成**:S3A-01~05 五组 P1 的入口闭合与行为回归;基线行为红绿对照;
PPV1 全量与 G01 实际数字;四崩溃/H06/零预算矩阵复跑;mimo v10 请求
(自包含);R8 继承与 runner fail-closed 保持。

**未完成(不冒充)**:S3b 全部 —— 队列化学集成(冻结池/备选/两类
deferred 的调度语义与 expected_parent_revision 激活)、条件依赖/场景
转换实际进入调度、`proposals[]` 模型协议与有界格式反馈、冻结 AtomTool
中心证据生产链(**含 audit_hypothesis 生产 caller 的异常逃逸义务**,
当前仍未闭合)、PPV1 独立 runner start_run/resume_run 公开分流;
H07/H08 之外的展示层增强(license_applied/顶层渲染);机制认证/来源
真实性认证;科学性能与判据冻结(S4/S5 未启动)。生产 caller 未闭合
仍留 S3b(复审 §5 ⑨口径)。

**已知工程边界(如实披露)**:complete_action 的写前权威核验与写事务
之间存在微秒级 TOCTOU 窗口(核验后、写入前并发改库理论上可绕过;
单进程顺序消费模型内无窗口,并发写期间 SQLite busy 可见;核验对
"核验中行消失后重现"的意外首提路径有防御性失败
event_ledger_authority_unexpected_write);defer 对"冻结身份下已提交
事件"的归因豁免依赖提交记录(事件已提交且无任何 action 提交记录归因
时保守拒绝挂起——宁可保额不退,不全面拒绝合法未执行路径);
recover 的 B3 身份失败按单 action 处置不中断其余 action(与 H07 同
口径),而 B4/done 的坏权威恢复按既有 H08 口径整体结构化失败 ——
两者口径差异如实登记。

## 10. 环境与命令

conda depending43(Python 3.11.16)、RDKit 2026.03.6、SQLite 3.53.4;
`-B` + `PYTHONDONTWRITEBYTECODE=1` + `pytest -p no:cacheprovider`;
G01 固定 PYTHONPATH/空 BBD_DATA_ROOT/V3_CODE_ROOT/V43_ASSET_ROOT/
DEPENDING_V3_ROOT 于隔离树;无字节码/pytest cache 残留(收尾清理);
无真实金标/题面/封存逐题 run/dependingv4/外部模型/真实付费 provider/
网络请求;判分零 LLM。
