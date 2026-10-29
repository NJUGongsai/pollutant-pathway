# 终裁请求第二轮 — ppv1-criteria-v2 appearance 首次消费闭合（正链 Codex，2026-10-14）

> 粘贴给 Codex 的完整提示词（自包含；建议发到终裁会话或上一轮
> 判据复审会话保持上下文连续，新会话亦可用）。
> 题域标签：298=RHEA 通用酶学/已见题；本文数字为工程验收口径
> （测试计数/探针），非判分成绩。

---

继续 ppv1-criteria-v2 判据级复审终裁（若新会话：先读 docs/POLLUTANT_PATHWAY_CRITERIA_V2_FINAL_DECISION_2026-10-14.md 补上下文）。你上一轮终判**不放行**，唯一余项 P1=状态出现记录在官方首次消费时被静默漏验（7e7855c 版 native_result.py:119 dict 过滤跳过非 dict 载荷 + 未复用 appearance 哈希校验；同库公共重放拒 appearance_hash_corrupt 而官方首次消费接纳，两路分裂）。

现在余项修复已提交：**commit `dda852b`**（v43 仓 /Volumes/CC/Enzyme_Agent/dependingv43）。请做第二轮终裁。

修复内容（交付书 docs/POLLUTANT_PATHWAY_CRITERIA_V2_P1FIX2_DELIVERY_2026-10-14.md）：
1. `native_result.py` 的 `_validate_native_state_rows` 扩为**完整出现集合逐行三查**：①对象形状（非 dict 结构化拒绝，不静默跳过）②appearance_hash 内容绑定 ③state_id 绑定（与行键/语义块一致）；kind=`native_result_appearance_corrupt`、reason 三分（payload_not_object / appearance_hash_mismatch / state_id_binding_mismatch），底层损坏 detail 原样保全；
2. **单一验证源**：`store.py:464` 新增 `_verify_appearance_content_hash`（内容⇄哈希判据），被首次消费（native_result.py:143,160）与写入收集/重放（`_verify_stored_appearances` 等三入口）**共用**——不另立判据、不静默丢行、不重算哈希洗损坏；
3. 原（语义,出现）逐对 from_dict 化学事实重算路径不动。

对照你的有限验收逐条：
- 你的两个反例（`[]` 载荷主反例、错绑 state_id 旁证）现在首次消费被结构化拒绝且**链在第一步截断**（persist/export/reader/evaluator 不执行）——证据 docs/review_evidence/criteria_v2_p1fix2_2026-10-14/postfix_participant_appearance_output.json（修复前基线同目录 prefix_repro_participant_appearance_output.json 确认原缺陷复现；探针演示前两分 reason，第三分 state_id_binding_mismatch 见 tests/test_ppv1_s4b_export.py 新测试；探针 actual_head 为隔离树父 7e7855c，HEAD 靠下条口径链条承接）；
- 合法多出现正控完整导出、公共 submit_event 重放幂等；
- 既有全部闭合保持：原 cn 腐蚀负控、零出现负控、合法边界、P2 批级=逐边和、缺省 v1 字节不变（同库 build/缺省 v1 evaluate+score/direct17/true-default 四对照哈希全等）；
- 全量 not-slow 零翻转。**口径链条（防撞账）**：P1fix2 自身验收=隔离树父树 2121+本修复 4 测试=**2125/0/16**；当前 HEAD（叠加并行 C 实施轮 873c323 的 +10 测试，与本轮文件面零重叠）主窗口复跑=**2135/0/16**（2026-10-14 实测）。受影响子集 211 passed。

请做的事：
1. 核对修复代码与验收标准（可自行复跑探针——p1fix2_participant_appearance_probe.py 在证据目录，python 用 ~/miniconda3/envs/depending43/bin/python）；
2. 顺手确认工作树里另一条并行实施线（C 线共底物供给，commit `873c323`）与本判据线零文件重叠、互不污染（git show --stat 两个 commit 可核；只看污染、C 的问题不阻塞本轮放行）；
3. 给**终判定三选一：放行（v2 生效）/有条件放行（列条件）/不放行（列 P1）**，报告落 docs/（命名建议 POLLUTANT_PATHWAY_CRITERIA_V2_FINAL_DECISION_R2_2026-10-14.md）。

纪律（不变）：只新增你的报告与证据目录；不改 src/tests/既有 docs/AGENTS.md；不访问金标/题面（questions.jsonl、reference_graphs/、逐题 metrics、gitignored reports 逐题数据）；封存 run 不进；不 git 提交不 push；不调用外部模型。证据带文件:行号或命令输出。
