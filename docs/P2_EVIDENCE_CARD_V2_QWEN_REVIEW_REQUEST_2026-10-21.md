# QwenReviewer 复审请求 — P2 证据卡 v2 离线实施（2026-10-21）

> **Provenance / 授权：** CC 2026-10-21 指示，P2 证据卡 v2 离线实施完成后
> 交 QwenReviewer 复审。本请求不是 Codex 正链裁定，不替代 Codex 最终裁定权；
> 复审结论采信到与源码/程序证据互证为止。R4 规则级化学评审
> （`docs/T_H_P0B_D6_CHEM_REVIEW_2026-10-21.md`）是另一条链，**不是化学终认**；
> 本请求不要求重开 R4，也不把 P0b 当 P2 变量。
>
> **题域：[298域] = RHEA 通用酶学 / 已见题（post-hoc）。** 本请求与所附证据
> 零金标、零题面、零真实候选结构、零参考图、零 key/env；只含合成 SMILES
> 与聚合 token 计数。**实施方披露：** 为找 pool_size 聚合做过一次 `grep`，
> 预览窗口意外显示过一条 reports 内的 substrate SMILES（环己烷）；未用于
> 任何实现/测试/token 样本/数字，未继续读取该文件。特此如实登记。
>
> **复审纪律：** 只读；可在全新临时目录 `git apply` patch 后跑测试/探针；
> 不访问金标/题面/`reference_graphs` 内容/封存逐题 run/`llm.env`/私钥；
> 不调用外部模型/网络；不跑 HPC/付费批；不 push；不改主树 src/tests。
> 证据目录：`docs/review_evidence/p2_evidence_card_v2_2026-10-21/`。

## 1. 复审对象与身份（请先实核）

| 项 | 值 |
|---|---|
| 冻结设计 | `docs/TASK_EVIDENCE_CARD_V2_DESIGN_2026-10-17.md`，SHA-256 `37d85958e02ca5263abb4c0f1a7a98a2177cea73ab451dcd77e74a43f332c4f4` |
| 设计终认 | `docs/EVIDENCE_CARD_V2_DESIGN_CODEX_FINAL_2026-10-18.md`，SHA-256 `48dfc59931c383e640c9753eb4998ec0b25c41648c79b9c489bf835f754f56e7` |
| P2 工作线要求 | `docs/T_H_HIT1_OPTIMIZATION_PLAN_2026-10-20.md` §4 P2 |
| 基线 commit | `11aeeafded1b41185f24de49767933709aad49db` |
| 实施 worktree | `/tmp/dependingv43_p2`（detached at 基线；未 push、未合并） |
| 任务书 | `docs/TASK_P2_EVIDENCE_CARD_V2_IMPL_2026-10-21.md` |
| 实施报告 | `docs/T_P2_EVIDENCE_CARD_V2_IMPL_REPORT_2026-10-21.md` |
| patch | `docs/review_evidence/p2_evidence_card_v2_2026-10-21/impl.patch`，SHA-256 `f3735bb07f24143150369db76d02fe2c45ff3958461d20ed4453758bfbd17f6d`；`1180 insertions / 44 deletions` |
| 修改面 | `src/pathway_v43/pollutant/candidate_evidence.py`、`real_model.py`、`runflow.py` + 新测试 `tests/test_p2_evidence_card_v2.py` |
| v1 prompt | `fe9eaf770deb19f8c6eec9aee14febe83f6b2d47f53e1c60002bb808eb3b0f4e`（未变） |
| v2 prompt | `89311fdb5a85e6699f558d7b0ab64e7cc7972cad616d3c8972101f80a6b50f37` |
| schema | `candidate-evidence-2` → `candidate-evidence-3` |
| descriptor | `candidate-evidence-descr-2` → `candidate-evidence-descr-3` |
| RDKit / Python | 2026.03.6 / 3.11.16 |

> **Addendum（2026-10-21，chemfix 后同步；不改写上方历史请求正文）：** 上表 v2 prompt
> `89311fdb5a85e6699f558d7b0ab64e7cc7972cad616d3c8972101f80a6b50f37` 是本次请求发出时的
> 历史值。chemfix（P1–P7 + N1/N2/N5）改了 v2 prompt 文本，现行 SHA-256 为
> **`c24bee42f651c783c9bdcee6e8f547bff63f1f5fee6a4a87f4816e4d15e57598`**
> （旧链：原始 `89311fdb…0f37` → E 轮 `e2aa2bbf61694c25f4607044f5f45a05c8e01c76dad8e26b1ecd71be7d953a5a`
> → 最终 `c24bee42…7598`）；v1 prompt 不变
> `fe9eaf770deb19f8c6eec9aee14febe83f6b2d47f53e1c60002bb808eb3b0f4e`。
> 本 addendum 只登记新身份，不重写历史请求正文、不改写历史结论。

## 2. 实施摘要（请对照冻结设计逐项核）

1. **S1 来源**：卡内 `source` 四件全删；顶层 `pool_hypotheses[i].transformation_ref`
   保留（非盲臂）；两臂共享 v2 prompt，仅证据字段不同。
2. **字段裁剪**：删 Gasteiger、`molecular_formula`、`element_counts`、FG 的
   `smarts`/`matches`；`alignment_quality` 只留 `status`；`edit_summary` 只留
   `n_edits`/`op_counts`/`bond_order_changes`；`participants` 删
   `coefficient_status`，保留 `side/role/coefficient/smiles` 全列表。
3. **新增**：`functional_group_delta`（`scope=principal_product`，
   `gained`/`lost` 类集合）与 `product_delta`（主产物−底物 formula 差 +
   甲酰基式平均碳氧化态差，保守元素域，否则 `unknown`）。
4. **SMARTS 质子化容忍**：羧酸/羧酸根、伯/仲/叔胺/铵双表示；酰胺排除沿用；
   v1 表未改。
5. **开关**：`evidence_card_version` 缺省/None/`v1` = 旧路径（零新键）；
   `v2` = 新 prompt/字段；resume 版本/身份核对，缺失/不符 fail-closed。
6. **off 路径**：不传 v2 时 v1 prompt/schema/descriptor/用户载荷/identity/
   summary 零漂移（见 §4）。
7. **未做**：worker/orchestrator 批级冻结、HPC 发车、付费批、P2 预注册、
   `requirement_missing` 负证据、候选硬筛、池/检索/排序/判分改动。

## 3. 请裁定（逐项 verdict + 证据；不要只给总评）

### Q1 字段裁剪是否忠实于冻结设计？

请逐项核：删/留/加是否与设计 §一表一致；是否偷偷保留或删除了真实事实；
`participants` 是否保真（已知系数不改成 unknown、不隐藏行数、不补假条目）；
`requirements` 缺席/unknown 语义与 `participant_list_status` 是否保留；
`source` 是否只删卡内、顶层引用保留；`edit_summary` 是否只留三项；
`alignment_quality` 是否只留 status。给出 **sound / clarify / blocking**。

### Q2 实现正确性与 off 路径零漂移是否成立？

请核：
- 不传 `evidence_card_version` 时 v1 路径是否真的零新键/零字节漂移
  （`off_path_probe.py` 的 A/B 载荷 SHA、v1 证据 SHA、system prompt SHA、
  summary 键集；identity 仅允许的 3 个源文件哈希与 `assets_root` 路径不同）；
- v2 A 臂用户 JSON 是否与 v1 无证据路径同字节；
- v2 两臂是否共用同一 v2 prompt（`seen_system_prompts` 断言）；
- v2 run identity 是否登记 schema/descriptor/RDKit，resume 是否 fail-closed；
- 是否存在隐藏的 v2 键泄漏到旧 summary/strategy/payload。
给出 **sound / clarify / blocking**。

### Q3 确定性锚是否覆盖冻结设计 §四.3？

请核新测试是否覆盖：中性/带电对；无变化/单得失/多命中/跨类重叠；
主副产物与次序置换；部分表/未知系数；新增原子/不可映射；解析失败 vs
真实零命中；完整内部匹配（10 片段 n_hits=10，无 8 条截断）；双跑字节
一致；输入只读；v1/v2 身份。缺哪项、是否 blocking。给出 **sound /
clarify / blocking**。

### Q4 化学语义（规则级）是否可接受？

只按规则级核，不要求真实结构：
- 质子化容忍 SMARTS 是否把羧酸根/铵正确归入同一官能团类，同时不误标酰胺；
- FG delta 的**类集合**语义（gained/lost，非命中数变化，跨类重叠独立）是否
  与「主产物 scope」自洽；是否夸大完整产物集/配平/机制/氧化态证明；
- 部分参与物/未知系数时仍给图级 delta 是否可接受（设计允许「限定图级差值
  或 unknown」）；
- `unknown` 是否只表示不可得，不被读成负证据/弃权理由。
给出 **sound / clarify / blocking**；如需措辞修正，请给最小改动。

### Q5 碳氧化态 delta 的定义与许可范围是否诚实？

本实现的定义：`C_ox = (q − H + 2O + X)/C`，约定 H=+1、O=−2、卤素=−1、
总形式电荷 q；只在两侧均含 C 且元素 ⊆ {C,H,O,F,Cl,Br,I} 时计算，否则
`unknown`；N/S/P/金属一律不猜；不是逐原子/机制/氧化还原配平证明。
请核该定义是否可辩护、是否应进一步收窄/放宽、提示词措辞是否足够。
给出 **sound / clarify / blocking**。

### Q6 token 离线门：本卡是「设计门失败」还是「样本校准伪失败」？

本卡实测（代理 Qwen3.5-2B tokenizer，system+user，标准/lean 两档）：
- v1 锚 B/A：**+33.95% / +32.89%**（已公布 chain14 锚为 +26%）；
- v2 B vs v2 A（离线门口径）：**+16.62% / +15.62%**，门限 13%；
- v2 增量 / v1 增量：**51.80% / 50.25%**，设计目标 ≤50%；
- 30 候选压力题：v2 B vs v2 A +201.55%，vs v1 B −20.34%；
- 按已公布 +26% 锚等比缩放投影：约 +12.3%～+12.7%（边界），但这不是实测。

请裁定：
(a) 样本校准方法（60/298 空池 + 1 候选为主 + 30 候选压力题分离）是否可辩护；
(b) 按任务书「>13% ⇒ 停」，本卡是否应判 **token 门未通过、停付费批**；
(c) 若判未通过，是否存在**设计内**的最小压缩（例如 requirements 行压缩、
participants 行格式）能在不删真实事实的前提下把增量压到 ≤13%，还是必须
由 CC 重开设计/调整 token 预算；
(d) 最终模型 tokenizer/真实池形状复测应作为发车前硬前置还是可豁免。
给出 **sound / clarify / blocking**，并明确「是否具备交 QwenReviewer
复审条件」与「是否具备发车条件」分开回答。

### Q7 剩余前置是否列全？

请核 §7 是否漏项：T-I 模型选择、最终 tokenizer、真实池形状 token 复测、
P2 预注册（298 配对/hit@1/strict/rank>1/分族/novel 首选/strict ≤−3 停点/
费用账）、付费批 CC 签字、化学评审、批级冻结/worker/orchestrator/HPC。
给出 **sound / clarify / blocking**。

## 4. 已附证据（可直接复核）

| 证据 | 路径/说明 |
|---|---|
| patch | `docs/review_evidence/p2_evidence_card_v2_2026-10-21/impl.patch` |
| 新测试日志 | `pytest_targeted.log`（70 passed：新 17 + 相关 53） |
| 全量 not-slow 日志 | `pytest_not_slow_r2.log`（以日志尾行为准） |
| off 路径探针 | `off_path_probe.py` + `off_path_baseline.json` / `off_path_after.json` |
| token 计量 | `token_measure.py` + `token_measure_result_standard.json` / `_lean.json` |
| 身份登记 | `identity.json` |
| 文件哈希 | `SHA256SUMS` |

**关键复核点：** `off_path_baseline.json` 与 `off_path_after.json` 的 A/B
用户载荷 SHA、v1 证据/底物卡 SHA、system prompt SHA 应全等；identity 的
`code_identity.files` 应只有 `candidate_evidence.py`、`real_model.py`、
`runflow.py` 三个哈希不同；token 结果应复现 §3 Q6 的数字。

## 5. 回复格式（请按此落盘）

1. **总裁定**：设计冻结是否仍成立；实施是否放行（附条件）；token 门
   通过/未通过/需复测；是否具备发车条件。
2. **Q1–Q7 逐项**：`sound / clarify / blocking` + 证据（源码行/测试名/数字）。
3. **必须修正项**：编号 + 最小范围（只列真正 blocking；措辞级另列）。
4. **非阻断澄清**：可随冻结文本落，不改行为。
5. **unknown / 本审核未覆盖**：明确列出。
6. **新问题分级**：P0/P1/P2；无则写无。
7. 建议落盘：`docs/P2_EVIDENCE_CARD_V2_QWEN_REVIEW_RESPONSE_2026-10-21.md`
   （由 CC 决定最终文件名/归宿）；回复原文保留 provenance，不改写。

**再次声明：** 本请求不授权付费批、不授权 HPC、不授权 push/合并、不授权
读取金标/题面/封存 run；QwenReviewer 结论不替代 Codex 正链最终裁定权。