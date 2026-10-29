# PPV1 S5b 298 全量跑：结果审核与调优建议（2026-10-09）

撰稿：S5b 审核子代理（当日，基于官方终判分与批根全量只读取证）
读者：teacher 黄（专家向，不做通俗化）
题域声明：本文全部对外数字属 **298 题域**（RHEA 通用酶学）；dev 题域数字不外推、不混报。
口径声明：**主口径（新严格口径）** 与 **老口径敏感性（v43-ec298-scorer-2 官方"整串任一命中"复刻）** 是两把尺子，**互不可比**；引用老系统数字一律注明锚次（首轮锚=通过线锚 116/128/130；复测锚 C0=136/182/186，**首轮与复测锚互不可比**）。

数字版本：**官方终判分**（远端 chain8 自动判分链输出，2026-10-09 10:24 UTC = 18:24 CST；`CHAIN8_SCORE_EXIT=0` → `CHAIN8_BASIS_OK graphs=298`）。本文不使用中期下界视图作为正文数字（中期 18:15 视图仅在第 1.1 节披露一笔）。判分数字一律引自冻结判分链输出（批根 `metrics.json` / chain8 `score` 命令），未自行重算口径。

---

## 0. 结论摘要

| 口径（题域 298，分母 298，零 LLM 判分） | hit@1 | hit@3 | hit@5 |
|---|---|---|---|
| **主口径**（参考边召回 matched_strict，事件报告序） | **39**（13.09%） | **72**（24.16%） | **74**（24.83%） |
| **老口径敏感性**（官方整串 any-one 复刻） | **71**（23.83%） | **111**（37.25%） | **122**（40.94%） |
| 多组分 any-of 探索表（不与主表混算） | 72 | 114 | 125 |
| 预注册通过线（锚=老口径首轮） | ≥116 | ≥128 | ≥130 |

- **§9-4 配对硬门：通过**（`coverage_report.pairing.bases_by_graph` 全部 298 图 = `qid_strict`；chain8 判 `CHAIN8_BASIS_OK graphs=298`）。分数可采信。
- 双口径均未达预注册线。老口径为与老系统可比口径：本批 71/111/122 对复测锚 C0 136/182/186（同口径可比）为 **52.2% / 61.0% / 65.6%** 相对水平。
- 两口径命中集合关系：主口径 74 题命中 ⊂ 老口径 122 题命中（both 74、old-only 51、main-only 0）；51 题差 = 参与物覆盖非 exact 的 15 题 + 产物串命中但必答节点未覆盖的 36 题（身份级近似，见 §2.2）。
- 主口径 95% CI（S1 bootstrap，单题簇，不消除跨题相关）：hit@1 [9.4%, 17.1%]，hit@3 [19.5%, 28.9%]，hit@5 [20.1%, 29.9%]；Wilson 按题 hit@1 [9.7%, 17.4%]。
- 失分主结构（详见 §2）：187 题"必答节点未覆盖"中，**约 35 题为身份级近似未中**（互变异构/立体化学/质子化状态），23 题官能团级答偏，84 题反应方向未中，45 题**提案全被执行期结构化拒因拒掉（零假说完成）**；另 22 题整题 run 失败（17 我方展开计划互斥冲突 + 5 模型 SMILES 不可解析）。芳香/凯库勒表示鸿沟是最大单一执行期损耗源（880 次展开尝试中 306 次失败，芳香相关两类占拒因大头）。
- 判分零 LLM；金标仅进入判分进程；本文零金标内容（附录 B 泄露扫描 0 命中）。

---

## 1. 审计段

### 1.1 发车史、作废披露与修复链

**尝试 1（已作废，如实披露）**。批根 `s5b_298_20261009_batch`。冒烟 10 题中 6 完成、3 失败：2 例 `KeyError 'aromatic'`（我方代码 bug：proposals 提示词键级词表含 `aromatic`，而执行器 `execute_edits` 为凯库勒空间只认 single/double/triple，模型按词表规范输出即崩）；1 例 `expansion_status_conflict`（模型侧提交契约冲突，按预注册记模型侧诚实失败）。约 15 次真实调用随批作废，原批根保留只读（约 15 调用未单独计价，见 §1.2）。

**修复 57ea99b**（本仓 HEAD，本轮已核 `git rev-parse HEAD` = `57ea99b47e1…`）：
- `execute_edits` 对未知键级词落结构化拒因（`edit_execution_failed:bad_bond_order:…:to_aromatic:…`）不抛异常；proposals 提示词词表改 `single|double|triple`；`PROPOSALS_PROMPT_VERSION` 为提示词内容 SHA256，自动升版。
- 全仓 1788 测试绿后仅两 src 文件（`real_model.py`、`atom_tool.py`）重部署 Chenyu 批代码目录。
- **部署核验（本轮新增）**：远端批代码两文件 SHA256 `7b39136e0a67…`（real_model.py）/ `f2efc993ee33…`（atom_tool.py）与本地 `git show 57ea99b:...` 逐字节一致。
- 修复前后行为差异：崩溃（整题 KeyError）→ 结构化拒因（提案级拒绝、run 继续）。修复后模型仍会输出 `to_aromatic`（词表遵从度有限，见 §2.2 拒因普查），但不再产生整题崩溃。

**尝试 2（官方批）**。批根 `s5b_298_20261009_batch2`。冒烟 10 题重跑 **10/10 终态、零代码崩溃**（原 2 崩题一活一走完多轮追问）；后按用户指令白名单推全量：288 qid = 冻结注册序 298 − 冒烟 10，17:25 CST（09:25 UTC）起跑 40 路；最后 1 题长尾 ~18:23 CST 收口、cases 计数达 298；chain8 依脚本自动执行"零 LLM 判分 → §9-4 硬门 → 报告落盘"，`CHAIN8_SCORE_EXIT=0`、`CHAIN8_BASIS_OK graphs=298`。中期判分（18:15，288/298 终态、10 题按漏计）主口径 39/71/73、老口径 70/110/121 —— 与终数差 = 长尾 1 题（主口径 rank 3 内命中、老口径 rank 1 命中）+1 题转 failed；终局无 no_case。

**预注册状态**。`prereg-s5b-2026-10-09`，批根 `preregistration_approval.json`：`approval_status=preregistration_confirmed`（2026-10-09T09:03:07+00:00 落盘），`user_authorization=launch-authorized-2026-10-09`。通过线 116/128/130 冻结于判分代码（`S5B_PASS_LINES`，s5b-scoring-1），判分时零触碰。

**SHA 锚**：
- 题卷：`questions_source_sha256 = 9f5955d418c2f387…`（批清单在档；两端当日核过，本报告沿用任务书口径）。
- 代码：部署两文件哈希见上；批 `run_identity.code_identity.aggregate_sha256 = c637fda4fbff…`；类比语料 `analog corpus v1，sha256 8f3f2c1ac0cb…`（run_identity asset_identity）。
- 模型身份：`ZHIPU/GLM-5.3-Flash`（dashscope 兼容通道，env 注入；密钥零回显）。

### 1.2 调用与费用账

| 项 | 数值 | 来源 |
|---|---|---|
| gate 请求启动 | **310 / 894 上限（34.7%）** | gate/gate.json（终态） |
| 429 | 15 次（其中 3 次重试耗尽） | 同上 |
| 并发峰值 | 40（= max_in_flight 上限） | 同上 |
| RPM / TPM 上限 | 180 / 2.7M（无 stopped） | 同上 |
| 计费调用 | 全量段 288（266 完成 + 22 failed）+ 冒烟段 10 = 298 次成功调用；另 4 次调用层错误（3 `rate_limited_exhausted` + 1 `empty_response`） | batch_report×2 + 调用账本聚合 |
| tokens（全量段，usage_status=known，缺失 0） | in 270,604 / out 5,001,101 / total 5,270,705 | batch_report.account |
| 费用（价格快照 0.8 / 2.8 CNY/Mtok，快照在位） | 全量段 **14.2168 CNY**（独立复算 ≈14.22，一致）；冒烟段 **0.5628 CNY**（3 调用 usage 缺失，known-usage 小计口径）；合计 **≈14.78 CNY** | batch_report×2 + price_snapshot.json |
| batch1 作废段 | ~15 调用，未单独计价（作废披露，不与上两段混算） | 任务书口径 |
| 墙钟 | 全量段 3,534 s（≈59 min）+ 冒烟重跑 1,721 s | batch_report.wall_clock_s |

"快照缺失⇒不计价"逻辑未触发（快照在位）。观测两点：(a) 计费 output 均值 ≈17.4K tok/调用，远大于响应正文中位 1,926 字符——差额应为模型侧 reasoning token 计费（推断；与调用耗时中位 279 s / p90 800 s / max 2,054 s、per-call timeout 3,600 s 一致）；(b) 每题恰好 1 次调用（298 个调用账本文件，每文件恰 2 条记录 = 1 issued + 1 完成），无格式反馈轮消耗——429 耗尽与空响应**未触发题级重试**，4 题按空跑计未命中（§2.2）。

### 1.3 提示词版本机制与批身份

`PROPOSALS_PROMPT_VERSION = sha256(_PROPOSALS_SYSTEM_PROMPT)`（`real_model.py`），内容变更自动升版，随 `run_identity.prediction.prompt_versions.proposals` 入批身份，旧批 resume 按身份拒。本批值 `5089601593d5…c6fba`（run_identity 与本地 HEAD 计算一致，两端核过）。模型 id `ZHIPU/GLM-5.3-Flash`。任何提示词内容改动 = 新批身份——这是机制而非障碍；§3 各提示词建议均以此为前提（改动随下一轮预注册批入账）。

---

## 2. 失分结构（证据导向）

### 2.1 分桶语义（先核代码，再解读）

以下语义已在 `src/pathway_v43/pollutant/s5b_scoring.py`（`_bucket_counts` / `_main_caliber_row`）与 `evaluation.py`（`match_reference_edges`）核实：

- **buckets 为按题计数、两遍叠加**：第一遍每题计入其首参考边 `match_status` 桶（各桶之和 = 298）；第二遍对 run 状态非 completed 的题**追加** `run_<status>` 桶（与第一遍重叠）。因此 `run_failed 22` 是叠加披露，不在 298 之内外加。
- 终局分桶（题数）：`matched_strict` 74，`matched_participant_coverage_partial` 15，`unmatched_required_node_uncovered` 187，`not_evaluated_no_edges` 22（= 22 个 failed run，评测器无该样本边匹配），`run_failed` 22（叠加遍）。终局无 `run_no_case`。
- `unmatched_required_node_uncovered`：该边声明的**必要 from/to 参考节点至少一个无许可严格命中**（S5A-03：空严格命中集不并入整侧 union，保持未覆盖）——不是"完全没答题"，而是"必答节点（通常是产物侧之一）结构未严格命中"。
- `matched_participant_coverage_partial`：结构候选存在、step_scope 一致，但事件参与物集合与参考声明集合**非 exact**（超集=多写共产物，或子集=缺声明参与物）。
- 主口径 hit@K：候选 = 根参考节点严格命中反应物侧的全部已提交事件按 `(created_at, event_id)` 升序；rank = 首 `matched_strict` 事件位次；分母固定 298。本批 `matched_event_not_in_candidates` = 0（rank 归位无异常）；宽度外产物（report_rank=None）仅 4 例。
- cases 普查（298 题终局）：completed 276 / failed 22（`expansion_status_conflict` 17 + `unparseable_smiles` 5）；全部题 `model_calls=1`；completed 题 `stop_reason` 一律 `budget_limit`（每题 1 次提案调用的设计终点），`endpoint_status` 全空。

### 2.2 全量失分分带（298 全体）

对每题"预测态集合 vs 金标产物集合"做 Morgan(2) Tanimoto 接近度分带（比对仅在远端只读分析进程内完成，正文零金标内容），交叉"是否有假说留存"：

| 桶（题数） | exact 产物在预测态中 | 近似 ≥0.90 | 0.60–0.90 | <0.60 | 零态 |
|---|---|---|---|---|---|
| 主口径命中（74） | 74 | — | — | — | — |
| partial（15） | 15 | — | — | — | — |
| uncovered（187） | 14 | 21 | 19+4* | 84+45* | — |
| failed（22） | — | — | — | — | 22 |

\* 格式为"带假说 + 零假说"。

结构化解读（298 题）：

1. **身份级近似未中 35 题**（uncovered 中 exact 14 + near≥0.90 21，全部带假说）：预测态里已经出现与金标产物**完全同结构**（14）或 ≥0.90 近似（21）的分子，败在共产物/参与物/表示层。抽样归因（§2.3 样本）：互变异构体（模型给烯醇式、金标酮/内酰胺式）、立体化学未标注（金标带绝对构型、模型给非立体式）、质子化状态差一个质子（无机磷酸/膦酸酯类产物）。这 35 题是**口径严格性的直接成本**，也是老口径 51 题 old-only 差的主体来源（old-only 51 = partial 15 + uncovered 36，后者与 35 高度重叠）。
2. **官能团级答偏 23 题**（0.60–0.90）：找对了反应位点家族但深度/位置错——氧化深度跳档（醇直接到酸、漏醛）、断键位置选错（磷酸酯 O-烷基 vs S-芳基）、对称杂环双侧取代基水解选错 N 位。
3. **反应方向未中（带假说）84 题**：提案全程与金标产物远带（<0.60）——反应类别/方向错误或仅提出底物自异构化类无效位移。
4. **零假说完成 49 题**（<0.60 带 45 + 0.60–0.90 带 4）：run "completed" 但**全部提案被执行期结构化拒因拒掉**，导出零假说零事件。含 4 题调用层错误（3×429 重试耗尽 + 1 空响应，按空跑完成）。
5. **整题 failed 22 题**：17 `expansion_status_conflict` + 5 `unparseable_smiles`，零态零事件，全部留分母。

**执行期拒因普查**（880 次展开尝试的 `expansion_outcome.json`，306 次 ok=False，多项拒因并存）：

| 拒因（前缀） | 次数 | 说明 |
|---|---|---|
| `edit_execution_failed:bond_order_mismatch` | 258 | 以 `expected_aromatic_have_single/double` 为主：编辑/模板的**芳香空间**键级假设撞**凯库勒空间**执行器 |
| `edit_execution_failed:bad_bond_order` | 229 | 含大量 `to_aromatic`：模型在词表已改后仍输出 aromatic 键级（57ea99b 后不再崩溃、改为提案级拒绝） |
| `edit_execution_failed:bond_already_present` | 146 | 重复成键 |
| `edit_execution_failed:sanitize_failed` | 79 | 施加后 sanitize 失败 |
| `bond_not_present` / `unknown_atom` | 12 / 2 | — |

→ **芳香/凯库勒表示鸿沟是最大单一执行期损耗源**，与 57ea99b 事故同根：修复消除了崩溃，但表示层冲突仍系统性吞掉提案（零假说 49 题的直接成因）。这是三轴调优的公共靶点。

### 2.3 抽样模式归类（10 题；只给模式名+定性证据，金标内容零入文）

样本选取：uncovered 均匀抽样（主失/老中分层）+ partial 1 + failed 2；qid 前缀索引（全 qid 见批根 metrics.json `per_qid`）。

| qid 前缀 | 桶 | 模式 | 定性证据 |
|---|---|---|---|
| RXNG_94539b62 | uncovered（exact 带） | 互变异构体表示差 | 断键正确、两产物之一精确，另一产物给烯醇式而金标为酮式（同分子式、结构不同） |
| RXNG_efa6ffdf | uncovered（near 带） | 立体化学未标注 | 还原产物结构与金标一致但缺绝对构型标注 |
| RXNG_36ff61dc | uncovered（exact 带） | 质子化状态差 | 有机主产物精确；无机产物差一个质子（去质子化级） |
| RXNG_04365649 | uncovered（far 带） | 反应类别未中 | 仅提出底物自异构化/互变位移，未做要求的 C-C 断裂 |
| RXNG_eb864c39 | uncovered（mid 带） | 氧化深度/区域误配 | 提出氧化但深度跳档（越过目标氧化级）且丢取代基 |
| RXNG_d6da5d9a | uncovered（mid 带） | 断键位置选错 | 磷酸酯类底物断错侧（O-烷基侧 vs S-芳基侧） |
| RXNG_e0bca299 | uncovered（mid 带） | 对称杂环位点选择错 | 双取代杂环水解选错取代基侧 |
| RXNG_66271eac | partial | 共产物多写 | 主产物精确；多写无机小分子共产物（酸/气态氧化物类）→ 参与物覆盖超集 |
| RXNG_0a2c91bd | failed（esc） | 正确化学已提案、死于计划冲突 | 调用响应里已含与金标同反应类别的 novel 提案（硝基部分还原方向），run 终结于展开计划对同一产物互斥状态 |
| RXNG_330b8f55 | failed（us） | 模型 SMILES 不可解析 | 整题零态报废 |

`expansion_status_conflict` 机制定位：`store._check_expansion_plan`（R2-09）提交期校验——同一事件展开计划对同一 `state_ref` 给出多个互斥状态即 fail-closed 拒绝整题。触发形态（重复产物/coproduct 映射到同一状态）需一根因探针钉死，列为下轮前置项（§3 轴 1-2）。

### 2.4 提案来源结构（全量调用账本 298 文件 + 导出假说 495 条）

- 提案量：905 条（292 个可解析响应；2 响应整体不可严格 JSON 解析，其题终态入分桶）。其中**池 id 提案 331（36.6%）**、**novel 提案 574（63.4%）**；252/292 题（86.3%）含 novel；**零弃权**；rank 清单 292/292 齐备，novel 被模型排首位 129/252。
- novel 引用率：574 条 novel 中 **140（24.4%）** 给非空 `reference_hypothesis_ids`，434 空引用（该字段模型侧自由填写，浅语义，仅登记不作依据）。
- 留存（导出假说 495 条，按 `origin_group_key` 前缀区分来源；`proposal_context` 不落假说行，已抽样核对无模板来源假说即 novel 接受）：**analog-template 92**（= 池提案留存率 92/331 ≈ 27.8%）+ **无模板来源 403**（= novel 留存率 403/574 ≈ 70.2%）。模板 spec 的执行留存率显著低于 novel——与拒因普查中模板侧芳香键级错配集中一致（§2.2）。
- **来源 × 命中**（题级）：analog-only 题 21 题中 14 中（**66.7%**）；mixed 题 35 题中 14 中（40.0%）；novel-only 题 170 题中 60 中（**35.3%**）；零假说 71 题 0 中。
- **池深 × 命中**：命中题均池深 0.95 vs uncovered 题 1.36；空池 120 题中 35 中（29.2%）vs 非空池 178 题中 39 中（21.9%）。**负向关联**——合理解释有二（未证，仅登记）：0.45 阈值召回的模板偏向难题底物；或模板错误断键先验误导（RXNG_d6da5d9a 型证据）。不可读作"池有害"，与来源×命中表（analog-only 66.7%）合并解读时更支持"池**留存下来时**是最强正向信号，问题在召回面与执行留存率"。

### 2.5 检索池现状（`s5b_builder.default_pool_provider`）

底物侧确定性相似检索：供体反应物与题面底物 Tanimoto ≥ 0.45、top-8、仅带映射模板；产物/反应侧检索不存在；空池走模型 novel（S3B-05 合法路径）。实收池深分布（298 题）：`{0:120, 1:92, 2:37, 3:26, 4:13, 5:7, 7:2, 8:1}`，**均值 1.18**，池深 ≥3 仅 43 题；**40.3% 空池**。模板来源（transformation_ref 前缀，留存假说侧）：env:EAWAG-BBD 42、EAWAG-SEDIMENT 6、EAWAG-SOIL 5、rhea:\* 若干。

---

## 3. 调优建议（三轴）

前置声明：本节全部为**建议**，属下一轮预注册流程，决定权在 teacher/用户；任何提示词内容变更自动升 `PROPOSALS_PROMPT_VERSION` 哈希并改变批身份（机制，非障碍）；判分口径与冻结判据零触碰。每条标注 **[工程]**（可进回修轮）或 **[口径级]**（须 teacher/用户裁定并走下一轮预注册）。优先级排序：轴 1-2 ≈ 轴 3-1 > 轴 2-1 > 轴 1-4 > 其余。

### 轴 1 提示词（`real_model._PROPOSALS_SYSTEM_PROMPT`，77–127 行区域）

1. **[工程] 芳香体系表示指令**（针对 to_aromatic 229 例 + 零假说 49 题）
   - 现状证据：词表已改 single|double|triple 后模型仍输出 `to_order=aromatic`（遵从度有限）；拒因 `bad_bond_order:*:to_aromatic` 与 `bond_order_mismatch:expected_aromatic_have_*` 合计占执行期失败大头。
   - 改法：提示词增加一句规则级指令"aromatic rings MUST be expressed via alternating single/double bonds in edits and product SMILES; the executor operates in Kekulé space"（不涉题面、不涉金标）。
   - 预期影响 bucket：零假说 49 → 部分回收（novel 留存率 70.2% → ↑）；间接改善 uncovered far 带。
   - 验证方法：下轮批后同口径拒因普查对比（880 样式的全量统计）+ 零假说题数。
   - 风险：提示词遵从度未知（本轮已见违规输出）；纯提示词方案天花板有限，建议与轴 3-1（执行器侧表示统一）**二选一或并行**——执行器侧是根修。
2. **[工程] 展开计划冲突消除**（针对 `expansion_status_conflict` 17 题整题报废）
   - 现状证据：17 题 run failed 零态；样本题模型已给出与金标同方向的正确化学，死于提交期计划校验（同一 state_ref 多个互斥状态）。触发形态推断为"同一分子以主产物+共产物（或重复）双写"。
   - 改法（优先工程侧，不依赖模型依从）：提交侧对重复 `state_ref` 的计划条目做确定性合并（取语义最强：expanded > deferred > not_tracked），或提案解析侧对同事件内重复分子去重；提示词侧可加一条"products and coproducts within one event must not repeat the same molecule"。
   - 预期影响 bucket：failed 22 中的 17 → 直接回收为可评测态（样本证据示至少 1 题含正确提案）。
   - 验证方法：17 qid 用其已存调用账本响应离线重放（零模型、零新调用），验证合并后走完公共链；新批分桶对比。
   - 风险：合并/去重语义须与 R2-09 契约一致性核对——若属契约内解释可走回修轮，若判定为新规则需 mimo 判据评审（AGENTS 三触发点之 1）后进预注册；先做根因探针钉死重复形态再动手。
3. **[工程] 断键/氧化深度自查字段**（针对 mid 带 23 题：氧化深度跳档、断键位置、对称位点选择）
   - 现状证据：§2.3 样本三类（RXNG_eb864c39 / RXNG_d6da5d9a / RXNG_e0bca299）。
   - 改法：要求每条 novel 提案附带结构化自查（断/成键原子对 + 反应中心氧化态变化），显式填入 `reaction_spec`（规则级，不新增题面信息）。
   - 预期影响 bucket：uncovered mid 带（23 题）与部分 far 带官能团错位题。
   - 验证方法：mid 带题集下轮同口径对比；抽查自查字段与 edits 一致性。
   - 风险：输出更长 → 费用上升（现均 17.4K output tok/调用）；自查字段可能流于形式，需抽查。
4. **[口径级] 共产物策略对齐**（针对 partial 15 题，全部主产物精确、败于多写共产物）
   - 现状证据：RXNG_66271eac 样本——脱磺化主产物精确，多写无机酸类共产物 → 参与物覆盖超集 → 不计严格。
   - 改法 A（提示词，[工程]）："only declare coproducts required by the transformation you are asserting; omit incidental inorganic leaving groups unless central"；
   - 改法 B（判分/参考图语义，[口径级]）：参与物覆盖比较对小分子无机共产物设忽略档——**改变主口径严格性，必须 teacher 裁定 + 预注册**，且涉及"参考边是否声明共产物"的金标口径问题（mimo 三触发点之 1）。
   - 建议顺序：先 A 观察一拍；B 不与本轮其他改动混轮（避免多因子归因）。
   - 风险：A 可能压掉真实共产物（低估化学）；B 放宽主口径须防"以放宽换通过"。
5. **[工程] 词表同源纪律**（aromatic 事故的通用化）
   - 现状证据：57ea99b 已加词表双锚测试（提示词词表 ↔ 执行器常量）。
   - 改法：把双锚扩展到提示词内**全部**受控词表（op / order / side / status / output_origin 等），从执行器常量单一来源生成或 CI 双向断言。
   - 验证：CI 常驻；预期影响：防再犯，无直接分数影响。

### 轴 2 检索池（`s5b_builder.default_pool_provider`：阈值 0.45 / max_pool 8 / pool-mode template）

1. **[工程] 阈值/池深参数扫描**（最高杠杆）
   - 现状证据：实收均值 1.18、40.3% 空池、池深 ≥3 仅 43 题；而 analog-only 命中率 66.7% 显著高于 novel-only 35.3%——池是最强正向信号但供给太浅。
   - 改法：阈值降至 0.35–0.40，或动态降档（不足 3 条时降阈值补齐）；max_pool 维持 8（上限不动，防噪声）。
   - 预期影响 bucket：空池 120 题 ↑ 覆盖；含 analog 假说题数 56 → 100+；主口径 hit 与 partial 均可能上移。
   - 验证方法：**离线零模型重放检索面**（只读资产，统计池深/模板来源分布）→ 新批"来源 × 命中"表对比。
   - 风险：低相似模板引入错误断键先验（RXNG_d6da5d9a 型误导，§2.4 负向关联的另一种解释）；须与轴 1-3 自查或轴 3-2 适用性门配套，不能单变量放阈值。
2. **[工程] 空池显式声明**
   - 现状证据：空池时 `pool_hypotheses` 为空列表，模型无从区分"无类比可循"与异常。
   - 改法：user payload 增 `pool_empty: true` 标志位（或等义文案），提示模型此题须走 novel 化学。
   - 预期影响：空池 120 题（现 35 中 / far 带为主）novel 提案方向性。
   - 验证：空池题 far 带占比变化。
   - 风险：低。
3. **[工程] 调用层有界重试**
   - 现状证据：4 题调用层错误（3×429 耗尽 + 1 空响应）无题级重试，按空跑计 0 分（4/298 ≈ 1.3 个百分点）。
   - 改法：gate 冷却后题级单次重试（与既有"失败同任务自动重试 1 次"纪律同构）。
   - 风险：费用微增（≤1.3% 题量的重复调用）。
4. **[口径级+资产级] 检索面扩展**（产物侧/反应侧检索）
   - 现状证据：仅底物侧 Tanimoto 单通道；novel-only 170 题 far 带占多是"无类比可循时方向未中"。
   - 改法：引入产物侧或反应类型级指纹检索需新资产/新语料授权（如 EAWAG 规则类目），且批内同卷跨题复用有泄漏风险——**语料可用范围须 teacher 裁定**后走预注册。
   - 验证：新批来源 × 命中表 + 泄漏审计。
   - 风险：工程量大；泄漏红线敏感。

### 轴 3 类比模板（`services/donor_applicability.py` + alignment 链 + `_template_to_spec`）

1. **[工程] 芳香/凯库勒空间统一（与轴 1-1 二选一或并行的根修）**
   - 现状证据：`donor_applicability` 对齐在芳香形式（aromatic≡aromatic 视为一致，混合记失配），而 `execute_edits` 在凯库勒空间施加；两套表示在模板派生 spec（`_template_to_spec._bond_diff_edits`）处相遇——`bond_order_mismatch:expected_aromatic_have_*` 258 例集中于此（模板提案留存率 27.8% 远低于 novel 70.2% 的直接嫌疑）。
   - 改法：核查 `execute_edits` 的"SINGLE 占位 + sanitize 重感知"机制为何未覆盖该路径（`production.execute_atomtool_expansion` 直调路径是否绕过预校验/芳香感知），在施加前对当前分子统一表示空间；或模板 edits 生成侧输出凯库勒显式键。
   - 验证方法：对 258 例 `bond_order_mismatch` 样本**离线零模型重放**（同响应重放公共链，57ea99b 已有先例配方）→ 接受率对比；全仓回归。
   - 预期影响 bucket：模板留存率与含 analog 假说题数双升（56 → ↑），经 §2.4 的 66.7% 命中率传导至主口径。
   - 风险：触及身份计算空间（结构身份/CN 同值口径），属判据级敏感面——**mimo 判据评审（触发点 1）后再进预注册**；保留合法正控、防过拒（AGENTS 返工 §7）。
2. **[工程] 模板适用性门与误导普查**
   - 现状证据：analog-only uncovered 7 题 + mixed uncovered 21 题——模板留存但导向错误断键（RXNG_d6da5d9a：断错侧）。
   - 改法：先做本批 `DONOR_FALLBACK_*` 五类 fallback 原因分布聚合（本轮未聚合，列为下轮前置探针）；再评估是否收紧 `COMPETING_TRANSFORMS` / 键级上下文失配门槛。
   - 验证：analog 假说题命中/误导率对比；正控保留清单。
   - 风险：过拒丢正控（池本来供给就浅）。
3. **[工程] alignment 质量抽检探针**
   - 现状证据：本批未做 `donor_to_current` 对齐错误归因，仅能从断键错位间接推断；`alignment.ref` 见 `self-declared`（模型自声明）案例。
   - 改法：对 56 个含 analog 假问题抽 10 个，人工核对对齐映射 vs 模板 lhs（零金标要求下可与模板 lhs 自身对照；抽样数注明）。
   - 产出：对齐错误率基线，决定是否值得做对齐校验加强。
4. **[口径级] 参考图共产物声明语义**（与轴 1-4B 同一裁定点）
   - 现状证据：partial 15 题全部主产物精确；若金标参考边不声明无机共产物而模型如实写出，则"超集不中"语义会系统性惩罚真实化学。
   - 改法：teacher 裁定参考图共产物口径（声明完整性 vs 判分忽略档），随下一轮预注册落字；出题侧（考卷化学抽审）与判分侧须同源。

---

## 附录 A：数据来源与取证方法（全只读）

- 官方终判分与硬门：远端 chain8 日志（`/tmp/s5b_chain8.log`：`CHAIN8_SCORE_EXIT=0`、`CHAIN8_BASIS_OK graphs=298`、`CHAIN8_SCORED 10:24:16`）+ 批根 `metrics.json`（chain8 score 命令输出）。
- 批根 `s5b_298_20261009_batch2`：`batch_manifest.json`（含题卷 SHA）、`batch_report.json`（冒烟/全量两份）、`gate/gate.json`、`price_snapshot.json`、`preregistration_approval.json`、`progress.json`、`cases/*.json`（298）、`run_inputs/*.json`（298）、`runs/*/`（native_export payload、results/*/expansion_outcome.json、s5b_real_calls.jsonl 逐调用账本）。
- 聚合分析：本地起草、远端只读 Python 执行（base64 传脚本、零远端落盘、零写操作、零模型调用、不触碰金标仓外副本判分进程之外的任何写路径）；接近度分带在分析进程内比对金标（仅比对用，产物不入文）。脚本留存本地 `/tmp/s5b_review/`（agg_calls / agg_pools / agg_rej / deep_dive / join_analysis / proximity）。
- 源码核实：`src/pathway_v43/pollutant/s5b_scoring.py`（分桶/口径语义）、`evaluation.py`（match_reference_edges / S5A-03）、`real_model.py`（提示词+版本哈希）、`s5b_builder.py`（default_pool_provider/_template_to_spec）、`services/donor_applicability.py`（芳香空间对齐/fallback 常量）、`store.py`（_check_expansion_plan）。

## 附录 B：金标泄露扫描

- 方法：对本文抽取全部类 SMILES token（正则覆盖 `>>` 反应式与含键符/括号的紧凑分子串），与 `/Volumes/CC/Enzyme_Agent/ec298_phase_a_seal/ec298_gold_readonly/questions.jsonl` 的 `products_smiles` / `substrate_smiles` 全集（298 题、去重 392 条及全部多组分拆分）做三通道比对：精确相等、RDKit 规范化相等、金标组分（≥8 字符）作为子串出现在文中。
- 结果：**三通道命中均 0**（文中抽取候选 token 6 个，全部为代码/文档标识符，无一为金标串或其规范化形）。本文示意用合成小分子 CCO→CC=O 经查非金标组分；qid 前缀、计数、模式名、命中率不构成金标内容。
- 扫描执行记录：成稿后本地只读执行（脚本 `leak_scan.py` 与输出留存 `/tmp/s5b_review/leak_scan/`）。

## 附录 C：未核项与诚实披露

1. batch1 作废段 ~15 调用未单独计价（作废披露口径）。
2. `expansion_status_conflict` 重复形态根因未钉死（已定位校验点与影响面 17 题；需一离线探针，见轴 1-2）。
3. output token 与响应正文差额归因"reasoning token 计费"为推断（有耗时旁证，未取得 provider 侧字段级确认）。
4. `DONOR_FALLBACK_*` 分布与 alignment 错误率未聚合/未抽检（本轮证据缺口，轴 3-2/3-3 前置探针）。
5. 池深与命中的负向关联为观测关联，因果未证（§2.4 两种解释并存）。
6. mimo 结果化学复核（AGENTS 三触发点之 3）未在本文内执行；本文为程序证据侧审核，建议随下一轮判据冻结/预注册一并送审。
