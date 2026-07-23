# EnzymeCAGE P0/P1/P2 最终结果与老师要求闭环报告

日期：2026-07-14

状态：P0/P1/P2 科学任务及可恢复证据已完成；原 7 次训练的部分历史资源字段按实际记录为 N/A；等待老师确认 P3 与 v1 冻结

黄老师您好，

按照您 2026-07-13 的回复，我们已完成晨羽环境确认、原 7 个模型备份、
P0 的 ESM-C 600M seeds 42/43/44、P1 的 ESM-2 3B seed40 半学习率消融，
以及 P2 的 ESM-C 600M 校正 pocket seed40 严格对照。本次没有直接采用
远端任务自报的 `PASS`，而是对配置、日志、checkpoint、逐行预测、指标、
校验和、tar 和外部 identity 做了本地独立复核。

## 一、最终审计结论

```text
P0 科学与汇报要求                 已完成
P1 科学与汇报要求                 已完成（含逐 epoch valid/test loss）
P2 科学与汇报要求                 已完成
晨羽启动前环境与备份要求           已完成
P3                               未启动，符合先完成 P0/P1/P2 再决定的要求
原 7 个历史资源字段                可恢复项已报告；未采集项如实 N/A
额外 P0/P1/P2 训练或推理            不需要
```

没有发现仍需补跑的 P0/P1/P2 科学任务，也没有发现配置漂移、指标漏交或
错误地把缺失证据当作通过的情况。唯一不能写成“已实测”的内容，是原 7 次
正式训练当时没有连续采集的逐任务 peak VRAM/RSS，以及拆分后的 valid/test
累计评估耗时。这些历史值无法事后还原，本报告按 `N/A` 披露，不以新任务
或重放推理的数据冒充。

## 二、老师要求逐项对账

| 编号 | 老师要求 | 最终状态 | 完成证据或边界 |
|---|---|---|---|
| R1 | 后续训练全部在晨羽执行 | 完成 | P0/P1/P2 均在晨羽路径与设备运行 |
| R2 | P0/P1/P2 前备份原 7 个 checkpoint | 完成 | 本地 D 盘 7/7 seeds、182 文件、10,581,103,041 bytes；42 个关键文件远端/本地 SHA256 一致 |
| R3 | 明确备份位置、期限与自动清理风险 | 完成 | 晨羽外本地副本；禁止自动清理；老师验收、v1 冻结和长期归档前不得删除 |
| R4 | 确认 8 卡 48 GB 实例 | 完成 | 8 张卡，每卡 49,140 MiB；每任务独占 1 卡 |
| R5 | 冻结环境依赖 | 完成 | pip freeze 与 Python/PyTorch/CUDA/cuDNN/PyG/torch_cluster/NumPy 已归档 |
| R6 | 固化 radius_graph 修复 | 完成 | 执行源与 torch_cluster 路径已固定并审计 |
| R7 | 补结构化训练耗时与设备详情 | 按证据闭环 | 原 7 个可恢复耗时已列出；历史未采集 peak/eval 分段保持 N/A；新 5 个任务均有完整日志实测 |
| R8 | P0 补 600M seeds 42/43/44，除 seed 外不变 | 完成 | 三个任务均自然完成 20 epochs |
| R9 | P0 输出 600M 五 seed AUC/MRR/gap 与 5v5 ensemble | 完成 | prediction rows 独立复算 |
| R10 | P0 做 3B-vs-600M paired reaction bootstrap | 完成 | 450 个共同 reaction，10,000 次 bootstrap |
| R11 | P1 lr 减半、30 epochs、patience=5 | 完成 | lr=0.00015；best=4；epoch 9 正常 early stop |
| R12 | P1 输出 AUC/MRR/Hit 与 best/stop epoch | 完成 | 指标与 prediction rows 独立复算 |
| R13 | P1 输出 valid/test loss 曲线 | 完成 | 对 epoch 0-9 checkpoint 逐个只读评估；两条 stable-logit BCE 曲线已复核 |
| R14 | P2 使用排除 BOS/CLS 偏移的校正 pocket | 完成 | 107,705 UIDs、3,673,607 pocket rows、1,152 维、与 GVP 节点行对齐 |
| R15 | P2 除 pocket 外保持 600M seed40 不变 | 完成 | structured diff 仅有 checkpoint 目录与 pocket-node feature 路径 |
| R16 | P2 输出 AUC/MRR 并与原 seed40 比较 | 完成 | 20 epochs、best checkpoint、最终 predictions 与差值均已审计 |
| R17 | P0/P1/P2 完成前只给初步结论 | 完成 | 未提前冻结正式结论 |
| R18 | P0/P1/P2 后再决定 P3 | 完成 | P3 尚未启动，本报告提交最终证据供老师决定 |

您在晨羽专项确认一节写了“5 件事”，正文实际编号列出 4 项：checkpoint
备份、实例可用性、环境冻结、radius_graph 固化。上述 4 项均已完成；我们
没有自行虚构第五项。

## 三、P0：600M 补齐 5 seeds

三个新增任务完成情况：

| 任务 | Epochs | Best epoch | 总 wall-clock | 结束方式 |
|---|---:|---:|---:|---|
| 600M seed42 | 20（0-19） | 7 | 06:33:26.6 | 自然完成 |
| 600M seed43 | 20（0-19） | 5 | 06:29:16.6 | 自然完成 |
| 600M seed44 | 20（0-19） | 12 | 06:34:03.3 | 自然完成 |

平衡后的 5v5 结果：

| 指标 | ESM-2 3B（5 seeds） | ESM-C 600M（5 seeds） |
|---|---:|---:|
| 单 seed Test macro reaction AUC，mean +/- SD | 0.772850 +/- 0.004531 | **0.779464 +/- 0.005801** |
| 单 seed Test MRR@10，mean +/- SD | **0.483798 +/- 0.009027** | 0.478767 +/- 0.007670 |
| 五 seed ensemble macro AUC | 0.768580 | **0.779219** |
| 五 seed ensemble MRR@10 | **0.504294** | 0.493895 |
| 五 seed ensemble Hit@1 | **0.408889** | 0.391111 |
| 五 seed ensemble Hit@5 | **0.648889** | 0.644444 |
| 五 seed ensemble Hit@10 | 0.728889 | **0.737778** |

600M 五 seed 的 validation-test AUC gap 为：

```text
mean +/- SD = 0.010286 +/- 0.011138
range       = [-0.004552, 0.023149]
```

在 450 个共同可评估 test reaction 上进行 paired reaction bootstrap，差值
方向为 3B 减 600M：

| 指标 | 观察差值 | 95% CI | P(diff > 0) |
|---|---:|---:|---:|
| Macro reaction AUC | -0.010640 | [-0.027509, 0.006318] | 0.1059 |
| MRR@10 | +0.010399 | [-0.012245, 0.032860] | 0.8175 |

两项区间均跨 0。600M 的 AUC 点估计较高，3B 的 ensemble MRR@10 点估计
较高，但当前 5v5 证据不能证明任一模型族在相应指标上具有统计显著优势。

## 四、P1：3B seed40 半学习率消融

P1 严格执行：

```text
learning_rate          0.0003 -> 0.00015
maximum epochs         20 -> 30
early_stop_patience    5
实际 epochs            0-9
best / stop epoch      4 / 9
```

最终 best checkpoint 指标：

| 指标 | P1 half-lr | 原 3B seed40 | P1 - 原模型 |
|---|---:|---:|---:|
| Test macro reaction AUC | 0.777743 | 0.776618 | +0.001126 |
| Test MRR@10 | 0.471282 | 0.493596 | -0.022314 |
| Hit@1 | 0.371111 | 0.386667 | -0.015556 |
| Hit@5 | 0.615556 | 0.637778 | -0.022222 |
| Hit@10 | 0.717778 | 0.733333 | -0.015556 |

P1 AUC 位于老师预设的 `>= 0.780` 和 `< 0.775` 两个区间之间，因此应
归为 borderline：学习率减半带来约 0.0011 的 AUC 小幅改善，但没有追回
到 0.78，也不能归入“明确追不回来”的区间。排序指标反而下降，因此 P1
checkpoint 不适合替换原 3B seed40。

### P1 valid/test loss 曲线

原训练日志没有逐 epoch 记录 valid/test loss。我们没有将该缺失项当作
通过，而是利用保留的 epoch 0-9 checkpoints 做了逐个只读推理，并对每一
行 raw logit 独立复算。主曲线定义为 stable raw-logit BCE：

| Epoch | Valid BCE | Test BCE |
|---:|---:|---:|
| 0 | 1.0748863220 | 0.8393085599 |
| 1 | 1.2728700638 | 0.9135040641 |
| 2 | 1.5887944698 | 1.0972121954 |
| 3 | 1.7612895966 | 1.3038955927 |
| 4 | 1.7448091507 | 1.4019416571 |
| 5 | 1.8634941578 | 1.4012843370 |
| 6 | 1.8864446878 | 1.6369504929 |
| 7 | 2.0185129642 | 1.7090831995 |
| 8 | 2.0079929829 | 1.7308937311 |
| 9 | 2.1764726639 | 1.8999311924 |

10/10 epoch 的 valid/test 行数、标签、AUC 和 loss 均已独立交叉验证；
`best_model` 与 Epoch 4 在 tensor、prediction、metric 和 loss 上完全一致。
曲线显示 AUC 仍可改善时 BCE 校准已经恶化，后期过拟合趋势明显；best
checkpoint 仍按老师指定的 validation macro reaction AUC，而不是 loss 选择。

## 五、P2：600M 校正 pocket 严格对照

P2 完成 20 epochs（0-19），best epoch 为 6，总运行 06:30:07.6。配置
逐项比较只出现两个预期差异：独立 checkpoint 目录，以及校正后的
`esm_node_feature` 路径；seed、lr、batch、epoch、split、mean ESM、GVP、
DRFP、reaction-center、molecule、loss、optimizer 与指标逻辑均保持不变。

| 指标 | P2 校正 pocket | 原 600M seed40 | 差值 |
|---|---:|---:|---:|
| Valid macro reaction AUC | 0.776357 | 0.788442 | -0.012085 |
| Test macro reaction AUC | 0.763440 | 0.783831 | -0.020390 |
| Test MRR@10 | 0.468442 | 0.484294 | -0.015852 |
| Test Hit@1 | 0.371111 | 0.382222 | -0.011111 |
| Test Hit@5 | 0.608889 | 0.631111 | -0.022222 |
| Test Hit@10 | 0.708889 | 0.742222 | -0.033333 |

按老师给出的 test AUC 分级，P2 不属于任何正向信号区间：

```text
P2_NEGATIVE_SIGNAL_OUTSIDE_TEACHER_POSITIVE_BUCKETS
```

因此，在本次严格的 seed40 对照中，校正 pocket 没有给 600M 带来收益，
反而使 test AUC 下降约 0.0204、MRR@10 下降约 0.0159。该结论只针对这一
个严格单 seed 实验；不能外推成“校正 pocket 在任何模型或 seed 都无用”。

P2 也使“同 seed、同样使用校正 pocket”的 3B/600M 对照成为可能：

| 指标 | 原 3B seed40（校正 pocket） | P2 600M seed40（校正 pocket） | 3B - 600M |
|---|---:|---:|---:|
| Test macro reaction AUC | 0.776618 | 0.763440 | +0.013177 |
| Test MRR@10 | 0.493596 | 0.468442 | +0.025154 |
| Hit@1 | 0.386667 | 0.371111 | +0.015556 |
| Hit@5 | 0.637778 | 0.608889 | +0.028889 |
| Hit@10 | 0.733333 | 0.708889 | +0.024444 |

这个单 seed 的严格路线对照在 AUC 和排序指标上都支持 3B。但它只有一个
seed，不能替代 5v5 的模型族不确定性分析，也不能单独证明统计显著优势。

## 六、设备、环境与训练耗时

### 6.1 晨羽设备与软件环境

```text
平台实例/SKU             INSTANCE_TYPE_NOT_EXPOSED_BY_GUEST
nvidia-smi GPU 名称       NVIDIA nGPU-48GB
PyTorch CUDA GPU 名称     NVIDIA GeForce RTX 4090 D
GPU 架构                  Ada Lovelace
单卡显存                  49,140 MiB
可见 GPU                  8
单任务 GPU 数             1
驱动 / nvidia-smi CUDA    570.144 / 12.8
Python                    3.12.3
PyTorch / build CUDA      2.7.1+cu126 / 12.6
cuDNN                     9.5.1
torch_geometric           2.8.0
torch_cluster             1.6.3+pt27cu126
NumPy                     2.3.1
```

两个 GPU 名称来自同一批设备的不同接口，显存完全一致，故同时披露。晨羽
guest 没有暴露具体商业实例/SKU，本报告不猜测机型。

### 6.2 原 7 次正式训练的可恢复耗时

| 模型 | Seed | 总 wall-clock | 平均 full epoch | Best epoch | 到 best 累计 | 历史 peak VRAM/RSS | valid/test 累计评估 |
|---|---:|---:|---:|---:|---:|---|---|
| 3B | 40 | 07:14:33 | 21.10 min | 10 | 04:02:51 | N/A | N/A |
| 3B | 41 | 07:06:30 | 21.16 min | 8 | 04:15:46 | N/A | N/A |
| 3B | 42 | 07:06:43 | 21.17 min | 5 | 02:09:10 | N/A | N/A |
| 3B | 43 | 07:06:35 | 21.15 min | 8 | 03:13:18 | N/A | N/A |
| 3B | 44 | 07:13:01 | 21.48 min | 8 | 03:15:34 | N/A | N/A |
| 600M | 40 | 06:39:37 | 19.80 min | 12 | 04:19:25 | N/A | N/A |
| 600M | 41 | 06:37:38 | 19.75 min | 10 | 03:38:45 | N/A | N/A |

`N/A` 的原因是原 7 次训练当时没有全程连续逐任务 VRAM/RSS 监控，也没有
把 valid/test 评估分别计时。现有 nvidia-smi 快照不能代表全程峰值；重新
推理只能产生新的重放耗时，不能恢复历史实测值。因此不补造、不冒充。

### 6.3 本轮 P0/P1/P2 的完整日志实测

| 任务 | 总 wall-clock | 平均 epoch | 到 best | valid/test/final eval | Eval 占比 | Peak CUDA alloc/reserved | Peak RSS |
|---|---:|---:|---:|---:|---:|---:|---:|
| P0 600M s42 | 06:33:26.6 | 19.4629 min | 2.6210 h | 1921.1 / 1735.3 / 183.9 s | 16.27% | 14.30 / 46.88 GiB | 50.0354 GiB |
| P0 600M s43 | 06:29:16.6 | 19.2567 min | 1.9396 h | 1898.6 / 1715.4 / 181.6 s | 16.25% | 14.01 / 46.84 GiB | 50.1141 GiB |
| P0 600M s44 | 06:34:03.3 | 19.4957 min | 4.2582 h | 1911.4 / 1731.7 / 182.0 s | 16.18% | 14.29 / 46.83 GiB | 50.1146 GiB |
| P1 3B s40 | 03:34:16.1 | 20.9767 min | 1.7637 h | 1033.2 / 935.6 / 197.9 s | 16.85% | 14.54 / 45.57 GiB | 56.5568 GiB |
| P2 600M s40 | 06:30:07.6 | 19.3023 min | 2.2791 h | 1907.4 / 1724.7 / 183.6 s | 16.30% | 14.17 / 46.90 GiB | 38.1631 GiB |

P0/P1 的单独 nvidia-smi monitor 开始晚于任务启动，因此只作为部分时间窗
观察；表中的 CUDA 与 RSS 峰值来自完整训练日志。P2 同样使用完整日志中的
逐 epoch 内存记录。

## 七、备份与交付完整性

原 7 个模型的独立保留副本位于：

```text
Windows  D:\enzymecage\enzymecage_runs
WSL      /mnt/d/enzymecage/enzymecage_runs
```

当前保留策略为：禁止晨羽自动清理影响本地副本；在老师验收最终报告、v1
模型冻结和长期项目归档完成前，不得删除、覆盖、移动或去重；之后长期保留
best model、配置、预测、指标、manifest 与最终报告。

P1 最终 loss 包和 P2 最终结果包均完成目录、checksum、tar 和外部 identity
独立核验：

```text
P1 F2A1：63 files，62/62 payload checksums，tar/directory 一致
P2 G1A： 78 files，77/77 payload checksums，tar/directory 一致
```

## 八、最终科学结论与 P3 建议

本轮证据不支持“3B 全面优于 600M”或“600M 全面优于 3B”：

1. 600M 五 seed ensemble 的 macro reaction AUC 点估计更高：
   `0.779219` vs `0.768580`。
2. 原 3B 五 seed ensemble 的 MRR@10 点估计更高：
   `0.504294` vs `0.493895`。
3. 两个 paired-bootstrap 95% CI 都跨 0，模型族差异没有达到统计上明确的
   单一胜者结论。
4. 同 seed、同校正 pocket 的 P2 严格对照在 AUC 与 MRR 上都支持 3B，
   但只有一个 seed，不能替代 5v5 统计。
5. P1 只把 3B seed40 AUC 提高约 0.0011，同时降低 MRR/Hit，不能证明
   “3B 只是欠训练”，也不应替换原 3B seed40。
6. P2 校正 pocket 对原 600M seed40 是负向结果，不应作为 v1 候选模型。

若 v1 的主要应用仍是候选酶检索，原 3B 五 seed ensemble 仍是合理候选，
因为它具有当前最高的 ensemble MRR@10；600M 五 seed ensemble 应继续作为
AUC 更高的正式基线共同报告。这是按应用目标做的选择，不是模型族全面胜负。

根据您给出的规则，当 3B/600M 没有明确拉开时，P3 的优先级应降低。我们
建议当前**不自动启动 P3**，先请老师确认以下两项：

```text
1. 是否按候选酶检索目标冻结原 3B 五 seed ensemble 为 v1，
   同时保留 600M 五 seed ensemble 为 AUC baseline；
2. P3 Luca M2 fusion 是降级后继续探索，还是暂缓到后续需求明确时再做。
```

P0/P1/P2 本身不需要进一步训练、补推理或重新打包。

## 九、主要证据位置

```text
老师要求原文：
00_Authority_Teacher_Plan/
TEACHER_REPLY_ENZYMECAGE_ESM2_3B_VS_ESMC600M_FORMAL_TRAINING_REVIEW_2026-07-13.md

P0/P1 与 5v5：
03_HPC_Returned_Result_Summaries/
t3_5f_p0_p1_completion_5v5_metrics_timing_backup_20260714/

P1 loss 最终纠正包：
03_HPC_Returned_Result_Summaries/
t3_5f2a1_p1_loss_evidence_provenance_final_correction_20260714/

P2 最终验收包：
03_HPC_Returned_Result_Summaries/
t3_5g1a_p2_evidence_validator_delivery_final_correction_20260714/

最终逐项闭环审计：
04_Local_Review_Audits/
ENZYMECAGE_TEACHER_P0_P1_P2_FINAL_REQUIREMENT_CLOSURE_AUDIT_2026-07-14.md

P1 独立审计：
04_Local_Review_Audits/
ENZYMECAGE_T3_5F2A1_P1_LOSS_EVIDENCE_FINAL_CORRECTION_LOCAL_AUDIT_2026-07-14.md

P2 独立审计：
04_Local_Review_Audits/
ENZYMECAGE_T3_5G1A_P2_EVIDENCE_VALIDATOR_DELIVERY_LOCAL_AUDIT_2026-07-14.md
```
