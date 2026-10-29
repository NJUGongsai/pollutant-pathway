# P2 四件补丁同树集成报告（2026-10-21，chemfix N 轮最终版）

> 题域标签：**[298 域]**（RHEA 通用酶学，已见题 post-hoc；离线实施集成）。
> 性质：工程集成与回归，不是科学性能读数；不连 HPC、不调模型、不读金标/题面。
> 基线：`11aeeafded1b41185f24de49767933709aad49db`（detach；集成树已重置到干净基线重放）。
> 集成工作树：`/private/tmp/dependingv43_p2_integration`。
> 证据目录：`docs/review_evidence/p2_integration_2026-10-21/`。

## 1. Apply 顺序与单次 apply 主路径

**唯一可行顺序（四件逐一 `git apply --check` 均 PASS，无冲突）：**

| 序 | 补丁 | SHA-256 | 件数 |
|---|---|---|---|
| 1 | `impl.patch`（v2 实现 r2） | `cd8c03e0a7ebc41e95ad7a1b9f323bda4a48caf3910373039c50f6ce6f9ebbd6` | 4 |
| 2 | `patch2_v1card.patch`（A 路） | `09414e26af89b3c12a7d3a37a60ddfeef1f3c006049badd427743c948338269e` | 2 |
| 3 | `patch3_ops_chain_incremental.patch`（B 路增量） | `31d50045bb8e30ec8f2570b962a685a93e474b939a8328229f213ea3369f4d24` | 10 |
| 4 | `chemfix.patch`（P1–P7 + N1/N2/N5，**N 轮最终版**） | `90f0d83b3a63d69ecb151362828c5d2b807cd9d0e3c305ff7d13db66d12e00bc` | 3 |

- **chemfix 最终件身份（N 轮）：** patch `90f0d83b…`；报告
  `docs/T_P2_V2_CHEMFIX_IMPL_2026-10-21.md` SHA-256
  `c9f5cf7da916168ae71899318abce5c720c1fe004eb2b2b9e9af1897c44ab979`；
  delta `RE_REVIEW_DELTA_2026-10-21.md` SHA-256
  `68bf3708dcfafb9465203c0b383e02814bb2152155a85a502226fa98e23e4cc9`；
  新测试 `tests/test_p2_v2_chemfix.py` SHA-256
  `c560977a29287c79a42eb01014c98db1ee35dda63ec6db711b1c04eff00dd73d`。
- **版本取代关系：** 本版取代 chemfix `eebca5f5…`（E1 前）与 `70ffc05b…`（E1–E3），
  以及上一轮组合补丁 `ba5b8d50…`。集成树已**重置到干净 `11aeeaf`**，按
  1→2→3→4（新）完整重放；无旧 chemfix 残留。
- 相对上一版（`70ffc05b…`）的差异：**仅** v2 prompt 证据段的 N1/N2/N5 措辞
  （恢复 `protonation-tolerant`、`n_hits ... may exceed`、补 `substrate_render_ok`
  空表语义）与 chemfix 测试的对应断言/新增 1 条 N1/N2/N5 测试；化学判据
  P1–P7 的代码/SMARTS 未变。
- 增量件 3 可用，**未启用**组合补丁 `patch_ops_chain_2026-10-21.patch`（`9169cd30…`，13 件）。
- **部署主路径（已验证）：** 干净 `11aeeaf` 单次 apply
  `docs/review_evidence/p2_integration_2026-10-21/p2_integration_combined.patch`
  （SHA-256 `608dec73f2060c78bbc891e134fb6ef16d6bebfa70e1de3e725f88c82c16a0a2`，16 件）。
  在独立 verify worktree `/private/tmp/dependingv43_p2_integration_verify` 上
  `git apply --check` + `git apply` 均通过，16/16 文件与集成树字节一致；
  verify 树定向 64 项（v1card 28 + chemfix 36）亦全绿。
- 备选：按 1→2→3→4 逐件 apply（结果相同）。**不要**在已 apply 1/2 的树上再叠组合补丁。

## 2. 逐文件 SHA 对账

完整机器可读表：`docs/review_evidence/p2_integration_2026-10-21/sha_reconciliation.json`。
集成树相对三棵来源树的共享文件为 16 件（5 源文件 + 8 脚本 + 3 测试）。

| 类别 | 文件 | 与来源树 |
|---|---|---|
| 化学修复 | `candidate_evidence.py`（`82b9b7cf…`）、`real_model.py`（`6351e9b8…`） | 与 `p2_chemfix` 逐字一致（N 轮） |
| A 路 | `runflow.py` | 与 `p2_v1card`、`p2_ops` 逐字一致 |
| 操作链 | `s5b_orchestrator.py`、`s5b_worker.py`、8 个 `scripts/hpc/p2_*` | 与 `p2_ops` 逐字一致 |
| 公共测试 | `tests/test_p2_evidence_card_v2.py` | 四棵树逐字一致 |
| A 路测试 | `tests/test_p2_v1card_mode.py` | 与来源树**有意不同**：`V2_PROMPT_SHA256` 常量由 `89311fdb…` 更新为 `c24bee42…` |
| 化学测试 | `tests/test_p2_v2_chemfix.py`（`c560977a…`） | 与 `p2_chemfix` 逐字一致（N 轮最终版） |

未解的“不一致”只有 `tests/test_p2_v1card_mode.py` 的常量更新一处（有意），
已在 `sha_reconciliation.json.documented_deltas` 记录；16 件共享文件中其余
15 件与来源树逐字一致。

## 3. 测试与探针

### 3.1 全量回归

| 项 | 结果 |
|---|---|
| 命令 | `pytest -q -m "not slow"`（`PYTHONPATH=<worktree>/src`，`-p no:cacheprovider`） |
| 结果 | **2398 passed, 16 deselected, 1 warning, 364.68s, EXIT=0**（N 轮 chemfix 重跑） |
| 数字账 | `2362`（`11aeeaf + impl r2 + v1card`）+ `36`（N 轮 chemfix）= `2398`；操作链不新增测试；deselect 仍 16 |
| 对照 | chemfix 单树报 2388（2352 + 36）、v1card 单树 2362；差值恰好等于新增测试数，无既有测试丢失 |

日志：`pytest_not_slow.log`。

### 3.2 定向测试

| 批次 | 结果 | 日志 |
|---|---|---|
| v1card 定向（A 路 28 项 = v2 18 + v1card 10） | **28 passed** | `pytest_v1card_targeted.log` |
| chemfix 定向 | **36 passed**（35 条化学/证据 + 1 条 N1/N2/N5 断言） | `pytest_chemfix_targeted.log` |

### 3.3 探针

| 探针 | 结果 | 文件 |
|---|---|---|
| chemfix 19 条 before/after 判定 | **19/19 PASS** | `chemfix_19probe_integration.out` |
| v1 零漂移（对 r2 实施前基线） | **20/20 checks pass** | `off_path_compare.json` |
| v1card 探针 | **7/7 checks true**；resume 同版本 `resumed=true`，换版本 `evidence_card_version_mismatch` 拒 | `v1card_probe_integration_result.json` |
| 两臂一致性 | 见 §5 | `two_arm_identity_check.json` |

零漂移细节：v1 prompt、v1 候选证据、v1 底物卡、A/B 用户载荷字节全等；identity
差异仅为 worktree 路径标签、聚合哈希与 5 个有意修改源文件的哈希。

## 4. Prompt SHA（新旧）

| 项 | SHA-256 |
|---|---|
| v1 prompt（不变） | `fe9eaf770deb19f8c6eec9aee14febe83f6b2d47f53e1c60002bb808eb3b0f4e` |
| v2 prompt（r2 旧） | `89311fdb5a85e6699f558d7b0ab64e7cc7972cad616d3c8972101f80a6b50f37` |
| v2 prompt（E 轮旧） | `e2aa2bbf61694c25f4607044f5f45a05c8e01c76dad8e26b1ecd71be7d953a5a` |
| **v2 prompt（N 轮/集成新）** | **`c24bee42f651c783c9bdcee6e8f547bff63f1f5fee6a4a87f4816e4d15e57598`** |

- 变更来源：chemfix P3/P4/P5 改写 v2 prompt 的 “Candidate evidence notes” 段，
  N 轮再补 N1/N2/N5（`protonation-tolerant`、`n_hits ... may exceed`、
  `substrate_render_ok` 空表语义）；v2 段长度 8836 字符。
- 硬编码旧 SHA 的处理：
  - `tests/test_p2_v1card_mode.py`：常量改为新 SHA，断言保留（严格相等）。
  - 证据探针副本 `v1card_probe_integration.py`：旧 SHA 比较改为新 SHA，断言保留。
  - `tests/test_p2_v2_chemfix.py` 仍保留 `OLD_V2_PROMPT_SHA256` 并断言 `NEW != OLD`（有意）。
- 未删除任何断言、未放宽为“任意非空/非旧值”。

## 5. 两臂 prompt / schema 一致性

| 臂 | prompt SHA | identity prompt | schema | descriptor | 载荷 |
|---|---|---|---|---|---|
| A = `v1card` | `c24bee42…` | `c24bee42…` | `candidate-evidence-2` | `candidate-evidence-descr-2` | v1 卡；与 v1 B 载荷逐字节同 |
| B = `v2` | `c24bee42…` | `c24bee42…` | `candidate-evidence-3` | `candidate-evidence-descr-3` | v2 卡；紧凑分隔符 |

`prompt_same_both_arms`、`schema_2_3_split`、`descriptor_2_3_split`、
`payload_schema_descriptor_2_3` 四项检查全为 true。结论：A/B 用同一个新 prompt
常量，schema/descriptor 仍 2/3 分工。

## 6. 操作链正负控（carry-over）

未在集成树重跑 `probe_ops_controls.py`：其 C7 需要读取 T-I 锁定件
`scripts/hpc/ti_operations.py`，该件刻意不在集成树。操作链 10 件产物与
`p2_ops` 树逐字一致，`p2_ops` 已记录 **77 checks / 0 failed**，故 C1–C7 结果
按字节同一性承接。说明见 `OPS_CONTROLS_CARRYOVER.md`。

## 7. 与预注册 / 发车书需要同步的字段

预注册：`docs/T_P2_PREREG_FULL_V2_2026-10-21.md`（SHA-256 `0841201d50…`）。
发车书：`docs/TASK_P2_FULL_V2_LAUNCH_2026-10-21.md`（SHA-256 `276afde205…`）。

| 文档·位置 | 现文 | 需同步为 |
|---|---|---|
| 预注册 头部 L23–25 | 仅列 `impl.patch` r2 | 增列 v1card / ops incremental / chemfix / 集成组合补丁的路径与 SHA |
| 预注册 §2.1 L110 | prompt “实测 SHA 登记” | 登记 `c24bee42f651…` |
| 预注册 §2.4 L144 | “v2 字段面、SMARTS 表、碳氧化态约定、prompt 文本按…r2 patch 执行，不改一字” | 改为“以 N 轮 chemfix 后文本为准”：2 个 SMARTS 家族 + v2 prompt 证据段（含 N1/N2/N5）+ C_ox unknown 守卫已变 |
| 预注册 §2.5 L173（第 6 条） | “v2 prompt 哈希不变” | “v2 prompt SHA 等于 `c24bee42…`（N 轮 chemfix 后集成常量）” |
| 预注册 §4.3 L289–294 | 同 prompt token 对比待测（基于 r2 prompt 的预测量） | prompt 文本已变，**需用新 prompt SHA 重测/登记 token** |
| 发车书 开头 L9（门 #4） | 化学复审 P1–P7 未闭合 | chemfix 本地 19/19 已闭合，但仍需化学复审确认后才能翻门（**拍板点**） |
| 发车书 §3.2 L171–175 | 补丁 1–4，状态“待实现/复审”，脚本锁待生成 | 更新 #2/#3/#4 为“本地实现+集成通过、待复审”；新增 chemfix 为 #5（附 SHA） |
| 发车书 §3.3 L198（第 6 条） | “v2 prompt 哈希不变” | 同预注册，改为新 SHA |
| 发车书 §3.5 L226 | “apply 补丁 1→2→3” | “单次 apply 组合补丁（16 件）”或“1→2→3→4”；用集成组合补丁 SHA 登记 |
| 发车书 §3.5 L227 | “全量 not-slow + v2 18 项 + 新 v1card 测试” | 全量 **2398 passed / 16 deselected**；v2 18 + v1card 10（定向 28）+ chemfix 36 |
| 发车书 §3.5 L230、附录 B L751 | `code_identity_aggregate_sha256` 占位 | 集成树实测 `cfd7406709b60344104c17513a0616b59380b971d5ede0d0909bc4f5c1322f07`；**部署树仍须复测** |
| 发车书 §3.5 L232、L175 | 脚本锁覆盖补丁 1–4 | 脚本锁改为覆盖 16 件（或 5 件源 + 8 脚本 + 3 测试）并登记部署树 SHA |
| 操作链证据 `environment.json.deploy_sequence_note` | “13 件组合补丁 / 备选 1→2→3” | 已过时；新主路径为 16 件组合补丁或 1→2→3→4（证据文件不自动改，交回处理） |

预注册“四文书 SHA”的定义若需把 chemfix 计入，也需 CC 在签字时明确（**拍板点**）。

## 8. 冲突、未解项与拍板点

1. **化学复审未做**：本任务只做集成与回归；chemfix 的 P1–P7 闭合是否被化学复审接受，
   需另走复审（mimo/Codex 通道）。发车门 #4 在复审前保持关闭。
2. **Token 重测未做**：v2 prompt 已变（`c24bee42…`），旧 token 预测量不能直接沿用；
   发车前需按新 prompt 重测或登记（离线可做）。
3. **chemfix 版本链**：`eebca5f5…`（E1 前）→ `70ffc05b…`（E1–E3）→
   **`90f0d83b…`（N 轮最终）**。本版从干净 `11aeeaf` 重放，无旧版残留；
   相对 E3 版仅 v2 prompt 的 N1/N2/N5 措辞与对应测试断言变化，
   化学判据代码/SMARTS 未变。
4. **v1card 单独重放会红**：`patch2_v1card.patch` 自带旧常量 `89311fdb…`；在
   N 轮 chemfix 之上单独重放该测试会失败。部署必须走组合补丁或 1→2→3→4，
   不能只回放 v1card。
5. **操作链控制未在集成树重跑**：原因见 §6；若复审要求同树实跑，需提供 T-I
   `ti_operations.py` 的只读副本或将 C7 拆出。
6. **聚合哈希**：`cfd74067…` 是 N 轮集成工作树实测；HPC 部署树须按发车书要求复测后回填。
7. **无脚本/配置冲突**：四件补丁之间无 hunk 冲突；`git apply --check` 四件全 PASS。

## 9. 硬约束遵守

- 只在集成工作树改代码；主树只新增本报告与证据目录。
- 未调模型/网络/费用，未连 HPC/sbatch，未读金标/题面/封存 run，未 push。
- 14 件 T-I 锁定文件未改：`11aeeaf` 中存在的 4 件与 HEAD 字节一致；其余 10 件未创建。
- 未改任务书/预注册；需要同步的行已列于 §7。

## 10. 证据清单

目录：`docs/review_evidence/p2_integration_2026-10-21/`

| 文件 | 内容 |
|---|---|
| `p2_integration_combined.patch` | 干净 `11aeeaf` 单次 apply 主路径（16 件） |
| `ORIGINAL_PATCHES.md` | 四件原始补丁索引、SHA、顺序、未用回退件 |
| `sha_reconciliation.json` | 逐文件 SHA 对账与有意差异（v1card 常量） |
| `environment.json` | 环境、命令、SHA、测试/探针摘要 |
| `pytest_not_slow.log` | 全量回归 2398 passed / EXIT=0 |
| `pytest_v1card_targeted.log` | v1card 定向 28 passed |
| `pytest_chemfix_targeted.log` | chemfix 定向 36 passed |
| `chemfix_19probe_integration.out` / `chemfix_19probe.py` | 19/19 |
| `off_path_integration.json` / `off_path_compare.json` / `off_path_probe.py` / `off_path_compare.py` | 零漂移 20/20 |
| `v1card_probe_integration_result.json` / `v1card_probe_integration.py` | v1card 7/7 + resume 正负控 |
| `two_arm_identity_check.json` | 两臂 prompt/schema/descriptor 一致性 |
| `OPS_CONTROLS_CARRYOVER.md` | 操作链控制承接说明 |
| `SHA256SUMS` | 本目录文件清单 |