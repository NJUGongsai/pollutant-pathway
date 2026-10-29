# chain14 发车物与 mimo 修正案整体代审

**结论：不放行。发现 4 项 P1，未发现 P0；另有 1 项非阻塞 P2 诊断缺口。** 本裁定按 CC 本轮委托用于发车门，本会话未部署、发车或自动回修。

| 阻塞项 | 已证后果 | 最小回修 |
|---|---|---|
| P1-1 真实反馈登记为 scripted，漏占额度 | 每题上限设 3，组合路径实际发送 4 次，仅预约 3 次 | 反馈沿实际 provider_kind 登记；全部真实发送共用每题预算，第四次发送前拒绝 |
| P1-2 重试成功响应无法崩溃重放 | 成功响应已落完整 blob，恢复却被原 failed 请求挡住 | 校验来源与唯一重试后继的身份，恢复消费已有有效响应，禁止新增付费调用 |
| P1-3 worker 恢复参数不匹配 | 合法中断 run 被 TypeError 写成失败终态 | 删除不存在的 profile_policy 参数，补公共 worker 恢复正负控 |
| P1-4 已冻结 A 的副本丢失后静默变 B | 实际载荷和 case 为 on，批报告仍报 off | worker 接收可信预期开关并核冻结副本；缺席拒绝；接纳 case 前核对同臂 |

审核对象：实际 HEAD `b4b89dc4ef525ed5c729e478ff4f2e677b0e3f16` 之上未提交工作树。题域仅 **298=RHEA 通用酶学/已见题**；本轮全部执行使用合成输入，不推断真实发生率、hit 收益或科学性能。内部代理分工不构成独立性背书，结论以源码与可复现程序证据互证为限。

## 1. A 臂字节兼容与全入口：字节通过，整体未闭合

off 首次 decide 与格式反馈均实际经过公共调用链，与历史 `b4b89dc^` 的原 `build_proposals_user_payload` 函数逐字节相等，含 JSON 键序。基线用 git 历史源码的 AST 提取，未靠重写当前实现充当历史。on/缺省两条路径有证据字段；正常冻结 A 的载荷、case、批报告均为 off；非法值、缺键、坏 JSON、null 均拒绝。直接 runflow resume 换臂返回 `evidence_card_flag_mismatch`。见[开关探针结果](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/chain14_launch_codex_2026-10-16/switch/stdout.json)。

**P1-3：公共 worker 恢复走不到开关门。** [s5b_worker.py:170](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/s5b_worker.py:170) 对已有身份调用 resume，并在第 173 行传 `profile_policy=None`；[runflow.py:1837](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/runflow.py:1837) 的签名没有该参数。真实协调者冻结 A 后，用公开 crash 注入造出“已有 run 身份、尚无正式 case”的合成中断状态；case validator 判为待恢复。实际 worker 返回 4，写 `failure_kind=TypeError`，原协调者接纳为失败终态，`n_failed=1`，没有新增模型发送。证据：[中断 worker 结果](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/chain14_launch_codex_2026-10-16/switch/interrupted_worker_stdout.json)。

无效参数在 HEAD 已存在，但本轮明确验收 worker/resume 与断点恢复，属于本轮必经入口，不能以“非新差分”放过。已完成且有有效 case 的题正常会 skip；本报告不声称 smoke10 必然重跑已完成题。最小修法是删无效参数，保留显式开关；验证中断 run 同臂恢复与换臂拒绝，不能只测直接 runflow resume。

**P1-4：副本缺席不能证明是手动批。** [s5b_orchestrator.py:166](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/s5b_orchestrator.py:166) 对整份文件缺席返回 None，[s5b_worker.py:91](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/s5b_worker.py:91) 转 True。探针仅在 tmp 中，于真实协调者冻 False 后、worker 启动前移走副本：worker rc=0、case completed/on，实际模型桩载荷含 substrate_evidence；原 loop 接受该 case，最终批报告仍为 False。正常文件在位的 A 是合法正控。证据为上述开关结果中的 `genuine_coordinator_off_copy_lost_before_worker`。

[s5b_orchestrator.py:792](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/s5b_orchestrator.py:792) 读终态时未核臂，第 892 行从协调者内存写批级开关，因此错误不止披露层。最小修法：可信批上下文显式传预期 bool，worker 要求冻结副本在位、严格 bool、同值；手动兼容若保留须明确进入手动模式。case 在 skip/汇总接纳前也核同源开关，不应仅把缺席默认值反向改成 False。

## 2. 重试语义与计费：有限部分通过，预算与重放不通过

可接受的部分：transport_error/empty_response 至多重试一次；timeout、鉴权付费拒绝、资源拒绝、429 有界退避耗尽不新增重试。两连败仍以 `real_model_transport_failure` 结束，失败未吞、仍导出；剩余额度不足时保留原失败，已发请求不退款。retry_of 指向对应首发，purpose 沿来源；[model_protocol.py:270](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/model_protocol.py:270) 排除同轮 retry，不多算格式反馈轮。见[重试探针结果](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/chain14_launch_codex_2026-10-16/retry/probe_retry_result.json)。

**P1-1：反馈首发漏记真实预算。** [runflow.py:1196](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/runflow.py:1196) 将反馈登记硬编码为 SCRIPTED，第 1215 行随后仍走 real fetch；[search.py:1723](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/search.py:1723) 仅 real 占真实额度。新重试在 [real_model.py:916](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/real_model.py:916) 又按实际 provider 登记，于是“首发失败→重试返回坏字段 JSON→反馈首发失败→反馈重试成功”实际发 4 次，只有 3 个 real 预约，整题无 run_error；反馈首发行 network_request_count=0。

这已用真实 RealModelAdapter、OpenAICompatibleClient、FileRateGate 互证，只有 urllib.urlopen 完全替换为本地桩：503→200坏字段→503→200合法，HTTP 桩 4 次、gate.total_requests=4、real 预约 3。cap=3 正控在第 4 次 HTTP 前拒绝，所以全批硬门没有旁路，出问题的是每题预算。逻辑模型请求、HTTP 尝试、gate 次数必须分开讲；既有 429 可在一个请求内占多个 HTTP 尝试。本轮零真实网络/费用。证据：[client/gate 结果](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/chain14_launch_codex_2026-10-16/retry/probe_http_gate_result.json)。最小修复是反馈沿实际 provider 登记，证明同组合第四次发送前被每题预算拦住，保留正常及单支重试正控。

**P1-2：完整成功 blob 被旧 failed 来源遮住。** 公开 start 先失败再重试成功，在 fetch 结束、解析前用既有 `after_request_registered` 注入崩溃；同配置公开 resume 仍找到原 request_key。原行 failed、重试行 responded 且 blob 完整，恢复却以 `request_not_consumable` 结束，调用前后都为 2；单次成功正控同点崩溃可零新增调用恢复。原因是 [real_model.py:649](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/real_model.py:649) 只定位来源，第 740 行直接拒 failed，第 950 行的重试成功只返回当次内存。见重试结果 `retry_success_replay_negative` 与 `single_success_replay_control`。

最小修法是建立可验证的来源→唯一重试终态链，核 run/action/provider/purpose/attempt/payload 与 retry_of 后，消费既有 responded 或 sent+有效完整 blob；缺失、损坏、错身份继续拒，禁止为恢复另发付费请求。补公共 start→crash→resume 正负控，不以重算新键掩盖坏记录。

**非阻塞 P2：逐 HTTP 留痕证明说满。** [llm_client.py:418](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/adapters/llm_client.py:418) 记录 HTTPError，但第 500 行成功路径未 append 当前 http_attempts；网络异常也不完整。真实 client 的本地桩 4 次发送只记 2 条 attempt，429→503→200 为 3 次发送仅 2 条。新测试 stub 自行为成功补条，不能证明生产完整记录。这是旧诊断缺口，gate 仍诚实、调用行仍在，不另加阻塞门；须更正交付声明，后续可补成功/异常/429 同源记录。

## 3. 四条实施偏差：①③接受，②需改，④有条件接受

| 偏差 | 裁定及依据 |
|---|---|
| ① None→True | 接受兼容直连缺省；wrapper 第 39、59–70 行两臂显式传值，协调者第 712、722、730–741 行冻结、同批比对；不豁免 P1-4 |
| ② worker 副本缺席回退 on | 不接受；已冻结 A 丢副本的公共反例证明真实换臂且错账，按 P1-4 回修 |
| ③ transport_error/empty_response | 接受有边界的重试族；timeout/永久拒绝排除合理，不要求扩族 |
| ④ gate_max_calls=4470 | 硬门接受；298题域×每题3个预算请求×每请求至多5个既有HTTP尝试的前提须先修 P1-1；重试应吃这3个之一，无需抬门 |

## 4. mimo 增量与版本：通过本验收面

[candidate_evidence.py:63](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/candidate_evidence.py:63)、第 65/66 行三处 SMARTS 实际用 RDKit 及渲染函数复核：乙酸不报羟基，乙醇及乳酸醇臂保留；一级/二级酰胺不误报胺，乙胺、苯胺、普通二级胺正控保留。[real_model.py:188](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/real_model.py:188) 起四句说明记账非机制、两类 unknown、电荷按所绘形式及未知不单独据以弃权；T2–T8 实际通过，未教模型内部 JSON 值。

schema 保持 candidate-evidence-2（第 45 行）；SMARTS 计算语义变更由 descr-2（第 47/281 行）披露。提示词哈希精确为 `fe9eaf770deb19f8c6eec9aee14febe83f6b2d47f53e1c60002bb808eb3b0f4e`、UTF-8 6123 字节，与 [T1:163](/Volumes/CC/Enzyme_Agent/dependingv43/tests/test_controlled_vocab_ci.py:163) 相同。源码全树、依赖身份仍承载变化，无本增量静默漂移；该判断不替 P1-2/3 的恢复缺陷背书。

## 5. 四件发车脚本：脚本结构通过，依赖的运行链仍阻塞

[wrapper:39](/Volumes/CC/Enzyme_Agent/dependingv43/scripts/hpc/chain14_run_wrapper.py:39) A=False/B=True；stub 捕获公共实参，除开关外完全同构：复用 chain13 profile，请求3/反馈2、workers8、RPM200/TPM3M/gate4470。build/run/score 按 ARM 派生分立批根及 runs 根，build 题卷参数与 chain13 固定 SHA 门保持同构，本轮不读题卷。

[run:29](/Volumes/CC/Enzyme_Agent/dependingv43/scripts/hpc/sbatch_chain14_run.sh:29) 的批准/no-cap 文件分别缺席时，均在任何 Python 前退出1；三段2→10→全量，各接 run-gate。[score:30](/Volumes/CC/Enzyme_Agent/dependingv43/scripts/hpc/sbatch_chain14_score.sh:30) 先全终态门，再v1、改名三件`.v1`、再v2。tmp 内 fake PY 拦截 A/B 各11条下游命令，归一化臂名与根后全等；实际 gate 对合成298个qid，缺case拒、297 completed+1 failed接纳。未执行真实 build、评分或模型。详见[化学/脚本证据](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/chain14_launch_codex_2026-10-16/chem_scripts/READOUT.md)。

## 6. 发车放行：不通过，按四项 P1 回修后同范围复核

执行边界：新 tmp 副本含 src/vendor/必要 metadata，禁 pyc 与 pytest cache；本机 Python3.11.16/RDKit2026.03.6，未访问HPC确认其版本。三个关键测试原样隔离为48过/5项缺资产清单失败；仅将资产身份替为 scripted 并使用源码根外 TMPDIR 后53过。审核期间交付书被交付方并发回填为2175/0/16（338.7s），这是其执行声明，本审未重跑该全量，不据自报认证；并发变化已单存 diff 和最新快照，未回改原件。第一次 TMPDIR 位于副本内被合法输出根守门、初次二甲胺匹配数预期错误等审核探针问题已纠正，失败日志保留，未执行的内部断言未报通过。

源码/测试/脚本前后哈希未变，缓存检查为零；[最终回查](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/chain14_launch_codex_2026-10-16/final_postcheck.json) 区分了交付书的外部回填，证据哈希见[最终清单](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/chain14_launch_codex_2026-10-16/FINAL_MANIFEST.sha256.json)。命令、脚本全文、合成输入输出在本轮 switch/retry/chem_scripts 分目录。本审未改 src/tests/既有 docs/AGENTS，未 commit/push、外部模型或真实调用。修复应仅闭合 P1-1～P1-4，保留合法正控；不追加科学性能门，本次不自动修复、部署或发车。

**总体裁定：不放行（回修P1-1～P1-4后同范围复核）。**
