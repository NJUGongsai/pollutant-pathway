# HANDOFF — 主窗口 → P2 窗口（2026-10-21 收尾）

> **题域：298 = RHEA 通用酶学 / 已见题（post-hoc）。** 本文是收尾交接，不产生成绩；
> 零新付费 run、零新修复/评审；所有停止点与 SHA 如下。
> 当前主窗口只做收尾，不再开新活；B3 后续决策归 CC。

## 1. B3 停点（最高优先）

| 项 | 值 |
|---|---|
| stop | `~/ppv1_hpc/operations/t_i_coordination_t-i-298-20261021b3/stop.json`，SHA256 `bc71cfa7…`（未改/未删） |
| 原因 | `stage_gate` / `phase=smoke10` / `arm=glm` / `detail=smoke10_completed_run_error:1` / recorded `2026-10-21T08:53:31.904627Z` |
| GLM `47068104` | **FAILED exit 1:0**，Elapsed 00:46:40 |
| DeepSeek `47068110` | **CANCELLED**（被停点 scancel），00:46:37 |
| monitor `47068118` | **CANCELLED**（收尾清理），00:57:03 |
| 失败 qid | `RXNG_56d8303ebd8a99f21974e52e9174f3a453c7e59071d517fc128b0a9bcd3162ec` |
| 失败 case | `status=completed`、`stop_reason=budget_limit`、`model_calls=2`、`retries=1`、usage **全 0**（2 次均无 usage） |
| run_error | `real_model_transport_failure / transport_error` |
| GLM smoke10 | 10/10 completed；9 题干净，1 题上述错误 |
| DeepSeek smoke10 | 10/10 completed，干净 |
| full/score | **未发/未跑** |
| 站点 | 同窗 soak `47041048` 12/12 GREEN；netcheck `47042109` PASS；C5 两臂 200 |

**跨批同题对照（只读）**：T-H r2 completed/calls=1/无错；chain14a completed/calls=2/无错；
chain14b completed/calls=1/无错；chain13 completed/calls=1/曾有同 kind 传输失败但完成。
⇒ **瞬时传输失败，非题目可复现、非站点全断。**

**三选项**：

| 选项 | 做法 | 代价/风险 |
|---|---|---|
| **A. B4 新批（推荐）** | 新 tag/根/协调目录；两臂 build（零模型费，~1h/臂）+ smoke；过 barrier 再 full | ~1–1.5h + smoke 少量；若同题再 transport_error ⇒ 升级网络 RCA，停开 B5 |
| B. 同批原地 resume 该题 | 清 stop、重试该题再 full | 会被 stage gate 再拦（completed_run_error 仍在）；已 2 次调用；改现场违反“不删改” ⇒ **不推荐** |
| C. 接受失败留分母 | 按未命中留 298，继续 full | 需绕过 smoke10 阈值（TI-F1=0），当前授权不允许 |

**本窗口未发起任何付费 run/resume**；B4/停 T-I 由 CC 拍板。
分诊报告：`docs/T_I_B3_STOP_TRIAGE_2026-10-21.md`（SHA `7be2db05…`）；
证据：`docs/review_evidence/ti_b3_stop_triage_2026-10-21/`（`SHA256SUMS` 3 条）。

## 2. P2 两份文书（M1–M3 后定稿，未签字）

| 文书 | 路径 | 最终 SHA256 | 状态 |
|---|---|---|---|
| 预注册 | `docs/T_P2_PREREG_FULL_V2_2026-10-21.md` | `0841201d…c868` | **DRAFT_NOT_SIGNED** |
| 发车书 | `docs/TASK_P2_FULL_V2_LAUNCH_2026-10-21.md` | `276afde2…6caa` | **DRAFT_NOT_EXECUTABLE** |

**M1–M3 改动摘要**：
- **M1**：task §6.2 与附录 A G4 统一为 `scripts/hpc/sbatch_p2_netcheck.sh`；写死
  “netcheck 是唯一允许直接 sbatch 的脚本，其余走 `p2_operations.py launch`”。
- **M2**：两文书落 `arm_a_definition = v1card`；注明这是设计修正/新增，冻结设计原 A
  （无证据字节兼容回退）保留为历史对照；provenance 逐字
  `qwen3.8max 代 Codex 代 CC 确认（CC 2026-10-21 指示，CC 后置复核）`，不伪填 CC。
- **M3**：发车前冻结 F2raw+规则（`p2_family_f2raw.json` 记 SHA）；A 臂评分后冻结 F1；
  F2=F2raw−F1、F3=补集按已写死规则确定性生成；最终记 `p2_family_partition.json` SHA。
- 四选择：A=v1card；两臂共用 v2 prompt+披露；克隆 `p2_operations`；seed build+copy
  （不复制 orchestration/gate/cases/状态文件；禁一臂 seed 一臂独立）。

**待同步 SHA 清单**（因 M1–M3 变更）：
1. 预注册 `0841201d…`、发车书 `276afde2…`（已在上表）；
2. 复审请求 `docs/P2_FULL_V2_QWEN_REREVIEW_REQUEST_2026-10-21.md` = `3b38ecfa…`（已更新）；
3. M1–M3 证据 `docs/review_evidence/p2_m1m3_fix_2026-10-21/SHA256SUMS` = `ece9079b…`；
4. **未来批准包/脚本锁/arm_config 必须绑定上面新 SHA**（尚未创建）；
5. 历史 qwen 确认报告 `docs/P2_FULL_V2_QWEN_CONFIRM_2026-10-21.md` 引用旧 SHA
   （`8ad5473b…`/`d47dae5d…`），作为历史件**不改写**；
6. 本交接文档 `docs/HANDOFF_MAIN_TO_P2_2026-10-21.md`（写后计 SHA）。

**仍缺付费前置（P2）**：T-I 模型、预注册签字（须显式落 A=v1card）、v2 化学复审条件闭合、
付费/HPC 授权+`no_cap_ack`、v1card 实现复审、P2 操作链/脚本锁、代码聚合身份/RDKit 对齐、
A/B 同 prompt token 披露件、站点 soak、Codex 正链复核。

**化学状态**：R4=`PASS_WITH_CONDITIONS`（C1–C4 未闭 + 58/146 unknown）；P2 v2 化学复审=
`PASS_WITH_CONDITIONS / 未放行`（P1–P7 未闭）；R4 不能充抵 P2 化学复审。**不得按已过推进。**

## 3. P1-B 预注册确认

- 报告：`docs/T_P1B_PREREG_QWEN_CONFIRM_2026-10-21.md`（SHA `c94e18e7…`）。
- 总裁定：**需修正后放行——仅限“进入签字准备”；化学条件未闭合前付费批 NO-GO。**
- 已并入 CC 纠正：R4 全文 `PASS_WITH_CONDITIONS`，不写“已过”；4 条条件在合同中命中 0，
  新增 M8；P1-B“改 edits 提示面”需独立化学规则级评审（M9）；设计稿 line 378“R4 已过”
  与纠正冲突，待改（本窗口不改）。
- 预注册草案 SHA `a9d6183e…`；M1–M9/工具链 M6（无 P1-B 发车工具链、ti_operations 四文书键集
  不兼容）/11 项付费前置未闭。**本窗口未批付费、未跑模型。**

## 4. Top3 levers（已完成）

- 合并报告（已提交 `966bc56`）：`docs/T_H_TOP3_LEVERS_REPORT_2026-10-21.md`（SHA `2f8e96b7…`）。
- 三表：`docs/T_H_TEACHER_LEVER1_RANK_TABLE_2026-10-21.md`、
  `docs/T_H_TEACHER_LEVER2_REMAP_AUDIT_2026-10-21.md`、
  `docs/T_H_TEACHER_LEVER3_PARTIAL_GAP_2026-10-21.md`（均在 `966bc56`）。
- 外部评审稿（未跟踪）：`docs/T_H_TOP3_LEVERS_CONCLUSIONS_FOR_REVIEW_2026-10-21.md`。
- 重复件（未跟踪、非权威）：`docs/T_H_TEACHER_LEVER3_PARTIAL_TABLE_2026-10-21.md`；
  以提交的 `..._PARTIAL_GAP` + 证据 `table_53.md` 为准。
- 结论：杠杆1 37/37 model_ranking ⇒ 不立 chain15；杠杆2 post_compile 100%、no_alignment 28/50；
  杠杆3 可修 44/待裁定 5/放弃 4。**无需再做合并。**

## 5. C1–C4 状态

**化学条件（R4/P2）**：
- C1 `stereo_only` 粒度解释：**未闭合**
- C2 `isomeric_unspecified` 桶含同位素/CX 扩展差：**未闭合**
- C3 空参与物不读 `participant_list_status=partial`：**未闭合**
- C4 互变/质子化未归一写入 `does_not_prove`：**未闭合**
- 附：58 `stereo_only`/146 `principal_absent` 化学真伪 unknown。

**T-I B3 的 C1–C4（工程门，B3 内均绿）**：
- C1 部署/锁：B3 锁 `c555eb03…`、批准包 `84babafa…`、HPC 14/14 核过；
- C2 环境：两 env 600、新路径、磁盘/flock 通过；
- C3 netcheck：`47042109` COMPLETED 0:0 + NETCHECK-PASS；
- C4 请求参数：两臂模型/base 同值、REQUEST_PARAMS 同值、无禁用键。
- C5 预检两臂 200；C6 build/身份 `f7fc8c83…` 两臂同；C7 prepare/P2-face 531/242/205/78、
  298/151/134/65；**C8 停在 smoke10**。

## 6. 未跟踪/易失件清单

**未跟踪、需保留**：
- `docs/T_I_B3_STOP_TRIAGE_2026-10-21.md` + `docs/review_evidence/ti_b3_stop_triage_2026-10-21/`
- `docs/T_P2_PREREG_FULL_V2_2026-10-21.md`、`docs/TASK_P2_FULL_V2_LAUNCH_2026-10-21.md`、
  `docs/P2_FULL_V2_QWEN_REREVIEW_REQUEST_2026-10-21.md`、`docs/P2_FULL_V2_QWEN_CONFIRM_2026-10-21.md`、
  `docs/P2_CC_DECISION_FULL_V2_2026-10-21.md`、`docs/review_evidence/p2_m1m3_fix_2026-10-21/`
- `docs/T_P1B_PREREG_FEEDBACK_2026-10-21.md`、`docs/T_P1B_PREREG_QWEN_CONFIRM_2026-10-21.md`
- `docs/T_H_TOP3_LEVERS_CONCLUSIONS_FOR_REVIEW_2026-10-21.md`
- `docs/T_H_TEACHER_LEVER3_PARTIAL_TABLE_2026-10-21.md`（重复件，可丢；以提交 GAP 为准）

**已跟踪但有未提交修改**：
- `docs/T_H_P0B_D6_IMPL_2026-10-20.md`（§13 已改为 PASS_WITH_CONDITIONS；未提交）

**工作树（不碰）**：
- `/private/tmp/dependingv43_p2_v1card`、`/private/tmp/dependingv43_p2_ops`、
  `/private/tmp/dependingv43_p2_chemfix`、`/private/tmp/qwen_review_p2`（CC 指定本窗口不碰）
- `/tmp/dependingv43_p0b`、`/tmp/dependingv43_p1b`、`/tmp/dependingv43_p2`（历史 worktree）

**易失/可丢**：`/tmp/t_h_p0_r2`、`/tmp/qwen_p1b_prereg_check`、`/tmp/codex_*`、`/tmp/th_*`、
`/tmp/ocagent-*`、`/tmp/c8_soak2_auto.sh` 等；如需复现再留，否则可清理。
**不要删**：HPC 批根 B2/20261020/B3、stop.json、封存 T-H 批根、上述已跟踪/未跟踪报告。

**Git**：HEAD `966bc56`；`M docs/T_H_P0B_D6_IMPL_2026-10-20.md`；未 push。

## 7. 子代理停止声明与自检

**子代理**（本窗口发起）：
- B3 build/prepare 代理：completed；
- B3 run 监控代理：stopped（其 monitor 作业 `47068118` 已 CANCELLED）；
- P2 M1–M3 修正代理：completed；
- P1-B 预注册确认 QwenReviewer：completed；
- P2 完整 v2 确认 QwenReviewer：completed；
- P1-B A 实现复审 QwenReviewer：completed；
- 老师三杠杆 1/2/3 代理：completed；
- 合并代理：stopped（避免与已提交汇总重复）。
**当前无活动子代理；squeue 空；无 monitor 在跑。**

**停工前自检**：
- ☑ stop.json 未改写/删除（B3 `bc71cfa7…`；B2 `fb1d1627…`；20261020 `164b9a6b…`）
- ☑ 无新的付费调用记录（B3 停后未发 run/resume；队列空）
- ☑ monitor 已停（`47068118` CANCELLED）
- ☑ P2 预注册仍 `DRAFT_NOT_SIGNED`；发车书 `DRAFT_NOT_EXECUTABLE`
- ☑ 报告 SHA 可在证据目录核对（`ti_b3_stop_triage.../SHA256SUMS`、`p2_m1m3_fix.../SHA256SUMS`）
- ☑ 工作树/易失件清单已写（§6）
- ☑ 交接文档已落盘（本文件）