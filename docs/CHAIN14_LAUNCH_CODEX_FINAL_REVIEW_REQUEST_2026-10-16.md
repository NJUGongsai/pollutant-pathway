# Codex 代审请求 — chain14 发车物 P1-2 收口轮终审（2026-10-16，代 CC）

> 代审依据：CC 委托 Codex 代其审核（结论=CC 的审核裁定执行）。本轮为
> 发车门第四轮：**只核 P1-2 最后子余项闭合与无新问题，不扩面**（P1-1/
> P1-3/P1-4 已关闭、越界面已确认零触碰——上轮 protected_scope 全 True）。
> 对象：HEAD `b4b89dc` 之上未提交工作树（四轮回修后）。
> 题域标签：**298=RHEA 通用酶学/已见题**。

【代审纪律——无沙箱全权配套约束，必须遵守】
- 只允许：读取仓库文件核对、在 tmp 隔离副本跑受控探针（禁 pyc/pytest
  缓存）、新增你的复核报告 md（建议名 docs/CHAIN14_LAUNCH_CODEX_FINAL_
  REVIEW_2026-10-16.md）与证据目录（docs/review_evidence/ 下新目录）。
- 禁止：修改 src/tests/既有 docs/AGENTS.md/任何已有文件；访问金标/题面/
  封存逐题 run；git push/commit；调用外部模型。
- 执行类声明如实标注；结论按与程序证据互证。

## 一、P1-2 收口轮修复声明（第四轮，依据实施方回传+交付书 §十）

| 项 | 位置 | 声明效果 |
|---|---|---|
| 复用前统一身份核验门 | model_protocol.py:278-395（`latest_format_feedback_round` 重写） | 所有状态分支（responded/sent/registered/failed）**共用一套判据、门在 ppv1_real_fetch 状态机之前一次性闭合**：①原登记键确定性重算定位第 rounds_used 轮（同键复算不换键）；②**计数>0 查不到原行 ⇒ 结构化拒（reason=original_row_missing，不返回 None 走新登记）**；③查到行后 purpose/run_id/action_id/attempt_id/provider_kind/retry_of 与本调用逐列一致；④payload_hash 按同源确定性载荷重算比对（登记载荷去 recorded_at 确定性化，时间由 model_requests.created_at 承载——**无 recorded_at 可冒充**） |
| 调用点 | runflow.py:1222-1228 | 传入当前解析 error 与重放响应 response_excerpt（判据④的同源重算输入） |

## 二、8 场景矩阵（新测 `test_feedback_resume_unified_identity_gate_matrix`，沿你 findings §二的受控损坏表）

| 受控损坏（你上轮实测=被接受/另发） | 修后声明 |
|---|---|
| responded 原行 run_id / attempt_id / provider_kind / payload_hash 单字段改坏 | 全部结构化拒、零新增调用、坏字段原样保全 |
| sent + provider 改坏 | 拒 |
| registered + provider 改坏（旧 2→3 另发） | 拒且**不分配新轮** |
| failed 来源 payload_hash 改坏（后继完整） | 拒（后继保全 3→3） |
| **原行 request_id 改坏（旧 2→3 另建第 2 轮）** | **拒 original_row_missing** |
| 正控 3→3（反馈重试成功恢复）/ 2→2（单次成功恢复） | 既有两测试零改动通过 |

测试：chain14 文件 33/33 全绿；全量 not-slow **2193/0/16**（=2192+1 新测；
**主会话独立复跑 394.7s 逐字相同**）。

## 三、实施方 4 条偏差（交付书 §十，请裁定可接受性）

①登记载荷去 recorded_at（跨版本 resume 旧行 fail-closed 拒；封存 run 只读
不受影响）；②核验门签名收紧为必填 error/response_excerpt（唯一调用点已
同步）；③purpose+request_id **双字段合谋**形状不在本轮矩阵/评审主证明
（单字段权威损坏）范围，列后续；④resume 带 run_error 仍出部分导出（既有
行为），拒绝以 run_error.kind+零调用/零新轮为准。

## 四、请终审的问题

1. **P1-2 闭合**：按你上轮 findings §三收口口径复核——统一身份核验是否
   所有适用入口共用、原键缺失是否结构化拒绝、坏记录是否保全、
   recorded_at 确定性化是否足以防「重算新键冒充原内容」。
2. **8 场景矩阵**：是否覆盖你上轮 result.json 的受控损坏表；正控 3→3/2→2
   是否零改动保持。
3. **修复无越界**：P1-1/P1-3/P1-4 保持关闭、A 臂字节兼容/判分/池/检索/
   重试族/gate4470 零触碰（与上轮快照比差分）。
4. **4 条偏差**可接受性（尤其③双字段合谋延后是否合理）。
5. **总裁定一行：放行 HPC 发车 / 不放行（附回修清单）**。不追加科学
   性能门；金标泄漏类标 P0。

## 五、回复格式

逐条 1–5：结论+证据（文件:行号/探针）；最后一行总裁定。
