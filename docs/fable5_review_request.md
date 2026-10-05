# 架构评审请求 — pathway v4.3（请以独立评审人身份作答）

你是一位独立的 LLM-agent 系统架构评审人，与系统作者无利益关系，直言不讳，不要客套。请用中文作答。

评审对象：本仓库（分支 `v4.3` @ `bf1ac38`），只做**静态评审**——读代码与文档，不运行任何命令（运行需要专有 conda env 与远端机凭证，你没有）。仓库只读，不要提出需要重跑已封存实验（如 298 外考 run-once 产物）的验证方案。

## 一、系统一句话与开发目标

**系统**：污染物（底物）生物降解路径预测 agent（`src/pathway_v43/`）。v3 冻结引擎/资产提供检索与候选，LangGraph 确定性主干编排，LLM 只在三个协议下介入：`rank_candidates`（既有候选间裁决）、`analogy_edit`（基于供体的受限 MoleCode 编辑）、`novel_proposal`（无证据时受约束新提案）。判分与评测全程确定性代码、零 LLM。

**开发目标**：构建可实现底物生物降解路径预测的 agent，当前目标线为单步 hit@1 ≥ 60%。Phase D 复测（已见 298 题、单次抽样）C0 为 136/182/186（45.6%/61.1%/62.4%），离目标还有距离；`reactant_similar_enabled` 发布默认保持 `false`（D1 通道未证增益，详见 §3）。

## 二、评审维度与问题

按以下六个方面逐一评价并给出建议。每个方面后附了必读文件（`文件:行号`为入口，其余顺藤摸瓜）。

### 1. 架构（分层、依赖方向、模块边界）

- `domain/`（纯函数策略，零框架依赖）/ `workflow/`（LangGraph 编排）/ `services/`（检索与预测组装）/ `storage/`（PathwayStore 账本 + ArtifactStore 不可变产物 + run_identity）/ `validation/`（确定性门禁）/ `adapters/`（LLM client + 限流闸门 + 资产）/ `output/`（裁决消费与导出）/ `batch.py`（批跑协调）——这个分层是否干净？有没有实际存在的反向依赖或层间泄漏？
- `REPO_DESIGN.md` 规定的依赖方向，代码是否遵守？`vendor/molecode` 随仓第三方命名空间的隔离是否充分？
- 为"多步路径预测"这个目标，当前架构缺什么、一 what's over-engineered？
- 必读：`REPO_DESIGN.md`、`ARCHITECTURE.md`、`src/pathway_v43/domain/policy.py`、`src/pathway_v43/storage/`、`src/pathway_v43/batch.py:run_batch,BatchCoordinator`

### 2. Prompt（协议提示词与组装）

- 三协议提示词 `configs/prompts/ranker.md`、`analogy_editor.md`、`novel_proposal.md` + MoleCode system prompt（`src/pathway_v43/vendor/molecode/prompts/`）：职责切分是否清晰？有无重叠、冲突或缺口（如温度未设、reasoning_effort=max 的含义）？
- 组装链 `services/prediction.py:137 build_prediction_task` → `:356 task_user_payload` → `workflow/nodes.py:616 _prompt_for` → `:444 call_model`（唯一出网点）：任务书里 discipline/预算/祖先链是否恰好够用、有无冗余或缺失字段？
- prompt 版本机制（`adapters/llm_client.py:119 prompt_versions` + 冻结进 `batch_identity`）是否足以支撑"改 prompt 即新实验"的可复现性？
- 必读：上述三份 `.md`、`src/pathway_v43/services/prediction.py:100-400`、`src/pathway_v43/workflow/nodes.py:362-500`

### 3. System design（并发、幂等、账本、身份）

- `BatchCoordinator`（40 worker、subprocess 派发、补位调度、持久闸门）+ `FileRateGate` + per-task 幂等 + checkpoint resume：并发与容错设计是否自洽？`run_identity` / `batch_identity` 的冻结粒度是否恰好（过多/过少）？
- PathwayStore + ArtifactStore 双存储：账本语义是否清晰？validation 门禁是否在正确的位置（进账本前）？
- 预算体系（depth/expansions/LLM calls/proposals + 费用账）是否真正约束了行为，还是只记账？
- 必读：`src/pathway_v43/batch.py:BatchCoordinator,worker_main,api_account`、`src/pathway_v43/adapters/rate_gate.py`、`src/pathway_v43/workflow/runner.py`、`src/pathway_v43/storage/run_identity.py`

### 4. Workflow（LangGraph 节点与路由策略）

- `workflow/graph.py`（START→normalize→select→retrieve→classify→预测分支→validate→adjudicate→commit 循环→export→END）与 `workflow/routing.py` 六个路由函数：状态机有无死角（想一个会卡住或静默丢弃的输入）？`mark_awaiting` / `mark_dead_end` 的合法停留是否完备？
- `domain/policy.py` 的证据分级与路由决策（`classify_evidence` / `decide_prediction_route` / `select_frontier`）：策略与提示词是否存在"两层决策打架"？
- D1 相似通道（`prediction_policy_overrides.reactant_similar_enabled`，见 `configs/phase_d_*.json`）：开关设计、阈值/top_k/donor 上限是否合理？结合 §3 的复测结论评价。
- 必读：`src/pathway_v43/workflow/graph.py`、`routing.py`、`nodes.py`、`src/pathway_v43/domain/policy.py`

### 5. Datachain（定义：检索证据 → 预测任务 → 模型响应 → 裁决 → 账本提交 → 导出的全程数据流转与字段契约）

> 注：仓库中没有名为 datachain 的模块，本条是你自定义的评审视角，按此定义评。
- 每个交接点的 schema 是否显式、有校验（`validate_card_for_reporting`、`validate_adjudication_payload`、answer 行三字段）？哪个交接点最可能丢信息或藏 bug？
- `report_adjudication.json` 的 `products[reportable]` → merged `predicted_products` → `export_v3` 投影：这条"来源链"是否端到端可审计？（刚修过来源读取口径，见 §3 v3）
- usage/费用/peak 等观测字段的采集口径是否一致（`transport` 结构）？
- 必读：`src/pathway_v43/services/report_adjudication.py`、`src/pathway_v43/output/export_v3.py`、`src/pathway_v43/output/pairing_gate.py`、`src/pathway_v43/adapters/llm_client.py:57-120`

### 6. Transfer（定义：跨步传递——父产物 SMILES 如何进入子步输入，ancestry/path_id 引用，去重与循环门禁）

> 注：同上，仓库无此命名模块，按此定义评。
- `ancestry` / `path_id` / `task_ref` 的引用完整性：能否从任意产物反查完整路径？断点续跑（resume）后引用是否不断裂？
- 去重门（兄弟范围 vs 全树）、循环检查、元素门禁（`validation/gates.py`）：跨步传递的护栏是否在正确的粒度上？有无"该拦没拦 / 不该拦拦了"（可参考 298 真空中"金标被查重门毙"的旧案，现已修为兄弟查重）？
- 必读：`src/pathway_v43/validation/gates.py`、`src/pathway_v43/workflow/state.py`、`src/pathway_v43/workflow/nodes.py:adjudicate/commit 相关段`

## 三、必须纳入论证的实测证据（不许忽视）

1. **Phase D 复测**（`docs/EC298_PHASE_D_RETEST_REPORT.md`）：已见 298 题、C0 136/182/186 vs D-3 132/174/182、配对 @5 四格 178/8/4/108；D1 通道效果 + 抽样噪声混合，3 题可归因损失（novel→analogy_edit 转路由后落空），8 题无召回差异纯噪声。结论措辞只能是"已见 298 题、冻结配置下观察到的差异"。
2. **刚修复的四项**（`docs/EC298_PHASE_D_RETEST_COMBINED_REVIEW.md`，已 resolved）：在途表 attempt 错标、调用算式 186×1+1×2 之误、"单调时间戳"术语错、并发先发后完与半开区间口径差。评审时不要把已修问题当新发现，但可以评价修复本身是否到位。
3. **失分归因**（`docs/EC298_HIT1_ATTRIBUTION_REPORT.md`、`docs/EC298_PD_RETEST_LOSS_ATTRIBUTION.md`）：162 失分题逐题归因 موجود，供判断"架构短板 vs 抽样噪声"。
4. **硬约束**：判分/评测零 LLM；298 题金标永不进运行侧（`exam_inputs.jsonl` 恰三字段）；单次抽样下 A/B 层效应与 C 层噪声不可定量分离；题卷与检索语料重叠未经审计。

## 四、阅读索引（按需取用）

- 总览：`ARCHITECTURE.md`、`REPO_DESIGN.md`、`docs/CORE_WORKFLOW_REPORT.md`、`docs/architecture_qa.md`
- 任务书体系：`docs/TASK_V43_CORE_WORKFLOW.md`（主干契约）、`docs/TASK_V43_PREDICTION_ATOMTOOL.md`（预测接线）、`docs/TASK_V43_EXPORT_DEV.md`（导出/dev）、`docs/TASK_V43_EC298.md`（外考口径）、`docs/TASK_V43_EC298_PHASE_{A,B,C,D}.md`（各阶段规则）
- 配置：`configs/dev_batch.json`、`configs/phase_d_C0.json`、`configs/phase_d_D3.json`、`configs/prompts/*.md`
- 测试：`tests/test_exam.py`（含并发半开区间边界测试）、全仓 456 passed（2026-09-29，conda env depending43）

## 五、纪律红线

1. 只读评审：不修改代码、不提交、不跑测试/发车；远端 Chenyu、凭证（`.env*`）、金标只读路径与你无关，一律不碰。
2. 引用精确到 `文件:行号`；涉及"实测数字"的断言必须能在 §3–§4 所列文档中找到依据，找不到就写"未见证据"而不是编造。
3. 不要复述文档原文凑篇幅；每条建议必须落到具体文件/函数/字段。
