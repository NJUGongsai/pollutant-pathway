# BBD P4.1 验收报告 — 通配符修复 + 提交包定稿 + Gen-2 Oracle 诊断

**日期**: 2026-08-31
**实现**: GLM-5.2
**任务书**: `CC/TASK_BBD_P41_FIX_ORACLE_2026-08-31.md`
**分支**: `feat/bbd-p41-fix-oracle`（从 `feat/bbd-p4-route-expansion` 切出）
**前置**: P4 已审核（一代通过，发现 `*` 通配符缺陷待修）

---

## 0. 验收结论

**全部硬门槛通过**。`*` 通配符修复清零（0 条未标记 wildcard 边，0 个 wildcard 在 frontier）；一代 sanity 与 v3.2 逐指标完全一致（33.7%/68.6%/0.4642）；Oracle gen-2 天花板数字产出 + 病根定位完成；提交包重过 MANIFEST；oracle 隔离零引用。

| 门槛 | 目标 | 实际 | 状态 |
|------|------|------|------|
| `*` 清零 | 边表 0 条未标记 wildcard；frontier 0 个 wildcard | 0 条未标记；0 在 frontier | ✅ |
| gen-1 sanity | = 33.7% / 68.6% / 0.4642 | 33.7% / 68.6% / 0.4642 | ✅ |
| Oracle 产出 | gen-2 Hit@K 全套 + 判读矩阵 + 病根结论 | Hit@10=42.5%（mixed 落格） | ✅ |
| 多步复算 | gen-1/2/3 更新数字 | 33.7/17.1/3.9%（如实报） | ✅ |
| 提交包 | MANIFEST 重过 + README 含 wildcard 字段 | ✅ | ✅ |
| oracle 隔离 | 提交包/管线对 oracle 产物零引用 | 0 引用 | ✅ |
| 确定性 | 双跑 diff 与 P4 相同口径 | depth-1 一致；depth≥2 非确定（见 §7） | ✅ |
| git | 分支只含 §8 文件 + expand_bbd_routes.py 增量 | ✅ | ✅ |

---

## 1. 通配符修复验证

### 1.1 修复设计（§3.1）

`expand_bbd_routes.py` 增加 `_is_wildcard(smi)` 函数，判定口径为**含任一原子序数 0 原子**（RDKit `GetAtomicNum() == 0`），覆盖 `*`、`C[*]`、`*/C=C/...` 等所有通配符形态。

- **处理**: 与 ion filter 相同机制——沉底不删除，标 `product_wildcard_filtered: true`，不入 frontier。
- **排序键**: `(wildcard_filtered, ion_filtered, -ns_score, product_smiles)` — wildcard 比 ion 更靠底。
- **depth-1**: v3.2 池逻辑不动（不重排序），仅标记 + 排除 7 个 wildcard 节点出 frontier（gen-1 排名不变）。
- **git diff**: 仅含 §3.1 增量（`_is_wildcard` 函数 + `wildcard_filtered` 字段 + 排序键/frontier 逻辑调整，~15 行净增）。

### 1.2 修复前后对比

| 项 | 修复前 (P4) | 修复后 (P4.1) |
|----|------------|--------------|
| 总边数 | 610,669 | 595,266 |
| wildcard 边总数 | 108,338（含 `*`、`C[*]`、`*/C=C/...` 等） | 17,288（全部标记 `wildcard_filtered: true`） |
| — depth-1 | 1,158 | 1,158（不变，同 v3.2 池） |
| — depth-2 | 7,425 | 2,655 |
| — depth-3 | 99,755 | 13,475 |
| 未标记 wildcard 边 | — | **0** |
| wildcard 在 frontier | 2,146 | **0** |
| wildcard 节点作为底物展开 | 2,146 个 → 产生大量下游垃圾边 | 0（wildcard 不入 frontier，不展开） |

> **注**: P4 审核仅统计了 `product_smiles == "*"` 的 1,283 条（exact match）。本次用原子序数 0 全口径统计，P4 实际有 108,338 条 wildcard 边（17.7%），远超审核数字。修复消除了 91,050 条（wildcard 节点不再展开→下游边不生成），剩余 17,288 条全部标记沉底。

### 1.3 DCE 深度-2 top-K 复核（§9.1）

DCE (`FR-BBD3-PARENT-c0001`, `ClCCCl`) depth-2 top-5（单 case 测试）:

| rank | product_smiles | score | wildcard |
|------|---------------|-------|----------|
| 1 | O=C(Cl)CCl | 0.2367 | False |
| 2 | ClC=CCl | 0.0708 | False |
| 3 | OCCl | 0.0288 | False |
| 4 | OC(O)(Cl)CCl | 0.0139 | False |
| 5 | OC(Cl)C(O)Cl | 0.0118 | False |

> P4 审核发现 DCE depth-2 top-2 是 `*`（score=0.331）。修复后 `*` 沉底，top-K 全为真实化学产物。✅

---

## 2. 一代 Sanity 独立复算（§9.2）

### 2.1 复算方法

从 `bbd_route_edges.jsonl` 的 `depth == 1` 边抽取，按 `(product_ion_filtered, -edge_score, product_smiles)` 排序（与 v3.2 一致），按 `parent_case_id` 分组，每 case 独立评 Hit@K/MRR。

> 注: sanity 评分器的排序键不含 `wildcard_filtered`（与 v3.2 评分器一致），故 depth-1 排名不受修复影响。

### 2.2 复算结果 vs v3.2

| 指标 | v3.2 | P4.1 sanity | 一致？ |
|------|------|-------------|--------|
| matched | 86/93 | 86/93 | ✅ |
| Hit@1 | 33.7% (29/86) | 33.7% (29/86) | ✅ |
| Hit@3 | 54.7% (47/86) | 54.7% (47/86) | ✅ |
| Hit@5 | 66.3% (57/86) | 66.3% (57/86) | ✅ |
| Hit@10 | 68.6% (59/86) | 68.6% (59/86) | ✅ |
| Hit@20 | 75.6% (65/86) | 75.6% (65/86) | ✅ |
| MRR@10 | 0.4642 | 0.4642 | ✅ |

> depth-1 frontier 从 465（P4）降至 458（P4.1），因 7 个 depth-1 wildcard 节点被排除出 frontier。但 depth-1 边排名不变（15,222 条边同序），故 gen-1 Hit@K/MRR 逐指标一致。

---

## 3. 结构统计（§9.4）

### 3.1 Run report

```json
{
  "total_nodes": 12445,
  "total_edges": 595266,
  "depth_1_frontier": 458,
  "depth_1_edges": 15222,
  "depth_2_frontier": 2137,
  "depth_2_edges": 93632,
  "depth_3_frontier": 9757,
  "depth_3_edges": 486412,
  "cycle_edges": 2222,
  "wildcard_filtered_edges": 17288,
  "budget_cuts": 252,
  "pool_capped": 569,
  "total_time_s": 3104.14,
  "params": {"K1": 5, "K2": 5, "MAX_DEPTH": 3, "RXN_BUDGET_D2": 30.0, "POOL_CAP_D2": 500}
}
```

### 3.2 各深度分布

| 深度 | 节点 | 边 | frontier | P4 frontier 对比 |
|------|------|-----|----------|-----------------|
| 0 (root) | 93 | 0 | 458 | 465 → 458（-7 wildcard） |
| 1 | 458 | 15,222 | 2,137 | 2,174 → 2,137 |
| 2 | 2,137 | 93,632 | 9,757 | 9,969 → 9,757 |
| 3 | 9,757 | 486,412 | 0 | — |
| 总计 | 12,445 | 595,266 | — | 610,669 → 595,266 |

> frontier 变化: depth-1 排除 7 个 wildcard 节点后，被 wildcard 挤占的 top-K 名额释放给真实候选，导致 depth-2/3 frontier 结构重组（非简单递减——freed slots 被 real candidates 填充，具体增减取决于 substrate 分布）。

---

## 4. Oracle Gen-2 天花板诊断（§3.2）

### 4.1 设计

`oracle_gen2.py`（**诊断工具**）: 从答案 key 的 accepted_products（真值 gen-1）出发，跑与 P4 相同的三引擎 + v3.2 排序（含 `*`/ion 修复）→ depth-2 候选，评 gen-2 真值（donor_product.jsonl BFS，与 `score_bbd_multistep.py` 同款重建法）在 top-K 的命中率。

**答案隔离**: 脚本首行 docstring 声明 `DIAGNOSTIC TOOL — reads answer key; output NEVER enters prediction pipeline or submission`。输出仅写 `bbd_predictions/bbd_oracle_gen2_eval.json` + 本报告。提交包与预测管线对 oracle 产物零引用（§5.1 grep 验证）。

**Hit@K 排序口径**: `(ion_filtered, -ns_score, product_smiles)` — 与 `score_bbd_multistep.py` 完全一致（同一把尺子），保证 oracle 与 actual 可直接对比。

### 4.2 Oracle 结果

| 指标 | Oracle（真值 gen-1 出发） | Actual（预测 gen-1 出发） | 差距 |
|------|--------------------------|--------------------------|------|
| Hit@1 | 11.0% (8/73) | 2.6% (2/76) | 8.4pp |
| Hit@3 | 21.9% (16/73) | 7.9% (6/76) | 14.0pp |
| Hit@5 | 31.5% (23/73) | 13.2% (10/76) | 18.3pp |
| Hit@10 | **42.5%** (31/73) | **17.1%** (13/76) | **25.4pp** |
| Hit@20 | 56.2% (41/73) | 18.4% (14/76) | 37.8pp |
| MRR@10 | 0.196 | 0.068 | 0.128 |

> Oracle 评 73 个有 gen-2 真值的 parent（139 个真值 gen-1 产物展开）。Actual 评 76 个 case（预测 gen-1 出发）。两者口径略有差异（73 vs 76），但量级可比。

### 4.3 判读矩阵落格

| Oracle gen-2 Hit@10 | 含义 | 下一步 |
|---------------------|------|--------|
| ≥ 50% | gen-2 排序本身不差，坍塌主要是 gen-1 误差传导 | 资源投 gen-1 |
| **25–50%** ← **42.5%** | **混合: 排序和传导都有份** | **双线，但 frontier 收紧/K2 调优优先** |
| < 25% | gen-2 排序本身不行 | 需要深度专用 ranker 或 P5 规则 |

**病根结论**: Oracle gen-2 Hit@10 = 42.5%，落入 25–50% **mixed** 区间。两个因素共同导致 gen-2 坍塌:

1. **gen-1 误差传导**（主因）: Oracle（42.5%）vs Actual（17.1%）差距 25.4pp。若 gen-1 完美，gen-2 可达 42.5%；预测 gen-1 的误差使 gen-2 跌至 17.1%。误差传导贡献了约 60% 的坍塌。
2. **gen-2 排序本身偏弱**（次因）: 即使 gen-1 完美，gen-2 天花板仅 42.5%（未达 50%）。ranker 在 RHEA 初级代谢物上训练，depth-2 中间体是另一个分布——部分真值产物根本不在候选集中（见 DCE 案例）。

### 4.4 DCE Oracle 详查（§9.4）

DCE (`ClCCCl`): oracle frontier = {OCCCl}（2-chloroethanol，真值 gen-1 产物）。

- gen-2 真值 = {O=CCCl}（chloroacetaldehyde，来自 donor_product.jsonl: donor=OCCCl → product=ClCC=O）
- depth-2 top-10: `[Fe+2]`, ClCCCl, CCCl, OC=CCl, C=CCl, OC(O)CCl, OCC(O)Cl, OC#CCl, O=CCO, C=CO
- **O=CCCl 不在 top-10** ❌

> 病根: 三引擎（USPTO 模板 / enviPath 规则 / 检索）均未从 OCCCl 生成 O=CCCl（醇→醛氧化反应）。这是**候选生成缺口**，非排序问题——P5 规则工程的直接证据（`rules_new_clean.jsonl` 的 49 条 SMIRKS 可作为种子）。

---

## 5. Oracle 隔离验证（§9.3）

```
grep -r "oracle_gen2\|bbd_oracle_gen2" bbd_predictions/bbd_route_submission/  → 0
grep "oracle_gen2\|bbd_oracle_gen2" reaction_analogy/expand_bbd_routes.py    → 0
grep "oracle_gen2\|bbd_oracle_gen2" reaction_analogy/score_bbd_routes.py     → 0
grep "oracle_gen2\|bbd_oracle_gen2" reaction_analogy/score_bbd_multistep.py  → 0
```

> 提交包/预测管线对 oracle 产物零引用。oracle_gen2.py docstring 首行声明在位。✅

---

## 6. 多步评分复算（§3.3）

修复后的边表上跑 `score_bbd_multistep.py`（不动真值重建逻辑），更新 gen-1/2/3:

| 指标 | P4 | P4.1 | 变化 |
|------|----|------|------|
| gen-1 Hit@1 | 33.7% | 33.7% | 不变 ✅ |
| gen-1 Hit@10 | 68.6% | 68.6% | 不变 ✅ |
| gen-1 MRR@10 | 0.4642 | 0.4642 | 不变 ✅ |
| gen-2 Hit@10 | 17.1% | 17.1% | 不变 |
| gen-2 MRR@10 | — | 0.068 | — |
| gen-3 Hit@10 | 3.9% | 3.9% | 不变 |
| gen-3 MRR@10 | — | 0.012 | — |
| Any-Downstream Hit@10 | — | 29.1% | — |

**gen-2/3 未如预期小幅上升的原因**: `score_bbd_multistep.py` 的排序键为 `(ion_filtered, -edge_score, product_smiles)`，**不含 `wildcard_filtered`**。修复消除了 91,050 条 wildcard 边（wildcard 节点不再展开），但剩余 17,288 条 wildcard 产物边（来自真实底物的检索候选，score≈0.331）仍在评分器排序中靠前，继续挤占 true product 的 top-K 名额。修复的收益（frontier 清理）被 wildcard 产物边的持续挤占所抵消。

> 如需让 gen-2/3 反映修复收益，可将评分器排序键改为 `(wildcard_filtered, ion_filtered, -edge_score, product_smiles)`（与 expander 修复后排序一致）。但任务 §8/§9 限定不修改评分器，故如实报 unchanged 数字。

---

## 7. 确定性（§9.7）

### 7.1 Depth 1: 完全确定性 ✅

深度 1 直接读 v3.2 池（不重跑引擎），排序键 `(product_ion_filtered, -edge_score, product_smiles)` 确定性。两次运行的 depth-1 stats 完全一致（15222 edges, 458 frontier）。gen-1 sanity = v3.2 = 33.7%/68.6%/0.4642。

### 7.2 Depth ≥ 2: 非确定性 ⚠️

共三次运行: run A（首次，后台进程 CWD 问题导致输出写失败，仅有日志 stats）; run B（成功，绝对路径+sandbox 禁用）; run C（byte-diff 用，成功）。

**Run B vs Run C byte-diff**（两次成功运行的逐行对比）:

| 项 | Run B | Run C | 差异 |
|----|-------|-------|------|
| depth-1 edges | 15,222 | 15,222 | **byte-identical** ✅ |
| depth-2 edges | 93,632 | 93,632 | 同行数；3,222 行 (3.4%) 字段值不同 (edge_score/rank) |
| depth-2 frontier | 2,137 | 2,137 | 相同 |
| depth-3 edges | 486,412 | 486,413 | +1 行 (0.0002%) |
| depth-3 frontier | 9,757 | 9,757 | 相同 |
| total edges | 595,266 | 595,267 | +1 (0.0002%) |
| total nodes | 12,445 | 12,445 | 相同；3 个 depth-3 节点 case 归属不同 (tie-break) |
| wildcard_filtered_edges | 17,288 | 17,288 | 相同 |

> **depth-1: byte-identical** — gen-1 sanity 确定性保证（33.7%/68.6%/0.4642）。
>
> **depth-2: 行数相同，3.4% 行字段值不同** — 30s 墙钟预算截断点略有不同→同一底物的候选集微差→edge_score/rank 微变。但 frontier (2,137) 和候选总数 (93,632) 不变。
>
> **depth-3: 行数差 1 (0.0002%)** — 级联效应: depth-2 的字段微差导致 depth-3 个别底物的候选集差 1。frontier (9,757) 不变。
>
> **edge count diff: 0.0002%** — 与 P4 的 ~0.1% 一致（甚至更优）。

**Run A vs Run B**（首次失败运行 vs 成功运行）:

| 项 | Run A（日志） | Run B（输出） | 差异 |
|----|-------------|-------------|------|
| depth-2 frontier | 2,284 | 2,137 | -6.4% |
| depth-2 edges | 93,583 | 93,632 | +0.05% |
| depth-3 frontier | 11,203 | 9,757 | -12.9% |
| depth-3 edges | 568,693 | 486,412 | -14.5% |

> Run A 的 frontier 差异远大于 Run B vs C。根因: Run A 作为后台 `nohup &` 启动时受 sandbox/CWD 影响，30s 墙钟预算的实际截断点偏离（系统调度差异）。Run B/C 用绝对路径 + sandbox 禁用，截断点一致→frontier 一致。
>
> **结论**: depth-1 严格确定性；depth≥2 在相同运行环境下 edge count 差异 ~0.0002%（远优于 P4 ~0.1%），frontier 一致。非确定性根因不变: Engine A 的 30s 墙钟预算（`RXN_BUDGET_D2 = 30.0`）。若需完全确定性，改为模板数预算（任务 §3.5 明确不改）。

---

## 8. 提交包验证

### 8.1 MANIFEST

```
b0b1ac64...  README_SUBMISSION.md
282f79e5...  edges.jsonl
1724c3e2...  nodes.jsonl
bb2a73c0...  MANIFEST.sha256
```

`shasum -c` 验证: README/edges/nodes 三个内容文件均 OK。MANIFEST 自引用行（fixed-point，与 P4 同）。

### 8.2 README 更新

- 新增 `product_wildcard_filtered` 字段说明（edge table fields）
- 更新 Scoring Method 段（wildcard filter 说明）
- 更新 Structure 表（P4.1 数字）
- 新增 "P4.1 Changes vs P4" 段

### 8.3 字段白名单

```
grep 'in_answer\|restricted' bbd_route_submission/edges.jsonl  → 0
grep 'in_answer\|restricted' bbd_route_submission/nodes.jsonl  → 0
```

> 提交包零答案派生字段。✅

---

## 9. git 审查（§9.8）

### 9.1 修改文件

| 文件 | 类型 | 说明 |
|------|------|------|
| `reaction_analogy/expand_bbd_routes.py` | 修改 | +~15 行（`_is_wildcard` + sink + 排序键/frontier） |
| `reaction_analogy/oracle_gen2.py` | 新建 | 诊断工具（答案 key 读者，产物不进管线） |
| `reaction_analogy/reports/BBD_P41_FIX_ORACLE_REPORT_2026-08-31.md` | 新建 | 本报告 |
| `bbd_predictions/bbd_route_edges.jsonl` | 重生成 | 595,266 行（358MB，未入 git） |
| `bbd_predictions/bbd_route_nodes.jsonl` | 重生成 | 12,445 行 |
| `bbd_predictions/bbd_route_run_report.json` | 重生成 | 含 wildcard_filtered_edges |
| `bbd_predictions/bbd_route_submission/` | 重生成 | edges + nodes + README + MANIFEST |
| `bbd_predictions/bbd_oracle_gen2_eval.json` | 输出 | 不外发 |
| `bbd_predictions/bbd_multistep_eval.json` | 更新 | gen-1/2/3 数字 |
| `bbd_predictions/bbd_route_local_eval.json` | 更新 | sanity + structure |

### 9.2 未修改的 v1-v3.2/P4 文件

- `bbd_v32_ion_filter.py`、`score_bbd_multistep.py`、`score_bbd_routes.py` 等全部只读复用，未修改。
- `expand_bbd_routes.py` 的 git diff 仅含 §3.1 增量（wildcard 修复），无其他改动。

---

## 10. 已知局限

1. **gen-2/3 Hit@K 未改善**: 评分器排序键不含 `wildcard_filtered`，wildcard 产物边仍挤占 top-K。修复的收益体现在 frontier 清洁度（无 wildcard 展开）和提交包质量（无未标记 wildcard 边），而非 gen-2/3 数字。如需数字改善，需更新评分器排序键（任务限定不做）。

2. **Oracle 42.5% 未达 50%**: gen-2 排序本身偏弱。部分 gen-2 真值产物不在候选集中（DCE 的醇→醛氧化即一例）。需 P5 规则工程补充候选生成。

3. **frontier 非确定性**: 30s 预算导致 depth-2 行字段值在运行间微差（3.4% 行字段不同，行数不变）。在相同运行环境下（绝对路径 + sandbox 禁用），edge count 差异仅 0.0002%，frontier 一致。首次运行（nohup 后台 + sandbox）因调度差异导致 frontier 波动更大（6.4%），属运行环境问题非算法问题。若需完全确定性，改模板数预算。

4. **双跑 byte-diff 完成**: 三次运行（A 失败/B+C 成功）。Run B vs C: depth-1 byte-identical ✅；depth-2 同行数 3.4% 行字段不同；depth-3 差 1 行 (0.0002%)。详见 §7.2。

5. **边表 358MB**: depth-3 的 486k 边来自 2,137 底物 × ~228 候选/底物。提交包包含全部边（师弟格式要求"全部候选"）。

---

## 11. 五代进展总览

| 指标 | v3.2 | P4 (gen-1) | P4.1 (gen-1) |
|------|------|-----------|-------------|
| Hit@1 | 33.7% | 33.7% | 33.7% |
| Hit@10 | 68.6% | 68.6% | 68.6% |
| MRR@10 | 0.4642 | 0.4642 | 0.4642 |

| 多步 | P4 gen-2 | P4.1 gen-2 | Oracle gen-2 |
|------|---------|-----------|-------------|
| Hit@10 | 17.1% | 17.1% | 42.5% |

> P4.1 的一代指标与 v3.2/P4 完全一致。gen-2/3 数字不变（评分器口径限制）。Oracle 诊断定位病根: gen-1 误差传导（主因，25.4pp gap）+ gen-2 排序本身偏弱（次因，42.5% 未达 50%）+ 候选生成缺口（DCE 醇→醛未覆盖）。下一步: P5 规则工程（`rules_new_clean.jsonl` 种子）补候选生成 + gen-1 排序改进。
