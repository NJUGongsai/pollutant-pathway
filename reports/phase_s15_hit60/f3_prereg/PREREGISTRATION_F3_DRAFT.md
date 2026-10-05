# PREREGISTRATION_F3_DRAFT — T8 F3 novel 受约束生成（任务载荷新增有界结构化上下文块）预注册草稿

- 状态：**DRAFT（待用户确认冻结）**。冻结生效条件见 §8.2；冻结前本稿任何数字与口径
  均可改（标"待冻结时定"处为必须拍板项），冻结后整文件 SHA256 重登记，看分后
  修改一律无效（I2）。
- 立项依据：[HIT60_IN_CORPUS_MISS_SOLUTION.md](../../../docs/HIT60_IN_CORPUS_MISS_SOLUTION.md)
  §1 F3 层诊断（"金标在场却被路由送进 novel 裸猜"）与 §6 建议 3（F3 专药、
  形态待设计——本稿把形态落为 **novel 任务上下文臂**而非路由改判臂，选型理由
  见 §1.4）；[T8 任务书](../../../docs/TASK_V43_HIT60_S1R2_GENERATION_ARMS.md)
  §3 G2 判据同源共用；teacher 批复 §四建议 2（先验进 prompt 类批准为可选辅助：
  闭卷 A/B 先行、不与主杠杆捆绑判定、可与守恒过滤合并设计）与 §七（路径预算
  与失败分支）。
- 判据证据基础（双源）：mimo E1 化学评审（gitignored
  `docs/mimo_e1_chem_review_comment.md`——本稿只取机制级结论不引 SMILES）§C2
  （novel 根因 = **确定性约束被卸掉**；最缺信息 = "这一步允许的骨架变化范围"
  ——ΔC 允许集/允许增删杂原子/可进攻位点，可由代码从题面确定性算出）、§A1/A3/B1
  （卡间区分度最大的化学字段）；mimo 守恒判据评审
  （[回复](../../../docs/mimo_conservation_rules_review_response.md)）——G1-b
  主产物骨架启发式、G2-b 杂原子分档、G3-b 官能团级可进攻性，即本臂**约束块的
  内容来源**；[采纳登记](../../../docs/MIMO_REVIEWS_ADOPTION_REGISTER.md) §2；
  程序互证 [COVERAGE_STAT](../../phase_s1_hit60/coverage_stat/COVERAGE_STAT.md)
  M1/M2（下称 M1/M2）。
- 题域与分母：dev v1.1 = **51 分母**（quarantine 已生效，
  [QUARANTINE_EFFECTIVE](../gold_health_check/QUARANTINE_EFFECTIVE.md)，
  2026-09-30）；判分口径 v3（component-aware，全主产物命中，
  [PREREGISTRATION_V3](../PREREGISTRATION_V3.md)）；对照基线 **C0 v3 = 14/51
  = 27.5% @1**。题域标签：dev = B1 环境路径中间步骤，数字不外推 298。
- 撰写代理纪律：2026-09-30，零 LLM 零 API、不改代码、不跑测试、不 git
  commit；分支 v4.3，工作树未提交改动全部保留（开工 `git status --short
  | head -20` 已记录：src/tests 20 文件 M + AGENTS.md untracked，与 G2 草稿
  同一现场）。
- 本文件不含任何金标内容；金标仅以 qid 与既有封存读数引用。

---

## 1. 臂定义与单变量

### 1.1 F3 主臂（本预注册对象）

- **臂名**：F3-NovelCtx v1（novel 任务载荷新增**有界结构化上下文块**——
  证据上下文 + 底物约束块 + prompt v2，一个开关）。
- **单变量开关**：`novel_context_block = v1|v2`（一个开关；值域 {v1,v2} 装配期
  fail-closed，随 policy 块进 run/batch identity，同 E1
  `rank_candidate_presentation` / G2 `novel_conservation_filter` 的开关链路
  先例；**不 bump PREDICTION_POLICY_VERSION**，身份差异由 policy 块携带）。
  版本串随开关进 run identity / 批次登记：
  - 上下文组装版本 `CONTEXT_ASSEMBLY_VERSION = v43-novelctx-1`（本稿 §2.1
    全文，含 N 与密度预算）；
  - 字段白名单版本 `CTX_FIELD_WHITELIST_VERSION = v43-ctx-fields-1`
    （本稿 §2.1.2 封闭表）；
  - 约束块计算版本：**复用 G2 判据版本串**（`v43-cons-1` / `v43-norm-1` /
    `v43-g3b-catalog-1` / `v43-donor-registry-1`）——同一规则体系、前向调用
    （§2.2；G2 用其判定方向，F3 用其呈现方向）；
  - prompt 版本：`novel_proposal_v2.md`（新文件常驻 `configs/prompts/`，SHA
    以 `novel_proposal_v2` 键进 `prompt_versions` dict → 经
    `ModelSetup.identity_block()` / `content_hash` / `build_batch_identity`
    进 run/batch/prediction_task 三级身份——E1 ranker_v2.md 同款既有链路，
    **零新身份代码**）。
- **作用位点（钉死，不得二义）**：`src/pathway_v43/services/prediction.py:
  build_prediction_task` 的 **novel 分支**（现 `candidates = []` 不变；任务书
  JSON 新增 `context` 块）+ `src/pathway_v43/workflow/nodes.py:_prompt_for`
  的 novel prompt 选择（v2 时装载 novel_proposal_v2.md，prompt 选择与上下文
  块**同一开关**，不可能错配）。**不改路由**（`domain/policy.py:
  decide_prediction_route` 一行不动——novel 仍是 novel）；**不改
  `_apply_novel` 落账逻辑**（G2 开关恒 off——见 §1.3 单变量纪律）；**不改
  输出解析契约**（novel 解析器零改动）。
- **现状代码事实（臂的动机锚点）**：novel 任务书现状 `candidates=[]`，任务书
  对证据池的全部可见信息 = `retrieval` 块三个文本字段（`task_id` /
  `payload_hash` / `substrate_identity`，prediction.py:544-549）——模型对
  "池里有什么、有多少、为什么没过门"**零可见**，只能从"我认识的分子"里自由
  作答（mimo C2 根因）。dev 六批路由分布恒为 novel 42 / recorded 8 / rank 3 /
  analogy 3：48 次 LLM 调用里 42 次是这种无上下文裸猜（M1 §1.1），novel 覆盖
  42/56 题 = 75%。
- **单变量纪律**：除开关（及其版本串）外，主臂与对照逐字段相等——输入、代码
  （commit）、资产、模型、预算参数、scorer 版本（v3）、价格快照、并发策略
  （S1 总则沿用）。
- **与 G1 的关系**：门 1（深位召回）迭代 2 已落"明显不过"支 → G1 付费臂维持
  不发车 → 本臂**不依赖 G1**、不受门 1 结论限制（同 G2 草稿 §1.1）。

### 1.2 边界钉死（四条，写死不得二义）

1. **candidates 恒空**：novel 任务书 `candidates = []` 不变——上下文块不是
   候选、不带 `evidence_id` 可引用身份，模型不得也不可能在 novel 协议内
   "选卡"；本臂不得变相把 novel 变成 rank 任务。
2. **原始卡不进任务**：任务书不携带任何完整证据卡（recorded/rule/analog 均
   不），只携带 §2.1.2 白名单内的**摘要字段**；排除清单（产物 SMILES、产物
   身份、完整卡 JSON、donor_refs 映射细节）为红线级封闭表。
3. **门禁只紧不松**：路由决策、资格门（recorded_eligibility_reasons /
   analogy 适用性）、`validate_products` 等既有门禁逐条不动、不放宽；本臂只
   在输入侧**新增信息**，输出侧门禁原样复验。
4. **fail-closed 不变**：输出解析契约逐字不动（解析器零改动）；上下文块自身
   的计算失败语义见 §2.2.5（"按不可用标注，不按零、不 fail 整题、不静默
   假装算过"）。

### 1.3 与 G2 的关系（正交性 + 发车顺序建议）

**机制正交（输入侧 vs 输出侧）**：

| 维度 | G2（守恒过滤 + 自排序） | F3（本臂） |
|---|---|---|
| 作用端 | 输出侧：提案落账之后、报告之前 | 输入侧：任务组装时点、提案之前 |
| 形态 | 纯后处理（无生成端反馈、无重试） | 生成端载荷（改模型输入与 prompt） |
| 判据关系 | conservation.py 的**判定方向**（剔除/降位/hold） | conservation.py 的**呈现方向**（允许集/白名单/清单作先验）——同一版本串 |
| 能否引入金标分子 | **不能**（只能移除/压后已生成候选；C1-novel 题明确不可及） | **能**（改变生成分布本身——C1-novel 12 题只有 F3 可及） |
| 离线可测性 | 可（封存答卷确定性重放，方案 B ¥0） | **不可**（模型输入变了必须真调用） |
| 费用 | ≈¥0（重放） | 必付费新跑（§5） |

两臂共享承载面（A 桶 11 题、spurious novel 面）但机制端不同——**单变量成臂
分开跑**，不在本臂内与 G2 叠加；联合形态（F3 on + G2 on）属下一轮预注册。

**发车顺序建议：先 G2 后 F3**。理由：

1. **就绪度不对称**：G2 已有完整草稿 + 判据冻结链（mimo 两轮评审 → 采纳
   登记）+ 判据代码与 29 例夹具已落盘 + 离线重放闭环
   （`reports/phase_s15_hit60/g2_arm/`）；F3 需新工程（§7：约 3.75–5.5 人日）
   与发车前置测量/审计（§8.3）。
2. **成本结构与信息序**：G2 判定走封存重放 ≈¥0，先跑零成本臂，其读数直接
   给 F3 的预期空间定价——G2 若已兑现 A 桶净赢，F3 的 @1 增量面相应收窄，
   发车前重估值；G2 若不过（输出端约束不够），F3 的输入侧先验反而更必要
   （mimo C2 的根因诊断指向生成端信息缺失，而非处置端不够严）。
3. **单变量纪律**：F3 对照 = C0 同款（G2 off），两臂先后跑互不污染；若 F3
   先跑，付费成本在前且 G2 的零成本判定被延后。

反方案（F3 先）的适用条件：teacher 里程碑裁定提前、或用户想先验证"生成端
可塑性"（F3 是 dev 上唯一能引入池内金标分子的臂）——可接受，但须接受付费跑
在前。**顺序最终由用户/teacher 拍板。**

### 1.4 形态选择：为什么是"上下文臂"而不是"路由改判臂"

诊断文档 §6 建议 3 原始形态 = "金标可推演在场时，路由从 novel 改判到带候选
的裁决任务"。本稿**不采用**该形态，理由三条：

1. **E2b 禁令正面冲突**：路由改判须把 rule/analog 卡喂进裁决任务——
   [TASK_V43_EC298_PHASE_E_POST_RETEST.md](../../../docs/TASK_V43_EC298_PHASE_E_POST_RETEST.md)
   §5 E2b 明令"禁止直接将原始 rule/analog 卡加入 rank 任务或因其检索出现
   就提交"；M2 实测按检索序放宽的假想卡 **79% 违反守恒/杂原子过滤器**
   （analog 迁移卡 16/16 全违规）——不捆绑过滤器的放宽 = 灌噪声（E3 实测
   @5 反降、spurious 升同向）。
2. **门禁只紧不松最易守住**：上下文形态零触碰路由与资格门（§1.2 边界 3），
   单变量纯净；路由改判形态则同时动路由、入围、裁决三处。
3. **根因诊断指向信息而非卡**：mimo C2 判定 novel 根因 = "确定性约束被
   卸掉"、最缺信息 = "这一步允许的骨架变化范围"（可由代码从题面算出）——
   药方是**把约束与池状态作为信息喂回去**，不是把卡喂回去。

继承 E3 设计先例的三条硬约束（§5-6 原文语义，F3 必须逐条继承）：①上下文
须**有界、结构化**（E1 密度预算方法，非堆料）；②**明确区分"完全无证据"
与"有证据但映射/条件未过门"**（池状态摘要的硬要求，§2.1.1）；③**不得把
未验证产物写成事实或照抄进报告**（排除产物 SMILES 的设计理由，§2.1.2）。
验收口径沿用 E3 原文：**看通过最终化学门禁且实际进入报告位的产物，而非
提案数。**

### 1.5 REAP 式先验辅助臂（另立，不捆绑）

- REAP 式化学先验若发车，**可挂本臂 A/B**：F3 的 prompt v2 载体与 REAP 的
  prompt 先验属同一工程形态（teacher §四建议 2 允许合并设计）。
- "可挂"≠判定合并：REAP 臂若发车须另行单变量预注册（主终点、判定线、费用
  帽独立登记），其结果不进 F3 主臂判定；spurious 治理是次要矛盾的定位不变。
- 本稿不为 REAP 臂设定任何判定条款；仅登记其存在、可挂靠载体与不捆绑原则
  （同 G2 草稿 §1.2 语义）。

## 2. 上下文块内容规范（冻结版正文；双源支撑，逐条写死）

> 本节 = novel v2 任务书 `context` 块的完整内容规范。块①证据上下文来自运行
> 时检索产物的确定性摘要；块②底物约束块来自题面的确定性前向计算（复用 G2
> 判据代码）；块③为 prompt v2 契约。三块同受一个开关控制，版本串见 §1.1。

### 2.0 适用对象与总声明

- 适用对象：**novel 路由的全部任务**（含 `allow_novel_on_mapping_failure`
  与 `allow_novel_on_no_evidence` 两个入口——两入口的池状态语义不同，上下文
  如实区分，见 §2.1.1）。analogy / rank / recorded 路由**不经过**本块
  （analogy 有供体卡与编辑协议，rank 有候选卡，各有既定载荷）。
- **先验声明（总语义，prompt v2 与块内都要写）**：上下文块 = 先验参考信息，
  **不是判定门**；块内约束清单不禁止清单外转化（编目覆盖不全是编目的问题，
  不是候选的问题——mimo G2 风险 8 的 prompt 侧镜像）；最终裁决以确定性校验
  与既有门禁为准。此声明防两件事：约束块软门禁化（模型不敢提清单外合理
  转化）、证据摘要被误读为实测记录（novel 铁律 2"不得声称来自任何记录"
  不变）。

### 2.1 块①证据上下文（evidence_context）

#### 2.1.1 池状态摘要（pool_state——"区分两入口"的硬要求）

全部为运行时确定性聚合（零 LLM、零回查金标）：

- `n_evidences`：检索证据总数；按 kind 分布计数（recorded /
  rule_application / analog_transfer）；
- 合格 recorded 计数 + 不合格原因分布（`recorded_eligibility_reasons`
  的聚合计数——身份/方向/来源/条件四核各挂多少张）；
- analogy 供体资格状态（applicable / inapplicable + 拒因枚举计数，来自
  Phase C 资格块）；
- `pool_empty: true` 显式旗标（两入口之一"完全无证据"的如实呈现；
  `allow_novel_on_no_evidence` 入口恒为真）。

语义：让模型第一次知道"我是完全没证据在裸猜，还是有证据但没过门"——
E3 设计先例②的落地。

#### 2.1.2 top-N 证据化学摘要（evidence_digest——字段白名单封闭表）

- **选卡规则（确定性）**：按 `retrieval_rank` 升序跨 kind 取前 N 张
  （建议 **N = 5**，待冻结时定；同位次按 `evidence_id` 稳定序）；同
  `source_id` 的连续同型卡按反应类型去重后合并计数（去重留痕）。
- **字段白名单（v43-ctx-fields-1，封闭表——只用运行时字段，逐字段列死）**：

| 字段 | 内容 | 来源（运行时可算） |
|---|---|---|
| `reaction_type` | 反应类型/变换类（水解/氧化/还原/裂解/转移/异构化…枚举） | 卡 kind + transform/规则名/来源通道映射（确定性枚举映射表，版本化） |
| `conservation_delta` | 该卡反应自身的两侧守恒差（ΔC/ΔO/ΔN…） | 卡内底物/产物 SMILES 的确定性计数（同 G2 `analyze_side` 前向调用） |
| `substrate_relation` | 卡内底物 cn ↔ 题面 cn 的关系：same / analog-of / different（+差异位点计数） | cn_identity 比对 + Morgan 指纹相似度（mimo B1 字段 1 的摘要版） |
| `source_channel` | 来源通道（kind + source_id 前缀归并，如 uspto/envipath/eawag） | 卡字段直读 |
| `retrieval_rank` | 引擎参照位次（明示"参照位次，不是裁决结论"——E1 去锚定语义） | 卡字段直读 |

- **排除清单（红线级，封闭表）**：**产物 SMILES、产物身份（cn）、完整卡
  JSON、donor_refs 映射细节、`score` 数值、任何金标信息**。排除产物结构的
  理由：①防照抄（E3 禁令③"不得把未验证产物写成事实或照抄进报告"；novel
  铁律 2"所有提案都是新提案"——喂产物等于制造"抄检索产物再宣称为新提案"
  的通道）；②防变相 rank（candidates 恒空的语言学落实——模型拿到的是
  "什么类型的反应发生过"，不是"答案长什么样"）；③防"因检索出现就提交"
  （E2b 禁令原文语义）。
- 监测配套：`evidence_echo` 运行时指标（novel 答卷首位产物身份 ∈ 检索证据
  池产物身份集合的题数——零金标可算，§6.3 污染监测）。

#### 2.1.3 密度预算（E1 方法复用，版本化进 CONTEXT_ASSEMBLY_VERSION）

- **硬上限（常量、版本化，进块内 `density_budget` 留痕）**：块总字符上限
  建议 **1,600**、单条摘要上限建议 **320**（待冻结时定；对照：E1 实测 rank
  候选块 median 1,278 / max 2,912 字符且截断未触发——预算不是瓶颈、字段
  质量才是）；
- **截断规则（确定性、可重放）**：超预算按固定降级次序裁：①差异位点计数 →
  ②source_channel → ③conservation_delta 元素表截短（保留 ΔC/ΔO/ΔN 首位）；
  **never-drop：reaction_type / substrate_relation / retrieval_rank**；每次
  截断逐项记入 `density.truncated`；prompt 明示"被裁 ≠ 不存在"。
- **预算是换仓不是堆料**：novel 任务书现状极小（无候选块，发车前置件实测
  其分布，§8.3）；新增块有独立预算上限，不与其他路由载荷共享、不因块超限
  裁剪既有任务字段。

### 2.2 块②底物约束块（substrate_constraints——G1-b/G2-b/G3-b 的"正向版"）

> 判据源与 G2 同一份（[G2 草稿](../g2_prereg/PREREGISTRATION_G2_DRAFT.md) §2
> / `src/pathway_v43/validation/conservation.py` 纯函数层）；F3 取其**呈现
> 方向**：把"判定候选违规与否的规则"改写为"告诉模型这一步允许什么"的
> 先验。内容四件，全部从题面确定性算出、零 LLM、零金标：

1. **ΔC 允许集（G1-b 正向版）**：`ΔC ∈ {0, −1, −2, 键型合法裂解}`，逐题
   附上母体结构的可断键型事实（"母体存在 β-酮/β-羟基/芳环/烯丙位等可断
   C–C 键型"，由 SMARTS 机械判定）；增碳须题面登记碳供体（默认隐式供体恒
   为 {H₂O, O₂}，不含 HCO₃⁻/NH₄⁺——与 G2 §2.4 同源同默认，每默认放宽一项
   等于把门禁拆一角，呈现侧同理不加默认）。
2. **杂原子增删允许（G2-b 正向版）**：增默认仅 {O, H}（源 O₂/H₂O）；题面
   登记供体解锁集（扫描结果如实列出——dev 题卷条件块为空 → 恒为
   {H₂O, O₂}，代码现状 `nodes._surface_text`）；减少侧白名单全表（脱卤/
   脱硫（含脱磺酸）/脱氨脱酰胺/脱磷酸/脱糖基/脱酰基/含氧基团还原脱 O）。
3. **G3-b 官能团级可进攻键型清单**：底物具备的可进攻键型 → 允许的首步
   反应类（编目 `v43-g3b-catalog-1`，与 G2 同一份；逐题由
   `_attackable_smarts` / `_patterns_of` 前向计算）。清单附 G3-b 语义声明：
   "给出允许的首步反应类，不给位点排名"（G3-c 原子级区域选择性**不进**
   本块——确定性代码判不了，不装懂）。
4. **底物分子式与元素集**（计算基线披露：C/H/O/N/S/P/卤素计数——守恒
   判断的"分母"显式给模型）。

- **计算源声明（单一事实源）**：全部复用 `validation/conservation.py` 纯
  函数前向调用（`analyze_side(题面底物)` → 分子式/可进攻键型；
  `registered_donors(题面条件文本)` → 登记供体集；`_attackable_classes`
  → 允许首步反应类）——**与 G2 判定同一版本串、同一函数**，保证"prompt 里
  说的允许集"与"输出端判定的允许集"永不漂移（若 G2 判据升版，本块版本串
  随之升版 = 新身份 = 新预注册，不可能静默不同步）。
- **诚实性**：约束块可由代码逐题重放复算（纯函数、同输入同输出）；
  不含金标、不含题面底物/条件之外的任何外部信息。

#### 2.2.5 计算失败语义（对齐 G2 §2.6.5 "解析失败按未知不按零"）

题面底物解析失败 → 块内置 `unavailable: "substrate_parse_fail"`（prompt v2
声明此时按无约束处理）；**不 fail 整题**（novel 本来就能跑，辅助块不能把
能跑的题搞挂）、**不静默假装算过**（缺失必须显式标注，与门禁侧"不可审计
→ hold"同族语义的提示层版）。解析失败题计数入报告（聚合，供 §7.4 人审）。

### 2.3 块③ prompt v2（novel_proposal_v2.md）

- **输出契约逐字不动**：`{decision, products, uncertainty, reason}` JSON
  契约与 novel 解析器零改动（护栏：既有 novel 解析测试不改一行通过）。
- **铁律 1–4 不动**（最多 5 个产物/新提案语义/化学约束/提不出就空列表）。
- **新增条（文本方向冻结时定稿）**：
  - 上下文使用规则："`evidence_context` 是检索证据的化学摘要（不含产物
    结构），可作反应类型先验；**不得把摘要中出现的信息宣称为本题实测
    记录**"（铁律 2 的上下文版）；
  - 约束块使用规则："`substrate_constraints` 是从题面确定性算出的先验
    参考（ΔC 允许集、杂原子增删、可进攻键型清单），**不是判定门**——
    清单外转化不被禁止，但须化学上站得住；你的提案最终由确定性校验逐条
    检查"；
  - 两入口应答基调：`pool_empty: true` 时更保守（约束块为主）；
    "有证据但未过门"时参考摘要先验（类型信息为主）。
- **版本化**：新文件 `novel_proposal_v2.md` 常驻 `configs/prompts/`（两版
  SHA 恒在身份里）；装载由 policy 开关决定（`nodes._prompt_for` 分派，E1
  ranker_v2.md 同款）；**prompt 版本进 run identity**（§1.1 既有链路）。

### 2.4 任务书 schema

novel v2 任务书 schema 升版（具体值以实现时现行常量递增，建议
`v43-prediction-task-4`），新增 `context` 块（`{pool_state, evidence_digest,
substrate_constraints, density_budget}`）；v1 任务（开关缺省/显式 v1）与
历史行为**逐字节一致**——黄金测试钉死（§7 测试要求）。

## 3. 设计原则（先例硬证据 → 约束，冻结）

1. **E3/M2 教训——无过滤的宽载荷 = 灌噪声**：按检索序放宽的假想第 9–16 卡
   79% 违规（analog 16/16 全违规）；E3 实测 @5 反降、spurious 升 40。→ 本臂
   载荷是**摘要字段白名单**而非原始卡，且不改变任何入围/提交规则（只加
   信息、不加通道）。
2. **mimo A4——对同池候选恒真的信号是常数项**（E3 同类错误）。→ 约束块是
   **逐题计算**（题面各异，跨题有区分度）；证据摘要三主字段（反应类型/
   守恒 Δ/底物同一性）恰是 mimo A1/B1 认定**卡间区分度最大**的化学字段
   （"反应类型是同池候选区分度最大的单字段"）。
3. **mimo C2——novel 根因 = 确定性约束被卸掉**；最缺信息 = "这一步允许的
   骨架变化范围"（可代码算，能一次性覆盖 C1 第 6/7/8 类合计 ~50% 的错型）。
   → 约束块正中此缺口；C0 首位反复出现的通用小分子（CO₂/异丁烷/尿素型
   崩塌输出）是无约束自由作答的 signature，约束块的目标错型。
4. **E1 密度实测——预算不是瓶颈、字段质量才是**（rank 候选块 median 1,278
   / max 2,912、截断未触发）。→ 上下文块按"换仓"设计、独立预算、never-drop
   保区分度字段。
5. **M1 §4.3 教训——多组分判负的 7 题走 recorded/rank 确定性路由**，与
   novel 无关。→ 本臂 spurious 面只登记 novel 路由部分，不把 recorded/rank
   的口径题记到 F3 头上（口径 v3 已救该 7 题）。

## 4. 主终点与判定线（建议值；待冻结时定）

### 4.1 口径与基线

- 分母 dev v1.1 = 51（quarantine 后）；判分口径 v3；对照基线 C0 v3 =
  **14/51 = 27.5% @1**（QUARANTINE_EFFECTIVE 双轨主口径）。
- @5 与 spurious 的 51 分母基线：发车前从 dual_track_rescore 封存件确定性
  导出（剔除 5 道 quarantine qid）并另行封存——**与 G2 草稿同一次导出、
  两臂共用**；本稿只锚 @1 = 14/51。
- spurious 定义沿用 S1：答卷含 ≥1 预测产物且全部产物不中任何金标组分的
  题数（空答单列，不算 spurious）。

### 4.2 主指标与机制通道分解（承载面四类，如实预登记；防看分后自由归因）

- **主指标双终点**：(A) @1 净赢；(B) spurious 净降。
- 通道分解（数字为 dev 56 分母的 M1 池级口径；quarantine 修正注记随附）：

| 通道 | 承载面 | 目标块 | 机制 | F3 独有性 |
|---|---|---|---|---|
| 一：C1-novel（池有金标被送 novel） | **12 题**（C0-a；C0-b 11、E1 12；quarantine 后 ≈11，退化题 149-S01 剔出） | 块①证据上下文 | 证据摘要把"类似底物上发生过什么类型的反应"提前 → 模型以类型先验 + 参数知识生成池内已有答案分子 | **F3 独有**（G2 明确登记"金标不在答卷的题无法经本臂进入 top-5"——只有生成端能引入） |
| 二：spurious 的 novel 部分 | novel 可及面 **A(11)+C1-novel(11–12) ≈ 23 题**同量级（M1 精算、G2 草稿同口径）；mimo C1 第 5–8 类（位点 4/氧化当量 5/骨架 6/反应类型组装 7）是约束块瞄准的错型，第 6/7/8 类合计 ~50% | 块②约束块 | ΔC 允许集/杂原子/键型清单压掉"通用小分子崩塌输出"与守恒不可能的提案 | 与 G2 共享面（输出端过滤也吃同一面），机制端不同 |
| 三：A 桶（金标@2–5 全 novel） | **11 题**（六批恒 11，M1 §1.2；quarantine 名单与该桶零交集） | 块②约束块（+自排序联合面） | 生成端把金标排到位次 1（分布整形）——G2 的输出端自排序吃同一承载面、不同端 | 与 G2 共享面；联合设计 = 下一轮预注册，本臂不做 |
| 四：C2 生成面（池也无） | **14 题**（M1 §1.5"必须改生成"；quarantine 后 ≈10：结构性不可答 067-S03/114-S01/028-S04 与退化 149-S06 剔出，novel 部分 11→约 7） | 块②约束块（防瞎猜） | 无金标信号可用，纯负向约束（防凭空编造）；上界未知、判定实测 | F3 与未来生成类臂共同面 |

- **不在本臂通道内（如实登记）**：B 桶口径题 7 题（recorded/rank 确定性
  路由，口径 v3 已救）；recorded 直通/analogy 路由的其余题；rank 协议内部
  排序（dev 承载面 0，复确认）。
- **dev 承载面量级注记**：novel 覆盖 42/56 题（75%）、48 次 LLM 调用中
  42 次（87.5%）——dev 是"不等题源即可验证生成端杠杆"的仅存大面（298 侧
  I1 不可用；mibPOPdb 候选池预估 novel 桶 236/321 = 73.5%，池结构同型参照、
  题域不外推）。
- 51 分母下的精确桶读数（C1-novel/C2-novel/echo 基线）= 发车前从封存件
  确定性导出（§8.3 前置件，与 G2 基线同批导出）。

### 4.3 判定线（建议值，待冻结时定）

**dev_candidate（全部满足）**：

1. **@1 净赢 ≥3 题**（14/51 → ≥17/51 = 33.3%，+5.9pp）；
2. **spurious 净降 ≥3 题**（判定口径 = 总 spurious 题数下降；双轨披露含/
   不含弃权转化两列）；
3. **@5 不降**：净 0 为底线；−1~−2 题允许但须逐题归因说明（S1 E1 先例）；
   ≤−3 题击穿；
4. **空答护栏**：非弃权空答不升；**弃权（abstain）净增 ≤3 且逐题披露**——
   prompt 改版 + 约束可见可能推高弃权率（"知道约束后更常承认不会"是诚实
   行为，但"以弃权换 spurious 下降"超出 3 即判兑换击穿）；
5. **解析失败护栏**：error_kind 聚合的解析失败/重试耗尽占比不升（输出
   契约不动 → 应不变；异常上升 = prompt v2 文本缺陷信号，触发 §6 分支 2）。

**机制正向登记带（mechanism_positive_not_adopted；非采用）**：spurious
净降 ≥3 且 @1 净赢 +1~+2 且护栏全守 → 机制正向但不足采用线（恰为 teacher
§七路径预算对"novel 守恒 + REAP 先验"的 +1–2 预期带——该预算行未对通道一
（C1-novel，F3 独有面）单独计价）；是否收编由 teacher/用户裁定，**不改
判定线**，采纳走下一轮预注册。

**rejected**：@1 净赢 ≤0 或任一护栏击穿。
**inconclusive**：账目/终态/方差证据不完整（缺 usage、非法终态 >10%、
双采样缺失）或 §6.3 污染条款触发（判定作废）。
三态不写 adopted（发布默认变更另走发布审查，S1 惯例）。

### 4.4 数值依据

- **@1 ≥3**：S1 最小有用增益同刻度（3/56≈5.4pp ↔ 3/51≈5.9pp）；与 G2/G1
  判定线同刻度（臂间可比）；三通道合计承载面（A 11 + C1-novel ~11 + C2 部分
  生成命中）约 22–29 题的 ~10–27% 转化下限。
- **spurious ≥3**：novel 可及面 ~23 题的 ~13% 转化下限；spurious 读数在
  C0-a/b 双采样间相同（v2 口径均 36）→ 采样方差近零，净降 3 远超噪声带。
- **弃权 ≤3**：与判定线同刻度的弃权兑换上限（G2 草稿 hold ≤3 的 prompt 侧
  对应物）。
- **@5 底线**：**F3 是生成端臂（非纯重排）——@5 集合允许变化**（不同于 G2
  的"纯重排硬验收：候选集合与 @5 逐题不变"）：F3 改变生成本身，5 候选池
  内容可变；底线仍是净 0，降 = 生成质量恶化信号（净赢题不得靠牺牲 @5 换）。

### 4.5 统计与止损（S1 框架同款）

- **双采样**：判定读数基于两次独立采样（方案 A = 主臂与对照各两次新采样；
  方案 B' = 主臂两次新采样 + 封存 C0-a/C0-b 两个现成样本）。单次抽样不证
  因果（S1 纪律原文沿用；novel @1 翻转 ~7 题量级）。
- **符号检验（佐证列，不作门槛）**：对配对逐题差值（主臂−对照）的 @1 翻转
  与 spurious 翻转做两侧精确二项检验，两个采样上分别做并合并报。功效事实
  如实登记：n=51 下 @1 净赢 3 符号检验 p≈0.55，不可能显著——主判定按预
  注册点估计线执行，不以不显著推翻已达线结果、不以显著加持未达线结果。
- **累计止损门 +8pp 沿用**（teacher §四 S1）：已判臂对其登记对照的 @1 净赢
  （pp）累计 <+8pp → 停止冲刺、出止损结论、不带弱证据碰 298。判定点 =
  F3 判定后立即评估。累计起算口径待冻结时定（建议同 G2：口径 v3 + 51 分母
  新链起算，S1 四臂 v2 链判定已由 teacher §七路径预算承接、不混算）。
- **里程碑口径**：30% 里程碑 = 16/51（31.4%，dev 刻度）；F3 净赢 3 →
  17/51 过线；但 30% 里程碑的判定场所在题源落地后的新盲测集（teacher
  §七/任务书），dev 结果只作开发期判定（I1）。

## 5. 对照设计（两选项，待冻结时定）

**共同前提（设计钉死）**：`novel_context_block = v1` 时任务书、prompt 选择
与调用行为与 C0 **逐字节一致**（no-op 回归 + v1 黄金测试钉死，§7/§8.3）；
novel_proposal_v2.md 文件常驻树内但不进 v1 路径（两版 SHA 恒在身份，文件
存在本身不构成差异）。

**G2 式"答案级离线重放"对 F3 结构性不可用**（须先声明）：F3 单变量在生成
端输入侧——模型输入变了必须真调用，封存答卷重放测不了新分布。F3 能拿到的
最强省费形态是方案 B'（封存 C0 作对照读数 + 主臂新跑）。

### 方案 A：同代码关上下文重跑 C0（in-run 双臂新跑）

- 结构：主臂（开关 v2）与对照（开关 v1）各为新批次根、同 commit、同资产、
  同协议，各 ≥2 次独立采样（双采样）→ 4 个计费批次。
- 配对性质：**身份级配对**（除开关外逐字段相等，S1 纪律字面合规）；答案级
  不配对——novel 采样方差（@1 翻转 ~7 题量级）直接进入臂差，靠双采样均值
  与逐题配对吸收。
- 费用：单批帽建议 ¥3.5（novel 调用 input +~15–25%：任务书 +≤1.6k 字符 +
  prompt v2 +~1.2k 字符，以 §8.3 实测校准；S1 单臂单批 ¥2.3–2.5 基数）；
  总帽 ≤¥14（4 批 + 烟测）。
- 附加价值：验证开关 + prompt v2 进 run identity 的生产 in-run 形态（与
  G2 方案 A 对称）。

### 方案 B'：封存 C0 对照 + 主臂新跑

- 结构：对照 = dual_track_rescore 封存 C0-a/C0-b（v1 读数即 off 读数；
  两个样本 = 现成双采样）；主臂 = 开关 v2 新跑 2 批（双采样）。
- 配对性质：身份级 + **身份差异登记**（封存 run 产于无上下文代码路径的
  commit；以 no-op 回归 + v1 黄金测试支撑行为等价 off ≡ 无操作）；省 2 个
  计费批。
- 费用：主臂 2 批 ≤¥7 + 烟测；总帽 ≤¥8。
- 风险：对照臂的历史采样方差与主臂新采样方差叠加于臂差（比方案 A 少一层
  同 commit 控制）。

### 两选项差异一览

| 维度 | A（in-run 双臂新跑） | B'（封存对照 + 主臂新跑） |
|---|---|---|
| 配对严格度 | 身份级（代码/资产逐字段同） | 身份级 + 身份差异登记（no-op 回归支撑） |
| 采样方差 | 含 novel 重采样方差（双采样吸收） | 主臂重采样 + 对照历史采样（两层叠加） |
| 费用 | ≤¥14（4 批） | ≤¥8（2 批 + 烟测） |
| 形态 | 生产 in-run 形态验证（双臂） | 主臂 in-run + 对照历史读数 |
| 前提 | 无额外前提 | no-op 回归 + v1 黄金测试通过 |

**建议**：A 为判定主案（生成端臂的身份级配对最干净、无身份差异登记负担、
双臂同 commit），B' 为省费备选（预算紧或想先快速拿读数）。**待冻结时定。**

## 6. 失败分支预声明（对齐 teacher §七；届时不得临时找理由）

1. **线未达但护栏全守**（@1 净赢 <3 或 spurious 净降 <3）→ rejected（或
   mechanism_positive_not_adopted 带内登记）；spurious 治理是次要矛盾的定位
   不变；**不得自行加臂**（不叠 G2/REAP 硬凑、不调 N/白名单/预算/键序
   重跑——任何改动 = 新版本走新冻结链 + 新预注册）。
2. **护栏击穿**（@5 净降 >2、非弃权空答升、弃权净增 >3、解析失败占比升、
   spurious 净升）→ 实现或白名单或 prompt 文本缺陷登记 → 新冻结链 →
   新批次根重跑；不得在原批次上静默改。
3. **上下文块变相污染（自查条款，红线级）**——"把答案喂给模型"的三道防线：
   - **预防**：字段白名单封闭表（§2.1.2 排除清单：产物 SMILES/身份/完整卡/
     映射细节/金标任何信息）；上下文字段必须来自运行时检索证据与题面确定性
     计算，**不得含金标信息**（写入红线，§9）。
   - **发车前审计**（零 LLM 离线，金标仅本地离线进程）：对 51 题 novel 任务
     的上下文块做与金标的**零交集断言**（逐题比对，仓内只进聚合计数；
     含金标中间件入 gitignored）——发现交集 >0 即判据/实现缺陷，判据回修
     走新冻结链，不得用该结果在冻结版内调参。
   - **运行时监测（零金标指标）**：`evidence_echo` = novel 答卷首位产物身份
     ∈ 检索证据池产物身份集合的题数（基线从封存 C0 导出；M1 §1.4 记录
     "金标不在池却命中"5 题全 novel 为参数知识直出——echo 指标与该读数
     互补，可区分"模型自己想到"与"从上下文抄来"）。F3 臂该读数**异常上升**
     = 上下文把池内答案喂给模型的信号 → 触发逐题人审（gitignored）→ 确认
     照抄 → **判定作废（inconclusive）**，缩白名单走新冻结链。
4. **约束块反向先验**（模型被清单框住：清单外合理转化不敢提 → C2 生成面
   命中反降 / @5 降）→ prompt v2"先验非门禁"文本与 §2.0 总声明回修走新
   冻结链（mimo G2 风险 8"编目覆盖不全系统性偏向已知化学、削弱 novel 臂"
   的 prompt 侧镜像）；不在本臂判定内消化。
5. **净赢为负**（约束块把模型推向系统性错型：如 ΔC 允许集呈现导致过度脱羧
   类提案——mimo C1 第 7 类的反向风险）→ 判据呈现方向回撤登记 → 新冻结链。
6. **F3 rejected 且 G2 rejected 且深位付费臂维持不发车**（门 1 迭代 2 已落
   "明显不过"）→ 闭卷 30% 里程碑重估，**teacher 侧重新审议目标，学生不得
   在 dev 上加臂硬凑**（teacher §七失败分支第 3 档原文）。

## 7. 工程量评估

| # | 件 | 内容 | 复用 | 预估人日 | 测试要求（全部离线零 API） |
|---|---|---|---|---|---|
| ① | 上下文块组装 | pool_state 聚合 + evidence_digest 选卡/字段映射/去重 + 密度预算与截断留痕 + policy 开关 fail-closed 归一 + 任务 schema 升版 | **E1 四层卡呈现工程**（`_apply_rank_presentation_v2` 的密度预算/截断/留痕方法、开关链路、去锚定语义） | 1.5–2 | payload 形状（v2 开：context 块存在、白名单逐字段核对、排除字段零出现；v1 黄金回归：任务书与 HEAD 逐字节一致）；开关非法值装配期 fail-closed；密度截断确定性重放同输出 |
| ② | 约束块计算 | ΔC 允许集/杂原子/供体扫描/G3-b 清单的题面前向计算与渲染 + 解析失败语义 | **G2 判据代码**（`validation/conservation.py` 纯函数：`analyze_side`/`registered_donors`/`_attackable_classes`——已存在、已有 29 例夹具） | 1–1.5 | 前向计算与 G2 判定同源一致性（同一底物两侧调用结果对拍）；解析失败 → unavailable 标注不 fail 整题；零金标零题面外信息断言 |
| ③ | prompt v2 | novel_proposal_v2.md 撰写 + `prompt_versions` 增键 + `nodes._prompt_for` 分派 | **E1 ranker_v2.md 链路**（零新身份代码；两版 SHA 恒在身份） | 0.5–1 | 提示词与代码枚举一致性（若引入枚举）；SHA 进身份端到端；输出契约不变——既有 novel 解析测试不改一行通过 |
| ④ | 发车前置件 | novel 任务书字符分布实测、evidence_echo 基线导出、上下文零金标审计、no-op 回归 | 封存 C0 答卷/任务书（只读）+ M1 的池身份集机器（cardval verdicts） | 0.75–1 | §8.3 前置件三件套 |
| | **合计** | | | **3.75–5.5 人日**（不含发车后跑分/判定/mimo 复核） | |

- ①②③ 均为纯增量（v1 路径零改动）可并行开工；② 的直接前提 = G2 判据代码
  已落盘（其版本串冻结状态随 G2 冻结链走，见 §8.1）。
- 判据实现不新写规则：本臂不新增任何化学规则——约束块是 G2 已冻结判据的
  前向呈现，规则级工作量已在 G2 臂内完成（这是 F3 工程量可控的根本原因）。

## 8. 冻结链状态声明

### 8.1 判据双源支撑状态

- **机制源**：mimo E1 化学评审 §C2（gitignored，本稿只取机制不引 SMILES：
  novel 根因 = 确定性约束被卸掉；最缺信息 = ΔC 允许集/杂原子集/位点清单）
  + §A1/A3/B1（反应类型区分度、裁决先验序、卡上最该有的字段）；
- **内容源**：mimo 守恒判据评审（G1-b 骨架启发式 / G2-b 分档 / G3-b 三层
  拆分）→ 采纳登记 §2（全部采纳为 T8 G2 判据底稿）→ G2 草稿 §2 已把判据
  落为版本化正文（`v43-cons-1` 等六常量，`validation/conservation.py` 已
  实现）→ **本臂 §2.2 复用同一版本串的前向呈现**。判据冻结状态随 G2 冻结
  链：**G2 判据未冻结则 F3 约束块内容同未冻结——F3 冻结须在 G2 判据冻结
  之后或同批确认**（引用其冻结 SHA）；
- **程序互证**：M1（路由 × 桶交叉表、C1-novel 12 题、novel 42/48）、M2
  （79% 违规——白名单而非原始卡的设计依据）、E1 密度实测（预算方法）、
  E3 载荷 no-op 教训（不改变入围/提交规则）。

### 8.2 本稿状态与冻结生效条件（含拍板点状态节，对齐 G2 §7.2）

- 当前：**DRAFT**。生效链：本稿落盘 → 用户确认冻结（六处"待冻结时定"拍
  板：§4.3 判定线数值、§4.5 止损起算口径、§5 对照方案 A/B'、§2.1.2 字段
  白名单终表、§2.1.3 N 与密度预算数值、§2.3 prompt v2 文本定稿）→ FROZEN
  （整文件 SHA256 重登记，发车后修改一律无效）。
- **拍板点状态（2026-09-30）**：本稿为首个草稿轮，尚未向用户提问——以下
  三处为最高优先拍板点，按建议默认挂起：①**对照方案 A 为判定主案**（身份
  级配对最干净，¥14 帽）、B' 为省费备选；②**N = 5、块上限 1,600 字符、
  单条 320 字符**；③**字段白名单按 §2.1.2 封闭表**（产物 SMILES/身份排除
  ——机制强弱的关键取舍：排除则 C1-novel 通道只喂"类型先验"，纳入则有
  照抄与变相 rank 风险；本稿建议排除）。**以上为建议默认，未冻结**，随
  发车授权一并确认。
- **发车条件**：(1) teacher 对 30% 里程碑的裁定回来；(2) 用户授权发车；
  (3) §8.3 前置件完成；(4) G2 判据版本串冻结（约束块内容源前提——G2 已
  冻结则直接引用其冻结 SHA）。

### 8.3 发车前置件（冻结后、判定前）

1. **实现 + 合成夹具**：§2 全部规范、白名单、密度预算、截断规则、计算
   失败语义先钉 pytest 合成夹具（每块每规则至少一例：pool_state 两入口、
   digest 选卡/去重/截断/never-drop、约束块四件、unavailable 语义、v1
   黄金回归、no-op 回归——**零真实金标**）；
2. **no-op 回归 + v1 黄金测试**：开关 v1 时任务书与调用行为与 HEAD 逐
   字节一致（方案 B' 启用条件）；
3. **零金标审计与基线导出（零 LLM 离线，金标仅本地离线进程）**：(a) 51 题
   novel 任务上下文块与金标**零交集断言**（仓内只进聚合计数）；(b)
   `evidence_echo` 基线（封存 C0 novel 题答卷首位 ∈ 证据池身份集的题数）；
   (c) novel 任务书字符分布实测（校准密度预算与费用帽）；(d) @5/spurious
   的 51 分母基线从 dual_track_rescore 封存件确定性导出（与 G2 草稿同一次
   导出、两臂共用）；(e) 51 分母下 C1-novel/C2-novel 精确桶读数。

### 8.4 跑分后 mimo 结果复核（AGENTS.md 触发点 3）

F3 判定（按本预注册即时出）后，对答题结果出一份 mimo 评审请求 md（自包含、
默认规则级不含金标；涉题面/金标数据外发须用户逐次拍板；由用户送 mimo，
回复原文落盘 docs/，含金标往来入 gitignored）——重点：净赢/净输题化学
解读（约束块先验是否起效/框死）、spurious 题归因（崩塌输出是否消失）、
证据摘要是否被误用为"实测记录"（铁律 2 的实际遵守度）。**后置不改已冻结
判定；结论采信到与程序证据互证的程度为止；采纳走下一轮预注册。**

### 8.5 预算帽建议（待冻结时定；参考 S1 单臂单批 ¥2.3–2.5 + G2 草稿 ¥3/批）

- 方案 A：单批帽 ¥3.5（载荷 +15–25% 余量，§8.3(c) 实测校准）；总帽 ≤¥14
  （4 批 + 烟测）；
- 方案 B'：主臂 2 批 ≤¥7 + 烟测；总帽 ≤¥8；
- token 口径：novel 任务书现状（无候选块，预计 2–4k 字符/题）+ 上下文块
  ≤1.6k + prompt v2 +~1.2k → input +~2.8k 字符/调用 ≈ +1.4–2k tokens/
  novel 调用；每批 42 次 novel 调用 → +59–84k input tokens/批（对 ¥2.3–2.5
  基数约 +15–25%，以实测为准）。

## 9. 红线附录

- **金标隔离**：金标 SMILES 永不进 git 跟踪文件（本稿与全部 F3 产物只含
  qid/计数/位次/旗标）；金标仅在独立评分/审计进程打开；含金标中间件入
  gitignored。
- **上下文不喂答案（本臂特有红线）**：上下文字段**必须来自运行时检索证据
  与题面确定性计算，不得含金标信息**（§6.3 自查条款：发车前零交集断言 +
  运行时 evidence_echo 监测）；证据摘要**不含产物 SMILES/身份**（防照抄、
  防变相 rank——E2b 禁令"禁止将原始 rule/analog 卡直接加入任务或因其检索
  出现就提交"的 F3 继承形态）；字段白名单封闭表版本化（v43-ctx-fields-1），
  看分后改白名单 = 新版本走新冻结链。
- **门禁只紧不松**：路由决策、资格门、`validate_products`、报告裁决逐条
  不动；candidates 恒空（§1.2）；本臂只在输入侧新增信息——"只加信息不改
  通道"满足"不放宽"的论证：入围、提交、验证、排序规则零变化，模型决策
  空间不变，信息面变宽不等于门禁变松。
- **预注册先于跑分（I2）**：本稿冻结先于任何 F3 判定读数（含前置件审计
  之外的任何跑分）；看分后改白名单/N/预算/prompt 文本一律无效，触发新
  冻结链重跑。
- **prompt 版本进身份**：novel_proposal_v2.md SHA 经 `prompt_versions` 进
  run/batch/prediction_task 三级身份（既有链路零新代码）；文件常驻树内、
  两版 SHA 恒在身份里，不可能静默混批。
- **298 不碰（I1）**：本臂仅 dev；不用 298 逐题信息调判据；所有数字带题域
  标签（dev = B1 环境路径中间步骤）；mibPOPdb 73.5% 仅作池结构参照不外推；
  双向不外推。
- **判分/评测零 LLM**：上下文组装、约束块计算、判定、统计全确定性；mimo
  评审不参与判分。
- **封存与批次纪律**：封存 run 只读不覆写；新实验一律新批次根；跨身份
  resume 端到端拒绝；历史读数不覆写；不 git commit；工作树未提交改动全部
  保留。

---

## 附录 A：机器可读 diff（冻结版摘要；JSON）

```json
{
  "prereg_id": "PREREG-F3-v1-DRAFT",
  "arm": "F3-NovelCtx",
  "single_variable": {
    "switch": "novel_context_block",
    "values": ["v1", "v2"],
    "versions": {
      "context_assembly": "v43-novelctx-1",
      "ctx_field_whitelist": "v43-ctx-fields-1",
      "cons_filter_reused_forward": "v43-cons-1",
      "normalization_reused": "v43-norm-1",
      "g3b_catalog_reused": "v43-g3b-catalog-1",
      "donor_registry_reused": "v43-donor-registry-1",
      "prompt": "novel_proposal_v2.md (sha256 via prompt_versions)"
    }
  },
  "scope": {
    "routes": ["novel"],
    "position": "build_prediction_task_novel_branch + _prompt_for",
    "routes_excluded": ["recorded", "rank", "analogy"],
    "routing_unchanged": true,
    "candidates": "always_empty",
    "parse_contract": "unchanged",
    "g2_switch": "off_for_this_arm"
  },
  "context_blocks": {
    "evidence_context": {
      "pool_state": ["n_evidences", "kind_distribution",
                     "eligible_recorded_count_and_reason_counts",
                     "analogy_eligibility_status",
                     "pool_empty_flag"],
      "evidence_digest": {
        "top_n": 5,
        "selection_rule": "retrieval_rank_asc_stable",
        "whitelist_fields": ["reaction_type", "conservation_delta",
                              "substrate_relation", "source_channel",
                              "retrieval_rank"],
        "excluded_redline": ["product_smiles", "product_identity",
                              "full_card_json", "donor_refs_detail",
                              "score", "any_gold"],
        "density": {"block_char_cap": 1600, "per_entry_cap": 320,
                    "never_drop": ["reaction_type", "substrate_relation",
                                    "retrieval_rank"]}
      }
    },
    "substrate_constraints": {
      "source": "conservation.py_forward_calls_reusing_g2_versions",
      "content": ["dC_allowed_set_g1b_positive",
                  "heteroatom_add_remove_g2b_positive",
                  "g3b_attackable_bond_class_list",
                  "substrate_formula_elements"],
      "semantics": "prior_not_gate",
      "compute_fail": "unavailable_flag_not_fail_not_silent"
    }
  },
  "endpoint": {
    "denominator": "dev_v1.1_n51_quarantine",
    "scoring": "caliber_v3",
    "baseline_C0_v3_at1": "14/51",
    "primary": ["at1_net_win", "spurious_net_reduction"],
    "carriers": {
      "C1_novel_evidence_ctx_target": "12 (post-quarantine ~11)",
      "spurious_novel_face": "A(11)+C1-novel(11-12)~23",
      "A_bucket_joint_face": 11,
      "C2_generation_face": "14 (post-quarantine ~10)"
    },
    "suggested_lines_to_be_frozen": {
      "at1_net_win_min": 3,
      "spurious_net_reduction_min": 3,
      "at5_floor": "net_0; -1..-2 with_per_question_attribution; <=-3 breach",
      "empty_guardrail": "non_abstain_empty_no_rise; abstain_net_increase<=3",
      "parse_fail_guardrail": "no_rise"
    },
    "secondary_band": "spurious_-3_and_at1_+1..+2_all_guardrails_held -> mechanism_positive_not_adopted",
    "stop_loss_cumulative_pp": 8,
    "stats": "double_sampling + two_sided_exact_binomial_sign_test_supportive_only"
  },
  "control_design": {
    "options": ["A_in_run_paired_rerun", "B_prime_sealed_C0_control_plus_main_rerun"],
    "recommended": "A",
    "decision": "to_be_set_at_freeze",
    "note": "G2_style_offline_answer_replay_structurally_unavailable",
    "option_A_cost_cap_cny": 14,
    "option_B_prime_cost_cap_cny": 8
  },
  "order_recommendation": "G2_first_then_F3",
  "freeze_chain": {
    "criteria_sources": ["mimo_e1_chem_review_C2_mechanism",
                         "mimo_conservation_rules_review_response",
                         "MIMO_REVIEWS_ADOPTION_REGISTER_S2",
                         "COVERAGE_STAT_M1_M2"],
    "status": "DRAFT_awaiting_user_freeze_confirmation",
    "constraint_block_freeze_depends_on": "G2_criteria_version_string_frozen",
    "launch_gates": ["teacher_30pct_milestone_ruling", "user_authorization",
                     "fixtures_plus_noop_regression_plus_zero_gold_audit"]
  },
  "pollution_self_check": {
    "pre_launch": "zero_intersection_audit_context_vs_gold_offline",
    "runtime_metric": "evidence_echo_novel_top1_identity_in_pool",
    "breach": "verdict_voided_inconclusive_new_freeze_chain"
  },
  "red_lines": ["gold_isolation", "context_feeds_no_answers_field_whitelist",
                "candidates_always_empty", "gates_tighten_only",
                "prereg_before_scoring", "prompt_version_in_identity",
                "no_298", "zero_llm_judging", "sealed_readonly",
                "new_batch_root", "no_git_commit"]
}
```
