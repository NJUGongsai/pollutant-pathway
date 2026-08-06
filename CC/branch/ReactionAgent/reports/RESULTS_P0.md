# P0 诚实评估结果报告

**日期**: 2026-07-28
**范围**: 阶段 0–1（诚实 benchmark 基线）
**语料**: 晨羽反应集（`data/rxn2enzyme_positives.pkl` + `feature/reaction/reacting_center` + `feature/reaction/drfp`）
**评估脚本**: `benchmark/honest_eval.py`（入口 `benchmark/run_p0.py`），结果落盘 `reports/p0_{random,scaffold,reaction_family}.json`

---

## 0. 一句话结论

在**去 oracle、防泄漏、全 X 进分母**的诚实设定下，当前"检索相似反应 → 迁移反应模板 → 酶集打分"的方法：

- **随机/scaffold 划分** top1 ≈ 12%、top5 ≈ 18%；
- **reaction-family 划分**（真正外推到未见转化家族）**断崖跌到 top1 3.6% / top5 7.1%**；
- 三划分**唯一且一致的瓶颈是"生成召回"**：≥72% 的测试反应连真产物都生成不出来（`not_generated`），而**一旦生成出来打分环节很强**（generated_true 139 → top5 130，≈94% 被排进前 5）。

这直接为 v3 设计（位点驱动神经-符号）定了靶：**要提升的不是打分，而是"能否生成到正确产物"的召回**。

---

## 1. 相对旧脚本修正的四类作弊

`honest_eval.py` 对旧 `verify_substrate_retrieval.py` 的四处已确认缺陷逐一修正：

1. **去 oracle donor**：donor 选择只看底物相似度、固定取 top-K，绝不因"候选恰好含真产物"而改变选择或分母。
2. **不偷 held-out 共反应物**：反应左侧只放 X，不注入真实反应的 co-reactants。
3. **全 X 进分母**：分母 = 全部可解析测试反应，失败按类型计入。
4. **防酶家族泄漏**：donor 检索与打分参考族都剔除与测试反应**同 group**（同 canonical 转化对）的反应，而非仅精确串匹配。

> 关于 X→Y 的定义：语料 97% 是多底物/辅酶耦合反应，"最大片段=主底物"会误把 NADH/CoA 等辅酶当主底物。本轮采用**辅酶剥离 + 反应中心锚定**（`canonical_identity.transformed_pair`）——先剥离辅酶字典中的管道分子，再用反应中心锚定被转化的主 X→Y 对。98% 反应可据此定出 X→Y。

---

## 2. 三划分主结果

| split | N_test | top1 | top5 | top10 | **gen_recall** | 耗时 |
|---|---|---|---|---|---|---|
| random | 692 | 81 (11.7%) | 130 (18.8%) | 136 (19.7%) | 139 (**20.1%**) | 724s |
| scaffold | 702 | 84 (12.0%) | 126 (17.9%) | 130 (18.5%) | 132 (**18.8%**) | 221s |
| **reaction_family** | 742 | 27 (**3.6%**) | 53 (**7.1%**) | 55 (7.4%) | 56 (**7.5%**) | 109s |

`gen_recall = generated_true / N_test`（真产物被生成出来的比例，是命中的上限）。

---

## 3. 漏斗分解（全部以 N_test 为分母）

| split | parsable | has_donor | has_candidate | generated_true | → top5 |
|---|---|---|---|---|---|
| random | 692 | 692 | 639 | **139** | 130 |
| scaffold | 702 | 702 | 622 | **132** | 126 |
| reaction_family | 742 | 742 | 661 | **56** | 53 |

**读法**：

- `has_donor` = 100%：底物检索永远能找到 top-K 相似 donor（不是瓶颈）。
- `has_candidate` 高（90%+）：模板大多能在 X 上点火产出**某些**候选。
- **`generated_true` 塌陷**：产出的候选里含**正确** Y 的只有 8–20%——**这就是天花板**。
- `generated_true → top5` 几乎无损（139→130、132→126、56→53）：**打分器一旦拿到正确候选，基本能排进 top5**。

失败分型（outcomes）：

| split | not_generated | no_candidate | generated_but_ranked_low | hit |
|---|---|---|---|---|
| random | 500 | 53 | 3 | 136 |
| scaffold | 490 | 80 | 2 | 130 |
| reaction_family | 605 | 81 | 1 | 55 |

`generated_but_ranked_low` 全程个位数 → **排序不是问题，生成才是**。

---

## 4. Novelty 分桶（按 X 对最相似 train donor 的 Tanimoto 相似度）

**random**

| bin | n | top1 | top5 | top10 |
|---|---|---|---|---|
| ==1.0 | 354 | 9% | 16% | 18% |
| [0.8,1.0) | 60 | 22% | 35% | 35% |
| [0.6,0.8) | 118 | 18% | 28% | 28% |
| [0.4,0.6) | 119 | 11% | 12% | 12% |
| [0.0,0.4) | 41 | 7% | 10% | 10% |

**scaffold**

| bin | n | top1 | top5 | top10 |
|---|---|---|---|---|
| ==1.0 | 62 | 15% | 23% | 24% |
| [0.8,1.0) | 45 | 13% | 27% | 27% |
| [0.6,0.8) | 147 | 5% | 11% | 11% |
| [0.4,0.6) | 276 | 13% | 19% | 20% |
| [0.0,0.4) | 172 | 14% | 18% | 19% |

**reaction_family**

| bin | n | top1 | top5 | top10 |
|---|---|---|---|---|
| ==1.0 | 345 | **1%** | **8%** | 8% |
| [0.8,1.0) | 43 | 12% | 14% | 14% |
| [0.6,0.8) | 128 | 9% | 12% | 12% |
| [0.4,0.6) | 138 | 1% | 1% | 2% |
| [0.0,0.4) | 88 | 3% | 3% | 5% |

**关键观察**：reaction_family 的 `==1.0` 桶（底物与某 train 反应**完全相同**，n=345）top1 仅 **1%**。即"同底物 ≠ 同转化"——一旦禁止借用同一转化家族，即便底物一模一样也几乎打不中。这是当前方法**吃家族泄漏红利**最直接的证据。

---

## 5. 结论与对 v3 的启示

1. **诚实基线已建立**：random/scaffold top5 ≈ 18%，reaction_family top5 ≈ 7%。后续任何改进都以此为对照，且必须在 **reaction_family 划分**上证明外推能力，否则只是过拟合家族。

2. **主攻方向 = 生成召回，不是打分**：打分器（DRFP-酶集）在 generated_true 上近乎无损进 top5，继续调打分收益极小；≥72% 的失败发生在"生成不出正确 Y"。→ v3 的**位点驱动模型**应直接对准"预测/枚举正确的反应位点与编辑操作"，把 generated_true 从 ~20% 抬上去。

3. **模板迁移的机制缺陷**：单 donor 转化对模板在单个 X 上"点火但产错"或"点不着"是主因。→ 需要（a）位点级迁移（把 donor 的反应中心/编辑对齐到 X 的等价位点），（b）多 donor / 多模板集成扩大召回，（c）对 `no_candidate` 的畸形 SMARTS 做鲁棒化。

4. **数据现实**：97% 多底物/辅酶耦合、仅 3% 干净 1:1。辅酶剥离+中心锚定是本轮为定义 X→Y 做的必要工程，98% 反应可解析；剩余 2% 无法定出主转化对的反应计入 `unparsable`，后续可通过扩充辅酶字典与更鲁棒的中心锚定继续回收。

---

## 6. 复现

```bash
cd CC/branch/ReactionAgent
python3 benchmark/run_p0.py            # 三划分全量，结果写 reports/p0_*.json
P0_MAX_CASES=60 python3 benchmark/run_p0.py   # 快速冒烟（每划分前 60 例）
```

产物：`reports/p0_random.json`、`reports/p0_scaffold.json`、`reports/p0_reaction_family.json`、`reports/p0_all.json`。