> **通道与 provenance（主会话 ZCode 记录，非 mimo 回应正文）**
>
> - 2026-10-08 晚（S4 回修 r2 轮，按 AGENTS.md「评审-回修自动循环」轮内第③步自动送审）：请求经 **opencode 免费模型 `opencode/mimo-v2.6-flash-free`** 只读评审；opencode 会话 `ses_ee490ebc0ffemt4ZyZQBQZwfJA`（标题 "mimo ppv1 v19 chem review"）。与手机 mimo 应用是否同一实例未经证实，采信按本通道口径区分。
> - 本轮一次运行完整输出（无断流）；opencode 服务运行于干净直连环境。
> - 评审为**只读**：执行类断言一律"待执行验证"；读码引用带行号。其中 PPV1 962 passed 已由主会话本机独立复跑证实（2026-10-08）；G01 安全隔离 1564/8/17 为交付方隔离证据，留 Codex 复核。
> - **本轮 P1 报出（判据五同位素轴，见回应 §一）**：冻结判据声明的同位素变化轴在实现中不存在（_atom_property_diffs 无同位素 diff；audit.py:2711-2726 把该形态错归因为立体表示差异）。mimo 评估为保守方向（不产生假 verified）、不影响本轮 S4 消费契约放行判断；处置（下版实现 vs 登记缺口+理由码中性化）交用户裁定——正链复核请对该发现做互证。
> - 请求原文：`docs/mimo_ppv1_chem_review_request.md`（v19，S4 回修 r2 版，自包含、无金标）。运行证据与原始输出：`docs/review_evidence/ppv1_s4_rework_r2_mimo_2026-10-08/`。
> - 以下为 mimo 回应原文（仅清理终端控制字符，未做任何内容改动）。

---
# mimo 化学评审回应：pollutant_pathway_v1 化学判据 v19（S4 回修 r2，判据已冻结 ppv1-criteria-v1）

## 〇、执行边界声明

- 本轮仅用读取类工具浏览仓库（`src/pathway_v43/pollutant/`、`tests/test_ppv1_*.py`），**无 shell 执行权限**；一切执行类声明（962/1564/1573 绿、父 0dd35d1 红绿分类、41 正控、字节一致、反例翻转、SHA 复核、HEAD 声明）一律标 **待执行验证**，本回应不为其背书，采信以与程序证据互证为限。
- 下列引用行号为本会话实读的**当前工作树**行号；不确定处标「未确认」。
- 未访问 gitignored 金标/题面/封存 run；未修改任何文件。
- **冲突判定：P1 一项**（判据五，见 §一）；**P2 落字十一项**（见 §二）。

---

## 一、P1：实现与冻结判据冲突（按指令明确报出）

**判据五「判定基础 = 实际净变化集」的同位素轴在实现中不存在。**

- 判据文本（冻结 v12/v15 底本）：净变化 = 「键 diff ∪ 电荷/立体/**同位素**变化集」。
- 实读实现：`audit.py:2110-2179 _atom_property_diffs` 只含 formal_charge（2158-2159）、h_count（2160-2161）、立体奇偶（2162-2166）、原子增删（2139-2147），**无同位素 diff 轴**；全 pollutant 目录 grep `GetIsotope` 仅 `chemstate.py:581` 与元素账口径注记（`audit.py:1417-1419`「同位素差异只在身份/同位素轴体现，不入本账」）。
- 加重项：`audit.py:2711-2726` 在「身份不同而图变化集为空」时把原因**固定归因于立体表示差异**（理由码 `net_change_only_in_stereo_representation`，2718-2722）。判据一第 1 条明确身份键保留同位素，故同位素示踪差异（如氘代）会落此分支并被错标为「立体表示差异」。
- 化学方向评估：该缺口方向**保守**（center 记 unknown → 决策表 R5/R5v，不产生假 verified、不进 R6），不构成放行面假阳性；但 (i) 冻结判据声明的能力未实现，(ii) 理由码的化学归因对同位素示踪场景是实质误导。
- **处置建议**：按冻结稿 §8/版本条款交用户裁定——要么下版实现补同位素轴（criteria-v2 或实现侧修订），要么显式登记为「已披露实现缺口」并把 2718-2722 理由码改为不排他表述（「身份差异未由图变化集承载：非四面体/未比较立体轴或同位素等身份轴差异」）。本项**不源自 0i/0f/0g/0h**，不改变本轮对消费契约文字的放行判断。

---

## 二、P2 落字清单（十一项，详细位置见各条）

1. **§6 契约族段落未登记 v19 升级（文档内部矛盾，必修）**：§6 写「本批(v18)升级 … native-export-1→2、profile-16→17」，而 0i 头部与源码为 `profile.py:212 = "ppv1-profile-18"`、`253 = "ppv1-native-export-3"`、`258 = "-policy-3"`、`268 = "ppv1-v3-projection-3"`。须补「本批(v19)：native-export-2→3、native-export-policy-2→3、v3-projection-2→3、profile-17→18」，v18 段改标历史。
2. **0f.8「四摘要」已过期**：实读 `endpoint.py:728-742` 返回 **5 个**摘要（events/search_actions/endpoint_evidence/inherited_dependencies + `route_conditions_digest`:741），0h.1 自 r1 起加入 staleness（923）。0f.8 应补「+ route_conditions_digest」。
3. **0f.2「七类情形」与冻结六值枚举不一致**：`search.py:304-320 STOP_REASON_*` 恰六值；`endpoint.py:9` 自己也写「六原因枚举」，仅 `endpoint.py:22` 散文列 7 项（多「弃权」，无对应常量）。统一计数口径。
4. **0i.1「在读文件之前」时序措辞**：`native_export.py:905` 注释同措辞，但读取流程内该计算是第 9 步（901-910），位于第 6 步逐 artifact 重读（836-860）之后。语义核心「不以文件存在/内容为输入」由 289-291 支撑，时序句应改写。
5. **0i.1「共用同一索引」到 helper 层非单一函数**：写侧 `_artifact_references`（441）、读侧 `_existing_artifact_reference_keys`（194），同源于 `native_result.py:92 artifact_reference_index`（docstring 自述单一来源）。建议注明层级。
6. **0i.2「contract_versions 整组」实为登记 7 键遍历**：`v3_projection.py:720-725` 只遍历 `current_contracts`，**登记源之外多出的未知键不入 problems**。要么改文字（「登记键整组+整块缺失」），要么补实现（多出键 ⇒ 披露拒，才与「未知来源版本不包装成已验证」完全对齐）。
7. **行号漂移**（§6 已总述待重锚，但请求内以「r2/r3 源码为准」呈现，易被当现行行号）：0c-v14.3「窄捕获 runflow.py:955-972」在当前树该行段**无 try/except**，`except AuditContractError` 实在 `runflow.py:1131`；冻结计划 `_persist/_load` 269/282、`_verify_frozen_plan_binding` 314-429、`_DriverSession` 435、`reconcile_followups` 540-598、`_ensure_transition_followup` 617-655（0c-v15.6 写 229-272/274-390/392/500-558/577-615）；0d.8 runner 实测分派 `214-223`（start）/`311-319`（resume），请求写 214-228/305-320；`store.verify_event_attachment_content` 实在 **store.py:2011**（0c-v15.6 写约 1988）。建议各处加「当前树实测」对照或明确标历史。
8. **路径名**：请求反复写 `legacy/export_v3.py`，当前树实为 **`src/pathway_v43/output/export_v3.py`**（glob 全树确认，无 legacy/ 包）。
9. **no_ledger_h07 / no_ledger_resealed_source 无常驻回归**：仅见于 `docs/review_evidence/.../flip_comparison.json:61-70`，`tests/` grep 无同名用例。建议入 tests（否则「保持接受」只由一次性探针证明）。
10. **export_digest_mismatch 无测试断言**：kind 存在（`native_export.py:765/772`），tests/ grep `digest_mismatch` 零命中。0g.4/G02⑥ 建议补一条。
11. **判据三 proof_record 句机制指向不明**：「proof_record 载荷不可变 + 入口身份复算（改前提不换 ID ⇒ 拒）」——实读只确认：类型契约拒（audit.py:1076-1083）、无 proof ⇒ unknown（1084-1102）、自报 vs 复算不一致 ⇒ AuditContractError（1105-1116）、`proof_record_hash` 仅入 audit input_hash（1388，无入口比对）；字面「改前提不换 ID ⇒ 拒」对应的是**假设载荷** `store.py:704-730`。两句勿并成一句（详见判据三条目）。

---

## 三、逐条表态

### 判据一：分子身份

**结论：同意**（含子问 a/b/c）。
(a) v12 落字读码准确：保留头正则 `(a|o\d+|&\d+|\^\d+):` 在 `chemstate.py:266`；分派 426-456；未登记兜底 456→473（`unregistered_cx_class`）；解析失败 690-693/925-928（`unparseable_smiles`）；恢复入口 `from_dict` 630-649 外层 ChemicalStateError、结构类内因 846/896 经 `detail.reason`（849/899）；writer 外层 Ppv1StateContractError（`store.py:498-666`，11 处 raise 全是）。「同源非独立」成立：`validate_state_object` 754-910 经 `build_chemical_state`（840）同一算法重推导。(b) 入口清单在读码范围内闭合（工厂 687、strict 923、判据五四入口 `audit.py:2572-2582`、恢复 648、直接对象 458-475）；**池 preview/冻结执行器内部解析的 C2 划界本轮未复核 = 未确认**。(c) 判据 1–4 文本按自包含展开，无重评意见。

**落字建议**：0c-v13.2 的两组 kind 加「结构类内因子集」限定——同入口另有 `schema_version`（633-637）、`invalid_structure_origin`（786-789）、`raw_identity_mismatch`（901-910）等 kind，**空输入路径（668-671/920-922）无 kind 字段**；若并列 writer 内因，注意字面是 `raw_structure_unparseable`（store.py:655）≠ 恢复入口 `raw_structure_rejected`。

**误导风险**：「登记保留真实 token」易被读成 RDKit/输出侧对这些注解的逐字保留承诺——它只是本仓输入词法守卫的放行边界（文本已有「不构成样品认证」，保持）；三字面别名 and/or/rad 被拒是本仓兜底拒绝，非 RDKit 自身行为（RDKit 实测行为 = **待执行验证**）。

### 判据二：参与物计量与元素/电荷核算

**结论：同意**（含两处 v12 落字）。读码：`coefficient_binding_mismatch` 全仓唯一落点 `audit.py:929` 进 coverage_violations，product_coverage 三值（896/1004-1005），无固定 R 映射（R2b 只认 caller 传参 1748-1755）✓；known_absent 全在 `path_context.py`（数值缺席 819-825 `numeric_absence_semantics_undefined`、同值 826-831 conflict、异值 832-837 unknown），audit.py grep `known_absent` 0 命中 ✓；系数边界 `hypothesis.py:136-173/202-224` + `store.py:669-701` ✓；full_known 不成立 ⇒ 元素账/电荷账直接 unknown（645-651/676-681）✓。

**落字建议**：无必改。

**误导风险**：「全氢账」易被读成质量/电子守恒已核——D/T 合并与自由基电子盲区已声明，保持；下游勿把「元素账 verified」简写为「守恒核过」（0c-v13.3/4 的声明清单限定是实质）。

### 判据三：admission 决策表与中心证据契约

**结论：有条件同意——条件 = 修正 proof_record 一句（P2-11）。**
决策表顺序与动作实读一致：`decide_admission` audit.py:1643-1818，R5d（1769-1777）在 R5v（1779-1786）**之前** ✓，R2b（1748-1755）只认 caller `contract_violation` ✓，R7（1815-1818）收尾 ✓；R2b 在生产链不可达已由 0c-v13.5 如实披露（唯一生产调用 `production.py:409` 未传该参）✓。恒入/早退成立：license 字段 1009-1013 与 full/partial 分支共用，early-return 分支（889-897 等）不携带 ✓；`completion_license_scope` 字面确**不含**「不区分键断裂方式与电子去向」（grep 0 命中）⇒ v9 scope 归属成立 ✓。λ_s×Δ 在 `audit.py:973-980` ✓。

**落字建议**：proof_record 句拆成实际机制：「自报字段与内部复算不一致 ⇒ AuditContractError（1105-1116）；类型违约 ⇒ 1076-1083；无 proof ⇒ unknown 1084-1102；proof_record_hash 入 audit input_hash（1388）」，另起一句「改前提不换 hypothesis_id ⇒ 入口拒（store.py:704-730，假设载荷）」。「R1 是防御行」源码无该字面（规则文本 1514），属定性，可保留但建议标「规则定性」。

**误导风险**：「载荷不可变」读起来像 proof 前提被防篡改；读码只证明「自报 vs 复算一致」检查存在——**前提与自报同步的一致性改写能否被入口拒绝 = 未确认**。勿让下游把 rerun 当密码学完整性证明。

### 判据四：条件相容聚合

**结论：同意。** 孤儿方向两处置实读（`assess_candidate_conditions` 1245-1269 ⇒ unknown；1487-1499 ⇒ `context_snapshot_inconsistent` 拒）✓；两种不可变分写（Requirement/ConditionFact frozen 333/438；PathContext 非 frozen 1942 + 内容身份 2186/2082-2091/1540-1548）✓；强制 validate 入口（648/2327/458-475）与三评估函数自身无 validate（1117/1172/2112）✓；重建半边（`derive_child_context` 2403-2427 新 ID + parent_context_ref）✓。

**落字建议**：无必改。

**误导风险**：「给定事实集相容性」易被读成来源事实已核真——0c-v13.6 已落字，保持原句，下游勿简写为「条件已验证」。

### 判据五：供体一致性诊断

**结论：有条件同意 + P1 报出（同位素轴，见 §一）。**
(a) 8b 表述准确：早退 `audit.py:2553-2562`（三字段 None、center_evidence 默认 `{}`）、四字符串守卫 2572-2592 在早退之后解析之前 ✓、converter `2983-2993` 返回版本/来源元数据 + center_match=None ✓；v12「失败 diagnostic 与下游 audit 各轴分开」如实（缺 proof 进 1084-1102 中心 unknown，其他轴照常评估）。(b) 8d「未闭合但如实披露」可接受：10 个 AuditContractError 抛点全在 audit.py（464/739/1076/1110/1589/1596/1603/1607/2547/2584）、源内无宽捕获 try-body；`runflow.py:1131` 有**窄** except（与 0d.2 口径一致）。(c) v11 落字 + 0c 清单足以防「错误分支名/版本/异常处置当读码事实」——同意。(d) 其余文本与实现一致，**除同位素轴**；另 `verify_event_attachment_content` 实在 store.py:2011-2044，只核版本/投影范围/展开计划（2036-2044），不读 states 行 ⇒「不单独证明 state 身份」成立（0c-v15.6 行号约 1988 属漂移，P2-7）。

**落字建议**：见 §一处置建议；理由码 2718-2722 改不排他表述。

**误导风险**：`net_change_only_in_stereo_representation` 会把同位素示踪差异报告成立体问题——对示踪实验解读是实质误导；`legacy_cn_match` 单 True 非通过依据（已写，保持）。

### 0c-v13：S3a 复审 R4 §8.5 七条 P2 落字

1. **同意**（11 合法正控 + 1 已关闭坏输入拒绝的定性）。数字类声明 = **待执行验证**。误导风险：把拒绝控制计入「合法正控」会高估正控面——文本已更正，保持。
2. **有条件同意**（见判据一落字建议：两组 kind 加「结构类子集」限定；writer raw 内因字面 `raw_structure_unparseable` store.py:655）。风险：枚举被读成「该入口只会抛这些 kind」→ 误判错误处理完备性。
3. **同意**（full_known 628-632；元素账 645-651、电荷账 676-681）。风险：账 unknown 时勿回退成「数值闭合=守恒已核」。
4. **同意**（绑定 922-933 vs 补全 934-980 分写；omission 1441/1454-1462 结构化）。风险：completion 对账被当独立元素守恒证明。
5. **同意**（1664-1667 不传不可达；production.py:409 未传）。风险：R2b 不可达 ≠ 表示契约没人管——实际在构造/提交边界拒（hypothesis 136-173、store 669-701），分写勿合并。
6. **同意**（1117/1172/1147/1205 无 validate；2112 route_assessment 自身无）。风险：相容性 ≠ 真实性（同判据四）。
7. **同意**（audit.py:2974-2981 旧注释实读仍不一致，0c-v15.5 P2 仍开放；复合探针未执行段不报通过——保持）。

### 0c-v14：Codex S3b 复审 §6 精度更正五条

1. **同意**（`strict False ⇒ violated` 实读 audit.py:1188-1203 → R5v；`strict None ⇒ unknown` 1204-1213）。落字：同 0c-v15.5 把 2980-2981 旧注释列冻结前同步。风险：violated 弱读 unknown → R5v 错走 R5（文本已警告）。
2. **同意**（`_completion_violations` 调用实读 973-980）。风险：λ_s×Δ 是数值组成对账，不是键级机理核。
3. **有条件同意**（行号漂移，P2-7：当前树 955-972 无 try、窄捕获在 1131；其余段落 269/282/314-429/435/540-598/617-655）。落字：标「r2/r3 历史行号」并附当前树实测对照。风险：读者按行号锚到错误代码段当证据。
4. **同意**（数字全部 **待执行验证**；「数 test 函数不证明参数化绿 case」「父/当前集合不混计」口径保持）。
5. **同意**（0d.1/0d.2/0d.5/0d.7 落字确在请求文本内，逐条比对无缺）。

### 0c-v15：S3b-r2 复审 §2/§5/§6 精度更正七条

1. **同意**（13 行为红+2 形态红更正；执行分类 = **待执行验证**）。
2. **同意**（abstain 父红更正；待执行验证）。
3. **有条件同意**（HEAD 时点声明 = 待执行验证；行号拆分历史标注保持 + 当前漂移见 P2-7。落字：加当前树实测行号）。
4. **同意**（novel 来源标签 P2 口径：不宣称逐字全链一致、不宣称认证现实来源——与「来源可追溯 ≠ 来源真实」一致）。
5. **同意——实读确认**：`audit.py:2980-2981` 仍写「strict_target_match=False ⇒ 该证据不得构成 verified（至少 unknown，mimo 3.3(3))」，与 1188 violated/R5v 不一致，**P2 仍开放**，冻结前须同步。
6. **同意**（`store.verify_event_attachment_content` 只核版本/投影/计划、不读 states ⇒ 不当 strict state 身份证明，成立；行号 2011 非 1988 = P2-7）。
7. **同意**（数字口径不混计；待执行验证）。

### 0d：S3b 生产链与调度消费契约（八条）

1. **同意**。风险：工具输出是核验轴输入，若被读成产物身份来源即混淆「声明结构/执行结构」——v14 落字已防，保持。
2. **同意**（窄捕获实读 `runflow.py:1131`；三类异常逃逸/零写入 = **待执行验证**）。风险：勿把「AuditContractError 已闭合」外推全部异常（文本已收窄）。
3. **同意**（三 None 与 converter 元数据实读）。风险：None=未评估（已写）。
4. **同意**（violated/R5v 实读 1188）。风险：复杂共底物配平不升级许可（已写，保持）。
5. **同意**（预约行/幂等键机制属搜索层，本轮未逐行复核 = **部分未确认**；行为待执行验证）。风险：持久上限是防循环计数，不是化学空间穷尽证明。
6. **同意**（行号以 0c-v15 漂移注为准）。风险：场景转换只认显式 source_ref——「污水」标签不造条件（已写，保持）。
7. **同意**（默认 0 轮 = 首次格式错误即结构失败停止；scripted 反馈网络 0 = 待执行验证）。风险：格式反馈轮回路不得被当 hypothesis 语义重试（已分写）。
8. **同意**（分流实读 `workflow/runner.py:214-223`/`311-319`；请求 214-228/305-320 近似，建议精确或标区间）。风险：分流是工程隔离，不是独立科学验证。

### 0e：S3b 恢复/调度/协议消费契约（六条）

1. **同意**（`_verify_frozen_plan_binding` 当前树 runflow.py:314-429 存在；锚定三拒因语义属 v15 前轮受审，本轮未重验 = **未确认**；行为待执行验证）。风险：锚定防输入漂移，不抗全库协同改写（已披露，保持）。
2. **同意**（`search.py:1155-1221 isolate_recovered_failure` 实读，claimed→blocked、`recovery_failure:<kind>` 1163/1180，与 1155-1224 吻合）。
3. **同意**（逐对象幂等/一次冻结入荷属行为，待执行验证）。风险：幂等补齐 ≠ 事件内容正确。
4. **同意**（同机 flock 语义已限定，不宣称分布式锁）。风险：不提供跨外部并发改库保证（已写）。
5. **同意**（novel 需完整 reaction_spec + 来源披露；待执行验证）。风险：proposal_context 可追溯 ≠ 现实来源认证（0c-v15.4 已落字）。
6. **同意**（blocked 持久行 + 主因优先级不动）。风险：blocked 对象清单存在 ⇒ 不称 exhausted_search（已写，保持）。

### 0f：S4a endpoint 分账与原生结果底座（十一条）

1. **同意**（四分账枚举实读 `endpoint.py:106-163/869-881`；两表 `store.py:353/360`）。风险：四分账「独立」不等于终点有独立实验证据——全部仍来自来源层直报。
2. **有条件同意（P2-3）**。落字：七类 → 六类冻结停止原因 + 「模型弃权经六值之一表达（映射待执行验证）」，0f.1/0f.2 计数统一。
3. **同意**（11 字段 49-55；direct-only 587-589；声明级充分性 188-197）。风险：字段齐全 = 声明级充分，非观察真实性认证（已写）。
4. **同意**（615-629 阻断 + blocked_reasons）。风险：recorded ≠ 支持（已写）。
5. **同意**（观察/来源双键 203-223；来路不删除 205-206/632）。风险：去重只影响计数，不影响证据质量。
6. **同意**（`co2_aggregated: False`/`co2_run_total: None` 543-546；root_carbon_fate_status 恒由证据定 858-864）。风险：账平→矿化是最常见下游误读（已写，保持）。
7. **同意**（最强已支持声明序与 handoff≠矿化、不推断永久去除/解毒）。风险：supported_terminal… 被读成永久去除（已禁，保持）。
8. **有条件同意（P2-2）**。落字：0f.8 四摘要后补「+ route_conditions_digest（0h.1 起）」。
9. **同意**（graph facts 恰 15 表实读 `native_export.py:397-434`，与 0g.2 名单一致 ✓；确定性/同 digest = **待执行验证**）。风险：同事实同 digest 只证确定性，不证事实被核真。
10. **同意（P2-8 路径名）**。落字：`legacy/export_v3.py` → `src/pathway_v43/output/export_v3.py`。
11. **同意（语义未改变声明）**——本评审判定 0f 属新增消费入口描述，未改判据一–五/0d/0e 正文与硬门；若日后认定改硬门须按其自设条款走 ppv1-criteria-v2，不得静默生效（该兜底句保留）。

### 0g：S4b 正式导出与 v3 有损投影（十二条）

1. **同意**（组成与首消费 kind 实读）。风险：导出不产生新化学判定（已写）。
2. **同意**（15 表核对 ✓）。风险：digest 变化 = 事实变化，不代表事实正确。
3. **同意**（无时间戳/字节一致 = **待执行验证**）。风险：确定性 ≠ 内容正确。
4. **同意**（八 kind 行号 674/682/715/724/765/811/869/898 齐）。落字+补测：export_digest_mismatch 无测试断言（P2-10）。
5. **同意**（写侧 `native_export_conflict` 529、读侧独立权威重算；无签名边界已披露）。风险：见 0i.1 的 payload 声明删除残余边界句。
6. **同意**（lossy 标记/字段形状/逐事件步骤/空答卷，测试待执行验证）。风险：v3 步骤被下游当转化完整性证明——12 轴损失清单是硬披露（实读 `v3_projection.py:125-190`，字段名 `axis`）。
7. **同意**（12 轴名字与 0g.7 名单逐字对上；动态条目 264-270/371-376；unprojectable_summaries 469-509）。落字：「损失清单 kind」→「axis」与代码一致。
8. **同意**。风险：CO₂ 不相加是防聚合误读（已写）。
9. **同意**（双向引用/反向禁止/模块无写入入口 = 测试断言 **待执行验证**）。风险：投影有效 ≠ 原生新鲜（已写）。
10. **同意**（G02 七测与完整链 = **待执行验证**）。风险：测试通过是程序证据，不是化学结论。
11. **同意**（P2-8 路径 + 数字待执行验证 + dev/298 不外推）。
12. **同意（语义未改变声明，限冻结范围）**——同 0f.11 判定。

### 0h：S4 回修 r1 四组消费契约闭合（七条）

1. **同意**（实读：essential/basis 常量 `path_context.py:206/212`；必要条件过滤 `endpoint.py:399-406`；阻断 617-629；`route_condition_assessment` 898-913 含 reason/fact_sources/requirement_signature（构造 1039-1049）；`route_conditions_digest` 入 derived_from 923、入 staleness 741；`route_assessment` 2112）。落字：连带 P2-2（0f.8 四摘要同步）。风险：必要条件是**阻断输入**不是支持输入——「已知满足 ⇒ 可支持」仍完全依赖来源直报，勿读成条件已实验验证。
2. **有条件同意**：内容读码支撑（manifest core 复算 `v3_projection.py:797-800` 及读侧；必要引用 910-929），但 **P2：标题版本号 `-2` 现源码为 `-3`**（profile.py:253/258），建议标「r1 时版本，现 -3」；0h.2(c)「应存在且实际存在的单集合」表述已被 0i.1 取代，建议加注。风险：fail-closed 核验集防文件篡改，不防 DB 行被删（不抗协同改写已披露）。
3. **同意**（实读 `native_result.py:138-150`：空 task_key 不挡 `stable_id("soutc", action_id)` 枚举；坏必要拒 276-289；写/读侧拒 native_export 209-221/836-848）。风险：调度结论全文 ≠ 化学结论（已写「调度结论」）。
4. **同意**（实读：`_verify_native_source_binding` 289-356，329 走 `read_native_export` 完整首消费、349 整对象比对；`_derived_projection_content` 362 双调用 404/652；读取侧内部一致 793-840 + 版本门 791）。风险：同源复算 = 同一函数复用，非独立第三方核对（同源口径已声明）。
5. **同意**（正控/反例复验结论结构）——**全部待执行验证**；连带建议 P2-9（no_ledger 两形态入 tests 常驻）。
6. **同意**。
7. **同意（语义未改变声明）**——本评审意见：必要条件阻断是 endpoint 契约族的阻断输入，不改判据三决策表与判据一–五正文，属 0f/0h 契约族自身版本登记（endpoint-2/endpoint-policy-2），不触发 criteria-v2；0f.1 由「只由证据决定」增写阻断限制已按其条款在版本登记里分写，认可。

### 0i：S4 回修 r2 两组残余闭合（六条，本轮核心）

1. **S4-C02 必要集合不由文件存在决定 — 同意（有条件，3 处落字）。** 实读支撑：`native_export.py:252-291`（docstring 289-291「纯只读 DB/payload，不读 artifact 文件 ⇒ 不存在由文件存在反推必要的回路」）；payload 三类 basis 335-352（含 `payload_audit_production_report_consumed`:340）；写侧守卫 549-595、目录创建 625 在守卫**之后** ⇒ 零新导出目录 ✓；soutc 行闭合 316-330（`stable_id("soutc", action_id)`:320、outcome 类:322、expand 空 task_key 回退:324-326）✓；`production.py:465-468` complete_action → `_report("submitted")` 顺序 ✓；B4 合法不产报告（docstring 269-275 + 测试 `test_c02_b4_recovered_expand_without_report_still_exports`:322）✓；读取侧第 9 步 901-929（kind 923、`omitted_necessary_refs`:925、`necessary_basis`:926-927）✓；新增 11 条回归在 `tests/test_ppv1_s4_rework_r2.py` 可数出（3+1+1+4+1+1）✓（**待执行验证**）。
   **落字**：(i) P2-4「在读文件之前」时序句改写；(ii) P2-5 索引同源层级注明；(iii) **补一句残余边界**：必要性源 = DB 行 + payload 声明，「payload 声明一并删除」的自洽重写不在本门捕获范围，且与 B4 合法缺席不可区分（这是 production_report 行闭合不判的固有代价，建议显式写出）。
   **误导风险（本条最重要）**：「必要集合不由文件存在决定」≠「一切文件删除必被抓」——捕获面取决于权威行与 payload 声明仍在；DB 协同改写已披露范围外，payload 声明级删除请按 (iii) 落字，防止下游把 0i.1 读成全能量化防篡改。
2. **S4-C04 无 ledger 首读核父来源版本 — 同意（有条件，1 处落字）。** 实读：`_verify_native_source_versions` `v3_projection.py:680-756`（schema 705-709、整块缺失 712-718、逐键 720-725、payload 版本 726-732、投影重叠键 733-744、kind `v3_native_source_version_unknown`:752）；调用点 791-792 **先于**绑定比对 793+ 与 adapter 同源复算 652 ✓；`read_native_export` payload 版本门 775-791（kind `export_version_unknown`）✓；登记源 `native_export.py:180-191` ✓；无 ledger 不查 DB（637）✓；历史版本无 adapter ⇒ 拒（691-692/745-756）✓。
   **落字**：P2-6——「contract_versions 整组」如实写「登记键整组（7 键）+ 整块缺失」，并披露「登记源之外的多出键当前不入 problems」（或补实现：多出未知键 ⇒ 披露拒，才与「不把未知来源版本包装成已验证」完全对齐）；另可补「schema/payload 版本由 v3 直引 profile 常量（99-108），同一 profile 源两条 import 路径」。
   **误导风险**：版本门挡的是「登记键值不对」，不挡「多出来的未知契约键」——勿读成整组未知全拒。
3. **C03 soutc 聚合闭合 — 同意**（native_result.py:138-150/276-289；写读双拒实读）。风险：聚合完整性 ≠ 结论正确性。
4. **C04 投影来源绑定 — 同意**（同上实读；同源复算 362 双调用 404/652）。风险：同源复算的独立性限度（同源口径已声明，勿称独立验证）。
5. **正控与反例复验 — 同意（结论结构），全部待执行验证**；连带 P2-9（no_ledger 两形态入 tests）。
6. **边界诚实声明 — 同意**（不改 legacy/production、scripted 网络 0、金标未触、dev/298 不外推；执行类数字待执行验证）。
7. **语义未改变声明 — 同意**：本评审判定 0i 两组均属消费入口核验集闭合，未触碰判据一–五/0d/0e 正文；与源码的唯一冲突（同位素轴）属判据五历史实现缺口、非 0i 引入，按冻结稿版本条款另行处置。

### §6 程序证据与状态

**结论：结构同意，1 项必修（P2-1）**：契约族段落仍标「本批(v18)升级…native-export-1→2、profile-16→17」，与 0i 头部及源码（profile.py:212/253/258/268 = profile-18/-3/-3/-3）矛盾，须补 v19 升级行并把 v18 段改标历史。**全部测试数字、父基线红绿、字节对比、SHA 复核、反例翻转 = 待执行验证**（本回应不引用为已证事实）。0i.4 所引 mimo r18 第 63 条原文不在本请求内 = **未确认**（自包含范围内无法复核）。判据冻结状态、行号待重锚披露、题域不外推声明：同意。

---

## 四、汇总

| 层面 | 结论 |
|---|---|
| 判据一 / 二 / 四 | 同意 |
| 判据三 | 有条件同意（P2-11 proof_record 句指明机制） |
| 判据五 | 有条件同意 + **P1**（同位素轴实现缺口 + 理由码归因，§一） |
| 0c-v13/14/15（19 条） | 同意为主，3 条有条件（行号漂移/结构类子集限定） |
| 0d（8 条）/0e（6 条） | 同意（行为类一律待执行验证；行号以当前树对照为准） |
| 0f（11 条）/0g（12 条）/0h（7 条） | 同意，附 P2-2/3/8/10 与 0h.2 版本号标注 |
| 0i（6 条，本批核心） | 同意（有条件：3 处 + 1 处落字；残余边界句须补） |
| §6 | 必修 P2-1（契约族版本登记与源码矛盾）；数字全待执行验证 |
| 语义未改变声明（0f.11/0g.12/0h.7/0i.6） | 同意其限冻结范围的定性 |

**给主会话的下一步选项**：① 按 §二 P2 清单（至少 P2-1、2、3、6）做文字回修后再送下一轮；② P1 同位素轴交用户按冻结稿版本条款裁定（补实现 vs 登记披露缺口 + 理由码中性化）；③ 执行类数字与反例翻转交 Codex 正链复验互证后，本评审对 0i 的有条件同意方可视为完成互证。
