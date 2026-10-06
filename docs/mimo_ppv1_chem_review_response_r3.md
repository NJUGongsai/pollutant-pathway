# mimo 化学评审回应:pollutant_pathway_v1 化学判据 v3(第三轮)

- 日期:2026-10-06(第三轮;回应 `docs/mimo_ppv1_chem_review_request.md` v3 文本)
- 评审对象:S0–S2 第三轮回修后的五条判据 v3 文本 + 实现(`src/pathway_v43/pollutant/`,ppv1-*-3);**尚未冻结**
- 范围与证据边界:只评规则级表述;源码只读核对;全部探针用合成分子/合成账本,
  无金标/题面/封存逐题数据;未运行真实模型、未跑真实题目
- 独立复跑:`pytest tests/ -k ppv1 -q` → **226 passed, 627 deselected, 0 skipped**
  (与请求 §6 一致;837 长跑本轮未复跑,与 r2 惯例相同——不以数量作结论,
  每条意见锚定可复跑探针或源码位置)
- 可复跑探针(合成夹具,临时证据;按 Codex §5 纪律,下列反例须在冻结前
  转成仓库回归测试,不依赖临时路径长期存在):
  - `ppv1_r3_probe.py` → `ppv1_r3_probe_out.json`(18 记录:身份/计量/admission/条件/供体)
  - `ppv1_r3_e2e5.py`(判据五错位中心 E2E)、`ppv1_r3_e2e7.py`(控制例 CIP 伪影)
  - `ppv1_r3_e2e8.py`(中心原子未声明立体反转全绿 + 假设构造契约 + useChirality 可行性)
  - `ppv1_r3_c1.py`(RegistrationHash 分歧)、`ppv1_r3_e2e.py`~`e2e4/6.py`(辅助)
  - 复跑:
    ~~~bash
    cd /Volumes/CC/Enzyme_Agent/dependingv43
    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src \
      /Users/cc/miniconda3/envs/depending43/bin/python \
      /private/var/folders/mg/7frznpjj7y16hqgk_g6h_28c0000gn/T/opencode/ppv1_r3_probe.py
    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src \
      /Users/cc/miniconda3/envs/depending43/bin/python \
      /private/var/folders/mg/7frznpjj7y16hqgk_g6h_28c0000gn/T/opencode/ppv1_r3_e2e5.py
    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src \
      /Users/cc/miniconda3/envs/depending43/bin/python \
      /private/var/folders/mg/7frznpjj7y16hqgk_g6h_28c0000gn/T/opencode/ppv1_r3_e2e7.py
    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src \
      /Users/cc/miniconda3/envs/depending43/bin/python \
      /private/var/folders/mg/7frznpjj7y16hqgk_g6h_28c0000gn/T/opencode/ppv1_r3_e2e8.py
    ~~~
- 外部常识引用:RDKit Book(Enhanced Stereochemistry 章,AND/OR/ABS 语义与
  增强立体子结构匹配规则)——非本仓资产,仅作化学语义基准
- 格式:逐条给 结论 / 直答 / 可直接落进规则文字的修改 / 风险点;不作总体评价

---

## 1. 判据一:分子身份

### 1.1 结论:**有条件同意**(4 条条件)

1. **混合注解 ABS 剥离修复**(行为级):`|a:1,&1:3|` 这类逗号并列混合
   注解中的 ABS 段未被剥离,同一立体事实分裂成两个 state_id
   (实测 4 个用例、3 组 id 分裂,见 1.2(a));
2. §1.2 **AND/OR 语义句与 RDKit Book 对调**,须改正(文本级,化学正确性);
3. **"与 RegistrationHash 一致"限定范围**并显式登记 plain≡ABS 分歧(文本级);
4. "无组分子输出与普通 canonical 逐字相同"补**自由基例外**(文本级)。

### 1.2 直答

**(a) 整组翻转归一 / 部分反转区分——行为正确;但论证句的化学语义写反了,RegistrationHash 一致性声明过宽。**

- 行为复核(探针 A1/A6/A7,全绿):27/27 期望通过——plain≡|a:…|、
  AND/OR 整组翻转同键(单/双组)、部分翻转保持不同键、排列归一、
  kekulé 归一、映射号剥离;过度合并反例 5/5 全部分立(对映体、ABS vs AND、
  ABS vs OR、D vs H、手性 vs 内消旋);内消旋底物部分反转 2/2 保持分立。
  整组翻转在**两种语义读法下都成立**(对"两者都在的混合物"整体取镜像=同一
  混合物;对"未知何者的单一物"整体取镜像=同一未知集),所以判定行为不受
  下述文本错误影响。
- **§1.2 语义句错误**:请求写"AND 组=未知何者对映体的单一非对映体声明;
  OR 组=两组分混合物声明"。RDKit Book 的定义正相反:**AND = 两者都在的
  混合物(mixture of both),OR = 未知何者(单一、未定),ABS = 单一确定
  构型**;Book 还明确举例 AND 包含"该手性分子与另一个"两者。按现在的写法,
  规则文本把 OR 解释成"两组分混合"、AND 解释成"单一未知",外部读者会用
  反了的语义去解读产物构成——程序自洽但化学陈述倒置,必须改。
- **RegistrationHash 一致性**:分层实测(探针 B6/`ppv1_r3_c1.py`)——
  AND/OR 整组翻转、部分反转区分、排列归一、kekulé、映射号五类与
  RegistrationHash **一致**;但 5 个"应同键"用例**分歧**(ours=同、reg=异),
  全部是 plain vs `|a:…|` 系列:RegistrationHash 的
  `HashLayer.CANONICAL_SMILES` 保留 `|a:1|`(plain=`F[C@H](Cl)Br`、
  abs=`F[C@H](Cl)Br |a:1|`),本仓按 mimo 1.3(1) 归一剥离。这是**设计决定
  的已知分歧**,不是缺陷,但请求把"与 RegistrationHash 的增强立体等价语义
  一致"写成了无条件声明,须限定到整组翻转/部分反转子集。
- 附带行为缺陷 **A2b**(与 (a) 同族,归一化不完备):`_ABS_SEGMENT_RE`
  (`chemstate.py:141`,`(?:^|\s)a:[\d,]+(?=\s|$)`)要求 ABS 段以空白起、
  空白/串尾止,而逗号并列的 `a:1,&1:3` 前后是 `|` 与 `,`,永远匹配不上:
  - `…Cl |a:1,&1:3|` → `cs_850fc18b411105e79889` ≠ `…Cl |&1:3|` → `cs_b20b9c7f84aab04fa5ac`
  - `…O |a:2,5,&1:2,5|` → `cs_55397a6bfc6dbddd8a42` ≠ `…O |&1:2,5|` → `cs_d93fdca46d28ec5e0065`
  - `[CH2][C@H](C)O |^1:0,a:1|` → `cs_02db12295564f646d197` ≠ `…|^1:0|` → `cs_e8f5e564b5856b12d0a0`
  单独的 `|a:1|` 能正确剥离(A3 往返里 `F[C@H](Cl)Br |a:1|` 归一到无注解
  串、同 id),只有**混合并列**失手——这直接违反 1.2 第 2 条
  "plain 与 |a:…| 同键"在混合形态下的同一承诺。

**(b) 公开表示 = 身份键同一串——取舍同意,补一处例外。**

往返闭合实测(A3,11 例):`|&…|`、`|o…|`、混合注解、同位素、电荷、
自由基输入全部 same_id + 幂等 ✓;原始串留 `structure_smiles_raw` 的
出现记录分层合理。例外:`[CH3]` 的公开表示是 `[CH3] |^1:0|`,与
`MolToSmiles` 的 `[CH3]` **不逐字相同**(A4:5 个非自由基例逐字相同,
自由基例因 CX 自由基层后缀不同)——1.2 第 4 条须加例外说明,否则该句
与 1.4 的 radical 缺口登记互相矛盾。

**(c) radical 轴缺口登记——足够。**

身份层区分自由基实测 ✓(`distinct:radical` 通过;`C`(甲烷)与 `[CH3]`
自由基分立),
保真轴未实现已按 1.4 明确登记为 known gap,符合 r2 条件。唯一要求:
缺口登记不得与 (b) 的"逐字相同"句混读(见上)。

### 1.3 可直接落进规则文字的修改

1. §1.2 第 2 条语义括注替换为:
   > "AND 组=两组分(该手性分子及其镜像)都在的**混合物**声明;
   > OR 组=二者**未知何者**的单一未定物质声明;ABS=单一确定构型声明;
   > 两类组对组内全中心整体反转不变(镜像化后的混合物/未知集与原声明同义)。"
2. §1.2 第 2 条后补:
   > "ABS 段剥离适用于**任意注解形态**,含与自由基/AND/OR 逗号并列的
   > 混合段(如 `|a:1,&1:3|` ≡ `|&1:3|`、`|^1:0,a:1|` ≡ `|^1:0|`);
   > 混合形态与单一形态同键。"
3. RegistrationHash 表述改为:
   > "与 RDKit RegistrationHash 在**整组翻转/部分反转/排列/kekulé/映射号**
   > 子集上一致;plain 与 `|a:…|` 同键是本仓 1.3(1) 归一决定,与
   > RegistrationHash 的 CANONICAL_SMILES 层(保留 `|a:…|`)存在**已登记分歧**。"
4. §1.2 第 4 条改为:
   > "无组**且无自由基层注解**的分子输出与普通 canonical isomeric SMILES
   > 逐字相同;自由基分子带 `|^1:…|` 后缀(见 1.4 已知缺口)。"

### 1.4 "程序上诚实但化学上误导"风险点

- **混合注解分裂**:同一立体事实两个 state_id,下游会把一个化合物当两个
  参与物各自计量/对账——账面全对,化学上是重复计数。程序没有任何报错,
  因为两边各自都"合法"。
- **倒置语义句**:实现按正确化学判定,文本按倒置语义论证;未来维护者按
  文本改代码(比如把 OR 真做成"两组分")就会把错误带进实现——文本是
  代码的下一轮夹具来源。
- **RegistrationHash 声明**:对外声称一致而实测 5 处系统性分歧,复审方
  一跑分层哈希即可证伪整段声明的可信度。

---

## 2. 判据二:参与物计量与元素/电荷核算

### 2.1 结论:**同意**(0 条硬条件;1 条可选强化句)

### 2.2 直答

**(a) 结构化模式字段与 H+_count1 命名——通过。**
实测(B2/B5):`omission_pattern_matches` 为结构化数组
`{pattern:"H2O", excess_on:"reactant_side", missing_from:"product_side",
element_delta:{H:2,O:1}}` ✓;`H+_count1` 输出为独立模式名(B5:CCO→CC=O+[H],
`element_delta:{H:1}`),且 `omission_pattern_semantics` 逐字落实"仅数值相符、
不证明缺项原因、不含电子/质子计量" ✓;反例(B4):`H:1,O:1/2` 这种半氧
缺口**不**误配任何既有模式(`pattern_matches: []`)——模式匹配没有被做宽。
`declared_account_violated:element_imbalance:H:2;O:1` 理由码逐元素 Δ 向量 ✓。

**(b) R5d 触发集合限定——通过。**
仓库测试双向钉住且随本轮 226 通过:`test_ppv1_r2_chem.py:402-417`
(一般 violated 检查 ⇒ R5v,断言**不**出现 `R5d:` 前缀)与 `:421-432`
(元素账 violated ⇒ `R5d:declared_account_violated`)。13 行政策表全量
复现(R1/R1b/R2/R2p/R2b/R3/R4/R5d/R5v/R5c/R5/R6/R7 及理由码)。

**(c) 同位素/自由基口径注记——充分。**
`accounting_notes` 实测恒带三段:`isotopes_D_T_counted_as_H;
radical_electrons_not_counted; verified_only_element_and_formal_charge_closure`。
数值核对 ✓:`[2H]OC(C)C` → H8(D/T 并入 H)、`[CH3]` → C1H3(未配对电子
不入账)、显式氢 `[H][H]`→H2 无双计、`[NH4+]`→N1H4、`CC(=O)[O-]` 电荷
恒等(B3:`charge_delta:"0"`,`full_balance_original_formal_charge`)。
"verified 仅数值闭合"的限定句(2.2)本身诚实,应保留。

### 2.3 可直接落进规则文字的修改

1. 2.4 条后补一句,把电荷账的口径钉死:
   > "电荷账是**全账恒等**(产物总电荷−反应物总电荷=0)的数值闭合,
   > **不核对电荷落点与声明是否一致**;落点/归属的一致性归判据五的
   > 声明–执行对账与身份轴。"

### 2.4 "程序上诚实但化学上误导"风险点

- **恒等 ≠ 落点**:一个把电荷挪到错误原子上的执行(判据五 E4 中心原子
  未声明 +1)若总电荷仍守恒,本账 verified。注记已声明"仅数值闭合",
  风险可控——但正因如此,**必须**让读者看到 2.3(1) 这句,否则
  `formal_charge_accounting: verified` 会被读成"电荷按声明落位"。
- 模式语义句已充分自我限定(不推断原因),无新增风险。

---

## 3. 判据三:admission 决策表

### 3.1 结论:**有条件同意**(4 条条件)

1. **R2p off 开关披露**(行为或文本,二选一):逐产物门禁部分被拒 +
   `per_product_gate_consumption=off` 时,决策为 `expand/R6:all_verified…`
   且理由中**零披露**被拒产物(实测见 3.2(a));
2. **input_hash 覆盖补项**(行为或改口径):指纹不含
   `unresolved_dependency_ids`,也不含 `center_evidence` 载荷/结论,与
   "覆盖实际科学输入"的头句不符(实测见 3.2(c));
3. **中心证据契约补 strict 轴**(文本+接线):`strict_target_match`
   全源码**无任何消费方**,`center_evidence_from_donor_diagnostic`
   (`audit.py:1840-1853`)也不透传它——判据五的 strict 轴进不了 admission;
4. **R2b 构造期契约**(行为级):`build_hypothesis(requirements=[Requirement(…)])`
   抛**裸 `TypeError: 'Requirement' object is not iterable`**
   (`hypothesis.py:433` 的 `dict(r)`),不是带 detail 的
   `HypothesisContractError`,调用方无法按 R2b 行映射成
   `contract_violated_representation`;且 requirement dict 无 schema 校验
   (缺 level/value、`level:"bogus"` 均照常生成 id,见 3.2(a) 附)。

### 3.2 直答

**(a) R1b/R2p/R5v/R5c 四行边界——三行通过,R2p 有披露缺口。**

- R1b:悬空 state 引用 ⇒ `reject/R1b:participant_state_missing` ✓,
  理由码不压平 ✓;
- R5v:中心证据 violated ⇒ `retain/R5v:declared_violated_other` ✓,
  与 R5d 不混用 ✓;
- R5c:窄 `audit_scope` ⇒ `retain/R5c:required_check_coverage_missing`
  并列出缺失检查清单 ✓,不因"事实齐备"进 R6 ✓;
- R2p:全部被拒 ⇒ `reject/R2p:…all_products_gate_rejected` ✓;部分被拒 ⇒
  `retain_conditional/R2p:…some_products_gate_rejected` 并带
  `position:0:element_gate_rejected` 逐位拒因 ✓;
  **但 `per_product_gate_consumption="off"` + 同样的部分被拒 ⇒
  `expand/R6:all_verified_no_conflict`,reasons 里没有任何被拒产物痕迹**。
  开关的设计意图(不消费=不阻断展开)可以理解,可"不阻断"不应等于
  "不留痕"——审计与展示层现在无法知道曾有产物被拒。
- 附(同属构造期契约,支撑条件 4):`requirements=[{"key":"temperature"}]`
  (缺 level/value)→ 正常生成 `hyp_a43abc28ec1c536f5ad5`;
  `level:"bogus"` → `hyp_ca4dcb74c344dbcf591b`——requirements 直接入
  身份哈希,无任何模式校验。

**(b) 中心证据注册制——机制通过,证据形状不足。**

注册制本身 ✓:`CENTER_CHECKER_REGISTRY` 现仅 `ppv1-donor-diagnostic-3`;
未注册 checker ⇒ `unknown(center_evidence_missing)`(探针
`unregistered_checker`);自报签名不授信(`transformation_signature_status
=verified` 单独出现 ⇒ 仍 unknown,仓库 `test_r2_01` 钉住);缺证据 ⇒
unknown ✓。**但**证据形状只含 `center_match` + `declaration_mismatch`:
判据五实测的错位中心(见 5.2(b) E-i)会以 `center_match=True` 直接构成
verified 证据,而判据五自己算出的 `strict_target_match=False`(产物不是
声明位点应得的种)既不进证据、也无任何代码消费——"verified 须注册
checker 输出"的门是实的,门后的内容缺一根横梁(条件 3)。

**(c) R6 覆盖核算——通过。**
窄 scope ⇒ R5c 不进 R6 ✓;无 context ⇒ `R5:unknown_checks_present`
(reason 带 `condition_check`,不记 NA)✓;无中心证据 ⇒ R5 带
`transformation_center` ✓;NA 白名单仅"关闭的有限规则诊断/汇总边"
(`finite_rule_diagnostic`、`step_scope`)✓;R6 仅在全 verified 且
无 unknown/violated/缺输入时 `expand` ✓(探针 `r6_with_evidence`)。

### 3.3 可直接落进规则文字的修改

1. R2p 行条件句补:
   > "`per_product_gate_consumption=off` 只关闭**消费/阻断**,
   > 不关闭披露:部分被拒时仍以披露性理由码列出被拒产物与拒因
   > (如 `R2p_disclosure:…`),决策可为 expand,但披露不可省。"
2. "input_hash 覆盖实际科学输入"改为(二选一,推荐前者):
   - **(改代码)** 指纹加入 `unresolved_dependency_ids` 与
     `center_evidence` 的规范化摘要(含 `center_match`/`declaration_mismatch`);
   - **(改文本)** "input_hash 覆盖**判定前输入**:hypothesis 语义载荷、
     参与物 state 身份、context 身份、audit_scope、checker 版本;
     **不含**依赖解析状态与证据结论——后者由决策层理由码单独记录,
     不得用 input_hash 相同推断两次审计可互换。"
3. 中心证据定义(本判据关键定义第 3 点)补:
   > "checker 输出若含期望产物比对轴(strict),该轴为**证据的一部分**:
   > `strict_target_match=False` 的证据不得注册为 verified 证据
   > (至少降 unknown);`center_evidence_from_donor_diagnostic`
   > 必须透传 strict。"
4. R2b 行括注补:"构造期一切契约违反(含 requirements 传入非 dict、
   缺必填字段、level 枚举外)须以 `HypothesisContractError(detail)` 抛出;
   不允许裸 TypeError 逃逸。"

### 3.4 "程序上诚实但化学上误导"风险点

- **off 开关抹掉痕迹**:`expand` + 干净理由码读起来像"所有产物都过了",
  实际有产物被拒只是没被消费——展示层与复审方无从发现。
- **同哈希异结论**:`ain_0729f6b44c69a5ad7b43` 在"依赖已解析 vs 未解析"
  (provenance_dependency: verified vs unknown)与"中心证据 verified vs
  violated"四种情形下**完全相同**(窄 scope `ain_3b5e4d1b9fcb9b081d25`、
  异 context `ain_a96618190b3da1243716` 反而不同)。若有人用 input_hash
  做"同输入即同结论/可缓存"推理,就会把两种相反证据的审计当成同一次。
- **裸 TypeError**:R2b 行承诺"detail 须由调用方映射传入"——异常类型都
  不对,映射无从谈起,最后落成 500 而非 `reject/contract_violated_representation`。

---

## 4. 判据四:条件相容聚合

### 4.1 结论:**有条件同意**(3 条条件)

1. **requirement 侧单位契约**(行为或文本):
   `build_requirement(..., unit="K")` →
   `TypeError: build_requirement() got an unexpected keyword argument 'unit'`,
   要求侧隐含键规范单位而事实侧携带单位——两侧不对称,须补 kwarg 或在
   文本钉死"要求值恒为键规范单位";
2. **`matrix` 键值语义定案**(文本/注册):`matrix` ∈ 7 个条件键
   (`path_context.py:68`),但不在 INTERVAL/SPECIES/ENUM 任一集合,
   落入通用字符串分支(`path_context.py:645-653`)——任意不等即
   conflict、无封闭值集、无标签注册表、无实体作用域(实测见 4.2(c));
3. **双层显示措辞**(文本):阶段绑定实测"父步 conflict、子步当前
   compatible、子步路线 conflict"三值并存,展示/规则文本须写明**两层
   都要显示**,不得只显示当前层冒充路线结论。

### 4.2 直答

**(a) 阶段绑定 + 历史快照合取——通过。**
D6 实测:父步 `environment_fit=conflict` 在子步路线聚合中**保持**
(`child_route_fit=conflict`)、子步当前场景独立判 `compatible`
(`introduced_phase_id:"p1"` 注记随 per-requirement 输出)——即"旧边冲突
在路线结果中保持、新阶段事实不重评旧要求" ✓;requirement 构造期即带
`introduced_phase_id/scenario_ref/edge` 字段 ✓;hypothesis_id 纳入
requirements/assumptions/dependency_refs、同反应不同前提不同 id、
重放幂等 ✓(身份语义与 3.2 附的未校验问题不冲突——那是构造期缺口)。

**(b) 区间×点三态与单位边界——通过,两处待钉。**
三态与独立理由码 ✓:点∈区间 ⇒ `unknown(point_in_uncertain_range)`、
点∉区间 ⇒ `conflict(point_outside_interval)`、退化区间 `[a,a]`×点=a ⇒
`satisfied(point_in_degenerate_interval)`、点=区间下沿 ⇒ `unknown`
(不在闭开上做小动作)。单位 ✓:事实 298 K vs 键规范 °C 的 20–30 要求 ⇒
`unknown(unit_mismatch:'K'(首版无换算,不按数值直比))`——298 K 实为
24.85 °C 本在区间内,仍诚实报 unknown,不偷换算 ✓;`°C` 事实 ⇒
satisfied ✓。待钉两处:**无单位事实**直接按键规范单位解读并参与比较
(实测 25.0 无单位 ⇒ `within_range/satisfied`),文本未声明该规则;
要求侧无单位字段(条件 1)。

**(c) entity basis 与物种作用域——通过,`matrix` 例外。**
他实体 present/absent 均 ⇒ `unknown(entity_not_among_known_facts:
required='NADH',known=[…])` ✓(他实体缺席≠本实体状态);本实体已知缺席 ⇒
`conflict(required_entity_known_absent)` ✓;多种已知供体并存 ⇒ satisfied ✓;
氧形态枚举不等 ⇒ `conflict(value_mismatch:oxygen_regime:anaerobic!=aerobic)`
✓(封闭枚举硬判,注释明确"不得为过测试把所有字符串改 unknown")。
scope 从实际执行检查派生 + `scope_narrowed_by` 留痕 ✓;coverage 取
worst-status(conflict 优先于 unknown)✓。例外:`matrix` 键:
事实 `"aerobic"` vs 要求 `"anaerobic"` 之类走 645-653 通用分支 ⇒
conflict,reason 无键专属语义——见条件 2。

**(d) 再生/启动分轴——通过。**
D7:仅再生支持 ⇒ 环保留且 `unresolved_initial_supply` 保留
(`regeneration ≠ initial_supply`);补 initial_supply 轴证据 ⇒
unresolved 清空;`support_axis` 输出两轴;环不自动 reject ✓。

### 4.3 可直接落进规则文字的修改

1. 2.2 单位条补两句:
   > "要求侧值**恒为键规范单位**(构造器不接受单位字段,单位只属于
   > 事实侧);**无单位事实**按键规范单位解读并参与比较(首版如此,
   > 来源单位不明的风险由事实来源注记承担)。"
   ——或改为代码:给 `build_requirement` 加 `unit` kwarg(与事实同构),
   两案择一,但文本必须与实现同向。
2. 值语义分 basis 处补一行,给 `matrix` 定案(二选一):
   > "`matrix` 是**封闭枚举键**(登记值集与标签,不匹配且双方已知 ⇒
   > conflict,不可解析 ⇒ unknown)"
   ——或 ——
   > "`matrix` 是**开放单值键**:字符串精确比对,已知不等 ⇒ conflict
   > (通用分支),不进标签注册表、不作实体作用域。"
   现状是实现按后者跑、文本没说——读者会以为 7 键都在 (a) 的分类学里。
3. 4.3 阶段绑定条补:
   > "展示层同时给出**当前步结论**与**路线合取结论**(父子两层并列),
   > 任一层单独出现不得代表整体。"

### 4.4 "程序上诚实但化学上误导"风险点

- **双层坍缩**:路线 conflict、当前 compatible 并存是设计;若展示只出
  一层,两个方向都会误导——只出当前层=掩盖历史冲突,只出路线层=冤枉
  新阶段已合规的步骤。
- **`matrix` 未定案**:开放值被当封闭判(误杀一次拼写差异即 conflict),
  或封闭值该 unknown 却混在通用分支里——两种读法都能"自圆其说",
  复审方无法从文本预测行为。
- **无单位事实静默按键解读**:来源若实际是 K,300 无单位进 °C 区间
  会给出方向相反的 satisfied/conflict,而理由码看不出单位曾缺失。

---

## 5. 判据五:供体一致性诊断

### 5.1 结论:**有条件同意**(3 条硬条件;不处置则**不同意**)

1. **CIP 腿换实现**(行为级):`_cip_of` 用 legacy
   `AssignStereochemistry`(`audit.py:1284`),在自由基产物上给**未被
   编辑触及**的远程立体中心伪造 CIP 翻转,导致**控制例(执行=声明)
   被判 center=False 且 extra_changes 记录假立体变化**(实测见 5.2(a) E-ii);
2. **联合映射的手性门**(行为级):`_joint_symmetric_image` 用
   `useChirality=False`(`audit.py:1509`),把立体化学**可区分**的两个
   位点当等价,**错位编辑被判 center=True 构成 verified 证据**
   (实测见 5.2(b) E-i;修复可行性已验证);
3. **属性 diff 披露范围入文**(文本级,建议加字段):声明–执行对账是
   ops-only,中心原子上的电荷/氢/立体变化**无披露通道**
   (实测见 5.2(c) E-iii);§5.3 的范围声明必须把这一点与
   strict 轴的消费责任写清楚。

### 5.2 直答

**(a) 实际净变化集合定义——骨架充分,CIP 腿有实现缺陷。**

- 组合(键 diff ∪ 增删 ∪ 逐原子电荷/ΔH/CIP)定义正确且互相补位:
  中心外 `h_count` 变化被 `extra_changes` 逐原子披露(before/after 成对,
  E6 例:`S_C_3 h 2→1`、`S_O_1 h 1→0`);`declaration_only` 单列 ✓。
- **零净变化永不 True** ✓:真实 noop(`change_bond_order single→single`)
  与 s→d→s 序列均 `center=None + no_executed_change`,
  `net_change_empty=true`,且顺带披露声明失配
  (`declared_change_not_executed:change_bond_order`) ✓。
- **同位素无假阳性** ✓:重氢分子的自同构搜索在立体感知下不把
  `[2H]`↔`[H]` 当等价(探针 E3:两例 joint 均 None)——r2 担心的
  同位素盲区在 RDKit 层被挡住。
- **缺陷 E-ii(硬条件 1)**:控制例——执行的正是声明的键断裂
  (`C[C@H](Cl)[C@H](Cl)C` 断甲基–手性碳)——却被判
  `center=False`,唯一 `extra_changes` 是远程原子 `R_C_3_R`
  `stereo: before_cip R → after_cip S`。核对:该原子**手性标签未变**
  (`CHI_TETRAHEDRAL_CCW`→同),`rdCIPLabeler` 前后均报 `R`,
  legacy `AssignStereochemistry` 在自由基产物上错报 `S`——
  即 extra_changes 记录了一次**没有发生的立体变化**,并因变化集
  膨胀(3 原子 vs 2 中心,联合映射尺寸不匹配)把正确编辑误杀成
  center=False(admission 落 R5v 而非 expand)。

**(b) 联合图映射判定——反例集通过,对称搜索有系统性假阳性。**

- 环己烷反例 ✓:`{相邻对}` vs `{对位}` ⇒ `center=False`,
  单原子各自同轨**不冒充**联合等价 ✓;搜索截断分支 ⇒ unknown(代码);
  中心部分缺映射 ⇒ unknown ✓;等价类只披露、不参与判定 ✓。
- **缺陷 E-i(硬条件 2)**:底物 `C[C@H](Cl)[C@H](Cl)C`(2S,3R),
  供体声明中心为键 (0,1),实际执行断的是另一端的键 (3,5):
  - 判定:`center=True, basis=symmetric_equivalent,
    joint={'center_image':[3,5], 'n_automorphisms':2}`,
    `declaration_mismatches=[]`、`missing=[]`——**全绿**;
  - 化学事实:两端是**立体可区分**位点(一端 S、一端 R,盲自同构把
    它们互换),两个产物是**不同种**——
    错位产物 `C.C[C@H](Cl)[CH]Cl` = `cs_b8f6e20cee2a23807d9a`,
    声明位点产物 `C.C[C@@H](Cl)[CH]Cl` = `cs_e9c6ed81ea7cc857eeae`
    (判据一身份轴自己判为不同 state);
  - 即使调用方给了独立的期望产物,`strict_target_match=False` 也
    **进不了任何检查**(见 3.2(b));代码里的
    `equivalence_note("图等价≠酶识别/机制等价")` 只是注释,判定照样 True。
- **修复可行性已验证**(`e2e8.py` F-D5):`useChirality=True` 下——
  meso 底物的互换映射被拒(blind=2/aware=1)即 E-i 被拦;C2 对称
  `(2S,4S)` 底物的合法互换**保持接受**(aware=2)、无手性骨架与
  gem-二甲基等位甲基场景均不受影响(blind=aware)。一个开关即可,
  附带把"products 不同种 ⇒ 不得 verified"写成证据前置条件更稳。

**(c) 声明–执行对账范围(ops-only)——设计可辩护,但范围声明缺三件事。**

ops-only(键变化+原子增删双向)本身合理:属性归属性轴,不混进对账。
但当前范围造成三个盲区,文本必须披露:

- **E-iii(条件 3)**:中心原子上的**未声明属性变化**无通道——
  1) 电荷版(探针 E4/E4b):中心 N 未声明 +1,`decl_mismatch=[]`、
  `center=True/direct`、`extra=[]`、`reasons=[]`;期望产物也带该变化时
  `strict=True` → **全字段 verified,零披露**;
  2) 立体版(`e2e8.py` F-E3a,更硬):2-戊醇断末端 C4–C5,声明中心内
  的手性碳(原子 idx1,呈报为 `R_C_2_S`)被注入**未声明的构型翻转**——
  `decl_mismatch=[]`、`center=True/
  direct`、`extra=[]`、`strict=True`、`cn=True`、`missing=[]` 全绿,
  而产物是不同种(`cs_51f3218012c5c21625a6` → `cs_77e81c13cd2c08f6451b`)。
  检测完全依赖期望产物来自哪里;而 ops 声明语言里**根本没有**
  "翻转/带电"这类操作,合法的差向异构步骤同样无从声明。
- **strict 轴无消费方**(条件 3/判据三条件 3):全源码 grep
  `strict_target_match` 仅定义与赋值;证据助手 `audit.py:1840` 也把它
  丢掉——判据 5.8 的 strict 轴目前是诊断内部字段,对 admission 零贡献。
- **legacy_cn_match 是立体盲的**:E-i 与 E-iii 中 `cn=True` 都发生在
  不同种产物上;5.8"仅旁证"的限定必须保持,展示层不得把 cn=True
  与身份结论并排。
- 正向项:plain 与 mapped 执行图不一致 ⇒ 两轴 unknown +
  `plain_product_mapped_product_disagreement` ✓(E5);执行失败 ⇒ 全轴
  unknown ✓;中心外偏离 ⇒ center=False + extra_changes 逐原子披露 ✓(E6)。

### 5.3 可直接落进规则文字的修改

1. 5.1 条逐原子 diff 括注改:
   > "CIP 立体描述符用 **rdCIPLabeler(CIPLabels)口径**(阶无关、
   > 自由基稳健);legacy AssignStereochemistry 结果不得进入变化集
   > ——未编辑原子的 CIP 不得因表示重建而'变化'。"
2. 5.5 条联合图映射句改:
   > "联合映射须为**保手性的**图自同构(`useChirality=True` /
   > 映射两端 CIP 相容);仅盲拓扑等价而两端立体可区分时,
   > center 不得为 True(降 False+披露,或 unknown,二选一钉死);
   > 且 **产物与声明位点产物非同一 ChemicalState 时,
   > 证据不得注册为 verified**(判据三证据门)。"
3. 5.3 条范围声明补:
   > "对账是 **ops 级**;中心原子上的形式电荷/ΔH/立体属性变化
   > **不在对账与 extra_changes 的披露范围内**(后者只覆盖中心外原子),
   > 其检出完全依赖期望产物比对(strict)与判据二的账;
   > strict 必须被证据层消费,否则该盲区不可见。"
   ——建议同时加披露字段 `center_property_deltas`(中心原子属性
   before/after,只披露不改判),成本低、直接消除 E-iii。
4. 5.8 条 legacy_cn_match 后补:"legacy CN 为立体盲旁证,
   不同立体种可 cn=True;禁止作为身份/一致性证据引用。"

### 5.4 "程序上诚实但化学上误导"风险点

- **E-i 是本判据核心承诺的直接反例**:判据自称"实际净变化区域诊断、
  不冒充完整变换一致",注释也写了"图等价≠酶识别/机制等价",但输出
  `center=True + basis=symmetric_equivalent` 经证据助手直达
  `transformation_center: verified`——酶区分得开的两位点(产物都不同种)
  被认证为同一位点,理由码里还带着 `basis=` 让人以为经过了证明。
- **E-ii 双重误导**:正确编辑被打成"中心偏离"(误杀降级),同时
  extra_changes 里记录一次不存在的 R→S 翻转——下游立体审计会拿着
  伪造的 before/after 做决策。
- **E-iii 全绿不同种**:五个字段全部 verified/空,读起来像
  "声明的都执行了、没别的变化",实际中心构型已换、state_id 已变;
  而声明语言里根本没有能表达这一步的操作——"诚实"只对 ops 层成立。
- **strict 沉默**:唯一能把"产物不是声明位点该得的"挑出来的轴,
  没有任何消费方;拼装成"verified"的路径上无人回头看它。

---

## 6. 冻结前必须处置清单(按"误导/误杀"风险排序)

| # | 项 | 归属 | 一句话 | 类型 |
|---|---|---|---|---|
| 1 | legacy `_cip_of` 伪造远程 CIP ⇒ 控制例 center=False + 假 extra_changes | 判据五 5.1(E-ii) | 换 rdCIPLabeler,补自由基产物立体夹具 | 代码 |
| 2 | 盲自同构把立体可区分位点判 center=True,产物异种仍 verified | 判据五 5.5(E-i)、判据三证据门 | `useChirality=True`(可行性已验)+ 产物同一性前置 + strict 入证据并被消费 | 代码+文本 |
| 3 | 混合并列注解 ABS 不剥离 ⇒ 同一立体事实两 state_id(3 组 id 分裂) | 判据一 1.2 | 正则按逗号拆段剥离,补混合形态同键夹具 | 代码 |
| 4 | R2p off 开关下部分被拒产物零披露仍 expand | 判据三 R2p 行 | 开关只关消费不关披露,补披露性理由码 | 代码或文本 |
| 5 | input_hash 不含依赖解析状态与中心证据结论,却称"覆盖实际科学输入" | 判据三关键定义 | 补指纹字段,或改口径为"判定前输入"并禁互换推理 | 代码或文本 |
| 6 | 中心原子属性变化(电荷/立体)无披露通道;strict 无消费方 | 判据五 5.3(E-iii)、判据三 | 文字钉死范围 + `center_property_deltas` 披露字段 + strict 消费 | 文本(+字段) |
| 7 | §1.2 AND/OR 语义句与 RDKit Book 对调 | 判据一 1.2 | 按 1.3(1) 改写两句 | 文本 |
| 8 | RegistrationHash"一致"声明过宽;逐字相同句缺自由基例外 | 判据一 1.2 | 范围限定 + 已登记分歧 + 例外句 | 文本 |
| 9 | `build_requirement` 无 unit 契约;`matrix` 键值语义未定案 | 判据四 4.2 | 两处二选一,文本与实现同向 | 文本/契约 |
| 10 | `build_hypothesis` 裸 TypeError + requirements 无 schema 校验 | 判据三 R2b 行 | 一律 `HypothesisContractError(detail)`,构造期校验 level/value | 代码 |
| 11 | 阶段绑定双层结论须并列显示 | 判据四 4.3 | 展示层两层并列,任一层不得代表整体 | 文本 |

判据二为本轮唯一**无条件同意**项。第 1、2、3、10 项需要改代码与测试,
其余可在规则文本+夹具层完成;所有反例(含临时探针)须在冻结前转为
仓库回归测试。判据一/三/四/五在上述处置并经程序证据互证前
**不建议冻结**;判据五的 3 条硬条件未处置前按本回应 5.1 记**不同意**。
