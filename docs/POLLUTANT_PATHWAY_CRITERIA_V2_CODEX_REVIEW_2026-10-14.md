# ppv1-criteria-v2 判据级 Codex 复审报告（2026-10-14）

> **Provenance**：通道 B 正链（ChatGPT.app codex CLI 新会话
> `01a13833-22e2-7e02-b832-08b22b6bda26`，gpt-6.1-sol，reasoning=ultra）。
> 评审中途**账号额度耗尽**（重置 14:24），终判与 P1/P2 结论已在额度
> 中断前收敛并完整输出；正式报告文件未及写盘——本文由主窗口从
> 证据目录三分支笔记+运行转录组装（转录全文
> `review_evidence/criteria_v2_codex_2026-10-14/run_log_transcript.txt`，
> 1634 行）。额度恢复后以同会话续跑补正式收口。
> 评审纪律遵守：只新增证据目录；src/tests/既有 docs 零改动；未访问
> 金标/题面/封存数据；实际 HEAD=0ba764f 与目标 84a9eb4 的 src/tests
> diff 为空（评审对象即 84a9eb4 实现+已确认预注册）。

## 终判：**不放行**（1 P1 阻塞 + 1 P2 + 若干 P3）

> 判定理由（Codex 原文）："确认 1 个阻塞，即官方链仍接收并重新封装
> 身份已损坏的记录。本次没有实证错误分数。"
> 修复验收后复审放行。

## P1（阻塞）：官方 S4→评测首次消费接受已损坏的权威 state，cn 身份依赖未闭合

- **限定名称**：不得命名为"真实完整 score 链已将 O₂ 错豁免为水并产生
  strict"——该执行没有证明后一件事。
- **证据**（`false_exemption/source_corruption_output.json`）：
  - 新合成 run 的合法 O₂ state，只改 SQLite payload `cn_identity`
    `O=O→O`（结构/state_id/schema 未动）；
  - 既有 `ChemicalState.from_dict` 正确拒绝
    （`state_fact_rederivation_mismatch`，provided O vs rederived O=O）；
  - 但真实官方链 read_endpoint → build_native_result → persist →
    export → 默认 reader → 默认 evaluator **全部接纳**（9 步 ok=true）；
    当前被评事件仍是 partial、豁免计数 0、坏 state 未被事件引用——
    **无实证错误分数**。
- **违反的既有合同**：AGENTS.md:67-68/75-78（接受已损坏权威记录=
  可升级阻塞；既存 state 首用与 replay 共用身份校验）；S5 消费合同
  （官方 reader 首次消费完整性）；预注册 pred3 依赖"声明 cn 已与
  真实结构事实闭合"前提。
- **入口定位**（Codex 读码）：`native_result.py:77-89,169-176`
  raw SQL/`_rows_sorted` 不做状态事实重算；`native_export.py:886-900`
  graph facts 校验只比当前源内容摘要（坏源重聚合后摘要一致）；
  `evaluation.py:1311-1327,978-986` 继续消费声明 cn。
- **修复验收**：上述坏源 state 在**原生构建或官方首次读取/评分消费
  处被拒绝**，保持合法 state 正控；相同身份事实校验共用现有源
  （不另立判据）；不要求补机制库或新阶段科学性能；版本/不支持边界
  与旧批零回写保持。全文：
  `review_evidence/criteria_v2_codex_2026-10-14/contract/source_corruption_classification.md`。

## P2（放行前应修）：预注册批级 tier 单归属计数缺项

- 预注册 :63 要求批级 `criteria_v2` 块含两 tier 计数；实现
  `evaluation.py:3225-3244` 只发豁免族计数与 occurrence 计数，
  **无 `v1_exempt`/`not_exempt_maintains_partial` 批计数**，且官方
  输出无法重建右侧计数（failed/mixed review 不保留在 matched-edge
  输出）。机器披露交付缺口，非 strict/误豁免证明错误。

## P3（登记即可）

1. default-vs-explicit 测试实际比较 explicit-to-explicit
   （`test_ppv1_criteria_v2_exemption.py:338,343-346`）——建议改真
   缺省回归测试；
2. 若干边界控制未永久化（反应物侧水/H⁺ 正控、产物 Pi 单独正控、
   独立 P 失败轴、元素账 unknown 层、非零 v2 聚合正控）——子评审
   已用补充合成探针闭合当前行为，建议永久化；
3. 硬拒绝表测试只核代表身份，未逐变体覆盖（不升级阻塞）。

## 七问结论（分支笔记汇总）

| 评审问题 | 结论 |
|---|---|
| 1 条款一致性 | 过（contract 分支表 1 全映射在位），除 P2 计数缺项 |
| 2 字节不变/缺省 v1 | **过**（compatibility 分支独立执行：17 直连接口用例全等+合成公共链 evaluate/score/metrics/report 哈希全等；parent/current 测试 145→161 全绿零翻转） |
| 3 误豁免面 | **P1**（见上）；另 41 例公共匹配用例+6 补充合成控制无假阳性（`false_exemption/summary.json`） |
| 4 漏拦/退出条件 | 参考侧身份信号在位；contract 分支未发现条款级漏拦 |
| 5 测试充分性 | 16 件真实断言在位；P2/P3 缺口如上 |
| 6 NC-12 前提域 | contract 分支核过（措辞与断言一致；运行时载荷未动声明属实） |
| 7 诚实性披露 | chain12 解锁 0 vs 探针 13 差异解释成立（声明链全空 ⇒ fail-closed；探针数据面判分面不可消费） |

## 分支证据索引

- `compatibility/notes.md`（Q2/Q5 独立执行+合成探针）
- `contract/notes.md`（条款映射表）、`contract/first_consumer_notes.md`、
  `contract/source_corruption_classification.md`（P1 分级全文）
- `false_exemption/`（41+6 公共匹配用例、四族探针脚本、
  source_corruption 全链记录、SHA256SUMS）
- `run_log_transcript.txt`（1634 行运行转录）
