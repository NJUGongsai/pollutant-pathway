# qwen3.8max 代 Codex 复审（不替代正链 Codex 最终裁定权）

> **Provenance：** qwen3.8max 代 Codex 复审，按 CC 2026-10-21 指示（AGENTS.md
> 通道 C 同理：Codex 无额度时代审；放行/冻结类重要轮次正链额度恢复后可复核
> 确认）。复审日期 2026-10-26；只读执行；未改 src/tests/scripts/既有 docs/
> 封存批；未 push；未调模型；未读金标/题面/reference_graphs/env/key；未跑
> HPC 作业。
>
> **题域标签：[298 域] = RHEA 通用酶学 / 已见题（post-hoc）。** 本报告结论
> 不外推 dev 域。
>
> **复审对象：** P2 `state_fact_rederivation_mismatch` 一行 CN 根因修复 +
> 回归测试。请求书 `docs/REVIEW_REQUEST_P2_FATAL_FIX_2026-10-26.md`；修复
> 报告 `docs/T_P2_FATAL_FIX_2026-10-26.md`；诊断 `docs/T_P2_FATAL_
> DIAGNOSIS_2026-10-26.md`。
>
> **复审环境：** macOS arm64；Python 3.11.16 / RDKit 2026.03.6（conda
> `depending43`）；主仓 HEAD `5c61fdb`（复审基线取 `11aeeaf`）；隔离树
> `/tmp/qwen_p2rev_tree`（干净 clone @ `11aeeaf` + 四件前置补丁 + 主
> patch）；独立执行记录 `docs/review_evidence/qwen_p2_fatal_fix_review_
> 2026-10-26/`（含 NOTES.txt、独立全量/定向日志、复现探针输出、SHA256SUMS）。

## 1. 总裁定

**PASS**（修复与回归测试本身达到请求书验收面；无 P0/P1 缺陷）。

放行边界：本 PASS 只覆盖「一行 CN 根因修复 + 回归测试」的代码正确性与
本地证据闭合。**发车前置门不因此豁免**——部署树 run env 复跑、脚本锁/
批准包/build 身份重绑（24 条披露清单）、只读全库扫描、真实批副本零模型
重放（46 题回归集）仍须按修复报告 §5/§8/§9 与
`TASK_P2_REBUILD_AFTER_SRCFIX_2026-10-26.md` 执行，最终裁定权在正链
Codex 与 CC。

## 2. 逐项审核（对应任务 6 项）

### 2.1 patch 在干净树上 apply 通过、改动面最小 —— **通过（独立复现）**

- 隔离树 = `git clone` 主仓 @ `11aeeafded…`（detached），四件前置补丁
  SHA-256 实测与披露逐字一致（`cd8c03e0…`/`09414e26…`/`31d50045…`/
  `90f0d83b…`），按序 `git apply --check` + apply 全 PASS。
- 主 patch `chemstate_cn_fix.patch`（实测 SHA `b4e0fbf2…feb075`，与披露
  一致）：`git apply --check` PASS；`git apply --stat` 确认**只含 3 个
  文件**：`src/pathway_v43/pollutant/chemstate.py`（1 hunk，+5/-1 行：
  1 行功能 + 4 行注释）、`tests/test_p2_fatal_cn_fix.py`（新增 238 行）、
  `tests/test_p2_v1card_mode.py`（仅 `V2_PROMPT_SHA256` 常量
  `89311fdb…`→`c24bee42…` + 注释，断言仍为严格相等）。无其他改动。
- 应用后三文件 SHA-256 实测 = `495d3d0e…fdeb` / `daa07201…905d` /
  `4c18ab53…6cfc`，与修复报告 §4.1 逐字一致；修前 `chemstate.py` 实测
  `5bd05f68…3639`，与脚本锁 `files` 登记值一致。
- 隔离树 `src/`、`tests/`、`scripts/` 与交付工作树
  `/private/tmp/dependingv43_p2_fatalfix` `diff -r` **零差异**。
- v1card 常量归属：`docs/review_evidence/p2_integration_2026-10-21/
  ORIGINAL_PATCHES.md` 确已预记录该「集成轮对输入件的必要改动」，
  `c24bee42…` 与 chemfix N 轮 v2 prompt 登记值一致；v1card 28 项在隔离树
  通过即证明常量 == 当前实际 prompt 哈希。

### 2.2 根因真闭合、同源、身份不变 —— **通过（代码核 + 独立执行）**

- 修后工厂：`chemstate.py:707` `cn = _legacy_cn_identity(identity)`；
  `identity = _identity_key(mol)` 显式清映射号/atom props/conformer/
  DAT SGroup（`chemstate.py:207-226` 实读确认）。
- 同源闭合（实读代码确认）：`validate_state_object` 从 `smiles_isomeric`
  调 `build_chemical_state` 重推（`chemstate.py:844-845`），CN 比较在
  `chemstate.py:862`；公共 writer 同法（`store.py:624-625`，CN 比较
  `store.py:641`）；reader 侧复核 `store.py:1341`；`from_dict` 走同一
  validator（audit 首消费守卫 `audit.py:512-513` 亦调
  `validate_state_object`）。修后工厂 CN 与所有重推口**由构造同源**。
- 身份不变：`state_id=stable_id("cs", identity)`、`smiles_isomeric=identity`、
  `formal_charge`、stereo/isotope 状态均未触及（patch 仅 1 hunk）；
  独立复现探针 `fatal_repro.py --mode both` 输出与 `fatal_repro_both.out`
  **逐字节相同**：novel-1 `state_id=cs_a1ec01b3e472d011d8b8`、novel-2
  `cs_d9e540ee221a9df3899a`，修后 CN 映射号 0、工厂 CN == 重推 CN；
  legacy 口径仍复现 mismatch 且 `mismatches` 仅 `cn_identity`
  （novel-1/2 provided CN 各含 19/20 个映射号）。
- 表示层边界（请求 §6.2）：validator 历来从 identity 串重推 CN，故
  「CN 从 identity 算」按定义就是所有重推门期望的值；往返闭合有
  `smiles_isomeric_not_canonical` 守卫（`chemstate.py:877-880`）+ 新测试
  断言兜底。「map-free mol 直接算」反而引入第二种表示（MolToSmiles vs
  CXSmiles 往返），不如现修法同源。增强立体/同位素/电荷保留在 identity
  中，`domain.identity.cn_identity` 的 stereo-blind/charge-normalize 口径
  未改。
- 其他 CN 来源排查（请求 §6.1，全仓 grep 实读）：
  - `legacy_reader.py:205/264/283/428`：`_legacy_cn_of(raw)` 用于「记录
    声明 CN vs raw 重算 CN」的记录间一致性比较，两侧同为 raw 口径，
    自洽；构建 state 走修后工厂，不受影响；矛盾时披露
    `product_identity_vs_raw_mismatch` 而非硬失败——语义未变。
  - `audit.py:2763-2768`（executed product 对账）：`cn_a`/`cn_b` 两侧都
    从 raw 串同函数计算，同源自洽，本 patch 未触及。
  - `evaluation.py:1815-1819`：声明 CN 优先、缺失时从 `smiles_isomeric`
    重推——与修后口径同源。
  - `evaluation.py:2271-2278`：`ref_cn` 从参考图节点结构算；若节点串带
    映射号则 ref CN 带映射号，与 map-free state CN 的 CN 级匹配会失配
    ——但 strict 路径（map-free 身份）不受影响，且该语义**修前修后相同**
    （修前 mapped state CN 也匹配不上 map-free ref CN）；见 §5 P2-1。
  - CN-only 入口 `build_chemical_state_from_cn_only`（`chemstate.py:728-
    755`）：独立命名空间 `stable_id("cs","cn-only",cn)`，不经工厂 CN
    路径，未受影响。
  - `exam.py`/`exam_v2.py`：直接调 `domain.identity.cn_identity(raw)`，
    属其他任务族评分口径；本 patch 未改 `domain.identity`，无新分裂。

### 2.3 负控未放宽 —— **通过（代码核 + 独立执行）**

- patch 对 validator/store **零改动**（`git apply --stat` 仅 3 文件；
  `chemstate.py` 仅 L700-710 一个 hunk）；`raw_identity_mismatch` 拒绝
  路径实读仍在（`chemstate.py:905-910`），`raw_structure_rejected`/
  `state_structure_unparseable`/`smiles_isomeric_not_canonical` 均未动。
- 负控测试独立跑通：`test_raw_pointing_to_another_molecule_still_rejected
  [map-free-other/mapped-other]` 断言 `kind == "raw_identity_mismatch"`
  且 state_id 精确匹配；正控 `test_mapped_raw_of_same_molecule_still_
  accepted`（同图异拼写）通过。负控用的是 CN 同源化**之后**仍拒绝的
  事实，证明未为过测降级。

### 2.4 测试数字 —— **通过（关键项独立复现；基线/off-path/audit-wrap 为日志核）**

| 项 | 披露 | 本复审 | 口径 |
|---|---|---|---|
| 全量 `-m "not slow"`（修复树） | 2409 passed / 16 deselected | **2409 / 16（378.86s）** | 独立复现（隔离树） |
| 全量基线（未加新测试） | 2398 / 16 | 未重跑；2409−11=2398 算术闭合，两份日志 diff 仅进度行与总数行 | 日志核 |
| 定向（新 11 + v1card 28 + chemfix 18） | 57 passed | **57 passed** | 独立复现 |
| chemfix 19 探针 | 19/19 PASS | **19/19 PASS**（PASS 行与证据文件一致） | 独立复现 |
| 复现探针 both | legacy 双 REJECTED / fixed 双 PASS | 输出与证据**逐字节相同** | 独立复现 |
| v1 零漂移 off-path | 20/20；identity 差异仅 assets_root + 聚合 + chemstate 文件哈希 | `off_path_compare.json` n_ok=20/20、20 项 check 全 true、允许差异清单与实测一致；`off_path_after_fixed.json` A/B 两臂聚合均 `c565cd56…` | 日志核（未重跑探针） |
| audit-wrap 验证 | 122 passed；before EXPECTED_ESCAPE / after EXPECTED_ABORTED（fail-closed，零事件） | 日志核 | 日志核 |

- 环境陷阱（复审中发现，非 patch 缺陷）：本 conda env 有
  `__editable__.pathway_v43-0.1.0.pth` 指向主仓
  `/Volumes/CC/Enzyme_Agent/dependingv43/src`；不带 `PYTHONPATH=<tree>/src`
  跑全量会 import 到主仓源码（`5c61fdb` 状态），3 个 P2 测试文件收集期
  ImportError（本次表现为**响亮失败**，2345/2361 collected + 3 errors）。
  README 的复跑命令已写明 `PYTHONPATH=src`；见 §5 P2-2。

### 2.5 身份差异归因与 24 条披露清单 —— **通过（聚合独立复算；部署侧物件为日志核）**

- 用仓库自带 `run_identity.code_identity(PROFILE_POLLUTANT_PATHWAY_V1)`
  在隔离树独立复算：修后聚合 **`c565cd56…56a4`**、反打主 patch 后（修前）
  **`cfd74067…2f07`**、`src/pathway_v43` `.py` 计数 **87**——三值与披露
  逐字一致。聚合口径只覆盖 `src/pathway_v43/**/*.py`，主 patch 在 src 内
  只改 `chemstate.py` 一个文件 ⇒ 聚合差异**只来自 chemstate.py**；两处
  测试改动不在聚合内。归因闭合。
- 可选 patch 于第二份临时副本独立验证：`runflow.py` → `90ba75f7…59b4`、
  聚合 → `60cf8030…9921`，与披露逐字一致（副本用后已删）。
  `ChemicalStateError` 在 `runflow.py:119` 已导入，可选 patch 无 NameError
  风险；`_run_decide` 已有同类双捕获先例（`runflow.py:959`）。
- `git diff --stat 11aeeaf..5c61fdb -- src/pathway_v43` 为空 ⇒ 修复报告
  §5.2 备注「新 commit 落点不影响聚合（只要源码集相同）」成立。
- 披露清单 24 条计数核对：§5.1(3)+§5.2(3)+§5.3(6)+§5.4(5)+§5.5(5)+
  §5.6(2)=24 ✓。旧值抽查全部对上：脚本锁聚合 `cfd74067…`、锁文件自身
  SHA `8ba2cbec…920d` == 批准包 `script_lock_sha256` ==
  `preregistration_docs.script_lock.sha256`、`approval_sha256`
  `bd42c4d1…3fcb`、锁 `files` 101 件（90 src + 8 scripts/hpc + 3 docs）
  **不含 tests**、`source_commit 11aeeaf…`、chemstate 条目 `5bd05f68…`。
  `p2_arm_config.json` 的 `identity_expectations.code_identity_aggregate_
  sha256` 现值 `"TBD"`（集成补丁出厂态），#18 要求重绑 `c565cd56…` 正确。
  `p2_operations.json` 重生成已在 §5.5 备注覆盖。本地可见范围内**无遗漏
  身份门**；build_identity/batch_manifest/build_origin×298/run_identity 属
  部署侧物件，只能按 §5.5 在部署树重绑时实测核对（见 §6 unknown）。

### 2.6 可选 audit-wrap 启用时机 —— **意见：本轮不启用，留下一轮独立评审（与修复报告建议一致）**

- 机制核过（代码 + 日志）：捕获面只加一个具名异常类型，outcome 记
  `error`/`kind`/`reason`，attempt 落 failed、零事件/零提交，fail-closed
  保持；不是「吞成成功」，可审计。
- 不现在启用的理由：① 本 fatal 根因已闭合，不依赖它；② 启用即改
  `runflow.py` ⇒ 聚合变 `60cf8030…`，本轮重锁要绑两套身份，徒增重锁
  复杂度与出错面；③ 它改的是**失败严重度分类**（整题 fatal → 单
  proposal contract_aborted），值得独立一轮评审 + 独立重锁。
- 但建议 CC **尽早排期**：不启用则任何其他 `ChemicalStateError`（诊断
  §8 已点名）仍会整题 fatal，这是已知稳健性缺口，不应无限期挂账。

## 3. 与上一轮结论的关系

本轮无正链 Codex 在先报告冲突项：诊断（判定 B）与修复报告结论同本次
独立证据一致，未发现需逐条对抗的证据分歧。诊断侧批扫描数字（1,475 条
静态串 0 分歧；269 条 novel 规格 2 条分歧同一题；存量 646 state 0 条带
映射号）为日志采信，本复审未开任何 DB/封存件。

## 4. 对请求书 §6 十问的逐条回答

1. **一行是否真闭合**：是。工厂/`from_dict`/audit 首消费/store writer/
   reader 复核全部经 `build_chemical_state(smiles_isomeric)` 重推，修后
   CN 与身份键同源由构造保证。遗漏面排查见 §2.2（legacy_reader、
   audit 对账、evaluation、CN-only、exam 均无新分裂）。
2. **表示层边界**：现修法（从 identity 串算）优于「map-free mol 直接
   算」，因为 validator 历来消费的就是 identity 串口径；往返闭合有守卫
   + 测试。除映射号外无合法输入 CN 语义变化的机制路径；1,475 条静态串
   0 分歧为佐证（日志采信）。
3. **兼容性**：无映射号输入 CN 逐字不变（v1 正控测试 + 静态扫描）；
   存量落库 0 条带映射号 CN（批扫描，日志采信）⇒ 存量零变化。**发车前
   只读全库扫描仍应做**（修复报告 §9.1 已列，同意）。
4. **邻近风险**：假想的存量「带映射号 CN」state 不会被自动治愈，但会
   在首消费 fail-closed（响亮失败，非静默损坏）；扫描若发现再定迁移，
   现在不需要。与新批构建/评分无冲突（新批全部走修后工厂）。
5. **负控充分性**：充分证明未放宽同源校验（validator 零改动 + 双负控
   独立跑通）。「同图异电荷/同位素/立体」负控属既有 2398 项覆盖的
   validator 语义，本 patch 未触及，可作后续增强（P3），不阻断。
6. **novel-2 pending 口径**：单元级账本复现对回归测试目的足够（调度是
   纯账本动作，修复不写队列）；**真实批副本零模型重放仍须作为发车前
   验收**（修复报告 §9.10 已自我要求，同意，不可用单元测试替代）。
7. **可选加固**：合理、fail-closed、不掩盖（记 error+kind）；本轮不
   启用，独立轮处理（§2.6）。
8. **披露/重锁完整性**：24 条在本地可见范围内完整，旧值全部对上；
   部署侧物件（build_identity/batch_manifest/build_origin/run_identity/
   notebook 归一包）必须在部署树实测重绑，不能拿本地值直接抄（修复
   报告 §5.3 #7 已写明「HPC 部署树须以部署字节实测」，同意）。
9. **RDKit 版本**：本修复的正确性由「比较两侧同函数同源」构造保证，
   对 RDKit 版本不敏感（三版诊断一致为佐证）；但**重锁前在部署 run
   env（2026.03.5）重跑新增 11 测试 + 19 探针 + 复现探针必须是硬门**
   （修复报告 §8.2.3 已列，同意）。
10. **边界**：patch 未触及评分/池/排序/门阈值代码（stat 仅 3 文件）；
    P2 评分读 state CN 走 store 行（map-free，与 v1 历史一致）；
    `evaluation.py:2271` ref CN 语义修前后不变。未发现隐藏 scoring/
    asset key 依赖；唯一登记项见 §5 P2-1。

## 5. 发现清单

**P0（阻断）**：无。

**P1（应修或 CC 书面接受）**：无。

**P2（建议）**：

- **P2-1** `src/pathway_v43/pollutant/evaluation.py:2271`：参考图节点
  `ref_cn` 从节点原始结构串计算；若参考图节点结构带原子映射号，CN 级
  匹配（`:2278`）对 map-free state CN 恒失配（strict 级不受影响）。此
  语义修前修后相同，非本 patch 引入；但发车前只读 CN 对比（修复报告
  §9.2）建议把参考图节点结构纳入扫描面（本复审无权打开
  reference_graphs，无法核实批扫描是否已覆盖节点结构——见 §6）。
- **P2-2** 部署/复验脚本应显式断言解释器实际解析的 `pathway_v43.__file__`
  与目标树一致后再采信测试计数。本复审实测：conda env 的 editable
  `.pth` 指向主仓 src，不带 `PYTHONPATH` 的全量 pytest 会 import 错树
  （本次表现为 3 个收集错误，响亮失败；若两树符号兼容则会**静默跑错
  树**）。README 复跑命令已带 `PYTHONPATH=src`，但 notebook/HPC 复验
  步骤（修复报告 §8.1.5/§8.2.3）建议补一句模块路径断言。

**P3（后续）**：

- **P3-1** 下一轮可加「同图异电荷/同位素/立体」的 validator 负控
  （现有 2398 项已覆盖该语义，仅为显性化）。
- **P3-2** `legacy_reader._legacy_cn_of` 保持 raw 口径属有意设计（记录
  间比较两侧同源），建议在函数 docstring 补一句「勿改为 identity 口径，
  两侧同源性依赖 raw」，防后人顺手统一时破坏自洽。
- **P3-3** 可选 audit-wrap 尽快排独立轮（§2.6）。

## 6. 独立复现 / 日志核 / unknown

**独立复现（隔离树 `/tmp/qwen_p2rev_tree`，执行记录
`docs/review_evidence/qwen_p2_fatal_fix_review_2026-10-26/`）**：

- 四件前置补丁 + 主 patch 的 SHA、apply 链、`git apply --check`、
  3 文件改动面、应用后三文件 SHA、隔离树与交付工作树逐字节一致；
- 聚合身份修后 `c565cd56…` / 修前 `cfd74067…` / 87 件计数（仓库工具）；
  可选 patch 副本 → `90ba75f7…` / `60cf8030…`；
- 全量 `-m "not slow"` **2409 passed / 16 deselected**；定向 **57
  passed**；19 探针 **19/19**；复现探针 both 输出与证据逐字节相同；
- validator/store/runflow 关键行实读；脚本锁与批准包旧值实测比对；
  `11aeeaf..5c61fdb` 不触 `src/pathway_v43` 实测为空 diff。

**只核了日志（未重跑）**：基线 2398/16（算术闭合 + 日志 diff 核）；
off-path 20/20（compare json 的 20 项 check 与允许差异清单核）；
audit-wrap 122 passed 与 before/after 探针输出；批扫描全部计数
（1,475/269/2/646/0）；诊断侧 v1/v2 DB 对照与 HPC 交叉复现。

**unknown（保持 unknown）**：

- 部署树（notebook `/root/v43_migration/v43cP2`、HPC
  `~/EnzymeAgent/v43cP2`）实际字节与 run env RDKit 2026.03.5 下的测试
  结果——本地不可核，重锁前必须实测；
- 批扫描是否覆盖参考图节点结构串（本复审未打开 reference_graphs，
  红线）；
- 12 个 `budget_limit` 无响应 run 与 243 道未跑 v2card 题的映射号暴露
  面（不可静态枚举，修复报告 §9.5 口径正确：不把 0.84% 当上界）；
- 历史/其他批次全库是否存量带映射号 CN state（扫描未做，§9.1 已列）；
- build_identity/batch_manifest/build_origin×298/run_identity 的重绑
  结果（属部署时动作）。

## 7. 最小回修清单（仅请求范围内）

**无必须回修项。** P2-2（复验脚本加模块路径断言）建议并入部署任务书
文字，不需改本 patch；P2-1/P3 均不阻断本轮。

## 8. 对 6 个 CC 待决项的意见（只给意见，不代 CC 签字）

| # | 事项 | qwen3.8max 意见 |
|---|---|---|
| 1 | 修复口径（工厂 CN 从去映射号身份键算） | **支持**。同源由构造保证、负控完整、身份/评分口径零变化，是四个候选修法中爆炸半径最小且唯一让工厂==validator==store 的 |
| 2 | v1card 测试常量并入主 patch | **可接受并入**。ORIGINAL_PATCHES.md 已预记录、仅测试常量、断言未放宽、隔离树 28 项通过证明常量==实际 prompt 哈希；若 CC 要求「主 patch 只含源码」，拆独立集成补丁同样可行，代价是交付物多一件 |
| 3 | audit-wrap 启用 | **本轮不启用，独立轮尽早排**（§2.6）。启用则聚合必须绑 `60cf8030…` |
| 4 | commit / source_commit | 属 CC 授权动作。技术上：`11aeeaf..5c61fdb` 不触 src/pathway_v43，新 commit 落在含这两者的线上、源码集与 patch 树一致时聚合应为 `c565cd56…`；commit 后仍须以**部署树实测**为准 |
| 5 | 重锁 / 批准包重绑 | 按 24 条清单执行（本地旧值全部核实无误）；硬门：run env 解释器复跑（11 测试 + 19 探针 + 复现探针）通过后才重锁；预注册文本不动则 `preregistration_text_sha256` 保持原值 |
| 6 | 部署 + 代审 | 按修复报告 §8「先停 P2 → 备份 → dry-run → SHA 核 → run env 复验 → 重锁 → 重建 → fatal 再验收 → smoke → full」顺序；建议补 P2-2 的模块路径断言。**本代审报告不替代正链 Codex 最终裁定**；重要放行轮次正链额度恢复后应复核确认 |

---

*报告完。证据哈希见 `docs/review_evidence/qwen_p2_fatal_fix_review_2026-10-26/SHA256SUMS`。*
