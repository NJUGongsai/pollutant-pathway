# 乌镇 HPC（wuzh02.hpccube.com）只读侦察报告（补全版）

- 日期：2026-10-12（上轮密钥未注册全项未测；本轮专用密钥到位后补全实测）
- 侦察方式：Mac 经 ssh（密钥 `/tmp/wuzh_key`，来源
  `~/Downloads/aclhl3hbth_wuzh02.hpccube.com_RsaKeyExpireTime_2026-11-30_*.txt`，
  chmod 600；密钥内容零打印零落盘）；目标 wuzh02.hpccube.com:65091，用户
  aclhl3hbth。登录验证轮落在 login03，本轮命令落在 login05（登录节点池轮转，
  均可认证）。
- 侦察执行：2 个 1 分钟级 srun 侦察作业（网络验证是任务核心，任务书明示
  允许）；未安装任何包、未改任何配置、未触碰本仓 src/tests；作业后远端
  侦察脚本已删除、队列已清空。
- 上轮结论（红：Permission denied）已被本轮推翻：专用密钥已在该站注册，
  SSH 认证成功，全部 6 项清单实测完成。

---

## 0. 可行性总判：绿（可直接进入 10 题验批）

六项清单全部实测通过，且上次 zzeshell 的硬阻塞项（分区授权）在本站**不
存在**：账号关联已建好、分区白名单已含本账号、`sbatch --test-only` 通过、
真实 srun 作业秒级起跑并 COMPLETED。**计算节点外网直连 dashscope 通**
（拿到 API 网关正式 JSON 应答），rdkit 可经 pip 安装（dry-run 证实），
登录/计算节点共享同一 /work 家目录。

---

## 1. 基础（实测）

```
$ hostname ; whoami
login05 / aclhl3hbth
$ uname -a
Linux login05 3.10.0-957.nfs.5.x86_64 #1 SMP Wed Apr 28 13:46:32 CST 2021 x86_64 ... GNU/Linux
$ cat /etc/os-release | head -4
NAME="NFS Server"   VERSION="3.2 (RTM1)"   ID="NFS"   HOME_URL="http://www.nfschina.com"
$ lscpu | grep -E "Architecture|Model name|^CPU\(s\)|Socket|NUMA node"
Architecture: x86_64    CPU(s): 64    Thread(s) per core: 1
Core(s) per socket: 32   Socket(s): 2   NUMA node(s): 2
Model name: Hygon C86 7285 32-core Processor    CPU MHz: 2000.000
$ free -g
Mem: 251 total / 41 used / 205 available
$ id
uid=18950(aclhl3hbth) gid=72676(aclhl3hbth) groups=72676(aclhl3hbth),39(video),10002(sothisai)
```

结论：登录节点 **Hygon C86 7285（x86_64，海光）**，64 核 2 路，251G 内存。
OS 为曙光系 "NFS Server 3.2"。计算节点 CPU 同款（见 §4 实测）——任务书
提示"乌镇可能非海光"不成立，本站登录+计算节点均为海光 x86_64。

## 2. 调度器与权限（重点，实测全绿）

### 2a. 分区与节点

```
$ srun --version
slurm 22.05.8-2.3.2-102-20250620
$ sinfo -s
PARTITION  AVAIL  TIMELIMIT   NODES(A/I/O/T) NODELIST
wzhcnormal    up 333-08:00:  3990/342/304/463  a01r1n[...]...k06r4n[...]
$ scontrol show partition | grep -E "AllowGroups|AllowQos|MaxTime|MaxNodes"
   AllowGroups=ALL AllowAccounts=<长名单，含 aclhl3hbth（见 2b）> AllowQos=ALL
   MaxTime=333-08:00:00  MaxNodes=UNLIMITED
$ sinfo -N -o "%P %N %C %T %m %f" | head -3
wzhcnormal a01r1n01 32/0/0/32 allocated 126536 32core
```

- 全站**单一分区 wzhcnormal**：463 节点（3990 核在用 / 342 节点空闲 /
  304 节点 drain 等），墙钟上限 333 天，节点规格 32 核 / ~123G 内存，
  feature `32core`。
- 空闲节点充足（侦察时点 342 台 idle）。

### 2b. 账号白名单（机器证据）

```
$ sacctmgr -n show assoc user=aclhl3hbth -P
clus_wz|aclhl3hbth|aclhl3hbth||1|||||||||||||user_aclhl3hbth||
$ grep -o ",aclhl3hbth," <scontrol show partition 输出>
,aclhl3hbth,        ← 命中：账号 aclhl3hbth 在 wzhcnormal 的 AllowAccounts 白名单内
$ sacctmgr -n show qos user_aclhl3hbth format=... -P
user_aclhl3hbth||||||      ← QOS 存在，无显式限制（grptres/maxtres/maxjobs/maxwall 全空）
```

- 关联：cluster `clus_wz`，account=user=aclhl3hbth，QOS `user_aclhl3hbth`
  **无显式核数/时长/并发限额**（分区级 MaxNodes=UNLIMITED、AllowQos=ALL）。

### 2c. 提交权限实测（三连过 + 真实作业）

```
$ sbatch --test-only -p wzhcnormal -N 1 -n 1  -t 1:00     --wrap "hostname"
sbatch: Job 46336245 to start at 2026-10-15T08:13:33 using 1 processors on nodes e09r4n15 in partition wzhcnormal
$ sbatch --test-only -p wzhcnormal -N 1 -n 32 -t 1:00     --wrap "hostname"
sbatch: Job 46336249 to start ... using 32 processors on nodes a01r4n17 in partition wzhcnormal
$ sbatch --test-only -p wzhcnormal -N 1 -n 1  -t 48:00:00 --wrap "hostname"
sbatch: Job 46336267 to start ... using 1 processors on nodes a01r2n11 in partition wzhcnormal
```

⚠️ 注：`--test-only` 预测的 2026-10-15 起跑是调度器保守模拟值；**真实
srun 作业秒级起跑**（下条），以实测为准。

### 2d. 真实作业实测（1 分钟侦察作业 ×2）

```
$ srun -p wzhcnormal -N 1 -n 1 -t 2:00 --immediate=90 hostname
srun: job 46336637 queued and waiting for resources
srun: job 46336637 has been allocated resources
e09r3n02
$ sacct -X -u aclhl3hbth -S 2026-10-12 -o JobID,State,Elapsed,ExitCode -P
46336637|COMPLETED|00:00:04|0:0
46336692|COMPLETED|00:00:02|0:0
```

两次 1 核作业均在数秒内分配资源并正常退出（耗时 4s / 2s 含程序本身）。
**1 核小作业排队等待 ≈ 秒级**，无需排队预估。

### 2e. 队列可见性

`squeue`（不带 -u）仅返回表头——站点设了 PrivateData，普通用户看不到
全局队列深度；本用户名下作业为空。队列量级以 sinfo 节点占用为代理：
3990 核在用 / 342 节点空闲（§2a）。

## 3. Python（实测）

```
$ which python3 / python3 --version
/work/home/aclhl3hbth/anaconda3/bin/python3
Python 3.12.4
$ pip3 --version
pip 24.0 (python 3.12)
$ which conda
/work/home/aclhl3hbth/anaconda3/bin/conda
$ pip3 install --user --dry-run rdkit   # 未真装
Collecting rdkit
  Downloading rdkit-2024.3.2-cp312-cp312-manylinux_2_17_x86_64...whl (35.2 MB)
  ━━━ 35.2/35.2 MB 10.8 MB/s
Requirement already satisfied: numpy (1.26.4) / Pillow (10.3.0)
Would install rdkit-2024.3.2
```

- 用户自带 anaconda3（在 /work 家目录，登录/计算节点同盘共享，计算节点
  上 `python3 -c` 实测可用，见 §4）。
- **rdkit 安装路径畅通**：PyPI 可达、cp312 manylinux x86_64 wheel 在架、
  依赖 numpy/Pillow 已就位，下载 10.8 MB/s。一条
  `pip3 install --user rdkit` 即可（本轮未真装，遵守零改动约定）。
- module 体系：`/public/software/modules` 有数百个应用模块（大量
  `-DCU2` 海光 DCU GPU 版本：Gromacs/Lammps/NAMD/AutoDock 等，另有
  anaconda3/5.2.0、各编译器 MPI）；验证批走自带 anaconda 即可，无需 module。

## 4. 网络出口（生死题，实测：登录+计算节点均通）

### 4a. 登录节点

```
$ curl -s -o /dev/null -w "..." -m 10 https://dashscope.aliyuncs.com
http_code=404 time=0.190915s          ← 根路径 404 = 网关应答，链路通
$ curl -s -m 15 https://dashscope.aliyuncs.com/compatible-mode/v1/models
{"error":{"message":"You didn't provide an API key. You need to provide your API key in an Authorization header using Bearer auth (i.e. Authorization: Bearer YOUR_KEY). ","type":"invalid_request_error",...}
http_code=401                          ← dashscope API 网关正式 JSON 应答
$ curl https://www.baidu.com      → http_code=200 (0.14s)
$ curl https://pypi.org/simple/rdkit/ → http_code=200 (0.91s)
```

### 4b. 计算节点（srun 侦察作业，节点 e04r3n02）

```
===COMPUTE_HOSTNAME===   e04r3n02
===COMPUTE_CPU===        Hygon C86 7285 32-core Processor / x86_64 / 32 CPU / 4 NUMA
===COMPUTE_MEM===        123G total / 87G available
===COMPUTE_PY===         /work/home/aclhl3hbth/anaconda3/bin/python3 → 3.12.4
===COMPUTE_CURL_DASHSCOPE===        http_code=404 time=0.168456s
===COMPUTE_CURL_DASHSCOPE_API===    {"error":{"message":"You didn't provide an API key. ..."},"request_id":"75203ff5-..."}
===COMPUTE_CURL_PYPI===             http_code=200 time=0.728800s
```

**结论：计算节点外网直连可用**——dashscope API 网关在计算节点返回正式
401 JSON 应答（带 request_id），PyPI 200。401/404 是"没带密钥/根路径
无路由"的正常应答，恰证明 TLS+HTTP 全链路通；带上 API key 即可调通。
pypi 在计算节点同样可达（0.73s）。

## 5. 存储（实测）

```
$ mount | grep -E "work|public|home"
ParaStor_01_home on /public type parastor (rw,noatime)
ParaStor_01_work on /work  type parastor (rw,noatime)
$ df -h $HOME          → ParaStor_01_work  3.5T  2.7T  795G  78%  /work
$ df -h /public/software → ParaStor_01_home  471T  332T  140T  71%  /public
$HOME = /work/home/aclhl3hbth
```

- 家目录在 **ParaStor 共享并行文件系统**（曙光 ParaStor，类 Lustre 语义，
  无 lfs 命令、`quota -s` 无输出=无可见配额限制），登录/计算节点同挂载，
  anaconda3 环境跨节点即插即用（已在计算节点实测 python3 可用）。
- 体量：/work 3.5T（余 795G），/public 471T（余 140T，软件库所在）。
  单账户占 /work 全分区的共享池，未观察到用户级硬配额。

## 6. 传输二进制（实测齐备）

```
rsync: /usr/bin/rsync    scp: /usr/bin/scp    sftp: /usr/bin/sftp
curl:  /work/home/aclhl3hbth/anaconda3/bin/curl    wget: /usr/bin/wget
git:   /usr/bin/git
```

rsync/scp/sftp/curl/wget/git 全部在位；Mac 侧推送代码包（rsync over
ssh -p 65091）无障碍。

---

## 7. 结论汇总（五项关键结论）

1. **连通**：✓ 已知——专用密钥注册成功，login03/login05 均可登录（上轮
   红判推翻，原因是上轮用的 zzeshell 钥匙未注册本站，非站点故障）。
2. **分区权限**：**绿**——账号 aclhl3hbth 在唯一分区 wzhcnormal 的
   AllowAccounts 白名单内（机器证据 §2b），QOS 无显式限额，
   `sbatch --test-only` 1/32 核与 48h 墙钟三连过，真实 srun 作业秒级
   起跑并 COMPLETED ×2（§2c/2d）。**可直接进入 10 题验批**。
3. **Python+RDKit 路径**：绿——自带 anaconda3 Python 3.12.4（/work 共享，
   登录+计算节点同环境）；rdkit 2024.3.2 wheel 可装（dry-run 证实，
   依赖齐、10.8MB/s），一条 pip --user 命令即完成。
4. **登录+计算节点外网**：**绿（生死题通过）**——两端 dashscope 均拿到
   API 网关正式 JSON 应答（401 请求密钥，带 request_id），计算节点
   PyPI 亦 200。API-key 调用链路无已知障碍。
5. **存储传输**：绿——家目录在共享 ParaStor（登录/计算同盘，环境即插
   即用），/work 余 795G；rsync/scp/sftp/curl/wget/git 齐备。

### 限制与注意（诚实披露）

- 全局 squeue 不可见（PrivateData），排队量级只能用 sinfo 节点占用代理；
  侦察时点空闲 342 节点，但"验批时点空闲度"需届时再看。
- 实测真实作业只跑过 1 核 ×2（任务书范围）；32 核/长墙钟只有
  --test-only 证据，未跑真实 32 核作业。
- dashscope 只验证到"网关应答"层（401 JSON），未带 key 发真实推理请求
  （不属于只读侦察范围，且密钥不应出现在侦察链路）。
- 计算节点为 Hygon C86 7285 x86_64（与登录节点同款），rdkit manylinux
  wheel 架构匹配；本站另有 DCU（海光 GPU）栈与本次 CPU 验批无关。
- 本轮唯一的远端写动作：2 个 1 分钟 srun 侦察作业 + 1 个临时脚本
  （已删）；作业与脚本零残留（squeue 空、sacct 双 COMPLETED）。
