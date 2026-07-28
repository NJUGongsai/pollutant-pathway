# ReactionAgent 设计文档

> 日期：2026-07-28
> 范围：`CC/branch/ReactionAgent`（本地 LangChain/LangGraph 单 agent，全新工程）
> 目标：输入未知污染物底物 X → agent 检索最相似的已知反应 A→B，学习其可迁移的反应特征，**有依据地**逐跳推测 X 的多步降解路径。
> 定位：这是把已验证的 `extract_rea_trans_fea` 引擎（真实 novel 判别力 2.8× 随机）从"确定性脚本"升级为"会推理的 agent"，而非重做化学。

---

## 1. 目标与非目标

### 1.1 目标
- 构建一个**本地 LangGraph 单 tool-calling agent（自由推理 / ReAct 风格）**：LLM 自主决定每一步调用哪个工具。
- 输入一个污染物 SMILES `X`（真实 novel，库里可以没有），输出一条**多步线性降解路径** `X → Y → Z → …`，每一步都附完整证据。
- LLM 的价值集中在两处历史痛点：
  - **A（选参照反应）**：不再只靠底物 Morgan 相似度，而是让 LLM 读候选参照反应（含催化酶/EC/相似度）后**推理**哪条转化逻辑最该迁移到当前底物。
  - **B（学特征 + 生成产物）**：让 LLM 审视 RDKit 生成的候选产物 + 可信度 + 证据后择优，并可组合多条参照反应。

### 1.2 非目标（本期不做）
- 不做分支降解网络（树/DAG）——但架构预留，见 §7。
- 不接入 EnzymeCAGE 3B 大模型做几何背书（Step 3b）——留 HPC，未来单独接。
- 不集成到 EnzymeCrew 10 节点主干（`reaction_prediction` 节点接线另立 plan）。
- LLM **不**直接生成产物 SMILES（避免幻觉、保价键守恒）。

---

## 2. 核心架构决策（本次头脑风暴确定，不可动摇的地基）

| 决策点 | 结论 | 理由 |
|---|---|---|
| LLM 角色 | **编排大脑**：RDKit 从 A→B 确定性提取可迁移规则，LLM 只负责选择与组合 | 化学 100% 可追溯、价键守恒、零幻觉，贴合"有依据推测"底线 |
| 输出形态 | **多步线性路径**（v1），架构预留分支树（v2） | "反应路径"需多跳；agent 迭代 loop 的价值正在于决定展开谁、何时停 |
| 部署 | **agent 本地跑，数据资产同步到本地** | v1 用不到 3B，所需资产都是中小文件；本地循环零延迟、可离线迭代 |
| 框架 | **LangChain(1.0)/LangGraph 单 tool-calling agent** | 单 agent 自由推理，工具可插拔 |
| LLM 自主度 | **自由推理（ReAct）**：LLM 自主决定工具调用顺序与次数 | 最"agent"，让 LLM 真正推理 A→B 迁移 |

---

## 3. 系统总览

```
输入：污染物 SMILES X
  │
  ▼
┌─────────────────────────────────────────────────────────┐
│ LangGraph 单 agent（自由推理循环）                        │
│  系统提示编码策略 + "有依据"底线；LLM 自主编排下列工具：    │
│                                                          │
│  每一跳 (current = X，之后 = 上一跳选定产物)：              │
│   ① retrieve_reference_reactions(current)  → 候选 A→B     │
│   ② [LLM 推理] 选最该迁移的参照反应（解 A）                 │
│   ③ extract_and_apply_template(donor,current) → 候选 Y'   │
│   ④ score_candidates(current, Y', enzyme)  → 可信度+证据   │
│   ⑤ [LLM 审候选] 择优 + 写理由（解 B）                     │
│   ⑥ [LLM 决策] 继续展开 / 停止                             │
└─────────────────────────────────────────────────────────┘
  │
  ▼
输出：PathwayState（路径链 + 每步完整证据）
```

**停止条件**（满足任一即停止继续展开当前链）：
- 达到最大深度（默认 **5 跳**）；
- `is_terminal(product)` 判定为矿化/终点；
- 该跳无有效候选产物；
- 该跳最高可信度 < 阈值（默认 **0.3**）——该步仍记录并标注"低可信"，但不再向下展开。

---

## 4. 工具集（确定性，全本地，包装已验证模块）

所有工具是**纯确定性**函数，直接复用 `extract_rea_trans_fea` 已验证的核心逻辑（移植到 `core/`）。

| 工具 | 签名（概念） | 职责 | 底层来源 |
|---|---|---|---|
| `retrieve_reference_reactions` | `(smiles, k=5) → List[RefReaction]` | 只凭底物 Morgan 检索 top-k 候选参照反应，每条带：反应 A>>B、底物相似度、催化酶 UniProt、EC | `chenyu_features.retrieve_by_substrate` + `enzyme_lookup.enzymes_for_reaction` |
| `extract_and_apply_template` | `(donor_reaction, substrate) → List[Candidate]` | 对 donor 用 MCS 中心(radius=1) 提放宽 SMARTS 模板，RunReactants 套到 substrate，返回价键合法候选产物 | `pipeline.extract_reaction_center/extract_template/apply_template_to_molecule` |
| `score_candidates` | `(substrate, candidates, enzyme_uniprot) → List[ScoredCandidate]` | 候选反应现算 DRFP，与该酶反应族取 max Tanimoto → 可信度 + best_match 先例 | `reaction_scorer.score_candidates` + `enzyme_lookup.reactions_for_enzyme` |
| `is_terminal` | `(smiles) → bool` | 判断分子是否达降解终点（简单规则：碳数≤1 / 已完全氧化为 CO₂/小分子等），供停止决策 | 新增（轻量规则） |

**工具设计原则**：
- 工具返回**结构化、可读**的结果（含证据字段），让 LLM 能基于证据推理，而非黑盒。
- 反应中心分工遵循既有规范：**MCS 中心用于模板迁移（生成）**；chenyu 真值中心仅用于打分场景（本期打分走 DRFP-酶集，不用真值中心做迁移）。
- 工具无副作用、可独立单测。

---

## 5. 状态与证据结构

```python
@dataclass
class StepEvidence:
    substrate: str              # 该跳输入底物
    product: str                # 该跳选定产物
    donor_reaction: str         # 提供模板的库内已知反应 A>>B
    donor_substrate_similarity: float
    enzyme_uniprot: str         # 背书催化酶
    ec: str
    score: float                # DRFP-酶集可信度 ∈ [0,1]
    best_match_reaction: str    # 酶反应族中与该候选最像的已知反应（可解释先例）
    llm_rationale: str          # LLM 选择该参照/该产物的理由
    low_confidence: bool = False

@dataclass
class PathwayState:
    query: str                  # 初始污染物 X
    steps: List[StepEvidence]   # 有序路径链
    status: str                 # "completed_terminal" | "max_depth" | "dead_end" | "low_confidence_stop"
    note: str = ""
```

**"有依据"保证**：产物只由 RDKit 确定性生成（价键守恒、不臆造）；LLM 只做选择/编排/写理由。每一步都可追溯到 donor 反应 + 酶 UniProt/EC + DRFP 可信度 + best_match 先例 + LLM 理由。

---

## 6. 目录结构（`CC/branch/ReactionAgent/`）

```
ReactionAgent/
├── agent.py            # LangGraph 单 agent 定义 + 推理循环 + 停止条件
├── tools.py            # 4 个工具的 LangChain @tool 封装（调 core/）
├── prompts.py          # 系统提示：策略 + "有依据"底线 + 选参照/择产物指引
├── state.py            # PathwayState / StepEvidence dataclass
├── run.py              # CLI 入口: python run.py 'SMILES'
├── sync_assets.sh      # 从晨羽 HPC 同步 data/ 资产
├── core/               # 移植自 extract_rea_trans_fea（确定性化学，不含 agent）
│   ├── chenyu_features.py
│   ├── pipeline.py
│   ├── reaction_scorer.py
│   └── enzyme_lookup.py
├── data/               # 本地资产（sync_assets.sh 拉取，gitignore）
│   ├── rxn2fp.pkl
│   ├── reacting_center.pkl
│   └── rxn2enzymes / formal_filtered_train.csv
└── README.md
```

**依赖**：`langchain`/`langgraph`、`rdkit`（2026.3.x）、`drfp` 0.3.7、LLM 网关（`LLM_API_BASE_URL` / `LLM_API_KEY`）。
**本地资产改路径**：`core/chenyu_features.py` 的 `ENZYMECAGE_DATA_ROOT` 指向本地 `data/`。

---

## 7. 可配置项与 v2 预留

| 参数 | 默认 | 说明 |
|---|---|---|
| `max_depth` | 5 | 路径最大跳数 |
| `top_k` | 5 | 每跳检索候选参照反应数 / 供 LLM 挑选的候选产物数 |
| `confidence_threshold` | 0.3 | 低于此值停止继续展开该链 |
| `branch_factor` | 1 | v1 固定 1（线性）；>1 即展开为分支树（v2） |

**v2 预留**：把每跳"取 top-1"放宽为"保留 top-b 个候选并各自继续展开"，PathwayState 由链变为树/DAG，加剪枝（可信度阈值 + 深度）即得分支降解网络。

---

## 8. 验证计划

- **工具层单测**：4 个工具各自对已知案例复现 `extract_rea_trans_fea` 的确定性输出（零偏差回归）。
- **端到端 smoke**：辛醇 `CCCCCCCCO` 应复现"借丁醇→丁醛模板 → 辛醛"这一已知正确单跳，并能继续展开（辛醛→辛酸等）成多步路径。
- **路径合理性抽查**：挑几个真实关注污染物，人工审阅路径链的化学合理性与证据完整性。
- **判别力不回退**：单跳排序结果应与现有引擎一致（agent 的编排不改变确定性工具的打分）。

---

## 9. 假设与风险

- **假设**：`rxn2fp.pkl` / `reacting_center.pkl` / 反应→酶映射可从晨羽 HPC 拷贝到本地（体积中小、无许可限制）。若不可拷贝，退回数据访问方案 C（HPC FastAPI 服务）。
- **风险**：LLM 自由推理可能调用工具次数过多/发散 → 由 `max_depth` + 系统提示中的流程指引 + 单跳工具幂等性约束收敛。
- **风险**：`drfp` 现算较慢 → 复用现有 `lru_cache`；每跳候选数受 `top_k` 限制。
- **既有坑规避**：模板显式 H 伪影导致不点火问题已在 `pipeline._atom_query_smarts`（放宽 SMARTS）修复，移植时保持不变。
