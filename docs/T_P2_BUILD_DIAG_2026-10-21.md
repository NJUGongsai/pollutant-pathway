# P2 集成树 HPC build-only 298 诊断（2026-10-21）

> **题域标签：[298 域] = RHEA 通用酶学 / 已见题（post-hoc）。** 本报告只验证 build 可用性与
> 墙钟；**没有任何 hit/score 指标**，不向 dev 或其他题域外推。
>
> **结论：P2 集成树部署成功，seed build 一次通过，build-gate 通过，298/298 run_inputs。**
> 零模型、零网络、未 run/test/score，未创建 runs 根。墙钟 **63 分 33 秒**，落在
> 61–64 分钟基线内。

## 0. 结果速览

| 项 | 结果 |
|---|---|
| 部署 | `~/EnzymeAgent/v43cP2`，713 文件，902M（含 assets 889M）；96 代码文件 SHA 部署时/复检均本地=远端；build 期间并发会话外部改了 1 个 config（见 §2.1） |
| 代码身份 | HEAD `11aeeaf` + 四补丁；v2 prompt SHA `c24bee42…7598`（实核一致） |
| 环境 | Python 3.11.15；RDKit **2026.03.5**；`import pathway_v43, rdkit` OK |
| build | `s5b_cli build` 一次（seed），`BUILD_SECONDS=3813`（63m33s），`BUILD_RC=0` |
| 作业 | job `47081102`，`COMPLETED 0:0`，sacct elapsed `01:03:37` |
| build-gate | `BUILD-GATE-OK: n=298 sha=9f5955d4… entries_with_cosub_labels=298/298`（1 秒） |
| run_inputs | **298 个 JSON / 298 个唯一 qid**；批根 29M |
| 身份指纹 | `build_identity_fingerprint = ea23bc359999f176513fb1844db20a54f86e5e0247a0ea5bad76de925cac1378` |
| 代码聚合 | `code_identity_aggregate_sha256 = cfd7406709b60344104c17513a0616b59380b971d5ede0d0909bc4f5c1322f07` |
| 基线对比 | 基线 61m46s–63m34s；本次 63m33s，范围内（比最快 +1m47s，比最慢 −1s） |
| 入口 | **底层 `s5b_cli build`**；ops 无 `build` 子命令且诊断 tag 不被 ops 接受（见 §3） |
| 阻塞点 | 无 build 阻塞；正式 P2 发车仍需两臂 build-copy；config 的模型/身份回填由并发会话**外部完成**，本诊断未背书（见 §8） |

## 1. 本地自检（部署前）

| 检查 | 结果 |
|---|---|
| 集成树 | `/private/tmp/dependingv43_p2_integration` |
| HEAD | `11aeeafded1b41185f24de49767933709aad49db` |
| 工作树 | 5 个 modified + 11 个 untracked（P2 四件输入齐全，见证据 `integration_selfcheck.txt`） |
| `git diff --stat 11aeeaf` | 5 files, +1169/−62 |
| v2 prompt SHA | `c24bee42f651c783c9bdcee6e8f547bff63f1f5fee6a4a87f4816e4d15e57598`（与任务书一致） |
| 组合补丁 | `p2_integration_combined.patch`，SHA `608dec73f2060c78bbc891e134fb6ef16d6bebfa70e1de3e725f88c82c16a0a2`（与任务输入一致） |
| 四补丁 | impl r2 / v1card / ops chain / chemfix 均在树中：`candidate_evidence.py`、`real_model.py`、`runflow.py`、`s5b_orchestrator.py`、`s5b_worker.py`、8 个 `scripts/hpc/p2_*`、3 个 `tests/test_p2_*` |

## 2. 部署

### 2.1 方式与清单

| 项 | 值 |
|---|---|
| 目标树 | `/work/home/aclhl3hbth/EnzymeAgent/v43cP2`（**新建**；部署前不存在） |
| 打包 | `tar czf`，排除 `.git`、`__pycache__`、`.pytest_cache`、`.DS_Store`、`assets`、`docs/review_evidence`、`reports` |
| 包 SHA | `4c9ddb3e1d68e01a0c26deb8250c98ed30de570c09fcc3240b4244df2e982a46` |
| 解包清理 | `find . -name "._*" -delete` |
| assets | 从 `/Volumes/CC/Enzyme_Agent/dependingv43/assets/` rsync 拷入；**27 文件，889M**；本地/远端逐文件 SHA 一致 |
| 部署树规模 | 部署时 713 文件，902M；src 131、tests 141、scripts 52、docs 337；复检时 +41 个 `__pycache__` |
| 逐文件 SHA（部署时） | src + scripts/hpc/p2_* + tests/test_p2_* 共 **96 文件，本地=远端**（`deploy_code_sha256.txt`） |
| 逐文件 SHA（复检） | 当前 **96 文件仍本地=远端**（`deploy_code_postcheck_sha256.txt`） |
| assets SHA | **27 文件，本地=远端**（`deploy_assets_sha256.txt`） |
| 部署后漂移 | 并发会话在 **19:52:18**（HPC）把 `scripts/hpc/p2_arm_config.json` 由 `d9afe0…` 改为 `c4789a…`（外部回填模型/env/身份）；新增 41 个 `__pycache__`（cpython-311/312 混合），**无 `.py` 源码变化**。build 用显式参数、不读该 config，故不受影响（`deployment_drift.json`） |

关键资产 SHA：

| 文件 | SHA-256 |
|---|---|
| `assets/METANETX.json` | `d2f5e2cf935f1a07383812ecc7b288fec3a74a18bb71eb07a94fbdedd300a27f` |
| `assets/USPTO.json` | `4baebf7582fc218f5ef1d7df98dbb9837c31ce43028f9e5cf97d784667e2327e` |
| `assets/rhea.json` | `8927221e4c5d866d259bba5ba269b6da995340b766e94deec440ad8503b173d9` |
| `assets/MANIFEST.sha256` | `ac9b97b872c9666eebbe32b42c626997aca34438ade17d7bbf36a8154b848e6c` |

### 2.2 环境校验

| 检查 | 结果 |
|---|---|
| `PYTHONPATH=~/EnzymeAgent/v43cP2/src python -c "import pathway_v43, rdkit"` | OK |
| Python | 3.11.15 |
| RDKit | 2026.03.5 |
| `resolve_config(v3_root, assets_root)` | OK（assets_root=`v43cP2/assets`，v3_code_root=`dependingv3`） |
| v2 prompt SHA（HPC 实跑） | `c24bee42f651c783c9bdcee6e8f547bff63f1f5fee6a4a87f4816e4d15e57598` |

> 部署树用 tar 打包时**未包含** `docs/review_evidence/` 与 `reports/`（体积大、非 build 依赖）；
> `docs/*.md` 保留，供后续 prepare 读预注册/任务书/复审/脚本锁。完整排除项见 `environment.json`。

## 3. build 命令与参数

### 3.1 为什么绕过 `p2_operations.py build`

| 原因 | 证据 |
|---|---|
| `p2_operations.py` **没有 `build` 子命令**（只有 `prebuild` / `build-copy` / `verify-identity` 等） | `main()` 分发；`build` 不在命令列表 |
| ops `load_config` 强制 `batch_tag` 以 `p2-298-` 开头，诊断 tag `p2-build-diag-20261021` 会被拒 | `load_config` 白名单 |
| `sbatch_p2_build.sh` 在 seed build 后**必接 `build-copy`**（两臂复制 + §5.2 身份门），本任务明确不做两臂复制 | 脚本尾部 |

因此改用底层 `s5b_cli build`，**参数逐字取自 P2 任务书 §5 / §2 冻结面**（池/阈值/来源/编译策略未改）。
注：当前 config 的 model/env 已被并发会话外部回填，但上述两个阻塞**与 TBD 无关**，仍然成立
（ops 仍无 `build` 子命令；诊断 tag 仍不符合 `p2-298-*` 白名单）。

```bash
PYTHONPATH=$CODE/src PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 \
$PY -B -m pathway_v43.pollutant.s5b_cli build \
  --questions ~/ppv1_hpc/questions.jsonl \
  --batch-root ~/ppv1_hpc/batch/p2_build_diag_20261021_seed \
  --batch-tag p2-build-diag-20261021 \
  --provider-kind real \
  --pool-mode template \
  --recorded-source \
  --max-pool 8 \
  --pool-threshold 0.45 \
  --v3-code-root ~/EnzymeAgent/dependingv3 \
  --assets-root ~/EnzymeAgent/v43cP2/assets
```

作业资源：`wzhcnormal`，8 CPU，16G，4h 上限；节点 `a04r2n12`；job `47081102`。

> `--provider-kind real` 只是批身份元数据；build 阶段**不装配模型、不读 env、不发网络请求**。
> 作业日志无 model/API/HTTP/DashScope 标记（`build_job_47081102.log`）。

### 3.2 只 build 一次

| 动作 | 状态 |
|---|---|
| seed build | 1 次 |
| 两臂复制 `build-copy` | **未做**（任务禁止） |
| runs 根 | **未创建** |
| run / test / score | **未做** |

## 4. 墙钟

| 计时 | 值 |
|---|---|
| build 内部起止 | `2026-10-21T11:31:05Z` → `12:34:38Z` |
| build 墙钟 | **3813 秒 = 63 分 33 秒** |
| build-gate | 1 秒 |
| sacct elapsed | `01:03:37` |
| 退出 | `COMPLETED 0:0` |

## 5. 产物与 gate

### 5.1 run_inputs / 批根

| 项 | 值 |
|---|---|
| 批根 | `~/ppv1_hpc/batch/p2_build_diag_20261021_seed` |
| `run_inputs/*.json` | **298** |
| 唯一 qid | **298**（文件名即 qid；逐文件 SHA 见 `run_inputs_sha256.txt`） |
| 批根大小 | 29M（manifest 25.8M + run_inputs 2.2M + reference_graphs 1.9M + identity/split） |
| 题卷 | 298 行，SHA `9f5955d418c2f3876f13cdc9bebea46a1d545d037b182fa5089f56293ff9211c`（只哈希，未读正文） |
| `batch_tag` | `p2-build-diag-20261021` |

### 5.2 顶层产物 SHA

| 文件 | SHA-256 |
|---|---|
| `batch_manifest.json` | `d754363d9597eef40b8e2e5555e4fd435ff33a6e433aaa786d9af0254a9fe29d` |
| `build_identity.json` | `220f0e4252ad203971b1f835f8c94de5262db57a4fc74c1a8b122ae717e237a7` |
| `split_manifest.json` | `6e0e89b9e00e0efbe7817a7fcabd8ed501043bcf11f4e8663f21715f4475601e` |

### 5.3 build-gate

```text
BUILD-GATE-OK: n=298 sha=9f5955d4… entries_with_cosub_labels=298/298
```

`GATE_RC=0`。

### 5.4 build_identity

| 字段 | 值 |
|---|---|
| `build_identity_fingerprint` | `ea23bc359999f176513fb1844db20a54f86e5e0247a0ea5bad76de925cac1378` |
| `code_identity_aggregate_sha256` | `cfd7406709b60344104c17513a0616b59380b971d5ede0d0909bc4f5c1322f07` |
| `compiler_version` | `s5b-compiler-6` |
| `pool_policy_version` | `s5b-pool-policy-9` |
| `recorded_source_version` | `s5b-recorded-source-4` |
| `corpus_retrieval_version` | `s5b-corpus-retrieval-6` |
| `formnorm_version` | `record-side-formnorm-1` |
| `formnorm_param_sha256` | `a7bcb788bd5983c0543e7e7a5060b09bc05c7547d383a6ac0419c575aa391dbd` |
| `route_version` | `s5b-analog-route-f1f4-1` |
| `rdkit_version` | `2026.03.5` |
| `run_inputs` 条数 | 298（每条第 `qid/run_id/run_input_sha256/substrate_sha256`） |
| `asset_identity.manifest_sha256` | `ac9b97b872c9666eebbe32b42c626997aca34438ade17d7bbf36a8154b848e6c` |

> 该聚合 `cfd74067…` **不是** T-I 旧聚合 `1aac04da…` / `a24700ab…`；是本次 P2 树实测值。
> **本会话未改** `p2_arm_config.json`（任务只允许新增报告与证据）。并发会话随后在 19:52
> 把同一聚合与 RDKit `2026.03.5` 外部回填到该文件（`d9afe0…` → `c4789a…`）；本诊断记录
> 该事实，但**不背书其授权链或模型选择**。

## 6. 与 61–64 分钟基线对比

基线取自 HPC sacct（只读，未动作业）：

| 批 / 臂 | build job | elapsed |
|---|---|---|
| T-H | `46930529` | 01:02:04 |
| T-H r2 | `46954982` | 01:01:46 |
| T-I 20261020 glm/deepseek | `47002738` / `47002742` | 01:02:50 / 01:03:14 |
| T-I B2 glm/deepseek | `47042872` / `47042874` | 01:02:41 / 01:02:46 |
| T-I B3 glm/deepseek | `47061667` / `47061671` | **01:03:31 / 01:03:34** |
| **本次 P2 诊断** | **`47081102`** | **01:03:33（build 内部）/ 01:03:37（作业）** |

| 对比 | 差值 |
|---|---|
| 相对基线最快 61m46s | **+1m47s（+2.9%）** |
| 相对基线最慢 63m34s | **−1s** |
| 是否明显更快/更慢 | **否**；落在 61–64 分钟内，与 B3 几乎相同 |

差异清单（只记录，不归因）：

1. 本次是 P2 集成树（含 v2 证据卡/chemfix 代码）在新树 `v43cP2` 上的首次 build；基线的代码树/补丁不同。
2. build 期间同分区有并发 T-I build（`47081227` RUNNING、`47081230` COMPLETED 01:03:32，19:34 起），共享 I/O/CPU 负载情况未知。
3. 本次批根在 ParaStor 新目录；基线批根的缓存/分配状态未测量。
4. 19:52 并发会话外部更新了 `p2_arm_config.json`；build 用显式参数、不读该文件，故与本次墙钟无关。
5. 池/阈值/来源/编译参数与基线同值；build 不是 P2 实验变量。

## 7. 保护面与零模型

| 检查 | 结果 |
|---|---|
| 本会话写 `~/EnzymeAgent/v43cTH` | **无**（只做 stat/find 读元数据） |
| 本会话写 T-I B2/B3/B4/20261020 批根/runs/stop | **无**；前后 mtime 逐项相同（`protected_pre_state.txt` / `protected_post_state.txt`） |
| 本会话写 `~/EnzymeAgent/v43c14` | **无** |
| `v43cTH` 全局是否静止 | **否**：并发 T-I 作业在 19:34–19:35 写入 `ti_build_47081227.out` / `ti_build_47081230.out`（两作业 20:37–20:38 完成），目录 mtime 17:32→19:34→**20:40:32**。**非本会话发起**，本会话只读其元数据 |
| `v43cP2` 部署树 | 本会话部署后，**并发会话在 19:52 写 `p2_arm_config.json`**（`d9afe0…`→`c4789a…`）并新增 41 个 `__pycache__`；无 `.py` 源码变化。build 未消费该 config |
| runs 根 | 未创建 |
| 模型/DashScope/env/key | 未调用、未读；build 零模型 |
| 金标/题面/reference_graphs | **本会话**未读题面正文（题卷只做 SHA/行数）；题卷由 build 进程按设计消费；`reference_graphs` 只出现目录名，未读内容 |

## 8. unknown / 阻塞点

| # | 项 | 状态 |
|---|---|---|
| U1 | 正式 P2 冻结身份尚未建立 | 诊断 tag `p2-build-diag-20261021` **不能**替代冻结的 `p2-298-20261021`；正式发车需按 §5.1 另建 `p2-298-20261021_seed` 并 build-copy |
| U2 | 两臂 §5.2 身份门未跑 | 本任务只 seed build；`batch_manifest` 字节相等/fingerprint 相等/298 条 `(qid,run_input_sha256)` 全等的两臂硬门留待正式轮 |
| U3 | 配置回填的授权链未由本诊断核验 | 并发会话已在 19:52 **外部**回填 `expected_model_id=deepseek-v4.1-flash-1017`、`env_file_basename=llm_ds.env`、`code_identity_aggregate_sha256=cfd74067…`、`rdkit_version=2026.03.5`；本会话未做该改动，也不背书其授权链/模型选择，发车前须按批准包复核 |
| U4 | 模型/env 实际可用性 | 当前树内配置为 `deepseek-v4.1-flash-1017` / `llm_ds.env`（外部回填）；本诊断**未读 env**、未验文件存在/权限 600/模型开通 |
| U5 | 墙钟差异原因 | 未归因；仅记录并发作业、新树首次 build、19:52 外部 config 变更三项上下文 |
| U6 | 诊断批根用途 | 可作 test/score 的**诊断**输入；若要发布 P2 结果，必须用冻结 tag 的新批根，不能混用本诊断身份 |
| U7 | RDKit 版本 | 本次实测 2026.03.5；与外部回填值一致；最终以脚本锁/批准包复核为准 |

## 9. 下一步 test/score 的前置

1. **核验外部回填与脚本锁**：当前 config 已有 `cfd74067…` / `2026.03.5`（外部回填）；须按批准包复核该回填，并生成/核对脚本锁 JSON 的逐文件 SHA（本诊断未生成脚本锁）。
2. **核验模型/env**：当前 config 为 `deepseek-v4.1-flash-1017` / `llm_ds.env`（外部回填）；须核 env 文件存在、权限 600、模型 ID 与配置一致；本诊断未读 env。
3. **正式 seed + 两臂复制**：用冻结 `batch_tag=p2-298-20261021` 新建 seed 根 → build → build-gate → `build-copy` → §5.2 八条身份门（manifest SHA / fingerprint / 298 条 run_input sha / build_identity_ref / 代码聚合非旧 T-I / RDKit 同值）。
4. **批准包与 no-cap**：`p2_approved_record_20261021/`、四文书快照、`budget_no_cap.json`、`SHA256SUMS`。
5. **test/score 边界**：score 零 LLM 可直接在封存批上跑；run/test 会调用模型，必须等付费/HPC 授权与环境就绪，**不得用本诊断报告当作发车授权**。
6. **本诊断批根**：若只做零模型 score 管线演练，可用 `p2_build_diag_20261021_seed`；任何对外数字必须标注“诊断批、非 P2 冻结身份”。

## 10. 证据

目录：[`docs/review_evidence/p2_build_diag_2026-10-21/`](review_evidence/p2_build_diag_2026-10-21/)

| 文件 | 内容 |
|---|---|
| `environment.json` | 站点/环境/部署来源/排除项/校验 |
| `integration_selfcheck.txt` | HEAD、status、diffstat、prompt SHA、补丁 SHA、四件文件 |
| `four_patches_presence.json` | 四补丁 SHA、目标文件、树内逐文件 SHA、齐全判定 |
| `sbatch_p2_build_diag.sh` | 实际作业脚本 |
| `deploy_code_sha256.txt` | 96 个代码文件 SHA（部署时，远端实算） |
| `deploy_code_postcheck_sha256.txt` | 96 个代码文件 SHA（复检，远端实算；本地=远端） |
| `deployment_drift.json` | 部署后外部漂移：config 1 件 + 41 个 `__pycache__`，无 `.py` 变化 |
| `deploy_assets_sha256.txt` | 27 个资产文件 SHA（远端实算） |
| `deploy_inputs_sha256.txt` | 脚本与部署清单自身 SHA |
| `build_job_47081102.log` | 完整 build/gate 日志 |
| `build_identity.json` | 完整 build 身份旁块（298 条 qid/run sha，无题面） |
| `build_identity_summary.json` | 身份标量/资产身份/manifest 摘要 |
| `build_results.json` | 机器可读结果汇总 |
| `run_inputs_sha256.txt` | 298 个 run_input 逐文件 SHA |
| `top_level_sha256.txt` | manifest/identity/split SHA |
| `baseline_build_jobs_sacct.txt` | 基线 build 作业 sacct 原始输出 |
| `protected_pre_state.txt` / `protected_post_state.txt` / `protected_final_state.txt` | 保护树前/后/最终快照（含并发 T-I 活动记录） |
| `SHA256SUMS` | 以上证据文件校验和（不含自身） |