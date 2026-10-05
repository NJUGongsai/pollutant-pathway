# EC298 Phase D 复测丢分逐题归因(C0 hit@1 162 失分题;D-3 对照)

> **状态:complete**。零 API、零预测重跑、零金标回灌;对复测两臂封存
> 产物(`runs/ec298_pd_retest_{C0,D3}`,代码 `eb3ba7f`)与同一引擎结果
> (`0e16268c…`)、同一金标(`9f5955d4…`,仅离线进程只读)做五层证据
> 断点取证。输入锚点 fail-closed 全过(C0 136/182/186、D-3 132/174/182、
> 引擎 118/174/193/209、空答 12/13、298 题);`--check` 复算逐字节一致;
> 产物 7 文件带 SHA 清单(`reports/phase_d/retest/loss_audit/`)。
> 方法与首跑归因(`scripts/ec298_hit1_attribution.py`)同口径,差异见 §1.3。
> 背景报告:[EC298_PHASE_D_RETEST_REPORT.md](EC298_PHASE_D_RETEST_REPORT.md);
> 通俗版:[EC298_PD_RETEST_LOSS_ATTRIBUTION_PLAIN.md](EC298_PD_RETEST_LOSS_ATTRIBUTION_PLAIN.md)。

## 0. 一句话结论

C0(发布默认配置)162 道 hit@1 失分题的确定性断点:**答案已报告但没排
第一位 50 题;选了另一条反应/记录 44 题;已观察检索范围内没有金标 31
题;检索里有金标但生成链路没用上(环节不可离线细分)25 题;类比编辑被
确定性拒绝 11 题;声明的正确目标被一致性门禁拒绝 1 题**。首跑的两类
工程断点(候选卡未选 27 题、验证拒绝 8 题)本轮归零/近零——B/C/D 修复
在已见题上兑现;持续丢分集中在**首位排序、recorded 提交选择、检索覆盖**
三类,均属此前 review 已声明"未瞄准 @1"或"资产侧"的类别。

## 1. 口径与输入完整性

### 1.1 输入(全部 SHA 对账)

| 输入 | 值 |
|---|---|
| C0/D-3 臂根 | `runs/ec298_pd_retest_{C0,D3}`(复测报告 §3 两臂,298/298 合法终态) |
| 引擎结果 | `engine_results.jsonl` SHA `0e16268c…`(两臂评分共用同一文件) |
| 金标 | `questions.jsonl` SHA `9f5955d4…`(与复测正式评分同源;只在本离线进程只读) |
| 锚点自检 | C0 136/182/186、空答 12;D-3 132/174/182、空答 13;引擎 118/174/193/209;任一不符即停止(fail-closed,未触发) |
| 复算 | 同输入 `--check` 逐字节一致(两次) |

### 1.2 五层证据与断点

逐题独立取证:raw_retrieval → task_candidate → selected →
validated_reportable → reported(下层成立不推出上层);断点标签由
`classify_breakpoint` 纯函数按首跑归因逐字一致的规则序确定性指派,
一题至多一个主断点;化学/模型因果推测不入标签。cn 身份一律从原始
SMILES 现算(忽略一切缓存身份)。

### 1.3 与首跑归因的方法差异(如实登记)

- **reported 层**:读 `report_adjudication.json` 的
  `products[reportable=true]`(report_rank 排序),与复测报告修订 v2
  同口径(首跑读 `entries`);
- **类比声明目标**:协议 v2 的 `atomtool_checks` 无 ledger
  `target_smiles` 键,改用运行时解析器 `molecode_to_smiles` 重解析
  `parsed.target_molecode`(与首跑 phase_c 重算法同源;首跑账本与
  解析器 22/22 一致)。该补充判出 1 题「声明目标=金标被拒」;
- **空答单列**:首跑把"模型弃答/编辑拒绝后无产物"并入 `unknown`,
  本表单列 `empty_no_model_answer`(12→11 题,1 题经目标重解析改判
  `validation_rejected_gold`),故两轮 `unknown` 不可直接相减。

## 2. C0 162 题断点总表

| 断点(丢分原因) | 题数 | 含义 |
|---|---:|---|
| `reported_at_rank_2_to_5` | **50** | 正确产物已在最终答卷第 2–5 位,首位是别的产物 |
| `selected_wrong_product` | **44** | 选中并提交了另一条记录/卡,其产物 ≠ 金标(44/44 题金标在原始检索层其他卡上可见) |
| `retrieval_absence_within_observed_scope` | **31** | 已封存检索卡范围内无任何含金标层;31/31 题引擎 Top-10 亦无金标 |
| `unknown`(候选形成/生成环节) | **25** | 金标仅见于原始检索层,agent 产物链从未出现;离线不可再细分 |
| `empty_no_model_answer` | **11** | 类比编辑被确定性拒绝(target_consistency),无任何产物 |
| `validation_rejected_gold` | **1** | 声明目标重解析=金标,被一致性门禁拒绝(首跑 8 题类残余) |
| 合计 | **162** | hit@1 = 136/298 |

按决策路由(mode)交叉:

| 断点 | recorded 直通 | rank 排序 | analogy 编辑 | novel 生成 | 和 |
|---|---:|---:|---:|---:|---:|
| rank_2_to_5 | 0 | 23 | 0 | 27 | 50 |
| selected_wrong | 31 | 13 | 0 | 0 | 44 |
| retrieval_absence | 17 | 8 | 1 | 5 | 31 |
| unknown | 0 | 0 | 4 | 21 | 25 |
| empty | 0 | 0 | 11 | 0 | 11 |
| validation_rejected | 0 | 0 | 1 | 0 | 1 |
| **失分合计** | **48** | **44** | **17** | **53** | **162** |
| 该路由题数 / hit@1 | 112 / 64 | 70 / 26 | 25 / 8 | 91 / 38 | 298 / 136 |

按引擎参照交叉(引擎 Top-10 首命中位):

| 断点 | 引擎第 1 | 引擎 2–5 | 引擎 6–10 | 引擎无 | 和 |
|---|---:|---:|---:|---:|---:|
| rank_2_to_5 | 4 | 27 | 4 | 15 | 50 |
| selected_wrong | 0 | 27 | 3 | 14 | 44 |
| retrieval_absence | 0 | 0 | 0 | 31 | 31 |
| unknown | 3 | 7 | 7 | 8 | 25 |
| empty | 4 | 3 | 0 | 4 | 11 |
| validation_rejected | 0 | 0 | 0 | 1 | 1 |
| **合计** | **11** | **64** | **14** | **73** | **162** |

## 3. 各断点细读

### 3.1 答案已给出、没排第一(50 题,最大桶)

- 位次分布:rank2 = 30、rank3 = 16、rank4 = 3、rank5 = 1
  (与 hit@3−hit@1 = 46 = 30+16 自洽)。
- 路由:novel 27 / rank 23。**首位排序未被任何阶段瞄准**(首跑
  fix_coverage 已声明 Phase B 只扩后位可报告性、不动 @1);本轮 50 题
  中 22 题正是首跑 `eligible_gold_not_selected` 修复后的直接去向——
  金标卡从"选不中"变成"可报告但排后位"。
- 引擎对照:27 题引擎也把金标排在 2–5 位(排序难度与引擎同源);
  15 题引擎 Top-10 没有、7 题检索层本无金标——其中后者是模型
  **自己生成的金标**排到了后位,属生成质量而非检索问题。

### 3.2 选了另一条反应(44 题)

- 31 题发生在 recorded 直通(确定性的记录提交路径选了非金标的
  recorded 反应;首跑 fix_coverage 已注明"唯一 recorded 金标/条件
  冲突、多 recorded 首位选择"未被任何阶段的 @1 语义覆盖)、13 题
  rank 排序。
- 44/44 题金标在**原始检索层其他卡**上可见(即库里查得到,选卡时
  没选它);30 题引擎 Top-10 含金标(27 题在 2–5 位)。
- 首跑同标签 39 题全部持续丢分,另 5 题从旧 `eligible_not_selected`
  迁入——该桶零修复、略有增长,是 @1 仅次于排序的第二大可撬动量。

### 3.3 检索范围内没有金标(31 题)

- 31/31 题引擎 Top-10 亦无金标(引擎与 agent 同源检索);路由
  recorded 17 / rank 8 / novel 5 / analogy 1。
- 限定:仅指**已封存检索卡范围**缺金标,完整候选池不存在,不得称
  "数据库没有正确反应";扩检索/资产属新外考问题。

### 3.4 生成环节未用上检索内金标(25 题,unknown)

- novel 21 + analogy 4;25/25 题金标在原始检索层可见,但任务候选、
  选中、验证、报告各层从未出现——断点在候选形成/生成,具体环节
  离线不可判(与首跑 unknown 语义一致)。
- 其中 3 题引擎排第 1(检索+引擎都把金标顶到首位,agent 生成链路
  仍没用上)。

### 3.5 类比编辑被拒(11 题)与目标=金标被拒(1 题)

- 11 题全部在 `target_consistency` 确定性门禁被拒:声明编辑执行后
  不等于声明目标(键级/元素不一致,bond_order/element/
  bond_in_execution_not_target 三类拒因)。**11/11 题声明目标重解析
  后均 ≠ 金标**——门禁本轮拒掉的都是错答案,未发现误杀;但其中
  4 题引擎排第 1(类比路线本身可以答对,编辑输出质量问题导致弃权)。
- 1 题(RXNG_b978fd…)声明目标重解析后**整分子匹配金标**,被
  `target_consistency` 拒(element:S_C_4 N≠C)——首跑 8 题类的
  残余,是本轮唯一可归因到门禁的正确答案损失。

## 4. 首跑 → 复测迁移(同一 298 题)

首跑 182 失分 → 本轮 162:**23 题修复**(旧标签 unknown 15、
validation_rejected 7、rank2-5 1),**3 题新丢**(novel 2、rank 1,
均非工程断点)。持续丢分 159 题的旧→新断点迁移:

| 旧标签(首跑) | → 新标签(本轮) | 题数 |
|---|---|---:|
| selected_wrong_product | selected_wrong_product | 39 |
| retrieval_absence | retrieval_absence | 31 |
| unknown | unknown | 23 |
| **eligible_gold_not_selected** | **reported_at_rank_2_to_5** | **22** |
| reported_at_rank_2_to_5 | reported_at_rank_2_to_5 | 13 |
| unknown | empty_no_model_answer | 11 |
| unknown | reported_at_rank_2_to_5 | 11 |
| eligible_gold_not_selected | selected_wrong_product | 5 |
| retrieval_absence | reported_at_rank_2_to_5 | 2 |
| validation_rejected_gold | unknown | 1 |
| unknown | validation_rejected_gold | 1 |

- **工程断点兑现**:旧 `eligible_gold_not_selected` 27 题本轮标签
  归零(22 → 后位可报告、5 → 选错);旧 `validation_rejected_gold`
  8 题中 7 题本轮 @1 命中。Phase B(候选裁决/报告展开)与 Phase C
  (编辑协议 v2+适用性门禁)的修复在已见题上方向为正。
- **未瞄准处不动**:selected_wrong 39→39 持续、retrieval_absence
  31/33 持续,与两阶段 review 的"未实现/资产侧"声明一致。

## 5. 结构性观察

- **多产物金标是最强单一结构因子**:金标含 ≥2 产物的题 45 道,
  hit@1 仅 11/45(24.4%);单产物题 125/253(49.4%)。丢分 162 题中
  34 题为多产物。「任一组分命中」口径下 13 题可翻转 @1
  (selected_wrong 11 + rank2-5 2)——即这 13 题答对了一半产物
  (组分正确、整串不等),指向多产物组装/输出完整性,而非反应方向
  错误。正式口径不变(整条候选)。
- **丢分题中金标的检索可见率 124/162(76.5%)**:大多数丢分不是
  "查不到",而是查到后没用对(选卡/排序/生成/组装)。
- **引擎首位但 agent 丢 11 题**(empty 4、rank2-5 4、unknown 3):
  引擎已把金标排第 1,agent 链路仍丢——纯 agent 侧损失。
- **agent 独有价值**:16 题 agent @1 命中而引擎 Top-10 无
  (novel 8 + analogy 8),生成/类比路线在引擎覆盖外有真实增益。

## 6. D-3 对照(次实验臂)

两臂断点结构几乎同构(selected_wrong 44/44、retrieval_absence
31/31、rank2-5 50/50);差异集中在 unknown 25↔28 与 empty 11↔13,
净差 −4 与复测报告 §5 的 A/B/C 层结论一致。逐题标签不同的仅 15 题
(novel unknown↔rank2-5 为主),与"任务载荷实质相同、分歧来自模型
抽样噪声"的 C 层判定一致。D-3 的 13 题空答中 0 题声明目标=金标。

## 7. 可撬动量排序(供下一步任务书参考;非本表授权调参)

| 优先 | 类别 | 题量 | 说明 |
|---|---|---:|---|
| 1 | @1 首位排序 | 50(+引擎 e1 的 11) | 无任何实现瞄准过首位;含 22 题旧 eligible 修复的自然去向 |
| 2 | recorded 提交选择 | 31 | 确定性路径选错 recorded;首跑起零修复 |
| 3 | rank 选卡 | 13(selected_wrong 内) | 模型在有金标卡的集合里选了别的卡 |
| 4 | 多产物组装 | 34 丢分(13 可翻) | 组分正确整串不等的 13 题是低垂果实 |
| 5 | 检索覆盖 | 31 | 资产侧;已见 298 不可用于检索调参后自称独立验证 |
| 6 | 类比编辑输出质量 | 11(4 题引擎 e1) | 门禁无误杀,但错编辑把可答题变成弃权 |

**红线**:本轮为已见题后验分析;不得据本表调参/prompt/阈值后在
已见 298 上再称独立验证(复测报告 §10 限定继续适用)。

## 8. 产物索引与复现

`reports/phase_d/retest/loss_audit/`(7 文件,`output_manifest.sha256` 全过):
`paired_298_loss_labels.tsv`(两臂合并 298 行速览)、
`loss_audit_298_{c0,d3}.tsv`(全 298 行五层旗标+断点)、
`miss_hit1_detail_{c0,d3}.tsv`(失分题证据引用/拒因/类比目标)、
`summary.json`、`input_sha256.json`。
脚本:`scripts/ec298_pd_retest_loss_audit.py`(零 API;远端执行于
Chenyu `/tmp` 同字节副本;run 根只读、只写 out-dir)。

复现(Chenyu,零 LLM):

```bash
cd /usrdata/EnzymeCAGE_data/workspaces/dependingv43 && \
OMP_NUM_THREADS=1 PYTHONPATH=src .venv/bin/python \
  /tmp/ec298_pd_retest_loss_audit.py \
  --c0-root runs/ec298_pd_retest_C0 --d3-root runs/ec298_pd_retest_D3 \
  --engine-results runs/ec298_pd_retest_engine/engine_results.jsonl \
  --gold /usrdata/EnzymeCAGE_data/workspaces/ec298_gold_readonly/questions.jsonl \
  --out-dir reports/phase_d/retest/loss_audit            # 加 --check 复算
```

## 9. 限定

1. 已见题后验分析,不构成独立外部验证;单次模型抽样,标签对"模型
   为什么这样输出"不做因果断言(因果推测不入标签,仅 §3 叙述性解释)。
2. 断点标签是**确定性观察**;"undetermined"(unknown 25)表示离线
   证据不足以细分,不是无法解释。
3. 逐题产物引用(远端相对路径)在 detail TSV `evidence_refs`/
   `validation_refs` 列,可回查至 `runs/<run_id>/results/T_*/`。
4. 本表不改变任何正式分数;金标未写入任何仓内产物。
