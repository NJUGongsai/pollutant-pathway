# EC298 Phase D R1 修复报告:产物完整性、pb_0117 TypeError、批次完成门禁与费用账

> 任务书:[TASK_V43_EC298_PHASE_D_R1_REPAIR.md](TASK_V43_EC298_PHASE_D_R1_REPAIR.md)。
> 实施会话:2026-09-28 晚 — 2026-09-29 凌晨;本报告为交付物,供独立 review。
> 结论先行:**四类阻断项全部闭环,完成状态 `ready_for_298`**。该状态只表示阻断修复
> 通过,**不代表 D-3 已提高命中或获准发布**;下一轮为已见 EC298 配对复测
> (`seen298_post_hoc_repair_check`),按 [复测任务书](TASK_V43_EC298_PHASE_D_RETEST_298.md) 执行。
>
> 通俗版:[EC298_PHASE_D_R1_REPAIR_REPORT_PLAIN.md](EC298_PHASE_D_R1_REPAIR_REPORT_PLAIN.md)。

## 0. 开工边界与封存(任务书 §1)

| 项 | 值 |
|---|---|
| Git HEAD(开工) | `9509985686259b0c29a2ebb70b210d048ec92620`(分支 v4.3) |
| 开工 git status | 仅 `?? docs/TASK_V43_EC298_PHASE_D_R1_REPAIR.md`(无其他会话活跃写盘) |
| HEAD 含 | 既有 str 键修补(donor_applicability 7 处 alignment str 化)+ 回归钉(413 基线) |
| r1 跑批代码(Chenyu) | aggregate `ca15d2ad…`,与 HEAD 差异仅 `domain/policy.py`+`services/donor_applicability.py`(即 r1 跑的是修补**前**代码;`prediction.py`/`nodes.py`/`atom_tool.py` 与 HEAD 逐字节一致——这是 R1-b 定根因的关键证据) |
| 修复后代码身份 | aggregate `07fef84f0945bcba055a6424d37efcab2c60ebf47cd1d639d676dd00133764bc`(50 文件) |
| 资产双清单 | `verify_repo_manifest` 通过:manifest `ac9b97b872c9666eebbe32b42c626997aca34438ade17d7bbf36a8154b848e6c`,22 文件 / 166,849,006 字节;运行资产仍为 v1,`reactant_similar_enabled` 发布默认关闭 |
| 金标隔离 | 修复全程未读取金标;smoke 底物取自输入清单 `root_smiles`(运行侧白名单字段,非金标) |

**只读封存(未改写任何旧产物)**:

- 四臂关键文件 16 项 SHA:`reports/phase_d/r1_four_arm_seal.sha256`(远端
  `runs/phase_d_{C0,D3,D5,D10}` 的 batch_identity / batch_report /
  merged 元数据与答卷)。
- 逐臂 20 路线审计表(终态/导出/答卷 SHA/usage):`reports/phase_d/r1_four_arm_audit.json`(远端生成后字节一致回传,SHA 复核通过)。
- pb_0117 事故现场产物(两个 run 的最后 decision/retrieval、D-3 checkpoint.sqlite)只读拉取至本地 `/tmp/pb0117_fixture/`,脱敏切片入库 `tests/fixtures/phase_d_r1/pb0117_d3_similarity_selected.json`(凭证扫描干净)。

**r2 残留批次处置**:开工时发现 Chenyu 上 `runs/phase_d_r2_C0` 仍在活跃运行
(18/20 终态、已发 80 次调用、pb_0117/pb_0447 仍在计费)。任务书 §6.4 已明确
用户决定不再进行 dev 20 r2,遂于 2026-09-28T15:13:22Z 记录现场快照
(progress/coordinator 尾部/进程表,存远端 `/tmp/r2_stop_evidence`)后停止
driver 与两个 worker 进程,批次目录原样保留并写入 `STOPPED.json`
(注明停止依据)。该批次无 merged/batch_report,数据未用于任何结论。

## 1. R1-a:产物指纹不稳定 — 根因、修复、验证

**根因(r1 真实产物复现)**:`assess_alignment` 返回的 `alignment` 是 int 键
dict(供体 map 号 → 当前原子索引,如 `{2:0, 11:8}`)。写入时 `canonical_json`
的 `sort_keys` 按**数值序**(2<11),JSON 落盘后键变字符串,重读按**字典序**
("11"<"2"),`content_hash` 写读不一致 → `ArtifactIntegrityError`。凡 decision
资格块含失败明细 `results[*].alignment` 的路线,后续任何重读(主循环下一步、
resume 幂等检查、导出 verify)必然失败,worker 把该路线记 0 交卷——模型其实
答了。具体 JSON 路径:
`payload.analogy_eligibility.cards[*].donor_evals[*].results[*].alignment`
与 `…selected.alignment.alignment`。

**修复(方案:生产者统一转字符串键,版本化)**:

- `donor_applicability.py` 7 处 `alignment: {str(d): c …}`(成功/失败/歧义/
  预算外各分支),随 `assess_donor` 透传 `mapped_lhs/mapped_rhs`;
- `APPLICABILITY_VERSION` → `v43-applicability-3`,`selected` 新增 `donor_ref`
  (见 R1-b);
- 读取端不放宽:`ArtifactStore.read` 哈希不符仍抛 `ArtifactIntegrityError`,
  不静默改写、不当正常缺失。

**验证(无凭证,`tests/test_artifact_fingerprint_r1a.py` 14 项)**:

- 7 个化学夹具 ×(无相似通道/带相似通道)全分支:资格块整树无 int 键 +
  canonical 双往返字节稳定;
- 多位映射号(2/11/13)机理钉:数值序 ≠ 字典序即分歧源;int 键 payload 写入
  后重读必炸(存储层守卫拦截演示);
- 真实故障结构 decision:写→读→再读三次哈希一致;同键同内容幂等、异内容
  `ArtifactConflict`;
- 单字段/单字节篡改被拒(field → `ArtifactIntegrityError`,byte → 同样
  fail-closed,JSON 损坏时 `JSONDecodeError` 不吞错)。

**冷跑 vs 合法 resume(`tests/test_r1a_resume_consistency.py` 2 项,子进程
硬杀注入)**:同配置冷跑与"classify 落盘后硬杀→resume"的**事件、资格块、
导出 SHA 逐项一致**;已完成 run 再 resume 零改写。**损坏旧 run 不能靠新代码
resume 当作已修好**:decision 被篡改后 resume 以非零退出显式报完整性错误,
损坏文件字节原样保留(不被静默修复)。r1 四臂产物未做任何 resume;修复后
验证一律使用新 run ID(新身份自动拒绝旧 run resume)。

## 2. R1-b:pb_0117 两次 TypeError — 根因闭环

**证据链(Chenyu r1 现场,非推测)**:

- D-3 `dev_2f824816_pb_0117` 最后产物 = `T_fd4dd1ca…/decision.json`(其
  task 目录只有 decision),D-10 `dev_2fab5f1a_pb_0117` 同形
  (`T_74bde163…`);mtime 序列证明崩溃发生在 classify 写盘后、下一节点;
- 最后 checkpoint(崩溃前 1 秒)state:`phase="select"、
  prediction_mode=""、prediction_failed=true、prediction_task_id=""` ——
  正是 `_hold_or_dead` 的返回形状;
- worker 日志仅一行 status(r1 的 `run_worker` 只记类型+消息,traceback 未
  落盘 —— 本次已补 `failed_traceback` 字段);
- **r1 跑批代码与 HEAD 仅差 policy.py/donor_applicability.py**,故
  `prediction.py`/`nodes.py`/`graph.py` 的事故行为可由当前代码直接推演复现;
- C0/D-5 的 pb_0117 均为合法 `awaiting_prediction`(其资格块未走相似通道
  selected),只有 D1 臂(D-3/D-10)踩雷。

**根因(两个 bug 叠加)**:

1. **触发器(Bug A)**:D1 相似检索通道选定的供体 `evidence_id=
   "reactant_similar_channel"` 是资格块内部的载体卡,**不在检索 evidences 中**
   (D3 现场检索 116 卡、D10 203 卡,均无此 id;D3 连 record_id 都无卡携带)。
   `build_prediction_task` ANALOGY 分支按 evidence_id 找卡落空 → 抛
   `PredictionTaskError("selected_donor_card_missing")` → `_hold_or_dead`
   (意图安全停留)。
2. **放大器(Bug B)**:`graph.py` 的 `prepare_prediction → call_model` 是
   **固定边**,`_hold_or_dead` 只改 state 字段无法改变路由 → 控制流仍进
   `call_model`,以空 `prediction_task_id` 读产物,
   `read(...)["payload"]` 对 None 下标 → **裸
   `TypeError: 'NoneType' object is not subscriptable`**,worker 崩溃。

**修复(三层 + 防御,`STRATEGY_VERSION` → `v43-policy-5`,旧 run 自动拒绝
resume)**:

1. `v43-applicability-3`:`selected.donor_ref` 携带所选供体完整引用
   (record_id/资产定位/**mapped_lhs/mapped_rhs**/find_channels/相似度);
2. `prediction.py` 兜底:ANALOGY 分支 evidences 找不到卡时,凭
   `selected.donor_ref` 在任务内**合成载体卡**(不回写检索产物);旧形状
   (无 donor_ref)仍显式 `selected_donor_card_missing`,不静默换供体;
3. `graph.py`:`prepare_prediction` 改条件路由 `route_after_prepare`
   (phase=call_model 且有任务 id → call_model;否则回主循环);
4. 防御层:`call_model` 入口与 `_read_decision` 对空 task_id/缺失产物抛
   `NodeStateError`(结构化,带 run/task 身份),图结构损坏不再伪装成裸
   TypeError;
5. `run_worker` 终态状态文件新增 `failed_traceback`(教训:本次排查成本
   主要来自 traceback 未落盘)。

**验证(无凭证,`tests/test_phase_d_r1_repair.py` 8 项)**:donor_ref 随行与
往返稳定;任务组装兜底成功(合成载体卡,transform/映射齐备);旧形状显式
失败;路由单元;call_model 双守卫(含旧表达式 TypeError 机理复现对照);
真实 pb_0117 切片(r1 现场输入)旧形状 → 结构化错误、补 donor_ref → 组装
成功;端到端相似通道轮次存活(run 合法终态不崩溃)。

**Chenyu 烟测(§6.2,详见 §6)**:pb_0117 底物同款情形真实重现——资格块
`applicable`、`selected.evidence_id=reactant_similar_channel`、
`donor_ref` 12 键齐备,decision 写读哈希稳定,run 正常终态并导出 verify
通过。**闭环状态:两臂(D-3/D-10)根因均已闭环,无 unresolved 项。**

## 3. R1-c:批次完成、归并与配对评分门禁

**机器可读路线状态(`batch.classify_route_state`,schema
`v43-route-state-1`)**:每路线五类 ——
`success_completed`(run 完成+导出)/ `legal_stop`(awaiting_prediction、
budget_exhausted、invalid_input 等**合法终态**,空答卷也是合法答卷)/
`failed`(worker 记录异常失败,含失败类别 `failure_class`;**即使
export_ok=true 有部分答卷也不算成功**)/ `export_failed` / `missing`(无终态
状态文件或无 stop_reason)。判定只认 worker 状态文件的持久事实,**不信批次
报告汇总字段**(r1 四臂 `status="completed"` 却有 52 条失败路线正是该形状)。

**批次终态(`batch.batch_terminal_summary`)**:`completed`(全部合法终态)/
`incomplete`(有缺失,无失败)/ `failed`(任一异常失败或导出失败);输出
`n_expected / n_valid_terminal / n_success_completed / n_legal_stop /
n_failed / n_export_failed / n_missing` 与三类失败路线清单。
`batch_report.json` 的 `status` 由该汇总得出(不再无条件 completed),并附
完整 `terminal_summary` 块。

**归并保留失败标志**:`merge_predictions` 元数据新增
`batch_terminal_status / n_routes_failed / n_routes_export_failed /
n_routes_missing / failed_route_ids / missing_route_ids`,逐路线
`per_route[*].route_state`。固定 20 行只是文件形制;`answer_kind` 语义
不变(full/partial/empty/fallback_empty)。

**配对评分门禁(新模块 `output/pairing_gate.py`,schema
`v43-pairing-gate-1`)**:`validate_arm` 六层只读校验 —— 冻结输入清单
(白名单声明/ route_order 与预期一致/无重复)→ 批次身份自洽(重算 identity
体哈希)→ 逐路线 worker 终态分类 → 归并元数据(行数/唯一 route_id 集合/
失败标志交叉核对)→ 逐路线答卷 SHA(元数据 vs 文件实算)→ 归并行 route_id
唯一且恰为清单。`paired_release_verdict`:全臂通过 → `complete`/
`release_eligible=true`;任一臂违规 → `diagnostic_incomplete`/
`release_eligible=false`(可出显式标记的部分诊断,不得作发布型配对结论)。
`scripts/phase_d_paired_scoring.py` 已接线:**评分前先过门禁**(门禁结果落
`pairing_gate.json`);`complete_20_of_20` 受 verdict 约束——行数 20 只是
形制,verdict≠complete 时恒 false。输出 schema 升 `pd-paired-2`。

**失败恢复边界**:批次 resume 沿用既有身份/调用账本安全规则
(`batch_identity_conflict_check` 同根异身份拒绝;worker resume 走既有
task_id 幂等,不重发已提交调用)。r1 四臂不恢复、不重标。

**验证(`tests/test_pairing_gate.py` 12 项 +
`tests/test_r1_end_to_end.py` 1 项)**:七类失败夹具各断言**发布判定被阻断
或放行**——(1) 20 行全在但 1 行 failed 且 export_ok=true → 阻断;(2) 失败后
部分答卷(有内容)→ 阻断;(3) 失败后空答卷 → 阻断;(4) 合法
awaiting_prediction/budget_exhausted 空答卷 → 放行;(5) 少 route_id →
阻断;(6) 重 route_id → 阻断;(7) 答卷 SHA 与元数据不一致 → 阻断;另加
身份篡改、清单不一致 → 阻断;全合法 → complete+release_eligible。
端到端单链(任务书 §6.1):真实 worker 子进程落盘 → 崩溃注入 → 协调器
respawn 走合法 resume → 批次终态 completed → 归并导出 → 门禁放行;再注入
1 条失败路线 → 批次翻转为 failed + 门禁 diagnostic_incomplete。

## 4. R1-d:费用账与硬上限

**保留诚实语义**:`cost_estimate_cny="unknown"` 当存在任何缺 usage 调用;
`cost_estimate_known_usage_cny` 为已知 usage 按价格快照的小计。r1 四臂审计:
known-usage 小计 0.5211/0.8259/0.6447/0.7597 元,合计 **¥2.7514 只是已知
部分估算小计,不是四臂总费用**;50 次调用缺 usage(7/16/11/16,全部为
transport_failed/超时),0 孤儿。

**逐调用明细(`api_account` 新增 `calls` 列表)**:每调用一行 ——
run/task/attempt、status、error_kind、HTTP 尝试数、usage_present、
known_tokens、elapsed_s。烟测现场示例:超时调用(attempt 1,300s,无 usage)
与重试成功(attempt 2,usage 6848 tokens)逐行可查。

**usage 缺失的保守预留(`conservative_reservation` 块)**:输出侧上界按
**可证明口径**——输入 = 已发出请求文本长度 `//4` 字符的 token 上界(请求侧
事实);输出 = **无请求级 max_tokens 上限,上界不可证明**
(`unprovable_no_request_output_cap`,费用记 null,不臆造);孤儿调用无请求
文本单列计数。`basis` 字段明文:须以服务商用量/账单回填核对后费用门才可
报绿。**未给出可信输出上界前,不宣称费用硬门通过。**

**价格快照**:现有快照 `checked=2026-09-25`(如实保留,未伪造成当天)。
**下一轮 298 付费前必须重新获取并存档来源/日期/模型/区域**(见 §6 冻结清单;
复测任务书 §1 亦已列此项)。

**验证(`tests/test_api_account_r1d.py` 6 项,无网络)**:全 usage(给数)/
部分缺失(unknown+小计+预留)/全缺失/超时后成功重试(旧 attempt 缺、新
attempt 计入)/孤儿(计数不估算)/价格快照逐字保留。

## 5. 旧结论更正说明(旧数据不重写)

r1 四臂原始失败分布(逐臂审计表,`reports/phase_d/r1_four_arm_audit.json`):

| 臂 | 归并行数 | 异常失败 | ArtifactIntegrityError | TypeError(pb_0117) | 旧报告 status |
|---|---:|---:|---:|---:|---|
| C0 | 20 | 11 | 11 | 0 | `completed`(无效) |
| D-3 | 20 | 12 | 11 | 1 | `completed`(无效) |
| D-5 | 20 | 12 | 12 | 0 | `completed`(无效) |
| D-10 | 20 | 17 | 16 | 1 | `completed`(无效) |
| 合计 | 80 | 52 | 50 | 2 | — |

- 旧版报告的"四臂各 20 行完成"只是答卷**形制**;真实成功终止(合法终态)
  分别为 9/8/8/3 条路线。
- 旧版 D-3 对 C0 的"0 赢 / 2 输"与"相似检索使成绩下降"是**受失败污染的
  观察**(52 条失败路线被记 0 交卷,且失败路线在臂间不均衡),不能作为发布
  判定,亦不能反推"D-3 已证实变差"。
- r1 数字(含 hit@1 各档位、¥2.75)仅作事故记录;**修复后判定一律以新批次
  为准**(下一轮 seen298 复测)。
- 旧产物零改写:封存 SHA 见 §0,`reports/phase_d/r1_four_arm_seal.sha256`
  可在授权环境回查。

## 6. 验证记录与 298 交接

**本地全仓无凭证回归**(2026-09-29,
`OMP_NUM_THREADS=1 PYTHONPATH=src python -m pytest tests/ -q`):
**456 passed / 0 failed**(基线 413 + 本次新增 43:
fingerprint 14 + pairing_gate 12 + r1_repair 8 + api_account 6 + resume 2 +
e2e 1),耗时 8m01s。

**Chenyu 远端回归**(同命令,`.venv`):449 passed + 5 failed + 2 skipped →
5 个失败全部为远端**历史部署缺脚本**(`scripts/phase_c_offline_audit.py`、
`scripts/ec298_phase_a.py` 等未同步,与本次修复无关),补传后该套件
**5 passed**;修复相关 9 个源文件本地↔远端逐字节 SHA 核对一致。

**资产双清单**:本地通过(§0);远端资产与本地同源(Phase D 部署口径)。

**Chenyu 烟测(§6.2,2026-09-28/29,零金标)**:

| run | 底物 | 结果 |
|---|---|---|
| `smoke_r1_pb0117` | pb_0117 同款羟基丁烯酸根 | 资格 `applicable`、selected=**reactant_similar_channel**、donor_ref 12 键齐备;decision 写读哈希稳定;run completed;导出 verify ok;31.4s |
| `smoke_r1_pb0117_d2` | 同上(depth2) | 2 decision 全部写读稳定;导出 verify ok |
| `smoke_r1_pb0002` | pb_0002 炔苯酰草胺 | 3 调用:1 次超时(300s,usage 缺失)+ 重试成功(usage 6848 tok);**调用不重复**(无孤儿);2 decision 写读稳定;导出 verify ok;答案 2 步 |

烟测费用:3 次真实调用(已知 usage 部分 13,025 total tokens ≈ ¥0.03 量级
+ 1 次超时调用未知)单独登记于此,不计入任何批次账本。产物保留于远端
`runs/phase_d_r1_smoke/`。

**298 冻结配置与 `ready_for_298` 交接清单**:

1. 代码:本地修复版(本报告同分支工作树;建议提交后以提交 SHA 为准)+
   Chenyu 同步(9 文件字节一致;远端补齐 2 个历史缺失脚本);代码身份
   aggregate `07fef84f…`;
2. 资产:v1 双清单 `ac9b97b8…`(22 文件);v2 **不进运行时**(未过独立人工
   化学复核);发布默认 `reactant_similar_enabled=false`;
3. 策略/prompt:`STRATEGY_VERSION=v43-policy-5`、
   `APPLICABILITY_VERSION=v43-applicability-3`;prompts 版本随
   `prompt_versions()` 冻结进批次身份;export policy/scorer(v2)不变;
4. 臂定义:C0(v1+关闭)与 D-3(v1+D1 固定参数:threshold 0.45/top-K 16/
   每父上限 3),**唯一预期差异为相似检索开关及其固定参数**;总 API 并发
   ≤40;协议参数沿复测任务书 §1.4;
5. 费用:价格快照发车前重取并存档;缺 usage 按本报告 §4 保守预留规则记账,
   未经账单回填不得报费用门绿;
6. 入口:复测执行协议 = [TASK_V43_EC298_PHASE_D_RETEST_298.md]
   (TASK_V43_EC298_PHASE_D_RETEST_298.md);结果统一标
   `seen298_post_hoc_repair_check`,金标只由两臂运行结束后的独立评分进程读取。

## 7. 残余限制

- 输出侧 token 上界在当前请求参数(无 max_tokens)下不可证明,费用硬上限
  须依赖账单回填(§4);若要求运行时硬门,需在下一轮请求参数冻结输出上限
  (属共同变更,须两臂同时冻结)。
- `pb_0117` 的修复路径已闭环,但 D1 相似通道的**化学有效性**(相似供体
  召回"结构可施加但化学不搭"的情形)仍靠下游门禁兜底,是 Phase E 的既有
  议题,不是本次修复范围。
- r2_C0 半途批次(18/20)仅作存档,不参与任何判定;如需恢复须按新身份
  重开(旧 run 因代码身份变化会被 resume 拒绝,符合预期)。
- 本次未实施 Phase E 的超时、排序、预算或语料优化(任务书边界)。

## 8. review 硬门自检(任务书 §7)

| 硬门 | 状态 | 证据 |
|---|---|---|
| ArtifactIntegrityError 写读/恢复仍可复现 | 否,已修 | §1 十四项测试 + 冷跑/resume 一致性 + Chenyu 写读稳定 |
| pb_0117 根因未闭环 | 已闭环(两臂) | §2 证据链 + 三层修复 + 真实切片与烟测 |
| 异常失败仍能通过完成/配对门禁 | 否 | §3 五类状态机 + 门禁七情形 + 端到端翻转 |
| usage 缺失被当作已知总费用 | 否 | §4 unknown 语义 + 逐调用明细 + 保守预留 |
| 旧产物被改写 | 否 | §0 封存 SHA 可回查 |
| 确定性化学门禁被放宽 | 否 | 仅加严(recorded 资格/裁决/AtomTool 门禁零触碰) |
| 旧失败数据表述为四臂全完成/D-3 已证实变差 | 否 | §5 更正说明 |

**结论:`ready_for_298`**(阻断修复通过;D-3 命中效果未判定,待复测)。
