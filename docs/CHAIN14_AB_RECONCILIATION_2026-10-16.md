# chain14 A/B 交付补齐对账（PRED-8，298 题域，2026-10-16）

> 题域标签：**298 = RHEA 通用酶学/已见题**（全文数字一体适用；dev 与 298 双向不外推）。
> 性质：本地只读对账补齐单（PRED-8，父单 PRED-7 拆单 #0「chain14 交付补齐」）；
> **零模型、零 API、零费用**——本单无任何跑批/模型/网络动作，全部数字
> 由本地既有产物逐题复算。判读边界：**不重新裁定**「v1 不装载（其余族
> v2 strict 59→53 触发预注册停点）」，A 臂 91 仅作单次实测工作参照（沿任务书既定结论）；
> chain14 负结果按诚实负结果归档，无任何能力类表述。
> 复算输入（全部只读）：`reports/ppv1_s5b/chain14_{a,b}/`（metrics / metrics.v1 /
> batch_report / orchestration / progress）、`chain13_glm/metrics.json`、
> `p0_ambiguity_2026-10-15/`（phase_a_data / phase_b_agg / p0_ambiguity_groups）、
> `evidence_card_probe_2026-10-15/probe_report.json`。脚本副本与全量输出：
> `docs/review_evidence/chain14_recon_2026-10-16/`（README 含 SHA256 与复现命令）。

## 一、主表逐题复算（与任务书交叉核对：全部一致）

| 口径 | A（off） | B（on） | B−A | chain13 参照 | 逐题复算=聚合 | 任务书/结果报告 |
|---|---|---|---|---|---|---|
| hit@1（v2 headline） | 91（30.5%） | 85（28.5%） | **−6** | 87 | ✔ 逐题=聚合 | 一致 |
| hit@3 / hit@5（v2） | 116 / 121 | 116 / 122 | 0 / +1 | 112 / 118 | ✔ | 一致 |
| 严格覆盖（v2 strict） | 124 | 122 | **−2** | 119 | ✔ | 一致 |
| partial / uncovered | 49 / 125 | 49 / 127 | 0 / +2 | 47 / 132 | ✔ | 一致 |
| hit@1（v1 敏感性，metrics.v1 独立文件复算） | 86 | 81 | −5 | 83 | ✔ 文件内聚合=逐题 | 一致 |
| strict-rank>1 | 33 | 37 | +4 | 32 | ✔ | 一致 |

配对与迁移（逐题配对复算，298 题域）：hit@1 双臂同时命中 77 题；**A 对 B 错 14 题、A 错 B 对 8 题，翻转 22/298，净 −6**；S/P/U 三状态变化 **45/298**（m→m 段 7、u→m 段 18、m→u 段 20；即 S→P 5、S→U 8、P→U 12、P→S 2、U→S 9、U→P 9），**strict 流出 13 / 流入 11，净 −2=122−124**（不是 25−20 的差）。与任务书主表及 `docs/CHAIN14_EVIDENCE_AB_RESULT_2026-10-16.md` 逐项一致，无一处不一致需要并列。

## 二、108 题精确歧义面转化率（本节核心缺口与可得替代口径）

### 2.1 成员口径（据预注册→P0 三件套→歧义探针原文）

口径链（预注册 §三.2 引用的题单来源= `docs/P0_TRIO_VERDICT_2026-10-15.md` → `reports/ppv1_s5b/p0_ambiguity_2026-10-15/`）：**歧义组 =（substrate_smiles 全等的）底物跨题组内 ≥2 题且组内 distinct 参考身份 ≥2**；参考身份 = 参考图内 role==principal_product 节点的 RDKit canonical SMILES 排序元组。聚合结果（`phase_b_agg.json`，HPC 判分侧金标面唯一出口）：**38 组 / 108 题**（组规模 2/3/4/5/6 = 20/8/7/2/1；组内目标多重性 2/3/4 = 27/7/4），**干净子集 34 组/97 题**，含真空题（decide 未提交）子集 **4 组/11 题**；底物跨题组面共 53 组/142 题（=108 的上界代理面），独苗底物 156 题非歧义。

### 2.2 精确逐题答案（诚实结论：本地不可得）

**108 面的逐题成员名单本地不可复得，因此逐题精确转化率按任务书口径如实记为缺口（unknown），不编造数字。** 原因（探针原文）：参考身份判定在 HPC 判分侧进程内完成，回传的唯一出口是聚合计数；「哪个组歧义」级别的组 id 是由底物派生的组级金标信息，遵守金标纪律未回传本地（`phase_b_agg.json` 逐键审计原文：「无 qid、无组 id、无 SMILES、无参考图身份」）。本地可得仅：qid→底物组映射（`p0_ambiguity_groups.json`，零金标）、底物组规模直方图、歧义组规模/多重性直方图与解析题数聚合计数。若需逐题精确化，应走判分侧受保护执行另立授权，本单不代做。

### 2.3 本地可用且已复算的替代口径（数字全部逐题复算，298 题域）

| 替代口径 | n | hit@1 A→B | strict A→B | 另附（同面内） |
|---|---|---|---|---|
| **上界代理面**（底物跨题组 53 组，⊇108） | 142 | 37（26.1%）→ 35（24.6%），**B−A −2** | 55（38.7%）→ 57（40.1%），Δ +2 | hit@3 A 51→B 53 |
| **互补独苗面**（底物单题组） | 156 | 54（34.6%）→ 50（32.1%），**B−A −4** | 69（44.2%）→ 65（41.7%），Δ −4 | hit@3 A 65→B 63 |
| 选择面（chain13 strict-rank>1，本地逐题可复得） | 32 | 7（21.9%）→ 5（15.6%），**B−A −2** | 23（71.9%）→ 25（78.1%），Δ +2 | strict-rank>1 16→20 |
| 其余族（不在选择面∩不在 142 代理面的补集，代账） | 141 | 52（36.9%）→ 49（34.8%），**B−A −3** | 59（41.8%）→ 53（37.6%），**Δ −6（停点触发项，复算吻合但本单不重裁）** | strict-rank>1 7→4 |

与结果报告已载分族数字 7→5 / 23→25、37→35 / 55→57、52→49 / 59→53 全部吻合；其中 142 代理面即结果报告标注的「歧义 108 上界代理面」。

### 2.4 零金标紧界（108 面命中数可行域，真实值必在其中；不是点估计）

108 面 = 142 面 − 15 个非歧义跨题组（34 题；组规模直方图 2→11、3→4；规模 4/5/6 组被歧义直方图整体占用，不会被移出）。组身份（哪些组歧义）属金标面，仅按聚合约束对移出组合做全置换搜索得紧界：

| 量 | 可行域区间（真实值必在其中；非点估计） |
|---|---|
| A 臂 108 面 hit@1 命中数 | [11, 37]（率 10.2%~34.3%，n=108 口径） |
| B 臂 108 面 hit@1 命中数 | [10, 35]（率 9.3%~32.4%） |
| A 臂 108 面 strict 命中数 | [25, 53] |
| B 臂 108 面 strict 命中数 | [26, 54] |
| 108 面 B−A（hit@1，并集差界，非配对界） | [−27, +24] |

追加**可证子集**（本地零金标推得，比位整组认证）：本地运行侧字段 cand_face_status（`p0_ambiguity_groups.json`，chain13 判定）与 phase_b 判分侧聚合在含真空题组上严格相等（本地 4 组/11 题 = 判分侧 4 组/11 题）→ **该 4 组（规模 2×3 + 5×1 = 11 题）全体成员必然落在 108 面内**；其成员名单出于组级金标纪律不在本对账文档点名（判分侧同层亦未回传）。其上实测（n=11）：**A hit@1 = 0、strict = 2；B hit@1 = 0、strict = 1**。该子集与选择面 32 题交 0 题；13 题真空全卷中 8 题在独苗组、与歧义面无关。
选择面 ∩ 108 面：可证 0 题、计数参照界 [6, 17]——上界 17 = 选择面∩142 代理面（移出组可避开全部选择面成员）；下界 6 = 17 − 11，其中 11 = 选择面 ∩ 可移出池成员数；率 5.6%~15.7%（n=108 口径）。

### 2.5 与任务书口径的对齐结论

任务书未载 108 面转化率任何数字（只标为待补），无与任务书数字冲突项；142 代理面与其余族数字与任务书/结果报告全部一致。**108 面逐题转化率维持缺口（unknown）**，本节给出：口径原文链、缺口原因、两个本地精确替代面（142/156）、零金标可行域紧界、以及一个 11 题的可证子集精确统计——以上可交付积 block 判分侧作后续精确化时的对照锚。

## 三、usage / cost 缺口披露（`batch_report.json` account 块原文抄录）

| 字段（原文） | A 臂 | B 臂 |
|---|---|---|
| `usage_status` | `"partial_unknown"` | `"partial_unknown"` |
| `usage_missing_calls` | **2** | **4** |
| `usage_known.input_tokens` | 795,192 | 1,006,206 |
| `usage_known.output_tokens` | 5,805,679 | 5,869,225 |
| `usage_known.total_tokens` | **6,600,871** | **6,875,431** |
| `model_calls_total` | 303 | 304 |
| `model_call_retries_total` | 6 | 5 |
| `cost_known_cny` | `null` | `null` |
| `cost_status` | `"no_snapshot"` | `"no_snapshot"` |
| `budget_mode` | `no_monetary_cap_user_decision` | 同左 |
| gate：`total_requests` / `total_429` / `total_forbidden` / `stopped` | 303 / 0 / 0 / null | 304 / 0 / 0 / null |
| `n_failed`（progress.json/ batch terminal 计数） | 0 | 0 |

复算与任务书一致：已知 tokens 6.60M/6.88M（两臂合计 13.48M ≈ 预注册 no-cap 12.6M 档量级）；**B 臂 input +26.5%**（1,006,206 vs 795,192；任务书/结果报告「约 +26%」吻合）。
`batch_report.json` note 原文：`失败题留 298 分母、不剔题;usage 缺失保守预留(known-usage 小计与总费用分开);账单回填后核对`。
**「双臂零 failed 是运行终态，不代表主跑零费用」**：n_failed=0 与两臂 gate 429/forbidden 为 0，均不产生任何金额记账；金额 unknown 由 `cost_known_cny=null / cost_status=no_snapshot` 原文承载，账单回填后另核。B−A 配对口径下同原结果报告口径一致，未二次新加判定。
逐题调用量出库（零金标）已另存：`docs/review_evidence/chain14_recon_2026-10-16/chain14_{a,b}_cases_zero_gold.json`（各 298 条：qid/run_id/model_calls/status/export_digest/failure_kind/stop_reason/endpoint_status）；两臂 model_calls 逐题分布：A 1×289、2×7、0×2；B 1×288、2×8、0×2（计数与 account total_calls 一致）。

## 四、证据字段覆盖率（字段清单、覆盖数与率、A/B 分别报）

**运行级披露字段**（字段清单 | 值 | 覆盖数/率 per 臂）：

| 字段 | A 臂 | B 臂 |
|---|---|---|
| `batch_report.evidence_card_enabled` | `False`（1/1=100%） | `True`（1/1=100%） |
| `orchestration.evidence_card_enabled` | `False`（1/1=100%） | `True`（1/1=100%） |

**载荷字段覆盖率——两臂题级：本地不可得（缺失，不是 0）**。载荷落 HPC 封存根（`orchestration.runs_root=/work/home/.../runs/chain14{a,b}_s5b_20261015`），本地判分侧产物（metrics/batch_report/orchestration/progress）**不含任何载荷内容字段**，逐题证据字段覆盖率无法本地统计（A 臂按预注册走「字节兼容路径」，证据字段本就不入载荷，覆盖率=0 是设计使然、非缺失；B 臂覆盖率=真实开启统计，本题级数字本地 unknown）。

**可作为设计面覆盖数锚的探针产物**（`probe_report.json`，offline 只读双跑字节全等都 `True`）——其字段清单即候选级+底物级证据卡字段总表：

| 字段（候选级，12 真实批 spec 池条目） | known/total | 率 |
|---|---|---|
| edit_summary / edit_summary.{n_edits,op_counts,bond_order_changes,added_atoms} | 12/12 ×5 | 100% |
| participants | 12/12 | 100% |
| source.{source_kind,transformation_ref,origin_group_key,alignment_ref} | 12/12 ×4 | 100% |
| alignment_quality.{status,n_donor_atoms_mapped} | 12/12 ×2 | 100% |
| alignment_quality.{mapping_origin,n_alignments_total,n_equivalent_alignments,enumeration_truncated,stereo_dissolution_applied} | 0/12 ×5 | **0%**（real batch spec 库没有 compile diagnostics 块的历史欠账，**欠账如实披露**） |
| conditions_and_scope.requirements | 0/12 | **0%** |
| conditions_and_scope.{participant_list_status,step_scope} | 12/12 ×2 | 100% |
| 底物级 7 字段（condition_keys_known/element_counts/functional_groups/gasteiger_charges_reference/molecular_formula/representation_fidelity/substrate_render_ok） | 20/20 ×7 | 100% |

（合成 supplement 表 6 条另有 container 级对照，见 probe_report.md 原文；其本身 limitations 原文两条随载：「real batch s5b_298_local specs predate compile diagnostics block ⇒ compile-derived fields unknown in real-batch table; supplement table measures current shape」「chain13 synced runs carry no run_inputs/plan.pools ⇒ current-shape real entries unavailable offline」。）

**口径说明**：本节「字段清单」= candidate-evidence-2 / candidate-evidence-descr-2 载荷文档面（`src/pathway_v43/pollutant/candidate_evidence.py`）＋运行级开关两处；「覆盖数与率」仅在探针 offline 样本（真实批 spec 12 池条目、底物级 20 题）上成立；**两臂本批题级真实载荷覆盖（B 臂）本地 unknown**，属于与 usage 同源「账单回填后核对」性质、非本单可补齐项。B−A 配对由 A 臂 design-off vs B 臂 design-on 字段价差支撑，与预注册 A/B 单差分设计一致（两臂 prompt 同版纪律）。

## 五、分族重叠披露（代账口径，非互斥记账）

**重叠事实**（本地逐题复算）：选择面 32 题 ∩ 上界代理面 142 题 = **17 题**；选择面 ∩ 独苗 156 面 = 15 题；其余族 141 = 298 − |选择面 ∪ 142 面|（补集代账，本身与其余两栏互斥，但「32+142+141=315 > 298」的出现源于选择面 17 题被两栏同时计入，故三栏**不能当互斥三栏相加**）；相互关系结构上：**108 ⊆ 142**（歧义组⊆底物跨题组），108∩其余族 = 0、108∩选择面 ∈ [6, 17]（据 §2.4 界与选择面 ∩ 独苗面=15 推得，组级身份本地 unknown）；**可证交集补充：108∩可证子集（4 组 11 题）= 11；而选择面∩可证子集 = 0**。
对账张力披露：任务书/预注册以「选择面 32 / 歧义 108 / 其余」三栏分账，而其口径链分属 chain13 选择面（32 题逐题成员可复）与 108 上界代理面（142 题，逐题成员可复）与 142 补集（141 题，逐题成员可复）；108 精确面成员逐题不可复得（金标面）——本对账提供两个替代口径与紧界（§2.3/§2.4），供后续精确化时对齐用；本单不改写任何一栏口径。

## 六、遗留与假设

1. **108 面逐题精确转化率 = unknown（本地）**（原因/口径/替代口径/紧界已全列 §2.2–§2.4）；如需逐题精确化须另行授权判分侧受保护执行（HPC 金标面内的组身份判定回传），非本单本地可补项。
2. **usage 回填挂账**：金额 unknown（cost_known_cny=null、cost_status=no_snapshot）、兜账缺 2/4 次调用 usage；待账单回填后核对。
3. **题级载荷证据字段覆盖率**：B 臂本地 unknown（载荷在 HPC 封存根）；如需逐题载荷证据成册须另行授权判分侧执行。
4. 运行侧环境假设（无人值守，保守处置）：任务书载明前置检查=217 条未跟踪（??）零已跟踪改动；本单开工实测 220 条（含 1 条已跟踪变更 `M AGENTS.md` 的 Multica 运行时自管理注入块——平台自动管理、注明 do-not-edit，非同期代理产物），交活时 222 条（仍仅此 1 条 M，其余全为 ??；增量 2 条目均为本单产出）。**本单未触碰 AGENTS.md**（diff 与开工时一致，241 行），全程未切分支、未 git add、未 commit、未 push，不改任何已跟踪文件，新增文件仅本单产出；`reports/`、`runs/` 只读（未写任何东西）；分析脚本在仓库外全新临时目录执行，证据产物（脚本副本+输出）落 `docs/review_evidence/chain14_recon_2026-10-16/`。
5. 本对账不改写任务书口径、判定线与叙事纪律（chain14 负结果按诚实负结果归档，禁止能力类表述）；对外数字全部带 298 题域标签（dev 与 298 双向不外推）。
