# HIT60 任务书 T0：S0 收尾——L1–L5 精确边界表 + 人工化学复核（零 API）

> 状态：待执行。依据 [teacher 指导书](TEACHER_PLAN_V43_HIT60_MASTERPLAN_2026-09-29.md) §4 S0；
> 162 题失分归因已完成（见 §1），本任务书只覆盖剩余两件事：精确边界表、人工复核。
> 开工先记录 `git status --short` 与 HEAD；只新增文件，不动既有未提交改动。

## 0. 目标

产出 S1 变更集施工的**唯一合法输入**：失分池精确边界表（L1 排序池 / L2 选错池 /
L3 引擎有 agent 无 / L4 真空区 / L5 语料无金标的逐题分野），以及刷新后的人工
化学复核清单与复核流程。全程零 LLM 调用、零预测重跑、零金标回灌。

## 1. 输入（只读，SHA 对账后才动手）

- `reports/phase_d/retest/loss_audit/` 7 文件：`loss_audit_298_c0.tsv`、
  `miss_hit1_detail_c0.tsv`、`paired_298_loss_labels.tsv`、`summary.json` 等
  （`output_manifest.sha256` 全过为前置）。
- 引擎结果 `runs/ec298_pd_retest_engine/engine_results.jsonl`（SHA `0e16268c…`）。
- 金标 `questions.jsonl`（SHA `9f5955d4…`；只在离线评分/复核进程只读，
  不写入任何运行侧或仓内产物）。
- 背景结论：[EC298_PD_RETEST_LOSS_ATTRIBUTION.md](EC298_PD_RETEST_LOSS_ATTRIBUTION.md)。

## 2. A｜池定义先冻结（预注册，再计算）

跑任何统计前，把下列定义写入登记文件（此后只许勘误追加）。主池按此优先序
**互斥指派、一题一主池**，原断点标签与路由保留为辅助列：

1. **L1 排序池**：@1 未中 ∧ @5 命中（金标在最终答卷 2–5 位）＝归因表
   `reported_at_rank_2_to_5`。锚点：50。
2. **L2 选错池**：`selected_wrong_product`（选中并提交了另一条记录/卡，金标在
   原始检索层可见但从未进入报告）。锚点：44；子标签 recorded 直通 31 / rank 选卡 13。
3. **L3 引擎有 agent 无**：其余失分（agent @5 未中且非 L2）∧ 引擎 Top-K 含金标。
   K 分 **@5** 与 **@10** 两版各出一列（指导书引的 209 实为引擎 @10，@5=193），
   主推 K 在登记文件里定。预期锚点（@10 版 ≈ 24：unknown 17 + empty 7）。
4. **L4 真空区**：其余失分 ∧ 引擎 Top-10 无金标 ∧ 已封存检索卡范围无金标
   （预期 ≈ 44：retrieval_absence 31 + unknown 8 + empty 4 + valrej 1）。
   标注 `scope_limited`（仅指已观察检索范围，不等于数据库没有）。
5. **L5 语料无金标**：对 v1 **完整资产池**离线核验（零 API）确无金标来源的题，
   是 L4 的子集并带子标签；未核验过不得标 L5。

守恒检查（fail-closed）：主池互斥且并集 = 162；L1 = 50；L2 = 44；
L3+L4 = 68（unknown 25 + empty 11 + valrej 1 + retrieval_absence 31）；
任何对不上处逐题列原因后才可发布。

## 3. B｜边界表生成

- 新脚本 `scripts/ec298_hit60_boundary.py`（零 API），`--check` 复算逐字节一致；
  输入 SHA 清单随产物落盘；远端执行沿用 loss_audit 的只读 run 根纪律。
- 类比声明目标沿用复测归因口径：协议 v2 `atomtool_checks` 无 ledger
  `target_smiles` 键，用运行时 `molecode_to_smiles` 重解析 `parsed.target_molecode`。
- 产物 `reports/phase_s0_hit60/`：
  - `boundary_pools.tsv`：失分 162 行（题号、主池、辅助标签、路由、引擎位次、
    证据引用），附全 298 行速览；
  - `pool_summary.md`：各池计数 + 与指导书 §3 近似数的对账表
    （L1 50 / L2 ~39→? / L3 23→? / L4 89→? / L5 ~33→?，差异逐条注释）；
  - `input_sha256.json`、`output_manifest.sha256`。

## 4. C｜人工化学复核清单（刷新）

指导书的 74 题（27+39+8）是首跑口径；按复测归因刷新为三桶，预计 ~56，
以落盘为准（增删桶须把理由写入登记文件）：

| 桶 | 复核对象 | 复核问题 |
|---|---|---|
| 模型选错 | rank 选卡 13 题 | 有金标卡的候选集合里选了别的卡：金标是否唯一正确/存在多解 |
| 直通答错 | recorded 直通 31 题 | 确定性提交选了非金标 recorded：金标口径、条件相容性、多 recorded 语义 |
| 编辑被拦 | empty 11 + validation_rejected 1 | 编辑被拒题：金标可否由该供体编辑达成；`RXNG_b978fd…` 目标=金标被拒案单列人审 |

清单每题列：题号、底物、金标（仅复核工作簿内）、桶、复核要点、证据引用
（检索卡 / 引擎位次）。**不含** agent 答卷内容与位次（盲性见 §5）。

## 5. D｜复核流程与盲性（不变量 I3）

1. 复核人**盲于模型输出**：只看题面底物、金标、相关检索证据卡与化学上下文；
   不看 agent 报告了什么、排第几、断点标签。工具端从复核导出中剔除答卷/位次列。
2. 逐题判定：`gold_correct_unique / gold_ambiguous_multi / gold_suspect /
   gold_wrong / undetermined`，每题附一句化学理由（不可空）。
3. 翻转 gold（suspect/wrong → 改金标或删题）：逐题理由 + **双人确认**；
   进独立金标版本与 SHA，不覆盖 `questions.jsonl` 原件。
4. 产物 `reports/phase_s0_hit60/manual_review/`（复核人、日期、逐题判定、
   翻转申请单）；汇总进 `docs/HIT60_S0_BOUNDARY_REPORT.md`（含通俗版）。

## 6. 红线

- 零 API；金标只在离线进程只读；不修改任何封存 run 与正式分数。
- 本表是已见题后验分析：不得据它调参/prompt/阈值后再在已见 298 上称独立
  验证（I1）；用途只有一个——给 S1 划边界。
- 复核不得因"模型答了什么"改金标（I3）；金标歧义是数据问题，单列，
  不靠改 scorer 消除。

## 7. 依赖与完成定义

- A/B/C（工具、边界表、清单）**无拍板依赖，可立即开工**；D 人工复核主复核人已定
  （2026-09-29 用户拍板：用户本人；第二确认人在金标翻转时确定即可）。
- 完成 = 边界表通过守恒检查 + 复核清单落盘（D 未定人时 A–C 可先交付，
  复核表留待）；报告 `docs/HIT60_S0_BOUNDARY_REPORT.md`（+通俗版）。
