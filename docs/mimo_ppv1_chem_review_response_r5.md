# mimo 化学评审回应:pollutant_pathway_v1 判据 v5(R5 回修版)

- 日期:2026-10-07(第 5 轮;回应 `mimo_ppv1_chem_review_request.md` v5)
- 对象:S0–S2 回修版判据草案 v5(实现于 `src/pathway_v43/pollutant/`,**未冻结**)
- 格式:按请求 §7,逐判据 1) 结论 2) 可直接落进规则文字的修改建议
  3) "程序上诚实但化学上误导"风险点
- 方法与证据(全部独立取证,不采信交付书自述):
  - 交付书 §6 程序证据独立复跑:`pytest` ppv1 13 文件 → **381 passed/0 failed**;
    `-m "not slow" tests/` → **992 passed / 16 deselected / 0 failed**;
  - 首手读码:`chemstate.py`(身份键/守卫)、`audit.py`(证据门、
    `_bond_changes`/`_declaration_accounting`/`_simulate_declared_edits`、
    载荷构造)、`path_context.py`(live 作用域/快照签名/单位契约/依赖轴);
  - 独立探针 4 件(临时目录,见附录 A;**冻结前须入库为回归**,附录 A 给出清单);
  - 仓库既有回归引用(凡探针与回归双覆盖处,以"代码+探针+测试"三方一致为准)。

---

## 判据一:分子身份

### 1) 结论

- **(a) 三类登记表划分(含 SgD 全类剥离 / Sg 全类保留):同意。**
  实测:`CCO |$_foo:0$|`(DAT 注记,化学样值)与裸 CCO 同 id(剥离);
  `CCO |Sg:n:1,2,3:n|`、`CCCCCC |Sg:n:1,2,3:3:ht:::|` 与裸骨架**不同 id**
  且**往返重建同 id**(探针 4)——"保留类承载化学事实、往返闭合"两条
  均成立。DAT 按 SubstanceGroup **类型**分子级剥离、非字符串令牌解析,
  与文本口径一致。
- **(b) 未登记类默认拒绝:有条件同意。条件见下。**
  分三层实测:
  - RDKit 能解析且规范写出器**再产出**的未登记类(如 `|w:1.0|`):
    `ChemicalStateError, kind=unregistered_cx_class` —— 与文本一致 ✓;
  - 语法不可解析的外部扩展段(`w:1:0.0`、`LN:1 3 2 1 2 3`、
    `atomProp:0:note:hello`、`atom:0`):拒绝,但机读码是
    `unparseable_smiles` 而非文本举例的 `unregistered_cx_class`
    (仍属诚实拒绝,仅码不同步);
  - **例外(不满足文本):`|r|` 旗标块与 RDKit 宽容忽略的畸形块,
    端到端被接受并静默并入身份。** 实测 `C[C@@H](N)C(=O)O |r|`
    (消旋丙氨酸)与裸 `C[C@@H](N)C(=O)O`(纯对映体)**同 state_id**
    —— RDKit 解析 `r` 后在规范写出时丢弃它,守卫只见不到扩展段,
    永不触发;`C1CCCCC1 |Ln:1|`(畸形块)同样被宽容忽略后与裸环己烷
    同 id。仓库测试 `test_r4_08_unregistered_cx_class_rejected`
    (tests/test_ppv1_r5_chem.py:701-703)是**直接调用守卫函数**钉
    拒绝语义,该测试自述"本仓生成路径不产未登记类"——绿测试
    **没有覆盖真实输入入口**对 `|r|` 的行为。文本判据一 2.未登记类
    段明确以"旗标块 r"为拒绝例,并要求"不默认进身份**也不默认剥掉**";
    当前入口行为恰是"默认剥掉"。
- **(c) 往返句的映射号例外:同意。** 实测 `C[CH2:1]O` 与 `CCO` 同 id、
  往返串 == 普通 canonical isomeric、自由基 `[CH2]O` 规范输出
  `[CH2]O |^1:0|` 往返同 id 且与甲醇不同 id——文本三条(映射号剥离、
  往返闭合、自由基后缀登记缺口)与实现一致。
- **(d) "组覆盖 ABS"矛盾输入解析:同意。** 端到端实测
  `C[C@H](Cl)[C@H](F)Cl |a:1,&1:1,3|` 与仅组形式 `|&1:1,3|` 同 id、
  规范存储剥去 `a:1`、往返同 id;"组成员资格覆盖 ABS"按登记规则落地;
  `|a:1|` ≡ plain 亦同 id(已登记分歧,文本已声明)。混合并列归一
  `a:1,&1:3 ≡ &1:3` 由 tests/test_ppv1_r4_chem.py:155 钉住。

### 2) 文本修改建议(可直接落字)

1. **未登记类段补输入侧口径**(判据一 2. 第三个要点内,紧接
   "unregistered_cx_class,如 …" 之后):

   > 拒绝检查以**原始输入扩展段字符串**为入口先行校验:RDKit 宽容
   > 解析会静默丢弃部分未登记块(实测旗标块 `r`、畸形 `LN/Ln` 类
   > 被丢弃后与裸骨架同 id),故不得以"解析后规范输出不含该块"代替
   > 拒绝。语法不可解析的外部扩展段归 `unparseable_smiles`(同为
   > 拒绝,机读码与 `unregistered_cx_class` 分列,均不进身份)。

   配套实现:入口处对 `|…|` 段做登记表字符串预校验(与
   `_guard_registered_cx_classes` 同一张表),或解析前后块集合比对
   (输入有块、规范输出无块 ⇒ 拒绝)。**在此之前,文本应把
   `r` 从"已实现拒绝例"降为"目标行为",避免规则声称未落地。**
2. **SgD 剥离补前提句**(判据一 2. 移除类要点末尾):

   > SgD 全类剥离以"DAT 仅承载出现/注记元数据"为前提;若适配器把
   > 化学事实写入 DAT,该前提失效,须改写为结构事实后重评剥离口径。

### 3) 风险点

- **R1-1(实测):消旋旗标静默丢失 ⇒ 消旋物与纯对映体同身份。**
  `… |r|` 被接受、与裸写同 id;程序无任何警告,身份层面把"外消旋
  样品"与"单一确定构型"当同一物质。这正是文本"不默认剥掉"要防的
  无声明状态;当前只有生成输出侧守卫,输入侧无防线。
- **R1-2(按类型剥离的暗面):** SgD 按 TYPE 全剥不看内容——若未来
  有来源把组分角色/条件值写进 DAT,身份会静默丢失差异。风险由
  适配器契约兜底,建议以第 2 条修改把它写成显式前提。
- **R1-3(诚实但易误读):** `unparseable_smiles` 与
  `unregistered_cx_class` 是两种拒绝理由,下游若只判"是否拒绝"则
  等价,若按机读码分支统计"未登记类出现率"会低估(部分案例落在
  unparseable 码)。程序诚实,统计口径需知悉。

---

## 判据二:参与物计量与元素/电荷核算

### 1) 结论

**同意;v4 已同意条款无需重评;恒等≠落点分工复核通过。**
实测分工:共底物未覆盖场景下 center=verified、
product_coverage=full,而元素核算 violated ⇒ admission
`retain_conditional`(探针 2a)——覆盖轴的"完全覆盖"没有掩盖
核算轴失败;恒等(判据一身份)与落点(判据五
center_property_deltas + 严格轴)分通道,`_declaration_accounting`
文档明确"原子属性不在 ops 对账范围,检出走属性 diff 披露 + strict 轴",
与文本"落点指路"一致。

### 2) 文本修改建议

无需修改。若判据三覆盖括注按本回应判据三-2) 落字,此处可加半句
交叉引用:"恒等与落点差异由判据一身份轴与判据五 center_property_
deltas 承载,本判据只管账平不管落点"(可选,防重复解读)。

### 3) 风险点

- **R2-1(登记项复述,无新增):** local_delta pending 排除声明、
  R5d 触发集合限定 {元素,电荷} 均为已登记设计;风险在于"账平"
  不等于"落点对",下游若把 element accounting satisfied 读成
  "转化已核实"即越权——由判据五/判据三分工文本约束,未见新缺口。

---

## 判据三:admission 决策表与中心证据契约

### 1) 结论

- **(a) 证明链内部重算口径:同意。** 独立构造"从未执行过、但自洽"
  的证明记录(手工改图伪造 result)⇒ 中心 verified、admission
  expand——与文本声明的信任边界**相符**(边界声明为真,不是隐藏);
  篡改 bound_inputs 任一字段 ⇒ `AuditContractError,
  kind=center_evidence_integrity_mismatch`(结构化拒绝)✓;类型违约
  `center_evidence_type_violation` 由 tests/test_ppv1_r5_chem.py:258
  钉住;无 proof_record ⇒ unknown 由代码(证据门 3)与回归钉住。
- **(b) 产物集合覆盖与部分覆盖语义:同意。** 实测:仅共底物未覆盖
  ⇒ coverage=full(核算另判,见判据二);旁观者场景 ⇒ 中心 unknown
  带 partial 理由、admission retain_conditional;"未覆盖产物与未覆盖
  共底物并存 ⇒ partial ⇒ unknown"由 tests/test_ppv1_r5_chem.py:336-350
  钉住(`partial_coverage_unchecked_transformation`)。碎片分列、
  未申报碎片 unknown 与文本一致。
- **(c) 信任边界声明:有条件同意。条件 2 条。**
  行为与声明一致(见 (a)),但**声明只存在于规则文档,机器输出不可见**:
  1. **载荷不披露运行事实缺口**:verified 中心检查的
    reason/detail 中检索不到任何"自包含重算、非运行事实"字样
    (探针:`payload_discloses_runfact_gap=false`)。下游只见
    `center_evidence_verified:…`,无法区分"复算自洽"与"执行器真跑过"。
  2. **`basis=` 恒为空(展示回归)**:verified 理由码实测为
    `center_evidence_verified:ppv1-donor-diagnostic-5(scope=region_net_change;basis=)`
    —— audit.py:935-936 从 `recomputed.center_evidence` 读
    `center_match_basis`,而载荷构造(audit.py:2518 起)不含该键;
    只有旧形状回退助手(2661 行)会补它,正常 v5 路径永不补。
    v4 曾显示 `basis=direct`,v5 变成空串紧跟等号,形似"依据未知"。

### 2) 文本修改建议(可直接落字)

1. **判据三 3.证据门第 2) 条末尾追加输出披露要求**:

   > verified 结论的载荷须同屏披露信任边界:`proof_scope=
   > self_contained_recompute(自包含输入集的复算可复现,不含
   > "编辑曾被执行"的运行事实;运行事实由执行器通道承担)`。
   > 边界仅写在规则文档而不出现在机读输出,视为未满足本条。

2. **判据三 input_hash 要点(R4-02 段)补一句,并给实现一行修复**:

   > 证据载荷携带 center_match_basis(direct|symmetric_equivalent,
   > 仅 center_match=True 时非空);verified 理由码的 basis= 不得
   > 为空串占位(空 ⇒ 省略该字段)。

   配套实现:`audit.py` 2518 行 `evidence_payload` 增
   `"center_match_basis": basis` 一项(与 2566 行 proof_record 同源)。
3. **判据三 3.第 4) 条覆盖括注补交叉引用**:

   > "完全覆盖"仅解除覆盖轴;元素/电荷核算(判据二)与严格轴
   > (判据五)独立把关,全部轴通过方得推进——共底物未覆盖场景
   > 在本判据可为 full,仍可能因核算 violated 走 retain_conditional。

### 3) 风险点

- **R3-1:"verified"标签的语义窄于直觉。** 程序上诚实(边界如实
  声明、篡改被拒),但输出无披露时,任何把 verified 读成"该编辑
  真实发生过"的下游都会被误导——这恰是请求 §3(c) 自己点出的
  信任边界;不落进载荷,边界对机器不可见。条件 1 未落实前,
  本判据不能算完全通过。
- **R3-2:`basis=` 空串。** 不影响判定正确性(direct/symmetric
  仍由 checker 内部使用),但理由码是审计证据屏,空 basis 形似
  "依据缺失"——展示层诚实性回归,修复成本一行。
- **R3-3:覆盖括注的联合语义。** 仅未覆盖共底物 ⇒ full 是对的,
  但若读者略去判据二,会把"coverage=full + center=verified"读成
  全绿;实测该组合下 admission 为 retain_conditional(靠核算轴兜住)。
  文本交叉引用(2)-3)落实前,这是"程序上诚实、文本上易误导"点。

---

## 判据四:条件相容聚合

### 1) 结论

**同意;(a)–(d) 四问逐一确认。**

- **(a) scenario+phase live 作用域:** 首手读码
  `path_context.py::_effective_scope`(二元组比较)与
  `_requirement_covered_by_snapshot`(phase_id + scenario_ref 双匹配)
  一致;同阶段名不同场景不重评旧行为由 test_ppv1_r4_conditions 旧边
  快照用例钉住。
- **(b) 快照签名覆盖(具体要求,非阶段存在):** 读码:
  `derive_child_context`(path_context.py:2048-2065)把该次评估
  **实际生效**的要求逐条 `canonical_json(r.to_dict())` 写入
  `covered_requirement_signatures`;核对侧(840-865)按签名成员资格
  判覆盖,两侧同源。测试钉住双向:test_ppv1_r5_conditions.py:230
  (空快照不得掩盖孤儿必要要求 ⇒ 显式 unknown、admission ≠ expand)、
  :267(sA→p0 的要求被签名覆盖 ⇒ 非孤儿、路线结果由快照行承载)。
- **(c) 单位入口契约:** 实测三行——空单位带量纲键 ⇒
  `unknown / source_unit_unknown`(理由码明示"不按数值直比,不以
  注记升级");显式规范单位 ⇒ `satisfied / canonical`;显式 K ⇒
  `unknown / unit_mismatch`。v4 的 assumed_canonical 升格路径已消失。
- **(d) 分轴撤销语义:** 实测——某轴 contradicted 后,再生支持
  只改轴集合为 `[regeneration]`、总状态保持 `contradicted`(支持
  不洗白反驳);补该轴(initial_supply)新证据 ⇒ `supported` 且
  轴集合 `[initial_supply, regeneration]`;双支持正控制不回退。
  resolution_log 为唯一事实源与文本一致。

### 2) 文本修改建议

无需修改。(c) 中 `unit_mismatch ⇒ unknown` 的 `unit_basis` 当前为
null(不声称基准),与文本"不按数值直比"一致,不必补字段。

### 3) 风险点

- **R4-1(方向安全的保守项):** 依赖某轴一旦反驳,只有该轴新证据
  能恢复;真实体系里"辅酶初始供给被反驳、仅靠再生"将长期
  contradicted ⇒ 路径不推进。化学上可能是保守误伤,但方向是
  retain/不冒进,且正是 R4-05 要求的语义;属已登记代价。
- **R4-2:** 首版无单位换算,`K` 与 `C` 并存即 unknown——诚实但
  会让真实温控路径停在 unknown;登记项,建议 S3 前评估换算表。

---

## 判据五:供体一致性诊断

### 1) 结论

- **(a) 非四面体 unsupported 按标签类型:同意。** 读码与回归一致
  (判据按 GetChiralTag 类型而非"四面体指定成功",公开列项
  `stereo_comparison_unsupported_atoms`;net_change_only 理由码在
  audit.py:2395,由 tests/test_ppv1_r5_chem.py:586-592 钉住)。
- **(b) 联合映射三类支持范围:同意(抽查)。** `_joint_symmetric_image`
  读码与 mimo R4 probe3 口径一致,回归钉住指定↔未指定互换被拒。
- **(c) 镜像活 ID 表与 from_order 前置:同意。** 读码
  `_simulate_declared_edits`(v5:活 ID 表先增后引、逐操作前置、
  `from_order == 列表时点实际键级`、净效应结算、终态 sanitize)
  与文本逐句对应;错误 from_order → `declared_precondition_violated:
  bond_order_mismatch` 由回归钉住。
- **(d) 键级立体入变化集/声明对账签名:有条件同意。条件见 2)。**
  - 正向(尾部断键,E-烯仍全取代):执行成功、
    `stereo_changes=[]`、无声明失配、center=True ✓——不误伤;
  - 同几何、不同立体参考原子写法(三取代烯换参考原子重写,映射
    承载对应):`changes=[]`,无假阳性 ✓;
  - 真翻转(E→Z,同骨架同映射,两种构造方式各测一次):均检出
    `bond_stereo_change(STEREOE↔STEREOZ)` 并入签名 ✓;
  - **反向案例(3b):断 E-烯邻位 σ 键 ⇒ 产物端烯化 ⇒ 执行器
    SMILES 往返后双键立体消失**:检出
    `bond_stereo_change STEREOE→STEREONONE` + 机读码
    `undeclared_bond_change:['U_C_2','U_C_3'](净效应:实际发生了
    未声明的键变化)` ⇒ 中心 None ⇒ admission retain。行为**符合
    文本**("执行图带未声明立体变化即为失配"),方向保守(阻断
    而非放行);但见风险 R5-1/R5-2。
  - (首版探针曾报 3c 翻转对照 `changes=[]`,系对照夹具自身错误
    ——枚举在内存中已被标反;修正夹具后检出,更正版结果如上。)
- **(e) "身份不同而图轴空"理由码:同意。**
  `net_change_only_in_stereo_representation` 实现存在
  (audit.py:2395)且测试钉住("不得称实际净变化为空")。
- **(f) center 外 unsupported 阻断 True:同意。** 读码+回归一致
  (区域约束对该轴不可核 ⇒ center 不可判 True)。

### 2) 文本修改建议(可直接落字)

1. **判据五 4.(键级立体入签名)句末追加**:

   > 断键若使邻位双键取代格局改变(如端烯化),E/Z 消失将**恒为
   > 签名失配且无声明通道**(ops 语言无立体操作,镜像终态不重感知);
   > 此时机读码 `undeclared_bond_change` 指"实际签名 ≠ 声明签名",
   > 不指调用方漏报——该类变换在本版为**保守不可通过**(方向
   > retain),不得解读为申报缺陷。

   (若 S3 想放行此类变换,需另设"断键致立体消失"的显式声明通道,
   本版不设。)
2. **判据五 4. 镜像口径补一句**:

   > 镜像终态的立体比较须与执行器同一归一路径:当前镜像读内存
   > `GetStereo`(编辑后不重感知),执行器经写出-重解析(重感知),
   > 两者存在知觉差;3b 两路同向(皆失)未暴露分歧,登记为边界,
   > 改变归一路径时须复评本条。

### 3) 风险点

- **R5-1(程序上诚实、化学上误导,本轮最主要项):** 3b 的立体
  消失是所声明断键的**化学必然结果**(端烯化后无 E/Z 可言),但
  机读码措辞"实际发生了**未声明的键变化**"把必然结果说成申报缺失;
  且不存在任何正确申报能让该变换通过——正确程序与"漏报"得到同一
  负面措辞。方向安全(阻断/retain),语义误导;按 2)-1) 落字前,
  下游会把合法申报的断裂步骤记为"申报不实嫌疑"。
- **R5-2(镜像-执行器知觉差):** 立体对账一侧是编辑后内存图
  (stale stereo),一侧是写出-重解析图(重感知)。3b 中两者恰好
  同向,3c 实测同几何重写两侧稳定,但"归一路径不同"这一结构仍在;
  未见反例不等于没有(例如执行器往返改变参考原子选择而几何未变)。
  建议按 2)-2) 登记为已知边界。
- **R5-3(登记项):** cip_label_change_is_not_config_change 为
  建议项(文本已标);若下游把 CIP 标签 diff 当构型变化,读码上
  载荷已带提示,但需消费方主动读——诚实但依赖阅读。

---

## 附录 A:独立探针清单(冻结前须入库)

以下探针由 mimo 本轮独立编写,现处临时目录,**属第 5 轮程序证据
的一部分;判据冻结前应按仓内规范转为 `tests/` 回归或
`docs/review_evidence/` 存档**(当前仅临时目录,不满足可追溯要求):

| 探针 | 路径(临时目录) | 覆盖 |
|---|---|---|
| probe1 | `.../T/opencode/ppv1_r5_mimo_probe.py`(输出 `ppv1_r5_mimo_probe_out.json`) | 判据三信任边界/覆盖分工、判据五 3a/3b/3c、判据一 CX 主组、判据四单位与依赖轴 |
| probe2 | `.../T/opencode/ppv1_r5_mimo_probe2.py`(输出 `ppv1_r5_mimo_probe2_out.json`) | 3c 同几何重写/真翻转双对照、`|a:|` 组立体与外挂 CX 判别力 |
| probe3 | `.../T/opencode/ppv1_r5_mimo_probe3.py`(输出 `ppv1_r5_mimo_probe3_out.json`) | `\|r\|` 手性合并、w/LN/atomProp 各语法的入口行为(接受/拒绝/静默丢弃)、Sg 保留 |
| probe4 | `.../T/opencode/ppv1_r5_mimo_probe4.py`(输出 `ppv1_r5_mimo_probe4_out.json`) | 组覆盖 ABS 矛盾输入端到端、Sg 往返同 id |

(`.../T/opencode` = 本机系统临时目录 `private/var/folders/…/T/opencode`。)

## 附录 B:独立复跑记录

- `pytest`(ppv1 13 文件):**381 passed / 0 failed**(与请求 §6 一致);
- `pytest -m "not slow" tests/`:**992 passed / 16 deselected / 0 failed**(与请求 §6 一致);
- 全部探针结论以更正后的一次运行为准(3c 翻转对照夹具修正后复跑;
  probe1 全量复跑,输出已刷新)。

## 总表

| 判据 | 结论 | 冻结前条件 |
|---|---|---|
| 一 分子身份 | (a)(c)(d) 同意;(b) 有条件同意 | 输入侧登记表预校验落地,或文本把 `r` 降为"目标行为"并登记解析丢弃分歧 |
| 二 计量核算 | 同意 | 无 |
| 三 admission/证据门 | (a)(b) 同意;(c) 有条件同意 | ①载荷披露 proof_scope;②`center_match_basis` 入载荷(或删空 `basis=`);③覆盖括注交叉引用 |
| 四 条件聚合 | 同意 | 无 |
| 五 供体诊断 | (a)(b)(c)(e)(f) 同意;(d) 有条件同意 | ①3b 恒失配语义落字;②镜像-执行器归一边界登记 |
