# 回复黄老师：降解路径分支判分口径与指标分工（补件完成定稿版）

> - **致**：黄老师
> - **来自**：弓赛（反应预测 / 降解路径分支）
> - **日期**：2026-11-21
> - **回复对象**：《给弓赛：降解路径分支判分口径与指标分工的批复》（`TEACHER_REPLY_GONGSAI_V6_CALIBER_2026-11-18(1).md`）
> - **补件总索引**：[`V6_CALIBER_SUPPLEMENTS_PACKAGE_2026-11-21.md`](V6_CALIBER_SUPPLEMENTS_PACKAGE_2026-11-21.md)（组织仓与个人仓 `v44` 分支均可直接打开核验）
> - **术语与边界声明**：本线所有 `v6` Hit@1 / @3 / @5 一律称作**「参考命中率」**，绝不称作“科学正确率”；全量 6 基模去泄漏（de-leak）重测完成并复核前，**不作任何“本线优于旧六基模”结论**；所有文件零 SMILES、零留出集接触。

---

## 一、8 项补件清单落实总表（对应批复 §4）

| # | 批复要求 | 本线落实交付与仓内路径 | 验证方式 / 当前状态 |
| :-: | :--- | :--- | :--- |
| **1** | **v6 冻结登记 + 评分脚本 + 三份 SHA256 进仓** | [`CRITERIA_V6_FREEZE_REGISTRATION_2026-11-13.md`](CRITERIA_V6_FREEZE_REGISTRATION_2026-11-13.md)、[`CRITERIA_V6_PROTONATION_INVARIANT_RULES_DRAFT_2026-11-13.md`](reports_teacher/CRITERIA_V6_PROTONATION_INVARIANT_RULES_DRAFT_2026-11-13.md)、[`score_disclosure_v4cn.py`](../scripts/eval/score_disclosure_v4cn.py)、[`evaluation.py`](../src/pathway_v43/pollutant/evaluation.py)、[`s5b_scoring.py`](../src/pathway_v43/pollutant/s5b_scoring.py) | ✅ 已入 `v44`；三份冻结 SHA256 逐字节匹配（`0ffb8b71...` / `ac38ea39...` / `5a677550...`）；[`test_v4cn_guards.py`](../tests/unit/test_v4cn_guards.py) 12/12 通过 |
| **2** | **v6 重算批次范围、分母、旧 v4 保留位置** | [`V6_CALIBER_SUPPLEMENTS_PACKAGE_2026-11-21.md`](V6_CALIBER_SUPPLEMENTS_PACKAGE_2026-11-21.md) §2 + [`V13_T6_V6_HISTORY_AND_RETRO_SELFCHECK_2026-11-13.md`](reports/V13_T6_V6_HISTORY_AND_RETRO_SELFCHECK_2026-11-13.md) | ✅ 完整列明调参重算批次、两域分母、历史 `v4` 只读保留路径及 `Exp-1b/Exp-2`/留出集未重算范围 |
| **3** | **多参考 Hit@k 预注册** | [`PREREG_MULTI_REFERENCE_HITK_DISCLOSURE_2026-11-21.md`](PREREG_MULTI_REFERENCE_HITK_DISCLOSURE_2026-11-21.md) | ✅ `pending_teacher_confirmation`；写死 Tier-1 参考库与 SHA、不含未审核文献路线、同分母、**`allow_writeback_to_primary = false`** |
| **4** | **五态 `route_status` schema 状态** | **已实现**（已落码，二选一明确为“已实现”）：[`route_status.py`](../src/pathway_v43/pollutant/route_status.py)、[`export_route_status_join.py`](../scripts/eval/export_route_status_join.py)、[`test_route_status_schema.py`](../tests/unit/test_route_status_schema.py) | ✅ 19/19 单测全绿（零改动冻结判分器）；强约束未核未中落 `UNRESOLVED (NE)`、外推 plausible 记 `NE`、contradicted 须专家+证据 |
| **5** | **14 道 `ROUTE_GOLD_COLLISION` 清单** | [`route_gold_collision_14_cases_qid_audit.tsv`](review_evidence/v6_caliber_supplement_2026-11-21/route_gold_collision_14_cases_qid_audit.tsv) + 补件包 §5 | ✅ 14 题 / 20 行碰撞（`8` 题在 `tuning_76` 共 26 个调参 `qid`，`6` 题标 `non_tuning_locked` 并附公开步 ID） |
| **6** | **de-leak 试点状态与暂缓对比声明** | 补件包 §6 + 历史对比报告顶部显著暂缓声明（[`B121_V14_VS_SIX_BASE_MODELS_N220_2026-11-16.md`](B121_V14_VS_SIX_BASE_MODELS_N220_2026-11-16.md)、[`B121_SIX_MODEL_CLEAN_SUBSET_HIT1_2026-11-16.md`](B121_SIX_MODEL_CLEAN_SUBSET_HIT1_2026-11-16.md)） | ✅ 仅完成 `gpt-5.6-luna` 20 题试点（测耗时/Token/格式）；**全量 6 基模重测前不写“优于旧六基模”** |
| **7** | **失败题双口径表** | [`failure_dual_denominator_table.tsv`](review_evidence/v6_caliber_supplement_2026-11-21/failure_dual_denominator_table.tsv) + 补件包 §7 | ✅ 39 行批/模型**主口径（留分母）+ 敏感性口径（剔工程失败 / 剔无事件）并报** |
| **8** | **第 2、6 项唯一 Owner + `qid` 级 Join 表** | 唯一 Owner：**基模评测与 Likert 线负责人（GitHub: `bgruiiii`）**；路径线交付 [`pathway_qid_hitk_join_tuning261.tsv`](review_evidence/v6_caliber_supplement_2026-11-21/pathway_qid_hitk_join_tuning261.tsv)（`261` 步）与 [`pathway_case_hitk_join_tuning76.tsv`](review_evidence/v6_caliber_supplement_2026-11-21/pathway_case_hitk_join_tuning76.tsv)（`76` 题） | ✅ 254/261 步精确匹配 `PER_GOLD_STEP.tsv`、`76/76` 病例 100% 匹配 `LIKERT_V05_SCORES_726.tsv` |

---

## 二、现行口径摘要与关键规则确认

1. **`ppv1-criteria-v6` 一句话定义与护栏**：
   - 在 2026-10-28 预注册的 `ppv1-criteria-v4` 全部规则不变的基础上，**唯一改动**是将底物与主产物的身份函数在参考侧和预测侧**对称替换为受 6 条护栏约束的质子化不变身份**（`1` 小分子排除清单 → `2` 多组分盐单列不中和 → `3` 中性短路 → `4` 原子图/键级/同位素/立体/自由基/组分数全不变量保护 → `5` 净电荷只降不升、禁止 0→非0 或符号翻转 → `6` 同源 CXSMILES 幂等往返）。
   - **明确不合并的小分子排除清单**：碳酸体系（`CO₂ / HCO₃⁻ / CO₃²⁻`）、`NH₃ / NH₄⁺`、`CN⁻ / HCN`、`SCN⁻ / HSCN`、`H⁺ / H₃O⁺`。
   - **不可变性**：`evaluation.py`、`s5b_scoring.py`、`score_disclosure_v4cn.py` 已在 `v44` 仓内钉死三份 SHA256；日后若需任何判据改动，必另立 `v7` 并重新登记。
2. **三层并存与互不混合**：
   - 反应预测 / 降解路径分支主指标为 **`v6` Hit@1 / Hit@3 / Hit@5 参考命中率**；完整答卷 Likert V0.5 与五层程序分归基模评测与程序分线。三者单独列报，不平均、不换算、不合成总分。
3. **五态路线状态与专家复核红线**：
   - 路径分支已通过 [`route_status.py`](../src/pathway_v43/pollutant/route_status.py) 正式实现五态伴随输出（完全正交，不动主判分器）。
   - 在 `v1.4 T1-6` (`[biosysmodb121·调参集 N=261]`) 上，`IN_GOLD_EXACT = 141`、`IN_GOLD_PARTIAL = 0`，全部未经专家复核的 `120` 道未命中题均 fail-closed 记为 **`UNRESOLVED`（科学层 `NE`，不记 `0`）**；`OUTSIDE_GOLD_PLAUSIBLE` 仅可由师姐 / 专家确认后产出并强制记 **`NE`**；`OUTSIDE_GOLD_CONTRADICTED` 必须附专家确认及非空化学矛盾证据才可记 `ZERO`。
4. **失败题双口径处理**：
   - 保守留分母为主口径，所有含非零失败或无事件的批次（如 `[dev-298 N=196]` 的 `2` 题无事件、`Paper Ablation DB-1` 的 `23` 题无事件、`BioTransformer` 的 `13/22` 题 `EMPTY`、`gpt-5.6-luna` 试点的 `1` 题 JSON 错）均已按**主口径 + 敏感性口径并报**（见 [`failure_dual_denominator_table.tsv`](review_evidence/v6_caliber_supplement_2026-11-21/failure_dual_denominator_table.tsv)）。

---

## 三、更新后的验收清单认领表（明确“已实现 / 待联合开展”并指定唯一 Owner）

| # | 来信交付物 | 更新后认领与实现状态 | 唯一责任人 / 对接方式 |
| :-: | :--- | :--- | :--- |
| **1** | 评分器 v2 schema（`route_status` 等） | **已实现**（路径线伴随五态 `route_status.py` + `delivery_status` + `zero_reason` + 19 项单测；五层程序分侧字段由程序分线按同一契约对接） | 路径线：**弓赛**（已落码并交单测）<br>五层程序分扩展：程序分线 |
| **2** | `v1→v2` 映射表 | **移交唯一 Owner 负责**（路径线自身 `scorer-1/2→v4→v6` 映射见补件 §2） | **基模评测与 Likert 线负责人（GitHub: `bgruiiii`）**† |
| **3** | 对称性审计 | **已满足**：`v6` 参考/预测双侧对称且同走 CXSMILES 身份机；[`test_v4cn_guards.py`](../tests/unit/test_v4cn_guards.py) 12/12 通过 | **弓赛** |
| **4** | 分桶与分母报告 | **已满足**：全集/调参/Clean-220/剔除清单分列；工程失败/无事件留主分母 + 剔除敏感性双口径并报 | **弓赛** |
| **5** | 校准集（30–50 题三态复核） | **待与师姐 / 领域专家联合开展**：五态 schema、专家复核结构化记录校验及 `120` 题 `UNRESOLVED` 待核池均已程序化就绪（未复核前一律记 `NE`，不自动记 `0`） | **师姐 / 领域专家**（化学仲裁）+ **弓赛 / `bgruiiii`**（联合抽样与混淆矩阵汇总） |
| **6** | `program_vs_likert` join | **移交唯一 Owner 负责**；路径线已交付 `Tuning-261` `qid → Hit@k` 与 `Tuning-76` `case_id → Hit@k` 对接表 | **基模评测与 Likert 线负责人（GitHub: `bgruiiii`）**† |
| **7** | 变更日志 | **已满足**：冻结登记含版本号、提交号、三份 SHA256、重算表与 delta 规则 | **弓赛** |

> † 说明：关于第 2、6 项的唯一 Owner，目前暂署名为**「基模评测与 Likert 线负责人（GitHub: `bgruiiii`）」**，待其本人确认实名后一并补注。

---

## 四、请老师确认

1. 8 项补件与仓内冻结锚点（组织仓 `v44` 分支）核对无误后，**`ppv1-criteria-v6` 可否正式从「内部口径」转为反应预测 / 降解路径分支的「正式口径」**（`v4` 保留于历史附录）？
2. 预注册草案 [`PREREG_MULTI_REFERENCE_HITK_DISCLOSURE_2026-11-21.md`](PREREG_MULTI_REFERENCE_HITK_DISCLOSURE_2026-11-21.md) 所锁定的 Tier-1 参考库版本、排除未审核文献路线及同分母不回写规则是否同意签批开启计算？
