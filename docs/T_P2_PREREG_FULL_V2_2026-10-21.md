# P2 完整证据卡 v2 · 预注册（草案，CC 签字前）

> **题域标签：[298 域] = RHEA 通用酶学 / 已见题（post-hoc）。** 本文件全部数字只在该题域内成立，
> 与 dev（B1 环境路径中间步骤）双向不外推。
>
> **性质：证据呈现整包实验，不是纯重排因果。** 完整 v2 证据卡相对 v1 证据卡同时改变字段集合、
> 字段语义、载荷体积（v2 更小）与 JSON 文本空白；可能同时改变模型提案与排名。本批只能估计
> “整包证据呈现差异”，**不识别单字段贡献**，不称纯重排，不称通用能力提升。
>
> **文档状态：DRAFT_NOT_SIGNED。** 本文件是预注册草案，`approval_status` 待 CC/代决填写；
> 只有 CC/代决签字并回填 `approved_at`、`approval_source`、四文书 SHA、模型 ID 与 T-I 结果
> SHA 后，才可作为 `preregistration_approval.json` 的批准文本。**预注册先于付费。**
>
> **本文件不执行任何动作：** 不调用模型/网络、不部署 HPC、不跑付费批、不改代码/证据、
> 不读金标/题面/reference_graphs/env/key、不 push。
>
> 上游与身份：
> - CC 决定：`docs/P2_CC_DECISION_FULL_V2_2026-10-21.md`（2026-10-21，完整 v2、无 token 预算帽、不截断）
> - 冻结设计：`docs/TASK_EVIDENCE_CARD_V2_DESIGN_2026-10-17.md`
>   （SHA-256 `37d85958e02ca5263abb4c0f1a7a98a2177cea73ab451dcd77e74a43f332c4f4`）
> - 设计终认：`docs/EVIDENCE_CARD_V2_DESIGN_CODEX_FINAL_2026-10-18.md`
>   （SHA-256 `48dfc59931c383e640c9753eb4998ec0b25c41648c79b9c489bf835f754f56e7`）
> - 完整 v2 离线实施：`docs/T_P2_EVIDENCE_CARD_V2_IMPL_REPORT_2026-10-21.md`；
>   patch `docs/review_evidence/p2_evidence_card_v2_2026-10-21/impl.patch`
>   （SHA-256 `cd8c03e0a7ebc41e95ad7a1b9f323bda4a48caf3910373039c50f6ce6f9ebbd6`，r2）
> - 全 298 真实池 token 预测量：`docs/T_P2_TOKEN_PREMEASURE_298_2026-10-21.md`
> - 选项/成本：`docs/P2_TOKEN_REVISION_OPTIONS_2026-10-21.md`
> - token 修订方向代决（qwen3.8max 代 Codex）：`docs/P2_TOKEN_REVISION_QWEN_DECISION_2026-10-21.md`
>   （建议 C uniform 13%；**CC 2026-10-21 直接否决 C、选择完整 v2**；见 §4.6）
> - qwen 确认（M1–M3 修正与四个工程选择依据）：`docs/P2_FULL_V2_QWEN_CONFIRM_2026-10-21.md`
> - T-I 模型选择先例：`docs/T_I_PREREG_2026-10-20.md`、`docs/TASK_T_I_LAUNCH_2026-10-20.md`
> - 优化方案 P2 节：`docs/T_H_HIT1_OPTIMIZATION_PLAN_2026-10-20.md` §4 P2

## 0. 一句话与两臂

在同一 298 题卷、同一模型、同一检索池、同一判据/配置/预算语义、**同一新版 prompt** 下，
只把候选证据卡从 **v1 证据卡** 换成 **完整 v2 证据卡**，测全 298 题配对新增/损失/净增、
hit@1/@3/@5、strict(U)、rank>1、分族、novel 首选、失败/unknown 与实际 usage。
token 增量只披露、不设门；strict 净失 ≤−3 为科学停点。

| 臂 | 证据卡 | prompt | 证据载荷 | schema / descriptor | 角色 |
|---|---|---|---|---|---|
| **A = v1-card** | v1 证据卡（现行生产卡） | 两臂共用 v2 prompt | v1 候选证据 + v1 底物证据 | `candidate-evidence-2` / `candidate-evidence-descr-2` | 对照 |
| **B = v2-card** | 完整 v2 证据卡 | 两臂共用 v2 prompt | v2 候选证据 + v2 底物证据 | `candidate-evidence-3` / `candidate-evidence-descr-3` | 处理 |

> **实现现状（必须正视）：** r2 patch 当前支持的是
> `v2 prompt + 无证据` vs `v2 prompt + v2 证据`；**不支持 `v2 prompt + v1 证据卡`**。
> 本文按 `arm_a_definition = v1card` 起草（见 §0.1）；A 臂需要新增一个 `v1card` 模式
> （见 §2.5）。若 CC 改回冻结设计的“A=无证据”，本文作废并另出预注册，不得把两种 A 臂
> 混写为同一实验。

### 0.1 A 臂定义与 provenance（M2 落字）

**`arm_a_definition = v1card`**：A 臂 = v2 prompt + v1 证据卡（`candidate-evidence-2` /
`candidate-evidence-descr-2`，默认 JSON 分隔符），即 §2.3 开关矩阵的 `v1card` 行、§2.5 的
差异表与七条实现要求。

- **这是相对冻结设计的设计修正/新增，不是“回到冻结设计原意”。** 冻结设计
  `docs/TASK_EVIDENCE_CARD_V2_DESIGN_2026-10-17.md` §二.1 原文的 A 臂是
  「用户 JSON 字节兼容回退」（r2 实现为 v2 prompt + 无证据）；该原文保留为历史对照，
  **不适用于本批 A**。
- **provenance：`qwen3.8max 代 Codex 代 CC 确认（CC 2026-10-21 指示，CC 后置复核）`。**
  该确认不是 CC 本人签字、不替代 CC 拍板，也不替代 Codex 正链最终裁定权；CC 签字文本
  必须显式落 `arm_a_definition = v1card`（设计修正/新增）。
- 归档的 CC 决定 `docs/P2_CC_DECISION_FULL_V2_2026-10-21.md` 原文不含“A=v1 卡”字样；
  本口径由 qwen 代确认补链，**不伪填 CC 本人**。
- 未实现、未复审前不签字、不发车：`v1card` 须完成 §2.5 七条 + 任务书 §3.3 最小合同，
  并经 Codex/qwen 复审（付费批仍 NO-GO，见 §7.4 与任务书 §12）。

## 1. 目的、可声明与不可声明

### 1.1 目的

1. 在 298 题域、同一模型、同一题卷/代码/池/profile/gate/超时/重试下，测完整 v2 证据卡
   相对现行 v1 证据卡的首位命中、strict 覆盖、rank>1 与分族变化；
2. 把“卡片整包效应”与“模型/运行面失败”分开报告；
3. 为 CC 决定“是否以 v2 卡替换 v1 卡、是否进入下一轮”提供一次同批配对证据。

### 1.2 可以声明

- 本批 298 题域、本任务形态下的逐臂 hit@1/@3/@5、strict(U)、rank>1、三桶计数；
- 同题 A/B 配对的新增/损失/净增、discordant 对数、精确 McNemar p（描述性，不作判定门）；
- 分族（F1/F2/F3）配对读数；novel 首选占比（按 §5.4 口径）；
- 失败/零调用/unknown 的计数与原因分布；真实批 usage 的已知部分；
- token 披露读数（含代理 tokenizer 与最终 tokenizer 分列；不是放行门）。

### 1.3 不可声明

- 不声明单字段因果（Gasteiger/source/FG delta/product_delta 等任一字段的独立效应）；
- 不声明“纯重排”：模型提案与排名都可能改变；
- 不声明通用酶学能力、跨题域泛化、闭卷能力、稳定模型排序；
- 不把“compiled / 候选被提交 / strict 覆盖”混写成 hit@1；
- 不把本批写成新基线、老师既定目标的达成或 v1 卡已被证伪；
- **不声称 token 门已过，也不声称完整 v2 卡的可负担性已被门证明**；token 只披露（CC 豁免）；
- 不在未过停点/四象限条件时使用“修复”“提升”“有效”等结论词。

## 2. 单变量、冻结面与实现模式

### 2.1 唯一变量

**证据卡版本**：`arm_a_definition = v1card` ⇒ A = v1 证据卡（`candidate-evidence-2` / `descr-2`，
默认 JSON 分隔符）；B = 完整 v2 证据卡（`candidate-evidence-3` / `descr-3`，紧凑分隔符）。
除证据卡外，下列全部同值：

| 项 | 冻结口径 |
|---|---|
| 模型 | 同一模型 ID、同一 env 文件（T-I 选定后写死） |
| 题卷/池/检索 | 同 298 题卷、同 `plan.pools`、同 build 输入；池成员与顺序零变化 |
| 判据/评分 | v2 headline 同一评分器；v1 仅敏感性；判分零 LLM |
| prompt | 两臂共用同一个 v2 prompt（`PROPOSALS_PROMPT_VERSION_V2` = `c24bee42f651c783c9bdcee6e8f547bff63f1f5fee6a4a87f4816e4d15e57598`，chemfix 后实测；两臂同值） |
| profile/gate/超时/重试 | 同值（`max_real_model_requests=3`、`max_format_feedback_rounds=2`、gate 4470/RPM 200/TPM 3M、3600s、传输重试 1 次、429 有界退避） |
| 温度 / max_tokens | 两臂都不发 temperature；都不发 max_tokens（no-cap 语义） |
| workers | 8 / max_in_flight 8 |
| 数据面/分母 | `real`；298 固定；失败/空池/弃权不剔题 |
| 金额帽 | 无（CC 2026-10-21；no-cap 标记 + usage 照记） |

### 2.2 两臂载荷与身份

| 身份键 | A = v1-card | B = v2-card |
|---|---|---|
| `run_identity.strategy.evidence_card_version` | `v1card` | `v2` |
| `evidence_card_enabled` | `true` | `true` |
| `prompt_versions.proposals` | `c24bee42f651c783c9bdcee6e8f547bff63f1f5fee6a4a87f4816e4d15e57598`（v2 prompt，chemfix 后） | 同左 |
| `candidate_evidence_schema_version` | `candidate-evidence-2` | `candidate-evidence-3` |
| `candidate_evidence_descriptor_version` | `candidate-evidence-descr-2` | `candidate-evidence-descr-3` |
| `rdkit_version` | 批内实际版本 | 同左 |
| 证据容器 | v1 候选证据 + v1 底物证据 | v2 候选证据 + v2 底物证据 |
| JSON 分隔符 | 默认（带空格；v1 字节） | 紧凑 `(",", ":")`（仅 v2 B 臂） |

### 2.3 开关矩阵（新增 `v1card`）

| `evidence_card_version` | `evidence_card_enabled` | 行为 | 用途 |
|---|---|---|---|
| 缺省/None/`v1` | False | 旧 v1 prompt、无证据（逐字节旧路径） | 历史/离线 |
| 缺省/None/`v1` | True | 旧 v1 prompt、v1 卡（逐字节旧路径） | 历史/离线 |
| **`v1card`** | **True（必须）** | **v2 prompt、v1 卡** | **P2 A 臂（新增）** |
| `v1card` | False | 拒绝（不定义无证据的 v1card） | 防歧义 |
| `v2` | False | v2 prompt、无证据 | 既有 r2 路径（非本批 A） |
| `v2` | True | v2 prompt、v2 卡 | P2 B 臂 |

### 2.4 冻结项

- v1 证据卡函数/常量、v1 prompt 哈希、v1 无证据路径**不得改**；
- v2 字段面、SMARTS 表、碳氧化态约定、prompt 文本按冻结设计与 r2 patch 执行，不改一字；
- 池/检索/排序/去重/截断/硬拒绝表/调用次数/判分版本/分母**零改动**；
- P0b/D-6 披露块**不是变量**：不消费、不修改、不比较；
- 不新增 `requirement_missing` 负证据、不新增候选硬筛、不加来源配额/偏爱 novel 规则。

### 2.5 与冻结设计的差异（必须签字确认）

冻结设计 `TASK_EVIDENCE_CARD_V2_DESIGN_2026-10-17.md` §二.1 原文的 A 臂是
**“用户 JSON 字节兼容回退”**（r2 实现为 **“v2 prompt + 无证据”**）；本草案按
**`arm_a_definition = v1card`** 起草：**“v2 prompt + v1 卡” vs “v2 prompt + v2 卡”**。
两者不是同一个实验；`v1card` 是**对冻结设计的变更/新增，不是“回到原意”**。该选择的
provenance 见 §0.1（`qwen3.8max 代 Codex 代 CC 确认（CC 2026-10-21 指示，CC 后置复核）`；
不伪填 CC 本人），CC 签字须显式确认本差异表：

| 项 | 冻结设计 A（无证据） | 本草案 A（v1 卡） |
|---|---|---|
| 对照含义 | v2 卡相对“不给卡”的效应 | v2 卡相对“现行 v1 卡”的效应 |
| 与历史 v1 负结果的关系 | 可读“v2 是否比无卡好” | 可读“v2 是否比现行卡好”；更贴近替换决策 |
| 实现 | 已实现（r2） | **未实现，需新增 `v1card` 模式** |
| 本批 token 对照 | +8.2165%（v2 B vs v2 无证据 A） | 需同 prompt 重测（v1 卡 vs v2 卡） |

**新增 `v1card` 模式的实现要求（发车前必须完成并复审）：**

1. `runflow` 接受 `evidence_card_version="v1card"`；`_Driver` 用 v2 system prompt，
   但证据载荷走 v1 `candidate_evidence_payload` + `substrate_evidence_payload`；
2. A 臂用户载荷与既有 v1 B 臂（v1 prompt + v1 卡）**逐字节相同**（system prompt 不同）；
3. A 臂 schema/descriptor 为 v1 版本；B 臂为 v2 版本；两臂 `prompt_versions` 均为 v2；
4. resume 以 `evidence_card_version` 同判据核对；缺失/不符 ⇒ 结构化拒，不静默换臂；
5. off 路径（None/v1）零漂移：prompt/schema/descriptor/payload 字节不变；
6. 测试覆盖：A 载荷字节等价、v2 prompt 哈希不变、A/B 身份键、resume 拒错、双跑字节一致；
7. 该扩展属于**设计/身份变更**，须走 Codex/qwen 复审并写进脚本锁；未复审不签字、不发车。

> **Prompt-卡语义不匹配（披露项）：** 两臂共用 v2 prompt，其“Candidate evidence notes”
> 描述的是 v2 字段集（FG delta、product_delta 等）。A 臂的 v1 卡没有这些 v2 字段，
> 却带有 v1 独有字段（如 source/alignment 明细、Gasteiger 等）未被该 notes 描述。
> 这是本实验 treatment 的一部分，**不是隐藏变量**；不得据此把 A/B 差异读成单字段因果。
> 若 CC 要求严格中性的共享 prompt，须新冻结一个中性 prompt（新哈希、新复审、重测 token），
> 本草案不擅自替换。

> **chemfix 后披露补充（2026-10-21）：** chemfix 的新 v2 prompt
> （`c24bee42f651c783c9bdcee6e8f547bff63f1f5fee6a4a87f4816e4d15e57598`）相对旧版
> 增加了 `n_hits` 定义（distinct matched atom tuples / match sites，可超过官能团数）、
> class-set delta 与 substrate `n_hits` 的区别、unknown 的原因语义（元素域外 / O–O /
> 非 −1 价卤素 / 开放壳层 / 不可得）以及“类表不穷尽、未列出≠不存在”的语义；
> A 臂的 v1 卡没有这些字段。因此 prompt-卡不匹配面**相对旧版扩大**，且仍是 treatment
> 的一部分：B−A 是“**同一 prompt 下 v2 卡 vs v1 卡**”的对照，**不是纯卡版本效应**；
> 不得写成纯重排效应或纯卡面（字段集合）效应。

### 2.6 非盲臂与整包解释

- v2 卡删除了卡内 source 四件，但顶层 `transformation_ref` 保留 ⇒ **非盲臂**：记录身份
  仍可见一次。S1 只检验“卡内重复呈现来源”的挤位假设，不识别 source 单字段因果。
- v2 卡比 v1 卡小约 20.8%（不同 prompt 口径；见 §4），字段集合与体积同时变化；
  A/B 差异是**整包证据呈现差异**（字段 + 语义 + 体积 + 非语义空白），不是纯重排因果。

### 2.7 四个工程选择（qwen 2026-10-21 确认，已落字）

| # | 选择 | 落字结论 | 本预注册锚点 | 任务书锚点 |
|---|---|---|---|---|
| 1 | A 臂 | **`arm_a_definition = v1card`**（v2 prompt + v1 卡） | §0.1、§2.3、§2.5 | §0.1、§3.3 |
| 2 | prompt | **两臂共用 v2 prompt；prompt-卡语义不匹配作为 treatment 披露**；不分臂 prompt | §2.1、§2.5 披露项、§10.3 | §2 冻结面 |
| 3 | 操作入口 | **克隆 `p2_operations.py`，不改 `ti_operations.py`**；阈值/fatal/恢复/barrier/monitor/stop/seal/评分逐字继承，差异仅白名单 | §3.3、§7.4 | §4.1–4.3 |
| 4 | build | **seed build + 字节级复制**（默认）；只复制 build 产物，不复制 `orchestration.json`/`gate/`/cases/状态文件；禁止一臂 seed 一臂独立 | §7.4 | §5.1–5.2 |

- 四选择都是工程选择，不改变 §2.1 唯一变量、§6.1 科学停点与 §7.4 签字前置；
- qwen 确认所附条件已落字：选择 1 的 provenance 见 §0.1；选择 4 的复制/身份门约束见
  任务书 §5.1–5.2；选择 2 的严格中性共享 prompt 出口保留但不默认采用（§2.5）。

### 2.8 化学复审状态（PASS_WITH_CONDITIONS；不是已通过）

P2 涉及两条不同的化学复审线，**不得互相充抵**：

| 复审线 | 文档/结论 | 状态 | 未闭合条件/限度 | 对 P2 的影响 |
|---|---|---|---|---|
| **R4：P0b/D-6 规则级化学评审** | `docs/T_H_P0B_D6_CHEM_REVIEW_2026-10-21.md`（qwen3.8max 代 Codex，2026-10-21；SHA-256 `fba74ea6fe11cdb4efa45e2193f90d3b914b2d20f83aeff1a5f9e5d675416b62`） | **PASS_WITH_CONDITIONS**（CC 2026-10-21 纠正；原文为“规则级语义可接受（可冻结）”，**不改写成 PASS**） | C1 `stereo_only` 粒度解释：含“指定 vs 未指定/增强立体注记差”，不得读作已证构型错误；C2 `isomeric_unspecified` 桶必含同位素/CX 扩展差，不得当纯结构差；C3 空参与物不读 `participant_list_status=partial`（须消费该字段或 proof_scope 明示）；C4 互变/质子化未归一写入 `does_not_prove`；另 **58 条 `principal_stereo_only` / 146 条 `principal_absent` 的化学真伪仍 unknown**，需真实结构复核 | P2 不消费 P0b/D-6；R4 **不能**充抵 P2 的 v2 证据卡化学复审 |
| **P2 v2 证据卡化学复审**（mimo 场景 1 口径） | `docs/T_P2_V2_CHEM_REVIEW_2026-10-21.md`（Stage B 独立复审，代位 mimo 场景 1；**非 mimo 原始回应**；SHA-256 `537047cc3abaf65124b50998fa6bf602755780fad97a17bc5fa9e55881d96b8a`） | **PASS_WITH_CONDITIONS / 未放行**（§2 P1–P7 七项阻断条件未闭合；**不构成化学放行**） | P1 碳酸盐/氨基甲酸酯不得计羧酸；P2 硫代酰胺/脒/胍/硫脲不得计胺；P3 定义 `n_hits`；P4 未列出的类≠不存在；P5 formula/C_ox delta 非配平净反应；P6 O–O/高价卤素 C_ox 必须 unknown 或正确；P7 开放壳层 C_ox 必须 unknown 或正确处理 | 付费批 NO-GO；P2 侧仍需独立 v2 证据卡化学复审/条件闭合，**不能用 R4 充抵** |

- **不把 `PASS_WITH_CONDITIONS` 写成 `PASS`/“化学已过”**；也不把 qwen 的 FAIL/条件事实
  改写成 PASS；
- R4 的 C1–C4 是 P0b/D-6 披露层的措辞/粒度条件，不解除 58/146 的真实结构化学复核挂账；
- P2 付费批在 §7.4 十项前置（含 v2 化学复审闭合）全部闭合前维持 **NO-GO**；
- D-2 离线实施书不得把化学复审写成“已过”而自动放行；先闭合上述条件。

## 3. 模型选择（T-I 依赖）

### 3.1 写死的选臂规则

| T-I 状态 | 条件 | P2 模型 |
|---|---|---|
| **完整有效** | T-I 主比较 B−A 的 hit@1 净增 **≥15 题** **且** T-I M2 桶迁移成立 | 选 **B（挑战臂，DeepSeek）** |
| **完整有效** | 不满足“≥15 且 M2” | 选 **A（基线，GLM）** |
| **未完成 / 无效** | — | **不做模型选择；P2 付费批不启动**（可继续离线准备） |

- “B−A≥15”指 T-I 挑战臂 hit@1 题数减基线臂 hit@1 题数 ≥15（15/298=5.03pp；口径沿
  `docs/T_I_PREREG_2026-10-20.md` §3.2）。
- “M2 成立”指 T-I 预注册 §3.3 的 M2 主判定（A 的 partial+unmatched 两桶在挑战臂中
  hit@1 合计增加 ≥15；A 的原 strict 桶 hit@1 损失 ≤5；strict 覆盖下降 ≤5 题；`c≥1.5b`）。
- **T-I 无效不选 B，也不默认选 A 发车**；只能继续离线准备（`v1card` 模式、token 披露件、
  化学复审、脚本锁等），不得产生付费调用。

### 3.2 “T-I 完整有效”的操作定义

必须同时满足：

1. T-I 两臂都有最终有效批与 `ti_score_complete.json`/评分产物；无未闭合的停批/身份/
   完整性错误；298 题分母完整，失败/零调用如实登记；
2. T-I 结果报告（`docs/T_I_RESULT_<date>.md`）已落盘，含两臂 hit@1/strict/三桶、B−A 配对
   `b/c/net/n_disc`、M2/M1 并列结果与身份表；
3. 结果报告的 SHA-256 记入 P2 批准包；P2 预注册签字文本引用该 SHA；
4. 若 T-I 报告自述批无效、或停点未闭环、或两臂分母不完整 ⇒ 视为无效。

### 3.3 不与 T-I 混批

- P2 有自己的批标签、批根、运行根、批准包、脚本锁、no-cap 标记；**不复制/不续跑 T-I 批**；
- T-I 的读数只用于**选模型**，不作为 P2 的 A 臂、基线或配对对象；
- T-H/chain13/chain14 历史数字只作背景，不参与 P2 配对，不写成同批对照。

## 4. Token 披露（不是门）

### 4.1 CC 决定与口径

CC 2026-10-21：**“我不考虑预算啊 我真不考虑预算 我只要效果好”**。因此：

- P2 采用完整 v2 证据卡；**不设 13% 门、不截断、不设逐题帽、不做 per-question exception**；
- C（逐题预算帽）、A K=1/2、B shared、D、E 等修订方向**关闭**，不作为 P2 主线；
- token 增量改为**披露项**，不是发车障碍；不得因 token 成本改判据/池/排序/评分；
- 真实批的实际 input/output tokens 照记；金额无账单记 `unknown`，不估算、不编单价；
- 最终模型 tokenizer 下的实测仍要做，但只用于**披露与用量核对**，不是放行门。

### 4.2 已知读数（298 题域，代理 tokenizer `87a7830d…`）

以下数字来自 `docs/T_P2_TOKEN_PREMEASURE_298_2026-10-21.md`，口径是
**v2 B vs v2 无证据 A**（同 v2 prompt）；它不是本草案 A（v1 卡）的对照，仅作完整 v2 卡
体积的披露：

| 披露项 | 读数 | 性质 |
|---|---:|---|
| 批合计 v2 B vs v2 A（无证据） | **+8.2165%** | 披露，不是门 |
| 逐题超 13% | **104/298**（真实可请求 104/296） | 披露，不是门 |
| 最大单题增量 | **+64.1263%**（8 候选） | 披露，不是门 |
| 逐题通过（全 298） | 194/298（65.1%） | 披露 |
| v2 B vs 现行 v1 B（v1 prompt + v1 卡） | **−20.8432%**；298/298 更小；最大 −6.6396% | 披露 |
| v2 A（无证据） vs v1 A（无证据） | +4.7733% | prompt 体积差披露 |
| 候选数分布 | 0:60、1:92、2:57、3:53、4:24、5:8、6:1、8:3；≥2 候选 146 题 | 真实池形状 |

> 重要：qwen 2026-10-21 代决仍判“完整 v2 卡 token 门 FAIL”（这是**事实记录**）；
> CC 2026-10-21 直接决定**豁免该门作为 P2 放行门**——不是把 FAIL 改写成 PASS。
> 不得把 +8.2165% 写成“P2 A/B 的 token 增量”，也不得把 104/298 写成“token 门失败/
> 发车障碍”。这些数字只用于如实披露完整 v2 卡的体积。

### 4.3 P2 同 prompt 对比（待测，披露）

本草案 A 是 **v2 prompt + v1 卡**，不是 v1 prompt + v1 卡。因此：

- **A 臂（v1card）与 B 臂（v2）的同 prompt token 对比尚未测量**；现有预测量不能直接
  替代（v1 B 用的是 v1 prompt；v2 prompt 比 v1 prompt 大 136 tok/题量级）。
- 发车前（离线、零模型）必须用与最终模型一致或已登记 SHA 的 tokenizer，按同一 298 输入
  形状测量 A/B 两臂的 system+user 固定载荷，产出
  `p2_token_measure_298_arms.json`：逐题 tokens、批合计、B vs A 增量、逐题分布、
  >13% 题集（**只披露，不设门**）、tokenizer 文件 SHA。
- 该测量**不得**用于截断/改字段/改池/改题；只用于披露与事后 usage 核对。
- 若最终 tokenizer 不可得，记 `tokenizer_unknown`，不得用代理 tokenizer 冒充最终模型；
  真实批 usage 以提供方返回为准。

### 4.4 真实批 usage 记录

| 记录点 | 内容 |
|---|---|
| 预检 | 模型、input/output/total tokens、耗时、金额或 unknown |
| smoke2 / smoke10 | 每臂 usage、失败原因、零调用 |
| full | 每臂 input/output/total tokens、调用数、重试数、零调用、`usage_missing_calls` |
| 格式反馈轮 | 每轮 tokens 计入 usage；不混入离线固定载荷披露 |
| 传输重试 | 每次 HTTP 尝试计入调用/usage（有返回到 usage 时） |
| 失败无 usage | 计 `unknown` 并披露计数，不估算 |
| 金额 | 有账单/价格快照才写实数；否则 `cost_status=no_snapshot`、`cost_known_cny=null` |

### 4.5 最终 tokenizer

- T-I 选模型后，用最终模型 tokenizer 按同口径复测 A/B 固定载荷，登记 tokenizer 文件 SHA；
- 结果只用于披露/用量核对；**不是放行门**；
- 若最终 tokenizer 与代理 tokenizer 读数差异大，如实并列，不据此改 treatment；
- 真实批 usage 与离线固定载荷的差异（反馈轮/重试/输出）在结果报告分列。

### 4.6 qwen 代决建议 C 与 CC 直接决定的冲突记录（必须保留）

qwen3.8max 代 Codex 于 2026-10-21 出 token 设计修订裁决
（`docs/P2_TOKEN_REVISION_QWEN_DECISION_2026-10-21.md`），建议 **C uniform 13% 题级预算帽**：
超帽题全体候选同一等级、按冻结优先级确定性降级；C 落地后 token 门 by construction 通过。
CC 2026-10-21 直接决定优先：**不考虑预算、完整 v2、不截断、token 增量门豁免**
（`docs/P2_CC_DECISION_FULL_V2_2026-10-21.md`）。

| 项 | qwen3.8max 代 Codex（2026-10-21） | CC（2026-10-21） | 本预注册采用 |
|---|---|---|---|
| token 门 | 完整 v2 卡 FAIL；建议 C uniform 13%，使门 by construction 通过 | 不把 token 成本作为约束；**豁免该门** | **CC** |
| treatment | v2 卡 + 题级预算帽（截断=治疗一部分）；schema-4/descr-4/`evidence_truncation`/帽表 | **完整 v2 卡，无帽、无截断、无逐题例外** | **CC** |
| 可负担性声明 | C 只证“带上限卡可负担”，不证完整卡 | 不把 token 当放行障碍；完整卡直接跑，token 只披露 | **CC** |
| 其他前置 | T-I 模型、P2 预注册、v2 化学复审、批级工程、付费代决、Codex 正链复核 | 同左 | **保留** |

执行口径：

1. **不采用 C**；不新增 `evidence_truncation`、不升 schema-4/descr-4、不生成帽表、
   不做截断等级/帽表/policy_version；本批 schema 仍为 `candidate-evidence-3`/`descr-3`；
2. **不写“token 门已过”**；写“qwen 判 FAIL 的事实保留；CC 豁免该门作为 P2 放行门；
   完整 v2 treatment”；
3. qwen 报告中**与 token 门无关**的前置全部保留：T-I 模型选择、P2 独立预注册、
   v2 化学复审、批级工程接入、CC 付费代决、Codex 正链复核确认；
4. qwen 的 C 规则 R1–R9、帽表工件、截断披露、截断/未截断分层停点等**不进入本预注册**；
   若未来 CC 改变决定，另立新预注册，不回写本文件；
5. 本批不引用 C 的 +3.81%/+4.86% 等读数作为任何证据；只引用完整 v2 的披露读数
   （+8.2165%/104/298/+64.13%，口径见 §4.2）；
6. 任何报告/汇报不得把 CC 的豁免写成“token 门通过”或“完整 v2 可负担性已被证明”。

## 5. 指标、分母与分族

### 5.1 主读数

- 全部 298 题配对：A/B 的新增、损失、净增；
- hit@1、hit@3、hit@5（v2 headline；v1 敏感性并列）；
- strict(U) = `buckets.matched_strict` 题数；
- rank>1 = strict 命中但首位 strict 位次 >1 的题数；
- 三桶：`matched_strict` / `matched_participant_coverage_partial` /
  `unmatched_required_node_uncovered`；
- 分族 F1/F2/F3 的上述指标；
- novel 首选占比（§5.4）；
- 失败/零调用/超时/空响应/解析失败/unknown 的计数；
- 实际 usage 与 token 披露读数。

### 5.2 定义

| 指标 | 定义 | 分母 |
|---|---|---|
| hit@1 | 首个 strict 命中位次 ≤1 的题数 | 298 |
| hit@3 / hit@5 | 首个 strict 命中位次 ≤3 / ≤5 的题数 | 298 |
| strict(U) | 有 strict 命中的题数（任意位次） | 298 |
| rank>1 | strict 命中且首个 strict 位次 >1 的题数 | 298 |
| 配对 b | A strict/hit 成立、B 不成立 | 298 |
| 配对 c | A 不成立、B 成立 | 298 |
| net | `c − b` | 298 |
| n_disc | `b + c` | 298 |

- hit@1/strict 的配对表分别报告 `b/c/net/n_disc`；精确 McNemar 双侧 p 作**描述性**披露，
  不单独否决任何结论，不做多重校正。
- 失败/零调用/超时/空响应/解析失败一律计入未命中，不替换题、不补跑换题、不剔题。
- 空池题（预计 60 题）留在分母；可单列披露，不作为剔除理由。
- 已知结构性零调用（NC-9，2 题，qid 前缀见 token 预测量 §8.3）若重现，按未命中计入并
  单列披露；不得当作模型差异。

### 5.3 分族（规则与 F2raw 发车前冻结；F1 评分后冻结；最终分区确定性生成）

| 族 | 定义 | 冻结/生成时点 |
|---|---|---|
| **F2raw 同底物多题面代理池** | 由 run_inputs 的 `substrate_smiles` 分组，同一底物出现在 ≥2 题的题；**不减去 F1** | build/prepare 后、发车前（零题面，仅用底物 SMILES/题号）；写 `p2_family_f2raw.json` 并记 SHA |
| **F1 选择面** | A 臂 strict 命中且首位 strict 位次 >1 的题（strict-rank>1） | A 臂评分后、看 B 配对前冻结（qid 列表）；F1 不参与发车前冻结 |
| **F2 同底物多题面代理面** | `F2raw − F1` | F1 冻结后按已写死规则**确定性生成**（无人工挑选） |
| **F3 其余** | `298 − F1 − F2` | 同上；与 F1/F2 一起写 `p2_family_partition.json` 并记 SHA |

- **时序（M3 修正）：** F2 的定义含“减去 F1”，而 F1 只有在 A 臂评分后（发车后）才能确定；
  因此**发车前不可能冻结最终 F2/F3**。发车前冻结的是 **F2raw 集合 + 分族规则**（含生成算法
  与 SHA）；F1 冻结后按规则确定性生成 F2/F3，不引入事后裁量，也不看 B 结果。
- 三族是**互斥分栏**（F1 优先，F2=F2raw−F1，F3 补集）；另可描述性报告 F2raw∩F1 的重叠计数
  与 F2raw 规模，但停点只按互斥分栏算。
- F1 用 A 臂定义，不用 B 臂，避免“看结果分族”；F2raw 只用预训练输入事实，不看模型输出。
- 预计 F2raw 规模接近 chain14 的 142 题上界代理，但**以实际 run_inputs 计**，不硬编码。

### 5.4 novel 首选占比（工程防退化读数，不是化学正控）

- 分母 = **全部注册题 298**；分子 = 协议解析规范化后 `rank_hypotheses` 首位为 novel 提案的题数。
- 首位定义：rank 字段缺席自动补为提案顺序；显式空 rank 且非空提案 = 合法无首位；
  合法弃权同。无首位/弃权样本**留在分母，不计分子**。
- A/B 并列报告；预注册写“v2 的 novel 首选占比不劣于 A 臂”为工程防退化线，
  **不靠来源配额/偏爱 novel 规则过线**；与 hit/strict 冲突时 hit/strict 优先。
- 该指标是行为读数，不是化学正控；不单独构成停点。

### 5.5 四象限判读（服从停点后适用）

| hit@1 B−A | rank>1 B−A | 本批允许读法 |
|---|---|---|
| ≥0 | ≤0 | 探索性支持字段修正方向；不认证完整因果或科学收益 |
| ≥0 | >0 | 混合结果，待归因；不直接判档位不适 |
| <0 | ≤0 | hit@1 仍未兑现，不因 rank 改善宣布修复 |
| <0 | >0 | 两面仍负；满足最小有效集等前提后**可开启**结构/档位议题；不据单批判普遍不适 |

### 5.6 报告纪律

1. 每张表带 **[298 域]** 标签；v1/v2 分列，禁止混比；
2. 同时给题数与百分比；分母固定 298；
3. 失败、零调用、超时、空响应、解析失败计入未命中，不剔除；
4. 分族同时给 A 锚定与历史对照（后者只作背景）；
5. 不因结果调整 headline、不因某桶好看改分母、不事后增加指标；
6. 不把 token 披露写成门结论；不把单批配对写成稳定效应。

## 6. 停点

### 6.1 科学停点（后置，评分后）

**全局或任一分族（F1/F2/F3）v2 strict 净失 ≤−3** ⇒ 停点复盘。

- 净失定义：`Δstrict_f = strict_count_B(f) − strict_count_A(f) = c_f − b_f`；
  `Δstrict_f ≤ −3` 即“B 比 A 净少 ≥3 题 strict”。
- 只在**全部 298 题评分完成后**计算；**不得中途 peek/提前停**，不得因 interim 读数改
  treatment、改分母、改分族。
- 触发后：不宣布收益、不进入下一轮、不据此改设计/判据；保留现场，报 CC/代决裁定
  （设计失败 / 局部噪声 / 需另轮预注册）。
- 全 298 与分族的读数必须同时报告；不得只报全局不报分族，也不得只报好看的分族。

### 6.2 运行硬停（TI-F1 继承，工程停点）

以下阈值/处置沿用 TI-F1，P2 的 `p2_operations` 克隆逐字继承，阈值零改动：

| 阶段/信号 | 阈值 | 处置 |
|---|---|---|
| 预检 | 401/402/403/400、模型 ID 不符、env 缺失、请求参数不兼容 | 停全部；不 build/不 run；报 CC |
| build | 作业非零、无 BUILD-PASS、build-gate 失败 | 停；不 run；查日志 |
| 身份门 | manifest/fingerprint/逐题 run_input sha 任一不同；缺指纹/空 sha | 停；不 prepare/run |
| prepare | 批准包缺件、SHA 不符、`no_cap_ack!=true`、P2 探针计数异常 | 停；不改审批/不猜 |
| smoke2 | 无“completed 且真实调用可核”；仍有 pending；模型/身份不符；usage 不可解析；fatal | 停两臂 |
| smoke10 | 非豁免 `failed>0`、未登记结构性零调用 >0、仍有 pending | 停该臂并停另一臂；不进 full |
| full | 非模型内容运行失败 >15；pending>0；fatal | 停两臂、保全现场、不在无效批上判 |
| 任一阶段致命信号 | auth/权限/欠费/配额、模型/身份/完整性/no-cap marker/evidence card 版本错误、未登记 CX、连续 2 个不同 qid 的限流/传输故障 | 立即停两臂并保全 |
| 恢复 | 仅 prediction_recovery 白名单、同题同参一次、先保全；二败停 | 不新增重试 |

> 这些是**工程守卫**，不是科学判定线；no-cap 下没有金额停点，token/usage 只记录。
> 科学停点只有 §6.1 的 strict 净失 ≤−3。

### 6.3 失败/零调用/unknown

- 分母固定 298；失败/空池/弃权/零调用不剔题；
- 非模型内容失败 >15 题 ⇒ full 工程停；
- 已登记 NC-9 结构性零调用按未命中计入并单列；其它未登记零调用 ⇒ smoke10/full 停；
- `usage_missing_calls` 单列；金额 unknown 不阻塞；
- 任何 auth/quota/identity/integrity/evidence-card-version 错误 ⇒ 立即停，不自动处置。

### 6.4 停点后的处置

- 保留现场：批根、runs 根、case、日志、stop.json、usage 全部只读保全；
- 不清 stop.json、不移 case、不删证据、不改配置；不自动重跑；
- 新尝试须新批标签/新批根 + 新预注册或 CC 书面偏离批准；旧批封存只读；
- 任何范围外要求（新参数/新 prompt/新判据/换模型/改分母）一律停，另立预注册。

## 7. 预注册/审批字段

### 7.1 本文件签字位（CC/代决逐项填写；填完才可发车）

```yaml
preregistration_id: prereg-p2-298-2026-10-21
approval_status: DRAFT_NOT_SIGNED          # 签字后改为：preregistration_confirmed
approved_at: TBD                            # CC/代决填 ISO8601 签字时间
approval_source: TBD                        # 签字人/渠道（如「CC 2026-10-21 会话确认」）
approval_source_kind: TBD                   # cc_personal | codex_delegated_cc_shijie | qwen_delegated_codex
preregistration_text_sha256: TBD            # 签字后回填本文件 SHA256
task_doc_sha256: TBD                        # TASK_P2_FULL_V2_LAUNCH_2026-10-21.md SHA256
chem_review_doc_sha256: TBD                 # v2 化学复审定稿 SHA256
script_lock_sha256: TBD                     # P2 脚本锁 SHA256
t_i_result_doc_sha256: TBD                  # T-I 最终有效批结果报告 SHA256
model_id: TBD                               # T-I 规则选定后写死
model_selection_rule: T-I有效且B-A>=15且M2成立=>B；T-I有效但不满足=>A；T-I无效=>不发车
batch_tag: p2-298-<YYYYMMDD>                # 发车日实定；两臂同 tag
arms: v1-card / v2-card
arm_a_definition: v1card                    # M2 落字；v2 prompt + v1 卡（见 §0.1/§2.5）
arm_a_definition_provenance: qwen3.8max 代 Codex 代 CC 确认（CC 2026-10-21 指示，CC 后置复核）
arm_a_definition_status: design_change_pending_cc_signature  # 非 CC 本人签字
budget_mode: no_monetary_cap_user_decision  # CC 2026-10-21
user_decision_date: 2026-10-21
cost_cap_cny: null
no_cap_ack: false                           # CC 阅 §4.4 风险段后改 true
token_gate_disposition: waived_by_cc_full_v2_disclosed
decision_caliber: 298配对；strict净失<=-3停点；token只披露；同模型同池同判据；A=v1卡/B=v2卡
```

### 7.2 `preregistration_approval.json` 模板（签字后落批根 record）

```json
{
  "approval_status": "preregistration_confirmed",
  "approved_at": "<CC/代决签字 ISO8601>",
  "preregistration_doc_status": "preregistration_confirmed",
  "preregistration_docs": {
    "prereg": {
      "path": "docs/T_P2_PREREG_FULL_V2_2026-10-21.md",
      "sha256": "<签字后本文件 SHA256>"
    },
    "task": {
      "path": "docs/TASK_P2_FULL_V2_LAUNCH_2026-10-21.md",
      "sha256": "<任务书 SHA256>"
    },
    "chem_review": {
      "path": "docs/T_P2_V2_CHEM_REVIEW_<date>.md",
      "sha256": "<化学复审定稿 SHA256>"
    },
    "script_lock": {
      "path": "docs/T_P2_SCRIPT_LOCK_<date>.json",
      "sha256": "<脚本锁 SHA256>"
    }
  },
  "preregistration_id": "prereg-p2-298-2026-10-21",
  "arm_a_definition": "v1card",
  "arm_a_definition_provenance": "qwen3.8max 代 Codex 代 CC 确认（CC 2026-10-21 指示，CC 后置复核）",
  "arm_a_definition_status": "design_change_pending_cc_signature",
  "model_id": "<T-I 规则选定>",
  "model_selection_evidence": {
    "t_i_result_doc": "docs/T_I_RESULT_<date>.md",
    "sha256": "<T-I 结果报告 SHA256>",
    "net_hit_at_1": "<int>",
    "m2_holds": "<bool>"
  },
  "batch_tag": "p2-298-<YYYYMMDD>",
  "budget_mode": "no_monetary_cap_user_decision",
  "user_decision_date": "2026-10-21",
  "cost_cap_cny": null,
  "no_cap_ack": true,
  "user_authorization": "<CC 预注册定稿 + 付费/HPC 授权文字>",
  "token_gate_disposition": "waived_by_cc_full_v2_disclosed",
  "decision_caliber": "298配对；strict净失<=-3停点；token只披露；同模型同池同判据；A=v1卡/B=v2卡"
}
```

> 该 JSON 只写元数据与文本 SHA，不含任何密钥。四文书快照的文件名 basename 必须与
> `preregistration_docs.<key>.path` 一致；`prepare` 与首付费 `run` 共用同一验证。

### 7.3 四文书

| key | 文档 | 签字前状态 |
|---|---|---|
| `prereg` | 本文件 | 草案 |
| `task` | `docs/TASK_P2_FULL_V2_LAUNCH_2026-10-21.md` | 草案 |
| `chem_review` | `docs/T_P2_V2_CHEM_REVIEW_<date>.md`（mimo 场景 1：v2 字段语义/质子化 SMARTS/碳氧化态约定） | **未放行**（2026-10-21 Stage B 独立复审为 PASS_WITH_CONDITIONS，§2 P1–P7 未闭合；非 mimo 原始回应；见 §2.8） |
| `script_lock` | `docs/T_P2_SCRIPT_LOCK_<date>.json`（P2 patch/扩展/操作脚本逐文件 SHA） | **未生成** |

### 7.4 签字前置（缺一不签）

1. T-I 完整有效、模型按 §3.1 选定，T-I 结果报告 SHA 已登记；
2. `v1card` 模式已实现、测试全绿、Codex/qwen 复审通过；**CC 签字文本显式落
   `arm_a_definition = v1card`（设计修正/新增，provenance 见 §0.1；qwen 代确认不作为
   CC 本人签字）**；
3. v2 化学复审已取得并**条件闭合**（或有 CC 书面接受的条件/偏离）：当前为
   **PASS_WITH_CONDITIONS**（`T_P2_V2_CHEM_REVIEW_2026-10-21.md` §2 P1–P7 未闭合）；
   R4（P0b/D-6）同为 **PASS_WITH_CONDITIONS**（C1–C4 未闭合 + 58/146 化学真伪 unknown），
   且**不能充抵** P2 v2 复审；见 §2.8；
4. 批级工程接入已复审：orchestrator/worker 的 `evidence_card_version` 冻结/透传、
   `p2_operations.py`/`p2_run_wrapper.py`/`sbatch_p2_*` 正负控通过；
5. P2 脚本锁已生成、逐文件 SHA 核对；
6. P2 同 prompt 的 A/B token 披露件已生成（最终 tokenizer 不可得时记 unknown）；
7. 批根/运行根/协调目录/两臂命名已写死；不与 T-I 混批；
8. `no_cap_ack=true`、付费/HPC 授权由 CC/代决落字；
9. 站点 soak/netcheck 在发车新窗全绿（沿 T-I C8 G1–G4）；
10. **Codex 正链复核确认**（qwen 代决不替代正链最终裁定权；正链额度恢复后复核
    设计/实施/放行类结论）。

## 8. 红线

1. 预注册先于付费；无签字不发车、不预检付费调用。
2. 判分/评测零 LLM；模型只出 proposals，不碰判分。
3. 金标隔离：题卷/参考图/逐题 case 只留 HPC 批根；本地只拉指标/身份件；不读金标/题面。
4. 不改判据/池/检索/排序/评分/硬拒绝表/调用次数/分母。
5. 不回溯旧批：T-H/chain13/chain14/T-I 批根只读；P2 新批根独立。
6. 一批跑完、禁止修一点跑一点；批中零代码/配置/prompt/模型改动。
7. 失败/零调用不剔题；不换题、不补跑换题、不按 flake 静默放行。
8. token 只披露、不设门、不截断；不得因 token 成本改 treatment。
9. 不把探针/单批配对写成成绩或稳定效应；不把 weak/mixed 写成“有效”。
10. 不 push；push 时机归 CC。

## 9. 变更控制

- 签字后任何判据、阈值、指标、分母、分族定义、模型 ID、prompt、证据卡版本、代码 commit、
  批标签、预算模式的变化，均视为新预注册或需 CC 书面偏离批准；不得在跑中改，也不得在
  结果出来后改口径重算头条。
- 结果出来后才发现歧义：先按本文件已写死的口径出数，再另文登记歧义；不得回头改口径。
- 任何 auth/quota/identity/integrity/evidence-card-version 错误、范围外要求、费用异常：
  停批、保留现场、报 CC；不自动换模型/加帽/重跑。

## 10. 限度与 unknown

1. **单批、单模型、单次采样**：模型默认采样与时间窗不确定性作为限制披露；不套用多 seed
   判定线；若 CC 要 3 seed，另立预注册。
2. **整包解释**：v2 卡同时改字段、语义、体积与空白；不识别单字段贡献；不称纯重排。
3. **Prompt-卡语义不匹配**：两臂共用 v2 prompt，A 臂 v1 卡带有 v2 notes 未描述的字段；
   这是 treatment 的一部分，已披露（§2.5）。
4. **非语义空白**：A 臂 v1 卡用默认分隔符，B 臂 v2 卡用紧凑分隔符；JSON 解析后字段差异
   之外还有空白差异；下游判分/解析零影响，但单变量叙述必须如实写明。
5. **token 读数**：+8.2165%/104/298/+64.13% 是代理 tokenizer、v2 B vs 无证据 A 的口径；
   P2 A（v1 卡）的同 prompt 对比待测；最终 tokenizer 读数只作披露。
6. **RDKit**：v2 字段依赖 RDKit；实现环境 2026.03.6，HPC venv 记录 2026.03.5。发车前须
   对齐或在实际版本下重跑 v2 确定性锚，并在 run identity 登记实际版本；不得用本地测试
   冒充 HPC 版本。
7. **结构性零调用**：NC-9 2 题可能重现；按未命中计入并单列，不作模型差异。
8. **空池**：预计 60 题空池；留分母，单列披露；不据此剔除。
9. **历史对照**：chain13/chain14/T-H/T-I 数字只作背景，不参与本批配对；不跨批外推。
10. **化学正确性**：本预注册不认证 v2 字段的化学正确性；归 v2 化学复审链；程序/存储事实
    归 Codex/qwen 复审。当前 v2 复审为 **PASS_WITH_CONDITIONS**（P1–P7 未闭合），R4 为
    **PASS_WITH_CONDITIONS**（C1–C4 未闭合 + 58/146 unknown），两者不得互相充抵（§2.8）；
    不得把任一写成“化学已过”。
11. **C 未采用**：qwen 2026-10-21 建议 C uniform 13% 截断；CC 直接否决并选择完整 v2。
    本批无帽表、无 `evidence_truncation`、schema 仍为 3；不得把 C 的 by-construction
    读数或 +3.81%/+4.86% 写成 P2 证据；token 门 FAIL 的事实保留，CC 豁免的是“作为
    P2 放行门”这一项。

## 11. 交付与签字

| 交付 | 路径 |
|---|---|
| 本预注册草案 | `docs/T_P2_PREREG_FULL_V2_2026-10-21.md` |
| 发车任务书草案 | `docs/TASK_P2_FULL_V2_LAUNCH_2026-10-21.md` |
| 完整 v2 实施报告 | `docs/T_P2_EVIDENCE_CARD_V2_IMPL_REPORT_2026-10-21.md` |
| 全 298 token 预测量 | `docs/T_P2_TOKEN_PREMEASURE_298_2026-10-21.md` |
| 选项/成本 | `docs/P2_TOKEN_REVISION_OPTIONS_2026-10-21.md` |
| CC 决定 | `docs/P2_CC_DECISION_FULL_V2_2026-10-21.md` |

**签字位（CC/代决）：**

- 预注册定稿：`approval_status = preregistration_confirmed`；`approved_at`、`approval_source`、
  四文书 SHA、`model_id`、`t_i_result_doc_sha256`、`arm_a_definition = v1card` 全部回填；
- **A 臂定义**：签字文本必须显式写 `arm_a_definition = v1card`（v2 prompt + v1 卡），并按
  §2.5 差异表确认这是相对冻结设计的设计修正/新增（冻结设计原 A=用户 JSON 字节兼容回退/
  无证据，仅作历史对照）；**不得把 qwen 代确认写成 CC 本人签字**；
- 付费/HPC 授权：CC/代决落字，明确 no-cap 与两臂同批；
- `no_cap_ack = true`：确认“无金额帽、费用事后账单回填、金额可能 unknown”；
- 签字文本 SHA 必须由签字后的最终文本计算；不得用草案 SHA 冒充。