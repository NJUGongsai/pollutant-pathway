> **provenance：qwen3.8max 代 Codex 复审，按 CC 2026-10-21 指示；C 项以「qwen3.8max
> 代 Codex 代 CC 代决追认」身份签署（CC 2026-10-21 授权「需要我/师姐裁决的由 Codex
> 代决，Codex 裁决即最终裁决」，本件为该代决链在 Codex 无额度时的代理）。不冒充 CC
> 本人签署，不代表 Codex 正链本人结论；CC 后置复核。**
>
> **题域标签：[298域] = 298 / RHEA 通用酶学 / 已见题（post-hoc）。** 本件只含工程
> 身份、脚本锁与证据引用核验，不含真实成绩、不含模型调用、不含题面/金标内容；
> 298 与 dev 双向不外推。
>
> **复核对象：** `docs/T_I_C6_IDENTITY_RECON_ADDENDUM_2026-10-21.md`（SHA256
> `3b78bee4…8bc48`）；`docs/review_evidence/ti_c6_identity_recon_2026-10-21/`
> （SHA256SUMS 39 条，本审 `shasum -c` 39/39 OK，exit 0；计数闭合 = 上轮 26 +
> raw_gate 12 + 附录 1）；`docs/T_I_C6_IDENTITY_QWEN_REVIEW_2026-10-21.md` §3 A/B/C。
> **复核环境：** 本地仓 HEAD `11aeeafded1b41185f24de49767933709aad49db`；只读，
> 未连 HPC、未跑作业、未调模型、未读 env/key 内容/金标/题面、未 push、未改任何
> 既有代码/文档/证据/批准件字节。本审核验输出落
> `docs/review_evidence/qwen_ti_c6_ack_2026-10-21/verification_log.txt`（新目录，
> 追加式）。时间口径：UTC 2026-10-20T20:47Z 起（本地 2026-10-21 凌晨，UTC+8）。

# T-I C6 身份重锁 — C 项代决追认与 A/B 闭合复核

## 1. 总裁定

**放行：A 闭合、B 闭合（一处字面偏差经等效方式闭合，留痕不改判）、C 追认成立。
T-I C6 的三项停点（qwen 代审 §3 A/B/C）全部解除，C8 付费 smoke / run 可以发车。**

发车仍受既有约束，本追认不豁免其中任何一条：

1. 原 C8 条件与分级（smoke 先行、逐级放大）与**原监控阈值**照旧；
2. 批准包 `b631f761…` 的 no-cap 预算框架、急停条件照旧；C8 付费 smoke 属既有批准
   范围，**本件不批准任何新付费批**；
3. 任何重部署必须从 `c9c6c7a` + TI-F1 补丁重建（HEAD 字节会得到第三个聚合值，
   身份门必红，见上轮 §2.6 残余风险）；
4. `GO(阶段) = 全部必须前置实证为真 AND 无活动停点`（Codex 终审 §4.2）逐阶段照旧。

## 2. A 项复核 — 两臂身份门 raw 原件 —— **闭合**

| 核点 | 本审实测 | 结论 |
|---|---|---|
| raw stdout 四项读数 | 两臂 stdout 均含 `"gate": "TI-BUILD-IDENTITY-PASS"`、`build_identity_fingerprint = 5014fa13…330a`、`manifest_sha256 = 10deab6d…cb00`、`n_run_inputs: 298`（另有 `batch_tag = t-i-298-20261020`） | 命中 |
| exit / stderr | 两臂 exit code 均 `0`；stderr 均 0 字节 | 命中 |
| 两臂 stdout 关系 | 逐字节相同（SHA256 同为 `94687a38…c742`，`cmp` 通过）；与附录 §2.1 命令语义备注一致——`verify-identity` 每次调用内部同校两臂，两次调用是独立进程；上轮 §2.5 已读源码核实该门为真门（跨臂 manifest/指纹/逐题 run_input 同值），此现象不构成缺口 | 一致 |
| SHA256SUMS | 39 条 `shasum -c` 全部 OK（含 raw_gate 12 件、附录 1 件、既有 26 件）；计数闭合 26+12+1=39 | 通过 |
| meta.txt 交叉哈希 | HPC 侧实测锁 SHA `0fe47c84…4641`、批准 JSON `b631f761…1a19`、arm_config `8dab7ebc…7695`、补丁后 orchestrator `a95bb8be…5d62`、compiler `f917762b…5dfc`、evaluation `37c09231…5ad8`、questions.jsonl `9f5955d4…211c`（仅哈希）——与本审本地实算及锁/批准包逐一同值 | 通过 |
| `hpc_verify_identity.txt` 引用修正 | `hpc_sync.json` 的 `verify_identity.evidence` 已改为实际存在的 12 件 `raw_gate/*` 清单，补 `recheck_*`、`arm_flag_note`、`remote_git_head`、`lock_sha256`、`raw_gate_sha256`（内嵌 12 条哈希与本审实算一致）；`previous_evidence_reference` 诚实登记旧引用文件缺失且已被取代。旧字串仅残存于冻结报告 `T_I_C6_IDENTITY_RECON_2026-10-21.md` §7（第 161 行）——该件是上一轮冻结记录、按约定不回写，由附录 §2.4 显式取代，处置正确 | 通过 |
| 时间线自洽 | 两臂 `build_identity.json`/`batch_manifest.json` mtime 2026-10-21 03:56（+0800，= 19:56Z）早于门重跑 20:42:35–41Z；assertions 20:43:31Z；`assertions_check.txt` 15 条全 PASS、OVERALL PASS | 通过 |

上轮 §3 A 的两个分支（补 raw 原件，或改引用并声明无原件）中，实施侧走了**更强的
第一分支**：真重跑并落盘原始 stdout/stderr/exit/命令/时间/meta（本地 + HPC 双份）。
A 项缺口按原口径闭合。

## 3. B 项复核 — prose 期望被取代的显式登记 —— **闭合（一处字面偏差，等效接受）**

| 核点 | 本审实测 | 结论 |
|---|---|---|
| 取代登记明确 | 附录 §1.1 逐字列出三处：`T_I_PREREG_2026-10-20.md` L77、`TASK_T_I_LAUNCH_2026-10-20.md` L74、L138，均标「已被取代」；§1.2 给出旧值 `a24700ab…6b85` → 新值 `1aac04da…4519`、基准 commit `c9c6c7a`；§1.4 明示附录为「prose 期望已被取代」的**唯一生效说明**，C7/C8 一律以 `ti_arm_config.json` 的 `1aac04da…` 为准 | 通过 |
| 原 prose 字节未动 | 本审实算三份快照 SHA256：PREREG `2e45d407…21b3`、LAUNCH `0b9b0557…b456`、CODEX_FINAL_REVIEW `8344265c…f39d`，与附录 §1.4、`hpc_sync.json:unchanged_prose_snapshots`、批准包绑定值三方同值；且三处行内 `a24700ab…` 字面仍在（本审 sed 抽查原文） | 通过 |
| 理由链 | 理由 = TI-F1 批准停派发补丁（补丁文件实算 SHA256 `ee218f71…b152`，吻合）；变更文件仅 orchestrator（`3cadb285…` → `a95bb8be…`）；科学源码两件未变（compiler/evaluation 哈希四处同值）。与上轮 §2.1–2.2 两条独立路径复算结论一致 | 通过 |
| 机器面登记 | `arm_config.identity_expectations.code_identity_aggregate_sha256 = 1aac04da…`（本审直读）；`identity_update` 块 reason/patch_sha/old/new/changed_file/base_commit/updated_at/note 齐备；批准 JSON `identity_reconciliation.reconciled_by` 仍诚实标注 "engineering re-lock; not a new approval or signature" | 通过 |
| **字面偏差（留痕）** | 上轮 §3 B 末句曾要求在 `arm_config.identity_update.note` 与批准 JSON `identity_reconciliation.note` 里各加一句指向附录。实施侧未改这两处，改为：`hpc_sync.json:raw_gate_recheck.addendum`（path + sha256）指向附录 + 附录自我声明唯一生效。**偏差原因成立**：改锁内 note 会变更 `8dab7ebc…` → 连锁重锁 → 重绑批准包，字节改动面反而更大；等效路径已达成「操作者能发现取代关系」的目的。**裁定：等效闭合，不要求回修**；配套要求见 §6 建议 1 | 等效接受 |
| 附录自身入证 | 附录已列入证据目录 SHA256SUMS（`3b78bee4…`，本审 OK），与本审实算一致 | 通过 |

## 4. C 项追认原文（代决）

以下为追认正文，自本件落盘即生效（CC 后置复核）：

> **C 项追认（qwen3.8max 代 Codex 代 CC 代决，按 CC 2026-10-21 授权）**
>
> 1. **追认** T-I 本批（batch_tag `t-i-298-20261020`）冻结期望值
>    `code_identity_aggregate_sha256` 由
>    `a24700abf992fb7e9a32822268a4e407b8497ef5d1d216fc11bcfa6762ff6b85`
>    变更为
>    `1aac04da751660ce231f5403f7304bd39afd6bc49506364eab994030a02e4519`。
>    依据：新值 = 基准 `c9c6c7a` + TI-F1 批准停派发补丁（`ee218f71…`）的确定性
>    聚合，经 qwen 代审两条独立路径离线复算吻合，非照 build 输出反填；重锁前
>    FAIL 原件显示差异仅此一项，其余 7 项期望当时已匹配；补丁是 C1 部署条件、
>    不得回退，故期望更新是唯一合规选项。
> 2. **原 prose 不改**：`T_I_PREREG` L77、`TASK_T_I_LAUNCH` L74/L138 的
>    `a24700ab…` 字面保持原字节；`docs/T_I_C6_IDENTITY_RECON_ADDENDUM_2026-10-21.md`
>    为「prose 期望已被取代」的唯一生效说明。C7/C8 及后续操作者核期望一律以
>    `scripts/hpc/ti_arm_config.json` 的 `1aac04da…` 为准。
> 3. **效力边界**：本追认不冒充 CC 本人签署，不构成新预注册、不构成判据变更、
>    不批准任何新付费批；既有批准包 `b631f761…`（`approved_at
>    2026-10-20T15:49:53Z`、`approval_source_kind=codex_delegated_cc_shijie`、
>    no-cap）身份与效力不变，本追认只消除其内部「文本期望 vs 机器期望」的分叉。
>    跨臂同值门与期望常量解耦，本追认不放松任何两臂比对。
> 4. **CC 后置复核**：CC 复核通过后本追认转为终局；CC 若否决，本追认作废，T-I
>    回到 §3 A/B/C 停点状态，已按新期望执行的只读门结果不受影响。

## 5. A/B/C 闭合判定与 C8 发车

| 项 | 判定 |
|---|---|
| A（两臂 raw 门原件） | **闭合**（§2） |
| B（prose 取代显式登记） | **闭合**（§3，含一处等效接受的字面偏差） |
| C（重锁授权归属追认） | **闭合**（§4 追认落定，CC 后置复核） |

**C8 付费 smoke / run 可以发车。** 上轮 §1 总裁定的停点条件（「须先闭合 §3 三项
最小回修并取得追认」）已满足。发车照旧受 §1 所列 4 条约束；smoke 回执、monitor
读数、任何阈值触碰按原任务书回报，不属本件豁免范围。

## 6. 最小回修清单

无新增必须回修项。建议（不阻塞发车）：

1. C7/C8 的现场任务书/操作单里**显式引用附录文件路径 + SHA**（`3b78bee4…`），
   弥补 §3 偏差项：只读批准 JSON 的操作者由此能发现取代关系；
2. E 项（`chain13_monitor.sh` 部署但未入 14 件锁）：若 C8 实际使用该 monitor，
   建议 CC 在其首次付费 run 前裁定是否纳锁；不纳锁也可发车，但须在 C8 记录中
   登记其 SHA `a006c61c…e82c`；
3. D 项口径更正已由附录 §4 完成（不回写 `aggregate_recompute.json`），按此关闭。

## 7. 仍需 CC / 老师批准或裁定的事项（本件只给建议）

1. **本追认的后置复核**（§4 第 4 条）；
2. E 项 monitor 是否纳锁（§6 建议 2）；
3. 本地 HEAD（`11aeeaf`）与 T-I 冻结部署位的分叉处置：补丁是否合并主树、T-I
   重绑件（当前均 untracked）是否提交入库取得 git 锚点——归 CC；
4. 上轮 §4.3 顺序知情项（C6 build 先于 C5 两臂最小真实调用）：CC 本次指示 C8 可
   发车即视为知情；C5 是否仍单独补做、何时做，归 CC 排期；
5. 任何新付费批、判据变更（v3/T1′ 类）、真实题面外发——一律仍须 CC/老师逐项拍板，
   本件不涉及。

## 8. unknown / 本审未核清单

| 项 | 状态 |
|---|---|
| HPC 现场状态 | **未核**：本审未连 HPC；raw_gate 12 件为实施侧 2026-10-20T20:42Z 抓取后落盘的原件，本审只核其字节/哈希/内嵌交叉引用自洽，抓取链真实性依赖实施侧记录（meta.txt 哈希与本审本地实算全吻合，无矛盾迹象） |
| 两臂 `build_identity.json`/`batch_manifest.json` 内容面 | **未核**（按红线只登记哈希/大小/计数，未复制、未读题面内容） |
| `hpc_sync.json` 旧行值 `494b88c7…` 的声明 | **未独立核**（目录内无旧版 SHA256SUMS 副本；当前行 verify OK，不影响 A 项结论，非阻塞） |
| C5 / C7 / C8 现场读数 | **未核**：无最小真实调用、无 prepare/P2-face 实测、无 smoke 回执；C8 发车后按原阈值回报 |
| C2 / C3 / C4 | **未核**（不在本轮验收面） |
| 停派发补丁运行时实效 | **未核**（同上轮：只核字节身份，不认证真实 scancel/停派发效果或任何科学收益） |
| 本地工作树杂项 | `docs/T_H_P0B_D6_IMPL_2026-10-20.md` 处于已修改状态（非 T-I C6 验收面，仅登记）；T-I 重绑件均 untracked（既有约定） |
| 性质声明 | 本轮全部为工程身份证据与授权面闭合，**不构成真实可发车能力的成绩证明**；不得外推为模型性能或收益 |

## 9. 与上一轮结论的关系

上轮（`docs/T_I_C6_IDENTITY_QWEN_REVIEW_2026-10-21.md`）§3 A/B/C 三项必须回修与
§1 停点条件，本审逐项对证后判定全部闭合，无冲突、无重开项；上轮 §2.6 残余风险
（HEAD 分叉、重部署须从 `c9c6c7a`+补丁重建）继续有效并纳入 §1 发车约束第 3 条。
