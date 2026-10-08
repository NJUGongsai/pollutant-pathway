# S3b 队列与公开恢复独立专项（2026-10-08）

结论：S3b 当前公开入口未达到完整 S3 验收；下列五组均来自既定任务书，不要求真实 provider、机制库、科学性能或外部 exactly-once。S3a 已关闭的底座反例不重开；cache_hit 同构边界沿 R4 既有 P2 裁定保持。

## 1. 实际输入、范围与执行纪律

实际 HEAD：`c1211183c0874b12c5b5461845d3c61f0a84719c`；父 `b7f2bba02ca49edd0a45a13bc9b8434909d99175`。源、vendor、pyproject 完整复制到新 `/private/tmp/ppv1_s3b_queue_vd18_t4h`，所有子进程运行 depending43 的 Python 3.11.16，`-B`、`PYTHONDONTWRITEBYTECODE=1`，未运行 pytest。全部是合成 CCO→CC=O 等规则级输入，模型为 scripted/off（只有默认 0 额度 real 登记拒绝控），无 provider/network 调用；资产与 v3 根显式指向 scratch 内不存在的目录，只走 scripted identity，未访问任何真实评价、题面、封存 run 或 dependingv4。

执行顺序：`scripts/probe_public.py` 一次、`scripts/probe_supplemental.py` 一次。前者在最后一个低层 distinct-worker barrier 的输出收集处遇空 stdout 抛 `IndexError`（exit 1），前面 34 顶层观察、全部子输入输出与表仍保存；后者只补未完成 capture、新 public same-action resume 控制、计划内两类 deferred/格式反馈，以及此前未触发的多产品 fault 注入，不重跑已完成正控。此轮无账号用量中断。

本专项不跑 PPV1/G01 全量，不将根专项工程数字当本地计数；也不复跑化学中心异常专项。40 个顶层观察记录不是“40 tests passed”：raw `observed_check` 某些用于验证缺口确实发生，两个 H07 负控为 false 正是坏输入后仍产生事件；一个原 fault 未触发、一个 distinct-worker barrier 为有限 capture，必须按下文裁定读取。

## 2. S3B-01：恢复消费了未冻结的 plan / pool

来源：任务书 §4.1（frozen_pool、上下文及相关版本绑任务键）、§4.4 B1（不按当前输入重算任务身份）、§6.2（保存池、恢复不重建/覆盖输入）、§7 E03。公共链：`workflow.runner.start_run/resume_run` → runflow。

- `frozen_plan_same`：B1 root retrieve 已认领硬杀，新进程恢复相同 plan，1 事件，合法控制。
- `frozen_plan_omitted`：同样边界不传 plan，恢复被接受；历史 retrieve 的 `task_key` 保持，原计划 donor-B 被变成空池 no_local_candidate，0 事件。
- `frozen_plan_changed`：同样边界把 B 换成 X，恢复被接受；历史 action/task_key 保持，但记录并提交 donor-X。
- `frozen_plan_decide_changed`：retrieve 已完成、decide 的 frozen `pool_digest/task_key` 已持久化后硬杀，恢复换 plan 为 X，也接受并提交 donor-X。不是单纯尚未检索时新增一个合法新池。

代码：runflow `start_ppv1_run` 961–999 只将 `_plan_digest` 嵌根 task key，不保存可复用完整 plan；resume 1048–1066 核 code/profile 等后，将调用时 `plan or {}` 直接给 Driver；`_pool_for` 394–406 与 `_run_decide` 411–430 从此 plan 重取 specs，不对照既有 pool_digest；prompt_version 亦取本次 plan 摘要。

证据：`inputs/frozen_plan_*_{start,resume}.json`、对应 `logs/*.execution.json`、`tables/*.json`，每案的历史/恢复 action、hypothesis/event 与完整持久表均保存。

最低收口：plan/冻结池和实际任务输入持久化并内容绑定；resume 无 plan 应沿已冻输入，若必须外部再供，应明确契约且在任何恢复/认领/请求/事件消费前验证同一内容，差异结构化拒绝或显式新 revision 新任务，不复用旧 task 消费新 specs。保持同计划 B1/B3/B4 成功与零重复预算。

## 3. S3B-02：H07 发现坏 bundle 后公开 driver 重新执行

来源：任务书 §4.4 B3/H07，§3 首消费失败不洗坏权威。独立负控分别改变 `search_commit_bundle.json` payload 而不改 hash，或写不可解析 `{not-json`。

`public_artifact_hash_bad` / `public_artifact_json_bad`：起始事件 0、commit 2、预约 7。新进程公共 resume 的 recover_run 明确报告 `SearchArtifactIntegrityError`，kind 分别为 `artifact_hash_mismatch` / `artifact_unparseable`，坏原文件逐字保全；但 resume 继续 Driver，claimed expand 被同 owner reclaim 并执行，结束 **1 事件、4 commit、10 预约**，不是隔离该 action。原 harness 要求拒绝且零成功写入，因此两案 `observed_check=false`，没有改写成通过。

代码：search `recover_run` 2999–3024 将坏 artifact 写为 action disposition；runflow 1061–1066 未消费 disposition 决定能否驱动；`_inflight_action_ids` 255–266 仍选择同逻辑 owner 的 claimed 行，`drive` 286–319 分发生产展开。即使坏原文件没覆盖，也已违反“不静默跳过/不重跑”。

合法控制：`crash_after_bundle_written` 正常 B3 同 output 在新进程公共恢复后事件仅一次，4 commits；再恢复 counters 不增。`public_event_ledger_bad`（B4 权威行 context_hash 变坏）公共恢复拒绝，0 新表数量变化、事件坏行保全，保持 H08。

最低收口：把 recovery 的结构化失败消费到恢复 admission；该 action 禁止 reclaim/工具重算/假设或 event 成功提交。允许合规地隔离失败 action、披露阻塞后处理独立合法分支，但不能把旧坏输出洗成新的成功。合法 B3/B4 与输入文件保全保持。

## 4. S3B-03：B4 没有闭合完整产物 followup / 转换集合

来源：任务书 §4.4 第四崩溃（事件/产品扩展不重复，完整权威决定剩余状态）、§5.1 完整 coproduct/followup、§5.2 显式转换只后效、§7 场景转换。

### 4.1 三产品部分调度

`three_products_normal`：事件 participants 与 expansion_plan 有三个产品（CC=O、[H][H]、O），width=3，三条 followup retrieve 正常存在。

`three_products_after_two_corrected`：公开 start 的第二条 followup 插入已提交后 `os._exit(77)`，新进程公共 resume。事件/plan 仍三产品，但最终只两条 followup；O 的 `cs_c4694f2e93d5c4e7d51f` 消失于搜索队列，未做 deferred/not_tracked 处置。起始事件 1/commit 3/action 5，恢复结束仍事件1/action5、commit5（正常三产品是 action6/commit6）。这是已承诺扩展对象丢失，不是要求搜索科学完备。

原 `three_products_after_two_followups` 注入条件误用了 enqueue 外层 source_event_id（实际在 payload），未触发而正常结束。原输入、输出与该失效必须保留，不作为 B4 fault 证据。补脚本只修此 runtime fault hook，fresh 新 run、新标签，合法已成控制不重跑。

代码：runflow `reconcile_followups` 221–226 以 `payload LIKE %eventid%` 的数量 >1 判“完成”而不核对 expected distinct product/action/context 集合；两条实际 followup 达此门槛，第三条直接遗漏。

### 4.2 显式转换中断

同一个携 `user:switch`→phase-1/scenario-new 的计划：

- `transition_normal`：1 done transition，followup phase-1。
- `transition_after_transition_enqueued_before_attach`：转换 action 入队后、pending_followup 附加前硬杀，恢复 1 done transition，但 followup **phase-0**。转换已经执行，后续仍消费旧 context。
- `transition_after_event_submitted`：标准 B4 边界在 event 提交后硬杀，恢复 **0 transition action**，followup phase-0。原 plan 即使重新提供，B4 补调度没有消费原显式转换指令。

代码：正常 `_run_expand` 701–740 先 enqueue transition 后另一次 UPDATE `_attach_followup_to_transition` 748–774；B4 reconcile 242–253 直接用事件 action 的旧 context，并不会恢复原转换意图/附随关系。不是“旧边评估被重写”，而是已明示的后效上下文/转换动作丢失。

最低收口：恢复按权威事件、完整 expansion_plan、已冻结转换意图和必要附随关系逐对象幂等补齐；不用模糊字符串计数证明集合完整；事件后未入队、只入队未附随、部分多产品 followup、转换后尚未结算均有限注入验收。原 event/participants/history 不改写，预约不重扣，合法不转换/合法转换与宽度 deferred 保持。

## 5. S3B-04：两个公共 resume 同 action 实际双执行

来源：任务书 §4.3/H06/§7，只有一个当前执行者；与外部 exactly-once、恶意 SQL 注入无关。

`public_concurrent_resume`：公开 start 取得 expand 的 action/attempt/预约后硬杀；两个新进程同时调用 **workflow.runner.resume_run**。在 `_run_expand` 入口 barrier，两者都持同 `sact_2bd9e95396a8184dba52`、同 `sattempt_ea6eaa197af10e2b5c7f` 和同 `ppv1-driver:public_concurrent_resume`。两个 PID 21506/21507 放行后都真实调用 `production.execute_atomtool_expansion`（两份 `tool_entered.json`）。结束幂等事件1/commit4，但其中一方生产 artifact 冲突 exit3，另一方0。最终写账幂等不等于只有一方执行。

代码：runflow `_worker_id` 149–152 给所有进程同一个 owner；search `claim_action` 1156–1167 将同 owner 认领视为 `reclaimed_by_owner/claimed=True`；resume 不持进程执行独占，Drive 两进程均调生产工具。

合法控制：`barrier_start` 两进程 barrier public start 原子目录唯一胜者、事件1；四硬杀单恢复继续成功。low-level distinct worker barrier 有 first 已被 second 认领而拒的持久行/预约及 stderr，但原控制器收集 first 空stdout时报错，second pipe 未完整归档，不冒称它是完整公开双执行证书。

最低收口：实际公开 start/resume 消费者具互斥执行权或可验证恢复移交，同 action 同时只一方进入请求/真实工具/成功提交；合法崩溃后单个新进程能沿原 task/attempt/预约恢复。测试须两个独立公开 resume 进程＋被动计数/barrier，不用只有 start 目录单胜或最终 event1 替代。

## 6. S3B-05：模型 novel 消费没有接成独立假设链

来源：任务书 §5.3（proposals[] 每项独立假设、novel 可池外，参与物/来源/条件/依赖沿既有契约；空池仍可组装独立底物档案）和 §7 模型协议行 `parse→冻结假设→固定工具/审核`。

- `model_novel_nonempty`：protocol 合法 novel ID+proposal_context（明确 novel_outside_pool），解析计数1，实际 schedule/工具/event 只处理原 donor-B，没有 novel hypothesis/action、没有 novel 参与物/条件/依赖审查。
- `model_novel_empty`：空池且已有 scripted novel 响应，公共 start 在 retrieve 直接 no_local_candidate；model request 0、hypothesis0，不进入新模型提案组装。
- parser 当前只承载 novel ID/context，可附 reaction_spec 等字段却不传给消费者；不是 missing scientific mechanism，也不是只缺文字。mimo r13 对消费者未实现的读码披露与本地执行一致。
- `model_abstain`：合法 proposals=[] 不异常，仍处理既有规则池，记 abstained=True。本专项不自创“模型弃权必须强制停止规则池”的约定，因此只登记此观察，不另增弃权阻塞。

代码：runflow 347–361 空池先返回；420–430 全来自 frozen specs；533–606 的 parse 结果只转 rank_by_key/计数/弃权，449–490 构建 schedule 条目未消费 novel；model_protocol 145–191 丢除 ID、context、coproducts 以外内容，现协议本身也缺完整 novel 假设承载。

最低收口：明确并实现完整 novel 合成输入/模型提案载荷，沿既有状态/假设/参与物/条件/依赖与出处身份验证，分别进入有界调度和真实工具→audit→admission→submit；空池可组装并消费合法空/novel响应。合法空列表、frozen-ID引用、非法结构/池外引用守卫保持；不启用 chemical_reproposal、不发真实 provider/费用试验。

## 7. 正控、文字精度和未扩大裁定

- E01 首选后续无候选仍保留 B/C 两事件与两个 recorded attempt，各有源事件 unresolved_continuation。
- C06/H04 missing→unresolved_initial_supply，supported→supported，两个公共真实事件可留 retain_conditional/R5（不授 R6）；essential conflict 保假设、零 event；分支 requirements 上下文隔离。
- E02 公共 start→public queue activate_deferred→公开 resume：错类型/旧 revision/错 trigger 不激活，两类分别激活且重复幂等；alternative预算不足保持独立未展开原因；完整事件产品不截断。
- 四个支持的崩溃边界硬杀均经新进程 workflow.runner.resume_run，合法各保持事件/请求/预约幂等；B2 scripted 登记1，无第二登记、网络0，pending 披露。此范围不能外推外部 provider exactly-once。
- H07/H08 结论分开：H08坏权威拒保持；H07低层认坏保持但生产恢复绕过失败，为上述 P1。
- public `zero_depth` 只证明深度0阻展开（0 events）；stop 却只 budget_limit，other_reasons=[]、unexplored.blocked=0，schedule outcome blocked=1。H05 原门要求同时原因/未探索对象，不应称公开 H05 全闭合。该已有输出交根裁定入有限消费者回修范围；本专项不追加新探针。
- `feedback_valid` 已有一次格式修复持久2请求、1事件、网络0，反馈轮计数合法；requests均 registered，pending_requests2。只登记真实状态边界，不把“parsed response 已闭合”作为已证事实。
- 无真实 provider/资产/金标/题面/封存读取，科学性能 pending；无 src/tests/AGENTS/既有docs修改，没有git commit/push。
