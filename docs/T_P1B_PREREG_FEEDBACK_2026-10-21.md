# P1-B 修复反馈（feedback）预注册草案（2026-10-21）

> **题域：[298域] = RHEA 通用酶学 / 已见题（post-hoc）。** 本文全部计数、
> 口径与结论只在该题域成立；与 dev（B1 环境路径中间步骤）双向不外推。
>
> **性质：效度修复，不是提分项。** P1-B 修的是「声明主产物 ≠ 执行产物」
> 这一效度缺口；实验臂可能因为残余拒而**降分**。本批不设「提分线」，
> 不承诺 F（feedback）能救回任何一条 absent；只测量修复/拒绝对 298 题
> 配对读数的影响。
>
> **文档状态：DRAFT_NOT_SIGNED。** 本文件是预注册草案；`approval_status`
> 待 CC/代决填写，四文书 SHA 为占位。只有签字并回填 `approved_at`、
> `approval_source`、四文书 SHA256 后，才可作为 `preregistration_approval.json`
> 的批准文本。预注册先于付费；本草案不构成付费/发车授权。
>
> 上游：P0b/D-6 合同（`docs/T_H_P0B_D6_CONTRACT_2026-10-20.md`）、
> P1-B 设计稿 §2A（`docs/T_H_P1B_RECONCILIATION_GATE_DESIGN_2026-10-21.md`）、
> P1-B A 实施报告（`docs/T_H_P1B_A_FEEDBACK_IMPL_2026-10-21.md`）、
> qwen 复审（`docs/T_H_P1B_A_FEEDBACK_QWEN_REVIEW_2026-10-21.md`）、
> T-I 预注册（`docs/T_I_PREREG_2026-10-20.md`）、
> P2 预注册与 CC no-cap 决定（`docs/T_P2_PREREG_FULL_V2_2026-10-21.md`、
> `docs/P2_CC_DECISION_FULL_V2_2026-10-21.md`）。

## 0. 一句话与两臂

P1-B 是 **298 题域内、已见题 post-hoc 的单变量效度修复批**：对照臂保持
P0b 的 `disclose`（提交前不拦截、只保留 P0b 披露），实验臂启用 `feedback`（对 `principal_absent`
候选先用现有 2 轮 `format_feedback` 让模型改 edits；2 轮仍 absent 才拒
`declared_product_not_executed`，不写事件，分母仍 298）。

| 臂 | 代号 | `P0B_D6_RECONCILIATION_POLICY` | 行为 | 角色 |
|---|---|---|---|---|
| 对照 | **D 臂** | `disclose` | 不做提交前对账/反馈/拒；保持 P0b 披露口径（合成场景已证与基线载荷等价，不替代 298 全链重跑） | 基线 |
| 实验 | **F 臂** | `feedback` | `principal_absent` → 有界反馈 → 改对则提交；耗尽/不可修 → 残余拒 | 效度修复 |
| 不进批 | `gate` | `gate` | 直接残余拒，不发反馈 | 仅实现内对照/残余兜底，不单独发车 |

> 设计稿里的「A = 修复反馈」「B = 硬门」是方案字母；本预注册为避免与
> T-I 的 A/B 模型臂混淆，统一用 **F（feedback）/ D（disclose）**。
> `gate` 不作为第三臂发车；如 CC 要求 gate 对照，另立预注册。

## 1. 目的、可声明与不可声明

### 1.1 目的

1. 在 298 题域、同模型/同池/同检索/同判据/同配置下，测量「提交前修复
   反馈 + 残余拒」相对「只披露」对配对读数的影响；
2. 把**修复面**（触发了多少 absent、修回多少、残余拒多少）与**代价面**
   （hit@1/@3/@5、strict、partial/unmatched、失败/unknown）分开报告；
3. 为「是否保留 feedback 作为默认效度门」提供一次付费探针证据，而不是
   宣布提分或能力提升。

### 1.2 可以声明

- 本批 298 题域、本任务形态下的逐臂 hit@1/@3/@5、strict 覆盖 U、
  partial/unmatched 计数；
- F−D 的逐题配对新增/损失/净增、discordant 对数、精确 McNemar p
  （仅描述性，不作放行/否决线）；
- 事件级触发/修复/残余拒计数、反馈轮数、失败/unknown/零调用计数；
- usage 的已知部分；金额未知部分如实标 unknown；
- 146 条 absent 的程序级分类在本批的实际触发/修复/拒分布。

### 1.3 不可声明

- 不声明「提分」「能力提升」「F 有效」或任何收益承诺；
- 不声明 F 的回收率上限/预期值；回收率只能新批测量，且本批只给点计数；
- 不声明 146/58 条 absent 的化学真伪已解决；程序级修复 ≠ 化学正确；
- 不把 298 已见题 post-hoc 结果外推到 dev、新题、闭卷或其它模型；
- 不把 strict 覆盖、候选提交、事件新增混写成 hit@1；
- 不在未完成全 298 评分时用 interim 读数下结论或提前停。

## 2. 单变量与冻结面

### 2.1 唯一变量

**`P0B_D6_RECONCILIATION_POLICY`**：D 臂=`disclose`，F 臂=`feedback`。
两臂其它全部同值：模型、题卷、代码（含 P1-B patch）、编译/池/来源/归一/
路由、语料检索、排序、判分、profile_policy、gate、worker、超时、重试、
温度策略、最大 token 策略、证据卡开关、分母。

> 该 env **不在** `run_identity`/profile 块（未改 `profile.py`）。发车脚本
> 必须把它的值显式写入每臂 `arm_config.json` 与批根记录，并在 smoke2
> 核对；两臂只允许这一项不同。D/F 臂名与 env 值必须一一对应，禁止
> 靠口头/目录名推断。

### 2.2 冻结项（发车前写死，批中零改动）

| 项 | 冻结值/口径 | 说明 |
|---|---|---|
| 题卷 | `questions.jsonl`，298 行，SHA256 `9f5955d418c2f3876f13cdc9bebea46a1d545d037b182fa5089f56293ff9211c` | 发车日实核；与 T-I/T-H 同源 |
| 代码 | 基线 `11aeeaf` + P1-B patch `0ae6535733cf97cbb4439b12e27528fcc7777a770aded2aee8ed8c68a18f491f`；合并后 commit 发车日实核 | 两臂同树；与 T-I/P2 非同树，禁止混比 |
| 编译/池/来源/归一/路由 | `s5b-compiler-6` / `s5b-pool-policy-9` / `s5b-recorded-source-4` / `record-side-formnorm-1` / `s5b-analog-route-f1f4-1` | 与 T-I/T-H r2 同值 |
| 语料检索 | `s5b-corpus-retrieval-6` | 与 T-I/T-H r2 同值 |
| 排序 | `s5b-rank-policy-2` | 与 T-I/T-H 同值 |
| 判分 | v2 headline + v1 敏感性；v3 纯披露；零 LLM | 判分链不改 |
| `profile_policy` | `max_real_model_requests=3`；`max_format_feedback_rounds=2`；其余 search_limits 沿 `CHAIN13_PROFILE` | 两臂同值；反馈复用这 2 轮，不新增预算 |
| gate | RPM 200 / TPM 3,000,000 / `max_calls=4470`/臂 | 与 T-I 同参；no-cap 下仍是工程硬门 |
| workers | 8 / max_in_flight 8 | 同 T-H/T-I |
| 证据卡 | 关（`evidence_card_enabled=false`） | P1-B 不是 P2，不启用 v2 证据卡 |
| 逻辑调用上限 | 每题至多 3 次逻辑调用 + 2 轮格式反馈 | 反馈轮计入同一 qid 的 3 次真实请求额度 |
| 金额帽 | **无**（`no_monetary_cap_user_decision`，沿用 CC 2026-10-20/21 口径） | 见 §7；no-cap ≠ 无限制 |
| HTTP 重试 | 传输失败自动重试 1 次；429 有界退避；timeout 不重试 | 同 T-I/T-H |
| 超时 | 3600s/调用，超时不重试 | 同 T-I/T-H |
| 温度 | 不发 `temperature`（`temperature=None`） | 两臂一致；env 出现温度/思考键在装配期 fail-closed |
| 最大 token | 不发 `max_tokens`（no-cap 模式，提供者默认） | 两臂一致；不得一臂单独设值 |
| 请求参数 | 两臂 `V43_LLM_REQUEST_PARAMS` 逐字同值 | 只核键值是否同值，不读/打印 key |
| 数据面 | `data_scope=real`；分母固定 298 | 失败/零调用不剔题 |

### 2.3 模型

- P1-B **不比较模型**；`model_id` 两臂必须同值。
- 取值来源：T-I 最终有效批选定模型；若 T-I 未出结果，由 CC 指定并在
  发车前写死。草案阶段 `model_id=TBD`。
- 发车后不得换模型；换模型 = 新预注册。
- P1-B 结果只对本批 `model_id` 成立，不得外推其它模型。

## 3. 触发面与流程（F 臂）

### 3.1 触发面（只碰 `principal_absent`）

| 对账结果 | F 臂行为 | 是否拒 |
|---|---|---|
| `consistent` | 正常提交 | 否 |
| `principal_stereo_only` | 正常提交 | 否 |
| `principal_isomeric_unspecified` | 正常提交 | 否 |
| 合法 copy（`consistent` / `not_applicable`） | 正常提交 | 否 |
| 其它 inconsistent 子类（`copy_contract_violation` / `expectation_contradiction` / `assembly_contradiction` 等） | 正常提交，不反馈 | 否 |
| `unknown`（缺资料/解析失败/执行未核） | 正常提交，保留 proof_scope | 否 |
| `not_applicable`（确知空声明） | 正常提交 | 否 |
| 合法多碎片/多组分主产物 | 按 `consistent` 正常提交 | 否 |
| **`principal_absent` + principal 边界 `model_declared`** | **发起有界反馈** | 改对则否；耗尽/不可修则拒 |
| `principal_absent` + 非 `model_declared` 边界 | 不发反馈，直接残余拒 | 是（本批 146 条均为 `model_declared`，预期不触发） |

- 判据复用 P0b 单一入口 `reconcile_declared_vs_executed`；不另写字符串
  比较、不新造身份、不改 R1–R7/`ADMISSION_SUBMITTABLE`。
- 插入点在 admission 可提交之后、事件提交之前；只对本来会提交的候选
  对账，避免为必被 admission 拒的候选花反馈调用。
- `disclose` 下不得调用 `reconcile_declared_vs_executed`、不得写
  `p0b_d6` 键、不得登记反馈轮。

### 3.2 反馈与残余拒

1. 执行 edits → audit → admission（R1–R7 不变）；
2. 构建事件/投影 → 同一 P0b 判据对账；
3. `principal_absent` + `model_declared`：不提交；登记/复用
   `format_feedback` 轮 → 取 revised `reaction_spec`；
4. revised 只允许改 `edits/donor/alignment`；身份字段
   （`product_smiles/coproducts/declared_copy_components/requirements/
   dependencies/assumptions/transformation_ref/expectation/compile` 等）
   必须不变；新 `hypothesis_id` 必须 == action `subject_ref`；
5. 重新执行/对账；非 `principal_absent` ⇒ 正常提交；仍 absent 且还有
   轮数 ⇒ 再反馈；
6. **2 轮仍 absent / 反馈轮预算 0 / 响应不可解析 / 改身份字段 /
   edits 非法或未变 / 非 `model_declared`** ⇒ 残余拒：
   `declared_product_not_executed`；**不写事件**；action 记
   `admission_rejected`；候选/池/分母不变；
7. 传输失败/超时/悬空 ⇒ 既有 run 失败语义（失败题留分母），不吞成
   「拒」或「成功」。

### 3.3 预算（不新增）

- 同一 purpose `format_feedback`；同一持久计数
  `format_feedback_rounds_used(ledger, action_id)`；同一上限
  `max_format_feedback_rounds=2`；
- 每 expand action 最多 2 轮；每轮仍受每题 `max_real_model_requests=3`
  即时占额；
- 不新增 purpose、轮数预算、每题调用上限或计数器；
- 33 题有 2–5 条 absent 事件，同题多条 absent 会互相争用 3 次请求额度；
  后面的 absent 可能拿不到反馈、直接残余拒。这是 F 的真实代价，不是
  测量缺失。

## 4. 主读数与报告口径

### 4.1 题级主读数（分母 298）

| 指标 | 定义 | 角色 |
|---|---|---|
| hit@1（v2 headline） | 首个 strict 命中位次 ≤1；分母 298 | 主描述读数 |
| hit@3 / hit@5（v2） | 首个 strict 命中位次 ≤3 / ≤5 | 次要描述 |
| strict 覆盖 U | `buckets.matched_strict` 计数 | 覆盖轴 |
| partial / unmatched | 三桶计数 | 桶结构 |
| 逐题配对 | 每 qid 的 hit@1/@3/@5、strict、桶、rank | 配对唯一数据面 |
| 新增/损失/净增 | F 有 D 无 = 新增；D 有 F 无 = 损失；净增 = 新增 − 损失 | 描述性 |

- 配对符号与 T-I 同构：`b`=D 命中且 F 未中（损失），`c`=D 未中且 F 命中
  （新增），`net=c−b`，`n_disc=b+c`。
- 强制报告 `b/c/net/n_disc`、双侧精确 McNemar p、配对差 95% CI
  （Newcombe 主法 + Wald 敏感性并列）。**p 与 CI 只作描述，不作
  放行/否决线**；本批不设多重校正（只有一个主比较 F−D）。
- 同时给题数与百分比；分母固定 298；失败/零调用/超时/空响应/解析失败
  一律按未命中计入，不剔题。

### 4.2 事件级读数（解释机制，不替代题级）

| 指标 | 定义 |
|---|---|
| `triggered_absent_events` | F 臂首次对账为 `principal_absent` 的 expand action 数（按 action 计，不按轮次重复计） |
| `feedback_rounds_used` | 本批 F 臂 `format_feedback` 行数（含首轮/续轮；按 action 分列） |
| `repaired_events` | 经过 ≥1 轮反馈后最终以非 absent 对账结果提交的事件数 |
| `residual_rejected_events` | 因 2 轮耗尽/0 轮/不可解析/改身份/edits 非法/非 model_declared/预算耗尽而拒的 action 数 |
| `recovery_rate` | `repaired_events / triggered_absent_events`；分母为 0 时写 `0/0, not estimable`，不得写 0% 冒充结论 |
| `absent_events_by_subclass` | 按 disjoint/overlap、rank1/rank2、共同产物 0/1/2 分列（沿用 146 分类口径） |
| `multi_absent_qids` | 有 2–5 条 absent 的题数（历史 33 题），及其反馈争用/残余拒分布 |
| `new_events` / `lost_events` | F 相对 D 的新增/损失事件数（事件级） |

- **F 的实际回收率 unknown**；本批只给点计数与分母，不承诺任何收益。
- 事件级新增/损失与题级 hit 变化必须分表；不得用事件净增替代 hit 净增。

### 4.3 失败 / unknown / 零调用

- 每臂报告：`n_completed`、`n_failed`、`zero_cx`、`usage_missing_calls`、
  失败原因分布；
- `unknown` 对账结果不触发反馈/拒，正常提交并保留 `proof_scope`；
- 残余拒不算 run 失败；它记 `admission_rejected`，题仍在分母；
- 崩溃/resume 导致的 run 失败与残余拒分开报；不得把 run 失败洗成
  「拒」或「未中模型差异」；
- 已登记 NC-9 结构性零调用按未命中计入并单列；其它未登记零调用按
  TI-F1 在 smoke10/full 停。

### 4.4 报告纪律

1. 每张表带 **[298 域]** 标签；v1/v2 分列，禁止混比；
2. 同时给题数与百分比；分母固定 298；
3. 不因结果调整 headline、不因某桶好看改分母、不事后增加指标；
4. 不把「修复/拒/新增事件」写成「提分/能力提升」；
5. 不把 146 条程序级分类写成化学真伪结论；
6. interim 读数不得用于提前停或改 treatment；只有全 298 评分完成后
   才出正式读数（运行硬停除外）。

## 5. 停点与风险

### 5.1 科学停点/复盘触发

- **P1-B 不设「提分线」**，也不设「F 有效/无效」判定线；F−D 的 hit/strict
  差异只作效度修复代价的描述性读数。
- **复盘触发（建议，签字时确认）**：全 298 的 v2 strict 净失
  `Δstrict = strict_F − strict_D ≤ −3` ⇒ 停点复盘。该阈值沿用 P2 §6.1
  既有口径，**只触发人工复盘，不构成 F 失败/否决，也不改变本批读数**；
  若 CC 不启用该触发器，则只如实报告，不设自动停点。
- 触发后：不宣布收益、不进入下一轮、不据此改设计/判据；保留现场，
  报 CC/代决裁定（设计失败 / 局部噪声 / 需另轮预注册）。
- 全 298 与分族（如按 strict/partial/unmatched 或 rank 分层）的读数必须
  同时报告；不得只报好看的分层。

### 5.2 B 残余拒的命中损失（当前 unknown）

- 历史 146 条 `principal_absent` 中，6 个 strict 对照事件 = 5 个 absent
  （**3 rank1 + 2 rank2**）+ 1 个 `principal_stereo_only`（不触发）。
- **§3.3 离线复算尚未做**，因此本草案把「B 残余拒的命中损失」显式登记为
  **unknown**，并给最坏情况口径（签字前若完成复算，回填实数并替换
  unknown）：

| 口径 | 当前状态 | 最坏情况上限（事件/题级） |
|---|---|---|
| 5 个 strict absent 事件被残余拒 | unknown | 5 个事件；其中 rank1 事件 3 个、rank2 事件 2 个 |
| 题级 hit@1 损失 | unknown | ≤3 题（rank1 事件所在题；同题多事件时更少） |
| 题级 hit@3/@5 损失 | unknown | ≤5 个事件所在题（rank1+rank2；同题多事件时更少） |
| 146 条非 strict absent 的 hit 贡献 | unknown | 需冻结 scorer 复算；不得用 5 条 strict 上限代替 |
| 合法正控误伤 | 预期 0 | 由 6 组非 absent 测试与 gate/F 分支保证；本批再核 |

- 离线复算方法（未做，签字前可补）：冻结 T-H r2 导出 + 冻结 scorer，
  只移除 146 条 absent 事件（stereo 不拒），重建已提交事件集，重算
  hit@1/@3/@5、strict/partial/unmatched、6 个 strict 事件去向、合法
  正控误伤；不改封存批根、不回写旧成绩。产物仍归
  `docs/review_evidence/p1b_impact_2026-10-21/`。
- 若签字前仍未做：结果报告必须并列「unknown + 上述最坏情况上限」，
  不得把 unknown 写成 0 损失，也不得把最坏情况写成实测。

### 5.3 崩溃/恢复失败模式（已入册）

- 修订 spec **只在当前进程内存**；崩溃后 resume 从 action 冻结的
  **原始 spec** 重跑。
- 两条路径均 fail-closed：
  - (a) 同 attempt 且响应已落盘 ⇒ 反馈轮身份门核验通过后 R3 重放修订
    （零新增付费调用）；
  - (b) attempt/载荷不符 ⇒ `feedback_round_identity_corrupt` 结构化拒
    ⇒ run 失败、题留分母、不静默提交错误事件。
- 代价：路径 (b) 把「本可残余拒」转成「run 失败」；若 HPC 崩溃率不可
  忽略，F 臂失败题数可能高于 D 臂。失败题按未命中计入，不剔题；报告
  必须把「反馈/恢复失败」与「模型未中」分开。
- 是否在付费批前先做「修订 artifact 持久化」= **CC 拍板项**；本草案
  不将其设为发车硬前置，但列为风险。若 CC 要求，先停，另立设计/预注册，
  不在本批加代码。

### 5.4 其它风险（如实登记）

| # | 风险 | 处置/披露 |
|---|---|---|
| 1 | F 回收率 unknown，可能为 0 | 只报点计数；不承诺收益 |
| 2 | 残余拒直接损失可能命中 | §5.2 unknown + 最坏情况；报告并列 |
| 3 | 33 题多 absent 争用 3 请求额度 | 报争用/耗尽/残余拒分布；不补调用 |
| 4 | 反馈可能诱导改声明/expectation | 身份门强制拒绝并残余拒；不依赖模型服从 |
| 5 | 146/58 化学真伪 unknown | 程序级分类 ≠ 化学正确；不做化学结论 |
| 6 | 本机 RDKit 2026.03.6 vs 批内登记 2026.03.5 | 发车记录实际版本；逐事件版本差未做，列 unknown |
| 7 | env 不在 run identity，可能错标臂 | arm_config 显式记录 + smoke2 核对；两臂只差这一项 |
| 8 | F 臂 submitted 报告新增 `p0b_d6`/`p0b_d6_history` 键 | 仅实验臂形状差；报告消费方须容忍；D 臂不加键 |
| 9 | resume/复用路径、run 级预算耗尽 outcome、非 model_declared 边界等分支测试缺口 | qwen 已列非阻断；本批用真实运行分布核验并披露 |
| 10 | 单批、单模型、采样/时间窗不确定性 | 只作本任务形态描述；不外推稳定排序/通用能力 |

## 6. 运行硬停（TI-F1 继承，工程停点）

以下阈值/处置与 TI-F1 零改动继承；P1-B 使用独立批根/`stop.json`，
但闸门语义相同：

| 阶段/信号 | 阈值 | 处置 |
|---|---|---|
| 预检 | 401/402/403/400、模型 ID 不符、env 缺失、请求参数不兼容 | 停全部；不 build/不 run；报 CC |
| build | 作业非零、无 BUILD-PASS、build-gate 失败 | 停；不 run；查日志 |
| 身份门 | manifest/fingerprint/逐题 run_input sha 任一不同；缺指纹/空 sha | 停；不 prepare/run |
| prepare | 批准包缺件、四文书 SHA 不符、`no_cap_ack!=true` | 停；不改审批/不猜 |
| smoke2 | 无「completed 且真实调用可核」；仍有 pending；模型/身份不符；usage 不可解析；fatal；**arm_config env 值与臂名不符** | 停两臂 |
| smoke10 | 非豁免 `failed>0`、未登记结构性零调用 >0、仍有 pending | 停该臂并停另一臂；不进 full |
| full | 非模型内容运行失败 >15；pending>0；fatal | 停两臂、保全现场、不在无效批上判 |
| P1-B 专项观察 | F 臂 `feedback_round_identity_corrupt`/修订重放失败或恢复失败 >15 题（或 >5%） | 停批报 CC；不自动加持久化/不自动改代码 |
| 任一阶段致命信号 | auth/权限/欠费/配额、模型/身份/完整性/no-cap marker/证据卡版本错误、未登记 CX、连续 2 个不同 qid 的限流/传输故障 | 立即停两臂并保全 |
| 恢复 | 仅 prediction_recovery 白名单、同题同参一次、先保全；二败停 | 不新增重试 |

> 这些是**工程守卫**，不是科学判定线；no-cap 下没有金额停点。
> 科学侧只有 §5.1 的复盘触发（且不构成提分线/否决线）。

## 7. 预算模式：no-cap + usage 照记

- **沿用 CC 2026-10-20/21 的 no-cap 口径**：两臂不设金额帽；
  批根落 `budget_no_cap.json`，`budget_mode="no_monetary_cap_user_decision"`，
  `user_decision_date` 记 CC 决定日期。
- 依据：CC 2026-10-21 P2 决定「不考虑预算，只效果」+ T-I 两臂 no-cap
  先例；P1-B 单独登记、独立批根，不复用 P2/T-I 的批。`no_cap_ack`
  仍须 CC 在签字时确认。
- **no-cap ≠ 无限制**：`max_calls=4470`/臂、RPM 200、TPM 3M、workers 8 /
  max_in_flight 8 照常；调用数由 gate 强制，速率由 gate 节流。
- **usage 照记**：每臂记录 input/output/total tokens、模型调用数、重试数、
  零调用数、`usage_missing_calls`；预检、smoke2/smoke10、full、格式反馈、
  传输重试全部计入 usage 账。
- **金额口径**：有账单/价格快照才写实数；无快照写
  `cost_status=no_snapshot`、`cost_known_cny=null`。不得用 token 数乘
  单价估算，不得编造单价，不得把估算写成账单。
- **风险披露**：两臂无金额帽，实际费用由事后账单回填；单次调用 token
  未显式设上限，账单金额可能显著高于规划带，且可能只能记 unknown。

## 8. 前置条件与拍板项

### 8.1 前置清单

| # | 前置 | 要求 | 当前状态 |
|---|---|---|---|
| P1 | r1fix 一行修复 | 非 dict 参与物 `return None, None` + 回归测试 | **已完成**：17 新测试、432 相关面、disclose 三方零漂移 |
| P2 | §3.3 B 残余拒离线命中损失 | 冻结 scorer 复算；或显式 unknown + 最坏情况 | **未做**；本草案按 unknown + 最坏情况登记（§5.2） |
| P3 | 崩溃失败模式入册 | 内存修订、resume fail-closed、分母后果 | **已入册**（§5.3）；是否做修订 artifact 持久化待 CC |
| P4 | env 值记录条款 | 每臂 `arm_config.json` 显式记录 `P0B_D6_RECONCILIATION_POLICY`；两臂只差这一项 | 条款已写（§2.1/§6）；发车脚本待实现/实核 |
| P5 | 「改 edits」提示面化学规则级评审 | 按仓库三触发点单独产出/送审；不冒充已评 | **未做**；本草案不声称已评 |
| P6 | 预注册签字 | CC/代决填 `approval_status/approved_at/approval_source/四文书 SHA` | **待签**（DRAFT_NOT_SIGNED） |
| P7 | 模型 ID | T-I 有效批选定或 CC 指定；两臂同值；发车前写死 | **TBD** |
| P8 | 任务书/脚本锁/化学评审/四文书 | 四文书齐备且 SHA 相符 | **未齐**；见 §9 |
| P9 | 付费/HPC 发车 | CC/Codex 代决落字；批根独立；旧批零回写 | **未做**；本草案不授权 |
| P10 | QA 样本/全量走查 | 发车前按 §6 做 smoke2/smoke10；F 臂 env/反馈路径实核 | 待执行 |

### 8.2 拍板项（CC/代决）

| 代号 | 问题 | 候选/建议 | 状态 |
|---|---|---|---|
| D1 | 是否启用 §5.1 strict 净失 ≤−3 复盘触发 | 建议沿用 P2 口径（只触发复盘，不作提分线） | 待签 |
| D2 | 是否要求付费批前做修订 artifact 持久化 | 默认不做（按 fail-closed 运行）；如要求则先停另立设计 | 待 CC |
| D3 | `model_id` | T-I 选定或 CC 指定；两臂同值 | 待定 |
| D4 | 是否保留 gate 对照臂 | 本预注册不发车；如需要另立 | 待 CC |
| D5 | no-cap 知悉 | `no_cap_ack=true` 才发车 | 待 CC |
| D6 | 化学规则级评审是否作为发车硬前置 | 建议是（涉及模型行为的新提示面） | 待 CC |

### 8.3 不与 T-I/P2 混批

- P1-B 使用独立 `preregistration_id`、独立批根/运行根、独立
  `batch_tag=p1b-298-<YYYYMMDD>`；不共享 T-I/P2 的 run/case/批根。
- P1-B 的两臂都必须是**新批**；不得把 T-I/P2 的任一臂结果当作 P1-B
  的 D 臂或 F 臂，也不得用跨批差值替代同批配对。
- P1-B 代码树含 P1-B patch，与 T-I/P2 非同树；P1-B 读数不与 T-I/P2
  数字混比，也不回写 T-I/P2 成绩。
- 若 T-I/P2 正在运行，P1-B 可并行但必须独立批根/独立 gate/独立
  `stop.json`；资源挤兑时按 TI-F1 停/错峰，不互相污染。
- P2 的 v2 证据卡开关在 P1-B 两臂均关闭；P1-B 不是 P2 的第三个臂。

## 9. 审批字段与四文书

### 9.1 本文件签字位（CC/代决逐项填写；填完才可发车）

```yaml
preregistration_id: prereg-p1b-298-2026-10-21
approval_status: DRAFT_NOT_SIGNED          # 签字后改为：preregistration_confirmed
approved_at: TBD                            # CC/代决填 ISO8601 签字时间
approval_source: TBD                        # 签字人/渠道（如「CC 2026-10-21 会话确认」）
approval_source_kind: TBD                   # cc_personal | codex_delegated_cc | qwen_delegated_codex
preregistration_text_sha256: TBD            # 签字后回填本文件 SHA256
task_doc_sha256: TBD                        # 任务书 SHA256
chem_review_doc_sha256: TBD                 # 「改 edits」提示面化学规则级评审 SHA256
script_lock_sha256: TBD                     # P1-B patch/操作脚本锁 SHA256
impl_patch_sha256: 0ae6535733cf97cbb4439b12e27528fcc7777a770aded2aee8ed8c68a18f491f
baseline_head: 11aeeafded1b41185f24de49767933709aad49db
model_id: TBD                               # T-I 选定或 CC 指定；两臂同值
batch_tag: p1b-298-<YYYYMMDD>               # 发车日实定
arms: disclose / feedback
budget_mode: no_monetary_cap_user_decision  # 沿用 CC 2026-10-20/21 口径
user_decision_date: 2026-10-21
cost_cap_cny: null
no_cap_ack: false                           # CC 阅 §7 风险段后改 true
decision_caliber: 298配对；单变量env；D=disclose/F=feedback；不设提分线；strict净失仅复盘触发；反馈复用2轮
```

### 9.2 `preregistration_approval.json` 模板（签字后落批根 record）

```json
{
  "approval_status": "preregistration_confirmed",
  "approved_at": "<CC/代决签字 ISO8601>",
  "preregistration_doc_status": "preregistration_confirmed",
  "preregistration_id": "prereg-p1b-298-2026-10-21",
  "preregistration_docs": {
    "prereg": {
      "path": "docs/T_P1B_PREREG_FEEDBACK_2026-10-21.md",
      "sha256": "<签字后本文件 SHA256>"
    },
    "task": {
      "path": "docs/TASK_P1B_FEEDBACK_LAUNCH_<YYYYMMDD>.md",
      "sha256": "<任务书 SHA256>"
    },
    "chem_review": {
      "path": "docs/P1B_FEEDBACK_PROMPT_CHEM_REVIEW_<YYYYMMDD>.md",
      "sha256": "<化学规则级评审 SHA256>"
    },
    "script_lock": {
      "path": "docs/P1B_SCRIPT_LOCK_<YYYYMMDD>.json",
      "sha256": "<P1-B patch/操作脚本锁 SHA256>"
    }
  },
  "impl_patch_sha256": "0ae6535733cf97cbb4439b12e27528fcc7777a770aded2aee8ed8c68a18f491f",
  "baseline_head": "11aeeafded1b41185f24de49767933709aad49db",
  "model_id": "<T-I 选定或 CC 指定>",
  "batch_tag": "p1b-298-<YYYYMMDD>",
  "arms": ["disclose", "feedback"],
  "budget_mode": "no_monetary_cap_user_decision",
  "user_decision_date": "2026-10-21",
  "cost_cap_cny": null,
  "no_cap_ack": true,
  "user_authorization": "<CC 预注册定稿 + 付费/HPC 授权文字>",
  "decision_caliber": "298配对；单变量env；D=disclose/F=feedback；不设提分线；strict净失仅复盘触发；反馈复用2轮"
}
```

### 9.3 四文书

| key | 文档 | 签字前状态 |
|---|---|---|
| `prereg` | 本文件 | 草案（DRAFT_NOT_SIGNED） |
| `task` | `docs/TASK_P1B_FEEDBACK_LAUNCH_<YYYYMMDD>.md` | **未生成**；需写自包含发车任务书（含 env 记录条款、TI-F1 停点、批根/回滚） |
| `chem_review` | `docs/P1B_FEEDBACK_PROMPT_CHEM_REVIEW_<YYYYMMDD>.md` | **未取得**；mimo 三触发点场景 1/2 的规则级评审，不冒充已评 |
| `script_lock` | `docs/P1B_SCRIPT_LOCK_<YYYYMMDD>.json` | **未生成**；逐文件 SHA（含 `impl.patch`、操作脚本、配置模板） |

> 四文书快照的文件名 basename 必须与 `preregistration_docs.<key>.path`
> 一致；`prepare` 与首付费 `run` 共用同一验证。`impl_patch_sha256` 与
> `script_lock` 分开登记，避免 patch 更新时四文书键歧义。

## 10. 红线与变更控制

1. 预注册先于付费；无签字不发车、不预检付费调用。
2. 判分/评测零 LLM；模型只出 proposals，不碰判分。
3. 金标隔离：题卷/参考图/逐题 case 只留 HPC 批根；本地只拉指标与身份件。
4. 一批跑完、禁止修一点跑一点；批中零代码/配置/prompt 改动。
5. 封存旧批只读；P1-B 两臂全部新批根；旧批零回写。
6. 不 push；push 时机归 CC。
7. 题域标签处处带；298 与 dev 双向不外推。
8. 单变量=env；任何超出 §2 的差异=停报 CC，不临场加变量。
9. 失败/零调用不剔题；不换题、不补跑换题、不按 flake 静默放行。
10. 不把效度修复写成提分；不把 unknown 写成 0 损失；不把 gate 臂
    当作已发车对照。
11. 签字后任何 policy/env、模型、题卷、池/检索/排序、判据、分母、
    反馈轮数、四文书 SHA 的变化，均视为新预注册或需 CC 书面偏离批准；
    不得在跑中改，也不得在结果出来后换口径。

## 11. 结果报告模板（签字后按此出数）

1. **臂身份与 usage**：model_id、代码 commit+patch SHA、题卷 SHA、
   pool/retrieval/rank 版本、env 两值、tokens/调用/重试/零调用/
   `usage_missing_calls`、金额（实数或 unknown）。
2. **题级配对表 [298 域]**：D/F 各自 hit@1/@3/@5、strict(U)、
   partial/unmatched；`b/c/net/n_disc`、McNemar p、Newcombe/Wald CI。
3. **事件级修复表**：triggered/repaired/residual/feedback rounds/
   recovery_rate（含 0/0 处理）、new/lost events、33 题多 absent 分布。
4. **失败/unknown 表**：n_completed/n_failed/zero_cx/未知原因；run 失败
   与残余拒分列。
5. **B 残余拒命中损失**：§3.3 实数，或 unknown + §5.2 最坏情况上限。
6. **6 个 strict 事件去向**：5 absent（3 rank1+2 rank2）+1 stereo；
   修复/拒/保留。
7. **化学与证明边界**：146/58 化学真伪 unknown；程序级修复 ≠ 化学正确；
   RDKit 版本差。
8. **限制**：单批/单模型/时间窗；F 回收率未知；no-cap 费用 unknown；
   不与 T-I/P2 混比。

## 12. 当前结论与仍缺

- **r1fix 已完成**：qwen 复审唯一必改项（`return None, None`）已修，
  17 新测试、432 相关面、disclose 三方零漂移均复跑通过；具备进入
  预注册**起草/确认**的程序条件。
- **仍缺**：§3.3 B 残余拒离线命中损失（本草案按 unknown + 最坏情况
  登记）、化学规则级评审、任务书、脚本锁、模型 ID、四文书 SHA、
  CC/代决签字、付费/HPC 发车授权。
- **本草案不授权付费批、不部署、不调真实模型、不跑 HPC、不读金标/
  题面/env/key、不 push。**