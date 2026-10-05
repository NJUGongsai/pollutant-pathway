# HIT60 S0 边界表与人工复核交付报告（C0 臂，零 API）

> **状态：complete（A 边界表 / B 工作簿与清单已交付；D 人工化学复核待用户执行）**。
> 2026-09-29。任务书：[TASK_V43_HIT60_S0_BOUNDARY_AND_REVIEW.md](TASK_V43_HIT60_S0_BOUNDARY_AND_REVIEW.md)；
> 池定义预注册：[registry_pool_definitions.md](../reports/phase_s0_hit60/registry_pool_definitions.md)。
> 全程零 LLM 调用、零预测重跑、零金标回灌；金标只在 Chenyu 离线进程只读打开，
> 写入的含金标产物仅存 gitignored 的 `manual_review/`。
> 通俗版：[HIT60_S0_BOUNDARY_REPORT_PLAIN.md](HIT60_S0_BOUNDARY_REPORT_PLAIN.md)。

## 1. 执行与对账

- 本地与 Chenyu 远端（`/tmp` 同字节脚本副本）各执行一次；三个共有产物
  （boundary_pools.tsv / pool_summary.md / review_checklist_goldfree.tsv）
  两端 SHA 逐字节一致；远端 `--check` 复算一致。
- 输入为复测丢分归因封存产物（`reports/phase_d/retest/loss_audit/`，7 文件
  manifest 本地复验 + 远端 `sha256sum -c` 双过——注意远端 locale 为中文，
  校验输出为「成功」而非 "OK"）；只读，未改动任何封存 run。
- 守恒断言 fail-closed 全过：298/136/162；L1=50、L2=44、L3(K10)=24、L4=44；
  L3@5=17（辅）；L4 子带 31+13；hit 路由 64/26/8/38；L1 路由 novel 27/rank 23；
  工作簿 13+31+12=56（全部为归因报告 §2 已发布数字的防错行断言）。
- D-3 臂按登记文件排除；引擎参照用封存 TSV 的 `engine_rank/engine_bucket`
  列，未重读引擎原始文件。

## 2. 边界表结果（`reports/phase_s0_hit60/`）

| 池 | 题数 | 含义 |
|---|---:|---|
| L1 排序池 | 50 | 金标在答卷 2–5 位（novel 27 / rank 23；引擎位次 e1 4 / e2-5 27 / e6-10 4 / 无 15） |
| L2 选错池 | 44 | selected_wrong（recorded 直通 31 / rank 选卡 13；44/44 金标在检索层可见） |
| L3 引擎有 agent 无 | 24 | K=10 主口径（unknown 17 + empty 7）；K=5 辅助口径 17 |
| L4 真空区 | 44 | l4_pure_vacuum 31（retrieval_absence，即 L5 候选）+ l4_retrieval_saw_gold 13（引擎 Top-10 亦无，但检索层见过金标） |

- **L5（语料无金标）本轮未核验**：本地/本轮无 v1 全池资产，全部 L4 维持
  `scope_limited=true`；脚本已预留 `--pool-check` 输入，远端全池核验后方可把
  `l4_pure_vacuum` 31 题中的子集升格 L5。**"已观察检索范围无金标" ≠ "数据库没有"**。
- 池×路由、池×引擎位次完整交叉表见 `pool_summary.md`。

## 3. 与 teacher 指导书 §3 近似数的对账

| 指导书 | 本表 | 差异说明 |
|---|---|---|
| L1 50 | 50 | 一致 |
| L2 ~39 | 44 | 指导书取首跑口径；复测 selected_wrong=44 |
| L3 23 | 24（K=10） | 指导书引「引擎@5 209」实为引擎 hit@10（hit@5=193）；K=5 口径为 17 |
| L4 89 | 44 | 指导书 89 = 112（@5 未中）− 23（引擎@5 有）的粗切，把 L2 的 44 也算进了"系统外"；本表 L4 不含 L2，且单列「引擎无但检索见过金标」13 题子带（这 13 题信息其实仍在系统内，只是引擎也没排上） |
| L5 ~33 | 待核验 | 对应 l4_pure_vacuum 31 题（范围限定口径） |

对 S1 的含义：**"信息在系统内"的可修题量 = L1 50 + L2 44 + L3 24 = 118**
（指导书按 112 估算，差额来自 L3 口径与 L2 计数）；主攻顺序与指导书一致。

## 4. 人工复核交付（D4：用户自任主复核）

- **盲性工作簿** `reports/phase_s0_hit60/manual_review/review_workbook_56.tsv`
  （gitignored，含金标）：56 行 ×15 列；每行有 qid、类目、底物、金标、桶、
  复核要点（rank_selected 13 / recorded_direct 31 / edit_blocked 12）、
  路由、引擎位次、检索证据引用；**已验证零模型输出列**（first_product/
  model_order/selected_evidence/analogy_target_* 均未导出），底物与金标 56/56 非空。
- **非盲人审附页** `special_case_nonblind.tsv`（gitignored）：唯一
  `validation_rejected_gold` 题（声明目标重解析=金标被一致性门禁拒）按任务书
  单列，允许查看声明目标相关字段，与盲性工作簿分开存放。
- **金标无关清单** `review_checklist_goldfree.tsv`（可入仓）：同 56 题的桶/
  要点/证据引用，无底物无金标，供进度跟踪。
- 复核填法：工作簿 `verdict` 列填
  `gold_correct_unique / gold_ambiguous_multi / gold_suspect / gold_wrong / undetermined`，
  `rationale` 每题一句化学理由（不可空）；判 `gold_suspect/gold_wrong` 的题进入
  翻转流程：逐题理由 + `second_confirmer` 第二人确认 + 独立金标版本，不覆盖
  `questions.jsonl` 原件。

## 5. 限定

1. 已见题后验分析，不构成独立外部验证；本表唯一用途是给 S1 划边界（I1：
   不得据本表在已见 298 上调参后自称验证）。
2. L5 未核验；"L4 真空区"全部带 scope_limited 限定。
3. `boundary_pools.tsv` 的 `category` 列沿用归因 TSV 原值（部分题为空），
   工作簿 `category` 取自金标文件。
4. 单次模型抽样的既有限定继续适用（归因报告 §9）。

## 6. 产物索引与复现

`reports/phase_s0_hit60/`：`registry_pool_definitions.md`（冻结）、
`boundary_pools.tsv`、`pool_summary.md`、`review_checklist_goldfree.tsv`、
`input_sha256.json`、`output_manifest.sha256`；`manual_review/`（gitignored）：
`review_workbook_56.tsv`、`special_case_nonblind.tsv`。
脚本：`scripts/ec298_hit60_boundary.py`（`v43-hit60-s0-boundary-1`，零第三方依赖）。

复现（Chenyu，零 LLM）：

```bash
cd /usrdata/EnzymeCAGE_data/workspaces/dependingv43 && python3 \
  /tmp/ec298_hit60_boundary.py \
  --audit-tsv reports/phase_d/retest/loss_audit/loss_audit_298_c0.tsv \
  --detail-tsv reports/phase_d/retest/loss_audit/miss_hit1_detail_c0.tsv \
  --loss-audit-dir reports/phase_d/retest/loss_audit \
  --gold /usrdata/EnzymeCAGE_data/workspaces/ec298_gold_readonly/questions.jsonl \
  --out-dir reports/phase_s0_hit60          # 加 --check 复算
```

本地（无金标，仅边界表三产物）：同脚本去 `--gold`/`--detail-tsv`。
