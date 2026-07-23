# P0 Step6b M1/M2 Prefusion Representation Metrics

黄老师您好，我们按您的要求先检查了 Luca pre-fusion representation 中 M1/M2 是否保留多样性。本次只做诊断统计，没有训练、没有修改模型代码，也没有声明 P0 通过。

## 结果

| 表征 | feature_key | feature_dim | effective_rank | pairwise_cosine_mean, random sample 10000 pairs | top-5 singular values |
|---|---:|---:|---:|---:|---|
| M1 | `embedding_pooled_vec` | 2560 | 691.8076725097683 | 0.7107045712709674 | 611.3426197827689, 278.91377918524154, 238.43956585507425, 204.48148422984266, 182.1939820814851 |
| M2 | `seq_pooled_vec` | 1024 | 3.000016937255894 | 0.9999999648630462 | 0.0037434834890547625, 0.001264669036876637, 0.0009534406132770415, 0.0006833278261171928, 0.0006367430951169095 |

## 解释

M1 的 effective_rank 较高，随机 10000 对样本的平均余弦相似度为 0.7107，说明 M1 在 pre-fusion 阶段保留了明显的特征多样性。

M2 的 effective_rank 只有约 3.00，随机 10000 对样本的平均余弦相似度接近 1.0，top-5 singular values 也极小，说明 M2 在 pre-fusion 阶段已经高度同向/低秩，基本没有保留有效多样性。

## 审计信息

```text
required_uid_count = 107706
M1 valid_count = 107706, bad_count = 0
M2 valid_count = 107706, bad_count = 0
random_pair_count_requested = 10000
random_pair_count_evaluated = 10000
array workers = 16 / 16 PART_PASS
worker stderr = empty
merge stderr = empty
training_executed = false
model_code_modified = false
p0_pass_claimed = false
```

HPC 返回包路径：

```text
/public/home/acfbwjsi7s/enzymecage_lucapcycle_adapter_data_2026-06-30/p0_stepwise_audits_20260702/step6b_m1_m2_prefusion_teacher_metrics/return_package/
```

本地审查结论：Step6b 返回包完整，能回答本次数值核查；但 Step6 的 `concat_pooled_vec` 质量门仍未通过，后续建议先按这个结果讨论是否检查 M2 提取流程、改用 M1-only、或调整 fusion 表征。
