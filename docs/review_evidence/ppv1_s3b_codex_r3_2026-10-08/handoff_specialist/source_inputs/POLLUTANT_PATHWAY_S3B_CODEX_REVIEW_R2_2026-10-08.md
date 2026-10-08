# pollutant_pathway_v1：S3b 回修 r2 Codex 独立复审

日期：2026-10-08（Asia/Shanghai）。实际 HEAD：`2bedfc060a9b19019ba44aa2a56dcacb88450c3b`；直接父：`c1211183c0874b12c5b5461845d3c61f0a84719c`。

**结论：S3b 不通过，完整 S3 尚未到达工程完成交接点。P1 只剩 S3B-01（冻结计划与既有任务权威的内容身份绑定）。S3B-02～06 本轮按固定验收面关闭，S3a、真实化学生产链及 AuditContractError 不吞成成功的已验义务保持。**

永久证据：`/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/ppv1_s3b_codex_r2_2026-10-08/README.md`。

## 1. 范围、来源与执行纪律

本轮固定验收为首轮 S3b 报告 §4 六组 P1 的最低收口与 §7 放行条件；来源为 S3 实施任务书 §3/§5/§6/§7，以及 S3a R4 §8 的五条生产接线要求。不是追加机制、来源真实性、分布式锁或科学性能门。

主输入为 `docs/POLLUTANT_PATHWAY_S3B_DELIVERY_R2_2026-10-08.md`、`docs/mimo_ppv1_chem_review_response_r14.md`，mimo 保留只读 provenance，执行数字仅按本审新执行及历史原证据互证。已关闭项只在原契约内有新公共反证时重开。本轮唯一残余仍属上一轮 S3B-01，没有新增阻塞组。

三专项均用新 `/private/tmp` 源码/测试/vendor/必要 metadata 副本，禁 Python 字节码与 pytest 缓存；旧永久证据脚本和合成输入先复制，不在旧证据中建库或执行。父基线用 detached worktree。无真实题面、金标、封存逐题 run、dependingv4、外部模型、真实 provider 或 LLM 判分访问；仅工程规则级/scripted 输入，网络请求为 0。源码/测试/既有 docs/AGENTS.md 不改，无 commit/push。

本轮是新 r2 复审，不是重复上一轮已成验证。PPV1 首次隔离配置出现父进程与 worker 的 v3 根不一致，得到 861 passed/10 failed，十项均提前在 v3_engine_code 身份门拒，尚未抵达目标行为。原日志保留，修正两端指向同一隔离依赖后完整重跑一次，以后者作为当前全量结果；不把第一次十项记为产品漏洞，不拼接两次 passed。同一环境误配还使初始父新20得到17 failed/3 passed，该日志保留、不用于红绿；修正后仅重复这一受影响父集合。父更新3文件及G01各一次。协议专项另有旧 oracle 字段捕获早停与同 label 日志覆盖，按原始输出与继续记录披露；未执行的内部段不报通过。此轮未发生额度中断，前轮额度事件留在前轮只读快照，不回写。

根发布守卫记录 1028 个明确白名单既存文件 SHA、实际 HEAD/父、初始工作树与 tracked diff；保全用户既有 AGENTS.md 差异、.zcodeignore 和未跟踪评审材料。最终只新增本报告和本轮证据目录。

## 2. 独立数字与红绿分类

| 集合 | 本审结果 | 限度/归属 |
| --- | --- | --- |
| 当前 PPV1 全量 | **871 passed / 0 skipped / 0 failed，exit 0**；31 文件，pytest 25.73s/外层 26.174s | 最终修正环境后的完整一次；851 存量＋20 新 r2，不以数目替代闭合证据 |
| 父 c121 同字节新 r2 文件＋更新 worker | **15 failed / 5 passed，0 collection** | **13 行为红＋2 产物/字段形态红**；不是 15 行为红 |
| 父 c121 同字节三个更新既有测试文件 | **3 failed / 52 passed** | 1 profile 版本字面量红＋1 `KeyError('action_id')` 字段形态红＋1 novel 缺 reaction_spec 未拒行为红；不是 54 绿 |
| 上述父集合合计 | **18 failed / 57 passed** | 交付合计对，单项分类和绿数须更正；两个集合不重复计数 |
| 当前新 r2 20 项 | **20 passed** | 已包含在 871 内，不另外加总；本审从完整当前 JUnit 提取 |
| 安全隔离 G01 | **1473 passed / 8 skipped / 17 deselected，exit 0**；pytest 214.61s/外层 216.949s | 287 输入 SHA 前后同值；缺席依赖见下；与历史 1453 等各轮分开登记 |

父形态红的内部到达精度：`test_s3b01_frozen_plan_tamper_integrity_failure` 在父没有新 frozen_plan.json，停在 `is_file`，未执行篡改和恢复；`test_s3b03_transition_enqueued_crash_window_closed` 已执行公开恢复并核转换 done，但在 pending_followup 缺失形态断言停止，**后面的新上下文核对未执行**。不能说二者都跑完旧行为，也不能把后者写成根本未 resume。旧公共反例的本轮复跑另有完整恢复/phase 证据。

实际父绿五项为 same_plan、b4_event_no_followup、three_products_normal、nonzero_no_blocked、empty_pool_no_local。`test_s3b05_model_abstain_empty_pool_legal` 在父请求数 0≠1 是行为红；其当前合法控制通过，但交付 §1.5 将其称为父绿不准确。函数名中的 positive/negative 不是实际红绿标签。

G01 287 输入＝227 个本仓白名单输入（含源码/测试/配置/脚本/非题面资产）＋42 个普通 dependingv3 源码＋18 个非题面资产镜像；源与隔离副本 SHA 前后一致。8 skipped 逐项为：真实评价 5（`test_batch_runner:52`；`test_score_report:110/163/172/184`），旧 v4 对照 1（`test_analog_assets:95`），phase_d 派生 provenance/summary 2（`test_analog_v2_corpus:62/153`）。17 deselected＝16 slow＋明确排除 `test_export_v3::test_charge_fixture_cn_hits_raw_sb_misses_neutralization_forbidden`；完整 nodeid/原因保存在 execution 专项，不访问缺席数据来补数。此为安全隔离工程口径，不拿原环境数字或前轮数字冒充本轮。

运行环境为 depending43：Python 3.11.16、RDKit 2026.03.6、SQLite 3.53.4；profile-14/search-6/store-9/search-limits-3/format-feedback-1/model-proposals-2/runflow-2。全部数字不代表 dev（B1 环境路径中间步骤）或 298（RHEA 通用酶学）科学性能。

## 3. 六组逐案裁定及继承保持

| 组/原验收 | 本轮公共链/实际观察 | 裁定 |
| --- | --- | --- |
| S3B-01：冻结输入，首用/恢复同源，旧任务不消费新计划 | 同计划、省略 plan 沿冻结输入完成；显式换 plan/已 decide 后换池均 frozen_plan_mismatch，15 表零变化；缺文件、不可解析、普通 payload 改坏均先拒。**B3/B4 自洽重封装 artifact 仍消费新转换**，见 §4 | 部分关闭，保留唯一 P1 |
| S3B-02：坏 artifact/缺权威恢复不重执行、不猜修 | 坏 bundle hash/JSON claimed→blocked、0 event，原文件及账保全；额外坏 hash＋独立 C 案实测坏任务工具0，独立合法 C 工具1/提交1；重复恢复无新增。坏已提交 event/缺必要 reservation 权威公开先拒 | 关闭；全 resume 权威拒与局部坏输出隔离分开 |
| S3B-03：0/部分/全部后续集合与转换新 context | 常规三产物 3/3；2/3 入队硬杀补齐 3/3；event 后零 followup、转换创建后、转换后调度未 complete 的窗口均闭合；followup phase-1、旧边历史快照保持；全部完成再 resume 无新增 | 关闭；不能用字段红替代这些执行证据 |
| S3B-04：公开同 action 双恢复只一方执行，硬杀接管 | 两真实 public resume 进程 barrier，恢复专项胜者在 expand 执行入口 barrier 持锁，竞争方 driver_session_active、未到工具；释放 barrier 后真工具收据 **1**；原 attempt/预约 ID 接管复用；后再 resume event/commit 不增 | 关闭；限定同机 flock，不宣称分布式 exactly-once |
| S3B-05：novel 独立消费者及空池档案 | 空/非空池 novel 实际形成 1/2 独立 hypothesis/event/production_report，真工具→audit→admission→submit trace 1/2；substrate profile 不依赖池；合法空池弃权请求 1 如实 no_local；缺内容结构化 run_error（decide仍claimed），零hyp/event；scripted 网络 0 | 关闭；来源标签精度 P2 见 §5，未重开来源真实性门 |
| S3B-06：真实 blocked 原因/对象持久披露 | zero_depth 主因仍正确 budget_limit，other_reasons 含 depth_limit；持久 blocked=1，对象/假设/原因与行同源，重复 resume 不丢/不重数；合法非零与空池控制保持 | 关闭；主因优先级未动 |

三产物复跑沿旧化学/硬杀输入，但 total_search_actions 从旧20改30留预算余量，未声称完整输入字节与旧反例相同。交付 `tests/s3b_worker.py`（含 concurrent-resume）实际调用底层 `runflow.start_ppv1_run/resume_ppv1_run`；其双进程工具内 barrier 不单独证明 `workflow.runner.resume_run` 包装层。本审恢复专项另用两个真实包装入口进程，在expand入口 barrier/工具前竞争拒和实际真工具收据取证，两种证据来源分开。

恢复专项共 25 顶层观察：23 契约符合＋2 同组 S3B-01 反例；不是 25 pytest passed 或 2 个漏洞组。四硬杀/同 output/零新增/完整产品集合/并发执行入口计数均有原始公开 worker 日志、表、artifact 与进程收据。B2 未响应照实 pending/unknown、不默发第二请求，网络 0，不把 B2 说成其它三边界同样的 event/commit 数量。

E01 首选后续无候选仍继续备选、E02 两类 deferred 显式激活/旧 revision、C06 unknown有界继承、H04循环启动 initial supply，以及条件冲突/分支隔离、runner start/resume 分流均由存量全量及本轮公共控制保持。S3a 已关项保留：本轮未改化学账/事件/store 模块，底座行引用/预算/身份守卫的原回归全通过；不声称把历轮所有永久探针重跑了一遍。

`production.py` 当前/父 SHA 同为 **`3b1a66ea2bc3aa37f7caaa2ed1a7f5395cda5901ef2a03d765b932ee5b082262`**。52 份 legacy code_identity 文件逐字节相同，聚合仍 **`18007e6a7cc239606eb30921f91045540446a7d7298108be30d47fce2f1374d6`**；runner 未改。九份生产/化学共享核心同父，冻结 AtomTool/G2 没有修改。本轮不再把首轮 legacy 聚合变更说成当前又变更，也不许旧 run 跨 PPV1 新版本原地迁移。

本轮实际 caller 注入坏 proof 经真工具/audit 抛 AuditContractError，driver 窄捕获只结算 contract_aborted/failed，0 event，不吞成 verified/R6/成功。坏 state raw 在 audit 首消费 ChemicalStateError、0 event；执行失败在 production audit 前短路、audit 0/event 0，三 None/空 diagnostic evidence/converter metadata 保持。首轮 production 宽捕获负控为旧已成证据，本轮字节不变＋当前窄捕获动态再证，不冒称宽负控也新跑。合法 composition-only/unknown/partial 原控制保持，不能以全面拒绝换通过。

## 4. 唯一残余 P1：S3B-01 的冻结计划身份锚只在 retrieve 执行时消费

**对应原条款：**首轮 §4.1/§8.1、任务书 §3 的首次消费身份闭合及 §7 E03。要核实际冻结输入与既有任务的绑定，不是要求抗全库协同改写或新建签名服务。

源码：`runflow.py:224–253` 的 `_load_frozen_plan` 核 artifact 信封自身 payload hash、plan 与 payload 内 plan_digest；未对照先前已冻结任务所绑定的摘要。`runflow.py:1262–1280` 将起始计划摘要存入 root retrieve 的 task_key/plan_digest；但比对仅在 `_run_retrieve` `:572–580`。resume `:1358–1371` 只将调用者提供的计划与**现读 artifact**比，省略 plan 就不比；`_run_decide :659–674` 二层核的只是池 spec 摘要，也不能锚住转换/响应/激活等整个输入。已过 root retrieve 后，B3/B4 可以不再运行此根摘要守卫。

**公共复现：**用原规则 CCO→CC=O、合法原冻结计划，无转换；分别真子进程在 bundle 已写/事件已提交 B3/B4 硬杀。之后只改 `results/run-plan/frozen_plan.json`：加一条该 hypothesis 后的 injected scenario transition，并重算该文件内 plan_digest 与信封 payload_hash。不改运行身份、root retrieve/task_key/plan_digest、数据库、原事件或输出 bundle。调用真实 `workflow.runner.resume_run`，**不传 plan**。

两个案均成功沿旧 action/attempt/event 恢复，新增原计划没有的 scenario_transition 并在 followup 消费新上下文。root 已存摘要仍为原值，artifact 摘要变新值；resume 没有 frozen_plan_mismatch/完整性拒绝。不是“调用者明确新 revision”，也不是损坏数据被安全隔离。恰有一份独立原锚可以区分，不能援引 cache_hit 删除两记录后存储同构的既定 P2 免责。

证据精确位置：`recovery_specialist/adjudicated_summary.json` 中 `self_consistent_replaced_plan_after_bundle_written` / `self_consistent_replaced_plan_after_event_submitted`；同名 `inputs/*_mutation.json` 保存完整旧/新信封，`inputs/*_resume.json` 为公共输入，`logs/*_resume.execution.json`、stdout/stderr 和 `tables/*_start.json`/`*_mutated.json`/`*_resume.json` 保全完整十五表。两案 root 原摘要都是 `880bf6c37d09af15db7a82ad19cfd9aa4b4d1d52eab0efe256e8dd08babdeb94`，新 artifact 摘要是 `7164d4f966b107f19544e5e0a0cac7a4a80ce22e7f289f24a5ebc8c7fe3acd04`，plan_version 仍 ppv1-frozen-plan-1；各新增1转换/phase-injected。artifact改前与改后全表逻辑 canonical SHA 同值，B3为 `8ab6f68d189da22614dac48f92286dd430e46561fc941b1a5625aa034bdf35f5`，B4为 `f1e7a20f803faf25e575e4bf7a9d3f2769019f4034c7f282b91ffbcc381edbb5`。这不是执行前SQLite二进制SHA；该值当时未采集，不倒补，实际最终binarySHA及完整逻辑快照在包中。

这是原 S3B-01 未闭合的**后段首消费**：现有修复已拒显式换 plan、缺计划和普通哈希错，但自洽新包不能单靠自己的摘要证明仍是该 run/task 的原输入。本轮不用此反例重开已正常闭合的 S3B-03 转换调度规则，错误来源在计划绑定，不是要求场景转换永远禁用。

**最低收口：**公开 resume 在任何 recover B3 event 提交/B4 补账/driver 调度之前，用独立既存权威核冻结计划内容与该 run/root/task 初始绑定，不依赖旧 retrieve 是否还会执行；版本/身份/必要锚缺失或不符先结构化拒且业务表/event/commit/consume 零新增，原资料保全。沿 start/resume 同源规则，正常同计划、省略 plan、显式计划合法全保持；只改一份 artifact 的 B3/B4 自洽重封装必须拒。不规定必须增加新表/密码学签名，不要求抵抗同时改完所有权威，不需新阶段功能。

## 5. 如实登记的 P2 与已接受边界

| 项 | 本审范围裁定 |
| --- | --- |
| 冻结计划仍是合成/规则级 | 接受，不认证检索质量/机制/酶学；**§4 的原输入身份仍须成立**，不能用科学 pending 免责 |
| 同机 flock | 接受，锁文件 pid/时间仅披露，flock 是权威；竞争拒的“零写”指业务账，不应说 driver.lock 披露文件也从未写过 |
| 二层 pool_digest 正常流不触发 | 第一层阻显式换输入、二层正常无坏输入可接受；但“第一层已经闭合所以后段都不可达”的全称被 §4 反证，需改成各自许可范围 |
| novel 来源标签 | decide prepare 传 model proposal source_refs，expand 重建未传而用默认 synthetic-pool-spec；实际 event appearance 使用后者。hyp ID 不受这些 refs 影响、冻结 plan 含原响应且 action proposal_context 保留，来源可追溯，未发现身份洗坏/错误 verified，**P2，不另加阻塞**。不宣称标签逐字一致或已认证现实来源，冻结前清理误导文字 |
| stop 对象有界 100 | 与交付相符，计数为完整行集、对象列有界；不报成无限清单。不同被隔离的 retrieve/decide subject 未必是化学 hypothesis，字段名是视图口径，别外推化学结论 |
| cache_hit 同构、两事务间外部 SQL 窗口、foreign-run 反向诊断、保守 defer | 沿 S3a/R4 已接受 P2；本轮无新公共高风险反证，不追加全库扫描/外部 exactly-once |
| 三 RuntimeError 包装、unused 历史 appearance | 保留首轮 §5 的精度与证据范围；不能将 Audit 窄捕获安全外推所有异常统一结算，也不说未实际复用的坏旧出现已经认证 |
| 默认反馈 0/scripted、科学性能 pending、判据未冻结 | 接受本阶段边界；不发真 provider，不用工程绿数宣传 dev/298 性能，不启 S4/S5 |

## 6. mimo v14 互证及交付精度更正

mimo 对五判据和 0c/0d/0e 的读码意见，不代替运行闭合。其“同意/基本同意”仍带执行待验证及未读分支；本审不调用外部模型。化学模块字节不变，R4 父绿 11+1、CX/RDKit 词法往返等保持**历史执行来源**，不说本轮又跑过/跨版本认证。实际 PPV1、G01、父红绿、双进程/硬杀、Audit 动态链由本轮包证成；同组计划残余使 0e.1 的全范围闭合声明不成立。

| 条件/落字 | 本轮互证 |
| --- | --- |
| 判据一词法与 identity、判据二 λ_s×Δ/known_absent | 不变源码/既有回归保持。元素账不消费 known_absent 缺席语义；给定声明清单的数值平不认证漏项、电子/同位素/机制或来源真实性。回应 §7.2 “973-779”是笔误；请求为 973-979，实际源式 `audit.py:973–980` |
| 判据三覆盖/full/入口范围 | full 只解除许可覆盖轴，不认证化学转换；补全与系数绑定分开；`store.py:1988` 的 verify_event_attachment_content 核附随内容/plan/projection，不能单独当 strict state 身份证明。一般 B4 followup 的实际入口 `runflow.py:364–423`，转换补齐 `:441–483`，不能把 `:428` 载荷构建当整个一般补齐证明 |
| 判据四事实/孤儿/history | 给定事实集条件相容不认证事实真实性；新转换只后效。历史快照与 orphan 既有源码/原回归保持，模型未逐行确认不等于源码缺失；无需本轮重新定义条件规范 |
| 判据五失败诊断 | audit 函数被调用时各轴独立；实际 production execution_ok=False 在 `production.py:399–404` audit 前短路，0 audit/0 event。三 None 不是通过，不能描述成生产链失败仍推进。`audit.py:2980–2981` “至少 unknown”旧注释与现 strictFalse 前置通过后 violated/R5v 不一致，列冻结前 P2 文本同步 |
| 行号/文件 | workflow/runner.py:214–228/305–320 为双入口，mimo v13 错文件名本轮已更正；计划 persist/load 为 runflow.py:211–253，driver flock 段 259–321，勿统称 211–321 都是计划段；Audit 窄捕获 955–966、production 399–404、search 隔离 1155–1224 与实际相符 |
| 0e.1–6 | 02隔离、03集合、04会话、05novel、06披露执行证成；01普通控制通过但 §4 自洽重包后段漏锚仍阻塞。不能将读码“冻结來源”与执行证明身份绑定混为一谈 |

交付须在下轮新文档更正而不改旧快照：15 红改 13 行为＋2形态；旧行 54 绿改 52 绿，合计 18/57 保留；abstain_empty_pool 父红；两个形态红早停的内部到达如 §2；实际 HEAD 在提交前 evidence 的 c121＋dirty 有其采集时序，最终受审提交为 2bedfc，不能把前者说成当前 HEAD。新日志/源码/提交与交付声明分开登记，不用本审给交付自报背书。

## 7. 最终裁定与交接停点

**不放行 S3b/完整 S3，P1=[S3B-01]。** 本轮已有实质进展：五组关闭，保留原 S3a 和真实化学链，不重复追已关门，也不把一般 P2/科学 pending 当新阶段阻塞。下一轮只修 §4 的同一内容身份规则和关联精度落字，不再回做六组已关功能。

有限回修→新自包含无金标 mimo 请求/回应→独立 Codex 复审。仅在该残余清零、合法及继承控制保持后，才到规格 §17 的 S3 工程完成交接点；随后交回用户裁定判据版本、证明范围、冻结包/teacher 审核。冻结前同步 §5/§6 的文字盲区及行号。工程放行也不等于判据自动冻结或真实性能通过，S4/S5/真实评测/费用与金标相关授权另起任务。本评审不启动外模或实施。

## 8. 下一轮自包含有限回修提示词

你负责 **S3b-r3**。仅工作于 `/Volumes/CC/Enzyme_Agent/dependingv43`；直接基线 `2bedfc060a9b19019ba44aa2a56dcacb88450c3b`。遵守仓库 AGENTS.md；实施由主会话派单一实施 agent，完成后走 mimo→Codex。只收口本报告唯一 P1 **S3B-01**，不重开 02～06/已过 S3a，不实现 S4/S5/分布式锁/新机制库，不访问题面金标封存 run/dependingv4，不调用真实 provider/收费模型，科学 pending。

必读绝对路径：

- `/Volumes/CC/Enzyme_Agent/dependingv43/AGENTS.md`。
- `/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S3B_CODEX_REVIEW_R2_2026-10-08.md` §2–§7及 `/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/ppv1_s3b_codex_r2_2026-10-08/README.md`，recovery 专项 B3/B4 自洽重封装输入/日志/旧新摘要。
- `/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S3B_CODEX_REVIEW_2026-10-08.md` §4.1/§7/§8；原证据只读。
- `/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S3_IMPLEMENTATION_TASK_2026-10-07.md` §3/§7/§9/§10。
- `/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S3B_DELIVERY_R2_2026-10-08.md`、`/Volumes/CC/Enzyme_Agent/dependingv43/docs/mimo_ppv1_chem_review_response_r14.md`、`/Volumes/CC/Enzyme_Agent/dependingv43/docs/mimo_ppv1_chem_review_request.md`。

先列 start/resume/frozen-input-load/recover-B3/recover-B4/driver 各入口→已冻结权威→守卫→正负控制矩阵，再实现共享规则。**不能只改 _run_retrieve/_run_decide 或只拒显式传入新 plan。** 在 resume 首消费前，把读取的冻结计划与独立既存 run/root/task 原绑定核对，覆盖 root retrieve 已 done 的 B3/B4；自洽 artifact 内自 hash/自己写的 plan_digest 不能当独立证书。缺/坏锚或不符先结构化拒，任何 event 提交/补账/新调度/成功 consume 前闭合，原数据保全。无需额外密码学服务/抗全库协同改写，选择符合既有身份规范的最小实现。

用本轮两原反例复制到新 tmp：只改 plan artifact 的转换意图、重算该文件摘要/信封，旧身份/root task/数据库不变；public resume 省略 plan，B3/B4 均拒且业务表/event/commit/consume 零变化。保留同计划、省略 plan、合法原计划转换、三产物 0/部分/全部恢复、重复完成无新增、双进程真工具只一执行/硬杀接管、novel及弃权、blocked多原因、E01/E02/C06/H04、真实化学 unknown/partial/Audit 异常控制。不要全面禁转换或全部拒恢复来换通过。

新增回归对直接父 2bedfc 同字节跑，分别登记行为红、版本/字段/产物/collection红及真正父绿，明确早停内部段；PPV1与安全G01 fresh批次运行，不锁死当前871/1473，287白名单随显式新增路径更新、SHA前后及缺席依赖逐项披露。完整命令/env/HEAD/schema/输入输出/worker日志/表/哈希入新 evidence；旧永久证据不得原地执行/改写。隔离父/worker V3 根保持一致，环境错误若有留原日志，不冒称产品失败。

新交付及下一 mimo 请求同步本报告 §2/§5/§6 精度，明确 01 后段锚定与其闭合证据，不称源标签逐字全链一致、不外推 full/账平/condition satisfied/失败诊断语义。版本/身份影响按既有规范登记待审，冻结 legacy/G2/AtomTool 不动。v4.3 本地提交，git add 显式路径、不 push，不顺手暂存 AGENTS 用户差异/评审侧未跟踪材料。Codex复审前不宣布 S3 完成/判据冻结。
