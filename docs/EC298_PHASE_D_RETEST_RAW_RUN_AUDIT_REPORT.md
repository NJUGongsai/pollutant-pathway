# EC298 Phase D 复测原始 run 复核报告（独立重算）

> 总判定：**`contradictory`**（窄范围：原始事实全部成立；矛盾仅限派生表元数据与报告措辞，主分数/配对/费用/峰值/完成性不受影响）。
> 任务书：`docs/TASK_V43_EC298_PHASE_D_RETEST_RAW_RUN_AUDIT.md`。被核报告：`docs/EC298_PHASE_D_RETEST_REPORT.md`（v2）。
> 性质：零 LLM、只读取证与独立重算；未重跑 agent/模型/引擎/烟测；未调用付费 API；未改原始 run、旧报告、旧派生表、封存清单、批次身份、远端金标。新输出仅在 `reports/phase_d/retest/raw_run_audit/`（独立目录）与本文件。
> 金标仅在远端隔离离线评分中打开；本仓表格只保留脱敏字段与远端相对证据路径，不含原始响应全文、金标答案、prompt 全文、凭证。
> 修订 v2（2026-09-29 review 补件）：v1 审计脚本来源段误读顶层 `products`（见 `raw_run_audit/audit_raw_run_v1_SUPERSEDED.py` 注记），来源数字改由修正脚本 `raw_run_audit/audit_raw_run_v2.py` 重算并交付逐位表 `v2_source_positions_{C0,D3}.tsv`；代码/资产聚合改由冻结函数从实际文件重算（`v2_code_aggregate.json` / `v2_asset_manifest.json`）；复现命令全部改到独立输出目录；隔离补全口径扫描判别记录（`v2_isolation_full_{C0,D3}.json`）；调用算式统一为 185×1+1×2=187。

## 0. 审计环境与输入

- 本地 HEAD `ea6de25…`（`git rev-parse HEAD`），审计开始 `2026-09-29T03:19:17Z`；工作树有 7 项预先存在的未提交文件（见 `raw_run_audit/audit_meta.json`），审计未触碰。
- 远端根 `/usrdata/EnzymeCAGE_data/workspaces/dependingv43`；两臂 `runs/ec298_pd_retest_C0/`、`runs/ec298_pd_retest_D3/`，引擎 `runs/ec298_pd_retest_engine/`，烟测 `runs/ec298_pd_retest_smoke/` 均可读。
- 远端 python `3.11.16` / rdkit `2026.03.6`；本地 python `3.14.7`（无 rdkit，判分一律远端重算）。
- 远端审计输出目录 `/tmp/raw_audit/`（v1）与 `/tmp/raw_audit_v2/`（v2，来源修正/聚合重算/全口径隔离；独立目录，不在被检查根与 `scoring/` 内）；本仓收录脱敏摘要于 `reports/phase_d/retest/raw_run_audit/`。
- **证据缺口（1 项）**：远端工作区不是 git 仓库（`GIT_DISCOVERY` 边界，无 `.git`），远端 `HEAD`/工作树状态无法记录；改用冻结函数从实际文件重算代码聚合（50 文件一致，见 §1），此缺口不影响其余结论。

## 1. 冻结锚（§2 待验证值逐项重算 SHA）

全部匹配（`raw_run_audit/remote_sha_checks.json`）：

| 项 | 重算 | 待验证 | 结论 |
|---|---|---|---|
| C0 / D-3 批次身份（`_arm_summary.batch_sha256`） | `31549aab…` / `cfe1534a…` | 同左 | pass |
| 白名单（两臂 `exam_inputs.jsonl`） | `cb5996c9…` | 同左 | pass |
| 金标（只读） | `9f5955d4…` | 同左 | pass |
| 代码聚合（冻结函数从实际 50 个 py 文件重算） | `07fef84f…` | 同左 | pass（`v2_code_aggregate.json:match=true`） |
| 资产清单（冻结函数从实际 22 文件/166849006 字节重算） | `ac9b97b8…` | 同左 | pass（`v2_asset_manifest.json:match=true`） |
| 引擎结果 | `0e16268c…` | 同左 | pass |
| C0 / D-3 merged 答卷 | `48c84bd6…` / `61386590…` | 同左 | pass |
| C0 / D-3 seal 清单 | `e83ad533…` / `ac1e0d2c…` | 同左 | pass |

报告待验证数字的复核结论见各门；主数字（298/286+12/285+13/187/hit 四格/峰值/费用）原始侧全部复现，下述窄矛盾（F1/F2）与勘误（K1/K2）均不触及这些数字。

## 2. 逐门判定

### A1 只读保护与通道 — `pass`（附 1 缺口）

- 通道按 `docs/CHENYU_ACCESS.md` 使用 `/tmp/cy_ssh.sh`（expect 封装）；长任务按 nohup+短连接轮询（本次审计脚本 `/tmp/audit_raw_run_v2.py` 即以后台方式执行，输出 `/tmp/raw_audit_v2/`）。
- 未向命令输出/报告写入密码、token、`.env` 值、金标内容、prompt 全文、原始响应全文。
- 缺口：远端非 git 仓，`HEAD`/工作树状态不可记（见 §0）。

### A2 审计前后文件清单 — `pass`

- 审计前清单：C0 `46446` 文件、D3 `47103` 文件（覆盖 `exam_inputs.jsonl`、`input_manifest.json`、`batch_identity.json`、`workers/`、`runs/`、`merged/`、`_arm_summary.json`、`_seal/` 的逐文件 path/size/SHA256；根摘要 C0 `928b66f7…`、D3 `8f3644dc…`）。
- 审计后同规则重算：两臂 `changed/added/removed` 均为 `[]`（`remote_manifest_post_diff.json`）。新输出落在 `/tmp/raw_audit/`、`/tmp/raw_audit_v2/` 与本仓 `raw_run_audit/`，未写入被检查根。

### A3 配置与批次身份 — `pass`

- 配置扁平键 38/38，对比 38 键，唯一值差 `prediction_policy_overrides.reactant_similar_enabled`（C0 `false` / D-3 `true`）。
- 身份扁平键 58/58，对比 58 键，唯一值差同一键（路径为 `config.prediction_policy_overrides.reactant_similar_enabled`）。
- 代码/资产/prompt/scorer/模型/预算/题卷/价格快照身份与报告 §1–§2 一致；`input_manifest.json` 两臂逐字节同源（白名单 SHA 同为 `cb5996c9…`）。

### A4 白名单与隔离 — `pass`

- 两臂各 298 行、298 唯一 qid，与 `input_manifest.route_order` 逐一同序；字段恰为 `qid/substrate_smiles/input_index`（坏行 0；答案字段 0；空底物 0；`gold_fields_excluded=true`）。
- 评分在封存与隔离检查后单独打开金标；本仓无金标答案。

### B1 298 题原始终态与答卷联结 — `pass`

- 以 `input_manifest.route_order` 显式联结（`run_id = exam298_<short>_<qid>`），未从目录名截取 qid。
- C0/D-3 各 298 run 目录，0 缺失、0 多余、0 联结失配（`remote_per_question_*.json` 全表 298 行，含每题状态/停因/导出/身份引用/答卷 SHA/候选数）。
- 终态与导出：C0 `success_completed` 286 + `legal_stop` 12；D-3 285 + 13；`failed/export_failed/missing` 均为 0。

### B2 归并与配对门禁 — `pass`

- `merged/export_metadata.json`：两臂 `n_lines=298`、`n_unique=298`、`batch_terminal_status=completed`；answer_kind full/empty = 286/12、285/13；宽度直方图 C0 `0:12/1:125/2:31/3:22/4:31/5:77`、D-3 `0:13/1:129/2:32/3:23/4:27/5:74`，超 5 者 0。
- `awaiting_prediction` 12/13 题对应 `legal_stop`（模型显式弃答/编辑拒绝的合法停留），与 §3 空答构成一致。
- 远端 `reports/phase_d/retest/scoring/pairing_gate.json`：`verdict=complete`、`release_eligible=true`，两臂 `ok=true`、`n_violations=0`；本审计的独立终态重读与之一致。

### B3 引擎 — `pass`

- `engine_results.jsonl` 298 行、298 唯一 qid、SHA `0e16268c…` 匹配；两臂 `score_v2` 记录的引擎 SHA 同为此值（同一引擎产物）。

### C1 请求重建、usage、112 直通 — `fail`（窄：措辞与事实不符；总量成立）

- 原始侧（`remote_requests_*.json/tsv`，算式经 `v2_call_arith_*.json` 显式复核）：两臂各 187 请求、187 唯一 request_id、187 ok、0 失败/0 429（`http_attempts` 内）/0 孤儿（`prediction_call` 187、`prediction_orphan` 0）；`usage` 缺 0；分布 **185 题×1 + 1 题×2 = 187**，另 112 题零调用（185+1+112=298）；零调用 112 题**两臂完全相同**。
- Usage 求和与 `{C0,D3}_api_calls.tsv` 一致：C0 输入 345123/输出 1656491；D-3 输入 356637/输出 1764086（缓存 40640 两臂同值，见 C4）。
- **最小反例（措辞矛盾）**：报告 §3 表注 `187(分布与 C0 逐题相同)`。原始事实为总量分布相同、发生二次尝试的题不同：
  - C0 二次尝试：`RXNG_16560019…`（`T_900d196341de803b1c31`，a1/a2 两个 request_id，见 `remote_attempt_bug.json`）；
  - D-3 二次尝试：`RXNG_7701b699…`（`T_dc74022fb8a0c8e002b6`，a1/a2 两个 request_id）；
  - 交叉核对：C0 的 `RXNG_7701…` 仅 1 次（`T_b3ac3e7…`），D-3 的 `RXNG_1656…` 仅 1 次（`T_85101fc7…`）。
- 影响面：仅报告措辞；主费用/峰值/分数不受影响（总量 187/187 不变）。补丁见 §4.P2。

### C2 两次尝试题与在途表 attempt 列 — `fail`（派生表元数据错误；原始事实成立）

- 原始响应明确呈现 attempt 1、2（两臂各 1 题，文件 `prediction_response.a1/a2.json` 的 `payload.attempt` 分别为 1、2，request_id 不同，见 `remote_attempt_bug.json`）；`{C0,D3}_api_calls.tsv` 正确记录 1、2（C0 `T_900d…` 两行 attempt 1/2；D-3 `T_dc74…` 两行 attempt 1/2）。
- **最小反例（派生表错误）**：`reports/phase_d/retest/C0_inflight_events.tsv` 中 `RXNG_16560019…` 两行 attempt 均为 `2`（request `f58844e8…`=a1 应为 1，`c9e2576d…`=a2 为 2）；`D3_inflight_events.tsv` 中 `RXNG_7701b699…` 两行 attempt 均为 `2`（request `143af641…`=a1 应为 1，`7589f5d7…`=a2 为 2）。
- 根因：`scripts/ec298_pd_retest_inflight.py:54-67` 以 `(run_id, task_id)` 为键的字典被后一文件覆盖（`attempt_by_key[(run_id, task_dir.name)] = payload.get("attempt")` 循环覆盖），同一 task 的两行都被标成最后一次 attempt。判定：**原始响应正确、API 调用表正确、在途表错误**；峰值不受影响（峰值不消费 attempt 列），但不得以峰值一致宣称逐请求表全对。补丁见 §4.P1。

### C3 并发峰值 — `pass`（附 2 项强制勘误，数字无影响）

- 独立区间扫描：0 负时长、0 零时长、0 缺区间；`elapsed_s` 与区间时长差 >5s 者 0。
- 两种口径峰值一致：C0 sent-first 33 / done-first 33（记录 33）；D-3 32/32（记录 32）。`peaks_match` 成立。
- **勘误 K1（措辞）**：报告“单调时间戳”不成立。原始字段为 epoch 墙钟（`llm_client.py:311,316 sent/done=time.time()`），`elapsed_s` 才用单调时钟（`time.monotonic()-t0`）；且 `llm_client.py:82` 注释把 `time.time()` 称为“单调时钟时间戳”，自相矛盾。应改为“epoch 墙钟时间戳；`elapsed_s` 为单调时钟差”。
- **勘误 K2（口径）**：`exam.inflight_evidence:441 events.sort(key=(t,-delta))` 为同分秒先发后完（闭区间口径），与任务书要求的半开区间 `[sent,done)` 同分秒先完后发相反。本次两口径峰值恰好一致，故数字无影响；建议按 §4.P4 对齐口径或明确声明闭区间口径。

### C4 费用 — `pass`

- 独立求和 + 快照价（input 0.8/M、output 2.8/M、cache-read 0.23/M，思考计输出）重算：C0 `¥4.8911`、D-3 `¥5.2016`、烟测 `¥0.0761`，与臂汇总及报告 §7 逐位一致（`fee_recompute.json`）；376/376 调用 usage 齐全，无 unknown 残差；烟测 2 次独立计账；账单回填仍待独立费用门（报告已如实标注）。

### D1 产物来源逐位比对 — `pass`

- 方法（可复现代码 `raw_run_audit/audit_raw_run_v2.py` §3，与 `scripts/ec298_pd_retest_pairing.py:_first_reportable_source` 同口径）：重读 `results/T_*/report_adjudication.json` 的 **`payload.products[reportable=true]`** 按 `report_rank` 排序，取 `product_smiles_full` 回退 `product_smiles`，与 merged `predicted_products` 逐位比对完整字符串。注：v1 脚本误读顶层 `products`（恒空，日志 0 匹配），已废弃为 `audit_raw_run_v1_SUPERSEDED.py`，D1 结论一律以 v2 为准。
- 逐位证据表：`raw_run_audit/v2_source_positions_{C0,D3}.tsv`（762/740 行：qid/pos/match/evidence_id/card_kind/report_rank，无 SMILES 内容）+ 汇总 `v2_source_positions_{C0,D3}.json`。
- 首位：C0 286/286、D-3 285/285（恰为非空数），不匹配 0；全部报告位：C0 762/762、D-3 740/740；宽度越界 0。
- 首位 card_kind：C0 `recorded_reaction` 182 / `novel_proposal` 91 / `analog_reaction` 13；D-3 182/86/17（即报告的 recorded/novel/analogy；`source_kind_correction.json` 记录标签映射）。

### D2 独立评分与配对 — `pass`

- 主复核独立读取原始 merged 答卷、显式 qid 联结、`cn_identity` 现算首命中 rank（生产 `score_exam_v2` 仅作第二对照，未直接复用其输出）。
- 298×2 逐题 rank 与 `score_v2_C0/D3.json` 差异 0；hits C0 `136/182/186`、D-3 `132/174/182` 一致；配对四格 @1 `127/9/5/157`、@3 `172/10/2/114`、@5 `178/8/4/108` 一致（`remote_scoring_independent.json`）。

### D3 封存与隔离 — `pass`（结论限定在本条列明的两个口径内）

- 口径一（官方 601 文件）：`_seal/` 独立验证，两臂 `n_sealed_files=309`，`seal.sha256` 文本逐字节一致，`seal_sha256_of_manifest` 一致（`seal_verify.json`）；官方口径（结构化 5 + worker status 298 + plan 298 = 601 文件）重扫两臂 0 违规，白名单坏行 0、答卷坏行 0。
- 口径二（全量补充扫描，判别记录 `raw_run_audit/v2_isolation_full_{C0,D3}.json`，由 `audit_raw_run_v2.py` §4 生成：官方严格正则、全文本无截断、被旗标文件全结构遍历、逐文件键路径上下文、无值内容）：C0 46751 文件（357 超 500k，均全量扫描）中 291 旗标、D3 47408 文件（361 超 500k，均全量扫描）中 290 旗标；其中 290/289 为 `products_smiles` **JSON 键名**（schema 字段，分布：`report/pathway.json` 186、`results/*/prediction.json` 104/103），`value` 含该标记者 0；金标路径标记（`ec298_gold_readonly`/`questions.jsonl`/`raw_reaction`）仅命中 `_seal/seal.json` 自身词表 1 文件，**运行侧 0 文件引用金标路径**；严格凭证正则 0 命中。
- 限定：官方 601 口径明确排除决策/预测载荷（语料 SMILES 合法存在）；口径二证明运行侧无金标路径引用、无值级 `products_smiles` 命中、无凭证字符串，但载荷 SMILES 与金标的语料重叠问题沿用报告 §10.5（未经单独审计），本条不据此断言“全部载荷语义零泄漏”。
- v1 期间 45k 文件 naive 扫描的 477 旗标系过宽模式误报（`prediction-task` 词内 `sk-` 子串等），在严格正则下为 0，已备案，不构成反证。

## 3. 差异清单（最小反例）

| # | 位置 | 原始证据 | 报告/派生主张 | 判定 |
|---|---|---|---|---|
| F1 | `reports/phase_d/retest/{C0,D3}_inflight_events.tsv`（C0 `RXNG_16560019…` 两行；D3 `RXNG_7701b699…` 两行） | `runs/ec298_pd_retest_{C0,D3}/runs/<run>/results/<task>/prediction_response.a1/a2.json`（attempt 1/2，request_id 见 §2.C2） | 两行 attempt 均为 2 | 派生表错，原始成立 |
| F2 | 报告 §3 `187(分布与 C0 逐题相同)` | `v2_call_arith_*.json` + `remote_requests_*.json:two_attempt_qids`（C0 `RXNG_1656…` / D3 `RXNG_7701…`）；112 零调用题两臂相同 | “逐题相同”与“186×1+1×2”算式（和为 188）均与事实不符 |
| K1 | 报告 §9 “单调时间戳”；`src/pathway_v43/adapters/llm_client.py:82` | 同文件 `:296,311,316`（sent/done=`time.time()`，elapsed=`monotonic`） | “单调” | 术语勘误 |
| K2 | `src/pathway_v43/exam.py:441` 排序口径 | `key=(t,-delta)`（同分秒先发）vs 任务书半开区间先完 | 口径描述 | 口径勘误（峰值无影响） |

影响面：F1/F2/K1/K2 均不触及主分数、来源、完成性、费用、峰值数字；`reactant_similar_enabled` 默认保持 `false` 的结论不受影响。

## 4. 补丁建议（不擅自改旧报告/历史输出）

- **P1（F1 修复）**：`scripts/ec298_pd_retest_inflight.py:54-83` 删除 `(run_id, task_id)` 覆盖字典，改为逐响应文件独立取数：遍历 `prediction_response.*.json` 时对每个文件读取其自身 `payload.attempt`（或由文件名 `*.aN.json` 解析 attempt）并随该行直接落盘；重生成两张 `*_inflight_events.tsv` 后复核 F1 两题为 1/2。
- **P2（F2 措辞与算式）**：报告 §3 改为“两臂总量同为 185×1+1×2=187（另 112 题零调用，185+1+112=298）；二次尝试的题不同（C0 `RXNG_16560019…`/D-3 `RXNG_7701b699…`）；112 道零调用题两臂完全相同”。注：原“186×1+1×2”之和为 188，属算式错误。
- **P3（K1 术语）**：报告 §9 与 `llm_client.py:82` 注释改为“epoch 墙钟时间戳（`time.time()`）；`elapsed_s` 为单调时钟差”。
- **P4（K2 口径）**：二选一并声明：(a) 代码改为 `events.sort(key=lambda x:(x[0],x[1]))`（同分秒先完后发，与半开区间一致）；或 (b) 任务书/报告明确声明闭区间口径（同分秒先发）。本次两口径峰值相同，无需改数字。

## 5. 复现命令（只读；输出一律独立目录，不进 arm/`scoring/`/`retest/`）

```bash
# 远端审计 v2（后台落盘 + 短连接检查；输出 /tmp/raw_audit_v2，不进被检查根）
/tmp/cy_ssh.sh "mkdir -p /tmp/raw_audit_v2 && cd /usrdata/EnzymeCAGE_data/workspaces/dependingv43 && nohup env OMP_NUM_THREADS=1 .venv/bin/python /tmp/audit_raw_run_v2.py > /tmp/raw_audit_v2/audit_v2.log 2>&1 &"
# 可复现代码已交付本仓：reports/phase_d/retest/raw_run_audit/audit_raw_run_v2.py
# （v1 audit_raw_run_v1_SUPERSEDED.py 仅留作 bug 链备案，其来源段作废）

# 门禁 + 评分 + 配对（远端，零 LLM；--out-dir 必须独立目录，禁止指向现有 scoring/）
cd /usrdata/EnzymeCAGE_data/workspaces/dependingv43 && OMP_NUM_THREADS=1 PYTHONPATH=src .venv/bin/python scripts/ec298_pd_retest_pairing.py --c0-root runs/ec298_pd_retest_C0 --d3-root runs/ec298_pd_retest_D3 --engine-results runs/ec298_pd_retest_engine/engine_results.jsonl --gold /usrdata/EnzymeCAGE_data/workspaces/ec298_gold_readonly/questions.jsonl --out-dir /tmp/repro_scoring
# 逐题分层差异（远端，零 LLM；同上）
OMP_NUM_THREADS=1 PYTHONPATH=src .venv/bin/python scripts/ec298_pd_retest_deepdiff.py --c0-root runs/ec298_pd_retest_C0 --d3-root runs/ec298_pd_retest_D3 --out-dir /tmp/repro_deepdiff
# 并发逐请求派生（远端，零 LLM；--out-dir 独立目录）
OMP_NUM_THREADS=1 PYTHONPATH=src .venv/bin/python scripts/ec298_pd_retest_inflight.py --arm-root runs/ec298_pd_retest_C0 --label C0 --out-dir /tmp/repro_inflight  # 同 D3
```

注：`scripts/ec298_pd_retest_seal.py` 按设计会写 `<arm-root>/_seal/` 派生文件，故**不作为只读复现命令交付**；封存核验由交付脚本 `audit_raw_run_v2.py` §6 只读重算（309 文件 manifest 文本、`seal.sha256`、`seal_sha256_of_manifest` 与 601 文件泄漏重扫，输出 `v2_seal_recompute_{C0,D3}.json`，均在独立目录）。本次审计前后清单零变化的结论不受此影响。

## 6. 审计限制

- 结论仅限“已见 298 题、冻结配置下观察到的差异”；单次真实模型抽样，A/B 层与 C 层噪声不可定量分离（沿用报告 §5、§10 限定）。
- 远端非 git 仓，远端 `HEAD`/工作树状态记为证据缺口；代码身份以冻结函数实际文件重算替代验证（50 文件聚合一致）。
- 12MB 逐文件 manifest 全文留远端 `/tmp/raw_audit/manifest_pre_{C0,D3}_files.jsonl`（路径/大小/SHA，无敏感内容）；本仓收录根摘要与 diff。v1 审计脚本来源段作废并留档（`audit_raw_run_v1_SUPERSEDED.py`），D1/代码/资产/隔离/封存结论一律以 v2 脚本（§1–§6）与 `v2_*` 证据为准。
- 本审计未核题卷与检索语料的潜在重叠（沿用报告 §10.5），未回填服务商账单（费用门仍独立）。
