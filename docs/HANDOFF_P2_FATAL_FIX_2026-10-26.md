# HANDOFF — P2 fatal 修复 → notebook P2 窗口（2026-10-26）

> **题域：298 = RHEA 通用酶学 / 已见题（post-hoc）。** 本文件只交接 P2 fatal 修复的
> 应用、重锁、批准包重绑与复验步骤；不产生成绩、不调模型、不发车。
>
> 上游：`docs/T_P2_FATAL_DIAGNOSIS_2026-10-26.md`、`docs/T_P2_FATAL_FIX_2026-10-26.md`、
> `docs/QWEN_P2_FATAL_FIX_REVIEW_2026-10-26.md`、`docs/TASK_P2_NOTEBOOK_B_2026-10-26.md`。
>
> **状态：修复已实现、qwen3.8max 代审 PASS；等待 notebook P2 窗口应用 + 重锁 + 独立复验。**
> 本窗口未部署、未发车、未 commit、未改预注册/批准包。

## 0. CC 六项决策（2026-10-26 弹窗确认）

| # | 决策 | 结论 |
|---|---|---|
| 1 | 修复口径 | **写侧 canonical CN**：工厂 CN 从去映射号身份键算，与 validator/store/audit 同源 |
| 2 | v1card 测试常量 | **并入主 patch**（`V2_PROMPT_SHA256` `89311fdb…` → `c24bee42…`） |
| 3 | 可选 audit-wrap | **本轮不启用**；保留 patch，后续独立轮 |
| 4 | commit / source_commit | **不 commit**；用 patch SHA + tree identity；`source_commit` 保持 `11aeeaf…` |
| 5 | 重锁/批准包 | **应用 + 重算 + 重绑**（不是先跑再锁） |
| 6 | 部署/代审顺序 | **qwen PASS 后部署 + 独立复验**；Codex 正链后置复核 |

## 1. 最终件与 SHA

| 件 | 路径 | SHA-256 |
|---|---|---|
| 主修复 patch | `docs/review_evidence/p2_fatal_fix_2026-10-26/chemstate_cn_fix.patch` | `b4e0fbf2baeda1a5711ed8e9d4d2c02a7b7c97a417d0b31b5f4f28f187feb075` |
| 可选 audit-wrap | 同目录 `optional_audit_wrap.patch` | `55575989b897b9a13be9e8aa2165739da772f2ab179ad80df30f8bf4b8cf9e72`（**不应用**） |
| 修复报告（含 46/269 普查 + 命令清单） | `docs/T_P2_FATAL_FIX_2026-10-26.md` | `a00ed7f79e6770adadbd5e42a86ea95dc73b45afdc4bd02ddb84f2fe413e6a6a` |
| 复审请求（追加普查后） | `docs/REVIEW_REQUEST_P2_FATAL_FIX_2026-10-26.md` | `9e4542292507f702320ca06f75b9e317af5ffe83fffcf7c6aaffee30b2aea212` |
| qwen 代审（针对代码/patch；报告后续只加证据节） | `docs/QWEN_P2_FATAL_FIX_REVIEW_2026-10-26.md` | `9a83319d8db03cfcfc63b1bfc57713f055f554f8c0bc962b58904f20488e6e40` |
| 证据清单（25 项，含 census_source/） | `docs/review_evidence/p2_fatal_fix_2026-10-26/SHA256SUMS` | `5e36d0959f4f7201372b2fb9bda873c93edfec716af0d1828033bc8667bc7639` |
| 新 code identity | P2 口径 87 `.py` | **`c565cd56854a4e55bca456012a4ed273285434fbaac8664baf79b7b4236c56a4`** |
| 修前 code identity | 10-21 锁 / 10-23 build 同值 | `cfd7406709b60344104c17513a0616b59380b971d5ede0d0909bc4f5c1322f07` |

改动文件（只 3 件）：

| 文件 | 修后 SHA-256 | 运行时 |
|---|---|---|
| `src/pathway_v43/pollutant/chemstate.py` | `495d3d0e8ad5fb40d7d557a865a51a1e07d8e51f73e8775a6d72f9842861fdeb` | 是（1 行功能 + 4 行注释） |
| `tests/test_p2_fatal_cn_fix.py`（新增 11 测试） | `daa07201f6ff8ac2e20f8295e52aebd838685e64e05329b1bcdb7e95805a905d` | 否 |
| `tests/test_p2_v1card_mode.py`（仅常量） | `4c18ab53c540982ef6ceb25bbf507f0b6d147d17c00e683a62137e3437e96cfc` | 否 |

## 2. 46/269 映射号普查（CC 追加项）

**口径澄清**：46 是“有 novel 的题数”，269 是“novel 反应规格数”，不是 46 条带映射号。

| 口径 | v1card | v2card | 合计 |
|---|---:|---:|---:|
| 有 novel 的题 | 41 | 41 | **46**（去重） |
| novel 反应规格 | 135 | 134 | **269** |
| 带映射号规格 | 0 | **2** | **2** |
| 无映射号规格 | 135 | 132 | **267** |
| 旧 CN ≠ 新 CN | 0 | 2 | **2**（均为映射号规格） |
| **无映射号但旧 CN ≠ 新 CN** | **0** | **0** | **0** |

- 2 条带映射号规格：novel-1 19 个映射号（1,2,3,4,7–21；5/6 缺失=被编辑原子）、novel-2 20 个；
  清掉映射号后 CN 与 canonical 逐字相同（sha16 `f6b6adde…` / `3d6c403b…`）。
- 覆盖率 269/269；`unparseable_smiles=0`；regex vs RDKit 分歧 0。
- **19 个映射号逐号**：`1,2,3,4,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21`；**缺 5、6**
  （被编辑的羰基 C/O）。19 个括号单元全是映射号原子（`bracket_units=19`、
  `mapped_atoms=19`、`regex_map_tokens=19`），**不是纯冗余括号**；canonical 的 7 个
  括号单元是立体原子、0 映射号。
- **state 未落库、无存量迁移**：v2 失败 run `p2-298-20261021-s5br_79e656bbe6a` 中
  `cs_a1ec…` 的 `states=0`、`state_appearances=0`（写库前 fatal）；v1 同 `state_id`
  行存在且 map-free，`from_dict`/validate PASS。
- **存量扫描**：10-21 两臂 117 个 run DB / 646 states / 749 appearances / 333 个
  state-valued 文件，`cn_identity`/`smiles_isomeric`/`structure_smiles_raw` 含映射号
  均为 **0**；非 10-21 历史批次仍 unknown。
- **1,475 静态串边界**：298 条底物 + 1,177 条池出现，`with_map=0`；所以“1,475 条 0 分歧”
  只覆盖无映射号面，不能替代 46/269 普查。
- 普查输出是聚合计数 + 2 条映射号明细（无结构正文）；**未出 269 行结构 CSV**。若 CC 要
  逐条结构 CSV，需另授权“结构正文外发”；当前 0 条无映射号 CN 分歧已由聚合覆盖。
- 原始件：`census_source/map_number_census.json`（SHA `74575a4f…314e`）、
  `census_source/map_census.py`（SHA `cf017f0a…26ef`）、
  `novel_map_census_summary.json/.csv`、`mapped_novel_specs.csv`。

## 3. notebook 部署步骤（P2 窗口执行）

> 目标树：`/root/v43_migration/v43cP2`（10-23 迁移，RDKit 2026.03.5）。
> **先停 P2 B 臂、确认无并发作业**；本修复不碰旧批根/旧 stop。

1. **备份**：`cp -a src/pathway_v43/pollutant/chemstate.py{,.bak.fatalfix}`，
   `cp -a tests/test_p2_v1card_mode.py{,.bak.fatalfix}`。
2. **应用**：把主 patch 传到 notebook（例 `/root/v43_migration/patches/chemstate_cn_fix.patch`）；
   - 若树是 git 仓库：`git apply --check <patch> && git apply <patch>`；
   - 否则：`patch -p1 --dry-run < <patch> && patch -p1 < <patch>`。
3. **核文件 SHA**：`chemstate.py` = `495d3d0e…`；`test_p2_fatal_cn_fix.py` = `daa07201…`；
   `test_p2_v1card_mode.py` = `4c18ab53…`。
4. **断言解释器**（qwen 提示，必做）：
   ```bash
   PYTHONPATH=/root/v43_migration/v43cP2/src python3 -c \
     "import pathway_v43; print(pathway_v43.__file__)"
   ```
   必须指向 `/root/v43_migration/v43cP2/src/...`；当前 env 的 editable `.pth` 可能指主仓 `src`。
5. **测试**：
   - 全量 `-m "not slow"` → 预期 **2409 passed / 16 deselected**；
   - 定向 57；chemfix 19/19；v1 零漂移 20/20；fatal 复现探针 novel-1/novel-2 PASS。
   完整命令见修复报告 §11.3。
6. **重锁**：按修复报告 §5 的 24 条清单重算：
   - 新 code aggregate `c565cd56…`；
   - 重生 `T_P2_SCRIPT_LOCK_2026-10-26.json`（列入 `chemstate.py`、新测试、v1card 常量）；
   - 部署到 `~/ppv1_hpc/operations/p2_approved_record_20261021/`。
7. **批准包重绑**：
   - `script_lock_sha256` → 新锁 SHA；
   - `identity_expectations.code_identity_aggregate_sha256` → `c565cd56…`；
   - `source_commit` 保持 `11aeeaf…`（不 commit）；
   - `preregistration_text_sha256` 保持 `86242516…`（预注册正文未改）；
   - `chem_review_doc_sha256` 保持 `1bea16b2…`；
   - 新批的 `batch_manifest.json` / `build_origin/<qid>.json` / `run_identity.json` 重绑新
     `build_identity_fingerprint`（修复报告 §5 第 20–22 条）；
   - 重算 `approval_sha256`。
8. **独立复验**：在 `docs/review_evidence/p2_fatal_reverify_2026-10-26/` 记录：
   - 同一 fatal qid novel-1/novel-2 不再触发 `state_fact_rederivation_mismatch`；
   - 负控 raw 指向另一分子仍抛 `raw_identity_mismatch`；
   - 复验脚本打印的 `pathway_v43.__file__` 指向 notebook 树；
   - 命令、HEAD、文件 SHA、预期输出、实际输出。
9. **之后**才按 10-26 任务书发 B 臂：新 `batch_tag`、smoke2→smoke10→full；不自动发。

## 4. 红线

- 不 commit、不 push、不改主树；`source_commit` 保持 `11aeeaf…`。
- 不改预注册正文、批准包签字字段（除上面列出的重绑项）；不伪造签字。
- 不碰 T-I 锁定文件、HPC 批根/runs、旧 coordination stop/lock。
- 金标/reference_graphs 只在 `/root/v43_migration`（700）内消费；不打印、不入仓。
- 同一批根禁止双发；发车前确认无并发 P2 作业。
- 可选 audit-wrap 不启用；若将来启用，aggregate 变 `60cf8030…9921`，必须重锁。

## 5. qwen 代审的两条 P2 提示（非阻断）

1. `evaluation.py:2271` 的参考 CN 扫描面建议复核（是否覆盖参考图节点）。
2. 复验脚本必须断言 `pathway_v43.__file__`，否则可能跑错树。

## 6. 仍 unknown

- notebook 部署树/run env 的 RDKit `2026.03.5` 实测（修复树本地 2026.03.6）。
- 批扫描是否覆盖 reference_graphs 节点。
- 12 个无响应 run + 243 未跑题的历史存量。
- 历史/其他批次是否存在带映射号的持久化 state（本修复不自动治愈旧 state）。
- 部署侧重绑结果。

## 7. 一句话

主 patch 已 PASS、qwen 已 PASS；**notebook 窗口按 §3 应用 + 按 §6 重锁/重绑 + 独立复验后，才发 B 臂**。
本窗口不直接动 notebook，避免和那边的 P2 作业撞车。