# P3 F3 WILDCARD 化学评审请求（2026-10-21）

> **题域标签：[298 域] = RHEA 通用酶学 / 已见题（post-hoc）。**
> 本请求只在该题域成立；与 dev（B1 环境路径中间步骤）双向不外推。
>
> **请求性质：独立化学评审（规则级，只读）。**
> - **零金标、零题面、零 `reference_graphs`、零 `env`/key、零封存逐题 run。**
> - 本请求不含任何底物/产物/题面 SMILES；只含**模板组分的聚合元素式与计数**。
> - **评审者只读、无执行权限**：不得运行代码、不得读金标/题面/封存 run、
>   不得调用模型、不得连接 HPC、不得编造执行结果。
> - 评审者结论是**建议**，不替代正链评审；采信按“与源码及程序证据互证”原则，
>   到互证程度为止（AGENTS.md 既有原则）。
>
> **请求对象：** F3 `wildcard_blocked` 的化学边界与政策选项 B（窄 wildcard
> 白名单）是否可定义；重点是 **B1：spectator `XH2` 类**。
>
> **配套文件（评审者可读）：**
> - `docs/T_H_P3_O4_F3_WILDCARD_2026-10-21.md`（规则级分析、全部计数与证据索引）
> - `src/pathway_v43/pollutant/s5b_builder.py`（`analog_cosub_supply` /
>   `_cosub_has_wildcard_atom` / F3 分支）
> - `src/pathway_v43/pollutant/s5b_compiler.py`（`template_elements_fit` /
>   `build_center_query` / `compile_donor_template`）
> - `src/pathway_v43/pollutant/production.py`（执行输入严格身份核验）
>
> **数字出处：** 本请求 §1.2、§1.4、§1.5 的计数逐项出处见配套分析
> `docs/T_H_P3_O4_F3_WILDCARD_2026-10-21.md` §6（证据索引）与 §0.2（M1-M6
> 测量定义）。本请求只复述结论，不把复述当独立证据。
>
> **不要读：** 金标、题面、`reference_graphs`、`env`、key、封存逐题 run、
> `reports/**/runs/**/payload.json`。

---

## 0. 请求元数据与 provenance 头（回复时请照抄/填写）

```text
request_id: P3-F3-WILDCARD-CHEM-2026-10-21
domain_tag: 298 (RHEA general enzymology / seen questions, post-hoc)
requester: T-H P3 O4 (read-only analysis)
reviewer:
review_channel:
review_date:
inputs_read:
execution: none
model_calls: none
gold_questions_text: none
reference_graphs: none
sealed_runs: none
limitations:
independence_statement: 本评审为独立化学建议；不背书评审者独立性；
  结论采信到与源码/程序证据互证的程度为止。
```

---

## 1. 背景：F3 wildcard 是什么（自包含）

### 1.1 代码合同（规则级）

在 analog 通道，模板的 `mapped_lhs` 可能有多个组分。若 F1 元素门不通过
（正常底物上含 dummy 的模板必然不通过，因为 dummy 被计为元素 `*`），
构建器会调用 `analog_cosub_supply`：

1. 选与底物最相似的 lhs 组分为“主反应物”（Tanimoto 最大；并列取后位；
   全不可解析时回退重原子数最大）；
2. 供给 = lhs 组分按位置扣除主组分那一份后的全体（原序、精确多重集）；
3. **若供给中任一组分含原子序数 0 的 dummy 原子 ⇒ 整袋 `wildcard_blocked`，
   不供给、不编译、不跑 F5**；候选行记 `f5=not_evaluated`、
   `reason=no_alignment`、`route=wildcard_blocked`；
4. 若 wildcard 组分被选为**主组分**，它不进供给，F3 不触发（T-H r2 有
   48 条这样的非 F3 行，其中 2 compiled、6 merged）。

**F3 挡的是“要供给的共底物组分含未定义元素”，不是“反应中心缺失”。**

### 1.2 已测事实（只读，A/D1）

| 事实 | 值 | 说明 |
|---|---:|---|
| F3 候选行 / 题 / 模板 | **178 / 52 / 72** | `[WL]` + 模板资产 SHA 匹配批身份 |
| 模板 `center_atoms` 非空 | **72 / 72** | 中心不是“未定义” |
| dummy 原子出现在 `center_atoms` | **0 / 72** | dummy 不在模板声明的中心 |
| dummy 原子落在编译器 L1（中心查询） | **85 行（76 确定 + 9 可能）** | 查询会原样包含 dummy；具体底物无法匹配 |
| dummy 不在 L1 | **86 行** | 中心查询不含 dummy |
| `transform_no_change`（无 L1） | **7 行** | F5 会 defer，编译走 remap |
| 非 dummy 元素账 `rhs-lhs = {}` | **166 / 178 行** | 非 dummy 部分净零；**不等于 wildcard 组分一定是旁观** |
| 非 dummy 元素账非零 | **12 / 178 行** | 非 dummy 部分不平衡；wildcard 组分可能参与，需评审 |
| F3 题已有 compiled/merged 候选 | **43 / 52** | 26 hit@1、35 strict、2 partial、15 unmatched |
| F3 题无 compiled/merged 候选 | **9 / 52** | 其中 6 strict（5 hit@1 + 1 rank 5）、3 unmatched |
| F3 是该题唯一候选类 | **0 / 52** | 不能按 178 条推题级收益 |

> **85/86 的口径：** 85 = 76 确定 + 9 可能。9 行是 attach+bare 混合模板，
> 至少一个 dummy 在 L1，但供给的是哪一个需底物/main_idx，`[WL]` 无此字段；
> 表把这 9 行暂计入 L1 上界，所以 **notL1 86 是下界**，真正“供货层替换一定
> 不够”的是 **76 行**。若 9 行实际供给 attach，则归 notL1（仍是 ambiguous，
> 不能直接当 B1）。
>
> **名词区分：** `center_atoms` 是模板声明的中心 map 集合；编译器 L1 是从
> 键/电荷/手性变化算出的编辑中心。前者回答“模板是否把 dummy 声明为中心”
> （0/72）；后者回答“编译查询是否含 dummy”（85）。两者不是同一集合。

> **口径警告：** `992` 不是 F3。它是 `analog_pregate_skipped` 计数器
> = 178（F3）+ 407（供给分支 F5 absent）+ 407（no_supply 分支 F5 absent），
> 与 864 条 F5 重叠 814，禁止相加。本请求只用 **178 / 52 / 72**。

### 1.3 三个 wildcard 形态（本请求的分类基础）

| 形态 | 结构定义 | 组分内重原子 | 模板 / 行（组分级，可重叠） | 化学读法 |
|---|---|---|---:|---|
| **裸 `*`** | 单个 dummy 原子，无键、无 H、无重邻居 | 0 | 29 / 85 | 完全未指定的单价原子/基团 |
| **`XH2`** | dummy 原子 + 2 个显式 H，无重邻居 | 2（H 计） | 22 / 54 | 未指定元素的二价原子（可能是 O/S/Se/…） |
| **attachment** | dummy 与 1 个重原子成键，其余骨架已定义 | ≥1 | 30 / 52 | 有骨架，只缺一个开放价/R 位 |

> 模板可含多个 wildcard 组分，所以上表模板/行数之和 > 72/178；
> 这是**组分级**计数，不是互斥模板分类。

### 1.4 政策相关互斥分区（本请求的核心）

| 分区 | 行 | 题 | 模板 | 化学含义 | 是否值得 B |
|---|---:|---:|---:|---|---|
| **L1：dummy 在中心查询** | **85**（76 确定 + 9 可能） | 38 | 29 | 中心查询含 `*`；具体底物无法匹配；供货层替换不够 | 76 否；9 unknown |
| ├ 裸 `*`（唯一 dummy 组分） | 76 | 38 | 24 | 裸 dummy 是键变化原子 | 否 |
| └ attach+bare 混合（供给哪个 unknown） | 9 | 4 | 5 | 多 dummy，供给角色需底物 | unknown |
| **notL1：dummy 不在中心查询** | **86** | 28 | 36 | 中心已定义；wildcard 在外围 | 见下 |
| ├ **spectator `XH2`** | **50** | **22** | **18** | 二价未指定元素；纯旁观；元素账 `{}` | **唯一有规模的 B1 候选** |
| ├ spectator `attach` | 1 | 1 | 1 | 有骨架、开放价、不在中心；骨架很小 | 规模太小 |
| ├ reactive `attach` | 11 | 8 | 8 | 骨架含 L1（被转化）；R 基替换会改变反应分子 | 高风险；不建议 |
| ├ ambiguous `attach` | 20 | 4 | 5 | 主/辅角色需底物 | unknown |
| └ ambiguous `XH2+attach` | 4 | 2 | 4 | 混合形态；角色未知 | unknown |
| **tnc：`transform_no_change`** | **7** | **1** | **7** | 无 L1；F5 defer，编译走 remap | 与 remap 分开评 |
| **合计** | **178** | **52（有重叠）** | **72** | | |

**关键：**

- **76 行确定**（+9 行可能）的中心查询含 dummy；供货层替换不能解决这 85 行，
  必须实例化模板 lhs/rhs，或维持 blocked。
- **50 行 / 22 题 / 18 模板**是 spectator `XH2`：dummy 不在 L1、组分不在中心、
  非 dummy 元素账 `{}`。这是唯一有规模、化学上还有讨论空间的类。
- **11 行 reactive `attach`**：R 基在反应分子上；替换会改变被转化的分子，
  不是“旁观取代基”。
- **12 行非零元素账**：wildcard 组分参与元素变化；不在 B1 范围。
- **7 行 tnc**：与 remap 交互，不能与 B1 混在一起。

### 1.5 attachment 组分的骨架类别（聚合，不含 SMILES）

> 下表按“含该类组分的模板/行”计，**可重叠**；不是互斥分类。
> 只给元素式、环数、dummy 连接方式，不给结构串。

| 骨架类别 | 元素式/结构特征 | 模板 | 行 | 题 | 备注 |
|---|---|---:|---:|---:|---|
| steroid-like | C19–C21、O1–O2、4 环、全单键或少量双键；dummy 接在环碳上 | 14 | 33 | 6 | 骨架大；但多为 reactive（骨架含 L1） |
| CoA-like | C24 N7 O18 P3 S、3 环、9 芳香原子；dummy 接在碳上 | 1 | 1 | 1 | 可能是酰基载体；dummy 未映射 |
| nucleotide/phosphate-like | C5/C8、N1、O6、P1；2 个 dummy 接在 O 上 | 3 | 3 | 1 | 可能是磷酸二酯/核苷酸类；dummy 未映射 |
| sugar/polyol-like | C3–C6、O3–O6、无环或 1 环；1–4 个 dummy 接在 C/O 上 | 9 | 23 | 8 | 多羟基骨架；R 位多 |
| small fragment | ≤3 重原子、无环；C1O1/C1O2/C2O1/O1 等 | 9 | 13 | 9 | 骨架太小，替换等于猜分子 |
| 裸 `*` / `XH2` | 无重原子 | 29 / 22 | 85 / 54 | 38 / 22 | 见 §1.3 |

**读法：** 大骨架（steroid/CoA/nucleotide）不自动等于“可安全供给”：
- steroid-like 多数是 reactive：骨架本身含 L1，R 位替换会改变被氧化的分子；
- CoA-like 的 dummy 未映射到 rhs，可能是酰基链的开放价，替换需要选链长；
- nucleotide/phosphate-like 的 dummy 接在 O 上，可能是磷酸酯的 R 基，
  替换会改变电荷/质子化/配位；
- sugar/polyol-like 多 R 位，替换组合爆炸，且立体/区域化学未定义。

**没有一个大骨架类别同时满足“spectator + 元素账净零 + 有规模”。**
唯一有规模的是 `XH2`（50 行），但它不是“有骨架的载体”，只是一个
“二价未指定原子 + 2H”。

---

## 2. 代码合同（评审所需的规则细节）

### 2.1 `analog_cosub_supply` 的状态

```text
lhs_comps = mapped_lhs.split(".")
if len(lhs_comps) <= 1: return no_supply
main_idx = argmax Tanimoto(component, substrate)   # tie -> later
main_cn = cn_identity(stripped[main_idx])
if main_cn is None: return no_supply               # fail-closed
supply = [comp for i, comp in enumerate(lhs_comps) if i != main_idx]
if not supply: return no_supply
if any(has_dummy_atom(comp) for comp in supply):
    return wildcard_blocked                        # whole bag
return supply
```

- `has_dummy_atom`: RDKit 解析成功时 `any(atomicNum == 0)`；解析失败时回退
  字符串 `*` 探测（不猜结构）。
- `wildcard_blocked` 是**整袋**：不是只拦 wildcard 组分，也不是只拦裸 `*`。
- F3 分支不调用 F5、不编译；`f5=not_evaluated`、`execution_input_source=None`。

### 2.2 中心查询（为什么 85 行供货层替换不够）

编译器中心查询（`build_center_query`）把 L1 原子 + 2 壳层原子按元素/芳香/
键级复制成查询子结构。若 dummy 原子在 L1，查询中会有一个 `atomicNum==0`
的原子；**RDKit 2026.03.6 只读实测：含 dummy 的 query 对普通 C/O 分子零命中
（裸 dummy、dummy+C=O、dummy+2H 三种形态都零命中；dummy 只匹配 dummy）**。
因此：

- **dummy 在 L1**：供货层替换（只改 `sub_supplied`）不够；必须把模板 lhs/rhs
  的 dummy 也实例化，否则 F5/编译仍会拒绝。
- **dummy 不在 L1**：中心查询不含 dummy；供货层替换在查询层面不被挡，
  但化学正确性仍需评审。

> 这是从 `build_center_query` + RDKit 匹配语义推出的**代码层期望**，不是
> 本批的执行回放结果；需要 D2 回放确认（评审者无执行权限，不得写成已执行）。

### 2.3 执行输入严格身份

生产层在事件前核验：

```text
declared multi-set(strict_identity(execution_input_smiles components))
  == multi-set(strict_identity(substrate) + strict_identity(declared co-substrates))
```

不等 ⇒ `ProductionContractError`，零事件/零提交。任何白名单替换都必须进入
`co_substrate_states`，不能用字符串拼接绕过。

### 2.4 判分

**零改动。** criteria-v2 不变；不按类加分/豁免；不读金标；B 试点必须全 298
配对报告新增/损失/净增。**18/50 等覆盖数不是收益。**

---

## 3. 请评审的化学问题（逐条 PASS / FAIL / UNKNOWN + must-fix）

> **判定口径：**
> - **PASS** = 维持现状（blocked）在化学上是必要的；或提议的窄白名单在
>   给定证据下不可辩护。
> - **FAIL** = 存在一个具体、可复现、化学上可辩护的替换/规则；请给出
>   替换身份、适用条件、正控/负控。
> - **UNKNOWN** = 现有信息不足以判；请列出需要补充的**非金标**证据
>   （模板级结构、元素式、中心距离、R 基角色等）。
>
> 每条请给：`verdict` + `rationale` + `must-fix` + `evidence_cited`。
>
> **以下各题的“期望”只是当前证据的倾向，不是要求评审者同意；请独立判，
> 允许给出与期望相反的 PASS/FAIL/UNKNOWN。**

### Q1. 三种形态的“不供给”是否化学上必要？

对 **裸 `*`（85 行）**、**`XH2`（54 行）**、**attachment（52 行）** 分别判：
- 该形态是否有一个**唯一/封闭**的具体化学解释？
- 若无，维持 blocked 是否化学上必要？
- 若有，是什么？在什么条件下？

**期望：** 裸 `*` 大概率 PASS（无具体身份）；`XH2` 可能 UNKNOWN/FAIL
（取决于能否封闭）；attachment 需分类讨论。

### Q2. `XH2` 能否封闭替换为水（或 O/S/Se 的封闭集）？

- `XH2` = dummy + 2 个显式 H、无重原子；这是一个**二价未指定元素**。
- 在 **50 行 spectator `XH2`** 中，dummy 不在中心查询、组分不在中心、
  非 dummy 元素账 `{}`。
- 问题：
  1. 把 `XH2` 读成水（O）是否在所有 18 个模板中都化学可辩护？
  2. 若不是水，O/S/Se 的封闭集是否可辩护？价态/质子化/溶剂条件是什么？
  3. 有没有模板的上下文（中心反应类型、其他组分、元素账）能**唯一**确定
     它是水，而不是 H2S/其他二价原子？
  4. 若替换为水，净反应/记录契约/产物集合会不会改变？

**期望：** 若不能给出“逐模板可判”的封闭集，请判 PASS（维持 blocked）
或 UNKNOWN（列出所需非金标证据）。**不要把“看起来像水”当证据。**

### Q3. spectator `attach`（1 行 / 1 模板）是否值得定义？

- 该组分有骨架、开放价、不在中心；骨架很小（<10 重原子）。
- 问题：R 基替换是否会改变分子的化学身份/净反应？是否有任何可辩护的
  封闭替换？若没有，PASS。

### Q4. reactive `attach`（11 行 / 8 模板）是否可能“外围 R 基无关”？

- 这些组分的骨架含 L1（被转化），dummy 是外围 R 位；dummy 本身不在 L1。
- 问题：
  1. R 基是否可能完全不参与反应中心/过渡态/产物身份？
  2. 若 R 基是“远端惰性基团”，能否用一个封闭集替换而不改变净反应？
  3. 若 R 基影响溶解度/质子化/配位/立体，是否必须维持 blocked？
- **注意：** 不要因为“R 基不在中心”就假定它化学无关；请给出判据。

### Q5. 裸 `*`（85 行；76 确定在 L1）是否有任何可辩护的模板级实例化？

- 裸 `*` 是键变化原子（插入/删除/转移一个 generic 原子），不是旁观 R 基。
- 问题：
  1. 是否有任何模板的上下文能唯一确定这个原子（例如 O 插入、S 转移）？
  2. 若没有，维持 blocked 是否必要？
  3. 若要做，是否必须实例化模板 lhs/rhs（而不是只改供给串）？
- **期望：** 若无逐模板唯一证据，PASS。

### Q6. 非 dummy 元素账 `{}` 是否足以证明“spectator”？

- 166/178 行的非 dummy 元素账为 `{}`；12 行非零。
- 问题：
  1. 元素账净零是否足以证明 wildcard 组分不参与反应？
  2. 还需要哪些证据（键变化、中心距离、产物侧身份、同位素/质子转移）？
  3. 12 行非零元素账中，wildcard 组分是反应物还是产物？是否一律禁止供给？

### Q7. 正控/负控：什么样的合成反例会推翻一个白名单？

请给出**不依赖金标**的具体控制：
- 正控：白名单替换后应编译成功/产物身份正确的合成例；
- 负控：错误元素/价态/电荷/净反应必须被拒；
- 局部性：一个 wildcard 组分被替换、另一个未替换时必须整袋拒绝；
- 路由：wildcard 在主侧（非 F3）的 48 行必须零变化。

### Q8. 当前 blanket block 是否有“假阴性”风险？

- 是否存在化学上**必须**供给、但被 F3 误拦的类？
- 若有，如何在没有金标/题面的情况下证明（模板级结构 + 元素账 + 中心距离）？
- 若没有，PASS。

### Q9. 对 12 行非零元素账的具体判读

请对以下元素差类别（聚合，不含 SMILES）分别判：
- `{O:-1}`（2 模板 / 2 行）
- `{C:-5, O:-5}`（1 / 4）
- `{C:8, O:-5, P:-1, N:-1}`（1 / 1）
- `{C:13, O:-5, P:-1, N:-1}`（1 / 1）
- `{C:-4, O:-5, P:-1, N:-1}`（1 / 1）
- `{C:-20, O:-5}`（1 / 1）
- `{C:12, O:-3}`（1 / 1）
- `{C:-6, O:-5}`（1 / 1）

问题：wildcard 组分是被消耗/产生的反应物/产物，还是账差来自其他组分？
是否一律禁止 B1？若某一类可定义，需要什么额外证据？

### Q10. 最终政策建议

请在三选一中给结论：
- **A：维持现状**（wildcard 一律不供给）；
- **B：窄白名单**（只允许经评审的类；本请求重点是 B1 spectator `XH2`）；
- **C：通用共底物供给**（不推荐）。

并给：
- 若选 B，最小白名单类别、替换规则、适用条件、失败模式；
- 若选 A，需要记录哪些“不做”的反证；
- 若选 UNKNOWN，列出需要补充的非金标证据与最小实验（零模型/零金标）。

---

## 4. 评审边界（请严格遵守）

1. **只读**：不运行代码、不写文件、不读金标/题面/`reference_graphs`/`env`/key/
   封存逐题 run；不调用模型；不连 HPC；不 push。
2. **不编造执行结果**：任何“编译成功/失败”“F5 pass/absent”“产物正确”
   都必须标为 **待执行验证**，不得写成已执行事实。
3. **不做收益推断**：不得从 178/992/50/22 推“可回收多少题/多少分”；
   不得把覆盖行数当净增。
4. **不改判分口径**：不提议按类加分/豁免；不提议放宽 `no_alignment`。
5. **不引入金标**：若某结论必须看金标/题面才能判，请写 UNKNOWN，并说明
   需要哪类非金标证据。
6. **不替 CC 拍板**：本评审是化学建议；政策/预注册/费用由 CC 决定。
7. **不背书独立性**：评审者结论与源码/程序证据互证后才采信；不因
   “多个模型同意”而升级。

---

## 5. 回复格式模板（请逐条填写）

```markdown
# P3 F3 WILDCARD 化学评审回复

## Provenance
request_id: P3-F3-WILDCARD-CHEM-2026-10-21
domain_tag: 298
reviewer:
review_channel:
review_date:
inputs_read:
execution: none
model_calls: none
gold_questions_text: none
reference_graphs: none
sealed_runs: none
limitations:
independence_statement: 本评审为独立化学建议；不背书评审者独立性；
  结论采信到与源码/程序证据互证的程度为止。

## Verdicts
| ID | verdict (PASS/FAIL/UNKNOWN) | rationale | must-fix | evidence_cited |
|---|---|---|---|---|
| Q1a bare `*` | | | | |
| Q1b `XH2` | | | | |
| Q1c attachment | | | | |
| Q2 `XH2`→water/closed set | | | | |
| Q3 spectator attach | | | | |
| Q4 reactive attach | | | | |
| Q5 bare `*` template instantiation | | | | |
| Q6 element-delta `{}` sufficiency | | | | |
| Q7 controls | | | | |
| Q8 false-negative risk | | | | |
| Q9 12 non-zero delta rows | | | | |
| Q10 policy A/B/C | | | | |

## Whitelist recommendation (if any)
| class | allow? | replacement rule | scope predicates | controls | evidence |
|---|---|---|---|---|---|

## Must-fix list
1. ...
2. ...

## Unknowns / required non-gold evidence
1. ...

## Policy recommendation
- A / B / C:
- Why:
- Stop conditions:
```

---

## 6. 附：本请求不提供的材料（避免误读）

- **不提供**底物/产物/题面 SMILES、任何 qid 的题面、任何金标图。
- **不提供**逐题封存 run、native export、payload、reference_graphs。
- **不提供**模型输出/评分结果；本文的 26/35/43/9 等桶来自冻结 metrics 的
  只读重算，不是本请求的化学证据。
- **不提供** RHEA/EC 元数据；模板资产只有 `mapped_lhs/mapped_rhs/
  center_atoms/env_shell/qc_flags`。若评审需要反应类型名，请标 UNKNOWN
  并说明需要哪类非金标元数据。

**只提供的：** 规则级代码合同、模板组分的聚合元素式/环数/dummy 连接方式/
中心距离/元素账、以及 178/52/72 的分区计数。**没有任何可反推题面或金标的内容。**

---

## 7. 一句话请评审回答的问题

**“在 50 行 spectator `XH2` 中，是否存在一个逐模板可判、封闭、化学上可辩护的
具体替换（首选水；或 O/S/Se 的封闭集），使得供给它不改变净反应/记录契约？
如果不存在，维持 `wildcard_blocked` 是否是化学上必要的？如果存在，最小白名单
和正负控是什么？”**