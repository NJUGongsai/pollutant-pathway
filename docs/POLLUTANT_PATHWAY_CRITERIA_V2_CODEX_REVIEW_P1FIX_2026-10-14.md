# PPV1 criteria-v2 P1+P2 修复备用通道复审

> 通道：`tokeasy/gpt-6-sol`（Codex 备用审核通道）  
> 复审对象：commit `7e7855cb3ead11c7153f57b8e47a5b018f9e4ba3`  
> 基线：`0ba764f121af8cbe001cad9442f2799cd108e21f`  
> 日期：2026-10-14

## 终判定

**放行 v2 生效。**

本结论仅是备用通道意见，不替代正链 Codex 最终裁定；放行/冻结类轮次仍应在正链额度恢复后复核确认。

## P1：官方链首次消费闭合

**等级：P1 已清零。**

`build_native_result` 在读取 `states` 和 `state_appearances` 后，按语义块与出现块逐对拼回完整 state，并调用既有 `ChemicalState.from_dict`。因此验证事实来自既有 `validate_state_object` 路径，没有在原生结果层另立化学判据。代码位置为 [native_result.py](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/native_result.py:93) 和调用点 [native_result.py](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/native_result.py:233)。入口矩阵见 [entry_matrix_and_closure.md](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/criteria_v2_p1fix_2026-10-14/entry_matrix_and_closure.md:7)。

独立性与结果：

- 合成负控将 O2 state 的 `cn_identity` 从 `O=O` 腐蚀为 `O`，官方链在 `build_native_result` 首次消费处抛出 `NativeResultContractError`，detail 为 `native_result_state_corrupt`，底层 `state_fact_rederivation_mismatch` 和 mismatch 明细保全。
- 零出现记录被 `native_result_state_unverifiable` fail-closed 拒绝。
- 合法正控可构建，重复构建 digest 一致，state 正常进入聚合载荷。
- 既有探针还显示坏 state 后没有继续触达 persist/export/reader/evaluator。

证据：[p1fix_source_corruption_output.json](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/criteria_v2_p1fix_2026-10-14/p1fix_source_corruption_output.json:36)、新增测试 [test_ppv1_s4b_export.py](/Volumes/CC/Enzyme_Agent/dependingv43/tests/test_ppv1_s4b_export.py:776)。本轮独立复跑四个关键用例全部通过，见 [README.md](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/criteria_v2_p1fix_codexc_2026-10-14/README.md)。

## P2：批级 tier 计数

**等级：P2 已清零。**

`match_reference_edges` 对每条边累计两个注册 tier，v2 时写入 `criteria_v2_tier_counts`；批级 `criteria_v2.tier_counts` 只汇总这些逐边字段，并对非法 tier 断言拒绝。代码位置为 [evaluation.py](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/evaluation.py:1554)、[evaluation.py](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/evaluation.py:1670)、[evaluation.py](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/evaluation.py:3205)。

测试覆盖了：

- `v1_exempt=1` 的正控；
- `not_exempt_maintains_partial=1` 的无中生水负控；
- 批级计数等于全部逐边计数之和；
- 两个 tier 键恒在，v1 缺省输出不出现 v2 新键。

证据：[test_ppv1_criteria_v2_exemption.py](/Volumes/CC/Enzyme_Agent/dependingv43/tests/test_ppv1_criteria_v2_exemption.py:694) 和 [test_ppv1_criteria_v2_exemption.py](/Volumes/CC/Enzyme_Agent/dependingv43/tests/test_ppv1_criteria_v2_exemption.py:722)。

## P3：回归与新增问题

**等级：P3 未发现阻塞性新问题。**

- 提交差异 `git diff ... --check` 无 whitespace 错误。
- 交付证据中的全量 not-slow 回归为 `2121 passed, 16 deselected, 0 failed`。
- v1 字节不变证据中公共链 parent/current SHA-1 均为 `48b1bdb3a0e82da8a93dea6c6004833737bd8ff1`；direct17 parent/current SHA-1 均为 `62cc9ad6d64a27b9e741e8289208a2e4695d89e4`，两组 `cmp` 均返回 0。
- 本轮独立关键测试：`4 passed in 1.15s`。

## 范围与保留事项

本复审没有访问金标、题面、封存逐题 run，也没有调用外部模型或网络。科学化学判据是否最终冻结、真实评测和正链 Codex 最终放行不在本备用通道的授权范围内。
