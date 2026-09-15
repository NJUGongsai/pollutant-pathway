# 弓赛侧任务完成报告（三模块集成 · 师兄线）

**收件**：老师 / 师兄线
**发件**：弓赛（`Frankgonghahaha`）
**日期**：2026-09-15
**对应任务清单**：`task_gongsai_2026-09-15(1).md`（2026-09-15 版，含任务 3 升级为"HF dataset 移出"）

---

## 总览

| 任务 | 状态 | 一句话结果 |
|---|---|---|
| 1 切 main + 确认资产 | ✅ 完成 | main = `e07bc77`（快进 33 commits），四大资产目录完整，无分叉 |
| 2 `reaction_analogy/README.md` | ✅ 完成 | 五节齐备（用途/谱系/口径/依赖/license），候选引擎口径与根 README 对齐 |
| 3 数据资产移出（HF dataset） | ✅ 建议完成 | 三个确认问题已答（见 §3），等 T6-2 后执行迁移，迁移命令已备好 |
| 4 T6-2 材料 | ⚠️ 就绪但缺件 | **A7/gold 18 条冻结包未收到**，评分框架/口径/增量表已备齐，包一到即可出数 |

---

## 任务 1 — 切 main + 资产确认（收到即做）

### 1.1 执行结果

```text
git fetch origin
git checkout main && git merge --ff-only origin/main   # ccb4667 → e07bc77（+33 commits，纯快进，0 分叉）
```

快进过程中遇到一个本地障碍并安全解决：本地 main 上有 32 个**未跟踪**文件与 origin/main
要创建的跟踪文件同名（`bbd_predictions/*.jsonl`、`assets/enzyme_cage_v1/*`——它们此前只在
`feat/bbd-uspto-integrated` 上提交，合并进 main 后本地 main 工作树里还是未跟踪副本）。
处置：tar 备份 + 逐文件 git hash 比对——31/32 与远端逐字节一致，唯一差异
`bbd_product_pool_v32.jsonl` 本地为零字节空文件（中断残留），远端为真内容（7.8MB），
让合并落地远端版本即为恢复。现 `main` 与 `origin/main` 完全同步，工作树干净（仅剩
从未跟踪的本地文档目录）。

### 1.2 资产清点（任务清单 §一 的四目录逐项核对）

| 目录 | 状态 | 备注 |
|---|---|---|
| `reaction_analogy/` | ✅ 完整 | v2→v33 全套训练/预测/评分脚本 + `eawag_lookup.py`（含 9-14 电荷键修复）+ `bbd_v33_fusion.py` + `single_smiles_hybrid.py` + 39 份报告 |
| `reaction_v3/data/lib_envipath/` | ✅ 完整 | 含 `templates.tsv.gz`（T2 补件 a8d1fc4 修过嵌套 repo 静默 add 失败） |
| `data/bbd_v3/v31/v32/v5/hfix` | ✅ 完整 | ranker 模型/训练数据/候选缓存均在 |
| `bbd_predictions/` | ✅ 完整 | 29 个跟踪文件，71.6MB；权威结果 `bbd_hybrid_eval_v5.json` 在位 |

### 1.3 后续工作模式确认

按任务清单要求：**后续 BBD/USPTO ranker 推进直接在 main 上做**，`feat/bbd-uspto-integrated`
（`32e5748`）保留作历史归档不再堆 commit。本人无独立实验线需求，无需另定合并节奏——
唯本地未跟踪的过程文档目录（`CC/` 任务书等）不进 repo，沿用现状。

### 1.4 需老师侧知悉的两点

1. **同事 e07bc77 清理对我线产物的影响**：删除了 `reaction_analogy/reports/DBP_*/` 下
   4 个文件——两个 DBP 大运行原始 JSON（`dbp_hybrid_RAW_STDOUT.json`、
   `dbp_hybrid_v3_RAW_STDOUT.json`，各 ~6MB）。**报告 md、CSV、RUN_META 全部保留**，
   原始 JSON 仍完整存于 git 历史（`32e5748`）可 `git show` 溯源。我认为该清理符合
   repo 卫生方向（过程性大文件不入 main），无需恢复，特此报备。
2. **merge commit `102e5c6` 验证**：`git log -1 --format=%p 102e5c6` = `1925785 32e5748`，
   双 parent 确认无误，feat 线 33 个 commit 全部合入。

---

## 任务 2 — `reaction_analogy/README.md`（已写入）

覆盖原有陈旧草稿（ReactionAgent 时代文档，描述的是已被 P0-P9 链取代的路线甲架构，
已备份 `/tmp/README_routeA_stale_draft_backup.md` 后重写）。五节要点：

1. **用途**：BBD 降解产物预测（母体 SMILES → rank-1 首步产物 + 多步路线），两层混合
   架构（Layer 1 EAWAG lookup / Layer 2 三引擎预测），在主管线中对应
   `reaction_prediction` fallback 角色，**evaluation candidate，非默认引擎**（T6-2 待裁定）。
2. **版本谱系**：v1(10.5%) → v2(22.1%) → v3(25.6%) → v3.1(27.9%) → v3.2(33.7%) →
   v3.3(37.2% prediction 闭卷) → P4.2 hybrid(90.7%) → **v5 hybrid(89.5%，对外权威)**。
   明确"当前最佳"双线：纯预测线 v3.3 / 对外引用线 v5。
3. **成绩口径**：`bbd_predictions/bbd_hybrid_eval_v5.json` 为准（89.5%/95.3%/MRR 0.919）；
   评测范围（BBD83 盲测 v0.3，93 parent，stereo-blind 匹配 v0.2 key 得 86 可评）、
   统计方法（Hit@K 严格匹配、泄漏纪律、one-shot）。
4. **依赖与入口**：RDKit/LightGBM；四个场景入口（单分子 hybrid / 单分子纯预测 /
   批量盲测 / ranker 重训），`--scoring v32|v33` 开关说明。
5. **License**：**自研声明**（非 EnzymeCAGE v1 衍生、非 enviPath/BioTransformer 衍生，
   三者仅作数据/工具被引用）；数据来源引用边界（EAWAG/enviPath/USPTO/RHEA 属各自
   发布方 license）；在老师确认前不扩散复用范围（任务清单红线）。

---

## 任务 3 — 数据资产移出代码仓（HF dataset 方案）

### 3.1 老师三个确认问题的回答

**Q1：这些数据你是否已在本机/晨羽有原始副本？**
**✅ 是，全部有**。本机（`/Volumes/CC/Enzyme_Agent/depending`）就是这些数据的**产生现场**——
评测结果是本地运行产出的原件，语料库（corpus_v1）/EAWAG 候选（eawag_candidates.jsonl）/
ranker 模型都是本地构建的。晨羽侧无需另存（构建脚本在 repo 内可重跑，但 12 分钟+8 分钟，
HF 缓存更稳）。**结论：git 里这份是冗余副本，可安全移出。**

补充一个测量口径供决策：任务清单说"约 230M 数据资产"指的是 **git 跟踪**的部分（
`bbd_predictions/` 71.6MB + `data/` 65.6MB + `reaction_analogy/data/corpus_v1/` 59MB 等）。
本地盘上 `bbd_predictions/` 目录还有 **756MB 未跟踪**的运行副本（`bbd_route_edges.jsonl`
342MB、`bbd_route_submission/` 349MB——从未进 git，不构成 repo 负担，移仓不受影响）。

**Q2：历史版本（v2/v3/v31/v32）是否还有引用需求？**
- **`bbd_hybrid_eval_v5.json` 及 v5 配套产物（pool/preds/report）**：对外权威 + T6-2 裁定
  材料，**必须保留引用**（建议保留在 git 或 HF 双份）。
- **v3.2 全套**（product_pool_v32 等）：v3.3 的回归基线 + `--scoring v32` 复现路径，
  **有引用需求**（T6-2 材料里 v3.2/v3.3 对比要用）。
- **v2/v3/v3.1**：谱系证据链价值，无运行时引用。**可归档**（HF 移出后 git 里删即可，
  历史在 git log 里永远可溯）。
- **`bbd_route_submission/`（P4 路线提交包）+ `bbd_route_edges/nodes.jsonl`**：
  给测试部门师兄的下游评分包，师兄已消费完毕（DBP 考题反馈 2026-09-12 已回）。可归档。

**Q3：HF dataset repo 由你侧建还是老师侧统一建？**
**建议老师侧统一建**（`WQRCE/EnzymeCAGE-bbd-data`），理由：(a) 和底座权重
`WQRCE/EnzymeCAGE-v1` 同 org 同步管理，访问控制一致；(b) 我侧无 HF org 权限。
我侧负责：把待移数据打包 + 写 dataset README（版本谱系 + 目录索引 + sha256 MANIFEST），
交老师侧上传。数据清单和打包命令见 §3.2。

### 3.2 迁移清单（等 T6-2 裁定后执行，命令已备好）

| 数据 | git 路径 | git 内大小 | 去向 |
|---|---|---|---|
| 评测结果 v2→v5 | `bbd_predictions/`（29 个跟踪文件） | 71.6MB | HF dataset（v5 保留 git 双份可选） |
| 语料库 | `reaction_analogy/data/corpus_v1/` | ~59MB | HF dataset |
| EAWAG 候选 | `data/bbd_v5/eawag_candidates.jsonl` | ~57MB | HF dataset |
| ranker 模型产物 | `data/bbd_v3/ranker_model.txt` + `data/bbd_v31/*.txt` | ~8MB | HF（跟权重走） |

迁移后代码侧需要一处小改：predict/score 入口的数据默认路径参数化（`BBD_DATA_ROOT`
env var，缺省回退本地路径），这样 repo clone 后指向 HF 缓存目录即可跑通。这项改动
约 10 行，T6-2 裁定后一并做。

---

## 任务 4 — T6-2 裁定材料（就绪，缺 A7/gold 冻结包）

### 4.1 缺件声明（阻塞项）

任务清单要求"v3.2/v3.3 在 **18 条 blind（A7/gold 冻结包）** 上的评分口径与结果"。
**该冻结包未收到**：本机（repo、微信文件、Downloads）均无 A7/gold 命名的 18 条包；
仓库内盲测资产是 BBD83 v0.2/v0.3 包（83/93 案），与"18 条 A7/gold"对不上。
**请师兄/老师下发该包**（或指认其等同物），包到当日即可出评分表（运行 15s + 评分 20s）。

**就绪状态**（包一到即跑，无需任何开发）：

```bash
# A7/gold 包到位后（假设提供 parent CSV + restricted answer key）：
cd reaction_analogy
# 单分子逐条（若包是 18 个 SMILES）：
python single_smiles_hybrid.py --smiles "<smi>" --top-k 10 --max-depth 3 --case-id <id> --out-prefix <prefix>
# 批量（若包是 CSV 格式，走既有盲测链）：
python predict_bbd_hybrid.py --rankers data/bbd_v5/rankers --eawag-rules data/bbd_expand/rules_new_clean.jsonl \
    --tiebreak on --out-preds <p.jsonl> --out-pool <pool.jsonl> --out-pred-pool <pp.jsonl> --out-report <r.json>
python score_bbd_hybrid.py calibers_v5 --preds <p.jsonl> --pool <pool.jsonl> --v32-pool <pp.jsonl> \
    --answer <A7/gold answer key> --stereo blind --json-out <eval.json>
```

**与 BioTransformer 同口径可比的关键**：我们的评分器接受任意 answer key 路径（CLI 参数），
Hit@K = stereo-blind canonical 严格匹配，评分器是唯一 key 读者（隔离纪律与 BBD83 相同）。
若 BioTransformer 侧口径为 charged/非 stereo-blind，`--stereo strict` 可切换，双口径同报。

### 4.2 v3.3 相对 v3.2 的增量点及实质影响（可先行裁定参考）

| 维度 | v3.2 | v3.3 | 实质影响 |
|---|---|---|---|
| **身份层** | raw canonical 去重（中性 MBP 与其羧酸根身份分裂） | 电荷归一化身份（RDKit Uncharger），lookup 键同步归一 | 中性/离子变体合并为单候选，证据集中（146 对合并）；库内阴离子 donor 可达（新增命中） |
| **评分层** | `ns = max(p_source)/3`，无跨源约束 | + 来源一致性加成 `×(1+0.15·(n_src−1))` 上限 1/3 | uspto+envipath 双来源候选置顶（如 DBP 首步 MBP） |
| **合理性** | 无 | 骨架检查（键级松弛子结构匹配 + 碎片归还归类），未解释丢失 ×0.70 + 审计字段 | 无降解依据的"高温重排"类错误产物降权（DBP 旧 Top-1 → Rank-2 带标记） |
| **多步** | 单步（旧包装只调一次引擎） | 真实 BFS（{1:1, 2:5, 3:22}）+ PRIMARY 级联 + Top-3 诊断路线 | DBP→MBP→PTA→二氢二醇 全链路可恢复 |
| **lookup 键** | raw stereo-blind（阴离子 donor 不可达） | 电荷归一化键 + 原始指纹排序（身份/相似度解耦） | PTA 上 EAWAG 记录反应置顶；93 案回归无变化（89.5%/95.3% 持平） |
| **成绩** | 33.7% / 68.6%（strict 闭卷） | **37.2% / 76.7%**（strict 闭卷）；hybrid 89.5%/95.3% 持平 | 闭卷 +3.5pp / +8.1pp；hybrid 口径不回退 |
| **DBP 考题** | 4 项全败（2026-09-12 反馈） | 全过（PRIMARY 化学正确 + lookup 证据） | 外部（测试部门）独立验证闭环 |

**诚实披露**：v3.3 的融合常数（0.15/0.70）为先验化学参数，未对基准拟合；v3.3 提升集中在
身份/打分/审计层，三个 LightGBM ranker 本身未动（模型级修复——ranker 重训时加入骨架
合理性特征——列为后续工作）。MPNN 在 BBD 域已盖棺 No-Go（`BBD_MPNN_TRIAL_REPORT_2026-08-31.md`），
v3.3 无 GPU 依赖。

### 4.3 T6-2 裁定的补充视角（供参考，非决定项）

- **vs BioTransformer ENVMICRO**：BioTransformer 是 EAWAG 规则系统（SMARTS 命中 + SMIRKS
  变换）。我们与它的重叠部分恰是我们的 Layer 1（EAWAG lookup）+ enviPath 引擎；差异在于
  我们还有 USPTO 模板引擎 + RHEA 检索 + ranker 融合，且全部输出带 provenance 审计字段。
  18 条 blind 上的同口径对比是决定性证据，建议包到位后双引擎同跑。
- 我们线自身最大短板（已在 README 披露）：库外污染物退化到 37.2% 闭卷线（hybrid 高分
  主要来自 lookup 库内命中 87/93）。T6-2 材料里会如实带这一条。

---

## 红线自查

| 红线 | 执行 |
|---|---|
| 不在 main 里把 `reaction_analogy/` 设成默认 predictor 路径 | ✅ 本次改动只有 README（文档）+ 本报告，未碰 `src/` 编排层；README 自身声明"evaluation candidate, 非默认引擎" |
| 历史版本成绩不用于对外口径 | ✅ README §3 + 本报告全部锚定 `bbd_hybrid_eval_v5.json`（89.5%/95.3%），历史版本标注"仅审计证据链" |
| license 未确认前不扩散复用范围 | ✅ README §5 明确"老师确认前不扩散"；自研声明已写入 |
| answer key 隔离 | ✅ 本轮只读 restricted key 于本地评分运行（评分器唯一读者），未写入任何将提交的文件 |
| 不 push 未经确认 | ✅ 本次仅本地 commit（README + 本报告），**未 push**——等老师确认后由本人推 main |

## 交付物

| 文件 | 类型 | 位置 |
|---|---|---|
| `reaction_analogy/README.md` | 任务 2 交付 | 本次 commit |
| 本报告 `TASK_GONGSAI_COMPLETION_REPORT_2026-09-15.md` | 任务 1-4 汇总 | 本次 commit |
| A7/gold 评分就绪命令链 | 任务 4 | 本报告 §4.1（待包） |
| 数据迁移清单 + HF 方案 | 任务 3 | 本报告 §3.2（待 T6-2） |

## 待老师/师兄侧输入

1. **A7/gold 18 条冻结包下发**（任务 4 唯一阻塞项）。
2. Task 2/3/4 DDL 确认（清单标注"待老师定日期"）。
3. HF dataset repo 谁建的裁定（我建议老师侧统一建，见 §3.1 Q3）。
