# HIT60 S1 收官报告 — 变更集四臂判定与止损结论

> 状态：**complete**（收官方式 = **止损结论**，非过门）。
> 任务书：[TASK_V43_HIT60_S1_CHANGESET.md](TASK_V43_HIT60_S1_CHANGESET.md)（T1，§7 交付件即本文件+通俗版）。
> 判定规则唯一依据：[reports/phase_s1_hit60/PREREGISTRATION.md](../reports/phase_s1_hit60/PREREGISTRATION.md)
> （F0b，2026-09-29 落盘，先于任何付费调用）；配置差异唯一依据：
> [ARM_CONFIG_DIFFS.md](../reports/phase_s1_hit60/ARM_CONFIG_DIFFS.md)；过程账本：
> [RUN_JOURNAL.md](../reports/phase_s1_hit60/RUN_JOURNAL.md)。
> 本报告为 git 跟踪文件：**零 SMILES、零 dev 逐题编号**；逐题细节只引用 gitignored 产物路径，
> 池级统计、臂级对比与费用账可全文写。结论三态 `dev_candidate | rejected | inconclusive`，
> 不写 `adopted`（发布默认变更另走发布审查）。通俗版：
> [HIT60_S1_CHANGESET_REPORT_PLAIN.md](HIT60_S1_CHANGESET_REPORT_PLAIN.md)。

## 0. 一行结论

**C0 闭卷基线 @1≈15–16%；E2（T=0）/E1（排序协议 v2）rejected；E3（窗口 16）
经 2026-09-30 [teacher 批复](TEACHER_REPLY_V43_HIT60_S0S1_VERDICT_2026-09-30.md) §五.3
改写为「无效应、不可判」**；
E4 not_attempted（五模型裸测未交付）；累计净赢 ≈ +2.7pp < +8pp → 止损门坐实，
S1 冲刺停止，不带弱证据碰 298。** 两个改变后续判断的新事实：dev 经全证据面
（22 项资产）审计确认为**配对级真闭卷**（配对泄漏 0 题）；且**归因反转**——
约三分之二题目的金标已在运行时候选证据池里，瓶颈是"排序/选择把金标丢了"而非
"检索不到"。费用记账 ¥21.18/¥50 未触顶。

## 1. 各臂判定总表

| 臂 | 批次（身份） | cn@1 | cn@3 | cn@5 | 空答 | spurious | 费用（快照价） | verdict |
|---|---|---|---|---|---|---|---|---|
| C0-a（基线） | `s1_dev_C0_20260929T182619Z`（a20ba9b9） | 8 | 16 | 19 | 1 | 36 | ¥2.5069 | 基线 |
| C0-b（基线二次采样） | `s1_dev_C0_20260929T190054Z`（a20ba9b9） | 9 | 16 | 20 | 0 | 36 | ¥2.3159 | 基线（方差采样） |
| E2-a（temperature=0.0） | `s1_dev_E2_20260929T192739Z`（1c0e9a73） | 8 | 18 | 20 | 1 | 35 | ¥2.7197 | **rejected** |
| E2-b（temperature=0.0） | `s1_dev_E2_20260929T201603Z`（1c0e9a73） | 8 | 16 | 19 | 1 | 36 | ¥2.1686 | **rejected** |
| E3（窗口 8→16） | `s1_dev_E3_20260929T204506Z`（f77b2991） | 9 | 15 | 16 | 0 | 40 | ¥2.2325 | **无效应、不可判**（teacher 2026-09-30 改写；原 rejected） |
| E1（rank_candidate_presentation v2） | `s1_dev_E1_20260930T023702Z`（f6a6e18b） | 10 | 16 | 19 | 1 | 36 | ¥2.2841 | **rejected**（用户 2026-09-30 批准补跑） |
| E4（模型臂） | —（未出臂） | — | — | — | — | — | ¥0 | **not_attempted** |

分母恒 56；口径 = 整串 `cn_identity`（IDENTITY_VERSION=cn-v1，与判分同源）、
exam_v2 同源评分器（s1-dev-scorer-1，合成夹具 PASS 后上岗）、空答留分母。
五个判定批次全部 56/56 合法终态、pairing gate 全过、0 缺 usage / 0 孤儿 / 0 429。
C0 首批（300s 超时墙，58/90 缺 usage）作废不进判定，处置见 §10 与
ARM_CONFIG_DIFFS §4.2。

## 2. F0｜dev 集冻结与题源红灯

### 2.1 D2 preflight 漏斗（CPU-only、零 LLM、口径预注册、全量扫描无抽样）

| 源 | 漏斗 | 可用 |
|---|---|---|
| B1（BIOSYSMOdb 121 拆步冻结包，SHA `6858c165…`） | 533 步 → 可构题 524（构题门排除 9）→ 去重 428 → 重叠排除 323（旧298 120 + 训练 203）→ 泄漏排除 49 | **56（全部进 dev，预留 0）** |
| RHEA broad-87 | 85 题构题全过 → 重叠排除 20（旧298 3 + 训练 17）→ 剩余 65 题全部泄漏 | **0** |
| BRENDA extra-213 | 维持默认排除（accession 拆分/表示分歧 bug，613 处 canonical 分歧，从未实际运行） | 0 |

- **RHEA 是结构性泄漏**：85 题中 84 题配对级泄漏（83 题泄漏源即 rhea 本身）——
  broad-87 抽自 rhea142，语料 rhea 记录直接含"题面→产物"对，对任何以 v1 语料为
  检索底的系统都不构成盲测，不是口径可以修的。
- **盲测预留池 = 0**：B1 可用 56 全部进 dev；RHEA 可用 0。稳健性检验（补充分析，
  非冻结口径）：训练判据放宽为仅反应层也只有 77 可用（dev 75 + 预留 2）——约束瓶颈
  是旧298 重叠 + v1 语料配对泄漏，非判据选择。**B1+RHEA 在预注册卫生标准下无力
  供养盲测预留池**，盲卷阶段需新题源或显式放宽口径决策（审计留痕可重算）。
- 漏斗明细与逐题留痕：[PREFLIGHT_REPORT.md](../reports/phase_s1_hit60/PREFLIGHT_REPORT.md)、
  `split_manifest.json`（状态 FROZEN）。

### 2.2 冻结与金标复核

- dev = 56 题（36 case / 56 反应；52 单金标 + 4 双金标，同步产物清单语义），
  划分种子 20260929；冻结 SHA：`dev_questions.jsonl` = `8869cd05…`、
  `dev_gold.jsonl` = `d285dc0b…`（敏感，仅 SHA 引用）、`split_manifest.json` = `cbc413ed…`。
- 金标双人确认（I3）：构建代理 + 复核代理**独立重推 56/56 一致**，无金标分歧，
  冻结件不动（gitignored `dev_gold/VERIFY_DEV_GOLD.md`）。运行侧输入仅
  `question_id / root_smiles / root_smiles_sha256` 三字段，金标只在独立评分进程读取。

### 2.3 dev 结构特性（跑分前预登记的解读口径，防看分后自由发挥）

- **退化题 2 题**（金标 = 题面，原样复读即命中）：主指标照算，另报剔除敏感性读出。
- **同题面异金标 4 对**：整串集合判分下每对至多 1 题 top-1 命中，**cn@1 存在
  54/56 结构性天花板**；两臂同天花板，配对对比不受影响。
- **新元素题 3 题**（金标含题面没有的 N/P/S，来自被过滤的 CoA/O2 共底物）：
  属难度属性，spurious 分桶单列。

### 2.4 题源红灯的后续影响

盲测预留池为空 → S2 盲测卷的题源需上游拍板（teacher 待裁决四项之①，选项：
biosysmodb150 线 / Eawag 酶级基准方向 / 修复 BRENDA / 显式放宽某一审计口径）。

## 3. 预注册与判定规则（引用，不重抄）

全部判定依据 [PREREGISTRATION.md](../reports/phase_s1_hit60/PREREGISTRATION.md)（§0 红线
I1–I4、§1 总则、§2 各臂六项预注册、§3 配对结构、§4 采用判据与止损门、§7 结构特性
解读口径），要点：

- **单臂采用门**：dev cn@1 净赢 ≥3 题（≈5.4pp）且 cn@5 不降、空答率不升、spurious
  不升；E2 按翻转口径替代均值门槛（F_E2/F_C0 符号检验双侧 p<0.05 或
  F_E2 ≤ max(0, F_C0−3)，且均值不劣于 C0−2 题）。
- **累计止损门**：各已判臂净赢（pp，对其登记对照）累计 <+8pp → 停止冲刺、出止损
  结论、不带弱证据碰 298；判定点在每个臂判定后立即评估。
- **配对结构**：C0 → E2 →（E3、E1）。E2 rejected → 接力不触发，E3/E1 直接对 C0
  配对（登记先于看分，看分后不得换对照）。
- **小样本纪律**：56 题逐题四格 + 不确定性一起报，**单次抽样不证因果**；关键臂
  两次采样（同身份、新批次根）。
- 各臂实际 diff（配置、prompt 版本、代码 commit）发车前补进
  [ARM_CONFIG_DIFFS.md](../reports/phase_s1_hit60/ARM_CONFIG_DIFFS.md) §4.1–§4.4，
  与预注册逐字段对得上才准发车；跑分侧身份核对（batch_identity.json 机读 +
  run_identity policy 块逐臂核对）确认差异字段恰为登记字段，无越界。

## 4. 四臂结果

### 4.1 C0 基线（两采样）

- C0-a：@1=8（14.29%）/@3=16（28.57%）/@5=19（33.93%）；空答 1；spurious 36；¥2.5069。
- C0-b：@1=9（16.07%）/@3=16/@5=20（35.71%）；空答 0；spurious 36；¥2.3159。
- 均值：@1 8.5（≈15.2%）/@3 16.0/@5 19.5/空答 0.5/spurious 36。
- **F_C0 = 7**（同臂两次采样之间 cn@1 翻转 7 题；宽口径"翻转或首位产物变化"30 题，
  仅诊断）→ 提供方缺省温度（T=1.0）下非确定，触发 E2 两次采样分支。
- **闭卷基线 ≈15%**：dev 配对级零泄漏（§6）下的端到端读数；对照旧 298 开卷
  45.6%（见 §6.3）。

### 4.2 E2 温度臂（temperature=0.0，先行臂）— rejected

- **单一机制差异**：三协议与 LLM client 显式 `temperature=0.0`（进 policy 与 run/batch
  identity）；基线臂请求体不含该键。温度通道实证：E2 两批 **97/97** 条 prediction_call
  留痕 `temperature: 0.0`（API 实收无 400；烟测另证 1/1）；C0/E3 批该键 0 条。
- **判定（PREREG §2.1 原文执行）**：F_E2 = 6（E2-a vs E2-b cn@1 翻转 6 题），
  F_C0 = 7。判据 1 符号检验：F_E2+F_C0 = 13 ≥ 3 适用，翻转 2×2 = both 3 /
  C0-only 4 / E2-only 3 / neither 46，不一致对 n=7，双侧 **p=1.0000 ≫ 0.05**
  不显著；判据 2：F_E2=6 > max(0, 7−3)=4 不成立。均值条件满足（8.0 ≥ 8.5−2=6.5）
  但前两判据任一成立才可能 win。
- 次级回退全守：@5 均值 19.5 = 19.5；空答均值 1.0 vs 0.5；spurious 35.5 vs 36。
- → **E2 = rejected**：均值未动 + 方差未显著减少。**披露：提供方在 T=0.0 下仍非确定
  （残余翻转 6/56）**，为提供方行为，如实登记；单次抽样不证因果。
- 接力决定（先于任何 E3 分数，ARM_CONFIG_DIFFS §4.3）：E2 非 dev_candidate →
  E3 对照 = C0。

### 4.3 E3 窗口臂（max_candidates_for_ranking 8→16，对照 = C0）— 无效应、不可判（teacher 2026-09-30 改写；原 rejected）

- **单一机制差异**：rank 任务候选上限 8→16（配置化、版本化；**报告宽度 5 不动**，
  产品决策）。run_identity policy 块：E3 (temp null, 窗 16) vs C0 (temp null, 窗 8)。
- 净赢 @1：vs C0-a **+1**、vs C0-b **0** → 两样本均 ≥3 的门远未达到。
- **回退上限双破**：@5 净降 **−3 / −4**（底线净降 0；≤2 题才可带逐题归因进降级，
  这里明确拒绝）；**spurious 40 > 36**（击穿）。空答 0 ✓。
- 费用 ¥2.2325 ≤ min(2.5×对照, 帽 ¥6) ✓；候选翻倍未致超时率上升（0 超时）。
- → **E3 = 无效应、不可判**（2026-09-30 teacher 批复 §五.3 定性改写，原判定
  rejected）：窗口 8→16 在 dev 上无 @1 增益；原"排序质量回退（放开更多不可
  区分候选稀释位次）"的机制解释被下方载荷层证据推翻，回退实为采样噪声，
  故按"无效应、不可判"记录。
- **归因修正（2026-09-30 coverage_stat M2，teacher 批复采纳）**：E3 三个 rank 任务
  实际只带 2/2/4 张卡——合格 recorded 池 ≤4，窗口 8 与 16 截断的是同一个
  未满的池，**窗口臂在 dev 载荷层 no-op**（C0-a/E3 候选产物逐一相同）；
  上述 @5 回退与 spurious 40 的机制解释相应修正为 **novel 采样噪声**，
  非"多卡稀释"。若未来放宽入围（深位召回），须同步上守恒/杂原子确定性
  过滤器（假想第 9–16 卡 79% 违规、analog 迁移卡 16/16 全违规）。

### 4.4 E1 协议臂（rank_candidate_presentation v1→v2，对照 = C0 两采样）— rejected

- **单一机制差异**：`rank_candidates` 协议 v2——候选分层四层卡（engine/source/
  condition/verification）+ candidate_set 集级事实 + 密度预算（1,600 字符/卡、
  300 字符/SMILES）；提示词换 ranker_v2.md；解析契约 v2（select 须任务书全部候选
  完整 order，hold 须结构化 {kind,note}）。v1 路径零改动（黄金对照 payload SHA
  `f7742643…` 打补丁前后逐字节一致）；prompt_versions 四键恒在身份。
  设计 = `e1_design/E1_DESIGN.md`（设计代理只设计不实施）+ 两 diff，实施与发车登记
  见 ARM_CONFIG_DIFFS §4.4、RUN_JOURNAL §10。
- 净赢 @1：vs C0-a **+2**（10−8）、vs C0-b **+1**（10−9）→ 两样本均 ≥3 的门未达，
  主终点失败。
- 次级全守：@5 净 0（vs a）/ −1（vs b，≤2 归因带内）；空答 1 ≤ 1 ✓；spurious
  36 = 36 ✓；费用 ¥2.2841 ≤ ¥6 ✓；56/56 合法终态、usage 100%、0 孤儿。
- **机制诊断（无承载面）**：全批 48 调用 = 42 novel + 3 analogy + **仅 3 rank**，
  三臂路由分布相同；这 3 个 rank 题在 E1/C0-a/C0-b **全部 miss** → **净赢 +2/+1
  全部来自 novel 模式的采样噪声**（F_C0=7 同量级，翻转 vs a 10 题 / vs b 5 题）。
  解析面完全干净：48/48 一次解析成功、0 hold、3 个 rank 全 select 且完整 order
  （长度 2/4/2）——完整 order + hold 枚举的解析严格度未推高空答（E1 最大风险
  R1 未发生）。密度：rank 候选块 median 1,278 / max 2,912 字符，截断未触发正常路径。
- **结构性落差（登记）**：E1 设计依据 = S0 池级结论（L1-rank 23 + L2-rank 13）；
  56 题 dev 切片 rank 路由仅 3 题、rank 机制可及的金标@2-5 题 = 0——池级机制在
  dev 上**无统计可判的承载面**。E1 在 dev 上"测不出增益"是承载面问题，不是机制
  被证伪（298 全卷承载面更大；I1 纪律下 dev 结论不外推）。
- → **E1 = rejected**（次级全守、主增益不足；无红线击穿）。

### 4.5 E4 模型臂 — not_attempted

按 PREREG §2.4/§6 捆绑说明：E4 出臂依赖 D3 五模型裸测（陈浩然线 G5-R2），该依赖
**未交付**（现仅三题 G5 工程 smoke 且 FAIL）→ 本轮不出臂，按 D3 继续等。处置：
已判臂不重跑；D3 交付后只补"新模型 ×（旧协议/新协议）"缺角臂；**止损已触发后，
缺角臂仅作机制登记，不再承载冲刺目标**。是否催测为 teacher 待裁决四项之④。
[REPLY_TO_TEACHER_HUANG_HIT60_S1_2026-09-30.md](REPLY_TO_TEACHER_HUANG_HIT60_S1_2026-09-30.md) §6 D3。

### 4.6 配对四格表（臂 × 题数；逐题配对明细见 gitignored `per_question.tsv`）

cn@1 四格（vs 对照；both = 两臂都中 / X-only = 仅实验臂中 / C-only = 仅对照中 / neither）：

| 配对 | both | X-only | C-only | neither | 净赢 |
|---|---|---|---|---|---|
| C0-a vs C0-b | 5 | 3 | 4 | 44 | F_C0 = 7（翻转） |
| E2-a vs E2-b | 5 | 3 | 3 | 45 | F_E2 = 6（翻转） |
| E3 vs C0-a | 3 | 6 | 5 | 42 | +1 |
| E3 vs C0-b | 6 | 3 | 3 | 44 | 0 |
| E1 vs C0-a | 4 | 6 | 4 | 42 | +2 |
| E1 vs C0-b | 7 | 3 | 2 | 44 | +1 |

cn@5 关键行：E3 vs C0-a both 14 / E3-only 2 / C-only 5 / neither 35（净 −3）；
E3 vs C0-b both 15 / E3-only 1 / C-only 5 / neither 35（净 −4）。
跨臂翻转联合 2×2（E2 判定输入）：both 3 / C0-only 4 / E2-only 3 / neither 46。

### 4.7 身份与配置指纹（判定批次）

- C0/E2/E3：代码聚合 SHA `fff3b417…4972c`（50 文件，本地=远端逐字节一致）；
  prompts rank `864a5f30…` / analogy `6d228935…` / novel `1aa41393…`；资产清单
  `ac9b97b8…`（22 文件）；配置 C0 `313af38b…` / E2 `8ba59742…` / E3 `6770f3c3…`。
- E1：代码聚合 SHA `3fe38c86…39c3c`；prompts 四键（rank `864a5f30…` /
  **rank_v2 `83056983…`** / analogy `6d228935…` / novel `1aa41393…`）；配置
  `975c6e3a…f7d06`；批次身份 f6a6e18b，烟测身份 b00d1ce1。资产清单未动。
- 模型 `ZHIPU/GLM-5.3-Flash`（远端 .env 实核，非 kimi-k3 系）；价格快照
  2026-09-29（当日重取官方页核对一致）：input ¥0.8/M、output ¥2.8/M、
  cache read ¥0.23/M。
- 配置差异机读核对：E2 vs C0 = {arm, batch_root, batch_cost_cap_cny, temperature}；
  E3 vs C0 = {arm, batch_root, batch_cost_cap_cny, max_candidates_for_ranking}；
  E1 vs C0 = {arm, batch_root, batch_cost_cap_cny=6.0, rank_candidate_presentation}——
  均为登记字段，无越界；跨身份 resume 由既有 IdentityMismatch 链路拒绝。

## 5. 止损门判定（PREREGISTRATION §4）

各已判臂对其登记对照的净赢：

| 臂 | 净赢（题） | 净赢（pp） |
|---|---|---|
| E2（均值 8.0 vs C0 8.5） | −0.5 | −0.89 |
| E3（两样本均值） | +0.5 | +0.89 |
| E1（两样本均值） | +1.5 | +2.68 |
| **累计** | | **≈ +2.7 < +8** |

**止损门触发并坐实**：止损门在 E3 判定后首次触发；E1 为用户 2026-09-30 明示
批准的补跑（判定框架不变），判定后在 E1 判定点重估，结论不变。**S1 冲刺停止，
出止损结论——不带弱证据去碰 298；重估目标或转 S3 由用户/teacher 决策。**

## 6. 闭卷真相：全证据面血统与泄漏审计

> 触发：用户指正 D2 preflight 泄漏审计只扫了 corpus_v1。补做全证据面审计
> （方法沿用 D2 双口径 = 精确串 + cn_identity，配对级判据 = 同记录题面在给体侧
> 且金标在产物侧、正反双向；零 LLM 调用、资产只读）。
> gitignored 细节：`reports/phase_s1_hit60/dev_gold/FULL_SURFACE_LEAK_AUDIT.md`
> 与同目录 `full_surface_asset_audit.json`；血统对账含勘误节：
> [CORPUS_LINEAGE_ECREACT_CHECK.md](CORPUS_LINEAGE_ECREACT_CHECK.md)。

### 6.1 全证据面清点与血统勘误（22 项资产，2026-09-30 实测）

| 资产 | 规模 | 血统 |
|---|---|---|
| corpus_v1.jsonl | 43,177 行 | rhea 37,100（release 141）+ envipath 6,077（EAWAG 系五包） |
| donor_index.jsonl | 95,782 行（16,875 distinct donor） | rhea 90,026 + envipath 5,756 |
| library_full.jsonl | 4,454 行 / 772 btid | **纯 EAWAG 系**（勘误：旧记录猜测 BRENDA/union 血统，实测否定；EnzymeCAGE 只是服务器目录名） |
| uspto_templates.json / uspto_relaxed_index_v1 | 188,725 模板（n_train=409,035） | USPTO 专利反应 |
| corpus_templates v1/v2 | 各 17,183 行 | corpus 映射模板 |
| eawag donor_product / rules | 1,066 / 49 行 | EAWAG-BBD |
| envipath 模板 | 573 行 | enviPath 规则 |
| rankers ×3 / calibrators ×2 | — | 模型转储/数值，无分子内容 |

- **全部 22 项资产串扫 ECREACT/EVODEX/BRENDA/enzymemap/metanetx/pathbank 血统
  标记 0 命中**；"语料缺 ECREACT"在血统层面成立（内容级与 ECREACT rhea 6,715
  子集可能同源重合，未量化，如实登记）。
- 顺带对账：corpus_v1 43,177 行中 303 个 envipath 重复 record_id（多 531 行），
  引擎按 record_id 去重装载 = 42,646，与 ASSET_WIRING_REPORT 口径吻合，无静默丢数。

### 6.2 配对级泄漏 = 0（真闭卷），分子级可见性如实登记

- **全部资产配对级泄漏 0 题**（library_full 0、eawag 两件 0、corpus_templates
  v1/v2 0、donor_index 结构性无产物侧、USPTO/envipath 模板为 SMARTS 无成对分子；
  正反双向皆 0）。**dev 56 的配对级"闭卷"属性在全证据面下成立并加固。**
- 分子级可见性（非泄漏，登记）：金标分子作为**其它给体**的产物出现在
  library_full 15 题、eawag donor_product 12 题、corpus_templates 18 题；作为
  **给体**出现在 donor_index 32 题、library_full 22 题；题面底物作为给体可见
  library_full 11 题、donor_index 16 题。属化学宇宙常态（常见代谢物），不构成泄漏，
  但对外表述须知悉。

### 6.3 开卷/闭卷落差：15% vs 45.6%，影响 60% 目标口径

- **C0 闭卷 @1 ≈ 15–16%（8–9/56）**是"配对级闭卷新题"的端到端干净度量。
- 旧 298 的 **45.6%（136/298，Phase D 复测）本质是开卷/已见成绩**：298 在
  Phase A–D 开发迭代中反复见过，且**从未做过 D2 式配对级泄漏审计**（该审计方法
  本轮才建立并首次应用于 dev）——部分分数可能是"答案在系统里"的开卷增益。
- 两数对比给出 ~30pp 的开卷/闭卷落差。**这直接影响 60% 盲测目标的可行性判断**：
  60% 是按开卷 45.6% 的差距设定的；盲测真实基线在 15% 一档，目标口径需 teacher
  裁决（待裁决四项之②：闭卷真相下 60% 如何设定、S3 地位是否调整）。

## 7. 归因反转：答案在手边选不出

### 7.1 运行时证据抽查（远端五个完整批次，每批 7,553–12,310 张证据卡）

判据：金标 cn 身份或精确串与证据卡**整串**产物候选相等（与评分器整串口径一致）。

| 臂 | 金标=完整产物候选（题/56） | 其中 USPTO 模板 | 其中 corpus 类比检索 | 其中 enviPath 规则 |
|---|---|---|---|---|
| C0-a | 36 | 22 | 10 | 9 |
| C0-b | 37 | 22 | 11 | 9 |
| E2-a | 36 | 22 | 10 | 9 |
| E2-b | 36 | 22 | 10 | 9 |
| E3 | 37 | 22 | 11 | 9 |

（一题可多来源；各臂间 1 题差异来自检索采样/预算波动。）

与官方评分交叉（C0-b 为例，@1=9、@5=20）：

| 分解 | 题数 |
|---|---|
| 金标在产物候选 & 最终 top-5 命中 | 15 |
| **金标在产物候选 & top-5 未命中（候选含金被丢弃）** | **22** |
| 金标不在候选 & top-5 命中（LLM novel 路径） | 5 |
| 金标不在候选 & 未命中 | 14 |

**深位案例（抽验，细节见 gitignored 审计）**：一题金标以整串相等出现在 USPTO
模板证据卡上，**引擎检索位次 rank 75**——远在窗口 8/16 与报告宽度 5 之外；
该题最终答卷为混合产物，判 spurious。证据链真实（非匹配伪影）。

### 7.2 解读与主杠杆

- **15% 的归因从"闭卷瞎猜/检索不到"反转为"生成得到、排序选不中"**：约三分之二
  题目（36–37/56）的金标能被规则泛化/类比检索**合法推演**出来并进入候选集
  （不是答案记录直查），其中仅 15–17 题进 top-5，"池里有、排序/漏斗丢掉"
  原计约 22 题；**[coverage_stat](../reports/phase_s1_hit60/coverage_stat/COVERAGE_STAT.md)
  M1 精算修正为 16 题真丢弃 + 6 题口径型假丢弃**（后者答卷已含金标组分，
  属 §8 判分口径问题），且"金标@2–5"的 11 题 100% 走 novel 路由——
  E1 式证据卡重排在 dev 无承载面，可救的重排对象是 novel 自产 5 候选自排序。
- **主杠杆 = 引擎候选池（含深位）喂进任务 + 排序层**：正对"候选含金被丢弃"
  的承载面。E1 已验证的完整 order 契约工程**可直接复用**（48/48 一次解析成功、
  0 hold、空答未升），工程增量集中在"深位候选的召回与喂入"而非协议本身。
- 对外表述口径：不能说"dev 题的答案在系统知识库里不存在"；应说"答案记录不存在，
  但答案分子可被合法推演到达"。15% 定性不变（仍是配对级闭卷新题的端到端度量）。
- 后续建议（待批未开工）：新增"深位召回 + 排序层"臂（listwise 再排序，
  RankLLM 范式可借鉴），按 I2 预注册发车；详见
  [REPLY_TO_TEACHER_HUANG_HIT60_S1_2026-09-30.md](REPLY_TO_TEACHER_HUANG_HIT60_S1_2026-09-30.md) §11。

## 8. 外部化学评审（mimo）要点与采纳路径

> 评审原文在 gitignored `docs/mimo_e1_chem_review_comment.md`（独立环境化学/
> 微生物代谢评审人，与系统作者无利益关系；其对判定表逐行复算 0 差异，守恒/
> 分子式结论为复算硬事实）。**本节只引池级要点**（占比、题数、结论），
> 不引其 SMILES 与逐题编号。

### 8.1 池级要点

- **spurious 36 题的构成**：约 **19%（7 题）是判分口径假失分**（多组分答案被
  整串比对结构性判负，其中 **6 题化学答案已含全部金标组分**——答得更完整反而
  必错）；约 **8%（3 题）题面/金标本身不可用**（金标含题面不提供的共底物或守恒
  不成立，单步结构性不可答）；**~72% 真化学错误**；另有 2 道退化题单列。边界题
  归类 ±1 使各档移动约 ±2.8pp；第 1、2 类为复算硬事实。
- **novel 失分根因 = 确定性约束被卸掉，不是模型不懂化学**：novel 任务无候选卡，
  守恒/验证字段整体不生效，模型被迫从"我认识的分子"里挑；首位产物反复出现
  通用小分子。最关键的缺失信息是"这一步允许的骨架变化范围"（ΔC 允许集、
  允许增删的杂原子集、可进攻位点清单），可由代码从题面确定性算出。
- **dev 上 rank 可及承载面 = 0**（与 §4.4 机制诊断互证）：rank 建议的正确战场
  在 **298 全卷**（S0 池级 L1-rank 23 + L2-rank 13）。
- E3 窗口解读：多出的卡是"信息但不可读"——缺淘汰信号（底物同源性、守恒、
  条件可实现性等确定性过滤器），放进更多不可区分的东西与实测回退一致。

### 8.2 最值得做的三件事（评审排序：预期提分 ÷ 成本）

1. **主分数改组分级口径**（component_mode 已实现，现仅用于敏感性表；判分侧，
   不改模型）：dev 理论上限 **+6 题（+10.7pp）**；口径变更移动全部历史数字 →
   **必须新臂预注册 + 重刷 C0 基线**。
2. **"金标是否已在 5 候选池"只读覆盖率统计 + novel 链路确定性守恒过滤**：
   覆盖率是决定"投生成 vs 投重排"的关键测量（成本近零）；守恒过滤为确定性代码，
   零 LLM，目标 spurious 26 题真化学错误中约 15–17 题潜在面。
3. **金标守恒体检 + 3 题金标处置**（数据侧）：三条 fail-closed 规则把结构性
   不可答题在跑批前拦下；上限 +3 题（+5.4pp）或分母 56→53。

**采纳纪律（fork 会话既定口径）：全部走新臂预注册，不直接改代码。** 三件事
均未开工，随 §11 建议一起等 teacher 裁决。

**统计核验（2026-09-30 [coverage_stat](../reports/phase_s1_hit60/coverage_stat/COVERAGE_STAT.md)）**：
三件事的关键数已全部实测——①组分级口径复算**六批全部 +6@1/+7@3/+7@5**，
救回题单与评审逐题相同（差异一条叙述修正：这 7 题全走 recorded/rank
确定性路由，评审原文记在 novel 名下）；②覆盖率已测（§7.2 修正后的
16 真丢弃 + 14 池无）；③E3 窗口臂载荷层 no-op（§4.3 归因修正）。

## 9. I1 合规与单次抽样限定

- **I1 信号源隔离**：止损触发后**未带任何变更碰 298**（298 全程只读）、未在
  已见题调参；S1 全部臂设计依据只用 S0 池级结论，无 298 逐题信息进设计。
  含金标产物全部 gitignored，不入 git 跟踪文件。
- **I2 判决先于数据**：判定规则先于任何付费调用；看分后未改规则；E1 为止损后
  用户明示批准的补跑，判定框架不变。
- **单次抽样限定**：C0 双采样（F_C0=7）与 T=0 翻转题（F_E2=6）说明提供方
  非确定性持续存在；56 题小样本，逐题配对 + 不确定性一起报，**不做单次抽样
  因果断言**；每臂两次采样（判定所需）。
- **异常披露**：C0 首批作废（超时墙，§10）；远端全仓回归 505–508 中 1–2 个
  失败均为共享机负载 flake（两轮失败用例不同、全部隔离复绿）或 assets 符号链接
  拓扑断言（改物理拷贝后 10/10 过），本地同代码 508/508 全绿（E1 施工后 541/541）。

## 10. 费用账

| 项 | 金额 |
|---|---|
| 烟测（E2 语义，独立账） | ¥0.0275 |
| C0 首批（作废，300s 超时墙；已知 usage 部分） | ¥0.8620（+输入预留 ¥0.0365） |
| C0-a / C0-b | ¥2.5069 / ¥2.3159 |
| E2-a / E2-b | ¥2.7197 / ¥2.1686 |
| E3 | ¥2.2325 |
| E1 烟测 / E1 批次 | ¥0.0240 / ¥2.2841 |
| **已知合计** | **¥15.18** |
| 作废批超时输出（不可证上界，保守预留） | ≤ ¥6.0 |
| **记账合计 / 总盘** | **¥21.18 / ¥50 ✓ 未触顶** |

- 所有进判定批次 usage 100% 完整；作废批 58/90 超时缺 usage 不进判定
  （PREREG §1.4），处置：`llm_timeout_s` 300→3600（Phase D 同款拆墙值，三臂
  同值，diff 纪律不破坏），修正由超时账目触发、先于任何臂间对比与分数趋势，
  登记 ARM_CONFIG_DIFFS §4.2；旧批根封存（_VOIDED）。
- **作废批真实账单：已核不可回填**（RUN_JOURNAL §11 勘误节，2026-09-30）：
  58 条超时调用用量只存在 DashScope 账单侧，拉取违反零 API 红线；可核实下界
  ¥0.8985，≤¥6 维持授权预留帽占位，记账口径 ¥21.18/¥50 不变；本节不报
  "已核总额"。

## 11. 产物索引与复现

**判定与登记（reports/phase_s1_hit60/）**

- [PREREGISTRATION.md](../reports/phase_s1_hit60/PREREGISTRATION.md) — 判定规则
  预注册（F0b）。
- [ARM_CONFIG_DIFFS.md](../reports/phase_s1_hit60/ARM_CONFIG_DIFFS.md) — 四配置
  预登记差异表（机读块 §5）+ 发车登记 §4.1–§4.4。
- [ARMS_C0_E2_E3_RESULT.md](../reports/phase_s1_hit60/ARMS_C0_E2_E3_RESULT.md) —
  四臂判定汇总（本文主要数字源）。
- [RUN_JOURNAL.md](../reports/phase_s1_hit60/RUN_JOURNAL.md) — 过程账本（批次、
  SHA、费用、E1 节 §10）。
- [PREFLIGHT_REPORT.md](../reports/phase_s1_hit60/PREFLIGHT_REPORT.md)、
  `split_manifest.json`、`BUILD_CONVENTION.md` — D2 题源预检与 dev 冻结。
- `e1_design/`（E1_DESIGN.md + 两 diff）— E1 设计件。

**远端产物（Chenyu `dependingv43_s1/runs/`，路径见 docs/CHENYU_ACCESS.md）**

- 六个批次根（五个判定批 + 一个作废批 `_VOIDED.json`）、各
  `scoring/{score.json, per_question.tsv}`、五份 pair json
  （`s1_dev_{C0,E2}_pair_ab.json`、`s1_pair_{E3,E1}_vs_C0{a,b}.json`）、
  两个烟测目录、`RELEASE_MANIFEST.sha256`（E1 delta 节后自 SHA `fd0a4812…`）。
- 本地拉回副本：`reports/phase_s1_hit60/artifacts_remote/`（不含金标、不含 .env）。

**gitignored（含金标，只在受限目录）**

- `reports/phase_s1_hit60/dev_gold/`：`VERIFY_DEV_GOLD.md`（金标独立复核）、
  `FULL_SURFACE_LEAK_AUDIT.md` + `full_surface_asset_audit.json` + 审计脚本
  （全证据面泄漏审计）。
- `docs/mimo_e1_chem_review_comment.md`（外部化学评审原文）。

**复现要点**

- 评分：`reports/phase_s1_hit60/scripts/s1_dev_score.py`（零 LLM，exam_v2 同源；
  `--pair` 出四格/净赢/翻转数；合成夹具自检 PASS）。
- 发车/归并/终态门禁：`scripts/s1_dev_driver.py`；单路线烟测：
  `scripts/s1_dev_smoke.py`（E2 语义）、`scripts/s1_dev_smoke_e1.py`（E1 语义）。
- 全证据面审计：`reports/phase_s1_hit60/dev_gold/_audit_full_surface_assets.py`
  （只读 assets/，输出 json）；D2 漏斗复跑：远端工作区
  `v43_hit60_d2_question_assembly_20260929/` 的 `scripts/run_all.sh` +
  `05_verify.py --check`（25/25 PASS）。
- 泄漏/血统对账复现命令见 [CORPUS_LINEAGE_ECREACT_CHECK.md](CORPUS_LINEAGE_ECREACT_CHECK.md)
  §五与勘误节。

**上报与裁决**

- teacher 回信（2026-09-30 已发出）：
  [REPLY_TO_TEACHER_HUANG_HIT60_S1_2026-09-30.md](REPLY_TO_TEACHER_HUANG_HIT60_S1_2026-09-30.md)；
  待裁决四项：①盲测题源 ②60% 目标口径 ③任务七死线 ④E4 是否催五模型裸测。

## 12. 差异清单（源文件间数字核对）

判定相关数字（漏斗、四臂分数、四格、翻转数、止损累计、费用、身份 SHA）在
PREREGISTRATION / ARM_CONFIG_DIFFS / ARMS / RUN_JOURNAL / PREFLIGHT /
split_manifest / teacher 回信之间核对一致，未发现影响判定的出入。以下为核对中
发现的口径性差异，逐条列出（不静默取一）：

1. **RHEA 泄漏计数 84 vs 65**：PREFLIGHT §5 报"85 题中 84 题配对级泄漏"
  （对全部构题的命中计数），而漏斗行与 split_manifest `rhea_funnel.leaked=65`
  （重叠排除 20 之后的漏斗口径剔除数）。两数口径不同（前者=全量命中，后者=
  漏斗内实际移出），非矛盾；本文 §2.1 两个数并存并注明口径。结论（可用 0、
  预留 0）不受影响。
2. **dev 链式相邻题计数 18 vs 19**：PREFLIGHT §7 报 18 题（金标 cn 同时是另一
  dev 题的题面）；gitignored `dev_gold/VERIFY_DEV_GOLD.md` 独立复核计数为 19
  （其 §3.3 有登记）。该计数只是 sanity 登记项（盲判分时金标不可见，不影响盲性
  与任何判定）；两数并存，未静默取一。
3. **作废批预留口径 ¥6 vs "真实账单"**：¥6 为超时输出不可证上界的保守占位
  （RUN_JOURNAL §3 记账口径 ¥6.93 = 已知 ¥0.899 + 预留 ¥6.0），非实测值；
  真实账单待回填（§10 已注明"占位待回填"）。凡引用 ¥21.18 处均为记账口径，
  已知口径为 ¥15.18。

---
*S1 收官。四臂判定完毕、止损结论产出；所有后续动作（深位召回+重排臂、组分级
口径、守恒过滤、金标处置、E4 缺角臂）均未开工，等 teacher 裁决与用户拍板。*
