# P2 B 臂（v2card）正式批次-单臂结果（2026-10-26）

> **题域标签：[298 域] = RHEA 通用酶学 / 已见题（post-hoc）；与 dev 域双向不外推。**
> **口径：正式批次-单臂（B=v2card）。A=v1card 未跑 full，本报告不出 B−A、不构成正式有效性结论。**
> 批次：`p2-298-20261026` · 批根 `p2_298_20261026_v2card` · 协调目录 `p2_coordination_nb_20261026`
> 执行：notebook（SCNet）· 模型 `deepseek-v4.1-flash-1017` · prompt `c24bee42…`

## 0. 一句话

B 臂全 298 跑完：full 终态门 `passed=true`（0 failed / 0 pending / 0 fatal / 0 内容失败），
score 自动完成（rc=0，v1+v2 双口径，headline=v2）。**v2 hit@1 = 68/298（22.82%），
v1 hit@1 = 64/298（21.48%）；v2 的 +4 hit@1（+5 strict）全部来自 5 条水分子豁免，
unmatched 不变（155）。**

## 1. 四件门（发车前）

| 门 | 状态 | 关键证据 |
|---|---|---|
| 本地入口 | ✅ v2.2 PASS | U7 默认 RC=0（live=cfg=build=`c565cd56…`）；gate-probe 6/6；dryrun 20/20；`deploy_4 check` 9/0/11 |
| 身份路径归一+披露 | ✅ v2 PASS | 新指纹 `fcd84049…`；298 run_inputs 去 tag 后 298/298 同、reference_graphs 298/298 同；R1–R4+N1 全闭 |
| token 实测 | ✅ 完成 | B−A −21.22%（1,091,679 vs 1,385,752，代理 tokenizer）；>13% 题集 0/298；只披露 |
| fatal 独立复验 | ✅ PASS_WITH_CONDITIONS | 隔离 646/646 零漂移、46 题重放全 completed；活体 fatal qid completed/无新门；锁 `828c527b…`、批准包 `c0b4c381…`/canonical `d950bf1d…` |

## 2. 身份与批次

| 项 | 值 |
|---|---|
| batch_tag | `p2-298-20261026` |
| 批根 | `p2_298_20261026_v2card` |
| 运行配置 | `f8089791…` |
| 脚本锁 | `828c527b…`（101 files） |
| 批准包 | `c0b4c381…` / canonical `d950bf1d…` |
| 部署树 code identity | `c565cd56…`（fatal 修复后；修前 `cfd74067…`） |
| build 指纹 | `fcd84049…`（贴 HPC assets_root 归一 `7be805d5…`，离线值） |
| prompt / 模型 | `c24bee42…` / `deepseek-v4.1-flash-1017` |
| source_commit | `11aeeaf…`（按 CC 决定不 commit） |

## 3. 阶段数字

| 阶段 | v1card | v2card | 判定 |
|---|---|---|---|
| smoke2 | 2/2 completed；2 calls / 27,403 tok | 2/2 completed；2 calls / 20,361 tok | 两臂 passed |
| smoke10 | 10/10 completed；10 calls / 130,485 tok | 10/10 completed；10 calls / 130,166 tok | 两臂 passed |
| barrier | — | rc=0（10:39:21Z） | 放行 |
| full | 未跑（单臂计划） | 10:39:21Z → 11:26:14Z（约 47 min） | passed=true |
| score | — | 11:26:16Z → 11:26:35Z rc=0 | 完成 |

## 4. full 终态门（`p2_full_status.json`）

| 项 | 值 |
|---|---|
| schema / passed / reasons | `p2-stage-gate-1` / **true** / `[]` |
| checked | 298 |
| completed / with_calls | 294 / 294 |
| failed / pending / fatal | **0 / 0 / 0** |
| content failures | **0** |
| run failures | 2（模型结构失败，各 1 call；≤15 上限；非 fatal） |
| structural zero-call | 2（`cosubstrate_copy_in_expectation`，0 call） |
| unregistered zero-call | 0 |
| cases_digest | `a98be233…6011b`；锁内 `evaluate_stage(final=True)` 复算同值 |

异常 qid（仅标识）：run failure `RXNG_59a40849…`、`RXNG_28cc9c75…`；structural zero-call `RXNG_7a886593…`、`RXNG_ed3d7072…`。四条均 `status=completed`，留在分母，不剔题、不重跑。

## 5. 结果（分母 298，data_scope=real）

| 指标 | v1 口径 | v2 口径 |
|---|---:|---:|
| **hit@1** | **64（21.48%）** | **68（22.82%）** |
| hit@3 | 96（32.21%） | 101（33.89%） |
| hit@5 | 97（32.55%） | 102（34.23%） |
| strict U | 97 | 102 |
| partial（participant_coverage） | 46 | 41 |
| unmatched（required_node_uncovered） | 155 | 155 |
| 老口径敏感性 hit@1/3/5 | 117/161/172 | 117/161/172 |

95% bootstrap CI（by source group）：

| 指标 | v1 | v2 |
|---|---|---|
| hit@1 | [0.1678, 0.2651] | [0.1812, 0.2785] |
| hit@3 | [0.2685, 0.3758] | [0.2852, 0.3926] |
| hit@5 | [0.2718, 0.3792] | [0.2886, 0.3960] |

**v2 增量归因**：`exemption_enabled=true`、`edges_with_exemption=5`、`events_exempted_strict=5`、`exempted_family_counts={"v1:H2O":5}`；+5 strict（97→102）与 5 条水分子豁免一一对应；+4 hit@1（64→68）为同一豁免在首位次上的表现；unmatched 两口径均 155。`tier_counts={v1_exempt:10, not_exempt_maintains_partial:87}`；reference 侧 `v1_identity_signal=ok`（0 命中）。

## 6. 失败 / 零调用 / usage

- `n_failed=0`；运行状态 `completed=298`。
- 结构性零调用 2 题（0 call、无 usage）；模型结构失败 2 题（各 1 call，usage 已记）；全部留在分母。
- full：`model_calls_total=298`、`total_tokens=3,621,410`、`cost_status=no_snapshot`（无金额帽）。
- smoke：两臂合计 20 calls / 280,651 tokens。
- `evaluator_output_status=pending_user_teacher_decision`（照原样披露）。

## 7. 分族

metrics 产物**无按底物族的分族表**（无 family/stratum 字段）；可用分组只有匹配状态桶与
`exempted_family_counts`（仅 `v1:H2O=5`）。本报告不自行另造分族。

## 8. 红绿与停点

fatal=0、终态 pending=0、内容失败=0、run failures=2（≤15）、stop.json 全程 ABSENT；
未发新车、未 kill、未清 stop、未 resume 旧批；driver 自然退出，无残留 P2 进程；
旧 10-23/10-21 根 0 新文件；`lockin_changed_midrun=[]`。

## 9. 不能证明什么（必须随数字一起引用）

1. **单臂**：A=v1card 只跑 smoke2/smoke10，未跑 full；**不出 B−A、不构成正式有效性结论**。
2. **不得跨批比较**：不得把本报告 68/298 与旧批 89/298、v44 94/298 或 chain14 91/298 直接比较——
   代码（fatal 修复）、batch_tag、批根、运行窗口、分母构成均不同；只能作为本批单臂读数。
3. **post-hoc 已见题**：298 域不外推 dev 域。
4. **v2 是敏感性口径**：headline 固定 v2；v1/v2 同值处不构成"v2 有效"证据；v2 的 +4/+5 只由 5 条 H2O 豁免解释。
5. **evaluator_output_status=pending_user_teacher_decision**：评分器输出状态待用户/老师裁定。
6. 2 条模型结构失败 + 2 条结构性零调用留在分母；不剔除、不重跑、不算"有效修复"。

## 10. 证据

- 运行/终态/score 证据：`docs/review_evidence/p2_launch_2026-10-26/`（`MONITOR_REPORT.md`、`LAUNCH_REPORT.md`、`receipts/terminal/`、`SHA256SUMS` 61 项）
- 身份 v2：`docs/review_evidence/p2_nb_identity_2026-10-26-v2/`
- 入口 v2.2：`docs/review_evidence/p2_nb_entry_2026-10-26-v2-2/`
- fatal 修复/复验：`docs/review_evidence/p2_fatal_fix_verify_2026-10-26/`、`docs/review_evidence/p2_fatal_reverify_2026-10-26/`
- 批准包：`docs/P2_APPROVAL_PACKAGE_2026-10-21/`（`preregistration_approval.json=c0b4c381…`）

## 11. 下一步

按 CC 既有授权 **B 验收通过后自动补 A 臂（v1card）full 298**；两臂齐后才出正式对照结论
（B−A），并需另标 `evaluator_output_status` 与 teacher 裁定状态。