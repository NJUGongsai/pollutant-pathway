> **通道与 provenance（主会话 ZCode 记录，非 mimo 回应正文）**
>
> - 2026-10-09 凌晨（S5a 回修 r1 轮内第③步自动送审，AGENTS.md「评审-回修自动循环」）：请求 `docs/mimo_ppv1_chem_review_request_r22.md`（自包含、无金标、只规则级+合成例）经 **opencode 免费模型 `opencode/mimo-v2.6-flash-free`** 只读评审；opencode 会话 `ses_ee2ee75adffekv2v7gz7XN4FBr`（标题 "mimo ppv1 v22 chem review"）。与手机 mimo 应用是否同一实例未经证实，采信按本通道口径区分。
> - **通道事件（如实登记）**：首轮运行与两次续跑连续报 `DEPTH_ZERO_SELF_SIGNED_CERT`（免费网关直连路径被自签证书拦截，期间直连 npmmirror 正常）；处置=带代理环境重启 opencode 服务（`http_proxy=127.0.0.1:7890`，会话存 DB 不丢失）后续跑成功，回应完整。三份原始输出（初始断流/续跑 TLS 失败/成功续跑）均归档本证据目录。**教训：该免费网关直连路径夜间会被本机代理栈拦截，遇 DEPTH_ZERO_SELF_SIGNED_CERT 时先带代理重启服务。**
> - 评审为**只读**：执行类断言（1087 绿、40/40 翻转、20 条件案等）一律"〔待执行验证〕"；读码引用带行号。其中 PPV1 1087 passed 已由主会话本机独立复跑证实（2026-10-09 凌晨）；G01 安全隔离 1689/8/17 为交付方隔离证据，留 Codex 复核。
> - **本轮建议 P1 四项（待 Codex 正链互证）**：A1——根配对入口 `_pair_exports_to_samples`（evaluation.py:1582-1611）不消费 `identity_scope`，有限身份参考根的维度差异会落 `not_evaluated_export_missing` 且归因 `native_export_missing`（化学归因失实）；B1——要求侧单位"分类 unknown 族"文字与实现（只披露不降档、单位被丢弃）不一致；B2——"多事实与顺序无关"文字在物种键不成立（`_assess_species_requirement` 取首条、顺序相关；系冻结侧既有实现，属文字↔实现不一致而非冻结冲突，改实现归 teacher/Codex）；C1——`participant_list_status` 未消费（建议 P1/P2 上界）。**未发现实现与 ppv1-criteria-v1 冻结正文冲突的 P1**；r21 两项 P1 判定"收对、没收过头、没收净"。
> - 请求原文：`docs/mimo_ppv1_chem_review_request_r22.md`。运行证据与原始输出：`docs/review_evidence/ppv1_s5a_rework_r1_mimo_2026-10-09/`。
> - 以下为 mimo 回应原文（仅清理终端控制字符，未做任何内容改动）。

---

**通道与执行边界**：本回应只用读取类工具核对仓库源码/文档（根 `/Volumes/CC/Enzyme_Agent/dependingv43`），**无 shell 执行权限、未跑任何脚本/测试**；凡涉及"20 案逐案一致、六 scope 翻转、反例翻转、写边界五案"等程序事实，一律为**〔待执行验证〕**——我只读了测试断言与实现，未见执行输出。引用行号=我实际读到的行；未读到的标"未确认"。未修改任何文件，未访问金标/题面/封存 run。

**一句话结论（先行）**：四个修复面的**方向都对**，r21 我报的两项 P1（面一 scope 未封顶、面三条件规则分歧）**收对了、没收过头**；但**没收净**——我读码发现 2 处"规则文字↔实现互相矛盾"（面二单位、面二"与顺序无关"）与 2 处"同规则的其他消费入口未收口"（面一根配对、面三 `participant_list_status`），建议按 **P1-不得随 proposed 定稿** 处理；另有多项 P2 读数误导。**未发现实现与 ppv1-criteria-v1 冻结正文冲突的 P1**（我逐段读了冻结稿判据一/判据四，见文末证据）。

---

## 面一（S5A-01：identity scope 先消费许可再授严格档）

### 1) 结论：**有条件同意**

条件三条：
- **(a)** 许可消费必须补到**样本配对入口**（见缺陷 A1，建议 P1）；
- **(b)** 旁证子桶在**聚合层**分列（见缺陷 A3）；
- **(c)** 封顶缺口在 `required_node_gaps` 里带 `gap_cause`（见缺陷 A4）。

读码确认实现与请求表述一致的部分：`evaluation.py:646-647` 取 `structure_identity_scope`，`:654-655` `scope_permits_strict = (scope == "strict_structure")`，`:675-701` 严格命中须 `strict_ids` 且许可，封顶走 `cn_only` + `identity_scope_cap`（`:690-701`），`:736-742` `strict_by_node` 只收 `strict_structure` 条目 → 节点→边→聚合逐层成立；schema 侧 `reference_graph.py:307-308` 强制 scope ∈ `IDENTITY_SCOPES`（`:54-55`），故不存在"缺字段静默封顶"的隐患。**没有发现收过头**：正控（全 strict 图两边保持 strict、真实同位素/电荷差只进旁证）我读到测试断言 `tests/test_ppv1_s5a_rework_r1.py:157-191`，属合理口径〔待执行验证〕。

### 2) 可直接落进规则文字的修改建议

1. **许可消费的入口闭合**：把"scope 许可消费"的适用入口写成**穷举清单**——节点匹配、边严格候选、聚合指标、**样本↔导出根配对**、（将来）关键中间体清单，全部同源消费同一 scope；未列入的入口不得按严格身份单独裁决。
2. **封顶因果分层**：`required_node_gaps[].gap_cause ∈ {reference_scope_capped, no_prediction_hit, reference_structure_unparseable}`；`reference_edge_recall` 聚合增加 `strict_unavailable_reference_scope_capped` 计数，与"模型未命中"分开。
3. **旁证分列**：`key_intermediate_recall` 聚合把 `cn_only` 拆成 `cn_only_content_equal_capped` / `cn_only_genuine`（节点级已有 `identity_scope_cap`，聚合级没有）。
4. **升格例外的边界**：明确写"节点 schema 无缺失维度字段 ⇒ `partial` 一律封顶，本版不做维度级升格；将来要例外须先扩 schema 并升 evaluation 版本"。

### 3) 结构性缺陷

- **A1（建议 P1，收得不彻底）：同规则的另一消费入口没收口——根配对。** `_pair_exports_to_samples`（`evaluation.py:1582-1611`）按根状态严格身份相等配对（`:1594-1609`），**完全不读 `root_entity.identity_scope` / 节点 scope**。若参考根是有限身份（`reference_graph.py:245-256` 允许 `strict_structure_identity` 为空 + `identity_scope=cn_only/partial/unknown`，`structure_smiles_raw` 又必填 `:232-233`），而预测根在参考缺的维度（立体/同位素/电荷）上与 raw 派生身份不等 ⇒ 该导出配不上任何样本 → 落 `unmatched_exports`，样本 `scoring_status = not_evaluated_export_missing`（`:1890-1898`），并被记为 "native_export_missing / S4 导出未交付"（`:1893-1895`）。
  **化学含义**：恰恰是 scope 封顶要吸收的那些维度差异，在样本入口变成了"整样本不评 + 归因于交付缺失"。这违反本仓"身份与完整性在首次消费时闭合/实施先列入口再修同一规则"的教训。**严重度按 P1 报，待 Codex 与程序证据互证**；是否真实触发取决于真实根是否带参考缺失维度〔待执行验证：我未构造该夹具〕。
- **A2（收得过紧的方向，轻微）**：`match_reference_nodes:669-674` 用**导出声明字段**直比（预测 `smiles_isomeric` vs 参考重算 `strict_identity_of`；CN 侧用预测声明 `cn_identity` vs 参考重算）。冻结判据一第 4 条写了"`smiles_isomeric` = 身份键同串"（冻结稿 `:105`），所以口径自洽；但评测侧是**信字段**而非重算，且我在 `native_export.py` 关键词核对中**未见** `validate_state_object`/`strict_identity_of` 同源重算（仅 grep 核到，未逐行读全 → **未确认**）。预测侧身份字段缺失/过期 ⇒ 只会落 unmatched/cn_only（不会假严格，方向安全），但会**漏掉本该在旁证桶的条目**。
- **A3（聚合读数）**：封顶旁证与真实 CN 旁证在聚合层同为 `cn_only` 一个数——两者化学含义相反（前者=参考证据不足，后者=预测结构确实不同）。
- **A4（缺口因果）**：`required_node_gaps` 只带 `node_match_status`（`:766-767`），而 `cn_only` 既可能是封顶也可能是真 CN 不等，**从缺口本身读不出原因**；边桶名 `unmatched_required_node_uncovered`（`:845`）字面归因于"没覆盖"。
- **A5（边界例外需落字）**："样本照常评估、条目保留"在参考结构不可解析时**例外**：`evaluation.py:1916-1923` 整样本 `invalid_input`，聚合只收 `scored`（`:1630-1631`）⇒ 该样本整条退出分母。规则文字应写明这个例外，否则读成"有限样本永在分母"。

### 4) "程序上诚实但化学上误导"风险点

- **R-A1**：A1 的状态文案 `native_export_missing`（":1893-1895"）程序上如实（确实没配上），**化学归因上撒谎**（导出交了，是身份许可差异）。
- **R-A2**：面一与面三联动后，封顶节点的边全部落 `unmatched_required_node_uncovered`（测试 `:116-127` 断言 `matched_strict=0`），**聚合严格召回归零**看起来像"模型完全没做"，实际是"参考只给旁证许可"。没有 A3/A4 的分列，这个数字在任何汇报里都会被误读。

### 问 1 逐项

- **①"参考自己声明只够旁证 ⇒ 内容相等也封顶"是否正确许可语义？有无升格例外？**
  **正确，同意。** `structure_identity_scope` 是**证据许可**而非字符串属性：参考来源只证到 CN 级，就不得用严格命中去消费它没证到的维度（与冻结稿 `:42`"旁证不叠加升格"、判据五 `:400` 同向）。
  **例外我建议本版不加**：要做"缺失维度恰是预测侧也不携带"的维度级升格，**节点 schema 目前没有可承载的字段**（`_NODE_FIELDS`，`reference_graph.py:93-98`，无 `missing_structure_dimensions`；该字段只在 root 侧 `:257-265`）。评测器无从知道 `partial` 缺的是哪一维 ⇒ 加例外=凭猜测升格，属**收得不彻底的反向**（该紧不紧）。要做得先扩 schema、走新版本 + teacher 裁定。
- **②封顶后落"必要节点未覆盖"而非 unmatched，分开计数是否仍有误导？**
  **仍有误导（部分分开，聚合未分开）。** 分开方向对：至少把"参考许可有限"与"边根本无候选"分开了。但缺口的因果证据只在**节点条目**里，**边桶与聚合桶读不出原因**（A3/A4）。按建议 2 落字即可闭合；不建议把它改回 `unmatched`（那会把参考侧许可问题算成预测侧未命中，更误导）。
- **③旁证桶要不要再分子桶？**
  **节点级不必**（`identity_scope_cap` 已机读可分），**聚合级必须**（现在合成一个数，见 A3/R-A2）。折中方案：节点级字段保持不动，聚合层加一个并列计数器，避免动桶结构引起契约抖动。

---

## 面二（S5A-02：条件分类沿冻结同源 + 登记映射）

### 1) 结论：**有条件同意；两处规则文字↔实现不一致必须先收口（P1-不得随 proposed 定稿）**

同源闭合本身**读码确认成立**：`evaluation.py:92-110` 直接 import `path_context` 的 `build_requirement`/`build_condition_fact`/`aggregate_environment_fit`/状态与 basis 常量，`:1066-1202` `_classify_condition_requirement_detailed` 全程只经这三个入口裁决，评测侧**不再有第二套字符串首条/区间解析规则**（旧简化分类在本文件中已不见——我按 `classify_condition_requirement:1205-1232` 追到底，返回值全部来自 `_classify_condition_requirement_detailed`）。

但下面两条**规则文字说的和代码做的不一样**，必须二选一收口：

- **B1（P1 级，建议）：要求侧单位——披露说"分类 unknown 族"，代码只披露、不降档，且单位被丢弃。**
  `_map_condition_scope_to_requirement:999-1024` 只 append 披露；`kwargs`（`:961-998`）**从不含 `unit`**，而冻结 `build_requirement` 压根没有 unit 形参（`path_context.py:554-560`，文档 `:563-567`"本构造器不支持 unit 字段"）。结果：
  - 声明 `temperature_C, value=298, unit="K"` 的要求 ⇒ 298 被当**规范单位 °C** 直接参与比较，事实 25 °C ⇒ 点/区间不相交 ⇒ **`essential_conflict`**（`path_context.py:862-877 / 894-900`），而机读披露同时写着"分类 unknown 族"（`evaluation.py:1016-1023` note）——**披露与分类互相打脸**；
  - 反过来，`unit=""` 的温度要求（合成夹具默认就是空串，`tests/test_ppv1_s5a_schema.py:69`）会打出 `requirement_unit_not_declared` 同款 note，而按冻结契约"要求值恒为键规范单位"，**空单位才是常态**、正常评估是对的——错的是 note 文本。
  - **测试不判别**：`tests:545-550` 用 `facts=[]`，分类为 unknown 来自 `no_applicable_fact`（`path_context.py:763-766`），**删掉整段单位逻辑该断言照样绿**；只有披露 kind 是判别的。
  **落字/改码二选一**：(i) 要求侧声明单位非规范/意外 ⇒ 该条分类**实际降为 unknown 族**（并在 20 案里补一条"有事实 + 非规范要求单位"的判别案）；或 (ii) 规则文字改成"要求侧单位仅披露、不参与分类（冻结契约：要求值恒为规范单位，声明单位与值冲突时以值为准并披露 `requirement_unit_declared_ignored`）"。**我不接受现状**（文字承诺 A、行为做 B）。
- **B2（P1 级，建议）：规则文字"多事实保守 unknown、与顺序无关"在物种键不成立。** 非物种键确实保守：`path_context.py:774-779` 同键有任一 `unknown` 事实 ⇒ unknown、多签名冲突 ⇒ unknown（测试 `:397-406` 两序同判，读码一致〔待执行验证〕）。但**物种键走独立分支** `_assess_species_requirement:701-733`：`same[0]` 取首条（`:727`）——`[known_present, unknown]` 按 present 在前 ⇒ **SATISFIED**，unknown 在前 ⇒ UNKNOWN；`[known_absent, unknown]` 按 absent 在前 ⇒ CONFLICT。这是**冻结侧既有实现**（不在本轮四面改动内），但请求把规则写成普适的"与顺序无关"就是**文字与实现不一致**。**收口方式**：规则文字限定为"同键**多条相反（present×absent）**事实两序同判 ⇒ unknown；物种键的 known×unknown 混合按既有实现、顺序相关，已登记为差异（属判据四消费口径，是否改实现归 teacher/Codex）"。**"相反事实两序同判"本身在物种键也成立**（`:723-726`），所以冻结判据四的三分与矛盾条款（冻结稿 `:368-379`）**未被违反**——这不是与冻结判据冲突的 P1。

### 2) 可直接落进规则文字的修改建议

1. 见 B1 的 (i)/(ii) 二选一。
2. 见 B2 的限定句。
3. **点值语义标注**：区间键裸数值/数值串被映射为 `point`（`evaluation.py:980-982`）时，机读加 `point_semantics_assumed_by_mapping`（或按我下面问③的建议降 `unspecified`→unknown，直到 teacher 裁定）。
4. **同键存在不可表示事实 ⇒ 分类降档**：`_build_frozen_facts:1044-1062` 跳过条目后，同键其余事实照常评估；落字"同键存在 `condition_fact_not_representable` 条目 ⇒ 该条目 classification 强制进 unknown 族 + `key_has_unrepresentable_fact`"，并给"不可评估"一个**独立分母口径**（与 `condition_unsupported_key`、`requirement_status_not_representable` 并列，不混入 compatible/无冲突读数）。
5. **preference 旁路的来源条件**：`evaluation.py:1163-1167` 把 preference 复制为 essential 探针 ⇒ preference 无 `source_refs` 时会命中 `necessity_unsourced_not_gating`（`path_context.py:761-762`）⇒ 分到 `condition_unknown` 而非 `preference_unsatisfied`，且 reason 码是"必要性无源"，**挂在 preference 行上属错码**。落字："preference 不满足轴按同源值轴探针读；preference 无 source_refs 时按冻结 preference 语义（永不门禁）单列，不复用 necessity 码"。
6. **枚举包含关系声明**：`oxygen_regime` 关闭集三值（`path_context.py:159`），字符串不等即 conflict（`:881-892`，matrix 除外 `:883-889`）⇒ **要求 aerobic + 事实 facultative ⇒ `essential_conflict`**。冻结稿判据四正文未展开三值包含关系（我 grep `facultative` 在冻结稿 0 命中 → **未确认**是否另有约定）。落字写明该互斥假设，并保留 `value_mismatch` 原码；是否登记"facultative ⊇ aerobic"之类兼容映射属 **teacher 裁定**，评测侧不自行发明。
7. **不可表示键与冻结 `UNASSESSED_DIMENSIONS` 的交叉引用**（`path_context.py:175-179` 含 `redox_regime`，而合成图 `condition_requirements` 就带 `redox_regime`，`tests/test_ppv1_s5a_schema.py:167`）：两者若各自计数会**重复披露同一未评估维度**，建议互相挂引用，分母只算一次。

### 3) 结构性缺陷

- **B1/B2**（见上，规则文字↔实现不一致）。
- **B3（收得过紧的方向）**：裸数值 ⇒ `point` ⇒ 事实值不等即 **conflict**（`path_context.py:862-866`）。冻结侧本有两条更保守的出路：`unspecified`⇒unknown（`:547,857-860`）与 `optimum`⇒永不 conflict（`:847-855`），**映射两条都够不到**（ConditionScope 无 `value_basis` 字段，`reference_graph.py:153-176`）。20 案里点值只测了"相等"（`tests:411-414`），**没有 point-mismatch 案**。
- **B4（收得不彻底）**：不可表示事实被静默跳过（有披露），同键其他事实仍可给出 `compatible`（`tests:531-538` 只覆盖"唯一事实被跳过→unknown"）。
- **B5**：preference 探针旁路（见建议 5）。
- **B6**：枚举互斥/包含（见建议 6）。

### 4) "程序上诚实但化学上误导"风险点

- **R-B1**：披露 `requirement_unit_noncanonical` + 分类 `essential_conflict` 同时出现——披露诚实、结论化学上错（298 K 被当 298 °C）。**这是本面最重的一条。**
- **R-B2**：`point_semantics_assumed` 未标注时，"名义/最适温度 25 °C"与事实 30 °C 会以 `essential_conflict` 进 `environment_conflict_rate`（`:1709-1716`），**把命名习惯读成化学矛盾**。
- **R-B3**：`requirement_status_not_representable` 与 `condition_unsupported_key` 若被读成"无冲突"，会**系统性低估冲突、抬高"相容"观感**——两个桶都必须显式标"不可评估，不进 compatible/无冲突分母"。

### 问 2 逐项

- **①同源闭合是否足以消除"同名 essential_conflict 两义"？**
  **足以消除"分类码两义"，不足以消除"映射层语义偏差"。** 分类码与 reason 码现在同源（`:1184-1202` 直接回传冻结 `row["status"]/row["reason"]`），同名两义确实关掉了。但语义在**映射层**还能进来：单位被丢弃（B1）、点值被发明（B3）、事实 `origin` 缺省补 `user_input`（`evaluation.py:1050`，冻结侧同缺省 `path_context.py:385` → 属**继承**而非新造，但会让"无来源无场景"的事实获得当前场景适用性，`path_context.py:694-696`）。所以映射层自身要有**独立的证明范围登记**，不能靠"同源"一词盖过去。
- **②负要求单列 `not_representable` 是否正确？**
  **正确，同意（有条件）。** 冻结 `Requirement` 无负表示（`path_context.py:439-`、`554-596` 构造器无 status/absence 轴），评测侧不发明"要求 absent"语义、不伪称冻结矛盾——这正是"不借本轮实现发明判据"。**对称语义（要求 absent + 事实 absent ⇒ 相容；+ 同值 present ⇒ 冲突）属 teacher 裁定**，不是评测侧该自行定义的。
  **条件**：该桶必须标 `denominator_treatment: not_evaluable_pending_teacher`，且**不进 compatible / 无冲突读数**；否则"参考声明了负要求"的样本会在冲突轴上表现为干净（R-B3）。
- **③区间键字符串规范为 `{lo,hi}`、单数值为点值——有无"point 写成 range"错配风险？**
  **方向相反且更大：是"名义值/最适值被写成 point"（B3/R-B2）。** 我逐行读了 `_parse_interval_literal:871-895`：只有形如 `lo-hi`（含 `-5-10` 负 lo 处理 `:883-888`）才落 range，多段/带单位/ en-dash/非数值一律返回 `None` → 回落 `_parse_number_literal:898-911` → 不是数则 `VALUE_BASIS_LABEL` → 注册表空（`path_context.py:182`）⇒ unknown（`:840-845`）。**"point→range 的错配我读不到触发路径**（数字不会被解析成区间）**〔待执行验证〕**；真正的风险是裸数值被钉成硬点值门。建议按落字建议 3 处理，或在 teacher 裁定前把区间键裸数值降为 `unspecified`（冻结侧本来就从严 unknown，`path_context.py:547`）。
- **④缺表示能力按 unknown/unsupported 族披露是否足够？**
  **不够（有条件同意）。** 键级与要求值级有独立桶（`condition_unsupported_key:1096-1099`、`requirement_value_not_representable:991-998`、`requirement_status_not_representable:1100-1115`），但**事实级"跳过"没有桶**（`:1044-1062` 只进 `mapping_disclosures`），且跳过后同键仍可能给 `compatible`（B4）。需要：(i) 专门的"不可评估"分母口径；(ii) 同键含不可表示事实 ⇒ 强制 unknown 族；(iii) 三个 not_representable 桶统一挂"不进相容/冲突分母"的机读标记。

---

## 面三（S5A-03：必要参考节点空命中不被 union 吞）

### 1) 结论：**有条件同意**

核心口径读码确认：`evaluation.py:758-772` 逐 `from_node_ids`/`to_node_ids` 节点核许可严格命中，无命中即入 `required_node_gaps`；`:782-783` `if not required_node_gaps and ...` 才进候选循环（**空集不并入 union、不生成候选**）；`:842-845` 落 `unmatched_required_node_uncovered` + `:859` 逐节点披露；节点 ID 唯一（`reference_graph.py:299-304`），故 `node_status_by_id`/`strict_by_node`（`:738-742`）不会被 distinct occurrence 覆盖写。两核心反例 + cn_only 联动变体 + 覆盖失配正控的断言我读到（`tests:237-337`）〔待执行验证〕。**没收过头到"全面拒绝"**：合法 exact/覆盖失配/共同产物披露保持（`:817-835,853-866`）。

条件：**C1（`participant_list_status` 必须消费，建议 P1/P2 上界）、C3（三桶归因必须 edge-specific）、C4（双桶关系必须落字）**。

### 2) 可直接落进规则文字的修改建议

1. **许可语义对称（C1）**：与面一同构——`participant_list_status ∈ {source_complete, declared_complete}` ⇒ 要求事件参与物集合精确相等；`∈ {partial, unknown}` ⇒ 事件**超集**单列 `coverage_superset_reference_list_incomplete`，不计模型侧覆盖失配（或至少机读披露"参考自认清单不完整"）。**现状**：该字段 `reference_graph.py:388-390`（枚举 `:56-58`）**在 evaluation.py 全文 0 命中**（我 grep 核过），判定层完全不消费，边条目只回执 `reference_participant_node_ids`（`:860-862`）。
2. **participants↔from/to 一致性披露（C2，纯披露不新增门）**：节点在 `participants` 中 side=reactant/product 却未列入对应 `from/to_node_ids` ⇒ 机读 `participant_side_inconsistency` + 该边**不得自称 declared_complete 完整**。语义谁是权威仍归 teacher。
3. **三桶归因 edge-specific（C3）**：`known_gaps` 是**图级列表**（`:751`），现写法 `elif edge_id in not_evaluable_edges or known_gaps`（`:846`）意味着**只要图声明过任何 known gap，所有无候选且无必要缺口的边都记 `unmatched_reference_coverage`**；`or deferred_count`（`:848-850`）同理是**运行级信号**下放边级。落字：known_gaps 须带 edge_id（或只留在 `coverage_report`，`coverage_report` 已有 `known_gaps_per_graph:1968-1971`），预算桶只在该边有关联 deferred/blocked 时使用，否则落 `unmatched`。
4. **双桶关系落字（C4）**：`matched_event_ids` 只收 `matched_events`（精确命中，`:1910-1913`）⇒ **只出现在 `coverage_mismatch_events`/`structure_only_events`/未覆盖边上的事件，会同时被记进"参考外未验证边"**（`:1504-1552`，跳过判断在 `:1537`）。面三上线后落未覆盖边的事件更多 → 这个耦合被放大。落字：`outside_reference_*` 明确"仅精确命中事件视为已覆盖参考；覆盖失配/结构域不符/必要缺口事件**双重计入**两轴，读数不得相加"，或给它们单独的 `matched_but_not_strict` 排除集。
5. **"必要"的定义落字**：必要 = "被列进 from/to"，**与 `node_status`（observed/reference_only/unknown）、`edge_status`、`evidence_basis` 无关**（实现里 `:759-772` 只看 from/to 列表）。请显式写出来，避免读者以为 reference_only 节点有更弱的门；是否按证据等级分档归 teacher。
6. **边级多因只报首因**：有 `required_node_gaps` 时候选循环整块跳过 ⇒ 该边若同时 step_scope 不符，`structure_only_events` 恒空（`:782-835`）。落字"边级缺口优先，其他轴在该边不评估"，或单独补一条 scope 只读披露。

### 3) 结构性缺陷

- **C1（收得不彻底，与面一原则不对称）**：面一学会"先消费参考许可再定档"，面三**没有消费 `participant_list_status`**。参考作者自认 `partial/unknown` 的清单，事件多带 H₂O/共产物（`evaluation.py:821-827` superset ⇒ 不 strict）会算到**模型**头上——正是问3①里"参考作者漏画 H₂O"的场景。
- **C2（可钻的表示漏洞，确认存在）**：participants-only 节点不进门禁，测试 `tests:292-315` 还钉住了 `matched_strict`。把必需参与物只写进 `participants` 即绕过核验，且**现在连不一致披露都没有**（边条目只列 participants 的 node_id，不与 from/to 求差）。
- **C3（三桶读数混淆，确认）**：见落字建议 3——图级 `known_gaps` / 运行级 `deferred_count` 下放边级，会把"模型没做到"记成"参考没画全"或"预算没展开"（`not_evaluable_edge_ids` 是 edge-specific，那个是对的）。
- **C4（跨轴双计）**：见落字建议 4。
- **C5（轻微）**：`from_node_ids` 允许为空（`reference_graph.py:369-376` 只强制 to 非空）⇒ `from_states=∅`，候选过滤 `:795-797` 却要求事件 `reactants` 非空，覆盖判定 `:821-827` 要求 `reactants == ∅` 才 exact ⇒ **此类边永远到不了 strict**，恒落 `matched_participant_coverage_partial`。〔待执行验证：未构造该夹具〕若业务上不存在"无反应物侧声明的边"，请在 schema 里禁掉空 `from_node_ids`；否则该桶会被永久占用。
- **C6（范围提示）**：同结构 distinct occurrence（`n-int-occ-a/b` 都是 `CC=O`）在同一侧并列时，集合并（`:773-778`）会**塌缩计量**——事件带 1 个 CC=O 也算 exact。这是预注册里已声明的"不新增角色/系数/计量门"（`preregistration.py:107-116`），**不算新缺陷**，但请在规则文字保留该限定，避免读者把 matched_strict 读成"2 当量也核过了"。

### 4) "程序上诚实但化学上误导"风险点

- **R-C1**：`matched_participant_coverage_partial` 在清单 `partial/unknown` 时= "参考没画全"，却以**模型覆盖失配**的名义进 `reference_edge_recall` 桶（`:1632-1636` 聚合）。
- **R-C2**：C4 的双计——同一事件既在"边未命中"又在"参考外未验证边"，两条轴单独看都诚实，**相加就是模型被双重记过**。
- **R-C3**：C3 的归因——图有 known gap 时，模型真没做的边被记 `unmatched_reference_coverage`，**参考覆盖不足洗白模型失败**（方向与 R-C1 相反，同属读数误导）。

### 问 3 逐项

- **①"每个声明必要节点须严格命中才可完整 strict"是否正确？超集不进 strict 对 declared_complete 是否过严？**
  **对 `source_complete/declared_complete`：正确，同意**——参考自认清单完整，事件多带物就不是"按声明完整命中"，等价于参考声明之外的物种（可能来自别处/别步），不授严格是**保守且自洽**的，与"备选不合并、共同产物不删"（`:863-865`）不冲突。
  **对 `partial/unknown` 清单：过严（C1）**——这正是"参考作者漏画 H₂O"的场景，应按与面一同构的许可语义分档，而不是一律算模型失配。**注意严格档本身不吃亏**：超集仍进 `coverage_mismatch_events` 披露，没被丢弃；吃的是**归属**。
- **②participants-only 不进门禁是否留下可钻漏洞？**
  **是，确认可钻（C2）。** 评测侧能做且不越权的：**不一致披露 + 禁止自称 declared_complete 完整**（落字建议 2）。是否把 participants 升为门禁、或要求 from/to 与 participants 同源校验，属 **schema 表示语义裁定（P2 归 teacher）**，不该由评测器自行堵。
- **③三桶读数是否混淆"模型没做到"与"参考没画全"？**
  **会混淆，根因不是新桶而是归因信号的粒度（C3）。** `unmatched_required_node_uncovered` 的触发是边级、逐节点的，可读；`unmatched_reference_coverage` 用图级 `known_gaps`、`unmatched_budget_unexpanded` 用运行级 `deferred_count/stop_reason`（`:846-850`），**非边特异** ⇒ 两个"参考/预算侧"桶会吸收"模型侧"的未命中。修归因（落字建议 3）后三分才可读；修之前**必须在 metric note 里写明该归因是全局信号**。

---

## 面四（S5A-04：persist 写边界根规则——工程面完整性检查）

### 1) 结论：**同意（含残留登记），无新增化学判据问题**

读码确认单路径：`evaluation.py:2110-2162`——`target = Path(target)`，`root = Path(repo_root).resolve()`、`resolved = target.resolve()` 各一次（`:2122-2123`），`resolved.relative_to(root)` 失败即 `gold_content_outside_declared_root` **先拒、零新文件**（`:2124-2139`），根内再按 `rel == root_path or rel.startswith(root_path + "/")` 核授权（`:2140-2142`，带 `/` 后缀，`dev_gold2` 不会被 `dev_gold` 前缀误收——读码结论），`write_path = resolved`（`:2155`）授权/建目录/写文件三处同一路径，回执 `path = str(write_path)`（`:2160`）；无 `repo_root` ⇒ 含金标一律 `gold_content_root_required`（`:2113-2121`）；非金标走原路径（`:2156-2157`）。

### 2) 可直接落进规则文字的修改建议

1. **授权根集合与 .gitignore 的一致性**：`GOLD_AUTHORIZED_ROOTS`（`:143-147`）是 `.gitignore` 金标隔离目录的**硬编码镜像**，运行时无同步核验 ⇒ 若 .gitignore 改了而镜像没改，会授权到"已不再 ignored"的目录。建议落字："授权根集合由常量镜像 .gitignore；一致性核验（读 .gitignore 或 CI 断言）为放行前必检项"——**不新增 DLP/沙箱**，只是让镜像的维护责任可见。
2. **回执双档语义落字**：金标回执=解析后实际路径（`:2160`），非金标回执=调用方给定串（测试 `tests:723-724` 断言 `== str(plain)`，可为相对路径）——两档别混读。
3. **大小写不敏感文件系统**（APFS 默认）：`resolve()` 不归一大小写 ⇒ 大小写变体的授权路径会 `rel` 不匹配而被**拒**（安全方向，只是过拒）。落一句"过拒属 fail-closed，不算 bug"即可。

### 3) 结构性缺陷（残留，均已在范围声明内或需登记）

- **D1 并发 symlink race**：`resolve()` 与 `mkdir/write_text`（`:2158-2159`）之间不是原子，同机另一进程可在窗口内把最后一环换成指向根外的 symlink。文档 `:2106-2108` 已明示**不做敌意并发 race 防御**——**接受**，但请把"非敌意威胁模型（同机可信进程）"写进规则文字，别让读者以为已闭合到敌意模型。
- **D2 `contains_gold` 由调用方标注**：无内容侧兜底，误标 False ⇒ 按普通写入落任意路径。同样已声明范围外（`:2106-2108`），**接受**，但规则文字应写"金标内容识别是调用方责任，属 S5-27 的授权维度而非内容维度"。
- **D3 授权根镜像漂移**（见落字建议 1）。
- **（非缺陷）相对基准=相对 cwd**：与声明根绑定后，错 cwd 必逃根被拒，方向正确（测试 `tests:615-641`）。

### 4) "程序上诚实但化学上误导"风险点

- **R-D1**（唯一一条）：D2 误标时，回执完全正常（有 path、有 sha256，`:2160-2162`）——**程序完全诚实，金标却落在普通目录**。这是把"完整性"押在调用方如实标注上；请在规则文字把这条责任显式钉在调用方，并考虑在含金标评测入口对 `contains_gold` 做"参考图/金标字段在输出中出现即强制 True"的廉价自检（属**建议**，不要求 DLP）。

### 问 4 逐项

- **相对基准选择**：`relative target ⇒ 相对 cwd 解析`，与 `repo_root` 解析后比对，错 cwd/绝对越界/**任意层 symlink 逃根**都在 `:2124-2139` 一次拒掉——**无泄漏路径**〔待执行验证：仅读码 + 读测试断言 `tests:615-725`，未执行〕。
- **并发 symlink race**：**有残留（D1）**，范围声明已排除，接受并要求落字威胁模型。
- **无 root 一律拒**：**正确**（授权判定必须有可核验根，`:2113-2121`）；这是 fail-closed，不是漏洞。
- **会导致金标泄漏到普通目录的路径**：只剩 D2（误标）与 D3（授权根集合与 .gitignore 漂移，可能授权到"当时已不 ignored"的路径）。两项都不是"绕过解析根规则"，而是**授权定义的维护问题**——建议按落字 1、4 收口。

---

## 对 r21 两项 P1 的收口判定

| r21 P1 | 本轮修复 | 收对？ | 收过头？ | 收净？ |
|---|---|---|---|---|
| 面一 identity scope 未封顶 | 节点→边→聚合封顶 + `identity_scope_cap` | **收对**（`evaluation.py:654-701,736-742`；与冻结稿 `:42`"旁证不叠加升格"同向） | **否**（无升格例外是因节点 schema 无缺失维度字段，`reference_graph.py:93-98`；不是过度收紧） | **否**：根配对入口未消费许可（**A1，建议 P1**）；聚合子桶、gap 因果未分（A3/A4，P2） |
| 面三条件判据分歧（另写简化规则） | 登记映射 + `path_context` 同源裁决 | **收对**（`evaluation.py:92-110,1066-1202` 不再有第二套规则；与冻结判据四 `:368-385` 三分/known_absent/给定事实集一致） | **否**（没有把 unknown 抬成 conflict，也没把 conflict 洗成 compatible；`preference` 永不门禁、`necessity` 无源⇒unknown 都在） | **否**：**B1 单位披露↔分类不一致、B2"与顺序无关"文字与物种键实现不一致（建议 P1-不得随 proposed 定稿）**；B3/B4/B5/B6 P2 |

**与冻结判据冲突检查**：我逐段读了 `docs/POLLUTANT_PATHWAY_CRITERIA_FROZEN_V1_2026-10-08.md` 判据一（`:56-140`）、判据四（`:340-388`）与 §0（`:42`），**未发现四面实现与 ppv1-criteria-v1 正文冲突的 P1**。B1/B2 属 **proposed 规则文字与实现不一致**（不是实现与冻结正文冲突），但按"文字与实现必须同真"的要求，建议同按 P1 处理，不得随 `ppv1-evaluation-2` 定稿。

## 证据与未核事项

- **已读（只读）**：`src/pathway_v43/pollutant/evaluation.py`（全文 1–2162）、`path_context.py`（`:130-189,382-596,630-900,989-1063`）、`reference_graph.py`（`:30-109,150-219,219-248,236-355,356-435`）、`chemstate.py`（`:900-929` + grep）、`profile.py`（`:215-324`）、`preregistration.py`（`:60-139`）、`native_export.py`（grep 关键词）、`tests/test_ppv1_s5a_rework_r1.py`（全文）、`tests/test_ppv1_s5a_schema.py`（`:55-204`）、冻结稿 `POLLUTANT_PATHWAY_CRITERIA_FROZEN_V1_2026-10-08.md`（相关节）。
- **未执行（全部〔待执行验证〕）**：请求所列 20 条件案、六 scope 翻转、两核心反例翻转、五写边界案、1087 绿、G01 隔离口径——**我一行未跑**；`native_export.py` 是否含状态身份同源重算（**未确认**，仅关键词 grep）；C5 空 `from_node_ids` 边、A1 有限身份根配对失败（均未构造夹具）。
- **不作背书**：本回应结论采信到与程序证据互证的程度为止；上述 P1 建议请 Codex 按源码与测试实际执行复核，若我读到的行号/分支与实现不符，以源码为准并更正我本轮读码结论。
