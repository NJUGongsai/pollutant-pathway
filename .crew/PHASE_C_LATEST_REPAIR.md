# Phase C 最新修复交接（二轮复核闭合声明）

> 来源：Phase C 实施会话的收尾交接评论（2026-09-28）。这是小队接手的基线事实。

修复完成：二轮复核的阻断 P1 和三个 P2 全部闭合，全仓回归 387 passed / 0 failed,离线审计重跑后各臂计数不变(金标诊断仍 8/23)。

## 需要知道的协作情况

另一会话今下午也在实施同一份复核(它做了 P1 的候选集收窄、rule 卡夹具、裁决层字段修正和 export 侧工作，最后一次写入是 11:47 的 Phase B 报告)；我做其余部分，双方文件零冲突，全仓回归覆盖了双方改动。

## P1:rank 选中原始 rule/analog 卡直提(三层防御 + 双卡反例夹具)

- 任务候选层：rank 的 candidates 只含同底物且通过 recorded 完整资格判据的卡；原始 rule/analog 卡不再进可选集，解析层引用即 invalid_evidence_id → 有界重试 → 停留。(候选集收窄由另一会话落地，已核实行为)
- 验证层：validate_products 新增防御——模型 rank 选择的检索层卡 kind 非 recorded → 全部产物拒绝，稳定拒因 rank_selected_non_recorded;提案卡(novel/analogy)不在检索集、不受影响(第一版误伤了合法提案流，已用 card_in_retrieval 区分修复)。
- 裁决层：检索层原始卡即使被选中，card_eligible=false、产物零占位；order 内合格 recorded 照常排名，不牵连。
- 夹具：rule 和 analog 各一对(端到端"选原始卡 → 零事件零裁决"+ 裁决层纯函数"构造选中原始卡载荷 → 零占位")，analog 镜像按复核反例新写。

## 三个 P2

1. 审计金标覆盖门禁：从"零交集才拒"升级为所有任务 qid 必须在金标中且唯一，金标为空/缺题/重复任一即失败退出；新增 tests/test_phase_c_audit_guards.py,用 tmp 假封存端到端跑脚本，含"金标删一题必须失败"反例。
2. 编辑协议严格化：逐操作允许字段表，未声明字段拒 edit_invalid:unknown_field:<name>;旧别名 remove_bond/add_bond 改为 edit_invalid:unknown_op(直接拒)。封存再分类有一行因 add_atom 带多余 atom2 字段导致拒因文本顺序变化，分类与计数不变。
3. 对齐枚举显式上限:_ALIGNMENT_ENUM_LIMIT=2000(RDKit 缺省 1000 也会静默截断)，触顶标 alignment_limit_exceeded 并 fail-closed——已评估有目标 → ambiguous(截断集合不得当唯一适用目标)，全败 → unavailable(不得假阴性 inapplicable);封存 66 题均在限内，计数不变。

## 验证与产物

全仓 387 passed(含双方新增测试)；审计重跑 exit 0,gold_coverage_gate=all_task_qids_in_gold_and_unique、66/66,再分类 1/22、金标 8/23、接纳 0/15、消融 23/43 全部不变，产物已重新生成。报告 docs/EC298_PHASE_C_REPORT.md 新增二轮复核声明、§7.1(P1 修复详情)和 §11.9,§10 更新了 387 实测与新 SHA。复核要求的"三轮入口"材料(反例夹具、P2 失败测试、重生成审计产物、测试结果)已齐；**工作树未 commit,提交时机由用户掌握**。
