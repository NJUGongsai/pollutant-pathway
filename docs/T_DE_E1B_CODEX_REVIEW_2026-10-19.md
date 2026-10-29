# T-D/E E1b(T-D-A/B ppv1-criteria-v3 披露轴)实施 — 代 Codex 复审报告(2026-10-19)

> **终判定:放行(P0=0,P1=0,P2=0,P3=3)。** 一句话理由:FROZEN_V3 §4/§8 逐条落实且档 A 硬边界
> (不授 strict/不进 hit@1/promoted 恒空/S5A-01 不越)有合成+批级双证据;验收复跑与归档一致、
> P2 口径差与 45/44 均机读定位且合理;pytest 失败件归因经八态对照确认可靠;最终树全量绿的评审侧
> 独立复跑 2293/0。
> 通道 provenance:CC 指派 ZCode 主会话**代替 Codex**(额度断流期);本评审执行子代理中途因 token
> 配额阵亡,盘面产物完整,主会话据盘面重建。**题域标签:298=RHEA/已见题(post-hoc);探针 ≠ 预注册
> ≠ 成绩;档 A 只披露,不构成系统能力提升。**

## 一、读时锁定(2026-10-19T16:05:41Z;HEAD `26ad119`)

`evaluation.py` `a7e5ecfd…`、`s5b_scoring.py` `4af3ed2d…`、`test_ppv1_criteria_v3.py` `fd391b5c…`、
`test_ppv1_criteria_v2_exemption.py` `9fc61237…`。读件:请求书、任务书 v2 §2/§3.2/§4.4、FROZEN_V3
§3/§4(A-1..A-8/B-1..B-7/C1-C3)/§6/§8/§9/§10、pre1_recompute/、e1_td_impl 全部产物、两 src diff(锚点级)。

## 二、FROZEN_V3 §4/§8 逐条落实核验表

| 条 | 判定 | 证据(产物字段/代码锚点) |
|---|---|---|
| A-1/S5A-01 不越 | **通过** | 合成单测+批级 N4(批内 scope!=strict 节点 0=真空如实;封顶逻辑有测)+全批 node/edge 态 v1==v3 |
| A-2 双臂独立登记 | **通过** | 默认臂(立体容忍,敏感性披露,不具 strict 准入)+候选主臂(removeSp3Stereo=False;**removeBondStereo 默认 true=未核范围,已披露**);四臂 param_sha256 与前置 1 实测登记逐臂一致 |
| A-3/A-6 分臂字段 | **通过** | 双臂布尔/臂名/分臂指纹/normalization_source/原状态/批级分列;P1 分臂报数:默认 14/14、**立体保留 13/14**(主臂待验值的诚实报数,不写 14/14 已过) |
| A-4 档 A only | **通过** | `cn_only_normalized` 披露语义;**`tautomer_promoted_nodes` 批级+全样本恒空**(D03 档 B 未解锁);不授 strict 不进 hit@1(批级 hit@1 影响none) |
| A-5 fail-closed | **通过** | 无第三态;批级 fail-closed 0 |
| B-1/B-2 | **通过** | Uncharger 默认逐组分+isomeric(非 cn 立体盲);默认单臂启用+ChargeParent 仅敏感性并列 |
| B-3 净电荷不授 | **通过** | 无净电荷对齐策略;批内无误授(N5 0+0) |
| B-5 单归属 | **通过** | 逐对双布尔+臂+指纹落账;单归属 A→B;**双满足 0(与前置 1 同)如实披露**;母集单归属 {tautomer 15, protonation 6, none 23} |
| B-6 碳酸闭集 | **通过** | 三物种经同算子 canonical 闭集+批级指纹+闭集断言(增删=升号);批内排除 0+合成钉死(含闭集外含碳正控);机读原因 `carbonate_system_exclusion` |
| C1-C3 措辞边界 | **通过** | 「互变归一(立体容忍)」「同一母体质子化表示」「同一母体对齐候选」按终审 D04-D06;不裁定 14 对同一实体 |
| §8 承载 | **通过** | v1 字节不变/v2 行为不变(**N3/N7:v2/v3 同 payload tier 逐位一致+criteria_v2 块一致**)/v3 显式启用;`PPV1_CRITERIA_V3` 常量+白名单+非法结构拒;不动 EVALUATION_VERSION/EDIT_PROTOCOL/V2 代码路径;旧批零回写 |

## 三、验收 §3.2 逐项 + 自披露裁定 + 归因复核

| 项 | 判定 | 依据 |
|---|---|---|
| P1/P2/N1-N7 | **通过(复现)** | 验收探针复跑与归档 canonical 一致(仅 provenance 差);P2 双臂 **6/7**,未命中对=composite 题 TAUTOMER 节点——**机读实锤**(`e_evidence_p2_caliber.json`:该节点 A 双臂 true/B 双臂 false;B 轴真读数 6 行 B-true=前置 1 的 6/6,`impl_vs_pre1_mismatch_n=0`);N1 双臂 0(ISOMER-TRUE 23 含 21 纯立体不塌缩) |
| v1/v2/v3 三断言 | **通过** | head_batch 探针复跑一致;v3⊇v2 单开关 `_criteria_exemption_enabled` |
| V3 重算对照 | **通过** | 批级 45 对/分臂 15,14,7,7/单归属合计闭合/promoted 恒空 |
| 45 vs 44 配对口径差 | **合理+已披露** | 批级全 298 A-1 适用面扫描 45 对 vs 来源母集 44 对,多 1 对逐条定位在 json;母集读数不受影响——两口径语义不同(适用面 vs 候选集),不属缺陷 |
| v3⊇v2 承载选择 | **裁定可接受** | N3/N7 正交性(同 payload tier 逐位一致)是承载正确性的直接证据;单开关消除 v3∧¬v2 组合态;登记承载语义:criteria_v3 启用⇒v2 豁免同时生效,不提供独立关闭 |
| N4 批级真空 | **可接受** | 批内确无 scope!=strict 节点(事实)+合成单测钉死封顶逻辑=该验收面的正确形态 |
| **pytest 归因复核(请求重点)** | **归因可靠(八态对照)** | `test_w4_pool_provider_backfill_and_order`:HEAD root **过**/E1b-only overlay **过**/E1a-only+HEAD 测试 **挂**/E1a+当前(同步后)测试 **过**/E1a+compiler **挂**/工作树副本 **过**——失败由 E1a 文件面拒因迁移(charge→tnc)+其测试同步所致,E1b 文件面无关;**E1b 文件面自身零翻转**(criteria 两文件 35 passed);最终树全量:评审侧独立复跑二跑 **2293/0**(一跑 2292/1=prediction_recovery 家族负载 flake,并入监控面) |
| 其余自披露(N2 沿前置 1/慢测未跑/单批零读数不可外推) | **通过** | 固定句与披露在位 |

## 四、P0/P1/P2 清单

**P0=0;P1=0;P2=0。** P3(登记):①prediction_recovery 家族 flake 第三件实证(全量一跑 no_recall 件挂、单跑绿+复跑 2293/0 绿)——并入 D1.2 二轮 P3-MONITOR 监控面(该家族再现即留现场根因,不得再按 flake 放行);②45/44 口径差登记句随交付书;③v3⊇v2 承载语义登记句(见 §三)。

## 五、随轮交付书可直接消费的验收结论

1. E1b 按 FROZEN_V3 §4/§8 **验收通过**:档 A 硬边界(披露不授 strict/不进 hit@1/promoted 恒空/S5A-01 不越/判分侧互变归一禁改未触碰)双证据闭合;正负控(P1 分臂/P2 双臂/N1-N7)全过且与前置 1 逐对一致;**可随轮提交**。
2. 表述纪律:A/B 属判据修正类⇒只能表述「测量修正」;C 属池策略损耗面⇒须附同口径前后对照;档 A 下 hit@1 影响=none。
3. 45/44 与 v3⊇v2 按本报告裁定登记;P2 的 6/7(含 composite TAUTOMER 节点行)与 B 轴真读数 6/6 并列披露。
4. 提交面与 D1.2/E1a 同树耦合(沿 P3-COMMIT)。

纪律:原仓写入仅证据目录与本报告;并行工作流文件零触碰;金标零接触;复跑全在 /tmp/证据目录;零外部模型。证据索引见同目录 `REVIEW_MANIFEST.json`(含执行子代理阵亡与重建说明)。
