# mimo 化学评审回应:pollutant_pathway_v1 化学判据(S0–S2 回修版 v6)第六轮

- 日期:2026-10-07(R6;回应 `docs/mimo_ppv1_chem_review_request.md` v6,
  替代对 v5 请求的回应口径)
- 触发点:AGENTS.md mimo 三触发点之 1(需评判化学结构时——冻结或发布前)
- 评审对象:S0–S2 第六轮回修后的判据文本 v6 + 实现 HEAD `6d90201`
  (`src/pathway_v43/pollutant/`);判据尚未冻结
- 自包含性:全部结论基于规则级表述 + 合成规则级夹具 + 公开 API 链,
  无任何金标/题面/封存逐题数据;由用户转交,回复原文落盘 `docs/`
- 证据口径:**不采信交付书自报**,逐项以本轮独立复跑与独立探针为准;
  独立结果与交付书 §6 声明数字一致(451 / 44-26 / 1062,见附录 B)
- 独立证据归档:`docs/review_evidence/ppv1_r6_mimo_2026-10-07/`
  (探针脚本 + 输出 + 三份测试日志 + README,满足 r5 回应"探针入库"
  要求中属 mimo 的部分)

---

## 0. 总述:对 Codex R5 §5 两点分歧的正式表态

### 分歧一(判据三"集合覆盖完全同意"):Codex 正确,mimo R5 表态撤回

- **撤回**:r5 回应判据三 1)(b)"产物集合覆盖与部分覆盖语义:同意"
  及 2)-3)"补交叉引用即可"的判断。Codex 的反驳成立:我 r5 的单侧
  共底物例恰好在元素核算轴 violated,证明不了覆盖轴本身安全;
  两组**数值完全配平**的反例在基线仍直达 R6,问题在覆盖轴,
  补文字不能修。
- **独立复现**(基线 worktree `293bc62` vs HEAD,探针 A1/A2):

  | 反例(配平) | 基线 293bc62 | HEAD(v6) |
  |---|---|---|
  | A1 真实 CCO→CC=O 证据用于 CCO→½CC=O+½C1CO1+H2 | coverage=full, admission=**expand** | coverage=partial_unchecked_transformation, admission=**retain_conditional** |
  | A2 真实 CC=O→CCO 证据用于 CC=O+C1CO1+2H2→2CCO | coverage=full, admission=**expand** | coverage=partial, admission=**retain_conditional** |
  | A3/A4 合法 H2 计量补全(氧化/加氢) | full/expand | full/expand(正控制不变) |
  | A8 系数未知 | center=**verified**/coverage=full | center=**unknown**/unknown_coefficients |

- 结论:v6 的"系数绑定 + 注册计量补全规则
  `atom_delta_stoichiometric_completion`"方向正确且行为级翻转属实
  (70 例新回归基线红 44/绿 26,mimo 独立复跑同分布)。

### 分歧二(判据五 E/Z 申报通道):Codex 正确,mimo R5 两处表态撤回

- **撤回一**:r5 判据五 2)-1)"断键致 E/Z 消失恒为签名失配、无声明
  通道,须另设立体申报通道(本版不设)"——作废。同一终态序列化
  足以对齐,无须新通道。
- **撤回二(事实性更正)**:r5 判据五 2)-2)/R5-2"3b 两路同向(皆失)、
  镜像-执行器知觉差登记为边界"——**这是事实错误**。基线独立探针
  (H_3b)直接证据:镜像终态=`STEREOE`(内存残留陈旧立体),
  实际重解析=`STEREONONE`,两者**相异**并触发
  `undeclared_bond_change:['U_C_2','U_C_3']` ⇒ center/strict=None。
  这正是 Codex R5-08 本身(镜像未随执行器做终态序列化),
  不是"两路同向"。
- r5 判据五 1)(d) 对基线行为的**观察**(检出 undeclared_bond_change
  ⇒ retain)在 v5 代码上属实,但把它**判读**为"符合文本的正确保守
  语义、只须登记"是错的:那是序列化不一致造成的伪失配。
- **HEAD 翻转**(独立探针 H_3b):镜像终态=实际终态=`STEREONONE`,
  mismatches=[], center=True, strict=True ⇒ 已声明断键的自然 E/Z
  消失不再入失配;真失配控制保持(D4 伪申报检出、D5 真 E→Z 翻转
  检出 mismatch_count=1)。
- 随之作废:r5 总表中判据五冻结条件①("3b 恒失配语义落字")与
  ②("镜像-执行器归一边界登记");r5 2)-1)/2)-2) 两句建议不落入 v6。
  r5 判据三条件③(覆盖括注交叉引用)已在 v6 落字,但按分歧一它
  **仅为补充**,不替代条件④(见判据三)。

### 本轮独立复跑摘要(详见附录 B)

- ppv1 全量:**451 passed / 0 failed / 0 skipped**
- 基线 `293bc62` + 3 个 r6 测试文件:**44 failed / 26 passed**
  (与交付书 §5.1 红绿分布一致;44 条红名单已完整归档
  `mimo_r6_red_base_full.txt`。交付书"其中 6 红仅因 v6 新披露键、
  其核心语义基线已绿"的归因属交付方声明,须按名单由 Codex 核,
  不在化学结论内)
- G01 全量 `-m "not slow"`:**1062 passed / 16 deselected / 184.20s**
- 独立探针:probe1 = 45 条(HEAD)+ 11 条(基线);probe2 = 10 条

---

## 判据一:分子身份

### 1) 结论:**有条件同意**(条件①②③)

**(a) 输入侧类级登记表的划分(移除/保留/拒绝)与"解析器静默丢弃
⇒ 拒绝"的默认行为:同意。** 独立验证(探针 B 段 + 直接调用守卫):

- **拒绝侧**:`CCO |r|` 在 build_chemical_state 与 strict_identity_of
  两入口均 `unregistered_cx_class`(B1/B1b);`C1CCCCC1 |Ln:1|` 同拒
  (B2,理由码明示登记类清单)。丢弃清单逐项与 RDKit 对照复核:
  `r/c/wU/o:/O/d/n/F` 块在 RDKit 往返输出中确实消失(解析成功后
  静默丢弃),`LN:1` 为语法整体不可解析;即"静默丢弃 ⇒ 拒绝"的
  默认行为防的是真实缺口,不是稻草人。
- **移除类**:`atomProp` 点分值、`$_AV` 标签、坐标、SgD 逗号值
  均放行且与裸输入同 state_id(B3/B4/B5/B6;回归
  `test_r5_02_registered_removal_classes_same_id`、
  `test_r5_02_sgD_comma_value_passes_input_guard`)——移除的是
  不入身份的元数据,同 id 正确。
- **保留类**:`Sg:` SRU 输入放行、身份含 Sg(与裸不同 id)、
  往返重建同 id(B7;回归 `..._sru_retained_input_and_roundtrip`)。
- **注记类**(独立逐类核):`&1:3`(AND)保留、不同 id;
  `o1:1,3`(OR)保留、不同 id;`^1:0`(自由基)入图改身份、
  不同 id;`a:1`(ABS)在身份中归一剥离、与裸同 id——ABS 是
  默认语义的冗余注记(混合并列时原子未入组即按 ABS 解释),
  该归一属请求判据一"1–4 同 v5"中列明的"混合并列 ABS 归一"
  口径,化学上等价,交付测试
  `test_r5_02_enhanced_group_radical_mapping_inputs_pass` 亦以此
  断言;token 级拒绝(`a:1,x:2`/`a:1,2x`)由
  `test_r5_02_annotation_token_level_guard` 钉住,451 绿。
- **fail-closed 默认方向正确**:未登记类一律拒绝而非静默剥离,
  与"丢弃后不得称 as_written"一致;代价是新 CX 类出现即拒
  (登记项,须随 RDKit 行为变化复评)。

**(b) 两个公共入口一致的执行位置:同意;但存在第三个公共结构
消费入口未设防 ⇒ 条件①。**

- 两个入口的执行位置核对属实:`build_chemical_state`
  (chemstate.py:506)与 `strict_identity_of`(:583)均在解析前调
  `_guard_input_cx_classes`(:227)。
- **新发现(条件①)**:`check_edit_against_donor`(audit.py:2417)
  是第三个公共结构消费入口,其对 `current.smiles`(:2479)、
  `result.product_mapped_smiles`(:2482)、`result.product_smiles`
  (:2498)为**原始 `Chem.MolFromSmiles` 直解**,不经输入守卫;
  且 `bound_inputs.substrate_identity = _norm_smiles(mol_before)`
  (:2738)直接采用剥离后的规范串参与覆盖绑定,而
  `proof_record.current.smiles`(:2755)保留原串。独立探针 probe2:
  - **X1**:`current = "CCO |r|"` 被无异常接受;flagged 与 clean 的
    `substrate_identity` **均为 "CCO"**(identities_equal=true),
    proof_record 保留原串含 `|r|`;
  - **X1b**:端到端 `audit_hypothesis` ⇒ center=verified、
    coverage=full、admission=**expand**,全程**无任何剥离警告**
    ——外消旋旗标在证据链中被当作从未存在;
  - **X2**(同函数内不对称):`result.product_smiles` 带 `|r|` 时,
    strict 分支经 `strict_identity_of`(:2558)正确拒绝
    ⇒ strict=None + `target_or_result_unparseable`,**但同一载荷的
    `bound_inputs.product_identity` 走原始解析被吸收为 "CC=O"**。
  - 该通道程序上自洽(audit 内部重算两侧同剥离 ⇒ integrity 通过),
    化学上误导(身份串声称却丢失未登记 CX 事实),正属
    "程序性真、化学误导";两公共入口的 R5-02 修复未覆盖此通道。
- **(c) 逗号不拆整段的边界:同意。** `CO |SgD:0:note:a,b::::|`
  类级放行、与裸同 id(B6),SgD 值含逗号不触发分段;代码侧
  守卫按类头切分、不按逗号拆整段(读码 `_guard_input_cx_classes`)
  与文本一致。

### 2) 可直接落字的文本修改(对应条件①②③)

1. **条件①——守卫范围补第三入口**(判据一 2. 新增要点,置于
   "不把输出侧逗号拆分守卫搬到原输入"要点之前):

   > - **守卫范围同规则覆盖第三公共结构入口**:除
   >   build_chemical_state 与 strict_identity_of 外,
   >   check_edit_against_donor 对 current/result 结构串的原始解析
   >   同受输入守卫约束——未登记块不得在 bound_inputs 的
   >   substrate/product 身份串中被静默剥离后参与覆盖绑定
   >   (剥离后不得称身份;拒绝或转结构化 unknown,机读码同上;
   >   proof_record 仍保留原串供追溯)。

   (若本轮不落码,则必须改为显式登记:该诊断/证明通道为已知
   未设防,其身份串不作 as_written 身份——**落码优先**,X1b 已
   证明该缺口可直达 verified/expand。)

2. **条件②——SgD 剥离前提句**(判据一 2. 移除类要点末尾,
   r5 条件②原文,v6 请求文本至今缺失):

   > SgD 全类剥离以"DAT 仅承载出现/注记元数据"为前提;若适配器把
   > 化学事实写入 DAT,该前提失效,须改写为结构事实后重评剥离口径。

3. **条件③——含空格登记类内容的过拒边界**(判据一 2. 末尾新增):

   > - 登记类**内容含空格**的输入按空格分块后余块落入未知类 ⇒
   >   拒绝(fail-closed)。其中 `$…$` 标签值与 `atomProp` 点分值
   >   含空格为 RDKit 可解析并原样保留的合法写法,本版为**过拒**
   >   (方向安全,不得静默剥离);待词法按闭合 `$`/值域识别后复评。

4. (可选精度句)丢弃清单中 `LN:1` 实为语法整体不可解析
   (归 unparseable_smiles 档),`w:1.0` 为 RDKit 保留但未登记
   (归 unregistered 档)——两者拒绝方向相同,建议措辞分列,
   避免按机读码统计"静默丢弃出现率"时口径混淆。

### 3) 风险点

- **R6-1(程序性真、化学误导——条件①)**:第三入口
  `check_edit_against_donor` 的 current/result 原始解析绕过输入
  守卫,X1/X1b 实证 `|r|` 被剥离进身份链并端到端
  verified/expand 无警告;X2 实证同载荷 strict 分支拒绝、
  product_identity 却吸收的不对称。完整性重算因两侧同剥离而
  自洽通过,任何依赖 integrity 的下游都无法发现。
- **R6-2(过拒边界——条件③)**:`CO |$_foo bar$|`、
  `CO |atomProp:0.note.hello world|` 被守卫拒为
  unregistered_cx_class,而 RDKit 原样解析保留(Y1/Y2;对照 Y3
  无空格放行、Y4–Y6 为 RDKit 自身不可解析、守卫拒绝方向一致)。
  方向安全(拒绝而非剥离),代价是合法登记内容无法提交。
- **R6-3(文档与实现不符)**:交付书 §3 称"SgD 剥离前提已写入
  mimo v6 请求判据一",实际 v6 请求只有"内容不查——SgD 值可含
  逗号"的机制句,无"DAT 仅承载出现/注记元数据"前提句(条件②
  仍缺)。

---

## 判据二:参与物计量与元素/电荷核算

### 1) 结论:**同意;已同意条款无需重评,分工复核通过。**

- v6 无变化,请求只要求确认;独立复核跨判据分工仍成立:
  覆盖 full 而元素轴 violated ⇒ `retain_conditional`(探针 A5:
  coverage=full + elements=violated ⇒ admission=retain_conditional;
  A6c 无共底物、元素 violated ⇒ 同),覆盖轴没有掩盖核算轴;
  恒等(判据一身份)与落点(判据五 center_property_deltas +
  strict 轴)分通道,r5 探针 2a 结论沿用。
- 系数未知 ⇒ 本判据元素/电荷轴 unknown(A8),与判据三
  unknown_coefficients 同源,两轴不互相顶替。

### 2) 可直接落字的修改建议

无需修改。r5 提议的半句交叉引用("恒等与落点差异由判据一身份轴
与判据五 center_property_deltas 承载")可留作可选项,判据三落字
条件④后已不必要。

### 3) 风险点

- **R2-1(沿用 r5,无新增)**:"账平≠落点对、恒等≠转化已核实"
  依赖读者不越权解读;由判据三条件④与既有分通道文本约束,
  未见新缺口。

---

## 判据三:admission 决策表与中心证据契约

### 1) 结论:**有条件同意(条件④,措辞级)**

**(a) 系数绑定与 `atom_delta_stoichiometric_completion` 语义:
同意**(并在此正式确认分歧一的让步)。独立验证:

- **关断反例**:A1/A2 基线 full/expand ⇒ HEAD
  partial/retain(翻转,见总述表);`环丙烷→丙烯`同式量异构
  反例(CCO+C1CC1→CC=O+H2+CC=C,净差可抵消)由回归
  `test_r5_01_two_sided_isomer_no_cancellation` 钉住:两侧各自
  `completion_surplus`(product 与 reactant 两侧**都**列)、
  partial、unknown、admission≠expand——"不许盈余/亏空互相抵消"
  行为属实。
- **正控制保持**:A3/A4(乙醇脱氢、乙醛加氢)、A6a(½O2)、
  A6b([O] 原子氧)、比例缩放(回归
  `test_r5_01_legal_ratio_scaling_full`)均 full/expand;
  `test_r5_01_h2_not_exempt_by_name` 钉住"整类共底物不按名称免审"。
- **系数未知 ⇒ unknown**:A8 由基线 center=verified/full 翻为
  unknown/unknown_coefficients(回归
  `test_r5_01_unknown_coefficient_coverage_unknown`)。
- **旁观水/超额声明**:A7(旁观 H2O)⇒ partial ⇒ unknown,
  不因补全规则放行;注册与披露由
  `test_r5_01_completion_rule_registered_and_disclosed` 钉住(detail
  含 coverage_rule/substrate_scale/atom_delta/两侧未覆盖元素/
  逐条 violations,F1 复核六键齐)。
- "无未覆盖参与物 ⇒ 覆盖 full"与"补全成立 ⇒ 同为 full"并存,
  即 Codex 指出的 **full 有两个互不替代的根据**——语义本身正确,
  但文本未把两根据与各自的证明范围说清 ⇒ 条件④。

**(b) "整类共底物不按名称免审"与"不要求每个计量共产物完整走
AtomTool"的边界:同意。** 前者由元素账规则独立判定(上表);
后者成立且边界清楚:真实断裂产物按碎片分列绑定为参与物
(回归 `test_r5_01_fragment_split_control_full` /
`..._fragment_lumped_control_whole_molecule`),计量必需的共产物
(H2)由补全规则按元素账放行而不要求每产物一份中心证据,
未申报碎片仍 unknown(文本 4)覆盖产物集两级映射)。

**(c) proof_scope / center_match_basis 披露位置:同意**——r5
条件①②已落实:载荷与 detail 同屏披露
`proof_scope=self_contained_recompute`、`center_match_basis=direct`,
理由码 `basis=direct` 非空、无空串尾巴(F1;回归
`test_p2_basis_and_proof_scope_disclosed`、
`test_p2_tampered_basis_integrity_reject`,451 绿);覆盖括注
交叉引用(r5 条件③)已在 v6 文本落字。

**(d) 信任边界声明:同意。** 行为口径与 r5 (a) 一致(自洽构造
复跑即通过、篡改 bound_inputs ⇒ integrity 拒、无 proof_record ⇒
unknown;本轮以 test_p2 系列复核披露侧),且边界已从"只写在规则
文档"变为机读输出可见——r5 R3-1 的缺口关闭。

### 2) 可直接落字的文本修改(对应条件④)

1. **条件④——full 的两个根据与补全的证明范围**(判据三 3. 第 4)
   条,置于"违反 ⇒ 部分覆盖"之后、披露要求之前):

   > **覆盖 full 有两个互不替代的根据**:①无未覆盖参与物;
   > ②注册补全规则 `atom_delta_stoichiometric_completion` 两侧各自
   > 精确相等。二者都只解除覆盖轴。**补全成立只证明"未覆盖部分的
   > 元素账与被核实转化的 Δ 数值闭合",不证转化的身份或机理**——
   > 身份归 strict 轴(判据五)、元素/电荷核算归判据二、转化核实归
   > 证据门,全部轴通过方得推进(与本判据新增披露的覆盖括注互为
   > 表里)。

   落字理由:Codex 分歧一裁定"单句交叉引用不能修"——既有括注只说
   了"full 只解除覆盖轴",未说 full 的两根据,也未说补全规则的
   证明范围止于成分闭合;两句补齐后,"full+verified"不再可能被读成
   "转化身份与机理已核实"。

### 3) 风险点

- **R6-4(条件④,程序性真、文本易误导)**:补全规则数值闭合
  不区分同元素组成的物种形态(如未覆盖产物写 2H• 与 [H][H] 元素账
  同解)——该类区分由 strict 轴/身份轴独立承担,程序分工正确;
  但文本若不说"补全只证成分不证身份/机理",下游会把 coverage=full
  + center=verified 读成全绿。条件④落字前,这是文本层误导点。

---

## 判据四:条件相容聚合

### 1) 结论:**同意;(a)–(d) 四问逐一确认。附程序证据条件⑤。**

**(a) 数值缺席 unknown / 同词缺席 conflict / 异词缺席 unknown 三分:
确认。** 独立探针 C 段逐行与文本对表:

| 案例 | 结果 | 理由码 |
|---|---|---|
| C1 pH 必需区间,数值事实明确否定 | unknown | `numeric_absence_semantics_undefined`(单点缺席不推区间缺席) |
| C2 温度点值,数值事实明确否定 | unknown | 同上 |
| C3 matrix 必需值,异词事实缺席 | unknown | `other_value_known_absent_not_determining` |
| C4 同词(必需值本身)被明确否定 | **conflict** | `required_value_known_absent` |
| C5 同值 present + absent 并存 | unknown | `conflicting_applicable_facts` |
| C6 物种实体缺席 | **conflict** | `required_entity_known_absent` |

  正控制保持(C 段 + 回归 `test_r5_03_positive_controls_kept`);
  "25 不存在不推 20–30 区间不存在"如实落码。

**(b) 快照同源派生的单向矛盾判定(不误拒合法历史):确认。**
独立验证:合法 to_dict→from_dict 往返**同 id 且幂等**(E1
same_id=true, idempotent=true;回归
`test_r5_04_legal_roundtrip_idempotent`);篡改摘要
environment_fit=compatible ⇒ 拒,`check=fit_conflict_mismatch`(E2);
篡改 has_gate_requirements ⇒ 拒(E3,kind=
context_snapshot_inconsistent);签名子集规则(凭空签名)⇒ 拒
`check=signature_not_in_requirements`(X3),**且同 fixture 合法
往返通过**——单向矛盾判定没有误拒合法历史。E1 的
route_assessment=conflict 是该 fixture 的如实评估(p0 阶段在场
aerobic 与累积必需 anaerobic 矛盾,逐条两行全部披露),保守方向。
读码:`_validate_phase_history_snapshot` 只核快照字段与逐条记录的
同源一致,不重跑历史事实评估,与"不拿当前事实重评旧边"一致。

**(c) 内容身份重算位置(from_dict + audit 直接对象入口):确认。**
读码:from_dict 在快照一致性之后以构造期同源 `_recompute_context_hash`
重算全部语义字段(含 phase_history)比对载荷 context_id
(path_context.py:2034);直接对象入口 `validate_context_object`
同源重算(:1492)。实测:篡改事实保留原 id ⇒ 拒
`context_content_identity_mismatch`(E4;回归
`test_r5_04_fact_tamper_kept_context_id_rejected`、
`test_r5_04_inplace_tampered_phase_history_rejected_at_audit`)。
不认证用户事实真实性、不重评旧边,与文本一致。

**(d) 环诊断关系轴的保守门:确认。** 独立探针 G 段:
G1 initial supported + reaction contradicted ⇒ 落
unsupported_relation_cycles、unresolved 为空(不再误报"启动未知");
G2 initial contradicted + regeneration supported ⇒ 仅 unresolved、
关系不被污染;G3 双支持正控制干净;G4 regeneration 被反驳 +
reaction supported ⇒ unsupported(**任一关系轴被反驳 ⇒ 关系不成立**
的保守门确实比字面"至少一条 supported"更保守,只增披露不减)。
回归 `test_p2_*` 五例钉住(451 绿)。

### 2) 可直接落字的修改建议 / 配套

1. **条件⑤(程序证据,非文本)**:`covered_requirement_signatures
   ⊆ 当前累积要求签名集合`是 v6 文本 10(a) 新增规则,实现存在
   (path_context.py:1447 `signature_not_in_requirements`)、行为
   已由 mimo X3 独立验证,**但 tests/ 全目录无任何夹具引用该字段
   (仅模块 docstring 提及)**——红绿回归无法捕获该规则的回退。
   建议补一例:注入凭空签名 ⇒ 拒(signature_not_in_requirements)+
   合法往返 ⇒ 过。冻结前应与 Codex 程序证据一并确认。
2. (可选,登记口径)route 级 environment_fit 聚合历史阶段已记录
   事实:曾在场且与必需值矛盾的事实使拟合为 conflict(保守),
   per_requirement 行全部披露来源;当前阶段满足不洗白历史矛盾。

### 3) 风险点

- **R6-5(证据缺口——条件⑤)**:见上,签名子集规则无行为夹具;
  mimo 探针只能证明"现在是对的",不能替仓库钉住"以后仍是对的"。
- **R6-6(登记项,方向安全)**:数值缺席 unknown 意味着真实
  pH/温度依赖路径可能长期停在 unknown(诚实但保守);这是请求
  §4-9 自己选择的语义,登记为已知代价,建议 S3 前评估数值否定
  语义的正式定义。

---

## 判据五:供体一致性诊断

### 1) 结论:**同意;(a)(b)(c) 三问确认;R5 分歧二让步与 r5
撤回见总述。**

**(a) 镜像终态序列化/重解析与执行器同口径:同意。** 读码:
镜像终态先 MolToSmiles 序列化再 MolFromSmiles 重解析后参与比较
(audit.py:2241),与冻结执行器消费 `product_mapped_smiles` 的路径
同源;H_3b 独立复现翻转——基线镜像 STEREOE(残留)vs 实际
STEREONONE + 伪 `undeclared_bond_change` ⇒ HEAD 两侧同
STEREONONE、零失配。"序列化/重解析失败按原内存图如实失配"的
回退方向保守,同意。

**(b) 已声明断键的自然 E/Z 消失不再入失配:同意。** H_3b:
`C/C=C/C` 断邻位 σ 键 ⇒ `C.C=CC`,自然后果后 center=True、
strict=True、mismatches=[]——正确申报的断裂不再背"未声明"措辞;
"不新增立体操作协议、不删 E/Z 轴、不默认忽略所有 stereo loss、
不改冻结 executor"四项边界:D5 真 E→Z 翻转仍检出
(bond_stereo_change, mismatch_count=1)、D4 伪申报/漏执行双侧
仍检出——未用"忽略一切"换通过。

**(c) 其余立体轴控制保持:同意。** D1(邻位断键)/D2(远端断键
对照)/D3(三取代邻位断键)零假阳性(mismatches=[], center=True);
D4/D5 检出保持;from_order 前置与净效应结算由 r6 回归
(`test_r5_08_adjacent_sigma_break_zero_mismatch` 等)与 r5 存量
共同钉住,451 绿。

### 2) 可直接落字的文本修改建议

无需新增。r5 判据五 2)-1)/2)-2) 两句**作废不落**;v6 判据五 4.
现有文本(mirror 同口径、四项不为、unsupported 走既有理由)即为
可冻结表述。

### 3) 风险点

- **R6-7(登记项)**:镜像与执行器的对齐建立在"执行器产物是
  MolToSmiles 序列化后被消费"这一前提上(v6 文本已显式声明)。
  若 S3 执行器改为直接输出 CXSMILES 或内存图直连,该前提失效,
  须复评本条——前提已登记,方向是复评而非默认通过。

---

## 存储线条款(R5-05/06/07)范围声明

按 Codex R5 §5 采纳边界,出现清单覆盖先存来源、既存假设首用不验、
旧兄弟来源循环证明三项属存储/旧来源程序问题,不属 mimo 化学抽查
范围:**mimo 不对其表态,亦不向判据一–五的结论外推**;其验收以
Codex 程序证据为准。相应地,70 例新回归跨 chem/conditions/storage
三个测试文件,其中 storage 项红绿仅计入程序核对(基线红 44 含
storage 项,完整红名单已归档供核)。

---

## 附录 A:独立证据清单(已归档)

归档路径:`docs/review_evidence/ppv1_r6_mimo_2026-10-07/`(含 README
复跑说明;全部为规则级合成夹具、公开 API 链,无金标/封存数据)。

| 文件 | 内容 |
|---|---|
| `mimo_r6_probe.py` | 主探针:A 覆盖/补全(10)、B CX 登记表(13)、C known_absent(6)、D 镜像与立体(5)、E 快照(5)、F 披露(1)、G 环轴(4)、H_3b(1) |
| `mimo_r6_probe_out_head.json` | HEAD 输出,45 条 |
| `mimo_r6_probe_out_base.json` | 基线 293bc62 输出,11 条(A1/A2/A3、A5–A8、H_3b;v6 专属段跳过) |
| `mimo_r6_probe2.py` / `..._out.json` | 补充探针 10 条:X1/X1b/X2 第三入口 CX 缺口、X3 签名子集规则、Y1–Y6 空格过拒边界(RDKit 侧对照) |
| `mimo_r6_ppv1_head.txt` | `451 passed in 3.65s` |
| `mimo_r6_red_base.txt` | 基线红绿末尾摘要 `44 failed, 26 passed in 1.18s` |
| `mimo_r6_red_base_full.txt` | 同一基线红绿完整输出:44 条 FAILED 全名单 + 汇总行(绿 = 70−44) |
| `mimo_r6_g01.txt` | `1062 passed, 16 deselected in 184.20s` |

关键单点证据索引:H_3b(分歧二让步)、A1/A2+基线(分歧一让步)、
X1/X1b/X2(条件①)、Y1/Y2 vs Y3–Y6(条件③)、X3(条件⑤)、
C1–C6(判据四 a)、E1–E5(判据四 b/c)、G1–G4(判据四 d)、
D1–D5(判据五 c)、F1(判据三 c)。

## 附录 B:独立复跑记录

- `pytest tests/test_ppv1_*.py -q`(HEAD 6d90201):**451 passed**
  (0 failed / 0 skipped,与请求 §6 一致);
- 基线 worktree `293bc62` 拷入 3 个 r6 测试文件后
  `pytest tests/test_ppv1_r6_*.py -q`:**44 failed, 26 passed**
  (与请求 §6/交付书 §5.1 红 44/绿 26 一致;完整红名单
  `mimo_r6_red_base_full.txt`);
- `pytest tests/ -m "not slow" -q`(HEAD):**1062 passed,
  16 deselected, 184.20s**(1062 = r5 存量 992 + 新增 70,数目
  自洽);
- 探针:probe1 HEAD 45 条 / 基线 11 条、probe2 10 条,全部结论
  以更正后的运行为准(本轮无夹具更正事项)。

## 总表:结论与冻结前条件

| 判据 | 结论 | 冻结前条件 |
|---|---|---|
| 一 分子身份 | **有条件同意** | ①第三公共结构入口(`check_edit_against_donor`)落输入守卫,或显式登记其为未设防通道且身份串不作 as_written;②SgD 剥离前提句落字(v6 文本至今缺失);③含空格登记类过拒边界落字(或词法修复) |
| 二 计量核算 | **同意** | 无 |
| 三 admission/证据门 | **有条件同意(措辞)** | ④"full 两根据 + 补全只证成分不证身份/机理"句落字 |
| 四 条件聚合 | **同意** | ⑤(程序证据,与 Codex 并核)签名子集规则补一例行为红绿夹具 |
| 五 供体诊断 | **同意** | 无(r5 条件①②作废) |
| 存储线 R5-05/06/07 | 不在化学范围 | 按 Codex §5,由程序证据验收 |

横向:探针与日志已按仓内规范归档
`docs/review_evidence/ppv1_r6_mimo_2026-10-07/`;分歧一/二的让步与
r5 撤回以上文总述为准,r5 回应中与之冲突的段落
(判据三 1)(b)、判据五 2)-1)/2)-2)、R5-1/R5-2、总表条件)
以本文件为最新口径。
