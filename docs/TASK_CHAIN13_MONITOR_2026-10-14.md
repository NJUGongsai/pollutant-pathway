# TASK — 三臂跑批监控值夜（catjam-coder，2026-10-14 夜）

> 派单：主窗口。执行：catjam-coder（cat-jam-free）。
> **本任务是纯监控：零代码改动、零 git 操作（不 commit 不分支）、
> 不动任何批根文件、不 scancel 任何作业、SSH 密钥零打印。**
> 你只做三件事：轮询读状态、按决策表机械行动、异常/收口时写报告返回。

## 一、被盯对象（三臂，全部已发车）

| 臂 | run 作业 | 批根 | runs 根 |
|---|---|---|---|
| GLM | 46560173（RUNNING） | `$WS/batch/chain13_s5b_20261014` | `$WS/runs/chain13_s5b_20261014` |
| qwen | 46567748 | `$WS/batch/chain13q_s5b_20261014` | `$WS/runs/chain13q_s5b_20261014` |
| ds | 46567752 | `$WS/batch/chain13d_s5b_20261014` | `$WS/runs/chain13d_s5b_20261014` |

`$WS` = `/work/home/aclhl3hbth/ppv1_hpc`。HPC 连接：
`ssh -i ~/.ssh/hpc_wuzh02_key -p 65091 -o BatchMode=yes -o ConnectTimeout=20 aclhl3hbth@wuzh02.hpccube.com '<命令>'`
（输出里的 perl locale 警告是噪声，忽略。）

## 二、轮询循环（每 20 分钟一次）

```bash
ssh ... '
squeue -u $USER -h -o "%i %j %T %M"
sacct -j 46560173,46567748,46567752 -n --format=JobID,JobName%14,State,Elapsed | grep -v "\."
for b in chain13 chain13q chain13d; do
  C=$(ls /work/home/aclhl3hbth/ppv1_hpc/batch/${b}_s5b_20261014/cases 2>/dev/null | wc -l)
  F=$(grep -l "\"status\": \"failed\"" /work/home/aclhl3hbth/ppv1_hpc/batch/${b}_s5b_20261014/cases/*.json 2>/dev/null | wc -l)
  echo "$b: cases=$C/298 failed=$F"
done
'
```

每轮把结果追加到本地日志 `/tmp/chain13_monitor.log`（Mac 侧）。
轮与轮之间 `sleep 1200`。

## 三、决策表（机械执行，零自由裁量）

| 观测 | 动作 |
|---|---|
| 三臂任一 run 状态 = RUNNING/PENDING | 记录，继续下一轮 |
| **某臂 run COMPLETED 且该臂 cases=298** | **提交该臂 score 作业**（命令见 §四），记录新作业号，继续轮询（盯 score） |
| 某臂 run COMPLETED 但 cases<298 | **异常 → 写报告退出** |
| 某臂 run 状态 = FAILED / CANCELLED / TIMEOUT | **异常 → 写报告退出** |
| 某臂 score 状态 = RUNNING/PENDING | 记录，继续 |
| **某臂 score COMPLETED 且该臂批根下 metrics.json 与 metrics.json.v1 都存在** | 该臂收口 ✓，继续盯剩余臂 |
| 某臂 score FAILED | **异常 → 写报告退出** |
| **三臂全部收口 ✓** | **写最终报告退出**（§五格式） |
| 轮询超过 30 轮（约 10 小时）仍未收口 | 超时 → 写状态报告退出 |

**异常退出 = 立即停止循环，把当时的三臂状态、异常臂的作业号与状态、
最后 5 轮轮询日志写进报告返回。不做任何修复尝试。**

## 四、score 作业提交命令（某臂 run 完成时逐臂执行）

```bash
ssh ... '
cd $HOME/EnzymeAgent/v43c13
# <ARM> 替换为该臂前缀（chain13 / chain13q / chain13d）
sbatch --parsable -J <ARM>-score -o $HOME/ppv1_hpc/slurm-logs/v43_%x-%j.out \
  BATCH_ROOT=/work/home/aclhl3hbth/ppv1_hpc/batch/<ARM>_s5b_20261014 \
  RUNS_ROOT=/work/home/aclhl3hbth/ppv1_hpc/runs/<ARM>_s5b_20261014 \
  scripts/hpc/sbatch_chain13_score.sh
'
```
注意：环境变量要放在 `sbatch` 命令**前面**（BATCH_ROOT=... RUNS_ROOT=... sbatch ...），
与上面示例一致。记下返回的作业号用于后续轮询（sacct 加上它）。

## 五、最终报告格式（三臂收口后）

1. 三臂 score 作业号与状态；
2. 每臂判分产物核对：`metrics.json`（v2 headline）与 `metrics.json.v1`
   （敏感性）是否存在、文件大小；
3. 每臂 cases 总数与 failed 数（从批根统计）；
4. 完整轮询日志的关键行摘要（里程碑时间点）；
5. 声明：零代码改动、零 git 操作、未动批根、未取消任何作业。

## 六、红线（违反即事故）

- 不改任何文件（除 /tmp/chain13_monitor.log）；
- 不 git commit / branch / merge；
- 不 scancel、不 scancel、不 scancel；
- 不碰批根内容、不碰 env 文件、不打印任何密钥；
- 异常不处置只报告；
- SSH 失败连续 3 次 → 记录后继续（网络抖动）；连续 5 次 → 异常报告退出。
