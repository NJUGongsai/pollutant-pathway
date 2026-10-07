# S3a 回修 r3 实施证据(ppv1_s3_impl_2026-10-07/s3a_r3)

日期:2026-10-07,Asia/Shanghai。固定仓库 `/Volumes/CC/Enzyme_Agent/dependingv43`,
实施前 HEAD(直接父基线)`dcb7ed62bd4271cfa7bde2732dc0b4fdd0360d03`
(v4.3 分支)。本目录为 **S3a 回修第三轮(r3)实施方证据**:Codex
S3a 复审 R2 残余三组 P1(S3A-02/03/04)的修复、回归与红绿对照。
复审报告:`docs/POLLUTANT_PATHWAY_S3A_CODEX_REVIEW_R2_2026-10-07.md`
(只读;其永久证据 `ppv1_s3a_codex_r2_2026-10-07/` 未在本轮回修中
原地执行任何探针,控制器脚本按复审证据 README 的纪律复制到新 tmp
适配后使用)。

## 1. 范围与完成/未完成

- **已完成**:S3A-02(预约单位/状态/scope-subject/主体共享
  alternatives、attempt 状态/hypothesis/task 的行级内容核验,提交
  记录归属/kind/适用 attempt 引用,done 四入口与 first complete/B4
  一致消费;附随投影/计划按首提同一判据只读内容核验;B3 事件提交
  前引用前置;done submit 返回真实已完成 event 或明确冲突)、
  S3A-03(register 落账完整装配块;读取/恢复/预算/认领/请求消费先
  严格核冻结块,null/缺版本/坏值消费前结构化拒、零执行预约)、
  S3A-04(请求已有 row 复用对照 stored 与 incoming 全部身份列;状态
  口核 run 绑定与 expand 必要 attempt;恢复 pending 逐行同源守卫、
  坏引用结构化披露不伪装普通合法 pending)。
- **未做(不冒充)**:S3b 全部;runner 双入口对 PPV1 继续
  fail-closed;外部 exactly-once;机制库;科学性能门;判据冻结;
  并发窗口收口(两个事务间未持锁按登记边界披露,不以未证支持的外
  部破坏模型增阶段门)。
- **契约影响**:search ppv1-search-2 → ppv1-search-3;profile -10 →
  -11;store 保持 -9(新增只读 verify_event_attachment_content 共享
  判据入口);search-limits 保持 -3;legacy code_identity 聚合不变
  (见 `meta/runtime.txt`)。

## 2. 实际执行与数字(全部 depending43 Python 3.11.16 / RDKit
2026.03.6 / SQLite 3.53.4,`-B` + `PYTHONDONTWRITEBYTECODE=1` +
`-p no:cacheprovider`;每目录 `run_meta.json` 记录实际 argv/env/
exit/junit 耗时)

| 执行 | 数字 | 证据 |
| --- | --- | --- |
| 当前源 PPV1 全量(25 文件) | **697 passed / 0 skipped / 0 failed**,exit 0 | `current/ppv1_full/` |
| r3 新回归(1 文件 49 项) | **49 passed**,exit 0 | `current/rework_r3/` |
| 四崩溃/H06 双进程/零预算/悬空请求矩阵(自审复跑) | **23 passed**,exit 0 | `current/crash_barrier_budget/` |
| 直接父基线 dcb7ed6 detached worktree 同字节新回归 | **40 failed / 9 passed**,exit 1 | `baseline/rework_r3/`(junit+stdout+failed_nodeids+failure_classification) |
| 同基线更新的既有测试(profile 副本) | **1 failed / 22 passed**(1 版本红:ppv1-profile-11 断言;无行为红) | `baseline/updated_existing/` |
| G01 安全隔离(R7 白名单 + R8/S3a/r2/r3 输入,276 项) | **1299 passed / 8 skipped / 17 deselected**,exit 0,pytest 194.18s / 控制器 195.649s | `g01/`(preparation/execution_result/junit/stdout/stderr/input_sha256 + 控制器 stdout/stderr) |

基线 40 红分类(`baseline/rework_r3/failure_classification.json`):
全部为**行为断言失败** —— 28 "预期结构化拒绝未发生"(Integrity)、
3 "预期契约拒绝未发生"(Contract)、2 Recovery、2 IdentityConflict、
5 断言值不符(B3 两案 = 基线先写 event=1 再拒,即复审 §4.1 第 4 项
消费顺序缺口;pending 两案 = 缺结构化披露;partial 注册两案 = 存
储块 2 键而非 11 键)。**无 collection 红、无返回形态 TypeError、
无错误 kind 先停导致内部未执行**;9 基线绿 = 3 首提同源判据对照 +
4 合法正控 + 1 r2 已闭合的越界读拒(保持控制)+ 1 r2 单口已拒的
commit.run-recover 对照(r2 经 run 过滤报 done_without_commit_
record,r3 起四口一致拒)。基线同字节输入哈希双向核对:
`baseline/test_input_hashes.txt`。

G01 8 skip 逐 nodeid 与 17 deselect 明细见 `g01/preparation.json` /
`g01/execution_result.json`(skip_lines)与交付书 §3;R7 1110/8/17、
R8 1138/8/17、S3a 首批 1196/8/17、r2 1250/8/17 各自单列不混计;
工程数字不外推 dev/298 科学性能。G01 只在仓外新 tmp
`/tmp/s3a_r3_g01_out_run` 执行(276 项输入 SHA 前后一致,
`g01/input_sha256.json`);不读取 evaluation/金标/题面/封存逐题
run/dependingv4;无 provider 调用、无判分 LLM、无网络请求
(scripted network_request_count 恒 0)。

## 3. mimo

- v11 送审快照:`mimo/mimo_ppv1_chem_review_request_v11_sent.md`
  (替换前 v10 原文保留为 `docs/mimo_ppv1_chem_review_request_v10_
  sent.md`;旧回应 r5–r10 在 `docs/` 原样保留)。v11 自包含内联全部
  规则文本;复审 R2 §6 的规则文字修订(判据一 2b 内因读法/判据二
  known_absent 实际语义与系数句/判据三恒入复用分写/判据四孤儿方向
  更正、入口限定、重建半边)与 mimo v10 回应事实纠错(0c 不采信
  清单:RDKit 2026.03.6、AuditContractError 抛点全在 audit.py、虚构
  分支名等)均落字;**未把虚构供体分支/错误 RDKit/错误异常处置
  照搬为事实**;**由主会话送审,实施 agent 未调用任何外部模型**。

## 4. 输入与完整性

- 基线 worktree:detached dcb7ed6,同字节测试输入
  `tests/test_ppv1_s3a_rework_r3.py`(只用 r2 已存在公开 API,基线
  可收集;profile 副本 `test_ppv1_profile_r3.py` 为仓内同字节拷贝,
  跑后删除);建立/清理记录 `meta/worktree_add.txt`、
  `meta/worktree_before_remove.txt`、`meta/worktree_remove.log`
  (清理用 --force 仅因副本为未跟踪的同字节测试输入,主仓未动);
- 实际 HEAD/父/dirty:`meta/head_status.txt`;运行时版本与契约与
  legacy code_identity:`meta/runtime.txt`;
- 本目录不含任何运行 SQLite/pytest cache/字节码/真实敏感数据;
  全部合成输入(CCO → CC=O 规则级夹具);所有执行在仓外新 tmp,
  不在永久证据原地写库;
- G01 控制器脚本:`scripts/safe_g01_s3a_r3.py`(适配 r2 控制器,
  追加 r3 测试输入到白名单;复制到新 tmp 使用,未在永久目录执行);
- manifest.json 与 SHA256SUMS 覆盖全部附件(README/manifest 本身
  不自我 hash;SHA256SUMS 额外校验 manifest 本身)。

## 5. 异常/准备修正

无:全部执行第一遍完成,无超时重试、无源码/断言修补;基线 40 红
全部为预期行为红(坏案在修前基线被错误接受或错误披露);G01 输出
目录为全新 tmp,控制器拒绝已有输出目录(第一次调用因输出目录尚
未创建前的 shell 重定向路径不存在而立即失败,未进入任何执行;随后
创建目录并完整执行一遍,controller_stderr 为空)。
