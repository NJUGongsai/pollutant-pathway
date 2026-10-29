> **通道与 provenance（主会话 ZCode 记录，非 mimo 回应正文）**
>
> - 2026-10-09 凌晨（S5a 批次轮内第③步自动送审，AGENTS.md「评审-回修自动循环」）：请求 `docs/mimo_ppv1_chem_review_request_r21.md`（自包含、无金标、只规则级+合成例）经 **opencode 免费模型 `opencode/mimo-v2.6-flash-free`** 只读评审；opencode 会话 `ses_ee3b96bd1ffecKiYl1B3TsB1dw`（标题 "mimo ppv1 v21 chem review"）。与手机 mimo 应用是否同一实例未经证实，采信按本通道口径区分。
> - 运行早期出现一次非致命断流（raw 输出第 22 行 "stream ended without finish_reason"），opencode 自行恢复续跑；**回应完整**（判断面一~六 + §7 汇总 + 结束语 + 全文声明均在）；主会话已核对无中段缺失。
> - 评审为**只读**：执行类断言（1045 绿、各测试行号判定）一律"待执行验证"；读码引用带行号。其中 PPV1 1045 passed 已由主会话本机独立复跑证实（2026-10-09 凌晨）；G01 安全隔离 1647/8/17 为交付方隔离证据，留 Codex 复核。
> - **本轮 P1 报出两项（待 Codex 正链互证）**：①面三——评测侧条件三分类（evaluation.py:774-816）与冻结判据四（known_absent 轴归属/单位三态/多事实保守 unknown/necessity 无源不进门禁）在五类输入上判决不同，同名 `essential_conflict` 两义；②面一——proposed 规则文字称 `identity_scope=cn_only` 参考节点只进旁证桶，实现无 scope 分支（evaluation.py:585-627）可计严格命中并传导至边严格匹配（:648-652），触碰冻结稿"旁证不叠加升格"原则。另有四个面有条件同意 + proposed 文本↔实现不一致清单（面四三件半实现/handoff 死键/预注册:101 文字/unknown==unknown 进严格）与 R16 `confirmed_claim_events` 名实不符（范围外）。**按既定循环，mimo 结论采信到与程序证据互证为止，P1 处置以 Codex 正链裁定为准。**
> - 请求原文：`docs/mimo_ppv1_chem_review_request_r21.md`。运行证据与原始输出：`docs/review_evidence/ppv1_s5a_mimo_2026-10-08/`。
> - 以下为 mimo 回应原文（仅清理终端控制字符，未做任何内容改动；含其自述落盘建议与结束语）。

---
以下为评审回应全文（可直接落盘为 `docs/mimo_ppv1_chem_review_response_r21.md` 的候选正文；本轮我不修改任何文件，仅输出文本）。

---

# mimo 化学评审回应 r21：pollutant_pathway_v1 S5a 评测接口六个判断面

**通道与边界（头部 provenance）**：只读评审；仅用读取类工具浏览仓库源码/文档核对请求表述，**未执行任何代码、未运行任何测试**——一切执行类数字（PPV1 1045 绿 / G01 1647 绿）按"**待执行验证**"处理，本回应不含任何自行执行得到的结果或数字。引用行号均为我本轮**实际读到**的行号与名称；未读到的一律标"未确认"。未访问任何金标/题面/封存 run 目录（未读 `reports/phase_*` 等 gitignored 路径）。评审独立性不做背书；结论采信到与程序证据互证的程度为止。

**口径状态**：六个判断面的匹配/分轴规则均为 **proposed（候选，未冻结）**；判据一~五与 0d/0e 已冻结 `ppv1-criteria-v1`（`docs/POLLUTANT_PATHWAY_CRITERIA_FROZEN_V1_2026-10-08.md`）。按请求口径，我发现 **2 项 P1 级（实现与冻结判据/冻结原则冲突）**，集中在判断面三与判断面一，详见各面与 §7 汇总；其余为 proposed 规则自身的结构性问题与"规则文字↔实现"不一致项（须在 proposed 冻结前处置，但不动冻结正文）。

---

## 判断面一：参考图匹配的严格身份 vs CN（旁证）（问 1）

**1) 结论：有条件同意。**
- 分轴方向正确：严格身份相等才计 `strict_structure`，CN 同而严格不同只进 `cn_only`，与冻结判据 §0"旁证不叠加升格"（冻结稿 :42）和判据五"legacy CN 仅旁证"（冻结稿 :399-401）一致。匹配键确非字面：参考侧经 `strict_identity_of`（`chemstate.py:913-929`）取与生产同源的 canonical CX 事实键（`_identity_key`，`chemstate.py:180-226`），Kekulé/芳香差异由 RDKit 归一（该 docstring `chemstate.py:204` 明示）；对映体例经读码与测试一致（`tests/test_ppv1_s5a_evaluator.py:493-533`，`cn_only` 判定在 :521）。
- **但有一处 P1 级条件**：提议规则写"参考图声明 `identity_scope=cn_only` 的节点同样只进旁证桶"，**实现没有这个分支**——`match_reference_nodes`（`evaluation.py:585-627`）把 `structure_identity_scope` 只抄进 `reference_identity_scope` 做披露（:590-591），匹配逻辑无条件对 `structure_smiles` 算严格键并可在字面相等时给 `strict_structure`（:597-618）；夹具 `n-cn-only`（`test_ppv1_s5a_schema.py:133-143`，`structure_smiles="CC=O"`、scope=`cn_only`）若过匹配，会拿严格命中，**且经 `strict_by_node` 喂给边严格匹配（`evaluation.py:648-652`）**。声明为旁证的参考节点冒充严格确证，触碰冻结稿 §0 原则 ⇒ 按请求口径记 **P1**。`partial`/`unknown` scope 同理未封顶（枚举见 `reference_graph.py:54-55`）。
- 关于"应视为等价却判不命中"的残留情形：
  - 显式/隐式氢（如 `CCO` vs 带显式 `[H]` 写法）：RDKit 解析层通常归一，**仓内未读到明示条款，标未确认（待执行验证）**；`[H][H]` 整分子情形经夹具严格命中（`test_ppv1_s5a_evaluator.py:251-256`）。
  - 质子化态（酸/碱式、两性离子 vs 中性）：严格键不同、CN 经电荷归一相同（`domain/identity.py:27-37,46-55`）⇒ 落 `cn_only`。方向正确（质子化是真实化学差异，不该给严格命中），但**不披露差异原因**（见误导风险 R4）。
  - 互变体（酮-烯醇）：严格与 CN 两轴都不等 ⇒ **完全 `unmatched`**，与"毫不相干的分子"同桶。
  - 参考侧立体未指定、预测侧给出构型 ⇒ 严格键不同 ⇒ `cn_only`（模型给了更具体信息反而不计严格）。

**2) 可直接落进规则文字的修改建议：**
- S1-1（P1 必修）："参考节点 `structure_identity_scope ∈ {cn_only, partial, unknown}` 时，严格比较结果**封顶为旁证档**：CN 相等 ⇒ `cn_only`，不产生 `strict_structure`，也不进入边严格匹配的 `strict_by_node`；scope=`strict_structure` 才允许严格档。"（同步修 `match_reference_nodes` 或改规则文字，二者必须一致，不能带着不一致冻结。）
- S1-2："匹配时对预测侧 `smiles_isomeric` **重算** `strict_identity_of` 并与导出字段比对，不一致 ⇒ 结构化披露 `prediction_identity_rederive_mismatch`（该样本降级/披露），匹配键以重算值为准。"（现状：预测侧键直接取导出行 `state["smiles_isomeric"]`/`state["cn_identity"]`，`evaluation.py:611-614`，依赖生产恒等式 `smiles_isomeric`=身份键同串与 `chemstate.py:870-873,900-910` 守卫，评测器自身不复核。）
- S1-3："评测输入核对导出的 CN/身份版本（当前 `cn-v1`，`domain/identity.py:18`）；版本缺失或不符 ⇒ 披露并停用 CN 旁证档（不静默比对）。"
- S1-4："`cn_only` 档按差异轴再分子桶披露（stereo / isotope / charge-protonation / other，可由严格键与 CN 键分层归一差分推出）。"
- S1-5（作者义务）："参考结构含未指定立体中心而作者无法定构型 ⇒ 必须声明 `identity_scope=partial/cn_only`；评测器对 scope=`strict_structure` 但立体未指定 vs 预测已指定的情形加 `reference_stereo_unspecified` 披露。"
- S1-6（可选）："互变体类差异（同骨架、互变氢位置不同）单列 `tautomer_equivalent_unmatched` 披露桶，不进确认。"

**3) "程序上诚实但化学上误导"风险点：**
- **R1（P1）**：`cn_only`/`partial` scope 节点可输出 `strict_structure`——程序逐字段如实，但读数者会把"参考自己声明只够旁证"的节点当成严格确证。
- **R2**：预测侧键不重算——表示层/版本问题会被读成化学差异（本该 cn_only 的对读成 unmatched，漏旁证）。
- **R3**：`cn_only` 桶把"对映体反转（模型可能真错）"与"酸碱写法不同（纯表示层）"混在一桶——同样叫 `cn_only`，化学含义天差地别。
- **R4**：互变体与无关分子同落 `unmatched`，漏报的"错法"不可区分。
- **R5**：`predicted_occurrence_count` 两档基数不同——严格档用 `state_appearances` 行数（`evaluation.py:619-620`），`cn_only` 档用事件参与数（:625-626）；跨档比较该数会误读。建议在字段说明里写死"两档基数不同、不可跨档比较"。

---

## 判断面二：step_scope 分轴（问 2）

**1) 结论：有条件同意——足以防"汇总边冒充净反应边"进严格档，但有一处规则自破口（unknown==unknown）。**
- 一致时进 `matched_strict`、不一致进 `matched_structure_only`（`evaluation.py:693-726`，等值判断 :700；状态选择 :727-732）：`multistep_summary` 参考边遇 `net_reaction` 事件 ⇒ `matched_structure_only` ✓，与合成例及测试一致（`test_ppv1_s5a_evaluator.py:536-555`，断言 `matched_strict==0`）。
- **破口**：双方都缺/都未知时 `event_scope == ref_scope == "unknown"` ⇒ `step_scope_consistent=true` ⇒ 覆盖精确即可 `matched_strict`（:693-695 缺字段默认 `"unknown"`；:720-724）。这违反本批自己的 proposed 文字"unknown 不冒充净反应"（`preregistration.py:104-107`），也与生产侧对 unknown scope 的保守处理（`audit.py:1290-1294` 记 `CHECK_UNKNOWN`，理由"汇总边不冒充净反应"）不一致。`STEP_SCOPES` 含 `unknown`（`reference_graph.py:59-60`），参考边声明 unknown 合法 ⇒ 路径可达。
- `elementary_step` 与 `net_reaction` 之间是否需要第三档：**保持不混即可，不建议现在加第三档进严格召回**；净等价的"多步合成净反应"聚合属指标口径（§10.1 `identity_matching_rules` 本就列了 step scope 匹配规则，`preregistration.py:43-44`），将来要做应作**独立披露档**、单独评审，不并入 strict。

**2) 修改建议：**
- S2-1（必修）："严格档要求 step_scope **已知且相等**；`unknown==unknown` ⇒ 单列 `matched_structure_only_scope_unknown`（或等名桶），不进严格召回。"
- S2-2："事件侧 `step_scope=net_reaction` 进严格档还须 `step_scope_evidence_refs` 非空（字段在 `hypothesis.py:378,382`），否则披露 `scope_claim_unevidenced`——因生产侧对未声明的池条目**默认 `net_reaction`**（`production.py:234`），'默认'不等于'已证'。"
- S2-3："参考 `multistep_summary` 与预测 `net_reaction` 结构相等时，可增披露 `net_equivalent_suspected`（仅披露、不计严格），供后续口径裁定。"
- S2-4："scope 不一致但结构匹配的事件，**不得**落进 `outside_reference_*` 桶——现 `matched_event_ids` 只收集 `matched_events`（精确档）（`evaluation.py:1474-1477`），structure_only/coverage 失配事件会被 `outside_reference_edges_from_export`（:1099-1106）当成'参考外边'计数。"

**3) 误导风险：**
- **R6**：unknown==unknown 计入 `matched_strict`——若日后把 strict 桶读成"净反应严格召回"，unknown 双方的边就冒充了净反应确认（正是规则自己禁止的事）。
- **R7**：默认 `net_reaction` + 评测器不看 `step_scope_evidence_refs` ⇒ "scope 声明一致"可能只是两个未举证的同词。
- **R8**：`outside_reference_*` 吸入 scope 不一致的结构匹配事件——"参考外未验证"读起来像模型凭空造边，实际是参考结构内的边、只是 scope 假设不同（化学含义完全不同）。

---

## 判断面三：条件 conflict/unknown/compatible 判据（问 3）

**1) 结论：不同意当前实现的 known_absent/单位/多事实处理——按请求口径记 P1（与冻结判据四冲突）。**
冻结判据四（冻结稿 :370-379）与生产实现（`path_context.py`）的口径是：实体/同值字符串缺席 ⇒ conflict；**异值字符串 known_absent ⇒ unknown**（:832-837）；**数值/区间 known_absent ⇒ unknown**（:819-825）；**单位三态**：缺单位/非规范单位 ⇒ unknown（:790-803）；**多事实值不一致 ⇒ 保守 unknown**（:774-777）；essential 无来源 ⇒ 不进门禁 unknown（:761-762）；optimum 永不 conflict（:846-849）。
评测器 `classify_condition_requirement`（`evaluation.py:774-816`）则：
- `known_absent` **一律** essential_conflict（:808-810，不比值、不分类型）——数值缺席、异值缺席被判成冻结判据的 unknown；
- **完全不读 `unit`**（要求侧有 `unit` 字段 `reference_graph.py:169`，事实侧有 `unit` `path_context.py:343`）——`30`(K) 对 `20-30`(C) 会判 **compatible**（假相容，比假冲突更危险）；
- 多事实取 `matching[0]`（:800）——同一键事实冲突时首条说了算，冻结侧是保守 unknown；
- essential 无 `source_refs` 不查——冻结侧 `necessity_unsourced_not_gating` ⇒ unknown。

"unknown 不计冲突、满足不升级为全路径相容"的**边界本身正确**（:859-860 note、测试 `test_ppv1_s5a_evaluator.py:561-603` 四例判定与请求一致）；错在缺席/单位/多值细则。**这是实现与冻结判据的直接冲突 ⇒ P1。**（若用户/teacher 想把评测侧定为独立口径，那必须显式声明为另一版本口径并披露分歧清单，不能沿用同名 `essential_conflict` 静默两义。）

值比较的假冲突/假相容具体情形（`_value_matches`，`evaluation.py:757-771`）：
- 单位不同（忽略 unit）⇒ **假相容**；
- 离散枚举拼写不同（`aerobic` vs `aerobic_conditions` vs 大小写）⇒ 假冲突；
- 负数区间 `-5-10` 解析失败（`split("-",1)` 首段空串）⇒ 假冲突；连字符仅此一种，en dash/`to` 不认；
- 事实值是区间 dict（`ConditionFact.value` 允许 dict，`path_context.py:342`）⇒ `str(dict)` 比较失败 ⇒ 假冲突；
- **数值 0 经 `or ""` 变空串**（:791、:802）——`0` 值事实（如氧化还原电位 0 mV、盐度 0）与要求 `"0"` 比对时一侧变 `""` ⇒ 假冲突或错配；
- 多值条件（multiple values）：建议**逐值判定并全量披露**，或保守进 unknown；**不要首条说了算**。

**2) 修改建议（可直接落进规则文字）：**
- S3-1（P1）："评测侧 known_absent 语义与冻结判据四对齐：物种/实体缺席或**同值**字符串缺席 ⇒ conflict；**异值**字符串 known_absent ⇒ unknown；**数值/区间** known_absent ⇒ unknown。"
- S3-2（P1）："要求与事实的 `unit` 必须参与比较：同键不同单位 ⇒ `condition_unit_mismatch`（进 unknown 桶）；带量纲键事实缺单位 ⇒ unknown；无量纲键不受影响。"
- S3-3："同一键多条事实：状态/值不一致 ⇒ `condition_unknown`（保守），全量披露各条；一致 ⇒ 取该一致值；仍按确定性排序。"
- S3-4："值比较前显式规范化：数值 0/空串按类型而非 truthiness 转换；区间支持 `{lo,hi}` dict 与非负 `lo-hi` 串；负区间/其他分隔符不支持时**明示不支持**并落 unknown，不落 conflict。"
- S3-5："要求 `status=known_absent` 的语义须定义（对称处理：事实同为 absent ⇒ compatible；事实 present 同值 ⇒ conflict）或**在 schema 层禁用**至定义完成——现实现仅对 `unknown` 早退（:794-795），known_absent 要求与 known_absent 事实会判 `essential_conflict`（把'一致'读成'冲突'），known_absent 要求遇同值 present 事实会判 `compatible`（把'矛盾'读成'相容'），两个方向都反。"
- S3-6："`subject_scenario_ref` 非空而事实场景为空（=当前场景）时，现行为是**直接比值**（:804 要求双方非空才走场景桶）——须披露'场景对齐为假定、未经验证'，或落独立 `scenario_assumed_matched` 桶。"
- S3-7："`condition_compatible` 的输出 note 补一句冻结判据四原话：'相容是给定事实集的结论，不核事实真实性'（冻结稿 :383-385）。"

**3) 误导风险：**
- **R9（P1）**：同名 `essential_conflict` 两义——生产路由评估说 unknown 的情形，评测指标数 conflict ⇒ `environment_conflict_rate` 系统性虚高，且与冻结判据对不上。
- **R10**：单位静默忽略 ⇒ 跨单位假相容（例：30 K 事实 vs 20–30 °C 要求读成相容）。
- **R11**：`matching[0]` 首条说了算——同一环境两条相反事实时，结果取决于上下文行序（确定性 ≠ 化学正确）。
- **R12**：要求侧 `status=known_absent` 的两个反向误判（见 S3-5）——"一致判冲突、矛盾判相容"，是本面最重的化学误导候选。

---

## 判断面四：矿化证据最低口径（endpoint 声明检查）（问 4）

**1) 结论：有条件同意——负控/停止分账/依赖不洗白/CO₂ 不合并四条与实现一致，但"最低口径三件"实现只落了一件半，且 handoff 检查是死键。**
- 与请求一致的部分（读码核对）：`stop_reason_mislabeled_as_endpoint`（`evaluation.py:889-894`，STOP_REASONS 六原因 :90-92）；`mineralization_claim_without_root_carbon_account`（:895-903，只认证据条目里 `root_carbon_fate_check_scope` 非空）；`unresolved_dependency_promoted`（:909-919，`recorded` 不洗白 ✓）；`co2_merged_across_alternative_routes`（:927-930）；合成例判定与测试一致（`test_ppv1_s5a_evaluator.py:665-720,723-761`）。
- **缺口 A（规则↔实现不一致）**："来源层直报"**正向要求未实现**——现只查"是否全部为 model*"（`all(evidence_basis.startswith("model"))`，:920-926）。证据为 `[inferred_from_pathway]` 或 `[bookkeeping（带 root scope 字段）]` 时**不报误声明**，而 S4 自家政策是"只有 `direct_observation` 可支持 claim、路径推断/模型预测不能单独产生 supported_*"（`endpoint.py:562-564,587-589`）。评测器本应独立复核，却比 S4 生产侧更松。
- **缺口 B**："观察范围"**完全未核**——`evaluation.py` 全文不读 `observation_window`/`detection_range`/`observation_scope`（grep 无命中；字段定义见 `endpoint.py:52-54`、参考侧最低口径字段 `reference_graph.py:76-80`）。请求说三件，实现只有"根碳账范围存在"一件半。
- **缺口 C（死检查）**：`metabolic_handoff_mislabeled_as_mineralization` 判的是 `evidence_basis == "metabolic_handoff"`（:904-908），而 basis 枚举只有 `direct_observation/inferred_from_pathway/model_prediction/no_evidence`（`endpoint.py:136-139`），非法 basis 在 S4 构造期就拒（`endpoint.py:239-245`）⇒ **对契约合法的导出，该检查永远不触发**；该键应为 `endpoint_claim`。这正对应问 4 点名的"把代谢交接终点当永久去除"类声明——现状既抓不到"handoff 证据撑 terminal product"，也抓不到"handoff 当矿化"。
- **缺口 D**：`supported_terminal_transformation_product` + 证据空 + **无停止原因** ⇒ 零误声明（停止检查 :889 需 stop_reason 在场；矿化检查只管 mineralization；model-only 检查要求证据非空 :923）。缺一个通用"supported_* 而证据空 ⇒ 误声明"兜底。
- 分工问题：评测器不做正面矿化判定（归 S4 四分账 + 用户/teacher）**方向正确**（S4 `_assess_endpoint` 已做 direct-only、声明级充分性、F02、S4-C01，`endpoint.py:556-666`）；漏洞不在分工，而在评测器这侧的**误声明清单不完整**（A–D），使"独立复核"退化为"S4 的镜子"。

**2) 修改建议：**
- S4-1："三件最低口径按字段落检查：① `root_carbon_fate_check_scope` 非空（已有）；② **存在** `evidence_basis=direct_observation` 且 `source_refs` 非空的证据条目，否则 `supported_claim_without_source_layer_direct_evidence`；③ 存在 `observation_window` 与 `detection_range` 非空的支撑条目，否则 `supported_claim_without_observation_scope`。"
- S4-2（死键修正）："handoff 类误声明判 **`endpoint_claim == "metabolic_handoff"` 的证据条目支撑 `assessment ∈ supported_*`** ⇒ `metabolic_handoff_promoted_to_endpoint`；basis 键不再参与该判断。"
- S4-3："通用兜底：`assessment ∈ supported_*` 而 `endpoint_evidence == []` ⇒ `supported_claim_without_evidence`（不限于有停止原因的情形）。"
- S4-4："`co2_merged_across_alternative_routes` 仅在 `assessment != unknown` 时计入误声明桶（或单列'记账契约违例'桶）——现只要 `bookkeeping.co2_aggregated=true` 就计，assessment=unknown 的运行也会被记一笔矿化误声明（:927-930 不挂 assessment）。"
- S4-5（问 4 的"未覆盖类型"清单）：至少还应判误声明的类型——① handoff 证据支撑 terminal product（`endpoint.py:664-665` 自己写着"terminal product 不推断永久去除"，评测器无对应检查）；② terminal product 声明缺观察窗/检出范围；③ 任何 supported_* 无证据（S4-3）；④ `annotation_checks` 的 `agrees` 布尔（:931-940）应拆 `overclaim`（预测强于参考）/`underclaim`（预测弱于参考）两向——化学含义相反，合一个布尔读不出是误报还是漏报。

**3) 误导风险：**
- **R13**：`mineralization_claim_without_root_carbon_account` 只要求**一个字符串字段存在**——一个 `bookkeeping` 来源的条目若带了 `root_carbon_fate_check_scope` 字符串即可全绿；"仅 bookkeeping 不构成矿化"靠的是 S4 不会这样填，而非评测器能查出。
- **R14**：handoff 死键（缺口 C）——检查列表上写着有这道门，实际对合法数据永不落闸。
- **R15**：`observed_endpoint_claimed_from_model_only` 读起来像"只用模型证据会报"，实际是"全部条目都是 model* 才报"——一个 model + 一个 inferred 的组合静默通过。
- **R16**（附带、范围外）：`confirmed_error_rate` 的 `confirmed_claim_events` 取的是"无 conditional admission 的**样本数**"（`evaluation.py:1236-1239`），不是"经独立复核确认的声明事件数"——空跑（零事件）样本也会贡献 1；名称与内容不符，读成"已确认声明数"会严重误导（空跑情形**待执行验证**，我未执行）。

---

## 判断面五：共同产物/备选反应不合并（问 5）

**1) 结论：有条件同意——对 `declared_complete` 参考边"精确覆盖才严格"不过宽但偏严且有三处未分轴；对 `partial/unknown` 参考边应单列桶（同意问 5 的方向）。**
- 精确/超集/部分的三分与合成例、测试一致（实现 :712-718、:720-724；状态 :727-732；测试 `test_ppv1_s5a_evaluator.py:222-264`，`matched_strict==2` 见 :915）。备选不合并 ✓、共同产物保留在条目内 ✓（:704-707,749-751）。
- **过严的来源**：覆盖比较的对象是 `from/to_node_ids` 的**严格命中状态集合**，事件侧是全部 `state_ref` 集合——事件多带一个溶剂/水/质子（参考没画）即 `superset` ⇒ 不进严格。参考作者漏画一个真实参与物（如 H₂O），模型更完整的事件反而被扣严格命中。对 `declared_complete` 这是"按声明办事"，但系统性低估严格召回的风险真实存在。
- **`participant_list_status` 评测器根本不读**（`evaluation.py` 无该词；枚举 `reference_graph.py:56-58`）⇒ `partial/unknown` 参考边被当成 declared_complete 治理：超集披露进 `coverage_mismatch_events`，边状态 `matched_participant_coverage_partial`（:729-730）——**这里要更正请求的一句表述**：该状态会进聚合桶（`_aggregate_metrics` :1196-1200），所以不是"仅披露"，而是"单列了桶，但**没按参考侧完整度分流**"。问 5 问"是否应放行超集为'部分覆盖匹配'单列桶"——**同意单列，但不放行进严格**：参考不完整时超集既可能是模型更全、也可能是模型多造，证据不足以给严格；单列成 `matched_superset_reference_partial`（按 `participant_list_status` 分流）即可。
- **角色/系数**：预注册 proposed 文字写着"参与物/**角色/系数**完整匹配"（`preregistration.py:101`），实现只比 state_ref 集合，role 与 coefficient 都不比；而事件 Participant 明明带 `coefficient/coefficient_status`（`hypothesis.py:196-197,226-235`）、参考边 participants 也带（`reference_graph.py:424-434`）。**规则文字（请求面五）已经不提角色/系数，与预注册文字不一致**——两份 proposed 文本须对齐一件：要么实现补比较/披露，要么预注册文字降级为"系数比较归生产侧 audit，评测侧仅披露不比较"。
- 化学例判定（b）：请求的 e1/e2 + 事件 B/C 例与实现/测试一致（含"事件 B 对 e2 超集、事件 C 对 e1 部分"——夹具 e-alt-1 `to=[n-int-occ-a,n-coproduct-h2]`、e-alt-2 `to=[n-int-occ-b]`，`test_ppv1_s5a_schema.py:144-200`）✓。

**2) 修改建议：**
- S5-1（问 5 直答）："`participant_list_status ∈ {declared_complete, source_complete}` ⇒ 现行精确规则；`∈ {partial, unknown}` ⇒ 超集匹配单列 `matched_superset_reference_partial` 桶（**不计严格**），缺项单列 `matched_subset_reference_incomplete`，两者与 declared_complete 的覆盖失配**分开计数**（前者是参考不完整，后者是模型欠/过产出）。"
- S5-2："覆盖桶改名 `non_exact_coverage` + 子标记 `missing_declared` / `extra_participants` / `mixed`——现 `partial_subset` 兜底分支（:715-718）会把'既多又缺'的混合情形也标成 subset，名不副实。"
- S5-3："系数轴：参考 `coefficient_status=known` 且事件 `coefficient_status=known` 时**比对系数**，不等 ⇒ 单列 `stoichiometry_mismatch`（不进严格）；任一侧 unknown ⇒ 披露 `stoichiometry_unchecked`。若本轮不比，规则文字必须写明'严格匹配不含计量核验'。"
- S5-4："角色轴：不参与门禁可以，但请披露 `role_label_mismatch`（模型把 coproduct 标成 principal_product 之类，是记账差异不是化学差异，披露即可）。"
- S5-5："对 `declared_complete` 参考边，事件侧的溶剂/催化/介质类角色（若角色枚举有此类）可豁免出覆盖比较并单列披露——避免'模型写得越全越吃亏'。"

**3) 误导风险：**
- **R17**：`matched_strict` 不含计量与角色核验——名字读作"反应完整匹配"，实际只保证"两侧参与物集合相等 + scope 相等"；2A→B 与 A→B 同判严格。
- **R18**：参考 `partial/unknown` 的超集与模型多产出共用一个桶——参考不全导致的"失配"会被读成模型多造。
- **R19**：`partial_subset` 混合命名（S5-2）——"既缺声明物又多带物"被读成单纯缺项。
- **R20**：预注册文字承诺"角色/系数完整匹配"而实现不比——按预注册文字读报告会高估核验范围（**规则文字与实现必须二选一对齐，这是两份 proposed 文本间的一致性缺陷**）。

---

## 判断面六：distinct occurrence 不按 CN 合并（问 6）

**1) 结论：有条件同意——occurrence 级计数支撑"不同来路不合并"的科学方向，但需补双轴聚合与基数披露。**
- 实现逐 reference 节点一条目、同结构不同 `occurrence_id` 各自独立（`evaluation.py:585-627`；schema 拒重复 occurrence、放行同结构不同 occurrence，`reference_graph.py:310-320`）；测试两 occurrence 均 strict、条目不合并（`test_ppv1_s5a_evaluator.py:267-282`）✓。合成例判定（b）正确。
- 对问 6 的直答：**存在**"预测侧只发生一次、却对两个参考 occurrence 各记一次命中"的情形，且现行输出无法一眼看出——两个 occurrence 的 `matched_state_ids` 是**同一个**预测 state，`predicted_occurrence_count` 也是同一个数（max 基数，:619-620）。若分子按 occurrence 求和，一次产出会被折算成两次"命中"；若两个 occurrence 实为同一事实的双重来源标注（同一事件的不同研究来路），这个膨胀没有化学意义。反过来，若两个 occurrence 属不同场景/研究，而预测只在场景 X 产出——节点匹配**不看场景/条件**（`match_reference_nodes` 不消费 `condition_scope`），跨场景命中照样记 strict。
- 另外两档基数不对称（严格档=出现行数、cn_only 档=事件参与数，:619-626）在面一 R5 已述。

**2) 修改建议：**
- S6-1："occurrence 级召回**与** distinct-结构级召回**双轴都报**：前者分母=参考 occurrence 数（来路不合并的口径），后者按严格身份去重（一次产出对应多条参考声明只计一次）；两轴并列，任何'命中数'必须注明轴。"
- S6-2："同一条目 `matched_state_ids` 长度为1而多个 occurrence 命中同一 state 时，输出附 `shared_prediction_state_group`（按预测 state 分组的 occurrence 列表），让'一次产出、多条命中'机器可见。"
- S6-3："（可选、披露级）occurrence 级场景一致性：比对参考节点 `condition_scope`/来源场景与预测侧上下文，跨场景命中记 `hit_cross_scenario`——不降级（结构命中是事实），但标明'命中的是结构，不是该来路的场景结论'。"
- S6-4："写死一条防误用规则：`predicted_occurrence_count` **不得跨 occurrence 求和**（同一预测 state 会被重复累加）；聚合层如需预测侧出现总量，按 strict 身份去重后统计。"
- S6-5："双重来源标注情形（同一事件被两个研究标注为同一 occurrence 事实）：分母侧是否去重属 §10.1 金标/分母口径（用户/teacher 裁定），评测器只保证两轴数据都在、来路都不删。"

**3) 误导风险：**
- **R21**：单轴 occurrence 计数下，"一产多中"会让召回读数虚高，而输出里没有现成字段暴露这种耦合（S6-2 补）。
- **R22**：跨场景/跨来路命中与同场景命中同名 `strict_structure`——读作"模型重现了该研究的发现"就过了（实际只重现了分子）。
- **R23**：两档 `predicted_occurrence_count` 基数不同（appearance vs participation），跨档比较会得出"cn_only 旁证比严格命中还多/少"的假趋势。

---

## §7 请求汇总（逐面 (a)(b)(c)）

| 面 | (a) 结构性化学错误 | (b) 合成例判定 | (c) 必须补的最低口径 |
|---|---|---|---|
| 一 | **有（P1）**：`cn_only/partial/unknown` 参考节点未封顶，旁证节点可计严格并喂给边严格匹配 | 例1 strict ✓、例2 cn_only ✓（读码+测试 `:493-533` 一致；执行待验证） | S1-1 封顶（P1 必修）+ S1-2 预测侧重算披露 + S1-3 CN 版本核对 + S1-4 cn_only 差异轴披露 |
| 二 | **有**：`unknown==unknown ⇒ matched_strict` 破坏"unknown 不冒充净反应"；scope 不一致事件流入 outside_reference | 例：net vs multistep ⇒ `matched_structure_only` ✓（测试 `:536-555`） | S2-1 严格档要求 scope 已知且相等 + S2-2 net 需 evidence refs + S2-4 outside 桶排除 structure_only 事件 |
| 三 | **有（P1）**：known_absent 一律 conflict、单位不读、多事实首条说了算、零值/负区间/区间 dict 解析错——与冻结判据四五类输入判决不同 | 四例（compatible/unknown/conflict/preference）✓；scenario 例 ✓（测试 `:561-603`） | S3-1/2/3（对齐冻结判据四 known_absent/单位/多事实）+ S3-4 值解析 + S3-5 要求侧 known_absent 定义或禁用 + S3-6 场景空值披露 |
| 四 | **有**："三件"只实现一件半；handoff 检查死键；terminal product 无证据无兜底 | 负控/正控/分类器负控三例 ✓（测试 `:665-720`） | S4-1 三件按字段落检查 + S4-2 改键 `endpoint_claim` + S4-3 supported 无证据兜底 + S4-4 co2 桶挂 assessment + S4-5 未覆盖声明类型清单 |
| 五 | **有（偏严+未分轴）**：`participant_list_status` 不读、系数/角色不比、`partial_subset` 混合命名 | e1/e2 与事件 B/C 覆盖例 ✓（测试 `:222-264`；夹具 `test_ppv1_s5a_schema.py:144-200`） | S5-1 按参考完整度分桶（partial 参考超集单列、不进严格）+ S5-2 命名 + S5-3 系数轴或明示不比 + 与预注册 `:101` 文字对齐 |
| 六 | 无方向性错误；缺双轴与基数披露 | 两 occurrence 各自保留、均 strict ✓（测试 `:267-282`） | S6-1 双轴聚合 + S6-2 共享预测 state 分组 + S6-4 禁跨 occurrence 求和 + （可选）S6-3 场景一致性披露 |

**P1 级发现（实现与冻结判据/冻结原则冲突，请主会话按 P1 登记）：**
- **P1-1（面三）**：评测侧条件三分类与冻结判据四（known_absent 轴归属、单位三态、多事实保守 unknown、necessity 无源不进门禁）在五类输入上判决不同（`evaluation.py:774-816` vs 冻结稿 :370-379 与 `path_context.py:761-762,774-777,790-803,807-837`）。同名 `essential_conflict` 两义。处置二选一：对齐实现，或显式声明评测侧为独立版本口径并披露分歧（后者牵动判据族一致性，属用户/teacher 裁定）。
- **P1-2（面一）**：提议规则文字（cn_only scope 只进旁证桶）与实现（无 scope 分支，`evaluation.py:585-627`）冲突；放行后果是旁证升格为严格确证并传导至边严格匹配（:648-652），触碰冻结稿 §0"旁证不叠加升格"（:42）。冻结 proposed 前必须二者一致。

**proposed 规则文本↔实现不一致清单（非冻结冲突，但冻结前必须收口）**：B1 面四三件（观察范围/来源层正向未实现）；B2 handoff 死键；B3 预注册 `:101`"角色/系数完整匹配"未实现（面五）；B4 unknown==unknown 进严格（面二）；另附带（范围外）R16 `confirmed_claim_events` 名实不符。

**纪律核对（读码层面，与请求声明一致）**：判分零 LLM（`llm_in_scoring: False`，`evaluation.py:1625`；消费字段白名单 :102-118）；确定性（output_sha256 :1639-1640，无时间戳——测试 `:790-826`）；provider 默认关（real 无授权拒绝 :1336-1342）；`evaluated_*` 永不程序生成（`EMITTED_STATUSES` :84-85，状态闸 :1554-1574）；金标写入守卫（`GOLD_AUTHORIZED_ROOTS` :96-100，`persist_evaluation_output` :1647-1681）。本批 audit.py 改动核为披露级 P2（donor-diagnostic-10 与 isotope 轴披露，`audit.py:3,1200,2200`；常驻测试 `tests/test_ppv1_s5a_isotope_regressions.py:22-24`）；profile.py 版本登记核为 `ppv1-reference-graph-1/…/ppv1-evaluation-1/ppv1-preregistration-template-1`（`profile.py:274-277`）——均未读到与六面或冻结判据的化学冲突。全部测试/回归数字（1045 绿等）**待执行验证**（本轮零执行）。

---

以上为完整评审回应。一句话给主会话：**六个面里两个 P1（面三的条件判据与冻结判据四打架、面一的 cn_only 参考节点没封顶会冒充严格确证），四个面有条件同意，合成例判定读码全部正确但测试执行待验证；每面的可落字修改建议和误导风险点已逐条给出，可直接用于 proposed 冻结前的收口。**
