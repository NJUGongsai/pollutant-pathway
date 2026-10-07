# pollutant_pathway_v1:S3a 回修 r4 交付书(2026-10-08)

- 基线:直接父 `41d0cd55f3def050a62325f00235cf22da302d2e`(r3);
  本轮 = Codex S3a 复审 R3
  (`POLLUTANT_PATHWAY_S3A_CODEX_REVIEW_R3_2026-10-08.md` §4 三组
  残余 P1 的 §8 有限回修)。
- 范围:只修 S3A-02(必要预约**集合**完整性)/ S3A-03(请求
  **状态口**接冻结策略)/ S3A-04(**非法来源状态**不能改记合法
  failed);S3A-01/05 与已证行级旧反例保持关闭;不实施 S3b、不加
  科学性能/机制库/冻结门;判据未冻结。
- 证据根:`docs/review_evidence/ppv1_s3_impl_2026-10-08/s3a_r4/`
  (manifest+SHA256SUMS;所有执行在仓外新 tmp)。

## 0. 结论一句话

三组残余已按复审 §4.1/§4.2/§4.3 最低收口闭合:必要预约集合缺项
在 9 入口先结构化拒(逐行守卫保留)、请求状态口在新 status 写入前
消费同一严格冻结块校验、枚举外来源不能洗成合法 failed;90 项新回归
在直接父基线上 77"未发生指定异常"红 + 1 形态红 + 12 正控绿,
PPV1 全量 787 绿,G01 安全隔离 1389 绿;同时更正 r3 交付书 §7.4
"未知 status 不会成功写"的错误声明与 §2 红分类精度(见 §5)。

## 1. 三组逐入口:行为 → 源码 → 证据

### 1.1 S3A-02:必要预约集合完整性(逐行守卫保留)

**入口矩阵(9 入口,全部经同一 `_verify_action_references`)**:
first complete(`complete_action` 写事务内)/ B4 恢复(`recover_run`
→ complete)/ **B3 事件提交前**(`recover_run` b3_precheck,先于
`store.submit_event`)/ B1(`recover_run` b1 分支)/ defer
(`defer_action` 释放前)/ done 四口(claim 复用 / submit 复用 /
complete 已有 commit 复用 / recover done,均经 `_verify_done_
action_authority`)。合法来源状态:claim 认领;必要资源条件:按
`claim_action`/`_create_attempt` 现有创建规则(总 action 恒有;
transition 另有 transitions;expand 按 attempt 引用集有
alternatives/attempts + reopen_of 非空的 reopens;retrieve 的两条
检索预约仅非 cache_hit 认领创建);共享主体:alternatives 预约跨
action 共享(scope=parent+subject=hypothesis,主体幂等 id_basis);
验证来源:预约 ID 派生抽出 `_reservation_id`
(search.py:572)与 `_reserve`(search.py:883)**单一来源**,
必要集合核验(search.py:2020–2081)与创建侧同源派生,不在核验
处另写第二套派生规则。

**修复前后行为**:

| 入口 | 修前(父 41d0cd5) | 修后(r4) |
| --- | --- | --- |
| first complete / B4 | 删必要预约 ref(行在)⇒ 被漏行不结算仍写 done/commit;删 ref+row ⇒ UPDATE 0 行当成功,总额度 used=0 | `necessary_reservation_ref_missing` / `reservation_row_missing` 结构化拒,零新 commit/consume,action 保持 claimed |
| B3 事件提交前 | 先写 event1/commit1 再靠 complete 拒,总额度 used=0 | b3_precheck 先拒,**0 event 新增**,artifact 保全 |
| B1 / defer | 不完整引用当 intact/可挂起 | 结构化拒(挂起不再退还已不完整的记账) |
| done 四口 | 缺必要集合仍 `done_commit_verified`/成功复用 | 完整权威核验前先拒,done 状态保持、零写入 |

上限 1 双链钉子(复审 §4.1 独立证据):干净链第二 claim 按预算
不足拒保持;删总额度 ref+row 后第一次 complete 被拒(不再
"used0/commits2 骗过 max_total=1"),后续不同 hypothesis 的干净
链仍可正常完成(损坏只钉死被删证据的 action,不扩大为全面拒绝)。

**证据**:`tests/test_ppv1_s3a_rework_r4.py`(54 坏分案 = 9 入口
× 3 必要预约 × 仅删 ref/删 ref+row,与复审探针
`necessary_reference_probe.py` 同构;9 入口 clean 正控;上限 1
双链;cache_hit 正控 + 非 cache 坏案;transition 必要预约);
JUnit 与逐案断言见 `current/rework_r4/`、父基线红绿见
`baseline/rework_r4/`(58 个 SearchIntegrityError 未拒红)。

### 1.2 S3A-03:请求状态首消费接冻结策略守卫

**入口矩阵**:register 装配(既有,validate_search_limits 写入侧
补齐)/ 已存读取(budget_snapshot)/claim/recover/请求新旧登记
(既有,`_limits` 于 register)/ **sent / response / failed(r4
新增:search.py:1480、1512、1564,在新 status UPDATE 之前消费
`self._limits(row["run_id"])` 即 validate_frozen_search_limits)**。
合法来源状态:先合法登记(scripted/real);必要资源条件:存储
search_limits 完整冻结块;验证来源:与预算/认领/恢复**同一**守卫
(`_limits` → profile.validate_frozen_search_limits),不在状态口
补默认或另造判据。

**修复前后行为**:修前,合法先登记的请求在存储 search_limits 被置
null/删 version/坏值(bool/越界/未知键/负数)后,3 状态口均成功
写 sent/responded/failed(复审 §4.2:3 状态口 × 2 模式 + 四坏值
×3 口共 18 案实际写入);修后,同 18 案全部
`SearchRecoveryError(kind=search_policy_block_corrupt)` 先拒、
事务回滚、**无成功状态变化**(状态/网络计数保持)。合法策略下
registered→sent→responded、registered/sent→failed、scripted 网络
0、真实额度同键幂等不重复扣、失败/悬空占额全部保持(r4 正控 +
r3 既有 49 项保持)。

**证据**:同测试文件(18 坏案 = 6 损坏 × 3 状态口,含 response
先合法到 sent 再损坏的时序;合法策略正控);父基线 18 个
SearchRecoveryError 未拒红。

### 1.3 S3A-04:非法来源状态不能改成合法 failed

**入口矩阵**:同键复用(register_model_request 存储状态枚举核,
search.py:1283)/ sent(状态机 != registered 即拒,r3 已闭合,
保持)/ response(!= sent 即拒,保持)/ **failed(正面限定
registered/sent 来源,search.py:1544–1561;枚举外未知来源
`request_status_unknown` 结构化拒并保全)**/ recover(run 范围
枚举外行结构化披露 `unknown_status_requests`,search.py:2763、
2766,不改状态、不伪装合法 pending)。复用既有
`REQUEST_STATUSES` 与迁移规则,不新增枚举体系;专用"状态未知"
理由码只是结构化披露,**不是以新增 reason 名替代行为拒绝**。

**修复前后行为**:修前,合法登记行仅改 status 为 `corrupt-status`
后,公共 `mark_request_failed` 正常返回并写 corrupt-status→failed
(损坏生命周期被正常化,原未知状态消失 —— 这正是 r3 交付书 §7.4
错误声明"不会成功写新状态"的反证,复审 §4.3 点名);同键重登记
返回 unchanged 并带坏状态;恢复扫描不披露该行。修后:failed 口
`request_status_unknown` 拒、行原样保全;同键复用按完整性失败拒
(零写入);恢复报告披露(不在 pending 清单)。合法
registered/sent→failed、responded/failed/abandoned 终态不可再
改记/重发(`request_not_failable`/`request_not_resendable` 保持)、
显式 retry 新 request_key、非 expand 合法空 attempt、真实失败占额
不释放、scripted 网络 0 全部保持。

**证据**:同测试文件(unknown→failed 拒并保全、sent/response
照旧拒、register 复用拒、recover 披露、合法生命周期正控);父
基线 1 个 SearchContractError 未拒红 + 1 形态红(恢复报告缺键)
+ 1 register 复用红。

## 2. 正负控制清单(90 项新回归)

- **S3A-02(66 项)**:54 坏分案(9 入口 × 3 必要预约 × 2 模式,
  复审 §4.1 反例矩阵同构复跑)+ 9 入口 clean 正控 + 上限 1 双链
  (坏 + 干净对照)+ cache_hit 正控/非 cache 删 ref 坏案(1)+ 
  transition 必要预约(坏 + 预算拒);
- **S3A-03(19 项)**:18 状态口策略坏案(6 损坏 × 3 口)+ 合法
  策略状态机/幂等/真实额度正控(1);
- **S3A-04(5 项)**:unknown→failed 拒并保全、sent/response 照旧
  拒(保持控制)、register 同键复用拒、recover 披露、合法生命
  周期(registered/sent→failed、终态不重发/不重败、真实失败占额
  不释放、显式 retry 新键、非 expand 空 attempt);
- 合法共享/幂等/同 hypothesis 不同 revision 正控由 r2/r3 既有
  测试继续覆盖(r2+r3 共 103 项本轮全绿,含共享 alternative 预约、
  reopen 双重约束、B1 续跑同 attempt、合法非事件 outcome)。

## 3. 独立执行数字(全部 depending43 Python 3.11.16 / RDKit
2026.03.6 / SQLite 3.53.4;PYTHONDONTWRITEBYTECODE=1、-B、
pytest -p no:cacheprovider)

| 执行 | 结果 | 证据 |
| --- | --- | --- |
| PPV1 全量(26 文件 = r3 的 25 + r4 新文件) | **787 passed / 0 skipped / 0 failed**,exit 0,pytest 9.43s | `current/ppv1_full/`(stdout/JUnit/run_meta) |
| r4 新回归(当前源) | **90 passed**,exit 0,1.16s | `current/rework_r4/` |
| 四崩溃(独立子进程硬杀 B1–B4)/H06 双进程 barrier/H07 H08/零预算/悬空请求矩阵 | **23 passed**,exit 0,2.26s | `current/crash_barrier_budget/` |
| 父 41d0cd5 detached worktree 同字节 r4 新回归 | **78 failed / 12 passed / 0 collection error**,exit 1,1.58s | `baseline/rework_r4/`(JUnit、failed_nodeids、逐案分类) |
| 78 红细分 | **77"预期结构化拒绝未发生"**(58 SearchIntegrityError + 18 SearchRecoveryError + 1 SearchContractError)**+ 1 形态红**(恢复报告缺 unknown_status_requests 键的 KeyError);无值断言红、无错误 kind 先停、无返回形态 TypeError | `baseline/rework_r4/failure_classification.json` |
| 12 父基线绿 | 9 入口 clean 正控 + 1 sent/response 未知状态已拒保持 + 2 合法生命周期控制 | 同上 |
| 同基线更新的既有测试(test_ppv1_profile 副本) | **1 failed(版本字面量 -12/-4,唯一改动)/ 22 passed** | `baseline/updated_existing/` |
| 安全隔离 G01(r4 控制器 = r3 控制器 + r4 测试输入) | **1389 passed / 8 skipped / 17 deselected**,exit 0,pytest 196.85s | `g01/`(preparation/input_sha256/execution_result/JUnit/deselected_nodeids) |

G01:277 项输入 = R7 清单 216 + 普通 dependingv3/src 42 + 本仓
普通资产镜像 18 + `tests/test_ppv1_s3a_rework_r4.py`(r3 为 276);
fresh SHA256、实际 HEAD+脏状态记录;8 skip = 5 真实评价依赖 +
1 v4 对照源 + 2 phase_d 派生 metadata;17 deselect = 16 slow +
1 显式排除 export 用例(逐 nodeid 留证);零金标/题面/封存/v4/
真实 provider,网络 0;1389 = r3 1299 + 90(历史 R7 1110、R8
1138、S3a 首批 1196、r2 1250、r3 1299 各自单列不混计)。全部
工程数字不外推 dev(B1 环境中间步骤)或 298(RHEA 通用酶学)
科学性能。

## 4. 版本 / 身份 / hash 影响

- `PPV1_SEARCH_SCHEMA_VERSION`:ppv1-search-3 → **ppv1-search-4**
  (必要集合完整性/状态口策略守卫/生命周期来源闭合;计数语义、
  键、单位未动);`PPV1_PROFILE_SCHEMA_VERSION`:ppv1-profile-11
  → **ppv1-profile-12**(contracts 登记同升);
- store 保持 **ppv1-store-9**:表结构与 writer 行为未改,r4 核验
  全部复用既有函数,无新入口;search-limits 保持
  **ppv1-search-limits-3**:状态口接守卫与必要集合语义是消费
  语义,按 r2/r3 先例随 search 契约登记;
- `runner.py` 未改:PPV1 双入口继续 fail-closed;legacy
  code_identity 聚合与父同为
  `4ea99b698a05ab8685bbd5687835043a2bf07f0c7f219591beccbff2507c
  29ae`(legacy 排除 pollutant/ 新包,r4 改动全部在其内);
- 更新的既有测试仅 `tests/test_ppv1_profile.py` 两个版本字面量
  断言(-11→-12、search-3→-4);r2/r3 全部既有测试不改不动
  (本轮全绿)。

## 5. 与复审验收的对照(措辞对齐证据)

- **§4.1 最低收口**:按现有创建参数同源确定必要集合、首次消费
  核完整性后再逐行核内容 —— 实施为:完整性与逐行内容同在首次
  消费、任何写账之前核验(逐行守卫保留在原位,r3 已关闭的行级
  反例诊断 kind 不变;完整性缺项即使剩余清单非空也先拒)✓;
  覆盖 9 入口 ✓;B3 零 event 新增、保全 ✓;主体
  共享 alternative、条件适用 reopen、合法非 expand/非事件
  outcome、同 hypothesis 不同 revision、幂等保持 ✓;cache_hit
  retrieve 不强加 ✓(行不存在按 cache_hit 合法,见 §7.1 边界);
  无新增独立来源证明/全库签名/机制库 ✓。
- **§4.2 最低收口**:状态首消费共用严格冻结块守卫、在新 status
  写入/执行许可之前失败 ✓;核失败无成功状态变化、不依赖 expected
  policy/调用方预验 ✓;合法用户 override 只在装配补齐、注册后
  完整块 ✓;合法 registered→sent→responded/failed、各适用零
  预算、失败/悬空不退已登记额度 ✓;无重复扣已占请求额度、无
  limits 单位重解释 ✓。
- **§4.3 最低收口**:所有适用状态消费核已有枚举和合法来源 ✓;
  失败口只有 registered/sent 允许正常 failed,未知值结构化拒/
  保全、不静默洗成合法终态 ✓;sent/response 已拒保持 ✓;同键
  既有坏 status 与恢复披露按适用语义明确(同键复用完整性拒、
  恢复结构化披露)✓;专用 reason 码可选且未替代行为拒绝 ✓;
  合法失败、显式 retry、closed 不重发、scripted 网络 0 保持 ✓;
  无新枚举体系/真实 provider/外部 exactly-once ✓。
- **§4.3 点名的 r3 交付错误声明更正**:r3 交付书 §7.4 第 4 条曾
  写"状态列被改成枚举外值时,现有状态机按 request_not_
  resendable/request_not_failable 类语义拒(**不会成功写新状态**)。
  但无专门的'状态未知'结构化码"—— **该声明不实**:R3 复审以
  公共链实证 mark_request_failed 会把 corrupt-status 正常写成
  failed(未知生命周期被正常化)。r4 修的是**行为**(正面限定
  合法来源 + 未知值结构化拒),`request_status_unknown` 只是披露
  名,不是以新增错误名替代行为拒绝。
- **§2 数字精度更正(沿 R3 复审 §2 口径)**:r3 交付书把父基线
  40 红写作"28 未拒 + 12 值断言";R3 复审精化为"**35 未发生
  指定异常 + 5 值断言**"。本轮交付按同一口径登记:78 红 = 77
  未发生指定异常 + 1 形态红(缺报告键 KeyError),无值断言红;
  12 绿按性质分列(9 合法行为正控 + 3 既有坏输入拒绝/已闭合保持
  控制),不称"合法化学正控"。

## 6. S3b 未交付清单(诚实边界,不用其缺席新增本批门)

队列化学集成(冻结池/备选、expected_parent_revision 的两类
deferred 激活调度)、条件依赖/场景转换实际进入调度、`proposals[]`
模型协议与有界格式反馈、冻结 AtomTool → donor 诊断 → converter →
audit → admission → submit 生产调用链(含 audit_hypothesis 生产
caller 的 AuditContractError 逃逸义务与宽捕获负控)、PPV1 独立
runner 双入口分流(公开 start_run/resume_run 对 PPV1 继续
fail-closed)。判据未冻结;本批工程通过不代表科学性能或 S4/S5
启动。

## 7. 自查未闭合残留(诚实清单)

1. **retrieve 检索预约的 cache_hit 条件参数不落列(本轮新增
   披露)**:cache_hit 认领不创建检索预约行,与"非 cache_hit
   认领后把两条检索预约 ref+row 一起删"在存储上同构(无持久
   区分标记);必要集合按"行存在 ⇒ 必须被引用"核验,行不存在
   按 cache_hit 合法不强制 —— ref+row 同删的检索案当前不可检
   出。复审探针与最低收口均未要求该形态(其 3 必要预约为
   expand 的无条件类);不加 schema 列(store 保持 -9),留
   mimo/Codex 裁定是否需要持久 cache_hit 标记。
2. **并发窗口(登记边界,非本轮新增)**:complete 的只读预核验
   与写事务之间不持锁;顺序单消费者/合法公共 writer 模型内无
   窗口,但不提供跨并发外部 SQL 改库的保证(复审 R2/R3 §5
   裁定保持)。
3. **defer 未归因事件保守拒绝(复审裁定接受,保持)**:不能
   安全证明可退 ⇒ 不退;不认证"一定执行过"。
4. **恢复清单的 run 作用域可见性(边界细化为两半)**:请求行
   run 列被改坏成 foreign run 时该行不出现在本 run 恢复清单
   (状态口/同键重登记均拒);**run 范围内的枚举外状态行本轮起
   结构化披露**(unknown_status_requests),foreign-run 行仍不
   反向披露 —— 跨 run 反向扫描属新机制,未加,留裁定。
5. **claim 幂等收据/停止报告等 r2 已有入口**未接入行级内容/
   必要集合判据(其消费对象不是 action 引用行;done 复用路径
   已接入)。
6. **mimo v12 与 Codex 复审待跑**:由主会话按通道接力,本轮
   实施 agent 未联系任何审核方、未调用任何外部模型;采纳与否、
   下一轮范围以复审为准。

## 8. 提交

- v4.3 本地提交(不 push;git add 仅显式路径:`src/pathway_v43/
  pollutant/{profile,search}.py`、`tests/test_ppv1_s3a_rework_
  r4.py`、`tests/test_ppv1_profile.py`、
  `docs/POLLUTANT_PATHWAY_S3A_DELIVERY_R4_2026-10-08.md`、
  `docs/mimo_ppv1_chem_review_request.md`、
  `docs/review_evidence/ppv1_s3_impl_2026-10-08/s3a_r4/`);提交
  哈希见 `git log -1`(提交信息含本交付书标题);既存 AGENTS.md
  用户差异与旧未跟踪评审材料不纳入提交;store.py 未改不提交。
