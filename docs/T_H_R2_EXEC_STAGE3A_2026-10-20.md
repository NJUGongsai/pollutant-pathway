# T-H r2 阶段 3a 执行记录：三版判分与产物回收（2026-10-20）

- 题域：**298 = RHEA 通用酶学／已见题（post-hoc）**
- 批根（远端只读消费）：`/work/home/aclhl3hbth/ppv1_hpc/batch/t_h_s5b_298_20261020r2`
- 判分性质：零 LLM；不读题卷/金标正文；未改 src/tests/scripts；未 push；**未封存**（封存留 3b/主窗口）
- 证据目录：`docs/review_evidence/t_h_r2_stage3a_2026-10-20/`
- 本地副本：`reports/ppv1_s5b/t_h_2026-10-20/r2/`（gitignored）

## 1. 时间线与作业

| 时点（UTC） | 事件 |
|---|---|
| 2026-10-20T07:19:36Z | `launch --phase score` 提交 score 作业（提交前 opsstate 无 score 作业、squeue 空） |
| 2026-10-20T07:19:44Z | 首次轮询：PENDING |
| 2026-10-20T07:21:02Z | RUNNING |
| 2026-10-20T07:23:31Z | `th_score_complete.json.completed_at`；判分完成 |
| 2026-10-20T07:23:38Z | sacct：COMPLETED 0:0，Elapsed 00:03:42 |

- **score job id：46969374**（job name `th-r2-sco+`）
- 终态：`sacct -j 46969374 -n -X` = `COMPLETED 0:0`
- 日志 `$TH_CODE/th_score_46969374.out`：
  ```
  SCORE-GATE-OK: n_terminal=298 n_failed=0 (失败题留分母)
  TH-SCORE-PASS: v1/v3/v2 preserved; root headline=v2; V3 no uplift
  TH-SCORE-PASS
  ```
- opsstate history 依次记录 build 46954982、run 46958084、score 46969374；未重复提交。

## 2. 三项核验

### 2.1 th_score_complete.json

| 字段 | 值 | 判定 |
|---|---|---|
| `headline` | `ppv1-criteria-v2` | PASS |
| `stable_field_differences` | `[]` | PASS |
| `outputs_sha256` 条目数 | 13（三版×三文件 9 + 根三文件 3 + 披露件 1） | PASS |
| 本地副本 SHA 与清单比对 | 13/13 一致，0 mismatch | PASS |
| `th_score_difference.json` 存在性 | **不存在**（`NO_DIFFERENCE_FILE`） | PASS |

稳定字段对照范围：`data_scope, domain_tag, denominator, main_caliber, old_caliber_sensitivity, old_caliber_anyof_multicomponent, buckets, aggregate_diagnosis, run_status_table, criteria_v2, per_qid, evaluator_pairing_bases, caliber_policy`；唯一 `other_different_fields` 为 `criteria_v3`（披露轴新增，非稳定字段漂移）。

### 2.2 三版产物齐全 / 根文件 = v2

| 文件 | `.v1` | `.v2` | `.v3` | 根（headline） |
|---|---|---|---|---|
| metrics.json | 有（169,185 B） | 有（170,192 B） | 有（175,810 B） | 有，SHA 与 `.v2` 相同 |
| report.md | 有（3,260 B） | 有（3,262 B） | 有（3,262 B） | 有，SHA 与 `.v2` 相同 |
| report_plain.md | 有（979 B） | 有（979 B） | 有（979 B） | 有，SHA 与 `.v2` 相同 |

- 根 `metrics.json` SHA256 `ceb9e72e…0c7f6` = `metrics.json.v2`
- 根 `report.md` SHA256 `2812f949…f2339` = `report.md.v2`（`.v3` 亦同，因 v3 纯披露）
- 根 `report_plain.md` SHA256 `e3233c42…63b7a` = `.v2`（`.v3` 亦同）
- 三版顺序符合操作书：v1→保存 `.v1`，显式 v3→保存 `.v3`，最后 v2→保存 `.v2` 且根文件保留为 headline。

### 2.3 criteria_v3_disclosure.json

| 断言 | 实测 | 判定 |
|---|---|---|
| `tier` | `disclosure_only` | PASS |
| `strict_promotion` | `false` | PASS |
| `hit_at_1_effect` | `none` | PASS |
| `tautomer_promoted_nodes` | `[]` | PASS |
| `tier_b_status` | `locked_not_unlocked_this_round` | 符合冻结口径 |

## 3. 核心数字（只读 metrics/report，未读 case/金标）

| 口径 | 分母 | hit@1 | hit@3 | hit@5 | strict（matched_strict 桶 / U） |
|---|---|---|---|---|---|
| v1（豁免关，旧判分语义） | 298 | 84（28.19%） | 113（37.92%） | 120（40.27%） | 121 |
| **v2（headline）** | 298 | **89（29.87%）** | **118（39.60%）** | **125（41.95%）** | **126** |
| v3（纯披露，不改 hit） | 298 | 89（29.87%） | 118（39.60%） | 125（41.95%） | 126 |
| 老口径敏感性（与 116/128/130 同尺） | 298 | 141（47.32%） | 209（70.13%） | 227（76.17%） | 不适用 |

- 运行状态：completed = 298；判分互斥桶 v1 = 58 partial / 121 strict / 119 unmatched，v2 = 53 / 126 / 119。
- 聚合诊断：v1 U=121、H5=120、L=1；v2 U=126、H5=125、L=1。
- v2 豁免块：`edges_with_exemption=5`、`events_exempted_strict=5`、`exempted_participant_occurrences=5`、族计数 `v1:H2O=5`；tier_counts `v1_exempt=10` / `not_exempt_maintains_partial=100`。
- 老口径数字三版一致（141/209/227），符合"判分侧口径变化不回写老口径"。
- 双口径并列、通过线锚（116/128/130）与结论句式均已在 report 中保留；对外引用须带题域标签 298，dev 不外推。

## 4. v3 披露块关键计数

| 项 | 值 |
|---|---|
| axis_pairs_total | 47 |
| axis_nodes_total / not_applicable | 645 / 598 |
| protonation_normalized_pairs（charge_parent / uncharger） | 10 / 10 |
| tautomer_normalized_pairs（default / stereo_preserving） | 13 / 13 |
| single_attribution_counts | none=24、protonation=10、tautomer=13 |
| double_satisfied_pairs / fail_closed_pairs | 0 / 0 |
| carbonate_system_excluded_pairs | 0 |
| AROMATIC-REPR | 本轮未实施/未启用，覆盖未证（对外必须附注） |

## 5. 回收清单（本地 gitignored 镜像）

目标：`reports/ppv1_s5b/t_h_2026-10-20/r2/`，共 **27 个文件**（26 个拉取/附带件 + 1 个 `SHA256SUMS`）。

| 类别 | 文件 |
|---|---|
| 三版 + 根 metrics | `metrics.json`、`metrics.json.v1/.v2/.v3` |
| 三版 + 根报告 | `report.md*`、`report_plain.md*`（各 4 件） |
| 判分完整性 | `th_score_complete.json`、`criteria_v3_disclosure.json` |
| 批运行旁件 | `batch_report.json`、`p2_face_measure.json`、`orchestration.json`、`profile_policy.json`、`th_full_status.json`、`build_identity.json` |
| 失败登记 | `monitoring/failure_register.json` |
| 批准件/记录 | `record/preregistration_approval.json`、`record/budget_no_cap.json`、`record/r2_operations.json`、`record/approved_text/T_H_LAUNCH_PREP_2026-10-20.md`、`record/approved_text/T_H_LAUNCH_TASK_2026-10-20.md` |
| 校验 | `SHA256SUMS`（26 行，覆盖除自身外全部本地副本） |

- `approved_text` SHA 与批准件登记一致：PREP `48ee237b…a317512`，TASK `b3984bbe…0fd5e25`。
- **未拉取**：题卷、金标、reference_graphs、run_inputs、逐题 case/run/state。

## 6. 异常与披露

- 判分链无异常：score 一次提交、一次成功，无重试、无 field 漂移、无 difference 文件。
- `monitoring/failure_register.json` 保留两题既有 NC-9 零调用终止披露项（`RXNG_7a886593…`、`RXNG_ed3d7072…`，`last_status=other_failed_terminal_registered`、`retry_count=0`）；判分按分母 298 全额计入未命中，`n_terminal=298 / n_failed=0`，与既有定性一致，不影响判分。
- 未封存批根；封存、对外发布与人类复核义务留阶段 3b/主窗口。