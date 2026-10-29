# v4 判据落码与零漂移验证报告（`matched_product_hit`）

> **题域标签：[298 域] = RHEA 通用酶学 / 已见题（post-hoc）。**
> 本文所有数字只在该题域、该批次（`p2-298-20261026_v1card`）、该分母（298）
> 内成立；与 dev 域双向不外推。零模型调用、零网络、零付费；不 commit / 不 push。
>
> 日期：2026-10-28。执行：notebook
> `crdnotebook-2113560935535583233-aclhl3hbth-81040`。
> 依据：`docs/CRITERIA_V4_MATCHED_PRODUCT_HIT_PREREG_DRAFT_2026-10-28.md`
> §1 定义 / §2 合法事件 / §3 桶 / §4 版本组合。
> 证据目录：`docs/review_evidence/v4_impl_2026-10-28/`（含 SHA256SUMS）。

---

## §0 结论

| 硬门 | 要求 | 实测 | 判定 |
|---|---|---|---|
| v2 基线零漂移 | 119 strict / 86 hit@1 / 298 逐题一致 | **119 / 86 / 298 道逐题 status+rank 全等**；hit@3 112、hit@5 119、partial 39、unmatched 140 | **PASS** |
| v4 主读数（分母 298） | 156 matched / 109 hit@1 / 2 partial / 140 unmatched | **156 / 109 / 2 / 140**；另 hit@3 148、hit@5 156 | **PASS** |
| 翻转对账 | 逐 qid 与 `flips.json` 37 题相同 | **37/37 qid 集合相同、37/37 rank 相同**；0 缺失、0 多余、0 变差 | **PASS** |
| v3 并存 | v3 与 v4 同时启用都正常输出、互不改写 | v3 块 sha 与 v3 单跑**逐位相同**；v4 块 sha 与 v4 单跑**逐位相同** | **PASS** |
| 旧路径零新键 | v1/v2/v3 输出无 `criteria_v4`；v4 无 `criteria_v2` 豁免块 | 全部成立 | **PASS** |
| 测试 | 既有判分类测试全绿（无新增失败） | **561 passed / 4 failed**；4 项均为**预存**失败（生产树同 FAIL，见 §3） | **PASS（条件）** |
| 生产树 / 批根 | 一行不改、只读 | 生产树三文件哈希与改动前相同；批根/runs 16:00 后新文件 **0**（pytest 缓存写入已披露并清理，见 §5.4） | **PASS** |

一句话：**v4 主口径已落码，156 / 109 / 2 / 140 与冻结读数逐数一致，37 题翻转逐 qid
对得上，v2 基线 298/298 原样复现，v3 披露轴并列不改写。**
唯一需要 CC 拍板的是 §5.1：预注册 §3 的 partial 字面 trigger 会给出 13 partial /
129 unmatched，与 §9 冻结读数 2/140 不一致；本次按冻结读数实现，并把另一读数
（13 / 11 题差异集）作为机读披露完整保留。

---

## §1 改动点逐条（文件 / 函数 / 行号）

> 全部改动只在 `/root/v43_migration/iter/worktrees/v4_impl/`（工作副本）；
> 生产树 `/root/v43_migration/v43cP2/` 零改动。行号为**改动后**行号。

### 1.1 `src/pathway_v43/pollutant/evaluation.py`（+586 / −12 行）

| # | 位置（行） | 改动 | 对 v1/v2/v3 的影响 |
|---|---|---|---|
| 1 | 901–903 | 新增 `PPV1_CRITERIA_V4 = "ppv1-criteria-v4"`，加入 `PPV1_CRITERIA_VERSIONS` 白名单 | 无（只加一个 token） |
| 2 | 1015–1050 | `resolve_criteria_version`：docstring/错误文案加入 v4；v4 请求而 `strict_identity_of` 缺席 ⇒ 结构化拒（`criteria_v4_identity_tools_unavailable`） | 合法 v1/v2/v3 token 解析结果不变 |
| 3 | 1163–1171 | `_criteria_exemption_enabled`：v4 返回 False（§4 豁免旁路）；docstring 登记 | 无 |
| 4 | 1182–1215 | v4 常量：预注册文档、指标名 `matched_product_hit`、`hit_mode_scope`、五桶名、参考无效原因、命名纪律/coverage 保留/豁免旁路三条 note | 无（新增常量） |
| 5 | 1217–1227 | `_criteria_v3_disclosure_enabled`：v3 主版本或 v4 并列披露时启用 v3 披露轴 | 缺省空披露清单 ⇒ 与既有行为逐位一致 |
| 6 | 1229–1255 | `_validate_disclosure_criteria_versions`：披露轴白名单只接受 v3；v1/v2/v4 作披露轴 ⇒ 结构化拒 | 缺省零调用 |
| 7 | 1257–1259 | `_criteria_v4_identity_sha256_16`：身份披露用哈希（输出零 SMILES） | 无 |
| 8 | 2327–2534 | `_criteria_v4_edge_product_hit`：单参考边 v4 判定（§1 公式、§2 合法事件、§3 桶、身份函数同一、目标集合只取 `principal_product`、禁止跨事件拼答案、参考无效 fail-closed、零 SMILES） | 无（v4 分支才调用） |
| 9 | 2536–2602 | `_criteria_v4_sample_block`：逐边块 → 题级桶/事件集合（接受边条目嵌套块与裸块） | 无 |
| 10 | 2604–2692 | `_criteria_v4_batch_block`：§3 五桶 + 豁免旁路计数 0 + 旧 `match_status` 桶分列 + §3/§9 差异披露 + v3 并存 note | 无 |
| 11 | 2694–2730 | `match_reference_nodes`：新增 keyword-only `disclosure_criteria_versions=()`；两处 v3 披露条件由 `criteria_version == V3` 改为 `v3_disclosure` | 缺省空 ⇒ 行为逐位不变 |
| 12 | 2816–3050 | `match_reference_edges`：新增 v4 分支——建 `v4_nodes_by_id`，逐边追加 `hit_mode_scope` / `matched_product_hit` / `product_hit_partial` / `product_hit_events` / `criteria_v4` 五键；**coverage 三分、`match_status`、`matched_events`、v2 豁免评审全部原样**（v4 下豁免函数自然返回 False） | 无（非 v4 时 `v4_nodes_by_id is None`） |
| 13 | 4088–4132 | `evaluate_scientific`：新增 keyword-only `disclosure_criteria_versions=()`；首消费处校验披露轴 | 缺省空 ⇒ 逐位不变 |
| 14 | 4395–4418 | 无导出样本：v4 下补 `criteria_v4` 块（参考有效性仍按图判定；无合法事件 ⇒ `unmatched_no_event`，留分母） | 无 |
| 15 | 4420–4434 | 已评样本：v4 下附 `sample["criteria_v4"]` 与四个新键 | 无 |
| 16 | 4706–4709 | 批级：v3 块条件改 `v3_disclosure`；v4 下追加 `output["criteria_v4"]` | 无 |

**明确未改**：`strict_identity_of`（`chemstate.py` 哈希 `495d3d0e…` 生产树与副本逐字节相同）；
coverage 三分（`exact`/`superset`/`partial_subset`）；`match_status` 与 `matched_events`；
v2 豁免三谓词与 tier 逻辑；v3 归一披露与指纹。v4 下 **superset 仍是 superset**，
不改写 exact（模块 docstring 与 v4 note 都写死）。

### 1.2 `src/pathway_v43/pollutant/s5b_scoring.py`（+198 / −1 行）

| # | 位置（行） | 改动 |
|---|---|---|
| 1 | 59–76 | 导入 v4 常量（桶名/metric 名/命名纪律等） |
| 2 | 196–232 | `score_s5b_batch`：新增 keyword-only `disclosure_criteria_versions=()`；docstring 登记 v4 |
| 3 | 355–359 | `evaluate_scientific(..., disclosure_criteria_versions=…)` 透传 |
| 4 | 452–461 | 逐题：v4 下附独立 `row["product_hit"]`（不混入 `main`） |
| 5 | 578–586 | 聚合：v4 下附 `matched_product_hit_caliber` 块与 `criteria_v4` 批级块 |
| 6 | 740–793 | `_product_hit_row`：v4 逐题行（rank 用预先固定候选序；非命中 rank=None；命中事件不在候选序 ⇒ 机读 `matched_event_not_in_candidates`） |
| 7 | 795–875 | `_product_hit_caliber_block`：五桶 + 独立 hit@K + 桶和/单调性 fail-closed 断言 + 与 strict 分列声明 |
| 8 | 1096–1122 | `render_report`：新增 “matched_product_hit 口径” 独立小节（与 strict 分列，含命名纪律） |
| 9 | 1237–1253 | `render_plain_report`：大白话版并列说明 |

`main_caliber`（v2 strict）与 `old_caliber_*` 的计算代码**未改**；v4 的指标块
从键名到报表位置都与 strict 分列，无同名。

### 1.3 测试

| 文件 | 改动 |
|---|---|
| `tests/test_ppv1_criteria_v4.py`（新增，671 行，21 个测试） | 版本承载/§1 判定/§2 目标集合/§3 五桶/§4 豁免旁路与 v3 并存/判分透传；全部合成规则级夹具，零真实 qid |
| `tests/test_ppv1_criteria_v2_exemption.py`（287–290） | 白名单断言同步加入 v4（仅断言面；v2 判定断言不变） |
| `tests/test_ppv1_criteria_v3.py`（52、304） | 白名单断言同步加入 v4（仅断言面；v3 判定与指纹断言不变） |

---

## §2 三次重放结果

执行基座：`bin/replay_v4.py`（`/root/v43_migration/iter/v4_impl/bin/replay_v4.py`，
sha `3afc7d1f…`），复用 `iter/bin/replay.py` 的装载/离线读取口径，逐模式调用
`evaluate_scientific` 与 `s5b_scoring._main_caliber_row` / `_product_hit_row`。
数据视图 `iter/v4_impl/data_view/` 全部为只读 symlink（批根 + runs + 基线 metrics）。

### 2.1 a) v2 基线（必与批根 metrics 逐题一致）

| 指标（298 域 / `p2-298-20261026_v1card` / v2 / 分母 298） | 批根 `metrics.json` | 本次重放 | 一致 |
|---|---:|---:|---|
| hit@1 | 86 | **86** | Y |
| hit@3 | 112 | **112** | Y |
| hit@5 | 119 | **119** | Y |
| strict | 119 | **119** | Y |
| partial | 39 | **39** | Y |
| unmatched | 140 | **140** | Y |
| 逐题 status+rank | — | **298 / 298** | Y |
| `n_candidate_events` 不一致 | — | **0** | Y |

判定：**PASS**（修改没有碰坏 v2 既有路径）。

### 2.2 b) v4 主口径（`ppv1-criteria-v4`，分母 298）

| 指标 | 实测 | 冻结读数（预注册 §9） | 一致 |
|---|---:|---:|---|
| `matched_product_hit` | **156** | 156 | Y |
| hit@1 | **109** | 109 | Y |
| hit@3 | **148** | 148 | Y |
| hit@5 | **156** | 156（与命中数恒等，零区分度，不作对外指标） | Y |
| `product_hit_partial` | **2** | 2 | Y |
| unmatched 合计 | **140** | 140 | Y |

桶（§3 五桶，互斥，桶和 = 298）：

| 桶 | 题数 | 说明 |
|---|---:|---|
| `matched_product_hit` | **156** | 存在同一合法事件 S ∈ R_E 且 P ⊆ T_E |
| `product_hit_partial` | **2** | 旧 coverage 轴 partial 且 v4 未命中（两题均为 subset_only） |
| `unmatched_no_event` | **6** | 该批 6 题 payload 事件数为 0 |
| `unmatched_reference_invalid` | **0** | 本批 298/298 参考目标可评（全部 `strict_structure`、可解析、非空） |
| `unmatched_product_mismatch` | **134** | 有合法事件但主产物身份不全命中 |
| 合计 | **298** | 与分母闭合（assert 已过） |

`rank_attribution_errors = 0`（所有命中事件都在固定候选序中；无“命中却排不上名次”）。

**v4 下旧轴（参考边召回）读数**：114 strict / 81 hit@1 / 107 hit@3 / 114 hit@5 /
44 partial / 140 unmatched —— 与批根 `metrics.json.v1`（`114 / 81 / 107 / 114 / 44 / 140`）
**逐题 298/298 一致**。这不是退化：§4 规定 v4 **旁路 v2 豁免**，所以 v4 下的旧轴
等于 v1 豁免关口径（比 v2 的 119 少 5 题 = 原来靠 H₂O 豁免转正的 5 个事件）。
两把尺子分列，禁止跨版本比较 strict 数。

### 2.3 c) v3 披露轴并存（v4 + v3）

| 检查 | 结果 |
|---|---|
| v3 单跑（`ppv1-criteria-v3`）旧轴 | 119 / 86 / 112 / 119 / 39 / 140，逐题 298/298 与 v2 基线一致（v3 承载 v2 判分语义） |
| v3 单跑 `criteria_v3` 块 sha | `9f2b6e425fd84ca7a29488a13bdea28b3dd0e1b3e9e37e7346612d57813c3f25` |
| v4 + v3 并列的 `criteria_v3` 块 sha | 同上（**逐位相同**） |
| v4 单跑 `criteria_v4` 块 sha | `78edcb9254865ed4071061352f1bcd7bb0eec2d25607eaa00aa7d23afae136c9` |
| v4 + v3 并列的 `criteria_v4` 块 sha | 同上（**逐位相同**） |
| v4 单跑 vs v4+v3 的 v4 逐题聚合 | 完全相同（156 / 109 / 148 / 156 / 2 / 140） |
| 键隔离 | v4 单跑无 `criteria_v3`；v3 单跑无 `criteria_v4`；v1/v2/v3 均无 `criteria_v4` |

判定：**PASS**（v3 归一披露与 v4 主口径正交，互不改写）。

### 2.4 支撑模式（v1 锚）

| 模式 | 旧轴读数（298 域 / 分母 298） | 用途 |
|---|---|---|
| v1 | 114 / 81 / 107 / 114 / 44 / 140 | 证明 v4 下旧轴 = 豁免关口径；同时证明 v1 路径未变（对 `metrics.json.v1` 逐题 298/298） |

---

## §3 测试结果

命令（工作副本，`PYTHONDONTWRITEBYTECODE=1`，`-p no:cacheprovider`）：

```bash
python3 -m pytest \
  tests/test_ppv1_criteria_v2_exemption.py tests/test_ppv1_criteria_v3.py \
  tests/test_ppv1_criteria_v4.py tests/test_ppv1_s5a_evaluator.py \
  tests/test_ppv1_s5b_*.py tests/test_s5b_offline_funnel_controls.py \
  tests/test_retrieval_schema_version.py -q
```

| 项 | 结果 |
|---|---|
| 总计 | **561 passed, 4 failed**（198.38 s） |
| 新增 v4 测试 | **21 / 21 passed** |
| 失败 1 | `test_ppv1_criteria_v3.py::test_criteria_v3_arm_fingerprints_and_registered_defaults` |
| 失败 2–4 | `test_retrieval_schema_version.py` 的 3 项，原因 `ModuleNotFoundError: No module named 'langgraph.checkpoint.sqlite'`（环境缺依赖） |

**4 项失败全部是预存问题，不是本次改动引入**：在**生产树 `v43cP2`** 上单独复跑
同样 4 项，结果**同样 FAIL**（`4 failed in 2.43s`），证据
`docs/review_evidence/v4_impl_2026-10-28/pytest_pristine_prod_4fails.log`。
v3 指纹失败的原因是当前 notebook 的 RDKit/算子库指纹与 2026-10-19 冻结期望值不同
（v3 参数登记问题，与 v4 无关）；本次不改 v3 指纹（改它等于改 v3 判据）。

原始日志：
`pytest_criteria_scoring.log`（工作副本全量）、`pytest_pristine_prod_4fails.log`（生产树 4 项）。

---

## §4 与 `flips.json` 对账（37 题）

对照源：`docs/review_evidence/coverage_v3_sim_2026-10-27/flips.json`
（sha `fa67ed6d…`；notebook 侧 `iter/flips.json` 同哈希）。
**期望集合** = `flips.json` 的 `flip_rows[].qid`（37 题）；
**实测集合** = 基线（v2 `metrics.json` 逐题 `main`）为
`matched_participant_coverage_partial` **且** v4 桶为 `matched_product_hit` 的题。
逐 qid 比集合与 rank。

| 检查项 | 结果 |
|---|---|
| 期望题数 / 实测题数 | 37 / **37** |
| qid 集合相同 | **Y**（缺失 0、多余 0） |
| 逐 qid rank 相同 | **Y**（rank 不等 0） |
| 翻转题 rank 分布 | 1:20、2:13、3:2、4:2 |
| baseline strict → v4 非命中（变差） | **0** |
| rank 数值变大（位次退化） | **0** |
| rank 数值 → null | **0** |
| 仍 partial 的 2 题 | `RXNG_2a805c8fc232e6b0c279dbb3d18d113fe2ffedfef5528573a60f251c0a879196`、`RXNG_b34d5882f63b2bca8233d83fdf0b8f4029b9480607be024986565a22672cc33b`（与 flips.json `stay_partial_rows` 完全一致） |
| baseline unmatched 140 题仍留 unmatched 桶 | **140 / 140** |

hit@1 的算术对账：86（v2 基线） + 20（翻转题落在 rank 1） + 3（原 strict 题位次升到 1：
`RXNG_15293261…` 2→1、`RXNG_2d49e945…` 2→1、`RXNG_b978fd0b…` 4→1）= **109**。
hit@3：112 + 35（翻转题 rank ≤3）+ 1（4→1 的那题进入 ≤3）= **148**。

逐 qid 明细：`docs/review_evidence/v4_impl_2026-10-28/v4/metrics.json` 的
`flips_per_qid` 与 `docs/review_evidence/v4_impl_2026-10-28/v4/per_qid.json`。

---

## §5 未覆盖项与偏离预注册草案

### 5.1 【需要 CC 拍板】§3 partial 桶字面 trigger 与 §9 冻结读数 2/140 不一致

- **§3 字面规则**：`product_hit_partial = 无事件满足全部主产物，但存在合法事件命中部分主产物（多主产物题专用）`。
  按字面实现，本批有 **13** 题满足（2 题旧 partial + **11 题旧 unmatched**）：
  这 11 题都有 2 个主产物，某个事件命中其中 1 个、缺另 1 个（另一个主产物参考节点无严格命中）。
- **冻结读数（预注册 §9 / 本任务硬门）**：partial **2**、unmatched **140**。
  这个 2/140 是**旧 coverage 轴**的读数（v3 模拟把 superset 升 exact 后剩下的旧 partial 与
  旧 unmatched），不是 §3 桶重算的结果。
- **本次实现选择**：`product_hit_partial` 只在既有 coverage 轴已判
  `matched_participant_coverage_partial` 且 v4 未命中时成立（即与 2/140 一致）；
  旧 unmatched 题即使命中部分主产物也按 `unmatched_product_mismatch` 计。
  **零信息损失披露**：同一块里给出
  `product_hit_partial_v4_sense = 13`（§3 字面读数）与
  `product_hit_partial_outside_legacy_partial = 11`，逐题在
  `v4/per_qid.json` 的 `product_hit.product_hit_partial_outside_legacy_partial`。
- **11 题差异集（qid 级）**：
  ```text
  RXNG_11aa04deb97743c957fe3090fffedc48d9977720dbb6877a201513fa3d789395
  RXNG_1c56dceb435794abce028e458a1e9a0f35a1945e3d8983c27aa2bc3961f13124
  RXNG_31299a2c77ec97998ff6c2d057a92d5bf9e80d5ef08e71cdfb8fc473cf906fba
  RXNG_3d58685aebce44376b74102596b979baa8aeaac74e31da59b4b15a8c96277858
  RXNG_59a408497ff3441288b65b3636dc59e09933cf08c13e68ebb9357d7dbe3cd6a5
  RXNG_6a813df32c174715980075b3bdb0bbecbab719e83e07afc4ef38d9a7eeebe6d8
  RXNG_8e87765558aab9758c28a2969c3dca0b1ff8068d4a25b416534e9ada9a1d7b08
  RXNG_94539b62f7f3a9fed030818f5c33a9c96c7ca2dd9094831e29bbcbcd828a4c9d
  RXNG_a30cf37e0b92662a6891c7c358222e6beae4a629854537a2d7daa930ab1b0575
  RXNG_bd3bc48984cbae8677446ad46fcfc9d11aeadaa52fc743b20f62b8498147862a
  RXNG_eebc99542192a23453205caef7d0a5c1fabe01300b2dc48ca04e5728d84bba1f
  ```
  （全量机读：`v4/metrics.json` 的 `matched_product_hit_aggregate` 与
  `v4/per_qid.json` 的 `product_hit.product_hit_partial_outside_legacy_partial`。）
- **需要 CC 裁定**：是把 §3 的 partial 文字改成“仅当旧 coverage 轴为 partial”，
  还是把桶规则改成字面版（那样冻结读数要改成 156 / 13 / 129）。本次不调参凑数，
  两个读数都机器可读地留着。

### 5.2 v4 下旧轴 strict 从 119 降到 114（§4 豁免旁路的直接后果）

v4 不启用 v2 豁免（§4 明文），所以 v4 运行里旧轴等于 v1 豁免关口径：
119→**114** strict、86→**81** hit@1、39→**44** partial（5 题从 strict 退回 partial，
但它们的 v4 判定仍是命中）。这是预期行为，不是回退；报表把两把尺子分列，
并披露 `exemption_bypassed=true` 与 `exemption_counts` 全 0。
**任何引用 v4 的场合不得拿 114 与 v2 的 119 比较**。

### 5.3 `unmatched_reference_invalid` 本批为 0，仅有合成证据

本批 298/298 参考节点 `structure_identity_scope = strict_structure`、可解析、
产物侧目标非空，所以 reference-invalid 分支没有真实数据证据。该分支由
`tests/test_ppv1_criteria_v4.py` 的合成负控覆盖（scope 封顶 / 不可解析 /
目标集为空）。未来若出现 scope=cn_only 的参考图，需要新的真实数据回归。

### 5.4 其他未覆盖 / 边界

- **没有做化学正确性评审**：v4 只回答“同一事件里主产物身份是否命中”，
  不证明配平、系数、机制、酶学可行、参考声明完整（预注册 §7 的证明范围照抄）。
  零模型任务，mimo 化学抽审未跑。
- **守恒披露 D1 未接入**（预注册 §5）：属另一条任务线；本报告不给 “156 题中 X 题自洽”。
- **hit@5 与命中数恒等**（156 = 156），零区分度；对外只报 hit@1 / hit@3（§6）。
- **v4 桶的部分判定依赖旧 edge `match_status`**（§5.1 的选择）；旧 `match_status`
  本身未改，v4 不重算 coverage。
- **证据目录的唯一 SMILES** 是新增合成测试夹具常量（与仓库既有 `tests/` 同类，
  非 298 题面/金标）；所有重放产物（metrics / per_qid / replay_all）**零 SMILES**，
  身份只以 sha256_16 披露。
- 工作副本里有两处**非本次**的既存 worktree/index 差异
  （`chemstate.py`、`scripts/hpc/p2_arm_config.json`，来自先前 fatal-fix 部署），
  本次 patch 只含 §1 的 5 个文件；`strict_identity_of` 所在 `chemstate.py`
  生产树与副本逐字节相同。
- 未 commit / 未 push；未调用外部模型；未写批根 / runs（新文件数 0）。
- **生产树操作偏差（如实披露）**：为取得“4 项失败在生产树同样 FAIL”的对照证据，
  在 `/root/v43_migration/v43cP2` 上跑过只读 pytest（`PYTHONDONTWRITEBYTECODE=1`），
  pytest 自身缓存 `.pytest_cache/v/cache/nodeids`、`lastfailed` 被写（17:27 / 17:49）；
  事后删除 `.pytest_cache/v/`（该目录 2026-10-23 已存在，内容仅为可再生 pytest 缓存）。
  **源码零改动**（三文件哈希见上），批根 / runs 零写入；清理后
  `find … -newermt '2026-10-28 16:00' -type f = 0`。这是缓存级操作偏差，
  不是源码或结果修改；详见证据目录 `environment.txt`。

---

## §6 复现命令

```bash
# 0) 本机 → notebook(两跳)
bash scripts/hpc/nb_ssh.sh "<cmd>"

# 1) 工作副本(从生产树 cp -a;生产树只读)
cd /root/v43_migration/iter/worktrees
cp -a /root/v43_migration/v43cP2 v4_impl

# 2) 数据视图(只读 symlink;不复制批数据)
cd /root/v43_migration/iter/v4_impl
mkdir -p data_view/baseline
B=/root/v43_migration/ppv1_hpc/batch/p2_298_20261026_v1card
R=/root/v43_migration/ppv1_hpc/runs/p2_298_20261026_v1card
for f in batch_manifest.json split_manifest.json cases reference_graphs \
         preregistration_approval.json; do
  ln -sfn "$B/$f" "data_view/$f"
done
ln -sfn "$R" data_view/runs
ln -sfn "$B/metrics.json"    data_view/baseline/metrics.json
ln -sfn "$B/metrics.json.v1" data_view/baseline/metrics.json.v1

# 3) 应用 patch(在**干净副本**上验证/复现;已在 /tmp 干净子树上
#    `git apply --check` 通过)
cd /root/v43_migration/iter/worktrees
rm -rf v4_impl && cp -a /root/v43_migration/v43cP2 v4_impl
cd v4_impl
git apply -p1 /root/v43_migration/iter/v4_impl/out/v4_matched_product_hit.patch

# 4) 五次重放(v1 锚 / v2 基线 / v4 / v3 单跑 / v4+v3 并列)
cd /root/v43_migration/iter/v4_impl
PYTHONDONTWRITEBYTECODE=1 python3 bin/replay_v4.py \
  --data-root data_view \
  --code-root /root/v43_migration/iter/worktrees/v4_impl \
  --out-dir out \
  --flips /root/v43_migration/iter/flips.json \
  --mode all

# 5) 判分类测试
cd /root/v43_migration/iter/worktrees/v4_impl
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m pytest \
  tests/test_ppv1_criteria_v2_exemption.py tests/test_ppv1_criteria_v3.py \
  tests/test_ppv1_criteria_v4.py tests/test_ppv1_s5a_evaluator.py \
  tests/test_ppv1_s5b_*.py tests/test_s5b_offline_funnel_controls.py \
  tests/test_retrieval_schema_version.py -q -p no:cacheprovider

# 6) 证据哈希
cd docs/review_evidence/v4_impl_2026-10-28 && shasum -a 256 -c SHA256SUMS
```

关键哈希：

| 项 | sha256 |
|---|---|
| patch | `ea8e99ab5a15d4d9e3fc3d960153ba0d2c1f5ba60a0dbae5a5f375323fb43cb3` |
| `evaluation.py`（改动后） | `01276a42413f33eddb81798f27e3de1c3f598c5885e01d8c06bfaae3039a5c14` |
| `s5b_scoring.py`（改动后） | `4d517f6d8b0a4273eab62120bd95a1ed6c3d6fa577bdcbc4dc051a0e31728d28` |
| `replay_v4.py` | `3afc7d1fd9d07425b795b4528eec760012b09440128f3c2ea8532aff2059af19` |
| 生产树 `evaluation.py`（未改） | `37c092310d34d9f417234ccacd508942b3ce3edef640c73ab94022fd8dc75ad8` |