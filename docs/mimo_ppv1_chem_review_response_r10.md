> **通道与 provenance（主会话 ZCode 记录，非 mimo 回应正文）**
>
> - 2026-10-07 S3a 回修 r2 轮（按 AGENTS.md「评审-回修自动循环」轮内第③步自动送审）：请求经 **opencode 免费模型 `opencode/mimo-v2.6-flash-free`** 只读评审；opencode 会话 `ses_ee97aeae8ffevGFvX57eI0YOCv`（标题 "mimo ppv1 v10 chem review"）。与手机 mimo 应用是否同一实例未经证实，采信按本通道口径区分。
> - 运行事件：判据四读码清单中途一次 `ECONNRESET` 断流；续会话补全判据四剩余部分（补全过程中模型复读源码并给出三处更正：孤儿引用方向与处置写反、"任何入口先验"需限定、r9⑦ 重建半句缺失）。正文由两次运行拼装：主运行（判据一～四前段+判据五+收尾）+ 续跑（判据四接续段，含其被切断那条的完整版）；被切断的残行已剔除、内容由续跑覆盖。
> - 评审为**只读**：模型自述仅用读取类工具、未执行任何测试/探针，执行类声明一律标"待执行验证"。其中 PPV1 648 passed 已由主会话本机独立复跑证实（2026-10-07）；G01 安全隔离 1250/8/17 为交付方隔离证据，留 Codex 复核。
> - 请求原文：`docs/mimo_ppv1_chem_review_request.md`（v10，自包含展开版，无金标）。运行证据与原始输出：`docs/review_evidence/ppv1_s3a_r2_mimo_2026-10-07/`。
> - 以下为 mimo 回应原文（仅清理终端控制字符与上述拼装，未做任何内容改动）。

---
# mimo 化学评审回应：pollutant_pathway_v1 化学判据 v10（S3a 回修 r2 版）

**边界声明**：本轮只用读取类工具浏览了 `src/pathway_v43/pollutant/`、`tests/test_ppv1_*.py`、`docs/`（含 r7–r9 旧回应与 R8/S3a 复审报告）。凡需运行才能确证的一律标 **待执行验证**，并在文末列出需要跑什么；"读码确认"= 静态阅读结论。下文行号均为本轮实际读到的行。

---

## 0/0b. 背景与 S3a r2 边界披露（受审表述）

### 1) 结论：**有条件同意**（五组闭合与"同源非双算"口径在静态读码范围内属实；附三条条件）

**五组闭合的静态核对（读码确认，非执行证据）**：

| 0b 表述 | 读码位置 | 结果 |
|---|---|---|
| 1. B3/写侧/正常提交共用 action+attempt+task+event 身份绑定 | `_verify_event_frozen_to_action` search.py:1379；`_verify_bundle_identity` :2376-2379（S3A-01 已含"事件完整身份冻结到 action"）；`_verify_action_references` :1461；B3 消费前 :2278 | 属实（r9 点名的 B3 缺身份比对已在 `_verify_bundle_identity` 补上） |
| 2. 首次 complete/B4/done 复用经公共 `store.submit_event` 重放分支同源权威核验 | `_verify_event_ledger_authority` :1557-1621（内调 `store.submit_event` :1593）；`_preverify_completion` :1691-1728；`_verify_done_action_authority` :1730 → `_verify_commit_event` :2372；B4 走 `complete_action` :2249；提交记录路径 :2236 | 属实 |
| 3. defer 先核未执行事实 + 十键校验单一实现 | `defer_action` :1884 起；`validate_search_limits` profile.py:258，别名 :295 | 属实 |
| 4. 请求同键异身份冲突零写入 + 执行引用/生命周期 | `register_model_request` :984 起、`_verify_request_execution` :1170、sent/response/failed :1237/:1270/:1297 | 属实 |
| 5. 停止报告披露 claimed/open attempt、阻止 exhausted_search | :2119-2149（claimed_actions/open_attempts 计数，:2137 齐判，:2148-2149 明示不报 exhausted_search） | 属实 |

**"只读复核、非第二套独立化学算法"**：属实且是本批最重要的准确表述 —— `_verify_event_ledger_authority` 直接调 `store.submit_event` 的重放分支（search.py:1593），重放分支对已存 state 行做 `build_chemical_state` 同源重推导（store.py:1274，核 state_id/电荷/CN/立体/同位素），appearence 内容 hash 复算（:1328），假设行内容身份复算（:1640），结尾 `rollback` + `created=False`（store.py:1708-1709）⇒ 行内容零写入。这是**同一实现的再次调用**，不是独立复核。

**三条条件**：

- **条件①（措辞）**："只读、零写入"建议补半句精度：该重放分支以 `BEGIN IMMEDIATE` 开启（store.py:1563）并以回滚收尾 —— **行内容零写入属实，但仍取写锁**；"只读"是结果语义不是事务语义。非化学项，但避免"纯读"被理解为对并发无影响。
- **条件②（承 r9 落字④，建议落进 0b）**：0b 目前只说"不是第二套独立化学算法"，未落 r9 ④ 那句边界 —— **"继承验证只核对象/账目内部一致性，不认证参与物来源真伪、化学稳定性或物种真实存在；'不绕过化学验证' ≠ '搜索产出结构化学上正确'"**。建议原样补入。
- **条件③（自包含性）**：本版自称"展开必要规则全文、不再缩写引用历史"，但正文仍用 `C2`、`mimo⑤`、`mimo v9 ①/⑥` 等外部标签（判据一 (b)、判据三、0b 各处）。`C2` 在 src/docs 中没有与本句对应的定义（`src/.../substrate_profile.py:3` 的 "C2 修复" 指底物档案不依赖候选，非本义）。建议冻结前**逐个内联定义或删掉标签**，否则"自包含"不成立。

### 2) 可直接落进规则文字的修改建议

1. 0b 补：**"搜索层不产生任何 state 身份 —— 身份一律由 chemstate 工厂/公共 writer 重推导产生；搜索层事件消费只复用同一验证源，不构成独立核验，也不认证来源真伪/物种真实存在。"**
2. 0b 补：**"权威核验以事务回滚实现行内容零写入（非纯读事务）；其强度上限 = 公共 writer 重放，writer 的系统性缺陷会同向通过（同源自证，冻结前须独立复核，见 §6）。"**

### 3) "程序上诚实但化学上误导"风险点

- **同源自证被读成"双保险"**：消费侧核验与写侧是同一段代码，锁定 RDKit 版本若对某 CX 类处理与守卫假设不一致，篡改与验证会同向通过 —— 这正是 §6 末条"冻结前以执行证据复核 RDKit 词法取证"必须覆盖的面，**待执行验证**。
- **"S3a r2 闭合"被读成"搜索链已能产出可信化学结论"**：r2 只闭合记账消费协议；`audit_hypothesis` 在 src 内**仍无生产 caller**（仅 audit.py:417 定义），队列化学集成/生产调用链属 S3b，0b 已如实列出 —— 冻结文本不得把这段挪进"已交付"。

---

## 1. 判据一：分子身份

### 1) 结论：**有条件同意**（(a) 三处落字实质准确，附两条精度条件；(b) 入口闭合在静态范围内成立，附一条条件；(c) 同意不重评）

**(a) 2b 三处落字与 r-不反推/内因读法 —— 同意，附两条条件**

- **同源、非独立双算：读码属实。** `validate_state_object`（chemstate.py:754-911）重推导直接调 `build_chemical_state`（:840），raw 守卫走 `strict_identity_of`（:890 → :923）与工厂同一 `_guard_input_cx_classes`（:687）；audit 直接 states 对象在**任何检查之前**统一验证（audit.py:469-475），writer 边界是 `_verify_state_payload_facts`（store.py:471，同源重推导 :572-580）。三个包装同一实现 ✓。
  **条件①**：承 r9 ③，建议把括注补全为：**"同源验证证明与工厂契约一致，不是独立双算；其拒篡改能力来自重推导的确定性，不来自第二次独立实现 —— 两个包装实现的存在不自动变成新阻塞，也不得引为'两处独立核验一致'。"** v10 现文只写了后半（不自动成阻塞/不得读成双重证明），**缺"确定性拒篡改"这半边**，单独读会滑向"验证可互相替代"。
- **`r` 不反推（两侧对称）：同意，v9 ② 已落到位。** "存在与含义均不采纳也不被反驳""拒绝不得推断消旋/样品纯度""裸指定结构/strict 不是同样品/对映纯认证"三条都在 ✓；"当前 RDKit 直接解析 `CCO|r|` 能输出 CCO"属 RDKit 行为声明 ⇒ **待执行验证**（§6 已列冻结前复核，保持）。
- **canonical+`r` 上层 kind 与内因读法：方向同意，附条件②。** 读码确认包装点**两处**：chemstate.py:843-849（`ChemicalStateError`，kind=`state_structure_unparseable`，`detail["reason"]` 带内因）与 store.py:574-580（`Ppv1StateContractError`，**同名 kind**，`reason` 同样带内因）；内因既可是 `unregistered_cx_class`（守卫先拒）也可是 `unparseable_smiles`（真解析失败，chemstate:689-693）。
  **条件②**：v10 现文只说"该上层 kind 实际包裹工厂未登记 CX 类守卫拒绝"，未写**双包装点**与"也可包裹真 unparseable"。建议原句落字：**"`state_structure_unparseable` 由恢复入口与公共 writer 两处共用（异常类不同、kind 同名），既可包裹 `unregistered_cx_class`（守卫先于 RDKit 拒），也可包裹 `unparseable_smiles`（真不可解析）；读取时必须取 `detail.reason.kind`，不得由上层 kind 推断具体原因，更不得推断该结构化学非法。"**

**(b) 入口清单闭合 —— 静态范围内同意，附一条条件**

读码逐入口核对（grep 全 src）：

- 守卫先于解析：`build_chemical_state` :687 → `MolFromSmiles` :688；`strict_identity_of` :923；`validate_state_object` 经 :890 → :923；判据五四原始串字段 audit.py:2572-2592（未登记 ⇒ `AuditContractError` kind=`raw_input_cx_class_unregistered`）。
- 全部身份生产点均经这两条：store.py:572/:623/:1274、events.py:160、legacy_reader.py:400/:438、audit.py:462 —— 无第三条旁路。
- 搜索层：`search.py` 无任何化学构造（本轮回读未见 `Chem.`/`build_chemical_state`/`strict_identity_of`），state 由 `store.submit_event` → `put_state` → `_verify_state_payload_facts` 生成 ⇒ 搜索层不产生身份 ✓。
- 诊断入口划界：`run_input_preview` 输出 `pool_unchanged=True`、`status=diagnostic_only`（pool_audit.py:262/:300-302）；audit 对 preview 只落 `finite_rule_diagnostic` 的 NA/unknown（audit.py:584-596），**到不了 verified** ✓；冻结执行器 `services/atom_tool.py` 内不构造 `ChemicalState`（grep 0 命中），其产物经诊断四字段守卫与工厂进入 ✓。
  **条件①**：判据一 (b) 用的 `C2` 标签在本仓无对应定义（见 0b 条件③），建议改为自述句："诊断入口按下列界：其结果不进入身份、不进入 verified 证据，preview 保持 `pool_unchanged/diagnostic_only`。"

**(c) 判据 1–4 不重评 —— 同意**（文本已展开，逐条与 `_identity_key` :180-226、ABS 令牌级剥离 :513-547、`_CX_STEREO_ITEM_HEAD_RE` :266、RegistrationHash 限定一致性 v4 文档 :17-23、`put_state` 语义/出现拆分 store.py:767-818 一致）。

### 2) 可直接落进规则文字的修改建议

1. （条件②）canonical+`r` 段补上面那句"双包装点 + `detail.reason.kind` 读法"原句。
2. （条件①）同源括注补"确定性拒篡改"半边（见 (a) 条件①原句）。
3. **移除类 CX 内容的丢失边界**（新增，建议落字）：**"坐标/atomLabel/atomProp/SgD(DAT) 属登记移除类：既不进入身份，也不进入 `representation_fidelity` 分轴 —— 移除是本仓登记决定，不随来源声明升级；若来源在 atomProp/SgD 内承载化学含义，本系统既不保留也不披露丢失。"** 现文只说"非化学 CX 元数据"，未点明"丢弃无保真度披露"这一盲面。
4. （自包含）把 "`a/o/and/or/rad` 立体注解=保留类" 改成**实际 token 语法**：**"`a:`、`o<N>:`、`&<N>:`、`^<N>:`（头 + 冒号 + 整数列表，`!` 可选）为保留注解类；其余任何首头（含 `r`/`Ln`/`c`/`wU`、无冒号旗标块、登记头后的并列未知项）一律拒绝"**。实现只认 `_CX_STEREO_ITEM_HEAD_RE = (a|o\d+|&\d+|\^\d+):`（:266）与 `_CX_REGISTERED_HEAD_RE = ^(?:Sg|SgD|a|o\d+|&\d+|\^\d+)!?:`（:237-238）；`and/or/rad` 是英文组名不是 CX token，`rad` 更易被读成存在 `rad:` 头 —— 是否存在该头 **待执行验证**（需对锁定版本 RDKit 跑一次词法探针）。
5. （测试侧，承 r9 ③ 同类）建议在冻结前把"放行保留类逐例往返无损正控"写成可执行验收（§6 已有，保持原文）。

### 3) "程序上诚实但化学上误导"风险点

- **同源自证**（r8/r9 沿袭，仍在）：重推导与验证共用 `_identity_key`/`build_chemical_state`，锁定版本若与词法守卫假设不一致 ⇒ 同向通过、不互检。**待执行验证**，冻结前置。
- **"unparseable"字面误导**：上层 kind 读起来像"这个分子不合法"，实际常见成因是本仓登记策略选择（拒绝是决定，不是化学事实）。
- **消旋误读叠加**：`canonical+|r|` 被拒（身份规范形层）与 `raw+|r|` 被拒（输入表示层）层级不同，混读会得出"系统判定该样消旋/非对映纯"；建议两处各标一次层级。
- **移除类被读成"已保全"**：见落字 3 —— 丢弃静默且无 fidelity 轴，`as_written` 不覆盖这一维。

---

## 2. 判据二：参与物计量与元素/电荷核算

### 1) 结论：**有条件同意**（主体与实现一致、"数值配平≠结构贡献已核实"未被 r2 改动，**但两处文本需更正/澄清**）

**读码确认一致的部分**：

- 全氢账 + D/T 并 H + 自由基电子不入账：audit.py:1409-1446（`accounting_scope=full_balance_all_hydrogen`、`accounting_notes` 三句机读披露）、:138-140 ✓。
- 系数契约：hypothesis.py:137-176（bool/零/负/非有限/known+null/unknown+数值全拒，kind 结构化）✓；`coefficient_status ∈ {known, unknown}` ✓。
- 未知系数 ⇒ 两轴 honest unknown：元素/电荷检查被 `full_known` 门挡住（audit.py:628-651，未跑就不猜数）；覆盖轴 `product_coverage=unknown_coefficients`（:889-897）✓。
- 电荷轴前提：states 在 audit 入口先 `validate_state_object`（:474-475），`formal_charge` 与重推导一致才过（chemstate:854-857）；且 `formal_charge` fidelity 非 as_written ⇒ `original_charge_unavailable` unknown（audit:658-669）✓ —— "2b 后不可被直传对象伪造"属实。
- `omission_pattern_matches` 结构化 + "仅数值相符、不证明缺项原因、不含电子/质子计量"（:1441-1446）✓。
- R5d 触发集合 `{element_accounting, formal_charge_accounting}`（:227-228），其他 violated 走 R5v（:1779-1786）✓。
- **恒等 ≠ 落点：确认口径未被 r2 改动且实现支撑** —— r2 只改 `search.py`/`profile.py`（grep `S3a 回修 r2` 仅命中这两文件；chemstate 仍是 v8、audit 仍是 v8、path_context v7、store v9）；且恒等变换因实际净变化为空 ⇒ `no_executed_change` ⇒ center 永不 True（audit:2634-2639），`transformation_center` 是必需检查（:217-224）⇒ 到不了 R6；补全两根据只解除覆盖轴（:970-1005）✓。

**需更正/澄清的两处**：

- **问题①（术语零命中）**：`known_absent 三方语义 (registered_missing/documented_absent/unrecorded)` —— 这三个标签在 `src/`、`docs/` **零命中**（只出现在本请求）。实现里的 known_absent 三消费语义是 `required_entity_known_absent` / `required_value_known_absent` / `other_value_known_absent_not_determining`（path_context.py:732/:828/:833），外加"未列出 ≠ known_absent ⇒ unknown"（tests/test_ppv1_s2.py:379）。**结论：有条件同意 —— 或改用实现理由码，或明写"此三者为规则层分类，不对应现有理由码"**，否则读者会去代码里找不存在的枚举。
- **问题②（该句未找到实现对应）**："声明系数与结构重推导的可确定不一致按契约拒绝（表示层违约，判据三 R2b）"。我读到的系数×结构可确定比较只有**覆盖绑定** `coefficient_binding_mismatch`（audit:928-933）⇒ `partial` ⇒ **retain_conditional，不 reject**（tests/test_ppv1_r2_chem.py 多处断言 partial/unknown）；提交边界的系数相关拒绝是内容指纹/身份重推导（store.py:666、:696），属 `Ppv1SubmitContractError`，且 R2b 是**调用方报告行**（`contract_violation` 参数，audit:1664-1667 "不传则 R2b 不可达"），二者之间没有自动映射。**结论：本条有条件同意 —— 请指明确切判定点，或改写为下面落字 1 的两分句。**

### 2) 可直接落进规则文字的修改建议

1. 把问题②拆成两句（与实现对齐）：**"(i) 系数表示层违约（零/负/非有限/known-null/unknown+数值）在构造与提交边界结构化拒绝，经调用方映射为 R2b；(ii) 声明系数与覆盖绑定重推导不一致（`coefficient_binding_mismatch`）是覆盖轴违例 ⇒ `partial` ⇒ retain_conditional，不是拒绝、不是化学否定。"**
2. 问题①改为：**"known_absent 的三种消费语义分开：实体自身缺席 ⇒ conflict；同值 known_absent ⇒ conflict；异值 known_absent ⇒ unknown；未列出 ⇒ unknown（不按 known_absent 处理）。"**（或标注为规则层分类。）
3. 补回 chemstate 既有不变量（判据二现文没有）：**"形式电荷是结构事实，不表示任何 pH 下的质子化/物种分布；电荷账核的是声明结构的数值闭合。"**
4. 补 CN-only 半句：**"结构不可得（CN-only）的参与物 ⇒ 元素/电荷账 unknown，不得读成'无电荷/无元素差异'。"**

### 3) "程序上诚实但化学上误导"风险点

- **D/T 盲区**（披露在，务必原样保留）：同位素示踪下"账平"≠ 氘守恒。
- **自由基电子双闭合**：中性自由基对在元素轴与电荷轴同时闭合，而氧化态/自旋不守恒 —— 这是"程序 verified、化学错"最典型的形状。
- **`omission_pattern_matches` 被读成"已确认补了水/质子"**：只有数值相符；规则文本勿用因果口吻转述。
- **电荷账被读成溶液形态守恒**：见落字 3；`formal_charge` 不随 pH/离子强度变化，只随声明结构。

---

## 3. 判据三：admission 决策表与中心证据契约

### 1) 结论

**(a) v10 精度更正四点 —— 同意（四点均准确反映实现语义），附两处归因/措辞更正**

- (a) 实际枚举 `partial_unchecked_transformation`（audit:1004），无裸 `partial` ✓；
- (b) `coverage_violations` 三类 kind 相互独立：`coefficient_binding_mismatch`（:928-933）、`completion_surplus/deficit`（:954-968）、`completion_license_unregistered_identity`（:991-999）—— 前两类与许可登记无关 ✓；系数绑定违例在**无未覆盖参与物**时同样可独立触发 partial（:922-933 在 :970 分支之外）✓，故"不能一律称许可本身判负"正确；
- (c) `unknown_coefficients` 早退（:889-997 之前返回）发生在许可分支（:970-999）之前，未用许可 ✓；
- (d) 只有 `completion_license_unregistered_identity` 直接挂"数值配平不证明未登记多原子共底物初始图的结构贡献"（:996-999 的 `note` 与规则正文一致）✓。

**归因更正（非阻塞但请改）**：v10 写"mimo 曾概括'partial = 许可本身判负'"。r9 原文是 **"`uncovered 非空且 product_coverage==partial` 表示补全规则被调用且判负"**（response_r9.md:81、条件汇总 :182 写作"partial=用且判负"）。r9 的说法确有 (b)(c) 指出的不精确处，但**不是"许可本身判负"**。建议按原文引用再更正（"r9 ⑥ 原话为'补全规则被调用且判负'，其不精确处在于……"），避免把前一轮评审的措辞改写得更错 —— 评审链上的转述也应可核。

**(b) v9 scope 归属 + 恒入≠已适用 —— 属实，附一处措辞限定**

- scope 归属：`completion_license_scope` 字面（audit:1010-1013）确实**不含**"不区分键断裂方式与电子去向"；该语义在**许可定义/规则正文**（许可定义注释块 audit:260-271，"补全规则不区分 ⇒ 不得据此授 full/R6"）与本请求规则正文 ✓。字段未改、无身份影响 ✓。**本项确认后不再列入后续请求**（同意）。
- 恒入≠已适用：`completion_license`/`_scope`/`unlicensed_uncovered_identities` 在 detail（:1009-1015）与 `uncovered_*_refs` 在 `base_coverage_detail`（:883-887）✓；三条件组合可推导"依据含许可补全" ✓；第三条件在实现下被前两条蕴含（unlicensed 非空必追加 violation ⇒ 必 partial，:991-999 → :1027），保留作渲染直检无害 ✓。
  **措辞限定（需改）**："**恒入** center detail" 不严格成立：`unknown_coefficients` 早退分支只回 `base_coverage_detail + product_coverage + coverage_rule`（:891-897），**不带这两字段**；三个 `unverifiable` 分支（:831/:837/:950）同样不带。建议改：**"在覆盖判定完成的分支（full/partial）恒入；`unknown_coefficients` 早退与 unverifiable 分支不带该两字段 —— 与 (c) 早退未用许可一致。"** 这样三条件判据的真值表才闭合（读到字段缺失时的解释方向也正确）。

**(c) 决策表与覆盖核算展开 —— 同意与实现一致，附一条必改**

- 决策表 13 行与 `AdmissionPolicy.rules`（audit:1555-1571）及 `decide_admission` 评估顺序（:1672-1818）**逐行一致**：R1→R1b→R2→R2p（on 双分支/`off` 仅披露）→R2b→R3→R4→R5d→R5v→R5c→R5→R6→R7；R5d 集合 :227-228；R6 需 `audit.checks` 非空、全 verified/语义 NA、无覆盖缺口（:1805-1813）；R7 落底（:1815-1818）；"任何 unknown 不自动 reject；新增诊断转拒绝必须扩表升版本""chemical_reproposal 首版 off" 均在 docstring（:1547-1553）✓。覆盖核算文本与 `_center_evidence_binding`（:797-1036）一致 ✓。
- **必改（与实现不符）**："跨假设复用 proof ⇒ 拒"。实现是：绑定不匹配（底物/产物身份对不上被审参与物）⇒ `transformation_center = UNKNOWN`（audit:1131-1148，reason `center_evidence_binding_mismatch:*`）⇒ admission 走 **R5 retain_conditional**；测试 `test_r4_01_cross_reaction_evidence_reuse_rejected`（tests/test_ppv1_r2_chem.py:412-434）断言的正是 `CHECK_UNKNOWN` + `R5`，函数名里的 "rejected" 指"拒绝授信"而非 disposition=reject。真正会抛异常（⇒ 无处置行）的只有两类：类型违约 `center_evidence_type_violation`（:1076）与自报≠复算 `center_evidence_integrity_mismatch`（:1110）。
- 同一句里的 "proof_record 载荷不可变 + 入口身份复算（改前提不换 ID ⇒ 拒）" 把两种机制并列：`proof_record` 本身没有 ID（其"不可变"靠自报 vs 复算比对 + `proof_record_hash` 进 input_hash :1388），"改前提不换 ID ⇒ 拒"指的是 **hypothesis_id 内容复算**（store.py:677-701）。建议拆开写。

### 2) 可直接落进规则文字的修改建议

1. （必改）**"跨假设复用/证据未绑定本假设 ⇒ 中心 unknown（`center_evidence_binding_mismatch:*`），admission 走 R5 retain，不 reject；自报字段与复算不一致 ⇒ 结构化异常（`center_evidence_integrity_mismatch`/`type_violation`），本次无处置行。篡改 = 异常，复用 = unknown，两者不可混写为'拒'。"**
2. （必改）恒入句按 (b) 限定改为"覆盖判定完成分支恒入；早退分支不带"。
3. **R2b 标注**：**"R2b 为调用方报告行：构造期契约异常须由调用方映射传入（不传则 R2b 不可达）；表中'酶计入净计量'等为例示类别，当前无自动检测器 —— 未被报告的酶混入会以普通参与物进入元素/电荷账（见判据二）。"**
4. **补 scope 语义（防 R6 被读成模板已核）**：**"当前注册 checker scope 仅 `region_net_change`（`full_template` 预留未注册）；R6 的 transformation_center verified 只表示：实际净变化限于对齐中心区域（或其联合对称像）+ 声明–执行对账通过 + strict 产物一致 + 覆盖两根据成立 —— 不表示供体侧变换模板或机理已核验。"**（依据 audit:239-248 "full_template 预留 S3 独立注册"。）
5. （承 r9 ⑤确认）"本许可不区分该参与物的键断裂方式与电子去向；这是许可定义的语义边界，非代码 `completion_license_scope` 字面内容。" —— 已在本请求正文出现，**确认落入冻结正文即闭合**（优先于改代码注释，零身份影响）。
6. （承 r9，可选）"两根据"句后补：**"两根据均以参与物系数已知且系数绑定无违例为前提；二者只解除覆盖轴，不解除元素/电荷轴与 transformation_center 轴。"**
7. 归因句改为按 r9 原文引用后更正（见 (a)）。

### 3) "程序上诚实但化学上误导"风险点

- **`partial_unchecked_transformation` 被读成"观察到副反应/额外转化发生"**：实际含义只是"覆盖/绑定轴未能证明被审转化的贡献绑定"（可能仅因一个系数绑定不符、并无任何未覆盖参与物）。建议在枚举定义处点名这一层（落字 1 的延伸）。
- **`full` 被读成"含 H2 活化在内的全部结构步骤已核实"**（r9 R7-5 沿袭未变）：`license_applied`/同屏 scope 落地前，scope 字段是唯一防线 —— 请保持 (b) 的"字段存在 ≠ 已使用"边界与落字 4。
- **R5d retain 被读成"该反应很可能不存在"**：账不平只证明声明内部矛盾；表内已写"绝不进入 R6"，保持。
- **R2b 被读成自动检测**（见落字 3）：否则酶/催化剂若被误列为净计量参与物，元素账会带着一个大分子算出"平衡或不平衡"，两者都不含酶学意义。

---

## 4. 判据四：条件相容聚合

### 1) 结论：**有条件同意**（分写/口径/双向对应与实现一致；**一处方向与处置需更正**；一处"已实现范围"需限定）

**读码确认一致**：

- 两种不可变机制分写 ✓：`ConditionFact`/`Requirement` `@dataclass(frozen=True)`（path_context.py:333/:438）+ 嵌套构造期冻结；`PathContext` 本体 `@dataclass` **非 frozen**（:1942-1943），兜底靠 `validate_context_object` 的同源内容身份重算（:1536-1548，`context_content_identity_mismatch`）与 `from_dict` 同款（:2089）。
- 快照双向对应 ✓：`covered_requirement_signatures` ⊆ 当前累积要求签名（:1470-1478）且 **集合 == per_requirement 各行 `requirement_signature` 集合**（:1487-1499），删行/删签名/凭空签名均拒 ✓。
- 派生先验 validate ✓（:2327-2332）；audit 直接对象 validate ✓（audit:455-458）。
- 单向矛盾（摘要不得洗绿已记录冲突、compatible 须由必要行支撑，:1455-1467）；三分；空要求/无 fits ⇒ UNKNOWN（:1277-1278）；`REQUESTED_SCOPE` 与 `ASSESSED_SCOPE` 分离（:198/:203）✓。

**判据四（接续，从"文献观察环境不构造当前事实"那条之后开始）**

- （清单收尾）文献观察口径的实现对应：`REQUESTED_SCOPE`/`ASSESSED_SCOPE` 分离（`path_context.py:198`/`:203`）+ 文献观察只进请求作用域、不进当前事实集（`path_context.py:211`/`:755`）；`transformation_class` 标签在 src 内**零命中**（不参与条件评估，仅作元数据），与 v10"不能构造当前条件事实"一致。
- 空要求/空覆盖不自动 compatible：`path_context.py:1277-1278`（`not fits ⇒ UNKNOWN`，注释"空要求列表不自动相容"）、`route_assessment` 空阶段不贡献未知也不产生相容声明（`path_context.py:2116`、`:2120-2126`）——与 v10 第 289-290 行一致。
- 双向签名对应与单向矛盾：`covered_requirement_signatures`↔`per_requirement` 行集合**双向**同源（`path_context.py:1470-1499`，`signature_not_in_requirements` 与 `signature_row_correspondence` 双向拒）；`environment_fit` 单向矛盾判定不误拒合法历史（`path_context.py:1455-1467`、`:1468-1469`）——与 v10 第 274-276、284-286 行一致。
- frozen vs 非 frozen 分写：`Requirement`/`ConditionFact` frozen+嵌套冻结，`PathContext` 本体非 frozen、靠内容身份同源重算兜底（`path_context.py:1540-1548` 直接对象、`:2079-2091` from_dict）——与 v10 第 277-283 行一致。

**结论：判据四大方向与实现一致，但有三处必须更正/补全才可冻结。**

**更正④（必改）：孤儿引用的定义与处置方向都反了。**
v10 第 286 行写"孤儿引用（评估行无对应要求）按 unknown 处理不崩溃"。实现是两个相反的方向：

1. 实现里的**孤儿**是"必要要求绑定旧作用域但无快照**按签名**承载"⇒ 显式 **UNKNOWN**（fail-closed，不崩溃）：`path_context.py:1245-1268`（`orphan_rows`、`route_edge_source="orphan_binding"`），计入 `fit=UNKNOWN`（`path_context.py:1277-1278`、`:1296`）。
2. 反方向——**评估行/签名无对应要求**（签名不在累积要求集合、或签名与行集合不等）⇒ **硬拒**，抛 `ConditionContractError(kind=context_snapshot_inconsistent)`：`path_context.py:1471-1478`（`signature_not_in_requirements`）、`:1489-1499`（`signature_row_correspondence`，删行留签名或删签名留行都拒）。

即：v10 把"硬拒"写成了"按 unknown 处理"，且把孤儿的方向指反。**落字建议改为**："孤儿必要要求（要求无快照按签名承载）⇒ 显式 unknown 不崩溃；评估行/签名无对应要求 ⇒ `context_snapshot_inconsistent` 结构化拒绝（fail-closed，不消费），二者方向相反，不得混写。"

**更正⑤（必改）：'任何…入口消费前必须先 validate'需限定为已强制的入口。**
实现中 validate 已闭合的是三类入口：恢复 `from_dict` 同款版本门+身份重算（`path_context.py:2061-2091`）、派生先 validate 父对象（`path_context.py:2321-2327`）、审核入口 `audit_hypothesis` 对直接对象 validate（`audit.py:455-458`）。但三个**纯评估函数本身不自验**：`assess_conditions`（`path_context.py:1117`）、`assess_candidate_conditions`（`:1172`）、`route_assessment`（`:2112`）直接读字段、体内无 `validate_context_object` 调用；其安全性依赖调用方已在上游 validate（当前唯一生产链 audit 先验后评）。**落字建议改为**："恢复/派生/审核入口已由代码强制 validate；评估纯函数自身不自验，依赖调用纪律——绕过上游 validate 直读字段属违约（该纪律的强制性待执行验证：构造未 validate 的篡改对象直调 `assess_candidate_conditions`，应由上游 audit 路径拒，标**待执行验证**）。"

**补全 r9⑦（落字缺失）：v10 只写了兜底的半边。**
v10 第 280-281 行只有"就地改语义字段保留原 `context_id` ⇒ 拒"；r9 条件⑦（`docs/mimo_ppv1_chem_review_response_r9.md:107`、`:182`）要求补的**重建半边**未见落字——"内容身份可重算，兜底只能拒'改了内容还用旧 ID'，不能拒'改了内容后重算新 ID'；因此因内容变化而重建的 context 必须产生新 `context_id` 并保留 `parent_context_ref` 链，禁止改语义字段后重算 ID 复用旧引用"。实现侧派生确实产出新 ID（`path_context.py:2403` 初始化空、`:2417-2418` 以 parent 链重算），代码支持该句落字。

**可直接落进规则文字的修改建议（汇总）：**

1. 按更正④改写孤儿句（方向与处置都要改）。
2. 按更正⑤把"任何入口"限定为"恢复/派生/审核入口（代码强制）+ 评估函数（纪律约束）"。
3. 补 r9⑦ 重建半句（新 `context_id` + parent 链 + 禁复用旧引用）。
4. 可选补一句边界语义："快照通过一致性校验只证明**记录同源**，不认证记录事实为真"——代码注释原话如此（`path_context.py:1391-1392`"不拿当前事实重评旧边，也不认证用户事实真实性"）。

**风险点（程序上诚实但化学上误导）：**

1. **历史 compatible 快照 ≠ 当前已证实**：`route_assessment` 合取的是冻结记录值（`path_context.py:2113-2115`），旧边 compatible 只说明当时记录如此；若产物把路线级 compatible 汇总为"全程条件已核验通过"，会把结构同源校验误读成事实认证。
2. **兜底依赖调用纪律**：`PathContext` 非 frozen，绕过 audit 入口直调评估函数可读到未验字段——这在代码上是"违约但可能可执行"的状态，与"无静默 catch"条款同性质，须以**待执行验证**的绕过探针确认实际行为，不能凭读码断言必拒。
3. **合取的空档**：空阶段不贡献未知（`path_context.py:2120-2126`）是诚实设计，但"全空"路线会直接返回 live 结果；若消费端把"无 conflict/unknown 进入合取"读成"已相容"，与 v10"空要求不自动 compatible"冲突——建议在风险句中点名 `route_edge_source="orphan_binding"` 与空阶段两类不得被汇总为正向相容证据。

**判据五（(a) 供体反应相关、(b) S3b 与 8d、(c) 限定语与 CN）**

**(a) 结论：基本一致，含两处落字补强；风险中等偏低。**

读码确认一致：`audit.py:2553-2562` 三个 None 仅跳过供体侧项目（`donor_present`、`donor_element`、`donor_charge` 预设 None/`{}`，无 WARN/CRIT，供体元素电荷**不进**主体账）；`audit.py:2604-2608` converter 元数据只进 `conversion_warnings`，不进供体元素电荷账；`audit.py:1919/:2983-2993` 共享包络在调用供体检查前已得证，供体问题不改写包络结论。`donor_consistency` 分支（`audit.py:2576-2599`）：已给带电荷结构⇒一致性检查（不一致 WARN `donor_structure_charge_conflict` + 诊断 + `== "consistent"` 才计证）；否则 `unknown_charge` 不判罪；缺带电荷结构⇒`missing_donor_structure` WARN+诊断、无证。该分支不改 `element_account`、不进覆盖核算，早退时并入 **R5**（`audit.py:2906`）。

**可直接落字的修改建议：**

1. **补一句 v10 缺失但代码已有的语句（r9⑧ 前半）**："分子级供体反应只作为"存在可行供体转化"的必要条件，**不核验供体反应自身的变换模板**（S3 接线）"——代码注释在 `audit.py:1886`（分析边界，非未决缺口）。建议原文内联，理由是判据五正文未出现此句，读者易把"检查仅及分子级"误读为"已核验供体模板"。
2. **补图等价限定**："匹配只表示**图等价，不表示酶识别或机制等价**"（`audit.py:1887` 注释原文）。v10 判据五缺此句。
3. 补路径句（r9⑧ 后半）：匹配可走三域 `graph_simple_iso/formal_iso/same_cid`，常规为 `same_cid`（charge-normalized 同同位素连接身份），偏离简明路径走容差路径并入 `conversion_warnings`（`audit.py:1866-1884`、`audit.py:1914-1917`）。注意路径不进 `element_account`（`audit.py:1919`）。
4. `legacy_cn_match` 语义落字（r9⑨）：代码把 `donor_result.legacy_cn_match` **直接继承**为 `donor_ligand_context.legacy_cn_match`（`audit.py:2968`、`audit.py:2986`）；`is True` 时只加诊断 `donor_legacy_cn_match`、`donor_ligand_context=None`（`audit.py:1988-1992`）。**仅作旁证，不加覆盖、不加证**（`audit.py:1890`、`audit.py:1898`：legacy 不恢复未被任何较严路径满足的许可）。落字建议加一句：`legacy_cn_match` 源自 `cn_identity`（电荷归一化+立体盲，`src/pathway_v43/domain/identity.py:46`），**is True 可对应对映体或不同质子化形**，任何"已匹配供体"表述不得建立在该字段上。

**风险点（程序上诚实但化学上误导）：**

1. `missing_donor_structure`/`unknown_charge` 均为"无罪推定"（不判罪、不计入正向证据），且属 WARN；若产物把"未出现供体电荷冲突"汇总为"供体电荷已相容"，会把**未检**读成**已验**。v10 已有"缺证据禁止写成已证实"总句，建议在此处点名这两个标签。
2. `unconnected`/`mixed` 的处置落字不在判据五而在判据三覆盖表（mixed 仍要求 `nn_transition_center=connected` 才可能满足 D1 硬门，`audit.py:1723-1739`）。判据五应加一句指向判据三，避免读者以为判据五内部处理连通性（`donor_consistency` 分支对 `unconnected` 无显式分支，仅靠计数不进覆盖兜底）——此句我按读码给出，**"unconnected 供体侧不会造成覆盖误计"的端到端结论待执行验证**（需跑 mixed/unconnected 合成夹具断言 `coverage_diagnostics` 不因供体侧出现 D1 满足）。
3. `center_evidence` 值域只可能是 `region_net_change`（`CENTER_CHECKER_SCOPES = frozenset({"region_net_change"})`，`audit.py:239-248`），代码把其他值抛 `AuditContractError`（`audit.py:1064-1066`）。v10 判据五说"只有该域携带 `center_evidence`"，未提"其他域带值即契约错"；建议补一句与"无静默 catch"条款呼应。

**(b) 结论：对 S3b 与 8d 的表述有条件同意；条件=闭合判据补"正常逃逸回归"一项 + 未闭合状态保持。**

- 静态读码支持 v10：S3b 未接线（`audit_hypothesis` 无生产 caller；v10 自身如此声明）；audit 内未见"转移模板"字段参与判负——供体侧只有反应签名/产物连接身份/电荷类别/中心区域净变化（`audit.py:2430`、`audit.py:1912`、`audit.py:2553-2608`），`donor_consistency` 不验证 donor→intermediate 模板（`audit.py:2576-2599`）；`_walk_conversions` 有 dead-end 早退与步数上限（`audit.py:1842-1852`），上限导致的不完整有显式标签 `conversion_not_exhausted`（`audit.py:1924-1930`）。**"无兜底、不静默放行"需执行验证**（源码侧 `AuditContractError` 10 个抛点、src 无 `except AuditContractError`，静态成立；包覆结论标待执行验证）。
- **8d 条件（与 r9 一致，v10 文字缺半边）**：闭合判据必须写全三件套——"S3b caller + **正常逃逸回归**（宽捕获之外还要有正向路径回归，证明合法 S3b 流在宽捕获下可达 R3）+ 宽捕获负控回归"。v10 现文只写了"宽捕获负控回归"（正常逃逸被"其余合同条款"隐含），建议显式化，防止未来把"任何异常都被拒"误当闭合。
- "未闭合"表述与 r9 一致，同意保持。

**风险点：**

1. 若 S3b 接线时把"图等价匹配"直接当"供体机制已核验"，判据五的分子级必要条件会被抬升为机制结论——v10 需把 `audit.py:1886-1887` 两句限定语内联进规则正文（见 (a) 建议 1、2），而不只留在本轮回应里。
2. `conversion_warnings` 是 WARN 级：步数上限、跨域偏离等都只进 warnings（`audit.py:1924-1930`）；若产物把"无 CRIT"汇总为"路径已穷尽"，是"未检=已验"的另一变体。建议落字："路径不完整（`conversion_not_exhausted`）不得表述为已穷尽验证"。

**(c) 结论：其余限定语与代码一致；但 `legacy_cn_match` 非 `True` 与 `center_evidence=={}` 两处缺测试断言。**

读码确认一致：`conversion_warnings` 是 code+message 列表，R2b 计入仅判 `"conversion_warnings" in evidence_set`（`audit.py:916-921`）——支持 v10"不等于已验"的落字；`legacy_cn_match is None` 不因缺数据判罪（`audit.py:1990` else 分支无判负）；`center_evidence={}` 仅在既有覆盖满足时可支持 R3，不独立授证（`audit.py:1775-1786`、`audit.py:1896-1899`）；无匹配时 CRIT `donor_transition_not_found`（`audit.py:1911-1912`）与 `center_evidence={}`（`audit.py:1920-1922`）且不授证。

**落字/测试建议：**

1. r9⑨ 归因照原话更正（`docs/mimo_ppv1_chem_review_response_r9.md` 第 81/182 行）：原话是"补全规则被调用且判负"（`unsupported_donor_detail`/`donor_profile_resolution_failed`），**不是"许可本身判负"**；v10 建议引原文更正。
2. 测试缺口：`tests/test_ppv1_s2.py:1301-1320`（`test_f11`）断言了 `legacy_cn_match is True ⇒ R1`，但**未**断言 `legacy_cn_match is None ⇒ 不因缺数据判负`、**未**断言 `center_evidence == {}`（无匹配路径）——请补这两处断言（属"同意方向、附执行条件"）。

**风险点：** `conversion_warnings` 进 `evidence_set` 会带出 `"conversion_warnings" ∈ evidence_set` 的机器信号；若消费端把 evidence 集合成员当"正面证据"而非"有该类证据记录（含失败/不完整）"，"不等于已验"的落字会被机器信号抵消。建议在规则文字中明确 evidence 集合的语义是"存在此类证据记录"，非"该检查通过"。

---

**§6 程序证据（逐项；本轮无执行权限，全部执行声明标"待执行验证"）**

| # | 声明 | 读码/静态结论 | 执行状态 |
|---|---|---|---|
| 1 | PPV1 回归 648 绿/0 红 | 主会话声明（报告方），非本会话执行 | **待执行验证**：`python3 -m pytest tests/test_ppv1_*.py -q` |
| 2 | 基线 `9b78f42` detached worktree 同字节复跑 52 红/2 绿、`655c7e8` 2 既有红/79 绿 | 静态可见测试文件存在；同字节结论无法读码证实 | **待执行验证**：worktree + `git diff --quiet` 后同命令 |
| 3 | G01 白名单 1250/8/17 逐 nodeid | 脚本/清单存在于仓内与否本轮未逐一核对 | **待执行验证**：按任务书命令逐 nodeid 跑并留输出 |
| 4 | 锁定 RDKit 2025.03.1 词法取证 + 往返无损正控 | `chemistry/rdkit_adapter.py` 存在；版本与执行结果不可读码证实 | **待执行验证**（并列为冻结前置） |
| 5 | `AuditContractError` 抛点无静默包覆 | 静态：10 个抛点（`search.py`×2、`path_context.py`×2、`profile.py`×1、`store.py`×4、`audit.py`×1）；src/tests/scripts/tools **零** `except AuditContractError` | 扫描式静态验收**本会话已复核**；"未来不被包覆"的仓库级守卫属持续纪律，**待执行验证**（若已有静态验收脚本则照跑） |
| 6 | r2 只改搜索/轮廓消费协议 | 静态：契约版本 `ppv1-search-2`/`ppv1-profile-10`/`ppv1-search-limits-3`/`store-9`（`profile.py:78/:107/:169`）；r2 回归文件头部声明 24 条坏账 | r2 提交范围（diff 仅 `search.py`/`profile.py`）**待执行验证**（需 git） |
| 7 | 24 条占位坏账 + 五组 P1 不得翻绿 | 静态：`tests/test_ppv1_s3a_rework_r2.py:363-408` 参数化为 12 坏账 × 2 入口 = 24 | **待执行验证**：`pytest tests/test_ppv1_s3a_rework_r2.py tests/test_ppv1_r2_chem.py -q` |

**本轮条件汇总（冻结前置，全部为落字/执行条件，不改判冻结权利）：**

1. 判据二更正两处（`known_absent` 命中数为零、"系数与结构不一致⇒R2b"改为反映单测实测的 R2/R4/R5/R6）。
2. 判据三更正两处（跨假设复用 ⇒ UNKNOWN→R5，非"直接拒"；r9② 归因引原文）；补"恒入"两处例外（`unknown_coefficients` 早退、unverifiable 分支不带 completion/scope/license 字段）。
3. 判据四更正/补三处（孤儿引用定义与处置方向、"入口先 validate"限定为恢复/派生/审核入口、r9⑦ "重建必须新 context_id"落字）。
4. 判据五补三句（不核验供体变换模板、图等价限定、`legacy_cn_match` 旁证边界）+ 补两处测试断言。
5. 判据一补：`state_structure_unparseable` 双包装点与 `detail.reason.kind` 读法、r9③ 半边、stereo token 实际语法（`a|o\d+|&\d+|\^\d+:`）、`C2` 内联定义。
6. 8d 闭合判据补"正常逃逸回归"，未闭合状态保持。
7. §6 全部执行声明按上表跑实并留证（尤其 648 绿、RDKit 锁定、24 坏账、五组 P1）。

以上为逐条回应；每条均已给结论、可落字建议与风险点，无总体评价式带过。凡标注"待执行验证"处均未在本轮执行，亦未据未执行内容给出通过结论。
