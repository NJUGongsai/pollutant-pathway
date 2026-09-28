# EC298 首跑 hit@1 失分逐题归因报告(v1)

> **通俗版(人类可读,无术语门槛):[`EC298_HIT1_ATTRIBUTION_REPORT_PLAIN.md`](EC298_HIT1_ATTRIBUTION_REPORT_PLAIN.md)**;本篇为技术版,供复核与审计。
>
> 任务书:[`TASK_V43_EC298_HIT1_ATTRIBUTION.md`](TASK_V43_EC298_HIT1_ATTRIBUTION.md);实施:独立实施会话 2026-09-28。正式口径为 Phase A `v43-ec298-scorer-2`(agent 116/128/130);本报告只做**封存首跑的离线审计与改动对照**,全程零 API、零预测/引擎重跑、零金标回灌;封存镜像与 Phase A/B/C 产物零写入。产物:[`reports/ec298/hit1_attribution_v1/`](../reports/ec298/hit1_attribution_v1/)(清单 `output_manifest.sha256`)。

## 0. 结论概要(先回答任务书问题)

**问题:182 道 hit@1 未命中,失分发生在哪里?哪些原因已被证实?各阶段改动触及哪些断点、效果是否被验证?**

182 题(=298−116)按断点标签分布(一题至多一个主断点,规则见 §2.2):

| 主断点 | 题数 | 性质 |
|---|---|---|
| `eligible_gold_not_selected` | 27 | **已证实**:金标卡在模型当时的真实选择集内且可选,模型排在其后并选了别的卡(22 张 recorded 卡 + 5 张 rank 任务内 rule/analog 卡,全部有模型自述不选理由,位次 2–6) |
| `validation_rejected_gold` | 8 | **已证实**(带明示上限):类比编辑声明目标经运行时确定性解析、整分子 cn 身份匹配金标,却被 AtomTool 编辑门禁确定性拒绝(§4) |
| `selected_wrong_product` | 39 | **已证实**(观察层):选中记录/卡产物不含金标;金标仅见于原始检索层其他卡(未进任务/未被选),是否可用未证实 |
| `reported_at_rank_2_to_5` | 14 | **已证实**:全部 novel_proposal,正确产物已验证并报告在第 2–5 位(9/3/2 道 rank=2/3/4) |
| `retrieval_absence_within_observed_scope` | 33 | **已证实**(范围限定):已封存检索范围内任何层都无金标;完整候选池不存在,不得称「数据库无正确反应」 |
| `validated_but_not_reported` | 0 | 首跑未出现该断点(v1 导出要求可报告=事件产物) |
| `unknown` | 61 | 断点在候选形成/生成阶段,离线不可判:类比弃答 26、类比生成错误产物 14、类比拒绝但声明目标非金标 11、novel 生成错误产物 10;已核实事实照登(金标仅存在于原始检索层等) |

**「8/23 vs 0/23」分歧裁决(§4):8/23 成立。** 本审计以**首跑账本** `target_smiles`(22/23 可解析,且与现解析器逐字一致)+ 正式金标 + `cn_identity` 独立重算:**8/23 整分子匹配**、+1 任一组分匹配、1 运行时不可解析、13 无匹配。Phase C 同日 R3 复核亦已查明其初版 0/23 系**审计脚本题号 bug**(run 名剥 `RXNG_` 前缀而金标保留 → 逐题查找落空)并更正撤回——两条独立路径(首跑账本直读 vs 修正后重放)结论一致。

**改进对照(§5,四状态严格区分)**:目前**没有任何一项改动拥有新 @1 提升证据**——无真实模型冻结 dev 对照(`dev_real_run_not_executed`),无 298 复跑。Phase A 修的是测量(298/298 rank 未变);Phase B 已实施,R1 review 两项 P1 修复后 R2 复核再提两项 P1+一项 P3 亦已修复复测(报告 §10,当前树 356 passed,未见最终通过结论),且其冻结策略规定 selected 恒排第一,对 27 道 `eligible_gold_not_selected` 的 @1 无已测收益;Phase C 已实施,二轮独立复核**暂不通过**(前轮三项 P1 确认修复,新发现 rank 可选原始 analog/rule 卡提交的绕过路径),其对 8 道目标命中题的同输入重放显示 22/23 旧编辑列表在新协议下仍不可执行(必要非充分);Phase D 仍为草案。后验分析不得宣称泛化改善;若复跑已见 298,只能标 `post_hoc_repair_check`。

## 1. 输入、隔离与复现

1. **输入与校验**:全部来自本地封存镜像 `/Volumes/CC/Enzyme_Agent/ec298_phase_a_seal/`(执行前后远端已复验不变,见 Phase A 报告):`dependingv43_dev/runs/ec298_v43r1`(4,660 文件)、`ec298_gold_readonly/questions.jsonl`、v4.1 判分件、资产 `library_full.jsonl`。脚本逐文件双向校验 Phase A 清单 `reports/ec298/phase_a_v2/input_manifest.json`(复用 `scripts/ec298_phase_a.py::verify_input_manifest`:缺/增/任一字节变化即失败,严禁重建清单),并对 `score_v2.json` 的 `inputs_sha256` 与当前文件对账。角色 SHA 见产物 `input_sha256.json`。
2. **锚点对账(全绿)**:298 qid 三方一致(答卷/白名单/金标);182 miss = 298−116;四组 48+43+66+25=182(类比子组 28 弃答/23 拒绝/15 接纳);rank 2–5 恰 14 题逐题对账。任何不符会写 `anchor_mismatch.json` 并以退出码 1 停止(本次未触发)。
3. **零影响声明**:金标仅由本离线脚本读取;未写封存目录、未改 Phase A/B/C 产物、未改任何预测实现/资产/提示词;不涉及 Chenyu 地址、密钥或本机私密路径(路径全部显式传参)。
4. **复现命令**(字节一致,`--check` 复核):

```bash
OMP_NUM_THREADS=1 python scripts/ec298_hit1_attribution.py \
  --run-dir  <seal>/dependingv43_dev/runs/ec298_v43r1 \
  --gold     <seal>/ec298_gold_readonly/questions.jsonl \
  --v1-scoring    <seal>/dependingv43_dev/runs/ec298_v43r1/scoring/per_question_scoring.json \
  --v41-baseline  <seal>/dependingv4_v41/runs/exam298_agent/per_question_scoring.jsonl \
  --asset-library assets/v3_reactions/library/library_full.jsonl \
  --phase-a-dir reports/ec298/phase_a_v2 \
  --out-dir reports/ec298/hit1_attribution_v1
# 复算核对:同命令 + --check(逐字节 + 清单 SHA,双跑实测一致)
```

## 2. 逐题表与断点规则

### 2.1 表字典

`hit1_misses.tsv` 恰 182 行,列=任务书 §2 要求:身份/评分(qid、input_index、run_id、path_id、两臂 rank、金标数/摘要摘要 `gold_ids_digest`、首位候选原文与身份、正式匹配结果)、路径/结局(持久 mode/outcome、selected、模型 `order`、五类引用 ref,无模型调用填 `not_applicable`)、证据五层(布尔+引用;`task_candidate_gold` 另附 `task_candidate_gold_recorded` 子列保持 Phase A recorded 口径可比)、候选与门禁(金标卡是否在任务/在 `order`/位次/资格/condition_fit/模型自述理由、选中卡门禁结果、拒因)、首位断点(标签/机制/置信/不确定/因果假设/引用)、评分敏感性(多组分、任一组分口径)。布尔列一律 `true/false/unknown/not_applicable`,无空串歧义;`evidence_trace.jsonl` 每题给出有限证据清单(相对封存根路径+文件 SHA+关键字段,含 merged 答卷行)。**金标不入表**:只保留匹配布尔、`gold_ids_digest`(金标身份集合 SHA 前 12 位)与 `n_gold_products`。

### 2.2 断点指派规则(确定性、互斥、按序短路)

`classify_breakpoint` 为纯函数(可单测),规则顺序:

1. `agent_rank∈2–5` → `reported_at_rank_2_to_5`;
2. 类比拒绝且运行时目标解析 ok 且**整分子身份匹配金标** → `validation_rejected_gold`(上限见 §4);或显式验证产物拒绝金标 → 同标签;
3. 验证接受金标但未进裁决 → `validated_but_not_reported`;
4. 任务含**可选择**金标卡(rank 任务内任一 kind 候选卡都是模型可选集;recorded 卡恒可选)且资格可用(`condition_fit≠conflict`)→ `eligible_gold_not_selected`;全部资格不可用 → `unknown`(机制 `task_candidate_gold_card_ineligible`);
5. 任何层都无金标 → `retrieval_absence_within_observed_scope`(优先于 selected 分支:选中卡不含金标只是范围缺金的伴生结果);
6. 有选中记录/卡且产物不含金标(金标仅在原始检索层)→ `selected_wrong_product`;
7. 其余 → `unknown`(机制单列:analogy_abstained/analogy_proposed/analogy_rejected/novel_generated)。

两条**显式映射决策**(报告负责说清,表内事实照登):类比任务的供体/规则卡是类比源而非答案候选,其"选中证据产物≠金标"不构成 `selected_wrong_product`,类比行不进该分支;类比值上的金标仅存在于原始检索层时,断点在生成阶段、离线不可判,按任务书 §2.1 归 `unknown` 而不是硬猜。化学/模型因果推测一律单列 `causal_hypothesis`(如 27 题的模型自述理由引自首跑 `parsed.reasons`,是原文非审计推断)。

## 3. 四组专项审计

### 3.1 唯一 recorded:48 题(=31 selected_wrong + 17 范围缺金)

逐题核对唯一 exact 记录:**48/48 方向一致**(输入底物 cn == 记录 reactant_identity)、**48/48 单产物记录**、condition_fit 全为 `unknown`、来源与资产 SHA 可回查(`source_record.btid/reac_id/library_sha256`)。子计数:当前选中记录不含金标 48/48;**另一条真实合格 exact 记录含金标 0**(每题检索中 recorded 卡恰 1 张);仅原始检索(非 recorded 卡)含金标 31;范围完全无金标 17;多金标/组分口径敏感(探索口径可翻转)11;证据不足 0。引擎在 64/112 命中组之外的 @5 配对差异不构成"本系统可合法报告"的证据——非 recorded 卡(规则/类比)按首跑策略不得直接提交,这一步是策略边界不是失误。

### 3.2 多 recorded:43 题(=27 eligible + 8 selected_wrong + 8 范围缺金)

Phase A「模型选错 22」**全部复核成立**:22 张含金标 recorded 卡都在任务候选集、`condition_fit=unknown`、都在模型 `order` 内位次 2–6(2:14、3:5、5:2、6:1),模型自述理由 22/22 可回查;选中卡 43/43 验证通过(「选中卡自身无效」子列 = 0);「任务有卡但不在 order」在 recorded 口径下 = 0。**本审计加厚 +5**:5 题任务内 rule/analog 候选卡含金标(位次 3/4/4/4/6,模型自述"苄位羟化模板对羰基底物机制不对应"等理由),按任务书 §2.1「候选卡含金标且满足当时可用资格」并入 `eligible_gold_not_selected`( recorded 口径子列单列,保持与 Phase A 可比)。R2 的「25/70 未选中 recorded 卡含金标」口径精确复现(25/70,其中 3 题命中 @1),确认其**不得**写成 25 个 @1 可修复题;@1 相关的正确集合是 22(recorded 口径)。26/27 的金标卡在引擎 Top-5 内也有命中位——引擎能找到不等于模型该选或可选,两臂角色不同。

### 3.3 类比:66 题(28 弃答 / 23 拒绝 / 15 接纳;=8 val_rej + 51 unknown + 7 范围缺金)

供体画像(与 Phase C 审计一致):mapping_status 全 `unavailable`、对齐 44 中心子图 / 22 全供体、62/66 供体中心原子 ≤3。23 条拒绝逐题重算见 §4(8 条目标整分子=金标,编辑门禁确定性拒绝)。15 条接纳:编辑执行成功但产物≠金标(0 命中),金标仅存于原始检索层 → `unknown`(机制 `analogy_proposed`)。28 条弃答:空答,无目标无产物 → `unknown`(机制 `analogy_abstained`)。与 Phase C 只读再分类按 qid 对照:23/66"仍适用"是**路由资格模拟**、非新命中分数,本表不将其折算任何 @1 收益。5 道类比题的任务卡(供体/规则卡)产物身份恰为金标——这是"供体按产物身份找回"机制的直接体现,只登事实列(`donor_product_matches_gold` 等),不构成选择集证据。

### 3.4 novel:25 题(=14 rank 2–5 + 10 unknown + 1 范围缺金)

14 题正确产物**已验证并已报告**在第 2–5 位(rank=2×9、3×3、4×2;13 题 report 宽度打满 5、1 题 4)——首位排序问题,与"提高 @5"是两件事。另 10 题:模型生成产物全部≠金标(生成失败断点,`unknown`);1 题范围完全无金标。novel 50 题全部有检索产物(Phase A 事实),本 25 题不得称为"零证据生成失败";原始检索重叠(9/25 题检索含金标)只进事实列。

## 4. 「8/23 vs 0/23」独立裁决(任务书 §3.3)

逐题行:`analogy_target_gold_recompute.tsv`(23 行,四口径 + 账本/现解析器逐字对比)。

| 口径 | 命中 |
|---|---|
| 整分子 `cn_identity`(账本 `target_smiles`) | **8/23** |
| 任一组分(含上一行的 8) | 9/23 |
| 目标文本包含金标 SMILES 字面 | 1/23(弱口径,仅登记) |
| 运行时 `target_molecode.ok=false`(不可解析) | 1/23(`RXNG_c48af809…`) |
| 四口径皆无匹配 | 13/23 |

- 8 题整分子匹配(强度:运行时账本由当时确定性解析器写出;今天用交付解析器对原文重算 **22/22 逐字一致**,排除"解析器版本差"解释)。
- **与 Phase C R3 更正双向一致**:Phase C 初版审计报 0/23 并据此撤回 R2 的 8/23;其同日 R3 复核查明根因是**审计脚本题号 bug**(run 目录名被剥掉 `RXNG_` 前缀而金标 qid 保留 → 逐题金标查找全部落空、诊断列假性归零),修正 `_norm_qid` + "金标零交集即失败"自检后复测得 8/23(`reports/ec298/phase_c/rejections_reclassified.tsv` 现版本 8 true,`summary.json` 留痕 `n_task_qids_found_in_gold=66`)。本审计**不依赖其脚本**:直接读首跑账本 `target_smiles` 匹配,得到同一批 8 题,且首次给出组分口径(9/23)、不可解析题(`RXNG_c48af809…`)与 13 题无匹配的完整分解。R2 原始口径成立;任何引用应以 8/23 为准,0/23 作废。
- **上限(防过度解读)**:8 题是"模型**声明**的目标匹配金标、编辑列表被确定性拒因拒绝"。编辑从未执行,"执行结果=声明目标"未获证明;Phase C 同输入重放显示**这 8 题的旧编辑列表在新协议下全部仍不可执行**(`new_classification=not_executable`)。所以 8 是"被证实的 @1 相关损失断点",不是"8 个可修复 @1"。

## 5. 改进对照:覆盖与效果分开(全文见 `fix_coverage.tsv`)

四状态:`observed_in_first_run` / `implemented` / `independently_reviewed` / `measured_on_frozen_dev`。文档状态快照 2026-09-28,SHA 见 fix_coverage 末行。

| 断点 | 触及阶段 | 实施 | 独立 review | 冻结 dev 真实对照 | 新 @1 证据 |
|---|---|---|---|---|---|
| eligible_gold_not_selected(27) | Phase B(报告展开解耦) | implemented | R1 两项 P1→修复;R2 再提两项 P1+一项 P3→修复复测(报告 §10,356 passed);未见最终通过结论 | 未执行 | 无 |
| validation_rejected_gold(8) | Phase C(编辑协议 v2+资格门禁) | implemented | **二轮复核暂不通过**(前轮三项 P1 确认修复;新发现 P1:rank 可选原始 analog/rule 卡提交;初版 0/23 系其脚本题号 bug,R3 已更正为 8/23) | 未执行 | 无 |
| reported_at_rank_2_to_5(14) | **无**(首位排序无人瞄准;`v43-repadj-1` 规定 selected 恒排第一) | — | — | — | 无 |
| selected_wrong_product(39) | 无直接瞄准 | — | — | — | 无 |
| retrieval_absence(33) | 无(Phase D1 供体找回为类比侧草案) | draft | — | — | 无 |
| unknown(61) | Phase C 门禁部分相关(改变类比进入率=路由资格,非命中) | 部分 | 同上 | 未执行 | 无 |
| 多组分正式评分定义(13 题探索口径可翻转:11 rec_direct/1 analogy/1 rank) | 无(正式口径保持整条候选) | — | — | — | 无 |

- Phase A:两臂同口径修复,**agent 298/298 rank 未变**——修的是测量,不是 @1 预测(R2 数据通过,`e6543f1`/`5c8f284`)。
- Phase B:R1/R2 两轮 review 的 P1 均修复后,其冻结策略 `v43-repadj-1` 仍规定 selected 恒排第一位——报告展开的改善属 @3/@5 叙事,@1 排序不动;不得引用 Phase B 产物主张 @1 收益,最终通过结论待下一轮 review。
- Phase C 门禁减少类比进入率(23/66)可能把题转向 novel/hold——这是路由构成变化,不构成准确率提升;其 dev 三臂对照(`analogy_enabled=false` 等)未执行。
- **尚未直接瞄准的断点**(单列,任务书 §4):首位排序(14)、recorded 金标/条件冲突与首位选择(39)、检索/资产覆盖(33)、多组分正式定义。低风险后续:全部建议在**冻结 dev 或新外考做成对比较**后评估,禁止用已见 298 选参;298 复跑只能标 `post_hoc_repair_check` 独立列示。
- 测试全绿只证明实现行为。截至本报告:**「目前尚无新 @1 提升证据」成立**,无需修正。

## 6. 审计缺口与人工复核清单

- `audit_gaps.tsv`:0 行(表头在)。逐题路径一致性检查(裁决 `path_id` 必须属于本题主链)未发现串线;引用缺失未发现。
- 已知限定(非缺口):1 题类比目标运行时不可解析(`RXNG_c48af809…`,target ok=false,如实留行);`retrieval_absence` 的范围限定(无完整候选池)已在每行 uncertainty 写明。
- **建议人工化学复核(三组,共 74 题;qid 16 位前缀,全单可按 `hit1_misses.tsv` 的 `first_proven_loss_stage` 列过滤回查)**:
  1. **8 道类比目标命中题**(`validation_rejected_gold`;复核声明目标在底物化学上是否合理,防"模型拼出金标 SMILES 但编辑无意义"): `RXNG_7701b6993b9` `RXNG_4609b23a9a2` `RXNG_208874cbe2e` `RXNG_30ab4108da3` `RXNG_cf89ba36228` `RXNG_d7656c5f483` `RXNG_6455b8da465` `RXNG_7d281486c75`
  2. **27 道 eligible**(`eligible_gold_not_selected`;复核金标卡化学竞争力,模型自述不选理由见各行 `gold_card_model_reason`,尤其 5 道 rule/analog 卡的"机制不对应"论断——`RXNG_4c2cd0c3e1c` `RXNG_8bc45c2fa9f` `RXNG_bff8e98f71a` `RXNG_d41e12c0137` `RXNG_e10f66db2bc`): `RXNG_a30cf37e0b9` `RXNG_d89bf895ae3` `RXNG_1eba3a0e975` `RXNG_3cdbe17c5f6` `RXNG_840d50abfec` `RXNG_33315ca374c` `RXNG_61667af8d9c` `RXNG_2a1a5bf6480` `RXNG_4c2cd0c3e1c` `RXNG_8bc45c2fa9f` `RXNG_bff8e98f71a` `RXNG_d41e12c0137` `RXNG_e10f66db2bc` `RXNG_eb7a8583af6` `RXNG_11e08d7a2a4` `RXNG_50e0f19bd85` `RXNG_7a886593dd0` `RXNG_164844b4b76` `RXNG_06453c845d4` `RXNG_0faafc67fe7` `RXNG_59a61f5ced6` `RXNG_e19ee1be47f` `RXNG_fd4e0bad9fc` `RXNG_c8836aa26b6` `RXNG_ef18f4fd48f` `RXNG_35a46ed17cd` `RXNG_891c844ebaa`
  3. **39 道 selected_wrong**(`selected_wrong_product`;复核选中记录与 benchmark 金标在条件/口径上是否本就冲突——此为 benchmark 相容性问题,不是本系统缺陷的证明): `RXNG_04365649555` `RXNG_103c84009b4` `RXNG_22901c4d6f4` `RXNG_330df242afd` `RXNG_526bccaa523` `RXNG_59a408497ff` `RXNG_fb86653f3fe` `RXNG_fce2c28fb26` `RXNG_febc7fbd3d7` `RXNG_fee48640c91` `RXNG_74406a79d20` `RXNG_cd29a6432c2` `RXNG_e7f836a4e6e` `RXNG_ef027adac9a` `RXNG_37e263634a3` `RXNG_09a6f7180b3` `RXNG_6d4d3e2fa5a` `RXNG_a401c95418f` `RXNG_05c5a15c9d9` `RXNG_365fb0be778` `RXNG_4ec68aa8196` `RXNG_5876dc9dadf` `RXNG_5e86f7ef4c7` `RXNG_654cc41cad1` `RXNG_efa6ffdfa07` `RXNG_fc90885a446` `RXNG_1c56dceb435` `RXNG_3c9d29b41b6` `RXNG_8237d7deec2` `RXNG_93d3a3ef9b7` `RXNG_d6da5d9aa47` `RXNG_18a3c06e422` `RXNG_d953c142283` `RXNG_5e9b5672eb1` `RXNG_249b9956c0b` `RXNG_94c56325db7` `RXNG_eee01aeed9e` `RXNG_036534a3cd4` `RXNG_e0bca299339`

## 7. 交付物与身份

```text
reports/ec298/hit1_attribution_v1/        # 9 文件,SHA 见 output_manifest.sha256
  input_sha256.json                        # 输入角色 SHA + 清单校验声明
  hit1_misses.tsv                          # 182 行(67 列)
  evidence_trace.jsonl                     # 182 行,逐题证据链(路径+SHA+字段)
  group_summary.tsv                        # 六子组 + TOTAL:层/标签/组分翻转计数
  fix_coverage.tsv                         # 8 行:断点 × 阶段 × 四状态
  score_sensitivity.tsv                    # 182 行:主口径 vs 任一组分口径
  analogy_target_gold_recompute.tsv        # 23 行:四口径独立重算(§4)
  audit_gaps.tsv                           # 0 行(表头在)
  output_manifest.sha256
scripts/ec298_hit1_attribution.py          # v43-ec298-hit1-attribution-1
tests/test_ec298_hit1_attribution.py       # 11 项(含 §5.3 全部负例)
```

复算身份:双跑逐字节一致实测通过;`--check` 对 9 文件做字节 + 清单 SHA 双核对;锚点不符自动停止正式报告。

全仓回归(2026-09-28,`OMP_NUM_THREADS=1 PYTHONPATH=src:tests pytest tests/ -q`):**370 passed / 1 failed**;唯一失败 `tests/test_batch_dev.py::test_worker_crash_after_commit_recovers_no_duplicate` 为并行会话未提交改动中的既有顺序依赖 flake——单跑必过(实测 98.7s 通过),按字母序先于本任务测试运行,与本任务文件零交集(本任务未修改任何已跟踪文件,仅新增上述三件交付物 + 产物目录)。新增测试 11 项全绿(`pytest tests/test_ec298_hit1_attribution.py -q` → 11 passed)。
