> **HISTORICAL / NON-AUTHORITATIVE**
> This document is retained for decision history only.
> Current implementation authority:
> - plan/final_design.md
> - plan/final_plan.md
> - plan/final_discussion.md


# UNIFIED PLAN — 反应类比推理 Agent · 实施计划（demov2 三方案融合权威版）

> 日期：2026-07-29
> 配套设计：`UNIFIED_DESIGN_REACTION_ANALOGY_AGENT_2026-07-29.md`
> 工作根目录：`CC/branch/ReactionAgent/demov2/`
> 运行约定：脚本从 `benchmark/` 跑时 `PYTHONPATH=../../core`；数据根 `ENZYMECAGE_DATA_ROOT` 默认 `/Volumes/CC/Enzyme_Agent/depending/data`。
> 工程纪律（取 ChatGPT）：**测试先行；数据不过测不写 MCP/LLM；每阶段独立可验收、可回退；每步 typed 失败（不 silent `[]`）**。

---

## 0. 总原则

- **地基先行**：Fragment Lineage / Reaction Ledger / 版本化快照必须先立，否则上面盖什么都白搭。
- **两次廉价验证机会**：Phase 0.5 手动 go/no-go（方向对不对）+ Phase 1 单步垂直切片（闭环通不通）。
- **单步立正确性，多步后承接**；**strict 先行，generalized/外部证据/research mode 后置**。
- **不先承诺 top-1 百分比**：先证地基可信（DESIGN §10），再据新 benchmark 设目标。

冻结项（本轮沿用不推倒）：DRFP 打分器（降级为弱排序特征）、`splits.py` 三划分防泄漏、`honest_eval` 四类防作弊口径（但其数字在地基过测前为 provisional）。

---

## 1. 目录结构（新建于 demov2/）

```
demov2/
├── plan/                          # 设计与计划（本文件 + UNIFIED_DESIGN 为权威）
├── data_foundation/               # Phase 0 数据地基
│   ├── lineage.py                 # bipartite fragment-lineage graph（替代旧 transformed_pair）
│   ├── ledger.py                  # reaction ledger 抽取 + 守恒校验
│   ├── snapshot.py                # 版本化快照 + content hash + quarantine
│   └── audit_protocol.md          # 分层人工审计规范
├── tools/                         # MCP 工具封装层（包装 core/ 资产）
│   ├── retrieve.py                # evidence.search_structured（adaptive donor）
│   ├── analyze.py                 # analyze_structure / analyze_diff（基于 lineage）
│   ├── details.py                 # reaction.get_details（含 ledger）
│   ├── apply_edit.py              # reaction.apply_edit（RDKit 确定性生成 Y）
│   ├── validate.py                # chem.validate（合法性 + ledger 守恒）
│   ├── score.py                   # score_candidate（DRFP 弱特征）
│   └── enzyme.py                  # enzyme.get_provenance
├── reasoner/                      # LLM 推理核心
│   ├── prompts/                   # 各阶段 prompt 模板
│   ├── hypothesis.py              # typed hypothesis 契约 + 确定性 compiler/validator
│   ├── stages.py                  # 六跳阶段 + 拒答闸
│   └── engine.py                  # 编排：推理链 + 工具调用循环 + trace
├── schemas.py                     # 输出契约 + PredictionResult 不变式（Pydantic v2 StrictModel）
├── run_predict.py                 # 单 X 预测入口
└── eval/
    ├── benchmark_rebuild.py       # 重建 honest_eval（多答案真值 + train-only + 六层）
    └── run_eval.py                # 三划分 + selective/abstention + 基线对拍
```

---

## 2. Phase 0 · 数据地基（最高优先级）

**目标**：修复 A/B 配对、建立反应账本与版本化快照。**在过测前所有旧 benchmark 数字标 provisional。**

### 任务
- [ ] **P0-T0 验证 lineage bug 发生率**（先做，决定阻塞程度）
  - 实跑现有 `canonical_identity.transformed_pair`，统计 A/B 错配案例数与占比；含 2-氧戊二酸/羟脯氨酸回归案例。
  - 输出发生率报告 → 普遍则全修（走 P0 全量）；边缘则并行修不全停。
- [ ] **P0-T1 fragment-lineage graph**（`data_foundation/lineage.py`）
  - bipartite mapped-overlap graph 替代"各自挑最大片段 + `max()`"；tie/ambiguity 显式报错入 quarantine。
  - 一个反应可产出多条 transformed participant lineage。
  - 回归测试：2-氧戊二酸案例、multi-reactant、multi-product、redox、transferase、cleavage、MCS fallback。
- [ ] **P0-T2 reaction ledger**（`data_foundation/ledger.py`）
  - participant roles / stoichiometry / atom transfer source / element·charge balance / H·proton·electron policy / mapping coverage。
  - 三档账本状态；守恒基于完整账本而非 X/Y 分子式差。
- [ ] **P0-T3 版本化快照 + quarantine**（`data_foundation/snapshot.py`）
  - content hash、可重放；问题记录进 quarantine 附 reason，不静默丢弃。
- [ ] **P0-T4 train-only 证据隔离**：按 fold 建独立证据视图，杜绝 test evidence 泄漏。
- [ ] **P0-T5 分层人工审计**（`audit_protocol.md`）：分层抽样、样本量、审计者一致性、catastrophic mismatch 阈值。

### 验收
- catastrophic A/B mismatch 不进生产索引；unresolved lineage 有明确 quarantine reason；atom mapping 与 snapshot 可重放；已知错误案例全部修复或隔离。

---

## 3. Phase 0.5 · 手动 go/no-go（取 Qwen，非 oracle 版）

**目标**：数据修好后，用最低成本验证"LLM 到底会不会做这种化学类比"。

### 任务
- [ ] **P0.5-T1** 预注册 20 个测试 X（含 invalid / ambiguous / OOD / 应拒答案例）。
- [ ] **P0.5-T2** donor **自动从 train-only 快照检索**（**禁止人工按真值挑 support**）。
- [ ] **P0.5-T3** 人肉喂 LLM 走六跳推理链（判 T / 定 S / 描述编辑），记录 retrieval/lineage/transform/site miss。
- [ ] **P0.5-T4** go/no-go 判据：LLM 对可类比案例的 T/S 判定正确率达标 → 继续；否则调整方向或 prompt。

### 验收
- 明确 go/no-go 结论文档；miss 归因到具体阶段。（保留 oracle upper-bound 仅作参照，不作生产验收。）

---

## 4. Phase 1 · strict 单步垂直切片（融合核心）

**目标**：`X → 自动 donor 检索 → 完整 A→B → LLM 判 T+S → 确定性生成 Y → ledger 校验 → ranked/abstain`，端到端非 oracle 跑通。

### 任务
- [ ] **P1-T1 工具封装（最小集）**：`retrieve` / `analyze_diff`(lineage) / `apply_edit`(RDKit 生成) / `validate`(ledger 守恒) / `score`。统一无状态函数式接口 + JSON schema。
- [ ] **P1-T2 typed hypothesis 契约**（`reasoner/hypothesis.py`）：LLM 输出 `{support_reaction_ids, transformation_type, target_site, relaxed_constraints, rationale}`；确定性 compiler 校验→只有通过者拿 `candidate_id`。
- [ ] **P1-T3 输出契约**（`schemas.py`）：Pydantic v2 StrictModel(extra="forbid")；PredictionResult 跨字段不变式（DESIGN §6）。
- [ ] **P1-T4 推理引擎**（`reasoner/engine.py`）：单步链路 ①→④→⑥；LLM 描述编辑意图，工具执行生成；每跳存 typed trace + hash。LLM 后端沿用 `call_dashscope`（kimi）。工具先走进程内 function-calling。
- [ ] **P1-T5 strict / generalized 分层**：strict 来自可信 atom mapping 精确回放；generalized 显式记录放宽项、独立标记 exploratory、不跨 lane 比 raw score（本 Phase 只需跑通 strict，generalized 占位后置）。
- [ ] **P1-T6 入口**（`run_predict.py`）：单 X → ranked top-K（每个带 donor/T/S/Δ/ledger/evidence）或 typed abstain。
- [ ] **P1-T7 冒烟**：预注册案例端到端 + 等价 SMILES 一致性 + 应拒答案例触发闸。

### 验收
- 等价 SMILES 输入不改变 canonical candidate set；每个 candidate 有 donor/transform/site/ledger/evidence；新增重原子有来源或明确 unknown；**LLM 不写 SMILES**（结构由内核生成）；infrastructure failure 不冒充 abstention。

---

## 5. Phase 2 · benchmark 重建 + 诚实评估

**目标**：先重建可信尺子，再报数字。

### 任务
- [ ] **P2-T1 多答案真值**（`eval/benchmark_rebuild.py`）：允许 Y 集合 + 等价（tautomer/盐/中性）+ stereo-sensitive/agnostic 两套指标。
- [ ] **P2-T2 fold-specific 证据 + train-only 检索/排名参照**。
- [ ] **P2-T3 六层指标**：data / retrieval / transform·site / generation / ranking·abstention / Agent。
- [ ] **P2-T4 划分**：exact-X / scaffold / transform-family / source / time。
- [ ] **P2-T5 selective / risk–coverage / abstention**：全 X 进分母；每指标带 N + 置信区间。
- [ ] **P2-T6 基线对拍**：旧 Morgan+模板+DRFP 管线同数据同划分重跑；strict/generalized 分报。

### 验收
- test evidence leakage 为零；split 前过滤数量进报告；strict/generalized 分报；无未修复数字作承诺。

---

## 6. Phase 3–5 · 后置能力

### Phase 3 · MCP + grounding guard
- [ ] 四个生产高层工具（`predict` / `get_run` / `get_candidate_evidence` / `expand_external_evidence`，外部证据移出 MVP）。
- [ ] strict JSON schema、稳定 IDs/resource URI、idempotency key + request hash run 复用、typed errors、正确 read-only/write/external-I/O 标注。
- [ ] grounding guard：拒绝未知 candidate/evidence ID；prompt-injection 测试；token/tool/time budget；no-invention benchmark（Agent invented = 0）。

### Phase 4 · generalized exploratory lane
- [ ] 明确可放宽约束列表 + generalization distance；generalized-only ranking；与 strict 完全分报；OOD gate。

### Phase 5 · 多步降解路径（取 Qwen 循环骨架）
- [ ] 候选图：canonical molecule node 去重 + candidate reaction edge + branch/beam + cycle detection + depth/cost/risk budget + 逐边 provenance + 路径级不确定性传播。**非线性递归。**

---

## 7. 待用户拍板（不阻塞 Phase 0-T0）

1. **地基阻塞程度**：先跑 P0-T0 验证发生率再定停多久（建议），还是直接全量修地基？
2. **research hypothesis mode** 是否本轮纳入？（建议后置到 Phase 3 之后）
3. **LLM 后端**：固定 kimi 还是可切换？（建议沿用 `call_dashscope` 网关）
4. **MCP 形态**：先进程内 function-calling（建议），Phase 3 再抽跨进程 server？
5. **文档处置**：以本 UNIFIED design+plan 为唯一权威，三份原始 design/plan/discussion 降级为过程参考？

---

## 8. 复用清单（现成积木，勿重写）

| 能力 | 现有位置 | 用途 | 本轮处置 |
|---|---|---|---|
| Morgan 底物检索 | `core/chenyu_features.retrieve_by_substrate` | retrieve 工具 | 沿用，升级 adaptive donor |
| 真值/MCS 反应中心 | `core/chenyu_features.reaction_center_from_chenyu`、`core/pipeline.extract_reaction_center` | site 佐证 | 沿用（条件化） |
| DRFP-酶集打分 | `core/reaction_scorer.score_candidates` | score 工具 | **降级为弱排序特征** |
| 变换签名 | `benchmark/edit_script.extract_edit + key()` | T 一致性校验 | 沿用（粗分桶键，非 canonical） |
| 辅酶剥离/反应中心锚定 | `benchmark/canonical_identity.transformed_pair` | A/B 配对 | **重写为 fragment-lineage graph** |
| 三划分防泄漏 | `benchmark/splits.make_split` | 评估划分 | 沿用 + train-only 隔离 |
| 诚实漏斗主评估 | `benchmark/honest_eval.py` | eval 接入 | **重建**（多答案+六层），旧数字 provisional |
| 模板迁移/对齐 | `core/pipeline.apply_template_to_molecule`、`align_transfer` | apply_edit 生成 | 沿用 |
| LLM 调用入口 | `src/utils/llm.call_dashscope`（kimi 网关） | 推理核心后端 | 沿用 |

---

## 9. 风险与对策

| 风险 | 对策 |
|---|---|
| lineage bug 波及面大、修复重 | 先 P0-T0 验证发生率分级处置；quarantine 兜底 |
| LLM 靠语言直觉而非证据 | typed hypothesis 强制引用 support_reaction_ids；grounding guard 校验 ID |
| LLM 判 T/S 但工具生成不出对的 Y | validate + ledger 守恒把关；生成失败 → typed abstain 不硬造 |
| 检索带不回可类比 donor | adaptive donor（distinct 分子优先）+ 多样性；带不回走拒答 |
| 评估口径漂移 / 泄漏 | train-only 隔离 + 多答案真值 + 全 X 进分母 + 每指标带 N/CI |
| 工程量膨胀 | 严格分 Phase，strict 单步/外部证据/多步/research mode 后置 |

---

## 10. 交接状态

- ✅ 一致性审阅完成；三方案 + 三 discussion 交叉评审完成。
- ✅ 融合权威 design + plan 落盘 `demov2/plan/`（UNIFIED_ 前缀）。
- ⬜ 下一步：用户拍板 §7；建议第一件事 = **P0-T0 验证 lineage bug 发生率**（读代码 + 实跑统计，不改地基、不写推理代码）。
