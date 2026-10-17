# Codex 同范围复审请求二 — 补回入口余项闭合确认（2026-10-17）

> 授权链同前；fork 父=你上轮复审会话（01a14a8e）。审核对象 commit：`84cc9ff0a9cb5fcce5559d3ba9520e86bec40dcf`。
> 上轮报告：`docs/T_RANK_INHERITANCE_FIX_CODEX_REREVIEW_2026-10-17.md`（你的未排名池反例与最小修法）。

## 回修摘要（请读码核对）

- **幸存条目原索引随行**：折叠循环保 `deduped_indices`（幸存条目的去重前索引），未在去重后重新 enumerate（避开你警告的索引错位）。
- **补回按真实来源**：`for entry_idx, (key,...) in zip(deduped_indices, prepared_entries)`——仅 `entry_idx in novel_entry_idx`（真幸存 novel）读 `model_rank_by_id`；池条目（含与已折叠 novel 同名者）不再经 `key in novel_by_key` 误补。
- **测试**：你的最小反例已落测（两池均未排名+novel ID="A" 折入 B ⇒ 池 A model_rank=None/fallback/生效 2；B 继承 1/生效 1）+ 无撞名严格单变量对照（novel:A）+ 原矩阵①的池**有**位次变体（col1）已在。**9 测全绿；全量 not-slow 2202/0/16**。

## 请裁定（P1 余项闭合=是/否+证据；新问题分级；总裁定=放行或再回修）

1. 你的未排名池反例（novel ID=A 偷位次）与严格单变量配对（novel:A 对照）在回修后是否闭合——建议复跑你的探针。
2. 补回改 zip(原索引) 有无新漏口（如：池有条目但未排名的同名幸存 novel 场景、多折叠链、来源披露一致性）。
3. 收口矩阵（首轮①有/无位次两变体+各自无撞名正控+原测与正常边界）是否全过。

## 纪律（同前两轮）

只读+可在全新临时目录跑测试/探针；不动 src/tests/既有 docs；新增仅限 `docs/review_evidence/tf_fix_codex_rereview2_2026-10-17/` 与你的报告 `docs/T_RANK_INHERITANCE_FIX_CODEX_REREVIEW2_2026-10-17.md`；不访问金标/题面/封存逐题 run；不 push；不调用外部模型；结论须与程序证据互证。
