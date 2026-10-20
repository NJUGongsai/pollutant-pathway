# T-H P0b/D-6 旁路披露合同（2026-10-20 冻结；2026-10-21 R1–R3 回修 v2）

> **题域：[298域] = RHEA 通用酶学 / 已见题（post-hoc）。** 本合同的全部计数、
> 状态和回放锚点只在该题域成立，不外推到 dev、新题或其他题域。
>
> **性质：只披露、不判分、不加门。** 本合同的四态与 reason 只用于诊断输出；
> 不进入 admission、候选/池/检索、排序、评分或事件提交。任何入口不得把
> `inconsistent` 当作拒绝候选、删除事件或降低分数的理由。
>
> **基线：** HEAD `c9c6c7a7ae02b46769add09fbc2536323ce8a985`；T-H r2
> v2 headline 89/298，strict 126、partial 53、unmatched 119；1586 个已提交事件。
>
> **2026-10-21 回修（Codex R1–R3）：** 装配轴改为共同多重集/交集计数；
> copy 被引用严格核声明 `state_ref`（结构对应另列披露轴）；缺资料/坏类型
> 保留 unknown，只有确知为空才 `not_applicable`；立体子类改用保留同位素的
> “去立体”代理，仅旧非异构代理相同不能证明只剩立体差 ⇒ 新增诚实未细分子类
> `principal_isomeric_unspecified`。块内 `version=2`、
> `rule_version=p0b-d6-reconcile-2`；不升全局导出/原生结果版本、不改评分。
>
> **依据：** `docs/TASK_T_H_P0B_D6_DISCLOSURE_2026-10-20.md`、
> `docs/T_H_P0_DECISION_CODEX_REVIEW_2026-10-20.md` §四/§五、
> `docs/review_evidence/t_h_p0_2026-10-20/p0b_declared_vs_executed.py` 及其摘要。
> P0 的 296/204/92/52/6 是**历史探针读数**，不是本合同的新判据；本合同的
> 分类若与其不同，必须在实施报告中给出逐项 crosswalk，不能静默改写 P0。

## 1. 冻结的字段与语义

### 1.1 origin（事件来源）

- **唯一来源：** `search_actions.payload.logical_proposal_id`，与 P0 探针
  `origin_of()` 同源、同分类规则。
- `rec-` 前缀 ⇒ `recorded`；`tpl-` 前缀 ⇒ `template`；其余非空值 ⇒ `novel`；
  字段缺失/空串 ⇒ `unknown`（只披露，不改变状态判定）。
- **禁止**从 `spec.compile`、`product_smiles` 形状或文件名反推 origin。生产报告
  本身不带 `logical_proposal_id`，所以 origin 只在原生结果聚合层
  （`native_result.derive_declared_vs_executed`）解析；生产报告侧若单独输出
  诊断，只能写 `origin=unknown, origin_basis=spec_only`。

### 1.2 结构身份版本（不得新造第二套）

- **主身份：** `pathway_v43.pollutant.chemstate.strict_identity_of`（既有单一
  事实源；`_identity_key` = 去除原子映射号/坐标/atomProp/DAT 后的 RDKit
  canonical **CXSMILES** 化学事实子集）。本任务只调用，不复制、不改写、不
  另立规范化。
- **组分多重集：** 对 SMILES 按 `'.'` 拆分后逐组分取
  `strict_identity_of`，排序后保留重复项（多重集，不用集合去重）。
  多重集包含/交集按出现次数计（同一出现只能被一个声明项消费）；
  本层不解释配平系数。
- **立体子类代理键（v2；仅用于区分“仅立体差”，不是第二套身份）：**
  1. **去立体代理（唯一可支持 `principal_stereo_only`）：** 逐组分
     `Chem.MolFromSmiles` → `Chem.RemoveStereochemistry` → 以
     `isomericSmiles=True` 写回 → 再取 `strict_identity_of`。该代理
     **保留同位素、电荷、连接、SGroup 等非立体化学事实**，只去掉立体
     （四面体/双键/增强立体组）。
  2. **非异构代理（仅披露）：** 旧 `isomericSmiles=False` canonical
     SMILES。它同时擦除立体与同位素，**不能**证明“只剩立体差”；只用于
     诚实标注“比结构差更弱、但无法细分”的差异。
- 任一解析失败 ⇒ 该轴 `unknown`，不落 `consistent`/`inconsistent`。
- **禁止**用字符串直接比较、CN 合并、`smiles_isomeric` 原始串比较或新建
  InChI/规范器。

### 1.3 主产物（principal product）

- **声明主产物：** `spec.product_smiles`（既有字段；编译链与 novel 提案同源）。
  该字段本身允许 `'.'` 多组分：多组分时记
  `principal_multi_component=true`，按多重集整体比较；不擅自只取第一段。
- **无主产物：** `spec.product_smiles` 缺失/空 ⇒ `unknown_reason=
  missing_declared_principal`；不得用 `coproducts[0]` 或投影 rank1 代填。
- **归属（attribution）：** 以 `production_report.report_projection.product_ranks`
  中 `report_rank==1` 的 `state_ref` 为归属依据；该状态的结构经 `states` 表
  解析后与声明主产物比较。
  - 无 rank1、状态缺失或无法映射 ⇒ `principal_attribution.basis="none"`，
    记 `principal_attribution_unknown`；**这是 proof_scope 限制，不是状态
    阻断项**（不因此把可比较的声明/执行对判成 unknown）。
  - 多组分主产物 ⇒ 归属只能披露 `multi_component`，不强行挑一个组分。
- **禁止**用 `hypothesis` 参与者顺序、投影文本或报告宽度反推主产物。

### 1.4 实际生成组分（executed components）

- **唯一来源：** `production_report.execution.result.product_smiles`（运行时
  真实 `execute_edits` 输出；不重跑、不重建、不用 expectation 或 compile
  期 execution 代替）。
- 按 1.2 拆分为多重集；`execution_ok`、`result.ok`、`result.product_smiles`
  任一缺失/假 ⇒ `unknown_reason=execution_not_verified`（或
  `missing_executed_product`）。
- **声明生成组分多重集** = `spec.product_smiles` 组分 ⊕ `spec.coproducts`
  组分（copy 不计入；copy 是声明未执行）。
- **装配轴（R1，v2）：** novel spec 的共同产物需要事件装配支持时，用
  **声明生成组分整体多重集**与事件产物侧参与物多重集做包含/交集：
  同一出现只计一次，重复 coproduct 缺一份即判
  `declared_coproduct_missing_from_event`；`declared_generated_present`
  输出共同多重集交集计数，不得用“同结构出现过”无限复用。
- 对应关系只输出计数与关系枚举：`equal / declared_subset_executed /
  executed_subset_declared / overlap / disjoint / unknown`；不输出组分正文。

### 1.5 copy 来源

- **唯一来源：** `spec.declared_copy_components`，逐条要求
  `component_source == "record_declared_copy"`；其他标签 ⇒
  `unknown_reason=copy_source_unverified`，不得当作已核 copy。
- copy 的合同地位：**记录侧声明、未经执行通道**（`declared_not_executed`）。
- 合法 copy 的判定（全部满足才算合法，不因 copy 判不一致）：
  1. **被引用（唯一合法性轴，R1）：** 事件产物侧参与物引用集合包含
     该 copy 声明的 `state_ref`（非空字符串精确匹配）；结构是否出现只作
     另一披露轴 `structure_in_event_products`，**不得用 OR 替代引用**；
  2. 不在 `execution.result.product_smiles` 组分内；
  3. 不在 `execution.tool_inputs.expectation.target_smiles` 组分内。
- 违反 1/2/3 任一 ⇒ `inconsistent`，子类 `copy_contract_violation`，reason
  指向具体字段（`copy_missing_from_event` / `copy_executed` /
  `copy_in_expectation`）。
- copy 不被要求出现在执行碎片中；**“copy 不在执行结果”本身不是不一致**。
- copy 结构多重集出现在事件产物侧但声明 `state_ref` 未被引用 ⇒ 仍按
  `copy_missing_from_event` 判不一致；`structure_in_event_products=true`
  只作为“结构出现过”的披露，不改变状态。

### 1.6 执行/装配边界

| 组分 | 边界标签 | 判定依据 |
|---|---|---|
| 主产物（compiled spec） | `execution_derived` | `spec.compile` 在位（编译器/装配器从离线执行派生 `product_smiles`） |
| 主产物（novel spec） | `model_declared` | `spec` 无 `compile` 块；`product_smiles` 由模型提案声明，执行只作支持核验 |
| 共同产物（compiled spec） | `execution_derived` | 同一编译执行拆分出的其余组分 |
| 共同产物（novel spec） | `assembly_declared` | 模型声明，进入事件装配；执行碎片不要求包含 |
| copy 组分 | `record_declared_not_executed` | `component_source=record_declared_copy` |
| 事件产物参与物 | `assembly` | `events.payload.participants` 产物侧 |

- 边界不明（如 `spec.compile` 缺失且 origin 也缺失，或状态表无法解析）⇒
  该轴 `unknown_reason=component_boundary_unknown`；不得默认成
  `execution_derived` 或 `assembly_declared`。
- 边界只决定“拿哪一侧比较”，不改变身份、不改变评分。

### 1.7 适用性（applicability；R2 修订）

- **来源缺失优先（v2）：** 事件无可用 production report ⇒ 阻断型
  `missing_production_report`；action 无 spec 或 spec 非对象 ⇒
  `missing_spec`。来源缺失不得因声明/执行为空而被洗成 `not_applicable`。
- **`not_applicable`（唯一条件）：** 来源在位（report/spec 均可核）、
  `execution` 在位且 `execution_ok/result.ok` 为真，并且
  `spec.product_smiles`、执行产物、`coproducts`、`declared_copy_components`
  **均确知为空**。此时四态只能是 `not_applicable`。
- **`applicable`：** 其余所有情况，包括字段解析失败、执行未核、边界不明、
  资料缺失/坏类型。
  “适用”只表示合同应处理该事件，不表示能给出结论；结论可为 `unknown`。
- 空声明 + 有执行 ⇒ `applicable`，状态 `unknown`（`missing_declared_principal`），
  不洗成 `consistent`。
- **“明确空参与物”是已核为空：** 事件 `participants` 存在且为合法空列表 ⇒
  装配侧已知为空；需要装配比较时按“缺失/矛盾”判不一致（如
  `declared_coproduct_missing_from_event`），不得升级成
  `event_assembly_unavailable`。`participants` 缺失、字段非列表、条目非对象、
  产物侧 `state_ref` 缺失或状态结构不可用 ⇒ 装配资料不可用。

### 1.8 proof_scope（本次对账能证明什么）

每个事件固定输出：

```json
{
  "scope": "event_local_execution_vs_declaration",
  "verified_range": "declared generated components vs this event's recorded execution.result fragments; copy and event assembly checked only where the recorded fields exist",
  "proves": [
    "under the frozen strict identity, whether the declared principal product is present in this event's recorded execution fragments",
    "whether declared generated components are present on the side determined by the frozen execution/assembly boundary",
    "whether copy components stayed outside execution and inside the event product side"
  ],
  "does_not_prove": [
    "reaction mechanism or enzymatic/biological feasibility",
    "reference/gold answer correctness",
    "reaction balance or stoichiometric completeness",
    "candidate ranking, pool quality or scoring semantics",
    "that a consistent event is chemically correct",
    "that an inconsistent event is a chemically wrong answer"
  ],
  "unverified_ranges": []
}
```

- `unknown` 状态必须把阻断原因写入 `unverified_ranges`（如
  `execution_not_verified`、`principal_unparseable`）。
- 不认证机制、不认证金标、不认证整条反应已由 edits 证成、不承诺收益。

### 1.9 四态（互斥，判定优先级固定）

按以下优先级**从上到下**取第一个成立者，保证互斥：

1. **`not_applicable`**：满足 1.7 的空声明条件。
2. **`unknown`**：存在任一**阻断型** `unknown_reason`（见 1.10）。
3. **`inconsistent`**：满足以下任一（且无阻断型 unknown）：
   - `principal_absent`：声明主产物多重集不 ⊆ 执行组分多重集，且去立体
     代理与非异构代理也都不匹配（结构/连接不同，或差异强于异构事实）；
   - `principal_stereo_only`（R3 强义）：strict 多重集不 ⊆ 执行，**且**
     去立体代理（保留同位素及其它化学事实）多重集 ⊆ 执行；即已证只剩
     立体差。**不得**仅凭非异构代理相等（它同时擦除同位素）判定；
   - `principal_isomeric_unspecified`（v2 诚实未细分）：strict 不 ⊆ 执行，
     去立体代理也不匹配，但旧非异构代理相等；差异属于立体/同位素/其它
     异构事实但无法细分为“只剩立体”。不得洗成 `consistent`，也不得
     沿用 `stereo_only` 强义；
   - `declared_component_absent_from_executed`：`spec.compile` 在位时，声明
     生成组分（主+共同产物）中有组分不在执行碎片内（多重集口径）；
   - `declared_coproduct_missing_from_event`：novel spec 的声明生成组分
     多重集未被事件产物侧参与物共同多重集支持（含重复 coproduct 缺一份）；
   - `copy_contract_violation`：违反 1.5 的 1/2/3（引用轴严格按 `state_ref`）；
   - `expectation_contradiction`：`expectation.target_smiles` 可解析且声明
     主产物不在其组分内；
   - `assembly_contradiction`：投影 rank1 归属的 `state_ref` 不在事件产物
     参与物内，或归属结构与声明主产物不同（仅在归属可解析时判定）。
4. **`consistent`**：其余情况。要求：主产物 strict 多重集 ⊆ 执行组分；
   适用边界上的声明生成组分均被对应侧多重集支持；copy 引用合同成立；无矛盾。

- `inconsistent_subclass` 只取一个**主**子类（按上面顺序第一个命中的
  inconsistent 子类）；`reason_codes` 可列多个，顺序固定。
- `stereo_only` 是 inconsistent 的**立体子类**，不得并入“结构不同”；
  只有去立体（保留同位素）代理相等才可输出。
- `consistent` 只支持“已核的局部结构对应”，不是“化学正确”或“机制已证”。

### 1.10 unknown_reason（枚举，冻结）

阻断型（出现即 `status=unknown`）：

| 值 | 含义 |
|---|---|
| `missing_production_report` | 事件找不到对应 production_report |
| `missing_spec` | action 无 spec 或 spec 非对象 |
| `missing_declared_principal` | `spec.product_smiles` 缺失/空 |
| `missing_executed_product` | 执行结果无产物串 |
| `execution_not_verified` | `execution_ok`/`result.ok` 为假或执行字段缺失 |
| `principal_unparseable` | 声明主产物不可解析 |
| `executed_unparseable` | 执行产物不可解析 |
| `declared_coproduct_unparseable` | 声明共同产物不可解析 |
| `declared_copy_unparseable` | copy 声明不可解析 |
| `expectation_unparseable` | expectation 存在但不可解析 |
| `copy_source_unverified` | copy 的 `component_source` 非 `record_declared_copy` |
| `component_boundary_unknown` | 无法按 1.6 定边界 |
| `event_assembly_unavailable` | **需要装配侧比较**（copy 或 novel coproduct）但事件参与物缺失/坏类型/不可解析（R2：与“明确空列表”区分） |

非阻断型（只披露，不改变状态）：

| 值 | 含义 |
|---|---|
| `origin_unknown` | `logical_proposal_id` 缺失/为空 |
| `principal_attribution_unknown` | 无投影 rank1 / 归属不可映射 |

- `unknown_reason` 取阻断型中**枚举顺序第一个**；`unknown_reasons` 列全部。
- 不得把阻断型 unknown 写成 `consistent`；也不得为了“看起来干净”把可解析
  的明确矛盾降级成 unknown。

## 2. 输出字段（per event）

```json
{
  "schema": "p0b-declared-vs-executed-1",
  "version": 2,
  "rule_version": "p0b-d6-reconcile-2",
  "identity_version": "chemstate.strict_identity_of (CXSMILES chemical-fact subset)",
  "ordinal": 1,
  "qid_prefix": "…",
  "event_id_prefix": "…",
  "origin": "recorded|template|novel|unknown",
  "origin_basis": "logical_proposal_id_prefix",
  "applicability": "applicable|not_applicable",
  "status": "consistent|inconsistent|unknown|not_applicable",
  "inconsistency_subclass": null,
  "reason_codes": [],
  "unknown_reason": null,
  "unknown_reasons": [],
  "declared": {
    "principal_present": true,
    "principal_multi_component": false,
    "principal_components": 1,
    "coproduct_components": 0,
    "copy_components": 0,
    "generated_components_multiset_size": 1,
    "sources": ["product_smiles", "coproducts"]
  },
  "executed": {
    "verified": true,
    "components": 1,
    "source": "production_report.execution.result.product_smiles"
  },
  "component_relation": {
    "relation": "equal|declared_subset_executed|executed_subset_declared|overlap|disjoint|unknown",
    "principal_in_executed": true,
    "principal_nonstereo_in_executed": true,
    "principal_flat_in_executed": true,
    "principal_nonisomeric_in_executed": true,
    "declared_missing_from_executed": 0,
    "executed_extra": 0,
    "boundary": "execution_derived|model_declared|assembly_declared|mixed|unknown"
  },
  "principal_attribution": {
    "basis": "report_projection.product_ranks[report_rank=1]|none",
    "attributed": true,
    "matches_declared": true,
    "state_ref_prefix": "…"
  },
  "copy": {
    "applicable": false,
    "n": 0,
    "source": "record_declared_copy",
    "execution_status": "declared_not_executed",
    "in_event_products": null,
    "structure_in_event_products": null,
    "in_expectation": null,
    "in_executed": null
  },
  "expectation": {
    "present": true,
    "principal_present": true
  },
  "assembly": {
    "event_product_components": 1,
    "declared_generated_present": 1,
    "copies_present": 0,
    "copy_refs_present": 0
  },
  "audit_cross_ref": {
    "center_match": true,
    "strict_target_match": false,
    "declaration_mismatch": false,
    "proof_scope": "self_contained_recompute"
  },
  "proof_scope": { "…": "见 1.8" }
}
```

- 输出**不含 SMILES、不含量组正文**；只含计数、布尔、枚举、前缀。
- `component_relation` 三个代理字段（v2）：
  - `principal_nonstereo_in_executed`：去立体（保留同位素）代理的多重集包含；
    只有它为真才支持 `principal_stereo_only`；
  - `principal_nonisomeric_in_executed`：旧非异构代理（同时擦除立体+同位素）；
    为真但去立体代理为假时输出 `principal_isomeric_unspecified`；
  - `principal_flat_in_executed`：兼容字段，等于旧非异构代理结果，仅披露，
    **不能**单独证明立体子类。
- `copy.in_event_products` 是合法性轴（严格 `state_ref`）；
  `copy.structure_in_event_products` 是另一披露轴（结构多重集是否出现），
  不能替代引用轴。
- `assembly.declared_generated_present` / `copies_present` 是共同多重集交集
  计数（同一出现只计一次）；`copy_refs_present` 是按声明 `state_ref` 被引用
  的 copy 条目数。
- `event_id_prefix`/`qid_prefix` 各取前 20 字符（证据目录同规）。
- 排序：按 `(created_at, event_id)` 与既有候选序一致；`ordinal` 从 1 起。
- 顶层聚合块：

```json
{
  "schema": "p0b-declared-vs-executed-1",
  "version": 2,
  "rule_version": "p0b-d6-reconcile-2",
  "identity_version": "chemstate.strict_identity_of (CXSMILES chemical-fact subset)",
  "universe": "submitted events in native export payload",
  "n_events": 1586,
  "counts": {"consistent": 0, "inconsistent": 0, "unknown": 0, "not_applicable": 0},
  "by_origin": {},
  "events": []
}
```

## 3. 开关、版本与等价承诺

- **开关：** 环境变量 `PPV1_P0B_D6_DIAGNOSTICS`，默认**关闭**。
  接受 `1/true/yes/on`（大小写不敏感）为开启；其他值/未设置为关闭。
  `build_native_result(..., include_declared_vs_executed=None)` 时读开关；
  显式 `True/False` 覆盖环境。
- **关闭时逐字节等价：** `build_native_result` 返回的 payload 不新增键；
  `export_native_result` 的 payload/manifest 字节与基线一致；
  生产报告、事件、action、hypothesis 零改动。
- **开启时：** 只在原生结果 payload 顶层新增 `declared_vs_executed` 块；
  `export_native_result` 在 manifest core 新增
  `diagnostic_bindings.declared_vs_executed`（含
  `schema/version/rule_version/n_events/digest`）。
  不改既有字段、不改事件/候选/排序/评分。
- **版本承载（v2，2026-10-21）：** 诊断块自带
  `schema=p0b-declared-vs-executed-1`、`version=2`、
  `rule_version=p0b-d6-reconcile-2`；manifest 绑定其
  `schema/version/rule_version/n_events/digest`。**不升**
  `ppv1-native-result-2` / `ppv1-native-export-3` / 导出策略版本：
  该块是**可选附加披露**，旧导出（无块）继续按原语义读取，读取路径不新增
  硬门；全局版本升位会使历史导出全部失败，且需改白名单外的 `profile.py`。
  若 Codex 要求全局版本升位，另行扩白名单并重做零漂移门。
- **v1 块的处理：** `version=2` 只影响显式 `read_declared_vs_executed`
  对块版本的校验；2026-10-20 的 v1 块按历史证据保留，不由新读取器消费；
  无块的旧导出路径完全不变。普通 `read_native_export` 不因块版本改变结果。
- **消费面：** `native_export.read_declared_vs_executed(payload)` 只在显式
  调用时校验块 schema/version/digest；普通 `read_native_export` 不因块
  存在与否改变结果。

## 4. 允许改动面（白名单对照）

| 文件 | 允许新增 | 禁止 |
|---|---|---|
| `src/pathway_v43/pollutant/production.py` | `P0B_D6_*` 常量、`build_declaration_disclosure()`、`reconcile_declared_vs_executed()`、纯辅助函数 | 改 `prepare_hypothesis`/`execute_atomtool_expansion`/`expand_hypothesis_production` 的既有语义；写事件/状态；调用评分 |
| `src/pathway_v43/pollutant/s5b_builder.py` | `assembled_declaration_boundary()` 纯函数/常量 | 改 spec 内容或装配结果 |
| `src/pathway_v43/pollutant/s5b_compiler.py` | `compiled_declaration_boundary()` 纯函数/常量 | 改编译/执行/目标 |
| `src/pathway_v43/pollutant/native_result.py` | `derive_declared_vs_executed(payload)`；`build_native_result` 可选参数与顶层块 | 改既有字段/排序/digest 语义（关闭时） |
| `src/pathway_v43/pollutant/native_export.py` | 开启时 manifest 的 `diagnostic_bindings`；`read_declared_vs_executed()` | 改导出策略/版本门/既有引用闭合 |
| `tests/test_p0b_declared_vs_executed.py`（新增） | 8 项控制 + 开关等价 + 集成最小用例 | 改既有测试断言 |

- **不新增第六个源码文件。** 若实施中发现必须改 `profile.py`（全局版本），
  停下来先改合同并报批，不自行扩权。
- 不碰 `evaluation.py` / `s5b_scoring.py` / `runflow.py` / `store.py` /
  `reference_graph.py` / `questions.jsonl` / `llm.env`。

## 5. 合成正负控（Phase C 冻结期望）

| # | 控制 | 输入要点 | 冻结期望 |
|---|---|---|---|
| C1 | 合法主产物 + 多碎片 | 声明主产物 1 组分；执行含主产物 + 2 个额外碎片；共同产物在执行内 | `consistent`；`executed_extra=2`；不得误判 inconsistent |
| C2 | 合法 copy | copy 被事件产物侧引用、不在执行、不在 expectation | `consistent`；`copy.applicable=true`；不得因 copy 判不一致 |
| C3 | 仅立体差 | 声明与执行 strict 不同；去立体（保留同位素）代理相同 | `inconsistent`，`inconsistency_subclass=principal_stereo_only`；不得标 `principal_absent`，不得标 `principal_isomeric_unspecified` |
| C4 | 明确声明矛盾 | 执行产物与声明主产物结构不同 | `inconsistent`，子类 `principal_absent`；reason 指向主产物字段 |
| C5 | 解析失败 | 声明主产物不可解析 | `unknown`，`unknown_reason=principal_unparseable`；不得 `consistent` |
| C6 | 空声明 | 无声明、无执行、无 coproduct/copy | `not_applicable` |
| C7 | 未核执行范围 | `execution_ok=false` 或结果缺失 | `unknown`，`unknown_reason=execution_not_verified`；`proof_scope.unverified_ranges` 保留 |
| C8 | 开关关闭等价 | 同一 payload 开关 off vs 基线 | payload 字节/canonical 完全一致；manifest 无 `diagnostic_bindings` |

**2026-10-21 新增 R1–R3 同根正负控（reconcile 与公开 derive 两层均覆盖）：**

| # | 控制 | 输入要点 | 冻结期望 |
|---|---|---|---|
| R1-a | 重复 coproduct 缺一份 | 声明两份相同 coproduct，事件产物侧只有一份 | `inconsistent`，`declared_coproduct_missing_from_event`；`declared_generated_present` 按交集计 |
| R1-b | 重复份数齐全 | 事件产物侧含两份相同 coproduct | `consistent`；交集计数 = 3（主+两份） |
| R1-c | copy 引用缺失 | copy 声明 `state_ref` 不在事件；同结构以另一 ref 出现 | `inconsistent`，`copy_contract_violation`；`in_event_products=false`、`structure_in_event_products=true` |
| R1-d | 合法 copy | `state_ref` 被事件产物侧引用、不在执行/expectation | `consistent`；引用轴与结构轴均真 |
| R2-a | 报告缺失 | 事件无可用 production report | `unknown`，`missing_production_report`，写入 `unverified_ranges` |
| R2-b | spec 缺失 | action 无 spec/非对象 | `unknown`，`missing_spec` |
| R2-c | 装配资料缺失/坏类型 | `participants` 字段缺失/非列表/条目非对象 | `unknown`，`event_assembly_unavailable`，写入 `unverified_ranges` |
| R2-d | 明确空参与物 | `participants=[]` 且需要装配比较 | 确定性 `inconsistent`（不得升级成 unknown） |
| R2-e | 已知空声明 | 来源在位、执行已核、声明/执行/coproduct/copy 全空 | `not_applicable` |
| R2-f | 合法完整 / 确有矛盾 / 解析失败 | 完整支持 / 结构矛盾 / 不可解析 | `consistent` / `inconsistent(principal_absent)` / `unknown` |
| R3-a | 真实合成立体差 | 仅手性中心构型不同 | `principal_stereo_only`（去立体代理相等） |
| R3-b | 纯同位素差 | 连接/立体相同，仅同位素标记不同 | `principal_isomeric_unspecified`，**不得** `stereo_only` |
| R3-c | 连接差 | 骨架/连接不同 | `principal_absent`，**不得** `stereo_only` |
| R3-d | 解析 unknown | 声明主产物不可解析 | `unknown`，`principal_unparseable` |

- 合法正控（C1/C2/R1-b/R1-d/R2-f）与诚实 unknown（C5/C7/R2-a–c/R3-d）必须
  保留；不允许“全面拒绝换通过”。
- C3 与 C4 必须是不同子类；`principal_stereo_only`、
  `principal_isomeric_unspecified`、`principal_absent` 三者互斥。
- **允许新诊断子类计数改变并解释**：不把原 [298域] 58 写死为验收目标；
  候选/事件/rank/评分及原锚点仍须零漂移。
- **R4 规则级化学评审状态（诚实登记）：** P0 决议要求的“合同/规则级化学评审”
  在本轮终审前**未见交付证据**，此前置**尚未完成**。自包含、零金标零题面的
  规则级请求已落
  `docs/T_H_P0B_D6_CHEM_REVIEW_REQUEST_2026-10-21.md`；本轮未调用外部模型，
  送审通道与采信由 CC/Codex 决定。本合同的程序正负控与零漂移门**不替代**
  化学终认，也不得表述为“实施前已评”。

- 合法正控（C1/C2）与诚实 unknown（C5/C7）必须保留；不允许“全面拒绝换通过”。
- C3 与 C4 必须是不同子类；不得合并成“结构不同”。

## 6. 正式零漂移回放门（Phase D 冻结口径）

**输入：** `/tmp/t_h_p0_r2/runs/<run_id>/native_export/<digest>/`（298 题，
P0 已下载的固定历史导出；runs 根与批根在本机不可达时，以此只读副本为准，
并在证据中披露）。批清单/案例/参考图经
`/tmp/t_h_p0_r2/scoring/` 只读消费；参考图只在冻结 scorer 进程内使用，
不复制、不输出。

**环境：** 本机 `~/miniconda3/envs/depending43/bin/python`，RDKit
**2026.03.6**；批内登记 **2026.03.5**。版本差按任务书固定环境条款如实披露；
若桶/rank 出现漂移，先查版本，不以新结果覆盖历史。

**A/B：**

- A（off）：原始 payload/manifest，原样离线读取。
- B（on）：对同一 payload 调用
  `native_result.derive_declared_vs_executed(payload)` 生成顶层块，重算
  `content_digest`、payload sha、manifest core/export_digest，写入
  `/tmp/p0b_replay_exports/`（不写 runs 根）。
- 剔除 B 的新块（顶层 `declared_vs_executed` + manifest
  `diagnostic_bindings`）后，payload/manifest 必须与 A **字节一致**。

**四项逐项比较（A vs B，剔字段后）：**

1. **候选成员与顺序：** 每题用冻结 scorer 的 `_candidate_events` 口径，
   比较 `event_id` 列表与 `created_at`；298 题逐题相等。
2. **事件身份/内容/顺序：** `events` 列表按 `(created_at, event_id)`；
   逐事件 `event_id`、`payload` canonical 哈希、序号；总数 **1586**。
3. **位次：** 126 个 strict 题逐题 `rank` 与 `n_candidate_events` 相等。
4. **评分语义：** 逐题桶与聚合 `hit@1=89`、`hit@3=118`、`hit@5=125`、
   `strict=126`、`partial=53`、`unmatched=119`；hit@1 是 strict 子集。

**额外披露：** 6 个 strict 对照事件的诊断字段逐条落盘（只前缀/计数/枚举），
并交叉 `strict_target_match` / `declaration_mismatch`；不据此加门、不改分。

**失败处理：** 任一项不等或锚点不复现 ⇒ 门失败，停下报告；不得以“新字段
不影响评分”的口头论证替代逐项 diff。允许的差异只有 B 中新增的诊断块
（剔字段后必须为零）。

## 7. 非目标（写死）

- 不做一致性硬门；不拒绝候选；不改 admission/排序/评分/候选/池/检索/编译准入。
- 不修 D-3 delta、不修 D-7 route、不做 v3 promotion、不重判、不回写旧成绩。
- 不考古原始模型响应；无法恢复的来源写 `unknown`。
- 不读金标/`reference_graphs`/`questions.jsonl`/`llm.env`/私钥；不输出化学结构正文。
- 不跑 HPC 作业、不调模型、不 push、不写封存批根/runs 根。