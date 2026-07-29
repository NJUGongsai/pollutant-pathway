> **HISTORICAL / NON-AUTHORITATIVE**
> This document is retained for decision history only.
> Current implementation authority:
> - plan/final_design.md
> - plan/final_plan.md
> - plan/final_discussion.md


# demov2 终审融合方案 — 三份 Discussion 的统一决议

> 日期：2026-07-29
> 作者：Qwen（作为三方讨论的终审综合者）
> 地位：**权威文档**，取代之前所有 design/plan/discussion
> 输入：ChatGPT discussion + Claude discussion + Qwen discussion 的完整交叉审阅

---

## 0. 三方已达成共识的决议（无需再争论）

在写分歧之前，先列出**三家 discussion 已经一致同意**的事项：

### 0.1 ✅ LLM 不直接写 SMILES

- Claude 自我否决："让 LLM 写 SMILES 有三个硬伤：幻觉、不可复现、无法归因"
- Qwen 原方案已是 RDKit 生成
- ChatGPT 一直坚持确定性生成

**决议**：LLM 拥有**推理决策权**（判转化族 T、定反应位点 S、判证据充分性、决定拒答）；RDKit 拥有**结构生成权**（确定性图编辑回放）。LLM **描述编辑意图**，工具**执行生成**。

### 0.2 ✅ Fragment Lineage Bug 必须修复

三家一致认为当前 `canonical_identity.py` 的 A/B 配对有错（2-氧戊二酸/脯氨酸案例），所有基于此的 benchmark 数字不可信。

**决议**：在任何新推理代码之前，先验证 Bug 发生率并修复。旧 benchmark 数字一律视为 provisional。

### 0.3 ✅ 数据地基需要升级

三家一致同意需要：
- 版本化证据快照 + content hash
- 问题记录 quarantine（不静默丢弃）
- train-only 证据隔离（防泄漏）
- 完整反应账本（辅因子/共底物/副产物）

### 0.4 ✅ Phase 0.5 手动验证的价值

- Claude 称之为"神来之笔"
- ChatGPT 同意有价值但要求改为非 oracle 版本
- Qwen 原始提案

**决议**：保留 Phase 0.5，但改为**自动检索 + 预注册测试集**版本，不人工挑 support。

### 0.5 ✅ 单步先行，多步后置

三家一致。ChatGPT 和 Claude 原本就主张单步先行；Qwen 接受修正。

### 0.6 ✅ Strict / Generalized 双通道

三家一致采纳 ChatGPT 的分层概念。

### 0.7 ✅ 拒答是正常业务结果

三家一致。ChatGPT 的 8 类 reason code + precedence 最完整，采纳。

### 0.8 ✅ ranking_score ≠ 概率

三家一致。校准置信度需要独立 calibration fold + Brier/ECE 验证后才能标注。

---

## 1. 尚存分歧（需要 CC 拍板）

### 分歧 A：LLM 的推理权限边界

这是**唯一的真正分歧**。

| 立场 | ChatGPT | Claude + Qwen |
|------|---------|---------------|
| LLM 能否判断转化族 T？ | ❌ 不能（确定性工具提取） | ✅ 能（LLM 从 A→B 集合归纳） |
| LLM 能否定位反应位点 S？ | ❌ 不能（edit preconditions 枚举） | ✅ 能（LLM 结合化学直觉 + 工具佐证） |
| LLM 能否判证据充分性？ | ❌ 不能（ranking 工具决定） | ✅ 能（LLM 综合判断） |

**ChatGPT 的理由**：LLM 的化学判断不可复现、不可校准、有幻觉风险。

**Claude + Qwen 的理由**：用户明确要求"LLM 做推理核心"。把 LLM 压成只读解释器违背产品目标。转化族判断和位点选择正是 LLM 化学推理的核心价值。

**我的终审建议**：采纳 Claude + Qwen 立场，但加护栏：

```
LLM 有权做的：
  - 从 A→B 集合归纳转化族 T（化学概念层面的推理）
  - 在 X 上定位反应位点 S（结合 analyze_structure 佐证）
  - 判断证据充分性并决定拒答
  - 描述编辑意图（"将 C1 伯醇氧化为醛"）

LLM 不能做的：
  - 直接写产物 SMILES
  - 自报校准置信度（只能给 qualitative confidence: high/medium/low）
  - 改写工具的 ranking_score
  - 创造不存在的 evidence_id / candidate_id

护栏：
  - LLM 的 T/S 判断必须被 edit_script 交叉验证
  - LLM 的位点选择必须被 analyze_structure 佐证
  - LLM 的拒答决策必须有 reasoning_chain 回溯到具体 evidence
```

### 分歧 B：Research Mode 是否保留

ChatGPT 提出了一个"Research LLM-hypothesis mode"——LLM 可以提交 typed hypothesis（转化类型+位点+约束放宽），但必须进入同一 deterministic compiler/validator，单独标记、单独 benchmark。

**我的终审建议**：采纳。这是一个优雅的折中——在生产模式（grounded）之外保留一个研究模式，让 LLM 的化学假设能力可以被独立评估，但不污染生产结果。

### 分歧 C：实施节奏

- ChatGPT：8 phase（0-8），非常重
- Claude：5 phase（0-4），适中
- Qwen：5 phase + Phase 0.5，最轻

**我的终审建议**：取 6 phase 折中路线（见 §4），兼顾数据严谨和快速验证。

---

## 2. 系统架构（终审版）

### 2.1 总体架构

```
用户输入 X (SMILES)
   │
   ▼
┌─────────────────────────────────────────────────────────┐
│              LangGraph 推理循环（LLM = 推理核心）          │
│                                                         │
│  潜变量六跳链（每跳 = LLM 推理 + MCP 工具 + 拒答闸）：     │
│                                                         │
│  ① 检索证据                                             │
│     [MCP] adaptive_donors(X) → donor 分子集 + 完整 A→B   │
│     拒答闸①：无 donor / 相似度全部过低                     │
│                                                         │
│  ② 判转化族 T                                           │
│     [LLM] 从 A→B 集合归纳共同转变模式                      │
│     [MCP] analyze_diff(A,B) × N 条交叉验证               │
│     拒答闸②：转化不一致 / 归纳不出共同族                    │
│                                                         │
│  ③ 定位点 S                                             │
│     [LLM] 在 X 上指出哪个位点接受 T 的转变                 │
│     [MCP] analyze_structure(X) 佐证                      │
│     拒答闸③：X 上不存在可接受 T 的位点                     │
│                                                         │
│  ④ 描述编辑 Δ → 生成 Y                                  │
│     [LLM] 描述编辑意图（自然语言/结构化描述）               │
│     [MCP] apply_transformation(A→B模板, X, S) → Y        │
│     [MCP] validate_chemistry(X, Y, reaction_ledger)      │
│     拒答闸④：生成失败 / 验证不通过                         │
│                                                         │
│  ⑤ 评酶可行性 E                                         │
│     [MCP] search_enzymes(T, S) + score_candidate(X>>Y)   │
│     [LLM] 综合酶证据判可行性                               │
│     拒答闸⑤：无酶支持（可配置是否启用）                     │
│                                                         │
│  ⑥ 置信决策                                              │
│     [LLM] 综合全部证据 → qualitative confidence           │
│     输出：产物 Y + 完整推理链 + 证据卡                     │
│     拒答闸⑥：综合证据不足                                 │
│                                                         │
└────────────────────┬────────────────────────────────────┘
                     ▼
输出：ranked top-K 候选 + 每候选证据卡 + 反应账本
     或：typed abstention（带 reason_code）
```

### 2.2 LLM 推理权限总结

| LLM 可以 | LLM 不可以 |
|----------|-----------|
| 归纳转化族 T | 直接写 SMILES |
| 定位反应位点 S | 自报校准概率 |
| 描述编辑意图 | 改写 ranking_score |
| 判证据充分性 | 创造 evidence_id |
| 决定拒答 | 覆盖 abstention 状态 |
| qualitative confidence | 声称生物发生概率 |
| 解释推理链 | 多 LLM 投票代替独立证据 |

### 2.3 两种运行模式

#### Production Mode（Grounded）
- 候选只由 deterministic kernel 生成
- LLM 只能请求预测、查看证据、解释
- Host 从工具结果渲染结构与分数
- 用于正式用户和 benchmark

#### Research Mode（LLM-hypothesis）
- LLM 可提交 typed hypothesis（T + S + 约束放宽 + rationale）
- hypothesis 进入同一 deterministic compiler/validator
- 未通过验证不得获得 candidate_id
- 单独标记 `exploratory`，单独 benchmark
- 用于研究 LLM 的化学假设能力

---

## 3. MCP 工具箱（终审版）

### 3.1 生产层工具（4 个，对外暴露）

| 工具 | 用途 | 幂等 |
|------|------|------|
| `reaction.predict_analogical_products_v1` | 端到端一步预测 | 是（idempotency_key） |
| `reaction.get_run_v1` | 查询已有 run | 是 |
| `reaction.get_candidate_evidence_v1` | 查看候选证据详情 | 是 |
| `reaction.expand_external_evidence_v1` | 请求外部证据增强 | 否（网络 I/O） |

### 3.2 内部化学工具（7 个，推理引擎内部调用）

| 工具 | 用途 | 来源 |
|------|------|------|
| `analyze_structure(smiles)` | 分子结构分析（官能团/反应位点/环系） | RDKit SMARTS |
| `analyze_diff(smiles_a, smiles_b)` | 结构差异分析（断键/成键/净编辑） | RDKit MCS + edit_script |
| `search_reactions(query, k)` | 多维反应检索 | SQLite 多维索引 |
| `get_reaction_details(rxn_id)` | 完整反应信息（含账本） | 数据库 |
| `apply_transformation(source_rxn, target, site)` | 确定性图编辑回放 | RDKit RunReactants |
| `validate_chemistry(substrate, product, ledger)` | 化学验证 + 反应账本 | RDKit + 账本计算 |
| `search_enzymes(query)` | 酶检索（provenance） | enzyme_lookup |

### 3.3 工具返回纪律

- 严格 JSON Schema，`additionalProperties: false`
- `structuredContent` 是权威结果
- 所有工具返回 typed 结果或 typed 失败（不 silent `[]`）
- 业务拒答返回正常结果（`status=abstained`），不抛异常
- 基础设施故障返回 typed 可重试错误，不伪装成"无候选"

---

## 4. 数据层（终审版）

### 4.1 版本化证据快照

```
data/
├── snapshots/
│   └── reaction-evidence-v1/
│       ├── manifest.json          # snapshot_id, versions, counts, hash
│       ├── accepted.jsonl         # 合格反应记录
│       └── quarantined.jsonl      # 问题记录 + quarantine reason
├── indices/
│   ├── edit_index.json            # 编辑签名索引
│   ├── functional_group_index.json # 官能团索引
│   └── donor_molecule_index/      # donor 分子级 Morgan 索引
└── build_database.py              # 构建脚本
```

### 4.2 反应记录（完整账本）

```python
class ReactionRecord:
    reaction_id: str
    source: str                          # 数据来源
    raw_reaction_smiles: str             # 原始反应 SMILES
    canonical_reaction_smiles: str       # canonical 反应 SMILES
    
    # 完整参与者账本
    participants: list[ReactionParticipant]  # 所有反应物/产物/辅因子
    
    # 原子谱系
    atom_mapping: list[AtomMapPair]         # 原子映射
    fragment_lineage: list[FragmentLineage]  # 片段谱系图（非单一 A/B）
    
    # 主底物→主产物（沿谱系确定）
    primary_substrate: str                   # A（沿 lineage 确定）
    primary_product: str                     # B（沿 lineage 确定）
    lineage_confidence: str                  # high/medium/ambiguous
    lineage_method: str                      # atom_map / fragment_overlap / MCS_fallback
    
    # 反应特征
    reaction_type: list[str]                 # 转化类型标签
    edit_key: str                            # 编辑签名
    reaction_center_atoms: list[int]         # 反应中心
    cofactors: list[str]                     # 辅因子
    ec_number: str                           # EC 编号
    uniprot_ids: list[str]                   # UniProt ID
    
    # 质量标记
    quality_flags: list[str]                 # 质量标记
    balance_status: str                      # fully_balanced / partial / unbalanced
    mapping_confidence: float                # 原子映射置信度
    quarantine_reason: str | None            # quarantine 原因（None=合格）
    
    # 版本追踪
    snapshot_id: str                         # 所属快照
    provenance: list[str]                    # 来源链
```

### 4.3 Fragment Lineage 修复

**核心变更**：从"独立挑最大片段"改为"沿原子映射构建 bipartite fragment-lineage graph"。

```python
# 旧方法（有 bug）：
A = max(reactants, key=lambda f: has_center(f) and size(f))
B = max(products, key=lambda f: has_center(f) and size(f))
# 问题：A 和 B 可能没有原子映射关联

# 新方法：
lineage_graph = build_fragment_lineage(mapped_reaction)
# 返回：reactant_fragment → product_fragment(s) 的 bipartite 图
# 每条边有：mapped_overlap, changed_atoms, role_hypothesis, ambiguity
# 可以有多个 primary lineage（不强制只选一个）
```

### 4.4 反应账本（Reaction Ledger）

对每条反应，追踪完整的原子/电荷/电子账本：

```python
class ReactionLedger:
    status: str  # fully_balanced / heavy_balanced_implicit_H / partial / unbalanced
    
    # 每个参与者的角色
    participant_roles: dict[str, str]  # smiles → target_substrate/cofactor/byproduct/...
    
    # 原子转移追踪
    atom_transfers: list[AtomTransfer]  # 新增原子从哪个参与者来
    
    # 元素/电荷守恒
    element_balance: dict[str, int]     # 每种元素的进出差
    charge_delta: int                   # 净电荷变化
    hydrogen_policy: str                # explicit / implicit_with_e_policy
    
    # 适配到 X→Y 时的替换映射
    adaptation_map: dict[str, str] | None  # donor atom → X atom 的对应
```

---

## 5. 置信度与拒答（终审版）

### 5.1 Qualitative Confidence（未校准前）

| 级别 | 条件 | 标签 |
|------|------|------|
| High | ≥2 条**独立** donor 支持同一 strict 转变 + 验证通过 + in-domain | `high_support` |
| Medium | 1 条 donor 支持，或转变环境不完全匹配 | `medium_support` |
| Low | 仅 generalized 候选，或证据冲突 | `low_support` |
| Abstained | 触发拒答闸 | `abstained` |

**注意**："独立"需要定义 independent evidence unit——不是同一个反应的不同 UniProt 记录，不是同一个 donor 的重复注释。

### 5.2 拒答 Reason Code（优先级从高到低）

```python
ABSTENTION_REASONS = [
    "INVALID_QUERY",                      # 输入无效
    "NO_DONOR_IN_DOMAIN",                 # 无可比 donor
    "NO_VALID_REACTION_RECORD",           # donor 无合格反应记录
    "AMBIGUOUS_FRAGMENT_LINEAGE",         # A/B 谱系歧义
    "NO_CONSISTENT_TRANSFORMATION",       # 归纳不出共同转化族
    "NO_APPLICABLE_SITE",                 # X 上无适用位点
    "ALL_CANDIDATES_INVALID",             # 全部候选验证失败
    "ONLY_OUT_OF_DOMAIN_GENERALIZATIONS", # 仅有 OOD 泛化
    "CONFLICTING_EVIDENCE",               # 证据冲突
    "INSUFFICIENT_EVIDENCE",              # 综合证据不足
]
```

### 5.3 Strict / Generalized 分层

| Tier | 含义 | 排序特征 |
|------|------|---------|
| **Strict** | 完整 atom mapping + edit preconditions 满足 + 确定性回放 | donor_similarity, site_local_similarity, mapping_quality, ledger_completeness, support_consensus |
| **Generalized** | 显式放宽了部分约束（如 radius、取代模式） | strict 特征 + generalization_distance, relaxed_constraint_count |

**规则**：
- Strict 永远排在 Generalized 之前
- 两个 tier 的 raw score 不跨 tier 比较
- Generalized 候选标记 `exploratory`
- Out-of-domain 候选不进 top-K（诊断保留）

---

## 6. 评估方案（终审版）

### 6.1 六层评估

| Layer | 评估内容 | 关键指标 |
|-------|---------|---------|
| L0: 数据正确性 | participant role, A/B lineage, atom-map coverage | 人工抽样准确率 |
| L1: Donor 检索 | relevant donor recall@K, diversity | recall, diversity score |
| L2: 转化/位点 | strict edit match, site recall@K | precision, recall |
| L3: 候选生成 | product top-K, validity, ledger completeness | recall, validity rate |
| L4: 排序/拒答 | MRR, nDCG, risk-coverage, abstention | selective accuracy |
| L5: Agent/MCP | grounding, hallucinated ID = 0 | grounding rate |

### 6.2 拆分方式（≥6 种）

1. **random sanity** — 仅做基本检查
2. **query scaffold split** — 新骨架
3. **atom-mapped transform family split** — 已见/未见转化
4. **exact-X isolation** — 同一 X 不跨折
5. **source/database split** — 不同数据来源
6. **time split** — 时间外推

**所有 scorer/reference evidence 必须严格来自 train fold。**

### 6.3 基线矩阵

| 基线 | 描述 |
|------|------|
| Legacy Morgan top-1 | 旧管线最简版 |
| Legacy Morgan top-5 + template | 旧管线完整版 |
| Adaptive donor + strict kernel | 新内核无泛化 |
| Adaptive donor + strict + generalized | 新内核完整版 |
| Generation order | 生成顺序基线 |
| Random ranking | 随机排序基线 |
| DRFP as feature / without DRFP | DRFP 消融 |

### 6.4 成功判据

**先证明地基可信**（Phase 1-2 验收门）：
- 已知 A/B 错配案例全部修复
- catastrophic lineage mismatch 不进入生产索引
- fold 内 test evidence leakage = 0
- strict candidate 100% 来自可回放 transform

**再设定性能目标**（Phase 3+ 基于新 benchmark）：
- 端到端 top-K 数字在新 benchmark 上报告
- selective accuracy vs coverage 曲线
- abstention reason 分布合理

---

## 7. 实施路线（终审版）

### Phase 0: 文档冻结 + 数据 Bug 验证（2-3 天）

**目标**：确认 Fragment Lineage Bug 的实际发生率，冻结旧承诺。

| 任务 | 产出 |
|------|------|
| 验证 2-氧戊二酸/脯氨酸案例 | Bug 确认 + 影响范围评估 |
| 抽检 50 条反应的 A/B 配对 | 错误率统计 |
| 旧 benchmark 数字标 provisional | 文档更新 |
| 统一 MCP schema 字段 | 术语表 |
| 修正辛醇→辛醛碳数错误 | 示例修正 |

**Go/No-Go**：
- Bug 普遍（>10% 案例受影响）→ 全力修地基（Phase 1 拉长）
- Bug 边缘（<5%）→ 并行修，不全停

### Phase 0.5: 非 Oracle 快速验证（3-5 天）

**目标**：验证 LLM+MCP 闭环的化学推理能力。

| 任务 | 产出 |
|------|------|
| 预注册 20 例测试集（含 novel 拒答案例） | 测试集 |
| 自动 train-only donor 检索（不人工挑） | 检索结果 |
| LLM 走六跳推理链（模拟 MCP 工具输出） | 推理链 |
| 评估：T 正确率、S 正确率、Y 正确率 | 评估报告 |

**Go/No-Go**：
- T 正确率 ≥ 70% 且 Y 正确率 ≥ 40% → 进入 Phase 1
- 不达标 → 分析失败原因，考虑调整方向

### Phase 1: 数据审计 + 反应表示（5-7 天）

**目标**：修复 Fragment Lineage，建立版本化快照和反应账本。

| 任务 | 产出 |
|------|------|
| Fragment lineage graph 实现 | chemistry/lineage.py |
| Participant role resolver | chemistry/roles.py |
| Atom mapping adapter + version | chemistry/mapping.py |
| Versioned snapshot + quarantine | evidence/snapshot.py |
| Data audit report | reports/data_audit.md |
| 分层人工抽样审计 | 审计报告 + CI |

**验收门**：
- 已知错配案例全部修复或 quarantine
- catastrophic mismatch 不进入生产索引
- snapshot 可重放（content hash 一致）

### Phase 2: 重建 Benchmark 地基（3-5 天）

**目标**：修复评估中的泄漏和多答案问题。

| 任务 | 产出 |
|------|------|
| Multi-answer truth policy | evaluation/truth.py |
| Fold-specific evidence store | evaluation/store.py |
| Train-only retrieval/ranking | evaluation/isolation.py |
| 6 种 split 实现 | evaluation/splits.py |
| Legacy baselines 重跑 | reports/baseline_v2.md |

**验收门**：
- test evidence leakage = 0
- split 前过滤数量进入报告
- strict/generalized 分报

### Phase 3: Strict One-Step Vertical Slice（5-7 天）

**目标**：端到端严格类比预测闭环。

| 任务 | 产出 |
|------|------|
| Adaptive donor retrieval | evidence/retrieve.py |
| Strict transform extraction | chemistry/transform.py |
| Conditioned site enumeration | chemistry/sites.py |
| Deterministic graph-edit generation | chemistry/generate.py |
| Molecule validation + reaction ledger | chemistry/validate.py |
| Tiered ranking + abstention | ranking/ranker.py |
| 端到端 predictor | service/predictor.py |

**验收门**：
- 等价 SMILES 输入不改变 canonical candidate set
- 每个 candidate 有完整 provenance（donor/transform/site/ledger/evidence）
- 所有新增 heavy atom 有来源
- infrastructure failure 不冒充 abstention

### Phase 4: MCP + Grounded Agent（3-5 天）

**目标**：MCP 暴露 + LLM grounded 解释。

| 任务 | 产出 |
|------|------|
| 4 个生产 MCP 工具 | mcp/server.py |
| Grounded reporter | agent/reporter.py |
| No-invention guard | agent/policy.py |
| 合同测试 + 混沌测试 | tests/ |

**验收门**：
- LLM invented candidate/evidence ID = 0
- schema adherence = 100%
- infrastructure failure → typed error（非 abstention）

### Phase 5: Generalized Lane + 校准（3-5 天）

**目标**：受控泛化 + 置信校准。

| 任务 | 产出 |
|------|------|
| Generalized transform 放宽规则 | chemistry/generalize.py |
| Counterevidence retrieval | evidence/counter.py |
| Risk-coverage + selective accuracy | evaluation/calibration.py |
| 与旧管线对拍报告 | reports/comparison_v2.md |

### Phase 6（单步达标后另行设计）: 多步降解图

多步不是线性递归。未来采用：
- Canonical molecule node（去重）
- Candidate reaction edge
- Branch/beam search
- Cycle detection
- Depth/cost/risk budget
- Per-edge provenance
- 路径级不确定性传播

---

## 8. 目录结构（终审版）

```
demov2/
├── reaction_agent/
│   ├── schemas.py              # 所有数据契约（Pydantic v2）
│   ├── settings.py             # 配置
│   ├── chemistry/
│   │   ├── normalize.py        # 分子标准化
│   │   ├── roles.py            # 参与者角色解析
│   │   ├── lineage.py          # Fragment lineage graph
│   │   ├── transform.py        # Strict/Generalized 变换提取
│   │   ├── sites.py            # Transformation-conditioned 位点枚举
│   │   ├── generate.py         # 确定性图编辑回放
│   │   └── validate.py         # 分子验证 + 反应账本
│   ├── evidence/
│   │   ├── store.py            # 证据存储
│   │   ├── snapshot.py         # 版本化快照 + quarantine
│   │   ├── retrieve.py         # Adaptive donor 检索
│   │   ├── counter.py          # Counterevidence（Phase 5）
│   │   └── external.py         # 外部证据（Phase 5+）
│   ├── ranking/
│   │   ├── features.py         # 排序特征
│   │   ├── ranker.py           # Tiered ranking
│   │   └── abstention.py       # Typed abstention
│   ├── service/
│   │   ├── predictor.py        # 端到端 predictor
│   │   ├── state.py            # 状态机
│   │   └── manifest.py         # Immutable run manifest
│   ├── mcp/
│   │   ├── server.py           # MCP server（4 个生产工具）
│   │   └── resources.py        # Resource URIs
│   └── agent/
│       ├── policy.py           # Agent 权限策略
│       ├── reporter.py         # Grounded 报告生成
│       └── research.py         # Research hypothesis mode（Phase 5+）
├── tools/                      # 内部化学工具（7 个）
│   ├── analyze_structure.py
│   ├── analyze_diff.py
│   ├── search_reactions.py
│   ├── get_reaction_details.py
│   ├── apply_transformation.py
│   ├── validate_chemistry.py
│   └── search_enzymes.py
├── reasoner/                   # LLM 推理核心
│   ├── prompts/                # 各阶段 prompt
│   ├── stages.py               # 六跳阶段函数 + 拒答闸
│   └── engine.py               # LangGraph 编排
├── evaluation/
│   ├── splits.py               # 6 种 split
│   ├── metrics.py              # 6 层指标
│   ├── truth.py                # Multi-answer truth policy
│   ├── calibration.py          # 置信校准
│   └── run_benchmark.py        # 主评估入口
├── scripts/
│   ├── build_snapshot.py       # 构建快照
│   ├── audit_snapshot.py       # 审计快照
│   └── run_pilot.py            # Phase 0.5 快速验证
├── data/                       # 数据（gitignore）
├── tests/                      # 测试
├── reports/                    # 报告
└── plan/                       # 设计文档
    └── FUSION_DESIGN_V5.md     # 本文档
```

---

## 9. 不可协商的否决项（终审版）

以下主张不得进入最终生产设计：

1. LLM 直接生成或修复产物 SMILES
2. LLM 自报校准置信度/生物概率
3. "RDKit 能解析 = 反应正确"
4. 只比较 substrate/product 质量差作为完整反应守恒
5. 原样使用旧 `main_substrate/main_product/transformed_pair`
6. 把 `reaction_center_from_chenyu(X)` 当无条件 site predictor
7. 把 DRFP max 当酶可行概率
8. "两条类似记录"自动等于高置信
9. 人工挑正确 evidence 后声称验证了端到端
10. 4541 条记录无 quarantine 全部进入生产索引
11. 修复 A/B、泄漏、多答案前引用旧 benchmark 数字作为承诺
12. 首版默认递归 3-5 步线性路径
13. 数据库没有 evidence 就表述为"无反应"
14. 把 strict structural analogy 表述为环境发生概率
15. 多 LLM 投票代替独立工具/模型/实验验证

---

## 10. 总时间线

| Phase | 时间 | 产出 | 前置条件 |
|-------|------|------|---------|
| Phase 0 | 2-3 天 | Bug 验证 + 文档冻结 | 无 |
| Phase 0.5 | 3-5 天 | LLM 能力验证 | Phase 0 |
| Phase 1 | 5-7 天 | 数据地基 | Phase 0 |
| Phase 2 | 3-5 天 | Benchmark 地基 | Phase 1 |
| Phase 3 | 5-7 天 | Strict 一步闭环 | Phase 1+2 |
| Phase 4 | 3-5 天 | MCP + Agent | Phase 3 |
| Phase 5 | 3-5 天 | Generalized + 校准 | Phase 4 |
| **总计** | **24-37 天** | **完整的 LLM-native 反应类比系统** | |

Phase 0 和 Phase 0.5 可部分并行（Phase 0.5 的 LLM 推理验证不依赖数据修复）。

---

## 11. 待 CC 确认的开放项

1. **LLM 推理权限**：接受 §2.2 的权限边界吗？（LLM 可判 T/S/拒答，但不写 SMILES/概率）
2. **Research Mode**：是否保留 §2.3 的研究模式？
3. **实施节奏**：接受 6 phase（24-37 天）的节奏吗？
4. **LLM 后端**：固定 kimi/kimi-k3 还是可切换？
5. **MCP 部署**：先进程内 function-calling（Phase 3），再抽 MCP server（Phase 4）？

---

*本文件是三方讨论的终审决议。待 CC 确认后，成为 demov2 的唯一权威设计文档。*
