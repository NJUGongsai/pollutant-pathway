# EnzymeCAGE ESM-2 3B 全量特征提取与适配说明

Date: 2026-07-06

## 1. 本次汇报目的

本轮工作的目标是把 EnzymeCAGE 原先使用的 ESM-C/600M 类特征替换为
ESM-2 3B 特征，并保证后续训练仍然能拿到 EnzymeCAGE 所需要的两类
蛋白特征：

```text
1. 序列级 ESM 向量
   protein_level/seq2feature.pkl
   key = protein sequence
   value shape = [2560]

2. 口袋节点级 ESM 特征
   pocket_node_feature/esm_node_feature.pt
   key = UniprotID
   value shape = [N_pocket, 2560]
```

本报告说明：

```text
1. 为什么没有继续使用 LucaCycle 的 M1/M2/concat 特征；
2. 原 EnzymeCAGE ESM 特征流程是什么；
3. 本次 ESM-2 3B 全量提取具体怎么做；
4. 为什么本次 pocket 坐标策略与旧 EnzymeCAGE 严格复现不完全一致；
5. 目前全量提取结果和审计结论；
6. 后续训练代码还需要怎样适配。
```

## 2. 当前结论

ESM-2 3B 全量特征已经在 HPC 上生成完成，并通过了本地返回包审计。

HPC 返回状态：

```text
T3_1_PASS_FULL_ESM2_3B_FEATURES_READY
```

最终特征规模：

```text
最终 UID 数 = 107705
序列级 seq2feature 数 = 87733 条唯一序列
pocket_node_feature 数 = 107705 个 UID
ESM 维度 = 2560
worker 数 = 20
worker 失败数 = 0
最终 validation failure = 0
```

特殊 UID 处理：

```text
Q0CJ57: 已通过特殊 offset 证据恢复，保留
Q0CJ62: AlphaFill-gap pocket-only 比对存在多解，无法唯一证明映射，排除
```

最终 HPC 输出位置：

```text
/public/home/acfbwjsi7s/enzymecage_lucapcycle_adapter_data_2026-06-30/esm2_3b_full_run_20260705/feature/protein/ESM2_3B_corrected_107705/protein_level/seq2feature.pkl

/public/home/acfbwjsi7s/enzymecage_lucapcycle_adapter_data_2026-06-30/esm2_3b_full_run_20260705/feature/protein/ESM2_3B_corrected_107705/pocket_node_feature/esm_node_feature.pt

/public/home/acfbwjsi7s/enzymecage_lucapcycle_adapter_data_2026-06-30/esm2_3b_full_run_20260705/feature/protein/ESM2_3B_corrected_107705/metadata
```

报告大小：

```text
seq2feature.pkl = 889.1 MB
esm_node_feature.pt = 35880.1 MB
```

重要边界：

```text
全量 ESM-2 3B 特征已经生成完成。
但还不能直接启动最终训练。
训练前仍需完成：
  1. 35GB 本体文件的 loader 兼容性审计；
  2. EnzymeCAGE 源码维度适配；
  3. tiny loader/model dry-run。
```

## 3. 为什么没有继续使用 LucaCycle 特征

最开始我们考虑过用 LucaCycle 的特征替代 EnzymeCAGE 里的 ESM 特征。
后续审计后停止了这条路线。

主要原因：

```text
EnzymeCAGE 不只需要一个蛋白整体向量。
它还需要 pocket/node-level 的残基级 ESM 特征。
```

LucaCycle 侧的 M1 是 pooled 后的 2560 维向量，已经不是逐残基矩阵，
不能恢复 EnzymeCAGE 所需的 pocket residue feature。

因此当前路线改为：

```text
不使用 LucaCycle M1/M2/concat_pooled_vec。
直接使用标准 ESM-2 3B 模型重新生成 EnzymeCAGE 所需的序列级和口袋级特征。
```

## 4. 原 EnzymeCAGE 的 ESM 特征流程

原 EnzymeCAGE 流程大致分为三层：

```text
1. 对整条蛋白序列跑 ESM，得到 sequence node matrix；
2. 对 sequence node matrix 做 mean pooling，得到 seq2feature.pkl；
3. 根据 pocket 信息，从 sequence node matrix 中切出 pocket_node_feature。
```

原代码中的目标路径形式是：

```text
feature/protein/<ESM_MODEL>/node_level/
feature/protein/<ESM_MODEL>/protein_level/seq2feature.pkl
feature/protein/<ESM_MODEL>/pocket_node_feature/esm_node_feature.pt
```

训练真正用到的是：

```text
protein_level/seq2feature.pkl
pocket_node_feature/esm_node_feature.pt
```

`node_level/` 主要是中间矩阵，不是最终训练必须直接读取的文件。

在旧资产中，ESM-C 的 sequence node matrix 实际是：

```text
[L+2, 1152]
```

也就是包含：

```text
node[0]     = BOS/CLS
node[1..L]  = 真实氨基酸残基
node[L+1]   = EOS
```

旧的 `seq2feature.pkl` 经 T1-E 审计确认，是对全部 `L+2` 行做 mean，
不是只对 `L` 个真实残基做 mean。

## 5. 旧 pocket 特征里发现的问题

我们为了避免再次生成“看起来有文件但不能用”的结果，对 pocket 坐标做了专门审计。

关键发现是：

```text
如果严格复现旧 ESM-C pocket 行号，旧 pocket 特征会系统性包含 BOS/CLS。
```

T1-F 在 5 个样本上看到：

```text
每个样本的 old-compatible pocket 行号都会选中 1 个 BOS/CLS token。
```

T3-0 和 T3-0B 后续扩大验证后，进一步说明：

```text
旧 strict-compatible/golden 坐标本质上是把 residue-style 0-based index
直接用于未裁剪的 [L+2] 矩阵。

因此 index 0 会选到 BOS/CLS，而不是真实第 1 个残基。
```

这就形成了一个选择：

```text
方案 A：严格复现旧 EnzymeCAGE pocket 行号
       优点是与旧资产完全兼容；
       缺点是会继续保留 pocket 里包含 BOS/CLS 的系统性问题。

方案 B：使用经过氨基酸一致性验证的真实 pocket 残基坐标
       优点是 pocket 特征只包含真实口袋残基；
       缺点是与旧 ESM-C pocket 特征不再逐行复现。
```

我们最终采用方案 B：

```text
序列级 mean pooling 保持旧 EnzymeCAGE 行为：仍对 [L+2] 做 mean。
pocket 特征采用校正后的真实残基坐标：只切 node[1..L]，不切 BOS/EOS。
```

## 6. 本次 ESM-2 3B 全量提取怎么做

### 6.1 模型和表示层

本次使用标准 ESM-2 3B：

```text
model = esm2_t36_3B_UR50D
repr_layer = 36
embedding_dim = 2560
```

没有使用：

```text
Luca pooling
Luca M1
Luca M2
concat/fusion feature
旧 ESM-C 模型输出
```

### 6.2 输入范围

初始需要覆盖的 UID 宇宙：

```text
107706 个 UID
```

经过 pocket 坐标审计后：

```text
107704 个 UID 直接通过 AA 验证；
Q0CJ57 通过唯一 offset=68 证据恢复；
Q0CJ62 因 pocket-only alignment 多解，无法唯一证明，排除；
最终提取 UID = 107705。
```

### 6.3 pocket 坐标生成

我们先生成 `final_corrected_pocket_indices.pkl`，作为全量提取的依据。

该文件保存的是未裁剪 ESM 坐标：

```text
node_untrimmed[0] = BOS/CLS
node_untrimmed[1..L] = 真实残基
node_untrimmed[L+1] = EOS
```

pocket index 必须满足：

```text
1 <= pocket_index <= L
```

这保证：

```text
pocket 不会切到 BOS/CLS，也不会切到 EOS。
```

全量 manifest 审计结果：

```text
final_corrected_pocket_indices.pkl records = 107705
BOS index 0 selected = 0
EOS index L+1 selected = 0
empty index lists = 0
out-of-range indices = 0
duplicate indices within UID = 0
corrected_count min = 1
corrected_count max = 155
```

### 6.4 GPU 提取流程

全量提取使用 20 个 GPU array worker。

每个 worker 的逻辑是：

```text
1. 加载 ESM-2 3B 模型；
2. 读取自己负责的一批 UID；
3. 对每条唯一 sequence 跑 ESM-2 3B；
4. 得到 node_untrimmed，shape = [L+2, 2560]；
5. seq2feature[sequence] = mean(node_untrimmed over all L+2 rows)；
6. pocket_node_feature[UID] = node_untrimmed[final_corrected_pocket_indices[UID]]；
7. 立即丢弃完整 node_untrimmed，不保存完整矩阵；
8. 保存 worker 分片；
9. merge job 合并成最终两个训练入口文件。
```

### 6.5 存储策略

因为全量完整 node matrix 会占用大量空间，本次没有保存：

```text
node_level/{UID}.npz
每个 UID 的完整 [L+2,2560] 矩阵
```

只保存训练真正需要的两个结果：

```text
protein_level/seq2feature.pkl
pocket_node_feature/esm_node_feature.pt
```

这样做的原因：

```text
1. 训练阶段不直接需要完整 sequence node matrix；
2. 35GB pocket 特征已经是主要训练输入之一；
3. 保存所有完整 [L+2,2560] 矩阵会显著增加 HPC 存储压力；
4. 先前旧 ESM-C 原始矩阵已经造成约百 GB 级别空间压力。
```

## 7. 本次输出和旧 EnzymeCAGE 的差异

### 7.1 模型不同

旧资产：

```text
ESM-C_600M
dim = 1152
```

新资产：

```text
ESM-2 3B
dim = 2560
```

### 7.2 pocket 坐标策略不同

旧 strict-compatible pocket 行号：

```text
会包含 BOS/CLS。
```

新 corrected pocket 行号：

```text
只包含真实 pocket 残基。
BOS/EOS 均不进入 pocket_node_feature。
```

这是本次与旧 EnzymeCAGE 最重要的语义差异。

### 7.3 不保存完整 node_level 中间矩阵

旧流程通常会保留：

```text
node_level/{UID}.npz
```

本次不保存该中间层，只保留最终训练需要的文件。

### 7.4 排除 1 个无法唯一证明的 UID

本次排除：

```text
Q0CJ62
```

原因：

```text
AlphaFill-gap pocket-only 结构无法唯一映射回全序列；
比对产生大量同等可行解；
为避免把不确定 pocket 残基错误送入训练，选择排除。
```

## 8. 全量提取审计结果

T3-1 本地审计确认：

```text
20 个 worker audit JSON: 全部 WORKER_PASS
20 个 worker count CSV: 107705 行 PASS，0 行 FAIL
final_feature_counts.csv: 107705 行
feature shape mismatch: 0
final_validation_failures.csv: 0 行
seq2feature_sequence_conflicts.csv: 0 行
return package sha256: 全部 OK
日志中无 Traceback / OOM / killed / CUDA out-of-memory
```

最终 shape：

```text
seq2feature value shape = [2560]
pocket_node_feature value shape = [N_pocket,2560]
N_pocket min = 1
N_pocket max = 155
```

重复 sequence 的处理：

```text
同一条 sequence 可能出现在多个 worker 分片中。
最终 exact duplicate difference 计数为 7452，但 tolerance conflict = 0。
也就是说这些差异没有超过 float32 容差，不作为阻塞。
```

## 9. 当前还需要补做的 35GB 本体审计

本地返回包没有包含最终 35GB `esm_node_feature.pt` 本体，因此我们又准备了
T3-1B 审计提示词，用于在 HPC 上直接检查最终大文件。

T3-1B 要确认：

```text
1. 35GB esm_node_feature.pt 文件存在且完整；
2. 889MB seq2feature.pkl 文件存在且完整；
3. 当前 EnzymeCAGE loader 能否直接读取 esm_node_feature.pt；
4. UID 数是否为 107705；
5. Q0CJ57 是否存在，Q0CJ62 是否排除；
6. shape 是否全部符合 [N_pocket,2560]；
7. 是否没有偷偷保存完整 node_level 矩阵。
```

需要特别注意：

```text
T3-1 脚本中 esm_node_feature.pt 是 pickle 写出的 dict。
当前 EnzymeCAGE loader 主要通过 torch.load 读取。
因此必须实测 loader 兼容性。
```

如果 T3-1B 发现 loader 不兼容，有两种处理：

```text
1. 在源码适配阶段修 loader，使其同时支持 pickle dict；
2. 或在 HPC 上把 esm_node_feature.pt 重存为 torch.save 格式。
```

## 10. 后续训练代码为什么必须修改

即使特征文件已经生成，原 EnzymeCAGE 训练代码仍不能直接训练。

原因一：ESM 维度变了。

```text
旧 ESM-C dim = 1152
新 ESM-2 3B dim = 2560
```

模型里与 ESM 相关的层输入维度需要变为 2560，否则 forward 时维度会不匹配。

原因二：配置需要指向新资产。

需要新建 ESM-2 3B 配置，而不是覆盖旧配置：

```text
esm_model = esm2_t36_3B_UR50D
esm_mean_feature = .../ESM2_3B_corrected_107705/protein_level/seq2feature.pkl
esm_node_feature = .../ESM2_3B_corrected_107705/pocket_node_feature/esm_node_feature.pt
pretrain_model = null
```

原因三：不能加载旧 ESM-C checkpoint。

旧 checkpoint 中 ESM 相关层是 1152 维，新模型是 2560 维，不能直接 strict load。

原因四：需要处理 Q0CJ62。

训练 split 或数据加载时需要明确：

```text
Q0CJ62 没有 ESM-2 3B corrected pocket feature。
相关训练/验证/测试行应过滤或记录排除。
```

原因五：需要增加早期验证。

训练启动前必须检查：

```text
所有使用到的 UID 都在 pocket_node_feature 中；
所有使用到的 sequence 都在 seq2feature 中；
seq2feature shape = [2560]；
pocket_node_feature shape = [N,2560]；
GVP pocket node 数与 ESM pocket node 数一致；
没有 silent zero-vector fallback。
```

## 11. 建议给老师审核的决策点

建议请老师确认以下事项：

```text
1. 是否接受 pocket 特征采用 corrected biological coordinate，
   而不是严格复现旧 ESM-C 中包含 BOS/CLS 的 pocket 行号。

2. 是否接受排除 Q0CJ62，
   原因是 AlphaFill-gap pocket-only 映射无法唯一证明。

3. 是否接受全量提取不保存完整 node_level 中间矩阵，
   只保留训练需要的 seq2feature.pkl 和 esm_node_feature.pt。

4. 是否同意在训练前继续执行：
   T3-1B 35GB 本体 loader 审计；
   EnzymeCAGE 2560 维源码适配；
   tiny loader/model dry-run。
```

## 12. 相关证据文件

本地审计报告：

```text
04_Local_Review_Audits/P0_ESM3B_T1F_UNTRIMMED_TOKEN_IDENTITY_LOCAL_REVIEW_2026-07-04.md
04_Local_Review_Audits/ESM3B_T3_0B_POCKET_COORDINATE_DECISION_LOCAL_REVIEW_2026-07-06.md
04_Local_Review_Audits/ESM3B_T3_0C_FULL_CORRECTED_POCKET_INDEX_LOCAL_REVIEW_2026-07-06.md
04_Local_Review_Audits/ESM3B_T3_0D_FINAL_CORRECTED_MANIFEST_LOCAL_REVIEW_2026-07-06.md
04_Local_Review_Audits/ESM3B_T3_1_FULL_EXTRACTION_LOCAL_REVIEW_2026-07-06.md
```

HPC 返回包：

```text
03_HPC_Returned_Result_Summaries/t3_0b_pocket_coordinate_decision_audit
03_HPC_Returned_Result_Summaries/t3_0c_full_corrected_pocket_index
03_HPC_Returned_Result_Summaries/t3_0c3_alphafill_mapping_evidence
03_HPC_Returned_Result_Summaries/t3_0d_final_corrected_manifest
03_HPC_Returned_Result_Summaries/t3_1_full_esm2_3b_extraction
```

后续 35GB 本体审计提示词：

```text
07_HPC_Prompts/HPC_ENZYMECAGE_ESM3B_T3_1B_FINAL_ARTIFACT_BODY_AUDIT_PROMPT_2026-07-06.md
```

## 13. 当前状态

```text
ESM-2 3B 全量特征提取：已完成
全量特征摘要审计：已通过
35GB 本体 loader 审计：待执行
EnzymeCAGE 训练源码适配：待执行
tiny dry-run：待执行
正式训练：尚未开始
```
