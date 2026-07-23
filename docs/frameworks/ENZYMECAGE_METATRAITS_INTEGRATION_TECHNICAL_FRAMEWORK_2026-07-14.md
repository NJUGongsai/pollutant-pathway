# EnzymeCAGE v1 × metaTraits 组合链路：技术框架讨论稿

日期：2026-07-14

目的：为 v1 冻结之后（M3.5-M4 阶段）新增"反应→酶→菌"完整推荐能力提供架构画像与接口契约，供内部讨论定稿。

约束：
- 本文档只画**框架**与**契约**，不写实现代码
- 所有决策点标注 `[TBD-讨论]`，供内部 review 定稿
- 架构风格延用 ADRMATS 现有模式（CrewAI BaseAgent + BaseAPITool + Pydantic 输出约束）

---

## 一、顶层链路图

```
用户输入：污水描述（污染物 + 场景）
    │
    ▼
[SubstrateAgent]          解析污染物 → SMILES / InChI
    │
    ▼
[ReactionAgent]           反应检索（相似性 OK）/ 反应预测（相似性不 OK）→ 候选反应集合
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│ EnzymeCAGE v1 Agent（M2 冻结组件）                          │
│   Input:  reaction_smiles + enzyme_pool_uids                │
│   Output: RankedEnzyme[]（uid, score, rank, ensemble_ci）   │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
[Enzyme2OrganismTool]     酶 → 宿主菌反查（UniProt / KEGG Organism）
    │                    输出：{enzyme_uid → [organism_uid + confidence + source]}
    ▼
[OrganismAggregator]      按候选菌聚合"支持酶数 / 累计打分 / 平均 CI" → 候选菌集合
    │
    ▼
[MicrobeTraitTool]        metaTraits 官网检索 API 批量拉性状表
    │                    保留证据分层（experimental / predicted / no-robust-majority）
    ▼
[TraitFilterLayer]        硬约束过滤 + 软约束打分
    │                    - 硬约束：违反 → 剔除（例如"厌氧场景 vs 严格好氧菌"）
    │                    - 软约束：违反 → 降权，不剔除
    ▼
[MicrobeSelectionAgent]   LLM 综合决策
    │                    输入：候选菌 + 酶匹配度 + 性状适配度 + 证据链
    │                    输出：Top-K 菌 + 排序理由 + 不确定性说明
    ▼
[DesignExplainingAgent]   最终推荐 + 可追溯 evidence（复用 ADRMATS 现有模块）
    │
    ▼
面向用户：Top-K 菌 + 目标反应 + 载体酶 + 性状适配 + 证据链
```

**关键定位**：
- EnzymeCAGE v1 是**排序底座**，不能被绕过
- metaTraits 是**筛除层**，不做主决策
- LLM 只在最后一层做**综合 + 解释**，决策面压到最小

---

## 二、模块划分与职责

| 模块 | 是否新建 | 类型 | 复用来源 |
|---|---|---|---|
| SubstrateAgent | 已存在（雏形） | Agent | 上游对齐 |
| ReactionAgent | 已存在（雏形） | Agent | 上游对齐 |
| EnzymeCAGE v1 Agent | **本轮完成** | Agent | 参考 ADRMATS `DesignExplainingAgent` 结构 |
| Enzyme2OrganismTool | **新建** | Tool (BaseAPITool) | 类比 `pubchem_tool.py` |
| OrganismAggregator | **新建** | 无状态函数 | utils 层 |
| MicrobeTraitTool | **新建** | Tool (BaseAPITool) | 类比 `epa_comptox_tool.py` |
| TraitFilterLayer | **新建** | 无状态函数 | utils 层 |
| MicrobeSelectionAgent | **新建** | Agent | 参考 `AdsorptionEvaluationAgent` |
| DesignExplainingAgent | 复用 | Agent | ADRMATS 已存在 |

**新建的 3 个 Tool 都遵循 ADRMATS 现有 BaseAPITool 契约**：
- 继承 `BaseAPITool`，自动获得 rate_limit / TTL cache / 指数退避重试
- CrewAI 适配层用 Pydantic `*Input` 声明 schema
- 单例工厂 `get_xxx_tool()` 供上层调用

---

## 三、关键数据契约（Pydantic 骨架）

### 3.1 EnzymeCAGE v1 → Enzyme2OrganismTool

```python
class EnzymeCAGEResponse(BaseModel):
    ranked_enzymes: List[RankedEnzyme]     # 已在 v1 wrapper 定义
    model_version: str = "v1_20260714"
    evidence_hash: str
```

### 3.2 Enzyme2OrganismTool

```python
class Enzyme2OrganismInput(BaseModel):
    enzyme_uids: List[str]                 # 来自 EnzymeCAGE 输出
    include_predicted: bool = False        # 是否包含预测型宿主注释
    top_organisms_per_enzyme: int = 20

class OrganismHit(BaseModel):
    organism_uid: str                      # NCBI Taxonomy ID 或 GTDB ID
    organism_name: str
    source: Literal["UniProt", "KEGG", "both"]
    evidence_level: Literal["reviewed", "unreviewed", "predicted"]  # UniProt SwissProt vs TrEMBL
    confidence: float                      # 归一化 0-1

class Enzyme2OrganismOutput(BaseModel):
    mappings: Dict[str, List[OrganismHit]] # enzyme_uid → 宿主列表
```

### 3.3 OrganismAggregator（无状态函数）

```python
def aggregate_organisms(
    enzyme_ranking: List[RankedEnzyme],
    e2o_mappings: Dict[str, List[OrganismHit]],
) -> List[OrganismCandidate]:
    """按候选菌聚合：
    - supporting_enzymes: 该菌能催化的候选反应数
    - cumulative_score: sum(enzyme_score × organism_confidence)
    - avg_ensemble_ci: 支持酶的 CI 平均（宽度加权）
    """

class OrganismCandidate(BaseModel):
    organism_uid: str
    organism_name: str
    supporting_enzymes: List[str]          # 该菌里包含的候选酶 UID
    cumulative_score: float                # 排序主键
    avg_ensemble_ci: Tuple[float, float]
```

### 3.4 MicrobeTraitTool（metaTraits 封装）

```python
class MicrobeTraitInput(BaseModel):
    organism_uids: List[str]               # NCBI / GTDB ID
    trait_categories: Optional[List[str]] = None  # 不指定则拉全量 144 项标准化性状

class TraitValue(BaseModel):
    trait_name: str                        # OMP/MICRO/GO 本体 ID + 可读名
    value: Union[str, float, bool]
    evidence: Literal["experimental", "predicted", "no_robust_majority"]
    source: str                            # BacDive / BV-BRC / Traitar / ...

class MicrobeTraitOutput(BaseModel):
    traits: Dict[str, List[TraitValue]]    # organism_uid → 性状列表
```

### 3.5 TraitFilterLayer

```python
class TraitConstraint(BaseModel):
    trait_name: str
    operator: Literal["must_be", "must_not_be", "in_range", "prefer"]
    value: Any
    hardness: Literal["hard", "soft"]      # hard 违反剔除；soft 违反降权
    weight: float = 1.0                    # soft 约束的权重

class FilteredOrganism(BaseModel):
    candidate: OrganismCandidate
    trait_score: float                     # 0-1，性状适配度
    violated_soft_constraints: List[str]
    uncertain_traits: List[str]            # no_robust_majority 的性状
```

### 3.6 MicrobeSelectionAgent 最终输出

```python
class MicrobeRecommendation(BaseModel):
    organism_uid: str
    organism_name: str
    rank: int
    total_score: float                     # cumulative_score × trait_score
    supporting_enzymes: List[str]
    key_traits_match: List[str]
    uncertainty_flags: List[str]
    reasoning: str                         # LLM 生成的推荐理由
    evidence_chain: EvidenceChain          # 全链路可追溯
```

---

## 四、不确定性合流规则

三个来源的不确定性必须在最终推荐里显式呈现，不能合并成一个数：

| 来源 | 表达 | 传递方式 |
|---|---|---|
| EnzymeCAGE 5v5 bootstrap | `ensemble_ci` | 累积到 `avg_ensemble_ci` |
| UniProt/KEGG 酶→菌注释 | `evidence_level` (reviewed/unreviewed/predicted) | 折算 `confidence` |
| metaTraits 性状 | `evidence` (experimental/predicted/no_robust_majority) | 归入 `uncertainty_flags` |

**输出侧的呈现要求**：每个推荐菌必须能看到"排序依赖的三层证据分别是哪一档"，不能只给一个综合分。这条对应你的**原始数据优先原则**——不允许下游只看压缩后的坍塌分数。

---

## 五、过滤层 vs 决策层的分工

**过滤层（TraitFilterLayer）—— 无 LLM，可复现**：
- 硬约束（hard）例子：
  - 厌氧场景 → 剔除"strict aerobe"
  - 温度 40℃+ → 剔除"psychrophile"
  - 高盐场景 → 剔除"non-halotolerant"
- 软约束（soft）例子：
  - 偏好"biofilm-forming"（挂膜工艺）→ 违反降权 0.7×
  - 偏好"non-pathogenic"（安全性）→ 违反降权 0.5×
- 违反 hard 的直接从候选池剔除；违反 soft 的降低 trait_score

**决策层（MicrobeSelectionAgent，LLM）**：
- 只做 Top-K 综合排序 + 理由生成
- 不能覆盖过滤层的硬约束（LLM 不能"觉得这个菌应该保留"就绕过过滤）
- LLM 的输入必须包含 `evidence_chain`，输出必须引用 evidence 才生效

这层分工的目的：**LLM 幻觉压不到主链路**，只影响解释文本，不影响候选池成员。

---

## 六、Fallback 处理

| 情境 | 触发条件 | 处理 |
|---|---|---|
| **F1: 候选酶查不到宿主** | UniProt/KEGG 都无命中 | 标记为"orphan enzyme"，从菌推荐链去除，但保留在"单酶推荐"结果里 |
| **F2: 候选菌 metaTraits 无覆盖** | metaTraits 查无此 organism | 保留候选，性状字段全部标 `unknown`，trait_score = 中性分（0.5），uncertainty_flags 标记 |
| **F3: 候选菌全部违反硬约束** | 过滤后候选池为空 | 报告"当前场景约束下无合适宿主菌"，返回 EnzymeCAGE 的单酶结果 + 场景约束原文，交给用户放宽约束 |
| **F4: 用户上传自采 MAG** | 需要 porTraits 做性状预测 | **本方案不支持**，走另一条独立链路（跟当前推荐系统分开） |

F4 明确排除是为了避免把 porTraits/sumTraits 拉进主链路稀释目标。

---

## 七、Agent 自主查询范式（符合你的偏好）

**不预注入**：orchestrator 不提前给 Agent 灌数据，Agent 自主判断要不要调 Tool。

- `MicrobeSelectionAgent` 在 backstory / goal 里写明：
  - 当拿到 `OrganismCandidate` 列表但缺 trait 信息时，**自主调用** `MicrobeTraitTool`
  - 拿到 trait 后**自主评判**哪些是关键性状（污水场景相关），丢弃噪声性状
  - 只在证据链完整时才输出推荐
- Tool 返回结构必须带 `confidence` / `evidence_level`，方便 Agent 做相关性评判

这条对齐你之前立的"Agent 自主决策 + 信息评判"规则。

---

## 八、待讨论的决策点 `[TBD-讨论]`

**D1：Enzyme2OrganismTool 的宿主定义**
- 选项 A：只收 UniProt reviewed（SwissProt）注释，精度高但覆盖低
- 选项 B：UniProt reviewed + KEGG Organism，均衡
- 选项 C：加 TrEMBL unreviewed，覆盖最全但假阳高
- **我倾向 B**，你怎么看？

**D2：酶→菌 confidence 归一化方案**
- 选项 A：按 evidence_level 硬映射（reviewed=1.0, unreviewed=0.6, predicted=0.3）
- 选项 B：用 UniProt 的 annotation score 直接映射
- 选项 C：不归一化，透传原始档位到 Agent，让 LLM 判断
- **需要跟学生确认**：UniProt 有没有稳定的 confidence 字段

**D3：OrganismAggregator 的排序主键**
- 选项 A：cumulative_score（sum(enzyme_score × org_confidence)）
- 选项 B：max_supporting_enzyme_score（只看最强酶）
- 选项 C：supporting_enzymes 数量优先，score 打平决胜
- **我倾向 A**（累积证据），但如果目标反应只需要一个酶催化，B 也合理

**D4：Trait 硬约束清单谁来定？**
- 选项 A：由污水处理专家事先定义一套通用清单（好氧/厌氧、盐度、温度、pH）
- 选项 B：从用户输入的"污水场景描述"用 LLM 抽取（灵活但可能漏项）
- 选项 C：两者结合，先跑 LLM 抽取再对齐专家清单
- **要问学生**：污水领域有没有现成的分级标准

**D5：metaTraits 的接口稳定性调研**
- 学生本周内做半天预调研（用 P0 test set 里 Top MRR 酶反查 5-10 个宿主菌）
- 验证：接口稳不稳 / 污水相关性状覆盖度 / no_robust_majority 比例 / rate limit
- 输出：一个 `metatraits_probe_report.md`，包含 5 个 sample 菌的原始 JSON

**D6：LLM 决策层的 prompt 硬约束**
- 是否要在 prompt 里明确"禁止绕过 TraitFilterLayer 的硬约束"？
- 是否要求 LLM 每个推荐都必须引用 ≥2 条 evidence？
- **我倾向都要**，防止 LLM 编推荐理由

**D7：新增 MicrobeSelectionAgent 是独立 crew 还是并入 AdsorptionCrew？**
- 选项 A：独立成一个新 crew（EnzymeCrew / MicrobeCrew）
- 选项 B：作为 AdsorptionCrew 的新 stage 挂进去
- **我倾向 A**：吸附法和微生物法是两条并列业务线，混在一起会污染 orchestrator 的意图路由

**D8：v1 checkpoint 的加载策略**
- 每次调用都加载 5 个 seed 的 checkpoint 太慢
- 选项 A：进程启动时预加载到 GPU 常驻
- 选项 B：LRU 缓存，冷启动接受
- 选项 C：加个模型推理服务（FastAPI + gRPC），跟 Agent 分离
- **要看 wrapper 的 QPS 预期**再定，M3 联调时明确

---

## 九、排期建议

| 阶段 | 内容 | 时间 |
|---|---|---|
| **M1（本轮）** | v1 冻结打包 + 交付说明 | 1.5 天 |
| **M2（本周）** | wrapper 契约 + EnzymeCAGE Agent + smoke test | 3-4 天 |
| **M3（下周）** | 端到端 3 case（"底物→反应→酶"链，暂不含菌层） | 1 周 |
| **M3.5** | metaTraits 接口预调研（D5） + 决策点定稿（D1-D8） | 3 天 |
| **M4a** | Enzyme2OrganismTool + OrganismAggregator | 3-5 天 |
| **M4b** | MicrobeTraitTool + TraitFilterLayer | 3-5 天 |
| **M4c** | MicrobeSelectionAgent + 端到端 3 case（"底物→反应→酶→菌"完整链） | 1 周 |
| **M5** | Design Explaining 挂接 + 上线灰度 | 后续 |

**关键节点**：M3 完成 = 有第一个 demo 可看；M4c 完成 = 完整"底物→反应→酶→菌"链路上线。

---

## 十、给学生讨论时的建议

1. 你先看 D1-D8 这 8 个决策点，本轮 review 时挨个过一遍立场
2. D5 metaTraits 预调研让学生本周做，成本 0.5 天，是所有下游动作的前提
3. 学生原来的想法（"识别性状 → LLM 选菌"）在这个框架里被拆成了**过滤层 + 决策层**两块，让他理解**"LLM 不该做主决策"** 这个架构判断是本次讨论的核心
4. 排期上 M3.5-M4c 加起来 3-4 周，不影响 M1-M3 主线，可以并行做前置调研

先按这份讨论稿过，你和学生 review 完把 D1-D8 定下来，我再出一份实施细节文档（含具体 API endpoint / 错误处理 / 单测覆盖）。
