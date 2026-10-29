# HPC CPU 镜像需求说明（给集群运维/镜像制作同事）

- 日期：2026-10-22
- 用途：在曙光/SCNet 集群上运行我们的 **298 题酶学推理管线**（`pathway_v43`）
- 结论先行：**纯 CPU 任务，不需要 GPU / CUDA / DCU / PyTorch**。
  只需要一个带 Python 3.11 的 Linux 环境 + 下列 pip 包 + 能出网访问模型 API。
- 本文件不含任何密钥、题面、标准答案；可直接外发。

---

## 0. 一句话版（TL;DR）

> 请基于 **CPU 镜像**给我们做一个 Python 3.11 环境：装好附录 A 的 pip 包，
> 加上 `libgomp1 / libsqlite3 / ca-certificates / util-linux(flock)` 等系统包；
> 作业规格按 **64 核 / 32–64 GB 内存 / 无 GPU / 24 小时**；
> 计算节点需能 **出站 HTTPS 443** 访问模型 API。
> 推荐现成镜像：**`vscode`（CPU 版）**，因为它自带 Python 开发环境；
> 若你们愿意按清单做干净镜像，用 **`custom`** 更好。

---

## 1. 镜像选择（我们这边的建议）

| 镜像 | 是否合适 | 说明 |
|---|---|---|
| `vscode`（CPU） | **首选（现成可用）** | 自带 Python 开发环境和终端，我们再 `pip install` 补齐依赖即可 |
| `custom`（CPU） | **有条件首选** | 如果你们能按本文件第 3–5 节构建干净镜像，这个最合适、体积最小 |
| `pytorch`（CPU） | 不建议 | 我们代码里没有一行 torch；多装一套深度学习栈只会增大镜像、增加依赖冲突 |
| `tensorflow-serving` / `tensorboard` / `rstudio` / `mongo` | 不适用 | 与我们的任务无关 |

如果只能从现成镜像里选：**选 `vscode` CPU**。
如果可以先确认镜像内 Python 版本：必须是 **3.11.x**（3.10 勉强可用但不建议，3.8/3.9 不行）。

---

## 2. 工作负载说明（帮助你们判断资源）

| 项 | 实际情况 |
|---|---|
| 任务类型 | 化学信息学规则计算 + 调用外部大模型 API，**无训练、无推理框架、无 GPU 计算** |
| 主要 CPU 工作 | RDKit 分子图解析/匹配/反应枚举（单进程，CPU 密集） |
| 并发方式 | 多进程（每个作业 8–20 个 worker），进程间用文件锁协调 |
| 主要耗时 | 等模型 API 返回（网络往返），不是本地计算 |
| GPU | **完全不用**；显存占用为 0 |
| 单作业墙钟 | build 约 1 小时；跑题 2–4 小时；判分分钟级 |
| 单作业资源 | 最低 12 核 / 32 GB；建议 24 核 / 64 GB（与现有作业一致） |
| 存储 | 读写共享家目录（Lustre/NFS），大量小文件；`/tmp` 可写 |
| 网络 | 只需**出站** HTTPS 443 到模型 API；不需要入站端口 |

---

## 3. 操作系统与 Python

| 项 | 要求 |
|---|---|
| 架构 | x86_64 |
| glibc | ≥ 2.17（当前集群登录节点实测 2.17；manylinux2014 轮子即可） |
| Python | **3.11.x**（我们实测 3.11.15；`requires-python >= 3.10`，但依赖轮子按 cp311 锁定） |
| Python 来源 | 系统 Python 3.11 或 conda 均可；需要 `venv` 模块和 `pip` |
| 字符集 | `LANG=C.UTF-8`（或 `en_US.UTF-8`），避免中文/特殊字符路径问题 |
| 时区 | `tzdata` 已安装即可，任务内部统一用 UTC |

> Ubuntu 22.04 默认 Python 是 3.10；如果做 `custom` 镜像，请显式安装 3.11
> （deadsnakes PPA 或 conda 均可）。不要用 3.12/3.13 替代 3.11——依赖轮子和
> 数值结果都按 3.11 基线锁定。

---

## 4. Python 依赖

### 4.1 必须精确一致的包（影响结果可比性）

这些包的版本会进入我们每次运行的 `build_identity` 指纹；版本变了，历史结果就不可比。

| 包 | 锁定版本 |
|---|---|
| rdkit | 2026.03.5 |
| lightgbm | 4.7.0 |
| numpy | **1.26.4（必须是 1.x，不要 2.x）** |
| scipy | 1.17.1 |
| pandas | 3.0.5 |
| scikit-learn | 1.9.0 |
| langgraph | 1.2.12 |
| langchain-core | 1.6.9 |
| langgraph-checkpoint | 4.2.0 |
| pydantic | 2.14.1 |
| httpx | 0.28.1 |
| requests | 2.34.2 |
| tenacity | 9.2.1 |
| orjson | 3.13.0 |
| SQLAlchemy | 2.0.51 |

### 4.2 安装方式

```bash
python3.11 -m venv /opt/py311-runtime
/opt/py311-runtime/bin/pip install --upgrade pip
/opt/py311-runtime/bin/pip install -r /opt/py311-runtime/requirements.lock
```

`requirements.lock` 见 **附录 A**（完整 69 个包，均为我们现行环境实测版本）。
如果镜像里直接装进系统 Python 也可以，只要保证 `python3.11 -c "import rdkit"` 可用。

> 注意：`rdkit` 的包名就是 `rdkit`，不要用已废弃的 `rdkit-pypi`。
> `numpy` 必须锁 1.26.4；如果 pip 解析出 2.x，请强制降回。

---

## 5. 系统软件包（apt 名，Ubuntu/Debian 系）

| 包 | 用途 |
|---|---|
| `python3.11`、`python3.11-venv`、`python3.11-dev` | Python 运行时与 venv |
| `libgomp1` | lightgbm / OpenMP 运行时（必需） |
| `libsqlite3-0` | Python `sqlite3` 模块与业务数据库（必需） |
| `ca-certificates` | 访问 HTTPS 模型 API（必需） |
| `util-linux` | `flock` 文件锁（我们的多进程协调依赖它，必需） |
| `procps` | `ps` 等进程查看工具（排障用） |
| `curl` | 网络连通性自检 |
| `tzdata`、`locales` | 时区与 UTF-8 |
| `libstdc++6` | C++ 扩展运行时（通常已自带） |

不需要：`cuda-*`、`rocm-*`、`dtk-*`、`torch`、`tensorflow`、任何 GPU 驱动。

---

## 6. 网络要求

| 项 | 要求 |
|---|---|
| 方向 | 计算节点 **出站** HTTPS（TCP 443） |
| 目标 | 外部大模型 API 网关（域名由我们提供，不在本文件写死） |
| DNS | 能解析上述域名 |
| 入站 | 不需要 |
| 代理 | 如集群要求走代理，请提供 `HTTP_PROXY/HTTPS_PROXY` 的用法说明 |

> 这是硬性要求：跑题阶段每题都要调模型 API。若计算节点不能出网，
> 整个管线只能停在 build 阶段（build 本身不需要外网）。

---

## 7. 文件系统与运行方式

| 项 | 要求 |
|---|---|
| 共享家目录 | `$HOME` 可读写，作业间可见（我们放代码、批根、运行结果） |
| 文件锁 | 共享文件系统需支持 POSIX 文件锁（`flock`）；当前集群已支持 |
| `/tmp` | 可写（临时文件） |
| 作业方式 | 非交互式 `sbatch`；镜像需能直接执行 `#!/usr/bin/env bash` 脚本 |
| 环境变量 | 支持 `sbatch --export=ALL` 透传（我们会传 `PYTHONPATH`、`OMP_NUM_THREADS=1` 等） |
| 用户 | 非 root 运行；镜像内不要强制 root |

我们不会在镜像里写任何数据；镜像只提供运行时。

---

## 8. 验收清单（镜像做好后请逐条执行并回传输出）

```bash
# 1) 版本
python3.11 -V
python3.11 -c "import sys; print(sys.executable)"

# 2) 关键包版本
python3.11 - <<'PY'
import importlib.metadata as m
for n in ["rdkit","lightgbm","numpy","scipy","pandas","scikit-learn",
          "langgraph","langchain-core","langgraph-checkpoint","pydantic",
          "httpx","requests","tenacity","orjson","SQLAlchemy"]:
    print(n, m.version(n))
PY

# 3) 功能冒烟（RDKit 解析一个乙醇分子）
python3.11 - <<'PY'
from rdkit import Chem
m = Chem.MolFromSmiles("CCO")
assert m is not None and m.GetNumAtoms() == 3
print("RDKIT-OK", m.GetNumAtoms())
PY

# 4) SQLite
python3.11 -c "import sqlite3; print('SQLITE-OK', sqlite3.sqlite_version)"

# 5) 文件锁
python3.11 - <<'PY'
import fcntl, tempfile, os
p = tempfile.mktemp()
f = open(p, "w")
fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
print("FLOCK-OK")
f.close(); os.unlink(p)
PY

# 6) 出网（把 URL 换成我们提供的模型 API 地址；不带 key 期望 401/403/404，
#    不能是超时/连接拒绝）
curl -sS -o /dev/null -w "HTTP=%{http_code}\n" --max-time 10 https://<模型API域名>/

# 7) 机器规格
nproc
free -g | head -2
df -h "$HOME" | tail -1
```

全部通过的标准：

| 检查 | 期望 |
|---|---|
| Python | 3.11.x |
| 15 个关键包 | 与 §4.1 完全一致 |
| RDKit | 输出 `RDKIT-OK 3` |
| SQLite | 有版本号 |
| flock | 输出 `FLOCK-OK` |
| 出网 | HTTP 401/403/404（说明链路通） |
| 资源 | 单作业可申请 ≥12 核 / ≥32 GB |

---

## 9. 明确不需要的东西（避免过度构建）

- 不需要 GPU、CUDA、DCU、DTK、ROCm
- 不需要 PyTorch / TensorFlow / JAX
- 不需要 Jupyter / Notebook 服务（我们主要用 `sbatch` 批处理；有终端即可）
- 不需要 conda（有更好，没有也行；系统 Python 3.11 + venv 就够）
- 不需要预装我们的代码或数据（运行时从共享目录读取）

---

## 10. 版本变更纪律

镜像里的 §4.1 包版本请**不要自行升级**。如果某个版本在你们的源里拿不到：

1. 先告诉我们具体是哪个包、可用版本是什么；
2. 由我们确认能否替代（部分包会影响结果指纹）；
3. 不要用"最新版"直接顶替。

---

## 附录 A：requirements.lock（现行环境实测，69 个包）

```text
annotated-types==0.8.0
anyio==4.15.1
certifi==2026.7.22
charset-normalizer==3.4.9
contourpy==1.3.3
cycler==0.12.1
distro==1.9.0
fonttools==4.63.0
freetype-py==2.3.0
greenlet==3.5.4
h11==0.16.0
httpcore==1.0.9
httpcore2==2.13.1
httpx==0.28.1
httpx2==2.13.1
idna==3.20
joblib==1.5.3
jsonpatch==1.35
jsonpointer==3.2.1
kiwisolver==1.5.0
langchain-core==1.6.9
langchain-protocol==0.0.19
langgraph==1.2.12
langgraph-checkpoint==4.2.0
langgraph-prebuilt==1.1.0
langgraph-sdk==0.4.6
langsmith==0.14.7
lightgbm==4.7.0
matplotlib==3.10.9
munkres==1.1.4
narwhals==2.24.0
numpy==1.26.4
orjson==3.13.0
ormsgpack==1.12.2
packaging==26.3
pandas==3.0.5
pillow==12.3.0
pycairo==1.29.0
pydantic==2.14.1
pydantic_core==2.50.1
pyparsing==3.3.2
python-dateutil==2.9.0.post0
PyYAML==6.0.3
rdkit==2026.3.5
reportlab==5.0.0
requests==2.34.2
requests-toolbelt==1.0.0
rlPyCairo==0.4.0
scikit-learn==1.9.0
scipy==1.17.1
six==1.17.0
sniffio==1.3.1
SQLAlchemy==2.0.51
tenacity==9.2.1
threadpoolctl==3.6.0
truststore==0.10.4
typing-inspection==0.4.4
typing_extensions==4.16.0
unicodedata2==17.0.1
urllib3==2.8.0
uuid_utils==0.17.1
websockets==16.1.1
xxhash==4.0.1
zstandard==0.25.0
```

> 说明：我们现行环境里部分包来自 conda 构建，所以版本号按 `importlib.metadata`
> 实测列出。若你们用 pip 源安装，`rdkit==2026.3.5` 等如不可得，请按 §10 先沟通。

---

## 附录 B：参考 Dockerfile（仅当你们用 `custom` 且需要参考时）

```dockerfile
FROM python:3.11-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 libsqlite3-0 ca-certificates util-linux procps curl tzdata \
    && rm -rf /var/lib/apt/lists/*

ENV LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    PYTHONDONTWRITEBYTECODE=1 \
    OMP_NUM_THREADS=1

COPY requirements.lock /tmp/requirements.lock
RUN pip install --no-cache-dir -r /tmp/requirements.lock

WORKDIR /work
ENTRYPOINT ["/bin/bash"]
```

> 基镜像可以用 `python:3.11-slim-bookworm`，也可以用你们平台的标准 CPU base；
> 只要 Python 3.11 和 §4.1 的包版本一致即可。

---

## 附录 C：我们这边怎么用这个镜像

```bash
# 作业脚本里只依赖镜像里的 python3.11
PY=/opt/py311-runtime/bin/python        # 或 python3.11
export PYTHONPATH=$HOME/ppv1_hpc/dependingv43/src
export OMP_NUM_THREADS=1
export PYTHONDONTWRITEBYTECODE=1
$PY -B -m pathway_v43 ...
```

镜像本身不含代码和数据；代码与批根都在共享家目录，按作业参数传入。
