# T-I 排序提示词变量清单（下一轮候选；不进当前 T-I 批）

> **题域：298 = RHEA 通用酶学 / 已见题（post-hoc）。** 本文所有证据与预期只在该题域成立；
> 与 dev 双向不外推。
>
> 状态：**DRAFT / 候选清单，不是预注册，不是发车指令。** 本文不调用模型、不跑批、不改 prompt、
> 不改判分。任何变量启用前必须另立预注册并由 CC 拍板。
>
> 上游证据：`docs/T_H_TEACHER_LEVER1_RANK_TABLE_2026-10-21.md`（37 题逐题分类）与
> `docs/review_evidence/t_h_lever1_rank_2026-10-21/lever1_rank.json`。

## 0. 为什么是清单而不是实施

老师任务书 §一 Day 2 的分支判定：

- 37 题 strict 非首位里，`model_ranking=37/37`，`execution_assembly=0`，`fallback_default=0`，`unknown=0`（已证）。
- 因而不在本周期实施执行/装配层位次修复，不立项 chain15；模型侧成因转成 T-I 提示词变量清单。

**本文的 3–5 个变量不塞进当前 T-I 批。** 当前 T-I 预注册
（`docs/T_I_PREREG_2026-10-20.md` §2.1）写死「唯一变量=模型」；T-I 是
GLM-5.3-Flash vs deepseek-v4.1-flash-1017 的模型配对批。把任何 prompt 变量塞进去，
就不再是单变量配对，主判定（hit@1 差 ≥5pp + 桶迁移）也不能归因到模型。

下一轮若启用，按「一次只开一个 prompt 变量 + 单独预注册 + prompt 文本 SHA 冻结」执行；
同一批不得同时改模型和 prompt。

## 1. 当前状态（证据）

| 事实 | 读数 | 标签 | 来源 |
|---|---:|---|---|
| 37 题 strict 事件 rank_basis=`model_selection` | 37/37 | 已证 | `lever1_rank.json` summary |
| `model_rank` 显式整数 | 37/37 | 已证 | 同上 |
| 模型 rank = effective rank = 提交位次 | 37/37 | 已证 | 同上 |
| strict 事件通道：novel / recorded / analog | 33 / 2 / 2 | 已证 | 同上 |
| 空池 5 题全部靠 novel，模型显式排 2/2/3/5/2 | 5/5 | 已证 | 37 题分类表 §3.3 |
| 全批 1586 事件 fallback 仅 27 条，且无一条成为评分 strict 对照事件 | 27/1586 | 已证 | `p0a_candidate_lineage.json` |
| 当前 prompt 的排序要求 | 只有 `rank_hypotheses: ["<hypothesis_id in your preference order, best first>"]` | 已证（源码） | `src/pathway_v43/pollutant/real_model.py:172,181` |
| 当前 prompt 是否要求排序理由 | 没有 | 已证（源码） | 同上，输出契约无 rationale 字段 |
| 当前 prompt 是否要求按证据强度/通道排序 | 没有；证据字段被声明为 “informational context…not proof” | 已证（源码） | `real_model.py` 静态段 4 |
| 当前 rank policy | 只消费模型显式 rank；novel 不因来源排后 | 已证（源码） | `src/pathway_v43/pollutant/runflow.py:204,986-1151` |
| 37 题 dedup 折叠 | 2 条；0 条让 strict 事件后移，1 条使之前移 | 已证 | 37 题分类表 §3.2 |

**读法：** 模型已经能给出显式位次，缺的不是「排不排」，而是「按什么排、为什么这样排、
首位失败时有没有可审计的备选」。所以候选变量集中在排序准则与可观测性，不是再扩候选。

**全 126 strict 的辅助背景（描述性，不改变 37 行分类）：**

| strict 事件通道 | 总 strict 题 | 其中首位 | 其中非首位 | 非首位占该通道 |
|---|---:|---:|---:|---:|
| novel | 64 | 31 | 33 | 51.6% |
| recorded | 41 | 39 | 2 | 4.9% |
| analog | 21 | 19 | 2 | 9.5% |

模型对 recorded/analog 的 strict 正确事件几乎都能排到首位，但 novel 正确事件有一半落在
非首位。这是同批 strict 事件内的关联，不是通道质量或因果结论；它只说明「novel 不降权」
值得作为候选变量，证据文件 `strict126_channel_context.json`。126 = 89 个首位 strict +
37 个非首位 strict（37 已含在内），不是两组独立样本。

## 2. 候选变量（3–5 个）

每个变量都只描述**提示词侧**的改动方向与观测方式；不写完整 prompt 文本，不写化学判据，
不承诺收益。预期一律是方向性假设，不是数字承诺。

### V1. 位次理由声明（rank rationale）

| 项 | 内容 |
|---|---|
| 变量定义 | 在输出契约里增加逐位理由：`rank_hypotheses` 的每一项附一个受控标签（如 `evidence_complete` / `source_match` / `mechanism_only` / `uncertain`），要求模型说明为什么排这个位次；不允许自由长文。 |
| 证据 | 当前 prompt 只要求 preference order，没有理由字段（`real_model.py:172,181`）；37/37 的 strict 事件只有位次整数，payload 里没有任何逐位理由，post-hoc 无法区分「证据不足」还是「机制偏好」。 |
| 预期（方向） | 让排序依据可审计，便于下一轮按标签归因；可能减少「无证据但排前面」的位次；不保证 hit@1 上升。 |
| 风险 | 增加输出 token 与格式失败/反馈轮；理由可能是事后合理化；受控标签若设计不当会变成新的隐式判据。 |
| 观测 | 格式反馈率、解析失败率、各标签的 strict 命中率、strict 事件模型 rank 分布。 |

### V2. 证据优先排序（evidence-first ordering）

| 项 | 内容 |
|---|---|
| 变量定义 | 在排序指令里要求先比较确定性证据（alignment 是否 resolved、participant 覆盖是否完整、compile diagnostics、source reference 是否存在），再比较机制偏好；证据不足的提案不得仅凭“机制上更像”排到证据更完整的提案之前。 |
| 证据 | prompt 已提供 evidence 字段，但明确说它们只是参考、不是 proof，且没有告诉模型如何在排序时使用；37/37 strict 事件均由模型显式排位，模型 rank>1，说明当前排序没有把「可被判分覆盖」放第一位。 |
| 预期（方向） | 首位更偏向 strict 覆盖完整的候选，可能提高 strict 事件排到首位的比例；对 novel-only 题可能无效。 |
| 风险 | 可能把排序推向 recorded/池内候选，压低 novel（本批 33/37 的 strict 事件是 novel）；证据字段本身可能有噪声，模型可能过度信任。必须与 V3 一起做通道中性检查，但不能同批启用两个变量。 |
| 观测 | 首位通道分布（novel/recorded/analog）、strict 事件模型 rank、hit@1、U、空池题表现。 |

### V3. 通道中性 / novel 不降权（channel-neutral ranking）

| 项 | 内容 |
|---|---|
| 变量定义 | 明确告诉模型：recorded / analog / novel 只是来源标签，不是排序先验；不得仅因缺少 recorded 支持就把 novel 降到后面；三类通道用同一套证据门槛比较。 |
| 证据 | 37 题 strict 事件里 novel 33、recorded 2、analog 2；5 个空池题 100% 靠 novel；代码侧也写明「novel 不因来源排后」（`runflow.py:204`）。37 个失败池内，模型首位是 analog 18 / recorded 11 / novel 8，其中 17 题「首位 analog → strict novel」、8 题「首位 recorded → strict novel」；这是失败池内描述，不是全批因果。若下一轮引入“recorded 优先”的先验，按本批结构会与多数正确通道相反。 |
| 预期（方向） | 保护 novel 通道的首位机会，避免 V2 的证据优先被模型误读成「recorded 优先」；对空池题尤其相关。 |
| 风险 | 可能过度抬高无约束 novel，增加错误首位；通道中性不等于通道等价，recorded 的证据强度仍应参与比较。 |
| 观测 | 首位通道分布、空池题 strict 排名、novel 首位的 strict 命中率、非空池 recorded/analog 命中率。 |

### V4. 去重感知的互异排序（dedup-aware distinct ranking）

| 项 | 内容 |
|---|---|
| 变量定义 | 要求模型在排序前先自查「同一净反应/同一产物集合」的重复提案，避免把多个位次花在同一条反应上；排序列表按互异反应排，不按重复条目凑数。 |
| 证据 | 37 题里 2 题出现 dedup 折叠；其中 1 题折叠后位次继承使 strict 事件从自排 r4 前移到 r3。折叠本身没有丢位次，但重复提案会占用模型自己的排序槽位，降低首位信息量。当前 prompt 没有提 dedup/merging 语义。 |
| 预期（方向） | 减少重复提案占用前排，让模型把有限位次分配给互异候选；对首位命中的影响不确定。 |
| 风险 | 模型对「同一净反应」的判断不可靠，可能误合并不同候选；增加输出与推理负担；dedup 是执行层确定性逻辑，prompt 只能近似。 |
| 观测 | 每题互异提案数、dedup 折叠条数、首位候选被折叠率、strict 事件模型 rank。 |

### V5. 覆盖完整性优先（coverage-completeness first）

| 项 | 内容 |
|---|---|
| 变量定义 | 排序指令要求：在机制合理性相近时，优先排「主产物 + 必要副产物/参与物覆盖更完整、alignment 可解析」的提案；明确这是排序准则，不改变提案内容，也不要求模型猜判分器。 |
| 证据 | strict 的判定需要必要节点/参与物覆盖；37 题虽然都达到 strict 覆盖，但全部被模型排到第 2 位以后，说明“覆盖完整”没有进入当前排序的首位决策。prompt 只给 preference order，没有覆盖完整性准则。 |
| 预期（方向） | 首位更可能是可被判分覆盖的候选，可能提高 strict 首位率；对覆盖本就不全的题无效。 |
| 风险 | 措辞过强会变成向模型泄露判分口径，甚至诱导模型堆参与物；必须只写“排序时优先考虑已声明的完整产物集”，不写判分内部规则，且需化学评审。 |
| 观测 | 首位候选的 participant 覆盖状态、strict 事件模型 rank、partial/unmatched 桶迁移、提案参与物数量分布。 |

## 3. 组合与优先级建议（只作下一轮排序，不本批实施）

| 优先级 | 变量 | 理由 | 前置 |
|---:|---|---|---|
| 1 | V1 位次理由声明 | 纯可观测性改动，风险最低，为后续变量提供归因标签 | 无 |
| 2 | V3 通道中性 | 本批 33/37 strict 事件是 novel，先防止任何“recorded 优先”的误读 | 可与 V1 同轮设计，但不同批启用 |
| 3 | V2 证据优先 | 最接近“把可判分覆盖放首位”的机制，但需与 V3 的通道中性一起验证 | V1 提供标签后再做 |
| 4 | V5 覆盖完整性优先 | 与判分口径最近，措辞风险最高，需化学评审 | V2 结果后再评估 |
| 5 | V4 去重感知 | 影响面小（本批仅 2 条折叠），优先级最低 | 可独立后置 |

**一次只开一个变量。** 上表是设计顺序，不是同批组合；同批多变量会破坏归因。

## 4. 下一轮预注册必须写死的项（若 CC 决定启用）

1. **单变量声明**：本批只改一个 prompt 变量；模型、题卷、代码、池、profile、gate、超时、
   重试、温度、max_tokens、判分全部与 T-H r2 / 对照臂同值。
2. **prompt 冻结**：候选 prompt 全文入批根，记 SHA256；批中零改动；对照臂用现行 prompt
   同 SHA 冻结。
3. **对照**：同批对照臂（现行 prompt）与处理臂（单变量 prompt）同模型、同题卷、同配置；
   不做跨批差值替代。
4. **主指标**：v2 headline hit@1；同时报告 hit@3/@5、strict 覆盖 U、三桶迁移、
   strict 事件的模型 rank 分布、首位通道分布。
5. **安全门**：strict 覆盖不得比对照臂下降超过既有判定线允许的题数；格式失败/零调用/
   超时单列，不剔题；任何 prompt 改动不得触碰判分器或金标。
6. **停点**：格式失败率显著上升、输出 token 异常、身份/预算/完整性错误即停批报 CC；
   不在失败批上判 prompt 效果。
7. **预期写法**：只写方向与观测指标，不写“预计 +N 题”；37 题是池，+37 是数学上限，
   实际兑现 unknown。

## 5. 明确不做

- **不**把本清单的任一变量塞进当前 T-I 两臂批（当前唯一变量=模型，预注册 §2.1）。
- **不**在本周期改 prompt、改排序策略、改判分或重跑 37 题。
- **不**把 37 题分类写成“换 prompt 可回收 37 题”；回收率 unknown。
- **不**把 V2/V5 写成判分口径披露；任何涉及化学判据的措辞在启用前送化学评审。
- **不**在本周期立项 chain15；chain15 只在执行层修复已实施的分支产出，本批不走该分支。

## 6. 证据路径

- 37 题分类表：`/Volumes/CC/Enzyme_Agent/dependingv43/docs/T_H_TEACHER_LEVER1_RANK_TABLE_2026-10-21.md`
- 机读证据：`/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/t_h_lever1_rank_2026-10-21/lever1_rank.json`
- 全 126 strict 通道背景：`/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/t_h_lever1_rank_2026-10-21/strict126_channel_context.json`
- 现行 prompt：`/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/real_model.py`
- 现行 rank policy：`/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/runflow.py`
- 当前 T-I 单变量预注册：`/Volumes/CC/Enzyme_Agent/dependingv43/docs/T_I_PREREG_2026-10-20.md` §2.1