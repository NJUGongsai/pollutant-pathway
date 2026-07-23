# ESM-2 3B 全量提取审核回复 (Teacher Review)

Date: 2026-07-06
Status: APPROVED with conditions
Reviewer: Axl
Reply to: `TEACHER_ESM2_3B_FULL_EXTRACTION_AND_ADAPTATION_REPORT_2026-07-06.md`

---

## 一、审核结论

ESM-2 3B 全量提取通过审核。从 LucaPCycle M1 转为直接用标准 ESM-2 3B 提取，是正确决策——LucaPCycle M1 只有 pooled 2560 维向量，无法恢复 EnzymeCAGE 还需要的 per-residue pocket 特征。这是之前 M1-only 方案的盲点，学生独立发现并补上了。

pocket 坐标校正（从 pocket 特征中排除 BOS/CLS token）是对旧 ESM-C pipeline 的真实 bug fix。

---

## 二、决策点回复（报告第 11 节的 4 项）

### DP1 — pocket 坐标策略：采用校正后的真实残基坐标

```
DECISION: APPROVED
```

理由：pocket 特征必须只包含真实残基。旧流程把 0-based residue index 直接用于 `[L+2]` 矩阵，导致 index 0 选到 BOS/CLS 而非第一个残基，是系统性错误。校正后的坐标 `1 <= index <= L` 是正确修复。不要试图复现旧的 BOS/CLS 污染行为。

### DP2 — 排除 Q0CJ62

```
DECISION: APPROVED
```

理由：AlphaFill-gap pocket-only 比对产生多解，无法唯一证明映射时，排除比猜测严谨。把不可验证的 pocket 残基塞进训练数据有风险。Q0CJ62 从所有 split 中排除，并记录到数据排除 manifest。

### DP3 — 不保存完整 node_level 矩阵

```
DECISION: APPROVED
```

理由：35 GB pocket 特征 + 889 MB seq2feature 已满足训练需求。完整 `[L+2, 2560]` 矩阵会增加数百 GB 存储且无训练价值。存储决策正确。

### DP4 — 继续 T3-1B + 源码适配 + dry-run

```
DECISION: APPROVED，但优先级需重排（见第四节）
```

---

## 三、待解决问题（不阻塞审核，但训练前必须解决）

### OI-1：107705 vs 107731 UID 差距（中等）

Round-1 训练池 107731 个 UID，本次提取 107705 个。Q0CJ62 排除 1 个，还差约 25 个。必须查清：
- 是缺少 pocket 坐标？
- 是 AA 验证过滤？
- 还是根本没进提取 manifest？

行动：产出 `uid_gap_analysis.csv`，列出全部 26 个排除 UID 及原因。训练 split 在加载前过滤掉不在 107705 集合内的 UID。

### OI-2：N_pocket 最小值为 1（中等）

部分蛋白的 pocket 特征只有 1 个残基。单残基 pocket 在生物学上可疑。行动：
- 统计有多少 UID 的 N_pocket <= 2
- 抽查 3-5 个：pocket 坐标来自 AlphaFill 还是其他来源？
- 如果 N_pocket=1 是坐标 artifact，标记 review，不要静默训练

### OI-3：35 GB loader 兼容性（高——训练阻塞项）

`esm_node_feature.pt` 35.9 GB。`torch.load` 加载 35 GB pickle 可能在训练节点 OOM。这是训练前唯一最高风险项。

行动（T3-1B，最高优先级）：
1. 在 HPC 上验证 `torch.load(esm_node_feature.pt)` 是否成功且不 OOM
2. 如果 OOM：测试 `torch.load(..., mmap=True)`（需 PyTorch >= 2.1）或切换为分片格式
3. 验证加载结果是 `dict[str, torch.Tensor]`，且 `value.shape[1] == 2560`
4. 记录加载耗时——如果 > 5 分钟，训练 dataloader 需要改成 lazy/mmap 加载，不能 eager load

如果 loader 失败需要换格式，re-save 必须在 HPC 上完成（不要把 35 GB 传回本地）。

### OI-4：重复 sequence 的 merge 策略（低）

7452 个重复 sequence 在不同 worker 间有 float32 容差内差异。报告说 tolerance conflict = 0，不阻塞。但 merge 时取哪个 worker 的值（first-wins？average？）需要记录。行动：在 metadata 中标注每个重复 sequence 保留的是哪个 worker 的值。

### OI-5：seq2feature 含 BOS/EOS，pocket 不含（低）

`seq2feature.pkl` 对全部 L+2 行做 mean pool（含 BOS/EOS），而 `pocket_node_feature` 用校正坐标（1..L，不含 BOS/EOS）。这是有意设计：
- seq2feature 对齐旧 EnzymeCAGE 行为（向后兼容）
- pocket 用校正坐标（生物学正确性）

可接受。BOS/EOS 对 mean pool 的贡献是 2/(L+2)，长序列可忽略。记录为已知语义差异，non-blocking。

---

## 四、优先级重排的后续步骤

报告第 10 节列了 5 个训练代码需改的原因。执行优先级：

```
P0  T3-1B：35 GB loader 兼容性审计（HPC）
    → 硬阻塞项。如果 torch.load OOM，其他都白谈。
    → 必须确认：加载成功、shape 正确、耗时可接受。

P1  UID gap 分析（OI-1）+ N_pocket 抽查（OI-2）
    → 产出 uid_gap_analysis.csv + N_pocket<=2 抽查报告。
    → 这些决定训练 split 的过滤逻辑。

P2  EnzymeCAGE 源码适配：1152 → 2560 维
    → baseline.py / model.py 里 esm_dim：1152/1280 → 2560
    → hidden_dims[0] 重算：structure(512) + ESM(2560) + DRFP(2048) = 5120
    → 新建 config 指向 ESM2_3B_corrected_107705 路径
    → 不加载旧 checkpoint（维度不匹配，strict load 会失败）

P3  Tiny loader/model dry-run
    → 10 样本子集，验证 forward pass 不报 shape 错误
    → 验证没有 silent zero-vector fallback（旧 get_esm_feat 在找不到
       sequence 时返回 torch.zeros，这个不能静默触发）

P4  重复 sequence merge 策略文档化（OI-4）
    → 低优先级，记录策略即可
```

P2（源码适配）不要在 P0（loader）解决前开始。如果 35 GB 文件需要换格式保存，config 路径会变，P2 必须引用新路径。

---

## 五、P0 状态更新

之前的 `P0_M1_ONLY_PLAN_20260702.md` 被本次提取取代。更新 repo 状态：

```
P0_STEPWISE_AUDIT_STATUS = ESM2_3B_FULL_EXTRACTION_DONE
feature_source = self_extracted_esm2_3b (NOT luca_m1)
seq_feature = seq2feature.pkl [2560] (87733 条唯一序列)
pocket_feature = esm_node_feature.pt [N_pocket, 2560] (107705 个 UID)
luca_m1_status = DROPPED (无法提供 per-residue pocket 特征)
luca_m2_status = DEGENERATE (不变，已知 limitation)
formal_p0_pass = false  (卡在 T3-1B loader 审计)
training_executed = false
model_code_modified = false  (适配待做，尚未开始)
```

M1-only 方案的 Step 6 诊断（对 M1 做 effective_rank / cosine）不再需要——我们不用 LucaPCycle M1 了。等价的诊断应改为对自提取的 `seq2feature.pkl` 值重跑，作为 tiny dry-run（P3）的一部分。

---

## 六、总结

```
提取质量：       PASS
路线决策：       CORRECT（LucaPCycle M1 → 直接 ESM-2 3B）
pocket 校正：    APPROVED（排除 BOS/CLS）
4 个决策点：     全部 APPROVED
训练就绪：       NOT YET——卡在 35 GB loader 审计
下一步行动：     在 HPC 上跑 T3-1B，先解决 loader 再谈其他
```
