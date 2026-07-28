# ReactionAgent 设计文档（v2 · 诚实评估先行 + 增强版不训练 agent）

> 日期：2026-07-28（v2 取代同日 v1）
> 范围：`CC/branch/ReactionAgent`（本地 LangChain/LangGraph 单 agent，全新工程）
> 目标：输入未知污染物底物 X → agent 从**多条**相似已知反应 A→B 归纳可迁移的转化概念，**有依据地**逐跳推测 X 的多步降解路径；证据不足时**拒答**。
> 定位：把已验证的 `extract_rea_trans_fea` 引擎升级为"证据编排器"，并**先建立诚实的端到端评估**再动刀。
> v1→v2 的原因：外部评审核对代码后确认——现有 67.1% 是"条件排序"指标（用了 oracle donor 选择 + held-out 共反应物 + 仅字符串去重），端到端真实能力未知，**首要瓶颈很可能是覆盖/生成与评估诚实性，而非 DRFP 排序**。v1（LLM 薄壳包旧引擎）会继承此天花板，故调整。

---

## 1. 目标与非目标

### 1.1 目标
- **P0 先行**：建立诚实的端到端 benchmark，定位瓶颈是"覆盖"还是"排序"。
- **增强版不训练 agent**：本地 LangGraph 单 tool-calling agent（自由推理），LLM 编排确定性工具，产出多步降解路径 + 每步**证据卡**。
- 直击两处历史痛点：
  - **A（选参照反应）**：从"单 donor 最近邻"改为"**多 support 证据集**"，LLM 在上下文中归纳共同转化（≈ transformation prototype，无需训练 encoder）。
  - **B（学特征 + 生成）**：**多尺度模板**（radius 0/1/2）+ RDKit 确定性生成，攻 35% 覆盖天花板；LLM 做**证据融合 listwise 择优**，DRFP 降为诸特征之一。
- **拒答**：证据不足时输出"无法有依据推测"，而非强给高分。

### 1.2 非目标（本期不做，架构留插槽）
- 不训练任何模型（site 模型 / listwise ranker / episodic 元学习 / template-free Transformer）。
- 不接入 EnzymeCAGE 3B 酶兼容性、不引入 EnzymeMap/ECREACT/enviPath 新数据层。
- 不做分支降解网络（v1 线性路径，架构预留树）。
- LLM 不直接生成产物 SMILES（避免幻觉、保价键守恒）。

---

## 2. 核心架构决策（本次头脑风暴 + 评审确定的地基）

| 决策点 | 结论 | 理由 |
|---|---|---|
| 顺序 | **诚实 benchmark（P0）先行**，再建 agent | 排序器再强也救不回没生成的产物；先定位瓶颈 |
| LLM 角色 | 编排大脑：RDKit 确定性提规则/生成，LLM 选择/归纳/择优/拒答 | 化学可追溯、价键守恒、零幻觉 |
| 证据 | **多 support 证据集**（非单 donor），LLM 上下文归纳 prototype | 攻"选错 donor"；无需训练 encoder |
| 生成 | **多尺度模板 radius 0/1/2** + RDKit RunReactants | 直接攻 35% 覆盖天花板 |
| 排序 | **证据融合 listwise**（LLM 综合多信号），DRFP 仅为一特征 | 单一 max-Tanimoto 易被偶然近邻抬高 |
| 兜底 | **拒答**（低证据/适用域外） | "有依据"= 完整可审计推理链，含反证与适用域 |
| 输出 | 多步线性路径（预留树）+ 每步**证据卡** | |
| 部署/框架 | 本地 · 数据同步本地 · LangChain(1.0)/LangGraph 单 agent | v1 已定，不变 |

---

## 3. 潜变量推理骨架（LLM 的思考结构）

不直接学 `X→Y`，而让 agent 显式沿以下链条推理，使**错误可定位**：

```
X → 转化族 T → X 上反应位点 S → 局部图编辑 Δ → 候选产物 Y → 催化酶/EC E →(可选)环境 C
```

- 本期 `T/S/Δ` 由**多尺度模板 + RDKit + LLM 归纳**近似（不训练模型）；`E` 来自酶反查；`C` 留插槽。
- 证据卡按此链条组织，便于诊断（T 错=检索/分类；S 错=区域选择性；Y 无效=化学约束；E 错=酶兼容性）。

---

## 4. Phase 0：诚实评估基准（先行交付物）

**目的**：把 `verify_substrate_retrieval.py` 的"条件排序"升级为端到端诚实评估，产出漏斗，定位瓶颈。

**必须修正**（逐条对应评审）：
1. **去 oracle donor 选择**：donor 不得依据"其候选是否含 Y_true"来挑；改为固定策略（如取检索 top-1/或 LLM 选），所有结果照单计入。
2. **不使用 held-out 共反应物**：输入只有主底物 X；共反应物按未知处理（或显式定义为输入才可用）。
3. **所有 X 进分母**：生成失败/无 donor/无候选都计入端到端分母。
4. **canonical reaction identity 去重**：canonicalize + 反应图编辑层面去重；同一 substrate→product 对同组；同一反应多 UniProt 不跨 train/test。
5. **命中判定收紧**：考虑计量数，避免 `issubset` 把"多带片段"的候选误判命中。
6. **错误谱系**：替换 `except: pass`，记录失败类型。

**产出漏斗指标**：
```
所有测试 X → 可解析 → 有适用 donor/family → ≥1 候选
→ 真产物 ∈ top-K（generation recall）→ top-1/top-3（end-to-end）→ 高置信子集准确率（selective）
```
**拆分**：至少 random（sanity）+ scaffold split + reaction-family split；报 confidence–coverage 曲线。
**验收**：得到端到端 top-1/top-3、逐阶段 recall、以及"覆盖 vs 排序"谁是主瓶颈的明确结论。

---

## 5. Agent 架构（P0 之后）

### 5.1 推理循环（LangGraph，自由推理）
```
输入 X
 ▼
每一跳 (current = X，之后 = 上一跳选定产物)：
 ① multi_view_retrieve(current)      → 多样化 support 证据集（全局+局部 motif）
 ② [LLM 归纳] 从 support set 抽象"共同转化 T"，形成假设（可多个）← 解 A
 ③ generate_candidates(support, current) → 多尺度模板(0/1/2) RDKit 生成候选 Y'（价键合法）
 ④ collect_evidence(current, Y')     → 每候选汇集：DRFP-酶集、多donor共识、适用域、酶/EC
 ⑤ [LLM listwise 择优 + 拒答]        → 综合证据挑本跳产物并写理由；证据不足→拒答 ← 解 B
 ⑥ [LLM 决策] 继续展开 / 停止
 ▼
输出：PathwayState（路径链 + 每步证据卡）；或 status=abstained
```
**停止条件**：矿化/终点 · 无候选 · 达深度上限（默认 5）· 最高证据分 < 阈值（默认 0.3，标注低可信/拒答）。

### 5.2 工具集（确定性，全本地）
| 工具 | 职责 | 底层来源 |
|---|---|---|
| `multi_view_retrieve(smiles, k)` | 全局 Morgan + 局部反应中心 motif 双视角检索，MMR 去近重复，返回**多样化 support set**（每条带 A>>B/相似度/酶/EC） | `chenyu_features` + `enzyme_lookup`（扩多视角） |
| `generate_candidates(support_reactions, substrate)` | 对每条 support 提**多尺度模板 radius∈{0,1,2}**，RDKit 生成候选 Y'，跨 support/尺度合并去重 | `pipeline`（扩多尺度） |
| `collect_evidence(substrate, candidates, enzymes)` | 每候选汇集证据：DRFP-酶集相似度（top-m 聚合非单 max）、多 donor 共识计数、适用域标记、酶/EC、best_match 先例 | `reaction_scorer`（扩聚合）+ `enzyme_lookup` |
| `check_conservation(substrate, product)` | 价键/质量/元素守恒、电荷标准化、碎裂过滤（进 LLM 择优前的硬门） | 新增（RDKit 规则） |
| `is_terminal(smiles)` | 矿化/终点判断 | 新增（轻量规则） |

**设计原则**：工具返回结构化、含证据字段的可读结果；反应中心分工遵循既有规范（MCS 用于生成，chenyu 真值仅打分场景）；工具无副作用、可单测。

### 5.3 证据卡 / 状态
```python
@dataclass
class Evidence:
    transformation_hypothesis: str      # LLM 归纳的转化族 T
    site: str                           # X 上反应位点 S（原子/键描述）
    edit: str                           # 局部图编辑 Δ 描述
    support_reactions: List[str]        # 多条支持 donor（非单条）
    support_consensus: int              # 支持同一编辑的独立 donor/尺度数
    enzymes: List[Tuple[str, str]]      # [(uniprot, ec), ...] 多条
    drfp_family_score: float            # top-m 聚合的酶反应族相似度
    applicability: str                  # "in" | "borderline" | "out"
    counter_evidence: str               # 主要反证
    confidence: float                   # 校准后置信度
    llm_rationale: str

@dataclass
class Step:
    substrate: str
    product: str
    evidence: Evidence
    low_confidence: bool = False

@dataclass
class PathwayState:
    query: str
    steps: List[Step]
    status: str   # "completed_terminal"|"max_depth"|"dead_end"|"low_confidence_stop"|"abstained"
    funnel: dict  # 每步在漏斗各阶段的通过情况（便于诊断）
    note: str = ""
```
**"有依据"= 完整可审计推理链**：转化族 + 位点 + 编辑 + 多 support donor + 多酶/EC + 适用域 + 反证 + 校准置信度 + LLM 理由；产物只由 RDKit 生成。

---

## 6. 目录结构（`CC/branch/ReactionAgent/`）
```
ReactionAgent/
├── benchmark/                 # P0 先行
│   ├── honest_eval.py         # 端到端诚实评估 + 漏斗 + 拆分
│   ├── canonical_identity.py  # canonical 反应去重/分组
│   └── splits.py              # scaffold / reaction-family split
├── agent.py                   # LangGraph 单 agent + 循环 + 停止/拒答
├── tools.py                   # 5 个工具的 @tool 封装
├── prompts.py                 # 系统提示：潜变量骨架 + 归纳/择优/拒答指引
├── state.py                   # PathwayState / Step / Evidence
├── run.py                     # CLI 入口
├── sync_assets.sh             # 从晨羽 HPC 同步 data/
├── core/                      # 移植 + 增强 extract_rea_trans_fea
│   ├── chenyu_features.py     # + 多视角/局部 motif 检索、MMR
│   ├── pipeline.py            # + 多尺度模板 radius 0/1/2
│   ├── reaction_scorer.py     # + top-m 聚合、多 donor 共识
│   └── enzyme_lookup.py
├── data/                      # 本地资产（gitignore）
└── README.md
```
**桶3 插槽**（本期空实现/接口）：`tools.py` 预留 `site_model_score` / `learned_ranker_score` / `enzyme3d_compat` / `transformer_generate` 的工具位；`Evidence` 字段已能容纳其输出。

---

## 7. 可配置项与 v2 预留

| 参数 | 默认 | 说明 |
|---|---|---|
| `max_depth` | 5 | 路径最大跳数 |
| `support_k` | 6 | support 证据集大小（MMR：全局2+局部2+远程类比1+反例1）|
| `template_radii` | [0,1,2] | 多尺度模板半径 |
| `topm_family` | 5 | 酶反应族相似度 top-m 聚合数（非单 max）|
| `confidence_threshold` | 0.3 | 低于此拒答/停止展开 |
| `branch_factor` | 1 | v1 线性；>1 长成分支树 |

---

## 8. 验证计划

- **P0 自身**：在明确的拆分上产出端到端 top-1/3、逐阶段 recall、confidence–coverage 曲线；给出"覆盖 vs 排序"瓶颈结论。
- **工具层单测**：多尺度模板对已知案例复现并扩大点火率；多视角检索/证据聚合对比旧单 donor/单 max 的变化。
- **端到端 smoke**：辛醇 `CCCCCCCCO` 复现"借醇脱氢族 → 辛醛"，并能多步展开（辛醛→辛酸…）；构造一个库内无相近转化的 X 验证 agent 正确**拒答**。
- **诚实回归**：agent 端到端指标必须用 P0 的诚实协议报告（不得回到 oracle donor / 偷共反应物）。
- **消融**：单 donor vs 多 support；固定 radius=1 vs 多尺度；单 max vs top-m 聚合；无拒答 vs 有拒答。

---

## 9. 假设与风险

- **假设**：`rxn2fp.pkl` / `reacting_center.pkl` / 反应→酶映射可拷贝到本地（中小、无许可限制）；否则退回 HPC FastAPI 服务方案。
- **风险·覆盖**：多尺度模板若仍不足以覆盖，P0 会暴露"覆盖为主瓶颈"→ 触发桶3 中的 template-free 生成器（另立 plan）。
- **风险·LLM 发散/成本**：自由推理可能多调工具 → 由 `max_depth` + 系统提示流程指引 + 工具幂等 + 每跳候选上限收敛。
- **风险·置信校准**：本期无训练，`confidence` 先用规则/证据加权近似；真正校准（temperature/isotonic/conformal）属桶3。
- **既有坑规避**：模板显式 H 伪影不点火问题已在 `pipeline._atom_query_smarts`（放宽 SMARTS）修复，移植/扩多尺度时保持。
- **诚实纪律**：任何对外汇报的判别力数字必须来自 P0 诚实协议，并标注 novelty 分桶。
