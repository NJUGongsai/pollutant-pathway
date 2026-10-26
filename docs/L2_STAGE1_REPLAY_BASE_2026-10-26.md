# L2 迭代工坊 Stage 1 —— 重放基座 + 重编译可行性（Step 4/5）

> **题域标签：[298 域] = RHEA 通用酶学 / 已见题（post-hoc）。** 本文所有数值只在该题域成立，
> 与 dev 域双向不外推。分母一律写明；金额一律 unknown（本阶段零付费调用）。
>
> 日期：2026-10-26。执行：notebook `crdnotebook-2113560935535583233-aclhl3hbth-81040`。
> 性质：零模型调用、零网络、零付费；只读 r2 数据副本；生产代码零改动；不 commit / 不 push。
>
> 本文件覆盖任务书 `docs/TASK_L2_ITER_WORKSHOP_2026-10-26.md` 的 **Step 4（重编译可行性探针）
> + Step 5（报告）**；Step 1–3 的零漂移门与数据搬迁已在上一轮完成，本文 §1.3 只引用其证据。

---

## 0. 结论先行

**PASS。** 对抽样的 3/298 道题：

1. **池重建逐字段一致（canonical 字节同）**：用 r2 原 build 参数（`--pool-mode template --recorded-source
   --max-pool 8 --pool-threshold 0.45`）重跑 `default_pool_provider`，得到的候选池与冻结
   `run_inputs/<qid>.json` 的 `plan.pools[substrate]` **成员、顺序、每个 spec 的全字段、
   `template_remap` 披露、`compile` 诊断**全部相等（3/3，`diff_count=0`）。
2. **全链重放语义一致**：用重建池 + 已落盘模型响应（零 LLM）重跑 `start_ppv1_run`，
   产出 payload 与冻结 `native_export/<digest>/payload.json` 在**去掉时间戳与派生 digest 后
   整体逐项相等**；`event_id` / `hypothesis_id` / `state_id` / `request_id` 全部相同，
   事件顺序相同，v2 口径 `match_status` / `rank` 相同（3/3）。
3. **负控有分辨力**：`max_pool 8→2` 使池 4→2 且全链重放立即分叉（events 8→0、payload 80 处差异）；
   在工作副本里关掉 remap 后，两个 remap 重题池 3→0、4→0。探针不是“永远相等”。

**这决定了什么**：`compile / remap / identity` 类改动**可以零 LLM 验证**——前提是重跑
“池构建（compile）”而不是只拿 `run_inputs` 里的已编译池；验证对象是
**池 spec 的字节相等**与**给定冻结响应后的全链语义相等**。注意：**池一变，旧模型响应
可能失效**（响应引用旧 hypothesis ID）；这种改动只能零 LLM 做到“池级对拍”，末段指标
要么重调模型（付费），要么把实验限制在响应仍可解析的题上（详见 §7.2）。

**一个必须知道的口径事实**：`payload.content_digest` 与 `native_export/export_digest`
内含行级 `created_at`，跨 run 不可能字节重现（native_export 的“无时间戳”指导出层不新增
时间戳，不是底层行没有时间戳）。因此 L2 的相等判据必须是“**去时间戳 + 去派生 digest 的
语义哈希**”，不能拿 `export_digest` 当跨 run 身份。

---

## 1. 代码、资产与环境核对

### 1.1 任务书要求的三件套哈希（notebook，2026-10-26 14:39 CST）

```
37c092310d34d9f417234ccacd508942b3ce3edef640c73ab94022fd8dc75ad8  src/pathway_v43/pollutant/evaluation.py
4af3ed2d60f97a3460df92027d2bb2b280b92c5956e81c475ee262cf33549ca3  src/pathway_v43/pollutant/s5b_scoring.py
58cf3dc94dd83cbf8245c9e2117ac50f41e847c685663321af973f637fba7058  src/pathway_v43/pollutant/s5b_compiler.py
```

与任务书期望逐字一致（`37c09231…` / `4af3ed2d…` / `58cf3dc9…`）⇒ **未被污染，继续**。
未发现 python/pytest/批任务在跑；另一窗口 14:24 对 `v43cP2` 的 `git init` 没有 commit
（`master` 无提交），工作树全为 `A`（staged）状态，不影响只读使用。

### 1.2 与 r2 build 身份的全量对照（87 文件）

r2 的 `run_identity.json.code_identity` 记录 87 个源文件的 sha256。notebook 当前
`v43cP2/src` 对照结果：**0 缺失，10 个文件哈希不同**：

`candidate_evidence.py, native_export.py, native_result.py, production.py, real_model.py,
runflow.py, s5b_builder.py, s5b_compiler.py, s5b_orchestrator.py, s5b_worker.py`

其中 **compile 层只有两个文件**，与 HPC r2 部署（`~/EnzymeAgent/v43cTH`，哈希与 r2
identity 逐字相同）做 unified diff：

| 文件 | r2 → notebook 当前 | 性质 |
|---|---|---|
| `s5b_compiler.py` | +18 行 / −0 行 | 仅 P0b/D-6 诊断常量（`P0B_D6_COMPILED_DECLARATION_BOUNDARY` 与 `compiled_declaration_boundary()`），不参与编译 |
| `s5b_builder.py` | +16 行 / −0 行 | 仅 P0b/D-6 诊断常量（`P0B_D6_ASSEMBLED_DECLARATION_BOUNDARY` 与 `assembled_declaration_boundary()`），不参与装配 |

完整 patch：`/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/l2_stage1_2026-10-26/step4/code_diff_compile_layer.patch`。
其余 8 个文件是 r2 之后的分析/导出层增强（P0b/D-6 等，行数增量较大，`runflow.py`
+212/−40、`production.py` +711/−0 等）；本次全链重放用的就是这些**新代码**，仍做到语义
逐项相等（见 §4），说明这 3 题上新旧代码行为兼容，但这是**实测证据**，不是源码级等价证明。

### 1.3 资产与上一轮门（引用，不重跑）

| 项 | 结果 |
|---|---|
| `analog/corpus_templates_v1.jsonl` | sha256 `8f3f2c1a…` 与 r2 `asset_identity` 一致 |
| `v3_reactions/library/library_full.jsonl` | sha256 `042e9e2c…` 一致 |
| `assets/MANIFEST.sha256` | sha256 `ac9b97b8…` 一致 |
| 零漂移门 v2 | 298 题：hit@1/3/5 = 89/118/125；strict/partial/unmatched = 126/53/119；逐题 298/298 一致（`…/rounds/r000/zero_drift_gate.json`） |
| 零漂移门 v1 对照 | 84/113/120；strict 121；桶 121/58/119；逐题 298/298 一致 |
| 数据搬迁 | 6,382 文件 / 146,242,738 字节；`SHA256SUMS` 894 OK / 0 FAILED；`pollutant.sqlite` 未搬（`…/migration_manifest.txt`） |

RDKit：notebook `2026.03.5`，与 r2 批内登记一致。所有实验都在 notebook 上做，Mac 未参与。

---

## 2. compile 的输入清单与模型响应位置

### 2.1 关键事实：`run_inputs` 里放的是“已编译产物”，不是原始模板

| 对象 | 路径/形态 | 说明 |
|---|---|---|
| run 输入 | `<data>/run_inputs/<qid>.json` | 顶层 `qid / run_id / substrate_smiles / note / plan`；`plan.pools[<substrate>]` = **已编译 spec 列表**（含 `edits/donor/alignment/expectation/compile/co_substrate_states/…`），`plan.model.provider_kind="real"` |
| 冻结池消费点 | `src/pathway_v43/pollutant/runflow.py:829-840`（`_pool_for`） | runflow **原样消费** `plan.pools`，不在运行时重编译 |
| 真正的编译入口 | `src/pathway_v43/pollutant/s5b_compiler.py:1416`（`compile_donor_template`） | 入参：`mapped_lhs, mapped_rhs, center_atoms, substrate_smiles, record_id, mapping_origin, alignment_ref, key_prefix, render_name` |
| 编译调用点（池构建） | `src/pathway_v43/pollutant/s5b_builder.py:1345,1383`（`_compile_at`） | `default_pool_provider`（`s5b_builder.py:1077`）逐候选编译；编译成功才入池 |
| remap 入口 | `src/pathway_v43/pollutant/s5b_compiler.py:530`（`complete_template_mapping`） | 只在 `extract_mapped_transform` 抛 `transform_no_change` 时触发（`compile_donor_template` 的 pre-flight，约 1459-1478 行）；无数字阈值，是确定性规则 + 规则版本 `S5B_TEMPLATE_REMAP_VERSION`（186 行） |

**结论**：想重跑 compile，不需要 `run_inputs` 里的池本身；需要的是
**底物 SMILES + 同一套 assets + 同一组池构建参数**，由 `default_pool_provider` 重新检索
模板并调用 `compile_donor_template`。`run_inputs` 的池是**对拍基准**。

严格说，只靠 `run_inputs` **无法反推**原始 mapped template 串：spec 里的原子 ID 是底物侧
`S_*`（由当前底物命名空间生成），不是模板的 map 号；`compile.template_center_maps` 只给
中心 map 集合，不给完整 mapped SMILES。因此“重跑 compile”的输入必须是
**底物 + assets + 池参数**。好在这些在 notebook 上都齐：assets 三个关键哈希与 r2
`asset_identity` 逐字一致，池参数在 `scripts/hpc/sbatch_th_build.sh` 里冻结。

### 2.2 r2 的池构建参数（来自 `scripts/hpc/sbatch_th_build.sh`）

```
--provider-kind real --pool-mode template --recorded-source \
--max-pool 8 --pool-threshold 0.45 \
--v3-code-root <HPC>/EnzymeAgent/dependingv3 --assets-root <HPC>/EnzymeAgent/v43cTH/assets
```

其余池参数取代码缺省：`raw_top=24`、`fallback_threshold=0.40`、`min_unique_targets=3`、
`corpus_channel=True`（`s5b_builder.py:515-519,1077-1085`）。

### 2.3 模型响应位置与形态

| 对象 | 路径/形态 |
|---|---|
| 调用账本 | `<run>/s5b_real_calls.jsonl`（追加；每逻辑调用先 `issued` 后 `responded` 行；`responded` 行含 `request_id / request_key / purpose / usage / response_blob_sha256 / provider_request_id / elapsed_s`） |
| 权威响应 blob | `<run>/s5b_responses/<request_id>.json`；`{"blob_version":"s5b-response-blob-1","request_id","request_key","purpose","sha256","bytes","chars","content","saved_at"}`；`content` 是完整最终文本（不截断） |
| 本次 3 题 | 各 **1 次**逻辑调用（账本 2 行 = issued + responded，blob 1 个） |
| 冻结导出 | `<run>/native_export/<digest[:24]>/{payload.json,manifest.json}` |
| 可重放机制 | `real_model.py:ppv1_real_fetch` 支持 “responded + 有效 blob ⇒ 零调用消费”（R3）；本次重放不需要改生产代码，用一个只返回冻结 blob 的最小客户端即可 |

### 2.4 最小调用示例（后续矩阵照抄）

池构建（compile 层，零 LLM）：

```python
import sys
sys.path.insert(0, "/root/v43_migration/iter/worktrees/probe_compile/code/src")
from pathway_v43.config import resolve_config
from pathway_v43.adapters.v3_engine import get_engine
from pathway_v43.pollutant.s5b_builder import default_pool_provider

config = resolve_config(
    v3_code_root="/root/v43_migration/dependingv3",
    assets_root="/root/v43_migration/v43cP2/assets")
engine = get_engine(config)                      # 进程内资产身份单例
provider = default_pool_provider(
    config, max_pool=8, raw_top=24, threshold=0.45,
    fallback_threshold=0.40, min_unique_targets=3,
    engine=engine, corpus_channel=True)
rebuilt_pool = provider(substrate_smiles)        # == run_inputs.plan.pools[substrate]
```

全链重放（给定池 + 冻结响应，零 LLM）：

```python
from pathway_v43.pollutant.runflow import start_ppv1_run
from pathway_v43.pollutant.real_model import RealModelAdapter, S5B_CALL_ACCOUNT_FILE

model = RealModelAdapter(
    replay_client,                               # 按账本顺序返回 s5b_responses/<request_id>.json 的 content
    call_account_path=runs_root / run_id / S5B_CALL_ACCOUNT_FILE)
summary = start_ppv1_run(
    config=config, runs_root=runs_root, run_id=run_id, smiles=substrate,
    plan={"pools": {substrate: rebuilt_pool}, "model": {"provider_kind": "real"}},
    model=model,
    profile_policy=frozen_profile_kwargs,        # 从 r2 run_identity.profile 反推 kwargs
    evidence_card_enabled=False)                 # 与 r2 strategy.evidence_card_enabled 同值
```

完整可执行脚本（含 blob 读取、比较、v2 打分）：
`/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/l2_stage1_2026-10-26/step4/bin/pools_probe.py`
与 `…/step4/bin/replay_probe.py`；notebook 工作副本在
`/root/v43_migration/iter/worktrees/probe_compile/`（`code/` 是 `v43cP2` 的 src+scripts 副本，
`code_nc_noremap/` 只用于负控，生产树零改动）。

---

## 3. 3 题选择与池重建结果

### 3.1 选题（v2 口径，来自 r2 `metrics.json` / `per_qid_diff.json`）

| 桶 | qid | v2 rank | 池宽 | 池来源构成 | 带 `template_remap` 的候选数 |
|---|---|---|---|---|---|
| strict 命中 | `RXNG_8ee93e3c…70acd3dd` | 1 | 3 | 2 个 recorded 推断映射（`rec-*`）+ 1 个 analog 模板 | 1 |
| partial | `RXNG_32293b69…1d388` | — | 3 | 3 个 analog 模板 | 3 |
| unmatched | `RXNG_036534a3…8d762bab` | — | 4 | 4 个 analog 模板 | 4 |

完整 qid（便于复现；qid 级信息，非金标内容）：

```
RXNG_8ee93e3c64f8c72d087c22ab2e3acdcf27740966fb1e187a37869c5b70acd3dd   # strict rank 1
RXNG_32293b693909ff88460f19bea98475ede7ae1cb8985ae0725062be223a21d388   # partial
RXNG_036534a3cd44ca02a8ea600357cdfc927dfb425471464464c89234af8d762bab   # unmatched
```

三题覆盖：recorded 推断映射通道、analog 原生映射通道、remap 触发路径。

### 3.2 池重建对拍（原参数，零 LLM）

| qid | 冻结池 n | 重建池 n | 深比较 diff | 池 canonical sha256（冻结 = 重建） | batch_manifest `pool_diagnostics` 对拍 |
|---|---|---|---|---|---|
| `RXNG_8ee93e3c…` | 3 | 3 | 0 | `51368309ebfe…` | 相等（diff 0） |
| `RXNG_32293b69…` | 3 | 3 | 0 | `2958480acf83…` | 相等（diff 0） |
| `RXNG_036534a3…` | 4 | 4 | 0 | `8437089271d2…` | 相等（diff 0） |

“深比较”是逐 spec、逐字段的 JSON 结构比较（含 `edits`/`donor`/`alignment`/`expectation`/
`compile` 诊断/共底物字段/`template_remap`），不是只比 key 或数量。`pool_diagnostics`
对拍的是 r2 build 时写进 `batch_manifest.json` 的逐候选谱系行（编译成功/拒因/合并/截断），
同样完全一致。

证据：`…/step4/out/pools_base.json`、`…/step4/logs/pools_base_all.log`。

---

## 4. 全链重放结果（零 LLM）

### 4.1 方法

- 用 §2.4 的重建池替换 `run_inputs.plan.pools`，其余 plan 字段（含 `model.provider_kind="real"`）
  保持冻结值；
- `ReplayClient` 只按 `s5b_real_calls.jsonl` 的 `responded` 顺序返回
  `s5b_responses/<request_id>.json` 的 `content`（并带上记录的 usage/elapsed/HTTP 尝试元数据），
  不发网络；每次运行都核对 blob sha 与账本 `response_blob_sha256`；
- profile 策略从 r2 `run_identity.profile` 反推 kwargs 再重建，**与原 profile 块逐字段相等**；
- 每题的 `request_id` 由 `stable_id("sreq", run_id, attempt_id, provider_kind, request_key)`
  推导；plan 池字节相同 ⇒ action/request key 相同 ⇒ request_id 相同（实测 3/3 相同）。

### 4.2 逐项比较表（PASS/FAIL）

时间戳字段（`created_at/updated_at/claimed_at/done_at/...`）在比较前剔除；`content_digest`
是派生摘要，单独列示。

| 检查项 | `RXNG_8ee93e3c…`（strict r1） | `RXNG_32293b69…`（partial） | `RXNG_036534a3…`（unmatched） |
|---|---|---|---|
| 重放模型调用数 / 网络 | 1 / 0 | 1 / 0 | 1 / 0 |
| blob sha 与账本一致 | PASS | PASS | PASS |
| profile 块复现 | PASS | PASS | PASS |
| 事件数（冻结 → 重放） | 7 → 7 | 4 → 4 | 8 → 8 |
| 假设数（冻结 → 重放） | 7 → 7 | 4 → 4 | 8 → 8 |
| 状态数（冻结 → 重放） | 9 → 9 | 7 → 7 | 15 → 15 |
| model_requests 数（冻结 → 重放） | 1 → 1 | 1 → 1 | 1 → 1 |
| 21 个 payload 区段（events/hypotheses/states/state_appearances/alternatives/paths/search_actions/search_attempts/search_commit_records/expansion_outcomes/expansion_plans/model_requests/contexts/coproducts/deferred_entries/blocked_entries/report_projections/audit_production_reports/budget/endpoint_record/event_ids） | 全等（顺序敏感） | 全等 | 全等 |
| `event_id` 列表/顺序 | 相同 | 相同 | 相同 |
| `event_semantics_hash` 列表 | 相同 | 相同 | 相同 |
| `hypothesis_id` 列表 | 相同 | 相同 | 相同 |
| `state_id` 列表 | 相同 | 相同 | 相同 |
| `request_id` 列表 | 相同 | 相同 | 相同 |
| 语义 payload sha256（去时间戳、去 `content_digest`） | 相同 | 相同 | 相同 |
| v2 `match_status` | `matched_strict` = `matched_strict` | `matched_participant_coverage_partial` = 同 | `unmatched_required_node_uncovered` = 同 |
| v2 `rank` | 1 = 1 | None = None | None = None |
| v2 `n_candidate_events` / 重算候选数 | 7 / 7 = 7 / 7 | None / 4 = None / 4 | None / 8 = None / 8 |

**唯一差异**：`payload.content_digest`（以及由它派生的 `export_digest`）因 `created_at`
不同而不同。整体 payload 去掉时间戳后只有这 1 处差异；所有业务区段 0 差异。

证据：`…/step4/out/replay_base_<qid>.json`、`…/step4/out/final_verify.json`、
`…/step4/logs/replay_base_*.log`。

### 4.3 这说明什么

对同一 `(底物, assets, 池参数, 模型响应)`，整条链（compile → prepare_hypothesis →
AtomTool 执行 → 审计/准入 → 事件/提交 → endpoint → native export）在**新代码**上
是确定性的；模型响应是唯一“外部输入”，而它已经落盘且可被零调用消费。因此：

> **remap / compile / identity 类改动可以在零 LLM 条件下验证**——只要改动后
> 重建池仍能给出与冻结池同成员、同顺序、同内容的 spec（或你有意让它变），
> 后续链就能用同一批冻结响应复算到指标。

---

## 5. 负控（证明探针有分辨力）

### NC-1：改池宽 `max_pool 8 → 2`（改动后必须看得见）

- 池重建：`RXNG_036534a3…` 冻结 4 → 重建 2（`pool.len` 1 处差异）。
- 全链重放（仍只用冻结响应，零 LLM）：events **8 → 0**；hypotheses 8 → 0；
  `event_id`/`hypothesis_id`/`state_id`/`request_id` 全部不等；整体 payload **80 处差异**
  （budget 27、search_actions 39、endpoint_record 13、events/hypotheses/states 各 1 等）。
- 机制（如实披露）：池截断后，冻结响应里引用的候选 hypothesis 不在新池，解析转
  format-feedback 轮，产生**原 run 没有的第二次模型请求**（`purpose=format_feedback`，
  `status=sent`）；零 LLM 重放没有这条响应，链接 fail-closed 停在 `budget_limit /
  awaiting_prediction`。这正说明“池变了，旧响应不再有效”，探针能识别。
- v2 打分对比：`n_candidates_recomputed` 8 → 0，`score_equal=false`。

### NC-2：在工作副本关掉 remap（`complete_template_mapping` 直接返回 `no_gap`）

- 只改 `code_nc_noremap/` 副本（哈希 `7f356aef…`；生产 `code/` 仍 `58cf3dc9…`）。
- remap 重的两题池全部塌缩：`RXNG_32293b69…` 3 → **0**，`RXNG_036534a3…` 4 → **0**。
- 说明：这两题的候选全部依赖 `transform_no_change → 补映射` 才能编译；remap 路径不是
  边角，关掉即无池。也证明池重建探针能观测 remap 语义变化。

证据：`…/step4/out/pools_nc1_maxpool2.json`、`…/step4/out/replay_nc1_maxpool2_<qid>.json`、
`…/step4/out/pools_nc2_noremap.json`、`…/step4/logs/pools_nc.log`、`…/step4/logs/replay_nc1.log`。

---

## 6. 证明范围披露（照 P0b disclosure 规矩）

### 已证明

1. 在 notebook 当前代码（`v43cP2`，三件套哈希与任务书一致）上，给定 r2 的 3 个底物、
   同一 assets、同一池构建参数，`default_pool_provider` 能**逐 spec 逐字段**重建冻结池
   （3/3，含顺序与 `pool_diagnostics`）。
2. 给定重建池 + 已落盘响应，`start_ppv1_run` 的完整链输出与冻结 payload
   **去时间戳后整体语义相等**，事件/假设/状态/请求身份与顺序全同，v2 判分 status/rank 全同
   （3/3）。
3. remap 路径在这 3 题里确实被使用（1/3/4 个候选带 `template_remap`），且关掉 remap
   会让 remap 重题的池归零——不是“样例没走到 remap”。
4. 负控表明探针能检测池宽变化与 remap 关闭，不是恒真比较器。

### 未证明 / 边界

1. **只抽了 3/298 题**，不是全量结论；其余 295 题未重编译。
2. **只覆盖单次模型调用的 run**（3 题账本均 2 行 = 1 次逻辑调用）。多轮 format-feedback、
   transport 重试、多次 decide（深度/扩展）的题未测；这类题重放需要按账本顺序服务多条
   响应，机制上可行（`ppv1_real_fetch` 支持），但本轮未取样证明。
3. **代码不是 r2 构建时的字节**：10 个文件与 r2 `code_identity` 不同；compile 层差异经
   unified diff 证明只是诊断常量（+18/+16 行，0 删除），但其余 8 个分析/导出层文件是
   新代码。§4 的 PASS 是“新代码 + 冻结输入/响应”的实测兼容性，不是“新旧代码源码等价”。
4. **不能跨 run 复现 `content_digest` / `export_digest`**：payload 内含行级时间戳。
   L2 的相等判据必须用“去时间戳语义哈希”，不能用 export digest 当身份。
5. **重放绕过了 worker/orchestrator 的外层门**（build_identity、evidence-card 冻结副本、
   budget guard）；本探针直接走 `runflow.start_ppv1_run` 公共入口。外层门是批运行纪律，
   不影响 compile/payload 语义，但“整批可这样跑”未证明。
6. **打分用的是冻结 reference_graphs（金标在进程内）**，报告与证据只落 qid 级指标/摘要，
   未落任何金标结构正文；`_offline_export_reader` 按设计跳过 step6/step8（需要 DB 权威）
   的检查。
7. **未验证 remap 改动的化学正确性/指标收益**：本探针只回答“能不能零 LLM 复算”，
   不回答“改了更好”。任何 remap 规则改动仍须走 mimo/Codex 评审与预注册。

---

## 7. 下一步建议：remap / compile 层可测参数面

### 7.1 真实可调参数（grep 自代码，含默认值与文件:行号）

| 层 | 参数 | 默认值 | 位置 |
|---|---|---|---|
| compile | `_COMPILE_ALIGNMENT_LIMIT`（对齐枚举上限，超限结构化拒 `alignment_limit_exceeded`） | `64` | `src/pathway_v43/pollutant/s5b_compiler.py:191` |
| compile | `_CENTER_QUERY_SHELL`（中心查询壳层 L2） | `2` | `s5b_compiler.py:195` |
| compile | `_INFER_ENUM_LIMIT`（recorded 推断映射枚举上限） | `200` | `s5b_compiler.py:198` |
| compile | `_DISSOLUTION_ELEMENTS`（立体消解元素域） | `("C",)` | `s5b_compiler.py:627` |
| compile | `S5B_COMPILER_VERSION` | `"s5b-compiler-6"` | `s5b_compiler.py:159` |
| remap | `S5B_TEMPLATE_REMAP_VERSION`（规则版本；**无数字阈值**） | `"template-remap-1"` | `s5b_compiler.py:186` |
| remap | `complete_template_mapping(mapped_lhs, mapped_rhs)`（确定性规则；开/关由 tnc pre-flight 决定） | — | `s5b_compiler.py:530`；触发点 `compile_donor_template`（1416，pre-flight 约 1459-1478） |
| compile 入参 | `mapped_lhs/mapped_rhs/center_atoms/substrate_smiles/record_id/mapping_origin/alignment_ref/key_prefix/render_name` | — | `s5b_compiler.py:1416-1430` |
| pool | `S5B_POOL_RAW_TOP`（每通道 raw 检索预算） | `24` | `s5b_builder.py:515` |
| pool | `S5B_POOL_MAX`（最终池宽，独特净反应槽） | `8` | `s5b_builder.py:516` |
| pool | `S5B_POOL_THRESHOLD`（首轮相似度阈值） | `0.45` | `s5b_builder.py:517` |
| pool | `S5B_POOL_FALLBACK_THRESHOLD`（不足时降阈值） | `0.40` | `s5b_builder.py:518` |
| pool | `S5B_POOL_MIN_UNIQUE`（触发降阈值的独特候选下限） | `3` | `s5b_builder.py:519` |
| pool | `corpus_channel`（recorded 直通通道消融开关） | `True` | `s5b_builder.py:1085` |
| pool | `default_pool_provider(..., max_pool, raw_top, threshold, fallback_threshold, min_unique_targets, engine, corpus_channel)` | 见上 | `s5b_builder.py:1077-1085` |

**重要澄清**：任务书里说的“remap 阈值 ±ε”在当前实现中**不存在**——remap 是
“签名配对 + 计数配对”的确定性规则，没有相似度/容差阈值。可测的 remap 面是
（a）规则版本/实现改动，(b) 触发条件（`transform_no_change` pre-flight），
(c) 输入模板串本身。若要做“阈值扫描”类实验，扫描面在**池检索层**（`threshold` /
`fallback_threshold` / `raw_top` / `max_pool`），不是在 remap 函数内部。

### 7.2 建议的 L2 实验矩阵（零 LLM 可测性分级）

| 改动类别 | 零 LLM 可测？ | 判据 |
|---|---|---|
| 只改身份/披露/诊断（spec 内容不变） | 是 | 重建池 spec 字节相等 ⇒ 用冻结响应直接重放，指标零漂移即证明无行为变化 |
| 改 remap 规则但**重建池成员与 spec 不变** | 是 | 同上（池 sha 相等 → 全链重放） |
| 改 remap 规则导致池成员/spec 变化 | **部分** | 池级可零 LLM 对拍（成员/顺序/spec/诊断）；但旧模型响应引用旧 hypothesis ID，可能触发格式反馈/新请求 ⇒ **末段指标不能零 LLM 得出**，须重调模型（付费）或把实验限制在“响应仍可解析”的题上 |
| 改池检索参数（threshold/raw_top/max_pool/…） | 部分 | 同上：池变化 ⇒ 旧响应可能失效 |
| 改判分/匹配（evaluation/scoring） | 是 | 冻结 payload 直接重算（上一轮零漂移门已证） |
| 改 build/pool 的**输入**（底物、assets、语料） | 否 | 模型看到的提示变了，必须重调 |

**成本口径**：池重建零 LLM；本轮 3 题一次进程总耗时约 153 秒（engine init ≈32 秒 +
3 题检索/编译）；全链重放单题 ≈2 秒（不含资产/代码身份哈希）。金额 unknown（无付费调用）。

---

## 8. 交付物、偏离与未完成

### 交付物（本地）

证据根（绝对路径）：`/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/l2_stage1_2026-10-26/step4/`

| 路径 | 说明 |
|---|---|
| `/Volumes/CC/Enzyme_Agent/dependingv43/docs/L2_STAGE1_REPLAY_BASE_2026-10-26.md` | 本报告 |
| `…/docs/review_evidence/l2_stage1_2026-10-26/step4/bin/pools_probe.py` | 池重建/对拍探针 |
| `…/step4/bin/replay_probe.py` | 全链重放/对拍/v2 打分探针 |
| `…/step4/out/pools_base.json` | 3 题池重建结果（含逐 spec 摘要与 diff） |
| `…/step4/out/replay_base_<qid>.json` | 3 题全链重放比较（21 区段 + 身份面 + 打分） |
| `…/step4/out/final_verify.json` | 去时间戳语义哈希 + 计数终检 |
| `…/step4/out/pools_nc1_maxpool2.json` / `replay_nc1_maxpool2_<qid>.json` | 负控 1 |
| `…/step4/out/pools_nc2_noremap.json` | 负控 2 |
| `…/step4/code_hashes.txt` / `code_drift.txt` / `code_diff_compile_layer.patch` | 代码核对与 compile 层 diff |
| `…/step4/logs/*.log` | 原始运行日志 |

### 偏离任务书的情况（不隐瞒）

1. **`nb_ssh.sh --put` 不可靠**：HPC 有多个登录节点，`/tmp` 暂存跨节点不可见，首次上传
   出现 `No such file or directory`。改用 **HPC home（共享 `/work/home`）暂存 + 内层 scp**
   完成上传；未改 `nb_ssh.sh`（该文件在本轮开始前已是 modified 状态，非本次改动）。
2. **全链重放没有走 worker/orchestrator**：直接用 `runflow.start_ppv1_run` 公共入口，
   理由是要零 LLM 替换模型且不触碰批根 gate 状态；外层门（build_identity/budget/evidence
   card）未覆盖。已在 §6 披露。
3. **负控 1 触发了一次“原 run 没有的 format-feedback 请求”**：这是池变化后的真实行为，
   零 LLM 无法服务该请求，链接 fail-closed。我们如实把它当作“已检测到变化”的证据，
   没有伪造第二条响应。
4. **未在 HPC 上运行任何东西**（除只读 `cat`/`tar` 取 r2 代码做 diff）；所有计算在 notebook
   `iter/worktrees/` 副本内完成；未写 `/root/v43_migration/ppv1_hpc/`；未动封存批。

### 没做到 / 没证明

- 未对 298 题全量重编译/重放（本轮只 3 题）。
- 未覆盖多轮反馈/重试/多次模型调用的 run。
- 未证明“任意 remap 改动后指标不变或提升”；本探针只证明“可零 LLM 复算到 payload 与
  v2 判分”，不评判化学正确性。
- 未做跨 RDKit 版本对照（只 notebook 2026.03.5）。
- 未实现“注入冻结时间戳以复现字节级 export_digest”；L2 建议直接采用去时间戳语义哈希
  作为跨 run 身份。