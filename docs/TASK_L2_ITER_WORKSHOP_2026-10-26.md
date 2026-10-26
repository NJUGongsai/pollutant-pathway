# 任务书：L2 迭代工坊 阶段 1 —— 重放基座 + 重编译可行性

> **题域标签：[298 域] = RHEA 通用酶学 / 已见题（post-hoc）。** 本文所有数值只在该题域成立，
> 与 dev 域双向不外推。本文是**任务书**，交实施子代理执行；CC 2026-10-26 拍板开工。
>
> **性质：零模型调用、零付费。** 只读 HPC 封存批、只写 notebook 独立工作区；不改判据、不改判分器、
> 不动任何封存批根；不 push；金标只落 notebook `/root/v43_migration`（700）。

---

## 0. 一句话目标

在 notebook 上建「零 LLM 重放基座」，**先复现 T-H r2 的 89/126/53/119 零漂移门**，
再实测**能否用已有模型响应重跑 compile**——这个答案决定 L2 能不能做 remap/identity 类实验。

---

## 1. 现状（已侦察确认，不用重查）

| 项 | 事实 | 出处 |
|---|---|---|
| r2 批根（HPC） | `/work/home/aclhl3hbth/ppv1_hpc/batch/t_h_s5b_298_20261020r2`，封存 555/444（只读） | `docs/T_H_RELAUNCH_EXECUTION_2026-10-20.md:91-93` |
| r2 runs 根（HPC） | `/work/home/aclhl3hbth/ppv1_hpc/runs/t_h_s5b_298_20261020r2`，可写（**不要写**） | 同上 |
| case 形态 | `cases/<qid>.json`，schema `s5b-case-1`，298 条全 completed | `src/pathway_v43/pollutant/s5b_worker.py:526` |
| native export | `runs/<run_id>/native_export/<digest[:24]>/{payload.json,manifest.json}`，298 组约 **16MB** | `scripts/s5b_offline_rescore.py:113-121` |
| 重放先例 | P0b Phase D：10.4s 跑完，全部 mismatch=0 | `docs/T_H_P0B_D6_IMPL_2026-10-20.md:93-108` |
| 现成脚本 | `docs/review_evidence/t_h_p0b_fix_2026-10-21/phase_d/phase_d_replay.py`、`scripts/s5b_offline_rescore.py` | — |
| r2 代码锚 | `c360e74`（evaluation.py/scoring.py 与当前 HEAD **字节相同**；compiler 多 21 行诊断常量，不参与编译） | `docs/T_H_R2_SCRIPT_LOCK_2026-10-20.json:3,15-17` |
| notebook 现状 | 有完整 298 build 产物，**没有** T-H r2 模型输出（只有 P2 停点 54/55 case） | `docs/NOTEBOOK_MIGRATION_2026-10-23.md:47-51,196-211` |
| notebook 连法 | `bash scripts/hpc/nb_ssh.sh "cmd"`（本地→HPC→notebook 两跳） | `scripts/hpc/nb_ssh.sh` |

**硬约束（决定实验设计）**：

| 改动层 | 能否零 LLM 重放 | 原因 |
|---|---|---|
| 判分/匹配层（`evaluation.py`、`s5b_scoring.py`） | ✅ 能 | 冻结导出 + 冻结 scorer 直接重算 |
| compile/remap/identity 层（`s5b_compiler.py`、`chemstate` 身份） | ❓ **待实测** | 冻结导出已固化当时编译结果；要么从模型响应重编译，要么做不到 |
| build/pool 层（`s5b_builder.py`、`recorded_source.py`） | ❌ 不能 | 候选池变了 → 模型看到的提示变了 → 必须重调模型 |

**remap 实验能不能零成本做，全看 Step 4 的结论。**

---

## 2. 交付物与验收门

### 交付 1：notebook 重放基座（必须过零漂移门）

- 工作目录 `/root/v43_migration/iter/`（新建，与既有迁移目录并列，不覆盖任何东西）
- 脚本 `bin/replay.sh` + `bin/replay.py`：输入 = 数据根 + 代码版本；输出 = 指标 JSON + 逐题 diff
- **验收门（硬）**：v2 口径复现

| 指标 | 期望值 | 来源 |
|---|---|---|
| 分母 | 298 | `docs/T_H_RESULT_2026-10-20.md:92` |
| hit@1 / hit@3 / hit@5 | **89 / 118 / 125** | 同上 |
| strict / partial / unmatched | **126 / 53 / 119** | 同上 |
| 逐题 `match_status` + `rank` | 与 r2 `metrics.json` **逐题完全一致** | r2 批根 |

- v1 对照也要跑：84 / 113 / 120，strict 121，桶 121 / 58 / 119。
- 任一不符 → 停下报告，不得继续调参凑数。

### 交付 2：数据搬迁与清单

- 从 HPC 搬（只读源）：`cases/`、`run_inputs/`、`reference_graphs/`、`batch_manifest.json`、`split_manifest.json`、`preregistration_approval.json`（如存在）、298 组 `native_export/`
- 落到 `/root/v43_migration/iter/data/r2/`（700）
- 落盘后核：文件计数、总字节、关键文件 SHA256 清单（`SHA256SUMS`），与源端 count 对齐
- **不搬** `pollutant.sqlite`（体积大且离线读取器不需要）；不搬 `env/`、密钥

### 交付 3：重编译可行性探针（本阶段最关键）

要回答一个问题：**给定「已有 run_inputs + 已有模型响应」，能不能重跑 compile 得到与冻结导出一致的结果？**

步骤：
1. 找 compile 的真实入口与输入：`grep -n "def compile_donor_template\|def complete_template_mapping" src/pathway_v43/pollutant/s5b_compiler.py`；找模型响应落在哪（`s5b_responses/`、`native_result.json`、`*.jsonl`，先在 runs 目录里 `find`）
2. 选 **3 道题**（1 道 strict 命中、1 道 partial、1 道 unmatched），用原参数重编译
3. 与冻结 `native_export/<digest>/payload.json` 比较：候选成员、顺序、事件身份/内容/顺序、strict rank 是否逐项一致
4. 出结论：
   - **PASS**：3/3 一致 → 写明"remap/compile 类改动可零 LLM 验证"，并给出最小调用示例
   - **FAIL**：写清缺什么（模型响应没落盘？输入不完整？有不可重放的随机性？）
5. 若 PASS，再做一个**负控**：故意改一个无害编译参数（或改一个 remap 阈值），确认重编译结果**会变**——证明探针真有分辨力，不是永远相等。

### 交付 4：报告

`docs/L2_STAGE1_REPLAY_BASE_2026-10-26.md`（本地落盘，同时回传），含：
- 零漂移门结果表（v1/v2 全部指标 + 逐题 diff 统计）
- 数据搬迁清单与 SHA
- 重编译探针结论（PASS/FAIL + 证据 + 负控结果）
- **明确写出本基座的证明范围**：证明了什么、没证明什么（照 P0b 的 disclosure 写法规矩）
- 下一步建议：如果 PASS，列出 remap 可测的参数面；如果 FAIL，给出替代方案的代价

---

## 3. 红线

1. **零模型调用**：全程不连 DashScope/任何 LLM；不设置模型 key。
2. **不动封存批**：HPC r2 批根只读（555/444），任何写操作先在 notebook 的 `iter/` 副本里做。
3. **不改判据/判分器**：`evaluation.py`、`s5b_scoring.py` 一行不改。需要改代码做负控时，只在 `iter/worktrees/` 下建临时副本。
4. **不碰金标内容**：可以读 `reference_graphs` 做判分，但不得把逐题金标内容写进任何报告/日志；报告只写聚合数与 qid 级指标。
5. **不撞车**：开工前先 `ps` 看 notebook 上有没有别人在跑的批（另一个窗口可能在做 P2 full）；新建目录不与 `p2_*` 批重名；不动 `/root/v43_migration/ppv1_hpc/`。
6. **不 commit、不 push**；本地只新增 `docs/L2_STAGE1_REPLAY_BASE_2026-10-26.md` 与证据目录。
7. 任何数字必须带口径（v1/v2）+ 分母；金额一律 unknown。

---

## 4. 分步

### Step 0：环境与不撞车检查（10 分钟）
```bash
bash scripts/hpc/nb_ssh.sh "ps -eo pid,etime,cmd --sort=-etime | head -20"
bash scripts/hpc/nb_ssh.sh "ls /root/v43_migration/ && df -h / | tail -1"
```
确认没有同名目录、没有正在跑的 298 批；记录当前时间与实例主机名。

### Step 1：搬数据（HPC → notebook）
从 **HPC 发起**（notebook 私钥在 HPC 上）：
```bash
# 在 HPC 上执行
rsync -a -z --info=progress2 \
  -e "ssh -i ~/.ssh/id_ed25519_nb -p 11009 -o StrictHostKeyChecking=no" \
  /work/home/aclhl3hbth/ppv1_hpc/batch/t_h_s5b_298_20261020r2/{cases,run_inputs,reference_graphs,batch_manifest.json,split_manifest.json} \
  root@ssh.zzai.scnet.cn:/root/v43_migration/iter/data/r2/
```
native_export 单独搬（只挑 payload/manifest，避免整 runs 根）：
```bash
# 先在 HPC 上生成清单，再按清单 rsync；或直接 rsync runs 根约 0.18GB
rsync -a -z -e "ssh -i ~/.ssh/id_ed25519_nb -p 11009" \
  /work/home/aclhl3hbth/ppv1_hpc/runs/t_h_s5b_298_20261020r2/ \
  root@ssh.zzai.scnet.cn:/root/v43_migration/iter/data/r2/runs/
```
落盘后：`find ... | wc -l`、`du -sh`、生成 `SHA256SUMS`（只对 case + native_export 的 payload/manifest）。

### Step 2：建重放器
照抄 `docs/review_evidence/t_h_p0b_fix_2026-10-21/phase_d/phase_d_replay.py`，适配成：
- 参数化数据根 / 代码根 / 输出根
- 输出：`metrics_replay.json`（三指标四桶）+ `per_qid_diff.json`（298 题 match_status/rank）+ 人类摘要
- 用 `_offline_export_reader`（`scripts/s5b_offline_rescore.py:100-107`），criteria 显式 `PPV1_CRITERIA_V2`
- 输出写到 `iter/rounds/r000/`，**不写批根**

### Step 3：过零漂移门
跑 v2 + v1，逐项比对交付 1 的表与 r2 `metrics.json`。不一致就停。

### Step 4：重编译探针（交付 3）
按 §2 交付 3 执行，先 3 题，再负控。

### Step 5：出报告（交付 4）

---

## 5. 排障表

| 症状 | 处置 |
|---|---|
| `nb_ssh.sh` 连不上 | 试 `NB_KEY` 直连模式；HPC 私钥可能被平台清（见 `docs/NOTEBOOK_ENV_FACTS_2026-10-26.md` §6） |
| rsync 慢/断 | 加 `--partial --append-verify`；小文件多则先 `tar` 再传再解 |
| 离线读取器报缺 step6/step8 | 那是设计行为（跳过权威引用与图事实陈旧检查），在报告里披露即可 |
| 重放数对不上（≠89） | **不要调参凑**。先核：代码版本、criteria 版本、case 是否 298、reference_graphs 是否同一份、native_export digest 是否对得上 |
| RDKit 版本差异 | notebook 是 2026.03.5 与批内登记一致；Mac 是 .6，**正式门必须在 notebook 上跑** |
| 重编译探针找不到模型响应 | 先把 runs 目录完整 `find` 一遍列文件清单；确实缺失就判 FAIL 并写清缺什么 |
| 发现另一窗口在跑批 | 立即停止写操作，只做只读，回传报告等待指令 |

---

## 6. 回传义务

1. 交付物路径 + 行数/字节数
2. **零漂移门原始输出**（v1/v2 两行 JSON + 逐题 diff 统计）
3. 重编译探针结论：PASS / FAIL，以及证据（3 题逐项比较结果 + 负控）
4. 数据搬迁清单与 SHA256SUMS 路径
5. 遇到的所有偏离任务书的情况（不隐瞒）
6. 明确列出**没做到/没证明**的部分

---

## 7. 附录：关键路径速查

```
HPC r2 批根   /work/home/aclhl3hbth/ppv1_hpc/batch/t_h_s5b_298_20261020r2
HPC r2 runs   /work/home/aclhl3hbth/ppv1_hpc/runs/t_h_s5b_298_20261020r2
notebook 工作区 /root/v43_migration/iter/
notebook 代码   /root/v43_migration/v43cP2
notebook 代理   source /root/v43_migration/iter/config/env_proxy.sh  （本阶段不需要）
本地仓         /Volumes/CC/Enzyme_Agent/dependingv43
重放先例       docs/review_evidence/t_h_p0b_fix_2026-10-21/phase_d/phase_d_replay.py
离线读取器     scripts/s5b_offline_rescore.py:100-107
判分入口       src/pathway_v43/pollutant/s5b_scoring.py:186-195（score_s5b_batch）
编译入口       src/pathway_v43/pollutant/s5b_compiler.py:1416（compile_donor_template）
```