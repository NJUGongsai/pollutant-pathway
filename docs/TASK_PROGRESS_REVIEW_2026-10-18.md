# P0-1 误拒率测量线 · 进程回顾 + 后续 TODO（梳理件，2026-10-18 夜）

> 性质：只读梳理（核验时点 2026-10-18 23:05–23:15 CST；回写实况以该时点磁盘为准）。
> 梳理时点观察：另一窗口当时仍活跃——`docs/HANDOFF_P01_REJUDGE_2026-10-18.md` 23:06:38 仍在编辑、
> `/tmp/p0_1_v3A_b1/`（批 1 逐件 RDKit 复核中间件）23:07–23:08 仍在生成。本件反映 23:12 前已落盘实况，
> 若后续有更新以新产物为准。
> 依据（全部已在盘）：`docs/HANDOFF_P01_REJUDGE_2026-10-18.md`（工作区最新版）、`docs/TASK_GONGSAI_LINE_TODO_2026-10-16.md`、
> `docs/P0_1_ERR_RATE_RESULT_2026-10-18.md`、`docs/P0_1_A_RULES_V3_DRAFT_2026-10-18.md`、
> `docs/P0_1_SISTER_ARBITRATION_PACK_2026-10-18.md`、`docs/P0_1_SISTER_ARBITRATION_ADDENDUM_O_SOURCE_2026-10-18.md`、
> `docs/mimo_p01_a_rules_v3_chem_review_{request,response}_2026-10-18.md`、`docs/P0_1_JUDGEMENT_CODEX_REVIEW_2026-10-18.md`、
> `docs/P0_1_PROBE_INITIATION_INPUT_2026-10-16.md`（设计稿）、`reports/ppv1_s5b/p0_1_initiation_input_2026-10-17/`（判读产物）。
> 产品目录缩写：下文 **⟦产品⟧** = `reports/ppv1_s5b/p0_1_initiation_input_2026-10-17/`。
> 题域标签：**298/RHEA 通用酶学/已见题**；判读零金标零题面。

## 1. 进程时间线（一步一行：干了什么 · 结论 · 产物）

| 时间 | 干了什么 | 结论 | 产物 |
|---|---|---|---|
| 10-15 晚 | P0 闭环漏斗三件套机械量（编译拒绝 5266 件/292 题、analog no_alignment 2818 件） | 均为机械量，不得当误拒量 | `reports/ppv1_s5b/p0_{funnel,rank_audit,ambiguity}_2026-10-15/` + `docs/P0_TRIO_VERDICT_2026-10-15.md` |
| 10-16 | 测量设计稿定稿（三值判定/uncertain 单列/分母纪律/分层抽样 seed=20261016/师姐确认流/正负控：二读门 ≥90% 且 κ≥0.6、负锚 >20% 误判⇒不采率） | 判定线一次写死 | `docs/P0_1_PROBE_INITIATION_INPUT_2026-10-16.md` |
| 10-17 白天（主会话自干） | 机械执行：A 2818→去重 1886→分层 155；B 224→去重 97 全查；材料包 155+97；闭合+重放校验 | 全过 | ⟦产品⟧ `sampled_{A,B}.json`/`material_packs_{A,B}.json`/`frame_{A,B}.json`/`p0_1_output.json`（seed=20261016） |
| 10-17 夜 | CC 五连拍板：修/派/按 mimo 修订/push/同意 v2 | 执行到齐；已 push `0865fba..e3fe446` | T-F 修复提交、V3 v2+mimo 场景1、chain14 归因+任务书、T-F 验证 |
| 10-17 夜→10-18 凌晨 | 第一轮判读（mimo 免费线，8 批）：A 5 批 155 + B 3 批 97 | 252/252 落盘（A 107 拒/27 过/21 存疑；B 96 拒/1 过） | ⟦产品⟧ `judgement_mimo_A_{pilot,batch2..5}.json`、`judgement_mimo_B_{batch1..3}.json` |
| 10-18 凌晨 | Codex 判读审（代审请求 04:50） | **回修**：P1-1 阳性锚与材料相反（a-075c…）；P1-2 二读门缺可核记录 | `docs/P0_1_JUDGEMENT_CODEX_REVIEW_REQUEST_2026-10-18.md` + 报告 + `docs/review_evidence/p0_1_judgement_codex_2026-10-18/` |
| 10-18 05:16 | P1-1 返工：a-075c0a3e10c5426f 锚修正、维持 pass | 单件闭合 | ⟦产品⟧ `judgement_mimo_A_case_rework.json` |
| 10-18 05:05 | P1-2 补独立二读（gpt-6-sol 30 件=second_read_sample.json） | **门未过**：A 12/15=80.0%、κ=0.505；B 0/15、κ=0 | ⟦产品⟧ `judgement_second_read_gptsol.json` |
| 10-18 05:08 | 结果表降级：正式降级为 judger 原始读数，T-G 消费挂起；按设计稿回炉条款处置（细化规则+Biii 强制子查+全量重判） | 回炉开工 | `docs/P0_1_ERR_RATE_RESULT_2026-10-18.md`（二读失败段） |
| 10-18 06:19–14:04 | **回炉 v2 重判**（细化规则版）：A b1→b5（+b1 跨会话自一致 recheck 08:04=32/34=94.1%）；B b1→b3 | 252/252 完成：A 109 拒/45 过/1 存疑（err_rate_raw=45/154=29.2%）；B 95 拒/2 过（=2/97≈2.1%） | ⟦产品⟧ `judgement_mimo_v2_A_batch{1..5}.json`（+`_recheck`）、`judgement_mimo_v2_B_batch{1..3}.json` |
| 10-18 14:37 | 手动通道交叉（CC 转发 mimo 判 B 批 3） | 5 过/26 拒；跨通道一致 **26/31=83.9%**；5 分歧=争议面 | ⟦产品⟧ `judgement_manual_channel_B_batch3.json` + `review_P0-1_误拒率_回炉批3_mimo.md` |
| 10-18 15:19 | **二读门复算**（tokeasy 撞额度→改 Codex fresh 会话 01a14ddb） | **B 通道 15/15=100% 过；A 通道 8/15=53.3%、κ=0.222 未过**（7 件分歧=反应中心/旁观位+uncertain 边界，双向非系统性） | ⟦产品⟧ `judgement_second_read2_codex.json` |
| 10-18 15:14–17:31 | 能力负锚三方读数：run1（v1 包）10 过/5 存疑/0 误判；发现 v1 包 bug（recorded 分支读 `products`，库字段实为 `product_smiles`）→ 修 v2 包重派；手动通道 8 过/7 拒；免费线 v2 包 11 过/4 拒=**26.7% 超 20% 线**（同材料 10 件跨会话仅 6/10 一致=自震荡） | 名义超线；与 A 门同根同处置（CC 拍板沿用 A 方案，手动数不计入门；负锚前提口径待裁定） | ⟦产品⟧ `judgement_mimo_v2_capability15_run1.json`（v1 包）、`judgement_mimo_v2_capability15.json`（v2 包正典）、`judgement_manual_channel_capability15.json`、`judgement_P0-1_mimo_2026-10-18.md`；`capability_packs.json`+`capability_pack_gen.py`（修复行 42–51） |
| 10-18 15:27–16:58 | CC 拍板 A 方案三件套：师姐裁定包（A7 分歧+B5 争议）、v3 规则草案、mimo 化学评审 | mimo 回应=「需修正」（修订 1/3/5/6 补强）；附问件 2 件（O 来源口径） | `docs/P0_1_SISTER_ARBITRATION_PACK_2026-10-18.md`、`docs/mimo_p01_a_rules_v3_chem_review_{request,response}_2026-10-18.md`、`docs/P0_1_SISTER_ARBITRATION_ADDENDUM_O_SOURCE_2026-10-18.md` |
| 10-18 18:12 | CC 拍板先交 Codex 代审师姐 12+O2 件（会话 01a14e7c） | 14 行全绿：A7 与 codex 二读 **6/7 一致**；B5 全判过（含 4 件主判拒翻转）；O2 均 uncertain、口径=证据集闭合 | ⟦产品⟧ `judgement_arbitration_codex.json`（14 行） |
| 10-18 19:04 | CC 拍板「Codex 代审意见=终审意见」→ 对账回填：修订 3/5 修正+**新增修订 7 材料保真纪律**（实锤主判两处材料误读）；B 组注记双层口径（judger 2/97 vs 终审翻转 6/97） | **v3.2 终审校准版定稿** | `docs/P0_1_A_RULES_V3_DRAFT_2026-10-18.md`（v3.2） |
| 10-18 19:05–19:42 | v3.2 第三轮 A 重判发车：批 1（34 件）免费线完成 | 17 拒/17 过；v2→v3 翻面 8 件全向过侧；验收三件套全绿 | ⟦产品⟧ `judgement_mimo_v3_A_batch1.json`（模板 `mimo_rejudge_v3_A_template.md`） |
| 10-18 19:43–21:32 | v3.2 批 2 免费线尝试失败 | **无产物**：opencode 日志两次「Response still truncated after two output token limit continuations」（20:39:52 会话 `ses_eb12d1fdaffe21dWA5bxrc20EA`、21:32 会话 `ses_eb0efbfc7ffedk0c22cq42O00v`，UTC+8 本地时） | 无 JSONL；⟦产品⟧ 仅有 `mimo_v3_A_batch2_prompt.md` |
| 10-18 20:43 | 出 5 份手动转发自包含任务书（批链改手动兜底，CC 拍板记录于 22:00 前后） | 34+34+34+34+19=155 件零重叠、材料全内联；仓内与 iCloud 副本逐字节相同（md5 逐件相等） | ⟦产品⟧ `mimo_v3_A_batch{1..5}_manual_prompt.md`；iCloud `~/Library/Mobile Documents/com~apple~CloudDocs/mimo_v3A_batch{1..5}_manual.md` |
| 10-18 23:06 | 移交书更新（另一窗口） | 工作区有 2 个未提交修改（移交书+TODO） | `docs/HANDOFF_P01_REJUDGE_2026-10-18.md`、`docs/TASK_GONGSAI_LINE_TODO_2026-10-16.md` |

**提交状态**：HEAD=`ff0b534`（移交书提交）；其后工作区修改未提交：`HANDOFF_P01_REJUDGE_…`/`TASK_GONGSAI_LINE_TODO_…`（M）+ 234 条 untracked（含全部 P0-1 判读产物与新增评审侧文档，按惯例留未跟踪）。

## 2. 当前精确状态表（以 23:12 前磁盘实况为准）

### 2.1 v3.2 第三轮 A 重判（进行中——批链 34+34+34+34+19）

| 批次 | 落盘文件 | 件数 | 三值分布 | 状态 |
|---|---|---|---|---|
| 批 1 | `judgement_mimo_v3_A_batch1.json` | 34 | 17 拒 / 17 过 / 0 存疑 | ✅（免费线；case 集合==manual 批 1 清单；pass 全带 anchor；judged_by=mimo-v2.6-flash-free） |
| 批 2 | `judgement_mimo_v3_A_batch2.json` | — | — | ❌**未落盘**（免费线 token 上限截断×2；手动任务书已备，尚未转发/回件） |
| 批 3 | — | — | — | ❌未派（手动任务书已备） |
| 批 4 | — | — | — | ❌未派（手动任务书已备） |
| 批 5 | — | — | — | ❌未派（手动任务书 19 件已备） |

批 1 是否手动重发=可选（不发则免费线结果留用主判；发则全程同通道、免费线那份转交叉验证）——CC/主窗口待决。

### 2.2 回炉 v2 重判（正典，252/252 全）

| 通道 | 批次文件 | 件数 | 三值分布 | 备注 |
|---|---|---|---|---|
| A = analog\|no_alignment | `judgement_mimo_v2_A_batch{1..5}.json` | 155 | 109 拒 / 45 过 / 1 存疑 | err_rate_raw=45/154=29.2%；另有 `_batch1_recheck`（同 34 件跨会话自一致 32/34=94.1%） |
| B = corpus\|mapping_enumeration_truncated | `judgement_mimo_v2_B_batch{1..3}.json` | 97 | 95 拒 / 2 过 / 0 存疑 | err_rate_raw=2/97≈2.1%；批 3 两件过=NADH 类干净二分映射被截断 |

### 2.3 第一轮判读（v1，已降级，仅供对照）

| 通道 | 文件 | 件数 | 三值分布 |
|---|---|---|---|
| A | `judgement_mimo_A_{pilot,batch2..5}.json` + `judgement_mimo_A_case_rework.json`（返工 1 件） | 155 | 107 拒 / 27 过 / 21 存疑 |
| B | `judgement_mimo_B_{batch1..3}.json` | 97 | 96 拒 / 1 过 / 0 存疑 |

### 2.4 门/交叉/负锚/代审读数（现存件）

| 项 | 文件 | 件数 | 读数 | 门判定 |
|---|---|---|---|---|
| 二读门第一轮（gpt-6-sol，对 v1） | `judgement_second_read_gptsol.json` | 30 | 13 拒/17 过 | A 12/15=80.0%、κ=0.505；B 0/15、κ=0 ❌ |
| 二读门第二轮（Codex fresh，对 v2） | `judgement_second_read2_codex.json` | 30 | 21 拒/6 过/3 存疑 | **B 15/15=100% ✅；A 8/15=53.3%、κ=0.222 ❌**（7 分歧=a-2027/a-9014/a-0120/a-079a/a-c2b2/a-6e42/a-ae58） |
| 手动通道交叉（B 批 3） | `judgement_manual_channel_B_batch3.json` | 31 | 5 过/26 拒 | 对 v2 主判 26/31=83.9%（5 分歧=b-ea54/b-63bc/b-4469/b-8863/b-35b8→进师姐争议面） |
| 能力负锚 run1（v1 包） | `judgement_mimo_v2_capability15_run1.json` | 15 | 10 过/5 存疑/0 误判 | 0% 误判，但 5 存疑=包生成 bug 所致 |
| 能力负锚 run2（v2 包正典） | `judgement_mimo_v2_capability15.json` | 15 | 11 过/4 拒 | **26.7%>20% 线**（4 拒=中心错配族 cap-ea49/daea/a87b/cae0；跨会话自震荡 6/10） |
| 能力负锚 手动通道（v2 包） | `judgement_manual_channel_capability15.json` | 15 | 8 过/7 拒 | 46.7%；CC 拍板手动数不计入门 |
| 师姐件 Codex 代审 | `judgement_arbitration_codex.json` | 14（主包 12+O 附问 2） | 9 过/1 拒/4 存疑 | A7 与 codex 二读 6/7 一致；B5 全过；O2 均 uncertain |

### 2.5 文档/模板/材料（关键件一览）

| 件 | 状态 | 说明 |
|---|---|---|
| `docs/P0_1_ERR_RATE_RESULT_2026-10-18.md` | 仍为降级版（05:08） | 主表=v1 读数（A 27/134=0.201、B 1/97=0.010）+二读失败段；**尚未重出表** |
| `docs/P0_1_A_RULES_V3_DRAFT_2026-10-18.md` | v3.2 终审校准版（19:04） | 含修订 1–7+校准样例；末段「发车状态」仍写 free-line（早于批 2 失败，未回写手动切换） |
| `docs/P0_1_SISTER_ARBITRATION_PACK_2026-10-18.md` | 已成稿（15:27，自包含零金标） | **仍在 CC 手中，待送出/回件** |
| `docs/P0_1_SISTER_ARBITRATION_ADDENDUM_O_SOURCE_2026-10-18.md` | 已成稿（16:58） | O 来源口径附问 2 件，可随主包同送 |
| mimo 化学评审请求/回应 | 已成对（15:28/16:27） | 回应「需修正」已并入 v3.1→v3.2 |
| ⟦产品⟧ 手动任务书×5 | 已备（20:43，仓内+iCloud 同字节） | 155 件零重叠 |
| ⟦产品⟧ 模板/样件 | `mimo_rejudge_v3_A_template.md`、`mimo_v3_A_batch{1,2}_prompt.md` | 占位符+sed 规矩在档 |

## 3. 后续 TODO list（按序；每项=做什么 / 判定线 / 谁干 / 产物落点）

以下 1–10 为 A 主线（判读），11–12 为并行线。

| # | 做什么 | 判定线/验收 | 谁干 | 产物落点 |
|---|---|---|---|---|
| 1 | **v3 A 批 2-5 手动转发+回件落盘**（批 2 重派优先；批 3-5 续发；批 1 可选重发）：把 iCloud/仓内任务书送 mimo，回复 JSONL 贴回 | 验收三件套：行数=34/34/34/19；case_id 集合==清单（a- 前缀）；pass_expected 全带 anchor；judged_by 标 `mimo(手动转发通道)` | CC/主窗口转发 + mimo（免费线判读） | ⟦产品⟧ `judgement_mimo_v3_A_batch{2..5}.json` |
| 2 | 负锚 v2 收数（**已完成，本项收口备案**）：免费线 11/4=26.7% 超线、手动 8/7、run1 10/5/0，三读数与跨会话自震荡已落盘 | 如实披露超线+处置沿用 A 方案；负锚前提口径（编译通过≠中心闭合）列待裁 | 已办（另一窗口） | `judgement_mimo_v2_capability15.json` 等 4 件（已落盘） |
| 3 | **师姐裁定包送出与回件**：主包 12 件+O 附问 2 件送师姐；回件原文落盘 | 14 行裁定（case_id\|三值\|一句话理由）+O 口径一行 | CC 送/师姐裁（Codex 代审已作预校准；师姐为最终生效口径，后置复核） | 回件落 `docs/`；确认回填 confirmed_by |
| 4 | **v3 对账修正**：师姐回件→条文对账（冲突条目就地修正）→校准样例入模板 | 与终审判例/师姐裁定无冲突；样例进模板 | 主窗口 | `docs/P0_1_A_RULES_V3_DRAFT_2026-10-18.md` 更新+`mimo_rejudge_v3_A_template.md` |
| 5 | **A 155 v3.2 全量重判**（进行中 34/155）：批 2-5 收口后拼全量 | 155 行、批间零重叠、并集==sampled_A | mimo（手动线为主） | ⟦产品⟧ v3 A 五批 judgement 文件 |
| 6 | **Codex fresh 二读门（v3.2 规则）**：30 件（second_read_sample.json），fresh 会话保独立；算 agreement+κ | **各通道 ≥90% 且 κ≥0.6**；A 16/17 件不一致即不过 | Codex（通道 B） | 新二读 judgment 文件（命名待定，如 `judgement_second_read3_codex.json`）+门计算记录 |
| 7 | **门过后重出表**：更新结果表（回炉终读数+门结果+条件读法+能力负锚记录） | 必含：**枚举上限 800 披露**（材料包文本 64 为旧值，`recorded_source.py:369 _INFER_MATCH_LIMIT=800`）；**B 双层口径**（judger 2/97 vs 终审翻转 6/97=「化学可行但截断因果未证」）；**手动交叉注记 26/31**；师姐确认为最终分子；298 题域标签 | 主窗口 | `docs/P0_1_ERR_RATE_RESULT_2026-10-18.md`（或新版日期） |
| 8 | **Codex fork 复审**：对重出表+全链复审 | 请求制式仿 `P0_1_JUDGEMENT_CODEX_REVIEW_REQUEST_2026-10-18.md`；fork 父=**01a14ba1**（判读审）或 **01a14ddb**（二读，可追问）取最新 | Codex | 复审报告落 `docs/`（+证据目录） |
| 9 | **师姐件收口**（pass 双锚+重放）：A pass 件（v3 全量后的最终清单，批 1 已 17 件）+B 2 件+5 争议面件+O 2 件逐件确认；重放正控（映射要点重放编译器）一并做 | pass 件经师姐确认才计分子；重放仍拒的降级存疑面；A 率裕量（27→14 敏感性）随确认更新 | 师姐（CC 送）+执行重放 | confirmed_by 回填；最终误拒率定稿 |
| 10 | **门再不过→升级 CC**：二读门/负锚任一未过，停下报 CC（附分歧样本） | 不自行处置 | 主窗口报 CC | — |
| 11 | **并行：证据卡 v2 实施单**（设计已冻结，通道 C 两轮+正链终认） | 按新派单规矩用 ZCode 本身子代理（执行类不走 opencode 免费线）；SMARTS 质子化容忍先行+冻结字段面+确定性锚 | ZCode 子代理 | 实施交付（另线） |
| 12 | 并行：T-H 修复批等 T-D/E/F/G 全齐 | blocked：等师姐 V3 冻结+误拒率定稿 | — | — |

（线外挂账：push 时机=P0-2/P0-3 随主线交付包，CC 拍板。）

## 4. 坑与机器参数（防再踩）

| 坑 | 规矩 |
|---|---|
| 提示词手拼 id 串 | **必须模板占位符 `CASE_IDS_PLACEHOLDER`+sed 换清单**（手拼两次翻车，其中一次静默无操作重复判读） |
| mimo 断流续跑 | 必须带 `-m opencode/mimo-v2.6-flash-free`（漏了会用默认模型 GLM 续跑走偏）；`opencode session list` 找会话→`run -s <id> "继续"` |
| 批验收 | 三件套：行数==预期；case_id 集合==清单；pass_expected 全带 mapping_anchor。CLI 退出码 1≠活没干完——以日志尾部+产物验收为准 |
| B 面前缀 | 材料包 case_id 是 `c-` 前缀（corpus→c），判读输出才是 `b-` 前缀，按 row_id 双射核对 |
| 枚举上限 | 源码 `_INFER_MATCH_LIMIT=800`（`src/pathway_v43/pollutant/recorded_source.py:369`）；材料包规则文本写「64」是旧值（`_COMPILE_ALIGNMENT_LIMIT=64` 是对齐面的另一常数）；判定语义不变（触顶即截断拒），**重出表须披露** |
| mimo 长材料 | 易撞输出 token 上限（v3 批 2 实例：20:39/21:32 两次「Response still truncated after two output token limit continuations」，无产物）；**小批量/手动通道兜底** |
| 免费网关 | 夜间慢+偶发 ConnectionRefused/断流；白天稳；批均 10–40 分钟；断流重试 1 次 |
| 派单 | 执行类子代理走 ZCode 本身子代理（OCAgent 停用）；mimo 免费线豁免（化学评审/判读）；Codex 通道 B fork 链与 tokeasy 通道 C 审核线不变 |
| 金标红线 | 判读材料零金标零题面；师姐件/回件涉金标往来入 gitignored |

## 5. 外部依赖挂 CC 清单

| 项 | 待决 | 说明 |
|---|---|---|
| 师姐裁定包送出/回件 | 主包 12+O 附问 2 件（CC 手里） | Codex 代审已作预校准；师姐为最终生效口径 |
| v3 批 2-5 手动转发 | 5 份任务书已在 iCloud（仓内同字节） | 回复贴回→主会话落盘+验收；批 1 是否重发可选 |
| 负锚前提口径 | 「编译通过=ground truth」与中心判据打架（4 件中心错配）；是否排除该族 | 随 v3.2 重跑一并计算披露；口径裁定挂 CC/师姐 |
| 门/负锚不过升级 | A 二读门若再不过→CC 裁定（再回炉/降级/单通道消费） | 不自动处置 |
| push 时机 | 工作区 2 个 M+234 untracked（评审侧文档惯例留未跟踪） | 随交付包，密钥扫描门先行 |
| 费用 | 本线零费用（mimo 免费线+Codex 订阅通道） | 无异常 |

## 6. 实况与既有摘要的不符项（如实记录，不静默修正）

| # | 既有说法 | 磁盘/日志实况 |
|---|---|---|
| 1 | 移交书 §3 步骤 0：「批 2 免费线 **ECONNRESET** 死中途无产物」 | opencode 日志（`~/.local/share/opencode/log/opencode.log`）**两次「output token limit 截断」**（20:39/21:32 本地时，会话 ses_eb12d1fdaffe21dWA5bxrc20EA / ses_eb0efbfc7ffedk0c22cq42O00v）；全日志 ECONNRESET 仅 10-07 两次。结论（无产物、批链改手动）不变，但根因表述以日志为准 |
| 2 | 移交书 §5 goal 大盘：「G1 回炉 **221/252**」 | §1/§2 已述 252/252（221 是 B 批 3 完成前旧数，§5 未同步） |
| 3 | 摘要「负锚 v2…当时在跑」/挂账「负锚 v2 收数」 | 已全部落盘：免费线 v2 包 17:31（11/4=26.7% 超线）、手动 16:54（8/7）、run1 15:14（10/5/0）；剩余挂账应改为「负锚 v3.2 重跑」 |
| 4 | v3.2 规则草案末段：「A 155 全量重判发车（mimo 免费线）」 | 批 2 起已改手动转发（批 1 免费线留用）；该末段未回写（v3.2 定稿 19:04 早于批 2 失败 20:39），以移交书新增段为准 |
| 5 | 梳理时点另一窗口仍活跃（移交书 23:06 在改、/tmp/p0_1_v3A_b1 23:07–23:08 生成批 1 复核中间件） | 状态可能继续变动；本件为 23:12 前快照 |