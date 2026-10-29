# Codex 代审 — chain14 发车物 P1-2 收口轮终审（2026-10-16）

审核对象：请求书 `docs/CHAIN14_LAUNCH_CODEX_FINAL_REVIEW_REQUEST_2026-10-16.md` 指定的 HEAD `b4b89dc4ef525ed5c729e478ff4f2e677b0e3f16` 之上未提交工作树。题域标签：**298=RHEA 通用酶学/已见题**。本审未访问金标、题面、封存逐题 run，未联网、未调用模型、未部署、未 commit/push；探针在既有隔离源码副本中执行，运行输出见 [证据目录](review_evidence/chain14_launch_codex_final_2026-10-16/README.md)。

## 1. P1-2 闭合

**结论：在本轮约定的单字段损坏合同内闭合。** `model_protocol.py:278-395` 的 `latest_format_feedback_round` 是唯一复用前门；`runflow.py:1221-1226` 是唯一调用点，并在 `ppv1_real_fetch` 之前调用。计数大于零但按原键重算查不到原行在 `model_protocol.py:331-356` 结构化拒 `feedback_round_identity_corrupt/original_row_missing`，不会返回 `None` 进入新轮登记。

门内逐列核验 `purpose/run_id/action_id/attempt_id/provider_kind/retry_of`（`model_protocol.py:357-371`），并按当前解析错误与响应摘录重算 `payload_hash`（`model_protocol.py:372-394`）。登记载荷在 `model_protocol.py:447-460` 移除 `recorded_at`，时间由 `model_requests.created_at` 承载，因此不存在用新时间戳重算相同内容冒充原登记的路径。核验通过后才进入 `real_model.py:614-769` 的 `responded/sent/registered/failed` 状态机。

注意边界：请求键和 `purpose` 同时被篡改时，计数可降为零并允许第 1 轮新登记；交付书 §十、`docs/CHAIN14_LAUNCH_IMPL_DELIVERY_2026-10-15.md:309-312` 已明确该双字段合谋不在本轮单字段主证明范围。本审将其作为后续 P2/完整性增强项，不据此重开本轮 P1-2；它不能被表述为所有任意多字段数据库损坏均已闭合。

## 2. 8 场景矩阵

**结论：覆盖声明的 8 个负控，并保留 2 个正控；独立受控复跑通过。** `tests/test_chain14_evidence_switch_retry.py:1445-1544` 逐一覆盖 responded 的 `run_id/attempt_id/provider_kind/payload_hash` 单字段损坏、sent+provider、registered+provider、failed 来源 `payload_hash`、原行 `request_id` 缺失；每场景断言零新增调用、零新行/新轮、坏字段保全及结构化拒。两项正控由同文件 `:1260-1317` 保留：预算 3 的反馈重试成功恢复为 3→3，单次反馈成功恢复为 2→2。

独立执行结果：使用既有隔离副本和合成资产身份替换层，`test_chain14_evidence_switch_retry.py` **32 passed**；连同 `test_ppv1_s5b_candidate_evidence.py` 与 `test_controlled_vocab_ci.py` 共 **70 passed**。首次未加载该替换层的 30/2 结果已保留，未计为通过；失败是资产身份前置，不是矩阵行为结论。证据见 [pytest 输出](review_evidence/chain14_launch_codex_final_2026-10-16/README.md)。

## 3. 修复无越界

**结论：未发现越界。** 当前差分文件为 `candidate_evidence.py`、`model_protocol.py`、`real_model.py`、`runflow.py`、`s5b_orchestrator.py`、`s5b_worker.py` 及两个既有测试文件；本轮收口实际新增逻辑仅在 `model_protocol.py` 与 `runflow.py`。既有复核的 `protected_scope.json` 已记录 A 臂字节兼容、判分、池、检索、重试族、gate4470 和发车脚本均未变；当前工作树 `git diff --check` 通过，HEAD 未变。未对 P1-1/P1-3/P1-4 重新立项，也未追加科学性能门。

## 4. 四条偏差可接受性

**结论：①接受，②接受，③有限接受并挂后续，④接受但按既有行为披露。**

1. 去掉反馈登记载荷的 `recorded_at` 是可接受的兼容收紧：新登记可确定性重算，旧形状 resume 失配即 fail-closed；封存只读 run 不受影响。
2. 核验门新增必填 `error/response_excerpt` 是可接受的 fail-closed 签名收紧；当前唯一调用点已同步，直接缺参不会产生静默复用。
3. `purpose+request_id` 双字段合谋不在本轮单字段损坏矩阵内，作为后续完整性增强合理，但必须保留为明确限制，不能宣称任意联合篡改已被检测。
4. resume 带 `run_error` 仍可能产出部分导出是既有行为；本轮以 `run_error.kind`、零新增调用和零新轮判定拒绝，范围内可接受。

## 5. 总裁定

按本请求书的有限验收面，P1-2 收口通过，未发现 P0/P1 新问题；**放行 HPC 发车**。放行不覆盖③所列双字段合谋，也不认证科学性能或真实 HPC 版本差异。
