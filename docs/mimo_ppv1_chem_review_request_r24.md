# mimo 化学评审请求 r24:pollutant_pathway_v1 S5a 回修 r3 上下文首消费引用绑定后的化学判断面

日期 2026-10-09。本请求**自包含、只含规则级表述与合成例**(如
CCO/CC=O/[H][H]、氧受体 O2/acetate、场景 aerobic/anaerobic),
不含金标/题面/封存逐题 run 数据,不含任何真实 dev/298 指标数值;
由用户送 mimo,回复原文落盘。触发点:AGENTS.md 化学评审三类之
1(需评判上下文权威/恢复口径——S5a 回修 r3 改动了生产上下文
**首消费引用绑定**的消费侧语义,拟冻结前需化学复核)。
**评审独立性不做背书;结论采信到与程序证据互证的程度为止;
本请求只问规则级判据,不请求任何执行声明。所有"已执行"字样的
程序事实均标注〔待执行验证〕,mimo 不复跑代码。**

---

## 0. 背景(一段)

S5a 回修 r2 经 Codex 正链 R3 复审(2026-10-09):S5A-02(要求侧
单位收口)关闭,但**唯一阻塞 P1 [S5A-05]**:上下文 artifact 存储
地址为 `ctx:<context_id>`(persist_context 写入即返回该
context_id 作为存储键与引用);恢复侧共同入口
`production.load_context` 只按请求引用读 H07 信封、再经
`PathContext.from_dict` 核**载荷自身**内容身份——但从未核对
**请求的 context_ref 与恢复载荷的 context_id 是否同一**。于是:
改事实+重算载荷 context_id+重封 H07、但**沿用旧 ctx: 地址与
旧行动引用** ⇒ 公开 resume 接受并继续沿新身份提交事件(实测
events 0→1、派生子上下文〔待执行验证〕)。这违反冻结判据四
"重建半边"的既有文字:**合法新内容重建用新 context_id 并保留
parent_context_ref 链,旧引用不复用**;也违反 S3 任务书 §3.1/§7
(H07/H08)首消费继承——上下文、内容身份、引用在首次消费闭合。
本轮回修 r3 在共同 load_context 的 H07+from_dict 完成后、
返回/派生/评估/审核前加**引用绑定核验**(消费侧守卫,冻结侧
path_context 判决与 criteria-v1 冻结正文/FREEZE_RECORD 逐字节
不改),登记 `ppv1-search-production-2`/`ppv1-profile-23`。请评审
以下三个判断面是否把口径收对了——是否存在"收得过紧导致
合法重建被拒"或"收得不彻底仍有身份误导"。

## 1. 判断面一(修复 S5A-05):恢复时上下文引用绑定

**修复后规则**(共同 `production.load_context`,runflow
decide/expand/scenario_transition 与 endpoint 三处派生消费共用
同一守卫):

- H07 信封完整性(可解析/信封 hash)先行,原文件保全;
- `from_dict` 内容身份核验先行:载荷 context_id 与按全部语义
  字段同源重算一致(篡改语义字段保留旧 context_id ⇒ 拒,
  `context_content_identity_mismatch`,既有防线不动);
- **新增引用绑定核验**:请求 context_ref ≠ 恢复载荷
  context_id ⇒ 结构化拒
  `context_reference_binding_mismatch`,机读披露
  expected_context_ref(请求)/recovered_context_id(实际)/
  storage_key/parent_context_ref。**selfhash 重算正确不能替代
  旧引用绑定**:载荷自洽只证明"这份内容与其自算 ID 一致",
  不证明"请求/行动引用的就是这份内容"。
- 拒后:不派生、不评估、不 audit、不提交坏上下文事件;
  坏 artifact 保全(不重封覆盖、不猜迁移、不默发新引用)。

**合成例**(三案与复审 R3 §4.2 同案构造,真实公共链合成
start(after_claim)→resume;无金标;before 为父 39d739d,
after 为 r3〔待执行验证〕):

| 案 | 突变(仅改 artifact,不改数据库/行动) | before(父) | after(r3) |
|---|---|---|---|
| 正常控制 | 不动;checked unknown 事实值 None | resume 成功,events 0→1 | **保持** resume 成功,events 1 |
| 旧 id+改内容 | unknown 事实值改实体值 O2,保留旧 context_id,重封 H07 | load/resume 拒 `context_content_identity_mismatch`,events 0 | **保持**同拒(既有防线) |
| 新 id+旧地址 | 同上突变+直构重算新 context_id(载荷自洽),旧 ctx: 存储键与行动引用不动 | **load 返回新身份、resume 成功、events 0→1、派生子上下文**(P1 反例) | **首消费拒** `context_reference_binding_mismatch`(披露期望 pc_a72…/实际 pc_d99…),resume 失败,events 0 |

**问 1**:
①"恢复时请求引用必须等于恢复载荷身份"是否正确的权威绑定
口径?还有哪些通道能造成"引用与内容身份错位"(如迁移、副本、
跨 run 拷贝),拒绝+保全是否比"自动迁移到新地址"更保守正确?
②该核验放在**消费侧**(load_context)而非**冻结侧**
(path_context.from_dict)——因为 from_dict 无法知道请求方引用
是哪个;这种职责切分是否会留"绕过 load_context 直读 artifact"
的洞?生产消费入口全集(runflow decide/expand/transition +
endpoint 派生三处)是否闭合?

## 2. 判断面二:自洽新内容不得占用旧地址(含"合法内容"变体)

**修复后规则**:地址 `ctx:<X>` 下任何与 X 不同的 context_id
——无论内容来历——一律首消费拒:

- **直构/篡改变体**(复审 R3 §4.2 实测):unknown+实体值的
  直构自洽新 ID 重封旧地址 ⇒ 拒〔待执行验证〕;
- **checked 正规合法新内容变体**(复审未执行、本轮自构造):
  用 checked 构造器(build_path_context+build_condition_fact,
  unknown 值恒 None)合法重建的语义上下文,整体写入旧地址并
  重封 ⇒ **同样拒**〔待执行验证〕——内容合法不豁免地址绑定;
  同一载荷存**自己的新地址**则正常消费(重建半边的合法半边)。
- 理由:旧地址/旧行动引用承载的是**旧裁决的历史**(旧
  necessary unknown、旧事件链);任何新身份占用旧地址都会让
  "沿旧引用回溯历史"读到不属于该历史的内容——即使新内容
  本身合法。化学上这等价于"把新实验记录装订进旧实验编号"。

**问 2**:
①"内容合法与否不影响地址绑定判定"——即绑定判据只看
(引用,身份)二元组,不看载荷质量。这是否过严?有没有
"合法新内容就该允许顶替旧地址"的合理场景(如显式修订)?
若允许,应走什么显式通道(新修订号+人工/teacher 批准),而非
静默顶替?
②拒绝后的**零派生/零评估/零提交**是否是唯一正确处置?
是否存在"隔离坏上下文但继续其他无关任务"的更优工程处置
(当前:首消费拒直接停 resume,错误上抛)?

## 3. 判断面三:合法新内容新 ID 新地址 + parent_context_ref 链

**修复后规则**(冻结判据四"重建半边"既有文字的兑现):

- 合法重建/派生的语义上下文:新 context_id、**新地址**
  `ctx:<新 ID>`、保留 `parent_context_ref` 指向父(旧引用不复
  用,但链路显式可溯);
- 场景转换链:scenario_transition(须带 source_ref,如
  user:switch-anaerobic)经 derive_child_context 派生子上下文
  ⇒ 子新 ID 新地址;后续 followup 行动携带**新** context_ref
  消费〔待执行验证〕;父上下文在旧地址照常可消费;
- 全 run 不变量:每个 ctx 地址的载荷 context_id 与地址一致
  (合法链零旧地址复用)〔待执行验证〕。

**合成例**(本轮自构造正控):CCO 池 + aerobic 根上下文 +
显式 source_ref 转换到 anaerobic——resume 后转换 done、
followup 沿子新引用、两代上下文地址-身份一一对应、
parent_context_ref 指向根〔待执行验证〕。

**问 3**:
①"新内容新 ID 新地址+父链"是否足以支撑后续审计回溯(历史
裁决沿 parent_context_ref 链可溯,而不需要内容顶替旧地址)?
②场景转换的子上下文沿**新**引用调度、旧边评估保持历史快照
(phase_history 冻结)——这个"引用换新、历史冻结"组合在化学
追溯上是否自洽?有没有"必须原地覆盖"的化学理由?

## 4. 边界与不请求事项

- 本轮**不改**冻结判据一–五任何正文;不增加换算、单位推断、
  负要求或物种语义新门;不启动 S5b;科学性能 pending,全部
  teacher TBD 不代定;判分零 LLM;无网络/外部模型调用。
- 低层语义(直构 dataclass/restore 不过 checked 构造器的
  unknown+值次序边界)仍为已登记 P2,归用户/teacher,本轮
  不以文字宣称首消费绑定已通过〔待执行验证〕。
- 程序事实(三案翻转、五案矩阵、事件/表计数)均由正链 Codex
  复审独立复验为准;本请求不附执行日志,不请求 mimo 背书
  任何数字。
