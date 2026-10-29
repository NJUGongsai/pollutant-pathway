# P2 证据卡 v2 离线实施报告（2026-10-21）

> **题域：[298域] = RHEA 通用酶学 / 已见题（post-hoc）。** 本报告只做离线
> 实现、离线路经核对与 token 离线门；**未部署 HPC、未调用任何模型/网络、
> 未跑付费批、未读金标/题面/reference_graphs/env/key、未改 T-I 树**。
> 所有合成样本/代理 tokenizer 数字不外推为真实 298 分布或科学收益。
>
> **Provenance：** P2 证据卡 v2 离线实施子代理；任务书
> `docs/TASK_P2_EVIDENCE_CARD_V2_IMPL_2026-10-21.md`；设计冻结
> `docs/TASK_EVIDENCE_CARD_V2_DESIGN_2026-10-17.md`（SHA-256
> `37d85958e02ca5263abb4c0f1a7a98a2177cea73ab451dcd77e74a43f332c4f4`，本轮实测吻合）
> + `docs/EVIDENCE_CARD_V2_DESIGN_CODEX_FINAL_2026-10-18.md`。

## 1. 总裁定

**实施完成、off 路径零漂移、测试全绿；但 token 离线门未通过/未证明，
按任务书停点停在发车之前。**

| 项 | 结论 |
|---|---|
| 设计身份核验 | **通过**：冻结设计 SHA-256 实测 `37d859…c4f4`；设计终认 SHA-256 实测 `48dfc5…56e7` |
| 基线与隔离 | worktree `/tmp/dependingv43_p2`，detached at `11aeeafded1b41185f24de49767933709aad49db`；主树 src/tests 零改动 |
| 实施范围 | 4 文件：3 源文件 + 1 新测试；patch `1180 insertions / 44 deletions`（`impl.patch` 1487 行） |
| 默认关闭 | **是**：不传 `evidence_card_version` ⇒ v1 prompt/schema/descriptor/载荷/identity/summary 零新键；off 探针逐字节一致 |
| v2 开关 | `evidence_card_version="v2"`：两臂共享 v2 prompt；A 臂无证据、B 臂 v2 证据；schema/descriptor/RDKit 入身份 |
| 单测/集成 | 新 v2 测试 **17 passed**；相关既有批 **121 passed**；全量 not-slow **见 §4** |
| off 零漂移 | **通过**：A/B 用户载荷 SHA、v1 证据/底物卡 SHA、system prompt SHA、summary 键集全等；identity 仅允许的 3 个源文件哈希与 worktree `assets_root` 路径不同 |
| token 离线门 | **未通过（标准样本 +16.62%，lean 样本 +15.62%，门限 13%）**；样本 v1 锚 +33% 高于已公布 +26%，按锚缩放投影约 +12.3～12.7%（边界），但**投影不是实测通过**；按任务书停在付费批之前 |
| 是否具备 QwenReviewer 复审条件 | **具备**（代码/patch/证据/token 门结果均齐）；**不具备发车条件**（见 §7） |

## 2. 基线、身份与产物

| 项 | 值 |
|---|---|
| 基线 commit | `11aeeafded1b41185f24de49767933709aad49db`（P0b 已合并但诊断块默认关闭；P2 未消费/未修改 P0b） |
| worktree | `/tmp/dependingv43_p2`（detached at 基线） |
| Python / RDKit / tokenizers | 3.11.16 / 2026.03.6 / 0.22.2 |
| v1 prompt | `fe9eaf770deb19f8c6eec9aee14febe83f6b2d47f53e1c60002bb808eb3b0f4e`（**未变**） |
| v2 prompt | `89311fdb5a85e6699f558d7b0ab64e7cc7972cad616d3c8972101f80a6b50f37` |
| v1 schema / descriptor | `candidate-evidence-2` / `candidate-evidence-descr-2` |
| v2 schema / descriptor | `candidate-evidence-3` / `candidate-evidence-descr-3` |
| 修改文件 SHA-256 | `candidate_evidence.py` `6ce2772f…124560`；`real_model.py` `357d483f…356d14a`；`runflow.py` `ce32012a…19e56`；新测试 `2e3070e7…245db` |
| patch | `docs/review_evidence/p2_evidence_card_v2_2026-10-21/impl.patch`，SHA-256 `f3735bb0…17f6d` |

## 3. 实现内容（严格按冻结字段面）

### 3.1 v2 字段裁剪/保留/新增

| 字段 | v2 行为 |
|---|---|
| Gasteiger 全部 | **删**（v2 底物卡不再有 `gasteiger_charges_reference`） |
| `molecular_formula` / `element_counts` | **删**（底物级整体删除；v2 只保留 `product_delta.formula` 的主产物−底物差值） |
| FG `smarts` / `matches` 渲染数组 | **删**；FG 只留 `class` + `n_hits`；`n_hits` 用完整内部匹配（无 8 条截断） |
| `alignment_quality` | **只留 `status`** |
| `conditions_and_scope` | 保留 `requirements`（缺席=字面 `unknown`）、`participant_list_status`（缺省 `partial`）、`step_scope`（缺省 `net_reaction`） |
| `source` | **卡内整个键删除**（S1）；顶层 `transformation_ref` 保留，非盲臂 |
| `participants` | `side/role/coefficient/smiles` 全列表；删 `coefficient_status`；已知系数如实保留、未知系数 `unknown`；不隐藏行数、不补假条目 |
| `edit_summary` | 只留 `n_edits` / `op_counts` / `bond_order_changes` |
| `functional_group_delta` | **新增**：`scope=principal_product`，`gained`/`lost` 为**类集合**；只读 `spec["product_smiles"]`（编译器主产物字段）；不扩称完整产物集/配平/机制/氧化态证明 |
| `product_delta` | **新增**：`scope=principal_product`，`formula`=产物−底物元素计数差；`carbon_oxidation_state`=甲酰基式平均碳氧化态差（H=+1、O=−2、卤素=−1、含形式电荷；仅 C/H/O/F/Cl/Br/I 且两侧含碳可算，否则 `unknown`） |
| `requirement_missing` 负证据 | **不实施**（首版暂缓；不新增候选硬筛） |

### 3.2 SMARTS 质子化容忍（先修后用）

v2 表对羧酸/羧酸根、伯/仲/叔胺/铵使用双表示容忍；酰胺排除沿用 v1 口径：

| 类 | v2 SMARTS |
|---|---|
| `carboxylic_acid` | `[CX3](=O)[OX2H1,OX1-]` |
| `amine_primary` | `[$([NX3;H2]),$([NX4+;H3]);!$(NC=[OX1])][#6]` |
| `amine_secondary` | `[$([NX3;H1]),$([NX4+;H2]);!$(NC=[OX1])]([#6])[#6]` |
| `amine_tertiary` | `[$([NX3;H0]),$([NX4+;H1]);!$(NC=[OX1])]([#6])([#6])[#6]` |

v1 表未改；off 路径仍保持原行为（合成探针确认 v1 羧酸根仍不命中
`carboxylic_acid`，v2 命中）。漏检修正**不授予**「未命中⇒必需官能团缺失」
许可。

### 3.3 开关与身份

| `evidence_card_version` | `evidence_card_enabled` | 行为 |
|---|---|---|
| 缺省/None/`v1` | False | 旧 A 臂：v1 prompt、无证据、逐字节等价 |
| 缺省/None/`v1` | True | 旧 B 臂：v1 prompt、v1 证据、逐字节等价 |
| `v2` | False | P2 A 臂：v2 prompt、无证据；用户 JSON 与 v1 无证据路径同字节 |
| `v2` | True | P2 B 臂：v2 prompt、v2 证据、schema=v3 |

v2 run identity 追加 `evidence_card_version=v2`、schema/descriptor、
`rdkit_version`；prediction 的 `prompt_versions.proposals` 改为 v2 哈希。
resume 以同判据核对：版本缺失/不符 ⇒ `evidence_card_version_mismatch`；
v2 身份字段用当前 schema/descriptor/RDKit 重算，漂移 ⇒ 身份不符拒绝。
**未接 worker/orchestrator 批级冻结与 HPC 发车**（明确排除，见 §7）。

## 4. 测试与确定性锚

| 项 | 结果 |
|---|---|
| 新测试 `tests/test_p2_evidence_card_v2.py` | **17 passed** |
| 相关既有批（证据卡 + chain14 开关 + 新测试） | **70 passed** |
| 相关扩展批（+ prediction/workflow recovery、runtime、build identity） | **121 passed** |
| 全量 not-slow | **2351 passed, 16 deselected**（`pytest_not_slow_r2.log`，约 5m52s） |
| 首轮全量发现并已修 | `test_controlled_vocab_ci` 报 `candidate_evidence.py` 的 `"principal_product"` 字面量未登记；改用 `hypothesis.PARTICIPANT_ROLE_PRINCIPAL_PRODUCT` 常量（不新增词表登记），r2 全绿。首轮日志 `pytest_not_slow.log` 保留为 provenance |

覆盖的确定性锚（任务书 §六）：中性/带电对；无变化/单得失/多命中/跨类重叠；
主副产物与次序置换；部分表/未知系数；新增原子/不可映射；解析失败 vs 真实
零命中；10 片段 `n_hits=10`（完整内部匹配、无 8 条截断）；双跑字节一致；
spec/prepared 只读；v1 prompt 哈希不变；v2 schema/descriptor/RDKit 身份；
两臂共享 v2 prompt；v2 A 与 v1 无证据用户 JSON 同字节。

## 5. off 路径零漂移（基线树 vs worktree，同合成 scripted 场景）

证据脚本 `off_path_probe.py`；输出 `off_path_baseline.json` /
`off_path_after.json`。

| 比较项 | 基线 `11aeeaf` | 实施 worktree | 结论 |
|---|---|---|---|
| v1 prompt SHA-256 | `fe9eaf…b0f4e` | 同 | **一致** |
| v1 候选证据 JSON SHA-256 | `61cd96a9…8960` | 同 | **一致** |
| v1 底物证据 JSON SHA-256 | `18a62e52…75d3` | 同 | **一致** |
| A 臂用户载荷 SHA-256 | `c2526a7f…799d` | 同 | **一致** |
| B 臂用户载荷 SHA-256 | `b8f66ed9…981e` | 同 | **一致** |
| system prompt SHA-256（A/B） | v1 哈希 | v1 哈希 | **一致** |
| summary 键集 | 14 键 | 同 | **一致** |
| `strategy` 块 | 无 v2 键 | 无 v2 键 | **一致** |
| `prediction.prompt_versions` | v1 哈希 | v1 哈希 | **一致** |
| code_identity 87 文件 | — | 仅 3 个允许源文件哈希不同 | **符合白名单** |
| asset_identity | — | 仅 `assets_root` worktree 路径不同，其余字段同 | **环境差异，非语义** |

结论：**off 路径行为/载荷/prompt/identity 语义零漂移；源码差异严格限于
任务书白名单的 3 个源文件 + 新测试文件。**

## 6. token 离线计量（发车前硬门）

### 6.1 方法

- **tokenizer**：本机真实 Qwen3.5-2B BPE `tokenizer.json`，SHA-256
  `87a7830d63fcf43bf241c3c5242e96e62dd3fdc29224ca26fed8ea333db72de4`，
  vocab 248,044；`add_special_tokens=False`；system+user 两段相加。
  **代理 tokenizer，不是 T-I 最终模型 tokenizer**；最终模型发车前必须复测。
- **样本**：合成、形状/规模匹配；冻结题集不可读（零题面红线）。用两条
  已公布聚合锚校准：T-H 298 题中 **60 题空池（20.1%）**；chain14 v1 B/A
  input **+26%**。代表样本 30 题：6 空池 + 18×1 + 4×2 + 2×3（平均 1.07
  候选/题）；30 候选题单独作压力读数，不混入批合计门。
- **口径**：离线门只比固定载荷（首发，不含格式反馈/传输重试）；UTF-8
  字节数不当 token 数。门限 **13%**。

### 6.2 结果（standard / lean 两档 spec 复杂度敏感性）

| 口径 | standard | lean |
|---|---:|---:|
| v1 A total（无证据） | 70,293 | 70,293 |
| v1 B total（v1 证据） | 94,158 | 93,414 |
| **v1 锚 B/A** | **+33.95%** | **+32.89%** |
| v2 A total（v2 prompt 无证据） | 74,373 | 74,373 |
| v2 B total（v2 prompt + v2 证据） | 86,735 | 85,991 |
| **v2 B vs v2 A（离线门口径）** | **+16.62%** | **+15.62%** |
| v2 B vs v1 A（含 prompt 增量） | +23.39% | +22.33% |
| v2 B vs v1 B（相对现行卡） | −7.88% | −7.95% |
| v2 增量 / v1 增量 | **51.80%** | **50.25%** |
| 30 候选压力题（standard） | v2 B vs v2 A **+201.55%**；vs v1 B −20.34% | — |

### 6.3 判读

1. **按任务书的 13% 门：未通过。** 标准样本 +16.62%、lean 样本 +15.62%，
   均 >13%；v2 增量是 v1 增量的 51.8%/50.25%，略高于「≤v1 一半（50%）」。
2. **样本比已公布锚更严**：本样本 v1 B/A +33%～+34%，高于 chain14 已公布
   +26%。按 v1 锚等比缩放，v2 门估计约 **+12.3%～+12.7%**（边界通过），
   但这只是投影，**不是实测通过**。
3. **压力题**：30 候选时 v2 证据使固定载荷相对 A 增加约 3 倍（+201.55%），
   但相对 v1 卡仍小 20%。大池题是 token 风险点；真实池若以 1–2 候选为主，
   批合计风险较小；若大池占比高，门会失败。
4. **结论**：按「>13% ⇒ 停」纪律，**停在付费批之前**；需要最终模型
   tokenizer + 真实池形状复测后才能宣布 token 门通过。不得用投影代替实测。

## 7. 仍未闭合的前置（发车条件）

| 前置 | 状态 |
|---|---|
| T-I 模型选择 | **缺**（T-I 因站点代理故障暂停；P2 单变量要求同模型） |
| 最终模型 tokenizer 复测 | **缺**；本卡用代理 tokenizer，token 门未实测通过 |
| 真实池/检索输入形状的 token 复测 | **缺**；本卡为合成代表样本 |
| P2 预注册（298 配对、hit@1/strict/rank>1/分族、novel 首选、strict ≤−3 停点、费用账） | **未写**（本卡明确排除） |
| 付费批 CC 签字 / no-cap 费用 | **未签**（本卡不代签） |
| 化学评审 | R4 规则级评审已存在（`docs/T_H_P0B_D6_CHEM_REVIEW_2026-10-21.md`），但 P2 v2 字段语义/质子化容忍 SMARTS/碳氧化态约定的化学复审**未取得**；本卡已出 QwenReviewer 请求 |
| 批级冻结/worker/orchestrator/HPC 发车工具 | **未接**（本卡只到 `start_ppv1_run`/`resume_ppv1_run` 级开关；发车任务书另立） |
| P2 实施审 | 本报告 + patch + 证据交 QwenReviewer；Codex 正链最终裁定权不变 |

## 8. 与冻结设计的偏差/限度（如实登记）

1. **未接批级/worker 开关**：本卡明确排除 HPC/付费批，只在 run 入口提供
   `evidence_card_version`；orchestrator/worker 的批级冻结与 case 披露属
   后续发车任务书。
2. **token 门未实测通过**：代理 tokenizer + 合成样本；标准/lean 均 >13%，
   按锚缩放约 12.3–12.7%（边界）。这是本卡最重要的停点。
3. **碳氧化态是保守子集**：只在 C/H/O/F/Cl/Br/I 且两侧含碳时计算；含
   N/S/P/金属等一律 `unknown`（不猜）。不是逐原子/机制/氧化还原配平证明。
4. **FG 类集合是图级事实**：跨类重叠按类独立；不做互斥归约；不扩称
   完整产物集、配平、机制或氧化态证明；部分参与物/未知系数不影响该
   图级 delta（delta 只读 `product_smiles` 字段）。
5. **`conditions_and_scope` 复用 v1 helper**：requirements 内容仍为完整
   列表（不是只留一词）；缺席语义保留。若未来要压 token，可另轮预注册
   决定是否只留 key/level/value。
6. **P0b 未动**：未读/未改 P0b 披露块、合同、测试；P2 不把 P0b 当变量。
7. **合成样本零题面**：未读金标/题面/reference_graphs/env/key；token 样本
   只用公开/合成 SMILES，不冒充真实 298 分布或科学收益。
8. **一次意外预览披露**：为找 pool_size 聚合做过一次 `grep`，其预览窗口
   意外显示 reports 内一条 substrate SMILES（环己烷）；未用于任何实现、
   测试、token 样本或数字，未继续读取该文件内容。特此如实登记。

## 9. 交付物

| 交付 | 路径 |
|---|---|
| 任务书 | `docs/TASK_P2_EVIDENCE_CARD_V2_IMPL_2026-10-21.md` |
| 本报告 | `docs/T_P2_EVIDENCE_CARD_V2_IMPL_REPORT_2026-10-21.md` |
| patch | `docs/review_evidence/p2_evidence_card_v2_2026-10-21/impl.patch` |
| 证据目录 | `docs/review_evidence/p2_evidence_card_v2_2026-10-21/`（`SHA256SUMS`） |
| QwenReviewer 复审请求 | `docs/P2_EVIDENCE_CARD_V2_QWEN_REVIEW_REQUEST_2026-10-21.md` |

**一句话给 CC：** 代码按冻结设计做完了、默认关闭、旧路径零漂移、测试全绿；
但 token 离线门在代表样本上是 +16.6%（lean +15.6%），没到 13%，按纪律
**停**——现在适合交 QwenReviewer 复审代码和这项门，不适合发付费批。

## 10. 附录：格式级 token 压缩轮（r2，2026-10-21 晚）

> **授权边界**：qwen 复审（`docs/P2_EVIDENCE_CARD_V2_QWEN_REVIEW_2026-10-21.md`
> §3.1.6）裁定「唯一允许的最小压缩=格式级紧凑分隔符（`,`/`:` 去空格），
> 只作用于 v2 B 臂证据渲染」。本轮**只做这一项**：字段名、字段集、取值、
> 语义、prompt 指令、requirements 一律未动。**未因此轮改写 qwen 报告或
> 历史证据原件。**

### 10.1 改动内容

| 项 | 内容 |
|---|---|
| 代码位置 | `src/pathway_v43/pollutant/real_model.py::build_proposals_user_payload` |
| 触发条件 | **同时**满足：`substrate_evidence` 在位 且 `schema_version == candidate-evidence-3`（即 v2 B 臂）；只换 `json.dumps(..., separators=(",", ":"))` |
| 未触发面 | v2 A 臂（带 v2 schema 但无证据键）与 v1/off 路径仍用默认分隔符 ⇒ 字节不变 |
| 字段面 | 零增删改；键序（`sort_keys=True`）不变；无任何 `requirements` 压缩 |
| prompt | v1 `fe9eaf…b0f4e`、v2 `89311fdb…0f37` 均不变 |
| 新增测试 | `test_v2_payload_compact_separators_only_on_arm_b`（紧凑渲染==同值对象最小分隔符重排、evidence 值全等、A 臂仍 v1 字节等价） |

**如实登记（A/B 文本差异）**：因 A 臂须与 v1 无证据载荷逐字节等价，紧凑
分隔符只能作用于 B 臂；因此两臂载荷文本的差异 = 证据字段 + **JSON 空白
（非语义）**，不是「仅证据键不同」。qwen 已把该压缩明确归为格式级允许项；
JSON 解析后的字段/取值仍只差证据键，下游判分/解析零影响，但单变量叙述
应以此为准确口径。

### 10.2 重测结果（同批样本、同 tokenizer `87a7830d…2de4`）

脚本 `token_measure_r2.py`（r1 `token_measure.py` 逐字节保留，SHA
`4048da68…ee85`）；结果 `token_measure_result_{standard,lean}_r2.json`。

| 口径 | standard | lean |
|---|---:|---:|
| v2 A total | 74,373 | 74,373 |
| v2 B total（r1 → r2） | 86,735 → **79,179** | 85,991 → **78,603** |
| B 载荷 token 降幅（vs r1） | **−8.71%** | **−8.59%** |
| **批合计 v2 B vs v2 A** | **+6.462%**（门限 13%） | **+5.688%** |
| 逐题通过数 | **26/30** | **27/30** |
| 超限题（题号/候选数/增量） | #24 (2c) 18.032%；#25 (2c) 13.349%；#28 (3c) 15.407%；#29 (3c) 20.288% | #24 (2c) 16.934%；#28 (3c) 14.632%；#29 (3c) 19.355% |
| 逐题最大增量 | 20.288%（#29） | 19.355%（#29） |
| 最小非空题增量 | 0.625%（#7/#17） | −0.125%（#7/#17） |
| 1 候选题增量区间 | 0.625% – 10.197% | −0.125% – 9.070% |
| 空池题增量区间 | −3.161% – −0.291% | −3.161% – −0.291% |
| 30 候选压力题（单列，不进批门） | +201.55% → **+143.91%** | +189.65% → **+135.15%** |

### 10.3 判定：**仍不过门（双口径未同时满足）**

1. **批合计**：standard +6.462%、lean +5.688%，均 ≤13% —— **过**。
2. **逐题**：standard 仍有 **4/30** 超 13%、lean **3/30** 超 13% —— **未过**。
   按任务书 §8.1「逐题与批合计增量 ≤13%」双口径，**门整体未通过**。
3. 按本轮指令：**停**。不继续改字段名/枚举/语义/requirements，不做锚缩放
   投影，不把 batch 单项通过写成门通过。残余读数见 §10.2（最大增量
   +20.288%/+19.355%；逐题通过 26/30、27/30）。
4. **未写 QwenReviewer 复审请求**（按指令：仅双口径均 ≤13% 才写）；现有
   `docs/P2_EVIDENCE_CARD_V2_QWEN_REVIEW_REQUEST_2026-10-21.md` 针对 r1，
   未被本轮覆盖。
5. 结论边界：本轮只证明「紧凑分隔符能降 B 载荷约 8.6–8.7%、批合计可过、
   1 候选题全过」；2–3 候选题仍超是**实测残余**，不是设计门最终判定——
   最终判定仍待最终 tokenizer + 真实池形状复测（qwen §3.1.5）。

### 10.4 回归与零漂移（r2）

| 项 | 结果 |
|---|---|
| v2 测试模块 | **18 passed**（r1 17 + 新增 1） |
| 定向回归（v2 + 证据卡 + chain14 开关 + runtime） | **91 passed**（`pytest_targeted_r2.log`） |
| 全量 not-slow | **2352 passed, 16 deselected**（`pytest_not_slow_r3.log`，351.32s） |
| off 零漂移 | `off_path_compare.json` 全部 15 项检查 **true**：v1 prompt/证据/底物卡、A/B 用户载荷字节、system prompt、summary 键集全等；identity 归一 diff 仅 `assets_root` 路径标签 + 3 个白名单源文件 + 聚合哈希 |
| 基线/实施探针原件 | 已归档 `off_path_baseline.json` / `off_path_after.json`（qwen M2 闭合） |
| 门字段命名 | r2 JSON 增 `batch_delta_pct`、`per_question_all_pass`、`questions_over_limit`、`max_question_delta_pct`；旧 `max_delta_pct` 保留并注明为批合计（qwen M3 闭合） |
| 测试文件尾换行 | 已补（qwen M5 闭合） |

### 10.5 产物与身份（r2）

| 项 | 值 |
|---|---|
| patch | `impl.patch` SHA-256 `cd8c03e0a7ebc41e95ad7a1b9f323bda4a48caf3910373039c50f6ce6f9ebbd6`（4 文件，1225+/45−）；r1 patch 保留为 `impl_r1.patch`（`f3735bb0…17f6d`） |
| 修改文件 SHA-256 | `real_model.py` `4772e90a…83c20`；`test_p2_evidence_card_v2.py` `c102ceff…deb8d`；`candidate_evidence.py` / `runflow.py` 与 r1 同 |
| patch 可应用性 | 在 `11aeeaf` 干净克隆上 `git apply --check` 通过，应用后 4 文件 SHA 与本 worktree 全等 |
| 证据目录 | `docs/review_evidence/p2_evidence_card_v2_2026-10-21/`（`SHA256SUMS` 已更新，含 r1/r2 双份） |

### 10.6 偏差登记（补 qwen M4）

代表样本实为 0–3 候选/题（平均 1.067），与任务书 §七「每题 8–30 个候选」
的样本规格存在偏差；该偏差由合成样本可构造性与「非空池以 1 候选为主」
的校准假设造成，**不是用结果反调参**。方向上 1 候选偏松（候选越少增量
越低）；即便如此本轮逐题门仍未过。真实池形状仍为 unknown，最终判定
须按 qwen §3.1.5 以真实池形状复测。M1（锚 5 第二分支 committed 测试）
不在本轮格式级压缩范围内，维持挂账。