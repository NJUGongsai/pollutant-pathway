# Notebook 环境事实固化（2026-10-26 只读探测）

> **题域标签：不涉分数。** 本文档只固化 SCNet notebook 的环境事实（硬件/出网/生命周期/资产），
> 无任何评测数字，无题域外推问题。
> **采集方式：只读 SSH 探测**（cat/ls/grep/ps/curl），未在 notebook 写任何文件、未 kill、
> 未装包、未重启。凭证/令牌一律打码，本文档不含任何密钥。
> 配套资产：`scripts/hpc/nb_ssh.sh`（两跳 SSH 封装）、`scripts/hpc/notebook_env_proxy.sh`（代理激活）。
> 上游文档：`docs/NOTEBOOK_MIGRATION_2026-10-23.md`（迁移与 10-23 环境基线）、
> `docs/TASK_P2_NOTEBOOK_B_2026-10-26.md`（§1 当日现状事实）。

## 0. 结论表

| 项 | 结论 | 依据 |
|---|---|---|
| 本机→notebook 连通 | **通（两跳：本机→HPC wuzh02→notebook）**；本机没有 `~/.ssh/id_ed25519_nb`（该密钥在 HPC 上） | §5 实测 |
| 直连外网 | **不通**（baidu/dashscope 均超时 rc=28） | §2 实测 |
| 裸代理 `10.16.1.51:3128`（不带凭据） | **不可用**（HTTP 407，代理要求认证） | §2 实测 |
| 带凭据代理（平台 bashrc/ai_proxy 里的值） | **通**（baidu 200；dashscope 404=可达） | §2 实测 |
| 代理激活方式 | `source scripts/hpc/notebook_env_proxy.sh`（解析平台文件，幂等，凭据不落仓） | §2/§5 实测 |
| Slurm / tmux / screen / at | **全无**；setsid、nohup 可用 | §3 实测 |
| systemd | PID 1 是 `sh`（容器 init），**systemd 非 init**；systemctl 二进制存在但无 systemd 可管 | §3 实测 |
| 长任务方案 | nohup/setsid + PID + 日志 + 状态文件（10-23 build 49m13s 先例） | §3，实测见 10-23 文档 |
| `/root/v43_migration` | **在**：700 root:root，1.7G，`scripts/run_local.sh` 在位 | §4 实测 |
| 并发占用 | notebook 上有**另一个 ZCode server 在跑**（另一窗口会话），探测时无用户批任务 | §3 实测 |

## 1. 硬件与软件事实

探测时间 2026-10-26 11:00（notebook 时区）。除注明外均为本次实测。

| 项 | 实测值 | 命令 |
|---|---|---|
| 主机名 | `crdnotebook-2113560935535583233-aclhl3hbth-81040` | `hostname` |
| 内核 | `Linux ... 5.15.0-25-generic #25 SMP Wed Sep 4 16:01:38 CST 2024 x86_64` | `uname -a` |
| CPU 核数 | 128 | `nproc` |
| 内存 | 503 GiB 总量；available 425 GiB；Swap 0 | `free -g` |
| 根盘 | overlay 1.8T，used 400G，**avail 1.3T**（10-23 文档记 728G 空闲，实例重建后已重置） | `df -h /` |
| 内核 uptime | 34 天（宿主机口径） | `uptime` |
| 容器(PID 1) 年龄 | **约 1 小时**（11:00 时 etime=01:08:37，即当日 ~09:52 启动/重启） | `ps -eo pid,etime,cmd --sort=-etime` |
| Python | 3.11.9 | `python3 -V` |
| RDKit | 2026.03.5 | `python3 -c "import rdkit;print(rdkit.__version__)"` |
| `ulimit -n` | 1048576 | `ulimit -n` |
| CPU 型号 | Hygon C86（引用 10-23 文档 §3，本次未重测 `/proc/cpuinfo`） | 引用 |

注：CPU 型号与依赖清单（numpy/pandas/langgraph/lightgbm 等）以 10-23 迁移文档 §3 为准，
本次未逐一重测；Python/RDKit 两项已重测同值。

## 2. 出网与代理

### 2.1 直连 vs 代理 curl 对照（2026-10-26 实测，均不带 key、不调 API）

| 路由 | 目标 | http_code | curl rc | 耗时 | 判定 |
|---|---|---|---|---|---|
| 直连（unset 全部 proxy 变量） | `https://www.baidu.com` | 000 | 28 | 11.4 s | **不通**（连接超时） |
| 直连 | `https://dashscope.aliyuncs.com` | 000 | 28 | 14.1 s | **不通**（连接超时） |
| 裸代理 `http://10.16.1.51:3128`（无凭据） | baidu | 407 | 56 | 0.09 s | **不可用**（代理要求认证） |
| 裸代理（无凭据） | dashscope | 407 | 56 | 0.09 s | **不可用**（同上） |
| 带凭据代理（值取自平台文件） | baidu | 200 | 0 | 0.16 s | **通** |
| 带凭据代理 | dashscope | 404 | 0 | 0.18 s | **通**（根路径无页面，属可达） |

命令（在 notebook 上执行）：

```bash
curl -sS -m 15 -o /dev/null -w "%{http_code} %{time_total}\n" https://www.baidu.com          # 直连
curl -sS -m 15 -x "http://10.16.1.51:3128" -o /dev/null -w "%{http_code} %{time_total}\n" ... # 裸代理
curl -sS -m 15 -x "$AUTH_PROXY"           -o /dev/null -w "%{http_code} %{time_total}\n" ... # 带凭据代理
```

API 级（带 key）实测见 `docs/TASK_P2_NOTEBOOK_B_2026-10-26.md` §1：带代理后 DashScope 可用
（当日会话实测；本次未重测 API 级，见 §6）。

### 2.2 代理配置来源（两处，同指 `10.16.1.51:3128`，均带认证）

| 来源 | 位置 | 变量 | 生效方式 |
|---|---|---|---|
| 平台托管 | `/root/private_data/.ai_user_info/ai_proxy`（326 B，aclhl3hbth 属主，2026-10-24 18:08） | `http_proxy` / `https_proxy` / `ftp_proxy` / `no_proxy` | 被 `/etc/bashrc:4` 与 `/etc/bash.bashrc:84` `source`——**仅交互 shell 生效** |
| 平台挂载用户 home | `/public/home/aclhl3hbth/.bashrc` 第 21–23 行 | `http_proxy` / `https_proxy` / `ftp_proxy`（无 no_proxy） | 需手动 `source` |

- 代理 URL 形如 `http://***:***@10.16.1.51:3128`（凭据打码；**明文只在 notebook 的上述两个平台文件里，不入仓**）。
- **非交互 ssh exec 的 env 里没有代理变量**（实测 `env | grep -i proxy` 为空）——这正是"每个新会话/子代理都要重新踩坑"的根源：平台只给交互 shell 自动配代理。
- `root` 的 `/root/.bashrc` 第 101 行导出 `SCNET_USER_HOME=/public/home/aclhl3hbth`（平台 init 写入），不直接配代理。
- 脚本化解法（已实测）：`source scripts/hpc/notebook_env_proxy.sh`
  - 探测顺序：`ai_proxy` → `$SCNET_USER_HOME/.bashrc` → `/public/home/aclhl3hbth/.bashrc`；
  - 幂等（二次 source rc=0，不叠加）；`no_proxy` 至少含 `localhost,127.0.0.1`；
  - `nb_proxy_status` 打印打码后的代理与一次连通探测（实测输出 baidu 200 0.195s）；
  - 解析失败直接报错退出，**不回落到裸地址**（裸地址实测 407，写死即坑）。

## 3. 常驻能力与生命周期

| 项 | 实测结果 | 性质 |
|---|---|---|
| Slurm | `sinfo/sbatch/srun` 均不存在 | 实测 |
| tmux / screen / at | 均不存在（`command -v` 无果） | 实测 |
| setsid / nohup | 均存在（`/usr/bin/setsid`、`/usr/bin/nohup`） | 实测 |
| PID 1 | `/bin/sh`（容器 init 脚本：配 sshd、起 jupyter lab、写平台 env）；**systemd 不是 init** | 实测 |
| systemctl | 二进制在 `/usr/bin/systemctl`，`/etc/systemd/system` 有 unit 文件，但容器内无 systemd 在跑——**systemctl 实际不可用（未实测调用，推断+标注）** | 实测+推断 |
| 容器重启 | 当日 ~09:52 PID 1 重启过一次；重启后 `/root/v43_migration`（1.7G）完整无损 | 实测 |
| 平台进程 | jupyter-lab（PID 50，token `sothisai_***` 打码）、sshd、以及 **一个 ZCode server + zcode-cli**（另一窗口会话在用） | 实测 |
| 用户批任务 | 探测时刻无任何用户 python/pytest 进程在跑 | 实测 |
| 长任务先例 | nohup + PID + 日志 + 状态文件：10-23 离线 build 2953 s（49m13s）稳定完成 | 引用 10-23 文档 |

**实例回收风险（如实标注）**：
- 实测到的事实：容器（PID 1）会在实例存活期内重启；重启后 `/root` 数据与平台进程自愈，但**用户 nohup 进程是否能在容器重启后存活——未证实**（本次未做重启实验，也不允许做）。
- 平台对 notebook 实例的最长寿命/回收策略——**未证实**（10-23 主机名 `…-33553` → 10-26 `…-81040`，中间发生过实例重建；任务书记录重建后数据完整）。
- 结论级建议（非事实）：凡跨天任务按"容器随时可能重启"设计——nohup 起跑后落 PID+状态文件，断点续跑逻辑照 10-23 `run_local.sh` 先例。

**安全注意（本次实测发现）**：平台 init（PID 1 命令行）包含改 `/etc/shadow`、写 jupyter token 等敏感操作，`ps -p 1` 输出**含敏感串**；本仓任何文档/日志不得原样转发 PID 1 的完整命令行（本文档已打码）。

## 4. 资产位置与权限

只 stat/ls，未读内容。

| 路径 | 权限/属主 | 大小 | 备注 |
|---|---|---|---|
| `/root/v43_migration` | `drwx------ root root`（700） | 1.7G（`du -sh`） | 迁移根；与任务书"1.7G 完整"一致 |
| `/root/v43_migration/scripts/run_local.sh` | `-rwxr-xr-x aclhl3hbth aclhl3hbth`，6841 B，mtime 2026-10-23 18:42 | — | **属主不是 root**：10-23 文档 §2.1 记 `chown -R root:root`，但该文件系当晚修复后重新上传（晚于 chown）；有执行位，是否影响 run 未验证（§6） |
| `~/.ssh/id_ed25519_nb`（HPC 侧） | `-rw------- aclhl3hbth`，411 B，mtime 2026-10-26 10:04 | — | notebook 私钥在 HPC 上，不在本机；10-26 上午随实例重建更新过 |

## 5. 复现命令

### 5.1 本机 → notebook（两跳 SSH，2026-10-26 实测）

```bash
# 方式一：仓内封装（推荐；HPC 密钥默认 ~/.ssh/hpc_wuzh02_key，实测可用）
bash scripts/hpc/nb_ssh.sh hostname
# 实测输出：crdnotebook-2113560935535583233-aclhl3hbth-81040（rc=0）

# 方式二：裸命令（等价；HPC 密钥路径按实际改）
ssh -i ~/.ssh/hpc_wuzh02_key -p 65091 -o StrictHostKeyChecking=no -o BatchMode=yes \
  aclhl3hbth@wuzh02.hpccube.com \
  "ssh -i ~/.ssh/id_ed25519_nb -p 11009 -o StrictHostKeyChecking=no root@ssh.zzai.scnet.cn '<command>'"
```

注意：
- **本机 `~/.ssh/id_ed25519_nb` 不存在**——旧文档里该密钥指 HPC 侧路径；本机直连方案不存在（除非 CC 另发直连密钥）。
- HPC 登录会打印 perl locale warning（无害）。
- 复杂命令用 `bash -s` 管道方式喂（见 5.3），避免三层引号。

### 5.2 notebook 上激活出网代理（幂等）

```bash
# 在 notebook 的 shell 里（任何非交互会话都要先做这一步）：
source scripts/hpc/notebook_env_proxy.sh   # 仓内脚本上传后；或直接 source 平台文件：
# source /root/private_data/.ai_user_info/ai_proxy    # 平台托管（含 no_proxy）
# source /public/home/aclhl3hbth/.bashrc              # 平台挂载 home（21–23 行）
nb_proxy_status   # 打印打码代理 + 连通探测
```

### 5.3 在 notebook 上跑一段只读脚本（不落文件）

```bash
{ cat your_probe.sh; } | ssh -i ~/.ssh/hpc_wuzh02_key -p 65091 -o StrictHostKeyChecking=no \
  -o BatchMode=yes aclhl3hbth@wuzh02.hpccube.com \
  "ssh -i ~/.ssh/id_ed25519_nb -p 11009 -o StrictHostKeyChecking=no root@ssh.zzai.scnet.cn bash -s"
```

## 6. 未证实项与待办

| # | 项 | 状态 |
|---|---|---|
| 1 | 用户 nohup 进程能否活过容器（PID 1）重启 | 未证实（不做重启实验）；按"不存活"设计 |
| 2 | 平台对 notebook 实例的回收策略/最长寿命 | 未证实；10-23→10-26 间发生过一次实例重建（主机名 33553→81040） |
| 3 | `/root` 数据在实例**重建**（非重启）后的持久化机制 | 未证实机制，仅知 10-26 重建后 `/root/v43_migration` 完整（任务书记录+本次实测在盘） |
| 4 | systemctl 在容器内实际调用是否报错 | 未实测（仅由 PID 1=`sh` 推断不可用） |
| 5 | DashScope/GLM **API 级**（带 key）出网 | 本次只测无 key 连通（200/404）；API 级可用性引用 10-26 任务书 §1 当日实测，未重测 |
| 6 | `run_local.sh` 属主为 aclhl3hbth（非 root）对执行的影响 | 未验证（有 x 位；10-23 修复后曾跑通 build） |
| 7 | 两个平台代理文件里的凭据是否同值 | 未比对（只确认同指 `10.16.1.51:3128`；值不打印） |
| 8 | `nb_ssh.sh --put` 两跳上传 | 代码就绪、`bash -n` 通过；**未远端实测**（红线：本次禁写 notebook 任何文件） |

## 变更记录

- 2026-10-26：初版，基于当日只读探测（探测人：ZCode 子代理，CC 派单）。
