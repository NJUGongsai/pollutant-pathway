# 回复:老师任务书(2026-09-27)执行情况 + 182 题 hit@1 逐题归因交付

- 日期:2026-09-28
- 执行:CC(v4.3 开发线)
- 回复对象:[`TEACHER_TASK_CC_V43_EC298_ATTRIBUTION_2026-09-27`](#) 任务书七项
- 状态:任务一至六**已全部完成**(任务四按勘误后口径重立);任务七(仓库合规)**未动,单列推进**;另按任务书精神追加了 182 题 hit@1 逐题归因。

---

## 0. 先说一件必须更正的事:判分口径勘误(v1 → v2)

老师任务书引用的数字(「对基线 +34」「引擎三档 153/0/145」「新基线 82 vs 旧 118」「hit@5 −5」)全部来自 scorer v1。v1 有一处口径缺陷:**两臂身份函数不对称**——agent 臂从原始 SMILES 现算身份,引擎臂却直接使用封存文件里的缓存 `product_identity`(可能保留电荷),引擎臂被系统性低估。Phase A 已用 scorer v2(两臂同一 `cn_identity` 函数、charge-normalized stereo-blind、引擎忽略缓存一律现算)重评,并经两轮独立复核通过。**勘误对照:**

| 指标 | v1(任务书引用,作废) | v2(正式口径) |
|---|---|---|
| agent hit@1/3/5 | 116/128/130 | 116/128/130(不变) |
| 引擎 hit@1/3/5/10 | 82/117/135/153 | **118/174/193/209** |
| @1 净差(agent−引擎) | **+34** | **−2** |
| @5 净差 | −5 | **−63** |
| 引擎档位切分 | 153/0/145 | **209/89** |

**方向性结论变化(请以本版为准):**

1. 「agent 超基线 +34」**不成立**:@1 两臂打平(116 vs 118);差距出现在 @3/@5(−46/−63,引擎 Top-10 池更宽)。
2. 「真空区 145 题」实为 **89 题**(引擎已导出 Top-10 内 209 / 外 89;Top-10 外是否有候选未知,不称完整池真空)。
3. 任务四的前提「hit@5 −5 疑似宽度截断」**前提已变**:v2 口径下差距是 −63,归因已按新口径重做(§2 任务四)。

勘误全文与 v1→v2 逐题差异(引擎 68 处 rank 变化 = 56 新命中 + 12 移位 + 0 丢失;agent 298/298 不变)见 `docs/EC298_REPORT.md` 勘误段与 `reports/ec298/phase_a_v2/score_v1_v2_diff.tsv`。

## 1. 任务一(P0):真空区命中切片 —— 已交付

产物:`reports/ec298/phase_a_v2/agent_hits_by_engine_tier.tsv`(+ summary)。

| 切片(v2 口径) | 题数 | agent hit@1 | hit@3 | hit@5 |
|---|---|---|---|---|
| 引擎 Top-10 档 | 209 | 111 | 114 | 114 |
| 引擎未检出档 | 89 | **5** | 14 | 16 |

**回答「LLM 泛化是否开始工作」:开始了,但量级还小。** v4.1 时代真空档 0/39 全灭;v4.3 真空档 hit@1 = 5/89,且 5 题**全部来自 novel_proposal**(模型生成,非检索复述),逐题 decision_log、裁决账本引用、命中证据 ID 全部可溯源(验收列 `agent_hit_ref_ok` 全 true):

| qid | 路径 | 命中证据 |
|---|---|---|
| RXNG_36c4cbdc… | novel_proposal/proposed | E_6e7cdebaf7a039(novel) |
| RXNG_8bb56f09… | novel_proposal/proposed | E_5e1213e44dc0db(novel) |
| RXNG_8f29c4de… | novel_proposal/proposed | E_e854310d15a0ed(novel) |
| RXNG_957aa185… | novel_proposal/proposed | E_1246d0576e8565(novel) |
| RXNG_c6992735… | novel_proposal/proposed | E_8987eb03169612(novel) |

同时注意反面:引擎 Top-10 档内 agent 丢掉 98 题 @1(111/209)——**当前主要失血点在「引擎也找得到」的档内**,这是 §3 归因工作的重点。

## 2. 任务二(P0):awaiting_prediction 50 题命运表 —— 已交付

产物:`reports/ec298/phase_a_v2/awaiting_prediction_fates.tsv`(50 行全覆盖 + budget_exhausted 1 题单列)。

- 空答闭环:51 题空答 = 50 awaiting + 1 budget_exhausted = **28 模型弃答 + 23 编辑拒绝**;
- 「发起调用但未落盘」与「落盘但未过 gate」已分开计数:51 题全部有完整调用账(**191 发起 / 186 成功 / 5 失败**;弃答/拒绝不等于没调用模型);
- 孤儿调用审计:**0 孤儿、0 attempt 错配**(调用↔响应按 task 目录 + attempt 逐条配对);
- 51 题无 validation.json 属预期(未产生可验证产物),逐题停点与 atomtool 检查项在表内;
- budget_exhausted 唯一一题耗尽的是 **worker 预算**(3 次调用均有响应),不是 LLM 预算。

## 3. 任务三(P0):决策路径贡献分解 —— 已交付

产物:`reports/ec298/phase_a_v2/decision_path_contribution.tsv`(+ 逐题明细)。以持久 decision_log 为准,不从产物反推;路径分布(题数)与命中分布分开列:

| 路径 | 题数 | agent @1/@3/@5 | 引擎 @1 |
|---|---|---|---|
| 唯一 recorded 直通 | 112 | 64/64/64 | 64 |
| 竞争 recorded(rank_candidates) | 70 | 27/27/27 | 27 |
| analogy_edit(弃答/拒绝/接纳) | 28/23/15 | **0/0/0** | 7/1/4 |
| novel_proposal | 50 | 25/37/39 | 15 |

配对 @1:both 103 / agent-only 13(12 novel + 1 rank)/ engine-only 15 / neither 167(两臂交叉验证:103+13=116=agent @1,103+15=118=引擎 @1)。**类比路线 66 题 @1 全灭**与 **novel 路径贡献了全部真空档命中**是两个最醒目的事实。

## 4. 任务四(P1):hit@5 差距归因 —— 前提已变,按 v2 重做

v1 的「−5」已作废(§0);v2 口径 @5 差 **−63**(130 vs 193)。产物:`reports/ec298/phase_a_v2/hit5_paired_attribution.tsv`(engine-only 82 题逐题 + 全 298 题配对行)。

- engine-only 82 题的**原始检索卡 82/82 含金标**——但仅是检索层重叠,不证明该卡满足条件、进入任务、通过验证或可报告(证据五层逐层单列);
- 主因标签(一题一个,规则确定性):证据不足以判断 40(其中 35 仅原始检索含金标)/ **模型选错 22**(任务候选集内存在含金标 recorded 卡未选,全部有模型 `order` 证据)/ 类比弃答 14 / 编辑拒绝 6;
- 宽度脚注:已在 `score_v2.json` summary 内建(hit@10 ≡ hit@5,agent 每父最多报告五个候选;与引擎 Top-10 的对比含宽度不对称成分)。

## 5. 任务五(P1):引擎基线差异说明 —— 已交付

- 机制解释:已随勘误报告写明——v4.3 资产为环境降解专用包(EAWAG 三环境 + BBD,library_full 4,454 反应),298 题卷为 RHEA/BRENDA/EnzymeMap 通用酶学来源;真空率抬升的主要来源是**资产-题卷域偏移**,不是引擎变弱(v2 下新引擎 @1=118 已与历史引擎 118 持平)。
- 定量重叠:`reports/ec298/phase_a_v2/asset_exam_overlap.tsv`——题卷底物命中资产 **182/298**,底物-金标产物对命中 **113/298**(规则层覆盖未评估,如实标注)。
- 新旧引擎逐题差异:`v41_baseline_diff.tsv`,24 处 rank 变化(v4.1 判分件只记 ≤5,已注明口径)。

## 6. 任务六(P1):模型调用分布 —— 已交付

产物:`reports/ec298/phase_a_v2/llm_call_distribution.tsv`。

| 每题调用次数 | 0 | 1 | 2 | 3 |
|---|---|---|---|---|
| 题数 | 112 | 182 | 3 | 1 |

合计 191 发起 / 186 成功 / 5 失败;`max_llm_calls=3` 触顶仅 1 题(RXNG_eef21424b5618cc);无 llm_remaining 归零题。0 调用的 112 题即唯一 recorded 直通(配合任务三可算直通占比 112/298=37.6%)。

## 7. 追加交付:182 题 hit@1 失分逐题归因(任务一至六的逐题下沉)

老师任务书的切片回答了「分布在哪」,我们进一步把 **182 道 @1 未命中逐题归因**(任务书 `docs/TASK_V43_EC298_HIT1_ATTRIBUTION.md`,独立实施+负例测试自检):产物 `reports/ec298/hit1_attribution_v1/`(182 行逐题表 + 182 行证据链 + 汇总),报告 `docs/EC298_HIT1_ATTRIBUTION_REPORT.md`(另配通俗版 `…_PLAIN.md`)。

**断点分布**(标准答案闯 5 关:检索出现→进候选→被选中→过验证→进答卷;断在哪关,哪关就是失分点):

| 失分点 | 题数 | 大白话 |
|---|---|---|
| 摆在眼前没排第一 | **27** | 金标卡在模型选择集内、可选,被排在 2–6 位(22 张 recorded 卡,Phase A「模型选错 22」全部复核成立;另 5 张 rank 任务内 rule/analog 卡) |
| 目标写对、被编辑工具拦下 | **8** | 模型声明的类比目标整分子身份=金标,编辑列表被确定性拒因拒绝 |
| 选中记录产物≠金标 | **39** | 31 唯一 recorded 直通 + 8 rank;48 道直通全部方向一致、单产物 |
| 对的答案在第 2–5 位 | **14** | 全部 novel;首位排序问题,**尚无任何改动瞄准** |
| 已观测范围内无金标 | **33** | 范围限定表述,不称「数据库没有」 |
| 断点不可离线判定 | **61** | 类比弃答 26 / 类比生成错产物 14 / 类比目标非金标 11 / novel 生成错产物 10;已核实事实照登 |

**一项数字分歧的裁决**:R2 曾引「23 条被拒类比中 8 条目标匹配金标」,后续审计一度报 0/23;本次用**首跑账本目标字符串**独立重算确认为 **8/23**(0/23 系审计脚本题号 bug,已双向更正)。上限同时声明:8 题的旧编辑列表在新协议下重放仍全部不可执行——是「8 个被证实的失分点」,不是「能捞回 8 分」。

**改进对照的诚实结论**:Phase A 修的是测量(agent 298/298 不变);Phase B(报告候选解耦)已实施、两轮 review 的 P1 均已修复但未见最终通过结论,且其策略 selected 恒排第一、不改善 @1;Phase C(类比门禁+编辑协议 v2)已实施、二轮 review 暂不通过;Phase D 仍为草案。**全部改动尚无冻结 dev 真实模型对照、无 298 复跑——目前没有任何新 @1 提升证据。** 下一步最大杠杆是首位排序(14+27+39 道均涉),参数只允许在冻结 dev 或新外考上做,298 正卷不重跑不调参。

## 8. 红线遵守(全部产出物适用)

- 已封存产物(`runs/ec298_v43r1/`、判分 JSON、金标)**只读**:本地封存镜像逐文件 SHA 双向校验,复算前后不变(实测 0 文件变动);
- 全部任务零 API、零重跑、零模型调用;金标仅离线判分进程读取,不回灌候选/提示词/路由/阈值;
- 派生脚本入库(`scripts/ec298_phase_a.py`、`scripts/ec298_hit1_attribution.py`),产物带 `output_manifest.sha256`;同输入双跑逐字节一致;
- 298 正卷未重跑;若将来复跑只作 `post_hoc_repair_check` 另立,不与本卷混分。

## 9. 任务七(仓库合规):如实报告——尚未整改

144.2MB 数据入库、`enzyme_cage_v1`/编排主线删除、commit 粒度三项**均未处理**,不混在本批离线分析里交差;拟单独排期(需与并发开发会话协调分支动作),整改方案先送审再动。如老师希望优先级提前,请示下。

## 10. 送审与复核入口

- **任务一至三**(P0):已过两轮独立复核(R1 修复 + R2 通过 + 防护加固,提交 `a66ceae…5c8f284`),可直接送审;
- **任务四至六**:按 v2 口径完成,随勘误报告一并送审;
- **182 题归因**(§7):自检+负例测试全绿,建议按流程过外审;
- 复核命令(零网络,路径显式传入;封存镜像可提供):

```bash
# Phase A 全量重算(清单校验 fail-closed)
python scripts/ec298_phase_a.py --run-dir <封存>/runs/ec298_v43r1 --gold <封存>/ec298_gold_readonly/questions.jsonl \
    --v1-scoring <封存>/…/per_question_scoring.json --v41-baseline <封存>/…/per_question_scoring.jsonl \
    --asset-library assets/v3_reactions/library/library_full.jsonl --out-dir reports/ec298/phase_a_v2

# 182 题归因复算 + 字节级核对
python scripts/ec298_hit1_attribution.py …同上输入… --out-dir reports/ec298/hit1_attribution_v1 --check
```

主要文档索引:`docs/EC298_REPORT.md`(勘误)、`docs/EC298_PHASE_A_REPORT.md`、`docs/EC298_HIT1_ATTRIBUTION_REPORT.md`(+ 通俗版)、`reports/ec298/phase_a_v2/`、`reports/ec298/hit1_attribution_v1/`。

---

CC(v4.3 执行线),2026-09-28

口径异议或需要补的切片,回信即办;任务七整改方案将单独送审。
