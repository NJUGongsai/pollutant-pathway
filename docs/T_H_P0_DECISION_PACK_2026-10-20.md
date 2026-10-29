# T-H hit@1 P0 诊断决议包（2026-10-20）

> **⚠ 2026-10-20 晚：本包已由 Codex 审核并代 CC 决议。**
> 审核报告：`docs/T_H_P0_DECISION_CODEX_REVIEW_2026-10-20.md`。
> **本包需按该报告的更正后使用**（关键更正：P0-C 的 45/6/2 是事件形态题级分组、**6 不等于
> missing-only**；P0-A 的“默认补齐为零”未证明；P0-D 的路由与“失败为零”不成立；
> 193 与 207 并存；正式回放门尚未实施）。**下一步以审核报告的代决为准**：
> 先做 P0b/D-6 旁路披露（不加硬门）；D-2 证据卡 v2 选为第一个选择层实验方向但不发车；
> D-1 延后；D-3/D-4/D-5/D-7 延后。

> **题域：298 = RHEA 通用酶学 / 已见题（post-hoc）。** 本文所有题数、比例、上限只在该题域成立；
> 不外推到 dev、新题或其他题域。基线：T-H r2，criteria-v2 headline **89/298 = 29.87%**；
> hit@3 118、hit@5 125；strict(U) 126；partial 53；unmatched 119。
>
> **性质：诊断取数，不替 CC/老师拍板。** 零模型调用、零重判改动、零付费、零代码改动；
> 封存批根只读。参考图只在冻结 scorer 进程内消费，未复制或输出；本代理未人工读取金标/
> 题面/候选 SMILES 正文，未输出任何化学结构字符串。
> 证据目录：`docs/review_evidence/t_h_p0_2026-10-20/`（含 `SHA256SUMS`）。

## 0. 结论先行

1. **排序层位次来源干净，但只是毛空间。** 37 个 strict 非首位题的评分对照事件 **37/37**
   都是解析规范化后的 `model_selection` 且 `model_rank` 为显式整数；全批 126 个 strict
   事件也 **126/126** 如此。37 仍是理想排序毛空间，不是可兑现净增。
2. **覆盖缺口已从“unknown”拆到机械类别。** 53 partial = **45 extra + 6 missing + 2 mixed**；
   119 unmatched = **45 cn_only 身份缺口 + 74 结构未命中**。类别互斥且总数闭合。
3. **执行对账给出新的效度信号。** 1586 个已提交事件中 **296 个** 的声明产物与自身 edits
   执行碎片不一致（全部为 novel）；其中 **204 个主产物根本不在执行碎片中**，**6 个恰好是
   评分 strict 对照事件**。另 92 个仅共同产物/额外组分不同，52 个仅立体差。
4. **供给漏斗最大闸门是 `no_alignment`，但同码多义已拆开。** 1585 条候选级
   `no_alignment` = 864 条 F5 预门 reject + 543 条 F5 defer 后编译器出因 + 178 条非 F5 适用；
   F3 wildcard 预门另有 992 条，不冒充 `no_alignment`。deferred 2366 条逐条闭合。
5. **207 锚点是跨批口径。** 同一探针逻辑在 T-H r2 实测 **193** 题无已调度 recorded 候选
   （207 来自 chain14 A/B）。两数并存，不硬改口径；这是本决议包必须披露的冲突。
6. **P0 回放门“具备执行条件”，但本轮未执行正式门。** 用冻结 scorer + 已保存 payload
   离线重跑，桶 **298/298**、strict rank **126/126**、候选事件 **1586** 全部复现；
   正式门还需 P0b 诊断字段包装后才能验“加字段零漂移”。

## 1. 统一取数口径与 provenance

| 项 | 值 |
|---|---|
| 本地 HEAD | `c9c6c7a7ae02b46769add09fbc2536323ce8a985` |
| 判分代码 | 本地 `evaluation.py` / `s5b_scoring.py` / `runflow.py` 与 HPC 部署逐字节同 SHA256 |
| 判分重跑 | 冻结 scorer + 已保存 `native_export` payload + 本地参考图（sha 298/298 对上 T-H manifest） |
| RDKit | 本地重跑 2026.03.6；批内登记 2026.03.5。桶/rank 298/298 一致，未观察到版本漂移；正式门建议用批内环境复核 |
| 模型调用 | 0 |
| 判分改动 | 0 |
| 封存批根写入 | 0 |
| 化学输出 | 无 SMILES / 无结构正文 |

每个子项一个 JSON + 一个 markdown 摘要，均在证据目录；哈希见 `SHA256SUMS`。

## 2. 证据摘要

### 2.1 P0-A 候选谱系（37 题）

| 项 | 值 |
|---|---:|
| strict 非首位题 | 37（rank2–5 36 + rank>5 1） |
| matched 事件 `model_selection` | 37 |
| matched 事件显式整数 `model_rank` | 37 |
| null / 默认补齐 / fallback | 0 / 0 / 0 |
| rank 继承自折叠条目 | 1 |
| 37 题内 dedup rejections | 2 条（2 题） |
| 空池 strict 非首位 | 5 |
| Stage 0 32 条 rank 行对账 | 32/32；37=32+5 |

全批对照：1586 事件中 `model_selection` 1559、`deterministic_fallback` 27、无 null/missing；
126 个 strict 事件全部 `model_selection`；27 个 fallback 无一成为 strict 对照事件。

**读法：** 不能说“32/32 都是模型显式自排”就推出可捞回；只能说位次来自解析规范化后的
模型位次，且评分对照事件没有 fallback/null。换卡/换 prompt/换 ranker 的实际回收率 unknown。

### 2.2 P0-B 声明产物 vs 执行产物（1586 事件）

| 状态 | 事件数 |
|---|---:|
| consistent | 1290 |
| inconsistent | 296 |
| unknown | 0 |
| not_applicable | 0 |

- 296 条不一致 **全部来自 novel**；recorded 151 / template 368 全部一致。
- **204 条主产物不在执行碎片中**；92 条主产物在、仅共同产物/额外组分不同；
  52 条仅立体差；198 条组分集合不同；45 条执行缺声明组分；1 条执行多出组分。
- **6 条不一致事件恰好是评分 strict 对照事件**（主产物均不在执行碎片中）；
  76 条不一致事件位于 hit@1 题内。
- audit 交叉：296 条中 **119 条** `center_match=True/None` 且 `declaration_mismatch=False`，
  现有中心审计没有标出这些声明矛盾；12 条 `strict_target_match=True`。
- 合成正负控 8 项全部通过（多碎片、合法 copy、立体差、明确矛盾、解析失败、空声明）。

**读法：** 这是“答案能否由所提 edits 支持”的效度披露，不证明候选化学错误；unknown 未洗成通过。
**最强的单点信号是 6 个 strict 对照事件**：它们命中了评分，但主产物与自身执行结果不一致。

### 2.3 P0-C 评分缺口（53 + 119）

对齐门：重跑桶 298/298，strict rank 126/126，候选事件 1586。

| partial 类 | 题数 | | unmatched 类 | 题数 |
|---|---:|---|---|---:|
| extra | 45 | | required node gap = cn_only | 45 |
| missing | 6 | | required node gap = 结构未命中 | 74 |
| mixed | 2 | | scope / unparseable / no event / unknown | 0 |
| scope / unknown | 0 | | | |

- partial：非空池 41 / 空池 12；remap 25 / 非 remap 28。
- unmatched：非空池 96 / 空池 23；remap 69 / 非 remap 50。
- Stage 0 交叉：coverage41 = extra 33 / missing 6 / mixed 2；secondary47 = cn_only 39 / 结构 8。
- v2 豁免 5 题 5 次，全部 `v1_exempt`（H2O）。

**读法：** extra/missing 是机械覆盖方向，不是化学裁决；删真实副产物被禁止，补缺失组分需化学
评审。cn_only 的 45 题属于 T1 判据研究面，不是本轮提分动作。

### 2.4 P0-D 供给漏斗

| 分母 | 值 |
|---|---:|
| 题 | 298 |
| 已调度 spec | 1601 |
| 已提交事件 | 1586 |
| manifest 候选行 | 5319 |
| deferred entries | 2366 |

- 候选行：compiled 531、compile_rejected 4311、merged_into 472、pool_truncated 5。
- 通道：analog 3576、corpus 1421、recorded 322。
- `no_alignment` 1585 = F5 预门 reject 864 + F5 defer 后编译器 543 + 非 F5 适用 178 + unknown 0。
- F3 wildcard 预门跳过 992（单独计，不冒充 `no_alignment`）；F5 checked 3398 / deferred 1548 / skipped 864。
- remap：已调度 spec applied 234、新 map 728、applied-zero-new 0、`remove_atom` 0、未尝试 analog 134、失败 0。
  P2 spec 级为 242/205/78、151 题 remap（分母不同，不互换）。
- 执行失败：候选 `execution_failed` 35 条 / 21 题；production `method_failed` 15 条 / 12 题。
- deferred 2366 = depth_limit 2358（retrieve / coproduct_deferred）+ alternatives_budget 8
  （expand / alternative_reaction_deferred），与 endpoint 计数逐条闭合。

**207 冲突：** 任务锚点 207 来自 chain14 A/B 探针；同一逻辑在 T-H r2 为 **193**（差 −14）。
未改口径、未把 193 写成 207。207 不是 T-H r2 的不变量。

### 2.5 T1 v3 归一配对

- 复现冻结披露：**47 配对 = tautomer 13 + protonation 10 + none 24**；axis nodes 645 / n/a 598。
- 有配对题 45；有归因配对题 **21**（tautomer 13 题、protonation 9 题，1 题两轴都有）。
- 47 个配对全部在 `principal_product` 节点、全部当前 `cn_only`；45 题的配对 state 出现在候选事件中。
- 影子（只把有归因 cn_only 提升 strict，按同一节点/事件集合重算必要节点→覆盖→首位）：
  **unmatched→strict 18 题，其中 rank1 8 题；unmatched→partial 3 题；已有 strict 题 rank 改善 0。**
- 与 P0-B 交叉：21 个归因配对题中 **6 题**的对账事件 inconsistent；8 个影子 rank1 里 **3 题** inconsistent。

**限制：** 不重做化学评审；不处理 v2 豁免、E/Z 与 stereo-preserving 未核范围；24 个 none 配对与
未披露配对未提升。影子是研究毛空间，不是净增、不是 23 题收益、不是判据提案。

### 2.6 T4 价态异常 12 题

- 12 题、15 条 `method_failed` 报告；全部 reason = `AtomValenceException:edit[last]`。
- 3 题仍 hit@1；strict 共 4（含 1 题 rank2）；partial 1；unmatched 7；这些题内已提交事件 51。
- 单题 1–7 个已提交事件，失败是单条 edit 路径，不是整题零答案。

**限制：** 不能据此说“隐式氢必撞墙/缺脱氢能力”；代码让 sanitize 重算隐式氢；12 题不足以定位能力缺口。

### 2.7 T5 立体能力缺口

- 金标级“纯立体差题数”：**unknown**（T-H 只读元数据无该字段）。
- T-H 代理：P0-B 仅立体差事件 **52** 条 / **25** 题；声明产物带立体 **254** 事件 / **60** 题；
  edits 设置立体的操作 **0**；本批 edits 只有 add_atom / change_bond_order / break_bond / form_bond。
- 历史 chain12 的 21 题是不同批次/口径，不是 T-H 硬天花板。

## 3. 决策项（只列证据与选项，不拍板）

> 每项给出：证据摘要、可动子集、若做下一步的单变量实验设计要点、若不做的反证、未知项。
> 所有“上限/毛空间”均不是收益承诺。

### D-1 v3 归一研究（T1）

| 项 | 内容 |
|---|---|
| 证据 | 47 配对 / 13 tautomer / 10 protonation / 24 none；21 题有归因配对；影子 18 题 unmatched→strict、8 题 rank1、3 题 partial；6 题对账事件不一致 |
| 可动子集 | 21 个归因配对题（其中 15 题对账事件 consistent；6 题 inconsistent）；24 个 none 配对不在内 |
| 若做 | 另立判据研究：两臂（冻结 v2 vs v3 归一提升）用同一候选、同一题集、完整链（去重题数→必要节点→边 exact→首位）；先冻结化学语义（互变/质子化/立体/E-Z 逐项）与两侧同源；预注册净增/损失/持平与停点 |
| 若不做的反证 | 影子 18/8 不是净增；3 个 rank1 影子点对账不一致；stereo-preserving 仍可能擦除 E/Z；不能用“放宽评分后过线”证明系统能力 |
| 未知 | 18 个 shadow strict 中多少在化学上真的同一物种；E/Z 与 sp3 立体保全；未披露配对；整个参考边是否可 strict |

### D-2 排序层（P0-A）

| 项 | 内容 |
|---|---|
| 证据 | 37 非首位全部 `model_selection` 显式 rank；126 strict 事件 126/126 显式；全批 27 fallback 无一成为 strict |
| 可动子集 | 37 题理想排序毛空间（36 rank2–5 + 1 rank6；5 空池）；37 题内 rank2 共 20 题（非空池 17 题） |
| 若做 | 首个选择层单变量实验优先按已冻结证据卡 v2 设计；同模型、同建池输入、同判据、同配置；全 298 题配对统计新增/损失/净增；不只在 32/37 失分题展示 |
| 若不做的反证 | 37 是固定事件集毛空间，全局重排会损失旧命中；历史机械重排负先例；17 题“只差一位”不保证可捞回 |
| 未知 | 换 prompt/换卡/换 ranker 的实际回收率；候选池/结构/匹配是否也拖累；证据卡 v2 的净效果 |

### D-3 partial 覆盖（P0-C）

| 项 | 内容 |
|---|---|
| 证据 | 53 = 45 extra + 6 missing + 2 mixed；Stage0 coverage41 = 33/6/2；非空池 41、空池 12 |
| 可动子集 | 6 个 missing-only 题是唯一“缺组分”方向；45 个 extra-only 需先判副产物真伪；2 个 mixed 两向都有 |
| 若做 | 先做逐事件/逐参与物化学评审与合法正控：missing 方向验证“缺的是真实必要参与物”；extra 方向验证“多的是真实副产物”，不预设删除；单变量实验只改装配/引用关系，不改判据 |
| 若不做的反证 | 删副产物/删 copy 改变净反应与记录契约；统一加共底物会制造假组分；width 截断不是 partial 成因 |
| 未知 | extra 中真实副产物 vs 装配多写的比例；missing 中真实缺组分 vs 表示/身份问题的比例；逐事件化学正确性 |

### D-4 价态异常（T4）

| 项 | 内容 |
|---|---|
| 证据 | 12 题、15 条 method_failed、3 题仍 hit@1；全部单条 edit 路径 AtomValenceException |
| 可动子集 | 12 题内失败的具体 edit 输入（合成复现），不是 12 题整体 |
| 若做 | 用合成输入复现具体失败，核对可表达性（sanitize 重算隐式氢、显式氢扣账）后再设计协议；保留合法正控与真实错误负控 |
| 若不做的反证 | “隐式氢升键级必撞价态墙”被源码否定；12 题不足以定位缺失能力；method_failed 不等于整题无答案 |
| 未知 | 这些失败是否对应真实化学可行的编辑；是否存在系统性缺失能力；修复后的命中变化 |

### D-5 立体能力（T5）

| 项 | 内容 |
|---|---|
| 证据 | 金标级纯立体差 unknown；P0-B 仅立体差 52 事件 / 25 题；声明带立体 254 / 60；edits 立体操作 0 |
| 可动子集 | 25 个仅立体差对账事件（声明 vs 执行）；60 个声明带立体题 |
| 若做 | 先建金标级/参考侧立体差字段与合成正负控；区分“声明产物带立体”“edits 设置立体”“执行擦除立体”三件事；再做单变量能力实验 |
| 若不做的反证 | 声明 `product_smiles` 可带立体；21 是 chain12 口径；把 21 当 T-H 硬天花板不成立 |
| 未知 | T-H 金标级纯立体差题数；E/Z 保全；哪些立体差来自执行擦除 vs 声明本身 |

### D-6 声明 vs 执行效度（P0-B）

| 项 | 内容 |
|---|---|
| 证据 | 296/1586 不一致（全部 novel）；**204 主产物不在执行碎片（承重信号）**；92 仅副产物/额外组分（需按 atom-tool 执行 vs 事件装配契约复核，不直接算错误）；52 仅立体；6 个 strict 对照事件不一致；119 条现有审计未标。合法 copy 正控 21 条全部 consistent，不一致与 copy 轴无关 |
| 可动子集 | 296 条不一致事件；其中 6 个 strict 对照事件是最高优先级；76 条位于 hit@1 题内 |
| 若做 | 先只披露（P1-B 方向）：按 origin、生成组分/copy、proof_scope 分层；合成正负控保留合法多组分/合法 copy；硬门只拒适用范围内已证不一致，unknown 保留未核范围 |
| 若不做的反证 | 简单比较两个 SMILES 字符串会误伤多碎片/合法 copy/立体；执行一致只证明局部事实，不证明机制或生物可行性；硬门可能降分，验收首看证明范围 |
| 未知 | 204 条主产物缺失中多少是声明错误 vs 执行路径不完整；92 条副产物差是正常执行/装配分工还是真实错误；6 个 strict 事件的实际答案正确性 |

### D-7 供给投入（P0-D）

| 项 | 内容 |
|---|---|
| 证据 | 193 题无已调度 recorded（T-H r2；207 为 chain14）；no_alignment 1585 = 864 F5 + 543 编译器 + 178 非 F5；F3 992；remap 234/728/0/134/0；deferred 2366 闭合 |
| 可动子集 | F5 预门 864 条（先查中心缺失是否真实）；编译器 543 条（查元素账/对齐）；F3 992 条（wildcard 边界）；134 条未尝试 remap 的 analog spec |
| 若做 | 按具体同规则反例分项：F5 / F3 / remap 各做单变量编译实验，保留合法正控与真实错误负控；分别报 spec/题/事件分母 |
| 若不做的反证 | 不能按拒绝条数排投资；`no_alignment` 同码多义；remap 与丢分只是关联，无同题 A/B；从 corpus 覆盖直接推收益不成立 |
| 未知 | 864 条 F5 拒绝中真实中心缺失 vs 检索/资产缺面；543 条编译器 no_alignment 的可表达性；193 题（或 chain14 的 207 题）recorded 缺席的根因分层 |

## 4. 回放门评估（本轮未执行正式门）

**具备执行条件。** 本轮已用冻结 scorer + 已保存 payload + 本地参考图做离线只读重跑：

- 桶：**298/298** 与 `metrics.json` 一致（v2/v3 各一次）。
- strict rank：**126/126** 一致。
- 候选事件：**1586**，与提交事件锚点一致。
- 判分聚合：hit@1 89、strict 126、partial 53、unmatched 119 复现。

**尚未执行的部分：** 正式门要求的“新增诊断字段排除后零漂移”需要 P0b 把诊断字段写进
`native_result`/`native_export`/`s5b_builder`/`s5b_compiler`/`production`（输出 schema 与版本升位），
本轮不在范围内。因此：**评分语义与已保存载荷的回放条件已具备；加字段零漂移门尚未执行。**
P1/P2 不应在正式门通过前启动。

## 5. 与四份报告的冲突/更新

| # | 来源 | 报告读法 | P0 实测 | 处置 |
|---|---|---|---|---|
| 1 | Minimax 意见 §3.1 / 任务锚点 | 207 题无 recorded 候选 | T-H r2 同逻辑 **193**；207 是 chain14 A/B | **冲突披露**：两数并存，不硬改；207 不是 T-H 不变量 |
| 2 | Stage 0 §4 | 41 覆盖题“可行动子集 unknown” | 冻结 scorer 拆成 extra 33 / missing 6 / mixed 2 | **更新**：机械层已拆；化学可行动性仍 unknown |
| 3 | Stage 0 §5 | 47 二级题 structure/coverage/matcher 无法分层 | 39 题 required node 为 cn_only、8 题为结构未命中 | **部分更新**：身份 vs 结构已分层；匹配器误拒仍未证 |
| 4 | 四份报告均未列 | — | **6 个评分 strict 对照事件的声明主产物不在执行碎片中**；296 条 novel 不一致；119 条现有审计未标 | **新增证据**，需在 D-6 处理 |
| 5 | 综合版 §2/§6 | 23 配对不能当 ≤23 题收益 | 影子 18 题 unmatched→strict、8 题 rank1，但 3 个 rank1 对账不一致 | **一致**：只作研究毛空间，不写净增 |
| 6 | 归因报告 §3.3 | P2 remap spec 级 242 / 205 / 78 | 已调度 spec 级 remap applied 234、新 map 728 | **口径不同**：spec 分母不同，不互换、不冲突 |
| 7 | Stage 0 §3 | 32 个 strict 匹配事件自报 partial | P0-C `partial_with_matched_strict_event=0` | **不冲突**：前者是 strict 题内事件自报，后者是 partial 边的 exact 事件数 |
| 8 | 归因报告 §7 / T4 | 12 个 method_failed，3 题仍 hit | 15 条报告、3 题 hit@1、4 strict、1 partial、7 unmatched | **一致**（15 条 vs 12 题是报告/题分母差） |
| 9 | 历史 chain12 | 21 题立体差 | T-H 金标级 unknown；代理 52 事件 / 25 题 | **不冲突**：21 是 chain12 口径，不是 T-H 天花板 |

## 6. 未知清单（不估算）

1. 37 题换 prompt/换卡/换 ranker 的实际回收率。
2. 296 条声明-执行不一致中，声明错误 vs 执行路径不完整各占多少；6 个 strict 对照事件的实际答案正确性。
3. 45 个 extra partial 中真实副产物 vs 装配多写的比例；6 个 missing 中真实缺组分的比例。
4. 45 个 cn_only unmatched 在化学上是否真的同一物种；E/Z 与 sp3 立体保全范围。
5. 864 条 F5 拒绝中真实中心缺失 vs 资产/检索缺面的比例。
6. 193 题（T-H）无已调度 recorded 的根因分层；与 chain14 的 207 题差集构成。
7. 12 题价态异常是否对应系统性能力缺口；修复后的命中变化。
8. T-H 金标级纯立体差题数。
9. 正式回放门的“加诊断字段零漂移”（需 P0b）。

## 7. 建议的下一步顺序（供 CC/老师选择，不代替拍板）

1. **先处理 D-6 的 6 个 strict 对照事件**：只做披露与化学复核，不改判分；确认是声明错误、执行路径不完整还是合法多步。
2. **再选 D-2 或 D-1 的单变量实验**：D-2 有已冻结设计（证据卡 v2）；D-1 必须先立判据研究并冻结化学语义。
3. **D-3/D-7 按分诊分项立项**：不按拒绝条数排投资，不统一删/加组分。
4. **P0b 与正式回放门另立任务书**：在 P1/P2 启动前完成。

> **边界声明：** 本决议包只做诊断取数与选项整理，不替 CC/老师拍板；不承诺任何恢复收益；
> 不把毛空间、配对数、影子数当净收益；所有 unknown 保持 unknown。
