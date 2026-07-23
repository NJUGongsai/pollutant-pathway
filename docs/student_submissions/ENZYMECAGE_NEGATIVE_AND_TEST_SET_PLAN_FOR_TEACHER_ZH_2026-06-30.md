# EnzymeCAGE + LucaPCycle 负样本与测试集构建方案（给老师审核）

日期：2026-06-30

状态：仅供老师审核。当前不生成负样本、不创建 split、不训练模型。

## 1. 背景与边界

当前路线是：

```text
使用 EnzymeCAGE 源码
使用我们自己准备的数据资产
接入 LucaPCycle 特征
```

EnzymeCAGE 当前训练 loader 不会动态生成负样本，而是直接读取 CSV 中已有的 `Label`：

```text
Label=1：数据库已知 enzyme-reaction 正样本
Label=0：预先构建好的负样本
```

因此，我们必须在正式 P0/P1 之前，先有一个经过审核的负样本与
train/valid/test 构建方案。

## 2. 原始 EnzymeCAGE 数据包实测结果

我们已直接读取原始下载数据包中解压后的训练文件：

```text
F:\training\train.csv
F:\training\valid.csv
```

实测结果：

| split | rows | Label=1 | Label=0 | 正:负比例 | reaction groups |
|---|---:|---:|---:|---:|---:|
| train.csv | 1,445,915 | 243,890 | 1,202,025 | 1:4.9286 | 9,310 |
| valid.csv | 67,677 | 12,707 | 54,970 | 1:4.3260 | 314 |
| test.csv | 未找到 | - | - | - | - |

原始 train/valid overlap：

```text
reaction overlap = 0
pair overlap = 0
UID overlap = 47,097
```

解释：

```text
原始 EnzymeCAGE 更接近 reaction-group split；
不是 enzyme-holdout split；
默认 config 中 test_path=valid.csv，因此不能直接声称有独立 test。
```

每个 reaction 的负样本数量也有明显规律：

```text
train.csv 每个 reaction 至少 50 个负样本，median=50，max=2000
valid.csv 每个 reaction 至少 50 个负样本，median=50，max=2000
```

因此，如果我们要模仿当前公开数据包，训练负样本比例应优先采用约：

```text
1 positive : 5 negatives
```

早期稿中推算出的 `negative/positive≈1.8` 只能作为历史版本背景，不作为本轮主比例。

## 3. 推荐负样本构建策略

推荐使用 EnzymeCAGE-style reaction-grouped candidate table：

```text
固定 reaction，构建 candidate enzymes。
每个 reaction group 中保留数据库已知正酶，并加入具有竞争性的负酶。
```

负样本来源按优先级：

```text
1. similar-reaction negatives
2. homologous wrong-enzyme negatives
3. EC top-3-dissimilar negatives
4. filtered random fallback，仅在候选不足时使用
```

### 3.1 Similar-Reaction Negatives

这是最接近 GitHub updated Enzyme-405 的做法。

对每个目标 reaction：

```text
1. 找 top 10 最相似 reactions；
2. 取这些相似 reactions 的已知催化酶；
3. 去掉目标 reaction 的已知正酶；
4. 剩余 enzyme 作为目标 reaction 的 Label=0 候选。
```

### 3.2 Homologous Negatives

参考论文方法重构：

```text
对目标 reaction 的正酶，用 MMseqs2 找同源酶；
阈值：sequence identity >= 0.4；
去掉目标 reaction 的已知正酶；
剩余同源酶作为 hard negatives。
```

### 3.3 EC-Dissimilar Negatives

参考论文方法重构：

```text
选 EC 前三级与目标 reaction 正酶不同的酶；
去掉目标 reaction 的已知正酶；
作为功能差异较大的 negatives。
```

如果 homologous negatives 和 EC-dissimilar negatives 都可用，建议在这两个来源内部采用：

```text
homologous : EC-dissimilar = 2 : 1
```

## 4. 推荐采样比例

训练集建议：

```text
global target: 1 positive : 5 negatives
```

每个 reaction group 建议：

```text
target_negatives_per_reaction =
  min(2000, max(50, round(5 * n_positive_for_reaction)))
```

这样既接近原始 train.csv 的全局比例，也接近其 per-reaction 候选结构。

如果某些 reaction 候选不足：

```text
保留可用候选；
记录到 audit；
不要静默补成未经审计的随机负样本。
```

## 5. Split 与独立测试集方案

推荐主 split：

```text
split unit = CANO_RXN_SMILES
train/valid/test reaction overlap = 0
train/valid/test pair overlap = 0
UID overlap 可以允许，用于模仿原始 EnzymeCAGE；
如老师需要，可另设 enzyme-holdout test。
```

建议第一版：

```text
train reactions: 80%
valid reactions: 10%
test reactions: 10%
random seed: 42
```

注意：

```text
必须创建真实 test.csv；
不能再使用 valid.csv 作为 test_path；
否则不能报告独立 test_auc。
```

## 6. 输出文件与审计

构建完成后应输出 frozen candidate table，所有实验共用完全相同 rows：

```text
E0
E6
E7
E9
E9-dim-ctrl
```

必需列：

```text
CANO_RXN_SMILES
UniprotID
sequence
Label
```

建议保留审计列：

```text
candidate_source
negative_type
source_reaction_id
source_positive_uniprot_id
seq_identity
reaction_similarity
rank_within_source
split
random_seed
```

必须输出审计报告：

```text
Label counts by split
reaction group counts by split
per-reaction positive/negative count distribution
feature coverage after filtering
reaction overlap across splits
pair overlap across splits
UID overlap across splits
duplicate pair/key audit
valid_equals_test=false
```

## 7. 指标适配

每个 valid/test reaction group 必须满足：

```text
n_pos >= 1
n_neg >= 1
```

为了 MRR@10 更有意义，优先保持：

```text
n_neg >= 50 where feasible
```

老师要求的指标：

```text
val_auc
test_auc
MRR@10
val_loss
test_loss
```

MRR@10 定义保持老师批准版本：

```text
每个 reaction group 内按 sigmoid score 降序排序；
找到第一个正样本 enzyme 的 rank；
rank <= 10 时贡献 1/rank；
rank > 10 时贡献 0；
最后对 reaction groups 求平均。
```

## 8. 请求老师确认

请老师确认以下点：

```text
1. 是否批准我们在单独的数据准备阶段构建 Label=0 负样本？
2. 是否同意负样本来源优先级：
   similar-reaction negatives > homologous negatives > EC top-3-dissimilar negatives；
   filtered random 仅作为候选不足时的 fallback？
3. 是否同意训练集采用原始数据包实测比例，约 1 positive : 5 negatives？
4. 是否同意 per-reaction 负样本数量尽量模仿原始数据：
   min 50 where feasible，max 2000？
5. 是否同意第一版 test 使用 reaction-group internal holdout，
   同时后续审计 temporal/external test 可行性？
6. 是否同意第一版允许 UID overlap，以模仿原始 EnzymeCAGE；
   enzyme-holdout 作为额外测试集而不是主 split？
```

老师批准前，不执行负样本构建、不创建 split、不进入 P1/P2/P3。
