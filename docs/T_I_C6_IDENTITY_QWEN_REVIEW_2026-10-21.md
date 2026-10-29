> **provenance：qwen3.8max 代 Codex 复审，按 CC 2026-10-21 指示。** 本报告不代表
> Codex 本人结论，不替代正链 Codex 的最终裁定权；放行/冻结类重要轮次仍建议正链
> 额度恢复后复核确认。
>
> **题域标签：[298域] = 298 / RHEA 通用酶学 / 已见题（post-hoc）。** 本报告只含
> 工程身份、脚本锁与批准包重绑的核验，不含真实成绩、不含模型调用、不含题面/金标
> 内容；298 与 dev 双向不外推。
>
> **复核对象：** `docs/T_I_C6_IDENTITY_RECON_2026-10-21.md` +
> `docs/review_evidence/ti_c6_identity_recon_2026-10-21/`（26 件）。
> **复核环境：** 本地仓 HEAD `11aeeafded1b41185f24de49767933709aad49db`（工作树
> `src/` 零改动）；冻结基线 `c9c6c7a7ae02b46769add09fbc2536323ce8a985`；只读复核，
> 隔离临时副本 `/tmp/qwen_c6_verify/`（`PYTHONDONTWRITEBYTECODE=1`，无字节码/缓存
> 写入）；未连 HPC、未跑作业、未调模型、未读 env/key 内容/金标/题面；未 push。
> **本轮独立复算证据：** `docs/review_evidence/qwen_ti_c6_identity_2026-10-21/`
> （`independent_recompute.json` + 复算脚本 + `SHA256SUMS`）。

# T-I C6 身份期望重锁/重绑复核（qwen3.8max 代 Codex）

## 1. 总裁定

**有条件接受本次身份期望重锁与批准包重绑；允许进入 C7（prepare + P2-face 探针，
非付费）。C8 的付费 smoke、以及任何 run/score/full，须先闭合下方 §3 三项最小回修
并取得 CC 对「移动预注册冻结期望值」的追认。**

| 判读面 | 结论 |
|---|---|
| 重锁的技术正当性 | **成立**。补丁部署是 TI-F1 §3 明写的 C1 部署条件（不打补丁 C1 不绿），因此冻结聚合期望必须随之更新；新值不是照 build 输出反填，而是 `c9c6c7a` + 已批准补丁的确定性哈希，本审用两条独立路径离线复算吻合 |
| 是否掩盖两臂差异/构建漂移 | **未发现**（详见 §2 第 6 项）；跨臂同值门与期望值无关，重锁未放松任何两臂比对 |
| 证据完整性 | **有一处实质缺口**：两处引用的 raw 门输出 `hpc_verify_identity.txt` 不在证据目录，两臂 PASS 的 fingerprint/manifest/n_run_inputs 目前只有实施侧结构化自述 |
| 授权面 | 实施侧标注「工程重锁，不是新批准/不代签」**属实且诚实**（未伪填 CC）；但被改的是**预注册冻结项之一**，追认权在 CC/正链 Codex，本代审不代行 |
| T-I 整体 | 仍 **NO-GO**：C2–C5、C7、C8 未核（本审不授予任何 GO，不批准付费批） |

## 2. 逐项审核（请求 §核点 1–6）

### 2.1 唯一代码差异 = orchestrator 停派发补丁；科学源码未变 —— **通过**

本审独立复算（不采信实施侧读数）：把重锁前抓取的 HPC 部署清单
`pre_state/hpc_deployed_manifest_pre.txt`（151 件）逐件与 `c9c6c7a` 比对——

| 类别 | 本审复算 | 实施侧报告 | 一致 |
|---|---:|---:|---|
| 部署件总数 | 151 | 151 | 是 |
| 在 `c9c6c7a` 中存在 | 140 | 140 | 是 |
| 逐字相同 | 138 | 138 | 是 |
| 两边都有但不同 | 2 | 2 | 是 |
| 仅部署侧有（T-I untracked 操作件） | 11 | 11 | 是 |

计数闭合（138+2=140，140+11=151）。差异 2 件即：
`src/pathway_v43/pollutant/s5b_orchestrator.py`（部署 `a95bb8be…5d62` vs 基线
`3cadb285…e684`）与 `docs/T_H_LAUNCH_TASK_2026-10-20.md`（非锁历史 T-H 任务书，
无代码/身份影响，已披露）。`src/**` 下 py 文件逐件 delta **只有 orchestrator 一件**。

补丁面独立验证：`docs/review_evidence/ti_f1_fatal_2026-10-21/orchestrator_stop_dispatch.patch`
SHA256 = `ee218f71…beb152`（吻合），`+++` 只触及 orchestrator 一个文件；对纯
`c9c6c7a` 树 `git apply` 干净，产物 SHA256 = `a95bb8be…5d62`（= HPC 部署实测 =
`hpc_verify_lock.json` 的 `expected_patched_sha256`）；`git apply -R` 可还原到
`3cadb285…e684`。补丁后文件 `stop_check` 出现 **10 次**、`dispatch_stopped` /
`dispatch_stop_reason` / `s5b_stop_check_failed` 三个标记均在；纯树 `stop_check`
出现 0 次——与 `hpc_verify_lock.json`（`stop_check_occurrences=10`、
`patched_match=true`）逐字吻合。

科学源码两件未变（本审从 `c9c6c7a` blob 直接计算）：
`s5b_compiler.py` = `f917762b…2685dfc`、`evaluation.py` = `37c09231…8dc75ad8`，
与部署清单、锁、`arm_config.scientific_source_sha256` 四处同值。

### 2.2 aggregate `a24700ab…` → `1aac04da…` 与「纯树 vs 补丁树」一致；两臂同为 new —— **通过（附证据缺口）**

本审用两条互相独立的路径复算聚合（算法核自
`src/pathway_v43/storage/run_identity.py:76–100`，profile
`pollutant_pathway_v1`，87 件 py）：

| 路径 | 纯 `c9c6c7a` | `c9c6c7a` + 补丁 |
|---|---|---|
| A：`git archive` 到临时副本，实算文件字节（补丁路径再 `git apply`） | `a24700ab…ff6b85` | `1aac04da…2e4519` |
| B：直接用重锁前 HPC 部署清单里的逐件哈希聚合 | `a24700ab…ff6b85`（由 `c9c6c7a` blob 算） | `1aac04da…2e4519`（由部署清单算） |

两路径与实施侧 `aggregate_recompute.json`、与重锁前失败输出
`pre_state/verify_identity_pre.txt`（expected `a24700ab` / actual `1aac04da`）全部
吻合。路径 B 尤其关键：**新期望值等于重锁之前就已存在的 HPC 部署树的确定性聚合**，
不是「先看 build 输出再填期望」。

两臂同为 new：两份 raw build 日志（`ti_build_47002738.out` GLM /
`ti_build_47002742.out` DeepSeek）均 `TI-BUILD-PASS`、`n_questions=298`、
`questions_source_sha256=9f5955d4…f9211c`（= `arm_config.questions.sha256` 冻结值）、
`registration_order_head` 五条逐字相同、calibrator 路径同为
`/work/home/aclhl3hbth/EnzymeAgent/v43cTH/...`（同一代码根）。结构上
`code_identity` 由被执行的共享代码根计算，两臂必然同值。

**缺口（→ §3 A）：** 两臂 `build_identity.json` / `batch_manifest.json` 原件未落盘，
`arms_byte_identical=true`、`31e8ec20…`、`10deab6d…`、`5014fa13…` 只有实施侧结构化
读数；无 HPC 侧原始文件副本可校。

### 2.3 `arm_config.identity_update` 完整性；锁 14/14 与新文件一致 —— **通过**

`scripts/hpc/ti_arm_config.json`（`8dab7ebc…77695`，= 锁内值 = post_state 副本 =
HPC `verify_lock` 行值）与 pre 副本做扁平化逐键对比：**变更只有 1 个已有键 +
新增 1 个块，0 删除**。

| 面 | 本审复算结果 |
|---|---|
| 唯一 changed key | `identity_expectations.code_identity_aggregate_sha256`：`a24700ab…` → `1aac04da…` |
| 新增块 `identity_update`（9 键） | `reason` / `patch_sha256` / `old_…` / `new_…` / `changed_file` / `changed_file_sha256` / `base_source_commit` / `updated_at`（`2026-10-20T20:10:39Z`）/ `note` —— 请求要求的 reason/patch sha/old/new/time **五项齐备** |
| 未动的冻结面 | 其余 7 项 identity 期望（`s5b-compiler-6`/`s5b-pool-policy-9`/`s5b-recorded-source-4`/`s5b-corpus-retrieval-6`/`record-side-formnorm-1`/`s5b-analog-route-f1f4-1`/`rdkit 2026.03.5`）、`scientific_source_sha256`、题卷 sha+298、`batch_tag=t-i-298-20261020`、`scoring`、`no_cap`、`arms`/`env_file`、`paths`、`immutable_batch_names` 全部逐字不变 |

锁面：`docs/T_I_SCRIPT_LOCK_2026-10-20.json` 本审复算 SHA256 =
`0fe47c84…54f4641`（= 报告值 = 批准包绑定值 = post_state 副本），pre 锁 =
`f0a43420…625f46`（吻合）。14 件、`missing=[]`、键集与 pre 锁完全相同、
**唯一变更条目 = `ti_arm_config.json`（`99ac34bb…` → `8dab7ebc…`）**，其余 13 件
逐字不变；`relock` 块含 reason / previous_lock_sha256 / patch sha / old+new
aggregate / changed_files / relocked_at，字段齐备。

| 核对面 | 本审复算 |
|---|---|
| HPC 部署树（`hpc_verify_lock.json` 14 行） | 与锁逐件同值，**0 处不符**，`files_checked=14`、`files_all_match=true` |
| 本地仓工作树 | **13/14**；唯一不符 = `s5b_compiler.py`（HEAD `11aeeaf` 为 `58cf3dc9…`，冻结部署位为 `f917762b…`），实施侧已在报告 §2/§4 与 `lock_relock.json` 主动披露，非隐瞒 |

### 2.4 批准包重绑 —— **通过（附一条必须补的登记项，见 §3 B）**

| 核点 | 本审复算 |
|---|---|
| 三份 prose 快照原字节 | `TASK_T_I_LAUNCH` `0b9b0557…`、`T_I_PREREG` `2e45d407…`、`T_I_CODEX_FINAL_REVIEW` `8344265c…`：与 pre 清单同值，且与仓内 `docs/` 同名文件**逐字节相同** |
| 第四份（脚本锁） | 按新 14 件重绑为 `0fe47c84…`，`preregistration_docs.script_lock.sha256` 与顶层 `script_lock_sha256` 同步更新 |
| 批准 JSON 变更范围 | 扁平化对比：**changed 2 键**（两处锁绑定）、**added 17 键**（全在 `identity_reconciliation` 下）、**removed 0 键** |
| 保留字段 | `approval_basis`=「原预注册+任务书+本终审增补」、`approval_source`=Codex 代 CC/师姐、`approval_source_kind=codex_delegated_cc_shijie`、`approved_at=2026-10-20T15:49:53Z`、`no_cap_ack=true`、`budget_mode`、`user_decision_date=2026-10-20`、`approval_status`、`preregistration_id`、授权链 —— **全部原值** |
| 是否伪填 CC 本人 | **否**。新增块自述 `reconciled_by = "T-I C6 identity reconciliation (engineering re-lock; not a new approval or signature)"`，`approved_at_preserved` 明示未改；无任何 CC 亲签字段 |
| `identity_reconciliation` 内容 | old/new aggregate、patch path+sha、patched file+sha、base commit、两臂 build 指纹、old/new 锁 SHA、`reconciled_at`、reason、note —— 登记完整、无伪填 |
| 清单一致性 | 本地包 `shasum -c` **5/5 exit 0**；`post_state/SHA256SUMS.external.hpc` 实算 SHA256 = `0b44b197…f6945`（= 报告值 = `hpc_record_post.txt` 值）；`budget_no_cap.json` `a2a61261…` 在 pre/post 两份外部清单中同值（未动）；外部 7 条 = 5 + budget + SHA256SUMS 自身，计数闭合 |

**必须补的登记项：** 冻结 prose 快照仍把 `a24700ab…` 写成期望身份事实——
`T_I_PREREG_2026-10-20.md` 第 77 行、`TASK_T_I_LAUNCH_2026-10-20.md` 第 74 与
138 行（第 138 行正是「期望身份事实」清单）。prose 保持原字节是对的（不得回写
已批准快照），但机器面已改 `1aac04da…`，于是同一批准包内出现**文本期望 vs 机器
期望分叉**，且现有 note 只说「prose 保持原字节」，未明示「prose 的 a24700ab 自
C6 起被 1aac04da 取代」。C7/C8 的操作者若照 prose 核对会得到错误期望。

### 2.5 两臂身份门是否真 PASS —— **需修正（证据缺口，非结论推翻）**

门语义本审已读源码核实（`scripts/hpc/ti_operations.py`，锁内 SHA `931966a8…` =
本地 = HPC 同值，故读到的就是发车执行的字节）：

- `check_build_identity`（:403–460）：逐键比对 `cfg["identity_expectations"]`
  全部 8 项 → 题卷 sha 与冻结值同 → `n_questions=298` → `run_inputs` 条数 298、
  逐条 qid 非空且 `run_input_sha256` 为 64 位 hex、qid 无重复 → fingerprint 为
  64 位 hex → `manifest.build_identity_ref` 指纹与 `build_identity.json` 一致 →
  `registration_order` 298 条且 qid 集合相同 → `entries` 298 → `batch_tag` 同配置；
  任一不符即 `RuntimeError`。
- `verify_identity`（:1888–1928）：对两臂各跑一遍上述检查，再跨臂要求
  `batch_tag` / `manifest_sha256` / `build_identity_fingerprint` /
  `identity_facts_sha256` 四者唯一值，且两臂逐题 `(qid, run_input_sha256)` 序列
  完全相同，否则报错不落 PASS。
- `build_identity_fingerprint` = `sha256(canonical_json(payload))`，payload 含
  `code_identity_aggregate_sha256` 等（`storage/build_identity.py:67/101/141`），
  并有指纹重算校验（:228–232）——指纹不能脱离 payload 伪造。

结论：门是真门，不是形式检查。重锁只改期望常量，**不削弱任何跨臂比对**。

但证据面有一处实质缺口：

| 事实 | 状态 |
|---|---|
| 重锁前 FAIL 原件 | **在案**：`pre_state/verify_identity_pre.txt`，`TI-OPERATIONS-STOP` + expected `a24700ab`/actual `1aac04da` + `EXIT_CODE=1`；且差异**只有 aggregate 一项**，说明其余 7 项期望当时已匹配 |
| 重锁后两臂 PASS 原件 | **缺失**：报告 §7 与 `hpc_sync.json:83` 两处引用 `hpc_verify_identity.txt`，该文件不在证据目录、不在 `SHA256SUMS`；全目录中含 `TI-BUILD-IDENTITY-PASS` 字串的只有 `hpc_sync.json`（实施侧结构化自述） |
| 可推定部分 | aggregate 维度可推定成立（新期望 = 本审独立复算的部署树聚合）；`hpc_verify_lock.json`、`hpc_approval_validation.json`、两份 build 日志均为 raw 且在案 |
| 不可推定部分 | `build_identity_fingerprint=5014fa13…`、`manifest_sha256=10deab6d…`、`n_run_inputs=298` 的**两臂同值**目前只有自述，无 raw stdout 佐证 |

判定：**不推翻 PASS 结论，但必须补 raw 原件**（§3 A）。这属 AGENTS.md「返工教训」
§5（来源声明与本会话独立执行分开）与 §6（证据可核）的范围，不是新增阶段门。

### 2.6 是否用重锁掩盖两臂差异/构建漂移 —— **不成立（未发现掩盖迹象）**

六条独立理由：

1. **改动面最小且可枚举**：arm_config 只动 1 个键、锁只动 1 个条目、批准 JSON 只动
   2 个绑定键 + 1 个纯登记块；题卷、298、batch_tag、7 项版本期望、科学源码 SHA、
   判分口径、no-cap、两臂 env/模型、`immutable_batch_names` 全部逐字未动。
2. **跨臂门与期望值解耦**：`verify_identity` 的两臂同值比对（manifest 字节 SHA、
   指纹、逐题 run_input SHA）不依赖期望常量，重锁无法用它洗掉臂间差异。
3. **重锁前 FAIL 只有 aggregate 一项**：若存在构建漂移（版本/资产/RDKit/池变化），
   同一次失败会一并暴露其余 7 项期望不符——实际没有。
4. **新值可离线复算、非反填**：本审两条独立路径（archive+apply、部署清单聚合）都
   得到 `1aac04da…`；补丁可 `git apply -R` 还原到 `3cadb285…`，即新旧期望之间只有
   一个已批准、可逆、单文件的确定性变换。
5. **逻辑上必须重锁**：TI-F1 §3 的部署条件要求 HPC 部署树 orchestrator 含补丁
   （`a95bb8be…`），否则 C1 不绿；补丁既已按批复部署，纯树聚合 `a24700ab…` 就不
   可能再是实测值。可选项只有「回退补丁」（TI-F1 禁止）或「更新期望」，本轮选后者
   且把 old/new/理由/补丁 SHA 全部登记在案。
6. **未触犯任务书 §3.2 禁令**：禁令是「不得用『改一臂旁件』或『重算新 ID』洗掉
   差异」——本轮无臂间差异可洗，改动作用于两臂共享的单一 `arm_config`，且新值不是
   凭新 build 反造的 ID（报告 §8 也明示「未用新 build 反造旧指纹」）。

**残余风险（须持续登记，非本轮缺陷）**：本地仓 HEAD 已与 T-I 部署位分叉
（`s5b_compiler.py`：HEAD `58cf3dc9…` vs 冻结 `f917762b…`；orchestrator 补丁未合并
主树，本地为纯 `3cadb285…`）。**从 HEAD 重新部署会得到第三个聚合值**（既非
`a24700ab` 也非 `1aac04da`），届时身份门必红。任何重部署必须从 `c9c6c7a` + 该补丁
重建，并逐件核 14 件锁；不得以 HEAD 字节替换冻结科学源码。

## 3. 最小回修清单（仅请求范围内）

| # | 级别 | 事项 | 具体做法（不改 src/tests/scripts/既有 docs/封存批） |
|---|---|---|---|
| A | **必须（C8 付费 smoke 与任何 run 之前）** | 补两臂身份门 raw 原件 | 把 HPC 上 `verify-identity --arm glm` 与 `--arm deepseek` 的原始 stdout + exit code 落盘为 `docs/review_evidence/ti_c6_identity_recon_2026-10-21/hpc_verify_identity.txt`，并追加进该目录 `SHA256SUMS`（新件追加，不回写既有 26 件哈希）；同时把两臂 `build_identity.json`/`batch_manifest.json` 的**哈希清单**（非题面内容）附上。若原件已不可得，则改正报告 §7 与 `hpc_sync.json` 的 `evidence` 引用指向实际存在文件，并在报告 §8 明示「PASS 无 raw 原件，仅结构化自述」 |
| B | **必须（进入 C7 之前）** | 显式登记 prose 期望被取代 | 新增一份独立 addendum（例：`docs/T_I_C6_IDENTITY_ADDENDUM_2026-10-21.md`，**不改**冻结 prose 原字节），写明：`T_I_PREREG` 第 77 行、`TASK_T_I_LAUNCH` 第 74/138 行的 `a24700ab…` 自 C6 起由 `1aac04da…` 取代，理由 = TI-F1 §3 部署条件，指针 = 补丁 SHA `ee218f71…` 与本报告 §2.1–2.2；并在 `arm_config.identity_update.note` 与批准 JSON `identity_reconciliation.note` 里加一句指向该 addendum（这两处是本 round 新增块，可改；改后须重算并同步锁/批准绑定 SHA） |
| C | **必须（C5 付费调用与任何 run/full 之前）** | 重锁的授权归属追认 | 由 CC（或正链 Codex 额度恢复后）追认「移动预注册冻结期望值」这一动作；追认记录写入 addendum 或批准包外新件。本代审**不代行批准** |
| D | 建议（不阻塞） | 复算口径写准 | `aggregate_recompute.json` 的 `aggregate_algorithm` 写作 `src/pathway_v43/**/*.py`，但 `run_identity` 实际 rel 键相对 `src/`（即 `pathway_v43/...`）。照文档字面复算会得到不同聚合（本审初次即踩到）。哈希值本身无误，只需把口径写准以便第三方逐字复现 |
| E | 建议（不阻塞，归 CC 决定） | 部署但未入锁的操作件 | `scripts/hpc/chain13_monitor.sh` 在部署树中但不在 14 件锁内（先前既有状态，非本轮引入）。C8 用到 monitor 时，建议 CC 决定是否纳入锁；本审不据此升级阻塞 |

## 4. 仍需 CC / 老师批准的事项（本代审只给建议，不裁定）

1. **§3 C 的追认**：预注册冻结项（期望身份事实之一）被移动，属预注册层面的变更，
   须 CC 追认或正链 Codex 复核确认；qwen 代审不批。
2. **T-I 整体 GO/NO-GO 与付费批**：本报告只接受「重锁/重绑」这一工程动作，
   **不批准** C5 付费最小调用、不批准任何 run/score/full、不批准新付费批；唯一判据
   仍是 Codex §4.2 的 `GO(阶段) = 全部必须前置实证为真 AND 无活动停点`。
3. **顺序知情项（范围外，仅披露）**：C6 build 作业（`47002738`/`47002742`，
   2026-10-20T18:53Z）已跑，而 C5 两臂最小真实调用仍未执行；任务书 §3 的表述是
   「先双臂预检通过，再并行 build」。build 非付费、不含模型调用，本审不据此升级
   阻塞，但请 CC 知情并在 C5/C7 排期时明确顺序口径。
4. **本地 HEAD 与 T-I 部署位分叉的处置**：是否/何时把停派发补丁合并主树、是否把
   T-I 重绑件（当前全为 untracked：`ti_arm_config.json`、锁、批准包、两份报告）
   提交入库以取得 git 历史锚点——归 CC 决定（评审侧文档默认留未跟踪是既有约定）。

## 5. unknown / 本审未核清单

| 项 | 状态 |
|---|---|
| 两臂身份门 PASS 的 raw stdout | **未核**（原件缺失，见 §2.5 / §3 A）；aggregate 维度已由本审独立复算支撑，fingerprint/manifest/n_run_inputs 的两臂同值仍为自述 |
| HPC 现场状态 | **未核**：本审未连 HPC，所有远端读数来自实施侧落盘证据（`hpc_verify_lock.json`、`hpc_record_post.txt`、`hpc_full_validation.txt`、部署清单）；`hpc_sync.json` 中 `SHA256SUMS.external` 的 `local_sha256=null` 亦如实标注为 HPC-only |
| 两臂 `build_identity.json`/`batch_manifest.json` 原件 | **未核**（无副本落盘） |
| C5 / C7 / C8 | **未核**：无最小真实调用、无 prepare 与 P2-face 现场读数（`files=298`/`specs_total=531` 等冻结期望无实测）、无真实 monitor 作业与 smoke2/smoke10 回执 |
| C2 / C3 / C4 | **未核**（凭证/净环境/netcheck/两臂 env 与有效请求参数），本轮不在验收面内 |
| 停派发补丁的运行时实效 | **未核**：本审只核字节身份与标记存在（`stop_check`×10、三个标记），不认证真实站点 scancel/停派发效果、失败频率或任何科学收益 |
| `docs/T_H_LAUNCH_TASK_2026-10-20.md` 部署副本为旧版（`abbfa39` 系） | 已披露、不入锁、不影响代码身份；本审未追其内容差异 |
| 时间戳口径 | 记录为 UTC（`2026-10-20T20:10–20:11Z`），与本地文件 mtime（10-21 04:1x，UTC+8）一致；无异常，但报告标题日期与记录日期跨日，读者需知其时区差 |
| 合成/工程绿的性质 | 本轮全部为工程身份证据，**不构成真实可发车证据**；不得外推为成绩或性能 |

## 6. 与上一轮结论的关系

- 与 `docs/T_I_F1_QWEN_REREVIEW_2026-10-21.md` §3（部署条件：HPC orchestrator 须含
  补丁，SHA 对上 `a95bb8be…5d62`）**一致且已闭合**：本审从部署清单与 `verify_lock`
  两处独立见到该 SHA。
- 与同文 §5（旧锁 `f0a43420…`、旧批准 `190e42a5…` 复算吻合）**无冲突**：本轮 pre
  副本实算即这两个值，变更后为 `0fe47c84…` / `b631f761…`，链条连续、旧件以
  `.bak.20261021_c6` 与 `pre_state/` 双份保留。
- 与 `docs/T_I_CODEX_FINAL_REVIEW_2026-10-20.md` §4.1 的 C6 判据对照：build 作业与
  build-gate 成功（raw 在案）、题卷冻结 SHA 与 298 一致（raw 在案）、D6 身份比较
  （**raw 缺，见 §3 A**）；「代码/科学聚合…符合」的含义自本轮起为「符合补丁后
  重锁期望」，此语义变化须由 §3 B/C 显式登记与追认后才算闭合。
- 本审未发现需要重开 TI-F1/TI-F2 的新证据；已证修复保持关闭。
