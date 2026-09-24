# v4.3 第一阶段实现任务书：路径账本、ReactionFinder 与 LangGraph 主干

> 交给独立执行模型实现；本会话只负责 review。日期：2026-09-24。目标仓：`/Volumes/CC/Enzyme_Agent/dependingv43/`。

## 0. 起点与边界

先阅读本仓 `ARCHITECTURE.md`、`REPO_DESIGN.md`、`ASSETS.md`、`TASK_ASSET_WIRING.md`、`docs/ASSET_WIRING_REPORT.md`，再检查现有 `src/pathway_v43/`。上一轮资产接线已经通过二轮 review：37/37 测试、21/21 文件校验、7/7 夹具中 778 个候选零差异。以现有 `V43Engine.predict/expand_raw/asset_identity` 和类比索引装载器为基座；不得重写或破坏已验收的资产接线。

本任务交付 **能够真实运行、持久化和恢复的确定性 v4.3 主干**：从一个底物出发，ReactionFinder 从本仓资产给出分级证据；LangGraph 选择当前路径、检索、分类、校验、提交确定可接受的已记录反应，并选择性继续展开。遇到多条竞争已知反应、仅规则/类比证据或无证据时，明确保存待预测/死端状态。后续 PredictionAgent、AtomTool 编辑和 LLM 调用另开任务，不在本轮伪实现。

不得把 LangGraph 的执行 State 当作化学路径图，也不得用原始引擎 score 当成概率或“已知反应”判据。

## 1. 要交付的接口与数据契约

推荐沿 `REPO_DESIGN.md` 落下列模块；可合并小文件，但接口职责与持久产物不变：

| 层 | 最少交付 |
|---|---|
| `domain/` | 版本化的 Compound、ReactionEvent、PathInstance、Evidence、Candidate/Decision 契约；规范分子身份和稳定 ID；证据分类与选择策略 |
| `storage/` | SQLite PathwayStore、不可变 JSON ArtifactStore、run identity；两个存储与 LangGraph checkpoint 各自职责清晰 |
| `services/reaction_finder.py` | 可注入的 ReactionFinder 接口及基于本仓资产/现有 V43Engine 的真实实现 |
| `validation/` | SMILES 可解析/价态、同一步去重、路径内循环、方向/来源、深度与预算等确定性门禁；不声称已证明反应机理或原子守恒 |
| `workflow/` | 小型 TypedDict State、StateGraph 节点与条件路由、SQLite checkpointer、run/resume 入口 |
| `output/` | 能检查路径、反应事件、证据/拒因和 stop_reason 的 JSON 报告；本轮不要求 v3 评测格式导出 |
| CLI | `run --smiles ...`、`resume --run-id ...`、`inspect --run-id ...`，保留原 `checkenv` 与 `probe` |

使用 Python 3.11 环境；在 `pyproject.toml` 声明 LangGraph 与 SQLite checkpoint 依赖，实际安装和版本记录在报告中。官方 API 参考：[StateGraph](https://docs.langchain.com/oss/python/langgraph/graph-api)、[持久化](https://docs.langchain.com/oss/python/langgraph/persistence)、[SQLite saver](https://reference.langchain.com/python/langgraph.checkpoint.sqlite/SqliteSaver/from_conn_string)。代码要按实际安装版本验证，不从文档示意代码直接假设方法签名。

### 1.1 化学路径图

- 化学事实表示为 `分子 → 反应事件 → 有序产物集合`。一个已记录反应的多个产物属于同一个 ReactionEvent，不能拆成几条互不相关的“单产物实测反应”。同一分子经两条路线到达时可共享 Compound 身份，但必须保留两个 PathInstance、各自父路径、入边、证据和状态。
- `path_id`、`event_id` 为稳定内部 ID；`S11`、`S211` 只是由路径计算的展示名。禁止解析展示名来查父子关系。祖先链 API 应能按顺序返回原底物、每一步父分子、反应和证据，供后续 PredictionAgent 构造完整任务书。
- PathwayStore 至少保存 `run_id`、root、compounds、reaction_events、event_products、path_instances、frontier 状态、graph_revision。对同一幂等键重复提交应返回已提交结果；若同键内容变化则报冲突。提交事件、产物和路径须在同一 SQLite 事务内完成。
- 路径内循环不再进入 frontier；不同路线汇合不是循环。已到深度上限、暂缓探索、待预测、死端、拒绝、已展开等状态分清。不得通过删除候选来隐瞒它们。

### 1.2 ReactionFinder 证据

输入至少包含当前 SMILES/规范身份、run_id、path_id、按顺序的祖先路径、环境条件（可空）。输出为版本化 JSON，至少包含 `evidence_id`、`source_id`、`kind`（`recorded_reaction` / `rule_application` / `analog_reaction`）、`query_identity`、`match_type`、反应物与有序产物、原子映射是否可用、`condition_fit`（compatible / unknown / conflict）、`retrieval_rank`、`score` 与 `score_semantics`、来源记录、文件相对路径与 SHA256、整个检索资产身份。

- `recorded_reaction` 只授予能够证明**同一规范底物、正确方向、可追溯反应记录**的命中。原版 `eawag_lookup` 可作来源，但需核实具体 reaction ID 与反应物匹配口径。规则模板命中、检索邻居、Tanimoto 高分、`source` 字符串中包含 `envipath`，都不自动升格为已记录反应。
- 同一个反应 ID 的多个产物合成一个 reaction evidence/event；不同反应 ID 仍是竞争反应。保留引擎原始候选顺序和来源字段，避免跨来源分数直接比较成概率。条件缺失标 `unknown`，不要猜测环境相容。
- 已验收的 `assets/MANIFEST.sha256` 仍是读取前的硬门槛。results 记录使用的资产清单 SHA、具体文件 SHA 和代码身份。若原索引未提供某种原子映射/条件，明确写 `unavailable`，不生成假的映射。
- 真实 ReactionFinder 最少在既有非 eval 夹具上产出可解释证据卡；另外用合成夹具覆盖无法由真实数据稳定触发的分支。真实引擎预加载/资产身份限制继续遵守上一轮适配器契约。

### 1.3 LangGraph State 与路由

State 尽量只含 `run_id`、root/active path ID、`graph_revision`、retrieval/decision/validation 的稳定引用、预算快照、phase、stop_reason 和 frontier 引用；完整候选池、证据与路径实例留在持久存储。单进程单 active path 顺序执行。

期望流程：

```text
START → normalize_input → select_frontier → retrieve_reactions
      → classify_evidence
          ├─ 唯一可接受的已记录反应 → validate_products → commit_pathway
          ├─ 多条竞争已知反应或仅规则/类比 → mark_awaiting_prediction
          └─ 无有效证据 → mark_dead_end
      → select_frontier（有预算与待探索路径时）
      → export_results → END
```

`classify_evidence` 的选择规则放在可测试的纯函数策略层。初始策略只自动接受“单一、同底物、方向正确、没有已知条件冲突”的 recorded reaction；多个可信反应不因引擎分数最高就自动淘汰其余。一个反应的多个产物全部入图并保留原始顺序；报告 top-5 与 frontier 展开数分离。首版默认只继续展开最前面的有限路径，其他合法候选标记暂缓，预算和宽度写入 run identity。仅规则或类比候选先持久化并转 `awaiting_prediction`，不谎称已完成预测。

## 2. 持久化、幂等与恢复

- 运行目录遵循 `REPO_DESIGN.md`：`checkpoint.sqlite`、`pathway.sqlite`、`results/<task_id>/*.json`、`run_identity.json`、`report/pathway.json`。`task_id` 由 run_id、path_id、phase、规范输入、资产/策略版本决定；同任务重试先读已有产物，不重复检索或覆盖不一致内容。写 JSON 应先完整写临时文件再原子提交，遇同名不同内容必须报冲突。
- LangGraph SQLite checkpointer 使用 `thread_id=run_id`。启动 `run` 时持久记录根分子、路径策略、代码/资产身份；`resume` 必须核对这些身份与 DB graph_revision，不可在资产或策略变更后静默继续旧 run。
- checkpoint 与路径账本不是同一事务。测试必须实际在**检索落盘后**和**路径事件提交后、下个 checkpoint 前/附近**中断进程或图执行，再在新进程/新连接恢复；结果中的事件、路径、候选 JSON 和预算计数不得重复。`invoke(None, config)` 等恢复语义按安装版 LangGraph 实测。
- 任何运行失败输出结构化原因；无模型时遇到待预测应以明确 `awaiting_prediction` 结束当前确定性阶段，不要返回“完整路径预测成功”。`inspect` 能区分完成、预算耗尽、待预测和异常停止。

## 3. 验收用例与运行命令

必须有可重复测试覆盖：

1. 一个已记录反应含多个有序产物：同一事件入图、最多五个可报告、只按配置展开选中路径。
2. 同一分子经不同路线汇合：两个 PathInstance、一个 Compound，路径历史各自完整；路径内返回祖先则标 cycle。
3. 两条已记录反应竞争、条件冲突、只有规则、只有类比、无证据：正确证据级别与 `awaiting_prediction`/dead_end，不能把规则/类比当实测。
4. 无效 SMILES、重复兄弟候选、原子映射缺失、预算耗尽、深度上限：有明确拒因/状态，已写事实保持一致。
5. 重复提交与 SQLite checkpoint 恢复：事件/路径/检索调用不重复；同键不同内容报错。
6. 真实引擎 integration：读取路径仍在本仓 assets，记录实际来源类别与资产身份；原资产接线 37 项测试继续通过，清单仍 21/21 OK。

至少提供等价命令并在 README 写明输出：

```sh
python -m pathway_v43 run --smiles 'Oc1ccccc1O' --run-id v43-smoke --max-depth 2 --max-expansions 3
python -m pathway_v43 inspect --run-id v43-smoke
python -m pathway_v43 resume --run-id v43-smoke
python -m pytest tests/ -v
( cd assets && shasum -a 256 -c MANIFEST.sha256 )
```

若真实烟测底物有多条 recorded reaction，`run` 停在 `awaiting_prediction` 是本阶段合格结果；另用固定合成夹具证明唯一 recorded reaction 的提交与第二步路径历史。

## 4. 本轮不做的工作

不接外部 LLM，不实现 PredictionAgent 的精排/类比编辑/新提案，不复制 v4 的洪水建图主循环，不运行冻结 eval 或 298 外考，不调反应评分/规则库，不修改 dependingv3、dependingv4 及已验收 assets。可复用旧源码时注明来源与许可；优先写小适配器，不把旧系统全量搬入。

## 5. 交给 reviewer 的材料

在 `docs/CORE_WORKFLOW_REPORT.md` 写明实现文件、schema 版本、依赖版本、真实与合成夹具、每条路由的实际结果、恢复前后 DB 计数、资产身份、完整命令与测试输出、已知限制。提供一个可直接查看的 `runs/<run_id>/report/pathway.json` 示例；不要放凭证或评测答案。

review 硬门槛：旧资产接线不回归；真实证据分级可靠；同一反应多产物与不同路径汇合正确；State 与路径图分离；幂等恢复无重复；无模型时明确停在待预测；每个结论有测试或运行产物可复核。通过后才开始 PredictionAgent/AtomTool 的下一阶段任务。
