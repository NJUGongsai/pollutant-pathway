# P2 正式 seed build + build-copy + prepare（2026-10-21）

> **题域标签：[298 域] = RHEA 通用酶学 / 已见题（post-hoc）。** 本报告只覆盖 build/prepare；
> **没有任何 run/test/score 指标**，不向 dev 或其他题域外推。
>
> **结论：正式 seed build 成功；两臂字节级复制与 §5.2 身份门通过；两臂 prepare rc=0；
> P2-face 八项与 B3 口径逐项一致，两臂相同。零模型、未 run/test/score。**
> 但 `launch --phase build` 存在一个已绕过的实施缺陷（见 §2.1），且 B4 作业在外部被取消
> （见 §5），均需 CC/评审知悉。

## 0. 速览

| 项 | 结果 |
|---|---|
| 批准包复核 | `approval-package` rc=0；四文书 SHA 与脚本锁 `8ba2cbec…` 一致 |
| 正式 seed build | job `47084480`，`COMPLETED 0:0`；job elapsed **01:04:00**；seed build span **63m47s** |
| build-gate | `BUILD-GATE-OK: n=298 sha=9f5955d4… entries_with_cosub_labels=298/298` |
| 298 qid | seed **298** run_inputs；两臂各 **298**；逐文件对 `(qid, run_input_sha256)` 全等 |
| 两臂 manifest | `837d38f55cf5cbe6806f9e0a7d1f1bc56f0a9b22416d99f41a06e7ac7af45212`（三根相同） |
| 两臂指纹 | `76858eb41c5e5ce46c093ea1fdd69e7d5c9bff3a3a1223ec65b1574f49228ab9`（逐字相同） |
| §5.2 身份门 | `P2-BUILD-IDENTITY-PASS`；n=298；code agg `cfd74067…`；RDKit `2026.03.5` |
| build-copy | `P2-BUILD-COPY-PASS`；seed manifest `837d38f5…` |
| prepare | v1card/v2card 均 rc=0；fingerprint 均 `76858eb4…` |
| P2-face | 八项 **全符**：298 / 531 / 242 / 205 / 78 / 151 / 134 / 65；两臂同 SHA `ac267fef…` |
| 模型/付费 | 零模型、零网络、无 run/test/score；runs 根未创建 |
| 主要偏差 | launch 未导出 `QUESTIONS/V3_CODE_ROOT`，首投写错臂根；已隔离并绕过（§2.1） |

## 1. 批准包复核

命令：

```bash
cd ~/EnzymeAgent/v43cP2
PYTHONPATH=$PWD/src PYTHONDONTWRITEBYTECODE=1 \
~/ppv1_hpc/venv_v44run/bin/python -B scripts/hpc/p2_operations.py approval-package \
  --config scripts/hpc/p2_arm_config.json \
  --record-dir ~/ppv1_hpc/operations/p2_approved_record_20261021 \
  --ws ~/ppv1_hpc
```

`rc=0`。四文书与配置路径一致，记录目录 `SHA256SUMS` 五项全部 OK：

| 文书 | SHA-256 |
|---|---|
| `docs/T_P2_PREREG_FULL_V2_2026-10-21.md` | `862425160f4bcaf3bafe933c39c02c45e1d44412b04ad6332d7d0b1647ca3ce5` |
| `docs/TASK_P2_FULL_V2_LAUNCH_2026-10-21.md` | `01b1896f7b3312b1c05671123eec35020b96c4a579d8ef7ccaf858600de9d092` |
| `docs/T_P2_V2_CHEM_REVIEW_ROUND3_2026-10-21.md` | `1bea16b249105bfc068caee39ece7e81936622f1536ab00cddfe844b3e7f0f81` |
| `docs/T_P2_SCRIPT_LOCK_2026-10-21.json` | `8ba2cbec554b8a72c0f52a1e88d9fed5e19eb8c947e8d5a28ff70da90769920d` |

| 其他身份 | 值 |
|---|---|
| 批准 JSON 磁盘 SHA | `ccdb9d14821ecb53c93df47aa6731739cd7c9b8f699d68741528bcf37975e46c` |
| 批准 JSON 规范自哈希 | `bd42c4d1770e583a60c98be8bbc3bcf50011871823eb907da2f69c68202d3fcb`（排除自身/算法说明键） |
| `approval_status` | `preregistration_confirmed` |
| `batch_tag` | `p2-298-20261021` |
| 模型 / env | `deepseek-v4.1-flash-1017` / `llm_ds.env`（两臂同值） |
| 配置 SHA | `c4789ac8fd44bea78e58782852c3da4a9bd82e0941da36c89080a056dfcd2028` |
| 脚本锁 schema / source_commit / missing | `p2-script-lock-1` / `11aeeaf…` / `[]` |

**偏差：** 批准记录目录原本**缺 `budget_no_cap.json`**，`prepare` 首次因此 rc=1。已用官方
`p2_operations.py no-cap --arm v1card --create` 生成（schema `v44-budget-no-cap-1`，marker
`no_monetary_cap_user_decision_2026-10-21`，SHA `3e8d08b608a0a1c1698488133e8a8e882bf58b525147e8382d2e1a0aefe2cd6e`），
并复制到 arm 批根；随后 `prepare` rc=0。记录目录原 `SHA256SUMS` 仍五项全 OK（该文件不在原清单内）。

## 2. 正式 seed build

### 2.1 首次 `launch` 失败与恢复（重要实施缺陷）

第一次按指定入口提交：

```bash
python -B scripts/hpc/p2_operations.py launch --phase build --arm v1card ...
```

作业 `47083951` 于 `2026-10-21T20:50:45+08:00` 启动，13m05s 后被本会话取消。现场：

| 项 | 事实 |
|---|---|
| 作业 | `47083951`，`CANCELLED`，elapsed `00:13:05` |
| 写入位置 | **`p2_298_20261021_v1card`**（臂根），83 个文件；seed 根未创建 |
| 根因 | `launch` 的环境只导出 `WS/CODE/BATCH_ROOT/BATCH_TAG/ARM/...`，**未导出 `QUESTIONS` / `V3_CODE_ROOT`**；`sbatch_p2_build.sh` 的 `if [ -z BATCH_TAG ] || [ -z QUESTIONS ] || [ -z V3_CODE_ROOT ]` 因此进入 `arm-env` 分支，`eval "$ARM_ENV"` 把 `BATCH_ROOT` 覆盖成臂根。内部 `build-copy` 随后会因 `seed == arm` 直接拒（`臂根不得等于 seed 根`） |
| 处置 | 取消本会话自己的作业；把 83 文件的部分臂根整体移到 `batch/_quarantine_p2_47083951_v1card_partial_20261021`（未删除） |
| 修复方式 | 提交前导出 `QUESTIONS` 与 `V3_CODE_ROOT`；因 `seed_batch_root()` 用 `batch_tag` 生成连字符路径，创建真实 seed 目录 `p2_298_20261021_seed`，并建 `p2-298-20261021_seed` → 真实目录的符号链接；`launch ... --resume` 重投 |
| 二次作业 | **`47084480`**，`COMPLETED 0:0`，`P2-BUILD-PASS` |
| 源码修改 | **无**；配置/脚本锁未改 |

> 这是操作链缺陷，不影响本次科学产物：真实 seed 根仍是冻结的 `p2_298_20261021_seed`，
> 两臂根为 `p2_298_20261021_v1card` / `p2_298_20261021_v2card`。ops 状态文件记录的
> `batch_root` 是连字符符号链接路径。建议后续另行授权修复 `launch`（导出
> `QUESTIONS/V3_CODE_ROOT`，或改 `sbatch_p2_build.sh` 的 guard），不要在发车前静默依赖本次绕过。

### 2.2 命令链与参数

`launch --phase build --arm v1card --resume` 提交 `scripts/hpc/sbatch_p2_build.sh`；脚本内部：

1. `p2_operations.py prebuild`（新批根非空/旧批/封存即拒）；
2. `s5b_cli build --provider-kind real --pool-mode template --recorded-source --max-pool 8 --pool-threshold 0.45 --v3-code-root … --assets-root …`；
3. `chain13_gate.py build-gate`；
4. `p2_operations.py build-copy`（seed → 两臂 + §5.2 身份门）。

作业资源：`wzhcnormal`，8 CPU，16G，4h；节点 `a02r2n12`。build 阶段不装配模型、不读 env、
不发网络请求；日志无 model/API/HTTP/DashScope 标记。

### 2.3 墙钟

| 计时 | 值 |
|---|---|
| job `47084480` 起止 | `2026-10-21T21:04:22+08:00` → `22:08:22+08:00` |
| job elapsed（sacct） | **01:04:00**（3840s） |
| seed build span（job start → `batch_manifest.json` mtime `22:08:09`） | **3827s = 63m47s** |
| build-gate + 内部 build-copy | 约 13s（至 job 结束） |
| 诊断 build 对照 | 3813s（63m33s）；本次 **+14s** |
| 61–64 分钟基线 | 3706–3814s；本次 3827s，比基线最慢 **+13s** |
| 队列等待 | 无；提交后立即在 `a02r2n12` 启动 |
| 资源竞争 | B4 full 两作业与 seed build **重叠 15m36s**（21:04:22–21:19:58，见 §5）；之后无 B4 |

> 差异只记录不归因：B4 竞争、节点差异、首次在新批根 build 都可能影响；池/阈值/来源/
> 编译参数与冻结面一致。

### 2.4 build-gate、指纹与产物

```text
BUILD-GATE-OK: n=298 sha=9f5955d4… entries_with_cosub_labels=298/298
```

| 项 | 值 |
|---|---|
| seed 根（真实） | `/work/home/aclhl3hbth/ppv1_hpc/batch/p2_298_20261021_seed` |
| seed 根（ops 记录/符号链接） | `/work/home/aclhl3hbth/ppv1_hpc/batch/p2-298-20261021_seed` |
| `batch_manifest.json` SHA | `837d38f55cf5cbe6806f9e0a7d1f1bc56f0a9b22416d99f41a06e7ac7af45212` |
| `build_identity.json` SHA | `dc61db1bef28bac5288784344aaa4e89ce2ca2daacf667e0032a87866ebf0781` |
| `split_manifest.json` SHA | `4e43015ab652d657a33d15156b9ee6c2f1baefde0d997f5cb6f6345e10ee7e7f` |
| `build_identity_fingerprint` | `76858eb41c5e5ce46c093ea1fdd69e7d5c9bff3a3a1223ec65b1574f49228ab9` |
| `code_identity_aggregate_sha256` | `cfd7406709b60344104c17513a0616b59380b971d5ede0d0909bc4f5c1322f07` |
| compiler / pool / source / retrieval | `s5b-compiler-6` / `s5b-pool-policy-9` / `s5b-recorded-source-4` / `s5b-corpus-retrieval-6` |
| formnorm / route | `record-side-formnorm-1`（param `a7bcb788…`）/ `s5b-analog-route-f1f4-1` |
| RDKit | `2026.03.5` |
| run_inputs | **298**；唯一 qid **298** |
| seed 文件数 | **599**（298 run_inputs + 298 reference_graphs + manifest/identity/split） |
| `asset_identity.manifest_sha256` | `ac9b97b872c9666eebbe32b42c626997aca34438ade17d7bbf36a8154b848e6c` |
| 题卷 SHA | `9f5955d418c2f3876f13cdc9bebea46a1d545d037b182fa5089f56293ff9211c`（298 行） |

## 3. build-copy 与 §5.2 身份门

seed build 的同一作业内已执行一次 `build-copy`；随后又显式重跑一次（幂等，既有相同文件保留）：

```text
{"gate": "P2-BUILD-COPY-PASS",
 "seed_manifest_sha256": "837d38f55cf5cbe6806f9e0a7d1f1bc56f0a9b22416d99f41a06e7ac7af45212",
 "seed_root": "/work/home/aclhl3hbth/ppv1_hpc/batch/p2_298_20261021_seed"}
```

`verify-identity` rc=0：

```json
{"gate":"P2-BUILD-IDENTITY-PASS","batch_tag":"p2-298-20261021",
 "build_identity_fingerprint":"76858eb41c5e5ce46c093ea1fdd69e7d5c9bff3a3a1223ec65b1574f49228ab9",
 "n_run_inputs":298,
 "manifest_sha256":"837d38f55cf5cbe6806f9e0a7d1f1bc56f0a9b22416d99f41a06e7ac7af45212",
 "code_identity_aggregate_sha256":"cfd7406709b60344104c17513a0616b59380b971d5ede0d0909bc4f5c1322f07",
 "rdkit_version":"2026.03.5"}
```

| §5.2 门 | 结果 |
|---|---|
| 两臂 `batch_manifest.json` 字节 SHA 相同 | 是：`837d38f5…`（seed/v1/v2 三根相同） |
| 两臂 `build_identity.json` 字节 SHA 相同 | 是：`dc61db1b…`（三根相同） |
| 两臂 `build_identity_fingerprint` 逐字相同 | 是：`76858eb4…` |
| 298 条 `(qid, run_input_sha256)` 全等 | 是；三根 digest 均 `b7d8e9309ff66b52405266aa80233e8f2fe78ecbdce13ab46b777c0ee69836f1` |
| `manifest.build_identity_ref` 与 identity 一致 | 是（`check_build_identity` 逐臂复算通过） |
| 代码聚合 = P2 实测且非旧 T-I | 是：`cfd74067…`，不在 `1aac04da…`/`a24700ab…` |
| RDKit 两臂同值 | 是：`2026.03.5` |
| 复制白名单 | 臂根顶层无 `orchestration.json` / `gate` / `cases` / `profile_policy.json` / `batch_report.json` / `progress.json`（`forbidden_present=[]`） |

| 批根 | 文件数 | 顶层 |
|---|---|---|
| seed | 599 | manifest / identity / split / reference_graphs / run_inputs |
| v1card | 609 | 上述 + `arm_config.json`、`budget_no_cap.json`、`p2_face_measure.json`、`preregistration_approval.json`、`record/` |
| v2card | 609 | 同 v1card（内容按臂差异） |

## 4. prepare 与 P2-face

`prepare` 两臂均 rc=0；`build_identity_fingerprint` 均 `76858eb4…`，`n_run_inputs=298`：

| 臂 | role | evidence_card_version | 模型 | env | prepare rc |
|---|---|---|---|---|---|
| v1card | control | `v1card` | `deepseek-v4.1-flash-1017` | `llm_ds.env` | 0 |
| v2card | treatment | `v2` | `deepseek-v4.1-flash-1017` | `llm_ds.env` | 0 |

P2-face 八项（`probe` 在 prepare 内自动执行；两臂分别独立输出）：

| 指标 | 期望（B3 口径） | v1card | v2card | 判定 |
|---|---:|---:|---:|---|
| `files` | 298 | 298 | 298 | PASS |
| `specs_total` | 531 | 531 | 531 | PASS |
| `remap_applied` | 242 | 242 | 242 | PASS |
| `remap_add_atom_ge1` | 205 | 205 | 205 | PASS |
| `remap_add_atom_ge2` | 78 | 78 | 78 | PASS |
| `questions_remap` | 151 | 151 | 151 | PASS |
| `questions_with_add` | 134 | 134 | 134 | PASS |
| `questions_with_multi_add` | 65 | 65 | 65 | PASS |

两臂 `p2_face_measure.json` SHA 均
`ac267feff5d592154ac105925e63bfab716d4053ac7bec5a1d53d08013a2fede`（逐字节相同）。

prepare 写入的批准旁件与源记录一致：

| 臂 | `record/p2_operations.json` 原批准 SHA | `record/approval_manifest.json` 文书 |
|---|---|---|
| v1card | `ccdb9d14…` | 四文书快照 SHA 与批准包一致 |
| v2card | `ccdb9d14…` | 四文书快照 SHA 与批准包一致 |

## 5. 保护面、B4 观察与零模型

| 检查 | 结果 |
|---|---|
| 本会话写 `v43cTH` / `v43c14` | **无**；`v43cTH` mtime 保持 `20:40:32`，`v43c14` 保持 `2026-10-16` |
| 本会话写 T-I/20261020/B2/B3 批根/runs/stop | **无**；前后 mtime 逐项相同 |
| P2 runs 根 | **未创建**（seed/v1/v2 三处均不存在） |
| run/test/score | **未执行** |
| 模型/DashScope/env/key | 未调用、未读；build/prepare 零模型 |
| 金标/题面/reference_graphs | 本会话未读题面正文；题卷只做 SHA/行数；reference_graphs 只计数/列目录，未读内容 |
| B4 作业 | **外部取消**：`47084122`/`47084123` 于 `21:19:58` 被取消（`CANCELLED+`）；B4 test `47083814` 已于 `20:56:25` 完成。**本会话只对 `47083951` 执行过 `scancel`（21:03:50）**，未对 B4 作业执行任何取消；B4 批根/runs 的 mtime `21:19:49/57` 也来自外部动作。事实如此记录，不推断取消者 |

> B4 取消发生在本次 build 进行中（build 21:04:22 起，B4 21:19:58 停）；B4 full 与本次
> build **重叠 15m36s**，共用 `wzhcnormal` 分区。该事件不由本会话发起，也未收到 B4 会话的
> 停点通知；如影响 B4 结论，需 B4 侧自行报告。

## 6. 偏差与阻塞

| # | 项 | 状态/影响 |
|---|---|---|
| D1 | `launch --phase build` 未导出 `QUESTIONS/V3_CODE_ROOT` | **已绕过**；首投 `47083951` 写错臂根后取消，部分根隔离；建议另行授权修复 ops/sbatch 集成。后续任何人直接 `launch` 仍会复现 |
| D2 | seed 根命名 | ops `seed_batch_root()` 用 `batch_tag` 生成连字符路径；本次真实目录用冻结下划线路径，另有连字符符号链接供 ops 使用。ops 状态记录符号链接路径 |
| D3 | 批准包缺 `budget_no_cap.json` | 已用 `no-cap --create` 补齐（SHA `3e8d08b6…`）；prepare 已通过；原记录目录 `SHA256SUMS` 未包含该新文件 |
| D4 | B4 full 作业被外部取消 | 非本会话动作；事实见 §5；不影响 P2 build/prepare 产物 |
| D5 | 墙钟略高于基线 | 63m47s，比 61–64 分钟基线最慢 +13s；B4 竞争/节点差异只记录不归因 |
| D6 | 未 run/test/score | 任务边界；runs 根未创建，无模型调用 |

## 7. 下一步（test/run 前置）

1. **修复 launch 集成缺陷**（另行授权）：`launch` 应导出 `QUESTIONS`/`V3_CODE_ROOT`，或
   `sbatch_p2_build.sh` 不应在仅缺这两个变量时用 `arm-env` 覆盖 `BATCH_ROOT`。
2. **核验 run 前置**：两臂 `preregistration_approval.json`、`budget_no_cap.json`、
   `p2_face_measure.json`、`arm_config.json`、`record/approval_manifest.json` 已在位；
   `launch --phase run` 还会核 env 文件（存在性/权限/模型 ID），本诊断**未读 env**。
3. **B4 状态**：B4 full 已被外部取消；P2 不去续跑/取消/改写 B4。若 B4 需恢复，由 B4 侧拍板。
4. **run/test/score 边界**：score 零 LLM；run/test 会调用模型，须等付费/HPC 授权与 env 就绪，
   不得用本报告当作发车授权。
5. **符号链接清理**：若后续 ops 修复了 seed 命名，可决定是否把 `p2-298-20261021_seed` 符号链接
   改为真实目录；当前保留以维持 ops 状态可解析。

## 8. 证据

目录：[`docs/review_evidence/p2_formal_build_2026-10-21/`](review_evidence/p2_formal_build_2026-10-21/)

| 文件 | 内容 |
|---|---|
| `approval_package_check.json` / `.err` | 批准包复核完整输出（rc=0） |
| `approval_summary.json` | 四文书/脚本锁/模型/env 摘要 |
| `build_job_47084480.log` | 成功 build 的完整日志（gate + build-copy + PASS） |
| `build_job_47083951_cancelled.log` | 首投失败作业日志 |
| `build_copy.json` / `verify_identity.json` | 显式 build-copy 与 §5.2 身份门输出 |
| `prepare_v1card.json` / `prepare_v2card.json` | 两臂 prepare 输出（rc=0） |
| `p2_face_measure_v1card.json` / `_v2card.json` | 两臂 P2-face 原始件 |
| `p2_face_eight.json` | 八项期望/实测对照 |
| `formal_summary.json` | 三根文件数/顶层/SHA/指纹/face 汇总 |
| `build_identity_seed.json` / `_v1card.json` / `_v2card.json` | 三根完整身份旁块 |
| `run_input_pairs_seed.txt` / `_v1card.txt` / `_v2card.txt` / `_digests.json` / `_cmp.txt` | 298 条 `(qid, run_input_sha256)` 与相等判定 |
| `top_level_sha256.txt` | manifest/identity/split 顶层 SHA |
| `timestamps.txt` / `seed_build_timing.json` | 构建起止与墙钟 |
| `jobs_sacct.txt` / `b4_observation.txt` | 本作业/B4 作业 sacct |
| `build_seed_state.json` | ops seed build 状态文件 |
| `quarantine.txt` / `launch_incident.json` | 首投失败现场与根因 |
| `record_p2_operations_*.json` / `record_approval_manifest_*.json` / `arm_config_*.json` | prepare 旁件 |
| `no_cap_create.json` | no-cap 标记生成 |
| `protected_pre_state.txt` / `protected_post_state.txt` | 保护面前后快照 |
| `zero_model_check.txt` | 日志无模型/网络标记 |
| `SHA256SUMS` | 以上证据校验和（不含自身） |