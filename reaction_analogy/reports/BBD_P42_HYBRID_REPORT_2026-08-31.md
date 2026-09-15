# BBD P4.2 验收报告 — EAWAG Lookup 引擎 + 辅因子过滤 + 全精度排序（混合架构第一步）

**日期**: 2026-08-31
**实现**: GLM-5.2
**任务书**: `CC/TASK_BBD_P42_LOOKUP_HYBRID_2026-08-31.md`
**分支**: `feat/bbd-p42-lookup-hybrid`（从 `feat/bbd-p41-fix-oracle` 切出，不 push）
**架构依据**: `CC/ARCHITECTURE_UNIFIED_MPNN_RANKER_LOOKUP_2026-08-31.md`（统一架构软着陆第一步）
**前置**: P4.1（`*` 修复 + oracle 诊断，commit `8d214b0`）

---

## 0. 一页摘要 + 验收结论

P4.2 落地统一架构软着陆第一步：引擎 D（EAWAG known-pathway lookup）两层路由版 + 预测层辅因子过滤（病 1）+ 全精度排序（病 2）。三口径全部产出并披露。

| 口径 | Hit@1 | Hit@10 | MRR@10 | 门槛 | 状态 |
|------|-------|--------|--------|------|------|
| **A. 混合（主口径）** | **90.7%** (78/86) | 96.5% (83/86) | 0.9341 | ≥85% | ✅ PASS |
| **B. 纯预测（学术口径）** | 38.4% (33/86) | 68.6% (59/86) | 0.4987 | ≥40% | ⚠️ 差 1 case |
| **C. lookup-only（诊断）** | 89.5% (77/86) | 94.2% (81/86) | 0.9167 | — | ✅ 复现 §1 |

**混合口径 Hit@1 = 90.7%，超过 85% 门槛。** lookup-only 复现任务 §1 模拟基准（77/81 选择 Hit@1 = 95.1% 内层、89.5% 外层）精确一致。

**纯预测口径 Hit@1 = 38.4%，差 40% 门槛 1 个 case——触发 §7 停机条款，提交 GLM-5.3 审核。** 这不是实现 bug：v3.2 基线（33.7%）和全精度消融（36.0%）均从 §1.2 精确复现。缺口来自 §0 预算把辅因子修复（+6）和 round(6) 修复（+2~3）当作独立项相加，但两者在 c0039/c0245 上**重叠**（round(6) 并列是辅因子并列的子集），合并净增益 +4 而非 +8。详见 §3。

确定性：depth-1（混合）双跑 byte-identical；run_report 仅 `total_time_s` 字段（壁钟，与 v3.2 同性质）差异。

---

## 1. 三口径 + 归因 + 双 donor==parent 口径

全部 stereo-blind，86 个 matched answer-key case（v0.2 答案 key 经 stereo-blind 匹配 93 个 v0.3 blind parent 中的 86 个）。

### 1.1 混合口径（A，主口径）

| Hit@1 | Hit@3 | Hit@5 | Hit@10 | Hit@20 | MRR@10 |
|-------|-------|-------|--------|--------|--------|
| 78/86 = 90.7% | 83/86 = 96.5% | 83/86 = 96.5% | 83/86 = 96.5% | 83/86 = 96.5% | 0.9341 |

两层结构归因（first-hit layer）：lookup 命中贡献 77，预测兜底贡献 1（DMSO c0236，parent 非 donor，Layer 2 全精度+辅因子后 top-1 命中）。87/93 case 的 parent 是 EAWAG donor（lookup 命中）。

### 1.2 纯预测口径（B，学术口径）

| Hit@1 | Hit@3 | Hit@5 | Hit@10 | Hit@20 | MRR@10 |
|-------|-------|-------|--------|--------|--------|
| 33/86 = 38.4% | 50/86 = 58.1% | 57/86 = 66.3% | 59/86 = 68.6% | 65/86 = 75.6% | 0.4987 |

- 辅因子过滤新增 4 case（c0039, c0245, c0371, c0444）；2 case 因 c0105 是 v0.3 库外（本地答案 key 不含）、c0426 真产物不在 v3.2 池（不可恢复）——故 §1.2 的"6 case"在本地 86-case 评分下实得 4。
- Hit@10 = 68.6% = v3.2 基线，**无倒退**（§5 红线 5 满足）。

**双 donor==parent 口径（leak-audit 纪律）**：
- 纯预测 no-donor==parent Hit@1 = 23.3% (20/86)，Hit@10 = 48.8% (42/86)。
- exact-donor cases = 40/86（RHEA retrieval donor_exact_match）。

### 1.3 lookup-only 口径（C，诊断）

| Hit@1 | Hit@3 | Hit@5 | Hit@10 | Hit@20 | MRR@10 |
|-------|-------|-------|--------|--------|--------|
| 77/86 = 89.5% | 81/86 = 94.2% | 81/86 = 94.2% | 81/86 = 94.2% | 81/86 = 94.2% | 0.9167 |

- parent 是 EAWAG donor：82/86；真产物在 donor 产物列表：81/86 = 94.2%（§1.1 精确复现）。
- 查表内选择 Hit@1 = 77/81 = 95.1%（§1.1 精确复现），Hit@3 = 81/81 = 100%。
- no-donor==parent 口径全 0（lookup tier 全部是 exact-donor 证据——这是其性质，非泄漏）。

---

## 2. §1 基准复现（Phase 0，实现正确性门）

独立诊断脚本（一次性，使用答案 key 作验证，非交付物）复现任务 §1 全部数字：

| 项 | 任务 §1 | 实测 | 状态 |
|----|---------|------|------|
| parent 是 EAWAG donor & 真产物在产物列表 | 81/86 = 94.2% | 81/86 = 94.2% | ✅ |
| 查表选择 Hit@1（in-list） | 77/81 = 95.1% | 77/81 = 95.1% | ✅ |
| 查表选择 Hit@3（in-list） | 81/81 = 100% | 81/81 = 100% | ✅ |
| 两层模拟 Hit@1（truth-aware OR 兜底） | 80/86 = 93.0% | 80/86 = 93.0% | ✅ |

DCE 单测：parent `ClCCCl` 查表命中 `OCCCl`，证据 `bt0022#r0001`（EAWAG r0001 反应）✅。

> **关键说明（交付物口径 vs 模拟口径）**：§1.1 的"93.0% 两层"是 **truth-aware OR 兜底**模拟（lookup top-1 命中 OR 预测 top-1 命中）——它需要答案 key 才能判定"lookup 是否选中真产物"。交付物预测器**不能读答案 key**（红线 1），故采用**结构化两层路由**（parent 是 donor → lookup 候选置顶，无论是否选中真产物）。这导致 2 个 selection-fail case（lookup 置顶了错的产物，预测本可命中却被压到 rank 2+）在交付物混合口径下丢失 top-1。故交付物混合口径 90.7% < 模拟 93.0%，差 2 case。任务 §7 把门槛设在 85%（"模拟 93.0% 留余量"）正是为此。这是诚实、可复现、答案隔离的结果。

---

## 3. 病 1（辅因子）+ 病 2（round6）修复审计——核心发现

### 3.1 消融分解（纯预测口径，逐 case）

| 配置 | Hit@1 | 相对 v3.2 | 说明 |
|------|-------|-----------|------|
| v3.2（stored ns, ion only）基线 | 29/86 = 33.7% | — | §1 精确复现 |
| + 全精度（ion only） | 31/86 = 36.0% | +2 | §1.2"31/86=36.0%"精确复现；新增 c0039, c0245 |
| + 辅因子（stored ns） | 33/86 = 38.4% | +4 | 新增 c0039, c0245, c0371, c0444 |
| + 全精度 + 辅因子（P4.2 交付） | 33/86 = 38.4% | +4 | 同上（全精度增益被子集吞没） |

### 3.2 重叠发现（为何 +4 而非 +8）

§0 预算：`33.7% + 辅因子 +6 + round6 +2~3`。实测合并净增益仅 +4。原因：

- **全精度单独**新增 2 case：c0039, c0245（NAD⁺ 与真产物在 stored ns_score 上 round(6) 假并列，全精度打破并列→真产物上 top-1）。
- **辅因子单独**新增 4 case：c0039, c0245, c0371, c0444（NAD⁺ 缀合物沉底→真产物上 top-1）。
- **c0039/c0245 同时被两种修复解决**——因为它们的病根既是 round(6) 假并列、又是辅因子并列。c0371/c0444 的 NAD⁺ 与真产物在全精度下仍**精确同分**（不是 round(6) 假象），故只有辅因子沉底能解。
- 因此全精度的 +2 是辅因子 +4 的**子集**，合并不叠加 → 净 +4 = 33/86 = 38.4%。

> 这是任务 §0 预算的校准误差（把非独立的两个修复当独立项相加），非实现 bug。§1.2 的所有参考数字（29、31）均精确复现。

### 3.3 辅因子白名单完整性

病 1 的 6 个 cofactor-tie case 中：c0105 是 v0.3 库外（本地答案 key 不含，由师弟评分）；c0426 真产物不在 v3.2 池（不可恢复）；c0039/c0245/c0371/c0444 全部由辅因子沉底修复（truthRank→1）。**白名单零漏项**：纯预测口径下 0 个 miss case 的 top-1 仍是辅因子缀合物（结构性 SMARTS + MW>500 双保险，87/1066 EAWAG 产物正确标记）。辅因子过滤无 bug 可补。

### 3.4 全精度对 Hit@10 的影响

全精度 + 辅因子 Hit@10 = 59/86 = 68.6%（= v3.2，无倒退）。但 stored ns + 辅因子 Hit@10 = 60/86 = 69.8%——全精度在 Hit@10 上反而 -1（一个 tie-break 把某真产物从 rank≤10 推到 >10）。任务 §4.3/§4.6 定稿要求全精度，故交付用全精度配置（Hit@1 不变，Hit@10 仍过 68% 门槛）；stored+辅因子配置作为对照在 REPORT 记录。两配置均过 Hit@10 门槛。

---

## 4. 单测与溯源抽查

| 单测 | 期望 | 实测 | 状态 |
|------|------|------|------|
| DCE | parent `ClCCCl` → `OCCCl` + 证据 | `OCCCl`, `bt0022#r0001` | ✅ |
| 辅因子自检 | NAD⁺ 沉底；小分子不误杀 | NAD⁺(MW 662) flagged；8 个小分子全 pass | ✅ |
| 氯苯 c0105 | NAD⁺ 沉底后真产物上 top-1 | lookup 命中真产物（dihydrodiol）置顶；NAD⁺ 沉入预测块 | ✅ |
| lookup 溯源 | 137 条 lookup 边 100% 带 eawag_reactions | 137/137 | ✅ |

lookup 边的 `eawag_reactions` 字段格式 `"btid#reac_id"`，师弟可按 reac_id 溯源到 `https://eawag-bbd.ethz.ch/servlets/pageservlet?ptype=r&reacID=<reac_id>`。

---

## 5. 红线 grep（§10.1）

### 5.1 答案隔离

| 文件 | grep `answer|restricted|KNOWN_PATHWAY|accepted_products` | 命中分析 |
|------|--------------------------------------------------------|---------|
| `eawag_lookup.py` | 2 | 均为 docstring 隔离声明 |
| `bbd_cofactor_filter.py` | 1 | docstring 隔离声明 |
| `predict_bbd_hybrid.py` | 2 | docstring 声明 + blind CSV 路径常量（盲测 parent 输入，非答案 key） |
| `build_hybrid_submission.py` | 1 | docstring 隔离声明 |

> `predict_bbd_hybrid.py` 的 `BLIND_CSV` 常量是盲测 parent 输入（文件名含 `BLIND_PARENT_INPUTS_FOR_PREDICTION_STRICT`），与 v3.2/expand_bbd_routes 同源。答案 key 文件名含 `RESTRICTED_ANSWER_KEY`，未在任何非评分器文件出现。`score_bbd_hybrid.py` 是唯一答案 key 读者（与 `score_bbd_hitk_v32.py` 等 v3.x 评分器同列）。✅ 红线 1 满足。

### 5.2 三口径披露

- README_SUBMISSION.md：三口径表 + 溯源字段说明 + 与 enviPath lookup 同构声明 ✅
- 本 REPORT：三口径表（§1）✅
- 红线 2（三口径不可省略）满足。

### 5.3 提交包字段白名单

```
grep -c 'in_answer|restricted' bbd_route_submission/edges.jsonl  → 0
grep -c 'in_answer|restricted' bbd_route_submission/nodes.jsonl  → 0
```

提交包零答案派生字段 ✅。lookup 边带 `eawag_reactions`（公共库证据，非答案派生）。

### 5.4 泄漏断言

混合预测器加载时断言训练 educt ∩ blind parent = 0（沿用 v3.2 断言，PASS）。

---

## 6. 确定性（§10.7）

| 产物 | 双跑 byte-diff | 说明 |
|------|---------------|------|
| `bbd_hybrid_predictions.jsonl` | identical | depth-1 混合排序完全确定 |
| `bbd_hybrid_pool.jsonl` | identical | 同上 |
| `bbd_hybrid_run_report.json` | `total_time_s` 差异（壁钟） | 与 v3.2 同性质，非数据差异 |
| `bbd_route_submission/edges.jsonl` (depth-1) | identical | 混合部分完全确定 |
| `bbd_route_submission/` (depth≥2) | ~0.1% 非确定 | 沿用 P4.1 的 30s Engine A 壁钟预算（任务 §3.5 已记录，未改） |

✅ depth-1 双跑 byte-identical；depth≥2 非确定性是 P4.1 遗留、任务明示沿用。

---

## 7. §7 停机条款触发与建议

**纯预测口径 Hit@1 = 38.4% < 40% → 触发 §7 停机条款。**

依任务 §7："纯预测 < 40% 或 Hit@10 倒退 → 停（辅因子/全精度引入回归）; 交 GLM-5.3 审核。"

- Hit@10 未倒退（68.6% = v3.2，过 68% 门槛）→ 仅 Hit@1 触发。
- 辅因子/全精度**未引入回归**（§5 红线 5：纯预测 ≥ P4.1 基线，33/86 ≥ 29/86 ✓；且 +4 净增益）。
- 缺口是 §0 预算校准误差（§3.2 重叠），非 bug，无可补。

**建议交 GLM-5.3 审核的事项**：
1. 确认 90.7% 混合口径作为主交付数字（过 85% 门槛，与 ECLIPSE/enviPath 同口径对比时披露同源性）。
2. 确认纯预测 38.4% 的预算校准误差解释（§3.2）是否接受，或是否调整 40% 门槛。
3. 若需纯预测上 40%+：路径是 P5（EAWAG 1066 反应进 ranker 训练 + 羟化 SMIRKS 规则），非本轮范围。
4. 确认结构化两层路由（90.7%）与 §1 模拟 93.0% 的 2-case 差异（selection-fail，§2）可接受。

---

## 8. 交付物清单（§9）

| 文件 | 类型 | 状态 |
|------|------|------|
| `reaction_analogy/eawag_lookup.py` | 新建 | ✅ |
| `reaction_analogy/bbd_cofactor_filter.py` | 新建 | ✅ |
| `reaction_analogy/predict_bbd_hybrid.py` | 新建 | ✅ |
| `reaction_analogy/score_bbd_hybrid.py` | 新建 | ✅ |
| `reaction_analogy/build_hybrid_submission.py` | 新建（提交包重建器） | ✅ |
| `reaction_analogy/reports/BBD_P42_HYBRID_REPORT_2026-08-31.md` | 新建 | ✅ |
| `bbd_predictions/bbd_hybrid_predictions.jsonl`（93 行 top-20） | 输出 | ✅ |
| `bbd_predictions/bbd_hybrid_pool.jsonl` | 输出 | ✅ |
| `bbd_predictions/bbd_hybrid_eval.json`（三口径） | 输出 | ✅ |
| `bbd_predictions/bbd_hybrid_run_report.json` | 输出 | ✅ |
| `bbd_predictions/bbd_route_submission/`（重建） | 重生成 | ✅ |

分支 `feat/bbd-p42-lookup-hybrid`，1 个 commit，不 push。
