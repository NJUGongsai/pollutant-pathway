# 证据 · T-F 位次传递核查（2026-10-16/17）

> 题域标签：**298 = RHEA 通用酶学/已见题**（chain13 批）。探针 ≠ 预注册 ≠ 成绩。
> 本目录是 `docs/TF_RANK_TRANSFER_VERIFICATION_2026-10-16.md` 的配套证据；只读离线，
> 零金标、零题面、零模型、零网络、零新实验。

## 1. 文件清单

| 文件 | 说明 |
|---|---|
| `tf_probe_rank_transfer.py` | 只读独立复算探针（stdlib only，不 import `pathway_v43`，不复用 `rank_audit.py` 任何函数） |
| `tf_probe_output.json` | 探针机读输出（聚合 + 对照表 + 折叠逐条明细 + build 侧折叠明细） |
| `tf_probe_stdout.txt` | 探针控制台输出原文 |
| `git_rank_block_identity.txt` | 「rank 传递代码块在两版 HEAD 间逐字节同一」的命令与输出，含收尾工作树核对 |

## 2. 执行环境（AGENTS.md 返工教训 6：隔离目录执行）

- 隔离目录：`/tmp/multica-task-1743981616/tf_rank_YXcpiV`（`mktemp -d` 新建，非仓库内）
- 做法：探针先 `cp` 到隔离目录再执行；`PYTHONDONTWRITEBYTECODE=1`；无 pytest；
  执行副本与落盘副本 sha256 相同（见下），仓库内不产生字节码/缓存/中间产物。
- 解释器：`/Users/cc/miniconda3/envs/depending43/bin/python`（Python 3.11.16）
- 执行时间：2026-10-17（本机），单次运行约 0.6 s
- 实际 HEAD：`3440ca760ab35d5949cb0947c3c72922575349dc`（分支 `v4.3`）

```
$ cd /tmp/multica-task-1743981616/tf_rank_YXcpiV
$ PYTHONDONTWRITEBYTECODE=1 /Users/cc/miniconda3/envs/depending43/bin/python \
    tf_probe_rank_transfer.py \
    --sync  <repo>/reports/ppv1_s5b/chain13_glm/synced \
    --attr  <repo>/reports/ppv1_s5b/chain13_glm/analysis/attr_chain13_c.json \
    --audit <repo>/reports/ppv1_s5b/p0_rank_audit_2026-10-15/rank_audit_data.json \
    --out   tf_probe_output.json
```

执行副本与落盘副本 sha256（相同）：

```
6adcabe252a6b70f2cd45926908b47e675dc0a54d4cf3d5bab0e118243f6cc54  tf_probe_rank_transfer.py（隔离目录副本）
6adcabe252a6b70f2cd45926908b47e675dc0a54d4cf3d5bab0e118243f6cc54  tf_probe_rank_transfer.py（本目录）
```

## 3. 输入（全部只读；sha256）

| 输入 | sha256 |
|---|---|
| `reports/ppv1_s5b/chain13_glm/synced/metrics.json` | `f2e5003c4bc2de08d34a0d145cceae4a93a0f2565fd5add15f3dc37a805f524e` |
| `reports/ppv1_s5b/chain13_glm/analysis/attr_chain13_c.json` | `738e8d0c72d0304c77a8ad223c99ef6577340ef5e8cf3f2c3382ec3e593913bc` |
| `reports/ppv1_s5b/p0_rank_audit_2026-10-15/rank_audit_data.json`（对照用，非判据源） | `a60adc46e4d9f012eb2c068c0f653a0e0c20324d9ff1d0f368a0cb6b2f04bcfc` |
| `reports/ppv1_s5b/p0_rank_audit_2026-10-15/rank_audit.py` | `7c400a69fca360bbb141b3990d058b6b99e19a24f59ba3f39dccf67d75fdbc32` |
| `reports/ppv1_s5b/p0_rank_audit_2026-10-15/rank_audit_summary.md` | `59d47e9681d914fbe7482867a5b34fba3f96012ca06592bf14bc2a8425647b78` |
| `docs/P0_TRIO_VERDICT_2026-10-15.md` | `54fce583cd5ee8344a4ed0a249f619261520ec98a1bc66d75118538bf796cb9b` |
| `synced/runs/*/native_export/*/payload.json`（298 件） | 逐件未逐一记 hash（只读；件数 298/298 命中，见探针输出） |
| `synced/cases/*.json`（298 件，qid→run_id/export_digest 映射） | 同上 |

## 4. 探针做了什么（四组复算 + 两个附加入口计量）

1. **P1 去重折叠逐条明细**：`expansion_outcomes[*].detail.model.dedup_rejections` ×
   `expand_hypothesis` 载荷（`logical_proposal_id`/`model_rank`/`effective_rank`/
   `rank_basis`）——被折叠者与幸存者的声明位次、生效位次、依据。
2. **P2 模型首位 vs 提交序首事件**：事件按 `(created_at, event_id)` 升序（与
   `s5b_scoring.py` 主口径同判据）取首条，比对模型 rank=1 候选的
   `prepared_hypothesis_id`。
3. **P3 微秒碰撞**：同题内 `created_at` 逐字节相同的事件对计数。
4. **P4 重点两组**：`attr_chain13_c.json → C1.hit1_v2_decomposition.lost_to_rank_gt1_qids`
   8 题 + 由 `metrics.json` 复算的 strict 且 rank>1 全集。
5. **附加入口计量①**：池装配（build）侧折叠痕迹（幸存 spec 的
   `compile.merged_source_keys`，随冻结任务载荷进入 `expand_hypothesis` payload）。
6. **附加入口计量②**：报告投影面（`report_projections[*].product_ranks` 的
   `report_rank`/`dedup_notes`）。

判据来源分别标注：源码读码（本核查自读）与探针复算（本目录）分开，不互相替代。

## 5. 结果与一致性

探针复算 vs P0② 审计产物：**12 项对照全部 MATCH**（折叠事件数 3、模型首位被折叠 0、
含折叠题数 2、微秒碰撞 0/1443、重点组①8 题全「首位=首事件」、重点组②32 题全
「首位=首事件」、strict 119、hit@1 87、题集集合相同）。逐项见
`tf_probe_output.json → compare_with_p0_audit` 与 `tf_probe_stdout.txt`。

**位次去向闭合**（本核查新增，用于排除「被排位的池条目被折叠后不留痕」这一盲区）：
被模型排过位次的声明 ID 里，在展开条目中找不到去向的共 **64 个**（分布 32 题）——
61 个落在模型 novel 预校验拒（`novel_rejections`）、**3 个落在去重折叠**（即上述三次
折叠的被折叠者，声明位次 4/2/5），**`unexplained` = 0**。若曾发生「被排位的池条目被
折叠」，其声明 ID（`hyp_*`）会落 `unexplained`；实测 0 ⇒ 本批不存在该类隐藏折叠。

另有两项**审计未计量的入口**（本探针补测，仅计量不判定）：
池装配侧折叠 **41 题 / 50 次**（与 decide 侧折叠零共现）；报告投影面 1443 条投影、
`dedup_notes` 非空 **0** 条、宽度外 `report_rank=None` 槽 **14** 个。
