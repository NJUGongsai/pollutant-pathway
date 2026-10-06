# mimo 化学评审回应:pollutant_pathway_v1 化学判据 v4(第四轮)

- 日期:2026-10-06(第四轮;回应 `docs/mimo_ppv1_chem_review_request.md` v4 文本)
- 评审对象:S0–S2 第四轮回修后的五条判据 v4 文本 + 实现(`src/pathway_v43/pollutant/`,`ppv1-*-4` 族);**尚未冻结**
- 范围与证据边界:只评规则级表述;源码只读核对;全部探针用合成分子/合成夹具,
  无金标/题面/封存逐题数据;未运行真实模型、未跑真实题目
- 独立复跑(本轮两条全量命令):
  - `pytest tests/ -k ppv1 -q` → **312 passed, 627 deselected, 0 skipped**(与请求 §6 一致)
  - `pytest tests/ -q -m "not slow"` → **923 passed, 16 deselected, 0 failed**(197.76s,与 §6 G01 一致)
  - §6 的"基线 af14fb2 行为级红 8/8"本轮**未独立复验**(需改 HEAD,不动工作区);不作为结论依据
- 本轮新探针(合成夹具,临时证据;按 Codex §5 纪律,下列反例冻结前须仓库化):
  - `ppv1_r4_probe.py` → `ppv1_r4_probe_out.json`(A 身份往返 / B 混合 ABS 语义 / C CX 拒绝表 /
    D 奇偶法边界 / E 键级立体)
  - `ppv1_r4_probe2.py` → `ppv1_r4_probe_out2.json`(§1.3 映射号边界修正 + §1.2 精确实例)
  - `ppv1_r4_probe3.py` → `ppv1_r4_probe_out3.json`(联合映射支持范围:部分指定/全未指定底物)
  - 复跑:
    ~~~bash
    cd /Volumes/CC/Enzyme_Agent/dependingv43
    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src \
      /Users/cc/miniconda3/envs/depending43/bin/python \
      /private/var/folders/mg/7frznpjj7y16hqgk_g6h_28c0000gn/T/opencode/ppv1_r4_probe.py
    # 同目录 ppv1_r4_probe2.py / ppv1_r4_probe3.py
    ~~~
  - 探针自更正(诚实披露):probe1 E2 字段 `substrate_stereo_retained_in_product`
    的斜杠计数写错(2 个斜杠判 4),该字段作废,以 `keys_equal: true` 为准;
    probe1 D4 的 `reachable_via_extra_changes: true` 是**强行传参**的产物,
    真实流程该原子进不了变化集(见 5.2(a) 条件 2)
- 外部常识引用:RDKit Book(增强立体 AND/OR/ABS 语义、CXSMILES、立体章节)、
  rdCIPLabeler API —— 非本仓资产
- 格式:按请求 §7,逐条给 **结论 / 可直接落进规则文字的修改 / 风险点**,不作总体评价

---

## 1. 判据一:分子身份

### 1.1 结论:**有条件同意**(3 条件)

1. CX 事实子集是**拒绝表**(denylist):未列入"移除"清单的 CX 类一律进身份键,
   而 SGroups / `r` / 氢键 / `w:` / link node / 原子值等既不在移除表也不在保留表 —— 须给出**逐类处置 + 默认规则 + 注册测试**;
2. §1.3"无组且无自由基 ⇒ 与普通 canonical isomeric SMILES 逐字相同"缺**原子映射号**例外
   (实测证伪,见 1.2(a));
3. 混合并列 ABS 归一除 `plain≡|a:…|` 外还有**第二处与 RDKit 立体组集合的分歧**
   (同族,须一并登记),且 ABS 与组**同原子重叠**的矛盾输入当前是静默解析 —— 须登记解析规则。

### 1.2 直答

**(a) CX 事实子集的划分(保留/移除清单)——保留/移除两表行为正确,但口径是拒绝表,未登记类默认进身份。**

- 行为复核(C1):绘图元数据移除对照通过 —— 带 conformer + `molFileAlias` + `atomLabel` + 分子级
  note 的 CO 与裸 CO **同键**(`drawing_metadata_same_key: true`);增强立体/自由基/同位素/电荷保留在基串
  与 `|…|` 段 ✓;顺反立体写在**基串**(`/C=C/` vs `/C=C\`),两个几何异构体身份键**分立**
  (`ez_distinct_keys: true`)—— 即键级立体目前由身份轴兜底,不靠 CX 段。
- 问题在**未列出的类**:`_identity_key`(`chemstate.py:125-152`)的移除项 = conformer + atom 级
  prop + 分子级 prop + 映射号,保留项靠"其余原样写出"。RDKit(及外来工具串)还能产出
  `Sg:` SGroup(可携带 SRU/混合组分等**化学事实**)、`r` 外消旋标志、`H:` 氢键、`w:` 波纹键、
  `LN:` 链接节点、`$_AV:` 原子值、非 RDKit 工具的 `c:`/`t:` 键立体 —— 这些既未登记为化学事实,
  也未登记为可移除,于是**默认进身份**:同分子带/不带此类注解会产生两个 state_id,
  与 R3-04 修掉的"绘图注解改身份"是同一族错误,只是换了一批注解类。
  (SGroup 构造探针本轮未成功:molblock 解析失败,`sgroup.parse_ok: false` —— 故此项是
  **文本级登记要求**,不是已证反例。)
- 另注:`_identity_key` 清 atom prop / 分子 prop / conformer,**未清 bond prop**;
  当前 `MolToCXSmiles` 是否写出 bond 级 prop 未经验证,须一条注册测试,不默认无害。

**(b) 令牌级 ABS 归一的语法口径——请求的三个精确实例全部成立;两处边界须入文。**

- 行为复核(probe2,四组等式全 `true`):
  `base+|a:1,&1:3|` ≡ `base+|&1:3|`、`|a:1,o1:3|` ≡ `|o1:3|`、`|^1:0,a:1|` ≡ `|^1:0|`,
  且 `|a:1,3|`(多原子 ABS 延续)与 plain 同键 —— "注解头 + 裸数字延续"的解析口径正确,
  逗号未被盲拆 ✓(R3 的 A2b 混合并列分裂已关闭)。
- **化学正确性依据**:不在任何增强立体组里的原子按 RDKit Book 隐含 ABS,故"ABS 原子不是组成员"时
  剥离 ABS 等于把显式 ABS 改回隐式 ABS,语义等价 —— 该方向**同意**。
- 边界 1(须登记):RDKit 真实解析**保留**被剥掉的 ABS 组对象 —— probe B1
  `rdkit_groups_equal_mixed_vs_and: false`(输入 `|a:1,&1:3|` 读出 ABS{1}+AND{3},
  剥离后读出 AND{3};RDKit 自己改写会把 `|a:1,&1:3|` 写回去)。即"混合 ABS ≡ 组形态"是
  **本仓第二处与 RDKit 表示层的已登记分歧**,与已登记的 `plain≡|a:…|` 同族,应并入 §1.2
  那句"已登记分歧"的范围(RegistrationHash 的 CANONICAL_SMILES 层同样保留该 ABS 文本)。
- 边界 2(须登记解析规则):**ABS 原子同时是组成员**的重叠输入(探针用 `|a:3,&1:1,3|`)是
  自相矛盾声明;RDKit 两个组都留,本仓按"组优先"解析成 `|&1:1,3|`(`key_equal` 为真但语义集合不同)。
  规则本身可辩护,但请求文本的"≡"没有区分"ABS 原子在组内/组外"两种情形 —— 须显式写明
  "组成员资格覆盖 ABS 声明"或改为对矛盾输入判 unknown,二选一。

**(c) AND/OR 语义句与整组翻转不变性——同意。**

- v4 文本现为"AND = 两组分(该手性分子及其镜像)都在的混合物;OR = 二者未知何者的单一未定物质;
  ABS = 单一确定构型",与 RDKit Book 一致(R3 的倒置已改正)✓;整组翻转不变(镜像化混合物/
  未知集同义)、部分翻转为不同键、组类型不合并 —— 与 R3 行为复核及仓库测试
  (`test_r2_02_and_group_whole_inversion_same_identity` 等 6 项)一致,本轮不撤销。
- 保留一条提醒:"多组组合不得一律简化成全分子只有两个构型"(Codex §4)—— 文本未出现该简化,通过。

### 1.3 可直接落进规则文字的修改

1. §1.2 第 2 条"移除非化学 CX 元数据"改为**双表 + 默认规则**:
   > "身份键的 CX 子集按**逐类登记表**处理:①移除类 = 坐标(conformer)、atomLabel、
   > 任意 atomProp、分子级绘图/注记 prop、原子映射号;②保留类 = 增强立体组、自由基层、
   > 基串内同位素/电荷/立体、顺反键立体(`c:`/`t:` 与基串 `/`,`\\` 同义归一);
   > ③**未登记类**(SGroups、`r`、`H:`、`w:`、`LN:`、`$_AV:` 等)在注册前一律按
   > **{移除 | 保留}之一**钉死并补注册测试 —— 不允许'默认原样进身份'这种无声明状态。"
   (保留/移除二选一由实现方定,但文本与代码必须同向,且反向各自有夹具。)
2. §1.3 往返句补映射号例外:
   > "无组**、无自由基层、无原子映射号**的分子输出与普通 canonical isomeric SMILES
   > 逐字相同;**映射号被剥离**(实测 `C[CH2:1]O` → `CCO`),映射信息只存在于
   > `structure_smiles_raw` 与对齐/编辑 ID 通道,公开表示不携带映射号;
   > 自由基分子带 `|^n:…|` 后缀(已登记缺口)。"
3. §1.2 RegistrationHash 那句的"已登记分歧"扩到混合形态,并补重叠解析规则:
   > "plain 与 `|a:…|` 同键、**混合并列 ABS 剥离**(`|a:1,&1:3|` ≡ `|&1:3|`)均为本仓归一
   > 决定,与 RegistrationHash 的 CANONICAL_SMILES 层、以及 RDKit 立体组集合(RDKit 保留显式
   > ABS 组)存在已登记分歧;
   > **ABS 原子同属某组**时组成员资格覆盖 ABS 声明(矛盾输入的解析规则,登记在案)。"

### 1.4 "程序上诚实但化学上误导"风险点

- **拒绝表默认保留**:一个带 SGroup(如聚合物 SRU、混合组分)的分子,与去掉注解的同骨架分子
  得到两个 state_id —— 账面各自合法,化学上是把同一物质当两个参与物;与 R3-04 修掉的
  "五个 CO 五个 id"同构,只是换了一批 CX 类,复审方一换工具串就能复现。
- **§1.3 逐字相同句**:评审方拿一个带映射号的常见输入(反应物几乎都带)一跑就证伪该句,
  连带质疑相邻的 RegistrationHash 限定句 —— 文本级可修,代价极低,不修则是可预期的
  "程序没错、声明被推翻"。
- **矛盾 ABS 静默解析**:两个不同串被合并成一个 id,而 `structure_smiles_raw` 仍留原串 ——
  下游按 id 计量没问题,但拿 raw 复核的人会看到与 id 不同的立体组,查不出为何被归一。

---

## 2. 判据二:参与物计量与元素/电荷核算

### 2.1 结论:**同意**(0 条硬条件;1 条可选强化句)

### 2.2 直答

- **(a) 恒等≠落点的口径句 —— 同意,且这是本轮最该保留的一句。** §2 第 7 条把电荷账钉为
  全账数值闭合、不核落点,与 mimo R3 2.3(1) 一致;`accounting_notes` 的
  `verified_only_element_and_formal_charge_closure` 与该句互证(仓库 `test_mimo_element_accounting_notes_disclosed`)。
- **(b) pending 条款的排除声明 —— 同意。** `local_delta = contract clause, implementation pending`
  明确不入册,且仓库 `test_pending_clauses_declared_not_implemented` 钉住"声明未实现"不被当成已实现 ✓。
- 1–6 同 v3 无改动:R5d 触发集限定 {元素, 电荷} 双向钉住
  (`test_r2_01_r5d_limited_to_element_and_charge` / `test_r2_01_center_mismatch_is_violated_r5v_not_r5d`)、
  H+_count1 命名、结构化 `omission_pattern_matches` —— r3 已无条件同意,本轮不撤销。

### 2.3 可直接落进规则文字的修改(可选)

1. §2 第 7 条后补一句指路,避免 `formal_charge_accounting: verified` 被读成"按声明落位":
   > "落点/归属一致性由**判据五的 `center_property_deltas`(中心原子电荷 before/after)**
   > 与**判据一的身份轴**(产物 state_id 是否等于声明产物)承担;本账对该问题**不作任何贡献**。"

### 2.4 "程序上诚实但化学上误导"风险点

- 无新增。唯一残留是 r3 已写明的:`formal_charge_accounting: verified` 与"电荷落在正确原子上"
  之间没有推论关系 —— §2 第 7 条 + 2.3(1) 的指路句并列出现即可控制;若两处只出一处,
  展示层仍可能把数值闭合当落位核实。

---

## 3. 判据三:admission 决策表

### 3.1 结论:**有条件同意**(1 条件 + 1 条展示要求)

1. **证据绑定契约的核验范围被文本高估**:代码只交叉核验 `bound_inputs` 的**底物身份**与
   **产物身份**两项;`edits 签名 / 执行指纹 / 供体中心 / 对齐引用` 是证据自报、
   且**缺失不触发 `binding_missing`**,而 §3 文本写成"映射编辑/无依据 True ⇒ unknown" —— 须收窄文本或补必填校验;
2. 展示层必须把 `checker_scope` 与"transformation_center: verified"**并列输出**(理由码已带
   `scope=…`,不得在展示时被截断/剥离)。

### 3.2 直答

**(a) 证据绑定契约的字段与核验范围——机制成立,范围须如实收窄。**

- 已验证成立的部分(代码 + 测试 + r4 交付互证):`checker_version` 注册制、
  `checker_scope ∈ {region_net_change}`(`full_template_visionary` 被拒,`test_r4_chem:557`)、
  底物身份 vs `substrate_state_ref` 公开表示、产物身份 vs 某产物参与物 —— 跨反应复用/注册名-only
  证据均落 unknown(`test_r4_01_cross_reaction_evidence_reuse_rejected` /
  `test_r4_01_name_only_evidence_not_verified`);strict 轴消费:False ⇒ VIOLATED(进 R5v)、
  None ⇒ UNKNOWN 阻断 all_verified、区域 True 与 strict False 在 `detail` 分列
  (`audit.py:660-685`);理由码自带 `scope=region_net_change;basis=…`(`audit.py:692-695`)。
- **缺口**:`audit_hypothesis` 不接收 edits/alignment,`Hypothesis` 也不携带供体中心/编辑
  (`hypothesis.py` 全文无 center_atom/edits 字段)—— 所以 `bound_inputs` 六项里只有两项有独立
  对照物。实测代码路径:`binding_reason` 只在 `not bound` / 底物缺失或不符 / 产物缺失或不符时置位
  (`audit.py:603-626`);一份只带底物+产物两项、`edits_signature`/`execution_fingerprint`/
  `donor_centers`/`alignment_ref` 全缺或全假的证据,照样通过绑定核验走向 verified。
  即 §3 文本"映射编辑/无依据 True ⇒ unknown"在**编辑/对齐维度上没有实现**
  (编辑维度目前只保证"改了就换 `input_hash`",不保证"改了就 unknown")。

**(b) R2p off 披露 —— 同意。** `audit.py:1205` 的 `R2p_disclosure:per_product_gate_rejected:not_consumed`
在 `per_product_gate_consumption=off` + 部分被拒时进 reasons,`test_s4_per_product_off_discloses_not_consumed`
钉住 r3 的零披露反例已关闭;off 只关消费不关披露的表述与实现同向 ✓。

**(c) input_hash 覆盖域与禁互换推理句 —— 同意。** `audit.py:834-858`:hypothesis 载荷 +
state 完整 `to_dict()`(fidelity/appearance)+ context `content_hash`(嵌套改即变)+ audit_scope +
checker 版本 + `center_evidence` 规范化摘要(含 `bound_inputs_hash`)+ `unresolved_dependency_ids`;
`test_r3_08_input_hash_covers_real_inputs` / `test_r3_08_context_nested_mutation_changes_input_hash`
覆盖;**"不能用 input_hash 相同推断两次审计可互换或缓存结论"这句必须原样保留**(它挡的是
缓存推理,不是哈希碰撞)。

### 3.3 可直接落进规则文字的修改

1. §3 关键定义的 `bound_inputs` 括注改为二选一(推荐前者,成本在测试不在代码):
   > **(A) 补必填)** "`bound_inputs` 六项**全部必填且非空**,缺任一项 ⇒
   > `center_evidence_binding_missing:*` ⇒ unknown;底物/产物两项与被审假设的
   > 公开表示**交叉核验**,edits 签名/执行指纹/供体中心/对齐引用为**同源随附**
   > (诊断产物原样携带,改任一项即换 `input_hash` 且可复查)。"
   > ——或——
   > **(B) 收窄文本)** "绑定核验的**交叉核验范围 = 底物身份 + 产物身份**;
   > edits 签名/执行指纹/供体中心/对齐引用由诊断**同源随附**并计入 `input_hash`,
   > 缺失即 binding_missing,**但无独立对照物**(hypothesis 不携带编辑与中心)——
   > '映射编辑 ⇒ unknown'仅在**与被审假设对照得到不同值**时成立。"
2. 展示层条款(可并入 §3 末尾):
   > "`transformation_center: verified` 必须与 `checker_scope` 同屏显示
   > (如 `verified(scope=region_net_change)`);scope 不得在展示/导出时丢失,
   > 否则限定区域证据在读者眼里就是完整变换核实。"

### 3.4 "程序上诚实但化学上误导"风险点

- **半绑定证据**:一份底物/产物对、编辑签名与执行指纹全空的证据,理由码写着
  `center_evidence_verified:ppv1-donor-diagnostic-3(scope=region_net_change;basis=direct)`,
  读起来像"编辑与执行都被核对过";实际核对的只有两个身份串。文本现在也这么写 ——
  文本与代码一起把"六项字段"呈现成"六项核验"。
- **scope 被截断**:理由码字符串是长文本,任何"截断到 reason_code 首段"的展示/聚合
  (决策表上游就有 `[:160]`/`[:200]` 截断习惯)会先砍掉 `scope=…`,于是区域证据
  以"verified"裸名进入汇总。

---

## 4. 判据四:条件相容聚合

### 4.1 结论:**有条件同意**(1 条件)

1. **单位契约必须二选一钉死**:当前"无单位事实按键规范单位比较 + `assumed_canonical` 注记"
   允许**来源单位未知**的带量纲事实落到 `satisfied`(= verified 状态),与 Codex §4
   "注记不能把未知来源变成 verified"直接冲突 —— 要么入口契约校验,要么无单位即 unknown。

### 4.2 直答

**(a) 候选级评估的两层语义 —— 同意。** 旧边取 `phase_history` 记录值合取不重评、本候选新增要求
在当前 scenario+phase 作用域评估、父冲突在子路线保持(不冤杀合法分阶段路线)、跨阶段空 phase
事实服务多边、外来 binding 构造期 `HypothesisContractError(kind=foreign_requirement_binding)`
(`test_r3_06_foreign_requirement_binding_structured_reject` 等 3 例),展示两层并列 ——
audit→admission 全链两行表测试在册(`test_r3_06_audit_row1/row2`)✓。

**(b) 单位 / matrix 契约 —— matrix 同意,单位有条件。**

- matrix:`无语义关系字符串不等 ⇒ unknown(matrix_value_unresolved)`、同词 satisfied、
  氧枚举与物种实体硬判保留 —— 与 Codex R3-12 验收一致,`test_r4_conditions:660` 钉住 ✓。
- 单位:显式规范单位 ⇒ `canonical`、显式错单位 ⇒ `unit_mismatch ⇒ unknown`、
  要求侧无 unit 字段(`build_requirement` 构造器不接受)—— 这三条通过。
  **但** `_assess_requirement`(`path_context.py:704-706`)对带量纲键 `unit==""` 的事实
  注 `unit_basis: "assumed_canonical"` 后**照常参与比较并可返回 `satisfied`**;
  `build_condition_fact` 也不拒无单位的量纲事实(不拒构造)。于是"已归一输入"与
  "原来源单位未知"两种情形**只有注记不同、状态相同**:`assumed_canonical` 行可以独立构成
  门禁的 verified 依据。Codex §4 允许的是"规范输入单位契约 + **适配器校验**",
  并明确"注记不能把未知来源变成 verified"—— 现状不满足后半句。
  (仓库只测注记本身:`test_unit_basis_assumed_canonical_disclosed` 断言
  `row["unit_basis"] == "assumed_canonical"`,未断言状态语义。)

**(c) 轴集合累积 —— 同意。** initial_supply 之后 regeneration 不覆盖前轴、启动未知不回退、
仅再生支持 ⇒ `unresolved_initial_supply` 保留;`test_r4_conditions`/`test_ppv1_r2_conditions`
双向钉住 ✓。`hypothesis_id` 入 requirements/assumptions/dependency_refs、排序归一、
嵌套载荷构造期深拷贝不可变(就地改 TypeError)—— `test_frozen_source_refs` 系列在册 ✓。

### 4.3 可直接落进规则文字的修改

1. §4 第 6 条改为二选一,并把归属方写进句子(推荐 A,与 Codex 原文对齐):
   > **(A 入口契约)** "带量纲键的事实**必须携带键规范单位**(适配器/入口校验);
   > `unit==""` 的量纲事实 = **来源单位未知 ⇒ 评估 unknown**(`unit_basis: source_unit_unknown`),
   > 不参与 satisfied/conflict;无量纲键(按注册清单:matrix、oxygen_regime、物种键等)
   > 恒不带单位,按值直接比较。"
   > ——或——
   > **(B 评估期假定)** "无单位量纲事实按规范单位比较,但其结论标注
   > `unit_basis: assumed_canonical` 且**该行不得单独构成 essential 要求的 satisfied**
   > (需另一条 `canonical` 事实或适配器确认方可升 satisfied)。"
   两案择一;现状(注记照常判 satisfied)与 Codex §4 不同向,须改文本或改代码。

### 4.4 "程序上诚实但化学上误导"风险点

- **注记代替校验**:`assumed_canonical` + `satisfied` 并排时,读者会把注记理解成
  "已确认是规范单位",实际含义是"假设是"。方向性错误两头都会发生:
  300(实为 K,26.85 °C)落进 20–30 °C 区间 ⇒ 假 conflict;
  30(实为 °C 但来源是 K 的 30 K?)⇒ 假 satisfied —— 理由码里看不出单位曾经缺失。
- **双层结论坍缩**已在文本钉住两层并列,风险转入实现:若展示层只出当前步或只出路线,
  两个方向仍各误导一次(这条 r3 已列,不撤销)。

---

## 5. 判据五:供体一致性诊断

### 5.1 结论:**有条件同意**(4 条条件;条件 1、2 未处置前**不建议冻结**)

1. **非四面体分支顺序与文本相反**(行为级):两侧同为非四面体手性标签时返回 `""`
   (= 构型保持的肯定判定)而非 `None`(unsupported),`stereo_comparison_unsupported` 根本不置位
   —— 直接违反 §5.2 第 2 条;
2. **`stereo_comparison_unsupported` 无公开披露通道**(行为级):该标志进不了
   `center_property_deltas`(过滤条件是 `property_delta`/`presence`),也进不了
   `extra_changes`(unsupported-only 原子不入变化集,自然不进 `outside`);
3. **联合映射支持范围声明欠声明**:代码只对**增强立体组**关 unsupported 门,
   "部分指定 / 全未指定"四面体底物**照常评估**,而 §5.3 只声明了"绝对四面体指定/无手性骨架"两类;
4. **净变化集合缺键级立体(cis/trans)轴,且理由码会断言"实际净变化为空"而身份轴说不空**
   (行为级,见 5.2(c))。

### 5.2 直答

**(a) 奇偶构型比较的化学正确性(含配体集合改变的边界)——方法正确,同意;一处分支顺序必须修。**

- **方法本身**:对前后配体集合相同(按构造 idx 的**原子同一性映射**)的原子,构型由
  (手性标签, 邻居序置换奇偶)共同决定 —— 这是标准做法,且这里的对应关系是"原子身份"而非
  CIP 或图自同构,因此置换良定义、无歧义。三组控制(probe D1 + 仓库 3 例):
  - **邻居序重排、几何不变**:同一分子的另一种写法(`N[C@@H](C)C(=O)O` ↔ `C[C@H](N)C(=O)O`),
    标签 CW vs CCW **不同**,朴素 tag 比较会报"变化",奇偶法返回 `""` ✓ —— 正是 R3-03 要防的失效模式;
  - **真实反转**(标签翻、邻居序不变)⇒ `"stereo"` ✓;
  - **配体集合改变**(断键)⇒ `None`,由键 diff/增删承载,不在立体轴伪造判定 ✓ —— 该边界的行为与文本一致。
- **隐式氢为何不需要特判**(建议写进规则文字,防后人"补一个 H 项"改坏):RDKit 手性标签的
  邻居序约定对隐式 H 的位置是**固定的**(或随某一指定邻居移动),而"固定位置插入/随元素移动"
  两种约定下,全 4 配体置换的奇偶都等于**显式邻居置换的奇偶** —— 故 H 数不变时直接用
  显式邻居序是正确的;H 数变化本来就会进 `h_count` Δ 与键/增删轴。
- **条件 1(行为级,必须修)**:`_stereo_config_delta`(`audit.py:1519-1529`)的判断顺序是
  `if not b_chiral and not a_chiral: return ""` **先于**两条非四面体 `return None`。
  于是两侧同为非四面体标签(平面手性/四方/八面/三角双锥等,molfile 金属配合物常见)
  —— 甚至一侧非四面体、另一侧 UNSPECIFIED —— 都命中第一条,返回 `""`
  (**肯定的"构型保持"**),两条 `return None` 只在"一侧非四面体、另一侧四面体指定"这个
  别扭组合下才可达。探针 D1:`CHI_TRIGONALBIPYRAMIDAL` 两侧 ⇒ `delta: ''`,
  `record_flag: null` —— §5.2"非四面体手性 ⇒ unsupported 不入变化集"**未实现**。
  修法(一行顺序调整,推荐):
  > 把两条"非四面体标签且非 UNSPECIFIED ⇒ `None`"提到 `not b_chiral and not a_chiral`
  > 之前;随后"两侧均 UNSPECIFIED ⇒ `''`"保持不变。
  文本侧同步写明:unsupported 的判据是**标签类型**,不是"是否四面体指定成功"。
- **条件 2(披露,必须补)**:即便修好条件 1,`_atom_property_diffs` 只在 `deltas` 非空时把原子
  放进 `changed`(`audit.py:1598-1604`),unsupported 单独出现时原子**不入变化集**;
  `center_property_deltas` 的过滤(`audit.py:2106`)要求 `property_delta` 或 `presence`,
  `_atom_change_summary` 只覆盖 `outside`(变化集内)原子,且其条目不携带
  `stereo_comparison_unsupported` 字段 —— 真实流程里该标志**任何公开字段都看不到**
  (probe D4 的 `reachable_via_extra_changes: true` 是强行传参的产物,不代表真实流向)。
  Codex §4"中心属性披露…暴露实际属性及 scope"要求的正是这条通道。
- 附:CIP 降级为披露(`cip_labels`,rdCIPLabeler)且不作变化判据 —— 与 Codex §5 修正裁定一致,
  本轮**接受**该修正(准确标签也会因配体优先级重排翻转,R3-03 第二组反例)。

**(b) 保手性联合映射的支持范围声明——行为正确,但声明欠一类。**

- 已验证:meso 换位 ⇒ False(两端严格身份不同)、真 C2 `(2S,4S)` 互换 ⇒
  `symmetric_equivalent` 保持、增强立体组 ⇒ `unsupported_stereo ⇒ unknown`
  (`audit.py:1828-1829` + `test_r3_02_*` 3 例)、搜索截断 ⇒ unknown ✓。
- **probe3 新增三类底物**(声明范围之外但代码照常评估):
  - **部分指定**(`C[C@H](Cl)[CH](Cl)C`,C1 指定 / C3 未指定):blind 自同构 2、
    **aware 仅 1**(指定↔未指定互换被 RDKit `useChirality` 拒绝)⇒
    声明中心在左、实断右端 ⇒ `center_match: False` + `extra_changes` 披露两侧原子 ——
    **化学上正确**:两端在"所写表示"下是可区分种(一端已定义、一端未定义),不等价 ⇒ False 合理;
  - **全指定对称**(控制):aware 2 ⇒ `symmetric_equivalent` ✓;
  - **全未指定**(`C[CH](Cl)[CH](Cl)C`):aware 2 ⇒ True,且两端产物**同一身份**
    (两边都只剩未定义中心)⇒ 在"不超出所写信息"的意义上可判 ✓。
- 结论:行为三例都对,但 §5.3 的两类声明("绝对四面体指定 / 无手性骨架")**覆盖不到**
  "部分指定 / 全未指定"这两种被评估的状态 —— 这不是冒称全范围,而是**欠声明**:
  复审方按文本无法预测这两类的行为。须把支持范围扩成三类并写明各自语义。

**(c) 净效应对账的执行器镜像口径——镜像正确,同意;但净变化集合缺键级立体轴,理由码会自相矛盾。**

- 镜像口径核对通过:编辑前 `Kekulize(clearAromaticFlags=True)` 与执行器
  `atom_tool.py:417` 同步 ✓;有序操作按净效应结算(s→d→s→d 终态 = double,
  `test_r3_05_ordered_ops_net_effect_accounted` ✓);`add_atom` 隐含 anchor 单键
  (`atom_tool.py:482`)在模拟中自然形成,不再误报 `undeclared_bond_change`
  (`test_r3_05_add_atom_implicit_anchor_bond_accounted` ✓);声明不可模拟 ⇒
  `declared_edits_not_simulable`;原子属性不在 ops 对账(声明语言无对应操作)—— 范围声明诚实 ✓。
- **条件 4(行为级 + 文本级)**:净变化集合 = 键 diff ∪ 原子增删 ∪ 逐原子(电荷/ΔH/构型)diff,
  **没有键级立体(cis/trans)轴**(全源码 `GetStereo`/`STEREOE` 仅出现在立体组判断,
  键变化只比键级 `audit.py:1417-1468`)。探针 E1(接口合成:调用方提供 E/Z 不同的产物、
  零编辑,不声称冻结执行器会自动生成该差异):
  - 身份键分立(`C/C=C/C` ≠ `C/C=C\C`,判据一自己判为不同种);
  - `bond_changes: []`、`atom_changed: []`、`declaration_mismatches: []`、
    `extra_changes: []`、`center_property_deltas: []` —— **零披露**;
  - `strict_target_match: true`(期望产物就是该异构体)、`center_match: null`;
  - 理由码 **`no_executed_change(实际净变化为空…)`**,而同一诊断的
    **`net_change_empty: false`** —— 两个字段对"净变化是否为空"给出相反答案,
    且理由码断言的是一件身份轴已证伪的事。
  - 真实执行器对照(控制,已跑):trans-2-butene 上 `double→single→double` 净效应序列
    `ok=True`、产物**保留** `/C=C/`、身份键不变(`keys_equal: true`)——
    即冻结执行器当前不产生该分歧;缺口是**潜伏的**,但公开接口接受调用方提供的产物图,
    且 ops 声明语言本身**无法表达** E/Z 变化(与"原子属性不在对账"同类)。
  - 修法(二选一,推荐前者):①把键立体纳入 diff(至少比较 `bond.GetStereo()` 与 stereo atoms
    经映射后的几何),或 ②声明键级立体为 unsupported 并**公开披露**;
    同时把理由码拆开:身份键不等而图轴全空时改发
    `net_change_only_in_stereo_representation` 之类,**禁止**再报 `no_executed_change`。
- §5.4 第 4 条同步补:"原子属性与**键级立体**都不在 ops 对账(声明语言两者皆无)。",
  并把检出责任指到具体通道(身份轴 / strict / 新增的键立体披露)。

**(d) `center_property_deltas` 披露范围——同意,附两条收紧。**

- E-iii 三例(中心电荷、中心构型翻转、以及 strict 消费)在 `test_r3_05_center_property_deltas_disclosed` /
  `test_r3_05_center_stereo_inversion_disclosed_with_strict` 钉住 ✓;中心外原子走
  `extra_changes` 的 before/after 成对披露 ✓(probe D1 强行传参条目可见字段齐全)。
- 收紧 1:与条件 2 合并 —— unsupported 标志须同通道公开。
- 收紧 2(**文本/载荷级**):`cip_labels` 与 `property_delta` 并排输出时会出现
  "标签 R→S、delta 为空"(配体优先级重排的真实形态,R3-03 第二组反例正是它)。
  须在载荷或理由码里就地标注 `cip_label_change_is_not_config_change`,
  否则披露字段自己会诱导误读:**看到 before/after CIP 不同却查不到变化,读者第一反应是漏报**。
- 附:strict 与 ChemicalState 同源规范化、执行失败全轴 unknown、`legacy_cn_match` 仅旁证 ——
  三条通过,`test_r2_03_*` 与 r3 结论一致,不撤销。

### 5.3 可直接落进规则文字的修改

1. §5.1 第 1 条逐原子 diff 括注补键级立体:
   > "判定基础 = 实际净变化集合(键 diff ∪ 原子增删 ∪ 逐原子(形式电荷/ΔH/构型)diff
   > ∪ **键级立体 diff(cis/trans)**);键级立体在并入前为 unsupported 的情形,
   > 须**公开列项**并使该轴 unknown,不得静默缺席。"
   ——或(若暂不实现):"键级立体(cis/trans)**不在**判定基础内,其变化仅由身份轴与
   strict 轴察觉;本诊断对其**不作任何陈述**,理由码不得在其缺席时报
   `no_executed_change`。"
2. §5.2 第 2 条的 unsupported 判据改写:
   > "非四面体手性标签(平面手性、四方、八面、三角双锥等)⇒ 该原子立体轴
   > **unsupported(`None`)**,不入变化集且**在公开载荷列项**
   > (`stereo_comparison_unsupported` 原子清单);判定依据是**标签类型**,
   > 不是'是否四面体指定'——两侧同为非四面体标签时同样 unsupported,
   > 不得返回'构型保持'。"
3. §5.3 第 3 条支持范围扩三类:
   > "支持范围 = ①绝对四面体**全部指定**;②**无手性骨架**(无任何四面体中心);
   > ③**部分指定/全未指定**四面体中心 —— 按所写表示参与保手性匹配:
   > 指定↔未指定互换不被接受(⇒ 实测 center=False,两端为不同种),
   > 全未指定两端产物同一身份时可判 True;增强立体组 ⇒ unsupported ⇒ unknown;
   > 搜索截断 ⇒ unknown。"
4. §5.4 第 4 条改为:
   > "对账是 **ops 级**;中心原子上的形式电荷/ΔH/立体属性**与键级立体**
   > 都不在对账范围内(ops 声明语言无对应操作),其检出分别走
   > `center_property_deltas`、键立体披露列项、身份轴与 strict 轴;
   > **同一诊断内身份键不等而图轴全空时,理由码须如实写'仅立体表示差异',
   > 不得写'实际净变化为空'。**"
5. §5.2 第 5 条后补 CIP 披露的就地警示:
   > "`cip_labels` 的 before/after 不等**不构成**构型变化证据
   > (配体优先级重排即产生标签翻转);载荷在标签不等而 `property_delta`
   > 无 `stereo` 项时须附 `cip_label_change_is_not_config_change` 标注。"

### 5.4 "程序上诚实但化学上误导"风险点

- **"净变化为空" vs "身份已变"**:同一诊断里 `net_change_empty: false` 与
  `no_executed_change(实际净变化为空…)` 并存 —— 下游按理由码读会认为"什么都没发生",
  按身份轴读会拿到一个新 state_id;两边都"程序正确",化学陈述互相打脸。
- **unsupported 静默**:非四面体中心先被报成"构型保持"(肯定结论),即便修好也**零披露** ——
  读者无从知道这一轴没被检查过;这正是判据五"不冒充完整变换一致"承诺的反面:
  限定范围只写在 docstring,不进输出。
- **区域 verified 的裸名**:`center_evidence_verified:…(scope=region_net_change;…)` 一旦被
  截断或转述成 `transformation_center: verified`,区域诊断就在读者眼里升级成完整变换核实 ——
  R3-01 修的是证据绑定,展示层这一刀还没人守。
- **CIP 披露的反向误导**:`cip_labels` 明明显示 R→S 而 delta 为空(真实、正确),
  展示层若并排放置,读者会认为系统漏报了立体变化,进而对整份诊断失去信任。

---

## 6. 冻结前处置清单(按"误导/误杀"风险排序)

| # | 项 | 归属 | 一句话 | 类型 |
|---|---|---|---|---|
| 1 | 净变化集合缺键级立体轴,理由码在身份已变时报"实际净变化为空"(字段自相矛盾) | 判据五 5.2(c) | 加键立体 diff 或列项披露 + 拆 `no_executed_change` 理由码 | 代码+文本 |
| 2 | 非四面体标签两侧同置 ⇒ 返回"构型保持"而非 unsupported;标志无公开通道 | 判据五 5.2(a) | 调整 `_stereo_config_delta` 分支顺序 + 公开 `stereo_comparison_unsupported` 清单 | 代码 |
| 3 | §1.3"逐字相同"缺原子映射号例外(`C[CH2:1]O` → `CCO`) | 判据一 1.3 | 补"无原子映射号"前提 + 说明映射号所在通道 | 文本 |
| 4 | CX 子集是拒绝表,SGroup/`r`/`H:`/`w:`/`LN:`/`$_AV:` 未登记默认进身份 | 判据一 1.2 | 逐类登记表 + 默认规则 + 注册测试(含 bond prop 是否外写) | 文本+测试 |
| 5 | `bound_inputs` 六项只有两项被交叉核验,文本写成"映射编辑/无依据 True ⇒ unknown" | 判据三 3.2(a) | 补必填校验(案 A)或收窄文本(案 B)+ scope 与 verified 同屏 | 文本(+校验) |
| 6 | 无单位量纲事实可 `assumed_canonical` 直接 satisfied,与 Codex"注记不把未知来源变 verified"冲突 | 判据四 4.2(b) | 单位契约二选一(入口校验 / 不可单独升 satisfied) | 文本或代码 |
| 7 | 联合映射支持范围未声明"部分指定/全未指定"四面体(代码已评估该两类) | 判据五 5.2(b) | 支持范围扩三类并写明实测语义 | 文本 |
| 8 | 混合并列 ABS 归一是与 RDKit 立体组集合的第二处分歧;ABS 同原子重叠为矛盾输入静默解析 | 判据一 1.2 | 并入已登记分歧范围 + 登记"组覆盖 ABS"解析规则 | 文本 |
| 9 | `cip_labels` 与空 delta 并排会诱导"漏报"误读 | 判据五 5.2(d) | 载荷就地标注 `cip_label_change_is_not_config_change` | 文本/载荷 |

判据二为本轮唯一**无条件同意**项。第 1、2 项需改代码与红绿回归(行为级),
其余可在规则文本 + 注册测试层完成;所有本轮探针(含 `ppv1_r4_probe*.py`)须在冻结前
仓库化为回归。**判据五在第 1、2 项处置并经程序证据互证前不建议冻结**;
判据一/三/四的条件为文本级与契约级,处置后可与判据五一并复审。

## 7. 程序证据与独立复跑

- `pytest tests/ -k ppv1 -q` → 312 passed / 627 deselected / 0 skipped(与请求 §6 一致);
- `pytest tests/ -q -m "not slow"` → 923 passed / 16 deselected / 0 failed(与 §6 G01 一致);
- 本轮探针:`ppv1_r4_probe.py`、`ppv1_r4_probe2.py`、`ppv1_r4_probe3.py`
  (输出 `*_out*..json`,临时目录,冻结前转仓库回归);
- 源码只读核对位置:`chemstate.py:125-201`(身份键/ABS 剥离)、`audit.py:1477-1615`
  (CIP/奇偶法/原子 diff)、`audit.py:1701-1767`(净效应对账)、`audit.py:1807-1844`
  (联合映射)、`audit.py:536-705`(证据门)、`audit.py:834-858`(input_hash)、
  `audit.py:1205`(R2p 披露)、`path_context.py:658-772`(单位/matrix)、
  `atom_tool.py:402-526`(执行器镜像对照);
- 未做:未改 HEAD、未动工作区、未运行真实模型、未读金标/封存逐题数据;
  §6"基线 8/8 红"未独立复验(见页首)。
