# P0-1 师姐裁定·附问件（2 件：recorded 声明式反应的 O 来源口径，2026-10-18）

> 配套主包：`docs/P0_1_SISTER_ARBITRATION_PACK_2026-10-18.md`（12 件主裁定）——本附问件可随主包一起送或后送，互不影响。自包含零金标；格式同主包：一行一裁定。
> **问题背景**：机器管线的 recorded 通道按「记录声明」编译反应（记录只给 donor→product 对）；而判读规则的「产物原子来源闭合」读法要求产物每个原子可溯至给定证据集。下列 2 件**管线编译通过**（判读者按来源闭合读法却会判拒）——两套语义打架，请裁定化学实质与判读口径。

## 附问 1 `cap-54f4f96b7d19ced2`（bt0049#r0225，recorded 通道）

**材料**
- 题底物（substrate_smiles）：`C=Cc1ccccc1`（苯乙烯）
- 证据记录：record_key `bt0049#r0225`（channel=recorded）
- 证据 donor：`C=Cc1ccccc1`
- 证据 product：`C1OC1c1ccccc1`（苯乙烯环氧化物）
- 模板：（空）

**分歧**：记录声明的反应是「苯乙烯→环氧苯乙烷」，但证据集内**没有任何 O 供体**（环氧化物的 O 无来源）。
**裁定问题**：这类「记录声明成立、O 供体未声明」的件，化学实质上应判 pass_expected（声明反应成立，O 来自未声明的环境共底物如 O₂/H₂O₂）还是 reject_correct（证据集自洽配平要求 O 来源）？判读规则应采哪种口径（或按通道分口径）？

## 附问 2 `cap-909d1d61d66e6d5c`（bt0036#r0265，recorded 通道）

**材料**
- 题底物（substrate_smiles）：`Cc1ccccc1`（甲苯）
- 证据记录：record_key `bt0036#r0265`（channel=recorded）
- 证据 donor：`Cc1ccccc1`
- 证据 product：`OCc1ccccc1`（苯甲醇）
- 模板：（空）

**分歧**：同上——苄位羟基化引入的 O 在证据集内无来源。

**裁定问题**：同附问 1。

## 回复格式（2 行）

`case_id | pass_expected 或 reject_correct 或 uncertain | 一句话化学理由`
外加一行口径意见：`O 来源口径：声明式放行 / 证据集闭合 / 分通道分口径（一句话说明）`

> 裁定结果将回填为 v3.1 判读规则的校准样例（修订 2 的开放问题条款）。
