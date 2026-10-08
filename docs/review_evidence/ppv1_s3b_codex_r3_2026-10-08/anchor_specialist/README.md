# S3b-r3 独立锚定/公开恢复专项

实际日期 2026-10-08。实际 HEAD `adf0287abef0c4803962fee0df0065d8e6f3793d`，直接父 `2bedfc060a9b19019ba44aa2a56dcacb88450c3b`。仅工程合成规则级，不代表 dev(B1) / 298(RHEA) 科学性能，不冻结判据，不包含 S4/S5。

全部执行在 fresh `/private/tmp/ppv1_s3b_r3_anchor_8dzzx_8b`；当前源码 src/vendor 与 pyproject metadata 先复制、SHA 固定，原 R2 永久证据只读、脚本/两反例 JSON 先复制。历史 JSON 的绝对运行路径只用于比对，绝不执行。Python depending43 `-B` / PYTHONDONTWRITEBYTECODE=1，未跑 pytest、未调用外部模型/真实 provider、网络请求计数 0，未访问金标、题面、封存逐题 run 或 dependingv4，主仓既有文件不改，无 commit/push。两个控制器各一次 exit 0，未额度中断、未重复行为执行。

## 结果与精度

- `observations_r2.json` 是原控制器原文件名，实际代码/输入 HEAD 为本轮 r3，不沿用旧脚本命名当 HEAD：21 顶层观察全部符合既定契约。两个原 B3/B4 自洽 artifact 重封装反例（旧根摘要 `880bf6c37d09af15db7a82ad19cfd9aa4b4d1d52eab0efe256e8dd08babdeb94`、新 artifact 内容摘要 `7164d4f966b107f19544e5e0a0cac7a4a80ce22e7f289f24a5ebc8c7fe3acd04`）均 `frozen_plan_binding_mismatch`，root retrieve done，十五表相等；B3 events0/commits2、B4 events1/commits2 不增，被改 artifact 字节保全。
- 原控制保留：四硬杀合法 public start/resume＋重复零新增；same/omitted 计划合法、changed/decide_changed 先拒；坏 bundle hash/JSON 被 blocked 及权威 event/reservation 损坏先拒；转换正常/0入队/转换创建后/转换后 followup 未complete 的四窗口恢复 phase-1；三产物正常与2/3硬杀恢复3/3（max_total_search_actions=30，预算放宽同 R2 复审，不冒称完整输入与旧20相同）；两真正 workflow.runner.resume_run 进程的 barrier 胜者在 expand 持锁、败者在GO前 driver_session_active、实际工具收据1、原 attempt/预约ID接管保持。
- `anchor_observations_r3.json` 17 顶层观察。11 个必要锚/字段坏/全 done 后 self-consistent 包/显式提供同新 plan 的拒绝控制全部先于 recover_run/drive/工具：instrument entries 0，十五表零变化，artifact 保全。三拒种分别 frozen_plan_anchor_missing、frozen_plan_anchor_corrupt、frozen_plan_binding_mismatch。缺/坏锚同时覆盖 B3/B4；其他字段入口是同一首消费守卫。
- novel 非空/空池真实工具2/1、events2/1，网络0；empty pool abstain 请求1/events0 合法；zero_depth stop 的 primary=budget_limit、other_reasons 含 depth_limit、blocked对象持久1且重复报告一致。两个 novel 原 oracle 错误要求 model_requests 恰1，输出实为3/2（额外请求归产物后续 decide），工具、事件、独立hypothesis、生产报告链均正确。按已有完整输出将此 oracle 纠正为至少1，不重跑，不回写 raw observations。
- 另两个小控制：单独把 payload.plan_version 改为 ppv1-frozen-plan-999 / 删除，再重封信封，自身 plan 与根锚摘要仍完全是原值。public B3 resume 正常消费原有效 bundle，event0→1、commits2→4，无新转换/新计划/工具重执行。`_load_frozen_plan` 实际未解释这个 header。它们 raw 的“应该版本拒”探索 oracle 为 false；本专项不把仅 metadata 标签改变当错误内容接受证据，不预定新 P1，建议 **P2：冻结前明示 header 许可/消费规范或补对称校验，不能声称该字段已经拒**。代码/运行profile/schema身份守卫与独立plan内容锚是另几轴。最终范围裁定归主审。

合计 38 顶层观察：36 符合既定契约（含两项 raw oracle 更正，凭既有输出），2 个版本 header P2 边界。不是 38 pytest passed，也不是发现两个新漏洞组。raw 34 true/4 false 原样保留；精度更正见 adjudicated_summary.json。读输出阶段一次请求字段误读 `task_key` KeyError 属只读检查笔误，后续改读实际 request.action_id 字段，未重跑行为或覆盖原日志。

## 文件、源码和复现

- `scripts/review_recovery.py`、`probe_public.py`、`probe_supplemental.py`：原 R2 审核脚本复制；raw_old_scripts 保原字节；仅执行公开worker/helper而非旧 probe_public 过期 oracle 的 main。
- `scripts/review_anchor_r3.py`：本审小控制，instrument 只记录进入 recover_run/drive/真实 AtomTool；不改产品路径或判据。
- `original_inputs/`：R2 两 before/new envelope/resume 输入只读复制；`inputs/` 本轮每次实际 JSON 与变更；`logs/` 完整 command/env/exit/stdout/stderr；`tables/` 完整十五表及artifact/identity逻辑快照；`artifacts_final/` 原文件（坏文件保全、identity、driver.lock披露文本）。SQLite二进制和临时barrier未入永久包，SHA 在 omitted_binary_inventory.json。最终库逻辑快照与前后表在证据中，不倒补没采集的执行前 DB binary SHA。
- `source_review_lines.txt` 锚守卫274–390、实际start1395–1417、resume1497–1548、同源 decision_task_key 379–399。guard对本 run 的 retrieve 行逐载荷验证；非empty payload.plan_digest 的行按 decision_task_key 重算列/载荷 task_key、对照内容摘要。root已done后段仍到入口守卫；“同库全权威协调改写”不在原门范围；同机 flock 不是分布式 exactly-once。
- 拒绝“零写”只指十五业务表/event/commit/consume，无 claim/recover/tool。driver.lock 披露文件在取得会话锁后可重写，不能写成所有文件都零变化。

复现只能复制整包到 fresh tmp，建立空 logs/tables/synthetic_runs 路径；不要执行 original_inputs 的历史绝对路径；不要在永久目录原地运行。当前 src 与worker配置都指同一 absent_v3/absent_assets 根，非真实依赖。

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<newtmp>/src /Users/cc/miniconda3/envs/depending43/bin/python -B <newtmp>/scripts/review_recovery.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<newtmp>/src /Users/cc/miniconda3/envs/depending43/bin/python -B <newtmp>/scripts/review_anchor_r3.py
```

manifest.json/SHA256SUMS/manifest.sha256 三控制文件不计入 payload。SHA256SUMS 钉 payload 及 manifest 自身。元数据记录真实HEAD、schema、命令和输入SHA前后，而非旧脚本硬编码。
