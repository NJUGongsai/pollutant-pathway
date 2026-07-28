# MT-D3 聚合排序 tie-break 口径冲突澄清问询

日期：2026-07-28
定位：本文是一份**问询件（TEACHER_QUERY）**，用于澄清 OrganismAggregator（酶→菌聚合层）排序主键 **tie-break（同分排序）口径**上的一处口径冲突。
起因：我在导师侧把酶→菌聚合层对齐你的权威实装（`microbe_crew`，15 tests passed）时发现——聚合主键的 **tie-break 规则**在「我此前的裁定文」与「你已实装并声明 DECIDED_AND_IMPLEMENTED 的版本」之间**不一致**。二者主排序键相同，仅 tie-break 不同，但足以改变同分候选菌的最终名次，进而影响选菌层 Top-K 呈现。**在你回复前，我暂按你的实装口径运行并已在代码注释留档，不擅自改回**。

依据（两处原文）：
- 我的裁定：`TEACHER_REPLY_MTD5_ACCEPTED_AND_MTD1_D8_DECISIONS_2026-07-16.md` §MT-D3
  > v1 默认实现锁 **B（supporting-enzyme 数量降序 + UID 升序 tie-break）**
- 你的实装与声明：`M3_2026_07_23_24_TEACHER_TASK_LIST_FINAL_RESPONSE_2026-07-27(1).md` §D3 / §4 aggregator
  > 状态：DECIDED_AND_IMPLEMENTED
  > supporting-enzyme count descending
  > **NCBI taxon ID numeric ascending tie-break**
  > 证据：`organism_aggregator.py`（15 passed）

冲突摘要：

| 维度 | 我的裁定（07-16） | 你的实装（07-27，15 tests） |
|---|---|---|
| 主排序键 | supporting-enzyme count 降序 | supporting-enzyme count 降序 ✅ 一致 |
| **tie-break** | **UID 升序** | **NCBI taxon ID 数字升序** ❌ 冲突 |
| 状态 | v1 默认锁 B | DECIDED_AND_IMPLEMENTED |

---

## A. 冲突事实确认（必答）

**A1.（必答）** 你在 07-27 把 tie-break 实装为 **NCBI taxon ID 数字升序**、并标注 `DECIDED_AND_IMPLEMENTED`。请确认：这是**有意识地相对 07-16 裁定做的调整**，还是**当时未注意到裁定文写的是 UID 升序**？（我需要判定这是"改进提案"还是"实装偏差"。）

**A2.（必答）** 若为有意调整，请给出**技术理由**：为什么 taxon ID 数字升序优于 UID 升序作为 tie-break？（例如：候选菌主键本就是 `ncbi_taxon_id`，按 UID 升序需回溯到组内代表酶的 UID，存在"用哪条 UID 代表该组"的二义性；而 taxon ID 升序在聚合后天然唯一、可复现——如果你的理由是这一类，请明确说明。）

## B. 可复现性与确定性

**B1.** 两种 tie-break 是否都能保证**完全确定、可复现**（同输入→同名次）？UID 升序在"一个 taxon 组由多条 UID 支撑"时，用于比较的是哪条 UID（组内最小 UID？代表酶 UID？）？请说明你实装里 taxon ID 升序的比较对象就是聚合后的 `ncbi_taxon_id` 本身。

**B2.** 15 个测试里是否有**专门覆盖 tie-break 的用例**（即构造 supporting-enzyme count 相同的两个 taxon，断言其相对顺序）？若有，请指出用例名；若无，这是我裁定前需要补的一项。

## C. 影响范围

**C1.** 此 tie-break 仅在 **count 相同**时生效。请你评估：在真实酶池规模下，count 打平的 taxon 组**是否常见**？（若极少发生，则口径分歧的实际影响有限，我倾向直接采纳你的实装口径消差；若常见，则需要更谨慎裁定。）

---

## 我的裁定计划（你回复后执行）

- 若 A1=有意调整且 A2 理由成立（taxon ID 升序在聚合语义下更无歧义、更可复现）：我将**正式采纳 taxon ID 数字升序**，更新 07-16 裁定文的 MT-D3 条目，消除文档与代码的口径分歧，你的实装无需改动。
- 若 A1=实装偏差：我会与你确认改回 UID 升序的成本，或就地把裁定文更新为 taxon ID 升序（以简单可复现为准）——两种都可，取决于 B1/B2。

**在你回复前**：导师侧代码维持 taxon ID 数字升序运行（与你实装一致），并在 `organism_aggregator.py` 保留 tie-break 口径待裁定的注释。此项为 P0，因为它是文档与代码之间唯一未消解的口径分歧。
