你是独立外部化学评审员，对 pollutant_pathway_v1 化学判据草案第八轮版本（v8，S0–S2 回修后，尚未冻结）做化学评审。评审请求全文附在最后。

回复要求（与请求原文的回复格式要求相同，重申）：对判据一～判据五**逐条**给出：1) 结论（同意/不同意/有条件同意+条件）；2) 可直接落进规则文字的修改建议；3) "程序上诚实但化学上误导"风险点。不接受总体评价式回复。

执行边界（重要）：
- 本轮你只能用读取类工具浏览仓库源码/文档来核对请求中的表述（仓库根 /Volumes/CC/Enzyme_Agent/dependingv43；判据实现于 src/pathway_v43/pollutant/，回归测试 tests/test_ppv1_*.py）；你**没有 shell 执行权限**，无法运行测试或探针——若某项判断必须依赖执行证据，请如实标注"待执行验证"并说明需要跑什么，**不要编造任何执行结果或数字**。
- 禁止访问 gitignored 金标/题面目录（如 reports/phase_s0_hit60/manual_review/）及任何金标、题面、封存逐题 run 内容；本轮评审仅限规则级判据文本。
- 不修改任何文件，直接输出评审回应文本。
- 请求原文自包含（规则级表述+合成夹具，无金标）；你的结论基于请求文本与你实际读到的代码。注意：R8 起 G01 采用安全隔离口径（不含 evaluation/金标），交付书里的 G01 数字是安全隔离工程回归数字，不是原环境全量数字。

--- 评审请求全文如下 ---
# mimo 化学评审请求:pollutant_pathway_v1 化学判据(S0–S2 回修版 v8)

- 日期:2026-10-07(R8 回修版;替换同日 v7 请求)
- 触发点:AGENTS.md mimo 三触发点之 1(需评判化学结构时——冻结或发布前)
- 评审对象:S0–S2 第八轮回修后的化学判据草案 v8(实现于
  `src/pathway_v43/pollutant/`,ppv1-*-8 版本族);**尚未冻结**
- 与 v7 的差异来源:第七轮 mimo 回应
  (`docs/mimo_ppv1_chem_review_response_r7.md`,条件 C1–C6)+
  Codex R7 复审(`POLLUTANT_PATHWAY_S0_S2_CODEX_REVIEW_R7_2026-10-07.md`
  两项 P1[R7-01/R7-02]与 §5 采信边界)。Codex R7 采纳 mimo C1 的
  窄判断(canonical 加 r 三例 retain)但确认**raw 恢复/直传路径**
  全 verified/R6(同契约残余);本轮修复:恢复(from_dict)与
  audit 直接 states 首次消费共用与公共 writer 同源的纯状态验证
  (R7-01);存储侧 supplied SID 的既存同 hash 出现行首提即校验
  (R7-02,程序事实,mimo 不审,仅披露)。mimo C4/C5/C6 的落字
  建议一并整理进判据文本(full 两根据/许可 scope 披露口径/拒绝
  ⇒ 无 disposition 与失败早退边界)。
- 自包含性:规则级表述与合成规则级夹具,无任何金标/题面/封存
  逐题数据;由用户转交,回复原文落盘 `docs/`

## 0. 背景(一段话)

v7 判据经第七轮独立复审确认 R6 五组原反例已翻转、三项关闭,
但同一既有契约内仍有两个消费入口缺口:① 状态恢复/直接对象
未验原始结构 —— 正常乙醇氧化证明不动,只改序列化状态的
`structure_smiles_raw`(如 `CCO |r|`、H2 挂 `CC=O`),
`ChemicalState.from_dict` 接受、恢复对象经 audit→admission 全
verified/full/R6(H2 raw 换成跨分子串同样 R6);② 显式重给
有效状态时首提复用损坏 appearance —— 先 public put 合法数据、
仅在合成 SQLite 改 appearance.source_refs 不改 hash,
states=[] 首提已拒(R6-04 修复保持),但重新提供有效 prod-only
或全量 states 仍 created=True 并写 event/projection/plan/links,
重放才报损坏。两处已回修并有行为级红绿回归(R8 新增回归 28 例
在基线 858dd94 红 14/绿 14,全部 14 红为复审反例行为翻转、
14 绿为正控制;ppv1 全量 536 passed/0 skip;G01 按安全隔离口径
——不含 evaluation/金标/题面,数字见 §6)。本轮请评审**回修后
的判据文本 v8**。目标不变:可能降解路径与条件相容路径的诚实
表示;unknown 不升格;verified 不靠模型或调用方自报字符串;
**账平、物种同 CN 或一份正确局部诊断不能代替整条声明的覆盖与
追溯;数值配平不等于未覆盖参与物初始图的结构贡献已核实;
对象内部可确定的身份/原始表示不一致不得授 verified/full**。

## 1. 判据一:分子身份(v8 文本)

1–4 同 v7(state_id 生成条件/化学 CX 事实子集/混合并列 ABS
归一/公开表示往返闭合/fidelity 分轴)。v7 的第 2 条(输入侧
注册感知校验,按真实 CX 类边界逐项词法、登记内容含空格放行、
DAT 剥离适配器前提)**原样保留**;v8 新增第 2b 条(恢复/直接
对象入口):

2b. **规范身份串在首次消费时同受约束(R7-01/v8 新增)**:
   - v7 缺陷:`ChemicalState.from_dict` 只校版本与 fidelity 枚举,
     不对载荷跑输入守卫或规范重推导;`audit_hypothesis(states=…)`
     直接消费调用方给的 dataclass 对象,也不重推导 —— 篡改
     `structure_smiles_raw`(state_id/规范串/四轴 as_written 全
     保留)后恢复/直传对象可达 verified/full/R6;
   - v8 规则:**恢复入口与 audit 直接对象入口在首次授信前共用与
     公共 writer(store put/submit 重推导)同源的纯状态验证**
     (chemstate.validate_state_object):
     (i) 版本门 + fidelity 分轴契约 + structure_origin 合法;
     (ii) 结构态:structure_smiles_raw 非空且**过判据一第 2 条的
     同一输入守卫**(未登记项 ⇒ 拒 —— 不静默清洗信息再授 full);
     (iii) raw 重推严格身份 == smiles_isomeric(同图异拼写如
     OCC 接受;跨分子如 H2 状态挂 CC=O、表示层身份声明不一致 ⇒
     拒);(iv) smiles_isomeric 须为身份键规范形,且 state_id/
     formal_charge/cn_identity/立体/同位素状态按工厂同源重推导
     一致;(v) CN-only 态走专用命名空间身份 + 未知事实契约
     (不重推导结构);
   - 违约 ⇒ 结构化拒绝(ChemicalStateError,机器码分列),或诚实
     身份 unknown;**不得 R6**;拒绝不清洗不覆盖原始信息;
   - **不认证来源真伪、历史执行或机制**—— 只核对象内部可确定
     的一致性(调用方如何拿到该对象不在判定范围);
   - 正控保持:clean 往返、raw `OCC` vs canonical `CCO` 同图异
     拼写、登记 atomProp 含空格、指定手性正常链、CN-only 诚实
     unknown、存档 fidelity 边界(absent_in_archive 轴如实声明,
     不升级不清洗)。

**请评审**:(a) 第 2b 条"恢复/直传首消费同源验证"的判定范围
(raw 登记守卫、raw→strict 身份一致、规范身份与结构事实重推导、
CN-only 契约)是否闭合 v7 缺陷且不含越权认证;(b) 全部原始 CX
入口清单(v8 后)——工厂 build、strict_identity_of、判据五四
原始字段、**from_dict 恢复与 audit 直接 states**(新增)共用同一
守卫,是否还有本仓未覆盖的产生身份/verified 的公共入口;不产生
身份或 verified 证据的诊断入口(池输入 preview 的 conservation
诊断、冻结执行器与外围服务的内部解析)按 C2 划界在守卫范围外,
其结果不得以任何方式回流为身份或核实证据(preview 保持
pool_unchanged/diagnostic_only)——该划界表述是否准确;
(c) DAT 剥离前提与含空格放行边界同 v7,不需重评;(d) **拒绝不
反推输入真实化学含义**:原始 `r` 标记的存在与含义均不被采纳也
不被反驳,拒绝事实不得用于推断实验消旋/样品纯度。

## 2. 判据二:参与物计量与元素/电荷核算(v8 文本)

1–8 同 v7(全氢账/系数契约/完整性 unknown/电荷轴前提/结构化
omission_pattern_matches/H+_count1 命名;R5d 触发集合限定
{元素,电荷};恒等≠落点口径句)。v8 无变化(v8 的状态验证使
formal_charge/stereo/isotope 自报值与结构重推导同源,元素/电荷
轴的前提不再可被直传对象伪造,判据本身不动)。

**请评审**:确认已同意条款不需重评。

## 3. 判据三:admission 决策表与中心证据契约(v8 文本;有序,首中即决)

R1/R1b/R2/R2p(on/off 披露)/R2b/R3/R4/R5d{元素,电荷}/R5v/
R5c/R5/R6/R7 行语义同 v7;类型契约/内部重算/无 proof_record ⇒
unknown/复算比对含 center_match_basis/strict 轴/input_hash 域/
audit.scope/proof_scope+basis 披露同 v7;注册补全规则及其许可
边界(composition_only_hydrogen_equivalents,按严格结构身份登记
H2/[H])同 v7。v8 落字两处(mimo C4/C5 口径整理,语义无变化):

- 4) 绑定核验补 **"覆盖 full 的两个互不替代根据"**(原文落字):
  **① 无未覆盖参与物;② 注册补全规则数值精确相等且未覆盖参与物
  身份全部在登记许可内。二者都只解除覆盖轴—— 补全(无论是否持
  许可)只证明组成闭合,不证明转化身份、机理或共底物初始图的
  键变化已核实;身份归 strict 轴、元素/电荷归判据二、转化核实
  归证据门。**
- 许可 scope 的披露口径(mimo C5):completion_license/
  completion_license_scope 现进 center detail 机器披露(满足 R6
  原门);**凡结论为 full/expand 且依据含许可补全,任何渲染必须
  与作用域文本同屏**——顶层/同屏展示列与 license_applied 标志
  为后续 API/展示层事项(P2,不作为本轮门);scope 文本声明
  "本许可不区分该参与物的键断裂方式与电子去向"。

**请评审**:(a) "full 两根据"句是否如实反映实现语义(两根据
只解除覆盖轴,不外溢到转化/机理核实);(b) scope 随结论外传的
口径(机器披露已落、同屏渲染列后续)是否可接受;(c) 补全许可
scope/严格身份登记/未登记 partial 语义同 v7,不需重评。

## 4. 判据四:条件相容聚合(v8 文本)

同 v7(快照一致性/签名↔评估行双向对应/派生先验父对象/内容
身份/三分/单向矛盾/孤儿 unknown)。v8 补一句契约前提(mimo r7
判据四建议 1,非阻塞):

- 10(a′) 前提:**行↔签名对应以"要求对象评估后不可变"为契约
  前提**——绑定字段一经冻结不得后改;变更须走新评估/新快照
  (将来若引入要求可变性,旧快照会整体拒绝,是有意 fail-closed,
  不当 bug 修)。

**请评审**:确认该前提句与既有实现一致,其余条款不需重评。

## 5. 判据五:供体一致性诊断(v8 文本)

1–3、5–7 同 v7(实际净变化判定基础/奇偶构型比较与非四面体
unsupported/联合映射三类支持范围/中心属性披露/strict 同源/
证据载荷内嵌);4(声明–执行净效应对账 + 镜像终态归一)同 v7;
8(四个原始字符串入口与工厂/strict 同源守卫)同 v7。v8 落字
拒绝与早退口径(mimo C6):

- 8b. **拒绝为契约性拒绝 ⇒ 本次诊断/审核不产生任何轴结论与
  disposition**(原文落字):未登记 CX 项的拒绝是输入契约违约,
  不是化学未知;调用方不得吞异常后按 retain/verified/any-R 行
  记录(异常≠处置行)。`execution_ok=False` 的早退路径不解析
  四字段亦不消费其任何轴(全轴 None/execution_failed),为已知
  安全边界;审计复算链对 proof_record 内含未登记项同样拒绝,
  复算拒绝同样不产生 disposition。
- 8c. **两处表述边界(原文落字)**:拒绝原始 `r` 标记不构成
  "已证实实验精确消旋";裸指定 SMILES(无来源记录)只声明表示
  事实,不称实验纯品/对映纯;strict=True = 同一化学身份,
  不是同一样品/同一立体纯度。

**请评审**:(a) 拒绝⇒无 disposition 与失败早退边界的口径是否
与实现一致;(b) 两处表述边界与 strict 语义提醒是否足够防
下游误读;(c) 四入口守卫/镜像终态条款同 v7,不需重评。

## 6. 程序证据与状态(程序事实,不替代化学判断)

- 规则级测试:ppv1 全量 **536 passed/0 skip**(508 v7 存量 +
  28 新增 R8 回归,全部合成夹具);新增回归在基线 858dd94
  **红 14/28**——12 红为 R7-01 反例行为翻转(from_dict 恢复 6、
  audit 直接对象 3、指定手性 1、恢复+绕路组合 2)、2 红为
  R7-02 反例翻转(prod-only/全量重给有效 payload 首提
  created=True → 首提即 Ppv1LedgerCorrupt 零写入);14 绿全部
  为正控制(clean/同图异拼写/含空格 atomProp/指定手性正常链/
  CN-only/存档 fidelity/合法 none/partial/all 先存/全新库首提/
  states=[] 拒绝保持/带载荷重放共享规则/语义冲突零写入保持);
- R7 复审探针在 v8 隔离复跑(脚本复制到新临时目录):C1_raw_*
  (substrate/product/H2/different_molecule/chiral)全部由 ok/R6
  翻转为结构化拒绝;clean/same_graph_spelling/registered_
  metadata/chiral_clean/CN-only 控制保持;存储 15 案中
  first_existing_appearance_{prod_only,all}_corrupt 首提翻转为
  LedgerCorrupt 零写入,none_corrupt/multi_occurrence/valid 全部
  保持;R7 观察断言(storage_assert_observed.py)按设计在翻转点
  失败(它钉住 R7 缺口,非修后期望);
- 存储两项(R7-02,mimo 不审,仅披露):首提对 supplied SID 的
  既存同 (SID,hash) 出现行在收集阶段(_collect_state_writes,
  首提/重放共用)立即复算内容 hash,损坏 ⇒ Ppv1LedgerCorrupt、
  零新增,不延后不自动覆盖修库;不按 supplied/unsupplied 两套
  规则授信;已正确零写入拒绝的 state 语义冲突保持;
- G01:按 R7 复审 §2 新口径**安全隔离工程回归**(不含
  evaluation/金标/题面/封存,路径白名单 + 普通dependingv3源码 +
  本仓非题面反应资产,逐项报告实际 passed/skipped/deselected 及
  缺席依赖;具体数字见 R8 交付书 §5 与证据目录——不是完整
  1119/16 的原环境数字,不外推科学性能);legacy 冻结
  AtomTool/存储未改;
- 判据未冻结;v8 语义变更(状态恢复/直传首消费验证/首提 supplied
  出现复用校验)全部**待审**;契约族升 ppv1-*-8(未发布
  profile,无历史产物迁移;旧 -7 载荷按未知版本既有门拒绝);
- 参考(外部常识,非本仓资产):RDKit Book(CXSMILES 扩展/
  增强立体/立体化学章节/非四面体立体支持说明)、rdCIPLabeler
  API;CXSMILES 解析器行为经 Release_2026_03_6 源码取证
  (parseCXExtensions 主分派循环)与实证用例校准;**冻结前须以
  执行证据复核 RDKit(锁定版本)词法取证与放行正控的往返无损**
  (放行的每个保留类含空格/含分隔符输入,往返后其保留类事实无
  静默丢弃;移除类放行项以结构串往返同 id 为控)。

## 7. 请求的回复格式

对每条判据:1) 结论(同意/不同意/有条件同意+条件);2) 可直接
落进规则文字的修改建议;3) "程序上诚实但化学上误导"风险点。
逐条表态,不接受总体评价式回复。
