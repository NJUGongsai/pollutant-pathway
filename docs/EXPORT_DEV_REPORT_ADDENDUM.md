# v4.3 第四阶段补充报告:dev 批跑复核轮、超时证据与跨迭代状态泄漏修复

> 本文是 `EXPORT_DEV_REPORT.md`(主报告,批次 c366e724)的**补充评审材料**,来自同日另一执行线的独立复核轮 dev 批跑与代码修复。所有运行在 Chenyu `/usrdata/EnzymeCAGE_data/workspaces/dependingv43_dev`(py3.12 venv,资产 21/21)。

## A. 复核轮 dev 批跑(r2/r3)与超时证据

主报告批次 c366e724(max_depth=6, max_expansions=40)冻结 `timeout=300s`,48 次调用中 **18 次传输失败(全部为 300 秒超时)**,导致多数路线停在 `awaiting_prediction`(模型调用耗尽重试仍未返回)。复核轮验证这是**基础设施参数问题,而非模型/策略能力问题**:

| 轮次 | timeout | 停止(completed/awaiting) | API 调用 | 传输失败 | cn step hit@1/3/5 | route_recall | spurious |
|---|---|---|---|---|---|---|---|
| r2 (`devbatch_v43r2`, depth=3/exp=24) | 300s | 12 / 8 | 36 | 17 | 0.2271 / 0.2271 / 0.2271 | 0.4365 | 0.0000 |
| r3 (`devbatch_v43r3`, 同 r2, 仅 timeout→900s) | 900s | 15 / 5 | 32 | 5 | **0.2512** / 0.2512 / 0.2512 | **0.4535** | 0.0417 |

- 同一代码、同预算,超时从 300s→900s:完成路线 12→15,cn hit@1 0.2271→0.2512,route_recall 0.4365→0.4535。深层路线的思考链经常超过 300s(实测成功调用 128–432s,超时调用恰为 900s 封顶值)。
- r3 中唯一仍超时的路线 pb_0471(depth 3 病态长链)连续 900s 超时烧完预算,归并仍从账本重导出其已提交事实(部分答卷)。
- **EC298 冻结采用 timeout=900s**,依据即此差异;其余冻结项(reasoning_effort=max 等)不变。两轮逐题产物、API 账与 eval JSON 原样保留在远端 `runs/devbatch_v43r2|r3/`,汇总副本在本仓 `reports/export_dev/`。
- 与主报告 c366e724(depth=6/exp=40,hit@1=0.3333)口径差异说明:其展开预算更深,数字**不可与 r2/r3 直接比较**;三者在"答卷只由已校验可报告候选构成、同判分器同切分"上口径一致。

## B. 历史 v4.1 dev 对照(部分覆盖,标注后仅供参考)

以同一冻结评测器对 `dependingv4_v41/runs/dev_hybrid_v41` 重打分(route_id 从目录名恢复,历史产物 `route_id` 字段为 null):

- **仅 10/20 路存在**(pb_0313 之后缺失),为部分覆盖的历史对照臂;
- cn:hit@1=0.2126 hit@3=0.3237 hit@5=0.3671;route_recall=0.3334;**spurious=0.4411**;gold_leaf=0.4325。
- v4.3(r3,20 路)hit@1=0.2512、spurious=0.0417:方向上 hit@1 更高、幻觉率大幅更低;hit@5 低于 v4.1(0.2512 vs 0.3671)与 v4.3 答卷**不含未验证检索补位**直接相关(见主报告口径说明)。两者输入/配置/覆盖均不同,**不作为同口径提升声明**。

## C. 发现并修复:预测状态跨迭代泄漏(P1)

**现象(dev 首跑 pb_0065 实际触发)**:`select_frontier` 不清理上一路径的 `state.predicted_evidence_id` 等引用;当路径 A 经模型 rank 选卡提交后,后续路径 B 进入 validate/commit 时仍读到 A 的选中 ID,在 B 的检索集中找不到,误入"提案卡"分支取 `proposed_card` → `KeyError` 崩溃;若陈旧 ID 恰好存在于 B 的检索集,则**静默提交错误证据卡**。

**修复**(`workflow/nodes.py`):
1. `select_frontier_node` 在进入新路径前重置全部迭代草稿引用(`retrieval_task_id/decision_task_id/validation_task_id/prediction_task_id/predicted_evidence_id/prediction_mode/...`);
2. 提案卡读取改为 `_load_proposed_card` 结构化失败(`NodeStateError`,带 path_id/evidence_id/任务 ID),不再裸 KeyError。

**回归测试**:`tests/test_state_isolation.py`(模型选卡提交→子路径确定性提交;修复前以 monkeypatch 复现崩溃,修复后通过)。本修复随 v43r3、EC298 引擎臂/agent 臂一同生效。

## D. 已知问题移交 review

1. **远端(py3.12)孤儿恢复测试不稳定**:`test_prediction_recovery.py::test_dangling_request_orphan_audited_then_retried_once` 在远端全量跑两次失败(本地 py3.11 连续 10/10 通过;失败先于上述任何修复存在)。症状:resume 后孤儿审计卡缺失、调用从 a1 重发。疑似 langgraph 1.2.12 checkpoint 与 `os._exit(70)` 注入时序在 3.12 下的差异,需要专门排查;生产侧由协调器 respawn 兜底,r3/EC298 运行未受影响(0 孤儿、0 重复)。
2. **dev 各轮 hit@1=hit@3=hit@5**:已提交事件的第二个及以后可报告产物从未命中金标;与"深度路线因超时停在浅层"叠加有关,r3 深层仍受限。EC298 为单步,不受此影响。
3. 费用口径:usage 缺失的失败调用使批次级费用按纪律标 `unknown`(known-usage 部分单独估算,见主报告与 EC298 报告)。
