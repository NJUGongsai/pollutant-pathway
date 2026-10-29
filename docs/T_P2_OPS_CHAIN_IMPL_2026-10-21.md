# P2 操作链交付报告（2026-10-21，断点续）

> **题域标签：[298 域] = RHEA 通用酶学 / 已见题（post-hoc）。** 本报告全部结论只在该
> 题域内成立，与 dev（B1 环境路径中间步骤）双向不外推。
>
> 任务书：`docs/TASK_P2_FULL_V2_LAUNCH_2026-10-21.md` §3.2（第 3/4 件）、§3.3、§3.4、
> §4.1–§4.3、§5.1–§5.2、附录 B。
> 证据目录：`docs/review_evidence/p2_ops_chain_2026-10-21/`。
> 工作树：`/private/tmp/dependingv43_p2_ops`，HEAD `11aeeafded1b41185f24de49767933709aad49db`。
> 本报告只做本地离线交付：**未连 HPC、未 sbatch、未调模型、未读金标/题面、未 push**。

## 0. 结论

操作链已按 §4.1 的“冻结克隆”方案交付：`p2_operations.py`、`p2_run_wrapper.py`、
5 个 `sbatch_p2_*.sh`、`p2_arm_config.json` 全部就位，补丁 3（orchestrator/worker）
已在工作树接线，补丁 2（v1card）已 `git apply --check` 通过并应用。

本地正负控 **77/77 全过**，其中：
- 旧批汇总与 `11aeeaf` 未打补丁主树**逐字节同**（除 `generated_at`），SHA 均为
  `b2ccb10de7fdd86a0d9931463ec515d6f11e2e5f4c455080e8e03808ee33a490`；
- 非法版本 / `evidence_card_enabled=false` / A/B 交叉错配 / 旧批升级版本臂 **全部拒**，
  桩件模型调用计数 **0**；
- `launch` 干跑不写状态 JSON、不调 `sbatch`（仅创建 0 字节 flock 锁文件）；squeue 活跃幂等、结束需 `--resume`、
  二败停报、`pending_submission` 禁盲重投、单发车 flock 生效；
- `stop.json` 首写生效，第二次不覆盖（文件 SHA 不变）；
- `ti_operations.py → p2_operations.py` 的 75 个 diff hunk 全部落在白名单 W1–W6，
  W0=0；20 个冻结语义函数名称归一后逐字相同；10 组阈值/分类常量逐字相同，approval 四文书键仅 `final_review→chem_review` 白名单差异。

**尚不能发车**：模型/env、P2 代码聚合、部署 RDKit 版本仍为 TBD；化学复审与 P2 脚本锁
尚未落盘；部署/HPC 侧检查与真实 build 未执行（本任务禁止）。详见 §7/§8。

## 1. 交付清单（含 SHA-256）

| # | 文件 | SHA-256 | 状态 |
|---|---|---|---|
| 1 | `scripts/hpc/p2_operations.py` | `2d41cc694162d71ada5be4b71c888c3e469419dddd662d1b8f916510e16b781e` | 已交付 |
| 2 | `scripts/hpc/p2_run_wrapper.py` | `dd74fe81d04ea1a97069753a3b8c2f2226a884f38c264487d3ccd04b6d5fa138` | 已交付 |
| 3 | `scripts/hpc/p2_arm_config.json` | `d9afe0badc167e24755532f16a34e44b661e2cf6e2631c1a180fefa153c0ea92` | 已交付（TBD 项见 §7） |
| 4 | `scripts/hpc/sbatch_p2_build.sh` | `1f07ff027621814d4de6b57b18ec7cc38766baef21171a4c91fa98b222fa75be` | 已交付 |
| 5 | `scripts/hpc/sbatch_p2_run.sh` | `3cf6d455220027ab478575cf09fb633b0580bb66df2ff5be77cba591c7bde169` | 已交付 |
| 6 | `scripts/hpc/sbatch_p2_score.sh` | `1230d025c664cf81919b95b69c6f861f4992c43dac84de9b50eebfaee578f648` | 已交付 |
| 7 | `scripts/hpc/sbatch_p2_monitor.sh` | `ad4b9e5e4b8d33ab130e85a7b775178a32f02277878433928337eac42ee9e4fb` | 已交付 |
| 8 | `scripts/hpc/sbatch_p2_netcheck.sh` | `ceb7dfed92eea1f36dee64da792f71b112dff10c347b9b6b42dd7fc290e5f2cb` | 已交付（未提交作业） |
| 9 | 补丁 3 接线（源码） | 见证据 patch：`patch_ops_chain_2026-10-21.patch` | 已接线 |
| 10 | 补丁 2（v1card） | `09414e26af89b3c12a7d3a37a60ddfeef1f3c006049badd427743c948338269e` | 已应用 |
| 11 | 证据目录 | `docs/review_evidence/p2_ops_chain_2026-10-21/` | 已交付 |

源码文件 SHA（补丁 1+2+3 组合后）：

| 文件 | SHA-256 |
|---|---|
| `src/pathway_v43/pollutant/candidate_evidence.py` | `6ce2772f716dfbefa3982cdf50992d01b5d0984afcc71751cbc5338ab0124560` |
| `src/pathway_v43/pollutant/real_model.py` | `4772e90a459ec43ab4e4fa41ff040851ed34efb3db7233c6e73f1153fce83c20` |
| `src/pathway_v43/pollutant/runflow.py` | `a26801f722825bf2ef666cf4f89e955feff5c102beb2eafc9aa8e9f8d0ec529c` |
| `src/pathway_v43/pollutant/s5b_orchestrator.py` | `131cf4ae330daa159f65b1a1ab116ce7855d6199e40a4cf865d9933662ead5d1` |
| `src/pathway_v43/pollutant/s5b_worker.py` | `d188b7402baaadb384828bb3c4c6502471dcf7929cd20277d43ae50f15d56caf` |
| `tests/test_p2_evidence_card_v2.py` | `c102ceff6bd778b5c163ebf90fd5162b5194d786deb06bc1510dad0c3dadeb8d` |
| `tests/test_p2_v1card_mode.py` | `4300d5b815350ea98da2fcfe1baf431a320fdbe3435c5d6f3a60eb78b90857f9` |

完整操作链补丁：`docs/review_evidence/p2_ops_chain_2026-10-21/patch_ops_chain_2026-10-21.patch`
SHA-256 `9169cd3099a5a4b7adee403c0354a3ab3cf4837c8e0bdb81bb07537081216dac`，
在 `11aeeaf` 干净归档上 `git apply --check` **PASS**。

> 补丁路径口径说明：任务书写 `git diff 11aeeaf -- src/ scripts/hpc/p2_*`，但该 glob
> 不含 `sbatch_p2_*.sh`。本交付显式加入 5 个 sbatch 脚本，否则操作链不完整；范围仍限定
> 在 P2 新增文件与 `src/` 补丁，不含 `ti_*` 参考副本、不含 doc/证据。
> 另附**备选增量补丁** `patch3_ops_chain_incremental.patch`
> （SHA-256 `31d50045bb8e30ec8f2570b962a685a93e474b939a8328229f213ea3369f4d24`），
> 仅用于任务书 §3.5 的 1→2→3 顺序；主路径是单次 apply 组合补丁。部署硬门见 §6。

## 2. 断点续：上次遗留与本次修复

上次工作树里 `p2_operations.py`（135 KB）与 `p2_run_wrapper.py`（5.2 KB）是“写到一半”的
状态；本次没有推倒重来，按 `ti_operations.py` 语义补齐/修复：

| 问题 | 位置 | 修复 |
|---|---|---|
| `choices` 含 `build-copy`，但 `main()` 无分发 | `p2_operations.py` | 加 `build-copy` 分支（seed 根缺省推导 + `--dry-run`） |
| 文档声明 `launch --dry-run`，parser/main 未接 | `p2_operations.py` | 加 `--dry-run`，透传 `launch(dry_run=...)` |
| `prepare(...)` 新增 `ws=` 必填但 main 未传 | `p2_operations.py` | main 传 `ws=ws`（§5.2 两臂身份门前置） |
| 残留 T-I 臂名 `glm|deepseek` | `p2_operations.py` 两处 | 改为 `v1card|v2card`（`approval-package` 默认臂 `v1card`） |
| `submit_monitor` 环境变量仍传 `TI_CONFIG` | `p2_operations.py` | 改 `P2_CONFIG` |
| `phase` 恢复路径未透传证据卡版本 | `p2_operations.py` | 传 `evidence_card_enabled/version`，避免 resume 错臂 |
| no-cap 文案日期仍是 2026-10-20 | `p2_operations.py` | 改 2026-10-21 |
| `p2_run_wrapper.py` 是 `ti_run_wrapper.py` 的逐字副本（import ti_operations、`ti_run`、证据卡关） | `p2_run_wrapper.py` | 重写为 P2 语义：import `p2_operations`、默认 `p2_arm_config.json`、`evidence_card_enabled=true`、透传 `evidence_card_version`、部署 orchestrator 不支持版本参数时 fail-closed |
| 5 个 sbatch 脚本与配置缺失 | `scripts/hpc/` | 新建（见 §3） |

## 3. 逐条对照

### 3.1 §3.2 第 3 件（操作链接线补丁）

| 合同 | 实现 | 证据 |
|---|---|---|
| `run_s5b_batch(..., evidence_card_version=None)`；合法 `None/v1card/v2`；非 None 要求 `enabled=true` | `s5b_orchestrator.py`：`normalize_evidence_card_version` + `require_evidence_card_version_enabled` | C3（非法值/disabled/旧批升级/冲突全拒） |
| 冻结副本仅非 None 写键；None 零新键 | 冻结字典条件写键；旧批读取不新增 | C1 与 11aeeaf 逐字节同 |
| worker argv 增加 `--evidence-card-version`；case 披露；缺失/不符/非字符串拒 | `_run_batch_loop` 传参；`validate_case` 版本判据；失败占位同样披露 | C3 四类 worker 拒错，case 记录 failure_kind |
| 批终态报告非 None 写版本 | `_run_batch_loop` 从冻结副本装载并核对后写 | orchestrator diff（`reported_version`） |
| 任何缺失/不符/非法 ⇒ fail-closed，零模型调用 | worker 在 build identity/模型装配之前核对 | C3 桩件计数 0 |

### 3.2 §3.4 验收（旧批零漂移 / 错配 / 身份）

| 验收 | 结果 |
|---|---|
| 旧批（无版本键）resume/汇总零新键、逐字节零漂移 | C1：汇总与 11aeeaf 基线 SHA 同为 `b2ccb10d…`（持久化于 `probe_ops_controls_result.json`）；C2：旧 run resume 无版本键；identity 文件字节在 resume 前后相同（不变量；本轮值见 `probe_ops_controls_result.json` → `C2.old_resume_identity_bytes_unchanged.before/after`，逐轮由合成输入生成，非固定证据哈希） |
| A/B 交叉错配拒 | C3：worker 冻结 v2 / 请求 v1card ⇒ `evidence_card_version_mismatch`；orchestrator 冻结 v2 / 请求 v1card ⇒ `s5b_orchestration_conflict` |
| v1card/v2 身份/resume 测试 | `tests/test_p2_v1card_mode.py` 10 项 + `tests/test_p2_evidence_card_v2.py` 18 项，28 passed |
| 全量 not-slow 绿 | 2362 passed, 16 deselected, 1 warning（401.32s，退出码 0） |

### 3.3 §4.1/§4.2（冻结克隆与 diff 白名单）

- 新建 `p2_operations.py`，`ti_operations.py` **零改动**（参考副本 SHA 与 T-I 锁一致）。
- 75 个 diff hunk 分档：W1 29、W2 10、W3 11、W4 17、W5 1、W6 7、W0 0。
  详见 `diff_whitelist_audit.md` 与 `diff_whitelist_hunks.json`。
- 不得改面核验：`MONITORING_THRESHOLDS`、fatal/transport/rate-limit/content/recovery
  分类、`STRUCTURAL_ZERO_CALL_CAUSES`、`STABLE_FIELDS`、`OUTPUTS`、`SECRET_FIELD_MARKERS`
  与 T-I 逐字相等；`APPROVAL_REQUIRED_KEYS` 仅 `final_review→chem_review`。
- 20 个冻结语义函数在名称归一后逐字相同（`classify_case`、`evaluate_stage`、
  `write_stop`、`barrier_full`、`monitor_once`、`seal`、`score_all` 等，清单见 C7）。
- P2 新增只在操作面：seed build/copy、§5.2 身份门、`--dry-run`、`build-copy` 命令。

### 3.4 §4.3 / 附录 B（配置）

`p2_arm_config.json` 已按 `p2-arm-config-1` 写：

| 项 | 值 |
|---|---|
| 两臂 | `v1card` / `v2card`；role `control` / `treatment` |
| 臂差异 | `evidence_card_version` = `v1card` / `v2`；两者 `evidence_card_enabled=true` |
| 同值面 | `expected_model_id`、`env_file_basename` 两臂逐字相同（当前 TBD） |
| approval 四文书 | `prereg` / `task` / `chem_review` / `script_lock` |
| prereg id / no-cap 日期 | `prereg-p2-298-2026-10-21` / `2026-10-21` |
| 批名/job/协调/记录 | `p2_298_*` / `p2-*` / `p2_coordination_*` / `p2_approved_record_*` |
| identity_expectations | 编译/池/来源/检索/归一/路由版本已填；**代码聚合与 RDKit 写 TBD** |
| 科学源码 SHA | compiler `58cf3dc9…`、evaluation `37c09231…`（本地实测） |

### 3.5 §5.1/§5.2（build 与身份门）

| 合同 | 实现 | 本地验证 |
|---|---|---|
| seed build 一次 + 字节级复制到两臂 | `seed_batch_root`/`seed_state_path`；`build-copy`；`sbatch_p2_build.sh` 一次 build 后调 `build-copy` | C4 干跑；真实复制未执行（无 HPC） |
| 不复制 orchestration/gate/cases/状态 | `BUILD_COPY_EXCLUDES` + 后缀/正则排除 | 代码审计；真实复制未执行 |
| 复制后核对 manifest SHA、fingerprint、298 条 `(qid,run_input_sha256)` | `_copy_build_tree` 逐文件复核 + `verify_identity` | 代码审计；真实 build 未执行 |
| §5.2 身份门 8 条 | `verify_identity`：batch_tag/manifest SHA/fingerprint 64hex/run_inputs 全等/ref 一致/代码聚合非旧 T-I/RDKit 同值/缺指纹即停 | C6 旧 T-I 聚合拒；真实两臂 build 未执行 |
| 缺少指纹、空 sha、旧 T-I 聚合 ⇒ 停 | `check_build_identity` 复算 fingerprint、核 schema、逐题 run_input 字节 sha | 代码审计 + C6 |

## 4. 正负控数字（77/77）

证据：`probe_ops_controls.py`、`probe_ops_controls_result.json`、
`probe_ops_controls_stdout.log`、`probe_ops_controls_stderr.log`（空）。

| 组 | 检查数 | 结果 |
|---|---|---|
| C1 旧批汇总零漂移 | 2 | 无版本键；与 11aeeaf 基线逐字节同（`b2ccb10d…`） |
| C2 旧批 run resume | 3 | 无版本键；identity 前后字节相同（不变量；本轮值见 result JSON 的 C2 字段，逐轮易变，不作固定证据哈希） |
| C3 拒错 + 零模型调用 | 14 | 7 个拒错场景（4 worker + 3 orchestrator），每场景桩件调用 0 |
| C4 launch 干跑/squeue/history/锁 | 10 | 不 sbatch、不写状态 JSON（仅锁文件）；活跃幂等；结束需 resume；二败停；pending 停；flock 拒 |
| C5 stop 首写 | 4 | 第二次不覆盖；`stop.json` 文件字节在第二次写入前后相同（不变量；本轮值见 result JSON 的 C5 字段，含 `recorded_at`，逐轮易变，不作固定证据哈希）；require_no_stop 阻断 |
| C6 配置负控 | 13 | schema/批名/错版本/disabled/异模型/异 env/角色/prereg/no-cap/文书键/旧聚合全拒 |
| C7 diff 白名单 | 31 | 10 组常量 + 1 组四文书键（白名单差异）+ 20 个冻结函数全等；W0=0 |

关键负控明细：

- `evidence_card_version="v9"` ⇒ worker `evidence_card_version_invalid`，调用 0；
- 冻结 `enabled=false` + version ⇒ worker 拒，调用 0；
- 冻结 v2 / 请求 v1card ⇒ worker `evidence_card_version_mismatch`，调用 0；
- 可信上下文请求 v2 / 冻结副本无版本键 ⇒ `evidence_card_version_frozen_copy_missing`，调用 0；
- orchestrator 旧批升级版本臂 ⇒ `s5b_orchestration_conflict`，调用 0。

## 5. 测试

| 套件 | 结果 |
|---|---|
| `tests/test_p2_v1card_mode.py` + `tests/test_p2_evidence_card_v2.py` | 28 passed（9.54s） |
| 全量 not-slow（`-m "not slow"`） | 2362 passed, 16 deselected, 1 warning（401.32s，退出码 0） |

命令（conda `depending43`，Python 3.11.16，RDKit 2026.03.6）：
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<worktree>/src python -m pytest -q -m "not slow" -p no:cacheprovider`。
日志：`pytest_not_slow.log`。未写 `.pytest_cache`/`__pycache__`。

## 6. 部署序列（hard gate）

> **结论：组合补丁只能单次 `git apply` 到干净 `11aeeaf`；不得先 apply patch1/patch2 再叠加。**
> 任务书 §3.5 的 1→2→3 顺序**不适用于本组合补丁**：组合补丁已包含 patch1/2 的 `src/`
> 结果，叠加会因 hunk 已应用而失败。若必须保留 1→2→3 语义，使用 §6.2 的增量 patch3 备选。

### 6.1 主路径（已验证）：干净 `11aeeaf` → 单次 apply 组合补丁

```bash
# 1) 新树到 11aeeaf（不得在 v43cTH / 主树 / 已打补丁树里做）
git clone <repo> v43cP2 && cd v43cP2
git checkout 11aeeafded1b41185f24de49767933709aad49db

# 2) 单次 apply（不要先 apply patch1/patch2）
git apply --check /path/to/docs/review_evidence/p2_ops_chain_2026-10-21/patch_ops_chain_2026-10-21.patch
git apply         /path/to/docs/review_evidence/p2_ops_chain_2026-10-21/patch_ops_chain_2026-10-21.patch
```

- 组合补丁含 **13 件**：5 个源码 + 8 个 P2 操作文件。
- 2 个 P2 测试文件（`tests/test_p2_evidence_card_v2.py`、`tests/test_p2_v1card_mode.py`）
  不在组合补丁内（属 patch1/patch2 交付物）。若部署树要跑 P2 定向测试，从 A 路证据目录
  复制并单独核 SHA；只跑流水线则不需要。
- **15 件 P2 产物期望 SHA 的引用位置**：`environment.json` → `p2_artifacts_15`
  （即 `files_sha256` 17 条中除 `evaluation.py`、`s5b_compiler.py` 两个基线未改文件）。
- 已验证：干净 `11aeeaf` 单次 apply 后，补丁内 13 件 SHA 与 `environment.json` 全等；
  A/B 侧独立复核记录为 15/15 全等（含 2 个测试件）。

### 6.2 备选路径（已验证）：patch1 → patch2 → 增量 patch3

为满足任务书 §3.5 的 1→2→3 顺序，本次额外产出增量补丁
`patch3_ops_chain_incremental.patch`（10 件：8 操作 + 2 源码；
SHA-256 `31d50045bb8e30ec8f2570b962a685a93e474b939a8328229f213ea3369f4d24`）。

```bash
git checkout 11aeeafded1b41185f24de49767933709aad49db
git apply docs/review_evidence/p2_v1card_2026-10-21/patch1_impl_r2.patch
git apply docs/review_evidence/p2_v1card_2026-10-21/patch2_v1card.patch
git apply docs/review_evidence/p2_ops_chain_2026-10-21/patch3_ops_chain_incremental.patch
```

- 已实测：该序列 apply 成功，**15 件 P2 产物 SHA 与工作树逐字全等**（含 2 个测试文件）。
- 主路径仍是 §6.1 单次 apply（步骤少、无顺序歧义）；§6.2 只作“必须保留 1→2→3 语义”
  时的备选。
- **不得混用**：先 patch1/patch2 再叠加组合补丁会 apply 失败（同一 src hunk 被应用两次）。

### 6.3 脚本锁注记（`s5b_compiler.py`）

`src/pathway_v43/pollutant/s5b_compiler.py` 在 P2 基线 `11aeeaf` 的 SHA 为
`58cf3dc94dd83cbf8245c9e2117ac50f41e847c685663321af973f637fba7058`，与 T-I 锁
（`c9c6c7a7`）记录的 `f917762bf9ec43d70b85ef3740ab7f22b866b42c06a1461ec336882eb2685dfc`
不同；差异是 `11aeeaf` 的 P0b/D-6 **仅新增诊断常量**
`P0B_D6_COMPILED_DECLARATION_BOUNDARY`，`S5B_COMPILER_VERSION` 仍为 `s5b-compiler-6`，
P2 补丁**未改**该文件。脚本锁/部署核对时按“基线演进”登记，不得误判为污染或第三方改动。

## 7. Pending（发车前必须闭合）

| # | 项 | 现状 | 闭合动作 |
|---|---|---|---|
| 1 | 模型 ID / env basename | 两臂均 `TBD` | T-I 规则选定模型后两臂同值写死；`require_model` 会拒 TBD |
| 2 | P2 代码聚合 `code_identity_aggregate_sha256` | `TBD` | 在 `~/EnzymeAgent/v43cP2`（11aeeaf + 组合补丁，或 §6.2 的 1→2→3）实测；两臂同值；不得用 T-I `1aac04da…`（旧聚合清单见 `environment.json` → `t_i_old_aggregates`） |
| 3 | 部署 RDKit 版本 | `TBD`（本机 2026.03.6 仅测试） | 部署环境实测并跑 v2 确定性锚（FG/质子化/碳氧化态/公式） |
| 4 | 化学复审 | `docs/T_P2_V2_CHEM_REVIEW_2026-10-21.md` 未落盘 | 按任务书 §3.3.7 / 三触发点走 mimo 化学评审，回复落 docs/ |
| 5 | P2 脚本锁 | `docs/T_P2_SCRIPT_LOCK_2026-10-21.json` 未生成 | 补丁 1–4 + 部署树逐文件 SHA + 两臂模型/env/证据卡版本 |
| 6 | 题卷 SHA | 配置写 T-I/T-H/P1B 同源锚 `9f5955d4…`（见 `environment.json` → `config_questions_sha256`） | HPC 发车日独立重算并登记 |
| 7 | 批准包 | 未生成/未签字 | 预注册签字 + 四文书快照 + `preregistration_approval.json` + `budget_no_cap.json` + `SHA256SUMS` |
| 8 | 部署 | 未部署 | 新树 `v43cP2`、tar 后删 `._*`、HPC 逐文件 `sha256sum -c` |
| 9 | HPC 前置 | 未执行 | C2–C5、netcheck、G1 soak 12/12、登录直连对照（任务书 §6） |
| 10 | 真实 build/prepare/run/score | 未执行 | 按 §5.1/§5.3/§7 执行；本任务禁止 |
| 11 | 补丁 2 复审 | 仅有 A 侧离线证据 | §3.3.7 要求 Codex/qwen 复审 + 化学复审引用；未复审不签字、不发车 |

## 8. 送审条件

满足以下条件后，建议把本报告 + `patch_ops_chain_2026-10-21.patch` + 证据目录送
Codex/qwen 复审（操作链/程序面）并同步 mimo 化学评审（证据卡语义面）：

1. 本文 §7 第 1–7 项闭合（尤其模型/env、代码聚合、RDKit、化学复审、脚本锁）；
2. §4 的 77/77 正负控在部署树重跑仍全过（本地值不能替代部署树实测）；
3. 全量 not-slow 绿 + v1card/v2 定向测试绿；
4. `git apply --check` 在部署树基线通过，脚本锁逐文件 SHA 与部署树一致；
5. 复审范围声明：只审操作链/证据卡版本面，不审科学性能、不改判据/阈值/分母。

## 9. 需要 CC 拍板的点

| # | 事项 | 当前默认 | 需要确认 |
|---|---|---|---|
| 1 | `approval.source_kind` | `cc_personal`（依据 `docs/P2_CC_DECISION_FULL_V2_2026-10-21.md` CC 本人指令） | 是否确为 CC 本人；若走代决链需改 `codex_delegated_cc_shijie`/`qwen_delegated_codex` |
| 2 | `token_plan_high` | 两臂 12,000,000（附录 B 草案占位，只告警不设帽） | 是否按实际规划回填 |
| 3 | build 策略 | `seed_copy`（§5.1 建议默认） | 是否坚持 seed+字节复制，还是两臂独立 build |
| 4 | v1card 补丁（补丁 2） | 已应用但未复审 | 是否进入 Codex/qwen + 化学复审；未复审不发车 |
| 5 | 发车时点 | 被 T-I 模型选择阻塞 | 模型选定后再填 TBD、生成脚本锁、部署与前置检查 |

## 附录：证据文件索引

| 文件 | 内容 |
|---|---|
| `patch_ops_chain_2026-10-21.patch` | 交付补丁（src + 8 个 P2 操作文件） |
| `patch3_ops_chain_incremental.patch` | 备选增量补丁（patch1+2 之上的 10 件；1→2→3 序列用） |
| `diff_ti_vs_p2_operations.diff` | `ti_operations.py` vs `p2_operations.py` 原始 diff（75 hunk） |
| `diff_whitelist_audit.md` / `diff_whitelist_hunks.json` | 白名单分档审计（机读 + 人读） |
| `probe_ops_controls.py` | 正负控探针（零模型/零网络/零金标） |
| `probe_ops_controls_result.json` | 77 项检查结果 |
| `probe_ops_controls_stdout.log` / `_stderr.log` | 干跑输出 / 错误流（stderr 空） |
| `pytest_not_slow.log` | 全量 not-slow 测试日志 |
| `environment.json` | HEAD、Python/RDKit、补丁与文件 SHA、T-I 锁审计 |
| `SHA256SUMS` | 证据目录逐文件 SHA-256 |