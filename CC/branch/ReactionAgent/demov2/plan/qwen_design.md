# ReactionAgent v4 设计文档 · LLM-native 化学推理

> 日期：2026-07-29
> 范围：`CC/branch/ReactionAgent/demov2/`
> 目标：构建一个 **LLM 驱动的 MCP 工具链系统**，让 LLM 自己充当"化学家"，根据已知酶催化反应 A→B 的例子，推断未知污染物 X 的生物降解路径。
> v3→v4 的原因：v3 把 LLM 降格为编排器，核心推理由 GNN site 模型 + DRFP + 模板迁移完成。这与"LLM 做化学推理"的目标存在结构性偏差。v4 彻底翻转：**LLM 做大脑，MCP 工具做手和眼**。

---

## 0. 与 v3 的核心区别

| 维度 | v3（位点驱动神经-符号混合） | v4（LLM-native 化学推理） |
|------|--------------------------|--------------------------|
| **核心推理者** | GNN site 模型 + DRFP + 模板迁移 | LLM 自己分析结构、理解转变、推断产物 |
| **LLM 角色** | 编排器（调工具、汇总结果） | 化学家（理解化学、做类比推理） |
| **检索方式** | Morgan 指纹 / 反应中心子图匹配 | LLM 按化学特征自然语言搜索 |
| **候选生成** | MCS 模板机械迁移 | LLM 理解转变后指导 apply_transformation |
| **排序** | 证据融合（site + consensus + DRFP） | LLM 综合化学证据做 listwise 判断 |
| **ML 模型** | 需训 GNN site 模型 + listwise ranker | 不需要训练任何模型 |
| **拒答** | 规则阈值 | LLM 证据不足时主动停止 |

---

## 1. 目标与非目标

### 1.1 目标
- **LLM 做核心推理**：LLM 通过 MCP 工具获取化学信息和验证结果，自身完成"理解 A→B 转变规律 → 推断 X→?"的化学推理。
- **保守但可靠**：宁可说"不知道"也不乱猜。有充分证据才给预测，否则明确拒答。
- **污染物生物降解场景**：给定有机污染物 X，推测其在微生物作用下的多步酶催化降解路径。
- **复用现有资产**：4541 条反应数据、RDKit 工具、LangGraph 框架、honest_eval 评估。

### 1.2 非目标
- 不训练任何 ML 模型（GNN、listwise ranker、Transformer 生成器等）
- LLM 不直接生成 SMILES 字符串（产物由 RDKit 工具生成，保证化学正确性）
- 不做广义化学反应预测（聚焦酶催化生物降解）
- 不引入 EnzymeCAGE 3B 排序（本阶段聚焦反应预测，酶排序后置）

---

## 2. 系统架构

### 2.1 总览

```
┌─────────────────────────────────────────────────────┐
│                    用户输入 X (SMILES)                │
└───────────────────────┬─────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────┐
│              LangGraph 推理循环 (LLM = 大脑)          │
│                                                     │
│  每一跳 (current_mol = X, 然后 = 上一跳产物):         │
│                                                     │
│  ① 分析 current_mol 的结构特征                       │
│     [MCP: analyze_structure]                        │
│                                                     │
│  ② 根据结构特征，搜索可能适用的已知反应                │
│     [MCP: search_reactions]                         │
│                                                     │
│  ③ 从搜索结果中选出最相关的 A→B 例子                  │
│     [LLM 判断 + MCP: analyze_diff]                  │
│                                                     │
│  ④ 理解 A→B 的化学转变，推断在 current_mol 上的应用   │
│     [LLM 推理 — 这是核心！]                          │
│                                                     │
│  ⑤ 生成候选产物                                      │
│     [MCP: apply_transformation]                     │
│                                                     │
│  ⑥ 验证产物的化学合理性                               │
│     [MCP: validate_chemistry]                       │
│                                                     │
│  ⑦ 决策：接受 / 标注低可信 / 拒答停止                 │
│     [LLM 决策]                                      │
│                                                     │
│  → 接受：current_mol = 产物，继续下一跳              │
│  → 拒答/到终点：输出路径                              │
└───────────────────────┬─────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────┐
│  输出: 降解路径 + 每步证据卡                          │
│  X → Y1 (醇脱氢, 高置信) → Y2 (醛脱氢, 中置信) → 停止 │
└─────────────────────────────────────────────────────┘
```

### 2.2 核心设计原则

1. **LLM 是大脑，工具是手眼**：LLM 做所有化学推理（识别官能团、理解转变、选择反应类型），MCP 工具提供信息和验证
2. **产物不由 LLM 生成**：所有产物 SMILES 通过 `apply_transformation` 工具由 RDKit 生成，保证价键正确
3. **证据驱动**：每个预测必须引用具体的已知反应作为支撑
4. **保守可靠**：证据不足时主动拒答，不强给答案

---

## 3. MCP 工具箱

### 3.1 工具清单

| # | 工具名 | 用途 | 输入 | 输出 | 底层 |
|---|--------|------|------|------|------|
| 1 | `analyze_structure` | 解析分子：官能团、反应位点、子结构 | SMILES | 结构化 dict（官能团列表、可反应位点、分子量、环系） | RDKit 子结构 SMARTS 匹配 |
| 2 | `analyze_diff` | 对比两个分子的化学差异 | SMILES_A, SMILES_B | 原子级差异：断键/成键、原子变化、净编辑 | RDKit MCS + atom mapping + edit_script |
| 3 | `search_reactions` | 多维搜索已知反应 | query（自然语言/SMILES/编辑模式）, k | 最相关的 k 条反应（含 A→B、酶、EC、编辑签名） | SQLite + 多维索引 |
| 4 | `get_reaction_details` | 获取一条反应的完整信息 | reaction_id | 底物/产物 SMILES、原子映射、反应中心、酶/EC、辅因子 | 数据库查询 |
| 5 | `apply_transformation` | 将 A→B 的转变应用到 X | source_rxn（A→B）, target_smiles（X）, target_site（可选） | 候选产物 SMILES + 是否成功 + 警告 | RDKit template extraction + RunReactants |
| 6 | `validate_chemistry` | 验证产物化学合理性 | substrate, product | 守恒检查、价键合理性、碎裂检测 | RDKit sanitize + 守恒计算 |
| 7 | `search_enzymes` | 查找能催化某类反应的酶 | reaction_pattern / EC / 关键词 | 酶列表（UniProt、EC、名称、已知底物数） | enzyme_lookup |

### 3.2 工具设计原则

**返回结构化数据，不返回自然语言解释**：

```python
# 工具返回 dict，由 LLM 自己解读
def analyze_structure(smiles: str) -> dict:
    return {
        "smiles": smiles,
        "molecular_weight": 94.11,
        "functional_groups": [
            {"name": "phenol", "smarts": "c1ccccc1O", "atoms": [0,1,2,3,4,5,6]},
        ],
        "reactive_sites": [
            {"type": "phenol_oh", "atom_idx": 6, "description": "酚羟基可被氧化"},
        ],
        "ring_systems": [{"type": "benzene", "size": 6}],
        "has_halogen": False,
    }
```

**化学计算保持确定性**：MCS、atom mapping、RunReactants、守恒检查都是确定性 RDKit 计算，不引入随机性或 LLM 判断。

---

## 4. 数据层

### 4.1 知识库架构

把 4541 条反应数据组织成 LLM 友好的多维索引：

```
data/
├── reactions.db              # SQLite 主库
├── edit_index.json           # 编辑签名索引
├── functional_group_index.json  # 官能团索引
└── transformation_labels.py  # 转变类型标签映射
```

### 4.2 SQLite 表结构

```sql
CREATE TABLE reactions (
    rxn_id       TEXT PRIMARY KEY,
    substrate    TEXT NOT NULL,
    product      TEXT NOT NULL,
    full_rxn     TEXT NOT NULL,
    cofactors    TEXT,
    ec_number    TEXT,
    ec_class     TEXT,
    uniprot_ids  TEXT,
    rxn_center   TEXT,
    edit_key     TEXT,
    func_groups_in  TEXT,
    func_groups_out TEXT,
    transformation_type TEXT
);
```

### 4.3 search_reactions 多维检索

```python
def search_reactions(query: str, k: int = 5) -> list[dict]:
    results = []
    results += fulltext_search(query, limit=k)       # 自然语言 → 全文匹配
    results += structured_search(parsed_query, limit=k) # 关键词 → 精确匹配
    if has_smiles_pair(query):
        results += edit_signature_search(edit_key, limit=k) # 编辑签名匹配
    if has_molecule(query):
        results += structure_similarity_search(query.mol, limit=k) # 结构相似性
    return deduplicate_and_diversify(results, k)
```

### 4.4 转变类型标签映射

让 LLM 能用化学术语搜索：

```python
TRANSFORMATION_LABELS = {
    "OH_dehydrogenation": "醇脱氢氧化",
    "aldehyde_oxidation": "醛氧化",
    "aromatic_hydroxylation": "芳环羟基化",
    "dehalogenation": "脱卤",
    "ester_hydrolysis": "酯水解",
    "amine_oxidation": "胺氧化",
    "ring_cleavage": "环裂解",
    "beta_oxidation": "β-氧化",
    # ...
}
```

### 4.5 数据预处理（离线）

从现有数据提取元数据：

| 字段 | 提取方式 | 来源 |
|------|---------|------|
| func_groups_in/out | RDKit 官能团 SMARTS 匹配 | 底物/产物 SMILES |
| edit_key | atom mapping → edit_script | reacting_center.pkl + MCS |
| transformation_type | 规则映射 edit_key → 化学名称 | 手工 + 规则 |
| rxn_center | reacting_center.pkl + MCS 回退 | 晨羽数据 |
| ec_class | EC 编号解析 | formal_filtered_train.csv |

---

## 5. LLM 推理流程

### 5.1 System Prompt 核心指引

```
你是环境生物化学专家。根据已知酶催化反应例子，推断未知污染物的生物降解路径。

## 推理原则
1. 像化学家一样思考：理解化学转变的本质，不机械匹配
2. 证据驱动：每个预测必须有具体已知反应支撑
3. 保守可靠：找不到充分证据时，明确说"无法推断"并停止
4. 结构化推理：每一步走固定思维链

## 每一跳的思维链

### Step 1: 结构分析
调用 analyze_structure，识别官能团、可反应位点、分子整体特征

### Step 2: 搜索相关反应
根据结构特征，调用 search_reactions 找已知例子
- 搜索"含有相同官能团的酶催化反应"
- 搜索"类似反应中心的转化"
- 搜索"同类 EC 编号的反应"

### Step 3: 理解转变规律
选出最相关的 1-3 条 A→B 例子，调用 analyze_diff 精确分析：
- 这些例子的共同转变模式是什么？

### Step 4: 推断应用
将转变规律应用到当前分子：
- 哪个位点可以接受这种转变？
- 有位阻/电子效应阻碍吗？

### Step 5: 生成与验证
- apply_transformation 生成候选产物
- validate_chemistry 验证化学合理性

### Step 6: 决策
- ≥2 条类似反应一致支持 → 高置信，继续
- 仅 1 条支持 → 中置信，标注并继续
- 无证据 / 验证失败 → 拒答停止
```

### 5.2 推理示例：1-辛醇的降解

```
输入: CCCCCCCCO (1-辛醇)

第 1 跳:
① analyze_structure → 伯醇(-OH), C8脂肪链
② search_reactions("伯醇 氧化 醛") → 8 条（乙醇→乙醛, 丁醇→丁醛...）
③ analyze_diff(乙醇, 乙醛) → C1-OH 脱氢, -2H, 形成 C=O (ADH, EC 1.1.1.1)
④ [LLM] 3 条例子完全一致："伯醇 ADH 脱氢为醛"。辛醇 C1 有伯醇，可应用。
⑤ apply_transformation(乙醇→乙醛模板, 辛醇) → CCCCCCCC=O (辛醛)
⑥ validate_chemistry → ✅
⑦ 高置信（3 条一致），继续

第 2 跳:
① analyze_structure → 醛(-CHO)
② search_reactions("醛 氧化 羧酸 酶") → 6 条
③ analyze_diff → 醛脱氢, -2H+O, 形成-COOH (ALDH)
④ 6 条一致支持 → 辛醛氧化为辛酸
⑤ apply_transformation → CCCCCCCCC(=O)O (辛酸)
⑥ ✅
⑦ 高置信，继续

第 3 跳:
① analyze_structure → 脂肪酸
② search_reactions("脂肪酸 β氧化") → 12 条
③ [LLM] β-氧化需要 CoA 活化，多步酶促...
④ search_reactions("辛酸 CoA 活化") → 2 条
⑤ 中置信 — 标注"需更多证据"
→ 继续但降低置信度...
```

---

## 6. 置信度与拒答

### 6.1 三级置信度

| 级别 | 条件 | 行为 |
|------|------|------|
| **高置信** | ≥2 条独立反应支持同一转变模式 + 产物验证通过 | 正常输出 |
| **中置信** | 仅 1 条支持，或转变环境不完全相同 | 标注 ⚠️ 并继续 |
| **低置信/拒答** | 无相关反应 / 产物验证失败 / 证据冲突 | 停止展开 |

### 6.2 证据评估清单

```
1. 证据数量：有几条独立反应支持？
2. 证据一致性：是否指向同一转变模式？
3. 位点匹配：反应位点环境是否相似？
4. 化学验证：产物是否通过 validate_chemistry？
5. 已知限制：是否需要特殊条件？

判断规则：
- 1+2+3+4 全通过 → 高置信
- 仅缺一项 → 中置信
- 4 失败 → 拒答（化学不合理）
- 1+2+3 全缺 → 拒答（无证据）
```

### 6.3 停止条件

| 条件 | 说明 |
|------|------|
| mineralization | 产物为 CO2/H2O/NH3 等小分子 |
| max_depth | 路径达 5 步上限 |
| no_evidence | 搜索不到任何相关反应 |
| chemistry_fail | 所有候选产物未通过验证 |
| conflicting | 多条证据矛盾，无法决策 |
| low_confidence | 连续 2 跳中置信，不确定性累积 |

---

## 7. 目录结构

```
ReactionAgent/demov2/
├── agent.py              # LangGraph 推理循环
├── prompts.py            # System prompt + 推理链指引
├── state.py              # Step / PathwayState / Evidence 数据模型
│
├── mcp_tools/            # 7 个 MCP 工具
│   ├── __init__.py
│   ├── analyze_structure.py
│   ├── analyze_diff.py
│   ├── search_reactions.py
│   ├── get_reaction_details.py
│   ├── apply_transformation.py
│   ├── validate_chemistry.py
│   └── search_enzymes.py
│
├── data/                 # 知识库
│   ├── build_database.py
│   ├── reactions.db
│   ├── edit_index.json
│   └── transformation_labels.py
│
├── benchmark/            # 评估
│   ├── honest_eval.py
│   ├── canonical_identity.py
│   ├── splits.py
│   └── eval_agent.py
│
├── core/                 # 底层化学工具（移植）
│   ├── pipeline.py
│   ├── edit_script.py
│   ├── canonical_identity.py
│   └── enzyme_lookup.py
│
├── plan/                 # 设计文档与计划
│   ├── qwen_design.md
│   └── qwen_plan.md
│
├── run.py                # CLI 入口
└── README.md
```

---

## 8. 评估方案

### 8.1 对比实验

| 方案 | 描述 | 来源 |
|------|------|------|
| **基线 A** | Morgan + SMARTS + DRFP | v2 已有结果 |
| **基线 B** | 位点驱动检索 + DRFP | v3 handoff 方案 C |
| **新方案** | LLM-native 化学推理 | v4 本设计 |

三个方案在 honest_eval 三划分（random/scaffold/reaction_family）上直接对比。

### 8.2 核心指标

| 指标 | 基线 A | 目标 |
|------|--------|------|
| 检索天花板 | 41.5% | ≥60% |
| 端到端 top-1 | ~23.5% | ≥35% |
| 拒答误拒答率 | N/A | <20% |
| 推理链质量 | N/A | ≥80% 人工认可 |

### 8.3 LLM-native 独有评估维度

- **推理链质量**：转变类型判断、位点选择、证据引用（人工抽检 50 例）
- **拒答质量**：真拒答 vs 误拒答比例
- **多步路径质量**：每步独立准确率 vs 全路径准确率
- **成本分析**：token 消耗、MCP 调用次数、延迟

### 8.4 快速验证（Phase 0.5）

在完整工程化之前，用最低成本验证方向可行性：

1. 从测试集中手动选 20 个案例
2. 用 Claude/GPT-4 手动走推理链（模拟 MCP 工具输出）
3. 评估 LLM 能否正确识别转变类型（≥80%）、找到相关反应（≥60%）、推断合理产物（≥50%）
4. 通过 → 工程化；不通过 → 回到方案 B/C

---

## 9. 假设与风险

| 风险 | 缓解措施 |
|------|---------|
| LLM 化学推理能力不足 | Phase 0.5 手动验证；不通过则退回 |
| LLM 不熟悉高度专业化的生化反应 | 用强模型（Claude Opus/Sonnet）；精心设计 prompt |
| 每个预测多轮 LLM 调用成本高 | 优化 prompt 减少轮次；缓存常见查询 |
| 4541 条数据覆盖不足 | search_reactions 支持多维度检索，最大化利用现有数据 |
| LLM 可能编造不存在的反应 | 产物必须由 RDKit 工具生成，LLM 不直接写 SMILES |

---

## 10. 一句话研究命题

> LLM 能否仅凭化学直觉和工具辅助，从已知酶催化反应中归纳转变规律，在未知污染物上定位反应位点并推断多步降解路径？

这比 v3 的"神经-符号混合"更纯粹，也更贴近"让 AI 像化学家一样思考"的终极目标。
