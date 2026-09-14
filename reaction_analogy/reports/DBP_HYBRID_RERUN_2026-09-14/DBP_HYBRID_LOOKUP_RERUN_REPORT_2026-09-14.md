# DBP 混合口径（lookup 开启）复测报告 — 回应测试部门 2026-09-12 诊断

**日期**: 2026-09-14
**收件**: 测试部门（DBP 诊断报告作者）
**对象**: depending BBD v3.2/v3.3 单污染物路线预测，**混合口径**（EAWAG known-pathway lookup 层 + v3.3 预测兜底）
**前置**: 《DBP路线预测结果与问题总结》（2026-09-12）、《BBD_V33_FUSION_FIX_2026-09-14.md》（纯预测口径修复）

---

## 一句话结论

按你们的要求开启 lookup 层对 DBP 做了完整复测（`--top-k 10 --max-depth 3`，混合口径入口 `single_smiles_hybrid.py`）：**PRIMARY 级联现在恢复教科书路线 DBP → MBP → 邻苯二甲酸 → 2-甲酰苯甲酸，且每步 rank-1**。需要诚实说明的一点：**DBP 本身不在 EAWAG 已知反应库（1,066 个 donor）中**——所以 DBP 这个具体分子上 lookup 层 depth-1 未命中，本次结果的主体仍由 v3.3 预测层贡献；lookup 层的价值在**后续深度**（邻苯二甲酸及其下游是 EAWAG 收录分子）与**库内污染物**。这与 README 声明的混合口径 89.5%/95.3% 的语义一致：那个数字的 94% 命中来自 93 案盲测集中 parent 恰在 EAWAG 库内的 case；DBP 是库外分子，属于"混合系统的闭卷部分"。

## 1. 本次运行参数（与你们的冻结链口径一致 + lookup）

```text
入口: reaction_analogy/single_smiles_hybrid.py（新增，接口同 single_smiles_v32.py）
输入: CCCCOC(=O)c1ccccc1C(=O)OCCCC（DBP，与冻结链同一 SMILES）
top_k=10, max_depth=3, scoring=v33
lookup 层: EAWAG donor_product.jsonl 全量索引（859 donor / 1,066 反应）
运行时间: ~14 分钟（含三引擎逐级展开; 单纯 depth-1 约 50 秒）
exit_code=0
```

## 2. 结果对照（三轮: 你们冻结的 v3.2 → v3.3 修复 → 本次混合口径）

| 指标 | 冻结 v3.2（你们的报告） | v3.3 纯预测（修复报告） | **本次混合（lookup on）** |
|------|----------------------|----------------------|------------------------|
| Rank 1 | `…c1ccccc1C`（无依据重排）0.2639 | **MBP（中性）** 0.2117 | **MBP（中性）** 0.2117（不变） |
| Rank 2 | MBP carboxylate 0.1841 | 旧错误产物 0.1847（带骨架标记） | 同 v3.3 |
| charge-normalized Hit@1 | 0 | 1 | 1 |
| 多步展开 | `{1:1}`（未展开） | `{1:1,2:5,3:21}` | `{1:1,2:5,3:22}` |
| PRIMARY 级联 | 错误邻域 | MBP → PTA → 2-formylbenzoic acid | **MBP → PTA → 2-formylbenzoic acid（同，每步 rank-1）** |
| 含 PTA 的完整路线 | 0 | 有（TOP3 之一） | **25 条** 3-step 路线含 PTA |
| lookup 层作用 | —（未接入） | —（纯预测口径） | depth-1 未命中（DBP 库外）; depth≥2 检索层已含 EAWAG 语料 |

**关于 Rank 1 为什么和 v3.3 修复报告相同**: lookup 层未在 depth-1 命中（见 §3），所以混合口径的 depth-1 排序 = v3.3 纯预测排序。这不是回归，是 DBP 库外身份的必然结果。

## 3. 关键事实: DBP 在 EAWAG 库内的身份核查（本次新增的透明度）

对 1,066 个 EAWAG 反应的 donor 索引做了三级匹配:

```text
DBP 立体盲 canonical:  CCCCOC(=O)c1ccccc1C(=O)OCCCC
精确匹配:              ✗ 不存在
电荷归一化匹配:        ✗ 不存在
最相似 donor（Tanimoto 0.351）: CC(C)OC(=O)c1ccccc1O（异丁基水杨酸单酯）
含邻苯二甲酸骨架的 donor: 65 个（邻苯二甲酸本身在库: bt0367 双加氧酶反应）
```

**解读**: DBP 属于"库外新污染物"——这正是 93 案盲测集之外的泛化场景。混合口径对它的行为退化到纯预测口径（v3.3），这本身是系统设计的正确行为（lookup 是查已知，不是猜未知）。**你们选择 DBP 做测试，恰好测到了混合系统的闭卷部分**——这个测试设计对评估泛化能力很有价值。

## 4. 对你们 2026-09-12 报告 §5 六条建议的逐条回应状态

| # | 你们的建议 | 状态 |
|---|-----------|------|
| 1 | 确认 Rank-2 MBP 为何低于 Rank-1 | ✅ 已修（v3.3 融合层: 电荷归一化身份合并 + 双来源加成 + 骨架合理性惩罚; 详见修复报告 §1） |
| 2 | 统一中性/离子产物身份 | ✅ 已修（生成/去重/排序/评价/路线展开五层统一; 146 对变体合并; 评价双口径同报） |
| 3 | 检查深度展开 | ✅ 已修（`{1:1,2:5,3:22}`; 根因是旧包装脚本只调一次引擎） |
| 4 | 通用反应合理性诊断 | ✅ 部分已修（骨架收支检查 + unexplained 归因审计字段; 原子映射级反应中心分析列为后续） |
| 5 | 训练域权重分析 | ◐ 诊断完成（USPTO ranker 首特征是模板频次 → 高频合成模板压过环境先验; 模型级重训列为后续） |
| 6 | 保留 Top-k 而非只传 Top-1 | ✅ 已提供（`*_TOP3_DIAGNOSTIC_ROUTES.jsonl` / 本次 `_RAW_STDOUT.json` 的 routes 字段; PRIMARY 仍按预注册 rank-1 规则，供对照） |

## 5. 复跑命令（混合口径，冻结链兼容输出命名）

```bash
cd /Volumes/CC/Enzyme_Agent/depending/reaction_analogy
python single_smiles_hybrid.py \
    --smiles "CCCCOC(=O)c1ccccc1C(=O)OCCCC" \
    --top-k 10 --max-depth 3 --case-id DBP \
    --out-prefix reports/DBP_HYBRID_RERUN_2026-09-14/dbp_hybrid
```

输出（已随本报告归档于 `reports/DBP_HYBRID_RERUN_2026-09-14/`）:
`dbp_hybrid_RAW_STDOUT.json`（含每候选 layer/来源/审计字段、每深度引擎调用数、PRIMARY 级联、top-50 路线）/ `dbp_hybrid_ALL_NORMALIZED_PREDICTIONS.csv` / `dbp_hybrid_RUN_META.json`。

评分语义声明（延续你们的审计要求）: 预测层分数 `ns33_max_source_x_agreement_x_skeleton_over_3`、lookup 层分数 `eawag_lookup_tanimoto`，两者**都不是校准概率**（`is_calibrated_probability=false`）。

## 6. 建议的下一步评估（供你们排期参考）

1. **选一个库内污染物做混合口径对照**（如 EAWAG 有收录的多氯联苯或表面活性剂类）——那才能展示 lookup 层置顶的实际效果（README 89.5% 口径的行为）。DBP 测的是闭卷，库内分子测开卷，两个都测才完整。
2. 下游酶/宿主模块接入 `TOP3_DIAGNOSTIC_ROUTES`（你们建议 #6 的后半句）——PRIMARY 现在化学正确，但下游管线仍只消费 rank-1。
3. PAE 家族的广度测试（DEHP 已在修复报告 §3.4 验证: MEHP rank-1）可扩到 DMP/DEP/DnOP。

---

*附: 本混合口径入口 `single_smiles_hybrid.py` 与纯预测入口 `single_smiles_v32.py` 共享全部引擎代码，仅新增 lookup 层合并逻辑; answer key 隔离纪律不变（不读任何 restricted 文件）。*


---

## 7. 补充发现（本次复测的审计输出）: lookup 索引的电荷口径缺口

本次混合运行中 lookup 层实际命中 3 条边（depth-3 的甲苯支路，bt0036/bt0005）。
**邻苯二甲酸（PTA，depth-2 的正确 rank-1 产物）未能触发 lookup**——根因: EAWAG 库
以阴离子形式 `O=C([O-])c1ccccc1C(=O)[O-]` 收录 PTA，而 `eawag_lookup.build_index`
用原始 stereo-blind canonical 做 donor 键，预测层输出的中性 PTA 精确匹配失败。
v3.3 的 `normalize_charge_smiles` 已能把两种形式归一到同一身份（实测两边都归一为
`O=C(O)c1ccccc1C(=O)O`）——**修复方向明确**（lookup 索引改用电荷归一化键），列为
下一个微修复。此缺口不影响本报告主体结论（DBP→MBP→PTA 级联由预测层达成），
但它正是你们 §4.3"电荷/质子化规范化不足"意见在 lookup 层的镜像体现——
规范化需要贯穿所有层，包括查表键。

---

## 8. 修复落地: lookup 键电荷归一化（§7 缺口的闭环）

**日期**: 2026-09-14（同日，§7 诊断后的微修复）
**改动**: 仅 `reaction_analogy/eawag_lookup.py`（一个文件，未提交，与其他 v3.3 工作树改动并列）
**规范**: 键 = `stereo_blind(normalize_charge_smiles(smi))`（v3.3 身份约定），复用 `bbd_v33_fusion.normalize_charge_smiles`；不含任何其他调参。

### 8.1 修复内容

- `build_index`: donor 键从原始 stereo-blind canonical 改为**电荷归一化 + 立体盲**身份（`_cn_identity`）。索引仍为 859 个 donor 键、0 条 parse-fail（电荷归一只改写 297 个键的书写形式，零合并、零新增——每条 donor 记录列表逐条不变）。
- `lookup`: 查询 parent 用同一 `_cn_identity` 归一后再匹配键（键与匹配同源）。
- 每条索引记录新增 `product_cn` 字段（电荷归一化产物身份，供下游合并）；`product_sb` 与其余字段**不变**（输出的候选身份仍为原始 stereo-blind，混合层合并行为不变）。
- `bbd_v33_fusion` 缺失时的兜底: protected/lazy import（文件加载 → sys.path 导入两级），失败则回退旧 stereo-blind 键，模块级 `KEY_MODE` 标志记录当前模式（本次运行 `charge_normalized`）。

### 8.2 单元检查（规范三条，全部通过）

| 查询 | 结果 |
|------|------|
| `O=C(O)c1ccccc1C(=O)O`（中性邻苯二甲酸） | **命中 2 条 bt0367 反应（r0102 / r1444）**——修复前 0 命中 |
| `O=C([O-])c1ccccc1C(=O)[O-]`（阴离子，EAWAG 原始形式） | 命中**同一集合**（两查询形式归一到同一键） |
| `CCCCOC(=O)c1ccccc1C(=O)OCCCC`（DBP） | `[]`（库外，负例不受影响） |

兜底模式（模拟 `bbd_v33_fusion` 缺失）实测: 键集合与旧索引逐一相同、中性 PTA 0 命中、阴离子 2 命中——即精确还原修复前行为。

### 8.3 93 案混合口径回归（诚实披露: Hit@1 变了 -1 case）

`predict_bbd_hybrid.py`（P4.2 与 v5 两模式）+ `score_bbd_hybrid.py calibers[_v5]`，stereo=blind，n=86:

| 口径 | 修复前 | 修复后 | 变化 |
|------|--------|--------|------|
| P4.2 hybrid H@1 | 78/86 = 90.7% | **77/86 = 89.5%** | **-1（c0134）** |
| P4.2 hybrid H@3/H@5/H@10/H@20 | 83/86 = 96.5% | 83/86 = 96.5% | 0 |
| v5 hybrid H@1 | 77/86 = 89.5% | **76/86 = 88.4%** | **-1（同一 case）** |
| v5 hybrid H@5/H@10 | 82/86 = 95.3% | 82/86 = 95.3% | 0 |
| lookup-only H@1 | 77/86 = 89.5% | 76/86 = 88.4% | -1（同一 case） |
| prediction（两模式） | 38.4% / 68.6%（P4.2）; 38.4% / 76.7%（v5） | 同左 | 0（预测路径不用 lookup） |
| n_lookup_hit | 87 | **87** | 0（案例级命中集合逐一相同，19 个阴离子 parent 换键命中） |

**根因（c0134 草甘膠）**: parent 本身是阴离子（`[O-]C(=O)CNCP([O-])([O-])=O`）。修复前排序指纹取原始阴离子形式，修复后取中性身份，两条 lookup 记录的 Tanimoto 下降幅度不同——sarcosine 0.400→0.214，混合共产物 0.393→0.226——记录顺序翻转，sarcosine（truth）从 rank-1 落到 **rank-2（仍在 H@3 内）**。c1072（o-氟苯甲酸）发生同类翻转但其两条记录都是 truth，指标不变。这是"键与相似度指纹同取中性身份"这一修复规范的直接后果，不是对答案 key 调参；blunt 事实是: 对**本身就是阴离子**的 8 个盲测 parent，旧口径的阴离子指纹对含阴离子产物有相似度优势，新口径抹平了它。

**真正的新增电荷命中（DBP 支路，见 §8.4）**: `Cc1ccccc1C(=O)O`（中性 o-甲苯甲酸）→ bt0368#r0223（阴离子 donor）——修复前不可达。

确定性: P4.2 双跑 byte-identical（preds/pool 均逐字节相同）。

### 8.4 DBP 端到端复测（修复后，`--out-prefix /tmp/dbp_hybrid_v2`）

```text
PRIMARY: DBP → MBP → 邻苯二甲酸 → 邻苯二甲酸顺-二氢二醇（bt0367#r0102, lookup 边 rank-1）
lookup 边计数: depth-1 = 0, depth-2 = 0, depth-3 = 6
  其中 2 条 = PTA → 二氢二醇（bt0367#r0102/r1444）——§7 缺口的闭环
  1 条 = o-甲苯甲酸 → 甲基二氢二醇（bt0368#r0223）——新增电荷命中
  3 条 = toluene 支路（bt0036/bt0005）——与修复前一致
n_edges: 8535 → 8537; 引擎调用 {1:1, 2:5, 3:22} 不变; 运行 205s
```

**深度语义说明**: PTA 以 depth-2 rank-1 预测产物进入 frontier，其 lookup 边在 depth-3 展开时触发（边深度 = 展开深度）——§7 所述"depth-2 的 rank-1 产物"即 PTA 本身，触发在其下一层展开，与代码语义一致。

**PRIMARY 第三步的变化**: 从预测的 2-formylbenzoic acid 变为 lookup 置顶的 PTA-dihydrodiol（greedy rank-1 cascade 含 lookup 边的预期行为——EAWAG 收录的 PTA 双加氧反应现在压过预测边）。depth-1/depth-2（MBP、PTA 均 rank-1）与修复前一致。

### 8.5 红线自查

- fail-closed: parse 失败跳过并计数（0 条）；兜底模式不 crash。
- answer-key 隔离: `eawag_lookup.py` / `single_smiles_hybrid.py` 未读任何 restricted 文件（评分器是唯一读者，本次回归的两次评分各只运行一次）。
- 未对答案 key 调参: 改动仅键归一化一处，无阈值、无权重。
- 未提交、未 push; 改动仅 `eawag_lookup.py` + 本报告追加 + `/tmp` 输出。

### 8.6 审计微修（GLM-5.3 audit pass，§8 交付后的一个两行修正）

**审计发现**: §8 的修复把两件事捆在一起改了——(a) 索引键/查询键用电荷归一化匹配（§7 缺口的修复本体，正确），(b) 块内 Tanimoto 排序指纹也换成了归一化形式（附带语义变更，且形成"归一化查询指纹 vs 原始产物指纹"的不对称比较）。(b) 是 §8.3 中 −1 case（c0134）回归的直接原因。

**微修**（`eawag_lookup.py` 一处，两行）: 键匹配保留电荷归一化；块内排序指纹恢复**查询的原始 stereo-blind 形式**（与修复前完全一致的 raw-vs-raw 对称比较）。原则: 电荷归一化是**身份/匹配**层的职责，不是**相似度**层的职责——键负责"是不是同一个分子"，Tanimoto 负责"结构有多像"，两者解耦。

**微修后三道门全部通过**:

| 验证门 | 结果 |
|--------|------|
| 单元检查 | 中性 PTA → 2 hits（bt0367#r0102/r1444）; 阴离子 PTA → 同一集合; DBP → `[]`（不变） |
| v5 混合口径回归 | **77/86 = 89.5% / H@10 82/86 = 95.3%**——与 `bbd_hybrid_eval_v5.json` 基线**完全一致**; c0134 rank-1 恢复为 sarcosine（truth）; 预测口径与 4 ablations 逐一相同 |
| P4.2 混合口径回归 | **78/86 = 90.7% / 96.5%**——与 P4.2 基线完全一致 |
| DBP 端到端 | PRIMARY: DBP → MBP → 邻苯二甲酸 → **邻苯二甲酸顺-二氢二醇（bt0367#r0102，lookup 边 rank-1）**; lookup 边 6 条全部在 depth-3（PTA 上 2 条 rank-1/2、o-甲苯甲酸 1 条、甲苯支路 3 条）; 引擎调用 {1:1, 2:5, 3:22}; n_edges 8537 |

终版 DBP 产物归档: `dbp_hybrid_v3_RAW_STDOUT.json / _ALL_NORMALIZED_PREDICTIONS.csv / _RUN_META.json`（本目录; `dbp_hybrid_*`（无 v3 后缀）为 §7 诊断时的修复前运行，保留作对照）。§8.3 表中"修复后 76/86"一列为微修前的中间状态，已被本节取代; n_lookup_hit=87 与案例级命中集合在微修前后均不变。

未提交、未 push（工作树统一管理）; 微修仅 `eawag_lookup.py` 一处（§8 声明的改动范围不扩大）。
