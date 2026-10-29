# L2 Stage 2 Step 0–2 诊断报告：判分侧身份归一（canonical identity）

> **题域标签：[298 域] = RHEA 通用酶学 / 已见题（post-hoc）。** 本文所有题数、比例与归因
> 只在该题域成立，与 dev 域双向不外推；298 是已见题，本诊断不构成能力进步证据。
>
> 日期：2026-10-26。执行：notebook `crdnotebook-2113560935535583233-aclhl3hbth-81040`。
> 性质：**零模型调用、零网络、零付费、零生产代码改动**。P2 B 臂（v2card）当时在跑，
> 本会话只读 `ps` / 哈希 / r2 数据与 Stage 1 重放产物，**未写 `iter/data/`、未写
> `ppv1_hpc/`、未碰 P2 批根/runs**。Step 3（改代码）未启动。
>
> 任务书：`docs/TASK_L2_STAGE2_PILOT_2026-10-26.md`
> 预注册：`docs/L2_STAGE2_PILOT_PREREG_2026-10-26.md`（签字版 SHA256
> `7ca3c0301deb7f120b7150f92cca60cdc8441ae2bc72b8e58141a3181c189e74`）

---

## 0. 结论先行

| 项 | 结果 |
|---|---|
| **诊断门** | **未过门**：可回收 **0 题**（门限 ≥10） |
| suspicious | **0**（无新增判等；无可疑放宽） |
| 基线复现 | **298/298 status + rank**；hit@1/3/5 = **89/118/125**，与 r2 基线逐题相同 |
| 正负控 | **9/9 通过**；raw 口径下负控零违规（基线无“该判不等却判等”的 bug） |
| 四桶覆盖 | 94 + 25 + 41 + 12 = **172**（119 unmatched + 53 partial 全覆盖） |
| Step 3 | **不启动**（按预注册 §6 止损） |

**一句话：** 当前 S5B 的 strict 身份比较**两侧都已经走 `_identity_key`**——原子映射号、芳香/
Kekulé、显式/隐式 H、括号冗余这四类白名单归一**在 raw 里已经全部做完**。本诊断追加的
canonical 白名单归一，在 **645 个参考身份 + 2415 个候选状态身份上逐字 no-op（0 个字符串改变）**。
所以 172 道非 strict 题不是“表示不同”造成的：

- **53 道 partial（41 非空池 + 12 空池）**：全部必要节点的 raw strict 匹配**已经存在**，
  卡点是事件参与物覆盖不精确（多出/缺少/混合），**不是身份**；
- **119 道 unmatched**：身份差是 **composition 79 / stereo 35 / constitution-or-tautomer 5**，
  都是真化学差（分子式不同、立体异构、连接方式不同），不是同一分子的另一种写法。

**建议：** 按任务书停，如实写“身份归一不是当前瓶颈”；下一候选按任务书为 element 7 题 /
no_alignment 28 题。**不进入 Step 3。**

---

## 1. Step 0：环境、哈希与 S5B 身份比较调用链

### 1.1 并发与环境

| 项 | 实测 |
|---|---|
| 主机名 | `crdnotebook-2113560935535583233-aclhl3hbth-81040` |
| 开工/收工 | 2026-10-26 19:05:25 +0800 / 19:20:15 +0800 |
| P2 是否在跑 | **在跑**：`p2_nb_entry.py run --full-arms v2card`（pid 39962）、`p2_run_wrapper.py --arm v2card`（pid 40240），多个 `s5b_worker` 写 `ppv1_hpc/runs/p2_298_20261026_v2card` |
| 本会话与 P2 的关系 | 只读；未写任何 P2 批根/runs/收据；未在同一目录并发写 |
| Python / RDKit | 3.11.9 / 2026.03.5 |
| r2 数据完整性 | `iter/data/r2/SHA256SUMS` **894 OK / 0 FAILED**；cases / reference_graphs / run_inputs / runs 各 298 |
| `baseline/metrics.json` | SHA256 `ceb9e72ea34d14ee95d2432b44ccce3c82b2d935fa0f5333de2d8a890cb0c7f6` |

### 1.2 四个代码哈希（开工与收工各核一次，均未变）

| 文件 | SHA256（64 位） | 判定 |
|---|---|---|
| `evaluation.py` | `37c092310d34d9f417234ccacd508942b3ce3edef640c73ab94022fd8dc75ad8` | 未变 |
| `s5b_scoring.py` | `4af3ed2d60f97a3460df92027d2bb2b280b92c5956e81c475ee262cf33549ca3` | 未变 |
| `s5b_compiler.py` | `58cf3dc94dd83cbf8245c9e2117ac50f41e847c685663321af973f637fba7058` | 未变 |
| `chemstate.py` | `495d3d0e8ad5fb40d7d557a865a51a1e07d8e51f73e8775a6d72f9842861fdeb` | 未变；**这是 2026-10-26 15:49 P2 CN 修复后的基线** |

`chemstate.py` 的 P2 修复只改 `cn_identity` 的推导来源（`_legacy_cn_identity(identity)` 而非
`structure`），不改 strict 身份键；本试点全程使用该当前版本，未回修前版本。

### 1.3 S5B 身份比较实际调用链（Step 0 必答项）

**结论：S5B strict 走的就是 `_identity_key`，且参考侧与候选侧共用同一函数。**

```
s5b_scoring.score_s5b_batch
  → evaluate_scientific(...)                              s5b_scoring.py:335
  → 节点匹配：
      ref_strict = strict_identity_of(node["structure_smiles"])
                                                          evaluation.py:2258
      chemstate.strict_identity_of                         chemstate.py:917
        → return _identity_key(mol)                        chemstate.py:933
      chemstate._identity_key                              chemstate.py:180
        - 去除原子映射号（SetAtomMapNum(0)）
        - 去除 atom props / conformer / DATA SGroup
        - 保留增强立体组 / 自由基 / 同位素 / 电荷 / 立体（基串）
        - ABS 注解按令牌级剥离
        - RDKit MolToCXSmiles（芳香/Kekulé 由 RDKit 感知归一）
  → 候选侧：
      pred_strict = state["smiles_isomeric"]               evaluation.py:2276
        _export_states 读 payload body                     evaluation.py:2142
        build_chemical_state 写入 identity = _identity_key(mol)
                                                          chemstate.py:702,711
  → 比较：pred_strict == ref_strict（**字面字符串相等**） evaluation.py:2277
```

因此“映射号导致不等”的假设**在 raw 口径下已经不成立**：映射号在 `_identity_key` 内就被剥掉；
芳香/Kekulé、显式/隐式 H、括号冗余也都由 RDKit 的 `MolToCXSmiles` 归一。Step 1 的正控
（P1–P3）用真实 r2 态实测确认了这一点，Step 2 的 no-op 统计也确认了这一点。

---

## 2. Step 1：正负控（真实 r2 态）

样本来源：r2 export payload 的真实 state 身份；P1–P3 是在真实态上做 RDKit 确定性改写
（加映射号 / Kekulé 化 / 加显式 H），不是编造新分子；N1–N3 是真实态对；N4 是真实
unmatched qid。完整身份串落在 notebook `iter/rounds/r001/controls/controls_full.json`；
本报告与仓库证据只写 sha16、分子式、电荷与差异类别（脱敏）。

| 控 | 内容 | 来源（qid 前缀） | 期望 raw / canonical | raw 实测 | canonical 实测 | 判定 |
|---|---|---|---|---|---|---|
| **P1** | 带原子映射号 vs 去掉映射号的同结构 | `RXNG_043656…`（真实态派生；sha16 `038503…` vs 映射版） | 等 / 等 | **判等** | **判等** | 通过 |
| **P2** | 芳香式 vs Kekulé 式同一分子 | `RXNG_103c84…`（真实态派生；sha16 `475294…` vs Kekulé 版） | 等 / 等 | **判等** | **判等** | 通过 |
| **P3** | 显式 H vs 隐式 H 等价表示 | `RXNG_043656…`（真实态派生；sha16 `038503…` vs AddHs 版） | 等 / 等 | **判等** | **判等** | 通过 |
| **N1** | 立体异构（R/S 不同） | `RXNG_526bcc…`（真实参考/状态对；C6H5Cl5；sha16 `07e2eb…` vs `65281b…`） | 不等 / 不等 | **判不等** | **判不等** | 通过 |
| **N2** | 位置异构（取代位不同） | `RXNG_164844…`（同题两个真实态；C12H11NO3；sha16 `949128…` vs `bd64c4…`） | 不等 / 不等 | **判不等** | **判不等** | 通过 |
| **N3** | 电荷/质子化态不同 | `RXNG_a16ff4…` vs `RXNG_18a3c0…`（真实羧酸根/羧酸；C5H5O3- vs C5H6O3） | 不等 / 不等 | **判不等** | **判不等** | 通过 |
| **N4a** | 已知应 unmatched（94 桶，composition） | `RXNG_036534…` | 非 strict / 非 strict | unmatched | unmatched | 通过 |
| **N4b** | 已知应 unmatched（94 桶，stereo 近失，Tanimoto=1.0） | `RXNG_0567e1…` | 非 strict / 非 strict | unmatched | unmatched | 通过 |
| **N4c** | 已知应 unmatched（25 桶，composition） | `RXNG_11aa04…` | 非 strict / 非 strict | unmatched | unmatched | 通过 |

**判定函数路径**（所有控共用）：

```
s5b_scoring.score_s5b_batch (s5b_scoring.py:335)
→ evaluation.py:2258 strict_identity_of → chemstate.py:917 → chemstate.py:933
→ chemstate._identity_key (chemstate.py:180)
→ evaluation.py:2276-2277 pred_strict = state["smiles_isomeric"]; 字面 ==
```

**关键读数：**

1. **P1–P3 在 raw 下已经判等**，说明白名单四类归一**不是缺口**；canonical 只是重复了
   raw 已经做的事。
2. **N1–N3 在 raw 与 canonical 下都判不等**；raw 没有“该判不等却判等”的基线 bug。
3. **N4a/b/c 在 canonical 下仍非 strict**；没有把已知 unmatched 洗成 strict。
4. N3 的差异类别在机械分类里记为 `composition`（分子式差 1 个 H），实质是质子化/电荷差；
   这不影响“判不等”的结论。

---

## 3. Step 2：全 298 四桶诊断门

### 3.1 方法（零 LLM）

- **范围：298 题全量**，不只 94+41。
- **数据：** Stage 1 全 298 重放基座——`iter/worktrees/full298/score/data`（cases 携带 replay
  export digest）+ `iter/worktrees/full298/work/runs`；参考图/基线仍指向 r2 只读副本。
- **raw 口径：** 直接调用生产 `evaluate_scientific(criteria_version=v2)`；候选 payload 从
  `native_export/<digest>/payload.json` 读取，并逐个核对 manifest 的 `payload_sha256`
  （298/298 通过）。raw 结果**必须复现 r2 基线**：实际 **298/298 status + rank 一致**，
  hit@1/3/5 = **89/118/125**。
- **canonical 口径：** 仅在进程内 monkey-patch 两个身份入口（跑完恢复，源码零改动）：
  1. `evaluation.strict_identity_of` → 先走原 raw 身份，再做白名单 base-SMILES 归一；
  2. `evaluation._export_states` → 把候选 `smiles_isomeric` 做同一归一。
  canonical 归一只做：**原子映射号剥离 / 芳香-Kekulé 归一 / 显式-隐式 H 归一 / 括号冗余
  归一**；**保留 CX 注解段（增强立体 AND/OR、Sg）逐字不变**，不改节点/边判定结构、不加
  近似匹配、不碰 `s5b_scoring.py` 主口径聚合。
- **suspicious 判据：** canonical 后新判等、但独立 RDKit 判定（canonical isomeric SMILES
  含立体/电荷 + Standard InChIKey）不等价，或差异类别不在白名单内 → 计入 suspicious。

### 3.2 四桶结果（合计 172）

| 签字标签 | 本报告的可复现操作定义 | 题数 | canonical 新增 strict | 节点级身份翻转 | suspicious |
|---|---|---:|---:|---:|---:|
| unmatched 非 remap（94） | unmatched、池非空、`model_calls>0`（即既有“unmatched 其它”） | **94** | **0** | 0 | 0 |
| unmatched remap（25） | 其余 unmatched：空池 23 + 零调用 2 | **25** | **0** | 0 | 0 |
| partial 非空池（41） | partial、池非空 | **41** | **0** | 0 | 0 |
| 空池（12） | partial、池为空 | **12** | **0** | 0 | 0 |
| **合计** | — | **172** | **0** | **0** | **0** |

> **口径披露（必须看）：** 签字预注册把 25 写成“unmatched remap”，但 r2 实际
> `template_remap` 交叉表是 **unmatched remap 69 / 非 remap 50；partial remap 25 /
> 非 remap 28**。能同时复现 94/25/41/12 且覆盖全部 172 题的操作分区，是上表的
> “其余 unmatched（空池 23 + 零调用 2）”。为了不漏 remap 题，下表另报**真实 remap
> 交叉表**；两个视图都覆盖全部 172 题，结论一致（全 0）。

### 3.3 真实 template_remap 交叉表（覆盖 172 题）

| 状态 | remap | 题数 | 新增 strict | 节点级身份翻转 | suspicious |
|---|---|---:|---:|---:|---:|
| unmatched | 是 | 69 | 0 | 0 | 0 |
| unmatched | 否 | 50 | 0 | 0 | 0 |
| partial | 是 | 25 | 0 | 0 | 0 |
| partial | 否 | 28 | 0 | 0 | 0 |

“remap 桶里的 identity 题会漏”这一担心已被覆盖：69 道 unmatched remap 全部逐题跑了
canonical 口径，**0 题可回收、0 个节点身份翻转**。

### 3.4 为什么不可回收：逐题归因

对 119 道 unmatched，取每个“必要且 raw 无 strict 命中”的节点，找与其最接近的候选
state 身份，做机械差异分类（不评判化学机制）：

| 归因类别 | 题数 | 含义 | 是否白名单表示差 | 可回收？ |
|---|---:|---|---|---|
| `composition` | **79** | 分子式不同（不同分子/不同元素组成） | 否 | 否 |
| `stereo` | **35** | 同分子式、同电荷、去立体后 canonical SMILES 相同；R/S 或 E/Z 不同；**Tanimoto 全部 = 1.0** | 否（立体是真化学事实） | 否（除非非法去立体） |
| `constitution_or_tautomer` | **5** | 同分子式/同电荷，但连接方式不同（位置异构/互变异构） | 否 | 否 |
| `coverage_only_all_required_nodes_strict` | **53** | partial 桶：全部必要节点 raw strict 已命中；卡在事件参与物覆盖 | 不适用 | 身份归一不能修 |

按四桶拆：

| 桶 | composition | stereo | constitution/tautomer | coverage-only |
|---|---:|---:|---:|---:|
| unmatched 94 | 59 | 31 | 4 | 0 |
| unmatched 25 | 20 | 4 | 1 | 0 |
| partial 41 | 0 | 0 | 0 | 41 |
| 空池 12 | 0 | 0 | 0 | 12 |

**可回收逐题清单：空（0 题）。** 没有“同一化学实体的另一种合法写法”被误判不等；
因此没有“原来哪两个身份串被误判不等”的条目可列。若需要逐题证据，见
`diag/diag_per_qid.json`（每题给出必要节点、raw/canonical strict 状态数、最接近身份对的
sha16/分子式/电荷/类别/Tanimoto；不含完整结构串）。

### 3.5 canonical 是 no-op 的硬证据

| 对象 | 数量 | canonical 后字符串改变数 |
|---|---:|---:|
| 参考图节点身份（`strict_identity_of(structure_smiles)`） | 645 | **0** |
| 候选 state 身份（`smiles_isomeric`） | 2415 | **0** |

这解释了 0 可回收：不是“canonical 没跑”，而是 raw 身份串**已经**是白名单归一后的
canonical CXSMILES；再套一层 base-SMILES canonicalization 不改变任何字符串。

### 3.6 suspicious 判定

canonical 新增 strict = 0，因此**没有新增判等对**；suspicious = **0**。
额外用独立 RDKit 检查（canonical isomeric SMILES 含立体/电荷 + Standard InChIKey）核对：
没有“canonical 判等但化学不等价”的对。

### 3.7 门判定

**未过门。** 可回收 **0 < 10**；suspicious **0**。

原因类别：**不是 identity 表示层**，而是：
1. **partial 53 题**：全部必要节点已 strict，身份归一无法改变事件参与物集合；
2. **unmatched 119 题**：79 题分子式不同、35 题真立体异构、5 题连接方式不同。

按预注册 §6 第 1 条：停，不实施；按任务书列下一候选（element 7 / no_alignment 28）。

---

## 4. 敏感性/边界证据（**不是门口径**，全部黑名单）

为了证明“0 可回收”不是因为诊断补丁无效，另跑了两个**故意过宽、已列入黑名单**的口径：

| 过宽口径 | 新增 strict | 掉出 strict（l） | 读法 |
|---|---:|---:|---|
| `drop_cx_enhanced_stereo`（丢掉增强立体/Sg CX 注解） | **0** | 0 | 本批没有“仅 CX 注解不同”的身份对；白名单外扩也救不回题 |
| `drop_stereo`（去掉全部立体） | **31** | **3** | 只有**非法去立体**才能把 31 道真立体异构题洗成 strict；这 31 题全部应计 suspicious，且违反 J3 负控 |

`drop_stereo` 的 31 题同时证明：诊断补丁机制**确实能检测到新增 strict**（canary 有效），
0 可回收是数据结论，不是补丁失效。该口径不用于门判定、不建议、不实施。

---

## 5. 证明范围与边界

1. **只覆盖 298 已见题（post-hoc）**；不证明泛化到闭卷集/新题，也不证明化学正确性。
2. **raw 复现**：在 Stage 1 replay 基座上，298/298 status + rank 与 r2 基线一致，
   hit@1/3/5 = 89/118/125；canonical 口径同样 89/118/125（无变化）。
3. **数据读取**：候选 payload 直接读 `payload.json` 并核对 native export manifest 的
   `payload_sha256`（298/298 通过），**未走**生产 `read_native_export` 的 ledger/authority/
   endpoint 完整首消费链（见 §6 偏离 2）。Stage 1 已逐 artifact 证明 replay 与冻结 payload
   语义相等；本轮 raw 复现到基线 status/rank 是该结论的再次核对。
4. **身份分类是机械分类**：composition/stereo/constitution 只描述字符串/图差异，不认证
   反应机制、生物可行性或参考图完备性。
5. **P2 并发**：全程只读；四哈希开工/收工一致；未写 P2 批根/runs；未写 `iter/data/`。
6. **`chemstate.py` 15:49 修复**：本试点以 `495d3d0e…` 为基线；该修复只影响 `cn_identity`，
   不改变 strict 身份键。

---

## 6. 偏离任务书的地方（如实登记）

1. **四桶标签与数据不一致。** 签字预注册写“unmatched remap 25”，但 r2 实际
   `template_remap` 是 unmatched remap 69 / 非 remap 50、partial remap 25 / 非 remap 28。
   本报告用“其余 unmatched（空池 23 + 零调用 2）”复现 94/25/41/12 的算术分区，并另报
   真实 remap 交叉表；两个视图都覆盖全部 172 题。**没有隐藏 remap 题。**
2. **用 Stage 1 replay 产物而不是冻结 r2 导出；也没有重跑 `iter/bin/replay.py`。**
   原因：Stage 1 已交付 298/298 重放与语义等价；本轮直接消费其 score data root +
   replay runs，避免改 `iter/data/` 或重复重放。候选 payload 用直接读取 + manifest sha256
   核对，未走生产 ledger/authority 完整读取链。raw 298/298 复现基线，见 §5.2。
3. **N4 拆成 3 个子例**（94 桶 composition、94 桶 stereo 近失、25 桶 composition），
   比预注册的 1 条 N4 更严；判定仍按“不得变 strict”。
4. **增加两个黑名单敏感性口径**（drop CX、drop stereo）作为边界证据；不参与门判定，
   不实施，`drop_stereo` 明确标注为不可用。
5. **仓库内 controls 脚本做了脱敏**：`bin/controls_redacted.py` 把 N2/N3 的两对真实态
   SMILES 字面量替换为占位符；可运行完整版在 notebook `iter/rounds/r001/scripts/controls.py`。
   仓库证据中所有身份串只保留 sha16/分子式/电荷/类别，不含完整结构串。
6. **没有做的**：Step 3 未启动；未改任何生产模块；未 commit/push；未调用任何模型/网络。

---

## 7. 证据与校验

### 7.1 本地证据根

`/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/l2_stage2_diag_2026-10-26/`

| 路径 | 内容 |
|---|---|
| `bin/diag_all.py` | 全 298 raw/canonical 诊断主脚本（只读，monkey-patch 后恢复） |
| `bin/controls_redacted.py` | 正负控脚本（N2/N3 字面量脱敏；完整版在 notebook） |
| `bin/sensitivity.py` | 黑名单过宽口径敏感性脚本 |
| `bin/diag_probe.py` | 首轮评估器输出结构探针 |
| `diag/diag_summary.json` | 汇总：哈希、调用链、四桶、remap 交叉表、门判定 |
| `diag/diag_per_qid.json` | 298 题逐题：状态、桶、池空/remap/调用数、必要节点、身份对 sha16/分子式/电荷/类别/Tanimoto（无 InChIKey、无完整结构串） |
| `diag/diag_status_map.json` | baseline/raw/canonical 逐题 status + rank |
| `diag/diag_recovered_pairs.json` | 可回收身份对（本轮为空 `[]`） |
| `diag/sensitivity.json` | drop CX / drop stereo 结果 |
| `controls/controls_redacted.json` | 9 条正负控（脱敏） |
| `logs/` | 三次运行 stdout、开工/收工四哈希 |
| `record.json` | 主机、时间、P2 并发、数据/代码哈希、命令、结果、写入边界 |
| `SHA256SUMS` | **16 个文件，16 OK / 0 FAILED**；`SHA256SUMS` 自身 sha256 见 `SHA256SUMS.sha256` |

### 7.2 notebook 落盘

`/root/v43_migration/iter/rounds/r001/`

| 路径 | 内容 |
|---|---|
| `scripts/{diag_all.py,controls.py,sensitivity.py,diag_probe.py}` | 完整可运行脚本 |
| `controls/controls_full.json`、`controls_redacted.json` | 完整/脱敏控 |
| `diag/diag_summary.json`、`diag_per_qid.json`、`diag_status_map.json`、`diag_recovered_pairs.json`、`diag/sensitivity.json` | 诊断产物 |
| `logs/` | 运行日志与四哈希 |
| `record.json` | 环境/边界记录 |
| `report.md` | 本报告副本 |

### 7.3 校验结果

- 本地 `shasum -a 256 -c SHA256SUMS`：**16 OK / 0 FAILED**。
- r2 数据 `sha256sum -c SHA256SUMS`：**894 OK / 0 FAILED**。
- 代码四哈希：开工 19:05 与收工 19:20 **完全一致**（见 `logs/code_hashes_initial.txt` /
  `logs/code_hashes_after.txt`）。
- 报告自身 sha256 登记在 `record.json` 的 `report_sha256` 字段（报告文件不在证据
  `SHA256SUMS` 内，避免自引用）。

---

## 附录 A：35 道 stereo 近失题（qid 级）

这 35 题的共同特征：必要节点与最接近候选状态**同分子式、同电荷、去立体后 canonical
SMILES 完全相同、Tanimoto=1.0**，但 R/S 或 E/Z 不同 → raw 判不等；canonical 正确保持不等。
它们不是“表示层误判”，而是本批最像 identity 的 35 个真立体异构案例。

```
RXNG_0567e10c5b9952b246b096964c7a6e179306f0fe3b2853d43447d3dc12269678
RXNG_0ecc3c755537e694db0310fa58dc00cb423604bb88ed6def9aee4418dff6b16d
RXNG_249b9956c0b5dbbc13be57918505bbe232fbd60505da0630bb61f3cc82b13414
RXNG_2b091d5531c746da0a4cf4d7bb7bf02ba1aa34a9d6765575769114cb4211d9a8
RXNG_35a46ed17cd3c206ad9d0234533c985f30e95a3291563ffcef239365f447eaa4
RXNG_3760e48820802c2f93407d9957c5bef6fed38303dad6314f44e1a5be2f71be13
RXNG_3cdbe17c5f67b3cdd01c5adb43a424b553e7afed86253559c2cb57bd19096210
RXNG_432f2f7cfa5ecf35ed15a4de0aac7285ad87733c8080b80dbeaf81be44a7697c
RXNG_47e0049436912f6e7dd19d22bf26e7305e27ca3215985a04a827a571b5a3648b
RXNG_5132632bb9fe36ab77fe882432bfa04e87b63aefc2fda003a6e99f1f64863564
RXNG_526bccaa52323be2a3209e3c280fb595d997eba34be2257729f559a272e42a61
RXNG_57f8007e4c39129205ba9e2210aa8853357b1840eb5f8822618e04a7d3507e47
RXNG_6bdfa9710e1199ecc5613eef7919052000fca052a25396c40b7854ed7c7d64a2
RXNG_6d2b8fd484e961591c9261eb9b0286648df99cbdff1182d30a5fe12c792a99e6
RXNG_74e2fc6a3bb573c21891eeeb5019a2c2695ce82412a3a5b3940b5d626d4a3c6e
RXNG_76682d9fbce33d2481da6b5d74a0f8eb2cf94b45bfb4c72af75a29c26c5107a9
RXNG_7701b6993b95ebfde638f35a13f1abe8db8ff759bf02454fce1b1b2d85dfe290
RXNG_840d50abfec60f462391ff62591259c587f5c7cc48e624baecde1ee919e25e43
RXNG_8bc45c2fa9ffdfea3dac207f5bb506734836749c5393d6c9946d1edef6d37842
RXNG_8f1eda02d28915b95038108c79a959b28d92552c866f259063e3dc8a202e7319
RXNG_a4e33509426969f288254b036b2063e73bc723290a8287cb716b277c8d09be03
RXNG_b980dba7feeecaa7865c090a301978808bb96b37a56750c7cf2322fbd188299a
RXNG_bd4f6f39af2d555bcae7cba6702f9cc0755995bd7f0af42f8482ca751303b32a
RXNG_c48af8091a02e72051ff27d2e3c4434f3be94b6bba3e4b48cf8352a7ee49d202
RXNG_c745f0a1d65aeafcfcf6e86d6f722ff8558a713771fd09eaafe3bee44b0fba7f
RXNG_d23a924f72135e2b9cae0628023bbb18e1d5e0787c8579b723fc38e2e8b89003
RXNG_d41e12c01377c97310a57b3401ed46e6f38d8ea48e34ddb56cb808f797b5dee1
RXNG_e10f66db2bc68d091ce332b7cdcf95eb63ed4fbf4e74e114d7068e454737797f
RXNG_e19ee1be47f17e03f3b4ef362d4357addbfd43613b2a21207728ba03ad2b8ea3
RXNG_eee01aeed9ebd1a309bf0101c26028efe9714583e293dec8411b78ef30c22aa6
RXNG_ef1bef54dae3310a41e2ee55ceee576625847fedf328803cd079c68c5320eb6f
RXNG_efa6ffdfa07dc70c6c85df5174891ae061f7b30d51fb9c4b59662c0d5fb36ba7
RXNG_f834521f979fbf02003dd6180ecced57e4e00e1b340b3f32ba5ac36105952be0
RXNG_fce2c28fb263c86f242772bf9e13687d1db5ec1006d31531616f516ae3fa5562
RXNG_febc7fbd3d797b1a6843b360df926dae8cdce475e292a62455ce6762eee044be
```

## 附录 B：5 道 constitution/tautomer 题（qid 级）

```
RXNG_1a5528f34b65ce23dd087b4a15bb2b254fb592ace2dacae6e4bfbc6941b849d4
RXNG_46c6b17b0697244ba89550472db43c404698d4b568785554ea603b5ef8e4dddd
RXNG_56d8303ebd8a99f21974e52e9174f3a453c7e59071d517fc128b0a9bcd3162ec
RXNG_5876dc9dadf845f4625ac53438a0dc58c915cc4c93caadbae847a1bede5bd02a
RXNG_7bd87d4003757022ec3259374973dc5ef894b91478cdf84607298ba14f9ab34c
```