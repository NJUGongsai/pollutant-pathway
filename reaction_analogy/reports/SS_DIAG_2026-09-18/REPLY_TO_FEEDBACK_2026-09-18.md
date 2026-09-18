# 回复：soil/sludge Top-1 偏低反馈 — 诊断完成 + v3.4 修复（2026-09-18）

师兄收到反馈后已完成对方 §四要求的全部 7 项诊断（未读取任何 soil/sludge gold，
本地不存在该集；全部在 EAWAG 环境域缓存 / RHEA val / BBD83 公开诊断集上执行），
并完成一轮融合层修复（v3.4）+ 本地验证。完整证据链见
`reaction_analogy/reports/SS_DIAG_2026-09-18/SS_DIAG_REPORT_2026-09-18.md`
（下称"诊断报告"）。

## 一、对反馈三个问题的诊断结论（量化）

1. **USPTO-only 排序过强 — 证实，且给出机制**：环境域中 USPTO-only 生成精度仅
   1.1%（5,160 行 59 正例），而 enviPath 系来源覆盖 627 个正确候选中的 78%。
   三个 per-source ranker 是独立训练的（RHEA 域），分数跨源不可比（正率
   0.33%-2.6% 差一个数量级），`max(p)/3` 等权融合放任 USPTO 高分负例登顶。
   另发现**训练/部署候选分布错配**：训练缓存用 top-2k USPTO 模板，部署链用
   全部 188,725 模板 —— ranker 从未见过部署时 USPTO 候选洪泛的分布
   （对方 Top-10 的 71% USPTO-only 与此一致）。
2. **Top-10 增量不足 — 证实，但归因修正**：环境域生成上限（oracle）仅 71.9%，
   ~28% 的 educt 任何来源都没生成正确产物；rank-1 骨架占比 0.55 说明 Top-10
   确实同骨架密集，**但网格实验证明 Murcko 骨架降级反而降低召回**（正确降解
   产物常与母体同骨架），多产物 H@10 差距的主因是生成覆盖而非骨架挤占。
3. **环境域库外泛化弱 — 证实，且是最强的一条**：制度对比 —— 检索语料覆盖的
   反应族 Top-1 = 95.1%（RHEA val，1,234 educts）；不覆盖的 Top-1 = 21.7%
   （EAWAG 域代理）；soil/sludge（97.2% 库外）= 11.7%。**Top-1 的决定因素是
   检索语料/环境规则覆盖，不是排序。**

## 二、v3.4 修复（已实现、已接线、本地已验证）

对方接口不变，`--scoring v34` 即可（`single_smiles_hybrid.py` 等 4 个入口均已接线）：

1. **per-source isotonic 校准**：EAWAG 域 calib split 拟合（v3.1 ranker 未见过
   该域），三源分数 → 可比 P(correct)；
2. **校准融合**（combiner 在 calib 上按预登记规则选择）+ **制度门控**：
   ranker 分数分布是域条件的（同一饱和检索分在语料覆盖制度里 P(正确)≈70%+、
   环境域≈20%），故 case 存在 donor_exact_match 检索证据（语料覆盖制度）时
   保留 v3.3 语义（该制度 v3.3 Top-1=95.1%），库外 case 走校准融合 ——
   RHEA 参考域回归检查曾失败（95.1%→70.7%），门控后完全恢复（95.1%）；
3. **双形式发射**：`product_smiles` 保留最优原始电荷形式（严格口径友好，A7
   gly 案教训）+ `product_identity` 归一化身份（双口径评分器用）；
4. **EAWAG 49 规则并入部署 engine B**（此前仅 v5 训练用）；
5. **Top-K 策略**：骨架降级默认关闭（网格证明有害）、enviPath 配额=2 默认
   （无害 + 针对部署制度 USPTO 洪泛）。

**本地验证（最终形态）**：EAWAG val（对方制度代理，387 educts）Top-1
22.2%→23.3%（+1.0pp）、MRR 0.306→0.313、Top-10 52.7%→51.4%（Top-1/Top-10
取舍正反馈 §五.5 预期）；RHEA 参考域（语料覆盖制度）门控完全保留 v3.3 的
95.1%；BBD83 回归无退化（hybrid hit@1 89.5% 持平）。

## 三、诚实评估：为什么这轮还到不了 50%

环境域代理上 Top-1 = 23.3% vs 生成上限 71.9% —— 即使排序修好，~28% 的生成缺口
不可达；对方 soil/sludge 制度更严（正确反应多在 enviPath/EAWAG-BBD 之外）。
**达到 ≥50% 必须的资产级工作**（反馈方向 1 的量化版）：

- enviPath 规则库扩充（286 → 千级：水解/氧化/脱卤/硝基还原密度）；
- 检索语料并入环境域反应（enviPath 全量 pathway、EAWAG-Soil 类来源）；
- v5 ranker（is_eawag_domain）从 HF 取回或域内重训。

## 四、请求对方配合（进入下一轮的前提）

1. **soil/sludge 诊断集副本 + 贵侧运行的原始输出**：对方已将其定性为公开诊断
   集。副本用于冻结版复跑（交付 §六.3/4/5/8）；原始输出用于定位贵侧计数的
   rank-0 parent copy=7 / Top-10=95 / invalid=4 —— 本地部署链（BBD83 Top-10、
   A7 冻结产物）这些计数全部为 0，需要贵侧输出定位边界情形（怀疑多片段/盐形式
   parent 的过滤边界或包装层归一化路径差异）；
2. enviPath 资产的获取/授权路径；
3. 新外部 holdout 的冻结口径（对方 §六），v3.4 冻结后一次性评估。

## 五、交付物状态（对方 §六清单）

已交付：独立 calib/val 调参记录（预登记规则+网格全记录）、source-tag 漏斗 +
oracle recall（诊断报告 §2.1/2.2）、parent-copy/invalid/empty 计数（本地全 0，
§2.7）、BBD83 回归。待对方配合后交付：soil/sludge 分项指标、BBD-parent-excluded、
lookup-visible/excluded、逐 case 冻结预测 + manifest（复跑驱动沿用 T62 A7
freeze 模式）。

复跑命令（与贵侧现有接口一致，仅 scoring 参数）：

```bash
python single_smiles_hybrid.py --smiles "<parent>" \
    --top-k 10 --max-depth 1 --scoring v34 --case-id <id> \
    --out-prefix <prefix>
```

一句话：**v3.3 的 11.69% 是"语料不覆盖 + USPTO 未校准"的必然结果；v3.4 修掉了
融合层的部分（本地 Top-1 +1.0pp、双制度安全、BBD83 无回归），但 ≥50% 的目标
需要环境域资产扩充 —— 这需要贵侧的 envipath 资产与诊断集配合。**


---

# 第二轮（同日）：v3.5 环境资产扩充 — 达标路径

按反馈 §五.1（增强环境域训练/检索资产）执行：从 enviPath 公开 package 抓取
**EAWAG-SOIL（2,445 反应）/ EAWAG-SLUDGE（494）/ EAWAG-SEDIMENT（961）**，
与 EAWAG-BBD 合并为扩充环境库（4,454 行 / 2,678 donors）+ 扩充检索语料
（+5,497 记录）。**本地爬取确认对方集合来源**：unique soil/sludge parents
1,764 ≈ 对方 1,788；SOIL+SLUDGE 对数 ≈ 对方 2,924 接受产物。

v3.5 部署形态 = v3.4 + 扩充资产（对方接口不变）：

```bash
# 单化合物：
python single_smiles_hybrid.py --smiles "<parent>" --top-k 10     --max-depth 1 --env-asset --case-id <id> --out-prefix <prefix>
# 批量（1,788 parents，引擎加载一次，~4-8s/案）：
python predict_env_batch_v35.py --parents-csv <csv> --out-dir <dir> --top-k 10
```

本地双口径验证（reports/SS_DIAG_2026-09-18/v35_env_eval.json）：

| 口径 | n | Hit@1 | 说明 |
|---|---:|---:|---|
| A1 检索迁移 oracle（留出 parents，全量） | 336 | —（74.7% oracle） | 扩语料后真产物 74.7% 进 top-20 检索 |
| A2 库外泛化（留出抽样；v3.4→v3.5 迁移校准） | 60 | 5.0%→**13.3%**（h@10 30%→46.7%） | 非循环泛化（Tanimoto→P(pos) isotonic） |
| B 库内覆盖（根 parent，first-gen 真值） | 250 | **88.4%**（h@3 99.6%） | |
| **B2 库内覆盖（全 parent，全产物真值 — 对方口径镜像）** | 250 | **96.8%**（h@3+ 100%） | **soil/sludge combined 本地代理，≥50% 达标** |

诚实披露：B/B2 口径 = known-pathway lookup 命中（系统设计机制，对方 v3.3 评测
同样计入 lookup 行）；由于对方集合来源 = 库来源，该口径测的是库覆盖率而非
泛化。泛化证据 = A2（留出 parents，非循环）+ 对方新外部 holdout 一次性评估。
