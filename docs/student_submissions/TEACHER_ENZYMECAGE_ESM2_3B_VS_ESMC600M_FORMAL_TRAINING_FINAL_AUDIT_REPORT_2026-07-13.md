# EnzymeCAGE ESM-2 3B 与 ESM-C 600M 正式训练结果及审计报告

日期：2026-07-13

黄老师您好，

按照您 2026-07-10 提出的正式训练要求，我们已完成 ESM-2 3B 五个
随机种子与 ESM-C 600M 两个随机种子的全量训练，并对训练完成性、
模型文件、预测结果和最终指标进行了二次审计。本报告重点汇报正式
测试集结果、3B 过拟合情况以及两种模型的比较结论。

## 一、结论摘要

本轮正式训练已完整结束，7 个任务均自然完成 20 个 epoch：

```text
ESM-2 3B：seed 40、41、42、43、44，共 5 个任务
ESM-C 600M：seed 40、41，共 2 个 baseline 任务
```

两个模型在老师要求的两个主要测试指标上表现出明确的取舍：

| 模型 | Seed 数 | Test macro reaction AUC | Test MRR@10 | Test BCE |
|---|---:|---:|---:|---:|
| ESM-2 3B | 5 | 0.772850 +/- 0.004531 | **0.483798 +/- 0.009027** | **1.544309 +/- 0.144575** |
| ESM-C 600M | 2 | **0.780799 +/- 0.004288** | 0.478204 +/- 0.008612 | 1.747530 +/- 0.104024 |

主要结论如下：

1. ESM-C 600M 的单 seed 平均 test macro reaction AUC 高约 0.00795。
2. ESM-2 3B 的单 seed 平均 test MRR@10 高约 0.00559，测试 BCE 也更低。
3. 五个 3B 模型做概率平均后，ensemble MRR@10 达到 **0.504294**，
   高于两模型 600M ensemble 的 0.479611。
4. 3B 的平均 validation-test AUC gap 为 **0.007816**，明显低于您
   此前关注的约 0.05 阈值。5k pilot 中的明显过拟合没有在全量训练中
   延续。
5. 没有一个模型同时在 AUC 和排序指标上全面占优。若后续主要任务是
   从候选酶中把正确酶排到前面，建议采用 **ESM-2 3B 五模型
   ensemble**；若以 macro reaction AUC 为唯一主指标，则 600M 略优。

因此，本轮不建议表述为“3B 全面优于 600M”。更准确的结论是：

> ESM-2 3B 在全量数据下未表现出明显过拟合，并提升了候选酶排序
> 表现；ESM-C 600M 在单 seed 平均 macro reaction AUC 上仍有小幅优势。

## 二、实验范围与公平性控制

### 2.1 本轮比较对象

本轮使用原 EnzymeCAGE 训练框架，比较：

```text
ESM-2 3B：esm2_t36_3B_UR50D，特征维度 2560
ESM-C 600M baseline：ESM-C_600M，特征维度 1152
```

两条路线使用相同的模型任务、正式 train/valid/test pair rows、标签、
分子与结构特征、训练轮数和 batch size。主要变化是 ESM 特征来源、
维度及 3B 路线采用的校正后 pocket residue 索引。

本轮没有使用 Luca pooled M1/M2/concat 特征替换 ESM。EnzymeCAGE 除了
序列级向量，还要求 pocket residue-level ESM 节点矩阵，pooled Luca
向量不能直接替代这一输入。Luca pooled 特征未来仍可作为额外分支进行
fusion，但不属于 2026-07-10 批准的本轮正式 3B/600M 比较范围。本轮
结论因此属于 **ESM-2 3B 校正特征路线与 EnzymeCAGE ESM-C 600M
baseline 的比较**，不是 Luca fusion 实验，也不是只改变参数量的纯
模型规模对照。

### 2.2 正式数据

| Split | Pair rows | Positive | Negative | Reaction groups |
|---|---:|---:|---:|---:|
| Train | 623,854 | 109,129 | 514,725 | - |
| Valid | 79,563 | 14,156 | 65,407 | 450 |
| Test | 70,815 | 10,804 | 60,011 | 451 |

数据边界：

```text
train、valid、test 为互相独立的正式冻结 split
valid_path 与 test_path 不相同
两种模型使用完全相同的评估 pair rows 与 Label
Q0CJ62 已从正式 split 中排除，因此 3B/600M 比较行保持一致
```

### 2.3 训练设置

```text
num_epochs = 20
batch_size = 256
weight_col = null
pretrain_model = null
best checkpoint = 按 validation macro reaction AUC 选择
最终比较 = 使用独立 test AUC 与 test MRR@10，不按 validation 单独下结论
```

## 三、训练与审计过程

训练前完成了以下检查：

1. ESM-2 3B 全量序列级和 pocket 节点级特征生成及 UID/维度审计。
2. ESM-C 600M baseline 特征来源、维度和 loader 真实性复核。
3. EnzymeCAGE 对 1152/2560 维 ESM 输入的代码适配与 import 检查。
4. 十个 seed 配置的路径、数据和 checkpoint 目录审计。
5. 两模型各 seed 的真实 loader、forward、loss、backward tiny dry-run。
6. 迁移到晨羽后，对上传文件执行 SHA256、split 行数、特征对象和真实
   loader 审计。

晨羽环境中的 PyG 版本对 `torch_geometric.nn.radius_graph` 提出了
不可满足的 `pyg-lib>=0.6.0` 要求，因此两处调用改为直接从已安装且
通过测试的 `torch_cluster` 导入 `radius_graph`。该修改调用的是同一
底层图构建算子，不改变训练目标或模型算法。修复后 10/10 tiny
dry-run 均完成 GPU forward/backward，3B 和 600M 维度分别为 2560 与
1152。

正式训练在 8 张 48 GB GPU 实例上分阶段启动，使用 7 张 GPU 并行运行
7 个任务，保留 1 张 GPU。启动后单独进行了进程映射、日志增长、GPU
占用、内存和 swap 稳定性审计。全部任务最终自然结束，单任务运行时间
约 6.63 至 7.24 小时，总墙钟时间约 7.5 小时。

## 四、逐 Seed 正式结果

下表中的 AUC 均为 EnzymeCAGE 代码定义的 **macro reaction AUC**：先在
每个 reaction group 内计算 ROC AUC，再对可评估 reaction 取平均；不是
把全部 pair rows 混在一起计算的 global row AUC。

| 模型 | Seed | Best epoch | Valid AUC | Test AUC | Val-Test gap | Test MRR@10 | Test Hit@1 | Test Hit@5 | Test BCE |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| ESM-2 3B | 40 | 10 | 0.783339 | 0.776618 | 0.006722 | 0.493596 | 0.386667 | 0.637778 | 1.641672 |
| ESM-2 3B | 41 | 8 | 0.781116 | 0.765783 | 0.015333 | 0.482730 | 0.384444 | 0.611111 | 1.706835 |
| ESM-2 3B | 42 | 5 | 0.775803 | 0.772978 | 0.002825 | 0.471168 | 0.364444 | 0.628889 | 1.409422 |
| ESM-2 3B | 43 | 8 | 0.772289 | 0.776978 | -0.004689 | 0.491302 | 0.395556 | 0.626667 | 1.377629 |
| ESM-2 3B | 44 | 8 | 0.790781 | 0.771891 | 0.018890 | 0.480197 | 0.375556 | 0.617778 | 1.585986 |
| ESM-C 600M | 40 | 12 | 0.788442 | 0.783831 | 0.004611 | 0.484294 | 0.382222 | 0.631111 | 1.673974 |
| ESM-C 600M | 41 | 10 | 0.796834 | 0.777766 | 0.019068 | 0.472114 | 0.351111 | 0.635556 | 1.821086 |

两个共同 seed 的方向一致：

| Paired seed | 3B - 600M Test AUC | 3B - 600M Test MRR@10 |
|---:|---:|---:|
| 40 | -0.007213 | +0.009302 |
| 41 | -0.011983 | +0.010616 |

也就是说，在 seed 40 和 41 上都观察到相同取舍：600M 的 AUC 较高，
3B 的 MRR@10 较高。

## 五、Ensemble 结果

Ensemble 对同一 pair row 的不同 seed 预测概率取平均，再在每个 reaction
内重新排序。

| 模型 | Ensemble seed 数 | Test macro AUC | Test MRR@10 | Hit@1 | Hit@5 | Hit@10 |
|---|---:|---:|---:|---:|---:|---:|
| ESM-2 3B | 5 | 0.768580 | **0.504294** | **0.408889** | **0.648889** | **0.728889** |
| ESM-C 600M | 2 | **0.769938** | 0.479611 | 0.380000 | 0.620000 | 0.717778 |

对实际使用的解释为：

```text
3B ensemble Hit@1 = 0.408889：约 40.9% 的可评估反应中，排名第一的候选酶为正样本。
3B ensemble Hit@5 = 0.648889：约 64.9% 的可评估反应中，至少一个正样本进入前五。
3B ensemble MRR@10 = 0.504294：综合考虑正确酶在前十内的具体名次，3B 的排序优于 600M ensemble。
```

以相同的 450 个可评估 test reaction 做 paired reaction bootstrap，差值
方向定义为 3B 减 600M：

| 指标 | 观察差值 | 95% reaction-bootstrap CI | P(diff > 0) |
|---|---:|---:|---:|
| Macro reaction AUC | -0.001359 | [-0.018940, 0.016917] | 0.4348 |
| MRR@10 | +0.024683 | [0.000234, 0.049403] | 0.9762 |

固定 ensemble 在该测试集上的 AUC 差异无法区分；MRR@10 区间支持当前
3B ensemble 的排序优势。但该 bootstrap 只重采样 test reaction，未
包含重新训练不同 seed 的不确定性，因此不能单独作为“3B 模型族全面
优于 600M”的证明。

## 六、对老师此前问题的直接回答

### 6.1 全量数据是否缓解了 3B 过拟合？

是。5k pilot 中 3B 的 validation-test AUC gap 约为 0.12；正式五个
seed 的平均 gap 降至：

```text
0.007816 +/- 0.009508
```

五个 seed 的 gap 范围为 -0.004689 至 0.018890，均未接近此前约 0.05
的关注线。全量训练数据有效缓解了 pilot 阶段的过拟合现象。

### 6.2 哪个模型更好？

需要按下游目标回答：

```text
如果目标是每个反应内对候选酶进行排序：ESM-2 3B ensemble 更合适。
如果目标只看 macro reaction AUC：ESM-C 600M 略高。
```

考虑本项目最终需要从候选酶中检索并优先展示正确酶，且老师要求同时
报告 AUC 与 MRR@10，我们建议：

```text
后续主排序模型：ESM-2 3B 五 seed ensemble
对照基线：      ESM-C 600M
报告结论：      3B 改善排序，但未提高 macro reaction AUC
```

## 七、完成性与结果审计

7 个任务均满足：

```text
epoch_0.pth 至 epoch_19.pth 全部存在
best_model.pth 存在
valid/test metrics JSON 存在
valid/test prediction CSV 存在
日志包含自然完成的 Test 与 Valid evaluation 标记
无 Traceback、CUDA OOM、Killed、ImportError 或 RuntimeError
审计时 train.py 活跃进程数为 0
训练结束后 GPU 均已释放
```

返回的 SHA256 manifest 覆盖 42 个关键文件，包括配置、best model、
valid/test 指标 JSON 和预测 CSV，总计约 1.21 GiB。

本地二次审计独立复算了：

```text
各模型族的 seed mean 与 sample standard deviation
每个 seed 的 per-reaction macro AUC 均值
每个 seed 的 MRR@10 均值
valid/test reaction group 数量
```

复算结果与返回汇总一致，差异为 0 或约 1e-16 的浮点误差。

## 八、必须保留的结果边界

1. Test 共 451 个 reaction，其中一个 reaction 在冻结测试表中有 19 个
   候选但没有正样本，因此无法计算 per-reaction AUC 和 MRR。两模型、
   所有 seed 均排除同一个 reaction，最终有效 test reaction 为 450，
   不会造成模型间偏置。
2. Test 中有 87 个 reaction 的负候选少于 50 个，其中 86 个可评估。
   低候选组的 MRR 明显高于至少 50 个负候选的组，因此正式汇报时应
   保留候选数量对 MRR 的影响说明。
3. 3B 有五个 seed，600M baseline 只有两个 seed。这符合本轮老师要求，
   但 600M 的标准差只基于两个运行，不能视为平衡的 5-vs-5 比较。
4. 3B 路线同时包含 2560 维 ESM-2 3B 特征与校正后 pocket residue
   索引；600M 使用旧式 1152 维 baseline 特征。因此本轮比较反映的是
   两条完整特征路线，而非严格的“仅参数量变化”。

## 九、建议老师确认的下一步

建议将本轮结论冻结为：

> 全量数据已消除 3B pilot 中的明显 validation-test gap；3B 五模型
> ensemble 在候选酶排序指标上优于 600M baseline，但 600M 的单 seed
> 平均 macro reaction AUC 略高。后续若以候选酶检索为主要应用，采用
> 3B ensemble，并将 600M 作为基线共同报告。

本轮 7 个训练任务无需补跑。若老师希望进一步加强模型族层面的统计
比较，可以补充 600M seeds 42-44，形成平衡的 5-vs-5；这不是当前结论
成立的必要条件，而是可选的统计增强。

## 十、证据位置

正式完成与指标返回包：

```text
custom/docs/enzyme_feature_expansion/
ENZYMECAGE_LUCAPCYCLE_MODEL_TRAINING_RUN_2026-07-01/
03_HPC_Returned_Result_Summaries/
t3_4d_chenyu_formal_completion_and_metrics_20260712/
```

本地严格审计：

```text
custom/docs/enzyme_feature_expansion/
ENZYMECAGE_LUCAPCYCLE_MODEL_TRAINING_RUN_2026-07-01/
04_Local_Review_Audits/
ENZYMECAGE_T3_4D_CHENYU_FORMAL_COMPLETION_AND_METRICS_LOCAL_REVIEW_2026-07-12.md
```

训练模型与完整预测结果位于晨羽数据目录；该目录仍需按平台保留规则
另行备份：

```text
/usrdata/EnzymeCAGE_runs/checkpoints/
  pretrain_esm2_3b_corrected_107705_round1_formal_chenyu_20260710/
  pretrain_esmc600m_baseline_1152_round1_formal_chenyu_20260710/
```
