# ppv1-criteria-v2 P1+P2 修复正链终裁（2026-10-14）

**终判：不放行。原始 cn 腐蚀 P1 已修复，P2 已关闭；仍有 1 项同合同 P1：状态出现记录在官方首次消费时被静默漏验。** 本次不宣布 v2 生效。

本报告是对 [上一轮报告](/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_CRITERIA_V2_CODEX_REVIEW_2026-10-14.md:14) 的正式收尾补篇。遵守“既有 docs 不改”的纪律，保留历史报告原文；已修复事项保持关闭，下面的余项有独立源码与公共链证据，不把它冒充原 cn 反例复发。

## 评审对象、范围与来源

用户明确授权执行 [终裁请求](/Volumes/CC/Enzyme_Agent/dependingv43/docs/REVIEW_REQUEST_CRITERIA_V2_P1FIX_FINAL_2026-10-14.md)。本次由当前 Codex 桌面会话执行，内置并行子代理核查 P1、P2、回归，主代理审阅证据并作最终判定。上下文承接自旧报告与证据文件，不声称恢复了旧 CLI 会话，也不以备用通道结论替代本次终裁。

| 项目 | 本次实际对象/范围 |
|---|---|
| 工作仓、实际 HEAD、目标提交 | `/Volumes/CC/Enzyme_Agent/dependingv43`；`7e7855cb3ead11c7153f57b8e47a5b018f9e4ba3` |
| 修复父树 | `0ba764f121af8cbe001cad9442f2799cd108e21f` |
| 提交构成 | native_result.py、evaluation.py、两测试文件、交付书；源码/测试工作树与 HEAD 无差异；diff --check exit 0 |
| schema | chemstate=`ppv1-chemstate-8`，store=`ppv1-store-10`，native result=`ppv1-native-result-2`，evaluation=`ppv1-evaluation-5` |
| 固定验收 | 损坏权威 state/appearance 首次消费与重放的身份/事实/内容校验；合法正控；P2 两 tier 披露与逐边/批级闭合；缺省 v1 兼容 |
| 排除范围 | 机制库、生成侧改造、真实题域成绩、新阶段科学性能；原有 P3 不转成新门槛 |

范围登记与源码快照见 [TASK.md](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/criteria_v2_final_codex_2026-10-14/TASK.md)、[root_scope_check.json](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/criteria_v2_final_codex_2026-10-14/root_scope_check.json)。仓库原有未跟踪文件和预注册文档的既有修改均保留。

## 上一轮 P1/P2 的正式收尾

| 事项 | 本次结论 | 独立证据 |
|---|---|---|
| 原 P1：O₂ 的 states.payload.cn_identity 单点 `O=O→O` 被官方链接纳 | **关闭**。现在在 build_native_result 拒绝，底层 mismatch 保全；合法臂全部 8 步执行 | [原探针重跑](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/criteria_v2_final_codex_2026-10-14/p1/original_source_corruption_output.json)、[正负控重跑](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/criteria_v2_final_codex_2026-10-14/p1/delivery_source_corruption_output.json) |
| 原 P2：批级两 tier 单归属计数缺项 | **关闭**。两键恒在，失败/混合评审不丢失，批级=全部逐边和，判分原样透传 | [P2 核查与执行记录](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/criteria_v2_final_codex_2026-10-14/p2/notes.md) |
| 缺省 v1 兼容与本轮新增 4 测试 | **通过已核范围**。207 项受影响回归通过；双树字节对照通过；真正省略参数对照通过 | [回归记录](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/criteria_v2_final_codex_2026-10-14/regression/notes.md) |
| 同合同余项：损坏 appearance 被首次消费静默漏验 | **P1 未关闭**。官方完整接纳，同库公共重放明确拒绝 | [参与事件的出现记录探针](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/criteria_v2_final_codex_2026-10-14/p1/participant_appearance_output.json:146) |

### 原 P1 确实修复

[native_result.py:243](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/native_result.py:243) 在读取 states/appearances 后立即调用验证；对进入验证索引的 dict appearance，按 store 出现字段清单拼接语义与出现事实，再调用 [ChemicalState.from_dict](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/native_result.py:143)。该恢复入口调用既有 [validate_state_object](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/chemstate.py:648)，使用既有结构工厂、严格身份与保真事实来源；没有新立豁免化学判据。writer 同源是指共享这些事实推导来源，不能误写成 writer 也直接调用 from_dict。

本轮重跑原始 O₂ cn 负控得到 `NativeResultContractError.detail.kind=native_result_state_corrupt`，`state_error_kind=state_fact_rederivation_mismatch`，底层 `mismatches.cn_identity={provided: O, rederived: O=O}` 原样保全。负控在 build 拒绝后，persist/export/reader/evaluator **未执行**，不把这些未执行步骤报为通过。

合法 state 的交付正控 8 步全部执行；合法双出现正控也通过；第二 dict appearance 的 raw `O=O→O` 被 build 拒绝，底层 `raw_identity_mismatch` 与 from_dict 对照一致。零出现记录的新测试 fail-closed 通过。两件新增 P1 测试为 `2 passed`。具体命令、输入、输出与分级映射见 [P1 notes.md](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/criteria_v2_final_codex_2026-10-14/p1/notes.md)。

### P2 完整关闭

[evaluation.py:1558](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/evaluation.py:1558) 每边初始化固定两 tier；[:1604](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/evaluation.py:1604) 从完整 occurrences 累加；[:1672](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/evaluation.py:1672) 仅 v2 披露逐边计数；[:3232](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/evaluation.py:3232) 汇总全部样本/边，输出 [:3257](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/evaluation.py:3257)。修复没有改变原豁免清单、三谓词或单归属判据。

两件新增 P2 测试通过。补充六组控制覆盖已声明水、非豁免 H₂、混合、无 extras、重复同身份/侧/角色、另一个角色；双边×四候选事件每边计数 `v1_exempt=2 / not_exempt_maintains_partial=2`，批级 `4/4`。失败、混合和 structure-only 中已评审的实例均保留计数；混合事件仍是 partial，没有被洗成已豁免事件。

计数单位是“样本×参考边×候选事件×去重的 extra（state_ref/side/role）评审实例”，不是全批唯一物种数。混合评审中一个实例获 v1_exempt，并不代表整事件获豁免；tier 计数与仅针对成功整事件的 exempted_participant_occurrences 允许不同。

新合成原生 run 经官方 reader、evaluate、score_s5b_batch，确认 `criteria_v2` 块完整进入判分返回值与新建合成 metrics。多边计数控制使用合成 callback，只用于验证聚合接线，不冒称已证明 native 完整性。证据：[synthetic_counter_output.json](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/criteria_v2_final_codex_2026-10-14/p2/synthetic_counter_output.json)、[synthetic_multi_output.json](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/criteria_v2_final_codex_2026-10-14/p2/synthetic_multi_output.json)、[scoring_control_output.json](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/criteria_v2_final_codex_2026-10-14/p2/scoring_control_output.json)。

## 唯一阻塞余项 P1：状态出现记录的首次消费静默漏验

**位置：[native_result.py:119](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/native_result.py:119)，尤其 121–123 的 dict 过滤，以及后面的“apps 非空即可继续”。**

验证索引只收 dict appearance。非对象载荷被静默跳过；只要同一 state 还留有一个合法 dict appearance，就不触发 `native_result_state_unverifiable`。但原始 appearances 列表仍完整进入 native_result 和导出，所以被跳过的坏权威记录继续成为正式当前载荷。新增验证也未复用既有 appearance 内容哈希校验。

### 公共链实证，含合法正控和同库重放对照

1. 用公共 scripted start_run 创建全新合成 run，O₂ 是已存事件的 coproduct；用公共 put_state 添加两个合法、不同 source_refs 的 O₂ 出现。此时共有三条合法 appearance。
2. 合法正控的 read_endpoint → build → persist → export → 默认 reader → 默认 v2 evaluator 六个消费步骤全部成功；公共 submit_event 重放返回 `created=false`。
3. 负控只把第二新增出现的 `state_appearances.payload` 改成 `[]`。其 SQL state_id、旧 appearance_hash、created_at、state 语义、event/hypothesis、manifest/links、endpoint/artifact 均未手改。
4. 官方六个消费步骤仍全部成功，正式导出保留三条 appearance，其中一条 payload 为 `[]`。
5. 在**同一数据库**对已存事件调用公共 `store.submit_event` 重放，明确拒绝 `Ppv1LedgerCorrupt`，detail=`{table: state_appearances, kind: appearance_hash_corrupt, state_id: cs_a41af84d453ceaadda96, appearance_hash: 963a61ccf86fdcfe1b3783bf22af5d967e14e3eccad87aeda44e3ca1ef90b024}`。

| 主例证据 | 定位 |
|---|---|
| 合法三出现正控、公共重放成功 | [participant_appearance_output.json:5](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/criteria_v2_final_codex_2026-10-14/p1/participant_appearance_output.json:5)、[:138](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/criteria_v2_final_codex_2026-10-14/p1/participant_appearance_output.json:138) |
| 单点腐蚀、官方链六步实际接纳 | [同文件:146](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/criteria_v2_final_codex_2026-10-14/p1/participant_appearance_output.json:146) |
| 接纳结果与仍存在的坏载荷 | [同文件:195](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/criteria_v2_final_codex_2026-10-14/p1/participant_appearance_output.json:195)、[:215](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/criteria_v2_final_codex_2026-10-14/p1/participant_appearance_output.json:215) |
| 同库公共重放识别为损坏 | [同文件:264](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/criteria_v2_final_codex_2026-10-14/p1/participant_appearance_output.json:264) |
| 自包含探针、实际命令与 exit code | [participant_appearance_probe.py](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/criteria_v2_final_codex_2026-10-14/p1/participant_appearance_probe.py)、[appearance_probe.py](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/criteria_v2_final_codex_2026-10-14/p1/appearance_probe.py)、[participant_appearance.command.json](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/criteria_v2_final_codex_2026-10-14/p1/participant_appearance.command.json) |

旁证：只将 appearance.payload.state_id 改成 `cs-unrelated`，旧 hash 和 SQL 键不变，也得到官方链全接纳/公共重放 appearance_hash_corrupt。原因是 [store._split_state_payload:455](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/store.py:455) 明确把 state_id 放进 appearance，但新拼接只遍历不含 state_id 的字段清单，忽略了坏出现的身份绑定。此旁证归同一条 appearance 完整性余项，不拆成第二个 P1；没有证明 SQL states 行键与语义 payload 键的另一个漏洞。

### 为什么属于原合同，不是扩大科学验收

[AGENTS.md:67](/Volumes/CC/Enzyme_Agent/dependingv43/AGENTS.md:67) 明定“接受已损坏权威记录”可凭具体代码与公共链证据升级阻塞；[:77](/Volumes/CC/Enzyme_Agent/dependingv43/AGENTS.md:77) 明定 state/appearance 首用与 replay 共用版本、身份、事实及内容校验，并保全完整 distinct occurrence 集合；[:92](/Volumes/CC/Enzyme_Agent/dependingv43/AGENTS.md:92) 要求已证修复保持关闭，只有新同合同证据才重开。上一轮 P1 已引用这一合同，而非仅要求避免实际错误分数。

已有 [store.py:1339](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/store.py:1339) 对参与物 state 的**每条**出现做内容哈希校验；本次公共重放已实际触达并拒绝。首次消费继续接纳同一损坏记录，与原合同直接冲突。交付称“任一对不一致、不静默略过”和“上游闭合后自然闭合全链”的范围因此需要收窄：当前只证明进入索引的 dict appearance 的化学事实闭合，没有证明完整出现集合内容闭合。

没有实证 O₂ 错豁免为水、错误 strict、错误分数或 R6。负控评测仍为 `interface_verified_only`、事件仍 partial。这里的阻塞依据是**已发生的损坏权威记录重新封装与消费**，不是假设的未来科学错误，也不要求机制库或性能提升。

### 下一次复审的有限验收

- 在原生构建或官方首次读取/评分消费处，对本次被消费的完整 appearance 集合核验对象形状、state_id 绑定和既存 appearance_hash 内容绑定；与已有写入/重放的验证来源共用，不另立判据，不静默丢弃坏行或重算新 hash 洗掉损坏。
- 本次 `[]` 主反例和错绑旁证在首次消费被结构化拒绝，后续 persist/export/reader/evaluator 不执行；底层损坏信息可追溯。
- 合法多出现正控仍完整导出，公共重放幂等；既有原 cn 负控、零出现负控、合法结构/CN-only 边界、P2 闭合和缺省 v1 兼容继续保持。

只剩这一条余项，不新增其他阶段门。当前授权只允许报告与证据，本次未实施修复。

## 回归、字节不变与 P3 保留项

本轮在显式新建 `/tmp` 隔离源码副本执行，包含 vendor 与 metadata，禁字节码和 pytest cache。正式受影响回归为 **207 passed、0 skipped**，覆盖 S4a endpoint/S4b export、S4 三轮完整性回归、S5a schema/evaluator/isotope、criteria-v2、S5b pairing/L01 共 11 文件，包含全部新增四测试。一条原有 chemstate 文档转义 DeprecationWarning 不影响行为。

| 双树/缺省对照 | 本轮结果 |
|---|---|
| 同一新合成 run 的父/当前树缺省 v1 公共 evaluate/score | 输出字节全等，SHA256 均 `d8d9e2ed750e1899b6dc23ea3dff707f21732146e5d5ea49d119b404cac97aa8` |
| 17 条直连接口，含异常 type/message/detail | 字节全等，SHA256 均 `d9cd7cb9edc3f878713686afb8e50410bbb7d82fe60298bd32b6be17177afca7` |
| 真正省略 criteria_version vs explicit v1，match/evaluate/score | 两树内部全部断言完成、exit 0，结果 SHA256 均 `9540050db3797e79d847386c5e16bfcfa4a7aa5db82400f4b41ac9a77f43e862` |
| 新建合成 metrics.json/report.md/report_plain.md | 父/当前树三份文件 SHA256 分别全等，详见比较 JSON |

证据：[v1_comparison.json](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/criteria_v2_final_codex_2026-10-14/regression/v1_comparison.json)、[commands.json](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/criteria_v2_final_codex_2026-10-14/regression/commands.json)、[pytest_current.stdout](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/criteria_v2_final_codex_2026-10-14/regression/pytest_current.stdout)。交付方此前的 `2121 passed / 16 deselected` 是既有全量证据；本轮没有复跑全套，不将该数字算作本会话独立执行。

原 P3“default-vs-explicit 实为 explicit-vs-explicit”依然是源测试事实：[test_ppv1_criteria_v2_exemption.py:338](/Volumes/CC/Enzyme_Agent/dependingv43/tests/test_ppv1_criteria_v2_exemption.py:338) 经显式 helper 与 :343–346 再次显式调用。本轮新证据已真正省略参数验证行为，未改源测试；其永久化增强仍为非阻塞 P3。其他已登记 P3/known gaps 不重开，不把回归通过当成出现记录余项已闭合。

## 证据纪律与采信限度

正式采信执行在新 `/tmp` 目录；有若干初次脚本搭建问题（系统默认临时路径、O₂ 夹具 raw 选择、补充 AST 名称依赖），原始失败/重试日志完整保全，各分支 notes 注明后经新隔离执行或仅重跑失败补充解决。这些失败不计作通过；空 stdout 字节相同不计断言通过；正式 v1 比较均以两边 exit 0 为前提。观察性负控脚本 exit 0 表示成功复现“错误接纳”，**不表示产品通过了该负控验收**。

未访问真实 questions.jsonl、金标 reference_graphs、既有逐题 metrics、gitignored reports 或封存 run；所有 graph、run、batch、metrics 为本轮新造合成控制。未调用 mimo/opencode 或其他外部模型/网络，不外推 dev/298 科学性能。未改 src/tests/既有 docs/AGENTS.md，未 commit/push。评审前后工作树差异核对见本证据目录 `final_integrity_check.json`；全部终裁证据与报告 SHA256 见 `SHA256SUMS.json`。

**正式收口：7e7855c 的原 cn 腐蚀修复和 P2 交付接受；当前整体放行条件因唯一的 appearance 首次消费 P1 余项尚未满足，终判仍为不放行。**
