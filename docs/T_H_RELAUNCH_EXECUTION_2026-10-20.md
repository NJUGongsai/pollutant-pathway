# T-H 重启执行记录（2026-10-20）

**最新状态：已审源码和 8 件锁定操作脚本已部署，netcheck 46954668 全过；r2 build 已由防重复入口提交，JobID 46954982。北京时间 09:51:47 实测 RUNNING（wzhcnormal/f02r3n02）；尚未完成 build，未提交 run/score。后续由 heartbeat `t-h-r2` 接续。**

题域标签：**298 = RHEA 通用酶学 / 已见题（post-hoc）**。本段只做部署、环境检查和合成正负控，不产生真实题成绩。

## 1. 第一段授权与执行边界（两源码部署、netcheck）

- 依据 `docs/HANDOFF_T_H_RELAUNCH_2026-10-20.md`、两 delta 本机复核报告及主会话本段明确派工执行；已重读 AGENTS.md。
- 本段获准：重核无 T-H 活作业和 r2 不存在；只 scp 两件已审源码；核完整 SHA、远端版本/v3 可用性；提交现有 netcheck 并核终态；合成门正负控；只核旧根探针脚本路径及 SHA。
- 未提交 build/run/score，未改旧事故批根或原审批文本；未读取 questions、gold、run_inputs、逐题 case 内容或逐题 run；未读取/输出私钥或 env 内容；未 push。
- 输出路径创建前两次核不存在；本记录和新 evidence 不覆盖先前文件。只保存筛选后的版本、SHA、作业状态、计数和出错 kind，未拉取完整业务日志或现场。

## 2. 实际部署身份

| 项目 | 实测 |
|---|---|
| 本地源码提交 | `c360e7428a9b765636922282f27c65e917071460`（7 件源码/测试提交） |
| 站点/登录节点 | `wuzh02.hpccube.com:65091` / `login03` |
| 远端代码根 | `/work/home/aclhl3hbth/EnzymeAgent/v43cTH` |
| 部署方式 | scp 覆盖该代码根中 `s5b_compiler.py`、`evaluation.py` 两文件；没有把远端 tarball 目录冒充本地 Git HEAD |
| compiler SHA256 | `f917762bf9ec43d70b85ef3740ab7f22b866b42c06a1461ec336882eb2685dfc` |
| evaluation SHA256 | `37c092310d34d9f417234ccacd508942b3ce3edef640c73ab94022fd8dc75ad8` |
| 既有 netcheck 脚本 SHA256 | `553212cb37d6949f714a883456a4a519cce14fc4db1d938bb85a6307145f32fc`（本地、远端一致；未修改脚本） |

远端 `sha256sum -c -` 对两文件均返回 `OK`；随后再次输出完整 SHA，与已审提交逐字一致。实际导入模块路径均位于上述远端代码根。

## 3. 前置状态与命令退出码

北京时间 **09:41:21** 首次实施前核查：`squeue` 没有名称以 `th-` 开头的本账号活作业；`t_h_s5b_298_20261020r2` 的 batch/runs 两根均不存在。netcheck 提交前又核一次，同样通过。

| 步骤 | 返回码/结果 |
|---|---|
| 本地提交、SHA、私钥可读及新输出路径检查 | 0 / `LOCAL_PREFLIGHT_PASS`；未打开私钥内容 |
| SSH 远端空队列、r2 不存在与 netcheck 脚本 SHA 检查 | 0 / `REMOTE_PREFLIGHT_PASS` |
| scp 两件源码 | 0 |
| SSH 完整 SHA 及远端 runtime 检查 | 0 / `REMOTE_RUNTIME_PASS` |
| SSH 再核前置后提交 netcheck | 0 / JobID `46954668` |
| SSH 查询 netcheck、脚本 SHA 和合成门 | 0 / `REMOTE_SYNTHETIC_GATE_PASS` |

所有 SSH 使用 CC 当轮提供的 `/Volumes/CC/Enzyme_Agent/aclhl3hbth_wuzh02.hpccube.com_RsaKeyExpireTime_2026-11-30_10-12-36.txt`，参数含 `BatchMode=yes`、`ConnectTimeout=10`、`ServerAliveInterval=10`、`ServerAliveCountMax=1`。locale 警告存在，但各步骤退出码为 0；未发生登录/分区拒绝或自动换站。

命令与筛选后的结构化结果分别见 [commands.md](review_evidence/t_h_relaunch_execution_2026-10-20/commands.md) 和 [observations.json](review_evidence/t_h_relaunch_execution_2026-10-20/observations.json)。

## 4. 远端 runtime 与合成门

北京时间 **09:42:08**，以 `/work/home/aclhl3hbth/ppv1_hpc/venv_v44run/bin/python -B`、部署树 `PYTHONPATH` 及禁字节码写入检查：

| 项目 | 值 |
|---|---|
| Python / RDKit | 3.11.15 / 2026.03.5 |
| chemstate / compiler | `ppv1-chemstate-8` / `s5b-compiler-6` |
| 产物身份门 | `product-identity-gate-1` |
| v3 注册表与解析 | `available=True`；`resolve_criteria_version(PPV1_CRITERIA_V3)` 返回 `ppv1-criteria-v3` |
| 合成退化 spec | 主产物 `[N+]` 被拒；1 件 invalid component，kind=`unregistered_cx_class` |
| 合成合法 spec | 主产物 `CO` 通过（helper 返回 None） |

v3 Linux 引擎库 SHA 和四臂参数指纹已保存于 observations；它们是本次 Linux runtime 实测值，不冒充 macOS 参数指纹。没有用合成门结果认证真实池 21/529 分判或科学性能。

## 5. netcheck 作业

| 项目 | 实测 |
|---|---|
| JobID / 名称 | `46954668` / `th-netcheck` |
| 分区 / 计算节点 | `wzhcnormal` / `a01r2n03` |
| 开始→结束（北京时间） | 2026-10-20 09:42:28 → 09:42:31 |
| 调度终态 / ExitCode | `COMPLETED` / `0:0`（3 秒） |
| 自检判定 | `NETCHECK-PASS`：Python、RDKit、代码布局、磁盘、flock、dashscope 出口全过 |
| 网络检查边界 | 无 key 请求收到 `InvalidApiKey`，仅证实出口；零有效模型调用 |

作业原始日志仍在 HPC `/work/home/aclhl3hbth/EnzymeAgent/v43cTH/th_netcheck_46954668.out`；本地 evidence 只记检查项判定，不复制原日志。

## 6. 第一段交接（第二段现已按 §7 执行）

- 旧根现有安全探针代码：`/work/home/aclhl3hbth/ppv1_hpc/batch/t_h_s5b_298_20261020/p2_face_probe.py`。
- 其 SHA256=`c63166a77834b6492aa864872fbe6ca0a8c5fc1b113920baf9309c2c7118f54b`。本段仅核路径和代码 SHA，未执行、复制或读取其数据。
- 后续由主会话待交操作 launcher 准备 `WS/operations` 原审批件和已批准文本快照；本段未准备这些文件。
- 下一段仍须使用全新 `t_h_s5b_298_20261020r2`；旧事故根留存。score/V3 并列产物和 monitor 操作脚本由另一实施代理闭合后再起 r2 build。

## 7. 第二段：操作部署与 r2 build 提交

主会话 READY 后执行：科学源码提交 `c360e7428a9b765636922282f27c65e917071460`；操作提交 `04b94cb75be74e0b72b2b103f5bbfae2fe83ab8c`。两科学源码 SHA 保持不变；8 件操作脚本及锁 JSON 本地/远端完整 SHA 全对齐，远端 compiler-6/v3 available 再核通过。详见 [脚本锁](T_H_R2_SCRIPT_LOCK_2026-10-20.json) 和 [第二段安全证据](review_evidence/t_h_relaunch_execution_2026-10-20/stage2_observations.json)。

原批准四文件逐字放至 `/work/home/aclhl3hbth/ppv1_hpc/operations/t_h_approved_record_20261020`；TASK 取 `git show abbfa39` 原批准快照，PREP 和两 JSON 保留原字节。四文件 SHA 及批准 JSON 的文本绑定均通过。没有预建 r2 根、修改原审批或旧事故根。

| 项目 | 实测 |
|---|---|
| 提交入口 / JobID | 锁定 `th_operations.py launch --phase build`，使用提交前 pending 意图门；**46954982**，未手工 sbatch 绕过 |
| 提交时刻 | **2026-10-20 09:51:33.246368 +08:00** |
| 初查状态 | **09:51:47 RUNNING**，wzhcnormal / f02r3n02，已运行 13 秒；尚无最终成功判定 |
| batch 根 | `/work/home/aclhl3hbth/ppv1_hpc/batch/t_h_s5b_298_20261020r2` |
| runs 根 | `/work/home/aclhl3hbth/ppv1_hpc/runs/t_h_s5b_298_20261020r2` |
| opsstate | `/work/home/aclhl3hbth/ppv1_hpc/operations/t_h_s5b_298_20261020r2.json`；build/history 各 1 条，pending_submission 已清 |

09:50:22、09:51:19 及提交前均核无活 T-H 作业、r2 不存在。全部部署/校验/提交/初查命令返回码 0。构建初查只核路径/文件大小及安全调度 metadata，没有读取或复制业务日志正文；未等待构建完成，未 run/score，不 push。实际命令见 [commands.md](review_evidence/t_h_relaunch_execution_2026-10-20/commands.md)。

**接续：heartbeat `t-h-r2`**（主会话已创建，ACTIVE，每 15 分钟核状态，不变静默；该状态来自主会话）。下一次先查 `squeue -h -j 46954982 -o '%i %T'` 和 `sacct -n -X -j 46954982 --format=JobIDRaw,JobName,State,ExitCode`，不重投。只有 **COMPLETED／Exit0 且安全过滤核出 TH-BUILD-PASS** 后，按 [操作书](T_H_R2_OPERATIONS_2026-10-20.md) 核 build gate，再用上述原批准 record-dir 执行 prepare/P2→run→三版 score→交付；异常停报，完成后暂停 heartbeat。
