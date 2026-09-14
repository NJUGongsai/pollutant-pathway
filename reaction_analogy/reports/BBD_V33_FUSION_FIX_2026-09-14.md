# BBD v3.3 融合层修复报告 — DBP 路线预测问题

日期：2026-09-14
对象：reaction_analogy 单污染物路线预测链（v3.2 引擎 + 新增 v3.3 融合层）
触发：测试部门《DBP路线预测结果与问题总结》（2026-09-12，冻结包 dbp_d4_...20260911）

## 一句话结论

四个问题全部修复并验证：正确的 DBP 首步产物 MBP 现在排 Rank 1（电荷归一化身份、
uspto+enviPath 融合），无降解依据的旧 Top-1 被通用骨架合理性检查降权到 Rank 2 并带
审计标记；max_depth=3 产生真实多步展开
（depth_engine_invocations={"1":1,"2":5,"3":21}）；
PRIMARY 级联与 Top-3 诊断路线均可恢复 DBP → MBP → phthalic acid；
93 例 BBD 盲测集无回归（strict Hit@1 36.0%→37.2%）。

## 1. 根因（对照测试报告 §4）

| 报告问题 | 根因定位 | 证据 |
|---|---|---|
| 4.1 Top-1 排序错误 | `ns_score = max(p_source)/3` 无跨源一致性约束；USPTO ranker 首要特征是 `log1p_template_freq`（v31_train_stats.json），高频合成模板天然高分（错误产物 pU=0.7917 vs MBP 的 pE=0.5522） | 复现运行：DBP Top-3 与冻结报告 0.263902/0.184055/0.146132 完全一致，生成计数 USPTO 374 / enviPath 11 / retrieval 25 完全一致 |
| 4.3 电荷规范化不足 | 候选按 raw canonical SMILES 去重；中性 MBP 与 MBP carboxylate 身份分裂，证据分散（中性 MBP 落到 rank 161，pU=0.005；carboxylate rank 2） | 复现运行 MBP-related 候选表 |
| 4.5 多步未展开 | 仓库侧无单 SMILES 递归入口；测试包装脚本只调用了一次引擎（depth 1），BFS 展开逻辑在 expand_bbd_routes.py 中但未被单化合物入口复用 | `depth_engine_invocations={"1":1}` |
| 4.2 下游只取 Rank 1 | 排序误差被 PRIMARY=rank-1 规则放大；无 Top-3 诊断通道 | 冻结的 Route B/C/酶池链 |
| 4.4 合理性约束缺失 | 无原子收支/骨架检查；`-C(=O)O-nBu → -CH3`（丢 6 重原子、两块无法归类的碎片）无提示成为 Top-1 | 骨架检查器输出 flag:unexplained_fragment[O]->C;[CCCCO]->C |

## 2. 修复内容（文件清单）

### 新增
- `reaction_analogy/bbd_v33_fusion.py` — 核心融合层：
  1. **电荷/质子化归一化**（RDKit Uncharger + canonical，lru_cache）：`normalize_charge_smiles`
     生成"可审计产物身份"；`merge_charge_variants` 合并同一身份的变体（p_source 取
     成员最大值=证据最大池化，source 标签取并集，`charge_variants` 保留全部原始形式）；
  2. **来源一致性加成**：`ns33 = (max p_source/3) × (1 + 0.15×(n_independent_sources−1))`，上限 1/3；
  3. **通用骨架合理性检查** `assess_skeleton_change`：产物作为底物（键级松弛）子结构
     匹配 → 归还丢失重原子为连通碎片 → 白名单归类（纯烷基 O/N/S-脱烷基、脱羧、
     脱卤、脱硝、≤2 原子小变化），无法归类 → ×0.70 惩罚 + `skeleton_unexplained/reason`
     审计字段。常数（0.15/0.70）为先验化学参数，未对任何基准拟合；
  4. 平局决胜与 v3.2 一致（stereo-blind canon），分数语义字符串
     `ns33_max_source_x_agreement_x_skeleton_over_3`，`is_calibrated_probability=false` 保留。
- `reaction_analogy/single_smiles_v32.py` — 单 SMILES 入口（与测试报告接口一致：
  --smiles/--top-k/--max-depth）：depth 1 三引擎生成 + v3.3 融合；depth≥2 逐级 BFS
  （frontier K1=5/K2=5）；输出冻结链兼容产物
  `*_RAW_STDOUT.json / *_ALL_NORMALIZED_PREDICTIONS.csv / *_RUN_META.json /
  *_TOP3_DIAGNOSTIC_ROUTES.jsonl`（含 depth_engine_invocations、PRIMARY=rank-1 级联、
  路线装配、每边 v3.3 审计字段）。
- `reaction_analogy/score_bbd_hitk_v33.py` — v3.3 评测器：在 v3.2 pool 上重排，
  **同时输出 strict-neutral-exact 与 charge-normalized 两种口径**（报告 §4.1 要求双口径）。
- `reports/DBP_V33_RERUN_2026-09-14/` — DBP 重跑全部产物 + DEHP 回归 + 单元测试脚本。

### 修改
- `reaction_analogy/predict_bbd_products_v32.py`：`--scoring v33`（默认）走融合层；
  序列化携带 `charge_variants/ns_semantics/n_independent_sources/skeleton_*`；
  `--scoring v32` 保留原行为可复现历史。
- `reaction_analogy/expand_bbd_routes.py`：`_score_and_sort` 接入 v3.3；BFS 节点身份、
  环检测、node_id 改用电荷无关 identity（MBP 与其 carboxylate 是同一节点）；depth-1
  从池重打分；边携带审计字段；stats 增加 `depth_engine_invocations`。

### 未改动（有意）
- 三个 v3.1 LightGBM ranker 与特征定义：模型级修复（域校准重训、把合理性特征纳入训练）
  列为后续工作；本轮修复在打分层完成，不使已训练模型失效。

## 3. 验证证据

### 3.1 单元测试（test_bbd_v33_fusion_unit.py，17 项全过）
MBP 水解丢失归因为干净脱烷基；错误重排产物标记 unexplained（丢 6 重原子）；脱羧/
脱烷基/脱卤/脱硝归因正确；环氧化（纯获得）不误标；MBP 两变体合并为单一身份且
双来源；融合分翻转（MBP 0.2117 > 错误产物 0.1847）。

### 3.2 DBP 端到端（--top-k 10 --max-depth 3，约 14 分钟）

| 指标 | 修复前（冻结 D1） | 修复后 |
|---|---|---|
| Rank 1 | `CCCCOC(=O)c1ccccc1C` 0.2639（无降解依据） | **`CCCCOC(=O)c1ccccc1C(=O)O`（MBP）0.2117**，uspto+envipath |
| Rank 2 | MBP carboxylate 0.1841 | 旧错误产物 0.1847，`skeleton_unexplained=true` |
| charge-normalized Hit@1 | 0 | **1** |
| 中性 MBP exact | 未输出 | Rank 1（合并身份显示中性形式） |
| depth_engine_invocations | `{"1":1}` | **`{"1":1,"2":5,"3":21}`** |
| 多步路线 | 无 | PRIMARY 级联：MBP → phthalic acid → 2-formylbenzoic acid；TOP3 诊断路线均 3 步，其中一条即 DBP→MBP→PTA |
| 评价口径 | 单一 | strict + charge-normalized 双口径同报 |

### 3.3 BBD83 盲测集回归（86 可评案例，answer key 隔离协议同 v3.2）

| 口径 | 指标 | v3.2 基线 | v3.3 |
|---|---|---|---|
| strict | Hit@1 | 36.0% | **37.2%** |
| strict | Hit@3 | 57.0% | **59.3%** |
| strict | Hit@5/@10/@20 | 66.3/68.6/75.6% | 66.3/68.6/75.6%（持平） |
| charge-norm | Hit@1/@3/@10/@20 | — | 37.2/61.6/70.9/79.1% |

无回归，头部指标提升；电荷变体合并 146 对。

### 3.4 非目标准确性回归（DEHP，depth-1）
Rank 1 = MEHP（正确的单酯水解产物，uspto+envipath，0.3323）；同类芳基-CH3 错误
重排降 Rank 2 且带骨架标记；游离 2-乙基己醇（整核丢失）被标记。
证明融合规则为通用酯类水解先验，非 DBP 特例。

## 4. 对测试部门的复跑说明

```bash
cd /Volumes/CC/Enzyme_Agent/depending/reaction_analogy
python single_smiles_v32.py --smiles "CCCCOC(=O)c1ccccc1C(=O)OCCCC" \
    --top-k 10 --max-depth 3 --case-id DBP --out-prefix <输出前缀>
# 批量（冻结链口径）：
python predict_bbd_products_v32.py ... --scoring v33   # 默认；v32 保留
python expand_bbd_routes.py ... --scoring v33
```

注意：真实多步展开需要逐级调用引擎，单化合物 max_depth=3 全量运行约 10–15 分钟
（此前 48 秒是 depth-1-only 的表现，正是报告 4.5 的问题）。

## 5. 后续工作（模型级，未包含在本轮）

1. USPTO ranker 对高频模板的过度自信：来源分位校准/重训时加入骨架合理性特征
   （现有检查器的归因结果可直接作为训练特征）；
2. enviPath 规则覆盖率（286 条）有限，PAE 类首步水解目前靠 uspto+envipath 双来源
   支撑；扩充环境降解规则库可加宽安全边际；
3. 下游酶/宿主模块接入 `*_TOP3_DIAGNOSTIC_ROUTES.jsonl` 做能力诊断（报告建议 #6）。
