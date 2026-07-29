> **HISTORICAL / NON-AUTHORITATIVE**
> This document is retained for decision history only.
> Current implementation authority:
> - plan/final_design.md
> - plan/final_plan.md
> - plan/final_discussion.md


# UNIFIED DESIGN — 反应类比推理 Agent（demov2 三方案融合权威版）

> 日期：2026-07-29
> 状态：融合 CLAUDE / ChatGPT / Qwen 三份 design+plan 及三份交叉 discussion 后的**唯一权威设计**
> 配套：`UNIFIED_PLAN_REACTION_ANALOGY_AGENT_2026-07-29.md`
> 取代关系：三份原始 design/plan 及三份 discussion 降级为**过程参考**，后续实现只以本文件 + 配套 PLAN 为准。

---

## 0. 一句话目标

构建一个 **LLM 做推理核心 + MCP 工具**的引擎：给未知污染物 X（SMILES），系统自适应检索已知反应 A→B 作证据，让 **LLM 类比推理**出 X 会转变成什么产物 Y，并**可靠**——证据不足能拒答、每个预测带可回溯推理链与完整反应账本、可用重建后的诚实漏斗量化。

---

## 1. 为什么是"融合"而不是"三选一"

三份方案各守住"可靠性铁三角"的一角，且三份交叉 discussion 的融合建议**高度收敛**到同一架构：

| 方案 | 守住的角 | 致命短板 |
|---|---|---|
| **ChatGPT**（受约束混合 Agent） | 科学严谨性：数据地基、防泄漏、可复现、禁幻觉 | 把 LLM 压成"只引用 ID 的解说员"，偏离"LLM 推理核心" |
| **Qwen**（LLM-native 化学推理） | 与用户目标一致：LLM 当化学家；工程务实（cheap pilot） | 默认数据地基可信；防泄漏/账本偏轻 |
| **CLAUDE**（潜变量分阶段） | 可解释推理结构：六跳 + 漏斗归因 + 拒答闸 | 让 LLM 亲自写 SMILES（幻觉+不可复现）；未质疑尺子 |

**三份 discussion 一致收敛的 11 条共识**（本设计全部采纳）：

1. **先修数据地基**：`canonical_identity` 的 A/B 原子谱系配对 bug 必须先验证并修复（ChatGPT 发现，Qwen+Claude 均确认为头号隐患）。
2. **LLM 不亲自写 SMILES**：LLM **描述编辑意图**（判转化族 T + 定位点 S），确定性工具（RDKit）**执行生成**产物结构。
3. **LLM 仍是推理核心**：T/S/donor 类比取舍/拒答/解释均由 LLM 决策；结构生成、原子映射、守恒、排名由确定性内核负责。
4. **完整反应账本（Reaction Ledger）**：辅因子/共底物/副产物/原子来源全记，降解场景刚需。
5. **版本化证据快照 + 内容 hash + quarantine**：可复现、可回滚、坏数据隔离而非静默丢弃。
6. **Strict / Generalized 双通道**：取代笼统三级置信度，明确区分"精确类比"与"受控泛化"。
7. **六跳潜变量链 + 拒答闸**：作为推理结构，天然对齐漏斗归因与逐阶段错误定位。
8. **诚实评估**：train-only 证据隔离 + 无泄漏 + 全 X 进分母 + selective/risk–coverage + 多答案真值。
9. **Phase 0.5 手动 go/no-go**（非 oracle 版）：最便宜的方向性验证，前置。
10. **单步先行，多步后置**：单步正确性是多步前提；多步用 Qwen 循环骨架承接。
11. **ranking_score ≠ probability**；provenance/grounding guard 杜绝 LLM 编造结构/证据。

---

## 2. 核心设计裁决：LLM 角色（融合三家的关键桥）

这是三份方案真正的分水岭，本设计给出**最终裁决**：

> **LLM 拥有推理决策权，确定性内核拥有结构执行权，二者用 typed hypothesis 契约衔接。**

| 职责 | 归属 | 说明 |
|---|---|---|
| 判转化族 T（这些 A→B 在做什么变化） | **LLM** | 化学逻辑归纳 |
| 定反应位点 S（X 上哪个原子/键会变） | **LLM** | 条件化于 T、donor 环境 |
| 选哪些 donor 可类比、证据是否充分、要不要拒答 | **LLM** | 推理核心的核心 |
| 生成产物 SMILES / 原子映射 / 守恒账本 | **确定性内核（RDKit + lineage）** | 杜绝幻觉、保证可复现 |
| 排名分数 / 校准置信 / abstention 状态 | **确定性内核** | LLM 不自报"概率" |
| 最终解释（引用 candidate_id/evidence_id 讲清推理链） | **LLM** | grounding guard 校验 ID 存在 |

**两种运行模式**（吸收 ChatGPT 的桥）：

- **Production grounded mode（生产）**：LLM 提交 typed hypothesis（`support_reaction_ids` + `transformation_type` + `target_site` + `relaxed_constraints` + `rationale`），hypothesis 进入**同一确定性 compiler/validator**；只有通过验证的才拿到 `candidate_id`。LLM 不直接写最终 Y，最终结构/分数由内核渲染。→ 用于正式用户与 benchmark。
- **Research hypothesis mode（研究/可选）**：放宽给 LLM 更多假设自由度，结果**单独标记、单独 benchmark、不进生产校准排名**。→ 保留"LLM 能否像化学家提假设"的研究价值，不牺牲生产可靠性。

这样既满足用户"LLM 推理核心"，又堵住"写 SMILES"的幻觉与不可复现。

---

## 3. 数据地基（取 ChatGPT，最高优先级）

一切推理代码之前先立地基。**地基过测前，honest_eval 现有数字（41.5% / 23.5% / 79.5% 等）一律视为 provisional，不作承诺。**

### 3.1 Fragment Lineage 修复（头号 bug）

现状：`benchmark/canonical_identity.py` 在反应物侧与产物侧**各自独立**挑"带反应中心的较大非辅酶片段"，不按原子映射配对 A/B。

```
反应：2-氧戊二酸 + 脯氨酸 + O2 → 琥珀酸 + 羟脯氨酸 + CO2
错配：X=2-氧戊二酸, Y=羟脯氨酸        ❌
正确：A=脯氨酸 → B=羟脯氨酸（沿原子谱系配对） ✅
```

修复方案：用 **bipartite fragment-lineage graph** 替代"各自挑最大片段 + `max()`"：

```
reactant participant ─mapped overlap fraction─▶ product participant(s)
                     ─changed mapped atoms─
                     ─role hypotheses─
                     ─ambiguity set─
```

- 一个完整反应可贡献**多条**可类比 transformed participant lineage，不强制只有一个全局 primary A。
- tie / ambiguity **必须显式报错并进 quarantine**，不允许 tuple `max()` 静默择一。

### 3.2 Reaction Ledger（完整反应账本）

对每条反应记录，不止"主底物→主产物"，还需：

```
participant roles       : target_substrate / co_substrate / cofactor / spectator
                          target_product / byproduct / unknown
stoichiometry           : 各 participant 计量
atom transfer           : 产物新增原子来源（O 来自 O2 还是 H2O？）
element / charge balance : 元素与电荷守恒状态
H / proton / electron    : 显式/隐式 H 策略、质子电子账
mapping coverage / confidence
```

账本状态至少三档：`fully_balanced_explicit` / `heavy_atom_balanced_with_implicit_H_policy` / `partial_or_unbalanced`。

**守恒必须基于完整反应账本验证，不能只比 X/Y 两分子的分子式差**（否则 O2/H2O 引氧、NAD(P)/FAD 氧化还原、CO2 羧化脱羧、转移酶、裂解多产物全部处理错）。

### 3.3 版本化快照 + Quarantine

- 数据源版本化、可重放、内容寻址 hash。
- 问题记录（catastrophic A/B mismatch、unresolved lineage、role 歧义、不守恒）进 **quarantine**，附明确 reason，不进生产索引，不静默丢弃。
- "4541 条全部入库"不是目标；**质量**才是。

### 3.4 train-only 证据隔离

检索/打分参照必须严格来自 train fold。现有 scorer 只排当前 test group，仍可能读到其他测试反应 → 泄漏。按 fold 建独立证据视图。

---

## 4. 推理架构：六跳潜变量链（取 CLAUDE 结构 + Qwen 执行 + ChatGPT 双通道）

潜变量链 `X → T → S → Δ → Y → L → R/A`，每跳 = **LLM 推理决策 + 工具执行/校验 + typed 拒答闸**：

```
输入：X (污染物 SMILES) + 环境上下文 C（可选）
  │
  ├─① 检索证据  [工具] adaptive donor retrieval（先选 distinct donor 分子 A，再载入每个 A 的完整 A→B 反应）
  │     拒答闸①：无足够类比证据（no_donor）
  │
  ├─② 判转化族 T  [LLM] 归纳 support set "本质在做什么变化"
  │     [工具·校验] edit_signature / analyze_diff 基于 mapped lineage 交叉验证一致性
  │     拒答闸②：support set 转化不一致，归纳不出共同族
  │
  ├─③ 定位点 S  [LLM] 在 X 上指出按 T 会变的原子/键，条件化 p(S | X, T, donor 环境)
  │     [工具·佐证] analyze_structure / 条件化位点枚举
  │     拒答闸③：X 上无可接受 T 的位点
  │
  ├─④ 编辑 Δ → 产物 Y
  │     [LLM] **描述**编辑意图（typed hypothesis：transformation + target_site + relaxed_constraints）
  │     [工具·执行] 确定性图编辑（RDKit apply_transformation）生成 Y —— LLM 不写 SMILES
  │     [工具·校验] validate_chemistry + 完整 reaction ledger 守恒
  │     拒答闸④：生成失败 / 账本不守恒 / 新增重原子无来源
  │
  ├─⑤ 支持与反证 L  [工具] support 聚合（independent evidence identity）+ counterevidence
  │     [工具] 酶 provenance / DRFP 弱排序特征（仅作特征，不当酶活概率）
  │
  └─⑥ 排名 / 适用性 / 拒答 R/A
        [工具] tiered ranking（strict > generalized，不跨 lane 比 raw score）+ applicability gate
        [内核] ranking_score / support_tier / applicability（非"概率"）
        拒答闸⑤：综合证据不足 → typed abstention（reason_code）
        否则输出：ranked top-K 候选（每个带 donor / T / S / Δ / ledger / evidence）
```

- **每跳保存 typed input/output + failure code + component version + input/output hash + stage metric**（把 Claude 的潜变量变成可审计 trace；不要求暴露完整 chain-of-thought，对用户展示 evidence card）。
- **单步先做通**；多步 X→Y→Z 后置，用候选图（canonical node 去重 + cycle detection + branch/depth/cost budget + 逐边 provenance），不是线性递归。

---

## 5. MCP 工具箱（融合三家，封装现有资产）

### 5.1 内部 / 只读证据工具（取 Qwen，约束化）

| 工具 | 来源资产 | 角色 |
|---|---|---|
| `chem.analyze_structure_v1` | RDKit | 结构分析佐证 S |
| `reaction.analyze_diff_v1` | `edit_script` / lineage | **基于 mapped lineage** 的 A→B 差异（校验 T） |
| `reaction.get_details_v1` | reaction ledger | 完整反应 + 辅因子 + 中心 + EC/UniProt |
| `evidence.search_structured_v1` | Morgan 检索 + 结构化 query | donor 检索（主检索**不依赖不可复现的自然语言 query**） |
| `enzyme.get_provenance_v1` | 酶集 | 仅作 provenance，不作酶活概率 |

### 5.2 执行 / 校验工具（融合）

| 工具 | 来源资产 | 角色 |
|---|---|---|
| `reaction.apply_edit_v1` | RDKit `apply_template_to_molecule` / `align_transfer` | 确定性生成 Y（LLM 不写） |
| `chem.validate_v1` | RDKit + ledger | 合法性 + 完整反应守恒 |
| `reaction.score_candidate_v1` | `reaction_scorer.score_candidates`（DRFP-酶集） | 弱排序特征 |

### 5.3 生产高层工具（取 ChatGPT）

| 工具 | 副作用真实标注 |
|---|---|
| `reaction.predict_analogical_products_v1` | 冻结并保存一次 run（append/write），需 `client_request_id`/`idempotency_key`/`snapshot_id`，同 request hash 复用 run |
| `reaction.get_run_v1` | read-only |
| `reaction.get_candidate_evidence_v1` | read-only |
| `reaction.expand_external_evidence_v1` | 外部网络 I/O（**移出 MVP**） |

**统一字段命名**：`manifest_uri`、`reaction_ledger`（不并存别名 `run_manifest_uri`/`ledger`）。

---

## 6. 输出契约与不变式

预测成功：ranked top-K，每个候选含 `product_smiles`（内核生成）/ `transformation_family` / `reaction_site` / `graph_edit` / `reaction_ledger` / `support_evidence`(可回溯 id) / `lane`(strict|generalized) / `ranking_score` / `support_tier` / `applicability` / `reasoning_chain`（LLM 引用 id 渲染）。

拒答：`abstained=true` + `abstain_stage` + `reason_code`。

**PredictionResult 跨字段不变式**：

```
status=completed + decision=predicted  + candidates ≥ 1
status=abstained + decision=abstained  + candidates = 0 + reason_code 非空
status=partial   + decision=partial    + 明确 partial_reason（仅 generalized 或部分失败）
status=failed    + dependency/protocol error（不冒充 abstention）
```

**运行 manifest** 记录：snapshot/version、Agent prompt hash、model/provider/revision、temperature/seed、tool schema versions、tool response hashes、per-run tool/time/token budget、trace/correlation id。

---

## 7. 可靠性与防幻觉

- **Grounding guard**：最终答案里每个结构/证据必须引用本次 run 的 `candidate_id`/`evidence_id`，host 校验 ID 存在，拒绝未知 ID。
- **ranking_score ≠ probability**：未经独立 calibration fold + Brier/ECE + risk–coverage 验证前，只输出 `ranking_score` / `support_tier` / `applicability`，不贴"概率"或"酶活性"。
- **DRFP** 最多是反应典型性 / 弱排序特征，**不当酶学可行概率**。
- **数据库无记录 ≠ negative**：counterevidence 需明确定义，不把"未收录"当反证。
- **strict 只表示结构类比严格，不表示生物真实发生**。

---

## 8. 评估（取 ChatGPT 六层 + Claude selective + 多答案真值）

- **六层**：Layer0 数据正确性 → Layer1 检索 → Layer2 transform/site → Layer3 generation → Layer4 ranking/abstention → Layer5 Agent/MCP。
- **划分**：exact-X / scaffold / transform-family / source / time。
- **多答案真值**：一个 X 可能对应多个允许 Y；定义允许 Y 集合、等价（tautomer/盐/中性形式）、stereo-sensitive 与 agnostic 两套指标；incomplete annotation 下 precision 的解释边界。
- **selective / risk–coverage / abstention rate**：全部测试 X 进分母，报端到端 top-K；每个指标带 N 和置信区间。
- **strict / generalized 分开报**，不合并。
- 与旧确定性管线（Morgan+模板+DRFP）**同数据同划分对拍**作基线。

---

## 9. 边界与非目标

- **不训练神经网络**：不走 GNN/Transformer/episodic 重型训练；推理靠 LLM + 工具。
- **A2 真 novel（全库无类比）**：应触发拒答，不硬造。
- **多步降解 X→Y→Z**：单步验收后另行设计（候选图，非线性递归）。
- **外部证据增强 / research hypothesis mode / generalized lane**：全部后置于 strict 单步垂直切片与 benchmark 之后。

---

## 10. 第一阶段真正的成功标准（不先承诺 top-1 百分比）

先证明**地基可信**，再据新 benchmark 设 top-K/coverage/risk 目标：

1. 已知错误 A/B 案例（含 2-氧戊二酸/羟脯氨酸）全部修复或 quarantine；
2. catastrophic lineage mismatch 不进生产索引；
3. fold 内 test evidence leakage 为零；
4. strict candidate 全部来自可回放 transform；
5. 等价 SMILES 输入不改变 canonical candidate set；
6. 每个新增重原子有来源或明确 unknown；
7. reaction ledger 状态语义明确；
8. Agent invented candidate/evidence 数为 0；
9. infrastructure failure 不冒充 abstention；
10. strict/generalized 分报；所有指标带 N 与置信区间。

---

## 11. 开放决策（待用户拍板，见 PLAN §7）

1. 数据地基修复的**阻塞程度**：全停先修 vs 先验证发生率再定停多久（建议：先验证，普遍则全修，边缘则并行）。
2. 是否本轮纳入 research hypothesis mode（建议后置）。
3. LLM 后端固定 kimi/kimi-k3 还是可切换（建议沿用 `call_dashscope` 网关）。
4. 首个 MCP 是进程内 function-calling 还是跨进程 server（建议先进程内，Phase 3 抽 server）。
5. 统一权威文档命名与后续三份原始文档处置（建议本 UNIFIED 为准，原始降级参考）。
