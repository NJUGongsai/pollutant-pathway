# TASK — C 线实施：共底物伴生供给 + 声明链发射（2026-10-14）

> 派单：主窗口（CC 拍板「开干 C 线」=设计书冻结+授权实施）。执行：
> 单个实施子代理（串行）。设计书（已冻结）：
> `docs/C_COSUB_SUPPLY_DESIGN_PREREG_2026-10-14.md`——**本任务书
> 与设计书冲突时以设计书为准**。探针（数字锚）：
> `reports/ppv1_s5b/c_probe_cosubgate_2026-10-14/`。

## 一、范围（两件，同轮）

### 1. 共底物伴生供给（语义 a，build 期）

- **落点**：`s5b_builder` 的 analog 候选装配——模板袋声明的共底物
  作为**伴生参与物**并入候选净反应表示（按模板记录原样两侧、
  **精确多重集份数**），使元素守恒门通过、候选可编译。
- **池策略版本**：`s5b-pool-policy-6` → **`s5b-pool-policy-7`**
  （版本承载+run_inputs 逐条断言同步；池宽 8/阈值 0.45/排序开关/
  截断语义/融合序全部不动——**单变量=共底物伴生供给**）。
- **声明面（同点装配）**：analog 候选带
  `declared_copy_components`（复用 corpus 通道既有机制）+
  记录方程声明（`record_equation` 形态照 criteria-v2 预注册 §二.1
  消费契约：`{"reactants":[{"smiles","role"?}…],"products":[…]}`）。
- **纪律条款**（设计书 §三.5，逐条落实现）：
  - 供给份数=模板袋精确多重集（2 H₂O≠1 H₂O）；
  - 未被模板变换消费的供给组分 **spectator 披露**（逐条标记，
    不得静默）；
  - 电荷/质子化改写 fail-closed（不改现有改写行为）；
  - **方向限定**（设计书 §三）：豁免消费按 v2 方向限定条款（Pi/PPi
    仅产物侧）——这在判分侧已冻结，供给侧只须保证声明如实带侧别；
  - wildcard 袋（`*`）**不供给**（35 行维持现状拦截）。

### 2. 声明链发射（run 期，13 题豁免兑现钥匙）

- **落点**：worker 事件提交路径——事件提交时把来源记录方程写进
  provenance 链（`event.hypothesis_id → hypothesis.provenance_refs →
  payload.provenance_records 行（record_id 匹配）→ 行 payload 的
  record_equation`——**严格按 criteria-v2 预注册 §二.1 的 pred1
  消费契约**，判分侧零改动、发射侧按契约供数）。
- 发射的声明内容=候选装配时的记录方程（与 §1 声明面同一数据源，
  不另造）。

## 二、验收（自测，主会复核）

1. **解锁面复现**：对 454 行 COSUB-GATE 做 build 期重放（探针
   `unlock_sim.py` 同口径），实心解锁面应≈**45 行/35 题**（探针
   锚；实现口径差异如实披露，不硬凑数）；
2. **v2 豁免正控**：纯 H₂O 袋题（探针 11 题）新载荷经
   `criteria_version=ppv1-criteria-v2` 判分——**豁免计数>0、
   v1_exempt tier 出现**（pred1 声明链可解析+pred2 元素账过+
   pred3 cn 身份过；探针 `d2_tier_breakdown.json` 可作对照）；
3. **字节不变**：非共底物路径零行为差（v1 缺省判分零漂移——
   沿用字节不变探针模式）；
4. **测试红绿**：新增测试（伴生供给装配/份数多重集/spectator 披露/
   声明链发射/policy-7 版本断言/wildcard 维持拦截）+ 全量 not-slow
   零翻转（基线 2121/0/16）；
5. **探针级免责**：解锁面=供给面编译解锁，不是 hit 预测——交付书
   如实写。

## 三、红线

- **判分侧零改动**（evaluation/s5b_scoring 不碰——豁免面冻结在
  criteria-v2 线）；
- 金标/题面零外带（重放在本地进程内，产物聚合 only，落
  gitignored 分析目录）；
- 只改 src/tests 本轮范围文件+新增交付书；**不夹带**工作树既有
  未跟踪/已修改文件（git add 只加自己改的）；随轮本地 commit
  **不 push**；
- 池宽/阈值/排序/融合序不动；生成侧其余行为不动。

## 四、回传义务

文件清单+行数、解锁面复现数字（vs 探针锚 45/35）、v2 豁免正控
输出（豁免计数/tier 分布）、字节不变探针结果、测试红绿、commit
hash、一切偏差如实。第一步先落
`reports/ppv1_s5b/c_impl_2026-10-14/` START_MARKER+progress（防
无痕死亡）。

## 五、排障

- 探针脚本可复用（`c_probe_cosubgate_2026-10-14/` 下
  unlock_sim.py 的语义 a 逻辑=实现参考）；
- 判据语义拿不准（声明链契约细节）停下写报告，不自行扩范围；
- corpus 通道 declared_copy_components 机制=既有同源参考
  （`recorded_source.py`/`s5b_compiler.py` 一带）。
