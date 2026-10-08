# S3b 生产链与首次消费专项独立复核

- 审核仓：`/Volumes/CC/Enzyme_Agent/dependingv43`；实际 HEAD `c1211183c0874b12c5b5461845d3c61f0a84719c`，父 `b7f2bba02ca49edd0a45a13bc9b8434909d99175`。
- 验收固定为 S3 任务书 §3/§6/§7、S3a-r4 报告 §8；不认证科学性能，不要求机制库、全库抗一致重造或 S4/S5。
- 本专项 **无 P1**。实际调用固定工具/诊断/converter/audit/admission/公共事件 writer/search complete，保留诚实 unknown，AuditContractError 不吞成成功。
- 一次执行 **17 个合成案**，raw assertion **13 pass / 4 fail**。三项是评审脚本错误预期/字段位置，另一个按既定实际复用范围裁为 P2。原脚本、原结果、原失败日志全部保留；`adjudicate_capture.py` 仅检查已捕获 JSON，**不再执行任何探针/工程代码**。不得写成“17 个原断言通过”。

## 1. 公开链到达边界

`results.json` 每案包含完整输入、真实函数轨迹、返回/异常、15 张表全量行、JSON artifact 内容与哈希。`trace_pipeline` 包装真实函数并调用原函数；只在声明的反例边界更改 converter 输出或存储资料，未伪造 AtomTool 成功。

| 案 | 入口与观察 | 固定契约裁定 |
|---|---|---|
| legal | `workflow.runner.start_run`，真实 render→execute_edits→donor→converter→audit→admission→submit→complete，1事件；中心 verified；无 legacy db | 合法正控；condition 等其余轴可能 unknown，中心 verified 不等于 R6 |
| missing_alignment | 同公开入口，unavailable 映射，1条件保留事件，中心 unknown | 不授中心 verified |
| missing_proof | 实际 converter 输出删除 proof_record，1条件保留事件，center_evidence_proof_missing | 缺证据不变成执行失败或通过 |
| execution_failed | 真工具无效 atom edits 返回失败，诊断三字段 None、diagnostic evidence={}、converter metadata+center_match=None，audit 调用0、0事件、attempt failed | 方法失败先于 audit 短路；与执行成功但中心缺证据分写 |
| target_deviation | 真实产物 CC=O，expectation 酸；当前假设绑定完整，strict=False，中心 **violated**、R5v retain_conditional，1事件 | 原 unknown oracle 错，原断言后余段未执行；只读捕获互证修正 |
| declared_product_differs | 冻结声明产品酸、真实工具输出醛，绑定失配、中心 unknown；事件身份仍冻结声明酸 | 允许 unknown 有界提交声明假设；不得称事件产品必然等于真实执行产品 |
| ambiguous_alignment | 模糊映射，中心 unknown、1条件保留事件 | 不强行洗成 resolved |
| full_balanced_extra_participant | 完整 CCO→CC=O+[H][H]，全部3参与物保存，元素/电荷 verified；H2 属已登记 composition-only 补全，中心 verified、许可范围机器披露 | 原 unknown oracle 错；H2 合法正控保持，不外推多原子初始图贡献/机制 |
| audit_contract_driver | 两个已经排队条目：B converter 自报中心改坏→AuditContractError；driver 窄捕获，B attempt failed/action done/outcome_recorded/event_id空；C 合法成功，事件恰1 | 失败结算不是成功完成；不是整库零写；只继续已排队 C，不证明自动激活 deferred |
| broad_caller_production | 真实 `expand_hypothesis_production` 外套 `except Exception`，坏 proof 仍上抛被抓，前后15表完全相同，0event/commit/hypothesis，action claimed | 实际函数宽捕获负控；真实 driver 自身无此宽捕获；不能把负控描述成真实 driver 捕获方式 |
| cross_hypothesis | 另一个真实甲醇→甲醛工具链证据喂当前公开乙醇链，绑定不匹配、中心 unknown，1条件保留事件 | 注册 checker + True 不是本假设证明 |
| raw_cx_factory_refused | 公开 start 坏池 `CC=O |atomProp:0.n,r|`→ChemicalStateError；kind=unregistered_cx_class、registered_head=atomProp；0event | malformed atomProp 项即拒，非独立 r 首头；prepare 异常原样逃逸 |
| hypothesis_constructor_refused | 公开 start 坏 participant_list_status→HypothesisContractError；0event | 构造拒不当 R2b/R1 行；原样 RuntimeError 逃逸 |
| context_envelope_tamper | 公开 start B1暂停后只改 context payload，公开 resume 留0event；run_error artifact_hash_mismatch，坏 artifact 原样保全 | H07 信封层正常拒 |
| context_content_tamper | 同边界改 scenario_ref 并重算信封 hash、保留旧 context_id；公開 resume→ConditionContractError/context_content_identity_mismatch，0event、坏 artifact保全 | 同源内容身份层正常拒；该 RuntimeError 原样逃逸无 stop report |
| state_appearance_hash_tamper | 见§2；新事件可先保存，complete 全SID旧出现重放拒；无event成功commit | unused历史出现 P2，不重开已关闭R8同hash复用 |
| state_semantic_fact_tamper | 根 formal_charge 改9保留 SID；put_state与真实公开resume事件首提交均 Ppv1EventConflict；0event | 未借新工厂重造洗掉损坏语义本体 |

## 2. unused 旧出现边界：不是 R8 同 hash 回退

`state_appearance_hash_tamper` 在 B1 暂停后的合成数据库中将 root occurrence `structure_smiles_raw` 改为 `CCO |r|`、保留旧 `appearance_hash=7c510820…`。同源根状态 `put_state` 返回 None，但此返回从来不是完整性证书。

真实 resume 以保存 identity/冻结 action 的 SMILES 组装新合法 substrate occurrence，`source_refs=[ppv1-substrate:<run>]` 与旧 `ppv1-root-input` 来源不同，故新 appearance hash不同。当前事件 manifest 和 links **不含坏旧 hash**。`store._collect_state_writes` 的 R8 实际同hash复用守卫没有被绕过：本事件根本未复用此旧出现。已有 store 源文件与父一致。

观察必须精确登记：events **0→1**；新事件的当前断言 occurrence合法；坏旧资料保全；随后 `complete_action` 的全SID历史出现重放以 `event_ledger_authority_failed`（内因 `appearance_hash_corrupt`）拒绝，action claimed、event_committed **0**，无成功预算消费/补账。本案是已定范围外的“unused 历史坏出现导致新事件先保留、结算后拒”边界，列 P2；不能声称零 event 写入，也不能声称旧坏出现经过认证或当前 event manifest已覆盖它。

`runflow._state_smiles` 本身仍只是读视图；事件权威路径恢复先有 `recover_run` 的真实提交/附件/状态验证。其独立读取不构成全 ledger 证书。不引入本轮的全库扫描增强门。

## 3. 其它 RuntimeError 原样逃逸边界

公开start坏池化学结构、坏假设状态及公开resume上下文内容身份损坏，分别执行得到 ChemicalStateError/HypothesisContractError/ConditionContractError；0event、无假设成功提交。当前prepare/load在生产窄try之外，drive捕获集合也不含三者，所以进程级调用返回异常、retrieval可以已有合法outcome记录、decide保持claimed、无统一stop/run_error报告。这是错误披露/包装 **P2**，不是错误verified、错误成功写入或被洗的旧守卫；AuditContractError义务闭合不得扩大成“所有契约异常均会方法失败结算”。

## 4. mimo v13 程序互证与落字

`static_checks.json` 保存15段带源SHA的逐行摘录，确切读码指针与运行证据分开。要更正/补齐：

1. **0d.8 文件名事实错**：`pollutant/runflow.py:214–223/315–319`是 reconcile/drive，不是两个公开 profile 分流；应为 **`workflow/runner.py`** 214–228/305–320。不是执行背书。
2. **strict False 加前置条件**：本案完整绑定strict=False实际violated；在 audit 1131/1164/1175 前置 binding、覆盖或 inconclusive 分支已unknown时不会到1188 strict分支。不要将“strict False⇒violated”写成无条件全称；原“至少unknown”也需要精确中心状态/R5v。
3. **execution失败前audit短路**：真实public failure trace audit0；中心证据不足但执行成功才audit unknown与其他轴verified并存。
4. **产品身份来源**：`spec.product_smiles`工厂派生；实际工具result只作核验输入。declared_product_differs执行例真实unknown、有界提交声明结构，不是工具输出身份强改。
5. **Audit异常零成功而非整库零变化**：真实driver窄捕获有失败settlement；宽捕获负控只指生产实际函数；继续已经排队独立条目，不自动激活deferred。
6. **R2b/R1**：decide_admission `contract_violation`参数是单独触发；此生产caller不传，AuditContractError中止，不降级R行。构造拒也不映射R1/R2b；不能推广R1全称不可达或删除防御行。
7. **λ_s×Δ不是无源承诺**：audit.py 973–979的两侧 `_completion_violations`分别用lambda_s*delta_pos/neg；coefficient_binding另在922–933；mimo的“本轮未确认”是自身采信边界，本专项已以源代码互证，不编造执行复算。
8. **各入口kind枚举是词法/解析内因子集**，非所有拒因全称；本轮 malformed atomProp实际kind与registered_head互证。
9. **条件相容≠条件事实真实性**；audit入口和derive父对象强制点是真实接线，上游assess/aggregate函数自身无新增强制门。
10. **G.1函数数量≠参数化绿案映射**：保留R4历史独立JUnit 11+1来源，本专项不重跑历史控、不因函数数冒充12绿。
11. AST当前src直接AuditContractError抛点 **10**，均在audit.py；新增生产窄捕获恰1个，runflow.py645；这个静态结果不证明未来/任意caller均不会吞异常。

真实RDKit跨版本往返未在本专项重跑；工程全量/父基线/G01由其它本会话专项独立执行，不能拿mimo或交付日志冒充。涉及novel/反馈、deferred计数与恢复窄窗口的结论交由队列专项，不抢范围。

## 5. 证据与纪律

执行仅 `/private/tmp/ppv1_s3b_production_84agv6jv`，隔离完整src/vendor/metadata，Python depending43明确路径、-B、PYTHONDONTWRITEBYTECODE=1、PYTHONPATH隔离src。probe一次1.52秒，socket connect被禁止且真实请求次数0；不读取真实题面/金标/封存run/旧v4/真实v3资产，不调用外部模型，不写主仓。模拟B1异常暂停不是硬杀验证，硬杀/进程barrier由其它专项负责。

`adjudication_v1`第一次只读重判把commit_kind常量误写为outcome，exit1；保留脚本/日志，改为真实outcome_recorded后第二次只读重判exit0。没有重新执行17探针。该修正不隐去原13/4或早停的内部断言。
