# PREFLIGHT_REPORT — EC298 HIT60 S1 / v4.3 D2 题源预检 + dev 冻结

日期：2026-09-29
工作区：`/usrdata/EnzymeCAGE_data/workspaces/v43_hit60_d2_question_assembly_20260929/`
执行代理：题卷构建代理（S1）；全程 CPU-only、零 LLM 调用、零费用；远端源目录只读。
本报告不含任何金标 SMILES；金标只存在于 `freeze/dev_gold.jsonl`（受限）与远端 `intermediate/` 留痕。

---

## 1. 漏斗一行

**B1：533 步 → 可构题 524 → 去重后 428 → 重叠排除 323（旧298 120 + 训练 203）→ 泄漏排除 49 → 可用 56（dev=56 / 盲测预留=0）**
**RHEA broad-87：85 → 重叠排除 20（旧298 3 + 训练 17）→ 泄漏排除 65 → 可用 0（盲测预留 RHEA=0）**
**BRENDA extra-213：默认排除（已知 accession 拆分/表示分歧 bug，且从未运行过），不入池。**

dev 规模 56 落在 50–100 区间内；**盲测预留池为空**（两源合计 0 题）——这是本次 preflight 的头号发现，详见 §7。

## 2. 资产复验（全部通过）

| 资产 | 登记值 | 复验 | 结论 |
|---|---|---|---|
| B1 121 拆步冻结包 | 6858c165…63f2 / 876022 B | 一致 | PASS |
| 旧 298 三模型冻结题卷 | a404f067…7524 / 114037 B | 一致 | PASS（路径漂移，见下） |
| RHEA broad-87 冻结包 | 847f061e…1606 | 一致 | PASS |
| RHEA primary-product 补丁 | cf09025d…5d2 / 17912 B | 一致 | PASS |
| BRENDA extra-213 | 00eaa634…60e9 / 4743751 B | 一致 | PASS（只读评估，未解包入池） |

**路径漂移（需登记）**：旧 298 tar 的登记路径 `EnzymeCAGE-master/HPC_Inputs/pollutant298_three_model_reaction_benchmark_freeze_20260921.tar.gz` 已不存在；盘上 6 份副本全部字节级一致（114037 B，sha256=a404f067…7524），本次使用 `EnzymeCAGE-master/HPC_Inputs/pollutant298_three_model_blind_run_20260921/` 下的副本（只读）。资产内容无恙，建议资产清单更新路径。

## 3. 构建口径（预注册）

`BUILD_CONVENTION.md` 于执行前登记（sha256 见 §9），要点：
1. **题面** = B1 参与者表中 `MAIN_SUBSTRATE`（方向已修正），注册辅因子表兜底剔除（游离 CoA、NAD(P)H/NAD(P)+、ATP/ADP/AMP、FAD/FMN、PAPS、H2O、O2、CO2 等无机/通用小分子；**酰基-CoA 不算辅因子**，可作题面/金标）；剔除后须恰剩 1 个，否则排除（`multi_main_substrate` 9 题；`root_is_cofactor` 0 题——7 个 step 的辅因子共底物被正确滤除后保留）。
2. **金标** = `MAIN_PRODUCT` 全部含碳可解析产物，**同步产物清单**语义（428 题中 399 单产物 / 29 双产物；dev 56 题中 52 单 / 4 双）；不剥离主产物（酰基-CoA 长 SMILES 原样保留）；辅因子共生产物（AMP/ADP/NAD+ 等）不入金标但逐题登记进"共生产物省略口径表"（`intermediate/audit_b1.jsonl` 的 omitted_coproducts 字段，含 role_label 与省略原因）。
3. **主键** `qid = b1_<step_occurrence_id>`（case+step 两级保留）；投影层去重 key=（root cn, 金标 cn 集合），524→428（96 题重复被并，75 个重复组）；460 反应层去重数为 B1 自报口径，单独上报不改主键粒度。
4. 构题质量门零误伤：root_unparseable=0、root_no_carbon=0、gold_unparseable=0、gold_no_carbon=0（B1 参与者结构质量好）。

## 4. 重叠审计（预注册维度，逐题留痕 `intermediate/audit_*.jsonl`）

**旧 298**（宇宙=298+206 盲面题面 ∪ 216 金标产物；精确串+cn 双口径）：428 题中 **120 题命中**。
- 命中方向拆分（题级）：root∈旧298题面 50、root∈旧298金标产物 68、金标∈旧298题面 51（多命中重叠）。
- 解读：BIOSYSMOdb 与旧 298（EAWAG/污染物谱）共享大量经典污染物与降解中间体（如黄嘌呤类代谢物、常见酚/苯甲酸类），正向与反向（底物↔产物对调）都有实质重叠。

**训练 run v6**（train/valid/test 全部 CANO_RXN_SMILES 去重 5770 条有向反应、4964 个 cn 分子；能力范围内口径）：428 题中 **293 题底物层命中**（其中 189 题同时反应层命中：训练反应底物侧含本题题面且产物侧含本题至少一个金标——即"见过同款反应"）；按注册规则全部移出，漏斗口径下在旧 298 之后又移出 203 题。另有 58 题训练反向反应留痕（不移出）。
- 解读：训练集（298+rhea142+brenda 反应）几乎覆盖了 B1 的全部"常见降解中间体"区段（儿茶酚/黏康酸/CoA 硫酯/黄嘌呤类等），B1 中真正对训练新颖的只有更"边缘"的污染物衍生中间体。

## 5. 泄漏审计（v1 检索语料，双口径=精确串+cn；配对级判据）

语料 `corpus_v1.jsonl` 43177 条（envipath 6077 + rhea 37100；42595 条含产物侧）。**全部候选题全量扫描，无抽样**；索引规模：donor 46166 精确键/42320 cn 键，product 45944/42357。
- B1 428 题中 **328 题配对级泄漏**（同一语料记录内"题面→金标"可直接检索；38 题仅正向、290 题正反向皆有——rhea 双向记录与 envipath 都在）；泄漏源：rhea 195、envipath 38、两者 95。其中与重叠排除相交后，漏斗内实际移出 49 题。
- 单侧覆盖（不移出，仅报告）：题面单侧命中 380/428，金标单侧命中 384/428 —— v1 语料对 B1 化学空间的覆盖面很广。
- RHEA broad-87：85 题中 **84 题配对级泄漏**（83 题泄漏源为 rhea）——broad-87 本就抽自 rhea142，语料里 rhea 源记录直接含其"题面→产物"对。**RHEA broad-87 对任何以 v1 语料为检索底的系统都不是盲测材料**，这是结构性泄漏，不是口径可以修的。

## 6. RHEA 同口径转换结果

85 题全部通过构题门（含碳、可解析、非辅因子；金标用 primary-product 补丁；79 单产物/6 双产物）；旧298 重叠 3、训练重叠 17、剩余 65 题全部泄漏 → **可用 0**。

## 7. 划分与冻结（注册规则下）

- 可用池 N4=56 ≥50（无阻塞）；dev 规模=min(75,56)=56；种子 20260929，`random.Random(seed).shuffle(sorted(qids))` 取前 56；全部 56 题进 dev，**预留 0**。
- dev 构成：56 题 / 36 个 case（占 121 案例的 30%）/ 56 个不同反应；52 单金标 + 4 双金标；18 题的金标（cn 口径）同时是另一 dev 题的题面（通路链式相邻，盲判分时金标不可见，不影响盲性，仅作登记）。
- **预留池为空的稳健性检验（补充分析，非冻结口径）**：若把训练重叠判据放宽为"仅反应层"（任务原文的优先口径），漏斗变为 428 − 120(旧298) − 145(训练反应层) − 86(泄漏) = **77 可用 → dev 75 + 预留 2**。即无论训练判据取严格（底物层）还是宽松（反应层），**盲测预留池都约等于空**。约束瓶颈是旧298 重叠 + v1 语料配对泄漏，而非训练判据选择。冻结仍按注册的严格口径执行（dev=56，最干净）。
- 结论：**B1+RHEA 在预注册卫生标准下无力供养盲测预留池**。盲卷阶段需要（a）新题源，或（b）由下一代理显式决策放宽某一审计口径（审计留痕已支持任意口径重算，`scripts/` 可复跑）。BRENDA 修好 accession 拆分/表示分歧 bug 前不可作为替补。

## 8. BRENDA extra-213 可用性评估（只读，默认排除维持）

- 包完整性 OK（sha 复验一致）；漏斗 2679 → 213（extra213_selected），全合格亲池 711。
- FINAL_STATUS = `PASS_..._NOT_RUN`（从未实际跑过）；envelope 报告 **613 处 canonical 分歧**（与已知 accession 拆分/表示分歧 bug 一致）。
- 结论：**维持排除**。若未来修复表示层 bug，需按本工作区同口径（构题门+重叠+泄漏三审计）重检后另行申请入池。

## 9. 冻结清单（远端 `freeze/`，SHA256）

| 文件 | SHA256 |
|---|---|
| dev_questions.jsonl | 8869cd05cea1a44220f3001f0b6415c6bf97eb5f0122ebc4609aa1c77ab0360c |
| dev_gold.jsonl（敏感） | d285dc0b63546bef3799f71a6065feeaa60bf202a97597b7431b4e4265262f2a |
| split_manifest.json | cbc413edab5f6c240f615a8bd1a3f84fa1ce188c93030795a1eeac01d6ceaa45 |
| blind_reserve_qids.json | d34de19831cd6953c361e2e2f1d1a1a4dd313dd563ab14feebbd5d4e4853083e |
| BUILD_CONVENTION.md | cbaf784f1ef79b50353657d068394433eef44b994ad5e87edd5eb9125b7a43ae |
| PREFLIGHT_REPORT.md | （本文件，见 SHA256SUMS.txt） |

`freeze/SHA256SUMS.txt` 汇总全部冻结文件（含本报告）；`split_manifest.json` 内嵌三个数据文件的 SHA、种子、抽样程序、全漏斗计数与排除明细、五资产 SHA。
dev 题 Gold 的 `dev_gold.jsonl` 已按敏感文件单独拉回本地 gitignored 目录，不入仓。

## 10. 留痕与复跑

- 逐题留痕：`intermediate/candidates_{b1,rhea}.jsonl`（含共生产物省略口径表）、`intermediate/audit_{b1,rhea}.jsonl`（重叠/泄漏命中明细，含匹配记录 id 与方向）、`intermediate/funnel_0{1,2,3}_*.json`。
- 复跑：`bash scripts/run_all.sh`；复核：`python scripts/05_verify.py --check`（25/25 PASS：文件存在性、字段模式、SHA 自洽、种子重放、漏斗算术、dev/预留互斥、全管线重跑一致）。
- 规范化口径：`pathway_v43.domain.identity.cn_identity`（IDENTITY_VERSION=cn-v1，与判分同源）。

## 11. 给下一代理（质量复核）的提示

1. dev 56 题未做任何化学合理化复核——按红线，构建只做确定性投影；金标语义（同步产物清单）与共生产物省略表需要人工抽查（建议优先抽 4 个双金标题与 18 个链式相邻题）。
2. 预留池为空是结构性结果（§7 稳健性检验）；盲卷阶段的题源决策需要用户/上游明确。
3. 旧 298 资产登记路径需更新（§2）。
4. 训练反向反应 58 题留痕（`train_reverse_reaction_note`）未移出，若下一阶段要更严口径可用。
