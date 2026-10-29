# 任务书 — chain14 发车物 P1-2 收口轮（第四轮，2026-10-16）

> 派单：主会话（评审-回修循环第四轮）。依据：Codex 复核2 的 P1-2 余项
> findings（`docs/review_evidence/chain14_launch_codex_rereview2_2026-10-16/
> feedback/findings.md`——**评审报告正文因额度中断未落盘，该 findings 与
> 运行日志裁定行为准**：P1-4 已闭合；P1-2 单一余项=复用前身份核验漏口）。
> 基线：全量 not-slow **2192/0/16**（主会话独立复跑确认）。
> 题域标签：**298=RHEA 通用酶学/已见题**。**只修这一项，不扩面。**

## 一、余项（评审 findings 原文口径）

**病灶**（两处语义漏）：
1. `model_protocol.py:306-327` `latest_format_feedback_round` 取到既有行后
   **只校 purpose**，返回整行直接复用——未核验原行 `run_id/action_id/
   attempt_id/provider_kind/payload_hash/retry_of` 与原登记及本次调用的
   对应关系（runflow.py:1214-1243 直接 fetch；real_model.py:651-671/699
   的 responded/sent 分支无首次身份核；:837-865 failed 分支核了来源与后继
   却未核原反馈来源 payload_hash）。
2. **原键缺失**（原行 request_id 被改坏）：`:306` 数到 1 轮、`:309-314`
   推得原第 1 轮 ID 却取不到 → `:315-316` 返回 None → runflow:1221-1227
   走新登记（model_protocol.py:378 rounds_used+1 构成第 2 轮新键）⇒
   **2→3 另发一次并完成，原坏行仍在**——违背「不为恢复另发付费请求、
   不用重算新键掩盖坏记录」。

**修法**（findings §三）：
- 复用既有反馈轮**之前**统一核验原登记身份/内容/执行引用，**所有适用
  状态共用**（responded/sent/registered/failed 一套判据）；
- 保留原请求键、坏行及原反馈/响应的可核验身份，不以新登记或重新生成
  内容身份洗掉坏记录（`recorded_at` 不许重算冒充——`model_requests` 只存
  payload_hash，需保留足够原登记事实供同源验证；不指定存储结构）；
- **已有轮计数>0 却查不到应有原行 ⇒ 结构化拒绝**（不返回 None 走新登记）；
- 保持既有正控与预算语义（3→3/2→2、预算第 4 次发送前拒、轮数判据）。

## 二、测试矩阵（评审 result.json 8 场景对齐）

公开 start→反馈重试成功→解析前崩溃→受控损坏→公开 resume，逐场景断言
**零新增调用/零新轮/坏记录保全**：

| 受控损坏（现状=被接受/另发） | 修后必须 |
|---|---|
| responded 原行 run_id / attempt_id / provider_kind(real→scripted) / payload_hash 改坏 | 结构化拒（identity 类 reason，坏行保全） |
| sent + provider 改坏 | 同上（状态分支同规则） |
| registered + provider 改坏（现状 2→3 另发） | 结构化拒，不分配新轮 |
| failed 原行 payload_hash 改坏（后继完整） | 结构化拒 |
| **原行 request_id 改坏（现状 2→3 另建第 2 轮）** | **结构化拒（计数>0 无原行）** |
| （正控保持）3→3 反馈重试成功恢复 / 2→2 单次成功恢复 | 照常完成 |

## 三、红线

只修本项；P1-1/P1-3/P1-4 及全部既有正控不动；A 臂字节兼容/判分/池/
检索/重试族/gate4470 零触碰；零金标零题面零模型零网络（合成验证沿评审
手法：start_ppv1_run(scripted=True, provider_kind=real)+合成 CCO+桩状态机）；
不 commit 不 push；`PYTHONDONTWRITEBYTECODE=1`；python=conda depending43；
全量 not-slow 2192/0/16 零翻转（新增测试另计）。

## 四、回传义务（≤20 行）

①修复点（文件:行号）+统一身份核验的判据清单；②8 场景矩阵测试结果；
③全量数字；④偏差（有必列）；⑤交付书追加「P1-2 收口轮」节。主会话核对
后走 Codex fork 同范围复核（父 01a14229；账号额度 11:44 重置，注意时序）。
