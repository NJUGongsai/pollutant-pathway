# BBD v2 降解产物预测 — 双引擎候选生成 + 组合分排序

**日期**: 2026-08-29
**实现**: GLM-5.2
**任务书**: `CC/TASK_BBD_V2_DUAL_ENGINE_2026-08-29.md`

---

## 0. 一页摘要

v2 双引擎管线（USPTO 图编辑 + enviPath RunReactants）已在 93 个盲测底物上全量跑通，0 crash。与 v1 相比，Hit@10 从 22.1% 提升到 **57.0%**（+34.9pp），Hit@1 从 10.5% 提升到 **22.1%**（+11.6pp）。

**验收门槛结果**:

| 门槛 | 目标 | 实际 | 状态 |
|------|------|------|------|
| Hit@10（83-case, stereo-blind） | ≥ 45% | **57.0%** | ✅ 通过 |
| Hit@1（同口径） | ≥ 25% | **22.1%** | ❌ 差 2.9pp |
| 池召回 union | ≈ 80.7% | **67.4%** | ❌ 见 §3 诊断 |

Hit@10 大幅超标（57% vs 45%门槛）。Hit@1 差 2.9pp 未达标，消融显示 enviPath-only 引擎单独可达 29.1% Hit@1——差距来自 USPTO 候选稀释 top-1，是排序问题（P3 学习型排序的启动信号）。池召回差异的根因是任务书诊断中"enviPath 单独"的数字实际来自 hfix 池（286 规则 ∪ 旧 RA-M1 检索池），而 v2 按任务书设计不接入旧池。详见 §3。

---

## 1. 指标表

### 1.1 v1 vs v2（83-case，stereo-blind 口径，parent 过滤后）

| 指标 | v1（基线） | v2 | Δ |
|------|-----------|-----|---|
| Hit@1 | 10.5% (9/86) | **22.1%** (19/86) | +11.6pp |
| Hit@3 | 19.8% (17/86) | **39.5%** (34/86) | +19.7pp |
| Hit@5 | 20.9% (18/86) | **44.2%** (38/86) | +23.3pp |
| Hit@10 | 22.1% (19/86) | **57.0%** (49/86) | +34.9pp |
| Hit@20 | 22.1% (19/86) | **64.0%** (55/86) | +41.9pp |
| MRR@10 | 0.1444 | **0.3194** | +0.175 |
| Recall@10 | 0.1453 | **0.4267** | +0.281 |

> v1 基线使用 `bbd_product_predictions.jsonl`（top-10），`--parent-filter` 移除 parent 副本后同口径评测。v2 预测已内置 parent 过滤。
>
> 口径说明：stereo-blind（两侧 `isomericSmiles=False`）。v2 的 stereo-blind 评测匹配 86 个 case（83 个 answer-key parent + 3 个 collision，即不同 blind case 映射到同一 canonical parent）。strict 口径下匹配 83 个 case，Hit@10=56.6%、Hit@1=22.9%，趋势一致。

### 1.2 v2 strict 口径（参考）

| 指标 | 值 |
|------|-----|
| Hit@1 | 22.9% (19/83) |
| Hit@10 | 56.6% (47/83) |
| Hit@20 | 62.7% (52/83) |
| MRR@10 | 0.3224 |

---

## 2. 池召回分 source 表

| 引擎 | 召回 case | 召回率 | 预期参照值 |
|------|----------|--------|-----------|
| USPTO（图编辑） | 28/86 | 32.6% | ≈30.1% ✅ 对齐 |
| enviPath（RunReactants, 286 规则） | 48/86 | 55.8% | — 见 §3 |
| Union | 58/86 | 67.4% | — 见 §3 |
| 平均候选数/case | USPTO 57.9 | enviPath 7.1 | Union 64.3 |

---

## 3. 池召回差异诊断（关键发现）

### 3.1 根因：任务书诊断中的"enviPath 单独"包含了旧 RA-M1 检索池

任务书 §1.2 诊断 #2 给出"enviPath 单独: 63/83 = 75.9%（stereo-blind）"和"与 USPTO 并集: 67/83 = 80.7%"。经实测分解，该数字实际来自 `data/hfix/candidates_hfix.json`，而该文件 = 286 条 enviPath 规则的 RunReactants 产物 ∪ 旧 RA-M1 检索池（`reaction_analogy/data/retrieval_v1/queries.jsonl`）。

分解实验（83-case，stereo-blind）:

| 池来源 | 召回 | 召回率 |
|--------|------|--------|
| enviPath 286 规则单独 | 47/83 | 56.6% |
| 旧 RA-M1 检索池单独 | 42/83 | 50.6% |
| hfix（enviPath ∪ 旧池） | 63/83 | 75.9% ← 任务书引用的"enviPath 单独" |
| hfix ∪ USPTO | — | ≈80.7% ← 任务书引用的"与 USPTO 并集" |

v2 按任务书 §4.1 设计为双引擎（USPTO + enviPath 286 规则），§3 明确 candidates_hfix.json "一致性校验用，不进预测"。因此 v2 不接入旧池，union 召回为 67.4%（=56.6% enviPath-only ∪ 32.6% USPTO-only），低于 80.7% 目标 13.3pp。

### 3.2 DCE 案例（FR-BBD3-PARENT-c0001）

任务书 Phase 2.1 预期"DCE，真产物 OCCCl 应在池中"。实测：`OCCCl` 来自旧 RA-M1 池，而非 286 条 enviPath 规则（后者对 DCE 只产出 `OC(Cl)CCl`）也不是 USPTO 图编辑可产（图编辑不能新增 O 原子）。因此 v2 池不含 `OCCCl`，DCE 是 26 个双池 miss case 之一。

---

## 4. 消融实验

| 消融 | Hit@1 | Hit@3 | Hit@5 | Hit@10 | Hit@20 |
|------|-------|-------|-------|--------|--------|
| **Full v2** | **22.1%** | 39.5% | 44.2% | **57.0%** | 64.0% |
| mpnn-off | 20.9% | 43.0% | 50.0% | 57.0% | 60.5% |
| src-off | 8.1% | 16.3% | 24.4% | 36.0% | 45.3% |
| **envipath-only** | **29.1%** | 44.2% | 48.8% | 52.3% | 55.8% |
| uspto-only | 8.1% | 15.1% | 19.8% | 29.1% | 30.2% |

**关键发现**:

1. **envipath-only 的 Hit@1（29.1%）高于 Full v2（22.1%）**。说明 USPTO 候选虽然扩大了 Hit@10 的覆盖（57% vs 52.3%），但高频模板的 USPTO 候选抢占 top-1，将正确 enviPath 候选挤出。这是 Hit@1 未达 25% 门槛的直接原因。→ **P3 学习型排序的启动信号**。

2. **src-off 退化最严重**（Hit@10: 57% → 36%），source 先验（enviPath 0.40 vs USPTO 0.10）是排序公式中最重要的组件。

3. **mpnn-off 几乎不影响 Hit@10**（57% → 57%），MPNN 原子概率在 BBD 底物上饱和（中位最高概率 0.96），区分度低。对 Hit@1 有轻微影响（22.1% → 20.9%）。

4. **uspto-only ≈ v1 基线**（Hit@10: 29.1% vs v1 22.1%），改进来自 parent 过滤 + 组合分（vs v1 的 max(site_probs)）。

---

## 5. 权重声明

排序公式定义于 `reaction_analogy/bbd_v2_scoring.py`（单一事实源，预测器与消融重打分共用），权重为**先验声明，非拟合值**，实现期间**未对着答案 key 调整**:

```
env_score = 0.40 + 0.30*mpnn_agg + 0.15*rc   + 0.15*spec     (enviPath 分支)
usp_score = 0.10 + 0.35*mpnn_agg + 0.35*freq + 0.15*spec    (USPTO 分支)
source="both" → max(env_score, usp_score)
mpnn_agg = 0.5*mpnn_site_mean + 0.5*mpnn_site_max
spec  = min(1.0, log1p(pattern_atom_count) / log1p(25))
rc    = min(1.0, log1p(reactions_count) / log1p(10))
freq  = min(1.0, log1p(template_freq) / log1p(50))
tie-break: (-score, product_smiles) 字典序
```

**权重依据**（详见 `bbd_v2_scoring.py` docstring）:
- enviPath 先验 0.40 vs USPTO 0.10：enviPath 是 EAWAG-BBD 人工策划的降解规则（域匹配），USPTO 是通用有机合成库。
- USPTO 侧 mpnn 权重更高（0.35 vs 0.30）：USPTO 候选无其他 site 化学信号。
- `spec`（规则/模板的 pattern 原子数）：上下文越多越特异、误触发越少。enviPath REACTIONS_COUNT 信号弱（203/286 条只有 1 条反应支撑），需 `spec` 补充。

---

## 6. skip 统计

| 计数项 | 值 |
|--------|-----|
| 案例数 | 93 |
| 0 候选案例 | 1（`FR-BBD3-PARENT-c0939`，次磷酸盐 `OP=O`，两池均无真产物，预期空） |
| budget 截断（Engine A, 60s） | 0 case |
| parent 过滤（Engine A） | 901 |
| skip_unsanitizable（Engine B） | 1333 |
| skip_wildcard（Engine B） | 0（野生卡候选全部未通过 sanitize，计入 unsanitizable） |
| skip_multi_fragment_rule（全局） | 0（286 规则均为单片段反应物） |
| mpnn_index_mismatch | 0 |
| pool_truncated（>2000 候选） | 0 case |
| 总候选（合并去重后） | 5844（5231 uspto + 672 envipath） |
| 总耗时 | 52.1s（8 proc） |

---

## 7. hfix 一致性校验

| 指标 | 值 |
|------|-----|
| 共享 parent 比较数 | 86 |
| hfix 有而 v2 没有的 case 数 | 86（全部） |
| v2 有而 hfix 没有的 case 数 | 0 |
| hfix\v2 总片段数 | 7713 |
| v2\hfix 总片段数 | 0 |

**差异根因**: `candidates_hfix.json` = 286 enviPath 规则 RunReactants 产物 ∪ 旧 RA-M1 检索池。v2 enviPath 引擎仅含 286 规则产物（不含旧池），且额外过滤了 `*` 通配符候选（hfix 池中有大量 `*` 条目）。v2\ hfix = 0 证明 v2 的 enviPath 引擎没有产出任何 hfix 池之外的候选，即 v2 enviPath ⊆ hfix enviPath，一致性校验通过。

> 阈值判定：任务书预期差异只来自 `*` 过滤与清洗规则，但实际 hfix 池包含大量旧 RA-M1 检索池候选（大分子、聚合物等），导致全部 86 case 都有 hfix-only 条目。这并非 v2 引擎 bug，而是 hfix 池定义不同（含旧池 ∪）。

---

## 8. 已知局限

### 8.1 双池 miss case（26 个，而非任务书预期的 16 个）

以下 26 个 answer-key case 的真产物不在 USPTO ∪ enviPath（286 规则）任一池中。任务书预期的 16 个是基于 hfix（含旧池）+ USPTO 的 80.7% 召回（83-67=16）；v2 不含旧池，union 召回 67.4%（83-56≈27），miss case 增至 26。

| # | Answer-key case ID | Parent | 真产物 |
|---|-------------------|--------|--------|
| 1 | SPD-BBD2-PARENT-c0001 | ClCCCl | OCCCl |
| 2 | SPD-BBD2-PARENT-c0039 | 二苯并呋喃 | 羟基二苯并呋喃 |
| 3 | SPD-BBD2-PARENT-c0121 | 苯甲酸 | 环己二烯甲酸 |
| 4 | SPD-BBD2-PARENT-c0153 | 苯乙醇酸 | (同 parent) |
| 5 | SPD-BBD2-PARENT-c0177 | 4-氯联苯 | 羟基化产物 |
| 6 | SPD-BBD2-PARENT-c0245 | 邻氨基苯磺酸 | 羟基化产物 |
| 7 | SPD-BBD2-PARENT-c0286 | 3-氯丙烯酸 | 丙酸 |
| 8 | SPD-BBD2-PARENT-c0352 | 1-氨基环丙烷甲酸 | 丁酸 |
| 9 | SPD-BBD2-PARENT-c0371 | 联苯 | 羟基联苯 |
| 10 | SPD-BBD2-PARENT-c0426 | 二苯并呋喃(异构) | 羟基化产物 |
| 11 | SPD-BBD2-PARENT-c0432 | 己内酰胺 | 氨基己酸 |
| 12 | SPD-BBD2-PARENT-c0444 | 咔唑 | 羟基咔唑 |
| 13 | SPD-BBD2-PARENT-c0612 | 1,2-二氯乙烯 | 羟基乙烯 |
| 14 | SPD-BBD2-PARENT-c0694 | 4-羟基苯乙酮 | 酯化产物 |
| 15 | SPD-BBD2-PARENT-c0865 | 2,4-二氯甲苯 | 羟基化产物 |
| 16 | SPD-BBD2-PARENT-c0908 | N-甲基己内酰胺 | N-甲酰己内酰胺 |
| 17 | SPD-BBD2-PARENT-c0939 | 次磷酸盐 | 次磷酸 |
| 18 | SPD-BBD2-PARENT-c0946 | 十二烷基苯磺酸 | 羟基化产物 |
| 19 | SPD-BBD2-PARENT-c0991 | 芘 | 芘酮/羟基芘 |
| 20 | SPD-BBD2-PARENT-c1039 | 4-氟苯甲酸 | 环己二烯甲酸(氟) |
| 21 | SPD-BBD2-PARENT-c1072 | 2-氟苯甲酸 | 环己二烯甲酸(氟) |
| 22 | SPD-BBD2-PARENT-c1201 | 4-羟基吡啶 | 羟基吡啶-N-氧化物 |
| 23 | SPD-BBD2-PARENT-c1354 | 1,4-二氧六环 | 二氧六环酮 |
| 24 | SPD-BBD2-PARENT-c1391 | 肉桂酸(苯基) | 环己二烯甲酸(苯基) |
| 25 | SPD-BBD2-PARENT-c1441 | 氯乙酰氨基甲氧基二甲苯 | 脱氯产物 |
| 26 | SPD-BBD2-PARENT-c1481 | 硫代磷酸二甲酯 | 硫代磷酸酯 |

这些 miss case 中，多数是**羟基化反应**（加 O 到芳香环），USPTO 图编辑引擎无法新增原子，enviPath 286 规则中没有对应规则。这正是 P5（手写补规则）的候选场景。

### 8.2 stereo 口径

v2 主口径为 stereo-blind（`isomericSmiles=False`）。Engine A（图编辑）不产立体，strict 口径下 Hit@10 从 57.0% 降至 56.6%，差异在 ±1pp 内。Engine B（RunReactants）可能产出立体异构体，但在 stereo-blind 口径下与真产物匹配。

### 8.3 site 分数近似

Engine B 的 MPNN site 分数取 `GetSubstructMatches` 枚举的聚合最大值，与 `RunReactants` 内部 match 不一一对应（任务书 §4.2 声明的近似）。不追求数学精确，仅作排序特征。

### 8.4 确定性

双跑（8 proc, fork Pool）byte-diff 通过：预测文件与池文件均 **byte-identical**（`diff` 零差异）。案例按 `case_id` 排序后写文件，候选按 `(-score, product_smiles)` 排序，不依赖 dict 插入序。

---

## 9. 交付物

| 文件 | 状态 |
|------|------|
| `reaction_analogy/predict_bbd_products_v2.py` | ✅ 新建 |
| `reaction_analogy/bbd_v2_scoring.py` | ✅ 新建 |
| `reaction_analogy/score_bbd_hitk_v2.py` | ✅ 新建 |
| `reaction_analogy/reports/BBD_V2_REPORT_2026-08-29.md` | ✅ 本文件 |
| `bbd_predictions/bbd_product_predictions_v2.jsonl` | ✅ 93 行 |
| `bbd_predictions/bbd_product_pool_v2.jsonl` | ✅ 全量池 |
| `bbd_predictions/bbd_v2_run_report.json` | ✅ 运行统计 |
| 分支 `feat/bbd-v2-dual-engine` | ✅ 本地，不 push |

---

## 10. 结论与下一步

**Hit@10 大幅超标**（57% vs 45% 门槛），证明双引擎候选生成 + 组合分排序的核心设计有效。v1→v2 的 +34.9pp Hit@10 提升主要来自 enviPath RunReactants 引擎接入（扩大候选池覆盖）和 parent 过滤（消除 parent 副本挤占）。

**Hit@1 未达标**（22.1% vs 25%），消融定位为排序问题：envipath-only 单引擎 Hit@1=29.1% 已过门槛，USPTO 候选稀释 top-1 是根因。按任务书 §7 停机条款，不调权重、不改公式，交 GLM-5.3 审核。这是 **P3 学习型排序**的启动信号。

**池召回低于预期**（67.4% vs 80.7%），根因是任务书诊断中"enviPath 单独"的数字实际来自 hfix 池（含旧 RA-M1 检索池），而 v2 按设计不接入旧池。若后续需对齐 80.7%，可将旧 RA-M1 检索池作为第三引擎接入（但此为设计变更，需任务书确认）。
