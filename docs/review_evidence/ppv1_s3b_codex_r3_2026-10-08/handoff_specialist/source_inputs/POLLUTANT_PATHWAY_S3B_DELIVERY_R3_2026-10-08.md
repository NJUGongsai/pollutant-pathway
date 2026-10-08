# pollutant_pathway_v1:S3b 回修 r3 交付书(2026-10-08)

- 基线:直接父 `2bedfc060a9b19019ba44aa2a56dcacb88450c3b`
  (S3b-r2 交付;Codex S3b-r2 复审未放行,唯一 P1 = S3B-01 后段
  锚定);本批 = 复审 R2 §8 有限回修提示词的**一次性实施**,只收口
  该 P1,不重开 S3B-02~06/已过 S3a;复审报告/永久证据只读。
- 范围:**公开 resume 首消费前**把读取的冻结计划与独立既存
  run/root/task 原绑定核对(覆盖 root retrieve 已 done 的 B3/B4;
  自洽 artifact 内自 hash/自己写的 plan_digest 不能当独立证书)。
  不做 S4/S5、不加分布式锁/机制库/密码学服务、不抗全库协同改写,
  判据未冻结,科学性能 pending。
- 证据根:`docs/review_evidence/ppv1_s3_impl_2026-10-08/s3b_r3/`
  (README + manifest.json + SHA256SUMS;全部执行在仓外新 tmp 或
  新 worktree;探针与 G01 控制器随目录,拒绝已存在输出目录)。

## 0. 结论一句话

唯一 P1 S3B-01 的后段锚定收口:resume 在任何 recover 补账/事件/
调度/consume 之前,用 **start 落账的根 retrieve 行**(DB 通道独立
权威;task_key 经单一来源 `decision_task_key` 重算比对)核对冻结
计划内容身份 —— 复审两原反例(B3/B4 自洽重封装 artifact、省略
plan 的 public resume)**均结构化拒 `frozen_plan_binding_mismatch`
且十五表零变化、原文件保全**(公开入口真子进程取证 15/15);
PPV1 全量 **879 passed/0 skip**(871 存量 + 8 新 r3,32 文件);
新测试对直接父 2bedfc0 同字节 **5 行为红 + 3 合法正控绿**
(0 collection/版本/字段红,本批不更新既有测试文件);G01 安全
隔离 **1481/8/17 exit 0(288 输入)**;生产化学链
production.py 与全部共享/legacy 文件**零改动**(父↔当前逐字节
一致,legacy 聚合保持 `18007e6a…f1374d6`)。

## 1. S3B-01 后段锚定:入口→已冻结权威→守卫→正负控制矩阵

### 1.1 入口矩阵(start/resume/frozen-input-load/recover-B3/recover-B4/driver)

| 入口 | 已冻结权威(独立既存) | 守卫 | 正负控制 |
| --- | --- | --- | --- |
| `start_ppv1_run`(runflow.py:1328) | 计划 → 冻结 artifact(`_persist_frozen_plan` :1395→:229-240)+ 根 retrieve 任务输入(task_key :1398-1407 由 `decision_task_key` 绑 `_plan_digest(plan)`;payload.plan_digest :1416)—— **同一调用内同源写入,无漂移窗口** | start 后驱动只消费冻结来源;重复 run 拒;会话 flock | 正:正常 start 完成(存量全量) |
| resume 传入比对侧(:1502-1512,r2 保持) | 冻结 artifact 计划摘要 | `frozen_plan_mismatch`(显式换 plan 拒;零写入) | 负:显式换 plan 拒(存量/探针 frozen_plan_changed);正:同计划显式传入(r3 正控 3) |
| `frozen-input-load`(`_load_frozen_plan` :242-272,r2 保持) | artifact 信封 payload_hash + 载荷内 plan_digest(自洽) | H07 完整性包装:缺/坏/digest 不符结构化拒(integrity/missing/corrupt/digest_mismatch;保全原文件) | 负:篡改/缺/坏 artifact 拒(r2 测试保持);**自洽重封装在此层通过 —— 由下一条闭合** |
| **resume 后段锚定(:1514-1521 调 `_verify_frozen_plan_binding` :274-390,本批新增)** | **start 落账的根 retrieve 行**(search_actions DB 通道:payload.plan_digest;task_key 列/载荷同值,由单一来源 `decision_task_key` 派生冻结)—— 与 artifact 文件相互独立 | ①行内身份字段 + 行内 plan_digest 重算 task_key 比对,不符 ⇒ `frozen_plan_anchor_corrupt`(:331-352);②锚摘要 ≠ 冻结计划摘要 ⇒ `frozen_plan_binding_mismatch`(:368-382);无携带 plan_digest 的 retrieve 行 ⇒ `frozen_plan_anchor_missing`(:354-367);载荷不可解析/非 dict ⇒ `frozen_plan_anchor_corrupt`(:296-324)。**先于 recover_run(:1522)的 B4 补账/B3 bundle 消费与任何新调度/事件/consume**;业务表/event/commit/consume 零新增,原资料保全;summary["frozen_plan_binding"](:1547)披露锚 id/状态/摘要 | 负(**两原反例翻转**):B3/B4 自洽重封装+省略 plan 拒(r3 测试 1/2;探针 2/2,root 锚 `880bf6…`、新 artifact 摘要 `7164d4…` 与复审原值逐项一致);重封装+显式同新 plan 拒(测试 3);缺锚拒(测试 4);坏锚拒(测试 5)。正:B3 省略 plan 合法恢复幂等(测试 6)、同计划显式(测试 7)、合法原计划转换 phase-1(测试 8) |
| recover-B3(`recover_run` bundle 消费,search.py:3069+) | 前置于锚核对(:1514-1521 在 recover 之前) | B3 消费只在锚核过后发生 | 负:B3 换 artifact 在消费前拒;正:合法 B3 同 output 恢复(测试 6/父存量) |
| recover-B4(`recover_run` 幂等补账) | 同上 | B4 补账只在锚核过后发生 | 负:B4 换 artifact 拒(事件已在,补账/转换/consume 零新增);正:合法 B4 补齐(r2 存量/探针 crash_after_event_submitted) |
| driver 调度(`reconcile_followups`/`_run_*`,消费冻结计划) | 冻结计划(已在入口锚定) | retrieve 执行层 plan_digest 核(:702-724)/decide 层 pool_digest 核(:784-818)保留为纵深防御 | 正:合法转换/三产物/重复 resume 无新增(r2 存量 + 探针) |

### 1.2 实现要点(共享规则,非单点补丁)

- **共享规则**:`_verify_frozen_plan_binding`(runflow.py:274-390)
  是 resume 入口的单一核对函数 —— 不是只改 `_run_retrieve`/
  `_run_decide`(执行层第二核保留),也不是只拒显式传入新 plan
  (传入比对侧独立保持);锚核对覆盖 root retrieve 已 done 的
  B3/B4(执行层核验后段不可达的入口闭合);
- **单一来源派生**:task_key 重算直接复用 start 侧同一
  `decision_task_key`(search.py:379-399),不另造第二套规则;
  锚 = 本 run 全部携带非空 payload.plan_digest 的 retrieve 行
  (当前只有 start 落账的根 retrieve;followup retrieve 不绑定
  计划摘要,扫描自动兼容);
- **最小实现**:不新增表/列/密码学服务(search-6/store-9 不动,
  核对读既有行);不抵抗全库协同改写(复审 §4 明示范围外);
  缺/坏锚/不符均先结构化拒(`PPV1RunError`,kind 分列),拒绝
  时序在 recover/补账/调度/consume 之前 ⇒ 零业务账写入。

### 1.3 前后行为对照(两原反例,复审 R2 §4 公共复现)

| 场景 | 父 2bedfc0(r2)行为 | r3 行为 |
| --- | --- | --- |
| B3(bundle 已写)后只改 frozen_plan artifact(加注入转换、重算自洽摘要),public resume 省略 plan | 沿旧 action/attempt/event 恢复,**新增原计划没有的 scenario_transition 并在 followup 消费新上下文**(phase-injected 转换 1);root 已存摘要 `880bf6…` 与 artifact 新摘要 `7164d4…` 不一致但无拒绝 | `frozen_plan_binding_mismatch` 结构化拒(anchor_status=done);十五表逻辑快照零变化;被改 artifact 逐字节保全;转换 action 0 |
| B4(事件已提交)后同样只改 artifact | 同上(事件已在,补账+新转换+consume) | 同上拒绝;事件/补账/consume 零新增 |
| 重封装 artifact + 显式传入同新计划 | `frozen_plan_mismatch` 不触发(传入==artifact),完成注入转换 | 锚核对拒(自洽证书+传入计划互证不是原输入) |
| 根 retrieve 行 plan_digest 被移除(DB 侧) | 不构成拒绝,正常恢复 | `frozen_plan_anchor_missing` 拒 |
| 根行 payload plan_digest 被改、task_key 落账未动 | 不构成拒绝(自洽互证) | `frozen_plan_anchor_corrupt` 拒(单一来源重算不同源) |
| 合法:同计划/省略 plan/合法原计划转换/四崩溃/三产物/重复 resume | 正常 | **不变**(父绿正控 + 879 存量全绿 + 探针保留控制 13/13) |

## 2. 版本/身份/Hash 影响(逐项披露)

- **RUNFLOW_VERSION:ppv1-runflow-2 → ppv1-runflow-3**(runflow.py:
  157;resume 消费契约新增入口锚核对;无测试断言其字面量,本批
  0 个既有测试文件更新);FROZEN_PLAN_VERSION 保持
  `ppv1-frozen-plan-1`(artifact 格式未变);profile 保持 **-14**、
  search 保持 **-6**、store 保持 **-9**(无新表/列,核对读既有
  search_actions 行)、search-limits 保持 **-3**、
  format-feedback 保持 **-1**、model-proposals 保持 **-2**;
  契约变更登记于 profile.py:150-163(注释注册表)。
- **生产化学链零改动**:production.py 本批 SHA 与父一致
  (`3b1a66ea…`,r2 复审核验值);chemstate/path_context/
  hypothesis/audit/events/store/queue/model_protocol/
  workflow-runner 与父逐字节一致(git diff 仅
  pollutant/runflow.py + pollutant/profile.py 注释;
  `metadata/legacy_identity_check.json`:52 份 legacy
  code_identity 文件父↔当前全部逐字节一致,legacy 聚合保持
  `18007e6a…f1374d6`—— r2 复审已证父=当前,本批未触碰其中
  任何文件)。
- 新增测试文件 1 个:`tests/test_ppv1_s3b_r3.py`(8 用例:
  5 负控 + 3 正控);本批**不更新任何既有测试/worker 文件**
  (r2 的 20 项与全部存量 871 项零改动全绿)。

## 3. 独立执行数字(depending43 Python 3.11.16 / RDKit
2026.03.6 / SQLite 3.53.4;PYTHONDONTWRITEBYTECODE=1、-B、
pytest -p no:cacheprovider)

| 执行 | 结果 | 证据 |
| --- | --- | --- |
| PPV1 全量(`pytest tests/ -q -k ppv1`,31→**32 文件**) | **879 passed / 0 skipped / 0 failed,exit 0**(871 r2 存量 + 8 新 r3) | `current/ppv1_full.*` |
| 新 r3 焦点(当前工作树) | **8 passed** | `current/current_r3_focus.*` |
| 父 2bedfc0 detached worktree 同字节(新 r3 文件,cmp 相同) | **5 行为红 + 3 合法绿 / 0 collection errors**(全部"未结构化拒"型;父上 public resume 完整执行,失败点在拒绝断言,非早停内部段) | `baseline/parent_r3.*` + `parent_r3_classification.json` + `worktree_setup.log` |
| S3B-01 反例翻转探针(公开入口真子进程,fresh tmp) | **15/15 观察符合**(两原反例拒+零变化+保全;13 保留控制全绿) | `probe/`(observations.json + inputs/logs/tables + 二进制 SHA 清单) |
| 安全隔离 G01(r3 控制器 = r2 控制器 + 1 新输入) | **1481 passed / 8 skipped / 17 deselected,exit 0**(1473 r2 + 8 新 r3;pytest 213.90s/外层 215.43s) | `g01/` |

G01:288 输入 = 287 r2 + 1 新增(test_ppv1_s3b_r3.py);runflow/
profile 为既有白名单路径的更新副本(新 SHA);fresh SHA256、实际
HEAD(2bedfc0)+ 脏状态记录;8 skip = 5 真实评价 + 1 v4 对照 +
2 phase_d 派生 metadata;17 deselect = 16 slow + 1 显式排除
export 用例;零金标/题面/封存/v4/真实 provider,网络 0;历史
1110/1138/1196/1250/1299/1389/1453/1473 各自单列不混计;全部
工程数字不外推 dev(B1 环境路径中间步骤)或 298(RHEA 通用
酶学)科学性能。

## 4. 复审 R2 §4 最低收口逐项对照

| 最低收口要求 | 本批落点 |
| --- | --- |
| 公开 resume 在任何 recover B3 event 提交/B4 补账/driver 调度之前,用独立既存权威核冻结计划内容与该 run/root/task 初始绑定,不依赖旧 retrieve 是否还会执行 | §1.1 锚核对行(:1514-1521 在 recover_run 之前;权威 = 根 retrieve DB 行;root 已 done 的 B3/B4 覆盖 —— 探针 anchor_status=done) |
| 版本/身份/必要锚缺失或不符先结构化拒,且业务表/event/commit/consume 零新增,原资料保全 | anchor_missing/anchor_corrupt/binding_mismatch 三类 kind;探针十五表逻辑快照相等 + 被改文件逐字节保全 + 转换 action 0 |
| 沿 start/resume 同源规则,正常同计划、省略 plan、显式计划合法全保持 | r3 正控 3 项父绿 + 探针 13 保留控制 + 871 存量零改动全绿 |
| 只改一份 artifact 的 B3/B4 自洽重封装必须拒 | 两原反例翻转(测试 1/2 + 探针 2/2,摘要与复审原值逐项一致) |
| 不规定必须增加新表/密码学签名,不要求抵抗同时改完所有权威,不需新阶段功能 | 无新表/列/签名服务(§1.2 最小实现);全库协同改写在范围外如实登记 |

## 5. 保留控制清单(不全面禁转换/不全拒恢复换通过)

- **同计划/省略 plan**:r3 正控 6/7(父绿)+ 探针
  frozen_plan_same/omitted(1 event/4 commit);
- **显式换 plan 第一层拒**:探针 frozen_plan_changed
  (`frozen_plan_mismatch` 保持;父行为同);
- **合法原计划转换**:r3 正控 8(转换 done、followup 用 phase-1
  新上下文;父绿)+ 探针 transition_normal/after_event_submitted
  (phase-1);
- **四崩溃合法恢复 + 重复完成无新增**:探针 crash_after_claim/
  request_registered/bundle_written/event_submitted(1 event/
  4 commit;B2 1 registered request、network 0、pending 披露、
  不默发)+ `*_again` 计数不变;父存量四崩溃测试全绿;
- **三产物 0/部分/全部恢复**:探针 three_products_after_two
  (2/3 硬杀 → 恢复 3/3,预算放宽 30 如实登记);r2 存量
  test_s3b03_* 零改动全绿(0/部分/全部窗口);
- **双进程真工具只一执行/硬杀接管**:r2 存量
  test_s3b04_concurrent_public_resume_single_executor 零改动全绿
  (r3 的锚核对在会话锁之后、recover 之前 —— 竞争方仍在执行前
  `driver_session_active`,顺序不变);
- **novel 及弃权**:探针 model_novel_nonempty(2 events/
  requests≥1/network 0)/model_abstain_empty(0 event/1 request);
  r2 存量 test_s3b05_* 零改动全绿;
- **blocked 多原因**:探针 zero_depth_budget(主因 budget_limit、
  other_reasons 含 depth_limit、blocked_objects 1、reason
  depth_limit);r2 存量 test_s3b06_* 零改动全绿;
- **E01/E02/C06/H04**:r1/r2 存量测试零改动全绿(851/871 存量
  全量内;S3a/R8 已关项不重开);
- **真实化学 unknown/partial/Audit 异常控制**:production.py/
  audit.py 等字节不变,存量全量(879)保持;本批未重跑化学专项
  探针(以字节一致 + 全量绿为据,不冒称重新执行了历轮化学探针)。

## 6. mimo v15 请求与外送边界

- `docs/mimo_ppv1_chem_review_request.md` 升级 **v15(S3b-r3)**:
  0e.1 补入**后段锚定**表述(读取侧/传入比对侧/后段锚定三类
  拒因分栏:frozen_plan_integrity/missing/corrupt/digest_mismatch
  + frozen_plan_mismatch + frozen_plan_anchor_missing/
  anchor_corrupt/binding_mismatch;独立权威 = 根 retrieve 行;
  task_key 单一来源重算;先于 recover 补账/consume);同步 R2
  复审 §2/§5/§6 的精度更正(0c-v15:13 行为红+2 形态红的更正、
  52 绿口径、abstain 父红、行为/形态红早停内部到达精度、行号
  修正、audit.py:2980-2981 旧注释 P2 列冻结前处理、0d.8 一般
  followup B4 补齐函数指认(`runflow.py:500-558` 一般产物补齐 +
  `:577-615` 转换补齐)、novel 来源
  标签 P2 精度、"冻结计划 211-321"拆为 229-272(计划)/
  274-390(锚核对)/392 起(会话锁));判据一–五正文不变(无新
  化学机制,本批不改任何化学判定模块)。v14 送审快照(父提交
  2bedfc0 的字节)已存
  `docs/review_evidence/ppv1_s3_impl_2026-10-08/s3b_r3/mimo/
  mimo_ppv1_chem_review_request_v14_sent.md`;旧回应 r5–r14
  原样保留不回写。
- 本批实施 agent 未调用任何外部模型;请求由主会话按通道送审,
  回应落盘后按互证原则采信(评审独立性不做背书)。

## 7. 自查未闭合残留(诚实清单)

1. **判据未冻结、科学性能 pending**:全部数字为工程合成规则级
   契约结果,不代表 dev/298 科学性能;S4/S5 未启动。
2. **计划仍是合成/规则级输入**:后段锚定解决"恢复消费的输入
   身份"契约,不证明计划池真实检索质量(真实检索 provider 属
   后续阶段)。
3. **锚权威是同库 DB 行,不抗全库协同改写**:artifact+DB 行+
   身份文件被同时一致改写的攻击不在本门范围(复审 §4 明示);
   无密码学签名服务。
4. **执行层第二核仍是纵深防御**:`_run_retrieve`/`_run_decide`
   的 plan_digest/pool_digest 核验在正常流(入口锚已闭合)不可
   达,保持为防 DB 侧输入漂移的第二层;未单独构造运行期反例
   (不伪造可达性声明)。
5. **mimo v15 与 Codex 复审待跑**:由主会话按 AGENTS 自动循环
   接力;本批实施未联系审核方。Codex 复审前不宣布 S3 完成/
   判据冻结。
6. **继承 P2 边界不变**:同机 flock(跨机/分布式不在范围;
   driver.lock 披露文件在拒绝路径会被持有方重写,"零写"指业务
   账)、cache_hit 同构、两事务间外部 SQL 并发窗口、foreign-run
   反向诊断、三类 RuntimeError 逃逸面、B2 0event/1commit 口径、
   novel 来源标签 P2(expand 重建默认 synthetic-pool-spec,不称
   逐字全链一致)、stop 对象有界 100、三 RuntimeError 包装 ——
   均按 R2 §5 既定口径保持,本批未扩大也未倒退。
7. **G01 历史缺席依赖**逐项披露沿 r2 口径(证据 README §4);
   1481 不外推科学性能。审计侧 audit.py:2980-2981 旧注释与
   0c-v14.1 violated 落字的不一致是冻结前 P2 文本同步项(列
   冻结前处理,不改行为)。
8. **父基线行为红的"内部到达"**:父上 5 个负控的失败点均为
   "未发生结构化拒"(public resume 完整执行、注入转换/补账发生),
   不是早停在某个内部段 —— 分类 JSON 逐案记录。

## 8. 提交

- v4.3 本地提交(不 push;git add 仅显式路径):
  `src/pathway_v43/pollutant/runflow.py`、
  `src/pathway_v43/pollutant/profile.py`、
  `tests/test_ppv1_s3b_r3.py`、
  `docs/POLLUTANT_PATHWAY_S3B_DELIVERY_R3_2026-10-08.md`、
  `docs/mimo_ppv1_chem_review_request.md`、
  `docs/review_evidence/ppv1_s3_impl_2026-10-08/s3b_r3/`;
  提交哈希见 `git log -1`。既存 AGENTS.md 用户差异与旧未跟踪
  评审材料不纳入提交;production.py/store.py/search.py/queue.py/
  model_protocol.py/runner.py/s3b_worker.py 及全部既有测试未改
  不提交。父基线 worktree(/private/tmp/ppv1_s3b_r3_base_2bedfc)、
  G01 tmp(/private/tmp/ppv1_s3b_r3_g01)已清理;探针 tmp
  (/private/tmp/ppv1_s3b_r3_probe*)保留至复审(含二进制 SHA
  清单所指原始运行树;如需释放可随时删除,证据已快照)。
