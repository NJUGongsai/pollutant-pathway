# HIT60 任务书 T4（并行）：fable5 三 P1 修复 + 门禁误杀修复（不背指标）

> 状态：**可执行**（2026-09-29 fable5 评审原文已落盘
> [FABLE5_REVIEW_RESPONSE.md](FABLE5_REVIEW_RESPONSE.md)，三 P1 以其 §7 为准）。
> 依据 [teacher 指导书](TEACHER_PLAN_V43_HIT60_MASTERPLAN_2026-09-29.md) §4 S1"并行不背指标"。
> 另含 S0 取证坐实的门禁误杀修复
> （`reports/phase_s0_hit60/manual_review/gate_case_b978fd0b_forensics.md` §6 三方向，gitignored）。

## 0. 纪律

- **不背指标**：不与 HIT60 任何臂混算、不进效果表；目标是工程质量与可审计性。
- 不改评分语义；门禁对**真不同分子**的拒绝一律不放松（fail-closed）；
  行为等价（P1c）与"只放行 canonical 相同分子"（§4）须测试证明。
- 全仓测试绿（基线 456 passed，conda env `depending43`）；三改动+门禁修复
  各自独立可回滚（分开提交）；先记录 `git status --short`，不动既有未提交改动。

## 1. P1a｜FileRateGate 跨进程竞态（fable5 §3.1、§7-1）

- 位置：`src/pathway_v43/adapters/rate_gate.py`。40 worker 并发读写共享闸门文件的
  `peak_in_flight`/`issued` 计数，读-改-写无互斥，存在丢失更新风险。
- 修法（评审建议）：`fcntl.flock` 文件锁 + 原子读改写段，或改 SQLite 计数表。
  **闸门文件格式保持向后兼容**——既有批次根的 resume 不得被破坏。
- 测试：多进程并发自增不丢更新、崩溃恢复、双进程互斥；不破坏既有
  并发半开区间/先发后完用例。

## 2. P1b｜证据卡 schema 版本（fable5 §5.1、§7-2）

- 位置：`src/pathway_v43/services/reaction_finder.py`。检索结果无 schema 版本字段，
  实现变更字段结构时下游无法区分旧新格式。
- 修法（评审建议）：返回值加 `{"schema_version": "v43-evidence-card-1", "cards": [...]}`；
  消费端（任务组装链）校验版本兼容性，未知版本 fail-closed 报错而非静默解析。
- 兼容：旧 run 产物读取不受影响（只加版本字段不改语义）；`prompt_versions`/
  run identity 机制不动。

## 3. P1c｜domain→services 拒因字符串耦合（fable5 §1.1、§7-3）

- 实际问题：`src/pathway_v43/domain/policy.py:71-74` 的 `_ANALOGY_FALLBACKS`
  拒因词表硬编码，与 `services/donor_applicability.py` 的拒因字面量隐性对齐；
  字面量一改，`decide_prediction_route` 分支静默失效。
- 修法（评审建议其一或组合）：拒因枚举提到 `domain/models.py` 纯常量双方共用；
  或 `decide_prediction_route` 改收结构化 `eligibility.status/fallback_reason`。
- 验收：路由决策**行为等价**——现有路由测试全绿 + 新增钉住测试
  （每个拒因枚举值 → 路由分支的映射各一条用例）。

## 4. 门禁误杀修复（S0 取证坐实）

- 根因（取证报告 §4-§5）：`execute_edits` 在**底物解析索引空间**建
  `atom_id_map`（约 :421、:511-512 原样随 canonical 化 product_smiles 返回），
  `check_target_consistency` 对 canonical SMILES **重新解析**（约 :610）后套用
  旧映射（约 :611）——两索引空间错位产生伪拒因（b978fd0b 案 19 条全为伪）；
  约 :624 与 :667 使 canonical 等价终判在 ID 级拒因非空时**永不可达**；
  约 :604-605 为死检查。
- 修法三方向（取证报告 §6）：
  1. canonical 等价判据前置为**短路终判**（建议 cn_identity 双口径）——分子相同的，
     ID 级差异不得拒；
  2. 统一 product_smiles 与 atom_id_map 的索引空间（内部 atom-map SMILES 或
     RenumberAtoms 对齐），改写死检查；
  3. 固定回归用例：正例（同一分子、ID 置换）必须过；负例（位置异构体等
     真不同分子）必须拒。
- **不背指标**：不改评分口径；不在已见 298 上重算或宣称提升。

## 5. 范围外登记（fable5 P2/P3，不在 T4 内做）

- P2#4 recorded 双轨并发；P2#5 reasoning_effort=max 输出格式要求（→S1 E1 prompt
  工作顺带）；P2#6 temperature 语义冲突（→S1 E2 已规划）；P2#7 D1 top_k=16 vs
  donor 3 的关系文档；P2#8 `normalize_usage` schema 变更防御日志。
- P3#9-12：ArtifactStore LRU 化、batch_identity 指纹化、`display_name` 冗余、
  `ancestry_chain` 环形深度上限。后续批次另排。

## 6. 交付

- `docs/FABLE5_P1A_P1B_FIX_REPORT.md`（P1a+P1b）与
  `docs/FABLE5_P1C_GATE_FIX_REPORT.md`（P1c+门禁修复）：评审原文摘录 → 改动 →
  测试 → 行为等价/只放行证明；改动分开提交可回滚；全仓回归绿。
