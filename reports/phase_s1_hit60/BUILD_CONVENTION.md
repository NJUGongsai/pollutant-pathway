# BUILD_CONVENTION — EC298 HIT60 S1 / v4.3 dev 题卷构建口径（预注册）

登记时间：2026-09-29（构建执行前登记，先登记后执行）
工作区：`/usrdata/EnzymeCAGE_data/workspaces/v43_hit60_d2_question_assembly_20260929/`
性质：本文件为预注册纪律文件。口径一经登记，执行阶段只做确定性投影与登记内的审计/排除，不做任何"化学合理化"改写；质量复核属于下一代理。

---

## 0. 任务定义

考题为"底物 → 降解产物"单步预测（不是酶排序）。题源主体为 B1（BIOSYSMOdb 121 拆步冻结包，121 formal pathways / 533 step occurrences / 460 去重 directed reactions）。只使用 B1 包内 `B1/` 正式文件；`B1_attempts/crash*`、`crosswalk_work/` 为开发证据，一律不读。quarantine 29 题、127/126 旧口径不使用。

## 1. 题面（root_smiles）投影规则

- 数据源：`B1/step_participants.tsv`（2473 行；`participant_side` 为方向修正后的定向侧）。
- 候选题 = 每个 step_occurrence（共 533 个）。
- 题面候选 = 该 step 中 `role_label == MAIN_SUBSTRATE` 的参与者（533 个 step 全部 ≥1，16 个 step 恰有 2 个）。
- 辅因子过滤：从题面候选中剔除命中注册辅因子表（§5）的参与者。
- 剔除后必须恰好剩 1 个，否则整题排除：
  - 剩 0 个 → `root_is_cofactor`；
  - 剩 ≥2 个 → `multi_main_substrate`。
- 剩 1 个即 root：取其 `isosmiles` 原串；`isosmiles` 为空时回退 `canonicalsmiles`；两者皆空 → `root_unparseable`。
- root 必须可被 RDKit 解析（含价态检查），否则 `root_unparseable`；必须含碳，否则 `root_no_carbon`。
- `cleaning_status`（CLEANED_MODEL_OK / FULL_EMPTY_STRUCTURE / HOLD）不作为构题门——它描述模型侧清洗反应 SMILES 的可构造性；本构题只依赖题面/金标参与者自身 SMILES 的质量门。

## 2. 金标（gold products）投影规则

- 金标候选 = 该 step 中 `role_label == MAIN_PRODUCT` 且 `participant_side == PRODUCT` 的参与者。
- 逐产物门：
  - SMILES 取 `isosmiles`（空则回退 `canonicalsmiles`）；不可解析 → 该产物不入金标（登记进省略口径表）；若金标因此为空 → `gold_unparseable`；
  - 必须含碳（规则④）：无碳的 MAIN_PRODUCT 不入金标（登记进省略口径表）；若金标因此为空 → `gold_no_carbon`；
  - **不得剥离主产物**（规则①）：金标 SMILES 原样保留，包括酰基-CoA 硫酯等长 SMILES，不做任何截断/简化。
- 多产物并列语义（规则③，显式登记）：金标 = 全部通过上述门的 MAIN_PRODUCT 集合，语义为**同步产物清单**（co-product list：金标是该步全部主要有机产物的集合；判分口径由后续阶段决定，本阶段只冻结清单）。不采用"备选答案"（either-or）语义。
- 同题金标内重复：按 SMILES 精确串去重（保序）。立体异构体（同 cn 不同精确串）视为不同产物条目，不去重。
- 排序：按 `participant_ordinal_in_step` 升序（同值按 `participant_position`），确定性输出。

## 3. 共生产物省略口径表（规则②）

每题在审计留痕中登记全部**产物侧但未入金标**的参与者：字段 = name / role_label / SMILES / 省略原因（cofactor_currency / redox_carrier / solvent_small_inorganic / byproduct / no_carbon_main_product / unparseable_main_product）。含 AMP、ADP、NAD+、NADP+、FAD 等辅因子共生产物。该表存远端 `intermediate/`（含 SMILES，远端不受限）；拉回本地的文件一律不含金标 SMILES，辅因子以"名称+分子式"表示。

## 4. 题目主键

- `qid = "b1_" + step_occurrence_id`，其中 `step_occurrence_id = <case_id>__S<NN>__<reaction_id>`，天然保留 case 与 step 两级（例：`b1_BIOPATH150_001__S01__BSY-r00594`）。
- 反应层去重数（460，`raw_full_directed_unique`）单独上报，不改变题目主键粒度。

## 5. 注册辅因子表（题面安全网；B1 role_label 为主判据，本表为兜底）

匹配机制：名称匹配（小写化、剥离 `(n±)` 电荷后缀与 trianion/dianion/anion/cation 字样后全等）或 SMILES 匹配（cn_identity 同构，仅用于小分子无机/通用条目）。
名称表：NADH、NAD+、NADPH、NADP+、FAD（含 FAD trianion）、FADH2（含 dianion）、FMN、reduced FMN、FMNH2、ATP、ADP、AMP、焦磷酸/正磷酸、CoA（游离辅酶 A，**不含酰基-CoA**——酰基-CoA 属底物衍生硫酯，可作题面与金标）、PAPS、PAP、SAM、SAH、GSH、GSSG、H2O、O2/dioxygen、CO2、碳酸氢盐/碳酸、H+、OH-、NH4+/NH3、H2O2、硫酸/硫酸氢盐。
SMILES（cn 口径）表（本地入仓版以名称+分子式表示，SMILES 原文见远端工作区 `scripts/common.py` 的 `_COFACTOR_SMILES`）：水 H2O、氧气 O2、二氧化碳 CO2、碳酸 H2CO3、氢离子 H+、氢氧根 OH−、铵根 NH4+、氨 NH3、过氧化氢 H2O2、正磷酸 H3PO4、焦磷酸 H4P2O7、硫酸 H2SO4、硫酸氢根 HSO4−。
注：nicotinamide（烟酰胺）不在表内——它是烟酰胺酶的真实降解底物（含碳有机小分子），不属于本表"无机/通用小分子辅因子"。

## 6. 去重规则

- 投影层去重 key =（root 的 cn_identity，金标 cn 集合的有序序列）。
- 同 key 多题 → 保留 `step_occurrence_id` 字典序最小者为代表，其余排除，原因 `dup_projected_question`。
- RHEA 盲测候选与 B1 可用池跨源去重：同 key 时保留 B1 版本，RHEA 侧排除，原因 `dup_cross_source`。

## 7. 排除规则汇总（漏斗口径）

对每个候选题依序判定，首个命中即定档（逐题留痕于 `intermediate/audit_b1.jsonl` / `audit_rhea.jsonl`）：

| 序 | 排除原因 | 说明 |
|---|---|---|
| 1 | `root_is_cofactor` | 题面候选全为注册辅因子 |
| 2 | `multi_main_substrate` | 辅因子剔除后仍有 ≥2 个 MAIN_SUBSTRATE |
| 3 | `root_unparseable` | 题面 SMILES 不可解析/缺失 |
| 4 | `root_no_carbon` | 题面不含碳 |
| 5 | `gold_unparseable` | 金标产物全部不可解析 |
| 6 | `gold_no_carbon` | 金标产物全部不含碳 |
| 7 | `dup_projected_question` | 投影层去重非代表 |
| 8 | `overlap_old298` | 见 §8.1 |
| 9 | `overlap_train` | 见 §8.2 |
| 10 | `leaked` | 见 §9 |

漏斗口径：533 → 可构题 N1（序 1–6 通过）→ 去重后 N1'（序 7）→ 重叠排除 N2（序 8–9，先到先得）→ 泄漏排除 N3（序 10）→ 可用 N4。

## 8. 重叠审计（预注册维度，逐题留痕）

### 8.1 旧 298（对照源：`pollutant298_three_model_reaction_benchmark_freeze_20260921`）

旧 298 化学宇宙 = REACTION_BLIND 298 题面 ∪ PARENT_UNION_BLIND 206 题面（公开盲面；已验证并集不引入新题面）∪ REACTION_PRODUCT_GOLD 全部 accepted_products（216 个去重产物；已验证 PARENT_UNION 金标产物为其子集）。
命中（精确串或 cn 口径，任一成立）即标 `overlap_old298` 并移出：
- 正向：root ∈ 旧 298 题面宇宙；
- 反向：root ∈ 旧 298 金标产物；
- 金标侧反向：任一金标产物 ∈ 旧 298 题面宇宙。

### 8.2 训练 run（对照源：`enzymecage_v6_298_rhea142_brenda_enzgfm650m_retrain_20260922`；train/valid/test 三个 split CSV 的全部 CANO_RXN_SMILES 去重后 5770 条有向反应；能力范围内口径）

- 底物层（移出判据，精确串或 cn 任一）：root ∈ 训练反应任一组分（底物侧 ∪ 产物侧的全体分子）→ 标 `overlap_train`（layer=substrate_layer）。
- 反应层（留痕计数）：存在训练反应 T 使 root ∈ 底物侧(T) 且存在金标 g ∈ 产物侧(T) → layer=reaction_layer（底物层已覆盖其移出；用于报告强度）。
- 训练反应反向（root ∈ 产物侧(T) ∧ 金标 ∈ 底物侧(T)）仅留痕（`train_reverse_reaction_note`），不单独移出。
- 序列 SHA 层与本考题无关（产物预测题不含酶序列面），不做。

## 9. 泄漏审计（对照源：v1 检索语料 `dependingv3/assets/corpus_env/corpus_v1.jsonl`，43177 条：envipath 6077 + rhea 37100；42595 条含产物侧）

双口径 = 精确串 + cn_identity 规范化；命中域 = donor_A_smiles / donor_components / product_B_smiles / product_components。
移出判据（配对级泄漏，`leaked`）：
- 正向：同一记录内（root 命中 donor 侧）∧（任一金标命中 product 侧）；
- 反向：同一记录内（任一金标命中 donor 侧）∧（root 命中 product 侧）；
- 精确串或 cn 任一口径成立即命中。
覆盖度：全部候选题做全量语料扫描（43177 条，无抽样）。另如实报告单侧计数（root_only_hit / gold_only_hit）；单侧命中不移出（检索语料天然包含常见代谢物，只有"题面→金标"配对可直接检索才构成答案泄漏）。

## 10. 划分规则（dev / 盲测预留）

- 可用池 N4 = 通过 §7 全部门与审计的 B1 题。
- 若 N4 < 50 → 阻塞（停止冻结并上报）。
- dev 规模 = min(75, N4)；若 N4 ∈ [50,75) 则 dev=N4 并上报预留池为空。
- 抽样程序（确定性）：`order = sorted(qids)`；`rng = random.Random(20260929)`；`rng.shuffle(order)`；`dev = sorted(order[:dev_size])`；`blind_reserve_b1 = sorted(order[dev_size:])`。
- 盲测预留池 = blind_reserve_b1（qid 清单+计数）+ RHEA 可用题（§11，同口径转换+同样审计）qid 清单。本阶段只登记清单与计数，不构完整盲卷。
- BRENDA extra-213：默认排除（已知 accession 拆分/表示分歧 bug；FINAL_STATUS 为 NOT_RUN；envelope 报告 613 处 canonical 分歧）。可用性评估结论记入 PREFLIGHT_REPORT，不入池。

## 11. RHEA broad-87 盲测候选转换（同口径）

- 题面 = `RHEA142_BROAD87_PARENT_BLIND.tsv` 的 parent_smiles（85 题，单底物，无 multi 门）。
- 金标 = primary-product 补丁 `RHEA142_BROAD87_PRIMARY_PRODUCT_GOLD.jsonl`（SUBSTRATE_DERIVED_PRIMARY_TRANSFORMATION_PRODUCTS_ONLY 策略）的 accepted_products，套用 §2 各门（可解析、含碳、不剥离、多产物=同步产物清单、精确串去重）。
- 题面门：可解析、含碳、非注册辅因子；qid = `rhea_` + case_id。
- 依次套用 §6 去重（含对 B1 可用池的跨源去重）、§8 重叠审计、§9 泄漏审计；通过者入盲测预留池（只登记 qid 与计数）。

## 12. 冻结产物（远端 `freeze/`，全部算 SHA256）

1. `dev_questions.jsonl`：qid / root_smiles / root_smiles_sha256（root_smiles UTF-8 串的 SHA256 hex）。
2. `dev_gold.jsonl`（敏感）：qid / products_smiles[]。
3. `split_manifest.json`：种子、抽样程序、漏斗各计数、排除明细、输入资产 SHA、冻结文件 SHA。
4. `BUILD_CONVENTION.md`（本文件）、`PREFLIGHT_REPORT.md`。
5. `intermediate/`：candidates_b1.jsonl、candidates_rhea.jsonl、audit_b1.jsonl、audit_rhea.jsonl（逐题留痕，含共生产物省略口径表）、blind_reserve_qids.json。

## 13. 复跑与复核

- 所有脚本在 `scripts/`，纯 CPU、零 LLM、零费用；远端源目录只读，产出只写本工作区。
- 复跑：`bash scripts/run_all.sh` 从冻结输入重建全部产物。
- 复核：`python scripts/05_verify.py --check` 重算漏斗计数、dev/预留划分与逐文件 SHA，与 `freeze/` 内登记值比对，输出 PASS/FAIL。
- 规范化口径统一 import 仓内 `pathway_v43.domain.identity.cn_identity`（与判分同源；IDENTITY_VERSION=cn-v1）。

---

> 本地入仓版说明：本文件与远端 `freeze/BUILD_CONVENTION.md`（sha256 cbaf784f…43ae）唯一差异为 §5 的辅因子 SMILES 清单已按纪律替换为"名称+分子式"表示；构建与审计执行均以远端版本为准。
