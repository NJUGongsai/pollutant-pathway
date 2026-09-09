# EnzymeCrew

**基于 LangGraph 的多智能体编排系统，用于「底物 → 反应 → 酶 → 菌」的酶-微生物推荐。**

面向水质风险控制中的污染物生物降解场景：给定一个底物（污染物）分子，系统检索/预测其可能的生化反应，用冻结的 EnzymeCAGE v1 模型对候选酶打分排序，再映射到宿主微生物并（在性状层就绪后）做污水适配筛选，最终产出带完整证据链的推荐报告。

---

## 一、业务链路

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

## 二、系统架构（LangGraph StateGraph）

10 个节点，双运行模式，路由函数按 `pipeline_mode` 分叉：

| 节点 | 职责 |
|------|------|
| `orchestrator` | 入口编排、模式路由 |
| `substrate` | 底物解析（名称/SMILES → 结构） |
| `reaction` | 基于底物相似性检索候选反应（route_b/route_c） |
| `reaction_prediction` | 相似性失败时的独立反应预测（fallback；引擎选型中：BioTransformer ENVMICRO 机制已验证——EAWAG 规则系统，SMARTS 命中 + SMIRKS 变换，非数据库查询；其 `Enzyme(s)` 字段不可作为候选酶 UID） |
| `enzyme_pool` | 候选反应合并 + 酶池构造（含 route 决策 provenance） |
| `enzymecage` | 调用冻结 EnzymeCAGE v1 wrapper 排序 |
| `llm_reranking` | LLM 重排（不可用时诚实 passthrough 降级） |
| `microbe_selection` | 酶 → 宿主微生物映射 + LLM 选菌 |
| `trait_filter` | 污水性状过滤（**M4b 契约锁定**，当前为诚实 soft-passthrough） |
| `evidence_synthesis` | 全链路证据合成与报告生成 |

- **M3 线性流**：底物 → 反应 → 酶池 → EnzymeCAGE 排序
- **M5 全量流**：追加 reaction_prediction fallback、reranking、microbe、trait、synthesis

## 三、运行

### 环境准备

```bash
# Python >= 3.10
pip install -e .            # 或 pip install -e ".[dev]" 装测试依赖
cp .env.example .env        # 填入实际 LLM / EnzymeCAGE 配置
```

### 本地 Dry-run（以 mock 替代 EnzymeCAGE 推理，仅验证流程，不产出真实排序）

设置 `ENZYMECAGE_DRY_RUN=1` 后，`enzymecage_client` 用 md5 确定性 mock 顶替对 EnzymeCAGE 真实权重的调用——因此**本地无需 GPU、无需加载 EnzymeCAGE 模型即可跑通全链路**，但输出仅用于 pool 构造与流程贯通验证，**不构成真实排序证据**（真实排序须在晨羽生产环境运行）。

```bash
ENZYMECAGE_DRY_RUN=1 python3 main.py '帮我找能降解己烷(CCCCCC)的酶' --mode m5
```

### 生产运行（晨羽 HPC）

生产环境部署在晨羽 HPC 同一 Python 3.12.3 环境，直接 `import` 冻结的 EnzymeCAGE wrapper。运行时路径见 [`configs/chenyu_paths.yaml`](configs/chenyu_paths.yaml)，同步脚本见 [`scripts/sync_to_chenyu.sh`](scripts/sync_to_chenyu.sh)。将 `.env` 中 `ENZYMECAGE_DRY_RUN` 改为 `0`。

## 四、目录结构

```
enzymecage_crew/
├── main.py                 # 入口
├── pyproject.toml          # 依赖与打包
├── src/
│   ├── graph.py            # LangGraph StateGraph 装配与路由
│   ├── state.py            # 全局 State 定义
│   ├── nodes/              # 10 个流程节点
│   ├── tools/              # 底层工具（substrate_parser / reaction_retriever
│   │                       #   / enzyme_pool_builder / enzymecage_client
│   │                       #   / microbe_recommender / trait_query 等）
│   ├── schemas/            # 证据 / 数据契约模型
│   └── utils/              # LLM 客户端等
├── config/                 # settings 与配置加载
├── configs/                # 运行时路径契约（chenyu_paths.yaml）
├── cases/                  # 测试案例（case_1~3）
├── scripts/                # 晨羽探测/真跑/同步脚本
├── reports/                # 真跑与 dry-run 证据归档
├── tests/                  # 单元测试
└── docs/                   # 框架文档 / 师生评审 / 可视化
```

## 五、配置说明

复制 `.env.example` 为 `.env` 并填入实际值。关键项：

| 变量 | 说明 |
|------|------|
| `LLM_API_BASE_URL` / `LLM_API_KEY` | OpenAI-compat MaaS 网关 |
| `ENZYMECAGE_DRY_RUN` | `1`=本地 mock；`0`=晨羽真实推理 |
| `ENZYMECAGE_BACKBONE` | `3b_ensemble`（默认）/ `600m_ensemble`（显存降级） |
| `ENZYMECAGE_CODE_ROOT` / `*_PACKAGE_ROOT` | 晨羽冻结组件路径 |

> ⚠️ `.env`（真实密钥）已在 `.gitignore` 中排除，切勿提交。

## 六、第三方依赖

- **EnzymeCAGE**：本项目将其作为**冻结的排序底座**调用，官方仓库不随本仓库重分发。请从官方渠道获取并按 `.env` 中的 `ENZYMECAGE_*` 路径配置。
- 化学结构处理依赖 **RDKit**。

## 七、状态

当前进度：图结构骨架 10/10 节点已装配；酶推荐主干（底物→反应→酶池→EnzymeCAGE→重排）已实装并通过晨羽真跑验证；微生物支线完成事实映射；性状层（M4b）按契约锁定，尚未启动运行时；反应预测器 fallback 引擎选型中（BioTransformer ENVMICRO 内部机制已由学生侧源码核查确认，等待弓师兄模型返回后三工具横向比较闭环）；D4 按需补资产（AlphaFill/P2Rank 口袋）已完成 100 UID 困难样本小试，作为 M4 立项前置摸底归档。详见 `docs/` 下框架与评审文档。

## 八、License

Internal R&D License（内部研发，见 `pyproject.toml`）。
