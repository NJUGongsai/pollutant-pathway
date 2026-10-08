# pollutant_pathway_v1：S3a 独立复审

日期：2026-10-07（Asia/Shanghai）。仓库：`/Volumes/CC/Enzyme_Agent/dependingv43`。

**结论：S3a 不通过，S3b 暂不可启动。五组 P1 为：输出恢复错绑、完成/恢复接受坏权威账、预算可退还已执行额度且配置首消费失守、请求同键异内容及执行权失守、停止报告漏掉正在执行的动作。** 全量工程测试与交付数字一致，但没有覆盖这些实际公共链缺口。下轮仅回修本报告 §4 五组，不增加 S3b、机制库或科学性能门。

从污染物降解路径预测的目标看，这些问题会把别的路径结果记到当前分支、把坏历史当成已完成、丢掉尚未探索的工作并突破有限搜索预算。先把这层账目和恢复闭合，才有可靠的生产化学链可接；本轮并未认证具体反应或酶的生物可行性。

实际审核 HEAD：`9b78f4279cc6fa50b3b51c31a5c8e07abbeda207`；父提交：`00e509a974b40a7c9779fcd35e53b16637a13d60`。以下行号均对应该 HEAD。

永久证据入口：`/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/ppv1_s3a_codex_2026-10-07/README.md`。其中 `execution_specialist/`、`search_specialist/`、`inheritance_specialist/` 是本次委派独立执行的三个专项；`root_probes/` 是主审另行执行的请求与策略消费探针。不是实施方日志换名归档，也没有调用外部模型。

## 1. 固定验收面与证明边界

验收基准为 `/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S3_IMPLEMENTATION_TASK_2026-10-07.md`：§2.3 S3a 边界、§3 继承、§4 底座、§7 的 a 批行、§8 文档同步、§9/§10 证据交付。任务书 SHA-256：`8488d36dc849393f6e0411423bcf5ec9d7275aa091a9ac9e1f05ff38ec29558d`。

审核交付书及 mimo 原回应：

- `/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S3A_DELIVERY_2026-10-07.md`。
- `/Volumes/CC/Enzyme_Agent/dependingv43/docs/mimo_ppv1_chem_review_response_r9.md`，连同当前 v9 请求；mimo 只读意见采信到与当前代码和本轮执行互证为止。
- R8 报告及永久证据仅作继承出处，保持只读；未把旧执行当本轮数字。

本批只验持久搜索身份、预算、请求底账、认领、artifact、恢复、停止及 H05–H08/E03/E04 底座。S3b 的生产调度、两类 deferred 触发、模型 proposals 协议、中心证据生产 caller、公开 runner 分流均未交付，不因其缺席增加本批 P1。S4/S5、判据正式冻结、科学性能仍 pending。

全部执行使用 depending43 Python 3.11.16、RDKit 2026.03.6、SQLite 3.53.4，在新仓外隔离目录复制完整 src/vendor 与必要 metadata，关闭 Python 字节码及 pytest 缓存。只用合成输入；不读取真实金标、题面、封存逐题 run、dependingv4；没有真实 provider 调用或判分 LLM。探针中 `provider_kind=real` 只测试登记账表，网络调用仍为 0。

本轮只新增本报告和上述证据目录。不修改 src/tests/既有 docs/AGENTS.md，不提交、不 push。原有 AGENTS.md 用户授权未提交差异、`.zcodeignore` 及未跟踪评审材料保留；执行前后的明确输入哈希、工作区和 HEAD 见外层 metadata 与专项日志。

## 2. 独立执行数字与红绿分类

| 执行 | 本轮实际 | 解释/证据 |
| --- | --- | --- |
| PPV1 全量 23 文件 | **594 passed / 0 skipped / 0 failed**，exit 0 | 536 存量 + 58 新项；1 条历史字符串转义 warning。`execution_specialist/ppv1_full/` |
| S3a 两个新增文件当前 | **58 passed**，exit 0 | search 45，recover **13**。`s3a_current/` |
| 父提交两新文件 + profile 同跑 | **2 collection errors**，exit 2 | 新 search 模块缺失；58 新用例未执行，该组合中 profile 也未执行。`baseline_collection/` |
| 父提交 profile 单跑 | **2 failed / 21 passed**，exit 1 | 两个首失败为 profile-8 对 -9、search-limits-2-proposed 对 -3；无字段/缺表适配红。`baseline_profile/` |
| 安全隔离 G01 | **1196 passed / 8 skipped / 17 deselected / 0 failed**，exit 0 | pytest 194.01s，控制器 195.855s；`g01_safe_isolation/`、`g01_summary.json` |

父提交使用 detached sparse worktree 及完整隔离 source；两新文件、profile、worker 的四份输入与当前文件字节完全一致，没有改 import、期待值或返回适配。worktree 已正常移除，建立/选取/清理全日志留存。**不能把两文件 collection 错误换算为“58 个旧行为漏洞”**。第二个 profile 测试在 search-limits 版本断言先失败，后面的 delivered_stages 断言未执行；不能称第三项已单独证红。

安全 G01 共 274 项显式输入：当前仓 214、普通 dependingv3/src 42、本仓明确非题面资产镜像 18。隔离固定 PYTHONPATH、空 BBD_DATA_ROOT 及 V3_CODE_ROOT/V43_ASSET_ROOT/DEPENDING_V3_ROOT；不补读真实评价、原 v3 资产、v4 或封存目录。只在交付控制器副本增加 JUnit 输出参数，没有改变选测/隔离语义。

| 缺席类别 | 实际项 |
| --- | --- |
| skip：真实评价依赖 | 5：test_batch_runner:52；test_score_report:110/163/172/184 |
| skip：v4 对照源 | 1：test_analog_assets:95 |
| skip：phase_d 派生 metadata | 2：test_analog_v2_corpus:62/153 |
| deselect：slow | 16；另做 collect-only 留下 nodeid，没有执行测试体 |
| deselect：明确排除 | 1：`tests/test_export_v3.py::test_charge_fixture_cn_hits_raw_sb_misses_neutralization_forbidden` |

R7 历史 1110/8/17、R8 历史 1138/8/17 与本次 1196/8/17 分开登记；不拿原环境 1119/16 混用。全部为工程回归，不能外推 dev（B1 环境路径中间步骤）或 298（RHEA 通用酶学）的科学性能。

附加执行按原始案例分段登记，不与 pytest 数相加：搜索 16 案 + 四个硬杀/一个 barrier 5 案 + 预算连用 1 案，共 22；继承权威 26 案 + raw 首提 1 案，共 27；主审请求 11 案（另有首行 metadata）与策略 5 案；化学小探针 15 案、原 R8 固定 CX 9 案另列。观察断言通过表示已钉住当前现象，**不表示坏案例符合正确契约**。

## 3. 固定矩阵逐项裁定与保持项

| 原任务 | 合法控制已证 | 本批残余/裁定 |
| --- | --- | --- |
| §4.1 身份/E03 | 正常任务/事件幂等，新假设/context 换身份 | B3 四种有效异身份事件被错绑消费；请求同键异载荷未冲突。对应 P1-01/04 |
| §4.2 十上限/E04 | 逐步复算、缓存不重复计 actual retrieval、适用零预算独立夹具、合法循环封顶 | 已执行 event 经 defer 退额度，可突破有限上限；坏策略可注册/执行。P1-03 |
| §4.3 H06 | 双进程 barrier 一胜一拒；1 attempt、3 预约、0 request、0 event；不同 parent/context 正控成立 | 基本认领事务成立，不证明下游请求拥有合法 action/attempt 执行权。P1-04 |
| §4.4 B1/B2 | 硬杀后沿旧 attempt/预约续跑；悬空请求可见、不默发，显式 retry 另登记；scripted 网络 0 | 坏必要引用消费仍未闭合，不能仅凭 B1 说明字符串证明完整。P1-02/04 |
| §4.4 B3/H07 | 合法同 output 恢复仅一个 event/commit；hash/反序列化负控保全拒绝 | artifact 自洽不等于与当前 action 的全身份绑定。P1-01 |
| §4.4 B4/H08 | 合法一次补账、二次恢复不重复；缺事件/索引错绑等已有负控拒绝 | 首次 complete、坏完整事件账、缺 attempt/预约仍可成功。P1-02 |
| H05 | 独立零总预算/零深度/空池、优先级、deferred 正控 | claimed 动作被漏掉，错误 exhausted_search。P1-05 |
| §3 R8 继承 | 正常搜索提交 raw+r 拒且零写入；化学五源字节未改；runner 两入口仍拒 PPV1 | 新恢复消费入口降格校验，是本批新缺口；不宣称既有普通 writer 又坏了。P1-02 |
| §8–§10 交付 | 文档同步主体已落字；安全 G01 与数字可证 | 精度项见 §5/§6，不能用主体绿代替上述公共链闭合 |

四个独立崩溃子进程均 `os._exit` 硬终止后新连接恢复，未用同进程 raise 冒充。B3/B4 合法控制 event=1、commit=1、预约=3，第二次恢复零新增。H06 使用两个独立进程双 ready+GO 同步，一方 exit 0，另一方 already_claimed/exit 3；没有顺序调用或随机 sleep 代替 barrier。

`submit_event` 事件事务保持；搜索记账是同一连接的另一段事务，二者间 B4 协议本身可接受，前提是**消费完整、合法权威**。本报告不要求跨 artifact/数据库假造原子，也不要求所有 action 整个 run 的恢复事务一体回滚。坏单案必须在其消费/补账前拒绝；其他合法 action 的已完成处理须在日志分开披露。

## 4. 五组 P1：证据、对应契约与最低回修验收

### S3A-01：B3 消费有效但属于别的动作的事件

**对应任务书 §4.1 冻结身份、§4.4 B3、§7 身份/E03 与 H07/H08。** 正常 `submit_action_event` 在 search.py:1086 调 `_verify_event_frozen_to_action`；B3 在 :1571 直接 `store.submit_event`，:1622 的 bundle 验证只查 action/条件性的 attempt 引用及 event 自推导 ID，未把 event 的 run/parent/context/hypothesis 与当前 action 闭合。

四个分案各建立合法 claimed A 与独立有效 event B，仅分别改变 run、parent、context、hypothesis。B 的化学/事件内容与 hash 均合法，bundle 绑定 A 的当前 action/attempt，没有破坏 artifact 字节或 hash：

- 同一个 B 经普通搜索提交会拒绝，零 event。
- 经 `write_commit_bundle → 新连接 recover_run` 却都插入 B：event 0→1、commit 0→1、原 A claimed→done。

证据：`search_specialist/observations.json`、`probe.stdout.jsonl` 四个 B3 wrong 身份案及合法 B3 对照。mimo v9 判据一末段也给过“转 Codex”的静态预警；本轮执行证成它，不能写成 mimo 已执行。

**最低修复：**所有同类输出首次消费/恢复复用同源 action+attempt+task+event 绑定，核适用的版本、归属和冻结事实后才写 event/补账。B3 不可只验“event 自己的 ID 正确”。列 write_bundle、正常提交、B3、已有完成结果复用的适用入口；不同 parent/context 的合法新 action 保留。

**最低验收：**四案逐一从公共链拒绝，原 artifact 保全、坏 action 零 event/commit/consume；合法 B3 同一 output/attempt 一次落 event、二次恢复零新增；hash/反序列化原负控保持。task/envelope/attempt 绑定共享校验，不能绕过另一消费口。

### S3A-02：首次完成与 B4/done 恢复只信索引，坏账仍当成功

**对应 §3 第2条 ledger 首消费、§4.3 提交事实、§4.4 B4/H08、§7 R8 继承。** `complete_action`（:1152–1265）在消费预约及写 done 前不核 event 是否存在/适配/完整。B4 `find_event` 命中即 complete（:1513–1537）；done/已有 commit 调 `_verify_commit_event`（:1595），只看 get_event 的四个身份列。`get_event/find_event` 是读视图，不能代替 store 现成完整重放校验。

公开链实证：

1. 首次 `complete_action(COMMIT_KIND_EVENT)` 指向不存在的 event 或另父有效 event，都先写 done/commit、consume 预约并返回成功；下一次恢复才 H08 拒。后续恢复拒绝不能抵消首次错误落账。
2. 合法 event 提交后，删该 action 必需的预约行或 attempt 行，B4 仍补 done；UPDATE 0 行没有被当缺权威失败。
3. event payload 损坏但身份列未变，B4 仍补账，正常同 event writer 重放当场 `Ppv1LedgerCorrupt`。
4. 继承专项分别在 B4 未补账与 done 首次恢复测试 12 类损坏：`state_charge`、`state_schema`、`appearance_source`、`appearance_raw`、`hypothesis_origin`、`event_manifest`、`projection_delete`、`plan_delete`、`links_delete`、`state_delete`、`appearance_delete`、`hypothesis_delete`。**24/24 坏案 recover 均成功**：B4 全部 done/consumed/recorded；done 全部报告 `done_commit_verified`。同库原有效输入调用公共 writer 重放 **24/24 拒且零变化**。两 clean 控制均合法。

证据：`search_specialist/observations.json` 的 complete/B4 案；`inheritance_specialist/authority_cases/` 每案原输入及 original/before/after/replay_after 全 14 表、异常 detail；`inheritance_v2.stdout.jsonl` 及两份断言。`assert_contract.py` 按正确契约应失败，实际首个 state_charge 停，未执行后半断言；24 案证据来自分案捕获和观察断言，不来自该早停脚本后半段。

**最低修复：**把现成完整事件 ledger 校验接入新搜索实际消费入口，覆盖 first complete、B4、done/已有 commit 幂等返回、实际复用提交结果；同时校验本 action 必需 attempt/预约/提交记录的存在、归属、版本、状态、内容与冻结引用。事件 outcome 不能空/不存在/错绑；非事件合法 outcome 按其实际契约校验，不给无关 decide 强加 event。不能用 get 视图、put 无异常或索引相等当证书；不能猜补坏行/用新 hash 洗旧账。

**最低验收：**上述分案均在坏对象首次消费前结构化失败、保全、无该坏 action 的补账/consume/成功确认；12×2 坏权威案、缺 attempt/预约、不存在/异父 event 逐案验证。合法首次完成/B4/done 重放仍幂等、一次补账，raw 正常首提仍拒。同规则入口共用验证，允许提取只读校验，不要求新机制库、来源真实性认证或整库抗一致重造。

### S3A-03：已执行额度可退还；搜索策略首消费未验范围/类型

**对应 §4.2 十上限、预约/consume/release/E04、§3 第5条策略身份。** `defer_action`（:1269–1313）把 claimed 直接当作未执行，释放全部 reserved、abandon attempt，不查实际 event/请求/执行记录。

先正常 `submit_action_event` 留下 event，再 defer，可以把总 action/备选/attempt 额度都退掉。加强的完整公开链把 `max_total_search_actions=1`、同父备选上限=1，重复提交→defer 三个不同合法备选，最终 **event=3、attempt=3，而两项预算 used=0**。没有模型/网络调用。未执行 defer 的合法释放正控保持。

另五案直接提交由合法 profile 块单改 search_limits 的策略。现成 profile builder 拒绝 max_total=1001、bool True、未知键、-1；`register_search_run`（:443）却全收。前三种还可 claim；bool 被 int 转为 1，越界 snapshot max=1001；负数已写入，随后仅按额度不足拒 claim。`_limits`（:482）只取 JSON，不复用现成配置校验。这是适用入口缺校验，不需重造十键或范围。

证据：`search_specialist/defer_bypass_observation.json` 及完整重复账表，`observations.json` 的 executed/unexecuted defer；`root_probes/policy_probe.stdout.jsonl`、`.run.json`。

**最低修复：**释放必须消费“确实未执行”的持久事实，已提交 event/已发送或已执行操作不能以 defer 退已用额度；悬空/失败真实请求继续占登记额度，合法未执行预约可释放。注册与后续读取/恢复实际消费配置用同源类型、范围、键、版本验证，拒坏块在写入/执行之前，不借 int coercion 接受 bool。保持现成十上限单位及适用资源判定。

**最低验收：**上限 1 的完整链无法留下三个已执行 event 却 used=0；实际执行次数与预算源记录可逐步复算，恢复不重复扣。五策略案合法通过、四非法入口拒且无写入；默认 real=0/off 仍允纯规则/scripted、检索/转换/深度/产品宽度按各自资源正负控；未执行 defer 合法释放。不要全面拒绝 defer 或看任一资源=0 全局停。

### S3A-04：请求同键异内容成功复用，未核合法执行引用和生命周期

**对应 §4.1 同键异内容冲突、§4.3 单认领执行权、§4.4 B2 请求权威。** `register_model_request`（:863–949）用 run/attempt/provider/key 生 ID；已有 row 立即 unchanged，未比较 payload_hash、action、purpose/retry 等内容，也不核新请求的 action/attempt 存在、归属及状态。record_request_sent/response/failed（:955/:985/:1009）仅核请求本身 status。

主审逐案实证：

- 同键换 payload、换 purpose、改成另一个合法 claimed action 并复用旧 attempt，均成功返回旧 request，没有冲突。
- 未 claim action、不存在 action、foreign/missing attempt，仍可新增 `provider_kind=real` 登记及已占额度的预约行；**只登记，不发送，实际网络 0**。
- 改已存 payload_hash 为 64 个 0，再拿原始正确 payload 注册，仍 unchanged；recover 也只把它当普通 pending。入口已有真实 payload 时没有比对是可执行事实；不要求仅凭 digest 在缺原载荷时凭空重算。
- 合法 scripted 请求注册后 action defer/attempt abandon/退预约，仍可记录 sent；失效执行引用没有被核。合法 scripted sent→responded（网络 0）和 real 预算 0 拒且零写入的正控保持。

证据：`root_probes/request_probe.stdout.jsonl` 全 11 案原输入、前后各表与返回；`.run.json` 实际命令/源码元数据；`assert_root_observed.py` 只读断言。

**最低修复：**定义并共用请求内容与冻结归属校验，同键只有同内容才能幂等，异内容结构化冲突且不写；登记/已有请求复用/发送/响应/失败/恢复在各适用消费口核合法 run、action、attempt、策略、生命周期与执行权，不能消费不存在/异属/已失效引用。decide/retrieve 若契约允许空语义 attempt，应保留其合法 action 驱动路径，不对无关 action 强加 expand attempt；没有 worker 参数的公共口也不能成为绕过认领的捷径。陈旧 worker、显式 retry 和 request 状态迁移须有明确可验证规则。

**最低验收：**逐一拒上述异内容/非法引用、损坏 hash 的同载荷重用与已释放执行权继续发送；坏案零新 request/consume/status 成功写入。合法同键重复零新增、合法 scoped action/attempt/request 完整链、空 attempt 适用正控、显式 retry 新 ID/占剩余预算、悬空不默发、真实请求 0 拒、scripted 网络 0 均保持。这里要求账目与执行协议，不要求实现真实 provider 或外部 exactly-once。

### S3A-05：H05 报告漏掉正在执行的 action

**对应 §4.2 停止原因/未探索集合及 §7 H05。** `stop_report`（:1352–1435）只计 pending/deferred/blocked/pending requests，不计 claimed/open attempt。

默认预算有余，只 claim 一个有效 action、没有请求：recover 明示 B1 awaiting completion；stop_report 却返回 **`primary=exhausted_search`，unexplored 所有计数为 0**。已经有实际持久的未完成工作，不是缺 S3b 调度的猜想。证据：`search_specialist/observations.json` 的 claimed 停止案及完整预算/rows/report。

**最低修复：**停止报告包含 claimed/inflight/open attempt 及适用持久未完成操作，exhaustion 前提不得漏掉它们。仍执行时可以 primary=None 或登记准确等待语义；保留六原因优先级及同时成立原因，不把停止升级为污染物终点。

**最低验收：**claimed 有余案例不 exhausted，机器披露未完成对象/数量；完成后或真正空 run 的合法 exhaustion、pending/deferred/blocked/悬空请求、user_stop 和独立零预算/零深度/空池控制保持。无需提前实现 S3b 队列选择。

## 5. mimo v9 九条件与待执行声明的有限裁定

| 条件 | 当前裁定/下轮落字 |
| --- | --- |
| ① 双包装点 + reason.kind 读法 | 当前 factory/恢复/writer 分案支持；canonical+r 的内因是 unregistered_cx_class，真坏串内因是 unparseable_smiles。补读法 P2，不能用外层名作全称化学判断 |
| ② r 接受/拒绝都不认证分析事实 | 同意输入表示契约范围。当前 RDKit 直接解析 CCO\|r\| 能输出 CCO，说明守卫拒绝不能反推样品；正控接受亦不证纯度。补对称文字 |
| ③ 同源确定性拒篡改，非独立复核 | 同意；v9 已有与工厂一致/非独立双算，可补不豁免必要入口。不能改成两个独立算法互证 |
| ④ 搜索继承验证不认证真实来源/稳定性 | 化学边界同意；但 v9“搜索不存在绕过验证”全称被新 B4/done 证据反驳。随 P1-02 修复改成实际入口证据，不再用 submit_event 两处调用证明恢复全覆盖 |
| **⑤ 键断裂/电子去向句实际归属规则正文** | **已落地**：当前 v9 判据三正文已有“本许可不区分该参与物的键断裂方式与电子去向”，声明归属许可定义/规则，代码 scope 未改。本批草案未冻结；不因为 mimo 提“冻结正文”新增冻结门 |
| ⑥ 恒入≠适用及真值表 | 现有三条件成立；纠正 mimo 精度：实际枚举是 partial_unchecked_transformation，不是 partial；uncovered+partial 也可能含 coefficient_binding_mismatch，不能一律称许可本身判负，须读 coverage_violations；unknown_coefficients 等早退不应称已使用许可。P2，无新机制 |
| ⑦ 内容改变要新 context_id/保留链 | 与继承契约方向一致；不是禁止合法重建新内容。S3b 消费接线保持，不强加 S3a 新调度 |
| ⑧ converter 缺 scope/proof → unknown | 本轮直接执行成立：三 None、diagnostic.center_evidence={}、converter 元数据/center_match=None，公共 audit 中 center_checker_scope_unknown。可精确落字 |
| ⑨ caller 逃逸与宽捕获负控，未闭合措辞 | S3a 源码无生产 caller，未闭合披露属实且可接受；S3b 必须证明异常中止本次成功 admission/submit，并有宽捕获反例。不是全面禁止 except Exception 的新框架门 |

本轮静态核验：全 src 10 个 AuditContractError 抛点无 enclosing broad-catch try-body，specific `except AuditContractError` 为 0；audit_hypothesis 生产 caller 为 0，check_edit_against_donor 唯一源内调用是复算链且无 try 祖先。它们是当前源码静态证据，不是未来 caller 动态安全证书。旧 test_f11 未完整断言三个 None/空 diagnostic，本轮独立公共探针已完整钉住；可在新回归补断言，不升另一个 P1。

mimo 待执行清单对应：全量/基线/G01 已按 §2 执行；raw 篡改公共搜索首提另证零全表变化；四硬杀/barrier/零资源/H05–H08 已执行但发现 §4 残余，不能统称完整通过；锁 RDKit 小 CX 矩阵和原 R8 retained6/removed3 9 案当前往返保持；广捕获关系用 AST 核验；失败 None→converter→audit 的 unknown 用实际公共调用验证。没有把读码、测试存在或旧声明当当前执行。

chemstate/audit/path_context/hypothesis/events 五源与父提交字节相同，hash 留存。R8 认可的 R6 五组及 R7 两项关闭继续保持；只分段复核必要 CX/失败控制，不冒称再跑全部 R8 永久脚本，也不要求未登记 CX 形全部支持。判据二 D/T 入 H、自由基电子不计账、数值闭合非机制证明的已披露边界不变。

## 6. 交付一致性、P2 与本审准备修正

可证的交付：594、58、1196/8/17；基本独立硬杀恢复与认领；profile/store/search 升位登记；runner start/resume 对 PPV1 仍 fail-closed；S3b 未实现逐项明列；R8 八项文档同步与 canonical 错误措辞、14 红不是 14 旧 R6、化学旧 assert 停在 55/57 等已在新请求/交付书登记，历史只读。

需要更正的结论范围：§6 B3“验身份后消费”只验了自洽部分；B4“完整权威”“done 验证”实际只看索引；§8 矩阵逐行绿未覆盖本报告公共链反例；defer“未执行预约释放”没有先核未执行事实；停止“耗尽”遗漏 claimed。这些对应 §4 P1，不可仅修宣传文字。

其他 P2/后续：

1. 交付 §1 recover 写 12，当前实际 13；基线 delivered_stages 后半未执行，不独立报红。
2. `reopen_of` 可省略，max_reopens=0 下同假设不同 revision 仍能安排多次 attempt，计数不进入 reopens；有限 attempt/action 上限仍在。生产“无新信息重开”触发语义属于 S3b，本批只明确 trusted caller 标记边界，不凭未传 trigger 就断言每次都是无新信息；S3b 必须消费真实 trigger/revision/重开规则。
3. v9 化学请求不少“同 v7/v8”“1–4 同 v8”缩写，严格自包含不足；下一请求展开必要规则，不让外部评审依赖历史补齐。这是文档交付精度，不新增化学功能门。
4. legacy code_identity 聚合父为 `5e8761c91d355f66ba81dfd80e6c3203b526d7ae4f2845baeaaa46b2246bf3a3`，当前 `4ea99b698a05ab8685bbd5687835043a2bf07f0c7f219591beccbff2507c29ae`，仅 runner.py 共享拒绝文案/detail 字节差异；排除 `_refuse_undelivered_profile` 后 AST 全同。跨提交合成旧 identity 的 resume 被既有 code_identity 门拒，交付已披露；不称跨提交恢复仍兼容。当前 legacy 运行行为由安全 G01 支持，证明限度分开。
5. 生产 caller 吞异常义务仍留 S3b，S3a 没有 caller 不新增阶段门；license_applied/顶层展示、机制认证、科学性能仍后续。

审核自写夹具的准备错误完整保留，未修改生产代码绕错：

- 搜索首脚本将异常名断言写为 LedgerCorrupt，实际 Ppv1LedgerCorrupt；9 行后早停。新隔离目录仅改类名，完整 16 案；原脚本/stdout/stderr 保留。
- 四硬杀控制器首次遗漏父侧 GO 写入；四崩溃已完成，双 worker ready 等待。实际父侧续接在双 ready 后写一次 GO，H06 完成，原体和续接 metadata 保留；便携控制器只内联同一步，未另跑全四崩溃。
- 继承首脚本误调用 PathwayEvent.to_dict，零 case JSONL；改用 asdict 记录，另目录完整 27 案。化学首脚本 14 案后 AST literal_eval 遇版本 Name 失败，两自写 DAT 尾字段错误被正确拒；修审核输入为已登记语法/忽略版本引用后，另目录完整 15 案；原错误脚本从编辑历史重构，明确不假称执行前冻结。
- 所有新归档便携控制器仅作语法/安全检查，实际执行是原脚本及分段日志。整理期间不重复全量/基线/G01，证据分别标实际执行、观察断言与便携模板。

## 7. 本批放行条件与下一批边界

**本轮不放行。** 下一轮先闭合 §4 五组入口矩阵，逐案行为修复、合法控制和诚实 unknown/partial 保持，PPV1 全量/安全 G01/四硬杀/barrier/H05–H08 不回退，文档与实际链相符，证据完整后再裁定 S3a→S3b。测试数可以随新回归增加，不锁死 594/1196；红绿必须按实际分类。

本报告不要求重开 S0–S2、不增加新化学机制/冻结/性能门。S3b 的有限范围仍是原任务书 §5/§6/§7 b 行：队列与两个 deferred、条件/依赖和场景转换、模型协议与有限反馈、固定工具中心证据生产链、公开 PPV1 分流与完整集成。S3a 尚未通过，主会话先派单个实施 agent 回修底座，不提前解开 runner。

## 8. 下轮有限范围实施提示词

> 以下可直接交单个实施 agent；详细反例输入在本报告永久证据中。只读旧证据，先复制到新 tmp，禁止原地建库。

你负责回修 pollutant_pathway_v1 S3a，不实施 S3b。仓库只用 `/Volumes/CC/Enzyme_Agent/dependingv43`，基线 `9b78f4279cc6fa50b3b51c31a5c8e07abbeda207`。先读当前 AGENTS.md、`/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S3_IMPLEMENTATION_TASK_2026-10-07.md` 的 a 批契约、本报告 §4/§7，以及 `/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/ppv1_s3a_codex_2026-10-07/README.md`。固定回修只有 S3A-01～05：

1. B3 与所有适用输出入口共用完整 action/attempt/task/event 绑定，四类异身份在任何消费/写账前拒；合法同 output 一次提交和 artifact 保全保持。
2. 首次 complete、B4、done/已有提交结果复用用完整权威校验，不能 get 索引即成功；核实际必需搜索 attempt/预约/commit 引用。12×2 坏事件账、缺引用、空/缺失/异父 event 均零成功消费/补账；合法非事件 outcome 按适用契约保留。
3. defer 先核未执行事实，禁止用已提交/已执行工作退还已用预算；保留未执行释放、失败/悬空真实请求占额。注册/读取/恢复策略共用现成十键类型/范围/版本校验，四非法策略在首次消费拒。逐步复算上限 1 连用反例，不能全面拒绝合法路径。
4. 请求身份与执行引用闭合：同键异 payload/purpose/action/其他身份内容冲突；登记、复用、状态消费、恢复核合法 run/action/适用 attempt/执行权/生命周期。保留非 expand 的合法空 attempt、scripted/fake 网络 0、显式 retry、新 request 占剩余额度、悬空不默发、真实预算 0/off。
5. H05 披露 claimed/inflight/open attempt，执行未完成不能 exhausted_search；现成六原因顺序、独立零资源/空池/user_stop/deferred/真正完成/空 run 正控保持。

开工先列适用 enqueue/claim/request/write_bundle/submit/complete/defer/replay/recover/budget/stop 入口矩阵，标消费对象、身份、版本、权威及校验来源；同规则共用校验，只给适用入口要求，别追单例补丁。坏单案消费前拒、保全且无该动作新成功写账；不能重建新 ID 洗损坏，不能静默猜修库。保留 R8 认可的 R6 五组及 R7 两项、正常 raw 守卫、合法不同 parent/context、unknown/partial，runner 双入口继续拒 PPV1；冻结 legacy/G2/AtomTool 行为不改。

先固定合法及坏输入，再写正确行为回归；在直接父基线 9b78f42 detached worktree 的隔离 source 跑同字节新回归，登记每项行为红、正控绿、collection/字段/表缺失及未执行内部段。原 00e509a 的初次 S3a 缺模块对照保留历史，不拿它替代回修行为红。永久旧 observed 断言钉住修前缺口，修后预期失败，分段 capture/新合同断言验证翻转；不修改旧证据来凑通过。

复跑 PPV1 全量与新当前 source/白名单安全 G01，逐项列 8 缺席依赖与 17 排除，按实际变化登记，不拿旧数字顶替、不补读禁区。四硬杀恢复/双进程 barrier、各预算适用资源、合法幂等/陈旧执行权/坏账/H07/H08/H05 同一矩阵自审。收口不加 S3b、外部 exactly-once、机制库或科学性能门。

新交付书逐 P1 给入口→行为→证据、红绿分类、预算账、语义/version/身份影响、完成/未完成清单。将 §5/§6 P2 精度合并落新文档，尤其 mimo⑥不能照抄 partial=许可判负；mimo⑤已在规则正文、不再次要求改代码 scope；生产 caller 未闭合仍留 S3b。下一 mimo 请求按真实轮序 v10，展开自包含必要规则、无金标，只读/执行声明待验证；由主会话送审，实施 agent 不调用模型。

用新 `docs/review_evidence/ppv1_s3_impl_<实际日期>/s3a_<新轮次>/` 冻结本轮脚本、全部合成输入输出/前后表、stdout/stderr/JUnit、实际 HEAD/schema/argv/env/耗时、manifest+SHA-256（含嵌套清单），不覆盖旧目录、不在永久证据原地执行。dependingv43/v4.3 本地提交，git add 显式路径，不 push；既存用户 AGENTS 差异、未跟踪评审文件/证据不带入。严禁真实金标、题面、封存逐题 run、dependingv4、外模和真实付费 provider；判分零 LLM。
