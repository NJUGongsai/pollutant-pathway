# L1 前置门扩罩分档设计回应（2026-10-15）

> 来源：GPT/Codex 本会话设计回应。输入文件为 [L1_TIERING_DESIGN_REQUEST_GPT_2026-10-15.md](/Volumes/CC/Enzyme_Agent/dependingv43/docs/L1_TIERING_DESIGN_REQUEST_GPT_2026-10-15.md)。已读取本仓 `AGENTS.md` 与本次任务书；真实可访问仓库，但事实依据仅取该请求内联的聚合数据，未取其他实验数据。本会话内子代理审阅不作独立背书，意见仅采信到与程序证据互证的程度。
> 题域：**298＝RHEA 通用酶学/已见题**；下文全部实测数字均属该域，与 dev 或其他题域双向不外推。设计≠实施≠预注册≠成绩；本文未执行探针、模型调用或评测，也不表示任何档已获批准。
> 文中新提出的预算、配额、相似度限制与继续条件均为**建议治理参数**，不是观察值、收益预测或安全证明。采纳仍须正式预注册确认及评审。

## 1. 档位与完整离线资格谓词

**结论：当前证据不能证明任何新档可装载。条件首选是纯 H₂O/H⁺ 簿记档；先守住现行 C，再逐个证明窄档存在有效机会。** 糖基件数最多不构成优先装载理由；机制、混合及身份未知面本设计不新增资格，只作诊断。

W/P/PP 的族比较对象是完整共底物供给义务，以及已有契约中可作为 v2 簿记项的伴生产物声明，不要求正常主产物也等于水/Pi。主底物、主产物仍保留原结构与角色验证，不能改主角色来洗袋；既有角色分界不可证则为 unknown。判族前仍须扫描完整记录，其他伴生有机物或机制物会否决纯簿记，不能因其不在豁免许可内就漏扫或先删除。

| 档位 | 完整参与物边界与资格方向 | 本次建议 |
|---|---|---|
| L0：现行 C | 保留原有语义 a 伴生供给资格和全部原规则 | 不收缩、不改写 |
| W：纯水/质子 | 上述完整伴生比较面仅含合法方向的 H₂O/H⁺ 簿记项 | 条件首选，独立开关 |
| P：产物 Pi | 含产物侧 Pi，其余伴生参与物仅属于 W，无 PPi | W 之后独立候选，不与 W 打包 |
| PP：产物 PPi | 含产物侧 PPi，其余伴生参与物仅属于 W，无 Pi | P 之后独立候选，不与 P 打包 |
| G：糖基有机第二底物 | 糖基参与物身份、角色明确且真实显式保留；具体完整子集另冻结，不获得有机物豁免 | 后置；当前编译器过门，或对应 L2 独立验收后才成为候选 |
| D：机制/混合/未知 | O₂、NH₃、C1（SAM/THF）、CoA 酰基、转氨（PLP/氨基酸），以及 NAD/ATP/FAD 等；CN、CH₂O 等危险形态；跨 P/PP、多有机族混合、身份或角色未知 | 本设计不新增资格，仅诊断并保留 unknown |

“本设计不装”是保守的资格选择；“永不豁免”是请求给定的许可红线。两者不能混为“整个系统禁止所有机制合法候选”。D 不借水、Pi 标签绕入新档，原有 C 资格也不因本分档收缩。P/PP 的产物方向限制只定义本保守档及既有 v2 许可，不能反推反应物侧 Pi/PPi 可以豁免。G 中有机参与物必须完整供给、显式执行，不能借簿记档洗成可豁免物。

G 还须在装载前冻结糖基身份、角色识别规则及允许的完整袋组合，不能只靠“糖基”粗标签收人。本方案不接纳跨 P/PP 或多有机族混合的 G 扩展；未能完整归类就维持 unknown，不进入先导队列。CN 亲核加成、NH₃ 胺化、CH₂O 羟甲基等即使得到合法备选面貌诊断，也不因此取得本设计的资格或豁免。诊断字段不能冒充有效供给、机制证明或目标正确性凭证。

对每个拟加档，候选新增资格取以下布尔条件的交集，全部在模型前离线计算：

```text
new_eligible = analog_channel
             & front_gate_rejected
             & !current_C_eligible
             & family_complete
             & declaration_precheck
             & unambiguous_existing_main_component
             & quota_mask
```

首轮只考虑已有同语义救援入口的 analog 通道。请求的 186 件是全通道族合格统计，不能直接当作 analog 新增资格；其他通道若没有现成同语义入口，不在本 L1 设计中另建通路。

`family_complete` 必须读取**完整、精确、多重集**：保留模板全部供给义务、计量和方向，检查完整声明中的主角色、全部伴生参与物及潜在凭证参与物。不得剪袋、删旁观物、按集合去重，或只找到一个水/Pi 标签就通过。主组分的确定与伴生物分类分别留证，不能为满足族谓词临时改主底物或主产物。`declaration_precheck` 要求完整声明面可解析、身份和方向一致，不能把“将来或许可生成凭证”当作已具资格。

沿用既有 Tanimoto、最大相似组分选择及对齐算法，并额外要求现有最大主组分唯一；冻结比较精度与并列判定规则，不可计算或并列时不新增资格，只约束新增面，不改排序。第一轮不另拍 0.8/0.9 门槛，记录现有指纹版本和最大相似度。若确需收紧，最多事前登记一个 `tau=1.0` 的嵌套 mask：只从原资格面收窄。它是治理选择，指纹同分不等于结构身份相同，更不证明正确或安全。

建议每个新增档、每题至多 **1 件**新增资格候选：完成该档静态过滤后、救援编译前，按冻结的既有遍历顺序固定首件身份；首件编译失败不递补。编译与池存活只用于整档判门，不允许先剔除失败者再取首件。现行 C 候选不占此新增配额。同时开放新增档至多 **2 个**，故每题新增资格至多 **2 件**。这不是池宽上限，不截断最终池，不改排序或去重语义；缺少稳定既有遍历或身份字段时先不装载。

建议所有先导档共用固定暴露预算：历史稳 strict 暴露 **0**、历史宽 strict 暴露 **≤2**、当前可比对照的 v1/v2 strict 并集暴露 **≤2**，定义见第 3 节。预算不从 C 的 35/19 或停点 -3 推导，也不保证可行；两轮内不自动放宽。唯一主组分门、配额、tau 与三项预算均没有最优性或安全性证据。全 298 题仍按原协议运行，不按历史 strict 逐题屏蔽或挑白名单，只能整档通过或弃档；全部档都过不了，可以不装。

**需要补的程序证据（字段名）**：`channel`、`candidate_id`、`candidate_identity_version`、`front_gate_reject_reason`、`current_C_eligible`、`supply_multiset_full`、`participant_role_direction`、`spectator_disclosures`、`declaration_payload`、`declaration_parse_status`、`family_labels`、`family_complete_status`、`fingerprint_version`、`max_tanimoto`、`similarity_comparison_precision`、`main_tie_policy`、`main_component_tie_count`、`existing_traversal_index`、`quota_selected`。字段名是证据需求，不声称已有这些接口。

## 2. 与 L2 的耦合：先证明能编译并真正改变池

**结论：资格、编译、池影响和 v2 凭证消费是四道不同的门。任何新档先在冻结的当前 C 编译器上做零模型重放；没有新增编译存活、或最终池没有有效变化，就不装。** 有机会进池也不等于能得 strict。

请求中 13 题观测面有 297 件池候选、289 件编译拒绝；全通道族合格的 186 件中，`no_alignment` 为 96、枚举截断为 56，是主死因。W 的 20 件也有 16 件 `no_alignment`、4 件其他原因，不能据此声称“水更容易编译”。chain13 的 17 件尝试存活 0，只说明该次观测面没有兑现，不证明全 298 题或未来版本全无机会。糖基 64 件最多，同样不证明它能优先带来收益。

离线门应同时要求：新增资格中编译成功数 **>0**，且经现有排序、去重、截断后的全链最终池序列化内容有新增变化 **>0**。仅原排序、执行、准入或判分实际消费的内容变动才算池机会，包括实际消费的参与物声明、记录方程及来源；候选数不变但此类声明改变，也应记录为可解释的 payload 变化。仅新增诊断标签、日志或 hash 元数据不算机会；若有效变化在去重/截断中全消失，则不装。编译成功但声明不能被原 v2 解析或消费，也不能作为合法凭证机会宣传。

若所有候选都被当前编译能力挡住，先另立 L2 工程里程碑：对齐覆盖、枚举可达性、糖基键合贡献与结构对应，分别对应实际阻塞，不把“放宽编译”塞进 L1。L2 验收须同时覆盖合法正控和硬拒绝、精确袋、零碳断言、声明完整性等不松动的负控；不支持的机制继续 `unsupported/unknown`。L2 验收后冻结版本 M1，再让对照和处理两臂都用 M1，仅切换一个 L1 开关。不得同轮改变 L1+L2，也不得把跨编译版本差归为 L1 收益。

**需要补的程序证据（字段名）**：`compiler_version_hash`、`replay_input_hash`、`compile_attempted`、`compile_status`、`compile_reject_reason`、`alignment_status`、`enumeration_truncation_reason`、`bond_contribution_status`、`structure_mapping_status`、`dedup_survival`、`final_pool_payload_hash_before/after`、`payload_change_kind`、`consumed_declaration_hash`、`v2_declaration_consumable`、`L2_acceptance_manifest_hash`、`positive_negative_control_results`。这些探针仅列为后续证据，本文没有执行。

## 3. 每档预注册骨架、暴露与判定规则

**结论：先统一计数单位、冻结完整 mask 和预算，再出数；离线全部过门也只获得进入预注册确认及评审的资格。** 既有整面 74/92 暴露与新档风险不能直接换算，当前还缺少族与 strict 面的交叉证据。

W/P/PP/G 各填一份同结构材料，不用一份“宽泛小分子档”覆盖全部族：

| 材料块 | 装载前应冻结的内容 |
|---|---|
| 身份与输入 | 注册 ID、题域、输入 manifest、候选宇宙及身份版本、语料和指纹版本、编译器 hash |
| 可比两臂 | 共享题目输入、冻结源候选宇宙、模型配置、prompt 模板及池构建/排序/去重配置；分别留最终池及候选 prompt 内容 hash、同配置对照来源和既有调用预算 |
| 唯一变化 | 单一档开关、完整族 mask、方向/声明/主组分门、每题配额及首件选择次序 |
| 风险与输出 | 历史及当前 strict 快照版本、三项暴露预算、v1/v2 计分版本、主次指标、分账标签 |
| 决策与学习 | 离线 no-go、族/全局停点、继续/退出条件、两轮分支、可选 tau 收紧及数据封存规则 |

离线阶段表必须逐层给出计数，不能用“186 件”替代“多少题”：

| 阶段 | 必报单位与意义 |
|---|---|
| 原始面 | 候选行数、按既有身份去重的唯一候选数、题数 |
| 新增资格 | `new_eligible` 件数、题级去重题数、被配额挡住件数 |
| 门与编译 | 新开门题数、尝试件数/题数、编译成功件数/题数及拒因 |
| 池机会 | 去重后存活、最终池 payload 变化的件数/题数、因新增而被替位的旧候选数 |
| 凭证 | 完整袋核验数、声明可解析数、原 v2 实际可消费数及各自题数 |

每层按 `channel × family × reject_reason` 分账，并在该层题级去重；排序算法未改，也可能因为新增候选替位旧候选，必须披露。5540 行、186 件、13 题不是可互换单位。资格题 245 与开门题 248 的关系尚未闭合，须对账，不能自行解释为统计误差。

**主暴露取编译前新增资格题集** `X_new`，而非编译幸存或获胜事件。设历史两批 strict 集交集为 `H_cap`（107 题），并集为 `H_cup`（137 题）；这些历史 strict 的计分版本在正文中未逐项明示，须严格继承原快照并核对版本，不能擅自称其必为 v1。设当前可比对照的 v1、v2 strict 集分别为 `H_now_v1/H_now_v2`，`H_now` 为二者并集。

```text
E_cap = |X_new ∩ H_cap|          建议预算：0
E_cup = |X_new ∩ H_cup|          建议预算：≤2
E_now = |X_new ∩ H_now|          建议预算：≤2
另报 |X_new ∩ H_now_v1| 与 |X_new ∩ H_now_v2|
```

同题新增候选即使现行 C 已开门，也算保守新增暴露，不能减掉所有 C 开门题。另报新开门、编译存活、最终池变化各阶段暴露，但不能代替主预算。原 74/92 的“新增暴露”算子在请求中未完整定义，须补齐后以原语义单列，不能声称等于本方案 `E_cap/E_cup`。若已保留上轮档，既算本轮增量，也算相对原始 C 的全部新增档资格题集并集，并集继续受同一总预算约束，不逐轮重置。

记账用两套视图。题级互斥主账按固定优先级“机制 > 有机第二底物 > PP > P > W”归类，纯簿记再由 W/P/PP 汇总；该优先级仅用于统计，不影响资格选择或排序。所有重叠安全切片仍另外报告，不能相加当全局。题级标签在跑前由新增资格面冻结，不依赖编译幸存者或事后赢家。全局每题只记一次；v1/v2 分别按同题对照到处理的 strict 状态配对：非 strict→strict 为 gain，strict→非 strict 为 loss，`net=gain-loss`。同臂 v1→v2 豁免回收另报，不能再加进处理减对照的净值；若某题 v1 丢 strict 而 v2 两臂均 strict，只是 v2 未丢，不是 v2 新增收益。partial/uncovered 互转不计 strict 得失但照报；新增资格暴露面外变化单报，不归为 L1 收益。

建议主指标为符合既有合法凭证消费目标的 **v2 strict 净得失**，v1 为强制安全账；出数前固定，不改判分。为保守执行族净得失 ≤-3 红线，本方案建议任一预登记族或重叠安全切片，在 **v1 或 v2 任一账 net≤-3 即停**，不以其他族、另一口径的正收益冲销；全局任一账达到同阈值也停。这是本设计选择的双账停法；如既定 S 口径另有权威规定，须在正式预注册时对齐，不能结果后改口。hit@1 是次指标，不能替代 strict 安全账。

| 决策时点 | 建议规则 |
|---|---|
| 离线 no-go | 零新增编译存活、零有效池变化、超任一预算、关键字段缺失或语义未闭合、声明无效；或需改变编译、排序、池宽、去重、通道路径，均不装本档 |
| 离线通过 | 全部条件满足后，进入既定预注册确认及评审；不自动发货 |
| 观测后继续候选 | 全局 v2 净得失 >0，且新增资格面内目标族 v2 净得失 >0；面外随机正变化不能作为通过依据，且没有任一双账停点。v1 如小负，须逐项由原 v2 合法声明消费解释，并明确报告 v1 损失，仍不声称显著 |
| 零或负收益 | 零净仅表示未证收益；负净不保留为获益档。族局部正不能掩盖全局负；是否确认或退出依事前规则及评审 |
| 控制或急停异常 | 缺同配置可比对照只能探索，不能作 L1 因果结论；触停点停止真实后续批次并回评审，不改参数躲停点 |

预注册须冻结题序和检查点，例如每完成一个有对照的题对累计检查；仅纳入已完成配对题，missing 不算 0。触停点后封存已产生事件，部分批不能称完整 298 成绩。分批急停不允许利用已知同批结果选参数，再把余下或重跑结果称作原预注册成绩；可选停机仅为安全措施，不是显著性证明。封存结果不回写；学习只服务下一次正式登记。

**需要补的程序证据（字段名）**：`registration_id`、`input_manifest_hash`、`candidate_universe_hash`、`corpus_hash`、`model_config_hash`、`prompt_hash`、`pool_builder_hash`、`rank_hash`、`dedup_hash`、`control_comparability_status`、`strict_snapshot_id/hash`、`strict_snapshot_scoring_version`、`legacy_exposure_operator_definition`、`qualification_gate_reconciliation`、`X_new_question_count`、`E_cap/E_cup/E_now`、`cumulative_X_union_count`、`stage_question_counts`、`displaced_old_candidate_count`、`frozen_accounting_labels`、`v1/v2_transition_counts`、`v1/v2_gain_loss_net`、`off_mask_transition_counts`、`stop_trigger`。

## 4. 两轮学习：先确认一个窄档，下一步由事前分支决定

**结论：两轮是有条件的学习框架，不是承诺跑两轮模型。第一轮按 W→P→PP→G 的固定顺序，选择首个离线全部过门的完整档，只切一个开关。** W 的优先性来自边界较易界定；20 件观测不证明它更能编译或更有收益。

两臂共享题目输入、冻结源候选宇宙、prompt 模板及其余全部配置，模型、编译及池语义须有同配置可比证据。L1 资格导致的最终池和候选 prompt 内容 hash 差异是预期处理效应，应分别留证，不要求两臂最终 payload/hash 相同。只用原已批准预算，每题每臂按既有协议单次调用，不为显著性增加采样、重试或模型复判；不能满足可比要求的旧控制不能默默复用，也不能擅自新增调用来补控制。没有合格控制则标探索或退出。

| 第一轮或装载前结果 | 第二轮预登记分支 |
|---|---|
| 首档无存活或无有效池变化 | 装载前弃档，按固定顺序检查下一已登记族；全部需 L2 时，两轮都可不装 |
| 首档 v2 正净，但样本小、波动未明 | 优先在原已准第二轮额度内确认原 mask，不立即扩罩 |
| 首档已满足事前明确的继续确认条件且未触停点 | 可将首档固定为双方共同基线，仅增加下一个预登记族开关；其余不动，仍算原始 C 之上的累计预算 |
| 首档零净或受益面小 | 不自动放宽；可用原 C 作为双方共同基线，另试一个已登记独立族，不能将旧档开关与新档开关同时变化算单变量 |
| P/PP/G 离线超预算 | 直接弃该档，不以 W 面小作为放宽预算或改配额的理由 |
| 首档小负、未触停点且风险有明确集中 | 最多采用事前登记的 `tau=1.0` 单参数嵌套收紧，其他族、通道、配额、编译均不变；先重做离线门，不承诺继续装载 |
| 任一族/切片或全局触停点 | 停止真实后续批次，回评审；不能自动转族规避停点 |
| 糖基因 L2 阻塞 | 先独立完成 L2 验收并冻结共同版本，不能第二轮同时打开 L2+G |

“满足继续确认条件”必须在看到结果前写清；现有数据不能给出可信样本充分性或显著性门槛。若尚不能事前明确，默认第二轮确认原 mask；无足够有效样本或可比控制则为 unknown，选择确认或退出，不扩。第二轮加族与 tau 收紧必须二选一，不能同时改首档参数。两轮均已用于学习时，只能为下一预注册供依据，不能包装成独立验证。

34/298 是两臂差一个供给开关时的状态翻转，包含干预效果与随机变化，**不是纯 A/A 噪声**；47/298 来自多变量批，更不能作为本档噪声分布。因此不设“收益超过 34 才显著”，也不容忍“损失在 34 内都算噪声”。现行 C 的 35 题、19 稳 strict 暴露及局部净零，也不能证明新档安全；请求给出的 chain12/13 总成绩不能分离单个 L1 档因果效应。

**需要补的程序证据（字段名）**：`round_id`、`frozen_family_order`、`common_baseline_mask_hash`、`single_changed_switch`、`authorized_call_budget_id`、`calls_per_question_per_arm`、`control_input_model_compiler_hashes`、`continuation_rule_frozen_at`、`confirmation_status`、`effective_exposed_question_count`、`tau_nested_mask_hash`、`round_branch_reason`、`stop_review_reference`、`sealed_result_manifest_hash`。不因提出字段而新增执行授权。

## 5. 诚实边界与待补证据

**结论：现有聚合数据支持“宽扩罩风险大、编译瓶颈重、应先离线证伪”，不足以批准任何窄档，更不能给出收益量或安全相似度阈值。** 下列 unknown 不用经验猜数，也不以本设计替代程序互证。

| 尚不能回答的问题 | 需要补的程序证据（字段名） |
|---|---|
| 各族究竟有多少 analog 新资格，跨通道/身份去重后还剩多少 | `channel_family_unique_candidate_counts`、`current_C_overlap_counts`、`new_eligible_question_counts` |
| 每族分别撞到多少历史及当前 strict，原 74/92 如何定义 | `family_strict_snapshot_intersections`、`strict_snapshot_scoring_version/hash`、`legacy_exposure_operator_definition` |
| 完整袋在当前编译器是否真可达，17 件零存活能否代表其他面 | `full_multiset_validation_status`、`family_compile_stage_counts`、`compiler_version_hash`、`rejection_coverage_scope` |
| 新候选经排序替位后是否有收益，池改动是否只换声明 | `final_pool_payload_diff_summary`、`displaced_candidate_counts`、`paired_v1/v2_transition_counts` |
| 机制合法但非目标面貌有多常见，混合族是否被错归簿记 | `diagnostic_mechanism_labels`、`legal_alternative_appearance_counts`、`mixed_unknown_family_counts` |
| 声明真能被现有 v2 消费，v1 损失是否确由合法凭证解释 | `declaration_parse_and_consume_status`、`event_record_equation_link_hash`、`v1_loss_v2_recovery_reason_counts` |
| 存在何种安全相似度、收益风险比或可靠噪声界 | `similarity_distribution_by_stage`、`exposure_gain_loss_counts`、`comparable_control_protocol_hash`、`intervention_randomness_identifiability`；现数据不能给结论 |
| 245/248 的差异、历史稳定性与跨域泛化 | `qualification_gate_stage_definition`、`stage_reconciliation_counts`、`replicate_protocol_hash`、`domain_label`；跨域需独立授权证据 |

逐题身份与状态如后续获准使用，只在原授权本地程序内 join 并输出聚合；不请求、导出题面、答案或逐题对错，不把金标写入仓库。无需新增读取凭证或对外发送；列补探针需求不构成给本会话执行探针的授权。本次新增设计回应及设计任务书，未改源码、测试、配置、判分、许可集或封存结果，未提交、推送或调用外部模型。

## 总体读法

先证明当前编译器有存活且真正改变最终池，再讨论窄档是否值得进入确认。
先纯簿记，后独立有机第二底物；机制面仅诊断，既有豁免红线不动。
当前证据允许 no-go，甚至两轮都不装；新预算和阈值均为待审治理提案。
所有资格、暴露、凭证与收益判断须由程序证据互证，并走正式预注册确认及评审。
