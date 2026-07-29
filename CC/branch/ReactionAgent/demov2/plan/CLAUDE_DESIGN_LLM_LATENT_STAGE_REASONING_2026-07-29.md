> **HISTORICAL / NON-AUTHORITATIVE**
> This document is retained for decision history only.
> Current implementation authority: `plan/final_design.md`, `plan/final_plan.md`, `plan/final_discussion.md`.

# CLAUDE_DESIGN — LLM 潜变量分阶段类比推理引擎（demov2）

> 日期：2026-07-29
> 状态：设计已获用户批准（brainstorming 阶段完成，进入 writing-plans）
> 定位：**全新架构**，取代确定性管线的"引擎"地位。现有确定性资产降级为 LLM 手里的证据源 / 校验器。
> 配套文件：`CLAUDE_PLAN_LLM_LATENT_STAGE_REASONING_2026-07-29.md`（实施计划）

---

## 0. 一句话目标

构建一个 **LLM 带 MCP 工具**的推理引擎：给它一个未知污染物 X（SMILES）和已知反应证据 A→B，让 LLM **亲自类比推理**出 X 会转变成什么产物 Y，并且**可靠**——证据不足时能拒答、每个预测都带可解释推理链、可用现有 honest_eval 诚实漏斗量化。

---

## 1. 为什么要重做（一致性审阅结论）

用户的核心目标是：**LLM 作推理核心 + MCP 工具 + A→B 类比推出 X→?**。经智能体团队代码级审阅，现状与目标存在根本性偏差：

| 目标关键词 | 现状（代码级证据） | 判定 |
|---|---|---|
| LLM 做推理核心 | 全工作区 `mcp`/`bind_tools`/`tool_call` **零匹配**。ReactionAgent 是 100% 确定性管线（Morgan 检索 → MCS/SMARTS 模板迁移 → DRFP 打分）；`src/` 的 LLM 只做化学名提取/意图分类/酶重排等边缘活 | 🔴 推理核心是算法，非 LLM |
| MCP 工具 | 两套系统均无 MCP 集成 | 🔴 不存在 |
| A→B 类比推理 | 现有"类比"是机械照葫芦画瓢：Morgan 找相似分子 → 硬搬其 SMARTS 模板 RunReactants → DRFP 打分。缺"理解转化概念再迁移"这一步 | 🟡 相似度检索+模板回放，非推理 |

两份历史文档的方向也都偏：
- `HANDOFF_2026-07-28`（解法C·位点驱动检索）= 在确定性检索层内做工程优化，格局太小，完全不碰 LLM/MCP。
- `NOVEL_SUBSTRATE_REASONING_REDESIGN` = 往训练重型神经网络（GNN/Transformer/episodic learning）走，且明确把 Agent 排除在推理核心之外（"Agent 不负责凭语言直觉直接写 SMILES"），与目标相悖。

**本设计的立场**：让 LLM 当司机、把现有化学工具变成它手里的方向盘和仪表盘。

---

## 2. 三条设计基线（用户已锁定）

1. **LLM = 推理核心**：转化族判定、位点定位、结构编辑、产物 SMILES 均由 LLM 亲自推理产出，不由算法生成。
2. **现有资产 = MCP 工具**：能复用的封装为工具复用（检索、DRFP 打分），其余作校验类工具（RDKit 合法性、位点佐证）。
3. **可靠性三件套**：
   - 沿用 `honest_eval.py` 诚实漏斗与三划分口径；
   - 必须能**拒答**（证据不足不硬猜）；
   - 每个预测输出**可解释推理链**。

---

## 3. 系统架构

### 3.1 总览

```
                        ┌─────────────────────────────────────┐
                        │        LLM 推理核心 (Reasoner)        │
                        │  每一阶段亲自推理 + 决定调用哪个工具   │
                        └───────────────┬─────────────────────┘
                                        │ 调用 / 读回
        ┌───────────────────────────────┼───────────────────────────────┐
        ▼                               ▼                               ▼
  证据类工具                        校验类工具                       打分类工具
  retrieve_support_reactions      validate_smiles                score_candidate
  check_reaction_center           (RDKit 合法性/价键)             (DRFP-酶集 Tanimoto)
  (Morgan / 位点检索)             apply_template(对照,可选)
        │                               │                               │
        └───────────────── 全部封装为 MCP tools（现有 core/ 资产）──────┘
```

LLM 不是被固定流水线调用的一个节点，而是**握着工具箱、按推理链主动决策**的核心。分阶段是**推理的结构约束**（保证可解释 + 漏斗归因），不是硬编码的节点路由。

### 3.2 潜变量推理链（六跳）

每一跳 = **LLM 推理 + 工具校验 + 拒答闸门**。潜变量链沿用 `X → T → S → Δ → Y → E → 置信`。

```
输入：X (污染物 SMILES) + 环境上下文 C（可选：好氧/厌氧、介质、pH…）
  │
  ├─① 检索证据
  │     [工具] retrieve_support_reactions(X) → 一组 A→B（含多样性采样，非单一最近邻）
  │     拒答闸①：证据条数 < 阈值 或 相似度全部过低 → 拒答"无类比依据"
  │
  ├─② 判转化族 T
  │     [LLM] 读 A→B 集合，归纳"这些反应本质在做什么变化"（氧化/还原/水解/脱卤/羟基化/裂解…）
  │     [工具·校验] edit_script 签名交叉验证 support set 的变换一致性
  │     拒答闸②：support set 内转化不一致、归纳不出共同族 → 拒答
  │
  ├─③ 定位点 S
  │     [LLM] 在 X 上指出"哪个原子/键会按 T 发生变化"
  │     [工具·佐证] check_reaction_center(X) / 位点检索（解法C 复用）
  │     拒答闸③：X 上不存在可接受 T 的位点 → 拒答
  │
  ├─④ 写编辑 Δ → 产物 Y
  │     [LLM] 亲自写出结构编辑，产出候选 Y（SMILES）
  │     [工具·校验] validate_smiles(Y) 价键/合法性；不合法打回重写（有限次数）
  │
  ├─⑤ 评酶可行 E
  │     [工具] score_candidate(X>>Y) DRFP-酶集打分（现有打分器，top1 77.8%）
  │     [LLM] 结合分数判酶学合理性
  │
  └─⑥ 置信 / 拒答
        [LLM] 综合每步证据强度 → 给校准置信度
        拒答闸④：综合证据不足 → 输出"证据不足，无法可靠预测"
        否则输出：产物 Y + 完整推理链
```

### 3.3 输出契约

预测成功时输出（结构化 JSON + 人类可读）：
- `product_smiles`：LLM 推出的产物 Y（可多候选，带排序）
- `transformation_family`：判定的转化族 T
- `reaction_site`：X 上被改变的原子/键 S
- `graph_edit`：施加的结构编辑 Δ
- `support_evidence`：依据的哪几条 A→B（可回溯）
- `enzyme_feasibility`：DRFP-酶集分数 + 酶学判断
- `confidence`：校准置信度
- `reasoning_chain`：人类可读推理链（供化学家核验）

拒答时输出：`abstain=true` + `abstain_stage`（在哪一闸拒答）+ 原因说明。

---

## 4. MCP 工具箱（封装现有资产）

| MCP 工具 | 来源（现有 core/ 资产） | 输入 → 输出 | 角色 |
|---|---|---|---|
| `retrieve_support_reactions(X, k, diversity)` | `chenyu_features.retrieve_by_substrate`（Morgan r=2,2048bit）+ 解法C 位点检索 | X → 一组 A→B + 相似度 | 找证据 |
| `check_reaction_center(X)` | `chenyu_features.reaction_center_from_chenyu` / `pipeline.extract_reaction_center`(MCS) | X → 候选反应位点原子集 | 位点佐证 |
| `validate_smiles(Y)` | RDKit（`Chem.MolFromSmiles` + 价键/合法性检查） | Y → 合法/非法 + 诊断 | 校验产物 |
| `score_candidate(rxn=X>>Y)` | `reaction_scorer.score_candidates`（DRFP-酶集 max Tanimoto） | X>>Y → 可信度分 | 打分 |
| `apply_template(donor_rxn, X)` | `pipeline.apply_template_to_molecule` / `align_transfer.transfer` | (donor, X) → 机械迁移产物 | 可选对照组 |
| `edit_signature(rxn)` | `edit_script.extract_edit + key()` | rxn → 变换签名 | T 一致性校验 |

**约定**：工具是无状态的纯函数式调用；推理状态（当前 T/S/Δ 假设、证据集）由 LLM 上下文 / 编排层维护。工具内部沿用现有数据根 `ENZYMECAGE_DATA_ROOT` 与 `PYTHONPATH=../core` 约定。

---

## 5. 可靠性设计

### 5.1 honest_eval 漏斗对齐

六道闸恰好构成六个分母，与现有 honest_eval 的 `unparsable/no_donor/no_candidate/not_generated/hit` 口径映射：

```
所有测试 X
  → ① 检索到足够证据      (对齐 no_donor)
  → ② 归纳出转化族 T
  → ③ 在 X 上定到位点 S    (对齐 selection)
  → ④ 生成合法候选 Y      (对齐 no_candidate / not_generated)
  → ⑤⑥ 真产物 top-k 命中  (对齐 hit → 端到端准确率)
```

关键升级：旧 benchmark 报的是"条件排名准确率"（只在候选含真产物时计入分母，且用了 oracle donor / 偷共反应物）；新设计报**端到端 top-k**——分母是全部测试 X，不做 oracle 筛选。

### 5.2 拒答（abstention）

四道拒答闸，任一触发即输出"证据不足"。核心指标：
- **selective accuracy**：高置信（未拒答）预测里的准确率
- **abstention rate**：拒答率
- 理想曲线：随置信阈值提高，selective accuracy 上升、coverage 下降——用于校准。

### 5.3 可解释推理链

每个预测强制带 `reasoning_chain`：依据哪几条 A→B、判成什么 T、改哪个位点 S、施加什么 Δ。供化学家逐环核验，而非只给一个分数。

### 5.4 防作弊约束（继承并强化）

- 去 oracle donor：真实预测不知道哪个 donor 能生成真产物，检索按相似度返回，不用真答案筛。
- 不偷共反应物：输入只有 X（+ 环境 C），共反应物不喂给推理。
- 全 X 进分母：不做"至少两候选/有酶注释"等人为筛选。
- 防酶家族泄漏：沿用 `splits.py` 的 canonical reaction identity 去重与三划分。

---

## 6. 评估方式（沿用现有尺子）

- 用 `honest_eval.py` 三划分（random / scaffold / reaction_family）跑，报**端到端 top-1 / top-3**。
- 新增 `selective_accuracy` 与 `abstention_rate` 两个指标。
- 与旧确定性管线（Morgan+模板+DRFP）**同数据同划分对拍**，量化：
  - LLM 推理核心 vs 机械模板迁移，端到端命中差多少；
  - 拒答换来多少 selective accuracy 提升。
- 成功判据（初版）：在 random 划分，端到端 top-3 覆盖 ≥ 旧管线，且高置信段 selective accuracy 显著高于旧管线整体准确率。

---

## 7. 落地节奏（里程碑）

| 里程碑 | 内容 | 验收 |
|---|---|---|
| **M0 · MVP 单环** | ①→④→⑥ 用单 ReAct 环跑通（LLM + retrieve/validate/score 三工具 + 拒答），验证 LLM+MCP 闭环可行 | 能对少量 case 端到端产出 Y + 推理链 + 会拒答 |
| **M1 · 完整潜变量链** | 拆出 ②③⑤ 完整六跳 + 漏斗归因，接 honest_eval 三划分 | 三划分端到端 top-k + 逐阶段漏斗报告 |
| **M2 · 校准与对拍** | 置信度校准 + selective/abstention 指标 + 与旧管线对拍报告 | 校准曲线 + 对拍结论文档 |

详见 `CLAUDE_PLAN_LLM_LATENT_STAGE_REASONING_2026-07-29.md`。

---

## 8. 边界与非目标

- **不训练神经网络**：不走 REDESIGN 文档的 GNN/Transformer/episodic learning 重型训练路线；推理靠 LLM + 工具，不靠新训练模型。
- **A2 真 novel（全库无类比）不在射程**：这类案例应触发拒答，而非硬造产物。
- **多步降解路径 X→Y→Z**：M0/M1 先做单步 X→Y；多步串接留待里程碑之后（可把单步引擎递归调用，待确认）。
- **冻结资产**：DRFP 打分器、splits 防泄漏逻辑、honest_eval 四类防作弊口径继续沿用，不推倒。

---

## 9. 待用户后续确认的开放项（不阻塞 M0）

1. 环境上下文 C 是否必须建模，还是先忽略（M0 建议先忽略）。
2. 多步路径 X→Y→Z 是否本轮必须（建议留到 M1 之后）。
3. LLM 后端固定 kimi/kimi-k3 还是需要可切换（建议沿用现有 `call_dashscope` 网关）。
4. 是否需要真正的 MCP server 进程（跨进程），还是先用进程内工具接口（function-calling）跑通 M0，再抽成 MCP server（建议后者）。
