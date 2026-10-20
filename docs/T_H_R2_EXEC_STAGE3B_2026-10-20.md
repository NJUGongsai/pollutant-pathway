# T-H r2 阶段 3b 执行报告：对账交付 + 逐桶回查 + 批根封存

> 题域：**298 = RHEA 通用酶学 / 已见题（post-hoc）**。本报告全部数字只在本批 298 题域内成立。
> 执行窗口：2026-10-20（北京时间下午；远端 UTC 07:40 左右封存）。
> 性质：只读分析 + 写交付文档 + 封存批根；未改 src/tests/scripts，未 push，未重跑/重判，
> 未读金标/题卷/`llm.env`/逐题 case 正文。
> 上游：`docs/T_H_LAUNCH_TASK_2026-10-20.md` §5/§6、`docs/T_H_LAUNCH_PREP_2026-10-20.md` §2.2/§2.3、
> 阶段 1/2a/2b/3a 报告、`docs/T_H_R2_OPERATIONS_2026-10-20.md`。

## 0. 结论

**STAGE3B = PASS。**

- 任务书 §5 六项全部落盘（同口径表、修复兑现表、P2 披露、human_review 义务、费用、<32% 回查）；
- 两份交付文档已写：`docs/T_H_RESULT_2026-10-20.md`（技术版）、
  `docs/T_H_RESULT_2026-10-20_PLAIN.md`（大白话版）；
- 批根已写 `th_sealed.json` 并整体只读封存（目录 555 / 文件 444）；runs 根保持可写；
- 封存前本地镜像 27 件齐全，`SHA256SUMS` 26 行全部 OK；
- 封存前确认 squeue 无本批作业；build/run/score 三作业均 COMPLETED 0:0。

**核心读数（298 题域，正式口径 v2）：hit@1 89/298 = 29.87%，未达预注册 35–40%（104–119），
低于 32%（<96）回查线。** 同口径对 chain13 v2：87→89（净 +2），逐题 18 改善 / 16 退化 /
264 持平；strict 119→126（+7），31 改善 / 15 退化。相对 chain14 A 91（−2）、chain14 B 85（+4），
落在历史单臂区间 85–91 内。v1→v2 的 +5 是 criteria-v2 测量修正，不是工程回收。

## 1. 做了什么（逐项）

| # | 任务 | 产物 | 状态 |
|---|---|---|---|
| 1 | 同口径对照表（v1↔v1、v2↔v2） | 结果文档 §2；`analysis.json → same_caliber` | 完成 |
| 2 | 修复兑现表（T-E 三层 / D1.2 / C / T-F） | 结果文档 §3；`analysis.json → repair_faces` | 完成（T-F unknown） |
| 3 | P2 披露（531/242/205/78 + strict 转化率） | 结果文档 §4；`analysis.json → p2` | 完成（候选级 unknown） |
| 4 | human_review 义务（2,503 行） | 结果文档 §5；`analysis.json → human_review` | 登记完成，未复核 |
| 5 | 费用（usage/金额） | 结果文档 §6；`analysis.json → cost` | usage 已知；金额 unknown |
| 6 | <32% 逐桶回查 chain13 | 结果文档 §7；`analysis.json → bucket_review/transitions` | 完成 |
| 7 | 两份交付文档 | `docs/T_H_RESULT_2026-10-20.md`、`_PLAIN.md` | 完成 |
| 8 | 批根封存 | 远端 `th_sealed.json`；本报告 §3 | 完成 |
| 9 | 阶段报告 + 证据 | 本文件；`docs/review_evidence/t_h_r2_stage3b_2026-10-20/` | 完成 |

## 2. 对账结果摘要

### 2.1 同口径核心表（v2；分母均 298）

| 批 | hit@1 | hit@3 | hit@5 | strict |
|---|---:|---:|---:|---:|
| chain13 | 87（29.19%） | 112（37.58%） | 118（39.60%） | 119 |
| chain14 A | 91（30.54%） | 116（38.93%） | 121（40.60%） | 124 |
| chain14 B | 85（28.52%） | 116（38.93%） | 122（40.94%） | 122 |
| **T-H r2** | **89（29.87%）** | **118（39.60%）** | **125（41.95%）** | **126** |

v1 同口径：chain13 83、14A 86、14B 81、T-H 84。**未混口径：chain13 的 87 是 v2，不是 v1。**

### 2.2 修复兑现（要点）

- **T-E 三层：** ①对齐 64 行/27 题（探针）；②编译 20 行/9 题（**上限口径，非命中**）；
  ③本批 9 题中 strict 6、hit@1 4（chain13 5/3；14A 5/4；14B 6/2）。
- **D1.2：** 17/17 迁移、9/17 compiled（case 级）；题级超集 25 qid：strict 15（chain13 14）、
  hit@1 9（chain13 11）；9 compiled case 的 14 qid 超集：strict 9（chain13 7）、hit@1 6（=chain13）。
  14 集含 1 题 NC-9 零调用。
- **C 面 45/35：** 35 qid 锚：strict 24（=chain13 24）、hit@1 19（chain13 15）。C 在 chain13 前已装，
  差值不是 C 增量；+4 主要来自 v2 测量修正/位次。
- **T-F：** unknown（缺 dedup_rejections/rank_basis/rank_policy_version/逐事件 rank）。
- **计数：** 5 项题级可测，1 项 unknown，0 项候选级归因。

### 2.3 <32% 回查

| chain13 v2 桶 | 分母 | chain13 hit@1 | T-H hit@1 | 差值 | 判断 |
|---|---:|---:|---:|---:|---|
| matched_strict | 119 | 87 | 79 | −8 | 退化 |
| matched_participant_coverage_partial | 47 | 0 | 4 | +4 | 改善 |
| unmatched_required_node_uncovered | 132 | 0 | 6 | +6 | 改善 |
| 合计 | 298 | 87 | 89 | +2 | 净 +2 |

逐题：18 改善 / 16 退化 / 264 持平。status：31 改善 / 15 退化 / 252 持平。
测量修正 v1→v2：+5（0 退化；5 题全 partial→strict→rank1；4 个核心 qid 在 chain13/14A/14B
四批都翻，另 1 题在 T-H/14A 翻）。工程/批次净效应：+2，与噪声同量级。

### 2.4 P2 与费用

- P2 分母：531 / 242 / 205 / 78；题数 151 / 134 / 65（remap / add / multi-add）。
  旧基 550/261/222/96，预案 529/240/201/75；差异归因见阶段 1。
- 题级 strict 转化率：remap+add **56/134 = 41.79%**；multi-add **32/65 = 49.23%**；
  remap-only **1/17 = 5.88%**；非 remap 对照 **69/147 = 46.94%**。候选级 unknown。
- 费用：调用 298 次 + 重试 2 次；input 821,107 / output 5,894,306 / total 6,715,413；
  missing_calls=0；`cost_status=no_snapshot`、`cost_known_cny=null` → **金额 unknown**。
- human_review：2,503 行（present 209 + unknown 2,294），披露≠已复核，义务已登记。

## 3. 批根封存记录

### 3.1 封存对象与前置

| 项 | 值 |
|---|---|
| 批根 | `/work/home/aclhl3hbth/ppv1_hpc/batch/t_h_s5b_298_20261020r2` |
| runs 根 | `/work/home/aclhl3hbth/ppv1_hpc/runs/t_h_s5b_298_20261020r2`（**不封**，保持可写） |
| 封存件 | 批根 `th_sealed.json`（4,990 B） |
| 封存时间 | `2026-10-20T07:40:52Z`（远端 login03 UTC） |
| 封存人 | T-H r2 stage3b 子代理（主窗口授权，任务书 §8） |
| 封存件 SHA256 | `424f81ad8f73bcedad7112849b121409b02208fdff9676501cd385ecc9883e9a` |
| `th_score_complete.json` SHA256 | `f13de7c040fd956490d4b903fdca4da0289d473457dd642fee1366bc68dc4133`（已列入封存清单 `artifacts_sha256`） |
| 封存清单 SHA 条目 | 28 个批根关键产物（含 `th_score_complete.json`、三版 metrics/report、P2、batch_report、build_identity、record、failure_register 等） |
| 封存前作业 | squeue 空；build 46954982 / run 46958084 / score 46969374 均 COMPLETED 0:0 |
| 封存前本地镜像 | 27 件；`SHA256SUMS` 26 行全部 OK；`rc=0` |

### 3.2 模式与访问复核（远端实测）

| 检查 | 结果 |
|---|---|
| 批根目录模式 | `555`（封存前 `775`） |
| 批根文件模式 | `444`（封存前 `644`/`664`） |
| `record/` 目录 | `555` |
| `metrics.json` | `444` |
| `th_sealed.json` | `444` |
| 可写目录（`find -type d -perm /222`） | **0** |
| 可写文件（`find -type f -perm /222`） | **0** |
| 目录模式非 555 的数量 | 0 |
| 文件模式非 444 的数量 | 0 |
| 批根 `test -w` | **不可写** |
| `metrics.json` `test -w` | **不可写** |
| runs 根 `test -w` | **可写**（按任务书不封） |
| 批根文件数 / 目录数 | 1,569 / 38（封存前 1,568 文件；+1 = th_sealed.json） |
| 符号链接 / 可执行文件 | 0 / 0 |

### 3.3 封存清单内容

`th_sealed.json` 包含：

- `batch_tag`、`batch_root`、`runs_root`、题域标签；
- `jobs`（build/run/score）；
- `score`（v1/v2/v3 的 hit@1/@3/@5、strict、分母 298、headline）；
- `artifacts_sha256`（28 个批根关键产物路径→SHA256）；
- `batch_tree`（1,568 文件 / 38 目录 / 0 符号链接 / 0 可执行文件，封存前计数）；
- `local_mirror`（27 件、26 行 SHA256SUMS、校验 all OK）；
- `local_delivery_sha256`（技术版、PLAIN 版、analysis.json、分析脚本、本地 SHA256SUMS）；
- `sealed_at`、`sealed_by`、`authorization`、`seal_mode`；
- `self_excluded=true`（th_sealed.json 不把自己放进 artifacts 清单）。

**封存后未再修改交付文档。** 交付文档/分析件的当前 SHA 与封存清单 `local_delivery_sha256`
逐项一致（证据 `05_delivery_doc_sha256.txt`，`ALL_MATCH=True`）。

## 4. 证据目录

`docs/review_evidence/t_h_r2_stage3b_2026-10-20/`：

| 文件 | 内容 |
|---|---|
| `analyze_stage3b.py` | 只读对账脚本（输入=本地 metrics/探针件；输出=analysis.json） |
| `analysis.json` | 全量对账数据：同口径表、逐题迁移、桶回查、修复面、P2、费用、human_review、NC-9 |
| `01_remote_artifact_sha256.txt` | 封存前远端 28 个关键产物 SHA256（sha256sum 原始输出） |
| `02_seal_chmod_verify.txt` | 封存前后模式、可写扫描、access 检查、封存件 SHA、文件/目录计数 |
| `03_local_mirror_verify.txt` | 本地镜像 27 件计数、SHA256SUMS 26 行、`shasum -c` 全 OK、rc=0 |
| `04_remote_jobs_and_counts.txt` | squeue 空、三作业 sacct 终态、批根计数、可写计数、封存件 SHA |
| `05_delivery_doc_sha256.txt` | 交付文档/分析件 SHA 与封存清单逐项对照（ALL_MATCH=True） |
| `th_sealed.json` | 封存清单本地副本（与远端同 SHA） |
| `SHA256SUMS` | 本目录证据文件哈希（不含自身） |

## 5. 观察、偏差与 unknown

| # | 事项 | 事实与处置 |
|---|---|---|
| 1 | 本地 `record/` 两件与远端布局不同 | 本地镜像的 `record/preregistration_approval.json`、`record/budget_no_cap.json` 与批根**顶层**同名文件同 SHA；远端 `record/` 实际只有 `r2_operations.json` + `approved_text/` 两件。不是数据不一致，是镜像平铺差异；封存清单按远端真实路径登记（顶层 prereg/budget + record/r2_operations + record/approved_text）。 |
| 2 | 两题 NC-9 零调用 | `RXNG_7a886593…`、`RXNG_ed3d7072…`；本批均 unmatched、rank=None、completed；分母 298 不变。历史 chain13/14 同形态，不是本轮回归。 |
| 3 | 60 题空池（新增 7） | 阶段 1 已归因（21 个旧 spec 过不了 compiler-6 身份门 → 19 删 + 2 替换；7 题唯一 spec 被拒变空池）。沿既有路径，计入未命中；不是判分异常。 |
| 4 | T-F unknown | 无本批逐题 fold/rank 字段；先例只有 chain13 的 0/298 触发 + 合成验证。要测需拉 `dedup_rejections`/`rank_basis`/`rank_policy_version`/逐事件 rank。 |
| 5 | 候选级归因 unknown | 所有修复面的命中都是题级；无法证明是哪个补映射/供给/位次候选命中。需逐事件/逐候选金标匹配明细。 |
| 6 | P2 候选级 strict 转化 unknown | 只有题级 41.79%/49.23%/5.88%；候选级需逐候选明细。 |
| 7 | 金额 unknown | `cost_status=no_snapshot`、`cost_known_cny=null`；不估算。 |
| 8 | human_review 未执行 | 2,503 行义务登记；披露≠已复核；行→题数映射未拉，题数 unknown。 |
| 9 | 单臂无同批 A/B | 修复包效应与批次噪声不可分；T-H 落在 chain14 A/B 的 85–91 区间内。 |
| 10 | D1.2 映射来源 | `record_key → qid` 取自 P0-1 `frame_A.json`（探针输入），不是本批 `run_inputs` 的权威映射；25/14 只是超集，精确 case→qid 归因 unknown。 |

## 6. 红线遵守

- 未改 `src/`、`tests/`、`scripts/`；未 push；未重跑、未重判；
- 未读金标、题卷、`llm.env`、逐题 case 正文；未拉 reference_graphs/run_inputs；
- 封存只 chmod + 写 `th_sealed.json`，未改任何产物内容；
- 旧批/事故批零触碰；runs 根未封；
- 对外数字均带 298 题域标签，未外推 dev 或其他题域；
- 预注册/费用/推远端红线归 CC；本阶段只交付事实与结论。

## 7. 交接

1. 结果可直接引用：`docs/T_H_RESULT_2026-10-20.md`（技术版）+ `_PLAIN.md`（大白话版）。
2. 批根已只读；后续任何再判分/重跑必须另开新批根，不得原地解封。
3. runs 根仍可写，但按封存纪律不再用于本批写操作。
4. 剩余挂账：T-F 逐题测量、P2 候选级转化、human_review 2,503 行、费用金额回填、
   D1.2 精确 case→qid 归因（均需另轮授权/拉数）。