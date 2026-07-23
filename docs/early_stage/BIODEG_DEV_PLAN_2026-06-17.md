# BioDeg 项目开发计划

> 文件创建时间：2026-06-17
> 项目代号：**BioDeg**（biodegradation 缩写；如坚持按 agent 首字母可换 CBEB / 其他）
> 状态：草案 v1（按业务命名重写 agent 角色），等你 review 后定稿

---

# 0. 终极目标主动复述

**输入**：一个污染物（化学名 / SMILES / CAS；新污染物 corpus 可能没见过）
**输出**：能降解它（或大概率能降解它）的酶 + 推荐理由 + 置信度

**用户定位**：
- **面向对象**：专业生物人员（学生 / 测试者）——输出用完整专业表达（EC number / UniProt / 反应机理 / Tanimoto / 置信度数学依据）
- **开发侧**（你）：不直接消费产出，需要生物语义解读时由 AI 助手（我）转译
- **测试**：交生物专业人员，不在 v0.1 scope 内

**不区分新/老污染物**——同一套流程，精确匹配优先；找不到就走 similarity transfer，二者用同一套置信度叙述呈现。

**R3 模型定位**：R3 在本系统中是**贯穿 4-agent 全程的三重角色基座**，不是孤立的外部验证点：
1. **检索后端 (retrieval)** —— 提供候选酶 / 微生物（r2e / s2m / e2m / encoder forward）
2. **验证锚 (verification)** —— 给 LLM 推理结果做事实 gating（is_known_ec4 / get_ec3_neighbors）
3. **解释材料库 (explanation source)** —— 提供 metadata 供 BioremediationConsultant 写报告（lookup_metadata）

具体每个 agent 怎么调 R3 见 §1.5 。
Agent 负责 curation / reranking / explanation / abstention gating，结构性事实必须从 R3 corpus 取（cite-or-die）。

---

## 1. 业务流程总览（一图两路径）

```
       [污染物：name / SMILES / CAS]
                 │
                 ▼
        ┌──────────────────────────┐
        │ ContaminantProfiler      │   污染物画像师
        │ （污染物画像）           │   解析 → 标准 SMILES +
        │                          │   物化属性 + 已知降解线索
        └────────┬─────────────────┘
                 │
       ┌─────────┴────────────────────────┐
       ▼                                  ▼
┌──────────────────────────┐   ┌────────────────────────────┐
│ BiotransformationPredictor│   │ EnzymeCandidateMiner       │
│ （生物转化预测师）        │   │ （酶候选挖掘师）           │
│ ─────────────────────────│   │ ──────────────────────────│
│ 推断可能的降解反应路径   │   │ 污染物 → DRFP →            │
│ 生成候选 RxnSMILES →     │   │ s2m_retrieval（闭域）→     │
│ encode → r2e_retrieval   │   │ microbe → enzyme           │
└──────────────┬───────────┘   └──────────────┬─────────────┘
               │                              │
               └──────────────┬───────────────┘
                              ▼
              ┌────────────────────────────────┐
              │ BioremediationConsultant       │   生物修复顾问
              │ （综合咨询）                   │
              │ ────────────────────────────── │   交叉 / Tanimoto /
              │ 专业生物语语义输出             │   置信度 / 事实可追溯
              │ （面向学生 / 测试人员）         │
              └──────────────┬─────────────────┘
                             ▼
              [推荐酶 + 专业报告 + 置信度]
```

**两路径独立信号**：BiotransformationPredictor 走 reaction-side，EnzymeCandidateMiner 走 substrate-side，BioremediationConsultant 做交叉验证。两条信号都命中 → 高置信；只一条命中 → 中置信；都不命中 → 走 abstain 路径。

---

## 1.5 R3 在 4-Agent 中的全程使用矩阵

### 1.5.1 R3 toolkit 能力清单（学生交付的 7 个 primitive）

| Primitive | 类型 | 用途 |
|---|---|---|
| `r3_reaction_encoder.npz` + numpy forward | encoder | **开域** RxnSMILES → 256-d vector |
| `r2e_retrieval` | retrieval | reaction emb → top-K enzyme |
| `e2m_retrieval` | retrieval | enzyme → top-K microbe |
| `s2m_retrieval` | retrieval | substrate → top-K microbe |
| `lookup_metadata` | metadata | 任意 ID → EC / UniProt / sequence / organism / SMILES |
| `is_known_ec4` | gating | EC-4 是否在 corpus |
| `get_ec3_neighbors` | expansion | 给定 EC-3 返回邻居酶集合（cross-class transfer）|

### 1.5.2 4 Agent × R3 调用矩阵

| Agent | R3 使用方式 | 调用 primitive | R3 角色 |
|---|---|---|---|
| **ContaminantProfiler**污染物画像师 | 检查污染物是否已在 corpus（精确匹配优先）；命中 → 走 known-substrate 快速路径 | `lookup_metadata`（substrate 维度）| **检索** |
| **BiotransformationPredictor**生物转化预测师 | LLM 生成候选 RxnSMILES → R3 encoder 编码（**开域 forward**）→ r2e_retrieval 拉候选 enzyme → 候选 EC-4 过 is_known_ec4 fact-gating → 不在 corpus 的 EC-4 走 get_ec3_neighbors transfer | reaction_encoder + r2e + is_known_ec4 + get_ec3_neighbors | **检索 + 验证** |
| **EnzymeCandidateMiner**酶候选挖掘师 | 污染物 SMILES → DRFP → s2m_retrieval（v0.1 闭域）拉 microbe → lookup_metadata 反查 microbe 上的 enzyme list → lookup_metadata 拿 EC/UniProt | s2m + lookup_metadata（× 多次）| **检索** |
| **BioremediationConsultant**生物修复顾问 | 接收两路径候选 → is_known_ec4 打 known/unknown 标签 → get_ec3_neighbors 验证两路径候选是否同 EC-3 邻域（一致性信号）→ lookup_metadata 拉完整专业信息写报告 → Tanimoto（rdkit，外部独立信号）→ cite-or-die：所有 enzyme 必须能在 R3 corpus lookup 到 | is_known_ec4 + get_ec3_neighbors + lookup_metadata（× 大量）| **验证 + 解释** |

### 1.5.3 三类角色 × 数学动作 × 失败 fallback

| R3 角色 | 数学动作 | 流程位置 | 失败 fallback |
|---|---|---|---|
| 检索 | cosine top-K | Predictor / Miner | top-K 全部 score < 0.6 → 走 EC-3 transfer |
| 验证 | `is_known_ec4(ec4) ∈ {True, False}` | Predictor / Consultant | False → 标记 unknown 不删除，由 Consultant 在置信度章节标注 |
| 解释 | `lookup_metadata(id)` 字段读取 | Consultant | id 查不到 metadata → 必须 abstain 或丢弃（cite-or-die）|

### 1.5.4 核心原则

- 每一步的**结构性事实**（EC / UniProt / sequence / 反应方程）必须能从 R3 corpus lookup 到
- **LLM 只允许做推理与组织语言**，不允许编造任何 ID 或字段
- R3 是贯穿全程的事实底座，不是某一个 agent 的专属工具

---

## 2. 技术栈决策（已锁）

| 项 | 选择 | 备注 |
|---|---|---|
| 编排框架 | **CrewAI 1.14.7** | 已验过 Flow kickoff contract |
| 编排模式 v0.1 | **Crew sequential**（不上 Flows DSL）| 4 节点线性 + 1 处并行 |
| 编排模式 v0.2 触发 | 出现条件循环 / 低置信度回退时 | 局部 Flow 嵌入，主线仍 Crew |
| LLM provider | DashScope（百炼）OpenAI 兼容接口 | API key 已交付 |
| 基底模型 | `qwen3.7-max` | 阿里云 Model Studio 官方 ID（已确认）|
| Python | 3.10.12 | 已验 |
| venv 隔离 | 独立 .venv，与 AdsorptionCrew / R3 toolkit 隔离 | |
| R3 集成 | numpy-only `r3_reaction_encoder.npz` + 学生交付的 4 retrieval API | cosine 1.0 已验 |

---

## 3. 项目骨架（v0.1 目录结构）

```
~/biodeg_2026-06-17/
├── .venv/                          # 独立隔离环境
├── .env                            # 百炼 API key（gitignore）
├── .gitignore
├── pyproject.toml
├── README.md
├── docs/
│   ├── BIODEG_DEV_PLAN_2026-06-17.md           # ← 本文件
│   ├── BIODEG_OBJECTIVE_2026-06-17.md          # 终极目标契约（v0.1 写）
│   └── BIODEG_AGENT_SPEC_v0.1.md               # 4 agent prompt + I/O schema
├── biodeg/
│   ├── __init__.py
│   ├── agents/
│   │   ├── contaminant_profiler.py             # 污染物画像师
│   │   ├── biotransformation_predictor.py      # 生物转化预测师
│   │   ├── enzyme_candidate_miner.py           # 酶候选挖掘师
│   │   └── bioremediation_consultant.py        # 生物修复顾问
│   ├── tools/
│   │   ├── name_to_smiles_tool.py
│   │   ├── reaction_encode_tool.py             # 调 r3_reaction_encoder.npz
│   │   ├── r2e_tool.py                         # 调 R3 toolkit
│   │   ├── s2m_tool.py
│   │   ├── tanimoto_tool.py                    # rdkit
│   │   └── metadata_tool.py
│   ├── crew/
│   │   ├── biodeg_crew.py                      # Crew 装配
│   │   └── tasks.py
│   ├── llm/
│   │   └── bailian_llm.py                      # OpenAI 兼容 wrapper
│   ├── schemas/
│   │   ├── pollutant.py                        # Pydantic models
│   │   ├── enzyme_candidate.py
│   │   └── recommendation.py                   # 专业输出 schema（EC / UniProt / 机理 / Tanimoto / 置信度）
│   └── config/
│       └── prompts/                            # agent backstory + task description
├── data/
│   ├── r3_reaction_encoder.npz                 # 从学生交付 copy（5.6M）
│   ├── corpus_meta_pointer.txt                 # 指向 R3 corpus 路径
│   └── pollutant_test_set.csv                  # v0.1 验收用 5-10 个污染物
├── tests/
│   ├── test_tools.py
│   ├── test_agents_smoke.py
│   └── test_crew_e2e.py
└── scripts/
    └── run_demo.py                             # 命令行入口
```

---

## 4. 三阶段路线图

### v0.1（**目标：端到端 happy path**）
**Done definition**：CLI 输入一个化学名，4 agent sequential 跑通，输出 1 个推荐酶 + 理由 + 置信度。**不处理低置信度回退**，不评测。

### v0.2（**目标：agentic RAG + 置信度回退**）
**Done definition**：
- 引入局部 Flow（router → listen 收尾，按 v0.1 已验契约）
- 低置信度（< 0.6）触发 D agent 重生成 RxnSMILES，最多 2 次
- 知识库注入：把已知酶-底物对作为 RAG 上下文，提升 Explainer 解释质量
- agentic：Explainer 判断置信度后**主动决定**是回退、abstain、还是 commit

### v0.3（**目标：优化 + 评测**）
- 引入 substrate encoder（让学生再交付一份 npz，开域查询）
- 验收数据集：~50 个污染物（含新污染物），人工标注 ground-truth top-K 酶家族
- 报告：MRR / top-K hit / abstain rate / explainability 主观分

---

## 5. v0.1 任务拆解（按顺序，每条都是一个独立 PR）

| # | 任务 | 依赖 | 工作量 |
|---|---|---|---|
| T1 | 项目骨架 + venv + pyproject + .gitignore + README | - | 0.5h |
| T2 | 百炼 LLM wrapper（OpenAI 兼容 + qwen3.7-max hello-world test）| T1 | 1h |
| T3 | Pydantic schemas（Pollutant / EnzymeCandidate / Recommendation）| T1 | 0.5h |
| T4 | NameToSmilesTool（PubChem fallback + rdkit 校验）| T3 | 1h |
| T5 | R2ETool（包学生交付的 r2e_retrieval + cosine 1.0 复测）| T3 | 1h |
| T6 | ReactionEncodeTool（numpy forward 按 MODEL_ARCHITECTURE.md）| T3 | 1.5h |
| T7 | S2MTool（包 R3 s2m_retrieval）| T3 | 0.5h |
| T8 | TanimotoTool（rdkit）+ MetadataTool | T3 | 1h |
| T9 | **ContaminantProfiler** agent（污染物画像师）+ prompt + smoke test | T2,T4 | 1.5h |
| T10 | **BiotransformationPredictor** agent（生物转化预测师，含 LLM 生成 RxnSMILES 子步骤）| T2,T5,T6 | 2h |
| T11 | **EnzymeCandidateMiner** agent（酶候选挖掘师）| T2,T7 | 1h |
| T12 | **BioremediationConsultant** agent（生物修复顾问，专业输出：EC / UniProt / 机理 / Tanimoto / 置信度，cite-or-die）| T2,T8 | 2h |
| T13 | BioDeg Crew 装配（sequential，1 处 async_execution 并行）| T9-T12 | 1h |
| T14 | scripts/run_demo.py CLI 入口 | T13 | 0.5h |
| T15 | 5 个污染物 happy path 测试集（如 BPA / atrazine / PFOA …）| T14 | 1h |
| T16 | docs/BIODEG_OBJECTIVE_2026-06-17.md（v0.1 写）| T13 | 1h |
| T17 | docs/BIODEG_AGENT_SPEC_v0.1.md（每个 agent 的角色 + prompt + I/O）| T9-T12 | 1.5h |

**v0.1 总工作量估算**：~18 工时（不含 R3 toolkit 学生交付前置——已 done）

---

## 6. 风险点（提前识别）

| # | 风险 | 触发概率 | 缓解 |
|---|---|---|---|
| R1 | qwen3.7-max 生成 RxnSMILES 不规范（rdkit 解析失败）| 高 | BiotransformationPredictor 加 rdkit 校验 + 重试，最多 3 次 |
| R2 | R3 corpus 对工业污染物覆盖率低（EnzymeCandidateMiner 的 s2m 全部 miss）| 中 | v0.1 不强求双信号命中；BioremediationConsultant 仅有 reaction-side 也能输出 |
| R3 | BioremediationConsultant 输出"看似专业但其实编造" | 中 | prompt 强约束 cite-or-die；只能引用 R3 检索结果 + Tanimoto 数字；学生 review 抽查 |
| R4 | 基底模型 token 成本失控 | 低 | T13 加 max_iter 限制；v0.1 单次推理 < 0.5 元 |
| R5 | reaction encoder numpy forward 数值漂移 | 低 | T6 加 cosine ≥ 0.9999 sanity check |

---

## 7. 你需要拍板的事

**P0（不拍板就开不了工）**

1. 项目代号：**BioDeg**（默认）/ 按 agent 首字母 CBEB / 别的
2. 项目目录名：`~/biodeg_2026-06-17/`（按代号 + 日期；改代号则同步改）
3. 4 个 agent 业务命名是否接受：ContaminantProfiler / BiotransformationPredictor / EnzymeCandidateMiner / BioremediationConsultant

**P1（v0.1 内可后补）**

4. abstain 阈值：当 reaction-side + substrate-side 都拿不到 score ≥ 0.6 候选时直接 abstain，还是仍给一个 low-confidence 推荐？我倾向 abstain
5. 输出格式：专业 markdown 报告 + JSON dump（供下游程序消费 / 学生 review）默认两者都给

---

## 8. 一句话总结

BioDeg = 用 **CrewAI 1.14.7 sequential** 编排 4 个生物降解领域角色 agent（**ContaminantProfiler** 画像 → **BiotransformationPredictor** 反应路径预测 ‖ **EnzymeCandidateMiner** 酶库挖掘 → **BioremediationConsultant** 综合咨询），输出面向专业生物人员；底座是已验证的 R3 retrieval toolkit（**贯穿全程的检索+验证+解释三重角色**）+ 百炼 `qwen3.7-max`；v0.1 跑通端到端 happy path（~18 工时），v0.2 引入局部 Flow 做置信度回退，v0.3 评测 + 开域 substrate encoder。
