# C 线共底物伴生供给实施 · Codex 复审报告 (2026-10-14)

> 复审对象：commit `873c323`（C 线實施：共底物伴生供給 + 声明链发射）；父 `7e7855c`；当前 HEAD `dda852b`，与本任务文件零重叠。
> 审查面：仅 `873c323` 本体（10 文件 / +1423 / −22，以 git stat 为准；交付书 §五 的 +1422 为笔誤）。
> 输入：冻结设计书 `docs/C_COSUB_SUPPLY_DESIGN_PREREG_2026-10-14.md`、任务书 `docs/TASK_C_COSUB_IMPL_2026-10-14.md`、交付书 `docs/C_COSUB_SUPPLY_IMPL_DELIVERY_2026-10-14.md`、探针证据 `reports/ppv1_s5b/c_impl_2026-10-14/`。
> 证据：`reports/ppv1_s5b/c_codex_review_c_impl_2026-10-14/RUN_LOG.md`。
> 题域标签：298=RHEA 通用酶学/已见题，与 dev 双向不外推；探针/验收数字为实施口径，非成绩/預注册投影。零金标/零题面外带。

## 元数据

- 审谁：`873c323` 本体；`git diff 873c323..dda852b --name-only` 仅 P1fix2 四个文件，`src/pathway_v43/pollutant/s5b_builder.py` 与 `production.py` 在该区间 diff 空，因此 HEAD 行号等同 873 本体。
- 判分侧零改动：`git diff 7e7855c..873c323 --name-only` 命中无 `evaluation` / `s5b_scoring` / `recorded_source`。
- 池策略：`S5B_POOL_POLICY_VERSION = "s5b-pool-policy-7"`；常量块 `S5B_POOL_MAX=8`、`S5B_POOL_THRESHOLD=0.45`、fallback/sort/truncation 常量本文件 diff 未动。
- Python：`~/miniconda3/envs/depending43/bin/python`；未调用外部模型。

## 1. 实现与冻结 설계 逐条款一致性

<|message|> 设計条款 | 實现落点 | 判定 |
|---|---|---|
| 语义 a 伴生供給 (build期) | `s5b_builder.py:1073-1163` pre-gate 后 rescue：`analog_cosub_supply` 重新过门；供給并入 `substrate + "." + 供給` | ✅ |
| 主反应物 = 底物最大 Tanimoto | `analog_cosub_supply:593-601` Morgan r2, 2048 bits, chirality=False；并列取后位；不可解析回退重原子数 | ✅ 与归因探针同口径 |
| 供給 = 模板袋精确多重集 | `analog_cosub_supply:607-619` 首份视为主，剩余主份数 + 其他 cn 逐条进入 supply | ✅ PC-S2 二份水袋 |
| 裸通配不供給 | `analog_cosub_supply:620-623` 仅组分身份恰为 `*` 拦截；`[H]*[H]` 等含通配原子的具体小分子正常供給 | ✅ 探针 3 行；PC-S4 |
| 主 cn 不可解析 fail-closed | `analog_cosub_supply:602-606` `main_cn is None ⇒ status=no_supply` | ✅ |
| spectator 披露 | `_cosub_supply_spectators:628-709` 按供給序逐条，未被模板变换消费且身份两侧净零 ⇒ `spectator=True,consumption_status=spectator_pass_through` | ✅ PC-S3 |
| 方向限定声明带侧别 | `analog_record_equation:712-728` 产出 `reactants/products` 两侧，消费侧按侧表解析 | ✅ |
| 候选带完整声明面 | `_attach_analog_cosub_supply_fields:731-862` participants / co_substrate_states / declared_copy_components=[] / contract / record_equation+ref / execution_input_smiles | ✅ |
| 供給救援失败维持现状 | `s5b_builder.py:1155-1163` rescue 不成功时仍 `_record_failure("no_alignment")` | ✅ |
| 池宽/阈值/排序/截断/融合不动 | 常量块 `457-463` 与 commit diff；`_net_reaction_signature` 与去重前后顺序未改 | ✅ |

结论： clauses 对齐，5 条设计红线全部 mechanized 且有 unit / probe 证据。未发现语义 a 瞎全——实施未 silently 将 mechanism 类 bag 洗白 strict；11 题纯 H₂O 袋端到端 positive control 正确。

## 2. 交付书 §三 六项偏差核查

| # | 偏差声明 | 实现证据 | 判定 |
|---|---|---|---|
| 1 | 主反应物 = 最大 Tanimoto，唇 tie 取后位 | 代码 594-601，与 `unlock_face_replay` drift 0 | ✅ 实报 |
| 2 | wildcard 只拦裸通配；含通配原子具体小分子按身份供給 | 代码 620-623；PC-S4 单元查證 | ✅ 实报 |
| 3 | `execution_input_smiles` 新声明字段，prepare 首消费核验组分多重集 | `production.py:194-244,550-561` | ✅ 实报 |
| 4 | NC-10 `record_products` = 执行净产物全量，不复制 donor rhs；与 `record_equation` 分開 | `_attach...` 815-816 vs 857-858 | ✅ 实报 |
| 5 | spectator 按供給序逐条对齐；RDKit 显式 map 并入重原子 | `_cosub_supply_spectators` 628-709；PC-S2 | ✅ 实报 |
| 6 | 无范围外改动 | git name-only stat；见 §3 | ✅ 实报 |

## 3. 判分侧零改动声明核查

- 命令：`git diff 7e7855c..873c323 --name-only | grep -E 'evaluation|s5b_scoring|recorded_source'` → 空。
- commit name list 共 10 文件，无 `evaluation.py/s5b_scoring.py/recorded_source.py`。
- 基线探针字节不变：262 run_inputs 全等 + 35 純新增供給 spec + 1 W4 合法互動；诊断 drift 0。
- 结论：判分侧 untouched，v1 缺省判分零漂移由探针實证（字節不变 + PC-S7 v1 对照 partial）。

## 4. 池宽 8 / 阈值 0.45 / 排序 / 截断 / 融合序零变化

- 常量块（`s5b_builder.py` 457-462）：`S5B_POOL_MAX=8`、`S5B_POOL_THRESHOLD=0.45`、`S5B_POOL_FALLBACK_THRESHOLD=0.40`、`S5B_POOL_MIN_UNIQUE=3`、`S5B_POOL_RAW_TOP=24`。
- policy-7 只在 pre-gate 拒後进行 rescue，stage 2-7（ fusion / dedup / fallback / truncation ) unchanged；`s5b_compiler.py` diff empty。
- 度量：`n_pool_returned = min(n_unique, 8)`，不改截断位；W4 probe 262 全等 + 1 合法互動说明不会 accidental 宽度 expansion。

## 5. 误供給面核查

- bare wildcard：locked，`wildcard_blocked=3`（unlock probe）+ PC-S4；
- main cn fail-closed：不可解析主供給 ⇒ `no_supply`，不供給（test main unparseable snippet passed）；
- proveanance 发射：`_record_equation_provenance` 五类 fail-closed shapes（不成对 / shape bad / entry unparseable）； NC-10 参与物删减が reject；
- idempotency：`store.put_provenance` 对 same payload 幂等、异 payload `Ppv1EventConflict` 拒绝；
- fail-closed 放射点：prepare 通过後，put_provenance 于 event submit 之前；put 失败直接 raise，不 submit；
- runtime verifier `production.py:194-244` 对执行输入进行多重集 canonical strict identity 比对，防止冒充执行输入。

## 6. 验收证据复跑

| 证据 | 结果 |
|---|---|
| 新测族 + lineage + cosub d2 + controlled vocab | 84 passed (6.19s) |
| `test_ppv1_s5b_cosub_supply.py` | 10 passed |
| unlock probe | 45 rows / 35 qids，446 matched，0 drifted，bare_wildcard_blocked 3，assembly_errors 0 |
| v2 positive control | exact 5，exempted 5，tiers `v1_exempt ×5`，3 谓词全 pass，declaration resolved ×5 |
| byte invariance | 262 full equal + 35 pure supply + 1 fallback interaction，drift 0 |
| 全量 | 未 rerun 2135/6m；算术与 targeted + probes 一致，报告不 claim 本会话实跑 2135 |

## P1 / P2 / P3 findings

- **P1：0**。未发现 contract mismatch / provenance 悬空气 / scoring 污染 / value math error / runtime fail-open。
- **P2：1** — 交付书 §5 行数笔誤：`+1422`，git stat 为 `+1423`；应以 git 为准（ harmless 文档事实，无代码影响）。
- **P3：6**（ Need no code fix で放行可；逐条 below ）：

| # | 出处 | 说明 | 目前表征 |
|---|---|---|---|
| P3-1 | `s5b_builder.py:602-606` | 主不可解析 status 仅标 `no_supply`，锚面 0 实例；实现侧更严格 fail-closed，无面差 | informational |
| P3-2 | `s5b_builder.py:810-814` | contract `co_substrates` 对重复身份 dedup；exact multiplicity 的真相仍由 states/participants/execution_input 保留 | audit metadata precision |
| P3-3 | `production.py:804-829`, `636-641` | NC-10 反應物侧集合语义；同身份份数删除在 set 比对中不被 reject，仅手造 spec 可达 | 実装语义一致，但 disclosure 有 precision limit |
| P3-4 | `production.py:549-561`, `206-207`, `1150-1152` | 放射声明在位而 execution_input 缺失时 fallback 裸底物；仅无 contract/壳造 spec 可達，正常 analog 链恒携带 | corpus semantics consistent |
| P3-5 | tests `PC-S5` | 版本承载为字符串断言；语义由另 5 文件同步 + 字节探针共同承载 | test-depth only |
| P3-6 | W4 / evidence | W4 补位 1 题consistent（供給 lift unique reaction count ⇒ no fallback）；full 2135 not rerun | evidence depth |

## 分域结论

- builder：有条件通过（供給语义、wildcard、multiset、spectator、declaration、rescue枝、constants OK；仅 P3 metadata precision）
- production：通过（AC fail-closed、execution input verify、declaration refs、put/idempotent、NC-10 unchanged surface）
- tests/evidence：通过（10/10 + 84 targeted，probes exact）

## 终判定

**有条件通过 (conditional pass)。**

放行条件仅 P2-1 documentation number + P3 transparency (accept-as-is if task owner understands exact multiplicity lives in refs/participants/execution_input). 无 P1，无需改码； recommending next phase C outcomes assessment proceed under pre-reg discipline. 不 push；report untracked per AGENTS redline.
PY