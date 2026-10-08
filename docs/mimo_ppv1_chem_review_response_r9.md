> **通道与 provenance（主会话 ZCode 记录，非 mimo 回应正文）**
>
> - 2026-10-07 S3a 轮（用户拍板"开干 S3"，按 AGENTS.md「评审-回修自动循环」轮内第③步自动送审）：请求经 **opencode 免费模型 `opencode/mimo-v2.6-flash-free`** 只读评审。与手机 mimo 应用是否同一实例未经证实，采信按本通道口径区分。
> - 本轮一次运行完整输出（无断流、无续跑）；opencode 会话标题 "mimo ppv1 v9 chem review"。
> - 评审为**只读**：模型自述未执行任何测试/探针、未访问金标/题面/gitignored 目录，执行类声明一律标注"待执行验证"。其中 PPV1 594 passed 已由主会话本机独立复跑证实（2026-10-07）；G01 安全隔离 1196/8/17 为交付方隔离证据（主会话核对其 execution_result 与逐项缺席依赖，未复跑），留 Codex 复核。
> - 请求原文：`docs/mimo_ppv1_chem_review_request.md`（v9，S3a 底座版，自包含、无金标；v8 快照在 `docs/review_evidence/ppv1_s3a_impl_2026-10-07/s3a_r1/mimo/`）。运行证据与原始输出：`docs/review_evidence/ppv1_s3a_mimo_2026-10-07/`。
> - 以下为 mimo 回应原文（仅清理终端控制字符，未做任何内容改动）。

---
# mimo 化学评审回应：pollutant_pathway_v1 化学判据草案 v9（S3a 底座版）

**评审边界声明**：只读读码（`src/pathway_v43/pollutant/`、`tests/test_ppv1_*.py`、`docs/` 中 R8 报告与旧回应），**未执行任何测试/探针/脚本，未修改任何文件，未访问 gitignored 金标、题面与封存逐题 run 目录**。凡需执行证据的声明一律标 **待执行验证**。下文"读码确认"= 静态阅读结论，"完整性待验证"= 静态检索的边界。

---

## 1. 判据一：分子身份

### 1) 结论：**有条件同意**（(a) 三处落字实质准确；(b)(c) 同意，附两条条件）

**(a) 三处落字——实质同意，附两条精度条件：**

- **"非独立双算"括注：同意，读码属实。** `validate_state_object`（chemstate.py:754）在 :840 直接调 `build_chemical_state` 做重推导，raw 守卫也是同一个 `_guard_input_cx_classes`（:889-890 → :923/ :687 同源）。两个包装（`validate_state_object` 与 store 的 `_verify_state_payload_facts`，store.py:572）确实是同一实现的两次调用，不是两套独立核验。**条件①**：规则文字须写成"同源验证证明的是**与工厂契约一致**；它仍能拒篡改（重推导确定性），但不构成第二次独立核算，不得引为'两处独立核验一致'"——只写"不是独立双算"会被读成"校验可以互相替代/可跳过其一"。
- **`r` 不反推含义升格：同意。** 读码确认 raw 带 `r` 走 `strict_identity_of` → `_guard_input_cx_classes` → `raw_structure_rejected`（chemstate.py:889-899），确属**输入表示层契约**，与实验事实无因果。且反向推断也应被堵：**即使该表示被接受，CX 注解也只是记录者声明，不是分析证明**（建议补对称句，见落字 2）。
- **canonical + `r` 上层错误名语义更正：方向同意，附条件②。** 读码证实 `build_chemical_state` 的输入守卫**先于** RDKit 解析（chemstate.py:684-688，注释明确"RDKit MolFromSmiles 会静默丢弃未登记 CX 类（`|r|`、`|Ln:1|`）"），故 canonical 串含 `r` 时 `state_structure_unparseable` 包裹的内层原因是 `unregistered_cx_class`。**条件②**：`state_structure_unparseable` 是**两个位置共用的上层 kind**（chemstate.py:843-849 与 store.py:574-580），且它同时包裹 `unregistered_cx_class`（守卫先拒）与 `unparseable_smiles`（真解析失败，:689-693）。因此"该上层 kind 实际包裹的是守卫拒绝"只能作为**对 canonical+r 这一例**的说明，规则文字必须写"**按 `detail.reason.kind` 读内层原因**"，否则会被读成全称判断（"凡是 state_structure_unparseable 都是 CX 策略拒绝"）。
- "不等于 RDKit 本体不能解析该串"是 **RDKit 行为声明 → 待执行验证**：仓库取证注释（chemstate.py:684-686）隐含"可解析但静默丢项"，但本会话无执行证据；请求 §6 末条"冻结前以锁定版本复核"必须显式覆盖 canonical+`r` 与 raw+`r` 这一对（见落字 4）。

**(b) v8 已同意范围与正控不重评——同意。**

**(c) S3a 边界披露（0b"搜索层不绕过化学验证"）——在静态读码范围内同意，如实：**

- `search.py` 全文 **无任何化学构造/解析**：grep `Chem.`/`MolFromSmiles`/`strict_identity_of`/`build_chemical_state` = 0 命中；只搬运 dict 与 `PathwayEvent` 身份字段。
- 事件提交走公共入口两处：常规 `submit_action_event` → `self.store.submit_event`（search.py:1079）；B3 恢复同样 `store.submit_event`（:1571），且先经 `read_search_artifact` 的 hash/可反序列化校验（:321-348）与 `_verify_bundle_identity` 的版本/action/attempt/event 身份校验（:1622-1665）。`store.submit_event` 内的版本门、参与物派生引用、`_verify_participants_contract`、事件 ID 重推导、假设同源 ID 复算（store.py:1502-1561）全部保持在搜索链之前。
- 存在正控测试 `tests/test_ppv1_s3a_search.py:1031`（篡改 raw=`CCO |r|` 经搜索驱动提交 ⇒ 拒 + `events==0`）——**测试存在为读码事实，其执行结果待执行验证**。
- 停止报告保留未探索集合（search.py:1421-1427），`exhausted_search` 仅在无 deferred/blocked/悬空请求时成立（:1415-1418），"停止不是化学终点"与实现一致。

**一条转 Codex（非化学，不作本判据条件）**：B3 分支直接调 `store.submit_event`，未见 `_verify_event_frozen_to_action`（:1086）那类"事件 run/parent/context == action 冻结身份"比对——`_verify_bundle_identity` 只验 action/attempt 绑定与 event 自洽。这不构成化学验证绕过（化学校验在 writer 内全量执行），属程序/存储身份范围，按请求分工转 Codex 复核。

### 2) 可直接落进规则文字的修改建议

1. canonical+`r` 段补读法句：**"上层 kind `state_structure_unparseable` 由恢复入口与公共 writer 两处共用，既可包裹 `unregistered_cx_class`（输入守卫先于 RDKit 拒），也可包裹 `unparseable_smiles`（真不可解析）；读取时必须取 `detail.reason.kind`，不得由上层 kind 推断具体原因，更不得推断该结构'化学非法'。"**
2. `r` 段补对称句：**"接受亦不构成认证——任何 CX 注解都只是输入侧声明，不是分析测定结果；拒绝与接受都不涉及样品组成或立体纯度。"**
3. 同源括注扩为：**"同源验证证明与工厂契约一致，不是独立双算；其拒篡改能力来自重推导的确定性，不来自第二次独立实现——两个包装实现的存在不自动变成新阻塞，也不得引为双重证明。"**
4. S3a 边界补一句限定：**"搜索层继承的验证是表示层/账目层契约（只核对象内部一致性），不认证参与物来源真伪、化学稳定性或物种真实存在；'不绕过化学验证' ≠ '搜索产出结构化学上正确'。"**

### 3) "程序上诚实但化学上误导"风险点

- **同源自证（r8 沿袭，仍在）**：canonical 重推导与验证共用实现，若锁定 RDKit 版本对某 CX 项的解析与词法守卫行为不一致，篡改与验证会同向通过、不互检——**待执行验证**，冻结前置。
- **"unparseable"字面误导**：上层 kind 读起来像"这个分子解析不了/不合法"，实际常见成因是登记策略选择（拒绝是本仓决定，不是化学事实）。
- **错误名语义与消旋误读叠加**：若读者把"canonical 带 `r` 被拒"与"raw 带 `r` 被拒"混为一谈，可能得出"系统判定该样为消旋/非对映纯"——两处拒绝的层级（身份规范形 vs 输入表示）不同，规则文字宜各标一次层级。

---

## 2. 判据二：参与物计量与元素/电荷核算

### 1) 结论：**同意，不需重评**（入口限定由判据一 2b 落字承担，但建议正文留一处显式回指）

读码确认既有披露未变：D/T 并入 H、自由基电子不入账、"verified 仅指元素与形式电荷数值闭合、radical 保真轴为已登记缺口"（audit.py:1417-1440、:138-140）；`omission_pattern_matches` 的"仅数值相符、不证明缺项原因、不含电子/质子计量"结构化声明（:1442-1446）；电荷轴独立且 `formal_charge is None ⇒ unknown`（:1476-1484）。

### 2) 可直接落进规则文字的修改建议

1. 判据二正文补一句回指：**"本判据关于 formal_charge/stereo/isotope 自报值不可伪造的性质，仅对经判据一 2b 首消费验证的入口成立（from_dict/直接对象/工厂/公共 writer）；对未过该入口的裸 dataclass 对象不作此声明。"**——否则单独读判据二会读成无条件性质。
2. （可选，加法）把机读披露同步成规则句：**"本判据 verified = 元素与形式电荷的数值闭合，不表示氧化数守恒、电子守恒或自旋守恒。"**

### 3) "程序上诚实但化学上误导"风险点

- **D/T 盲区**：同位素示踪/代动力学数据下，D 增减被计作 H，账"平"不等于氘守恒；披露已在，规则文本必须原样保留。
- **自由基电子不入账**：中性自由基对（同一分子式、形式电荷皆 0）在元素轴与电荷轴**双闭合**，而氧化还原态/自旋并不守恒——"账平"最典型的应用误读就在这里（程序输出 verified、化学结论错）。
- **`omission_pattern_matches` 被读成"已确认补了水/质子"**：代码已声明仅数值相符；规则文本勿用"匹配到遗漏模式"这种因果口吻转述。

---

## 3. 判据三：admission 决策表与中心证据契约

### 1) 结论

**(a) scope 归属更正 + "恒入≠已适用"三条件：有条件同意。**

- **归属更正属实**：我读到的 `completion_license_scope` 字面（audit.py:1010-1013）确为 `"registered:composition_only_hydrogen_equivalents(H2/[H] 按 2[H] 氢当量;数值配平不证明未登记多原子共底物初始图的结构贡献)"`，**不含**"不区分键断裂方式与电子去向"；与 R8 §5 ④ 判定一致。改归属而不动字段字面（= r8 的选项②）在化学语义上无损失：composition-only 本就不作键/电子声称。
  **条件①（本判据唯一硬条件）**："归属许可定义/本规则正文"必须**字面成立**——该句须实际出现在**冻结版判据三正文**里（r8 已指出它此前只活在 docs/评审往来中）。若顺手把它写进 audit.py:260-271 的许可定义注释块，则会改变代码身份哈希（如 §6 中 `workflow/runner.py` 文字变更引发 legacy code_identity 聚合变化的同款情形），须按身份门槛登记；**只落规则正文则零身份影响，优先**。
- **"恒入≠已适用"+ 三条件：如实。** `completion_license`/`completion_license_scope` 恒入 detail（:1009-1015，两分支共用一个 `detail`）；`uncovered_reactant_refs`/`uncovered_product_refs` 在 `base_coverage_detail`（:883-886）恒在。三条件组合确实可推导"依据含许可补全"。
  **精度补充（建议落字，非阻塞）**：第三条件（`unlicensed_uncovered_identities` 空）在 `product_coverage=="full"` 且 uncovered 非空时**被实现蕴含**——unlicensed 非空必追加 violation ⇒ 必为 partial（:991-999 → :1027）。保留作渲染直检无害，但应标注"冗余直检"，并补出**第四态**：uncovered 非空 + partial ⇒ 补全规则**被调用且判负**，同样不构成结论依据。这样才覆盖完整真值表（full×uncovered空 = 未用补全；full×uncovered非空 = 依许可补全且成立；partial×uncovered非空 = 用且不成立；uncovered 空时无第四态）。

**(b) "full 两根据"与补全许可 scope/严格身份登记同 v8、不需重评——同意。** 读码两分支与文字一致（:970-999 有未覆盖 ⇒ 两侧精确对账 + 许可登记；:1000-1005 无违规 ⇒ full；补全只进 coverage 轴）。

### 2) 可直接落进规则文字的修改建议

1. （条件①）判据三正文落一句原文：**"本许可不区分该参与物的键断裂方式与电子去向；这是许可定义的语义边界，非代码 `completion_license_scope` 字面内容。"**
2. 恒入句扩为真值表：**"`completion_license`/`completion_license_scope` 恒入 center detail；字段存在 ≠ 本结论使用了补全许可。判定'本结论依据含许可补全'须同时满足：`product_coverage==full`、`uncovered_reactant_refs`/`uncovered_product_refs` 非空、`unlicensed_uncovered_identities` 为空（第三条在当前实现下被前两条蕴含，保留作渲染直检）。uncovered 非空且 `product_coverage==partial` 表示补全规则被调用且判负，同样不构成结论依据。"**
3. （可选，加法不重开 v8）"两根据"句后补：**"两根据均以参与物系数已知且系数绑定无违例为前提；二者只解除覆盖轴，不解除元素/电荷轴与 transformation_center 轴。"**

### 3) "程序上诚实但化学上误导"风险点

- **R7-5 沿袭未变**：`full` 外传被读成"含 H2 活化在内的全部结构步骤已核实"——程序真、化学假。P2 `license_applied` 落地前，同屏 scope 是唯一防线。
- **composition-only 被读成"H2 均裂已证"**：同一 full 至少兼容同裂/异裂、H·/H⁺/H⁻ 载体、酶促与非酶途径三种以上机理图景；这正是条件①那句话要防的误读（R7-6）。
- **恒入字段被渲染成"许可已用/其结构贡献已核"**：落字 2 针对此；`unlicensed` 空只说明身份在登记许可内，**不**说明该共底物初始图的键变化已被核。

---

## 4. 判据四：条件相容聚合

### 1) 结论：**同意**（两种不可变机制分写与既有实现一致；其余不需重评）

读码逐项对应：`ConditionFact` `@dataclass(frozen=True)` + `__post_init__` 深拷贝转冻结（path_context.py:333-353）；`Requirement` frozen + 嵌套容器构造期转 tuple（:438-450）；**`PathContext` 本体非 frozen**（:1942-1943），其不可变性由消费前 `validate_context_object` 的内容身份同源重算兜底（:1540-1548，就地改语义字段保留原 `context_id` ⇒ `context_content_identity_mismatch`），`from_dict` 侧同款（:2089）。"任何派生/评估/审核入口消费前必须先 validate、绕过即违约"与实现的生效条件一致（兜底只在 validate 被调用时生效）。

### 2) 可直接落进规则文字的修改建议

1. 分写句原样落字（同意），建议再补**重建身份半边**：**"内容身份是可重算的——兜底能拒的是'改了内容还用旧 context_id'，不能拒'改了内容后重算出一个新 context_id'；因此任何因内容变化而重建的 context 必须产生新 context_id 并保留 parent 链，禁止改语义字段后重算 ID 复用旧引用。"**
2. （可选）把"两入口同验"写进正文：**"快照内部一致性与内容身份在 `from_dict` 与直接对象两个入口都执行，缺一入口即为违约入口。"**

### 3) "程序上诚实但化学上误导"风险点

- **流程性契约风险（r8 沿袭）**：内容身份靠"先 validate 再消费"，类型系统不强制；将来若有入口直读字段，兜底即失效。建议探针：就地改一个语义字段（如 pH 事实值）后走派生/评估 ⇒ 应整体拒绝——**待执行验证**。
- **旧快照未被重评 ≠ 旧阶段已被当前数据确认**：`validate_context_object` 明令"不拿当前事实重评旧边"（:1517，正确），但下游易把"历史 `environment_fit=compatible` 快照留在账上"读成"该阶段条件已被现在数据证实"；规则文本宜保留"历史快照是当时的评估、不追改也不追认"。
- **合取不覆盖**：历史逐边合取 + 当前 live 的聚合口径须保持"任一 conflict 即 conflict"，不得因当前步 satisfied 覆盖历史 unknown/conflict（既有三分口径已如此，提醒保持）。

---

## 5. 判据五：供体一致性诊断

### 1) 结论

**(a) "三个 None + converter 元数据"更正表述：同意，读码准确。**

- 失败早退：`execution_ok` 为假 ⇒ 直接返回 `strict_target_match=None, legacy_cn_match=None, reaction_center_match=None` + `missing_info_reasons=["execution_failed:…"]`（audit.py:2553-2562），`center_evidence` 走默认空 dict（:1919）；另一失败分支（before/after 结构不可解析）同为三 None（:2604-2608）。"**不是**'四轴 None'、**不是** converter 整个 evidence 为空"的更正属实。
- converter：`center_evidence_from_donor_diagnostic` 在 `diagnostic.center_evidence` 为空时走兼容路径，返回 `checker_version` + `center_match=None` + `declaration_mismatch` + `center_match_basis` + `evidence_refs`（:2983-2993）——"仍返回版本/来源元数据与 `center_match=None`"属实。
- **建议补一条精确路径（见落字 1）**：该兼容载荷**既无 `checker_scope` 也无 `proof_record`**，进 audit 后先撞 scope 检查（:1064-1071，`reason=center_checker_scope_unknown`）——即使版本已在注册表（:241）也到不了复算，不可能 verified。把这条路径写死，读者就不会以为"带 checker_version 就过了注册门"。
- `None=未评估≠通过`、早退不解析四字段、无 verified 泄漏面、拒绝 ⇒ 无轴结论无 disposition（`AuditContractError` 自 `check_edit_against_donor` :2547/:2584 与复算链 :739/:1076/:1110 一路逃逸，in-src 无捕获）——同意。

**(b) 8d 义务承担方式与当前状态：有条件同意（可接受为 S3a 边界，附一条条件）。**

- 事实核实：src 内 `audit_hypothesis` **无调用方**（grep 仅 :417 定义）；`check_edit_against_donor` 唯一 in-src 调用是复算链（:746），无 try 包裹；全 src **无 `except AuditContractError`**（grep 0 命中）。与 R8 §5 ⑧ 一致。
- **闭合方式足够，但回归必须是负控**：仅"正常路径下异常逃逸"的用例只能证明当前实现不吞；须另有一个**故意用宽 `except Exception` 包住调用**的用例（断言该包覆被静态验收拒绝，或断言不允许继续 admission），否则"调用方不吞异常"只有实现自觉。
- **条件**：在该 S3b caller + 负控回归落地前，规则文字必须保持**"义务未被执行证据闭合"**的披露措辞（当前 v9 已如此写，保持即可），**不得**在冻结文本里改写成"已承担/已闭合"。

**(c) 其余条款同 v8、不需重评——同意**（读码抽查：四原始字符串入口守卫 :2572-2592；strict 同源 `strict_identity_of` :2675-2679；声明–执行对账 :2656-2659 与 :2699-2702；镜像终态写出/重解析同一归一 :2318-2332；奇偶构型/非四面体 unsupported、联合映射对称证据的范围限定与 docstring :1880-1894 一致）。

### 2) 可直接落进规则文字的修改建议

1. 8b 补读法路径句：**"失败诊断经 converter 进入 audit 时，载荷缺 `checker_scope` 与 `proof_record` ⇒ transformation_center 判 unknown（`center_checker_scope_unknown`），到不了内部复算；失败诊断的元数据仅用于追溯，不参与任何轴判定。"**
2. 8d 补闭合判据句：**"闭合 = S3b 生产 caller + 正常逃逸回归 + 宽捕获负控回归；三者齐备前，本义务保持'未闭合、如实披露'状态，冻结文本不得写成已承担。"**
3. （测试侧，静态建议）`tests/test_ppv1_s2.py:1301` `test_f11_execution_failed_all_unknown` 目前只断言 `reaction_center_match`/`strict_target_match` 为 None，**未断言 `legacy_cn_match is None` 与 `center_evidence == {}`**——建议补这两个断言，把"三个 None + 空 evidence"的规则文字钉在测试上（是否已由他处覆盖 → **待执行验证**）。

### 3) "程序上诚实但化学上误导"风险点

- **None 被读成"各轴无反对"**：执行失败的诊断若按"各轴无异议"消费，是本判据最典型的程序诚实、化学误导形状。
- **"converter 仍返回元数据"被读成"该次诊断已产出证据"**：有版本号/来源引用 ≠ 有检查结果；建议落字 1 的"仅用于追溯"半句。
- **`symmetric_equivalent` 被读成机理等价**：拓扑联合对称 ≠ 酶识别/机制等价（docstring :1886-1887 已声明），规则文本须原样保留，防"对称像通过 ⇒ 供体迁移机制已证"。
- **宽捕获降格（r8 沿袭）**：audit.py 内存在多处 `except Exception`（:1956/:2054/:2214/:2316/:2331/:2491），读码未见其包覆当前抛点，但这是**静态结论 → 待执行验证**（验收命令：每个 `AuditContractError` 抛点与最近宽捕获 try 之间无包覆关系）。

---

## 附 1：静态核对清单（读码可确证，非执行证据）

| v9 表述 | 读码位置 | 结果 |
|---|---|---|
| 同源=非独立双算 | chemstate.py:840 调 `build_chemical_state`；:889 raw 同守卫 | 属实 |
| canonical+r 上层 kind 包裹 CX 守卫拒绝 | chemstate.py:684-688（守卫先于 RDKit）+ :843-849 包装；store.py:574-580 同名包装 | 属实（**双包装点须写进文字**） |
| scope 字面不含"不区分键断裂/电子去向" | audit.py:1010-1013 | 属实 |
| license/scope 恒入 detail、uncovered refs 恒在 | audit.py:1009-1015、:883-886 | 属实 |
| Requirement/ConditionFact frozen、PathContext 非 frozen + 内容身份兜底 | path_context.py:333/:438/:1942、:1540-1548、:2089 | 属实 |
| 失败三 None + `center_evidence={}`；converter 回元数据 | audit.py:2553-2562、:2604-2608、:1919、:2983-2993 | 属实 |
| 早退不解析四字段 | :2554 return 早于 :2572 守卫 | 属实 |
| src 无 `audit_hypothesis` 生产 caller；无 `except AuditContractError` | grep 仅 :417 定义；0 命中 | 属实 |
| 搜索层无化学构造、提交走公共 writer、B3 先验 hash/身份 | search.py grep 0；:1079/:1571；:321-348、:1622-1665 | 属实 |
| 停止原因优先级与六原因顺序 | search.py:152-167 | 与请求逐字一致 |
| 十上限、search-limits-3、search-1、delivered_stages | profile.py:83、:142-168、:291 | 属实（**"键/默认/范围/单位与 v2 不变"需历史对照 → 待执行验证**） |
| 篡改 raw 正控测试存在 | tests/test_ppv1_s3a_search.py:1031-1051 | 文件存在属实，**执行结果待执行验证** |

## 附 2：待执行验证（本会话无执行权限，全部不背书）

| 声明 | 需要跑什么 |
|---|---|
| ppv1 全量 594 passed/0 skip（536+58） | `pytest tests/test_ppv1_*.py -q` |
| 基线 00e509a：2 行为红 + 两文件 collection 红（58 未执行） | detached worktree 同字节复跑并分类核对 |
| G01 安全隔离 1196/8/17 及逐项 skip/deselect | 按 R7/R8 白名单口径复跑，核 nodeid 清单 |
| 篡改 raw 经搜索驱动提交被拒、零事件 | 单跑 `test_search_layer_composes_with_frozen_validation` |
| 四崩溃硬杀恢复、H05–H08、预算零额度夹具 | 单跑 `test_ppv1_s3a_recover.py`/`test_ppv1_s3a_search.py` |
| 锁定 RDKit 版本：`|r|` 词法取证 + canonical/raw 往返无损正控 | **冻结前置项**：对放行保留类（含空格/含分隔符）与移除类逐例往返比对 |
| 宽捕获与 `AuditContractError` 抛点无包覆 | 静态验收脚本（抛点 → 最近 try body 逆向可达性） |
| 三 None + `center_evidence=={}` 有测试钉住 | grep/补断言（见判据五落字 3） |

**本轮条件汇总**（均为落字性质，无一要求新增化学机制）：判据一 ①`state_structure_unparseable` 双包装点与 `reason.kind` 读法 ②`r` 拒/受两侧都不构成化学事实 ③同源括注补"确定性拒篡改、非独立复核" ④S3a 边界补"继承验证 ≠ 认证来源真伪"；判据三 ⑤"键断裂/电子去向"句须字面落入冻结正文（落规则文本、优先于改代码注释以免身份哈希变化）⑥恒入≠已适用补完整真值表与 partial=用且判负；判据四 ⑦补"重建必须新 context_id"半边；判据五 ⑧失败载荷缺 scope/proof ⇒ unknown 的路径句 ⑨8d 闭合判据（正常逃逸 + 宽捕获负控）与"未闭合"措辞保持。其中 ⑤ 是对请求归属更正的落地条件，建议优先。
