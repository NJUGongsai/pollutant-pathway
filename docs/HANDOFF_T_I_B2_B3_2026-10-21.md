# HANDOFF — T-I：B2 停点、B3 build 中（2026-10-21 15:20 CST）

> **题域标签：[298 域] = 298 / RHEA 通用酶学 / 已见题（post-hoc）。** 本文全部数字只在该题域成立，
> 与 dev（B1 环境路径中间步骤）双向不外推。
>
> **用途：换窗口零上下文接手。** 初稿 **2026-10-21 14:36 CST（06:36Z）**；
> **新窗口接手进度补记 15:20 CST（07:20Z）**。B3 准备子代理 14:26 启动，仍在跑；
> B3 已进入两臂 build。**先核 §3 再动手，别重复派工。**

## 0. 一句话

T-I 的站点代理已恢复（10:13 soak 12/12、10:16 netcheck PASS）；B2 新批也已完成
build / 身份 / prepare，但 **14:15 发 run 时被 13:03 一次越权直接 sbatch 留下的 run 目录卡住**，
GLM smoke2 两题报 `run_already_exists`，代码写成 `recovery_second_failure` 停点。
**不是代理、不是模型、不是科学代码失败。** 主窗口已改走 **B3 新批**，14:26 派了子代理只做
零/低费准备（不 run）；现在 B3 两臂 build 在跑（14:47 起），B2 与旧批现场都保全。
下一步是等 B3 build/身份/prepare 和报告，核完再由 CC 拍板是否发 B3 run（付费）。

## 1. 本窗口做了什么

| 事 | 结果 |
|---|---|
| 诊断“站点代理” | 是 HPC 账号 `~/.bashrc` 里的代理 `10.15.2.115:3000`，不是 ZCode、不是 Clash 7890、不是模型 API |
| 现场复核 | 09:41 CST 登录节点 3/3、计算节点 `a04r2n14` 3/3 可达 |
| 正规 soak G1–G3 | G1 **12/12**、窗口 720s；G2 **3/3**；G3 直连 401/0.132s；作业 `47036677`，节点 `a02r2n14` |
| G4 官方 netcheck | 作业 `47038252`，`COMPLETED 0:0`，`NETCHECK-PASS` |
| 证据 | `docs/review_evidence/ti_b2_soak_2026-10-21/`，SHA256SUMS **9/9 OK** |
| 会话 | 本 OpenCode 会话已改名；ID 见 §7 |

> G4 是趁 30 分钟窗口关前补的官方口径；G1–G3 是自建探针，两者不互相替代。

## 2. T-I B2：停在哪、为什么停

### 2.1 时间线（2026-10-21，CST）

| 时间 | 事件 |
|---|---|
| 05:46 / 08:07 | 旧批两次 soak 因代理故障停（已记录） |
| 10:13–10:16 | 代理恢复；G1–G4 全绿 |
| 11:02:36 | 最后一次官方 netcheck 绿（`47042265`） |
| 11:09 | B2 build 作业 `47042872`（GLM）/ `47042874`（DeepSeek） |
| 12:33 | B2 身份确认件落盘（qwen3.8max 代 Codex 复审） |
| 12:35–12:40 | B2 两臂 prepare + P2-face 探针完成（零模型费） |
| **13:03** | **一次越权子代理直接 `sbatch sbatch_ti_run.sh`**：DeepSeek `47054286`、GLM `47054336`；GLM 13:04:15 被 uid 18950 取消 |
| 13:08 / 13:11 | DeepSeek smoke2 / smoke10 回执 PASS（12 次真实调用） |
| **14:15:20** | 正规 `ti_operations launch --phase run`：GLM `47059065`、DeepSeek `47059067`、monitor `47059069` |
| **14:15:58** | GLM smoke2 两题 `run_already_exists` → 写 `stop.json`（`recovery_second_failure`），DeepSeek 被 scancel |
| 14:16:15 | 13:03 的 DeepSeek 老作业在 barrier 处失败退出 |

### 2.2 根因（重要，别误读）

- **直接触发**：14:15 的正规 launch 要求 GLM 跑 smoke2 两题；这两个 run 目录在 13:03 已被
  越权直接 sbatch 创建，里面**只有 `driver.lock`、没有可恢复状态**，`ti_run` 拒绝复用，
  报 `run_already_exists`。
- 失败 qid：
  `RXNG_043656495555eab986eb1f00c64dcfc33a9b9d44612a13e7c135579da51d46af`、
  `RXNG_103c84009b441fd0510268b3f8fe1b522ed9a4ce12d4210bcc90e3eedfcbe4e7`；
  残留 run id：`...54d2b2ff245`、`...01f057160fd`。
- `stop.json` 的 `reason: recovery_second_failure` 是 TI-F1 的通用“第二次恢复失败”标签，
  **不是**“代理又坏了”。现场 case 明确是 `failure_kind=run_already_exists`。
- 13:03 的直接 sbatch **不在 `ti_operations` history 里**（history 只有 build 47042872/74
  和 14:15 的 run 47059065/67），说明它绕过了正规 launch。主窗口已在 B3 任务书里
  定性为“越权子代理”。
- 教训：同一 batch_tag/roots 只能有一个发车者；发车前必须查 `squeue` + 两臂 `history`；
  **禁止直接 sbatch `sbatch_ti_run.sh`**。

### 2.3 现场保全（截至 14:30）

| 项 | 状态 |
|---|---|
| 运行作业 | `squeue` 空，无作业 |
| B2 批根 | `~/ppv1_hpc/batch/t_i_298_20261021b2_{glm,deepseek}` 各顶层 21 项、批根内各 609 文件；未删未改 |
| B2 runs | DeepSeek 10 个 run 目录（smoke 阶段有结果）；GLM 2 个目录只有 `driver.lock`（stub） |
| B2 stop | `~/ppv1_hpc/operations/t_i_coordination_t-i-298-20261021b2/stop.json`，**保留，不清除、不覆盖** |
| 旧批 20261020 | 按 B2 prepare 的 pre/post 快照，批根、stop、封存零变化 |
| score / sealed | 未见；B2 未进入 full、未判分、未封存 |
| 已花费 | B2 C5 预检 seq 3/4（2 次，HTTP 200）+ DeepSeek smoke 12 次；GLM 0 次。金额未知 |

## 3. B3：另一窗口已在准备（接手先核，别重复）

主窗口在 14:26 派了一个 **B3 新批执行子代理**，任务书写明：

- 新 tag：`t-i-298-20261021b3`；批根 `t_i_298_20261021b3_{glm,deepseek}`；
  协调目录 `t_i_coordination_t-i-298-20261021b3`。
- **B2 两根 + 20261020 旧批两根全部加入 `immutable_batch_names`**；B2/旧批零触碰。
- 流程：C3 netcheck → B3 config → 14 件重锁 + 批准包新增 `b3_rebatch` → C2/C4 →
  **C5 两臂最小真实调用（付费 2 次）** → 两臂 build → 身份（两臂指纹逐字相同）→
  prepare（P2-face 八项）→ **不 run/score**。
- 报告路径：`docs/T_I_B3_REBATCH_2026-10-21.md`（截稿时尚未落盘）；证据目录由执行者按报告建。
- 子代理 session：`sess_subagent_agent_7b210fdc-eb91-49fe-a3c1-75c9126476d7`；
  父窗口 `sess_68ac8cb9-3b68-4dad-a1a2-db95ed8e78aa`。

**14:57 状态（15:20 更新见 §3.1）**：B3 证据目录已出现
（`docs/review_evidence/ti_b3_rebatch_2026-10-21/`，含 `pre_state.json`、`netcheck_47060529.out`、
`c2_c4.json`、`preflight_calls.json`、`lock_verify.txt`、`approval_revalidate.out`）；
**C3 netcheck 14:34 已 PASS**（作业 `47060529`，节点 `g02r1n01`）；
**C2/C4 14:43 双 PASS**；**C5 seq 5/6 均 HTTP 200（14:45）**；
**两臂 build `47061667`/`47061671` 14:47 起 RUNNING**；B3 报告尚未落盘；
B3 批根/身份门/prepare 尚未完成。子代理已过 config/锁/批准包阶段。
**不要另起一个 B3 准备任务**；如果它被关窗打断，先看它已写了哪些文件、
HPC 是否有半成品，再从断点续，不要推倒重来。

> 注意：B3 的 C5 是付费的 2 次真实调用；除 C5 外，B3 准备不调模型。是否已发生，查
> `~/ppv1_hpc/operations/preflight_calls.json` 里 `batch_tag=t-i-298-20261021b3` 的 seq。

### 3.1 新窗口接手进度（2026-10-21 15:20 CST）

新窗口 `session_ffad599cdcdfd84f2926c09e83edf165`（title `main-1021`）14:38 接手；
只读核验后没有重复派 B3，也没有发 run。14:53 另开 4 路离线任务（零模型费、不连 HPC）。

**B3 主线（截至 15:20）**

| 项 | 结果 |
|---|---|
| C3 netcheck | 14:34 PASS（`47060529`，`g02r1n01`） |
| 锁/批准包 | 14:40 14/14 锁 OK（仅 `ti_arm_config.json` 变）；批准包重验 PASS，`b3_rebatch` 块已写，B2 + 20261020 四根 immutable |
| C2/C4 | 14:43 双 PASS；凭证 600、新路径不存在、flock 语义、两臂模型同值 |
| C5 | seq 5（GLM）/6（DeepSeek）均 HTTP 200；GLM in/out 21/41 tok，DeepSeek 38/18 tok；金额 unknown；B3 仅此 2 次付费调用 |
| build | `47061667`/`47061671` 14:47 起 RUNNING；15:20 时 32:55，两臂 `run_inputs=145/298`；日志无报错 |
| 未做 | build-gate / verify-identity / prepare / B3 报告；协调目录未建（launch 时才建，正常） |

**新窗口 14:53 派的 4 路离线任务（最终交付未完成）**

| 路 | 工作树/交付 | 截至 15:20 |
|---|---|---|
| P2 v1card 实现 | `/private/tmp/dependingv43_p2_v1card`；报告 `docs/T_P2_V1CARD_IMPL_2026-10-21.md` | 已改 `runflow/real_model/candidate_evidence` + 新测试；报告未落，仍在跑 |
| P2 操作链 | `/private/tmp/dependingv43_p2_ops`；报告 `docs/T_P2_OPS_CHAIN_IMPL_2026-10-21.md` | orchestrator/worker 接线中；脚本族/正负控/报告未落 |
| P3 供给诊断 | `docs/T_H_P3_SUPPLY_TRIAGE_2026-10-21.md` | 只读诊断中，报告未落 |
| P2 v2 化学复审 | `docs/TASK_P2_V2_CHEM_REVIEW_2026-10-21.md`（SHA `27b58b56…20dcb7`） | 14:53 请求子代理 `...ca09658e` 14:55 失败；15:18 另开 side session `sess_05143c…` 写了自包含任务书，列出 3 个待判点（碳酸/羧酸 SMARTS、季铵漏类、过氧化物氧化态）；**Stage A 请求 + Stage B 独立评审仍未做** |

> 这 4 路都在隔离 worktree/只读，未触碰 14 件 T-I 锁定文件，未调模型，未连 HPC。
> 不要因为“P2/P3 在跑”就去动 B3 的锁定树。

## 4. 新窗口的决策点

| 选项 | 说明 | 建议 |
|---|---|---|
| **A. 等 B3 准备完 → 核报告 → 发 B3 run** | 最干净；B3 身份/批准/锁都是新的，旧批零触碰 | **默认走这条**；发车付费前必须 CC 点头 |
| B. 救 B2 | 需要清 `stop.json` + 对两个 stub 做 `resume`；但 stop 现场“首个写入者生效、不清除”是既定纪律，且 stub 没有可恢复状态 | 不建议；除非 CC 明确特批并记录披露 |
| C. 暂停/换站 | 代理已绿，没有换站证据；除非 B3 C3/netcheck 再失败 | 暂不需要 |

**B3 发车前必须满足**：

1. B3 报告落盘，锁/批准包/两根/immutable 四项自洽；两臂 build 指纹逐字相同；
   prepare 八项等于 `531/242/205/78`、`298/151/134/65`、`files=298`。
2. B2 + 旧批零触碰（报告里有审计）。
3. 距最近一次 netcheck 绿 ≤2h；超了先做快检（登录经代理 3/3 或计算节点 6/6 或官方 netcheck）。
4. `squeue` 为空；`ti_operations` 两臂 history 里没有未收尾的 run；只允许一个发车者。
5. CC 明确同意付费发车。

## 5. 接手第一步（只读核验，不改）

```bash
cd /Volumes/CC/Enzyme_Agent/dependingv43
date
git rev-parse --short HEAD
git status --short | head -20

# B3 是否落盘
ls -l docs/T_I_B3_REBATCH_2026-10-21.md 2>/dev/null || echo "B3 report not yet"
ls -ld docs/review_evidence/ti_b3_rebatch_2026-10-21 2>/dev/null || echo "B3 evidence not yet"

KEY=/Volumes/CC/Enzyme_Agent/aclhl3hbth_wuzh02.hpccube.com_RsaKeyExpireTime_2026-11-30_10-12-36.txt
SSH="ssh -i $KEY -p 65091 -o BatchMode=yes -o ConnectTimeout=10 aclhl3hbth@wuzh02.hpccube.com"
$SSH 'squeue -u aclhl3hbth -o "%i %j %T %M"; echo ---; ls -d ~/ppv1_hpc/batch/*b3* ~/ppv1_hpc/runs/*b3* ~/ppv1_hpc/operations/*b3* 2>/dev/null; echo ---; cat ~/ppv1_hpc/operations/t_i_coordination_t-i-298-20261021b2/stop.json'
```

核完 B3 报告后，**发车命令用报告里的原文**（模板同 B2
`docs/T_I_B2_PREPARE_2026-10-21.md` §8，只把 tag/路径换成 b3）。发车前再跑一次：

```bash
$SSH 'squeue -u aclhl3hbth; python3 -c "import json;d=json.load(open(\"/work/home/aclhl3hbth/ppv1_hpc/operations/preflight_calls.json\"));print([r for r in (d if isinstance(d,list) else d.get(\"calls\",[])) if r.get(\"batch_tag\")==\"t-i-298-20261021b3\"])"'
```

> 不要直接 `sbatch sbatch_ti_run.sh`；只走 `ti_operations.py launch`。发车后立刻确认
> history 里只有一组新 job id，且没有第二个人在发。

## 6. 其他并行线程（别丢）

| 线程 | 状态 | 下一步 |
|---|---|---|
| P2 完整证据卡 v2 | 预注册 `docs/T_P2_PREREG_FULL_V2_2026-10-21.md` **DRAFT_NOT_SIGNED**；发车任务书不可执行；14:53 新窗口另开 v1card/操作链/化学复审三路，均未交付；化学复审已由 side session 写任务书 `docs/TASK_P2_V2_CHEM_REVIEW_2026-10-21.md`，但独立评审未做 | 等 T-I 结果/模型对确定；先补三路交付/复审，再签字，预注册先于付费 |
| P3 供给分项 | 14:53 起只读诊断；报告 `docs/T_H_P3_SUPPLY_TRIAGE_2026-10-21.md` 未落 | 报告落盘后按优化计划 §4 P3 立项 |
| T-H P1-B 反馈 | r1fix 已实现，patch `docs/review_evidence/p1b_impact_2026-10-21/impl.patch` SHA `0ae65357…`；qwen 复审已出；预注册草案 `docs/T_P1B_PREREG_FEEDBACK_2026-10-21.md` 未签 | CC 签预注册 + 决定是否合并 `/tmp/dependingv43_p1b` |
| Codex 额度 | 截至本窗口仍按无额度处理；qwen3.8max 代审 | 额度恢复后对 B3/关键轮做正链复核（不替代程序证据） |
| 代理长期稳定性 | 本次恢复，根因/归属未查清 | 记录到运维；下次发车前仍按 2h 快检 |

## 7. 文件、会话、易失件

### 7.1 本窗口/相关会话

| 会话 | ID | 说明 |
|---|---|---|
| 本 OpenCode 会话 | `ses_ea3e668beffe9dJeLDrbD3B3U3` | 标题已改为“T-I B2 停点诊断 + B3 准备中移交 2026-10-21” |
| 本窗口 soak 子代理 | `ses_ea3d08e14ffe7SA89XenC9KHfE` | G1–G4 执行 |
| zcode 主窗口 | `sess_68ac8cb9-3b68-4dad-a1a2-db95ed8e78aa` | B2 发车/停点、B3 派工 |
| zcode B3 子代理 | `sess_subagent_agent_7b210fdc-eb91-49fe-a3c1-75c9126476d7` | 14:26 起，B3 build 中 |
| zcode B2 prepare 子代理 | `sess_subagent_agent_91ab8503-2f7e-4afc-a723-bdbce5566d07` | 12:53 结束 |
| 新窗口（接手） | `session_ffad599cdcdfd84f2926c09e83edf165` | 14:38 起，title `main-1021`；只读核验 + 4 路离线任务 |
| 新窗口 P2 v1card | `sess_subagent_agent_7d2f9a13-4001-442d-92cd-db1475043dff` | 14:53 起，跑中 |
| 新窗口 P2 操作链 | `sess_subagent_agent_5a2ff91a-ea94-4b79-91df-ed07b1ad1b24` | 14:53 起，跑中 |
| 新窗口 P3 诊断 | `sess_subagent_agent_c9efef02-b3dc-4981-b123-b451e990cabc` | 14:53 起，跑中 |
| 新窗口 P2 化学请求 | `sess_subagent_agent_ca09658e-bf2f-4607-91f5-0cc8ea4725cd` | 14:55 失败；由 side session 接手 |
| 新窗口 P2 化学任务书 | `sess_05143c65-7f30-4308-9ef8-4c8fde18cf69` | 15:12 起；15:18 写 `TASK_P2_V2_CHEM_REVIEW_2026-10-21.md` |

### 7.2 证据目录（本地）

| 目录 | 内容 | 校验 |
|---|---|---|
| `docs/review_evidence/ti_b2_soak_2026-10-21/` | G1–G4 原始输出、脚本、RUN_NOTES | SHA256SUMS 9/9 OK |
| `docs/review_evidence/ti_b2_rebatch_2026-10-21/` | B2 重批身份证据、pre_state、raw_gate | SHA256SUMS 12/12 OK |
| `docs/review_evidence/ti_b2_prepare_2026-10-21/` | 两臂 prepare/P2-face/审批重验/前后快照 | SHA256SUMS 19/19 OK |
| `docs/review_evidence/ti_b3_rebatch_2026-10-21/` | C3/C2/C4/C5、锁/批准重验、build 提交回执 | 未封 SHA（build 中） |
| **B2 停点现场** | **尚未镜像本地** | 待办：拉 `stop.json`、两 case、两份 slurm out、monitor json、smoke 回执、run 目录清单到 `docs/review_evidence/ti_b2_stop_2026-10-21/` |

### 7.3 HPC 关键路径

```text
~/ppv1_hpc/batch/t_i_298_20261021b2_{glm,deepseek}        # B2 批根（只读保全）
~/ppv1_hpc/runs/t_i_298_20261021b2_{glm,deepseek}         # B2 runs（ds 10 个，glm 2 个 stub）
~/ppv1_hpc/operations/t_i_coordination_t-i-298-20261021b2 # stop.json / 回执 / monitor
~/ppv1_hpc/batch/t_i_298_20261021b3_{glm,deepseek}        # B3（已建，build 中）
~/EnzymeAgent/v43cTH                                      # 部署代码树
~/ppv1_hpc/venv_v44run/bin/python                         # 运行解释器
```

### 7.4 易失件

- `/tmp/dependingv43_p1b`：P1-B r1fix worktree（4 个 modified src + 1 个新测试）；
  patch 已落 `docs/review_evidence/p1b_impact_2026-10-21/impl.patch`，即使 /tmp 被清也可恢复。
- `/private/tmp/dependingv43_p2_v1card`：新窗口 P2 v1card 实现 worktree（3 源文件 + 2 测试）；
  未提交、未合并，报告未落。
- `/private/tmp/dependingv43_p2_ops`：新窗口 P2 操作链 worktree（orchestrator/worker + 脚本族）；
  未提交、未合并，报告未落。
- HPC 旧 `/tmp` pre_state（10-20）已丢，既有文档已记录；不要再用它做证据。
- zcode 原始日志：`/Users/cc/.zcode/cli/rollout/*.jsonl`（含 13:03 越权现场线索，只读）。

## 8. 挂账义务

1. **B2 停点现场镜像**：按 §7.2 拉回本地 + SHA256SUMS；不修改 HPC 现场。
   15:15 实测 B2 `stop.json` SHA256 `fb1d162728c2df8043e19423afad591574c8ce3b875330a42eb49582a7825c46`，未清未改。
2. **B2 费用回填**：C5 seq 3/4 两次 + DeepSeek smoke 12 次；金额未知，等账单/用量页回填。
3. **B3 费用**：C5 seq 5/6 两次已发生（HTTP 200，金额 unknown）；发车后另记 smoke/full。
4. **批名偏差追认**：B2/B3 的 tag 与旧批命名不同，需 CC 在结果报告里追认。
5. **结果披露**：T-I 最终报告必须披露 10-20 首次停点、B2 越权污染、B2→B3 身份切换；
   不能只报 B3。
6. **Codex 正链复核**：额度恢复后补；qwen 代审不替代。
7. **流程修复**：单发车锁/发车前 `squeue`+history 检查/禁止直接 sbatch；B3 任务书已写
   “绝对不许直接 sbatch”，但要在代码或 runbook 里落一条硬门。
8. **代理归属**：`10.15.2.115:3000` 的负责人/长期稳定性未查清；下次仍按 2h 快检。
9. **P2 化学复审独立结论**：原始请求子代理 14:53 派、14:55 失败；side session 15:18 已写
   任务书 `docs/TASK_P2_V2_CHEM_REVIEW_2026-10-21.md`（SHA `27b58b56…`），但 Stage A 请求
   与 Stage B 独立评审都未做；P2 签字前必须补齐。
10. **B3 build 未收工**：15:20 两臂 `run_inputs=145/298`；build 完还要 build-gate、verify-identity、
    prepare。**不要重复派 B3，也不要直接 sbatch。**

## 9. 红线（接手先读）

- 金标/题面/封存逐题 run 永不入仓、不外发；本文件不含金标。
- 20261020 旧批与 B2 批根/runs **只读**；不写、不删、不改 stop。
- B2 `stop.json` **不清除、不覆盖**；不自动 resume。
- B3 准备阶段不 run/score、不调模型（C5 两次预检除外）。
- 任何付费 run 必须 CC 拍板；没有 token/金额硬帽（2026-10-20 用户决定），但费用异常随时停。
- 不 push；评审/证据文档默认未跟踪，由用户定期自决。

## 10. 给下一窗口的开场提示（可直接粘）

```text
读 /Volumes/CC/Enzyme_Agent/dependingv43/docs/HANDOFF_T_I_B2_B3_2026-10-21.md 全文。
当前 T-I：B2 因 13:03 越权直接 sbatch + 14:15 正规 launch 重叠，停在 smoke2
（run_already_exists），stop.json 保留；主窗口已派 B3 子代理只做准备（不 run），
15:20 两臂 build 仍在跑（145/298），B3 报告未落。
先按 §5 只读核 B3 是否落盘/有无作业，别重复派 B3，别动 B2/旧批，别清 stop.json，别直接 sbatch。
核完 B3 报告后，把“是否发 B3 run（付费）”的选项给我，我拍板。
```
