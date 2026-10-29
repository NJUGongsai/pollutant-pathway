# T-I C6 身份重锁/重绑 — 说明附录（Addendum，2026-10-21）

> **provenance：T-I C6 复审 A/B 闭合执行件（实施侧工程记录），按 CC 2026-10-21 指示起草。**
> 本文件不是批准、不是签名、不代表 CC 本人已签；C 项追认仍待 qwen3.8max 代 Codex
> 代决（见 §3 占位）。
>
> **题域标签：[298域] = 298 / RHEA 通用酶学 / 已见题（post-hoc）。** 本文件只含工程
> 身份、脚本锁与证据引用，不含真实成绩、模型调用或题面/金标内容；298 与 dev 双向不外推。
>
> **复核对象：** `docs/T_I_C6_IDENTITY_QWEN_REVIEW_2026-10-21.md` §3 A/B、§2.5；
> `docs/T_I_C6_IDENTITY_RECON_2026-10-21.md` §7；证据目录
> `docs/review_evidence/ti_c6_identity_recon_2026-10-21/`。

## 0. 本附录的效力

本附录只做两件事：**（A）补两臂身份门 raw 原件**、**（B）显式登记冻结 prose 的期望
值已被取代**，并附 C 占位与 D/E 备注。它**不修改**任何冻结 prose、批准 JSON、脚本或
`src/` 字节；凡与冻结 prose 冲突处，以本附录 + 机器面（锁 / `ti_arm_config.json` /
批准 JSON）为准。

## 1. B 项 — 冻结 prose 中的 `a24700ab…` 自 C6 起由 `1aac04da…` 取代

### 1.1 涉及位置（原字节不动）

| 文件 | 行 | 原文摘录（逐字） | 本条状态 |
|---|---:|---|---|
| `docs/T_I_PREREG_2026-10-20.md` | 77 | 「科学代码聚合身份应为 `a24700abf992fb7e9a32822268a4e407b8497ef5d1d216fc11bcfa6762ff6b85`（T-H r2 build identity 读数）」 | **已被取代** |
| `docs/TASK_T_I_LAUNCH_2026-10-20.md` | 74 | 「`a24700abf992fb7e9a32822268a4e407b8497ef5d1d216fc11bcfa6762ff6b85`（T-H r2 build identity）」 | **已被取代** |
| `docs/TASK_T_I_LAUNCH_2026-10-20.md` | 138 | 「期望身份事实（与 T-H r2 同代码/同资产）：`code_identity_aggregate_sha256=a24700ab...`」 | **已被取代** |

### 1.2 生效期望值

| 项 | 值 |
|---|---|
| 旧期望（纯 `c9c6c7a` 树） | `a24700abf992fb7e9a32822268a4e407b8497ef5d1d216fc11bcfa6762ff6b85` |
| **新期望（`c9c6c7a` + TI-F1 停派发补丁）** | `1aac04da751660ce231f5403f7304bd39afd6bc49506364eab994030a02e4519` |
| 基准 commit | `c9c6c7a7ae02b46769add09fbc2536323ce8a985` |
| 补丁 | `docs/review_evidence/ti_f1_fatal_2026-10-21/orchestrator_stop_dispatch.patch`，SHA256 `ee218f717242bd54971e3a1343eeb5f9bf597f089f0d7a61601f53b789beb152` |
| 变更文件 | `src/pathway_v43/pollutant/s5b_orchestrator.py`：纯树 `3cadb285b0ea55a6a3e418e564fd017c77f491eebd684857c77cb447ef84e684` → 补丁后 `a95bb8beee864c8815b565e97facf98ec9adafc2ca5dccf9786a7757b3385d62` |
| 科学源码（未变） | `s5b_compiler.py` `f917762bf9ec43d70b85ef3740ab7f22b866b42c06a1461ec336882eb2685dfc`；`evaluation.py` `37c092310d34d9f417234ccacd508942b3ce3edef640c73ab94022fd8dc75ad8` |

### 1.3 原因

1. TI-F1 批准的停派发补丁（`ee218f71…`）是 C1 部署条件：HPC 部署树必须含该补丁
   （打补丁后 orchestrator = `a95bb8be…`），否则 C1 不绿；补丁不得回退。
2. 代码身份聚合按 `pollutant_pathway_v1` profile 对 `src/pathway_v43/**/*.py`（87 件）
   逐件哈希后聚合；orchestrator 是被聚合的 `src/**` 文件之一，因此纯 `c9c6c7a` 树与
   「`c9c6c7a` + 补丁」树的聚合必然不同：`a24700ab…` vs `1aac04da…`。
3. 科学源码（compiler / evaluation）两件未变，见 §1.2；差异只在停派发控制流，
   不涉及池、判据、版本、题卷或判分。
4. 该结论与 qwen 代审的独立复算一致（其 §2.1–2.2 两条独立路径均得 `1aac04da…`）。

### 1.4 原 prose 字节不动

| 快照 | SHA256（本附录写作时实算） |
|---|---|
| `docs/T_I_PREREG_2026-10-20.md` | `2e45d40721168a19016e1488539e76b40ba55020a2f15a9c8b108646b84921b3` |
| `docs/TASK_T_I_LAUNCH_2026-10-20.md` | `0b9b0557b1d55d5ec77a9edb24b87d9a2532cfb4333dfecd27330d5736c7b456` |
| `docs/T_I_CODEX_FINAL_REVIEW_2026-10-20.md` | `8344265c4b1417a14cd4e6238366af9405211a0a2a52209d90205b0bc4edf39d` |

三份值与批准包绑定值、`post_state/SHA256SUMS` 一致；本附录**没有也不得**回写这三份
快照。**本附录是「prose 期望已被取代」的唯一生效说明**：C7/C8 操作者核期望时一律以
`scripts/hpc/ti_arm_config.json` 的 `identity_expectations.code_identity_aggregate_sha256
= 1aac04da…` 为准，不得再照 prose 字面的 `a24700ab…` 核对。

## 2. A 项 — 两臂身份门 raw 原件（缺口闭合）

### 2.1 重跑事实

| 项 | 值 |
|---|---|
| 时间（UTC） | 2026-10-20T20:42:35Z 起；glm 20:42:37–20:42:40Z；deepseek 20:42:40–20:42:41Z |
| 站点 | 乌镇 wuzh02，登录节点 `login03` |
| 代码根 | `/work/home/aclhl3hbth/EnzymeAgent/v43cTH`（**非 git checkout**；`remote HEAD = NO_GIT_DIR`，`source_commit` 取 `arm_config` = `c9c6c7a7ae02b46769add09fbc2536323ce8a985`） |
| Python | `/work/home/aclhl3hbth/ppv1_hpc/venv_v44run/bin/python`（Python 3.11.15，rdkit 2026.03.5） |
| 命令 | `cd ~/EnzymeAgent/v43cTH && PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 ~/ppv1_hpc/venv_v44run/bin/python -B scripts/hpc/ti_operations.py verify-identity --arm <glm\|deepseek>` |
| 锁 SHA | `0fe47c841935fd8e4642655af2b037eb52cc7cf3e65f9c6bdb26e2d8154f4641`（HPC 批准记录目录实测） |
| 批准 JSON SHA | `b631f761d7efa85aca8807b97c2a2f98fc177ad8827da8c08a059eb2bd691a19`（实测） |
| 代码件 SHA | `ti_operations.py` `931966a8…dfa7`；`ti_arm_config.json` `8dab7ebc…7695`；orchestrator（补丁后）`a95bb8be…5d62` |

命令语义备注：`verify-identity` 接受 `--arm`，但实现按 `REQUIRED_ARMS` 在**每次调用内
同时校验两臂**（manifest/fingerprint/逐题 `run_input_sha256` 同值门）；两次调用是独立
进程，stdout 逐字相同。这解释了为何两臂 raw 输出完全一致，不影响门的意义。

### 2.2 四项读数（两臂均命中）

| 读数 | 值 | glm | deepseek |
|---|---|---|---|
| gate | `TI-BUILD-IDENTITY-PASS` | 命中 | 命中 |
| build_identity_fingerprint | `5014fa1398aa330b841b69146917d21809da9a4b9688ad62723021db792d330a` | 命中 | 命中 |
| manifest_sha256 | `10deab6d646b6eb81f7ffb08e2b2487913326a70b8d43d560c9343a0b89fcb00` | 命中 | 命中 |
| n_run_inputs | `298` | 命中 | 命中 |
| exit code | `0` | 0 | 0 |
| stderr | 空 | 空 | 空 |

两臂 `build_identity.json` 实测 SHA256 同为 `31e8ec205a32b9ce8c1ffd36ef825c6a5cb9613e70860ea916726ca3dccd3cb0`；
`batch_manifest.json` 实测同为 `10deab6d…cb00`（只登记哈希与大小，**未复制题面内容**）。
逐项断言见 `raw_gate/assertions_check.txt`（OVERALL PASS）。

### 2.3 落盘位置

| 位置 | 内容 |
|---|---|
| HPC | `~/ppv1_hpc/operations/t_i_c6_identity_raw_20261021/`：`glm.stdout.txt`、`glm.stderr.txt`、`glm.exitcode.txt`、`glm.command.txt`、`glm.timing.txt`，deepseek 同名五件，`meta.txt` |
| 本地 | `docs/review_evidence/ti_c6_identity_recon_2026-10-21/raw_gate/`：同上 11 件 + `assertions_check.txt` |

### 2.4 引用修正

原 `docs/T_I_C6_IDENTITY_RECON_2026-10-21.md` §7 与 `hpc_sync.json` 引用的
`hpc_verify_identity.txt` **从未落盘**（qwen §2.5 缺口）。本轮：

- 实际 raw 文件路径为 `raw_gate/glm.*` 与 `raw_gate/deepseek.*`；`hpc_sync.json` 的
  `verify_identity.evidence` 已改为实际文件清单，并补 `recheck_*`、`arm_flag_note`、
  `remote_git_head`、`lock_sha256`、`raw_gate_sha256` 字段；
- `hpc_sync.json` 因本轮补注字节已变，其 `SHA256SUMS` 行由 `494b88c7…` 刷新为新值
  （新值见 `SHA256SUMS`）；其余既有条目未动；
- 重锁报告本身（`T_I_C6_IDENTITY_RECON_2026-10-21.md`）是上一轮冻结记录，**不回写**；
  其 §7 的旧引用由本附录 §2.3–2.4 取代。

## 3. C 项占位 — 重锁授权归属追认（未签）

> **C 项状态：待 qwen3.8max 代 Codex 追认（CC 2026-10-21 已授权代决；CC 后置复核）。**

本条只登记「移动预注册冻结期望值（`a24700ab…` → `1aac04da…`）」这一动作待追认，
**不构成 CC 本人签署、不构成 Codex 正链裁定、不构成新批准**。追认文本落定后，应以
追加方式写入本附录或批准包外新件；在追认完成前，C8 付费 smoke / 任何 run/score/full
仍按 qwen 代审 §1 保持停点。

## 4. D 备注 — 复算口径写准（不阻塞）

`aggregate_recompute.json` 的 `aggregate_algorithm` 字面写作 `src/pathway_v43/**/*.py`，
但 `run_identity.code_identity` 的 rel 键**相对 `src/`**，实际形如
`pathway_v43/pollutant/s5b_compiler.py`（即 `pathway_v43/...`），不是
`src/pathway_v43/...`。照字面拼 `src/` 前缀复算会得到不同聚合（qwen §3 D 已踩到）。
哈希值本身无误；为不改变既有证据字节，本轮**只在本附录更正口径**，不回写
`aggregate_recompute.json`。

## 5. E 备注 — 部署但未入锁的操作件（已知非阻塞）

`scripts/hpc/chain13_monitor.sh` 在 HPC 部署清单中（SHA256
`a006c61c7aa4bd1dada9b8667dd1525eb6e210c7ee12fd040e94a380b3ede82c`），但**不在 14 件
脚本锁内**；这是先前既有状态，非本轮引入。该件不进入 `code_identity`（聚合只覆盖
`src/pathway_v43/**/*.py`），不影响两臂身份门。登记为已知非阻塞项；是否在 C8 使用
monitor 前纳入锁，归 CC 决定（qwen §3 E 同口径）。

## 6. 边界自查

- 未执行 prepare/run/score，未调用模型；`verify-identity` 为只读门（无写入、无
  字节码落盘：`-B` + `PYTHONDONTWRITEBYTECODE=1`）；
- 未读 key/env 内容、金标或题面；只登记哈希、大小、时间；
- 未改 `src/`、`tests/`、`scripts/`、冻结 prose、批准 JSON 字节；未 push；
- 本附录与 raw 输出已纳入证据目录 `SHA256SUMS`（追加式，仅 `hpc_sync.json` 一行随
  其内容变更刷新）。

## 7. 交 QwenReviewer 追认所需条件核对

| 条件 | 状态 |
|---|---|
| 两臂 raw stdout/stderr/exit code/命令/时间落盘（本地 + HPC） | 已闭合（§2） |
| 四项读数两臂命中 | 已闭合（§2.2，`assertions_check.txt` PASS） |
| 缺失引用 `hpc_verify_identity.txt` 修复 | 已闭合（§2.4） |
| prose 期望被取代的显式登记 | 已闭合（§1） |
| C 项追认占位（不冒充 CC） | 已留位（§3） |
| D/E 备注 | 已登记（§4/§5） |

结论：A/B 已具备交 QwenReviewer 追认（C 项代决）的条件；本附录不自行宣布 C 完成。