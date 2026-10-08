# mimo 化学评审请求:pollutant_pathway_v1 化学判据(S4 回修 r2 版 v19)

- 日期:2026-10-08(S4 回修 r2 批(复审 R2 剩余两组 P1:S4-C02
  必要集合不由文件存在决定/S4-C04 无 ledger 投影首读核父来源
  版本);替换 2026-10-08 v18 请求。v17/v18 送审快照(字节存
  s4b_r1/mimo/、s4_rework_r1/mimo/)与本批 v19 送审快照(存
  s4_rework_r2/mimo/)均不覆盖;旧回应 r5–r18 原样保留不回写)
- 触发点:AGENTS.md mimo 三触发点之 1(需评判化学结构时——冻结或
  发布前);本批为 **S4 复审 R2(Codex 正链)判 C01/C03 关闭、
  C02/C04 残余 P1 后的回修交付判据侧请求**(S4 任务书 §12 +
  复审 R2 §8 回修提示词;S4a 复审已通过,S4b 经确认复核与复审 R2
  不通过、本批只回修剩余两组)
- 评审对象:冻结判据 ppv1-criteria-v1(判据一–五 + 0d/0e 消费契约
  正文**不变**)+ S4a/S4b 的 endpoint/导出/投影消费契约(0f/0g 节;
  v16/v17 已送审,回应 r16/r17 待采信互证)+ r1 回修四组(0h 节;
  回应 r18)+ **本批回修的两组残余消费契约表述**(S4-C02:必要
  集合闭合语义修正 = ppv1-native-export-3/native-export-policy-3;
  S4-C04:无 ledger 父来源版本门 = ppv1-v3-projection-3;endpoint-2/
  endpoint-policy-2/native-result-2 沿 r1 不变;profile-18 为其
  工程登记面,store 保持 -10、runflow 保持 -5;见 0i 节)
- 与 v18 的差异来源:复审 R2 `POLLUTANT_PATHWAY_S4_CODEX_REVIEW_R2_
  2026-10-08.md` §4 两组 P1 公开反例(single_ref_missing /
  unknown_export_schema / unknown_contract_profile /
  unknown_native_result)的最低收口实施。**v19 不修改判据一–五
  与 0d/0e 的任何正文语义**("语义未改变"声明见 0i 节末;限冻结
  范围 = 判据一–五与 0d/0e);新增的是 0i 节(两组回修的规则级
  表述)、0f.1/0f.11/0g.12/0h.6 的 P2 精度同步落字与 §6 数字更新
- 自包含性:本版展开必要规则全文,不以"同 v7/v8"缩写引用历史;
  规则级表述与合成规则级夹具,无任何金标/题面/封存逐题数据;由
  用户转交,回复原文落盘 `docs/`;实施 agent 不调用模型,只读/执行
  类声明一律待执行验证(本批执行声明由主会话安排的 Codex 复审
  另行验证,不以本请求文字替代)

## 0. 背景(一段话)

S0–S2 判据 v8 经 R8 独立复审放行;S3a r4 放行搜索底座;S3b 首批
交付调度/生产链/PPV1 分流;S3b-r2 关闭六组 P1 中的五组后,Codex
S3b-r2 复审**仍未放行完整 S3**,唯一残余 P1 = S3B-01 **后段锚定**
(root retrieve 已 done 的 B3/B4 后段,冻结计划 artifact 被自洽
重封装后仍被消费 —— r2 的绑定只在传入比对侧与 retrieve/decide
执行层到达,后段不可达)。本批(S3b-r3)按复审 R2 §4 最低收口:
resume **首消费前**(任何 recover 补账/事件提交/新调度/预算
consume 之前)把读取的冻结计划与**独立既存权威**核对 —— start
落账的根 retrieve 行(DB 通道 payload.plan_digest;task_key 经
同一 `decision_task_key` 单一来源按行内字段重算比对;artifact
文件内自算的信封 hash/plan_digest 是自洽证书,不能单独证明仍是
原输入)。缺锚/坏锚/摘要不符先结构化拒(frozen_plan_anchor_missing / frozen_plan_anchor_corrupt / frozen_plan_binding_mismatch 三 kind),业务表/event/commit/consume 零新增,原资料保全;正常
同计划、省略 plan、显式同计划、合法原计划转换恢复全保持(复审
两原反例 B3/B4 自洽重封装均翻转拒绝:公开入口真子进程取证 15/15,
十五表逻辑快照零变化)。工程数字:ppv1 全量 **879 passed/0 skip**
(871 r2 存量 + 8 新 r3,32 文件);直接父 2bedfc0 同字节对照(新
r3 文件)**5 行为红 + 3 合法正控绿**(0 collection/版本/字段红,
本批不更新既有测试文件);G01 安全隔离 **1481 passed/8 skipped/
17 deselected**(288 输入)。目标不变:可能降解路径与条件相容
路径的诚实表示;unknown 不升格;verified 不靠模型或调用方自报
字符串;账平、物种同 CN 或一份正确局部诊断不能代替整条声明的
覆盖与追溯。停止不是化学终点;搜索记录/合成图不是终点结论。工程
数字是合成规则级契约结果,不代表 dev(B1 环境路径中间步骤)或
298(RHEA 通用酶学)科学性能。**v15 后判据已冻结
(ppv1-criteria-v1,2026-10-08 用户拍板;冻结稿 =
`docs/POLLUTANT_PATHWAY_CRITERIA_FROZEN_V1_2026-10-08.md`,底本
即本文件 v15)**;Codex S3b-r3 终审通过、S3 工程交接完成。本批
(S4a,S4 任务书首批)交付 **endpoint 分账与原生结果底座**:
公共 start/resume 在驱动结束后把 execution_status /
search_stop_reason / chemical_endpoint_assessment /
bookkeeping_status 四分账独立持久化(stop_reason_records /
endpoint_records 两张派生投影表),终点评估只由独立终点证据
(冻结计划的来源层直报声明)决定,F01 停止非终点/F02 未知依赖
不被 recorded 洗白/F03 重复来源不增独立支持,根碳账只表达核查
范围(账平不当矿化、备选 CO₂ 不相加),并构建确定性原生结果
对象(同事实同 digest;正式文件导出与 v3 有损适配属 S4b 未做)。
工程数字:ppv1 全量 **914 passed/0 skip**(879 存量 + 35 新 S4a,
33 文件);直接父 adf0287 同字节对照(新 S4a 文件)**35 collection
红(模块缺失)+ 更新的 profile 测试 2 版本字面量红 + 21 合法正控
绿**;G01 安全隔离 **1516 passed/8 skipped/17 deselected**
(291 输入)。**S4a 复审已通过(2026-10-08 备用通道 tokeasy
gpt-6-sol 独立复审:P1 清零,建议通过;正链 Codex 裁定权保留,
主会话记录)**。本批(S4b,S4 收尾批)交付 **正式文件导出 +
v3 有损投影 + 完整端到端公共链**:原生结果落为 run 目录
`native_export/<export_digest>/` 文件对(payload.json 全量事实 +
manifest.json 新鲜度锚:graph facts digest/权威引用/策略 hash),
首消费五类结构化拒(missing/corrupt/version/policy/stale/
reference),G02 七测(含独立子进程字节一致与自洽重写不可洗白);
v3 投影为显式 lossy_projection(原生引用 + 十二类信息损失清单 +
不可投影摘要 + 反向消费禁止);legacy/export_v3/AtomTool/G2 冻结
路径经当前树 vs 直接父 fc40605 专项字节对比(四产物逐字节一致,
52 份 legacy code_identity 文件聚合保持 18007e6a…)。工程数字:
ppv1 全量 **932 passed/0 skip**(914 + 18 新 S4b,34 文件);全量
非 slow **1543 passed/16 deselected**;直接父 fc40605 同字节对照
(新 S4b 文件)**18 collection 红(模块缺失)+ 更新的 profile
测试 2 版本字面量红 + 21 合法正控绿**;G01 **1534 passed/
8 skipped/17 deselected**(294 输入)。S5(科学性能评测)未做;
科学性能保持 pending。

## 0b. S3a r4 实现与未实现边界(工程披露;受审表述)

- **r4 闭合的三组残余消费缺口(全部为工程记账行为,不改化学
  判定)**:
  1. **S3A-02 必要预约集合完整性**:`_verify_action_references`
     在既有逐行内容守卫(保留不动)之后,按 claim/`_create_attempt`
     现有创建规则**同源派生**本 action 应有的必要预约集合(总
     action 恒有;scenario_transition 另有 transitions;expand 按
     attempt 引用集有 alternatives/attempts,attempt 行记录
     reopen_of 非空另有 reopens;retrieve 的两条检索预约按"行存在
     ⇒ 必须被引用"核验 —— cache_hit 合法认领不落检索预约行,不强
     加),必要行被删或引用清单缺项**即使剩余清单非空也先结构化
     拒**,覆盖 first complete/B4/B3 事件提交前/B1/defer/done 四口;
     B3 事件提交之前先核,坏链 0 event/commit/consume、artifact
     保全;不猜补缺行;预约 ID 派生抽出单一来源函数与 `_reserve`
     共用(核验与创建同源,不是第二套派生);
  2. **S3A-03 请求状态口接冻结策略守卫**:record_request_sent/
     response/failed 在新 status 写入之前消费**同一**严格冻结块
     校验(`_limits`/validate_frozen_search_limits)—— 存储
     search_limits 为 null/缺 version/坏值 ⇒ 状态口先结构化拒
     (search_policy_block_corrupt)且无成功状态变化,与预算/认领/
     恢复同一守卫来源(不补默认、不依赖 expected policy 或调用方
     预验;合法已登记请求不重新扣额度、失败/悬空占额、scripted
     网络 0 保持);
  3. **S3A-04 非法来源状态不能改记合法 failed**:mark_request_
     failed 正面限定只有 registered/sent 是合法来源(枚举外未知
     来源结构化拒 request_status_unknown 并保全,不静默洗成合法
     终态);register 同键复用对存储状态核枚举(坏行按完整性失败
     拒,不把坏状态当合法幂等 unchanged 返回);recover 对 run 范围
     状态枚举外请求行结构化披露(不改状态、不猜补)。
- **r2/r3 已闭合并经复审 R3 确认保持的项(不重开)**:S3A-01 四类
  异身份输出绑定、S3A-05 停止披露、r3 的行级内容判据(预约单位/
  状态/scope-subject、attempt 状态/hypothesis/task、提交记录归属/
  kind/适用引用、附随投影/计划首提同判据、B3 事件前置、done submit
  真实已完成 event)、r3 的冻结策略读取/恢复/预算/认领严格核验与
  请求身份/引用闭合。
- **并发边界如实披露(复审 R2/R3 §5 裁定保持)**:complete 的只读
  预核验与后续写事务**两个事务之间不持锁**;顺序单消费者/合法公共
  writer 模型内无窗口,但不提供跨并发外部 SQL 改库的保证;defer 对
  未归因已提交事件的保守拒绝同为登记接受边界。跨 run pending 扫描
  作用域、生产 caller/调度属已登记后续边界(S3b)。
- **r4 如实新增披露的边界(不升级为门,留 mimo/Codex 裁定)**:
  retrieve 的 cache_hit 认领不落检索预约行,cache_hit 合法状态与
  "非 cache_hit 认领后把两条检索预约 ref+row 一起删"在存储上同构
  (创建规则的条件参数 cache_hit 不落独立列;本轮不加 schema 列,
  store 保持 -9)—— 检索预约的必要集合按"行存在 ⇒ 必须被引用"
  核验,行不存在按 cache_hit 合法不强制;复审探针未覆盖该形态,
  已在交付书残留清单登记。
- **消费侧权威核验是"写账前的只读复核",其强度与正常 writer 重放
  一致,不是第二套独立化学算法**(同类口径——同源复用,非独立
  双算)。**搜索层的结构权威依公共 writer 重放;verify_event_
  attachment_content 只核附随内容,不单独证明 state 身份**(复审
  R3 §6⑤ 入口划界,判据三 v12 落字)。
- **未实现(S3b,不冒充已交付)**:冻结池/备选/两类 deferred 的调度
  语义与 expected_parent_revision 激活;条件依赖/场景转换实际进入
  调度;模型协议与格式反馈;冻结 AtomTool → donor 诊断 → converter
  → audit → admission → submit 的生产调用链(**S3a/r4 仍未新增
  audit_hypothesis 生产 caller**,判据五 8d 的 caller 义务继续由
  S3b 承担);PPV1 独立 runner 双入口(继续 fail-closed)。
- 搜索层不构造/不修改任何化学对象;停止不是化学终点:停止报告保留
  未探索集合(deferred/blocked/悬空请求/claimed/open attempt),存在
  deferred/知识缺口时不称"所有路线都探索完";chemical endpoint 评估
  属 S4,本批不产出任何终点/矿化/解毒结论。

## 0c. mimo v11 回应八条件采信/纠错清单(受审;v12 重写)

复审 R3 §6 对 mimo v11 回应的裁定如下,**本仓采信限度:读码与
公开运行一致的部分才可作为事实输入;下列更正不得在 v12 回应中
再次照搬**:

1. **⑦ 括注更正(v11 判据一 2b 的表述错误,本版已改)**:v11 所写
   "工厂未登记 CX 类守卫拒绝 vs 真解析失败是不同异常类"的括注
   **不实** —— 同一入口(工厂/恢复)下 canonical+r 与真坏
   canonical 两种内因的外层**同为 ChemicalStateError 的不同
   kind**,按 `detail.reason.kind` 区分(unregistered_cx_class /
   unparseable_smiles);**跨入口**的外层才确不同(restore 入口
   外层 ChemicalStateError、公共 writer 外层 Ppv1StateContract
   Error)。不能把所有外层写成同一类,也不能把同入口内因写成
   不同异常类。
2. **两种潜在扩大(v11 回应若含,不采信)**:(a) 失败 diagnostic
   三个 None/`center_evidence={}` **不等于**下游 audit 所有轴/
   所有 R 行都不存在 —— converter 仍返回版本/来源元数据与
   center_match=None,缺 scope/proof 进 audit 中心 UNKNOWN;同一次
   audit 仍可以给其他轴 verified 并由决策表处置;(b) 同源重放/
   输入守卫**不证明来源真实性、历史执行、酶识别或供体机制**。
   (判据五 8b v12 落字。)
3. **① CX 保留 token(采纳更正)**:登记保留注解头按**真实 CX
   token** 写 —— `a:`(绝对/ABS)、`o<N>:`、`&<N>:`(相对组)、
   `^<N>:`(自由基层)与已登记 Sg 类;**不把 and/or/rad 英文类名
   当输入字面**;RDKit 2026.03.6 实际写出 ABS/AND/OR/自由基并
   保持严格身份往返;以三字面别名(and/or/rad)传入均按
   unregistered_cx_class 拒。接受/拒绝不认证样品。(判据一 v12
   落字。)
4. **② 系数句边界(采纳精化)**:非法表示系数在构造/提交边界拒;
   coefficient_binding_mismatch **属覆盖轴**(partial_unchecked_
   transformation + 中心 unknown,最终依首中规则),**不可虚称
   入口在比对"系数与结构重推导值"**;R2b 还需 caller 映射
   detail。(判据二/判据三 v12 落字。)
5. **③ 恒入/R2b(采纳精化)**:覆盖判定完成 full/partial 分支必带
   license/scope;unknown_coefficients/unverifiable 早退不带;
   R2b 调用方依赖落字,不把缺映射当化学已核;未来 caller 义务留
   S3b。(判据三 v12 落字。)
6. **④ 中心 partial 与四串守卫(采纳)**:删"裸 partial"概念,
   按映射理由码/中心 unknown 表述,与覆盖枚举分开;四个原始字符串
   守卫**限定执行成功路径解析前**;失败早退未解析;None 非通过。
   (判据三/判据五 v12 落字。)
7. **⑤ 入口划界(采纳)**:公共 writer 清单可补;搜索结构权威依
   公共 writer 重放,verify_event_attachment_content 只核附随内容,
   **不单独证明 state 身份**;substrate_profile 无生产 caller,档案
   输出/未来 caller 前置验证划界为 P2,不重开旧 S0–S2 门。(判据三
   v12 落字。)
8. **⑥ known_absent 轴归属(采纳)**:属**条件评估轴**非元素账;
   实体缺席/非物种字符串同值 ⇒ conflict;异值/未列出 ⇒ unknown;
   数值/区间缺席 ⇒ numeric_absence_semantics_undefined 的 unknown;
   不跨值域泛化物种字符串规则。(判据二/判据四 v12 落字。)
9. **⑧ 执行证据互证(保持)**:R3 复审独立验证 697、40/9、
   1299/8/17 与 276 输入;655c7e8 非任一轮父基线,其历史数字不引用
   为证据;读码行号/版本须与实际源码交叉核对,不能拿模型"已读"
   当执行。锁定 RDKit **2026.03.6**(v10 所写 2025.03.1 不采信)。

## 0d. S3b 生产链与调度消费契约(受审表述;新增)

S3b 把 S0–S2/S3a 的判据接进**固定生产调用链与调度**。以下为受审
的规则级文字(全部为消费/调度契约,不是新化学判据):

1. **固定调用链与顺序**:`AtomTool 真实执行输出(render+execute_
   edits)→ check_edit_against_donor(供体诊断,含 proof_record)
   → center_evidence_from_donor_diagnostic(converter,不另手造
   verified 中心结论)→ audit_hypothesis(首消费守卫)→
   decide_admission → build/submit_event(公共 writer)→
   complete_action(搜索记账)`。合成合法编辑必须实际调用冻结
   AtomTool(渲染、映射/编辑执行及现有约束),保存真实执行前后/
   atom_id_map/edits/donor/alignment/expectation/result;对工具已
   确定的产品只能引用(状态身份由结构内容派生),不暗改结构。
   **v14 落字(产品来源精度,复审 §6/0d.1)**:事件产物身份 =
   **冻结池声明的 product_smiles 经内容派生的 state_id**;工具
   真实执行输出是核验轴输入(donor/center 诊断),**不改写产物
   身份**;两者不一致经中心轴落 unknown/violated 按决策表处置
   (声明酸/实际醛时事件仍带声明结构提交、中心不可 verified)。
2. **生产 caller 的异常义务(R8 P2 ⑧ 落字,S3 首个生产 caller)**:
   AuditContractError 不得吞成 verified/R6/成功提交 —— 生产链在
   audit+admission 之后才写事件,契约异常上抛 ⇒ 零事件/零提交/零
   完成;调用方(runflow 驱动)只**窄捕获**以记录方法失败
   (contract_aborted,attempt 落 failed)并调度独立备选,宽捕获
   (except Exception)下同样零写入,无"捕获后成功"路径。
   **v14 落字(闭合范围如实收窄,复审 §6/0d.2)**:已闭合范围 =
   AuditContractError(驱动窄捕获 ⇒ 结构化失败结算:artifact +
   action 以 contract_aborted 结算、attempt failed,事件零提交);
   失败结算与"再调度独立备选"须分开读——**已排队的其余独立条目
   继续执行,deferred 不因本次 aborted 自动激活**(激活仍须显式
   指令/activate_deferred);真实驱动**不存在**宽捕获(宽捕获仅
   负控测试语境);ChemicalStateError/HypothesisContractError/
   ConditionContractError 三类契约异常当前**原样逃逸至 run 进程级
   终止**(零事件写入成立、无 stop report/run_error 披露、action
   保持 claimed)—— 如实登记为已披露边界,不以"AuditContractError
   闭合"外推全部异常都有失败结算。
3. **三个 None 与缺 proof 的语义(与 v12 判据五 8b 一致,现为
   生产链实际行为)**:工具 execution_ok=False ⇒ 诊断三判定字段
   (reaction_center_match/strict_target_match/legacy_cn_match)
   全 None、diagnostic.center_evidence 空字典,converter 仍返回
   版本/来源元数据与 center_match=None(None = 未评估,不是通过);
   记方法失败(method_failed),不伪装成功工具结果。缺证据/映射
   的 None 或空 payload 不是契约异常也不是执行失败:audit 保留
   unknown/partial,admission 按既有 R5 有界探索,不授 verified。
4. **中心证据分段负控语义**(与 v12 判据三一致;v14 措辞精度见
   0c-v14.1):缺/歧义映射 ⇒ 中心 unknown;strict 目标偏离 ⇒
   中心 **violated**(强于 unknown;决策表走 R5v,不弱读成
   unknown 错走 R5;strict None ⇒ unknown);proof 更改(自报字段
   与 proof_record 复算不一致)⇒ AuditContractError 结构化拒;
   跨假设复用 ⇒ 绑定不匹配中心 unknown(注册名+True 不构成核
   实);复杂共底物不能只凭配平升级(completion_license 组成型
   氢当量边界由 audit 既有判据保留,production 不另造许可)。
5. **队列与两类 deferred**:schedule_hypotheses 产 selected/
   deferred/blocked+原因(池 digest/排序/截断可重放;池成员/档位/
   原顺序不被筛选结果改写);备选反应 deferred(alternative_
   reaction_deferred,对象=假设 ID)与共同产物 deferred(
   coproduct_deferred,对象=事件产物 state_ref)**分别有类型、
   对象、触发条件/未展开原因**;激活(activate_deferred)幂等、
   trigger 与冻结记录一致、expected_parent_revision 匹配(旧
   revision ⇒ unchanged stale)、预算不足留独立未展开原因不改
   状态、不重复安排同 action。无新信息不无限重开(持久上限);
   **v14 落字(持久上限来源精度,复审 §6/0d.5)**:"无新信息不
   无限重开"的持久计数来源 = claim 事务内的预约行
   (max_reopens_per_hypothesis 与 max_attempts_per_hypothesis
   双重约束,预约 ID 确定性派生 ⇒ 重放/恢复同 ID 复用不重复扣)
   与 already_expanded/done 幂等键(同身份 done ⇒ 不再安排);
   blocked 计数不是防循环证书。**S3b-r2 起深度阻断对象以 blocked
   行持久化(见 0e.6),blocked 不可执行(claim/激活均拒)**;首选
   下游无候选记 unresolved_continuation(不反证上游;按稳定次序
   继续可用备选);完整事件保存全部已知参与物/产物,报告 K/展开
   宽度或预算不足不删事件事实。
6. **条件依赖与场景转换进调度**:子路径继承父事实/要求/假设/依赖,
   分支互不污染(带自身要求/依赖的假设经 derive_child_context 派生
   专属上下文);环境 essential conflict 阻当前场景展开(假设保留
   留痕,不称化学不可能);共底物循环有启动供应/再生支持不自动
   阻断,缺支持标 unresolved_initial_supply(按显式、版本化策略
   处理,不称化学不可能);场景转换只由用户/来源明确支持
   (source_ref 必需;不从文献观察/矩阵"污水"/工具隐式 O2/H2O/
   transformation_class 标签造当前条件),独立 action/预算/记录,
   仅改变后续阶段(旧边评估冻结于 phase_history,不重写)。
7. **模型假设协议(proposals[])**:每项一条独立反应假设(内部
   共同产物集合与 participants/来源/条件/依赖按既有契约);rank_
   hypotheses 引稳定 ID,**模型选择不升成 recorded**;novel 有界
   proposal_context(reference_hypothesis_ids/output_origin 明示,
   不伪造来源)—— **v14 落字(S3B-05,协议升 model-proposals-2):
   novel 池外提案必须另携带 reaction_spec 完整反应内容(与冻结池
   条目同形状的假设载荷;缺 ⇒ json_field 格式错误可进有界反馈;
   无足够内容不授有效 hypothesis、不伪造内容),并由驱动构造独立
   假设消费(见 0e.5)**;空列表/弃权合法(脚本响应耗尽 = 合法
   弃权,不猜内容)。**有界格式反馈**(独立策略
   ppv1-format-feedback-1,默认 0 轮、范围 0-4、计数单位=同任务
   JSON 格式修复轮数,**不是 hypothesis 语义 attempt**、非 S2 十
   搜索上限旧字段):只有 JSON 字段/类型/允许 ID/语法契约错误可进
   反馈;结构无法解析记结构失败,不能以格式反馈改分子再试到通过;
   **v14 落字(默认 0 轮实际后果,复审 §6/0d.7):默认 0 轮 =
   可反馈错误首次即结构失败(model_structure_failure,run 如实
   停止);反馈机制仅在配置 1–4 轮时生效;反馈轮的 scripted 重试
   不发网络,真实 provider 的反馈重试属付费路径,默认 off/0 下
   不可达**;chemical_reposal 首版 off(化学重提案数 0/路径
   unsupported 如实披露)。模型不直接写 SQLite/frontier/条件
   事实/策略;真实 provider 默认 off、max_real_model_requests=0,
   传入模型对象不自动启用/补预算;scripted/fake 恒 network 0。
8. **PPV1 独立 runner 分流**:公开 start_run/resume_run 按 profile
   分流到独立执行/存储(**分流代码在 `workflow/runner.py:214-228/
   305-320`——v14 行号更正:mimo v13 回应误写 runflow.py:214-223/
   315-319,runflow 同区间是 reconcile/drive,文件名与行号以此处
   为准**;严格状态/搜索 ledger/事件账;不落 legacy CN/
   PathwayStore/预算派生);resume 验完整身份后经四崩溃恢复
   (B4 补账/B3 消费同一 output/B1 同 worker 幂等续跑/B2 pending
   披露不默发);事件已提交而 followup 未调度的 B4 残余由权威记录
   (事件+展开计划附件)幂等补调度,不重发事件。停止报告按冻结
   优先级取主因,deferred/知识缺口存在时不称"所有路线都探索完"。
   **v14 落字(S3b-r2 增量见 0e 节):冻结计划/池输入内容绑定、
   恢复坏 artifact 隔离、后续/转换集合逐对象补齐、执行会话互斥、
   novel 独立假设消费、blocked 持久披露。**交付 worker 曾以底层
   start_ppv1_run/resume_ppv1_run 驱动四硬杀;复审另以两公开入口
   独立子进程复验四硬杀/新进程恢复/二次幂等恢复/并发控制(r2 起
   公开入口测试覆盖恢复/并发)。

## 0e. S3b 恢复/调度/协议消费契约(受审表述;v14 新增,v15 更新 0e.1)

S3b-r2 按 Codex S3b 复审 §4 六组 P1 的最低回修实施;S3b-r3 按
Codex S3b-r2 复审 §4 收口唯一残余(0e.1 后段锚定)。以下六条全部
是**恢复/调度/协议的消费契约**(契约随 ppv1-search-6 /
ppv1-runflow-3(r3 自 -2 升)/ ppv1-model-proposals-2 登记;
**不是新化学判据**;生产化学链 production.py 两批均零改动):

1. **冻结输入身份(S3B-01;v15 补后段锚定)**:计划(池/模型
   响应/转换意图/激活指令/条件事实)在 start 时持久化为**冻结
   输入来源**(run-plan/frozen_plan artifact,plan_digest 内容
   绑定)。resume 的 retrieve/decide/模型请求/expand/followup/
   转换全部消费该冻结来源:**旧任务不消费新输入**。三类拒因
   分栏(v15 落字):
   - **读取侧**(artifact 完整性/自洽):H07 完整性包装 + 内容
     身份核验 —— 缺/坏/digest 不符 ⇒ frozen_plan_missing/
     frozen_plan_corrupt/frozen_plan_integrity_failure/
     frozen_plan_digest_mismatch(保全原文件,不猜);
   - **传入比对侧**:不传 plan ⇒ 沿冻结输入(**缺输入不变空
     池**,不当 no_local_candidate 合法完成);传入计划内容
     不符 ⇒ frozen_plan_mismatch(差异须显式新 revision/新
     任务登记,不复用旧裁决键);
   - **后段锚定(S3b-r3 新增;v15 受审重点)**:resume **首消费
     前**(任何 recover 补账/事件提交/新调度/预算 consume 之前)
     把读取的冻结计划与**独立既存权威**核对 —— start 落账的根
     retrieve 行(DB 通道 payload.plan_digest;task_key 经同一
     `decision_task_key` 单一来源按行内冻结字段重算比对)。
     **artifact 文件内自算的信封 payload_hash/plan_digest 是
     自洽证书,不能单独证明仍是该 run/root/task 的原输入**;
     覆盖 root retrieve 已 done 的 B3/B4(执行层核验后段不可
     达)。缺锚 ⇒ frozen_plan_anchor_missing;坏锚(锚行载荷
     不可解析/task_key 重算不同源)⇒ frozen_plan_anchor_corrupt;
     锚摘要 ≠ 冻结计划摘要 ⇒ frozen_plan_binding_mismatch ——
     均先结构化拒,业务表/event/commit/consume
     零新增,原资料保全。不做密码学签名、不抗全库协同改写
     (复审明示范围外);正常同计划/省略 plan/显式同计划/合法
     原计划转换恢复全保持。
   第二层(纵深防御):retrieve 任务 plan_digest 与 decide 冻结
   pool_digest 同源重算核验(入口锚定后正常流不可达,保持为
   防 DB 侧输入漂移)。
2. **恢复裁定接执行门(S3B-02)**:recover 已诚实识别的坏
   artifact(hash 不符/不可反序列化)action,在恢复后**明确隔离**
   (claimed → blocked,defer_reason=recovery_failure:<kind>):
   **零猜重算、零坏任务 event/成功 commit/consume**;坏原文件/
   attempt/预约行保全(不释放不猜补);blocked 不可执行
   (claim/激活均拒);其他合法 B1–B4 与明确独立任务继续驱动。
   H08(提交事实与 ledger 不一致)仍为恢复前置结构化失败(整
   resume 拒),不自动补事件/修库。
3. **后续/转换集合完整性(S3B-03)**:B4 恢复的期望后续集合从
   **已核权威**(提交记录 event_id → 事件行参与物产物全集 × 展开
   计划 expanded/deferred/not_tracked + 冻结计划的显式转换意图)
   派生,**逐对象幂等补齐**(0/部分/全部),不以"payload 引用
   计数>1"当完整性证书;转换 action 的 pending_followup(事件/
   产物全集/父路径/上下文/revision/深度)**创建时一次冻结入载
   荷**(消除"先入队后 UPDATE 附加"的两写窗口);转换执行后按
   新上下文调度 followup(只后效,旧边评估冻结);不重发事件、
   不重复扣额;完整共同产物事件不截断。
4. **执行会话互斥(S3B-04)**:公开 start/resume 以 run 目录
   driver.lock 的 flock(LOCK_EX|LOCK_NB)取得**可验证执行权**:
   双进程同时驱动同一 run 只有一方进入恢复/认领/请求/工具执行,
   竞争方在任何执行前结构化拒(driver_session_active;不创建新
   attempt/event、不重复扣额;持有方退出后再次 resume 即幂等复用
   完成结果);崩溃(进程死亡)⇒ OS 自动释放 ⇒ 新进程接管(原
   attempt/预约/claim 行原样保留,B1 同 worker 幂等 reclaim 续
   跑,不永久锁死)。**同机文件锁语义;不宣称分布式锁或外部
   provider exactly-once**。并发验证用两个真实公开 resume 进程 +
   真实工具入口计数(patched 包装调用冻结工具)+ barrier,不以
   最终 event 幂等为唯一断言。
5. **novel 独立假设消费者(S3B-05)**:novel 池外提案(协议
   model-proposals-2)必须携带**完整反应内容**(reaction_spec:
   product_smiles/edits/donor/alignment/expectation 等与冻结池
   条目同形状;缺 ⇒ json_field 格式错误可进有界反馈)与**来源**
   (proposal_context:reference_hypothesis_ids/output_origin 明
   示,不伪造)。驱动经 prepare_hypothesis 单一构建源构造独立
   假设(结构身份/参与物/系数/共同产物/条件/依赖沿既有契约;来
   源入冻结任务输入与产物 source_refs),按预算入队走**固定
   AtomTool→供体诊断→converter→audit→admission→submit** 生产
   链(与池内假设同一链;proposal_context 披露);无足够内容 ⇒
   构造侧结构化拒(run_error 如实停止,不以反馈改分子再试)。
   空池仍**组装底物档案**(独立于候选,持久 artifact)并消费
   模型响应(novel/合法弃权);池内选择/弃权合法,弃权与规则池
   并行;不启 chemical_reposal、不发真实 provider/付费;scripted
   网络 0。
6. **blocked 持久披露(S3B-06)**:调度深度阻断的假设对象以
   search_actions **blocked 行**持久化(status=blocked +
   defer_reason=原因 + 冻结任务输入;幂等不重数;不可执行);
   公开 stop 从持久行**同源派发**:depth_limit 停止原因 + 
   unexplored.blocked_objects 对象清单(action/假设/原因,有界
   100 条),不是只存计数;**主因优先级不动**(user_stop >
   budget_limit > depth_limit > …;零深度+预算复合时主因
   budget_limit 合法、depth_limit 入其他原因);正常运行/恢复
   同源、不丢/不重数;blocked 对象存在 ⇒ 不称 exhausted_search。

## 0f. S4a endpoint 分账与原生结果底座(受审表述;v16 新增)

S4a(S4 任务书首批)把"搜索停止"与"化学终点"正式分账。以下
全部为**消费契约与化学边界声明**(终点/账目/导出侧),不改判据
一–五与 0d/0e 任何正文语义(见本节末"语义未改变"声明)。

1. **四分账(四者独立存在、互不代替)**:
   - `execution_status`(completed/failed/incomplete):执行会话
     本身是否完成(claimed/open 在途 = incomplete;run_error =
     failed)—— 是执行事实,不是停止原因、不是终点、不是账目;
   - `search_stop_reason`(六原因 + 冻结主因优先级,沿用 0e.5/
     search-6 已冻结口径):**独立持久化**于 stop_reason_records
     表;endpoint 记录只按 payload_hash 引用,不复制其语义;
   - `chemical_endpoint_assessment`(unknown / metabolic_handoff /
     supported_terminal_transformation_product /
     supported_mineralization):**只**由独立终点证据决定(见 3/4;
     S4 回修 r1 起另受必要条件 unknown/conflict 的**阻断输入**
     限制,见 0h.1 —— 阻断不是支持输入,不新增支持来源);
   - `bookkeeping_status`(closed_within_declared_scope /
     not_closed / unknown):参与物/系数/根碳账/映射是否在声明
     范围内闭合(见 6)。
2. **F01 停止非终点**:无候选/深度上限/预算上限/模型弃权/等待
   预测/队列耗尽/用户停止七类情形只产生搜索停止状态,**永不**
   映射为终点值;无独立终点证据 ⇒ assessment = unknown;停止不
   覆盖已有有效终点证据(有效直报证据 + budget_limit 停止并存:
   评估照 supported、停止照 budget_limit);停止时保留 deferred/
   未展开/blocked 对象/预算原因/已有证据。
3. **终点证据(来源层直报;全部字段保留)**:证据声明来自冻结
   计划输入(S3B-01 冻结来源;合成规则级夹具,不是生产数据),
   每条必带:evidence_basis(direct_observation /
   inferred_from_pathway / model_prediction / no_evidence ——
   表示依据种类,不是固定强度次序)、endpoint_claim、source_refs
   (来源引用)、source_support_scope(来源支持范围)、
   conditions_environment(条件与环境)、observation_window
   (观察时间/窗口)、detection_range(检测范围)、
   necessary_dependencies(必要依赖)、root_carbon_fate_check_
   scope(根碳去向核查范围)、unverified_axes(未核实轴)、
   proof_scope(证明范围)。**只有 direct_observation 可支持
   claim;模型预测或路径推断不能单独产生 supported_***
   (inferred/model/no_evidence 条目保留作披露,不入支持)。
   声明级充分性(claim 所需字段缺失 ⇒ 该证据不足以支持该 claim,
   评估保持 unknown 并逐字段披露缺失;证据本身不丢):handoff 需
   source_refs + scope;terminal product 需 + 条件 + 窗口 + 检测
   范围;mineralization 需再 + 根碳去向核查范围 + 必要依赖
   (缺根碳去向/来源终点证据/必要条件 ⇒ unknown)。
   来源报告的矿化比例必须保留计量基础、条件、时间范围和证据
   引用(观察窗口/检测范围/核查范围字段即其载体);较长观察期
   不自动更可信(窗口是保留字段,不是强度)。
4. **F02 未知依赖不被 recorded 洗白**:route 上未解决必要依赖
   (上下文 Dependency status != supported,含 unresolved/
   contradicted)沿途保留并继承进 endpoint 记录(依赖 id/kind/
   statement/status/来源/引入假设);存在未解决必要依赖 ⇒ 评估
   保持 unknown(evidence 保留 + blocked_reasons=
   unresolved_dependencies_inherited;依赖解决后同证据可支持)。
   recorded 只表示该边/该观察在来源层被记录,不表示终点已获
   支持 —— endpoint 记录同时保留 recorded 状态(事件/attempt
   行)、inherited unresolved、依赖来源、条件快照与 proof scope。
5. **F03 不同来路与重复来源不增独立支持**:计数用去重口径 =
   观察身份(来源引用集合 + basis + 声明 + 窗口/检测/条件)+
   来源身份(来源引用集合);同一观察的多个包装、同一来源的
   多个引用/多条声明只算一次独立支持;**来路不删除** —— 全部
   原始条目按原样保留在 endpoint_evidence;同模型多次采样按
   同一来源身份计(model_prediction 本就不支持)。同一模型多次
   采样只估计随机变化,不是新增独立路径(S5 统计侧同口径)。
6. **根碳账(账平不当矿化)**:bookkeeping 只表达声明范围内
   账面闭合(全部事件参与物系数已知且引用完整 ⇒ closed;
   未知系数 ⇒ unknown,不猜数值;参与物状态引用悬空 ⇒
   not_closed);`root_carbon_accounting_coverage` 是**核查范围**
   (查了什么:submitted 事件的声明参与物),不表示所有根碳已
   转化;**不同备选反应生成的 CO₂ 不相加**(逐事件/逐备选列示,
   运行级聚合值不产生);单项 CO₂ 产物不自动解释为根污染物
   矿化;root_carbon_fate_status 只能来自证据(有直报核查范围 ⇒
   source_reported_check_scope_only,仍非本仓自己的核实;无 ⇒
   unknown),**恒不由 bookkeeping 推导**;账目闭合不等于发生
   矿化,也不等于生物可行。
7. **评估取值边界**:评估 = 已获支持的最强声明(mineralization >
   terminal product > handoff);metabolic_handoff 不等于矿化;
   supported_terminal_transformation_product 不推断永久去除;
   不自动推导解毒(S4 全程无解毒结论字段;detoxification 不在
   首版语义内);停止/账平/同 CN/多旁证均不作为终点依据。
8. **endpoint 独立持久化与首消费**:stop_reason_records /
   endpoint_records 两张派生投影表(纯增量,store-10;零既有列/
   行为改动);派生只读业务表(零 event/attempt/request/budget
   写入);派生后立即首消费读回(版本门 / payload_hash 复算 /
   跨表 stop 引用一致 / staleness 输入摘要重算对照 —— events/
   actions/证据/依赖四摘要 + endpoint_policy_version 任一漂移 ⇒
   endpoint_record_stale 拒;篡改 payload ⇒ corrupt 拒;自洽改写
   schema_version ⇒ 版本门拒;引用断裂 ⇒ 拒;均保全原行、零写入,
   不能以重算新 hash 洗白);重复 resume 同事实 ⇒ 同 payload_hash
   (载荷不含时间戳;停止视图含会话 refusals/no_local_candidate
   的会话观察,允许随会话更新 —— 事件/预算零新增是硬边界)。
9. **原生结果对象(底座;ppv1-native-result-1)**:从持久权威
   (store 行 + H07 校验 artifact)聚合完整字段:states+appearances
   (不同来路 source_refs/structure_origin 各自保留,不按 CN
   合并)、路径身份(父+事件+产物引用,同 queue 单一来源)、
   全部假设/事件/报告投影/展开计划(仅报告状态与已展开状态
   分列)、备选反应关系(同父多 expand)、共同产物(事件内
   coproduct)、条件与依赖(上下文 artifact 首消费)、provenance、
   audit 结果与 proof scope(每 expand 的 production_report,
   H07 校验读取)、失败/unknown/partial 原因(expansion_outcome:
   unresolved_continuation/method_failed/contract_aborted 等)、
   deferred 两类分别列示、blocked、预算预约与实际消耗、model
   requests、搜索停止记录、endpoint 四分账记录;**确定性规范
   化**:canonical_json 键序 + 列表稳定排序,载荷不含构建时间戳
   ⇒ 同事实同 digest;落盘为 digest 键派生 artifact(不可变幂
   等,事实变化 = 新键新记录,历史保留)。**G02 完整面(文件级
   重复导出/manifest/读取消费/过期识别与 v3 lossy_projection
   适配)属 S4b 未做** —— S4a 只交付对象级确定性与 endpoint 记录
   级 stale/integrity。
10. **S4a 边界诚实声明**:v3 有损适配**未实施**(无 lossy_
    projection 产出;legacy/export_v3.py/AtomTool/G2 冻结零改动,
    52 份 legacy code_identity 文件与生产/化学共享核心
    production/chemstate/path_context/hypothesis/events/audit/
    search/queue/model_protocol 逐字节同父 adf0287,legacy 聚合
    保持 18007e6a…);原生正式文件导出/manifest/读取消费契约/
    过期识别的完整矩阵未做(仅对象底座 + endpoint 记录级校验);
    完整端到端链(start/resume→native export→v3 adapter→replay)
    未做(S4a 只验证 start/resume→驱动→停止→endpoint 分账→
    首消费→对象底座);本批全部 scripted/off 规则级夹具,网络
    请求 0、真实 provider 默认 off、判分零 LLM;科学性能/真实
    检索质量/金标/题面/封存 run 一律未触碰;dev 与 298 题域
    双向不外推。
11. **语义未改变声明(v16 对冻结判据的关系)**:判据一–五与
    0d/0e 正文**一字未改**;本批只是**描述 S4a 实际新增的消费
    入口**(endpoint 四分账派生/读取/首消费 + 原生结果对象),
    不改变已冻结判据的含义、范围或硬门 —— 按 AGENTS.md 与冻结
    稿"冻结后变更"条款,这属"只描述本批实际新增的消费入口且
    不改变已冻结判据含义"情形,**明确写出:语义未改变**。工程
    登记面变化(store-9→10 两张纯增量派生投影表、profile-14→15
    新增 endpoint/native-result 契约注册、runflow-3→4 公共入口
    接线)不改 0d/0e 消费契约行为(put_state/submit_event/搜索
    记账/恢复协议/冻结计划锚定全部保持;879 存量测试零改动
    ——**限定:除 S4 回修 r1 起逐批披露的版本字面量行**——
    全绿为程序证据;S4 侧 endpoint 评估行为自 r1 起有实际变化
    (必要条件阻断,0h.1),属 S4 契约族自身版本登记范围,
    **不在判据一–五/0d/0e 冻结范围**)。若评审认定 0f 任何
    表述实际改变判据正文/范围/硬门,须按版本规范另评
    (ppv1-criteria-v2 起),不得静默生效。

## 0g. S4b 正式导出与 v3 有损投影(受审表述;v17 新增)

S4b(S4 收尾批)把 S4a 原生结果对象落为**正式文件导出**,并给出
**显式有损的 v3 兼容投影**。0f.9/0f.10 所列"S4b 未做"项(正式
文件导出/manifest/读取消费契约/过期识别/v3 lossy_projection/完整
端到端链/legacy 字节专项)在本批全部交付。以下全部为**消费契约
与化学边界声明**(导出/投影侧),不改判据一–五与 0d/0e/0f 任何
正文语义(见本节末"语义未改变"声明)。

1. **正式导出的组成(ppv1-native-export-1)**:每 run 导出为
   `native_export/<export_digest>/payload.json + manifest.json`
   文件对。payload = 原生结果对象全量载荷(S4a 0f.9 的全部字段组
   —— 共同产物/备选/不同来路/条件/依赖/audit/proof scope/
   deferred 两类/未展开集合/budget 预约与消耗/停止记录/endpoint
   四分账记录,逐组保留,不按 CN 合并、不截断、不改写 unknown/
   partial/deferred 为成功);manifest = 新鲜度锚(全部契约版本
   常量、固定导出策略 hash、payload 字节 sha256、graph revision
   等价身份、权威引用)。**导出不产生任何新化学判定**(纯派生
   文件;终点评估仍只在 endpoint 分账)。
2. **graph revision 等价身份(G02 过期识别的事实锚)**:PPV1
   pollutant 存储没有 legacy 的整数 graph_revision;本仓的事实图
   修订身份 = **15 张持久事实表的逐表内容 digest**(states/
   appearances/hypotheses/events/projections/plans/appearance_
   links/provenance/actions/attempts/reservations/requests/
   commits/stop 记录/endpoint 记录)。任何事实行新增/改写 ⇒
   对应 digest 变化 ⇒ 旧导出按 stale 拒(不能静默当作当前结果)。
3. **确定性(G02 ①②)**:payload 与 manifest 均无时间戳、
   canonical_json 键序 + 列表稳定排序;`export_digest =
   content_hash(manifest 核心)` ⇒ 相同事实 + 相同版本 + 相同
   策略 ⇒ 相同目录、相同字节(同进程/跨进程一致,独立子进程
   重导出字节一致有测试);事实变化 = 新 digest = 新目录,**旧
   导出文件保全不覆盖**(历史按 digest 可回溯);恢复后(驱动
   结算)重复导出字节不变 —— 停止视图含会话成分(session
   refusals / events_submitted_session,S4a 既有披露)的夹具,
   相邻 resume 允许 stop/endpoint 权威行合法更新 ⇒ 新 digest 新
   目录(事件/预算零新增是硬边界)。
4. **首消费读取(结构化拒;G02 ③⑥)**:按固定次序核验,
   fail-closed、零写入、原文件保全:文件缺失 ⇒ export_missing;
   manifest 不可解析/digest 绑定断裂 ⇒ export_manifest_corrupt;
   payload 字节 sha 不符 ⇒ export_payload_corrupt;schema 版本
   未知 ⇒ export_version_unknown;内容 digest 复算不符 ⇒
   export_digest_mismatch;权威引用断裂(endpoint/stop 行、
   原生结果 artifact、逐 artifact 内容 hash、冻结计划)⇒
   export_reference_mismatch;导出策略 hash 不符 ⇒
   export_policy_stale;graph facts digest 与当前持久权威不符 ⇒
   export_stale(带 changed_facts 清单)。
5. **防洗白(G02 ⑦)**:过期/损坏导出零写入、原文件保全;
   自洽重写(payload + manifest 内部 hash 全部重算的"新 ID")
   逃不过权威引用与事实 digest —— 两者都从**独立权威**(DB 行 +
   artifact store)重算,不信任 manifest 自声明;导出同 digest
   路径已有不同字节 ⇒ 重导出拒(不可变;篡改文件须显式清除,
   不能靠重导出静默洗掉)。无密码学签名、不抗全库协同改写
   (沿 S3B-01/S4a 已披露边界)。
6. **v3 有损投影(ppv1-v3-projection-1;legacy export_v3 冻结
   零触碰)**:投影是 native result 的显式有损视图,载荷顶层
   `lossy_projection: true`(缺失/篡改 ⇒ 拒);v3 字段形状冻结
   (route_id/root_smiles/steps[parent_smiles, predicted_
   products]);**每步 = 一个已提交事件**(同父备选不合并为单
   反应;同父多事件保留为多步;多 reactant 事件 collapse 为首
   reactant 并逐条披露);root_smiles = run identity 的真实原始
   输入(不用 path_id/显示名/cn 冒充);无事件 ⇒ 空步骤答卷
   (空答卷不是终点/去除结论)。
7. **信息损失清单(显式列示,逐项带 native_authority 指回原生
   字段组)**:来路(route_origins)/共同产物角色(coproducts)/
   备选关系(alternative_reactions)/条件与依赖(conditions_
   dependencies)/audit 与 proof scope(audit_proof_scope)/
   deferred 与未展开集合(deferred_unexpanded)/endpoint 证据
   等级(endpoint_evidence_level)/预算停止原因(budget_stop_
   reason)/unknown 与 partial 具体轴(unknown_partial_axes)/
   系数(coefficients)/路径身份(path_identity)/来源
   provenance(source_provenance)+ 动态条目(多 reactant
   collapse、空答卷)。**不可投影字段的摘要或引用**保留在
   unprojectable_summaries(endpoint 评估/独立支持计数/依赖
   未解决清单/停止原因/CO₂ 逐事件数/条件键已知未知等计数与
   状态值;不展开全文,全文在原生导出)。
8. **不为填满旧字段编造**:投影**不产生**终点/矿化/解毒/去除
   结论 —— endpoint 评估、证据等级、矿化边界全部留在原生
   endpoint 分账(0f);v3 步骤不得解释为矿化/去除/解毒;
   CO₂ 备选不相加语义保持(逐事件步骤保留;unprojectable_
   summaries 计数不聚合);不同备选 CO₂ 不因投影合并相加。
9. **双向引用边界**:正向(原生 → v3):投影携带 native_
   reference(export_digest/原生内容 digest/原生结果 artifact
   task_key),读取时核对原生导出 manifest 存在(断裂 ⇒ 拒);
   原生侧新鲜度由 read_native_export 负责(投影有效 ≠ 原生
   不过期)。反向(v3 → 原生):仅**只读反查**(按 native 引用
   扫描投影目录;不改原生 manifest/任何文件);原生 manifest
   不内嵌投影清单(原生不可变,投影可后生成)。**反向消费在
   契约上禁止**:投影载荷不能进原生消费入口(原生导出读取/
   原生结果读取均拒);v3_projection 模块不暴露任何投影 → 原生
   事实/事件/状态的写入入口;消费投影零 DB 写入;投影与原生
   结果**不得计为两条路径**(F03)。
10. **完整公共链(scripted/off 规则级;网络 0)**:scripted 输入
    → start/resume(含崩溃恢复)→ action/attempt/ledger 消费 →
    停止 → endpoint 四分账 → 原生正式导出 → 首消费读回 →
    v3 有损投影(构建即读回)→ 再次读取/消费 → replay(再
    resume:零新 event/attempt/request/budget;旧导出文件保全)。
    G02 七测矩阵(①重复导出含子进程字节一致 ②恢复后重复导出
    ③导出再读取 ④源图变化过期 ⑤策略变化过期 ⑥内容 hash/引用
    不一致结构化失败 ⑦自洽重写不可洗白)全部有测试。
11. **S4b 边界诚实声明**:legacy/export_v3.py 与冻结路径**零
    字节触碰**(当前树 vs 直接父 fc40605 专项对比:两组合成
    legacy run 的 predictions.jsonl + export_metadata.json 四
    产物逐字节一致;52 份 legacy code_identity 文件聚合保持
    18007e6a…;AtomTool/G2/production/chemstate 等共享核心零
    改动);本批全部 scripted/off 规则级夹具,网络请求 0、
    真实 provider 默认 off、判分零 LLM;科学性能/真实检索质量/
    金标/题面/封存 run 一律未触碰;dev 与 298 题域双向不外推;
    S5(评测器/数据规范/预注册)未启动。
12. **语义未改变声明(v17 对冻结判据的关系)**:判据一–五与
    0d/0e/0f 正文**一字未改**;本批只是**描述 S4b 实际新增的
    消费入口**(正式文件导出 + v3 有损投影),不改变已冻结
    判据的含义、范围或硬门 —— 按 AGENTS.md 与冻结稿"冻结后
    变更"条款,这属"只描述本批实际新增的消费入口且不改变已
    冻结判据含义"情形,**明确写出:语义未改变**。工程登记面
    变化(profile-15→16 新增 native-export/native-export-policy/
    v3-projection 契约注册、runflow-4→5 公共入口接线、store
    保持 -10 导出为 run 目录文件无新表)不改 0d/0e/0f 消费契约
    行为(914 存量测试零改动——**限定:除后续回修批次逐批披露
    的版本字面量行**——全绿为程序证据;导出/投影首消费核验集
    自回修 r1/r2 起有实际扩充(0h/0i),属 S4 契约族自身版本
    登记范围,**不在判据一–五/0d/0e/0f 冻结范围**)。若评审
    认定 0g 任何表述实际改变判据正文/范围/硬门,须按版本规范
    另评(ppv1-criteria-v2 起),不得静默生效。

## 0h. S4 回修 r1:四组消费契约闭合(受审表述;v18 新增)

S4 正链确认复核(Codex,2026-10-08)对 S4a+S4b 裁定**不确认通过**,
四组 P1(均落在 S4 任务书已定验收内,不是新增化学门):S4-C01 必要
条件未知未进入终点阻断;S4-C02 manifest 未绑定自身内容、必要权威
引用可被删后绕过首消费;S4-C03 空 task_key 动作的下游 soutc 结论
漏聚;S4-C04 v3 投影可把错误内容挂到真实原生引用。本批按确认复核
§4 最低收口回修;以下全部为**消费契约闭合表述**,不改判据一–五
与 0d/0e/0f/0g 任何正文语义(见本节末"语义未改变"声明)。

1. **S4-C01 必要条件同源限制(ppv1-endpoint-2/endpoint-policy-2)**:
   当前路线已引入的**必要条件**(假设声明 level=essential 且
   basis=essential_claimed_by_source,即"来源声明必需"轴)经**同源**
   `PathContext.route_assessment()`(历史快照逐边合取 + 当前阶段
   live;旧边按记录值消费,不拿当前事实重评后洗白)评估为
   unknown/conflict 时,chemical_endpoint_assessment 保持 **unknown**
   —— 必要条件未知/冲突不能被来源层 recorded 标记或充分证据字段
   洗白(与 F02 未解决依赖同层阻断);逐条评估行**全文保留**在
   record.route_condition_assessment(含 reason/fact_sources/
   requirement_signature),输入摘要(route_conditions_digest)入
   derived_from 与首消费 staleness 同源重算;start/resume/严格首消费/
   native 导出载荷/v3 摘要(endpoint_assessment + 必要条件 unknown/
   conflict 键)同值。**边界**:已知兼容(必要条件满足)与无必要
   条件的合法来源声明保持可支持(**不全拒**);缺启动 NAD 依赖正/
   负控保持;不解析证据自由文本;不新增机制/生物可行性/电子转移硬
   门(评估仍只由来源层直报证据决定,必要条件只作**阻断输入**,
   不作支持输入);来源声明真实性仍不在认证范围(沿 0f.2)。
2. **S4-C02 manifest 绑定与必要引用集合闭合(ppv1-native-export-2/
   native-export-policy-2)**:首消费新增三层核验(全部 fail-closed、
   零写入、原文件保全,八 kind 拒绝面保持):(a) **manifest core
   自身 digest 复算** —— manifest 去掉 export_digest 键后重算内容
   hash 须与声明值一致(不是新增自比较字段,是对文件内容本身与
   导出侧同一构造复算),manifest-only 改坏 run_id/契约版本/策略
   正文/引用集合而保持原 digest ⇒ export_manifest_corrupt 拒;
   (b) **run/版本/策略内容与当前登记源绑定** —— manifest.run_id
   与当前 ledger run 绑定、contract_versions 块与 profile 常量逐项
   绑定、自记策略正文重算 hash 须与自记 sha256 一致且正文等于当前
   策略 ⇒ 自洽重封换 run/版本/策略不再照收;(c) **必要 artifact
   引用集合由独立权威同源枚举后整集闭合**(与每行 hash 校验分别
   核)—— 与导出写入共用同一 artifact_reference_index + 冻结计划
   来源(**同一完整索引,不各修一套规则**),枚举"当前应被引用且
   实际存在"的集合与 manifest 自报集合整集比对:漏单项必要引用的
   自洽重封(重算 digest、新目录、复制 payload)⇒ export_reference_
   mismatch 拒;引用的 artifact 已缺失 ⇒ 同拒;枚举撞到损坏
   artifact ⇒ 结构化拒(不静默略过);**合法缺席**(尚未产出的
   artifact)保留,不产空引用。仍不做密码学签名、不抗全库协同改写
   (沿已披露边界)。
3. **S4-C03 空 task_key 的 soutc 聚合闭合(ppv1-native-result-2)**:
   非事件动作完成的调度结论 artifact 按 `stable_id("soutc",
   action_id)` 键**独立枚举,不再被空 action.task_key 挡住** ——
   正常公共链中 child retrieve 的 no_local_candidate /
   unresolved_continuation=True 结论**全文**进原生结果对象的
   expansion_outcomes 与导出 manifest 引用(build 与 manifest 共用
   同一索引);task_key 键的生产报告/结论**仅在键合法时列举**(缺键
   不产空键引用);坏必要 soutc ⇒ build 与导出读取都结构化拒(不
   静默略过、不当合法缺席);合法缺席与去重保持;retrieve/decide/
   activate/transition 同一规则适用。
4. **S4-C04 原生→v3 投影来源绑定(ppv1-v3-projection-2)**:
   **已验证原生存在/投影自 hash 不再是投影证书**:(a) 构建侧先经
   `read_native_export` 首消费核验其引用的原生导出,并要求传入的
   native_result 与该导出的 payload **同一**(整对象比对 + 内容
   digest/导出摘要/run 绑定)—— 假 native(删 events/deferred 后
   自洽重算 digest)配真 export 引用 ⇒ 构建拒;(b) 读取侧核
   native_reference 与真实原生导出 manifest 的**内部一致**(export
   digest/core 复算/payload sha/content digest/task_key/graph
   revision aggregate/run_id 两两绑定)—— 混搭 digest/task_key/sha
   或换 manifest ⇒ 拒;(c) 投影**已表达字段**(route.steps/
   root_smiles/unprojectable_summaries/information_losses/run_id)
   由该原生 payload 按**登记 adapter 同源复算比对**(单一来源
   派生函数,构建与读取共用)—— projection-only 自洽改内容
   (重算 projection_digest 换新目录)配真 reference ⇒ 拒;可选传
   ledger 时读取先走完整原生首消费。有损 12 轴、正常与空池答卷、
   逐事件步骤不按 CN 合并、不编造终点、反向消费禁止、零 DB 写、
   投影与原生不计两条路径(F03)全部保持(0g.6–0g.9)。
5. **正控保持声明**:四组回修均带确认复核给出的正控/负控复验
   (同一充分矿化声明:无必要条件 ⇒ supported;已知 aerobic 必要
   条件满足 ⇒ supported;缺启动 NAD ⇒ unknown;边界控制 5/5;
   修前 2F/3P oracle 对修后重捕获数据 5/5、对修前捕获数据保持
   2F/3P 不改期待);确认复核的公开反例逐案复制到新 tmp 复跑全部
   翻转为拒;旧观察脚本钉住缺口、按修后预期失败登记(两支脚本
   逐字复跑 exit 1 于缺口闭合点,忠实微调版记录全部翻转为拒)。
6. **S4 回修 r1 边界诚实声明**:本批不改 legacy/export_v3/G2/
   AtomTool/production.py(逐字节);全部 scripted/off 规则级夹具,
   网络请求 0、真实 provider 默认 off、判分零 LLM;金标/题面/封存
   逐题 run/dependingv4/冻结 v3 资产一律未访问;dev 与 298 题域
   双向不外推;S5 未启动;判据冻结状态不因本批改变;工程登记面
   版本升级(见 §6 契约族)**不改判据一–五与 0d/0e 冻结范围**;
   0f/0g 所属的 S4 endpoint/导出/投影契约族自本批起**有实际行为
   变化**(必要条件阻断、导出首消费核验集扩充),按各自契约版本
   号登记(endpoint-2/native-export-2/v3-projection-2 等),
   不与"冻结判据语义不变"混同(见 0h.7 与复审 R2 §5)。
7. **语义未改变声明(v18 对冻结判据的关系)**:判据一–五与
   0d/0e/0f/0g 正文**一字未改**;本批只是把确认复核判为缺失的
   四组**既有验收**(任务书 §2.B/§2.C/§4.2/§4.4/§8 已定范围)
   落到消费入口闭合,不新增化学判据、不改变已冻结判据的含义/
   范围/硬门 —— 按 AGENTS.md 与冻结稿"冻结后变更"条款,属
   "只描述本批实际新增的消费入口且不改变已冻结判据含义"情形,
   **明确写出:语义未改变**。若评审认定 0h 任何表述实际改变判据
   正文/范围/硬门(尤其 0h.1 的必要条件阻断是否应视为新硬门),
   须按版本规范另评(ppv1-criteria-v2 起),不得静默生效。

## 0i. S4 回修 r2:两组消费契约残余闭合(受审表述;v19 新增)

S4 正链复审 R2(Codex,2026-10-08)对回修 r1 裁定 C01/C03 关闭,
**剩余 P1 = S4-C02(必要文件与引用一起消失后必要集合被缩小)、
S4-C04(无 ledger 投影首读不核父来源版本)**;另列 P2 精度项。
本批按复审 R2 §4 最低收口回修,不新增化学门;以下全部为**消费
契约闭合表述**,不改判据一–五与 0d/0e 冻结范围(见本节末声明)。

1. **S4-C02 必要集合不由"文件目前存在"决定(ppv1-native-export-3/
   native-export-policy-3)**:应有必要项由**原生实际消费 + 已完成
   action/task/commit + 冻结计划锚行**同源闭合(共用同一
   artifact_reference_index 索引,必要性按权威行判定,在读文件之前
   从 DB 行 + payload 判定,不读 artifact 文件反推):
   - **原生实际消费闭合(主反例捕获)**:导出 payload 的
     audit_production_reports / expansion_outcomes / contexts 声明
     引用的每个键 ⇒ 必要 —— 删已完成任务的 production_report
     文件 + 删 manifest 同引用 + 自洽重算新 digest(文件与引用
     一起消失,DB/native 均不改)不再被"枚举时文件不存在 = 合法
     缺席"放过 ⇒ export_reference_mismatch 拒(omitted_necessary_
     refs 带判定依据 payload_audit_production_report_consumed);
     零业务写、缺席形态保全、原导出不受影响、还原正控通过;
   - **已完成 action/task/commit 行闭合(写路径不变量)**:
     done 且 outcome 类提交的 retrieve/decide/activate_deferred/
     scenario_transition ⇒ soutc(stable_id(action_id))键
     expansion_outcome 应存在(调度结论 artifact 先写后完成);
     done 且 outcome 类提交的 expand_hypothesis(空 task_key 回退
     soutc)同理 ⇒ 该项缺文件时**导出侧写入前先拒**(不封不
     完整 manifest,零新导出目录);
   - **production_report 的行闭合不判(合法边界保持)**:生产链
     `production.py _report("submitted")` 在 complete_action
     **之后**落盘,B4 崩溃恢复(事件已提交、记账未闭合 ⇒ 恢复
     幂等补账)**合法不产报告** ⇒ "done expand 必有 report"不是
     本系统不变量;B4 恢复后的 done expand 无 production_report
     保持可导出、可读取(合法未生产保持,不一刀切)。
2. **S4-C04 无 ledger 投影首读核父来源版本(ppv1-v3-projection-3)**:
   `_load_bound_native_export` 在解析父 manifest/payload 后、
   当前 adapter 解释内容**之前**,按**共用登记源**(profile 常量
   经 native_export 的版本单一来源,与有 ledger 首读/构建同一
   登记)核:父 manifest `schema_version`、`contract_versions`
   整组(缺失/未知/冲突分别披露)、native payload
   `native_result_version`、投影自记 native_graph_revision 版本组
   与登记源重叠键冲突 —— 未知/缺失/不一致 ⇒ `v3_native_source_
   version_unknown` 结构化拒;原生读取(read_native_export)同批
   新增 payload 原生结果版本门(export_version_unknown)。
   **边界**:无 ledger **不强加 DB 新鲜度**(文件级分工不变:
   坏 H07/重封已知版本假原生的无 ledger 个别观测按 R2 登记边界
   保持接受);但**不得把未知来源版本包装成已验证结果**,不用
   当前 adapter 默猜迁移(历史版本无显式对应 adapter ⇒ 拒);
   合法无/有 ledger 读取、有损 12 轴/空答卷、旧文件保全、零
   原生/业务写保持。
3. **正控与反例复验声明**:R2 复审公开反例逐字复跑(independent_
   cases.py 复制到新 tmp):single_ref_missing 自洽重封读取由接受
   翻转为拒;unknown_export_schema / unknown_contract_profile /
   unknown_native_result 无 ledger 首读全部翻转为拒;
   no_ledger_h07 / no_ledger_resealed_source 按 R2 登记的文件级
   边界保持接受(不加 DB 新鲜度门);全部用例零 DB 写、还原
   正控;公开 start/resume 正控全绿、网络 0。新增 11 条回归
   (三变体单引用/写入侧守卫/B4 合法无报告/四个未知或缺失版本/
   版本组缺失与投影版本组冲突/合法无-有 ledger 读取与空答卷)
   对直接父 0dd35d1 同字节运行 = 7 拒绝缺失行为红 + 1 字段红 +
   3 版本字面量红,0 collection;正控 41 绿。
4. **P2 精度同步(复审 R2 §5,不单独阻塞)**:本批同步落字
   0f.1(评估只由证据决定 ⇒ 同时引用必要条件阻断输入限制)、
   0f.11/0g.12(存量零改动限定为"除逐批披露字面量";S4 契约族
   实际行为变化与冻结范围分写)、0h.6(旧"0f/0g 化学含义都不变"
   缩回冻结一至五/0d/0e);mimo r18 第 63 条按程序实证继续采信
   为 P1 消费规则(不是纯文字条件)。
5. **S4 回修 r2 边界诚实声明**:本批不改 legacy/export_v3/G2/
   AtomTool/production.py(52 份非 pollutant src 文件聚合两树一致;
   两树四产物 legacy 字节专项 4/4 一致);全部 scripted/off 规则
   级夹具,网络请求 0、判分零 LLM;金标/题面/封存逐题 run/
   dependingv4/冻结 v3 评价资产一律未访问;dev 与 298 题域双向
   不外推;S5 未启动;判据冻结状态不因本批改变。
6. **语义未改变声明(v19 对冻结判据的关系)**:判据一–五与
   0d/0e 正文**一字未改**;本批只是把复审 R2 判为缺失的两组
   **既有验收**(任务书 §5.1"派生前必须先验证父对象"/§5.4
   版本规则已定范围)落到消费入口闭合,不新增化学判据、不改
   变已冻结判据的含义/范围/硬门 —— **明确写出:语义未改变
   (限冻结范围 = 判据一–五与 0d/0e;S4 契约族 endpoint/native-
   export/native-result/v3-projection 的首消费核验集自 r1/r2
   有实际行为变化,按各契约版本号登记,不属冻结范围)**。
   若评审认定 0i 任何表述实际改变判据正文/范围/硬门,须按版本
   规范另评(ppv1-criteria-v2 起),不得静默生效。

## 1. 判据一:分子身份(v12 文本,自包含)

**1. 身份键**:`state_id` = **化学 CX 事实子集**的规范化 canonical
CXSMILES 的稳定哈希。生成前移除非化学 CX 元数据:坐标(conformer)、
原子标签(atomLabel)、任意 atomProp(绘图/注释不改严格分子图身份);
保留增强立体组(AND/OR/绝对)、自由基层、基串内的同位素/电荷/
立体。无组且无自由基层注解的分子输出与普通 canonical isomeric
SMILES 逐字相同(自由基分子带 `|^n:…|` 后缀是例外:身份层区分
自由基,保真轴为已登记缺口)。与 RDKit RegistrationHash 的一致性
限定在整组翻转/部分反转/排列/kekulé/映射号子集;plain≡`|a:…|`
同键是本仓归一设计,与 RegistrationHash 的 CANONICAL_SMILES 层
存在已登记分歧。

**2. 输入侧注册感知校验(原始串词法守卫)**:解析**之前**对原始
结构串逐项词法 —— RDKit 解析会静默丢弃 `|r|`、`|Ln:1|`、`|c:1|`、
`|wU:1.5|` 等未登记块(之后与裸输入同 state_id,输出侧守卫永远
看不到),故输入侧按真实 CX 类边界逐项分派:项序列由 ','/空格
分隔;登记类(atomProp/SgD=移除类;Sg=保留类;$…$ 标签值块与
(...) 坐标块=移除类;增强立体与自由基层注解=保留类)各自耗尽
自己的字段(字段内逗号/空格是内容,**登记内容含空格放行**,如
`atomProp:0.note.hello world`);未登记首头(含并列位置,如
`atomProp:0.n,r` 的 `r`)显式拒绝;DAT(SgD)值内逗号继续受
保护(DAT 剥离有适配器前提,只剥已登记 SgD 形态)。同一守卫覆盖
**全部原始 CX 入口**:工厂 build、strict_identity_of、判据五的
四个原始字符串字段、恢复入口与 audit 直接对象(2b)。
**v12 落字(复审 R3 §6①,真实 token)**:登记保留的立体/自由
基层注解头按**实际 CX token** 写 —— `a:`(绝对/ABS)、`o<N>:`
与 `&<N>:`(相对增强组)、`^<N>:`(自由基层)及已登记 Sg 类;
**and/or/rad 是英文类名,不是输入字面**(RDKit 2026.03.6 实际
写出 ABS/AND/OR/自由基并保持严格身份往返;以三字面别名作为
输入串传入均按 unregistered_cx_class 拒)。"接受/拒绝"只是输入
表示层契约结果,**不构成样品认证**(见 2b 的 r 不反推条款)。

**3. 混合并列 ABS 归一**:ABS(绝对立体)注解剥离为令牌级语法
解析(`a:1,&1:3` ≡ `|&1:3|`、`^1:0,a:1` ≡ `|^1:0|`;段级正则对
逗号并列形态匹配不上会造成同一立体事实分裂成两个 state_id——
已修复)。plain 与 ABS 归一后的分子同键。

**4. 公开表示往返闭合**:`smiles_isomeric` = 身份键同串(往返
无损);`structure_smiles_raw` 保留原始串与 structure_origin/
source_refs/分轴 representation_fidelity 一起存出现记录(appearance),
语义块(states 行)只存严格分子事实 —— representation_fidelity
不是语义成分,同图不同来源保真度共存、互不升级/降级;需要某来源
保真度必须按出现取。

**2b. 恢复/直接对象首消费同源验证(v8 新增,v9 落字三处,v11
再落一处,v12 更正一处)**:恢复入口(`ChemicalState.from_dict`)与
audit 直接 states 对象在首次授信前共用与公共 writer 同源的纯状态
验证(`validate_state_object`):(i) 版本门 + fidelity 分轴契约 +
structure_origin 合法;(ii) 结构态:raw 非空且过判据一第 2 条
同一输入守卫(未登记项 ⇒ 拒,不静默清洗信息再授 full);(iii)
raw 重推严格身份 == smiles_isomeric(同图异拼写如 OCC 接受;跨
分子如 H2 状态挂 CC=O 拒);(iv) smiles_isomeric 须为身份键规范形,
state_id/formal_charge/cn_identity/立体/同位素状态按工厂同源重推导
一致;(v) CN-only 走专用命名空间身份(cs(cn-only,cn))+ 未知
事实契约(不重推导结构)。v9 三处落字保持(同源验证非独立双算;
`r` 标记存在与含义均不采纳也不反驳;canonical+r 的上层错误名
语义须读内因)。**v12 落字(更正 v11 括注,复审 R3 §6⑦ 分两维)**:
同一入口下 canonical+r 与真坏 canonical 两种内因的外层**同为
ChemicalStateError 的不同 kind**,按 `detail.reason.kind` 区分
(unregistered_cx_class / unparseable_smiles)—— v11 所写"工厂
未登记 vs 真解析是不同异常类"的括注**错误**,不得沿用;**跨
入口**的外层才确不同(恢复入口外层 ChemicalStateError、公共
writer 外层 Ppv1StateContractError)。不能把所有外层写成同一类,
也不能把同入口内因写成不同异常类;"同源确定性重推导拒篡改"是
同一算法的复算(不是第二套独立证明);v10 ②③的精度句保持。
- 自报 formal_charge/stereo/isotope 与结构重推导一致的声明,
  限定"经首消费验证的入口"(2b 覆盖的 from_dict/直接对象/工厂/
  writer),不是所有裸 dataclass 对象的无条件性质。

**请评审**:(a) v12 落字(真实 token 表/外层-内因两维更正/同源
非独立算法)与 2b 三处 v9 落字是否准确、不引入越权认证;(b) 入口
清单(工厂/strict/判据五四字段/恢复/直接对象/搜索层全部消费入口)
是否闭合,不产生身份或 verified 证据的诊断入口(池输入 preview 的
conservation 诊断、冻结执行器内部解析)按 C2 划界在守卫外、其
结果不得回流为身份或核实证据(preview 保持 pool_unchanged/
diagnostic_only);(c) 判据本身(1–4)无需重评——文本如上展开
供自包含核对。

## 2. 判据二:参与物计量与元素/电荷核算(v12 文本,自包含;
v12 落字两处)

- **全氢账**:元素核算按全氢(分子式含 H);D/T 合并计 H(已
  登记披露,不区分同位素);**自由基电子不计入元素/电荷账**(数值
  账"平"在这两类有系统盲区,不得读成质量/电子守恒已核)。
- **系数契约(v12 落字,复审 R3 §6②)**:非法表示系数
  (零/负/非有限/bool)在**构造/提交边界拒绝**;
  coefficient_binding_mismatch **属覆盖轴违例**(按判据三处理:
  partial_unchecked_transformation/中心 unknown,**最终处置依
  其他轴与决策表首中规则,不能固定写成自动 reject/R2b,也不能
  固定写成 R5**);**不可虚称"入口在比对系数与结构重推导值"**
  —— 系数绑定核的是声明与补全/覆盖核算的对应,不是对结构重
  推导数值的比对;caller 侧须如实报告映射、不吞错改写处置;
  R2b(表示契约违反)的判定还须 caller 映射 detail(缺映射不当
  化学已核,见判据三 v12 落字)。
- **完整性 unknown**:未知系数 ⇒ coverage unknown_coefficients
  (中心结论 unknown,不猜数值)。**v12 落字(复审 R3 §6⑥,
  known_absent 轴归属)**:known_absent 类语义**属条件评估轴,
  不是元素账的判据**;实体缺席与**非物种字符串的同值缺席** ⇒
  conflict;非物种字符串**异值** known_absent 或未列出 ⇒ unknown;
  **数值/区间缺席 ⇒ unknown(数值缺席语义未定义
  numeric_absence_semantics_undefined,不跨值域泛化物种字符串的
  规则)**。
- **电荷轴前提**:formal_charge 判定以经首消费验证的结构重推导
  值为前提(2b 后不可被直传对象伪造);电荷与元素分轴,不互相
  抵消解释。
- **结构化 omission_pattern_matches**:缺参与物按模式匹配结构化
  报告(不静默);R5d 触发集合显式限定
  {element_accounting, formal_charge_accounting},其他 violated 走
  R5v 独立码(防新增检查静默挂进"声明账不一致")。
- **恒等 ≠ 落点**:净反应两侧同分子(恒等变换)不因元素/电荷平
  而获得任何"转化已核实"结论;数值配平只证明组成闭合,不证明
  转化身份、机理或未覆盖参与物初始图的键变化(与判据三的 full
  两根据互锁)。

**请评审**:确认 v12 两处落字(系数句"不可虚称入口在比对系数与
结构重推导值" + known_absent 轴归属与数值缺席语义)是否准确反映
实现、防止下游把覆盖违例读成固定 R 行或把条件评估轴语义泛化到
元素账;其余展开文本与已同意条款一致(r3/r4 工程回修未改变本
判据任何口径)。

## 3. 判据三:admission 决策表与中心证据契约(v12 文本,自包含;
有序,首中即决)

决策表(评估顺序固定,首中即决):

```
R1  structure_unparseable      → reject  (实际输入语法非法;CN-only 等
    合法缺结构走 unknown,悬空引用走 R1b,不进本行)
R1b participant_state_missing  → reject  (参与物 state 引用悬空 = 账本/
    引用完整性问题,理由码保留,不压平成"结构不可解析")
R2  active_gate_rejected       → reject  (活动门禁显式拒绝;仅 reject_gates
    名单内 —— 不暗改冻结判据,新门禁须独立评审)
R2p per_product_gate_rejected  → reject(全部共同产物被拒)/
    retain_conditional(部分被拒:被拒产物保留拒因、不可展开,不删除
    被拒共同产物凑合法事件)
R2b contract_violated_representation → reject (表示契约违反:零/负/
    非有限系数、酶计入净计量、结构性违约;理由码 representation =
    非化学)
R3  current_scenario_conflict  → defer   (有来源 essential 条件与当前
    场景已知事实冲突;action=blocked,假设保留不在此场景展开)
R4  budget_or_wait             → defer   (独立原因)
R5d declared_account_violated  → retain_conditional(触发集合显式限定
    {element_accounting, formal_charge_accounting};账不平只证明声明
    内部矛盾,不证明反应不存在;绝不进入 R6)
R5v declared_violated_other    → retain_conditional(其他检查 violated
    的独立码,如确定性 checker 的中心偏离)
R5c required_check_coverage_missing → retain_conditional(必需适用检查
    未被执行/不在审计内:窄 audit_scope 只能作诊断,R6 覆盖核算
    不通过)
R5  unknown_checks_present     → retain_conditional(检查 unknown/因缺
    输入未执行;继承未解决依赖)
R6  default_all_verified       → expand(全部必需适用检查覆盖且
    verified,无 unknown/violated/缺输入未执行;语义 NA 白名单除外)
R7  no_applicable_checks       → retain_conditional(无适用检查:保守
    保留,不冒充核实)
```

任何 unknown 不自动 reject;新增"诊断转拒绝"必须扩表并升版本;
chemical_reproposal 首版 off。

类型契约/内部重算:center_evidence 的判定字段由**内部重算**(不采
信自报签名/字符串)产生;无 proof_record ⇒ unknown(不猜);复算
比对含 center_match_basis 披露;proof_record 载荷不可变 + 入口身份
复算(改前提不换 ID ⇒ 拒)。**v11 落字(复审 §6 判据三"复用")**:
"跨假设复用 proof ⇒ 拒"按实际行为分写:跨假设**未绑定** proof 通常
产出**中心 unknown**;**篡改自报与复算不一致**抛契约异常、**本次
无成功 admission**(异常逃逸,不落任何 R 行)—— 两种情形不混成
同一种"拒"。audit.scope/proof_scope+basis 分轴披露:缺 proof/映射/
参与物覆盖时 unknown/partial(center_checker_scope_unknown 等),
字段存在不等于适用。**v12 落字(复审 R3 §6③④⑤)**:
- **R2b caller 映射依赖(③)**:R2b(表示契约违反)的最终判定依赖
  caller 侧如实提供映射 detail —— **缺映射不得当成化学已核**;
  未来 caller 映射义务留 S3b 生产链交付,不在本判据预先虚称已闭合;
- **中心 partial 的表述(④)**:中心结论层面**没有"裸 partial"**
  —— 未满足核(center)按**映射理由码/中心 unknown** 表述
  (center_checker_scope_unknown 等),与覆盖轴枚举
  (partial_unchecked_transformation)分开,不得把覆盖枚举当作中心
  结论名词用;四个原始字符串守卫(判据五)限定**执行成功路径的
  解析之前**;失败早退未解析、不消费其任何轴;None 非通过;
- **入口划界(⑤)**:公共 writer 清单可补;**搜索层的结构权威依
  公共 writer 重放,store.verify_event_attachment_content 只核附随
  投影/计划内容,不单独证明 state 身份**(state 身份的事实源仍是
  states/appearance 行与首消费同源验证);substrate_profile 无生产
  caller,档案输出/未来 caller 前置验证划界为 P2,不重开旧 S0–S2 门。

**覆盖核算与补全许可(composition_only_hydrogen_equivalents)**:
绑定核验按复算的底物/产物身份做整组覆盖;产物覆盖判定输出
`product_coverage` ∈ {full, partial_unchecked_transformation,
unknown_coefficients} 与逐条 `coverage_violations`(kind 如
coefficient_binding_mismatch[系数与声明不符]、completion_surplus/
deficit[补全规则数值不符]、completion_license_unregistered_identity
[未覆盖参与物严格结构身份未登记许可])。**覆盖 full 的两个互不
替代根据**:① 无未覆盖参与物;② 注册补全规则(H2/[H] 按 2[H]
氢当量)数值精确相等且未覆盖参与物身份全部在登记许可内。**二者
都只解除覆盖轴** —— 补全(无论是否持许可)只证明组成闭合,不
证明转化身份、机理或共底物初始图的键变化已核实;身份归 strict
轴、元素/电荷归判据二、转化核实归证据门。

**v9 落字两处 + v10 精度更正一处 + v11 落字一处**:
- **scope 归属(v9,⑤已落地)**:当前代码 `completion_license_
  scope` 字面**不含**"不区分键断裂方式与电子去向"句;该表述归属
  **许可定义/本规则正文**(composition-only 许可不区分该参与物的
  键断裂方式与电子去向,是许可的语义边界)。字段字面未改、无版本
  身份影响;**本请求不再要求改代码 scope 字面**(复审 §5:已在
  规则正文,勿再当未闭合项;正式冻结由用户另裁)。
- **恒入 ≠ 已适用(v9;v11 精度补写)**:`completion_license`/
  `completion_license_scope` 恒入 center detail,**full/partial 完成
  分支携带 license/scope 字段**,但 unknown_coefficients/unverifiable
  的**早退例外**不携带(早退发生在覆盖判定之前);字段存在不等于
  本结论使用了补全许可;判定"本结论依据含许可补全"须同时看
  **product_coverage=full、uncovered_reactant_refs/uncovered_
  product_refs 非空、unlicensed_uncovered_identities 为空** 三条件
  组合;license_applied 标志/顶层别名/同屏渲染列属后续 API/展示层
  (P2,不作本轮门)。
- **v10 精度更正(mimo v9 回应 ⑥ 的判负口径,保持)**:mimo 曾
  概括"partial = 许可本身判负"—— 不精确,不得照抄:(a) 实际枚举
  是 `partial_unchecked_transformation`(存在额外未核实转化/未
  核实结构贡献),不是裸 "partial";(b) uncovered+partial 组合下
  `coverage_violations` 可能是 `coefficient_binding_mismatch`(系数
  与声明不符)或补全数值不符,与许可是否登记无关 —— **不能一律称
  "许可本身判负"**,须读 coverage_violations 的逐条 kind;(c)
  `unknown_coefficients` 等早退(coverage unknown)发生在覆盖判定
  之前,**尚未使用许可**,不得称"已使用许可后判负"(**r9 原话是
  "补全规则被调用且判负",不得转写成"许可本身判负"**);(d)
  许可未登记身份的 case(completion_license_unregistered_identity)
  才直接关联"数值配平不证明未登记多原子共底物初始图的结构贡献"
  这句规则正文。
- **v11 落字(复审 §6 判据三"恒入/复用"补写)**:见上文类型契约
  段 —— full/partial 完成分支的 license/scope 恒入、早退例外、跨
  假设未绑定 proof 与篡改复算不一致两种情形分写,不再用单一"拒"
  概括。

**请评审**:(a) v12 落字(R2b caller 映射依赖/中心 partial 按映射
理由码与覆盖枚举分开/入口划界)与 v11 落字(恒入/复用分写)、v10
精度更正四点(a–d)是否准确反映实现语义、足以防止下游把 coverage
枚举读成"许可判负"或把附随内容核验读成 state 身份证明;(b) v9
scope 归属与恒入≠已适用+三条件判定是否如实(确认后本项不再列入
后续请求);(c) 决策表与覆盖核算展开文本是否与实现一致。

## 4. 判据四:条件相容聚合(v12 文本,自包含;v11 落字三处保持,
v12 补一处轴归属)

- **快照一致性**:路径上下文快照由已验证父对象派生,派生先验
  validate 父对象;快照的 covered_requirement_signatures 与已记录
  的 per_requirement 评估行**双向对应**(签名↔行双向:删行/改
  签名都拒)。**v11 落字(复审 §6 判据四"孤儿方向",更正 v10
  方向)**:两个方向的处置分写 —— **已有必要要求绑定旧作用域但
  无按签名快照 ⇒ unknown**(证据不足,不猜);**评估行/签名无
  对应要求或集合不一致 ⇒ `context_snapshot_inconsistent` 拒**
  (引用完整性/一致性失败,不是 unknown;v10 把后一种写成 unknown
  且方向写反,以本版为准)。
- **内容身份**:PathContext 内容身份同源重算;**两种不可变机制
  分写(v9 落字)**:Requirement/ConditionFact 由 frozen(嵌套冻结)
  强制;PathContext 本体**非 frozen**,其不可变性由消费前 validate
  的内容身份同源重算兜底(就地改语义字段保留原 context_id ⇒
  `context_content_identity_mismatch` 拒)。不得把两种机制写成同一
  类不可变;任何派生/评估/审核入口消费前必须先 validate(绕过
  validate 直读字段属违约)。**v11 落字(复审 §6 判据四"入口
  限定")**:已**强制** validate 的入口 = 恢复/from_dict、derive 的
  父对象、audit 直接对象;`assess_conditions`/`assess_candidate_
  conditions`/`route_assessment` 自身**没有**该调用,**需上游纪律**
  (新 S3b 必须接真实守卫,不以上游纪律替代入口强制)。
- **重建半边(v11 落字,复审 §6 判据四)**:合法**新内容重建**的
  语义 context 使用**新 context_id** 并保留 `parent_context_ref`
  链(旧引用不复用)—— 新内容重建**不是篡改**,不得被
  content_identity 判据拒绝;篡改是"旧 ID + 新内容"的组合(见
  上文 mismatch 拒)。
- **三分与矛盾**:条件评估三分为 satisfied/conflict/unknown;已知
  事实与要求冲突为**单向矛盾**(conflict 只阻止当前场景,不反推
  全局)。**v12 落字(复审 R3 §6⑥,known_absent 轴归属)**:
  known_absent 类缺席语义**属本条件评估轴,不是元素账判据** ——
  实体缺席/非物种字符串同值 ⇒ conflict;非物种字符串异值
  known_absent 或未列出 ⇒ unknown;数值/区间缺席 ⇒ unknown
  (numeric_absence_semantics_undefined,不跨值域泛化物种字符串
  规则;该句与判据二 v12 落字同源,两处一致表述)。
- **场景评估口径**:文献观察环境、矩阵"污水"标签、工具隐式
  O2/H2O、transformation_class 标签都**不能**构造当前条件事实;
  请求 condition_compatible 不是已相容;空要求/未知覆盖不自动
  compatible(相容判断需实际评估)。
- **行↔签名对应的契约前提**:绑定字段一经冻结不得后改;变更须
  走新评估/新快照(将来引入要求可变性,旧快照整体拒绝是故意
  fail-closed,不当 bug 修)。

**请评审**:(a) v11 三处落字(孤儿方向更正/入口强制与纪律清单/
重建半边)与 v12 known_absent 轴归属补写是否准确、与 v10 的差异
是否如实登记;(b) 分写/口径其余文本与实现一致(v9/r2/r3/r4 无
进一步变化)。

## 5. 判据五:供体一致性诊断(v12 文本,自包含)

- **判定基础 = 实际净变化集**:供体编辑一致性以键 diff ∪ 电荷/
  立体/同位素变化集的实际净变化判定(含 bond_stereo_change 与
  键级立体入变化集;非四面体公开列项按标签类型分开),不采信
  声明的"编辑列表"与实际不一致的自报。**v11 落字(复审 §6
  S3b 行)**:区域净变化不认证**供体模板/机制**(净变化判定是
  表示层契约,不是机理证明);**图等价不是酶识别**;
  legacy_cn_match 仅**旁证**(不是反应身份判定)。
- **奇偶构型比较与非四面体 unsupported**:四面体手性按奇偶
  (parity)构型比较;非四面体立体(_at 等)公开列
  unsupported(不冒充核实也不静默拒);E/Z 与非四面体轴分开。
- **联合映射三类支持范围**:原子映射支持范围(完全/部分/缺失)
  与歧义映射分列;缺/歧义映射 ⇒ 中心 unknown(partial),不猜
  对应。
- **中心属性披露/strict 同源**:诊断输出的中心属性(参与物/键/
  电荷/立体)按 proof_scope 分轴披露;strict 目标比较与
  strict_identity_of 同源(与身份键同一推导,不是第二套)。
- **证据载荷内嵌**:check 结果(含 proof_record)内嵌进审核证据
  载荷(不可变、入口身份复算);跨假设未绑定 proof ⇒ 中心
  unknown;篡改自报与复算不一致 ⇒ 契约异常(本次无成功
  admission;见判据三 v11 落字)。
- **四个原始字符串入口与工厂同源守卫**:供体诊断的四个原始结构
  串字段与工厂共用判据一第 2 条输入守卫(未登记 CX 项 ⇒ 契约
  拒绝)。
- **声明–执行净效应对账 + 镜像终态归一**:声明编辑与实际执行
  对账(镜像活 ID 表 + 前置复核);终态序列化与冻结执行器对齐。
- **8b 拒绝与失败早退(v9 落字,精度保持;v12 补一处)**:失败诊断
  是**三个**判定字段 reaction_center_match/strict_target_match/
  legacy_cn_match 均为 None、`diagnostic.center_evidence={}`;
  **converter 仍返回版本/来源元数据与 center_match=None**(不是
  "四轴 None",也不是"converter 整个 evidence 为空")。None=未
  评估,**不等于通过**(三个 None 不是通过;legacy_cn_match 单
  True 也不是任何 R 行的通过依据);`execution_ok=False` 早退
  路径不解析三字段亦不消费其任何轴,无 verified 泄漏面。拒绝为
  契约性拒绝 ⇒ 本次诊断/审核不产生任何轴结论与 disposition;
  调用方不得吞异常后按 retain/verified/any-R 行记录(异常≠处置
  行)。两处表述边界:拒绝原始 `r` 不构成"已证实实验精确消旋";
  裸指定 SMILES 只声明表示事实,不称实验纯品/对映纯;strict=
  True = 同一化学身份,不是同一样品/同一立体纯度。
  **v12 落字(复审 R3 §6"两种潜在扩大"之 (a),失败 diagnostic
  与下游 audit 分开)**:失败 diagnostic 的三个 None/`center_
  evidence={}` **不等于**下游 audit 所有轴/所有 R 行都不存在 ——
  converter 仍返回版本/来源元数据与 center_match=None,缺
  scope/proof 进 audit 中心 UNKNOWN;**同一次 audit 仍可以给
  其他轴 verified 并由决策表处置**(中心 unknown 与其他轴的
  verified 不互斥,按决策表首中规则合成整体处置);不得把
  "诊断失败"扩大成"整个 audit 无结论"。同源重放/输入守卫也
  **不证明来源真实性、历史执行、酶识别或供体机制**(②之 (b),
  同类口径)。四个原始字符串守卫限定**执行成功路径的解析之前**
  (§6④;失败早退未解析)。
- **8d caller 义务(如实披露,仍未闭合)**:S3 新 caller 必须承担
  "让 AuditContractError 逃逸并中止本次 admission 计算/提交"的
  义务,不得吞异常继续。**S3a/r4 未新增生产 caller(生产链属
  S3b)**,该义务尚未被执行证据闭合;当前静态证据(10 个
  AuditContractError 抛点全部在 audit.py、无 enclosing 宽捕获
  try-body、check_edit_against_donor 唯一源内调用无 try 祖先)
  不是动态安全的通用证明。S3b 交付生产链时以实际调用与宽捕获
  负控(异常正常逃逸 + 合法正控)闭合。

**请评审**:(a) 8b"三个 None + converter 元数据"表述与早退边界
是否准确,v12 落字"失败 diagnostic 与下游 audit 各轴分开"是否
如实(中心 unknown 与其他轴 verified 不互斥);(b) 8d"未闭合但
如实披露"作为 S3a/r4 边界是否可接受(闭合路径 = S3b caller +
回归测试);(c) v11 落字(净变化不认证模板/图等价非酶识别/
legacy_cn_match 仅旁证)与 0c 清单是否足以防止把不存在的分支名/
错误版本/错误异常处置再次当作读码事实;(d) 其余条款展开文本
是否与实现一致。

### 0c-v13. S3a 复审 R4 §8.5 七条 P2 落字(受审;v13 补入)

S3a 复审 R4 §6/§8.5 的落字要求,本版按实现核对后采信为规则文字:

1. **11+1 父绿精度**:S3a r4 父基线 12 绿 = **11 合法行为正控 +
   1 已关闭的坏输入拒绝控制**(9 clean 入口、1 合法策略状态控制、
   1 合法失败生命周期、1 sent/response 已拒未知状态保持控制);
   不是"9 合法 + 3 既有坏输入"。历史交付该处误记已更正。
2. **各入口 kind/reason 层次**:工厂/strict 入口外层
   ChemicalStateError、`detail.kind` ∈ {unregistered_cx_class,
   unparseable_smiles};恢复入口外层 ChemicalStateError、`detail.kind`
   ∈ {raw_structure_rejected, state_structure_unparseable}、内因读
   `detail.reason.kind`;公共 writer 外层 Ppv1StateContractError。
   三字面别名 and/or/rad 落兜底显式拒绝,不是输入 token。
3. **未知系数使元素/电荷账亦 unknown**:`full_known` 不成立时
   元素账与电荷账直接记 unknown(不只是 coverage 的
   unknown_coefficients);verified 只覆盖**调用方声明清单**的数值
   闭合,两侧对称漏写参与物在本轴不可见。
4. **omission 及声明清单边界**:omission_pattern_matches 不证明
   实际缺该物质、不含电子/质子计量;completion_surplus/deficit 拿
   未覆盖参与物的元素和与结构重推导的 λ_s×Δ 对账,而
   coefficient_binding_mismatch 只比声明系数绑定(两者分写,不
   互相冒充)。
5. **R2b/R1 对象范围**:R2b 表示契约违反由调用方传入
   contract_violation 触发(不传则该分支不可达;S3b 生产 caller
   在 audit 抛 AuditContractError 时中止本次 admission/提交,不把
   契约异常降级为 R2b/R 行);R1 为防御行 —— 坏结构通常在首消费
   守卫即异常逃逸,不落任何 R 行。
6. **条件事实真实性**:assess_conditions/assess_candidate_
   conditions/aggregate_environment_fit 的满足/冲突是**给定事实集
   相容性**,不核事实真实性;S3b 真实 caller(生产链/驱动)接
   context 首消费守卫(from_dict 内容身份核验;场景转换须显式
   source_ref,不从观察/标签/工具隐式条件造当前事实)。
7. **异常不当 R 行**:AuditContractError(类型违约/复算不一致/
   proof_record 形状不完整)是结构化契约拒绝,**不落 R 行**;S3b
   生产 caller 不吞该异常成 verified/R6/成功提交(宽捕获下零
   写入)。复合探针在首处拒绝后,未执行的内部段不报通过。

### 0c-v14. Codex S3b 复审 §6 精度更正落字(受审;v14 补入)

Codex S3b 复审 §6 对 mimo v13 回应的互证裁定,本版按 r2 源码核对
后落字(旧回应原文不回写):

1. **0d.4 措辞精度(strict False 的行话)**:strict 目标偏离 ⇒
   中心轴记 **violated**(决策表走 R5v;audit.py:1188 一带),
   不是"至少 unknown";strict None ⇒ unknown。原 0d.4"strict
   False ⇒ 至少 unknown"按此更正(violated 强于 unknown;弱读成
   unknown 会错走 R5)。
2. **λ_s×Δ 对账复算式源位置**:completion 类差额核算的源式在
   audit.py:973-979 一带(lambda_s×delta_pos/delta_neg 进
   _completion_violations 的 product/reactant 两侧);mimo v13 回应
   "未确认"是其只读采信边界,不是源码缺该式。
3. **0d.8 行号更正**:公开分流代码在 `workflow/runner.py:214-228/
   305-320`(mimo v13 回应误写 runflow.py:214-223/315-319;runflow
   同区间是 reconcile/drive)。r2 起关键行号以 r2 源码为准:
   窄捕获 runflow.py:955-972、失败短路 production.py:399-404
   (未变)、恢复隔离 search.py:1155-1224、冻结计划 runflow.py:
   211-321。
4. **测试集合与数字精度**:mimo v13 的"待执行验证"执行类数字由
   r2 独立执行闭合(ppv1 全量 851→**871**、G01 1453→**1473**、
   父红分类见 §6);数 test 函数不证明参数化绿 case;"父旧 64 绿
   与当前新 64 是两个不同集合"的口径沿 S3b 复审 §2 保持,不重复
   相加;R4 父绿 11+1 历史标签不混入本轮数字。
5. **mimo v13 的 0d.5/0d.7/0d.1/0d.2 披露建议**:已按 v13 建议与
   复审 §6 落进 0d.1(产品来源=冻结池声明结构)/0d.2(闭合范围=
   AuditContractError,三类 RuntimeError 逃逸面如实披露)/0d.5
   (持久上限来源=预约行+幂等键)/0d.7(默认 0 轮 = 首次格式错误
   即结构失败停止;scripted 反馈重试网络 0)。

### 0c-v15. Codex S3b-r2 复审 §2/§5/§6 精度更正落字(受审;v15 补入)

Codex S3b-r2 复审对 r2 交付与 mimo v14 回应的互证裁定,本版按
r3 源码核对后落字(旧交付/旧回应原文不回写):

1. **r2 父基线红绿分类更正**:r2 交付"15 行为红"应更正为
   **13 行为红 + 2 形态红**;更新的 3 个既有文件"54 绿"应更正
   为 **52 绿**(合计 18 failed/57 passed 保留)。两个形态红的
   父上内部到达精度:`test_s3b01_frozen_plan_tamper_integrity_
   failure` 在父没有新 frozen_plan.json、停在 `is_file`,**未
   执行篡改和恢复**;`test_s3b03_transition_enqueued_crash_
   window_closed` 在父已执行公开恢复并核转换 done,但在
   pending_followup 缺失形态断言停止,**后面的新上下文核对未
   执行**。不能说二者都跑完旧行为,也不能把后者写成根本未
   resume。r3 本批不更新既有测试文件,父基线 = 新 r3 文件
   (5 行为红全为"未结构化拒"型,父上 public resume 完整执行,
   失败点在拒绝断言,非早停内部段)。
2. **abstain 空池父红更正**:r2 交付 §1.5 将
   `test_s3b05_model_abstain_empty_pool_legal` 称为父绿不准确
   —— 父上请求数 0≠1 是**行为红**;当前合法控制通过。函数名中
   的 positive/negative 不是实际红绿标签。
3. **r2 证据 HEAD 采集时序**:r2 实施时点 HEAD 为 c1211183 +
   脏工作树(实施未提交),最终受审提交为 **2bedfc0**;不能把
   前者说成当前 HEAD。r3 实施时点 HEAD = 2bedfc0 + 脏工作树
   (本批变更未提交),同口径登记。
4. **novel 来源标签 P2 落字**:decide 的 prepare 传入 model
   proposal 的 source_refs,expand 重建未传而用默认
   synthetic-pool-spec;实际 event appearance 使用后者。hyp ID
   不受这些 refs 影响、冻结 plan 含原响应且 action
   proposal_context 保留,来源可追溯,未发现身份洗坏/错误
   verified。**不宣称来源标签逐字全链一致,也不宣称已认证现实
   来源**;冻结前清理误导文字(P2 不另加阻塞)。
5. **audit.py:2980-2981 旧注释**:docstring 仍写"strict False ⇒
   至少 unknown",与 0c-v14.1 的 violated/R5v 落字不一致 —— 列
   **冻结前 P2 文本同步项**(现行实现 1188 一带为 violated→
   R5v;不改行为)。
6. **行号拆分(mimo v14 建议采纳,r3 源码为准)**:"冻结计划
   runflow.py:211-321"拆为:**冻结计划持久化/读取 229-272、
   后段锚定核对 `_verify_frozen_plan_binding` 274-390、执行
   会话锁(`_DriverSession`)392 一带起**;勿把锁段误标为计划
   段。0d.8 一般 followup 的 B4 补齐函数指认:
   `_Driver.reconcile_followups`(r3 源码 runflow.py:500-558,一般
   产物补齐)与转换补齐 `_ensure_transition_followup`:
   577-615;`store.verify_event_attachment_content` 在
   store.py:1988(只核附随内容/plan/projection,不单独当
   strict state 身份证明)。
7. **r2 交付数字口径**:新 r2 20 项已含在 871 全量内不另加总
   (v14 已写;r3 的 8 新项已含在 879 全量内同口径);父形态红
   与行为红分开统计;历史 871/1473 与本轮 879/1481 各自单列不
   混计。

## 6. 程序证据与状态(程序事实,不替代化学判断;执行类声明待验证)

- **本批(v19 / S4 回修 r2,隔离源正式执行,执行细节由主会话安排
  的 Codex 复审另行验证)**:ppv1 全量 **962 passed/0 skipped/
  0 failed exit 0**(951 r1 存量 + 11 新回修回归,36 文件;隔离源含
  vendor/普通 dependingv3 同级副本、父/子同一 V3_CODE_ROOT;两次
  准备事故(资产缺失/复跑目录预建冲突)如实保留,唯一有效重试为
  正式数字);隔离全量非 slow(G01 同口径 deselect)**1564 passed/
  8 skipped/17 deselected exit 0**(仓内树不 deselect 为 1573
  passed/16 deselected);G01 安全隔离(新控制器,**296** 输入 =
  295 + 1 新测试文件,执行后逐文件 SHA 复核 0 失配)= **1564
  passed/8 skipped/17 deselected exit 0**(8 skip = 5 真实评价 +
  1 v4 + 2 phase_d;17 = 16 slow + 1 明确排除;1553(r1)→ 1564
  各自单列不混计);直接父 0dd35d1 detached 稀疏 worktree 同字节:
  新回修文件与两份字面量更新文件 **11 红 = 7 拒绝缺失行为红 +
  1 字段红 + 3 版本字面量红(0 collection 红)**,41 合法正控绿;
  legacy 字节专项(当前树 vs 父 0dd35d1)两 run 四产物**逐字节
  一致**,52 份非 pollutant src 文件 code_identity 聚合两树一致;
  R2 复审反例逐字复跑结论见 0i.3;
- 规则级测试(v17 / S4b 历史口径,供对照):ppv1 全量 **932
  passed/0 skip**(914 存量 + 18 新 S4b;仓内树)与全量非 slow
  **1543 passed/16 deselected**;直接父 fc40605 上新 S4b 文件
  18 collection 红 + 2 版本字面量红 + 21 合法绿;G01 294 输入
  1534/8/17;详见 0g 节与 S4b 交付书——以下 18 项覆盖清单沿
  v17 保留:
  manifest 结构/全量事实覆盖(共同产物/备选/来路/条件/audit/
  deferred/预算/停止/endpoint + 15 表 graph facts + 四类 artifact
  引用)、G02 七测(①同进程+独立子进程重复导出字节一致 ②崩溃
  恢复后重复导出字节一致 ③导出再读取=原生权威 ④源图变化过期
  (动作漂移 ⇒ endpoint 先拒 + 新增事实行 ⇒ export_stale,旧
  文件保全+新 digest 新目录)⑤策略变化过期 ⑥篡改/引用断裂/
  缺失结构化失败 ⑦自洽重写不可洗白)、同 digest 不同字节重导出
  拒、v3 投影 lossy 标记/原生引用/损失清单/不可投影摘要、逐
  事件步骤不按 CN 合并/不编造终点/CO₂ 不相加、投影确定性+反查+
  正向引用断裂拒、反向污染负控(零 DB 写入+入口拒+模块无写入
  入口)、完整公共链(崩溃→resume→导出→投影→读取→replay 零
  新写+旧文件保全+scripted 网络 0)、endpoint/stop 引用断裂拒、
  空池 run 导出与投影、投影不可变);另有全量非 slow
  **1543 passed/16 deselected**(含 legacy/export_v3 全量回归,
  当前树,exit 0);
- **本批新增 19 项回修回归覆盖清单(v18)**:S4-C01 必要条件缺失/
  显式 unknown 双参数化(start/resume/记录全文/阻断原因/derived_
  from 摘要/严格首消费/native 导出/v3 摘要同值)+ 已知满足与
  无必要条件正控 + 冲突反例 + 上下文损坏首消费拒;S4-C03 child
  retrieve soutc 全文聚合 + manifest 引用 + 坏必要 soutc build/
  read 双拒 + 空键不产引用;S4-C02 manifest 四例 mutation core
  复算拒 + 自洽漏必要引用集合闭合拒(单项/全部)+ 自洽换 run/
  版本/策略绑定拒 + 缺 H07 逐行拒;S4-C04 假 native 构建拒 +
  projection-only 自洽改内容读取拒 + 混搭 reference 拒 + ledger
  联动原生首消费拒/还原正控 + 完整公共链一致性/幂等/网络 0;
- **legacy/export_v3 冻结字节专项(本批新增)**:当前树 vs 直接
  父 fc40605 detached worktree,同字节探针脚本(两组合成 legacy
  run:单事件多产物/两事件竞争同父+deferred)分别构建并导出
  ⇒ predictions.jsonl + export_metadata.json **四产物逐字节一致**
  (SHA256 两两相等);52 份 legacy code_identity 文件聚合保持
  `18007e6a7cc239606eb30921f91045540446a7d7298108be30d47fce
  2f1374d6`(与 S3b-r2/r3/S4a 复审核验值一致);
- 基线红绿(直接父 fc40605 detached worktree 同字节):新 S4b
  文件 **18 collection 红**(`pathway_v43.pollutant.native_export`
  模块缺失;implementation missing 如实登记,未 stub/未改
  import/未弱化期望);更新的 test_ppv1_profile.py **2 版本/
  阶段字面量红**(profile-16 与 delivered_stages 字面量;父合法
  实现 profile-15)+ **21 合法正控绿**;0 行为红;
- G01:安全隔离工程回归(R7 路径白名单 + R8/S3a/r2/r3/r4/S3b/
  S3b-r2/S3b-r3/S4a/S4b 输入,**294** 项输入(291 s4a_r1 + 3 新
  S4b:native_export.py/v3_projection.py/test 文件)SHA 前后一致;
  不复制 evaluation/金标/题面/封存/v4;固定 PYTHONPATH/空
  BBD_DATA_ROOT/V3_CODE_ROOT/V43_ASSET_ROOT/DEPENDING_V3_ROOT)
  ⇒ **1534 passed/8 skipped/17 deselected**,exit 0(8 skip =
  5 真实评价依赖 + 1 v4 对照源 + 2 phase_d 派生 metadata;
  17 deselect = 16 slow + 1 明确排除 export 用例;历史
  R7 1110/R8 1138/S3a 1196/r2 1250/r3 1299/r4 1389/S3b 1453/
  S3b-r2 1473/S3b-r3 1481/S4a 1516 各自单列,不混计;1534 =
  1516 + 18);
- 契约族:**本批(v18)升级** endpoint **ppv1-endpoint-1 → -2**
  (S4-C01:记录新增 route_condition_assessment 字段 + 必要条件
  同源评估)、endpoint 派生策略 **ppv1-endpoint-policy-1 → -2**
  (必要条件 unknown/conflict 阻断输入)、原生结果对象
  **ppv1-native-result-1 → -2**(S4-C03:soutc 键独立枚举)、
  原生正式导出 **ppv1-native-export-1 → -2** 与导出策略
  **ppv1-native-export-policy-1 → -2**(S4-C02:core 复算 +
  run/版本/策略绑定 + 必要引用集合闭合)、v3 有损投影
  **ppv1-v3-projection-1 → -2**(S4-C04:构建与首消费验证真实
  原生来源/adapter 同源复算);profile **ppv1-profile-16 → -17**
  (契约注册面;旧 run 按版本门拒,不跨版本续跑);search 保持
  **ppv1-search-6**、search-limits 保持 **-3**、format-feedback-1
  保持(默认 0 轮)、model-proposals 保持 **-2**;store 保持
  **ppv1-store-10**(无新表)、执行流保持 **ppv1-runflow-5**
  (接线不变,投影读回增加可选 ledger 联动)。FROZEN_PLAN_VERSION
  保持 ppv1-frozen-plan-1。**production.py 本批零改动(生产化学
  链与 AuditContractError 义务字节不变)**;以下为 v17 历史登记
  沿革:search 保持 **ppv1-search-6**、search-limits 保持
  **-3**、format-feedback-1 保持(默认 0 轮)、model-proposals
  保持 **-2**;endpoint **ppv1-endpoint-1**、endpoint 派生策略
  **ppv1-endpoint-policy-1**、原生结果对象 **ppv1-native-result-1**
  沿 S4a;**新增** 原生正式导出 **ppv1-native-export-1**、导出
  策略 **ppv1-native-export-policy-1**(固定序列化/命名/无时间
  戳/不可变规则,无用户可配项)、v3 有损投影
  **ppv1-v3-projection-1**;store 保持 **ppv1-store-10**(导出为
  run 目录文件,无新表);profile **ppv1-profile-15 → -16**(
  新契约注册 + delivered_stages 增 S4b-export;两个既有字面量
  测试为本批唯一既有测试改动,如实披露);执行流
  **ppv1-runflow-4 → -5**(公共 start/resume 在 S4a 派生后接
  正式导出 + v3 投影 + 双首消费读回;单一事实源常量移入 profile
  注册)。FROZEN_PLAN_VERSION 保持 ppv1-frozen-plan-1。
  **production.py 本批零改动(生产化学链与 AuditContractError
  义务字节不变)**;
- **legacy 影响:本批零改动**(git diff vs fc40605 仅
  pollutant/native_export.py(新)/v3_projection.py(新)/
  native_result.py(引用索引重构:非事件调度结论 artifact 聚合
  修正 + 单一来源抽取)/runflow.py/profile.py +
  tests/test_ppv1_s4b_export.py(新)/test_ppv1_profile.py;
  52 份 legacy code_identity 文件与 production/chemstate/
  path_context/hypothesis/events/audit/search/queue/
  model_protocol/runner/store 共享核心父↔当前逐字节一致);
- **判据冻结状态**:ppv1-criteria-v1 已冻结(2026-10-08 用户
  拍板;冻结稿 = `docs/POLLUTANT_PATHWAY_CRITERIA_FROZEN_V1_
  2026-10-08.md`,底本即本文件 v15,冻结批次在 adf0287 只读
  复核行号)。v16/v17 **不改判据正文**(见 0f.11/0g.12 语义
  未改变声明);冻结稿 §8 要求后续源码变更重锚行号 —— 本批
  改动的 runflow/profile 行号继续漂移,属工程登记面,待下次
  判据版本(如有)统一重锚;判据行为互证以 914 存量零改动
  全绿 + 逐字节 diff 为程序证据;
- 参考(外部常识,非本仓资产):RDKit Book(CXSMILES 扩展/
  增强立体/立体化学章节)、rdCIPLabeler API;CXSMILES 解析器
  行为经 Release_2026_03_6 源码取证与实证用例校准(冻结时已由
  Codex R3 复审独立执行证成);本批无新 RDKit 依赖面。

## 7. 请求的回复格式

对每条判据(含 0d 节八条、0e 节六条消费契约,0c-v13 七条/
0c-v14 五条/0c-v15 七条落字,0f 节 S4a 十一条 endpoint/原生结果
表述,0g 节 S4b 十二条正式导出/v3 有损投影表述,以及 **0h 节
S4 回修 r1 七条四组消费契约闭合表述**):
1) 结论(同意/不同意/有条件同意+条件);
2) 可直接落进规则文字的修改建议;3) "程序上诚实但化学上误导"
风险点。逐条表态,不接受总体评价式回复。执行类声明一律标
"待执行验证"。引用 0c/0d/0e/0f/0g/0h 清单之外的事实(分支名/
版本/异常处置)时必须先给出可复核的源位置,否则按不采信
处理。
