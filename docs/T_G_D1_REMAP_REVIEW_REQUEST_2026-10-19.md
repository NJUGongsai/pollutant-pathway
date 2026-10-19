# 评审请求 — T-G Step D1.2 确定性模板补映射实施（送 Codex，2026-10-19）

> 请求类型：**实施评审**（评审-回修循环；任务书 `docs/TASK_T_G_D1_REMAP_IMPL_2026-10-19.md`）。
> 题域标签：**298 = RHEA 通用酶学 / 已见题（post-hoc）**；探针 ≠ 预注册 ≠ 成绩；零金标。
> **工作树状态（重要）**：D1.2 改动**未提交**且**有其他子代理并行编辑其它文件**（T-E/T-D 实施，
> 涉及 `recorded_source.py`/`s5b_builder.py`/`evaluation.py` 等）。**你的评审范围只限 D1.2 文件面**：
> `src/pathway_v43/pollutant/s5b_compiler.py`、`tests/test_ppv1_s5b_template_remap.py`、
> `tests/test_ppv1_s5b_hit50_v4b.py`、`tests/test_ppv1_s5b_hit50_w1.py`——**读时对这四个文件记录
> sha256 并锁定该版本**；其它文件的并行改动不在本轮评审范围、也不得据此判 D1.2 对错。

## 1. 你要评什么（按序）

1. 任务书（含验收 A–F）：`docs/TASK_T_G_D1_REMAP_IMPL_2026-10-19.md`；
2. D1 探针（v0 规则来源与基线）：`docs/TASK_T_G_D1_PROBE_2026-10-19.md` +
   `reports/ppv1_s5b/t_g_fix_2026-10-19/d1_probe/d1_probe.py`（`unmapped_components`/`pair_components`/
   `patch_v0`，:201-447）；
3. 实施产物（只读）：`reports/ppv1_s5b/t_g_fix_2026-10-19/d1_remap/`——`d1_remap_summary.md`（主窗口汇总；
   **实施子代理终答环节被基础设施截断，summary 由主窗口按落盘产物汇总**）、`d1_remap_replay.{json,log,py}`、
   `d1_remap_c2probe_diff.{json,log,py}`、`c2probe_*.{json}`、`d1_remap_replay.json` 等；
4. 代码 diff（锁版本）：`git diff -- src/pathway_v43/pollutant/s5b_compiler.py` 与
   `git diff -- tests/test_ppv1_s5b_template_remap.py tests/test_ppv1_s5b_hit50_v4b.py tests/test_ppv1_s5b_hit50_w1.py`。

## 2. 评审要求（P0/P1/P2 制式）

- **规则保真**：`complete_template_mapping` 与探针 v0 是否逐字同规则（分量/签名/配对/新鲜号/
  写回侧/顺序）；工业化命名是否引入语义差；幂等/确定性/解析失败 fail-closed 是否与声明一致。
- **触发面**：唯一触发点=wrapper 层 pre-flight 且仅 `transform_no_change`；其它拒因零触碰
  （含「pre-flight 两次解析不改输出」论证）；补映射后仍 tnc ⇒ 原拒因原样；补映射后其它拒因
  如实迁移；`_compile_donor_template_impl` 内部判据零改动。
- **披露与版本**：spec/detail `template_remap` 同形披露；非 tnc 无新增键；compiler-5 升位与
  新常量；版本断言同步是否完整（全仓 `s5b-compiler-4` 引用点是否只剩历史注释）。
- **验收 A–F**：
  A（17 件迁移表 + compiled 数）；B（全框 732→116 迁移与退化件保持）；C（reject_correct 33 件
  负控与 **2 件 reject→compiled 翻转**——重点：判其化学有效性风险与处置建议）；D（非目标
  1,154 行零漂移 + unlock/byte 同源复跑与归因充分性——**other_diff 2/10 同型（阈值降载互动
  非四条件齐备形态）与 additive 全量明细未落盘两处局限**，判是否可接受/需补）；E（全量 pytest；
  注：本轮并行工作树，实测数以交付记录为准）；F（签名巧合专项负控测试是否存在且钉死）。
- **负控纪律**：翻转件不得静默/不得当收益（判是否满足）；退化件 116 保持；依赖 replay json 逐行。
- 终判定=「放行 / 需修正（列 P0/P1）/ 退回」。

## 3. 输出（写到文件）

`docs/T_G_D1_REMAP_CODEX_REVIEW_2026-10-19.md`：
1. 头部：终判定 + 一句话理由 + D1.2 四文件读时 sha256 + 读过的文件清单；
2. 规则保真/触发面/披露版本/验收 A–F 逐项判定表（项 | 判定 | 依据（行号/产物字段）| 要求动作）；
3. 重点项的独立复核：2 件翻转（给处置建议）、other_diff 2/10（判归因充分性）、additive 抽样局限；
4. P0/P1/P2 清单；
5. 「随轮交付书可直接消费的验收结论」汇总。

**纪律（写死）**：只读评审+只新增本报告与你的证据文件（`docs/review_evidence/t_g_d12_codex_2026-10-19/`）；
**不动 src/tests/既有 docs（并行子代理正在编辑，禁止触碰）**；不访问金标/题面/封存逐题 run；
不执行真实批脚本；探针如需复跑一律新 tmp、`PYTHONDONTWRITEBYTECODE=1`、`-B`；不 push；不调用外部模型。