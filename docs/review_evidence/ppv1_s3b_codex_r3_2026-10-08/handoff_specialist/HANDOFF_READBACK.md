# S3b-r3：mimo v15、继承控制与阶段交接补充

实际受审 HEAD：adf0287abef0c4803962fee0df0065d8e6f3793d；父：2bedfc060a9b19019ba44aa2a56dcacb88450c3b。日期 2026-10-08。程序证据只来自 depending43 的 Python 3.11.16 / RDKit 2026.03.6、独立 src/vendor/pyproject 副本、公开 start_run/resume_run 合成夹具。仓内只读，未执行外模/真实网络/题面金标/封存 run。冻结材料不在本子任务里修改。

## 1. mimo v15 七项冻结前更正与源码互证

| 项 | 本轮源码事实 | 交接操作，非本轮代码门 |
|---|---|---|
| 1. substrate_profile 已有生产 caller | runflow.py:809 调 build_substrate_profile；812–814 持久写 artifact，空池不跳过。 | 判据三⑤/入口清单旧“无生产 caller”改成“S0–S2 时点无；S3b 起有”。档案不是身份/verified 证书，输出前置验证一般增强继续 P2。 |
| 2. R3 defer 不等于持久 blocked 行 | audit.py:1528–1529 的 action=blocked 注释旧；生产 runflow.py:1122–1133 留假设、记 admission_deferred。当前真实 essential_conflict：三 action 都 done、假设1、event0、R3 defer。search.py:1078–1147 深度阻断、1155–1224 恢复隔离才写 blocked。 | 请求规则表改“当前场景不展开，admission_deferred，假设留痕”。将 audit docstring/旧规格正文相同措辞列 P2 文本同步，不要求为了匹配旧注释改变正确实现。 |
| 3. runner/runflow 错行段 | 真分流为 workflow/runner.py:214–228/305–320；runflow 同区间为 _complete_action 尾部、锚 SELECT；reconcile_followups:500，drive:629。 | 0d.8 与 0c-v14.3 去掉“runflow 同区间 reconcile/drive”。 |
| 4. Audit 窄捕获旧行号 | 当前 runflow.py:1091–1102；955–972 属历史 r2。production.py:399–404 是工具 execution_ok=False 的 method_failed 短路，不是 Audit 异常短路。 | 标历史版本/当前行号。三 RuntimeError 原样逃逸为已登记 P2，不把窄捕获安全夸成所有异常统一结算。 |
| 5. “恒入”限定 | audit.py:1009–1013 完成覆盖判定后带 license/scope；889–897 unknown_coefficients、其他早退不带。 | 改“凡完成覆盖判定的 center detail 必带（full/partial，早退不带）”。字段存在不表示本结论用了许可；同屏保留 full + uncovered refs 非空 + unlicensed 为空的组合判据。 |
| 6. λ_s×Δ 行号 | audit.py:973–980 两侧均有对账，非缺式。 | 973–979 更正为973–980；同源算法复算不称独立化学证明。 |
| 7. 执行数字/HEAD/字节声明 | mimo 只读、未执行，不背书数字。当前本审独立执行项/执行专员回执与历史 R2 来源分列。 | 冻结稿给独立执行回执；未重跑历史项明确历史来源；不要将所有数字永久笼统标“本轮已执行”。 |

前六项是文字精度；第七类取证。现请求仍有这些旧文字，不在审核侧偷偷改既有文件。工程裁定和正式冻结分开：即使根审核放行 S3，也不自动宣布判据已冻结。mimo v15 原文允许“改字后无需新增化学评审轮次”，前提是不触碰判据一–五化学正文；有语义改变须既有版本规范登记待审。

## 2. 进一步事实更正与读码补足

- mimo v15 §10.1 将 **历史 r2 13行为红+2形态红**复跑的父基线写成2bedfc0。正确：历史 r2 新20项的父是 **c1211183**；本轮 r3 新8项的直接父才是 **2bedfc0**。历史 R2 报告/永久证据已经有独立结论，本子任务不浪费重跑历史。R4的11合法+1旧坏输入拒绝控制同样标历史执行来源，不宣称本轮新跑。
- novel 来源标签读码与实跑补足：decide runflow.py:856–862 传 `novel-model-proposal:<origin>`；expand1069–1073不传 refs；production.py:195 默认 `synthetic-pool-spec`。当前 trace 两构造 product_state_id 相同，标签不同；proposal_context 仍在 expand action payload（runflow.py:920–921）。不能写全链标签逐字一致或现实来源已认证，P2不升门。
- preview C2 的行号补证：pool_audit.py:249–306 的 run_input_preview，275–279 调冻结 conservation_filter_and_rank，只取诊断、302 明写 pool_unchanged=True。它不创建 ChemicalState/identity/verified 证书，diagnostic/off 划界可核，不能用“全入口守卫”扩为全仓旁路不存在。
- followup未亲读部分补足：runflow.py:500–558 从 commit/event/expansion_plan逐对象派生 products；:564–575 为 pending_followup 单一载荷构造；:596–615 在 enqueue_scenario_transition 时一次传入；常规生产1144–1166共用构造；转换执行1247–1278读取载荷并用新context调后续。这是补 action 集合，非重造事件。恢复行为闭合由恢复专员取证，本子任务未重复其锚/硬杀任务。
- 异常词法静态 AST 互证：audit.py10个AuditContractError抛点、6个except Exception，宽捕获不词法包住这些抛点；runflow0宽捕获、1个特定Audit窄捕获；production0宽捕获/0直接该异常抛点。静态不是任意第三方 caller 的动态保证，当前真实 driver 负控另见§3。
- 恢复/写入异常层次不可混：工厂/strict外层 detail.kind；from_dict 外层 state_structure_unparseable/raw_structure_rejected 且 reason 内因；writer raw_structure_unparseable（store.py:632）无 reason。输入接受只表示表示层契约通过，不认证样品或异构体鉴定。
- 补全full只解除许可覆盖轴；账平不认证声明清单完整/电子/机制，D/T合并与自由基电子不入账盲区保持；known_absent归条件轴；条件satisfied/conflict仅核给定事实相容，不认证事实为真。strictFalse在绑定/覆盖/前提成立后violated/R5v；None=unknown。

## 3. 本轮已执行与未执行来源

1. `lexical_probe.py`：RDKit2026.03.6实写 plain/ABS/AND/OR/自由基5正控；factory、strict、canonical输出与state.from_dict往返同身份。ABS写`a:`但规范身份剥离，AND实写`&1:`、OR`o1:`、自由基`^1:`；and/or/rad三个英文别名分别factory/strict入口共6负控都拒unregistered_cx_class。表示层规则级结果，不是化学鉴定/跨RDKit认证。
2. `inheritance_probe.py`：复制历史原规则输入到fresh tmp，9项公共观察全真、所有worker真实`workflow.runner.start_run`且socket connect禁止。novel空/非空分别1/2真实AtomTool→audit→decide→event；脚本响应network0。
3. zero_depth：budget_limit主因正确、depth_limit在other_reasons、blocked=1且对象持久披露。本子任务只本轮start控制，不说又重跑恢复幂等。
4. essential_conflict：R3 defer、event0/hypothesis1、actiondone、admission_deferred，与0e.6持久blocked不同。
5. E01 event2，第一支no_local仍探索另一支；H04 missing/supported均event1，dependency轴分别unknown/verified；branch_isolation event2。`read_captured_semantics.py`只读已捕获数据（不复跑行为），另断言C06 unknown条件/账目仍retain_conditional提交，以及H04未解/支持差别。
6. novel真实AuditContractError负控：真工具/诊断/converter之后改proof raw为含r串，真实audit抛，事件0/假设0、attemptfailed、actiondone、落contract_aborted。search_commit_records=3含已有retrieve/decide及失败结算；**不得说业务账全零/commit0**。此包未重跑首轮“第三方人工宽捕获包裹”控制，其既证义务由未改production字节/当前原回归及当前真实driver负控继承。
7. 本包不执行全量pytest/G01/父基线/恢复锚/并发；那些由其他专员独立执行、根报告登记。没有把整个历史probe库都跑过的声明。

## 4. 如实接受的P2/范围，不添加新门

- source标签不全链同字；audit.py2980–2981 strictFalse“至少unknown”旧注释应冻结前同步violated/R5v，audit451附近已正确不要乱改；R3 blocked旧注释及substrate_profile过时无caller表述一并文字清理。
- 同机flock只约束同机driver；driver.lock的pid/时间是披露，持锁者拒绝锚路径会重写它。“零写”指15业务表/业务artifact，不承诺锁披露文件不写；不宣称分布式互斥/provider exactly-once。
- 计划文件和数据库根retrieve行是不同存储通道；它们共同处于同run储存域。不抗artifact+DB+identity全量协同一致改写，无额外密码学服务门。
- 执行层plan_digest/pool_digest保留纵深防御；正常公开流已由入口守卫拒，不能虚称本轮实际运行时触发二层漂移负控。锚扫描无plan_digest的普通followup retrieve被跳过，缺锚是无任何携带该字段retrieve。
- cache_hit同构（删检索ref+row与合法缓存形态不能区分）；两事务间外部SQL并发窗口；foreign-run反向诊断；保守defer继续沿S3a/R4已定P2。
- RuntimeError包装、unused旧appearance未消费边界沿首轮/R2，不把全库历史损坏都说成认证/修复，也不把上述逃逸误称成功事件。
- blocked计数完整，对象列有界100；不是无限清单。有些被隔离subject是retrieve/decide非化学hypothesis，不外推化学结论。
- 夹具三产物total_search_actions旧20→30是单例留预算余量的显式变化；不可说完整输入字节与旧反例完全一样，也不是生产最优预算。格式反馈默认0/scripted，真实provideroff。
- 合成/规则级计划池不认证检索质量、机制、酶学或真实主路径。科学pending、判据未冻结。

## 5. 工程交接后的路线（仅建议，不实施）

1. **若根评审裁定P1清零，S3工程到交接点即停**，按AGENTS交回用户。冻结是独立裁定：准备一个可review的最新判据稿，完成§1七项与§2来源标签/旧注释精度同步，附已执行/历史未重跑/仍pending清单及本轮HEAD、schema、哈希。核版本/证明范围；无语义变更纯文字同步不偷偷升gate。有语义改变按版本待审，必要mimo；不篡改旧报告回应证据。
2. **S4另写任务、用户启动**：规格§10/§11/§17.3/§17.5，endpoint分账、原生导出、v3适配lossy_projection与loss清单、scripted端到端。F01：搜索停止/仅CO2不冒称矿化；F02：模型上游依赖继承至下游recorded，不能洗成观测；F03：保留同CN不同来路、重复来源不增加独立支持；G02：相同版本/图修订确定性、过期派生可识别。终点依据evidence_basis不当固定强度序，矿化coverage不等于根碳全矿化。保留事件全部共同产物/角色/context/audit/预算与未展开集合，不把本轮验收JSON当S4正式产品。
3. **S5另写任务**：规格§13、§17.1 P0-5、§17.5。交付评测器/参考图与数据清单schema、研究来源组留出/防泄漏、retrieval_supported与unseen_path_inference两轨、样本量/通过线/区间预注册。计分零LLM；参考图外边不自动化学错误，无独立题源时交工程规则级测试、科学pending。真实题面金标/teacher/费用/外发须另按既有授权边界，当前任务一律不碰。

PPV1/G01绿数是工程规则级计数；不外推dev(B1环境中间步骤)或298(RHEA通用酶学)，不说路径命中率提高。
