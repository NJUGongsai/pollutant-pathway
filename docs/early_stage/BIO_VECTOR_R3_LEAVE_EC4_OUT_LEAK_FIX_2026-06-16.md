# R3 Leave-EC4-Out Validation 返工指令（修两处 leakage，不重训）

> 接收人：执行 R3 leave-EC4-out 的学生
> 触发原因：当前 `R3_LEAVE_EC4_OUT_20260616_171432.md` 中 hold-out (0.985) > in-sample (0.936)，ratio = 1.052 — **方向错了**，真 generalization 不可能让 unseen 比 seen 更好。
> 工作量：~10 行代码改动；无 GPU、无重训、无 train.py 修改
> 不动的部分：R3 model freeze（model_v3.pt + SHA256）、agent prerequisites v1 策略、R3 acceptance note 主体结论

---

## 1. 当前 validation 实际在测什么

**不是 family-level generalization**，是 row-level self-alignment 的 grouped 包装。原因有两处 target leakage：

### Leak A: Retrieval pool 没有排除 hold-out class 的 enzyme

`compute_ec3_grouped_metrics` 里：

```python
sim_chunk = query_emb[start:end] @ corpus_emb.T   # corpus = 全部 N=145607 enzyme
```

`corpus_emb` 包含 hold-out class 自己的所有 enzyme。query 来自 hold-out class，它**最容易 retrieve 到的就是自己 EC-4 class 内的 enzyme**——而那些 enzyme 当然属于同一个 EC-3 family，所以 `gi ∩ top-K ≠ ∅` 几乎必然命中。

这等价于：**测"模型能不能找到同 class 的 enzyme"，不是"跨 class 找到同 family 的 enzyme"**。

### Leak B: Query 自身（row i）在 EC-3 group 里

```python
gi = ec3_groups_arr.get(my_ec3)            # 包含 row i 自己
best_pos_score = float(np.max(s[gi]))      # s[i] = reaction[i] · enzyme[i]
rank = int(np.sum(s > best_pos_score)) + 1
```

`ec3_groups_arr` 基于全部 N 行构造，包含 `global_i` 自身。`s[global_i] = reaction[i] @ enzyme[i]` 是 same-row pair——R3 在 InfoNCE 下专门训练过这个 pair，**该值在 R3 上预计 > 0.9（推断，未实测）**。`best_pos_score` 几乎总从 query 自己来，`rank ≈ 1` 是必然。

---

## 2. 反常证据：ratio > 1 是 leak 铁证，不是 generalization 证据

| 现象 | 真 generalization | 当前数字 | 判定 |
|---|---|---|---|
| HO MRR vs IS MRR | HO ≤ IS（unseen 比 seen 难）| 0.985 > 0.936 | **leak** |
| HO top-1 vs IS top-1 | HO ≤ IS | 0.967 > 0.890 | **leak** |
| HO/IS ratio | ≤ 1.0 | 1.052 | **leak** |

学生在 §7 写的 "ratio supports generalization"——结论方向反了。Ratio > 1 不是 generalization 证据，是 leak 证据。

---

## 3. 修复 Patch（基于 `eval_leave_ec4_out.py` 原文件）

### 3.1 修改 `compute_ec3_grouped_metrics` 函数签名

**位置**：原函数签名行
**改动**：增加两个参数 `exclude_corpus_mask` 与 `exclude_self`

```python
def compute_ec3_grouped_metrics(
    query_emb,
    corpus_emb,
    ec3_labels_query,
    ec3_groups_arr,
    chunk_size,
    ks=(1, 5, 10),
    ec4_labels_query=None,
    query_row_indices=None,        # NEW: 每个 query 在 corpus 里的 global index
    exclude_corpus_mask=None,      # NEW: shape=(N,) bool, True 表示要 ban 的 corpus 位置
    exclude_self=True,             # NEW: 是否 ban query 自己（防 row-level self-leak）
):
```

### 3.2 在 inner loop 里加 mask

**位置**：`s = sim_chunk[local_i]` 之后、`best_pos_score = ...` 之前

```python
for local_i in range(end - start):
    global_i = start + local_i
    my_ec3 = ec3_labels_query[global_i]
    if my_ec3 is None:
        continue
    gi = ec3_groups_arr.get(my_ec3)
    if gi is None or len(gi) == 0:
        continue

    s = sim_chunk[local_i].copy()       # NEW: 必须 copy，原地改会污染下次迭代

    # ── NEW: ban corpus 行 ──
    if exclude_corpus_mask is not None:
        s[exclude_corpus_mask] = -np.inf

    # ── NEW: ban self ──
    self_global = None
    if exclude_self and query_row_indices is not None:
        self_global = int(query_row_indices[global_i])
        s[self_global] = -np.inf

    # ── NEW: gi 同步过滤 ──
    gi_eff = gi
    if exclude_corpus_mask is not None:
        gi_eff = gi_eff[~exclude_corpus_mask[gi_eff]]
    if self_global is not None:
        gi_eff = gi_eff[gi_eff != self_global]
    if len(gi_eff) == 0:
        continue   # 这个 query 没有 cross-class same-family target，skip

    best_pos_score = float(np.max(s[gi_eff]))
    rank = int(np.sum(s > best_pos_score)) + 1
    # ... 后续 top-k / accum 部分不变，但用 gi_eff 替代 gi
    gset = set(gi_eff.tolist())
    # ...
```

### 3.3 调用侧（hold-out）

**位置**：原 hold-out 调用处

```python
# ── 构造 hold-out class 全部 corpus 的 ban mask ──
holdout_corpus_mask = np.zeros(N, dtype=bool)
for hc in holdout_classes:
    holdout_corpus_mask[ec4_groups[hc]] = True

log(f"  hold-out corpus mask: ban {int(holdout_corpus_mask.sum())} enzyme rows")

ho_metrics = compute_ec3_grouped_metrics(
    ho_reaction,
    enzyme_emb,
    ho_ec3_labels,
    ec3_groups_arr,
    args.chunk_size,
    ec4_labels_query=ho_ec4_labels,
    query_row_indices=holdout_row_indices,   # NEW
    exclude_corpus_mask=holdout_corpus_mask, # NEW: ban 同 class corpus
    exclude_self=True,                       # NEW
)
```

### 3.4 调用侧（in-sample baseline）

In-sample 不用 ban hold-out class（它本来就不属于 hold-out），但 **也必须 ban self**（否则 in-sample baseline 同样虚高）：

```python
is_metrics = compute_ec3_grouped_metrics(
    is_reaction,
    enzyme_emb,
    is_ec3_labels,
    ec3_groups_arr,
    args.chunk_size,
    query_row_indices=subset_pick,           # NEW
    exclude_corpus_mask=None,                # in-sample 不 ban class
    exclude_self=True,                       # NEW: 必须 ban self
)
```

---

## 4. 修复后预期数字（参考区间，非硬指标）

| 指标 | 修复前 | 修复后预期 | 判定逻辑 |
|---|---|---|---|
| HO EC-3 MRR | 0.985 | **0.45 – 0.75** | 同 class ban + self ban 后剩 cross-class same-family，难度上升 |
| IS EC-3 MRR | 0.936 | **0.55 – 0.85** | 只 ban self，仍可命中同 class 邻居 |
| HO/IS ratio | 1.052 | **0.70 – 0.95**（应 < 1）| ratio < 1 才符合 generalization 物理意义 |

**新的合格线**（建议老师阈值）：

| 指标 | 阈值 | 容差 | 含义 |
|---|---|---|---|
| HO EC-3 MRR | ≥ 0.50 | ±0.05 | 跨 class 仍能找到 family-level 邻居 |
| HO EC-3 top-5 | ≥ 0.65 | ±0.05 | top-5 给 agent 候选集仍可用 |
| HO/IS ratio MRR | ≥ 0.65 | ±0.05 | 与 in-sample 差距 < 35% 即视为有 transfer |

**关键判断不在绝对数字，在三件事**：
1. **HO MRR 是否显著高于随机基线**（187 个 EC-3 class 随机基线 ≈ 1/187 ≈ 0.005，所以 HO > 0.05 已经远超随机）
2. **ratio < 1**（方向对）
3. **HO top-K 是否足够给 agent 当候选集**

如果修复后 HO MRR 落在 < 0.3，那是有用的 finding——说明 R3 family-level transfer 弱，agent 集成时 unseen EC-4 必须 fallback 而不是 abstain。

---

## 5. 连带修订清单（扫描 06_r3_agent_ready_package_20260616 后补充）

扫过交付包里另外三份 md 后，需要补充修订。**原则**：所有修订采用 **"事实陈述 + pending 状态"**，不要采用 "deprecated / 锁保守路径" —— 因为 agent 还没建，§3 决策树没有任何代码在消费它，过度锁定反而会让学生的 AI 在后续读 md 时形成 "R3 unseen EC-4 弱" 的错误 echo。

**关键区分**：

| 表述方式 | 学生 AI 读后印象 | 是否采用 |
|---|---|---|
| "v1 deprecated, failed" | R3 generalization 不行 | ❌ |
| "v1 测的是 row-level self-alignment，cross-class transfer pending v2" | 客观状态描述，无价值判断 | ✅ |
| "agent v1 abstains on unseen EC-4" | R3 unseen EC-4 已知没能力 | ❌ |
| "unseen EC-4 fallback policy pending v2 leave-out result; not yet implemented" | 决策待定，agent 编码前不需要落地这条 | ✅ |

### 5.1 R3_ACCEPTANCE_NOTE_20260616_173549.md

| 章节 | 状态 | 动作 |
|---|---|---|
| §1 Acceptance Decision | 保留 | R3 作为 tool/verifier 候选不依赖 leave-out 数字 |
| §2 Tail bucket / 训练时间改判 | 保留 | 该改判依赖 EC-4 grouped 评估，不受 leak 影响 |
| **§3 Required Evidence 表的 leave-out 行** | **改为事实陈述** | 状态写 `v1 measures row-level self-alignment; v2 cross-class transfer pending`，**不写 "deprecated/PENDING re-run"** |
| **§3 Leave-EC4-Out summary 整表** | **加注脚** | 表上方加一行说明：`v1 metrics below reflect in-distribution row-level self-alignment under R3 embedding, not cross-EC4-class generalization (corpus and self not excluded). v2 with corpus + self exclusion will report true cross-class transfer.` 数字本身**保留**，让审计能看到对比 |
| §4 Declarations | 部分改 | `Leave-EC4-Out prerequisite completed: yes (v1 in-distribution, v2 cross-class pending)` |

### 5.2 R3_AGENT_INTEGRATION_PREREQUISITES.md

| 章节 | 状态 | 动作 |
|---|---|---|
| §1 Required Inputs | 部分改 | `Leave-EC4-Out validation = v1 in-distribution complete; v2 cross-class pending` |
| §2 Confidence Threshold Strategy（score ≥ 0.9）| **完全保留** | calibration bin / threshold 与 leave-out 解耦 |
| **§3 Unseen EC-4 Fallback Decision** | **标 pending，不做临时决策** | 把整段决策树改为：`Decision pending v2 leave-out result. Threshold (≥ 0.80 → allow fallback / else abstain) remains as the rule; the input metric will be supplied by v2.` **不要预设 agent v1 走 abstain 分支**——agent 还没建，policy 还没消费，临时锁 abstain 会传递错误信号 |
| §4 OOD Detection Staging | 保留 | 与 leave-out 解耦 |
| §5 Do Not Deliver | 保留 | 负面清单不受影响 |
| **§6 Final Agent-Readiness Statement** | **改** | 删除 `Allow unseen EC-4 natural fallback ... because Leave-EC4-Out passed with EC-3-grouped MRR = 0.984791.`，换为：`Unseen EC-4 fallback decision pending v2 leave-out result; not blocking agent v1 prototyping on in-distribution EC-4 classes.` |

**关键澄清**：§3 决策树本身**不删**，阈值规则（≥ 0.80 → allow fallback / else abstain）是合理的。只是 v1 数字测错了对象（row-level self-alignment 而非 cross-class transfer），所以**输入数字 pending**，**决策本身待定**。这跟 "临时锁 abstain" 是两件事——后者会让学生 AI 误读为 "R3 已经被证明 unseen EC-4 弱"。

### 5.3 R3_MODEL_FREEZE_20260616_174232.md

| 章节 | 状态 | 动作 |
|---|---|---|
| §1–§5 （commands / ls / stat / sha256 / paths / declarations）| **全部保留** | 与 leak 无关 |
| **§6 Model Provenance 的 Leave-EC4-Out 表** | **加注脚** | 表上方加一行：`v1 metrics reflect in-distribution row-level self-alignment, not cross-EC4-class transfer. v2 corpus+self-excluded variant pending.` 数字**保留** |
| §6 结论行 "Robust cross-EC-4-class generalization demonstrated" | **改** | 改为：`In-distribution row alignment intact under R3 embedding (v1); cross-EC4-class generalization pending v2 evaluation.` |
| §7 Freeze Procedure Summary | 保留 | 只涉及 freeze 本身 |

### 5.4 一句话总结修订范围

> 模型冻结（SHA256 + chmod）**完全保留**。R3 作为 tool/verifier 候选的接受决定 / tail bucket 改判 / score≥0.9 confidence policy / OOD staging **保留**。三份 md 中 cite leave-out 数字的位置 **不删数字、不写 deprecated**，改为客观陈述："v1 measures in-distribution row-level self-alignment; v2 cross-class transfer pending"。Agent prereq §3 决策树本身保留，**只把输入数字标 pending，不要临时锁 abstain**——agent 未建时这条 policy 没消费，临时锁会向学生 AI 传递错误信号。

---

## 6. 不动的部分（原 §5 保留、去除与 §5 冲突的部分）

| 项 | 状态 | 原因 |
|---|---|---|
| `frozen/model_v3.pt` + SHA256 | **不动** | 模型本身没问题，leak 是评估口径 |
| R3 acceptance note 主体 | **保留** | EC-4 grouped MRR 0.918 / tail top-1 +7.53% 等评估流程没这两个 leak |
| Agent prerequisites v1 | **保留** | score ≥ 0.9 / abstain 策略与 leave-out 数字解耦 |
| EC-4 grouped 评估 | **不动** | 那个评估测的是 family-level retrieval 在 in-distribution 数据上的表现，与 leave-out 是两件事 |

---

## 7. 学生 Todo Checklist

- [ ] 在 `eval_leave_ec4_out.py` 应用 §3.1 – §3.4 的 patch
- [ ] 保留原 `R3_LEAVE_EC4_OUT_20260616_171432.md` 不删，重命名为 `R3_LEAVE_EC4_OUT_v1_LEAKED_20260616_171432.md`，并在文件头部加一行：`> 已废弃：存在 target leakage（同 class corpus + self），见 v2 报告`
- [ ] 重跑 eval 生成 `R3_LEAVE_EC4_OUT_v2_<timestamp>.md` 与 `r3_leave_ec4_out_v2.json`
- [ ] v2 报告里**必须包含**：
  - hold-out corpus mask 中被 ban 的 enzyme 行数（log 里有）
  - "ratio < 1" 的方向性验证语句（如果 ratio ≥ 1 则直接 FAIL，不要再走"tolerance"逻辑）
  - 与 §4 预期区间的比对
- [ ] **连带改三份 md**（按 §5.1–5.3）：
  - `R3_ACCEPTANCE_NOTE_20260616_173549.md` §3 + §4
  - `R3_AGENT_INTEGRATION_PREREQUISITES.md` §1 + §3 + §6（§3 fallback 决策临时锁住 abstain）
  - `R3_MODEL_FREEZE_20260616_174232.md` §6
- [ ] GitHub `06_r3_agent_ready_package_20260616/` 目录里**两份都留**（v1 标作废 / v2 是 final），README 里指明
- [ ] 不重训、不动 train.py、不收 OOD 数据——返工只在 eval 脚本 + 4 份 md 的文本修订

---

## 8. 一句话给学生

> 数字漂亮但物理意义反了——hold-out 不可能比 in-sample 更好。问题不在你的代码计算，在评估口径：retrieval pool 没 ban 同 class enzyme，EC-3 group 没 ban self。`compute_ec3_grouped_metrics` 加两个 mask（~10 行），重跑即可。
>
> 模型冻结（SHA256/chmod）本身不动。**三份 md 中 cite leave-out 数字的位置不要写 deprecated/abstain，改为客观陈述**：v1 测的是 in-distribution row-level self-alignment，v2 测 cross-class transfer，决策本身待 v2 数字。Agent 还没建，§3 决策树没消费，不要临时锁 abstain 路径——那会向学生 AI 传递 "R3 unseen EC-4 已知弱" 的错误信号。
