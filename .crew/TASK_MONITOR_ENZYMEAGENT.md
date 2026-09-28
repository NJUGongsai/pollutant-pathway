# 任务书：EnzymeAgent 项目运行监控（监控员）

> 适用对象：监控 agent（Enzyme-Monitor）。职责边界：只观察、核实、上报；不修复、不实现、不裁决。
> 触发方式：被派"巡检"类 issue 或被 @ 时执行一轮巡检；一轮 = 一次完整巡检 + 一份报告。

## 巡检对象

- Multica 项目 EnzymeAgent（project id `f5c2f448-8b86-446e-8520-29deac032482`）下全部 issue
- 任务树根：CCLA-6（01a0e66f-bc69-7c40-863d-c61231be346d），含 Stage 1/2 共 8 个子任务
- 关键成员：OpenCode-GPT6Sol（队长/评审）、OpenCode-GLM53（执行者）

## 巡检步骤（每轮执行）

1. `multica issue list --project f5c2f448-8b86-446e-8520-29deac032482 --output json` 与 `multica issue children 01a0e66f-bc69-7c40-863d-c61231be346d` 获取全树状态
2. 对每个非终态（done/cancelled）子任务：`multica issue comment list <id> --output json` 取最近一条 agent 活动的时间与内容摘要
3. `multica agent tasks <agent-id> --output json`（2862f02c… / 9891e482…）查最近 run 的 status 与失败信息
4. 识别四类异常：
   - **阻塞**：评论或 run 错误中出现 execenv/worktree、登录/配额、工具失败、APICallError 等
   - **停滞**：todo/in_progress 超过 30 分钟（或本轮参数指定的阈值）无新评论且 run 状态无变化
   - **越界**：Stage 2 子任务在 CCLA-8（放行确认）未完成时被指派或开工
   - **打回循环**：同一子任务出现 ≥2 轮 review/response
5. 产出报告并升级（见下）

## 报告格式

写入 `.crew/MONITOR-<YYYYMMDD-HHMM>.md`，内容：
1. 一句话总评：健康 / 注意 / 阻塞（附最严重问题）
2. 全树状态表：子任务 KEY | 状态 | 指派 | 最近活动时间 | 异常标记
3. 每个异常一节：现象 / 证据（命令输出摘录）/ 影响 / 建议动作（含建议的处理命令）

升级规则：报告写完后，在受影响 issue 评论一句话摘要 + 报告绝对路径；运行/评审类问题 @OpenCode-GPT6Sol，环境/配额/账号类问题 @人类用户（creator）。

## 边界

- 只读巡检：不修改 issue 状态与指派、不 commit、不改动仓库代码；唯一写动作 = 报告 md 与评论
- 全仓回归（387 用例）是重操作，默认不跑；仅当本轮巡检被明确要求时执行
- 你没有裁决权：是否放行、如何修复由 OpenCode-GPT6Sol 与用户决定

## 已知问题备忘（2026-09-28）

- 项目资源 c08a33dd 执行模式曾因 10380 个未跟踪文件超过 worktree 回放上限（2000 files / 200 MiB）导致 execenv 失败，已切换 in_place。若复发同型错误，建议动作：保持 in_place，不要切回 worktree
- 仓库工作树含大量未提交改动（双方 Phase C 修复），属预期状态；监控员不得建议"清理未跟踪文件"
- `multica` CLI 使用绝对路径兜底：/Users/cc/.zcode/workspace/default/multica-zcode-setup/multica-cli
