# T-I B3 停点分诊（2026-10-21）

> **题域：298 = RHEA 通用酶学 / 已见题（post-hoc）。** 本文只做停点分诊，不产生成绩；
> 零模型调用（本报告本身）、零新批次、不读金标/题面/结构正文。
> 现场：B3 批根 `~/ppv1_hpc/batch/t_i_298_20261021b3_{glm,deepseek}`；
> stop `~/ppv1_hpc/operations/t_i_coordination_t-i-298-20261021b3/stop.json`（未改）。

## 1. 事实

| 项 | 值 |
|---|---|
| 停点时刻 | 2026-10-21T08:53:31.904627Z |
| stop | `reason=stage_gate`, `phase=smoke10`, `arm=glm`, `detail=smoke10_completed_run_error:1` |
| GLM 作业 | `47068104` **FAILED exit 1:0**，Elapsed 00:46:40，End 16:53:32（北京） |
| DeepSeek 作业 | `47068110` **CANCELLED**（被停点 scancel），smoke10 10/10 干净 |
| monitor | `47068118` 已 **CANCELLED**（收尾清理，非作业失败） |
| GLM smoke10 | 10/10 completed；9 题带调用干净，1 题 `completed_run_error` |
| 失败 qid | `RXNG_56d8303ebd8a99f21974e52e9174f3a453c7e59071d517fc128b0a9bcd3162ec` |
| 失败 case | `status=completed`, `stop_reason=budget_limit`, `model_calls=2`, `retries=1` |
| usage | `calls_with_usage=0`, `calls_without_usage=2`, input/output/total **全 0**, `present=False` |
| run_error | `real_model_transport_failure / transport_error`（PPV1RunError） |
| full / score | **未发 / 未跑** |
| 站点 | 同窗口 soak `47041048` 12/12 GREEN；C5 两臂 200；netcheck `47042109` PASS |

## 2. 跨批对照（同 qid）

| 批 | 模型 | status | calls | 结果 |
|---|---|---|---:|---|
| `t_h_s5b_298_20261020r2` | GLM-5.3-Flash | completed | 1 | 无 run_error |
| `chain14a_s5b_20261015` | 同基线 | completed | 2 | 无 run_error |
| `chain14b_s5b_20261015` | 同基线 | completed | 1 | 无 run_error |
| `chain13_s5b_20261014` | 同基线 | completed | 1 | 曾有 `real_model_transport_failure`，仍完成 |

**读法**：同题在四次历史批（含同一 GLM 模型）都能完成，其中 chain13 也出现过同 kind 的传输失败
但完成了。B3 这次是 **2 次调用、usage 全 0** 的传输失败；没有证据表明是题目/提示词可复现问题。

## 3. 分诊结论

**判定：瞬时传输失败（非题目可复现、非站点全断），不是模型/判据/代码缺陷。**
- 站点同期 12/12 soak、两臂 C5 200、netcheck PASS，排除站点大面积故障。
- 同 qid 历史四批均完成，排除题目/模型内容层面的稳定失败。
- 失败发生在 smoke10 的第 10 题，2 次调用均无 usage，符合“连接/响应丢失”而非模型返回错误。
- 运行脚本按 TI-F1 `smoke10_completed_run_error>0` 阶段门停两臂，属按规则执行，不是脚本误杀。

**残余 unknown**：该次失败的具体网络路径（代理 vs 模型端点）未取到 detail（`detail={}`）；
是否需要网络侧 RCA 由 CC/运维决定。

## 4. 三个选项

| 选项 | 做法 | 代价 | 风险 |
|---|---|---|---|
| **A. B4 新批**（推荐） | 新 tag/根/协调目录，重跑两臂 build（零模型费，~1h/臂）+ smoke；过 barrier 后 full | 重建 ~1–1.5h + smoke 少量调用；full 未开始前不烧大钱 | 若同题再次 transport_error，则可复现性升级，需网络/端点 RCA；否则正常 |
| **B. 同批原地 resume 该题** | 清 stop、单独重试失败 qid，再放 full | 表面省时 | 大概率被 `stage_gate` 再拦（completed_run_error 仍在 case）；该题已 2 次调用，恢复白名单不覆盖 transport_error；且要改 stop/现场，违反“现场不删改”。**不推荐** |
| **C. 接受失败留分母** | 把该题按未命中留 298 分母，继续 full | 最省事 | 需要绕过 smoke10 阶段门（TI-F1 阈值 0），属改阈值；当前授权不允许。**不可直接做** |

**建议：A（B4 新批）**。理由：瞬时失败、同题历史可完成、站点健康；B4 是唯一不改阈值/不删改现场的合规路径。
若 B4 同题再次 transport_error，则升级为“可复现传输失败”，停止并交 CC/运维做网络 RCA，不再开 B5。

## 5. 边界

- 本报告未发起任何付费 run/resume；B3 现场（cases/monitoring/stop.json）原样保留。
- 未改 B2/20261020 批根与 stop.json；未改代码/判据/池；未 push。
- 决策权：B4/停 T-I 由 CC 拍板；本报告只给选项与建议。

## 6. 证据

- stop：`~/ppv1_hpc/operations/t_i_coordination_t-i-298-20261021b3/stop.json`
- GLM case：`~/ppv1_hpc/batch/t_i_298_20261021b3_glm/cases/RXNG_56d8303e…json`
- GLM 日志：`~/EnzymeAgent/v43cTH/ti_run_47068104.out`
- DeepSeek 日志：`~/EnzymeAgent/v43cTH/ti_run_47068110.out`
- monitor 日志：`~/EnzymeAgent/v43cTH/ti_monitor_47068118.out`
- 跨批 case：`~/ppv1_hpc/batch/{t_h_s5b_298_20261020r2,chain14a_s5b_20261015,chain14b_s5b_20261015,chain13_s5b_20261014}/cases/<qid>.json`
- 本地证据：`docs/review_evidence/ti_b3_stop_triage_2026-10-21/`（本报告的筛选读数与 SHA256SUMS）