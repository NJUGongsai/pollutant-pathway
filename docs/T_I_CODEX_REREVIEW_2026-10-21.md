# T-I TI-F1/F2 固定面复审（2026-10-21）

> **题域：[298域] = 298 / RHEA 通用酶学 / 已见题（post-hoc）。** 本报告仅核工程控制与批准包，不生成真实成绩，不外推 dev、闭卷或通用能力。测试数、文件数、哈希、版本和行号均为工程核验身份。
>
> **权限与边界：** 依据本轮用户授予的最终复核权，仅按 `docs/T_I_CODEX_FINAL_REVIEW_2026-10-20.md` §5 的固定面审 TI-F1/TI-F2；不扩 P0b、证据卡、池、检索、排序、评分、D-1/D-3/D-7 或付费批。只新增本报告与 `docs/review_evidence/t_i_codex_rereview_2026-10-21/`。未改源码、测试、脚本、既有文书或封存批；未 push、未调用外部模型、未连接或运行 HPC；未读真实 env/key/题面/金标/reference_graphs/封存逐题 run，未输出凭证值或结构正文。
>
> **实际 HEAD：** `c9c6c7a7ae02b46769add09fbc2536323ce8a985`。观察 schema：`t-i-script-lock-1`、`ti-arm-config-2`、`ti-stage-gate-1`、`v44-budget-no-cap-1`。
>
## 1. 总裁定

**[298域] 总裁定：需修正。TI-F1 不允许关闭；TI-F2 允许关闭。当前真实发车仍为 NO-GO。**

实际 worker 可以产生 `status=completed` 且内嵌 `forbidden_permanent` 权限故障的产物；现行分类在 completed 分支提前返回，将原本应立即停止的致命信号降为普通运行失败。新增公共链证明该产物进入 full 后仍获通过，巡检也未停止；另一个真实调度循环探针显示，收割该产物后仍派发新的 qid。这是同一 TI-F1 阻塞的两种表现，直接违反原终审第 90、94 行的致命信号立即停与运行中阻断要求。

原终审批准的是“原预注册＋任务书＋终审增补”的整体政策，允许两项有限回修关闭并且当前阶段全部事实前置满足后依原裁决执行；本报告不重复作政策签字，不认证未知运行事实为真。批准包生成、脚本锁匹配和合成控制通过均不等于真实可发车。

## 2. TI-F1、TI-F2 逐项结论

### 2.1 TI-F1：监控／双臂阶段硬停

固定规则取自原终审第 83–94、131–134 行，不增加新阈值。

| 原固定规则 | 本轮核验与结论 |
|---|---|
| 按唯一 qid 计数、失败分类及 unknown 不豁免 | `registered`/`evaluate_stage` 按注册 qid 逐题计数；坏 JSON、unknown 与未登记零调用计运行面，已登记 NC-9 需同因证据；该计数框架具备。完成态内嵌致命错误的优先级另见下项，不能以总失败计数正确覆盖该缺陷。 |
| smoke2 身份、真实调用与 usage | 冻结至少一题 completed 且 `model_calls>0`、所检题终态、prediction/model 身份、usage 可解析；原合成正负控可重现。真实 smoke 回执未核。 |
| smoke10 failed／未登记零调用／pending 任一 >0 停两臂 | 数量阈值为 0，阶段末和公共消费链均有拦截；正常完成态未中与 NC-9 保持正控。 |
| full 第 16 个非内容运行失败 qid 起停两臂 | 阈值 `>15` 与唯一 qid 计数具备；15 放行、16 拒绝的既有合成正负控通过。该数量门不覆盖致命信号的立即停规则。 |
| 任一阶段致命信号立即停；不得按数量容忍 | **需修正。** `classify_case` completed 分支第 565–594 行先返回，致命标记检测在第 595–602 行；真实 worker 可达的 completed+`forbidden_permanent` 被降为普通运行失败，公共 full 门与 monitor 均错误接受；真实调度循环在收割该产物后仍派第二个新 qid。仅修事后 gate 不够，详见下方复现。 |
| 恢复仅 prediction_recovery 原白名单、同题同参一次、先保全、二败停 | 已有失败登记与一次恢复/二败停 helper 正负控通过；不新增恢复类别、不重置次数。原控未执行真实 driver 恢复或 shell 恢复全链，此证明边界照列，不另升新阻塞。 |
| 无 token／金额硬停 | `token_projection` 第 794–804 行固定 `action=warn_only`；超规划带只告警的合成正控通过；金额无依据保留 unknown。 |
| 双臂 smoke10 barrier、15 分钟巡检、单协调者、取消／阻断路径 | `barrier_full` 第 986–1025 行、`write_stop` 第 876–913 行、monitor 与 shell 入口具备本地执行链；首写/flock/barrier/halt 原控通过。本轮另执行实际 monitor shell→CLI，full16 后本地 scancel 替身收到两臂作业号 111/222。**运行中已收割致命产物后的新派发仍未阻断，需与同源分类一并修正。** 真实站点权限、monitor 作业与 scancel 效果未核。 |

**可复现反例。** 本轮在新 tmp 隔离副本执行真实 worker/runflow/adapter/case writer，模型端使用既有零网络 `ScriptedRealModelAdapter` 返回 `forbidden_permanent`。此步仅把资产身份函数换为内存替身，未访问真实资产，未替换错误处理或 case writer。实际路径为 `real_model.py:1020–1027 → runflow.py:1429–1435,747–756 → s5b_worker.py:296–303`：传输错误保留在返回报告的 `run_error` 中，worker 因正常返回 summary 写 completed。

再将该实际产物的安全错误字段/形状投放到 full 第 11 个合成 qid，只换合成 qid/run_id，交实际 `sbatch_ti_run.sh → ti_run_wrapper → phase → run-gate → barrier → full` 控制链消费；此步整个 orchestrator 为固定终态替身，不声称公共链执行了真实编排器/模型。这些控制均无真实网络、付费请求或 HPC。

| 工程反例读数 | 实际结果 |
|---|---|
| 实际 worker 产物 | `status=completed`，含 `forbidden_permanent` |
| 公共链退出与阶段 | `exit=0`；`limits=[2,10,null]`，实际走完 smoke2、smoke10 与 full |
| full 门 | `full_passed=true`、`n_run_failures=1`、`n_fatal=0`；full 通过回执存在 |
| 协调停点与巡检 | `stop=null`；同一产物经 `monitor_once` 得 `stopped=false` |

来源与消费结果分别见 [真实 worker 安全读数](review_evidence/t_i_codex_rereview_2026-10-21/f1/actual_worker_result.json) 及 [完整公共阶段链](review_evidence/t_i_codex_rereview_2026-10-21/f1/fatal_public_chain_summary.json)。

这不是只向 helper 塞一条不可达字符串：worker 来源与公共消费入口均有执行证据。错误在共用分类，不在 full 的 15/16 数量阈值；数量阈值不得豁免权限故障。smoke10 数量门可拒绝该产物时，也不能推翻它在 full 出现后仍被放行的反例。

**运行中阻断复现。** 本轮另执行真实 `orchestrator._run_batch_loop(workers=1)` 的收割/派发控制流（`s5b_orchestrator.py:830–859,888–906`），本地 worker 进程/result 替身写入上述真实 worker 来源产物。该产物经实际 `read_validated_case` 校验为 `ok=true` 并被收割后，调度器仍派发第二个 fresh qid；它是新派发，不是在途请求。workers=1 仅用于排除在途歧义，不冒称冻结并发。探针在第二次派发处主动终止，第二 worker 正文及之后循环/汇总未执行，均不报通过。详见 [真实调度消费读数](review_evidence/t_i_codex_rereview_2026-10-21/f1/actual_dispatch_result.json)。

`ti_run_wrapper.py:65–81` 同步等待 `run_s5b_batch` 返回，`sbatch_ti_run.sh:63–89` 在 wrapper 之后才运行 phase；`ti_operations.py:2084–2110` 的 900 秒轮询不能承担“已见致命信号后禁止新派发”的即时约束。同源持续故障统计也只让 `status=failed` 进入 streak（第 689 行），回修须保留实际分类事实，不能再被 completed 状态洗掉。

**最小回修仅限 TI-F1：** 共用分类必须在 completed 提前返回前识别原已定义的致命／持续故障信号，并在 T-I 现有运行监督／调度消费链执行同一规则：已收割致命产物后不再派发新的 qid，立即写双臂停点、触发现有取消／阻断路径并保全；不能只改阶段末 gate。这里规定原验收行为，不擅自扩大源码修改许可，不新增阈值或恢复类别。

补充回归必须用本次真实 worker 来源产物走完整公共阶段链及真实调度消费入口，分别断言不授 full 通过、巡检识别致命错误、收割后无第二个 fresh 派发及双臂停点生效；保留原 63 项、NC-9、普通非致命 ≤15 正控与诚实 unknown。原先已在途请求及取消时点照实记录，不要求撤回已消费请求。按原有限回修约定同步正负控、操作说明、脚本锁及批准包身份，不触及科学面或新阶段。

### 2.2 TI-F2：批准包首次消费校验——关闭

批准 JSON 写真实代决来源 `Codex 代 CC/师姐`、`approval_source_kind=codex_delegated_cc_shijie`、授权链和原决议时间 `2026-10-20T15:49:53Z`；`approval_basis=原预注册+任务书+本终审增补`、`no_cap_ack=true`、`cost_cap_cny=null`。没有伪填 CC 本人已修改原草案。

四文书键为 prereg/task/final_review/script_lock；本轮独立核得四份仓库源文件、包内快照与 JSON 声明 SHA 全同，批准包外部 `SHA256SUMS` 五项全同。原草案保留，生效依据是完整包。文本 SHA 为 `2e45d40721168a19016e1488539e76b40ba55020a2f15a9c8b108646b84921b3`；批准 JSON 自身 SHA 为 `1766734bf00183d6525eea7cf5f9523a858a4f45423988458d94d500007fa6b1`，二者分列。现行脚本锁自身 SHA 另为 `1ed4f2789f4b7d9f4104446904861ff0a1271cc68ba3fbf2a48324c5528d13d0`。

`validate_approval_package`/`validate_batch_approval` 为 prepare 与 run 首消费共用；prepare 第 1395–1470 行、launch 第 1886–1906 和 1934–1973 行、wrapper 第 51–59 行在付费消费前重新核包。缺件、内容/SHA 不符、错误来源或 `no_cap_ack=false` 均拒绝；本轮补控含 1 正 7 负，保留合法通过而非全面拒绝。七个负控均有 wrapper 首消费调用栈与预期 validator `RuntimeError`，之后 shell 错误后处理的标签变量次生报错不作拒绝主证据。详见 [TI-F2 笔记](review_evidence/t_i_codex_rereview_2026-10-21/f2/NOTES.md) 与 [首消费矩阵](review_evidence/t_i_codex_rereview_2026-10-21/f2/first_consumption_matrix.json)。

`approved_at` 表示原终审政策决议时间，不冒称未来修复字节已在该时点被审核；原终审第 133–137 行已授权有限回修后重新锁定，本次复核与之后 C1 部署事实分别承担其义务。关闭 TI-F2 不等于批准包已经部署、C4 请求参数已经核实或任何调用已经发生。

## 3. 原 63/63 正负控的覆盖评价

**[298域／工程核验] 本轮已在新系统 tmp 隔离副本、禁字节码及测试缓存条件下，完整独立复跑原 50 项与 13 场景，结果仍为 63/63 通过。** 50 条 helper 记录含嵌套预期拒绝与组包装，不能称 63 个独立端到端实验或独立漏洞。这与来源报告的声明分开记录；不把合成数写成真实题数、真实成功率或科学性能。读数见 [50 项完整复跑](review_evidence/t_i_codex_rereview_2026-10-21/f1/unit_replay_summary.json)、[13 场景完整复跑](review_evidence/t_i_codex_rereview_2026-10-21/f1/public_replay_summary.json)；首次公共链尾部 HEAD 元数据查询失败的尝试不另计通过数，采信完整重跑。

| 覆盖层 | 能证明的内容 | 边界 |
|---|---|---|
| 50 项本机控制 | 数量阈值、分类、smoke2、full15/16、恢复、token 告警、barrier/monitor/flock/halt、批准包及首消费拒绝 | 部分直接消费手工构造的 case 或替代 wrapper；不能自动证明真实 worker 产生的所有终态形态都已覆盖 |
| 13 个公共链场景 | 实际 shell→wrapper→phase→run-gate→barrier 的原正负控，含 smoke10 单 failed/零调用/pending、full15/16、CX/quota/连续传输、批准包缺件/no_cap_ack=false | 公共控制流真实，但 worker/case 仍有合成替身；其 fatal 样本不足以证明 completed 内嵌致命错误的真实来源链 |
| 本轮 TI-F2 补控 | 1 正 7 负覆盖 prepare 后首消费包校验 | 本地拒绝证明，不认证远端部署/真实凭证或真实发车 |
| 本轮 TI-F1 新探针 | 实际 worker 产物、公共阶段链与真实调度消费循环 | 补出 completed 内嵌致命错误；full/monitor 错误接受，且已收割致命产物后仍新派发；对应原终审第 90、94 行；不外推真实失败频率 |

因此，原 63/63 的“这些场景通过”成立；它们不能替代固定面全部规则的闭合证明。固定面若出现真实 worker 可达且公共消费链错误接受的致命信号，必须按原契约回修，不能以测试数将其关闭。

## 4. 脚本锁与白名单

**现行脚本锁通过：14/14 文件逐字节 SHA 匹配，`missing=[]`，schema 正确，`source_commit` 与实际 HEAD 相同。** 两份科学源码和两份 chain13 共享件既与旧摘要相同，也与当前 HEAD blob 同值；tracked 工作树无差异。

| 对上轮保全 `lock_check.json` 的关系 | 准确路径与判断 |
|---|---|
| 五个既有操作件改变 | `scripts/hpc/ti_operations.py`、`scripts/hpc/ti_run_wrapper.py`、`scripts/hpc/sbatch_ti_run.sh`、`scripts/hpc/sbatch_ti_score.sh`、`scripts/hpc/ti_arm_config.json`，均为 T-I 操作白名单 |
| 新增操作件 | `scripts/hpc/sbatch_ti_monitor.sh`，对应原 TI-F1 的巡检／协调要求 |
| 配套文书改变 | `docs/TASK_T_I_LAUNCH_2026-10-20.md`；原终审第 134 行明确允许“对应正负控、操作例子修正、更新锁与批准包”，故此项不能误判越界 |
| 七件原样 | 科学源码两件、chain13 两件、`sbatch_ti_build.sh`、原预注册、实施准备文书 |
| 证明限制 | T-I 脚本／文书均未跟踪；旧锁摘要能证明上述锁内身份差异，不能重建全仓未跟踪文件历史，也不能生成无原始旧字节支持的源码 diff。未发现具体白名单外改动证据；该限制记 unknown，不追加范围外阻塞 |

`source_commit` 不包含未跟踪的 T-I 操作件，不能单靠 checkout 宣称部署完成；C1 必须对 HPC 实际使用的现行文件逐件复算锁 SHA。详见 [锁与关卡子审](review_evidence/t_i_codex_rereview_2026-10-21/lock_gates/NOTES.md) 和 [独立身份读数](review_evidence/t_i_codex_rereview_2026-10-21/lock_gates/lock_package_audit.json)。

## 5. 关闭后 C0–C8 最小事实与唯一 GO／NO-GO

沿用原终审第 102–124 行的原名、事实与依赖，不重开科学预注册，也不混入 P2 新批条件。下表“本轮未核”不能代签为真。

| 条件（原名） | 最小事实与依赖 | 当前状态 |
|---|---|---|
| C0 有效批准包 | 四文书完整快照/逐件 SHA、真实代决来源/时间/授权链、no_cap_ack=true、两臂 no-cap、增补优先；可与只读离线/站点核验并行；任何付费 C5 前完成 | 本地包具备；HPC 记录目录部署及外部清单绑定未核 |
| C1 两个实施阻塞关闭及部署锁定 | 同消费入口复核关闭、现行操作件锁、HPC 逐件同值、科学源码/冻结参数不变；缺一不发车 | 本地 14/14 锁通过；TI-F1 未关闭，远端部署未核 |
| C2 真实作业能力与净环境 | 凭证可用布尔、权限/分区/路径/磁盘/flock、无遗留 V43_LLM_* 覆盖或最终有效值已核；可并行批准/离线核验；缺一不发车 | 真实事实本轮未核；不得回传凭证值 |
| C3 netcheck | 实际作业号、COMPLETED 0:0、NETCHECK-PASS，代码路径/环境符合计划；站点证据可双臂复用，不替代模型开通；缺一不发车 | 本轮未核 |
| C4 两臂文件与有效请求预检 | 两 env 在位/600，精确模型/base host 正确，request params 逐字同值；有效发送不含 temperature/max_tokens/禁用思考键；timeout/重试同冻结；离线部分可并行；未知/不同不放行 | 本轮未读真实 env／有效请求，未核；只记录同值布尔及安全身份 |
| C5 两臂最小真实调用 | 有效批准及站点核验后，各模型最小调用成功、非空、usage 可解析、身份/参数可接受；每次尝试用量/时间/金额或 unknown 入 preflight_calls；两臂可并行，一臂失败停两臂，未知/不兼容不发车 | 未调用；这是付费请求，不能在 C0 前先试 |
| C6 同题集与双臂 build 身份 | 题卷仅远端安全核行数/冻结 SHA；代码/科学聚合/版本/资产/RDKit 符合；新根同 batch_tag、build/build-gate 成功；D6 manifest SHA/fingerprint/逐题输入 SHA 全同；双臂 C5 先过后可并行 build，D6 后才 prepare；缺一不 run | 无真实 build 读数；不拉回原题卷／输入 |
| C7 prepare 与现有 P2-face 探针 | 合法包/no-cap/arm_config；每臂 p2_face_measure 全部期望逐项实核及操作者/审核记录；双臂可并行；文件生成不算通过，任一不符/未核不 run | 无真实 prepare／读数 |
| C8 协调/阶段放行与回传 | 单协调者、失败分类/取消路径、双臂 smoke barrier、阶段允许件、usage/失败/作业事实回传责任；调度前齐备，full 前双臂 smoke2/smoke10 实际通过；缺一不进入对应阶段 | 只有本地实现/合成证据，真实 monitor 作业、run 回执及双臂 smoke 未核 |

C7 冻结的工程身份读数是 `files=298`、`specs_total=531`、`remap_applied=242`、`remap_add_atom_ge1=205`、`remap_add_atom_ge2=78`、`questions_remap=151`、`questions_with_add=134`、`questions_with_multi_add=65`（原终审第 112 行）。不符查身份/资产，不改探针口径；这不是后续证据卡 v2 的 P2 启动门。

C0 文书 SHA、C1 部署 SHA、C4 有效请求、C6 build 身份各证不同事实，不能互相代替。env 文件同值也不能替代有效作业值：进程 `V43_LLM_*` 覆盖、`--export=ALL` 与客户端参数合并均须核实（原终审第 114 行）；`TI_WS` 要 export 或显式传给读取该环境变量的核验命令（第 116 行）。

**[298域] 唯一判据仍为：`GO(当前阶段) = 该阶段全部必须前置均有实证为真 AND 无活动停点`；任一 false 或 unknown 即 NO-GO。** 正式 run 前 C0–C8 的全部必须事实均须满足；full 前另须双臂 smoke 全绿。未来 run 作业号仅在真实提交后取得并保存，不循环要求提交前有未来号；无可靠号先查调度器，禁盲重投。没有单价/精确金额本身不否决 no-cap，usage 采集能力必须具备。当前仍 **NO-GO**。

## 6. unknown／未核事项与证据

| 未核事项 | 本报告的限度 |
|---|---|
| 真实站点、凭证、参数、作业与用量 | 未登录 HPC、未读 env/key、未做 netcheck/最小真实调用/build/run/score；不据本报告宣称已发车或真实模型兼容 |
| 合成与科学表现 | 63/63、补控和新反例均为工程控制证据；没有真实双臂结果、运行失败频率或科学收益，不据此选模型 |
| 在途取消 | 本地可执行取消／阻断路径不能认证站点 scancel 权限或撤销已消费请求；真实停点时须记在途与取消时点 |
| 未跟踪文件保全 | 没有全仓未跟踪文件的历史逐字节基线；只对固定锁集合与本轮授权新增件承担明确证据责任 |
| 费用 | 金额/单价/账单快照 unknown；不估造、不新增 token／金额硬停 |

复跑与探针在新系统 tmp 的隔离副本运行，源码副本含 vendor 和必要 metadata，禁 Python 字节码和测试缓存；旧永久证据没有原地运行。命令摘要：原 50 项控制脚本、13 场景公共链完整复跑；TI-F2 首消费 1 正 7 负补控；TI-F1 实际 worker 零网络探针、公共阶段链、真实调度循环和 [monitor shell 取消补控](review_evidence/t_i_codex_rereview_2026-10-21/f1/monitor_shell_cancel.json)；脚本锁／批准包 SHA 使用只读标准库脚本独立复算。确切命令见 [TI-F1 COMMANDS](review_evidence/t_i_codex_rereview_2026-10-21/f1/COMMANDS.txt)、[TI-F2 执行记录](review_evidence/t_i_codex_rereview_2026-10-21/f2/probe_execution.json) 与 [锁核验命令/身份](review_evidence/t_i_codex_rereview_2026-10-21/lock_gates/lock_package_audit.json)；实际 HEAD、输入哈希和替身范围在各自证据中保全，区别本轮独立执行与旧报告来源声明。

证据根目录为 [本轮证据](review_evidence/t_i_codex_rereview_2026-10-21/)，分项为 [TI-F1 执行与反例](review_evidence/t_i_codex_rereview_2026-10-21/f1/NOTES.md)、[TI-F2 首消费核验](review_evidence/t_i_codex_rereview_2026-10-21/f2/NOTES.md)、[锁及 C0–C8 身份边界](review_evidence/t_i_codex_rereview_2026-10-21/lock_gates/NOTES.md)；完整新增证据由 [总 SHA256SUMS](review_evidence/t_i_codex_rereview_2026-10-21/SHA256SUMS) 绑定。清单排除自身，不对历史文书或封存材料回写。
