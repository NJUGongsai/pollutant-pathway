# 任务书 — chain14 发车物 P1 回修轮（Codex 代审回修，2026-10-16）

> 派单：主会话（评审-回修循环；Codex 代 CC 审裁定「不放行，回修 P1-1～4」）。
> 执行者：实施子代理（单人串行）。依据：`docs/CHAIN14_LAUNCH_CODEX_REVIEW_2026-10-16.md`
> （复现证据 docs/review_evidence/chain14_launch_codex_2026-10-16/，探针脚本可
> 参考复现手法）。**只修列出的 4×P1+P2 措辞，不得顺手扩范围。**
> 基线：全量 not-slow **2175/0/16**（HEAD `b4b89dc`+未提交工作树）。
> 题域标签：**298=RHEA 通用酶学/已见题**。

## 一、四项 P1（评审已给文件:行号+最小修法）

### P1-1 反馈首发漏记真实预算

- 病灶：`runflow.py:1196` 反馈登记硬编码 SCRIPTED、`:1215` 却走 real fetch；
  `search.py:1723` 仅 real 占额度 ⇒ 组合路径（首发失败→重试坏 JSON→反馈
  首发→反馈重试）实发 4 次、只预约 3 次，每题 3 预算被旁路。
- 修法：反馈沿**实际 provider_kind** 登记；全部真实发送共用每题预算，
  第 4 次发送前被每题预算拦截（拒绝优先于 HTTP）；gate/batch 硬门不动。
- 测试：复现组合路径（评审用真实 RealModelAdapter+OpenAICompatibleClient+
  FileRateGate、urlopen 换本地桩：503→200 坏字段→503→200 合法）断言第 4 次
  发送前拒；保留正常路径+单支重试正控。

### P1-2 重试成功响应无法崩溃重放

- 病灶：`real_model.py:649` 只定位来源、`:740` 直接拒 failed、`:950` 重试
  成功只返回当次内存 ⇒ 崩溃后 resume 以 `request_not_consumable` 拒掉
  **已完整落盘的 responded blob**。
- 修法：建立可验证的「来源→唯一重试终态」链（核 run/action/provider/
  purpose/attempt/payload+retry_of 后消费既有 responded 或 sent+有效完整
  blob）；缺失/损坏/错身份继续拒；**禁止为恢复另发付费请求**；不以重算
  新键掩盖坏记录。
- 测试：公开 start→崩溃注入（评审用既有 `after_request_registered` 钩）→
  同配置 resume：先败后成功场景零新增调用恢复（负控=坏 blob/错身份仍拒；
  正控=单次成功同点崩溃可恢复）。

### P1-3 worker 恢复参数不匹配

- 病灶：`s5b_worker.py:170-173` 对 resume 传 `profile_policy=None`，
  `runflow.py:1837` 签名无该参数 ⇒ 合法中断 run 被写成 `failure_kind=
  TypeError` 失败终态。
- 修法：删无效参数、保留显式开关；验证**中断 run 同臂恢复成功+换臂拒绝**
  （沿真实协调者冻结→公开 crash 注入中断→公共 worker 恢复路径测，不能只
  测直接 runflow resume）。

### P1-4 已冻结 A 的副本丢失后静默变 B

- 病灶：`s5b_orchestrator.py:166` 整文件缺席返回 None→`s5b_worker.py:91`
  转 True ⇒ 实际载荷/case=on 而批报告=off（错账）；`:792` 终态读不核臂、
  `:892` 批级开关从协调者内存写。
- 修法：可信批上下文**显式传预期 bool**；worker 要求冻结副本**在位+严格
  bool+同值**（缺席=拒，不回退）；手动兼容若保留须显式进手动模式；
  case 在 skip/汇总接纳前核同源开关。
- 测试：评审反例复现（真实协调者冻 False→worker 启动前移走副本）修后
  必须**拒绝**；正常在位 A 正控保留。

### P2（非阻塞，措辞更正一并做）

交付书 §四/重试节关于「逐 HTTP 尝试留痕」的说法更正为如实（`llm_client.
py:500` 成功路径未 append http_attempts=旧诊断缺口，gate 诚实/调用行仍在；
成功/异常/429 同源补记留后续轮）。**不改 llm_client 行为**（非阻塞项）。

## 二、红线

1. 只修上述四项+措辞；A 臂字节兼容/判分/池/检索零触碰；重试族与
   gate_max_calls=4470 不动（评审裁定④：重试吃每题 3 预算之一，不抬门）。
2. 零金标零题面零模型零网络（修复合成验证）；不 commit 不 push；
   `PYTHONDONTWRITEBYTECODE=1`；python=conda depending43。
3. 全量 not-slow 2175/0/16 零翻转（新增测试另计）。
4. 复现不了评审反例=停下报告（其探针脚本在证据目录）。

## 三、回传义务（≤25 行）

①四 P1 修复点（文件:行号）+各自新测试结果（组合路径预算拦截/崩溃重放/
中断恢复/副本丢失拒绝）；②全量数字；③P2 措辞落点；④偏差（有必列）；
⑤交付书追加「P1 回修轮」节。主会话核对后走 Codex fork 同范围复核
（新父会话 01a141bc-6c7b）。
