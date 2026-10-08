# pollutant_pathway_v1 判据冻结记录（ppv1-criteria-v1，2026-10-08）

- **冻结对象**：`docs/POLLUTANT_PATHWAY_CRITERIA_FROZEN_V1_2026-10-08.md`
  （判据一～五 + 0d/0e 生产/恢复/调度消费契约，版本号
  **ppv1-criteria-v1**）。
- **冻结权威**：用户（Gong）2026-10-08 拍板"冻结"化学判据。冻结
  权归用户/teacher；本记录与冻结稿是执行该拍板的文案同步产物，
  不含新的化学判断。
- **冻结依据**（四件，全部既有）：
  1. Codex S3b-r3 终审报告
     `docs/POLLUTANT_PATHWAY_S3B_CODEX_REVIEW_R3_2026-10-08.md`：
     S3 工程完成、P1=[]、S3B-01 关闭；§6 给出七项改字+判据五两句
     的冻结前同步清单；§6 末段"若不改变已审正文语义则无需新增
     化学评审轮次；若改字实际改变判据正文/范围/硬门，应按仓库
     已有化学评审与版本规范另评"；§7.1 交接顺序第一条（冻结稿
     纯文案同步）。
  2. mimo v15 化学评审回应
     `docs/mimo_ppv1_chem_review_response_r15.md` §十二："在第 1、2、
     3、4 项改字并完成'待执行验证'清单之前，不建议冻结；**改字后
     无需新增化学评审轮次，除非更正过程中触碰判据一–五正文**"。
     其七项更正清单与待执行五类清单全部落实（见 §3、§7）。
  3. mimo v15 请求正文
     `docs/mimo_ppv1_chem_review_request.md`（v15，冻结稿底本；
     原文不回写，留作历史）。
  4. 用户 2026-10-08 冻结拍板（本记录的触发指令）。
- **冻结时锚定**：实际 HEAD
  `adf0287abef0c4803962fee0df0065d8e6f3793d`（本冻结批次
  `git rev-parse` 复核，与 R3 终审报告所记一致）。

---

## 1. 冻结版本与契约族关系

- 判据冻结版本：**ppv1-criteria-v1**（判据族首个冻结版本号，沿用
  ppv1 前缀命名规范）。
- 覆盖的实现契约族登记面（冻结时点，均经 R3 复核）：ppv1-search-6、
  ppv1-store-9、ppv1-profile-14、ppv1-search-limits-3、
  ppv1-format-feedback-1、ppv1-model-proposals-2、ppv1-runflow-3、
  ppv1-frozen-plan-1。
- 底本版本链：v8（S0–S2 判据，R8 复审放行）→ v12 判据正文定型 →
  v14（S3b 消费契约）→ v15（S3b-r3 后段锚定+精度更正，mimo 逐条
  同意/有条件同意）→ **ppv1-criteria-v1（本冻结稿）**。冻结稿相对
  v15 的全部差异即 §3 判定表所列改字项；除该表所列外正文逐字
  沿用 v15（"请评审"段按文档性质移除，见 §3 第 20 项）。

## 2. 冻结范围与不覆盖

- **冻结的是**：判据一～五的化学判定口径（门、枚举、处置规则、
  理由码语义）与 0d/0e 消费契约文字；proof_scope/术语口径（§6）；
  采信与证据分级表述（冻结稿 §8）。
- **冻结的不是**：科学性能（pending，S4/S5 另行验收）；endpoint
  评估（属 S4）；dev/298 两题域的任何外推；工程实现的行号细节
  （行号是锚定指针，非判据内容，源码变更须重锚但不自动构成判据
  变更——重锚后若行为语义与冻结判据不符，则属实现违约或触发
  判据升版本，二者必居其一，由 mimo 触发点流程裁定）。
- **自包含与红线**：冻结稿与冻结记录均为规则级表述，无金标/题面/
  封存 run 数据；含金标往来不入仓（本两文件均不含）。

## 3. 逐项语义判定表（语义守卫，本记录核心）

判定口径：**仅文案** = 不改判据正文的判定规则、适用范围、门
（硬门/软门）、枚举值或处置强度；**风险** = 触及上述任一者（须另
走化学评审，冻结不成立）。下表每项均给出 v15 原表述 → 冻结稿表
述的差异要点与"语义不变"的依据。

| # | 改字项（出处） | 差异要点 | 语义判定 | 依据 |
|---|---|---|---|---|
| 1 | ① substrate_profile 生产 caller（R3 §6 行 1；mimo v15 §三(a)1 必须更正 1） | "无生产 caller" → "S0–S2 时点无；S3b 起由驱动在决定层只读调用并写持久 artifact（runflow.py:809/812-814）" | **仅文案** | 化学边界三要素逐字保留：输出不构成身份/核实证据、前置验证仍 P2、不重开 S0–S2 门。变化仅是工程事实状态描述（S0–S2 时点 → S3b 起接生产），消除与 0e.5"空池仍组装底物档案"的自相矛盾；R3 §6 行 1 明示"不让其证明结构或当审核证书"。本冻结批次已核 runflow.py:809 调用、:812-814 写 artifact |
| 2 | ② 决策表 R3 行 action=blocked（R3 §6 行 2；mimo §三(a)1 必须更正 2） | "action=blocked" → "动作结算为 admission_deferred、假设留痕；与 0e.6 持久 blocked 行不是同一状态（deferred 可激活、blocked 不可执行）" | **仅文案** | R3 行触发条件（有来源 essential 条件与当前场景已知事实冲突）与处置（defer、不称化学不可能）逐字不变；被更正的是对实现的误述——本冻结批次已核 runflow.py:1122-1133 结算 OUTCOME_KIND_ADMISSION_DEFERRED + put_hypothesis 留痕，blocked 写点仅 search.py:1145/:1213。更正后与 0d.5/0e.6 的 deferred/blocked 分写一致，消除"场景冲突=不可逆阻断"的误导（mimo 定性为程序诚实但化学误导的原句被替换，不是新增门） |
| 3 | ③a 窄捕获行号（R3 §6 行 4；mimo §六 0d.2） | 955-972（r2 标签）→ 1091-1102（r3），旧号标为历史勿按其取证 | **仅文案** | 纯代码位置指针更正。本冻结批次已核 runflow.py:1091 except AuditContractError、:1096-1101 落账、:1102 return；窄捕获义务条款（不吞成成功、零事件、失败结算）逐字不变 |
| 4 | ③b "runflow 同区间是 reconcile/drive"（R3 §6 行 3；mimo §六 0d.8/§九 0c-v14.3） | → "runflow 同区间为 _complete_action 尾部/冻结计划锚定段，非分流代码，勿引；reconcile 实为 500-558、drive 629 起" | **仅文案** | 纯行号/指认更正。已核 _complete_action runflow.py:209、reconcile_followups :500、drive :629、runner.py:218-219/316-317；runner 分流事实（runner.py:214-228/305-320）不变 |
| 5 | ③c 冻结计划段行号拆分（R3 §6 行 3；mimo §十 0c-v15.6） | "211-321" → 持久化/读取 229-272、锚定 274-390、锁段 392 起；0e.1 补锚行扫描跳过/1521 先于 1522 | **仅文案** | 纯行号拆分。已核 _persist_frozen_plan :229、_load_frozen_plan :242、_verify_frozen_plan_binding :274、锁段注释 :392、锚定调用 :1521 先于 recover_run :1522、无 plan_digest 行跳过 :329-330、task_key 重算 :332 起；0e.1 三类拒因分栏与"首消费前、零新增、原资料保全"语义逐字不变 |
| 6 | ④ "恒入 center detail" 语序（R3 §6 行 5；mimo §三(b)2） | → "凡完成覆盖判定的 center detail 必带（full/partial 均携带；早退例外不携带）" | **仅文案** | v15 原句已同时含"full/partial 完成分支携带"与"unknown_coefficients/unverifiable 早退例外不携带"两个限定；改字仅把限定语序前置，防止快速阅读把"恒入"读成所有 detail 恒带。携带范围、早退例外、三条件判定组合逐字保留。已核写入点 audit.py:1009-1013、早退 :889-897 |
| 7 | ⑤ λ_s×Δ 源位置（R3 §6 行 6；mimo §三(c)2） | "973-979 一带" → "973-980（产物侧 973-976、反应物侧 977-980）" | **仅文案** | 行号补全。已核 audit.py:973-980 两个 _completion_violations 调用；λ_s×Δ 对账规则与"和 coefficient_binding_mismatch 分写"不变 |
| 8 | ⑥ 数字/HEAD/字节一致性采信（R3 §6 行 7；mimo §十一/§十二 7） | "待执行验证" → "由 Codex R3 复审独立执行证成"（工程数字、RDKit 往返、父基线红绿、G01、字节一致、探针 15/15、锚定 38 观察）；mimo 原回应保持"待执行验证"原文不改 | **仅文案** | 证据出处标注更正，不改任何判据文本。R3 §6 行 7 明示"新冻结包可标'由本报告/独立日志证成'，不得改原回应成模型已跑"；工程数字不当化学证据声明保留并前置（冻结稿 §0/§8）。判据一～五正文不含工程数字 |
| 9 | ⑦a standalone audit 分轴判定（R3 §6 末段判据五两句之一） | 8b 补写"standalone audit 被调用时可分轴判定"（中心 unknown 与其他轴 verified 不互斥） | **仅文案** | v15 8b v12 落字已含"同一次 audit 仍可以给其他轴 verified 并由决策表处置（不互斥，按首中规则合成）"——补写仅标注其适用上下文（audit 被独立调用的路径），规则本身与决策表首中即决逐字一致，mimo v15 §五(a)1 核到并同意 |
| 10 | ⑦b 固定生产链 execution_ok=False 于 audit 前短路（R3 §6 末段判据五两句之二） | 8b/0d.3 补写"production.py:399-404 工具执行失败短路 → method_failed，零 audit/零 event" | **仅文案** | v15 0d.3 已写"记方法失败（method_failed），不伪装成功工具结果"、0d.2 已写零事件/零提交；补写仅精确短路位置（audit 之前、工具执行失败短路而非 AuditContractError 短路，mimo §九 0c-v14.3 建议注明）。已核 production.py:399-404 return method_failed 先于 :406 audit 调用。化学规则（失败执行无 verified 泄漏、中心不可 verified、事件不得凭它提交）逐字保留 |
| 11 | ⑦c strictFalse→violated 带绑定/覆盖先行分支范围（R3 §6 末段；R3 §5 旧注释行） | 0d.4/判据三补写"该判定在前置绑定/覆盖核验通过后的中心证据分段内成立，不能无条件全称" | **仅文案** | violated 判定本身与 R5v 处置不变（v15 0c-v14.1/0d.4 已落字，mimo 同意）；补写限定与决策表首中即决及判据二"绑定失配 ⇒ 中心 unknown"（v12 落字，mimo 同意）同源一致，防止把 violated 读成覆盖先行 unknown 的全称句。已核 audit.py:1188-1203 violated、:1204-1213 None⇒unknown |
| 12 | known_absent 理由码实名（R3 §6 末段"等"；mimo §二(a)1） | 描述语句 → 附实现真实码：required_entity_known_absent（:732）、required_value_known_absent（:828）、other_value_known_absent_not_determining（:833）、numeric_absence_semantics_undefined（:822） | **仅文案** | 判定规则（同值 conflict/异值 unknown/数值 unknown、不跨值域泛化、不进元素账）逐字保留，仅附机读码实名。已核 path_context.py:732/822/828/833 四码与所述行为一一对应（同值缺席落 conflict 类码、异值落 not_determining 类码、数值落 numeric_absence_semantics_undefined） |
| 13 | novel 来源标签 P2 表述（R3 §5 novel 源标签行；mimo §十 0c-v15.4） | 0e.5 补写"decide 传 source_refs/expand 用默认 synthetic-pool-spec/event appearance 用后者；不宣称逐字一致、不认证现实来源" | **仅文案** | 如实披露，不改变 novel 消费契约任何门（reaction_spec/proposal_context 必带、单一构建源、弃权合法等逐字保留）；R3 §5 明示 state_id/hypID 不受影响、无身份洗坏/错误 verified |
| 14 | 判据五 8d caller 义务闭合状态同步（v15 自身 0d.2 落字 + R3 执行证据） | "S3a/r4 未新增生产 caller、尚未闭合" → "已由 S3b 生产链交付闭合（窄捕获 1091-1102 结算 contract_aborted；R3 真实 caller 坏 proof 互证）" | **仅文案** | caller 义务条款（"让 AuditContractError 逃逸并中止本次 admission 计算/提交，不得吞异常继续"）逐字保留；变化仅是义务履行状态（S3a 时点 → S3b 已闭合），依据是 v15 自身 0d.2 v14 落字（受审且 mimo 同意）+ R3 §2 化学/交接补充行执行互证；"静态无宽捕获不是任意第三方 caller 动态安全证书"与三类逃逸披露保留 |
| 15 | RDKit 往返"待执行验证"→独立执行证成（R3 §6 待执行③；mimo §一(a)1） | 判据一 v12 落字 RDKit 句标注"已由 R3 独立执行证成（本机 2026.03.6 五正控+三别名×两入口负控）；仅证本机该版本" | **仅文案** | 状态标注更正（R3 §6 行 7 同款授权）；登记保留 token 表、三别名拒、不构成样品认证等规则逐字保留；跨版本兼容未认证的边界如实保留 |
| 16 | 判据二系数句实测指向（mimo §二.2 建议①，R3 §6 未列、属"等"类同步） | 补"当前实现下该 kind ⇒ 中心 unknown、最终走 R5；如未来扩表须升版本" | **仅文案** | 原则句"不能固定写成自动 reject/R2b，也不能固定写成 R5"逐字保留；补写是实测行为与原则并钉（mimo 实读核到），不改处置规则 |
| 17 | 判据二 full_known 补写（0c-v13.3 落字并入正文；mimo §八.3 同意） | "未知系数 ⇒ coverage unknown_coefficients" 后补"full_known 不成立时元素账与电荷账同样直接记 unknown；verified 只覆盖调用方声明清单的数值闭合，两侧对称漏写在本轴不可见" | **仅文案** | 0c-v13.3 为 v13/v15 两轮受审并获 mimo 同意的落字（实现在 audit.py:628/641/648/673/679 一带，mimo 实读），并入正文不改判定——unknown 的处置（R5、不授 R6）本就由决策表固定 |
| 18 | 判据一 writer raw 机读码补写（mimo §一(a)2 建议②；0c-v13.2 同源） | 2b 补"writer 侧 raw 失败码 raw_structure_unparseable（store.py:632，不带 reason），与恢复入口 raw_structure_rejected 不同名" | **仅文案** | 机读码实名化，防跨入口串味；两入口外层异常类与 kind 层次（v12 落字、已审）不变。已核 store.py:632 |
| 19 | 判据一 preview 划界升为正文（v15 请评审(b) 自身内容） | 请评审段中的 preview/冻结执行器 C2 划界表述移入判据一第 2 条正文，并如实标"preview 侧守卫调用关系未逐行核到" | **仅文案** | 内容是 v15 请评审段原有边界（其结果不得回流为身份或核实证据），非新增门；未核状态如实登记（§7） |
| 20 | 移除各判据"请评审"段（文档性质变化） | 评审请求段落不再保留于冻结稿 | **仅文案** | "请评审"是向 mimo 提问的请求文字，非判据规则；其承载的边界表述已并入正文（第 19 项等）。判据规则文本零删改 |

**结论：全部 20 项均为"仅文案精度"，无任何一项触及判据一–五正文
的判定规则、范围、枚举或硬门；无任何一项改变 0d/0e 消费契约的门。
依据 R3 §6 末段与 mimo v15 §十二（"改字后无需新增化学评审轮次，
除非更正过程中触碰判据一–五正文"），本冻结声明成立，无需新增化学
评审轮次。**

补强说明（为何可判定"未触碰判据正文"）：① 七项更正中 1、2 两项
替换的是**对实现的误述/过时事实**（mimo 定位为"程序上诚实但化学上
误导"的反例句），替换后与已审的 0d/0e 落字一致，化学边界逐字保留；
② 3、4、5、7 项是纯行号/指认指针；③ 6、15 项是证据出处标注；④
判据五两句（9、10、11）均为上下文/范围澄清，与决策表首中即决、
绑定先行 unknown、失败执行零 verified 泄漏等已审规则同源；⑤ 12、
16、17、18 项是把已受审的机读码/实测指向/0c 落字并入正文；⑥ 决策
表 14 行的触发条件与处置列除 R3 行括注（第 2 项）外逐字未动。

## 4. 采信边界（冻结稿 §8 的依据）

- **mimo 评审独立性不做背书，结论采信到与程序证据互证的程度为止**
  （AGENTS.md 既定口径）。mimo v15 为只读评审（opencode 免费通道，
  ses_ee6f27063ffe4W4kSYyM5xaSZXm5xaSZX 会话，与手机 mimo 应用是否同
  一实例未证实——以通道口径区分）；其读码事实凡被本冻结批次/R3
  复核到的均已成锚（§9），未核到的保持"未确认/读码未覆盖"标注
  （§7）。
- **模型声明与独立执行分开**：mimo 回应中一切执行类声明保持"待执行
  验证"原文、不回写、不援引为已验证事实；工程数字/红绿/HEAD/字节
  一致性全部以 Codex R3 复审的独立执行回执为准（R3 §2/§6 待执行五
  类闭合）。
- **工程数字不当化学证据**：879/1481/15/15/38 观察等全部为合成规则
  级契约结果，不外推 dev（B1 环境路径中间步骤）或 298（RHEA 通用
  酶学），不当冻结科学正确性的证明（见 §5）。

## 5. 工程完成与冻结状态分开声明

- **S3 工程完成**（R3 终审，2026-10-08）：S3a+S3b 全部 P1 关闭，
  879 passed/0 skip、G01 1481/8/17、父基线 5 行为红+3 正控绿、
  探针 15/15、production/legacy 与父逐字节一致。这是**工程事实**。
- **判据冻结**（本记录，2026-10-08）：判据**文本/口径/门的版本
  冻结**——判据正文与实现的互证达到 R3 复审与 mimo v15 的采信线，
  文本按 §3 全仅文案同步后定格为 ppv1-criteria-v1。这是**文本状态
  事实**。
- 两者**互不蕴含**：工程完成不当科学证据（合成规则级契约绿数不证
  明化学正确性）；判据冻结不宣布污染物路径科学性能通过、不宣布
  S4/S5 已实施、不外推 dev/298。科学性能保持 pending，留 S4（工程
  评测接口）与 S5（数据/科学验收规格）按各自任务书验收。
- 冻结不改变：停止不是化学终点；unknown 不升格；真实 provider 默认
  off；判分/评测零 LLM。

## 6. proof_scope 与术语表（冻结口径）

**proof_scope**：判据五供体一致性诊断输出的中心属性（参与物/键/
电荷/立体）按 proof_scope **分轴披露**的口径；判据三 audit 侧
audit.scope/proof_scope+basis 同为分轴披露。proof_scope 描述**证据
覆盖范围**，不描述证据强度——scope 内的轴仍按各自检查状态
（verified/violated/unknown）报告，scope 外的轴不产生结论（不冒充
核实也不静默拒）。字段存在 ≠ 适用（判据三 v12 落字 ④ 同款口径）。

**术语表**（口径以冻结稿正文为准，此处为速查索引；每条均取自冻结
稿原文，无新增定义）：

| 术语 | 冻结口径（出处） |
|---|---|
| state_id / 身份键 | 化学 CX 事实子集的规范化 canonical CXSMILES 稳定哈希（判据一 1） |
| appearance | 原始串+来源+分轴 representation_fidelity 的出现记录；语义块只存严格分子事实（判据一 4） |
| 首消费守卫 | 恢复/直接对象/工厂/writer 首次授信前的同源验证；绕过属违约（判据一 2b） |
| unknown / partial / violated | 检查三态+违例态；unknown 不自动 reject、不升格；violated 强于 unknown（决策表 R5/R5v/R5d；判据二） |
| verified | 仅由内部重算产生、不采信自报签名/字符串；R6 需全部必需适用检查覆盖且 verified（判据三） |
| 首中即决 | 决策表评估顺序固定，第一个命中行决定处置（判据三） |
| R1–R7 | admission 决策表行（判据三） |
| coverage 枚举 | product_coverage ∈ {full, partial_unchecked_transformation, unknown_coefficients}；无"裸 partial"中心结论（判据三） |
| completion_license / scope | composition_only_hydrogen_equivalents 补全许可；完成覆盖判定的 detail 必带，早退不携带；存在≠已适用（判据三） |
| license 三条件 | product_coverage=full + uncovered 两 refs 非空 + unlicensed 为空（判据三） |
| λ_s×Δ 对账 | completion_surplus/deficit 的未覆盖参与物元素和差额核算；与系数绑定核验分写（判据二/三） |
| admission_deferred | R3/R4 defer 的动作结算 kind（假设留痕、可激活）；≠ 持久 blocked 行（决策表 R3；0e.6） |
| deferred / blocked | deferred=可激活（activate_deferred）；blocked=不可执行（claim/激活均拒）；对外分开展示（0d.5/0e.2/0e.6） |
| 冲突（conflict） | 给定事实集相容性结论，单向矛盾（只阻当前场景，不反推全局），不认证事实真实性（判据四） |
| known_absent | 条件评估轴缺席语义：同值 conflict/异值 unknown/数值 unknown，不进元素账（判据二/四） |
| 旁证 | legacy_cn_match、图等价等；仅旁证、不叠加升格、不构成反应身份判定（判据五） |
| proof_record | 内嵌审核证据载荷、不可变、入口身份复算；改前提不换 ID ⇒ 拒（判据三/五） |
| 冻结计划 / 锚定 | run-plan/frozen_plan artifact（plan_digest 绑定）与 start 落账根 retrieve 行的独立权威核对；三类拒因分栏（0e.1） |
| method_failed | 工具执行失败短路（production.py:399-404，audit 之前），零 audit/零 event；≠ 契约异常（0d.3） |
| contract_aborted | AuditContractError 窄捕获的失败结算 kind（runflow.py:1091-1102）（0d.2） |
| standalone audit | audit_hypothesis 被独立调用（非固定生产链短路路径），可分轴判定（判据五 8b） |

## 7. 未核事项清单（冻结不关闭、如实登记）

### 7.1 mimo v15 待执行验证五类 —— 状态：已由 R3 复审独立执行闭合

| mimo 待执行项 | R3 独立执行闭合情况（R3 §2/§6） |
|---|---|
| ① PPV1 全量与 r3 新 8 项、父 2bedfc0 红绿分类复跑 | 当前全量 879 passed/0 skipped/0 failed（新 8 在全量内）；父同字节新 r3 八项 5 行为红+3 正控绿、0 collection/版本/字段红（R3 fresh tmp 专项） |
| ② G01 全量 | 1481 passed/8 skipped/17 deselected，exit 0；288 白名单输入 SHA 前后一致（缺席依赖逐项披露） |
| ③ RDKit 2026.03.6 词法与往返正控（五正控+三别名负控） | 本机 RDKit2026.03.6 五正控+三别名×工厂/strict 两入口六负控已执行；仅证本机该版本 |
| ④ production.py git diff 与 legacy 聚合哈希 | production.py 当前/父 SHA 同 3b1a66ea…；12 共享核心同父；52 份 legacy 同字节，聚合 18007e6a… |
| ⑤ novel source_refs 两侧行号读码补证 | R3 §6 末段：已补读并与实际 appearance 互证（0c-v15.4 表述据此采信） |

注意：以上五类为**工程/取证闭合**，数字本身不当化学证据（§5）；
mimo 原回应中相应"待执行验证"字样保持原文不改。

### 7.2 R3 §5 P2/许可范围条目（逐条登记，冻结不关闭、不自动扩成
下一阶段前置门）

1. **plan_version header 未解释**：loader 只取 plan，未解释未知/缺
   header——不宣称已拒未知/缺 header，不认证未来 schema；列
   metadata 规范/校验 P2；正式 schema 演进前明确该字段约束或补
   校验。
2. **协同改写/第二核**：DB 锚与文件 artifact 为不同通道、同一 run
   存储环境，不抗同时一致改写全部权威；无密码学真实性服务；入口
   正常核过后执行层第二核是纵深防御，未认证运行期外部 SQL 全部
   窗口。
3. **锁/预算夹具**：同机 flock，不认证分布式/external
   exactly-once；锁文本仅披露（持锁方可重写，"零变化"指十五业务
   表与被改输入保全，不指全目录无写）；三产物 probe 总预算 30
   （原 20）给余量，不说完整输入字节同原。
4. **novel 源标签**：decide model source_refs、expand 默认
   synthetic-pool-spec、event appearance 用后者；不认证现实来源/
   逐字一致；冻结前同步文字/来源一致性设计仍 P2（冻结稿已同步
   文字，一致性设计未做）。
5. **旧注释/异常包装**：audit.py:2980-2981 docstring 仍写"strict
   False ⇒ 至少 unknown"、:1528-1529/:1757 仍写"(blocked)"——与
   现行实现（violated/R5v；admission_deferred）不一致，**列源码
   文本同步 P2（不改行为；冻结稿表述为准）**；三个 RuntimeError
   可原样逃逸，不能把 Audit 失败结算外推所有异常；unused 旧
   appearance 未认证。
6. **既定底座 P2**：cache_hit 同构、两事务间外部 SQL 窗口、
   foreign-run 反向诊断、保守 defer、scripted 请求登记生命周期
   及 stop 对象列有界 100 保留；不要求全库扫描/机制或 provider
   新门。
7. **科学/收费/真实资料**：合成规则池不认证检索质量；工程
   pending 边界不外推 dev/298；真实 provider 默认 off；科学性能
   pending；判分零 LLM。
8. **（另登）证据 HEAD 采集时序**：r2 实施时点 HEAD=c1211183+
   脏树，最终受审 2bedfc0；r3 实施时点 2bedfc0+脏树，最终受审
   adf0287（R3 §5/§6 末段更正 mimo §十.1 把 R2 历史 20 的父误写
   为 2bedfc0——历史 R2 正确父为 c1211183）；不得把实施时点
   HEAD 说成受审 HEAD。

### 7.3 其他登记（冻结批次如实披露）

- **preview 侧守卫调用关系未逐行核到**（mimo v15 §一(b) 未确认；
   冻结稿判据一第 2 条已标"读码未覆盖"）——preview 划界规则
   （pool_unchanged/diagnostic_only、结果不回流）依 v15 原文冻结，
   行级证据未补。
- **RDKit 跨版本兼容未认证**：全部 RDKit 取证锁定本机 2026.03.6；
   升级 RDKit 须重跑词法/往返正负控并重锚。
- **静态无宽捕获不是任意第三方 caller 的动态安全证书**（判据五
   8d 边界保持；通用动态闭合未认证）。
- **0e.1 锚定的范围外事项保持**：不做密码学签名、不抗全库协同
   改写（R3 §5 行 2 同款）；retrieve/decide 第二层核验为纵深
   防御。
- **判分/评测零 LLM、真实金标/题面/封存 run 零访问**：冻结批次
   与冻结稿均遵守（本记录无任何金标产物）。

## 8. 冻结后变更要求（mimo 三触发点与版本规范）

- **判据正文改动 = 升版本**：ppv1-criteria-v1 任何对判据一～五/
  0d/0e 的改动（含决策表扩行、枚举扩值、理由码语义变化、门增
  删）须出 ppv1-criteria-v2 起，且按 AGENTS.md mimo 三触发点走
  化学评审——触发点 1（需评判化学结构时——冻结或发布前）对任何
  判据语义/范围/硬门的改动强制触发；请求自包含、规则级表述不含
  金标、涉题面/金标外发须用户逐次拍板，由用户送 mimo，回复原文
  落盘 `docs/`。
- **纯文案勘误**（不触语义的错字/行号重锚）可由用户裁定是否豁免
  新评审轮，但须在本冻结记录追加勘误登记，不得静默改冻结稿。
- **实现偏离冻结判据属违约**：后续源码变更导致行为与冻结判据
  不符时，修实现或升判据版本（走评审），二者必居其一；行号重
  锚（行为语义不变）不构成判据变更，但须在冻结记录登记新锚。
- **触发点 2/3 不受本冻结影响**：出题前对考卷的化学抽审（题卷
  冻结前）、出题后对答题结果的化学复核（后置、不改已冻结判定、
  采纳走下一轮预注册）按 AGENTS.md 原样执行；本冻结判据是考卷
  化学抽审（触发点 2）的判据口径底本之一。
- **评审独立性不做背书，采信到程序证据互证为止**；工程数字不当
  化学证据；对外数字带题域标签（dev/298 分开）。

## 9. 冻结包文件清单与本批次行号复核

**冻结包（本批次仅新增以下两份文件，未动其他任何文件）**：
1. `docs/POLLUTANT_PATHWAY_CRITERIA_FROZEN_V1_2026-10-08.md`
   （冻结稿，ppv1-criteria-v1）
2. `docs/POLLUTANT_PATHWAY_CRITERIA_FREEZE_RECORD_V1_2026-10-08.md`
   （本冻结记录）

**关联既有文件（只读引用，不改动）**：
`docs/mimo_ppv1_chem_review_request.md`（v15 底本）、
`docs/mimo_ppv1_chem_review_response_r15.md`（mimo v15 回应）、
`docs/POLLUTANT_PATHWAY_S3B_CODEX_REVIEW_R3_2026-10-08.md`（R3
终审）、`docs/review_evidence/ppv1_s3b_codex_r3_2026-10-08/README.md`
（R3 证据入口）、`AGENTS.md`。

**本冻结批次行号复核清单**（冻结时 HEAD adf0287，只读 grep/sed
实读，冻结稿所引全部行号在此范围内）：

| 锚 | 位置 | 复核 |
|---|---|---|
| build_substrate_profile 调用/写 artifact | runflow.py:809 / :812-814 | 已核 |
| admission_deferred 结算（put_hypothesis 留痕） | runflow.py:1122-1133 | 已核 |
| AuditContractError 窄捕获 | runflow.py:1091-1102 | 已核 |
| 冻结计划持久化/读取/锚定/锁段 | runflow.py:229 / :242 / :274-390 / :392 | 已核（函数级） |
| 锚行 SELECT / 无 plan_digest 跳过 / task_key 重算 | runflow.py:304-309 / :329-330 / :332 起 | 已核 |
| resume 锚定先于 recover | runflow.py:1521 → :1522 | 已核 |
| reconcile_followups / _ensure_transition_followup / drive | runflow.py:500 / :577-615 / :629 | 已核（pending_followup 入队调用内一次写入已核） |
| _complete_action 尾部（runner 分流勿引段） | runflow.py:209-223 | 已核（函数级） |
| runner 分流实调 | runner.py:218-219 / :316-317 | 已核 |
| λ_s×Δ 对账 | audit.py:973-980（产物 973-976/反应物 977-980） | 已核 |
| license/scope 写入 / 早退 | audit.py:1009-1013 / :889-897 | 已核 |
| strict violated / None⇒unknown | audit.py:1188-1203 / :1204-1213 | 已核 |
| decide_admission | audit.py:1643 起 | 已核（函数级） |
| R3 旧"(blocked)"docstring/注释（P2 同步项） | audit.py:1528-1529 / :1757 | 已核（确认仍为过时表述） |
| execution_ok=False 早退三 None | audit.py:2553-2562 | 已核 |
| converter 兼容分支元数据 | audit.py:2983-2993 | 已核（:2980-2981 旧 docstring 一并确认） |
| 工具执行失败短路（audit 前） | production.py:399-404（audit 调用 :406） | 已核 |
| 生产链节点 | production.py:396/:406/:409/:417/:456/:465 | 已核 |
| known_absent 四 reason 码 | path_context.py:732/:822/:828/:833 | 已核 |
| blocked 行写点 | search.py:1078 起 / :1145 / :1213 | 已核 |
| writer raw 码 raw_structure_unparseable | store.py:632 | 已核 |
| verify_event_attachment_content | store.py:1988 | 已核（函数级） |
| CX 立体头正则 | chemstate.py:266 | 已核（`(a\|o\d+\|&\d+\|\^\d+):`） |

未复核即引用的行号：无（冻结稿所引行号全部在上表内；mimo 回应中
未被本表覆盖的行号未引入冻结稿）。

**冻结声明成立**：§3 全部 20 项改字均判定"仅文案精度"，无风险项；
冻结稿 ppv1-criteria-v1 于 2026-10-08 生效。冻结权与后续变更裁定
归用户/teacher。
