# mimo 化学评审请求 r21:pollutant_pathway_v1 S5a 评测接口化学判断面

日期 2026-10-08。本请求**自包含、只含规则级表述与合成例**(如
CCO/CC=O/[H][H]/F[C@H](Cl)Br),不含金标/题面/封存逐题 run 数据,
不含任何真实 dev/298 指标数值;由用户送 mimo,回复原文落盘。触发
点:AGENTS.md 化学评审三类之 1(需评判化学结构口径——S5 评测器的
参考图匹配与分轴判据属"金标口径/判据"侧接口,proposed 规则冻结
前)。**评审独立性不做背书;结论采信到与程序证据互证的程度为止;
本请求只问规则级判据,不请求任何执行声明。**

---

## 0. 背景(一段)

S5a 批次(任务书 `POLLUTANT_PATHWAY_S5_SPEC_TASK_2026-10-08.md`
§15)交付了**评测器接口**(`ppv1-evaluation-1`):判分零 LLM、
确定性、合成规则级验证;阈值/样本量/分母/金标口径全部 TBD(用户/
teacher 裁定,§10.1)。评测器内置的**proposed 匹配/分桶规则**是
未来真实评测(S5b)判分的候选口径 —— 请评审以下六个判断面是否
存在"把口径写成会误报/漏报的化学错误"的结构性缺陷。每面都给出
实现当前行为与合成例;例中产物来自公共链真实生成(合成 run 走
start_run 真实执行流),无金标。

## 1. 判断面一:参考图匹配的严格身份 vs CN(旁证)

**proposed 规则**:预测侧节点与参考图节点匹配时,**严格结构身份**
(与生产同源的 strict identity,含立体/同位素/电荷表示层)相等才计
`strict_structure` 命中;**CN 相同而严格身份不同/未知 ⇒ 只计
`cn_only` 旁证桶,不计严格命中**;参考图声明 `identity_scope=
cn_only` 的节点同样只进旁证桶。CN 不参与确认类计数。

**合成例**:
- 例 1(严格命中):预测 state `CC=O`(smiles_isomeric=CC=O)对
  参考节点 structure_smiles=CC=O ⇒ strict_structure。
- 例 2(旁证不升格):预测 state `F[C@@H](Cl)Br` 对参考节点
  `F[C@H](Cl)Br` —— CN(stereo_blind)相同、严格身份不同 ⇒
  `cn_only`,不计严格命中(对映体不互认)。

**问 1**:该分轴是否满足"CN 仅旁证、不冒充严格结构确证"?严格
身份键含同位素/立体/电荷 —— 有没有应当**视为等价**却被该规则
判为不命中的表示层情形(如互变体质子的显式/隐式氢表示、芳香
Kekulé 双写)——如果有,是否应该以"规范化严格身份"而不是"字面
严格身份"为匹配键?(实现用与生产同源的 canonical 身份键,已非
字面;请指认残留风险。)

## 2. 判断面二:step_scope 分轴

**proposed 规则**:参考边携带 `step_scope`
(net_reaction/elementary_step/multistep_summary/unknown);预测事件
按其假设的 step_scope 对比。**scope 不一致 ⇒ 结构匹配但仍单列
`matched_structure_only`**(不并入严格边召回);multistep_summary
保留为汇总边,不冒充净反应;unknown 不参与 net 计数。

**合成例**:参考边 A→B(net_reaction);预测事件 A→B 结构严格
匹配但假设 step_scope=multistep_summary ⇒ matched_structure_only
(step_scope_consistent=false)。

**问 2**:该分轴是否足以防止"汇总边冒充净反应边"进入严格召回?
`elementary_step` 与 `net_reaction` 之间是否需要第三档(同净反应
但多步已知)——还是保持不混即可?

## 3. 判断面三:条件 conflict/unknown/compatible 判据

**proposed 规则**(条件分类器,essential/preference × 事实状态):

| 参考要求(required=essential) | 预测事实 | 判定 |
|---|---|---|
| key 缺事实 / 事实 status=unknown / 要求 status=unknown | — | `condition_unknown`(不计冲突) |
| 事实 known_absent | — | `essential_conflict` |
| 事实 known_present 且值一致(精确串或 lo-hi 区间包含) | — | `compatible` |
| 事实 known_present 且值不一致 | — | `essential_conflict` |
| required=preference 且不满足 | — | `preference_unsatisfied`(独立桶,非冲突) |
| 要求挂接的 subject scenario ≠ 事实 scenario | — | `scenario_transition_changed`(独立桶) |

历史来源条件(provenance source_conditions)**原样保留**披露,
不改写为当前场景事实。

**合成例**:事实 {oxygen_regime: aerobic, known_present};要求
① oxygen_regime essential aerobic ⇒ compatible;② redox_regime
essential anaerobic(无事实)⇒ condition_unknown;③ oxygen_regime
essential anaerobic(值冲突)⇒ essential_conflict;④ preference
不满足 ⇒ preference_unsatisfied。

**问 3**:"unknown 不计冲突、满足不升级为全路径相容"的边界是否
正确?值比较用"精确串相等或区间包含"是否有会产生**假冲突**的
情形(单位不同/离散枚举拼写不同/多值条件)?多值条件(multiple
values)建议进 unknown 还是逐值判定?

## 4. 判断面四:矿化证据最低口径(endpoint 声明检查)

**proposed 规则**(消费 S4 endpoint 四分账,评测器只做**误声明
检查**,不自己判矿化):

- 预测 assessment=supported_mineralization 而证据缺
  root_carbon_fate_check_scope 或无来源层直报证据 ⇒ 误声明
  `mineralization_claim_without_root_carbon_account`(仅提出 CO₂
  产物/仅 bookkeeping 皆不构成);
- 停止原因(budget/depth/no_candidate/awaiting/exhausted/user)
  在场而 assessment 非 unknown 且无证据 ⇒ `stop_reason_mislabeled_
  as_endpoint`;
- 继承未解决必要依赖(unresolved)而 assessment ∈ supported_* ⇒
  `unresolved_dependency_promoted`(recorded 不洗白);
- bookkeeping.co2_aggregated=true ⇒ `co2_merged_across_alternative_
  routes`(不同备选路线 CO₂ 不合并);
- metabolic_handoff ≠ 矿化。

**合成例**(真实链路):无证据 run:产物 CC=O/[H][H],stop=
budget_limit ⇒ assessment=unknown,零误声明(负控);带来源层直报
矿化证据(根碳 14C 平衡 92% + 观察窗口 + 检出范围)⇒
supported_mineralization 合法(正控)。分类器负控:手工构造
"assessment=supported_mineralization 而证据空" ⇒ 误声明命中。

**问 4**:最低口径三件(根碳账核查范围 + 来源层直报 + 观察范围)
是否充分防"仅 CO₂ 就叫矿化"?还有哪些**应当判为误声明**而该
清单未覆盖的终点声明类型(如"把代谢交接终点当永久去除")?
评测器不做正面矿化判定(归 S4 四分账 + 用户/teacher 金标口径)——
该分工是否有漏洞?

## 5. 判断面五:共同产物/备选反应不合并

**proposed 规则**:边匹配按**参与物精确覆盖**:预测事件参与物
集合(反应物侧/产物侧)与参考边声明的节点集合**两侧相等**才计
严格匹配;事件多出共同产物(超集)或缺声明共同产物(部分)⇒
单独披露 `coverage_mismatch_events`,不计严格匹配。同父备选
(A→B 与 A→C)各自匹配独立事件,**不折叠**;共同产物(事件内
role=coproduct)完整保留在匹配条目,不受报告 K/展开宽度影响。

**合成例**:参考边 e1=A→B(+共同产物 H2,declared_complete)、
e2=A→C(无共同产物);预测事件 B(A→B+[H][H])精确匹配 e1;
事件 C(A→C)精确匹配 e2;事件 B 对 e2 为超集、事件 C 对 e1 为
部分(缺 H2)⇒ 两者都只进覆盖失配披露。

**问 5**:"精确覆盖才计严格匹配"对 declared_complete 的参考边是
否过严/过宽?若参考边 participant_list_status=partial/unknown,
实现同样只给精确匹配严格地位(其余披露)——是否应对不完整参考
放行超集匹配为"部分覆盖匹配"(单列桶)而不是仅披露?

## 6. 判断面六:distinct occurrence 不按 CN 合并

**proposed 规则**:参考图同一分子不同来路/场景/研究来源保留
**distinct occurrence**(node_id + occurrence_id);匹配输出逐
occurrence 一条,不按 CN 或结构首现合并;预测侧 occurrence 计数
取该 state 的出现行数/事件参与数如实披露。

**合成例**:参考两个 CC=O 节点(occ-cco-a 来自研究 A、occ-cco-b
来自研究 B);预测侧同一 state(cs_...CC=O)被两个事件(备选 B
与备选 C)产出 ⇒ 两个 occurrence 条目各自保留,均严格命中同一
state,条目不合并。

**问 6**:occurrence 级计数是否足以支撑"同一分子不同来路不合并"
的科学口径?两个 occurrence 命中**同一**预测 state 时,是否存在
应当视为"预测侧只发生了一次"而不能对两个参考 occurrence 各记
一次命中的情形(如同一事件的双重来源标注)?

## 7. 请求汇总

请对上述六个判断面逐面回答:(a) 分轴/判据是否有结构性化学错误
(会系统性误报或漏报);(b) 各合成例的预期判定是否正确;(c) 有无
必须补的最低口径。不要执行任何代码;程序行为数字以仓内证据为准
(PPV1 全量 1045 绿/G01 1647 绿,见交付书)。本请求不含也不请求
任何阈值/样本量/金标内容 —— 那些属用户/teacher 裁定(§10.1)。
