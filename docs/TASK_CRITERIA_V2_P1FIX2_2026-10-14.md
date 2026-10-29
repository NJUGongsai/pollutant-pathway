# TASK — criteria-v2 终裁余项修复：appearance 首次消费完整集合校验（2026-10-14）

> 派单：主窗口（终判不放行余项，回修循环自动续轮）。执行：实施
> 子代理。终判报告：
> `docs/POLLUTANT_PATHWAY_CRITERIA_V2_FINAL_DECISION_2026-10-14.md`
> （余项=唯一阻塞 P1，验收标准在其"下一次复审的有限验收"节）。
> 探针（可复跑同构）：
> `docs/review_evidence/criteria_v2_final_codex_2026-10-14/p1/participant_appearance_probe.py`。

## 一、缺陷（终判已实证，先自己复现确认）

`native_result.py:119-123`（`_validate_native_state_rows` 的 appearance
索引循环）：非 dict 的 `payload` 被静默跳过；同 state 只要还有一条
合法 dict appearance 就不触发 unverifiable；但**原始 appearances
列表仍完整进入 native_result 与导出**——坏权威记录被重新包装消费。
且未复用既有 appearance 内容哈希校验（`store.py` 的
`_verify_stored_appearances` 重放侧每行核 `appearance_hash`——同库
重放拒 `appearance_hash_corrupt` 而官方首次消费接纳，两路分裂）。
旁证：appearance.payload.state_id 改错绑（`store._split_state_payload`
把 state_id 放进 appearance，但拼接字段清单不含 state_id）同样漏验。

## 二、修复要求（终判验收原文，逐条落）

在 `build_native_result` 验证处对**被消费的完整 appearance 集合**核验：

1. **对象形状**：非 dict payload ⇒ 结构化拒绝（不静默跳过）；
2. **state_id 绑定**：appearance 的 state_id 与语义块/行键一致；
3. **appearance_hash 内容绑定**：与已有写入/重放的验证来源**共用**
   （提取/复用 `store._verify_stored_appearances` 的内容哈希校验逻辑
   为单一来源，不另立判据）——不静默丢弃坏行、不重算新哈希洗损坏。

## 三、验收（自测，主会复核）

- 终判的两个反例（`[]` payload 主反例、错绑 state_id 旁证）在首次
  消费被**结构化拒绝**，后续 persist/export/reader/evaluator 不执行，
  底层损坏信息可追溯；
- 合法多出现正控仍完整导出；公共 `submit_event` 重放幂等（合法侧）；
- 既有全部闭合保持：原 cn 腐蚀负控、零出现负控、合法结构/CN-only
  边界、P2 批级=逐边和、缺省 v1 字节不变（双树对照）；
- 新增测试（形状拒绝/绑定拒绝/哈希拒绝/合法正控）+ 全量 not-slow
  零翻转（基线 2121/0/16）。

## 四、红线（特别标注）

- **不 git add、不 git commit**——并发 C 实施轮在同一工作树在跑，
  本轮改动留在工作树由**主窗口统一收口提交**；
- 判分侧零改动（evaluation/s5b_scoring 不碰）；
- 金标/题面零触碰（探针全用合成 run）；零模型零网络；
- 只改 src/tests 本轮范围文件+新增证据目录；不动既有 docs/AGENTS。

## 五、回传义务

文件清单+行数、两反例拒绝输出（结构化错误原文）、合法正控/重放
幂等输出、字节不变与全量红绿、一切偏差如实。第一步先在
`docs/review_evidence/criteria_v2_p1fix2_2026-10-14/` 落
START_MARKER+progress。
