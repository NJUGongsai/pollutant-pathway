# 任务书：`[biosysmodb121]` 多步反应路径能力评测（121 条路径 / 417 步：路径级重建与自回归多步展开）

- **文档编号**：`TASK_B121_MULTISTEP_PATHWAY_EVAL_2026-11-11`
- **立项日期**：2026-11-11
- **题域标签**：**`[biosysmodb121]`**（B1 环境微生物多步降解路径，与 `[dev-298]` 双向不外推）
- **分集与锁死纪律**：
  - `biosysmodb121` 全卷 `417` 道单步题源自 `121` 条正式路径（其中含 `417` 道可评步骤的路径组共 `119` 条，另有 `2` 条路径因全部步骤处于 `FULL_INCOMPLETE`/`HOLD` 未进 `417` 集）；
  - 既有分集清单（`ppv1-holdout-v1-2026-11-05`，`group_unit = "case_id"`）**严格按整条路径（`BIOPATH150_xxx`）切分**，无任何一条路径跨调参/留出集切碎：
    - **`[biosysmodb121·调参集]`（`tuning_subset`，本任务默认评测域）**：**`76` 条完整多步路径，合计 `261` 个反应步**（单条路径步数范围 `1–8` 步，均值 `3.43` 步）；
    - **`[biosysmodb121·留出集]`（`holdout_subset`，默认 `LOCKED`）**：**`43` 条完整多步路径，合计 `156` 个反应步**（未经 CC 显式口令解锁，严禁读取或报出留出集与全卷 `119` 条路径数字）。

---

## 一、 现状表与核心科学问题

### 1.1 现状盘点

| 维度 | 现状事实 | 缺口与待回答问题 |
| :--- | :--- | :--- |
| **底层数据拓扑** | `417` 道题的 `qid` 格式为 `BIOPATH150_<case_id>__S<step_idx>__<rxn_id>`；B1a 拆步表完整保留了 `predecessor_step_ids`、`successor_step_ids`、`topological_level`、`branch_id` 与路径图类型（线性链 `LINEAR_UNIQUE` vs 分支有向无环图 `BRANCHED_DAG`）。 | 既有报告（`B121_417_RESULT`、强模型探针、`v44-Next`）均将 `261`（或 `417`）个反应步视作**独立单步题**统计 `Hit@1/3/5`，尚未还原到**“每条多步降解路径”**的维度。 |
| **单步基线资产** | 已落盘封存多套完整单步评测结果（均为 `deepseek-v4.1-flash-1017` 或探针对照模型）：<br>① 永久 `v4` 基线 (`fcd2707`)：`76/261 (29.12%)`<br>② 强模型探针三臂 (`F-ds` `83/261`、`F-qw` `70/261`、`M-qw` `68/261`)<br>③ 正规生产管线 `v44-Next v1.1 / v1.2`：`87/261 (33.33%)` | 不知道这 `87/261` 的单步命中在 `76` 条多步路径上是如何分布的：<br>• 究竟是把少数短路径全部走通了，还是每条长路径只猜对了第 1 步（`S01`）而在第 2–5 步断链？<br>• 模型在起始污染物首步攻击（`S01`）vs 中间体后续转化（`S02+`）上的准确率衰减斜率是多少？ |
| **多步评测双范式** | • **范式 A（Teacher-Forced 路径级聚合）**：已知每步真实前体底物，测试模型能否把整条路径的每一步都答对（零额外调用，直接由现有单步结果聚合）；<br>• **范式 B（End-to-End 自回归多步路径树搜索）**：只给每条路径的起始污染物（Root Substrate），由模型预测第 1 步产物并自动作为第 2 步底物继续往下推演，测试真实无外部纠偏下的端到端多步推演能力。 | 需分两阶段推进：**Phase 1（零调用、零成本）**先完成范式 A 的全套多步路径重建与深度衰减诊断；**Phase 2（受控自回归束搜索）**在调参集多步路径（`L >= 2`）上评测端到端级联推演。 |

---

## 二、 铁律与红线约束

1. **留出集（Holdout）绝对隔离**：
   - 全程只准读取并报告 **`[biosysmodb121·调参集]`（`76` 条路径 / `261` 道单步题）**；
   - 严禁读取、聚合或通过“全卷减调参集”间接推算留出集（`43` 条路径 / `156` 道单步题）的任何路径级或步级数字；`holdout_subset` 必须保持 `locked_needs_CC_token`。
2. **金标、题面与私有 `qid` 隔离**：
   - 公开报告（`docs/reports/`）只允许包含聚合指标、按路径长度 $L$ / 拓扑深度 $t$ / 路径类型（线性 vs 分支）的分桶统计表；
   - 任何单条路径真实 `case_id`（`BIOPATH150_xxx`）、单步 `qid`、底物/产物 SMILES 结构串一律写入 gitignored 目录 `reports/manual_review/b121_multistep_eval_2026-11-11/`。
3. **100% 零 LLM 判分与双口径并行（G1 护栏）**：
   - 单步与路径级命中判定严格复用官方 `ppv1-criteria-v4` (`matched_product_hit`) 与 `ppv1-criteria-v5` (`role_bound_product_hit` + `C4*`)，并同时披露剔除检索自命中后的 `ex-self` 口径。
4. **拍板点节奏**：
   - **Phase 1（Teacher-Forced 多步路径重建与深度衰减评测）** 为纯离线零调用分析，获批后由子代理直接跑完出表；
   - **Phase 2（End-to-End 自回归多步树搜索）** 涉及多步在线 LLM 调用，必须在 Phase 1 报告产出后、由 CC 确认束宽 $B$ 与深度上限 $D$ 后再启动。

---

## 三、 评测指标体系定义（Phase 1 & Phase 2）

### 3.1 Phase 1：Teacher-Forced 多步路径级指标（基于既有单步运行结果，0 Token）

设调参集共有 $M = 76$ 条路径，第 $m$ 条路径包含有序/有向反应步集合 $S_m = \{s_{m,1}, s_{m,2}, \dots, s_{m,L_m}\}$（$\sum_{m=1}^{76} L_m = 261$）。对任一候选截断阈值 $K \in \{1, 3, 5\}$ 及判据口径 $c \in \{\text{v4}, \text{v5}, \text{v4-ex-self}\}$：

1. **整条路径全通率（Exact Pathway Completion Rate, `PW-Exact@K`）**：
   $$\text{PW-Exact@}K = \frac{1}{M} \sum_{m=1}^{M} \mathbb{I}\Big(\forall s \in S_m,\ \text{rank}_c(s) \le K\Big)$$
   - 同时报告：**全量路径（$M=76$）** 与 **真多步路径子集（$L_m \ge 2$）** 的 `PW-Exact@K`，避免 $L_m=1$ 的单步路径稀释多步难度。
2. **从根污染物出发的连续前缀步深与比例（Root-Prefix Contiguous Reach, `PW-PrefixDepth@K` / `PW-PrefixRatio@K`）**：
   - 定义每条路径从第 1 步（`S01`）起沿着路径有向图连续不中断命中的步数 $d_m^{(K)} \in [0, L_m]$：若 `S01` 未命中，则 $d_m^{(K)} = 0$（代表第一步就断链，后续全断）；
   - 汇总平均连续步数 $\overline{d}^{(K)} = \frac{1}{M}\sum_m d_m^{(K)}$、平均连续完成比 $\text{PW-PrefixRatio@}K = \frac{1}{M}\sum_m \frac{d_m^{(K)}}{L_m}$，以及**至少走通前 2 步（`Prefix >= 2`）**、**至少走通前 3 步（`Prefix >= 3`）**的路径数。
3. **路径级宏平均步召回率（Macro-Averaged Pathway Step Recall, `PW-MacroRecall@K`）**：
   $$\text{PW-MacroRecall@}K = \frac{1}{M} \sum_{m=1}^{M} \left( \frac{1}{L_m} \sum_{s \in S_m} \mathbb{I}(\text{rank}_c(s) \le K) \right)$$
   - 与微平均（Micro-Average，即既有单步 `Hit@K / 261`）并列对比，检验模型是否偏科于短路径或特定家族路径。
4. **拓扑步深衰减曲线（Step-Depth Decay Curve, $t = 1, 2, 3, 4, \ge 5$）**：
   - 将 `261` 个反应步按其在路径中的步序号 / 拓扑层级 $t = 1\ (\text{S01}),\ 2\ (\text{S02}),\ 3\ (\text{S03}),\ 4\ (\text{S04}),\ \ge 5\ (\text{S05+})$ 分组，分别计算各层的 `GIP@16`（候选池覆盖率）、`v4 Hit@1`、`v4 Hit@3`、`v4 Hit@5` 与 `v5 Hit@5`；
   - 直接回答：**“模型是死在首步外源污染物激活（$t=1$），还是死在中后段代谢中间体开环/氧化（$t \ge 2$）？”**
5. **路径长度分桶表（By Pathway Length $L \in \{1, 2, 3, 4, 5, \ge 6\}$）与断链归因**：
   - 对未全通路径（`PW-Exact@5 == False`），统计其首个断链点（First-Break Step Index）及断链原因占比（① 候选池无金标且模型未写出 `pool_miss_and_novel_miss`、② 模型写出但编译/守恒被拒 `compile_or_audit_loss`、③ 金标已进榜但排在 $>K$ `ranking_loss`、④ 电荷/质子化或立体表示差 `form_representation_gap`）。

---

### 3.2 Phase 2：End-to-End 自回归多步路径树搜索指标（脱离 Teacher-Forcing，从 `S01` 根底物自由推演）

在调参集真多步路径（$L_m \ge 2$）上，仅向 `v44-Next` 输入每条路径的起始反应物 $u_0$（`S01` 底物），按束搜索宽度 $B \in \{1, 3, 5\}$、深度上限 $D = L_m$ 自回归展开（每步取各分支 Top-$B$ 合规主产物去重后作为下一步底物）：

1. **端到端中间体节点召回率（End-to-End Metabolite Node Recall, `E2E-NodeRecall@B`）**：
   - 预测树生成的全部合规产物节点集合 $\hat{V}_m$（按 `strict_identity` 与 `cn_identity` 双口径）命中金标路径全部下游代谢物集合 $V_{m,\text{gold}} = \{v_1, \dots, v_{L_m}\}$ 的比例。
2. **端到端级联反应边召回率（Cascaded Edge Recall, `E2E-EdgeRecall@B`）**：
   - 预测树中的有向转化边 $(\hat{u} \to \hat{v})$ 双端同时严格匹配金标反应边 $(u \to v) \in E_{m,\text{gold}}$ 的比例（按深度 $t=1, 2, \dots, L_m$ 披露级联衰减）。
3. **端到端全路径打通率（End-to-End Full-Pathway Reachability, `E2E-FullReach@B`）**：
   - 从根底物 $u_0$ 出发，存在一条完全由合规预测边组成的有向路径直达金标终末产物 $v_{L_m}$ 的路径数与占比。

---

## 四、 横向对比矩阵（Phase 1 一次跑齐 6 个代表性实验臂）

Phase 1 脚本将对以下 **6 个已封存实验臂** 在 `[biosysmodb121·调参集]`（`76` 条路径 / `261` 步）上进行同口径多步能力横向对比：

| 对比臂编号 | 实验臂名称 | 模型与架构配置 | 数据来源路径 |
| :---: | :--- | :--- | :--- |
| **Arm 1** | **`Permanent_v4_Baseline`** | `deepseek-v4.1-flash-1017` + `S0` 池 (`fcd2707`) | `reports/ppv1_s5b/b121_full_20261013_020955/` |
| **Arm 2** | **`Exp1b_Arm_A`** | `deepseek-v4.1-flash-1017` + 同配置 A 臂基线 | `reports/ppv1_s5b/exp1_b121_20261108_1956/` |
| **Arm 3** | **`SMP_F_ds` (探针 Flash-DS)** | `deepseek-v4.1-flash-1017` + 强模型探针 `S0′` | `reports/manual_review/strong_model_probe_2026-11-09/per_qid_flags_b121_f_ds.tsv` |
| **Arm 4** | **`SMP_M_qw` (探针 Qwen-Max)** | `qwen3.8-max` + 强模型探针 `S0′` | `reports/manual_review/strong_model_probe_2026-11-09/per_qid_flags_b121_m_qw.tsv` |
| **Arm 5** | **`v44_Next_v1_0` (`c16cb85`)** | `deepseek-v4.1-flash-1017` + `v44-Next v1.0` | `reports/ppv1_s5b/v44_next_tuning_20261110/` |
| **Arm 6** | **`v44_Next_v1_1 / v1.2`** | `deepseek-v4.1-flash-1017` + `S1d ∪ S5` Top-16 + 智能回填与精排 | `reports/ppv1_s5b/v44_next_v1_1_tuning_20261110/`（及 `v1_2`） |

---

## 五、 分步执行命令（供执行子代理照书执行）

### Step 1：运行 Phase 1 零调用多步路径能力评测脚本
```bash
PYTHONPATH=/Volumes/CC/Enzyme_Agent/v44/src \
  /Users/cc/miniconda3/envs/depending43/bin/python \
  /Volumes/CC/Enzyme_Agent/v44/scripts/eval/eval_b121_multistep_pathway.py \
  --repo-root /Volumes/CC/Enzyme_Agent/v44 \
  --out-summary /Volumes/CC/Enzyme_Agent/v44/docs/reviews/evidence/b121_multistep_eval_2026-11-11/b121_multistep_tuning_summary.json \
  --out-report /Volumes/CC/Enzyme_Agent/v44/docs/reports/B121_MULTISTEP_PATHWAY_BENCHMARK_2026-11-11.md \
  --private-dir /Volumes/CC/Enzyme_Agent/v44/reports/manual_review/b121_multistep_eval_2026-11-11
```

### Step 2：红线与闭合门禁核验
```bash
# 1. 验证留出集 156 题 / 43 条路径零触碰，且调参集 76 条路径步数加总 == 261
/Users/cc/miniconda3/envs/depending43/bin/python -c '
import json
from pathlib import Path
d = json.loads(Path("/Volumes/CC/Enzyme_Agent/v44/docs/reviews/evidence/b121_multistep_eval_2026-11-11/b121_multistep_tuning_summary.json").read_text())
assert d["holdout_touched"] is False
assert d["n_tuning_pathways"] == 76
assert d["n_tuning_steps"] == 261
print("GATE-1 PASS: 76 tuning pathways / 261 steps closed, holdout untouched.")
'

# 2. 扫描公开报告与公开 JSON 确认零 BIOPATH150_ 单路径 ID、零 BSY-r 反应 ID、零 SMILES
! grep -E "BIOPATH150_[0-9]{3}|BSY-r[0-9]+" \
  /Volumes/CC/Enzyme_Agent/v44/docs/reports/B121_MULTISTEP_PATHWAY_BENCHMARK_2026-11-11.md \
  /Volumes/CC/Enzyme_Agent/v44/docs/reviews/evidence/b121_multistep_eval_2026-11-11/b121_multistep_tuning_summary.json \
  && echo "GATE-2 PASS: Zero private pathway/step IDs in public artifacts."
```

### Step 3：同步文档至双仓
将生成的报告与证据包同步拷贝至 `/Volumes/CC/Enzyme_Agent/dependingv43/docs/` 对应路径。

---

## 六、 排障表

| 故障现象 | 根因排查 | 标准处置动作 |
| :--- | :--- | :--- |
| 部分路径步序号不连续（如存在 `S01, S03` 缺 `S02`） | 原 `121` 条路径总计 `533` 步中有 `66` 步因无结构电子载体属 `FULL_INCOMPLETE`、`15` 步属 `HOLD` 等未进入 `417` 题集 | 同时计算两种口径：① **可评步集合全通（Evaluated-Steps Exact）**：该路径在 `417` 集中的所有可评步全中；② **严格拓扑前缀（Strict Topological Prefix from `S01`）**：按步序号 `S01 -> S02 -> ...` 连续核算，并在汇总表中如实披露含缺步跳号路径的数量。 |
| 分支路径（`BRANCHED_DAG`）存在同级并列步 | `121` 条路径中有 `97` 条线性路径、`24` 条分支 DAG 路径 | 若存在精确拓扑前驱表（`step_queries.tsv`），按有向无环图前驱可达性计算连续深度；若仅消费 `qid` 步序号，则按步序号升序计算主干前缀，同时单列“任意子集命中率（Step Recall）”。 |
| `v5` 与 `v4` 口径混淆 | 历史探针脚本曾将去电荷/去立体骨架匹配误标为 `v5` | 本任务强制只认 `s5b_scoring.py` 官方 `ppv1-criteria-v5`（`role_bound_product_hit` + `C4*`）；去电荷/去立体同骨架匹配一律标为诊断列 `skeleton_cn_hit`，不进主成绩。 |

---

## 七、 回传义务清单

执行子代理完成后必须向主窗口回传：
1. **76 条调参集多步路径总表**：6 个实验臂在 `PW-Exact@1/3/5`（全量 76 条 vs 真多步 $L \ge 2$）、`PW-PrefixDepth@1/3/5`、`PW-PrefixRatio@1/3/5`、`PW-MacroRecall@1/3/5` 上的完整对照表（含 `v4`、`v4 ex-self`、`v5`）；
2. **按拓扑步深（`S01` vs `S02` vs `S03` vs `S04+`）的命中率衰减表**：明确指出 `v44-Next` 相比基线提升最大的是首步（`S01`）还是后续步（`S02+`）；
3. **按路径长度 $L \in \{1, 2, 3, 4, 5, \ge 6\}$ 的全通率与首断链归因表**；
4. **Phase 2（端到端自回归树搜索）的候选路径清单与预计 Token 预算表**（供 CC 拍板是否启动在线自回归多步推演）。

---

## 八、 脚本全文附录（`scripts/eval/eval_b121_multistep_pathway.py` 骨架规范）

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 1 Multi-Step Pathway Capability Evaluator for [biosysmodb121] (Tuning Set: 76 pathways / 261 steps).
Zero LLM calls, zero holdout access, zero private qid/SMILES in public outputs.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

QID_RE = re.compile(r"^(BIOPATH150_\d+)__S(\d+)__(BSY-r\d+)$")


def parse_qid(qid: str) -> tuple[str, int, str]:
    m = QID_RE.match(qid.strip())
    if not m:
        raise ValueError(f"Unrecognized biosysmodb121 qid format: {qid!r}")
    return m.group(1), int(m.group(2)), m.group(3)


def evaluate_pathway_arm(
    step_ranks: dict[str, int | None],
    pathways: dict[str, list[tuple[int, str]]],
) -> dict[str, Any]:
    """
    Compute pathway-level multi-step metrics for a given arm's step_ranks {qid: rank_int_or_None}.
    pathways maps case_id -> sorted list of (step_num, qid).
    """
    n_pathways = len(pathways)
    multistep_ids = [cid for cid, steps in pathways.items() if len(steps) >= 2]
    out: dict[str, Any] = {
        "n_pathways_all": n_pathways,
        "n_pathways_multistep_ge2": len(multistep_ids),
        "n_steps_total": sum(len(s) for s in pathways.values()),
        "by_k": {},
        "by_step_depth": {},
        "by_pathway_length": {},
    }

    for k in (1, 3, 5):
        exact_all = 0
        exact_ge2 = 0
        prefix_depths: list[int] = []
        prefix_ratios: list[float] = []
        macro_recalls: list[float] = []
        prefix_ge2 = 0
        prefix_ge3 = 0

        for cid, steps in sorted(pathways.items()):
            L = len(steps)
            hits = [
                (step_ranks.get(qid) is not None and 1 <= int(step_ranks[qid]) <= k)
                for _, qid in steps
            ]
            if all(hits):
                exact_all += 1
                if L >= 2:
                    exact_ge2 += 1

            # Contiguous prefix from the first recorded step in the pathway
            p_depth = 0
            for h in hits:
                if h:
                    p_depth += 1
                else:
                    break
            prefix_depths.append(p_depth)
            prefix_ratios.append(p_depth / L)
            macro_recalls.append(sum(1 for h in hits if h) / L)
            if p_depth >= 2:
                prefix_ge2 += 1
            if p_depth >= 3:
                prefix_ge3 += 1

        out["by_k"][f"top_{k}"] = {
            "pw_exact_all": exact_all,
            "pw_exact_all_rate": round(exact_all / n_pathways, 4) if n_pathways else 0.0,
            "pw_exact_ge2": exact_ge2,
            "pw_exact_ge2_rate": (
                round(exact_ge2 / len(multistep_ids), 4) if multistep_ids else 0.0
            ),
            "pw_mean_prefix_depth": round(sum(prefix_depths) / n_pathways, 4),
            "pw_mean_prefix_ratio": round(sum(prefix_ratios) / n_pathways, 4),
            "pw_macro_step_recall": round(sum(macro_recalls) / n_pathways, 4),
            "pw_prefix_ge2_count": prefix_ge2,
            "pw_prefix_ge3_count": prefix_ge3,
        }

    return out
```
