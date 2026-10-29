# T-H P3 O0：口径对账与指标字典更正（2026-10-23）

> **题域标签：[298 域] = RHEA 通用酶学 / 已见题（post-hoc）。**
> 本文所有数值只在该题域成立；与 dev（B1 环境路径中间步骤）双向不外推。
>
> **性质：只读文档对账。** 零模型调用、零付费、零代码改动、零金标/题面读取；
> 不读封存逐题 run、不读 `reference_graphs`/`env`/key；不连 HPC；不 push；零化学串。
> 只新增本文件与证据目录 `docs/review_evidence/p3_o0_metric_2026-10-23/`，不改任何既有文档。
> 文件名日期 2026-10-23 为任务书指定；实际落盘 2026-10-26。
>
> 机读字典：`docs/review_evidence/p3_o0_metric_2026-10-23/metrics.json`（51 条指标，
> 含名称/值/单位/精确定义/出处/关系/证据级；哈希见同目录 `SHA256SUMS`）。

## 0. 结论先行

| # | 关键更正 | 错写法（出现过的） | 正确口径（最终值） |
|---|---|---|---|
| 1 | **992 ≠ F3** | "F3 wildcard 预门跳过 992"、"F3 992 条" | F3 wildcard = **178 条候选行 / 52 题(D1)**；992 = `analog_pregate_skipped` **计数器** = 178（F3）+ 407（supply 分支 F5 absent）+ 407（no_supply 分支 F5 absent）；与 F5 reject 864 **重叠 814，禁止相加** |
| 2 | **193 不是 "EAWAG recorded 资产缺席"** | "recorded 资产缺席 193 题"、"recorded 没资产" | 193 = **无已调度 `rec-` 前缀 spec 的题数**；`rec-` 同时由 EAWAG recorded 与 corpus 直通产生；内部 D1 分层 25/71/8/89 与 25/166/2 |
| 3 | **134 不是 remap 欠账** | "134 条有 remap 机会但没试" | 134 = 已调度 analog spec 中**未触发 `transform_no_change` 的补集**（无 `template_remap` 键）；234/242/151 是三个不同分母（已调度 spec / P2 spec 面 / P2 题面），不可互换 |
| 4 | **统一漏斗口径** | 2366 与 1548 混用；864 两个名字混写 | F5 **checked 3398 / deferred 1548 / skipped 864**；`no_alignment` **1585 = 864 + 543 + 178**（唯一互斥可加拆分）；search deferred **2366 = 2358 + 8**（与 F5 defer 1548 单位/对象不同，禁止互换或相加） |

**一句话：** 1585 里只有 864 + 543 + 178 能相加；992 是横跨两类的诊断计数器，碰到任何
候选行数都必须停手；193、134 的名字必须按定义写，不许按直觉写；2366 和 1548 是两回事。

本轮新发现并一并更正的一处旧标签：`[P0D]` 的 `by_channel.analog = 1585` 说明 1585 条
`no_alignment` **全部是 analog 通道**；P0 摘要/决议包把 178 写成"非 F5 适用（recorded/corpus 等）"
是错误标签——178 全部是 analog wildcard 行（`f5=not_evaluated`）。同理 `[P0D]` 的 `f3_note`
（"never labelled no_alignment"）与其自身 `by_f5` 字段及代码矛盾：wildcard 行确实以
`reason="no_alignment"` 落行（`s5b_builder.py:1507-1509`），以字段和代码为准。

## 1. 证据级与 provenance

| 级别 | 含义 | 本轮状态 |
|---|---|---|
| D0 | 官方冻结 SHA256 证据（`[P0D]`）直接判定 | 本轮已对冻结 JSON **逐项复验**（§3 等式全部闭合） |
| D1 | P3 报告期用 `[WL]`（`/tmp/th_pool_diag.json`）逐行重算 | **该 /tmp 副本现已不存在**；本轮未复算，引用须写 "D1, P3 报告 §2–§4"；再证需新的只读白名单投影 |
| derived | 由 D0 字段经闭合等式机械推出 | 如 F5 pass 986、重叠 814 |

- 冻结证据：`docs/review_evidence/t_h_p0_2026-10-20/p0d_supply_funnel.json`（下称 `[P0D]`，行号按该 JSON 文件行）。
- 代码行号在当前 HEAD `966bc5664a7daa30f24860d2b5594a9dddc6eee2` **逐一复核一致**
  （P3 报告期 HEAD 为 `11aeeafd…`；计数点行号未漂移）。
- 源码计数点核对结果：
  - `analog_pregate_skipped` 三处 +1：`src/pathway_v43/pollutant/s5b_builder.py:1514-1516`（F3 wildcard）、
    `:1529-1531`（supply 分支 F5 absent）、`:1602-1604`（no_supply 分支 F5 absent）；
  - F3 wildcard 分支本体：`s5b_builder.py:1499-1517`（同时加 `analog_cosub_supply_wildcard_blocked`）；
    wildcard 判据 `_cosub_has_wildcard_atom` 定义 `:571`，`wildcard_blocked` 返回 `:710`；
  - direct_raw 分支 F5 absent（`:1454-1462`）**不加**该计数器（50 条推断的代码依据）；
  - F5 门三计数：`s5b_builder.py:1352-1365`（checked/skipped/deferred）；
  - tnc 唯一触发：`src/pathway_v43/pollutant/s5b_compiler.py:1466-1470`；编译层 `no_alignment`：`:1591-1598`；
  - `rec-` 前缀：`src/pathway_v43/pollutant/recorded_source.py:3044`（`key_prefix="rec"`）。

## 2. 四组更正说明

### 2.1 更正一：992 不是 F3，864 + 992 会重复计数

`analog_pregate_skipped` 在**三个**分支各按被拒候选行 +1（`s5b_builder.py:1514-1516, 1529-1531, 1602-1604`）：

1. F3 wildcard 分支：`analog_cosub_supply` 返回 `wildcard_blocked`，不供给、不编译，
   行记 `reason=no_alignment`、`f5=not_evaluated`（178 条）；
2. supply 分支 F5 `absent`（407 条，D1）；
3. no_supply 分支 F5 `absent`（407 条，D1）。

direct_raw 分支的 F5 `absent`（50 条）**不加**计数器（`:1454-1462`）。闭合：

- 992 = 178 + 407 + 407；
- 864 = 407 + 407 + 50；
- **重叠(992, 864) = 814** → `864 + 992` 会把 814 数两遍；
- 992 覆盖 198 题 / 1094 事件（D1）。

**读法：** F3 只有 178 条候选行（52 题 / 277 事件，D1）；992 横跨 F3 与 F5-absent 两类，
不标识任何单一候选类，只能以计数器身份引用。此更正不改变 P0-D 的候选成员或判分，只改口径标签。

### 2.2 更正二：193 不是 "EAWAG recorded 资产缺席"

定义（`[P0D] no_recorded_anchor_reconciliation.definition`）：**题没有已调度 `expand_hypothesis`
action、其 `logical_proposal_id` 以 `rec-` 开头**。而 `rec-` 同时由 EAWAG recorded 与 corpus
直通两条路径产生（`recorded_source.py:3044` `key_prefix="rec"`）。因此：

- 193 = 无已调度 recorded/**corpus 直通** spec 的题数；
- `recorded_present_scheduled=105`（有 `rec-` spec，**含 corpus**）与
  `recorded_present_any_pool_row=182`（有 EAWAG channel 行，**仅 EAWAG**）分母定义不同，
  **105 − 182 之类的"转化率"算法无效**；
- `recorded_zero_pool_questions=116`（无 EAWAG 行）= 96（193 内）+ 20（193 外）（D1），
  **116 不是 193 的子集**；
- 193 内部（D1，`[WL]` 重算）：通道存在性 25/71/8/89（无行/仅 corpus/仅 EAWAG/两者都有）；
  compiled 状态 25/166/2（无行 / 有行无 compiled / 有 compiled 未调度）。
  涉"资产"的表述必须拆到这三层，不许整体说"recorded 缺席"。

### 2.3 更正三：134 不是 remap 欠账；234/242/151 三个分母

`complete_template_mapping` 只在 pre-flight 提取抛 `transform_no_change`（tnc）时触发，
其它拒因零触碰（`s5b_compiler.py:1466-1470`）。所以：

- `template_remap` 键只会在 tnc 触发后出现；无键 = **未触发 tnc**；
- 134 是已调度 analog spec 中"未触发 tnc"的补集，**不是 134 个可修复缺口**；
- remap 规则只补 map 号、不删原子；`[P0D] remap.removed_atom_ops = 0` 计数佐证。

**三个 remap 数字分母不同，禁止互换：**

| 值 | 分母 | 单位 |
|---:|---|---|
| 234 | 已调度 analog spec（applied 且新增 map>0） | scheduled_spec |
| 242 | P2 spec 面（specs_total=531） | spec_p2_face |
| 151 | P2 题面（有 remap 的题） | question（是 234 的题数上界，非精确值） |

### 2.4 更正四：统一 F5 / no_alignment / deferred 口径

| 口径 | 统一写法 | 关系 |
|---|---|---|
| F5 三件套 | checked **3398** / deferred **1548** / skipped **864** | 3398 = 986 + 1548 + 864；skipped ≡ `f5_pregate_reject` ≡ `analog_center_admission_skipped`，同一物三个名字 |
| `no_alignment` | **1585 = 864 + 543 + 178** | 唯一互斥可加拆分；全部 analog |
| F5 pass | **986**（derived = 3398 − 1548 − 864） | 去向（D1）：134 独特 compiled + 183 merged + 669 rejected |
| search deferred | **2366 = 2358（depth_limit）+ 8（alternatives_budget）** | 单位是检索/展开 action 的延迟项；与 F5 defer 1548 **单位不同、对象不同**，禁止互换或相加 |

## 3. 指标字典（51 条）

> 单位词表：question=题；candidate_row=manifest 候选行（池构建逐候选尝试行，不是已调度
> spec 也不是事件）；scheduled_spec=已调度 expand spec；event=已提交事件；
> search_action_deferred_entry=检索/展开延迟项；counter=诊断计数器；map=补映射 map 号；
> op=remap 操作；report=production 失败报告；spec_p2_face=P2 spec 面（specs_total=531 分母）。
> 证据级：D0=冻结 JSON 直接判定（本轮复验）；D1=P3 报告期 `[WL]` 重算（副本已失，未再证）；
> derived=闭合等式推出。完整机读版见 `metrics.json`。

### 3.1 分母（5 条）

| 名称 | 值 | 单位 | 定义 | 出处 | 关系 |
|---|---:|---|---|---|---|
| `questions_total` | 298 | question | 全批题数，298 域母分母 | `[P0D] denominators.questions` | 所有题级分母的母分母 |
| `scheduled_specs_total` | 1601 | scheduled_spec | 已调度 expand spec 总数 | `[P0D] denominators.scheduled_specs` | remap 234/134 的分母域 |
| `submitted_events_total` | 1586 | event | 已提交事件数 | `[P0D] denominators.submitted_events` | 被拒候选直接事件=0；事件是题级上下文分母 |
| `candidate_rows_total` | 5319 | candidate_row | manifest 候选行总数 | `[P0D] denominators.candidate_rows_in_manifest` | = 531+4311+472+5 = 3576+1421+322 = Σ19 个 reason 值 |
| `search_deferred_total` | 2366 | search_action_deferred_entry | 检索/展开 deferred entries 总数 | `[P0D] denominators.deferred_actions_total` | = 2358+8；**不是 F5 defer 1548**；与任何候选行数不可相加 |

### 3.2 outcome（4 条，D0，均为 5319 的互斥组件）

| 名称 | 值 | 单位 | 定义 | 出处 | 关系 |
|---|---:|---|---|---|---|
| `outcome_compiled` | 531 | candidate_row | 编译成功 | `[P0D] candidate_outcomes.compiled` | 组件 |
| `outcome_compile_rejected` | 4311 | candidate_row | 编译拒绝 | `[P0D] candidate_outcomes.compile_rejected` | 组件；1585 是其拒因子集 |
| `outcome_merged_into` | 472 | candidate_row | 编译后并池 | `[P0D] candidate_outcomes.merged_into` | 组件 |
| `outcome_pool_truncated` | 5 | candidate_row | 池宽截断 | `[P0D] candidate_outcomes.pool_truncated` | 组件；不能当 partial 主因 |

### 3.3 通道（3 条，D0，互斥，合计 5319）

| 名称 | 值 | 单位 | 定义 | 出处 | 关系 |
|---|---:|---|---|---|---|
| `channel_analog_rows` | 3576 | candidate_row | analog 通道行 | `[P0D] candidate_channels.analog` | = 3398 + 178 |
| `channel_corpus_rows` | 1421 | candidate_row | corpus 通道行 | `[P0D] candidate_channels.corpus` | D1: 51 compiled+1355 rejected+13 merged+2 truncated |
| `channel_recorded_rows` | 322 | candidate_row | EAWAG recorded 通道行（channel=recorded） | `[P0D] candidate_channels.recorded` | D1: 104+214+4；**≠ rec- 前缀 spec 全集**（后者含 corpus 直通） |

### 3.4 no_alignment 家族（6 条）

| 名称 | 值 | 单位 | 定义 | 出处 | 关系 |
|---|---:|---|---|---|---|
| `no_alignment_total` | 1585 | candidate_row | reason=no_alignment 候选行；全批最大拒因 | `[P0D] no_alignment_split.candidates_total; candidate_reasons_top.no_alignment` | = 864+543+178（唯一互斥可加拆分）；全部 analog；227 题/1268 事件(D1)；不含 992 |
| `f5_pregate_reject` | 864 | candidate_row | F5 probe=absent 预编译短路；reason=no_alignment | `[P0D] by_f5.reject / f5_pregate_reject; CODE-B:1352-1365,1454-1462,1523-1531,1595-1604` | 194 题/1077 事件(D1)；= 407+407+50(D1/推断)；与 992 重叠 814；≡ f5_skipped_total |
| `compiler_after_f5_defer` | 543 | candidate_row | F5 defer 发编译后，编译层中心枚举零命中 | `[P0D] compiler_after_f5_defer; CODE-C:1591-1598` | 是 1548 的子集(35.1%)；164 题/920 事件(D1)；536 raw+7 supplied(D1) |
| `f3_wildcard_rows` | 178 | candidate_row | F3 wildcard_blocked：袋含未定义 dummy 原子，不供给不编译；f5=not_evaluated | `[P0D] by_f5.not_evaluated; CODE-B:1499-1517,571,710` | 52 题/277 事件(D1)；在 1585 内、也在 992 内；**≠ 992**；全部 analog |
| `analog_pregate_skipped` | 992 | **counter** | 三分支各按被拒行 +1：F3(178)+supply F5 absent(407)+no_supply F5 absent(407)；direct(50) 不加 | `[P0D] f3_pregate_skipped_total; CODE-B:1514-1516,1529-1531,1602-1604` | 覆盖 198 题/1094 事件(D1)；**与 864 重叠 814；禁止与任何候选行数相加；禁止当 F3 引用** |
| `overlap_pregate_with_f5_reject` | 814 | candidate_row | 992 ∩ 864 = supply 407 + no_supply 407 | derived（闭合+分支代码） | 864 = 814 + 50；992 = 178 + 814；是"864+992 禁止相加"的原因 |

### 3.5 F5 门内部（4 条）

| 名称 | 值 | 单位 | 定义 | 出处 | 关系 |
|---|---:|---|---|---|---|
| `f5_checked_total` | 3398 | candidate_row | F5 helper 实际调用行数 | `[P0D] f5_checked_total; CODE-B:1354-1356` | = 986+1548+864；3398+178 = 3576 |
| `f5_deferred_total` | 1548 | candidate_row | F5 probe=defer（变换异常/空中心/截断/底物不可解析），照常发编译 | `[P0D] f5_deferred_total; CODE-B:1361-1364` | **≠ search deferred 2366**；543 ⊂ 1548；D1 去向 242 compiled+272 merged+3 truncated+1031 rejected |
| `f5_skipped_total` | 864 | candidate_row | `analog_center_admission_skipped` = F5 absent 行数 | `[P0D] f5_skipped_total; CODE-B:1357-1360` | ≡ f5_pregate_reject；**与 F3 178 不是同一回事** |
| `f5_pass_derived` | 986 | candidate_row | F5 probe=present 行数 | derived = 3398−1548−864 | D1 去向：134 独特 compiled+183 merged+669 rejected；pass 不是通行证 |

### 3.6 search deferred（2 条，D0）

| 名称 | 值 | 单位 | 定义 | 出处 | 关系 |
|---|---:|---|---|---|---|
| `deferred_depth_limit` | 2358 | search_action_deferred_entry | retrieve / coproduct_deferred 深度截断 | `[P0D] deferred_by_reason.depth_limit; by_action_kind.retrieve` | 2366 的组件 |
| `deferred_alternatives_budget` | 8 | search_action_deferred_entry | expand / alternative_reaction_deferred 预算截断 | `[P0D] deferred_by_reason.alternatives_budget; by_action_kind.expand_hypothesis` | 2366 的组件 |

### 3.7 remap 家族（11 条）

| 名称 | 值 | 单位 | 定义 | 出处 | 关系 |
|---|---:|---|---|---|---|
| `remap_applied_scheduled` | 234 | scheduled_spec | 已调度 analog spec：applied 且新增 map>0 | `[P0D] remap.added_specs_with_new_maps` | **≠ 242 ≠ 151**，分母各异 |
| `remap_new_maps_total` | 728 | map | 补映射新增 map 号总数 | `[P0D] remap.n_new_maps_total` | 0 removed、0 failed 伴随 |
| `remap_applied_zero_new` | 0 | scheduled_spec | applied 但零新 map | `[P0D] remap.applied_zero_new_maps` | — |
| `remap_removed_atom_ops` | 0 | op | remove_atom 操作数（规则只补 map 号） | `[P0D] remap.removed_atom_ops` | 否定"remap 删原子致丢分"；"映射偏移"仍未证 |
| `remap_failed_specs` | 0 | scheduled_spec | remap 失败 spec | `[P0D] remap.failed_specs` | — |
| `remap_not_attempted_analog` | 134 | scheduled_spec | 无 template_remap 键 = 未触发 tnc 的补集 | `[P0D] remap.not_attempted_analog_specs; CODE-C:1466-1470` | **不是欠账**；题/事件分母 unknown；与 234 键有无互斥 |
| `p2_remap_applied_spec_face` | 242 | spec_p2_face | P2 spec 面 remap applied | `[P0D] remap.p2_spec_level.remap_applied` | 与 234 分母不同不可互换 |
| `p2_questions_remap` | 151 | question | P2 题面有 remap 的题 | `[P0D] remap.p2_spec_level.questions_remap` | 234 的题数上界，非精确值 |
| `p2_specs_total` | 531 | spec_p2_face | P2 spec 面总数 | `[P0D] remap.p2_spec_level.specs_total` | 242/205/78 的分母 |
| `p2_add_atom_ge1` | 205 | spec_p2_face | P2 面 add_atom≥1 | `[P0D] remap.p2_spec_level.add_atom_ge1` | 分母 531 |
| `p2_add_atom_ge2` | 78 | spec_p2_face | P2 面 add_atom≥2 | `[P0D] remap.p2_spec_level.add_atom_ge2` | 分母 531 |

### 3.8 recorded 家族（6 条）

| 名称 | 值 | 单位 | 定义 | 出处 | 关系 |
|---|---:|---|---|---|---|
| `no_scheduled_rec_prefix_questions` | 193 | question | **无已调度 rec- 前缀 spec 的题数**；rec- 含 EAWAG recorded 与 corpus 直通 | `[P0D] no_recorded; no_recorded_anchor_reconciliation.definition; CODE-R:3044` | **≠ "EAWAG recorded 资产缺席"**；D1 内部 25/71/8/89 与 25/166/2；与 F5 交 121、compiler 98、F3 34(D1) |
| `recorded_present_scheduled` | 105 | question | 有已调度 rec- spec 的题（**含 corpus**） | `[P0D] recorded_present_scheduled` | 与 182 **不可相减算转化率** |
| `recorded_present_any_pool_row` | 182 | question | 有 EAWAG recorded 候选行（channel=recorded）的题 | `[P0D] recorded_present_any_pool_row; recorded_manifest_any_nonzero` | 仅 EAWAG；否定"recorded 没资产"的全局读法 |
| `recorded_zero_pool_questions` | 116 | question | 无 EAWAG recorded 行的题 | `[P0D] recorded_zero_pool_questions` | = 96(193 内)+20(193 外)(D1)；**不是 193 的子集**；是 25 的超集 |
| `recorded_manifest_strict_nonzero` | 147 | question | manifest EAWAG recorded 严格非零题 | `[P0D] recorded_manifest_strict_nonzero` | 背景计数 |
| `chain14_anchor_no_recorded` | 207 | question | chain14 A/B 探针锚点；**跨批** | `[P0D] no_recorded_anchor_reconciliation.task_anchor` | 207−193=14 差集 unknown；**不是 T-H r2 不变量** |

### 3.9 执行失败（4 条，D0）

| 名称 | 值 | 单位 | 定义 | 出处 | 关系 |
|---|---:|---|---|---|---|
| `execution_failed_candidates` | 35 | candidate_row | reason=execution_failed 候选行 | `[P0D] candidate_reasons_top.execution_failed` | 与 21 题、与 production 15/12 分母不同 |
| `execution_failed_qids` | 21 | question | 有 execution_failed 候选的题 | `[P0D] execution_failed_candidate_qids` | 35 行 / 21 题 |
| `production_method_failed_reports` | 15 | report | production method_failed 报告条数 | `[P0D] production_method_failed_reports` | 15 报告 ≠ 12 题 |
| `production_method_failed_qids` | 12 | question | production method_failed 涉及题 | `[P0D] production_method_failed_qids` | 与候选级 35/21 分母不同 |

### 3.10 非 no_alignment 的大拒因箱（6 条，D0）

> 19 个 reason 值（含空 1008）合计 = 5319，是候选行的**单拒因穷尽分箱**（本轮复验闭合）。
> 跨箱相加只在"5319 行按单拒因分箱"口径下合法；不得解读为"同批可修复总量"
> （同码多义，修复语义各自独立，见 P3 报告 §6 第 4 行）。

| 名称 | 值 | 单位 | 定义 | 出处 | 关系 |
|---|---:|---|---|---|---|
| `reason_cosubstrate_bonded_contribution_unsupported` | 972 | candidate_row | 共底物键合贡献不支持；全部 corpus(D1) | `[P0D] candidate_reasons_top` | > 543；不可因 no_alignment 更大而忽略 |
| `reason_mapping_enumeration_truncated` | 260 | candidate_row | 映射枚举截断 | `[P0D] candidate_reasons_top` | L2 审计另见题级信号 12 题/22 条 |
| `reason_stereo_edit_unsupported` | 255 | candidate_row | 立体编辑不支持 | `[P0D] candidate_reasons_top` | 与 charge 253 同码族，修一不修另一 |
| `reason_charge_edit_unsupported` | 253 | candidate_row | 电荷编辑不支持 | `[P0D] candidate_reasons_top` | 同上 |
| `reason_ambiguous_alignment` | 242 | candidate_row | 对齐歧义 | `[P0D] candidate_reasons_top` | **与 P2 面 242 数值巧合、毫无关联，禁止混写** |
| `reason_transform_no_change` | 231 | candidate_row | 变换无净变化（remap 触发面） | `[P0D] candidate_reasons_top; CODE-C:1466-1470` | 与 134（未触发补集）互斥；与 234/242 不同物 |

## 4. 闭合等式（本轮复核）

**D0（本轮对冻结 JSON 逐项机械复验，24 项检查全过）：**

```text
5319 = 531 + 4311 + 472 + 5                      （outcome 互斥拆分）
5319 = 3576 + 1421 + 322                          （通道互斥拆分）
5319 = Σ19 个 reason 直方图值（含空 1008）          （单拒因穷尽分箱）
1585 = 864 + 543 + 178                            （no_alignment 唯一互斥可加拆分）
by_channel.analog = 1585                          （no_alignment 全部 analog）
3398 = 986 + 1548 + 864                           （F5 checked 拆分；986 为 derived）
3576 = 3398 + 178                                 （analog = F5 checked + F3）
2366 = 2358 + 8                                   （deferred；by_reason/by_type/by_action_kind 三投影一致）
992  = 178 + 407 + 407                            （计数器构成闭合；407/407 为 D1）
864  = 407 + 407 + 50                             （50 = direct_raw，代码+计数闭合推断）
overlap(992, 864) = 814 = 407 + 407
no_recorded = 193；difference −14 = 193 − 207     （锚点对账自洽）
```

**D1（P3 报告期 `[WL]` 重算；副本已失，本轮未复算，引用须注明）：**

```text
193 = 25 + 71 + 8 + 89        （通道存在性）      193 = 25 + 166 + 2   （compiled 状态）
116 = 96 + 20                 （EAWAG zero pool 的 193 内外拆分）
322 = 104 + 214 + 4；1421 = 51 + 1355 + 13 + 2
题集重叠：F5∩compiler=135、F5∩F3=45、compiler∩F3=26、三交集=23、并集=227；
         193∩F5=121、193∩compiler=98、193∩F3=34
```

**正控/负控：** 上表 D0 全部等式即 O0 正控；负控样例——把 992 当 F3、把 864+992 相加、
把 116 当 193 子集，均被 §3 字典的"关系"列拒绝。

## 5. 以后必须怎么写 / 不能怎么写

### 5.1 必须这么写

1. 每个数字带**单位**（题 / 候选行 / 已调度 spec / 事件 / 计数器 / 报告 / map 号）与
   **题域标签 [298]**。
2. F3 预门 → "F3 wildcard **178 条候选行**（52 题，D1）"。
3. 引用 992 → 必须写全名 `analog_pregate_skipped`（计数器），并注明"含 814 条 F5 reject，
   禁止与候选行相加"。
4. 引用 193 → "无已调度 `rec-` 前缀 spec 的题数"；涉资产必须拆 25/166/2（D1）。
5. 引用 134 → "未触发 `transform_no_change` 的已调度 analog spec（补集）"。
6. F5 三件套 → checked 3398 / deferred 1548 / skipped 864；864 的三个名字
   （`f5_pregate_reject` / `f5_skipped_total` / `analog_center_admission_skipped`）视为同一物。
7. 2366 → "search deferred entries"；1548 → "F5 defer"。
8. remap 三数必须带分母名：234（已调度 spec）/ 242（P2 spec 面）/ 151（P2 题面）。
9. 题/事件级分项分母引用时标注 D1 与出处（P3 报告 §3）。
10. 拒因相加仅在"5319 行单拒因穷尽分箱"口径下声明。

### 5.2 不能这么写

| # | 禁止 | 原因 |
|---|---|---|
| 1 | 864+992、1585+992、1585+2366 等任何含计数器/跨口径的加法 | 992 与 864 重叠 814，重复计数 |
| 2 | "F3 992 条" / 把 992 当 F3 | F3 只有 178 条候选行 |
| 3 | 把 178 写成"非 F5 适用（recorded/corpus 等）" | 1585 全部 analog；178 全部是 analog wildcard 行 |
| 4 | "EAWAG recorded 资产缺席 193" / "recorded 无资产" | rec- 含 corpus 直通；193 内 160 题有 corpus 行、97 题有 EAWAG 行(D1)；全批 182 题有 EAWAG 行 |
| 5 | 105−182 或反向推"转化率" | 两个 presence 分母定义不同 |
| 6 | 把 116 当 193 的子集 | 20 题在 193 外 |
| 7 | "134 条 remap 欠账 / 134 个可修复缺口" | 134 是未触发 tnc 的补集 |
| 8 | 234/242/151 互换 | 三个分母（已调度 spec / P2 spec 面 / P2 题面） |
| 9 | 194+164+52、1077+920+277 等题/事件跨分项相加 | 并集 227，重叠大 |
| 10 | 2366 与 1548 互换或相加 | search deferred entry vs 候选行 |
| 11 | 把 207 写成 T-H r2 实测 | T-H 实测 193；207 是 chain14 跨批锚点 |
| 12 | 从拒绝条数推收益或题级损失 | 关联≠因果；F5 194 题中 58 题仍 hit@1(D1) |
| 13 | 把 reason 直方图跨箱相加当"可修复总量" | 分箱合法，修复语义各自独立 |
| 14 | 把 D1 值冒充冻结证据 | `[WL]` 已失；D1 只能引 P3 报告并标注 |

## 6. 仍 unknown 的口径（不估算）

1. **最大 unknown**：864 条 F5 拒绝中真实中心缺失 vs 检索/资产缺面的比例（D2/D3）。
2. 543 条 compiler no_alignment 中 remap 诱导 vs 非 remap 的比例（D2）。
3. 134 的题/事件分母（`[WL]` 无该投影且已失；需新的只读白名单投影，D2）。
4. direct_raw 50 的逐行身份（仅代码+计数闭合推断，无逐行字段）。
5. F3 178 的 wildcard 化学语义与可编译子集（D3，需化学评审与 CC 授权）。
6. 193 A 组 25 题：资产缺面 vs 检索键/索引漏召（D2）。
7. 193 C 组 2 题是否即 NC-9 零事件 2 题（2/2 重合，疑似未 crosswalk）。
8. 207 与 193 的 −14 差集构成（跨批）。
9. 全部 D1 题/事件分母的当前复算（`[WL]`=/tmp/th_pool_diag.json 已不存在；需新的只读
   白名单投影再证；P3 报告 §3 的 D1 数值在再证前以该报告为准）。
10. 事件级候选归因（1586 事件与候选行的逐条对应）。

## 7. 边界声明

- 只读：未改代码、未改判据、未动封存批根、未调用模型、未连 HPC、未 push；
  未读金标、题面、`reference_graphs`、`env`、key、封存逐题 `payload.json`；零化学串。
- 只新增本文件与 `docs/review_evidence/p3_o0_metric_2026-10-23/`（metrics.json + SHA256SUMS），
  **未改任何既有文档**；既有文档中的旧标签（P0 摘要"992/F3"、"recorded/corpus 等 178"、
  P0 决议包 D-7"F3 992 条"等）以本文 §3 字典为准更正引用方式，原文不作回写。
- 代码行号在 HEAD `966bc566…` 复核；与 P3 报告期 HEAD `11aeeafd…` 的被引行号一致。
- `[WL]` 已失的披露：P3 报告所有 D1 重算值本轮无法独立复验；本字典将它们与 D0 严格分级，
  后续任何引用都必须带 D1 标签。
