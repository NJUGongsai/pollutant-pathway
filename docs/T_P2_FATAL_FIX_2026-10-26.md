# T-P2 v2card fatal 修复报告（2026-10-26）

> **题域：[298 域] = RHEA 通用酶学 / 已见题（post-hoc）。** 本报告只做
> 离线代码修复、测试与部署披露；**未调用模型/网络、未部署、未发车、
> 未跑付费批、未读金标/题面/reference_graphs/env/key、未碰 T-I 锁定
> 文件、未碰 notebook `/root/v43_migration` 与 HPC 批根/runs、未
> push**。结论不外推 dev 域。
>
> **Provenance：** 诊断 `docs/T_P2_FATAL_DIAGNOSIS_2026-10-26.md`
> （判定 B：代码/序列化 bug）；任务书 `docs/TASK_P2_REBUILD_AFTER_SRCFIX_
> 2026-10-26.md`；四件前置补丁按序 apply（`impl.patch` `cd8c03e0…`、
> `patch2_v1card.patch` `09414e26…`、`patch3_ops_chain_incremental.patch`
> `31d50045…`、`chemfix.patch` `90f0d83b…`）。映射号普查原始件来自
> 并行只读扫描 `docs/review_evidence/p2_fatal_repro_2026-10-26/batch_scan/
> map_number_census.json`（notebook，零模型/只读，代码身份
> `cfd74067…`，RDKit 2026.03.5，不打印结构）；本会话已与
> `batch_cn_scan.json` 逐项交叉核对（§3.3）。本报告与 patch 不替代
> qwen3.8max/Codex 复审、CC 拍板或发车签字。

## 0. 结论（先看这）

| 问题 | 回答 |
|---|---|
| 根因是否一行闭合 | **是**。`build_chemical_state` 的 CN 改从去映射号身份键算（`cn = _legacy_cn_identity(identity) or ""`）；`state_id`/`smiles_isomeric`/电荷/立体/同位素/评分口径均不变 |
| 改了哪些文件 | 源码 1 个：`src/pathway_v43/pollutant/chemstate.py`（1 行功能 + 4 行注释）；新增测试 1 个：`tests/test_p2_fatal_cn_fix.py`（11 测试）；集成兼容 1 个：`tests/test_p2_v1card_mode.py` 的 **测试常量**（见 §4.1） |
| 新 code identity aggregate | **`c565cd56854a4e55bca456012a4ed273285434fbaac8664baf79b7b4236c56a4`**（P2 口径，87 个 `.py`，修复树实测） |
| 修前 aggregate | `cfd7406709b60344104c17513a0616b59380b971d5ede0d0909bc4f5c1322f07`（与 2026-10-21 脚本锁、10-23 build **逐字相同**） |
| 测试数字 | 全量 `-m "not slow"`：修前集成树 **2398 passed / 16 deselected**；加新测试 **2409 passed / 16 deselected**；v1card **28**；chemfix 测试 **18** + 19 条判定探针 **19/19**；v1 零漂移 **20/20**；新增 **11** |
| 46/269 映射号普查 | **46 是题数，269 是 novel 规格数**；带映射号规格 **2**、无映射号 **267**；旧 CN ≠ 新 CN **2**（均为映射号规格）；**无映射号但改 CN = 0**（§3.3） |
| fatal state 是否落库 | **否**。v2 失败 run 的 `states`/`state_appearances` 均为 0 行，fatal 发生在写库前；**没有存量 CN 需要迁移**；v1 同 `state_id` 行存在且 map-free，恢复 PASS（§3.2） |
| 主 patch | `docs/review_evidence/p2_fatal_fix_2026-10-26/chemstate_cn_fix.patch`，SHA-256 **`b4e0fbf2baeda1a5711ed8e9d4d2c02a7b7c97a417d0b31b5f4f28f187feb075`** |
| 可选加固 patch | `optional_audit_wrap.patch`，SHA-256 **`55575989b897b9a13be9e8aa2165739da772f2ab179ad80df30f8bf4b8cf9e72`**，**默认不应用** |
| 是否需要 CC 拍板 | **是**（6 项，见 §7）：修复口径、v1card 测试常量是否并入、可选加固是否启用、commit/source_commit、重建/重锁/批准包重绑、部署与代审 |
| 披露清单条数 | **24 条**（§5） |

## 1. 根因对照（逐行）

失败对象：qid `RXNG_ebe7683e…541650`，run
`p2-298-20261021-s5br_79e656bbe6a`，state
`cs_a1ec01b3e472d011d8b8`。v2 模型把 novel-1 产物写成**带 19 个
原子映射号**的 SMILES；v1 同一产物无映射号。

| 行（修复前） | 代码 | 消费的事实 | 后果 |
|---|---|---|---|
| `chemstate.py:702` | `identity = _identity_key(mol)` | `_identity_key` 清除原子映射号/atom props/conformer/DAT SGroup（L207-226） | 身份键 map-free |
| `chemstate.py:703` | `cn = _legacy_cn_identity(structure) or ""` | **原始串**，RDKit `MolToSmiles` 默认保留 `:n` 映射号 | CN 带 19 个映射号 |
| `chemstate.py:705` | `state_id = stable_id("cs", identity)` | map-free 身份 | `cs_a1ec…` |
| `chemstate.py:707` | `smiles_isomeric = identity` | map-free 身份 | 与 v1 逐字相同 |
| `chemstate.py:840` | `derived = build_chemical_state(isomeric, …)` | validator 从 `smiles_isomeric` 重推导 | 重推 CN map-free |
| `chemstate.py:858` | `derived.cn_identity != state.cn_identity` | 比较两个 CN 来源 | 仅 `cn_identity` 分歧 |
| `chemstate.py:900` | `raw_identity != derived.smiles_isomeric` | raw→strict 身份核 | 本题 raw 与重推身份相同，**不是** raw 身份问题 |
| `store.py:624` | `derived = build_chemical_state(isomeric, …)` | 公共 writer 同法 | 若到写库也会拒 |

**一句话：** 同一对象内部两个 CN 来源——`state_id`/`smiles_isomeric`/
validator/store writer 走 map-free 身份键，工厂 CN 走带映射号原始串；
差在 19 个非身份的映射号注解，不在化学图。v1 没有映射号所以过；
v2 只是表示层多了映射号。

**为什么是整题 fatal：** `runflow._run_expand` 只窄捕获
`AuditContractError`（`runflow.py:1534`）；`ChemicalStateError` 继承
`RuntimeError`，从 audit 直接对象路径逃逸到 worker 顶层，整题记
`failed`。这是严重度问题，不是根因；可选 patch 处理（§6）。

## 2. 逐行 diff（主 patch 的源码部分）

```diff
diff --git a/src/pathway_v43/pollutant/chemstate.py b/src/pathway_v43/pollutant/chemstate.py
index 19b494a..17cd099 100644
--- a/src/pathway_v43/pollutant/chemstate.py
+++ b/src/pathway_v43/pollutant/chemstate.py
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

**为什么不是其他修法**（诊断 §7 已列，本单复核）：
- 只在 s5b/production 给模型产物去映射号：其他来源带映射号仍触发；
- validator 改从 raw 重推 CN：工厂与 store writer 仍不同源；
- 全局改 `domain.identity.cn_identity` 去映射号：爆炸半径大，影响所有
  legacy CN 调用；
- 本修法只改工厂的 CN 事实源，与 validator/store 同源，最小。

**未改**：`_identity_key`、`validate_state_object`、`store.py`、
`domain.identity`、schema/descriptor、评分/池/排序/门阈值。

## 3. 复现（before/after）

探针 `docs/review_evidence/p2_fatal_fix_2026-10-26/fatal_repro.py`
（只读、零模型；结构来自诊断的脱敏 v2 novel-1/novel-2）：

| 口径 | novel-1 | novel-2 |
|---|---|---|
| 旧 writer（CN 从 raw 算） | `state_fact_rederivation_mismatch`；`mismatches=[cn_identity]`；provided CN 含 **19** 个映射号，rederived **0** | 同款；provided CN 含 **20** 个映射号，rederived **0** |
| 修后 | **PASS**；CN 映射号 **0**；工厂 CN == 重推 CN；`state_id=cs_a1ec01b3e472d011d8b8` | **PASS**；CN 映射号 **0**；工厂 CN == 重推 CN；`state_id=cs_d9e540ee221a9df3899a` |

证据：`fatal_repro_both.out`。novel-1 的 `smiles_isomeric` sha16 =
`a1ec01b3e472d011`，与 `state_id` 后缀一致，确认身份键未变。

### 3.1 19 个映射号清单（fatal state）

fatal state 的 `provided` CN 含 **19 个原子映射号**，逐号为：

```
1, 2, 3, 4, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21
```

- **缺失 5、6 号**：这两个号是**被编辑的羰基 C/O**（产物酮
  `C(=O)` 处）；模型产物串没有给这两个被编辑原子重新编号。它们的
  缺失是**非身份元数据缺失**，不改变 InChIKey/state_id。
- **不是纯冗余括号**：raw 的 19 个括号单元**全部是映射号原子**
  （`bracket_units=19`、`mapped_atoms=19`、`regex_map_tokens=19`，
  三者相等）；canonical 形有 7 个括号单元，全部是 7 个立体原子、0 个
  映射号。因此该例的括号折叠不是“空括号/冗余括号”，而是**映射号
  注解被 `_identity_key` 当非身份元数据剥离**。
- CN 长度/映射号 token：raw CN 154 字符 / 19 个 `:n`；canonical CN 34
  字符 / 0 个。**把 raw 的映射号清零后重算 CN，长度 34、sha16
  `f6b6adde70afe710`，与 CN(canonical) 逐字节相同** ⇒ 分歧 100% 由
  映射号解释。
- 证据：`docs/review_evidence/p2_fatal_fix_2026-10-26/census_source/
  map_number_census.json` 的 `fatal_state.raw_stats` 与本会话用 RDKit
  对 `inputs.json` 的复算（19 个号、缺 5/6）一致；逐号明细也见
  `mapped_novel_specs.csv`。

### 3.2 state 未落库：没有存量 CN 需要迁移

| 事实 | 值 | 来源 |
|---|---|---|
| v2 失败 run `p2-298-20261021-s5br_79e656bbe6a` 中 `cs_a1ec…` 的 `states` 行 | **0** | 10-21 两臂 SQLite 只读扫描 |
| 同 run 的 `state_appearances` 行 | **0** | 同上 |
| 同 run 的 `states` 总行数 | 2（底物 + 模板产物） | 同上 |
| fatal 发生位置 | 写库前（audit 首消费） | 诊断 §1/§3 |
| 10-21 两臂 117 个 run DB：`states` / `state_appearances` | **646 / 749** | 普查 `stored_states_supplement` |
| 其中 `cn_identity` / `smiles_isomeric` / `structure_smiles_raw` 含映射号 | **0 / 0 / 0** | 同上 |
| 333 个 state-valued 产物文件中含映射号的 CN/iso/raw 值 | **0** | 同上 |
| v1card 同 `state_id` 行 | 存在；CN 34 字符 / sha16 `f6b6adde70afe710` / 0 映射号；iso+raw 67 字符 / sha16 `a1ec01b3e472d011` / 0 映射号 | 同上 + 诊断 §1 |
| v1card 该行恢复 | `ChemicalState.from_dict` / `validate_state_object` **PASS** | 诊断 §1 |

**结论：v2 的 fatal state 从未落库，写库前就失败；v1 同 `state_id`
的行是 map-free 的，恢复 PASS。因此本修复不需要迁移任何存量 CN**；
它只改变“带映射号 raw 在内存里构造的那一条 in-flight CN”。同一
`state_id` 在 v2card/v1card 的其他 qid 也以 map-free 形式落库（普查
`found_elsewhere`），同样不受影响。

### 3.3 46/269 novel 映射号普查（CC 追加项）

**口径澄清：46 是“有 novel 的题数”，269 是“novel 反应规格数”，
不是“46 条带映射号”。** 实测带映射号的规格只有 **2** 条（0.74%），
无映射号 **267** 条。

| 口径 | v1card | v2card | 合计 |
|---|---|---|---|
| 有响应的 run | 47 | 50 | **97** |
| 有 novel 的题 | 41 | 41 | **46**（去重） |
| novel 反应规格 | 135 | 134 | **269** |
| 带映射号规格 | 0 | 2 | **2** |
| 无映射号规格 | 135 | 132 | **267** |
| 旧 CN ≠ 新 CN 规格 | 0 | 2 | **2** |
| **无映射号但旧 CN ≠ 新 CN** | **0** | **0** | **0** |
| 映射号原子合计 | 0 | 39 | **39** |
| 涉及 qid 数 | 0 | 1 | **1** |
| novel 侧 SMILES 出现数 | 185 | 183 | **368** |
| 不可解析 SMILES | 0 | 0 | **0** |
| regex vs RDKit 映射号分歧 | 0 | 0 | **0** |

2 条带映射号规格的逐条明细（无结构正文，只有计数/哈希）：

| qid | 臂 | 提案 | 角色 | 映射号原子 | 去重号 / 最大号 | raw 长 → CN 长 | canonical 长 → CN 长 | 旧 CN≠新 CN | 清零映射号后 CN==canonical | prevalidation / 生产建 state |
|---|---|---|---|---|---|---|---|---|---|---|
| `RXNG_ebe7683e…541650` | v2card | novel-1 | product_smiles | **19** | 19 / 21 | 164 → 154（19 token） | 67 → 34（0 token） | 是 | **是**（sha16 `f6b6adde…`） | 是 / 是 |
| 同上 | v2card | novel-2 | product_smiles | **20** | 20 / 21 | 164 → 152（20 token） | 64 → 33（0 token） | 是 | **是**（sha16 `3d6c403b…`） | 是 / 是 |

- **无映射号但 B 会改 CN 的 case：0 条**。267 条无映射号规格全部
  旧 CN == 新 CN；没有需要逐条标红的 case。
- 发生率两个分母：**2/269 = 0.74%**（全部 novel 规格）；
  **2/238 = 0.84%**（实际生产建 state 的 novel 规格；238 = 128 v1card
  + 110 v2card）。
- 2 条带映射号规格的 `cn_maps_stripped_equals_canonical` 均为
  **true**：把 raw 的映射号清零后重算 CN，与 canonical CN 逐字节
  相同 ⇒ 带映射号的差异**只来自 `:n` 注解**（以及 canonical 排序，
  分子图不变）。
- 普查覆盖 269/269 规格：`unparseable_smiles=0`、`regex_vs_rdkit_
  disagreements=0`；368 个 novel 侧 SMILES 出现全部核过。
- 原始件：`census_source/map_number_census.json`（SHA-256
  `74575a4f…314e`）与 `census_source/map_census.py`（SHA-256
  `cf017f0a…26ef`）；provenance 见 `census_source/SOURCE.md`。本会话
  已与 `batch_cn_scan.json` 的 269/2/368/46/1,475 计数逐项交叉核对，
  全部一致。
- 汇总 CSV/JSON：`novel_map_census_summary.csv` /
  `novel_map_census_summary.json`；2 条明细：`mapped_novel_specs.csv`。

**与 1,475 条静态串的关系（CC 第 4 点）**：1,475 条 = 298 条底物 +
1,177 条池出现，**全部无映射号**（普查 `static_frozen_input_supplement`
`with_map=0`）。所以“1,475 条 0 分歧”只覆盖**无映射号面**，不能代表
novel 面；46/269 普查是另一层，二者不能互相替代。novel 面唯一的
2 条分歧就是上表的 2 条映射号规格。

**输出限制（诚实披露）**：普查逐条检查了 269 条规格，但输出**不打印
结构正文**（只给计数、长度、哈希、qid、提案名）；因此 CSV/JSON 给出
聚合计数 + 2 条映射号明细，而不是 269 行结构明细。267 条无映射号
规格由“0 条 CN 分歧”的聚合覆盖；若 CC 需要 269 行逐条结构 CSV，
属另一项“结构正文外发”授权（本次未做）。

## 4. 测试与证据

### 4.1 改动的文件与测试

| 文件 | 改动 | SHA-256（修后） |
|---|---|---|
| `src/pathway_v43/pollutant/chemstate.py` | 1 行功能 + 4 行注释 | `495d3d0e8ad5fb40d7d557a865a51a1e07d8e51f73e8775a6d72f9842861fdeb` |
| `tests/test_p2_fatal_cn_fix.py` | 新增 238 行 / 11 测试 | `daa07201f6ff8ac2e20f8295e52aebd838685e64e05329b1bcdb7e95805a905d` |
| `tests/test_p2_v1card_mode.py` | **仅测试常量** `V2_PROMPT_SHA256`：`89311fdb…` → `c24bee42…` | `4c18ab53c540982ef6ceb25bbf507f0b6d147d17c00e683a62137e3437e96cfc` |

**关于 v1card 常量的说明**：这是
`docs/review_evidence/p2_integration_2026-10-21/ORIGINAL_PATCHES.md`
已记录的“集成轮对输入件的必要改动”——chemfix 改了 v2 prompt，v1card
测试里写死的“当前 v2 prompt SHA”必须同步；断言仍是严格相等，未放宽。
若复审/CC 认为不应并入主 patch，可拆出为独立集成补丁，但四件集成树的
全量测试会因该陈旧常量红 1 项；本单为保持“四件集成树 + 修复”全绿而
并入，且**无运行时影响**。

### 4.2 测试数字

| 批次 | 命令/对象 | 结果 | 日志 |
|---|---|---|---|
| 全量（集成树，未加新测试） | `pytest -m "not slow" --ignore=tests/test_p2_fatal_cn_fix.py` | **2398 passed / 16 deselected**，393.37s | `pytest_not_slow_baseline.log` |
| 全量（集成树 + 新测试） | `pytest -m "not slow"` | **2409 passed / 16 deselected**（= 2398 + 11） | `pytest_not_slow_final.log` |
| v1card 定向 | `pytest tests/test_p2_v1card_mode.py` | **28 passed** | `pytest_targeted.log` |
| chemfix 测试 | `pytest tests/test_p2_v2_chemfix.py` | **18 passed** | 同上 |
| 新增测试 | `pytest tests/test_p2_fatal_cn_fix.py` | **11 passed** | 同上 |
| 定向合计 | 上述三文件 | **57 passed** | 同上 |
| chemfix 19 条判定探针 | `chemfix_19probe.py --src <修复树>/src` | **19/19 PASS** | `chemfix_19probe_after.out` |
| v1 零漂移 | `off_path_probe.py` + `off_path_compare.py` | **20/20**（v1 prompt/证据/底物卡/A、B 载荷字节全等；identity 仅 `assets_root`、聚合哈希、`chemstate.py` 哈希） | `off_path_after_fixed.json` / `off_path_compare.json` |

**新增 11 个测试与任务 5 项要求的对应**：

| 任务要求 | 测试 |
|---|---|
| 1. 带映射号产物 build + validate PASS；CN 不含 `:\d+` | `test_mapped_product_builds_and_passes_first_consumption[novel-1/novel-2]`（含 `from_dict` 同验） |
| 2. 工厂 CN == 从 `smiles_isomeric` 重推 CN | `test_factory_cn_equals_rederived_cn[novel-1/novel-2/v1-novel-1]` |
| 3. v2 novel-1/novel-2 回放；novel-2 pending 不变 | `test_v2_novel_replay_no_rederivation_mismatch`、`test_v2_novel2_action_stays_pending` |
| 4. 负控：raw 指向另一分子仍拒绝 | `test_raw_pointing_to_another_molecule_still_rejected[map-free-other/mapped-other]`、`test_mapped_raw_of_same_molecule_still_accepted` |
| 5. v1 无映射号正控 | `test_v1_identity_and_cn_unchanged` |

**未改测试凑绿**：除 §4.1 的 v1card 常量外，没有修改/跳过/删除既有
断言；`raw_identity_mismatch`、`state_structure_unparseable` 等门未
放宽。测试 4 的负控在 CN 检查通过后仍由 raw→strict 身份核拒绝，
证明本修复没有把同源校验降级。

### 4.3 环境与边界

| 项 | 值 |
|---|---|
| 本地 Python / RDKit | 3.11.16 / 2026.03.6 |
| 诊断记录 run RDKit | 2026.03.5 |
| HPC 登录节点交叉复现 RDKit | 2024.03.2（state_id/mismatch 一致） |
| 零模型/网络 | 全程无模型调用、无网络、无 env/key |
| 金标/题面 | 未读；只用诊断的脱敏产物串 + 合成底物 CCO |
| 封存/批根 | 未触碰；未写 `/root/v43_migration`、HPC `~/EnzymeAgent` |
| T-I 锁定文件 | 未触碰（14 件 T-I 文件均未改） |

## 5. 披露 / 重锁清单（24 条；本单**未改**预注册/批准包）

> 本单只在工作树改代码、在主树新增报告/证据；以下字段**需要 CC 在
> 部署/重建时重绑**，本单不代为修改。

### 5.1 源码/测试（3 条）

| # | 文件 | 旧 → 新 | 说明 |
|---|---|---|---|
| 1 | `src/pathway_v43/pollutant/chemstate.py` | `5bd05f68…3639` → **`495d3d0e…fdeb`** | 唯一功能修改；CN 从 identity 算 |
| 2 | `tests/test_p2_fatal_cn_fix.py` | 新增 → **`daa07201…905d`** | 11 个回归测试；不在脚本锁 `files`（锁只覆盖 src/scripts/docs） |
| 3 | `tests/test_p2_v1card_mode.py` | `89311fdb…` 常量 → **`c24bee42…`** | 集成必要项；仅测试常量，无运行时影响 |

### 5.2 代码身份（3 条）

| # | 字段 | 旧值 | 新值 |
|---|---|---|---|
| 4 | `code_identity_aggregate_sha256`（P2 口径，87 `.py`） | `cfd7406709b60344104c17513a0616b59380b971d5ede0d0909bc4f5c1322f07` | **`c565cd56854a4e55bca456012a4ed273285434fbaac8664baf79b7b4236c56a4`** |
| 5 | `identity.n_python_files` | 87 | 87（不变） |
| 6 | 若启用可选 patch：aggregate / `runflow.py` | `c565cd56…` / `a26801f7…` | **`60cf8030098c0d61cebe1adfca331c2127bfc83078298314e6b019815a609921`** / `90ba75f750c4f3a73c9553888fa95a34195798bba153a36c05d94deb732659b4` |

> 已核：主分支 `11aeeaf..5c61fdb` 的 60 个新增文件**不碰
> `src/pathway_v43`**，因此无论新 commit 落在主分支哪个提交，只要
> 源码集与本 patch 相同，聚合都应为 `c565cd56…`；若部署树另有源码
> 改动，以部署树实测为准。

### 5.3 脚本锁（6 条）

`docs/T_P2_SCRIPT_LOCK_2026-10-21.json`：

| # | 字段 | 需要做什么 |
|---|---|---|
| 7 | `files["src/pathway_v43/pollutant/chemstate.py"]` | 重测部署树 SHA → `495d3d0e…`（本地值；HPC 部署树须以部署字节实测） |
| 8 | `identity.code_identity_aggregate_sha256` | `cfd74067…` → `c565cd56…`（部署树实测） |
| 9 | `identity.measured_on` | 改为新部署树/新 commit/新日期（旧值写的是 HPC login03 + 10-21 build diag） |
| 10 | `source_commit` | `11aeeaf…` → CC 拍板后的新 commit SHA（本单不 commit） |
| 11 | `patches` | 新增 `chemstate_cn_fix.patch`（SHA `b4e0fbf2…`）；若启用可选件再加 `optional_audit_wrap.patch`（SHA `55575989…`）；若重生成 `p2_integration_combined.patch`，其 SHA 也必须更新（旧 `608dec73…` 作废） |
| 12 | `generated_at` / `missing` | 重新生成时间；`missing` 必须仍为空 |

> 脚本锁 `files` 只覆盖 `src/` 90 件（87 `.py` + vendor 3 件）+
> `scripts/hpc` 8 件 + 文档 3 件；**不含 tests**。新测试不需要进
> `files`，但要进 `patches` 或交付物清单（见 #11）。

### 5.4 批准包（5 条）

`docs/P2_APPROVAL_PACKAGE_2026-10-21/preregistration_approval.json`：

| # | 字段 | 旧值 | 需要做什么 |
|---|---|---|---|
| 13 | `script_lock_sha256` | `8ba2cbec554b8a72c0f52a1e88d9fed5e19eb8c947e8d5a28ff70da90769920d` | 重设为新脚本锁 SHA |
| 14 | `preregistration_docs.script_lock.sha256` | 同上 | 同上 |
| 15 | `approval_sha256` | `bd42c4d1770e583a60c98be8bbc3bcf50011871823eb907da2f69c68202d3fcb` | 按既有 canonical JSON 自哈希规则重算（排除自身与算法说明两键） |
| 16 | `SHA256SUMS` | 旧包 | 重新生成；若把本报告/复审请求/补充披露加入包，一并登记 |
| 17 | `preregistration_text_sha256` / `preregistration_docs.prereg.sha256` | `86242516…` | **仅在 CC 修改预注册文本时**更新；本单未改预注册，若只重绑脚本锁则保持原值 |

> **未改**：预注册 `docs/T_P2_PREREG_FULL_V2_2026-10-21.md`、发车书
> `docs/TASK_P2_FULL_V2_LAUNCH_2026-10-21.md`、化学终审
> `docs/T_P2_V2_CHEM_REVIEW_ROUND3_2026-10-21.md` 及其签字文本；本单
> 只列需要重绑的字段。

### 5.5 build/config（5 条）

| # | 文件/字段 | 需要做什么 |
|---|---|---|
| 18 | `scripts/hpc/p2_arm_config.json`（部署树/批根配置） | `identity_expectations.code_identity_aggregate_sha256` → `c565cd56…`；`source_commit` → 新 commit；`identity_expectations.rdkit_version` → 部署 run env 实测 |
| 19 | `build_identity.json` | `code_identity_aggregate_sha256` → `c565cd56…`；`source_commit`（如有）→ 新 commit；`build_identity_fingerprint` 重算 |
| 20 | `batch_manifest.json` | `build_identity_ref.build_identity_fingerprint` 重绑新指纹 |
| 21 | `build_origin/<qid>.json`（298 份） | `build_identity_fingerprint` 重绑新指纹；`run_input_sha256`/qid/run_id 不动 |
| 22 | `run_identity.json`（resume/审计身份） | `code_identity`/指纹/`source_commit` 重绑；旧 run 不得在新代码上 resume（身份门会拒，属设计行为） |

> `orchestration.json` 冻结的是 evidence card 版本/开关与 policy，
> **不含 code identity**；预期不变，但 prepare 记录
> `p2_operations.json` 会绑批准/脚本锁/ build 身份，必须在 prepare 后
> 重新生成并核对。旧 10-21/10-23 批根与 runs 只读保全，不得 resume。

### 5.6 其它（3 条）

| # | 项 | 需要做什么 |
|---|---|---|
| 23 | notebook 身份归一包（`de19dc6e…`） | 旧归一包只对旧 build 成立；新 code identity 必须重做 seed build + 身份归一 + 披露（按 `TASK_P2_REBUILD_AFTER_SRCFIX_2026-10-26.md`），旧包作废 |
| 24 | 旧批/旧 run | `p2-298-20261021-s5br_79e656bbe6a` 等**不得 resume**；新批根/新 runs 根/新协调目录，旧根只读 |

## 6. 可选加固（独立 patch，默认不应用）

`optional_audit_wrap.patch`：`runflow._run_expand` 的异常捕获从
`except AuditContractError` 改为
`except (AuditContractError, ChemicalStateError)`，outcome detail 记
`error`/`kind`。效果：单个 proposal 的 `ChemicalStateError` 不再逃逸
成整题 fatal，而是记 `contract_aborted`、attempt failed、零事件/零
提交（保持 fail-closed），由调度走独立备选。

- **不混入主 patch**；应用后 `runflow.py` 变为
  `90ba75f7…59b4`，aggregate 变为 `60cf8030…9921`，必须按 §5 重锁。
- 本单在独立副本上验证（`optional_audit_wrap_probe.py`）：
  - 未应用：`ChemicalStateError(state_fact_rederivation_mismatch)` 从
    `_run_expand` **逃逸**（`EXPECTED_ESCAPE`）；
  - 已应用：不再逃逸，`record_expansion_outcome` 记
    `kind=contract_aborted`、`detail={error:"ChemicalStateError",
    kind:"state_fact_rederivation_mismatch"}`（`EXPECTED_ABORTED`）；
  - 应用后 5 个 expand/audit 相关测试文件 + 新增测试共 **122 passed**
    （`optional_audit_wrap_validation.log`）；
  - **未**把可选 patch 应用到主修复树。
- 是否启用由 CC/复审决定；不用它也不影响本 fatal 的根因闭合。

## 7. 需要 CC 拍板（6 项）

| # | 事项 | 本单状态 | 建议 |
|---|---|---|---|
| 1 | 修复口径：工厂 CN 从 **去映射号身份键** 算（写侧 canonical CN） | 已按诊断首选实现 | 接受；与 validator/store 同源，最小爆炸半径 |
| 2 | v1card 测试常量更新是否并入主 patch | 已并入（集成必需，无运行时影响） | 接受并入；若要求“主 patch 只含源码”，拆成独立集成补丁 |
| 3 | 可选 `optional_audit_wrap.patch` 是否启用 | 未应用 | 建议下一轮独立评审后启用；本 fatal 不必等它 |
| 4 | commit / `source_commit` | **未 commit、未 push** | CC 授权后在修复线 commit，记录新 SHA；聚合应为 `c565cd56…` |
| 5 | 重建 / 重锁 / 批准包重绑 | **未改预注册/批准包** | 按 §5 与 `TASK_P2_REBUILD_AFTER_SRCFIX` 执行；任何身份异常停 |
| 6 | 部署 + 代审 | **未部署** | 先按 §8 停 P2、apply、重锁、qwen3.8max/Codex 复审，之后才发 |

## 8. 部署说明（notebook / HPC，先停再 apply）

### 8.1 notebook `/root/v43_migration/v43cP2`（无 `.git`，Python 3.11.9，RDKit 2026.03.5）

1. **先停 P2**：确认无并发 P2 作业（`ps`/协调目录锁/`stop.json`）；
   不删 `stop.json`、不删 case、不移证据；旧 10-23 批根与 runs 只读。
2. **备份**：把 `src/pathway_v43/pollutant/chemstate.py` 与
   `tests/test_p2_v1card_mode.py` 复制到 `/tmp`（或新目录）留回滚。
3. **apply**（无 git 树，用 `patch -p1`；先在临时副本 dry-run）：

   ```bash
   cd /root/v43_migration/v43cP2
   patch -p1 --dry-run < chemstate_cn_fix.patch   # 期望无 FAILED
   patch -p1 < chemstate_cn_fix.patch
   ```

   若平台有 `git apply`，也可在 git 工作树用
   `git apply --check` + `git apply`；本单已在干净 worktree 验证
   forward/reverse 均 PASS。
4. **核对**：`chemstate.py` = `495d3d0e…`，新测试 =
   `daa07201…`，v1card 测试 = `4c18ab53…`；用 notebook Python 重算
   `code_identity(PROFILE_POLLUTANT_PATHWAY_V1)` = **`c565cd56…`**。
   任一不符 ⇒ 停，不继续。
5. **本机复验**：在 notebook 跑新增 11 测试、v1card 28、chemfix 18、
   19 探针、off-path 20/20；再跑全量 `-m "not slow"`（期望
   2409/16）。RDKit 若与本地不同，至少必须重跑新增测试 + 19 探针 +
   复现探针，确认 CN/state_id 结论一致。
6. **重锁**：按 §5.3/§5.4 重建脚本锁与批准包绑定；qwen3.8max 代
   Codex 复审通过后才生效；**不得**在旧 build 上发车。
7. **重建**：按 `TASK_P2_REBUILD_AFTER_SRCFIX_2026-10-26.md` 新 seed
   （`p2_nb_seed_20261026`）+ 两臂 prepare + 身份归一 + fatal 再验收；
   298 run_inputs/reference_graphs 必须与旧 build 逐字节相同；之后才
   smoke2 → smoke10 → full。

### 8.2 HPC `~/EnzymeAgent/v43cP2`（tar 部署，非 git worktree）

1. **先停 P2**：确认无运行中批/并发写；保留批根、runs、`stop.json`、
   usage、日志；不删、不移、不 resume 旧批。
2. **apply**：在**新部署树**（或先备份旧树）用 `patch -p1` 应用主
   patch；不要就地改旧批根；`find . -name "._*" -delete` 后再核对。
3. **核对**：部署树逐文件 SHA（至少 `chemstate.py`）、新测试、
   聚合 `c565cd56…`；聚合用 **run env 的解释器/RDKit**（2026.03.5）
   实测，不拿登录节点 2024.03.2 的化学结论代替 run env 验证。
4. **重锁**：脚本锁 `files`/`identity`/`source_commit`/`patches` 按
   §5.3 重生成；批准包按 §5.4 重绑；qwen3.8max/Codex 复审后才生效。
5. **重建**：新 seed + build-gate + build-copy + 两臂 prepare；
   `identity_expectations`/build identity/fingerprint 按 §5.5 重绑；
   298 静态输入逐字节相同；fatal 再验收后再发车。
6. **不得**：在旧 build/旧 run 上发车或 resume；改判据/评分/门阈值；
   碰 T-I 锁定文件/批根。

## 9. unknown / 风险（诚实披露）

| # | 风险/unknown | 现状 | 处置建议 |
|---|---|---|---|
| 1 | **其他带映射号的持久化 state** | 10-21 两臂 **117 个 run DB（646 states / 749 appearances / 333 个 state-valued 产物文件）已只读扫描，0 条 mapped CN/iso/raw**；fatal state 未在失败 run 落库。静态 1,475 条全无映射号；novel 269 条中仅 2 条映射号、0 条无映射号 CN 变。**非 10-21 两臂的历史批次/其他 run 仍未扫** | 新批发车前如需覆盖历史批次，再做只读全库扫描（只出计数/state_id）；若发现旧带映射号 CN state，它们**不会被本修复自动治愈**，仍会在首消费 fail-closed |
| 2 | **CN 兼容性** | CN 是旧评分/资产键。无映射号面：1,475 条静态串 + 267 条 novel 规格均 **0 差异**；映射号面：2 条规格的新 CN 就是 validator/store 期望的 map-free 值，清零映射号后与 canonical CN 逐字相同；10-21 两臂存量 0 mapped | 部署树做“旧 CN vs 新 CN”只读对比；其他历史批次若有非映射号但 canonicalization 改 CN 的输入，需单独解释后再评分 |
| 3 | **RDKit 版本** | 本地 2026.03.6；run 2026.03.5；HPC 登录 2024.03.2（诊断三版 state_id/mismatch 一致） | 在部署 run env 重跑新增测试 + 19 探针 + 复现探针；若 CN/state_id 不同 ⇒ 停，不重锁 |
| 4 | **其他 `ChemicalStateError` 仍可能整题 fatal** | `_run_expand` 只捕 `AuditContractError`；`ChemicalStateError` 仍逃逸 | 可选 patch 处理；不启用则作为独立稳健性风险登记 |
| 5 | **未扫描的 12 个无响应 run / 243 道未跑题** | `budget_limit` 无响应，novel 内容不可见；243 道 v2card 题从未跑 | 修复后 full 新跑批会重新取响应，按 2/269=0.74%（全部规格）或 2/238=0.84%（生产建 state 规格）外推；不把它当上界 |
| 6 | **映射号缺失** | v2 novel-1 缺 5/6 号、novel-2 缺 18 号（被编辑的原子）；非身份元数据缺失，不改变 InChIKey | 本修复不处理；其他对齐/证明检查未评估 |
| 7 | **v1card 常量改动** | 仅测试常量，无运行时影响；但若复审认为不应并入主 patch，需拆出 | CC/复审裁定 |
| 8 | **预注册/批准包未动** | 本单只列重绑字段；`script_lock_sha256`/自哈希/`SHA256SUMS` 需 CC 授权后更新 | 未授权前不得发车 |
| 9 | **旧 run 不可 resume** | code identity 变化 ⇒ 身份门拒 | 设计行为；新批根/新 run，不绕过 |
| 10 | **本单未做真实零模型重放** | 无 notebook/HPC 批副本、无响应 blob；novel-1/novel-2 回放是单元级 `prepare_hypothesis` + audit 首消费守卫 + 临时账本 pending | 发车前按 `TASK_P2_REBUILD_AFTER_SRCFIX` 做 46 题/本 qid 的真实副本零模型重放 |

## 10. 交付物

| 文件 | 内容 |
|---|---|
| `docs/review_evidence/p2_fatal_fix_2026-10-26/chemstate_cn_fix.patch` | 主修复 patch（`b4e0fbf2…`） |
| 同目录 `optional_audit_wrap.patch` | 可选加固（`55575989…`，默认不应用） |
| 同目录 `fatal_repro.py` / `fatal_repro_both.out` | before/after 复现 |
| 同目录 `pytest_not_slow_baseline.log` | 2398 passed / 16 deselected |
| 同目录 `pytest_not_slow_final.log` | 2409 passed / 16 deselected |
| 同目录 `pytest_targeted.log` | 57 passed（v1card 28 + chemfix 18 + 新增 11） |
| 同目录 `chemfix_19probe_after.out` | 19/19 PASS |
| 同目录 `off_path_after_fixed.json` / `off_path_compare.py` / `.json` | v1 零漂移 20/20 |
| 同目录 `identity_aggregate.json` | 修前/修后/可选聚合 |
| 同目录 `novel_map_census_summary.json` / `.csv` | 46/269 普查汇总：2 mapped / 267 unmapped；0 unmapped CN change |
| 同目录 `mapped_novel_specs.csv` | 2 条映射号规格逐条明细（计数/哈希，无结构正文） |
| 同目录 `census_source/` | 普查原始 JSON/脚本 + `SOURCE.md`（provenance、交叉核对） |
| 同目录 `README.md` / `SHA256SUMS` | 目录说明与校验和 |
| `docs/REVIEW_REQUEST_P2_FATAL_FIX_2026-10-26.md` | 给 qwen3.8max 代 Codex 的自包含复审请求（零金标） |
| 本文件 | 修复报告、披露/重锁清单、部署说明、风险 |

> **本单未做**：commit/push、部署、发车、改预注册/批准包、调用模型、
> 读金标/题面/reference_graphs/env/key、碰 T-I 锁定文件/notebook
> `/root/v43_migration`/HPC 批根 runs。

## 11. Patch / 文件清单 / 测试命令（CC 追加项）

### 11.1 Patch

| 件 | 路径 | SHA-256 | 规模 | 状态 |
|---|---|---|---|---|
| 主修复 patch | `docs/review_evidence/p2_fatal_fix_2026-10-26/chemstate_cn_fix.patch` | `b4e0fbf2baeda1a5711ed8e9d4d2c02a7b7c97a417d0b31b5f4f28f187feb075` | 3 文件 / +248 / −3 | 已应用于本单工作树 |
| 可选加固 | `docs/review_evidence/p2_fatal_fix_2026-10-26/optional_audit_wrap.patch` | `55575989b897b9a13be9e8aa2165739da772f2ab179ad80df30f8bf4b8cf9e72` | 1 文件 / +9 / −3 | **默认不应用**；仅在独立副本验证 |

- 应用基线：`11aeeaf` + 四件 P2 补丁（按序 `impl` → `v1card` →
  `ops_chain` → `chemfix`）。
- `git apply --check` / `--check -R` 均 PASS；最小前置树 forward
  apply PASS。
- 主 patch 只改 **1 个源码文件**；其余 2 个是测试文件（1 个新增、
  1 个既有测试常量），无运行时影响。

### 11.2 改动文件清单

| 文件 | 改动 | 修前 SHA-256 | 修后 SHA-256 | 运行时 |
|---|---|---|---|---|
| `src/pathway_v43/pollutant/chemstate.py` | 1 行功能（CN 从 identity 算）+ 4 行注释 | `5bd05f68f1d2183c122361318475db875f5872d78de8cd40624533d6db433639` | `495d3d0e8ad5fb40d7d557a865a51a1e07d8e51f73e8775a6d72f9842861fdeb` | **是** |
| `tests/test_p2_fatal_cn_fix.py` | 新增 238 行 / 11 测试 | —（新文件） | `daa07201f6ff8ac2e20f8295e52aebd838685e64e05329b1bcdb7e95805a905d` | 否（测试） |
| `tests/test_p2_v1card_mode.py` | 仅常量 `V2_PROMPT_SHA256`：`89311fdb…` → `c24bee42…` | 旧常量值 `89311fdb5a85e6699f558d7b0ab64e7cc7972cad616d3c8972101f80a6b50f37`（非文件 SHA） | 文件 `4c18ab53c540982ef6ceb25bbf507f0b6d147d17c00e683a62137e3437e96cfc` | 否（测试） |
| `runflow.py`（仅可选 patch） | `except` 加 `ChemicalStateError` + detail | `a26801f722825bf2ef666cf4f89e955feff5c102beb2eafc9aa8e9f8d0ec529c` | `90ba75f750c4f3a73c9553888fa95a34195798bba153a36c05d94deb732659b4`（若启用） | 否（未应用） |

**未改**：预注册、批准包、评分/判据/池/排序/门阈值、schema/
descriptor、`_identity_key`、`validate_state_object`、`store.py`、
`domain.identity`、`scripts/hpc/*`、T-I 锁定文件。

### 11.3 可复制测试命令（本机实测）

工作树：`/private/tmp/dependingv43_p2_fatalfix`；Python：
`/Users/cc/miniconda3/envs/depending43/bin/python`。

```bash
cd /private/tmp/dependingv43_p2_fatalfix

# 1) 全量（含新测试）→ 2409 passed / 16 deselected
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src \
  /Users/cc/miniconda3/envs/depending43/bin/python -m pytest \
  -m "not slow" -q -p no:cacheprovider

# 2) 全量（不含新测试，集成树基线）→ 2398 passed / 16 deselected
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src \
  /Users/cc/miniconda3/envs/depending43/bin/python -m pytest \
  -m "not slow" -q -p no:cacheprovider \
  --ignore=tests/test_p2_fatal_cn_fix.py

# 3) 定向三文件 → 57 passed（v1card 28 + chemfix 18 + 新增 11）
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src \
  /Users/cc/miniconda3/envs/depending43/bin/python -m pytest \
  tests/test_p2_v1card_mode.py tests/test_p2_v2_chemfix.py \
  tests/test_p2_fatal_cn_fix.py -q -p no:cacheprovider

# 4) 新增测试单跑 → 11 passed
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src \
  /Users/cc/miniconda3/envs/depending43/bin/python -m pytest \
  tests/test_p2_fatal_cn_fix.py -q -p no:cacheprovider

# 5) chemfix 19 条判定探针 → 19/19 PASS
PYTHONDONTWRITEBYTECODE=1 \
  /Users/cc/miniconda3/envs/depending43/bin/python \
  /Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/\
p2_v2_chemfix_2026-10-21/chemfix_19probe.py \
  --src /private/tmp/dependingv43_p2_fatalfix/src \
  --label p2_fatal_fix

# 6) fatal 复现探针（before/after）→ exit 0，fixed PASS
PYTHONDONTWRITEBYTECODE=1 \
  /Users/cc/miniconda3/envs/depending43/bin/python \
  /Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/\
p2_fatal_fix_2026-10-26/fatal_repro.py \
  --src /private/tmp/dependingv43_p2_fatalfix/src --mode both

# 7) v1 零漂移（探针 + 20 项对比）→ 20/20
rm -rf /tmp/p2fatal_offpath_runs
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src \
  /Users/cc/miniconda3/envs/depending43/bin/python \
  /Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/\
p2_v1card_2026-10-21/off_path_probe.py \
  --src /private/tmp/dependingv43_p2_fatalfix/src \
  --out /tmp/p2fatal_offpath.json \
  --runs-root /tmp/p2fatal_offpath_runs
cp /tmp/p2fatal_offpath.json \
  /Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/\
p2_fatal_fix_2026-10-26/off_path_after_fixed.json
PYTHONDONTWRITEBYTECODE=1 \
  /Users/cc/miniconda3/envs/depending43/bin/python \
  /Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/\
p2_fatal_fix_2026-10-26/off_path_compare.py

# 8) 可选加固探针（默认不应用）
#    未应用 → EXPECTED_ESCAPE；应用后 → EXPECTED_ABORTED
PYTHONDONTWRITEBYTECODE=1 \
  /Users/cc/miniconda3/envs/depending43/bin/python \
  /Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/\
p2_fatal_fix_2026-10-26/optional_audit_wrap_probe.py \
  --src /private/tmp/dependingv43_p2_fatalfix/src
```

### 11.4 预期输出

> 注：命令 7) 会把新探针输出写回 `off_path_after_fixed.json`；若只想
> 复核而不改证据，先备份原文件，或把 `cp` 目标改到 `/tmp` 后人工对比。

| 命令 | 预期输出 |
|---|---|
| 全量（含新测试） | `2409 passed, 16 deselected, 1 warning` |
| 全量（不含新测试） | `2398 passed, 16 deselected, 1 warning` |
| 定向三文件 | `57 passed` |
| 新增测试 | `11 passed` |
| 19 探针 | `passed 19/19; failed: -`，A1–C6 全 PASS |
| fatal 复现 | exit 0；novel-1/novel-2 的 `fixed.result=PASS_EXPECTED`、`legacy.result=REJECTED_EXPECTED` |
| v1 零漂移 | `"n_checks": 20, "n_ok": 20, "all_ok": true` |
| 可选探针（未应用） | `"classification": "EXPECTED_ESCAPE"` |
| 可选探针（应用后） | `"classification": "EXPECTED_ABORTED"`；定向 122 passed |

### 11.5 映射号普查输出

| 文件 | 内容 |
|---|---|
| `novel_map_census_summary.json` | 97 run / 46 题 / 269 规格 / 2 mapped / 267 unmapped / 0 unmapped CN change；按臂计数；fatal state 19 号明细；static/stored 补充 |
| `novel_map_census_summary.csv` | 同上聚合表（novel/static/stored 三类 scope） |
| `mapped_novel_specs.csv` | 2 条映射号规格逐条：qid、臂、提案、角色、映射号数/最大号、长度、CN 长度、`cn_divergent`、`cn_maps_stripped_equals_canonical`、state_id |
| `census_source/map_number_census.json` | 普查原始 JSON（SHA-256 `74575a4f…314e`） |
| `census_source/map_census.py` | 普查脚本（SHA-256 `cf017f0a…26ef`） |
| `census_source/SOURCE.md` | provenance、与 `batch_cn_scan.json` 的逐项交叉核对 |