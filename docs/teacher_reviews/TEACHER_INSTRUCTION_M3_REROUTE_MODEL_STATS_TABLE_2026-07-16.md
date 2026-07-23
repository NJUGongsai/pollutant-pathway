# 任务重排：学生转做论文级模型性能统计表 & 智能体搭建收回

日期：2026-07-16  
上游文档：`TEACHER_REPLY_D4_ACCEPTED_AND_M3_STARTUP_PACKAGE_2026-07-16.md`  
状态：M3 智能体搭建部分收回（导师自做）/ 学生转向论文级性能统计表交付

---

## 一、分工调整

**原 M3 分工作废**，重新分工如下：

| 里程碑 | 之前分工 | 现分工 |
|---|---|---|
| M3-P0 前置澄清（4 决策） | 学生本地建议 → 导师裁定 | **撤销**。智能体架构由导师直接定 |
| M3-P1 Substrate + Reaction Agent | 学生做 | **导师做** |
| M3-P2 EnzymePoolAgent | 学生做 | **导师做** |
| M3-P3 EnzymeCAGEAgent + orchestrator | 学生做 | **导师做** |
| M3-P4 3 case 端到端 | 学生做 | **导师做** |
| **新增：论文级性能统计表** | — | **学生做** ← 本轮唯一任务 |

**分工调整理由**：智能体层与 ADRMATS 现有架构共享 CrewAI + BaseAgent + prompts YAML 那套骨架，导师侧做集成成本更低；学生的比较优势在于对 v1 冻结数据、12 次训练运行、seed 级原始产物的一手掌握，直接支撑论文写作的性能分析章节最合适。

---

## 二、交付物：论文级模型性能统计表

**目标**：一份可以直接支撑论文 "Results / Experiments" 章节的完整性能分析材料。不做新训练，**只从已有的 12 次训练运行 + P0/P1/P2 冻结产物里**汇总、重分析、分层。

### 2.1 交付清单

```text
model_performance_statistics_v1/
├── MODEL_PERFORMANCE_STATISTICS_TABLE_v1.md    # 主文档：所有表格 + 说明
├── raw_data/
│   ├── per_seed_predictions.csv                # 每个 seed × 每个 test reaction 的原始预测
│   ├── ensemble_predictions.csv                # 5-seed ensemble 汇总
│   └── bootstrap_samples.jsonl                 # paired bootstrap 每轮采样结果
├── stratified/
│   ├── per_ec_class.csv                        # 按 EC 1-7 分层
│   ├── per_reaction_novelty.csv                # 按底物新颖性分层（如可行）
│   └── per_enzyme_similarity.csv               # 按 enzyme 序列相似性分层（如可行）
├── figures/
│   ├── loss_curves.svg                         # train/valid/test loss 曲线
│   ├── metric_convergence.svg                  # 各指标随 epoch 变化
│   └── roc_pr_curves.svg                       # ROC + PR 曲线（3B ensemble vs 600M ensemble）
├── latex/
│   └── tables.tex                              # 主表格的 LaTeX 版本，可直接粘进论文
└── audit_manifest.sha256                       # 所有产物的 SHA256 完整性清单
```

### 2.2 必须包含的核心表格

**表 1：Overall Performance（主表）**

| Model | Seeds | AUC (Macro) | AUPR (Macro) | Hit@1 | Hit@3 | Hit@5 | Hit@10 | MRR@10 |
|---|---|---|---|---|---|---|---|---|
| ESM-2 3B | seed 40 | ... | ... | ... | ... | ... | ... | ... |
| ESM-2 3B | seed 41 | ... | ... | ... | ... | ... | ... | ... |
| ESM-2 3B | seed 42 | ... | ... | ... | ... | ... | ... | ... |
| ESM-2 3B | seed 43 | ... | ... | ... | ... | ... | ... | ... |
| ESM-2 3B | seed 44 | ... | ... | ... | ... | ... | ... | ... |
| **ESM-2 3B** | **ensemble (5)** | **...** | **...** | **...** | **...** | **...** | **...** | **...** |
| ESM-C 600M | seed 40-44 (5 rows) | ... | ... | ... | ... | ... | ... | ... |
| **ESM-C 600M** | **ensemble (5)** | **...** | **...** | **...** | **...** | **...** | **...** | **...** |

**每个 ensemble 行必须给出 paired bootstrap 95% CI**（[lower, upper]）。

**表 2：3B vs 600M Paired Comparison**

对每个指标做 paired bootstrap（沿用 P0 已用的 10000 次配对重采样）：

| Metric | 3B mean | 600M mean | Diff | 95% CI | p-value |
|---|---|---|---|---|---|
| Macro AUC | ... | ... | ... | [..., ...] | ... |
| MRR@10 | ... | ... | ... | [..., ...] | ... |
| Hit@1 | ... | ... | ... | [..., ...] | ... |
| Hit@5 | ... | ... | ... | [..., ...] | ... |
| Hit@10 | ... | ... | ... | [..., ...] | ... |

**表 3：Per EC Class Stratified Performance**

按 EC top-level (EC 1: Oxidoreductases / EC 2: Transferases / EC 3: Hydrolases / EC 4: Lyases / EC 5: Isomerases / EC 6: Ligases / EC 7: Translocases) 分层：

| EC class | # reactions | # enzymes | 3B AUC | 3B MRR@10 | 3B Hit@10 | 600M AUC | 600M MRR@10 | 600M Hit@10 |
|---|---|---|---|---|---|---|---|---|
| EC 1 | ... | ... | ... | ... | ... | ... | ... | ... |
| ... | ... | ... | ... | ... | ... | ... | ... | ... |

**这张表非常关键**——论文里 reviewer 一定会问"模型对哪类反应表现更好"。

**表 4：Training Dynamics**

12 次训练运行的收敛信息：

| Run | Model | Seed | LR | Total epochs | Best epoch | Best valid loss | Test AUC @ best | Wall time (h) |
|---|---|---|---|---|---|---|---|---|
| 1 | ESM-2 3B | 40 | 3e-4 | ... | 10 | ... | ... | ... |
| ... | ... | ... | ... | ... | ... | ... | ... | ... |

**表 5：Ablation Studies**

P1（半 lr）和 P2（校正 pocket）的结果，注明每一项是"辅助诊断"不是"主线消融"：

| Ablation | Δ AUC | Δ MRR@10 | 95% CI | 定性结论 |
|---|---|---|---|---|
| P1: LR 3e-4 → 1.5e-4 (seed 40 only) | ... | ... | [..., ...] | 3B 欠训练假设否定 |
| P2: 600M 未校正 → 校正 pocket (seed 40) | ... | ... | [..., ...] | 600M 对 pocket 口径敏感 |

### 2.3 分层分析（能做多少做多少）

**必做**：
- Per EC top-level class（表 3）

**尽力做**：
- Per reaction novelty：区分"底物在训练集出现过" vs "新底物"（如果 test 集自带这个标签）
- Per enzyme cluster：按 CD-HIT 30%/60%/90% 序列相似性对 test enzyme 聚类，看模型对"跟训练集相似 vs 差异大"的 enzyme 表现差异
- Per pocket quality：如果冻结数据里有 pocket confidence score，按高/中/低分层

**不做**（明确排除）：
- 不做新的 baseline 训练（对比 Prot2Prot / ESP / CLIPZyme 这些不在本次任务范围）
- 不做特征消融（去掉 GVP / 去掉 pocket ESM 之类的，都要重训，本次不做）

### 2.4 必须遵守的表述纪律

沿用 D4 交付确立的三条：

1. **边界如实披露**：所有已知问题（pocket 处理不对称、batch-context sensitivity、Hit@10 = 73% 的 27% 长尾）必须在报告 "Known Limitations" 章节明确列出，不藏
2. **表述不越界**：CI 描述为"paired bootstrap 95% CI"或"5-seed empirical quantile range"，**不**说成"population 95% CI"；p-value 不引申为"效应显著"或"效应不显著"，只报数字
3. **权限自觉**：报告尾部写"本地统计通过 / 提交审阅"，不写"通过论文投稿标准"

### 2.5 数据溯源要求

**每一个数字都必须能溯源**。在 MODEL_PERFORMANCE_STATISTICS_TABLE_v1.md 的每个表格下方注明：

```text
Data source: <哪个 run / 哪个 checkpoint SHA256 / 哪个 eval 脚本 / 生成时间>
```

原始 CSV/JSON 文件本身要留在 `raw_data/` 下，任何统计数字要能从原始文件重算复现。

### 2.6 图的要求

**Loss curves**：3B 5 seed 各画一条，valid/test 分色；ensemble 后不画（loss 无 ensemble 意义）。要标出 best epoch 位置。

**ROC + PR curves**：3B ensemble vs 600M ensemble 两条并排，标出 AUC / AUPR 数值。

**Metric convergence**：AUC / MRR@10 / Hit@10 三个指标各画一张图，横轴 epoch，纵轴指标值，5 seed 各一条 + ensemble 一条粗线。

图用 SVG 格式，方便论文投稿时改格式。matplotlib 生成即可，不用 tikz。

---

## 三、不做的事（边界前置明确）

- **不做新训练** ——只用已有的 12 次运行结果
- **不改 v1 冻结** —— 所有 checkpoint 保持只读
- **不做智能体相关代码** —— 那块导师直接做
- **不写 M3 前置澄清文档** —— 4 决策撤销
- **不做外部 baseline 复现** —— 论文对比表格用文献报告值，本次不复现别人的模型

---

## 四、时间预期

| 阶段 | 内容 | 预计耗时 |
|---|---|---|
| P1 数据抽取与整理 | 从 12 个训练运行里抽出所有 per-seed 原始预测，整理成规范 CSV | 1 天 |
| P2 主表统计（表 1-4） | Overall / Paired / EC 分层 / Training dynamics | 1-1.5 天 |
| P3 分层分析（表 3 + 2.3 里能做的） | Per EC 必做 + Novelty/Similarity 尽力做 | 1 天 |
| P4 图与 LaTeX 输出 | 3 类图 + tables.tex | 0.5 天 |
| P5 报告主文档 + 本地审计 + SHA256 清单 | MODEL_PERFORMANCE_STATISTICS_TABLE_v1.md 收尾 | 0.5 天 |

**总计约 4-5 天**。这个时间预算允许做完前 3 张必做表 + 1 张 EC 分层。剩余分层（novelty / similarity）能做多少算多少，做不完在报告里明确 N/A 披露。

---

## 五、验收标准

按 D4 模式，这次也走"前置澄清 + 本地审计"：

**前置澄清**（先做，1 天）：

学生开工前先出一份 `MODEL_STATS_PREIMPLEMENTATION_CLARIFICATION.md`，回答：

- Q1: 12 次训练运行的具体清单是什么？哪些是主线（3B seeds 40-44 + 600M seeds 40-44 = 10 次），哪些是辅助（P1 半 lr = 1 次、P2 校正 pocket = 1 次）？如果有遗漏或多算，指出来
- Q2: Per EC class 分层可行吗？test set 里每个 reaction 的 EC annotation 覆盖度多少？如果覆盖不全，怎么处理（丢弃 / 标 unknown / 合并到 "EC-unassigned"）
- Q3: 底物新颖性、enzyme 序列相似性两个分层维度，冻结数据里有没有现成的标签或工具能直接用？如果没有，就走 2.3 的"尽力做"路径，做不了就 N/A 披露
- Q4: paired bootstrap 用 10000 轮沿用 P0 的口径，还是要重新讨论？统一意见

**本地审计通过标准**：

- 所有主表（1-4）填满，每个数字有出处
- 所有 CI 用 paired bootstrap 计算，代码可复现
- 图 3 类都生成，SVG 格式
- `audit_manifest.sha256` 完整
- 报告尾部"本地通过 / 提交审阅"，权限表述自觉

---

## 六、给学生的话

1. M2 已经通过。**M3 智能体搭建那块导师直接做**，学生这轮不碰。你手头的比较优势是训练数据一手掌握——直接投到论文写作准备上，价值更大
2. 本轮唯一目标：出一份论文级性能统计表，**能直接支撑论文 Results / Experiments 章节**
3. 交付节奏跟 D4 一样：先出前置澄清（回答 Q1-Q4）→ 导师裁定 → 开工 → 本地审计 → 提交审阅
4. 三条治理纪律（边界披露 / 表述不越界 / 权限自觉）继续沿用
5. 时间预算 4-5 天。做扎实比做多重要——分层分析里凡是数据不支撑的直接标 N/A，不硬凑

有问题随时问，没问题就开始出前置澄清。
