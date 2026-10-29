# REVIEW REQUEST — ppv1-criteria-v2 判据级复审（2026-10-14）

> 请求方：v2 确认窗口（主会话）。通道：Codex 正链（新会话，本文件为
> 自包含评审请求）。发起 cwd = v43 仓根。
> 评审性质：**判据级必过审**（冻结/放行类轮次）——通过后 ppv1-criteria-v2
> 正式生效（chain13 起新批次按预注册以 v2 出数）。

## 一、评审对象与背景链

- **对象**：ppv1-criteria-v2 判分面参与物豁免实现（提交 `84a9eb4`，
  evaluation.py +647 行、s5b_scoring.py 版本承载、recorded_source.py
  NC-12 前提域重写、新测试 16 件）及其预注册。
- **裁定链**（全部在仓内可读）：teacher 裁定 b 档
  `docs/TEACHER_DECISION_PPV1_T1_COSUBSTRATE_TIER_2026-10-12.md`
  → CS2c 探针 N1=16 → mimo r36 有条件放行九条件
  `docs/mimo_ppv1_chem_review_response_r36.md` → 补证 N1''=13 →
  冻结拍板包 `docs/TEACHER_T1_FREEZE_DECISION_PACKAGE_2026-10-13.md`
  → **teacher 批复三项全批**
  `docs/TEACHER_REPLY_PPV1_T1_FREEZE_APPROVAL_2026-10-13.md`
  （SHA256 `76c4f7d2…`=approval_source；附加要求 1 双口径判分已兑、
  要求 2 CO₂ v2.1/v3 消解已按 known gap 登记）。
- **预注册**（状态已翻 confirmed_2026-10-14，含确认读记录）：
  `docs/POLLUTANT_PATHWAY_CRITERIA_V2_PREREGISTRATION_2026-10-13.md`
- **交付书/任务书**：`docs/POLLUTANT_PATHWAY_CRITERIA_V2_DELIVERY_2026-10-13.md`、
  `docs/TASK_CRITERIA_V2_EXEMPTION_IMPL_2026-10-13.md`
- **独立佐证**（v44 线跨树核验）：hpc2 两臂双口径重判的 v1 复现守门
  逐位一致（v43 代码 v1 ≡ v44 树官方判分）：
  `v44/reports/ppv1_s5b/hpc2_a/v44_dual_caliber_rescore_v2.json`

## 二、评审问题（读码级，逐条给结论）

1. **条款一致性**：实现 vs 预注册逐条款——豁免身份集（产物侧 H₂O/
   H⁺/Pi/PPi + 反应物侧仅 H₂O/H⁺ 的方向限定）、三谓词（pred1 声明链
   fail-closed / pred2 元素账 / pred3 cn 身份）、完备二分单归属
   （`v1_exempt | not_exempt_maintains_partial` 无第三态）、辅因子硬
   拒绝表、零碳断言、豁免集∩许可集=∅ 断言——是否全部如实落字、
   有无静默偏差。
2. **字节不变性**：缺省 v1 路径零行为差的测试与探针是否充分
   （提交声明：298/298 桶/rank/edge/节点全零漂移 + G01 配对对照
   delta 恰 +16 + 全量 2117/0/16 零翻转）；是否存在任何缺省路径
   上的可观察副作用（schema/聚合/异常路径）。
3. **误豁免面（最高优先）**：任何能造成"不该豁免却被豁免"的路径
   ——pred1 声明链解析的宽松点（悬空引用/方程缺失/条目不可解析是否
   全部 unknown→不通过）、pred2 计数账的边界（P/O 记账轴两侧、
   not_applicable 的适用范围）、pred3 cn 收敛的变体覆盖（质子化变体
   组是否照抄补证脚本 V1_VARIANTS 且幂等）、辅因子族的变体逃逸。
4. **漏拦截面**：豁免被用于洗白机制主张的可能路径；参考侧监控
   （reference_side_v1_identity_signal）与退出条件接线是否正确。
5. **测试充分性**：16 件新测试的负控/正控覆盖（三谓词各 fail 路径、
   unknown 路径、方向限定、硬拒绝、零碳、交集断言、tier 单归属、
   H⁺/[H] 无合流）有无明显缺口。
6. **NC-12 前提域重写**：措辞与既有断言的一致性；运行时字符串
   产物载荷未动的声明是否属实。
7. **诚实性披露**：chain12 解锁 0 vs 探针 13 的差异解释（声明链
   全空 ⇒ fail-closed；探针读题卷侧数据判分面不可消费=实现更诚实）
   是否成立、表述是否如实。

## 三、纪律（必须遵守，写死）

- 只新增：评审报告落 `docs/`（命名
  `POLLUTANT_PATHWAY_CRITERIA_V2_CODEX_REVIEW_2026-10-14.md`）+
  证据目录 `docs/review_evidence/criteria_v2_codex_2026-10-14/`；
- **不动**：src/、tests/、既有 docs/、AGENTS.md、任何仓内既有文件；
- **不访问**：金标/题面（questions.jsonl、reference_graphs/、
  metrics 逐题内容、gitignored reports 下逐题数据）；封存 run 只读
  名义也不进；
- 不 push、不 git 提交、不调用任何外部模型；
- 报告数字/结论一律带证据（文件:行号或命令输出）。

## 四、报告格式

- P1（阻塞生效）/ P2（放行前应修）/ P3（登记即可）分级清单，每条带
  文件:行号证据；
- 终判定三选一：**放行（v2 生效）** / 有条件放行（列条件） /
  不放行（列 P1）；
- 对 §二 七个评审问题逐条结论（过/不过/存疑+证据）。
