# `[biosysmodb121·调参集 N=261]` 41 道剔除题逐题核对清单（已同步 `v1.4` 终版结果）

> **外发授权登记**：本文包含 41 道被剔除调参题的 `qid` 与结构串（SMILES），经项目负责人于 2026-11-16 明确逐次授权发布至个人仓 `v44` 分支供外部核验（156 道单步留出集全程零触碰）。
>
> - **来源批**：`[biosysmodb121·调参集 N=261]`（剔除以下 `41` 题后得 `[biosysmodb121·调参干净集 N=220]`；未触碰 156 道留出集）
> - **配套脱敏报告（`v1.4` 更新版）**：[`B121_CLEAN_SUBSET_V14_EVALUATION_2026-11-16.md`](B121_CLEAN_SUBSET_V14_EVALUATION_2026-11-16.md)
> - **判分参考臂**：`v1.4` 终版 `b121_wl4_pa_11p_at16::v14s4_cons_v3_prom_adj`（主）与 `v1.3` 冠军 `b121_pa_pb`（旧对照）

## 一、 各层题量与模型命中汇总（`v1.4` 终版 vs `v1.3` 基线）

| 层级 | 剔除类型 | 题数 | `v1.4` 终版 `v6` Hit@1 / Hit@5 | `v1.4` 终版 `v4` Hit@1 / Hit@5 | `v1.3` 基线 `v6` Hit@1 / Hit@5 |
|---|---|---:|---:|---:|---:|
| **L1A** | 底物已是 23 中心碳代谢终点池分子 | 7 | 2 / 2 | 2 / 2 | 2 / 3 |
| **L1B** | 无环直链脂肪族 CoA → CoA 宿主 β-氧化家务步 | 7 | 3 / 4 | 2 / 4 | 2 / 3 |
| **L2** | 硬伤 A — 纯自环 / 同分子零反应伪影 | 5 | 0 / 0 | 0 / 0 | 0 / 0 |
| **L3** | 硬伤 B — 单底物漏给供体却凭空增重原子 | 16 | 0 / 1 | 0 / 0 | 0 / 2 |
| **L4** | 硬伤 C — 零骨架变化纯顺反 / 手性翻转异构 | 6 | 0 / 0 | 0 / 0 | 0 / 0 |
| **合计** | **4 层去重总剔除** | **41** | **5 / 7** | **4 / 6** | **4 / 8** |

## 二、 41 道剔除题逐题明细

### Layer 1A：底物已是 23 中心碳代谢终点池分子（7 题）

| # | QID | 具体判定归因 | 分子式 / 重原子变化 | `v1.4` 终版 (v6 / v4) | `v1.3` 基线 (v6 / v4) | 底物 SMILES | 参考产物 SMILES |
|---:|---|---|---|---|---|---|---|
| 1 | `BIOPATH150_041__S03__BSY-r03869` | 底物为 `succinyl_coa`（23终点池）→ 产物 `methylmalonyl_coa` | `C25H35N7O19P3S-5` (55 HA) → `C25H35N7O19P3S-5` (55 HA) | Miss / Miss | Miss / Miss | `CC(C)(COP(=O)([O-])OP(=O)([O-])OC[C@H]1O[C@@H](n2cnc3c(N)ncnc32)[C@H](O)[C@@H]1OP(=O)([O-])[O-])[C@@H](O)C(=O)NCCC(=O)NCCSC(=O)CCC(=O)[O-]` | `C[C@H](C(=O)[O-])C(=O)SCCNC(=O)CCNC(=O)[C@H](O)C(C)(C)COP(=O)([O-])OP(=O)([O-])OC[C@H]1O[C@@H](n2cnc3c(N)ncnc32)[C@H](O)[C@@H]1OP(=O)([O-])[O-]` |
| 2 | `BIOPATH150_054__S02__BSY-r02236` | 底物为 `lactate`（23终点池）→ 产物 `pyruvate` | `C3H5O3-` (6 HA) → `C3H3O3-` (6 HA) | Rank 1 / Rank 1 | Rank 1 / Rank 1 | `C[C@@H](O)C(=O)[O-]` | `CC(=O)C(=O)[O-]` |
| 3 | `BIOPATH150_056__S01__BSY-r02237` | 底物为 `lactate`（23终点池）→ 产物 `pyruvate` | `C3H5O3-` (6 HA) → `C3H3O3-` (6 HA) | Rank 1 / Rank 1 | Rank 1 / Rank 1 | `C[C@H](O)C(=O)[O-]` | `CC(=O)C(=O)[O-]` |
| 4 | `BIOPATH150_104__S04__BSY-r01615` | 底物为 `propionyl_coa`（23终点池）→ 产物 `propanoyl_phosphate` | `C24H36N7O17P3S-4` (52 HA) → `C3H5O5P-2` (9 HA) | Miss / Miss | Miss / Miss | `CCC(=O)SCCNC(=O)CCNC(=O)[C@H](O)C(C)(C)COP(=O)([O-])OP(=O)([O-])OC[C@H]1O[C@@H](n2cnc3c(N)ncnc32)[C@H](O)[C@@H]1OP(=O)([O-])[O-]` | `CCC(=O)OP(=O)([O-])[O-]` |
| 5 | `BIOPATH150_107__S06__BSY-r03834` | 底物为 `fumarate`（23终点池）→ 产物 `fumarate` | `C4H2O4-2` (8 HA) → `C4H2O4-2` (8 HA) | Miss / Miss | Miss / Miss | `O=C([O-])/C=C\C(=O)[O-]` | `O=C([O-])/C=C/C(=O)[O-]` |
| 6 | `BIOPATH150_110__S01__BSY-r01923` | 底物为 `malate`（23终点池）→ 产物 `pyruvate` | `C4H4O5-2` (9 HA) → `C3H3O3-` (6 HA) | Miss / Miss | Rank 4 / Rank 4 | `O=C([O-])C[C@@H](O)C(=O)[O-]` | `CC(=O)C(=O)[O-]` |
| 7 | `BIOPATH150_110__S03__BSY-r03264` | 底物为 `fumarate`（23终点池）→ 产物 `malate` | `C4H2O4-2` (8 HA) → `C4H4O5-2` (9 HA) | Miss / Miss | Miss / Miss | `O=C([O-])/C=C\C(=O)[O-]` | `O=C([O-])C[C@@H](O)C(=O)[O-]` |

### Layer 1B：无环直链脂肪族 CoA → CoA 宿主 β-氧化家务步（7 题）

| # | QID | 具体判定归因 | 分子式 / 重原子变化 | `v1.4` 终版 (v6 / v4) | `v1.3` 基线 (v6 / v4) | 底物 SMILES | 参考产物 SMILES |
|---:|---|---|---|---|---|---|---|
| 8 | `BIOPATH150_041__S02__BSY-r03821` | 无环直链酰基-CoA (`C4` → `C4`)，宿主 β-氧化支路 | `C25H35N7O19P3S-5` (55 HA) → `C25H35N7O19P3S-5` (55 HA) | Miss / Miss | Miss / Miss | `C[C@H](C(=O)[O-])C(=O)SCCNC(=O)CCNC(=O)[C@H](O)C(C)(C)COP(=O)([O-])OP(=O)([O-])OC[C@H]1O[C@@H](n2cnc3c(N)ncnc32)[C@H](O)[C@@H]1OP(=O)([O-])[O-]` | `C[C@@H](C(=O)[O-])C(=O)SCCNC(=O)CCNC(=O)[C@H](O)C(C)(C)COP(=O)([O-])OP(=O)([O-])OC[C@H]1O[C@@H](n2cnc3c(N)ncnc32)[C@H](O)[C@@H]1OP(=O)([O-])[O-]` |
| 9 | `BIOPATH150_045__S02__BSY-r02054` | 无环直链酰基-CoA (`C6` → `C6`)，宿主 β-氧化支路 | `C27H37N7O20P3S-5` (58 HA) → `C27H39N7O20P3S-5` (58 HA) | Miss / Miss | Miss / Miss | `CC(C)(COP(=O)([O-])OP(=O)([O-])OC[C@H]1O[C@@H](n2cnc3c(N)ncnc32)[C@H](O)[C@@H]1OP(=O)([O-])[O-])[C@@H](O)C(=O)NCCC(=O)NCCSC(=O)CC(=O)CCC(=O)[O-]` | `CC(C)(COP(=O)([O-])OP(=O)([O-])OC[C@H]1O[C@@H](n2cnc3c(N)ncnc32)[C@H](O)[C@@H]1OP(=O)([O-])[O-])[C@@H](O)C(=O)NCCC(=O)NCCSC(=O)C[C@@H](O)CCC(=O)[O-]` |
| 10 | `BIOPATH150_045__S03__BSY-r02509` | 无环直链酰基-CoA (`C8` → `C8`)，宿主 β-氧化支路 | `C29H40N7O19P3S-4` (59 HA) → `C29H39N7O20P3S-5` (60 HA) | Rank 1 / Rank 4 | Rank 1 / Rank 3 | `CC(C)(COP(=O)([O-])OP(=O)([O-])OC[C@H]1O[C@@H](n2cnc3c(N)ncnc32)[C@H](O)[C@@H]1OP(=O)([O-])[O-])[C@@H](O)C(=O)NCCC(=O)NCCSC(=O)CC(=O)C/C=C\CC=O` | `CC(C)(COP(=O)([O-])OP(=O)([O-])OC[C@H]1O[C@@H](n2cnc3c(N)ncnc32)[C@H](O)[C@@H]1OP(=O)([O-])[O-])[C@@H](O)C(=O)NCCC(=O)NCCSC(=O)CC(=O)C/C=C\CC(=O)[O-]` |
| 11 | `BIOPATH150_045__S07__BSY-r03623` | 无环直链酰基-CoA (`C6` → `C6`)，宿主 β-氧化支路 | `C27H39N7O20P3S-5` (58 HA) → `C27H37N7O19P3S-5` (57 HA) | Miss / Miss | Miss / Miss | `CC(C)(COP(=O)([O-])OP(=O)([O-])OC[C@H]1O[C@@H](n2cnc3c(N)ncnc32)[C@H](O)[C@@H]1OP(=O)([O-])[O-])[C@@H](O)C(=O)NCCC(=O)NCCSC(=O)C[C@@H](O)CCC(=O)[O-]` | `CC(C)(COP(=O)([O-])OP(=O)([O-])OC[C@H]1O[C@@H](n2cnc3c(N)ncnc32)[C@H](O)[C@@H]1OP(=O)([O-])[O-])[C@@H](O)C(=O)NCCC(=O)NCCSC(=O)/C=C/CCC(=O)[O-]` |
| 12 | `BIOPATH150_082__S05__BSY-r03566` | 无环直链酰基-CoA (`C3` → `C3`)，宿主 β-氧化支路 | `C24H36N7O18P3S-4` (53 HA) → `C24H34N7O17P3S-4` (52 HA) | Rank 1 / Rank 1 | Rank 3 / Rank 3 | `CC(C)(COP(=O)([O-])OP(=O)([O-])OC[C@H]1O[C@@H](n2cnc3c(N)ncnc32)[C@H](O)[C@@H]1OP(=O)([O-])[O-])[C@@H](O)C(=O)NCCC(=O)NCCSC(=O)CCO` | `C=CC(=O)SCCNC(=O)CCNC(=O)[C@H](O)C(C)(C)COP(=O)([O-])OP(=O)([O-])OC[C@H]1O[C@@H](n2cnc3c(N)ncnc32)[C@H](O)[C@@H]1OP(=O)([O-])[O-]` |
| 13 | `BIOPATH150_139__S02__BSY-r02505` | 无环直链酰基-CoA (`C3` → `C3`)，宿主 β-氧化支路 | `C24H34N7O17P3S-4` (52 HA) → `C24H36N7O17P3S-4` (52 HA) | Rank 2 / Rank 2 | Rank 1 / Rank 1 | `C=CC(=O)SCCNC(=O)CCNC(=O)[C@H](O)C(C)(C)COP(=O)([O-])OP(=O)([O-])OC[C@H]1O[C@@H](n2cnc3c(N)ncnc32)[C@H](O)[C@@H]1OP(=O)([O-])[O-]` | `CCC(=O)SCCNC(=O)CCNC(=O)[C@H](O)C(C)(C)COP(=O)([O-])OP(=O)([O-])OC[C@H]1O[C@@H](n2cnc3c(N)ncnc32)[C@H](O)[C@@H]1OP(=O)([O-])[O-]` |
| 14 | `BIOPATH150_139__S03__BSY-r03566` | 无环直链酰基-CoA (`C3` → `C3`)，宿主 β-氧化支路 | `C24H36N7O18P3S-4` (53 HA) → `C24H34N7O17P3S-4` (52 HA) | Rank 1 / Rank 1 | Miss / Miss | `CC(C)(COP(=O)([O-])OP(=O)([O-])OC[C@H]1O[C@@H](n2cnc3c(N)ncnc32)[C@H](O)[C@@H]1OP(=O)([O-])[O-])[C@@H](O)C(=O)NCCC(=O)NCCSC(=O)CCO` | `C=CC(=O)SCCNC(=O)CCNC(=O)[C@H](O)C(C)(C)COP(=O)([O-])OP(=O)([O-])OC[C@H]1O[C@@H](n2cnc3c(N)ncnc32)[C@H](O)[C@@H]1OP(=O)([O-])[O-]` |

### Layer 2：硬伤 A — 纯自环 / 同分子零反应伪影（5 题）

| # | QID | 具体判定归因 | 分子式 / 重原子变化 | `v1.4` 终版 (v6 / v4) | `v1.3` 基线 (v6 / v4) | 底物 SMILES | 参考产物 SMILES |
|---:|---|---|---|---|---|---|---|
| 15 | `BIOPATH150_141__S03__BSY-r03453` | 去电荷完整 InChIKey 一致（SMILES 完全相同） | `C12H24N2O4S` (19 HA) → `C12H24N2O4S` (19 HA) | Miss / Miss | Miss / Miss | `CCCC(C)(CCO)SC[C@H](N)C(=O)NCC(=O)O` | `CCCC(C)(CCO)SC[C@H](N)C(=O)NCC(=O)O` |
| 16 | `BIOPATH150_145__S07__BSY-r03791` | 去电荷完整 InChIKey 一致（SMILES 完全相同） | `C2H5O4S-` (7 HA) → `C2H5O4S-` (7 HA) | Miss / Miss | Miss / Miss | `O=S(=O)([O-])CCO` | `O=S(=O)([O-])CCO` |
| 17 | `BIOPATH150_146__S04__BSY-r03670` | 去电荷完整 InChIKey 一致（SMILES 完全相同） | `C3H4O6S-2` (10 HA) → `C3H4O6S-2` (10 HA) | Miss / Miss | Miss / Miss | `O=C([O-])[C@H](O)CS(=O)(=O)[O-]` | `O=C([O-])[C@H](O)CS(=O)(=O)[O-]` |
| 18 | `BIOPATH150_149__S01__BSY-r01831` | 去电荷完整 InChIKey 一致（SMILES 完全相同） | `C5H13N4O3+` (12 HA) → `C5H13N4O3+` (12 HA) | Miss / Miss | Miss / Miss | `NC(N)=[NH+]OCC[C@H]([NH3+])C(=O)[O-]` | `NC(N)=[NH+]OCC[C@H]([NH3+])C(=O)[O-]` |
| 19 | `BIOPATH150_149__S06__BSY-r03410` | 去电荷完整 InChIKey 一致（SMILES 完全相同） | `CH6N3O+` (5 HA) → `CH6N3O+` (5 HA) | Miss / Miss | Miss / Miss | `NC(N)=[NH+]O` | `NC(N)=[NH+]O` |

### Layer 3：硬伤 B — 单底物漏给供体却凭空增重原子（16 题）

| # | QID | 具体判定归因 | 分子式 / 重原子变化 | `v1.4` 终版 (v6 / v4) | `v1.3` 基线 (v6 / v4) | 底物 SMILES | 参考产物 SMILES |
|---:|---|---|---|---|---|---|---|
| 20 | `BIOPATH150_028__S04__BSY-r03812` | 单底物凭空增原子 +C1 | `C4H7N3O` (8 HA) → `C5H9NO3` (9 HA) | Miss / Miss | Miss / Miss | `CN1CC(=O)N=C1N` | `N[C@@H](CCC=O)C(=O)O` |
| 21 | `BIOPATH150_045__S01__BSY-r01589` | 单底物凭空增原子 +C21, +N7, +P3, +S1 （凭空挂 CoA） | `C8H7O2-` (10 HA) → `C29H38N7O17P3S-4` (57 HA) | Miss / Miss | Miss / Miss | `O=C([O-])Cc1ccccc1` | `CC(C)(COP(=O)([O-])OP(=O)([O-])OC[C@H]1O[C@@H](n2cnc3c(N)ncnc32)[C@H](O)[C@@H]1OP(=O)([O-])[O-])[C@@H](O)C(=O)NCCC(=O)NCCSC(=O)Cc1ccccc1` |
| 22 | `BIOPATH150_051__S01__BSY-r01634` | 单底物凭空增原子 +C21, +N7, +P3, +S1 （凭空挂 CoA） | `C2H4O` (3 HA) → `C23H34N7O17P3S-4` (51 HA) | Miss / Miss | Miss / Miss | `CC=O` | `CC(=O)SCCNC(=O)CCNC(=O)[C@H](O)C(C)(C)COP(=O)([O-])OP(=O)([O-])OC[C@H]1O[C@@H](n2cnc3c(N)ncnc32)[C@H](O)[C@@H]1OP(=O)([O-])[O-]` |
| 23 | `BIOPATH150_075__S03__BSY-r01960` | 单底物凭空增原子 +C21, +N7, +P3, +S1 （凭空挂 CoA） | `C7H4ClO2-` (10 HA) → `C28H35ClN7O17P3S-4` (57 HA) | Miss / Miss | Miss / Miss | `O=C([O-])c1ccc(Cl)cc1` | `CC(C)(COP(=O)([O-])OP(=O)([O-])OC[C@H]1O[C@@H](n2cnc3c(N)ncnc32)[C@H](O)[C@@H]1OP(=O)([O-])[O-])[C@@H](O)C(=O)NCCC(=O)NCCSC(=O)c1ccc(Cl)cc1` |
| 24 | `BIOPATH150_080__S01__BSY-r02143` | 单底物凭空增原子 +C21, +N7, +P3, +S1 （凭空挂 CoA） | `C10H9O4-` (14 HA) → `C31H40N7O19P3S-4` (61 HA) | Miss / Miss | Miss / Miss | `COc1cc(/C=C/C(=O)O)ccc1[O-]` | `COc1cc(/C=C/C(=O)SCCNC(=O)CCNC(=O)[C@H](O)C(C)(C)COP(=O)([O-])OP(=O)([O-])OC[C@H]2O[C@@H](n3cnc4c(N)ncnc43)[C@H](O)[C@@H]2OP(=O)([O-])[O-])ccc1O` |
| 25 | `BIOPATH150_082__S02__BSY-r02088` | 单底物凭空增原子 +C20, +N7, +P3, +S1 （凭空挂 CoA） | `C3H3O3-` (6 HA) → `C23H34N7O17P3S-4` (51 HA) | Miss / Miss | Miss / Miss | `O=CCC(=O)[O-]` | `CC(=O)SCCNC(=O)CCNC(=O)[C@H](O)C(C)(C)COP(=O)([O-])OP(=O)([O-])OC[C@H]1O[C@@H](n2cnc3c(N)ncnc32)[C@H](O)[C@@H]1OP(=O)([O-])[O-]` |
| 26 | `BIOPATH150_087__S01__BSY-r01636` | 单底物凭空增原子 +C21, +N7, +P2, +S1 （凭空挂 CoA） | `C2H3O5P-2` (8 HA) → `C23H34N7O17P3S-4` (51 HA) | Miss / Miss | Miss / Miss | `CC(=O)OP(=O)([O-])[O-]` | `CC(=O)SCCNC(=O)CCNC(=O)[C@H](O)C(C)(C)COP(=O)([O-])OP(=O)([O-])OC[C@H]1O[C@@H](n2cnc3c(N)ncnc32)[C@H](O)[C@@H]1OP(=O)([O-])[O-]` |
| 27 | `BIOPATH150_104__S02__BSY-r01613` | 单底物凭空增原子 +C21, +N7, +P3, +S1 （凭空挂 CoA） | `C3H6O` (4 HA) → `C24H36N7O17P3S-4` (52 HA) | Miss / Miss | Miss / Miss | `CCC=O` | `CCC(=O)SCCNC(=O)CCNC(=O)[C@H](O)C(C)(C)COP(=O)([O-])OP(=O)([O-])OC[C@H]1O[C@@H](n2cnc3c(N)ncnc32)[C@H](O)[C@@H]1OP(=O)([O-])[O-]` |
| 28 | `BIOPATH150_109__S01__BSY-r02165` | 单底物凭空增原子 +P1 | `C6H11O8S-` (15 HA) → `C6H10O11PS-3` (19 HA) | Rank 4 / Miss | Rank 5 / Miss | `O=S(=O)([O-])C[C@H]1OC(O)(CO)[C@@H](O)[C@@H]1O` | `O=P([O-])([O-])OCC1(O)O[C@H](CS(=O)(=O)[O-])[C@@H](O)[C@@H]1O` |
| 29 | `BIOPATH150_114__S01__BSY-r01911` | 单底物凭空增原子 +C21, +N7, +P3, +S1 （凭空挂 CoA） | `C11H7O2-` (13 HA) → `C32H38N7O17P3S-4` (60 HA) | Miss / Miss | Miss / Miss | `O=C([O-])c1ccc2ccccc2c1` | `CC(C)(COP(=O)([O-])OP(=O)([O-])OC[C@H]1O[C@@H](n2cnc3c(N)ncnc32)[C@H](O)[C@@H]1OP(=O)([O-])[O-])[C@@H](O)C(=O)NCCC(=O)NCCSC(=O)c1ccc2ccccc2c1` |
| 30 | `BIOPATH150_128__S01__BSY-r02167` | 单底物凭空增原子 +P1 | `C4H8O4` (8 HA) → `C4H7O7P-2` (12 HA) | Miss / Miss | Miss / Miss | `O=C(CO)[C@@H](O)CO` | `O=C(COP(=O)([O-])[O-])[C@@H](O)CO` |
| 31 | `BIOPATH150_135__S04__BSY-r02148` | 单底物凭空增原子 +C21, +N7, +P3, +S1 （凭空挂 CoA） | `C10H13O2-` (12 HA) → `C31H44N7O17P3S-4` (59 HA) | Miss / Miss | Miss / Miss | `C=C(C)C1CC=C(C(=O)[O-])CC1` | `C=C(C)C1CC=C(C(=O)SCCNC(=O)CCNC(=O)[C@H](O)C(C)(C)COP(=O)([O-])OP(=O)([O-])OC[C@H]2O[C@@H](n3cnc4c(N)ncnc43)[C@H](O)[C@@H]2OP(=O)([O-])[O-])CC1` |
| 32 | `BIOPATH150_136__S01__BSY-r01634` | 单底物凭空增原子 +C21, +N7, +P3, +S1 （凭空挂 CoA） | `C2H4O` (3 HA) → `C23H34N7O17P3S-4` (51 HA) | Miss / Miss | Miss / Miss | `CC=O` | `CC(=O)SCCNC(=O)CCNC(=O)[C@H](O)C(C)(C)COP(=O)([O-])OP(=O)([O-])OC[C@H]1O[C@@H](n2cnc3c(N)ncnc32)[C@H](O)[C@@H]1OP(=O)([O-])[O-]` |
| 33 | `BIOPATH150_139__S01__BSY-r01907` | 单底物凭空增原子 +C21, +N7, +P3, +S1 （凭空挂 CoA） | `C3H3O2-` (5 HA) → `C24H34N7O17P3S-4` (52 HA) | Miss / Miss | Miss / Miss | `C=CC(=O)[O-]` | `C=CC(=O)SCCNC(=O)CCNC(=O)[C@H](O)C(C)(C)COP(=O)([O-])OP(=O)([O-])OC[C@H]1O[C@@H](n2cnc3c(N)ncnc32)[C@H](O)[C@@H]1OP(=O)([O-])[O-]` |
| 34 | `BIOPATH150_144__S01__BSY-r02119` | 单底物凭空增原子 +C21, +N7, +P3, +S1 （凭空挂 CoA） | `C7H15NO2` (10 HA) → `C28H46N8O17P3S-3` (57 HA) | Miss / Miss | Miss / Miss | `C[N+](C)(C)CCCC(=O)[O-]` | `CC(C)(COP(=O)([O-])OP(=O)([O-])OC[C@H]1O[C@@H](n2cnc3c(N)ncnc32)[C@H](O)[C@@H]1OP(=O)([O-])[O-])[C@@H](O)C(=O)NCCC(=O)NCCSC(=O)CCC[N+](C)(C)C` |
| 35 | `BIOPATH150_146__S01__BSY-r02165` | 单底物凭空增原子 +P1 | `C6H11O8S-` (15 HA) → `C6H10O11PS-3` (19 HA) | Miss / Miss | Rank 3 / Miss | `O=S(=O)([O-])C[C@H]1OC(O)(CO)[C@@H](O)[C@@H]1O` | `O=P([O-])([O-])OCC1(O)O[C@H](CS(=O)(=O)[O-])[C@@H](O)[C@@H]1O` |

### Layer 4：硬伤 C — 零骨架变化纯顺反 / 手性翻转异构（6 题）

| # | QID | 具体判定归因 | 分子式 / 重原子变化 | `v1.4` 终版 (v6 / v4) | `v1.3` 基线 (v6 / v4) | 底物 SMILES | 参考产物 SMILES |
|---:|---|---|---|---|---|---|---|
| 36 | `BIOPATH150_024__S06__BSY-r03661` | 连接层 InChIKey-14 相同，仅立体/顺反构型不同 | `C8H7O4-` (12 HA) → `C8H7O4-` (12 HA) | Miss / Miss | Miss / Miss | `O=C([O-])[C@@H](O)c1ccc(O)cc1` | `O=C([O-])[C@H](O)c1ccc(O)cc1` |
| 37 | `BIOPATH150_039__S03__BSY-r03728` | 连接层 InChIKey-14 相同，仅立体/顺反构型不同 | `C7H13NO2` (10 HA) → `C7H13NO2` (10 HA) | Miss / Miss | Miss / Miss | `C[N+]1(C)CCC[C@@H]1C(=O)[O-]` | `C[N+]1(C)CCC[C@H]1C(=O)[O-]` |
| 38 | `BIOPATH150_076__S03__BSY-r03779` | 连接层 InChIKey-14 相同，仅立体/顺反构型不同 | `C7H4O6-2` (13 HA) → `C7H4O6-2` (13 HA) | Miss / Miss | Miss / Miss | `O=C([O-])/C=C\C(=O)CC(=O)C(=O)[O-]` | `O=C([O-])/C=C/C(=O)CC(=O)C(=O)[O-]` |
| 39 | `BIOPATH150_081__S06__BSY-r03761` | 连接层 InChIKey-14 相同，仅立体/顺反构型不同 | `C5H13N2O2+` (9 HA) → `C5H13N2O2+` (9 HA) | Miss / Miss | Miss / Miss | `[NH3+]CCC[C@H]([NH3+])C(=O)[O-]` | `[NH3+]CCC[C@@H]([NH3+])C(=O)[O-]` |
| 40 | `BIOPATH150_109__S05__BSY-r03760` | 连接层 InChIKey-14 相同，仅立体/顺反构型不同 | `C6H11O8S-` (15 HA) → `C6H11O8S-` (15 HA) | Miss / Miss | Miss / Miss | `O=S(=O)([O-])C[C@H]1O[C@H](O)[C@H](O)[C@@H](O)[C@@H]1O` | `O=S(=O)([O-])C[C@H]1O[C@@H](O)[C@H](O)[C@@H](O)[C@@H]1O` |
| 41 | `BIOPATH150_145__S05__BSY-r03760` | 连接层 InChIKey-14 相同，仅立体/顺反构型不同 | `C6H11O8S-` (15 HA) → `C6H11O8S-` (15 HA) | Miss / Miss | Miss / Miss | `O=S(=O)([O-])C[C@H]1O[C@H](O)[C@H](O)[C@@H](O)[C@@H]1O` | `O=S(=O)([O-])C[C@H]1O[C@@H](O)[C@H](O)[C@@H](O)[C@@H]1O` |
