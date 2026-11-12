# BIOSYSMOdb121 多步降解与完全矿化评测基准 (`docs/`)

本目录汇总了 **`biosysmodb121` 全卷 121 条环境污染物降解路径** 的最新多步推导与端到端完全矿化评测成果。

---

## 核心基准报告

1. **[B121_E2E_MINERALIZATION_BENCHMARK_2026-11-11.md](B121_E2E_MINERALIZATION_BENCHMARK_2026-11-11.md)**  
   **全卷 121 条路径端到端零束宽（`B=1`）完全矿化六臂消融终版报告**：
   - 涵盖从 `Naive B=1` 到 `Arm 6: Stage-Aware B=1`（分阶段生化门控，20 步上限）的六臂消融；
   - 包含 61 条走满 15 步未完路径的零 LLM 离线深度解剖；
   - 包含第 8 节：与原 121 标准答卷的逐步对标与“殊途同归”四分类关系分析。

2. **[B121_MULTISTEP_PATHWAY_BENCHMARK_2026-11-11.md](B121_MULTISTEP_PATHWAY_BENCHMARK_2026-11-11.md)**  
   **已知前体对照基准（Teacher-Forced）**：
   - 统计调参集 76 条路径在每步给定标准底物时的多步串联还原与步深衰减曲线。

---

## 全卷 121 路径六臂消融成果总表（零束宽 $B=1$）

> 判定依据：`ppv1-mineralization-sink-v1`（严格碳账闭合 + 23 个中心碳代谢池或 $\text{CO}_2$ 直达）。

| 消融实验臂 (Policy) | 最大步深 | [Full-121] 完全矿化闭合率 | [Tuning-76] 完全矿化闭合率 | [Holdout-43] 完全矿化闭合率 | 环路熔断 (`CYCLE`) | 满步未完 (`MAX_DEPTH`) | 断头 (`DEAD_END`) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Arm 1: Naive $B=1$** | 15 步 | 21 / 121 (17.36%) | 16 / 76 (21.05%) | 5 / 43 (11.63%) | 89 (73.55%) | 8 (6.61%) | 3 (2.48%) |
| **Arm 2: Non-Backtrack $B=1$** | 15 步 | 38 / 121 (31.40%) | 26 / 76 (34.21%) | 12 / 43 (27.91%) | 6 (4.96%) | 61 (50.41%) | 16 (13.22%) |
| **Arm 3: Catabolic-Progress $B=1$** | 15 步 | 39 / 121 (32.23%) | 25 / 76 (32.89%) | 14 / 43 (32.56%) | 13 (10.74%) | 53 (43.80%) | 16 (13.22%) |
| **Arm 4: Non-Backtrack $B=1$** | 20 步 | 60 / 121 (49.59%) | 42 / 76 (55.26%) | 18 / 43 (41.86%) | 7 (5.79%) | 32 (26.45%) | 22 (18.18%) |
| **Arm 5: Catabolic-Progress $B=1$** | 20 步 | 42 / 121 (34.71%) | 27 / 76 (35.53%) | 15 / 43 (34.88%) | 13 (10.74%) | 42 (34.71%) | 24 (19.83%) |
| **Arm 6: Stage-Aware $B=1$ (终局合体)** | **20 步** | **`67 / 121 (55.37%)`** | **`46 / 76 (60.53%)`** | **`21 / 43 (48.84%)`** | **`10 (8.26%)`** | **`27 (22.31%)`** | **`17 (14.05%)`** |

---

## 预测路径与原 121 标准答卷对标总账

| 关系分类桶 | 全卷路径数 ($N=121$) | 调参集 ($N=76$) | 留出集 ($N=43$) | 机制说明 |
| :--- | :---: | :---: | :---: | :--- |
| **类型 I：顺着原答卷走 + 完全矿化** | **24 条** (19.8%) | 16 条 (21.1%) | 8 条 (18.6%) | 首步直接对齐原答卷（其中 **19 条** 顺势帮数据库补齐了后半程开环矿化步） |
| **类型 II：殊途同归替代通路 + 完全矿化** | **43 条** (35.5%) | 30 条 (39.5%) | 13 条 (30.2%) | 首步选了另一合法反应位点（14 条中途汇回答卷中间体，29 条走平行合法漏斗闭合） |
| **类型 III：踩中原答卷步骤、但步满未完** | **31 条** (25.6%) | 17 条 (22.4%) | 14 条 (32.6%) | 成功踩中原答卷中间体，因多支链切碳在 20 步上限处有残余支链 |
| **类型 IV：首步偏离且未闭合** | **23 条** (19.0%) | 13 条 (17.1%) | 8 条 (18.6%) | 首步选入盲端或发生全候选倒车 |
| **合计有效覆盖（类型 I + II + III）** | **`98 / 121 (81.0%)`** | **`63 / 76 (82.9%)`** | **`35 / 43 (81.4%)`** | **超八成路径要么踩中原答卷中间体（69条），要么实现 100% 严格碳账完全矿化（67条）** |

---

## 支撑文档与脱敏证据导航

- **评测任务书**：
  - [tasks/active/TASK_B121_CATABOLIC_PROGRESS_B1_EVAL_2026-11-11.md](tasks/active/TASK_B121_CATABOLIC_PROGRESS_B1_EVAL_2026-11-11.md)
  - [tasks/active/TASK_B121_NON_BACKTRACKING_B1_EVAL_2026-11-11.md](tasks/active/TASK_B121_NON_BACKTRACKING_B1_EVAL_2026-11-11.md)
  - [tasks/active/TASK_B121_E2E_MINERALIZATION_EVAL_2026-11-11.md](tasks/active/TASK_B121_E2E_MINERALIZATION_EVAL_2026-11-11.md)
  - [tasks/active/TASK_B121_MULTISTEP_PATHWAY_EVAL_2026-11-11.md](tasks/active/TASK_B121_MULTISTEP_PATHWAY_EVAL_2026-11-11.md)
- **化学审理回执**：
  - [reviews/mimo_mineralization_endpoint_review_response_2026-11-11.md](reviews/mimo_mineralization_endpoint_review_response_2026-11-11.md)
- **脱敏证据 JSON 数据包**：
  - [reviews/evidence/b121_e2e_mineralization_2026-11-11/stage_aware_b1_summary.json](reviews/evidence/b121_e2e_mineralization_2026-11-11/stage_aware_b1_summary.json)
  - [reviews/evidence/b121_e2e_mineralization_2026-11-11/b121_reference_alignment_comparison.json](reviews/evidence/b121_e2e_mineralization_2026-11-11/b121_reference_alignment_comparison.json)
  - [reviews/evidence/b121_e2e_mineralization_2026-11-11/max_depth_61_autopsy_summary.json](reviews/evidence/b121_e2e_mineralization_2026-11-11/max_depth_61_autopsy_summary.json)
