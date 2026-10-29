# v4.3（ppv1 多步）hit@1 优化建议 —— 代码架构解剖与分级行动清单

> **题域标签：298 = RHEA 通用酶学 / 已见题（post-hoc）。** 本文所有题数、比例、桶读数
> 均限定在该题域；**不向 dev（B1 环境路径）、新题或任何其他题域外推**。
> **判分零 LLM**；本文未重跑判分、未改判据、未调模型、未读金标 / 题面 /
> `reference_graphs` 结构正文。代码身份：`v4.3` @ `c9c6c7a`。
> **性质：工程诊断 + 建议书，不是成绩承诺。** 所有上限均标注证据强度，
> 「上限 ≠ 收益」。

---

## 0. 结论先行（大白话）

### 0.1 先纠正一个前提：T-H 其实没有"下降"

| 线 | 口径 | 读数 | 说明 |
|---|---|---:|---|
| v43 **单步** | 298 开卷 post-hoc | **136/298（45.6%）** | **本轮未动**（`REPLY_TO_TEACHER_HUANG_T_H_2026-10-20.md` §1） |
| ppv1 **多步** T-H r2 | 298 已见 post-hoc，判据 v2 | **89/298（29.87%）** | 本轮实测 |
| ppv1 多步历史 | chain13 / chain14 A / chain14 B | 87 / 91 / 85 | 同口径 v2 |

- **89 落在历史单臂散布区间 85–91 内**，不是新低。
- **136 与 89 不是同一条线**（单步开卷 vs 多步闭卷检索），**不可混比**；
  把两者相减得出"v4.3 下降"是口径误读。
- 但"只涨了 +2"本身是事实：**离预注册 35–40%（104–119 题）差 30 题**。
  本文回答的是：**这 30 题为什么拿不到，以及拿不到的是哪一层。**

### 0.2 四个结构性缺口（不是"模型不够努力"，是架构性的）

| # | 缺口 | 规模 | 性质 |
|---|---|---:|---|
| **A** | **判分面认不出正确答案**：产品已经对了，严格反应口径不认 | **52 题（17.4pp）**，跨四批稳定 52–58；其中 **T-H 本批 v3 披露直接测出 ≥23 个节点对**（互变 13 + 质子化 10）归一后相等却被判死 | 表示层 / 判据面 |
| **B** | **确定性供给面几乎是空的**：只有 91/298 题（30.5%）有 recorded 候选；编译产出中位数 **1** 个 spec | 207 题无任何 recorded 候选 | 供给面 |
| **C** | **排序面：模型自排第一 = 24% hit@1，recorded 排第一 = 49%** | 178/294 题由模型自由提案占据第一 | 排序面 |
| **D** | **⚠️ 口径效度：答案产物与所提变换脱钩** —— 事件产物取自模型**声明**的 `product_smiles`，不与它自己提出的 edits 执行结果对账 | 机制已证实，**占比 unknown** | **效度**（比提分更该先说清） |

**一句话**：这套系统目前的真实形态是「**一次 LLM 调用 + 几乎空的确定性召回 + 一个
把同一分子不同写法判死的严格身份键 + 一个只认模型声明产物、不认变换本身的答卷口径**」。
前三个缺口里有**两个（A、C）不需要新化学能力，只需要改装配与排序规则**；
缺口 B 需要真正的检索/编译产能；缺口 D 需要先说清"我们在测什么"。

### 0.3 最重要的一个数字

| 批 | 主口径 hit@1（严格反应） | 老口径 hit@1（产品 any-of） | 差 | 差/298 |
|---|---:|---:|---:|---:|
| chain13 | 87 | 145 | 58 | 19.5% |
| chain14 A | 91 | 149 | 58 | 19.5% |
| chain14 B | 85 | 142 | 57 | 19.1% |
| **T-H r2** | **89** | **141** | **52** | **17.4%** |

- **T-H 实测：141 题的第一个报告产物已经等于金标产物，老口径第一名；其中只有 89 题
  通过严格反应口径。**
- 交叉表（自算）：`main_hit1 ∧ old_hit1 = 89`、`main_hit1 ∧ ¬old_hit1 = 0`、
  `¬main_hit1 ∧ old_hit1 = **52**`、两者皆无 = 157。
- **老口径命中集合严格包含主口径命中集合**（0 题反向）。
- ⇒ **老口径是主口径的严格超集，且超集部分稳定占 52–58 题。** 这是全系统最大的、
  最稳定的单一漏斗，比 T-H 归因报告里的"位次杠杆 37 题"更大。

> ⚠️ **读数纪律**：老口径与主口径是**两把不同的尺**（老口径 = 产物串 CN 同值 any-of；
> 主口径 = 反应级参与物集合**恰好相等** + 结构严格身份），**不可混算、不可当成绩**。
> 此处只用来**定位漏斗位置**（"答案在哪个环节掉的"），不作为收益预算。

---

## 1. 架构解剖：命中到底由哪几层决定

### 1.1 全链路（含本轮实际生效的开关）

```
BUILD 阶段（批内冻结，零模型、零金标）
  ├─ 通道1 recorded exact        recorded_source.find_recorded_exact
  │    └─ compile_recorded_reaction → _assemble_cosubstrate_spec
  │         ★ 唯一会声明"反应物侧共底物"的通道（recorded_source.py:2745-2758）
  ├─ 通道1b corpus recorded      recorded_source.find_corpus_recorded_exact
  ├─ 通道2/3 analog 模板         AnalogSourceResolver.templates_similar_to
  │    └─ _compile_analog_refs：F1 路由 / F2 共底物袋 / F3 wildcard 拦 / F4 输入冻结 / F5 中心准入
  │         └─ compile_donor_template（compiler-6：remap 前置 + 产物身份自洽门）
  ├─ 去重（net_reaction_signature）+ 截断（max_pool = 8）
  └─ 产出 run_inputs/<qid>.json

RUN 阶段（每题模型调用**上限 3**、格式反馈轮 ≤2；本批实测 **294 题用 1 次、2 题用 2 次、2 题 0 次**）
  ├─ prepare_hypothesis：池条目 **全部** spec 先 prepare（无 try/except，坏 spec 整题死）
  ├─ decide：模型调用 → proposals + rank_hypotheses
  │    └─ 载荷 = {substrate_smiles, atom_id_map, pool_hypotheses[4 字段], execution_graph}
  │         ★ evidence_card_enabled = **false**（本批），模型看不到任何候选级化学事实
  │         ★ 载荷里**只有**底物 SMILES / 原子表 / 执行图 / 池条目产物 SMILES：
  │           无名称、无 EC、无条件、无模板供体式、无相似度、无编译诊断
  ├─ effective_rank 分配（runflow.py:1089-1103）
  │    ├─ 有模型显式位次 → 1..k，basis = model_selection
  │    └─ 无位次 → k+1..，basis = deterministic_fallback（= 池声明序）
  │         ★ 关键：模型**没排**的条目一律沉底；模型排的条目**全部**在未排条目之前
  │         ★ 且模型不写 rank_hypotheses 时**自动补 = 提案顺序**（model_protocol.py:223-225）
  │           ⇒ "model_selection" 这个 basis 有一部分是名义上的
  ├─ 调度：max_alternative_hypotheses_per_parent = 8（队列按 rank 截断）
  └─ 执行 → 事件（created_at 微秒序 = 提交序）
       ★★ **答案-变换脱钩**：事件产物取自 **spec 声明的 product_smiles**
          （production.py:1187-1190 ← prepared["product_states"]），
          **不是** execute_edits 的实际产物；novel 提案的这两者可以不一致，
          审计只比对 expectation.target_smiles 与执行产物（audit.py:2746-2768），
          不一致 ⇒ violated ⇒ 准入 **retain_conditional ⇒ 事件照旧提交**
          （production.py:129 ADMISSION_SUBMITTABLE）—— 见 §4.5

SCORE 阶段（零 LLM）
  ├─ 节点级：strict_identity_of == 预测态 smiles_isomeric ⇒ strict_structure
  │         否则 cn_identity 同值 ⇒ cn_only；再否则 unmatched
  ├─ 边级（S5A-03）：每个必要 from/to 参考节点都要有许可严格命中
  │    否则整条边无候选 ⇒ unmatched_required_node_uncovered
  ├─ 覆盖分级：reactants == from_states ∧ products == to_states ⇒ exact
  │            from ⊆ reactants ∧ to ⊆ products ⇒ superset ⇒ partial
  └─ 题级：rank = 第一条 matched_strict 事件在候选事件序列中的位次
```

### 1.2 参考图的真实形状（决定一切匹配行为的总开关）

`s5b_builder.py:216-287` 构造的 S5B 参考图，**每一题只有一条边**：

```
nodes = [ root(底物), product_1, ..., product_n ]
edge  = { from_node_ids: [root], to_node_ids: [product_1..n],
          participants: [root(reactant), products(product)] }
```

**这意味着**：

1. 参考侧**永远只有一个反应物节点 = 底物**。共底物/辅因子在提取规则里已被剥离
   （`s5b_builder.py:60-68` known_gaps：`cofactors_cosubstrates_stripped...`，
   "反应物侧共剥 473 项"）。
2. ⇒ **预测事件只要多声明一个反应物侧参与物（例如共底物），就变成 superset ⇒ partial。**
   **给预测侧加共底物会伤命中，不是帮忙。**（这一点与直觉相反，必须钉死。）
3. ⇒ **多声明一个产物侧副产物（coproduct）同样 ⇒ superset ⇒ partial**，
   除非该 extra 恰好是 H₂O / H⁺ / Pi / PPi 且通过三谓词（criteria-v2 豁免面）。
4. ⇒ **只要参考的任一产物节点拿不到"严格身份"命中，整条边直接判 uncovered**，
   哪怕其它产物都中了。这就是 `unmatched_required_node_uncovered` 的机制。

### 1.3 严格身份键包含什么（决定"产品对了却不认"的机制）

`chemstate._identity_key`（`chemstate.py:180-226`）→ canonical CXSMILES，
**保留**：电荷 / 立体（`@`/`@@`、E-Z）/ 同位素 / 互变异构形态；
**剥离**：原子映射号 / 坐标 / atomLabel / DATA SGroup。

⇒ **同连接、不同互变异构 / 不同质子化 / 不同立体 ⇒ 不是严格命中。**
这条已被本仓自己登记为 known gap（`s5b_builder.py:64-66`）：

```
identity_underestimation_charge_difference_cn_only
identity_underestimation_stereo_difference_cn_only
identity_underestimation_tautomer_no_match
```

而 `ppv1-criteria-v3` **已经实现了互变异构 / 质子化归一（A/B 两轴），
但被冻成 `strict_promotion = false` 的纯披露轴**（`evaluation.py:1041-1046`，
`docs/POLLUTANT_PATHWAY_CRITERIA_FROZEN_V3_2026-10-19.md`）。
**换句话说：能救的那部分算法已经写好了，只是被锁在"只看不加分"档。**

---

## 2. 缺口 A：判分面 / 表示层 —— 52 题"产品对了但反应不对"

### 2.1 证据（自算复核，T-H r2 本地镜像）

| 指标 | 值 | 来源 |
|---|---:|---|
| 老口径（产品 any-of）hit@1 | **141** | `reports/ppv1_s5b/t_h_2026-10-20/r2/metrics.json` → `old_caliber_sensitivity` |
| 主口径（严格反应）hit@1 | **89** | 同上 → `main_caliber` |
| 老口径中、主口径未中 | **52** | 自算交叉表 |
| 反向（主中老不中） | **0** | 自算 ⇒ 老口径 ⊇ 主口径 |
| 52 题的主口径桶 | unmatched 27 / partial 24 / strict-rank2 1 | 自算 |

### 2.2 机制分解（chain12 逐事件归因，判分程序复算产物，只读）

`reports/ppv1_s5b/chain12_s5b_298_v4b_20261012/analysis/` 已有的两层拆解：

**(a) partial 桶（43 题）—— 93% 是"多声明了副产物"**

| 类 | 题数 | 判据 |
|---|---:|---|
| **superset** | **40** | `from_states ⊆ reactants ∧ to_states ⊆ products`（事件多出参与物） |
| partial_subset | 3 | 事件少了参考参与物 |
| 其中 `superset_with_coproduct = true` | **40 / 43** | **多出来的那个是产物侧副产物** |
| `n_required_node_gaps > 0` | **0** | partial 题**没有**必要节点缺口 |

⇒ **partial 的主形态不是"少报"，是"多报了一个产物侧副产物"。**
判分侧对此**没有出口**：T1′（coproduct_ignore）明确未实施
（`evaluation.py:882-887`），criteria-v2 豁免只认 H₂O/H⁺/Pi/PPi 四族零碳身份
（`evaluation.py:891-904`），其余副产物**恒维持 partial**。

**(b) unmatched 桶（120 题）—— 缺口全在产物侧**

| 事实 | 值 |
|---|---|
| 未覆盖 gap 落在哪一侧 | **120/120 全在 product 侧** |
| 根节点（底物）匹配状态 | 120/120 全是 `strict_structure` |
| C1 单 gap·unmatched | 64 |
| **C2 单 gap·cn_only** | **42** |
| C3–C5 双 gap | 14 |
| 事件级覆盖错配（coverage_mismatch_events） | **0** |

**C2 = 42 题：预测产物与参考产物 CN 同值，但没到严格结构层。**
`cnonly_repr_classification.md` 已把这 43 个 cn_only 节点做完机器分类：

| 类 | 题数 | 含义 | 身份预处理可救？ |
|---|---:|---|---|
| TAUTOMER | 14 | 互变异构形式差 | ✅ |
| PROTONATION | 6 | 盐式/酸式质子化写法差 | ✅ |
| AROMATIC-REPR | 0 | — | — |
| ISOMER-TRUE | 23 | 其中 **21 题是纯立体化学差**、2 题骨架/电荷真差 | ❌ |

> **表示层便宜赢面上限 = 20/43（46.5%）**（= 互变异构 14 + 质子化 6）。

**(c) T-H 本批自己的 v3 披露（原生读数，优先于上面的 chain12 代理）**

`reports/ppv1_s5b/t_h_2026-10-20/r2/criteria_v3_disclosure.json` —— **T-H r2 这一批**跑
`ppv1-criteria-v3` 时，A/B 归一轴**已经算出来了**，但被冻在披露档：

| 字段 | 值 | 读法 |
|---|---:|---|
| `axis_pairs_total` | **47** | 归一轴判定"相等"的参考节点对 |
| `single_attribution_counts` | tautomer **13** / protonation **10** / none 24 | 23 对是**互变异构或质子化差**（可归一救） |
| `tautomer_normalized_pairs_default` = `..._stereo_preserving` | 13 = 13 | **13 对互变异构在"保留立体"臂下依然成立** ⇒ 不是消旋假象 |
| `protonation_normalized_pairs_uncharger` = `..._charge_parent` | 10 = 10 | 两种算子一致 |
| `carbonate_system_excluded_pairs` | 0 | 本批无碳酸体系冲突 |
| `fail_closed_pairs` / `double_satisfied_pairs` | 0 / 0 | 无解析失败、无双轴争用 |
| **`strict_promotion`** | **false** | **不授 strict** |
| **`hit_at_1_effect`** | **"none"** | **不进 hit@1** |
| **`tier_b_status`** | **"locked_not_unlocked_this_round"** | **档 B 未解锁** |
| `tautomer_promoted_nodes` | `[]` | 恒空 |

⇒ **T-H 本批至少有 23 个节点对（互变异构 13 + 质子化 10）是"归一后相等、但被判分面
判死"的**；节点对 ⇒ 题数上限 **≤23 题**（一题可能多对）。
**这不是推测，是本批自己跑出来的机读数 —— 算法已经写好，锁在披露档。**
（"none 24"那 24 对是真结构差，不可归一救。）

### 2.3 立体化学那 21 题是硬天花板

- **编辑协议只有四个操作**（`services/atom_tool.py:73`）：
  `("break_bond", "form_bond", "change_bond_order", "add_atom")`
  —— **没有任何一个能设置立体构型**。
- 提示词契约（`real_model.py:135-193`）也没有立体字段；示例（`real_model.py:195-198`）
  是无立体的。
- 编译器还会主动**消解**立体（`s5b_compiler.py:619` `_is_stereo_dissolution`，
  sp3→sp2）。
- 而严格身份键**保留立体**（`chemstate.py:180-226`）。

⇒ **模型自由提案的新产物，除底物原有中心外不可能带立体；**
⇒ **凡是金标产物带新立体中心的题，novel 通道结构上永远 strict 不中。**
`cn_only` 分类里 21 题"纯立体差"就是这个天花板的量化。

### 2.4 配套的判分面数据缺口（R9 / R14，零成本但必须知道）

- **豁免三谓词的 pred1 需要"声明链"**（`event → hypothesis → provenance_refs →
  provenance_records.record_equation`）。链断 ⇒ `unknown` ⇒ fail-closed **不豁免**
  （`evaluation.py:1848-1920`）。这是**数据管线问题，不是化学问题**，
  但它会把"化学上正确的事件"判死。
- **`edge.participants` 只被披露、不被比较**（`evaluation.py:2513-2515`），
  `participant_list_status = "partial"` 也**从不被消费**（`evaluation.py` 内无读取）。
  ⇒ 参考侧自认"清单不完整"，判分侧却仍要求**参与物集合恰好相等**。
- **题级只取第一条参考边**（`s5b_scoring.py:678` `edge = edge_matches[0]`）——
  S5B 图目前恰好一条边，暂无害，但多边图会误判。
- **`known_gaps` 会遮蔽预算桶**（`evaluation.py:2499-2503`）：S5B 图永远带 known gap，
  所以 `unmatched_budget_unexpanded` 在本线**永远不会出现**，
  预算侧漏题被记到模型侧桶里。

---

## 3. 缺口 B：供给面 —— 确定性通道只覆盖 30.5% 的题

### 3.1 自算证据（chain14 A/B 本地 synced run 库，只读，未重判）

探针：`reports/ppv1_s5b/opt_probe_2026-10-20/probe_channels.py`
（只读 `pollutant.sqlite` 的 `search_actions.payload`，零金标、零重判）

| 指标 | chain14 A（证据卡 off） | chain14 B（证据卡 on） |
|---|---:|---:|
| 已调度候选总数 | 1539 | 1482 |
| ├ **novel（模型自由提案）** | **1335（86.7%）** | **1279（86.3%）** |
| ├ recorded（记录反应） | 135（8.8%） | 134（9.0%） |
| └ template（模板编译） | 69（4.5%） | 69（4.7%） |
| `rank_basis = model_selection` | 1538 | 1482 |
| `rank_basis = deterministic_fallback` | **1** | **0** |
| **有 recorded 候选的题** | **91 / 298（30.5%）** | 91 / 298（30.5%） |

**"模型显式排了序"占比 1538/1539 = 99.94%。确定性 fallback 形同虚设。**

### 3.2 recorded 通道在场与否的成绩差（chain14 A，自算）

| 桶 | 题数 | hit@1 | hit@1 率 | strict | 老口径产品命中@1 |
|---|---:|---:|---:|---:|---:|
| **recorded 候选在第 1 位** | 77 | 38 | **49.35%** | 49 | 61.0% |
| **recorded 候选在场但不在第 1 位** | 14 | 2 | **14.29%** | 6 | 42.9% |
| **完全没有 recorded 候选** | **207** | 51 | **24.64%** | 69 | 46.4% |

**读法**：
- recorded 通道**在场且排第一**时 hit@1 是 49.4%；**不在场**时只有 24.6%。
- 这个差是**关联不是因果**（recorded 能检索到的题可能本身更容易），但量级大、两臂同向。
- recorded 在场却没排第一的只有 14 题（arm A）/ 8 题（arm B）⇒ **"把 recorded 提前"
  这个杠杆本身很小（≤14 题）**；**真正的问题是 207 题根本没有 recorded 候选。**

### 3.3 编译产出近乎为零（chain12 供给面描述统计，`funnel_chain12_summary.md`）

| 指标（strict 桶 130 题） | 均值 | 中位 | 最大 |
|---|---:|---:|---:|
| `specs_raw` | 18.97 | 17 | 45 |
| **`pool_compiled`（真正编译出来的 spec）** | **0.78** | **1.0** | **4** |
| `pool_compile_fail_total` | 18.18 | 17 | 43 |

**每题约 19 个原始 spec，只编译出 0–4 个（均值 0.78、中位 1）。**
126/130 题出现过池编译失败。

### 3.4 为什么编译不出来：漏斗上的三层门

| 层 | 位置 | 拒因（机器码） |
|---|---|---|
| 模板元素账 F1 / 共底物袋 F2 / wildcard F3 / 中心锚 F5 | `s5b_builder.py:1431/1475/1480/1501/1333` | `no_alignment`（**F5 未评估、F3 被拦、编译器真无对齐，三者共用同一码**） |
| 模板映射不完整 | `s5b_compiler.py:396-401` → remap 前置 `:1442-1458` | `transform_no_change`；remap 只能补**编号**，补不了化学 |
| 中心定义 / 对齐 / 歧义 | `s5b_compiler.py:779/1572/1581/1716` | `center_empty:*` / `no_alignment` / `alignment_limit_exceeded` / `ambiguous_alignment` |
| 产物身份自洽门（compiler-6） | `s5b_compiler.py:1504-1535` | `product_component_identity_invalid`（RDKit 把 `[N+]` 写成裸 `\|0\|` 旗标块 ⇒ 未登记 CX 类 ⇒ 整 spec 拒） |

**两个具体的诊断盲点**（零风险、可直接修）：

1. **`no_alignment` 一码多用**：F5 跳过、F3 wildcard 拦、编译器真无对齐全落同一码
   （`s5b_builder.py:1376-1391` `_emit_rejected`）⇒ `compile_failure_histogram`
   **无法区分"省预算的预门跳过"与"真编译失败"**，漏斗分析一直在读被污染的数。
2. **remap 披露不区分加/减**（`s5b_compiler.py:1538-1547`）：只给 `applied` + `n_new_maps`，
   不给"补出了新增原子（→ add_atom）"还是"只补出了离去基（→ break_bond）"。
   而实测 **remap-only（add=0）面 17 题只命中 1 题（5.88%）**，
   非 remap 对照 147 题命中 53 题（36.05%）—— **remap-only 面就是"只断键、
   不长原子"的退化变换**，缺这一位披露就无法在题级归因。

### 3.5 一个必须先排掉的反例

**remap 不是"越长越对"**：T-H 实测 remap 面（151 题）hit@1 23.84% < 非 remap 面
（147 题）36.05%，缺口约 18.4 题。但这是**关联不是因果**——remap 题集可能更难，
本轮没有同题 A/B。**不能写成"remap 导致丢分"。**（`T_H_R2_HIT1_LOSS_ATTRIBUTION` §3.3 已如此标注。）

---

## 4. 缺口 C 与 D：排序面 + 模型交互层

### 4.1 证据（chain14 A/B 自算）

| 第一名通道 | 题数（A） | hit@1 率（A） | 题数（B） | hit@1 率（B） |
|---|---:|---:|---:|---:|
| **recorded（记录反应）** | 77 | **49.35%** | 83 | **42.17%** |
| template（模板编译） | 39 | 28.21% | 46 | 21.74% |
| **novel（模型自由提案）** | **178（60.5%）** | **23.60%** | 164 | **24.39%** |

**模型把自由提案排第一的题，hit@1 只有 24%；把记录反应排第一的题，hit@1 有 49%。**
模型自己的第一选择，精确度大约是确定性通道的一半。

### 4.2 机制（代码）

- `runflow.py:1089-1103`：**全部有模型显式位次的条目排在所有未排条目前面**；
  未排条目按池声明序（recorded → corpus → template）沉底。
  代码注释写明这是有意的（"全部显式有效 rank 先于一切未 rank fallback"）。
- `queue.py:211-215`：调度按 `rank` 排序，`rank is None` 沉底；
  `max_alternative_hypotheses_per_parent = 8`。
- `real_model.py:255-268`：模型看到的池**就是池声明序**（recorded 在前），
  但模型可以把 pool 条目排到自己的 novel 提案后面。
- **没有任何一处把"通道出处"当作排序先验**。`retrieval_rank` / 检索分数
  **从不参与排序**（只作披露）；`evidence_level` 在 PPV1 路径上根本不在候选上。
- ⇒ **模型对"自己写的"和"语料里查到的"没有任何差别对待的倾向约束**，
  而两者的精确度差一倍。

### 4.3 已有证据：证据卡 v1 是**负结果**，别重复踩

chain14 同批 A/B（`CHAIN14_EVIDENCE_AB_RESULT_2026-10-16.md`）：
**B（证据卡 on）− A（off）= hit@1 −6**，目标面（strict-rank>1 的 32 题）反而 −2，
选择面恶化（strict-rank>1 33→37），input token +26%。
机制归因（`CHAIN14_ATTR_PROBE_RESULT_2026-10-17.md`）：
**"出处通道挤位"批级显著（novel 被挤出第一名 15:2，p=0.0024）**，
**"完整度挤位"题内最强（参与者行数 +0.79 行，p=0.078）**。

⇒ **信息增肥（加字段）解决不了排序问题，还会让模型更偏爱"看起来完整"的候选。
要动排序，得动排序本身（代码层先验），不是动提示词层信息量。**

### 4.4 证据卡 v2：**已设计冻结，未实施**（且本批根本没开卡）

`docs/TASK_EVIDENCE_CARD_V2_DESIGN_2026-10-17.md`（设计任务书，正链终认见
`docs/EVIDENCE_CARD_V2_DESIGN_CODEX_FINAL_2026-10-18.md`：**只放行设计冻结，
明示"不能声称 v3 已实现"**）的裁剪清单 —— **代码里一条都没实施**：

| v2 冻结裁定（任务书行号） | 代码现状 |
|---|---|
| 砍 Gasteiger 全部（:13） | ❌ 仍在 `candidate_evidence.py:284, 324-361` |
| 砍 `molecular_formula`/`element_counts` + FG 的 `smarts` 串/`matches` 渲染数组；**FG 只留类名 + n_hits**（:14） | ❌ 仍渲染 `smarts` 与 `matches`（`:306-323`） |
| `alignment_quality` 只留 status 一枚（:15） | ❌ 仍 7 字段（`:190-212`） |
| **S1**：卡内 `source` 四件（source_kind / transformation_ref / origin_group_key / alignment_ref）全删，顶层 transformation_ref 原样保留（:17） | ❌ 卡内 source 仍在（`:163-187`）；顶层保留属实（`real_model.py:263`） |
| 加 FG delta（编译器指定主产物 scope，类集合语义）（:20） | ❌ 无 |
| 加 Δ 分子式/氧化度（次优，主产物级）（:22） | ❌ 无 |
| token 离线门 **≤+13%** 为发车前硬门（:23，tokenizer 版本固定、逐题+批合计、UTF-8 字节数不得当 token） | ❌ 无（仓内无 tokenizer 计量代码） |
| schema 升 v3 | ❌ 仍是 `candidate-evidence-2`（`:45`） |

且本批 `orchestration.json → evidence_card_enabled = false` ⇒
**模型在本批既没有证据卡，也没有 v2。**

> **两条必须随带的纪律（来自 v2 任务书自身，不是我加的）**：
> ① S1 是**非盲臂**（记录身份在顶层仍可见一次）；
> ② **A/B 估计的是整包方案差异，不识别单字段贡献**；
> ③ 既有停点（**全局或任一分族 v2 strict 净失 ≤−3**）保持最高优先，
> token 门是附加读数、不取代停点。

⇒ **读法**：证据卡这条路线的状态是「v1 实测负、v2 设计完但没写、v2 的动机来自对 v1
负结果的归因」。**不建议把它当第一优先**（v1 的 −6 已经证明"加字段"这条路本身有问题）；
但 **v2 的裁剪方向（砍完整度信号）恰好命中 §4.1 的"完整度挤位"机制**，
若将来重启这条路，**必须先实现 v2 的裁剪，再开卡**，不能直接开 v1。

### 4.5 ⚠️ 新发现：**答案产物与所提变换脱钩**（口径效度问题，不只是效率问题）

**代码事实链（逐条可核）**：

| 环节 | 取什么 | 位置 |
|---|---|---|
| 事件产物 | **`spec` 声明的 `product_smiles`**（+ coproducts） | `production.py:1187-1190`（`prepared["product_states"]`） |
| 实际执行产物 | `execute_edits` 的 `result["product_smiles"]` | `production.py:1004`、`:1022` |
| 两者对账 | **全仓无此比较** | —— |
| 审计比对的是 | `expectation.target_smiles` **vs** 执行产物（**模型自己写的**） | `audit.py:2746-2768` |
| 对账失败的后果 | audit `violated` → 准入 `retain_conditional` → **事件照旧提交** | `production.py:129`（`ADMISSION_SUBMITTABLE`）、`:1176-1181` |
| 池条目为何没事 | 编译器保证 spec 产物 **==** 执行产物 | `s5b_compiler.py:1747-1764` |
| **novel 提案为何有事** | **模型声明的 product_smiles 与它自己的 edits 之间无任何强制** | —— |

⇒ **模型可以声明任意"可解析 + 价态合法"的产物 SMILES，同时给一套产生别的结构的 edits；
系统会把模型声明的那个 SMILES 当作"该反应的产物"写进事件，交给判分面比金标。**

**这条的意义有两层**：

1. **效度层（必须知悉）**：当前 hit@1 度量里，有一部分是"模型有没有点名正确的产物 SMILES"，
   而不是"模型有没有提出正确的变换"。**这是口径效度问题，比提分更该先说清。**
2. **工程层（一条明确的可试路径）**：把事件产物改成**执行产物**，或加一道
   **"声明产物 == 执行产物"的硬门**，系统的答案就和变换重新绑定。
   **方向不确定**：会让"声明对了但变换错了"的题掉分（诚实化），也可能因执行产物更贴近
   正确化学而涨分。**必须单变量 A/B 实测，不能拍脑袋，更不能默认它是"提分项"。**

> ⚠️ **本报告不宣称这 52 题里有几题是由脱钩造成的** —— 那需要候选级金标匹配
> （见 §7 unknown #3）。**目前只能确认机制存在，不能确认占比。**

### 4.6 模型交互层的两堵硬墙

**(a) 价态墙：`change_bond_order` 只能扣"括号显式氢"**

`atom_tool.py:486-503`：键级升高时，只对端点的 **`numExplicitHs`（括号显式氢）**
按级差消耗；**隐式氢不动**（注释明写"隐式 H 由 sanitize 按剩余价自动重算"），
真实超价**由 sanitize 诚实拒** ⇒ `edit_execution_failed:sanitize_failed:
AtomValenceException:edit[last]`。

⇒ **对普通 SMILES（隐式氢）做 `change_bond_order` 升键级（如醇 C–O single→double 的氧化），
必然撞价态墙**——除非底物写成 `[CH3]CO` 这种括号氢形式。
提示词**没有**任何氢/价态说明，也**没有**"脱氢"操作（`real_model.py:179-180` 只讲
add_atom / form_bond）。
**本批 12 题命中这个拒因**（其中 3 题仍 hit ⇒ 是单条候选执行失败，不是整题零答案）。

⇒ **提分方向：把"键级变化所需的脱氢"做成显式可表达的操作或显式的氢预算**，
而不是让模型靠猜括号氢。

**(b) 芳香键：模型看到的是 Kekulé 形式，不是 aromatic 词**

执行图先 Kekulize 再渲染（`real_model.py:352-355`），所以模型看到的是
交替 single/double；`capability.unsupported` 明列 `aromatic_bond_tokens`
（`:399-400`）—— 即**模型不能写 "aromatic" 作为键级词**，只能在系统给定的那一套
Kekulé 形式上编辑。
**注意（避免误读）**：这**不是**"模型不能改芳香键"，而是"模型必须在系统给的那一套
Kekulé 形式上改"。**副作用**：模型若在芳香环上改键级，最终 `SanitizeMol` 要么重新芳构化、
要么产出**去芳构化**产物 —— 属于化学质量风险，不是结构性拒。

> 这条与 §2.3 的"立体硬天花板"同族：**编辑协议只有四个操作**
> （`break_bond` / `form_bond` / `change_bond_order` / `add_atom`，`atom_tool.py:73`），
> **既不能设立体、也不能表氢、也不能说 aromatic** —— 模型的可表达空间比看起来窄得多。

### 4.7 三条容易读错的口径（读数纪律）

| 叙述 | 实际 | 位置 |
|---|---|---|
| "每题 1 次模型调用" | **上限是 3**（`max_real_model_requests=3`）+ 格式反馈轮 ≤2；`1` 只是编排器缺省值，被发车 profile 覆盖；"每题 1 次"是**涌现事实**（298 请求行 / 298 题） | `s5b_orchestrator.py:102-118`（缺省）vs `scripts/hpc/chain13_run_wrapper.py:25-34`（实发）；`orchestration.json`（冻结 3/2） |
| "deferred 是候选被挤掉了" | **本批 deferred 主要是深度上限产物**（`max_search_depth=1` ⇒ 所有 followup 全 defer），**不是** alternatives 额度；全批只有 **2** 个 expand 动作被 `alternatives_budget` 拒 | `production.py:1191-1208`；`queue.py:670-681`；实测见 §3 探针 |
| "模型排了序" | 模型**不写** `rank_hypotheses` 时**自动补 = 提案顺序** ⇒ `rank_basis=model_selection` 里有一部分是名义上的 | `model_protocol.py:223-225` |

---

## 5. 分级行动清单

> 编号即建议执行顺序。**每条都写明：机制 → 代码位置 → 上限 → 证据强度 → 风险。**
> 「上限」是数学上限或程序口径上限，**不是收益承诺**。
> **红线提醒**：判据面改动（criteria 版本）属**用户/老师裁定**事项，
> 生成侧改动不涉及判分，但**必须按 §8 的顺序走（任务书 → 评审 → 实施）**。

### 5.1 【A 档：零模型、零判分改动、几天内可做】—— 先把"已经做对的事"记下来

| # | 动作 | 机制 | 代码位置 | 上限 | 证据强度 | 风险 |
|---|---|---|---|---:|---|---|
| **A1** | **候选级归因披露**：把 `rank_basis` / `model_rank` / `effective_rank` / `dedup_rejections` / `folded_model_rank` 落到 `native_result` 与 `native_export` 的**题级**产物 | 现在题级产物里**没有** `rank_basis`、没有 `dedup_rejections` ⇒ T-F 位次继承"0/298 触发"与"能否重排"**都不可测** | `runflow.py:1144-1150`（字段已在 action payload 里，只是没进题级产物）；`native_result.py` / `native_export.py` | 不直接提分 | **可证**（当前不可测就是证据） | 零：纯披露字段 |
| **A2** | **`no_alignment` 拆码**：F5 跳过 / F3 wildcard 拦 / 编译器真无对齐分列 | 漏斗分母现在被污染，`compile_failure_histogram` 不可用于归因 | `s5b_builder.py:1376-1391`（`_emit_rejected`）、`:1761` | 不直接提分 | **可证**（同码多义） | 零：仅诊断口径 |
| **A3** | **remap 披露加/减拆分**（`n_added_maps` / `n_removed_maps` / `side`） | remap-only（17 题 / 5.88%）与 remap+add 面的差异**目前只能离线重建** | `s5b_compiler.py:1538-1547`（`_template_remap_disclosure`） | 不直接提分 | **可证**（现有字段不足） | 零：纯披露字段 |
| **A4** | **参与物画像披露**：每题事件级 `n_reactant_participants` / `n_product_participants` / `n_coproduct` / `participant_list_status` | 缺口 A 的 52 题，**当前无法在题级区分"缺参与物"与"多参与物"** | 事件 payload 已有 `participants`；缺的是题级聚合披露 | 不直接提分 | **可证** | 零：纯披露 |
| **A5** | **通道构成披露**：每题候选按 recorded / template / novel 计数 + 各通道位次分布 | 缺口 B/C 的核心量（30.5% 覆盖率、86.7% novel 占比）**目前只在离线探针里**，不在批产物里 | 同 A1 | 不直接提分 | **可证** | 零 |

> **A1–A5 合起来 = 把"下一次归因"从 3 天的人工考古变成 1 小时的读表。**
> **本报告的其余所有结论都会因此变成可日常监控的指标。** 建议**先做这一档**。

### 5.2 【B 档：生成侧规则改动，单变量 A/B 可验】—— 不碰判据就能提分

> ⚠️ **B7 例外**：它是**效度修复**而不是提分项，方向可能向下（诚实化）。
> 见 §4.5 与 §8 第 3 条。

| # | 动作 | 机制 | 代码位置 | 上限 | 证据强度 | 风险 |
|---|---|---|---|---:|---|---|
| **B1** | **通道先验排序**：`effective_rank` 里给 recorded 通道一个**可配的先验档位**（例如 recorded 恒占第 1 槽，模板/模型在其后），模型的显式位次只决定**同档内**次序 | 模型把自由提案排第一时 hit@1 24%；recorded 排第一时 49%。当前**完全没有任何通道先验** | `runflow.py:1089-1103`（effective_rank 分配）+ 队列 `queue.py:211-215` | **≤14 题**（chain14 A 中 recorded 在场但未排第一的题数）；链上更大 | **中**（关联，非因果；A/B 可验） | **高**：可能把对的 novel 挤下去 ⇒ **必须单变量 A/B + 预注册**，不能拍脑袋 |
| **B2** | **副产物最小化**：编译/提案侧**不产出参考侧不会有的产物侧副产物**（`_split_components` 的 coproducts 与模型 `coproducts` 字段）；产物侧只留主产物 | partial 桶 **40/43 是 superset_with_coproduct** ⇒ 多一个副产物 = 掉一档 | `s5b_compiler.py:1747`（`_split_components`）→ spec `coproducts`（`:1752`）；`production.py:527-530`；`real_model.py:144`（池提案可选 `coproducts`）/ `:156`（novel 的 `coproducts` 标注 optional） | **≤53 题**（partial 全桶），实际只有副产物是"多余"的那部分 | **中**（40/43 是 chain12 口径；T-H 需复测） | **中**：副产物有时是化学必要的（如脱羧放出 CO₂）⇒ **不能一刀切**，需按"副产物是否为必要脱离去向"分档 |
| **B3** | **候选列表头部位次改为"确定性优先 + 模型排序"**（不是把 recorded 硬塞第 1，而是让**模型排序只在同通道内生效**，跨通道用先验） | 同 B1，但比 B1 温和 | 同 B1 | 同 B1 | 中 | 中 |
| **B4** | **产物侧质子化/互变异构约定与底物对齐（生成侧，弱）**：提示词与装配侧约束"产物沿用底物的质子化/互变异构书写约定"，减少模型自由改写酸式/盐式 | 缺口 A 里"质子化 6 题"是**同一分子的书写差**；模型被告知电荷按底物书写（`real_model.py:191`），但产物侧无强制 | `real_model.py:135-193`（提示词契约段）、`production.build_product_state`（`:139`） | **≈6 题**（chain12 口径） | **低-中**（约定对齐 ≠ 归一；**单侧归一无效**，见下注） | 低 |
| **B4′** | **归一化必须两侧同源**（⚠️ 与 B4 配套的硬约束） | 严格身份键**不做**电荷归一（`chemstate.py:180-226`），而 `cn_identity` 是**电荷归一 + 立体盲**的复合键 ⇒ **单侧归一不会改变 strict 比较结果**；要让归一生效，必须参考侧与预测侧**同一算子、同一参数**同时归一 —— **那属于判据变更（见 C1），不能由生成侧单方面做** | `domain/identity.py:46`；`chemstate.py:180-226`；`evaluation.py:2274-2279` | — | **可证**（代码口径） | **高**：越界即变成暗改判分 ⇒ **必须走 C1 流程** |
| **B5** | **立体可表达性**：给编辑协议加一个**受控的立体设置操作**（或至少允许模型在提案里带**立体标记的 product_smiles**，由 AtomTool 复验） | 21 题"纯立体差"是 novel 通道的**结构性天花板**：协议四操作里没有一个能设立体 | `services/atom_tool.py:73`（`_EDIT_OPS`）、`:322`（`validate_edits`）、`:405`（`execute_edits`）；`real_model.py:135-193`（提示词契约段）；`controlled_vocab.py`（词表单一来源） | **≤21 题**（chain12 口径） | **中**（分类已做，但落到 edit 协议是设计工作） | **高**：涉及化学正确性 ⇒ **必须走 mimo 场景 1（判据级）+ Codex 复审**，且词表/提示词/执行器三处同步（`tests/test_controlled_vocab_ci.py` 已是这个约束） |
| **B6** | **recorded 通道的"拷贝组分"参与物口径复核（含一处文档/代码矛盾）** | `recorded_source.py:2756-2758` 把**拷贝组分也挂成 `product/coproduct` 参与物**；而参考图 `to_node_ids` 只有主产物 ⇒ **superset ⇒ partial**。⚠️ 但 `production.py:368-370` 的契约 docstring 明写拷贝组分"**不进 Participant 字段**" —— **文档与代码口径相反**，需先定性再动 | `recorded_source.py:2745-2758`；`production.py:362-370`（docstring）；`production.py:577-580`（copy_states 进 states 与 product_states） | 与 B2 同族 | **低-中**（矛盾是事实；哪个口径对是化学问题） | 中 |
| **B7** | **答案-变换对账门**：新增一道"**声明产物 == 执行产物**"的检查（先做成**披露**，再决定是否硬门） | 事件产物取自 spec 声明，执行产物从未对账（§4.5）⇒ 模型可声明任意产物 SMILES 而 edits 产生别的结构 | `production.py:1187-1190`（事件产物）、`:1004`（执行产物）、`:129`（`ADMISSION_SUBMITTABLE`）；`audit.py:2746-2768` | 方向**不确定**（可能掉分也可能涨分）⇒ **只能当"效度修复"立项，不能当"提分项"立项** | **可证**（机制）；占比 unknown | **高**：这是"改口径"性质 ⇒ **必须老师知悉 + 单变量 A/B**；先做披露档，别一步到硬门 |
| **B8** | **氢预算 / 脱氢可表达**：把 `change_bond_order` 升键级所需的脱氢做成**显式氢预算或显式操作**，并在提示词里说明氢记账语义 | 价态墙：`change_bond_order` 只扣括号显式氢 ⇒ 隐式氢底物做升键级**必撞** `AtomValenceException`；本批 **12 题**命中该拒因 | `atom_tool.py:486-503`（显式氢记账）；`real_model.py:179-180`（提示词无氢/价态说明） | **≤12 题**（本批 method_failed 题数；实际可救数 unknown） | **中**（拒因与题数可证；可救数 unknown） | **中**：改的是编辑协议语义 ⇒ 需 mimo 场景 1 + 词表/提示词/执行器三处同步 |

> **B6 附注（重要，影响 B2 的可行性）**：拷贝组分/共底物的声明触发**只挂在 D2 组件分支**
> （`production.py:612-620`："whole/EAWAG spec 两处均无声明"）⇒ **B2"副产物最小化"
> 不能一刀切**，必须先按"记录侧是否声明"分层，否则会把合法的共底物语义一起砍掉。

### 5.3 【C 档：需要判据/预注册裁定，属用户与老师决策】—— 上限最大但不是工程单方面能定

| # | 动作 | 机制 | 上限 | 为什么必须裁定 |
|---|---|---|---:|---|
| **C1** | **criteria-v3 的 B 轴从"披露"升为"可升格"**（互变异构 / 质子化归一后允许升 strict） | v3 **已经实现** A/B 两轴归一，只是冻成 `strict_promotion = false`；**T-H 本批实测 23 个节点对（互变 13 + 质子化 10）归一后相等但被判死** | **≤23 题**（T-H 原生机读；chain12 代理口径 20 题） | 判据变更 = **判分口径变更** ⇒ 走 criteria 冻结流程 + 老师批复。**v3 冻结文档里 tier B 本来就是"未来解锁门槛"，本条等于把它打开**；且归一必须**两侧同源同参数**（见 B4′），不能只改一侧 |
| **C2** | **T1′（coproduct_ignore 档）实施** | 未声明的多余产物**恒 partial**（`evaluation.py:882-887` 明文未实施） | **≤40 题**（partial 桶 40 题的 superset_with_coproduct） | 判据面；且 T1′ 要解决的是"主产物 vs 副产物角色不区分"（`S5B_KNOWN_GAPS` 已登记 `principal_vs_coproduct_undistinguished`）⇒ 需要化学裁定 |
| **C3** | **立体轴的一个受限档**：只对"同连接 + 仅立体标记缺失/相反"开一个**受限 strict 档** | 21 题纯立体差 | **≤21 题** | 判据面 + 化学裁定；且与 C1 互斥性要一起设计（v3 A 轴默认臂已把消旋当负控失败，不可 strict-eligible，`evaluation.py:1055-1059`） |
| **C4** | **`participant_list_status = "partial"` 被消费**：参考侧自认清单不完整时，判分侧不要求**集合恰好相等**，改要求"包含关系 + extras 可解释" | `edge.participants` 只披露不比较；`participant_list_status` 从不被读取 | 可能覆盖 partial 桶相当一部分 | 判据面；**这是"放宽还是换尺"要老师拍板的事** |
| **C5** | **参考侧 `from_node_ids` 空集边的处置** | 空 from 侧 ⇒ `reactants == from_states` 永不成立 ⇒ 该边**永久 partial**（mimo r22 C5） | 未知 | 判据面 |

### 5.4 【D 档：真正的产能工程（重、慢、要钱）】—— 缺口 B 的正面解法

| # | 动作 | 说明 | 规模感 |
|---|---|---|---|
| **D1** | **扩大 recorded/corpus 召回** | 现在 **207/298 题（69.5%）没有 recorded 候选**；recorded 在场时 hit@1 是 44–49%，不在场时 24.6%。这是**单点最大差距** | 需要查：语料覆盖？检索键？编译拒因分布？（A2/A3 是它的前置） |
| **D2** | **提高模板编译产出率** | 每题 19 个原始 spec → 0.78 个编译成功 | 要按 A2 拆码后的 histogram 定位是哪一层门在吃 |
| **D3** | **模板资产侧补映射** | remap 只能补**编号**不能补化学；`transform_no_change` 时代（chain12 直编 0/56）说明**模板资产本身映射不全** | 资产工程，不是代码工程 |
| **D4** | **候选宽度与深度** | `max_alternative_hypotheses_per_parent = 8` **不是瓶颈**（chain14 A 全批只有 **2** 个 expand 动作被 `alternatives_budget` 拒；`max_total_search_actions = 48` 只用了 8）。**这条明确不是杠杆** | — |
| **D5** | **模型调用数** | `max_real_model_requests = 3` + 格式反馈轮 ≤2（**注意：缺省值是 1/0，被发车 profile 覆盖成 3/2**；"每题 1 次"是涌现事实）。实测 **294/298 题只用了 1 次**、2 题用 2 次 ⇒ **模型预算不是瓶颈，格式反馈轮几乎不消费** | — |

---

## 6. 明确**不要**做的方向（附反证）

| 方向 | 反证 |
|---|---|
| **打开证据卡 v1** | chain14 同批 A/B：**B−A hit@1 = −6**，目标面 −2，input token +26%（`CHAIN14_EVIDENCE_AB_RESULT_2026-10-16.md`）。**且 v2 的裁剪还没写**（§4.4）⇒ 直接开卡只会重现 v1 |
| **"证据卡 v2 可以直接开"** | v2 冻结裁剪**一条未实施**：Gasteiger 仍在、FG 数组仍在、卡内 source 四字段仍在、无 FG delta、无 token 门 ⇒ 现在开卡 = 开 v1 |
| **"每题 1 次调用是上限"** | 上限是 **3**（+ 反馈轮 2），`1` 只是缺省值被发车 profile 覆盖（§4.7） |
| **"deferred 是候选被挤掉了"** | 本批 deferred **主要是深度上限产物**（depth=1 ⇒ followup 全 defer），全批只有 **2** 个 expand 被 `alternatives_budget` 拒 ⇒ **deferred 计数不是"缺面"证据** |
| **"把 60 个空池题当 60 个损失"** | 60 空池里 **20 题 hit@1（33.3%）**，高于非空池的 29.0%；本批未命中的空池只有 **40 题**（`T_H_R2_HIT1_LOSS_ATTRIBUTION` §0） |
| **"21 题身份门 = 21 题损失"** | 21 题里只有 **1 题**从 chain13 hit 退化，其余 19 题本来就不是 hit |
| **"把 v1 命中题丢了"** | 209 个 v2 未命中里 v1 命中 = **0**；v2 是 v1 的**超集** |
| **"给预测侧加反应物侧共底物"** | 参考图 `from_node_ids` **永远只有底物**（`s5b_builder.py:271`）⇒ 多一个反应物 = superset = **partial**。**加了会掉分** |
| **"提高候选宽度 / 模型调用预算"** | alternatives 预算全批只拒了 **2** 个；模型请求 294/298 只用 1 次 ⇒ 这两个旋钮**没在瓶颈上** |
| **"用位次重排当第一杠杆"** | 位次杠杆上限 37 题（12.4pp），但**产品 any-of 漏斗是 52 题（17.4pp）且跨四批稳定** ⇒ 优先级应更高（但两者**不互斥**：重排要靠 A1 披露才能定位） |
| **"remap 导致丢分"** | 关联非因果，无同题 A/B；remap 题集本身可能更难（`T_H_R2_HIT1_LOSS_ATTRIBUTION` §3.3 已如此标注） |
| **"strict 覆盖 126 ≈ hit@1 126"** | 37 题 strict 但非首位；U=126、H5=125、L=1，排序损失真实存在 |

---

## 7. Unknown 清单（缺什么，不估算）

| # | unknown | 影响 | 缺什么 |
|---|---|---|---|
| 1 | **T-H 批的通道构成** | 缺口 B/C 的 30.5% / 86.7% 目前是 **chain14 A/B** 读数；T-H 本地镜像无 run 库 | HPC 上 T-H 的 `pollutant.sqlite`（只读拉回） |
| 2 | **52 题缺口在 T-H 上的形态分布** | partial/unmatched 的 27/24 拆分已知，但"superset_with_coproduct"在 T-H 未测 | chain12 同款逐事件复算产物（T-H 需重跑 `scripts/s5b_offline_rescore.py` 同口径） |
| 3 | **候选级金标匹配** | 不能说"误拒"还是"候选本身不对"；B1/B2/B4 的收益上限都卡在这里 | 逐事件金标匹配明细（判分侧产物） |
| 4 | **remap 因果** | 只能给关联 | 同题非 remap 对照 / A/B |
| 5 | **位次重排可实现性** | 37 题上限可证，兑现多少 unknown | `rank_basis` / `dedup_rejections` / 逐事件有序 rank（**= A1**） |
| 6 | **立体差在 T-H 的当前规模** | 21 题是 chain12 口径；**T-H 的 v3 披露只给互变/质子化数（13/10），没给"纯立体差"数** | 同 #2 的复算产物 + v3 披露补轴 |
| 7 | **互变异构/质子化归一在生成侧的效果** | 6 题是 chain12 口径 + 推演 | 同 #2 + 生成侧探针 |
| 8 | **recorded 通道在 207 题上为何缺席** | 缺口 B 的正面解法（D1）完全取决于此 | 检索命中层 + 编译拒因拆码（**= A2**） |
| 9 | **单人批泛化** | 298 已见题 post-hoc；不外推新题 | 重复批 / 新题 |
| 10 | **答案-变换脱钩的规模** | 机制已证实（§4.5），但**不知道有多少题的事件产物与其 edits 实际产物不一致**，也不知道其中多少是靠这条拿到分的 | 事件级"声明产物 vs 执行产物"对账计数（**= B7 的披露档**） |
| 11 | **价态墙的可救规模** | 12 题撞 `AtomValenceException`，但其中几题撞墙后**还能靠别的候选命中**（3 题仍 hit）⇒ 可救数 unknown | 同 #2 的复算产物 + 逐候选执行失败明细 |
| 12 | **`retain_conditional` 的实际放行量** | 45 题有 audit `violated` 记录，12 题仍 hit ⇒ 但"其中几题是脱钩造成的"unknown | 准入处置分布 + 事件级对账（同 #10） |

---

## 8. 建议的落地顺序（一句话版）

1. **先 A 档（A1–A5）**：把"下一轮能自动归因"的地基建起来。零风险、几天。
   **A1 建议扩一条：把"事件声明产物 vs 执行产物"的对账结果一并披露**（即 B7 的披露档）
   —— 它同时服务于缺口 D 的量化。
2. **再 B 档低风险项（B2、B8）**：副产物最小化 + 氢预算/脱氢可表达。
   方向明确、不改判据、单变量 A/B 可验。（**B4 可搭车做**：成本低，但预期也低。）
3. **B7 单独走"效度"立项**（不是"提分"立项）：先做披露档拿数，
   再决定是否上硬门；**必须老师知悉**，因为它可能让分数掉。
4. **B1/B3/B5 单独立项**：排序先验（必须 A/B + 预注册）、立体可表达性
   （必须走 mimo 场景 1 + Codex 复审 + 词表/提示词/执行器三处同步）。
5. **C 档全部上呈老师/用户裁定**：判据口径变更不是工程单方面能定的
   （C1/C2/C3/C4/C5）。**先呈报，本报告不代拍。**
6. **D 档在 A2/A3 出数后再排期**：缺口 B 的解法取决于拆码后的漏斗分布。
7. **证据卡**：**暂不开**。要开必须先实现 v2 裁剪（§4.4），否则等于重跑 v1 的负结果。

---

## 9. 证据路径与复现

**本文自算/自测产物（仓内 gitignored 目录）**

| 件 | 位置 |
|---|---|
| 通道/位次探针脚本 | `reports/ppv1_s5b/opt_probe_2026-10-20/probe_channels.py` |
| 探针输出 | `reports/ppv1_s5b/opt_probe_2026-10-20/summary_chain14_{a,b}.json` |
| T-H 本地镜像 | `reports/ppv1_s5b/t_h_2026-10-20/r2/`（`metrics.json` / `.v1` / `.v2` / `.v3` / `batch_report.json` / `p2_face_measure.json` / `orchestration.json` / `profile_policy.json` / **`criteria_v3_disclosure.json`**） |
| chain13 / chain14 镜像 | `reports/ppv1_s5b/chain13_glm/` / `chain14_a/` / `chain14_b/` |
| chain12 逐事件归因 | `reports/ppv1_s5b/chain12_s5b_298_v4b_20261012/analysis/`（`funnel_chain12_summary.md` / `hbucket_attribution.md` / `partial_breakdown.json` / `cnonly_repr_classification.md`） |

**复现命令（只读；零模型零判分重算）**

```bash
cd /Volumes/CC/Enzyme_Agent/dependingv43
PYTHONDONTWRITEBYTECODE=1 python3 reports/ppv1_s5b/opt_probe_2026-10-20/probe_channels.py
```

**上游文档**

- `docs/T_H_R2_HIT1_LOSS_ATTRIBUTION_2026-10-20.md`（本轮 T-H 丢分归因）
- `docs/REPLY_TO_TEACHER_HUANG_T_H_2026-10-20.md`（T-H 结果交付 + 任务七）
- `docs/CHAIN14_EVIDENCE_AB_RESULT_2026-10-16.md`（证据卡 A/B 负结果）
- `docs/CHAIN14_ATTR_PROBE_RESULT_2026-10-17.md`（证据卡负结果机制归因）
- `docs/TASK_EVIDENCE_CARD_V2_DESIGN_2026-10-17.md` + `docs/EVIDENCE_CARD_V2_DESIGN_CODEX_FINAL_2026-10-18.md`（证据卡 v2 设计冻结；**明示未实施**）
- `docs/POLLUTANT_PATHWAY_CRITERIA_V2_PREREGISTRATION_2026-10-13.md`（参与物豁免三谓词）
- `docs/POLLUTANT_PATHWAY_CRITERIA_FROZEN_V3_2026-10-19.md`（A/B 归一轴，披露档）

**红线自查**：本文未改任何源码、未改判据、未调模型、未读金标 / 题面 /
`reference_graphs` 结构正文；所有数字带 298 题域标签；chain12 / chain14 派生读数
**已逐处标注来源批**，未与 T-H 混算；上限均标注为上限而非收益。
