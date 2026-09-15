# 弓赛侧后续任务清单（三模块集成 · 师兄线）

> 收件：弓赛（`Frankgonghahaha` / `NJUGongsai`）
> 日期：2026-09-15
> 状态：待老师确认后下发

---

## 一、背景：你的分支已合入 main

你的 `feat/bbd-uspto-integrated` 分支已合并进 `main`（merge commit `102e5c6`，双 parent `1925785` + `32e5748`）。

**已合入 main 的资产**（你线的内容，原样保留）：

| 目录 | 内容 |
|---|---|
| `reaction_analogy/` | BBD/USPTO 降解产物预测 + ranker（v2→v33 全套训练/预测/评分脚本） |
| `reaction_v3/data/lib_envipath/` | enviPath 反应模板 |
| `data/bbd_v3/v31/v32/v5/hfix` | BBD ranker 训练数据 |
| `bbd_predictions/` | BBD 各版本评测输出（json/jsonl） |

**科学角色未变**：你的 depending v3.2/v3.3 仍作 **evaluation candidate**——合并代码 ≠ 切换默认引擎。正式反应预测器选型走 T6-2 裁定。

**分支现状**：`main`（单线索）+ `feat/bbd-uspto-integrated`（保留，`32e5748`）+ `demov2`（已打 `archive/demov2-v4.2` tag 归档并删分支）。

---

## 二、需要你做的任务

### 任务 1 — 切到 main 工作，确认资产完整

```bash
git fetch origin
git checkout main
git pull origin main
# 确认你的资产在 main 完整：
ls reaction_analogy/ data/bbd_v3/ bbd_predictions/ reaction_v3/
```

后续 BBD/USPTO ranker 的推进**直接在 main 上做**，不要在 `feat/bbd-uspto-integrated` 上继续堆 commit（避免二次分叉）。若你还要用 `feat` 分支作为独立实验线，请在回复里说明，我们定一个明确的合并节奏。

### 任务 2 — 补 `reaction_analogy/README.md`

目前 `reaction_analogy/` 没有任何说明文档，职责靠根 README 反推。请补一份 README，至少写清：

1. **用途**：这套 ranker 做什么（BBD/USPTO 降解产物预测的哪一环）。
2. **版本谱系**：v2 / v3 / v31 / v32 / v33 各自的差异与「哪个是当前最佳」。
3. **成绩口径**：以 `bbd_predictions/bbd_hybrid_eval_v5.json` 为准（Hit@1 89.5% / Hit@10 95.3%），说明该口径的评测范围与统计方法。
4. **依赖**：eawag_lookup / enviPath / 其它外部工具链，以及运行入口脚本（哪个 `train_*` / `predict_*` 是主流程）。
5. **license**：这套代码是你的自研，还是基于某开源项目？需要明确声明（关系到和 CC-BY-NC 底座的边界）。

### 任务 3 — `bbd_predictions/` 结果数据的处置建议

`bbd_predictions/` 里的 json/jsonl 是评测「结果数据」，合并时贡献了 main 新增约 103 万行插入的大头（不是代码）。请确认：

- 这些是否都需要留在代码仓库？还是可以移到独立的 data release / 归档目录？
- 若保留，哪些是「对外权威结果」（如 `bbd_hybrid_eval_v5.json`），哪些是历史审计证据链（可归档）？

### 任务 4 — 配合 T6-2 裁定（反应预测器选型）

T6-2 待裁定：`reaction_prediction` MISS 后的正式 predictor 是 **depending v3.2/v3.3** 还是 **BioTransformer ENVMICRO**。需要你侧提供：

- v3.2/v3.3 在 **18 条 blind（A7/gold 冻结包）** 上的评分口径与结果（与 BioTransformer 同口径可比）。
- v3.3 相对 v3.2 的增量点（fusion layer 等）及其对评分的实质影响。

---

## 三、DDL

- 任务 1（切 main + 确认资产）：收到即做，回复确认。
- 任务 2（README）+ 任务 3（数据处理建议）：【待老师定日期】
- 任务 4（T6-2 材料）：【待老师定日期，与 T6-2 裁定节奏对齐】

## 四、红线（沿用既往裁定）

- 合并后你是「候选引擎」口径，**不得**在 main 里把 `reaction_analogy/` 设成默认 predictor 路径。
- `bbd_predictions/` 里的历史版本成绩不用于对外口径，一律以 `bbd_hybrid_eval_v5.json` 为准。
- 涉及 license 的声明（任务 2 第 5 点）未明确前，不要扩散 `reaction_analogy/` 的复用范围。

---

本文件为老师侧待下发任务清单，正式生效前请老师复核补充 DDL 与裁定细节。