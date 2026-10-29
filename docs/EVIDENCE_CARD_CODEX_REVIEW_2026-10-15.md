# 候选证据卡有限范围审核（2026-10-15）

**结论：暂不通过；确认 2 项 P1，未发现 P0。** 接线与候选池边界成立，但正常可达输入会把未知系数输出为 `null`，并把不可计算的电荷输出为 `NaN`。两项均违反本轮已声明的“缺失或不可用事实统一字面 `unknown`”合同，应修复后在同一范围复核。本次只审核，不实施修复、不提交、不发车，也不据此判断 hit@1 收益。

| 级别 | 阻塞项 | 最小修复 |
|---|---|---|
| P1-1 | 合法参与物的未知系数被渲染成 `null` | 只在证据层把系数 `None` 转为 `UNKNOWN`，保留底层对象与 `coefficient_status`；补实际编译形状、默认副产物负控 |
| P1-2 | 合法底物的 Gasteiger 计算返回非有限值而不抛异常，最终载荷含裸 `NaN` | 每个电荷检查 `math.isfinite`；任一非有限则整个电荷描述符降为 `unknown`，保留其它事实；补同链负控及有限值正控 |

## 阻塞项证据与影响

**P1-1：正常编译产物的未知系数未按合同编码。** [candidate_evidence.py](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/candidate_evidence.py:145) 在系数缺失时直接返回 `None`。这不是坏输入：[recorded_source.py](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/recorded_source.py:2275) 因库记录没有配平系数，正常删除 spec 的 `coefficient`；[production.py](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/production.py:503) 随后合法装配未知系数，默认副产物也在该文件第 518–521 行使用 `None/unknown`。

本次合成验证实际调用 `compile_recorded_reaction` 编译 `CCO→CC=O`，得到合法且无 `coefficient` 的 spec；再走公开 `start_ppv1_run(scripted=True)` 与 `ScriptedRealModelAdapter`，原生导出成功，最终模型载荷中的两个参与物均为 `coefficient: null`、`coefficient_status: unknown`。另一组探针覆盖主系数已知而默认副产物未知的合法装配，同样出现 `null`。影响是证据编码违约，不能把底层 Participant 使用 None 本身判错，也不能用伪造系数 1 消除未知。修复应限定在证据渲染，并核对最终用户载荷。

**P1-2：不可用参考描述符被当成数值输出。** [candidate_evidence.py](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/candidate_evidence.py:317) 调用 `ComputeGasteigerCharges` 后直接取值、四舍五入、排序并计算极值与均值，第 337 行的异常降级无法捕捉“不抛异常但返回 NaN”。合成底物 `C[SeH]` 可合法解析与渲染，公开启动链零 monkeypatch，原生导出成功；最终用户载荷电荷的 min/max/mean 和逐原子值均为 NaN，`allow_nan=False` 检查拒绝。另一独立隔离探针以 `C[Se]C` 完成 render/roundtrip 后复现同一问题。

这精确证明不可用描述符没有降为 `unknown`，且模型收到的内层文本含非标准 JSON 数值。HTTP 外层把用户载荷当字符串发送，**不能据此声称当前 HTTP 发送必然失败**。同链 `CCO` 正控正常，helper 正控另含 Na/Mg/Cu/Si/B/Fe 等输入；这不是依赖缺失，也不需要全面拒绝含特殊元素的合法底物。最小修复是取电荷后逐一检查有限性，失败只降级整个电荷描述符；仅设置 `allow_nan=False` 使整题失败不满足既定降级合同。未测真实题域发生率或 hit 损失。

## 1. 接线正确性：通过

[runflow.py](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/runflow.py:836) 是本轮 decide 消费入口，第 879–881 行将已构造的在线底物档案传入 `_model_proposals`。首发第 1162–1164 行、一次有界格式反馈第 1213–1219 行都到同一个 `_call_real_fetch`；第 1289–1308 行按准备好的冻结候选原顺序装配新 dict，同时计算候选和底物证据。没有另加模型调用或提案重试。

[real_model.py](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/real_model.py:722) 将证据经 `pool_entries` 与显式 `substrate_evidence` 参数交给唯一 JSON builder；该文件第 235、242–245 行在白名单输出面保留两类证据及 schema，没有中途丢键。`ScriptedRealModelAdapter` 第 837 行继承同一 fetch，第 883 行只替换传输；传统无注入对象的脚本响应队列仍走 runflow 第 1167–1174 行，不构造实际请求载荷。

[llm_client.py](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/adapters/llm_client.py:382) 在 HTTP 重试循环前构造请求体，第 403–405 行复用该 body，不会在重试时另算另一份证据。real_model 第 635–691 行的有效 blob 重放保持零调用，且公开 resume 在恢复前核对新身份。P1-1/P1-2 是同入口中的内容问题，不重复计为接线漏洞。

## 2. 确定性与版本：有条件通过

在固定输入和依赖环境下，未发现新增随机或时序输出源；函数只读 spec/prepared，RDKit 分子局部计算不改冻结池。三次新进程以 `PYTHONHASHSEED=0/1/8675309` 执行同一合成 compile/prepared、四个合成底物档案和完整载荷，各退出 0、stderr 空，stdout 均 6851 字节，SHA256 均为 `7ef1f9a39cd8beff859a4c940454c462c8570161144b80030e76e095587453a9`。这只证明所选合成输入在同一 Python/RDKit 环境下跨进程一致，不证明跨版本恒等；NaN 的值域错误仍由 P1-2 处理。

[real_model.py](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/real_model.py:197) 以完整提示词内容计算新哈希，真实与 scripted 身份分别在第 466、875 行携带该值。新 schema 为 `candidate-evidence-1`，底物描述符另有版本常量。[run_identity.py](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/storage/run_identity.py:76) 第 76–100 行哈希全部包内 `.py`，包含新增未跟踪文件；第 103–112 行记录 RDKit 依赖版本，第 243–255 行比较代码、依赖和预测身份。因此不能因证据子对象未重复写 RDKit 版本，就认定版本没有承载。

[runflow.py](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/runflow.py:1859) 在第 1867 行完成身份核对后才进入恢复，旧代码、旧提示词或不同依赖不能静默恢复为本版。此处新批身份与拒旧批恢复的声明成立；未接线 helper 的用户 JSON 字节兼容，不等于全局系统提示词不变。

原子编号也核对了同源关系：[atom_tool.py](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/services/atom_tool.py:177) 与证据模块分别解析同一底物原串，底层转换没有重新排列原子，因而参考描述符使用既有执行图的编号空间。此结论限于已支持表示的合法路径。新函数禁用 RDKit 日志存在形式上的全局副作用，但原调用链已禁用相同日志，不把它另列为本轮行为回归；“纯函数”的工程表述宜理解为输出无随机、无时序、不修改输入，不扩大为对整个进程状态完全无影响。

## 3. 在线信息与 unknown 边界：不通过

字段读取路径限于 spec 的编辑/来源/编译诊断、prepared 的参与物与状态、输入底物的 RDKit 计算和既有 substrate_profile，未发现新增读取金标、判分结果、真实逐题对错或 EC 的生产路径。[candidate_evidence.py](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/candidate_evidence.py:221) 的组装和第 253 行的底物函数均可由这些在线输入解释。

但“来源可解释”不能替代“缺失和不可计算时如实 unknown”：P1-1/P1-2 已由合法公共链复现，因此本题整体不通过。修复仅需闭合这两项，不要求扩展机制证明，也不把来源标签、对齐成功或参考电荷当成反应正确性、生物可行性或确定反应位点的证明。此审核没有使用真实题目来推断字段收益。

## 4. 未接线透传与其它行为面：通过

生产代码的 payload builder 调用只有 [real_model.py](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/real_model.py:722) 一处。第 224–254 行对未携带新证据的调用方保留原候选四键的取值/字符串化、候选列表次序、execution_graph、format_feedback 和 JSON 排序规则；缺新三键时原载荷字节兼容成立。已有向后兼容测试也在本次受控测试通过集合中。

审查 diff 未见池构建、检索、去重、排序、候选截断或 scoring 算法改动；runflow 仅在 fetch 前组装新 dict，没有写回 spec、prepared 或冻结计划。`run_inputs` 仍不存证据卡。所谓“排序零变化”应准确解释为**排序算法及固定模型响应下的消费规则不变**；新信息让模型改变 rank 正是预期影响，不能据此承诺输出次序、得分或真实实验结果与旧版相同。

## 5. 负控与测试充分性：不通过

[新增测试](/Volumes/CC/Enzyme_Agent/dependingv43/tests/test_ppv1_s5b_candidate_evidence.py:311) 第 311–334 行只用 `spec={}/prepared=None` 和不可解析底物检查 unknown；正控第 64–93 行显式设置系数 1 且无默认副产物，因此绕开正常未知系数。第 350–367 行以固定输出扫描禁词和参考字段名，未覆盖“合法可渲染但 Gasteiger 返回非有限值”。这是两项已证实现问题的相应测试漏口，不另算漏洞数；固定样本禁词扫描也不能证明任意输入都无禁词，但本次没有据此发现第三项可达生产泄漏。

| 本会话执行 | 实际结果与限度 |
|---|---|
| 原样执行新增测试与词表 CI 两文件 | 30 过、2 环境失败；两项完整集成测试默认 `scripted=False`，隔离副本无真实 assets，资产身份核验先失败；不作产品缺陷 |
| 受控复跑同两文件 | 仅把 `runflow.retrieval_asset_identity` 替为公开 `scripted_asset_identity` 后 32 过；不称原样 32 全绿，不证明真实资产清单校验 |
| 两项 P1 的公共链探针 | 均用公开 `scripted=True`，零 monkeypatch，真实被审 fetch/builder，成功捕获最终用户载荷与原生导出 |
| 交付书全量测试与真实旧批探针 | 本会话未重跑；不把实施方“2154 全绿”或真实样本覆盖声明充作独立执行结果 |

修复后应保留乙醇等正控，增加实际 recorded 编译形状、默认副产物未知系数、Se 非有限电荷负控，核到最终用户载荷。有限值电荷继续保留、不可用电荷局部降级，不能靠全面拒绝通过。

复核收口时分别检查错误行为已经消失和合法能力仍保留：未知系数不得变为数值，已知系数应维持原值；不可用电荷不得残留 NaN/Infinity，分子式、元素组成与表示档案仍应输出已有事实。上述检查只验证本轮编码与降级合同，不追加科学性能门，也不要求运行真实模型才能关闭这两项问题。

## 6. 两项放弃：有条件通过；1 项非阻塞 P2 文档纠正

全通道 strict_exact/cn 层级确实保存在 [recorded_source.py](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/recorded_source.py:1240) 的检索包装，第 1260–1272 行的 tier 与 donor_smiles 未整体进入 compile spec；mapping_origin 不能替代该层级。本轮放弃统一复原可以接受。

但“通道事实完全不入 spec、decide 完全不可获得”说得过满：该文件第 1727–1735 行和第 1994–2002 行分别给 corpus 两条路径写入 `spec.corpus`；[s5b_builder.py](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/s5b_builder.py:1038) 第 1038–1046 行将原 spec 入池。块存在至少是 corpus 的正向标记，`donor_match_kind` 的 whole/component 也已有事实，但它并非 strict_exact/cn，亦未证明全通道和合并后来源能够完备恢复。

**P2 最小建议**：将设计与交付理由改为“部分通道事实可得，完整恢复尚未证明，v1 范围不纳入”。这不要求本轮新增细分字段；当前只标 recorded_inferred 并未把 corpus 错标成 EAWAG。不得为补字段直接透传整个 corpus 块，其中含本轮禁止展示的 EC。此文档纠正不计入 2 项 P1。

## 本次执行证据与边界

实际 HEAD 为 `461844eef6c3d0c464b12db0d89fc34e9971e825`，审核对象是未提交工作树的 5 个被审文件。Python 3.11.16、RDKit 2026.03.6、pytest 9.1.1。两组探针分别在新 tmp 隔离副本执行，源码包含 vendor 与必要 metadata，禁用 Python 字节码和 pytest 缓存；C 结束时核到 pyc=0、无 pytest 缓存，被审源 hash 与开始一致。A 首次旧 venv 失效导致 child 未启动，已单独留记录，不计探针成功。

证据根为 [本轮证据目录](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/evidence_card_codex_2026-10-15)。可复核入口如下：

- [A 字段与纯函数核验](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/evidence_card_codex_2026-10-15/purity/findings.md) 及同目录 `execution.json`、脚本全文和 stdout/stderr。
- [C 执行摘要](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/evidence_card_codex_2026-10-15/execution_probe/execution_summary.md)，原样及受控 pytest 输出、命令文件均在同目录。
- [公共链探针脚本](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/evidence_card_codex_2026-10-15/execution_probe/full_chain_probe.py) 与 [输出](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/evidence_card_codex_2026-10-15/execution_probe/full_chain_probe_stdout.jsonl)。
- [跨进程结果](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/evidence_card_codex_2026-10-15/execution_probe/cross_process_result.json)、`snapshot_metadata.json`、`source_postcheck.json` 与 `MANIFEST.sha256.json` 记录输入身份、命令、哈希及回查。

candidate_evidence 模块 SHA256 为 `47dfce355686fda26026a21f0c31b1f351ba4cb40c1d75e7287d77c2bc1a29f4`；其余文件完整哈希见 snapshot。审核未读金标、真实题面、真实逐题 run/calls/答案或逐题对错，未调用模型、网络、远端，未修改原源码、测试、配置或既有文档。全部新执行是合成输入，不外推真实题域频率或科学表现；交付材料中的科学数字只属于 298（RHEA 通用酶学/已见题），本报告不重新认证。内部子代理结论按源码与实际程序证据互证采信，不作独立性背书。

## 总体读法（≤5 行）

暂不通过：2 项 P1 是 unknown 合同内的真实漏口，未发现 P0。
接线、版本身份、未接线载荷兼容及候选池等算法边界成立。
先局部修复未知系数与非有限电荷，再按既定正负控复核；通道放弃理由另作 P2 文档纠正。
此结论不授权发车，也不证明证据卡能提高 298 题域的 hit@1。
