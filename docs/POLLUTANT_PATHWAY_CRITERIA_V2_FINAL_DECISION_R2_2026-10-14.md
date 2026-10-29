# ppv1-criteria-v2 第二轮终裁（本地代审，2026-10-14）

> **通道声明**：本报告是主会话在用户授权下的**本地代审**，不是正链 Codex
> 链式 fork 评审，不署名 Codex、不替代正链最终裁定权。正链额度恢复后，
> 放行类结论可由正链复核确认。**v2 是否生效（判据冻结）仍由 CC 拍板。**
> 题域标签：298=RHEA 通用酶学/已见题；本文数字为工程验收口径
> （测试计数/探针），非判分成绩。

## 一、身份与输入

| 项 | 值 |
|---|---|
| 待审 HEAD | `dda852ba71cd41518d2cf390ee843c4db8508633` |
| 直接父 | `873c323116e065ca7596f7655bbf74f31c3881f3`（C 线共底物供给） |
| 上轮终判 | `docs/POLLUTANT_PATHWAY_CRITERIA_V2_FINAL_DECISION_2026-10-14.md`（终判：不放行，唯一余项 P1） |
| 交付书 | `docs/POLLUTANT_PATHWAY_CRITERIA_V2_P1FIX2_DELIVERY_2026-10-14.md` |
| 评审请求 | `docs/REVIEW_REQUEST_CRITERIA_V2_FINAL_R2_2026-10-14.md` |
| Python | `python_version.txt`（depending43，见证据目录） |
| 落盘时间 | 2026-10-14 17:29 CST |
| 工作树 | 除既有用户差异（`M docs/...PREREGISTRATION...`，未碰）外干净；本审零改动、零提交、零 push |

## 二、固定验收（上轮有限验收原文转述）

R1 余项 P1：`7e7855c` 版首次消费对完整 appearance 集合漏验（非 dict 静默
跳过 + 未复用哈希校验 + state_id 绑定缺失），官方链接纳而同库重放拒。
复审只验三条：①两反例首消费结构化拒绝、链第一步截断、底层可追溯；
②合法多出现正控完整导出、公共重放幂等；③既有闭合（原 cn 负控、零出现
负控、合法边界、P2 批级=逐边和、缺省 v1 字节不变）+ 全量零翻转。
C 线只看污染，不阻塞本轮。

## 三、独立执行（隔离 /tmp，禁字节码/缓存写入）

1. **探针 HEAD 复跑**：`git archive HEAD src/tests` 到新隔离目录，探针复制件
   运行（合成 O2，全程 /tmp 建库）。EXIT=0，断言全过——合法 6 步全绿、
   重放 `created=false`；`[]` 反例 `payload_not_object`、错绑旁证
   `appearance_hash_mismatch`，均为 1 步（`after_step=read_endpoint`），
   重放同判 `Ppv1LedgerCorrupt/appearance_hash_corrupt`，两路已无分裂。
   见 `probe_rerun_head_summary.json`。
2. **新测试 4 件 + 关联文件**：隔离目录 `test_ppv1_s4b_export.py` +
   `test_ppv1_criteria_v2_exemption.py` 共 **42 passed**。第三分
   `state_id_binding_mismatch`（重签腐蚀，`native_result.py:180`）由
   `test_native_build_rejects_appearance_state_id_binding`（`:986-1013`）
   覆盖通过。
3. **全量 not-slow（HEAD 工作树）**：**2135 passed / 0 failed / 16
   deselected**（314s，EXIT=0），与请求稿口径 `2125+10=2135` 一致。
   见 `full_head_tail.txt`。
4. **读码核对**：`store.py:464` `_verify_appearance_content_hash` 为唯一
   哈希判据，被首消费（`native_result.py:143,160`）与收集/重放三入口共用；
   `dda852b` 未碰 `evaluation.py/s5b_scoring.py`（判分侧零改动）。
   字节四对照复核交付证据全 `equal:true`，哈希与请求稿一致；重构消息
   `3/3 byte-identical`。
5. **C 线零重叠**：`git diff-tree` 两 commit 文件面交集为空（判据线 4 文件
   vs C 线 10 文件），C 交付书已如实登记并行改动归因。只记污染结论，
   不评 C 线本身。

## 四、结论：建议放行（本地代审建议）

上轮唯一余项 P1 已闭合：完整出现集合三查落地、单一验证源无分裂、两反例
截断可追溯、正控幂等、既有闭合与字节不变保持、全量零翻转。**建议放行，
即 v2 可生效**——最终生效仍待 CC 拍板（判据冻结属用户裁定）；正链额度
恢复后可做一次正链复核确认。

证据目录（未跟踪）：`docs/review_evidence/criteria_v2_final_r2_local_2026-10-14/`
（`commands.txt` / `probe_rerun_head_summary.json` / `full_head_tail.txt` /
`python_version.txt` / `SHA256SUMS.txt`，自哈希除外）。完整探针输出与全量
日志原文在仓外隔离目录（易失），备查可按 `commands.txt` 重跑。
