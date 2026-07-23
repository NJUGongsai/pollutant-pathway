# EC-4 是怎么从训练里"冒出来"的？

> 受众：参与 Bio Vector 项目但还没参与 R2 postmortem 讨论的学生
> 场景：你看到 R3 报告里 EC-4-grouped MRR = 0.918 是主指标，但训练 loss 里完全没看到 EC-4，怀疑这个评估方式是不是在自欺欺人
> 一句话：EC-4 不是训练目标，是 **emergent evaluation metric**

---

## 你的问题拆成 3 层（每一层都比上一层深）

1. 训练 loss 里有 EC-4 吗？
2. 我们不是直接找 enzyme 吗？为什么评估变成找 EC-4 了？
3. 那训练 enzyme 特征那一段在干什么？

---

## Q1：训练 loss 里**没有** EC-4

我们的训练 loss 是：

```
total_loss = InfoNCE(reaction, enzyme)            # row-level pair 对齐
           + VICReg(variance + covariance reg)     # 防向量塌缩
           + cross-modal terms (E↔M, S↔M)          # 跨模态对齐
```

`hard_neg_weight` 曾经用 EC-1（一位数）做 hard-negative mining 加权，但 R3 验证后已经是 **dead code**（`hard_neg_weight = 1.0` 时 same_ec 矩阵全失效）。

**EC-4（4 位 EC 号）在训练 loss 里完全不出现**。loss 只看 "reaction[i] 是否拉向 enzyme[i]"，不看 EC label。

---

## Q2：那为什么评估变成 EC-4 主指标？

因为数据结构有个硬约束：

> 训练集 145,607 row 里，每个 EC-4 类**平均 47 行 row 共享同一个 EC-4 标签**（中位数 4，最大 2,291）

举例：EC `1.14.13.1`（苯单加氧酶）有 ~50 个 row。这 50 行的：
- **reaction 端 DRFP fingerprint 几乎一模一样**（同样的化学转化）
- **enzyme 端是不同物种的同源蛋白**，ESM-C embedding 相似

给一个 reaction query，模型能做的：
- 把这 50 个候选 enzyme 都打高分 ✅（这正是模型该做的）
- **但它没有任何信号能告诉它"该选第 23 行，不选第 17 行"**——因为 reaction 端两行特征几乎一样
- 所以 row-level top-1 数学上限 = 1/50 ≈ **0.02**

R2 实测 row-level top-1 = 0.0176，EC-4 ceiling = 0.0197，**已经达到 ceiling 的 89%**——模型已经做到信息论极限了。

**这不是"效果不好"，是数据本身让 row-level 任务不可解。**

---

## Q3：那训练 enzyme 特征是在干什么？

**这个问题最关键。** enzyme 特征训练的目的不是为了"找到第 23 行那个 enzyme"，而是为了：

| 训练 enzyme 特征想达成的 | 实际达成情况 |
|---|---|
| reaction 和 enzyme 拉到同一个 d=256 向量空间 | ✅ 达成 |
| 同功能 enzyme 在向量空间中聚集 | ✅ 达成（EC-4 grouped MRR = 0.918） |
| 在 47 个同功能 enzyme 中精确分辨第 23 行 | ❌ 数据上不可解 |

**enzyme 特征训得好的衡量标准不是 row-level top-1，是 EC-4 grouped top-1**：
- 给一个 reaction，能找到一堆"功能正确"的候选 enzyme（同 EC-4 类）= **0.854**
- 工业上这就够了：tool/verifier 只需要给 agent 一个候选集，不需要精确到行

---

## EC-4 是怎么"emerge"出来的？

虽然 loss 里没有 EC-4，但**同 EC-4 类的 row 在两个端都结构性相似**，对比学习把这两个相似性"传染"到统一向量空间里：

```
reaction 端: 同 EC-4 反应的 DRFP fingerprint 几乎一样
                          ↓
                    InfoNCE loss 拉近 reaction[i] 与 enzyme[i]
                          ↓
        reaction 向量天然聚成 EC-4 簇
                          ↓
        通过 reaction-enzyme 配对"传染"到 enzyme 端
                          ↓
        enzyme 向量也聚成 EC-4 簇
                          ↓
        EC-4-grouped retrieval = 0.918（emergent）
```

EC-4 family structure 是 **emergent property**，不是 trained label。这是对比学习的标准副作用——只要训练数据有潜在的 group structure，learned representation 就会自然反映这个 structure。

---

## "应该让效果好一点"——你想 push 哪个指标？

你的直觉是对的，但要 push 对方向。下表是当前 5 个候选 push 方向：

| 指标 | 当前值 | 还有空间吗 | 怎么 push |
|---|---:|---|---|
| row-level top-1 | 0.0176 | ❌ 数据 ceiling 锁死 0.02 | 数据去重（损失 97% 训练数据）/ 加 UniProt 级别 supervision（没数据） |
| EC-4-grouped top-1 | 0.854 | 边际空间 5–10% | class-balanced sampler / 更长训练 / 更深 encoder |
| **EC-4-grouped 长尾 top-1** | 0.821 | **R3 已 +7.53%**，还有 5–10% | 继续 sampler 优化 |
| Calibration（0.8–0.9 bin 死区） | gap +0.485 | 还有空间 | isotonic regression / Platt scaling，但属于 agent 端 |
| **Leave-EC-out 泛化** | **未知** | **进行中** | 当前 leave-EC-4-class-out 验证就是测这个 |

学生说"应该让效果好一点"——你**很对**，但要 push 对方向：

- 如果你看的是 **row-level** → 死路，ceiling-bound，再训也是 0.02
- 如果你看的是 **EC-4 grouped** → R3 已经 0.918，边际收益小
- **真正还没做完的是 leave-EC-class-out 泛化** —— 模型对**训练时没见过的 EC-4 类**能不能 retrieve 到正确的 EC-3 邻居（family-level generalization），这才是当前的 push 方向

---

## 那 EC-4 → 具体 enzyme 这一步呢？（two-stage retrieval）

你可能马上有下一个疑问：

> EC-4 grouped 给的是一堆候选 enzyme（同 EC-4 family），那从 50 个候选里挑**具体那个**怎么办？这一步谁来做？

**答案：交给 Agent，不是模型**。这是 two-stage retrieval 架构：

```
Stage 1（R3 模型）: reaction ──▶ top-K=50 candidate enzymes (同 EC-4 family)
                                            │
Stage 2（Agent）  : (K candidates + query context) ──▶ 1 ranked enzyme
                                            │
Stage 3（可选）   : verify with BRENDA / KEGG / UniProt
```

### 为什么 Stage 2 不让模型做？

不是不能做（叫 conditional reranker），而是**模型做不如 agent 做**：

| 维度 | 模型 Stage 2 ranker | **Agent Reranker** |
|---|---|---|
| 训练成本 | 1-2 周 + 数据构造 | **0** |
| Context schema 灵活性 | 固定 input schema | **prompt 临时换** |
| 生物学常识 | 需要从零教 | **LLM 自带**（嗜热菌酶不能用在常温反应等隐性约束）|
| 数据库访问 | 离线 embedding | **实时查 UniProt/BRENDA**|
| 可解释性 | black-box score | **reasoning trace**|
| Latency | <10ms | 500ms-2s（LLM call）|

业务定位是"模型作为 tool/verifier"——verifier 给 family-level 候选 + 信心度，**row-level 决策权本来就该在 agent**。这是架构上的自然分工，不是补丁。

### Conditional ceiling 数学（为什么 row-level 在 agent 端有空间）

unconditional retrieval（R3 模型）的 ceiling 是 0.02：

```
unconditional ceiling = 1 / (avg rows per EC-4) = 1/47 ≈ 0.02
```

加上 agent 给的 microbe context 后：

```
conditional ceiling = 1 / (avg rows per (EC-4 ∩ microbe)) ≈ 1/2 = 0.5
```

**ceiling 上去了 ~25 倍**。所以"row-level 死路"只对 unconditional 成立——对 conditional 仍有空间，但这空间在 **agent 端**，不在模型端。

### 模型端要补的接口（训练侧 todo）

R3 retrieval tool 当前只返回 `[uniprot_id, score]`。要让 agent 能做 reranker，必须扩展 metadata：

```json
{
  "uniprot_id": "P12345",
  "ec_number": "1.14.13.1",
  "organism": "Escherichia coli K-12",
  "organism_taxonomy": "Bacteria/Proteobacteria/...",
  "annotation": "Phenol 2-monooxygenase",
  "score": 0.94
}
```

**~50 行代码的接口扩展**，从 `metadata_v3.json` 拼回 organism / annotation 字段即可，**不需要重训模型**。

### Agent reranker prompt 关键约束（agent 侧 todo）

1. **Within-K constraint**：明确告诉 LLM "you must select from the K candidates, do not introduce new enzymes"——防 hallucination 编造 UniProt ID
2. **Cite-or-die**：每个 ranking 决策必须 cite candidate 的具体字段（organism / annotation / score）
3. **Abstention 路径**：K 个 candidate 都不匹配 context 时输出 `{"answer": null, "reason": "..."}`，不强行选

### 不要预训 Stage 2 ranker

先用 agent reranker 跑通 50-100 query 端到端，**根据真实效果决定要不要训**。多数 multi-agent system 在这个阶段都不需要单独训 reranker。预训是工程浪费。

---

## 一句话总结

> **EC-4 不是训练目标，是 emergent evaluation metric。**
> 我们一直在训"找正确 row"，但数据结构让 row-level ceiling 锁死 0.02。
> EC-4 grouped retrieval 是衡量 enzyme 特征"够不够好用"的现实指标——
> 0.918 说明 enzyme 特征学到了 family-level structure，足够 tool/verifier
> 给 agent 提供候选集。
>
> 如果想让"效果好一点"，方向不是 push row-level，而是 push family-level
> generalization——这正是当前 leave-EC-out 验证在做的事。

---

## 进一步阅读

如果对上述论证还有疑问，按顺序看以下三份文档（项目内）：

| 文档 | 主要回答 |
|---|---|
| `R2_POSTMORTEM_20260615_FINAL.md` Task 1.1 | row-level ceiling 0.0197 的原始数据基线 |
| `R3_RESULT_SUMMARY_20260615.md` §3.3 | EC-4 tail/mid/head bucket 分桶证据 |
| `BIO_VECTOR_R3_ACCEPTANCE_AND_LEAVE_EC_OUT_FOR_STUDENT_2026-06-16.md` §1.1 | 为什么必须做 leave-EC-out |
