# reaction_analogy — BBD 降解产物预测引擎（evaluation candidate）

> **定位**：本目录是 depending（EnzymeCrew）仓库「板块③ — 反应预测引擎候选」的实现载体，
> 开发者为师兄（`feat/bbd-uspto-integrated`，merge `102e5c6` 合入 main）。
> **合并代码 ≠ 默认引擎**：`reaction_prediction` MISS 后的正式 predictor 选型待 **T6-2 裁定**
>（对照候选：BioTransformer ENVMICRO）。本目录代码**不在**主管线的默认 predictor 路径上。

## 1. 用途：这套东西做什么

**BBD（生物降解产物）预测**：给定一个污染物母体分子的 SMILES，输出它可能的微生物降解产物
（rank-1 首步产物 + 多步路线），每条候选带来源、分数与审计字段。它在整条
「底物 → 反应 → 酶 → 菌」链路里对应 **`reaction_prediction`** 节点的 fallback 角色——
当基于相似性的反应检索（route_b/route_c）MISS 时，由预测引擎直接给出候选反应。

系统为**两层混合架构**：

| 层 | 机制 | 数据 |
|---|---|---|
| **Layer 1 查表** | EAWAG-BBD 已知途径 lookup（donor 精确匹配 → 每条记录产物入池，Tanimoto 排序） | `data/bbd_expand/donor_product.jsonl`（1,066 反应 / 859 donors） |
| **Layer 2 预测** | 三引擎生成 + LightGBM ranker 重排 | ① USPTO 188,725 图编辑模板（graph-edit templates） ② enviPath 286+49 规则（SMARTS/SMIRKS，RunReactants） ③ RHEA 37k 检索语料（相似反应迁移） |

**三个口径**（引用成绩时必须注明）：hybrid（查表+预测，对外权威口径）、prediction-only（闭卷，
测自研引擎真实水平）、lookup-only（纯查表上限）。详见 §3。

## 2. 版本谱系（哪个是当前最佳）

| 版本 | 关键增量 | strict Hit@1 / Hit@10（86 可评案例） | 状态 |
|---|---|---|---|
| v1/v2 | 单引擎（MPNN 概率 + 检索池） | 10.5% / 22.1% → 22.1% / 57.0% | 历史版本 |
| v3 | 生成式引擎引入（USPTO 模板 + enviPath 规则） | 25.6% / 60.5% | 历史版本 |
| v3.1 | per-source ranker（uspto/envipath/retrieval 三个 LightGBM），触发器 | 27.9% / 68.6% | 厹史版本 |
| v3.2 | ion 白名单 28 物种、cofactor SMARTS+MW>500、wildcard 沉底、全精度 ns_score | 33.7% / 68.6% | 历史版本 |
| **v3.3** | **v3.3 融合层**：电荷归一化身份（RDKit Uncharger）、来源一致性加成 ×(1+0.15·(n_sources−1))、骨架合理性检查 ×0.70、lookup 键电荷归一化 | **37.2% / 76.7%**（prediction 闭卷） | **纯预测线当前最佳** |
| P4.2 | 两层混合架构（lookup 置顶） | 90.7% / 96.5%（hybrid） | 已被 v5 取代 |
| **P5.1 (v5)** | v5 ranker（28 维 is_eawag_domain 特征）+ EAWAG 规则引擎 + tiebreak | **89.5% / 95.3%（hybrid，对外权威）** | **对外口径当前最佳** |

> 阅读指引：**"当前最佳"分两条线**——纯预测线（闭卷能力）看 v3.3；对外引用成绩看 v5 混合口径
>（`bbd_predictions/bbd_hybrid_eval_v5.json`）。hybrid 的高分主要来自 lookup 层（87/93 库内命中），
> 库外新污染物会退化到预测线水平（DBP 案例：首步 MBP rank-1 由 v3.3 融合层修复达成）。

**为何对外口径用 v5（89.5%）而不用更高的 P4.2（90.7%）**：两者评测集、stereo 匹配口径、
lookup 库内命中范围（87/93）完全相同，差异**只**来自 Layer 2 的 ranker 换代（v3.1 → v5 ranker，
重训含 RHEA+EAWAG 混合集与 28 维 `is_eawag_domain` 特征）。v5 ranker 的重训是一次显式权衡：
**用 top-1 精度换 top-10 召回**（prediction 口径 H@1 −1 case，H@10 +7 case，见 P5 报告 §3.1——
5 个正确产物进入 top-10，2 个原 rank-1 产物移至 rank 2–5）。hybrid 口径的净效果是 78→77
（−1），具名案例 c0236（DMSO → 甲基硫醚）：P4.2 rank-1，v5 里 truth 掉到 rank-5，被一条
结构荒谬的长链检索假阳性顶掉。**定 v5 为权威的原因**：(a) v5 是后续发展线（v5 ranker +
EAWAG 规则引擎 + tiebreak 是 T6-2 裁定时要拿出去与 BioTransformer 对比的形态，P4.2 的
v3.1 ranker 已不是演进方向）；(b) 闭卷 prediction 口径 v5 大幅更好（H@10 68.6%→76.7%），
库外场景（lookup miss 时）鲁棒性显著更强——hybrid 的 −1 case 是 lookup-miss 案例暴露在
Layer 2 差异下的结果，这恰是 hybrid 指标无法反映的分层信息；(c) 89.5% 与 90.7% 的差
（1 个 case）在 n=86 下不构成统计显著。若老师侧裁定需要"最高分版本"，P4.2 全套产物
（`bbd_hybrid_eval.json`）保留在库可随时切换口径。

## 3. 成绩口径（对外一律以此为准）

**`bbd_predictions/bbd_hybrid_eval_v5.json` — Hit@1 89.5% (77/86) / Hit@10 95.3% (82/86) / MRR@10 0.919。**

- **评测集**：BBD83 盲测包 v0.3（`bbd_known_pathway_full_route_v0_3_candidate_v3_1_strict_blind_fix_20260821/blind/`），
  93 个 blind parent，经 v0.2 restricted answer key stereo-blind 匹配得 86 个可评案例
  （另 7 个 blind parent 在 v0.2 key 中无对应记录，只计池召回不计分）。
- **统计方法**：Hit@K = 任一 top-K 产物与答案 key 严格匹配（stereo-blind canonical SMILES）。
  stereo-blind = 忽略立体异构、保留电荷与组成；泄漏纪律：84/90 blind parent 是 EAWAG donor
  （已从训练集排除），answer key 只允许评分器读取，预测器/ranker/lookup 永不读。
  一次性评测（one-shot），无对 key 调参。
- **同目录各历史版本产物**（v2/v3/v3.1/v3.2/v3.3 eval json）仅作审计证据链保留，**不用于对外口径**
  （红线：历史版本成绩不对外）。

## 4. 依赖与运行入口

**外部依赖**：Python 3.10+、RDKit、LightGBM、scikit-learn、pandas。语料数据：
EAWAG-BBD 途径库（donor_product.jsonl）、enviPath 模板（`../reaction_v3/data/lib_envipath/`，
含 `templates.tsv.gz`）、USPTO 模板（hfix 重建，M4-A）、RHEA 141（37k RXN）。
**不依赖** GPU/MPNN（BBD 域 MPNN 微调试水结论 No-Go，见
`reports/BBD_MPNN_TRIAL_REPORT_2026-08-31.md`；MPNN 侧资产仅活在 USPTO v3 线）。

**入口脚本（按使用场景）**：

```bash
cd reaction_analogy
# ① 单分子预测（混合口径，推荐）——lookup + v3.3 预测，真实多步 BFS
python single_smiles_hybrid.py --smiles "<SMILES>" --top-k 10 --max-depth 3 \
    --case-id <ID> --out-prefix <前缀>
# ① 单分子预测（纯预测/闭卷）——v3.3 融合层
python single_smiles_v32.py --smiles "<SMILES>" --top-k 10 --max-depth 3 \
    --case-id <ID> --out-prefix <前缀>
# ② 批量盲测（混合口径 93 案）：预测 + 评分
python predict_bbd_hybrid.py --rankers data/bbd_v5/rankers --eawag-rules data/bbd_expand/rules_new_clean.jsonl \
    --tiebreak on --out-preds <p.jsonl> --out-pool <pool.jsonl> --out-pred-pool <pp.jsonl> --out-report <r.json>
python score_bbd_hybrid.py calibers_v5 --preds <p.jsonl> --pool <pool.jsonl> --v32-pool <pp.jsonl> \
    --answer <restricted key path> --stereo blind --json-out <eval.json>
# ③ ranker 重训（完整链条见 P5 报告 §repro）
python build_bbd_train_v2.py --procs 8      # EAWAG 训练缓存
python train_bbd_ranker_v2.py --out-dir data/bbd_v5
# ④ v3.3 单元测试
python reports/DBP_V33_RERUN_2026-09-14/test_bbd_v33_fusion_unit.py
```

**版本目录索引**：`reports/` 下每个版本有交付报告（`BBD_V2_REPORT` → `BBD_V33_FUSION_FIX`），
`data/` 下有对应训练/语料产物（corpus_v1、bbd_v5、bbd_expand 等）。历史脚本命名规律：
`*_v2 / *_v3 / *_v31 / *_v32 / *_v33` 后缀 = 该版本冻结的入口，v3.2 与 v3.3 通过 `--scoring v32|v33`
开关共存于 `predict_bbd_products_v32.py` / `expand_bbd_routes.py`（默认 v33，v32 保留用于复现历史）。

## 5. License

**自研声明**：本目录代码（v2→v3.3 全套训练/预测/评分脚本）为**弓赛自研**，无上游开源项目
（非 EnzymeCAGE v1 的衍生，也不是 enviPath/BioTransformer 的衍生——三者仅作**数据/工具被引用**）。
许可沿用仓库根 LICENSE（`assets/enzyme_cage_v1/` 的 CC-BY-NC 4.0 只覆盖底座模型代码，
不覆盖本目录）。

**数据来源与引用边界**（数据 license 属于各自发布方，非本仓库可再授权）：

- EAWAG-BBD 途径数据：公共学术数据库，仅作输入数据引用
- enviPath 模板（`reaction_v3/data/lib_envipath/`）：源自 enviPath 项目发布物，仅作输入引用
- USPTO 模板（hfix 重建）：源自 USPTO 专利反应数据（50k LT + MC 数据集传承），仅作输入引用
- RHEA 141：CC-BY-4.0 数据库，仅作输入引用
- **约束**：涉及本目录代码复用扩散的范围问题（与 CC-BY-NC 底座的边界），在老师侧确认
  license 声明前不扩散（任务清单红线 §四）。

---

**产物索引**：评测输出在 `../bbd_predictions/`（对外权威：`bbd_hybrid_eval_v5.json`）；
训练数据在 `../data/bbd_v3|v31|v32|v5/`；交付报告在本目录 `reports/`（含 DBP 考题三份报告、
P4/P4.1/P4.2/P5 里程碑报告、MPNN No-Go 决策报告）。
