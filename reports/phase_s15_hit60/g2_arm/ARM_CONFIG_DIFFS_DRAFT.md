# ARM_CONFIG_DIFFS_DRAFT — T8 G2 臂预登记差异表(HIT60 T8,机读登记·草稿)

登记时间:2026-09-30(T8 G2 实施代理;先于任何付费调用;随
[PREREGISTRATION_G2.md](PREREGISTRATION_G2.md) 一并送 mimo 终版规则
复核与用户冻结,**冻结前本表为 DRAFT,不得据以发车**)。
性质:预注册差异表(S1 `ARM_CONFIG_DIFFS.md` 同款纪律)。跑分配对
判定时,两臂身份/配置的合法差异**只认本文件列出的字段**;出现本表
之外的差异 = 预注册被破坏,该批不得进判定(须新批次根重跑)。

- 基线(对照臂):`configs/s1_dev_C0.json`(= 当前行为:不发送
  temperature、rank 窗口 8、rank 呈现 v1、**novel 守恒过滤 off**)。
- 实验臂:`configs/s1_dev_G2.json`(**待发车授权后由部署代理落盘**;
  唯一实验差异 `prediction_policy_overrides.novel_conservation_filter="on"`)。
- 判定规则、配对结构、费用上限:见 PREREGISTRATION_G2.md §4/§4.4。

## 1. 逐字段差异表(相对基线 C0;全量扫描,未列字段 = 两配置完全相等)

| # | 字段路径 | C0(基线) | G2 | 类别 |
|---|---|---|---|---|
| 1 | `arm` | `s1_dev_C0` | `s1_dev_G2` | 基建标识(臂名,非行为) |
| 2 | `batch_root` | `s1_dev_C0` | `s1_dev_G2` | 基建(批次根基名;部署代理加时间戳后缀;一律新批次根) |
| 3 | `prediction_policy_overrides.novel_conservation_filter` | (未写 = 默认 `off`) | `"on"` | **实验变量:G2 唯一差异** |
| 4 | `config_notes` / `budget_rationale` | (C0 原文) | (G2 按上表差异改写,语义等价) | 说明字段(非行为) |

未列出的一切字段(budgets / model_request_params / llm_timeout_s /
max_http_retries / rate / batch_cost_cap_cny / provider_price_snapshot /
export_policy_overrides / capacity / worker_wall_clock_cap_s /
max_worker_respawns / poll_interval_s / max_parallel / exam_inputs /
其余 prediction_policy_overrides 键)两配置逐字节相等。

## 2. 差异的运行侧语义

| 开关 | 默认(C0) | G2 臂 | 进 run identity | 进 batch identity | 进模型请求体 |
|---|---|---|---|---|---|
| `novel_conservation_filter` | `off` = novel/analogy 提案不经守恒过滤与自排序(`_apply_novel`/`_apply_analogy` 与历史行为**逐字节一致**,回归测试钉住) | `"on"` = 提案落账前过 v43-cons-1 判据 + v43-norm-1 规范化 + v43-selfrank-1 自排序(纯后处理:剔除不入卡、降位垫底、剔空/底物不可判定 → held 诚实弃权;结构化拒因随 prediction.json 与提案卡落账) | 是(`prediction.policy.novel_conservation_filter`) | 是(经 `_policy_block_for_identity` 的 prediction_policy 块) | **否**(不改 prompt、不改请求参数、零生成端反馈——novel 提案仍是同模型同提示词产物,差异纯在落账后处理) |

值域 fail-closed:取值仅 `off`/`on`(装配期 `ValueError`,不静默回退)。
recorded / rank 路由不受该开关影响;REAP 式 prompt 先验不并入(另立臂)。

身份冻结链:`prediction_policy_overrides` → `prediction_policy()` 合并块
→ `ModelSetup.identity_block()["policy"]`(run identity)+ `build_batch_identity(
prediction_policy_block=...)`(批次身份短哈希)。跨配置 resume 在
`prediction` 块上被拒(IdentityMismatch),不静默继续。

## 3. 版本三元组(随开关进身份;判据变更 = 新身份新批次)

| 组件 | 版本 | 载体 |
|---|---|---|
| 守恒判据 | `v43-cons-1` | `validation/conservation.py::CONSERVATION_FILTER_VERSION`(落 prediction.json conservation_filter.versions) |
| 前置规范化 | `v43-norm-1` | 同上(versions.normalization) |
| 自排序键 | `v43-selfrank-1` | 同上(versions.self_rank) |
| G3-b 编目 | `v43-g3b-catalog-1` | 同上(versions.g3b_catalog;25 条 SMARTS) |
| 供体登记表 | `v43-donor-registry-1` | 同上(versions.donor_registry) |
| 完整性关键词 | `v43-cons-kw-1` | 同上(versions.completeness_keywords) |

## 4. 部署回填契约(JSON 无注释,占位说明登记于此)

| 字段 | 施工时值 | 发车前动作 | diff 纪律 |
|---|---|---|---|
| `batch_cost_cap_cny` | `null` | 部署代理按 PREREGISTRATION_G2 §4.4 回填(总帽 ≤¥6:判定主案方案 B ¥0 + 可选 in-run 烟测 ≤¥5) | 回填值若与 C0 不同,属费用治理字段,须在本表补登记 |
| `provider_price_snapshot` | `null` | 与 C0 同模型同值回填 | 两臂必须同值;不回填 = 无费用账,批不得进判定 |
| `batch_root` | 基名 | 时间戳后缀、新建目录 | 一律新批次根,禁跨身份 resume |

## 5. 判定形态登记(与 PREREGISTRATION_G2 §4.3 一致)

- 判定主案 = **方案 B(封存答卷离线确定性重放)**:对照 = dual_track_
  rescore 封存 C0-a/C0-b(v3 读数即 off 读数,双采样现成);主臂 = 同一
  封存答卷离线应用过滤器 + 自排序(本目录 `offline_replay.py` 即其驱动,
  判据同一函数)。生成成本 ¥0。
- 可选补强 = in-run 烟测(G2 开 on 一批新批次根,验证生产形态;
  ≤¥3/批)。方案 A(全量 in-run 双臂 4 批,帽 ≤¥12)不默认启用。
- **发车前置**:mimo 终版规则复核(`docs/mimo_g2_rules_final_review_request.md`)
  + 用户冻结确认 + 判据健全性预检过(金标候选落剔除档 = 0,已实测
  过,见 `replay_summary.json` gold_in_exclusion_tier 字段)。
