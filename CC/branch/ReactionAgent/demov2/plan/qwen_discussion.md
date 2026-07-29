> **HISTORICAL / NON-AUTHORITATIVE**
> This document is retained for decision history only.
> Current implementation authority: `plan/final_design.md`, `plan/final_plan.md`, `plan/final_discussion.md`.

# Qwen 讨论报告 — 三份 demov2 设计的交叉审阅与综合建议

> 日期：2026-07-29
> 审阅对象：ChatGPT、Claude、Qwen 三家各自给出的 design + plan
> 角色：作为三个方案的参与者之一，站在用户 CC 的立场做交叉比较

---

## 0. 三份方案的灵魂差异

先不看细节，看每个方案的**核心信念**：

| 模型 | 核心信念 | 一句话总结 |
|------|---------|----------|
| **ChatGPT** | 科学计算必须确定性，LLM 只做解释 | "LLM 是嘴，管线是脑" |
| **Claude** | LLM 能推理化学，但需要工具校验 | "LLM 是脑，工具是校验" |
| **Qwen** | LLM 就是化学家，MCP 是它的手和眼 | "LLM 是脑+手，工具是器材" |

CC 你已经明确选了 **LLM 做核心推理**——这直接否定了 ChatGPT 的核心信念。但 ChatGPT 的方案里有几个**非常重要的洞察**被 Claude 和我都忽略了，值得吸收。

---

## 1. ChatGPT 方案的关键贡献（必须吸收）

### 1.1 🔴 Fragment Lineage Bug — 这是当前系统最大的隐患

ChatGPT 发现了一个我们都没注意到的**数据级 Bug**：

> `canonical_identity.py` 在反应物侧和产物侧分别独立选择"带中心且较大的非辅酶片段"，没有沿原子映射或 fragment lineage 配对 A 与 B。

具体例子：
```
反应：2-氧戊二酸 + 脯氨酸 + O2 → 琥珀酸 + 羟脯氨酸 + CO2

当前系统认为：
  X = 2-氧戊二酸（最大的非辅酶反应物）
  Y = 羟脯氨酸（最大的非辅酶产物）  ← 错！

正确的 A/B 配对应该是：
  A = 脯氨酸 → B = 羟脯氨酸（沿原子谱系配对）
```

**这意味着当前 benchmark 的所有指标（41.5% 检索天花板、A1/A2 分析、generation recall）全部基于可能错误的 A/B 配对，不可信。**

这个发现不管走哪条技术路线都必须修复。Claude 和 Qwen 的方案都假设现有数据是对的，直接用 `canonical_identity.transformed_pair` 提取 A/B——如果 A/B 配对本身就错了，后面所有推理都建在沙子上。

### 1.2 反应账本（Reaction Ledger）

ChatGPT 提出了一个我们都没有的概念：**完整反应账本**。

对于生化反应，不只有主底物→主产物，还有：
- 辅因子消耗（NAD+ → NADH）
- 共底物参与（O2、H2O）
- 副产物生成（CO2、NH3）
- 原子来源追踪（产物中新增的 O 来自 O2 还是 H2O？）

这对污染物降解场景特别重要——比如芳香环羟基化时，新增的 -OH 中的 O 来自 O2 还是 H2O，直接决定了反应的辅因子需求。

Claude 和我的方案都只关注"主底物→主产物"，忽略了反应账本。这会导致：
- LLM 推理时缺少辅因子信息，可能推出化学上不可能的转变
- 多步路径时，辅因子循环（NAD+/NADH）无法追踪

### 1.3 Strict / Generalized 双通道

ChatGPT 的候选分层很精巧：
- **Strict**：来自可信 atom mapping 的精确图编辑回放
- **Generalized**：放宽了部分约束的泛化候选，独立排序并标记为 `exploratory`

这比我们 Qwen 的"三级置信度"更结构化——它不是给一个笼统的"中置信"，而是明确区分"这是精确类比"还是"这是受控泛化"。

### 1.4 版本化证据快照 + 隔离（Quarantine）

ChatGPT 要求数据源必须版本化、可重放、有 content hash。有问题的反应记录进入 quarantine 而不是静默丢弃。这是生产级工程实践，Claude 和 Qwen 都没有。

---

## 2. ChatGPT 方案的致命问题

### 2.1 LLM 角色被过度限制

ChatGPT 明确禁止 LLM：
- 自己解析或修复 SMILES
- 自己做原子映射
- 创造或修改候选 Y
- 改写工具排名、分数或 abstention

这把 LLM 变成了一个**只读解释器**，不是推理核心。CC 你选了"LLM 做核心推理"——这意味着 LLM 必须有权做化学判断，不只是引用工具结果。

### 2.2 工程量过大

14 个 TDD task，每个 task 包含多步实现+测试+commit。按 ChatGPT 自己的估计，至少 4-6 周才能完成到 MCP 层。这还没算 Phase 0 的数据审计。

### 2.3 14 态状态机过于刚性

```
RECEIVE → NORMALIZE → RETRIEVE_DONOR → LOAD_REACTIONS → RESOLVE_ROLES
→ BUILD_TRANSFORMS → ENUMERATE_SITES → APPLY_EDITS → VALIDATE
→ RETRIEVE_SUPPORT → RANK → APPLICABILITY_GATE → FREEZE → REPORT
```

这是传统化学信息学 pipeline 的形态，不是 LLM 推理的形态。LLM 在这种架构里确实只是"最后一公里的解释器"。

---

## 3. Claude 方案的关键贡献

### 3.1 六跳潜变量链 — 最贴合你的推理结构

```
X → ① 检索证据 → ② 判转化族 T → ③ 定位点 S → ④ 写编辑 Δ→Y → ⑤ 评酶 E → ⑥ 置信
```

每一跳都有**拒答闸**，这与你的"保守但可靠"完美对齐。错误可以被定位到具体阶段（T 错 vs S 错 vs Δ 错），方便诊断。

### 3.2 三里程碑递进

- **M0**：单 ReAct 环 MVP（先证明 LLM+MCP 闭环可行）
- **M1**：拆出完整六跳 + 接 honest_eval
- **M2**：校准 + 与旧管线对拍

这比 ChatGPT 的 14 task 更务实，比 Qwen 的 5 phase 更聚焦。每个里程碑独立可验收、可回退。

### 3.3 LLM 亲自写 SMILES 的勇气

Claude 让 LLM 在④亲自写出编辑和产物 SMILES，然后由 `validate_smiles` 校验。这虽然有风险，但**最贴合"LLM 做核心推理"的目标**。如果 LLM 连产物 SMILES 都不能写，那它做什么推理？

---

## 4. Claude 方案的隐患

### 4.1 没有发现 Fragment Lineage Bug

Claude 的方案直接复用了 `canonical_identity.transformed_pair` 做辅酶剥离和反应中心锚定——但 ChatGPT 已经指出这个函数有 A/B 配对错误。**如果 A/B 配对是错的，Claude 的 LLM 拿到的 evidence 就是错的，推理再好也白搭。**

### 4.2 validate_smiles 是事后补救

LLM 写了错误的 SMILES → validate 发现不合法 → 打回重写（有限次数）。这是**事后补救**而非**事前约束**。对复杂分子，LLM 可能反复写出不合法的 SMILES，浪费 token 且不稳定。

### 4.3 对数据质量关注不足

Claude 的方案假设现有 4541 条反应数据基本可靠，主要工作是让 LLM 用好这些数据。但 ChatGPT 的分析表明数据层本身有问题（A/B 错配、group_key 不准、edit_key 太粗）。

---

## 5. Qwen 方案（我们自己）的反思

### 5.1 做得好的部分
- **Phase 0.5 手动验证**：在投入工程前用最低成本验证 LLM 化学推理能力，这是三个方案里最聪明的风险控制
- **7 个 MCP 工具的分工**清晰，覆盖了化学推理全流程
- **多维检索策略**（全文+结构+编辑签名+官能团）比单 Morgan top-K 好得多
- **辛醇推理示例**具体展示了 LLM 推理链的样子

### 5.2 需要改进的部分
- **没有发现 Fragment Lineage Bug**：和 Claude 一样，我们的 `search_reactions` 和 `get_reaction_details` 依赖的底层数据可能是错的
- **没有反应账本概念**：只关注主底物→主产物，忽略辅因子/共底物/副产物
- **数据层设计太粗**：SQLite + JSON 索引只是基本的 CRUD，没有版本化、content hash、quarantine
- **"三级置信度"太笼统**：不如 ChatGPT 的 strict/generalized 分层有信息量
- **没有 strict/generalized 区分**：所有候选一视同仁，没有区分精确类比和受控泛化

---

## 6. 综合建议：取三家之长的融合路线

### 6.1 核心信念：采纳 Claude + Qwen 的共识

**LLM 做核心推理者**，不是管线末端的解释器。但 LLM 的化学输出必须由确定性工具**事前约束 + 事后验证**。

具体做法：
- LLM 有权判断转化族 T、定位反应位点 S、描述结构编辑 Δ
- LLM **描述**编辑意图（如"将 C1 伯醇氧化为醛"），由 `apply_transformation` 工具**执行**生成 SMILES
- 这避免了 Claude 的"LLM 直接写 SMILES"风险，也避免了 ChatGPT 的"LLM 不能推理"限制

### 6.2 Phase 0：采纳 ChatGPT 的数据审计（最高优先级）

**在任何推理代码之前**，先做数据审计：

1. **修复 Fragment Lineage Bug**
   - 重写 `canonical_identity.transformed_pair`，用 atom mapping 沿原子谱系配对 A/B
   - 重新生成所有 4541 条反应的 A/B 对
   - 人工抽检 50 例确认配对正确

2. **建立反应账本**
   - 为每条反应记录完整的辅因子、共底物、副产物信息
   - 追踪新增原子的来源

3. **版本化证据快照**
   - 用 content hash 做不可变快照
   - 有问题的记录进 quarantine 而不是丢弃

### 6.3 Phase 0.5：采纳 Qwen 的手动验证

数据修好后，花 1-2 天手动验证 LLM 化学推理能力。如果 LLM 对 20 个案例的推理正确率不达标，及时调整方向。

### 6.4 推理架构：采纳 Claude 的六跳链 + Qwen 的工具集

```
① 检索证据 [MCP: search_reactions + retrieve_support]
   拒答闸①：证据不足

② 判转化族 T [LLM 推理 + MCP: analyze_diff 交叉验证]
   拒答闸②：转化不一致

③ 定位点 S [LLM 推理 + MCP: analyze_structure 佐证]
   拒答闸③：无可反应位点

④ 描述编辑 Δ + 生成 Y [LLM 描述编辑 → MCP: apply_transformation 执行 → MCP: validate_chemistry 验证]
   拒答闸④：生成失败或验证不通过

⑤ 评酶 E [MCP: search_enzymes + score_candidate]
   拒答闸⑤：无酶支持

⑥ 置信决策 [LLM 综合判断]
   拒答闸⑥：综合证据不足
```

关键改动：
- ④ 不让 LLM 直接写 SMILES，而是**描述编辑意图**，由工具执行（融合三家）
- 每个候选区分 **strict / generalized**（采纳 ChatGPT）
- 输出带**完整反应账本**（采纳 ChatGPT）

### 6.5 工程节奏：采纳 Claude 的 M0/M1/M2

| 里程碑 | 内容 | 采纳来源 |
|--------|------|---------|
| **M-1** 数据审计 | 修 Fragment Lineage + 反应账本 + 版本化快照 | ChatGPT |
| **M0** 手动验证 | 20 例手动走推理链 | Qwen |
| **M1** MVP 单环 | ①→④→⑥ 最小闭环 + 拒答 | Claude |
| **M2** 完整六跳 | 拆出 ②③⑤ + honest_eval | Claude |
| **M3** 校准对拍 | selective/abstention + 基线对比 | Claude + ChatGPT |

---

## 7. 具体工具/概念采纳清单

| 概念/工具 | 来源 | 是否采纳 | 理由 |
|-----------|------|---------|------|
| Fragment Lineage（沿原子谱系配对 A/B） | ChatGPT | ✅ 必采 | 修复数据级 Bug |
| Reaction Ledger（完整反应账本） | ChatGPT | ✅ 必采 | 生化反应需要辅因子追踪 |
| Versioned Evidence Snapshot | ChatGPT | ✅ 必采 | 可复现、可审计 |
| Quarantine（问题记录隔离） | ChatGPT | ✅ 必采 | 不静默丢弃数据 |
| Strict / Generalized 双通道 | ChatGPT | ✅ 采纳 | 比笼统的置信度更有信息量 |
| 14 态状态机 | ChatGPT | ❌ 不采 | 过于刚性，违背 LLM 核心推理目标 |
| LLM 禁止写 SMILES | ChatGPT | ❌ 不采 | 过度限制；改为 LLM 描述编辑、工具执行 |
| 六跳潜变量链 + 拒答闸 | Claude | ✅ 必采 | 最贴合推理结构 + 保守可靠 |
| M0/M1/M2 里程碑 | Claude | ✅ 采纳 | 务实的节奏控制 |
| LLM 直接写 SMILES | Claude | ⚠️ 改良 | 改为 LLM 描述编辑意图 + 工具执行 |
| Phase 0.5 手动验证 | Qwen | ✅ 必采 | 最低成本的方向验证 |
| 7 个 MCP 工具分工 | Qwen | ✅ 采纳 | 工具集设计合理 |
| 多维检索策略 | Qwen | ✅ 采纳 | 比单 Morgan 好得多 |
| 三级置信度 | Qwen | ⚠️ 升级 | 融合 ChatGPT 的 strict/generalized |
| SQLite 数据层 | Qwen | ⚠️ 升级 | 加入版本化和 quarantine |

---

## 8. 对三家 Plan 的评价

| 维度 | ChatGPT | Claude | Qwen |
|------|---------|--------|------|
| **与用户目标对齐** | 🔴 低（LLM 不是推理核心） | 🟢 高 | 🟢 高 |
| **数据质量关注** | 🟢 最强（发现 lineage bug） | 🟡 未关注 | 🟡 未关注 |
| **工程可行性** | 🟡 工程量大（14 task） | 🟢 适中（3 里程碑） | 🟢 适中（5 phase） |
| **风险控制** | 🟡 有验收门但节奏慢 | 🟢 M0 先验证闭环 | 🟢 Phase 0.5 最聪明 |
| **测试覆盖** | 🟢 TDD 最严格 | 🟡 提到但不够细 | 🟡 提到但不够细 |
| **创新性** | 🟡 概念创新（lineage/ledger） | 🟢 架构创新（潜变量链） | 🟡 方法创新（手动验证） |
| **可直接执行** | 🟡 需要大量前置工作 | 🟢 可以立即开始 M0 | 🟢 可以立即开始 Phase 0.5 |

---

## 9. 我的最终建议

### 执行顺序（融合路线）

```
Week 1:  数据审计（ChatGPT 的 Phase 0）
         ├── 修复 Fragment Lineage
         ├── 建立 Reaction Ledger
         └── 版本化快照

Week 1-2: 手动验证（Qwen 的 Phase 0.5）  ← 可与数据审计并行
           └── 20 例手动走推理链，验证 LLM 能力

Week 2-3: MVP 单环（Claude 的 M0/M1）
           ├── 6 个 MCP 工具（Qwen 的工具集，升级加入 lineage + ledger）
           ├── 六跳推理链 + 拒答闸（Claude）
           └── Strict/Generalized 双通道（ChatGPT）

Week 3-4: 完整六跳 + honest_eval（Claude 的 M1）
           └── 三划分端到端指标 + 漏斗归因

Week 4-5: 校准对拍（Claude 的 M2 + ChatGPT 的评估层）
           └── selective/abstention + 与旧管线对比
```

### 关键原则

1. **数据先行**：不管走哪条路线，Fragment Lineage Bug 必须先修
2. **LLM 描述编辑意图、工具执行生成**：不让 LLM 直接写 SMILES，也不把 LLM 降格为解释器
3. **保守但可靠**：六跳拒答闸 + strict/generalized 分层 + 完整反应账本
4. **快速验证**：Phase 0.5 手动验证 + M0 最小闭环，两次验证机会

---

## 10. 一个关键问题需要你确认

ChatGPT 发现的 Fragment Lineage Bug 是否真的存在？它给出的例子（2-氧戊二酸 + 脯氨酸 + O2 → 琥珀酸 + 羟脯氨酸 + CO2）需要验证。如果确实存在，那当前所有 benchmark 数字都需要重新评估。

建议在 Week 1 优先验证这个 Bug 的真实性和影响范围。

---

*本报告由 Qwen 方案的设计者撰写，力求客观评价三家方案的优劣。如有偏颇之处，欢迎 ChatGPT 和 Claude 指正。*
