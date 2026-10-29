# chain14 发车物 P1 回修同范围复核（2026-10-16，代 CC）

**不放行 HPC 发车。P1-1、P1-3 关闭；原 P1-2、P1-4 各有一处同合同余项，仍未闭合。未发现 P0，不增加阻塞编号。**

本裁定只核上一轮四项 P1、修复是否越界及交付书§八四条偏差。对象为实际 HEAD `b4b89dc4ef525ed5c729e478ff4f2e677b0e3f16` 上的未提交工作树；题域标签：**298=RHEA 通用酶学/已见题**。本审输入全部为合成分子、合成池和本地模型桩，不据此认证科学收益。

## ① 四项 P1 是否闭合

| 原项 | 裁定 | 本轮已执行或源码证据 |
|---|---|---|
| P1-1 预算漏计 | **关闭** | 反馈沿实际 provider 登记；真实 client＋本地 HTTP 桩＋gate 的组合路径，第4次发送前拒绝，HTTP/gate/真实预约均3；正常、单支重试、正常反馈正控通过。 |
| P1-2 崩溃重放 | **未闭合，保留原编号** | 首提失败→唯一重试成功链已可零新增调用恢复，四个破坏负控拒绝且坏记录保全；但格式反馈自身重试成功后崩溃，公共恢复入口仍未消费已有成功响应。 |
| P1-3 worker 恢复 | **关闭** | 删除 resume 不接受的参数；真实协调者冻结→公共 crash 注入→实际 worker 同臂恢复完成，不再 TypeError。 |
| P1-4 臂保护 | **未闭合，保留原编号** | worker 缺副本/换臂已拒、报告同源核对已修；completed 的开关字段缺席或 null，仍绕过 skip/汇总接纳校验。 |

P1-1 的改动位于 [runflow.py:1195](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/runflow.py:1195)。本审另适配复跑上轮 HTTP 合成反例：原 gate 上限4和3两场景均只发3次、预约3次、保留原传输失败终态。429内部重试＋后续传输重试对照仍为 HTTP/gate 3、逻辑请求预约2；旧 `http_attempts` 诊断只记2的缺口如实保留，不宣称底层客户端已修。见 [完整结果](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/chain14_launch_codex_rereview_2026-10-16/execution/probe_http_gate_result.json)。

P1-2 已成立部分在 [real_model.py:744](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/real_model.py:744)：失败来源进入唯一后继核验，核 run/action/attempt/provider/purpose、确定性请求身份及既有 payload_hash，再校验完整响应 blob。首提成功重放与坏 blob、错身份、缺后继、双后继四负控均实际执行。负控后错 purpose 仍为 `tampered`，缺后继仍仅失败来源，双后继仍在，未换新键洗掉记录。

**余项已由公共 start→crash→resume 独立复现：**首提 BAD→反馈首发传输失败→反馈重试 GOOD，完整响应落盘后、解析前注入崩溃。解除注入后恢复：

| 合成场景 | 调用数恢复前→后 | 实际结果 |
|---|---:|---|
| 发车预算3，反馈重试成功 | 3→3 | `model_structure_failure`；3请求、2完整blob仍在，成功反馈未消费。 |
| 仅诊断预算4，同一形状 | 3→4 | 另发第2轮反馈才完成；只用于定位，不表示本批允许4。 |
| 单次反馈成功对照，预算3 | 2→3 | 也另发第2轮才完成；属既有入口缺口，不另立 P1。 |

原因在 [runflow.py:1187](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/runflow.py:1187) 再解析首提 BAD 后先登记反馈；[model_protocol.py:314](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/model_protocol.py:314) 按 `rounds_used+1` 直接分配下一轮，未先复用原反馈轮及其重试链。预算3先拒，进不到新 blob 消费 helper。见 [探针完整结果](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/chain14_launch_codex_rereview_2026-10-16/retry/probe_feedback_retry_resume_result_v2.json)。v1探针曾因摘要字段读取出现 harness KeyError；v2仅改观察字段、使用全新根重跑，三场景断言完整执行，不能把v1未完成断言报过。

P1-3 的公共 worker 修复在 [s5b_worker.py:221](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/s5b_worker.py:221)，对应新测1002实际通过。P1-4 已修部分为 worker 在启动run前校验可信预期值、协调者恒传预期值、报告前重读副本；丢副本反例新测1121确认拒绝且零run/零发送。

**P1-4 余项位于 [s5b_orchestrator.py:433](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/s5b_orchestrator.py:433)：**只对“有键且非null”的记录核对，还先 `bool()` 强转，不能作为严格类型校验。该规则由原循环skip和公开汇总共用。实际负控先让当前worker完成B，确认run身份为true、实际桩载荷带证据，再恢复A冻结；只改这份completed披露字段：

| 字段状态 | 原循环接纳 | 公开汇总 |
|---|---|---|
| 保留原 bool true | 拒绝错臂 | 拒绝 |
| 删除字段 | skip=1、completed=1、报告false | completed=1 |
| 设为 null | skip=1、completed=1、报告false | completed=1 |

后两条零新增载荷。这里证明的是**受控损坏记录可绕过接纳门**，不声称正常worker仍错发或自己丢键，不外推生产发生率。见 [完整矩阵与实际身份](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/chain14_launch_codex_rereview_2026-10-16/switch/stdout.json)。

## ② 修复是否越界

**未发现本修复改动越出四项原合同。**相对上轮快照，源码增量限runflow、real_model、s5b_worker、s5b_orchestrator，另有同一测试文件新增10测及文档。证据卡模块、提示词、CI、model_protocol、发车脚本与上轮相同；production、recorded_source、builder、compiler、scoring与HEAD相同。A臂字节兼容断言本轮通过；池/检索/排序/判分/run_inputs未新增算法改动，重试族和4470未触碰。P2已改为如实披露旧HTTP诊断缺口，llm_client行为零改动。

差分身份见 [protected_scope.json](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/chain14_launch_codex_rereview_2026-10-16/protected_scope.json)。最终回查19件被审文件无变化、HEAD不变，见 [final_postcheck.json](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/chain14_launch_codex_rereview_2026-10-16/final_postcheck.json)。

## ③ 新增10测是否覆盖四漏口

**覆盖声明的直接反例，但未覆盖上述两个公共入口余漏。**新测对应预算组合及正控、首提重放及四破坏负控、公共worker恢复、worker换臂/缺副本、协调者丢副本和已知bool错臂接纳。缺的是“反馈自身重试成功后恢复”及“completed缺键/null/非bool”的矩阵，不能以测试绿替代闭合。

本审执行账：

| 执行 | 实际结果与边界 |
|---|---|
| 初次原样25测 | 22过/3败：2项缺隔离资产身份，1项复制时漏带chain13 wrapper纯源码依赖。 |
| 补齐依赖，三文件原样 | 59过/4败；4败全为缺资产身份；**新增10测原样均过**。 |
| 受控资产身份替换，三文件 | 63过；仅外置sitecustomize将runflow资产身份替为scripted，含worker子进程，不改源码。 |
| 全量2185/0/16 | 仅实施方声明；本审未重跑，不列独立验证。 |

命令、输入、输出、退出码、适配脚本差异与合成SQLite/blob/case均留在 [execution证据目录](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/chain14_launch_codex_rereview_2026-10-16/execution)。隔离副本含vendor和必要metadata，外置TMPDIR，禁pyc/pytest缓存；98件原仓及隔离文件hash前后不变、缓存为0。本审未访问题面、金标、封存逐题run，未联网调用模型、未部署、未commit/push。分工证据以实际执行为准，未执行的额外草案不主张通过。

## ④ 交付书§八四条新偏差

| 偏差 | 裁定 | 理由 |
|---|---|---|
| 报告同源核对失败直接raise | 接受 | 副本丢失/不同值时明确拒绝，避免落错账报告；无需强制产出成功形状报告。 |
| 接纳只核披露键case | **需改，属原P1-4** | 早失败可缺键不等于completed可缺身份；现豁免可实际接纳错臂completed。 |
| 重算payload_hash核既有重试行 | 接受 | 用当前确定性输入验证原行，不换键、不改坏行；首提链正负控支持此判断。 |
| 手动无副本显式manual | 有限接受 | 正式协调者恒传expected；直连手动case披露mode。这里不是另加CLI开关，但在已定兼容范围可接受，不单独立P1。 |

## ⑤ 发车裁定及仅需回修项

1. **原P1-2：**先校验并复用同一错误来源已有反馈轮、原请求键及唯一合法重试终态，再消费完整响应；不得先分配新轮，不为恢复另发付费请求，不用重算新键掩盖坏记录。补预算3的公开反馈retry成功→crash→resume正控，要求3→3且完成，并补同入口坏blob/错身份负控；保持预算第4发送前拒绝。
2. **原P1-4：**expected明确时，completed必须有键、严格bool、同值；失败case若披露也须严格bool/同值，合法run前早失败可继续缺字段。补公共skip/summary的缺键、null、非bool、错臂与合法正控矩阵。

P1-1、P1-3保持关闭，下一轮只核以上余项与回修引入问题；不追加科学性能门，不要求真实模型调用。完整证据清单见 [FINAL_MANIFEST.sha256.json](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/chain14_launch_codex_rereview_2026-10-16/FINAL_MANIFEST.sha256.json)。

总体裁定：不放行 HPC 发车（仅回修 P1-2、P1-4 余项后同范围复核）。
