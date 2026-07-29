> **HISTORICAL / NON-AUTHORITATIVE**
> This document is retained for decision history only.
> Current implementation authority: `plan/final_design.md`, `plan/final_plan.md`, `plan/final_discussion.md`.

# CLAUDE_discussion — 三份 demov2 方案（CLAUDE / ChatGPT / Qwen）交叉评审

> 日期：2026-07-29
> 评审对象：`demov2/plan/` 下三个模型的 design + plan
> 评审者：Claude（含对自己方案的批评）
> 用户目标基准：**LLM 做推理核心 + MCP 工具 + 可靠地从 A→B 类比推出 X→?**，可拒答、可解释、沿用 honest_eval。

---

## 0. 一句话结论

三份方案**不是三选一**，而是各占了"可靠性铁三角"的一个角：

- **ChatGPT** 守住了**科学严谨性**（数据地基、防泄漏、可复现、禁止幻觉），但把 LLM 压得太扁，几乎退回用户当初否决的"LLM 只做编排解释"。
- **Qwen** 守住了**与用户目标的一致性**（LLM 当化学家做推理）和**工程务实**（Phase 0.5 手动验证、多步降解、11–18 天落地）。
- **CLAUDE（我）** 守住了**可解释的推理结构**（潜变量分阶段 + 漏斗归因 + 拒答闸），但在最要害的一点上做了最冒险的选择——**让 LLM 亲自写 SMILES**。

**推荐不是选一份，而是融合**：以 Qwen 的"LLM 定转化+定位点、RDKit 生成结构"为推理主干，强制先补 ChatGPT 揭露的数据地基与防泄漏，再套我的潜变量分阶段做可解释与漏斗归因。理由见 §5。

---

## 1. 三份方案速览对比

| 维度 | CLAUDE（我） | ChatGPT | Qwen |
|---|---|---|---|
| 核心命名 | LLM 潜变量分阶段类比推理 | 受约束混合 Agent | LLM-native 化学推理 v4 |
| **LLM 是否亲自写 SMILES** | ✅ **是**（阶段④ LLM 写 Y，再 validate 打回重写） | ❌ **严禁**（确定性内核生成，LLM 只引用 candidate_id 解释） | ❌ **否**（LLM 定转化类型+位点，RDKit `apply_transformation` 生成产物） |
| LLM 定位 | 每阶段推理核心 | 编排 + 解释（最弱） | 化学家 / 大脑（最强） |
| 候选生成 | LLM 写 → 工具校验 | 确定性图编辑回放 | RDKit 模板迁移 |
| 数据地基 | 沿用现有 honest_eval（默认可信） | **推翻重建**（lineage/角色/防泄漏，判定现有数字 provisional） | 沿用 + 建 SQLite 多维索引 |
| 多步 X→Y→Z | M1 之后 | 单步验收后另开 | ✅ **本轮就做**（降解路径主场景） |
| 拒答 | 四道拒答闸 | 8 类 reason code + precedence | 三级置信 + 6 停止条件 |
| 评估 | honest_eval 三划分 + selective/abstention | **6 层 + 6 种 split + 基线矩阵** | honest_eval 三划分 + 消融 |
| 工程节奏 | M0→M1→M2 里程碑 | 14 个 TDD 任务，数据不过测不写 MCP/LLM | Phase 0.5 手动验证→工具→数据→Agent→评估 |
| 落地速度 | 中 | 慢（地基优先） | 快（有 cheap go/no-go） |
| MCP 成熟度 | 进程内先行，后抽 server | FastMCP + 严格 schema + resource URI + grounding guard（最成熟） | LangGraph + 7 工具（中） |

---

## 2. 核心分歧（逐个深入）

### 分歧 1（最要害）：LLM 到底要不要亲自写 SMILES？

这是三份方案的**真正分水岭**，也是 review 的核心。

- **我的方案**：阶段④让 LLM 亲自写产物 SMILES，写完 `validate_smiles` 校验，非法就打回重写。
- **Qwen**：LLM 只负责"判断这是什么转化 + 应该改哪个位点"，产物 SMILES 由 RDKit `apply_transformation` 确定性生成。
- **ChatGPT**：更狠，LLM 连位点都不自己定，一切结构操作都在确定性内核，LLM 只引用 ID 做解释。

**我的自我批评（必须诚实）**：ChatGPT 对我这一点的批评是**成立且尖锐**的——"把不可复现的语言模型猜测放进化学内核"。让 LLM 写 SMILES 有三个硬伤：
1. **幻觉**：LLM 会写出看似合理、实则价键/化学错误的结构，validate 只能挡掉"非法"，挡不掉"合法但错误"。
2. **不可复现**：同一个 X 两次可能写出不同 Y，破坏 honest_eval 的可复现要求。
3. **无法真正归因**：产物错到底是"推理错"还是"手滑写错 SMILES"分不清。

**但 ChatGPT 也走过头了**：它把 LLM 压成"只引用 ID 解释"，这恰恰是用户在 `NOVEL_SUBSTRATE_REASONING_REDESIGN` 里**明确否决**的定位（"Agent 不负责凭语言直觉直接写 SMILES" → 用户反感这种把 LLM 排除在推理核心外的做法）。用户要的是"LLM 当推理核心"，不是"LLM 当解说员"。

**Qwen 的折中是最优解**：
> LLM 拥有**推理决策权**（判转化类型、定反应位点、判证据是否充分、要不要拒答），RDKit 拥有**结构生成权**（确定性图编辑）。

这样 LLM 仍是"化学家的大脑"（它决定化学逻辑），但不碰"写分子式"这种最容易幻觉、又必须可复现的活。**既满足用户"LLM 推理核心"，又堵住幻觉与不可复现。** 我原方案的阶段④应当据此修正。

### 分歧 2（最重要发现）：数据地基是否可信？

**ChatGPT 抓到了一个能动摇一切的真 bug**，这是三份文档里信息量最大的一条：

> `benchmark/canonical_identity.py` 在反应物侧和产物侧**各自独立**挑"带反应中心的较大非辅酶片段"，没有沿原子映射配对 A 和 B。

举证（脯氨酸羟化反应）：
```
2-氧戊二酸 + 脯氨酸 + O2 → 琥珀酸 + 羟脯氨酸 + CO2
真值主转化应是：脯氨酸 → 羟脯氨酸（2-氧戊二酸→琥珀酸是共底物侧）
但独立挑片段会配成：X=2-氧戊二酸, Y=羟脯氨酸  ❌ 完全错配
```

**如果这个 bug 属实，后果是灾难性的**：`group_key`、`edit_key`、A1/A2 诊断、generation recall、top-K——**全部被污染**。而**我的方案和 Qwen 的方案都默认 honest_eval 是可信的尺子**，这个前提可能不成立。

**这条必须在写任何新推理代码之前先验证**。ChatGPT 主张"数据不过测不写 MCP/LLM"在这一点上是对的——地基裂了，上面盖什么楼都白搭。

（评审附注：需实跑确认该错配的实际发生率。若是普遍现象 → 按 ChatGPT 先修地基；若只是少数边缘 case → 可并行修，不必全停。这一步是**本次讨论后第一件要做的事**。）

### 分歧 3：可靠性基础设施的深度

ChatGPT 在这里**遥遥领先**，且大多是真需求，不是过度设计：
- **train-only 证据隔离**：打分/检索参照必须严格来自 train fold（现有 scorer 只排当前 test group，仍可能读到其他测试反应 → 泄漏）。
- **版本化快照 + 内容寻址 hash + quarantine**：可复现、可回滚、坏数据隔离。
- **provenance / grounding guard**：Agent 最终答案里每个结构必须引用本次 run 的 candidate_id，host 校验 ID 存在——**从架构上杜绝 LLM 编造结构/证据**。
- **ranking_score ≠ probability**：不给未经校准的置信度贴"概率"标签。

我和 Qwen 的方案在这些点上都偏轻。**这些应当直接采纳为地基约束**，与选哪条推理主干无关。

### 分歧 4：单步 vs 多步

- **Qwen 本轮就做多步 X→Y→Z**——这贴合真实场景（生物降解本就是多步到 CO₂）。
- **我和 ChatGPT 都主张先单步跑通再说**。

**评审倾向**：单步正确性是多步的前提，一步都不准，多步只会误差累积。但 Qwen 的多步循环结构（每跳一个证据卡 + 置信衰减 + 停止条件）设计得很清晰，可作为单步验收后的现成蓝图。**建议：单步先立地基，多步用 Qwen 的循环骨架承接。**

### 分歧 5：工程节奏与成本

- **Qwen 的 Phase 0.5 手动验证是神来之笔**：花 1–2 天，人肉喂 20 个案例给 LLM 走推理链，先验证"LLM 到底会不会做这种化学类比"，不行就别投工程。**这是最便宜的方向性 go/no-go，三份里唯一有的，强烈建议采纳并前置到一切之前。**
- **ChatGPT 的 14 个 TDD 任务**质量最高（测试先行、每步可验收、明确 stop conditions），但从头重建数据地基，见到端到端信号慢。
- **我的里程碑**节奏适中，但 M0 直接让 LLM 写 SMILES，等于把最大风险放在最前面还没护栏。

---

## 3. 对每份方案的诚实评价

### CLAUDE（我）
- **优点**：潜变量分阶段（T→S→Δ→Y→E）天然对齐漏斗归因、可解释性和拒答闸；里程碑节奏合理。
- **致命弱点**：阶段④让 LLM 写 SMILES——幻觉、不可复现、归因困难，是三份里最大的可靠性隐患。
- **盲点**：默认 honest_eval 可信，未质疑数据地基；可靠性基础设施（防泄漏/快照/grounding）偏轻。
- **处置**：分阶段推理结构值得保留，但阶段④改为"LLM 定 T+S，RDKit 生成 Y"；地基约束补齐。

### ChatGPT
- **优点**：科学严谨性和工程纪律天花板级；抓到数据错配真 bug；防泄漏/快照/provenance/grounding 是真需求；评估分层最完整。
- **弱点**：把 LLM 压成"只引用 ID 解释"，**偏离用户"LLM 推理核心"目标**，退回被否决的定位；地基全重建导致见效慢。
- **盲点**：几乎不相信 LLM 的化学推理能力，没给 LLM 留推理空间（连位点都不让 LLM 参与）。
- **处置**：**地基与可靠性部分整段采纳**；但 LLM 权限边界要放宽到"LLM 定转化+定位点"，而非只解释。

### Qwen
- **优点**：与用户目标最一致（LLM=大脑）；"LLM 推理 + RDKit 生成结构"的折中最平衡；多步降解贴合真实场景；Phase 0.5 cheap 验证；7 个工具 + SQLite 索引具体可落地；含酶检索。
- **弱点**：数据地基同样默认可信（没接住 ChatGPT 的 lineage bug）；防泄漏/train-only 隔离/provenance 偏轻；置信度是 LLM 主观三级，未校准。
- **盲点**：`transformation_type` 靠规则映射 edit_key，若 edit_key 本身被地基 bug 污染，标签也跟着错。
- **处置**：**作为推理主干采纳**；补 ChatGPT 的地基与防泄漏；置信度后续加校准。

---

## 4. 与用户目标的一致性检验

| 用户目标 | CLAUDE | ChatGPT | Qwen |
|---|---|---|---|
| LLM 做推理核心 | ✅ 但含写 SMILES 风险 | ⚠️ 偏离（仅解释） | ✅ 最贴合 |
| MCP 工具 | ✅ | ✅ 最成熟 | ✅ |
| 可靠地 A→B 类比 | 🟡 幻觉风险 | ✅ 最可靠 | ✅ |
| 可拒答 | ✅ | ✅ 最完整 | ✅ |
| 可解释推理链 | ✅ 最结构化 | 🟡 只解释 ID | ✅ 每步证据卡 |
| 沿用 honest_eval | ✅ 但默认可信 | ⚠️ 判定需重建 | ✅ 但默认可信 |

**结论**：没有任何一份单独完全对齐。Qwen 在"LLM 推理核心"上最贴合用户本意，ChatGPT 在"可靠"上最扎实，我在"可解释结构"上最清楚。**三者互补，应融合。**

---

## 5. 推荐的融合方案（Claude 建议）

**主干取 Qwen，地基取 ChatGPT，推理结构取 CLAUDE。**

1. **LLM 权限边界（取 Qwen，修正我）**：
   LLM 负责推理决策——判转化族 T、定反应位点 S、判证据充分性、决定拒答；**RDKit 确定性生成产物 SMILES**，LLM 不写结构。既是"推理核心"，又无幻觉、可复现。

2. **地基先行（取 ChatGPT，本次讨论后第一件事）**：
   先验证并修复 `canonical_identity` 的 A/B 原子谱系配对 bug；建 train-only 证据隔离、版本化快照、quarantine。**在地基过测前，honest_eval 现有数字一律视为 provisional，不作承诺。**

3. **推理结构（取 CLAUDE）**：
   保留潜变量分阶段（T→S→Δ→Y→E）+ 六道漏斗闸 + 拒答，用于可解释推理链和逐阶段错误归因。阶段④的"生成"换成 RDKit。

4. **防幻觉护栏（取 ChatGPT）**：
   provenance/grounding guard——最终答案每个结构引用本次 run 的 candidate_id，host 校验；ranking_score 不称概率。

5. **验证前置 + 多步承接（取 Qwen）**：
   先做 Phase 0.5 手动 20 例 go/no-go；单步跑通后用 Qwen 的多步循环骨架承接 X→Y→Z。

6. **工程纪律（取 ChatGPT）**：
   测试先行、每阶段 typed 失败（不 silent `[]`）、明确 stop conditions。

**推荐落地顺序**：
```
Phase 0（新增·最先）：验证数据地基 bug 实际发生率
  ├─ 若普遍 → 先修 lineage/角色/防泄漏（ChatGPT Task 3–5、11）
  └─ 若边缘 → 并行修，不全停
Phase 0.5：LLM 手动 20 例 go/no-go（Qwen）
Phase 1：单步引擎 = LLM 定 T+S + RDKit 生成 + 潜变量分阶段 + 拒答（融合）
Phase 2：honest_eval 端到端 + selective/abstention + train-only（融合）
Phase 3：MCP server + grounding guard（ChatGPT）
Phase 4：多步降解路径（Qwen 循环骨架）
```

---

## 6. 待用户拍板的问题

1. **LLM 写不写 SMILES**：接受"LLM 定转化+定位点、RDKit 生成结构"的折中吗？（我建议接受——这修正了我原方案最大的风险，同时仍是"LLM 推理核心"）
2. **地基是否先修**：是否认可"先花时间验证/修 `canonical_identity` 配对 bug，再写新推理代码"？（我建议至少先**验证发生率**再决定停多久）
3. **本轮是否要多步**：单步先行、多步用 Qwen 骨架承接，还是本轮必须端到端多步？
4. **可靠性基础设施深度**：train-only 隔离 + 版本化快照 + grounding guard 是否本轮纳入？（我建议纳入——这是"可靠"的硬支撑）
5. **是否采纳融合方案**：还是坚持三选一（若三选一，我推荐 Qwen 作主干，因它与你"LLM 推理核心"最一致）？

---

## 附：一句话给每份方案

- **ChatGPT**：最像一个严谨的化学数据工程师——它会先质问"你的标签是不是错的"，但差点忘了用户要的是让 LLM 思考。
- **Qwen**：最懂用户要什么——让 LLM 当化学家，但对脚下的数据地基太乐观。
- **CLAUDE（我）**：结构画得最清楚，但把最危险的一步（写 SMILES）交给了最容易幻觉的 LLM，且没质疑尺子本身准不准。
