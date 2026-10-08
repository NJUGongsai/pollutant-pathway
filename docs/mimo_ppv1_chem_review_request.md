# mimo 化学评审请求:pollutant_pathway_v1 化学判据(S3b 回修 r2 版 v14)

- 日期:2026-10-08(S3b 回修 r2 批次;替换 2026-10-08 v13 请求。
  v13 送审快照已存 `docs/review_evidence/ppv1_s3_impl_2026-10-08/
  s3b_r2/mimo/mimo_ppv1_chem_review_request_v13_sent.md`(字节同
  刚送审的 v13);旧回应 r5–r13 原样保留不覆盖)
- 触发点:AGENTS.md mimo 三触发点之 1(需评判化学结构时——冻结或
  发布前)
- 评审对象:S0–S2 判据(ppv1-*-8 契约族)+ S3 消费契约的 S3b-r2
  更新(ppv1-search-6 / ppv1-store-9 / ppv1-profile-14 /
  search-limits-3 / format-feedback-1 / model-proposals-2 /
  runflow-2);**判据尚未冻结**
- 与 v13 的差异来源:Codex S3b 复审未放行
  (`POLLUTANT_PATHWAY_S3B_CODEX_REVIEW_2026-10-08.md` §4 六组 P1
  S3B-01~06 + §6 mimo v13 互证裁定)+ S3b-r2 回修交付。r2 **不新增
  化学判据或门禁**;新增的是**恢复/调度/协议消费契约文字**(0e 节
  六条:冻结输入身份、坏 artifact 恢复隔离、后续集合完整性、执行
  会话互斥、novel 独立假设消费者、blocked 持久披露)与 0c-v14 节
  (复审 §6 的精度更正落字);受审文字为 0e 全部、0c-v14 全部、
  0d 按 0c-v14 更正后的表述、§6 数字与契约版本更新
- 自包含性:本版展开必要规则全文,不以"同 v7/v8"缩写引用历史;
  规则级表述与合成规则级夹具,无任何金标/题面/封存逐题数据;由
  用户转交,回复原文落盘 `docs/`;实施 agent 不调用模型,只读/执行
  类声明一律待执行验证

## 0. 背景(一段话)

S0–S2 判据 v8 经 R8 独立复审放行;S3a r4 放行搜索底座;S3b 首批
交付调度/生产链/PPV1 分流后,Codex S3b 复审**未放行完整 S3**
(P1=S3B-01~06:冻结输入恢复消费、坏 artifact 恢复消费、后续调度
集合、公开恢复执行权、novel 提案生产消费者、停止报告必要原因/未
探索对象;化学生产链与异常义务已验过)。本批(S3b-r2)按复审
§8 有限回修:计划/池/必要输入 start 持久化为冻结来源且 resume 内容
绑定;recover 的坏 artifact 裁定接到 driver 执行门(隔离不重执行);
后续/转换集合从已核事件/计划/转换事实逐对象幂等补齐(转换附随一次
冻结);公开 start/resume 以 run 目录 flock 互斥(崩溃 OS 释放、
新进程接管);novel 池外提案须携带完整 reaction_spec 反应内容并
作为独立假设走固定工具→audit→admission→submit(空池仍组装底物
档案并消费模型响应);blocked 原因/对象持久行由公开 stop 同源派
发。工程数字:ppv1 全量 **871 passed/0 skip**(851 存量 + 20 新
r2);直接父基线 c1211183 同字节对照(新 r2 文件)**15 行为红 +
5 合法正控绿**、0 collection 红(父已含全部 S3b 模块),更新的
3 个既有文件 1 版本翻转红 + 1 字段形态红 + 1 行为红;G01 安全隔离
**1473 passed/8 skipped/17 deselected**(287 输入)。目标不变:
可能降解路径与条件相容路径的诚实表示;unknown 不升格;verified 不
靠模型或调用方自报字符串;账平、物种同 CN 或一份正确局部诊断不能
代替整条声明的覆盖与追溯。停止不是化学终点;搜索记录/合成图不是
终点结论。工程数字是合成规则级契约结果,不代表 dev(B1 环境中间
步骤)或 298(RHEA 通用酶学)科学性能;判据未冻结;S4/S5 未启动。

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

## 0e. S3b-r2 恢复/调度/协议消费契约(受审表述;v14 新增)

S3b-r2 按 Codex S3b 复审 §4 六组 P1 的最低回修实施。以下六条全部
是**恢复/调度/协议的消费契约**(契约随 ppv1-search-6 /
ppv1-runflow-2 / ppv1-model-proposals-2 登记;**不是新化学判
据**;生产化学链 production.py 本批零改动):

1. **冻结输入身份(S3B-01)**:计划(池/模型响应/转换意图/激活
   指令/条件事实)在 start 时持久化为**冻结输入来源**
   (run-plan/frozen_plan artifact,plan_digest 内容绑定;读取经
   H07 完整性包装 + 内容身份核验)。resume 的 retrieve/decide/
   模型请求/expand/followup/转换全部消费该冻结来源:**旧任务不
   消费新输入**;不传 plan ⇒ 沿冻结输入(**缺输入不变空池**,
   不当 no_local_candidate 合法完成);传入计划内容不符 ⇒ 结构
   拒(frozen_plan_mismatch;差异须显式新 revision/新任务登记,
   不复用旧裁决键);冻结计划被篡改 ⇒ 完整性失败保全。第二层:
   retrieve 任务 plan_digest 与 decide 冻结 pool_digest 同源重算
   核验(纵深防御)。
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

## 6. 程序证据与状态(程序事实,不替代化学判断;执行类声明待验证)

- 规则级测试:ppv1 全量 **871 passed/0 skip**(851 存量 + 20 新
  r2,全部合成夹具;20 项覆盖六组 P1:冻结输入三负控一同计划正控/
  坏 bundle 两负控(隔离不重执行、独立任务继续)/部分 followup 与
  两转换窗口三负控 + 0/全部与三产物正常正控/双进程并发恢复互斥
  (真实工具入口计数 + barrier)/novel 三负控一正控/零深度复合与
  重复 resume 两负控两正控;四崩溃子进程硬杀等存量 851 保持);
- 基线红绿(直接父基线 c1211183 detached worktree 同字节,父已含
  全部 S3b 模块 ⇒ **无 collection 红**):新 r2 文件 **15 行为红 +
  5 合法正控绿**(正控 = 同计划 B3 恢复/B4 0-followup 窗口/三产物
  正常/合法非零/空池,父亦绿;早停内部段不报通过);更新的 3 个
  既有文件 **1 版本字面量翻转红(profile-13→14/search-5→6)+ 1
  字段形态红(父 blocked 条目缺 action_id 键,底层为无持久行)+
  1 行为红(父接受无 reaction_spec 的 novel)**;
- G01:安全隔离工程回归(R7 路径白名单 + R8/S3a/r2/r3/r4/S3b/
  S3b-r2 输入,**287** 项输入(286 r1 + 1 新 r2 测试文件)SHA 前
  后一致;不复制 evaluation/金标/题面/封存/v4;固定 PYTHONPATH/空
  BBD_DATA_ROOT/V3_CODE_ROOT/V43_ASSET_ROOT/DEPENDING_V3_ROOT)
  ⇒ **1473 passed/8 skipped/17 deselected**,exit 0(8 skip =
  5 真实评价依赖 + 1 v4 对照源 + 2 phase_d 派生 metadata;17
  deselect = 16 slow + 1 明确排除 export 用例;历史 R7 1110/R8
  1138/S3a 首批 1196/r2 1250/r3 1299/r4 1389/S3b 1453 各自单列,
  不混计;1473 = 1453 + 20 新 r2);
- 契约族:search ppv1-search-5 → **ppv1-search-6**(blocked 持久
  行 + 恢复隔离 + 转换附随一次冻结的消费语义;计数键/默认/范围/
  单位未动),profile -13 → **-14**(contracts 登记);新增登记
  model 协议 **ppv1-model-proposals-2**(novel 须 reaction_spec)
  与执行流 **ppv1-runflow-2**(冻结输入绑定/会话互斥/恢复门/
  novel 消费接线);store 保持 **-9**(无新表:blocked/隔离复用
  search_actions 行,冻结计划/底物档案走 artifact,转换附随复用
  payload);search-limits 保持 **-3**;format-feedback-1 保持
  (默认 0 轮);**production.py 本批零改动(生产化学链与
  AuditContractError 义务字节不变)**;
- **legacy 影响:本批零改动**(未触碰 workflow/runner.py 与任何
  共享 legacy 文件;legacy code_identity 聚合保持
  18007e6a7cc239606eb30921f91045540446a7d7298108be30d47fce
  2f1374d6;chemstate/hypothesis/events/audit/path_context/store
  字节与 S3b 父一致);
- 判据未冻结;v14 无新化学机制(判据一–五正文与 v12/v13 相同未
  改);受审文字:0e 节六条(恢复/调度/协议消费契约)、0c-v14
  五条精度更正、0d 按 0c-v14 更正后的表述、§6 数字与契约版本;
- 参考(外部常识,非本仓资产):RDKit Book(CXSMILES 扩展/增强
  立体/立体化学章节)、rdCIPLabeler API;CXSMILES 解析器行为经
  Release_2026_03_6 源码取证与实证用例校准;**冻结前须以执行
  证据复核 RDKit(锁定 2026.03.6)词法取证与放行正控的往返无损**。

## 7. 请求的回复格式

对每条判据(含 0e 节六条消费契约、0d 节八条消费契约与 0c-v13
七条/0c-v14 五条落字):1) 结论(同意/不同意/有条件同意+条件);
2) 可直接落进规则文字的修改建议;3) "程序上诚实但化学上误导"
风险点。逐条表态,不接受总体评价式回复。执行类声明一律标"待执行
验证"。引用 0c/0d/0e 清单之外的事实(分支名/版本/异常处置)时
必须先给出可复核的源位置,否则按不采信
处理。
