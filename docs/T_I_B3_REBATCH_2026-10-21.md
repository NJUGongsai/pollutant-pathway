# T-I B3 新批重建与 prepare 报告（2026-10-21）

> **题域标签：[298域] = 298 / RHEA 通用酶学 / 已见题（post-hoc）。** 本报告只含
> 工程准备面读数、批准包校验与批内聚合计数，不含真实成绩、真实模型输出或题面/金标
> 内容；298 与 dev 双向不外推。
>
> **状态：B3 全链走到 prepare，未 run、未 score。** C3 netcheck PASS；B3 配置/重锁/
> 批准包重绑完成；C2/C4/C5 通过（C5 付费调用 2 次，均 200）；两臂 build 均
> `COMPLETED 0:0`；`verify-identity` 两臂指纹逐字相同；两臂 prepare 均 exit 0、
> stderr 空；P2-face 八项两臂逐项相同且全符冻结期望；B2 与 20261020 原批零触碰。
> 发车由 CC/主窗口确认后执行，本代理未发 run。

## 1. 结论

| 项 | GLM（baseline） | DeepSeek（challenger） |
|---|---|---|
| 批根 | `~/ppv1_hpc/batch/t_i_298_20261021b3_glm` | `~/ppv1_hpc/batch/t_i_298_20261021b3_deepseek` |
| build job | `47061667`，`COMPLETED 0:0`，01:03:31 | `47061671`，`COMPLETED 0:0`，01:03:34 |
| build 日志判据 | `TI-BUILD-PASS` + `BUILD-GATE-OK` | 同 |
| build 身份门 | `TI-BUILD-IDENTITY-PASS`，`f7fc8c83…` | 同值（逐字相同） |
| `prepare` 退出码 / stderr | **0** / 0 字节 | **0** / 0 字节 |
| P2-face 八项 | **全符** | **全符**（逐项相同） |
| `p2_face_measure.json` SHA | `ac267fef…` | **同值** |
| 封存/停点 | 无 `ti_sealed.json`、无 `stop.json` | 同 |
| runs 根 / 协调目录 | 未创建 | 未创建 |

## 2. 执行入口与时间线

站点乌镇 wuzh02；代码树 `~/EnzymeAgent/v43cTH`；Python
`~/ppv1_hpc/venv_v44run/bin/python`；环境变量按任务书 §5.0 设置
（`TI_WS/TI_CODE/TI_PY/PYTHONPATH/PYTHONDONTWRITEBYTECODE`）。

| 事件 | UTC |
|---|---|
| 旧批/B2 全量 pre-state 快照（SHA+mtime） | 06:32:06Z |
| netcheck `47060529` 提交 / 完成 | 06:34:02Z / 06:34:15Z |
| B3 配置部署（`84181c56…`） | 06:36Z |
| 14 件重锁（`c555eb03…`）/ 批准包重绑（`84babafa…`） | 06:37:26Z / 06:37:57Z |
| C2/C4（`c2_c4.json`） | 06:43Z |
| C5 GLM / DeepSeek 付费调用 | 06:45:18Z / 06:45:46Z |
| 两臂 build 提交 / 作业启动 | 06:47:04Z / 06:47:05Z |
| 两臂 build 完成 | 07:50:36Z / 07:50:39Z |
| `verify-identity`（prepare 前） | 07:54:10Z |
| `prepare glm` / `prepare deepseek` | 07:54:23–30Z / 07:54:31–38Z |
| `verify-identity`（prepare 后） | 07:54:39Z |
| post-state 快照 / 审计 / 批准包复验 | 07:56Z / 08:00Z / 08:01Z |

## 3. C3 站点 netcheck（硬门）

- 提交：`WS=$TI_WS sbatch --parsable scripts/hpc/sbatch_th_netcheck.sh`；**唯一**直接
  sbatch 的脚本，其余全部走 `ti_operations.py launch`。
- `47060529`：`COMPLETED 0:0`；日志含
  `NETCHECK-PASS: python/rdkit/layout/disk/flock/dashscope 全过`。
- 关键读数：Python 3.11.15、rdkit 2026.03.5、`pathway_v43 import ok`、
  `flock: 互斥/释放语义成立`、dashscope 出口 API 层应答（`InvalidApiKey` 404 层，
  链路通）、`df` 790G free（78%）。

## 4. B3 配置、重锁与批准包

### 4.1 配置

`$TI_CODE/scripts/hpc/ti_arm_config.json`：

| 字段 | B3 值 |
|---|---|
| `batch_tag` | `t-i-298-20261021b3` |
| 两臂 `batch_name` / `runs_name` | `t_i_298_20261021b3_{glm,deepseek}` |
| `coordination_dir` | `{ws}/operations/t_i_coordination_t-i-298-20261021b3` |
| `immutable_batch_names` | `t_h_s5b_298_20261020`、`t_i_298_20261020_{glm,deepseek}`、**`t_i_298_20261021b2_{glm,deepseek}`** |
| config SHA | `84181c56b04109ff1a97165c0b4b2367262637a9e81e31337725078376ef0cda` |

### 4.2 14 件重锁

- 对部署树逐件重算 14 件：**14/14 OK，`missing=[]`，`T-I-LOCK-VERIFY PASS`**。
- 与 B2 锁（`45a82d25…`）逐件比较：**仅 `scripts/hpc/ti_arm_config.json` 变化**
  （`4feecdc3…` → `84181c56…`），其余 13 件逐字不变。
- 新锁 SHA：`c555eb03810227fc20ed874ebbce9729e273ac87a8f532b0315a980e28313d9d`；
  新增 `relock_b3_rebatch` 块（新 tag/根/协调目录；B2 两根加入 immutable；
  自述“非新批准、非签名”）。

### 4.3 批准包重绑

批准 JSON（`84babaf0…`，7272 B）在 B2 版基础上新增 `b3_rebatch` 块：

| 字段 | 值 |
|---|---|
| `approved_at_preserved` | `2026-10-20T15:49:53Z`（原值） |
| `approval_basis_preserved` | `原预注册+任务书+本终审增补` |
| `approval_source_kind_preserved` | `codex_delegated_cc_shijie` |
| `no_cap_ack_preserved` | `true` |
| `previous_script_lock_sha256` | `45a82d25…` |
| `new_script_lock_sha256` | `c555eb03…` |
| `reason` | B2 被越权直接 `sbatch sbatch_ti_run.sh`（绕过 launch）污染；B3 新 tag/根/协调目录；B2 与 20261020 原批只读保全 |
| `b2_pollution.observed_jobs` | `47054286`、`47054336`、`47059065`、`47059067`、`47059069` |
| `old_batches_preserved_immutable` | 20261020 两根 + B2 两根 |
| `old_batch_zero_write` / `old_stop_json_untouched` | `true` / `true` |

- 未新增 CC 签名；`approval_basis`/`approval_source`/`approved_at`/`no_cap_ack`
  逐字保留。三份 prose 快照 SHA 不变。
- HPC 记录目录已同步：`preregistration_approval.json` `84babafa…`、
  `T_I_SCRIPT_LOCK_2026-10-20.json` `c555eb03…`、`SHA256SUMS` `2950c7d0…`
  （5/5 `sha256sum -c` OK）、`SHA256SUMS.external` `a3329313…`。
- `approval-package` 只读复验：prepare 前、prepare 后各一次，均 **exit 0 / stderr 0 字节**。
- 旧 B2 件保留在证据目录 `*.b3pre`：批准 `7e5d1635…`、锁 `45a82d25…`、
  `SHA256SUMS` `31493bc1…`、external `75fa7fb8…`。

## 5. C2 / C4 / C5

### 5.1 C2（凭证/权限/路径/磁盘/flock）

| 项 | 结果 |
|---|---|
| 两份 env 存在、权限 | `llm.env`、`llm_ds.env` 均 `600` |
| key/base 存在性（只布尔） | 两臂均 `has_api_key=true`、`has_base_url=true` |
| B3 新路径（批根/runs/state/lock/协调目录） | **全部不存在** |
| 磁盘 | `/work` 3.5T，free **847.6 GB**（used 77.4%），>100GB 门通过 |
| flock（父持锁子拒/父释放子得） | 两项均 true |
| immutable 语义 | 20261020 两根、B2 两根 `REFUSED_IMMUTABLE`；B3 `ALLOWED` |

### 5.2 C4（两臂模型/base/REQUEST_PARAMS）

| 项 | GLM | DeepSeek |
|---|---|---|
| 模型 | `ZHIPU/GLM-5.3-Flash` | `deepseek-v4.1-flash-1017` |
| 模型与冻结期望一致 | true | true |
| base | `https://dashscope.aliyuncs.com` | 同值（sha `5891aed8…`） |
| `V43_LLM_REQUEST_PARAMS` | 未设置（None） | 同值（None） |
| 禁用温度/思考键 | 无 | 无 |

两臂唯一差异仍是模型 ID + env 文件；base 与 REQUEST_PARAMS 同值。

### 5.3 C5（两臂最小真实调用，付费 2 次）

| seq | 臂 | 模型 | status | input | output | total | 耗时 | 金额 |
|---|---|---|---:|---:|---:|---:|---:|---|
| 5 | GLM | `ZHIPU/GLM-5.3-Flash` | 200 | 21 | 41 | 62 | 3.431s | unknown |
| 6 | DeepSeek | `deepseek-v4.1-flash-1017` | 200 | 38 | 18 | 56 | 1.200s | unknown |

- 两臂均 `ok=true`、`content_nonempty=true`；记录写入
  `$TI_WS/operations/preflight_calls.json`（seq 1–4 原样保留；文件权限 600）。
- 累计：6 次调用，input 177 / output 534 / total 711 tokens；金额
  `cost_status=no_snapshot`、`cost_known_cny=null`，**不估算**。
- 预检调用不计批内 gate，但计入两臂 usage 账。

## 6. 两臂 build 与身份门

| 项 | GLM | DeepSeek |
|---|---|---|
| job / 名称 | `47061667` / `ti-glm-build` | `47061671` / `ti-deepseek-build` |
| 提交 / 启动 | 06:47:04Z / 06:47:05Z | 同 |
| 终态 | `COMPLETED 0:0`，01:03:31 | `COMPLETED 0:0`，01:03:34 |
| 日志 | `TI-BUILD-PASS`；`BUILD-GATE-OK n=298 sha=9f5955d4… entries_with_cosub_labels=298/298` | 同 |
| build-gate | exit 0 | exit 0 |
| `batch_manifest.json` SHA | `5e8c2a4ef06e49940ee59fc8bfc5cfb99a2928e081c313e8f7d792bf86919c89` | 同值 |
| `build_identity.json` SHA | `ec90ec545247d74c061a45461005ae63ca9a57f359ea180667c221353c5e9616` | 同值 |

`verify-identity`（prepare 前后各一次）均 **exit 0 / stderr 0 字节**：

| 字段 | 值 |
|---|---|
| `gate` | `TI-BUILD-IDENTITY-PASS` |
| `batch_tag` | `t-i-298-20261021b3` |
| `build_identity_fingerprint` | `f7fc8c83a71b25cce53063e4ae2e4d108ad010d8ebac97b3b037766f9608ce8b` |
| `manifest_sha256` | `5e8c2a4ef06e49940ee59fc8bfc5cfb99a2928e081c313e8f7d792bf86919c89` |
| `n_run_inputs` | 298 |

指纹与 B2（`77cb843b…`）不同属预期（B3 新 `batch_tag` 进入 `run_id`/指纹）；
**两臂逐字相同**是硬门，已由断言式门背书（含 298 条 `(qid, run_input_sha256)`）。

## 7. 两臂 prepare 与 P2-face

两臂串行执行 `ti_operations.py prepare --arm {glm,deepseek}`：

| 项 | GLM | DeepSeek |
|---|---|---|
| exit / stderr | 0 / 0 字节 | 0 / 0 字节 |
| `prepared_at` | `2026-10-21T07:54:24.699507+00:00` | `2026-10-21T07:54:31.783362+00:00` |
| 批准包首消费 | PASS（`84babafa…`） | PASS（同值） |
| `arm_config.json` SHA | `bbe8fc0e…`（GLM 模型/env） | `750c715d…`（DeepSeek 模型/env） |
| `record/approval_manifest.json` | `ae27526e…` | `f6f1414f…` |
| `record/ti_operations.json` | `d073c8a8…` | `cb593d98…` |

P2-face 八项（只读 `run_inputs.plan.pools`，零模型、零金标）：

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

- 两臂 `p2_face_measure.json` 整文件 SHA 相同：
  `ac267feff5d592154ac105925e63bfab716d4053ac7bec5a1d53d08013a2fede`。
- `note` 保持探针原文；`by_qid` 仅计数 151 条，未外带题面/逐题明细。
- 两臂批根文件数均 609（prepare 后）；`runs/` 与 B3 协调目录均未创建。

## 8. 旧批零触碰（B2 + 20261020）

pre-state（06:32:06Z）与 post-state（07:56Z）均做逐文件 SHA + mtime_ns 树摘要；
摘要含 mtime，任何写入都会改变摘要。两次逐项相等：

| 旧面 | 文件数 | 摘要（pre=post） |
|---|---:|---|
| `batch/t_i_298_20261020_glm` | 620 | `3af61d4c…` |
| `batch/t_i_298_20261020_deepseek` | 648 | `a61c4665…` |
| `runs/t_i_298_20261020_glm` | 20 | `2370d61b…` |
| `runs/t_i_298_20261020_deepseek` | 168 | `773b1ad9…` |
| `operations/t_i_coordination_t-i-298-20261020` | 8 | `78641eda…` |
| 旧 `stop.json` | — | `164b9a6b…`（相同） |
| `batch/t_i_298_20261021b2_glm` | 671 | `4882696d…` |
| `batch/t_i_298_20261021b2_deepseek` | 649 | `b3ca909c…` |
| `runs/t_i_298_20261021b2_glm` | 2 | `6751872d…` |
| `runs/t_i_298_20261021b2_deepseek` | 187 | `3e73fd9b…` |
| `operations/t_i_coordination_t-i-298-20261021b2` | 8 | `6b523366…` |
| 旧两臂/B2 四份 operations state | — | SHA 全部相同 |

`$TI_WS` 下自 pre-state 起的**越界写入 = 0**（审计脚本按 mtime 全树扫描，
允许面仅 B3 批根/ops state、B3 证据目录、记录目录同步、`preflight_calls.json`）。
B2 的 `stop.json`、runs 残留、批根产物均原样保全；本轮未读取/改写其内容。

## 9. 手动 run 命令（CC 执行；本代理未执行）

在 HPC 登录节点、已 export 任务书 §5.0 变量且 `cd "$TI_CODE"` 后：

```bash
"$TI_PY" -B scripts/hpc/ti_operations.py launch --phase run --arm glm --ws "$TI_WS" --code "$TI_CODE" --config "$TI_CODE/scripts/hpc/ti_arm_config.json"
"$TI_PY" -B scripts/hpc/ti_operations.py launch --phase run --arm deepseek --ws "$TI_WS" --code "$TI_CODE" --config "$TI_CODE/scripts/hpc/ti_arm_config.json"
```

两臂 run 作业都提交后，可选监控：

```bash
"$TI_PY" -B scripts/hpc/ti_operations.py monitor --submit --ws "$TI_WS" --code "$TI_CODE" --config "$TI_CODE/scripts/hpc/ti_arm_config.json"
```

**绝对禁止**直接 `sbatch scripts/hpc/sbatch_ti_run.sh`——B2 就是这样被污染的；
run/score 只能走 `launch`。

### 发车前快检条件

- 最近一次 netcheck 绿：**2026-10-21T06:34:15Z**（`47060529`）。
- 若距该时点超过 2h 才发 smoke，先按 C8 口径补快检（登录经代理 3/3、计算节点
  6/6 或官方 netcheck `NETCHECK-PASS`）。
- B2 事故后的发车确认由 CC/主窗口决定；本代理不自行发 run。

### 停点（零改动，照 TI-F1 原阈值）

| 停点 | 行为 |
|---|---|
| `launch --phase run` 内部 | 每臂 smoke2 → smoke10 → 两臂 barrier → full |
| smoke10 barrier | 任一臂未过 ⇒ 禁止进 full；默认超时 21600s |
| fatal / `consecutive_outage>=2` | 写 B3 `coordination_dir/stop.json`，可执行时 `scancel` 两臂 |
| full 运行失败 >15 | monitor 每 15 分钟巡检触发停两臂 |
| score | full 门通过后另行执行；本代理不 run/score |

## 10. 证据

目录：`docs/review_evidence/ti_b3_rebatch_2026-10-21/`（含 `SHA256SUMS`、`RUN_NOTES.md`）。

| 文件 | 内容 |
|---|---|
| `pre_state.json` / `post_state.json` | 旧批/B2 全量逐文件 SHA+mtime 快照（前后） |
| `post_audit.json` | 两臂产物/批准件/arm_config/record/P2/旧批 diff 全量审计 |
| `b3_summary.json` | 关键 ID/SHA/计数汇总 |
| `p2_face_aggregates.json` | 八项期望 vs 两臂 + 同值判定 |
| `c2_c4.json` / `c2_c4.py` | C2/C4 原始读数与可复跑脚本 |
| `c5_glm.out` / `c5_deepseek.out` / `c5_preflight.py` | C5 两臂调用回执与脚本 |
| `preflight_calls.json` | 预检账（seq 1–6） |
| `lock_verify.txt` / `lock_verify.py` | 14 件逐件重算 + 旧锁 diff |
| `approval_revalidate.out` / `_post.out` | 批准包前后只读复验（exit 0） |
| `build_submit_*.out` / `build_*.out` / `build_gate_*.out` | build 提交、日志、build-gate |
| `verify_identity_pre.out` / `_post.out` | 身份门前/后原始输出（exit 0，stderr 空） |
| `prepare_<arm>.stdout.log` / `.stderr.log` | prepare 输出逐字 / stderr 空 |
| `sacct_build.txt` | 两臂 build 作业终态 |
| `netcheck_47060529.out` | C3 原始日志 |
| `*.b3pre` | 重绑前的批准件/锁/SHA256SUMS（B2 值） |

## 11. unknown / 未核（诚实登记）

| # | 项 | 状态 |
|---|---|---|
| U1 | run/score/smoke 回执、B3 协调目录、monitor 作业 | 未执行（本轮边界；属 CC 发车后） |
| U2 | 金额 | 仅 2 次预检付费调用；无价格快照，金额 unknown，不估算 |
| U3 | B2 污染的操作者与完整动机 | 非本代理处置范围；只记录观察到的 job/stop 事实，B2 零改写 |
| U4 | B3 build 指纹与 B2 差异的逐字节载荷 diff | 未做（新载荷在 HPC）；门语义已强制两臂逐字相同，指纹差异归因于新 batch_tag |
| U5 | 部署树 `docs/` 无脚本锁文件 | 锁校验用批准记录目录内的锁快照（`c555eb03…`），14/14 OK |
| U6 | `p2_face_measure.json` SHA 与 B2/旧批相同 | 预期（同题卷/同池/同代码、探针只读 `plan.pools`）；以 B3 实测为准 |

## 12. 红线自查

- 未 run/score，未发 monitor；未调用模型做批内请求（仅 C5 两次预检）；
- 未读 key 值、金标、题面、`reference_graphs`/`run_inputs` 内容；
- 未改 `src/`、判据、池、探针口径、三份 prose 批准文本；未回退 TI-F1 补丁；
- 未写 20261020/B2 批根、runs、协调目录、stop.json（快照摘要前后相同）；
- 未封存、未动封存 run；未 push。