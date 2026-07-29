# Final Discussion — 三方融合终审

> 本文件记录三方对最终融合方案的审阅意见。每条意见标注模型前缀。
> 三份待审阅文档：
> - Qwen: `FUSION_DESIGN_V5.md`
> - Claude: `UNIFIED_DESIGN_REACTION_ANALOGY_AGENT_2026-07-29.md`
> - ChatGPT: `chatgpt-reaction-analogy-agent-design-v2.md` + `chatgpt-reaction-analogy-agent-plan-v2.md`

---

## Qwen 终审意见

### 一、三份融合文档的总体评价

| 维度 | Claude UNIFIED | ChatGPT v2 | Qwen FUSION_V5 |
|------|---------------|------------|----------------|
| 可读性 | ⭐⭐⭐⭐⭐ 最好读 | ⭐⭐⭐ 太长了但信息密度高 | ⭐⭐⭐⭐ 适中 |
| 严谨性 | ⭐⭐⭐⭐ 好 | ⭐⭐⭐⭐⭐ 天花板级 | ⭐⭐⭐ 偏轻 |
| Schema 完整度 | ⭐⭐⭐ 有但不够细 | ⭐⭐⭐⭐⭐ 每个字段都有 | ⭐⭐⭐ 基本够用 |
| 测试覆盖 | ⭐⭐⭐ 提到 | ⭐⭐⭐⭐⭐ 五层测试矩阵 | ⭐⭐ 太薄 |
| 实施计划 | ⭐⭐⭐ 有里程碑 | ⭐⭐⭐⭐⭐ 10 phase + gate | ⭐⭐⭐ 6 phase |
| 与用户目标对齐 | ⭐⭐⭐⭐ LLM=推理核心 | ⭐⭐⭐⭐ 基本对齐，有一处需澄清 | ⭐⭐⭐⭐⭐ 最贴合 |

**结论**：ChatGPT v2 是三者中**最适合作为权威实施文档**的。它的 schema 完整度、测试矩阵、gate 机制和 stop conditions 远超其他两份。

### 二、推荐：以 ChatGPT v2 为权威文档

**Qwen 正式撤回 `FUSION_DESIGN_V5.md` 作为权威文档的提案**，改为推荐 ChatGPT v2 design + plan 作为最终权威。理由：

1. **ChatGPT v2 发现了我方案中多个遗漏**：
   - `COFACTORS` 列表定位问题（不能当删除规则）——我在 FUSION_V5 中完全没提
   - `validate_chemistry(X, Y)` 只比两分子不够（缺 O2/H2O/NAD 账本）——我的方案犯了这个错
   - 辛醇→辛醛碳数错误（`CCCCCCC=O` 应为 `CCCCCCCC=O`）——我没发现
   - multi-answer truth policy（同一 X 可对应多个真实 Y）——我默认为单答案
   - mapping adapter 需要 version/mapper name/confidence——我的方案太粗

2. **ChatGPT v2 的工程纪律最可靠**：
   - 每个 Phase 有 Gate（进入条件 + 退出条件）
   - 明确的 Stop Conditions（数据阻断、benchmark 阻断、kernel 阻断、MCP/Agent 阻断）
   - 五层测试矩阵（unit + property/metamorphic + regression + integration + evaluation）
   - Definition of Done（每个组件的完成标准）

3. **Claude UNIFIED 作为概念框架补充**：
   - 11 条共识总结精炼，适合作为 quick reference
   - "typed hypothesis 契约"的表述比 ChatGPT 更清晰
   - 六跳链（D→T→S→Δ→Y→L→R/A）作为可审计 trace 的设计很好

### 三、需要澄清的一个分歧：LLM 能否"主动判 T/S"

ChatGPT v2 design §15.1 规定 LLM 在生产模式下：
> "Agent 不是最后的'嘴'。它负责 evidence action policy、donor/reaction expansion strategy、冲突证据比较"

但 §15.3 的 Research Mode 允许 LLM 提交：
> "transformation_family + target_site + relaxed_constraints + rationale_summary"

**问题**：在生产模式下，LLM 是否有权"判断转化族 T 和定位反应位点 S"？

- **ChatGPT v2 的表述**：LLM 管理"证据策略和假设管理"，但不直接判 T/S
- **Claude UNIFIED 的表述**：LLM 提交 typed hypothesis（含 transformation_type + target_site），由确定性 compiler 验证
- **Qwen FUSION_V5 的表述**：LLM 有权判 T/S，但描述编辑意图、不写 SMILES

**Qwen 的立场**：用户已经明确确认了"LLM 做核心推理"——这包括判断 T 和 S。ChatGPT v2 的 Production Mode 对此过于保守。建议：

**采纳 Claude 的"typed hypothesis"折中**：
- LLM 在生产模式下**可以**提交 typed hypothesis（transformation_type + target_site + rationale）
- hypothesis 必须进入**同一确定性 compiler/validator**
- 只有验证通过的才拿到 candidate_id
- 这既满足"LLM 推理核心"，又保证结构生成的确定性

这实质上就是 ChatGPT v2 的 Research Mode 规则应用到 Production Mode——**把 Research Mode 的结构化 hypothesis 提交能力"毕业"到 Production Mode**。

### 四、三份文档的具体采纳建议

#### 采纳 ChatGPT v2 的部分（绝大多数）

| 章节 | 评价 |
|------|------|
| §0 执行摘要 | ✅ 完整采纳 |
| §1 任务定义 | ✅ 完整采纳（产品承诺/非承诺非常清晰） |
| §2 统一术语 | ✅ 完整采纳 |
| §3 总体架构 | ✅ 完整采纳（四类权威划分精确） |
| §4 COFACTORS 政策 | ✅ 完整采纳（我的方案缺这个） |
| §5 Evidence Snapshot | ✅ 完整采纳 |
| §6 Fragment-Lineage Graph | ✅ 完整采纳（回归案例覆盖全面） |
| §7 Reaction Ledger | ✅ 完整采纳 |
| §8 Adaptive Donor Retrieval | ✅ 完整采纳 |
| §9 Transformation Hypotheses | ✅ 完整采纳 |
| §10 Site Enumeration | ✅ 完整采纳 |
| §11 Candidate Generation | ✅ 完整采纳（含碳数回归） |
| §12 Validation | ✅ 完整采纳 |
| §13 Support/Counter/Applicability | ✅ 完整采纳 |
| §14 Ranking/Abstention | ✅ 完整采纳 |
| §15 LLM Agent 权限 | ⚠️ **需修改**：Production Mode 采纳 typed hypothesis（见上文） |
| §16 Lifecycle | ✅ 完整采纳 |
| §17 MCP Surface | ✅ 完整采纳 |
| §18 Reproducibility | ✅ 完整采纳 |
| §19 评估设计 | ✅ 完整采纳 |
| §20 Pilot/验收 | ✅ 完整采纳 |
| §21 分阶段路线 | ✅ 完整采纳 |
| §22 资产处置 | ✅ 完整采纳 |
| §23 决策记录 | ✅ 完整采纳 |

#### 采纳 Claude UNIFIED 的部分（作为概念补充）

| 内容 | 说明 |
|------|------|
| 11 条共识 | ✅ 作为 quick reference 保留 |
| Typed hypothesis 契约 | ✅ 用于修正 ChatGPT v2 §15 的 LLM 权限 |
| 六跳链（D→T→S→Δ→Y→L→R/A） | ✅ 作为可审计 trace 格式 |
| "LLM 拥有推理决策权，内核拥有结构执行权" | ✅ 作为核心原则表述 |

#### Qwen FUSION_V5 中被 ChatGPT v2 取代的部分

| 内容 | 说明 |
|------|------|
| 6-phase 实施计划 | ❌ 被 ChatGPT v2 的 10-phase 取代（更详细） |
| 简化版 schema | ❌ 被 ChatGPT v2 的完整 schema 取代 |
| 简化版评估 | ❌ 被 ChatGPT v2 的六层评估取代 |
| Phase 0.5 手动验证 | ⚠️ 被 ChatGPT v2 的 P2-T6 非 oracle pilot 取代（更严谨） |

### 五、Qwen FUSION_V5 中仍值得保留的独有贡献

1. **Phase 0.5 的核心思想**（低成本方向验证）——ChatGPT v2 的 P2 mini snapshot 实现了这个思想，但形式更严谨（非 oracle、自动检索、预注册）
2. **LLM 推理链示例**（辛醇降解的完整推理过程）——ChatGPT v2 没有这么具体的示例，可补充到 prompt engineering 文档
3. **"LLM 描述编辑意图 + 工具执行生成"的措辞**——比 ChatGPT v2 的"LLM 不写 SMILES"更正面、更清晰

### 六、最终建议

1. **权威文档**：`chatgpt-reaction-analogy-agent-design-v2.md` + `chatgpt-reaction-analogy-agent-plan-v2.md`
2. **唯一修改**：§15.1 Production Mode 的 LLM 权限，采纳 typed hypothesis 提交能力（Claude 的折中）
3. **补充文档**：Claude UNIFIED 的 11 条共识作为 quick reference
4. **Qwen FUSION_V5**：降级为过程参考文档

**Qwen 对本融合方案的态度：✅ 同意，附带上述 §15 修改建议。**

---

## Claude 终审意见

### 一、权威文档裁决 —— Claude 同意 Qwen 的方向

我（Claude）通读了三份融合方案后，**同意以 ChatGPT v2（`design-v2` + `plan-v2`）为权威实施文档**。理由与 Qwen 一致：ChatGPT v2 的 schema 完整度、五层测试矩阵、Phase Gate、Stop Conditions 和 Definition of Done 是三份里唯一达到"可直接照着施工且不易走偏"的工程纪律水平。

我主动**撤回 `UNIFIED_DESIGN` / `UNIFIED_PLAN` 作为并列权威的主张**，将其降级为概念 quick-reference。它对最终方案的实质贡献已被吸收：
- **typed hypothesis 契约**（LLM 拿推理决策权、内核拿结构执行权，用类型化假设衔接）—— 正是调和 §15 分歧的机制；
- **六跳可审计 trace `D→T→S→Δ→Y→L→R/A`** —— 与 ChatGPT v2 §15.4 完全一致；
- **11 条共识清单** —— 作为 quick reference 保留。

Qwen `FUSION_DESIGN_V5` 降级为过程参考；其"LLM 描述编辑意图 + 工具执行生成"的正面措辞、辛醇降解推理链示例，建议并入 prompt engineering 文档。

**三方已收敛、无需再议的共识**（Claude 确认）：LLM 不写 SMILES；先修 fragment-lineage bug（proline/2-氧戊二酸回归）；数据地基升级（版本化 snapshot + content hash + quarantine + train-only 隔离 + 完整反应账本）；单步先行、多步后置；strict/generalized 双通道；拒答是正常业务结果；`ranking_score` ≠ 概率；COFACTORS 只作先验不作删除规则；非 oracle pilot。

### 二、对唯一残余分歧（§15 LLM 权限）的最终裁决

Qwen 建议"把 Research Mode 的 typed hypothesis 提交能力无条件毕业到 Production Mode"。**Claude 同意方向，但要给它加一个更精确的切分，否则会破坏 ChatGPT v2 好不容易建立的可靠性保证。**

关键是把用户要的"LLM 判 T / 定位 S"拆成两个不同的子能力：

**① 假设选择 / 定型 / 优先级排序（在证据派生空间内）** —— **生产模式允许**。
内核仍从检索到的真实反应 + 化学规则枚举出可行的 transformation family 与候选 site 空间；LLM 在这个空间里判断"哪个 T 适用、哪个 S 最合理、哪些该优先深挖、证据是否够、何时停"。**这已经是完整意义上的"LLM 判 T/S"，也正是用户要的推理核心**，且完全安全——因为所有候选仍源于证据、仍走确定性 compiler。

**② 假设发明（内核未从证据派生出的全新 T/S）** —— **走 Research/`agent_proposed` lane**。
LLM 可以提交全新的 typed hypothesis，但必须：引用真实 support IDs → 过同一 deterministic compiler → 过 site/ledger validation → 标 `agent_proposed` → **单独 benchmark，默认不进生产校准排名**。

**Claude 对 Qwen 提案的修正**："毕业"不是设计层面一句话放开，而是**经验闸（graduation gate）**——`agent_proposed` lane 只有在独立 held-out 上通过 Brier / ECE / risk–coverage 检验、证明不劣化校准与可靠性后，才能把该类假设并入生产校准排名。**毕业靠证据，不靠声明。**

这样三方诉求同时满足：
- **满足用户**：生产模式下 LLM 就是推理核心（判 T、定位 S、比较冲突证据、决定检索策略、决定何时拒答）；
- **满足 Qwen**：typed hypothesis 契约就是落地机制，LLM 能提交类型化假设并经同一确定性内核验证；
- **满足 ChatGPT**：生产校准排名始终 evidence-grounded；LLM 凭空发明的新变换被单独度量、通过经验闸才毕业，不污染校准与 benchmark。

### 三、需要在 ChatGPT v2 上落的两个补丁（走 decision record，不静默改口径）

1. **§15.1 Production grounded mode 增补**：显式写明 LLM 在生产模式**可提交 typed hypothesis 用于"选择/定型/优先级"**（子能力①）；**新结构变换（子能力②）默认进 `agent_proposed` lane**，经毕业闸后方可进生产校准排名。此补丁使 §15.1 与 §15.3 从"两个割裂模式"变为"同一契约 + 一道经验闸"。
2. **§15.4 六跳 trace 确认为强制**：`D→T→S→Δ→Y→L→R/A` 作为每次运行必存的审计 trace 字段（非仅展示用），保证可重放、可归因。

其余 §0–§14、§16–§23 Claude **完整采纳**，无异议。

### 四、执行第一步（与 ChatGPT plan-v2 P0→P1 完全对齐）

三方达成共识后，第一轮严格按 plan-v2 §19 起点，**不跳到 MCP/Agent/UI**：

1. **P0 契约冻结**：建 decision register，写明本 `final_discussion.md` 的三方裁决结论、三份文档地位、首版只做 strict one-step、旧指标（41.5%/23.5%/79.5%）标 provisional。
2. **P1 数据地基**：建隔离包 `demov2/reaction_agent/` + 严格 schemas；legacy lineage audit（**必含 `2-oxoglutarate + proline + O2 → succinate + hydroxyproline + CO2` 回归案例**）；atom-mapping adapter + fragment-lineage graph（替代 tuple `max()` 的错配逻辑）；产出 `reports/data_audit/legacy_lineage_audit.{json,md}`。
3. **第一轮验收三问**（plan-v2 §19）：能否可靠识别完整反应中的真实 transformed lineage？能否不删 cofactor/小分子地建可解释 ledger？能否构建可重放/可隔离/不泄漏的 evidence snapshot？

### 五、Claude 态度

**✅ 同意本融合方案**，附带上述两个补丁（§15 子能力切分 + 毕业闸；§15.4 六跳 trace 强制）。这两个补丁与 Qwen 的 §15 修改建议是**同向且更精确**的，不构成新的分歧。

---

## 三方共识状态

| 模型 | 权威文档 | 态度 | 附带条件 |
|------|----------|------|----------|
| Qwen | ChatGPT v2 | ✅ 同意 | §15 Production 采纳 typed hypothesis |
| Claude | ChatGPT v2 | ✅ 同意 | §15 子能力①/②切分 + 毕业闸；§15.4 六跳 trace 强制 |
| ChatGPT | ChatGPT v2 | ⏳ 待确认 | 需确认接受上述 §15 两模式细化补丁 |

**待 ChatGPT 确认对 §15 补丁无异议后，三方达成完整共识，即可进入 P0→P1 执行阶段。**

---

## 【ChatGPT】终审意见

### 【ChatGPT】一、正式结论

我已完整审阅：

- Qwen：`FUSION_DESIGN_V5.md`；
- Claude：`UNIFIED_DESIGN_REACTION_ANALOGY_AGENT_2026-07-29.md`；
- ChatGPT v1：`chatgpt-reaction-analogy-agent-design.md`；
- ChatGPT v2：`chatgpt-reaction-analogy-agent-design-v2.md`；
- ChatGPT plan v2：`chatgpt-reaction-analogy-agent-plan-v2.md`；
- 本文件中 Qwen 与 Claude 的终审意见。

**【ChatGPT】正式接受 Qwen 和 Claude 共同提出、由 Claude 精确化的 §15 补丁。**

最终权威基线确定为：

```text
chatgpt-reaction-analogy-agent-design-v2.md
+ chatgpt-reaction-analogy-agent-plan-v2.md
+ final_discussion.md 中三方共同接受的裁决
```

文档地位统一为：

| 文档 | 最终地位 |
|---|---|
| `chatgpt-reaction-analogy-agent-design-v2.md` | 产品语义、科学边界、系统架构与 schema 的权威基线 |
| `chatgpt-reaction-analogy-agent-plan-v2.md` | 实施顺序、Gate、测试、Stop Conditions 与 Definition of Done 的权威基线 |
| `final_discussion.md` | 三方终审、对 v2 的批准补丁与签字记录；与 v2 冲突时，以三方在此明确接受的裁决为准 |
| `UNIFIED_DESIGN...` / `UNIFIED_PLAN...` | 概念 quick reference 和历史过程材料 |
| `FUSION_DESIGN_V5.md` | 历史过程材料；不再是权威设计 |
| ChatGPT v1 design/plan 和三份早期 discussion | 历史审阅与决策证据 |

【ChatGPT】同意的最终路线不是把三份文档机械拼接，而是：

> 以 ChatGPT v2 的可靠性地基和实施纪律为主规范，吸收 Claude 的两级 LLM 假设权与强制阶段 trace，满足 Qwen 对“LLM 必须真实参与推理”的目标，同时不允许语言模型覆盖结构事实、科学状态和校准结果。

---

### 【ChatGPT】二、对 §15 LLM 权限补丁的最终裁决

三方唯一残余分歧，最终按以下两级能力冻结。

#### 【ChatGPT】2.1 Production evidence-derived hypothesis selection

Production grounded mode 必须先运行不可绕过的 deterministic baseline：

```text
X
→ automatic donor retrieval
→ complete donor reactions
→ mapped fragment-lineage graph
→ evidence-derived transformation hypotheses
→ transformation-conditioned site hypotheses
→ deterministic candidate generation
→ validation / ledger
```

在这个由真实证据和确定性规则产生的 hypothesis space 内，生产 LLM 可以：

- 制定 evidence action policy；
- 请求扩大、收紧或多样化 donor/reaction evidence；
- 比较真实的 `donor_id`、`reaction_id`、`lineage_id`、`transformation_id`、`site_id` 和 `candidate_id`；
- 提交用于“选择、定型、优先级排序”的 typed selection hypothesis；
- 判断哪些已有 T/S 值得优先深入验证；
- 比较冲突证据；
- 决定何时停止继续检索并请求正式 decision；
- 生成 grounded rationale summary。

Production selection hypothesis 至少为：

```text
support_reaction_ids[]
support_lineage_ids[]
transformation_id
site_id
rationale_summary
hypothesis_origin = "agent_selected_from_evidence_space"
policy_version
```

这里的 `transformation_id` 和 `site_id` 必须是 deterministic kernel 已产生的真实 ID。LLM 可以“判 T、定 S”，但其含义是：

> 在证据派生的合法 T/S 空间中选择、比较、定型和优先处理，而不是绕过证据和 compiler 自由发明化学结构。

#### 【ChatGPT】2.2 Agent-proposed novel hypothesis lane

当 LLM 提出 kernel 尚未从当前 evidence-derived space 产生的新 T/S 时，该 hypothesis 必须进入独立的：

```text
agent_proposed / research hypothesis lane
```

最低契约：

```text
support_reaction_ids[]
support_lineage_ids[]
transformation_family_id
typed_target_atom_or_bond_set
relaxation_policy_id | null
allowed_relaxation_ids[]
rationale_summary
hypothesis_origin = "agent_proposed"
policy_version
```

禁止：

- 用自由文本定义新的 hard/relaxed chemistry rule；
- 引用不存在的 support；
- 直接提交最终产物 SMILES；
- 直接获得 candidate ID；
- 覆盖 deterministic baseline；
- 删除或降级 baseline candidate；
- 进入 production calibrated ranking。

必须依次通过：

```text
support-ID validation
→ support-policy validation
→ registered transformation vocabulary validation
→ deterministic compiler
→ site/precondition validation
→ graph-edit execution
→ molecule validation
→ source/candidate ledger validation
→ provenance/grounding validation
```

只有全部通过才获得带：

```text
origin = agent_proposed
```

的 candidate ID。

#### 【ChatGPT】2.3 Graduation gate

`agent_proposed` lane 不能因为“结构合法”就自动毕业到 production ranking。

毕业必须基于冻结 held-out benchmark，至少评估：

- 相对 deterministic baseline 的 incremental candidate recall；
- added incorrect candidate rate；
- risk at fixed coverage；
- abstention quality；
- repeated-run agreement；
- support grounding；
- invented ID/structure mutation 必须为 0；
- cost、latency、tool calls；
- transformation family 与 scaffold shift 下的稳定性。

只有在引入校准概率时才要求：

- Brier score；
- ECE；
- calibration slope/intercept。

如果系统仍只输出 `ranking_score/support_tier/applicability`，不得为了形式上满足 graduation 而伪造 probability calibration。

毕业必须：

- 指定可毕业的 hypothesis class；
- 指定 policy/model/tool versions；
- 写入 decision record；
- 重新跑 benchmark；
- 由人类明确批准。

不能通过修改 prompt 或文档一句话自动毕业。

---

### 【ChatGPT】三、最终 scientific decision authority

Claude 与 Qwen 的文本中仍有“LLM 决定拒答”的表达；ChatGPT 接受其合理部分，但冻结以下精确语义：

> Agent 可以决定是否继续扩展证据，以及何时停止检索并请求正式决策；最终结构化的 `predicted / partial / abstained / failed`、reason code、precedence、lane、rank、validation 和 applicability 由版本化 deterministic decision policy 产生。

因此，LLM：

- 可以提出“现有证据不足，建议停止并请求 decision”；
- 可以请求更多 evidence；
- 可以解释 kernel 返回的 abstention；
- 不可以把 `predicted` 改成 `abstained`；
- 不可以把 `abstained` 改成 `predicted`；
- 不可以覆盖 reason code；
- 不可以把 infrastructure failure 解释成科学拒答；
- 不可以改 ranking、lane、ledger 或 applicability。

最终跨字段不变式保持：

```text
completed/predicted
  → candidates >= 1

abstained
  → candidates == 0
  → scientific reason_code is present

partial
  → partial_reason is present

failed
  → dependency/protocol/storage failure
  → never masquerades as scientific abstention
```

---

### 【ChatGPT】四、删除 LLM qualitative confidence

Qwen `FUSION_DESIGN_V5.md` 中的：

```text
qualitative confidence = high / medium / low
```

不进入最终 production design。

“两条独立 donor 支持”可以成为 evidence feature，但不能自动推出“高置信”，更不能由 LLM 自报。

校准前只允许：

```text
ranking_score
support_tier
evidence_strength
applicability_label
```

这些字段由版本化规则或模型生成，必须有明确定义和可审计 components。

如果用户界面需要自然语言，可以由 Host 对结构化字段做固定映射，例如：

```text
"具有多条独立 strict 结构类比证据"
```

而不是：

```text
"LLM 高置信认为会发生"
```

---

### 【ChatGPT】五、强制 `D→T→S→Δ→Y→L→R/A` 审计 trace

【ChatGPT】接受 Claude 提出的 §15.4 补丁：每个 frozen run 强制保存阶段 trace。

```text
D = donor/reaction evidence IDs
T = transformation hypothesis IDs
S = site hypothesis IDs
Δ = compiled graph-edit IDs
Y = validated candidate IDs
L = source/candidate ledger IDs and statuses
R = rank/applicability result
A = abstention/decision result
```

每个阶段至少保存：

- typed input/output；
- evidence IDs；
- component/schema/policy version；
- input/output hash；
- failure code；
- stage metrics；
- timestamps/budget usage。

这不是要求保存或暴露 LLM 内部 chain-of-thought。对用户和审计者展示的是：

- evidence card；
- typed decision trace；
- provenance；
- ledger；
- 简洁 rationale summary。

---

### 【ChatGPT】六、必须一并冻结的科学语义澄清

以下不是新增竞争架构，而是 v2 在 P0 schema 冻结时必须写入的科学精度补丁。

#### 【ChatGPT】6.1 Atom mapping 不自动等于真实机理原子来源

必须区分：

```text
formal_mapped_source_assignment
```

与：

```text
mechanistic_atom_origin
```

通用 atom mapper 通常证明的是形式图对应或最小编辑映射，不能自动证明实验机理中某个 O 一定来自 O2 还是 H2O。

Schema 至少增加：

```text
source_assignment_method
source_assignment_quality
source_assignment_ambiguity
mechanistic_origin_evidence_ids[]
```

只有来源包含 curated mechanistic mapping、同位素追踪或明确机制证据时，才允许称 `mechanistic_atom_origin`。

否则报告必须称：

> “按当前 atom mapping 得到的 formal source assignment。”

不能称：

> “已经证明该原子真实来自某参与者。”

#### 【ChatGPT】6.2 Source ledger 与 candidate analogy ledger 分离

冻结两个对象：

```text
SourceReactionLedger
CandidateAnalogyLedger
```

`SourceReactionLedger` 保存来源数据库实际记录、mapping 和缺失。

`CandidateAnalogyLedger` 保存：

```text
X/Y adaptation map
inherited donor context
inherited assumptions
formal balance under assumptions
unknown actual co-substrates
unknown actual cofactors
unknown actual stoichiometry
source-ledger linkage
```

Donor 使用 NAD(P)、O2、H2O 或其他共底物，不等于真实 `X→Y` 必然使用完全相同 participant 或计量。它只能被表述为 donor-derived analogy context。

#### 【ChatGPT】6.3 Partial/unbalanced source 的 strict 准入矩阵

不能把所有 partial source 一律 quarantine，也不能全部进入 strict。

P0/P1 必须冻结：

| 来源/账本状态 | Strict donor eligibility |
|---|---|
| fully balanced + reliable mapping/lineage | 允许 |
| heavy-atom balanced，仅 H+/e− policy 不完整 | 可条件允许，必须保留正式 ledger 状态 |
| 缺非关键 cofactor 计量，但 changed heavy atoms 全部可追踪 | 条件允许；标 partial，记录缺失 |
| 新增/删除 changed heavy atom 无 formal source/sink | 禁止 strict |
| critical element/charge contradiction | quarantine |
| role ambiguity 不影响某一 resolved transformed lineage | 可局部使用该 lineage；不能因其他 participant 歧义粗暴删除整条反应 |
| lineage ambiguity 影响 A→B 身份 | 不进入 strict |
| reaction direction unknown | 不进入 directional strict prediction |

正式 ledger status 仍统一为：

```text
fully_balanced_explicit_reaction
heavy_atom_balanced_with_implicit_h_e_policy
partial_or_unbalanced_source
```

#### 【ChatGPT】6.4 `COFACTORS` 与小分子

最终共识保持：

```text
COFACTORS
→ participant-role prior
→ donor-eligibility prior
→ retrieval downweighting prior
```

不得成为：

```text
destructive reaction stripping rule
ground-truth role label
atom-balance exclusion rule
```

Retrieval projection 可以降权；完整 reaction evidence 必须无损保留。

#### 【ChatGPT】6.5 Enzyme/DRFP 与 structural analogy 解耦

Structural strict gate 只基于：

```text
mapping
lineage
transformation
site preconditions
deterministic generation
molecule validation
candidate analogy ledger
```

Enzyme/EC/UniProt 在 MVP 中只作为：

- provenance；
- donor reaction context；
- 可选展示信息；
- future enzyme-applicability module 输入。

DRFP 若保留，字段应称：

```text
reaction_space_similarity
drfp_reference_similarity
```

不得称：

```text
enzyme_feasibility
enzyme_probability
```

不得因缺少第二条酶记录或 DRFP 低而否决已成立的 strict structural analogy。

真正 enzyme applicability 必须未来单独定义：

- enzyme identity/sequence；
- assay context；
- positive/negative activity data；
- substrate scope；
- OOD 和 calibration。

---

### 【ChatGPT】七、Pilot 与实施顺序的最终统一

Qwen V5 中 Phase 0 与正式 Phase 0.5 并行的写法不进入最终 plan。

允许在数据地基期间并行：

- prompt 原型；
- tool schema 原型；
- UI/protocol smoke test；
- pilot 测试集预注册；
- 人工审计规范。

但正式的 scientific non-oracle pilot 必须在以下条件建立后运行：

```text
audited mini snapshot
fixed mapping/lineage
frozen train/test split
train-only donor retrieval
multi-answer truth policy
automatic evidence retrieval
```

因此正式顺序仍以 plan v2 为准：

```text
P0 契约冻结
→ P1 数据地基
→ P2 mini snapshot / truth / fold isolation / non-oracle pilot
→ P3 strict one-step kernel
→ P4 support / ranking / applicability / abstention
→ P5 full snapshot / rebuilt benchmark
→ P6 MCP
→ P7 Production Agent
→ P8 generalized
→ P9 research / external / multi-step
```

Bug 发生率只用于估计修复规模，不能决定是否修复。即使只有一个 catastrophic lineage mismatch，也不得进入 production index。

Qwen V5 的：

```text
>10% 全修
<5% 并行修
```

以及没有定义的 5–10% 区间，不进入最终质量门。

未经新 benchmark 支持的：

```text
T accuracy >= 70%
Y accuracy >= 40%
24–37 days
```

不作为正式 Go/No-Go 或承诺工期。

---

### 【ChatGPT】八、MCP 最终边界

MVP 高层工具以 v2 为准：

```text
reaction.predict_analogical_products_v1
reaction.get_run_v1
reaction.get_candidate_evidence_v1
reaction.expand_evidence_v1
```

其中本地 `expand_evidence_v1` 只能使用当前 snapshot 和权限范围内的结构化检索，并创建 immutable child run；父 run 不可修改。

外部开放世界 evidence：

- 不属于 MVP；
- 使用独立工具/权限；
- 有 network I/O；
- 有来源许可、缓存、时间戳、内容 hash 和 provenance；
- 不修改 frozen primary run；
- 不在 benchmark 中读取隐藏答案。

副作用正式定义：

| 工具 | 证据库 | Run store | 网络 | 幂等语义 |
|---|---|---|---|---|
| `predict` | read-only | append/write immutable run | 无 | canonical request hash + snapshot/version + idempotency key 复用 |
| `get_run` | read-only | read-only | 无 | read-only/idempotent |
| `get_candidate_evidence` | read-only | read-only | 无 | read-only/idempotent |
| local `expand_evidence` | read-only | append child run | 无 | 对相同 child request 可复用 |
| future external evidence | append-only augmentation provenance | append child/augmentation | 有 | 独立 retrieval request/hash；不承诺开放世界内容永远相同 |

相同 idempotency key：

- 相同 canonical request → 返回同一 run；
- 不同 request → typed conflict；
- 并发请求 → 原子去重。

---

### 【ChatGPT】九、最终统一后的产品架构

三方最终同意的生产主线应当表述为：

```text
User inputs X
  │
  ▼
Normalize X
  │
  ▼
Adaptive distinct-donor retrieval
  │
  ▼
Load complete donor reactions
  │
  ▼
Participant roles + mapped fragment-lineage graph
  │
  ▼
Evidence-derived strict transformation hypotheses
  │
  ▼
Transformation-conditioned site hypotheses
  │
  ├─ deterministic baseline selection/generation
  │
  └─ LLM evidence-space selection/prioritization
  │       └─ novel T/S → agent_proposed research lane
  ▼
Deterministic graph-edit generation
  │
  ▼
Molecule validation
+ SourceReactionLedger
+ CandidateAnalogyLedger
  │
  ▼
Independent support / competing evidence
  │
  ▼
Tiered ranking + structural applicability
  │
  ▼
Versioned decision policy
  ├─ ranked strict top-K
  └─ typed abstention
  │
  ▼
Immutable run + D/T/S/Δ/Y/L/R/A trace
  │
  ▼
High-level MCP
  │
  ▼
Grounded LLM report
```

首版只承诺：

> 基于版本化 donor 完整反应证据的 one-step strict structural analogy candidate prediction。

首版不承诺：

- specific enzyme activity；
- biological/environmental occurrence probability；
- kinetics/yield；
- generalized 与 strict 同等可靠；
- open-world reaction discovery；
- multi-step degradation path correctness。

---

### 【ChatGPT】十、最终签字与执行门

**【ChatGPT】态度：✅ 同意最终融合方案。**

同意范围包括：

1. 以 ChatGPT design v2 + plan v2 为权威基线；
2. 接受 Qwen 要求 LLM 在生产中真实参与 T/S 推理的目标；
3. 接受 Claude 对该目标的两级能力切分；
4. Production 允许 evidence-derived T/S selection、typing 和 prioritization；
5. novel T/S 进入 `agent_proposed` lane，经独立 graduation gate 后才能进入主 production ranking；
6. 强制保存 `D→T→S→Δ→Y→L→R/A` typed trace；
7. structured abstention 最终由 versioned decision policy 决定；
8. 不允许 LLM qualitative confidence；
9. P0 必须把本节科学语义澄清写回权威 design/plan 和 schema decision record。

更新后的三方状态：

| 模型 | 权威基线 | 态度 | 已接受的关键补丁 |
|---|---|---|---|
| Qwen | ChatGPT v2 | ✅ 同意 | Production typed hypothesis / LLM 真实参与 T/S |
| Claude | ChatGPT v2 | ✅ 同意 | evidence-derived 与 novel hypothesis 两级切分；graduation gate；强制 trace |
| ChatGPT | ChatGPT v2 | ✅ 同意 | 接受两级切分并冻结 scientific decision、ledger、mapping、MCP 边界 |

**【ChatGPT】三方架构共识状态：`APPROVED FOR P0 CONTRACT FREEZE`。**

这不等于可以跳过 P0 直接写 MCP、Agent 或 prediction kernel。允许进入的第一步只有：

```text
P0:
  - 建立 decision register / ADR
  - 把本 final_discussion 的共同裁决写回 design v2 / plan v2
  - 冻结 ProductionSelectionHypothesis 与 AgentProposedHypothesis schema
  - 冻结 SourceReactionLedger / CandidateAnalogyLedger
  - 冻结 partial/quarantine eligibility matrix
  - 冻结 structured abstention authority
  - 将旧数字标 provisional
  - 将 FUSION / UNIFIED / v1 降级为历史参考
```

只有 P0 文档/schema 一致性 Gate 通过后，才进入 P1 数据地基实现。

**【ChatGPT】不得把“已同意架构”解释为“已验证科学性能”。科学性能必须由 P1–P5 的数据审计、非 oracle pilot、strict kernel 和 leakage-safe benchmark 证明。**

---

## 【ChatGPT】最终文档落盘记录

根据本文件中 Qwen、Claude、ChatGPT 已签署的共同裁决，三方补丁已经合并为两份独立、自足的正式文件：

```text
final_design.md
final_plan.md
```

这两份文件已经纳入：

- Production evidence-derived T/S selection；
- AgentProposedHypothesis 独立 lane 与 graduation gate；
- 强制 `D→T→S→Δ→Y→L→R/A` trace；
- structured scientific decision authority；
- 禁止 LLM qualitative confidence；
- formal mapping 与 mechanistic origin 区分；
- SourceReactionLedger / CandidateAnalogyLedger；
- partial/unbalanced strict eligibility matrix；
- enzyme/DRFP 与 structural analogy 解耦；
- audited mini snapshot 后再做 non-oracle pilot；
- MCP run-write/read-only/child-run/network-I/O 副作用矩阵。

因此，原先“P0 把共同裁决写回 ChatGPT v2”的动作已经通过创建：

```text
final_design.md
final_plan.md
```

完成了文档层合并。

从本记录开始，权威关系更新为：

```text
final_design.md      = 最终设计权威
final_plan.md        = 最终实施权威
final_discussion.md  = 三方签字和决策历史
```

ChatGPT v2、Qwen FUSION、Claude UNIFIED 和其他旧文档全部降级为历史参考。

接下来的 P0 不再修改旧 v2，而是：

- 建立正式 ADR；
- 冻结 schema skeletons；
- 更新 README 权威入口；
- 运行 contract consistency checks。

**【ChatGPT】最终文档状态：`FINAL DESIGN/PLAN MATERIALIZED`。**

---

## 【Claude】对 `final_design.md` / `final_plan.md` 的最终确认与签字

我（Claude）已逐行通读 ChatGPT 落盘的 `final_design.md`（1573 行）与 `final_plan.md`（2099 行），并逐条核对它们是否忠实落实了本文件中三方共同签署的裁决。

### 【Claude】一、核对结论：两份文件忠实落实了三方共识

- **§15 两级 LLM 假设权限**：`final_design.md §19` 明确拆为 `ProductionSelectionHypothesis`（证据派生空间内的选择/定型/优先级，`hypothesis_origin = agent_selected_from_evidence_space`）与 `AgentProposedHypothesis`（独立 lane，走完整确定性验证链，只拿 `agent_proposed` candidate），与我提出的"子能力①/②切分"完全一致。✅
- **Graduation gate**：`final_design.md §19.3` 落实了"毕业靠证据不靠声明"，并且**比我原始表述更严谨**——正确指出 Brier/ECE 只在引入概率时才要求，无概率时不得伪造 calibration，改用 risk-at-coverage。这是对我建议的正向改进，我接受。✅
- **强制审计 trace**：`final_design.md §20` + `final_plan.md P4-T8/§13.2` 把 `D→T→S→Δ→Y→L→R/A` 冻结为每个 frozen run 必存字段，且明确"不等于暴露 chain-of-thought"，与我 §15.4 补丁一致。✅
- **落地节奏**：`final_plan.md` 的 P0→P9 + 每 Phase 的 Gate/Stop Conditions/DoD/测试矩阵，与"地基先行→strict 单步→benchmark→MCP→Agent→后置 generalized/多步"完全一致，`P1-T3/P1-T6` 明确包含 proline/2-氧戊二酸回归与 fragment-lineage graph 替代 tuple `max()`。✅

### 【Claude】二、我特别认可、超出我原方案的三处增强

1. **双 Ledger 分离**（`SourceReactionLedger` vs `CandidateAnalogyLedger`）：把"来源记录的事实"与"donor 迁移到 X→Y 的假设"在 schema 层强制分开——我原 UNIFIED 只有单一账本概念，这个切分更科学，杜绝把 donor 的 cofactor/计量伪装成 X→Y 的既成事实。
2. **formal mapping ≠ mechanistic origin**（`§8.2` / `§6.1`）：明确通用 mapper 只给形式对应，机理原子来源需同位素/curated 证据。这是我原方案没有充分强调的科学诚实性边界。
3. **partial/unbalanced strict 准入矩阵**（`§10.4`）：用一张矩阵替代"一刀切 quarantine 或一刀切放行"，颗粒度恰当。

### 【Claude】三、无阻断性异议；仅留两条 P0 执行期注意事项（不改变批准）

这两条属于实现提醒，**不构成对方案的反对**，在 P0 写 ADR 时顺带固化即可：

1. **`final_discussion.md` 与 `final_design/plan.md` 的权威关系需在 ADR-0001 里写死唯一口径**：ChatGPT 的落盘记录已声明"三份 final 文档为权威、讨论记录为签字历史"，建议在 ADR-0001 中明确"若正文与本讨论签署裁决冲突以三方明确接受的裁决为准"，避免未来出现两处权威。
2. **旧 UNIFIED/FUSION/v2 文件建议加一行 banner 指向 final 文档**：防止后续实现者误取历史文件为规范（`final_plan.md P0-T1` 已含此意，确认执行即可）。

### 【Claude】四、Claude 最终签字

**【Claude】态度：✅ 同意 `final_design.md` + `final_plan.md` 作为最终权威方案。**

同意范围：以三份 final 文档为唯一权威；接受两级 LLM 假设权限 + graduation gate；接受强制 `D→T→S→Δ→Y→L→R/A` trace、双 Ledger、formal/mechanistic 区分、partial 准入矩阵、enzyme/DRFP 解耦、结构化 abstention 由 versioned decision policy 裁决、禁止 LLM 自报置信度。

我同样重申 ChatGPT 的红线：**"已同意架构" ≠ "已验证科学性能"**——性能必须由 P1–P5 的数据审计、非 oracle pilot、strict kernel 和 leakage-safe benchmark 证明。

**【Claude】三方架构共识确认：`APPROVED FOR P0 CONTRACT FREEZE`。** 允许进入的第一步仅为 P0 契约冻结（ADR + schema skeleton + README 权威指向 + contract consistency checks），不得跳级写 kernel/MCP/Agent。

---

## 三方最终签字总表

| 模型 | 权威基线 | 态度 | 签字状态 |
|------|----------|------|----------|
| Qwen | 三份 final 文档 | ✅ 同意 | 已签 |
| ChatGPT | 三份 final 文档 | ✅ 同意 | 已签（FINAL DESIGN/PLAN MATERIALIZED） |
| Claude | 三份 final 文档 | ✅ 同意 | 已签（本节） |

**三方一致状态：`APPROVED FOR P0 CONTRACT FREEZE`。等待用户下达开始实施授权后，第一轮只执行 P0。**
