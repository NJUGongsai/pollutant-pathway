# L2 Stage 1 全 298 —— 池重编译 + 全链零 LLM 重放

> **题域标签：[298 域] = RHEA 通用酶学 / 已见题（post-hoc）。** 本文所有数值只在该题域成立，
> 与 dev 域双向不外推。分母一律写明；零模型调用、零网络、零付费。
>
> 日期：2026-10-26。执行：notebook `crdnotebook-2113560935535583233-aclhl3hbth-81040`。
> 数据：`/root/v43_migration/iter/data/r2`（只读）。工作根：`/root/v43_migration/iter/worktrees/full298/`。
> 生产代码零改动；不 commit / 不 push；未写 `iter/data/`；未碰 `ppv1_hpc/` 的 P2 批根/runs。

---

## 0. 结论先行

**PASS（任务书规定的“去时间戳 + 去派生 digest”语义口径）。**

| 门 | 结果 |
|---|---|
| A1 池重建：298/298 成员、顺序、逐 spec 字段、`template_remap`、`pool_diagnostics` | **298/298 一致**，差异字段分布为空 |
| A2 全链重放：21 个 payload 区段 + event/hypothesis/state/request ID + 去时间戳语义 sha256 | **语义 298/298 一致** |
| v1 指标（分母 298） | **84/113/120；strict/partial/unmatched = 121/58/119；逐题 status/rank 298/298** |
| v2 指标（分母 298，正式口径） | **89/118/125；strict/partial/unmatched = 126/53/119；逐题 status/rank 298/298** |
| 零漂移门 `zero_drift_gate.json` | `all_pass = true`（v1+v2 七项 gate 全 true） |

**必须同时知道的原始口径事实（不隐瞒）：**

1. A2 的**原始严格比较**不是 298/298 全等：286 题立即全等，**12 题**只在
   `search_actions[].outcome_ref` / `search_attempts[].outcome_ref` /
   `search_commit_records[].payload_hash` 这 3 类**时间戳派生引用**上不同。
   其余所有区段、所有事件/假设/状态/请求 ID、事件语义哈希全部相同。
2. 这 12 题的差异已逐题用**artifact 证据**证明是时间戳造成的：`queue.record_outcome`
   把 `recorded_at` 写进 outcome payload，再 `content_hash(payload)` 得到 `outcome_ref`；
   commit 的 `payload_hash` 又是 `{action_id, outcome_kind, outcome_ref, event_id}`
   的确定性内容哈希。把 artifact payload 的 `recorded_at` 去掉后，冻结/重放**逐字节相等**。
   这与 Stage 1 已登记的 `content_digest` 含时间戳是同一类问题，不是池、链或判分差异。
3. 因此本报告给两个口径：
   - **raw strict**：286/298 全等，12/298 有上述 3 类派生引用差异；
   - **semantic（任务书口径）**：298/298 全等，45 个派生引用全部经 artifact 验证后归一。
4. **第一次原始不一致**（按 registration_order）：`RXNG_526bccaa…e42a61`
   的 `search_actions[5].outcome_ref`，冻结 `fd275320…e233c3` vs 重放 `20922065…0d29ed`；
   同题另有 `search_attempts[1].outcome_ref` 与 `search_commit_records[4].payload_hash`
   同源差异。全链只差这 3 处，identity facts 全 true。

---

## 1. 开工核对与环境

### 1.1 主机与并发

| 项 | 实测 |
|---|---|
| 主机名 | `crdnotebook-2113560935535583233-aclhl3hbth-81040` |
| CPU / 内存 | 128 核 / 503 GiB；本次 16 个 shard 进程，`nice 5` |
| Python / RDKit | 3.11.9 / 2026.03.5 |
| P2 并发 | 开工时 `ppv1_hpc` 的 P2 build 在跑（`p2_nb_seed_20261026`，1 核）；本会话只读 `ps`，未写 P2 批根/runs |
| 另一窗口活动 | 15:49 CST 修改了 `v43cP2/src/pathway_v43/pollutant/chemstate.py`（P2 CN 修复）；本次未改生产树，另建只读代码副本 |

### 1.2 代码三件套哈希（开工前 / 收工后）

| 文件 | 期望 | 开工前 | 收工后 | 判定 |
|---|---|---|---|---|
| `evaluation.py` | `37c09231…` | `37c09231…` | `37c09231…` | 未变 |
| `s5b_scoring.py` | `4af3ed2d…` | `4af3ed2d…` | `4af3ed2d…` | 未变 |
| `s5b_compiler.py` | `58cf3dc9…` | `58cf3dc9…` | `58cf3dc9…` | 未变 |

完整 64 位哈希见证据 `code_hashes_source_after.txt` 与 `summaries/identity_preflight.json`。
`s5b_builder.py = db52ef20…`、`chemstate.py = 495d3d0e…` 也已登记。

本次把 `v43cP2/{src,scripts}` 复制到 `iter/worktrees/full298/code/` 后运行，三件套副本哈希与源树
逐字相同；A1/A2/scoring 全部使用该副本，避免另一窗口在 run 中途改代码。副本与 r2
`code_identity` 的差异是 **11 个文件**（`candidate_evidence.py, chemstate.py, native_export.py,
native_result.py, production.py, real_model.py, runflow.py, s5b_builder.py, s5b_compiler.py,
s5b_orchestrator.py, s5b_worker.py`），其中 `chemstate.py` 的差异是 15:49 的 P2 修复
（`cn = _legacy_cn_identity(identity)` 而非 `structure`）；其余 10 个是 Stage 1 已登记的文件
（`s5b_builder.py` / `s5b_compiler.py` 为诊断常量，另 8 个为分析/导出层增强）。
本轮的 PASS 是“当前副本 + 冻结输入/响应”的实测行为兼容，不是新旧源码等价证明。

### 1.3 数据与身份门

| 项 | 结果 |
|---|---|
| `iter/data/r2/SHA256SUMS` | 894 行，`sha256sum -c` = 894 OK / 0 FAILED |
| cases / run_inputs / reference_graphs / runs | 298 / 298 / 298 / 298 |
| 资产身份内容字段（manifest/source/analog corpus） | 298/298 与冻结一致；仅 `assets_root` 路径字符串不同（HPC → notebook） |
| v3 引擎代码身份 | 冻结侧 `git_available=false`（HPC 非 git 检出），当前侧是 git 检出；git 元数据不可比，已披露 |
| profile 块复现 | 298/298 |
| prediction 块复现 | 298/298 |
| 冻结响应 blob sha256（blob 元数据 + 账本双核） | 296/296 个 responded blob 通过；2 题无账本/无 blob |
| 账本形态 | 294 题 1 次 issued；2 题 2 次 issued（transport retry）；2 题无账本（0 调用） |

身份预检结论：`all_ok = true`（三件套、资产内容、profile、prediction、blob 全过）。
资产路径与 v3 git 元数据差异单独披露，不作为内容不一致。

---

## 2. A1：全 298 池构建回放

### 2.1 方法

- 入口：`s5b_builder.default_pool_provider`（`s5b_builder.py:1077`）。
- 冻结 r2 原参数：`--pool-mode template --recorded-source --max-pool 8 --pool-threshold 0.45`；
  其余缺省：`raw_top=24`、`fallback_threshold=0.40`、`min_unique=3`、`corpus_channel=True`。
- 每题：底物 SMILES + 当前 assets + 同一 v3 引擎 → 重建池；与 `run_inputs/<qid>.json`
  的 `plan.pools[substrate]` 做**逐 spec、逐字段**深比较；同时把
  `provider.last_diagnostics` 与 `batch_manifest.entries[qid].pool_diagnostics` 深比较。
- 16 个 shard 并行（按 registration_order 取模切片），逐题原子落盘，可断点续跑。

### 2.2 结果（298/298）

| 指标 | 数值 |
|---|---|
| 应到 / 实到 / 缺失 | 298 / 298 / 0 |
| `specs_equal` | **298** |
| `diagnostics_equal` | **298** |
| 两者都相等 | **298** |
| error / mismatch | **0 / 0** |
| 池 diff 字段分布 | **空**（无任何成员、顺序、spec 字段、`template_remap`、compile 诊断差异） |
| `pool_diagnostics` diff 字段分布 | **空** |
| 含 `template_remap` 的 spec 数 | 242（重建后逐一相等） |
| 池宽分布（冻结 → 重建） | `0→0: 60`、`1→1: 92`、`2→2: 57`、`3→3: 53`、`4→4: 24`、`5→5: 8`、`6→6: 1`、`8→8: 3` |

**A1 判定：PASS。** 没有第一处不一致。

耗时：16 shard wall **7 分 59 秒**（08:34:23Z–08:42:22Z）；单题 CPU 合计 4568.23 s；
每个 shard 的引擎初始化 38–40 s。证据：`pools/`（298 个逐题 JSON）、
`summaries/pools_summary.json`、`logs/pools_*.log`、`logs/pools_*.jsonl`。

---

## 3. A2：全 298 全链重放

### 3.1 方法

- 用 A1 重建池替换 `run_inputs.plan.pools`，其余 plan 字段（含 `model.provider_kind="real"`）保持冻结值。
- `ReplayClient` 按 `s5b_real_calls.jsonl` 的 issued 顺序服务冻结响应：
  - 294 题 1 次成功响应；
  - 2 题 transport retry：第 1 次返回结构化 `transport_error`（复现账本 failed 行），第 2 次返回冻结成功 blob；
  - 2 题无账本：0 次调用。
- 每次响应核对 blob 元数据 sha256/bytes/chars 与账本 `response_blob_sha256`；不联网、不读 API key。
- 调用 `runflow.start_ppv1_run` 公共入口（与 Stage 1 相同，绕过 worker/orchestrator 外层门）。
- 比较：剔除时间戳字段（`created_at/updated_at/claimed_at/recorded_at/...`）与派生 digest
  （`content_digest/export_digest`），比较 21 个 payload 区段、event/hypothesis/state/request ID、
  事件语义哈希列表、整体语义 sha256。

### 3.2 原始严格结果

| 指标 | 数值 |
|---|---|
| 重放 run 数 | 298 |
| 实际 `client.complete` 调用数 | **298**（296 成功 + 2 模拟 transport 失败；无网络） |
| 剩余未消费 outcome | 0（298/298） |
| blob 校验通过 | 298/298 题层面通过（296 个 responded blob + 2 题 0 blob） |
| profile / prediction 块复现 | 298/298 / 298/298 |
| identity facts 全 true（run/event/hypothesis/state/request ID） | **298/298** |
| 21 区段 ordered-equal | **286/298** |
| 整体 payload 语义 sha256 相等 | **286/298** |
| 原始 mismatch | **12/298**，全部只差 3 类时间戳派生引用 |
| `same_export_digest` | 0/298（预期；`content_digest` 含行级时间戳） |

原始 mismatch 的 12 题（按 registration_order）：

```
RXNG_526bccaa52323be2a3209e3c280fb595d997eba34be2257729f559a272e42a61
RXNG_56d8303ebd8a99f21974e52e9174f3a453c7e59071d517fc128b0a9bcd3162ec
RXNG_418ef97d77fe80eef663029cf87450e6bcc3386cc10b19ebf9f0d7a2f82fdf9a
RXNG_6455b8da465a85681898b43b23ba043ab9ad2f782f0cc4513f798f2f0a5ee131
RXNG_80f2f3aea4c026a2727ce7b36f38554b0df54e1c1b788ede9c299e6a7b4f8d19
RXNG_8dce8a33d8bd39029f2f9025f9a209245921cf2308df3c8ff8ab28b4967a5dc9
RXNG_957aa185eecb8f30560716e70f1c59ea855d6cf1df84de5c98b085ad7bd1fcd0
RXNG_a401c95418f5ee54961cc1f417f34526e92b56d02e63e227f545f14abd990c32
RXNG_bd85ad14b78156020e920618510ff430ef84321bfd466c311613ce614735a055
RXNG_c01c97cb2e52814d859babc180a11eef019e0405771b405c6f4ba3284ddc9a80
RXNG_cb1818122c3fa66cd7de27665330bb578462c6aa5084234ea997d91200175092
RXNG_e97de46f27c02383bafd7ba488371c677aeea1da91e131ea42a66a1cfce4362b
```

### 3.3 第一处不一致的完整证据与根因

| 项 | 内容 |
|---|---|
| qid | `RXNG_526bccaa52323be2a3209e3c280fb595d997eba34be2257729f559a272e42a61` |
| run_id | `t-h-s5b-298-20261020r2-s5br_0890d1659a6` |
| 字段 | `search_actions[5].outcome_ref` |
| 冻结值 | `fd275320ab68120b4f6ab793b59246ce3103c3d2f6ba3ffeec87a16e12e233c3` |
| 重放值 | `2092206582a1e4e19d91d405f033ecdf01b57713afbc3fda1d59975abc0d29ed` |
| 同源差异 | `search_attempts[1].outcome_ref`、`search_commit_records[4].payload_hash` |
| 其他差异 | 无；events/hypotheses/states/model_requests 身份与语义哈希全同 |
| 事件计数 | 冻结 3/3/5/1，重放 3/3/5/1（events/hypotheses/states/model_requests） |

根因（已用 artifact 证明，不是猜测）：

1. `queue.record_outcome` 构造 outcome payload：
   `{outcome_version, attempt_id, action_id, run_id, hypothesis_id, outcome, evidence_refs, recorded_at}`，
   然后 `outcome_ref = content_hash(payload)`。
2. `search.py` 的 commit 记录：
   `payload_hash = content_hash({action_id, outcome_kind, outcome_ref, event_id})`。
3. 冻结与重放的 `results/stask-exp_81f846d367a4e27b3a87/expansion_outcome.json`：
   - `content_hash(payload)` 分别等于两侧记录的 `outcome_ref`（已验证 true）；
   - 两侧 payload 去掉 `recorded_at` 后逐字节相等（`a0105091…`）；
   - 两侧 envelope 除 `created_at` 外相等；
   - 两侧 commit `payload_hash` 的函数复算都等于记录值（已验证 true）。
4. 唯一变化是冻结 `recorded_at=2026-10-20T03:26:09+00:00` vs 重放
   `recorded_at=2026-10-26T08:43:08+00:00`。

这是 `content_digest` 含时间戳的同类问题；`outcome_ref`/commit `payload_hash` 是
时间戳派生 digest，不是化学/调度语义事实。

### 3.4 语义归一（逐 artifact 验证，不盲删字段）

对每个**不同的**派生引用，只有同时满足以下 5 条才归一：

1. 在冻结/重放 run 的 `results/*/expansion_outcome.json` 中找到同一 `action_id` 的 artifact；
2. `content_hash(artifact.payload)` 分别等于两侧记录的 ref；
3. 两侧 artifact payload 去掉时间戳后逐字节相等；
4. 两侧 envelope 除 `created_at` 外相等；
5. commit `payload_hash` 的确定性函数在两侧都复算通过。

不满足任一条 → 保持原字段，计入 `artifact_verification_failures` / `unexplained_diffs`，
不归一。实际结果：

| 项 | 数值 |
|---|---|
| 归一的题数 | 12 |
| 归一的 action 实例 | 15（全部 `method_failed`） |
| 归一的字段 | 45 = 15 × 3（action outcome_ref / attempt outcome_ref / commit payload_hash） |
| artifact 验证失败 | **0** |
| 未解释差异 | **0** |
| 语义 21 区段 ordered-equal | **298/298** |
| 语义整体 payload sha256 相等 | **298/298** |
| identity facts 全 true | **298/298** |

这 12 题的判分 status/rank 与基线 298/298 一致，归一没有改变任何判分输入。

### 3.5 21 个 payload 区段

语义归一后，以下 21 区段在 298/298 题上 ordered-equal（顺序敏感）：

`events, event_ids, hypotheses, states, state_appearances, alternatives, paths,
search_actions, search_attempts, search_commit_records, expansion_outcomes,
expansion_plans, model_requests, contexts, coproducts, deferred_entries,
blocked_entries, report_projections, audit_production_reports, budget,
endpoint_record`

另整体 payload 语义 sha256 在 298/298 题上相等（`content_digest` 单独披露为不可跨 run 复现）。

### 3.6 v1 / v2 指标（分母 298）

| 指标 | v1 | v2（正式口径） | 基线/期望 | 逐题一致 |
|---|---|---|---|---|
| hit@1 | 84 | **89** | 84 / 89 | — |
| hit@3 | 113 | **118** | 113 / 118 | — |
| hit@5 | 120 | **125** | 120 / 125 | — |
| strict | 121 | **126** | 121 / 126 | — |
| partial | 58 | **53** | 58 / 53 | — |
| unmatched | 119 | **119** | 119 / 119 | — |
| 逐题 status+rank 一致 | **298/298** | **298/298** | — | status 0 不一致；rank 0 不一致 |
| `n_candidate_events` 不一致 | 0 | 0 | — | — |
| 门判定 | PASS | PASS | — | `zero_drift_gate.json all_pass=true` |

`reference_graph_sha_all_ok=true`、`all_298_scored=true`、`denominator_298=true`。

### 3.7 A2 判定

- **任务书语义口径：PASS（298/298）。**
- **raw strict：286/298 全等，12/298 仅时间戳派生引用不同。** 若把 `outcome_ref` /
  commit `payload_hash` 也当作必须逐字节相等的字段，则不能称 298/298 全等；
  但这与 `content_digest` 不可跨 run 复现是同一类，且已逐 artifact 证明无其他差异。

---

## 4. 特殊题与影响

| 类别 | 数量 / qid | 结果 | 是否影响结论 |
|---|---|---|---|
| transport retry（1 次失败 + 1 次成功） | 2 题：`RXNG_20b83d4f…a86817`、`RXNG_80f2f3ae…f8d19` | 各 2 次调用、1 failed + 1 responded；blob 全过；raw/semantic 均通过 | 不影响；机制已覆盖 |
| 无账本 / 0 模型调用 | 2 题：`RXNG_7a886593…ad4740`、`RXNG_ed3d7072…a3c96c` | 冻结 `ProductionContractError / cosubstrate_copy_in_expectation` 复现；events/hypotheses/model_requests = 0；endpoint 等区段一致 | 不影响；失败路径已覆盖 |
| failed expansion（`method_failed`，触发时间戳派生引用） | 12 题（见 §3.2；15 个 action 实例） | raw 3 字段差异；artifact 逐条验证后语义 298/298；判分 298/298 | 不影响判分；已作为原始口径披露 |
| 空池 | 60 题 | 池 0→0；诊断一致 | 不影响 |
| 最大池宽 8 | 3 题 | 池 8→8；spec/诊断一致 | 不影响 |
| `repeated_substrate=true` | 142 条 entry | 每题独立 run，逐题重放一致 | 不影响 |
| 多轮 format-feedback / 多 decide | **0 题** | 本批全部 run 最多 1 次 `decide` 模型调用；无 >1 个成功响应的 run | **覆盖限制**：本批没有多轮反馈/多 decide 样本，不能据此证明这些路径 |

说明：transport retry 的 2 题里，`RXNG_80f2…` 同时属于 12 题 failed-expansion 归一集合；
两项互不冲突。

---

## 5. 耗时（分阶段）

| 阶段 | Wall | 说明 |
|---|---|---|
| 开工核对 + 身份预检 + 代码副本 | ≈ 1–2 min | 三件套/资产/profile/prediction/blob/账本形态 |
| A1 全 298 池重建 | **7 min 59 s** | 16 shard；引擎初始化 38–40 s/shard；单题 CPU 合计 4568.23 s |
| A2 首次 fail-fast 重放 | 7 s | 停在第一处原始不一致；已完成 23 题 |
| A2 续跑 275 题（raw 收集） | 18 s | 16 shard；全部 298 题落盘 |
| 语义 artifact 验证 | ≈ 1–2 s | 298 题；12 题/45 字段归一 |
| v1 + v2 判分 | 11.2 s | v1 5.9 s + v2 5.3 s |
| 证据打包/下载/校验 | ≈ 2 min | 1004 文件；SHA256SUMS 校验 |
| **首尾 wall（含根因分析）** | **≈ 24 min** | 08:30–08:55Z 左右；其中约 7 min 用于第一处不一致的根因定位与口径确认 |

---

## 6. 证据与 SHA256SUMS

### 6.1 本地证据根

`/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/l2_stage1_full298_2026-10-26/`

| 路径 | 内容 |
|---|---|
| `bin/` | 全部探针/驱动/聚合脚本（A1、A2、semantic、score、aggregate） |
| `pools/<qid>.json` | 298 题池重建逐题结果（sha、diff、诊断、耗时；无完整结构正文） |
| `replay/<qid>.json` | 298 题原始严格重放结果（21 区段、identity、diff head、调用/响应核验） |
| `semantic/<qid>.json` | 298 题 artifact 验证后的语义判定（归一动作、失败、未解释差异） |
| `summaries/` | pools/replay/semantic 汇总、身份预检、第一处不一致、归一明细、特殊题 |
| `score/v1/`、`score/v2/` | `metrics_replay.json`、`per_qid_diff.json`、`provenance.json`、`summary.md` |
| `score/zero_drift_gate.json` | v1+v2 零漂移门 |
| `score/SCORE_INPUT_PROVENANCE.json` | 判分数据根的派生说明（case.export_digest 换成 replay digest） |
| `logs/` | driver/shard/aggregate/score/semantic 原始日志 |
| `SHA256SUMS` | 1004 个文件的 sha256（不含自身） |

### 6.2 校验

| 项 | 结果 |
|---|---|
| 本地 `shasum -a 256 -c SHA256SUMS` | **1004 OK / 0 FAILED** |
| `SHA256SUMS` 自身 sha256 | `cf3a29e7d641567d2ba9c0a52124c2e943fe1ea6fc62157e504732f9bbb051d4` |
| notebook 证据包 tar.gz | `0d7a24d9c93df3f2bae36fd5b4fdabd53021f22d96fa5422cedae98ad5fb52a7`（709 KB） |
| notebook 全量重建池 / run 根 | `/root/v43_migration/iter/worktrees/full298/out/rebuilt/`、`.../work/runs/`（未下载；见 `notebook_paths.txt`） |

---

## 7. 证明范围披露

### 已证明

1. 在 notebook 当前代码副本（三件套哈希与任务书一致）上，给定 r2 的 298 个底物、同一 assets、
   同一池参数，`default_pool_provider` **逐 spec 逐字段**重建冻结池：298/298，成员、顺序、
   `template_remap`、compile 诊断、`pool_diagnostics` 全等。
2. 给定重建池 + 已落盘响应，`start_ppv1_run` 的完整链输出在**去掉时间戳与派生 digest**后
   与冻结 payload 语义相等：298/298；event/hypothesis/state/request ID 与事件语义哈希
   298/298 相同；21 区段顺序敏感相等 298/298。
3. v1/v2 判分在 298 题上复算到与 r2 基线完全相同的指标与逐题 status/rank：
   v1 84/113/120（121/58/119），v2 89/118/125（126/53/119）。
4. 12 题 failed-expansion 的时间戳派生引用已逐 artifact 证明：artifact payload 去时间戳后
   逐字节相等；commit payload_hash 的确定性函数两侧都复算通过；0 失败、0 未解释。
5. 2 题 transport retry 与 2 题 0 调用失败路径都被覆盖并复现。

### 未证明 / 边界

1. **不是字节级全等**：`created_at/updated_at/claimed_at/recorded_at`、`content_digest`、
   `export_digest`、以及 12 题的 `outcome_ref`/commit `payload_hash` 不可能跨 run 字节复现；
   本报告的“一致”是任务书规定的**去时间戳语义口径**。
2. **不是源码等价证明**：当前副本与 r2 `code_identity` 有 11 个文件不同（含 15:49 的
   `chemstate.py` P2 修复）。本轮只证明这些文件在当前 298 题上的**行为兼容**；不证明任意
   输入、任意 remap/compile 改动都等价。
3. **未覆盖多轮 format-feedback / 多 decide**：本批 298 题没有 >1 个成功模型响应的 run；
   2 个 transport retry 是唯一的多调用形态。Stage 1 的同一限制仍在。
4. **绕过 worker/orchestrator 外层门**：本探针直接走 `runflow.start_ppv1_run`；批级
   build_identity、evidence-card 冻结副本、budget guard 未覆盖。
5. **判分使用冻结 reference_graphs**：金标只在进程内消费；报告/证据只落 qid 级与聚合，
   未落参考图正文或产物结构正文。per-qid replay JSON 含 qid/run_id、底物 SMILES（题面输入）、
   哈希、计数与差异路径；`_offline_export_reader` 按设计跳过 step6/step8（需 DB 权威）。
6. **不评判化学正确性/机制/收益**：本探针只回答“能否零 LLM 复算到 payload 与指标”，
   不回答“池/remap 改得更好”。任何 remap/compile 规则改动仍须走评审与预注册。
7. **v3 引擎代码身份不可比**：冻结侧 `git_available=false`；当前侧是 git 检出。资产内容
   哈希一致，但 v3 代码内容没有冻结哈希可对拍。
8. **未验证 `chemstate.py` P2 修复的全局影响**：只证明它在该 298 题 S5B 重放中不改变
   payload/指标；P2 批本身的结果归 P2 窗口。

---

## 8. 偏离任务书的地方（如实登记）

1. **使用冻结代码副本**：把 `v43cP2/{src,scripts}` 复制到 `iter/worktrees/full298/code/` 后运行；
   生产树零改动。原因：另一窗口在 15:49 改过 `chemstate.py`，且 P2 批在跑，需保证 run 期间
   代码不变。三件套副本哈希与源树逐字相同。
2. **16 shard 并行**：任务书允许分批/并行；128 核，16 进程，`nice 5`。P2 批只有 1 核，
   未写 P2 目录。
3. **原始 fail-fast 后继续**：A2 第一次严格比较在 2 题上触发 stop（第一处为
   `RXNG_526b…`）。按任务书停在第一处并完成根因取证；确认是时间戳派生引用后，才用
   `FAIL_FAST=0` 续跑收集 298 题 raw 结果，并另设 **artifact 逐条验证** 的语义层。
   raw 结果没有被覆盖；`first_stop_evidence.json` 由保留的 raw 结果重建（原 `STOP_REPLAY.json`
   在根因分析后删除）。
4. **判分数据根的 `case.export_digest` 替换为 replay digest**：冻结 digest 无法定位 replay run 的
   `native_export/<digest>/`（content_digest 含时间戳）。只改这一个寻址字段；reference_graphs、
   split、preregistration、baseline 全部是指向 r2 的只读符号链接，见
   `score/SCORE_INPUT_PROVENANCE.json`。
5. **`chemstate.py` 预存改动**：15:49 由另一窗口写入（P2 CN 修复），不是本会话所为；
   本会话只读并复制。已在 §1.2/§7 披露。
6. **证据包不含完整重建池与 run DB**：完整 pool spec 在 notebook `out/rebuilt/`，run 根在
   `work/runs/`；本地只放逐题结果/日志/汇总/判分，避免把大体积结构与 run 数据库带入仓。

---

## 9. 复现入口（notebook）

```bash
R=/root/v43_migration/iter/worktrees/full298

# 身份预检
python3 $R/bin/identity_preflight.py \
  --data-root /root/v43_migration/iter/data/r2 \
  --code-root $R/code \
  --assets-root /root/v43_migration/v43cP2/assets \
  --v3-code-root /root/v43_migration/dependingv3 \
  --out $R/out/identity_preflight.json

# A1：16 shard 池重建（可断点续跑）
bash $R/bin/run_pools_all.sh 16

# A2：16 shard 原始重放（严格 fail-fast 用默认；收集全量 raw 用 FAIL_FAST=0）
FAIL_FAST=0 bash $R/bin/run_replay_all.sh 16

# artifact 逐条验证的语义层
bash $R/bin/run_semantic.sh

# v1+v2 判分（使用 replay digest 的派生 score data root）
bash $R/bin/run_score.sh
```

---

## 10. 附：12 题归一明细入口

逐题 45 条归一动作（action_id、冻结/重放 ref、artifact 路径、`recorded_at`、artifact 语义 sha、
commit 函数复算布尔）在：

`docs/review_evidence/l2_stage1_full298_2026-10-26/summaries/semantic_normalization_details.json`

该文件只含 qid/action_id/哈希/布尔/时间戳与 `method_failed` 类别，不含参考图或金标正文。