# EnzymeCrew M3 开发计划：LangGraph 编排实施方案

日期：2026-07-17  
定位：独立项目，`projects/enzymecage_crew/`  
编排框架：LangGraph（非 CrewAI）  
LLM：统一千问 API（DashScope），不同节点可配不同模型  
EnzymeCAGE：晨羽智云 HPC 部署，开发机 HTTP 远程调用

---

## 一、流程图 → 节点映射（M3 最小可用版）

流程图完整版 10 个智能体，M3 只做 5 个节点（4 个功能节点 + 1 个编排入口）：

```
用户输入（SMILES/InChI/场景描述）
  │
  ▼
┌──────────────────────────────────────────────────────────────┐
│  OrchestratorNode（M3 简化版：固定路由，不做意图分类）          │
│  后续版本：LLM 意图路由，决定走"酶推荐"还是"菌推荐"链            │
└──────────────────────┬───────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────┐
│  Node 1: SubstrateNode（LLM 节点）                             │
│  对应图中：01-未知污染物输入                                     │
│  职责：解析 SMILES/InChI/自然语言 → 结构化底物信息               │
│  LLM：qwen-turbo（轻量解析，不需要大模型）                       │
│  输出：substrate_smiles + provenance                           │
└──────────────────────┬───────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────┐
│  Node 2: ReactionNode（确定性节点，无 LLM）                     │
│  对应图中：02-每步反应 + Top-10 相似反应检索                     │
│  职责：RDKit/Morgan/Tanimoto 相似反应检索                       │
│  输入：substrate_smiles                                        │
│  输出：candidate_reactions（Top-10 相似反应列表）                │
│  约束：M3 只有 retrieved，无 predicted fallback                 │
└──────────────────────┬───────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────┐
│  Node 3: EnzymePoolNode（确定性节点，无 LLM）                   │
│  对应图中：02-候选酶池构建                                      │
│  职责：B-primary / C-fallback 两路 pool 构造                    │
│  输入：candidate_reactions（取 Top-1 反应）                     │
│  逻辑：                                                        │
│    1. B 路线：Rhea 140 精确 EC → EC→UID 索引 → B pool         │
│    2. B 为空 → C 路线：Top-10 相似反应 → 已知酶合并 → C pool   │
│    3. pool >100 → fail closed                                 │
│  输出：enzyme_pool_final + pool_route_used + pool_size         │
└──────────────────────┬───────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────┐
│  Node 4: EnzymeCAGENode（远程调用节点，无本地 LLM）              │
│  对应图中：02-EnzymeCAGE 反应-酶排序模型（核心）                  │
│  职责：HTTP 调用晨羽智云上的 EnzymeCAGE wrapper                 │
│  输入：reaction_smiles + enzyme_pool_final                     │
│  输出：ranked_enzymes（score + rank + CI）                     │
│  约束：60s 超时、幂等、batch-context sensitivity 披露            │
└──────────────────────┬───────────────────────────────────────┘
                       │
                       ▼
                  输出 Top-K 候选酶
                  + 证据链 + provenance
```

**M3 不做的节点**（完整版后续加）：
- PathwayPredictionAgent（LOGOS 路径预测）—— M3 没有新反应预测能力
- LLMRerankingAgent（LLM 二次审核）—— 等 3 case 基线后再加
- MicrobeCrew 全部 3 个（酶→菌映射 / MetaTraits / MicrobeSelection）—— M4 才接入

---

## 二、State Schema（Pydantic）

```python
from typing import List, Optional, Literal, Any
from pydantic import BaseModel, Field

# ---------- 子模型 ----------

class SubstrateInfo(BaseModel):
    substrate_smiles: str
    substrate_name: Optional[str] = None
    source: Literal["user_smiles", "user_inchi", "llm_parsed"] 
    provenance: str                          # 解析来源说明

class CandidateReaction(BaseModel):
    reaction_smiles: str
    similarity_score: float
    source: Literal["retrieved"] = "retrieved"   # M3 只有 retrieved
    rhea_id: Optional[str] = None
    ec_numbers: Optional[List[str]] = None

class RankedEnzyme(BaseModel):
    uid: str
    score: float
    rank: int
    ensemble_ci: Optional[tuple[float, float]] = None

class EvidenceRecord(BaseModel):
    stage: str                               # "substrate" / "reaction" / "pool" / "ranking"
    action: str                              # 具体动作描述
    data: dict[str, Any]                     # 该阶段的关键数据快照
    timestamp: str

# ---------- 主 State ----------

class EnzymeCrewState(BaseModel):
    # 用户输入
    user_query: str
    
    # Node 1 输出
    substrate_info: Optional[SubstrateInfo] = None
    
    # Node 2 输出
    candidate_reactions: List[CandidateReaction] = Field(default_factory=list)
    
    # Node 3 输出
    enzyme_pool_b: Optional[List[str]] = None        # B 路线 pool（保留 provenance）
    enzyme_pool_c: Optional[List[str]] = None        # C 路线 pool（保留 provenance）
    enzyme_pool_final: Optional[List[str]] = None    # 实际使用的 pool
    pool_route_used: Optional[Literal["B", "C"]] = None
    pool_size: Optional[int] = None
    
    # Node 4 输出
    ranked_enzymes: Optional[List[RankedEnzyme]] = None
    model_version: str = "v1_20260714"
    
    # 证据链与不确定性
    evidence_chain: List[EvidenceRecord] = Field(default_factory=list)
    uncertainty_flags: List[str] = Field(default_factory=list)
    
    # 错误处理
    error: Optional[str] = None
    fail_closed: bool = False
```

---

## 三、项目目录结构

```
projects/enzymecage_crew/
├── pyproject.toml
├── requirements.txt
├── config/
│   ├── settings.py                  # 环境变量、API keys、路径
│   └── llm_config.yaml              # 各节点 LLM 模型配置
├── src/
│   ├── __init__.py
│   ├── state.py                     # EnzymeCrewState Pydantic schema
│   ├── graph.py                     # LangGraph StateGraph 定义 + 条件边
│   ├── nodes/
│   │   ├── __init__.py
│   │   ├── orchestrator_node.py     # M3 简化版：固定路由
│   │   ├── substrate_node.py        # LLM 节点：底物解析
│   │   ├── reaction_node.py         # 确定性：相似反应检索
│   │   ├── enzyme_pool_node.py      # 确定性：B/C pool 构造
│   │   └── enzymecage_node.py       # 远程调用：EnzymeCAGE wrapper
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── reaction_search.py       # RDKit/Morgan/Tanimoto 检索
│   │   ├── ec_lookup.py             # Rhea 140 EC 索引查询
│   │   └── enzymecage_client.py     # 远程 wrapper HTTP 客户端
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── evidence.py              # EvidenceRecord 等子模型
│   └── utils/
│       ├── __init__.py
│       └── retry.py                 # 重试 + 熔断
├── data/                            # 学生提供的数据资产（符号链接或挂载）
│   ├── rhea/                        # Rhea 140 本地文件
│   ├── reference_fingerprints/      # 参考反应指纹预计算
│   └── d4_assets/                   # D4 冻结资产索引
├── cases/
│   ├── case_1_strong.yaml           # 已裁定 case 配置
│   ├── case_2_medium.yaml
│   └── case_3_weak.yaml
├── tests/
│   ├── test_substrate_node.py
│   ├── test_reaction_node.py
│   ├── test_enzyme_pool_node.py
│   ├── test_enzymecage_node.py
│   └── test_e2e_3cases.py
└── reports/
    └── m3_e2e_report.md
```

---

## 四、技术栈

| 层 | 选型 | 说明 |
|---|---|---|
| 编排 | **LangGraph** | StateGraph + conditional edge + Pydantic state |
| LLM | **千问 API（DashScope）** | SubstrateNode 用 qwen-turbo；后续重量节点可配 qwen-max |
| 本地模型 | **EnzymeCAGE v1 wrapper** | 晨羽智云 HPC 部署，开发机 HTTP 调用 |
| 化学工具 | **RDKit** | Morgan 指纹 + Tanimoto 相似度 |
| 数据验证 | **Pydantic v2** | State + 所有输入输出 schema |
| 测试 | **pytest** | 单元 + 集成 + 端到端 |
| Python | **3.10+** | 跟 ADRMATS 保持一致 |

---

## 五、LLM 节点模型配置

```yaml
# config/llm_config.yaml
nodes:
  substrate_node:
    provider: dashscope
    model: qwen-turbo              # 轻量解析，不需要大模型
    temperature: 0.1
    max_tokens: 500
    
  orchestrator_node:               # M3 简化版不用，后续版本配置
    provider: dashscope
    model: qwen-max
    temperature: 0.3
    max_tokens: 1000

  # M4+ 后续节点预留
  llm_reranking_node:
    provider: dashscope
    model: qwen-max
    temperature: 0.2
    max_tokens: 4000

  microbe_selection_node:
    provider: dashscope
    model: qwen-max
    temperature: 0.2
    max_tokens: 4000
```

---

## 六、开发里程碑拆解

### Phase 0：项目骨架（0.5 天）

- [ ] 创建 `projects/enzymecage_crew/` 目录结构
- [ ] `pyproject.toml` + `requirements.txt`（langgraph、langchain、dashscope、rdkit、pydantic、httpx、pytest）
- [ ] `config/settings.py`（API keys 从环境变量读取、数据路径配置）
- [ ] `src/state.py`（完整 EnzymeCrewState Pydantic schema）
- [ ] `config/llm_config.yaml`

**验收**：`python -c "from src.state import EnzymeCrewState"` 无报错。

### Phase 1：确定性工具 + 节点（1.5 天）

**工具层**：
- [ ] `tools/reaction_search.py`：加载参考反应指纹 → Morgan/Tanimoto Top-K 检索
- [ ] `tools/ec_lookup.py`：加载 Rhea 140 文件 → reaction→EC 精确查询 → EC→UID 索引
- [ ] `tools/enzymecage_client.py`：HTTP 客户端（先 mock 返回固定排序，后续替换真实 API）

**节点层**：
- [ ] `nodes/reaction_node.py`：调用 reaction_search，输出 candidate_reactions
- [ ] `nodes/enzyme_pool_node.py`：B-primary/C-fallback 逻辑 + pool >100 fail closed
- [ ] `nodes/enzymecage_node.py`：调用 enzymecage_client（先 mock）

**测试**：
- [ ] `test_reaction_node.py`：用已知反应测试相似检索正确性
- [ ] `test_enzyme_pool_node.py`：B 有 EC / B 无 EC / pool >100 三种路径

**验收**：3 个确定性节点单元测试全 PASS，mock 数据下能跑通。

### Phase 2：LLM 节点（0.5 天）

- [ ] `nodes/substrate_node.py`：DashScope qwen-turbo 解析自然语言 → SMILES
- [ ] `nodes/orchestrator_node.py`：M3 简化版（固定路由到 substrate_node，不做意图分类）

**测试**：
- [ ] `test_substrate_node.py`：SMILES 输入 / InChI 输入 / 自然语言描述输入 三种路径

**验收**：3 种输入类型都能正确解析出 substrate_smiles。

### Phase 3：LangGraph 编排 + 真实 EnzymeCAGE 集成（1 天）

- [ ] `src/graph.py`：StateGraph 定义 + 节点注册 + 条件边
  ```
  orchestrator → substrate → reaction → enzyme_pool → enzymecage
  条件边：
    substrate 失败 → fail closed
    reaction 无结果 → fail closed
    pool >100 → fail closed
    enzymecage 超时 → retry 1 次 → fail closed
  ```
- [ ] `tools/enzymecage_client.py`：替换 mock 为真实 HTTP 调用
- [ ] 集成测试：全链路 mock → 真实 EnzymeCAGE 切换

**验收**：graph.compile() 无报错，mock 全链路跑通。

### Phase 4：3 case 端到端 + 报告（1 天）

**前置依赖**：学生提供 3 个已裁定 case 的 reaction SHA256 + SMILES + 数据资产。

- [ ] `cases/case_1_strong.yaml` / `case_2_medium.yaml` / `case_3_weak.yaml`
- [ ] `tests/test_e2e_3cases.py`：3 个 case 逐个跑通全链路
- [ ] `reports/m3_e2e_report.md`：逐 case 记录
  - 每一 stage 是否完成、schema 是否有效
  - 反应来源、Rhea/EC 或相似邻居 provenance
  - pool 构造路线、大小及正确 UID 是否入池
  - 正确 UID 的 EnzymeCAGE rank、Top-10/Top-50 可见性
  - batch-context sensitivity 和预计算资产域警告
  - 不把 rank 1 表述为现实世界最优酶

**验收**：3 个 case 全链路跑通，报告包含学生 M3-P0 裁定要求的 8 项记录。

---

## 七、前置依赖清单（需要学生提供）

| # | 依赖项 | 格式 | 用途 | 紧急程度 |
|---|---|---|---|---|
| 1 | 3 个已裁定 case 的 reaction SHA256 + SMILES | YAML/JSON | case 配置 | **阻塞 Phase 4** |
| 2 | Rhea 140 本地文件（4 个 tsv） | TSV 文件 | B 路线 EC 索引 | **阻塞 Phase 1** |
| 3 | 参考反应指纹数据库 | pickle/numpy | C 路线相似检索 | **阻塞 Phase 1** |
| 4 | D4 冻结资产索引（UID → 资产可用性） | JSON/CSV | pool 过滤 | **阻塞 Phase 1** |
| 5 | EnzymeCAGE 远程服务 HTTP 接口文档 | OpenAPI/README | 远程调用 | **阻塞 Phase 3** |
| 6 | EC → UID 映射表 | CSV/JSON | B 路线 pool 构造 | **阻塞 Phase 1** |

**建议**：把学生 M3-P0B1 的公平基准代码和数据作为参考实现，工具层可以直接复用或适配。

---

## 八、EnzymeCAGE 远程调用接口（待对齐）

需要跟学生对齐晨羽智云上的 wrapper 服务接口。建议沿用 D3 v1.1 契约：

```
POST /api/v1/predict
Content-Type: application/json

Request:
{
  "reaction_smiles": "CC(=O)Oc1ccccc1C(=O)O",
  "enzyme_pool_uids": ["P0A123", "Q45678", ...],
  "top_k": 10,
  "return_ci": true
}

Response:
{
  "ranked_enzymes": [
    {"uid": "P0A123", "score": 0.95, "rank": 1, "ensemble_ci": [0.91, 0.98]},
    ...
  ],
  "model_version": "v1_20260714",
  "evidence_hash": "sha256:..."
}
```

**约束**：
- 超时 60s
- 幂等：同一请求多次调用返回相同结果（容差 1e-5）
- 无效 UID 跳过不报错
- 响应含 evidence_hash（SHA256）

---

## 九、风险与缓解

| 风险 | 影响 | 缓解 |
|---|---|---|
| EnzymeCAGE 远程接口未定义 | Phase 3 阻塞 | Phase 1 先用 mock，接口对齐后替换 |
| 参考反应指纹数据库不存在 | Phase 1 阻塞 | 从学生 M3-P0B1 代码中导出，或现场预计算 |
| RDKit 指纹计算慢 | 响应时间过长 | 预计算全部参考反应指纹，运行时只算 query |
| 晨羽智云网络不稳定 | EnzymeCAGE 调用失败 | retry 1 次 + 熔断 + fail closed |
| 3 个 case 未冻结 | Phase 4 阻塞 | 先用 mock case 开发，case 确认后替换 |

---

## 十、时间线总览

```
Phase 0  项目骨架          0.5 天    ▓▓
Phase 1  确定性工具+节点    1.5 天    ▓▓▓▓▓▓
Phase 2  LLM 节点           0.5 天    ▓▓
Phase 3  LangGraph 编排     1.0 天    ▓▓▓▓
Phase 4  3 case 端到端      1.0 天    ▓▓▓▓
─────────────────────────────────────────
总计                        4.5 天
```

**关键路径**：Phase 1（工具层）→ Phase 3（编排集成）→ Phase 4（端到端）  
**并行可做**：Phase 2（LLM 节点）可以跟 Phase 1 并行

**前置条件**：Phase 1 需要数据资产（依赖 #2/#3/#4/#6），建议先跟学生要数据。
