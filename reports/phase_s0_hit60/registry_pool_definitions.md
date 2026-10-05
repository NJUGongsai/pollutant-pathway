# HIT60 T0 池定义登记文件（预注册，先于计算冻结）

> 2026-09-29 冻结。此后只许勘误追加，不许改定义重算。依据
> [TASK_V43_HIT60_S0_BOUNDARY_AND_REVIEW.md](../../docs/TASK_V43_HIT60_S0_BOUNDARY_AND_REVIEW.md) §2。
> 本文件不含金标；金标只在生成复核工作簿的离线进程中只读打开，且工作簿落在
> gitignored 目录 `reports/phase_s0_hit60/manual_review/`。

## 1. 输入（只读，以 manifest 对账为准）

- `reports/phase_d/retest/loss_audit/loss_audit_298_c0.tsv`（298 行五层旗标 + 断点）
- `reports/phase_d/retest/loss_audit/miss_hit1_detail_c0.tsv`（失分题证据引用；仅供工作簿 join）
- 两者的完整性与 SHA 以 `reports/phase_d/retest/loss_audit/output_manifest.sha256` +
  `input_sha256.json` 为准；本任务开跑前已复验 7 文件全 OK。
- **只用 C0 臂**（发布默认配置）。D-3 臂不进边界表（次实验臂，其断点结构与 C0
  几乎同构，见归因报告 §6）。
- 引擎参照直接用 TSV 的 `engine_rank`/`engine_bucket` 列（源自
  `engine_results.jsonl` SHA `0e16268c…`，loss_audit 已对账），不重读引擎原始文件。

## 2. 池定义（主池按此优先序互斥指派，一题一主池）

前置切分：`hit1`（@1 命中）= `reported_gold=true ∧ gold_report_rank=1`，共 136 题，
不进任何池。注意：TSV 的 `breakpoint_label` 列对 @5 命中题统一标
`reported_at_rank_2_to_5`（含 @1 命中），**必须**用 `gold_report_rank` 区分命中与
失分，不得直接数标签。

| 序 | 池 | 规则 | 预期锚点 |
|---|---|---|---|
| 1 | **L1 排序池** | @1 未中 ∧ `reported_gold=true ∧ gold_report_rank∈{2..5}` | 50 |
| 2 | **L2 选错池** | 断点 `selected_wrong_product`（金标在检索层可见、从未进报告） | 44（recorded 直通 31 + rank 选卡 13） |
| 3 | **L3 引擎有 agent 无** | 其余失分 ∧ `engine_bucket∈{e1,e2_5,e6_10}`（引擎 Top-10 含金标） | **24**（K=10 主口径） |
| 4 | **L4 真空区** | 其余失分 ∧ `engine_bucket=e_none` | 44 |

- **主推 K=10**（指导书引用的 209 即引擎 hit@10；hit@5=193）。辅助列 `pool_k5`
  同规则但 L3 仅 `engine_bucket∈{e1,e2_5}`，预期 L3@5=17。
- **L4 子带**（辅助标签，不改主池）：`l4_pure_vacuum` = 断点
  `retrieval_absence_within_observed_scope`（检索范围本无金标，预期 31）；
  `l4_retrieval_saw_gold` = unknown/empty/valrej 中引擎也无（金标检索层可见但
  引擎与 agent 都没排上，预期 8+4+1=13）。两者都带 `scope_limited=true`
  （"已观察检索范围"≠"数据库没有"）。
- **L5 语料无金标**：仅当对 v1 完整资产池离线核验确无金标来源才可标注；本轮
  本地无全池资产，**默认不标 L5**，`l4_pure_vacuum` 的 31 题是 L5 候选，
  待远端全池核验（脚本预留 `--pool-check` 输入，未提供即全部维持 L4）。

## 3. 守恒断言（fail-closed，任一不符即停止并写 anchor_mismatch.json）

298 总数 / hit1=136 / 失分=162；L1=50、L2=44、L3=24、L4=44；L3@5=17（辅）；
L4 子带 31+13；hit 按路由 recorded 64 / rank 26 / analogy 8 / novel 38；
L1 按路由 novel 27 / rank 23；工作簿三桶 13+31+12=56。
（全部为归因报告 §2 已发布数字，此处仅作防错行断言。）

## 4. 人工复核清单（工作簿桶定义）

| 桶 | 定义 | 预期 |
|---|---|---|
| rank_selected | L2 中 `mode=rank_candidates` | 13 |
| recorded_direct | L2 中 `mode=recorded_direct` | 31 |
| edit_blocked | 断点 `empty_no_model_answer`(11) + `validation_rejected_gold`(1) | 12 |

盲性规则：工作簿**只含** qid/类目/底物/金标/桶/复核要点/检索证据引用（检索卡属
系统输入证据，可看）；**不含**任何模型输出列（first_product、model_order、
selected_evidence_id、analogy_target_* 一律剔除）。唯一例外：`validation_rejected_gold`
的 1 题（RXNG_b978fd…，声明目标=金标被拒案）按任务书"单列人审"，其声明目标等
字段放**非盲人审附页**（同样 gitignored），与盲性工作簿分开。

## 5. 工具与产物

脚本 `scripts/ec298_hit60_boundary.py`（零 API、零第三方依赖，本地与远端同字节
副本可跑）；`--check` 复算逐字节一致。产物：

- `boundary_pools.tsv`（298 行，无金标）
- `pool_summary.md`（计数 + 与指导书 §3 近似数对账，无金标）
- `review_checklist_goldfree.tsv`（56 行，无底物无金标，可入仓）
- `manual_review/review_workbook_56.tsv`（含底物+金标，**gitignored**）
- `manual_review/special_case_nonblind_rxng_b978fd.tsv`（非盲人审附页，gitignored）
- `input_sha256.json`、`output_manifest.sha256`

## 勘误（2026-09-29）

- §5 登记的附页文件名有误：原文 `manual_review/special_case_nonblind_rxng_b978fd.tsv`
  实为 `manual_review/special_case_nonblind.tsv`（实物文件与 `output_manifest.sha256`
  中同名条目 SHA 吻合可佐证）。按"只许勘误追加"规则，原登记行不改，仅此更正。
- `manual_review/review_workbook_56.tsv` 在人工复核填答 + 三方判定签字后内容已变更：
  其当前 SHA 以 `output_manifest_addendum.sha256` 登记为准；原 `output_manifest.sha256`
  中的 `e3558d0d…` 为填答前（空白待填版）基线，两个版本各自可校验。

