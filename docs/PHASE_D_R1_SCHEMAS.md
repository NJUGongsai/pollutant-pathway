# Phase D R1 修复:机器可读 schema 与字段说明

> 配套 [修复报告](EC298_PHASE_D_R1_REPAIR_REPORT.md)。本文是任务书 §7 交付的
> schema 文档:批次完成状态、配对评分门禁、费用账三类产物的字段语义。
> 全部为 JSON;语义以 `schema_version` 字段版本化,消费端不得忽略未知违规。

## 1. 路线终态分类 — `v43-route-state-1`

生产者:`pathway_v43.batch.classify_route_state(worker_status)`。
输入 = 单路线 worker 终态状态文件(`workers/<route_id>.status.json`)的
持久事实;**不读批次报告汇总字段**。

| 字段 | 类型 | 语义 |
|---|---|---|
| `route_state` | enum | `success_completed` \| `legal_stop` \| `failed` \| `export_failed` \| `missing` |
| `failure_class` | str\|null | 异常类别 = `failed` 字段 `:` 前段(如 `ArtifactIntegrityError`、`TypeError`);非失败为 null |
| `stop_reason` | str\|null | run 级停止原因(`completed`/`awaiting_prediction`/`budget_exhausted`/`invalid_input`/…) |
| `export_ok` | bool\|null | worker 是否成功导出答卷 |
| `failed` | str\|null | worker 记录的原始失败描述(截 300 字符) |

分类规则(按序):

1. 无 `finished_at` → `missing`(未终止);
2. `failed` 非空 → `failed`(**即使 `export_ok=true`、有部分答卷也不算成功**);
3. `export_ok` 为假 → `export_failed`;
4. `stop_reason ∈ {completed, already_completed}` → `success_completed`;
5. `stop_reason ∈ {awaiting_prediction, budget_exhausted, invalid_input}`
   → `legal_stop`(**合法终态;空答卷也是合法答卷**);
6. 其余 → `missing`(有终止时间但无合法 stop_reason)。

## 2. 批次终态汇总 — `batch_terminal_summary`

生产者:`pathway_v43.batch.batch_terminal_summary(route_ids, terminal)`。
出现在 `batch_report.json` 的 `status`/`terminal_summary` 字段与
`merged/export_metadata.json` 的批次块。

| 字段 | 语义 |
|---|---|
| `status` | `completed`(全部合法终态)\| `incomplete`(有缺失无失败)\| `failed`(任一 `failed`/`export_failed`) |
| `n_expected` | 冻结清单路线数 |
| `n_valid_terminal` | = `n_success_completed + n_legal_stop`(可进入发布型判分的路线数) |
| `n_success_completed` / `n_legal_stop` / `n_failed` / `n_export_failed` / `n_missing` | 五类计数 |
| `failed_route_ids` / `export_failed_route_ids` / `missing_route_ids` | 对应 route_id 清单(排序) |
| `route_states` | `{route_id: classify_route_state 结果}` 全量明细 |

`merge_predictions` 元数据同步携带:`batch_terminal_status`、
`n_routes_failed`、`n_routes_export_failed`、`n_routes_missing`、
`n_routes_valid_terminal`、`failed_route_ids`、`missing_route_ids`,及逐路线
`per_route[*].route_state`(与 `answer_kind` 并存:`answer_kind` 描述答卷
**形制**,`route_state` 描述路线**终态**,两者独立)。

## 3. 配对评分门禁 — `v43-pairing-gate-1`

生产者:`pathway_v43.output.pairing_gate`。评分入口
(`scripts/phase_d_paired_scoring.py`)在读取答卷**之前**调用;结果另落
`reports/<out>/pairing_gate.json`。

### `validate_arm(batch_root, expected_route_ids) → dict`

| 字段 | 语义 |
|---|---|
| `ok` | 无违规(该臂可进入发布型配对) |
| `n_violations` / `violations` | 违规数与明细(每条 `{code, …detail}`) |
| `n_routes` | 清单路线数 |
| `route_states` | `{route_id: route_state}` 摘要 |
| `batch_sha256` | 该臂批次身份哈希 |

违规码(`code`):

| code | 含义 |
|---|---|
| `input_manifest_missing / input_manifest_bad_shape` | 冻结清单缺失/形制不符(缺白名单声明) |
| `route_order_mismatch / route_order_duplicates` | 清单与冻结顺序不一致 / 清单内重复 |
| `batch_identity_missing / batch_identity_hash_mismatch / batch_identity_unreadable` | 批次身份缺失 / 体哈希重算不符 / 不可读 |
| `route_failed` | 逐路线分类发现异常失败(detail 含 `failure_class`) |
| `route_export_failed` / `route_missing_terminal` | 导出失败 / 无终态 |
| `merged_artifacts_missing / merged_meta_unreadable / merged_predictions_unreadable` | 归并产物缺失/不可读 |
| `merged_per_route_missing` / `merged_failure_flag_inconsistent` | 归并缺该路线 / 失败标志与独立分类矛盾 |
| `merged_row_count` / `merged_route_id_set` / `merged_route_id_duplicates` | 行数≠清单 / route_id 集合不符 / 行内重复 |
| `route_predictions_file_missing` / `route_predictions_sha_mismatch` | 答卷文件缺失 / 元数据 SHA 与文件实算不符 |
| `merged_terminal_status_inconsistent` | 归并元数据记录的批次终态与独立重算不符 |

### `paired_release_verdict({label: validate_arm 结果}) → dict`

| 字段 | 语义 |
|---|---|
| `verdict` | `complete`(全臂 `ok`)→ 可发布型配对;否则 `diagnostic_incomplete`(仅可出显式标记的部分诊断) |
| `release_eligible` | `verdict=="complete"`;**`complete_20_of_20` 之类发布判定字段必须以此为前提** |
| `per_arm` | `{label: {ok, n_violations, violations(前 20), n_routes, route_states}}` |

配对脚本输出 schema 升为 `pd-paired-2`:新增顶层 `pairing_gate` 块;
`pair_summary_vs_c0[*].complete_20_of_20 = (行数==20 且 verdict=="complete")`。

## 4. 费用账 — `api_account` 输出字段

| 字段 | 语义 |
|---|---|
| `calls[]` | **逐调用明细**(R1-d 新增):`run_id/task_id/attempt/status/error_kind/n_http_attempts/usage_present/known_tokens/elapsed_s` |
| `totals` | 聚合计数与 token 和(含 `n_usage_records`/`n_usage_missing`) |
| `cost_estimate_cny` | **仅当零缺 usage 才为数值**;任何缺失 = `"unknown"` |
| `cost_estimate_known_usage_cny` | 已知 usage 部分按价格快照的小计(部分缺失时存在;**不是总费用**) |
| `conservative_reservation` | 缺 usage 调用的保守预留(仅存在缺失时):`input_tokens_upper`(已发请求文本 `//4` 字符)、`input_cost_upper_cny`、`output_bound="unprovable_no_request_output_cap"`(**输出无请求级上限,上界不可证明**,费用 null 不臆造)、`orphan_calls_not_reserved`(孤儿无请求文本单列)、`basis`(明文规则:须账单回填后费用门才可报绿) |
| `price_snapshot` | 冻结价格快照**逐字保留**(`checked` 日期如实,不伪造成刷新日);下一轮付费前须重取并存档来源 |

不变式:① 不得把 `cost_estimate_known_usage_cny` 写/读作总费用;
② usage 缺失未被账单回填前,费用硬门不得报绿;③ 孤儿调用计数但不估算。

## 5. worker 终态状态文件新增字段

`workers/<route_id>.status.json` 新增 `failed_traceback`(失败时完整调用栈
尾部 4000 字符)——R1-b 教训:r1 只记类型+消息,定位 pb_0117 根因不得不从
checkpoint 反推。该文件是路线终态分类的唯一事实源。
