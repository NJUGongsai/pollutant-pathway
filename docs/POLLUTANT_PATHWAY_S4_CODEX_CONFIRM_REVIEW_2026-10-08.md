# pollutant_pathway_v1 S4（S4a＋S4b）正链确认复核

日期：2026-10-08（Asia/Shanghai）。

**正链裁定：不确认 S4 通过。P1＝[S4-C01, S4-C02, S4-C03, S4-C04]。备用通道的执行数字与本审互证，但两份放行建议的验收覆盖不足；完整 S4 完成交接点尚不成立，不交接 S5。**

本结论没有重开 S3，也没有追加科学性能、机制认证或真实来源认证门。四组反例均落在原 S4 任务书的 F02、全量事实保留、G02 完整性和原生→投影消费契约内。

## 1. 身份、固定验收与执行纪律

- 身份：本次 ChatGPT/Codex 正链会话及其三个专项子代理实际取证；不是 opencode/tokeasy 备用通道报告。会话 UUID 未由工具提供，不编造。
- 待审实际 HEAD：`8735601b75825388fe9f4a177a1131ef264054a1`；直接父：`fc40605819201ae4a7101fc500b19083d78383b0`。
- S4a 源码基线：`adf0287abef0c4803962fee0df0065d8e6f3793d`；文档入库提交 `0e345e83de27e7369334fe092da7a6ccbc8afd6c` 不改变该基线的 src/tests。S4a 实施为 fc40605；S4b 为本 HEAD。
- 实际任务书：`/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S4_IMPLEMENTATION_TASK_2026-10-08.md`。派单中的 2026-10-07 路径不存在，使用仓内实际文件，备用 S4b 报告也已登记同一更正。
- 验收：该任务书 §2.B/§2.C/§2.D、§4.1–§4.5、§5、§7–§9；两交付书与两备用报告；mimo r16/r17；冻结稿及冻结记录；备用审核协议。只确认核心主张，不冒称逐份复跑所有历史探针。
- 全部运行在新 `/private/tmp` 隔离树，源码含 vendor 和必要 metadata；depending43，Python 3.11.16、RDKit 2026.03.6、SQLite 3.53.4；`-B`、禁字节码和 pytest cache。完整输入、命令、环境、输出、独立采集退出码/JUnit 与逐案权威效果见本证据；终点首7案的初始 shell 未独立记录子进程 exit，该局限与只读 oracle 后补实际 exit 明示于专项 README，不伪造退出元数据。
- 未访问真实金标、题面、封存逐题 run、dependingv4 或原 v3 资产；安全 G01 仅读取既定普通源码/准入资产白名单；真实 provider/网络请求为 0，判分零 LLM，未调用外部模型，未 push/commit。
- 本仓只新增本报告及 `docs/review_evidence/ppv1_s4_confirm_codex_2026-10-08/`。旧报告、证据、AGENTS、src/tests 不回写。

本轮没有账号限额中断。准备错误与更正如实保留：第一次全量因隔离父/子进程空 v3 根不一致，得到 914 passed/18 failed；失败是 `v3_engine_code` 身份环境不一致，不采信为产品回退。仅修隔离环境、保留源码/测试/期待，唯一重试取得正式 932/0。根窗口首个旧 SHA 清单解析器误拒绝绝对路径，随后只允许规范化到原证据根内部，未影响产品运行。专项首探针因“预期全部 soutc 已聚合”的断言早停，原失败保留；后续观测版与独立分案补证分别记录，不把未到达段算通过。

## 2. 独立执行数字与父基线分类

| 项目 | 本审实际结果 | 证据口径 |
| --- | --- | --- |
| 当前 PPV1 全量 | **932 passed / 0 skipped / 0 failed** | 34 个 `test_ppv1*.py`；正式唯一有效全量，工程规则级 |
| 当前 G01 安全隔离 | **1534 passed / 8 skipped / 17 deselected** | **294** 输入逐 SHA，执行前后一致；实际 pytest 原始日志/JUnit |
| S4a 新文件在 adf0287 | **1 个 collection/import error，35 个用例体未执行** | 父缺 endpoint 模块；不是 35 个行为失败 |
| S4a 同批 profile 在 adf0287 | **2 个版本/阶段字面量红＋21 passed** | 同字节测试；0 个已证行为红 |
| S4b 新文件在 fc40605 | **1 个 collection/import error，18 个用例体未执行** | 父缺 native_export 模块；不是 18 个行为失败 |
| S4b 同批 profile 在 fc40605 | **2 个版本/阶段字面量红＋21 passed** | 同字节测试；0 个已证行为红 |
| S4b 导出焦点 | **18 passed** | 已包含在 932 中，不能相加 |
| 终点独立公共场景 | **12 案** | 7 条需求/依赖 start＋resume＋完整消费，5 个边界 start＋消费；socket connect 0 |
| 终点边界／观察 oracle | **5/5 边界控制；2 failed＋3 passed 观察断言** | 两红是同一 S4-C01 的两个 unknown 输入；只读既捕获结果，未重跑搜索，不与全量相加 |
| legacy 字节专项 | **4/4 产物当前/父字节一致** | 两个合成 legacy run 的 predictions.jsonl/export_metadata.json；本审实际执行 |
| legacy code_identity | **52/52 文件一致** | 聚合 `18007e6a7cc239606eb30921f91045540446a7d7298108be30d47fce2f1374d6` |

G01 缺席和排除逐 nodeid＋理由保存在 `execution/g01_dependency_disclosure.json`：真实冻结评价 5（batch/score）、缺 v4 对照 1、缺 phase-d provenance/summary 2；16 slow＋明确排除 `tests/test_export_v3.py::test_charge_fixture_cn_hits_raw_sb_misses_neutralization_forbidden` 1。没有复制敏感依赖来补数字。本轮 1534 与 S4a 历史 1516、S3 历史数字分开登记。

数字证明相应工程测试执行，不证明污染物路径、矿化比例、酶活性或 dev/298 科学性能。专项反例是规则级合成输入，不使用真实考卷或标准答案。

## 3. 六项放行主张的确认矩阵

| 原放行主张 | 本审裁定 | 独立互证与限度 |
| --- | --- | --- |
| 冻结稿零触碰、新模块不生成 state_id | **确认此项** | FROZEN_V1 与冻结入库 0e345e8 同字节；adf0287 尚无此文件。新 endpoint/native_result/native_export/v3_projection 只消费/派生；runflow 仍调用既有化学链，未新增身份算法。冻结文本不变不等于 S4 实现正确 |
| legacy/export_v3 不变 | **确认此项** | 核源码字节及本审实际四产物对照；补足备用 S4b 仅采信交付专项的范围 |
| G02 文件级确定性、stale/篡改拒 | **部分成立，不足放行** | 同进程＋独立子进程 payload/manifest 逐字节、恢复正控和原有七测成立；manifest 自身绑定与必要引用集合有 S4-C02 |
| soutc 两键聚合修复完整 | **不确认完整性** | 非空 task_key 的两键修复成立；空 task_key 的 child retrieve 被提前 continue，见 S4-C03 |
| F01/F02/F03 与终点边界 | **部分成立，不足放行** | 停止不当终点、重复来源去重、未解决 Dependency 正控/负控及 CO₂ 不相加保持；必要 condition requirement 的 unknown 被漏掉，见 S4-C01 |
| start/resume→endpoint→导出→投影→读取完整公共链 | **正常链已执行，异常边界未闭合** | 正常、恢复、重复生成及读取实际到达，业务计数不重复；投影可混搭原生来源并读回错误摘要，见 S4-C04 |

S3、S3a 已关闭项保持关闭。化学生产链、AuditContractError 义务及既有身份/恢复守卫未由本批改写；通过源码字节、全量回归和相应公共链收口，不宣称本轮跑遍全部历史永久脚本。`production.py` SHA 为 `3b1a66ea2bc3aa37f7caaa2ed1a7f5395cda5901ef2a03d765b932ee5b082262`。

## 4. 四组 P1：具体反例与最低收口

### S4-C01：必要条件未知未进入终点阻断，错误授 supported_mineralization

**原验收：**任务书 §4.2 F02 明确包括“条件未知、环境事实未闭合”，§4.5 缺必要条件保持 unknown；§8 终点条件/依赖与失败状态；不是新增现实来源认证门。

**公开反例：**沿原合法 `spec`＋充分 `mineralization_evidence` 夹具，只引入有来源的 essential `oxygen_regime=aerobic` requirement，分别令当前事实缺失、显式 unknown。两例 `start_run` 都提交 1 event；持久 `load_context(...).route_assessment()` 明确 `unknown_keys=[oxygen_regime]`。但 start/resume 的 endpoint 都为 `supported_mineralization`，inherited unresolved 计数为 0；`read_native_export` 全文和 v3 摘要仍是同值，未拒。

这里的 `supported_mineralization` 是来源层声明等级，不是本仓实测；错误是把当前路线已经持久记录的必要条件未知丢掉后授予该等级。充分来源声明保留，不应因此删证据或把所有未核维度统统判负。

**合法/诚实控制：**同一证据＋已知 aerobic/支持的 NAD 依赖保留 supported；缺启动 NAD 的必要 Dependency 正确保留 unknown。已知 anaerobic 冲突、event=0 仍 supported 另作补充观察；本组最低阻塞锚是上述两例 event=1 的 unknown，不仅凭“零事件”否定独立来源观测。

**代码：**`endpoint.py:298` 仅遍历 `context.dependencies`；`:343` 条件快照只采事实；`:461` `_assess_endpoint` 只消费 inherited dependencies；`:739–743` 没有消费已存在的 requirements/history 条件评估。未把当前必要条件 unknown 接进共同阻断和派生输入身份。

**最低修复/验收：**共用历史同源条件评估，分开来源观测声明与当前路线的适用性；必要 unknown/unresolved/conflict 不能被 recorded 或充分证据字段洗白。覆盖 derive、首读/consume、start/resume、native 导出与 v3 摘要；保留来源证据全文、conditions/proof scope 及失败原因，已知兼容正控保持 supported，不要求解析自由文本成完整科学证明。派生与读取须消费同一必要条件集合及其内容摘要；历史旧边不得用当前事实重评后洗白。

证据：`endpoint_contract/cases/requirements_and_dependencies.json`（7个独立公共 start/resume 输入/全表）、`endpoint_contract/logs/endpoint_readback.json`（只读历史条件及 endpoint/native/v3 全文）；另5个边界场景在 `endpoint_contract/cases/endpoint_boundary_controls.json`。

### S4-C02：manifest 未绑定自身内容，必要权威引用可被删后绕过首消费

**原验收：**任务书 §2.B“manifest 或引用内容 hash 不一致/依赖对象内容变化/产出与当前权威不匹配”、§4.4 G02 ⑥⑦、§5.1、§8 导出完整性；不是要求抗全库协同改写。

**反例 A：**在合法公共 start 产物中，分别仅改 manifest 的 run_id、profile 契约版本、export_policy 正文、artifact_references。保持原 export_digest，请求原 digest。四例 `content_hash(manifest_core)` 已与声明不符，`read_native_export` 仍全部接受。DB、真实 native payload 和 artifact 权威均不改。

**反例 B（独立验证必要集合）：**只删唯一 production_report 引用，其他引用保留；按设计正确重算 manifest core/export_digest，复制原 payload 到新 digest 目录，再只损坏该 production_report 的 H07 内容。原导出读取按 `artifact_hash_mismatch` 正确拒；自洽重封的新导出接受。所有业务表、原 native artifact 和 payload 字节零改，损坏 artifact 保全。全删引用的复合案也记录，但最低收口以单项必要引用案为准。还原 artifact 后原导出正常读回。

**代码：**`native_export.py:382–393` 只对 manifest.export_digest 与请求字面值；`:421` 重算的是 payload 内容，没有重算 manifest core；`:480` 仅遍历 manifest 自报的 artifact 集合；`:498–505` 比较策略 hash 字段，不验证正文与该 hash 的绑定。自包含重封装和缺项集合都没有由独立权威收口。

**最低修复/验收：**manifest core 复算与 requested/recorded digest 同时绑定，run/版本/策略内容及 hash 共用登记源；必要 artifact 引用集合从该原生结果实际消费、依既有 action/task 与冻结计划登记源应引用的 artifact 同源列举后比对，不能仅遍历清单自报项。分别核完整集合与每行有效；覆盖普通 manifest-only 篡改、自洽换新 digest＋单项/全部引用遗漏＋坏/缺 artifact；先拒、零业务写、原文件保全。原有八 kind、正常导出、幂等和合法空池保持。此修复不需要额外 artifact 体系、签名、分布式存储或抗全库共同改写。

证据：`export_chain/observed/results.json`、`export_chain/observed_supplemental/results.json`；原始输入/文件/前后表另存相应 cases。

### S4-C03：空 task_key 的下游 soutc 仍漏聚，unknown 结论及其权威校验一起丢失

**原验收：**任务书 §2.B 全量事实和失败/unknown 原因、§4.1 未解决 continuation 保留、§8 原生完整导出；派单核心主张④的两键聚合，不重开 S3 搜索算法。

**公开反例：**公共 start 的下游 child retrieve 合法 `task_key=''`，但 `_complete_action` 已以 `stable_id('soutc', action_id)` 写 `no_local_candidate`/`unresolved_continuation=True`。实际四份 soutc 中只聚合根 retrieve/decide 两份，另两份 child retrieve 没有进入 native `expansion_outcomes`，也没有进入正式 manifest 的 artifact_references。

**首消费补强：**仅损坏其中一份已漏聚的 child soutc，不改 DB、native/export 文件或 manifest。直接 H07 读取正确拒；公开 `build_native_result` 与 `read_native_export` 仍接受，所有表零变化。这个缺口在正常合法搜索中已经丢事实，不依赖恶意重封 manifest。

**代码：**`native_result.py:123–125` 空 task_key 时提前 continue，位于 `:137` 独立 soutc 键的枚举之前；共享索引让 build 和 manifest 同时漏掉。非空键修复有效，但不能称“两个实际写入口全部覆盖”。

**最低修复/验收：**按 action_id 枚举 soutc 不依赖 action.task_key 非空；原 task_key 的生产报告/结论仅在键合法时列举，缺键不能生成空键引用。覆盖同一规则适用的 retrieve/decide/activate/transition/expand，保留合法缺席和去重；下游有/无 task_key、共同产物/备选、未解决 continuation 正控均保留全文并纳入权威引用。坏必要 soutc 首消费先拒、不静默略过。S4-C02 与本组须使用同一完整索引，不各修一套规则。

证据：`export_chain/` 的第一失败原日志、观测版真实 soutc/index/native 快照以及 `observed_supplemental/results.json::missing_outcome`。

### S4-C04：v3 投影只核原生 manifest 存在，可把错误内容挂到真实原生引用

**原验收：**任务书 §2.C 原生→有损适配、原生引用及不可投影摘要/引用，§5.1 v3 首消费验证父对象、§8 失败与原生完整事实；不是要求 v3 无损，也不是新增反向写入功能。

**公开反例 A：**先 `read_native_export` 正确消费真实原生结果（1 event、1 deferred）。复制 native 对象，删 events/deferred 并正确重算 content_digest；用真 native_export 返回值公开 `build_v3_projection→persist_v3_projection→read_v3_projection`。全链接受，steps=0、deferred_count=0，而投影 content_digest/task_key 与真实 manifest 指向对象不符。

**反例 B（不靠构建者裸对象）：**仅改 projection 文件的 steps/deferred 摘要并重算 projection_digest、新目录，所有 native_reference 三类身份/字节引用都保持真实原值。读投影仍接受；前后原生 `read_native_export` 都正确通过；native payload/manifest/DB 完全不变。说明先读原生并不能代替投影与该原生的内容绑定。

**代码：**`v3_projection.py:253–323` 构建直接信调用方 native_result；`:458–488` 读取只核投影自 hash、版本、lossy 标记和原生 manifest 文件存在，没有对照 content_digest/task_key/payload_sha 或投影内容。原生“存在”不是该投影来源证书。

**最低修复/验收：**构建与首消费共用原生消费/绑定源，核 reference 内部一致及其对应的已验证原生 manifest/payload；投影的已表达字段和不可投影摘要必须由该原生对象按登记 adapter 同源确定性生成/复算，不能自洽换新 ID 后照收。可调整消费 API 明示 ledger/已验证原生输入及版本；不得仍把“只列文件/只检查存在”的发现接口叫完整授信入口。覆盖混搭 digest/task_key/sha、裸 native 改坏、投影-only 自洽删/增事实；保留正常单底物、真实空池空答卷、固定12轴、有损边界、反向消费禁止、零原生写、只读反查。无需补多 reactant 公共生产功能。

证据：`export_chain/observed/results.json::projection_binding`、`observed_supplemental/results.json::projection_only`；真实来源及原/伪投影完整输入均归档。

## 5. 已披露边界与 P2 的裁定

继续接受：来源层 endpoint 证据为合成冻结计划声明，未认证真实性；bookkeeping 仅声明范围闭合，CO₂ 逐事件/备选不相加，不推导解毒/永久去除；同机 flock 非分布式；cache_hit 同构、外部 SQL 两事务窗口、foreign-run 诊断、stop 对象有界、已登记 RuntimeError 面、来源标签精度等既有 P2 不凭本轮假设升级。

S4 新边界如实成立：相邻会话 stop 视图可能变化而新 digest 合法生成；结算后重复导出稳定，旧文件保全，业务计数不重复；目录取 digest 前24字符但完整值保留；多 reactant collapse 分支未由生产夹具动态覆盖，读码披露不冒称执行；行号锚随工程漂移，冻结正文未改；v3 字段为有损结构视图，消费者必须读 losses，不得独立称矿化/去除/解毒或另算一条路径。

**不能用“协同改写范围外”包住本轮 P1：**S4-C02 仅动 manifest 与一项 artifact，不改 DB/native 权威；S4-C03 直接正常公共链丢现有事实；S4-C04 只动投影或构建输入，真原生不动；S4-C01 使用合法规则夹具便可授错误 endpoint。它们都在已定消费边界内。

文档 P2：任务书早期“判据未冻结”字样与后续用户冻结记录时点不同，应在后续交付解释，不回写冻结历史；两批“879/914存量零改动”应明确除 profile 版本/阶段字面量；拒绝优先级区分 endpoint 先行与导出八 kind；24字符目录命名、多 reactant 未覆盖、stop 副本与独立权威、H07/上下文身份分层继续明确。

## 6. 备用报告质量与 mimo 互证

### 6.1 数字可互证，放行覆盖不充分

- 备用 S4a 的 914、1516 与 S4b 的 932、1534 是各批口径。本审独立确认当前 932、1534/8/17/294；父 collection＋版本字面量分类方向相符。备用通道没有把 legacy 专项冒充自身执行，S4b 明示依交付证据，属于诚实范围披露；本审补做实际字节专项。
- 原证据 SHA 清单逐项一致：S4a 46 条、其 manifest 44 条；S4b 21 条、附件快照 manifest 20 条，均无 hash 漂移。本审只读校验，没有修改旧目录。
- 归档质量不足：S4a 有5份JUnit，但两次准备失败仅保留各87字节说明，不能称完整原始失败日志；S4b 没有JUnit，归档 G01 stdout 为控制器JSON，`g01_execution_result.json` 指向的实际 pytest stdout 没有随包保存；部分其他命令/exit/环境及无效父准备原日志缺席，README 也未纳入 SHA 清单。绝对 SHA 路径降低可移植性。本轮重新执行并完整归档，补证而不修写原包。这些是证据可审计性 P2，不凭环境/附件缺失制造产品 P1。
- 主要不足是验收覆盖：重复执行实施方焦点和全量用例，可以证成这些用例，不能证明同规则所有消费入口闭合。原条件冲突测试没有充分 endpoint 证据，预期 unknown 因“无证据”即成立，不能证明必要条件真的阻断充分声明；soutc 修复只读到双键没检查空键公共链；manifest 负控只覆盖已测形态没核自身 core/必要集合；v3 只验引用存在没核来源内容。四组新增公共反例推翻的是这几项全称及 P1=[] 放行建议，不是否定其全部工作或数字真实性。

### 6.2 mimo 只读意见不替代本轮执行

mimo r16/r17 的执行类数字、字节/哈希与 G02 声明继续按待执行处理。用户摘要“全同意级”须精确化：r16 对部分 0f 现描述含“不同意”，包括 0f.11 其中一句，整体 A1–A6 是文案精度更正；r17 的多个 0f/0g 项为有条件同意，核心是文本自修，不要求新化学门。本审当前 r17 的9组行号/源码抽查与冻结字节互证见 `endpoint_contract/` 专项清单；r16 行号须按其 S4a HEAD 看，不能误当当前行号；正确读码、漂移锚与未核项分别登记。

保留修整项：stop 语义副本与独立权威分写；endpoint self-hash 协同改写范围；H07/内容身份分层；六原因/七场景精度；S4a 实际父0e345e8与源码基线adf分写；0g目录 `digest[:24]`；endpoint首消费优先；多 reactant 未覆盖；879/914存量字面量例外。原回应只读不改。

mimo 对本批“无 P1/实现一致”的读码意见不被采信为充分放行证据：本轮执行新增反例证明上述四处遗漏。修复仍沿原 S4 工程契约；不得为迎合绿色结果改冻结判据。若修复实际改变已冻结化学口径或 proof scope，按已有版本/化学评审规则登记另审。

## 7. 正链裁定与 S5 前置状态

**不确认 S4 通过；四组 P1 待闭合。S3 通过继续有效，完整 S4 尚未形成正式交接。**

下一轮只回修 §4 四组及 §5/§6 描述精度，保持原正常链、真实 unknown/partial、合法来源声明、幂等、旧版字节和原拒绝控制。不得提前实施 S5、访问真实评测材料、调用 provider、修改冻结判据或承诺科学性能。

S5 前置可确认的工程部分是：932/G01工程回归、冻结稿零差异、旧版字节、正常完整链与文件确定性。尚不可交接的是：必要条件限制、完整 unknown/outcome 来源集、导出及投影的独立权威绑定。四组清零后正链按同一验收收口，不另增机制库/性能门；随后由用户另行授权 S5 任务书、评测域/留出与统计预注册、阈值/费用/真实provider及敏感资料边界。既有 `ppv1-criteria-v1` 冻结记录保持有效，本报告不重新冻结或自动升版本。

## 8. 下一轮有限回修提示词（自包含）

```text
你负责 pollutant_pathway_v1 S4 回修，不实施 S5。仓库仅
/Volumes/CC/Enzyme_Agent/dependingv43；基线完整HEAD
8735601b75825388fe9f4a177a1131ef264054a1，父fc40605819201ae4a7101fc500b19083d78383b0。

必读绝对路径：
/Volumes/CC/Enzyme_Agent/dependingv43/AGENTS.md
/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S4_CODEX_CONFIRM_REVIEW_2026-10-08.md（§4最低收口＋§7）
/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/ppv1_s4_confirm_codex_2026-10-08/README.md（各专项真实输入/日志入口）
/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S4_IMPLEMENTATION_TASK_2026-10-08.md（§2/§4/§5/§8）
/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S4A_DELIVERY_2026-10-08.md
/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S4B_DELIVERY_2026-10-08.md
/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_CRITERIA_FROZEN_V1_2026-10-08.md
/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_CRITERIA_FREEZE_RECORD_V1_2026-10-08.md
/Volumes/CC/Enzyme_Agent/dependingv43/docs/mimo_ppv1_chem_review_response_r16.md
/Volumes/CC/Enzyme_Agent/dependingv43/docs/mimo_ppv1_chem_review_response_r17.md
/Volumes/CC/Enzyme_Agent/dependingv43/docs/PPV1_REVIEW_PROTOCOL_2026-10-08.md

先列四组适用 build/derive/首读/consume/start/resume/export/project/read 入口矩阵；
每项标明消费的权威、必要集合、版本/身份/内容/证明范围和合法/诚实控制。
只修：
1. S4-C01：把当前路线已引入的必要 condition requirement/history 中 unknown/unresolved/conflict
   接入 endpoint 同源限制及输入摘要；保留 source-reported证据全文，已知兼容/支持正控，
   NAD未解决unknown控制。不能靠解析自由文本或全拒改变化学门，旧边按历史快照消费。
2. S4-C02：manifest core自身digest＋run/版本/策略内容绑定；必要artifact引用集合由独立
   权威同源枚举后闭合，与每行hash校验分别核。普通manifest-only改坏、自洽新digest漏
   单production_report＋坏/缺H07必须消费前拒；不是仅增加一个字段自比较。
3. S4-C03：空task_key不能挡soutc(action_id)独立枚举，统一build和manifest索引；
   正常child retrieve的no_local_candidate/unresolved_continuation全文入原生输出，
   坏必要soutc不能被跳过；保留合法缺席、缺键不产空引用、去重和正常非空两键。
4. S4-C04：v3构建与首消费验证真实原生来源、reference一致及当前adapter派生内容。
   假native删events/deferred＋真export引用、projection-only自洽改内容＋真reference均拒；
   已验证原生存在/自hash不是投影证书。保留有损12轴、正常和空池答卷、反向禁止/零DB写。

保留S3/已关S3a/S3b、首消费/ledger/AuditContractError、正常start/resume完整链、
未知/partial/deferred/失败、幂等、子进程确定性、八kind和已登记P2；
不改冻结legacy/G2/AtomTool/export_v3，不改金标/题面/封存逐题run，不调用外模或真实provider，
判分零LLM、不push。源码/契约消费变化按既有identity/version规范登记；旧run不跨版本续跑。
FROZEN正文不改；若改变已冻结化学含义/范围/硬门，停下按已有协议登记待审。

分别把本审每案复制到新tmp复跑，旧观察脚本钉住缺口、按修好后预期失败登记；
不要改永久反例期待造绿。新增回归在直接父8735601 detached稀疏worktree同字节运行；
行为红/collection/形态/字段/版本红与合法正控分开，不因新模块让所有用例停收集。
正式当前PPV1全量、G01安全白名单复跑；基线本轮932/1534/8/17/294只作历史比较，
实际数和缺席依赖逐nodeid如实报。禁pyc/pytest缓存，含vendor/metadata，父子环境相同。
注意本轮全量准备错误：硬杀子进程精简ENV会丢V3_CODE_ROOT，父/子应指同一隔离普通/空根。

补交付书入口→行为→证据→红绿四组映射，同步本报告§5/§6文案P2；更新自包含mimo新请求
描述实际化学消费限制（无金标，原r16/r17回应不回写，执行声明留待复审），由主会话按授权送审。
新证据根含README、实际HEAD/父/schema/version、完整合成输入/权威前后、argv/cwd/env/exit、
原始stdout/stderr/JUnit、准备失败原日志、SHA256 manifest；不以控制器JSON替代pytest输出。
v4.3本地提交只git add显式交付路径，不顺手加入旧未跟踪评审材料、不push；交主会话复审。
四组闭合后依同一范围收口，不启动S5、不承诺科学性能、不自动改判据冻结状态。
```

## 9. 永久证据入口

`/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/ppv1_s4_confirm_codex_2026-10-08/`：

- `README.md`：总导航、执行者与有限范围、准备错误/续跑、各子包入口。
- `root_audit/`：原材料快照、125项输入SHA、旧证据清单校验与报告质量、工作区保护。
- `execution/`：全量/两父基线/隔离G01/旧版字节，完整日志/JUnit和逐项缺席。
- `endpoint_contract/`：冻结字节、F01–F03、7个公共链条件/依赖案、mimo源码行号互证。
- `export_chain/`：18焦点、真实公共链/同进程与子进程字节、三组导出/聚合/投影反例，原失败与补证分别归档。
- `scripts/`、`manifest.json`、`SHA256SUMS`：只读装配/校验脚本和附件哈希，包含嵌套控制文件；外层仅排除其manifest与自身SHA。报告独立SHA在 `report.sha256`。

发布前后核HEAD、输入、既有工作树；旧证据只读不回写。精确实际脚本/输出路径以各子包 README 为准；子集结果不与全量相加。
