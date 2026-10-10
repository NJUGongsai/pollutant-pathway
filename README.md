# dependingv43 — 酶催化污染物环境归趋路径预测与评测系统（v4.3 工作线）

> 面向半年后的自己和新的 AI 会话的自用导航。细节一律以被引用文件里的原文为准，
> 本文只负责指路；和正文冲突时，以 AGENTS.md 与各任务书为准。

## 这个仓库是什么

一句话：用 LLM（大模型）驱动的**酶催化污染物环境归趋路径预测系统**，外加一套
配套的**评测/判分体系**。给它一个污染物分子，系统检索已记录的酶反应证据、
必要时让模型提案，沿路径逐级展开，产出可审计的反应路径报告；再用确定性的
评测器（打分程序，全程不调用模型）对答卷判分。本仓是 v4.3 工作线，主线代号为
污染物路径 **ppv1**（S0–S5 分阶段推进，当前在 **S5b** 阶段），同期并行 HIT60
目标线（详见任务索引）。

## 快速上手

```sh
# 环境：本机 conda 环境 depending43（Python 3.11 + rdkit/lightgbm/numpy 等）
cd /Volumes/CC/Enzyme_Agent/dependingv43

# 跑全量测试（约数千项；slow 用例会真实加载 v3 引擎，明显更慢）
OMP_NUM_THREADS=1 /Users/cc/miniconda3/envs/depending43/bin/python -m pytest tests/ -v
# 只跑快速用例：在上面命令后加 -m "not slow"
# 包未 editable 安装时需前置 PYTHONPATH=src

# CLI 冒烟（资产自检 / 单分子探针 / 路径运行），见下节入口后按 --help 展开
/Users/cc/miniconda3/envs/depending43/bin/python -m pathway_v43 checkenv
```

CLI 入口统一是 `python -m pathway_v43`（子命令：`checkenv` / `probe` / `run` /
`resume` / `inspect` / `export` / `batch` / `score` 等）。路径依赖旁边的
`../dependingv3` 冻结引擎代码与本仓 `assets/` 反应检索资产（EAWAG/enviPath/USPTO
衍生数据，**许可未核实，仅限内部使用，不得公开分发**，见 ASSETS.md）。

## 目录地图（关键入口）

| 入口 | 一句话说明 |
|---|---|
| `AGENTS.md` | 全仓工作约定（红线、评审-回修循环、返工教训），**AI 会话开工必读** |
| `docs/TASK_V43_HIT60_INDEX.md` | HIT60 主线任务书总索引：各任务状态、teacher 拍板、口径裁决 |
| `ARCHITECTURE.md` / `REPO_DESIGN.md` / `ASSETS.md` | 系统架构、仓库设计、数据资产与许可说明 |
| `docs/CHENYU_ACCESS.md` | 远端执行通道与路径说明（跑大批量任务的那台机器怎么连） |
| `docs/TASK_*.md`、`docs/POLLUTANT_PATHWAY_*` | 各阶段任务书、实施与评审报告（按主题+日期命名，找事先进这里） |
| `src/pathway_v43/` | 主代码包：`adapters/`（v3 引擎/类比索引接线）、`domain/`、`workflow/`（LangGraph 主干）、`storage/`、`exam*.py`（评测/判分）、`pollutant/`（ppv1 主线）、`batch.py`（批跑） |
| `tests/` | pytest 测试集（含 slow 标记的真实资产烟测） |
| `configs/` | 批跑配置与提示词模板 |
| `runs/`、`reports/` | 运行产物与阶段报告（`runs/` 与含金标的 reports 子目录已 gitignored） |

## 仓库红线（摘要，全文以 AGENTS.md 与 docs/ 为准）

- **金标（标准答案）永不入仓**：含金标的产物只放 gitignored 目录，绝不提交。
- **封存 run 只读**：历史实验产物不续跑、不改写；新实验一律开新的批次根。
- **判分零 LLM**：评测打分全靠确定性程序，判分链路里不允许调用任何模型。
- **对外数字必须带题域标签**：dev（开发集中间步骤）和 298（RHEA 通用酶学）
  是两个题域，两边数字不互相外推、不混着报。
- 另有 mimo 化学评审三触发点、评审-回修自动循环等流程约定，见 AGENTS.md
  对应章节；流程类结论采信到与程序证据互证的程度为止。

## 当前主线与远端

- 当前主线：污染物路径 **ppv1 S5b** 阶段（升级与复测轮，评审-回修循环推进中）；
  更早的 EC298 系列、HIT60 双轨口径等历史见 `docs/` 各报告与任务索引。
- 远端（git remote）说明：
  - `origin` = 组织仓（Water-Quality-Risk-Control-Engineering/depending），
    **只读拉取用**，对本仓会话严禁任何写操作（不 push、不改分支）；
  - `github` = 个人私有备份仓（NJUGongsai/pollutant-pathway），承载本仓
    v4.3 分支完整历史的镜像备份。
