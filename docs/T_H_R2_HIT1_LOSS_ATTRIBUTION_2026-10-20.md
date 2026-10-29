# T-H r2 hit@1 丢分归因（209 题）

> **题域：298＝RHEA 通用酶学/已见题，post-hoc。** 本文所有题数、比例、桶读数均限定在该题域；
> 不向 dev、新题泛化或其他题域外推。批 `t_h_s5b_298_20261020r2`（build 46954982 / run 46958084 /
> score 46969374）已封存只读；本文只读本地镜像与 HPC run 元数据，**未重跑、未重判、未调模型、
> 未读金标/reference_graphs/questions**。`v1`/`v2` 指同批 criteria 豁免开关；headline 为 v2。

## 0. 结论先行

- **v2 未命中 209 题**（298−89）。按“供给面优先”的互斥分类：
  **unmatched 其它 94（45.0%/31.5%）、partial 41（19.6%/13.8%）、空池 40（19.1%/13.4%）、
  strict rank 2–5 31（14.8%/10.4%）、零调用 2（1.0%/0.7%）、strict rank>5 1（0.5%/0.3%）**。
- **最大单块是“非空池、非零调用的 unmatched”94 题**。其中 47 题连旧口径投影候选都没有
  （41 题在 remap 面），另 47 题有旧口径候选但没过 strict/partial。
- **空池不是本批的主要丢分来源。** 60 个空池题里 20 题 hit@1（33.3%），高于非空池
  69/238（29.0%）；但**新增 7 个空池题 0 命中**，其中仅 1 题是 chain13 原 hit。旧 53 个空池
  题贡献 20 个命中。把“60 空池”整体读成 60 个损失是错的；本批未命中的空池只有 40 题。
- **16 个退化题**：按池优先级＝空池 4、rank 2–5 8、strict→partial 3、strict→unmatched 1；
  按分数形态＝rank 掉出 10、strict→partial 5、strict→unmatched 1、零调用 0。
  其中 1 题落入新增 7 空池（同时是 21 题身份门影响面），6 题在 remap 面，4 题在 P2 add 面。
- **18 个改善题**：unmatched→strict 6、partial→strict 4、原 strict 但 rank>1→rank1 8；
  10 题 remap、10 题 add、0 题身份门/新增空池。
- **v1 命中在 209 个 v2 未命中里为 0**：v1→v2 只新增 5 个命中，84 个 v1 命中全部保留，
  v2 命中集合是 v1 的超集。因此“v1 是否命中”这一刀切对本批丢分没有解释力。

## 1. 数据与字段（先摸清再分类）

### 1.1 本地 metrics 的 per_qid 字段

`reports/ppv1_s5b/t_h_2026-10-20/r2/metrics.json` 的 `per_qid[]` 实际字段：

| 块 | 字段 | 用途 |
|---|---|---|
| `main` | `match_status`、`rank`、`scoring_status`、`scoring_error_kinds`；strict 题另有 `matched_event_not_in_candidates`、`n_candidate_events`、`n_matched_events` | v2 主口径状态/位次 |
| `old` | `anyof_rank`、`gold_ids_empty`、`n_candidates`、`rank`、`width_capped_products` | 老口径敏感性（不同尺，不混比） |
| 顶层 | `qid`、`run_id`、`run_status`、`stop_reason` | 运行态 |

- `match_status` 只有三值：`matched_strict` 126、`matched_participant_coverage_partial` 53、
  `unmatched_required_node_uncovered` 119。
- strict 的 `rank` 分布：1=89、2=20、3=9、4=5、5=2、6=1。
- 全部 298 题 `run_status=completed`、`stop_reason=budget_limit`；`scoring_error_kinds` 全空。
- `old.n_candidates=0` 仅 2 题（即两题 NC-9 零调用）；其余题都有候选投影。

### 1.2 补充元数据（只读，不含化学内容）

| 来源 | 取用的元数据 | 不读/不输出 |
|---|---|---|
| `batch_report.json` | `model_calls`（0=2、1=294、2=2）、状态、stop_reason | 无 |
| `p2_face_measure.json` | 逐题 `remap`/`add`/`add_multi` 计数（151 题 remap、134 题 add） | 无 |
| HPC `batch_manifest.json`（新/旧批） | `pool_size`、`n_pool_returned`、`n_analog_compiled`、候选 `outcome`/`reason` 计数、`compile_failure_histogram` | 不输出 substrate/candidate SMILES |
| HPC 逐 run `native_result.json` | `events` 数、`report_projections` 数、`model_requests` 状态、`search_actions` 状态、`blocked/deferred`、audit 状态计数、`run_error.kind` | 不读 reference_graphs/金标/候选结构正文 |
| 旧批 `degenerate_fragment_face_v2.json` | `cop_qids` 21 个 qid | 不读 `cop_detail` 化学细节 |

运行面核对：298 题 `endpoint` 执行状态 = completed 296 / failed 2（两题 NC-9）；
`primary stop_reason` 全部 `budget_limit`；`blocked_entries=0`；`deferred_entries` 每题 0–19
（中位 8，合计 2366；0 的 2 题即 NC-9）。
提交事件总数 1586，`submitted.created=True` 1586；即除两题 NC-9 外，**没有“模型没答/零事件”的题**。

native_result 里可见的两类“拒绝/失败”元数据（都不等于金标误拒）：

| 形态 | 题数 | 其中 hit | 其中未命中 | reason（元数据原文） | 读法 |
|---|---:|---:|---:|---|---|
| production `method_failed` | 12 | 3 | 9 | `edit_execution_failed:sanitize_failed:AtomValenceException:edit[last]` | 单条候选执行失败；题内仍有其它提交事件，3 题仍 hit |
| audit check `violated` | 45 | 12 | 33 | `center_mismatch_per_deterministic_checker:ppv1-donor-diagnostic-10` | 45 题共 67 条 violated 检查记录（45 条带该 reason）；admission 仍 `retain_conditional`，不是硬拒绝 |

- 45 题（67 条 violated 检查记录）里 12 题仍 hit，说明它**不能当作丢分标记**；只能说明该题
  有一条中心匹配检查与声明不一致，是否影响 strict 需候选级证据。
- 12 个 `method_failed` 里 9 个未命中（空池 6、unmatched 1、rank2–5 1、partial 1），
  但同题往往还有 3–6 个其它提交事件；它更像“单条路径执行失败”，不是整题零答案。

## 2. 209 个未命中的互斥分类

分类采用“供给面优先”的互斥顺序：先分零调用、空池，再按 strict 位次、partial、其它 unmatched。
这样“空池”不会与 partial/unmatched 重复计数。

| # | 类别 | 题数 | 占 209 | 占 298 | 定义/备注 |
|---|---|---:|---:|---:|---|
| 1 | 零调用结构终止（NC-9） | 2 | 0.96% | 0.67% | `model_calls=0`、0 事件、`cosubstrate_copy_in_expectation`；既有形态 |
| 2 | 空池（本地编译池=0） | 40 | 19.14% | 13.42% | 60 个空池题中未命中的 40；另 20 题 hit@1 |
| 3 | strict 但 rank 2–5 | 31 | 14.83% | 10.40% | 非空池；strict 命中已存在，仅位次非首 |
| 4 | strict 但 rank>5 | 1 | 0.48% | 0.34% | rank=6 |
| 5 | partial 部分覆盖 | 41 | 19.62% | 13.76% | 非空池；`matched_participant_coverage_partial` |
| 6 | unmatched 其它 | 94 | 44.98% | 31.54% | 非空池、非零调用、非 partial/strict |
| | **合计** | **209** | **100.00%**（分项四舍五入合计 100.01%） | **70.13%** | |

### 2.1 与原始判分状态的对账（非互斥视图）

| 原始状态 | 未命中题数 | 其中空池 | 其中非空池 | 其中零调用 |
|---|---:|---:|---:|---:|
| `matched_strict`（rank≠1） | 37 | 5 | 32 | 0 |
| `matched_participant_coverage_partial` | 53 | 12 | 41 | 0 |
| `unmatched_required_node_uncovered` | 119 | 23 | 96 | 2 |
| **合计** | **209** | **40** | **169** | **2** |

- 原始 strict 未命中 37 = rank 2–5 的 36 + rank>5 的 1。分类表里的 rank 2–5 只列了 31，
  另外 5 题因空池优先归入“空池”；做“位次杠杆”时应使用 **36+1=37** 这个总数。
- 原始 partial 53 = 分类表的 41（非空池）+ 12（空池）。
- 原始 unmatched 119 = 分类表的 94（非空池其它）+ 23（空池 unmatched）+ 2（零调用）。

## 3. 交叉切面

### 3.1 模型调用 × 空池/非空池

| 切面 | 未命中题数 | 说明 |
|---|---:|---|
| `model_calls=0` | 2 | 两题 NC-9；事件 0 |
| `model_calls=1` | 205 | 主体 |
| `model_calls=2` | 2 | 1 题空池 + 1 题 partial；均未命中 |
| 空池 | 40 | 60 空池中 20 命中、40 未命中 |
| 非空池 | 169 | 238 非空池中 69 命中、169 未命中 |
| remap 面（remap>0） | 115 | 151 题中 36 命中（23.84%） |
| 非 remap 面 | 94 | 147 题中 53 命中（36.05%） |

**要点：** 空池题仍有 1 次模型调用和 1–8 个提交事件（novel proposals），并非“无答案”；
60 个空池题 20 个命中，命中率 33.3%，高于非空池的 29.0%。**空池本身不是丢分主因。**

### 3.2 空池分群（60 题全量）

| 空池分群 | n | hit@1 | 未命中 | 备注 |
|---|---:|---:|---:|---|
| 旧批已空（T-H 旧池=0） | 53 | 20（37.74%） | 33 | 模型 novel 候选可命中 |
| 新增 7（compiler-6 身份门拒绝唯一 spec） | 7 | 0 | 7 | 6 partial + 1 unmatched；1 题是 chain13 原 hit |
| **合计** | **60** | **20（33.33%）** | **40** | |

新增 7 题的 old→new 池均为 1→0；它们全部非 remap、`model_calls=1`、事件 3–6。
其中仅 `RXNG_531caa559d3` 是 chain13 hit（strict→partial）；其余 6 题 chain13 不是 hit。
**身份门对 hit@1 的已证实损失 = 1 题；另外 6 题的反事实收益 unknown。**

### 3.3 remap / P2 面

P2 披露分母（spec 级）：`specs_total=531`、`remap_applied=242`、`add_atom≥1` 205、`≥2` 78；
本节用题级 `by_qid`（151 题 remap、134 题 add、65 题 multi-add），不把 spec 数当题数。

| 面 | n | hit@1 | 命中率 | strict（U） | strict 率 |
|---|---:|---:|---:|---:|---:|
| remap any | 151 | 36 | 23.84% | 57 | 37.75% |
| remap + add（P2 主面） | 134 | 35 | 26.12% | 56 | 41.79% |
| remap + multi-add≥2 | 65 | 21 | 32.31% | 32 | 49.23% |
| remap-only（add=0） | 17 | 1 | 5.88% | 1 | 5.88% |
| 非 remap 对照 | 147 | 53 | 36.05% | 69 | 46.94% |

- remap 面与非 remap 面命中率差 **12.2 个百分点**；按非 remap 命中率外推，151 题应有
  约 54.4 个命中，实际 36 个，**缺口约 18.4 题**。
- 这是**关联**，不是因果：remap 题集的难度/题型可能与对照不同，本批没有同题 A/B。
- **remap-only 17 题是更尖的信号**：1 命中、7 partial、9 unmatched；其中 9 个 unmatched
  里有 6 个旧口径投影也无候选。小样本，但对“模板 remap 编译链”的排查价值高。
- P2 add 面（134 题）命中率 26.12%，也低于非 remap 对照；multi-add 反而更高（32.31%）。

### 3.4 与 chain13 v2 / v1 的交叉

| 切面 | 未命中题数 | 说明 |
|---|---:|---|
| chain13 v2 命中、T-H v2 未命中 | 16 | 即 16 个退化题 |
| chain13 v2 未命中、T-H v2 未命中 | 193 | 绝大部分没有迁移 |
| v1 命中 | 0 | v2 命中集合包含全部 v1 命中；v1→v2 只新增 5 命中 |
| chain13 v2 桶 = strict（rank1） | 16 | 全部退化题都是 chain13 v2 hit；退化发生在 T-H v2 |
| chain13 v2 桶 = partial | 0 | — |
| chain13 v2 桶 = unmatched | 0 | — |

### 3.5 21 题身份门影响面

| 指标 | 值 |
|---|---:|
| 身份门 cop qid 数 | 21 |
| 其中 T-H v2 hit@1 | 1（`RXNG_a62f2c58286`，池 3→2） |
| 其中 T-H v2 未命中 | 20 |
| 其中新增 7 空池 | 7（0 命中） |
| 其中 chain13 v2 hit | 2 |
| 其中退化为未命中 | 1（`RXNG_531caa559d3`，1→0 空池，strict→partial） |

**读法：** 21 个 spec 被身份门拒绝/替换，并不等于 21 题丢分；最终只有 1 题从 chain13 hit
退化为未命中。其余 19 题在 chain13 本来就不是 hit。不要把 21 直接写成 hit@1 损失。

## 4. 最大单项损失来源

**最大单块是“非空池、非零调用的 unmatched”94 题（占 209 的 44.98%、占 298 的 31.54%）。**
拆开看：

| unmatched 其它子类 | n | 其中 remap | 其中非 remap |
|---|---:|---:|---:|
| 旧口径投影也无候选（`anyof_rank=None`） | 47 | 41 | 6 |
| 旧口径有候选但未过 strict/partial | 47 | 26 | 21 |
| **合计** | **94** | **67** | **27** |

- 47 题“旧口径也无候选”更偏**检索/生成缺面**；其中 41 题在 remap 面，是 remap 关联的主要承载。
- 47 题“旧口径有候选”更偏**strict 匹配/参与物覆盖**：候选已经投影出来，但主口径 strict/partial
  没过。由于没有候选级金标匹配，不能进一步说是“匹配器误拒”还是“候选本身不对”。
- partial 53 题是另一块“接近命中”的覆盖损失（41 非空池 + 12 空池；25 remap）；
  但 partial→strict 需要补参与物/修正结构，本批没有候选级证据，不能承诺可转化。

## 5. 16 个退化题专项（chain13 v2 hit → T-H v2 未命中）

### 5.1 归类计数

| 口径 | 计数 |
|---|---|
| 按池优先级（互斥） | 空池 4、rank 2–5 8、strict→partial 3、strict→unmatched 1、零调用 0 |
| 按分数形态（不按池优先） | rank 掉出 10（8 非空 + 2 空池 rank2）、strict→partial 5（3 非空 + 2 空池）、strict→unmatched 1、零调用 0 |
| 池关系 | 新增 7 空池 1；旧空池 3；21 题身份门 1；remap 面 6；P2 add 面 4 |

T-H v2 的分数形态：strict 10（rank2 8、rank3 1、rank4 1）、partial 5、unmatched 1。
空池 4 题的内层形态＝2 题 strict rank2 + 2 题 partial。

### 5.2 逐题（qid 前缀；只含元数据）

| qid 前缀 | T-H v2 | 退化类型 | 池 old→new | 新增7空池 | 身份门 | remap | events |
|---|---|---|---|---|---|---:|
| RXNG_531caa559d3 | partial | 空池 | 1→0 | Y | Y | 0 | 4 |
| RXNG_57e0d0320b6 | strict r2 | 空池 | 0→0 | — | — | 0 | 6 |
| RXNG_adab6b32443 | partial | 空池 | 0→0 | — | — | 0 | 3 |
| RXNG_ddbcc56d153 | strict r2 | 空池 | 0→0 | — | — | 0 | 3 |
| RXNG_167dfdcc8dd | partial | strict→partial | 2→2 | — | — | 1 | 3 |
| RXNG_45d8d90fa8c | partial | strict→partial | 2→2 | — | — | 1 | 4 |
| RXNG_5727b6273dc | partial | strict→partial | 2→2 | — | — | 0 | 5 |
| RXNG_1c56dceb435 | strict r2 | rank 2–5 | 1→1 | — | — | 0 | 6 |
| RXNG_365fb0be778 | strict r4 | rank 2–5 | 1→1 | — | — | 1 | 6 |
| RXNG_3c9d29b41b6 | strict r2 | rank 2–5 | 1→1 | — | — | 0 | 6 |
| RXNG_3f134aaae71 | strict r2 | rank 2–5 | 1→1 | — | — | 0 | 2 |
| RXNG_65536b469cf | strict r3 | rank 2–5 | 3→3 | — | — | 3 | 6 |
| RXNG_9b313824f01 | strict r2 | rank 2–5 | 2→2 | — | — | 2 | 5 |
| RXNG_b139babc703 | strict r2 | rank 2–5 | 1→1 | — | — | 0 | 6 |
| RXNG_ebe7683e257 | strict r2 | rank 2–5 | 1→1 | — | — | 0 | 3 |
| RXNG_2e1157b17a3 | unmatched | strict→unmatched | 3→3 | — | — | 3 | 4 |

**读法：** 16 个退化里只有 1 题能直接连到本批 r2 池变化（身份门 1→0 空池）；其余 15 题
r2 新旧池大小未变。6 题在 P2 remap 面、4 题在 add 面；remap 与题集/修复包混杂，且 10 题
不在 remap 面，不能把退化整体归给 P2。按分数形态：10 题 strict 候选仍在但掉到 2–5 名
（8 非空 + 2 空池），5 题 strict→partial（3 非空 + 2 空池），1 题 strict→unmatched。
4 题空池中 3 题在 chain13 与 T-H 旧池都为空，只有 `RXNG_531caa559d3` 是 T-H 旧池 1→r2 0。

## 6. 18 个改善题（chain13 v2 未命中 → T-H v2 hit@1）

| 迁入路径 | n | remap | add | 空池 | 身份门/新增空池 |
|---|---:|---:|---:|---:|---:|
| unmatched→strict | 6 | 3 | 3 | 1 | 0 |
| partial→strict | 4 | 1 | 1 | 2 | 0 |
| strict（rank>1）→strict rank1 | 8 | 6 | 6 | 2 | 0 |
| **合计** | **18** | **10** | **10** | **5** | **0** |

- 18 个改善中 8 个是纯位次改善（已有 strict，只是从 rank 2/3 升到 1），10 个是覆盖改善
  （unmatched/partial→strict）。
- 0 个改善题与身份门/新增空池相关；改善不是靠本批池变化解释的。
- 18 个改善题的 v1 状态：v1 `matched_strict` 且 rank1 的 17 题、v1 partial 的 1 题
  （`RXNG_8dce8a33d8b`，v1 partial→v2 strict rank1）；无 v1 unmatched。

## 7. Top 3 可行动杠杆（含证据强度）

### 杠杆 1：位次重排（最干净的上限）

- **题数：** strict 但 rank 2–5 的 **36 题** + rank>5 的 **1 题** = **37 题**非首位 strict。
- **上限：** 若全部排到首位，hit@1 从 89 到 **126（+37，+12.4pp）**。这是数学上限，不是收益预测。
- **结构：** 36 题 rank2–5 中 31 非空池 + 5 空池；20 题 remap；10 题是 chain13 原 hit。
- **证据强度：可证（题数与上限）**；实际重排能兑现多少 **unknown**——本批 per_qid 没有
  `rank_basis`、dedup/排序策略字段，T-F 位次继承仍是 unknown（T_H_RESULT §8 #4）。
- **动作：** 先查这 37 题的排序/去重/候选序列生成，而不是再扩候选。

### 杠杆 2：P2 remap 面，尤其是 remap-only 与“旧口径无候选”子集

- **关联：** remap 151 题 hit 36（23.84%），非 remap 147 题 hit 53（36.05%）；按非 remap
  命中率外推，缺口约 **18.4 题**。
- **尖点：** remap-only（add=0）17 题仅 1 命中（5.88%），7 partial、9 unmatched；9 个
  unmatched 中 6 个旧口径无候选。
- **承载：** 94 个 unmatched 其它里 41 题是“remap + 旧口径无候选”，是最大的一块可定位子集。
- **证据强度：可证（关联与计数）**；因果 **unknown/推测**——remap 题集可能本身更难，没有同题 A/B。
- **动作：** 对 remap-only 17 题和 41 题无候选子集做编译/对齐/身份链审计；不要直接把
  “remap 导致丢分”写成结论。

### 杠杆 3：partial 覆盖转化

- **题数：** partial 53 题（41 非空池 + 12 空池；25 remap）。全部转 strict 的上限是 +53，
  但这不是可承诺收益。
- **结构：** 53 题中 5 题是 chain13 原 hit 退化（其中 2 题空池、3 题非空池）；48 题本来就不是
  chain13 hit。
- **证据强度：可证（题数）**；可转化性 **unknown**——没有逐候选/逐事件金标匹配，无法区分
  “缺一个参与物”“结构差一点”“匹配器误拒”。
- **动作：** 先做 53 题的参与物覆盖/缺口分类（只读元数据+候选级披露），再决定是否作为下一轮
  修复面；不要直接把它当 +53 的预算。

### 附：身份门 7 个新增空池（有界项，不进 top3）

- 7 题全部 0 命中；其中仅 1 题是 chain13 原 hit（`RXNG_531caa559d3`，1→0，strict→partial）。
- **已证实 hit@1 损失 = 1 题**；另外 6 题的反事实收益 **unknown**（它们 chain13 本来就不是 hit）。
- 这项应作为“已知有界回归”披露，不应写成 7 题损失，也不应挤掉上面的三个大杠杆。

## 8. 明确不成立的读法

| 读法 | 数据反证 |
|---|---|
| “60 个空池题全丢” | 60 空池中 20 题 hit@1；未命中只有 40 |
| “空池供给是最大杠杆” | 空池命中率 33.3%，高于非空池 29.0%；旧 53 空池贡献 20 命中 |
| “21 题身份门 = 21 题损失” | 21 题中仅 1 题从 chain13 hit 退化；1 题仍 hit；其余 19 题本来不是 hit |
| “v1 命中题在 v2 丢了” | 209 个 v2 未命中里 v1 命中 = 0；v2 是 v1 的超集 |
| “16 个退化都是 P2 remap 造成” | 16 题中 6 题 remap；15 题池大小未变；只有 1 题连到新增空池 |
| “strict 覆盖 126 就等于 hit@1 126” | 37 题 strict 但非首位；U=126、H5=125、L=1，排序损失真实存在 |

## 9. Unknown 清单（缺什么，不估算）

| # | unknown | 影响 | 缺什么 |
|---|---|---|---|
| 1 | 候选级/事件级归因 | 不能证明是哪个候选命中/丢分，也不能说“误拒” | 逐事件金标匹配、逐候选 strict 判定明细 |
| 2 | 误拒/unknown 类别 | 本批 per_qid 没有该字段；45 题 audit `violated` 中 12 题仍 hit，12 题 `method_failed` 中 3 题仍 hit，均不能当误拒证据 | 被拒/失败候选的结构正确性评估；audit 拒绝链的逐事件记录 |
| 3 | remap 因果 | 只能给关联，不能给因果 | 同题非 remap 对照或 A/B；题难度分层 |
| 4 | 位次重排可实现性 | 37 题上限可证，能兑现多少 unknown | `rank_basis`、dedup/排序策略、逐事件有序 rank |
| 5 | 新增 7 空池的反事实 | 仅 1 题已证实损失，其余 6 题 unknown | 恢复 spec 后的同题重放（本轮红线内不做） |
| 6 | deferred 动作的收益 | 每题 0–19 个 deferred（中位 8）、全部 budget_limit；执行后是否命中 unknown | 延后动作的重放/预算实验 |
| 7 | P2 remap 的化学有效性 | p2_face_measure 只是披露分母，不是化学有效性证明 | 化学评审/独立判据；本轮不重开 |
| 8 | 单批泛化 | 298 已见题 post-hoc；不能外推 | 新题/重复批；本轮没有 |

## 10. 证据路径

- 本报告：`/Volumes/CC/Enzyme_Agent/dependingv43/docs/T_H_R2_HIT1_LOSS_ATTRIBUTION_2026-10-20.md`
- 证据目录：`/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/t_h_r2_loss_attr_2026-10-20/`
  - `extract_r2_run_meta.py`：HPC 只读元数据提取（manifest + native_result；不输出化学字符串）
  - `r2_run_meta.json`：298 题的池/运行元数据（无金标/候选 SMILES）
  - `analyze_loss.py`：本地分类/交叉/退化/改善脚本
  - `analysis.json`：完整分类、交叉表、退化/改善明细
  - `summary.txt`：人读摘要
  - `loss_209.csv`、`degradations_16.csv`、`improvements_18.csv`：筛选输出（qid 前缀）
  - `SHA256SUMS`：上述证据文件哈希
- 本地镜像：`/Volumes/CC/Enzyme_Agent/dependingv43/reports/ppv1_s5b/t_h_2026-10-20/r2/`
  （`metrics.json`、`.v1`、`batch_report.json`、`p2_face_measure.json`、`monitoring/failure_register.json`）
- 基线：`/Volumes/CC/Enzyme_Agent/dependingv43/reports/ppv1_s5b/chain13_glm/metrics.json`
- 交付文档：`/Volumes/CC/Enzyme_Agent/dependingv43/docs/T_H_RESULT_2026-10-20.md` §7
- 身份门证据：`/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/t_h_r2_stage1_2026-10-20/07_spec_diff_old_vs_new.txt`、`08_gate_recheck_pool.txt`
- HPC（只读）：`~/ppv1_hpc/batch/t_h_s5b_298_20261020r2/`、`~/ppv1_hpc/runs/t_h_s5b_298_20261020r2/`；
  旧批对照 `~/ppv1_hpc/batch/t_h_s5b_298_20261020/`
- 归因口径先例：`/Volumes/CC/Enzyme_Agent/dependingv43/docs/CHAIN13_HIT50_DIAGNOSIS_GPT_2026-10-15.md`、`/Volumes/CC/Enzyme_Agent/dependingv43/docs/CHAIN14_ATTR_PROBE_RESULT_2026-10-17.md`

### 10.1 复现命令

```bash
cd /Volumes/CC/Enzyme_Agent/dependingv43
python3 docs/review_evidence/t_h_r2_loss_attr_2026-10-20/analyze_loss.py
```

HPC 侧提取命令（只读；本次已执行，不需要重跑）：

```bash
python3 ~/extract_r2_run_meta.py \
  ~/ppv1_hpc/batch/t_h_s5b_298_20261020r2/batch_manifest.json \
  ~/ppv1_hpc/batch/t_h_s5b_298_20261020/batch_manifest.json \
  ~/ppv1_hpc/runs/t_h_s5b_298_20261020r2 \
  ~/ppv1_hpc/batch/t_h_s5b_298_20261020/degenerate_fragment_face_v2.json \
  ~/t_h_r2_run_meta.json
```