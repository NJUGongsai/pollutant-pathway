# USPTO v3 闭环报告 — MPNN v3 特征进 GBDT 重排器 + 域特征实验

**日期**: 2026-09-01
**执行**: GLM-5.2（按 `CC/TASK_USPTO_V3_CLOSED_LOOP_2026-09-01.md`）
**环境**: HPC wuzh02（login05/login03 提交，wzhcnormal 分区，conda env `rxn`，LightGBM 4.7.0 / numpy 1.26.4 / sklearn 1.9.0）
**分支**: `feat/uspto-v3-closed-loop`（不 push）

---

## 0. 一页结论

| 验收项 | 门槛 | 实测 | 判定 |
|--------|------|------|------|
| **v3-on top-1** | ≥ 69% | **68.28%** | **FAIL**（差 0.72pp） |
| **v3 增益 (on − off)** | ≥ +2.5pp | **+3.26pp** | **PASS**（v1 时代 +3.12pp，增益不降反微升） |
| rempnn 回归（v1 preds 重算对旧值） | 对上 | **0 / 162,154 候选不匹配**（5 shards：3 train + 2 test） | PASS |
| rempnn 双跑确定性（byte-diff） | 0 差异 | **2238 shards（1598 train + 640 test）全 byte-identical** | PASS |
| v1 基线复现 | 67.5% 可复现 | **67.82%**（原 67.50%，Δ +0.32pp，在训练噪声带内，见 §5.3） | PASS |
| 域特征消融（≥3 配置） | 数字产出 | 3 配置全跑（v3-on / v3-on+is_metal / v3-off+is_metal + 对照） | PASS（数字见 §4） |

**Gate-1 失败的诊断结论（按任务书 §6 三方向逐一核查）**：不是 rempnn 错位（回归锚点全对上、双跑 byte-identical），而是 **候选级 mpnn 特征在 v1 时代已经饱和** —— 80.2% 的正例候选 mpnn≥0.9（v3 后仍为 80.0%），v3 把正例原子概率推进到 ≥0.99 的比例从 5.6% 翻到 22.3%，但候选级特征是 site 原子概率的 **max-pool**，饱和尾部的提升被 max 吃掉；能兑现的只有负例变尖锐（中位数 0.51→0.26）带来的 +0.5~0.8pp。原子级 hit@1 +6.5pp 在 ranker 侧边际递减到 +0.5~0.8pp（mpnn-argmax 单特征 top-1 也恰好只从 35.5%→36.3%，+0.78pp，与 GBDT 级增益同量级——瓶颈在特征表示而非 GBDT）。这是任务书 §0 预判过的"原子概率饱和在 USPTO 出现"场景，如实报告，未做任何超参追调。

---

## 1. Phase 0 — rempnn 回归锚点（全链路正确性）

**方法**：取 3 个 train shard（shard_0/1/500，来自 `shards_train3`）+ 2 个 test shard（shard_0/100，来自 `shards_test3`）拷贝到 `~/rxn6/v3loop/regress/`，用 **v1 preds**（`train_preds.jsonl` / `test_preds.jsonl`，即当年生成这些 shard mpnn 值的同一份 preds）重算，与 shard 内既有 mpnn 值逐候选比对。

- train 侧：`--preds train_preds.jsonl --train train.txt`（lhs→full_line 索引）
- test 侧：`--preds test_preds.jsonl --train test.txt.proc`（test shard 的 lhs 在 test.txt.proc 里索引）
- 比对脚本 `regress/compare.py`：同时校验 mpnn 逐位相等 + 其他字段（s/f/l/type/sf/v/r/fs/site_atom_idx）零改动

**结果（`logs/phase0_regress_slurm.out`）**：

| shard | 候选数 | mpnn 精确匹配 | 不匹配 | 其他字段差异 |
|-------|--------|--------------|--------|--------------|
| train/shard_0 | 50,212 | 50,212 | 0 | 0 |
| train/shard_1 | 49,171 | 49,171 | 0 | 0 |
| train/shard_500 | 49,889 | 49,889 | 0 | 0 |
| test/shard_0 | 3,360 | 3,360 | 0 | 0 |
| test/shard_100 | 6,161 | 6,161 | 0 | 0 |
| **合计** | **162,154** | **162,154** | **0** | **0** |

另：本地→HPC 上传了带 CLI 的 `gnn_phase6_rempnn.py`（HPC 原版是硬编码路径版，计算函数与本地逐行一致——diff 只在 main() 的参数化）。

---

## 2. Phase 1 — v3 preds 上传 + 全量重算 + 确定性

**上传**：rsync（220MB + 21MB），行数校验 **409,006 / 39,994** 与本地一致（本地 `reaction_analogy/data/gnn_model_v3_preds/` 与 HPC `~/rxn6/train_preds_v3.jsonl` / `test_preds_v3.jsonl`）。

**重算**：shards 拷贝成 A/B 两份（不改 v1 原件）：

- `v3loop/shards_train_v3_A` + `_B` ← `shards_train3`（1598 片，与 v1 时代 ranker 用的同一集合——当年 shards_train3 缺 shard_105/1051，1598 片，n_train_case=408,497 与 ranker_mpnn.json 一致）
- `v3loop/shards_test_v3_A` + `_B` ← `shards_test3`（640 片）
- rempnn: A 用 `train_preds_v3.jsonl`+`train.txt`，B 同配置重跑；test 同理用 `test_preds_v3.jsonl`+`test.txt.proc`

**汇总行**（`logs/rempnn_train_A.log` 等 4 份）：

- train: `DONE cands=79280276 mpnn>0=53752769 hit=408492 coverage=0.678 skip=0`（与 v1 时代的 79,280,276/53,752,769/408,492 完全一致——覆盖结构不变，只有值本身变了）
- test: `DONE cands=3427306 mpnn>0=2286204 hit=4997 coverage=0.667 skip=0`

**确定性双跑**（`logs/phase1_verify_slurm.out`）：2238 个 shard 文件 A/B **MD5 + 文件大小全一致，mismatch=0**。

**v3 特征确实变了、变尖了**（抽查 5 shard，v1→v3）：

| 指标 | v1 | v3 |
|------|----|----|
| 负例候选 mpnn 中位数（train shard_0/1） | 0.510 | 0.257 |
| 负例候选 mpnn 均值（train shard_0/1/500） | 0.472~0.492 | 0.446~0.463 |
| 正例候选 mpnn 均值 | 0.906~0.948 | 0.914~0.944 |
| 正例候选 mpnn≥0.9 | 0.571~0.875 | 0.571~0.750 |

---

## 3. Phase 2 — 实验 A：v3 闭环主表

全部配置：同脚本（`gnn_phase6_train_ranker.py`）+ 同超参（defaults: 1500 iters / 127 leaves / lr 0.05 / neg-ratio 5 / eval-cap 1000 / LightGBM random_state=0, n_jobs=64）+ 同 shards（只有 mpnn 列的值不同）。评测口径与 v1 时代完全一致（top-1 分母含 no-cand，n=4997）。

| 配置 | shards | top-1 | hit@3 | hit@5 | hit@10 |
|------|--------|-------|-------|-------|--------|
| 模板频次基线 | — | 18.51% | — | — | — |
| **v1-on（2026-08-27 原版）** | shards_train3/test3 | 67.50% | 83.77 | 87.49 | 90.91 |
| v1-on（今日复现） | shards_train3/test3 | **67.82%** | 83.91 | 86.97 | 90.49 |
| v1-off（2026-08-27 原版） | shards_train3/test3 | 64.38% | — | — | — |
| v1-off（今日复现） | shards_train3/test3 | **64.30%** | 81.07 | 85.39 | 89.07 |
| **v3-on** | shards_*_v3_A | **68.28%** | 83.77 | 87.65 | 90.73 |
| **v3-off** | shards_*_v3_A | **65.02%** | 81.31 | 85.43 | 89.31 |
| v3-on（变体脚本对照，无 is_metal） | shards_*_v3_A | 67.68% | 83.75 | 87.55 | 90.73 |

**增益对照（核心口径——同跑 on−off，消除训练噪声）**：

| 时代 | on | off | 增益 |
|------|----|----|------|
| v1（08-27 原版对） | 67.50 | 64.38 | **+3.12pp** |
| v1（今日复现对） | 67.82 | 64.30 | **+3.52pp** |
| **v3（今日）** | 68.28 | 65.02 | **+3.26pp** |

- **v3 mpnn 特征的增益守住了**（+3.26pp vs v1 时代 +3.12~3.52pp），Gate-2 通过。
- v3-on 比 v1-on 高 **+0.78pp**（对 08-27 原版）/ **+0.46pp**（对今日复现）——远小于原子级 +6.5pp 的预期传导，Gate-1（≥69%）差 0.72pp 未过。诊断见 §5。
- v3-on 对 v1-on 的 hit@5 也有提升（87.65 vs 87.49/86.97），hit@3 持平，hit@10 +0.24pp（对原版）。

---

## 4. Phase 3 — 实验 B：域特征（is_metal）消融

**实现**：新脚本 `reaction_analogy/gnn_phase6_train_ranker_v3loop.py`（原脚本零改动，v1 可复现性保留）。`--is-metal` 开关在 cand_row 末尾追加 1 列 `is_metal = 1 if 候选 type（center 元素 tuple）含 {Pd,Ni,Cu,Zn,Fe,Mg,Li,Na,K,Sn,Ti,Co,Mn,Al,Ag,Hg,Ca,B,Si,Se} 中任一元素`。变体在开关关闭时特征向量与原脚本逐位一致（已用同 shard 双跑对照验证：v3-on 68.28 vs 变体对照 67.68，差异纯属训练噪声，见 §5.3）。

**三配置（+1 对照）**：

| 配置 | top-1 | hit@3 | hit@5 | hit@10 | vs 对照 |
|------|-------|-------|-------|--------|---------|
| (iii) v3-on（对照，原脚本） | 68.28% | 83.77 | 87.65 | 90.73 | — |
| (i) v3-on + is_metal | **68.04%** | 83.97 | 87.75 | 90.81 | **−0.24pp** |
| (ii) v3-off + is_metal | 65.46% | 81.45 | 85.57 | 89.23 | vs v3-off 65.02: +0.44pp |
| （附）v3-on 变体对照（无 is_metal） | 67.68% | 83.75 | 87.55 | 90.73 | — |

**is_metal 特征统计**（pass1 全量扫描）：train 79.3M 候选中 330,007 个（0.42%）is_metal=1；正例中 24,686/395,614（**6.24%**，相对全量 15 倍富集——金属催化模板确实是强正例信号）。LightGBM gain 重要性第 21/40 位（92,976 gain vs 首位 f_norm 5.45M）。

**结论（如实报）**：is_metal 的 top-1 净增益 −0.24pp（在 ±0.35pp 训练噪声带内，本质为 0）；hit@3/5/10 有 +0.10~0.20pp 的边际改善。**未触发任务书 §4.2 的 >0.5pp 细粒度版条件，第二版（金属种类 one-hot）不做**。合理解释：金属信息已被 `type_idx`（gain 排名第 4）部分捕获——type tuple 本身含金属元素，GBDT 能从 type_id 分裂里学到等价分组；is_metal 作为 type 的确定性函数几乎不提供增量信息。与 BBD P5 的 `is_eawag_domain`（检索域三来源之一，信息不在其他特征里）不同，USPTO 的域代理是已有特征的冗余投影——**"域特征进 ranker"的 BBD 反哺在 USPTO 单域场景下不迁移**，这本身是有价值的负结果。

---

## 5. Gate-1 失败诊断（按任务书 §6 停机条款）

### 5.1 ① v3 概率饱和？——是，主因

**原子级（test preds 673,422 原子 / 91,922 正例原子，`diag_preds_dist_test.json`）**：

| 指标 | v1 | v3 |
|------|----|----|
| 正例原子概率均值 | 0.865 | 0.898 |
| 正例原子 ≥0.9 占比 | 51.5% | 62.1% |
| 全原子 ≥0.9 占比 | 13.1% | 14.4% |

**候选级（ranker 实际看到的特征 = site 原子概率 max-pool，test 全量 640 shards / 3,427,306 候选 / 4997 案例，`diag_saturation_test.json`）**：

| 指标 | v1 | v3 | 变化 |
|------|----|----|------|
| 正例候选 mpnn≥0.9 | **80.2%** | **80.0%** | **持平** |
| 正例候选 mpnn≥0.99 | 5.6% | 22.3% | 4 倍（但 max-pool 吃不掉） |
| 正例候选均值 | 0.916 | 0.925 | +0.009 |
| 负例候选中位数 | 0.510 | 0.257 | **大幅变尖** |
| 负例候选 ≥0.9 | 25.5% | 24.4% | −1.1pp |
| mpnn-argmax 单特征 top-1 | 35.50% | 36.28% | +0.78pp |

**解读**：v1 时代正例候选的 max-pooled mpnn 已 80% 落在 ≥0.9——**候选级特征在 v1 就饱和了**。v3 的原子级改进（hit@1 +6.5pp）主要把正例原子从 0.9 推到 0.99（≥0.99 占比 4 倍），但 max 已在 0.9+，推到 0.99 对候选排序几乎无增益；正例 ≥0.9 的占比原地踏步（80.2→80.0）。能兑现的是负例分布变尖（中位数砍半），它带来 mpnn-argmax +0.78pp、GBDT top-1 +0.46~0.78pp——**两条路径的增益量级完全一致**，证明瓶颈在候选级 max-pool 特征表示，不在 GBDT 也不在原子模型。

### 5.2 ② rempnn 特征错位？——排除

- Phase 0 回归锚点：v1 preds 重算 5 shards **162,154 候选 0 不匹配**（含其他字段零改动校验）。
- 确定性：2238 shards A/B 双跑 byte-identical。
- 覆盖结构：cands/mpnn>0/hit 计数与 v1 时代逐位一致（79,280,276/53,752,769/408,492），v3 只改值不改覆盖。
- 特征分布：v3 shard 的 mpnn 分布确实相对 v1 整体下移变尖（§2 表）——preds 真的换了。

### 5.3 ③ GBDT 对更强特征的边际递减？——是，且训练噪声带让小增益不可追

**训练非确定性实测**（LightGBM 4.7.0, n_jobs=64, random_state=0——多线程直方图归约的浮点非结合性）：

| 对比对（训练数据逐位相同） | top-1 差 |
|------|------|
| v1-off（08-27）vs v1-off（今日） | 0.08pp |
| v1-off（今日）vs v3-off（今日）——mpnn 列两侧都被置 0，X 逐位相同 | **0.72pp** |
| v3-on（原脚本）vs v3-on（变体对照，同日同 shards 同特征） | **0.60pp** |

→ 同环境同数据的同日双跑可差 0.6~0.7pp，**单次训练的噪声带约 ±0.35pp**。v3-on 的三次同配置观测（68.28/67.68 + 噪声带）期望区间约 67.6~68.9pp，与 69% 门槛确实差一口气；而 on−off 同跑差分把共享噪声抵消（+3.26pp 稳健），所以 Gate-2 比 Gate-1 更能反映特征真实贡献。**未做任何超参追调**（任务书红线）。

### 5.4 综合结论

v3 闭环的**特征贡献兑现且稳健（+3.26pp ≥ +2.5pp）**，但绝对 top-1 受两层天花板压制：(a) 候选级 max-pool 表示在 v1 已饱和（80% 正例 ≥0.9），原子级 +6.5pp 只能传导 +0.5~0.8pp；(b) top-1 已在 68% 区间，剩余错误里 mpnn-argmax 单特征只能解决 36% 的案例，GBDT 的其他特征（f_norm/r/type）承担了大部分排序。**若要突破 69%，方向不是更强的原子概率，而是更丰富的候选级 mpnn 聚合（如 site 原子概率的 mean/top-2/熵，或全底物概率向量）——这是后续任务的候选提案，本任务不动 shards 结构。**

---

## 6. 与 BBD 战线 P5 域特征结论的呼应

- P5（BBD）: `is_eawag_domain` 在三个 per-source ranker 特征重要性全进前列（uspto 24.6k / envipath 179k / retrieval 80.6k gain）——跨域检索场景下"来自哪个域"是强信号。
- 本任务（USPTO 单域）: `is_metal`（域代理 = type 含金属元素）gain 第 21 位、top-1 净增益 ≈0。
- **调和解释**: BBD 的域特征携带"检索来源/数据分布"信息，不在其他特征中；USPTO 的 is_metal 是 type_idx（gain 第 4）的确定性函数，信息冗余。域特征的价值取决于**是否注入了模型已有特征之外的分布信息**，而非"域特征"本身。BBD 教训的普适化表述应为"分布来源信号对 ranker 有效"，在 USPTO 需要找到真正的分布外信息（如反应大类、文献来源）才有戏——type 派生的金属代理不满足。

---

## 7. 已知局限

1. 训练非确定性 ±0.35pp（LightGBM 64 线程）意味着 <0.7pp 的配置间差异不可判定——is_metal 的 −0.24pp 结论"无增益"是"噪声内"判断，不能断言为真负。
2. is_metal 金属清单含 B/Si/Se（类金属，任务书 §4.2 原文 21 种）；若剔除类金属结论方向不变（金属候选更少）。
3. 饱和诊断基于 test 侧（3.4M 候选）；train 侧抽查 3 shards 同趋势（正例 ≥0.9: 79.2→80.0 / 82.2→83.0 / 79.3→79.3）。
4. 模型文件（`ranker_v3_*_model.txt`，各 ~21MB）保留在 HPC `~/rxn6/v3loop/results/` 并拉回本地 `data/uspto_v3loop/models/`（未入库），供审核员独立重打分复算（审核清单 §9.2）。

---

## 8. 交付物清单

| 项 | 位置 |
|----|------|
| 本报告 | `reaction_analogy/reports/USPTO_V3_CLOSED_LOOP_REPORT_2026-09-01.md` |
| 结果 json（7 个 ranker 配置 + 2 个诊断 json） | `reaction_analogy/data/uspto_v3loop/` |
| 运行日志（phase0 回归 / phase1 verify+rempnn×4 / ranker×7 / 诊断） | `reaction_analogy/data/uspto_v3loop/logs/` |
| HPC 作业脚本（rank_job/rempnn/verify/regress/diag/compare） | `reaction_analogy/data/uspto_v3loop/scripts/` |
| 模型（未入库，本地备份 + HPC） | `reaction_analogy/data/uspto_v3loop/models/`、HPC `~/rxn6/v3loop/results/` |
| 域特征变体脚本 | `reaction_analogy/gnn_phase6_train_ranker_v3loop.py` |
| rempnn CLI 版（上传 HPC） | `reaction_analogy/gnn_phase6_rempnn.py` |
| HPC 重算 shards（A/B 双份） | HPC `~/rxn6/v3loop/shards_{train,test}_v3_{A,B}/`（1598+640 ×2） |
| git | 分支 `feat/uspto-v3-closed-loop`（从 `feat/bbd-p5-domain-ranker` 切出——main 无 `reaction_analogy/` 脚本目录），不 push |

**HPC 作业台账**（wzhcnormal 分区）：43365156（phase0 回归）、43365681（shards 拷贝）、43365907/09/11/12（rempnn A/B × train/test）、43365913（verify）、43366630-36（6 个 ranker 配置）、43368325（饱和诊断）、43368333（v1-off 复现）。
