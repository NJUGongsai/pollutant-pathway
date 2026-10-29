# 复审请求：P2 `state_fact_rederivation_mismatch` 修复（2026-10-26）

> **给 qwen3.8max 代 Codex 复审用。** 本请求自包含：背景、根因、逐行
> diff、测试证据、边界、待答问题都在本文内；不需要访问金标/题面/
> reference_graphs/env/key，也**不要**修改任何文件或执行付费调用。
>
> **题域标签：[298 域] = RHEA 通用酶学 / 已见题（post-hoc）。** 本文
> 所有结论不外推 dev 域；本文不含金标、题面、真实成绩或机制判断。
>
> **零金标声明**：本次修复与证据只使用 `docs/T_P2_FATAL_DIAGNOSIS_
> 2026-10-26.md` 的脱敏结构（v2 模型响应的 novel-1/novel-2 产物）与
> 合成底物 CCO；未打开 `reference_graphs`、题卷、封存 run、env/key。

## 0. 请先给结论

请按 §7 的格式回复：**PASS / PASS_WITH_CONDITIONS / FAIL**，并给
P0/P1/P2 问题清单（含 `文件:行`）、已核证据、残留风险、未审范围。
本请求只请求复审，不请求改代码、不请求签字、不请求发车。

## 1. 背景：v2card 单题 fatal

- 批：`p2_298_20261021_v2card`；qid `RXNG_ebe7683e…541650`；
  run `p2-298-20261021-s5br_79e656bbe6a`；失败 state
  `cs_a1ec01b3e472d011d8b8`。
- v2 模型响应的 `novel-1` 产物是**带 19 个原子映射号**的 SMILES；
  v1card 臂同一产物**无映射号**。两者 InChIKey 均为
  `NVKAWKQGWWIWPM-ABEVXSGRSA-N`，分子式 `C19H30O2`，charge 0，
  `state_id` 相同。
- 失败字段只有 `cn_identity`；`state_id`/`smiles_isomeric`/
  `formal_charge`/`stereo_information_status`/
  `isotope_information_status` 全一致。
- 根因（诊断判定 B）：`build_chemical_state` 用**带映射号的原始串**
  算 CN，而 `state_id`/`smiles_isomeric` 与
  `validate_state_object` 的重推导都用**去映射号身份键**；同一对象
  两个 CN 来源分裂，首消费抛
  `state_fact_rederivation_mismatch`。
- 影响面（批级只读扫描，已有证据）：298 题冻结池/底物 1,475 条串
  **0 分歧**；97 个已录制 run 的 269 条 novel 规格中 2 条分歧，全部
  落在同一道题（即 fatal 题）；12 个 `budget_limit` 无响应 run 与
  243 道从未跑的 v2card 题属**未知面**，不能静态枚举。

## 2. 修复对象与工作树

| 项 | 值 |
|---|---|
| 基线 | `11aeeafded1b41185f24de49767933709aad49db` |
| 工作树 | `/private/tmp/dependingv43_p2_fatalfix`（detached） |
| 前置补丁（按序 apply，均 PASS） | `impl.patch` `cd8c03e0…`；`patch2_v1card.patch` `09414e26…`；`patch3_ops_chain_incremental.patch` `31d50045…`；`chemfix.patch` `90f0d83b…` |
| 主修复 patch | `docs/review_evidence/p2_fatal_fix_2026-10-26/chemstate_cn_fix.patch`（SHA-256 `b4e0fbf2baeda1a5711ed8e9d4d2c02a7b7c97a417d0b31b5f4f28f187feb075`） |
| 可选加固 patch（默认不应用） | 同目录 `optional_audit_wrap.patch`（SHA-256 `55575989b897b9a13be9e8aa2165739da772f2ab179ad80df30f8bf4b8cf9e72`） |
| 本地 Python / RDKit | 3.11.16 / 2026.03.6 |
| 部署 run 的 RDKit（诊断记录） | 2026.03.5；HPC 登录节点交叉复现 2024.03.2（state_id/CN 结论一致） |

**主 patch 只含 3 个文件**：
1. `src/pathway_v43/pollutant/chemstate.py`（1 行功能修改 + 4 行注释）；
2. `tests/test_p2_fatal_cn_fix.py`（新增 11 个测试）；
3. `tests/test_p2_v1card_mode.py`（**仅测试常量** `V2_PROMPT_SHA256`
   从 `89311fdb…` 更新为 chemfix 后的 `c24bee42…`；这是
   `docs/review_evidence/p2_integration_2026-10-21/ORIGINAL_PATCHES.md`
   已记录的“集成轮对输入件的必要改动”，无运行时影响；若复审认为
   不应并入主 patch，可拆出，但四件集成树的全量测试会因该陈旧常量
   红 1 项）。

## 3. 逐行 diff（`chemstate.py`）

```diff
@@ -700,7 +700,11 @@ def build_chemical_state(
         base_fidelity[k] = v
     resolved_fidelity = _validate_fidelity(base_fidelity, origin)
     identity = _identity_key(mol)
-    cn = _legacy_cn_identity(structure) or ""
+    # CN 与身份键同源(去原子映射号):原子映射号不属于分子身份,若从
+    # 原始串算 CN,带映射号的输入会得到含 ":n" 的 canonical SMILES,
+    # 与 validate_state_object/store writer 从 smiles_isomeric 重推的
+    # CN 分裂(2026-10-26 诊断 B:state_fact_rederivation_mismatch)。
+    cn = _legacy_cn_identity(identity) or ""
     return ChemicalState(
         state_id=stable_id("cs", identity),
         structure_smiles_raw=structure,
         smiles_isomeric=identity,  # 规范化 CXSMILES(=身份键,往返闭合)
```

**为什么这是一行闭合**：
- `_identity_key(mol)` 在生成身份前显式清除原子映射号（`chemstate.py`
  L207-210），因此 `identity` 是 map-free；
- `state_id = stable_id("cs", identity)`、
  `smiles_isomeric = identity` 原本就是 map-free；
- `validate_state_object` 从 `smiles_isomeric` 调
  `build_chemical_state` 重推（L840），公共 writer `store.py` 同法
  （L624）；修后工厂 CN 与它们同源；
- 映射号以外的 `formal_charge`/stereo/isotope 不受影响；
- 未改 `domain.identity.cn_identity`，未改 validator，未改评分口径。

## 4. 测试证据（本地实测）

| 批次 | 结果 | 日志 |
|---|---|---|
| 复现探针（旧口径 CN 从 raw 算） | novel-1/novel-2 均 `state_fact_rederivation_mismatch`，`mismatches` 仅 `cn_identity`；provided CN 含 19/20 个映射号，rederived 0 个 | `fatal_repro_both.out` |
| 复现探针（修后） | novel-1/novel-2 均 PASS；CN 映射号 0；工厂 CN == 重推 CN；novel-1 `state_id=cs_a1ec01b3e472d011d8b8` | 同上 |
| 新增 `tests/test_p2_fatal_cn_fix.py` | **11 passed** | `pytest_targeted.log` |
| v1card 定向 | **28 passed** | 同上 |
| chemfix 测试文件 | **18 passed**（另有 19 条判定探针 **19/19 PASS**） | 同上 / `chemfix_19probe_after.out` |
| 定向合计 | **57 passed** | `pytest_targeted.log` |
| v1 零漂移 | **20/20**：v1 prompt/证据/底物卡/A、B 用户载荷字节全等；identity 仅 `assets_root`、聚合哈希、`chemstate.py` 文件哈希 | `off_path_compare.json` |
| 全量 `-m "not slow"`（集成树，未加新测试） | **2398 passed / 16 deselected** | `pytest_not_slow_baseline.log` |
| 全量 `-m "not slow"`（加新测试） | **2409 passed / 16 deselected** | `pytest_not_slow_final.log` |

新增 11 个测试覆盖任务要求的 5 项：
1. 带映射号产物 build + `validate_state_object` PASS，CN 不含 `:\d+`
   （novel-1/novel-2 各一条；`from_dict` 恢复同验）；
2. 工厂 CN == 从 `smiles_isomeric` 重推的 CN（逐字；novel-1/novel-2/
   v1 无映射号正控各一条）；
3. v2 novel-1/novel-2 回放：`prepare_hypothesis` → states 首消费守卫
   不再触发分歧；novel-1 认领后 novel-2 的 action 仍 `pending`
   （临时账本复现录制 run 的 `claimed`/`pending` 顺序）；
4. 负控：raw 指向另一个分子（map-free 与带映射号两种）仍抛
   `raw_identity_mismatch`；同图异拼写（不同映射号编号）仍接受；
5. v1 无映射号产物的 `state_id`/CN 与历史记录逐字相同。

**未改测试凑绿**：除上面记录的 v1card 常量（集成必要项）外，没有
修改/跳过/删除任何既有断言；没有放宽 `raw_identity_mismatch`、
`state_structure_unparseable` 或其他门。

### 4.1 映射号普查（CC 追加项，只读/零模型）

> 原始件：`docs/review_evidence/p2_fatal_fix_2026-10-26/census_source/
> map_number_census.json`（SHA-256 `74575a4f…314e`，notebook 只读扫描，
> 代码身份 `cfd74067…`，RDKit 2026.03.5，不打印结构）；已与
> `batch_cn_scan.json` 的 269/2/368/46/1,475 计数逐项交叉核对。

| 口径 | v1card | v2card | 合计 |
|---|---|---|---|
| 有响应 run | 47 | 50 | 97 |
| 有 novel 的题 | 41 | 41 | **46**（去重） |
| novel 规格 | 135 | 134 | **269** |
| 带映射号规格 | 0 | 2 | **2** |
| 无映射号规格 | 135 | 132 | **267** |
| 旧 CN ≠ 新 CN 规格 | 0 | 2 | **2** |
| **无映射号但旧 CN ≠ 新 CN** | **0** | **0** | **0** |
| 映射号原子合计 | 0 | 39 | 39 |
| 涉及 qid 数 | 0 | 1 | 1 |
| novel 侧 SMILES 出现数 | 185 | 183 | 368 |
| 不可解析 / regex-vs-RDKit 分歧 | 0 / 0 | 0 / 0 | 0 / 0 |

**“46/269”口径澄清**：46 是**有 novel 的题数**，269 是**novel 规格数**；
带映射号的规格只有 **2** 条（0.74%），无映射号 **267** 条。

2 条映射号规格（无结构正文）：

| 提案 | 映射号原子 | 去重号 / 最大号 | raw→CN 长度 | canonical→CN 长度 | 旧 CN≠新 CN | 清零映射号后 CN==canonical |
|---|---|---|---|---|---|---|
| novel-1 | 19 | 19 / 21 | 164 → 154（19 token） | 67 → 34（0 token） | 是 | **是**（sha16 `f6b6adde…`） |
| novel-2 | 20 | 20 / 21 | 164 → 152（20 token） | 64 → 33（0 token） | 是 | **是**（sha16 `3d6c403b…`） |

- **19 个映射号逐号**：`1,2,3,4,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21`；
  **缺 5、6**（被编辑的羰基 C/O）。19 个括号单元**全部是映射号原子**，
  不是冗余括号；canonical 的 7 个括号单元是 7 个立体原子、0 映射号。
- **state 未落库**：v2 失败 run 中该 `state_id` 的 `states`/`appearances`
  均为 **0** 行（写库前 fatal）；10-21 两臂 117 个 run DB 的
  646 states / 749 appearances / 333 个 state-valued 产物文件**全部 0
  条 mapped**；v1 同 `state_id` 行 map-free，`from_dict`/validate PASS
  ⇒ **无存量 CN 需要迁移**。
- **1,475 条静态串**（298 底物 + 1,177 池出现）**全部无映射号**，
  0 分歧只覆盖无映射号面；novel 269 条的普查是另一层，二者不能互相
  替代。
- **输出限制**：普查逐条核过 269 条，但 CSV/JSON 只给聚合 + 2 条
  映射号明细（不打印结构正文）；267 条无映射号由“0 条 CN 分歧”聚合
  覆盖，没有需要标红的 case。

## 5. 身份与影响

| 项 | 修前 | 修后 |
|---|---|---|
| `code_identity_aggregate_sha256`（P2 口径，87 个 `.py`） | `cfd74067…2f07`（与 2026-10-21 脚本锁/10-23 build 逐字相同） | **`c565cd56…56a4`** |
| `chemstate.py` SHA-256 | `5bd05f68…3639` | **`495d3d0e…fdeb`** |
| `state_id` / `smiles_isomeric` | — | **不变** |
| `formal_charge` / stereo / isotope | — | **不变** |
| v1 prompt / v2 prompt / schema / descriptor | — | **不变** |

若应用可选 `optional_audit_wrap.patch`：`runflow.py` 变为
`90ba75f7…59b4`，聚合变为 `60cf8030…9921`；默认**不应用**。

## 6. 请重点审的问题

1. **一行是否真闭合**：把 `cn` 的来源从 `structure` 改成 `identity`
   是否在所有入口（工厂、`from_dict`、audit 首消费、store writer、
   公共 resume）保持同源？有没有遗漏的 CN 来源（如 donor 诊断、
   CN-only、executed product、native export）？
2. **表示层边界**：`_identity_key` 会去映射号、清 atom props/
   conformer/DAT SGroup、保留增强立体/同位素/电荷；从 identity 算
   CN 是否可能改变某些合法输入的 CN 语义（除映射号外）？是否应
   改为“map-free 的 mol 直接算 CN”而不是经 CXSMILES 往返？
3. **兼容性**：CN 是旧评分/资产键。无映射号面：1,475 条静态串 +
   267 条 novel 规格均 0 差异；2 条映射号规格的 CN 变为 map-free 值，
   清零映射号后与 canonical CN 逐字相同。历史持久化 state、外部录入、
   其他批次是否可能因该修复改变 CN？是否必须在发车前做一次只读全库
   扫描？
4. **未修复的邻近风险**：10-21 两臂 117 run DB / 646 states / 749
   appearances / 333 个 state-valued 产物文件已扫，0 条 mapped；v2
   fatal state 未落库，v1 同 state_id 行 map-free 且 PASS。其他历史
   批次若有“带映射号 CN”state 不会被自动治愈，仍会在首消费
   fail-closed；这是否需要单独迁移/披露？是否会与新批构建/评分冲突？
5. **负控是否充分**：`raw_identity_mismatch` 负控是否足以证明没有
   为了过测放宽同源校验？是否还需要“同图不同电荷/同位素/立体”的
   负控？
6. **测试 3 的“novel-2 pending”口径**：临时账本复现
   `claimed`/`pending` 是否足以代表录制 run 的调度行为？是否应改为
   真实批副本的零模型重放（notebook/HPC）作为发车前验收？
7. **可选加固**：`_run_expand` 同时捕获 `ChemicalStateError` 是否
   合理？它保持 fail-closed（attempt failed、零事件/零提交），只把
   单 proposal 契约中止与整题 fatal 分开；是否应启用？是否会掩盖
   其他契约错误？
8. **披露/重锁是否完整**：新聚合 `c565cd56…`、脚本锁逐文件 SHA、
   批准包 `script_lock_sha256`/自哈希、`p2_arm_config`
   `identity_expectations`、build identity/fingerprint、source_commit
   更新是否已覆盖所有消费入口？有没有遗漏的身份门？
9. **RDKit 版本**：本地 2026.03.6、部署 run 2026.03.5、HPC 登录
   2024.03.2；诊断结论在三个版本一致。是否必须在部署解释器/run env
   重跑新增测试与 19 探针后才可重锁？
10. **边界**：本修复是否真的只影响映射号表示层、不影响化学判据/
    评分/池/排序/门阈值？有没有隐藏的 scoring 或 asset key 依赖？
11. **普查输出是否够**：269 条规格逐条核过，但 CSV/JSON 只给聚合 +
    2 条映射号明细，不打印 267 条无映射号结构（避免结构正文外发）。
    这是否满足 CC 的“逐条统计”验收？若要求 269 行结构 CSV，是否
    需要单独授权？

## 7. 回复格式（请逐条）

```markdown
## 结论
PASS | PASS_WITH_CONDITIONS | FAIL

## P0（必须修，阻断放行）
- [文件:行] 问题；证据；建议

## P1（应修，或需 CC 书面接受）
- ...

## P2（建议/后续）
- ...

## 已核证据
- 列出你实际核对过的文件/数字（不得声称未执行的测试）

## 残留风险 / 未审范围
- ...

## 对 §6 十一问的逐条回答
1. ...
...
```

**纪律**：只读复审；不得编造执行结果；不得修改任何文件；不得
调用模型/网络/付费批；不得打开金标/题面/reference_graphs/env/key；
不得给发车/签字结论（最终裁定权在 Codex 正链与 CC）。

## 8. 复审材料路径

| 材料 | 路径 |
|---|---|
| 主修复 patch | `docs/review_evidence/p2_fatal_fix_2026-10-26/chemstate_cn_fix.patch` |
| 可选加固 patch | `docs/review_evidence/p2_fatal_fix_2026-10-26/optional_audit_wrap.patch` |
| 修复报告 | `docs/T_P2_FATAL_FIX_2026-10-26.md` |
| 诊断报告 | `docs/T_P2_FATAL_DIAGNOSIS_2026-10-26.md` |
| 映射号普查汇总 | `docs/review_evidence/p2_fatal_fix_2026-10-26/novel_map_census_summary.json` / `.csv` |
| 映射号明细（2 条） | `docs/review_evidence/p2_fatal_fix_2026-10-26/mapped_novel_specs.csv` |
| 普查原始件 + provenance | `docs/review_evidence/p2_fatal_fix_2026-10-26/census_source/` |
| 证据目录 | `docs/review_evidence/p2_fatal_fix_2026-10-26/` |
| 集成必要改动说明 | `docs/review_evidence/p2_integration_2026-10-21/ORIGINAL_PATCHES.md` |
| 批级 CN 扫描 | `docs/review_evidence/p2_fatal_repro_2026-10-26/batch_scan/README.md` |
| 重建/再验收任务 | `docs/TASK_P2_REBUILD_AFTER_SRCFIX_2026-10-26.md` |