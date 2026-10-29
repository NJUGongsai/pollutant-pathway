# v4.3（T-H r2）代码架构通读与优化建议（2026-10-20）

> **题域标签：298 = RHEA 通用酶学 / 已见题（post-hoc）。** 本文所有题数、比例、桶读数只在该
> 题域成立，不向 dev 或其他题域外推。
>
> **性质**：只读架构通读 + 优化建议。未重跑、未重判、未调模型、未读金标/reference_graphs/
> 题卷；批 `t_h_s5b_298_20261020r2` 封存只读，本文零触碰。
>
> **证据基础**：三条链路（排序位次、编译供给、判分预算）逐文件通读，全部结论带 `file:line`；
> 关键结论（effective_rank 生成、位次字段披露、宽度截断、partial 判据、T-F 修复状态）已由
> 主会话二次抽查源码确认。证据强度按仓内惯例标注：**可证**（源码/计数直证）/ **关联** /
> **unknown**（缺什么写明）。

---

## 0. 先纠正一个读法：不是"下降"，是"平台"

| 对照（v2 同口径） | hit@1 | 差值 |
|---|---:|---:|
| chain13 | 87 | T-H **+2** |
| chain14 A | 91 | T-H **−2** |
| chain14 B | 85 | T-H **+4** |
| **T-H r2** | **89** | 落在历史单臂散布区间 85–91 内 |

- T-H 相对 chain13 是 +2，相对 14B 是 +4，只相对 14A 是 −2；**整体不是回归，是净效应≈0**
  （18 改善 / 16 退化的高换手，见归因报告 §5/§6）。
- 真正的问题是**平台**：四批全挤在 29–30.5%，而预注册线是 35–40%（104–119 题），
  距下沿还差 15 题。单臂批次噪声量级 ±3，任何单项优化若只值 2–3 题，永远测不出来。
- 因此本文的优化目标不是"找回那 2 题"，而是**找到能单独够到 +15 量级的杠杆**，并把
  "不可归因"变成"可归因"。

---

## 1. 架构速览（通读后的一句话版本）

系统是三段流水线，298 批的命中由第三段决定：

```
[build 期·供给链]                      [run 期·执行链]                 [score 期·判分链]
检索(recorded/corpus/analog)            池冻结进 run_inputs             参与物多重集严格相等 ⇒ strict
→ F1-F4 路由 → F5 中心锚定              → _run_decide: 模型显式 rank     (criteria-v2 只豁免 superset
→ 编译(remap/编辑/身份门)                 绝对优先,其余 fallback 池序      的 H2O/H+/Pi/PPi 多余物)
→ 去重(net_reaction_signature)          → 按 effective_rank 入队         → 候选=已提交事件按
→ 截断(max_pool=8) → 池                 → 微秒 created_at 串行执行        (created_at, event_id) 排序
                                      → 每个成功 expand 提交 1 事件     → rank = 首个 strict 命中事件位次
```

关键文件：`s5b_builder.py`（建池）、`s5b_compiler.py`（编译/门）、`runflow.py`（位次与驱动）、
`queue.py`/`search.py`（调度与预算）、`production.py`（事件生产）、`evaluation.py`/`s5b_scoring.py`
（判分）。

---

## 2. 从代码里读出的八个关键事实（每条都带杠杆含义）

### 事实 1（可证）：hit@1 = strict 命中 **且** 该事件是提交序第一个；提交序 = effective_rank 序，判分后不可重排

- 位次唯一生成点：`runflow.py:1089-1103`（模型显式 rank 密集重编号在前，未 rank 条目按
  `prepared_entries` 原序殿后）。
- 兑现通道：`queue.py:211-215` 排队 → `search.py:717-757` 微秒单调 `created_at` →
  `runflow.py:688-757` 串行执行 → `s5b_scoring.py:641-664` 按 `(created_at, event_id)` 重建候选序。
- 判分侧明文"冻结后不得按结果重排"（`s5b_scoring.py:643`）。
- **含义**：一切位次优化必须落在**提交序生成之前**；事后重排不是合法杠杆。

### 事实 2（可证）：37 题"strict 但非首位"的成因目前二分不可知——但反查材料齐了

- 归因报告杠杆 1 的 37 题（rank 2–5 的 36 + rank 6 的 1）是最大单块，上限 +37。
- `per_qid` 没有 `rank_basis` 字段 ⇒ 分不出"**模型自己把金标排 2–5**"还是"**模型没排、
  掉进 fallback 按池序殿后**"。这两者的修法完全不同（前者要动模型序，后者动池序/排序键）。
- 但逐 expand 冻结载荷里其实**全带**：`model_rank / model_rank_inherited_from / effective_rank /
  rank_basis / rank_policy_version`（`runflow.py:1144-1150`），事件经
  `hypothesis_id → prepared_hypothesis_id` 可映射回条目。
- **含义**：把 37 题拆桶只需要一次**只读反查**（零模型、零判据、零金标外发）。这是所有
  位次工作的第 0 步，见 §3 档 A。

### 事实 3（可证，且发现一处对老师回复的事实错误）：T-F 位次继承**已修**，且真实批 0/298 触发

- 修复 = `s5b-rank-policy-2`，2026-10-17 三连提交（`e3fe446`/`0facf85`/`84cc9ff`）：
  折叠位次继承（min 语义）落地于 `runflow.py:1076-1088`，回归测试
  `tests/test_tf_rank_inheritance.py` 全绿；T-H r2 批版本面就是 rank-policy-2。
- 但 chain13/T-H 两次真实批"首位被折叠"均 0 例 ⇒ 37 题的位次损失**不是**这个 bug 造成的。
- **⚠️ 文档不一致**：`REPLY_TO_TEACHER_HUANG_T_H_2026-10-20.md` §3 行 6 写"T-F 修复未实施、
  请老师裁定是否单独补修"，与代码事实（policy-2 已随既往轮安装、`T_H_RESULT` §1 版本面已列）
  矛盾。**建议向老师补一条事实更正**：修复本体已在，未做的只是**披露半边**（per_qid 缺
  rank_basis/fold 字段）——这正是下条事实。

### 事实 4（可证，有全负先例）：机械重排已被试过且全负，"换个排序规则就好了"不成立

- 先例：`scripts/s5b_t6_rerank_probe.py` 四条机械规则（来源优先级/参与物数/重原子数/反序）
  在 chain12 损失批上**全部为负**（最好 −2，见 `S5B_CHAIN12_LOSS_ATTRIBUTION_ROUND1_...:30`）；
  且当时 `model_rank` 在候选事件上覆盖率仅约 12%。
- **含义**：位次杠杆必须先做事实 2 的拆桶归因，再按证据选刀；盲试机械键已有负先例，
  不要重复烧批。

### 事实 5（可证）：供给面是"质量问题"不是"数量问题"；remap 失败在批级不可归因

- r2 全批编译拒绝直方图（5319 候选行 → 531 入池）：`no_alignment 1585（37%）`、
  `cosubstrate_bonded 972`、`mapping_truncated 260`、`stereo_edit 255`、`charge_edit 253`、
  `ambiguous_alignment 242`、`transform_no_change 231`。
- remap 面池反而**更深**（均值 2.56 vs 对照 0.98）但命中更低 ⇒ 编译进来的候选不对/
  该编译的被拒，不是候选不够。
- `template-remap-1`（D1.2）**只在 transform_no_change 一条路上触发**（`s5b_compiler.py:1442-1452`），
  且 remap 失败 detail 被 builder 丢弃（`s5b_builder.py:1236-1246` 只取 reason 不取 detail）
  ⇒ 批级分不出"没试 / 试了配不上 / fail_closed"，231 条 tnc 是一团黑箱。
- analog 召回侧 `scored[:top_k]` 截断与超阈候选数**无任何诊断字段**（`analog_source.py:391`）
  ⇒ 41 题"remap+旧口径无候选"分不出"召回不够"还是"召回到了全被拒"。
- **含义**：供给侧动手之前必须先补诊断透传，否则任何改动都无法验收（见 §3 档 A3/A4）。

### 事实 6（可证）：compiler-6 身份门的拒绝粒度是"整件 spec"，且判据挂在 RDKit 序列化能力上

- 门在 `s5b_compiler.py:1472-1485`：产物侧任一组分 `build_chemical_state` 失败 ⇒ 整 spec 拒。
- 根因实测：自由电子数=4 的 `[N+]`/`[C]`，RDKit 写出裸 `|0|`（无登记）被拒；=1/3 的
  `[CH3]`/`[CH]` 写出 `|^1:0|`/`|^5:0|`（登记类）**放行**——门的边界是"RDKit 能不能写进
  `^N` 层"，既不是"自由基一律拒"也不是"退化碎片全抓"。
- 已证实 hit@1 代价 = 1 题（`RXNG_531caa559d3` 1→0 空池）；另有 7 题空池的反事实 unknown。
- **含义**：存在"丢弃坏 coproduct + 披露"的中间档（现在只有整件杀），但产物集变化动
  `net_reaction_signature` 与 strict 产物门，**属金标相关，须用户/老师拍板 + mimo 场景 1**。

### 事实 7（可证）：partial 53 题的判据结构决定了"接近命中"分两种，其中一种可能被自家配置卡住

- exact = 参与物多重集**严格相等**（`evaluation.py:2438-2444`）；criteria-v2 豁免**只救
  superset**（多余物全属 H2O/H+/Pi/PPi 且过三谓词才升 exact，`evaluation.py:2445-2463`）；
  **`partial_subset`（缺参考侧参与物）完全没有升级路径**；step_scope 不一致连 partial 都进不了。
- 另一侧：`max_product_expansion_width=2`（`s5b_orchestrator.py:106`）——超出宽度的产物直接
  进 deferred（`production.py:1197-1208`，reason=`product_width_limit`），**不进事件参与物**。
  若金标边有 3+ 产物，事件天然缺参与物 ⇒ partial_subset。
- **含义**：53 题 partial 里可能有一块是"宽度配置自己造成的缺参与物"——这是零模型可实验的
  面（先归因后动刀，见 §3 档 D）。此推断目前是**假设**，需 A2 的 defer_reason 直方图证实。

### 事实 8（可证）：预算与失败处置的三个"沉默点"

- `budget_limit` 是**任一上限打满即计**（`search.py:3091-3105`），不只是总动作数；
  `max_real_model_requests=1`、`alternatives=8`、`attempts=1`、`depth=1`、`width=2`、
  `total_actions=48`（`s5b_orchestrator.py:102-118`）都极易打满——298 题全 budget_limit
  不代表"预算紧张"，代表这个停止标签信息量很低。
- 2366 个 deferred **在生产里没有任何回收路径**：激活入口 `plan.activations` 是测试专用
  （`runflow.py:68-73` 明文"不是生产数据"，生产 run_input 不带该键），且重激活还要过预算预检。
- `method_failed`（AtomValenceException）处置 = 丢候选、不产事件、**不通知模型、不重试**
  （`production.py:1165-1170`、`runflow.py:1489-1498`；format_feedback 轮数=0）。
  12 题受影响、9 题未命中。候选死掉还会让后继候选位次整体前移——对位次是双向扰动。
- audit 的 `center_mismatch` violated（45 题）**不降权**，事件照常提交参与排名
  （`production.py:126-129`）——它不是丢分标记，不要当杠杆。

---

## 3. 优化建议（分档：证据强度 × 杠杆 × 成本 × 风险）

### 档 A：零模型、零判据、零金标——先做，本周可完成（A1 是一切位次工作的第 0 步）

| # | 动作 | 做法 | 产出 | 成本 |
|---|---|---|---|---|
| A1 | **37 题位次拆桶反查** | 从封存批只读拉逐题 expand 载荷，经 `hypothesis_id→prepared_hypothesis_id` 映射，把 37 题非首位 strict 拆成"模型排 2–5" vs "fallback 池序"两桶；顺带统计 T-H 批 `model_rank` 在候选事件上的覆盖率（历史 chain12 仅 ~12%，本批未知） | 位次杠杆走"模型序"还是"fallback 序"当场定刀；填掉归因报告 unknown #4 的一半 | 极低 |
| A2 | **deferred 2366 条按 defer_reason 直方图** | `native_result.json` 已导出 `defer_reason/defer_trigger`，只读聚合 | 分清 alternatives_budget / product_width_limit / depth_limit / selection_cap 各占多少；**证实/证伪事实 7 的宽度假设** | 极低 |
| A3 | **remap 诊断透传 + analog 召回计数**（工程小改） | ① builder 消费 compile detail 时把 `template_remap{applied,n_new_maps,未命中签名}` 透传进 `_diag_row`/直方图键；② analog 侧补 `n_scored/n_above_threshold/n_truncated`（纯诊断字段，不动池成员，不需版本升版） | 下一批起 231 条 tnc 与 41 题"无候选"从黑箱变可归因 | 低 |
| A4 | **身份门旁路诊断落盘** | 被身份门拒的 spec 原文 + `invalid_components` 落旁路诊断件（不进池） | 7 题空池逐件可复盘，供 mimo 场景 1 评审取材 | 低 |
| A5 | **披露半边补齐 + 老师回复事实更正** | ① 后续批 per_qid 增加 `rank_basis`/fold 披露字段（即 T-F 未做的那一半）；② 向老师更正"修复未实施"表述（事实 3） | 位次实验的验收前提；对外事实准确 | 极低 |

**纪律**：A3/A4 是新增披露字段/旁路件，不改判据与池成员，按"纯诊断"走；一旦字段进公共
验收面，随下一轮交付提交。

### 档 B：位次杠杆（唯一天然够 +15 量级的杠杆；上限 +37 是数学上限，不是收益预测）

| # | 动作 | 前置 | 风险控制 |
|---|---|---|---|
| B1 | **按 A1 结果选刀**：fallback 桶大 ⇒ 改 fallback 排序键/池序（升 `s5b-pool-policy-10` 或 `rank-policy-3`）；模型序桶大 ⇒ 做**基于证据的**排序特征（如 recorded_strict_exact 提层、化学先验分层），不做盲机械键 | A1 完成 | 机械键全负先例在案（事实 4）；任何位次改动=提交序变化，必须升版本 + 预注册 + 基线红绿对照 |
| B2 | **同题配对验收**（不靠单臂总数） | B1 实施 | 单臂噪声 ±3；用逐题配对（改善/退化/持平三栏，同 T-H 回查口径）判定，而非 hit@1 总数 |
| B3 | **预期管理** | — | 37 题里已有 10 题是 chain13 原 hit 的位次换手——重排是"双向刀"，验收必须同时看改善与退化两栏 |

### 档 C：供给面（把"该有候选没有"变成候选；每项都动化学/身份判据，全部走 mimo 场景 1 + 版本流程）

按"确定性收益 ÷ 判据风险"排序：

| # | 动作 | 量级证据 | 风险/前置 |
|---|---|---|---|
| C1 | **edit proto 加电荷 op**（charge_edit v3） | `charge_edit_unsupported 253`（remap 面 174 vs 对照 79）——remap 面特有大户 | 动 `v43-editproto` 公共契约，最大一刀；先做 A3 诊断确认样本形态 |
| C2 | **no_alignment 两级探针**（L2 壳层失败降级"放宽再试+披露"） | 全批拒绝 37%（1585 条） | 化学判据面变化；`c2_l3_disclosure` 已有豁免披露机制可复用 |
| C3 | **身份门处置粒度**（坏 coproduct 降级丢弃+披露，非整 spec 杀） | 有界：7 空池 + 14 余池题；已证实 hit@1 代价仅 1 题 | 产物集变化 ⇒ 金标相关，**须拍板**；双向风险（过松=整题 0 调用重现） |
| C4 | **共底物键合贡献归属扩档** | `cosubstrate_bonded 972`（量最大） | 化学判断最重，排在 C1/C2 后 |
| C5 | **remap 触发面扩展**（tnc → "存在未映射分量且拒因∈{tnc,no_alignment}"） | 待 A3 诊断定标 | 判据面变化，mimo 场景 1 |

**明确不建议**：扩池宽/降阈值这类"多给候选"的粗刀——remap 面池更深命中更低已证明
数量不是瓶颈（事实 5）；且动池配置要升 pool-policy，改完也无法归因。

### 档 D：partial 53 题（先归因，再决定是否动刀）

| # | 动作 | 说明 |
|---|---|---|
| D1 | **53 题三分类归因**（零模型，只读）：superset 非豁免 extra / partial_subset 缺参与物 / step_scope 不一致 | 判据结构见事实 7；scope 类直接排除（改不动） |
| D2 | 若 D1+A2 证实"宽度截断造成缺参与物" ⇒ **width 2→3/4 单变量实验**（预注册、注意与 total_actions=48 的预算交互） | 零模型成本的配置实验；这是 partial 面唯一可能"免费"的块 |
| D3 | **不碰 T1′**（未声明多余产物第三态）：判据代码里明写"未实施、fail 方向保守" | 动它=判分口径变更=红线，须老师批准，本文不建议列入本轮 |

### 档 E：预算/调用结构（费用敏感，默认不做）

- `max_real_model_requests=1`、`alternatives=8` 提额 = 新实验，**预注册先于付费**；
  2366 个 deferred 无生产回收路径（事实 8），任何"回收 deferred"设计都要动预算账与
  plan 冻结身份，属拍板级改动。若 A2 显示 alternatives_budget 是 deferred 大头，
  可把"alternatives 8→12 单变量批"作为**下一轮预注册候选项**报老师，不自动执行。

---

## 4. 与死路清单的对账（对应老师任务书 §二）

任务书封存的六项——深位召回、类比编辑线、窗口扩大、温度调整、L3 补声明、L1 新 mask、
RankLLM 工具包与多轮调用——**本文零重启项**。档 A 全部在死路外（诊断/披露）；档 B 是
既有候选的排序（非召回扩展）；档 C 是编译漏斗确定性修复（T-G 线既有授权范围的延伸，
但每项都标了 mimo/拍板前置）；档 D2 是既有配置的单变量实验。任何重启死路仍按原纪律：
新证据 + 老师批准。

## 5. 建议推进顺序（一张表收口）

| 顺序 | 动作 | 预期 | 前置审批 |
|---|---|---|---|
| 1 | 档 A 五项（A1 拆桶 → A2 直方图 → A3/A4 诊断工程 → A5 更正） | 把 unknown 变可归因；定 B/C/D 选刀 | 无（A3/A4 随下轮交付提交） |
| 2 | 档 B 位次实验（按 A1 选刀，预注册，配对验收） | 唯一可能单独够 +15 的杠杆；实际兑现 unknown | 预注册 + 版本升版；**预注册冻结前报老师** |
| 3 | 档 D2 宽度实验（若 A2 证实成因） | partial 面零模型块；量级 unknown | 预注册 |
| 4 | 档 C1/C2（每项独立预注册 + mimo 场景 1） | 确定性供给回收，单项量级 unknown | mimo 评审 + 拍板 |
| — | 档 C3/C4/C5、档 E | 本轮不动 | 拍板级 |

**验收纪律（对所有实验统一）**：单变量；预注册先于付费；同题配对三栏（改善/退化/持平）
而非单臂总数；判分零 LLM 不变；分母固定 298；对外数字带 298 题域标签；小改动 ≥3 seed。

## 6. Unknown 清单（缺什么，不估算）

| # | unknown | 缺什么 |
|---|---|---|
| 1 | 37 题里模型序 vs fallback 序的占比 | 即 A1；材料已齐，只差反查 |
| 2 | 位次重排实际兑现量 | 依赖 1 + 配对实验；机械键全负先例压低预期 |
| 3 | 2366 deferred 的 reason 构成 | 即 A2；native_result 已导出，只差聚合 |
| 4 | 41 题"remap 无候选"是召回不足还是全被拒 | 即 A3；诊断字段未透传 |
| 5 | 53 题 partial 的三分类构成 | 即 D1；需只读归因脚本 |
| 6 | 身份门 7 题空池的反事实 | 需 A4 旁路件 + 恢复 spec 同题重放（本轮红线内不做） |
| 7 | C1–C5 各自的真实解锁题数 | 需候选级证据（本仓无金标匹配明细），实施后按配对验收 |

## 7. 证据路径

- 本文结论的源码依据：`src/pathway_v43/pollutant/{runflow,s5b_builder,s5b_compiler,production,queue,search,evaluation,s5b_scoring,recorded_source}.py`、`src/pathway_v43/services/{analog_source,atom_tool}.py`（各处 file:line 见正文）
- 位次重排负先例：`scripts/s5b_t6_rerank_probe.py`、`docs/S5B_CHAIN12_LOSS_ATTRIBUTION_ROUND1_DELIVERY_2026-10-12.md`
- T-F 修复提交：`e3fe446` / `0facf85` / `84cc9ff`（2026-10-17）、`tests/test_tf_rank_inheritance.py`、`docs/T_RANK_INHERITANCE_FIX_CODEX_REREVIEW2_2026-10-17.md`
- 丢分归因（本文的输入）：`docs/T_H_R2_HIT1_LOSS_ATTRIBUTION_2026-10-20.md` 及其 `docs/review_evidence/t_h_r2_loss_attr_2026-10-20/`
- 同口径结果：`docs/T_H_RESULT_2026-10-20.md` §2/§4
