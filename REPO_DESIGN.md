# dependingv43 仓库设计

> 状态：2026-09-24 设计稿。本文定义 v4.3 独立仓库的代码归属、依赖方向、运行产物和迁移顺序。系统行为及数据语义见 [ARCHITECTURE.md](ARCHITECTURE.md)。

## 1. 仓库角色

dependingv43 是采用 LangGraph 的新工作流仓，拥有 v4.3 的状态模型、反应规则与库资产、检索和预测任务协议、路径图、选择性展开策略、配置、测试和运行产物。它通过适配器只读调用 dependingv3 的冻结引擎代码与评测器。dependingv4 的 feat/v42-fix 是对照基线和可复用实现来源；迁入代码需在 v4.3 中独立测试并记录来源，不把旧洪水调度直接搬来。

仓库采用 Python 3.11 及以上版本，包名建议为 pathway_v43，命令名建议为 pathway-agent-v43，以免与 v4 的 pathway_agent 混淆。LangGraph StateGraph 是唯一的工作流编排层；模型提供者由独立适配器接入。反应规则、反应库和最终类比索引落在本仓 assets/ 并校验哈希；模型权重可由配置引用外部路径。

## 2. 目标目录

    dependingv43/
    ├── ARCHITECTURE.md
    ├── REPO_DESIGN.md
    ├── README.md
    ├── pyproject.toml
    ├── .env.example
    ├── .gitignore
    ├── ASSETS.md
    ├── assets/
    │   ├── MANIFEST.sha256
    │   ├── MANIFEST.json
    │   ├── v3_reactions/          # v3 来源规则、反应库及引擎运行依赖
    │   └── analog/                # v4 来源最终类比索引
    ├── configs/
    │   ├── default.yaml
    │   ├── evidence_policy.yaml
    │   └── prompts/
    │       ├── ranker.md
    │       ├── analogy_editor.md
    │       └── novel_proposal.md
    ├── src/pathway_v43/
    │   ├── __init__.py
    │   ├── main.py
    │   ├── config.py
    │   ├── workflow/
    │   │   ├── state.py
    │   │   ├── graph.py
    │   │   ├── nodes.py
    │   │   └── routing.py
    │   ├── domain/
    │   │   ├── identity.py
    │   │   ├── models.py
    │   │   ├── pathway.py
    │   │   └── policy.py
    │   ├── services/
    │   │   ├── reaction_finder.py
    │   │   ├── prediction.py
    │   │   └── atom_tool.py
    │   ├── adapters/
    │   │   ├── v3_engine.py
    │   │   ├── eawag_lookup.py
    │   │   ├── analog_index.py
    │   │   ├── llm_client.py
    │   │   └── mpnn.py
    │   ├── validation/
    │   │   ├── gates.py
    │   │   └── atom_mapping.py
    │   ├── storage/
    │   │   ├── pathway_store.py
    │   │   ├── artifact_store.py
    │   │   └── run_identity.py
    │   └── output/
    │       ├── export_v3.py
    │       └── report.py
    ├── tests/
    │   ├── unit/
    │   ├── contract/
    │   ├── workflow/
    │   └── integration/
    ├── scripts/
    │   ├── inspect_run.py
    │   └── score_dev.py
    └── runs/                         # gitignored

此树是模块边界和命名约定；实现时可以合并过小的模块，但跨层调用方向保持下节规则。

## 3. 依赖方向

    main / CLI
       ↓
    workflow (LangGraph StateGraph、路由、检查点)
       ↓
    services (检索、预测、AtomTool)
       ↓
    domain + validation + storage + adapters
       ↓
    v4.3 assets / v3 冻结引擎代码 / LLM API

- domain 保存纯数据模型与选择策略，不导入 LangGraph、模型框架或 CLI。
- workflow 只编排步骤和处理 State 引用；化学判定留在 domain、services 和 validation。
- 只有 adapters/v3_engine.py 等 v3 适配器导入冻结 v3 代码；只读桥接必须在资产 SHA 校验通过后启用。
- ReactionFinder 只消费经 manifest 校验的本仓 assets/。若旧引擎适配器暂时仍消费 v3 原资产，run_identity 分别记录两套资产根及哈希，完成同输入对拍后再切到本仓资产。
- 只有 adapters/llm_client.py 发出外部模型请求；PredictionAgent 不直接处理密钥或网络重试。
- 模型提案都经过 validation 后才由 storage/pathway_store.py 提交；评测与导出不调用模型。
- 配置、提示词、索引和代码版本全部写入 run_identity。密钥只经环境变量注入，不落仓库或日志。

## 4. 各层接口与代码归属

| 模块 | 输入 → 输出 | 主要责任 |
|---|---|---|
| workflow/state.py | 小型 TypedDict State | 保存当前任务 ID、路径 ID、产物引用、预算、阶段与图版本 |
| workflow/graph.py | StateGraph 构建器 | 注册节点和条件路由，配置持久化 checkpointer |
| workflow/nodes.py | State → State 更新 | 调用服务、读写产物、保证节点幂等 |
| domain/models.py | 结构化记录 | Compound、ReactionEvent、PathInstance、Evidence、Candidate、Decision |
| domain/pathway.py | 图操作 | 路径实例、入边、同分子汇合、路径内循环与终点状态 |
| domain/policy.py | 图与证据 → 下一路径 | 证据优先级、候选排序、暂缓、展开、回溯及预算 |
| services/reaction_finder.py | 当前节点 + 路径上下文 → 检索 JSON | 已记录反应、规则、类比证据的统一入口 |
| services/prediction.py | 任务书 + 证据 → 候选 JSON | 精排、类比编辑、无证据提案三种明确任务协议 |
| services/atom_tool.py | SMILES/映射/MoleCode → 结构 | 往返转换和结构编辑接口 |
| validation/ | 候选 + 父路径 → 接受或拒因 | 结构、映射、元素变化、来源、去重、预算 |
| storage/ | 稳定 ID → 持久产物 | 化学路径图、不可变 results JSON、运行身份 |
| output/ | 已提交图 → 评测行/报告 | 按 v3 契约导出及审计可视化 |

类型契约以明确 schema_version 标记。ReactionFinder 的结果、PredictionAgent 的任务与结果、校验结果分别持久化；任何一个阶段只引用前一阶段产物的稳定 ID，避免把一整段长对话当作系统状态。

## 5. 运行产物与恢复

    runs/<run_id>/
    ├── checkpoint.sqlite           # LangGraph 本地持久检查点
    ├── pathway.sqlite              # 分子、反应事件、路径实例、frontier
    ├── results/
    │   └── <task_id>/
    │       ├── retrieval.json
    │       ├── prediction.json      # 未调用模型时可无此文件
    │       └── validation.json
    ├── events.jsonl                 # 选择、拒绝、回溯、预算变动
    ├── predictions.jsonl           # v3 基准导出契约
    ├── run_identity.json
    └── report/
        ├── summary.md
        └── pathway.json

task_id 由 run_id、path_id、当前分子、阶段和输入版本确定。results JSON 一经写入不覆盖不同版本；同键重试返回原产物。PathwayStore 对重复提交执行幂等检查。LangGraph 恢复点与 pathway.sqlite 的提交不是同一个事务，因此节点重跑是正常情况，所有外部调用和写入均须处理重放。运行目录可备份、复制和只读复核；不放 API key 或 SSH 凭证。

初版在单机使用持久 SQLite checkpointer 和顺序处理。若以后需要多进程共享，再迁移到支持并发的持久后端，并明确 State reducer、冲突解决及 frontier 归并顺序。InMemorySaver 只用于单测，不能承担断点续跑。

## 6. 从旧系统复用什么

| 旧来源 | v4.3 用法 | 迁入前验证 |
|---|---|---|
| v3 反应规则、EAWAG 库、环境检索语料、USPTO 模板 | 原样迁入 assets/，保留来源清单 | 源与目标逐文件 SHA256 对拍、记录授权/来源 |
| v4 最终类比索引 | 原样迁入 assets/analog/ | 原始 manifest、索引行数及 SHA256 对拍 |
| v3 冻结引擎代码、EAWAG lookup 逻辑、评测器 | 只读适配调用 | 资产 SHA、同输入候选顺序、评测契约对拍 |
| v4 engine.py、identity 函数 | 提炼 v3 桥与规范身份 | 分子身份与 v3 引擎、评测器一致 |
| v4 gates.py、terminals.py | 移植确定性护栏和终点规则 | 按新 ReactionEvent/PathInstance 语义重测 |
| v4 molecode_render.py、vendor/molecode | AtomTool 的表示转换基础 | SMILES ↔ MoleCode 往返、映射保存、许可与来源 |
| v4 analog.py、rules.py、annotate.py | ReactionFinder 的类比、规则与证据卡实现 | 检索来源、索引 SHA、条件标签和结果重放 |
| v4 mpnn.py | 可选、带未验收状态的证据列 | 域迁移诊断结论与降权标记保留 |
| v4 export.py、report.py | 输出格式与报告素材 | v3 evaluator CLI 能读取 v4.3 答卷 |
| v4 config.py、run_identity | 配置和追溯规则参考 | 新提示词、LangGraph 版本和图策略入身份块 |

v4 hybrid.py 的“洪水建图 → 全图精排 → 空位写入”不作为新主流程；它留作对照实现。v4 orchestrator.py 的预算、审计、带因重试经验迁入新节点与策略。v4 CrewBrain 可以作为行为对拍参考；v4.3 的主工作流直接由 LangGraph 管理，模型调用通过独立适配器完成。

任何复制到本仓的第三方源码连同 LICENSE、来源和哈希记录。反应数据及最终检索索引已在 assets/ 下保留字节一致的 v4.3 副本：[ASSETS.md](ASSETS.md) 和 manifest 记录 21 个来源文件（149,475,454 字节）的来源、大小与 SHA256；构建中间件、评测隔离语料和运行产物不混入默认检索资产。将来初始化 Git 时，大文件的纳管方式按规模与数据许可选择普通 Git、LFS 或独立发行包。

## 7. 配置与命令

配置拆成三类：工作预算与分支策略；证据等级及适用性规则；模型任务设置。精排和编辑各有提示词及独立的模型参数字段，实际取值在 dev 实验后冻结。默认配置的每项都应可写入 run_identity；eval 不从环境变量临时改变策略。

建议 CLI：

    pathway-agent-v43 checkenv
    pathway-agent-v43 run --smiles <SMILES> --config configs/default.yaml
    pathway-agent-v43 batch --split dev --config configs/default.yaml
    pathway-agent-v43 resume --run-id <RUN_ID>
    pathway-agent-v43 export --run-id <RUN_ID>
    pathway-agent-v43 inspect --run-id <RUN_ID>

batch 按路径/题号使用稳定身份，遇到已完成项跳过；resume 读取 LangGraph 检查点和领域图版本后继续。checkenv 核验本仓 assets manifest、仍需桥接的 v3 引擎资产、MoleCode、持久化后端与模型配置，并明确报告可用或降级状态。

## 8. 实施顺序与验收

1. **契约和夹具**：落 Compound、ReactionEvent、PathInstance、Evidence、Candidate、WorkflowState 的 schema；用少量合成反应覆盖多产物、汇合、循环、条件冲突。
2. **确定性骨架**：PathwayStore、证据等级、frontier 策略、LangGraph 路由和 SQLite 检查点；先用假 ReactionFinder、假 PredictionAgent 跑通选择性展开及恢复。
3. **检索接线**：本仓 assets/ 作为 ReactionFinder 的反应规则与库来源，v3 引擎和 EAWAG lookup 逻辑只读适配；输出 results JSON，精确记录与规则应用分级。
4. **预测接线**：接入精排、类比编辑、AtomTool 和确定性护栏；模型超时、解析失败及重试留痕。
5. **导出与对照**：完成 v3 评测契约、dev 单步/多步对照和成本统计；再冻结策略与提示词，用独立题集检验泛化。

仓库级验收包括：纯函数测试不需要模型服务；checkpoint 恢复后路径图与产物无重复；同一分子不同来路均保留；exact 多产物与条件冲突处理可追溯；每步 top-5 输出与 frontier 展开数独立；v3 评测器成功读取导出；无模型配置时已知反应与规则通路仍可运行并如实报告降级。

## 9. 外部技术依据

- LangGraph 官方：[Graph API](https://docs.langchain.com/oss/python/langgraph/graph-api)（State、Node、条件边、Send、Command、重执行语义）
- LangGraph 官方：[Persistence](https://docs.langchain.com/oss/python/langgraph/persistence)（持久 checkpointer）
- 本仓行为设计：ARCHITECTURE.md
