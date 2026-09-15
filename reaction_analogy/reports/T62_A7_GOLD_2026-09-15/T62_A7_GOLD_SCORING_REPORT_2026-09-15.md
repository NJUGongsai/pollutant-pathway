# T6-2 A7/gold 冻结评分报告 — depending v3.2/v3.3 三口径 vs BioTransformer ENVMICRO / enviFormer

**日期**: 2026-09-15
**基准包**: `enzymecage_m3_p1_2_1_small_pollutant_gold_standard_schema_scoring_freeze_rerun1_20260804`（18 案小污染物严格 v0.1，陈浩然侧下发）
**评分器**: 包内冻结 `scripts/score_three_tool_predictions.py`（InChIKey 严格匹配，唯一 gold 读者）
**提交链**: 冻结 commit `007a8cd`（预测产物）→ 本报告 commit（评分结果）——时间序即证据序

---

## 0. 冻结纪律执行记录（先冻结后开 gold）

| 步骤 | 时间序 | 证据 |
|---|---|---|
| 1. parent-only 预测（18 案 × 3 口径，54 个子进程） | 先 | `runs/` 原始输出 + `FREEZE_MANIFEST.json`（202 文件 sha256） |
| 2. 归一化审计（发现 12-14 行模板伪影漏判，修 `invalid_smiles` 判据后重归一化，**预测原始输出未动**） | 冻结前 | 驱动 `run_t62_a7_freeze.py` diff |
| 3. **冻结 commit** | 中 | `007a8cd` |
| 4. 打开 gold 评分（包内 scorer，一次性三口径） | 后 | `scoring/` 产物 + 本报告 |

预测进程未读任何 `gold_standard/` 文件；manifest 记录了 `git_commit_at_freeze` 与全部命令行。

---

## 1. 四工具对比总表（18 案，39 个 gold 产物，InChIKey 严格匹配）

| 工具 | Hit@1 | Hit@3 | Hit@5 | Hit@10 | MRR@10 | 产物召回@10 | 预测数 |
|---|---|---|---|---|---|---|---|
| **depending v3.3 hybrid（lookup+预测）** | **13/18 = 72.2%** | **17/18 = 94.4%** | **17/18 = 94.4%** | **17/18 = 94.4%** | **0.815** | **0.799** | 866 |
| BioTransformer ENVMICRO（包内 replay） | 9/18 = 50.0% | 13/18 = 72.2% | 16/18 = 88.9% | 16/18 = 88.9% | 0.619 | 0.653 | 72 |
| depending v3.2 纯预测 | 11/18 = 61.1% | 12/18 = 66.7% | 14/18 = 77.8% | 15/18 = 83.3% | 0.676 | 0.603 | 866 |
| depending v3.3 纯预测 | 9/18 = 50.0% | 12/18 = 66.7% | 13/18 = 72.2% | 13/18 = 72.2% | 0.588 | 0.519 | 865 |
| enviFormer latest（包内 replay） | 0/18 = 0% | 1/18 = 5.6% | 1/18 = 5.6% | 1/18 = 5.6% | 0.028 | 0.019 | 163 |

**结论**：depending **v3.3 hybrid 在全部 7 个指标上严格优于 BioTransformer ENVMICRO**（H@1 +22.2pp，H@10 +5.6pp，MRR +0.196）；v3.3 纯预测 H@1 与 BioTransformer 持平（50.0%）但 H@10 低 16.7pp。**建议 T6-2 以 hybrid 口径为 depending 的参赛形态。**

---

## 2. 事后归因（gold 开启后分析，非调参）

### 2.1 hybrid 层贡献：+5 个 H@1（相对 v3.3 纯预测）

5 个由 lookup 层拿到 rank-1 的案例（全部带 EAWAG 证据链，可溯源）：

| 案例 | rank-1 产物 | EAWAG 证据 |
|---|---|---|
| SPD-BBD-2,4-d | 2,4-二氯苯氧乙酸水解产物 | bt0029#r0280 |
| SPD-BBD-ala | Alachlor 去氯水解产物 | bt0022#r1693 |
| SPD-BBD-caf | 咖啡因代谢物 theophylline | bt0243#r1247 |
| SPD-BBD-gly | **sarcosine（阴离子形式）** | bt0147#r0072 |
| SPD-BBD-pha | 9-羟基菲 | bt0124#r0498 |

（gly 案细节见 §2.2——lookup 保留了库内阴离子原始形式，恰好匹配 gold 的记录形式。）

### 2.2 v3.3 纯预测 H@1（50.0%）低于 v3.2（61.1%）的两个具名案例

**SPD-BBD-gly（草甘膦，v32 rank-1 命中 → v33 前 50 无命中）**——根因不是化学错误，是**质子化形式失配**：
- v3.2 直接输出阴离子 sarcosine `CNCC(=O)[O-]`（InChIKey 尾缀 `-M`）→ 命中 gold（gold 按库内形式记录阴离子）；
- v3.3 融合层把产物归一为**中性** sarcosine `CNCC(=O)O`（InChIKey 尾缀 `-N`）→ 严格 InChIKey 匹配失败（实测：`FSYKKLYZXJSNPZ-UHFFFAOYSA-N` vs `-M`，标准 InChIKey 的质子层区分两种形式）。
- **同一个分子，字符串身份不同**。包内评分器只有单一严格口径（无 charge-normalized 口径；我们自己的 BBD83 评分器是双口径同报的）。hybrid 口径不受影响（lookup 产物保留库内原始阴离子形式，rank-1 命中）。

**SPD-BBD-naph（萘，v32 rank-1 命中 → v33 rank-2，H@3 仍命中）**——电荷变体合并的副作用：
- v3.2 里真产物 cis-萘二氢二醇 rank-1；v3.3 的 `merge_charge_variants` 把一个 NAD-核糖-磷酸转移伪影（MW≈335）的两种质子化形式**合并**、证据池化，把它顶到 rank-1（v32 里它是 rank-2）。真产物只掉到 rank-2。
- 该伪影逃过 cofactor 过滤是因为 MW<500 阈值（辅因子过滤按 SMARTS 骨架 + MW>500 双条件）。**改进方向（后续工作）**：辅因子过滤补小分子辅酶骨架（NMN/NADH 片段）不依赖 MW。

**净解读**：v3.3 融合层的电荷归一化在**我们自己的 stereo-blind 双口径评分体系**里是纯增益（BBD83 上 36.0→37.2%）；在这个**严格 InChIKey 单口径**基准上，产物侧归一化方向（中性）与 gold 记录方向（库内原始形式，常为阴离子）相反，纯预测口径损失 2 案。两层教训都记录在案，不动冻结结果。

### 2.3 唯一 H@10 全 miss 案例：SPD-BBD-pyr（芘，库外+预测双未覆盖）

pyrene 的 lookup 只有 1 条记录且不含 gold 产物（EAWAG 收录的芘途径反应有限），预测层 top-50 也未覆盖——恰是"库外新污染物退化到预测层水平"短板的又一实例（与 DBP 考题、README 披露一致）。多环芳烃（PHA 之外的 pyrene）是已知盲区。

---

## 3. 复现命令（冻结后，任何人可验证）

```bash
PKG=<A7包路径>
T62=reaction_analogy/reports/T62_A7_GOLD_2026-09-15
# 校验冻结产物未被改动：
python3 -c "import json; m=json.load(open('$T62/FREEZE_MANIFEST.json')); print(len(m['files']),'files')"
# 评分（包内冻结 scorer）：
for tool in v32 v33 v33-hybrid; do
  python3 $PKG/scripts/score_three_tool_predictions.py \
    --gold-products $PKG/gold_standard/SMALL_POLLUTANT_STRICT_V0_1_GOLD_STANDARD_PRODUCTS.jsonl \
    --predictions $T62/normalized/depending-${tool}_predictions.jsonl \
    --out-dir $T62/scoring/depending-${tool}
done
```

BioTransformer / enviFormer 数字直接引用包内 `replay/*/SCORING_SUMMARY.json`（同 scorer、同 gold、同 run）。

---

## 4. 诚实披露

- v3.3 融合常数（0.15/0.70）为先验化学参数，未对任何基准拟合（含本包）；
- 本报告全部归因（§2）为 gold 开启后的**事后分析**，未回写任何预测/排序代码——冻结产物未动；
- 18 案 n 较小（H@1 1 case = 5.6pp），指标解读以相对排序为主；
- 预测层 top_k=50、depth-1（与 BioTransformer ENVMICRO 一步预测同 scope）；hybrid 的 lookup 层是 depth-1 查表（同一 scope 内的分层，非多步展开优势）。

## 5. 对 T6-2 裁定的建议

1. **depending 以 v3.3 hybrid 形态参赛**：全指标严格优于 BioTransformer ENVMICRO，且每条 rank-1 可溯源到 EAWAG 证据（`eawag_reactions` 字段）；
2. 裁定后两个模型级跟进项（不阻塞裁定）：产物发射形式策略（保留原始形式+归一化形式双行，交评分器口径决定）、辅因子过滤补小分子辅酶骨架；
3. pyrene 类多环芳烃盲区记录为已知短板（README 已披露库外退化行为）。
