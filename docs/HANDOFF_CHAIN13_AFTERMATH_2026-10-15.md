# HANDOFF — chain13 后续窗口（2026-10-15）

> 交出窗口：本窗口（criteria-v2 生效+C 线落地+chain13 三模型复测全链）。
> 接手窗口：零上下文按本交接执行。**第一件事=§六建议的 C 归因轮**。

## 一、一句话现状

ppv1-criteria-v2 已放行生效、C 线（共底物供给 policy-7）已落地，
chain13 三模型复测（GLM/qwen/ds × 298 题）**全链跑完出数**——
结果为**下行信号**：GLM hit@1=87（v2 口径）比基线 92/94 掉 5~7 题；
净负贡献来自 C 供给/声明链的生成侧改动（v1 口径 strict 126→114、
partial 43→52），v2 判据本身方向正确（+4）。**下一步核心=C 供给
净负贡献归因（零成本离线可拆）。**

## 二、chain13 结果（题域标签 298=RHEA 通用酶学/已见题）

| | GLM-5.3-Flash | deepseek-v4.1-flash | qwen3.8-flash |
|---|---|---|---|
| hit@1（v2 headline） | **87**（29.2%） | 83 | 79 |
| hit@3 / hit@5 | 112 / 118 | 104 / 107 | 103 / 103（平台） |
| hit@1（v1 敏感性） | 83 | 79 | 74 |
| 严格覆盖/partial/unmatched | 119/47/132 | 108/34/156 | 104/23/171 |
| 终态/账目 | 298 零失败 6.3M tok | 298 零失败 4.8M（最省） | 298 零失败 6.5M |

基线参照 chain12=92/126/130、hpc2-A=94/121/124（v1）。诚实读法
全文：[CHAIN13_MODEL_CMP_TABLE_2026-10-15.md](CHAIN13_MODEL_CMP_TABLE_2026-10-15.md)
（含分解与机制读法：C 供给候选带共底物参与物 → v1 落 partial、
v2 救 5 亏 12+；三模型横向可比、绝对数不与旧协议批直比）。
其它实测：v2 豁免三臂各 5 题（同 5 题、模拟 13 兑现 5）；3 调用
预算零消费（三臂每题 1 次首调全过）；老口径 anyof GLM=145 vs
chain12=143（宽口径没亏）。

## 三、两仓状态（v43 主线 / v44 支线）

- **v43**（`/Volumes/CC/Enzyme_Agent/dependingv43`，分支 v4.3）：
  本地 HEAD=`461844e`，**8 个未推提交**（0ba764f 之后）：
  `7e7855c` P1fix → `873c323` C 线实施 → `dda852b` P1fix2 →
  `b6ba35f` P2-1 落字 → `5ade032` **v2 生效登记** → `fec1f07`
  chain13 发车物 → `27300cf` 三模型预注册 → `461844e` no-cap 移植。
  **origin/v4.3 停在 0865fba**（推送节奏待 CC）。全量测试基线
  **2139/0/16**。
- **v44**（RR A/B 支线，af0fd26）已封存不动；其 no-cap 运营壳已
  移植回 v43。
- 未跟踪件：chain13 对照表/各设计书/任务书/评审报告族（评审侧
  留未跟踪由 CC 定）、三大 assets json（gitignored 级）。

## 四、HPC 现场（乌镇 wuzh02，已验证全链）

| 件 | 位置 |
|---|---|
| 连接 | `ssh -i ~/.ssh/hpc_wuzh02_key -p 65091 -o BatchMode=yes aclhl3hbth@wuzh02.hpccube.com`（密钥在 Mac ~/.ssh，600） |
| 代码树 | `~/EnzymeAgent/v43c13`（v43@461844e 前身，跑批用）+ 仓外引擎 `~/EnzymeAgent/dependingv3` |
| **三批根（只读封存）** | `~/ppv1_hpc/batch/chain13{,q,d}_s5b_20261014`（判分产物齐：metrics.json v2+metrics.json.v1；approve/budget_no_cap 在根） |
| runs 根 | `~/ppv1_hpc/runs/chain13{,q,d}_s5b_20261014` |
| env 文件 | `~/ppv1_hpc/env/llm{,_qwen,_ds}.env`（GLM/qwen3.8-flash/deepseek-v4.1-flash 三份，600） |
| python | `~/ppv1_hpc/venv_v44run/bin/python`（rdkit 2026.03.5+lightgbm+langgraph） |
| 发车族脚本 | v43 仓 `scripts/hpc/sbatch_chain13_{build,run,score}.sh` + `chain13_*.py`（可复用为 chain14+） |

**已知坑（全踩过）**：登录节点跑重活会被静默 SIGKILL（判分一律
sbatch 上计算节点）；节点本地 /tmp 满时 bash heredoc 会炸（脚本
全部实体化）；HPC 登录节点轮转 /tmp 不共享（中转一律走家目录）；
老 rsync 不认 `--info` 也不建多级父目录（先 mkdir）。

## 五、易失件清单

| 件 | 用途 | 丢失怎么办 |
|---|---|---|
| `~/.ssh/hpc_wuzh02_key` | HPC SSH | 原钥在 `/Volumes/CC/Enzyme_Agent/aclhl3hbth_…txt`（2026-11-30 到期，重拷+chmod 600） |
| `/tmp/cy_ssh.sh` | chenyu 探测 | 凭证在用户处按 AGENTS 重建 |
| `/tmp/chain13_monitor.log` | 值夜日志（00:24 中断，三臂完成记录以 sacct/批根为准） | 无需重建 |
| `~/.ssh/hpc_cancon_key` | 昆山（迁移已作废，部署留位无害） | 可弃 |

## 六、接手建议执行序

1. **C 供给净负贡献归因轮（第一优先，零成本零模型）**：对 chain13
   GLM 臂做离线拆账——v1 口径 strict 126→114 的 -12 里，哪些题是
   "共底物候选被选中带参与物→partial"、哪些是"声明链上下文漂移"；
   工具=既有 offline funnel/谱系（`scripts/s5b_offline_funnel.py`
   + hpc2 批根同款方法）；产出决定 C 线**回滚/收窄/重设计**的
   拍板材料。
2. **v2 豁免 5/13 兑现面归因**（同轮顺手）：8 题差额在声明链消费
   还是模型选择面。
3. teacher/mimo 汇报：chain13 结果是下行信号，按三触发点该出
   结果复核请求（mimo 场景 3 零金标自包含）+ teacher 知会。
4. 挂账待 CC：D 线新语料收录（86 题 BRENDA/ENZYMEMAP 缺书）、
 8 个本地提交的推送节奏、正链 Codex R2 事后复核确认（AGENTS 允
 许，本地代审已放行）。
5. 仓规速记：金标/题面永不入仓（三批根只读封存）；判分零 LLM；
 对外数字带 298 题域标签；不 push 不自动提交；探针≠预注册≠成绩。

## 七、回传义务

接手后每完成一步：大白话汇报（结论先行+表格）；关键拍板点
（C 线回滚/收窄、D 线语料、推送）停下问 CC；涉金标外发/费用
异常立即停。会话记忆已存
`v43-c-cosub-criteria-loop-2026-10-14.md`（项目记忆索引可查）。

交接人：主窗口（2026-10-15 晨）。
