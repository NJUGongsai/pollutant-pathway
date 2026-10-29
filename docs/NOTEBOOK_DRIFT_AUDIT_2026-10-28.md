# Notebook（SCNet）漂移核查报告 — 2026-10-28

- 核查时间：2026-10-28 10:23–10:2x CST（notebook 本地时间）
- 核查方式：只读；两跳 SSH（`scripts/hpc/nb_ssh.sh`）；零模型、零付费、未 commit/push
- 对照基线：用户给定的 2026-10-27 状态表
- 证据命令：见文末附录

## §0 一句话结论

**生产树 `v43cP2` 没有被改动**：四个关键文件 sha256 与基线逐字节一致，且 2026-10-27 00:00 以后生产树内没有任何非缓存/非 runs 文件被修改；`.git` 仍是无 commit 的空仓。所有新活动都发生在 `iter/`（n003/n004 实验、v4 守恒扫描、coverage_v3 产物、主产物表、anscard 构建）和一个极小的诊断 run 里；**最后一次文件写入是 2026-10-27 18:19 CST，此后（含整夜和今天上午）无任何业务文件变化**，也没有计算进程在跑。

## §1 生产树 `/root/v43_migration/v43cP2`

### 1.1 四个关键文件（与基线逐项对照）

| 文件 | 当前 sha256 | 基线 sha256 | 结论 | mtime |
|---|---|---|---|---|
| `src/pathway_v43/pollutant/evaluation.py` | `37c092310d34d9f417234ccacd508942b3ce3edef640c73ab94022fd8dc75ad8` | `37c09231…` | **一致** | 2026-10-21 17:24 |
| `src/pathway_v43/pollutant/s5b_scoring.py` | `4af3ed2d60f97a3460df92027d2bb2b280b92c5956e81c475ee262cf33549ca3` | `4af3ed2d…` | **一致** | 2026-10-21 17:24 |
| `src/pathway_v43/pollutant/s5b_compiler.py` | `58cf3dc94dd83cbf8245c9e2117ac50f41e847c685663321af973f637fba7058` | `58cf3dc9…` | **一致** | 2026-10-21 17:24 |
| `src/pathway_v43/pollutant/chemstate.py` | `495d3d0e8ad5fb40d7d557a865a51a1e07d8e51f73e8775a6d72f9842861fdeb` | `495d3d0e…` | **一致** | 2026-10-26 15:49 |

### 1.2 最近活动文件

```
find . -newermt "2026-10-27 00:00" -type f \
  -not -path "*/__pycache__/*" -not -name "*.pyc" -not -path "*/runs/*"
```

结果：**空**（生产树内 10-27 00:00 以后无任何文件修改）。

### 1.3 需要注意但不是新改动的事项

`git status --porcelain` 显示以下非暂存差异/未跟踪文件；它们全部早于基线时间点，且当前 `chemstate.py` 哈希与基线一致，属于 2026-10-26 14:25 建立 git index 之后的**基线前遗留**，不是本次漂移：

| 路径 | 状态 | mtime | 判断 |
|---|---|---|---|
| `src/pathway_v43/pollutant/chemstate.py` | `AM`（相对 10-26 index） | 2026-10-26 15:49 | 基线前修改；当前哈希 = 基线 |
| `scripts/hpc/p2_arm_config.json` | `AM`（相对 10-26 index） | 2026-10-26 15:57 | 基线前修改 |
| `src/pathway_v43/pollutant/chemstate.py.bak.fatalfix` | 未跟踪 | 2026-10-21 17:24 | 旧备份 |
| `tests/test_p2_fatal_cn_fix.py` | 未跟踪 | 2026-10-26 15:49 | 基线前新增测试 |
| `tests/test_p2_v1card_mode.py.bak.fatalfix` | 未跟踪 | 2026-10-21 18:13 | 旧备份 |

> 说明：10-28 10:24 对生产树跑 `git status` 时只创建/删除了 `.git/index.lock`，`.git/index` 本身 mtime 仍为 2026-10-26 14:25，无内容变化。

## §2 `v43cP2/.git` 状态

| 项 | 值 |
|---|---|
| `.git/HEAD` | `ref: refs/heads/master` |
| commit 数 | **0（unborn HEAD，与基线一致）** |
| `.git/refs/heads/` | 空 |
| `.git/index` | 2026-10-26 14:25（72354 B，未重写） |
| 新 commit | **无** |

另外发现 `iter/worktrees/coverage_v3/.git` 和 `iter/worktrees/anscard_code/.git`：它们是 10-26 从 `v43cP2` 复制工作树时带过来的同款空仓（`rev-list --count HEAD = 0`，无 commit），不是新开的仓库。`full298`、`probe_compile`、`repair3`、`n004_retro` 没有 `.git`。

## §3 `iter/` 新增内容

### 3.1 新目录/新实验（基线表中未列出）

| 路径 | 时间（CST） | 性质 | 判断 |
|---|---|---|---|
| `iter/worktrees/n004_retro/` | 17:17–18:19 | 新工作树；`code/` 为生产树副本 + n004 补丁 | 正常实验产物 |
| `iter/rounds/n004/` | 17:54–18:19 | n004 stage2 证据：`g2_1..g2_5.json`、`channel_patch.diff`、`stage2_run_evidence.json` | 正常实验产物 |
| `iter/probe/n003/` | 16:23–16:33 | 133 题的 exact-template / reaction 检查 | 正常分析产物 |
| `iter/v4_conservation/` | 16:52–16:58 | 298 题 v4 守恒扫描（code_root=`repair3`，batch=`p2_298_20261026_v1card`） | 正常分析产物 |
| `iter/coverage_v3/`（顶层 harness） | 15:37–17:06 | coverage v3 模拟的 bin/out/logs/data_view/notebook_meta；`code` 软链到 `worktrees/coverage_v3` | 正常分析产物 |
| `iter/mainproduct_table/` | 15:23 | 主产物表 md + rows/summary | 正常分析产物 |
| `iter/audit_mainproduct/` | 11:40–11:51 | 主产物审计脚本与 per-qid/aggregate 结果 | 正常分析产物 |
| `iter/prompt_v2_full.txt` | 10:31 | 提示词文本 | 正常分析产物 |
| `iter/wronged_probe.py/.json` | 11:21 | 错判探针 | 正常分析产物 |
| `iter/extras_probe.py` | 11:44 | 附加探针 | 正常分析产物 |
| `iter/demo_one.json`、`iter/dump_one.py` | 15:35 | 单题样例导出 | 正常分析产物 |
| `iter/flips.json`、`flip_cases.py/.json` | 16:24–16:25 | v2/v4 翻转案例 | 正常分析产物 |

### 3.2 n004 实验要点（从证据文件读到的元信息，未读金标）

- 目的：`retro_template` 通道 stage-2 验证；`domain_tag=298`。
- 性质声明：`zero_model_calls=true`、`zero_paid_calls=true`、`zero_network=true`、`no_commit=true`、`production_read_only=true`。
- 代码：`n004_retro/code/src` 的四个关键文件与生产树**哈希完全一致**；补丁只改 `config.py`、`pollutant/s5b_builder.py`、`storage/run_identity.py`，并新增 `services/retro_source.py`、`services/retro_loader.py`。
- 门禁：`g2_1..g2_5` 全部 `all_pass=true`；三臂 `off / on / on2` 各 298 题全部 `ok`，on 与 on2 的 pool 身份哈希相同（确定性复跑一致）。
- `channel_patch.diff`：1856 行，证据记录其 sha256 为 `68f479ce…`，可 `patch -p1` 干净应用到 `v43cP2/src`。

### 3.3 已知工作树的改动文件

| 路径 | 当前 sha256 | 大小/mtime | 与基线关系 |
|---|---|---|---|
| `worktrees/coverage_v3/src/.../evaluation.py` | `ab098be5d2bf08e278ac40d370bf315b98358f39b929e1c89df71c28bd030c24` | 213202 B / 10-27 15:39 | 基线所述“子代理改 coverage 判定”，有 `out/coverage_v3_applied.diff` 留档 |
| `worktrees/anscard_code/src/.../runflow.py` | `9886a2920453182eeeb5a475f848555ba915e7a68a889be7373559a44a9c7da6` | 119750 B / 10-27 11:16 | 基线所述 oracle_hint 改动（文件内 `oracle_hint` 出现 10 次） |
| `worktrees/anscard_code/src/.../s5b_worker.py` | `fab85684505071ae3d4742f7598352330d77ab9b74f09db2ee2e519b23a9eed8` | 30398 B / 10-27 11:16 | 同上（出现 3 次） |
| `worktrees/repair3/src/.../s5b_compiler.py` | `e89419f5997c8abdfbd9bebc44abd9b5c7f3253b2257d27427fbae00953e5409` | 101693 B / 10-27 02:55 | 工作树本地改动；生产树未受影响 |
| `worktrees/repair3/src/.../chemstate.py` | `495d3d0e…`（同生产） | 44647 B / 10-26 15:49 | 未改 |

`full298`、`probe_compile` 目录 mtime 仍为 10-26，无新改动。`iter/bin/replay.py` 未变（`3d2a3a5a…`，10-26 14:35）；`iter/data/r2` 未变（外层 10-26，内部资产 10-20）。

## §4 新批根 / 新 run

| 位置 | 状态 |
|---|---|
| `ppv1_hpc/batch/` | **无新批根**。仍是基线已知的 P2 两臂 + `anscard_diag_20261027`（11:17 完成报告）+ `anscard_seed_20261027`（12:07 写出 batch_manifest/build_identity/split_manifest/run_inputs/reference_graphs） |
| `ppv1_hpc/runs/` | 新增 `runs/anscard_diag_20261027/`，仅 `trial2_summary.json`（11:14）和 `trial3_summary.json`（11:17）；体量极小，属诊断输出 |
| P2 298 新 run | **无**。`p2_298_20261026_v1card`、`p2_298_20261026_v2card` 的 mtime 仍为 10-26 |

> 未读取 `anscard_seed_20261027/reference_graphs` 或任何 `env/` 内容，只做了目录/文件名与时间核对。

## §5 进程与磁盘

| 项 | 观测 |
|---|---|
| 计算/评测进程 | **无**（没有 python 跑批、没有 compile/scoring 任务） |
| 常驻进程 | jupyter-lab（PID 50，已 2 天）、ZCode server（PID 116/127，已 2 天）、`zcode-cli` 父进程 171（已 2 天） |
| 今晨新进程 | 4 个 `zcode-cli` 子进程（PID 65841/65848/65855/65864，PPID=171，10-28 10:15 启动，cwd=`/`），属 notebook 侧 ZCode 服务会话，不是计算任务；未产生业务文件写入 |
| SSH | 除本次审计连接外无交互登录（`who` 为空）；PID 89 的 `root@notty` 是已存在两天的无 pty 会话/隧道 |
| 磁盘 | `/` 1.8T，已用 602G，可用 1.1T，使用率 **37%** |

## §6 与给定基线的差异清单

| # | 路径 | 旧 → 新（哈希/时间） | 判断 |
|---|---|---|---|
| 1 | `v43cP2/src/.../{evaluation,s5b_scoring,s5b_compiler,chemstate}.py` | 四个哈希与基线完全相同；mtime 仍为 10-21/10-26 | **改动：无** |
| 2 | `v43cP2` 全树 10-27 00:00 后文件 | 无 | **改动：无** |
| 3 | `v43cP2/.git` | unborn → unborn，0 commit | **无变化**（无新 commit） |
| 4 | `v43cP2` 的 `AM chemstate.py` / `AM p2_arm_config.json` / `*.bak.fatalfix` / `test_p2_fatal_cn_fix.py` | 10-26 15:49/15:57、10-21 | 基线前遗留（index 快照较旧），非新漂移 |
| 5 | `iter/worktrees/n004_retro`、`iter/rounds/n004` | 基线表中没有 → 10-27 17:17–18:19 | **新增**：正常实验产物（gates 全过、298 题三臂 ok） |
| 6 | `iter/probe/n003` | 基线只有 n001 → 10-27 16:23–16:33 | **新增**：正常分析产物 |
| 7 | `iter/v4_conservation` | 基线没有 → 10-27 16:52–16:58 | **新增**：正常分析产物 |
| 8 | `iter/coverage_v3`（顶层）+ `out/` | 基线只列了 `worktrees/coverage_v3` → 15:37–17:06 | **新增产物**；evaluation.py 改动属基线已知子代理改动 |
| 9 | `iter/mainproduct_table`、`audit_mainproduct` | 基线没有 → 11:40–15:23 | **新增**：正常分析产物 |
| 10 | `iter/` 根下 `prompt_v2_full.txt`、`wronged_probe*`、`extras_probe.py`、`demo_one.json`、`dump_one.py`、`flips.json`、`flip_cases*` | 基线没有 → 10:31–16:25 | **新增**：正常分析产物 |
| 11 | `iter/anscard/` | 基线已列该目录；新增 `feasibility.json`、`oracle_hints.json`、`bin/*`、`logs/build.log`（11:09–12:07） | 已知目录的**正常构建产物**（`oracle_hints.json` 只核对了路径/大小，未读内容） |
| 12 | `iter/rounds/r002`、`iter/probe/n001` | 基线已列；子目录/阈值产物 mtime 10-27 00:57–01:13 | 基线目录的**正常收尾产物** |
| 13 | `worktrees/repair3/src/.../s5b_compiler.py` | 生产 `58cf3dc9…`/90609 B → `e89419f5…`/101693 B，10-27 02:55 | 工作树本地改动，**未进入生产树** |
| 14 | `worktrees/coverage_v3/src/.../evaluation.py` | 生产 `37c09231…` → `ab098be5…`，10-27 15:39 | 基线已知改动的落盘确认 |
| 15 | `worktrees/anscard_code/{runflow,s5b_worker}.py` | 生产对应文件 → `9886a292…`/`fab85684…`，10-27 11:16 | 基线已知 oracle_hint 改动的落盘确认 |
| 16 | `ppv1_hpc/batch/` | 无新目录；anscard_seed 内容写到 12:07 | **无新批根**，正常构建产物 |
| 17 | `ppv1_hpc/runs/anscard_diag_20261027` | 基线未列 runs → 11:14–11:17，仅 2 个 summary | **新增诊断 run**，非 P2 正式 run |
| 18 | `.git` 目录/index 的 10-28 10:24 mtime | 无 → 本次审计 | **审计副作用**：`git status` 刷新 stat 缓存（`anscard_code/.git/index` 被重写 stat 信息）；无 tracked 内容变化、无 commit |

### 结论性判断

1. 没有任何证据表明生产树被改：四个关键哈希全对，10-27 起零文件改动，无新 commit。
2. 10-27 白天到傍晚有人（或某个会话）在 `iter/` 下做了大量**只读/实验性**工作，最后落点是 n004 stage-2 实验（18:19 完成，门禁全过）。
3. 10-27 18:19 之后到本次核查（10-28 10:23）**没有任何业务文件写入**；昨天的工作已自然结束，没有遗留进程。
4. 唯一需要留意的“写”是本次审计自身触发的 git index stat 缓存刷新（§6 #18），不涉及代码内容。

## 附录：核查命令（均为只读，除 `git status` 的 index stat 刷新）

```bash
sha256sum src/pathway_v43/pollutant/{evaluation.py,s5b_scoring.py,s5b_compiler.py,chemstate.py}
find . -newermt "2026-10-27 00:00" -type f \
  -not -path "*/__pycache__/*" -not -name "*.pyc" -not -path "*/runs/*"
git -C . status --short | head -30
git -C . log --oneline -5
ls -lt iter/ | head -20
ls -lt iter/worktrees/ | head
find iter -maxdepth 2 -newermt "2026-10-27 00:00" -type d | head -20
ls -lt ppv1_hpc/batch/ | head -10
ls -lt ppv1_hpc/runs/ | head -10
ps -eo pid,etime,cmd --sort=-etime | grep -vE "grep|ps -eo" | head -15
df -h / | tail -1
```

补充核对：`git --no-optional-locks ... status --porcelain`、`sha256sum` 工作树改动文件、`diff -rq v43cP2/src n004_retro/code/src`、读取 `iter/rounds/n004/stage2_run_evidence.json` 与 `g2_*.json` 的汇总字段。