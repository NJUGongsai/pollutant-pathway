# HANDOFF — RR A/B 298 全量上曙光 HPC（2026-10-12 交接）

> 交出窗口：主会话（本窗口）。接手窗口：零上下文按本交接执行。
> 用户已拍板：RR A/B 可以测、**都在 HPC 上测**（不用 chenyu 跑），
> 先核代码版本再 sbatch。本交接按"版本核验 → 环境核验 → 发车"三段
> 给全部活状态与命令。

---

## 一、任务一句话

v44 仓（RetroRules 供给通道）的 298 A/B 对照实验：**A 臂=RR 关**
（pool-policy-5，现供给）vs **B 臂=RR 开**（pool-policy-6-rr1，加
RetroRules 21,454 条规则池）——同 298 题、同模型（GLM-5.3-Flash）、
同冻结判分，唯一变量是供给。目的是攻 chain12 丢分主战场
（120 题"已提交但不匹配"=供给内容不对）。发车环境=曙光 HPC
（乌镇 wuzh02），**不是 chenyu**。

## 二、关键仓库与版本（开工先核这个）

| 件 | 路径 / 值 | 状态 |
|---|---|---|
| **v44 仓**（A/B 实验本体） | `/Volumes/CC/Enzyme_Agent/dependingv43/v44`（分支 `codex/v44-bootstrap`） | HEAD=`af0fd26`（12:10）✅ 这就是丢分归因拍板要钉的基线（含 v43 三收口修复+T1a 池层谱系+RR 通道同 schema 谱系行+受控词表 CI） |
| v44 工作树 | 3 个文件被改：AGENTS.md / README.md / docs/TASK_V44_RETRORULES_INTEGRATION_2026-10-11.md | 接手时先 `git diff` 看一眼——是兄弟会话的在飞文档改动，**不阻塞发车**（不动 src/tests）；如实登记进你的交付记录，不擅自提交不回退 |
| v43 仓（发车脚本所在） | `/Volumes/CC/Enzyme_Agent/dependingv43` | HEAD=`652ec27`；sbatch 脚本族在 `scripts/hpc/`（4a4004a 提交） |
| chenyu（**不要在这跑**） | `/usrdata/.../v44_glm_298_20261012`（代码）+ `v44_glm_298_20261012_a`（A 臂 build，仅 batch_manifest+run_inputs，**无 cases/runs=未发车跑题**） | 16:24 实查：**无任何 v44/s5b 进程在跑**，双发车风险当前为零。但兄弟会话（钉 b7be4d1 基线的那个）可能随时回来发车——**你发车前再查一次**：`/tmp/cy_ssh.sh "ps aux | grep -E 'v44|s5b_cli run' | grep -v grep"`，若见进程立即停下与用户协调 |
| chenyu SSH 助手 | `/tmp/cy_ssh.sh "<cmd>"`（expect 封装；连接不稳，失败重试 5 次间隔 12s） | 凭证内嵌勿打印 |

## 三、HPC 环境事实（已端到端验证过，来自 v43 兄弟轮）

- **连接**：`ssh -i "/Volumes/CC/Enzyme_Agent/aclhl3hbth_wuzh02.hpccube.com_RsaKeyExpireTime_2026-11-30_10-12-36.txt" -p 65091 aclhl3hbth@wuzh02.hpccube.com`
  （密钥文件就是那个长名 txt；`zzeshell` 侦察实锤：**账号当前不在分区**，任何 sbatch 会被拒——**开工第一件事核分区状态**：登录后 `sinfo -a` 看乌镇分区名+账号权限，若仍无分区权限→停，报告用户走分区申请，别硬投）
- **代码位置**：`/work/home/aclhl3hbth/EnzymeAgent/v43`（v43 代码已部署并 10 题验批通过：netcheck→build→10/10 零失败 0.84 元→判分→报告全链通）
- **python**：必须用 `/usr/local/python3.12/bin/python3`（系统 py 缺 numpy）；rdkit 已 `pip install --user`；**共享盘不走 /tmp**（登录节点轮转，易失）；scp 要绝对路径
- **sbatch 脚本族**（v43 `scripts/hpc/`，`deploy.md` 有完整手册）：
  - `sbatch_hpc_298_netcheck.sh`（环境自检）
  - `sbatch_hpc_298_build.sh`（批根构建，~20-25 分钟/臂）
  - `sbatch_hpc_298_shard.sh`（**分片跑题**；作业数组 `sbatch --array=1-5`，每分片 20 workers，同参发车，断点续跑=重投同参）
  - `sbatch_hpc_298_score.sh`（判分）
  - 串接：`BUILD_ID=$(sbatch --parsable ...build.sh); sbatch --dependency=afterok:$BUILD_ID --array=1-5 ...shard.sh`
  - 首批建议全分片同节点（`--nodelist=`）——跨节点 flock/死亡占位回收未实测

## 四、A/B 的 v44 侧事实（发车要用的）

- **本地 A/B build 已齐**（v44 仓 `reports/ppv1_s5b/`，gitignored）：
  - `v44_glm_298_a_g1`（A 臂，policy-5，build 19m51s）
  - `v44_glm_298_b_g1`（B 臂，policy-6-rr1，含 `rr_sidecars/`+`rr_workers/`，build 22m07s）
  - 两臂 run_input 白名单已核（零金标键、池语义版本逐条断言）
- **但 HPC 上要用 af0fd26 重 build**（丢分归因拍板）：chenyu 上那个 `v44_glm_298_20261012_a` 是兄弟会话按 **b7be4d1** 钉的旧基线 build——**不要用它**。正确路径：把 v44@af0fd26 代码传 HPC（v43 代码已在，v44 是独立目录树，传法照 deploy.md §部署，rsync 增量）→ 在 HPC 上重 build A/B 两臂（build 脚本跑两遍，B 臂带 RR 注入：`scripts/v44_build_arm_b.py` 的 P2 入口，参考 v44 仓 docs/V44_298_PREREGISTRATION_2026-10-11.md §5 的 build 命令与 RR 激活证据）
- **预注册**：`docs/V44_298_PREREGISTRATION_2026-10-11.md`（v44 仓内）——A/B 臂定义/RR 索引 SHA（radius6 21,454 规则，`99d697c2…`）/注册序 SHA（`7d73294f…` 题卷序一致）/no-cap 模式（用户四项授权：无预算帽/不看价/Chenyu env/已批准）。**注意**：预注册代码身份节写在 d8089cd（钉 b7be4d1）——按拍板 A/B 应钉 af0fd26，接手后需出一条预注册勘误/增补记录（新登记 af0fd26 身份，旧稿不回写），随发车证据落盘
- **题卷**：HPC 上 questions.jsonl 已到位（10 题验批用过）；SHA `9f5955d4…` 发车时实核
- **发车硬门**：v43 侧 real 批要 budget_guard（60 帽）——**但 v44 A/B 是 no-cap 模式**（用户拍板无帽），确认 v44 发车器（`scripts/v44_298_launch.py`）与 v43 sbatch 脚本的门衔接：若 sbatch 脚本强制 budget_guard 而预注册是 no-cap，以 v44 预注册为准调整或写明豁免（如实登记）

## 五、建议执行序（接手窗口照此走）

1. **核版本**：v44 仓 `git log -1` 应为 af0fd26；diff 那 3 个在飞文档改动如实登记
2. **核 chenyu 无双发**（§二表格末行的命令）；有进程→停+报告用户
3. **登录 HPC 核分区**：`sinfo -a` + 试投 `sbatch scripts/hpc/sbatch_hpc_298_netcheck.sh`——被拒→报告用户分区申请状态，到此为止
4. **部署 v44@af0fd26 到 HPC**（rsync 增量，照 deploy.md；别覆盖 v43 目录，v44 独立树）
5. **HPC 重 build 两臂**（A：标准 build；B：RR 注入 build）+ 白名单核验（`scripts/v44_check_build_outputs.py`）
6. **预注册增补记录**（af0fd26 身份）+ 题卷 SHA 实核
7. **发车**：netcheck→build→shard --array→score 全链 sbatch（两臂各一套批根，臂间串行或并行按资源定；同臂分片必须同参同节点）
8. **监控**：squeue/slurm-logs 轮询；两臂出数后对照表（主口径 hit@1/3/5、U、池诊断计数——B 臂 RR 池供给 vs A 臂）落盘 docs/ 交回用户

## 六、红线（沿用仓规）

金标/题面永不入仓（HPC 批根承载）；判分零 LLM；两臂同配置单变量（RR 开关唯一差异）；no-cap 但请求/费用账照记；不做多批 best-of 拼接；兄弟会话的在飞文件不动；不 push（发车产物按轮提交另说）。A/B 结果定位=已见题供给实验，不外推。

## 七、/tmp 易失件（本交接依赖）

| 件 | 用途 | 丢失怎么办 |
|---|---|---|
| `/tmp/cy_ssh.sh` | chenyu 探测 | 凭证在用户处，按 AGENTS 交接文档 §6 重建 |
| HPC 密钥 txt（`/Volumes/CC/Enzyme_Agent/aclhl3hbth_...txt`） | HPC SSH | 在 Enzyme_Agent 根目录，非易失 ✅ |

交接人：主会话（2026-10-12 16:30）。接手后先读本文件+v44 预注册+deploy.md 三件，再动手。
