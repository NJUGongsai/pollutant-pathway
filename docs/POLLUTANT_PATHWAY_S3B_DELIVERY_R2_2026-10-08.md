# pollutant_pathway_v1:S3b 回修 r2 交付书(2026-10-08)

- 基线:直接父 `c1211183c0874b12c5b5461845d3c61f0a84719c`
  (S3b 批次;Codex S3b 复审未放行,P1=S3B-01~06);本批 = 上述
  复审 §8 有限回修提示词的**一次性实施**,只修六组 P1,不追单
  字符串补丁;复审报告/永久证据只读。
- 范围:冻结计划/池/必要输入的首次与恢复消费绑定(S3B-01)、
  恢复坏 artifact/缺权威裁定接 driver 执行门(S3B-02)、后续集合
  从已核事件/计划/转换事实逐对象补齐(S3B-03)、公开 start/resume
  执行会话互斥与接管(S3B-04)、novel 独立假设消费者(S3B-05)、
  blocked 原因/假设/作用域同源持久接到公开 stop(S3B-06)。
  不做 S4/S5、不加机制库、判据未冻结、科学性能 pending。
- 证据根:`docs/review_evidence/ppv1_s3_impl_2026-10-08/s3b_r2/`
  (README + manifest.json + SHA256SUMS;全部执行在仓外新 tmp 或
  新 worktree;G01 控制器随目录)。

## 0. 结论一句话

六组 P1 全部收口并接进公开入口:PPV1 全量 **871 passed/0 skip**
(851 存量 + 20 新 r2),新测试在直接父 c1183 同字节对照
**15 行为红 + 5 合法正控绿**(新文件,0 collection 红;父已含全部
S3b 模块),更新的 3 个既有文件 **1 版本翻转红 + 1 字段形态红 +
1 行为红**;G01 安全隔离 **1473/8/17 exit 0(287 输入)**;生产
化学链(production.py)本批**零改动**(复审已验的 AtomTool 中心
链/AuditContractError 义务/三个 None 保持)。

## 1. 入口→消费权威→同源守卫→正负控制矩阵(六组)

### 1.1 S3B-01 冻结计划/池/必要输入的首用与恢复消费

**入口矩阵**:`runflow.start_ppv1_run`(start:冻结计划持久化
`runflow.py:1259` `_persist_frozen_plan`;根 retrieve 任务输入绑定
plan_digest `runflow.py:1261-1284`)、`resume_ppv1_run`
(`runflow.py:1358-1371` 冻结计划加载 + 传入计划 digest 核对)、
`_Driver._pool_for`(:566-604)、`_run_retrieve`(:566-580
plan_digest 同源核验)、`_run_decide`(:648-674 pool_digest 同源
核验)、`_model_proposals`(响应来自冻结计划)、`_match_transition`
(转换意图来自冻结计划)、expand/followup(全部经 Driver 的冻结
计划来源)。

**消费权威**:start 时持久化的冻结计划 artifact
(`run-plan/frozen_plan.json`;plan_digest 内容绑定;H07 包装读取
+ 内容身份核验 `runflow.py:211-257`)。

**同源守卫**:
- resume 不传 plan ⇒ 沿冻结输入(缺输入不变空池);
- 传入计划 digest ≠ 冻结 digest ⇒ `frozen_plan_mismatch`
  结构化拒(`runflow.py:1362-1371`,零写入;差异须显式新
  revision/新任务登记,不复用旧裁决键);
- 冻结计划 artifact 被篡改/损坏 ⇒ `frozen_plan_integrity_failure`
  /`frozen_plan_digest_mismatch`(保全原文件);
- 第二层:`_run_retrieve` 的 plan_digest(:576-580)与
  `_run_decide` 的 pool_digest(:659-674)重取重算核验(正常流
  不可达,防 DB 侧输入漂移)。

**正负控制**:
- 正(父绿):同计划 B1/B3/B4 恢复、幂等复用
  (`test_s3b01_same_plan_resume_positive_control`:B3 同 output
  事件 1/commit 4,再 resume 不重数);
- 负(父红):`test_s3b01_resume_without_plan_uses_frozen_input`
  (父把不传 plan 当空池 no_local_candidate,r2 沿冻结完成 1
  event)、`test_s3b01_resume_changed_plan_rejected`(父接受
  donor-X,r2 拒)、`test_s3b01_frozen_plan_tamper_integrity_
  failure`(父无完整性门,r2 拒)。

### 1.2 S3B-02 恢复的坏 artifact/缺权威裁定接到 driver 执行门

**入口矩阵**:`resume_ppv1_run` → `SearchLedger.recover_run`
(search.py:3060-3194,诚实识别 H07)→ `_isolated_recovery_
actions`(`runflow.py:323-338`)→ `SearchLedger.isolate_
recovered_failure`(search.py:1155-1224,claimed→blocked)→
`_Driver._inflight_action_ids`(:502-514,blocked 不执行)。

**消费权威**:recover 报告的失败处置(disposition 携带 error 的
dict:artifact_hash_mismatch / artifact_unparseable)。

**同源守卫**:坏任务隔离(blocked + `recovery_failure:<kind>`;
幂等不重数);**零猜重算、零坏任务 event/成功 commit/consume**;
坏原文件/attempt/预约行保全(不释放不猜补);claim/激活对
blocked 均拒(不强行执行);合法 B1–B4 与明确独立任务继续;
披露:`summary["recovery"]["isolated_actions"]` + stop 的
unexplored.blocked。

**正负控制**:
- 正(父绿):B3 同 output 恢复(1.1 正控)、四崩溃合法恢复
  (存量测试)、B4 坏权威拒(`public_event_ledger_bad` 口径
  保持);
- 负(父红):`test_s3b02_bad_bundle_hash_isolated_not_
  reexecuted`(父重跑真工具写 1 event/4 commit;r2 events 0、
  commits 不变、action blocked、坏文件保全)、
  `test_s3b02_bad_bundle_json_isolated_independent_tasks_
  continue`(坏任务隔离 + 独立备选 C 继续提交,events 恰 1)。

### 1.3 S3B-03 后续集合从已核 event/plan/转换事实确定

**入口矩阵**:`_Driver.reconcile_followups`(`runflow.py:
364-440`:期望集合 = 提交记录 event_id → 事件行参与物产物全集 ×
展开计划 expanded/deferred/not_tracked;**删除 payload LIKE 计数
>1 的伪完整性判据**)、`_ensure_transition_followup`(:441-494,
冻结计划 scenario_transitions 按该 expand 的 hypothesis_key 匹配
⇒ 幂等补齐/复用携带 pending_followup 的转换 action)、
`_transition_followup_payload`(:424-439,**单一构建源**:
_expand 入队与 reconcile 补齐共用同字节载荷)、`_run_expand`
(:1005-1025 转换一次冻结入队,无两写窗口)、`_run_transition`
(:1093-1139 按 pending_followup 用新上下文调度)、
`enqueue_scenario_transition` 新增 pending_followup 参数
(queue.py:503-586,缺/坏 ⇒ 契约拒)。

**消费权威**:事件行 + 展开计划附件(公共 store 提交路径已核)
+ 冻结计划的显式转换意图。

**同源守卫**:逐对象幂等补齐(enqueue 同键同内容 unchanged,
不重发事件、不重复扣额);只后效(旧边评估冻结于
phase_history);转换入队/附随一次写入覆盖"事件后未入队、只入队
未附随、部分多产物 followup、转换后尚未结算"窗口;0/部分/全部
均逐对象闭合。

**正负控制**:
- 正(父绿):`test_s3b03_b4_event_submitted_no_followup_
  completed`(0/全部窗口父亦闭合;r2 为幂等双保险)、三产物
  正常(`test_s3b03_three_products_normal_positive_control`,
  3 followup/事件不截断);
- 负(父红):`test_s3b03_partial_followup_hard_kill_completed`
  (2/3 丢失 ⇒ r2 补齐 3/3;真实子进程硬杀注入)、
  `test_s3b03_transition_after_event_submitted_new_context`
  (父丢转换意图 ⇒ r2 补齐,转换 done、followup 用 phase-1 新
  上下文)、`test_s3b03_transition_enqueued_crash_window_
  closed`(父两写窗口丢附随 ⇒ r2 一次冻结,恢复执行到新上下文)。

### 1.4 S3B-04 公开 resume 实际执行会话独占/接管

**入口矩阵**:`start_ppv1_run`(`runflow.py:1232` 取锁)/
`resume_ppv1_run`(:1353 取锁)的 `_DriverSession`
(`runflow.py:259-321`:run 目录 driver.lock 的
flock LOCK_EX|LOCK_NB;锁文件内容只作披露,**flock 是权威**)。

**同源守卫**:竞争方在**任何恢复/认领/请求/工具执行之前**
`driver_session_active` 结构化拒(不创建新 attempt/event、不重复
扣额;竞争方可复用:等持有方退出后再次 resume 幂等复用完成
结果);崩溃(进程死亡)⇒ OS 自动释放 ⇒ 新进程接管(原
attempt/预约/claim 行原样保留,B1 同 worker 幂等 reclaim 续跑;
不永久锁死);正常完成/异常退出都释放(try/finally)。同机文件
锁语义;不宣称分布式锁或外部 provider exactly-once(沿复审裁定)。

**正负控制**:
- 正:四崩溃单进程接管(存量;attempt/预约保持)、胜者退出后
  幂等复用(本组测试内断言:再 resume events 1/commits 4 不变);
- 负(父红):`test_s3b04_concurrent_public_resume_single_
  executor`——两个真实公开 resume 进程 + **真实工具入口计数**
  (patched `execute_atomtool_expansion` 包装调用真工具,写收据)
  + barrier(胜者持锁在工具内等竞争方尝试标记,证明两进程实际
  重叠):r2 只一方 tool_entered(计数 1),另一方
  driver_session_active 且 tool_entries 0;父两方都执行
  (second resumed=True + 工具收据)。最终 event 幂等不是唯一
  断言(工具入口计数 + barrier + 表量并用)。

### 1.5 S3B-05 novel 完整独立假设消费者

**入口矩阵**:`model_protocol.parse_model_proposals`
(model_protocol.py:200-212:novel 须携带 `reaction_spec` 完整
反应内容,缺 ⇒ json_field 格式错误 `novel_reaction_spec_missing`,
可进有界反馈;不伪造内容)、`_run_decide`(`runflow.py:714-728`
novel 经 `prepare_hypothesis` 单一构建源构造独立假设,来源
`source_refs=[novel-model-proposal:<output_origin>]`;:783-785
proposal_context 入冻结任务输入;随后与池内条目同一
`schedule_hypotheses` 入队走固定生产链)、`_run_retrieve`
(:584-600 空池+计划带模型 ⇒ 仍进 decide,不再空池短路)、
`build_substrate_profile`(:673-678 底物档案独立于候选,持久
artifact)、`_next_model_response`(:916-922 脚本响应耗尽 ⇒ 合法
弃权,不猜内容)。

**同源守卫**:结构身份/参与物/系数/共同产物/条件/依赖沿既有
prepare_hypothesis/build_hypothesis 契约(单一构建源:decide 取
hypothesis_id 与执行重建同对象);无足够内容 ⇒ 构造侧结构化拒
(run_error,不伪造);池内选择/弃权合法(弃权与规则池并行,
不强制停止);不启 chemical_reproposal、不发真实 provider/
付费;scripted 网络 0。

**正负控制**:
- 正:`test_s3b05_model_abstain_empty_pool_legal`(合法弃权 +
  空池 ⇒ no_local_candidate 如实停止,请求 1);
- 负(父红):`test_s3b05_novel_nonempty_independent_hypothesis_
  chain`(父 novel 只计数 1 event;r2 = 2 events/2 hypotheses/
  2 production_report,经真实工具→audit→admission→submit,
  network 0)、`test_s3b05_novel_empty_pool_profile_and_
  consumption`(父不进模型 0 请求;r2 组装底物档案 + novel
  独立假设事件 + 请求 ≥1)、`test_s3b05_novel_insufficient_
  content_structured_reject`(父忽略坏 novel 照常完成;r2
  run_error=spec_missing_product 如实停止)。

### 1.6 S3B-06 blocked 原因/假设/作用域从调度结果持久接到公开 stop

**入口矩阵**:`queue.schedule_hypotheses`(queue.py:236-258
深度超限整池 blocked ⇒ `ledger.record_blocked_hypothesis`;
:295-306 入队层深度拒绝同样持久)→ `SearchLedger.record_
blocked_hypothesis`(search.py:1078-1153:search_actions 行
status=blocked + defer_reason + 冻结 payload,幂等/冲突与
enqueue 同一判据)→ `stop_report`(search.py:2999-3012 从持久行
派生 depth_limit 停止原因;:3047-3058 blocked_objects 逐对象
披露,有界 100 条)。

**同源守卫**:正常/恢复同源(重放幂等,不重数;refusals 会话
内存不作唯一来源);主因优先级不动(budget_limit > depth_limit,
本案 budget 主因合法);blocked 不是可执行状态(claim/
reactivate 均拒);不用只存 blocked 计数充当整对象消费
(blocked_objects 含 action/假设/原因)。

**正负控制**:
- 正(父绿,键容差):`test_s3b06_legal_nonzero_no_blocked_
  positive_control`(无 blocked/无深度原因)、空池
  no_local_candidate 正控(`test_s3b06_empty_pool_no_local_
  candidate_positive_control`,检索预算不耗尽的独立夹具);
- 负(父红):`test_s3b06_zero_depth_budget_composite_stop_
  disclosure`(零深度+预算复合:主因 budget_limit(优先级
  不动)、other_reasons 含 depth_limit、blocked=1 +
  blocked_objects[0].reason=depth_limit 与持久行同源;scheduled
  outcome blocked=1)与 `test_s3b06_zero_depth_repeat_resume_
  not_recounted`(重复 resume 不丢不重数)。

## 2. 版本/身份/Hash 影响(逐项披露)

- `PPV1_SEARCH_SCHEMA_VERSION`:ppv1-search-5 → **ppv1-search-6**
  (blocked 持久行 + 恢复隔离 + 转换附随一次冻结的消费语义;
  计数键/默认/范围/单位未动);`PPV1_PROFILE_SCHEMA_VERSION`:
  -13 → **-14**(契约登记);**MODEL_PROTOCOL_VERSION**:
  ppv1-model-proposals-1 → **-2**(novel 须 reaction_spec);
  **RUNFLOW_VERSION**:ppv1-runflow-1 → **-2**(冻结输入绑定/
  会话互斥/恢复门/novel 消费接线);store 保持 **-9**(无新表:
  blocked/隔离复用 search_actions 行;冻结计划/底物档案走
  artifact;转换附随复用 payload);search-limits 保持 **-3**;
  FORMAT_FEEDBACK_POLICY_VERSION 保持 -1;production.py 本批
  **零改动**(SEARCH_PRODUCTION_VERSION 保持 -1,生产化学链与
  AuditContractError 义务字节不变)。
- **legacy 影响**:本批未触碰 workflow/runner.py 与任何共享
  legacy 文件(legacy code_identity 聚合与父一致
  `18007e6a…f1374d6`);chemstate/hypothesis/events/audit/
  path_context/store 字节与父一致。
- 更新的既有测试 4 文件:`test_ppv1_profile.py`(版本字面量
  13→14/search-5→6)、`test_ppv1_s3b_queue.py`(深度 blocked
  持久行断言)、`test_ppv1_s3b_model.py`(novel reaction_spec
  契约)、`s3b_worker.py`(新注入/并发恢复/无 plan resume 模式);
  其余 S3a/S0-S2 测试零改动全绿(871 = 851 存量 + 20 新)。

## 3. 独立执行数字(depending43 Python 3.11.16 / RDKit
2026.03.6 / SQLite 3.53.4;PYTHONDONTWRITEBYTECODE=1、-B、
pytest -p no:cacheprovider)

| 执行 | 结果 | 证据 |
| --- | --- | --- |
| PPV1 全量(31 文件 = 30 存量 + 1 新) | **871 passed / 0 skipped / 0 failed**,exit 0 | `current/ppv1_full/`(junit+stdout) |
| 新 r2 测试(1 文件) | **20 passed**(六组 15 负控 + 5 正控) | `current/ppv1_full/` 内 |
| 父 c1211183 detached worktree 同字节(新 r2 文件 + 更新 worker) | **15 行为红 + 5 合法绿** | `baseline/parent_c121_new_and_updated.*` |
| 父 c1211183 同字节 3 个更新既有文件 | **1 版本翻转红 + 1 字段形态红 + 1 行为红 / 54 绿** | 同上(合并 18 failed/57 passed) |
| 安全隔离 G01(r2 控制器 = r1 控制器 + 1 新输入) | **1473 passed / 8 skipped / 17 deselected**,exit 0,pytest 208.51s | `g01/`(preparation/execution/junit/stdout) |

G01:287 输入 = r1 286 + 1 新增(test_ppv1_s3b_r2.py);queue/
model_protocol/runflow/profile 为 286 内已有路径的更新副本(非
新增);worker/3 个更新测试为已有路径更新副本;fresh SHA256、
实际 HEAD(c1211183)+ 脏状态记录;8 skip = 5 真实评价 + 1 v4
对照 + 2 phase_d 派生 metadata;17 deselect = 16 slow + 1 显式
排除 export 用例;零金标/题面/封存/v4/真实 provider,网络 0;
1473 = 1453(r1)+ 20。历史 1110/1138/1196/1250/1299/1389/1453
各自单列不混计;全部工程数字不外推 dev(B1 环境路径中间步骤)
或 298(RHEA 通用酶学)科学性能。

## 4. 复审 §4 六组最低回修逐项对照

| 组 | 最低回修要求 | 本批落点 |
| --- | --- | --- |
| 01 | 首用与恢复共用持久冻结实际输入;缺原输入不当空池;变更拒或显式新 revision;同 plan 正控保持 | §1.1(冻结计划 artifact + 三层核对;同计划正控父绿) |
| 02 | 恢复裁定接执行门;零猜重算/零坏任务成功;证据保全;合法 B1–B4 与独立任务继续 | §1.2(isolate_recovered_failure;两负控 + 存量正控) |
| 03 | 后续集合从已核事实确定,0/部分/全部逐项;转换/待跟进持久关联;不用计数当证书 | §1.3(删除 LIKE 判据;权威事件/计划/转换意图;四窗口) |
| 04 | 会话独占/接管;双进程同 action 只一方执行;保留崩溃接管与原 attempt;真实工具入口计数 + barrier | §1.4(flock 会话;并发负控 + 幂等复用/接管正控) |
| 05 | novel 完整独立假设消费者;空池可组底物档案;池内选择/弃权合法;不启 chemical_reposal/不付费 | §1.5(reaction_spec 协议 + prepare/schedule/生产链;三负控一正控) |
| 06 | blocked 原因/假设/作用域同源持久;主因优先级不动;其他原因与未探索对象披露;恢复不丢/不重数 | §1.6(blocked 行 + stop 同源派生;两负控两正控) |

保留项核验:真实 AtomTool 中心链/audit/admission/submit 未动
(production.py 零改动);AuditContractError 窄捕获不吞成功
(runflow.py:955-972 保持);三 None/unknown/partial 与 H2
composition-only 合法控制由存量 851 全绿保持;E01/E02/C06/H04、
S3a/R8 已关项不重开(存量测试零改动);cache_hit 同构与外部 SQL
并发范围 P2 保持;未补机制库;未访问真实金标/题面/封存 run;
未改冻结 legacy/G2/AtomTool;不含 S4/S5;科学性能 pending。

## 5. mimo v14 请求与外送边界

- `docs/mimo_ppv1_chem_review_request.md` 升级 **v14(S3b-r2)**:
  新增 0e 节(本批六组消费契约:冻结输入身份/恢复隔离/后续集合
  完整性/执行会话互斥/novel 消费者/blocked 持久披露)与 0c-v14 节
  (复审 §6 精度更正:测试数字/worker 入口/产品来源口径与
  runflow 行号更正落字);判据一–五正文与 v13 相同(无新化学
  机制;本批不改任何化学判定模块)。v13 送审请求与回应保留
  原样,不回写。
- 本批实施 agent 未调用任何外部模型;请求由主会话按通道 A 送审,
  回应落盘后按互证原则采信。

## 6. 自查未闭合残留(诚实清单)

1. **判据未冻结、科学性能 pending**:全部数字为工程合成规则级
  契约结果,不代表 dev/298 科学性能;S4/S5 未启动。
2. **计划仍是合成/规则级驱动输入**:冻结计划绑定解决的是
  "恢复不换输入"的身份契约,不证明计划池本身的真实检索质量
  (真实检索 provider 属后续阶段)。
3. **执行会话互斥是同机文件锁**:跨机/分布式锁、外部 provider
  exactly-once 不在范围(复审 §4.4 明示不要求);锁文件内容
  (pid/时间)是披露信息,flock 是权威。
4. **第二层守卫不可达性**:pool_digest/plan_digest 同源核验在
  正常流不可达(第一层冻结计划绑定已闭合),登记为纵深防御;
  未单独构造运行期反例(不伪造可达性声明)。
5. **cache_hit 同构 / 两事务间外部 SQL 并发窗口 / foreign-run
  反向诊断 / 三类 RuntimeError 逃逸面**:沿 S3a R4 §5 与复审
  §5 既定 P2 边界保持(本批未扩大也未倒退);B2 0event/1commit
  口径与 B1/B3/B4 的 1event/4commit 分列沿复审 §3。
6. **mimo v14 与 Codex 复审待跑**:由主会话按 AGENTS 自动循环
  接力(核对→送 mimo→交 Codex);本批实施未联系审核方。
7. **G01 历史缺席依赖逐项披露**沿 r1 口径(见证据 README §4);
  1473 不外推科学性能。

## 7. 提交

- v4.3 本地提交(不 push;git add 仅显式路径):
  `src/pathway_v43/pollutant/{profile,search,queue,model_protocol,
  runflow}.py`、`tests/test_ppv1_s3b_r2.py`、`tests/s3b_worker.py`、
  `tests/test_ppv1_profile.py`、`tests/test_ppv1_s3b_queue.py`、
  `tests/test_ppv1_s3b_model.py`、
  `docs/POLLUTANT_PATHWAY_S3B_DELIVERY_R2_2026-10-08.md`、
  `docs/mimo_ppv1_chem_review_request.md`、
  `docs/review_evidence/ppv1_s3_impl_2026-10-08/s3b_r2/`;
  提交哈希见 `git log -1`。既存 AGENTS.md 用户差异与旧未跟踪
  评审材料不纳入提交;production.py/store.py/runner.py 未改
  不提交。基线 worktree(/private/tmp/ppv1_s3b_r2_base_c121)与
  G01 tmp 已清理;收尾无 __pycache__/.pytest_cache 残留。
