# T-H P3 O4：F3 wildcard 化学边界与政策选项（2026-10-21）

> **题域标签：[298 域] = RHEA 通用酶学 / 已见题（post-hoc）。**
> 本文所有题数、候选行数、模板数、比例只在该题域成立；与 dev（B1 环境路径
> 中间步骤）双向不外推，也不外推到新题、新批次或其它题域。
>
> **性质：只读规则级分析 + 化学评审请求稿。** 零模型调用、零付费、零代码改动、
> 零金标/题面/`reference_graphs`/`env`/key/封存逐题 run 读取；不连 HPC；不 push；
> 不碰 T-I 锁定文件；不碰 P2 工作树。唯一改动 = 新增本文件与
> `docs/P3_F3_WILDCARD_CHEM_REVIEW_REQUEST_2026-10-21.md` 两个文档。
>
> **成本口径：** 本报告零模型、零付费，但“零模型 ≠ 零成本”；新测量仍要计算、
> 存储与工程时间（`docs/T_H_HIT1_OPTIMIZATION_PLAN_2026-10-20.md:115`）。
>
> **一句话结论：** `wildcard_blocked` 挡的不是“中心缺失”，而是**“要供给的共底物
> 组分含未定义元素（原子序数 0 的 dummy/R 基团），供给规则没有化学身份可填”**。
> 178 条里 0 条能离线判成“真实缺中心”；85 条（76 确定 + 9 可能）连编译器的
> 中心查询都含 dummy，
> 只能靠模板实例化、不能靠供货层替换；50 条是唯一有化学讨论价值的
> spectator `XH2` 类，但“`XH2` = 水”不是模板能推出的规则。**推荐 A（维持现状）；
> B 只作为条件性预注册试点（仅 B1：spectator `XH2`）；C 否决。**

---

## 0. 出处、测量定义与读法

### 0.1 出处缩写

| 缩写 | 文件 / 对象 | 用途 |
|---|---|---|
| `[P3]` | `docs/T_H_P3_SUPPLY_TRIAGE_2026-10-21.md` | 供给漏斗分项诊断；178/52/277、992 修正、O4 立项 |
| `[DP]` | `docs/T_H_P0_DECISION_PACK_2026-10-20.md` | P0 决议包；1585 拆分与 F3 旧标签 |
| `[PLAN]` | `docs/T_H_HIT1_OPTIMIZATION_PLAN_2026-10-20.md` | 优化计划 §4 P3（149-162）与 §6（181-195） |
| `[LEVER2]` | `docs/T_H_TEACHER_LEVER2_REMAP_AUDIT_2026-10-21.md` | remap/供给面现状；339 行仍有 992 旧标签 |
| `[P0D]` | `docs/review_evidence/t_h_p0_2026-10-20/p0d_supply_funnel.json` | 冻结的 P0-D 聚合证据（SHA256SUMS 成员） |
| `[WL]` | `/tmp/th_pool_diag.json` | P0-D 脚本输入副本；**不是 SHA256SUMS 成员**；本文只用于逐候选行重算 |
| `[TPL]` | `assets/analog/corpus_templates_v1.jsonl` | T-H r2 实际使用的 analog 模板资产；SHA256 与批 `build_identity` 一致 |
| `[BID]` | `reports/ppv1_s5b/t_h_2026-10-20/r2/build_identity.json` | 批资产身份；2-8 行 |
| `[METRICS]` | `reports/ppv1_s5b/t_h_2026-10-20/r2/metrics.json` | 逐题桶/rank；只读、无化学串 |
| `[CODE-B]` | `src/pathway_v43/pollutant/s5b_builder.py` | 池构建、F1-F5 路由、供给与诊断 |
| `[CODE-C]` | `src/pathway_v43/pollutant/s5b_compiler.py` | 中心查询、编译、remap |
| `[CODE-P]` | `src/pathway_v43/pollutant/production.py` | 执行输入/事件级核验 |
| `[TEST-S]` | `tests/test_ppv1_s5b_cosub_supply.py` | wildcard 供给契约测试 |
| `[TEST-C]` | `tests/test_ppv1_s5b_c2_center_anchor.py` | F3 先于 F5/直编的路由测试 |

**代码阅读 HEAD：** `966bc5664a7daa30f24860d2b5594a9dddc6eee2`（2026-10-21）。
与 `[P3]` 的代码快照 `11aeeafded1b41185f24de49767933709aad49db` 相比，
`git diff --stat 11aeeaf..HEAD -- src/pathway_v43/pollutant/s5b_builder.py
src/pathway_v43/pollutant/s5b_compiler.py` **为空**；本文的代码判据引用对两个 HEAD
都成立。

**资产身份（A）：** `[TPL]` SHA256 =
`8f3f2c1ac0cb17501e6a6f2ab65c22ae9e1768a3f1e8e4227b8305ba5ccfad92`
（`shasum -a 256`），与 `[BID:2-5]` 的
`analog_corpus=v1` / `analog_corpus_file=analog/corpus_templates_v1.jsonl` /
`analog_corpus_sha256` **逐字节一致**。该文件 17,183 行、17,035 个唯一
`record_id`（离线计数）。

### 0.2 测量定义（本文所有派生数字都挂在这里）

| 标签 | 测量 | 输入 | 判定级别 | 说明 |
|---|---|---|---|---|
| **M1** | F3 候选行选择：`channel=analog` 且 `reason` 前缀 `no_alignment` 且 `f5=not_evaluated` | `[WL]` | D1（重算；`[WL]` 非冻结成员） | 得 178 行 / 52 qid；与 `[P3:138,219]` 一致 |
| **M2** | `record_key` 去 `tpl-` 后与 `[TPL].record_id` 精确连接 | `[WL]` + `[TPL]` | A（模板资产哈希匹配批身份）/ D1（行选择） | 178/178 行、72/72 模板全部匹配；无重复模板行 |
| **M3** | 逐模板/逐组分结构画像：组分重原子数、dummy 原子数/度/显式 H/邻居元素、环数、芳香原子数、元素多重集、dummy 是否在 `mapped_rhs` | `[TPL]` | A（只读结构解析，RDKit 2026.03.6） | 不输出 SMILES；只出聚合计数 |
| **M4** | 编译器 L1/中心查询成员：`extract_mapped_transform` + `l1_maps_of_transform`（`[CODE-C:357,769]`）；`build_center_query` 的 `shell=2` 保留集（`[CODE-C:817-857]`） | `[TPL]` | A（调用冻结 helper，只读，不写库） | 7 个模板 `transform_no_change` 抛错，单列 |
| **M5** | 非 dummy 重元素账：去掉原子序数 0 的原子后，`rhs - lhs` 的元素差 | `[TPL]` | A（RDKit 元素计数） | 只出 `{}` 或元素差计数，不出结构串 |
| **M6** | 52 个 F3 qid 的桶/rank | `[METRICS]` | D1 | 与 `[P3:88,219,448]` 的 26/35/2/15 一致 |

**读法纪律：**

1. `[WL]` 不是 `SHA256SUMS` 成员。若只认官方冻结 SHA256 成员，本文的
   qid/事件/模板级数字应写 `unknown`；候选级聚合（178/52）仍由
   `[P0D]` 支持（`[P0D:243,248]`；`[P3:110,219]`）。本文把 M1-M6 标为“重算/只读测量”，
   不冒充冻结证据。
2. `[WL]` 的候选行字段只有
   `channel/outcome/reason/f5/record_key/execution_input_source/merged_into/
   pool_rank/light_gap_coverable_by_bag/record_side_form_norm`（离线键枚举）；
   **没有底物 SMILES、没有题面、没有金标、没有 `signature_head`**。本文不输出任何
   化学结构串/反应式/题面文本。
3. `[TPL]` 是批实际使用的模板资产（哈希匹配），不是金标/题面/`reference_graphs`；
   读取它是为了规则级结构画像，不是为了看答案。
4. **992 不是 F3。** 本文只用 **178 条候选行 / 52 题 / 277 题内事件**
   （`[P3:138,219]`）。`992` 是 `analog_pregate_skipped` 计数器
   = 178（F3）+ 407（供给分支 F5 absent）+ 407（no_supply 分支 F5 absent），
   与 864 重叠 814，禁止相加（`[P3:123-143]`）。`[DP:31-32,127-128,234-235]`
   与 `[LEVER2:339]` 仍写“F3 992”，是 P3 修正前的旧标签；本文以
   `[P3:123-143]` 与字段/代码为准，不回写既有文档。
5. **277 事件是上下文分母，不是 F3 直接事件。** 被拒候选的直接事件 = 0
   （拒因发生在事件之前）；277 是这 52 题在 T-H r2 已提交的事件数
   （`[P3:210-212,219]`）。本文不用它推收益。

### 0.3 证据强度

| 级别 | 含义 |
|---|---|
| A | 机械事实：代码 + 哈希资产 + 计数确定性闭合 |
| B | 只读离线测量可判定，但尚未做全量回放 |
| C | 只能支持关联；无同题反事实 |
| D | 无直接证据，保持 unknown |

> D0/D1/D2/D3 沿用 `[P3:50-57]` 的定义：D0 = 官方冻结 SHA256 证据可直接判定；
> D1 = 需用 `[WL]` 重算（非冻结成员）；D2 = 需新的只读资产/编译回放测量；
> D3 = 需化学评审、金标或模型运行。本文的 M1-M6 多数是 D1；模板资产哈希匹配
> 批身份的部分是 A；化学可替换性是 D3。

---

## 1. Q1：`wildcard_blocked` 的精确语义

### 1.1 触发链（代码事实，A）

F3 只挂在 **analog 通道、F1 拒之后的供给路由**。完整链：

1. **F1 路由**（`[CODE-B:1449-1452]`）：`gate_raw = template_elements_fit(lhs, substrate)`。
   - F1 过 ⇒ 直编分支（`direct_raw`）：F5 → 编译；**不调用 F2/F3**
     （`[CODE-B:1452-1492]`）。
   - F1 拒 ⇒ 进入 F2 供给计算（`[CODE-B:1493-1496]`）。
2. **F1 对 dummy 的计数方式**（`[CODE-C:258-264]`）：`lhs_elems[a.GetSymbol()]`。
   RDKit 对原子序数 0 的 dummy 返回符号 `*`；正常底物没有 `*` 元素，所以
   **任何含 dummy 的模板在正常底物上都必然 F1 拒**，走 F1 拒路由。这是“F3 在效果上
   先于 F5/直编”的机械原因，不是“模板含 wildcard 就一律 F3”（见 §1.4 的 48 行反例）。
3. **F2 供给计算**（`[CODE-B:640-714]`）：
   - `len(lhs_comps) <= 1` ⇒ `no_supply`（`[CODE-B:674-677]`）；
   - 主组分 = 与底物 Tanimoto 最大者；并列取后位；全不可解析时回退重原子数最大
     （`[CODE-B:679-687]`）；
   - 主组分 `cn_identity` 不可解析 ⇒ `no_supply`（fail-closed，
     `[CODE-B:688-692]`）；
   - `supply` = lhs 组分**按位置扣除选定 `main_idx` 那一份**后的全体，
     原序、精确多重集（`[CODE-B:693-704]`）；
   - `supply` 为空（纯主单组分袋）⇒ `no_supply`（`[CODE-B:705-707]`）；
   - **`supply` 中任一 stripped 组分含原子序数 0 的原子 ⇒ `wildcard_blocked`，
     整袋不供给**（`[CODE-B:708-712]`）。
4. **`_cosub_has_wildcard_atom`**（`[CODE-B:571-587]`）：
   - 能解析：`any(atom.GetAtomicNum() == 0)` 为真 ⇒ wildcard；
   - 解析失败：回退串面 `"*" in text`（“坏组分由编译层结构化拒，此处不猜结构”）。
   - 覆盖形态包括裸 `*`、`[H]*[H]`、`*C=O` 等**含 dummy 原子**的组分；
     不是只认裸 `*`（P2-WILDCARD-01 回退后的冻结边界，`[CODE-B:571-576,656-662]`）。
5. **F3 分支**（`[CODE-B:1499-1517]`）：
   - `analog_cosub_supply_wildcard_blocked += 1`；
   - `analog_pregate_skipped += 1`；
   - 发候选行：`route="wildcard_blocked"`、`f5="not_evaluated"`、
     `execution_input_source=None`、`reason="no_alignment"`、
     `record_side_form_norm.unknown_reason="wildcard_blocked:not_consumed_by_alignment"`；
   - **不调用 F5、不发编译、不产生执行输入**；直接 `continue`。
6. **供给分支**（`[CODE-B:1518-1532]`）只有在 `status="supply"` 时：
   `sub_supplied = substrate + "." + ".".join(supply)`，再做 F5、
   `compile_donor_template`。F5 absent ⇒ 仍记 `no_alignment`；
   F5 defer/pass ⇒ 发编译；编译失败按真实拒因记（`[CODE-B:1523-1590]`）。
7. **no_supply 分支**（`[CODE-B:1592-1605]`）：F4 = raw，F5 在 raw 上判；
   F5 absent ⇒ `no_alignment`；否则发编译。

**状态机（`[CODE-B:667,708-714]`）：**

| `status` | 触发条件 | F3 是否拦截 | 后续 |
|---|---|---|---|
| `no_supply` | lhs ≤1 组分；主 cn 不可解析；supply 为空 | 否 | raw 上 F5/编译 |
| `wildcard_blocked` | supply 非空且任一供给组分含原子序数 0 | **是，整袋** | 不 F5、不编译、记 no_alignment |
| `supply` | supply 非空且全部组分无 dummy | 否 | 加袋成 F4 → F5 → 编译 |

### 1.2 它挡的是什么：一句话

**它挡的是“供给规则未定义”，不是“化学上证明不该供给”。**

- 执行输入必须是**具体分子**。`analog_cosub_supply` 的供给清单要并进底物侧
  形成 `sub_supplied`；如果某个供给组分含原子序数 0 的 dummy，这个组分没有
  元素、没有价态、没有 H 数，**无法成为一个可执行的具体物种**。
- 冻结政策原话：“wildcard 袋本轮不供给、定义另行拍板；收窄须 CC 授权词”
  （`[CODE-B:572-576,656-662]`；`[CODE-B:991-997]` 的
  `supply_semantics.wildcard_bags`）。
- 所以 F3 是**政策边界**，不是编译器拒因，也不是“试过后失败”：
  178 条一次编译都没发（`[P3:422-423]`；`[CODE-B:1507-1517]`）。

**但要区分两种“未定义”：**

1. **裸 `*` / `XH2` 这类“整个分子没有一个确定的中心元素”**：不仅规则未定义，
   化学上也没有一个唯一的具体物种可填；不猜就是对的。
2. **attachment 型“有骨架、只缺一个 R 位”**：骨架是具体的，只缺一个取代基；
   规则未定义，但化学上**可能**存在一个可辩护的封闭替换集。这是 B 唯一有讨论
   空间的地方，也是本文要求化学评审的核心。

### 1.3 它**不**挡什么（容易误读的三件事）

1. **不是“模板中心缺失”。** 72/72 个 F3 模板的 `center_atoms` 非空
   （M3；`center_atoms` 长度分布见 §2.6）；**0/72** 个模板把 dummy 原子写进
   `center_atoms`。F3 发生在中心探测之前，`f5=not_evaluated`，所以“中心是否
   真实存在”**没有被测过**（unknown，D3）。
2. **不是“模板含 wildcard 就一律拦截”。** 如果 dummy-bearing 组分被选为
   **主组分**，它会被 `main_idx` 位置扣除，不进 `supply`，F3 不触发。
   T-H r2 有 **48 条**这样的非 F3 行（22 个模板；17 个 qid），其中
   **2 条 compiled、6 条 merged_into、5 条 ambiguous_alignment、
   3 条 defer/no_alignment、32 条 reject/no_alignment**（M1+M2；§2.1）。
   这**与 F3 的作用域=wildcard 在共底物侧一致**；代码上，wildcard 模板
   若不在 F3，只能是因为 wildcard 组分被选为主（否则 supply 含它 ⇒
   `wildcard_blocked`）。`[WL]` 未投影 `route`，所以逐行的主/辅判定仍是
   **代码推断**，不是逐行字段（B）。
3. **不是“F1 过也会被 F3 拦”。** F1 过的候选走 `direct_raw`，根本不进入
   supply 计算（`[CODE-B:1452-1492]`）。只是正常底物上含 `*` 的模板过不了 F1，
   所以实际看不到这条路径；如果底物自身含 dummy，才会出现“F1 过、F3 不查”的
   理论边界。本文不把这条理论边界当现实风险，但政策合同里要写明“F3 只作用于
   F1 拒后的供给路由”。

### 1.4 化学语义的三层判读

| 层 | 判读 | 证据 | 强度 |
|---|---|---|---|
| 代码层 | 供给组分含 `atomicNum==0` ⇒ 整袋 `wildcard_blocked`，先于 F5/编译 | `[CODE-B:571-587,708-712,1499-1517]` | A |
| 执行层 | 执行输入必须是具体分子；生产层核验 `execution_input_smiles` 的组分严格身份多重集 == 底物 ⊕ 声明供给，不等即 `ProductionContractError` | `[CODE-P:196-260]`；`[CODE-B:1003-1006]` | A |
| 化学层 | 模板中心是具体的（dummy 不在 `center_atoms`）；wildcard 是**外围未定义基团/原子**，不是“中心缺失” | M3；`[TPL].center_atoms` | A（结构事实）/ D（化学可替换性） |

**结论：** `wildcard_blocked` 是**供给规则的化学身份缺口**，不是“真实化学上
不该供给”的证明。对裸 `*`/`XH2`，它同时是“规则未定义”和“没有唯一具体物种”；
对 attachment，它只是“规则未定义”，化学上是否可填要独立评审。

---

## 2. Q2：178 条 / 52 题的分布与可拆程度

### 2.1 机械计数（M1/M2）

| 项 | 值 | 出处 |
|---|---:|---|
| F3 候选行 | **178** | `[P3:138,219]`；M1 |
| F3 题（qid） | **52** | `[P3:138,219]`；M1 |
| F3 题内事件（上下文，非直接事件） | **277** | `[P3:219]` |
| 唯一模板 | **72** | M2 |
| 只出现 1 行的模板 | **35** | M2 |
| 出现 ≥2 行的模板 | **37** | M2 |
| 前 5 个模板覆盖行数 | **30 / 178** | M2 |
| 每题行数 = 1 的题 | **31** | M1 |
| 每题行数 ≥2 的题 | **21** | M1 |
| 单题最多行数 | **18（2 题）** | M1 |
| 至少有 1 条 compiled/merged 候选的 F3 题 | **43 / 52** | M1 + `[WL]` outcome；与 `[P3:219]` 的“9 题无 compiled”互补 |
| 无任何 compiled/merged 候选的 F3 题 | **9 / 52** | `[P3:219,448]`；M1 |
| 其中仍 strict 的题 | **6 / 9**（5 题 hit@1、1 题 rank 5） | M6；`[P3:448]` |
| 其中 unmatched 的题 | **3 / 9** | M6 |
| F3 是该题唯一候选类的题 | **0 / 52** | `[P3:219]`（“该类是唯一候选类的题 = 0”） |

**读法：**

- 43/52 题已有其它 compiled/merged 候选；9 题没有 compiled，但 6 题仍 strict，
  只有 3 题 unmatched。**F3 不是任何一题的唯一候选类**，所以“178 条”不能读成
  “52 题都靠 F3”。
- 277 是题级上下文事件，不是 F3 直接事件；被拒候选直接事件 = 0
  （`[P3:210-212]`）。

### 2.2 每题行数分布（M1）

| 行/题 | 题数 | 行数小计 |
|---:|---:|---:|
| 1 | 31 | 31 |
| 2 | 9 | 18 |
| 5 | 1 | 5 |
| 7 | 2 | 14 |
| 8 | 2 | 16 |
| 9 | 2 | 18 |
| 11 | 1 | 11 |
| 13 | 1 | 13 |
| 16 | 1 | 16 |
| 18 | 2 | 36 |
| **合计** | **52** | **178** |

分布高度长尾：31 题只有 1 行，2 题各 18 行（合计 36 行 = 20.2%）。
这说明“178 条”主要是少数题的模板多样性放大，不是 52 题均匀分布。
**这是分母结构，不是收益结构。**

### 2.3 结构类：按模板组分拆（M2/M3）

把每个模板的 `mapped_lhs` 拆成 `n` 个组分，按“无 dummy 的干净组分”与
“含 dummy 的 wildcard 组分”计数：

| 结构类 `(n, clean, dummy)` | 含义 | 模板 | 行 | 题 |
|---|---|---:|---:|---:|
| `(2,0,2)` | 两个组分都含 dummy；**没有干净锚点** | 14 | 30 | 7 |
| `(2,1,1)` | 1 干净 + 1 wildcard；F3 行为 wildcard 在共底物侧 | 40 | 108 | 36 |
| `(3,1,2)` | 1 干净 + 2 wildcard | 1 | 4 | 4 |
| `(3,2,1)` | 2 干净 + 1 wildcard | 15 | 31 | 20 |
| `(4,3,1)` | 3 干净 + 1 wildcard | 2 | 5 | 5 |
| **合计** | | **72** | **178** | **52（有重叠）** |

- **30 行 / 7 题**属于 `(2,0,2)`：模板里一个干净组分都没有，主组分也只能是
  generic；这是化学上最不可定义的一类。
- **148 行**至少有一个干净组分；wildcard 在共底物侧（否则不会 F3）。

### 2.4 wildcard 形态：按组分拆（M3）

对每个含 dummy 的组分，按 dummy 原子的邻居判形态：

| 形态 | 判定 | 组分内重原子 | 模板 | 行 | 说明 |
|---|---|---|---:|---:|---:|
| **裸 `*`** | dummy 度 0、无 H、无重邻居 | 0 | 29 | 85 | 完全未指定的单价原子/基团 |
| **`XH2`** | dummy 无重邻居、2 个显式 H | 2（H 计） | 22 | 54 | 未指定元素的二价原子（可能是 O/S/…） |
| **attachment** | dummy 有 1 个重邻居 | ≥1 | 30 | 52 | 已有骨架，只缺一个开放价/R 位 |

> 模板可含多个 wildcard 组分，所以三行模板数/行数之和 > 72/178；这是
> **组分级**计数，不是互斥模板分类。互斥分类见 §2.5。

**裸 `*` 形态共 85 行**（29 个模板）：其中 **76 行的 bare 组分是唯一 dummy 组分**
（裸组分无重原子，不可能是主组分 ⇒ 确定被供给，且 dummy 在 L1）；另 **9 行**
模板还含 attach dummy，供给的是 bare 还是 attach 需底物/main_idx，`[WL]` 无此
字段 ⇒ **可能**在 L1。裸 `*` 不是“旁观 R 基”，而是键变化中心里的一个未定义原子
（例如插入/删除一个 generic 原子）；这类不是“补一个共底物”能解决的。

### 2.5 政策相关互斥分区：dummy 是否进中心查询 × 供给角色（M3/M4）

这是本文最重要的表。用 `extract_mapped_transform` + `l1_maps_of_transform`
（`[CODE-C:357,769]`）算 L1，再用 `build_center_query` 的 `shell=2` 规则
（`[CODE-C:817-857]`）判断 dummy 是否落在中心查询的保留集；同时判断
dummy-bearing 组分是否含 L1 原子（reactive vs spectator）：

> **名词区分：** `center_atoms` 是模板声明的中心 map 集合；编译器 L1 是从
> 键/电荷/手性变化算出的编辑中心。两者不是同一集合。本节用 **L1** 判
> “中心查询是否含 dummy”，用 **`center_atoms`** 判“模板是否声明 dummy 为
> 中心”（§2.6 的 0/72）。

| 分区 | 行 | 题 | 模板 | 化学含义 | B 可行性 |
|---|---:|---:|---:|---|---|
| **L1：dummy 原子本身在中心查询** | **85**（76 确定 + 9 可能） | 38 | 29 | 模板的中心查询含一个 `*` 原子；具体底物无法匹配 dummy；即使供货，F5/编译仍会撞上未定义原子 | **供货层替换不够**；必须模板实例化（另立合同）或维持 blocked |
| ├ reactive 裸 `*` | 76 | 38 | 24 | 裸 dummy 是键变化原子；整个分子没有具体骨架；裸组分无重原子，不可能是主组分 ⇒ **供给的 dummy 确定在 L1** | 同上 |
| └ ambiguous `attach+bare` | 9 | 4 | 5 | 模板同时有 attach 与 bare 两个 dummy；至少一个在 L1，但供给的是哪一个需底物/main_idx，`[WL]` 无此字段 ⇒ **可能** | 同上；逐行 unknown |
| **notL1：dummy 不在中心查询** | **86** | 28 | 36 | 中心查询不含 dummy；wildcard 是中心外围基团/分子 | 供货层替换在**查询层面**不被挡；化学可替换性另评 |
| ├ **spectator `XH2`** | **50** | **22** | **18** | 二价未指定元素，纯旁观；非 dummy 元素账 `{}` | **唯一有规模的 B1 候选**；`XH2→?` 是化学假设 |
| ├ spectator `attach` | 1 | 1 | 1 | 有骨架、开放价，但骨架很小且不在中心 | 规模太小；无实际价值 |
| ├ reactive `attach` | 11 | 8 | 8 | 有骨架、开放价；骨架含 L1（被转化） | R 基替换会改变反应分子；B 高风险 |
| ├ ambiguous `attach` | 20 | 4 | 5 | 主/辅角色无法离线判（需底物） | unknown |
| └ ambiguous `XH2+attach` | 4 | 2 | 4 | 混合形态；主/辅角色未知 | unknown |
| **tnc：`transform_no_change`** | **7** | **1** | **7** | 无 L1；F5 会 defer，编译会走 remap | 与 remap 交互，不能当普通 B |
| **合计** | **178** | **52（有重叠）** | **72** | | |

**关键读数：**

0. **85 是 L1 上界，不是 85 行都确定。** 其中 76 行（裸 `*` 唯一 dummy 组分）
   确定在 L1；9 行（attach+bare 混合）只有“至少一个 dummy 在 L1”，
   实际供给的是哪一个需底物/main_idx，`[WL]` 无此字段。表把这 9 行暂计入
   L1 上界，所以 **notL1 86 是下界**；真正“供货层替换一定不够”的是 **76 行**，
   不是 85 行。若 9 行实际供给 attach，则它们归 notL1（但仍是 ambiguous，
   不能直接当 B1）。
1. **76/178 确定 + 9/178 可能，连中心查询都含 dummy。** 这不是“供货后 F5
   可能不过”，而是 `build_center_query` 会把 dummy 原样复制进查询
   （`[CODE-C:860-889]`），具体底物不可能匹配 `atomicNum==0`。
   **RDKit 2026.03.6 只读实测：含 dummy 的 query 对普通 C/O 分子零命中
   （裸 dummy、dummy+C=O、dummy+2H 三种形态都零命中；dummy 只匹配 dummy）。**
   **B 不能只改 `sub_supplied` 字符串；它必须实例化模板的 lhs/rhs，否则这 76 行
   仍然过不了 F5；另 9 行因多 dummy 组分，供给的 dummy 是否在 L1 需底物/main_idx，
   `[WL]` 无此字段，保持 unknown。**
2. **50/178（28.1%）是 spectator `XH2`**：dummy 不在 L1，组分不在中心，
   非 dummy 元素账 `{}`，是唯一有规模的“中心已定义、wildcard 在外围”的类。
   但它的化学身份只有“二价 + 2H”，元素未定；`XH2` 可以读成水、H2S、
   或任何二价原子。**“`XH2` = 水”不是模板能推出的规则，必须化学评审。**
3. **11 行 reactive `attach`**：骨架在中心里，R 基替换会改变被转化的分子；
   B 不应把这类当“旁观 R 基”放行。
4. **7 行 tnc**：没有 L1，F5 会 defer，编译层会触发 `complete_template_mapping`
   （`[CODE-C:530-612,931-934]`）；B 若碰这 7 行，必须和 remap 单变量分开，
   不能混在一起。
5. 以上分区是**模板级**的；同一题可同时有多个分区的行（qid 列有重叠），
   所以题数不能相加。

**同分母占比（行，分母 178；不是题占比）：**

| 分区 | 行 | 占比 |
|---|---:|---:|
| 裸 `*`（76 确定在 L1） | 76 | 42.7% |
| attach+bare（9 可能） | 9 | 5.1% |
| spectator `XH2` | 50 | 28.1% |
| spectator `attach` | 1 | 0.6% |
| reactive `attach` | 11 | 6.2% |
| ambiguous `attach` | 20 | 11.2% |
| ambiguous `XH2+attach` | 4 | 2.2% |
| tnc | 7 | 3.9% |
| **合计** | **178** | **100.0%** |

### 2.6 中心大小与元素账（M3/M5）

**中心大小（`center_atoms` 长度，按行加权）：**

| 中心原子数 | 模板 | 行 |
|---:|---:|---:|
| 1 | 8 | 11 |
| 2 | 38 | 110 |
| 3 | 14 | 40 |
| 4 | 7 | 10 |
| 8 | 4 | 4 |
| 10 | 1 | 3 |
| **合计** | **72** | **178** |

所有 72 个模板的中心都非空；**0 个模板中心为空**。这再次说明 F3 不是
“中心未定义”，而是“共底物身份未定义”。

> **map 号口径：** `center_atoms` 是 map 号集合；**9 个模板的 dummy 未映射**
> （map 0），按定义不可能出现在 `center_atoms` 或 L1。它们单列为 unmapped/tnc，
> **不当作“dummy 已核不在中心”的证据**；其中 7 个是 tnc，另 2 个是可解析但
> dummy 未映射。`0/72` 只说明“没有模板把 dummy 的 map 号写进 center_atoms”，
> 不等于“所有 dummy 的化学角色都已核”。

**非 dummy 重元素账（M5）：**

- **166/178 行**：去掉 dummy 原子后，`rhs - lhs` 的元素差为 `{}`。
  即 wildcard 组分在重元素账上是**净零**的（generic 替换/旁观），
  换什么元素都不破坏非 dummy 部分的配平；**但净零是必要不充分条件，
  不能单独证明 wildcard 组分不参与反应**（可能被同元素的其他组分掩盖）。
  这也意味着“换元素”不会自动证明化学正确。
- **12/178 行**：元素差非空（例如 `{O:-1}`、`{C:-5,O:-5}`、
  `{C:8,O:-5,P:-1,N:-1}` 等）。这些行的非 dummy 元素账不平衡，
  **不能证明 wildcard 组分是纯旁观**；可能是它，也可能是其它组分。
  在化学评审给出逐模板判读前，**这 12 行不应进入 B1**。

### 2.7 “真实缺中心” vs “共底物供给规则缺面”

| 判据 | 结论 | 证据 | 强度 |
|---|---|---|---|
| **真实缺中心**（底物真的没有该反应中心） | **unknown，0 条可判** | F3 在 F5 之前；`f5=not_evaluated`；没有中心探测（`[CODE-B:1499-1517]`） | D |
| **模板中心未定义**（模板自己没有中心） | **0/72** | 72/72 `center_atoms` 非空；0/72 dummy 在 `center_atoms`（M3） | A |
| **中心查询含未定义原子** | **76 行确定 + 9 行可能（模板级上界 85）** | dummy 原子在 L1；`build_center_query` 复制 dummy 进查询（M4；`[CODE-C:860-889]`）；9 行为多 dummy 模板，供给哪个 unknown | A（76）/ D（9） |
| **共底物供给规则缺面**（机制层） | **178/178** | 全部是 `wildcard_blocked`；没有编译尝试（`[P3:417-423]`；`[CODE-B:1499-1517]`） | A |
| **共底物身份缺口的具体形态** | 85 L1（76 确定 + 9 可能）/ 50 spectator XH2 / 11 reactive attach / 1 spectator attach / 24 ambiguous / 7 tnc | §2.5；M3/M4 | A（结构）/ D（化学可替换性） |

**回答方式：**

- 如果“真实缺中心”指**底物真的没有中心**：**unknown**，不能给数字。F3 没有
  跑过 F5，任何“多少条真实缺中心”都是猜。
- 如果“真实缺中心”指**模板中心未定义**：**0 条**；72/72 模板中心非空。
- “共底物供给规则缺面”：**178/178 机制上成立**；但内部不是一类：
  85 条（76 确定 + 9 可能）是“中心查询含 dummy”，50 条是“spectator XH2”，11 条是“reactive
  attachment”，1 条“spectator attachment”，24 条“角色未知”，7 条“tnc”。
  **能离线判定的 100% 是供给规则缺口；真实缺中心 0 条可判，全部 unknown。**

### 2.8 可拆程度：题型 / 底物 / 变换类型

| 维度 | 能拆到什么程度 | 依据 |
|---|---|---|
| **模板/形态/结构类** | **完全可拆**：72 模板、5 个结构类、3 种 wildcard 形态、§2.5 的 8 个政策分区 | M1-M4 |
| **供给角色**（reactive/spectator/ambiguous/tnc） | **可拆**（模板级）；每题多行可跨区 | M4；§2.5 |
| **中心查询成员**（dummy in L1 / not / tnc） | **完全可拆** | M4 |
| **元素账**（净零 / 非零） | **完全可拆** | M5 |
| **题型** | **unknown**：qid 是 `RXNG_<sha256>`；`[METRICS]` 只有 `main`/`old` 桶，没有题型字段；题面读取被红线禁止 | `[WL]` 键枚举；`[METRICS]` per_qid 键；任务红线 |
| **底物** | **unknown**：`[WL]` 没有底物 SMILES；封存逐题 run/题面禁止读取 | `[WL]` 键枚举；任务红线 |
| **反应类型名**（水解/氧化/转移…） | **unknown/不能命名**：模板资产只有 `center_atoms/env_shell/qc_flags`，没有 EC/反应类型字段；`assets/rhea.json` 是模板模式表，不是逐 RHEA 的 EC 元数据；本轮不联网、不猜 | `[TPL]` 键枚举；`assets/rhea.json` schema |
| **变换的粗粒度描述** | **可拆到**：中心大小（1/2/3/4/8/10）、是否含 L1、dummy 是否在 L1、非 dummy 元素差 | M3-M5 |

**结论：** 178/52 可以 100% 拆到“模板 × 形态 × 供给角色 × 中心查询成员 ×
元素账”的规则级分层；**不能**拆到题型、底物、反应类型名。后者需要题面/底物/
化学分类元数据，均在红线外或本轮不可得，保持 unknown。

### 2.9 辅助诊断字段（不推收益）

`[WL]` 的 F3 行还有两个只读归因字段：

| 字段 | 分布 | 含义 | 读法 |
|---|---:|---|---|
| `light_gap_coverable_by_bag` | `True` 108 / `False` 70 | 主组分元素缺口是否可被袋元素覆盖（`[CODE-B:731-756]` 的只读归因） | 只是“元素账可覆盖”，**不是**“可编译/化学正确/有收益” |
| `record_side_form_norm` | `not_applicable` 138 / `applied` 40 | 记录侧形式归一的三值标量 | 不用于 F3 判定；不作版本键以外的推断 |

**不要把 108 读成“108 条可救”。** 它只说明袋的元素多重集覆盖主组分的元素缺口；
化学身份、中心匹配、编译、判分都还没有发生。

---

## 3. Q3：政策选项 A / B / C

> 三个选项都**不改判分口径**（criteria-v2 不变）、**不读金标**、**不用 178/992
> 推收益**。所有“覆盖行数”都是政策作用面上界，不是收益预测。

### 3.1 选项 A：维持现状（wildcard 一律不供给）

| 项 | 内容 |
|---|---|
| **化学判据** | 供给组分含原子序数 0 ⇒ 没有具体元素/价态/H 数，不能成为执行输入的具体分子；fail-closed。 |
| **作用面** | 178 行 / 52 题；其中 L1 上界 85 行（76 确定 + 9 可能），50 行 spectator XH2，11 行 reactive attach，1 行 spectator attach，24 行 ambiguous，7 行 tnc（§2.5）。 |
| **正控** | 非 wildcard 的多组分供给袋仍可编译（`[TEST-S:263-292]` 的 clean bag；`[P3:250-252]` 的 986 F5 pass / 134 compiled 面不受影响）。 |
| **负控** | 裸 `*` 与 `[H]*[H]` 袋整袋拦截（`[TEST-S:294-313]`）；F3 先于 F5/直编、`f5=not_evaluated`、编译调用 0（`[TEST-C:280-305]`）。 |
| **298 影响面** | 零改动；headline 89/298 与 F3 qid 的 26 hit@1 / 35 strict / 9 无 compiled 全部不变。**不预报收益/损失。** |
| **实施入口** | 无。build/compile/execute/audit 全部保持现状。 |
| **风险** | 178 条候选不尝试；9 题无 compiled（但 6 题 strict、只有 3 题 unmatched）；其中是否有真实可救的化学缺口，unknown。 |
| **停点** | 无（冻结政策）。任何收窄/放宽都必须 CC 授权 + 化学评审 + 预注册（`[CODE-B:572-576]`）。 |

### 3.2 选项 B：定义并启用窄 wildcard（逐类白名单）

B 不是“开一个开关”，而是**五个不同子问题**，必须分开拍板：

| 子项 | 目标类 | 行 / 题 / 模板 | 化学判据 | 建议 |
|---|---|---:|---|---|
| **B1** | spectator `XH2`（dummy 不在 L1、组分不在中心、非 dummy 元素账 `{}`） | **50 / 22 / 18** | 二价未指定元素 + 2H；只有在化学评审能给出**封闭替换集**（例如仅水，或 O/S/Se 的封闭集）且不改变净反应时才可放行 | **唯一值得做条件性试点的子项**；默认仍 blocked，评审 PASS 才试点 |
| **B2** | spectator `attach`（有骨架、开放价、不在中心） | **1 / 1 / 1** | 骨架太小；R 基替换无规模价值 | 不做 |
| **B3** | reactive `attach`（骨架含 L1） | **11 / 8 / 8** | R 基替换会改变被转化的分子；不是“旁观取代基” | 不做；维持 blocked |
| **B4** | dummy 在 L1（85 行：76 确定 + 9 可能；含裸 `*` 76 行） | **85 / 38 / 29** | 中心查询本身含 dummy；供货层替换不可能匹配；必须模板实例化 | **不在 B 的供货层合同内**；若要做，另立“模板实例化”合同 |
| **B5** | notL1 ambiguous（20+4=24 行）+ tnc（7 行） | **31 / 7 / 16** | 主/辅角色需底物；tnc 与 remap 交互 | unknown；不纳入首轮 |

**B 的化学判据（总则）：**

1. 只允许**中心已定义、wildcard 不在中心查询**的行（notL1）。
2. 只允许**spectator**（dummy-bearing 组分不含 L1 原子），不允许 reactive。
3. 只允许**非 dummy 元素账 `{}`** 的行；非零元素差的行必须保持 blocked。
4. 替换必须是**具体、可解析、无 dummy、价态/电荷/立体明确**的分子；
   不允许“任意原子”“删掉组分”“把 dummy 当 H”。
5. 替换集必须**逐模板/逐组分封闭**，不能按名字/子串/相似度泛化。
6. 替换后仍走原 F5 → 编译 → 执行 → 判分；**不得绕过 `no_alignment`**。

**B 的正控：**

- 非 wildcard 供给袋仍可编译（`[TEST-S:263-292]`）。
- B1 白名单命中后，`sub_supplied` = 底物 ⊕ 具体替换分子；必须通过
  `production._verify_execution_input` 的严格身份多重集核验
  （`[CODE-P:196-260]`）。
- 同一具体分子若能从非 wildcard 路径供给，两条路径的 F5/编译结果应一致；
  这是 A/B 正控（需要 D2 回放，未做）。
- 234/242 remap、其它池成员、非 F3 qid 的候选集不变（全 298 配对）。

**B 的负控：**

- 裸 `*` 袋仍 blocked（`[TEST-S:263-292]`）。
- 不在白名单的 `[H]*[H]` 袋仍 blocked（`[TEST-S:294-313]`）。
- 替换分子含 dummy、价态非法、电荷/元素账改变 ⇒ 结构化拒。
- 部分覆盖（一个 wildcard 组分有白名单、另一个没有）⇒ 整袋仍 blocked。
- dummy 在 L1 ⇒ 供货层替换必须拒；不得靠“编译器可能忽略”放行。
- 替换后净反应/记录契约改变 ⇒ 停，不进入评分。
- 48 条非 F3 行（wildcard 在主侧）必须零变化；这是“路由作用域”负控。

**B 的 298 影响面（不预报收益）：**

- B1 覆盖上界 = **50 行 / 22 题 / 18 模板**；其中 7 题当前无 compiled 候选
  （M1 + `[WL]`；§2.5 的 XH2 类），这 7 题里 5 题当前 strict（4 hit@1 + 1 rank 5）、
  2 题 unmatched。这是**覆盖上界**，不是净增。
- 22 题里很多已有其它 compiled 候选；**没有证据说 B1 能把这 7 题变成命中。**
  （全 52 题的 9 个无 compiled 题中 6 题仍 strict、3 题 unmatched，见 §2.1。）
- 任何 B 试点必须全 298 配对报告：新增/损失/净增、hit@1、strict、partial、
  unmatched、分族；不能只报“这 50 条编译成功”。
- 判分口径零改动；B1 只改候选供给，不改 criteria-v2。

**B 的实施入口（build/compile/execute/audit）：**

| 层 | 消费点 | B 要做什么 | 不能做什么 |
|---|---|---|---|
| build | `analog_cosub_supply`（`[CODE-B:640-714]`） | 在 `wildcard_blocked` 返回前加白名单查找；命中则返回 `supply`（带替换后的组分）并打标 | 不改主组分选择、不改其他 supply 组分、不改 `no_supply` 分支 |
| build | F3 分支（`[CODE-B:1499-1517]`） | 白名单命中走 supply 分支；未命中保持 blocked 原口径 | 不跳过 F5；不改 `no_alignment` 口径 |
| build | 供给装配（`[CODE-B:862-1006]`） | participants/co_substrate_states/record_equation/execution_input 使用替换后的具体分子；保留 spectator 披露 | 不伪造状态、不省略声明 |
| build | `_light_gap_coverable_by_bag`（`[CODE-B:731-756]`） | 用替换后的袋重算归因字段 | 不把它当准入判据 |
| build | 诊断（`[CODE-B:1782-1807]`） | 新增 `wildcard_whitelist_*` 计数/版本/条目哈希；旧 `wildcard_blocked` 语义保留给未命中行 | 不改旧字段含义 |
| compile | `template_elements_fit`（`[CODE-C:230-264]`） | 不动；F1 仍按原模板 `*` 判 | 不用白名单改 F1 路由 |
| compile | `build_center_query` / `enumerate_center_alignments`（`[CODE-C:817-907]`） | 若 dummy 不在 L1，查询不含 dummy；不改编译器 | 若 dummy 在 L1（76 确定 + 9 可能），不得供货层放行；必须模板实例化或保持 blocked |
| compile | `compile_donor_template` / `_compile_donor_template_impl`（`[CODE-C:1416-1830]`） | 不改中心/编辑/歧义判据 | 不为白名单放宽 `no_alignment`、charge/stereo、alignment limit |
| compile | `complete_template_mapping`（`[CODE-C:530-612]`） | 7 条 tnc 行保持独立；不把 remap 与白名单混在一起 | 不扩 remap 触发面 |
| execute | `production._verify_execution_input`（`[CODE-P:196-260]`） | 替换分子必须进入 `co_substrate_states`，严格身份多重集 == 底物 ⊕ 声明供给 | 不得用字符串拼接绕过身份核验 |
| execute | `prepare_hypothesis` 事件级合同（`[CODE-P:437-490]`） | participants/co_substrate_states/copy 合同照旧；NC-10 不变量不变 | 不跳过事件级核验 |
| audit | `pool_diagnostics` 计数/逐候选行（`[CODE-B:1782-1807]`） | 新版本键 + 逐候选 `wildcard_policy`/`whitelist_entry`/替换身份哈希 | 不把新字段当版本排除来洗掉损坏 |
| audit | 批身份/池策略版本（`[BID:2-8]`；`[CODE-B:514]`） | 升 `S5B_POOL_POLICY_VERSION` 与 `S5B_ANALOG_COSUB_SUPPLY_VERSION`；新批根；预注册 | 不在旧批上原地改；不覆盖封存 run |
| replay | 同 build/prepare 路径 | 白名单版本/条目哈希进 run identity；重放确定性 | 不用旧 run 重算新身份；不延迟到重放才校验 |

**B 的风险与停点：**

| 风险 | 说明 | 停点 |
|---|---|---|
| 元素猜错 | `XH2` 不一定是水；O/S/Se 的价态/质子化不同 | 化学评审给不出封闭集 ⇒ 停 |
| 净反应改变 | 替换分子可能改变配平/产物集合；12 行非零元素差已证 | 任一替换改变净反应/记录契约 ⇒ 停 |
| 模板 rhs 仍含 dummy | 供货层替换不改模板 rhs；若编译器/产物侧仍引用 dummy，产物可能缺组分或身份不一致 | D2 回放不能证明产物身份 ⇒ 停 |
| 中心查询含 dummy | 76 行确定（+9 行可能）dummy 在 L1；供货层替换无法匹配（9 行是否如此 unknown） | 这些行保持 blocked；要做另立模板实例化合同 |
| 路由外溢 | 48 条非 F3 行、2 compiled/6 merged 可能被误改 | 非 F3 行零变化负控失败 ⇒ 停 |
| 版本/身份漂移 | 新池成员必须新 pool policy 版本/新批根 | 未升版本/未预注册 ⇒ 停 |
| 收益误读 | 50/22 是覆盖上界，不是净增 | 用覆盖数报收益 ⇒ 停 |

### 3.3 选项 C：放宽为通用共底物供给（不推荐）

| 项 | 内容 |
|---|---|
| **化学判据** | 无。把原子序数 0 当“任意原子”、把 dummy 组分当“可忽略”、或直接把 dummy 原样并入执行输入，都不是化学规则：dummy 没有元素/价态/H 数，具体底物无法匹配；强行替换等于凭空指定元素。 |
| **为什么不行** | ① 76 行确定（+9 行可能）dummy 在 L1，dummy 本身是键变化原子；把它当任意原子 = 伪造反应中心。② 166 行非 dummy 元素账 `{}`，删掉 dummy 会改变净反应（少一个旁观分子）；12 行元素账非零，删掉直接破坏配平。③ 会外溢到 48 条非 F3 行（含 2 compiled/6 merged）和 94 个 wildcard 模板的其它候选。④ 违反 `[PLAN:154,181-195]` 的“不改变净反应/记录契约”“不从 no_alignment 条数推收益/普遍放宽”。 |
| **正控/负控** | 正控：真实具体共底物的供给仍可编译。负控：任何 dummy-as-any、drop-dummy、dummy 原样入执行输入都必须拒；元素账/净反应必须核。 |
| **298 影响面** | 不预报；高概率产生假候选、改变净反应、降低 strict；不能作为提分手段。 |
| **实施入口** | 会同时改 build/compile/execute/audit 全部层；不是单点开关。 |
| **风险/停点** | 化学错误、假阳性、判分口径被动改变；**直接否决**。 |

### 3.4 推荐：A 为主，B1 仅条件性试点

**推荐 A（维持现状）。理由按证据强度排序：**

1. **F3 不是任何一题的唯一候选类**（0/52，`[P3:219]`）；43/52 题已有
   compiled/merged 候选；26/52 已 hit@1、35/52 strict（M6；`[P3:88,219]`）。
   9 题无 compiled，但 6 题仍 strict（5 hit@1 + 1 rank 5），只有 3 题 unmatched
   （M6；`[P3:448]`）。这 9 题也不是 F3-only：每题仍有 9–37 条候选行，
   原因含 F5 reject/defer、`cosubstrate_bonded_contribution_unsupported`、
   `transform_no_change` 等（M1）；F3 只是其中一部分。**没有题级证据支持
   F3 是瓶颈。**
2. **178 条里 126 条是裸 `*`/`XH2`（无具体骨架）**，85 条（76 确定 + 9 可能）
   dummy 本身在中心查询；
   真正“中心已定义、wildcard 在外围、且非 dummy 元素账净零”的只有
   **51 条**（50 XH2 + 1 attach），其中只有 **50 条**有规模（§2.5）。
3. **B1 的化学前提没有被证明**：`XH2` 是“二价未指定元素”，不是“水”。
   把它当水是一个化学假设；没有模板内证据、没有 RHEA/EC 元数据、没有
   化学评审结论。用假设换候选，风险不对称。
4. **B 不是单点开关**：76 行确定（+9 行可能）需要模板实例化；7 行与 remap
   交互；48 行非 F3
   行是路由外溢负控；execution 层还有严格身份多重集核验。工程面远大于
   “在 `analog_cosub_supply` 加一个白名单”。
5. **计划红线**：`[PLAN:149-162]` 要求按证据拆项、不按拒绝条数排投资；
   `[PLAN:181-195]` 明确不按 `no_alignment` 条数推收益、不普遍放宽。
   A 是唯一不需要新化学假设、且不改变判分口径的选项。

**B1 的条件性试点（仅当以下全部满足才启动）：**

1. 独立化学评审给出 **PASS**：`XH2` 的封闭替换集、适用条件、反例；
2. 正/负控全部通过（§4.6）；
3. CC 明确授权 + 新 pool policy 版本 + 预注册；
4. 全 298 配对实验，判分口径零改动；
5. 只作用于 `wildcard_blocked` 分支，不碰 `supply`/`no_supply`/直编；
6. 85 行 L1（76 确定 + 9 可能）、12 行非零元素账、11 行 reactive attach、7 行 tnc 全部排除。

**不推荐 B2/B3/B4/B5；C 否决。**

### 3.5 对 298 的影响面（不预报收益）

| 选项 | 作用面（候选行上界） | 298 读数要求 | 收益结论 |
|---|---:|---|---|
| A | 0（现状） | 无需新跑 | 不变；不报收益 |
| B1 | 50 行 / 22 题 / 18 模板 | 全 298 配对新增/损失/净增、hit@1、strict、partial、unmatched、分族 | **不预报**；覆盖上界 ≠ 净增 |
| B（B1+B2+B3，可供货层处理的子项） | 62 行（50+1+11）/ 28 题（有重叠） | 同上 | **不预报**；且 B3 化学风险高 |
| C | 178 行 + 48 非 F3 行（94 模板面） | 同上，另加净反应/配平核验 | **不预报**；高概率负向 |

> 表内“题”是并集上界，不是互斥题数；B1 的 22 题与 B（B1+B2+B3）的 28 题有重叠。
> 50/22 是“最多可能被政策碰到”，不是“能救 50 条/22 题”。

---

## 4. Q4：如果选 B，最小可实施合同

> 本节只给 **B1（spectator `XH2`）** 的最小合同；B3/B4 不在供货层合同内。
> 合同原则：**白名单、逐模板、封闭集、fail-closed、判分零改动、全 298 配对。**

### 4.1 前置条件（缺一不可）

1. 化学评审 PASS（§5 的请求稿）；评审必须给出：
   - 允许的替换元素/分子封闭集；
   - 每个类的适用条件（价态、质子化、溶剂/水合、是否旁观）；
   - 至少 1 个正控 + 1 个真实错误负控；
   - 明确 unknown 范围。
2. CC 授权（政策变更，不是代码优化）。
3. 新 `S5B_POOL_POLICY_VERSION` + 新 `S5B_ANALOG_COSUB_SUPPLY_VERSION`；
   新批根；预注册。
4. 只改 `wildcard_blocked` 分支；`supply`/`no_supply`/`direct_raw` 分支零改动。
5. 判分口径零改动；不读金标；不新增 LLM 调用。

### 4.2 白名单 schema（版本化、哈希固定）

```json
{
  "whitelist_version": "f3-wildcard-whitelist-1",
  "chemistry_review_ref": "<docs/... review response>",
  "entries": [
    {
      "entry_id": "f3w-0001",
      "template_record_id": "<exact record_id>",
      "wildcard_component_identity": "<canonical stripped component identity>",
      "wildcard_atom_map": "<int or null>",
      "wildcard_form": "XH2",
      "scope": {
        "dummy_not_in_L1": true,
        "component_not_in_center": true,
        "non_dummy_element_delta_empty": true,
        "supplied_component_only": true
      },
      "replacement": {
        "smiles": "<concrete molecule, no dummy>",
        "identity": "<cn/strict identity>",
        "element": "O",
        "charge": 0,
        "stereo": "unspecified"
      },
      "review_evidence": "<review PASS item>"
    }
  ]
}
```

**硬规则：**

- `template_record_id` 必须精确匹配；不允许按名字/子串/相似度/EC 类泛化。
- `wildcard_component_identity` 用 canonical stripped identity（与
  `analog_cosub_supply` 的 `_cosub_strip_map` 同口径）；不允许“同 CN 模糊匹配”。
- 一个袋里**所有** wildcard 组分都必须有条目；任一缺失 ⇒ 整袋仍 blocked。
- 同一模板/组分出现多条不同条目 ⇒ 歧义 ⇒ blocked（不取第一条）。
- 条目只对 `wildcard_form` 匹配的组分生效；`bare` 不允许出现在条目里。

### 4.3 匹配与执行顺序

1. 先跑现有 `analog_cosub_supply`，得到 `status`、`supply`、`main_idx`。
2. `status != wildcard_blocked` ⇒ 完全走现状（零改动）。
3. `status == wildcard_blocked`：
   1. 对每个 `supply` 组分查白名单；
   2. 检查 scope 谓词（dummy 不在 L1、组分不含 L1、非 dummy 元素账 `{}`）；
   3. 任一不满足/缺失/歧义 ⇒ 保持 `wildcard_blocked`，旧计数与旧拒因不变；
   4. 全部满足 ⇒ 用 `replacement.smiles` 替换该组分，得到 `supply_replaced`；
   5. 重算 `sub_supplied = substrate + "." + ".".join(supply_replaced)`；
   6. 重算 `_light_gap_coverable_by_bag`（用替换后的袋）；
   7. 走现有 F5 → 编译 → 供给装配 → 执行；**不跳过任何一步**。
4. 如果 F5 absent ⇒ 仍 `no_alignment`；如果编译失败 ⇒ 真实拒因；
   如果编译成功 ⇒ 按现有 `_attach_analog_cosub_supply_fields` 装配，
   `co_substrate_states` 里是替换后的具体分子。
5. 生产层 `_verify_execution_input` 必须通过：声明供给多重集 ==
   `co_substrate_states` 多重集；不等 ⇒ `ProductionContractError`，零事件。

### 4.4 失败模式（全部 fail-closed）

| 失败模式 | 处置 | 诊断 |
|---|---|---|
| 白名单缺条目 | 保持 blocked | `wildcard_whitelist_miss` |
| 多条目歧义 | 保持 blocked | `wildcard_whitelist_ambiguous` |
| 替换 SMILES 含 dummy/不可解析/价态非法 | 保持 blocked | `wildcard_whitelist_invalid_replacement` |
| 替换改变非 dummy 元素账 | 保持 blocked | `wildcard_whitelist_element_mismatch` |
| dummy 在 L1 | 保持 blocked | `wildcard_whitelist_dummy_in_l1` |
| 组分含 L1（reactive） | 保持 blocked | `wildcard_whitelist_reactive_component` |
| 部分 wildcard 组分未覆盖 | 整袋 blocked | `wildcard_whitelist_partial_bag` |
| 模板/记录不匹配 | 保持 blocked | `wildcard_whitelist_template_mismatch` |
| 执行输入多重集不等 | `ProductionContractError` | `execution_input_multiset_mismatch` |
| 净反应/记录契约改变 | 停，回化学评审 | 不进入评分 |

**不允许的 fallback：** 任意原子、删组分、把 dummy 当 H、按相似度选一个
“最像”的分子、按模板名/EC 类批量套用、编译器报错后自动放宽。

### 4.5 与 F5 预门/编译器/判分的关系

| 层 | 关系 |
|---|---|
| **F5 预门** | B 只改 F4 输入；F5 仍对 `sub_supplied` 判 `present/absent/defer`。F5 absent 仍 `no_alignment`；不得用白名单绕过 F5。 |
| **编译器** | B 不改 `build_center_query`/`enumerate_center_alignments`/`compile_donor_template` 的任何判据；不改 `no_alignment`、charge/stereo、alignment limit。若 dummy 在 L1（76 确定 + 9 可能），供货层替换不能匹配，必须保持 blocked；要做模板实例化，另立合同。 |
| **执行** | B 的替换分子必须进 `co_substrate_states`/participants；`production._verify_execution_input` 的严格身份多重集核验不变；NC-10 事件级合同不变。 |
| **判分** | **零改动**。criteria-v2 不变；不新增按类加分/豁免；不读金标；全 298 配对报告新增/损失/净增。 |
| **重放** | 白名单版本/条目哈希进 run identity；重放确定性；旧 run 不重写。 |

### 4.6 正控/负控（最小集）

**正控（必须全过）：**

1. **非 wildcard 供给袋**：`[TEST-S:263-292]` 的 clean bag 仍 `supply` 且可编译。
2. **F3 clean 对照**：同一模板去掉 wildcard 组分后（或同净反应的非 wildcard
   模板）仍可编译；证明“不是全面拒绝换通过”。
3. **白名单命中**：替换分子进入 `execution_input_smiles`，生产层严格身份
   多重集通过；F5/编译结果与同一具体分子的非 wildcard 路径一致（D2 回放）。
4. **非 F3 零变化**：48 条非 F3 行、2 compiled、6 merged 不变。

**负控（必须全拒）：**

1. 裸 `*` 袋仍 blocked（`[TEST-S:263-292]`）。
2. 非白名单 `[H]*[H]` 袋仍 blocked（`[TEST-S:294-313]`）。
3. 白名单条目替换成错误元素/电荷/价态 ⇒ 拒。
4. 替换改变非 dummy 元素账/净反应 ⇒ 拒。
5. dummy 在 L1 的行 ⇒ 拒（供货层不可匹配）。
6. 部分覆盖袋 ⇒ 整袋拒。
7. 模板 record_id 不匹配/多条目歧义 ⇒ 拒。
8. 执行输入多重集不等 ⇒ `ProductionContractError`，零事件。

### 4.7 版本、诊断与放行

- 版本：`s5b-pool-policy-10`（或下一可用号）+
  `s5b-analog-cosub-supply-2` + `f3-wildcard-whitelist-1`。
- 逐候选诊断：`wildcard_policy`（blocked/whitelist_applied）、
  `wildcard_whitelist_version`、`wildcard_entry_id`、
  `wildcard_replacement_identity`、`wildcard_replacement_sha256`、
  `wildcard_scope_checks`。
- 批级诊断：`wildcard_whitelist_applied/miss/rejected` 计数；
  旧 `analog_cosub_supply_wildcard_blocked` 只统计未命中行，语义不变。
- 放行：全 298 配对、正负控、生产层核验、审计可重放；任一失败 ⇒ 停，
  不承诺“永不犯错”，也不以全面拒绝换通过。

---

## 5. Q5：明确“不做什么”及反证

### 5.1 引用优化计划 §6 原文（`[PLAN:181-195]`）

| 不做 | §6 原文（反证） | 本文对应证据 |
|---|---|---|
| 从 `no_alignment` 条数推收益 | “同码多义；需拆码与合法正控” | 178 是政策边界；26/52 hit@1、35/52 strict、43/52 已有 compiled；0 题 F3-only（M6；`[P3:88,219]`） |
| 普遍放宽 `no_alignment` | 同码多义；需正控/负控 | F3 拦截发生在 F5 前；85 行（76 确定 + 9 可能）dummy 在 L1；放宽会把未定义原子放进中心查询 |
| 删副产物/删 copy/加反应物侧共底物 | “改变净反应与记录契约” | 166/178 行非 dummy 元素账 `{}`；删 dummy = 少一个旁观分子；12 行非零元素差 = 直接破坏配平（M5） |
| 用 12 题异常证明缺脱氢 / 用 21 题证明硬天花板 | 隐式氢由 sanitize 重算；声明可带立体 | 与 F3 无关；本文不引 |
| 以“多个模型同意”代替证据 | 只认机读与源码互证 | 本文只认代码/哈希资产/计数；化学可替换性保持 unknown 等评审 |
| recorded 硬优先 | 49%/24% 不同题群；历史不可迁移 | 与 F3 无关；不借 F3 重开 |
| 打开证据卡 v1/v2 | chain14 A/B 负先例 | 与 F3 无关 |
| 以 width 截断解释 partial | 事件由完整 hypothesis 创建 | 与 F3 无关 |

### 5.2 F3 专项“不做”清单

| 不做 | 反证/理由 |
|---|---|
| **不要按 178/992 条数推收益** | 178 是候选行，不是可回收题；992 是计数器，含 814 条 F5，禁止相加（`[P3:123-143]`）；0 题 F3-only，26/52 已 hit@1 |
| **不要为提分放宽 `no_alignment`** | F3 是政策边界，不是对齐失败；放宽会把 dummy 放进 F4/中心查询；`[PLAN:156]` 明确禁止 |
| **不要把 wildcard 全都当“任意原子”供给** | dummy 无元素/价态/H；85 行（76 确定 + 9 可能）dummy 在 L1；12 行非零元素差；会伪造中心/破坏配平 |
| **不要只改 `analog_cosub_supply` 就以为 B 能工作** | 85 行（76 确定 + 9 可能）需要模板实例化；7 行与 remap 交互；生产层还有严格身份核验 |
| **不要碰 48 条非 F3 行** | 它们是 wildcard 在主侧、2 compiled/6 merged；路由外溢会破坏现有合法面 |
| **不要把 108 条 `light_gap_coverable_by_bag=True` 当可救数** | 只是“袋元素覆盖主组分元素缺口”，不是化学正确/可编译/有收益 |
| **不要用 277 事件当 F3 直接事件** | 277 是 52 题的上下文事件；被拒候选直接事件 = 0（`[P3:210-212]`） |
| **不要用 992 旧标签写 F3** | `[DP:31-32,127-128,234-235]`、`[LEVER2:339]` 是修正前标签；以 `[P3:123-143]` 为准 |
| **不要把 `XH2` 默认当水** | 二价未指定元素；O/S/Se 都可能；必须化学评审给封闭集 |
| **不要在没有预注册/新版本/新批根时改池成员** | 池成员变化 ⇒ 新身份；旧批不原地改 |

### 5.3 反证数字（防止“条数=收益”）

- 178 条覆盖 52 题，但 **0 题**的候选全是 F3；43/52 题已有 compiled/merged；
  26/52 hit@1、35/52 strict（M6；`[P3:88,219]`）。
- 9 题无 compiled，但 **6 题仍 strict**（5 hit@1 + 1 rank 5）；只有 3 题 unmatched
  （M6；`[P3:448]`）。
- 178 条中 85 条（76 确定 + 9 可能）dummy 在 L1；50 条 spectator XH2；11 条 reactive attach；
  1 条 spectator attach；24 条 ambiguous；7 条 tnc（§2.5）。
- 48 条非 F3 行（22 模板 / 17 题）中，2 compiled、6 merged；
  这些不是“F3 漏掉的欠账”，而是 wildcard 在主侧的正常路由（§2.1）。
- 以上全部是**分母/覆盖**，不是净增；任何收益必须全 298 配对实验。

---

## 6. 证据索引

| 结论 | 证据 | 强度 |
|---|---|---|
| F3 = 178 行 / 52 题 / 277 上下文事件 | `[P3:138,219]`；M1 | D1 |
| 992 不是 F3；= 178 + 407 + 407；与 864 重叠 814 | `[P3:123-143]`；`[CODE-B:1514-1516,1529-1531,1602-1604]` | A |
| F1 对 dummy 计 `*` 元素 ⇒ 正常底物必 F1 拒 | `[CODE-C:258-264]`；RDKit dummy 符号 | A |
| F2 主组分选择/扣除/整袋规则 | `[CODE-B:640-714]` | A |
| `_cosub_has_wildcard_atom` 覆盖裸 `*`/`[H]*[H]`/`*C=O` | `[CODE-B:571-587,656-662]` | A |
| F3 分支：不 F5、不编译、`f5=not_evaluated`、`route=wildcard_blocked` | `[CODE-B:1499-1517]`；`[TEST-C:280-305]` | A |
| 整袋拦截（不是只拦 wildcard 组分） | `[CODE-B:708-712]`；`[TEST-S:294-313]` | A |
| clean bag 正控仍 supply | `[TEST-S:263-292]` | A |
| 72 模板 / 5 结构类 / 3 形态 / 6 政策分区 | M1-M4；`[TPL]` SHA 匹配 `[BID:2-5]` | A（资产）/ D1（行选择） |
| dummy 不在 `center_atoms`（0/72）；中心非空（72/72） | M3；`[TPL].center_atoms` | A |
| 85 行（76 确定 + 9 可能）dummy 在 L1；50 行 spectator XH2；11 行 reactive attach；1 行 spectator attach；24 行 ambiguous；7 行 tnc | M4；`[CODE-C:357,769,817-889]` | A |
| 166 行非 dummy 元素账 `{}`；12 行非零 | M5 | A |
| 26/52 hit@1、35/52 strict、2 partial、15 unmatched；9 无 compiled、6 strict | M6；`[P3:88,219,448]` | D1 |
| 48 条非 F3 行：2 compiled、6 merged、5 ambiguous、3 defer、32 reject | M1+M2；`[WL]` outcome/reason | D1 |
| 前端执行输入严格身份多重集 | `[CODE-P:196-260]`；`[CODE-B:1003-1006]` | A |
| 事件级共底物合同 | `[CODE-P:437-490]` | A |
| 计划 §4 P3 / §6 红线 | `[PLAN:149-162,181-195]` | A |

---

## 7. 未知清单（不估算）

1. **真实缺中心**：178 条中底物真的没有中心的比例 —— **unknown**；F3 没跑 F5。
2. **题型**：52 qid 的题型分布 —— **unknown**；qid 哈希、`[METRICS]` 无题型、
   题面读取禁止。
3. **底物**：52 题的底物类别/骨架分布 —— **unknown**；`[WL]` 无 SMILES、
   封存 run 禁止。
4. **变换类型名**：水解/氧化/转移等 —— **unknown**；模板资产无 EC/反应类型
   元数据，本轮不联网、不猜。
5. **B1 的化学可替换性**：`XH2` 能否封闭映射到水/O/S/Se；哪些模板适用；
   —— **unknown**（D3，等化学评审）。
6. **B1 的 F5 pass 率/编译成功率**：需要 D2 回放；未做。
7. **B1 的题级收益/损失**：需要模型运行与全 298 配对；不在本轮。
8. **模板 rhs dummy 的产物处理**：供货层替换后，模板 rhs 仍含 dummy；
   产物派生是否忽略/保留 dummy，逐行 unknown（D2）。
9. **48 条非 F3 行的化学正确性**：2 compiled/6 merged 是否化学有效
   —— unknown（D3）。
10. **7 条 tnc 行与 remap 的交互**：F5 defer 后 remap 是否改变中心
    —— unknown（D2）。
11. **`[WL]` 非冻结成员**：若只认 SHA256 成员，本文的 qid/模板级数字
    应写 unknown；候选级 178/52 仍由 `[P0D]` 支持。
12. **事件归因**：每条候选对 277 事件的贡献 —— unknown；277 是题级上下文。

---

## 8. 边界声明

- 本报告只做规则级分析、政策选项与评审请求稿；**不替 CC/老师拍板**，
  不预注册，不承诺收益。
- 只读：未改代码、未改判据、未改封存批根、未调用模型、未连 HPC、未 push。
- 未读金标、题面、`reference_graphs`、`env`、key；未读封存逐题 `payload.json`；
  未输出任何化学结构串/反应式/题面文本。
- `[WL]` 是 P0-D 输入副本，不是 SHA256 证据成员；所有派生数字已标
  “重算/只读测量”。若只认官方 SHA256 成员，这些列写 `unknown`，
  但候选级 178/52 结论不变。
- `[TPL]` 是批实际使用的模板资产，SHA256 与 `[BID:2-5]` 一致；本文只用它做
  结构画像，不把它当金标/题面。
- 所有“覆盖行数/上界”都不是净收益；所有 unknown 保持 unknown。
- 代码引用是 HEAD `966bc56`；与 `[P3]` 快照 `11aeeaf` 的 builder/compiler
  两个文件 diff 为空。
- 只新增本文件与 `docs/P3_F3_WILDCARD_CHEM_REVIEW_REQUEST_2026-10-21.md`；
  未改任何既有文档；未碰 T-I 锁定文件/P2 工作树。

---

## 附录 A：复算口径（只读）

### A.1 F3 行选择（M1）

```text
pool = json.load(/tmp/th_pool_diag.json)          # SHA256 57316fbd…b65b72a2
for qid, d in pool.items():
    for c in d["candidates"]:
        if c["channel"] == "analog"
           and c["reason"].split(":")[0] == "no_alignment"
           and c["f5"] == "not_evaluated":
            F3.append((qid, c["record_key"].removeprefix("tpl-")))
# 结果：178 行 / 52 qid / 72 个唯一 record_id
# 对照：pool_diagnostics.analog_cosub_supply_wildcard_blocked 求和 = 178
```

### A.2 模板连接（M2）

```text
templates = {row["record_id"]: row for row in
             jsonl("assets/analog/corpus_templates_v1.jsonl")}
assert all(rid in templates for rid in F3_record_ids)   # 72/72
# 无重复：每个 record_id 只命中 1 行
# 资产 SHA256 = 8f3f2c1a…ccfad92 = [BID].analog_corpus_sha256
```

### A.3 结构/L1 判定（M3/M4/M5）

```text
for each template:
    lhs_components = mapped_lhs.split(".")
    for comp in lhs_components:
        mol = MolFromSmiles(strip_map(comp))
        dummies = [a for a in mol.GetAtoms() if a.GetAtomicNum() == 0]
        form = "bare"   if dummy has no heavy neighbor and no H
               "XH2"    if dummy has no heavy neighbor and 2 H
               "attach" otherwise
    tx = extract_mapped_transform(mapped_lhs, mapped_rhs)   # [CODE-C:357]
    l1 = l1_maps_of_transform(tx)                            # [CODE-C:769]
    dummy_in_l1 = any(dummy atom map in l1)
    component_has_l1 = any(component atom map in l1)
    # shell=2 保留集：[CODE-C:817-857]
    # 非 dummy 元素账：去掉 atomicNum==0 后 rhs - lhs
```

- `extract_mapped_transform` 抛 `transform_no_change` 的 7 个模板单列 tnc；
  不把异常当 wildcard 化学结论。
- 所有解析用 RDKit 2026.03.6（`depending43` 环境）；解析失败按 code 口径
  fail-closed/串面 `*` 回退，不猜结构。

### A.4 统计口径

- 行 = 候选尝试行（一个 qid × 一个模板一行），不是已调度 spec，不是事件。
- 题 = 至少有一条该类的 qid；子类题数有重叠，不能相加。
- 模板 = `record_id`（不是 `template_id`；72 个 record_id 各 1 行）。
- 事件 = `[P3:219]` 的 277，是题级上下文，不是 F3 直接事件。
- 百分比只在明确分母时给；不给“可回收题数”。

### A.5 复算等式（必须闭合）

- 178 = 76（确定在 L1：reactive bare）+ 9（可能在 L1：ambiguous attach+bare）
      + 86（dummy not in L1）+ 7（tnc）
- 85 = 76（reactive bare）+ 9（ambiguous attach+bare）
- 86 = 50（spectator XH2）+ 1（spectator attach）+ 11（reactive attach）
      + 20（ambiguous attach）+ 4（ambiguous XH2+attach）
- 72 = 29（L1 模板：24 bare + 5 attach+bare）
      + 36（notL1 模板：18 XH2 + 1 attach + 8 attach + 5 attach + 4 XH2+attach）
      + 7（tnc）
- 178 = 30 + 108 + 4 + 31 + 5（§2.3 结构类）
- 178 = 76 + 50 + 11 + 1 + 20 + 4 + 9 + 7（§2.5 分区）
- 166 + 12 = 178（非 dummy 元素账净零/非零）

> 以上等式全部由只读测量闭合；`[WL]` 非冻结成员的限制见 §0.2。