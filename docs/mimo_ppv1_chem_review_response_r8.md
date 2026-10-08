> **通道与 provenance（主会话 ZCode 记录，非 mimo 回应正文）**
>
> - 2026-10-07 R8 轮（用户已拍板开 R8，按 AGENTS.md「评审-回修自动循环」轮内第③步自动送审）：请求经 **opencode 免费模型 `opencode/mimo-v2.6-flash-free`** 只读评审；opencode 会话 `ses_eeb143e1cffeFDe4prKTG10UCJ`（标题 "mimo ppv1 v8 chem review"）。与手机 mimo 应用是否同一实例未经证实，采信按本通道口径区分。
> - 本轮运行中途一次 `ECONNRESET` 断流，opencode 侧自动恢复后完整输出；续会话确认回应无遗漏（按请求 §7 不设总评段，条件汇总即收尾）。
> - 评审为**只读**：模型自述未执行任何测试/探针，执行类声明一律标注"待执行验证"。其中 PPV1 536 passed 已由主会话本机独立复跑证实（2026-10-07）；G01 安全隔离 1138/8/17 为交付方隔离证据（主会话核对其 run_result 与逐项缺席依赖，未复跑），留 Codex 复核。
> - 请求原文：`docs/mimo_ppv1_chem_review_request.md`（v8，自包含、无金标）。运行证据与原始输出：`docs/review_evidence/ppv1_r8_mimo_2026-10-07/`。
> - 以下为 mimo 回应原文（仅清理终端控制字符，未做任何内容改动）。

---
# mimo 化学评审回应：pollutant_pathway_v1 化学判据草案 v8（R8 轮）

- 评审对象：`docs/mimo_ppv1_chem_review_request.md`（v8 全文）
- 方式：只读读码（`src/pathway_v43/pollutant/` + `tests/test_ppv1_*.py`），未执行测试、探针或任何脚本；凡需执行证据的声明一律标 **待执行验证**
- 格式：按请求 §7，逐判据给 1) 结论 2) 落字建议 3) 化学误导风险点；不给总体评价

---

## 1. 判据一：分子身份

### 1) 结论：**同意**（(a)(c)(d) 直接同意；(b) 附一条完整性限定）

**(a) 2b 判定范围是否闭合 v7 缺陷、不含越权认证——同意。** 读码逐项对应：
- 恢复入口：`ChemicalState.from_dict`（chemstate.py:630，:648 调 `validate_state_object`）——v7 的"只校版本与 fidelity 枚举"缺陷已被替换为完整纯状态验证；
- audit 直接对象入口：`audit_hypothesis` 对每个被消费 state 首消费同验（audit.py:474–475），raw_structures 亦走 `build_chemical_state`（audit.py:460–468）；
- `validate_state_object`（chemstate.py:754–910）与文字 (i)–(v) 逐条同构：版本门 + fidelity 分轴 + origin 合法；CN-only 专用命名空间与未知事实契约（:791–821）；`structure_smiles_raw` 非空且过与工厂同一的 `_guard_input_cx_classes`（:395–456，在 :883–910 内调用）；raw→strict 同图异拼写（OCC/CCO）接受、跨分子拒绝；state_id/formal_charge/cn_identity/立体/同位素按工厂同源重推导（:839–880）；
- "不认证来源真伪、历史执行或机制"与实现一致：validate 只重算对象内部可确定事实，不消费任何来源/运行字段语义，未越权。

**(b) 入口清单与 C2 划界——在读码范围内同意，附完整性限定。** 共用同一守卫的入口读码确认：`build_chemical_state`（chemstate.py:687）、`strict_identity_of`（:923）、`from_dict`（:648）、audit 直接 states（audit.py:474–475）、store writer/replay 同源 `_verify_state_payload_facts`（store.py:377，调用点 :689/:1013；重放复算 :1179–1216）、判据五四原始字段（audit.py:2569–2592）。非消费入口划界与 C2 相符：池输入 preview `run_input_preview`（pool_audit.py:248–309）结果标记 `pool_unchanged`/`diagnostic_only`，不产身份；`substrate_profile.py:91` 只消费 `smiles_isomeric`；conservation 与冻结外围服务内部解析不产 verified；events/legacy_reader 均经 `build_chemical_state` 归一；pollutant 包内未发现绕过工厂的 `ChemicalState(...)` 直构点。**限定：grep 级"无遗漏入口"是读码结论，完整性待执行验证**（建议验收：在 `src/` 内 grep `ChemicalState(`、`MolFromSmiles(`、对 `.smiles_isomeric`/`.structure_smiles_raw` 的赋值，逐点归类为"过守卫/不产身份"两类，白名单外为空）。

**(c) 同意不需重评。**

**(d) 同意，且建议升格为规则正文。** 该句目前只出现在"请评审"问题里，不是规则条款；读码确认 src 内不存在任何从 `r` 反推消旋/样品纯度的路径（全仓无此类字符串）——即"拒绝不反推含义"当前是代码行为的**偶然事实**，不是受约束条款。应写进 2b 正文。

### 2) 落字建议（可直接进规则文字）

1. 2b 末新增一条 bullet，原文：**"原始 `r` 标记的存在与含义均不被采纳也不被反驳，拒绝事实不得用于推断实验消旋/样品纯度。"**（即 (d) 句升格）
2. 2b 的"共用与公共 writer 同源的纯状态验证"后补括注：**"同源验证证明与工厂契约一致，不是独立双算"**——把证明范围写明，防下游读成双重独立核验。
3. (b) 划界句后可补一句点名：**"preview 输出字段不得进入 center evidence 或 state payload 的任何字段"**（现有"不得以任何方式回流"为原则句，点名一次更难被绕）。

### 3) 化学误导风险点

- **同源即自证**：`validate_state_object` 与工厂/writer 共用同一重推导实现。契约一致性由此保证，但若 canonical 重推导本身有边界行为（如 RDKit 对某 CX 项的解析与词法守卫不一致），篡改与验证会同向通过、不互检。§6 末条的 RDKit 锁版本往返无损复核必须覆盖这一对——**待执行验证**。
- **拒绝语义靠异常上抛**：2b 的"结构化拒绝"在 audit 链上表现为异常逃逸（见判据五风险 1），若调用方吞异常则降格；2b 文本已写"不得 R6"，但承担方在调用侧。

---

## 2. 判据二：参与物计量与元素/电荷核算

### 1) 结论：**同意，不需重评**

读码确认已同意条款未变：R5d 触发集合限定 `{element_accounting, formal_charge_accounting}`（audit.py:227–228）；电荷轴 fidelity 前提（audit.py:652–678）；结构化 `omission_pattern_matches` 与 `H+_count1` 命名；"恒等≠落点"口径句保留。v8 关于"状态验证使 formal_charge/stereo/isotope 自报值与结构重推导同源"的增补，与 `validate_state_object` 的 (iv) 重推导（chemstate.py:839–880）一致。

### 2) 落字建议

- v8 那句加一个入口限定：**"……不再可被直传对象伪造（经判据一 2b 首消费验证的入口）"**。"同源"只对过 validate 的入口成立，不加限定会被读成无条件性质；判据二的前提事实上**依赖判据一 2b 的执行**，这个依赖关系值得写明。

### 3) 化学误导风险点

- **D/T 合并计 H、自由基电子不入元素账**的既有披露（audit.py 注释 :1417–1420 一带）必须保留在规则文本里：数值账"平"在这两类上有系统盲区，属已知诚实缺口，不得被读成"质量/电子守恒已核"。v8 未动此句，保持即可。
- `formal_charge` 重推导依赖 RDKit 形式电荷约定，其边界行为随冻结前 RDKit 复核一并确认——**待执行验证**。

---

## 3. 判据三：admission 决策表与中心证据契约

### 1) 结论

**(a) "full 两根据"句是否如实反映实现语义——有条件同意。** 读码：`_center_evidence_binding`（audit.py:970–1036）正是两分支——有未覆盖参与物 ⇒ 两侧各自与注册补全规则数值对账（:973–980）+ 许可登记检查（:985–999）；无未覆盖 ⇒ full。补全结果只进 coverage 轴（`coverage_violations`→partial，:1027–1035），strict 身份另走 `strict_identity_of`、元素/电荷归判据二、转化核实归决策表 R6——**"二者都只解除覆盖轴、不外溢"与代码一致**。限定条件见落字 1、2。

**(b) scope 随结论外传的口径（机器披露已落、同屏列 P2）——有条件同意。** 读码确认：`completion_license`/`completion_license_scope` 恒入 center detail（audit.py:1009–1013）；`license_applied` 标志 src 中**不存在**（仅 docs 提及），P2 定位属实。关键是 P2 之前渲染方能否判定"依据含许可补全"——读码答案是**能**：`uncovered_reactant_refs`/`uncovered_product_refs` 非空（:883–886）+ `product_coverage == "full"` + `unlicensed_uncovered_identities` 为空（:1014–1015）三者组合可推导。故本轮边界可接受，前提是落字 2 成立。

**(c) 同意不需重评。**

### 2) 落字建议

1. **scope 字面与规则文本对齐（本判据最重要一条）**。请求第 121–122 行称 scope 文本声明"本许可不区分该参与物的键断裂方式与电子去向"——读码确认**代码 scope 字面（audit.py:1010–1013）不含此句**，该句目前只存在于 docs（r7 回应与本请求）。二选一：
   - ①（推荐）把这句追加进 `completion_license_scope` 字面，一行改动，字段与规则文本对齐；
   - ② 或改规则文本，把该句归属从"scope 文本"改为"许可定义/本规则文本"。
   语义上 scope 的 composition-only 表述已隐含不作键/电子声称，故这是**措辞精度修正，不是化学变更**。
2. **恒入 ≠ 已适用**：补一句——**"completion_license/completion_license_scope 恒入 center detail，字段存在不等于本结论使用了补全许可；判定'依据含许可补全'须看 uncovered_*_refs 非空且 unlicensed_uncovered_identities 为空；在 license_applied（P2）落地前，本句是渲染方唯一判据。"**
3. （可选）"full 两根据"句后注明**"此为对两个代码分支的规则级归纳"**，防止下游按字符串检索"两根据"找机器字段。

### 3) 化学误导风险点

- **R7-5 沿袭未变**：full/expand 结论若脱离 scope 外传，下游把"覆盖全部核实"读成"含 H2 活化在内的全部结构步骤已核实"——程序真、化学假。P2 之前唯一防线是规则文本的同屏义务。
- **恒入字段被误读**为"许可已用/其结构贡献已核"——落字 2 针对此；这是本轮最具体的"程序诚实但化学误导"面。
- H2/[H] 许可仍按严格结构身份、composition-only 登记，"许可边界变化待审"的既有状态保持，同意不扩。

---

## 4. 判据四：条件相容聚合

### 1) 结论：**同意**（10(a′) 前提与实现一致；其余不需重评）

读码：Requirement/ConditionFact 为 `@dataclass(frozen=True)` + 嵌套 `_freeze`（path_context.py:333/:438，_freeze :298）；`derive_child_context`（:2298）先验父对象再冻结快照；行↔签名双向对应 `_validate_phase_history_snapshot`（:1357，由 `from_dict` 与 `validate_context_object` :1502 调 :1537）——"绑定字段一经冻结不得后改、变更须走新评估/新快照"与实现一致。**一处精度差异**：PathContext 本体是**非 frozen** dataclass（path_context.py:1942–1943），其不可变性靠消费前 validate 的内容身份同源重算兜底（:1537–1548，就地改语义字段保留原 context_id ⇒ `context_content_identity_mismatch` 拒），不是 frozen 强制。10(a′) 对 Requirement/ConditionFact 用"冻结"措辞准确，对 PathContext 本体应说"改了必被 validate 拒"。

### 2) 落字建议

1. 10(a′) 原文落字可以，后补半句区分两种机制：**"Requirement/ConditionFact 由 frozen 强制；PathContext 本体非 frozen，其不可变性由消费前 validate 的内容身份同源重算兜底（就地改任何语义字段保留原 context_id ⇒ 拒）。"**
2. （可选）补：**"任何派生/评估/审核入口在消费前必须先 validate（derive 已如此）；绕过 validate 直读字段属违约。"**——把兜底机制的生效条件（必经 validate）写成义务。

### 3) 化学误导风险点

- 内容哈希兜底是**流程性契约**，不是类型系统保证：将来若有调用方直读 PathContext 字段而不跑 validate，兜底即失效。建议探针：就地改一个语义字段后走派生/评估，应整体拒绝——**待执行验证**。
- 将来引入要求可变性时旧快照整体拒绝是有意 fail-closed，规则文本已声明"不当 bug 修"，保持。

---

## 5. 判据五：供体一致性诊断

### 1) 结论

**(a) 拒绝⇒无 disposition 与失败早退边界——同意，与实现一致。** 读码：
- 早退：`execution_ok` 检查（audit.py:2553–2562）在四字段守卫（:2569–2592）**之前**，早退路径不解析四字段、返回全轴 None + `execution_failed`，无任何 verified 泄漏面——8b 对该已知安全边界的描述准确；
- 拒绝：四字段过 `_guard_input_cx_classes`（:2582），`ChemicalStateError` 包装为 `AuditContractError`（:2583–2592，kind=raw_input_cx_class_unregistered）；
- 复算链：proof_record 复跑（:727–751 与 :1105）**无 try 包裹**，异常原样上抛；全 src 无 `except AuditContractError`（grep 读码——完整性**待执行验证**：`grep -rn "except AuditContractError" src/` 应为空）；
- disposition：`decide_admission`（audit.py:1643）为纯函数，src 内无异常路径调用点 ⇒ "拒绝⇒本次审核不产生任何 disposition"成立。
- 附注：src 内 `check_edit_against_donor` 唯一调用点是 audit.py:746（复算链）；实时诊断的生产方调用点在 src 之外（tests/探针），其异常处理属外部契约——这正是 8b"调用方不得吞异常"要约束的对象。

**(b) 两处表述边界与 strict 语义提醒是否足够——同意。** 拒绝 `r` ≠ 证实精确消旋；裸指定 SMILES 只声明表示事实、不称实验纯品/对映纯；strict=True = 同一化学身份（同一 `smiles_isomeric` 身份键），非同一样品/同立体纯度——三句与 `strict_identity_of` 实现一致，足以防常见误读。

**(c) 同意不需重评**（四入口守卫与镜像终态归一 audit.py:2318–2332 读码同 v7）。

### 2) 落字建议

1. 8b 补一条给下游的读法约束：**"execution_ok=False ⇒ 该次诊断结论为执行失败；四轴 None 表示未评估，不表示该轴通过。"**——防止 None 被读成"无异议"。
2. 8b 的"调用方不得吞异常"后补明承担方：**"audit_hypothesis 在 src 内当前无调用方，该约束由回归测试与未来调用方契约承担；任何调用点必须让 AuditContractError 逃逸并中止该次 admission 计算。"**
3. 8c 三句与 (d) 原样落字即可，无需改。

### 3) 化学误导风险点

- **R7-11 沿袭**：拒绝语义靠文本约束、无机器强制。src 内虽无 `except AuditContractError`，但存在多处宽 `except Exception`（store.py:597/:1727、audit.py:1956 等）；读码未见其包覆当前抛点，但未来重构把守卫挪进宽捕获块即静默降格为 retain/unknown。建议加一条静态验收（**待执行验证**）：AuditContractError 各抛点与最近宽捕获之间无包覆关系。
- **全轴 None 的读法风险**（见落字 1）：执行失败的诊断若被下游按"各轴无反对"消费，就是程序上诚实、化学上误导的典型形状。

---

## 附：§6 程序证据的采信状态（非化学结论）

本会话未执行任何命令，以下全部为 **待执行验证**，我不以其自报数字背书：

| 声明 | 验证方式 |
|---|---|
| ppv1 全量 536 passed/0 skip、R8 新增 28 例 | `pytest tests/test_ppv1_*.py -q` |
| 基线 858dd94 红 14/绿 14（12+2 红全为反例翻转） | 在 858dd94 worktree 复跑同批测试做红绿对照 |
| R7 探针 v8 隔离复跑（C1_raw_* 翻转、控制保持、15 案存储） | 按交付书证据目录复跑探针 |
| G01 安全隔离工程回归数字 | 见 R8 交付书 §5；非 1119/16 原环境数字，不外推 |
| RDKit 词法取证与放行正控往返无损 | 冻结前以锁定 RDKit 版本执行复核（§6 末条），**冻结前置项** |

**本轮条件汇总**（均为落字性质，无一要求新增化学机制）：判据一 ①(d) 句升格 ②同源=非双算括注；判据二 ③入口限定；判据三 ④scope 字面/归属对齐 ⑤恒入≠已适用+推导式；判据四 ⑥frozen 与内容哈希两种机制分写；判据五 ⑦None≠通过 ⑧异常承担方写明。其中 ④ 是对请求文本与代码字面不一致的直接修正，建议优先。
