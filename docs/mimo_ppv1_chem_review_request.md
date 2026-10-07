# mimo 化学评审请求:pollutant_pathway_v1 化学判据(S0–S2 回修版 v6)

- 日期:2026-10-07(R6 回修版;替换同日 v5 请求)
- 触发点:AGENTS.md mimo 三触发点之 1(需评判化学结构时——冻结或发布前)
- 评审对象:S0–S2 第六轮回修后的化学判据草案 v6(实现于
  `src/pathway_v43/pollutant/`,ppv1-*-6 版本族);**尚未冻结**
- 与 v5 的差异来源:第五轮 mimo 回应
  (`docs/mimo_ppv1_chem_review_response_r5.md`)+ Codex R5 复审
  (`POLLUTANT_PATHWAY_S0_S2_CODEX_REVIEW_R5_2026-10-07.md` R5-01～08
  与 §5 采纳边界)。Codex 已互证的 v5 缺陷:单侧覆盖自动 full
  (R5-01)、原始 CX 输入绕过注册检查(R5-02)、非物种 known_absent
  当正事实(R5-03)、恢复入口信任矛盾快照(R5-04)、出现清单不覆盖
  先存来源(R5-05)、既存假设首用不验(R5-06)、旧兄弟来源循环证明
  (R5-07)、镜像漏执行器终态序列化(R5-08)共 8 项 P1 + 2 项 P2。
- **Codex R5 §5 不采纳并已修正的两点**(与 mimo v5 回应的分歧,供
  本轮重新表态):①mimo 曾"完全同意判据三覆盖语义"——Codex 用两组
  **数值完全配平**的公开 API 反例证明集合覆盖不安全(单侧空即 full),
  本轮改为**系数绑定 + 注册计量补全规则**(见判据三 4);②mimo 曾
  建议"断键致 E/Z 消失须另设立体申报通道才能通过"——实测同一终态
  序列化(镜像写出/重解析)即对齐,无须新增申报通道(见判据五 4);
  相应地"3b 恒失配"表述废除。
- 自包含性:规则级表述与合成规则级夹具,无任何金标/题面/封存
  逐题数据;由用户转交,回复原文落盘 `docs/`

## 0. 背景(一段话)

v5 判据经第五轮代码复审发现:证据覆盖按物种集合判定,两组数值配平
的单侧反例(真实 CCO→CC=O 证据用于 CCO→1/2CC=O+1/2C1CO1+H2;真实
CC=O→CCO 证据用于 CC=O+C1CO1+2H2→2CCO)均直达"全部核实"并放行
展开;原始 CX 的 |r|/|Ln:1| 被解析器静默丢弃后与裸输入同身份;
oxygen aerobic absent/matrix soil absent/温度 25°C absent 均能满足
必要条件;恢复入口只信快照旗标摘要;事件出现清单不覆盖先存来源;
既存假设行首用不验;旧同父兄弟来源用循环查询自证;诊断镜像不随
执行器做终态序列化。8 项 P1 + 2 项 P2 已全部回修并有行为级红绿
回归(基线 293bc62 新增回归 70 例红 44/绿 26,其中 6 红仅因 v6
新披露键、其核心语义基线已绿;ppv1 全量 451 passed/0 skip)。
本轮请评审**回修后的判据文本 v6**。目标不变:可能降解路径与
条件相容路径的诚实表示;unknown 不升格;verified 不靠模型或调用
方自报字符串;**账平、物种同 CN 或一份正确局部诊断不能代替整条
声明的覆盖与追溯**。

## 1. 判据一:分子身份(v6 文本)

1–4 同 v5(state_id 生成条件/化学 CX 事实子集三类逐类登记表/
混合并列 ABS 归一/公开表示往返闭合/fidelity 分轴;细节略,见
仓内 v5 请求存档)。v6 改第 2 条的执行位置:

2. **输入侧注册感知校验(R5-02,替换 v5 的"守卫只看规范输出")**:
   拒绝检查以**原始输入扩展段字符串**为入口**先行**校验——
   build_chemical_state 与 strict_identity_of 两个公共结构入口在
   解析之前调用输入守卫;RDKit MolFromSmiles 宽容解析会**静默丢弃**
   部分未登记块(实测旗标块 `r`、`Ln`/`LN`、`c`、`wU`、`o`、`O`、
   `d`、`n`、`F` 等),丢弃后与裸骨架同 state_id/as_written,输出侧
   守卫永远看不到——此前文本声称拒绝 `r` 但入口并未落地(mimo R5
   1(b) 的例外已修)。输入侧登记表按**类级**处理(与输出侧同一
   注册体系):
   - 登记移除类:`$…$` 标签/值块($_AV、atomLabel)、`(…)` 坐标块、
     `atomProp:`、`SgD:`(内容不查——SgD 值可含逗号,**不按逗号
     拆整段**;解析为属性/组后生成前清除,同 ID);
   - 登记保留类:`Sg:`(SRU/聚合物等非 DAT 组,内容不查);
   - 登记保留注记类:`a`/`oN`/`&N`/`^N`(逐 token 复核注记头与
     裸数字原子列表延续,含 `!` 前形);
   - 无冒号旗标块与其余未知类 ⇒ ChemicalStateError
     (kind=unregistered_cx_class,构造即拒);语法整体不可解析
     的外部扩展段归 unparseable_smiles(同为拒绝,机读码分列);
   - **不把输出侧逗号拆分守卫搬到原输入,也不"输入输出不等一律
     拒绝"**(合法移除的 DATA/标签/坐标与保留事实并存)。

**请评审**:(a) 输入侧类级登记表的划分(移除/保留/拒绝)与
"解析器静默丢弃 ⇒ 拒绝"的默认行为;(b) 两个公共入口一致的
执行位置;(c) 逗号不拆整段的边界(SgD 值内逗号)。

## 2. 判据二:参与物计量与元素/电荷核算(v6 文本)

1–8 同 v5(全氢账/系数契约/完整性 unknown/电荷轴前提/结构化
omission_pattern_matches/H+_count1 命名;R5d 触发集合限定
{元素,电荷};恒等≠落点口径句)。v6 无变化。

**请评审**:确认已同意条款不需重评。

## 3. 判据三:admission 决策表与中心证据契约(v6 文本;有序,首中即决)

R1/R1b/R2/R2p(on/off 披露)/R2b/R3/R4/R5d{元素,电荷}/R5v/
R5c/R5/R6/R7 行语义同 v5。v6 重写证据门的第 4 条并增披露:

- 1) 类型契约、2) 内部重算、3) 无 proof_record ⇒ unknown——
  同 v5(结构化拒绝/自报须与复算一致/两条身份字符串不构成证明);
  **复算比对增 center_match_basis**(自报 basis ≠ 复算 basis,
  如声称 direct 实为 symmetric_equivalent ⇒ integrity 拒);
- 4) **绑定核验(复算值)——覆盖绑定参与物系数/贡献 + 注册计量
  补全规则(R5-01,替换 v5 的"集合覆盖 + 单侧空即 full")**:
  设 s=复算底物身份、p=复算产物身份(可为点分碎片串如 "C.CO"):
  - 底物绑定:证据底物身份 == 本假设 primary substrate 身份;
  - **λ_s(底物规模)= Σ 反应物侧 identity==s 的参与物系数**
    (须全部 known);
  - 覆盖产物集:整分子(p ∈ 产物 identity 集合)或碎片(p 按
    "." 拆、全部碎片须有对应参与物)两级映射(真实断裂的分列
    产物正确绑定,不要求把碎片拼成一个物种);碎片无参与物 ⇒
    未申报碎片 ⇒ unknown;
  - **系数绑定**:每个覆盖 identity 的产物侧声明系数总和 ==
    λ_s × 该 identity 在 p 中的重数(关断"1/2 乙醛 + 1/2 环氧
    乙烷"类反例:声明 1/2 ≠ λ_s=1 ⇒ 部分覆盖);
  - **注册计量补全规则**(命名
    `atom_delta_stoichiometric_completion`):Δ=elements(s)−
    elements(p)(逐元素分数);**Σ 未覆盖产物元素(系数加权)
    == λ_s×Δ⁺(被核实转化释放的原子)且 Σ 未覆盖反应物元素 ==
    λ_s×(−Δ)⁺(被核实转化消耗的原子),两侧各自精确相等,
    不许盈余/亏空互相抵消**(关断"环丙烷→丙烯"同式量异构反例:
    净差可抵消但两侧各自超出);**无未覆盖参与物 ⇒ 覆盖 full**
    (元素账是否平衡归判据二独立轴,不在此重复);**整类共底物/
    共产物(H2、水等)不按名称免审**——只按本规则的元素账判;
    合法的 H2 计量补全(乙醇脱氢 CCO→CC=O+H2、乙醛加氢
    CC=O+H2→CCO、比例缩放 2CCO→2CC=O+2H2)恰由 Δ 两侧精确
    相等放行;
  - 未知系数 ⇒ 覆盖 unknown_coefficients(中心 unknown);
    违反 ⇒ 部分覆盖(partial_unchecked_transformation)⇒ 中心
    unknown、不 R6;detail 披露 coverage_rule/substrate_scale/
    atom_delta/两侧未覆盖元素/逐条 coverage_violations;
- 5) strict 轴消费、input_hash 域、audit.scope 不遮蔽——同 v5;
- **新增披露(P2/R5 §4-1,mimo R5 冻结前条件 ①②的落实)**:
  verified 结论的载荷与理由码**同屏披露** `proof_scope=
  self_contained_recompute`(自包含输入集的确定性重算可复现,
  不含"编辑曾被执行"的运行事实;运行事实由执行器通道的 result/
  指纹绑定)与 `center_match_basis`(direct|symmetric_equivalent,
  仅 center_match=True 时非空,不再空串占位);覆盖括注交叉引用
  (mimo R5 条件 ③):"完全覆盖"仅解除覆盖轴,元素/电荷核算
  (判据二)与 strict 轴(判据五)独立把关,全部轴通过方得推进。

**请评审**:(a) 系数绑定与注册补全规则 `atom_delta_stoichiometric_
completion` 的语义(两侧各自精确相等、不许抵消、无未覆盖即 full);
(b) "整类共底物不按名称免审"与"不要求每个计量共产物完整走
AtomTool"的边界;(c) proof_scope/center_match_basis 披露位置;
(d) 信任边界声明同 v5(证明记录是自包含输入集,自洽构造复跑即
通过;运行事实归执行器通道,S3 完整模板另议)。

## 4. 判据四:条件相容聚合(v6 文本)

1–4、7 同 v5(封闭 7 键/区间×点三态/实体身份/matrix unknown)。
v5 的 5/6/8(live 二元组/快照签名/单位契约/分轴撤销)保留,v6
新增两条:

9. **非物种 known_absent 语义(R5-03,新增)**:评估在单位三态
   检查之后、值匹配之前**先消费事实 status**——
   - 物种键实体缺席 ⇒ conflict(v5 已有,保持);
   - 数值/区间值事实被明确否定 ⇒ **unknown**
     (numeric_absence_semantics_undefined:首版未定义数值否定语义,
     "25 不存在"不推出"整个 20–30 区间不存在");
   - 字符串值事实 = 必需值同词被明确否定(封闭枚举/标签)⇒
     **conflict**(required_value_known_absent:必需值被明确
     否定,明确缺失不提供正支持);
   - 字符串值事实 ≠ 必需值 ⇒ **unknown**
     (other_value_known_absent_not_determining:封闭枚举下
     "anaerobic 缺席"不证明 aerobic 在场;matrix 文本不等只证明
     标签未解析);
   - present/unknown/单位控制不受影响;oxygen aerobic absent/
     matrix soil absent 不再 satisfied→R6;
10. **恢复/审核入口核快照一致性与内容身份(R5-04,新增)**:
    - **(a) 快照内部一致性**:phase_history 每条快照的
      environment_fit / has_gate_requirements /
      requirement_coverage.essential_keys 必须与逐条评估行
      (per_requirement)**同源派生**(单向矛盾判定:含 conflict
      行而摘要非 conflict ⇒ 拒;compatible 而行非全部
      satisfied/not_applicable ⇒ 拒;旗标与必要行集合不符 ⇒ 拒);
      covered_requirement_signatures 须 ⊆ 当前累积要求签名集合
      (快照冻结于转换时、子上下文只累积不删要求;签名不能凭空
      覆盖不存在的要求);
    - **(b) 内容身份**:from_dict 与 audit 对直接对象的入口按
      构造期同源算法对全部语义字段(含 phase_history)重算
      context_id,不等于载荷/对象值 ⇒ 结构化拒绝
      (context_content_identity_mismatch)——篡改快照摘要/旗标/
      事实而保留原 context_id ⇒ 拒;合法 to_dict→from_dict 往返
      幂等通过;**不拿当前事实重评旧边,不认证用户事实真实性**;
11. **环诊断按对应有效轴消费(P2/R5 §4-2,新增)**:
    has_initial 只看 initial_supply 轴当前 supported(无总体
    status 门);关系成立 = 全部依赖的关系轴(reaction/
    regeneration)各自当前有效状态通过(至少一条 supported 且
    无一条 contradicted);**不以总体 status 污染两种语义**
    ("initial supported + reaction contradicted"不再误报启动
    未知;"initial contradicted + regeneration supported"不再
    混入关系不支持);环不自动 reject/defer。

**请评审**:(a) 数值缺席 unknown / 同词缺席 conflict / 异词缺席
unknown 的三分;(b) 快照同源派生的单向矛盾判定(不误拒合法
历史);(c) 内容身份重算的位置(from_dict + audit 直接对象
入口);(d) 环诊断关系轴的"任一关系轴被反驳 ⇒ 关系不成立"门
(比字面"至少一条 supported"更保守,只增披露不减)。

## 5. 判据五:供体一致性诊断(v6 文本)

1–3、5–7 同 v5(实际净变化判定基础/奇偶构型比较与非四面体
unsupported/联合映射三类支持范围/中心属性披露/strict 同源/
证据载荷内嵌)。v6 改第 4 条:

4. **声明–执行净效应对账(R5-08,镜像终态归一)**:镜像执行器
   路径模拟——活 ID 表 + 逐操作前置复核(from_order 等)同 v5;
   **终态归一与冻结执行器同一**:执行器产物
   (product_mapped_smiles)是 MolToSmiles 序列化后被消费的
   (映射号以 [C:1] 形式随序列化穿越,立体在重解析时重感知),
   镜像终态同样**先序列化再重解析**后才参与比较——内存镜像
   不走序列化会残留陈旧键立体(实测:真实 C/C=C/C 断邻位 σ 键
   成 C.C=CC,双键端烯化后无 E/Z,实际重解析 STEREONONE 而内存
   镜像残留 STEREOE ⇒ 伪 undeclared_bond_change);镜像同走
   写出/重解析后键变化集合与实际一致,**已声明断键的自然立体
   后果不再称漏申报**;序列化/重解析失败按原内存图(如实失配);
   **不新增立体操作协议、不删除 E/Z 轴、不默认忽略所有 stereo
   loss、不改冻结 executor**;mimo R5 的"3b 恒失配/须另设申报
   通道/镜像-执行器知觉差登记为边界"三条按本修正废除——归一
   路径统一后无该边界;确实在比较支持范围外的情况(非四面体
   等)用既有 unsupported 理由。

**请评审**:(a) 镜像终态序列化/重解析与执行器同口径;(b)
已声明断键的自然 E/Z 消失不再入失配的语义;(c) 其余立体轴
(真翻转检出/伪造失配/from_order/净效应)控制保持。

## 6. 程序证据与状态

- 规则级测试:ppv1 全量 **451 passed/0 skip**(381 v5 存量 +
  70 新增 R6 回归,全部合成夹具);新增回归在基线 293bc62
  **红 44/70**——其中 38 红为复审反例行为翻转、6 红仅因 v6
  新披露键(detail 的 substrate_scale/atom_delta/coverage_rule/
  center_match_basis/proof_scope,其核心语义断言在基线已通过)、
  26 绿为基线已绿的正控制;
- G01 全量 not slow 与 R5 复审探针复跑:见 R6 交付书 §5(探针
  在 v6 复跑:8 组 P1 + 2 项 P2 逐案翻转,旧控制保持;
  assert_observed.py 按设计在翻转点失败,不把旧观测值当新期待);
- 判据未冻结;mimo R5 的冻结前清单处置:条件①②(proof_scope/
  basis 载荷)已落实,③(覆盖括注交叉引用)并入判据三文本;
  判据一输入侧预校验已落地(`r` 从"目标行为"变为已实现拒绝例);
  判据五"3b 恒失配/立体申报通道/知觉差边界"按 Codex R5 §5
  裁定废除(同一终态序列化足以对齐);
- 参考(外部常识,非本仓资产):RDKit Book(CXSMILES 扩展/
  增强立体/立体化学章节/非四面体立体支持说明)、rdCIPLabeler API。

## 7. 请求的回复格式

对每条判据:1) 结论(同意/不同意/有条件同意+条件);2) 可直接
落进规则文字的修改建议;3) "程序上诚实但化学上误导"风险点。
逐条表态,不接受总体评价式回复。
