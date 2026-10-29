# T-I B2 新批身份确认件（2026-10-21）

> **provenance：qwen3.8max 代 Codex 复审，按 CC 2026-10-21 指示**（Codex 无额度，
> 依授权链 CC 2026-10-20/21 → Codex 代决 → qwen3.8max 代 Codex 执行；不冒充 Codex/CC
> 本人，不替代正链 Codex 恢复后的最终复核权）。
>
> **题域标签：[298域] = 298 / RHEA 通用酶学 / 已见题（post-hoc）。** 本件只含工程身份
> 核验，不含科学成绩；一切数字与 dev 双向不外推。
>
> 审阅环境：本机只读（macOS，`/Volumes/CC/Enzyme_Agent/dependingv43`，实际 HEAD
> `11aeeafded1b41185f24de49767933709aad49db`）。未连 HPC、未跑作业、未调用模型、
> 未读 key/env 值/金标/题面/reference_graphs、未改代码/证据/批准件、未 push。
> 新增文件仅本确认件。本地核验手段：SHA256SUMS 全量复核、pre_state↔现树逐件 diff、
> 冻结位（`c9c6c7a`）源码只读走查（`ti_operations.py` 门逻辑、`storage/build_identity.py`
> 指纹定义、`s5b_builder.py` run_id 构造）。

## 1. 总裁定

**确认（CONFIRMED）：B2 新批身份成立，证据链闭合到本地可核范围；允许进入 C7
prepare + P2-face 探针（零模型费），并在 §4 条件下允许 CC 手动发 run。**

- 证据目录 `docs/review_evidence/ti_b2_rebatch_2026-10-21/` SHA256SUMS **12/12 OK**；
  soak 门证据 `ti_b2_soak_2026-10-21/`（9/9 OK）与 `ti_c0_c5_2026-10-21/c8_soak3_*`
  （5/5 OK）本地复核通过。
- 现树三件机器面与证据声明逐哈希吻合：锁 `45a82d25…`、批准 JSON `7e5d1635…`、
  config `4feecdc3…`；批准包内部 SHA256SUMS 实测 `31493bc1…`（5/5 OK），与证据
  `sums_sha256`/`hpc_sums_sha256` 同值。
- 身份门 raw 原件（exit 0 + stderr 空 + `TI-BUILD-IDENTITY-PASS`，两臂批根均在 stdout）
  已本地哈希核验；门语义经源码走查确认覆盖两臂 fingerprint/manifest/身份事实/298 条
  `(qid, run_input_sha256)` 逐字相同与冻结期望比对（见 §2.4/§2.5）。
- B2 停在 build 后属实：`prepare_run_score_executed=false`、`stopped_before_prepare=true`、
  `pending_jobs=0`；本确认件即 C8 代决 §4.5 要求的「身份确认件」，落盘后 prepare 解锁。
- 未发现需修正项；3 个非阻塞证据面建议见 §5/§6。

## 2. 逐项审核（核点 1–6）

### 2.1 新批身份与旧批零触碰 —— 通过

| 项 | 结果 | 依据 |
|---|---|---|
| batch_tag `t-i-298-20261021b2` | 通过 | config 现树实核；verify_identity raw stdout 同值；两臂 marker 同 tag |
| 批根/运行根 `t_i_298_20261021b2_{glm,deepseek}` | 通过 | config diff 仅此两处名称变化；raw stdout `arms` 指向两新批根 |
| 协调目录 `t_i_coordination_t-i-298-20261021b2` | 通过 | config diff；C2 `new_paths_absent=true`（远端读数） |
| 旧根入 immutable | 通过 | config `immutable_batch_names` 含旧两根 + `t_h_s5b_298_20261020`（本地实核）；`mutable()`（ti_operations.py:492-496）对名单内批名一律拒写，prepare/run 入口均先过 `mutable()`/`require_no_stop`（源码走查） |
| 旧批零触碰 | 通过（远端读数） | 证据 `baseline==final` 文件清单摘要 `c3207ac6…`、stop.json `164b9a6b…` 前后同值、`files_newer_than_rebatch_start=0`、旧 case 数 glm=1/deepseek=10 保全。**注意**：`c3207ac6…`/`164b9a6b…` 在本地无更早独立读数可比对（首次镜像即本轮），属实施侧远端自证；内部一致性成立，见 §5-U3 |

### 2.2 锁与批准包 —— 通过

| 项 | 结果 | 依据 |
|---|---|---|
| 新锁 `45a82d25…`，14 件、仅 config 变 | 通过 | pre_state 锁（`0fe47c84…`，与 C6 登记值同）↔ 现树锁程序化 diff：14 件中唯一变化 = `scripts/hpc/ti_arm_config.json`（`8dab7ebc…`→`4feecdc3…`），13/14 逐字不变；新增 `relock_b2_rebatch` 注记块（自述「非新批准、非签名」） |
| 批准 JSON `7e5d1635…` | 通过 | diff 实证：三份 prose 快照 SHA（`0b9b0557…`/`2e45d407…`/`8344265c…`）与现树文件、包内副本、C6 登记值三方同值，原字节未动；`approved_at=2026-10-20T15:49:53Z`、`approval_basis`、`approval_source(_kind)=codex_delegated_cc_shijie`、`no_cap_ack=true` 全部保留；变更仅 = 新增 `b2_rebatch` 块 + `script_lock_sha256` 两处更新为新锁；`b2_rebatch.note` 明示「执行续行、非新批准、未伪填 CC 签名」——**无 CC 本人签署伪造** |
| 内部 sums `31493bc1…` | 通过 | 本地实测 `docs/T_I_APPROVAL_PACKAGE_2026-10-20/SHA256SUMS` 哈希同值，且 5/5 条目全 OK |
| external `75fa7fb8…` | unknown（远端） | 外部清单在 HPC（含 `budget_no_cap.json` 7 件），本地无镜像；证据声明 `hpc_validation_exit_0=true`、`hpc_record_dir_synced=true`，与 C6 结构先例一致；见 §5-U1 |
| 三份 prose 原字节 | 通过 | 同上行；批准包目录副本 `shasum -c` 全 OK |

### 2.3 C3/C5 网络与预检 —— 通过（远端读数为主）

- **netcheck `47042265`**：raw 原件已本地镜像且哈希吻合（`540ef494…`），内容含
  `NETCHECK-PASS` 全行（python 3.11.15 / rdkit 2026.03.5 / v43 import / 磁盘 78% /
  flock / dashscope 401 出口通），时间 `03:02:36Z`；`COMPLETED 0:0` 为 sacct 远端读数。
  前序 `47042109`（03:00:46Z）raw 亦在 `ti_c0_c5` 目录核验 PASS。
- **soak `47041048`**：summary 本地实核 12/12、window 720s、connect 0.000387–0.002244s
  （<3.5s 限）、`SOAK-GREEN`；jsonl/slurm out 哈希 OK。
- **soak 门全链**：更早 r3 窗（job `47036677`，02:01–02:13Z）G1 12/12 + **G2 登录经代理
  3/3**（raw 实核，3 次 401/pass=true）+ G3 直连 401/0.132s + G4 netcheck `47038252` PASS；
  soak3 窗（02:48–03:00Z）+ 直连对照 401/0.177s（03:01:22Z）+ 两次 netcheck 再证。
  两窗合计计算节点 24/24 连续绿。**小缺口**：被引用的 soak3 窗内未重做 G2（登录经代理
  3/3），由 45 分钟前 r3 窗 G2 全绿 + 其后 3 次 netcheck PASS 补强，判非阻塞（§5-U5）。
- **C5 两臂 200**：GLM 21→389 tok / 8.143s；DS 38→22 tok / 1.371s；均 ok=true/status 200；
  **金额 unknown**（诚实登记，未估算）；账目 `operations/preflight_calls.json` seq 3–4、
  带新 batch_tag——远端读数，本地无镜像（§5-U2）。C4 两臂 env/model 核对（forbidden_keys
  空、request_params 两臂一致、未打印值）同为远端读数，与 C6/C0 先例结构一致。

### 2.4 两臂 build —— 通过

- 作业 `47042872`(glm)/`47042874`(deepseek)，submitted `03:09:33Z`，`COMPLETED 0:0`
  （sacct 远端读数），elapsed 01:02:41/01:02:46；两臂 `TI-BUILD-PASS` marker 带各自
  新批根 + 同 tag；`BUILD-GATE-OK: n=298 sha=9f5955d4… entries_with_cosub_labels=298/298`
  raw 已镜像（两文件同哈希，符合逐字相同的预期）。
- `verify-identity` raw：exit 0、stderr 0 字节、timing 04:14:46–04:14:50Z（与 build 完成
  时间顺序自洽）；stdout 含 `gate=TI-BUILD-IDENTITY-PASS`、fingerprint `77cb843b…`、
  manifest `e2e7eb70…`、`n_run_inputs=298`、两臂批根路径。
- **两臂逐字相同的证明力来自门语义**（源码实核，ti_operations.py:1888-1928）：单次
  `verify-identity` 对两臂各跑 `check_build_identity`（比对全部 `identity_expectations`、
  题卷 SHA `9f5955d4…`、n=298、qid 唯一、manifest ref、注册序、`batch_tag==config`），
  再跨臂比对 `batch_tag`/`manifest_sha256`/`build_identity_fingerprint`/
  `identity_facts_sha256`/298 条 `(qid, run_input_sha256)` 元组，任一不同即 raise。
  exit 0 ⇒ 上述全部成立。`build_identity.json` 两臂字节同值（`929207cb…`）为远端读数。

### 2.5 身份语义与指纹变化归因 —— 通过（归因在门语义+代码结构范围成立）

- `code_identity_aggregate_sha256=1aac04da…`（含 TI-F1 停派发补丁，orchestrator
  `a95bb8be…` 不回退）：config `identity_expectations` 本地实核未变，且门在 build 身份
  事实上逐键强制比对 ⇒ 声明由 exit 0 背书。
- 科学源码 `f917762b…`（s5b_compiler.py）/`37c09231…`（evaluation.py）：config
  `scientific_source_sha256` 未变（diff 实核）；`verify_code_sources`（红线「两文件零
  改动」）在 prepare 入口对部署树强制校验（ti_operations.py:1460-1466 源码走查）——
  B2 prepare 将再次机器验证。本地 HEAD 的 `s5b_compiler.py`=`58cf3dc9…` 与冻结部署位
  分叉为 C6 已登记既有状态（锁按部署位计算，本地未改 src），非本轮引入。
- 版本键 compiler-6 / policy-9 / source-4 / retrieval-6 / formnorm-1 / route-f1f4-1 /
  rdkit 2026.03.5：config 实核在位，门逐键比对 ⇒ 在位。
- **旧 `5014fa13…` → 新 `77cb843b…` 仅由 batch_tag 引起**：结构归因成立——
  指纹 = sha256(canonical_json(payload))，payload = schema 常量 + 身份事实（聚合/版本/
  rdkit/formnorm 参数/资产身份）+ `run_inputs`（逐题 `{qid, run_id, substrate_smiles,
  plan.pools, note}`）；`run_id = s5b_run_id(qid, batch_tag)`（冻结位源码实核），新
  run_id 例 `t-i-298-20261021b2-s5br_7bfbfecf689` 仅 tag 段变化；身份事实全部被门锁死
  为冻结期望、题卷 SHA 冻结、config 资产/题卷段零变化 ⇒ 唯一变化输入 = batch_tag。
  **限度**：新旧两批 `build_identity.json` 载荷未做逐字节 diff（新载荷仅存 HPC），
  归因是「门语义 + 冻结代码结构」级而非字节级复算；建议下轮取证镜像两份载荷做
  字节 diff 作后置复核（非阻塞，§5-U4）。

### 2.6 prepare/P2-face（C7）与 run 放行 —— 允许（条件见 §4）

- prepare 期望计数与旧批 C7 实测一致（`docs/T_I_C7_PREPARE_2026-10-21.md` §计数表
  实核）：**核心四项 531 / 242 / 205 / 78；题数面 298 / 151 / 134 / 65；files=298**，
  两臂逐项相同；不符即停（C8 代决 §4.6 原判据，零改动）。
- prepare 为**零模型费**步骤：入口强制 `mutable()`（旧批天然拒写）+
  `check_build_identity` + `verify_code_sources` + `validate_approval_package`（自动重验
  批准包）+ P2-face 探针只读本批 `run_inputs.plan.pools`（零金标、非成绩证明）。
- run 属付费步骤，放行方式与条件见 §3/§4。

## 3. 允许范围

1. **允许**：两臂 C7 prepare + P2-face 探针（自动重验批准包/科学源码/身份门；期望计数
   照 §2.6；不符即停，不自动修）。
2. **允许**：prepare 绿 + 计数全中后，**CC 手动发 run**（smoke2→smoke10→barrier→full
   + `monitor --submit`，TI-F1 停点/barrier/15 分钟巡检阈值**零改动**）；按常设自动循环
   授权由实施链自动发车亦在 C8 代决 §6 范围内，两种方式均合规，以 CC 现场指令为准。
3. **不允许**（本件不授权）：任何写旧批根/旧协调目录/stop.json 的动作；任何冻结面
   （模型/题卷/代码/判分/profile/gate/超时重试）改动；score/封存/发布成绩；push；
   新付费批（超出本预注册范围者）；判据变更（v3/T1′ 类）——后者归 CC/老师。

## 4. 条件（发车与监控）

| # | 条件 |
|---|---|
| 1 | prepare 计数任一项与 531/242/205/78、298/151/134/65、files=298 不符，或两臂不一致 ⇒ 停，回 CC/代决 |
| 2 | prepare 的 `verify_code_sources`/批准包重验任一非 exit 0 ⇒ 停（红线级） |
| 3 | 距最近一次 netcheck/soak 绿（03:02:36Z）超过 2h 才发 smoke ⇒ 先按 C8 代决 §3 G4 口径补快检（计算节点 6/6 或官方 netcheck）再发 |
| 4 | 运行中任一 fatal / `consecutive_outage>=2` / barrier 不过 ⇒ TI-F1 自动停两臂后**保全现场、不自动 resume**；第二次基础设施停跑 = 站点级决策，归 CC |
| 5 | 费用：no-cap 拍板续行、金额 unknown、不估算；预检/smoke/full 调用逐笔入账（`preflight_calls.json` 自 seq 5 起连续、带 batch_tag），账单出后回填复核 |
| 6 | 旧批三不变：immutable 名单不撤、stop.json 不清、旧 case 不移；结果报告并列披露第一次停跑与 B2 新批身份（披露债照 C8 代决 §7.4） |
| 7 | 非阻塞建议：run 前或结果报告前，把 HPC 侧 verify_lock 14/14、approval-package 校验、外部 sums（`75fa7fb8…`）、两臂 build 日志与 `build_identity.json`（`929207cb…`）镜像回证据目录，补齐远端证据面 |

## 5. unknown / 未核清单（诚实登记）

| # | 项 | 状态 |
|---|---|---|
| U1 | HPC external sums `75fa7fb8…`、批准包远端校验 exit 0、record dir 同步 | 远端声明，本地不可复核 |
| U2 | C4/C5 读数（preflight seq 3–4、token/耗时/200）、金额 | 远端声明；金额 unknown 如实 |
| U3 | 旧批 `c3207ac6…`/`164b9a6b…`/case 数 1+10 | 本地无更早独立读数；证据内部 baseline==final 自洽，远端自证 |
| U4 | 新旧 build_identity 载荷字节级 diff | 未做（新载荷仅存 HPC）；归因为结构级，建议后置复核 |
| U5 | soak3 窗内 G2（登录经代理 3/3）未重做 | 由 r3 窗 G2 全绿 + 3 次 netcheck PASS 补强；非阻塞 |
| U6 | 两 build 作业 `COMPLETED 0:0`/elapsed、HPC verify_lock 14/14 | sacct/远端读数，本地未镜像 |
| U7 | `b2_rebatch.json` `created_at_utc=03:12:00Z` 早于其所载 04:14Z 身份读数 | 判读为「重批窗口起点」语义；不影响任何哈希/门结论 |
| U8 | 站点代理根因/长期稳定性 | unknown（站点侧）；由 §4.3/4.4 条件兜底 |

## 6. 仍需 CC/老师批准或追认的事项

1. **批名 deviation 追认**（C8 代决 §7.1）：新批名/新 tag 开新批属操作面 deviation，
   依授权链先行生效，请 CC 追认；正链 Codex 恢复后可复核本确认件。
2. **run 发车时点与方式**（CC 手动 vs 自动循环）：本件给到「允许」，实际发车由 CC 现场定。
3. **费用回填**：账单出来后按 seq 对账复核（no-cap 不免除对账义务）。
4. 若 §4.3 快检或 §4.4 停点触发后的换站/中止决策：归 CC/老师，不在本件范围。

## 7. 与上一轮结论的一致性

本件与 `T_I_C8_STOP_QWEN_DECISION_2026-10-21.md`（B2 代决）无冲突：§4 步骤 1–5 已按
判据完成并留证（soak 门 G1–G4 绿、config 唯一件修改、锁 13/14 不变重算、C2–C5 新窗
重跑、两臂 build + 身份门 PASS + 本确认件）；步骤 6–8（prepare/发车/旧批保全披露）
按 §3/§4 放行。与 C6 重锁报告及其 addendum 的身份口径（`1aac04da…` 取代 prose 字面
`a24700ab…`、锁按部署位计算）完全一致，未静默取舍任何前轮结论。
