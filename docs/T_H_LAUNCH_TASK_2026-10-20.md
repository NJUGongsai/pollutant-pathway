# 任务书 — T-H 修复批发车物（298 post-hoc，2026-10-20）

> **⚠ 2026-10-20 晨附记（冒烟事故+重启）**：本任务书首轮发车在 run 冒烟段抓到 CX 身份守卫杀题
> （21/298 题 0 调用即死；D1.2 副作用）⇒ 主动停批（费用仅 10 次请求）；修复=compiler-6 产物侧
> 身份自洽门（CC 拍板 A，待复核）。**重启一律按 `docs/HANDOFF_T_H_RELAUNCH_2026-10-20.md` §3
> 执行**（批根改 r2、批准件三件套复制、P2 探针预期值更新 261→240/222→201）；本文件其余章节
> （批定义/对账清单/红线）继续有效。事故档案：`docs/T_H_SMOKE_INCIDENT_2026-10-20.md`。

> **状态**：发车任务书（CC 已签字 2026-10-20；首轮冒烟中断，重启见上方附记）。本文件是「发车面」的唯一操作底稿：
> 执行者照此走，一步一核，禁止临场加戏。
> **必须 CC 亲自签的两件**：①预注册定稿签字（`approval_source`）；②付费+HPC 发车指令。
> **题域标签**：**298 = RHEA 通用酶学 / 已见题（post-hoc）**；探针 ≠ 预注册 ≠ 成绩；
> **一批跑完、禁止修一点跑一点**。
> 上游：老师任务书 #8（`docs/TEACHER_TASK_GONGSAI_LINE_EXECUTION_2026-10-15(1).md`）+
> `docs/T_H_LAUNCH_PREP_2026-10-20.md`（预注册骨架）+ `docs/T_H_P2_CHEM_FORWARD_DRAFT_2026-10-20.md`
> （**CC 已认可 A=披露**）+ 三份实施复审放行报告（D1.2 二轮/E1a/E1b，代 Codex 通道）。

## 0. 一句话

单臂 T-H 修复批：把 **D1.2（compiler-5 补映射）+ E1a（T-E 归一/policy-9/source-4）+ E1b（criteria-v3
档 A）+ C/T-F 既往轮**全部装进**一次批跑**（298 题、GLM-5.3-Flash、双口径判分），预注册
**hit@1 35–40%**、**<32% 逐桶回查 chain13**。代码面=已提交 `d4cc871`（v4.3）。

## 1. 前置状态（全齐，2026-10-20）

| # | 前置 | 状态 |
|---|---|---|
| 1 | T-F / T-G C1/C2 / D1.2 / E1 全收口 | ✅（复审全放行，P0/P1/P2=0） |
| 2 | 提交面 | ✅ `d758845`（代码+测试）/`ba9b3f2`（文档）/`616dad8`（P3 小件）/`d4cc871`；**发车前全量 not-slow 2293/0/16 绿记录**；HPC 同步的代码 sha 以上述为准 |
| 3 | P2-CHEM-FORWARD | ✅ **A=披露**（CC 认可）；**分母已测**（本地 298 重建：remap-applied 261 / 含新增原子 222 / 多原子 96；144 题；`reports/ppv1_s5b/t_h_prep_2026-10-20/p2_face_measure_2026-10-20.json`）——**发车后按批根复测为准**（§3 步 5） |
| 4 | P3-IDENT | ✅ 批级 `compiler_version` 键已落地（`616dad8`；batch 诊断三处） |
| 5 | 预注册 | 📝 定稿候选（`T_H_LAUNCH_PREP §2` 全文）+四点补充（human_review 义务/P3-MONITOR/HPC 机坑/T-E 上限句）——**待 CC 签字** |
| 6 | 费用/发车指令 | ⏳ **待 CC**（real 批走既有 approve+budget 流程；帽值由 CC 在指令中给） |

## 2. 批定义

| 项 | 值 |
|---|---|
| 批 | **单臂**（非 A/B；对照=chain13/14 历史批，同题域标签） |
| 模型/配置 | **GLM-5.3-Flash**；配置沿 chain13/14（llm.env；同参） |
| 变量登记（相对 chain13） | D1.2=compiler-5/template-remap-1；E1a=policy-9/source-4/record-side-formnorm-1；E1b=criteria-v3 档 A 披露块（**不进 hit@1**）；C=policy-7/8；T-F=rank-policy-2；**P2 面=披露口径（A）** |
| 题卷 | 298 冻结题卷（questions.jsonl；**发车时实核 SHA**，与 chain13/14 同源） |
| 判分 | v1 缺省 + v2 显式**双口径并列报**；V3 档 A 披露块随批输出；零 LLM 程序侧 |
| 批根（HPC） | `~/ppv1_hpc/batch/t_h_s5b_298_20261020`（runs 根同款；新批根，封存批只读） |
| 本地镜像 | `reports/ppv1_s5b/t_h_2026-10-20/`（拉回产物；gitignored） |
| 费用 | 按批请求/费用账照记（usage/金额；缺数如实 unknown）——帽=CC 指令 |

## 3. 发车步骤（HPC 乌镇 wuzh02 为主；昆山为备选）

1. **CC 签发**：预注册定稿（approval_source=CC+日期+预注册文本 sha）→ 落批根
   `preregistration_approval.json`（real 批判分门要求；沿既有格式）；付费/HPC 指令落字。
2. **登录核分区**：`ssh -i <key.txt> -p 65091 aclhl3hbth@wuzh02.hpccube.com`；`sinfo -a`
   → 账号分区权限；**被拒→停，报 CC**（不硬投）。
3. **代码同步**：rsync 增量 v4.3@`d4cc871` 工作树 → HPC `/work/home/aclhl3hbth/EnzymeAgent/v43_TH`
   （照 `scripts/hpc/deploy.md` 方法；新目录不覆盖旧 v43）；同步后 HPC 侧实核
   `s5b_compiler.py=1f1343cd`/`evaluation.py=a7e5ecfd` 等关键 sha 并记录（**记录实际 HEAD/sha，
   不信旧脚本硬编码**）。
4. **netcheck → build**：`sbatch_hpc_298_netcheck.sh` 过 → `sbatch_hpc_298_build.sh`
   （~20–25 分钟）；**build 后核 `build_identity.json` 在位**（E1a 首消费绑定的批旁块）+
   `pool_policy_version=s5b-pool-policy-9`/`compiler_version=s5b-compiler-5`/formnorm 键在位。
5. **P2 面向分母探针（发车硬前置，分钟级）**：扫批根 run_inputs `plan.pools`：
   `template_remap.applied` 计数 / 其中含 `add_atom` 编辑计数 / 多原子（≥2）计数（分通道、
   题级）→ 落批根 `p2_face_measure.json`（**披露项分母以批根实测为准**）。
6. **shard 跑题**：`sbatch --dependency=afterok:$BUILD_ID --array=1-5 sbatch_hpc_298_shard.sh`
   （20 workers/分片；**同参同节点**；断点续跑=重投同参；不发中间修跑）。
7. **score**：`sbatch_hpc_298_score.sh`（双口径；metrics/report 落批根）。
8. **拉回**：批根产物 → 本地 `reports/ppv1_s5b/t_h_2026-10-20/`（只读留档）；
   批根置只读封存。

**备选**：昆山 cancon:65023（kshcnormal 不排队）——**跨站批根必须在同站 build**（sidecar
绝对路径烤死），整套步骤在昆山重走；站选择归 CC 指令。

## 4. 监控与失败处置（P3-MONITOR 条款，CC 简报落字）

- **prediction_recovery 家族（含 crash/resume 幂等件）在 HPC 批跑是常态路径**：该家族任一失败件
  ⇒ **留现场**（日志 + state 目录 + validation.json 原样，不删不覆盖）→ **同题重试 1 次**
  （重投同参）→ 仍败 ⇒ **如实登记**（题号/阶段/证据路径），**不得按 flake 静默放行**。
- 批跑期间**代码零改动**（一批跑完纪律）；节点 /tmp 满 ⇒ 门逻辑写**实体脚本**（heredoc 会炸）；
  sbatch 提交时快照脚本；传输/API 断流 ⇒ 重投同参续跑；flock 单协调者守卫在位。
- 费用异常/超帽 ⇒ 停并报 CC。

## 5. 出数后对账清单（交付义务）

1. 双口径 hit@1/@3/@5 + strict 覆盖 vs chain13(87)/chain14(A 91/B 85) 同口径表；
2. **修复兑现表**（工程损耗回收，同口径前后对照，每项挂 record_key/题域标签）：T-E 面
   （三层分开；**20/9=上限口径非命中**；第三层 strict 命中本批实测）、D1.2 面（tnc 迁移件）、
   C 面（45/35）、T-F 面；
3. **P2 披露项**：批根 `p2_face_measure.json` 分母 + strict 转化率；
4. **human_review 面**：2,503 行（present 209/unknown 2,294）**披露≠已复核**义务登记随交；
5. 费用登记（usage/金额；缺数 unknown）；
6. <32% ⇒ 逐桶对比 chain13 回查；产出 `T_H_RESULT_*.md` 交 CC（区分测量修正与工程回收）。

## 6. 红线

1. 一批跑完、禁止修一点跑一点；判分零 LLM；金标隔离（HPC 批根承载，本地只拉指标）；
2. 单变量纪律：任何超出 §2 变量登记的改动=停报 CC；
3. 封存批/旧批零回写；不 push（除 CC）；题域标签处处带；
4. 探针≠预注册≠成绩；compiled≠化学有效（P2 面口径）。

## 7. 回传义务

- 每步完成回报「做了什么/读数/下一步」（步 2/4/5/6/7 各一次）；
- 出数后按 §5 出对账与交付（大白话版+技术版）；
- 异常（分区拒/费用/连续失败）⇒ 停下报 CC，不自动处置。