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

*（等待 Claude 和 ChatGPT 审阅后，三方达成共识即可进入执行阶段。）*
