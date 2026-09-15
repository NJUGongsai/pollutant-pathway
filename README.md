# EnzymeCrew（仓库：`depending`）

**基于 LangGraph 的多智能体编排系统，用于「底物 → 反应 → 酶 → 菌」的酶-微生物推荐。**

面向水质风险控制中的污染物生物降解场景：给定一个底物（污染物）分子，系统检索/预测其可能的生化反应，用冻结的 EnzymeCAGE v1 模型对候选酶打分排序，再映射到宿主微生物并（在性状层就绪后）做污水适配筛选，最终产出带完整证据链的推荐报告。

> 命名说明：项目名 **EnzymeCrew**；GitHub 仓库名 **`depending`**（历史沿用）。二者指同一套代码。

---

## 仓库结构总览（四板块）

本仓库实际上承载四个职责板块，边界如下：

| 板块 | 目录 | 职责 | 维护者 |
|---|---|---|---|
| **① 编排核心** | `src/` · `main.py` · `config/` · `configs/` | 底物→反应→酶→菌 的 LangGraph 编排、节点/工具/契约 | 老师侧（主线） |
| **② 冻结排序底座** | `assets/enzyme_cage_v1/` | EnzymeCAGE v1 **模型定义代码**（GVP+SchNet+attention）；**权重不在仓库**，托管在 Hugging Face `WQRCE/EnzymeCAGE-v1`（私有） | 学生侧，冻结 |
| **③ 反应预测引擎候选** | `reaction_analogy/` · `reaction_v3/` · `data/bbd_*` · `bbd_predictions/` | 师兄的 BBD/USPTO 降解产物预测 + ranker（v2→v33），**evaluation candidate，非默认引擎** | 师兄（`feat/bbd-uspto-integrated`） |
| **④ 交付/文档** | `docs/` · `reports/` · `cases/` · `scripts/` · `tests/` | 师生评审、真跑证据、测试案例、晨羽脚本、单测 | 学生侧 |

关键原则：**板块②是唯一冻结排序底座，板块③是「候选待裁定」的预测引擎，二者都不并入板块①的主编排默认路径**，除非对应裁定（T6-2）落地。

---

## 业务链路

```
底物(Substrate)
   │  解析 SMILES / 名称→结构
   ▼
反应(Reaction) ──相似性 OK──▶ route_b 历史反应检索
   │                          route_c 泛化回退
   └──相似性 不OK──▶ reaction_prediction（独立预测器，fallback）
   │
   ▼  两路候选反应合并
酶 Pool 构造 ──▶ EnzymeCAGE v1（冻结排序底座）──▶ LLM 重排
   │
   ▼
酶 → 宿主微生物映射 ──▶ 性状过滤(M4b, 契约锁定) ──▶ LLM 选菌
   │
   ▼
证据合成 → 推荐报告（全链路 provenance）
```

**核心原则 — 模型/智能体职责分离**：EnzymeCAGE v1 是**唯一冻结的排序底座**（给定 enzyme_pool 输入 → 输出排序分数），不引入第二个并行打分器；所有 pool 构造、结果解释、后处理、交互编排均由智能体层完成，不修改冻结模型。

**反应预测引擎现状**：`reaction_prediction` 的 fallback 当前实现为 **BioTransformer ENVMICRO**（EAWAG 规则系统，SMARTS 命中 + SMIRKS 变换，非数据库查询；其 `Enzyme(s)` 字段不可作为候选酶 UID）。师兄的 **depending v3.2/v3.3（`reaction_analogy/`）已合入本仓库作为 evaluation candidate**，MISS 后的正式 predictor 选型待 **T6-2 裁定**——合并代码≠切换引擎。

> **BBD 降解产物预测最终成绩**：以 `bbd_predictions/bbd_hybrid_eval_v5.json` 为准（混合口径 Hit@1 89.5% / Hit@10 95.3%，P5.1 版本）。`reaction_analogy/` 下各历史版本产物仅作审计证据链保留，对外引用一律以该文件为准。

---

## 系统架构（LangGraph StateGraph）

10 个节点，双运行模式，路由函数按 `pipeline_mode` 分叉：

| 节点 | 职责 |
|------|------|
| `orchestrator` | 入口编排、模式路由 |
| `substrate` | 底物解析（名称/SMILES → 结构） |
| `reaction` | 基于底物相似性检索候选反应（route_b/route_c） |
| `reaction_prediction` | 相似性失败时的独立反应预测（fallback；引擎选型见上） |
| `enzyme_pool` | 候选反应合并 + 酶池构造（含 route 决策 provenance） |
| `enzymecage` | 调用冻结 EnzymeCAGE v1 wrapper 排序 |
| `llm_reranking` | LLM 重排（不可用时诚实 passthrough 降级） |
| `microbe_selection` | 酶 → 宿主微生物映射 + LLM 选菌 |
| `trait_filter` | 污水性状过滤（**M4b 契约锁定**，当前为诚实 soft-passthrough） |
| `evidence_synthesis` | 全链路证据合成与报告生成 |

- **M3 线性流**：底物 → 反应 → 酶池 → EnzymeCAGE 排序
- **M5 全量流**：追加 reaction_prediction fallback、reranking、microbe、trait、synthesis

---

## 运行

### 环境准备

```bash
# Python >= 3.10
pip install -e .            # 或 pip install -e ".[dev]" 装测试依赖
cp .env.example .env        # 填入实际 LLM / EnzymeCAGE 配置
```

### 本地 Dry-run（mock 替代推理，验证流程）

设置 `ENZYMECAGE_DRY_RUN=1` 后，`enzymecage_client` 用 md5 确定性 mock 顶替对 EnzymeCAGE 真实权重的调用——**本地无需 GPU、无需加载模型即可跑通全链路**，但输出仅用于 pool 构造与流程贯通验证，**不构成真实排序证据**（真实排序须在晨羽生产环境运行）。

```bash
ENZYMECAGE_DRY_RUN=1 python3 main.py '帮我找能降解己烷(CCCCCC)的酶' --mode m5
```

### 生产运行（晨羽 HPC）

生产环境部署在晨羽 HPC 同一 Python 3.12.3 环境，直接 `import` 冻结的 EnzymeCAGE wrapper。运行时路径见 [`configs/chenyu_paths.yaml`](configs/chenyu_paths.yaml)，同步脚本见 [`scripts/sync_to_chenyu.sh`](scripts/sync_to_chenyu.sh)。将 `.env` 中 `ENZYMECAGE_DRY_RUN` 改为 `0`。

**冻结底座权重**托管在 Hugging Face `WQRCE/EnzymeCAGE-v1`（私有 model repo）：
- 业务主线 = `3b_ensemble`（seeds 40–44 五种子均值概率集成，MRR@10 0.5043 / Hit@1 0.4089）
- 参考 = `600m_ensemble`（观测 AUC 更高，非业务模型）

---

## 目录结构

```
depending/                       # 仓库根（项目名 EnzymeCrew）
├── main.py                      # 入口
├── pyproject.toml               # 依赖与打包
├── src/                         # ① 编排核心
│   ├── graph.py                 #   LangGraph StateGraph 装配与路由
│   ├── state.py                 #   全局 State 定义
│   ├── nodes/                   #   10 个流程节点
│   ├── tools/                   #   底层工具（substrate_parser / reaction_retriever
│   │                            #     / enzyme_pool_builder / enzymecage_client
│   │                            #     / microbe_recommender / trait_query 等）
│   ├── schemas/                 #   证据 / 数据契约模型
│   └── utils/                   #   LLM 客户端等
├── assets/enzyme_cage_v1/       # ② 冻结排序底座（模型定义代码，权重在 HF）
│   ├── model.py / schnet.py / gvp/ / interaction.py / attention.py / ...
│   └── LICENSE                  #   CC-BY-NC 4.0（原 EnzymeCAGE）
├── reaction_analogy/            # ③ 反应预测引擎候选（师兄 BBD/USPTO ranker v2→v33）
├── reaction_v3/                 #    enviPath 反应模板（lib_envipath）
├── data/bbd_*                   #    BBD ranker 训练数据（v3/v31/v32/v5/hfix）
├── bbd_predictions/             #    BBD 各版本评测输出（结果数据，非代码）
├── config/                      # settings 与配置加载
├── configs/                     # 运行时路径契约（chenyu_paths.yaml）
├── cases/                       # 测试案例（case_1~3）
├── scripts/                     # 晨羽探测 / 真跑 / 同步脚本
├── reports/                     # 真跑与 dry-run 证据归档
├── docs/                        # 框架文档 / 师生评审 / 可视化
└── tests/                       # 单元测试
```

---

## 配置说明

复制 `.env.example` 为 `.env` 并填入实际值。关键项：

| 变量 | 说明 |
|------|------|
| `LLM_API_BASE_URL` / `LLM_API_KEY` | OpenAI-compat MaaS 网关 |
| `ENZYMECAGE_DRY_RUN` | `1`=本地 mock；`0`=晨羽真实推理 |
| `ENZYMECAGE_BACKBONE` | `3b_ensemble`（默认，业务主线）/ `600m_ensemble`（显存降级） |
| `ENZYMECAGE_CODE_ROOT` / `*_PACKAGE_ROOT` | 晨羽冻结组件路径 |

> ⚠️ `.env`（真实密钥）已在 `.gitignore` 中排除，切勿提交。

---

## 第三方依赖与开源边界

- **EnzymeCAGE v1 模型**：模型定义代码在本仓库 `assets/enzyme_cage_v1/`，权重在 HF `WQRCE/EnzymeCAGE-v1`（私有）。此模型是 Liu, Yong et al. *Nature Catalysis* 2026 的论文模型，受 **CC-BY-NC 4.0** 约束（非商用 + 署名 + 禁用于药物发现）。见 `assets/enzyme_cage_v1/LICENSE`。
- 化学结构处理依赖 **RDKit**。
- 反应预测候选（`reaction_analogy/`）依赖师兄的 BBD/USPTO 工具链与 enviPath 数据（`reaction_v3/data/lib_envipath/`，见其 `PROVENANCE.txt`）。

---

## License

本仓库是**双许可**结构：

| 范围 | 许可 |
|---|---|
| 编排代码（`src/` 等，板块①核心） | Internal R&D License（见 `pyproject.toml`） |
| 模型定义 & 权重（`assets/enzyme_cage_v1/`，板块②） | **CC-BY-NC 4.0**（见 `assets/enzyme_cage_v1/LICENSE`） |

> 板块③（`reaction_analogy/`）的许可以师兄原分支的声明为准，引用前确认。

---

## 状态

- **主线**：图结构骨架 10/10 节点已装配；酶推荐主干（底物→反应→酶池→EnzymeCAGE→重排）已实装并通过晨羽真跑验证；微生物支线完成事实映射；性状层（M4b）按契约锁定，尚未启动运行时。
- **反应预测器**：fallback 引擎选型中——BioTransformer ENVMICRO 内部机制已验证；师兄 depending v3.2/v3.3 已合入为 evaluation candidate，正式选型待 T6-2 裁定。
- **分支**：`main` = 单一线索（含上面全部板块）；`feat/bbd-uspto-integrated` 保留给师兄继续推进；历史 `demov2` 已打 `archive/demov2-v4.2` tag 归档。
- 详见 `docs/` 下框架与评审文档（`docs/teacher_reviews/` 有最新 T6-R3 裁定）。