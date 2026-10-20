# T-H r2 操作件闭合复验（2026-10-20，主窗口独立复验）

**结论：复核报告 §4 点名的「score 未接 V3 / 无并列产物」缺口已闭合——操作链随 `04b94cb` 提交，
附 `SCRIPT_LOCK` sha 清单与 12 组合成验收；本窗口另做独立复验（18 项合成正负控+语法检查+远端
sha 对账），全绿，判定=可用。本复验不替代外部复核，也不认证真实批结果。**

题域标签：**298 = RHEA 通用酶学 / 已见题（post-hoc）**；合成门 ≠ 成绩。

## 1. 背景与时间线

`docs/T_H_DEPLOY_FIX2_REVIEW_2026-10-20.md` §4 登记两项操作链缺口：
① `sbatch_th_score.sh` 当时只跑 v1/v2，未接 V3 档 A 披露；
② 直接追加 v3 会覆盖根部 v2 产物。
操作链随后于 09:45–09:49 闭合，并在 **`04b94cb`**（09:49:06）提交，随提交的权威件：
`docs/T_H_R2_OPERATIONS_2026-10-20.md`（自包含命令链）与
`docs/T_H_R2_SCRIPT_LOCK_2026-10-20.json`（8 操作/依赖文件+2 科学源码 sha 锁）。
提交信息登记：初轮 12 组合成验收 + 独立短审三处修正闭合。

本窗口在未先看到 `04b94cb` 的情况下独立做了复验（18 项），事后与 `SCRIPT_LOCK` 对账：
**四件操作文件 sha 逐字一致**。本文件记录复验本身，不重复登记原提交已载内容。

## 2. 闭合件与 sha（与 SCRIPT_LOCK 对账）

| 文件 | sha256 | 作用 |
|---|---|---|
| `scripts/hpc/sbatch_th_build.sh` | `9c0180d6…` | r2 build；`prebuild` 拒非空批根；build-gate |
| `scripts/hpc/sbatch_th_run.sh` | `70054091…` | smoke2→smoke10→full 三段；每段 `phase` 门 + run-gate |
| `scripts/hpc/sbatch_th_score.sh` | `36177599…` | 全 qid 终态门 → `th_operations score` 三版判分 |
| `scripts/hpc/th_operations.py` | `4f2fe987…` | phase 零 CX 门 / probe / prepare / score / launch |

远端 `v43cTH/scripts/hpc/` 四件 sha 与本地**逐字一致**（2026-10-20 实测），即 HPC 侧已是闭合版。
完整 sha 清单见 [scripts_sha256.txt](review_evidence/t_h_v3_closure_2026-10-20/scripts_sha256.txt)。

## 3. 闭合内容（读码确认）

1. **三版并列判分**（`score_all`）：`v1`→保存 `.v1`；`v3`→保存 `.v3`；`v2`→保存 `.v2` 并保留为
   根 headline（`metrics.json/report.md/report_plain.md` 三件）。互不覆盖。
2. **V3 披露档 fail-closed 断言**：`tier=disclosure_only`、`strict_promotion=false`、
   `hit_at_1_effect=none`、`tautomer_promoted_nodes=[]` 四项任一不符 ⇒ 保留三版现场、拒封存。
3. **V3/V2 稳定科学字段对账**：13 个 `STABLE_FIELDS` 任一差异 ⇒ 写 `th_score_difference.json` 并停。
4. **幂等与防篡改**：`th_score_complete.json` 记录全部产物 sha；二跑校验，产物被改 ⇒ 停报。
5. **零 CX 硬停**（`phase_guard`）：失败件先保全完整现场（case/run/gate/日志）再判定；命中
   `unregistered_cx_class` ⇒ 登记 `hard_stop_cx` 并立即停报；`identity/integrity/schema/budget/…`
   类失败不重试；仅 recovery 家族允许同题同参重试**一次**。
6. **提交器幂等**（`launch`）：提交前落 `pending_submission` 意图；无可靠 job_id 不盲重投；
   同阶段重投上限一次；build 前拒非空批根；run 前核五件前置（含 `p2_face_measure.json`）。
7. **批准件快照绑定**（`prepare`）：先核 `build_identity.json`，再逐份校验批准文本 sha，
   不一致即停（不改写审批）。HPC 批准快照目录四件 sha 实测匹配（含 TASK 原批准文本
   `b3984bbe…`＝`abbfa39` 版本，非当前带事故注记版本）。

## 4. 本窗口独立验证

环境：本地 `v44/.venv` Python 3.11.16 / RDKit 2026.03.6；全部产物写 /tmp 临时根；
不触真批根、不调模型、不联网。

| 验证 | 结果 |
|---|---|
| `bash -n` × 4 脚本 | 全过 |
| `py_compile` `th_operations.py` | 过 |
| 合成正负控 18 项 | **18 passed / 0 failed** |

18 项覆盖：三版并列产物齐全、根 headline=v2、V3 披露块落盘、receipt 字段、幂等二跑、
篡改产物拒、坏披露档拒、稳定字段漂移拒（含差异文件落盘）、clean 段 zero_cx 通过、
CX 硬停+登记+现场保全、identity 类不触发重试、recovery 家族重试恰好一次并恢复。
脚本与原样输出见 [verify_script.py](review_evidence/t_h_v3_closure_2026-10-20/verify_script.py) /
[verify_output.txt](review_evidence/t_h_v3_closure_2026-10-20/verify_output.txt)。

## 5. 残余风险（如实登记）

1. 闭合件的外部复核=提交信息所载「独立短审三处修正」；本窗口复验是额外的合成负控，
   两者均不构成真实批性能认证。
2. 真实 21 拒/529 过、池效应与成绩一律以 r2 批根实测为准。
3. 本文件与证据目录按评审侧惯例未跟踪；是否入库归 CC 挂账。