# T-I C6 身份期望重锁/重绑报告（2026-10-21）

> **题域标签：[298域] = 298 / RHEA 通用酶学 / 已见题（post-hoc）。** 本报告只含
> 工程身份、脚本锁与批准包重绑，不含真实成绩、真实模型调用或题面内容；298 与 dev
> 双向不外推。
>
> **状态：C6 两臂 build 身份门 PASS（`TI-BUILD-IDENTITY-PASS`，两臂 exit 0）。**
> 停派发补丁不回退；冻结期望由纯 `c9c6c7a` 聚合改为补丁后实测聚合。
> **边界：** 未执行 prepare/run/score；未调用模型；未读 key/env 内容/金标/题面；
> 未改 `src/` 科学代码；未 push。当前仍 **NO-GO**（C5、C7、C8 未完成）。

## 1. 结论

C6 两臂 build 已成功、产物逐字相同，但 `verify-identity` 在
`code_identity_aggregate_sha256` 上失败：冻结期望是纯 `c9c6c7a` 的
`a24700ab…`，实际是“`c9c6c7a` + 已批准停派发补丁”的 `1aac04da…`。
按 TI-F1 要求补丁不得回退，因此本轮做**身份期望重锁**：

| 项 | 旧 | 新 |
|---|---|---|
| `code_identity_aggregate_sha256` | `a24700abf992fb7e9a32822268a4e407b8497ef5d1d216fc11bcfa6762ff6b85` | `1aac04da751660ce231f5403f7304bd39afd6bc49506364eab994030a02e4519` |
| 脚本锁 SHA | `f0a43420003ba130fbf48ae41527abb991cfd796738e6650ba2e973110625f46` | `0fe47c841935fd8e4642655af2b037eb52cc7cf3e65f9c6bdb26e2d8154f4641` |
| 批准 JSON SHA | `190e42a5f0178fa9b18336da9881cb09b7c3f191b82fdff9d5aacb8da4a50ae7` | `b631f761d7efa85aca8807b97c2a2f98fc177ad8827da8c08a059eb2bd691a19` |
| 两臂 build 指纹 | 未变（补丁后） | `5014fa1398aa330b841b69146917d21809da9a4b9688ad62723021db792d330a` |

## 2. 只读复核：部署树 vs `c9c6c7a`

基线 = `c9c6c7a7ae02b46769add09fbc2536323ce8a985`。HPC 部署树
`~/EnzymeAgent/v43cTH` 共 151 个文件（排除代码根下的作业日志），逐件 SHA256 对比：

| 类别 | 数量 | 说明 |
|---|---:|---|
| 与 `c9c6c7a` 逐字相同 | 138 | 含全部科学源码（除 orchestrator） |
| 仅 `c9c6c7a` 中不存在（T-I untracked 操作件） | 11 | T-I 任务书/预注册/实施准备 + `ti_operations.py` 等，按锁核身份 |
| 两边都存在但不同 | 2 | 见下 |

差异 2 件：

| 文件 | 部署 SHA | `c9c6c7a` SHA | 定性 |
|---|---|---|---|
| `src/pathway_v43/pollutant/s5b_orchestrator.py` | `a95bb8be…3385d62` | `3cadb285…ef84e684` | **已批准 TI-F1 停派发补丁**（补丁 SHA `ee218f71…beb152`） |
| `docs/T_H_LAUNCH_TASK_2026-10-20.md` | `b3984bbe…d5e25` | `b8b8f5d6…e14f9` | 非锁历史 T-H 任务书；HPC 副本是 `abbfa39`（`96b68b0` 晨间附记之前），不影响代码身份/锁 |

**代码与科学面结论：** `src/**` 唯一差异就是该补丁；补丁对纯树
`git apply`/`patch` 干净、反向补丁可还原到 `3cadb285…`；补丁后 orchestrator
`a95bb8be…` 与 HPC 部署实测一致。科学源码两件未变：

| 科学源码 | SHA256 |
|---|---|
| `src/pathway_v43/pollutant/s5b_compiler.py` | `f917762bf9ec43d70b85ef3740ab7f22b866b42c06a1461ec336882eb2685dfc` |
| `src/pathway_v43/pollutant/evaluation.py` | `37c092310d34d9f417234ccacd508942b3ce3edef640c73ab94022fd8dc75ad8` |

聚合复算（`src/pathway_v43/**/*.py` 共 87 件，算法与
`run_identity.code_identity(PROFILE_POLLUTANT_PATHWAY_V1)` 相同）：

| 树 | orchestrator | 聚合 |
|---|---|---|
| 纯 `c9c6c7a` | `3cadb285…` | `a24700ab…`（与冻结期望一致） |
| `c9c6c7a` + 补丁 | `a95bb8be…` | `1aac04da…`（与两臂 build 实测一致） |

> 说明：本地仓 HEAD 已到 `11aeeaf`（P0b/D-6），其中
> `s5b_compiler.py` = `58cf3dc9…`；T-I 发车冻结在 `c9c6c7a`，部署与锁仍用
> `f917762b…`。这是仓 HEAD 与 T-I 部署位的既有分叉，本轮未改任何本地
> `src/` 文件；锁按部署位计算，不以 HEAD 字节替换冻结科学源码。

## 3. 两臂 C6 build 读数

| 臂 | 作业 | 日志 | 结果 | 批根 |
|---|---|---|---|---|
| GLM | `47002738` | `ti_build_47002738.out` | `TI-BUILD-PASS`（298/298，题卷 SHA `9f5955d4…`） | `batch/t_i_298_20261020_glm` |
| DeepSeek | `47002742` | `ti_build_47002742.out` | `TI-BUILD-PASS`（298/298，题卷 SHA `9f5955d4…`） | `batch/t_i_298_20261020_deepseek` |

两臂 `build_identity.json` 与 `batch_manifest.json` 逐字节相同：

| 文件 | 两臂同值 SHA256 |
|---|---|
| `build_identity.json` | `31e8ec205a32b9ce8c1ffd36ef825c6a5cb9613e70860ea916726ca3dccd3cb0` |
| `batch_manifest.json` | `10deab6d646b6eb81f7ffb08e2b2487913326a70b8d43d560c9343a0b89fcb00` |

## 4. 脚本锁重算

`docs/T_I_SCRIPT_LOCK_2026-10-20.json` 仍为 14 件，`missing=[]`；逐件重算后
**只有 `scripts/hpc/ti_arm_config.json` 变化**（`99ac34bb…` → `8dab7ebc…`），
其余 13 件逐字不变。锁内新增：

- `relock`：reason、previous_lock_sha256、patch SHA、old/new aggregate、changed_files；
- `note`：说明本轮只随已批准补丁更新期望，14/14 与 HPC 部署树一致。

一致性：

| 核对面 | 结果 |
|---|---|
| 规范部署树（`c9c6c7a` + T-I untracked 件 + 补丁） | **14/14 吻合** |
| HPC 部署树（`verify_lock.py` 实测） | **14/14 吻合**，`orchestrator.patched_match=true`，`stop_check` 出现 10 次 |
| 本地仓工作树 | 13/14；唯一不符是 `s5b_compiler.py`（HEAD `58cf3dc9…` vs 冻结部署 `f917762b…`，见 §2 说明） |

新锁 SHA256：`0fe47c841935fd8e4642655af2b037eb52cc7cf3e65f9c6bdb26e2d8154f4641`。

## 5. 批准包重绑

本地包 `docs/T_I_APPROVAL_PACKAGE_2026-10-20/` 与 HPC 记录目录
`~/ppv1_hpc/operations/t_i_approved_record_20261020/` 同步：

| 快照 | SHA256 | 变化 |
|---|---|---|
| `TASK_T_I_LAUNCH_2026-10-20.md` | `0b9b0557…6c7b456` | 原字节不变 |
| `T_I_PREREG_2026-10-20.md` | `2e45d407…84921b3` | 原字节不变 |
| `T_I_CODEX_FINAL_REVIEW_2026-10-20.md` | `8344265c…edf39d` | 原字节不变 |
| `T_I_SCRIPT_LOCK_2026-10-20.json` | `0fe47c84…54f4641` | 按新 14 件重绑 |
| `preregistration_approval.json` | `b631f761…bd691a19` | 新增 `identity_reconciliation`，更新锁绑定 |
| `budget_no_cap.json` | `a2a61261…e221f2f` | 不变 |

批准 JSON 保留：`approval_basis`、`approval_source`、
`approval_source_kind=codex_delegated_cc_shijie`、`approved_at=2026-10-20T15:49:53Z`、
`no_cap_ack=true`、`budget_mode`、`user_decision_date`、授权链。**未伪填 CC 本人，
不是新批准/代签**；`identity_reconciliation` 只登记 old/new aggregate、补丁 SHA、
补丁后文件 SHA、两臂 build 指纹、old/new 锁 SHA、时间与理由。

`SHA256SUMS`（本地/HPC 均 5/5 OK）与 `SHA256SUMS.external`
（HPC 7/7 OK，含 `budget_no_cap.json` 与本清单自身）已重建；外部清单 SHA256：
`0b44b19737570ae917916cda7e5c64cea8cced7bda8b1a3562a143fd4b2f6945`。
HPC 侧旧锁/旧批准/旧清单均以 `.bak.20261021_c6` 备份保留；旧 arm_config
备份移到 `operations/t_i_c1_deploy_20261021/`。C1 的
`deploy_manifest.json` 是当轮历史快照，保留旧锁/旧 arm_config 读数，不回写；
C6 重绑以本报告 §4–§5 与证据为准。

## 6. 身份门结果

| 阶段 | 命令 | 结果 |
|---|---|---|
| 重锁前 | `ti_operations.py verify-identity --arm glm --ws ~/ppv1_hpc` | **FAIL**（exit 1）：expected `a24700ab…` actual `1aac04da…` |
| 重锁后 | 同上，`--arm glm` | **PASS**（exit 0） |
| 重锁后 | 同上，`--arm deepseek` | **PASS**（exit 0） |

两次 PASS 输出一致：

```json
{"gate": "TI-BUILD-IDENTITY-PASS",
 "batch_tag": "t-i-298-20261020",
 "build_identity_fingerprint": "5014fa1398aa330b841b69146917d21809da9a4b9688ad62723021db792d330a",
 "manifest_sha256": "10deab6d646b6eb81f7ffb08e2b2487913326a70b8d43d560c9343a0b89fcb00",
 "n_run_inputs": 298}
```

HPC 批准包校验 `approval-package` exit 0；`verify_lock.py` exit 0
（14/14、`missing=[]`、orchestrator patched）。

## 7. 证据

目录：`docs/review_evidence/ti_c6_identity_recon_2026-10-21/`（含 `SHA256SUMS`）。

| 文件 | 内容 |
|---|---|
| `pre_state/` | 旧 arm_config/旧锁/旧批准 JSON/旧 SHA256SUMS/旧外部清单/重锁前失败输出 |
| `post_state/` | 新 arm_config/新锁/新批准 JSON/新 SHA256SUMS/HPC 外部清单 |
| `aggregate_recompute.json` | 纯树/补丁后聚合、补丁正反向、科学源码、两臂 build 身份 |
| `deploy_diff.json` / `.txt` | 部署树 vs `c9c6c7a` 逐件差异 |
| `lock_relock.json` | 14 件 old/new、规范树/HPC/本地工作树核对 |
| `approval_rebind.json` | 批准包 old/new、保留字段、校验结果 |
| `hpc_sync.json` | HPC 安装/备份/两臂 gate/外部清单 |
| `hpc_verify_identity.txt` | 两臂 gate 原始输出 |
| `hpc_verify_lock.json`、`hpc_approval_validation.json` | HPC 独立校验读数 |
| `checksums_verify.txt` | 本地包 5/5、HPC 包 5/5、外部 7/7 |
| `ti_build_47002738.out`、`ti_build_47002742.out` | C6 build 日志 |

## 8. 仍缺/未核（unknown）

| 项 | 状态 |
|---|---|
| C5 两臂最小真实调用 | 仍未执行（此前 C3 首跑失败后停；C3 重试已 `NETCHECK-PASS`，但不替代 C5） |
| C7 prepare 与 P2-face 探针 | **未执行**；`files=298`/`specs_total=531` 等冻结读数无现场读数 |
| C8 协调/monitor/双臂 smoke barrier/回执 | **未执行**；无真实 monitor 作业与 smoke2/smoke10 回执 |
| 本地 HEAD 与 T-I 部署位 | `11aeeaf` 的 `s5b_compiler.py` 与冻结 `c9c6c7a` 不同；T-I 身份以部署位为准，未改本地科学源码 |
| 非锁历史 T-H 任务书 | HPC 仍是 `abbfa39` 旧版；不进入 14 件锁、不影响代码身份；本轮未改 |
| 旧纯树 build 指纹 | 只登记旧聚合 `a24700ab…`；未用新 build 反造旧指纹 |
| C1 部署清单 | `t_i_c1_deploy_20261021/deploy_manifest.json` 是当轮历史快照（旧锁/旧 arm_config 读数），未回写；C6 以新锁/新批准 JSON 为准 |
| 本轮重锁的独立复核 | 本报告是实施侧工程重绑，未自行宣布 GO；候选下一轮 Codex/Qwen 复核可据本报告与证据复算 |

## 9. 红线自查

- 未回退停派发补丁；未改 `src/` 科学代码；未改池/判据/版本；
- 未执行 prepare/run/score；未调用模型；未读 key、env 内容、金标或题面；
- 未 push；批准来源仍为 Codex 代 CC/师姐，`approved_at` 原值保留，未伪填 CC。