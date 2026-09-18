# depending v3.3 soil/sludge 反馈 — 诊断报告 + v3.4 修复（2026-09-18）

对象：《FEEDBACK_TO_GONG_DEPENDING_V33_SOIL_SLUDGE_LOW_TOP1_AND_REQUIRED_REPAIR_2026-09-17》
执行：弓师兄侧（本地诊断 + 修复实现 + 本地验证）；soil/sludge gold 未读取（本地不存在）
产物目录：`reaction_analogy/reports/SS_DIAG_2026-09-18/`（本文件 + 全部 JSON 证据）

---

## 0. 执行摘要

对方反馈的三个问题（USPTO-only 排序过强 / Top-10 增量不足 / 环境域库外泛化弱）全部在
本地独立数据上得到**量化证实**，并定位出**三层根因**。同时完成了一轮融合层修复
（v3.4，per-source 校准融合 + 双形式发射 + 可选 Top-K 配额）并在本地验证。

**最重要的单条发现（制度对比，D1/D6）**：

| 评估制度 | 检索语料是否覆盖该反应族 | Top-1 | Top-10 |
|---|---|---:|---:|
| RHEA val（1,234 educts，语料含真值反应） | 覆盖 | **95.1%** | 97.8% |
| EAWAG 环境域（775 donors，语料不含其反应） | 不覆盖 | **21.7%** | 52.8% |
| 对方 soil/sludge（1,788 parents，2.8% lookup 可见） | 不覆盖 | **11.7%** | 27.8% |

**系统的 Top-1 能力完全取决于检索语料/环境规则对目标反应族的覆盖，而不是排序本身。**
排序层修复（v3.4 校准+制度门控）在环境域把 Top-1 从 22.2%→23.3%（+1.0pp）
——真实但量级有限；达到 ≥50% 的验收目标**必须扩充环境域语料与规则资产**（对方建议
方向 1），这一点有本地数字支撑（见 §5）。

---

## 1. 诊断执行环境与数据纪律（对方 §六要求）

| 数据集 | 规模 | 角色 | 与 v3.1 ranker 的关系 |
|---|---|---|---|
| EAWAG donor 缓存（`data/bbd_v5/eawag_candidates.jsonl`） | 775 educts / 122,398 候选 / 627+ 正例 | 环境域代理（soil/sludge 制度的最接近本地形态：语料不含其反应） | **从未参与 v3.1 训练**（仅 v5 训练用，且 v5 ranker 不在本地/本次链路） |
| RHEA val split（`data/bbd_v31/val_split.json`） | 1,234 educts | 语料覆盖制度 + 大规模 | 曾用于 v3.1 模型选择（如实披露） |
| BBD83（93 案 + 答案键） | 86 可评 | 公开诊断集（对方已声明）+ 部署口径 pool | 预测层从未见过 |

- soil/sludge 冻结集**不在本地**，本诊断零读取；所有参数（校准器、Top-K 策略）仅在
  EAWAG 缓存 calib/val split（seed=0, 50/50）上拟合/选择。
- 诊断/拟合脚本：`diag_ss_feedback_20260918.py`（A/B）、`diag_ss_stagesCEF_20260918.py`
  （C/E/F）、`fit_v34_calibration.py`（校准+网格+BBD83 回归）。

---

## 2. 七项诊断（编号对齐对方 §四）

### 2.1 候选生成上限（oracle recall，分来源）

EAWAG 环境域（775 educts，预测层，双口径）：

| family | 生成行数 | 正确数（strict∪cn） | 生成精度 |
|---|---:|---:|---:|
| envipath+retrieval | 494 | 143 | **28.9%** |
| envipath+uspto | 1,812 | 67 | 3.7% |
| envipath-only | 18,464 | 322 | 1.7% |
| uspto-only | 5,160 | 59 | **1.1%** |
| retrieval-only | 96,292 | 174 | 0.18% |

- 总 oracle：**557/775 = 71.9%**（cn）/ 530/775 = 68.4%（strict）→ **~28% 的环境域
  educt 是纯生成缺口**（任何来源都没生成正确产物）。
- 分来源 educt 覆盖：enviPath 430（55.5%）> retrieval 277（35.7%）> uspto 83（10.7%）。
- 电荷口径差：uspto-only 正例 strict=14 vs strict∪cn=59（**76% 的 USPTO 正确候选因
  质子化形式失配被缓存严格标签漏标**，见 2.7）。
- 对照组：RHEA val oracle = 1,228/1,234 = 99.5%（retrieval 覆盖 99.5%）；BBD83
  pred-only oracle = 74/86 = 86%。
- **结论**：在"语料不覆盖"制度下，生成上限 ~72%，Top-1 的理论天花板与之绑定；
  soil/sludge 制度更严（其正确反应多在 enviPath/EAWAG-BBD 之外）。

### 2.2 来源分层漏斗（generated → Top-50/10/1 + 命中）

EAWAG 域 v3.3 预测层（缓存口径，Top-10 组成 vs rank-1 命中）：

| family | Top-10 行数占比 | rank-1 行数 | rank-1 命中率 |
|---|---:|---:|---:|
| envipath+retrieval | 5.5% | 144 | **104/144 = 72.2%** |
| envipath-only | 41.3% | 116 | 26/116 = 22.4% |
| envipath+uspto | 15.5% | 284 | 22/284 = 7.7% |
| retrieval-only | 27.0% | 145 | 10/145 = 6.9% |
| uspto-only | 9.2% | 44 | 3/44 = 6.8% |

- 与对方 soil/sludge 观察同构：enviPath 系 rank-1 命中（22-72%）≫ uspto-only
  （6.8%；对方 1.35%）。多源环境证据（envipath+retrieval）是最强信号。
- **缓存口径 vs 部署口径的关键错配**：缓存 engine A 用 USPTO **top-2,000 模板**
  （训练口径），部署链（single_smiles/predict）用**全部 188,725 模板**（60s 预算）。
  因此本地代理 Top-10 的 uspto-only 仅 9.2%，而对方实测 71.0% —— 部署时 USPTO 候选
  洪泛远超训练时 ranker 见过的分布（详见 2.3）。
- RHEA val（语料覆盖制度）：rank-1 uspto-only = **0 行**（retrieval 996/1,234，
  99.5% 命中）；BBD83 部署口径 Top-10：uspto-only 32.6%、enviPath 系 18.8%、
  lookup 15.2%、retrieval 32.2%。

### 2.3 融合截断审计（k1/k2、配额、去重、融合规则）

静态清单（全部核过）：
- `TOP_K=20`（predict 链）/ `--top-k`（single 链，对方用 10/50）；`POOL_CAP=2000`；
- `k1=5/k2=5` 只作用于 **depth≥2** 的 BFS frontier —— depth-1 评分不受影响，
  对方 Top-10 口径无 k1/k2 截断；
- lookup 命中时预测层同身份候选**整行删除**（`predict_bbd_hybrid` 的
  `pred_dedup`，不是合并）；
- v3.3 电荷归一合并（`merge_charge_variants`）；
- 无任何 source 配额 —— 融合纯按 `max(p_source)/3` 等权。

定量（参数无关反事实，EAWAG 域）：
- 删除全部 USPTO-only 候选：hit@1 21.7%→21.6%（持平）、hit@10 52.8%→**54.3%（+1.5pp）**
  —— 缓存口径下 USPTO 拥挤不是主要损失；
- 但**部署口径**（188k 模板 + 语料不覆盖的 parent）USPTO-only 占 Top-10 71% 且
  rank-1 命中仅 1.35%（对方实测）→ 拥挤损失集中在部署制度。本地 BBD83（部署口径
  pool）uspto-only 32.6%、rank-1 命中 0 —— 介于两者之间，与"越库外、USPTO 洪泛
  越重"的单调关系一致。
- **训练/部署候选分布错配**（新发现）：训练缓存 top-2k 模板 vs 部署 188,725 模板，
  ranker 从未见过部署的 USPTO 候选分布。

### 2.4 ranker 分数审计（分布 + 校准，USPTO 是否虚高）

EAWAG 环境域（v3.1 ranker 打分，全缓存）：

| source | 正例 p50 | 负例 p50 | 负例 p90 | within-source AUC |
|---|---:|---:|---:|---:|
| uspto | 0.245 | 0.022 | 0.453 | 0.743 |
| envipath | 0.359 | 0.034 | 0.591 | 0.759 |
| retrieval | 0.993 | 0.009 | 0.022 | 0.889 |

（RHEA val 域内对照：0.867 / 0.887 / 0.996 —— ranker 在环境域仍有域内判别力，
**问题不是"反信息"，是跨源分数不可比 + 训练域先验错配**。）

- **USPTO 虚高机制确认**：v3.1 USPTO ranker 首要特征 `log1p_template_freq`
  （v31_train_stats.json），高频合成模板天然高分；环境域 uspto-only 负例 p90=0.45、
  p99=0.95 —— 大量高分垃圾。融合 `max(p)/3` 把它们推到顶部（对方 71% Top-10 占比）。
- **来源基率差**（校准的依据）：环境域 uspto 正率 1.2%、envipath 2.6%、retrieval
  0.33%（但 retrieval 正例的 donor_exact_match 通道饱和于 0.993）。三个源分数的
  "0.5"含义完全不同 —— 等权 max 融合必然偏袒高分基率低的源。

### 2.5 多产物 / Top-10 diversity 审计

- Top-10 中 rank-1 同 Murcko 骨架占比：EAWAG 域 0.550、BBD83 0.549（Top-10 一半
  与 rank-1 同骨架）——"多样性不足"的名义证据存在；
- **但策略网格证伪了朴素 diversity 修复**（EAWAG val，v3.4 排序之上）：

| 策略 | hit@1 | hit@10 |
|---|---:|---:|
| 无策略（raw） | 0.233 | **0.514** |
| 骨架上限=3 | 0.233 | 0.496 |
| 骨架上限=2 | 0.233 | 0.496 |
| enviPath 配额=2/3（骨架关） | 0.233 | 0.514 |

  **Murcko 骨架降级伤害环境域召回** —— 环境降解的正确产物常与母体同骨架
  （同骨架不同位点氧化/水解系列）。对方观察到的多产物 H@10 差距更可能来自**生成
  覆盖缺口**（2.1）而非同骨架挤占。已采纳：骨架降级默认关闭；enviPath 配额=2
  保留（无害 + 针对部署制度）。
- 多产物 educt：EAWAG 域 85 个（平均 1.18 个真产物进 Top-10）、BBD83 34 个（2.41）。

### 2.6 环境域覆盖缺口

资产现状 vs 需求：

| 资产 | 规模 | 状态 |
|---|---|---|
| enviPath 规则（部署 engine B） | **286 条** | 部署中，密度低 |
| EAWAG 规则（`rules_new_clean.jsonl`） | 49 条 | **仅 v5 训练用，v3.3 部署链未接入** |
| EAWAG-BBD lookup 库 | 859 donors / 1,006 对 | 部署中（对方 soil/sludge 可见率 2.8%） |
| 检索语料 corpus_v1 | RHEA 37,100 + enviPath 580 donors | 环境域占比极低 |

- BBD83 按污染物类别的证据可得性（stageE_coverage.json）：82/83 parent lookup 可见
  （该集与 EAWAG-BBD 同源，覆盖高不意外）；enviPath 规则 0 触发的 parent 仅
  3/83（halogenated 2、other 1）；retrieval tanimoto 中位数普遍 1.0（语料内）。
  BBD83 无法代表 soil/sludge 的覆盖缺口 —— **这正是对方集合的价值**。
- 制度对比（§0 表）即覆盖缺口的直接度量：语料覆盖 → 95% Top-1；不覆盖 → 11-22%。
- 环境降解主力反应类（酯/酰胺水解、芳香/脂肪羟基化、环氧化开裂、脱卤、硝基还原、
  甲基化/去甲基化等）在 USPTO 高频模板（合成向）中不占主导；enviPath 286 条覆盖
  类型但不覆盖密度。

### 2.7 结构规范化（质子化/立体化学/parent-copy/无效）

- **质子化形式系统性失配（最重要）**：EAWAG 域 uspto-only 正例 59 个中仅 14 个能以
  严格 sb 匹配命中（其余 45 个是电荷变体）；A7 gly 案（InChIKey 严格口径 miss）
  同机制。v3.3 的归一方向（中性）与库记录方向（常为阴离子）相反。
  → **v3.4 双形式发射**：`product_smiles` = 最优原始变体（严格口径友好）+
  `product_identity` = 归一化身份（双口径评分器用），`charge_variants` 全保留。
- parent-copy / invalid / ion 计数：
  - EAWAG 缓存生成侧：parent-copy **0**、invalid 15/122,398、ion 2,901（2.4%）；
  - BBD83 Top-10（部署口径 pool）：parent-copy 0、invalid 0；
  - A7 冻结产物（3 口径 × 18 案）：parent-copy 0、invalid 0、empty 0。
  本地部署链的 parent 过滤有效。对方运行中出现的 rank-0 parent copy=7 / Top-10=95 /
  invalid=4 **未能在本地复现**——需要对方提供原始输出定位（怀疑：多片段/盐形式
  parent 的边界情形，或其包装层的归一化路径差异）。**不排除、已请求复现材料**。

---

## 3. 根因综合（三层，按影响排序）

1. **检索语料/环境规则不覆盖 soil/sludge 反应族**（制度层）：语料覆盖时 Top-1
   95%，不覆盖时 11-22%。对方 1,788 parents 97.2% 处于不覆盖制度。EAWAG 域生成
   上限 72%，其中 enviPath 系承担 78% 的正确候选。**这是 Top-1 ≥50% 的真正约束。**
2. **训练/部署候选分布错配**（分布层）：训练用 top-2k USPTO 模板 + RHEA 域，
   部署用 188,725 模板 + 环境域 parent → USPTO-only 洪泛（71% Top-10）且
   ranker 对其无域内校准。
3. **跨源分数不可比 + max/3 等权融合**（融合层）：三源基率 0.3%-2.6% 差一个数量级，
   `max(p)/3` 放任 USPTO 高分负例登顶。**v3.4 已修此层**（见 §4）。

---

## 4. v3.4 修复（已实现 + 本地验证）

代码：`bbd_v34_fusion.py`（新）+ `expand_bbd_routes.py` / `single_smiles_v32.py` /
`single_smiles_hybrid.py` / `predict_bbd_products_v32.py` 接线（`--scoring v34`）。
校准器：`data/bbd_v34/calibrator_v34.json`（isotonic cutpoints，无 sklearn 依赖可加载）。

组件（对齐对方 §五 1-5）：
1. **per-source isotonic 校准**（calib split 拟合，EAWAG 环境域，v3.1 ranker 未见过）：
   三源分数 → 可比 P(correct)；
2. **校准融合** `ns34 = min(combine(cal_*) × agreement × skeleton, 1.0)`，
   combiner 在 calib split 上按预登记规则（hit@1 > hit@10 > mrr）选择；
   **制度门控**：case 存在 donor_exact_match 检索证据 → 保留 v3.3 语义
   （v34_regime 审计字段，见下方迭代披露）；
3. **双形式发射**（2.7 的修复）；
4. **EAWAG 49 规则并入部署 engine B**（v5 训练口径一致：source="envipath"）；
5. **Top-K 策略**（可选，默认：骨架降级关 + enviPath 配额=2；网格证据见 2.5）；
6. Top-1 与 Top-10 分开报告（v3.4 主打 Top-1；Top-10 差距归因到生成层）。

**设计选择与迭代过程（如实披露，三轮）**：

| 迭代 | 设计 | EAWAG calib h@1 | EAWAG val h@1 | RHEA val h@1（回归检查） |
|---|---|---:|---:|---:|
| 1 | 校准 + max（calib 对比数据流有 bug，已修复） | 25.00% | 25.06% | 未测 |
| 2 | 校准 + noisy_or（calib 修复后按预登记规则选中） | 25.26% | 24.03% | **70.66% ❌（v3.3 = 95.06%）** |
| 3 | **+制度门控**（donor_exact_match → 该 case 走 v3.3 语义），calib 重选 | 22.68%（max） | 23.26% | **95.06% ✅（= v3.3）** |

- **制度门控的必要性**（迭代 2 的失败教训）：ranker 分数分布是**域条件的** —— 同一个
  饱和检索分 0.993，在语料覆盖制度里 P(正确)≈70%+，在环境域只≈20%；EAWAG 拟合的
  校准对目标制度（库外环境域）正确、对语料覆盖制度是灾难（-24.4pp）。部署系统必须
  同时服务两个制度 → **当 case 存在 donor_exact_match 检索证据（语料覆盖制度的产品
  级信号，与 lookup 层同构）时保留 v3.3 分数语义**（该制度 v3.3 Top-1=95.1%），
  其余 case 走校准融合。门控后 calib 重选 max（hit@1 优先规则；noisy_or 的
  h10/MRR 更优但 h1 差 1 例）。每个输出行带 `v34_regime` 审计字段。
- 代价与收益：环境域 Top-1 增益从 +1.8pp（无门控）收窄为 **+1.0pp（门控）**，
  换取语料覆盖制度的完整保留 —— 部署上必要的取舍。

**本地验证（最终形态：门控 + max）**：

| 口径 | Hit@1 | Hit@3 | Hit@5 | Hit@10 | MRR@10 |
|---|---:|---:|---:|---:|---:|
| EAWAG val：v3.3 基线 | 22.22% | 34.37% | 41.86% | **52.71%** | 0.3061 |
| EAWAG val：**v3.4** | **23.26%** | 35.14% | 42.38% | 51.42% | **0.3131** |
| EAWAG val：v3.4 严格口径 | 23.00% | 34.88% | 41.34% | 49.87% | 0.3083 |
| RHEA val：v3.3 = v3.4（门控生效，全指标一致） | 95.06% | 97.41% | 97.73% | 97.81% | — |

- Top-1 +1.0pp / Top-3 +0.8pp / MRR +0.007 / Top-10 -1.3pp —— Top-1 precision 与
  Top-10 recall 的取舍正对方 §五.5 预期；Top-10 侧增益属生成层（§3.1）。
- 双形式发射把严格口径 Top-1 差距收敛到 -0.26pp（23.26→23.00）。

**BBD83 回归（公开诊断集，86 案，hybrid 口径）**：

| | Hit@1 | Hit@3 | Hit@5 | Hit@10 | MRR@10 |
|---|---:|---:|---:|---:|---:|
| v3.3 hybrid | 89.53% | **96.51%** | 96.51% | 96.51% | **0.9283** |
| v3.4 hybrid（raw = +配额策略 (10,10,2)） | 89.53% | 95.35% | 95.35% | 96.51% | 0.9239 |

无实质回归（hit@1 持平；1 案 hit@3 移位；配额在 lookup 置顶制度下不触发）。

**Top-K 策略网格（val，预登记选择：hit@10 > hit@1 > 更简）**：骨架降级 2/3 档
全部低于无策略（0.496 vs 0.514）→ **骨架降级默认关闭**；enviPath 配额=2
与 raw 持平 → 保留为默认（针对部署制度 USPTO 洪泛的结构性保护，本地无害）。
完整网格见 `v34_val_grid.json`。

---

## 5. 达标差距与所需工作（诚实评估）

以对方目标（combined Top-1 ≥50%，期望 60%）衡量：

1. **融合层修复不足以达标**：v3.4 在本地代理上 Top-1 +1.0pp；对方制度更严。
   数字上的锚点：环境域代理 Top-1 = 25.1%，生成上限 71.9% —— 即使排序完美
   （oracle），仍有 28% 不可达；排序从 25%→50% 需要生成+证据双扩。
2. **必须做的资产级工作**（对方 §五.1 的量化版）：
   - enviPath 规则库扩充（286 → 千级；水解/氧化/脱卤/硝基还原的密度）；
   - 检索语料并入环境域反应（enviPath 全量 pathway 数据、EAWAG-Soil 类来源）；
   - v5 ranker（is_eawag_domain）取回或重训（当前在 HF teacher 侧）；
   - EAWAG 49 规则已并入 v3.4 部署（本轮完成，量级有限）。
3. **请求对方配合**：
   a. 提供 soil/sludge 诊断集副本（对方已定性为公开诊断集）+ 其运行原始输出
      （定位 parent-copy/invalid 的 95/4 计数来源）；
   b. enviPath 资产的获取/授权路径；
   c. 新外部 holdout 冻结口径（对方 §六）。

---

## 6. 验收交付物状态（对方 §六清单）

| # | 要求 | 状态 |
|---|---|---|
| 1 | 固定 commit + 代码/模型/数据 SHA256 | 本轮诊断+修复 commit 见 git log；冻结 manifest 待对方复跑轮 |
| 2 | 独立 train/validation 调参过程 | ✅ calib/val split（seed=0）+ 预登记选择规则 + 网格全记录 |
| 3 | soil/sludge/sludge 分项 Hit@K+MRR | ⏳ 需对方在 v3.4 冻结版上复跑（本地无该集） |
| 4 | BBD-parent-excluded | ⏳ 同上（复跑时按对方口径输出） |
| 5 | lookup-visible/excluded | ✅ 本地：BBD83 pred-only(lookup-excl) hit@1=0/4 案；⏳ 对方集 |
| 6 | source-tag 漏斗 + oracle recall | ✅ 本报告 §2.1/2.2（对方集复跑脚本已就绪） |
| 7 | parent-copy/invalid/empty 计数 | ✅ 本地全 0（§2.7）；对方侧待原始输出 |
| 8 | 逐 case 冻结预测 + manifest | ⏳ 对方复跑轮（驱动脚本沿用 T62 A7 freeze 模式） |

复跑命令（对方接口不变，仅 `--scoring v34`）：

```bash
cd /Volumes/CC/Enzyme_Agent/depending/reaction_analogy
python single_smiles_hybrid.py --smiles "<parent>" \
    --top-k 10 --max-depth 1 --scoring v34 --case-id <id> \
    --out-prefix <prefix>
```

---

## 7. 一句话结论

v3.3 在 soil/sludge 的 11.69% 不是运行失败，是**检索语料/环境规则不覆盖 + USPTO
洪泛未被校准**的必然结果；v3.4 修复了融合层（本地代理 Top-1 +1.0pp、RHEA 制度门控保留 95.1%、
BBD83 无回归）并暴露了真正约束：**要达到 ≥50% 必须扩充环境域资产（语料+规则+域内
ranker），仅排序层无解**。请对方提供诊断集副本与资产路径后进入下一轮。
