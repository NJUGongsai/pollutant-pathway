# P2 A 臂主产物命中审计（2026-10-27）

> 只读取证：零模型调用、零付费、不写 P2 批根/runs、不改源码。
> 批：`p2-298-20261026` / arm `v1card`
> 批根：`/root/v43_migration/ppv1_hpc/batch/p2_298_20261026_v1card`
> 判分：`ppv1-criteria-v2`（`metrics.json`；`metrics.json.v1` 是 v1 对照）
> 题域：298（RHEA 通用酶学 / 已见题，post-hoc）；分母固定 298

## 0. 结论先行（CC 版）

- **86/298 是 hit@1，不是 strict。** strict = 119/298；失分 179 = 298 − 119 = 140 unmatched + 39 partial。
- **主产物（任一 `principal_product`）严格命中但未 strict：50 题** = 11 unmatched + 39 partial。
  - 若要求“全部声明的主产物都命中”：**39 题**（全部来自 partial）。
  - 若还要求模型显式把命中产物标成 `principal_product`（不接受只放在产物侧、角色写成 coproduct）：任一主产物口径 **50 → 43 题**；全部主产物口径 **39 → 33 题**。
- **140 unmatched 里，129 题根本不是“参与物覆盖不齐”**：主产物没严格做出来（104 题连 CN 都不等；25 题是 CN-only 近失——同骨架，立体/电荷/质子化层不同）。
- **39 partial 全部主产物命中**，且全部只卡在参与物覆盖：35 题 superset（多带参与物）、2 题 subset（少带声明的其它主产物）、2 题 mixed（两者都有）。
- **底物/根节点在 298/298 题都严格命中**；本批失分与底物身份无关，缺口全部在产物侧。

一句话：**179 道失分题里，真正“主产物做对了但被判错”的是 50 道；其中 39 道是 partial（参与物不齐），11 道是 unmatched（多产物题只做对其中的产物）。剩下 129 道 unmatched 是主产物没严格做出来。**

---

## 1. 179 题按 `match_status` 拆分（先对账）

| `main.match_status` | 题数 | 判分含义（人话） |
|---|---:|---|
| `matched_strict` | 119 | 至少有一条参考边找到“参与物集合完全相等”的事件 |
| `matched_participant_coverage_partial` | 39 | 必要节点都有严格命中，但事件里的参与物集合与参考不完全相等（多带或少带） |
| `unmatched_required_node_uncovered` | 140 | 至少一个“声明的必要节点”（根或主产物）没有严格命中；判分链不再进入事件覆盖比较 |
| **合计** | **298** | |

- **对账结果**：`metrics.json` 三桶 = 119 / 39 / 140，与批次 `report.md`、`report_plain.md` 写的 39 / 119 / 140 一致。
- 本次审计用判分链同款 `match_reference_nodes` / `match_reference_edges`（criteria v2）逐题重算，**298/298 题状态完全一致**。
- **口径提醒**：179 是“非 strict”数，不是 298 − hit@1。298 − 86 = **212** 才是“没进 hit@1”的题数；不要把 179 和 212 混用。
- 主口径其他数：hit@1 = 86/298（28.86%）、hit@3 = 112/298、hit@5 = 119/298。

---

## 2. 140 道 unmatched 逐题判定

### 2.1 总表

| 类别 | 题数 | 含义 |
|---|---:|---|
| `main_product_present`（任一主产物严格命中，但缺其它必要主产物） | **11** | 全部是多产物题；缺的是“别的 `principal_product`” |
| `main_product_absent`（没有任何主产物严格命中） | **129** | 主产物没做出来/没对上 |
| `unknown`（判不了） | **0** | 图、payload、解析均正常 |
| **合计** | **140** | |

- **根节点（底物）严格命中：140/140。** 140 题的 162 个“必要节点缺口”**全部在产物侧**：
  - 135 个缺口是 `unmatched`（连 CN 都不等）；
  - 27 个缺口是 `cn_only`（同骨架/同 CN，但严格身份不同，不计 strict）。
- 这 140 题没有任何 `coverage_mismatch`、`exact`、`structure_only` 事件：判分链在“必要节点缺口”这一步就停了，没进入事件覆盖比较。

### 2.2 11 题：主产物命中，但缺别的必要主产物（用户说的 `main_product_present`）

- 11 题全部是多产物题：10 道双产物 + 1 道三产物。
- 缺的其它主产物状态：
  - **9 题**：缺的产物完全无匹配（`unmatched`）；
  - **2 题**：缺的产物是 CN-only 近失（同骨架，严格身份不同）。
- 代表 qid（完整 qid 见证据 `per_qid.json`）：

| qid 前缀 | 产物数 | 模型产物状态（按参考声明顺序） | 说明 |
|---|---:|---|---|
| `RXNG_11aa04de…` | 2 | strict, unmatched | 做对第 1 个，缺第 2 个 |
| `RXNG_1c56dceb…` | 2 | cn_only, strict | 做对第 2 个，第 1 个只是 CN 近失 |
| `RXNG_a30cf37e…` | 3 | unmatched, strict, strict | 做对后 2 个，缺第 1 个 |

### 2.3 129 题：主产物没出现

| 子类 | 题数 | 含义 |
|---|---:|---|
| CN-only 近失 | **25** | 至少一个主产物在 CN（骨架）层对上，但严格身份不同；不计 strict |
| 连 CN 都不等 | **104** | 在判分身份函数下，主产物完全没对上 |
| **合计** | **129** | |

- 25 道 CN-only 近失里：24 道是单产物题（唯一主产物 CN-only），1 道是双产物题（一个 CN-only、另一个完全无匹配）。
- 代表 qid：

| 子类 | 代表 qid 前缀 |
|---|---|
| CN-only 近失（25） | `RXNG_0567e10c…`、`RXNG_0ecc3c75…`、`RXNG_2492077a…` |
| 连 CN 都不等（104） | `RXNG_036534a3…`、`RXNG_04365649…`、`RXNG_05c5a15c…` |

> 口径说明：这里的“命中”一律是 **strict 身份**（`chemstate.strict_identity_of`，与判分链同源）。CN-only 是判分链的旁证档，不算节点严格命中；若把 CN 也算“骨架对上”，这 25 题会进入敏感性口径（见 §5.3）。

---

## 3. 39 道 partial 逐题判定

### 3.1 总表

| 覆盖类型 | 题数 | 含义 |
|---|---:|---|
| superset（事件里多了参考没声明的参与物） | **35** | 26 题只有产物侧多；9 题产物侧和反应物侧都多 |
| subset（事件里缺参考声明的参与物） | **2** | 都是多产物题，事件里少了声明的其它主产物 |
| mixed（既有额外也有缺失） | **2** | 都是多产物题，同时出现 superset 和 partial_subset 事件 |
| **合计** | **39** | |

- **39/39 题的全部 `principal_product` 都严格命中**（node、事件产物、状态存在三轴逐题一致，0 例外）。
- **39/39 题的根节点严格命中**；subset/mixed 缺的也不是底物/反应物，而是“参考声明的其它主产物”。
- **没有“其它”原因**：39 题的 `structure_only_event_count` 全为 0，不存在 step_scope 不一致的干扰；partial 全部只卡在参与物覆盖。

### 3.2 superset 的额外参与物是什么

- 35 道 superset 题中：
  - 26 道只有产物侧额外参与物；
  - 9 道产物侧 + 反应物侧都有额外参与物；
  - 另有 2 道 mixed 也同时有两侧额外（归在 mixed 桶）。
- 额外参与物（按身份去重）：
  - 产物侧 **43 个不同身份**：其中 40 个角色是 `coproduct`，3 个被模型标成 `principal_product`（即模型多报了一个它自己认为是主产物的分子）；
  - 反应物侧 **15 个不同身份**，角色均为 `cosubstrate`。
- 这些额外参与物没有被 v2 的 T-1 豁免全部升格为 exact，所以该事件仍维持 superset → partial。
- 代表 qid：

| 子类 | 代表 qid 前缀 |
|---|---|
| superset 仅产物侧多（26） | `RXNG_04103546…`、`RXNG_04d8e54d…`、`RXNG_08d3aa8a…` |
| superset 两侧都多（9） | `RXNG_03ebc970…`、`RXNG_0eda0ec3…`、`RXNG_167dfdcc…` |

### 3.3 subset / mixed 缺的是什么

- subset（2 题）+ mixed（2 题）全部是多产物题（产物数 2 或 3）。
- 这 4 题合计涉及 **8 个“按题计”的缺失产物身份**：事件里缺的是参考声明的其它主产物，不是底物/反应物（`identity_missing_reactant_count` 全为 0）。
- 代表 qid：

| 子类 | 题数 | 代表 qid 前缀 |
|---|---:|---|
| subset only | 2 | `RXNG_2a805c8f…`、`RXNG_b34d5882…` |
| mixed | 2 | `RXNG_164844b4…`、`RXNG_96836273…` |

---

## 4. 一张表：主产物命中但未 strict

| 行 | 类别 | 题数 | 卡在哪 |
|---|---|---:|---|
| A | unmatched：任一主产物严格命中，但缺其它必要主产物 | **11** | 多产物题的其它产物缺失（9 无匹配 + 2 CN-only） |
| B | partial：全部主产物严格命中，覆盖 = superset | **35** | 事件多带参与物（26 产物侧 + 9 两侧） |
| C | partial：全部主产物严格命中，覆盖 = subset | **2** | 多产物题事件少带其它声明产物 |
| D | partial：全部主产物严格命中，覆盖 = mixed | **2** | 既有额外也有缺失 |
| — | **主产物（任一）命中但未 strict 合计** | **50** | A+B+C+D |
| — | **全部主产物命中但未 strict** | **39** | B+C+D |
| — | **显式 `principal_product` 角色口径（任一主产物）** | **43** | 50 题中 7 题的金标产物只以 coproduct 角色出现 |
| — | **显式 `principal_product` 角色 + 全部主产物** | **33** | 39 道 partial 中 6 道有主产物只以 coproduct 角色出现 |

补充（不在 50 里，但为了把 179 拆完）：

| 行 | 类别 | 题数 |
|---|---|---:|
| E | unmatched：无严格主产物，但至少一个主产物 CN-only 近失 | **25** |
| F | unmatched：无严格主产物，连 CN 都不等 | **104** |
| G | unknown | **0** |

对账：A + E + F = 11 + 25 + 104 = **140**；B + C + D = **39**；合计 **179**。

---

## 5. 与用户口径的差异说明

### 5.1 “节点命中”和“主产物命中”不是一回事

判分链的“节点命中”是**逐必要节点**的严格命中；参考边的必要条件 = **根节点（底物）+ 所有声明的 `principal_product` 节点**。规则是（S5A-03）：

1. 任一声明的必要节点没有严格命中 ⇒ 该题 `unmatched_required_node_uncovered`，**不再看事件覆盖**；
2. 所有必要节点都严格命中 ⇒ 才扫描事件；事件参与物集合与参考完全相等才 `matched_strict`，多/少则 `matched_participant_coverage_partial`。

本批的特殊之处：**根节点 298/298 都严格命中**。所以：

- 单产物题（253 道）：主产物节点命中 = 主产物命中。在本批实际出现的三桶里，单产物题只要主产物严格命中（根又恒命中），就会落到 strict 或 partial；本批 140 道 unmatched 全部是 `required_node_uncovered`，没有“节点都命中但事件不搭桥”的 plain unmatched。
- 多产物题（45 道）：判分要求**所有**主产物节点都命中；只做对其中的产物仍会 unmatched。这正是 11 道 `main_product_present` unmatched 的来源。
- “节点命中”比“任一主产物严格命中”更严的差额 = **11 题**（多产物完整性）。
- 另有 **27 题**是“严格身份 vs CN 骨架身份”的差异（25 题在 absent 桶、2 题在 11 题的 subset 桶）；这属于身份轴，不是“节点命中 vs 主产物命中”的差额。

### 5.2 为什么 50 和 43 不一样

- **50** 是按判分链的“产物侧参与物集合”（`side=product`，**不区分 role**）算的；判分链的节点匹配和边覆盖都只看身份和 side，不看模型自己写的 role。
- **43** 是额外要求“至少一个命中产物被标成 `principal_product`”算的；若要求“全部主产物都标成 `principal_product`”，则是 **33**。
- 差额：50 → 43 少 7 题（金标产物在模型事件里只以 `coproduct` 角色出现，从未标成 `principal_product`）；39 → 33 少 6 题（partial 里也计入这类角色差异）。
- 这 7 题里：4 题在 11 道 unmatched subset 中，3 题在 39 道 partial 中。
- 上述 3 道 partial 也正是 §3.2 里“模型多报了一个 `principal_product`”的 3 道题：模型把另一个分子标成了主产物，金标主产物只以 coproduct 出现。

### 5.3 如果把 CN-only 也算“骨架对上”

- strict 口径：**50** 题（本文主答案）。
- 若把 `cn_only`（同 CN/同骨架、严格身份不同）也算任一主产物命中：**75** 题（50 + 25 道 absent 桶的 CN-only 近失）。
- 若还要求所有主产物都在 CN-or-strict 层命中：**65** 题。
- 这些不是 strict 口径，不能进 hit@1 / strict 指标；列在这里只是为了解释“为什么用户直觉上可能觉得不止 50”。

### 5.4 179 和 212

- **179** = 298 − 119 strict = 39 partial + 140 unmatched。
- **212** = 298 − 86 hit@1。
- 用户说的“179 道失分题”对应前者；若按 hit@1 口径，失分是 212 道。两个数不要混。

---

## 6. 证据与复现

### 6.1 文件

| 文件 | 路径 |
|---|---|
| 本报告 | `/Volumes/CC/Enzyme_Agent/dependingv43/docs/P2_MAINPRODUCT_HIT_AUDIT_2026-10-27.md` |
| 审计脚本 | `/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/p2_mainproduct_audit_2026-10-27/audit_mainproduct.py` |
| 逐题 JSON（298 条） | `/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/p2_mainproduct_audit_2026-10-27/per_qid.json` |
| 聚合 JSON | `/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/p2_mainproduct_audit_2026-10-27/aggregate.json` |
| SHA256SUMS | `/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/p2_mainproduct_audit_2026-10-27/SHA256SUMS` |

notebook 侧中间产物（只读消费，未写批根/runs）：
`/root/v43_migration/iter/audit_mainproduct/`

### 6.2 关键哈希

| 对象 | SHA256 |
|---|---|
| `metrics.json` | `0510febdd4ed50965be21ad3099342a4e4d1d59f66551bb4bbffb8aac9cfe912` |
| `batch_manifest.json` | `7e27e87b05aea94227c6282113679f0b0edc14eaff14abe33a22265c2d707ef3` |
| `evaluation.py`（代码根） | `37c092310d34d9f417234ccacd508942b3ce3edef640c73ab94022fd8dc75ad8` |
| `chemstate.py`（代码根） | `495d3d0e8ad5fb40d7d557a865a51a1e07d8e51f73e8775a6d72f9842861fdeb` |
| `audit_mainproduct.py` | `90ece1a58601e9e6ed7be177a46652617efc3e70b1af5d3f39b587d53b6e88cf` |
| `per_qid.json` | `a97a1b4536c05d835ccfd722f2805106c8522f5e002be247aa0f2720eb7bd993` |
| `aggregate.json` | `b9a6784b3780b99e494e422da475c912d1ee4007ffd888a430cd2d680e9ebb61` |
| `SHA256SUMS` | `5d519c904820cc2fb22368359ce96639c8b8447868c42b8241dec25af849d87e` |

> `SHA256SUMS` 里以本地证据目录的实际文件为准；notebook 侧同名文件与本地哈希一致（已逐一核对）。

### 6.3 复现

```bash
cd /Volumes/CC/Enzyme_Agent/dependingv43
# 脚本已在 notebook: /root/v43_migration/iter/audit_mainproduct/audit_mainproduct.py
bash scripts/hpc/nb_ssh.sh \
  "cd /root/v43_migration/iter/audit_mainproduct && PYTHONDONTWRITEBYTECODE=1 python3 audit_mainproduct.py"
```

- 代码根：`/root/v43_migration/iter/worktrees/repair3`（`evaluation.py` / `chemstate.py` 哈希与本地 `src/` 一致）。
- 参考图：`/root/v43_migration/iter/data/r2/reference_graphs/`（只读消费；图内容哈希与 `batch_manifest.json` 的 `graph_sha256` 298/298 一致）。
- payload：`/root/v43_migration/ppv1_hpc/runs/p2_298_20261026_v1card/<run_id>/native_export/<digest>/payload.json`（只读）。
- 零模型调用、零外网/零付费（仅 SSH 读取 notebook）；未写 P2 批根、runs 或任何源码。

---

## 7. 局限与边界

1. **身份判等是纯代码口径**：参考侧用 `chemstate.strict_identity_of`，模型侧用 payload `states[].payload.smiles_isomeric`（判分链同源），未做任何人工 SMILES 目测。
2. **参考图角色**：本批 298 张图共 347 个产物节点，全部 `role=principal_product`；图内没有 side_product/co_product 角色，因此“主产物”定义没有角色歧义。每个图恰 1 条边，根节点恒 1 个。
3. **事件 role 是模型自报**：判分链只看 `side=product`，不看 role；50/43 的差异已在 §5.2 说明。
4. **partial 的 v2 豁免**：superset 事件按 T-1 做豁免评审；本报告报的是豁免后的最终状态。未逐事件展开豁免明细。
5. **不评价化学机制/生物可行性**：本审计只回答“身份是否对上、卡在哪个判分步骤”，不判断反应是否化学合理。
6. **unknown = 0**：298 题图、payload、解析、匹配全部正常；没有“判不了”的题。