# 曙光 HPC（zzeshell.scnet.cn）只读侦察报告

- 日期：2026-10-12（侦察执行日）
- 侦察方式：Mac 经 ssh（密钥登录，密钥内容不入本报告）只读执行命令；未提交任何
  sbatch 作业（仅 `sbatch --test-only` 校验与 `srun --immediate` 探测，二者均不
  产生实际作业）；未安装任何包（仅 `pip --dry-run`）；未改任何远端配置。
- 平台：超算互联网（SCNet）华中一区【A区】，登录节点 zz-login02。
- 用途评估对象：298 全量测试管线（Python+RDKit 单机逻辑、40 路进程并发、
  每题一次 HTTPS 调用 LLM API、批根 ~3-4GB）。

---

## 0. 可行性总判：黄（有条件可行）

技术栈全部就绪（连得上、Python 3.12 + pip --user 装 rdkit 验证通过、登录节点
到 dashscope LLM API 端到端 HTTPS 通、PB 级存储、chenyu 直传二进制齐备）；
但**当前账号一个计算作业都提不了**——`aclhl3hbth` 不在任何分区的
AllowAccounts 白名单里，先要在 SCNet 门户开通分区/机时权限，否则整条管线
无法上计算节点。计算节点外网因无作业权限无法实测，风险未排除。

---

## 1. 基础信息（登录节点 zz-login02）

| 项 | 机器输出证据 | 结论 |
|---|---|---|
| 内核/架构 | `Linux zz-login02 5.10.134-17.1.3.sga8.x86_64 ... x86_64` | x86_64，兼容 manylinux wheel |
| OS | `NAME="Sugon OS" VERSION="8.9" ID_LIKE="rhel fedora centos"` | RHEL8 系；glibc `2.28`（`ldd --version`），正好满足 manylinux_2_28 |
| CPU | `CPU(s): 128`，`Model name: Hygon C86-4G (OPN:7495)`，2 插槽 8 NUMA | 登录节点 128 核海光 x86 |
| 内存 | `Mem: 1007 total`（GB） | 1TB 级 |
| HOME | `df -h $HOME` → `scnet.hx:/mnt/public 9.2P ... 41% /public` | 家目录在 9.2PB Lustre（/public），余 5.4P |
| 身份 | `uid=193399(aclhl3hbth) gid=193399(aclhl3hbth)` | 普通用户，无额外组 |
| 计算节点规格 | `sinfo -a -N -o '%N %P %C %m %G'`：如 `a02r1n01 hx1hdnormal01 128/0/0/128 510000 dcu:Hygon:8` | 计算节点 128 核/510GB 内存/8 块海光 DCU；CPU 作业无碍 |
| 登录节点政策 | MOTD：`登录节点用于编译和编辑工作，请勿在登录节点直接运行程序` | 长跑 40 路管线不建议压登录节点（详见 §8） |

## 2. 调度器（Slurm 24.05.8）

- 二进制：`/opt/gridview/slurm/bin/` 下 sbatch/sinfo/squeue/srun/sacctmgr 齐全；
  `sinfo --version` → `slurm 24.05.8-3.1.3-668-20260723`。
- `sinfo`（不带 -a）输出空表 → 分区默认隐藏，`sinfo -a` 可见 14 个分区：
  hx1hdnormal（3 天时限）、hx1hdnormal01（333 天时限）、hx1hdpack、
  hx1hdnormal02、hx1hdexclu02/03/05/06、hx1hdhpc02、hx1hdT、hx1hdnormal03、
  rg_inf、rg_temp、rg_temp2。
- 我的关联（`sacctmgr show assoc user=$USER -P`）：
  `cluster_zz_2|aclhl3hbth|aclhl3hbth||1|||||||||||||user_aclhl3hbth||`
  —— QOS `user_aclhl3hbth` **无任何显式限制**（MaxJobs/MaxTRES/MaxWall 全空），
  关联也未绑定分区。
- **【硬阻塞实锤】账号不在任何分区白名单**：
  - 逐分区 `sbatch --test-only -p <p>` 探测：13/14 分区返回
    `allocation failure: Invalid account or account/partition combination specified`
    （仅 hx1hdnormal02 报分区 drain，那是状态检查先于 ACL 触发）；
    不带 -p 报 `No partition specified or system default partition`（无默认分区）。
  - 根因（读 `/opt/gridview/slurm/etc/slurm_partition.conf`，只读）：
    每个分区用 `PartitionName=xxx AllowAccounts=<长名单>` 控制；
    `grep -c ",aclhl3hbth," slurm_partition.conf` → **0**，
    即我的账号不在 14 个分区任何一个的 AllowAccounts 里。
  - 账号本身未被禁用：不在 `disableAccounts`（7836 行黑名单，未命中），
    也不在 `luaconfig/passUser`/`passPart` 白名单（未命中，白名单是豁免机制）。
  - `sacct -u $USER --starttime 2026-08-01` 无任何历史作业 → 此账号从未跑过作业。
- 结论：**分区别名/QOS 都不是问题，缺的是分区授权**。SCNet 这类平台通常要在
  网页门户申请/购买机时后才把账号加进分区 AllowAccounts（MOTD 引导
  www.scnet.cn 门户与"算力套餐"）。此步只能由用户在门户完成，CLI 侧无法自开通。
- 作业形态参考：家目录自带 `/public/home/aclhl3hbth/job_example/`（serialjob/
  ompjob/mpijob/gpu/dcu + slurmPython.sh 等 30+ 示例）；注意示例里
  `--partition=debug` 在本集群不存在（通用模板，实际要写 `sinfo -a` 里可见的
  分区名）。ompjob 示例：`#SBATCH --cpus-per-task=8` + `export
  OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK`。slurmPython 示例带
  `--mem-per-cpu=2gb`。`squeue` 对普通用户不可见他人作业（输出空表，
  AccessLevel 受限），无法抽样他人作业规模。
- 分区默认内存：job_submit.lua 显示 `DefMemPerCPU=3800`（MB），另有
  partDefMemPerCpuConf 按分区覆盖（如 hx1hdnormal02 DefMemPerCPU=7950）。
  40 路 × 每进程内存需求正常申请即可，未见单作业核数上限（QOS 层无 MaxTRES）。

## 3. Python 环境

| 项 | 机器输出证据 | 结论 |
|---|---|---|
| python3 | `/usr/local/python3.12/bin/python3`，`Python 3.12.6` | 系统 Python 3.12，够新 |
| pip | `pip 25.1.1 from /usr/local/python3.12/...`（python 3.12） | pip 可用 |
| conda | `which conda` → 无；module 有 `anaconda3/2023.09`（=Py3.11）、`anaconda3/5.2.0`、`python/3.8.10` | 有 anaconda 模块可 module load，但非必需 |
| 常用库 | dry-run 依赖解析输出：`Requirement already satisfied: numpy (2.4.0)`、`Pillow (12.0.0)`（系统 site-packages） | numpy/Pillow 已在系统 Python 里 |
| module 体系 | /usr/share/Modules（tclsh），compiler/gcc 9.3–12.2、intel、cmake 等 | 编译链全，本管线用不上 |

## 4. RDKit 可行性（未安装，路径已验证）

- `python3 -c "import rdkit"` → `ModuleNotFoundError: No module named 'rdkit'`（未装）。
- `python3 -m pip install --user --dry-run rdkit` →
  `Downloading rdkit-2026.9.1-cp312-cp312-manylinux_2_28_x86_64.whl (31.8 MB) ...
  Would install rdkit-2026.9.1`。
  —— **PyPI 直连可达（~8.3 MB/s），wheel 选型 cp312/manylinux_2_28/x86_64 与
  系统 glibc 2.28 精确匹配，pip --user 安装路线验证可行，无需 conda 打包传输。**
- 注意坑：`pip install rdkit-pypi` 会报 `No matching distribution found`
  （rdkit-pypi 是已废弃的旧包名），**必须用包名 `rdkit`**。首次误报"找不到版本"
  曾疑似镜像问题，实为包名问题。
- 未真装（遵守侦察红线）；正式跑批时一条
  `pip3 install --user rdkit` 即可（numpy/Pillow 依赖已就位）。

## 5. 网络出口【最关键】

### 5a. 登录节点：外网通，LLM API 端到端可用

- `curl https://www.baidu.com` → `baidu:200`
- `curl https://pypi.org/simple/` → `pypi:200`（根页面 47MB 较慢但可达）
- `curl https://dashscope.aliyuncs.com` 根路径 → `dashscope:404`（404 = TCP+TLS+HTTP 全通，仅路径无内容）
- **端到端 API 实测**（POST 真实生成端点，无 key，看是否返回 API 层应答）：
  `curl -X POST https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation -d '{}'` →
  `{"code":"InvalidApiKey","message":"No API-key provided.","request_id":"2d0a33f6-..."}`
  —— **返回的是 dashscope 服务端的正式 JSON 应答，说明登录节点到阿里 LLM API
  的完整 HTTPS 链路（DNS/TLS/请求路由）全通**，带真 key 即可用。
- 无代理环境变量（`env | grep -i proxy` 为空），是直连出口。

### 5b. 计算节点：无法实测，风险未排除

- 无作业权限（§2 硬阻塞）→ 没有任何办法在计算节点上执行命令：
  - `srun --immediate -t 1 ...` 各分区全部被拒（同 sbatch 错误）；
  - 登录节点 `ssh a02r1n01` 直连计算节点 → 
    `Access denied by pam_slurm_adopt: you have no active jobs on this node`
    （节点 SSH 严格绑定活跃作业，绕不过）。
- 文档旁证未找到：本地 /usr/share/doc/slurm* 无外网说明；SCNet 在线手册
  （www.scnet.cn/help/docs）为 JS 渲染 SPA，curl 抓不到正文（仅 169 字节壳）。
- **如实标注：计算节点外网"未能实测，风险未排除"**。开通分区权限后，第一个
  侦察作业应先跑 `curl dashscope` 验证计算节点出口（1 分钟即可闭环），再决定
  管线是在计算节点直调 API、还是改走"登录节点代理转发"方案。

## 6. 存储与传输

| 项 | 机器输出证据 | 结论 |
|---|---|---|
| 家目录 | /public（Lustre，9.2P，余 5.4P），`test -w` 可写 | 3-4GB 批根放家目录毫无压力 |
| 大容量共享 | `/work2`（9.4P，余 4.8P，**drwxrwxrwx 全局可写**）；/work1 21P（根不可写）；/work5 1.6P（不可写）；/data 3.5T 本地 NVMe（不可写）；另有 /slurm_share | 需要大暂存时用 /work2 |
| Mac→HPC 直传 | 本次 ssh/scp 通道即证明（`ssh -p 65032` 直连成功） | rsync -e ssh 可直推批根 |
| chenyu→HPC 直传 | 登录节点 `which`：`/usr/bin/curl wget ssh rsync scp sftp` 全有 | chenyu 侧可 ssh/rsync/scp 直传 HPC，或走 HTTP 中转，二进制条件齐备 |

## 7. 298 管线适配要点（基于以上事实）

- 运行位置：必须 sbatch 到分区（建议 hx1hdnormal01 或 hx1hdnormal，128 核节点
  一个节点内跑 40 路进程绑 --cpus-per-task=40 或 --ntasks=40 皆可，示例脚本
  已有范式）——**前提是先拿到分区授权**。
- Python：直接用系统 /usr/local/python3.12（numpy/Pillow 现成），作业脚本里
  `pip3 install --user rdkit` 一次（或先在登录节点装好 --user 落家目录，家目录
  Lustre 计算节点同挂载可见）。
- LLM 调用：登录节点已证明 dashscope 端到端通；计算节点出口待分区授权后
  首个作业验证；不通则退路是登录节点跑一个本地反代/任务队列进程，计算节点
  经内部网回连登录节点（登录节点与计算节点同为 10.x 内网，DNS 互通已由
  `ssh a02r1n01` 解析成功佐证）。
- 不建议在登录节点直接跑 40 路长管线：MOTD 明文"请勿在登录节点直接运行程序"，
  且登录节点资源公共共享；短时冒烟可以，全量跑批有账号风控风险。

## 8. 红线执行情况（自证）

- 未提交任何 sbatch 作业：仅 `sbatch --test-only`（不产生作业）与
  `srun --immediate`（资源被拒，未执行任何远端命令）；`sacct -u $USER` 历史
  作业数 0 可复核。
- 未安装包：pip 仅 --dry-run（缓存里落了 wheel，属 pip cache 副作用，未写入
  site-packages）；未改任何远端配置/文件（仅 cat/grep 只读）。
- 密钥内容未打印、未落盘；本报告不含密钥任何片段。
- 未动本仓 src/tests；本报告为唯一落盘文件。

## 附：关键证据命令清单（复跑用）

```
ssh -i <key> -p 65032 aclhl3hbth@zzeshell.scnet.cn "<cmd>"
  uname -a; cat /etc/os-release | head -3; lscpu | head; free -g; df -h $HOME
  sinfo -a | head -40; sbatch --test-only -p hx1hdnormal --wrap=hostname
  sacctmgr show assoc user=$USER -P; sacctmgr show qos -P | grep user_aclhl3hbth
  grep -c ",aclhl3hbth," /opt/gridview/slurm/etc/slurm_partition.conf   # → 0
  python3 --version; python3 -m pip --version
  python3 -m pip install --user --dry-run rdkit                          # → Would install rdkit-2026.9.1
  curl -sS -m 10 https://www.baidu.com -o /dev/null -w '%{http_code}'    # → 200
  curl -sS -m 10 -X POST https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation -H 'Content-Type: application/json' -d '{}'   # → InvalidApiKey JSON（链路通）
  timeout 30 srun --immediate -t 1 -p hx1hdnormal hostname               # → Invalid account or account/partition combination
  ssh a02r1n01 hostname                                                   # → pam_slurm_adopt 拒绝
  df -h | grep -vE 'tmpfs|devtmpfs'; ls -ld /work2; which curl ssh rsync scp
```
