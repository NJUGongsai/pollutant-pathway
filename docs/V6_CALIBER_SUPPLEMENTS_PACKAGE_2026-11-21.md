# `ppv1-criteria-v6` 口径与指标分工 · 8 项补件总包（2026-11-21）

> - **对应批复**：《给弓赛：降解路径分支判分口径与指标分工的批复》（`TEACHER_REPLY_GONGSAI_V6_CALIBER_2026-11-18(1).md`）§4（需要提交的 8 项补件清单）
> - **交付分支**：`v44`（同时推送至组织仓 `Water-Quality-Risk-Control-Engineering/depending` 与个人仓 `NJUGongsai/pollutant-pathway`；严禁触碰 `main` 与 `v4.3`）
> - **合规红线**：全程零 LLM 调用、零新增单步推理、零 SMILES 外泄、未接触两域 30% 单步留出集及其隔离令牌（留出集始终保持锁定）。
> - **术语声明**：本文及本分支报告中，所有 `Hit@k` 统一称作**「参考命中率」**，严禁称作「科学正确率」；在全量 6 基模去泄漏（de-leak）重测完成并复核前，**不作任何“本线优于旧六基模”结论**。

---

## 补件总索引（§4 清单 1–8 一览）

| # | 补件内容 | 仓内交付路径 | 验收状态 |
| :-: | :--- | :--- | :---: |
| **1** | v6 冻结登记 + 评分脚本 + 三份 SHA256 进仓 | [`docs/CRITERIA_V6_FREEZE_REGISTRATION_2026-11-13.md`](CRITERIA_V6_FREEZE_REGISTRATION_2026-11-13.md)<br>[`scripts/eval/score_disclosure_v4cn.py`](../scripts/eval/score_disclosure_v4cn.py)<br>[`src/pathway_v43/pollutant/evaluation.py`](../src/pathway_v43/pollutant/evaluation.py)<br>[`src/pathway_v43/pollutant/s5b_scoring.py`](../src/pathway_v43/pollutant/s5b_scoring.py) | ✅ 已入仓并三 SHA 逐字节一致 |
| **2** | v6 重算批次/分母/旧 v4 保留位置 | 下方 §2 全表 + [`docs/reports/V13_T6_V6_HISTORY_AND_RETRO_SELFCHECK_2026-11-13.md`](reports/V13_T6_V6_HISTORY_AND_RETRO_SELFCHECK_2026-11-13.md) | ✅ 与仓内报告逐位一致 |
| **3** | 多参考 Hit@k 预注册 | [`docs/PREREG_MULTI_REFERENCE_HITK_DISCLOSURE_2026-11-21.md`](PREREG_MULTI_REFERENCE_HITK_DISCLOSURE_2026-11-21.md) | ✅ 参考集/版本/分母写死（`pending_teacher_confirmation`） |
| **4** | 五态 `route_status` schema 状态 | **已实现**：[`src/pathway_v43/pollutant/route_status.py`](../src/pathway_v43/pollutant/route_status.py) + [`tests/unit/test_route_status_schema.py`](../tests/unit/test_route_status_schema.py) | ✅ 已落码并 19/19 单测全绿 |
| **5** | 14 道 `ROUTE_GOLD_COLLISION` 清单 | 下方 §5 + [`docs/review_evidence/v6_caliber_supplement_2026-11-21/route_gold_collision_14_cases_qid_audit.tsv`](review_evidence/v6_caliber_supplement_2026-11-21/route_gold_collision_14_cases_qid_audit.tsv) | ✅ qid 级可核（含 `split_status`） |
| **6** | de-leak 试点状态 | 下方 §6 | ✅ 已明确状态与暂缓声明 |
| **7** | 失败题双口径表（主口径 + 敏感性口径） | 下方 §7 + [`docs/review_evidence/v6_caliber_supplement_2026-11-21/failure_dual_denominator_table.tsv`](review_evidence/v6_caliber_supplement_2026-11-21/failure_dual_denominator_table.tsv) | ✅ 39 行批/模型双口径并报 |
| **8** | 第 2/6 项唯一 owner + `qid` 级 join 表 | 下方 §8 + [`pathway_qid_hitk_join_tuning261.tsv`](review_evidence/v6_caliber_supplement_2026-11-21/pathway_qid_hitk_join_tuning261.tsv) + [`pathway_case_hitk_join_tuning76.tsv`](review_evidence/v6_caliber_supplement_2026-11-21/pathway_case_hitk_join_tuning76.tsv) | ✅ 已指定唯一 owner 并交付 261 qid / 76 case 键 |

---

## §1. 补件 #1：v6 冻结锚点、一句话口径、6 条护栏与小分子排除清单

### 1.1 仓内可核对冻结文件与三份 SHA256

以下文件均已完整同步入本仓 `v44` 分支，逐字节对齐 [`CRITERIA_V6_FREEZE_REGISTRATION_2026-11-13.md`](CRITERIA_V6_FREEZE_REGISTRATION_2026-11-13.md)：

| 文件 | 仓内路径 | 冻结 SHA256 | 说明 |
| :--- | :--- | :--- | :--- |
| 冻结登记稿 | [`docs/CRITERIA_V6_FREEZE_REGISTRATION_2026-11-13.md`](CRITERIA_V6_FREEZE_REGISTRATION_2026-11-13.md) | 文档锚点（2026-11-13） | 记录冻结时间（先于任何留出集接触）、CC 拍板、规则与报告纪律 |
| 规则说明稿 | [`docs/reports_teacher/CRITERIA_V6_PROTONATION_INVARIANT_RULES_DRAFT_2026-11-13.md`](reports_teacher/CRITERIA_V6_PROTONATION_INVARIANT_RULES_DRAFT_2026-11-13.md) | 规则正文 + 示例 | §4 完整定义允许合并 / 明确排除 / 6 条顺序护栏 |
| mimo 化学评审与加固报告 | [`docs/reviews/mimo_v4cn_charge_neutral_review_response_2026-11-13.md`](reviews/mimo_v4cn_charge_neutral_review_response_2026-11-13.md)<br>[`docs/reports/V13_T2H_V4CN_HARDENING_REPORT_2026-11-13.md`](reports/V13_T2H_V4CN_HARDENING_REPORT_2026-11-13.md)<br>[`docs/reports/v4cn_operator_behavior_table_2026-11-13.json`](reports/v4cn_operator_behavior_table_2026-11-13.json) | 25 夹具行为表 + 12 项护栏单测 [`test_v4cn_guards.py`](../tests/unit/test_v4cn_guards.py) | 覆盖季铵/两性离子/硝基/磷酸酯/磺酸/硫酯/盐/烯醇负离子 |
| **v6 评分实现脚本** | [`scripts/eval/score_disclosure_v4cn.py`](../scripts/eval/score_disclosure_v4cn.py) | **`0ffb8b71330653f7b0373a67d028b14a84d4c5f13a83abd17db89a3c82a28f2f`** | 对参考侧与预测侧对称做护栏受控质子化归一后送入冻结 v4 引擎 |
| **底层冻结判分器 1** | [`src/pathway_v43/pollutant/evaluation.py`](../src/pathway_v43/pollutant/evaluation.py) | **`ac38ea393bfb91e420e98730415cba334df2f9d3d9de4ecfde90914f45363f41`** | 冻结 `ppv1-criteria-v4` 判分核心（一行未改） |
| **底层冻结判分器 2** | [`src/pathway_v43/pollutant/s5b_scoring.py`](../src/pathway_v43/pollutant/s5b_scoring.py) | **`5a677550ef54a3a1e16d5b5a1ce4dd8d2cdcb55dd56224e8a148f50511dc456d`** | 已恢复第 181 行原始 docstring 词（`Remote`→`Chenyu`），与冻结登记三 SHA 逐字节一致 |

**本地一键复现核对命令**：

```bash
shasum -a 256 scripts/eval/score_disclosure_v4cn.py src/pathway_v43/pollutant/evaluation.py src/pathway_v43/pollutant/s5b_scoring.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -B -m pytest tests/unit/test_v4cn_guards.py -v
```

### 1.2 一句话说清 v6 改动、6 条护栏与小分子排除清单

- **v6 唯一改动**：在 `ppv1-criteria-v4` 全部事件合法性、禁止跨事件拼答案、主产物覆盖、固定分母与排序规则**原样不变**的前提下，仅将底物与主产物的分子身份函数在参考侧和预测侧**对称替换为「受 6 条护栏约束的质子化不变身份」**（只消解羧酸/羧酸根、胺/铵、磷酸/硫酸/磺酸各级解离、两性离子与烯醇负离子的质子化写法差异）。
- **6 条顺序护栏**（见规则稿 §4.4；任一条不通过即退回严格 v4 身份并留痕原因）：
  1. 小分子排除清单命中 → 不归一（记 `excluded_family`）；
  2. 多组分盐 / 带反离子 → 不归一（记 `salt_not_normalized`）；
  3. 本来即为中性且无形式电荷 → 直接短路沿用原身份（记 `not_applicable`）；
  4. 归一前后**重原子连接图、键级、元素序列、同位素、立体（含增强立体）、自由基电子数、组分数**必须 100% 不变，仅允许形式电荷与相应位点氢数改变（否则 `invariant_broken`）；
  5. **净电荷单调趋中保护**：出现 `0 → 非 0`、正负号翻转或净电荷绝对值增大时一律回退（`net_charge_changed`）；
  6. **同源幂等往返**：输出必须走冻结 v4 同一 CXSMILES `strict_identity_of` 身份机器，且满足二次调用幂等（否则 `identity_roundtrip_failed`）。
- **明确不参与合并的小分子排除清单**（CC 2026-11-13 拍板 + `EXCLUDED_FAMILIES` 严格身份锁死）：
  - **碳酸体系**（`CO₂` / `HCO₃⁻` / `CO₃²⁻`）、**氨/铵体系**（`NH₃` / `NH₄⁺`）、**氰体系**（`CN⁻` / `HCN`）、**硫氰酸体系**（`SCN⁻` / `HSCN`）、**氢离子体系**（`H⁺` / `H₃O⁺`）。

---

## §2. 补件 #2：v6 重算批次范围、分母与历史 v4 保留位置

> 依据仓内已有权威报告 [`V13_T6_V6_HISTORY_AND_RETRO_SELFCHECK_2026-11-13.md`](reports/V13_T6_V6_HISTORY_AND_RETRO_SELFCHECK_2026-11-13.md)、[`V14_45PCT_CLOSEOUT_REPORT_2026-11-15.md`](V14_45PCT_CLOSEOUT_REPORT_2026-11-15.md)、[`PAPER_ABLATION_STUDY_V14_REPORT_2026-11-16.md`](reports/PAPER_ABLATION_STUDY_V14_REPORT_2026-11-16.md) 与 [`B121_EXTERNAL_BASELINES_BENCHMARK_2026-11-16.md`](reports/B121_EXTERNAL_BASELINES_BENCHMARK_2026-11-16.md) 汇总，零新跑批、数字与各报告逐位一致。

| 批次 / 实验配置 | 题域与分母标签 | `v6` 参考命中率 `Hit@1 / @3 / @5` | 并列保留的旧 `v4` `Hit@1 / @3 / @5` | 历史 `v4` 永久保留位置（永不覆盖） |
| :--- | :--- | :---: | :---: | :--- |
| **`v1.4` 终版 `T1-6` (`11p + trace_protected`)** | `[biosysmodb121·调参集 N=261]` | **`118 / 133 / 141` (`45.21%`)** | `80 / 96 / 102` (`30.65%`) | `V14_45PCT_CLOSEOUT_REPORT_2026-11-15.md` §1、`PAPER_ABLATION_STUDY_V14_REPORT_2026-11-16.md` 表 D1/D2、`t14_step4_summary.json` |
| **`v1.4` 终版 `T1-6` (去噪切片)** | `[biosysmodb121·调参干净集 N=220]` | **`113 / 127 / 134` (`51.36%`)** | `76 / 91 / 96` (`34.55%`) | `B121_CLEAN_SUBSET_V14_EVALUATION_2026-11-16.md` §1、`V14_45PCT_CLOSEOUT_REPORT_2026-11-15.md` §1 |
| **`v1.4` `T1-6 NoSelf` (11p 输入无自记录)** | `[biosysmodb121·调参集 N=261]` | `94 / 127 / 134` (`36.02%`) | `61 / 87 / 93` (`23.37%`) | `PAPER_ABLATION_STUDY_V14_REPORT_2026-11-16.md` 表 D1/D2 与 §5（`Clean-220`: `v6 90` vs `v4 58`） |
| **`v1.4` `298` 双路共识 (`2p wl3+@20 cons_v3`)** | `[dev-298·调参集 N=196]` | `95 / 123 / 127` (`48.47%`) | `92 / 119 / 124` (`46.94%`) | `V14_45PCT_CLOSEOUT_REPORT_2026-11-15.md` §1、`t14_step4_summary.json` |
| **`v1.4` `298` 单路代表 (`single_v2 pa`)** | `[dev-298·调参集 N=196]` | `97 / 123 / 126` (`49.49%`) | `93 / 118 / 121` (`47.45%`) | `V14_45PCT_CLOSEOUT_REPORT_2026-11-15.md` §1、`t14_step4_summary.json` |
| **`v1.3` 控制基线 (`ctrl_pa_pb` / `ctrl_w20`)** | `B121 N=261` / `298 N=196` | `105/117/133` / `86/118/127` | `71/87/97` / `84/115/124` | `t14_step4_summary.json`、`V14_45PCT_CLOSEOUT_REPORT_2026-11-15.md` §1 |
| **历史 T6 复算：`v1.0` / `v1.1` / `v1.2` / `T2-R` / `T2-T`** | `[biosysmodb121·调参集 N=261]` | `86/111/114` · `90/111/122` · `99/116/125` · `88/114/122` · `92/117/124` | `57/76/77` · `54/75/87` · `66/80/90` · `58/78/87` · `61/82/88` | `docs/reports/V13_T6_V6_HISTORY_AND_RETRO_SELFCHECK_2026-11-13.md` §3.1 + 原始归档 `metrics_v4.json` |
| **历史 T6 复算：`v1.0` / `v1.1` / `v1.2` / `T2-R` / `T2-T`** | `[dev-298·调参集 N=196]` | `74/102/107` · `78/105/111` · `94/118/122` · `84/113/117` · `86/115/123` | `73/98/103` · `77/102/108` · `91/113/117` · `82/110/114` · `84/111/119` | `docs/reports/V13_T6_V6_HISTORY_AND_RETRO_SELFCHECK_2026-11-13.md` §3.2 + 原始归档 `metrics_v4.json` |
| **外部基线：`BioTransformer 3.0` / `ECLIPSE`** | `B121 N=261` (`Clean-220` / `Full-417` 见单测报告) | `54/78/84` · `61/101/111` *(N=261)* | `45/65/69` · `53/86/92` *(N=261)* | `B121_EXTERNAL_BASELINES_BENCHMARK_2026-11-16.md` + `b121_external_baselines_summary.json` |
| **历史全集基线（暂不重算）** | `[biosysmodb121·全集 N=417]` & `[dev-298·全集 N=298]` | *留出集未开箱，暂不重算* | 永久基准：`113/417`、`156/298` | `docs/review_evidence/2026-11-02/V4_IMPL_REPORT.md` & `v4_metrics.json`（历史只读保留，待开箱留出集时一并重算 v6 并列披露） |
| **未重算历史探测（说明原因）** | `Exp-1b`（8 题合成） / `Exp-2`（HPC 远端） | *不可重算（无调参交集 / 本地无原生导出批根）* | 各自原批报告保留 | `V13_T6_V6_HISTORY_AND_RETRO_SELFCHECK_2026-11-13.md` §5.1–5.2 |

---

## §3. 补件 #3：多参考 Hit@k 预注册

完整预注册文本已独立落盘：[`docs/PREREG_MULTI_REFERENCE_HITK_DISCLOSURE_2026-11-21.md`](PREREG_MULTI_REFERENCE_HITK_DISCLOSURE_2026-11-21.md)（当前状态 `preregistration_status = pending_teacher_confirmation`，`allow_writeback_to_primary = false`）：

- **参考集与版本**：仅纳 `Tier-1` 已审核生化学多参考（`BIOSYSMOdb121` 同底物兄弟 curated 路径 + `dependingv3 v3.5` `EAWAG-BBD/enviPath` + `Rhea/MetaNetX`，并按非生物审计剔除纯自发/UV/`[OH]` 条目）；**严格排除** `USPTO` 合成模板与**任何未审核文献路线**。
- **分母与并列**：与主口径保持 **100% 同题集同分母**（`N=261` / `Clean-220` / `298 N=196` / `Tuning-76`，零触碰留出集），成对并列披露 `Single-Ref v6 (冻结主表)` 与 `Multi-Ref Tier-1 v6 (披露)`；**绝不回写主成绩**。

---

## §4. 补件 #4：五态路线状态（`route_status`）落地实现状态

- **明确结论**：选择方案一——**「已实现」**（已完成独立 schema 模块、校验器、导出器与单元测试落地，正式口径改用明确“已实现”；且**零修改**三份冻结判分器）。
- **核心契约（[`src/pathway_v43/pollutant/route_status.py`](../src/pathway_v43/pollutant/route_status.py)）**：
  - 枚举定义五态 `RouteStatus`：`IN_GOLD_EXACT`、`IN_GOLD_PARTIAL`、`OUTSIDE_GOLD_PLAUSIBLE`、`OUTSIDE_GOLD_CONTRADICTED`、`UNRESOLVED`；并正交分离 `DeliveryStatus`（`OK` / `LENGTH_EMPTY` / `INVALID_JSON` / `RESULT_UNKNOWN` / `RUN_ERROR` / `NO_EVENT`）、`ZeroReason` 与 `ScientificEvalLabel`（`HIT_EXACT` / `HIT_PARTIAL` / `NE` / `ZERO`）。
  - **强制专家复核红线**：未经师姐 / 领域专家书面确认（`ExpertReviewRecord(confirmed=True, reviewer_role in {"domain_expert", "senior_chemist"})`），所有单一参考未命中题一律 fail-closed 记为 **`UNRESOLVED`（科学层 `NE`，不记 `0`）**；`OUTSIDE_GOLD_PLAUSIBLE` 永远记 **`NE`**（严禁记 `ZERO`）；`OUTSIDE_GOLD_CONTRADICTED` 必须附非空化学矛盾 `evidence` 才可记 **`ZERO`**；工程/交付失败一律归交付轴且科学层记 **`NE`**，且 `primary_score_immutable=True` 硬性禁止回写主成绩。
- **回归验证**：[`tests/unit/test_route_status_schema.py`](../tests/unit/test_route_status_schema.py) 19 项单测全部通过（`19 passed`），并校验三份冻结判分器 SHA256 逐字节未变。
- **在 `v1.4 T1-6`（`[biosysmodb121·调参集 N=261]`）上的实际跑通摘要**（见 [`route_status_summary_tuning261.json`](review_evidence/v6_caliber_supplement_2026-11-21/route_status_summary_tuning261.json)）：
  - `IN_GOLD_EXACT = 141`（`Top-1 = 118, Top-3 = 133, Top-5 = 141`）；`IN_GOLD_PARTIAL = 0`；
  - 未核未命中全部 fail-closed 归入 `UNRESOLVED (NE) = 120`；在师姐/专家复核接入前，`OUTSIDE_GOLD_PLAUSIBLE = 0`、`OUTSIDE_GOLD_CONTRADICTED = 0`、`ZERO = 0`。

---

## §5. 补件 #5：14 道 `ROUTE_GOLD_COLLISION` qid 级可核清单

> **出处依据**：`EnzymeCAGE-Teacher-Deliverables/2026-09-28_BIOSYSMODB150_G2_G9_FINAL_CONSOLIDATED_REVIEW_V2.tar.gz` 内 `G2_questions/leakage_hits.tsv`（合计 `20` 条碰撞行，去重覆盖 `14` 个独立 `BIOPATH150` 案例）。按本仓零留出接触红线，通过与 `Tuning-261` 公开调参清单比对划分 `split_status`（8 题属 `tuning_76`，共 26 个调参 `qid`；6 题属 `non_tuning_locked`，其公开总步骤列引自 `PER_GOLD_STEP.tsv`）。完整机读 TSV 见 [`route_gold_collision_14_cases_qid_audit.tsv`](review_evidence/v6_caliber_supplement_2026-11-21/route_gold_collision_14_cases_qid_audit.tsv)。

| 案例 ID | 分集状态 | 题面 `old_route_qualifier` | 碰撞词 (`token`) | 碰撞金标字段 | 调参 `qid`（仅 `tuning_76`） / `PER_GOLD_STEP` 公开步骤数 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `BIOPATH150_009` | `tuning_76` | `Limonene degradation III (to perillate)` | `perillate` | `MAIN_PRODUCT_NAME` | 3 步：`BIOPATH150_009__S01__BSY-r01699; ...S02__BSY-r01701; ...S03__BSY-r01702` |
| `BIOPATH150_016` | `tuning_76` | `p-Cymene degradation to p-cumate` | `p-cumate` | `MAIN_PRODUCT_NAME` | 7 步：`BIOPATH150_016__S01__BSY-r00339` .. `S07__BSY-r00345` *(公开 G3 记 3 步)* |
| `BIOPATH150_019` | `tuning_76` | `Toluene degradation II (aerobic) (via 4-methylcatechol)` | `methylcatechol; 4-methylcatechol` | `MAIN_PRODUCT_NAME` | 4 步：`BIOPATH150_019__S01__BSY-r00220; ...S03__BSY-r01749; ...S05__BSY-r01752; ...S06__BSY-r01754` *(全路径 6 步)* |
| `BIOPATH150_020` | `non_tuning_locked` | `Toluene degradation to benzoate` | `benzoate` | `MAIN_PRODUCT_NAME` | 0 调参步 / 3 公开步：`BIOPATH150_020__S01__BSY-r00229; ...S02__BSY-r00231; ...S03__BSY-r00232` |
| `BIOPATH150_041` | `tuning_76` | `propanoyl CoA degradation I` | `propanoyl` | `MAIN_PRODUCT_NAME` | 2 步：`BIOPATH150_041__S02__BSY-r03821; ...S03__BSY-r03869` *(全路径 3 步)* |
| `BIOPATH150_054` | `tuning_76` | `methylglyoxal degradation VIII` | `methylglyoxal` | `MAIN_PRODUCT_NAME` | 1 步：`BIOPATH150_054__S02__BSY-r02236` *(全路径 2 步)* |
| `BIOPATH150_068` | `non_tuning_locked` | `3-chlorobenzoate degradation I (via chlorocatechol)` | `chlorocatechol` | `MAIN_PRODUCT_NAME` | 0 调参步 / 4 公开步：`BIOPATH150_068__S01__BSY-r02059` .. `S04__BSY-r03303` |
| `BIOPATH150_079` | `non_tuning_locked` | `5,5'-dehydrodivanillate degradation` | `vanillate` | `MAIN_PRODUCT_NAME` | 0 调参步 / 4 公开步：`BIOPATH150_079__S01__BSY-r01799` .. `S04__BSY-r02941` |
| `BIOPATH150_082` | `tuning_76` | `acrylate degradation I` | `acrylate` | `MAIN_PRODUCT_NAME` | 5 步：`BIOPATH150_082__S01__BSY-r00663` .. `S05__BSY-r00667` |
| `BIOPATH150_094` | `non_tuning_locked` | `testosterone and androsterone degradation to androstendione (aerobic)` | `testosterone` | `MAIN_PRODUCT_NAME` | 0 调参步 / 2 公开步：`BIOPATH150_094__S01__BSY-r03700; ...S02__BSY-r03701` |
| `BIOPATH150_106` | `non_tuning_locked` | `β myrcene degradation` | `myrcene` | `MAIN_PRODUCT_NAME` | 0 调参步 / 4 公开步：`BIOPATH150_106__S01__BSY-r01725` .. `S04__BSY-r01728` |
| `BIOPATH150_141` | `tuning_76` | `S-(6-hydroxy-4-methylhexan-4-yl)-L-cysteinylglycine degradation` | `methylhexan` | `MAIN_SUBSTRATE_NAME` | 1 步：`BIOPATH150_141__S01__BSY-r02165` *(全路径 3 步)* |
| `BIOPATH150_143` | `non_tuning_locked` | `γ-butyrobetaine degradation I` | `butyrobetaine` | `MAIN_PRODUCT_NAME` | 0 调参步 / 4 公开步：`BIOPATH150_143__S01__BSY-r00741` .. `S04__BSY-r00744` |
| `BIOPATH150_144` | `tuning_76` | `γ-butyrobetaine degradation III` | `butyrobetaine` | `MAIN_PRODUCT_NAME` | 3 步：`BIOPATH150_144__S01__BSY-r00752` .. `S03__BSY-r00754` *(全路径 4 步)* |

---

## §6. 补件 #6：de-leak 试点状态与旧六基模对比暂缓声明

1. **当前进展**：
   - 已先期在 `Tuning-76` 抽样的 **20 题小规模试点（单模型 `gpt-5.6-luna`，去除题面路线名 `chosen_route_name` 与氧条件、要求写到完全矿化并输出至多 5 条排序候选路线）** 上完成格式、耗时与 Token 测量（20 题串行 `1,314.56 s`，JSON 合法 `19/20`，`BIOPATH150_007` 1 题 JSON 语法错误；具体含失误双口径数字见下节 §7）。
   - **完整六基模的正式 de-leak 重测尚未开展，也未经过独立化学/专家复核**。
2. **明确暂缓声明**：
   - 严格遵照 2026-11-18 批复，**全量 6 基模 de-leak 重测完成前，本线撤回/暂缓任何“本线优于旧六基模”的结论**（含已同步加挂治理提示的 [`B121_V14_VS_SIX_BASE_MODELS_N220_2026-11-16.md`](B121_V14_VS_SIX_BASE_MODELS_N220_2026-11-16.md) 与 [`B121_SIX_MODEL_CLEAN_SUBSET_HIT1_2026-11-16.md`](B121_SIX_MODEL_CLEAN_SUBSET_HIT1_2026-11-16.md)）。
   - 未来开展正式六基模对照时，**必须满足四同**：同 **`ppv1-criteria-v6` 口径**、**同分母**、**同参考集**、**单参考 Hit@k 与 Tier-1 多参考 Hit@k 分开列报**。

---

## §7. 补件 #7：失败题双口径并报表（主口径 + 敏感性口径）

> **统计口径规则**：
> - **主口径（保守，默认主表）**：全部注册题留分母，工程/格式失败与无合规事件均按未命中计（不抬高命中率）；
> - **敏感性口径 A（剔除 API/JSON/EMPTY 失败）**：仅剔除未产出可解析结果的工程/格式失败题后的分母（按来信把工程失败归交付轴、科学层记 NE 时的参考分母）；
> - **敏感性口径 B（进一步剔除 `unmatched_no_event` / 0 覆盖）**：供诊断“有输出时的相对准确度”。
> 完整 39 行机器核验表见 [`failure_dual_denominator_table.tsv`](review_evidence/v6_caliber_supplement_2026-11-21/failure_dual_denominator_table.tsv)。以下摘录关键配置（含全部 `n_failed > 0` 或 `unmatched_no_event > 0` 的代表项）：

| 题域·分集 | 系统 / 配置 | 口径 | 工程失败 (`API/JSON/EMPTY`) | `no_event` / 0 覆盖 | **主口径 `Hit@1` (`n/N`, %)** | **敏感性 A (剔工程失败)** | **敏感性 B (剔全部无事件)** |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `[biosysmodb121·调参集 N=261]` | **`v44-Next v1.4 T1-6` 终版** | `v6` | `0` | `0` | **`118 / 261 (45.21%)`** | `118 / 261 (45.21%)` | `118 / 261 (45.21%)` |
| `[biosysmodb121·调参干净集 N=220]` | **`v44-Next v1.4 T1-6` 终版** | `v6` | `0` | `0` | **`113 / 220 (51.36%)`** | `113 / 220 (51.36%)` | `113 / 220 (51.36%)` |
| `[dev-298·调参集 N=196]` | **`v44-Next v1.4 (2p wl3+@20 cons_v3)`** | `v6` | `0` | `2` | **`95 / 196 (48.47%)`** | `95 / 196 (48.47%)` | `95 / 194 (48.97%)` |
| `[dev-298·调参集 N=196]` | `v44-Next v1.4 (single_v2 pa)` | `v6` | `0` | `2` | `97 / 196 (49.49%)` | `97 / 196 (49.49%)` | `97 / 194 (50.00%)` |
| `[dev-298·调参集 N=196]` | `v44-Next v1.3 control` | `v6` | `0` | `2` | `86 / 196 (43.88%)` | `86 / 196 (43.88%)` | `86 / 194 (44.33%)` |
| `[biosysmodb121·调参集 N=261]` | `Paper Ablation DB-1 EmptyPool` | `v6` | `0` | `23` | `83 / 261 (31.80%)` | `83 / 261 (31.80%)` | `83 / 238 (34.87%)` |
| `[biosysmodb121·调参集 N=261]` | `Paper Ablation T1-0a AT-RawBlind+Gate` | `v6` | `0` | `21` | `84 / 261 (32.18%)` | `84 / 261 (32.18%)` | `84 / 240 (35.00%)` |
| `[biosysmodb121·调参集 N=261]` | `Paper Ablation DB-6 MNXOnly` | `v6` | `0` | `6` | `102 / 261 (39.08%)` | `102 / 261 (39.08%)` | `102 / 255 (40.00%)` |
| `[biosysmodb121·全集 N=417]` | **`BioTransformer 3.0`** | `v6` | `22 (EMPTY)` | `1` *(有输出0覆盖)* | **`81 / 417 (19.42%)`** | `81 / 395 (20.51%)` | `81 / 394 (20.56%)` |
| `[biosysmodb121·调参集 N=261]` | **`BioTransformer 3.0`** | `v6` | `13 (EMPTY)` | `0` | **`54 / 261 (20.69%)`** | `54 / 248 (21.77%)` | `54 / 248 (21.77%)` |
| `[biosysmodb121·调参干净集 N=220]` | **`BioTransformer 3.0`** | `v6` | `7 (EMPTY)` | `0` | **`51 / 220 (23.18%)`** | `51 / 213 (23.94%)` | `51 / 213 (23.94%)` |
| `[biosysmodb121·全集/N=261/N=220]` | `ECLIPSE PREDEC (10f)` | `v6` | `0` | `0` | `93/417` · `61/261` · `57/220` | 同左 *(0 失败)* | 同左 *(100% 覆盖)* |
| `[biosysmodb121·Tuning-76 路径]` | `v44-Next v1.4 E2E Stage-Aware` | 矿化 `sink-v1` | `0` | `0` | `36 / 76 (47.37%)` | `36 / 76 (47.37%)` | `36 / 76 (47.37%)` |
| `[biosysmodb121·去泄漏20题试点]` | `gpt-5.6-luna` *(步级 Clean-58)* | `v6` | `8 步` (`1 题 JSON 错`) | `0` | `Hit@1 10/58 (17.24%)` / `@5 12/58 (20.69%)` | `Hit@1 10/50 (20.00%)` / `@5 12/50 (24.00%)` | `10 / 50 (20.00%)` |
| `[biosysmodb121·去泄漏20题试点]` | `gpt-5.6-luna` *(严格碳矿化 N=20)* | `sink-v1` | `1 题` (`BIOPATH150_007`) | `0` | `3 / 20 (15.00%)` | `3 / 19 (15.79%)` | `3 / 19 (15.79%)` |

*(注：旧六基模 `Likert V0.5` 发布快照 `EnzymeCAGE-Teacher-Deliverables/2026-11-15_BIOSYSMODB121_Likert_V05_Results_And_Attribution/data/LIKERT_V05_SCORES_726.tsv` 共 `726` 槽位中有 `3` 条工程失败，均落在 `Tuning-76` 内：`BIOPATH150_023 (GLM: LENGTH_EMPTY)`、`BIOPATH150_087 (Grok: RESULT_UNKNOWN_HELD)`、`BIOPATH150_145 (Grok: SCHEMA_CONTROL_FAIL)`。)*

---

## §8. 补件 #8：验收清单第 2、6 项唯一 Owner 与 `qid` 级 Join 表交付

### 8.1 唯一 Owner 认领矩阵

| 验收清单项 | 交付物 | **唯一责任人（Owner）** | 降解路径分支（**弓赛**）实际对接交付 |
| :---: | :--- | :--- | :--- |
| **第 2 项** | 五层程序分 `v1 → v2` 映射表 | **基模评测与 Likert 线负责人（GitHub 账号：`bgruiiii`）**† | 路径线已另行在 §2 交付本线的版本映射表（`v43-scorer-1/2 → v4 → v6`），不与五层程序分混算 |
| **第 6 项** | `program_vs_likert` 案例级 join 表 | **基模评测与 Likert 线负责人（GitHub 账号：`bgruiiii`）**† | 路径线已按老师要求交付下方 **`Tuning-261` 步级 `qid → Hit@k` 表**与 **`Tuning-76` 病例级 `case_id → Hit@k` 表**供直接 join 对接 |

> † 注：`bgruiiii` 系 `EnzymeCAGE-Teacher-Deliverables` 中 Likert V0.5 评分与五层程序分汇总报告的维护提交者；正式对外归档前的实体姓名确认待其本人复核补注。

### 8.2 路径线交付的 `qid` 级与 `case_id` 级 Join 表说明

由 [`scripts/eval/export_route_status_join.py`](../scripts/eval/export_route_status_join.py) 从封存 `v1.4 T1-6` 逐题输出确定性生成（零 SMILES、零触碰留出集）：

1. **步级主键表（`261` 行）**：[`pathway_qid_hitk_join_tuning261.tsv`](review_evidence/v6_caliber_supplement_2026-11-21/pathway_qid_hitk_join_tuning261.tsv)
   - Join 键：`qid`（逐字节对应 `PER_GOLD_STEP.tsv::gold_step_id`）与 `case_id`；
   - `254 / 261` 行精确匹配 `PER_GOLD_STEP.tsv` 且全部 `scope_evaluable=True`；其余 `7` 题显式标 `in_per_gold_step_public=False`（`BIOPATH150_016__S04..S07`、`_024__S06`、`_090__S01`、`_139__S03`，属旧 G3 120 题范围裁剪外步骤）；
   - 包含字段：`tuning_subset`（`Clean-220`/`Excluded-41`）、`is_route_gold_collision_case`、`v14_t16_delivery_status`、`v14_t16_v6_rank / hit1 / hit3 / hit5`、`v14_t16_v4_rank / hit1 / hit3 / hit5`、`v14_t16_route_status`、`v14_t16_scientific_eval_label`、`v14_t16_zero_reason`。
2. **病例级主键表（`76` 行）**：[`pathway_case_hitk_join_tuning76.tsv`](review_evidence/v6_caliber_supplement_2026-11-21/pathway_case_hitk_join_tuning76.tsv)
   - Join 键：`case_id`——与 `LIKERT_V05_SCORES_726.tsv` 中的 `Tuning-76` 全部 **`76 / 76`（`100%`，`456` 条六模型评分行）精确匹配**；每行同时提供路径线步级 `v6` / `v4` Hit@1/@3/@5 命中数与命中率、五态计数，以及仅供参照的 Likert V0.5 / 程序分 v1 上游均值与工程失败标记（`program_vs_likert` 正式总表仍由唯一 owner `bgruiiii` 统一产出与维护）。
