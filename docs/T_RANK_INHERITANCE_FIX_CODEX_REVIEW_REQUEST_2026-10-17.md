# Codex 代审请求 — T-F 折叠位次继承修复（s5b-rank-policy-2，2026-10-17）

> 授权链：CC 2026-10-17 指令「有需要人工审核的你就发送给 codex 审核」（沿 2026-10-16 审核类 Codex 代 CC 审授权，fork 链父=chain14 发车终审会话）。
> 题域标签：修复为运行时排序语义，不涉题域数字；引用的合成验证为纯构造输入（零金标零题面）。
> 审核对象 commit：`e3fe446c84842f9f3d9dea0b7d99f84d535ea1dc`（src/pathway_v43/pollutant/runflow.py + tests/test_tf_rank_inheritance.py + tests/test_ppv1_s5b_hit50_w23456.py 版本断言；同批带 T-F 证据链文档）。

## 一、背景（自包含）

T-F 专项合成验证（`docs/TF_SYNTHETIC_VALIDATION_2026-10-17.md`，证据 `docs/review_evidence/tf_synth_fixture_2026-10-17/`）**证实** v1 缺陷：模型把 novel 排第一位、novel 与更早出现的池条目同净反应签名且该池条目无模型声明位次 ⇒ novel 被折叠（runflow 去重后到者折叠），被折叠者声明位次在幸存键过滤时**静默丢弃**，幸存池条目落 deterministic_fallback 段后——模型第一选择的反应劣化到全部显式位次候选之后。chain13 真实批 298 题该组合 0 次触发（3 次折叠幸存者位次均优于被折叠者）⇒ 无已知损失，修复属低成本加固（老师任务书「排序免费收益」档）。

## 二、修法摘要（当前 HEAD 实况，请读码核对）

- 折叠循环内：被折叠者声明位次（rank_by_key 或 model_rank_by_id 两个来源）优于幸存者（或幸存者无位次）⇒ 记入 best_folded_rank；dedup_rejections 每条新增 folded_model_rank 与 rank_inherited 披露。
- 幸存键过滤 + novel 位次补回之后：幸存者取 min(自身位次, 被折叠者最优位次)；载荷新增 model_rank_inherited_from（null=未继承）。
- S5B_RANK_POLICY_VERSION 升 s5b-rank-policy-2（含注释）；全量 not-slow 2197/0/16（基线 2192+新增 4 夹具+1）。

## 三、请逐条裁定（回复格式：每问 通过/不通过+证据；P0/P1/P2 分级；末尾总裁定=放行或回修）

- **Q1 继承语义**：min 语义是否正确覆盖全部边界——幸存者无位次/被折叠者无位次/同一幸存者被多次折叠（取最优且逐条披露）/幸存者本身是 novel（位次来自 model_rank_by_id 补回，继承应用在其后）/被折叠者与幸存者都无位次（不继承不误标）？有无遗漏路径或顺序依赖错误？
- **Q2 披露完备**：dedup_rejections(folded_model_rank/rank_inherited)+载荷(model_rank_inherited_from) 是否足以无静默审计？被折叠者为 novel 时其位次来源（model_rank_by_id 自报）是否需要在披露中可辨？
- **Q3 版本与兼容**：policy-2 升版是否完备（旧批载荷恒 policy-1 零回写；新批全 policy-2；hit50 版本断言同步）？rank 语义变化对判分/hit@K 的传导是否确认为零（判分消费事件序与产物身份，不消费 effective_rank）？
- **Q4 测试覆盖**：tests/test_tf_rank_inheritance.py 四夹具是否覆盖风险形态与绕过面？缺哪些负控（如：两次折叠取最优、被折叠者无位次、幸存者为 novel）？
- **Q5 行为不变声明**：「真实批 3 次折叠幸存者位次均优于被折叠者⇒行为零变化」是否由代码路径与 chain13 数据支撑（可读 docs/review_evidence/tf_rank_transfer_2026-10-16/tf_probe_output.json 的 fold_detail 核对）？

## 四、纪律（无沙箱全权配套，违反=停止）

1. 只读评审为主，可跑测试/探针但须在全新临时目录（PYTHONDONTWRITEBYTECODE=1），不动 src/tests/既有 docs/AGENTS.md；
2. 新增仅限 `docs/review_evidence/tf_fix_codex_2026-10-17/`（你的证据目录）与 `docs/T_RANK_INHERITANCE_FIX_CODEX_REVIEW_2026-10-17.md`（你的报告）；
3. 不访问金标/题面/封存逐题 run；不 push；不调用外部模型；不 git 写操作。
4. 采信原则：结论须与程序证据互证（读码+可复跑探针），不得凭推断下裁定。
