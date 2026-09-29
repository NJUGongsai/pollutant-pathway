# EC298 Phase D 修复后配对复测报告(C0 vs D-3)

> **状态:complete**(六项 review 硬门自检全部通过,见 §8;结论措辞按任务书
> §5.5 限定为"在已见 298 题、这次冻结配置下观察到的差异")。
> **修订 v2(2026-09-29 R2 review)**:外部 review 发现两张派生表的
> schema 读取缺陷(首位产物来源全空、deepdiff 报告层计入了非报告候选)
> 与仓内并发证据不足;已修复并重生成(§12)。**主分数与逐题 rank
> 逐字节不变**(重跑前后 score_v2 摘要、hits、四格、赢/输/平全部相同),
> 受影响的只有逐题证据列与并发复核材料。
> 任务书:[TASK_V43_EC298_PHASE_D_RETEST_298.md](TASK_V43_EC298_PHASE_D_RETEST_298.md);
> 实验标签:`seen298_post_hoc_repair_check`。
> 发车前不可变登记:[EC298_PHASE_D_RETEST_REGISTRATION.md](EC298_PHASE_D_RETEST_REGISTRATION.md)
> (登记原文 SHA `449ea043…`;含两臂身份 SHA 的勘误 #1 版本 `603467ac…` 于首次
> 付费调用前落盘;勘误 #2 记录引擎臂/烟测/首次付费时刻,在烟测后、两臂
> 运行前追加,版 `f95fa8fb…`;勘误 #3 登记本轮 R2 review 派生表修复
> (§12),现版 `b2c11c13…`)。
> 通俗版:[EC298_PHASE_D_RETEST_REPORT_PLAIN.md](EC298_PHASE_D_RETEST_REPORT_PLAIN.md)。
> 执行环境:本地(conda env depending43)+ Chenyu
> `/usrdata/EnzymeCAGE_data/workspaces/dependingv43`(与验收字节一致);
> 远端原始日志与逐题产物保留在各新 run 根,本仓只收可审计派生结果。

## 0. 结论

**在同一份冻结 298 题、同一修复版代码(`eb3ba7f`,代码身份
`07fef84f…`)、同一 v1 资产、同一 scorer v2 下,D-3(reactant_similar
通道开启,D1 固定参数)相对 C0(通道关闭)在全部主对照 K 上净落后:**

| 指标(分母恒 298) | C0 | D-3 | 净差(D-3 − C0) |
|---|---:|---:|---:|
| hit@1 | **136(45.6%)** | 132(44.3%) | **−4(−1.34 pp)** |
| hit@3 | **182(61.1%)** | 174(58.4%) | **−8(−2.68 pp)** |
| hit@5 | **186(62.4%)** | 182(61.1%) | **−4(−1.34 pp)** |
| hit@10(宽度说明) | 186 | 182 | −4(hit@10 恒等于 hit@5) |

- 完整性门:**两臂 298/298 合法终态、配对门禁 `complete`、
  `release_eligible=true`**;逐题配对四格在每个 K 均恰为 298(§4)。
- 逐题配对(@5):both 178、C0_only 8、D3_only 4、neither 108;
  D-3 题级赢/输/平 @1 = 5/9/284、@3 = 2/10/286、@5 = 4/8/286。
- 差异构成(§5):27 题命中状态变化中,3 题由 D1 相似通道**直接改变路由**
  (novel→analogy_edit,全部为 C0 命中、D-3 落空),16 题有 D1 召回但路由
  未变(任务上下文变化 + 模型抽样),8 题**无任何 D1 召回差异**(任务载荷
  逐字段实质相同,仅身份字段不同)——该 8 题的分歧只能来自模型抽样噪声
  (temperature 未设,提供方默认非确定性)。**单次真实模型抽样不能证明
  确定性因果**;本轮 −4/−8/−4 是"D1 通道效果 + 抽样噪声"的混合观察。
- **发布默认值不变**:`reactant_similar_enabled` 默认仍为 `false`。本轮
  结果只是"已见 298 题、这次冻结配置下观察到的差异",不得用于改发布
  默认值,也不得称独立外部验证。

## 1. 发车前硬门(全部完成后才发生首个付费调用)

| 门 | 事实 |
|---|---|
| 修复验收 | R1 修复报告 `ready_for_298`,无 unresolved 项([EC298_PHASE_D_R1_REPAIR_REPORT.md](EC298_PHASE_D_R1_REPAIR_REPORT.md)) |
| Git 状态 | 开工 HEAD `eb3ba7f7dc52fdccad4956346bfd2c5cefe1e7f4`(分支 v4.3),工作树干净;旧产物零改写(远端旧 run 目录 mtime 复核:ec298_v43r1 2026-09-24、phase_d_* 2026-09-28 晨、r2 2026-09-28 15:13,均早于本会话) |
| 代码身份 | aggregate `07fef84f0945bcba055a6424d37efcab2c60ebf47cd1d639d676dd00133764bc`(50 文件),本地与 Chenyu 一致;**部署对齐披露**:远端 `domain/policy.py` 曾与验收字节不一致(旧默认 `reactant_similar_enabled=True`)→ 以验收字节同步;远端 src 内 75 个 macOS AppleDouble 垃圾文件(`._*`,污染代码身份)→ 删除(清单留远端);对齐后远端代码身份 = `07fef84f…`,124/124 文件 SHA 与本地一致(本地多 2 个与本轮无关的离线诊断脚本) |
| 资产双清单 | manifest `ac9b97b872c9666eebbe32b42c626997aca34438ade17d7bbf36a8154b848e6c`,22 文件 / 166,849,006 字节,v1 运行资产,v2 不进运行时;本地与远端同值 |
| 本地回归 | `OMP_NUM_THREADS=1 PYTHONPATH=src python -m pytest tests/ -q`(python 3.11.16 / rdkit 2026.03.6)→ **456 passed / 0 failed,474.57s**;含 worker 子进程/崩溃注入/resume/终态/归并/配对门禁端到端 |
| Chenyu 回归 | 同命令 `.venv` → **456 passed / 0 failed,655.36s** |
| 无金标夹具 | 本地与远端各跑一次 `run --model off`(合成底物 pb_0117 root_smiles,非 298)→ completed + 导出 verify ok,答卷 SHA `8e6ba1b8…` **逐字节一致**(跨机确定性);远端首次尝试因 shell 引号转义错跑底物,已删除并以 python 精确传串重跑(如实披露) |
| 价格快照 | 2026-09-29 刷新(官方文档逐字取数):input ¥0.8/M、output ¥2.8/M、cache read ¥0.23/M、RPM 200、TPM 3,000,000、cn-beijing、按量计费;与 2026-09-25 旧快照同值(旧快照仅作历史);env 三键当日实核(模型 ID 匹配/DashScope 域/key 存在,只验存在性) |
| 输入锚 | 源 CSV `a3cb7955…`、`questions.jsonl` `9f5955d4…`、白名单 `exam_inputs.jsonl` `cb5996c9…` 独立重算一致;298 qid 唯一、与题卷顺序逐一相同、逐题 substrate 相同、白名单字段恰为 qid/substrate_smiles/input_index(0 金标字段) |
| 实验登记 | `docs/EC298_PHASE_D_RETEST_REGISTRATION.md`(原文 SHA `449ea043…`)先于发车落盘;**勘误 #1(两臂 batch identity SHA)于首次付费调用之前追加**(17:26Z;首次付费调用 = 烟测 r2,2026-09-28T17:35:12Z);勘误 #2(引擎臂/烟测事实/首次付费时刻)在烟测完成后、两臂运行开始前追加(17:47Z,仅追加不回写) |
| 烟测 | r1(pb_0117,两臂语义):管线 + D1 修复路径验证(d3-like 资格 applicable、selected=reactant_similar_channel、donor_ref 无 TypeError),0 模型调用(该底物唯一 recorded 直通,如实记录);r2(pb_0002,**首次付费**):2 次真实调用 2 ok(0 失败/孤儿/429),usage 2/2,已知部分费用 ¥0.0761,独立烟测账,不进臂账本 |

## 2. 冻结身份与两臂隔离

- **两臂配置(38 个扁平键比较)唯一差异 =
  `prediction_policy_overrides.reactant_similar_enabled`(false/true)**;
  机器可读 diff `reports/phase_d/retest/config_diff.json`(SHA
  `005056e4…`)。D1 固定参数(threshold 0.45 / top_k 16 /
  max_analogy_donor_candidates 3)两臂取值相同;关闭臂该参数惰性
  (`workflow/nodes.py` 强制 threshold/top_k = 0/0)。
- **两臂批次身份(实机落盘,58 个扁平键比较)唯一差异同一键**;
  C0 `31549aab3db5fd2ef832996d5622d80ec8e17984e5b32e19a966455ac3b42df8`,
  D-3 `cfe1534a93d7fe1596f997272cb2e3260001f0861ecd4d66f286c6e99b2495b4`;
  两臂 `input_manifest.json` 逐字节相同(同一冻结白名单);run_id 由
  身份短哈希 + qid 显式派生,不从目录名反推;每题 run_identity 内
  `prediction.policy.reactant_similar_enabled` 与臂语义一致(C0=False /
  D3=True,逐臂抽查确认)。
- 身份与本地 dry-run 计算值**逐一相同**(跨机一致性:本地与远端代码/
  资产/配置逐字节一致)。
- 共同变更(相对首轮 298,两臂同值、看分前冻结):`llm_timeout_s`
  900→3600(用户 2026-09-29 指令拆时间墙);`batch_cost_cap_cny=null`
  与 `rate.max_calls=10,000,000`(用户 2026-09-29 指令:不设费用上限、
  不设 issued 停止线);资产清单 21→22 文件(Phase D 加入 v2 语料,
  运行时不用)。单步协议与其余配置与首轮 298 身份一致
  (max_depth=1、max_expansions=1、max_frontier_width=5、
  max_llm_calls=3/题、max_proposals=1/题、max_http_retries=4、
  reasoning_effort=max、每步最多 5 个可报告产物)。

## 3. 两臂执行事实(顺序运行:先 C0 后 D-3)

| 项 | C0(17:49–18:17Z,28 分钟) | D-3(18:19–18:53Z,34 分钟) |
|---|---|---|
| 终态 | **completed**:286 success + 12 awaiting_prediction | **completed**:285 success + 13 awaiting_prediction |
| failed / export_failed / missing | 0 / 0 / 0 | 0 / 0 / 0 |
| 归并 | 298 行、298 唯一 qid | 298 行、298 唯一 qid |
| answer_kind | full 286 + empty 12 | full 285 + empty 13 |
| issued 调用 | 187(186 题各 1 次 + 1 题 2 次;112 题零调用走 recorded 直通) | 187(分布与 C0 逐题相同) |
| 响应 | 187 ok / 0 失败 / 0 孤儿 / 0 次 429 | 187 ok / 0 失败 / 0 孤儿 / 0 次 429 |
| usage | 187/187 齐全(缺 0) | 187/187 齐全(缺 0) |
| tokens | 输入 345,123 / 输出 1,656,491(思考 1,554,372) | 输入 356,637 / 输出 1,764,086(思考 1,660,114) |
| 费用估算(快照价) | **¥4.8911** | **¥5.2016** |
| 在途实测峰值 | 33(提供方正常响应) | 32 |
| 配对门禁 | ok(六层全过) | ok(六层全过) |
| seal | 309 文件,清单 SHA `e83ad533…`,泄漏扫描 0 违规(601 文件) | 309 文件,清单 SHA `ac1e0d2c…`,泄漏扫描 0 违规 |

- 40 题目 worker、共享持久闸门(RPM 180 / TPM 2.7M / max_in_flight 40 /
  max_calls 10M)、`OMP_NUM_THREADS=1`、nohup 落盘 + 短连接查进度;
  闸门全程未停止;无 respawn、无墙钟击杀、无 resume(两臂一次跑完)。
- 空答构成:仅 D-3 空答的 3 题全部是 D1 相似通道 selected 的题
  (§5);仅 C0 空答的 2 题(RXNG_31299a2c…、RXNG_e11a1cac…);
  其余空答两臂共有(模型显式弃答/编辑拒绝的合法停留)。

## 4. 评分与逐题配对(scorer-2,两臂同一引擎文件)

- 正式 `v43-ec298-scorer-2`(零 LLM);两臂均从原始候选 SMILES 现算
  `cn_identity`;计分单位为整条候选字符串;分母恒 298;两次评分传入
  **同一个**引擎结果文件(SHA `0e16268c…`,§6);金标 SHA `9f5955d4…`
  随评分文件封存。配对按显式 qid 联结;评分前两臂各自通过
  `v43-pairing-gate-1` 六层完整性门(独立重读 worker 终态/身份自洽/
  归并元数据/逐路线答卷 SHA/行唯一性),verdict = **complete**。
- 逐题 298 行配对表:`reports/phase_d/retest/scoring/paired_scoring_298.tsv`
  (qid、两臂 rank、@1/@3/@5 命中、n_predicted、answer_kind、
  stop_reason、route_state、首位产物、来源 evidence_id/kind/report_rank;
  JSON 版含逐题调用/重试/孤儿/usage 状态)。
  **首位产物来源(修订 v2)**:merged 答卷的 step 不含来源字段,来源引用
  从封存裁决产物 `results/T_*/report_adjudication.json` 的
  `products[reportable=true]`(按 `report_rank` 排序)重建,并与 merged
  `predicted_products[0]` 逐题交叉核对:填充 C0 286/286、D-3 285/285
  (恰为各臂非空答卷数),**首位产物不匹配 0 题**(脚本内置校验,见
  `paired_scoring_298.json` summary.first_product_source)。首位产物的
  card_kind 分布:C0 recorded 182 / novel 91 / analogy 13(空答 12);
  D-3 recorded 182 / novel 86 / analogy 17(空答 13)。注意此口径是
  **首位报告产物的卡类型**,与 §4 末的 prediction_mode(决策层路由
  分布)是两个不同层面,不能互相替代。

| K | C0 | D-3 | both | C0_only | D3_only | neither | 和 | D-3 赢/输/平 |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| @1 | 136 | 132 | 127 | 9 | 5 | 157 | **298** | 5/9/284 |
| @3 | 182 | 174 | 172 | 10 | 2 | 114 | **298** | 2/10/286 |
| @5 | 186 | 182 | 178 | 8 | 4 | 108 | **298** | 4/8/286 |

- 双命中 178 题内位次比较:C0 更靠前 11 题、D-3 更靠前 6 题、相同 161 题。
- 输出宽度:C0(0/1/2/3/4/5 个产物)= 12/125/31/22/31/77 题;
  D-3 = 13/129/32/23/27/74 题(有效宽度不足如实披露:两臂各约 4 成题
  只报 1 个产物)。
- 多组分敏感性(探索性另表,不与主分数混算):C0 149/195/199;
  D-3 145/187/195("任一组分命中"口径)。
- 路由模式分布:C0 recorded 直通 112 / rank 70 / analogy 25 / novel 91;
  D-3 recorded 112 / rank 70 / analogy 30 / novel 86 —— **D1 通道把 5 题
  从 novel 转到 analogy_edit**;模式级命中率:C0 analogy 8/25(@1),
  novel 38/91;D-3 analogy 6/30,novel 35/86;recorded 直通两臂相同
  (64/112 @1)。

## 5. 逐题差异分层(27 题命中状态变化;证据可回查)

分层口径(§登记 §8):A = D1 相似通道 selected 且路由改变;B = 有 D1
新召回(n_similar_channel_refs>0)但路由未变;C = 无 D1 召回差异。

| 层 | 题数 | @1 方向(C0 更好 / D-3 更好 / 仅位次移动) | 事实 |
|---|---:|---|---|
| A(sim-selected 路由改变) | 3 | 1 / 0 / 2 | 全部 novel→analogy_edit;3 题均为 C0 命中、D-3 落空(2 题 D-3 空答 = 编辑弃答/被拒,1 题 D-3 有答卷但未命中);另 bd85ad14…(非分歧题,C0 两臂皆未命中)同为 sim-selected 且仅 D-3 空答 |
| B(有召回、路由未变) | 16 | 6 / 4 / 6 | 相似供体进入资格块/任务上下文(位移卡 displaced 留痕),模型输入变化 → 输出变化 |
| C(无召回差异) | 8 | 2 / 1 / 5 | **任务载荷逐字段实质相同**(run_id/task_id/path_id/时间戳与由此派生的哈希除外),分歧只能来自模型抽样噪声 |

- 全 298 题分层事实:D-3 相似通道有召回的题 265/298(C0 为 0,符合
  设计);**selected(实际采用相似供体)11 题**;资格状态变化 25 题;
  路由变化 9 题;供体评估总数 887(C0)→ 894(D-3),被相似通道位移的
  卡 228 张(逐题 `displaced_by_similar_channel` 留痕)。
- 50/298 题两臂首位产物不同(全部发生在调用模型的题内);其余 248 题
  首位产物逐题相同(recorded 直通 112 + 模型题中输出一致的题)。
- 层级证据引用:逐题事件/卡/验证文件在远端各 run 根
  `runs/ec298_pd_retest_{C0,D3}/runs/<run_id>/results/T_*/`
  (decision/validation/report_adjudication/cardval.*);本地汇总
  `reports/phase_d/retest/scoring/deepdiff_298.json`(298 行,schema
  `ec298-pd-retest-deepdiff-2`,含六层字段与来源引用)。**报告层(L6)
  口径(修订 v2)**:读取 `report_adjudication.json` 的
  `products[reportable=true]`(report_rank 排序)——`n_report_products`
  为可报告产物数(两臂 max 恰为 5、0 题越界;裁决总候选数另记
  `n_adjudication_products_total`,如某题 503 选 2),`report_evidence_ids`
  为可报告产物的 evidence_id 列表。r1 版曾误读不存在的 `report/entries`
  键且把全部候选计入报告层(max 505、286/285 题"越界"),已废弃并
  保留于 `scoring_r1_superseded/`(§12)。
- **限定**:相似召回/applicable 增加不是命中证据;A/B 层差异不能与 C 层
  噪声在单次抽样下定量分离;3 题 A 层损失是本轮唯一可归因到 D1 通道的
  直接证据,方向为负。

## 6. 引擎背景参照(不参与主配对)

- 首轮封存引擎臂资产清单(21 文件)与本轮部署(22 文件)不一致,按
  任务书 §5.3 未直接复用;**另跑零 API 引擎臂**(同一冻结白名单、当前
  代码/资产):298/298 ok,`engine_results.jsonl` SHA
  `0e16268c375585f622f826a3649ef272f70154d22b2bae02c6e99b90537992cf`。
- 引擎 Top-10:@1/@3/@5/@10 = 118/174/193/209;两臂评分共用此同一文件
  (引擎数字两臂完全相同,仅作背景)。
- **稳定性检查**:本轮引擎臂与首轮封存引擎臂**逐题首命中 rank 完全
  一致(0/298 差异)** —— 引擎/资产行为跨版本跨次运行稳定;agent 臂
  与首轮的差异来自 agent 侧代码修复(Phase B/C/D)与模型抽样,不是
  引擎漂移。
- 封存 `pool_identities` 只覆盖导出 Top-10,不得称为完整候选池。

## 7. 费用账(诚实口径;未回填账单前不报费用门绿)

| 项 | 调用数 | usage | tokens(in/out,其中思考) | 估算(2026-09-29 快照价) |
|---|---:|---|---|---:|
| C0 臂 | 187 | 187/187 | 345,123 / 1,656,491(1,554,372) | ¥4.8911 |
| D-3 臂 | 187 | 187/187 | 356,637 / 1,764,086(1,660,114) | ¥5.2016 |
| 烟测(独立账) | 2 | 2/2 | 4,451 / 25,922(24,160) | ¥0.0761 |
| **合计** | 376 | 376/376 | — | **≈ ¥10.17(全部调用 usage 齐全,无 unknown 残差)** |

- 两臂各 187 调用全部正常响应、0 失败/0 孤儿/0 次 429:本轮**没有缺
  usage 的调用**(与首轮 5 次超时不同——`llm_timeout_s=3600` 下无超时
  截断),`cost_estimate_cny` 为全量估算而非部分小计;思考 token 按
  提供方计费口径计为输出。**按纪律,该估算仍须以服务商账单回填核对后
  费用门才可报绿**;逐调用明细(时间/attempt/HTTP 尝试/usage)在
  `reports/phase_d/retest/{C0,D3}_api_calls.tsv` 与远端各 run 产物。
- 无任何费用上限触发(用户 2026-09-29 指令不设上限;闸门从未因预算/
  费用停止)。

## 8. review 硬门自检(任务书 §6"任何一项缺失则不得写 complete")

| 硬门 | 状态 | 证据 |
|---|---|---|
| 修复未通过 review | 通过(ready_for_298) | §1;R1 修复报告 |
| 金标进入运行侧 | 否 | 白名单三字段结构校验 + seal 泄漏扫描 601 文件 0 违规;金标只在封存后评分进程打开 |
| 两臂输入或 D1 开关外配置不一致 | 否 | 批次身份 58 键 diff 恰 1 键;配置 38 键 diff 恰 1 键;manifest 逐字节相同 |
| 错用多步预算或 scorer-1 | 否 | 单步预算冻结(§2);正式 scorer-2,两臂同函数同规则 |
| 任一臂异常失败/缺题/导出失败/身份或 SHA 不符 | 否 | 两臂 298/298 合法终态,0 failed/missing;身份/答卷/资产 SHA 逐一复核 |
| 只看 298 行而不核终态 | 否 | 配对门禁六层(独立重读 worker 终态)先于读答卷,verdict=complete |
| 缺 usage 被报成已知总费用 | 否 | 376/376 调用 usage 齐全;仍标"须账单回填核对" |
| 旧 run 被覆盖 | 否 | 旧 run 目录 mtime 复核早于本会话;本轮产物全部在新根 |
| 只报总体分数而无逐题配对 | 否 | 298 行配对表 + 四格(和=298)+ 赢/输/平 + 逐题分层 |
| 并发实测峰值不足 40 | 已单独披露 | §9 |

## 9. 并发证据与披露

- **实测峰值:C0 = 33、D-3 = 32 个提供方正常响应同时在途**(以请求
  发出/响应结束的单调时间戳重叠计算;限流拒绝/失败不计;闸门持久
  `peak_in_flight` 证据 + 响应产物 `sent_at/done_at/request_id/
  status/usage` 逐请求可查)。
- **仓内可独立复核(修订 v2)**:逐请求派生表
  `reports/phase_d/retest/{C0,D3}_inflight_events.tsv`(各 187 行,零
  凭证:qid/run_id/task_id/attempt/request_id/sent_at_epoch/
  done_at_epoch/duration_s/http_status/total_tokens),由
  `scripts/ec298_pd_retest_inflight.py` 从封存响应产物只读重导;
  峰值用与批次协调器**同一函数同一口径**
  (`pathway_v43.exam.inflight_evidence`)重算:C0 33/32 记录值复核
  一致(peaks_match=true),D-3 32/32 一致;摘要见
  `{C0,D3}_inflight_summary.json`。r1 版后处理只保留峰值、丢弃逐请求
  时间区间,仓内无法复核——该缺陷已修(driver 现落盘
  `_inflight_requests.json`,§12)。
- 未达 40 的原因(如实披露,与首轮 33 相同):298 题中 112 题为
  recorded 确定性直通(无模型调用),需要模型的题目在补位调度下的
  重叠不足以填满 40 槽;两臂均未设发车屏障(生产纪律),未用伪请求/
  重复请求/recorded 题强制调用凑数。**该项判为"工程验收未完全达标,
  如实标注"**,不影响 298 配对完整性门。

## 10. 限定与结论措辞

1. 本轮是**已见题集的修复后复测**(`seen298_post_hoc_repair_check`),
   题卷对模型/工程均非首次;不得称独立外部验证。
2. 结论只能是:"**在已见 298 题、这次冻结配置下观察到的差异**:D-3
   相似供体通道(D1 固定参数)开启后 hit@1/@3/@5 净差 −4/−8/−4 题**"。
   差异含 D1 直接路由效应(3 题,均向负)与模型抽样噪声(8 题无通道
   差异的分歧);单次抽样无法把两者定量分离。
3. `reactant_similar_enabled` 发布默认保持 `false`;不得用本轮逐题
   答案调 D1 阈值/排序/预算/prompt 后再称独立验证;如需改变发布默认
   值,另提独立数据与发布审查。
4. C0 本轮 136/182/186 与首轮 v43r1(116/128/130)不同源不可比:首轮
   跑在 Phase B/C/D 修复前的代码上;旧 Phase D r1 四臂的受污染分数保留
   为历史诊断,不作本轮基线。
5. 题卷来源与检索语料的潜在重叠未经单独审计;本轮为单步酶促污染物
   转化,不证明多步 pathway 准确率。

## 11. 产物索引与复现

**本仓(可审计派生结果,均入 git)**:`reports/phase_d/retest/`
- `config_diff.json` / `ec298_pd_retest_C0.json` / `ec298_pd_retest_D3.json`
  (两臂配置与机器可读 diff);
- `local_identity_snapshot.json` / `local_pytest.log` / `remote_pytest.log`
  / `local_tree_manifest.txt` / `provider_price_snapshot_2026-09-29.json`;
- `ec298_pd_retest_driver.py`(身份/运行/后处理三段驱动,
  `--phase identity|run|post`;v2 起后处理落盘 `_inflight_requests.json`
  逐请求表)、`ec298_pd_retest_smoke.py`(发车烟测)、
  `ec298_pd_retest_pairing.py`(门禁+评分+配对;v2 起首位产物来源从
  裁决产物重建并交叉核对)、`ec298_pd_retest_deepdiff.py`(逐题分层;
  v2 起报告层按 products[reportable] 口径)、
  `ec298_pd_retest_inflight.py`(并发逐请求派生表+峰值复核,新增)、
  `ec298_pd_retest_seal.py`(封存审计);
- `C0/`、`D3/`(两臂身份/归并答卷/汇总/seal 拉回副本)、
  `scoring/`(pairing_gate、score_v2_C0/D3、paired_scoring_298
  .json/.tsv、multicomponent、deepdiff_298;**v2 重生成版**)、
  `scoring_r1_superseded/`(r1 派生表存档,见 §12)、
  `{C0,D3}_api_calls.tsv`(逐调用账)、
  `{C0,D3}_inflight_events.tsv` + `{C0,D3}_inflight_summary.json`
  (并发逐请求派生表与峰值复核,新增)、`engine_arm_metadata.json`、
  `smoke_summaries.json`。

**远端(Chenyu dependingv43,原始产物,不入仓)**:
`runs/ec298_pd_retest_C0/`、`runs/ec298_pd_retest_D3/`(exam_inputs、
input_manifest、batch_identity、workers/、logs/、gate/、runs/(298×
checkpoint+results)、merged/、_arm_summary、_seal/);
`runs/ec298_pd_retest_engine/`;`runs/ec298_pd_retest_smoke/`;
`runs/ec298_pd_retest_pre/`(driver/配置/回归日志/夹具);
`reports/phase_d/retest/scoring/`(评分原始输出)。

**复现命令**(零 LLM 判分/分析部分;路径显式、无凭证入仓):

```bash
# 门禁 + 评分 + 配对(Chenyu,零 LLM)
cd /usrdata/EnzymeCAGE_data/workspaces/dependingv43 && \
OMP_NUM_THREADS=1 PYTHONPATH=src .venv/bin/python \
  scripts/ec298_pd_retest_pairing.py \
  --c0-root runs/ec298_pd_retest_C0 --d3-root runs/ec298_pd_retest_D3 \
  --engine-results runs/ec298_pd_retest_engine/engine_results.jsonl \
  --gold /usrdata/EnzymeCAGE_data/workspaces/ec298_gold_readonly/questions.jsonl \
  --out-dir reports/phase_d/retest/scoring

# 逐题分层差异(Chenyu,零 LLM)
OMP_NUM_THREADS=1 PYTHONPATH=src .venv/bin/python \
  scripts/ec298_pd_retest_deepdiff.py \
  --c0-root runs/ec298_pd_retest_C0 --d3-root runs/ec298_pd_retest_D3 \
  --out-dir reports/phase_d/retest/scoring

# 臂封存审计(Chenyu,零 LLM)
OMP_NUM_THREADS=1 PYTHONPATH=src .venv/bin/python \
  scripts/ec298_pd_retest_seal.py --arm-root runs/ec298_pd_retest_C0   # 同 D3

# 全仓无凭证回归(本地/远端同命令)
OMP_NUM_THREADS=1 PYTHONPATH=src python -m pytest tests/ -q
```

(臂运行复现:`ec298_pd_retest_driver.py --phase identity|run|post`
命令见 `runs/ec298_pd_retest_pre/ec298_pd_retest_driver.py` 文档串;
运行侧复现受模型非确定性影响,同配置重跑的逐题答卷不保证逐字节一致。)

## 12. 修订记录

### v2(2026-09-29,R2 外部 review 修复)

review 指出三处问题并"暂不接受 complete"——已全部修复,主分数未受
影响,complete 结论维持:

1. **[P1] 首位产物来源未交付**:r1 配对脚本从 merged 答卷不存在的
   `steps[].source` 字段取来源,导致 286/285 个非空答卷的
   evidence_id/kind/report_rank 全空。修复:从封存裁决产物
   `report_adjudication.json products[reportable=true]`(report_rank
   排序)重建,并与 merged 首位产物逐题交叉核对(0 不匹配);填充率
   286/286、285/285。
2. **[P1] deepdiff 报告层读错 schema**:r1 读不存在的 `report/entries`
   键,`report_evidence_ids` 全空;`n_report_products` 计入全部候选
   (max 505、两臂各 286/285 题"超过 5")。修复:改读
   `products[reportable=true]`,两臂 max 恰为 5、0 题越界;裁决总候选
   数另记。schema 升 `ec298-pd-retest-deepdiff-2`。
3. **[P2] 仓内无法复核并发峰值**:r1 后处理只保存峰值、丢弃逐请求
   时间区间。修复:新增 `scripts/ec298_pd_retest_inflight.py` 只读
   重导逐请求派生表(187+187 行,零凭证),用与批次协调器同一函数
   同一口径重算峰值:C0 33、D-3 32,与记录值一致(peaks_match=
   true);driver 后处理同步改为落盘 `_inflight_requests.json`。

**不变性证明(修复前后逐项比对,`scoring_r1_superseded/` vs
`scoring/`)**:score_v2 两臂 summary 相同;paired_scoring 的
hits/四格/赢输平相同;298×2 逐题 `agent_rank` 全部相同;deepdiff
决策层指标(召回 265/selected 11/资格变化 25/路由变化 9)相同。
修复只影响逐题证据列(来源引用、报告层)与并发复核材料,零 LLM、
零付费调用、封存运行产物零改写(全部只读重导)。

**对本报告的影响**:§4 补首位产物来源口径与填充统计;§5 补报告层
口径;§9 补逐请求派生表与峰值复核;§11 产物索引更新;登记勘误 #3
追加(见 EC298_PHASE_D_RETEST_REGISTRATION.md)。
