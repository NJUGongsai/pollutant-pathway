# T-F 位次传递核查：首位候选折叠后位次传递的夹具证据链核对（2026-10-16/17）

> 题域标签：**298 = RHEA 通用酶学/已见题**（chain13 批）。探针 ≠ 预注册 ≠ 成绩。
> 口径声明：本文件是**证据评估记录**——只核「哪份产物 / 哪个脚本 / 什么数据 / 什么判据
> 支撑哪条结论」以及「证据覆盖是否包含被核分支」。**全文不做源码有无缺陷的断言、
> 不给修复方案、不扩大工程范围**（老师拿本记录配后续专项合成验证自行裁定）。
> 判据/数字只在本批 298 题域内成立，不外推。

## 0. 一句话结论

1. **「被折叠的模型首位」在 chain13 本批 298 题里出现 0 次（0/298）** ⇒ 「首位被折叠后
   位次如何传递（其余候选是否继承/丢失）」这一分支在本批夹具上**零覆盖**。因此三项
   背景结论中的「折叠丢位 0」应读作**「该分支在本批未被触发」**，不能读作「该分支的
   行为已被实测证实无丢位」；其余两项（8+32 题首位=首事件、微秒碰撞 0）本核查可
   独立复算且与审计产物逐项一致。
2. 代码路径上「位次传递」的实现语义是**去重保留先出现者 + 紧凑化 + 不继承**：折叠只
   移除被折叠条目自身的位次；幸存者保留**自己的**声明位次；其余候选整体上移一格、
   相对次序不变；幸存者若本来没有显式声明位次，则落到 `deterministic_fallback`
   （排在全部显式位次之后）。chain13 实测 3 次折叠的幸存者**全部**为
   `model_selection`（有显式位次），**0 例**退到 fallback。
3. P0② 审计只读取**decide 层**的折叠表（`dedup_rejections`）；本核查另测出两个
   **未被该审计读取的位次/折叠入口**：池装配（build）侧折叠 **41 题 / 50 次**（发生在
   模型 rank 产生之前，无位次继承语义）与报告投影位次面（1443 条投影）。

## 1. 核查对象与依据（自包含）

被核的三项背景结论出自：`reports/ppv1_s5b/p0_rank_audit_2026-10-15/`
（`rank_audit.py` / `rank_audit_data.json` / `rank_audit_summary.md`）与
`docs/P0_TRIO_VERDICT_2026-10-15.md`；任务书先例 `docs/TASK_P0_RANK_AUDIT_CHAIN13_2026-10-15.md`。

| # | 背景结论（原文口径） | 出处 |
|---|---|---|
| ① | 「折叠丢位 0 题」（GPT 条件性推演风险实测为「否」；2 题去重折叠、3 次折叠事件） | summary §四 + `rank_audit_data.json → fold_rank_loss_verdict` |
| ② | 「hit@1 掉出第一的 8 题 + strict rank>1 的 32 题**全部**『模型第一名已是首事件』」 | summary §五/§六 + `focus_group_1_lost_to_rank_gt1` / `focus_group_2_rerank_space` |
| ③ | 「微秒碰撞 0」 | summary §七 + `microsecond_collision` |

被核问题（老师要求 #6 行）：核对「**首位候选被折叠后的位次传递**」的夹具证据链。
本单**不做**专项合成验证（明确留给后续另一步）。

## 2. 读码定位：位次传递的代码路径（`file:line` 级）

以下行号均为当前 HEAD `3440ca7`（`src/pathway_v43/`）。

### 2.1 唯一构建点：`decide` 内的位次分配（runflow.py）

| 步 | 位置 | 逻辑摘要 |
|---|---|---|
| 1 | `pollutant/runflow.py:871-879` | 装配 `prepared_entries`：**先池条目**（按 `plan.pools` 声明序），每条的键 = 池 spec `key` |
| 2 | `pollutant/runflow.py:923-959` | 模型 novel 提案逐条预校验（`928-937`：`validate_edits` 不过 ⇒ 进 `novel_rejections` 并 `continue`，不入池）→ `prepare_hypothesis` → **后接** `prepared_entries`（`958`），键 = 模型自报 `hypothesis_id`（如 `novel-1`） |
| 3 | `pollutant/runflow.py:998-1014` | **净反应签名去重**（`s5b_compiler.net_reaction_signature`，`996` 导入）：按 `prepared_entries` 顺序遍历，签名已见 ⇒ 后到条目进 `dedup_rejections{logical_proposal_id, merged_into, signature}` 并 `continue`（`1005-1008`）；**先出现者（幸存者）保留**（`1010-1011`），末尾 `prepared_entries = deduped_entries`（`1012`） |
| 4 | `pollutant/runflow.py:1015-1017` | `model_rank_by_key` 用**幸存键集合**过滤显式 rank：被折叠条目的声明位次**在此丢弃**（无任何字段承接） |
| 5 | `pollutant/runflow.py:1021-1030` | novel 条目的位次从原始 ID 表 `model_rank_by_id` **按自身键**回补（`1029-1030`）；回补的是**自己的**声明位次，不是被折叠条目的 |
| 6 | `pollutant/runflow.py:1031-1039` | 幸存显式 rank 键按 `(声明位次, 键名)` 升序 → **密集重编号** `effective_rank = 1..n`，`rank_basis="model_selection"`（即「紧凑化」：被折叠条目消失后，其后的候选**整体上移**） |
| 7 | `pollutant/runflow.py:1040-1045` | 未获显式 rank 的条目 → `effective_rank` 接在其后，`rank_basis="deterministic_fallback"`（**排全部显式位次之后**） |
| 8 | `pollutant/runflow.py:1059` | 入队位次 `rank = effective_rank_by_key.get(key, index + 1)`（兜底为池内下标 +1，正常路径不触发） |
| 9 | `pollutant/runflow.py:1070-1092` | 位次事实落**冻结任务载荷**：`logical_proposal_id` / `prepared_hypothesis_id` / `net_reaction_signature` / `model_rank` / `effective_rank` / `rank_basis` / `rank_policy_version`（`S5B_RANK_POLICY_VERSION="s5b-rank-policy-1"`，`runflow.py:203-205`） |
| 10 | `pollutant/runflow.py:1102-1111` | `schedule_hypotheses(...)` 按上述 `rank` 入队；outcome 把 `model_note`（含 `dedup_rejections`、`model_rank_by_id`、`novel_rejections`；**排除** `rank_by_key`）落账（`1112-1121`） |
| 11 | `pollutant/runflow.py:1271-1288` | 位次事实的来源：`rank_by_key`（`prepared_hypothesis_id → 出现序`）与原始 ID 表 `model_rank_by_id`（`1286-1288`） |

**读码结论（实现语义，非缺陷断言）**：

- **没有任何「位次继承」代码**：被折叠条目的 `model_rank` 在被折叠的那一刻从 rank 表
  消失（步 4 的幸存键过滤），不存在把该位次转给幸存者的赋值；幸存者拿的是自己的位次。
- **折叠对幸存者的位次效果分两种**：① 幸存者有显式声明位次 ⇒ 保留自己的位次、并因
  紧凑化可能**上移**（后文 §4 实测 3 例：声明位次 3/4/6 → 生效 2/3/4）；
  ② 幸存者**无**显式声明位次 ⇒ 落 `deterministic_fallback`，排在**全部**显式位次之后
  （这正是任务书 §一 引用 GPT 推演的条件性风险形态：带模型首位的 novel 被折叠进
  **无显式 rank** 的早期池条目时，那条反应的展开位次会退到显式候选之后）。
- **折叠不影响其余候选的相对次序**：紧凑化只压缩 `effective_rank` 数值，序号密集但
  次序不变；队列消费只比较 `rank` 值大小（见 §2.2 入口 4）。

### 2.2 全部适用入口清单（AGENTS.md 返工教训 1：不追单一调用点）

| # | 入口 | 位置（当前 HEAD） | 消费/产出什么位次事实 | 折叠或位次传递语义 | 本批实测触发 | 本核查是否覆盖其「首位被折叠」分支 |
|---|---|---|---|---|---|---|
| 1 | **池装配/编译**（recorded + analog 通道融合） | `pollutant/s5b_builder.py:1217-1240`（融合循环）；`1247-1253`（截断前 `pool_rank` 回填）；签名单源 `s5b_compiler.py:166` | 尚无模型 rank（模型未运行）；池槽/池序 + 诊断行 `merged_into` | 同净反应签名 ⇒ 后到 spec 丢弃，`compile.merged_source_keys` 记在幸存 spec 上；**保留先出现者**（与 decide 层同一签名函数） | **41 题 / 50 次**（见 §4） | 分支不适用（此处不存在 rank 事实）；P0② 审计**未读取**本入口 |
| 2 | **decide 层统一排序**（唯一 rank 生成点） | `pollutant/runflow.py:979, 998-1092` | 模型 `rank_by_key`/`model_rank_by_id`、池序、novel 序 → `model_rank`/`effective_rank`/`rank_basis` | 去重保留先出现者；被折叠者位次丢弃、**无继承**；紧凑化；fallback 殿后 | 2 题 / 3 次折叠；其中首位折叠 **0** | **这是被核分支的唯一构建点**；本批 0 例触发 ⇒ 覆盖为空 |
| 3 | **模型协议解析**（rank 事实来源） | `pollutant/model_protocol.py:91-240`；`runflow.py:1271-1288` | `rank_hypotheses` 出现序 → `rank_by_key` / `model_rank_by_id` | 位次 = 响应内出现序；引用未在提案集合内 ⇒ 结构化拒 | 298 题落账；无 rank 表 1 题（分类：无首位） | 部分（只覆盖「rank 表本身落地」） |
| 4 | **调度/入队消费**（cap 选中 + 次序） | `pollutant/queue.py:211-215`（`rank` 升序 + `hypothesis_id` tie-break）；`258-260`（`taken < selectable`）；`275-283`（超 cap ⇒ `deferred`，`defer_reason=selection_cap/alternatives_budget`）；`287-295` | 冻结负载的 `rank`（= `effective_rank`） | 位次决定「被选中执行」还是「转 deferred（备选，不保证再执行）」 | 含 deferred 展开动作 2 题；模型首位 deferred/blocked **0** 题 | 间接：首位折叠若发生，位次后果在本入口显形 |
| 5 | **取任务序/提交序** | `pollutant/search.py:212-231`（W-V1 策略注释）；`707-745`（run 内严格递增微秒 `created_at`，事务内 `MAX+1µs` 递推）；`976-985`（入队 INSERT 同事务） | `search_actions.created_at` → 驱动取任务序 | `ORDER BY created_at, action_id` 被装配成 = 调度入队序（判据一字未改） | — | **未单独验证**（见 §6 unknown-3） |
| 6 | **事件首提时间** | `pollutant/events.py:85-89`（`created_at` 默认 `now_iso_hires`）；`domain/models.py:78-87`；持久化 `store.py:1514+`（`submit_event` 同事务） | 事件 `created_at` | 微秒墙钟，**无单调下界**（同微秒碰撞另计） | 1443 事件 / 逐字节相同对 **0** | 是（微秒碰撞计量，与审计①②一致） |
| 7 | **判分主口径（消费事件序）** | `pollutant/s5b_scoring.py:631-655` | 事件序 → `rank` → hit@K | 反应物侧含根严格命中的已提交事件按 `(created_at, event_id)` 升序，首个严格命中决定 `hit@K` | 87 hit@1 / 119 strict（复算一致） | 是（本核查 transfer 复算采用**同一判据**） |
| 8 | **报告投影位次面**（第二套位次） | `pollutant/events.py:220-255`；旧口径消费 `s5b_scoring.py:725-739` | `product_ranks[*].report_rank`（`declared_rank_order` + 报告宽度 K）/ `dedup_notes` | 宽度外 ⇒ `report_rank=None`（`exclude_from_candidates`）；与模型 rank 面**不同源** | 1443 条投影；`dedup_notes` 非空 **0**；宽度外槽 **14** | 不适用（独立入口，P0② 未读取） |
| 9 | **裁决/报告消费者**（只读展示） | `services/report_adjudication.py:63/65`（`model_order` / `deterministic_fallback` 常量）、`324-352`、`480-490`；`output/report.py:252` | 排序依据标签 → 选择排序规则 | 按 `rank_basis` 选「模型 order 相对次序」还是「冻结后备键」；不重排序位次事实 | — | 不适用（消费面，无折叠语义；注意其 `rank_basis` 与 runflow 的 `model_selection` 是**两套命名空间**） |
| 10 | **导出/重放**（replay） | `pollutant/native_export.py:403-414`（events / report_projections / search_actions 表导出） | 原样导出，不重排序 | 本核查与 P0② 的输入都取自本面 | 298/298 payload 命中 | 是（输入面已核） |

## 3. 证据链映射：三项背景结论各由什么支撑

| 结论 | 产物 | 计算脚本 | 数据（一手） | 判据（脚本口径） | 与源码逻辑是否同源 | 本核查复核结果 |
|---|---|---|---|---|---|---|
| ① 折叠丢位 0 | `rank_audit_data.json → fold_rank_loss_verdict{...}`；summary §四 | `rank_audit.py:343-348`（分类序第 5 类）；聚合明细 `main()` `473-495` | `payload.json` 的 `expansion_outcomes[*].detail.model.dedup_rejections` + `expand_hypothesis` 载荷 `model_rank/effective_rank/rank_basis` + `model_rank_by_id` | 分类前置 = 「模型首位键出现在 `dedup_rejections`」；命中后 `inherited = survivor_model_rank is not None` ⇒ 无继承判 `fold_rank_loss`，否则 `other_unknown` | **大体同源**（都用同一批载荷字段）；两处口径差见下方注 A/B | 独立复算：折叠事件 3、**首位被折叠 0**、幸存者无声明位次 0、幸存者落 fallback 0 —— 与审计一致 |
| ② 8+32 题「模型第一名已是首事件」 | `focus_group_1_lost_to_rank_gt1`（8 行）/ `focus_group_2_rerank_space`（32 行） | `rank_audit.py:256-299`（首事件取 `(created_at,event_id)` 升序） | `payload.json` 事件 + `metrics.json(.v1)` 的 `per_qid.main.rank/match_status` + `attr_chain13_c.json → C1.hit1_v2_decomposition` | 「提交序首事件的 hypothesis == 模型首位 prepared_hypothesis_id」；8 题集合须与 attr 清单相同 | 是（与 `s5b_scoring.py:631-655` 主口径同判据） | 独立复算：组① **8/8**、组② **32/32** 均为「首位=首事件」；strict 119 / hit@1 87 复算一致；题集与审计相同 |
| ③ 微秒碰撞 0 | `microsecond_collision{total_events,n_collision_pairs,...}`；summary §七 | `rank_audit.py:301-311` | `payload.json` 的 `events[*].created_at` | 同题内 `created_at` 字符串**逐字节相同**计 1 对 | 是（`events.py:85-89` 微秒墙钟；`s5b_scoring.py:653` 同键排序） | 独立复算：1443 事件、**0 对**、0 题 —— 与审计一致 |

**注 A（口径差，不影响本批数字）**：审计的「继承」判据是 `survivor_model_rank is not None`
（只看幸存者**有没有**声明位次）；而源码里根本不存在位次继承机制，「幸存者保留自己位次」
才是实际语义。更严的口径应同时看「幸存者位次是否劣于被折叠者 / 是否退到
`deterministic_fallback`」。本批 3 次折叠的幸存者声明位次均**优于**被折叠者
（2<4、1<2、4<5）且全部 `model_selection`，故该口径差不改变 0 这个数字。

**注 B（口径差，不影响本批数字）**：审计每题只取**最后一个** `scheduled` outcome
（`rank_audit.py:69-79`）；本核查实测 chain13 **每题恰 1 个** `scheduled`（298/298），
多层 decide 场景未被折叠，无信息损失。

**注 C（入口覆盖）**：P0② 的「折叠」判据只读 **decide 层** `dedup_rejections`
（入口 2）。**池装配侧融合（入口 1）在 chain13 触发 41 题/50 次却完全不在其证据面内**；
该入口发生在模型 rank 产生之前（模型看不到被并 spec，也无从给它 rank），因此按语义
**不可能**产生「首位被折叠丢位」这一形态，但它确实改变了模型看到的池组成与池序，
属本单要求列出的「全部适用入口」中未被审计读取的一个。

## 4. 复跑核对（隔离目录；只读）

按 AGENTS.md 返工教训 6：探针先复制到**全新临时目录**执行（`PYTHONDONTWRITEBYTECODE=1`，
无 pytest 缓存），不在仓库原地跑、不写封存产物。执行目录
`/tmp/multica-task-1743981616/tf_rank_YXcpiV`，输入全部为只读的 synced 一手产物
（`payload.json` ×298 / `metrics.json` / `attr_chain13_c.json`）+ 审计产物（仅作对照，
**不作判据源**）。命令、输入 hash、执行副本 hash 见
`docs/review_evidence/tf_rank_transfer_2026-10-16/README.md`。

### 4.1 独立复算结果（与 P0② 审计产物对照，12 项全 MATCH）

| 对照项 | 本核查复算 | P0② 审计 | 结果 |
|---|---|---|---|
| payload 命中 | 298/298 | 298/298（缺失 0） | MATCH |
| 去重折叠事件数 | 3 | 3 | MATCH |
| 被折叠者是模型首位 | **0** | 0 | MATCH |
| 含折叠题数 | 2 | 2 | MATCH |
| 幸存者无声明位次 | 0 | ——（口径差见注 A） | 一致方向 |
| 幸存者落 `deterministic_fallback` | 0 | `fallback_entries_are_fold_survivors=0` | MATCH |
| 微秒碰撞（事件/对/题） | 1443 / 0 / 0 | 1443 / 0 / 0 | MATCH |
| 组① 8 题「首位=首事件」 | 8/8 | 8/8 | MATCH |
| 组② 32 题「首位=首事件」 | 32/32 | 32/32 | MATCH |
| strict(v2) / hit@1(v2) 复算 | 119 / 87 | 119 / 87 | MATCH |
| 题集一致性 | 298 题集合相同 | —— | MATCH |
| 每题 `scheduled` decide 数 | 全部 = 1 | 取最后一个 | 一致（注 B） |
| 位次去向闭合（声明 ID 无去向者） | 64 个 = 61 预校验拒 + 3 折叠，**unexplained 0** | ——（审计未做此闭合） | 本核查新增 |

「位次去向闭合」的口径：模型对池条目按 `prepared_hypothesis_id`、对 novel 按自报 id
报位次；凡是被排过位次的声明 ID 在展开条目里找不到对应条目，就必须能在
`novel_rejections`（预校验逐条拒）或 `dedup_rejections`（去重折叠）里找到去向。
实测 `unexplained = 0` ⇒ 本批不存在「被排位的条目被折叠/消失却无痕」的隐藏情形；
3 个落折叠的声明位次分别是 4 / 2 / 5，**没有一个是 1**。

### 4.2 本核查新测（P0② 未读取的入口，仅计量不判定）

| 入口 | 实测 |
|---|---|
| 池装配（build）侧折叠（入口 1） | **41 题 / 50 次**（32 题 1 次、9 题 2 次）；与 decide 侧折叠**零共现**；被并来源以 `tpl-rhea` 31、`tpl-env` 31、`rec-rhea` 3 为主，幸存者多为 recorded 键 |
| 报告投影位次面（入口 8） | 投影 1443 条；`dedup_notes` 非空 **0** 条；宽度外 `report_rank=None` 槽 **14** 个 |
| 折叠题内「声明位次 → 生效位次」（入口 2 的紧凑化实测） | 见 4.3 |

### 4.3 三次折叠的逐条明细（本核查复算，与审计 3 行一致）

| qid（前 16） | 被折叠条目 | 折叠进 | 被折叠者声明位次 | 幸存者声明位次 | 幸存者生效位次 | 幸存者 `rank_basis` | 被折叠者=首位 |
|---|---|---|---|---|---|---|---|
| `RXNG_a69bf0d2eb7…` | `novel-4` | `novel-2` | 4 | 2 | 2 | `model_selection` | 否 |
| `RXNG_c9ee5eb0c5f…` | `novel-3` | `novel-1` | 2 | 1 | 1 | `model_selection` | 否 |
| `RXNG_c9ee5eb0c5f…` | `novel-6` | `novel-4` | 5 | 4 | 3 | `model_selection` | 否 |

三次折叠的**被折叠者都未进入调度**（无 `expand_hypothesis` 条目：`folded_has_expand_action=false`）；
**没有任何一次折叠的是模型首位**（`folded_is_model_first=false`、`declared_rank==1` 亦为 0）。

**「其余候选位次如何传递」的实测形态**（`RXNG_c9ee5eb0c5f…`，该题两次折叠）：

| 候选 | 声明位次 | 生效位次 | 依据 |
|---|---|---|---|
| `novel-1` | 1 | 1 | `model_selection` |
| `novel-2` | 3 | **2** | `model_selection` |
| `novel-4` | 4 | **3** | `model_selection` |
| `novel-5` | 6 | **4** | `model_selection` |

读法（本批实测，非外推）：折叠使**下游候选整体上移**、相对次序不变；没有任何候选
因折叠**下移**；被折叠条目自身**不再占位**。全批 3 题含 fallback 候选（共 3 个条目），
**0 个**是折叠幸存者。

## 5. 逐条判定

| # | 核查项 | 判定 | 理由 |
|---|---|---|---|
| 1 | 「chain13 本批不存在被折叠的模型首位」 | **证据充分** | 一手 payload 字段级复算 = 0（298/298 命中、0 缺失），与审计产物一致；两次折叠的两题逐条明细可人工对链；并做过位次去向闭合（被排位的声明 ID 无去向者 64 个全部有去向，`unexplained=0`；其中 3 个落折叠的声明位次为 4/2/5，无一是 1） |
| 2 | 「首位被折叠后位次如何传递（是否有丢失/继承）」 | **证据不足（覆盖为空）** | 判据前置「模型首位被折叠」在本批**从未成立**（0/298）⇒ 夹具对该分支零实例；0 这个数字来自「未触发」，不是「已实测传递正确」。代码语义可详述（§2.1）但未被本批数据检验 |
| 3 | 「非首位折叠（本批 3 次）的位次后果」 | **证据充分** | 3 次折叠逐条可对链：幸存者全部有显式位次且声明位次优于被折叠者；下游候选整体上移、相对次序不变；0 例退 fallback |
| 4 | 「8 题模型第一位已是提交首事件」 | **证据充分** | 独立复算 8/8；判据与 scorer 主口径同源（`(created_at,event_id)` 升序）；8 题集合与 attr 清单一致 |
| 5 | 「32 题模型首位已居首（重排空间 0）」 | **证据充分（就『首位已居首』这一事实而言）** | 独立复算 32/32。注意外延：由此推出「重排模型自选次序不可能带来 hit@1 增益」成立；但「该候选若换成别的事件是否会命中」不在本证据面内（审计已自标 unknown） |
| 6 | 「微秒碰撞 0」 | **证据充分（就『无逐字节相同时间戳』而言）** | 1443 事件、0 对；判据与排序键一致 |
| 7 | 「事件提交序忠实反映调度序」 | **存疑（未核）** | 碰撞 0 只说明**无同时间戳**，不构成「提交序 = 调度序」的证明（事件时间取微秒墙钟、无单调下界；审计原文亦声明只披露计数、不判其是否改变 hit@K） |
| 8 | 脚本判据 vs 源码逻辑「同源」 | **大体同源，两处口径差已登记** | 同源：都用同一批载荷字段与同一排序键；差异：注 A（「继承」判据宽于源码语义）、注 B（每题只取最后一个 decide，本批无影响） |
| 9 | 入口覆盖完整性 | **证据不足（P0② 未读取两层入口）** | 池装配侧折叠（41 题/50 次）与报告投影位次面（1443 条）不在审计证据面内；前者按语义无 rank 可丢，后者是独立位次面 |

## 6. 诚实 unknown 清单（未核范围机器披露）

1. **「首位被折叠」分支的运行时行为**：chain13 零实例。本单不做专项合成验证（任务书
   明确该步在后续另一步），因此该分支的行为在本记录里**只有读码语义、没有实测证据**。
2. **8/32 题的两个不可分子情形**：「模型首位不 strict 命中」vs「其反应物侧未进入
   评分候选面」——事件级匹配身份未在 payload/metrics 披露，属 unknown（沿用审计自标）。
3. **提交序忠实性**：`search_actions.created_at` 的 run 内单调递增装配（`search.py:707-745`）
   与事件侧微秒时间戳（`events.py:85-89`）在同一次运行内「是否严格保持提交序」未经
   端到端核验；本核查只做了同时间戳计数（0）。
4. **池装配侧折叠的正确性**：本核查只计量其触发次数（41 题/50 次），**未**判定其
   合并判据是否漏并/误并（不在被核问题范围内，且 PI 未列入本单）。
5. **多层 decide（深度展开）**：本题域每题恰 1 个 `scheduled` decide，故「多层 decide
   下 rank 传递 + 折叠的交互」无覆盖。
6. **其他批次/题域**：结论仅限 chain13 本批 298（298 = RHEA 通用酶学/已见题）；
   chain14 两臂、dev 题域未核，不外推。
7. **两套 `rank_basis` 命名空间**：`model_selection`/`deterministic_fallback`（runflow，展开
   条目）与 `model_order`/`deterministic_fallback`（report_adjudication，报告裁决）是否
   需要在文档层统一，属工程命名议题，不在本单范围。

## 7. 未触发分支的语义描述（描述性，非断言）+ 建议下一步

- **描述**：若「模型首位」是一条 novel 且其净反应签名与**更早出现**的池条目相同，则该
  novel 会被折叠进该池条目；被折叠的位次不转移，池条目保留自己的位次；若该池条目
  **本来没有任何显式声明位次**（模型未在 `rank_hypotheses` 里引用它），它会落
  `deterministic_fallback`，即排在**全部显式位次候选之后**——那条反应的展开位次因此
  退到显式候选之后。这是「首位被折叠 + 幸存者无显式位次」这一**组合前置**下的语义。
  chain13 三条折叠均不满足该组合（幸存者全部有显式位次，且被折叠者都不是首位）。
- **建议下一步（不在本单，交老师/CC 裁定）**：专项合成验证——用最小合成输入覆盖
  「首位（novel-1）被折叠进无显式 rank 的池条目」这一组合，观察展开位次与提交序；
  该验证同时可作为上一行语义描述的**它证**或**反证**。本单不做。

## 8. 复现与证据清单

| 项 | 路径 |
|---|---|
| 本记录 | `docs/TF_RANK_TRANSFER_VERIFICATION_2026-10-16.md` |
| 证据目录（含执行说明与 hash） | `docs/review_evidence/tf_rank_transfer_2026-10-16/README.md` |
| 只读探针脚本（落盘副本） | `docs/review_evidence/tf_rank_transfer_2026-10-16/tf_probe_rank_transfer.py` |
| 探针机读输出 | `docs/review_evidence/tf_rank_transfer_2026-10-16/tf_probe_output.json` |
| 探针控制台输出 | `docs/review_evidence/tf_rank_transfer_2026-10-16/tf_probe_stdout.txt` |
| rank 代码块两版一致性证据 | `docs/review_evidence/tf_rank_transfer_2026-10-16/git_rank_block_identity.txt` |

复现命令（隔离目录内执行）：

```
cd <新建临时目录>
cp <repo>/docs/review_evidence/tf_rank_transfer_2026-10-16/tf_probe_rank_transfer.py .
PYTHONDONTWRITEBYTECODE=1 /Users/cc/miniconda3/envs/depending43/bin/python \
  tf_probe_rank_transfer.py \
  --sync <repo>/reports/ppv1_s5b/chain13_glm/synced \
  --attr <repo>/reports/ppv1_s5b/chain13_glm/analysis/attr_chain13_c.json \
  --audit <repo>/reports/ppv1_s5b/p0_rank_audit_2026-10-15/rank_audit_data.json \
  --out tf_probe_output.json
```

## 9. 收尾核验与假设

- **HEAD / 分支**：`3440ca7`（`v4.3`）；本核查未切分支、未 commit、未 push。
- **判据同源前置（已核）**：P0② 审计产出于 HEAD `461844e`；本核查核对
  `runflow.py`「位次传递/去重折叠」代码块（旧 `979-1092` == 新 `985-1098`）两版
  **sha256 相同、diff 为空** ⇒ 审计所读逻辑在当前 HEAD 未被改动
  （`runflow.py` 两版间另有 +149/−31 改动，hunk 边界不覆盖该区间）。`queue.py`/`search.py`/
  `events.py`/`s5b_scoring.py` 两版间**零改动**。证据见 `git_rank_block_identity.txt`。
- **仓库不变量**：`git status --porcelain` 中 `src/`、`tests/` **零改动**（0 条）；
  新增文件全部为 `docs/` 下未跟踪文件（本记录 + 证据目录）。
  唯一已跟踪改动是 `AGENTS.md`（工作树 `+241/−0`），内容为 daemon 自动注入的
  `MULTICA-RUNTIME` 块（文件末追加），**任务开始时即已存在**，本核查未写入该文件。
- **零模型/零 API/零费用**：全程本地只读，无网络、无模型调用、无新实验；未读题面、
  未读参考图、未读 gold；`reports/`、`runs/` 只读。
- **假设（任务书未明确处，按最保守合理取值）**：
  1. 「位次传递」的被核面取**模型 rank → effective_rank → 提交序首事件**这条主链
     （与错题书一致）；报告投影位次面（入口 8）作为并列入口只计量不判定。
  2. 审计产物的定位以 `rank_audit_data.json` 的显式键为准（`fold_rank_loss_verdict` 等），
     不重新解释 summary 的散文表述。
  3. 「证据充分/不足」按**是否有本批实测实例**划分：判据前置未触发的分支一律记
     「证据不足（覆盖为空）」，不因读码语义清晰而升格为「充分」。
