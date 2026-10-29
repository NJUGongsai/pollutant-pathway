# T-I C7 prepare + P2-face 报告（2026-10-21）

> **题域标签：[298域] = 298 / RHEA 通用酶学 / 已见题（post-hoc）。** 本报告只含
> 工程准备件、批准包校验与批内聚合计数，不含真实成绩、真实模型调用或题面/金标内容；
> 298 与 dev 双向不外推。
>
> **状态：两臂 prepare 均 exit 0；批准包首消费校验 PASS；P2-face 8 项冻结期望
> 两臂逐项一致、且 `p2_face_measure.json` 两臂逐字节相同。** 未启动 run/score；
> 未调用模型；未读 key/env 内容/金标/题面；未改代码/判据/池；未 push。
> 本报告不自行宣布 GO——C7 只交付准备面读数，C8 是否发车由 CC 拍板。

## 1. 结论

| 项 | GLM（baseline） | DeepSeek（challenger） |
|---|---|---|
| `prepare` 退出码 | **0** | **0** |
| 批根 | `~/ppv1_hpc/batch/t_i_298_20261020_glm` | `~/ppv1_hpc/batch/t_i_298_20261020_deepseek` |
| runs 根（尚未创建） | `~/ppv1_hpc/runs/t_i_298_20261020_glm` | `~/ppv1_hpc/runs/t_i_298_20261020_deepseek` |
| 批准包首消费 | **PASS** | **PASS** |
| build 身份门 | `TI-BUILD-IDENTITY-PASS`（`5014fa13…`） | 同值 |
| P2-face 8 项 | **全符** | **全符** |
| `p2_face_measure.json` SHA | `ac267feff5d592154ac105925e63bfab716d4053ac7bec5a1d53d08013a2fede` | **同值** |
| 封存/停点 | 未封存；无 `stop.json` | 同 |

补充前置（只读复核，不属本轮准备动作）：`operations/preflight_calls.json` 有 **2 条**
调用记录（A `ZHIPU/GLM-5.3-Flash`、B `deepseek-v4.1-flash-1017`，均 `status=200,
ok=true`），与 CC 所述 C5 已完成一致；两份 env 文件在位且权限 `600`（未读内容）。
C6 报告 §8 里“C5 仍未执行”的记载已被后续 C5 执行取代。

## 2. 执行入口与命令

按任务书 §5.3 的等价命令，逐臂串行执行（登录节点，零模型、零网络）：

```bash
TI_WS=$HOME/ppv1_hpc; TI_CODE=$HOME/EnzymeAgent/v43cTH
TI_PY=$TI_WS/venv_v44run/bin/python
export PYTHONPATH=$TI_CODE/src PYTHONDONTWRITEBYTECODE=1
cd $TI_CODE
for arm in glm deepseek; do
  "$TI_PY" -B scripts/hpc/ti_operations.py prepare \
    --arm "$arm" --ws "$TI_WS" --code "$TI_CODE" \
    --config "$TI_CODE/scripts/hpc/ti_arm_config.json" \
    || { echo "STOP: prepare $arm"; exit 1; }
done
```

`prepare` 内部顺序（源码 `ti_operations.py::prepare`）：build 身份核对 → 科学源码两文件
SHA → 模型 ID → 批准包（四文书快照/逐件 SHA/代决来源/`no_cap_ack`）→ 预算 no-cap →
复制批准件到批根 → 写 `record/` 与 `arm_config.json` → 批根侧批准包再校验 →
调用 `probe()` 写 `p2_face_measure.json`。任一校验失败都不会落旁件。

两臂实测 stdout（逐字，见证据 `prepare_<arm>.stdout.log`）：

```json
{"files": 298, "remap_add_atom_ge1": 205, "remap_add_atom_ge2": 78, "remap_applied": 242, "specs_total": 531}
{"arm": "glm", "build_identity_fingerprint": "5014fa1398aa330b841b69146917d21809da9a4b9688ad62723021db792d330a", "n_run_inputs": 298, "prepared": "/work/home/aclhl3hbth/ppv1_hpc/batch/t_i_298_20261020_glm"}
```

```json
{"files": 298, "remap_add_atom_ge1": 205, "remap_add_atom_ge2": 78, "remap_applied": 242, "specs_total": 531}
{"arm": "deepseek", "build_identity_fingerprint": "5014fa1398aa330b841b69146917d21809da9a4b9688ad62723021db792d330a", "n_run_inputs": 298, "prepared": "/work/home/aclhl3hbth/ppv1_hpc/batch/t_i_298_20261020_deepseek"}
```

## 3. 批根产物清单

两臂批根均具备（任务要求的 6 件 + 既有 build 件）：

| 文件/目录 | GLM | DeepSeek | 说明 |
|---|---|---|---|
| `batch_manifest.json` | 有 | 有 | build 产物，两臂同 SHA `10deab6d…` |
| `build_identity.json` | 有 | 有 | 两臂同 SHA `31e8ec20…` |
| `preregistration_approval.json` | 有 | 有 | 两臂同 SHA `b631f761…` |
| `budget_no_cap.json` | 有 | 有 | 两臂同 SHA `a2a61261…` |
| `record/` | 有 | 有 | 四份批准文本快照 + `approval_manifest.json` + `ti_operations.json` |
| `p2_face_measure.json` | 有 | 有 | 两臂同 SHA `ac267fef…` |
| `arm_config.json` | 有 | 有 | 逐臂不同（arm/模型/env 字段不同，见 §4） |
| `split_manifest.json`、`run_inputs/`(298)、`reference_graphs/`(298) | 有 | 有 | build 既有；本轮只计数量，不逐件读取 |

产物 SHA：

| 文件 | GLM | DeepSeek |
|---|---|---|
| `batch_manifest.json` | `10deab6d646b6eb81f7ffb08e2b2487913326a70b8d43d560c9343a0b89fcb00` | 同值 |
| `build_identity.json` | `31e8ec205a32b9ce8c1ffd36ef825c6a5cb9613e70860ea916726ca3dccd3cb0` | 同值 |
| `preregistration_approval.json` | `b631f761d7efa85aca8807b97c2a2f98fc177ad8827da8c08a059eb2bd691a19` | 同值 |
| `budget_no_cap.json` | `a2a612614a82c08ae6e568d10deaa2f8cc04b689297dc0986e9b8b150e221f2f` | 同值 |
| `p2_face_measure.json` | `ac267feff5d592154ac105925e63bfab716d4053ac7bec5a1d53d08013a2fede` | 同值 |
| `arm_config.json` | `87f47ef1eb272b50b70157200f3d7f86ecb53d5aa1df6cd31974e8de52f35592` | `98722d812ea48816d8105004f09fe7ad73aa183c4b10c77245a01c1d8dd27216` |
| `record/approval_manifest.json` | `8597c394…` | `26a0b0d6…` |
| `record/ti_operations.json` | `365523c9…` | `8be02df6…` |

`arm_config.json` / `record/*` 逐臂不同是预期：内容含逐臂 `arm`、模型 ID、env 文件名与
生成时间；共享事实（`batch_tag=t-i-298-20261020`、`code_commit=c9c6c7a`、题卷 SHA
`9f5955d4…`、预注册文本 SHA `2e45d407…`、批准包 SHA `b631f761…`）两臂一致。

## 4. 批准包首消费校验

`prepare` 内部两次校验（源记录目录 + 批根副本），另做一次显式只读复核
（`validate_batch_approval` + `require_arm_config`）：两臂均 **PASS**。

| 核对面 | 值 | 两臂 |
|---|---|---|
| 批准 JSON SHA | `b631f761d7efa85aca8807b97c2a2f98fc177ad8827da8c08a059eb2bd691a19` | 同值（= 源记录目录） |
| `approval_status` | `preregistration_confirmed` | 同值 |
| `approval_source_kind` | `codex_delegated_cc_shijie` | 同值 |
| `approved_at` | `2026-10-20T15:49:53Z`（原值保留） | 同值 |
| `no_cap_ack` | `true` | 同值 |
| `budget_no_cap.json` | `a2a61261…`；`budget_mode=no_monetary_cap_user_decision`、`marker` 含 `2026-10-20` | 同值 |
| 脚本锁 | `0fe47c841935fd8e4642655af2b037eb52cc7cf3e65f9c6bdb26e2d8154f4641` | 同值 |
| 四份文书快照 | 任务书 `0b9b0557…`、预注册 `2e45d407…`、终审 `8344265c…`、脚本锁 `0fe47c84…` | 同值 |
| `record/approval_manifest.json` 的 `approval_package_sha256` | `b631f761…` | 同值 |
| `arm_config.approval_package_sha256` / `preregistration_text_sha256` | `b631f761…` / `2e45d407…` | 同值 |
| 逐臂模型/env | GLM `ZHIPU/GLM-5.3-Flash` + `llm.env`；DeepSeek `deepseek-v4.1-flash-1017` + `llm_ds.env` | 符合 config |

部署树脚本锁在 prepare 前另行重算：**14/14 OK，`missing=[]`，`T-I-LOCK-VERIFY PASS`**；
两臂 `verify-identity` 复跑仍 `exit=0`，`TI-BUILD-IDENTITY-PASS`，指纹 `5014fa13…`。

## 5. P2-face 全表（只读聚合）

来源：每臂 `p2_face_measure.json` 的顶层聚合字段；未读题面/金标，未外带 `by_qid`。

| 指标 | 冻结期望 | GLM 实测 | DeepSeek 实测 | 判定 |
|---|---:|---:|---:|---|
| `files` | 298 | 298 | 298 | 符 |
| `specs_total` | 531 | 531 | 531 | 符 |
| `remap_applied` | 242 | 242 | 242 | 符 |
| `remap_add_atom_ge1` | 205 | 205 | 205 | 符 |
| `remap_add_atom_ge2` | 78 | 78 | 78 | 符 |
| `questions_remap` | 151 | 151 | 151 | 符 |
| `questions_with_add` | 134 | 134 | 134 | 符 |
| `questions_with_multi_add` | 65 | 65 | 65 | 符 |

- 四项核心 **531 / 242 / 205 / 78** 与题数面 **298 / 151 / 134 / 65** 两臂逐项相同且等于期望。
- 两臂 `p2_face_measure.json` 整文件 SHA 相同：`ac267fef…`（探针产物逐字节一致）。
- 文件内 `note` 保持探针原文：`298 post-hoc；只读本批 run_inputs.plan.pools；非成绩/化学有效性证明`。
- 本轮未改探针口径、未改判据、未改池、未重跑 build。

## 6. 与 C8 的衔接（不宣布 GO）

| C8 前置 | 当前状态 |
|---|---|
| 两臂 prepare 批准件/no-cap/arm_config | **就绪**（本报告） |
| 批准包首消费 | **PASS**（本报告） |
| build 身份门 | **PASS**（两臂 `5014fa13…`） |
| C5 预检最小调用 | 已见 2 条 200 记录（只读结构核对） |
| 两模型 env | 文件在位、权限 600（未读内容） |
| 停点/封存 | 无 `stop.json`、未封存、runs 根未创建 |
| 仍需 C8 执行 | coordination 目录、monitor 作业、两臂 smoke2/smoke10 barrier 回执、run 发车 |

C8 属真实付费调用与两臂同步放行，须 CC 明确发车指令；C7 只证明“准备面已齐”。

## 7. 证据

目录：`docs/review_evidence/ti_c7_prepare_2026-10-21/`（含 `SHA256SUMS`）。

| 文件 | 内容 |
|---|---|
| `post_state.json` | 两臂批根/ runs 根、产物 SHA、8 项聚合、首消费 PASS、封存/停点、record 清单 |
| `c7_audit.py` | 上述审计脚本原文（HPC 可重跑；只读） |
| `p2_face_compare.json` | 期望 vs 两臂逐项对比 + 两臂同 SHA 判定 |
| `identity_gate.txt` | 两臂 `verify-identity` 原始输出与真实 exit code |
| `lock_and_identity.txt` | 脚本锁 14 件逐件重算 + `T-I-LOCK-VERIFY PASS` |
| `prepare_glm.stdout.log` / `prepare_deepseek.stdout.log` | prepare 执行时 stdout 逐字记录（远程 /tmp 为登录节点本地盘，跨会话不可取回，按执行会话捕获落盘） |
| `pre_state.txt` | prepare 前批根/批准包/锁状态 |
| `provenance.txt` | 证据来源、未纳入项、复算命令 |

## 8. 仍缺/未核（unknown）

| 项 | 状态 |
|---|---|
| run/score | 未执行（本轮边界） |
| smoke2/smoke10/barrier 回执 | 未执行（属 C8） |
| monitor 作业与 coordination 目录 | 未创建（属 C8） |
| 两臂 env 内容与模型连通 | 未读、未调用；仅核文件存在/权限 |
| `preflight_calls.json` 细节 | 只核 2 条/状态 200；未复算 token/费用 |
| C7 独立复核 | 本报告是实施侧准备读数，未自行宣布 GO；可交下一轮复核 |

## 9. 红线自查

- 未启动 run/score，未调用模型，未联网；
- 未读 key、env 内容、金标、题面；证据不含 `by_qid`、run_inputs、reference_graphs 内容；
- 未改 `src/`、判据、池、探针口径、批准件；未回退 TI-F1 补丁；
- 未封存、未动封存 run；未 push。