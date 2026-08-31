# BBD MPNN 域微调试水 — 决策报告

**日期**: 2026-08-31
**任务书**: `CC/TASK_MPNN_DOMAIN_TRIAL_CHENYU_2026-08-31.md`
**执行**: GLM-5.2 → 本报告
**判据结论**: **No-Go**

---

## 0. Go/No-Go 判据表（跑前定死，§5.3 红线：先判据后结果）

| 指标 | 基线（v3 原模型） | Go 门槛 |
|------|-----------------|---------|
| BBD 93 底物 top1-top2 原子概率分离度（中位） | 0.0195 | **≥ 2× 基线 = 0.039** |
| 分离度 < 0.01 的底物占比 | 44% | **≤ 30%** |
| USPTO test hit@1（防灾难遗忘） | 75.23% | **≥ 70%** |

三项全过 = **Go**（P6 立项）; 分离度两项过但 USPTO 崩 = **有条件 Go**（§4.4 重试一次）; 其他 = **No-Go**。

---

## 1. 架构修正（先说明）

任务书 §4.2 写微调模型为 `MPNN(68, 6, 256, 6)`，但 chenyu `~/rxn6/gnn_model_v3/model.pt` 的 state_dict 实际是 **`MPNN(68, 6, 384, 8)`**：

- `atom_emb.weight (384, 68)`、`mps.0..mps.7`（8 层）→ `d_hidden=384, n_layers=8`
- `~/rxn6/gnn_model_v3/result.json` 明确记录 `"hidden": 384, "layers": 8, "hit1": 0.7523`

用 256/6 调 `load_state_dict` 会 shape mismatch 崩溃，故全程用 **384/8**。`hit1=75.23%` 与任务书一致，仅架构维度记录有误。参数量 3,574,657。

---

## 2. Phase 1 — 数据派生（本地）

**脚本**: `reaction_analogy/build_finetune_trial_data.py`
**输入**: `reaction_analogy/data/aam/aam_sample.jsonl`（500 条 RHEA，479 ok+roundtrip）

**派生逻辑**（§4.1）: 对每条 `mapped_reaction_smiles = lhs>>rhs`，用 atom-map 号将 lhs/rhs 原子配对，比对 (a) 形式电荷、(b) 总 H 数、(c) 对 mapped 邻居的键序签名（`GetBondTypeAsDouble`）；任一变化即记该 lhs 原子为 reacted。`substrate_smiles` 保留 lhs 的 atom-map（与 USPTO 训练集口径一致，保证 `mol_to_tensor` 解析序与 `reacted_atom_indices` 对齐）。

**统计**:

| 项 | 值 |
|----|----|
| 总输入 | 500 |
| ok+roundtrip | 479 |
| parse fail | 0 |
| 多片段 lhs 丢弃 | 0 |
| **无 reacted 原子丢弃** | **110** |
| 泄漏剔除 | 2 |
| **最终训练集** | **367** |

110 条"无 reacted"全部是**纯立体异构化反应**（R/S 翻转）——lhs/rhs 的 stereo-blind canonical 完全相同，且 aam 自身 `changed_atom_detail.changed_reactant=0`，无原子级反应性标签，按 §4.1 正确丢弃。这使最终 367 条低于任务书预测的 ~450-470，但属正确口径（23% 的 RHEA 样本是异构酶，对原子活性训练无信号）。367 条对试水足够。

**reacted 原子数分布**: 3 个（184 条，最多）、4 个（76）、5-6（46）、7-10（36）、>10（25）。

### 抽查 3 条（派生 vs aam changed_atom_detail）

| record_id | 派生 n_reacted | aam changed_reactant | 一致? |
|-----------|---------------|---------------------|------|
| rhea:10005 | 4 | 4 | ✅ |
| rhea:10006 | 4 | 4 | ✅ |
| rhea:10057 | 3 | 10 | ❌（见下） |

- rhea:10005 / 10006: 简单异硫氰酸酯/硫氰酸酯重排，派生 4 个 reacted 与 aam 完全一致（C-S-C 键序翻转的 4 个原子）。
- rhea:10057: CoA 硫酯消除反应（C2-C3 单键→双键 + NH3+ 离去为 NH4+）。派生按 §4.1 精确口径得 3 个真实键/电荷/H 变化原子（C2、C3、N54），而 aam 报告 `changed_reactant=10`（`covered=20=2×10` 对称计数）用的是更宽的邻域计数。差异是算法口径之别，非 bug——派生遵循 §4.1 的"键变化∪电荷/H 变化∪新键形成"定义，2/3 简单案例完全匹配验证了逻辑正确性。

**泄漏断言（红线 §5.1）**: 训练 substrate（stereo-blind canonical）∩ 93 blind parent = **0**（2 条撞 blind 已剔除，断言通过）。

---

## 3. Phase 2 — chenyu 微调 + 推理

**脚本**: `reaction_analogy/finetune_trial_chenyu.py`（上传至 chenyu `~/rxn6/mpnn_trial/`）
**硬件**: 单卡 RTX 4090 D，torch 2.7.1+cu126，无 DataParallel（§4.5 确定性）。
**种子**: `torch.manual_seed(0)` + cuda seed + `np.random.seed(0)` + cudnn deterministic。

**微调配置**（§4.2）: lr=1e-4（预训练 1/10），epochs=50，early_stop patience=10（train loss），pos_weight=20，bsize=32，全参数不冻结，BCEWithLogits+mask。

**训练结果**:

| 项 | 值 |
|----|----|
| 训练样本 | 367 |
| epochs 跑完 | 50（未触发早停） |
| best train loss | 1.8907 @ ep48 |
| 起始 loss | 3.5537 (ep0) |
| wall time | 42.5s |

train loss 单调下降（3.55→1.89，50 epoch 无早停）——**367 样本上的典型过拟合**（§8 陷阱）。loss 仍缓慢下降故 patience 未触发。这是过拟合信号：模型在拟合 RHEA 标签，但（见下）这种拟合未迁移到 BBD 底物。

**推理 A — BBD 93**: 从 `~/rxn6/bbd_predictions.jsonl` 读 93 条 smiles（保证与基线同底物同序），微调后 + v3 原模型各跑一次（cuda），按基线 schema dump 概率。
**推理 B — USPTO 防遗忘**: `~/rxn6/gnn_uspto_test/train_set.jsonl`（39,994 条）用 `np.random.RandomState(0)` 抽 5k，对微调后 + v3 原模型各跑一次 hit@1（同 5k 同口径配对）。

---

## 4. Phase 3 — 评估与判据（本地）

**脚本**: `reaction_analogy/eval_finetune_trial.py` → `data/bbd_mpnn_trial/trial_eval.json`

### 三指标对照表

| 指标 | 原基线(CPU) | 配对 v3(cuda) | 微调后 | Go 门槛 | 过? |
|------|-----------|-------------|--------|---------|----|
| 分离度中位 top1-top2 | 0.01947 | 0.01947 | **0.01844** | ≥0.039 | ❌ |
| 分离度 <0.01 占比 | 44.1% | 44.1% | **39.8%** | ≤30% | ❌ |
| USPTO hit@1 (5k) | — | 75.24% | **57.10%** | ≥70% | ❌ |
| (ref 全量 40k v3) | 75.23% | — | — | — | — |

**三项全不过 → No-Go。**

### 关键观察

1. **分离度纹丝不动**: 微调后中位 0.0184 vs 基线 0.0195——不升反略降，远未达 2× 门槛 0.039。<0.01 占比 44.1%→39.8% 仅边际改善，远未达 30%。**MPNN 在 BBD 底物上的概率饱和未因 RHEA 微调而打开。**
2. **配对基线验证**: 原基线(CPU, 0.01947) = 配对 v3(cuda, 0.01947) = 文档 0.0195，三者一致——cuda/CPU 无设备伪影，基线口径可靠。USPTO 配对 v3 hit1=75.24% ≈ 全量 40k 75.23%，5k 抽样代表性验证通过。
3. **灾难遗忘**: USPTO hit@1 75.2%→57.1%，暴跌 18pp，远低于 70% 门槛。模型确实学到了 RHEA 标签（loss 降、USPTO 崩），但学到的变化**没有转化为 BBD 分离度的提升**——只破坏了 USPTO 知识，没获得 BBD 判别力。
4. **§4.4 重试不适用**: 重试条件是"分离度两项 Go 但 USPTO 崩"。本试水分离度两项均不过，故不触发重试（最多一次重试的纪律自然满足：0 次重试）。

### 分离度直方图（bin: count）

| bin | 配对 v3 | 微调 |
|-----|--------|------|
| 0-0.005 | 37 | 35 |
| 0.005-0.01 | 4 | 2 |
| 0.01-0.02 | 6 | 11 |
| 0.02-0.05 | 21 | 14 |
| 0.05-0.1 | 8 | 13 |
| 0.1-0.2 | 8 | 11 |
| 0.2-0.5 | 5 | 6 |
| 0.5-1.0 | 4 | 1 |

微调后低分离度区（0-0.01）从 41→37 条（边际），高分离度区（0.5-1.0）从 4→1 条（反而减少）。整体分布基本未变，微调对 BBD 原子概率分离度无系统性改善。

---

## 5. 结论与建议

### 判据结论: **No-Go**

MPNN 的 BBD 域失效（v2 消融 ±0pp、概率饱和）**不是 479 样本量级 RHEA 微调能修复的**。试水的核心信号: 即便模型在 367 条 RHEA 上拟合到 loss 单调下降、且为此付出灾难遗忘（USPTO 75%→57%）的代价，BBD 93 底物的原子概率分离度仍纹丝不动（中位 0.0195→0.0184）。这说明**域外失配 + 标签稀缺**的死结未被小样本微调打开——模型要么背了 RHEA 标签（过拟合，不泛化到 BBD 结构），要么输出仍被 USPTO 先验主导（饱和概率无区分度）。

### 建议行动

- **MPNN 在 BBD 战线正式盖棺**: 按任务书 §0，No-Go = 省下全量 37k RHEA 映射 + 正式微调的全部 GPU 费。MPNN 底座在 BBD 域作为 negative result / ablation 记入论文（与 v2 消融 ±0pp、v3.2 删 MPNN 特征反升的成绩呼应，形成完整的"域外 MPNN 失效"证据链）。
- **BBD 产物预测与排序**: 维持 v3.2+ 时代的非-MPNN 路线（检索 + 规则 + 查表混合，见 P4.2 hybrid 报告），不再期待 MPNN 原子概率贡献。
- **试水产物的归宿**: `trial_bbd_probs.jsonl`、`model_finetuned_trial.pt` 仅留本评估与报告，不进任何预测/排序/提交包（见 §6 管线隔离 grep）。

### 诚实的局限说明

本试水用的是 367 条 RHEA（非全量 37k）+ 激进全参数微调（lr=1e-4，无 replay，无冻结）。理论上一个更保守的 P6（全量 37k + replay 数据混合 + 低 lr + 部分冻结）**可能**表现不同。但试水提供的信号是明确的负面——分离度对 367 样本微调**完全无响应**，而全量 37k 的主要增量是更多同分布标签，未必能克服"结构域外失配"这个根因（BBD 环境底物与 RHEA/USPTO 的结构空间差异）。**按预定判据，No-Go，不立项 P6。** 若未来出现新的正面证据（如更大 RHEA 映射 + 更高 roundtrip 保真），可重评估，但当前无正面信号支撑。

---

## 6. 红线合规

| 红线 | 执行 |
|------|------|
| §5.1 泄漏断言 | ✅ 训练 substrate ∩ 93 blind = 0（2 条撞 blind 已剔除，断言通过；独立可由 `finetune_train_stats.json` 复算） |
| §5.2 管线隔离 | ✅ trial 产物只进 `eval_finetune_trial.py` + 本报告；grep 预测/排序/查表/提交包文件对 `trial_bbd_probs`/`model_finetuned_trial` 零引用（见下） |
| §5.3 判据先于结果 | ✅ §0 判据表在本报告最前，结果在后；脚本 `eval_finetune_trial.py` 同样先打印判据表再打印结果 |
| §5.4 chenyu 只跑微调+推理 | ✅ 数据派生（Phase 1）与评估（Phase 3）均在本地，可复现 |
| §5.5 新文件只放 `~/rxn6/mpnn_trial/` | ✅ chenyu 上 `finetune_trial_chenyu.py` + 5 个产物全在 `~/rxn6/mpnn_trial/` |
| 不改已交付文件 / 不 push | ✅ 全部新建文件，未修改既有管线；commit 不 push |
| §4.4 重试纪律 | ✅ 0 次重试（分离度不过→不触发；≤1 次上限满足） |

### 管线隔离 grep 证据

对 `predict_bbd*.py`、`score_bbd*.py`、`bbd_v*_scoring.py`、`bbd_v*_ranker.py`、`eawag_lookup.py`、`build_hybrid_submission.py`、`rank_*.py` 等管线文件 grep `trial_bbd_probs` 与 `model_finetuned_trial`：**零命中**（trial 产物未被任何管线引用）。grep 命令与结果存于 commit。

---

## 7. chenyu 收尾

试水产物已全部拉回本地 `reaction_analogy/data/bbd_mpnn_trial/`。chenyu `~/rxn6/mpnn_trial/` 保留（用户决定何时关机——本任务是 P5 之后唯一需要 chenyu 的任务，做完即可关机）。

---

## 8. 确定性与双跑

- **Phase 1 派生**: 纯 RDKit 解析，无随机性，天然确定性。重跑结果相同。
- **Phase 3 评估**: 纯 numpy 数值计算（固定概率文件），天然确定性。
- **Phase 2 训练**: 设了 seed=0 + cudnn deterministic。训练双跑为可选（§4.5）。**未做双跑**——理由: 结论是分离度对微调**无响应**（0.0195→0.0184，delta 远小于任何 cudnn 噪声量级，且方向是略降），USPTO 崩是 18pp 的大效应。无论双跑的微差如何，三项判据均不会翻盘，verdict No-Go 鲁棒。

---

## 9. 交付物清单

| 文件 | 类型 | 位置 |
|------|------|------|
| `build_finetune_trial_data.py` | 新建 | `reaction_analogy/` |
| `finetune_trial_chenyu.py` | 新建 | `reaction_analogy/`（+ chenyu `~/rxn6/mpnn_trial/`） |
| `eval_finetune_trial.py` | 新建 | `reaction_analogy/` |
| `finetune_train.jsonl` + `finetune_train_stats.json` | 输出 | `reaction_analogy/data/bbd_mpnn_trial/` |
| `trial_bbd_probs.jsonl` / `trial_bbd_probs_v3.jsonl` / `trial_uspto_hit.json` / `train_log.json` / `model_finetuned_trial.pt` | 输出 | `reaction_analogy/data/bbd_mpnn_trial/` |
| `bbd_predictions_v3_baseline.jsonl` | 拉回基线 | `reaction_analogy/data/bbd_mpnn_trial/` |
| `trial_eval.json` | 输出 | `reaction_analogy/data/bbd_mpnn_trial/` |
| `BBD_MPNN_TRIAL_REPORT_2026-08-31.md` | 本报告 | `reaction_analogy/reports/` |
| 分支 `feat/mpnn-domain-trial` | commit 不 push | — |
