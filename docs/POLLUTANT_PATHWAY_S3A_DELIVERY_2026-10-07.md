# pollutant_pathway_v1 S3a 批次交付书(持久搜索底座)

- 日期:2026-10-07
- 任务依据:`docs/POLLUTANT_PATHWAY_S3_IMPLEMENTATION_TASK_2026-10-07.md`
  §2.3 S3a 行 + §4 + §7(a 批行)+ §8/§9/§10(必读文档五份全部读取;
  R5–R8 评审侧未跟踪文件与证据目录只读,未在其内写任何探针)
- 回修基线:`00e509a974b40a7c9779fcd35e53b16637a13d60`(=R8 交付
  提交,实际 HEAD 开工=收尾一致);分支 v4.3,仅本地提交不 push;
  AGENTS.md 有一处用户授权未提交流程修订(自动循环第 5 条)按任务书
  §1 保持原样、不入本批提交、未改动;R5–R8 评审侧未跟踪文件原样
  保留不入库
- 范围:**仅 S3a 持久搜索底座**;S3b(队列化学集成/两类 deferred 调度、
  条件依赖/场景转换、新假设协议与格式反馈、固定工具中心证据生产链、
  PPV1 独立 runner 分流)未交付,逐项见 §15;`workflow.runner.
  start_run/resume_run` 对 PPV1 **继续 fail-closed**(legacy 分支行为
  不变);判据与化学契约**不宣称冻结**(mimo v9 请求已备,待主会话
  送审)
- 状态:ppv1 全量 **594 passed/0 skip**(536 存量 + 58 S3a 新增);
  新增回归对基线 00e509a 红 = **2 行为红 + 2 文件 collection 红**
  (58 用例缺实现未执行,如实分类);G01 安全隔离 **1196/8/17**
  (1138 + 58,逐项缺席依赖披露);mimo v9 请求已更新

## 0. 一句话结论

S3a 把搜索/任务/attempt/请求身份、十上限实际计数、认领/预算事务、
artifact 完整性与四崩溃恢复协议落成持久底座(`pollutant/search.py`
SearchLedger + store 六张新表,与公共 `submit_event` 同 SQLite 事务
边界接合但**不复制其校验**):恢复读冻结权威记录(同 attempt/同预约
/同事件,不重复扣额、不重发请求、不把草稿当事件),并发认恰一方取
得执行权,停止原因按冻结优先级取主因并保留未探索集合;runner 对
PPV1 双入口仍拒;队列化学集成与生产链明确未交付,不称完整 S3。

## 1. 提交与 diff

| commit | 内容 |
|---|---|
| (本批单提交) | src 4 文件 + 1 新文件(pollutant/search.py 新增;store.py 加六张搜索表+版本 -9;profile.py 契约升位+search-limits 实际版本+停止优先级登记+delivered_stages;workflow/runner.py 仅 PPV1 拒绝文案与 detail 字面更新,legacy 行为零改变)+ 测试 3 新文件 2 处存量断言升位(test_ppv1_s3a_search.py 45 例/test_ppv1_s3a_recover.py 12 例/s3a_worker.py 子进程崩溃与 barrier 驱动;test_ppv1_profile.py 3 处断言随版本升位,理由见 §11.2)+ mimo v9 请求 + 本交付书 + 证据目录 |

触碰面:`src/pathway_v43/pollutant/`(新 search.py,改 store/profile/
__init__)+ `src/pathway_v43/workflow/runner.py`(仅 `_refuse_
undelivered_profile` 文案/detail;**共享文件文字变更使 legacy
code_identity 聚合哈希变化** —— 旧 legacy run 跨版本 resume 按既有
身份门槛拒绝,是设计行为;legacy 运行时行为不变,G01 1196/8/17 为
证,如实登记)+ ppv1 测试 + docs。**冻结模块零语义改动**:
services/atom_tool.py 未改;storage/pathway_store.py 未改;audit/
chemstate/hypothesis/events/path_context 未改(仅 profile 版本常量
引用不变)。

## 2. 入口矩阵(实施先列;每处消费的对象/身份/版本/事实范围)

| # | 入口 | 消费 | 校验/事务 | 源码位置 |
|---|---|---|---|---|
| 1 | register_search_run | profile 身份块(search_limits+契约版本) | 未注册/同 run 异块 fail-closed;幂等 | search.py:443 |
| 2 | enqueue_action | 任务身份输入(run/父/context/subject/kind/revision/policy) | 幂等;同键异内容 SearchIdentityConflict;深度/宽度入队级拒绝(零写入) | search.py:505 |
| 3 | claim_action | 冻结 action 行 + 预算账 | BEGIN IMMEDIATE + action 状态守卫;all-or-nothing 预约;同 worker 幂等再认领;done 复用 | search.py:662 |
| 4 | _create_attempt / open attempt | hypothesis 语义尝试 | 恢复同 attempt 不再扣;新备选/重开换 attempt;确定性预约 ID | search.py:791 |
| 5 | register_model_request | 请求载荷 | real 登记即时占额(0 ⇒ 拒 ⇒ 网络发送被阻止);scripted/fake network 恒 0 | search.py:863 |
| 6 | submit_action_event | PathwayEvent(冻结身份) | 所有权+冻结身份核验(run/parent/context/hypothesis);经公共 store.submit_event(全部首消费验证照常) | search.py:1040 |
| 7 | write_commit_bundle / read_search_artifact | 提交捆绑 artifact | 不可覆盖(同键异内容 ArtifactConflict);H07 完整性 wrapper 保全原文件 | search.py:1113/321 |
| 8 | complete_action / defer_action | 认领所有权 + 预约 | 陈旧 worker 不可越权/覆盖;consume/release;提交记录 action 维度唯一 | search.py:1152/1265 |
| 9 | recover_run | 持久权威记录 | 四崩溃边界;策略身份不一致 fail-closed;H08 不一致保全失败 | search.py:1436 |
| 10 | budget_snapshot / stop_report | 持久记录派生值 | 每次从记录重算(内存重置一致);snapshot 是派生不是事实源 | search.py:1320/1352 |
| 11 | (公共) store.submit_event | 事件/投影/计划/参与物 | 既有冻结事务(R2–R8 全部校验),本批零改动,搜索层不绕过 | store.py:1468(既有) |

## 3. 持久身份与对象(§4.1;前后行为)

| 项 | 前(00e509a) | 后(本批) |
|---|---|---|
| SearchAction | 无(仅规格草案) | search_actions 表(store.py:254):action_id/run_id/parent_path_id/context_ref/subject_ref(hypothesis 或 pool)/action_kind(五类含 activate_deferred 与 scenario_transition,调度语义属 S3b)/parent_search_revision/policy_version/status(pending/claimed/done/deferred/blocked)/attempt_refs/outcome_ref/budget_reservation_ref 全列落账 |
| expansion_attempt_id | 无 | search_attempts 表(store.py:277):(run,hypothesis) 持久序号;恢复继续旧 attempt(claim 复用 open attempt,不再扣 attempts/alternatives);新备选=不同 hypothesis_id(身份含父路径,天然不互斥);重开=reopen_of+双上限 |
| 任务键 | task_id_for 绑 CN(legacy) | decision_task_key 绑冻结池摘要/父 context/parent_search_revision/严格状态摘要/工具/提示词/反馈策略版本(search.py:227);expansion_task_key 绑 hypothesis+attempt(search.py:250);substrate_feature_cache_key **不含** parent_search_revision(search.py:271,E03 正控) |
| 同键异内容 | — | action_id 派生自身份输入,payload 全量冻结;同 ID 异 payload ⇒ SearchIdentityConflict 零写入(search.py:588) |
| 事件幂等 | event_id_for 绑 run/parent/hypothesis/context/语义(既有) | 不变;新增**沿 action 冻结身份提交**核验(search.py:1086):retry/claim owner/attempt 序号变化不建第二个事件(测试:重开 attempt 2 重放同事件 created=False) |
| parent_search_revision | — | 只进 decision/expansion 键与 action 身份;恢复沿冻结 task_key(测试:认领后 revision 前进,再认领 receipt 的 task_key/attempt 不变) |

## 4. 预算账表(§4.2;十上限实际计数)

版本:`ppv1-search-limits-2-proposed` → **`ppv1-search-limits-3`**
(profile.py:142;键/默认/范围/单位沿用草案,不凭空重造;配置完整
往返可重放,未知键/错型/负数越界拒绝——既有 profile 校验保持)。

| limit_key | scope | 预约点 | consume | release |
|---|---|---|---|---|
| max_total_search_actions | run | claim 每 action 1 | 完成/失败 | defer(未执行) |
| max_alternative_hypotheses_per_parent | parent | claim 首次选中该 hypothesis(主体幂等) | 随 action | defer |
| max_attempts_per_hypothesis | hypothesis | claim 建 attempt(含首次) | attempt 记录/失败 | abandon |
| max_reopens_per_hypothesis | hypothesis | claim 重开 attempt | 随 attempt | abandon |
| max_product_expansion_width | source event | 入队结构上限(队列级不算已用;只限继续探索不截断事件事实) | — | — |
| max_search_depth | path | 入队结构上限(0=不展开产品;仅 expand 受约束,转换另计) | — | — |
| max_scenario_transitions | run | claim(transition 另加 1) | 完成 | defer |
| max_real_model_requests | run | 登记即时占额(失败/超时/悬空均占,永不释放) | — | 永不 |
| max_retrievals_per_parent | parent | claim(retrieve 且非 cache_hit) | 完成 | defer |
| max_retrievals_total | run | 同上 | 完成 | defer |

- **事实源**:budget_reservations 表(store.py:293),预约 ID 确定性
  派生(action 作用域以 action_id、主体作用域以 subject 为幂等基准,
  search.py:626)⇒ 重放/恢复同 ID 复用不重复扣;snapshot(search.py:
  1320)每次从记录重算(内存重置一致,测试覆盖);
- **零预算只挡该资源**(§4.2):真实请求 0 ⇒ 仅拒 real provider
  登记(网络发送被阻止,传模型对象不自动补额度——legacy 的
  max_llm_calls 派生逻辑不进 PPV1);检索 0 ⇒ retrieve 拒、冻结池
  decide 可用;转换 0 ⇒ 仅 transition 拒;总 action 0 ⇒ 全拒;深度 0
  ⇒ 仅产品展开拒(五组正负控独立测试);
- **缓存检索不重复计 actual**(cache_hit 跳过检索预约,总 action 照
  扣 ⇒ 新增 action 不免费);队列待办不预留(claim 才预约,入队拒绝
  零写入);E04 循环稳定停:小上限+每轮换备选 ⇒ 迭代在预算处停
  (<100 护栏),stop primary=budget_limit 且 used==max 复算一致。

## 5. 并发与事务(§4.3)

- 认领在 BEGIN IMMEDIATE 单事务(search.py:662):同 action 只有一
  方取得执行权;竞争方 `SearchClaimError(already_claimed)`(不开新
  attempt/request/事件、不重复扣额);同 worker 重认领幂等返回原
  收据(执行方恢复续跑入口);done ⇒ 复用完成结果零新增;
- **H06 双口径测试**:两独立连接 + threading.Barrier(确定性同步,
  不靠顺序调用/sleep)单赢家;两独立**进程** + 文件 barrier(GO 门)
  单赢家(s3a_worker.py barrier-claim;attempt/请求/预约/事件均无
  翻倍);
- **陈旧 worker**:提交/完成/挂起均 owner_mismatch 拒;认领者完成后
  迟到的 complete 幂等 unchanged(outcome 不被覆盖);
- **锁超时/SQLite busy**:SearchConcurrencyError(kind=sqlite_busy,
  可见并发结果,不当化学拒绝;search.py:432/786);重试沿原 action
  身份(测试:锁释放后同 action 再认领成功);
- **提交事务边界**:事件提交走公共 `store.submit_event`(既有冻结
  事务,本批零改动);搜索记账(预约 consume/action 状态/提交记录)
  在 store.conn 独立事务闭合;两段间的中断由 **B4 恢复协议**覆盖
  (权威 = 事件行 + 认领/预约/attempt 行 + search_commit_records,
  store.py:322;不以内存状态或 LangGraph checkpoint 声称跨文件原子;
  artifact 文件先写不可覆盖,"有文件"≠事件已提交);
- **正控**:同 hypothesis 不同 context ⇒ 两个 action 各自可认领
  (hypothesis_id 含父路径,不同 parent 也天然不互斥)。

## 6. 四个崩溃边界(§4.4;独立子进程硬杀,非同进程 raise)

| 边界 | 恢复观察(实现) | 测试 |
|---|---|---|
| B1 认领+预约落账后硬杀 | recover_run 报告 B1;冻结 action/attempt/预约原样(attempts=1、预约无重复、快照复算相同);执行方沿原身份再认领(reclaimed_by_owner,同 task_key/attempt)后完成 | test_b1_claimed_reservation_frozen_then_resume |
| B2 请求已登记无响应 | pending_requests 暴露 status=registered+network=0(scripted),**不默发**(状态保持 registered、请求数不增);显式重试=新 request_key 新 request_id+剩余额度;real 悬空/失败占额不释放 | test_b2_registered_request_pending_unknown_no_resend / test_real_request_dangling_occupies_budget |
| B3 artifact 已写事件未提交 | 先验 bundle 版本/action/attempt 绑定+事件 ID 重推导(search.py:1622)⇒ 消费同一 output 完成:事件仅一次、请求 0(不重发)、consume 恰一次;负控:字节损坏/hash 不符 ⇒ SearchArtifactIntegrityError 原文件保全、零事件、action 仍 claimed | test_b3_artifact_written_consumed_same_output_after_crash / test_b3_corrupt_artifact_preserved_fail_closed / test_b3_bundle_identity_verification |
| B4 事件已提交记账未闭合 | find_event 命中(公共路径/注入点 crash_after="event_submitted" 均可达)⇒ 以记录在案的 claim owner 名义幂等补账:事件不重复、预算 consume 恰一次、attempt recorded、action done;二次恢复 done_commit_verified 零新增 | test_b4_event_committed_bookkeeping_completed_idempotently / test_crash_injection_point_b4 |

H07:read_search_artifact wrapper(search.py:321)—— 不可反序列化/
hash 不符 ⇒ 结构化完整性错误 + **原文件字节保全**(测试逐一断言前后
字节相同),不静默跳过、不重跑覆盖。H8:提交记录 ↔ 事件行
(_verify_commit_event,search.py:1595)—— 事件缺失/记录改指/event
身份列被改 ⇒ SearchIntegrityError 保全失败零写入,不默认补事件/修库
(三负控);done 而无提交记录同样是记账不变量破坏(恢复即拒)。

## 7. 停止原因(H05)

- 常量与优先级登记于 search.py:`user_stop > budget_limit > depth_
  limit > no_local_candidate > awaiting_prediction > exhausted_search`
  (STOP_REASON_PRIORITY,随 ppv1-search-1 进 run 身份);
- **三独立夹具**(不用复合夹具冒充):仅总 action=0 ⇒ budget_limit
  (budget_exhausted_keys 只含该键);仅深度=0 ⇒ depth_limit(预算
  未耗尽,budget_exhausted_keys 空);仅池空 ⇒ no_local_candidate;
- 复合:user_stop+预算+深度 ⇒ 主因 user_stop、其余原因保留;预算+
  深度 ⇒ 主因 budget_limit(优先级);未知停止原因 ⇒ 契约拒绝;
- awaiting_prediction:悬空请求且无 pending 动作;exhausted_search
  仅在无 pending/deferred/blocked/悬空请求时;**存在 deferred ⇒ 不称
  "所有路线都探索完"**(unexplored 集合机器披露;停止不是化学终点,
  endpoint 属 S4);
- 正控:预算有余额+队列有待办 ⇒ primary=None(不停)。

## 8. 分任务验收矩阵映射(任务书 §7,a 批行)

| 任务/批次 | 入口→行为→断言 | 结果 |
|---|---|---|
| 身份/E03,a | 两假设任务键/attempt 互不复用、context/池/版本换键、底物特征键无 revision(签名级)、同键异内容拒、同事件重放不多事件、恢复沿冻结键 | 45 例中 12 例直接覆盖,绿 |
| P0-3/E04,a | 十上限默认/范围/单位/优先级登记、逐步复算、内存重置复算、缓存检索不重复计、循环稳定停、重开/attempt/备选/总量四类上限各自封顶 | 绿(§4) |
| H05,a | 三独立零预算夹具+复合优先级+user_stop 支配+deferred 不称探索完+正控 | 绿(§7) |
| H06,a | 双连接 barrier 单赢家、双进程 barrier 单赢家、done 复用、陈旧 worker 不可越权/覆盖、busy 可见、同 hypothesis 异 context 正控 | 绿(§5) |
| 四崩溃,a | 子进程硬杀(os._exit)→新连接 recover;B1/B2/B3/B4 各自独立注入点;不以事务回滚单案代替 | 绿(§6) |
| H07/H08,a | artifact 损坏分案+保全;提交记录↔ledger 不一致三分案+零写入 | 绿(§6) |
| R8 继承,a | 存量 536 全绿(594-58);搜索层不绕过公共 writer 首消费验证(篡改 raw 经搜索驱动提交仍拒零事件);runner 双入口仍拒(start+resume) | 绿 |
| G01,a+b | 新控制器 safe_g01_s3a.py(白名单+新输入,实际 HEAD 与 dirty 记录) | 1196/8/17,逐项披露(§10) |

S3b 行(E01/E02/C06/H04/条件继承/场景转换/模型协议/实际中心链/
公开分流)全部未实现,见 §15。

## 9. R8 P2 文档同步清单(任务书 §8;全部落字于 mimo v9 请求 + 本节)

1. raw `r` 拒绝不反推实验消旋/样品纯度(存在与含义均不被采纳/反
   驳;裸指定结构/strict 身份非同样品/对映纯认证)—— v9 判据一
   2b 升格为规则条款;✓
2. 同源=非独立双算括注(两个包装实现不自动成新阻塞)—— v9 判据
   一 2b;✓
3. 自报 formal_charge/stereo/isotope 与重推导一致声明限定"经首消费
   验证的入口" —— v9 判据一末条;✓
4. **scope 归属更正**:代码 completion_license_scope 字面不含"不区分
   键断裂方式与电子去向",归属许可定义/规则正文(未改字段字面,
   无版本身份影响)—— v9 判据三;✓
5. 恒入≠已适用 + 三条件判定(product_coverage=full、uncovered_*_
   refs 非空、unlicensed_uncovered_identities 为空);license_
   applied/顶层/同屏列后续 P2 —— v9 判据三;✓
6. Requirement/ConditionFact frozen 与 PathContext 内容身份兜底
   两种机制分写 —— v9 判据四;✓
7. 失败诊断**三个**判定字段 None、diagnostic.center_evidence={};
   converter 仍有版本/来源元数据与 center_match=None(非"四轴
   None"/非"整个 evidence 为空")—— v9 判据五 8b;✓
8. audit_hypothesis 生产 caller 义务(不得吞 AuditContractError):
   **S3a 未新增生产 caller(生产链属 S3b),如实披露为未闭合项**
   (grep 空不是动态安全通用证明)—— v9 判据五 8d + 本批 §15;✓
   (文字落字,义务闭合待 S3b)
9. 文案更正:canonical+r 上层 kind=state_structure_unparseable 实为
   工厂未登记 CX 守卫拒绝(非 RDKit 本体不可解析);14 行为红不是
   14 个旧错误 R6(charge=99 在父基线已电荷 violated/R5d retain);
   R7 旧化学脚本 55 条早停(旧 assert 先在 len==57 计数失败),尾部
   补全;R7 flag 测试实参顺序已修 —— 全部落 v9 请求 §6 与本节,
   旧记录只读不回写;✓

未新增任何化学功能门(八条均为范围/文字同步)。

## 10. 测试证据与命令

~~~bash
PY=~/miniconda3/envs/depending43/bin/python
REPO=/Volumes/CC/Enzyme_Agent/dependingv43
E=$REPO/docs/review_evidence/ppv1_s3a_impl_2026-10-07/s3a_r1

# PPV1 全量(23 文件;536 存量 + 58 新增)
PYTHONDONTWRITEBYTECODE=1 $PY -B -m pytest -p no:cacheprovider -q \
  tests/test_ppv1_profile.py ... tests/test_ppv1_r8_storage.py \
  tests/test_ppv1_s3a_search.py tests/test_ppv1_s3a_recover.py
# => 594 passed, 0 skipped(日志 $E/ppv1_current/pytest_full_output.txt)

# 基线红(先红后绿;detached worktree,同字节、无 import 适配)
git worktree add --detach /private/tmp/ppv1_s3a_baseline_wt 00e509a
cp tests/test_ppv1_s3a_search.py tests/test_ppv1_s3a_recover.py \
   tests/s3a_worker.py tests/test_ppv1_profile.py \
   /private/tmp/ppv1_s3a_baseline_wt/tests/
# 三文件同跑 => 2 collection error(日志 baseline_red/...
# baseline_red_s3a_collection.txt);profile 单独再跑 =>
# 2 failed / 21 passed(行为红:profile-9/search-limits-3/delivered_
# stages 断言;日志 baseline_red/baseline_red_profile_behavior.txt)
git worktree remove --force /private/tmp/ppv1_s3a_baseline_wt
# 红分类:行为红 2(断言);缺实现红 58(两新文件 collection,
# ModuleNotFoundError: pollutant.search,未执行)—— 分类记录
# $E/red_green_worktree_log.md

# G01 安全隔离(新控制器;R7/R8 白名单 + S3a 新输入)
PYTHONDONTWRITEBYTECODE=1 $PY -B $E/safe_g01_s3a.py \
  --repo $REPO --out /private/tmp/ppv1_s3a_g01_safe \
  --python ~/miniconda3/envs/depending43/bin/python
# => 1196 passed / 8 skipped / 17 deselected, exit 0, 194.8s
#    (结果归档 $E/g01_safe_isolation/;隔离树留在 /private/tmp,收尾清理)
~~~

### 10.1 G01 缺席依赖逐项披露(与 R8 同口径;数量/理由实际登记)

| 类型 | 数量及实际项 |
|---|---|
| skip:真实评价依赖缺席 | 5:test_batch_runner:52;test_score_report:110/163/172/184 |
| skip:v4 对照源缺席 | 1:test_analog_assets:95 |
| skip:phase_d 派生 metadata 未复制 | 2:test_analog_v2_corpus:62/153 |
| deselect:slow | 16(-m "not slow" 选择) |
| deselect:明确排除 | 1:test_export_v3::test_charge_fixture_cn_hits_raw_sb_misses_neutralization_forbidden |

R7 历史 1110/8/17 与 R8 历史 1138/8/17 单列,不与本批 1196 混计;
未把缺席项改 pass,未读真实评价/金标/题面/封存/v4;工程回归不代表
任何题域科学性能。本控制器按任务书 §9.2 新建(fresh hash + 实际
HEAD 00e509a + dirty 状态记录),R8 固定 hash 的 safe_g01_reproduce/
safe_g01_r8 只读保留,不冒用为当前数字。

### 10.2 修改的存量测试与理由(§9.1 单列)

| 测试 | 改动 | 理由 |
|---|---|---|
| test_ppv1_profile.py:46 | profile-8 → profile-9 | S3a 契约升位(新 search 契约 + search-limits 实际版本 + delivered_stages;机械) |
| test_ppv1_profile.py:75-77 | search_limits version 改为 "ppv1-search-limits-3"(不再 endswith "proposed");delivered_stages 改 "S0-S2,S3a-base" | 语义升位:草案 → 实际可执行版本(键/默认/范围不变);交付阶段如实声明(基线红即来自这两处,行为红) |

其余 536 存量断言零改动(全文绿为证)。

## 11. schema/语义版本与兼容策略

| 契约 | v8 → v9 | 兼容声明 |
|---|---|---|
| profile | -8 → -9 | 新增 search 契约登记、search-limits v2-proposed→v3(实际计数)、delivered_stages 更新;PPV1 从未放行执行流,无历史产物迁移,升版即生效;v8 载荷按既有门拒绝 |
| store | -8 → -9 | 六张搜索底座表(search_runs/actions/attempts/budget_reservations/model_requests/commit_records);既有事件/状态/假设路径校验语义零改动;旧 -8 库按版本门拒绝(无兼容迁移) |
| search | 新 | ppv1-search-1(SearchAction/attempt/预约/请求/提交记录/恢复协议/停止优先级) |
| search_limits | -2-proposed → -3 | 实际可执行(键/默认/范围/单位沿用;新增预约/consume/release 规则) |
| chemstate/hypothesis/event/context/dependency/provenance/substrate_profile/audit/admission_policy/donor_diagnostic/pool_audit/pool_order/input_preview/condition_assessment | -8(不动) | 本批无语义变更 |
| gate_mapper / run identity | -3 / v43-identity-2(不动) | run identity 经 profile 块自动携带新契约;runner.py 文字变更使 legacy code_identity 聚合哈希变化(如实登记,行为不变) |
| workflow runner | 未触碰逻辑 | PPV1 双入口 fail-closed 保持;拒绝 detail 字面更新(delivered_stages S0-S2,S3a-base / missing S3b-S5) |

legacy_v43:冻结执行器/存储/门禁语义零改动(G01 1196 为证);旧
legacy run 的同版本 resume 因共享 runner 文字变更被身份门槛拒绝
(设计行为)。

## 12. 公共链入口与预算账表位置

- 搜索底座公共入口:`pathway_v43.pollutant.search.SearchLedger`
  (register_search_run / enqueue_action / claim_action /
  register_model_request / write_commit_bundle / submit_action_event /
  complete_action / defer_action / budget_snapshot / stop_report /
  recover_run;便捷驱动 commit_search_event 供合成/scripted 夹具,
  **不是生产 runner**);
- 事件提交公共链:SearchLedger.submit_action_event → 公共
  PollutantPathwayStore.submit_event(冻结校验全量照常);
- 预算账表/入口矩阵/崩溃边界:search.py 模块 docstring(与任务书
  §4.2 逐步复算的 fixture 对应测试 test_budget_ledger_stepwise_
  recompute);
- 测试入口(公开底座,非 runner):tests/test_ppv1_s3a_search.py +
  tests/test_ppv1_s3a_recover.py + tests/s3a_worker.py(子进程硬杀/
  barrier 驱动)。

## 13. mimo v9 请求(已备,主会话送审)

`docs/mimo_ppv1_chem_review_request.md` 已更新为 **v9(S3a)**:自
包含(S0–S2 五判据文本 + R8 八项更正落字 + S3a 实现与未实现边界
披露);规则级合成示例,无金标;S3a 不新增化学机制,受审项为文字
更正与边界声明;要求 mimo 只读化学判据、执行类声明标注"待执行验
证"。v8 请求快照与 v9 送审快照存本批证据 `s3a_r1/mimo/`;旧回应
r5–r8 原样不覆盖。实施 agent 不自行调用外部模型(送审由主会话按
AGENTS 自动接力)。

## 14. 已知边界与诚实披露

1. **S3a 是底座,不是完整 S3**:队列化学集成、生产中心证据链、
   runner 分流全部未交付(§15 逐项);不拿底座绿冒充完整 S3;
2. 恢复协议对 B3 的自动完成依赖 commit bundle artifact 完整可验
   —— 损坏时保全失败(不修不跳过),需人工/下一轮处置;
3. budget 账表的选择已登记:真实请求登记即占额且永不释放(失败/
   超时/悬空均占);deferred/blocked 的未执行预约释放(不计已用);
   失败的已执行 action 计入总 action(执行过即占);宽度/深度是
   入队级结构上限(队列创建拒绝,不算已用预算)—— 单位与任务书
   表一致,选择如实写进 search.py docstring;
4. scenario_transition/activate_deferred 仅有种类与事务底座,调度
   语义(触发条件/expected_parent_revision/显式支持来源)属 S3b;
5. runner.py 文字变更对 legacy code_identity 的影响已如实登记(§11);
6. 化学判据未冻结;mimo v9 待审;本批工程数字不外推任何题域科学
   性能;commit bundle/artifact 均为合成夹具。

## 15. 未完成清单(S3b,逐项;不许拿底座绿冒充)

1. **队列与调度**:`schedule_hypotheses`/`record_expansion_outcome`/
   `activate_deferred` 等价职责接口(冻结池选择/deferred 两类分别
   激活/expected_parent_revision 与 trigger 验证/重复触发幂等);
   E01(首选受阻备选继续+unresolved_continuation)、E02(两类
   deferred 激活+预算不足独立原因)端到端;
2. **条件与依赖实际进入调度**:子路径继承/分支隔离/essential
   conflict 阻当前场景/unknown 有界探索沿途保留(C06);H04 共底物
   循环(supported 不阻断/缺支持 unresolved_initial_supply);
3. **场景转换语义**:仅显式支持、独立预算/记录、只后效不追改;
4. **模型协议与反馈**:`proposals[]` 协议/rank_hypotheses 稳定 ID
   引用/有界格式反馈策略(独立 policy 键与计数,与 hypothesis
   attempt 分账)/chemical_reproposal 保持 off 如实披露;scripted
   driver 的网络 0 已有底座,协议层未接;
5. **固定工具中心证据生产链**:AtomTool 真实输出 → check_edit_
   against_donor → center_evidence_from_donor_diagnostic →
   audit_hypothesis → decide_admission → submit 的生产调用链与
   分段负控(**含 audit_hypothesis 生产 caller 的 AuditContractError
   逃逸义务** —— R8 P2 ⑧ 未闭合项);converter 复用现成实现,
   不另手造;
6. **公开分流**:`workflow.runner.start_run/resume_run` 的 PPV1
   独立执行/存储分流与解除 fail-closed(须先建正确存储再解除拒绝,
   不只删 `_refuse_undelivered_profile`);
7. **S3b 基线红绿**:在 S3a 已审父批基线跑同批集成测试定位新增行为
   (保留 00e509a 总体对照);
8. mimo v10 及后续轮次请求/回应/provenance。

## 16. 与任务书/AGENTS 的冲突清单

无实质冲突。两处任务书未逐字规定、按其最低要求收紧并登记:
- 恢复完成认领中的 action 时以**记录在案的 claim owner** 名义补账
  (执行权来自已验证的持久权威记录:事件行+认领/预约/attempt 行+
  提交记录),而非恢复者自署 —— 满足"claim owner/恢复者有可核验
  执行权"且不破坏"陈旧 worker 不可越权";
- done 状态的 action 在恢复时也核验提交记录 ↔ 事件一致性(H08
  对已完成动作同样适用,不只对 claimed)。
另:任务书 §6.2 允许"若更改共享 runner 等文件,如实登记对身份的
影响"—— 本批只改 runner 拒绝文案/detail 两个字面,legacy 行为
不变,身份影响登记于 §11/§14.5。

## 17. 提交卫生

- 分支 v4.3 本地提交(不 push);`git add` 显式列:src 四文件+新
  search.py、tests 三新文件+test_ppv1_profile.py、docs/mimo_ppv1_
  chem_review_request.md、本交付书、docs/review_evidence/ppv1_s3a_
  impl_2026-10-07/(证据目录);**禁 git add -A/.,未带入** AGENTS.md
  用户未提交修订、R5–R8 评审侧未跟踪文件(review/mimo 回应/各证据
  目录)与本任务书本身(评审侧产物,归宿由用户定);
- 收尾清理:仅清理本批自建 tmp(baseline worktree 已移除、G01 隔离
  树已删);不删除他人文件、不回写旧永久证据/报告/封存 run;
- 交付状态:本代理变更已提交、无本代理未提交源码测试;既存
  AGENTS.md 差异与未跟踪评审材料单列保留(未 stash/restore/clean)。
