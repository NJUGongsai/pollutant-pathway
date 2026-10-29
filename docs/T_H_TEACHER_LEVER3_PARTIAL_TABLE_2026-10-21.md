# T-H 老师杠杆 3：53 题 partial 覆盖缺口分类表

> **题域标签：298 = RHEA 通用酶学 / 已见题（post-hoc）。** 本文全部题数、比例和分类
> 只在本批 298 题域成立，不向 dev、新题或其他题域外推。
>
> 批：`t_h_s5b_298_20261020r2`（封存只读）。本文**零模型调用、零新批次、零判分改动**；
> **零金标/reference_graphs 结构正文、零 SMILES/结构正文输出**；不改封存批与主树；不 push。
> 日期：2026-10-21。对应任务书 §三（杠杆 3）。

## 0. 结论

- **53/53 闭合（已证=判分桶计数；池=298 题域）。** 53 行每行都有组分类型和去向；
  `unknown=0`。
- 组分类型（老师口径，互斥）：

| 组分类型 | 题数 | 池/证据标签 | 一句话 |
|---|---:|---|---|
| `bookkeeping_exempt`（簿记类） | **16** | 池=53；已证=身份族+tier 计数 | H₂O/H⁺/Pi/PPi 身份族；53 内 v2 三谓词未全过，所以仍是 partial |
| `cofactor`（辅因子/共底物） | **5** | 池=53；已证=角色+成分计数 | NAD(P)/NADH 2 题、O₂/H₂O₂ 3 题；化学必要性送师姐 |
| `structural_near`（结构差一点） | **7** | 池=53；已证=同式/同骨架代理比较 | 缺的参考主产物与事件产物同式或同骨架（≥6 重原子） |
| `other`（其他） | **25** | 池=53；已证=逐事件角色差集 | 21 未声明副产物 + 3 多声明主产物 + 1 缺主产物且无近结构 |
| `unknown` | **0** | — | 无 |

- 去向（三类）：

| 去向 | 题数 | 池/上限/已证标签 | 含义 |
|---|---:|---|---|
| **可修（下一批修复面）** | **44** | 池=53；分类已证；转化上限 unknown | 16 簿记 + 7 结构近 + 21 未声明副产物；只表示有修复面，不承诺兑现 |
| **待裁定（辅因子类）** | **5** | 池=53；已证=5 题 | 化学判断送师姐；本表不写判据结论 |
| **放弃（本轮）** | **4** | 池=53；已证=4 题 | 3 多声明主产物 + 1 缺主产物且无近结构；不是永久否定 |
| unknown | **0** | — | 无 |

- **5 题 T-1 已兑现的 H₂O 豁免不在 53 内（已证：v1 partial → v2 strict rank 1；
  与 P0-C `v2_exemptions=5 occurrences` 一致）。** 53 已经是豁免后的 partial 集。
- **P0-C 的 45/6/2 只是题内 superset/partial_subset 事件形态分组，不是 missing-only 证明。**
  本表按逐事件两侧 `state_ref` 差集重算，得到 **extra 45 / mixed_components 5 / missing 3**。
  3 个 P0-C 标为 `missing` 的题，事件里同时有多和缺（Codex P0 评审 D-3 的同一条提醒）。
- **不写转化预期。** 53 是池计数；全部转 strict 的 **+53 是上限，不是预期**。可修=存在
  下一批修复面，不等于可兑现；没有候选级/事件级金标匹配，也没有同题 A/B。

## 1. 口径

### 1.1 partial 与逐事件差集

- `partial`：metrics v2（headline）`match_status = matched_participant_coverage_partial`，
  53 题；41 非空池 + 12 空池；25 remap + 28 非 remap（已证=本地 metrics 计数）。
- `p0c形态`：P0-C 的题内事件形态分组（extra=只出现 superset、missing=只出现
  partial_subset、mixed=同题两形态并存）。**它是事件形态，不是逐事件 missing-only 证明。**
- `逐事件方向`：本表对每个 `coverage_mismatch_events` 事件做两侧 `state_ref` 集合差：
  `extra`（事件多出参考参与物）、`missing`（事件缺参考参与物）、`mixed_components`
  （同一题两种差集都有）。这一列才是老师说的“缺哪类组分”的机械底稿。
- `缺节点`：参考节点没有出现在该侧事件里。参考节点身份用它的 **strict 匹配候选状态**
  代理（候选状态与参考节点严格身份相等）；本表只比较“同分子式/同 Murcko 骨架”，
  不读参考图结构正文，也不输出任何 SMILES/结构文本。

### 1.2 组分类型（老师口径）

| 类型 | 判定（机械可复核） | 题数 |
|---|---|---:|
| `bookkeeping_exempt` | extra 的 cn 身份落在 criteria-v2 豁免族（H₂O/H⁺/Pi/PPi）。53 内身份属簿记族，但 v2 三谓词没有全部通过（全批 tier：4 `v1_exempt` / 60 `not_exempt`），所以仍为 partial。 | 16 |
| `cofactor` | 非豁免 extra 的角色是 `cosubstrate`（NAD(P)/NADH、O₂/H₂O₂ 等氧化还原/载体共底物）；或 ≥30 重原子且含 P/N、S/N 的大辅因子。 | 5 |
| `structural_near` | 缺失参考主产物与事件侧产物**同分子式**，或**同 Murcko 骨架且 ≥6 重原子**；另含“同身份错侧/重复”的簿记角色成分。 | 7 |
| `other` | 剩余覆盖缺口：21 未声明副产物 + 3 多声明主产物 + 1 缺主产物且无可接受近结构。 | 25 |
| `unknown` | 无缺口成分或代理不可解析。本批 0。 | 0 |

**簿记类的关键读法：** 5 个 T-1 已兑现题是“全部 extras 都过 v2 三谓词 ⇒ 升 exact”的那一档，
**不在 53 内**。53 内还有 16 题的身份同属 H₂O/H⁺/Pi/PPi 族，但 v2 豁免评审的 tier 只有
**4 个 v1_exempt / 60 个 not_exempt**（已证=逐实例 tier 计数），即谓词没有全过，所以维持
partial。这 16 题是“簿记类待修”，不是“已经豁免过”。

### 1.3 去向

| 去向 | 映射 | 说明 |
|---|---|---|
| **可修** | 16 簿记 + 7 结构近 + 21 未声明副产物 | 修复面分别是：T-1 声明/谓词链、身份/近结构归一、共产物声明/忽略档规则。**不删真实副产物**；具体规则需判据/化学裁定，不能写成已兑现。 |
| **待裁定** | 5 辅因子/共底物 | 化学必要性、是否应忽略/声明，送师姐；本表不写化学结论。 |
| **放弃** | 3 多声明主产物 + 1 缺主产物且无近结构 | 本轮不进下一批修复面；不是永久否定，重开需新化学/契约证据。 |
| unknown | 0 | 无 |

### 1.4 与 T-1 豁免档的关系

- T-1 已兑现 5 题：`metrics.json.v1` partial → `metrics.json.v2` strict rank 1；P0-C
  `v2_exemptions` 5 occurrences；全部在 53 外。清单见 §3.5。
- 53 内没有“已兑现”的 T-1 题；16 题是簿记族但 v2 谓词未全过（4 v1_exempt / 60
  not_exempt）。所以本表不会把“已兑现的 5 题”重复算进 53。
- 辅因子类 5 题与 T-1 的关系：它们是 `not_exempt_maintains_partial` 或声明链未闭合，
  不属于 T-1 豁免档；送师姐的是化学必要性，不是 T-1 口径本身。

## 2. 53 行分类表

> 列说明：`p0c形态` = 事件形态分组；`逐事件方向` = 本表逐事件两侧差集；
> `组分计数` = 豁免族n+辅因子n+错侧n+同式n+其他n；`缺节点(近/其他)` = 缺失参考节点数
> （近结构/其他）；`去向` 三值：可修/待裁定/放弃。53/53 均 `not_t1_redeemed`，不再单列。

| # | qid 前缀 | 池 | remap | p0c形态 | 逐事件方向 | 组分类型 | 组分计数 | 缺节点(近/其他) | 去向 | 依据/备注 |
|---:|---|---|---|---|---|---|---|---|---|---|
| 1 | `RXNG_08d3aa8a02eec3c` | nonempty | no_remap | extra | extra | `bookkeeping_exempt` | 豁免族1 | 0/0 | 可修 | 簿记族身份;v2 tier v1_exempt=0/not_exempt=1 |
| 2 | `RXNG_09a6f7180b39254` | empty | no_remap | extra | extra | `bookkeeping_exempt` | 豁免族1 | 0/0 | 可修 | 簿记族身份;v2 tier v1_exempt=0/not_exempt=1;空池 |
| 3 | `RXNG_0a2c91bde7717cf` | nonempty | remap | extra | extra | `bookkeeping_exempt` | 豁免族1 | 0/0 | 可修 | 簿记族身份;v2 tier v1_exempt=0/not_exempt=1 |
| 4 | `RXNG_0ab7c126b56b876` | nonempty | no_remap | extra | extra | `bookkeeping_exempt` | 豁免族1 | 0/0 | 可修 | 簿记族身份;v2 tier v1_exempt=0/not_exempt=1 |
| 5 | `RXNG_445673c6693414a` | nonempty | no_remap | extra | extra | `bookkeeping_exempt` | 豁免族1 | 0/0 | 可修 | 簿记族身份;v2 tier v1_exempt=0/not_exempt=1 |
| 6 | `RXNG_4f47ef5ad741ca6` | nonempty | no_remap | extra | extra | `bookkeeping_exempt` | 豁免族1 | 0/0 | 可修 | 簿记族身份;v2 tier v1_exempt=0/not_exempt=1 |
| 7 | `RXNG_51cb56fdbce6b60` | empty | no_remap | extra | extra | `bookkeeping_exempt` | 豁免族1 | 0/0 | 可修 | 簿记族身份;v2 tier v1_exempt=0/not_exempt=1;空池 |
| 8 | `RXNG_531caa559d3dda2` | empty | no_remap | extra | extra | `bookkeeping_exempt` | 豁免族1 | 0/0 | 可修 | 簿记族身份;v2 tier v1_exempt=0/not_exempt=1;空池 |
| 9 | `RXNG_5727b6273dcf603` | nonempty | no_remap | extra | extra | `bookkeeping_exempt` | 豁免族3 | 0/0 | 可修 | 簿记族身份;v2 tier v1_exempt=1/not_exempt=2 |
| 10 | `RXNG_6d4d3e2fa5ade73` | empty | no_remap | extra | extra | `bookkeeping_exempt` | 豁免族1 | 0/0 | 可修 | 簿记族身份;v2 tier v1_exempt=0/not_exempt=1;空池 |
| 11 | `RXNG_6f0eea09ebe3729` | empty | no_remap | extra | extra | `bookkeeping_exempt` | 豁免族1 | 0/0 | 可修 | 簿记族身份;v2 tier v1_exempt=0/not_exempt=1;空池 |
| 12 | `RXNG_8d9fa8b67a68df3` | nonempty | no_remap | extra | extra | `bookkeeping_exempt` | 豁免族1 | 0/0 | 可修 | 簿记族身份;v2 tier v1_exempt=0/not_exempt=1 |
| 13 | `RXNG_9c383e61351d8b9` | empty | no_remap | extra | extra | `bookkeeping_exempt` | 豁免族1 | 0/0 | 可修 | 簿记族身份;v2 tier v1_exempt=0/not_exempt=1;空池 |
| 14 | `RXNG_adab6b324439580` | empty | no_remap | extra | extra | `bookkeeping_exempt` | 豁免族1 | 0/0 | 可修 | 簿记族身份;v2 tier v1_exempt=0/not_exempt=1;空池 |
| 15 | `RXNG_c01c97cb2e52814` | nonempty | no_remap | extra | extra | `bookkeeping_exempt` | 豁免族1 | 0/0 | 可修 | 簿记族身份;v2 tier v1_exempt=0/not_exempt=1 |
| 16 | `RXNG_f2044d5f4d637b4` | nonempty | no_remap | extra | extra | `bookkeeping_exempt` | 豁免族1 | 0/0 | 可修 | 簿记族身份;v2 tier v1_exempt=0/not_exempt=1 |
| 17 | `RXNG_0eda0ec3a41b2c3` | nonempty | no_remap | extra | extra | `cofactor` | 辅因子1+其他1 | 0/0 | 待裁定 | 辅因子/共底物(化学裁定) |
| 18 | `RXNG_167dfdcc8dd009e` | nonempty | remap | extra | extra | `cofactor` | 豁免族1+辅因子2 | 0/0 | 待裁定 | 辅因子/共底物(化学裁定) |
| 19 | `RXNG_21ed83a680e54ef` | nonempty | no_remap | extra | extra | `cofactor` | 辅因子1+其他1 | 0/0 | 待裁定 | 辅因子/共底物(化学裁定) |
| 20 | `RXNG_45d8d90fa8ccd5c` | nonempty | remap | extra | extra | `cofactor` | 豁免族1+辅因子2 | 0/0 | 待裁定 | 辅因子/共底物(化学裁定) |
| 21 | `RXNG_c2fb10b79767bb7` | nonempty | remap | extra | extra | `cofactor` | 辅因子1+其他1 | 0/0 | 待裁定 | 辅因子/共底物(化学裁定) |
| 22 | `RXNG_2a805c8fc232e6b` | nonempty | remap | missing | missing | `structural_near` | — | 3/0 | 可修 | 缺参考主产物与事件产物同式/同骨架(身份归一候选) |
| 23 | `RXNG_8e87765558aab97` | nonempty | remap | missing | missing | `structural_near` | — | 2/0 | 可修 | 缺参考主产物与事件产物同式/同骨架(身份归一候选) |
| 24 | `RXNG_93d3a3ef9b712f2` | nonempty | remap | missing | mixed_components | `structural_near` | 豁免族3+错侧2+其他2 | 1/1 | 可修 | p0c事件形态=missing;逐事件差集=mixed_components;含参考侧同身份错侧/重复(簿记角色);缺参考主产物与事件产物同式/同骨架(身份归一候选) |
| 25 | `RXNG_96836273fb2c376` | nonempty | remap | mixed | mixed_components | `structural_near` | 辅因子2+其他2 | 1/1 | 可修 | p0c事件形态=mixed;逐事件差集=mixed_components;含次要辅因子/共底物成分(主缺口非辅因子);缺参考主产物与事件产物同式/同骨架(身份归一候选) |
| 26 | `RXNG_b34d5882f63b2bc` | nonempty | no_remap | missing | missing | `structural_near` | — | 2/0 | 可修 | 缺参考主产物与事件产物同式/同骨架(身份归一候选) |
| 27 | `RXNG_d6da5d9aa4780df` | nonempty | remap | missing | mixed_components | `structural_near` | 豁免族3+辅因子1+其他4 | 1/1 | 可修 | p0c事件形态=missing;逐事件差集=mixed_components;含次要辅因子/共底物成分(主缺口非辅因子);缺参考主产物与事件产物同式/同骨架(身份归一候选) |
| 28 | `RXNG_eabc2bf0bfa38d7` | nonempty | no_remap | missing | mixed_components | `structural_near` | 豁免族2+错侧2+其他1 | 1/1 | 可修 | p0c事件形态=missing;逐事件差集=mixed_components;含参考侧同身份错侧/重复(簿记角色);缺参考主产物与事件产物同式/同骨架(身份归一候选) |
| 29 | `RXNG_03ebc970515b44b` | nonempty | no_remap | extra | extra | `other` | 豁免族1+其他1 | 0/0 | 可修 | 未声明副产物(共产物声明/忽略档修复面;不得删真实副产物) |
| 30 | `RXNG_04d8e54db1cf2ee` | nonempty | no_remap | extra | extra | `other` | 其他1 | 0/0 | 可修 | 未声明副产物(共产物声明/忽略档修复面;不得删真实副产物) |
| 31 | `RXNG_0f02d5d2f47173f` | nonempty | remap | extra | extra | `other` | 其他1 | 0/0 | 可修 | 未声明副产物(共产物声明/忽略档修复面;不得删真实副产物) |
| 32 | `RXNG_13141108d9e6fff` | nonempty | remap | extra | extra | `other` | 其他1 | 0/0 | 可修 | 未声明副产物(共产物声明/忽略档修复面;不得删真实副产物) |
| 33 | `RXNG_15a597617bc29ae` | nonempty | remap | extra | extra | `other` | 其他1 | 0/0 | 可修 | 未声明副产物(共产物声明/忽略档修复面;不得删真实副产物) |
| 34 | `RXNG_164844b4b76b8ac` | nonempty | remap | mixed | mixed_components | `other` | 豁免族4+其他2 | 0/2 | 放弃 | p0c事件形态=mixed;逐事件差集=mixed_components;缺主产物且无可接受近结构(放弃) |
| 35 | `RXNG_1692948d4ad5bd7` | nonempty | remap | extra | extra | `other` | 其他1 | 0/0 | 放弃 | 多声明主产物(化学裁定前放弃) |
| 36 | `RXNG_20b83d4f65520d2` | nonempty | remap | extra | extra | `other` | 其他1 | 0/0 | 可修 | 未声明副产物(共产物声明/忽略档修复面;不得删真实副产物) |
| 37 | `RXNG_2579ae3ecc63b26` | nonempty | remap | extra | extra | `other` | 豁免族1+其他1 | 0/0 | 放弃 | 多声明主产物(化学裁定前放弃) |
| 38 | `RXNG_2b9dd28e603c64b` | nonempty | remap | extra | extra | `other` | 其他1 | 0/0 | 可修 | 未声明副产物(共产物声明/忽略档修复面;不得删真实副产物) |
| 39 | `RXNG_32293b693909ff8` | nonempty | remap | extra | extra | `other` | 其他1 | 0/0 | 可修 | 未声明副产物(共产物声明/忽略档修复面;不得删真实副产物) |
| 40 | `RXNG_342929a68971758` | empty | no_remap | extra | extra | `other` | 其他1 | 0/0 | 可修 | 未声明副产物(共产物声明/忽略档修复面;不得删真实副产物);空池 |
| 41 | `RXNG_37e263634a33873` | nonempty | remap | extra | extra | `other` | 其他1 | 0/0 | 可修 | 未声明副产物(共产物声明/忽略档修复面;不得删真实副产物) |
| 42 | `RXNG_654cc41cad1160a` | nonempty | no_remap | extra | extra | `other` | 豁免族1+其他1 | 0/0 | 可修 | 未声明副产物(共产物声明/忽略档修复面;不得删真实副产物) |
| 43 | `RXNG_66271eac90b08ad` | nonempty | remap | extra | extra | `other` | 豁免族1+其他1 | 0/0 | 可修 | 未声明副产物(共产物声明/忽略档修复面;不得删真实副产物) |
| 44 | `RXNG_7fab823b3a4e8b6` | empty | no_remap | extra | extra | `other` | 其他1 | 0/0 | 可修 | 未声明副产物(共产物声明/忽略档修复面;不得删真实副产物);空池 |
| 45 | `RXNG_a275c5200849ef8` | nonempty | remap | extra | extra | `other` | 其他1 | 0/0 | 可修 | 未声明副产物(共产物声明/忽略档修复面;不得删真实副产物) |
| 46 | `RXNG_a69f41ef39c4a70` | nonempty | remap | extra | extra | `other` | 其他1 | 0/0 | 可修 | 未声明副产物(共产物声明/忽略档修复面;不得删真实副产物) |
| 47 | `RXNG_b6e5b278012c2fc` | nonempty | remap | extra | extra | `other` | 其他1 | 0/0 | 可修 | 未声明副产物(共产物声明/忽略档修复面;不得删真实副产物) |
| 48 | `RXNG_c8836aa26b6039a` | nonempty | remap | extra | extra | `other` | 其他1 | 0/0 | 可修 | 未声明副产物(共产物声明/忽略档修复面;不得删真实副产物) |
| 49 | `RXNG_c9ee5eb0c5f911d` | empty | no_remap | extra | extra | `other` | 其他2 | 0/0 | 可修 | 未声明副产物(共产物声明/忽略档修复面;不得删真实副产物);空池 |
| 50 | `RXNG_cee619845b65292` | empty | no_remap | extra | extra | `other` | 其他1 | 0/0 | 可修 | 未声明副产物(共产物声明/忽略档修复面;不得删真实副产物);空池 |
| 51 | `RXNG_ef18f4fd48f1b2c` | empty | no_remap | extra | extra | `other` | 其他1 | 0/0 | 可修 | 未声明副产物(共产物声明/忽略档修复面;不得删真实副产物);空池 |
| 52 | `RXNG_f30855a0ac0fa91` | nonempty | remap | extra | extra | `other` | 其他1 | 0/0 | 放弃 | 多声明主产物(化学裁定前放弃) |
| 53 | `RXNG_fc90885a446192f` | nonempty | no_remap | extra | extra | `other` | 豁免族1+其他1 | 0/0 | 可修 | 未声明副产物(共产物声明/忽略档修复面;不得删真实副产物) |

## 3. 汇总

### 3.1 组分类型 × 去向（已证=53 行互斥计数；池=53）

| 组分类型 | 可修 | 待裁定 | 放弃 | 合计 |
|---|---:|---:|---:|---:|
| `bookkeeping_exempt` | 16 | 0 | 0 | **16** |
| `cofactor` | 0 | 5 | 0 | **5** |
| `structural_near` | 7 | 0 | 0 | **7** |
| `other` | 21 | 0 | 4 | **25** |
| `unknown` | 0 | 0 | 0 | **0** |
| **合计** | **44** | **5** | **4** | **53** |

### 3.2 池 / remap 切面（已证=本地批件计数；不是转化率）

| 切面 | 题数 | bookkeeping | cofactor | structural_near | other |
|---|---:|---:|---:|---:|---:|
| 非空池 | 41 | 9 | 5 | 7 | 20 |
| 空池 | 12 | 7 | 0 | 0 | 5 |
| remap | 25 | 1 | 3 | 5 | 16 |
| 非 remap | 28 | 15 | 2 | 2 | 9 |

- 12 个空池题仍可有 partial（模型 novel 事件 + 参考匹配）；**空池是供给面解释项，
  不是本表缺口分类的判据**。空池里 7 簿记 + 5 其他；没有辅因子/结构近。

### 3.3 P0-C 形态 × 本表类型（已证=53 行计数）

| P0-C 形态 | 题数 | bookkeeping | cofactor | structural_near | other |
|---|---:|---:|---:|---:|---:|
| extra（只 superset） | 45 | 16 | 5 | 0 | 24 |
| missing（只 partial_subset） | 6 | 0 | 0 | 6 | 0 |
| mixed（两形态并存） | 2 | 0 | 0 | 1 | 1 |

**注意：** P0-C 的 6 个 `missing` 在逐事件差集里并不都是“只缺不多”；本表另有 3 个题
（93d3、d6da、eabc）P0-C 标 `missing`，逐事件却是 `mixed_components`。因此 P0-C 的
45/6/2 不能直接当“45 extra-only / 6 missing-only / 2 混合”使用。

### 3.4 组分总量与 v2 tier（已证=逐事件/逐实例计数；池=53）

| 项 | 数量 | 读法 |
|---|---:|---|
| 豁免族 extra 成分 | 37 | H₂O/H⁺/Pi/PPi 身份族；不全是 v1_exempt |
| 辅因子/共底物 extra 成分 | 10 | NAD(P)/NADH 对、O₂/H₂O₂ 对，另有小题的次要共底物 |
| 同身份错侧/重复（簿记角色） | 4 | 93d3、eabc 两题；按 structural_near 处理 |
| 同式 structural extra | 0 | 没有“多出来的成分与参考参与物同式”的题 |
| 其他 extra 成分 | 39 | 未声明副产物/多声明主产物等 |
| 缺失参考节点 | 17 | 近结构 11 / 其他 6 / unknown 0 |
| v2 豁免 tier | 4 v1_exempt / 60 not_exempt | 53 内逐实例；不是 5 题 T-1 的重复计数 |

### 3.5 T-1 已兑现 5 题（53 外；已证=v1/v2 状态翻转）

| qid 前缀 | v1 状态 | v2 状态 | v2 rank | 关系 |
|---|---|---|---|---:|---|
| `RXNG_8f29c4de07a9e9a` | partial | strict | 1 | H₂O 豁免兑现；不在 53 |
| `RXNG_5e9b5672eb14525` | partial | strict | 1 | 同上 |
| `RXNG_7652a03dff72dc7` | partial | strict | 1 | 同上 |
| `RXNG_3b8991e91ab5f4c` | partial | strict | 1 | 同上 |
| `RXNG_8dce8a33d8bd390` | partial | strict | 1 | 同上 |

## 4. 送师姐 / 化学判断清单

### 4.1 必须送：辅因子/共底物 5 题（待裁定）

| qid 前缀 | 辅因子成分 | 备注 |
|---|---|---|
| `RXNG_0eda0ec3a41b2c3` | 非豁免 cosubstrate ×1 + coproduct ×1 | O₂/H₂O₂ 型氧化还原对；化学必要性送师姐 |
| `RXNG_21ed83a680e54ef` | 非豁免 cosubstrate ×1 + coproduct ×1 | 同上 |
| `RXNG_c2fb10b79767bb7` | 非豁免 cosubstrate ×1 + coproduct ×1 | 同上 |
| `RXNG_167dfdcc8dd009e` | NAD(P)/NADH 型 cosubstrate ×2 + H⁺ ×1 | 也是 16 退化题之一（strict→partial）；化学必要性送师姐 |
| `RXNG_45d8d90fa8ccd5c` | NAD(P)/NADH 型 cosubstrate ×2 + H⁺ ×1 | 同上 |

### 4.2 次要辅因子成分（不改变主去向）

- `RXNG_96836273fb2c376`（structural_near）：含 2 个小分子 cosubstrate 成分，主缺口是
  缺失参考主产物的近结构；去向仍为可修。
- `RXNG_d6da5d9aa4780df`（structural_near）：含 1 个 cosubstrate 成分，主缺口同上；
  去向仍为可修。
- 这两题的辅因子成分若下一批要动，仍需化学确认；本表不把它们升级为“待裁定”。

### 4.3 真实副产物（21 题未声明副产物 + 3 题多声明主产物 + 1 题缺主产物）

- 21 题未声明副产物：去向“可修（共产物声明/忽略档修复面）”，但**不得删真实副产物**；
  规则落地前仍需化学/契约裁定。
- 3 题多声明主产物（1692948d、2579ae3e、f30855a0）：本轮“放弃”，不进修复面。
- 1 题缺主产物且无近结构（164844b4）：本轮“放弃”。

## 5. Unknown / 限制（不估算）

| # | unknown / 限制 | 影响 | 缺什么 |
|---|---|---|---|
| 1 | 候选级/事件级金标归因 | 不能证明哪个候选应命中或为何丢分 | 逐事件金标匹配、逐候选 strict 判定明细 |
| 2 | 转化题数 | 不能把“可修”写成收益；53 是池，+53 是上限 | 下一批单变量实验/候选级证据 |
| 3 | 真实副产物的化学必要性 | 21 题未声明副产物不能凭元数据判“可忽略” | 化学评审/判据裁定 |
| 4 | 缺失主产物的真实可修性 | 7 题 structural_near 只证“同式/同骨架”，不证“同一化学个体” | 化学语义核对、完整计分链、判据裁定 |
| 5 | 空池 12 题的供给面 | 缺口分类独立于池，但空池会限制下一批修复面 | 空池逐题供给诊断（本表不展开） |
| 6 | 单批、已见题 | 298 post-hoc，不能外推 | 新题/重复批 |
| 7 | P0-C 形态标签 | 45/6/2 不是 missing-only 证明 | 本表已用逐事件差集替代；3 题由 missing 改判 mixed_components |

**本表没有把“可修”写成“可兑现”，也没有把“放弃”写成“永久不可修”。** 所有“可修”
都只是下一批修复面候选；所有“待裁定”都没有在本表做化学结论。

## 6. 证据与复现

| 件 | 路径 |
|---|---|
| 本报告 | `/Volumes/CC/Enzyme_Agent/dependingv43/docs/T_H_TEACHER_LEVER3_PARTIAL_TABLE_2026-10-21.md` |
| 证据目录 | `/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/t_h_lever3_partial_2026-10-21/` |
| 机读 53 行 | 同目录 `lever3_partial_table.json` |
| 复现脚本 | 同目录 `lever3_partial_classify.py` |
| provenance | 同目录 `provenance.json`（合并视图 provenance，含本报告主视图命令与输入哈希） |
| 人读摘要 | 同目录 `summary.txt`（合并视图） |
| 哈希 | 同目录 `SHA256SUMS`（覆盖 `lever3_partial_classify.py` 与 `lever3_partial_table.json`） |

复现命令（仓库根目录；staged 输入同 P0-C，零模型）：

```bash
cd /Volumes/CC/Enzyme_Agent/dependingv43
/Users/cc/miniconda3/envs/depending43/bin/python \
  docs/review_evidence/t_h_lever3_partial_2026-10-21/lever3_partial_classify.py \
  --batch-root /tmp/t_h_p0_r2/scoring \
  --runs-root /tmp/t_h_p0_r2/runs \
  --out-dir docs/review_evidence/t_h_lever3_partial_2026-10-21
```

输入哈希、实际 HEAD（`11aeeafded1b41185f24de49767933709aad49db`）、Python/RDKit 版本
见 `provenance.json`。证据目录含两份视图：本报告的 `lever3_partial_table.json`
（老师四类主视图）与 `partial53_gap_table.json`（元数据角色交叉视图）；合并后的
teacher-facing 表 `table_53.md` 以本报告 JSON 为主视图。两视图只差 7 题：
缺主产物且有同式/同骨架证据的 7 题，由“放弃”改判 `structural_near`（可修面）；
剩 1 题缺主产物且无近结构，维持“放弃”。

## 7. 红线合规

| 红线 | 状态 | 证据 |
|---|---|---|
| 零模型调用 | 合规 | 仅本地读取已封存 run 元数据/候选事件；无 API/模型调用 |
| 零新批次 | 合规 | 未发车、未重跑；只读 `/tmp/t_h_p0_r2` staged 输入与本地 metrics |
| 不读金标/reference_graphs 内容 | 合规 | reference graph 只在冻结 evaluator 内消费；脚本不读 `structure_smiles`/`state_identity` 正文 |
| 不输出题面/SMILES/结构正文 | 合规 | 候选 state 的分子式/骨架只在进程内比较；表内只有 qid、角色、计数、类别；JSON 不含 SMILES/分子式 |
| 不改封存批/主树 | 合规 | 只新增 docs 与证据目录；未写 reports/ppv1_s5b 封存目录 |
| 不 push | 合规 | 无 git push |
| 数字带池/上限/已证 | 合规 | 结论与各表均带“池=53 / 池=298 / 上限 / 已证”标签 |

**一句话：** 53 题 partial 的缺口分类已闭合；可修 44、待裁定 5、放弃 4、unknown 0；
5 题 T-1 已兑现且全在 53 外；本表不承诺任何转化题数。
