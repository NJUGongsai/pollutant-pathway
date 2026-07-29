> **HISTORICAL / NON-AUTHORITATIVE**
> This document is retained for decision history only.
> Current implementation authority: `plan/final_design.md`, `plan/final_plan.md`, `plan/final_discussion.md`.

# ReactionAgent v4 实现计划 · LLM-native 化学推理

> 参照设计文档：`demov2/plan/qwen_design.md`
> 工作目录：`CC/branch/ReactionAgent/demov2/`
> 原则：**Phase 0.5 手动验证先行** → 构建 MCP 工具箱 → 构建数据层 → 组装 Agent → 评估

---

## 摘要

1. **Phase 0.5**：手动验证 LLM 化学推理能力（1-2 天，无代码）
2. **Phase 1**：构建 7 个 MCP 工具（底层化学计算）
3. **Phase 2**：构建数据层（4541 条反应 → SQLite + 多维索引）
4. **Phase 3**：组装 LangGraph Agent（推理循环 + system prompt）
5. **Phase 4**：适配 honest_eval 评估，与基线 A/B 对比

---

## Phase 0.5 · 手动验证（1-2 天，无代码）

**目的**：在投入工程之前，用最低成本验证 LLM-native 方向是否可行。

### 步骤

1. 从 `benchmark/` 测试集中手动选 20 个案例（覆盖 high/medium/low novelty）
2. 为每个案例准备：
   - X 的 SMILES 和结构描述（人工写）
   - 3-5 条相关 A→B 反应例子（人工从数据库中挑）
   - A→B 的结构差异描述（人工写）
3. 将上述信息喂给 Claude/GPT-4，让它走推理链推断 X→?
4. 对照真值 Y_true 评估

### 评估表

| 案例 | X | 真值 Y | LLM 预测 | 转变类型正确? | 位点正确? | 产物正确? |
|------|---|--------|---------|-------------|---------|---------|
| 1 | ... | ... | ... | ✅/❌ | ✅/❌ | ✅/❌ |
| ... | | | | | | |

### 通过标准

- 转变类型正确率 ≥ 80%
- 位点选择正确率 ≥ 60%
- 产物正确率 ≥ 50%

### 决策

- **通过** → 进入 Phase 1 工程化
- **不通过** → 分析失败原因，考虑回到方案 B（LLM + 轻量计算）或方案 C（辅助模型）

---

## Phase 1 · 构建 MCP 工具箱（3-5 天）

**目的**：实现 7 个确定性化学工具，封装为 MCP 可调用的函数。

### 1.1 移植底层化学工具到 `core/`

从现有 `CC/branch/ReactionAgent/core/` 和 `benchmark/` 移植：

| 文件 | 移植内容 | 改动 |
|------|---------|------|
| `pipeline.py` | `mcs_atom_mapping`, `extract_reaction_center`, `extract_template`, `apply_template_to_molecule`, `_get_env_atoms`, `_atom_query_smarts` | 保持原样 |
| `edit_script.py` | `extract_edit`, `EditScript.key()` | 保持原样 |
| `canonical_identity.py` | `transformed_pair`, `main_substrate`, `main_product`, `canon_frags` | 保持原样 |
| `enzyme_lookup.py` | `enzymes_for_reaction`, `reactions_for_enzyme` | 保持原样 |

### 1.2 实现 7 个 MCP 工具

**工具 1: `analyze_structure(smiles) -> dict`**
- 输入：SMILES 字符串
- 输出：
  ```python
  {
      "smiles": str,
      "canonical_smiles": str,
      "molecular_weight": float,
      "molecular_formula": str,
      "functional_groups": [{"name": str, "smarts": str, "atoms": [int]}],
      "reactive_sites": [{"type": str, "atom_idx": int|list, "description": str}],
      "ring_systems": [{"type": str, "size": int, "atoms": [int]}],
      "has_halogen": bool,
      "num_hba": int,  # H-bond acceptors
      "num_hbd": int,  # H-bond donors
  }
  ```
- 实现：RDKit 子结构匹配 + 官能团 SMARTS 库 + 反应位点规则

**工具 2: `analyze_diff(smiles_a, smiles_b) -> dict`**
- 输入：两个 SMILES
- 输出：
  ```python
  {
      "mcs_smiles": str,           # 最大公共子结构
      "mcs_atom_count": int,
      "bonds_broken": [{"atoms": [int,int], "order": int}],
      "bonds_formed": [{"atoms": [int,int], "order": int}],
      "atoms_added": [{"element": str, "count": int}],
      "atoms_removed": [{"element": str, "count": int}],
      "net_edit": str,             # 如 "-2H, +O" 或 "-HCl"
      "edit_key": str,             # 编辑签名（来自 edit_script）
      "transformation_type": str,  # 推断的转变类型标签
  }
  ```
- 实现：RDKit MCS + atom mapping + edit_script.extract_edit

**工具 3: `search_reactions(query, k=5) -> list[dict]`**
- 输入：自然语言查询 / SMILES / 编辑模式 / 官能团
- 输出：最相关的 k 条反应
  ```python
  [{
      "rxn_id": str,
      "substrate": str,
      "product": str,
      "transformation_type": str,
      "ec_number": str,
      "edit_key": str,
      "similarity_score": float,  # 检索相关度
  }]
  ```
- 实现：SQLite 多维检索（全文 + 结构化 + 编辑签名 + 结构相似性）

**工具 4: `get_reaction_details(rxn_id) -> dict`**
- 输入：反应 ID
- 输出：
  ```python
  {
      "rxn_id": str,
      "substrate_smiles": str,
      "product_smiles": str,
      "full_reaction": str,
      "cofactors": [str],
      "ec_number": str,
      "ec_class": str,
      "uniprot_ids": [str],
      "reaction_center_atoms": [int],
      "edit_key": str,
      "edit_details": dict,  # analyze_diff 的完整输出
      "functional_groups_in": [str],
      "functional_groups_out": [str],
  }
  ```

**工具 5: `apply_transformation(source_rxn, target_smiles, target_site=None) -> dict`**
- 输入：源反应（A→B SMILES 对）+ 目标分子 + 可选位点
- 输出：
  ```python
  {
      "success": bool,
      "product_smiles": str | None,
      "template_smarts": str,
      "applied_at": int | None,  # 目标分子上的应用位点
      "warnings": [str],         # 如"模板在目标分子上匹配到多个位点"
  }
  ```
- 实现：pipeline.extract_template + pipeline.apply_template_to_molecule

**工具 6: `validate_chemistry(substrate, product) -> dict`**
- 输入：底物和产物 SMILES
- 输出：
  ```python
  {
      "valid": bool,
      "checks": {
          "sanitize": bool,
          "mass_balance": {"substrate": float, "product": float, "diff": float},
          "element_balance": {"C": {"in": int, "out": int}, ...},
          "charge_balance": bool,
          "valence_ok": bool,
          "aromatic_ok": bool,
          "fragmentation": bool,  # True = 有不合理碎裂
      },
      "small_molecules": [str],  # 如识别出的 H2O, NAD+ 等
      "warnings": [str],
  }
  ```

**工具 7: `search_enzymes(query) -> list[dict]`**
- 输入：反应模式 / EC 编号 / 关键词
- 输出：
  ```python
  [{
      "uniprot_id": str,
      "ec_number": str,
      "enzyme_name": str,
      "known_substrate_count": int,
      "source_organism": str,
  }]
  ```

### 1.3 测试

每个工具配单元测试：
- 输入已知案例 → 输出与预期一致
- 边界情况：无效 SMILES、空查询、无匹配
- 工具间组合测试：analyze_structure → search_reactions → apply_transformation → validate_chemistry

---

## Phase 2 · 构建数据层（2-3 天）

**目的**：把 4541 条反应数据组织成 LLM 友好的多维索引。

### 2.1 数据预处理脚本 `data/build_database.py`

```
输入:
  - reacting_center.pkl (4541 条反应中心)
  - rxn2fp.pkl (4541 条 DRFP 指纹)
  - formal_filtered_train.csv (反应→酶映射)

处理:
  1. 对每条反应:
     - canonicalize 底物/产物 SMILES
     - 提取 edit_key (atom mapping → edit_script)
     - 识别 functional_groups_in/out (RDKit SMARTS)
     - 映射 transformation_type (edit_key → 标签)
     - 解析 ec_class, cofactors
  2. 构建 SQLite 数据库
  3. 构建 edit_index.json (编辑签名 → 反应 ID 列表)
  4. 构建 functional_group_index.json (官能团 → 反应 ID 列表)

输出:
  - data/reactions.db
  - data/edit_index.json
  - data/functional_group_index.json
```

### 2.2 转变类型标签映射 `data/transformation_labels.py`

- 手工定义 ~20 种常见生化转变类型的 edit_key 模式
- 对 4541 条反应的 edit_key 自动标注 transformation_type
- 未匹配的反应标为 "other"

### 2.3 验证

- 检查数据完整性：4541 条全部入库
- 抽检 50 条反应的 edit_key 和 transformation_type 是否正确
- 测试 search_reactions 的 4 条检索路径各返回合理结果

---

## Phase 3 · 组装 Agent（3-5 天）

**目的**：用 LangGraph 构建推理循环，LLM 调用 MCP 工具完成多步降解路径预测。

### 3.1 数据模型 `state.py`

```python
@dataclass
class Step:
    substrate: str           # 当前底物 SMILES
    product: str | None      # 产物 SMILES（拒答时为 None）
    transformation: str      # 转变类型描述
    evidence: list[dict]     # 支撑的 A→B 例子
    confidence: str          # "high" | "medium" | "low"
    reasoning: str           # 推理过程（2-3 句话）
    tool_calls: list[dict]   # 本步调用的工具记录

@dataclass
class PathwayState:
    query: str               # 原始输入 X
    steps: list[Step]        # 路径链
    status: str              # 终止状态
    stop_reason: str         # 停止原因
    total_tool_calls: int    # 总工具调用次数
    total_llm_tokens: int    # 总 token 消耗
```

### 3.2 System Prompt `prompts.py`

- 完整的推理链指引（见设计文档 §5）
- 置信度评估清单
- 停止条件说明
- 输出格式要求（JSON 结构化的 Step）

### 3.3 LangGraph 推理循环 `agent.py`

```python
# 简化的推理循环结构
graph = StateGraph(AgentState)

graph.add_node("reason", llm_reasoning_step)     # LLM 推理 + 工具调用
graph.add_node("evaluate", evaluate_step)         # 评估当前步结果
graph.add_node("decide", decide_continue_or_stop) # 决策：继续/停止

graph.add_edge("reason", "evaluate")
graph.add_conditional_edges("evaluate", route_by_confidence)
graph.add_conditional_edges("decide", route_by_stop_condition)

# 循环: reason → evaluate → decide → (continue → reason) | (stop → end)
```

### 3.4 CLI 入口 `run.py`

```bash
python run.py "CCCCCCCCO"                    # 单分子输入
python run.py --file test_cases.txt          # 批量输入
python run.py --verbose "c1ccc(O)cc1Cl"      # 详细输出推理链
```

输出格式：JSON 格式的 PathwayState + 可读的文本报告

---

## Phase 4 · 评估（2-3 天）

**目的**：在 honest_eval 框架上评估新方案，与基线对比。

### 4.1 适配 honest_eval

在 `benchmark/honest_eval.py` 中新增 `llm_native` generator 模式：

```python
def generate_candidates_llm_native(x_smiles: str) -> list[str]:
    """用 LLM agent 生成候选产物"""
    result = agent.predict(x_smiles, max_steps=1)  # 单步
    return [step.product for step in result.steps if step.product]
```

### 4.2 评估脚本 `benchmark/eval_agent.py`

```
功能:
  1. 加载测试集（复用 splits.py 的 3 种划分）
  2. 对每个 X 调用 agent 预测
  3. 记录漏斗各阶段指标
  4. 记录拒答率和拒答质量
  5. 对比基线 A/B 的结果

输出:
  - reports/v4_random.json
  - reports/v4_scaffold.json
  - reports/v4_reaction_family.json
  - reports/v4_comparison.md (对比报告)
```

### 4.3 成功判据

| 指标 | 基线 A (已知) | 目标 |
|------|-------------|------|
| 检索天花板 | 41.5% | ≥60% |
| 端到端 top-1 | ~23.5% | ≥35% |
| 拒答误拒答率 | N/A | <20% |

### 4.4 消融实验

- 有拒答 vs 无拒答（强制给答案）
- 高置信子集 vs 全量
- 不同 max_depth (1/3/5)
- 不同 LLM 模型（Claude Sonnet vs Opus）

---

## 总时间线

| 阶段 | 时间 | 交付物 |
|------|------|--------|
| Phase 0.5 手动验证 | 1-2 天 | 20 例验证表 + Go/No-Go 决策 |
| Phase 1 MCP 工具箱 | 3-5 天 | 7 个工具 + 单元测试 |
| Phase 2 数据层 | 2-3 天 | SQLite DB + 索引 + 预处理脚本 |
| Phase 3 Agent 组装 | 3-5 天 | LangGraph agent + system prompt + CLI |
| Phase 4 评估 | 2-3 天 | 对比报告 + 消融结果 |
| **总计** | **11-18 天** | **完整的 LLM-native 反应预测系统** |

---

## 风险与回退

| 阶段 | 风险 | 回退方案 |
|------|------|---------|
| 0.5 | LLM 化学推理能力不足 | 回到方案 B（LLM + 轻量计算） |
| 1 | RDKit 工具移植困难 | 逐步移植，优先 analyze_structure 和 search_reactions |
| 2 | edit_key 自动标注准确率低 | 扩大手工标签集，或回退到纯全文检索 |
| 3 | LLM 推理链不稳定 | 强化 prompt 约束 + few-shot 示例 |
| 4 | 端到端指标不达标 | 分析瓶颈（检索 vs 生成 vs 推理），针对性优化 |
