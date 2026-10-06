# mimo 化学评审回应:pollutant_pathway_v1 化学判据 v2(第二轮)

- 日期:2026-10-05(第二轮;回应 `docs/mimo_ppv1_chem_review_request.md` v2 文本)
- 评审对象:S0–S2 回修后的五条判据 v2 文本 + 实现(`src/pathway_v43/pollutant/`,ppv1-*-2);**未冻结**
- 范围与证据边界:只评规则级表述;源码只读核对;全部探针用合成分子/合成账本,
  无金标/题面/封存逐题数据;未运行真实模型、未跑真实题目
- 独立复跑:`pytest tests/test_ppv1_{profile,domain,s2,rework}.py -q` →
  **129 passed, 1 skipped**(与交付书 §7 一致);本轮不以测试数量作结论,
  每条意见锚定可复跑的探针或源码位置
- 可复跑探针(合成夹具,临时证据;按 Codex §5 纪律,下列反例须在冻结前
  转成仓库回归测试,不依赖临时路径长期存在):
  - `/private/var/folders/mg/7frznpjj7y16hqgk_g6h_28c0000gn/T/opencode/ppv1_r2_probe.py`
    (身份键/元素账/admission/条件聚合)
  - `/private/var/folders/mg/7frznpjj7y16hqgk_g6h_28c0000gn/T/opencode/ppv1_r2_probe2.py`
    (供体诊断六场景)
  - 复跑:
    ~~~bash
    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/Volumes/CC/Enzyme_Agent/dependingv43/src \
      /Users/cc/miniconda3/envs/depending43/bin/python \
      /private/var/folders/mg/7frznpjj7y16hqgk_g6h_28c0000gn/T/opencode/ppv1_r2_probe.py
    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/Volumes/CC/Enzyme_Agent/dependingv43/src \
      /Users/cc/miniconda3/envs/depending43/bin/python \
      /private/var/folders/mg/7frznpjj7y16hqgk_g6h_28c0000gn/T/opencode/ppv1_r2_probe2.py
    ~~~
- 格式:逐条给 结论 / 直答 / 可直接落进规则文字的修改 / 风险点;不作总体评价

---

## 1. 判据一:分子身份

### 1.1 结论:**有条件同意**

第一轮 C1–C4 已落地(sanitize 后才生成 state_id、分轴 fidelity、增强立体入身份键、
派生等价类不入身份/禁 CN 去重),本轮新增两条冻结前条件:

- **C5(分裂)**:`ABS` 立体组与"无立体组"是同一立体事实,必须归一或登记为已知分裂;
- **C6(未落地条款标注)**:判据一第 4 条的 `edge_kind`(互变/质子化边)与第 5 条的
  `basis=scoring_key` 当前**无实现、无测试**,冻结文本须标注"未实现(S3 落地)",
  不得与已实现条款并列呈现。

### 1.2 直答

**(a) 增强立体序列化的键设计:无碰撞,有一处分裂。**

实测(探针 1):

| 输入 | state_id |
|---|---|
| `F[C@H](Cl)Br` | `cs_bfc4ac69054e81d064fd` |
| `… \|&1:1\|` | `cs_7980781f2f95d1f0ec61` |
| `… \|o1:1\|` | `cs_30c974462c49d0e874e9` |
| `… \|a:1\|` | `cs_4b97c9d3f324a8ad5aec` |

四态互不相同(碰撞已解决 ✓);原子映射号剥离后身份不变 ✓;Kekulé/芳香互写归一 ✓。

- **分裂风险(需处置)**:plain 与 `|a:1|` 的**基础串完全相同**,只差 SG 段。
  按默认语义,普通 isomeric SMILES 的全部已指定中心就是绝对构型,与 `ABS` 等价 ⇒
  同一立体事实得到两个 state_id。
- 碰撞风险其余各点我未发现:`|SG:…|` 段只由代码追加,SMILES 正文不含 `|`,分隔符无歧义;
  StereoGroup 序列化用重排后下标,与 canonical 秩同源,幂等 ✓;`strict_identity_of`
  与 state_id 同一事实源 ✓(第 2 条满足)。

**(b) archive 电荷轴 `as_written`:成立(同意 Codex 纠偏),但必须补一条转换历史条款。**

`as_written` 是关于**字符串**的诚实陈述(中性串电荷为零是合法结构事实),
它不等于"该 pH 下的物种分布"——这条边界判据一已写清。条件是:轴的判定依据只能是
**来源转换历史**,而当前实现里 `build_chemical_state(fidelity=…)` 的缺省值就是
`as_written`,`legacy_reader` 对全部存档产物无条件传 `archive_recovered_fidelity()`
(电荷/质子化两轴均 `as_written`),**没有任何字段记录该串是否经过中和/归一**。
即"依据是转换历史"在文本上成立,在数据结构上无处可读。

**(c) CN-only 与语法非法分开(R1 只收语法非法):成立(同意)。**

复跑确认:CN-only 参与物 ⇒ parse 检查 `unknown(structure_unavailable_legacy_cn_only)`
⇒ 不进 R1,admission 为 `retain_conditional` 且无 `R1:` 理由 ✓;通用工厂拒
`origin=legacy_cn_only` ✓;CN-only state_id 前缀隔离 ✓。
**但**同节有一处理由码压平,归入判据三 3.2(2)。

### 1.3 可直接落进规则文字的修改

1. **第 2 条后补一句(消分裂)**:
   > 增强立体组序列化前先归一:`ABS` 组按冗余注解剥离(其语义与普通 isomeric SMILES
   > 的默认绝对构型等价),`AND/OR` 组保留;故 `M` 与 `M |a:…|` 得同一 state_id,
   > 与 `M |&:…|` / `M |o:…|` 得不同 state_id。
   > (若不采纳归一,则须把"plain 与 ABS 得两个身份"登记为已知分裂特性,并在
   > 严格身份比对前对两侧做同一归一,否则 `strict_target_match` 会因注解差异判 False。)

2. **第 3 条补转换历史条款**:
   > 轴取值的判定依据是**来源转换历史字段**(如 `conversion_history` 含
   > `neutralized_by_cn` / `cn_normalized`),不是字符串长相;凡转换历史显示经过
   > 中和的来源,电荷轴与质子化轴必须记 `neutralized_by_cn`/`unknown`,
   > **不得默认 `as_written` 而不留痕**;转换历史未知时记 `unknown`。
   > 存档形(stereo/isotope=`absent_in_archive`)的电荷轴仍可 `as_written`,
   > 但 `identity_fidelity` 不得因此显示为无注记的 verified(见 1.4 风险 4)。

3. **第 4/5 条加实现状态标注**:
   > `edge_kind`(S3 落地)与 `basis=scoring_key` 当前**未实现**:
   > 冻结文本将二者标为 "contract clause, implementation pending",
   > 未落地前不得在报告中呈现该字段;`cn_identity` 的序列化输出须在同级
   > 输出 `basis: scoring_key`(现仅存在于代码注释)。

4. **第 1 条补同位素与氢的口径交叉引用**(与判据二 2.3(1)同源):
   > 身份键保留同位素;元素账不区分同位素(D/T 并入 H)。两轴口径不同,
   > 不得互相引用为"同位素已核"。

### 1.4 "程序上诚实但化学上误导"风险点

1. **ABS 分裂 → 供体被冤枉**:供体预期串写 `F[C@H](Cl)Br`,执行产物带 `|a:1|`
   ⇒ `strict_target_match=False`,差异只是注解写法,化学同一。
2. **CN-only 与结构态双身份**:同一实体两态并存是刻意设计(诚实),但若下游把
   `state_id` 当"物质唯一"键会双计 —— 展示层归组必须用评分键并带 `basis=scoring_key`,
   而该标记未实现(见 1.3(3))。
3. **未落地条款与已实现条款并列**:`edge_kind`/`scoring_key` 在文本中与已测条款同级
   措辞,读者会当成已有保障(第一轮"程序诚实但化学误导"的同族风险,方向是覆盖虚高)。
4. **`identity_fidelity=verified` + `reason=archive_form:…` 混读**:
   存档形缺立体却显示 verified(现只在 reason 里带注记),建议分轴呈现与判据一 fidelity 对齐。

---

## 2. 判据二:参与物计量与元素/电荷核算

### 2.1 结论:**有条件同意**

三条直答全部同意;新增两条冻结前条件:同位素/自由基口径写明、第 7 条(局部结构差)
标注未落地。

### 2.2 直答

**(a) 全氢计数口径:同意,复跑无重无漏。**

`element_counts_full` 实测:`C([H])([H])([H])[H]` → `C1 H4`(独立 H 顶点与属性 H
不双计)、`[H][H]` → `H2`、`O` → `H2`、`[NH4+]` → `N1 H4`、`CCO` → `C2 H6 O1` ✓。
`GetTotalNumHs()` 不含邻居顶点氢,与独立 `[H]` 顶点相加恰好覆盖 —— 口径正确。
**须补写两条**:
- **同位素氢并入元素 H**:实测 `[2H]OC(C)C` → `H8`。D/T 的差异只在身份/同位素轴体现,
  元素账不体现 ⇒ "element_accounting=verified" **不是** 同位素账已核;
- **自由基/未配对电子不在账内**:与"不含电子/质子计量"一致。身份层已区分自由基
  (实测 `C` 与 `[CH3]` 得不同 state_id),但 mimo 第一轮提过的 `radical` **保真轴**
  在 v2 被删且在 Codex §4 裁定表与 v2 请求中均无处置记录 —— 影响面是"来源是否丢失
  自由基信息"这一保真问题;不补轴须登记为已知缺口,不得静默消失。

**(b) 模式标注"仅数值相符"语义边界:同意。**

`COMMON_OMISSION_PATTERNS = {H2O, H+, O2, 2H}`,逐元素**精确相等**才标注,
语义字段明写"不证明实际缺该物质、不推断遗漏原因、不含电子/质子计量" ✓,
方向含 `reactant_side`/`product_side` ✓。Codex 收紧(缺 2H 不标 +2e)已落实 ✓。
两点收尾建议见 2.3(2)(3)。

**(c) violated → retain_conditional(不 reject):同意。**

复跑确认:缺 H 例 → `R5d:declared_account_violated` → `retain_conditional`,
不 reject、不进 R6 ✓;`unknown` 与 `violated` 分码 ✓;不补水/氧/辅酶 ✓;
电荷账前提(轴 == `as_written` 才算)已实现,且优先于"结构不可用"归因 ✓。

### 2.3 可直接落进规则文字的修改

1. **第 2 条补同位素/自由基口径**:
   > 元素账把 D/T 计入元素 H(同位素不入本账);自由基电子不入本账。
   > 本账 verified 仅指元素与形式电荷的数值闭合,不指同位素计量、
   > 不指电子转移、不指机制(与第 6 条同族纪律)。

2. **第 5 条把模式标签改成结构化字段并改名**:
   > `omission_pattern_matches: [{pattern, excess_side, missing_from_side,
   > element_delta}]`;方向词用"多出侧/缺写侧"而不是裸 `product_side`
   > (现 `H2O:product_side` 表示"产物侧多出 ⇒ 反应物侧缺写水",极易读反);
   > `H+` 模式改名或加注:`H+_count1`(仅表示 H 计数为 1 的模式名,
   > 不表示质子/电子计量)。

3. **第 7 条标注未落地**:
   > 局部结构差 `local_delta` 当前**无实现、无测试**(仓库内检索不到),
   > 本条为 pending 子句;冻结前二选一:补实现+夹具(系数未知只报方向、
   > 与 full_balance 各带状态/系数假设/适用范围),或标 "S3/展示层落地"
   > 并在本轮判据文本中显式排除出冻结范围。

4. **第 3 条补完整性取值封闭集**(消除"子型"歧义):
   > 完整性取值封闭为 `source_complete | declared_complete | partial | unknown`
   > **不引入 `complete_stoichiometric` / `complete_transformation` 子型**;
   > 转化级/汇总边语义由 `step_scope` 轴单独表达,不通过完整性子型表达。
   > (Codex 裁定"未声明 ⇒ unknown"已按现文本落实;写明无子型,避免读者去找不存在的枚举。)

### 2.4 "程序上诚实但化学上误导"风险点

1. **"元素账 verified" 与 "条件从未评估" 同屏**:见 3.2(1),本轮最大的 verified 面积
   虚高来自 admission,不在本判据;但展示层必须让 `element_accounting=verified` 与
   `condition_check` 状态同屏(第一轮同族意见,方向现在是"核得太少却显示全核")。
2. **D/T 并入 H 的假精确**:氘代底物参与的反应元素账"verified",读者会读成同位素也核过。
3. **`H2O:product_side` 方向词读反**:字符串标签本身在制造"水写在产物侧"的错觉。
4. **R2b 是纸面规则的风险**:零/负/非有限系数在**构造期**就抛
   `HypothesisContractError`(实测 null 系数被拒),不会进入 audit;
   若调用方不把 `detail` 映射为 `contract_violation` 传入 `decide_admission`,
   R2b 永远不触发(见 3.2(3))。

---

## 3. 判据三:admission 决策表

### 3.1 结论:**有条件同意**

R2b 落点同意、R5d/R5 分码同意、R7 保守同意;但 **R6"全部核实"的定义必须收紧**,
否则本轮最重要的假 verified 仍然存在,并且它与判据四直接冲突。

### 3.2 直答与修改

**(1)(最重要)R6 可在"条件从未评估"时达成 —— 实测复现。**

```
audit_hypothesis(hyp, states=…)        # 不传 context
condition_check = not_applicable | no_context
decide_admission(audit) = expand | R6:all_verified_no_conflict
```

配平、全系数已知、签名 verified 的假设,在**完全没有上下文**时拿到 `expand` +
`all_verified`;仓库 4 个 ppv1 测试文件里只有 2 处传 `context=`。
这同时违反判据四第 5 条(条件未知 ⇒ unknown ⇒ 不 compatible)与判据三 R5
(条件未知 ⇒ retain):缺输入被记成"不适用"而不是"未评估"。

**可直接落进规则文字(R6 与 not_applicable 定义):**
> - `not_applicable` 只表示**语义上不适用**(如 `multistep_summary` 汇总边、
>   诊断类 `not_run`),必须带不适用理由;
> - **因缺输入而未执行的检查记 `unknown(reason=…_not_run)`**,不得记 `not_applicable`
>   (首版具体化:`context is None` ⇒ `condition_check=unknown(reason=condition_assessment_not_run)`);
> - R6 条件改为:**全部检查 verified,且不存在 `unknown`/`violated`/因缺输入未执行的检查**
>   (即"全部核实"不含缺输入跳过);
> - `context is None` 的调用须在报告中显式出现 `condition_assessment_not_run`,
>   不得以"无冲突"措辞呈现。

**(2) R1 理由码压平(判据一 (c) 的关联项)。**

`participant_state_missing`(账本/引用完整性,F07 层)与 `unparseable_smiles`
(实际语法非法)在 audit 中是两个 `reason_code`,但 `decide_admission` 只看
`structure_parse_valence == violated` ⇒ 一律输出 `R1:structure_unparseable`。
**修改:** R1 只收 `unparseable_smiles`;悬空 state 引用走 R2b
(`contract_violated_representation`,理由码 `participant_state_missing`)
或单列 R1b;决策表加一行,理由码不压平。

**(3)R2b 的落点与措辞:同意,补触发路径。**

落点(R1/R2 之后、R3 之前)与"非化学"措辞都正确 ✓。
**补一句:** `contract_violation` 由调用方传入;构造期异常
(`HypothesisContractError.detail`)必须由调用方映射进 `decide_admission`,
否则 R2b 不可达 —— 这是接口契约条款,须写进决策表脚注。

**(4)R5d 与 R5 分码:同意,建议限定触发集合。**

代码里 R5d 触发条件是"**任意** check violated";当前只有元素/电荷能到达
(parse → R1、condition → R3 先行),故与文本"元素/电荷账 violated"暂等价。
**修改:** R5d 触发集合显式限定为 `{element_accounting, formal_charge_accounting}`,
其余 violated 用独立码(如 `declared_violated_other`),防止将来新增检查
静默挂进 `declared_account_violated`。

**(5)R7 空审计的保守保留:同意。** 复跑确认 R7 仅在全部检查 `not_applicable` 时触发,
理由与 R5 分开 ✓;配合 (1) 后,"部分 NA + 其余 verified ⇒ R6"的口子关闭,
R7/R6 边界才与文本一致。

**(6)P2-2 门禁适配的一处不可消费:** `AdmissionPolicy.from_dict` 拒绝
`DEFAULT_REJECT_GATES` 之外的门禁,故 mapper 产出的 `gate_atom_mapping_declared`
**无法**被策略配置为 reject 门禁。文本"供策略显式消费"须改为
"只读旁证;启用为拒绝门禁须扩本表并升政策版本"。

### 3.3 "程序上诚实但化学上误导"风险点

1. **`all_verified` 在零条件评估下达成**(3.2(1))—— 本轮最高优先级;
   它把"我们没看环境"呈现成"环境已核"。
2. **R1 吞掉引用完整性问题**:悬空引用显示为"结构不可解析",把账本缺陷说成结构化学问题。
3. **R5d 全集触发**:未来新增 violated 检查会被读成"声明账与结构不一致"。
4. **R3 覆盖率**:已知特性(文献少用 essential 字面),文本已登记"触发率偏低 ≠ 冲突罕见"
   ✓,保留原样。

---

## 4. 判据四:条件相容聚合

### 4.1 结论:**有条件同意**

(a) 基本成立(补一条 scope 派生纪律);(b) 三个缺口必须先定案(其中一个是文本与实现
互相矛盾);(c) 合取同意(补一条 coverage 汇总缺陷)。

### 4.2 直答

**(a) 未评估维度显式化:足以防"全维度相容"的直读,尚不足以防"已评估维度"的偏读。**

实测:compatible 结论随附 8 个 `unassessed_dimensions` ✓;scope 声明为空时
`aggregate` 的 `and scope` 挡住 compatible ✓;essential 键 ⊄ scope 时挡住 compatible ✓;
`known_absent ⇒ conflict`、未列出 ⇒ unknown、同键多条适用事实不一致 ⇒ unknown ✓。
**残留缺口**:`assessment_scope` 来自调用方 `declared_scope`,是**声明**而非派生;
判据四第 6 条已写"assessed_scope 派生不继承请求",须把它落到第 2 条旁边:
> `assessment_scope` 必须由当前上下文的可用事实键派生(有适用事实的键),
> 调用方只能收窄、收窄必须留痕(`scope_narrowed_by`),收窄后仍 compatible 的
> 结论须同时给出 `scope_narrowed` 标注。

**(b) optimum / label / basis 不明的三态处理:一半同意,三个缺口。**

- `optimum`:实测偏离 → `not_applicable` + `preference_notes`,**永不 conflict** ✓;
  单点 basis 不明不自动推 optimum ✓(数值 → unknown)。
- `label`(区间键):注册表空 ⇒ unknown ✓(实测 `mesophilic` → `label_without_registered_range`)。
- **缺口 1(误杀,实测)**:`point` 要求 × **区间事实** → `conflict`,
  理由串还是 `range_disjoint_or_outside:pH`(与事实不符):
  事实 `pH∈[6.8,7.2]`、必需点 `pH=7.0` ⇒ 被判 conflict。
  **落文字:**
  > 区间事实 × `point` 要求:区间退化为该点 ⇒ satisfied;点 ∈ 区间 ⇒ **unknown**
  > (实际点值不确定);点 ∉ 区间 ⇒ conflict;理由码分别为
  > `point_in_uncertain_range` / `point_outside_interval`,不得复用区间判据的理由码。
- **缺口 2(文本与实现矛盾,必须二选一)**:判据文本说
  "label ⇒ 首版注册表为空 ⇒ **一律** unknown",但 `label` 只对
  `INTERVAL_CONDITION_KEYS` 查注册表,非区间键直接走字符串比较:
  实测 `electron_donor` 要求 `NADH` × 事实 `benzene` ⇒ **conflict**
  (`value_mismatch`)。而 `_infer_value_basis` 对**一切字符串值**都返回 `label`
  (含 `oxygen_regime`),所以照字面实现 ⇒ oxygen/donor/acceptor 的枚举比对
  全部退化为 unknown(丢掉真实冲突),而**这条回归测不出来**:仓库里没有一条测试
  钉住"枚举值不匹配 ⇒ conflict"(两个字符串冲突夹具,一个走 `known_absent` 分支、
  一个显式传 `value_basis="unspecified"`),照字面改实现不会有任何测试变红;
  照实现则文本"一律 unknown"不成立。
  **落文字(建议):**
  > `label` 仅指**区间键上的定性标签**(须注册表映射,空注册表 ⇒ unknown);
  > 物种/枚举键的字符串值是**实体/枚举比对**,不适用 `basis`,
  > 枚举键取值须过封闭集合(`oxygen_regime` 已有),物种键取值须为可解析实体引用,
  > 不可解析 ⇒ unknown(而不是 conflict)。
- **缺口 3(缺构造期校验)**:`value_basis` 与值形状不校验(可声明 `range`+标量、
  `point`+区间),声明与实际判定语义脱节。**落文字:** 构造期按值形状强制/校验 basis
  (dict ⇒ range;标量 ⇒ point/optimum/unspecified;字符串 ⇒ 枚举或 label),
  不一致即 `ConditionContractError`。

**(c) 合取聚合:同意(判定层);coverage 汇报层有缺陷。**

实测同键两条要求(第一条 conflict、第二条 satisfied)全部进入 `per_requirement`
逐条评估 ✓,合取判定 ✓,F02 反例已回归 ✓。
**缺陷(判定不受影响,汇报自相矛盾):** `per_status` 按键 last-wins,实测
`coverage = {covered_keys:['pH'], conflict_keys:['pH']}` —— 同一键同时"已覆盖"且"冲突"。
**落文字:** coverage 聚合按最坏状态(`conflict > unknown > satisfied`),
`covered_keys` 不得包含任何存在 conflict/unknown 要求的键。

### 4.3 "程序上诚实但化学上误导"风险点

1. **point×区间的假 conflict**:方向是错杀真可能路径,且理由码自称"区间不相交",
   审阅者无法从理由识别真实原因。
2. **label 文本/实现二义**:照字面丢真冲突(厌氧 vs 需氧变 unknown),
   照实现丢"标签不编造区间"的承诺 —— 冻结前必须定案并写进判据。
3. **缺 context ⇒ condition 不评估**(与 3.2(1) 同源):`compatible`/`unknown`
   的三态设计在缺输入时退化成"不适用",条件轴整体被跳过。
4. **coverage 双报**:`covered_keys` 含冲突键,阅读"已覆盖"会漏看同键冲突。
5. **`unspecified`+字符串仍可 conflict**:判据第 5 条把"值语义未声明"列为 unknown
   来源,但实现只对数值生效(字符串走比对,`test_c02` 依赖 conflict)。
   文本须限定:**"值语义未声明 ⇒ unknown"只适用于区间键的数值**,
   否则文本与实现、测试三者互斥。

---

## 5. 判据五:供体一致性诊断

### 5.1 结论:**有条件同意**

方向正确(真实编辑协议、basis 字段、自同构验等价、CN 旁证、执行失败全 unknown),
但 (a) 答"不充分",需补三条;第 8 条前半句无实现。

### 5.2 直答

**(a) 键变化集合是否充分:不充分 —— 三个实测反例。**

| 场景 | 实测结果 | 判定 |
|---|---|---|
| i) 声明改 C-O 单→双,执行**零变化** | `center=True, basis=direct, bond_changes=[], missing=[]` | ✗ 假命中 |
| ii) 声明改中心,实际改中心外 C1–C2 | `center=False` + `extra_changes`(含 element/formal_charge) | ✓ |
| iii) 声明与执行一致 | `strict=True, center=True, basis=direct` | ✓ |
| iv) 声明改 a1–a2,**实际**改 a2–a3(中心内) | `center=False`(声明原子 a1 被计入变化集) | ✗ 假偏离 |
| v) 仅形式电荷变化 / 仅对映体翻转 | `_bond_changes = []` | ✗ 两类变化不可见 |
| vi) 执行失败 | 全轴 `None` + `execution_failed` | ✓ |

根因有三:
1. `changed_atoms |= _edit_atom_ids(edits)` 把**声明的**编辑原子并入"实际变化集",
   于是 (i) 无任何实际变化仍判 center=True,(iv) 未变化的声明原子造成假 False ——
   这正是判据五第 1 条明文排除的"编辑原子是否落入允许集合"逻辑回潮;
2. 键 diff 只看成/断/键级,**形式电荷、立体、隐式氢数**的变化不进 diff
   (实测 charge-only、enantiomer 两个 diff 均为空),而 Codex F11 回修验收
   明列"键变化、原子增删、形式电荷/氢/立体变化";
3. **第 8 条前半句无实现**:没有任何代码把 `edits` 的
   `(atom1, atom2, from_order, to_order)` 与实际 `bond_changes` 双向核对,
   "编辑声明与执行结果不一致时不授予 verified"目前不成立。

**可达性与覆盖说明(诚实边界):** 场景 (i)(iv) 的 `result` 由探针按规则接口构造
(规则必须能处理任意执行输出,判据第 8 条本身就预设"声明与执行不一致"会发生);
当前 `execute_edits` 是否可能产出这类输出,须在冻结前对着执行器契约核一遍并给出结论。
仓库现有 8 处供体诊断夹具(`test_ppv1_s2.py` 内 8 次调用)**全部基于真实发生的键变化**,
没有一个覆盖"零变化 / 声明与执行不一致 / 电荷或立体单独变化",所以这三类缺口不会被测试发现。

**落文字:**
> - 判定基础 = **实际变化集合**(键 diff ∪ 原子增删 ∪ 逐原子形式电荷/氢数/立体 diff);
>   声明的编辑原子**单独列** `declaration_only`,不参与 center 判定:
>   实际变化集为空 ⇒ `center_match=unknown(reason=no_executed_change)`,**永不 True**;
> - 新增**声明–执行一致性核对**:声明的每条 `(atom1,atom2,from,to)` 须在实际
>   `bond_changes` 中出现,实际出现的键级变化须被声明覆盖;不一致 ⇒
>   `declaration_mismatch`,该轴不得 verified(strict/center 至少 unknown);
> - `extra_changes` 的逐原子 Δ 补上 ΔH 与 Δ立体(现只有 element/formal_charge)。

**(b) 等价类图自同构验证的口径:同意方向,需三条收紧。**

实现用 `CanonicalRankAtoms(mol_before, breakTies=False)` 的同秩类作为对称等价类,
类内成员不全同秩 ⇒ **整类拒用**(不部分采信)✓,未知原子 ⇒ 拒用 ✓,
`equivalence_classes` 自报集合不直接采信 ✓,`symmetric_equivalent` 只作 basis、
不升格机制 ✓,`legacy_cn_match` 只是字段、仓库内无任何计数器 ✓。

**落文字:**
> - 口径写明:等价类 = **当前(编辑前)分子图**上 canonical 同秩类,
>   属拓扑对称等价的实现近似,不是完整自同构群枚举;判定与理由码须带
>   `equivalence_basis=canonical_rank_breakTies_false`;
> - 需钉四组夹具:①对称等价命中 `symmetric_equivalent`;②**第一次取代后对称即破**
>   (第二次编辑可判,不许外推);③同位素/形式电荷不同的原子不得判等价;
>   ④部分中心缺映射 ⇒ unknown(已有);
> - `symmetric_equivalent` 在报告中必须带"图等价 ≠ 酶识别等价"注记
>   (现 docstring 有,字段级注记缺)。

**(c) 部分中心缺映射 ⇒ unknown:同意,实测 ✓。**
(`donor_centers_partially_unmapped` ⇒ `center=None`,不部分 True。)
补一句:同一诊断里若 strict=True 而 center=None,汇总层不得取两者之一冒充整体结论 ——
各轴独立呈现。

### 5.3 跨判据项:诊断结果不进 admission

两点接线缺口:
1. `CHECK_TRANSFORMATION_CENTER` 直接采用 `hypothesis.transformation_signature_status`
   (**调用方自报** `verified` 即 verified),与 `check_edit_against_donor` 的输出没有
   一致性要求;
2. `check_edit_against_donor` 当前**只有测试消费**,没有任何生产调用点 ——
   判据五实现并测过,但结果不进任何决策。

**落文字:**
> `transformation_center=verified` 须以供体诊断输出为前提
> (`reaction_center_match=True` 且无 `declaration_mismatch`);
> 诊断缺失或与自报签名不一致 ⇒ `unknown`。自报 `verified` 不得单独授予该检查。
> 判据五输出在 S3 接线前,冻结文本须标注 "diagnostic not wired to admission"。

### 5.4 "程序上诚实但化学上误导"风险点

1. **零变化判 center=True(实测 i)**:最容易被读成"反应中心经验证",实际什么都没发生;
2. **假偏离(实测 iv)**:声明原子混入变化集,真实命中被判 deviation,供体被冤枉;
3. **电荷/立体变化不可见(实测 v)**:去质子化、翻转这类真实编辑在 center 轴上等于没发生;
4. **自报 `transformation_signature_status=verified` 直通 admission**:
   诊断与门禁脱钩,判据五的全部纪律都可以被绕过;
5. `symmetric_equivalent` 裸 True 被读成机制背书(第一轮同族意见,现靠 basis 字段兜,
   仍需字段级注记)。

---

## 6. 冻结前必须处置清单(按"误导/误杀"风险排序)

| # | 项 | 归属 | 一句话 |
|---|---|---|---|
| 1 | `context is None ⇒ not_applicable ⇒ R6 expand` | 判据三 3.2(1)、判据四 | 缺输入记 unknown,R6 定义补"无缺输入跳过" |
| 2 | 供体诊断的声明原子混入变化集 + 电荷/立体 diff 缺失 + 声明–执行一致性未实现 | 判据五 5.2(a)、5.3 | 实际变化集为唯一判定基础;自报签名不得直通 admission |
| 3 | point×区间事实假 conflict | 判据四 4.2(b) | 三种取值 + 独立理由码 |
| 4 | label"一律 unknown"文本 vs 非区间键硬判实现 | 判据四 4.2(b) | 定案:label 仅区间键;物种键走实体/枚举比对 |
| 5 | ABS 与无立体组身份分裂 | 判据一 1.2(a) | 归一或登记 + strict 比对同归一 |
| 6 | R1 吞掉悬空引用;R5d 全集触发 | 判据三 3.2(2)(4) | 理由码不压平,R5d 限定元素/电荷 |
| 7 | 未落地条款(edge_kind、scoring_key、local_delta、转换历史字段) | 判据一/二 | 标 pending,不与已测条款并列 |
| 8 | 同位素/自由基口径、coverage 双报、mode 方向词 | 判据二/四 | 文本级修补,不改判定 |

以上均可在规则文本 + 少量夹具层完成;第 1、2 项需要改代码与测试(与 Codex §4
"七项不只改文字"的裁定一致)。判据在上述处置并经程序证据互证前**不建议冻结**。
