# pollutant_pathway_v1:S3a 回修 r3 交付书(2026-10-07)

- 仓库:`/Volumes/CC/Enzyme_Agent/dependingv43`(v4.3 本地提交,不 push)
- 实施基线(直接父):`dcb7ed62bd4271cfa7bde2732dc0b4fdd0360d03`
  (S3a 回修 r2);复审来源:`docs/POLLUTANT_PATHWAY_S3A_CODEX_REVIEW_R2_2026-10-07.md`
  §4 三组残余 P1(S3A-02/03/04)+ §5 两个边界裁定 + §6 文字修订与
  mimo 事实纠错;回修提示词为其 §8。
- 范围纪律:只修这三组;**不实施 S3b**;S3A-01(四类异身份输出
  绑定)与 S3A-05(停止披露)经复审确认保持关闭,本轮不重开、
  其回归继续全绿;不增加机制库、来源真实性认证、外部 exactly-once、
  科学性能门;判据未冻结。
- 实施证据(绝对路径):`/Volumes/CC/Enzyme_Agent/dependingv43/docs/
  review_evidence/ppv1_s3_impl_2026-10-07/s3a_r3/`(脚本/输入输出/
  argv/env/exit/耗时/HEAD/junit/manifest+SHA;全部执行在仓外新 tmp,
  未在永久证据原地写任何库)。
- mimo v11 请求(自包含,替换 v10):`/Volumes/CC/Enzyme_Agent/
  dependingv43/docs/mimo_ppv1_chem_review_request.md`(v10 送审快照
  已存 `docs/mimo_ppv1_chem_review_request_v10_sent.md`);复审 §6
  的规则文字修订(判据一内因读法/判据二 known_absent 与系数句/
  判据三恒入复用分写/判据四孤儿方向更正、入口限定、重建半边)与
  mimo v10 回应事实纠错(RDKit 2026.03.6、AuditContractError 抛点
  全在 audit.py、虚构分支名不采信等)均已落字进 v11 的 0c 与各节
  "v11 落字";**未把虚构的供体分支、错误 RDKit 版本、错误异常处置
  照搬为事实**。mimo 送审由主会话按通道执行,实施 agent 未调用任何
  外部模型。

## 0. 结论一句话

三组残余 P1 已按复审 §4 最低验收闭合,均为**工程消费协议**修复
(不改任何化学判定);当前源 PPV1 全量 **697 passed / 0 skipped / 0
failed**;新回归 49 项在直接父基线 dcb7ed6 同字节 **40 行为红 + 9
正控绿**(全部为行为断言失败,无 collection 红/返回形态异常/错误
kind 先停);更新的既有测试在基线 1 版本红 + 22 绿;G01 安全隔离
**1299 passed / 8 skipped / 17 deselected**(276 项白名单输入)。
S3b 未交付清单见 §6;并发窗口与恢复 pending 可见性两条诚实边界见
§7。

## 1. 三组逐入口:行为 → 源码 → 证据

### 1.1 S3A-02:完整搜索权威与附随语义

入口矩阵(每处消费的对象、判据与源码位置;`src/pathway_v43/
pollutant/search.py` 下同):

| 入口 | 消费对象 | r2 行为(缺口) | r3 行为 | 源码 |
| --- | --- | --- | --- | --- |
| 首次 complete(`complete_action` 写前 `_preverify_completion`) | 事件类 outcome + 预约/attempt 引用行 | 预约只核存在/run/action;attempt 只核归属;附随 projection/plan 从当前行取出自比较 | 预约**行级内容**:单位恒 1、状态合法未释放、各 limit 所需 scope/subject(共享 alternatives 按 scope=parent+subject=本 action attempt 的 hypothesis 识别);attempt 状态(claimed ⇒ open)/task_key/同 action hypothesis 唯一且与 alt 主体一致;附随内容按**首提同一判据**只读核验 | `_verify_action_references`:1651;`_verify_event_ledger_authority`:1925(附随内容核在 1996 附近调用 `store.verify_event_attachment_content`) |
| B4 恢复(`recover_run` claimed+事件已提交 → `complete_action`) | 同上 | 坏预约/attempt 内容可补 done | 同 first complete 同一判据(经 `complete_action` 写前+写事务内两段) | `recover_run`:2545;`complete_action`:2133 |
| B3(claimed+bundle,事件未提交) | bundle + 必要 attempt/预约引用 | **先写 event(0→1)再在 complete 拒** | 事件提交**之前**先 `_verify_action_references` ⇒ 坏链 0 event/commit/consume、artifact 保全 | `recover_run` B3 前置:2683 附近 |
| done 四入口:claim 复用 / submit 复用 / complete 已有 commit 复用 / recover done | 提交记录 + 完整冻结引用 | 删必需预约/attempt 行仍接受;commit.attempt_id 不存在接受;commit.run 错属仅 recover 单口拒;done submit 返回未存的 foreign event_id | 四口一致:提交记录哈希复算 + **归属(run/action)/合法 kind/事件类记录非空 event_id/适用 attempt 引用(存在、归属、在冻结集合内)** + 完整冻结引用(done 判据:预约 consumed、attempt recorded/failed);done submit 异身份事件**明确冲突**,返回真实已完成 event_id | `claim_action` done 分支:~905;`submit_action_event` done 分支:1503;`_preverify_completion` commit 复用:2070;`_verify_done_action_authority`:2111;`_verify_commit_event`:2766;`recover_run` done 分支:~2596 |
| 附随 projection/plan 权威 | 已存 report_projections/expansion_plans 载荷 | 重放自比较("坏存储=传入坏存储"),悬空 state 引用/非法计划状态通过 | 公共 store 新增**只读** `verify_event_attachment_content`(复用 `_check_projection_scope`/`_check_expansion_plan`/版本门,不另造判据)在消费前拒;同一坏载荷经公共 writer 正常首提同样拒(同源对照) | `store.py:1988`;调用在 `search.py` `_verify_event_ledger_authority` |
| defer(`defer_action`) | 未执行事实 + 引用行 | 引用只核存在/归属 | 同一 `_verify_action_references`(claimed 判据) | `defer_action`:2270 |

保持:合法非事件 outcome(COMMIT_KIND_OUTCOME 不强加 event)、
共享 alternative 预约(同 hypothesis 不同 revision 共享行,两个 action
都可完成)、同事件幂等(created=False 重放不新增)、raw 拒守卫、
12×2 坏事件账反例(r2 回归全绿复跑)。

### 1.2 S3A-03:冻结策略消费不能补默认

| 入口 | r2 行为(缺口) | r3 行为 | 源码 |
| --- | --- | --- | --- |
| `register_search_run` | 校验后按**原始块**落账(partial 存 partial) | 用户 partial 覆盖经 `validate_search_limits` **合法补齐为完整装配块**再落账(装配语义只在写入侧);幂等/冲突按装配后完整块比较(同 effective 策略幂等,异 effective 冲突);四非法块仍零写入拒 | `register_search_run`:631;`_normalized_policy_block`:449 |
| `_limits` 读取(enqueue/claim/请求/budget_snapshot/stop_report 共用) | 对**存储块**用装配语义(缺键补默认)⇒ search_limits=null 时 budget 0 变默认 10、缺 version 被补齐 | **严格冻结块校验** `validate_frozen_search_limits`(profile.py:337):非 dict/null、缺 version、缺任一必需键、未知键、坏类型/越界 ⇒ `search_policy_block_corrupt` 消费前结构化拒、零执行预约 | `_limits`:681 |
| `recover_run` 前置 | 不传 expected 也接受坏存储块;传同一坏块接受 | **先严格核存储块**(无 expected 也拒;不靠调用方传 expected 或先手工校验);expected policy_block 按装配后完整块比较 | `recover_run`:2545(前置段) |

保持:四非法原注册零写入拒(r2 回归)、合法完整往返、各资源
零预算只挡该资源、未执行 defer 释放、已执行不退款(r2 回归全绿
复跑);`validate_search_limits` 用户覆盖装配函数原样保留(仍合法
补齐)。

### 1.3 S3A-04:所有请求消费同源冻结引用

| 入口 | r2 行为(缺口) | r3 行为 | 源码 |
| --- | --- | --- | --- |
| `register_model_request` 已有 row 复用 | 只对照 action/purpose/payload_hash/retry_of ⇒ 存储行 run/attempt 被改坏后原参数重登记 unchanged | 对照 stored 与 incoming **全部身份列**(run/attempt/provider——request_id 派生输入,存储行改坏即冲突;action/purpose/payload_hash/retry_of)⇒ `SearchIdentityConflict` 零写入 | `register_model_request`:1085(复用对照段) |
| 状态口 sent/response/failed(`_verify_request_execution`) | 只核 action claimed + attempt 归属/open ⇒ foreign run / expand 空 attempt 可写状态 | 补 **run 绑定**(request.run_id == action.run_id ⇒ `request_run_binding_mismatch`)与 **expand 必要 attempt**(空 attempt 仅非 expand 合法 ⇒ `request_attempt_required_for_expand`);attempt 归属补 run 维度 | `_verify_request_execution`:1288 |
| `recover_run` pending 请求 | 直接列行,缺 action/已失效执行引用伪装普通合法 pending | 逐行同源守卫:坏/失效引用条目带 `reference_integrity`(error/kind/detail)结构化披露 + "不伪装普通合法 pending" 注记;零新状态写入、不猜补 | `recover_run` pending 段:~2570 |

保持:同键同内容幂等 unchanged、合法非 expand 空 attempt、
scripted/fake 网络 0、真实额度 0 拒登记(网络发送被阻止)、失败/
悬空占额不退、显式 retry 新 request_id + 剩余额度、单认领执行权、
合法 B2 pending(claim 中、attempt open)照常暴露"不默发第二请求"
(r2 回归全绿复跑 + r3 正控)。

## 2. 正负控制清单(49 项新回归)

- **S3A-02 负控(坏案,修前基线红)**:预约 units=0/status 未知/
  scope 错/alt subject 改坏(4);attempt abandoned/异 hypothesis/异
  task_key(3);B4 恢复同判据(2);done 后删预约/attempt 行 ×
  四入口(8);commit.attempt_id 不存在 / commit.run 错属 × 四入口
  (8);附随投影悬空引用/计划非法状态/incomplete 缺原因在首次
  complete 拒(3);done 复用入口对坏附随投影拒(1);B3 前置
  (删预约/attempt ⇒ 0 event/commit、artifact 保全)(2);done
  submit 异 parent 有效事件明确冲突且 B 不入账(1);请求 row 改坏
  后重登记冲突(2);状态口 foreign run/expand 空 attempt 拒(2);
  恢复 pending 坏引用结构化披露(2)。
- **正控(修后必须绿;基线亦绿)**:同一坏 projection/plan 经公共
  writer 正常首提拒(3,同源判据对照);合法完成链 + done 四口
  合法复用 + 预算恰好 consume 一次(1);共享 alternative 预约两
  action 完成且 used=1(1);合法完整策略往返 + budget 0 只拒认领 +
  同块恢复通过(1);合法 B2 pending/同键幂等/非 expand 空 attempt
  登记发送(1)。
- **r2 回归(54 项)全绿复跑**:S3A-01 四类异身份、12×2 坏事件账、
  defer 不退已执行、四非法策略块、请求登记引用闭合等(见
  `tests/test_ppv1_s3a_rework_r2.py`)。
- **存量 594 项全绿复跑**(含四硬杀 B1–B4 子进程、H06 双进程
  barrier、H07/H08、E03/E04、runner 双入口 fail-closed)。

## 3. 独立执行数字(全部 depending43 Python 3.11.16 / RDKit
2026.03.6 / SQLite 3.53.4;`-B` + `PYTHONDONTWRITEBYTECODE=1` +
`-p no:cacheprovider`;证据见 s3a_r3/ 目录)

| 执行 | 数字 | 证据 |
| --- | --- | --- |
| 当前源 PPV1 全量(25 文件) | **697 passed / 0 skipped / 0 failed**,exit 0,7.77s | `current/ppv1_full/` |
| r3 新回归(1 文件 49 项) | **49 passed**,exit 0 | `current/rework_r3/` |
| 四崩溃/H06 双进程/零预算/悬空请求矩阵(自审复跑) | **23 passed**,exit 0,1.54s | `current/crash_barrier_budget/` |
| 直接父基线 dcb7ed6 detached worktree 同字节新回归 | **40 failed / 9 passed**,exit 1 | `baseline/rework_r3/` |
| 同基线更新的既有测试(profile) | **1 failed / 22 passed**(1 版本红:ppv1-profile-11 断言;无行为红) | `baseline/updated_existing/` |
| G01 安全隔离(R7 白名单 + R8/S3a/r2/r3 输入,276 项) | **1299 passed / 8 skipped / 17 deselected**,exit 0,pytest 194.18s / 控制器 195.649s | `g01/` |

基线 40 红细分(全部行为断言失败,非计数错误):**28 项"预期
结构化拒绝未发生"(DID NOT RAISE)+ 12 项断言值不符**(其中 B3
两案为基线先写 event=1 再拒 —— 正是复审 §4.1 第 4 项的消费顺序
缺口;pending 两案为缺 reference_integrity 披露;partial 注册两案
为存储块 2 键而非 11 键完整)。9 项基线绿 = 3 首提同源判据对照 +
4 合法正控 + 1 r2 已闭合的越界读拒(保持控制)+ 1 r2 单口已拒的
commit.run-recover 对照(r2 的 recover 经 run 过滤查不到提交记录
报 done_without_commit_record;r3 起四口一致按
commit_record_binding_mismatch/同拒)。无 collection 红(新回归
只用 r2 已存在的公开 API)、无返回形态 TypeError、无错误 kind
先停导致的内部未执行。

G01 8 项 skip 逐 nodeid:`test_analog_assets.py:95`(v4 对照源)、
`test_analog_v2_corpus.py:62/153`(phase_d 派生 metadata)、
`test_batch_runner.py:52`、`test_score_report.py:110/163/172/184`
(真实评价依赖);17 deselect = 16 slow(`-m "not slow"`)+ 1 明确
排除 `tests/test_export_v3.py::test_charge_fixture_cn_hits_raw_sb_
misses_neutralization_forbidden`。R7 1110/8/17、R8 1138/8/17、
S3a 首批 1196/8/17、r2 1250/8/17 各自单列,不混计。工程数字不
外推 dev(B1 环境中间步骤)或 298(RHEA 通用酶学)科学性能。

## 4. 版本 / 身份 / hash 影响

- 契约:search **ppv1-search-2 → ppv1-search-3**(三组残余消费
  闭合);profile **ppv1-profile-10 → -11**(contracts 登记);
  store 保持 **-9**(表结构与 writer 行为未改;r3 只新增**只读**
  `verify_event_attachment_content` 共享判据入口,复用既有首提
  校验 `_check_projection_scope`/`_check_expansion_plan`/版本门,
  不另造判据、不动事务);search-limits 保持 **-3**(键/默认/
  范围/单位/计数语义未动;装配与严格消费的拆分按 r2 先例随 search
  契约登记)。
- `search_policy_version()` 随 search 契约升版 ⇒ PV 字符串变化 ⇒
  action_id/task_key 派生值变化(测试均经 `search_policy_version()`
  动态取值,无硬编码)。
- `register_search_run` 落账完整装配块 ⇒ 存储 policy_block 字节对
  partial 输入变化(合法 complete 输入字节不变);幂等语义从
  "原始字节相等"变为"装配后 effective 策略相等"。
- legacy code_identity 聚合**不变**
  (`4ea99b698a05ab8685bbd5687835043a2bf07f0c7f219591beccbff2507
  c29ae`;legacy 集排除 pollutant/ 新包,本轮源码改动全部在其内;
  `workflow/runner.py` 未触碰,PPV1 双入口 fail-closed 保持)。
- PPV1 从未放行执行流,无历史产物迁移;v10 身份载荷按既有门拒绝。

## 5. 与复审验收的对照(措辞对齐证据)

- §4.1 预约 units/status/scope、attempt 状态/hypothesis/task、
  first complete/B4/done 四入口一致、附随非自比较、B3 前置、done
  submit 真实 event/明确冲突:逐项闭合(§1.1;基线红 = 修前缺口)。
  **已验证的坏行类与入口即上表所列**;不宣称"全部事件消费入口
  闭合"或"完整权威闭合"这类超出本轮证据的全称。
- §4.2 装配/消费拆分、null/缺版本/坏值消费前拒、budget 0 不变
  10、四非法原注册与各正控保持、不靠 expected policy:闭合
  (§1.2)。
- §4.3 已有 row 复用全列对照、状态口 run 绑定/expand 必要 attempt、
  恢复 pending 守卫、digest-only 不凭空复算(复用比较仍按
  payload_hash;incoming payload 存在即参与哈希)、各保持项:闭合
  (§1.3)。
- §5 边界裁定:TOCTOU 按"两个事务间未持锁,不提供跨并发外部改库
  保证"披露(§7.1);defer 未归因事件保守拒绝保持(§7.2)。
- §6:mimo v11 落字(0c 事实纠错清单 + 判据一 2b/判据二/判据三/
  判据四 v11 落字),未照搬虚构内容(见交付书开头)。
- §7 交付一致性:本轮不使用"完整权威闭合"类全称表述;数字
  697/1299/40+9 可证;测试调整仅 profile 版本断言(1 处 2 行)。

## 6. S3b 未交付清单(诚实边界,不用其缺席新增本批门)

队列化学集成(冻结池/备选/两类 deferred 的调度语义与
expected_parent_revision 激活)、条件依赖/场景转换实际进入调度、
`proposals[]` 模型协议与有界格式反馈、冻结 AtomTool → donor 诊断
→ converter → audit → admission → submit 生产调用链(含
audit_hypothesis 生产 caller 的 AuditContractError 逃逸义务与宽捕获
负控)、PPV1 独立 runner 双入口分流(公开 start_run/resume_run 对
PPV1 继续 fail-closed)。判据未冻结;本批工程通过不代表科学性能
或 S4/S5 启动。

## 7. 自查未闭合残留(诚实清单)

1. **并发窗口(登记边界,非本轮新增)**:`complete_action` 的只读
   预核验与写事务两个事务之间不持锁;顺序单消费者/合法公共 writer
   模型内无窗口,但**不提供跨并发外部 SQL 改库的保证**(复审 §5
   已裁定不据此增第 4 组 P1/阶段门;无"微秒级/必 busy"承诺)。
2. **defer 未归因事件保守拒绝(复审裁定接受)**:冻结身份下已提交
   事件无其他 action 提交记录归因时拒释放;不认证"一定执行过"。
3. **恢复 pending 清单的 run 作用域可见性**:pending 请求扫描按
   run_id 过滤(`_crash_boundary_rows`);请求行的 run 列被改坏成
   foreign run 时该行**不出现在本 run 的恢复清单里**(不伪装成
   普通合法 pending,但也不披露)。此类行在状态消费口(发送/响应/
   失败)与同键重登记口均被 run 绑定/身份冲突拒;跨 run 反向扫描
   属新机制,按"不增加机制库"未加,留待 mimo/Codex 裁定是否需要。
4. **request 状态枚举的未知值**:状态列被改成枚举外值时,现有
   状态机按 `request_not_resendable`/`request_not_failable` 类语义
   拒(不会成功写新状态),但无专门的"状态未知"结构化码;未按
   新枚举校验扩机制。
5. **claim 幂等收据/停止报告等 r2 已有入口**未接入本轮的行级内容
   判据(其消费对象不是 action 引用行;done 复用路径已接入)。
6. **mimo v11 与 Codex 复审待跑**:由主会话按通道接力,本轮实施
   agent 未联系任何审核方;采纳与否、下一轮范围以复审为准。

## 8. 提交

- v4.3 本地提交(不 push;git add 仅显式路径:src/pathway_v43/
  pollutant/{profile,store,search}.py、tests/test_ppv1_s3a_rework_
  r3.py、tests/test_ppv1_profile.py、docs/POLLUTANT_PATHWAY_S3A_
  DELIVERY_R3_2026-10-07.md、docs/mimo_ppv1_chem_review_request.md、
  docs/review_evidence/ppv1_s3_impl_2026-10-07/s3a_r3/);提交哈希见
  `git log -1`(提交信息含本交付书标题);既存 AGENTS.md 用户差异
  与旧未跟踪评审材料不纳入提交。
