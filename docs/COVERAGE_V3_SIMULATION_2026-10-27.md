# coverage v3 模拟判分：P2 A 臂（2026-10-27）

> **题域标签：[298 域] = RHEA 通用酶学 / 已见题（post-hoc）。** 本文所有数字只在该题域、
> 该批次内成立，与 dev 域双向不外推。分母一律写明；金额 unknown（零付费）。
>
> 日期：2026-10-27。执行：notebook
> `crdnotebook-2113560935535583233-aclhl3hbth-81040`。
> 性质：**零模型调用、零网络、零付费；P2 批根/runs 只读；生产源码零改动；不 commit / 不 push。**
> 上游：`docs/CRITERIA_PARTICIPANT_COVERAGE_DEFECT_2026-10-27.md`（判据缺陷报告）、
> `docs/P2_MAINPRODUCT_HIT_AUDIT_2026-10-27.md`（39 道 partial 的 35/2/2 分类）。

---

## 0. 结论先行

| 问题 | 实测 |
|---|---|
| 基线（未改代码）复现 P2 A v2 | **strict 119、hit@1 86、hit@3 112、hit@5 119；partial 39、unmatched 140；逐题 298/298 一致** |
| 新口径 strict | **156 / 298（52.35%）** |
| 新口径 hit@1 | **109 / 298（36.58%）** |
| 新口径 hit@3 / hit@5 | **148 / 298（49.66%）/ 156 / 298（52.35%）** |
| 新口径 partial / unmatched | **2 / 140** |
| 翻转 | **37 题 partial→strict（35 道 superset + 2 道 mixed）；2 题仍 partial（subset）；0 题变差** |
| 与「156」预估 | **逐数一致（156）**；与早期 154 预估差 +2，见 §7 |

一句话：新口径把 P2 A 臂从 **119 strict / 86 hit@1** 抬到 **156 strict / 109 hit@1**；
37 题转正全部来自原 39 道 partial，140 道 unmatched 一动不动；没有 strict 回退、没有位次变差。
**这是判据口径模拟，不是模型能力提升。**

---

## 1. 红线与执行摘要

| 红线 | 执行结果 | 证据 |
|---|---|---|
| 零模型调用、零付费 | `provenance.json`：`llm_calls=0`、`network_calls=0` | 两份 provenance |
| 生产树 `v43cP2` 只读 | 源码哈希未变（`evaluation.py` 仍 `37c09231…`）；**但一次预检 import 刷新了 6 个 `.pyc` 的 mtime，见 §8.4** | `notebook_meta/environment.txt` |
| P2 批根 / runs 只读 | 批根与 runs 内 15:30 后新文件数 = **0**；仅通过 symlink 视图读取 | `notebook_meta/environment.txt` |
| 判分器改动只在副本 | 生产树 `evaluation.py` = `37c09231…`；副本 = `ab098be5…`；交付物是 patch | `coverage_v3.patch`、两个 `.sha256` |
| 不 commit / push | 副本 git 状态仅 `AM evaluation.py`，无 commit | `notebook_meta/minimal_change_check.txt` |
| 金标只写 qid 级/聚合数 | 报告、逐题 JSON、翻转表均无 SMILES/参考图正文 | 见 §9 |

执行路径：

- 代码副本：`/root/v43_migration/iter/worktrees/coverage_v3/`（从 `/root/v43_migration/v43cP2` `cp -a`）
- 运行工作区：`/root/v43_migration/iter/coverage_v3/`（data_view / out / logs / bin / notebook_meta）
- 重放基座：`/root/v43_migration/iter/bin/replay.py`（sha `3d2a3a5a…`，未改动）

---

## 2. 必须先说的数据路径偏差

任务书写的数据根是 `/root/v43_migration/iter/data/r2/`，但**这个目录不是 P2 A 臂的数据**：

| 数据根 | `batch_manifest.batch_tag` | 基线 v2 |
|---|---|---|
| `/root/v43_migration/iter/data/r2/` | `t-h-s5b-298-20261020r2` | **strict 126 / hit@1 89**（T-H r2） |
| `/root/v43_migration/ppv1_hpc/batch/p2_298_20261026_v1card/` + `runs/p2_298_20261026_v1card/` | `p2-298-20261026`（arm `v1card`） | **strict 119 / hit@1 86**（P2 A） |

任务书自己给的基线预期是 **119 / 86**，只有 P2 A 批根能复现；用 `iter/data/r2` 只会得到
126 / 89，会被误判为「基座跑偏」。本次因此改用 P2 A 批根 + runs，**只读**，在
`iter/coverage_v3/data_view/` 下用 symlink 暴露给重放器（未复制、未写批根）。基线逐题
298/298 一致，证明这个选择是对的。

**建议**：任务模板里的数据路径改成 P2 A 批根，或明确写「r2 是 T-H r2，不是 P2 A」。

---

## 3. 代码副本与新口径实现

### 3.1 副本与最小改动

| 项 | 值 |
|---|---|
| 副本根 | `/root/v43_migration/iter/worktrees/coverage_v3/` |
| 源树 | `/root/v43_migration/v43cP2/`（`cp -a`） |
| 改动文件 | 仅 `src/pathway_v43/pollutant/evaluation.py` |
| 改动前 sha256 | `37c092310d34d9f417234ccacd508942b3ce3edef640c73ab94022fd8dc75ad8` |
| 改动后 sha256 | `ab098be5d2bf08e278ac40d370bf315b98358f39b929e1c89df71c28bd030c24` |
| `s5b_scoring.py` | `4af3ed2d…`（未改） |
| `s5b_offline_rescore.py` | `b5e7ba0c…`（未改） |
| `diff -rq src` / `scripts` | 只有 `evaluation.py` 一处不同；`scripts` 全同 |

完整 patch：`docs/review_evidence/coverage_v3_sim_2026-10-27/coverage_v3.patch`
（应用后 diff：`coverage_v3_applied.diff`）。

**基线与新口径两次运行使用同一副本、同一 data_view、同一 `replay.py`；唯一差异是
`evaluation.py` 是否打了 patch。** 两份 `provenance.json` 的 `code_sha256` 只在
`evaluation.py` 上不同（`37c09231…` vs `ab098be5…`），其余 8 个文件逐字相同。

### 3.2 新口径的精确语义

改动在 `evaluation.py` 的 coverage 三分处（原 2438–2444 行附近）。新增逻辑：

```python
ref_participant_list_status = str(
    edge.get("participant_list_status") or "")
ref_declared_subset_ok = (
    ref_participant_list_status not in (
        "source_complete", "declared_complete")
    and from_states <= reactants
    and to_states <= products)
coverage = (
    "exact"
    if (reactants == from_states and products == to_states)
    or ref_declared_subset_ok
    else ("superset" if
          from_states <= reactants and to_states <= products
          else "partial_subset"))
```

| 参考边 `participant_list_status` | 事件形态 | 判定 |
|---|---|---|
| `partial` / `unknown`（非完整） | 声明 ⊆ 事件（superset，含恰好相等） | **exact → strict 候选** |
| `partial` / `unknown`（非完整） | 事件缺声明参与物（partial_subset） | 仍 `partial_subset`（不转正） |
| `source_complete` / `declared_complete` | superset | 保持原样：superset → 非 strict |
| `source_complete` / `declared_complete` | 恰好相等 | exact → strict（原样） |

**本批参考图实测：298 个图 / 298 条边，`participant_list_status` 全部 = `partial`**
（`partial: 298`，无 `source_complete` / `declared_complete` / `unknown`）。因此新分支对
本批每条边都生效。

### 3.3 合成规则级对照（实际函数，非纯逻辑推演）

用 `tests/test_ppv1_criteria_v2_exemption.py` 的合成夹具（零金标、零真实 qid）直接调用
副本里的 `match_reference_edges`，结果：

| 参考状态 | 事件形态 | `match_status` | 预期 | 结果 |
|---|---|---|---|---|
| `partial` | superset（多一个合成副产物，乙烷） | `matched_strict` | strict | PASS |
| `unknown` | superset | `matched_strict` | strict | PASS |
| `source_complete` | superset | `matched_participant_coverage_partial` | partial | PASS |
| `declared_complete` | superset | `matched_participant_coverage_partial` | partial | PASS |
| 上述四种 | exact | `matched_strict` | strict | PASS |

`all_pass = true`。证据：`new_caliber/v2/synthetic_status_control.json`。

### 3.4 一个必须披露的副作用：v2 豁免计数变成 0

新分支在 v2 豁免评审**之前**执行，因此本批所有 superset 事件都直接升 exact，
`evaluate_participant_exemption` 不再被调用：

| `criteria_v2` 块 | 基线 P2 A | 新口径 |
|---|---:|---:|
| `edges_with_exemption` | 5 | **0** |
| `events_exempted_strict` | 5 | **0** |
| `exempted_participant_occurrences` | 5 | **0** |
| `tier_counts.v1_exempt` | 10 | **0** |
| `tier_counts.not_exempt_maintains_partial` | 84 | **0** |
| `exempted_family_counts` | `{"v1:H2O": 5}` | `{}` |

strict 数不受影响（原本靠豁免转正的 5 个 H₂O 事件仍然 strict），但**豁免披露链在新口径下
实际上被旁路**。如果采用新口径，`criteria_v2` 块需要同步改语义或退役，否则批级披露会
显示「0 豁免」而历史读数曾显示 5，审计上会对不上。证据：`new_caliber/v2/evaluator_detail.json`。

---

## 4. 基线复现（未改代码）

命令（`replay.sh` 内部固定 `PYTHONDONTWRITEBYTECODE=1`）：

```bash
bash /root/v43_migration/iter/bin/replay.sh \
  --data-root /root/v43_migration/iter/coverage_v3/data_view \
  --code-root /root/v43_migration/iter/worktrees/coverage_v3 \
  --out-dir /root/v43_migration/iter/coverage_v3/out/baseline \
  --criteria v2 \
  --baseline .../data_view/baseline/metrics.json.v1 .../data_view/baseline/metrics.json
```

| 指标 | P2 A `metrics.json`（期望） | 本次重放 | 一致 |
|---|---:|---:|---|
| hit@1 | 86 | **86** | Y |
| hit@3 | 112 | **112** | Y |
| hit@5 | 119 | **119** | Y |
| strict | 119 | **119** | Y |
| partial | 39 | **39** | Y |
| unmatched | 140 | **140** | Y |
| 逐题 status+rank | — | **298 / 298** | Y |
| `n_candidate_events` 不一致 | — | **0** | Y |
| 参考图 sha | — | **298 / 298** | Y |

**基线判定：P2 A v2 完整复现，基座没有跑偏。**

关于重放脚本的 `pass=false`：`replay.py` 里硬编码的 `EXPECTED_ANCHORS` 是 **T-H r2**
（hit@1 89 / strict 126 / partial 53），不是 P2 A（86 / 119 / 39）。所以基线运行的
`aggregate_matches_expected_anchors=false` 是脚本常量导致的，不是数据或判分不一致；
真正该看的 `aggregate_matches_baseline_metrics=true`、逐题 298/298 都是 PASS。

---

## 5. 新口径结果

### 5.1 主表

| 指标 | 基线（v2） | 新口径 | 变化 | 新口径 95% Wilson |
|---|---:|---:|---:|---|
| hit@1 | 86（28.86%） | **109（36.58%）** | **+23** | 31.3–42.2% |
| hit@3 | 112（37.58%） | **148（49.66%）** | **+36** | 44.0–55.3% |
| hit@5 | 119（39.93%） | **156（52.35%）** | **+37** | 46.7–58.0% |
| strict | 119（39.93%） | **156（52.35%）** | **+37** | 46.7–58.0% |
| partial | 39（13.09%） | **2（0.67%）** | **−37** | 0.2–2.4% |
| unmatched | 140（46.98%） | **140（46.98%）** | **0** | 41.4–52.6% |

分母固定 298；零模型调用、零网络。

### 5.2 指标对账

| 指标 | 增量 | 拆解 |
|---|---:|---|
| hit@1 | +23 | 20 道翻转题落在 rank 1；另有 3 道原 strict 题位次升到 1（2→1 ×2、4→1 ×1） |
| hit@3 | +36 | 35 道翻转题落在 rank ≤3（20+13+2）；另有 1 道原 strict 题 4→1（原不在 hit@3） |
| hit@5 | +37 | 37 道翻转题全部 rank ≤4；3 道位次提升题的基线 rank 2/2/4 本来就在 hit@5，净增 0 |
| strict | +37 | 37 道 partial→strict |
| partial | −37 | 同一批 37 道 |
| unmatched | 0 | 140 道题没有任何变化 |

**hit@5 = strict = 156**：新口径下所有 strict 题的首个匹配事件都在 rank ≤5。

### 5.3 rank 分布

| rank | 基线 strict | 新口径 strict |
|---:|---:|---:|
| 1 | 86 | 109 |
| 2 | 19 | 30 |
| 3 | 7 | 9 |
| 4 | 4 | 5 |
| 5 | 3 | 3 |
| >5 | 0 | 0 |

### 5.4 桶转移（逐题，298 题）

| 基线 → 新口径 | 题数 |
|---|---:|
| strict → strict | 119 |
| partial → strict | **37** |
| partial → partial | 2 |
| unmatched → unmatched | 140 |
| **strict → 非 strict（变差）** | **0** |
| **unmatched → 非 unmatched** | **0** |
| **位次变差 / 位次消失** | **0 / 0** |

完整性门：`denominator_298=true`、`all_298_scored=true`、
`reference_graph_sha_all_ok=true`、`n_candidate_events_mismatch=0`。
`per_qid_match_status_all_equal=false` 与 `per_qid_rank_all_equal=false` 是**预期**
（37 题翻转 + 3 题位次提升），不是完整性失败。

---

## 6. 逐题翻转清单

全量机器可读：`docs/review_evidence/coverage_v3_sim_2026-10-27/flips.json`；
人读表：同目录 `flips.md`。

### 6.1 partial → strict（37 题）

分类取自 P2 A 主产物审计（`partial:superset_only:extra_only` 简写为 `superset`，
`partial:mixed:both_extra_and_missing` 简写为 `mixed`）。

| qid | 新 rank | P2 partial 分类 |
|---|---:|---|
| `RXNG_03ebc970515b44b852ed443ee83382e42fc7f9187577ff9d5a3b9d718af93014` | 1 | superset |
| `RXNG_08d3aa8a02eec3c1781990d03e1392cd369679bedd64a422046232d0cd2296cd` | 1 | superset |
| `RXNG_0eda0ec3a41b2c3acfd65b9fb04c98769602f4e7fcc9d41e156cfa5d020f1d7a` | 1 | superset |
| `RXNG_13141108d9e6fff229c829769312b0278c4b29eef400ff00fc4035bbb0d3181b` | 1 | superset |
| `RXNG_164844b4b76b8ac5477595bb93d376ba7bfb3ac5d31abc4f096c9ea3d196364b` | 1 | mixed |
| `RXNG_167dfdcc8dd009e80e713dc3b71286e691b0332aaea4d6fdb203ffc5cfe7b100` | 1 | superset |
| `RXNG_1692948d4ad5bd73360199106ccafb1453bb51acb6268b5033e58604c9578999` | 1 | superset |
| `RXNG_21ed83a680e54ef6741935a58d8f25e9fbde2714dd60c0793d731d875750bfc0` | 1 | superset |
| `RXNG_2579ae3ecc63b2677829ff39f5890a30436586ff24b2f8d3184dc0814d24262c` | 1 | superset |
| `RXNG_32293b693909ff88460f19bea98475ede7ae1cb8985ae0725062be223a21d388` | 1 | superset |
| `RXNG_45d8d90fa8ccd5c3b22a7a15aa6bb45c6e622e0091caa6ad462692b4d92d5182` | 1 | superset |
| `RXNG_5727b6273dcf6031a1c4f52e4ddf59706a95f5b94787f406a911104f8b277e61` | 1 | superset |
| `RXNG_66271eac90b08ad3268e5296699a435d0eb0864357cc7ddee59a434b721911bb` | 1 | superset |
| `RXNG_69c18546cc61c922cbc714c7f7b5667059ad47b577d8c5ac40c2a85f062271b8` | 1 | superset |
| `RXNG_7fab823b3a4e8b6a451483052f1c289151952774a86c8ce31939bff50aeb98bd` | 1 | superset |
| `RXNG_8d9fa8b67a68df3d23d1753ae15a463c9cf3376b2b4269a09949e7b75fbc86a3` | 1 | superset |
| `RXNG_a275c5200849ef8a1f8b8fae5945c33d92484a4cc96f7d670e84e3319a542939` | 1 | superset |
| `RXNG_a69f41ef39c4a709a585e1fa680a82e3904fc0f65ddba824f3882b1ace120aef` | 1 | superset |
| `RXNG_b6e5b278012c2fc36dd78beceffd2fecaccf65dbda15d15665b2ec0c966d0f3a` | 1 | superset |
| `RXNG_c9ee5eb0c5f911d80c6586a23575b4ce128c59608d4203618cfb40803f4a5aaa` | 1 | superset |
| `RXNG_0410354680d374fc880124f2e8742251ad9c12082d4e24ab4749284a6e1f6101` | 2 | superset |
| `RXNG_04d8e54db1cf2eee180ad272d26d804a4525d2abeb3d2d7d5faa713e713d710b` | 2 | superset |
| `RXNG_0ab7c126b56b87641946bcb273ee05744436dd09255df0aa183d6cff3a9d4048` | 2 | superset |
| `RXNG_0f02d5d2f47173ff20d001f5b9d3c2250b588913504dbe21b6a6c316eb2bec9a` | 2 | superset |
| `RXNG_2b9dd28e603c64b7e8e219e1f6feb7cc6b14e7210ffa7228428698edd89bb563` | 2 | superset |
| `RXNG_37e263634a3387350c0c20777dc629506d9212d1471ea97440a86c567f69a06c` | 2 | superset |
| `RXNG_445673c6693414a3aff38a620382912906a6a1edf06bc6a5a2fcc8f385523482` | 2 | superset |
| `RXNG_4f47ef5ad741ca620b4702f3c908f418524cbc821c091926a623c067748dd6f4` | 2 | superset |
| `RXNG_654cc41cad1160a9152a56bd41cc3ff515af2e909142aa463031c0896c87a6e8` | 2 | superset |
| `RXNG_96836273fb2c376cc96985d7ab5b3f35566778d7b9778ea812534ecbecc2a180` | 2 | mixed |
| `RXNG_c2fb10b79767bb786aa8d6e5df177fd580acbde9eb229e4fa70cfb34db5fe7ff` | 2 | superset |
| `RXNG_f2044d5f4d637b4101af41c10e44b40618eac6ab6fb0eae8688a059417fb5200` | 2 | superset |
| `RXNG_f30855a0ac0fa9188f6a03b5fea6cbb2bc9b84a9bc445a6a00efe39354aa7744` | 2 | superset |
| `RXNG_20b83d4f65520d2ec49187322a3daefed3465f394d3c2c4b2639fb5f64a86817` | 3 | superset |
| `RXNG_fc90885a446192fc4209fc6cd1006c8d7400ae365399f6262f05b736670b824e` | 3 | superset |
| `RXNG_15a597617bc29ae0a35d56b81b9347ea386bb349a6b10d249664b34a22081099` | 4 | superset |
| `RXNG_cee619845b65292d8c899a70944cd062541a65902f978454a1bb00e21cd05962` | 4 | superset |

### 6.2 仍为 partial（2 题，不变）

| qid | P2 partial 分类 | 原因 |
|---|---|---|
| `RXNG_2a805c8fc232e6b0c279dbb3d18d113fe2ffedfef5528573a60f251c0a879196` | subset_only | 事件缺参考声明的其它主产物；没有「声明 ⊆ 事件」的候选事件 |
| `RXNG_b34d5882f63b2bca8233d83fdf0b8f4029b9480607be024986565a22672cc33b` | subset_only | 同上 |

### 6.3 原 strict 题位次提升（3 题）

| qid | 基线 rank | 新 rank |
|---|---:|---:|
| `RXNG_1529326185deb8aaef6b237d68ae703df957b9036b039004e1bb76c177633ca7` | 2 | 1 |
| `RXNG_2d49e9455f2fbba4e4c580c010c7fb0eb86107775f1f0fc984a7a6e29c376f02` | 2 | 1 |
| `RXNG_b978fd0b540c4b52d0b90b504c8479c5fdb89291e40f9ab008f2639964bdd9b3` | 4 | 1 |

### 6.4 变差检测

- strict → 非 strict：**0**
- 非 null rank → null：**0**
- rank 数值变大：**0**
- unmatched 桶变化：**0**
- 没有报警项。

---

## 7. 与「156」预估的差异说明

**实测 strict = 156，与「156」预估逐数一致。**

与早期判据缺陷报告 §2.2 的 **154** 预估差 **+2**，原因清楚：

| 预估 | 算法 | 题数 |
|---|---|---:|
| 缺陷报告 154 | 119 + 35（只算 `superset_only`） | 154 |
| 本次实测 156 | 119 + 35（superset）+ 2（mixed） | **156** |

- P2 A 的 39 道 partial = **35 superset_only + 2 mixed + 2 subset_only**。
- 2 道 mixed 题在**题级**同时有 superset 事件和 partial_subset 事件；本任务的口径是
  **事件级**：只要存在一个候选事件满足「声明参与物 ⊆ 事件参与物」，该边就是 exact。
  mixed 题有这样一个 superset 事件，所以也转正。
- 2 道 subset_only 题没有任何「声明 ⊆ 事件」的候选事件，所以保持 partial。

**这里有一个需要 CC 知道的口径事实：**

- 本任务的字面规则是**事件级**：任一候选事件满足「声明 ⊆ 事件」⇒ exact。2 道 mixed
  题有这样一个事件，所以转正；这是 156 的来源。
- 如果 CC 想要的是**题级**规则（例如「该题所有候选事件都必须满足声明 ⊆ 事件，
  不允许任何 partial_subset 事件」），那是另一条规则，**不能直接写成 154**：
  本批另有 8 道 strict 题（6 道原 strict + 2 道 mixed 翻转）也含 partial_subset
  事件；题级规则会同时动到这 8 道，需要单独重跑。本文不替这条规则给数。

---

## 8. 风险、边界与待裁定

### 8.1 化学正确性没有评（零模型任务不评）

- 37 道翻转题里，多出来的参与物按 P2 审计包括：产物侧 43 个不同身份（40 个
  `coproduct`、3 个被模型标成 `principal_product`）、反应物侧 15 个 `cosubstrate`。
- 新口径只回答「多写算不算错」，**不回答「多写的分子化学上对不对」**。如果某些
  多余产物是错的，156 是**口径上限**；化学门控后的数字可能低于 156。
- 本次没有调用任何模型做化学评审；按仓规，采用前仍需 mimo/师姐化学评审 + 新预注册。

### 8.2 v2 豁免披露被旁路

见 §3.4。strict 不受影响，但 `criteria_v2` 的 5 条 H₂O 豁免计数归零。若采用新口径，
需要同步改 `criteria_v2` 块语义或退役该机制，否则历史读数与批级披露会对不上。

入口面：本模拟只改 `evaluation.py` 一个判分入口；`audit.py:636-666` 对 partial 参考声明
本来就判 `CHECK_UNKNOWN`，语义方向一致。生产采纳前仍需按仓规列全部适用入口
（build / parse / audit / 首提 / 重放）并走新预注册，不能把本模拟的单入口证据当成
全链等价证明。

### 8.3 完整声明分支只有合成证据

本批 298/298 条边都是 `partial`，没有真实 `source_complete` / `declared_complete` 边。
「完整声明保持原样」由合成规则级对照（§3.3）证明，不是真实数据证明。未来参考图若出现
完整声明，需要新的真实数据回归。

### 8.4 生产树 bytecode 缓存的一次写入（如实披露）

一次只读预检 import（核对 P2 预注册门）在
`/root/v43_migration/v43cP2/src/pathway_v43/pollutant/__pycache__/` 下刷新了 6 个 `.pyc`
的 mtime（`evaluation` / `s5b_scoring` / `native_export` / `native_result` / `endpoint` /
`audit`，15:35）。**没有改任何 `.py` 源码、批根、runs 或结果**；源码哈希仍为
`37c09231…`。后续所有重放与诊断均带 `PYTHONDONTWRITEBYTECODE=1`。这是一次操作偏差，
不是内容修改。

### 8.5 历史读数

新口径下历史读数（T-H r2 89、chain14 A 91、P2 A 86、P2 B 68 等）都需要按同一规则重算，
不能直接与新数字比较。本文只重算了 P2 A。

### 8.6 重放脚本的 `pass` 标志

`replay.py` 的 `pass` 同时要求「匹配 T-H r2 锚」与「匹配基线」。本次基线只过了后者，
新口径两者都不过（因为数字本来就要变）。完整性门（分母、全评分、图 sha、候选事件数）
都过。不要把 `pass=false` 读成「新口径运行失败」。

---

## 9. 证据与复现

### 9.1 本地证据

| 内容 | 路径 |
|---|---|
| 本报告 | `docs/COVERAGE_V3_SIMULATION_2026-10-27.md` |
| 证据根 | `docs/review_evidence/coverage_v3_sim_2026-10-27/` |
| 改动 patch | `.../coverage_v3.patch` |
| 应用后 diff | `.../coverage_v3_applied.diff` |
| 基线逐题 JSON | `.../baseline/v2/per_qid_diff.json`（298 行） |
| 新口径逐题 JSON | `.../new_caliber/v2/per_qid_diff.json`（298 行） |
| 新口径评估明细 | `.../new_caliber/v2/evaluator_detail.json`（298 行，只含状态/覆盖标签） |
| 翻转清单 | `.../flips.json`、`.../flips.md` |
| 合成对照 | `.../new_caliber/v2/synthetic_status_control.json` |
| 诊断脚本 | `.../scripts/dump_criteria_v2.py`、`.../scripts/synthetic_status_control.py` |
| 基线/新口径摘要 | `.../baseline/v2/summary.md`、`.../new_caliber/v2/summary.md` |
| provenance | `.../baseline/v2/provenance.json`、`.../new_caliber/v2/provenance.json` |
| 运行日志 | `.../logs/baseline.log`、`.../logs/new_caliber.log`、`.../logs/baseline_attempt1_missing_sha.log` |
| 环境与哈希 | `.../notebook_meta/environment.txt`、`.../notebook_meta/minimal_change_check.txt` |
| SHA256SUMS | `.../SHA256SUMS`（25 个文件，`shasum -c` 全 OK） |

### 9.2 关键哈希

| 对象 | SHA256 |
|---|---|
| 源树 `evaluation.py` | `37c092310d34d9f417234ccacd508942b3ce3edef640c73ab94022fd8dc75ad8` |
| 副本 `evaluation.py`（改后） | `ab098be5d2bf08e278ac40d370bf315b98358f39b929e1c89df71c28bd030c24` |
| `s5b_scoring.py` | `4af3ed2d60f97a3460df92027d2bb2b280b92c5956e81c475ee262cf33549ca3` |
| `replay.py`（基座） | `3d2a3a5a5b519abc6389a584f7f7cf88df5815a9df72dea46f1d5256a10dd454` |
| P2 A `metrics.json` | `0510febdd4ed50965be21ad3099342a4e4d1d59f66551bb4bbffb8aac9cfe912` |
| P2 A `batch_manifest.json` | `7e27e87b05aea94227c6282113679f0b0edc14eaff14abe33a22265c2d707ef3` |
| P2 A `preregistration_approval.json` | `c0b4c381de247488aed83351f344db31496193495d0d7e2ba31540d1056a0981` |
| `coverage_v3.patch` | `ad9ac1b7d788da3619710ab45d3bfbc91a6bfd09e5c8e703719fd45c865dd75b` |
| `coverage_v3_applied.diff` | `5adbca9860951411d737c988f52c67b69c3b552dd064a40e7b165f036dfe06f6` |

### 9.3 复现命令（notebook）

```bash
# 基线（未改代码）
bash /root/v43_migration/iter/bin/replay.sh \
  --data-root /root/v43_migration/iter/coverage_v3/data_view \
  --code-root /root/v43_migration/iter/worktrees/coverage_v3 \
  --out-dir /root/v43_migration/iter/coverage_v3/out/baseline \
  --criteria v2 \
  --baseline .../data_view/baseline/metrics.json.v1 .../data_view/baseline/metrics.json

# 新口径（先 patch 副本）
cd /root/v43_migration/iter/worktrees/coverage_v3
patch -p1 < /root/v43_migration/iter/coverage_v3/out/coverage_v3.patch
bash /root/v43_migration/iter/bin/replay.sh \
  --data-root /root/v43_migration/iter/coverage_v3/data_view \
  --code-root /root/v43_migration/iter/worktrees/coverage_v3 \
  --out-dir /root/v43_migration/iter/coverage_v3/out/new_caliber \
  --criteria v2 \
  --baseline .../data_view/baseline/metrics.json.v1 .../data_view/baseline/metrics.json
```

重放器固定 `PYTHONDONTWRITEBYTECODE=1`；两份 provenance 均记录
`llm_calls=0`、`network_calls=0`。参考图只在判分进程内消费，sha 校验 298/298。

---

## 10. 待 CC 拍板

| # | 事项 | 选项 |
|---|---|---|
| 1 | 新口径按事件级（本次 156）还是另立题级规则 | 事件级 = 39 道 partial 中 37 道转正；题级规则需另测，不能直接写 154（会动到 8 道已 strict 但含 partial_subset 事件的题） |
| 2 | 是否采用新口径 | 需化学评审（多写是否化学成立）+ 新预注册 + 历史读数重算 |
| 3 | v2 豁免机制怎么处理 | 新口径下计数归零；建议同步改披露或退役 |
| 4 | 任务模板数据路径 | `iter/data/r2` 是 T-H r2（126/89），不是 P2 A（119/86），建议改正 |
| 5 | 是否重算历史读数 | T-H r2 89、chain14 A 91、P2 B 68 等需同规则重算后才能并列 |

---

## 变更记录

- 2026-10-27：初版。基于 P2 A 批根只读重放（298 题），基线与新口径各一次；
  新口径 +37 strict / +23 hit@1；逐题翻转与证据落盘。