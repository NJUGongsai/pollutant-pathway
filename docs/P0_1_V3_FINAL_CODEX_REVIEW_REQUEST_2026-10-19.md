# Codex 复审请求 — P0-1 误拒率判读 v3 终局与定稿表（2026-10-19）

> 授权链：CC goal 指令（审核类走 Codex 正常通道；代审即终审模式本轮已多轮先例）；fork 父=判读审会话 `01a14ba1-d84b-7343-b7c8-72d0c782dc16`。
> 审核对象：v3.2 判读全链产物——`reports/ppv1_s5b/p0_1_initiation_input_2026-10-17/` 下 `judgement_glmsub_v3_A_batch{1..5}.json`（155 件）、`judgement_second_read3_codex.json`（二读 30 件）、`judgement_glmsub_v3_capability15.json`（负锚 15 件）、`judgement_gate_dispute_codex.json`（门处置 2 件）、`judgement_pass_confirm_codex.json`（pass 确认 56 件）+ 定稿表 `docs/P0_1_ERR_RATE_RESULT_2026-10-18.md`（v3 定稿头部）+ 全注记底稿 `docs/P0_1_ERR_RATE_RESULT_V3_DRAFT_2026-10-18.md`。
> 上游：设计稿 `docs/P0_1_PROBE_INITIATION_INPUT_2026-10-16.md`；判读规则 v3.2=`docs/P0_1_A_RULES_V3_DRAFT_2026-10-18.md`（终审校准版）；judger=ZCode 子代理（GLM，judged_by 如实标注）；二读/终审/确认=codex 正常通道（代审即终审）。

## 请逐条裁定（每问 通过/不通过+证据；P0/P1/P2 分级；总裁定=定稿可交 T-G 消费/回修）

- **Q1 链条完整性**：5 批并集=155、批间零重叠、case_id 对上 sampled_A row_id；两处回正（a-bde2/a-759c，judgement_basis 带「终审回正」标记）与确认层否决 14 件在批文件/确认文件的登记是否自洽可核（可脚本复核；注意批 4 曾有 qid 截短已按材料包回填修复——请复核修复完整性）。
- **Q2 定稿表核算**：A 三层口径算术（judger 56/130=43.1% [34.9,51.7]；确认口径 42/120=35.0% [27.1,43.9]——分子=42 维持件、分母=42+（74+4 确认拒））、B 双层（2/97 与 6/97）、Wilson 算术；T-G 消费读法（A 过线立项/B 未过线降维护、各自判）是否符合任务书 §三.7；uncertain（25+10）单列不进率是否贯彻。
- **Q3 判读质量抽核**：抽 10-15 件（含 4 件确认层改拒件与数件维持件）——judgement_basis 是否引用材料包实际字段、pass 件锚与模板实际断/成键是否逐一一致、确认层否决理由是否化学上站得住。
- **Q4 过程诚实边界**：二读门双层口径（原始 86.7% 如实记+终审回正后 100% 复合——代审注记「仲裁不自动抬门」是否如实保留）；判读者通道变迁（mimo→GLM 子代理，opencode 退役）披露；负锚门 13.3% 与前提注记（编译通过≠闭合净反应）；64/800 旧值注记；手动通道数据收档不入正式读数——有无越界或美化了失败记录。
- **Q5 采信边界**：零金标零题面、机械量只当抽样框、298 标签、单批不外推、预注册纪律（冻结走 CC 拍板开关）——有没有越界表述。

## 纪律（同前，违反=停止）

只读评审+可在全新临时目录跑只读核算脚本（PYTHONDONTWRITEBYTECODE=1）；不动 src/tests/既有 docs；新增仅限 `docs/review_evidence/p0_1_v3_final_codex_2026-10-19/` 与你的报告 `docs/P0_1_V3_FINAL_CODEX_REVIEW_2026-10-19.md`；不访问金标/题面/封存逐题 run；不 push；不调用外部模型；结论须与程序证据互证。
