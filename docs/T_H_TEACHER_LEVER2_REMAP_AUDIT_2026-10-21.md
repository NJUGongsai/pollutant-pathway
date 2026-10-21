# T-H 老师杠杆 2：58 题次 remap 死因审计（2026-10-21）

> **题域：298 = RHEA 通用酶学 / 已见题（post-hoc）。** 本审计所有题数、题次、比例、拒因计数只在该题域成立；
> 与 dev（B1 环境路径中间步骤）双向不外推。
>
> 批：`t_h_s5b_298_20261020r2`（封存只读；build 46954982 / run 46958084 / score 46969374）。
> 性质：**只读诊断，零模型调用、零新批次、零金标/reference_graphs/questions 内容、零结构正文输出**。
> 只读字段：manifest 候选元数据（channel / f5 / outcome / reason / route）、native_result 计数与状态、
> metrics per_qid、P0-D 供给漏斗。**没有读候选/底物 SMILES，没有读 reference_graphs，没有读金标。**
>
> 对象：remap-only 17 题 + 「旧口径 anyof 无匹配」41 题 = **58 题次**；去重后 **51 个唯一 qid**，
> 其中 50 个损失题 + 1 个命中幸存者（7 个题次重叠）。58/58 题次闭合，51/51 唯一题闭合。
>
> **措辞纪律：remap 面与非 remap 面的命中率差是关联，不是因果。本批没有同题 A/B，
> 不写「remap 导致丢分」，也不写「修掉某拒因能回收多少题」。**
> 50 是本题集的损失题数（池），不是“可回收 +50”的预测。
>
> **数字标签：** `已证` = 直接字段计数；`关联` = 分类/关联读数；`unknown` = 缺候选级证据；
> `池` = 题集/分母口径。

## 0. 结论先行

| 判定项 | 结果 | 标签 |
|---|---|---:|
| 审计闭合 | **58/58 题次；51/51 唯一 qid**；损失唯一 50；命中幸存 1 | 已证 |
| 编译空池死因 | **0/58 题次**；51/51 唯一题 `new pool_size>0`；51/51 有 `analog` compiled 候选 | 已证 |
| 死因发生环节 | **57/58 题次在 `post_compile_match_coverage`（编译后匹配/覆盖）**；1/58 是 `survivor_hit` | 已证 |
| 主死因（58 题次，供给面主瓶颈） | `no_alignment` 31、`identity_gate` 13、`element_mismatch` 8、`other` 4、`enumeration_truncation` 1、`n/a`（命中）1 | 关联分类 |
| 主死因（57 失败题次） | `no_alignment` 31、`identity_gate` 13、`element_mismatch` 8、`other` 4、`enumeration_truncation` 1 | 关联分类 |
| 主死因（50 唯一失败 qid） | `no_alignment` 28、`identity_gate` 10、`element_mismatch` 7、`other` 4、`enumeration_truncation` 1 | 关联分类 |
| 拒因层可修性（57 失败题次） | **需新契约 53、可修 3、unknown 1、无救 0** | 分类（非收益） |
| 拒因层可修性（50 唯一失败 qid） | 需新契约 46、可修 3、unknown 1、无救 0 | 分类（非收益） |
| 身份门影响面 | 10 个唯一 qid / 13 题次；17 条 `product_component_identity_invalid`；池 −1 的 9 个、±0 的 1 个；0 空池 | 已证 |
| 候选级可修性 | **57/57 失败题次 unknown**（无逐候选金标匹配、无同题 A/B） | unknown |
| 最大供给面主瓶颈 | `no_alignment`：28/50 唯一损失（56.0%）；31/57 失败题次（54.4%） | 关联 |
| 最大决定性死因 | **post-compile 匹配/覆盖：50/50 唯一损失（100%）、57/57 失败题次** | 已证（池非空 + 状态） |
| 枚举截断二级信号 | 12 题 `mapping_enumeration_truncated`、2 题 `pool_truncated`、14 题 old `width_capped_products`；主类仅 1 题 | 已证 / 关联 |
| P0-D / native | 51/51 不在 P0-D `no_recorded` 193 名单；51/51 `completed`、`model_calls=1`；1 题 `method_failed`；14 题 audit `violated`；0 `run_error` | 已证 |
| 收益 | **不估**；50 是损失题数池，不是 +50 收益 | 红线 |

**一句话：** 这 58 个题次不是「remap 后没候选」——新池全部非空，且 51/51 有 analog 编译候选；
它们死在**编译后的身份/对齐/覆盖匹配**。供给面最大背景闸门是 `no_alignment`（31/58 题次、
28/50 唯一损失），身份门次之（13/58 题次、10/50 唯一损失）；不是空池、不是枚举截断
（后者只占 1/58 的主导位）。**「旧口径无候选 41 题」实际是「旧 anyof 无匹配 41 题」，不是供给空池。**

## 1. 集合口径与「旧口径无候选」的更正

### 1.1 数据字段

| 代号 | 来源 | 用到的字段 | 不读/不输出 |
|---|---|---|---|
| M | `reports/ppv1_s5b/t_h_2026-10-20/r2/metrics.json` | `per_qid[].main.match_status/rank`；`old.anyof_rank/n_candidates/width_capped_products` | 无化学内容 |
| P2 | `.../r2/p2_face_measure.json` | `by_qid[].remap/add/add_multi` | 只作披露分母，不作化学有效性证明 |
| N/O | 封存批 `batch_manifest.json`（new/old） | `pool_size`；`pool_diagnostics.candidates[].{channel,f5,outcome,reason,route}`；`compile_failure_histogram`；`analog_*` 计数 | 不输出 substrate/candidate SMILES、结构正文 |
| R | 封存 run `native_result.json` | events / reportable / novel / deferred / audit 状态 / method_failed / run_error | 不读 reference_graphs/金标；不输出结构 |
| D | `docs/review_evidence/t_h_p0_2026-10-20/p0d_supply_funnel.json` | `by_qid.no_recorded_prefixes`；全局候选漏斗、`no_alignment` 分拆 | 无化学内容 |

分类沿用归因脚本的互斥类别（`docs/review_evidence/t_h_r2_loss_attr_2026-10-20/analyze_loss.py`）：
先零调用、再空池、再 strict 位次、再 partial，最后才是 `unmatched_nonempty_other`。
本审计的 S41 就是该脚本 `unmatched_nonempty_other` 里 `old.anyof_rank=None` 且在 remap 面的题。

### 1.2 三个集合与名单闭合

| 集合 | 定义 | 题次 | 唯一 qid | v2 状态 | 标签 |
|---|---|---:|---:|---|---|
| S17 remap-only | P2 `remap>0` 且 `add==0` | 17 | 17 | unmatched 9 / partial 7 / strict 1 | 已证 |
| S41 旧口径 anyof 无匹配 | 归因类别 `unmatched_nonempty_other` + `old.anyof_rank=None` + `q in P2.by_qid` | 41 | 41 | unmatched 41 | 已证 |
| 并集 | S17 ∪ S41 | **58 题次** | **51** | unmatched 43 / partial 7 / strict 1 | 已证 |
| 损失唯一 | 唯一题去掉 1 个命中幸存者 | — | **50** | — | 已证 |
| 命中幸存 | `RXNG_8ee93e3c64f8`（S17，v2 strict rank1） | 1 | 1 | strict r1 | 已证 |

- 7 个题次同时属于 S17 和 S41；所以 **58 是题次，不是 58 个不同题**。逐题表按 58 行保留，
  汇总时另给 51 unique、50 unique loss、1 unique hit survivor。
- 唯一 hit survivor 是 `RXNG_8ee93e3c64f8`（S17，v2 strict rank1）。它**不是损失题**，
  但在 58 行里保留，用于证明「同一 remap 面也能出 hit」，避免只挑失败样本。

**交叠 7 题**（全部同时是 remap-only + 旧 anyof None + unmatched）：
`RXNG_05c5a15c9d96`、`RXNG_7beff0374166`、`RXNG_94539b62f7f3`、`RXNG_b98e5b272c2d`、
`RXNG_d6c4161ded12`、`RXNG_e7f836a4e6e7`、`RXNG_fc8720410441`。

这 7 题不是同一死因：3 题 identity_gate、3 题 no_alignment、1 题 element_mismatch。
它们在本表里保留两行（S17 行与 S41 行），所以**分类计数按 58 行和按 51 唯一题会不同**；
引用时优先用“50 唯一损失”或明确写“58 行/题次口径”。

**完整 qid 前缀清单即 §2 表**：第 1–17 行 = S17，第 18–58 行 = S41；
7 个交叠题在表内以 `S17+S41` 标记并保留两行。

### 1.3 「旧口径无候选」是误名

S41 的 41 题在旧口径下 `anyof_rank=None`，但**不是没有候选**：

| 指标 | 读数 | 标签 |
|---|---:|---|
| `old.n_candidates=0` 的题 | **0/41** | 已证 |
| `old.gold_ids_empty=true` 的题 | **0/41** | 已证 |
| 旧口径候选数范围 | 3–16 条 | 已证 |
| 旧口径 `pool_size=0` 的题 | **0/41**；范围 1–8 | 已证 |
| 旧口径 `width_capped_products>0` 的题 | 13/41（unique；58 行口径 15 行） | 已证 |
| 新池为 0 的题 | **0/51 unique** | 已证 |
| 新池有 analog compiled 的题 | **51/51 unique** | 已证 |

**读法：** S41 的旧口径是「有候选、但 anyof/宽度口径没有匹配上」，不是「检索没召回」。
把它写成「旧口径无候选」会误导修复方向；本审计统一改称「旧口径 anyof 无匹配」。
另外，若只按“`old.anyof_rank=None` 且 remap>0”机械筛，会得到 **43** 题；归因脚本的 41
还要求类别为 `unmatched_nonempty_other`，因此排除了 2 个零调用 NC-9 题
（`RXNG_7a886593dd02`、`RXNG_ed3d70729ea7`，`model_calls=0`）。本文按归因的 **41** 执行；
若有人用字面 43，唯一题会变成 53。这是口径差，不是数据变化。

**归因文档的“9 unmatched 里 6 个旧口径无候选”应为 7。**
按 `old.anyof_rank=None` 复算：remap-only 9 个 unmatched 中 **7** 个 old anyof None；
另 2 个有旧 anyof 投影（`RXNG_65c761ceea29`、`RXNG_d23a924f7213`，均为 rank 3）。
本文以复算 7 为准。

### 1.4 新池规模与 remap 池计数

| 新池大小 | 1 | 2 | 3 | 4 | 8 | 合计 |
|---|---:|---:|---:|---:|---:|---:|
| 唯一 qid | 21 | 13 | 11 | 4 | 2 | **51** |

| 池变化 | 0（持平） | −1 | +1 | 合计 |
|---|---:|---:|---:|---:|
| S17 | 12 | 5 | 0 | 17 |
| S41 | 34 | 7 | 0 | 41 |
| 唯一去重 | 42 | 9 | 0 | 51 |

9 个 −1 全部是身份门 qid：身份门只把池缩小 1 条，不是把池清空；这 9 个 −1 也不能直接写成
9 个丢分。池计数不变不等于 remap 没改候选结构——remap 可能“换了候选但数量不变”；
本审计没有读结构，**化学正确性/换没换对 unknown**。

### 1.5 死因分类规则（单标签，互斥）

| 步骤 | 规则 | 证据字段 |
|---|---|---|
| 1 | qid 在 21 个 cop qid 内，且 `product_component_identity_invalid` 候选拒因 >0 → `identity_gate` | `degenerate_fragment_face_v2.cop_qids`；N candidate reason；O/N `pool_size` 差 |
| 2 | 否则取 N 中 `compile_rejected` 且 reason 非空的**单条最大拒因**；按类映射 | N `candidates[].reason` |
| 3 | `no_alignment` / `no_compilable_alignment` → `no_alignment` | N reason |
| 4 | `mapping_enumeration_truncated` / `alignment_limit_exceeded` / `ambiguous_alignment` / `ambiguous_mapping` → `enumeration_truncation` | N reason |
| 5 | `no_structure_correspondence` / `product_set_mismatch` / `product_component_identity_invalid` / `partial_dearomatization_inconsistent` / `center_empty` → `element_mismatch` | N reason |
| 6 | 其余拒因（charge/stereo/cosubstrate/aromatic/new_atom/execution/transform 等）→ `other`；无拒因也记 `other` | N reason |
| 7 | 同一 qid 多条 reason 并列最大时，按 `element_mismatch > enumeration_truncation > no_alignment > other` 取更具体类 | 规则固定，可复现 |

**重要限定：** 上述是“供给面主瓶颈”，不是“已证的丢分因果”。
51/51 都有编译池，所以第 2–7 步的拒因只是候选级背景；损失的决定性环节由
`new pool_size>0` + v2 状态单独判定为 `post_compile_match_coverage`。
命中幸存者 `RXNG_8ee93e3c64f8` 的 `death_cause` 记 `n/a (hit)`，不计入死因分母。

## 2. 58 题次逐题分类表

**证据图例**（每行只列字段名；全值见 `docs/review_evidence/t_h_lever2_remap_2026-10-21/lever2_remap_audit.json`）：

- `old anyof/n` = M `old.anyof_rank` / `old.n_candidates`；`None` 表示旧 anyof 无匹配，不是无候选。
- `width` = M `old.width_capped_products`（旧口径产物宽度截断数）。
- `pool o→n` = O/N `pool_size`（旧批 → r2 批）。
- `compiled new` = N `outcome=compiled` 的候选数；`a/r/c` = analog / recorded / corpus。
- `主拒因(条数; f5)` = N 中单条最大 `compile_rejected` reason 及条数；`rej/def/pass/ne/none` 是该 reason 的 f5 状态分布。
- `死因类` = 上表第 1–7 步的供给面主瓶颈；不是因果。
- `身份门` = `Y(池差;身份拒因数)`；`—` 表示不在 21 cop qid 或没有身份拒因。
- `可修性(拒因层)` = 针对该拒因的可修性，不是题级 hit 回收承诺。
- `决定性环节` = `post_compile_match_coverage`（池非空、损失在编译后）或 `survivor_hit`。
- `native e/r/n/v/m;P0D` = native_result 的 events / reportable / novel / violated / method_failed；`nr0` = 不在 P0-D `no_recorded` 193 名单，`nr1` = 在。
- P0-D：51/51 唯一题都是 `nr0`（逐行已列）。

| # | qid前缀 | 集合 | v2状态 | old anyof/n | width | pool o→n | compiled new | 主拒因(条数; f5) | 死因类 | 身份门 | 可修性(拒因层) | 决定性环节 | native e/r/n/v/m;P0D |
|---:|---|---|---|---:|---:|---|---:|---|---|---|---|---|---|
| 1 | `RXNG_05c5a15c9d96` | S17+S41 | unmatched | None/8 | 0 | 3→2 | 2(a1,r1) | `charge_edit_unsupported×11` [pass11] | **identity_gate** | Y(-1;id1) | 需新契约 | post_compile_match_coverage | 6/8/4/0/0;nr0 |
| 2 | `RXNG_0a2c91bde771` | S17 | partial | 1/14 | 0 | 2→1 | 1(a1) | `charge_edit_unsupported×6` [pass6] | **identity_gate** | Y(-1;id2) | 需新契约 | post_compile_match_coverage | 7/14/6/0/0;nr0 |
| 3 | `RXNG_15a597617bc2` | S17 | partial | 3/12 | 0 | 1→1 | 1(a1) | `no_structure_correspondence×1` [none1] | **element_mismatch** | — | 需新契约 | post_compile_match_coverage | 7/12/6/0/0;nr0 |
| 4 | `RXNG_167dfdcc8dd0` | S17 | partial | 1/6 | 0 | 2→2 | 2(a1,c1) | `product_set_mismatch×1` [none1] | **element_mismatch** | — | 需新契约 | post_compile_match_coverage | 3/6/1/0/0;nr0 |
| 5 | `RXNG_2b9dd28e603c` | S17 | partial | 3/6 | 0 | 2→2 | 2(a1,c1) | `product_set_mismatch×1` [none1] | **element_mismatch** | — | 需新契约 | post_compile_match_coverage | 4/6/2/0/0;nr0 |
| 6 | `RXNG_37e263634a33` | S17 | partial | 5/7 | 0 | 1→1 | 1(a1) | `no_alignment×2` [rej1/def1] | **no_alignment** | — | 需新契约 | post_compile_match_coverage | 4/7/3/0/0;nr0 |
| 7 | `RXNG_45d8d90fa8cc` | S17 | partial | 1/8 | 0 | 2→2 | 2(a1,c1) | `product_set_mismatch×1` [none1] | **element_mismatch** | — | 需新契约 | post_compile_match_coverage | 4/8/2/0/0;nr0 |
| 8 | `RXNG_65c761ceea29` | S17 | unmatched | 3/10 | 0 | 2→1 | 1(a1) | `charge_edit_unsupported×10` [pass10] | **identity_gate** | Y(-1;id1) | 需新契约 | post_compile_match_coverage | 7/10/6/0/0;nr0 |
| 9 | `RXNG_7beff0374166` | S17+S41 | unmatched | None/9 | 0 | 3→3 | 3(a1,r2) | `no_alignment×9` [rej5/def4] | **no_alignment** | — | 需新契约 | post_compile_match_coverage | 6/9/3/0/0;nr0 |
| 10 | `RXNG_8ee93e3c64f8` | S17 | strict r1 | 1/10 | 0 | 3→3 | 3(a1,r2) | `no_alignment×9` [rej5/def4] | **n/a (hit)** | — | n/a (hit) | survivor_hit | 7/10/4/0/0;nr0 |
| 11 | `RXNG_93d3a3ef9b71` | S17 | partial | 1/11 | 3 | 2→2 | 2(a2) | `no_alignment×2` [def2] | **no_alignment** | — | 需新契约 | post_compile_match_coverage | 6/14/4/0/0;nr0 |
| 12 | `RXNG_94539b62f7f3` | S17+S41 | unmatched | None/8 | 3 | 1→1 | 1(a1) | `no_alignment×1` [def1] | **no_alignment** | — | 需新契约 | post_compile_match_coverage | 4/11/4/0/0;nr0 |
| 13 | `RXNG_b98e5b272c2d` | S17+S41 | unmatched | None/10 | 0 | 3→3 | 3(a1,r2) | `no_alignment×9` [rej5/def4] | **no_alignment** | — | 需新契约 | post_compile_match_coverage | 7/10/4/0/0;nr0 |
| 14 | `RXNG_d23a924f7213` | S17 | unmatched | 3/7 | 0 | 1→1 | 1(a1) | `no_alignment×12` [rej4/def8] | **no_alignment** | — | 需新契约 | post_compile_match_coverage | 5/7/4/0/0;nr0 |
| 15 | `RXNG_d6c4161ded12` | S17+S41 | unmatched | None/9 | 0 | 2→1 | 1(a1) | `charge_edit_unsupported×6` [pass6] | **identity_gate** | Y(-1;id2) | 需新契约 | post_compile_match_coverage | 5/9/4/0/0;nr0 |
| 16 | `RXNG_e7f836a4e6e7` | S17+S41 | unmatched | None/10 | 0 | 1→1 | 1(a1) | `no_structure_correspondence×1` [none1] | **element_mismatch** | — | 需新契约 | post_compile_match_coverage | 6/10/5/0/0;nr0 |
| 17 | `RXNG_fc8720410441` | S17+S41 | unmatched | None/5 | 0 | 2→1 | 1(a1) | `charge_edit_unsupported×6` [pass6] | **identity_gate** | Y(-1;id2) | 需新契约 | post_compile_match_coverage | 3/5/2/0/0;nr0 |
| 18 | `RXNG_036534a3cd44` | S41 | unmatched | None/14 | 4 | 4→4 | 4(a4) | `no_alignment×10` [rej7/def3] | **no_alignment** | — | 需新契约 | post_compile_match_coverage | 8/18/4/0/0;nr0 |
| 19 | `RXNG_05c5a15c9d96` | S17+S41 | unmatched | None/8 | 0 | 3→2 | 2(a1,r1) | `charge_edit_unsupported×11` [pass11] | **identity_gate** | Y(-1;id1) | 需新契约 | post_compile_match_coverage | 6/8/4/0/0;nr0 |
| 20 | `RXNG_06453c845d47` | S41 | unmatched | None/10 | 2 | 2→2 | 2(a2) | `no_alignment×9` [rej6/def3] | **no_alignment** | — | 需新契约 | post_compile_match_coverage | 6/12/5/0/0;nr0 |
| 21 | `RXNG_0657c0389a44` | S41 | unmatched | None/4 | 0 | 2→2 | 2(a2) | 无拒因 | **other** | — | unknown | post_compile_match_coverage | 3/4/2/0/0;nr0 |
| 22 | `RXNG_103c84009b44` | S41 | unmatched | None/10 | 3 | 3→3 | 3(a3) | `charge_edit_unsupported×11` [pass10/none1] | **identity_gate** | Y(+0;id2) | 需新契约 | post_compile_match_coverage | 7/13/4/2/0;nr0 |
| 23 | `RXNG_11e08d7a2a44` | S41 | unmatched | None/7 | 0 | 3→3 | 3(a2,r1) | `no_alignment×12` [rej3/def8/ne1] | **no_alignment** | — | 需新契约 | post_compile_match_coverage | 7/7/4/2/0;nr0 |
| 24 | `RXNG_1a5528f34b65` | S41 | unmatched | None/4 | 0 | 1→1 | 1(a1) | `no_alignment×10` [rej7/def2/ne1] | **no_alignment** | — | 需新契约 | post_compile_match_coverage | 4/4/3/0/0;nr0 |
| 25 | `RXNG_22901c4d6f41` | S41 | unmatched | None/16 | 0 | 8→8 | 8(a8) | `new_atom_placement_incomplete×3` [def3] | **other** | — | 可修 | post_compile_match_coverage | 8/16/2/0/0;nr0 |
| 26 | `RXNG_2a1a5bf6480d` | S41 | unmatched | None/6 | 0 | 3→2 | 2(a1,r1) | `no_alignment×10` [rej6/def4] | **identity_gate** | Y(-1;id2) | 需新契约 | post_compile_match_coverage | 6/6/4/1/0;nr0 |
| 27 | `RXNG_2e31a4648b68` | S41 | unmatched | None/11 | 1 | 1→1 | 1(a1) | `new_atom_placement_incomplete×1` [def1] | **other** | — | 可修 | post_compile_match_coverage | 8/12/7/0/0;nr0 |
| 28 | `RXNG_330df242afd7` | S41 | unmatched | None/10 | 1 | 4→4 | 4(a4) | `no_alignment×10` [rej8/def2] | **no_alignment** | — | 需新契约 | post_compile_match_coverage | 8/11/4/0/0;nr0 |
| 29 | `RXNG_39a545f6bb42` | S41 | unmatched | None/13 | 0 | 2→2 | 2(a2) | `no_alignment×3` [rej2/def1] | **no_alignment** | — | 需新契约 | post_compile_match_coverage | 7/13/5/0/0;nr0 |
| 30 | `RXNG_3d58685aebce` | S41 | unmatched | None/3 | 0 | 2→1 | 1(a1) | `no_alignment×7` [rej3/def4] | **identity_gate** | Y(-1;id1) | 需新契约 | post_compile_match_coverage | 2/3/3/1/0;nr0 |
| 31 | `RXNG_46c6b17b0697` | S41 | unmatched | None/8 | 1 | 3→3 | 3(a3) | `no_alignment×1` [ne1] | **no_alignment** | — | 需新契约 | post_compile_match_coverage | 6/9/3/2/0;nr0 |
| 32 | `RXNG_4ec68aa8196a` | S41 | unmatched | None/5 | 0 | 3→2 | 2(a1,r1) | `no_alignment×10` [rej6/def4] | **identity_gate** | Y(-1;id2) | 需新契约 | post_compile_match_coverage | 4/5/2/1/0;nr0 |
| 33 | `RXNG_50e0f19bd85d` | S41 | unmatched | None/7 | 0 | 3→3 | 3(a2,r1) | `no_alignment×12` [rej3/def8/ne1] | **no_alignment** | — | 需新契约 | post_compile_match_coverage | 7/7/4/2/0;nr0 |
| 34 | `RXNG_5876dc9dadf8` | S41 | unmatched | None/6 | 0 | 1→1 | 1(a1) | `no_alignment×10` [rej6/def4] | **no_alignment** | — | 需新契约 | post_compile_match_coverage | 6/6/5/0/0;nr0 |
| 35 | `RXNG_72d2660c0f1b` | S41 | unmatched | None/9 | 0 | 1→1 | 1(a1) | `no_alignment×4` [rej3/def1] | **no_alignment** | — | 需新契约 | post_compile_match_coverage | 5/9/4/0/0;nr0 |
| 36 | `RXNG_75674c48e707` | S41 | unmatched | None/4 | 0 | 1→1 | 1(a1) | `mapping_enumeration_truncated×2` [none2] | **enumeration_truncation** | — | 可修 | post_compile_match_coverage | 4/4/3/1/0;nr0 |
| 37 | `RXNG_76160d33bf9f` | S41 | unmatched | None/4 | 0 | 1→1 | 1(a1) | `no_alignment×11` [rej2/def9] | **no_alignment** | — | 需新契约 | post_compile_match_coverage | 4/4/3/0/0;nr0 |
| 38 | `RXNG_7bd87d400375` | S41 | unmatched | None/8 | 0 | 1→1 | 1(a1) | `no_alignment×5` [rej2/def3] | **no_alignment** | — | 需新契约 | post_compile_match_coverage | 7/8/6/1/0;nr0 |
| 39 | `RXNG_7beff0374166` | S17+S41 | unmatched | None/9 | 0 | 3→3 | 3(a1,r2) | `no_alignment×9` [rej5/def4] | **no_alignment** | — | 需新契约 | post_compile_match_coverage | 6/9/3/0/0;nr0 |
| 40 | `RXNG_891c844ebaa8` | S41 | unmatched | None/13 | 3 | 2→2 | 2(a2) | `no_alignment×9` [rej6/def3] | **no_alignment** | — | 需新契约 | post_compile_match_coverage | 7/16/5/0/0;nr0 |
| 41 | `RXNG_89b8bce798e2` | S41 | unmatched | None/11 | 3 | 3→3 | 3(a3) | `no_alignment×3` [rej2/def1] | **no_alignment** | — | 需新契约 | post_compile_match_coverage | 8/14/5/1/0;nr0 |
| 42 | `RXNG_94539b62f7f3` | S17+S41 | unmatched | None/8 | 3 | 1→1 | 1(a1) | `no_alignment×1` [def1] | **no_alignment** | — | 需新契约 | post_compile_match_coverage | 4/11/4/0/0;nr0 |
| 43 | `RXNG_a319f41e077e` | S41 | unmatched | None/5 | 0 | 1→1 | 1(a1) | `partial_dearomatization_inconsistent×1` [none1] | **element_mismatch** | — | 需新契约 | post_compile_match_coverage | 3/5/5/0/0;nr0 |
| 44 | `RXNG_a401c95418f5` | S41 | unmatched | None/9 | 1 | 3→3 | 3(a3) | `no_alignment×11` [rej7/def4] | **no_alignment** | — | 需新契约 | post_compile_match_coverage | 6/10/4/0/1;nr0 |
| 45 | `RXNG_ae3a789f9c20` | S41 | unmatched | None/3 | 0 | 1→1 | 1(a1) | `no_alignment×10` [rej7/def2/ne1] | **no_alignment** | — | 需新契约 | post_compile_match_coverage | 3/3/3/0/0;nr0 |
| 46 | `RXNG_aefef2f58e31` | S41 | unmatched | None/7 | 0 | 3→3 | 3(a3) | `no_structure_correspondence×1` [none1] | **element_mismatch** | — | 需新契约 | post_compile_match_coverage | 4/7/4/1/0;nr0 |
| 47 | `RXNG_b98e5b272c2d` | S17+S41 | unmatched | None/10 | 0 | 3→3 | 3(a1,r2) | `no_alignment×9` [rej5/def4] | **no_alignment** | — | 需新契约 | post_compile_match_coverage | 7/10/4/0/0;nr0 |
| 48 | `RXNG_cd29a6432c26` | S41 | unmatched | None/10 | 1 | 4→4 | 4(a3,r1) | `no_alignment×3` [def3] | **no_alignment** | — | 需新契约 | post_compile_match_coverage | 8/11/4/2/0;nr0 |
| 49 | `RXNG_d239738da046` | S41 | unmatched | None/8 | 0 | 2→2 | 2(a2) | `no_alignment×3` [rej2/def1] | **no_alignment** | — | 需新契约 | post_compile_match_coverage | 4/8/3/0/0;nr0 |
| 50 | `RXNG_d6c4161ded12` | S17+S41 | unmatched | None/9 | 0 | 2→1 | 1(a1) | `charge_edit_unsupported×6` [pass6] | **identity_gate** | Y(-1;id2) | 需新契约 | post_compile_match_coverage | 5/9/4/0/0;nr0 |
| 51 | `RXNG_d89bf895ae38` | S41 | unmatched | None/14 | 0 | 1→1 | 1(a1) | `charge_edit_unsupported×15` [pass13/none2] | **other** | — | 需新契约 | post_compile_match_coverage | 8/14/7/0/0;nr0 |
| 52 | `RXNG_e7f836a4e6e7` | S17+S41 | unmatched | None/10 | 0 | 1→1 | 1(a1) | `no_structure_correspondence×1` [none1] | **element_mismatch** | — | 需新契约 | post_compile_match_coverage | 6/10/5/0/0;nr0 |
| 53 | `RXNG_eb7a8583af6d` | S41 | unmatched | None/6 | 0 | 3→2 | 2(a1,r1) | `no_alignment×10` [rej6/def4] | **identity_gate** | Y(-1;id2) | 需新契约 | post_compile_match_coverage | 5/6/3/1/0;nr0 |
| 54 | `RXNG_ef027adac9a9` | S41 | unmatched | None/10 | 1 | 4→4 | 4(a3,r1) | `no_alignment×3` [def3] | **no_alignment** | — | 需新契约 | post_compile_match_coverage | 8/11/4/2/0;nr0 |
| 55 | `RXNG_f6ac633af28c` | S41 | unmatched | None/9 | 0 | 1→1 | 1(a1) | `no_alignment×10` [rej6/def4] | **no_alignment** | — | 需新契约 | post_compile_match_coverage | 6/9/5/0/0;nr0 |
| 56 | `RXNG_fb86653f3fe3` | S41 | unmatched | None/14 | 0 | 8→8 | 8(a8) | `no_alignment×8` [def8] | **no_alignment** | — | 需新契约 | post_compile_match_coverage | 8/14/4/0/0;nr0 |
| 57 | `RXNG_fc8720410441` | S17+S41 | unmatched | None/5 | 0 | 2→1 | 1(a1) | `charge_edit_unsupported×6` [pass6] | **identity_gate** | Y(-1;id2) | 需新契约 | post_compile_match_coverage | 3/5/2/0/0;nr0 |
| 58 | `RXNG_fd4e0bad9fcb` | S41 | unmatched | None/9 | 3 | 3→3 | 3(a3) | `no_alignment×10` [rej7/def2/ne1] | **no_alignment** | — | 需新契约 | post_compile_match_coverage | 6/12/3/0/0;nr0 |

## 3. 死因计数与关键证据

### 3.1 死因主类计数（四种分母）

| 死因类 | 58 题次 | 57 失败题次 | 51 唯一 | 50 唯一失败 | 标签 |
|---|---:|---:|---:|---:|---|
| `no_alignment` | 31 | 31 | 28 | 28 | 关联分类 |
| `identity_gate` | 13 | 13 | 10 | 10 | 已证门 + 关联分类 |
| `element_mismatch` | 8 | 8 | 7 | 7 | 关联分类 |
| `other` | 4 | 4 | 4 | 4 | 关联分类 |
| `enumeration_truncation` | 1 | 1 | 1 | 1 | 关联分类 |
| `n/a (hit)` | 1 | — | 1 | — | 已证 |
| **合计** | **58** | **57** | **51** | **50** | |

**读法：** 58 题次口径下 `no_alignment` 31/57 失败题次（54.4%）；50 唯一失败口径下 28/50（56.0%）。
这是“单条最大拒因”的计数，不是“修掉 no_alignment 就能回收 28 题”。所有 50 个唯一失败题
都有非空编译池，且 0 题是空池/零候选。

**`no_alignment` 的候选级总数：** 51 唯一题的 `compile_rejected` 里 `no_alignment` 290 条
（`no_compilable_alignment` 另 3 条）；这是**本集 51 题**的候选行计数。P0-D 的全局 1585 条
（F5 预门 reject 864 + F5 defer 后编译器 543 + 非 F5 178）是 **298 全批**候选行级，不是本集，
两者不混比。本集逐题的 no_alignment f5 分布见 §2 表 `[rej/def/...]`。

### 3.2 可修性计数（拒因层 vs 题级）

| 可修性 | 58 题次 | 57 失败题次 | 51 唯一 | 50 唯一失败 | 标签 |
|---|---:|---:|---:|---:|---|
| `可修`（同规则） | 3 | 3 | 3 | 3 | 分类 |
| `需新契约`（化学/身份判据变更） | 53 | 53 | 46 | 46 | 分类 |
| `unknown` | 1 | 1 | 1 | 1 | unknown |
| `无救` | 0 | 0 | 0 | 0 | 已证 0 |
| `n/a (hit)` | 1 | — | 1 | — | 已证 |
| **合计** | **58** | **57** | **51** | **50** | |

**可修 3 题（唯一）**：`RXNG_75674c48e707`（`mapping_enumeration_truncated` 为最大拒因）、
`RXNG_22901c4d6f41`、`RXNG_2e31a4648b68`（`new_atom_placement_incomplete` 为最大拒因）。
只表示这些拒因可走同规则工程修，不表示修完 hit 能回来。

**unknown 1 题**：`RXNG_0657c0389a44`（无 compile_rejected 拒因，2 条 analog 已编译，仍 unmatched；
缺候选级匹配证据）。

**无救 0 题**：本集没有空池、没有零候选；不能把某个模板的 `no_structure_correspondence`
扩大成整题无救。整题可救性仍是 unknown。

**`fixability_qid` 57/57 unknown**：没有逐候选金标匹配，也没有同题 A/B；无法证明
「哪条候选被误拒」或「修掉主拒因后 hit@1 能回收多少」。本表**不写转化预期值**。

### 3.3 最大发现：没有一题死于编译链全灭

| 指标 | 值 | 标签 |
|---|---:|---|
| 唯一题 `new pool_size>0` | 51/51 | 已证 |
| 唯一题有 `analog` compiled 候选 | 51/51 | 已证 |
| 空池题 | 0/51 | 已证 |
| `new pool_size` 分布（唯一） | 1:21、2:13、3:11、4:4、8:2 | 已证 |
| `old pool_size` 分布（唯一） | 1:16、2:14、3:15、4:4、8:2 | 已证 |
| pool 差 old→new（唯一） | 0:42、−1:9、增加:0 | 已证 |
| S41 old `n_candidates=0` | 0/41；范围 3–16 | 已证 |
| S41 old `anyof_rank=None` | 41/41 | 已证 |
| S41 old `pool_size=0` | 0/41；范围 1–8 | 已证 |
| 失败题次决定性环节 post_compile | 57/57 | 已证 |

**这张表直接否掉“58 题次是 remap 编译链死亡”的读法：**
- 41 题是按旧 **anyof 评分**选出来的，不是按编译失败选出来的；41/41 旧候选投影和新编译池都非空。
- 17 题 remap-only 也没有一题空池；唯一命中 `RXNG_8ee93e3c64f8` 就在这 17 题里。
- 57 个失败题次的池非空，说明丢分发生在编译后的 strict/partial/unmatched 匹配与覆盖层，
  不是“编译全灭/无候选可提交”。

**remap-only 与非 remap 对照（关联，不是因果）：** remap-only 17 题是 **1 命中（5.88%）、
7 partial、9 unmatched**；非 remap 对照 147 题是 **53 命中（36.05%）**。这是同批描述性关联；
remap-only 的题型/难度可能不同，**没有同题 A/B，不能写成“remap 导致命中率低”**。
（数字标签：已证/描述。）

### 3.4 身份门：10 题、13 题次，9 题池 −1

| 指标 | 值 | 标签 |
|---|---:|---|
| 本集 identity_gate 唯一题 | 10 | 已证 |
| 58 题次中 identity_gate 题次 | 13（3 个交叠题各两行） | 已证 |
| 池差 −1 | 9 题 | 已证 |
| 池差 0 | 1 题（`RXNG_103c84009b44`） | 已证 |
| `product_component_identity_invalid` 拒因合计 | 17 条 | 已证 |
| 身份门后空池 | 0 题 | 已证 |
| 身份门题 `new pool` 范围 | 1–3 | 已证 |

21 个 cop qid 中只有 10 个落在这 58 题次内；其余 11 个不在本审计对象，不能把本集 10 当身份门全量。

身份门是唯一有 qid 级 old→new 池差的已识别门：9 题各少 1 条已编译候选，但仍剩 1–3 条；
1 题池不变（`RXNG_103c84009b44`，身份拒因 2 条）。**因此身份门不是“整题零供”**，
且被拒的那 1 条是否含正确候选 **unknown**（无候选级结构/金标证据）。
**不要把 13 题次读成 13 个丢分**；可修性归 `需新契约`：放宽/改写身份判据属于化学/身份契约变更，
不是工程 patch。

### 3.5 枚举截断：主类 1 题，但二级信号覆盖 25 题

| 信号 | 唯一题 | 行/条 | 标签 |
|---|---:|---:|---|
| `mapping_enumeration_truncated` | 12 | 22 条候选 | 已证 |
| `pool_truncated` | 2 | 3 条候选（`RXNG_22901c4d6f41` 1、`RXNG_fb86653f3fe3` 2） | 已证 |
| old `width_capped_products>0` | 14 | 15 行；`width` 合计 30 | 已证 |
| 至少一个上述信号 | **25** | — | 已证 |
| 主类 `enumeration_truncation` | **1** | `RXNG_75674c48e707` | 关联分类 |

**不要把 25 直接写成 25 题枚举死因。** 三层不是同一环节：
`mapping_enumeration_truncated` 是编译器枚举；`pool_truncated` 是池上限；
`width_capped_products` 是旧 anyof 评分口径的产物宽度截断。只有 1 题把枚举截断作为单条最大拒因。
S41 里 13/41 有 old width cap（31.7%），全 298 是 64/298（21.5%）——轻度富集，关联，不是因果。

### 3.6 P0-D 与 native 元数据

| 指标 | 值 | 标签 |
|---|---:|---|
| 本集在 P0-D `no_recorded` 193 名单 | 0/51 | 已证 |
| P0-D 全局候选行 / compiled / compile_rejected | 5319 / 531 / 4311 | 池 |
| P0-D `no_alignment` 总候选 | 1585 = F5 预门 reject 864 + F5 defer 后编译器 543 + 非 F5 178 | 已证 |
| P0-D F3 wildcard 预门跳过 | 992（不是候选行，单列） | 已证 |
| native `completed` | 51/51 | 已证 |
| `model_calls=1` | 51/51 | 已证 |
| events | 2–8（2:1、3:5、4:10、5:4、6:11、7:11、8:9） | 已证 |
| `method_failed` | 1 题（`RXNG_a401c95418f5`） | 已证 |
| audit `violated` | 14 题 | 已证 |
| `run_error` 非空 | 0/51 | 已证 |
| recorded 候选缺失 / corpus 候选缺失 | 9 题 / 11 题；但 51/51 有 analog 候选 | 已证 |

`method_failed` 和 audit `violated` 都不能当丢分标记：归因文档全批 45 题 audit violated 里 12 题仍 hit；
本集 1 题 method_failed 也仍有编译候选。这里只作运行面背景，不升级成死因。
本集没有 `retrieval_missing` 整题缺供：51/51 至少有 analog 候选；9/11 题的 recorded/corpus 通道缺口
不足以构成“整题检索缺失”。

### 3.7 与归因文档的对账

| 项 | 归因文档 | 本审计 | 一致/差异 |
|---|---|---:|---|
| `unmatched 其它 94` 里旧 anyof None | 47 | 47（其中 remap 41、非 remap 6） | 一致 |
| remap 面旧 anyof None | 41 | 41（S41） | 一致 |
| remap-only 17 | 17 | 17（S17） | 一致 |
| remap-only 1 hit / 7 partial / 9 unmatched | 1 / 7 / 9 | 1 / 7 / 9 | 一致 |
| remap-only 9 unmatched 中旧 anyof None | 6 | **7** | **差 1，本文以复算 7 为准** |
| remap-only 旧 anyof None 总数 | 未单列 | 7（全部 unmatched） | 补充 |
| S41 旧 n_candidates>0 | 未单列 | 41/41，3–16 | 补充（纠正“无候选”读法） |

> 47 个 `unmatched 其它` 里的旧 anyof None = **41 remap + 6 非 remap**；本审计只覆盖 41 remap 面，
> 6 个非 remap 题不在 58 对象内，未做逐题分类。这里引用 47 只用于对账，不把 6 个非 remap 混进分母。

## 4. 可修性与下一步（不写收益）

| 去向 | 拒因层（57 失败题次 / 50 唯一失败） | 题 | 下一步 |
|---|---|---|---|
| `可修`（同规则） | 3 / 3 | `RXNG_75674c48e707`、`RXNG_22901c4d6f41`、`RXNG_2e31a4648b68` | 可做合成夹具/离线重放，但只验证拒因消失，不承诺 hit 回收 |
| `需新契约` | 53 / 46 | no_alignment 28、identity_gate 10、element_mismatch 7、other 1（`RXNG_d89bf895ae38` charge） | 化学/身份判据变更，须预注册；不是 patch |
| `unknown` | 1 / 1 | `RXNG_0657c0389a44` | 需要候选级匹配证据；本轮红线内不做 |
| `无救` | 0 / 0 | — | 本集无空池/零候选，不能宣布无救 |

**建议（按证据强度）：**

1. **不要基于本审计立“remap 编译修复”批。** 51/51 有编译池、0 空池、57/57 失败题次在 post_compile；
   没有任何一题是编译链全灭。若老师要推进杠杆 2，下一道判别器必须是**候选级匹配/覆盖证据**
   （需要候选级正确性判断或同题 A/B；本轮红线内不做），而不是再加编译拒因。
2. **身份门按“新契约”处理。** 9 题池 −1、1 题池 0，全部仍非空；放宽身份判据属于化学/身份判据变更，
   应走预注册，不应作为工程补丁。被拒候选是否正确 unknown。
3. **枚举截断可做“上限抬升”预注册，但不要按 25 题算收益。** 主类只有 1 题；25 题是三层信号的并集。
   若要试，先固定单变量（只动枚举/池上限），并接受命中回收 unknown。
4. **口径修正入下一份文档：** 把“旧口径无候选 41 题”改写成“旧 anyof 无匹配 41 题”；
   同时保留“41/41 old n_candidates 3–16”这句，避免再被读成供给空池。
5. **交叠 7 题在后续分母中只算一次。** 58 题次是老师口径的行数；唯一 51、失败 50 才是题级分母。

## 5. 证据与复现

- 本报告：`/Volumes/CC/Enzyme_Agent/dependingv43/docs/T_H_TEACHER_LEVER2_REMAP_AUDIT_2026-10-21.md`
- 证据目录：`/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/t_h_lever2_remap_2026-10-21/`
  - `extract_candidate_meta.py`：HPC 只读候选元数据提取（channel/f5/outcome/reason/route；不输出 SMILES）
  - `new_candidate_meta.json`、`old_candidate_meta.json`：r2/旧批 51 题的候选元数据（无结构正文）
  - `build_lever2_audit.py`：本地分类/计数脚本
  - `lever2_remap_audit.json`：58 行 + 51 唯一 + 汇总 + 口径定义 + 源哈希 + unknown
  - `table_58.md`：本报告 §2 的表（机读生成）
  - `summary.txt`：人读摘要
  - `qid_sets.json`：S17 / S41 / 交叠 / 唯一 qid 清单
  - `SHA256SUMS`：上述文件哈希
- 只读源：
  - `reports/ppv1_s5b/t_h_2026-10-20/r2/{metrics.json,p2_face_measure.json,batch_report.json}`
  - `docs/review_evidence/t_h_r2_loss_attr_2026-10-20/r2_run_meta.json`
  - `docs/review_evidence/t_h_p0_2026-10-20/p0d_supply_funnel.json`
  - 权威路径（只读）：`~/ppv1_hpc/batch/t_h_s5b_298_20261020r2/batch_manifest.json`、
    `~/ppv1_hpc/batch/t_h_s5b_298_20261020/batch_manifest.json`、
    `~/ppv1_hpc/batch/t_h_s5b_298_20261020/degenerate_fragment_face_v2.json`
- 复现命令：

```bash
cd /Volumes/CC/Enzyme_Agent/dependingv43
python3 -B docs/review_evidence/t_h_lever2_remap_2026-10-21/build_lever2_audit.py
```

HPC 只读提取（本次已执行，不需要重跑；只在需要复核时使用）：

```bash
KEY=/Volumes/CC/Enzyme_Agent/aclhl3hbth_wuzh02.hpccube.com_RsaKeyExpireTime_2026-11-30_10-12-36.txt
scp -i "$KEY" -P 65091 \
  docs/review_evidence/t_h_lever2_remap_2026-10-21/extract_candidate_meta.py \
  docs/review_evidence/t_h_lever2_remap_2026-10-21/qid_sets.json \
  aclhl3hbth@wuzh02.hpccube.com:/tmp/th_lever2/
ssh -i "$KEY" -p 65091 aclhl3hbth@wuzh02.hpccube.com \
  'cd /tmp/th_lever2 && python3 extract_candidate_meta.py \
   /work/home/aclhl3hbth/ppv1_hpc/batch/t_h_s5b_298_20261020r2/batch_manifest.json \
   qid_sets.json --out new_candidate_meta.json && \
   python3 extract_candidate_meta.py \
   /work/home/aclhl3hbth/ppv1_hpc/batch/t_h_s5b_298_20261020/batch_manifest.json \
   qid_sets.json --out old_candidate_meta.json'
```

> 注：`qid_sets.json` 的顶层是 `{"S17":[...],"S41":[...],"union":[...],"overlap":[...]}`；
> `extract_candidate_meta.py` 读取 `union` 键，与仓库内文件一致。

## 6. 仍缺字段 / unknown

| # | unknown | 影响 | 缺什么 |
|---:|---|---|---|
| 1 | 候选级/事件级金标匹配 | 不能证明哪条候选被误拒，也不能把 no_alignment 写成丢分因果 | 逐候选/逐事件正确性判断；本轮不读金标 |
| 2 | remap 化学有效性 | 不能证明 remap 换对了/换错了；池计数不变不代表候选没变 | 结构级对照/化学评审；本轮不读结构 |
| 3 | 同题非 remap 对照或 A/B | remap 因果 unknown；只能给关联 | 同题 A/B 或题难度分层 |
| 4 | 身份门拒绝的那 1 条 spec 是否含正确候选 | 不能把身份门 9 题池 −1 写成 9 题损失 | 被拒候选的结构/正确性评估 |
| 5 | old width_cap 是否切掉正确产物 | 枚举截断的旧口径影响 unknown | 旧口径候选级产物序列/正确性 |
| 6 | 主拒因修掉后 hit@1 回收多少 | 可修性不是收益；3 题可修也不等于 +3 | 同题离线重放/新批单变量实验 |
| 7 | no_alignment 是算法漏配还是化学不支持 | 决定它是“可修”还是“需新契约” | 候选级 alignment 明细；本轮只有 reason 计数 |
| 8 | P0-D 的逐题 no_alignment 分拆 | P0-D 只给全局 864/543/178；逐题分拆由 manifest 候选行给出，口径不完全同源 | 逐题 F5 预门/编译器分拆的权威导出 |
| 9 | 单批泛化 | 298 已见题 post-hoc；不能外推 dev/新题 | 新题/重复批；本轮没有 |