# pollutant-pathway

**Enzymatic pollutant transformation prediction with an LLM-in-the-loop, deterministic chemistry and zero-LLM scoring.**
酶催化污染物降解产物预测：确定性化学检索/编译 + 大模型提案 + 零 LLM 判分。

> 状态：科研代码存档（v4.3 工作线，2026-11）。本仓库**不含**题卷、金标、运行产物和第三方数据资产；**不报告任何成绩数字**。
> Python 包名仍为 `pathway_v43`。

---

## 1. 它做什么

给定一个污染物底物（SMILES），系统预测它在一步酶促反应后的产物，输出最多 5 个有序候选，每个候选都附带可审计的反应事件：参与物、原子编辑、证据来源和审计结果。随附一套**确定性判分器**，判分全程不调用任何模型。

## 2. 默认架构（单步 S5b，"A 臂"）

```text
底物 SMILES
  │
  ├─① 建池（零 LLM，确定性）
  │     精确记录通道（vendored v3 引擎，查已记录的酶反应）
  │   + 语料直通通道
  │   + 类比模板通道（底物相似度 ≥ 0.45，最多 8 条）
  │   → 每条候选编译成可在底物上执行的原子编辑，并附 v1 证据卡
  │
  ├─② 模型调用一次（atom_edit 协议，v2 prompt + v1 证据卡）
  │     模型对池候选排序，或自行写出原子编辑（novel 提案）
  │
  ├─③ 确定性执行与审计
  │     原子编辑执行（AtomTool / MoleCode）
  │   → 11 项审计检查（结构解析、身份保真、参与物完整性、元素账、
  │     形式电荷账、反应中心、步骤范围、条件、来源依赖等）
  │   → 不可变反应事件入账 → 输出前 5 名
  │
  └─④ 零 LLM 判分
        ppv1-criteria-v4（matched_product_hit，永久基线）
        ppv1-criteria-v5（role_bound_product_hit，要求命中为主产物角色）
        v1 / v2（历史口径，供对照）
```

主要模块：

| 路径 | 职责 |
|---|---|
| `src/pathway_v43/pollutant/s5b_builder.py` | 建池：三通道检索、融合、编译、去重 |
| `src/pathway_v43/pollutant/s5b_compiler.py`、`recorded_source.py` | 反应记录 / 模板 → 可执行原子编辑（含逆向映射推断） |
| `src/pathway_v43/pollutant/runflow.py`、`real_model.py`、`model_protocol.py` | 运行流程、模型请求组装、提案解析 |
| `src/pathway_v43/pollutant/audit.py`、`chemstate.py`、`events.py` | 审计检查、化学状态身份、事件存储 |
| `src/pathway_v43/pollutant/evaluation.py`、`s5b_scoring.py` | 零 LLM 判分（v1–v5） |
| `src/pathway_v43/pollutant/s5b_cli.py` | 命令行：build / run / score 等 |
| `vendor/v3_engine/` | vendored v3 反应检索引擎（运行时只读依赖，见 `PROVENANCE.json`） |
| `src/pathway_v43/vendor/molecode/` | vendored MoleCode（MIT） |

### 可选功能（默认全部关闭，效果**未确认**）

以下功能在代码中保留、可以通过参数开启，但在留出数据上**没有确认带来增益**，因此不是默认配置：

| 功能 | 说明 |
|---|---|
| product-first 核验反馈（B） | 模型先写产物，程序反推编译并把核验结果反馈给模型，最多 3 轮 |
| 先盲写再看池（C″） | 先不给候选池让模型盲写，再合并池候选，配合 product-first 反馈 |
| RetroRules 通道 | `--retro-channel`，需另行准备 RetroRules 数据 |
| 池参数档位 / 官能团检索 | `--pool-profile`、`--max-pool`、`--pool-threshold` 等 |

多步路径编排（LangGraph 工作流，`src/pathway_v43/workflow/`）的代码保留，但当前评测的是**单步模式**。

## 3. 数据资产（不随仓库分发）

代码运行需要以下数据，放在 `assets/` 下。代码按 `assets/MANIFEST.json` / `assets/MANIFEST.sha256` **逐文件校验哈希**，缺失或不一致就拒绝运行（fail-closed）。

| 目录 | 内容 | 来源 |
|---|---|---|
| `assets/v3_reactions/` | 反应语料（RHEA + enviPath/EAWAG-BBD 派生）、环境反应库、enviPath / EAWAG 规则、USPTO 模板 | 各上游数据库，按其许可获取 |
| `assets/analog/` | 类比模板索引（`corpus_templates_v1/v2`、`uspto_relaxed_index_v1`） | 由上述语料派生 |
| `assets/retrorules/raw/`（可选） | RetroRules 导出（`rhea.json`、`METANETX.json`、`USPTO.json`） | https://retrorules.org （数据 CC BY 4.0，上游各库条款另行核对），哈希见 `assets/retrorules/MANIFEST.sha256` |

已随仓库提供：`assets/MANIFEST.*`、`assets/functional_groups/rules.json`（本项目编写的官能团规则表）、`assets/retrorules/SOURCES.json`、`assets/retrorules/MANIFEST.sha256`。

上游数据的再分发许可尚未逐一核实，因此本仓库不包含这些数据。

## 4. 安装与运行

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"        # rdkit, lightgbm, numpy, langgraph, pytest

# 资产自检（数据就位后）
python -m pathway_v43 checkenv

# 单步评测流程（题卷需自备，格式见 src/pathway_v43/pollutant/s5b_builder.py:load_questions）
python -m pathway_v43.pollutant.s5b_cli build \
    --questions <questions.jsonl> --batch-root <batch_root> \
    --provider-kind real --pool-mode template --recorded-source
python -m pathway_v43.pollutant.s5b_cli run \
    --batch-root <batch_root> --runs-root <runs_root> --env-file <llm.env>
python -m pathway_v43.pollutant.s5b_cli score \
    --batch-root <batch_root> --runs-root <runs_root>
```

模型凭证只从环境变量或 env 文件读取：`V43_LLM_BASE_URL`、`V43_LLM_API_KEY`、`V43_LLM_MODEL`（OpenAI 兼容接口）。**不要把 env 文件提交进仓库。**

测试：

```bash
PYTHONPATH=src python -m pytest tests/ -q
```

部分集成测试依赖未随仓库分发的数据资产或外部对照代码；条件不满足时会自动跳过。

## 5. 方法纪律

见 `docs/architecture/BIBLE/`：零 LLM 判分、双口径并列、先预注册后发车、先探针后工程、止损门等。

## License

MIT（见 `LICENSE`）。第三方组件与数据保留各自的许可。
