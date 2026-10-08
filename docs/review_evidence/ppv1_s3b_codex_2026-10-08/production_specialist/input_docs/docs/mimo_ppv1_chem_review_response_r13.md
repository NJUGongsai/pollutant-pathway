> **通道与 provenance（主会话 ZCode 记录，非 mimo 回应正文）**
>
> - 2026-10-08 凌晨（S3b 批次轮，按 AGENTS.md「评审-回修自动循环」轮内第③步自动送审）：请求经 **opencode 免费模型 `opencode/mimo-v2.6-flash-free`** 只读评审；opencode 会话 `ses_ee7ef98e4ffe4EywJgDo7V9mga`（标题 "mimo ppv1 v13 chem review"）。与手机 mimo 应用是否同一实例未经证实，采信按本通道口径区分。
> - 本轮一次运行完整输出（无断流、无续跑）。
> - 评审为**只读**：模型自述未执行任何命令/测试/探针、未修改任何文件，所引行号自称"本轮实际读码、可被抽查复读"（历轮曾有读码事实错误被 Codex 交叉核出，本轮行号一致性留 Codex 互证）。其中 PPV1 851 passed 已由主会话本机独立复跑证实（2026-10-08 凌晨）；G01 安全隔离 1453/8/17 为交付方隔离证据，留 Codex 复核。
> - 请求原文：`docs/mimo_ppv1_chem_review_request.md`（v13，S3b 批次版=完整 S3，自包含、无金标）。运行证据与原始输出：`docs/review_evidence/ppv1_s3b_mimo_2026-10-08/`。
> - 以下为 mimo 回应原文（仅清理终端控制字符，未做任何内容改动）。

---

---

## A. 判据一:分子身份

**1) 结论:有条件同意。** 条件:修正第 2 条示例的机制描述;`and/or/rad` 拒绝与 RDKit 往返句待执行验证。

**2) 修改建议:**
- 第 2 条示例 `atomProp:0.n,r` 的落字与读码不符:实现里该项在 atomProp 项扫描处即因三元组畸形返回 None(`_cx_scan_atom_prop_item`,chemstate.py:310-335),由分派处以 `registered_head="atomProp"`、`kind=unregistered_cx_class` 拒(chemstate.py:434-437 → 459-476);**并不是把 `r` 识别成一个独立的"未登记首头"**。建议二选一落字:(i) 换示例为"三元组完整 + 并列未知头"形态(`atomProp:0.n.v,r`),其路径才是无头上下文的未知首头拒(chemstate.py:456);(ii) 保留现示例但补一句:"该项拒时报 `registered_head='atomProp'`、kind 同为 unregistered_cx_class —— kind 名指'含未登记/畸形项',不表示 atomProp 本身未登记"。两种内因外层 kind 同名这一点,恰好与 2b 的"读内因"要求呼应,建议正文显式点名。
- `a:`/`o<N>`/`&<N>`/`^<N>`/Sg 登记头与"其余任何首头(含并列未知项)拒绝"与守卫分派逐条一致(chemstate.py:400-413、452-456),可原样落字。"三字面别名 and/or/rad 按 unregistered_cx_class 拒"与登记表(chemstate.py:259-266)读码一致,但**实际拒绝与 RDKit 2026.03.6 往返无损属执行证据,待执行验证**。
- (b) 入口清单:C2 划界读码一致 —— preview 为 `diagnostic_only`/`pool_unchanged`、不回流身份(pool_audit.py:295-302);首消费强制点为 from_dict/audit 直接对象(复用 `validate_state_object`,audit.py:474-475)。清单闭合**在读码范围内成立**;"搜索层全部消费入口"的完备性属可达性声明,待执行验证。

**3) 风险点:** `registered_head="atomProp"` + `kind=unregistered_cx_class` 的组合是"程序上诚实但化学上误导"的典型面:下游若只读 kind,会得出"atomProp 未登记"的错误化学印象;建议正文补内因读法,否则该错误码语义会被引用成规则事实。

---

## B. 判据二:参与物计量与元素/电荷核算

**1) 结论:同意**(v12 两处落字读码属实)。仅一处待补确认。

**2) 修改建议:**
- 系数句落字与实现一致:非法系数在构造/提交边界拒、`coefficient_binding_mismatch` 属覆盖轴且与 `completion_surplus/deficit` 分写(audit.py:922-933 vs 954-999),R5d 触发集合恰为 `{element_accounting, formal_charge_accounting}`(audit.py:227-228),可直接落字。
- `known_absent` 属条件评估轴的补写与判据四同源、两处表述一致,建议照抄同一段文字避免两处漂移。
- 建议补一句:`full_known` 不成立 ⇒ 元素账/电荷账记 unknown 的实现位置(audit.py:628-632 → 641-651、673-681),把"未知系数 ⇒ 账亦 unknown"从承诺变成可复核引用。

**3) 风险点:** 0c-v13.4 中"λ_s×Δ 对账"的**具体复算式我未在本轮读码中逐式确认**(读到的是 completion 类 violation 的分写位置 audit.py:954-999),该句按不采信处理直至给出行号或标待执行验证;若落字保留精确数学式而无源位置,属"程序上诚实但化学上误导"风险(读者会以为本轮已核过该式)。

---

## C. 判据三:admission 决策表与中心证据契约

**1) 结论:同意**,附一处精度修改(strict False 的行话)。

**2) 修改建议:**
- 决策表顺序读码一致:R1,R1b,R2/R2p,R2b,R3,R4,R5d,R5v,R5c,R5,R6,R7(audit.py:1643-1818),首中即决可落字。
- 中心证据分段与实现逐段对应,建议行号随文:proof 缺失→unknown(1085-1102)、完整性→契约异常(1110)、绑定不匹配→unknown(1131-1148)、覆盖缺→unknown(1164-1174)、center_match None→unknown(1175)、strict False→**violated**(1188)、strict None→unknown(1204)、True→verified(1214)。
- **0d.4 与判据三衔接处的精度**:正文写"strict False ⇒ 至少 unknown",实现是 **violated**(audit.py:1188;audit.py:447-452 的注释亦写 "False ⇒ violated")。建议统一落字为"strict False ⇒ 中心 violated(强于 unknown);strict None ⇒ unknown",防止把 violated 读成 unknown 后在决策表里错走 R5 而非 R5v。
- 三 None 早退先于四个原始字符串守卫(2553-2562 早于 2572-2592)、恒入/早退例外、v10 四点(a–d)读码一致,照录即可。

**3) 风险点:** "至少 unknown"是"程序上诚实但化学上误导"点:覆盖读者会把它读成"中心记 unknown、走 R5",实际 violated 走 R5v;同一审计产物两种 R 行归属差异会传播到下游处置统计。

---

## D. 判据四:条件相容聚合

**1) 结论:同意。**

**2) 修改建议:**
- 孤儿方向两分读码一致:绑定旧作用域且无按签名快照的必要要求 ⇒ **UNKNOWN**(path_context.py:1245-1269,并计入 1277-1278 的整体 unknown);快照签名↔行双向不一致 ⇒ 拒(1487-1499)。v11 方向更正可落字。
- 入口限定句建议按读码原样落字:**强制 validate 的两个调用点**是 audit 直接对象(audit.py:458)与 derive 父对象(path_context.py:2327);`aggregate_environment_fit`(989)/`assess_conditions`(1117)/`assess_candidate_conditions`(1172)**自身无强制调用**,维持"入口强制 + 上游纪律"的分写,不要写成三入口已强制。
- 内容身份两种机制分写(from_dict 同源重算 2078-2091 vs frozen 嵌套)、source_ref 必需(2328-2332)、phase freeze(2376-2400)读码一致。

**3) 风险点:** 若 0c-6 把"真实 caller 已接守卫"写成"三个评估入口已强制",会把上游纪律冒充入口强制 —— 这是本判据历史上 v10→v11 已更正过的同一类误导,勿在 S3b 文字里回潮。

---

## E. 判据五:供体一致性诊断

**1) 结论:有条件同意**(8b 准确;8d 作为 S3a/r4 边界可接受,但闭合描述需按 S3b 实际补一处;其余同意)。

**2) 修改建议:**
- **(a) 8b 补一条路径区分**:S3b 生产链中 `execution_ok=False` 在 **audit 之前**短路返回 method_failed(production.py:399-404),失败 diagnostic **不会进 audit**;"同一次 audit 仍可给其他轴 verified"只对"执行成功但中心证据/映射不足"的路径成立。建议落字:"工具执行失败 ⇒ 不调用 audit(production 399-404);中心证据不足但执行成功 ⇒ 调用 audit,中心 unknown 与其他轴 verified 并存"。两个 None 语义(None=未评估、converter 元数据仍在)读码一致(1085-1102、2553-2562)。
- 四个原始字符串守卫限定执行成功路径解析之前读码一致(2553-2562 早退在 2572-2592 之前),可落字。
- **(b) 8d**:作为 S3a/r4 "未闭合但如实披露"的边界我同意;且 S3b 已交付生产 caller(production.py:406-409 无 try、audit 抛点 10 处全在 audit.py),**但闭合描述不完整** —— 见 0d.2 的逃逸类缺口:窄捕获只接 AuditContractError(runflow.py:645),`ChemicalStateError`/`HypothesisContractError`/`ConditionContractError` 同为首次消费守卫抛出的 RuntimeError(chemstate.py:172、hypothesis.py:117、path_context.py:248),不在窄捕获与 drive 捕获集合(runflow.py:326-335)内。建议 8d 落字加:"已闭合范围= AuditContractError;其余契约异常类的驱动处置未在本批闭合,如实披露"。
- (c) v11 净变化/图等价/legacy_cn_match 三句与 0c 清单足以防旧错再犯,同意;RDKit 词法取证与往返正控**待执行验证**。

**3) 风险点:** 若 8d 写成"AuditContractError 义务已由 S3b 全面闭合",读者会外推成"全部契约异常均有方法失败结算"—— 实际三个 RuntimeError 类会让 run 以未捕获异常终止、**无 stop report、action 停在 claimed**(见 0d.2),这是本批最大的"程序上诚实但化学上误导"面:写入诚实,错误披露面不诚实。

---

## F. 0d 节:S3b 生产链与调度消费契约(八条)

### 0d.1 固定调用链与顺序

**1) 结论:有条件同意。** 条件:落字必须写明事件产物身份的真实来源。

**2) 修改建议:** 调用链顺序与读码一致(execute_atomtool_expansion production.py:396-398 → audit 406-408 → decide 409 → submit 456-459 → complete 465-467;render/execute_edits 真实调用于 281-282,无 mock 分支)。但"对工具已确定的产品只能引用(状态身份由结构内容派生)"易被读成**产物身份来自工具输出**——实际事件产物身份来自**冻结池 `spec.product_smiles`** 经 prepare_hypothesis 构造(production.py:196 → 417 → 434),工具执行结果只作为核验证据进入 donor/center 诊断。建议落字:"事件产物身份 = 冻结池声明结构(内容派生 state_id);工具真实执行输出是核验轴输入,不改写产物身份;两者不一致经中心轴落 unknown/violated,按决策表处置"。

**3) 风险点:** 现文字下,读者会以为"事件里的产物就是工具实际做出的分子";实际是规则级声明身份 + 核验轴结论并存。若两者不一致且落 retain_conditional(见 0d.2),事件仍以池声明身份提交 —— 该事实必须在正文可见,否则是化学误导。

### 0d.2 生产 caller 的异常义务

**1) 结论:有条件同意**(核心义务"不吞成成功"同意;"零完成""调度独立备选"与逃逸面必须改写)。

**2) 修改建议(逐点):**
- "零事件/零提交"成立(audit/admission 在 406-409,submit 在 456,production 函数内无 try —— 全文件无 try/except);**"零完成"需限定为"生产链不写完成"**。因为窄捕获后驱动会 `record_expansion_outcome(contract_aborted)` → artifact 写入 + `complete_action`(queue.py:385-394),attempt 落 failed(89-90)。建议落字:"生产链自身零完成写入;驱动窄捕获后**有意写失败结算**(artifact + action 以 contract_aborted 结算、attempt failed)—— 是结算记录,不是成功完成"。
- "并调度独立备选"建议改为:"队列中**其余已调度的独立条目继续执行**(runflow.py:645-656 记录后 return,循环继续);**deferred 备选不因本次 aborted 自动激活** —— 激活仍需显式指令(plan.activations,runflow.py:273-280)或 activate_deferred(queue.py:397+ / search.py:956-1074)"。
- **逃逸面必须落字或补实现**:窄捕获只包 `expand_hypothesis_production` 内、且只接 AuditContractError(runflow.py:631、645);`prepare_hypothesis` 在 try **之外**被调(runflow.py:623、420),其内部可抛 ChemicalStateError(production.py:196 → chemstate.py:669-693/459-476)与 HypothesisContractError(production.py:228 → hypothesis.py);audit 内首消费守卫抛 ChemicalStateError/ConditionContractError(audit.py:458、474-475 → chemstate.py:843/875、path_context.py:1502+)。三类均为 RuntimeError,不在 drive 捕获集合(runflow.py:326-335),start/resume 无外层 try(1000、1066)⇒ **run 以未捕获异常终止:无 stop report、无 run_error 披露、action 保持 claimed**。建议落字:"本条覆盖 AuditContractError;ChemicalStateError/HypothesisContractError/ConditionContractError 当前原样逃逸至 run 进程级终止,零事件写入成立、**错误披露未闭合**,如实登记为边界(待执行验证:构造坏池 spec / 被篡改 context 触发)"。
- "宽捕获(except Exception)下同样零写入"——真实驱动**不存在**宽捕获(全 runflow 唯一 `except Exception` 是回滚,772);该句只在负控测试语境成立(tests 静态见 `test_ppv1_s3b_production.py:244-296` 断言 claimed 零写;**执行待验证**)。建议改:"负控测试模拟宽捕获下生产链零写入;真实驱动无宽捕获,契约异常按上句两种路径处置"。

**3) 风险点:** "零完成 + 调度独立备选"连读,读者会以为 aborted 后系统自动换了备选路线并干净收尾;实际是失败结算 + 已调度条目续跑 + deferred 冻结不动,且三个异常类连 stop report 都没有。这是 0d 节最重的误导面。

### 0d.3 三个 None 与缺 proof 的语义

**1) 结论:同意**(附一处措辞精度)。

**2) 修改建议:** method_failed 短路(production.py:399-404)、converter 元数据与 center_match=None 进 audit 未知轴(1085-1102)、缺 proof→unknown 不是契约异常、R5 有界探索不授 verified —— 均读码一致。建议把"audit 保留 unknown/partial"改成"**中心 unknown / 覆盖轴 partial_unchecked_transformation**(不用裸 'partial' 作中心名词,与 R3 §6④ 一致)"。

**3) 风险点:** 裸 "partial" 复活会绕开 v12 的中心/覆盖两轴分写,属旧错回潮。

### 0d.4 中心证据分段负控

**1) 结论:有条件同意**(一处改字)。

**2) 修改建议:** "strict False ⇒ 至少 unknown"改"strict False ⇒ 中心 violated(决策表走 R5v);strict None ⇒ unknown"(audit.py:1188/1204)。proof 更改⇒AuditContractError(1110)、跨假设未绑定⇒unknown(1131-1148)、注册名+True 不构成核实、production 不另造 completion 许可(license 逻辑仅在 audit,1002-1036)—— 读码一致,照录。

**3) 风险点:** 同 C 条:violated 被弱读成 unknown 会改变 R 行归属与下游统计。

### 0d.5 队列与两类 deferred

**1) 结论:同意**(大部分逐行核实;"持久上限"一句待执行验证)。

**2) 修改建议:** 可引行号:两类 deferred 类型与对象(queue.py:60-63)、池摘要含条目身份/次序/截断且不消费 preview 筛选(109-112)、already_expanded 幂等(279-283)、blocked 保留原因不可强执(search.py:1000-1006)、trigger 不一致拒(1017-1025)、旧 revision ⇒ unchanged stale(1026-1033)、预算不足留独立未展开原因不改状态(1046-1062)、source_ref 必需(queue.py:500-514)、宽度/深度只推迟 followup 不删事件(production.py:424-432)。**"无新信息不无限重开(持久上限)"的具体持久计数器我未在本轮定位到实现行,标未确认**;若无实现,建议删"持久上限"或标"策略级承诺,待执行验证"。

**3) 风险点:** "不重复安排同 action"若被读成全局防重开保证,而实现只保证 already_expanded/幂等键,会高估防循环强度。

### 0d.6 条件依赖与场景转换进调度

**1) 结论:同意。**

**2) 修改建议:** 分支隔离(带自身 requirements/dependencies/assumptions 才派生专属上下文,runflow.py:454-461)、derive 前验证父对象 + source_ref(path_context.py:2327-2332)、阶段冻结与 phase_history 不重写(2376-2400;旧边不重评见 1242-1244)、循环依赖缺启动供应 ⇒ unresolved_initial_supply(production.py:112-142)、场景转换独立 action + 独立上限 max_scenario_transitions(search.py:1038-1039)—— 读码一致,可直接落字。

**3) 风险点:** "essential conflict 阻当前场景展开(不称化学不可能)"是规则级语义,阻断实现于调度 blocked 路径;若读者把 blocked 当作化学判据输出,属越权 —— 建议正文保留"留痕、非化学结论"的显式句(现文已有,照录即可)。

### 0d.7 模型假设协议(proposals[])与有界格式反馈

**1) 结论:有条件同意。** 条件:补两条披露。

**2) 修改建议:**
- **披露一(消费者范围)**:读码范围内,解析后的 proposals 只两处消费 —— `rank_by_key`(runflow.py:595-606)与计数/弃权标记(603-604);条目由冻结池 spec 构造(451-489)进 schedule_hypotheses(490)。**novel proposal 不构造 hypothesis、不入队列、不被 participants/条件/依赖契约校验**。建议落字:"novel proposal 仅记录与披露;'按既有契约'指记录结构自律,当前无消费者按该契约校验(读码范围 runflow/model_protocol/queue;未见 ≠ 证明不存在)"。
- **披露二(默认 0 轮的实际后果)**:FEEDBACK_ELIGIBLE 错误在默认 0 轮下首次即 `SearchBudgetExhausted` → 升级 PPV1RunError(model_structure_failure)→ run 停止并记 run_error(runflow.py:561-582、326-335)。建议落字:"默认 0 轮 = 格式错误即 run 终止;反馈机制仅在 1–4 轮配置下生效"。
- 其余(结构失败不进反馈、不以反馈改分子再试到通过 587-594;真实请求默认 0、传 model 不补预算 430-447;profile 默认 0/范围 0-4、max_real_model_requests=0、chemical_reproposal off:profile.py:281-318、369、540)读码一致。

**3) 风险点:** "有界格式反馈"字面给人"格式错会被自动修复"的印象,默认配置下行为是立即终止;"每项一条独立反应假设(按既有契约)"给人"模型提案受契约校验"的印象,实际只有排序消费。两句都是程序上可辩护、语义上误导。

### 0d.8 PPV1 独立 runner 分流

**1) 结论:同意**(读码部分核实;恢复/子进程行为待执行验证)。

**2) 修改建议:** 双入口分流(runflow.py:214-223、315-319)、B3/B4 注入点(production.py:452-464)、B1(300-303)/B2(547-551)、followup 幂等补调度(reconcile_followups,runflow.py:205-253)、停止报告按冻结优先级取主因且 deferred/blocked/claimed/open 存在时不报 exhausted_search(search.py:2873-2877)、unexplored 集合含六类计数与"停止不是化学终点"注(2880-2889)—— 均读码一致。四崩溃恢复与硬杀子进程测试属执行证据,**待执行验证**。

**3) 风险点:** "幂等补调度,不重发事件"是恢复语义核心,静态读码只看到入口与注入点;在执行证据出来前,正文宜标"恢复正确性依执行证据(待执行验证)",不以读码替代。

---

## G. 0c-v13 七条 R4 §8.5 落字

**1. 11+1 父绿精度 — 结论:同意(执行面待验证)。** 组成与 R4 报告 §2 一致(docs/POLLUTANT_PATHWAY_S3A_CODEX_REVIEW_R4_2026-10-08.md:31);我静态数得 `tests/test_ppv1_s3a_rework_r4.py` 恰 12 个 test 函数(与 12 父绿数一致),但函数↔绿项映射属执行结果,**待执行验证**。风险点:把"11+1"写成执行结论而不附分类产物路径,后续轮次无法互证。

**2. 各入口 kind/reason 层次 — 结论:有条件同意(枚举是内因子集,非入口全称)。**
修改建议:两处 `∈ {…}` 都应加限定语。工厂/strict 入口除 unregistered_cx_class(chemstate.py:473)、unparseable_smiles(690-693)外,另有 invalid_structure_origin(680-683)、cn_only_requires_dedicated_factory(674-679),且**空输入 raise 无 kind 字段**(669-671)、未知保真轴 raise 只带 axis(697-699)。恢复入口除 raw_structure_rejected(896,内因读 reason,889-899)、state_structure_unparseable(846)外,另有版本门 raise **无 kind**(779-783)、invalid_structure_origin(789)、cn_only_contract_violated(819)、structured_state_missing_isomeric(828)、structured_state_availability_mismatch(835)、state_fact_rederivation_mismatch(879)、raw_structure_missing(888)、raw_identity_mismatch(906)。建议落字:"该枚举限'结构串词法/解析'两内因,不是该入口 kind 全称"。风险点:现文字会被读成"恢复入口只会报这两种 kind",消费方按两 kind 写分支判断将漏掉其余全部拒因。

**3. 未知系数使元素/电荷账亦 unknown — 结论:同意。** `full_known`(audit.py:628-632)不成立 ⇒ 元素账/电荷账 unknown(641-651、673-681);"verified 只覆盖调用方声明清单"与 omission 语义一致(1441-1446)。风险点:无。

**4. omission 及声明清单边界 — 结论:同意(一处未确认)。** omission 不证明实际缺物质(1441-1446)、两类 violation 分写(922-933 vs 954-999)读码一致;"λ_s×Δ 对账"复算式**未在本轮读码确认,标未确认**,给出行号或删精确式后再落字。风险点:精确数学式无源位置 = 伪装成已核事实。

**5. R2b/R1 对象范围 — 结论:有条件同意(补 R4 原话 caveat)。**
修改建议:补 R4 原句"**不声称 R1 全称不可达、不建议删除防御行**"(R4 报告 line 101 语义);R2b 由调用方传 contract_violation 触发读码支持(decide_admission 内 contract_violation 字面 audit.py:1649、1749),但"不传则分支不可达"是可达性声明,我未穷举全部调用方传参面 → **部分确认,待执行验证**;S3b caller 不把 AuditContractError 降级为 R 行读码一致(runflow.py:645-656)。风险点:把 R1 写成"不可达"会诱导后人删防御行,恰是 R4 明令禁止的推断。

**6. 条件事实真实性 — 结论:同意(补强制点清单精度)。**
修改建议:"S3b 真实 caller 接 context 首消费守卫"落字为:"强制点 = audit 入口(audit.py:458)与 derive 父对象(path_context.py:2327);`aggregate_environment_fit`/`assess_conditions`/`assess_candidate_conditions`(989/1117/1172)自身仍无强制调用,靠调用序经上述两点守卫 —— 维持 v11 '入口强制 + 上游纪律'分写";场景转换 source_ref 必需(queue.py:500-514)读码一致。"不从观察/标签/工具隐式条件造当前事实"是规则级构造约束,本轮未逐一读构造点 → 规则文字与判据四同源,可照录,不加执行背书。风险点:见 D 条 —— 把上游纪律写成入口强制是已更正过的旧误导。

**7. 异常不当 R 行 — 结论:有条件同意(零写入口径修正)。**
修改建议:AuditContractError 是结构化契约拒绝、不落 R 行读码一致(audit.py:316、10 处抛点全在 audit.py;decide 不消费异常为 R 行);"宽捕获下零写入"改"**负控测试模拟的宽捕获下生产链零事件/零提交写入**;真实驱动无宽捕获,窄捕获路径**会写失败结算**(queue.py:385-394)";复合探针"首处拒绝后未执行段不报通过"依测试执行,**待执行验证**。风险点:把"零写入"无限放大成"异常后库内无任何变化",与 contract_aborted 结算写入的事实冲突。

---

## H. §6 程序证据与状态

**1) 结论:有条件同意**(结构与静态可核部分成立;全部执行类数字待执行验证)。

**2) 修改建议(逐项):**
- **静态已核(本轮读码/静态计数,非执行)**:契约版本与默认值 —— profile-13(profile.py:135)、store-9(139)、search-5(198)、search-limits-3(268)、format-feedback-1 默认 0/范围 [0,4](281-318)、max_real_model_requests 默认 0(369)、chemical_reproposal off(540)、delivered_stages "S0-S2,S3a-base,S3b"(569);store 15 张表(search_actions 列 258-278 含 defer_reason)⇒ "无新表"静态一致;deferred 两类复用 search_actions、格式反馈复用 model_requests(queue.py:60-63、model_protocol.py:241-303)静态一致;S3b 测试静态计数 61 个 `def test_` × runner 单测 crash_after 参数化 4(runner 433-435)⇒ 64,算术成立。
- **待执行验证(列出复核所需动作,不代述结果)**:851/787/64、4 行为红 + 4 collection 红、G01 1453/8/17 与 286 输入、1453=1389+64、全部新测试绿 —— 需在指定 HEAD 下各跑一次 pytest 并归档完整输出与 SHA;legacy code_identity 新值 `18007e6a…` 我只核到**证据文件记录**(docs/review_evidence/ppv1_s3_impl_2026-10-08/s3b_r1/code_identity_after.txt),**重算待执行验证**(旧值 4ea99b… 在 R2/R3/R4 证据中一致)。
- 建议每条执行数字后附:命令、HEAD、输出文件路径 + SHA,否则下轮无法互证。

**3) 风险点:** 数字链条(851=787+64、1453=1389+64)算术自洽且与静态计数吻合,是"程序上诚实"的一面;但自洽 ≠ 执行过。若在回应/落字中把自洽当执行,即构成对冻结裁定的证据冒充 —— 全部标待执行验证是唯一诚实写法。另:工程数字不代表 dev/298 科学性能、判据未冻结,照录。

---

## 汇总(按请求 §7 要求的逐条结论一览)

| 条目 | 结论 |
|---|---|
| 判据一 | 有条件同意(示例机制改写;词法/往返待执行验证) |
| 判据二 | 同意(λ_s×Δ 式待补源位置) |
| 判据三 | 同意(strict False 落字改 violated) |
| 判据四 | 同意 |
| 判据五 | 有条件同意(8b 补短路路径;8d 闭合范围按逃逸类如实收窄) |
| 0d.1 | 有条件同意(产物身份源=冻结池 spec 落字) |
| 0d.2 | 有条件同意(零完成口径/备选语义/三类异常逃逸披露) |
| 0d.3 | 同意(裸 partial 改两轴名词) |
| 0d.4 | 有条件同意(strict False ⇒ violated) |
| 0d.5 | 同意("持久上限"未确认句删或标待验证) |
| 0d.6 | 同意 |
| 0d.7 | 有条件同意(消费者范围 + 默认 0 轮即终止两条披露) |
| 0d.8 | 同意(恢复正确性待执行验证) |
| 0c-v13.1 | 同意(分类待执行验证) |
| 0c-v13.2 | 有条件同意(枚举加"内因子集"限定) |
| 0c-v13.3 | 同意 |
| 0c-v13.4 | 同意(复算式未确认) |
| 0c-v13.5 | 有条件同意(补 R4 line 101 caveat;可达性待验证) |
| 0c-v13.6 | 同意(强制点清单精度) |
| 0c-v13.7 | 有条件同意(零写入口径修正) |
| §6 | 有条件同意(全部执行数字待执行验证) |

本回应为只读评审:未执行任何 shell/测试/探针,未修改任何文件;所引行号均来自本轮实际读码,读码准确性按互证原则可被下一轮抽查复读,发现任一事实错误请直接指出更正。
