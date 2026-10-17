# Codex 同范围复审请求 — T-F 位次继承回修确认（P1 闭合，2026-10-17）

> 授权链：同首轮（CC「审核类发 Codex」）；fork 父=你上一轮审核会话（01a14a7a）。
> 审核对象 commit：`0facf85333eed4fef3436e18f80dc295d6532caa`（src/pathway_v43/pollutant/runflow.py + tests/test_tf_rank_inheritance.py）。
> 首轮报告：`docs/T_RANK_INHERITANCE_FIX_CODEX_REVIEW_2026-10-17.md`（你的 P1 反例与固定矩阵）。

## 一、回修摘要（请读码核对）

- **来源追踪**：novel 追加处记录 `novel_entry_idx`（条目索引集合）；池/novel 同名不再靠字串辨源。
- **来源分流查表**：`_declared_rank(entry_idx, key)`——novel 条目读 `model_rank_by_id`（模型原始 ID 表），池条目读 `rank_by_key`（池逻辑键表）；`dedup_by_signature` 存 `(key, idx)` 取幸存者来源。
- **披露**：`dedup_rejections` 每条新增 `folded_entry_source`（novel/pool）；`model_rank_inherited_from` 升为「来源:ID」格式（如 `novel:A`）。
- **测试**：你的固定矩阵①（novel ID 撞**他**池 key，位次 1 正确进幸存者、首选反应第一执行）与②（撞**幸存**池 key，两来源位次正确比较）已落 `tests/test_tf_rank_inheritance.py`；另有同名 novel **幸存**自检（登记 v1 身份行为现状：池位次占字串槽、双条目同位次——不扩修）。7 测全绿；全量 not-slow **2200/0/16**。
- **P2 措辞纠正已采纳**：本轮提交表述为「判分算法与产物身份判据零改动；新运行提交顺序可能改变（即修复目的），科学收益未认证」。

## 二、请裁定（回复格式：P1 闭合=是/否+证据；新问题 P0/P1/P2 分级；总裁定=放行或再回修）

1. 首轮两个合成反例（novel-id-collides-pool-key / novel-id-collides-survivor-key）在回修后是否闭合——建议你复跑自己的探针核对（纪律同首轮：全新临时目录）。
2. 来源分流实现有无新漏口（如：池条目读 model_rank_by_id 的可达路径是否已消除；best_folded_rank 四元组在多次折叠/链式折叠下是否仍取最优并逐条如实披露）。
3. 固定矩阵四项（①②③无重名正控④原测+正常边界）是否全过。

## 三、纪律（同首轮，违反=停止）

只读评审+可在全新临时目录跑测试/探针（PYTHONDONTWRITEBYTECODE=1）；不动 src/tests/既有 docs/AGENTS.md；新增仅限 `docs/review_evidence/tf_fix_codex_rereview_2026-10-17/` 与你的复审报告 `docs/T_RANK_INHERITANCE_FIX_CODEX_REREVIEW_2026-10-17.md`；不访问金标/题面/封存逐题 run；不 push；不调用外部模型；结论须与程序证据互证。
