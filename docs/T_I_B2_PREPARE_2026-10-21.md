# T-I B2 两臂 prepare + P2-face 报告（2026-10-21）

> **题域标签：[298域] = 298 / RHEA 通用酶学 / 已见题（post-hoc）。** 本报告只含
> 工程准备面读数、批准包校验与批内聚合计数，不含真实成绩、真实模型调用或题面/金标
> 内容；298 与 dev 双向不外推。
>
> **状态：两臂 prepare 均 exit 0、stderr 空；批准包首消费 PASS；build 身份门
> prepare 前后均 PASS；P2-face 八项两臂逐项相同且全符冻结期望；旧批两根/旧 runs/
> 旧协调目录/stop 零触碰。** 未启动 run/score，未调用模型，未读 key/env 内容/金标/
> 题面，未改代码/判据/池，未 push。本报告不自行宣布 GO——发车由 CC 按 §8 手动执行。

## 1. 结论

| 项 | GLM（baseline） | DeepSeek（challenger） |
|---|---|---|
| `prepare` 退出码 | **0** | **0** |
| `prepare` stderr | 0 字节 | 0 字节 |
| 批根 | `~/ppv1_hpc/batch/t_i_298_20261021b2_glm` | `~/ppv1_hpc/batch/t_i_298_20261021b2_deepseek` |
| 批准包首消费 | **PASS**（`7e5d1635…`） | **PASS**（同值） |
| no-cap 标记 | `a2a61261…`，`no_monetary_cap_user_decision` | 同值 |
| `arm_config.json` | `cb541075…`（GLM 模型/env） | `4616fe75…`（DeepSeek 模型/env） |
| build 身份门 | `TI-BUILD-IDENTITY-PASS`，`77cb843b…` | 同值 |
| P2-face 八项 | **全符** | **全符** |
| `p2_face_measure.json` SHA | `ac267fef…` | **同值**（逐字节相同） |
| 封存/停点 | 无 `ti_sealed.json`、无 `stop.json` | 同 |
| runs 根 | 未创建 | 未创建 |

## 2. 执行入口与时间线

在 HPC 登录节点（login05）逐臂串行执行任务书 §5.3 等价命令：

```bash
export TI_WS="$HOME/ppv1_hpc" TI_CODE="$HOME/EnzymeAgent/v43cTH"
export TI_PY="$TI_WS/venv_v44run/bin/python"
export PYTHONPATH="$TI_CODE/src" PYTHONDONTWRITEBYTECODE=1
cd "$TI_CODE"
for arm in glm deepseek; do
  "$TI_PY" -B scripts/hpc/ti_operations.py prepare \
    --arm "$arm" --ws "$TI_WS" --code "$TI_CODE" \
    --config "$TI_CODE/scripts/hpc/ti_arm_config.json" \
    || { echo "STOP: prepare $arm"; exit 1; }
done
```

| 事件 | UTC |
|---|---|
| 前置 `verify-identity`（exit 0） | 04:37:45Z 会话内 |
| `prepare glm` 起/止，exit 0 | 04:37:48Z / 04:37:56Z |
| `prepare deepseek` 起/止，exit 0 | 04:37:56Z / 04:38:03Z |
| 复核审计（login04） | 04:38–04:41Z |

两臂 `record/ti_operations.json` 的 `prepared_at`：`04:37:49.777520Z`（glm）/
`04:37:57.323153Z`（deepseek），与时间线自洽。

两臂 stdout 逐字（stderr 均为空）：

```json
{"files": 298, "remap_add_atom_ge1": 205, "remap_add_atom_ge2": 78, "remap_applied": 242, "specs_total": 531}
{"arm": "glm", "build_identity_fingerprint": "77cb843b1beeab2d6d2d34f497b653a886e6d813323db421166c81cfbe446e59", "n_run_inputs": 298, "prepared": "/work/home/aclhl3hbth/ppv1_hpc/batch/t_i_298_20261021b2_glm"}
{"files": 298, "remap_add_atom_ge1": 205, "remap_add_atom_ge2": 78, "remap_applied": 242, "specs_total": 531}
{"arm": "deepseek", "build_identity_fingerprint": "77cb843b1beeab2d6d2d34f497b653a886e6d813323db421166c81cfbe446e59", "n_run_inputs": 298, "prepared": "/work/home/aclhl3hbth/ppv1_hpc/batch/t_i_298_20261021b2_deepseek"}
```

## 3. 批准包首消费

prepare 内部完成源记录目录校验 + 批根副本再校验；另做一次显式只读复验
（`approval-package`，**exit 0**）。批准件字段两臂一致：

| 字段 | 值 |
|---|---|
| 批准 JSON SHA | `7e5d1635c0c4ab0f220aa7e453ffb41de602b4c7ace1da9bf7a832029473e16d`（5009 B） |
| `approval_status` | `preregistration_confirmed` |
| `approval_source_kind` | `codex_delegated_cc_shijie` |
| `approved_at` | `2026-10-20T15:49:53Z`（原值保留） |
| `preregistration_id` | `prereg-t-i-298-2026-10-20` |
| `budget_mode` / `user_decision_date` | `no_monetary_cap_user_decision` / `2026-10-20` |
| `no_cap_ack` / `cost_cap_cny` | `true` / `null` |
| `preregistration_text_sha256` | `2e45d407…`（预注册文本，非批准 JSON 自身） |
| `script_lock_sha256` | `45a82d25…`（b2 重锁后新锁） |
| `b2_rebatch` | 新 tag/两新批根/新协调目录/旧批零写声明，`approved_at_preserved` 同值 |

| 源记录目录文件 | SHA |
|---|---|
| `preregistration_approval.json` | `7e5d1635…` |
| `budget_no_cap.json` | `a2a61261…` |
| `T_I_SCRIPT_LOCK_2026-10-20.json` | `45a82d25…` |
| `TASK_T_I_LAUNCH_2026-10-20.md` | `0b9b0557…` |
| `T_I_PREREG_2026-10-20.md` | `2e45d407…` |
| `T_I_CODEX_FINAL_REVIEW_2026-10-20.md` | `8344265c…` |

两臂批根均生成：`preregistration_approval.json`、`budget_no_cap.json`、
`record/approved_text/`（4 份快照，SHA 与源记录目录逐件同值）、
`record/approval_manifest.json`（glm `611faa72…` / deepseek `3247b1c6…`）、
`record/ti_operations.json`（glm `5a2e1055…` / deepseek `7587357c…`）、
`arm_config.json`。

`arm_config.json` 共享事实两臂一致：`batch_tag=t-i-298-20261021b2`、
`code_commit=c9c6c7a7…`、题卷 SHA `9f5955d4…`、预注册文本 `2e45d407…`、
批准包 `7e5d1635…`；逐臂差异仅 `arm`/模型 ID/env 文件名（GLM `ZHIPU/GLM-5.3-Flash`
+ `llm.env`；DeepSeek `deepseek-v4.1-flash-1017` + `llm_ds.env`）。

部署树脚本锁对批准记录目录内的锁快照重算：**14/14 OK，`missing=[]`，
`T-I-LOCK-VERIFY PASS`**（锁 `45a82d25…`，`source_commit=c9c6c7a…`）。

## 4. Build 身份门

`verify-identity` 在 prepare 前后各执行一次，均 **exit 0、stderr 0 字节**：

| 字段 | 值 |
|---|---|
| `gate` | `TI-BUILD-IDENTITY-PASS` |
| `batch_tag` | `t-i-298-20261021b2` |
| `build_identity_fingerprint` | `77cb843b1beeab2d6d2d34f497b653a886e6d813323db421166c81cfbe446e59` |
| `manifest_sha256` | `e2e7eb70d5ca13442234cb4b7d97cc115f6d9ec556539c2351e173d9969d4376` |
| `n_run_inputs` | 298 |
| 两臂 `batch_manifest.json` | 同 SHA `e2e7eb70…` |
| 两臂 `build_identity.json` | 同 SHA `929207cb…` |

## 5. P2-face 八项（只读聚合）

| 指标 | 冻结期望 | GLM | DeepSeek | 判定 |
|---|---:|---:|---:|---|
| `files` | 298 | 298 | 298 | 符 |
| `specs_total` | 531 | 531 | 531 | 符 |
| `remap_applied` | 242 | 242 | 242 | 符 |
| `remap_add_atom_ge1` | 205 | 205 | 205 | 符 |
| `remap_add_atom_ge2` | 78 | 78 | 78 | 符 |
| `questions_remap` | 151 | 151 | 151 | 符 |
| `questions_with_add` | 134 | 134 | 134 | 符 |
| `questions_with_multi_add` | 65 | 65 | 65 | 符 |

- 八项两臂**逐项相同**且全部等于冻结期望；两臂 `p2_face_measure.json` **整文件 SHA
  相同**：`ac267feff5d592154ac105925e63bfab716d4053ac7bec5a1d53d08013a2fede`。
- 文件内 `note` 保持探针原文：`298 post-hoc；只读本批 run_inputs.plan.pools；
  非成绩/化学有效性证明`。
- 未改探针口径、未改判据、未改池、未重跑 build。`by_qid` 仅计数 151 条，
  未外带题面/逐题明细。

## 6. 新批根产物清单

| 产物 | GLM | DeepSeek |
|---|---|---|
| `batch_manifest.json` | 有 `e2e7eb70…` | 有，同值 |
| `build_identity.json` | 有 `929207cb…` | 有，同值 |
| `preregistration_approval.json` | 有 `7e5d1635…` | 有，同值 |
| `budget_no_cap.json` | 有 `a2a61261…` | 有，同值 |
| `record/`（4 快照 + manifest + ti_operations） | 有（6 件） | 有（6 件） |
| `p2_face_measure.json` | 有 `ac267fef…` | 有，同值 |
| `arm_config.json` | 有 `cb541075…` | 有 `4616fe75…` |
| `run_inputs/` / `reference_graphs/` | 298 / 298 | 298 / 298 |
| 批根文件数（prepare 前→后） | 599 → 609 | 599 → 609 |
| `ti_sealed.json` / `stop.json` | 无 / 无 | 无 / 无 |
| runs 根 / 协调目录 | 未创建 / 未创建 | 未创建 / 未创建 |

## 7. 旧批零触碰

prepare 前（04:35:51Z）与后（04:40:49Z）两次对旧面做**逐文件 SHA + mtime_ns 树摘要**；
摘要含 mtime，任何写入都会改变摘要：

| 旧面 | prepare 前 | prepare 后 | 判定 |
|---|---|---|---|
| `batch/t_i_298_20261020_glm`（620 文件） | `3af61d4c…` | `3af61d4c…` | 相同 |
| `batch/t_i_298_20261020_deepseek`（648 文件） | `a61c4665…` | `a61c4665…` | 相同 |
| `runs/t_i_298_20261020_glm`（20 文件） | `2370d61b…` | `2370d61b…` | 相同 |
| `runs/t_i_298_20261020_deepseek`（168 文件） | `773b1ad9…` | `773b1ad9…` | 相同 |
| `operations/t_i_coordination_t-i-298-20261020`（8 文件） | `78641eda…` | `78641eda…` | 相同 |
| 旧 `stop.json` | `164b9a6b…` | `164b9a6b…` | 相同（`dispatch_fatal` / smoke10 停点） |
| 旧两臂 operations state | — | mtime `2026-10-20T20:59Z`，早于 prepare | 未触碰 |

- prepare 期间 `$TI_WS` 下**越界写入 = 0**：新增/修改仅位于两个 B2 批根与 B2
  operations state/lock；旧批根、旧 runs、旧协调目录、旧 stop 均无变化。
- 新批 runs 根与 B2 协调目录**未被 prepare 创建**（属 run 阶段）。

## 8. 手动 run 命令（CC 执行；本代理未执行）

在 HPC 登录节点、已 export 任务书 §5.0 的 `TI_WS/TI_CODE/TI_PY/PYTHONPATH` 且
`cd "$TI_CODE"` 后，两臂各一条：

```bash
"$TI_PY" -B scripts/hpc/ti_operations.py launch --phase run --arm glm --ws "$TI_WS" --code "$TI_CODE" --config "$TI_CODE/scripts/hpc/ti_arm_config.json"
"$TI_PY" -B scripts/hpc/ti_operations.py launch --phase run --arm deepseek --ws "$TI_WS" --code "$TI_CODE" --config "$TI_CODE/scripts/hpc/ti_arm_config.json"
```

绝对路径等价写法（任选其一）：

```bash
cd $HOME/EnzymeAgent/v43cTH && PYTHONPATH=$HOME/EnzymeAgent/v43cTH/src PYTHONDONTWRITEBYTECODE=1 $HOME/ppv1_hpc/venv_v44run/bin/python -B scripts/hpc/ti_operations.py launch --phase run --arm glm --ws $HOME/ppv1_hpc --code $HOME/EnzymeAgent/v43cTH --config $HOME/EnzymeAgent/v43cTH/scripts/hpc/ti_arm_config.json
cd $HOME/EnzymeAgent/v43cTH && PYTHONPATH=$HOME/EnzymeAgent/v43cTH/src PYTHONDONTWRITEBYTECODE=1 $HOME/ppv1_hpc/venv_v44run/bin/python -B scripts/hpc/ti_operations.py launch --phase run --arm deepseek --ws $HOME/ppv1_hpc --code $HOME/EnzymeAgent/v43cTH --config $HOME/EnzymeAgent/v43cTH/scripts/hpc/ti_arm_config.json
```

可选配套（身份确认件 §3 所述）：另发 `"$TI_PY" -B scripts/hpc/ti_operations.py
monitor --submit --ws "$TI_WS" --code "$TI_CODE" --config
"$TI_CODE/scripts/hpc/ti_arm_config.json"`；15 分钟巡检阈值不变。

### 发车前快检条件

- 最近一次 netcheck/soak 绿：**2026-10-21T03:02:36Z**；身份确认件 §4.3 条件为
  超过 2h 才发 smoke ⇒ **05:02:36Z 后发车先补快检**（登录经代理 3/3，或计算节点
  6/6，或官方 netcheck `NETCHECK-PASS`）。
- qwen 确认件落盘约 **04:33Z**（文件 mtime 本地 12:33 = UTC 04:33）；若按
  “距 qwen 确认超 2h”口径，**06:33Z 后发车同样先快检**。两条取更严者。
- prepare 完成时（04:38Z）距 netcheck 绿 1h35m，未超 2h；实际发车时点由 CC 判断。

### 停点（零改动，照 TI-F1 原阈值）

| 停点 | 行为 |
|---|---|
| `launch --phase run` 内部 | 每臂 sbatch `sbatch_ti_run.sh`：smoke2 → smoke10 → **两臂 barrier** → full |
| smoke10 两臂 barrier | 任一臂未过 barrier ⇒ 禁止进 full；默认超时 21600s |
| fatal / `consecutive_outage>=2` | 写 `coordination_dir/stop.json`，可执行时 `scancel` 两臂 run 作业；**不自动 resume** |
| full 非模型内容运行失败 >15（第 16 个） | monitor 每 15 分钟巡检触发停两臂 |
| 第二次基础设施停跑 | 站点级决策，**归 CC** |
| score | 必须在 full 门通过后另行执行；本代理不 run/score |

## 9. 证据

目录：`docs/review_evidence/ti_b2_prepare_2026-10-21/`（含 `SHA256SUMS`）。

| 文件 | 内容 |
|---|---|
| `post_audit.json` | 两臂产物/批准件/arm_config/record/P2-face/旧批 diff 全量审计 |
| `post_state.json` | 复核时全量逐文件 SHA+mtime 快照（新旧批根、runs、协调目录、operations state） |
| `pre_state_summary.json` | prepare 前树摘要（执行会话转录；完整映射因 login05 `/tmp` 不跨节点丢失，见 `RUN_NOTES.md`） |
| `p2_face_aggregates.json` | 八项期望 vs 两臂 + 同值判定 |
| `lock_verify.txt` | 14 件逐件重算 + `T-I-LOCK-VERIFY PASS` |
| `approval_revalidate.out` | 显式只读批准包复验（exit 0） |
| `verify_identity_pre.out` / `verify_identity_post.out` | 身份门前后原始输出（exit 0，stderr 空） |
| `prepare_<arm>.stdout.log` / `.stderr.log` | prepare 输出逐字转录 / 空 |
| `exits.txt` | 执行会话退出码与时间线（含首次锁自查读错路径的说明） |
| `audit.py` / `snapshot.py` | 可复跑的只读审计/快照脚本 |
| `RUN_NOTES.md` | provenance、诚实缺口、复算命令 |

## 10. unknown / 未核（诚实登记）

| # | 项 | 状态 |
|---|---|---|
| U1 | run/score/smoke 回执、monitor 作业、B2 协调目录 | 未执行（本轮边界；属 CC 发车后） |
| U2 | 金额 | 未发生付费调用；金额 unknown，不估算 |
| U3 | prepare 原始 stderr 远端留存 | login05 `/tmp` 不跨节点；stderr 空已由执行会话捕获，stdout 逐字转录 |
| U4 | pre_state 完整逐文件映射 | 同上丢失；摘要 digest 与复核全量快照逐项相等，零触碰结论成立 |
| U5 | 部署树 `docs/` 无脚本锁文件 | 锁校验改用批准记录目录内的锁快照（`45a82d25…`），14/14 OK |
| U6 | 两臂 P2-face 文件 SHA 与旧批 C7 相同 | 预期结果：探针只读 `plan.pools`，同题卷/同池/同代码；本轮仍以 B2 新批根实测为准 |

## 11. 红线自查

- 未 run/score，未调用模型，未联网；
- 未读 key/env 内容、金标、题面、`reference_graphs`/`run_inputs` 内容；
- 未改 `src/`、判据、池、探针口径、批准件；未回退 TI-F1 补丁；
- 未写旧批根/旧 runs 根/旧协调目录/stop.json；未封存、未动封存 run；
- 未 push。