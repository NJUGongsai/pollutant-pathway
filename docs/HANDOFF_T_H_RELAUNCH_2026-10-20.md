# HANDOFF — T-H 修复后重启（2026-10-20 晨，交新窗口零上下文接手）

> **2026-10-20 本轮接续状态**：两源码 delta 已有限范围复核通过并提交 `c360e74`（104 项独立合成回归）；
> T-H 操作链已补齐并提交 `04b94cb`：V3 三版保留、零 CX／恢复一次／二败停、提交前意图和作业号防重复；8 件锁定脚本与原批准四件已部署核 SHA。
> **接续改用 `docs/T_H_R2_OPERATIONS_2026-10-20.md` 的自包含命令与 `docs/T_H_R2_SCRIPT_LOCK_2026-10-20.json` SHA 清单**。
> 远端 netcheck `46954668` 已 COMPLETED／Exit0，compiler-6／v3 available 已独立核；**r2 build `46954982` 已提交，2026-10-20 09:51:47（北京时间）实测 RUNNING（wzhcnormal/f02r3n02）**，尚未完成，未 run/score。
> 接续 heartbeat=`t-h-r2`（主会话已创建，15 分钟查状态、不变静默）；opsstate=`/work/home/aclhl3hbth/ppv1_hpc/operations/t_h_s5b_298_20261020r2.json`；执行与下一步见 `docs/T_H_RELAUNCH_EXECUTION_2026-10-20.md` §7。
> 下方“源码未提交／待 CC 复核”及旧双版 score 步骤为本窗口此前快照，当前以本段和操作补充为准；原审批和旧事故批不改。
> **2026-10-20 终态**：r2 全链完成——build `46954982` / run `46958084` / score `46969374` 均 COMPLETED 0:0，298/298、failed=0、zero_cx=true；
> 结果 v1 hit@1 **84（28.19%）** / v2（headline）**89（29.87%）**，未达预注册 35–40%，<32% 强制逐桶回查已完成（对 chain13 v2 净 +2）；
> 批根已封存（`th_sealed.json` sha `424f81ad…883e9a`，目录 555/文件 444，零可写；runs 根不封）；结果见 `docs/T_H_RESULT_2026-10-20.md`（+`_PLAIN`）；**未 push**。

> 写给：下一个窗口。本窗口按 CC 指令完成 T-H 发车→冒烟事故→修复（compiler-6 身份自洽门），
> **修复待 CC 复核**；复核放行后新窗口**见放行即自动续跑**发车链（CC 2026-10-20 拍板）。
> 读法：§1 一句话 → §2 活状态 → §3 续跑步骤（命令级）→ §4 未提交 delta → §5 HPC 事实 →
> §6 挂账 → §7 机坑 → §8 关键文件。

## 1. 一句话

**T-H（298 修复批）万事俱备，卡在最后一步**：两处部署修复（compiler-6 门 + v3 指纹平台化）
在工作树未提交、等 CC 复核（请求稿已备）——**见 `docs/T_H_DEPLOY_FIX2_REVIEW_2026-10-20.md`
终判定=放行 ⇒ 本移交书 §3 自动续跑**；无该文件或需修正 ⇒ 停下找 CC。

## 2. 活状态表

| # | 事项 | 状态 |
|---|---|---|
| 1 | D1.2+E1a+E1b 三单 | ✅ 复审全放行+已提交（`d758845` 耦合/`ba9b3f2` 文档/`616dad8` P3 小件/`d4cc871` 状态/`abbfa39` 发车物） |
| 2 | T-H 预注册+付费+HPC | ✅ **CC 已签字**（2026-10-20：预注册定稿+付费/HPC 指令；no-cap 沿 chain13/14 先例） |
| 3 | T-H 发车（第一次） | ⚠️ **冒烟事故停批**：netcheck/build 全过；run 在 smoke10 抓到 CX 身份守卫杀题（21/298 题 0 调用即死）⇒ 主动 scancel（费用仅 10 次请求）。档案 `docs/T_H_SMOKE_INCIDENT_2026-10-20.md` |
| 4 | 修复（CC 拍板 A=编译层自洽门） | ✅ 实现+验证全绿（定向 69/全量 2299-0/真面分判 21 拒 529 过零误伤）；**未提交**（§4） |
| 5 | 修复复核 | ✅ **复核已放行**（`docs/T_H_DEPLOY_FIX2_REVIEW_2026-10-20.md`） |
| 6 | T-H 重启（r2 批根） | ✅ **r2 完成**：build/run/score 三作业 COMPLETED，298/298、零 CX；已封存；结果见 `docs/T_H_RESULT_2026-10-20.md` |

## 3. 续跑步骤（见放行后照此执行，命令级）

**本文件 §3 已于 2026-10-20 15:40 执行完毕，保留为历史操作底稿。**

**前置自检**：`docs/T_H_DEPLOY_FIX2_REVIEW_2026-10-20.md` 存在且终判定=**放行**（若「需修正」
⇒ 按其清单修完再回到本节；无文件 ⇒ 停，提醒 CC 复核）。

1. **提交两处 delta**（一个提交；复审放行才提交纪律已满足）：
   `git add src/pathway_v43/pollutant/s5b_compiler.py src/pathway_v43/pollutant/evaluation.py
   tests/test_ppv1_s5b_product_identity_gate.py tests/test_ppv1_s5b_template_remap.py
   tests/test_ppv1_s5b_hit50_v4b.py tests/test_ppv1_s5b_hit50_w1.py tests/test_ppv1_s5b_pool_lineage.py`
   ——提交信息引事故档案+复核报告；**不 push**（push 时机=CC 挂账）。
   提交前复核 sha：`s5b_compiler.py=f917762b…`、`evaluation.py=37c09231…`（与复核报告读时锁一致；
   若 CC 回修动过文件 ⇒ sha 以届时工作树为准并登记差异）。
2. **重部署 HPC（两文件 scp）**：
   `KEY=/Volumes/CC/Enzyme_Agent/aclhl3hbth_wuzh02.hpccube.com_RsaKeyExpireTime_2026-11-30_10-12-36.txt`
   （若 Permission denied 先 `chmod 600 "$KEY"`）；
   `scp -i "$KEY" -P 65091 src/pathway_v43/pollutant/{s5b_compiler.py,evaluation.py}
   aclhl3hbth@wuzh02.hpccube.com:/work/home/aclhl3hbth/EnzymeAgent/v43cTH/src/pathway_v43/pollutant/`
   ；HPC 侧 `shasum` 复核两文件；跑 v3 冒烟（evaluation 那份已在，重点核 compiler）：
   `~/ppv1_hpc/venv_v44run/bin/python -c "import sys; sys.path.insert(0,'/work/home/aclhl3hbth/EnzymeAgent/v43cTH/src');
   from pathway_v43.pollutant.s5b_compiler import S5B_COMPILER_VERSION; print(S5B_COMPILER_VERSION)"` ⇒ 须 `s5b-compiler-6`。
3. **重建批根 r2**（池成员变了必须重 build；旧根 `t_h_s5b_298_20261020` 原封=事故史）：
   `ssh … 'cd ~/EnzymeAgent/v43cTH && WS=$HOME/ppv1_hpc BATCH_ROOT=$WS/batch/t_h_s5b_298_20261020r2
   RUNS_ROOT=$WS/runs/t_h_s5b_298_20261020r2 BATCH_TAG=t-h-s5b-298-20261020r2
   sbatch --parsable scripts/hpc/sbatch_th_build.sh'`（~66 分钟；日志 `th_build_*.out` 在 v43cTH 根；
   完成判据 `TH-BUILD-PASS`）。
4. **批根三件套**（旧根复制或按事故档案 §4 的格式重写，`budget_no_cap.json` 必须含
   `budget_mode="no_monetary_cap_user_decision"`+marker 与日期绑定）：
   `preregistration_approval.json`（approval_status=preregistration_confirmed，白名单三值之一）
   / `budget_no_cap.json` / `p2_face_probe.py` 重跑 ⇒ `p2_face_measure.json`（**门后预期变化：
   remap-applied 261→240、含新增原子 222→201**——21 件被拒 spec 出池；以 r2 实测为准披露）。
   版本核：r2 manifest 诊断须见 `pool_policy_version=s5b-pool-policy-9`、`compiler_version=s5b-compiler-6`。
5. **run**：`ssh … 'cd ~/EnzymeAgent/v43cTH && WS=$HOME/ppv1_hpc
   BATCH_ROOT=$WS/batch/t_h_s5b_298_20261020r2 RUNS_ROOT=$WS/runs/t_h_s5b_298_20261020r2
   sbatch --parsable scripts/hpc/sbatch_th_run.sh'`（自带 smoke2→smoke10→full 三段；单 job，
   workers 8/gate 4470/RPM 200/TPM 3M；GLM-5.3-Flash）。**冒烟判据：smoke 段 0 件
   `unregistered_cx_class`**（门生效的直接证据；若再现 ⇒ 停，门有漏，回 CC）。
6. **score**：全 qid 终态后 `BATCH_ROOT/RUNS_ROOT 同 r2 sbatch --parsable scripts/hpc/sbatch_th_score.sh`
   （双口径 v1 敏感性+v2 headline）。
7. **回收+对账**：批根 metrics/report/batch_report 拉回 `reports/ppv1_s5b/t_h_2026-10-20/`（已建
   record/）；按 `docs/T_H_LAUNCH_TASK_2026-10-20.md` §5 对账清单出交付（双口径表/修复兑现表
   （T-E 三层分开、20/9=上限口径）/P2 披露（r2 分母+strict 转化率）/human_review 2503 行义务/
   费用登记/<32% 桶回查）；r2 批根置只读。
8. **回传**：出数后大白话+技术版交 CC；主 TODO 行 8 刷新；push 时机归 CC。

**急停条件**（沿任务书 §4）：smoke 再现 CX 杀题/费用异常/连续失败/范围外要求 ⇒ 停报 CC。

## 4. 未提交 delta（工作树，等放行后按 §3.1 提交）

| 文件 | 已审锁定 → 现值 | 内容 |
|---|---|---|
| `src/pathway_v43/pollutant/s5b_compiler.py` | `4cf61a8a…`→`f917762b…` | compiler-5→6：包装层产物身份自洽门+`S5B_PRODUCT_IDENTITY_GATE_VERSION` |
| `src/pathway_v43/pollutant/evaluation.py` | `a7e5ecfd…`→`37c09231…` | v3 transforms 指纹平台化（mac/conda/pip-linux 候选；environment 零增删） |
| `tests/test_ppv1_s5b_product_identity_gate.py` | 新（`7a99fab5…`） | 6 测 |
| `tests/test_ppv1_s5b_{template_remap,hit50_v4b,hit50_w1,pool_lineage}.py` | 版本断言 5→6 同步 | — |

验证账：定向 69 全绿；全量 not-slow **2299/0/16**（基线 2293+6 零翻转）；真面分判 21 拒/529 过；
evaluation 平台化本地 35 测绿+四臂指纹与常量逐字同+HPC available=True。

## 5. HPC 事实速查（乌镇 wuzh02）

- SSH：`ssh -i "$KEY" -p 65091 aclhl3hbth@wuzh02.hpccube.com`；分区 **wzhcnormal**（全部历史作业同）；
- python=`~/ppv1_hpc/venv_v44run/bin/python`（3.11.15/rdkit **2026.03.5**/langgraph）；系统 python 的
  rdkit 是 2024.03.2 勿用；
- 代码树 `~/EnzymeAgent/v43cTH`（tarball 部署自 `abbfa39`+evaluation.py 热修；`._*` 已清）；
  T-H 脚本族 `v43cTH/scripts/hpc/sbatch_th_{netcheck,build,run,score}.sh + th_run_wrapper.py`
  （CODE 默认 v43cTH；BATCH_ROOT/RUNS_ROOT/BATCH_TAG/WS/PY 均可环境变量覆盖）；
- 题卷 `~/ppv1_hpc/questions.jsonl`（sha `9f5955d4…`，298 行）；凭证 `~/ppv1_hpc/env/llm.env`
  （GLM-5.3-Flash；envcheck 报 configured=false 是老自检毛病，实跑正常）；
- 旧批根 `~/ppv1_hpc/batch/t_h_s5b_298_20261020`（**只读留档**：cases 6 件、gate 10 请求、
  `degenerate_fragment_face_v2.json` 21 题名单、`p2_face_measure.json`、批准件三件套）；
- v3 引擎代码根 `~/EnzymeAgent/dependingv3`；venv 的 rdkit 实体在
  `~/anaconda3/envs/rxn/lib/python3.11/site-packages/rdkit`（C++ 库在 `envs/rxn/lib/`）。

## 6. 挂账（不自动处置）

| # | 事项 | 时机 |
|---|---|---|
| 1 | push 时机：**12 个未推提交**（d9cee97…abbfa39 + 本轮文档提交）+§4 delta 提交后 +1 | T-H 发车或 CC 指令（origin/v4.3、main 不动、密钥扫描门先行） |
| 2 | T-H 出数对账交付（§3.8） | score 后 |
| 3 | 两件 reject→compiled 翻转化学复核链（诊断包含）+P2-CHEM-FORWARD 后续轮（B=判据对账） | T-H 后 |
| 4 | T-I（模型配对三臂） | T-H 后（预注册先于付费，归 CC） |
| 5 | 正链 Codex 额度恢复后对代审轮次的复核确认 | 额度窗口 |
| 6 | P3-MONITOR：prediction_recovery 家族 flake 再现即留现场根因 | 持续 |

## 7. 机坑合集（本窗口新增；历史坑见 `docs/HANDOFF_TG_NEXT_PHASE_2026-10-19.md` §7）

1. **ZCode 子代理 token-plan 配额会耗尽**（`Your token-plan quota has been exhausted`）——派不出
   代审子代理 ⇒ 备选=CC 亲验或 CC 手动搬运（本窗口即此态）；
2. Codex 正常通道额度 ~5h 窗口，本轮两轮即耗尽；评审一律走 CC 搬运；
3. tar 从外置盘打包会带 `._*` AppleDouble 文件 ⇒ HPC 解包后 `find . -name "._*" -delete`；
4. HPC 钥匙在 `/Volumes/CC/Enzyme_Agent/`（非 Downloads），权限必须 600；
5. `budget_no_cap.json` 必须含 `budget_mode="no_monetary_cap_user_decision"` 且
   `marker=no_cap_marker_string(日期)`（chain14 早期文件无此键会 fail-closed）；
6. **worker decide 段在模型调用前对全部池 spec 构建产物态**——池里任一 spec 产物组分身份不可
   表示 ⇒ 整题 0 调用死（本事故根因；门已堵）；
7. `[N+]` 游离 → `|0|` 未登记 CX 块（拒）；`[O-]` → `|^1:0|` 登记（放行）——分判时别混；
8. 默认 llm timeout **3600s/调用且超时不重试**——慢调用可挂近 1h（043656 实例 ~50min 自愈），
   别急杀；
9. sbatch 作业日志写在**提交 cwd**（v43cTH 根）`th_*.out`；
10. 事故诊断法（可复用）：失败 case 的 error 一行 + 本地直调 `start_ppv1_run` 拿全栈
    （run_input scp 回来即可，引擎版本差不碍 CX 守卫复现）。

## 8. 关键文件索引

- 事故+修复档案：`docs/T_H_SMOKE_INCIDENT_2026-10-20.md`（本轮唯一权威叙述）
- 复核请求/放行位：`docs/T_H_DEPLOY_FIX2_REVIEW_REQUEST_2026-10-20.md` → `docs/T_H_DEPLOY_FIX2_REVIEW_2026-10-20.md`
- 发车任务书：`docs/T_H_LAUNCH_TASK_2026-10-20.md`（§5 对账清单；批根/命名/机坑）
- 预注册骨架：`docs/T_H_LAUNCH_PREP_2026-10-20.md`（§2 判定线 35–40%/<32% 回查）
- P2 对账草案：`docs/T_H_P2_CHEM_FORWARD_DRAFT_2026-10-20.md`（A=披露已认可）
- 三单复审报告（放行）：`docs/T_G_D1_REMAP_CODEX_REREVIEW_2026-10-19.md`、
  `docs/T_DE_E1{A,B}_CODEX_REVIEW_2026-10-19.md`
- 主 TODO：`docs/TASK_GONGSAI_LINE_TODO_2026-10-16.md` 行 7/8
- 本地批件副本：`reports/ppv1_s5b/t_h_2026-10-20/record/`（批准件三件套模板）；
  `/tmp/th_run_inputs/`（旧根 298 run_inputs，事故分析用，易失可弃）

## 9. 回传义务（新窗口）

- 见放行即续跑（CC 2026-10-20 拍板）；每完成一程刷本文件 §2 + 主 TODO 行 8；
- smoke 判据（0 件 CX 杀题）不过 ⇒ 停报；出数后按 §3.8 交付；
- 预注册/费用/金标/推远端红线不变，归 CC。
