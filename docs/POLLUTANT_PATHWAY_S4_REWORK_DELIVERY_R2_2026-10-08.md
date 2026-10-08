# pollutant_pathway_v1 S4 回修 r2 交付书(2026-10-08)

实施者:主会话按 AGENTS.md 评审-回修自动循环派出的一次性 S4 r2 实施
agent。回修范围 = 复审 R2(`docs/POLLUTANT_PATHWAY_S4_CODEX_REVIEW_R2_
2026-10-08.md`)§4 剩余两组 P1(S4-C02 / S4-C04)+ §5 P2 精度同步;
C01/C03、S3 与已证正控保持关闭,不加新科学门。实际开工 HEAD =
`0dd35d14d6539fbf134be18565f6709e852fc076`(= 直接父 = r1 提交)。
**S4 完成交接点仍不由本批宣布**——后续 mimo/Codex 复审由主会话接力,
本实施 agent 不调用任何外部模型、不联系审核方。

---

## 1. 入口矩阵(开工先立;每口登记必要集合/独立权威/版本身份/hash/
证明范围/合法缺席)

| 入口(源码锚) | 必要集合(应消费/应存在) | 独立权威 | 版本/身份/hash/证明范围 | 合法缺席 |
| --- | --- | --- | --- | --- |
| `build_native_result`(native_result.py:157;索引 :92) | index 全候选:ctx 上下文 / task_key 键 production_report+expansion_outcome / soutc(action_id) 键 outcome | store SQLite 行 + H07 artifact 信封 | native-result-2(沿 r1);content_digest 全量哈希;缺/坏 artifact 结构化拒 | 未完成动作候选、retrieve/decide 的 report 候选(生产链不写)、事件类提交 expand 的 outcome 候选 |
| `build_native_export`(= export_native_result,native_export.py:534) | **必要项** = 原生实际消费(payload 引用)+ 已完成 action/task/commit 行闭合 + 冻结计划锚;写前缺文件 ⇒ 先拒(:549–590) | DB 行 + payload + artifact store | **native-export-3 / native-export-policy-3**(本批升);manifest core digest = export_digest;策略正文+hash 双绑定 | B4 恢复 done expand 合法无 production_report;未完成动作全部候选 |
| `read_native_export`(native_export.py:657) | 同上必要集合 + 现存集合分别核(:901–933);payload 原生结果版本门(:775) | 同上 + endpoint 首消费先行 | 同上;八 kind 拒绝面保持 + 5b 版本门 | 同上;文件级读取缺 artifact ⇒ 每行拒 |
| `build_v3_projection`(v3_projection.py:387) | 经 `read_native_export` 完整首消费 + 传入 native = 导出 payload 整对象 | 导出文件 + ledger | **v3-projection-3**(本批升);projection_digest;adapter 派生内容同源 | ——(纯派生) |
| `read_v3_projection`(v3_projection.py:594;无 ledger) | `_load_bound_native_export`(:759)解析父 manifest/payload → **父来源版本门**(:680 `_verify_native_source_versions`,先于 adapter)→ 绑定比对 → adapter 同源复算 | 文件 + 共用登记源(profile 常量经 native_export 单一来源) | 同上;`v3_native_source_version_unknown` 拒;无 ledger 不核 DB 新鲜度(分工不变) | 坏 H07/重封已知版本假原生的无 ledger 个别观测按 R2 登记边界保持接受 |
| `read_v3_projection`(带 ledger) | 先走 `read_native_export` 完整原生首消费(含本批新版本门) | DB + 文件 | 同上;失败包装 `v3_projection_source_binding_mismatch` | 同上 |
| 公开 start/resume(runflow.py:1447/:1552;派生 :1347) | 全链:四分账 → native → export → projection → 双首消费读回 | 全部上述 | profile-18(本批升)/runflow-5/store-10 沿不变 | 派生失败结构化上抛,事件/预算零新增 |

## 2. S4-C02 修复:必要 artifact 集合不由"文件目前存在"决定

**改前行为**(复审 R2 §4 反例 single_ref_missing):`_necessary_
artifact_reference_keys` 以"读文件得到 envelope ⇒ 存在 ⇒ 必要"枚举,
`envelope is None` 一律 continue 当合法缺席 ⇒ 删已完成任务的
production_report 文件 + 删 manifest 同引用 + 自洽重算新 digest
(DB/native 均不改)后,`read_native_export(new_digest)` **接受**。

**改后行为**(native_export.py):
- `_necessary_artifact_reference_keys(ledger, payload)`(:252):必要性
  在读文件之前从 DB 行 + payload 判定(本函数零文件读写,不存在
  "文件存在反推必要"回路):① payload 的 audit_production_reports /
  expansion_outcomes / contexts 声明引用的每个键(**原生实际消费**,
  主反例捕获);② done + outcome 类提交的 soutc/task_key 键
  expansion_outcome(**先写后完成**的写路径不变量);③ 携带
  plan_digest 的 retrieve 锚行 ⇒ frozen_plan 应存在(S3B-01 同源)。
- `_existing_artifact_reference_keys`(:194):原存在性枚举拆出
  (合法缺席语义),损坏 artifact 仍结构化拒。
- 读取 step 9(:901):`omitted_necessary`(权威闭合必要项漏引用,
  带判定依据标签)/`omitted_existing`(现存项漏引用,旧语义保持)
  /`dangling` 分别披露,整集先结构化拒、零业务写、缺席形态保全。
- 写入侧 `export_native_result`(:549–590):封 manifest 前先核必要
  项文件存在与引用覆盖(缺失/漏引用 ⇒ `export_reference_mismatch`,
  check=necessary_artifact_reference_set_closure,零新导出目录)。
- **B4 合法边界**:`production.py _report("submitted")` 在
  complete_action 之后落盘,B4 恢复幂等补账合法不产报告 ⇒ 行闭合
  **不判** production_report(必要性只由 payload 实际消费决定);
  B4 恢复后的 done expand 无报告保持可导出/可读取(专项正控钉住,
  tests/test_ppv1_s4_rework_r2.py::test_c02_b4_...)。不做密码学签名、
  不抗全库协同改写(沿披露边界)。

## 3. S4-C04 修复:无 ledger 文件级投影首读核父来源版本

**改前行为**(复审 R2 §4 两最小案):`_load_bound_native_export` 核
自 hash/字节/reference/run/图摘要,但**不核**父 manifest schema/
contract_versions/native payload 版本 ⇒ 未知来源版本经自洽重封 +
新投影 reference 后,无 ledger 首读**接受**(有 ledger 拒)。

**改后行为**(v3_projection.py):
- `_verify_native_source_versions`(:680,`_load_bound_native_export`
  解析后、绑定比对与 adapter 解释**之前**调用):父 manifest
  `schema_version`、`contract_versions` 整组(整块缺失/逐键对当前
  登记源)、native payload `native_result_version`(缺失/未知)、
  投影自记 native_graph_revision 版本组与登记源重叠键冲突 ——
  分别入 `version_problems` ⇒ `v3_native_source_version_unknown`
  结构化拒;**共用登记源** = profile 常量经 native_export 的
  `_current_contract_versions`/版本常量(与有 ledger 首读/构建同一
  来源),不用当前 adapter 默猜迁移(历史版本无显式 adapter ⇒ 拒)。
- `read_native_export` 5b(:775):payload 原生结果版本门
  (export_version_unknown,check=payload_native_result_version_
  binding)——自洽重封换 native_result_version 不再只靠权威
  artifact 绑定兜底。
- **边界保持**:无 ledger 不强加 DB 新鲜度(no_ledger_h07 /
  no_ledger_resealed_source 的无 ledger 观测按 R2 裁定登记的文件级
  边界保持接受,逐字复跑验证);合法无/有 ledger 读取、有损 12 轴/
  空答卷、旧文件保全、零原生/业务写保持。

## 4. 版本登记(工程注册;判据冻结范围零触碰)

- `ppv1-native-export-2 → -3`、`ppv1-native-export-policy-2 → -3`
  (native_export.py;stale_detection 串更新,旧导出按 policy stale 拒)、
  `ppv1-v3-projection-2 → -3`(v3_projection.py)、
  `ppv1-profile-17 → -18`(profile.py 注册注释);endpoint-2/
  endpoint-policy-2/native-result-2/runflow-5/store-10 沿 r1 不变。
- 既有测试字面量 8 行(2 文件 3 用例):test_ppv1_s4b_export.py
  6 行(schema/policy/profile/projection×2/future-policy-3→-4)+
  test_ppv1_profile.py 2 行(断言+注释);future-policy 用例在父上
  仍绿(语义:未来版本 ≠ 当即拒)。**判据 ppv1-criteria-v1 冻结
  正文/记录逐字节零触碰**。

## 5. P2 精度同步(复审 R2 §5;不单独阻塞,本批全部落字)

| P2 项 | 处置 |
| --- | --- |
| 35 文件、19 红 = 11 缺拒绝+5 值+2 签名+1 字段、0 collection;9 字面量行/4 失败用例/72 控制绿(r1 口径) | 交付书/证据按此口径引用 r1 基线数字;本批 r2:36 文件(35+1 新)、11 红 = 7 拒绝缺失+1 字段+3 字面量、0 collection、8 字面量行/3 失败用例/41 控制绿,数字不是漏洞数 |
| 旧"零改动"限定测试字面量例外 | 0f.11/0g.12 增"限定:除逐批披露字面量"落字;交付书明确"951→962 不能全叫存量" |
| endpoint 实际变化与 criteria-v1 冻结范围分写 | 0h.6 缩回"判据一–五与 0d/0e 冻结范围",S4 契约族实际行为变化按契约版本号单列;0f.1 增必要条件阻断输入交叉引用;0i.6 声明限冻结范围 |
| mimo 第 63 条不是纯文字条件 | 0i.4 明确按程序实证采信为 P1 消费规则(C02 主反例即其实证);不按纯文字条件结案 |

## 6. 新增回归与控制清单(tests/test_ppv1_s4_rework_r2.py,11 用例)

**负控(修后必须拒;父上行为红)**:
1. C02 三变体(参数化):仅删引用(文件在,父上已拒 → 字段红)/
   文件改坏+删引用(枚举侧 H07 拒)/ **文件+引用同删+自洽新 digest
   (主反例,父上接受 → 翻转拒)**;每案断言必要性独立证据
   (done expand+event 提交+payload 消费同 task)、零 DB 写
   (17 表内容哈希前后)、原 payload/native 权威字节不变、缺席
   形态保全、还原正控。
2. C02 写入侧守卫:done outcome soutc 文件缺席 ⇒ export_native_
   result 先拒(零新导出目录/零业务写/还原幂等)。
3. C04 四个未知/缺失来源版本案(参数化:unknown_export_schema/
   unknown_contract_profile/unknown_native_result/missing_native_
   result):无 ledger 拒(v3_native_source_version_unknown,逐案
   expected_problem)+ 有 ledger 拒(包装原生首消费)+ 原生读取拒
   + payload 其余字节/DB/steps 不变 + 原文件保全。
4. C04 版本组:contract_versions 整块缺失拒;投影自记版本组冲突拒
   (projection_contract_versions:profile)。

**正控(修后必须保持;父上绿)**:
1. B4 崩溃(事件已提交未结账)→ resume 补账:done expand **无**
   production_report ⇒ 导出/投影读取照常(合法未生产保持)。
2. 合法无/有 ledger 投影读取同值;12+ 损失轴;空池(零事件)
   空答卷 + no_committed_events 轴;投影读取零业务写。
(既有 s4a/s4b/r1 控制全部保持:全量 1573 绿。)

## 7. 执行数字(隔离源 fresh tmp;合成规则级,不外推 dev/298)

| 执行 | 结果 |
| --- | --- |
| PPV1 全量(隔离源,36 文件) | **962 passed / 0 skipped / 0 failed,exit 0**(951 r1 存量 + 11 新) |
| S4 焦点 | **83 passed,exit 0**(11+19+35+18) |
| 全量非 slow(隔离源,G01 同口径 deselect) | **1564 / 8 / 17,exit 0**(首跑 7 失败 = 准备事故 prep-1:dependingv3 副本缺 assets,补拷后单次重跑;首败输出保留) |
| 全量非 slow(仓内树,不 deselect) | 1573 / 16,exit 0 |
| G01 安全隔离(296 输入 = 295 r1 + 1 新;控制器谱系 R7→…→s4_rework_r1→r2) | **1564 / 8 / 17,exit 0**;执行后对仓源逐文件 SHA 复核 **0 失配**;8 skip 逐 nodeid(5 真实冻结评价 + 1 缺 v4 + 2 phase_d;缺席不当作通过)+ 16 slow + 1 显式 deselect |
| 直接父 0dd35d1 同字节(detached 稀疏 worktree,3 份测试文件 SHA 相等) | **11 红 = 7 拒绝缺失行为红 + 1 字段红(intact 变体:父上 r1 闭合已拒,缺 r2 新增 necessary_basis 字段)+ 3 版本字面量红;0 collection**;41 合法绿 |
| legacy 字节专项(两树各 2 run × 2 产物;probe 逐字复本 SHA 相等) | **4/4 逐字节一致**;52 非 pollutant src 文件 code_identity 聚合两树一致(2b32c86e…,本探针自有计法;`git diff 0dd35d1 -- src` 仅 3 个 pollutant 文件为旁证) |
| R2 反例逐字复跑(independent_cases.py 复制 fresh tmp;5 脚本 SHA 与永久证据逐字相等) | single_ref_missing 自洽重封读取 **ACCEPTED→REFUSED**;unknown_export_schema/contract_profile/native_result 无 ledger 首读 **ACCEPTED→REFUSED**;no_ledger_h07/no_ledger_resealed_source 按登记边界保持 ACCEPTED;全部用例零 DB 写;public_controls 正控全绿(网络 0);旧确认探针按 r1 已闭合缺口预期早停(未执行段单列) |

## 8. 诚实残留(未闭合/边界,如实列出)

1. **全库协同改写不在范围**:C02/C04 闭合均为单文件/单 manifest/
   文件+引用联合变体;DB+artifact+manifest 全部自洽重写仍不能被
   文件级核验区分(沿 S3B-01/S4a 披露边界,复审 R2 §4 明示豁免外)。
2. **无 ledger 文件级分工边界**(复审 R2 正式裁定按登记接受):
   坏 H07 来源与重封已知版本假原生在无 ledger 投影读取下仍接受
   (版本门只覆盖来源版本登记,不替代 DB/权威 artifact 新鲜度);
   有 ledger 路径均拒。
3. **production_report 必要性单边依赖 payload 消费闭合**:B4 恢复
   合法无报告 ⇒ 行闭合不判 report;构建时(导出前)删除已完成
   expand 的报告且 manifest/payload 均未消费过它的形态,属 payload
   构建时缺席(与 B4 合法形态不可区分,不加新门);导出后删除的
   主反例形态已闭合。soutc/task_key outcome 因写路径先写后完成,
   行闭合覆盖构建时缺席。
4. **24 字符目录名截断、endpoint 先消费后的拒绝优先级、H07 信封
   与内容身份分层、multi-reactant 公共生产分支未由公共链夹具覆盖、
   stop 视图会话成分**:沿 r1 披露,本批不追加机制/性能验收。
5. 准备事故 2 起(缺 assets 的 7 失败/复跑目录预建冲突)已如实
   登记(metadata/preparation_incidents.json),单次修正重跑,
   不改产品/断言;G01 树内既有非 PPV1 子进程 pyc 副作用沿 r1 登记。

## 9. 边界声明

legacy/export_v3/G2/AtomTool/production.py 零触碰(两树字节专项 +
code identity 互证);全部 scripted/off 规则级夹具、model_requests 0、
网络 0、判分零 LLM;金标/题面/封存逐题 run/dependingv4/冻结 v3 评价
资产一律未访问(G01 白名单沿 r1 谱系;评审脚本复跑 V3_CODE_ROOT 指
向空目录);dev 与 298 题域双向不外推;S5 未启动;mimo v19 请求
(自包含、规则级、合成例,无金标/题面)已落盘,由用户送审;
旧报告/旧证据/旧 manifest 只读未回写。

## 10. 交付物与提交

- 交付书:本文件。
- mimo 请求:`docs/mimo_ppv1_chem_review_request.md`(v19 新增 0i 节
  + P2 同步落字;送审快照字节存证据包 mimo/)。
- 证据:`docs/review_evidence/ppv1_s4_impl_2026-10-08/s4_rework_r2/`
  (README + manifest.json + SHA256SUMS;current/baseline/g01/legacy/
  review_rerun/scripts/metadata/mimo)。
- 代码:src/pathway_v43/pollutant/{native_export,v3_projection,profile}
  .py;tests/{test_ppv1_s4_rework_r2.py,test_ppv1_s4b_export.py,
  test_ppv1_profile.py}。
- 本地显式路径提交(不 push;Codex 报告/回应/旧证据不代为提交):
  提交在本证据归档后创建,哈希由主会话以 `git log -1` 核对记录。
