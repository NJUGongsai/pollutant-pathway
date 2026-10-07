# mimo 化学评审请求:pollutant_pathway_v1 化学判据(S3a 底座版 v9)

- 日期:2026-10-07(S3a 批次;替换同日 v8 请求。v8 请求原文快照已存
  `docs/review_evidence/ppv1_s3a_impl_2026-10-07/s3a_r1/mimo/`;旧回应
  r5–r8 原样保留不覆盖)
- 触发点:AGENTS.md mimo 三触发点之 1(需评判化学结构时——冻结或
  发布前)
- 评审对象:S0–S2 回修后(R8,ppv1-*-8 契约族)加上 **S3a 持久搜索
  底座**(ppv1-search-1 / ppv1-store-9 / ppv1-profile-9 / search
  -limits-3)之上的化学判据文本 v9;**尚未冻结**
- 与 v8 的差异来源:R8 复审放行 S3 时提出的八项 P2 文字更正
  (`POLLUTANT_PATHWAY_S0_S2_CODEX_REVIEW_R8_2026-10-07.md` §5)
  与 R8 §6/§8 文案更正;**S3a 本身不新增任何化学判据或门禁**
  (搜索底座是工程事实:mimo 不审程序/存储,本请求如实披露实现与
  未实现边界,其中涉及的化学消费契约文字受审)
- 自包含性:规则级表述与合成规则级夹具,无任何金标/题面/封存逐题
  数据;由用户转交,回复原文落盘 `docs/`

## 0. 背景(一段话)

S0–S2 判据 v8 经 R8 独立复审确认:R7 两项 P1 已闭合、R6 五组保持
关闭、剩余 P1 为空,S3 工程放行。本批(S3a)交付**持久搜索底座**:
搜索/任务/attempt/请求身份与 schema、十上限实际计数(search-limits
草案 v2 → 实际可执行 v3,键/默认/范围/单位不变)、认领/预算事务、
artifact 完整性校验、四崩溃恢复协议、停止原因主因优先级
(user_stop > budget_limit > depth_limit > no_local_candidate >
awaiting_prediction > exhausted_search)。**不交付**(S3b):队列化学
集成(冻结池/备选/两类 deferred 调度)、条件依赖/场景转换、新模型
假设协议与格式反馈、固定工具中心证据生产链、PPV1 独立 runner 分流
——公开 start_run/resume_run 对 PPV1 继续 fail-closed。工程数字
(合成规则级):ppv1 全量 **594 passed/0 skip**(536 存量 + 58 S3a
新增);新增回归在基线 00e509a 红 = 2 行为红(profile 版本断言)+
两文件 collection 红(新模块缺失,58 用例未执行,如实分类,不冒充
行为红);G01 安全隔离 **1196 passed/8 skipped/17 deselected**
(1138 + 58;8 skip 逐项缺席依赖披露,不是原环境数字)。这些是
工程契约结果,不代表 dev(B1 环境中间步骤)或 298(RHEA 通用酶学)
科学性能。本轮请评审:**判据文本 v9(= v8 + R8 八项更正落字 +
S3a 边界的诚实声明)**。目标不变:可能降解路径与条件相容路径的
诚实表示;unknown 不升格;verified 不靠模型或调用方自报字符串;
账平、物种同 CN 或一份正确局部诊断不能代替整条声明的覆盖与追溯。

## 0b. S3a 实现与未实现边界(工程披露;判据不受影响的如实声明)

- **已实现(底座,公开接口 + scripted/fake 驱动验证)**:
  `pollutant/search.py` —— SearchAction(身份含 run/父/context/
  subject/kind/revision/policy;同键异内容拒)/ expansion_attempt
  (恢复同 attempt 不再扣,新备选/重开换 attempt)/ 预算预约账表
  (十上限的预约/consume/release,确定性预约 ID,持久记录为事实
  源,快照是派生值)/ 模型请求预登记(real 登记即时占额,失败/
  超时/悬空均占;**默认 0 ⇒ 登记被拒 ⇒ 网络发送被阻止**;scripted/
  fake network_request_count 恒 0,不冒充真实调用)/ commit bundle
  artifact(不可覆盖;先验版本/hash/身份后消费同一 output)/ 四崩溃
  恢复协议(B1 冻结续跑、B2 悬空暴露不默发、B3 同一 output 完成、
  B4 幂等补账;H08 不一致保全失败)/ 停止原因优先级解析。
- **未实现(S3b,不冒充已交付)**:冻结池/备选/两类 deferred 的
  调度语义与 expected_parent_revision 激活;条件依赖/场景转换实际
  进入调度;`proposals[]` 模型协议与有界格式反馈;冻结 AtomTool →
  donor 诊断 → converter → audit → admission → submit 的生产
  调用链(因此 **S3a 未新增 audit_hypothesis 生产 caller**,下文
  判据五 8d 的 caller 义务仍由 S3b 承担);PPV1 独立 runner
  start_run/resume_run(继续 fail-closed)。
- 搜索层与化学验证的关系:搜索提交链**不构造/不修改任何化学对象**,
  事件提交经公共 `store.submit_event` 的全部首消费验证(R7-01/R7-02
  已闭合的入口),测试含"篡改 raw 的载荷经搜索驱动提交仍被拒、零
  事件"的正控;**不存在经搜索层绕过化学验证产生 verified/事件的
  路径**。
- 停止不是化学终点:停止报告保留未探索集合(deferred/blocked/悬空
  请求),存在 deferred/知识缺口时不称"所有路线都探索完";chemical
  endpoint 评估属 S4,本批不产出任何终点/矿化/解毒结论。

## 1. 判据一:分子身份(v9 文本)

1–4 及 2b 同 v8(输入侧注册感知校验/混合并列 ABS 归一/公开表示往返
闭合/fidelity 分轴;恢复与直传首消费共用公共 writer 同源验证)。
v9 落字三处(R8 P2 ①②③):

- 2b 括注:**"同源验证证明与工厂契约一致,不是独立双算"** ——
  `validate_state_object` 与工厂/writer 共用同一重推导实现(两个包装
  实现的存在不自动变成新阻塞);契约一致性由此保证,不是两套独立
  核验,下游不得读成双重独立证明。
- 2b 新增条款(升格自"请评审"问题):**"原始 `r` 标记的存在与含义
  均不被采纳也不被反驳,拒绝事实不得用于推断实验消旋/样品纯度;
  裸指定结构/strict 身份也不是同样品或对映纯认证。"** 拒绝是输入
  表示层契约,不反推输入真实化学含义。
- **canonical+r 上层错误名的含义更正**(R8 §6/§8 文案更正):canonical
  串加 `r` 在 v8 走 `state_structure_unparseable` 拒绝 —— 该上层
  kind 实际包裹的是**工厂未登记 CX 类守卫拒绝**(unregistered_cx_
  class),不等于 RDKit 本体不能解析该串、更不表示真实化学结构
  非法或实验消旋/纯度已证。方向为拒绝(不回退),语义按此读。
- 判据二前提限定(v8 已有,v9 明确入口限定):自报 formal_charge/
  stereo/isotope 与结构重推导一致的声明,**限定"经首消费验证的
  入口"**(2b 覆盖的 from_dict/直接对象/工厂/writer),不是所有裸
  dataclass 对象的无条件性质。

**请评审**:(a) 2b 的三处落字(非独立双算括注/r 不反推含义升格/
canonical 上层错误名语义)是否准确且不引入新的越权认证;(b) v8
已同意的判定范围与正控(CX 入口清单、DAT 剥离、含空格放行、CN-only
契约)不需重评;(c) S3a 边界披露(0b 节"搜索层不绕过化学验证")
表述是否如实。

## 2. 判据二:参与物计量与元素/电荷核算(v9 文本)

1–8 同 v7/v8(全氢账/系数契约/完整性 unknown/电荷轴前提/结构化
omission_pattern_matches/R5d 触发集合限定/恒等≠落点)。v9 无判据
变化;D/T 合并计 H、自由基电子不入元素账的既有披露保留(数值账
"平"在这两类有系统盲区,不得读成质量/电子守恒已核)。

**请评审**:确认不需重评(入口限定已在判据一 2b 落字)。

## 3. 判据三:admission 决策表与中心证据契约(v9 文本;有序,首中即决)

R 行语义/类型契约/内部重算/proof_scope 披露同 v7/v8;"覆盖 full 的
两个互不替代根据"(①无未覆盖参与物;②注册补全规则数值精确相等且
未覆盖身份全部在登记许可内;二者都只解除覆盖轴)同 v8。v9 落字
两处(R8 P2 ④⑤):

- **scope 归属更正**:v8 请求称 scope 文本声明"本许可不区分该参与物
  的键断裂方式与电子去向" —— 更正:当前代码的
  `completion_license_scope` 字面**不含**该句;该表述归属**许可定义/
  本规则正文**(composition-only 许可不区分键断裂方式与电子去向,
  这是许可的语义边界,不是代码 scope 字面)。未改字段字面,无版本
  身份影响;composition-only 不能升级机制证明的边界不变。
- **恒入 ≠ 已适用**:`completion_license`/`completion_license_scope`
  恒入 center detail,字段存在不等于本结论使用了补全许可;判定
  "本结论依据含许可补全"须同时看 **product_coverage=full、
  uncovered_reactant_refs/uncovered_product_refs 非空、
  unlicensed_uncovered_identities 为空** 三条件组合;license_applied
  标志、顶层别名、同屏渲染列后续 API/展示层事项(P2,不作本轮门)。

**请评审**:(a) scope 归属更正与"恒入≠已适用+三条件判定"的表述
是否如实反映实现语义;(b) "full 两根据"与补全许可 scope/严格身份
登记同 v8,不需重评。

## 4. 判据四:条件相容聚合(v9 文本)

同 v7/v8(快照一致性/签名↔评估行双向对应/派生先验父对象/内容身份/
三分/单向矛盾/孤儿 unknown;行↔签名对应以"要求对象评估后不可变"为
契约前提)。v9 落字一处(R8 P2 ⑥):

- **两种不可变机制分写**:Requirement/ConditionFact 由 frozen 强制
  (嵌套冻结);PathContext 本体**非 frozen**,其不可变性由**消费前
  validate 的内容身份同源重算兜底**(就地改语义字段保留原 context_id
  ⇒ `context_content_identity_mismatch` 拒)。不得把两种机制写成
  同一类不可变;任何派生/评估/审核入口消费前必须先 validate(绕过
  validate 直读字段属违约)。

**请评审**:确认该分写与既有实现一致,其余条款不需重评。

## 5. 判据五:供体一致性诊断(v9 文本)

1–8 同 v7/v8(实际净变化判定基础/奇偶构型比较与非四面体 unsupported/
联合映射三类支持范围/中心属性披露/strict 同源/证据载荷内嵌/四个
原始字符串入口与工厂同源守卫/声明–执行净效应对账 + 镜像终态归一)。
v9 落字两处(R8 P2 ⑦⑧):

- 8b 拒绝与失败早退(R8 复核精度更正):**失败诊断是三个判定字段
  reaction_center_match/strict_target_match/legacy_cn_match 均为
  None**、`diagnostic.center_evidence={}`(均未评估);**converter
  仍返回版本/来源元数据与 center_match=None**,不是"四轴 None"
  也不是"converter 整个 evidence 为空"。None=未评估,**不等于通过**;
  `execution_ok=False` 早退路径不解析四字段亦不消费其任何轴,无
  verified 泄漏面。拒绝为契约性拒绝 ⇒ 本次诊断/审核不产生任何轴
  结论与 disposition;调用方不得吞异常后按 retain/verified/any-R 行
  记录。
- 8d caller 义务(R8 P2 ⑧):R8 源码当时无 audit_hypothesis 生产
  caller;**S3 新 caller 必须承担"让 AuditContractError 逃逸并中止
  本次 admission 计算/提交"的义务,不得吞异常继续**。如实披露:
  **S3a 未新增生产 caller(生产链属 S3b)**,该义务尚未被执行证据
  闭合;grep 无 except 不是动态安全的通用证明(静态清单仅证当前
  抛点不在宽捕获 try body 内)。

**请评审**:(a) "三个 None + converter 元数据"的更正表述是否准确;
(b) 8d 义务的承担方式(S3b caller + 回归测试)是否足以闭合,当前
"未闭合但如实披露"的状态是否可接受为 S3a 边界;(c) 其余条款同
v8,不需重评。

## 6. 程序证据与状态(程序事实,不替代化学判断)

- 规则级测试:ppv1 全量 **594 passed/0 skip**(536 v8 存量 + 58
  S3a 新增,全部合成夹具;S3a 新增覆盖身份/E03、预算/E04、H05 三
  独立零预算夹具、H06 双连接/双进程、四崩溃硬杀恢复、H07/H08、
  搜索层不绕过公共 writer 验证、runner 双入口仍拒);
- 基线红绿:新增测试(含 test_ppv1_profile.py 升位断言)在基线
  00e509a detached worktree 同字节运行 ⇒ **2 行为红(profile-9/
  search-limits-3/delivered_stages 断言)+ 两新文件 collection 红
  (pollutant.search 缺失,58 用例未执行)** —— 如实分类:缺实现红
  与行为红分开,不以 collection 红冒充化学行为翻转;
- 基线文案更正落字(R8 §6/§8):14 行为红(v8 新测试对 858dd94)
  **不是 14 个旧错误 R6** —— 其中如 direct_dataclass_fact_tampered
  单改产物 charge=99 在父基线已是电荷 violated、R5d retain(元素/
  身份/center verified/full,电荷轴 violated),旧 R6→新拒只在 raw
  最小链成立;R7 旧化学脚本实际 55 条早停(旧 assert 先在 len==57
  计数失败、行为分支未执行),尾部 2 案+直接对象补充由分段脚本补全;
  R7 flag 测试实参顺序已修(实际断 gate_flag_mismatch)。旧记录只读,
  更正只落新文本;
- G01:安全隔离工程回归(R7/R8 白名单口径:不复制 evaluation/金标/
  题面/封存/v4;R7 路径清单 + R8/S3a 新增输入;固定
  PYTHONPATH/空 BBD_DATA_ROOT/V3_CODE_ROOT/V43_ASSET_ROOT/
  DEPENDING_V3_ROOT)⇒ **1196 passed/8 skipped/17 deselected**
  (1138 + 58;8 skip = 5 真实评价依赖 + 1 v4 对照源 + 2 phase_d
  派生 metadata;17 deselect = 16 slow + 1 明确排除的 export 用例,
  逐项 nodeid 披露;R7 历史 1110/8/17 与 R8 历史 1138/8/17 单列,
  不混计);legacy 冻结 AtomTool/存储语义未改(workflow/runner.py
  仅更新 PPV1 拒绝文案与 detail 字面,legacy 分支行为不变;该共享
  文件文字变更使 legacy code_identity 聚合哈希变化,旧 legacy run
  的跨版本 resume 按既有身份门槛拒绝,是设计行为,如实登记);
- 判据未冻结;v9 无新化学机制,S3a 消费契约/文字受审项:判据一 2b
  三处落字、判据三 scope 归属与恒入≠已适用、判据四两种不可变机制
  分写、判据五三个 None/caller 义务披露;契约族 profile/store 升 -9
  (新搜索表+search 契约;PPV1 从未放行执行流,无历史产物迁移),
  其余 -8 不动;未实施的 S3b 中心集成不得伪称执行完成;
- 参考(外部常识,非本仓资产):RDKit Book(CXSMILES 扩展/增强
  立体/立体化学章节)、rdCIPLabeler API;CXSMILES 解析器行为经
  Release_2026_03_6 源码取证与实证用例校准;**冻结前须以执行证据
  复核 RDKit(锁定版本)词法取证与放行正控的往返无损**(放行的
  每个保留类含空格/含分隔符输入,往返后其保留类事实无静默丢弃;
  移除类放行项以结构串往返同 id 为控)。

## 7. 请求的回复格式

对每条判据:1) 结论(同意/不同意/有条件同意+条件);2) 可直接
落进规则文字的修改建议;3) "程序上诚实但化学上误导"风险点。
逐条表态,不接受总体评价式回复。执行类声明一律标"待执行验证"。
