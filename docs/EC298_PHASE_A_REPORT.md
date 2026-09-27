# EC298 Phase A 报告:同口径重评分与离线归因(v43-ec298-scorer-2)

> 任务书:[`TASK_V43_EC298_PHASE_A.md`](TASK_V43_EC298_PHASE_A.md);主报告(修正口径):[`EC298_REPORT.md`](EC298_REPORT.md);独立复核依据:[`EC298_REVIEW_R2.md`](EC298_REVIEW_R2.md)、实施首轮 review:[`EC298_PHASE_A_REVIEW.md`](EC298_PHASE_A_REVIEW.md)(R1,三处 P1 已在本版修复)。
> 本报告与 `reports/ec298/phase_a_v2/` 全部产物仅由封存首跑数据离线计算:零 API、零 298 引擎/agent 重跑、零预测代码修改;金标只在离线评分/归因进程打开。
> 实施日期:2026-09-27(R1 修复同日,R2 两处 P2 防护补齐)。生成脚本:`scripts/ec298_phase_a.py`(43 项锚点自动对账;输入清单双向校验,初始化与复算分离;score_v2.json 与含 rank TSV 自动对账)。R1 review 前的 17 个产物文件及其哈希保留在 `phase_a_v2/r1_snapshot/`。

## 0. 摘要

1. **测量修正先行**:v1(scorer-1)引擎臂直接使用缓存的 `product_identity` 对金标,agent 臂却从原始 SMILES 现算 `cn_identity`,两臂不同口径。v2(scorer-2)两臂统一从原始候选 SMILES 现算身份后:agent **116/128/130**,引擎 Top-10 **118/174/193/209**,同 K 净差 **−2/−46/−63**。逐题对账:引擎首命中 rank 变化 **68**(56 新命中 + 12 移位 + 0 丢失),agent rank **298/298 不变**。
2. **"完整候选池"三档撤回**:`pool_identities` 仅由 `top_k=10` 返回值填充;v2 只称"已导出 Top-10 内(209)/外(89)",89 题不是"完整池真空"。
3. **@5 差距 63 题的构成**(证据五层分层后;原始检索含金标≠可用候选):engine-only 82 题的**原始检索产物** 82/82 含金标——这只是原始检索重叠,**不证明**该卡能过结构门禁、进入任务或可报告;其中 22 题的模型选择集(任务候选)存在含金标 recorded 卡未选,标"模型选错"(有资格证据);其余 60 题中 40 题证据不足(35 条仅原始检索含金标、5 条候选集无正确选项),如实标"证据不足以判断";空答 20 条为类比弃答 14 / 编辑拒绝 6。agent-only 19 题全部来自 `novel_proposal`,标签限定为"候选未检出(引擎已导出 Top-10)",其中 14 题原始检索卡含金标(未证实可用,只进事实列)。
4. **调用账**:191 次 issued 与请求账对平(186 成功 / 5 失败 / 0 孤儿,按完整 task 路径+attempt 配对);51 条空答(50 awaiting_prediction + 1 budget_exhausted)全部闭环核验为 28 弃答 + 23 编辑拒绝。

## 1. 口径异议说明(向老师提出的修正)

老师任务引用的 `agent @1 +34`、引擎 Top-10 153、真空 145、`@5` 净差 −5、"新引擎比旧引擎弱 36 题"等前提,均来自 v1 scorer 的**引擎身份不对称**(`exam.py::_engine_chunk` 优先取引擎缓存 `product_identity`,可能保留电荷;金标已经 `cn` 归一化)+ `pool_identities` 被误当完整池。独立只读重算、两臂均从原始候选 SMILES 求 `cn_identity` 后,校验锚点为:

| 口径 | agent @1/@3/@5 | 引擎 @1/@3/@5/@10 | 说明 |
|---|---|---|---|
| **v2(正式)** | **116/128/130** | **118/174/193/209** | 两臂同函数;本报告与主报告全部数字 |
| v1(已废弃) | 116/128/130 | 82/117/135/153 | 引擎身份不对称所致;仅作审计线索 |
| 历史错误口径档 | — | 153/0/145 | "完整池三档"不成立(池=Top-10) |

历史 v4.1 引擎为 118/172/190(封存判分件仅记 ≤5;@10=208 引用历史报告),与新引擎汇总接近但逐题首命中 rank 有 **24 题**不同,不能宣称版本等价;**"82 对 118 的资产域偏移"在 v2 口径下没有前提**,不写入报告。若老师仍需按旧口径另附切片,将标为 `v1_invalid_identity_diagnostic`,不与 v2 混算。

## 2. 输入、封存性与复现

- 唯一预测输入:封存 `runs/ec298_v43r1/`(agent 答卷 `merged/predictions.jsonl`、引擎 `engine_arm/engine_results.jsonl`、逐题 run/decision/validation/model-call 产物、`exam_inputs.jsonl` 白名单);金标只读 `ec298_gold_readonly/questions.jsonl`;v1 评分 `scoring/per_question_scoring.json` 仅作对账。
- **逐文件 SHA256 清单**:`phase_a_v2/input_manifest.json`(**4,664 条角色条目 / 4,663 个不同物理文件**:run 目录 4,660 项 + 金标 + v4.1 判分件 + 资产库各 1 项;v1 评分文件既在 run 目录内又单列一次,故两种计数相差 1),生成于远端、拉取后逐文件比对一致;`scripts/ec298_phase_a.py` 的**初始化与复算分离**:清单只能用 `--init-input-manifest` 在核验过的封存副本上一次性建立,已存在时严禁覆盖;正常复算缺清单即失败,且校验是**双向的**——磁盘文件集合与清单一一对应,少文件、多文件(包括新增会被扫描的结果文件)、改任一字节或换资产库都立即失败,不存在"重建清单接受变化"的路径。资产库 `library_full.jsonl` 已列为受保护角色 `asset_library`。
- 衍生输出只写 `phase_a_v2/`;封存目录零写入。脚本不包含任何主机地址、凭证或私密路径;输入路径全部命令行显式传入。
- 零网络复算命令见主报告 §6;`python -m pathway_v43.exam_v2 …` 与 `python scripts/ec298_phase_a.py …` 均可从相同输入字节复现相同输出字节(正式逐题评分 `score_v2.json` 内封存三输入的 SHA256,并与各 TSV 逐题回读对账)。

## 3. A0:同口径重评分(scorer-2)

| 指标(分母 298) | agent | 引擎 Top-10 | 净差 |
|---|---:|---:|---:|
| hit@1 | 116 (38.9%) | 118 (39.6%) | −2 |
| hit@3 | 128 (43.0%) | 174 (58.4%) | −46 |
| hit@5 | 130 (43.6%) | 193 (64.8%) | **−63** |
| hit@10 | 130(宽度上限) | 209 (70.1%) | −79* |

逐题配对 @5:both 111、agent-only 19、engine-only 82、neither 86(111+19+82+86=298)。**正式逐题评分文件 `score_v2.json` 已交付**:scorer 版本 + 三输入 SHA256 + 298 行逐题 agent/engine rank + 汇总与配对四分;脚本写盘后回读该文件与内存结果对账,并**自动回读全部含 rank 的 TSV 逐题对账**(六类文件、缺失/行数/任一取值不符即失败,见 `scripts/ec298_phase_a.py::verify_score_v2_against_tsvs`);引擎结果文件显式传入时严格要求存在、非空且 qid 集合与金标完全一致(空文件亦失败)。

v1↔v2 差异(`score_v1_v2_diff.tsv`,298 行):引擎 rank 变化 68(56 新命中/12 移位/0 丢失),每处差异可回到触发候选的原始 SMILES、缓存身份与重算身份;agent 0 变化。Top-10 两档:**209 + 89 = 298**。

**多组分敏感性(探索性,非主结果)**:18 条 agent 候选含 `.`(引擎 34 条,受影响 28 题)。整条候选主分数照旧;"任一组分命中"两臂同法:agent 129/141/143,引擎 132/184/199(引擎 @10=214),与主分数分离呈现。正式组分口径若要变更,须另立 scorer 版本并书面决定。

## 4. A1:引擎 Top-10 切片中的 agent 命中(`agent_hits_by_engine_tier.tsv`)

| tier | 题数 | agent @1/@3/@5 |
|---|---:|---|
| engine_top10_hit | 209 | 111 / 114 / 114 |
| not_in_exported_top10 | 89 | 5 / 14 / 16 |
| 合计 | **298** | 116 / 128 / 130 |

- 每题含两臂首命中 rank、agent 命中候选原始 SMILES、命中来源(裁决账本 evidence_id/report_rank/证据类型/文件引用)。**130 个 agent 命中全部追溯到裁决账本条目(130/130 可回查)**。
- 89 题档中 agent 命中的 **16 题**全部为 `novel_proposal` 模式;此档仅说明"已导出 Top-10 未命中",Top-10 外是否存在引擎候选**未知**,不得称为"真正无证据泛化"。
- `novel_proposal` 的证据状态单列:50 题**全部**属于"有检索产物但映射失败"(`retrieval_products_present`),0 题为"无检索产物";44/50 的原始检索卡含金标。
- 如需回答"完整池真空",须确认封存件另有真实全池并能核实生成时点与 SHA——本阶段确认为无,报告 `unknown`;未为补档重跑引擎。旧 v4.1 的 0/39 档与本 Top-10 未命中档不可比。

## 5. A2:50 条 awaiting_prediction 的命运(`awaiting_prediction_fates.tsv`)

- 行数:**50 行 awaiting_prediction + 汇总单列 1 行 budget_exhausted = 51 条空答闭环**;每题 v2 命中均为空(与答卷一致)。
- 结局核验(持久 prediction/decision 产物,非空答反推):**28 条模型显式弃答(abstained)+ 23 条编辑拒绝(rejected)**。51 题均无 `validation.json`(未产生可验证产物,属预期);拒绝题的 AtomTool 检查项(target_molecode / edit_references)与拒因逐题列自 prediction payload。
- 调用账(按题):awaiting 50 题 issued 52(48 题 1 次 + 2 题 2 次),成功 50 / 失败 2;budget_exhausted 题 issued 3、成功 1、失败 2(耗尽的是 worker 预算,3 次调用均有账目)。空答合计 issued 55 / 成功 51 / 失败 4。
- **孤儿审计 = 0**:逐题核对 `prediction_call.aN.json ↔ prediction_response.aN.json`,配对键为完整 task 目录 + attempt,**attempt 以 `payload.attempt` 为准并逐条与文件名 aN 交叉核对**(错配计入 `attempt_mismatch_count` 且错配对不抵消);无调用缺响应、无响应缺调用、**payload/文件名错配 0**。
- 含 `bond_already_present` 的拒绝不等同"本可命中";目标是否匹配金标仅作离线诊断,见 A4 与 R2 §4。

## 6. A3:决策路径贡献(`decision_path_contribution.tsv` + `_detail.tsv`)

分组按**持久 decision_log**(`decision.json` 的 prediction_mode/outcome)与 prediction payload 交叉核对,不以预测 SMILES 倒推模式;`mode_source_agrees` 全部一致(0 处分歧)。

| 组(实际分支与结局) | 题数 | agent @1/@5 | 引擎 @1/@5 | @5 配对 both/agent/engine/neither |
|---|---:|---|---|---|
| 唯一 recorded,直接提交 | 112 | 64 / 64 | 64 / 86 | 64/0/22/26 |
| 多 recorded,模型选一个(rank_candidates) | 70 | 27 / 27 | 27 / 54 | 27/0/27/16 |
| 类比编辑:弃答 | 28 | 0 / 0 | 7 / 14 | 0/0/14/14 |
| 类比编辑:提案被拒 | 23 | 0 / 0 | 1 / 6 | 0/0/6/17 |
| 类比编辑:提案接纳 | 15 | 0 / 0 | 4 / 9 | 0/0/9/6 |
| 新提案:接纳(novel_proposal) | 50 | 25 / 39 | 15 / 24 | 20/19/4/7 |
| **合计** | **298** | **116 / 130** | **118 / 193** | 111/19/82/86 |

锚点对账:模式题数 112/70/28/23/15/50;类比内结局 28/23/15;agent @1 分解 64+27+0+25=116,@5 分解 64+27+0+39=130——与任务书/R2 锚点完全一致。类比三组合计 66 题 agent 0/66;agent 独有 @5 命中全部来自新提案分支。

## 7. A4:@5 损失与输出宽度(`hit5_paired_attribution.tsv` + 两个筛选视图)

- 298 题一题一行;discordant:**engine-only 82、agent-only 19,净差 −63**(不是"找 5 道丢失题";rank 9–10 本就不计入引擎 @5,不能把 @5 差距解释为五位被十位挤出)。
- 宽度分布:0 个 51 题、1 个 197 题、2 个 1 题、3 个 1 题、4 个 5 题、5 个 43 题——197 题只报一个产物,"有效宽度不足"如实披露。
- **证据五层**(逐题列布尔与引用,下层成立不推出上层):`raw_retrieval_gold`(原始检索卡含金标,未经任何门禁)→ `task_candidate_gold`(预测任务候选=模型选择集的 recorded 卡含金标)→ `selected_gold`(被选中证据产物含金标)→ `validated_reportable_gold`(validation 判 accepted 的产物含金标)→ `reported_gold`(最终裁决账本可报告产物含金标)。
- engine-only 82 题:原始检索层 82/82 含金标——**这只是原始检索产物重叠,不能表述为"损失不在检索覆盖率"或"可用候选覆盖"**;其中仅 22 题上升到任务候选层(模型选择集里存在含金标 recorded 卡未选),其余 60 题缺可用性证据。
- 主因标签(一题一个主因;规则只允许有资格证据的标签;事实列保留完整层次,不确定保留):

| 主因标签 | 题数 | 资格证据 |
|---|---:|---|
| 证据不足以判断 | 40 | 35 条仅原始检索层含金标(未证明过门禁/进任务/可报告)+ 5 条任务候选层无正确选项;不外推任何"可报告"断言 |
| 模型选错 | 22 | 任务候选层(模型选择集)存在含金标 recorded 卡,模型未选;`task_candidate_gold_refs` 可回查 |
| 类比弃答 | 14 | 空答 + outcome=abstained,引擎 @5 有命中 |
| 编辑拒绝 | 6 | 空答 + outcome=rejected,引擎 @5 有命中 |
| 候选未检出(引擎已导出 Top-10) | 19 | 全部 agent_only;标签写全限定对象——仅指已导出 Top-10,外池未知;其中 14 题 agent 原始检索卡含金标(未证实可用,只进事实列) |
| 候选检出但未报告 / 候选虽报告但身份不匹配 | 0 | 本卷未触发;词表保留(需已验证/可报告层证据才可使用) |

## 8. A5:基线差异与资产重叠(`v41_baseline_diff.tsv`、`asset_exam_overlap.tsv`)

- 新引擎 118/174/193/209 vs 历史 v4.1 引擎 118/172/190(封存 v4.1 判分件仅记录 ≤5 的 baseline_rank;@10=208 引用历史 v4.1 报告,封存件无法离线复算 6–10 位)。逐题首命中 rank 差异 **24 题**(同 R2 比法)——汇总接近**不能宣称版本等价**。
- 资产重叠(描述统计,扫描文件 `assets/v3_reactions/library/library_full.jsonl`,SHA256 `042e9e2c…67f3`,与封存 run_identity 的 `source_file_sha256` 一致;4,454 条记录,0 条底物不可解析):
  - 底物身份重叠:**182/298 题**(61.1%)的底物 cn 身份出现在资产库 donor_smiles;
  - 底物-金标产物对重叠:**113/298 题**(37.9%)在同一底物身份下存在产物 cn 身份等于金标的记录;
  - 反应规则覆盖:**not_assessed**(规则资产匹配语义未在本阶段核实);
  - 重叠率**不能**单凭证明性能差异的因果来源;检索/引擎对资产的实际使用方式未在此核实。

## 9. A6:模型调用分布(`llm_call_distribution.tsv`)

- 逐题 issued/成功/失败/响应文件/request_id/孤儿/attempt 错配;**总 issued=191,提供方正常响应 186,失败 5,孤儿 0,payload.attempt 与文件名错配 0**——与封存调用账对平。
- 两套口径:issued=持久 `prediction_call.*.json`(status=issued);提供方口径=对应 `prediction_response` 的 transport(ok=200 计成功,其余计失败)。本卷两口径总数一致(191=186+5),无差值需解释。
- issued 分布(按题):**0 次 112 题、1 次 182 题、2 次 3 题、3 次 1 题**;触顶(达单任务尝试上限 3)1 题,即 budget_exhausted 题(3 次调用均有响应,耗尽的是 worker 预算)。调用分布按 qid 统计,不以 191/298 平均替代。
- 5 次失败全部为 timeout/传输类(0 次 429);33/40 在途峰值属原运行验收事实,本阶段只引用。

## 10. 数据字典(TSV 列名与空值语义)

通用:TSV 为 UTF-8、制表符分隔、首行列名;空串=不适用/未发生;rank 类列空=该臂该 K 内未命中;布尔列 `true`/`false`。所有 `*_ref` 列为相对封存 run 目录的路径,可逐题回查。

| 文件 | 行 | 关键列 |
|---|---|---|
| `score_v2.json` | 298 | scorer 版本、口径说明、三输入 SHA256、逐题 agent/engine rank、n_predicted、tier_v2、汇总 @1/@3/@5/@10 与配对四分;脚本自动回读并与六类含 rank 的 TSV 逐题对账 |
| `score_v1_v2_diff.tsv` | 298 | agent/engine rank v1→v2、变化布尔、触发候选原始 SMILES、缓存身份、重算身份、触发位置、note |
| `multicomponent_sensitivity.tsv` | 298 | 两臂 main/sensitivity rank、changed;汇总在 §3(探索性) |
| `agent_hits_by_engine_tier.tsv` | 298 | tier_v2、两臂 rank、命中布尔、命中原始 SMILES、来源(evidence_id/report_rank/kind/ref/ref_ok)、decision 模式/结局/path_id、run_id、novel_evidence_state、gold_in_retrieval_any_card |
| `agent_hits_by_engine_tier_summary.tsv` | 2 | 档位 × agent @1/@3/@5 |
| `awaiting_prediction_fates.tsv` | 50 | stop_reason、mode/outcome、issued/ok/failed、响应文件、request_ids、parsed_present、产物/决策引用、atomtool 两项检查、拒因(≤500 字,全文见引用文件)、submitted、validation_state、v2 rank、orphan_count、attempt_mismatch_count |
| `awaiting_prediction_fates_summary.tsv` | 1 | budget_exhausted 行,同列 |
| `decision_path_contribution.tsv` | 6 | 组×子组、题数、两臂 @1/@3/@5、@1/@5 配对四分 |
| `decision_path_contribution_detail.tsv` | 298 | 逐题组、两处模式来源、一致性、rank、决策/预测引用 |
| `hit5_paired_attribution.tsv` | 298 | paired_hit5、方向、引擎金标 rank、已报来源、selected_evidence、order、**证据五层**(raw_retrieval_gold(+refs)/task_candidate_gold(+refs)/selected_gold/validated_reportable_gold/reported_gold)、未选中含金标 recorded 卡、验证拒因、主因标签、事实列、不确定列 |
| `hit5_engine_only.tsv` / `hit5_agent_only.tsv` | 82 / 19 | 同上筛选视图 |
| `v41_baseline_diff.tsv` | 298 | v2 rank、v41 baseline_rank、changed |
| `asset_exam_overlap.tsv` | 298 | 底物身份、库内底物布尔、记录数、金标对布尔、记录引用(≤5) |
| `llm_call_distribution.tsv` | 298 | issued/ok/failed、响应文件、request_ids、孤儿(按 task 目录+经核对的 attempt 配对)、attempt_mismatch_count、llm_remaining、stop_reason |
| `input_manifest.json` | 4,664 条角色条目 | run_dir(4,660 文件完整集合)/gold/v1_scoring/v41_baseline/asset_library 各角色 relpath+sha256;不同物理文件 4,663 个(v1 评分与 run 目录内同一文件重复计入角色一次) |
| `anchor_reconciliation.json` | 43 项锚点 | expected/actual/ok + 各审计块(含 A4 标签分布与证据层说明) |
| `output_manifest.sha256` | 全部输出 | sha256sum 格式(含 `r1_snapshot/` 内文件,按相对路径) |
| `ec298_report_v1_snapshot.md` | — | v1 报告快照,SHA256 `ca17f674…764d` |
| `r1_snapshot/` | 18 文件 | R1 review 前的 17 个产物 + 当时输出哈希清单,原样保留供审计 |

## 11. 限定与验收状态

1. **封存性**:执行前后本地镜像与远端封存目录逐文件 SHA256 一致;全程零 API、零 298 重跑、零预测代码修改;`exam.py`(scorer-1)未改动。输入清单初始化与复算分离:清单不可覆盖、不可重建,完整文件集合双向校验,"改一个字节/加一个文件/换资产库"均有失败测试钉住(`tests/test_ec298_phase_a_script.py`)。
2. **评分性**:两臂同函数同规则,298/298 对账;qid 重复、引擎 qid 集合不一致(含显式空文件/路径不存在)均 fail-closed;v2 汇总与任务书锚点一致;68 处引擎 rank 变化逐题可回查;agent rank 298/298 不变;正式逐题评分 `score_v2.json` 由脚本自动与六类含 rank 的 TSV 逐题对账(门禁,非人工复核)。
3. **归因性**:A1 档位 209+89、A2 50+1、A3 112/70/28/23/15/50 与 @1/@5 分解、A4 82/19、A6 191/186/5(孤儿按完整 task 目录 + 经 payload.attempt 交叉核对的 attempt 配对 = 0,错配 = 0)全部对账通过(43 项锚点自动核对);A4 标签全部有资格证据支撑,五层证据列逐题可回查,不得从原始检索层推出可报告断言。
4. **报告性**:89 题仅称"已导出 Top-10 未命中";82/82 只表述为原始检索产物重叠;资产重叠与模型模式相关性均为描述统计;含 `.` 口径敏感性与主分数分离;全文无未限定的"模型选错""候选未检出"或 @10 优势声明。
5. R1 review 三处 P1(score_v2.json 缺失、标签证据越层、清单可被重建绕过)与四条 P2(孤儿配对键、scorer fail-closed、报告文案、清单计数)均已修复;复核对照 R1 快照 `r1_snapshot/`。
6. 本阶段为测量与归因,修复优先级(候选裁决架构、类比供体门槛、AtomTool 键级编辑)见 R2 §6 阶段 B/C,不在本任务范围。
