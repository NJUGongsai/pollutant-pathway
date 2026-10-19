# 评审请求 — T-D/E E1b（T-D-A/B ppv1-criteria-v3 披露轴）实施复审（2026-10-19）

> 请求类型：**实施评审**（评审-回修循环；任务书 `docs/TASK_T_DE_E1_IMPL_2026-10-19.md` v2 §2/§3.2/§4.4）。
> 题域标签：**298 = RHEA 通用酶学 / 已见题（post-hoc）**；探针 ≠ 预注册 ≠ 成绩；零金标。
> 通道：Codex 正常通道额度断流期 → **由 CC 手动发送或代审**（provenance 如实标注；放行类结论正链
> 恢复后可复核）。
> **工作树状态**：E1b 改动**未提交**；**并行子代理仍在编辑其它文件**（T-E/E1a：`recorded_source.py`/
> `s5b_builder.py`/`s5b_worker.py`/`storage/build_identity.py`；D1.2：`s5b_compiler.py`）。
> **你的评审范围只限 E1b 文件面**：`src/pathway_v43/pollutant/evaluation.py`、
> `src/pathway_v43/pollutant/s5b_scoring.py`、`tests/test_ppv1_criteria_v3.py`、
> `tests/test_ppv1_criteria_v2_exemption.py`——读时记录四文件 sha256 并锁定；其它文件并行改动
> 不在范围、不得据此判 E1b 对错。

## 1. 你要评什么（按序，全部只读）

1. 任务书 v2：§2（T-D-A/B 全节）/ §3.2 / §4.4；
2. FROZEN_V3（语义权威）：`docs/POLLUTANT_PATHWAY_CRITERIA_FROZEN_V3_2026-10-19.md` §3、§4
   （A-1..A-8 / B-1..B-7）、§6、§8、§10；**逐条核实现与其一致**；
3. 前置 1 证据：`reports/ppv1_s5b/t_de_e1_2026-10-19/pre1_recompute/`（分臂实测基线/指纹）；
4. 实施产物：`reports/ppv1_s5b/t_de_e1_2026-10-19/e1_td_impl/`（`e1b_acceptance_results.json` /
   `e1b_acceptance_summary.md` / `e1b_pre_baseline*` / `e1b_head_batch_v1v2.json` /
   `e1b_pytest_attribution.md`）；
5. 代码 diff（锁版本）：`git diff -- src/pathway_v43/pollutant/evaluation.py
   src/pathway_v43/pollutant/s5b_scoring.py tests/test_ppv1_criteria_v3.py
   tests/test_ppv1_criteria_v2_exemption.py`。

## 2. 评审要求（P0/P1/P2 制式）

- **档 A 硬边界**：归一相等只产披露（`cn_only_normalized` 语义）、**不授 strict、不进 hit@1**、
  `tautomer_promoted_nodes` 恒空（含全批样本扫描）；match_status/严格档/**S5A-01 封顶**零改动
  （合成单测 + 批级零位移双证据）；**判分侧互变归一禁改**未被违反。
- **双臂语义**：默认臂/立体保留臂参数照 FROZEN_V3 A-2（`removeBondStereo` 保持默认=true=未核范围
  已披露）；分臂布尔/臂名/分臂指纹/归一来源逐字段；B 轴 Uncharger 启用 + ChargeParent 仅敏感性；
  **B-5 双布尔+单归属 A→B+双满足披露**；B-6 闭集机读排除（tri-state）+ 闭集断言。
- **fail-closed 无第三态**；fingerprint 照 §3 条 3（实测默认值/双臂 diff/transforms 替代登记已披露）；
- **验收逐项**（对照 §3.2 与前置 1）：P1（14/14、13/14、唯一对 `RXNG_50891a38435`）；P2（两臂 6/7——
  **注意 E1b 报 6/7 而前置 1 报 6/6：差 1 对为 composite 题 TAUTOMER 节点对，判「口径差是否合理+是否
  已如实披露」**）；N1/N2/N3/N7/N4/N5/N6；v1 字节不变 / v2 行为不变 / v3 显式启用（三断言）；
  旧批零回写；V3 重算对照读数。
- **E1b 自披露的风险项逐条判**（`e1b_acceptance_results.json`/summary 内）：N4 批级真空（合成单测
  补证是否够）；N2 沿前置 1；**45 vs 44 配对口径差**（A-1 适用面扫描 vs 母集——判语义与披露）；
  **v3⊇v2 承载选择**（单一改动点 `_criteria_exemption_enabled`；判「v3 应否独立关闭 v2 豁免」）；
  单批零读数不可外推句；慢测未跑披露。
- **测试面**：全量 pytest 归因披露（E1b 报「实施后实际树 2259 passed / 1 failed」——失败件
  `test_ppv1_s5b_hit50_w23456.py::test_w4_pool_provider_backfill_and_order` 经隔离归因到并行 E1a
  文件面（只读隔离 HEAD 树+仅 E1b 两文件 ⇒ 1 passed），**该归因是否可靠**须复核）；E1b 文件面自身
  零翻转断言。
- 终判定=「放行 / 需修正（列 P0/P1）/ 退回」。

## 3. 输出（写到文件）

`docs/T_DE_E1B_CODEX_REVIEW_2026-10-19.md`：
1. 头部：终判定 + 一句话理由 + 四文件读时 sha256 + provenance（通道）+ 读件清单；
2. FROZEN_V3 §4/§8 逐条落实核验表（A-1..A-8 / B-1..B-7 / §8 承载面 | 判定 | 证据（行号/字段）| 要求动作）；
3. 验收 §3.2 逐项判定表；自披露风险项逐条裁定；测试归因复核结论；
4. P0/P1/P2 清单；
5. 「随轮交付书可直接消费的验收结论」汇总（含 v2 承载选择与 45/44 口径差的最终裁定）。

**纪律（写死）**：只读评审+只新增本报告与你的证据文件（`docs/review_evidence/t_de_e1b_codex_2026-10-19/`）；
**不动 src/tests/既有 docs（并行子代理在编辑，禁止触碰）**；不访问金标/题面/封存逐题 run；
探针如需复跑一律新 tmp、`PYTHONDONTWRITEBYTECODE=1`、`-B`、pytest `-p no:cacheprovider`；
不 git add/commit/push；不调用外部模型/网络。