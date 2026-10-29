> **通道与 provenance（主会话 ZCode 记录，非 mimo 回应正文）**
>
> - 2026-10-08 中午（S4a 批次轮，按 AGENTS.md「评审-回修自动循环」轮内第③步自动送审）：请求经 **opencode 免费模型 `opencode/mimo-v2.6-flash-free`** 只读评审；opencode 会话 `ses_ee6594c39ffeMCtVtFNmD0C7Ih`（标题 "mimo ppv1 v16 chem review"）。与手机 mimo 应用是否同一实例未经证实，采信按本通道口径区分。
> - **运行事件**：本机代理（127.0.0.1:7890）当日死亡，opencode 后台服务（周一启动、环境携带旧代理）所有请求被劫持连接拒绝；主会话杀旧服务并以干净直连环境重启后，续会话完整输出（无断流）。该环境修复对后续 opencode 调用长期生效。
> - 评审为**只读**：模型自述未运行任何测试、执行类声明（C 级）一律标"待执行验证"，读码引用均给出文件行号。其中 PPV1 914 passed 已由主会话本机独立复跑证实（2026-10-08）；G01 安全隔离 1516/8/17 为交付方隔离证据，留 Codex 复核。
> - 请求原文：`docs/mimo_ppv1_chem_review_request.md`（v16，S4a 批次版，自包含、无金标；**判据已冻结为 ppv1-criteria-v1**，本轮含冻结一致性专项）。运行证据与原始输出：`docs/review_evidence/ppv1_s4a_mimo_2026-10-08/`。
> - 以下为 mimo 回应原文（仅清理终端控制字符，未做任何内容改动）。

---
# mimo 化学评审回应:pollutant_pathway_v1 判据 v16(S4a 批次)

## 0. 执行边界与方法(先读)

- **本轮未运行任何 pytest/探针/脚本,没有任何执行结果可报**;shell 仅用于**只读文本与只读 git 查询**(`git log`/`git diff`/`git show`、`grep`/`sed`/`wc`)。凡执行类数字(914/879/35/1525/1516/291、父基线红绿分类、G01、并发与恢复探针)一律标 **待执行验证**。
- 未访问任何金标/题面/封存逐题 run 目录;只读了 `src/pathway_v43/`、`tests/test_ppv1_*.py`、`docs/POLLUTANT_PATHWAY_CRITERIA_FROZEN_V1_2026-10-08.md`。
- **行号口径**:除标 `adf0287(=r3)` 外,均为当前 HEAD 实读。**HEAD 实读 = `fc40605`,其直接父 = `0e345e8`(评审归档/冻结提交)**,`adf0287` 是祖父。
- 分级:**A = 受审文本与实现不符/内部矛盾,须更正**(否则 0f 不建议按现文字定稿);**B = 精度与风险披露建议**;**C = 待执行验证**。
- **P1 判定先行**:我把 0f 十一条与冻结判据(判据一–五、0d/0e)、S4a 实现逐条对照,**未发现"S4a 实现与冻结判据冲突"的 P1**(production/audit/chemstate 等与 `adf0287` 逐字节无差异,见 §6)。0f 属**新增文本**,其 A 级问题是"文本对实现的描述错误",不动冻结判据正文,故不构成对 ppv1-criteria-v1 的 P1;但 **A1/A2/A3/A4/A7 不更正不应随 0f 定稿**。

---

## 1. 判据一:分子身份(v12 文本)

**(a) v12 落字与 2b 三处 v9 落字是否准确、不引入越权认证**
1. **结论:同意(有条件)**。条件:RDKit 2026.03.6 的真实 token 往返(ABS/AND/OR/自由基、三字面别名按 `unregistered_cx_class` 拒)与 RegistrationHash 分歧面属**历史互证 + 需 RDKit 实证**,本轮只读码 → **待执行验证**。读码可核部分:`chemstate.py:63-65/95/413-414/473/498` 的 `unregistered_cx_class` 与 `unparseable_smiles` 分列存在;恢复入口 `from_dict` 在 `chemstate.py:630`,恢复态 kind `state_structure_unparseable`(`chemstate.py:846`,store 侧 `store.py:605`)与 `raw_structure_rejected`(`chemstate.py:896`)实读命中 —— "同入口内因不同 kind、跨入口外层不同类"的两维更正与源码不矛盾。
2. **落字建议**:无强制项。建议在 2b 末补一句边界:"新增消费入口(0f 的 endpoint 派生/原生结果对象)不产生身份或 verified 证据"(0f 侧确不产生,见 0f.8/0f.9)。
3. **风险点**:"同源确定性重推导拒篡改"被读成"身份经外部独立核验"。文本已有"同一算法的复算(不是第二套独立证明)"兜底,**保持原文即可**。

**(b) 入口清单是否闭合、诊断入口 C2 划界**
1. **结论:同意(闭合)**。S4a 新增的两个消费入口实读均在守卫外且不回流身份:`endpoint.py` 只读业务表与 artifact,上下文走 `production.load_context`(`production.py:327-335`,H07 + `PathContext.from_dict` 内容身份);`native_result.py:98-159` 全部是 `SELECT` 行聚合,**不调用工厂、不构造化学对象**。
2. **落字建议**:把"endpoint 派生 / 原生结果对象"写进"不产生身份或 verified 证据、结果不回流"的显式名单(建议落 0f.8/0f.9)。
3. **风险点**:无新增风险;preview `pool_unchanged/diagnostic_only` 划界维持原状即可。

**(c) 判据本身(1–4)无需重评** → **同意**;文本供自包含核对,与冻结稿 §1 同源(冻结稿 §1 实读在 `docs/...FROZEN_V1...md:56` 起)。

---

## 2. 判据二:参与物计量与元素/电荷核算(v12)

1. **结论:同意 v12 两处落字**,读码支持:
 - 系数构造边界拒绝:`hypothesis.py:136-174`(`known_coefficient_null` / `invalid_coefficient_type` bool / `non_finite_coefficient` / `non_positive_coefficient`)+ `hypothesis.py:188-197`(构造即校验)实读;
 - "不可虚称入口在比对系数与结构重推导值":覆盖侧 `coefficient_binding_mismatch` 实读在 `audit.py:929`,与 `completion_surplus/deficit`(用 `lambda_s*delta` 对账,`audit.py:973-979`)分属两条不同账,**分写属实**;
 - known_absent 轴归属:`path_context.py:730-734`(`required_entity_known_absent`)、`826-835`(`required_value_known_absent` / `other_value_known_absent_not_determining`)实读;**数值缺席** `numeric_absence_semantics_undefined` 实读在 `path_context.py:822`(doc `:24`)。
2. **落字建议**:无必改项。可在判据二补半句"未知系数 ⇒ coverage `unknown_coefficients` 之外,元素账与电荷账同样记 unknown"——**该项 0c-v13.3 已落字**(实读 `audit.py:628-647` 元素、`663-680` 电荷,`full_known` 不成立即 unknown,reason `partial_or_unknown_participants_full_balance_unknown`),建议在判据二正文也留一个回指,避免两处只在 0c 侧存在。
3. **风险点**:"数值账平 = 质量/电子守恒已核"的误读面,文本已用自由基电子与 D/T 合并两条盲区封住,**保持**;另一个隐性误读是把 `omission_pattern_matches` 当成"实际缺该物质"(0c-v13.4 已分写,`audit.py:1441-1454` 实读为"缺口向量与常见模式逐元素匹配"的披露),建议在判据二该行尾加"(不证明实际缺该物质)"。

---

## 3. 判据三:admission 决策表与中心证据契约(v12)

**(a) v12 落字(R2b caller 依赖/中心 partial 分开/入口划界)+ v11/v10 是否足以防误读**
1. **结论:同意**。实读 `decide_admission` 全函数(`audit.py:1643` def,R2/R2p 块起 `audit.py:1689`,R5d 触发集常量 `audit.py:117` 与 `:1532`,R5v/R5c/R5/R6/R7 依次至 `:1819`):顺序与首中语义与判据三表格**逐行对应**;R2b 由调用方传 `contract_violation` 才可达(`audit.py:1649` 参数 + `:1741` 一带分支,docstring "不传则 R2b 不可达" `:1664-1667`),`center_checker_scope_unknown` 实读 `audit.py:1067`。
2. **落字建议**:无必改。建议把"per_product_gate_consumption=off 时只披露不阻断(`audit.py:1723` 一带 `R2p_disclosure`)"在决策表 R2p 行加括注 —— 判据三正文只写了 on 的两分支,off 是显式版本化策略,留痕行为已有代码,**补一句可防读者以为 off 模式不存在**。
3. **风险点**:把 `coverage_violations` 枚举当"许可判负"(v10 已四点封)与把附随内容核验当 state 身份证明(入口划界⑤已封),**两处维持**;新风险是读者把 `R5d` 的"账不平不 reject"读成"账不平可放行"—— 表内已写 retain_conditional 且"绝不进入 R6",**足够**。

**(b) v9 scope 归属与恒入≠已适用三条件**
1. **结论:同意(如实)**。属既有落字,本轮未发现相反实现;"三条件组合(product_coverage=full + uncovered 非空 + unlicensed 为空)"是读法约定,与 `audit.py:1350`(`"full" if full_known and not prerequisite_failed` 一带)不冲突。
2. **落字建议**:无;确认后**不再列入后续请求**。
3. **风险点**:`completion_license_scope` 字面不含"不区分键断裂方式与电子去向"句(规则正文承载)—— 读码者若只看字段会以为许可范围更大;**建议在许可定义处保留该句**(已在正文,够)。

**(c) 决策表与覆盖核算展开文本与实现一致**
1. **结论:同意(限于本轮实读范围)**。R1/R1b/R2/R2p(on+off)/R2b/R3/R4/R5d/R5v/R5c/R5/R6/R7 全序实读一致;`lambda_s×Delta` 对账实读 `audit.py:973-979`。**覆盖核算的逐 `coverage_violations` kind 全枚举未逐条复跑** → 那部分 **待执行验证**。
2. **落字建议**:R6 行补"语义 NA 白名单"在表内已有,无需改。
3. **风险点**:"R7 无适用检查保守 retain"被读成"无证据即通过"—— 表内已写"不冒充核实",**保持**。

---

## 4. 判据四:条件相容聚合(v12)

**(a) v11 三处落字 + v12 known_absent 轴归属是否准确、与 v10 差异如实**
1. **结论:同意**。known_absent 轴归属与判据二**同源同锚**(实读 `path_context.py:730-734/822/826-835`),两处表述一致 ✓;孤儿方向两分("旧作用域无快照 ⇒ unknown" vs "行/签名无对应要求 ⇒ `context_snapshot_inconsistent` 拒")、入口强制 vs 需上游纪律、重建半边(新 ID ≠ 篡改)读码与既有落字不矛盾(本轮未逐行重放 `assess_conditions` 的 validate 缺席 → 该细项 **待执行验证/沿用前轮互证**)。
2. **落字建议**:无必改;建议在"入口限定"处把 S4a 也写进去:`endpoint._inherited_unresolved_dependencies` / `_route_conditions_snapshot` **经 `load_context`(含 `from_dict` 内容身份)读取**(`endpoint.py:304/347` 实读),属"已强制 validate 的消费入口"名单的自然延伸,写一句可让名单闭合。
3. **风险点**:"给定事实集相容性 ≠ 事实真实性"(0c-v13.6)若只在 0c 而不在判据四正文,读者可能把 satisfied 读成"事实已核实来源"—— **建议把这句回指进判据四"场景评估口径"段**。

**(b) 其余文本与实现一致**
1. **结论:同意**(r3/r4/S4a 未改条件评估口径;`production.py`/`path_context.py` 本批零差异实读)。
2. **落字建议**:无。
3. **风险点**:矩阵"污水"标签隐式条件 —— 已封,保持。

---

## 5. 判据五:供体一致性诊断(v12)

**(a) 8b 表述与早退边界、v12"诊断与下游 audit 分开"是否如实**
1. **结论:同意(附一处必须补的切分,见落字建议)**。实读 `production.py:399-404`:`execution_ok=False` → 直接 `_report("method_failed", ...)`,`audit_hypothesis` **根本不被调用**;`audit_hypothesis` 调用在 `production.py:406`、`AuditContractError` 原样上抛在 `:405` 注释与 `:409` 决策之前。
2. **落字建议(重要)**:判据五 8b 的"同一次 audit 仍可以给其他轴 verified 并由决策表处置"是 **audit 入口被喂该 diagnostic 时的一般行为**;生产链在工具失败时**不进 audit**。建议补:"(生产链 `production.py:399-404` 在 `execution_ok=False` 时直接 method_failed、不调用 audit;本句描述 audit 入口被消费时的一般行为,不描述生产链实际路径)"。
3. **风险点**:读者可能以为"生产链跑了 audit 并给了部分 verified 轴"——这会**放大** verified 面,属典型"程序诚实、化学误导"。

**(b) 8d"未闭合但如实披露"作为 S3a/r4 边界是否可接受**
1. **结论:有条件同意**。S3a 时点的"未闭合"如实;但 **0d.2 已声明 S3b 交付了该闭合**,且我实读到生产 caller 窄捕获:`runflow.py:1095-1120`(`except AuditContractError` → `OUTCOME_KIND_CONTRACT_ABORTED`,`queue.py:72/356` → attempt failed),`runflow.py` 内**无 `except Exception`**(实读 grep 零命中)。
2. **落字建议**:8d 是冻结正文,不改;**在 0d.2 或 0f 加一句时态澄清**:"判据五 8d 的'尚未闭合'是 S3a 时点快照,S3b 已以 `runflow.py:1109` 窄捕获 + 负控闭合 AuditContractError 义务;ChemicalStateError/HypothesisContractError/ConditionContractError 三类仍原样逃逸(0d.2 已披露)"。
3. **风险点**:反向风险(把 8d 的"未闭合"当成当前状态会过度保守,方向安全);正向风险是把"窄捕获存在"当成"全部契约异常都有失败结算"——0d.2 已收窄,**保持**。

**(c) v11 落字 + 0c 清单是否足以防再次误读**
1. **结论:同意**。0c 的①②⑦⑧条与本轮读码一致(0c-v13.2 的四种 kind 全部实读命中,见判据一 (a));0c-v15.5 的旧注释**当前仍未同步** —— 实读 `audit.py:2980-2982` docstring 仍写"strict_target_match=False ⇒ 该证据不得构成 verified(至少 unknown)",与 0c-v14.1 的 violated/R5v 不一致。
2. **落字建议**:把 0c-v15.5 从"冻结前 P2"改登记为"**冻结后仍开放的代码注释同步项**"(改注释不改行为、不触判据正文),排进下个源码批次。
3. **风险点**:`legacy_cn_match` 单 True 当通过 —— 8b 已封("不是任何 R 行的通过依据"),保持。

**(d) 其余条款与实现一致**
1. **结论:同意(抽核范围)**:strict False → `CHECK_VIOLATED`(`audit.py:1193-1201`)、strict None → `CHECK_UNKNOWN`(`:1202-1211`)实读;非四面体/E-Z 分列、净变化判定、四原始串守卫沿前轮互证,**未重跑** → 待执行验证。
2. **落字建议**:无。
3. **风险点**:无新增。

---

## 6. 0c-v13 七条(逐条)

| # | 结论 | 落字建议 | 风险点 |
|---|---|---|---|
| 1(11+1 父绿) | **同意作为历史标签更正**;本轮未复跑 → 数字本身 **待执行验证** | 写明"1 合法坏输入拒绝控制"已含在 12 内,不与本轮数字混计 | 把历史父绿当本轮证据 |
| 2(各入口 kind 层次) | **同意,实读命中**:`unregistered_cx_class/unparseable_smiles`(`chemstate.py:63-65/473/498`)、`state_structure_unparseable`(`:846`;`store.py:605`)、`raw_structure_rejected`(`:896`) | 无必改 | 把"同入口不同 kind"写成"不同异常类"(0c⑦ 已禁) |
| 3(未知系数 ⇒ 元素/电荷亦 unknown) | **同意,实读** `audit.py:628-647/663-680` | 建议回指进判据二正文(见判据二落字) | "coverage unknown 但元素账 verified"的分裂读法 |
| 4(omission/绑定分写) | **同意,实读** `audit.py:929/973-979/1441-1454` | 无必改 | 两条账互相冒充 |
| 5(R2b/R1 对象范围) | **同意,实读** `audit.py:1649/1664-1667/1741` 一带 | 无必改 | 把契约异常降级成 R2b/R 行 |
| 6(条件事实真实性) | **同意**;"不核事实真实性"是给定集相容语义,与 `path_context` 评估函数一致(本轮抽核) | 建议回指判据四正文 | satisfied 被读成"来源已核" |
| 7(异常不当 R 行) | **同意,实读** `runflow.py:1109-1120` 窄捕获 + `queue.py:345-360` 结算语义 | 无必改 | 复合探针"首拒后未执行段报通过"(文本已禁) |

---

## 7. 0c-v14 五条(逐条)

1. **0d.4 strict False = violated → R5v:同意,实读** `audit.py:1193-1201`。落字建议:无。风险:弱读成 unknown 错走 R5(文本已禁)。
2. **λ_s×Δ 源位置 973-979:同意,实读**(`lambda_s * v` 在 `:975/:979`)。落字建议:无。风险:把局部对账当整条覆盖证明(判据三已封)。
3. **0d.8 行号 runner.py:214-228/305-320:同意,实读命中**(start 分流 `runner.py:212-227`、resume 分流 `:303-321`;runner 本批零改动实读)。落字建议:0c-v14.3 的"r2 源码"行号与 0c-v15.6 的 r3 锚请统一标 HEAD 漂移值(见 0c-v15.6)。风险:拿旧锚当当前行号。
4. **测试数字口径:同意并已执行其纪律** —— 我按"数函数不证明参数化绿"处理:本轮**只读计数** `test_ppv1_s4a_endpoint.py` = **30 个 `def test_` + 唯一参数化 F01 ×6 = 35 个收集用例**(与"35 新"结构自洽),**通过与否待执行验证**。落字建议:无。风险:把收集数当通过数。
5. **0d.1/0d.2/0d.5/0d.7 已落字:同意,请求文本已含**(0d.2 的三类 RuntimeError 逃逸面、0d.7 默认 0 轮后果均在)。落字建议:无。风险:把"AuditContractError 已闭合"外推到全部异常(0d.2 已挡)。

---

## 8. 0c-v15 七条(逐条)

1. **r2 父基线 13 行为红 + 2 形态红 / 52 绿:同意作为历史登记**;本轮未复跑 → **待执行验证**。落字建议:无。风险:把形态红当行为红(文本已分)。
2. **abstain 父红更正:同意(历史)**;`test_ppv1_s3b_model.py` 未读 → 行为细节 **待执行验证**。落字建议:无。风险:函数名当红绿标签(已禁)。
3. **HEAD 采集时序:同意,且本轮实读给出新事实** —— 当前 HEAD=`fc40605`、直接父=`0e345e8`;**`0e345e8` 只改 AGENTS.md/docs(实读 diff:`src/`+`tests/` 命中数 = 0)**,故 src/tests 内容与 `adf0287` 逐字节一致。落字建议:把 §0/§6 的"**直接父 adf0287**"改为"直接父 `0e345e8`(纯 docs 归档/冻结),src/tests 与 `adf0287` 逐字节一致(实读 diff=0)"。风险:基线拓扑说错会让复核者找不到父。
4. **novel 来源标签 P2:同意(不宣称逐字全链一致)**;本轮未读 decide/expand 传参 → **待执行验证**。落字建议:冻结前清误导文字照办。风险:来源标签被读成"已认证现实来源"。
5. **audit.py:2980-2981 旧注释:同意,且实读确认仍未同步**(`audit.py:2980-2982` 仍写"至少 unknown")。落字建议:改登记为"冻结后仍开放的注释同步项"。风险:注释被当规则(与 0c-v14.1 冲突)。
6. **行号拆分:同意,全部实读复核命中** —— `adf0287(=r3)`:`_persist_frozen_plan` **229**、`_verify_frozen_plan_binding` **274**、`reconcile_followups` **500**、`_ensure_transition_followup` **577**、`store.verify_event_attachment_content` **1988**;`_DriverSession` r3 实为 **395**("392 一带"是约数,可接受)。**HEAD(fc40605)漂移值**:247 / 292 / 518 / 595 / `store.py:2011` / `_DriverSession` **413**(本批 runflow +18、store +23 实读)。落字建议:引用处标"r3 锚(adf0287);HEAD 漂移 = +18/+23"。风险:把 r3 锚当当前行号(§6 已声明待重锚 ✓)。
7. **数字口径:同意"各自单列不混计"**;数字本身 **待执行验证**。落字建议:无。风险:把 871/879/914 相加。

---

## 9. 0d 八条(S3b 生产链与调度消费契约)

1. **固定调用链与产品来源** — **结论:同意**。实读:`production.py:396`(AtomTool 执行)→ `:406`(audit,携带 `execution["center_evidence"]`)→ `:409`(decide)→ `:434`(build event);产物身份取冻结池声明结构的口径与 0d.1 v14 文本一致。落字建议:无。风险:把工具执行输出读成"产物身份已由工具证明"(v14 已分:声明结构提交、中心可 unknown)。
2. **生产 caller 异常义务** — **结论:同意(范围已如实收窄)**。实读 `runflow.py:1095-1120` 窄捕获 + `runflow.py` 无 `except Exception`;失败短路 `production.py:399-404`。落字建议:在 0d.2 补"该闭合同时使判据五 8d 的 S3a 时点'未闭合'成为历史状态"(见判据五 (b))。风险:把三类逃逸异常读成"也有失败结算"(0d.2 已挡)。
3. **三个 None 与缺 proof** — **结论:同意,实读** `production.py:399-404/405`。落字建议:补生产链不进 audit 的切分句(判据五 (a) 同款)。风险:见判据五 (a)。
4. **中心证据分段负控** — **结论:同意,实读** strict False→violated(`audit.py:1193-1201`)、None→unknown(`:1202-1211`)、proof 复算不一致走契约异常(`audit.py:1067` 一带 scope unknown 与既有 proof 路径)。落字建议:无。风险:violated 弱读成 unknown 错走 R5(0c-v14.1 已禁)。
5. **队列与两类 deferred** — **结论:同意(抽核)**;持久上限来自预约行 + 幂等键的口径与 S3a 落字一致,本轮未重放上限测试 → **待执行验证**。落字建议:无。风险:"blocked 计数不是防循环证书"(已写,保持)。
6. **条件依赖与场景转换进调度** — **结论:同意**;场景转换 `source_ref` 必需与"不从标签/隐式 O2 造事实"与判据四同源。落字建议:无。风险:把"不阻断共底物循环"读成"化学上必然可行"(文本已写"缺支持标 unresolved_initial_supply,不称化学不可能")。
7. **proposals[] 与有界格式反馈** — **结论:同意**;空池/弃权合法实读(`model_protocol.py:117-118/240`),`reaction_spec` 必需实读(`model_protocol.py:29` 入口契约行)。落字建议:无。风险:格式反馈被读成"化学语义可重试到通过"(已禁)。
8. **PPV1 独立 runner 分流** — **结论:同意,实读命中** `workflow/runner.py:212-227`(start)与 `:303-321`(resume)。落字建议:无。风险:把分流当"legacy 与 PPV1 共享执行语义"(已写不落 legacy CN/PathwayStore)。

---

## 10. 0e 六条(恢复/调度/协议消费契约)

1. **冻结输入身份 + 后段锚定** — **结论:同意**。实读 resume 顺序:`runflow.py:1562`(会话锁)→ `:1567` 读冻结计划 → `:1568-1578`(`frozen_plan_mismatch`)→ `:1585` `_verify_frozen_plan_binding`(def `:292`)→ **`:1586` 才 `recover_run`**,即"首消费前"成立;`_plan_digest = content_hash(整 plan)`(`runflow.py:189-190`),故 `endpoint_evidence` 也随整计划被锚定 ✓。落字建议:无。风险:把 artifact 内自洽 hash 当独立证书(已禁)。
2. **恢复裁定接执行门** — **结论:同意(抽核)**,隔离调用实读 `runflow.py:1591-1599`(`isolate_recovered_failure`)。落字建议:无。风险:隔离被读成"坏任务被重算过"(零猜重算已写)。
3. **后续/转换集合完整性** — **结论:同意(抽核)**,补齐函数实读 `runflow.py:518`(`reconcile_followups`)、`:595`(`_ensure_transition_followup`)。落字建议:无。风险:把"逐对象幂等补齐"当"完整性证书"(已写不以 payload 计数当证书)。
4. **执行会话互斥** — **结论:同意,实读** `_DriverSession` docstring(`runflow.py:413-417`:`flock LOCK_EX|LOCK_NB`)。落字建议:无。风险:同机文件锁被读成分布式 exactly-once(已声明范围外)。
5. **novel 独立假设消费者** — **结论:同意(抽核)**;固定链与池内同一链的表述与 0d.1 一致。落字建议:无。风险:"有足够内容"被读成"化学上充分"(内容完整 ≠ 化学成立)。
6. **blocked 持久披露** — **结论:同意,实读** `search.py:3005-3013`(从持久 blocked 行派生 `depth_limit`)与 `:3037-3041`(exhausted 前提含 blocked/pending 检查)、`unexplored` 构造 `:3044` 起。落字建议:无。风险:blocked 存在时称 exhausted_search —— 实读 `:3037-3041` 显示 blocked>0 时不进 exhausted_search ✓,与 0e.6 一致。

---

## 11. 0f 十一条(S4a 新增,本轮重点)

### 0f.1 四分账
1. **结论:不同意(现文字)** —— **A1**。文本写"stop 独立持久化于 stop_reason_records;**endpoint 记录只按 payload_hash 引用,不复制其语义**";实读 `endpoint.py:755-763`:endpoint 记录**内嵌** `search_stop_reason.primary / other_reasons / unexplored` 副本,`stop_record_payload_hash` 只是交叉引用(`:664-676` 核对)。文本与实现不符。
2. **落字建议**:"endpoint 记录以 `stop_record_payload_hash` 与 stop 行**交叉引用**(引用断裂 ⇒ 结构化拒),并内嵌 `primary/other_reasons/unexplored` **摘要副本**;语义权威在 stop_reason_records 行,副本随整行 `payload_hash` 锁定。"
3. **风险点**:读者以为 endpoint 记录不含停止语义副本 → 下游直接读 endpoint 行时既看不到副本也无从核对来源(反之亦然);四分账"互不代替"的承诺会被"其实复制了"削弱 —— 属"程序诚实、文字误导"。

其余三条枚举实读一致:execution 三值 `endpoint.py:95-101/732-737`、assessment 四值 `:105-121`、bookkeeping 三值 `:145-152`;**A5** 见 0f.2。

### 0f.2 F01 停止非终点
1. **结论:有条件同意** —— **A5(内部矛盾)**:0f.1 写"六原因",0f.2 列"七类情形"。实读枚举为 **6 值**(`search.py:304-320`,未知原因契约拒 `search.py:536-540`);七情形归六枚举:模型弃权/池空 ⇒ `no_local_candidate`(`runflow.py:884` 一带注释:有效候选集为空含模型弃权)、队列耗尽 ⇒ `exhausted_search`。
2. **落字建议**:"七类情形经冻结优先级归入**六值枚举**(search.py STOP_REASON_PRIORITY):模型弃权/池空 ⇒ `no_local_candidate`;队列耗尽 ⇒ `exhausted_search`;枚举与未知原因拒绝以 search 层为准。"
3. **风险点**:读者按七类去实现/断言停止原因 → 与六值枚举契约冲突;或把"模型弃权"当成独立停止原因去映射终点(F01 本身不受影响,方向仍安全)。
- F01 语义本身 **同意**:assessment 派生函数不读 stop_report(`endpoint.py:460-554` 签名与实现),停止不覆盖证据(测试夹具 `test_f01_stop_does_not_overwrite_valid_evidence` 实读,零事件 run + budget_limit 停止仍 supported)。

### 0f.3 终点证据(来源层直报、字段充分性)
1. **结论:同意(附两条披露建议)**。实读:11 字段校验 `endpoint.py:215-264`、claim 必需字段表 `:177-186`、充分性判定与逐字段缺失披露 `:495-511`、只有 direct 且带 source_refs 才入支持 `:484-486`、证据来自冻结计划 `:727`(整计划 digest 覆盖,`runflow.py:189-190`)。
2. **落字建议**:(i) 补**校验时机**——"证据形状契约在**派生/读取时**执行(`endpoint.py:727/678`),start 入口不预检;计划带坏证据 ⇒ 搜索照跑、派生结构化拒、**无 endpoint 记录**(fail-closed,下次 resume 重派生)";(ii) 补"**`necessary_dependencies` 非空只证明声明了必要依赖,不证明其已满足**;满足性由 F02 的上下文依赖账承担,未入上下文账的声明依赖不可核"。
3. **风险点**:"字段齐全 = 已支持矿化"的最强误读面 —— 必须强调 supported_* 是**来源层声明可支持性**,不是本仓核实(建议并入 0f.7,见下)。

### 0f.4 F02 未知依赖不被 recorded 洗白
1. **结论:同意(附范围精化)**。实读 `endpoint.py:298-340`:实现取 **run 内全部 `search_actions.context_ref` 引用上下文中全部 status != supported 的依赖**(按 `dependency_id` 去重),**不分"必要/非必要"、不按 route 过滤**;阻断后 `blocked_reasons` 置 `unresolved_dependencies_inherited`(`:512-513`)、评估保持 unknown(`:519-522`),证据与依赖全保留(`:525/546`)。
2. **落字建议**:"实现口径比'route 上未解决**必要**依赖'更宽 —— 取本 run 已引用上下文的**全部**非 supported 依赖(方向保守:多拦不误放);依赖解决后同证据可支持"。
3. **风险点**:文本写"必要依赖"而实现拦"全部依赖",读者可能以为非必要依赖不会影响评估 → 反向误判(把 unknown 归因错)。方向安全,但归因披露要准。

### 0f.5 F03 去重与独立支持
1. **结论:有条件同意**。实读:观察身份键 = source_refs + basis + claim + **source_support_scope** + 条件 + 窗口 + 检测(`endpoint.py:192-205`)——**文本漏了 `source_support_scope`**;来源身份键 = source_refs(`:208-212`);`independent_source_support_count` **只统计 direct 且带 source_refs 的条目**(`:484-487`)——即 **model_prediction/inferred 对该计数贡献为 0**,不是"按同一来源身份计 1"。
2. **落字建议**:(i) 观察身份字段清单补 `source_support_scope`;(ii) 改写为"模型预测/路径推断条目**不进入**独立支持计数(贡献 0),仅入 `basis_counts` 披露;同一来源身份只在 direct 条目间计"。
3. **风险点**:把 `independent_source_support_count` 读成"已证实的独立证据条数"(它只统计来源直报的 direct 条目,且不做最小来源数门槛 —— 见 0f.7)。

### 0f.6 根碳账(账平不当矿化)
1. **结论:同意(附三处精度补)**。实读:closed/unknown/not_closed 三分 `endpoint.py:427-438`;CO₂ 逐事件列示、`co2_aggregated=False`、`co2_run_total=None` `:446-448`;coverage 是核查范围、`root_carbon_fate_inferred_from_bookkeeping=False` 恒定 `:449-450`;fate 状态只来自证据 `:745-749`。
2. **落字建议**:(i) 补**零事件 ⇒ `bookkeeping=unknown` + coverage=`no_events_no_account`**(`:427-429`);(ii) 补**次序**:引用悬空(not_closed)优先于未知系数(unknown)(`:430-438`);(iii) `source_reported_check_scope_only` 的触发是"**任一 basis 条目**该字段非空"(`:745-747` 不看 basis/claim/充分性),把"直报"改写为"任一来源层条目声明了核查范围(不看 basis)"或改为仅 direct 计入(需改实现,二选一)。
3. **风险点**:(a) 模型预测条目填 `root_carbon_fate_check_scope` 也能置 `source_reported_check_scope_only` —— 该状态字面带 "only" 不等于 verified,但**字段来源比读者预期宽**;(b) "closed_within_declared_scope" 被读成"根碳账已核"—— 文本已用 coverage 语义封,补上零事件与次序后更完整。

### 0f.7 评估取值边界
1. **结论:同意(附一条必须补的门槛披露)**。实读 `_ENDPOINT_CLAIM_RANK`(`endpoint.py:117-121`)与 max 取值(`:514-518`);`detoxification`/解毒在 `src/pathway_v43/pollutant/*.py` **零命中**(实读 grep)。
2. **落字建议**:"supported_* = **来源层声明的可支持性**:单一直报来源 + 字段齐全 + 无未解决依赖即足(**无最小独立来源数门槛**;独立来源数只是披露);**零事件 run 同样可呈 supported_***(证据来自冻结计划、与本 run 搜索产物无关);任何 supported_* **不得读成本仓核实的终点结论**。"
3. **风险点**:`supported_mineralization` 这个值名 + 摘要里的 `independent_source_support_count` 极易被读成"本仓已证实矿化"。这是本轮**最需要文字设防的一处**(实现方向是保守的,但命名进取)。

### 0f.8 独立持久化与首消费
1. **结论:不同意(现文字)** —— **A2**。文本"**不能以重算新 hash 洗白**"是全称保证,实现不支持:持有 DB 写权者同步改 `payload` 与 `payload_hash` 后,hash 门过(`endpoint.py:652`);若同时保持 `schema_version`、`derived_from` 四摘要与 stop 引用不变,则版本门(`:657-663`)、跨表引用(`:664-676`)、staleness(`:677-697`)**全部通过**。测试面也只覆盖"改 payload 不改 hash"(corrupt)与"自洽改写 schema_version"(版本门)(`tests/test_ppv1_s4a_endpoint.py:758-799` 实读),**没有**"自洽改写 assessment 值"的负控。
2. **落字建议**:"首消费三重检出面:①行内 hash 不符;②`schema_version` 自洽改写;③四摘要(`events/search_actions/endpoint_evidence/inherited_dependencies`)或 `endpoint_policy_version` 漂移;④stop 引用断裂。**持有库写权的自洽改写(同步重算 hash 且不触上述四项)不在检出范围** —— 与 S3B-01 同级'不抗全库协同改写'边界;本仓不做签名。"
3. **风险点**:读者把 endpoint 记录当成"防篡改的化学结论载体",据此对外宣称矿化已受完整性保护 —— 典型"程序诚实、化学误导"。其余五负控 + 正控实读齐全(`:717-825`),描述属实。
- 另注(精度):`derived_from.search_schema_version` 只存不比(当前门只比 policy),0f.8 描述与实现一致 ✓,但建议注明该字段为披露项。

### 0f.9 原生结果对象
1. **结论:不同意(现文字)** —— **A4**。文本"条件与依赖(**上下文 artifact 首消费**)"与实现不符:原生对象侧 `native_result.py:203-208` 用 `read_search_artifact` **只做 H07 信封完整性**,取 `envelope["payload"]`;`production.load_context`(`production.py:327-335`)的 **`PathContext.from_dict` 内容身份核验未在原生侧执行**(该核验只在 endpoint 派生侧 `endpoint.py:304/347` 做)。
2. **落字建议**:"条件与依赖:**H07 信封完整性读取**;内容身份首消费核验(`from_dict`)由 endpoint 派生侧 `load_context` 承担,原生对象侧不重复执行" —— 或改实现原生侧也走 `load_context`(改实现属 S4a 行为变化,需在交付书登记)。
3. **风险点**:把原生结果对象当"全部字段都过了首消费"的正式结果 —— 而 0f.9 恰要对外供 S4b 导出消费,此时缺陷会被放大。
- 其余字段组 **同意**:`states/appearances` 不按 CN 合并(全表 SELECT,native_result.py:98-104)、路径同 `queue.child_path_id` 单一来源(`:162-196`)、备选同父多 expand(`:241-257`)、共同产物 `role=coproduct`(`:258-272`)、deferred 两类/blocked 分列(`:274-295`)、确定性规范化与 digest 键落盘(`:338-354`)。
- 两条 B 级:(i) **`events` 未按 run_id 过滤**(`native_result.py:110-111`,而 `store.list_events(run_id)` 存在,`store.py:2052-2054`);当前每 run 一个 `pollutant.sqlite`(`runflow.py:1437/1563`、测试 `:129`)故生产路径安全,但 schema 允许多 run 同库(`store.py:234-245`)→ 建议改 `WHERE run_id=?` 或在 0f.9 写明"单 run 库"前提;(ii) "同事实同 digest"建议限定为"**同一持久库、同一事实状态**"(载荷含行级 `created_at/updated_at`,跨库同事实 digest 会不同)。

### 0f.10 S4a 边界诚实声明
1. **结论:同意(附一处措辞更正)** —— **A6**:"直接父 `adf0287`"与 git 拓扑不符:实读 HEAD=`fc40605`、直接父=`0e345e8`(纯 docs 归档/冻结提交);`0e345e8` 对 `src/`+`tests/` 的 diff 命中数 = **0**,故"src/tests 与 `adf0287` 逐字节一致"成立,基线对照有效,但"直接父"应改。
2. **落字建议**:"直接父 `0e345e8`(仅 AGENTS.md/docs 归档与判据冻结,src/tests 零改动,实读 diff=0);S4a 源码基线 `adf0287` 与 `0e345e8` 在 src/tests 面等价。"并把"git diff 仅…7 个文件"限定为"**src/tests 面**"(全仓 diff 还含本批 docs 证据/交付书/请求)。
3. **风险点**:复核者按"直接父 adf0287"去 checkout 会与实际提交历史对不上;52 份 legacy code_identity 与聚合哈希 `18007e6a…` 属**执行类** → **待执行验证**(我只验证了 `production.py/audit.py/chemstate.py` 等与 `adf0287` 无 diff,以及本批 src/tests 变更集恰为 5 src + 2 tests)。

### 0f.11 语义未改变声明
1. **结论:不同意(其中一句)** —— **A3**:文本"**879 存量测试零改动全绿**为程序证据"与本请求 §6 自相矛盾(§6:"两个既有字面量测试为本批唯一既有测试改动")。实读 `git diff 0e345e8 HEAD -- tests/`:仅 `tests/test_ppv1_profile.py` 被改,且只有两处字面量(`ppv1-profile-14`→`-15`、`delivered_stages`→`S0-S2,S3a-base,S3b,S4a-endpoint`)。
2. **落字建议**:"879 存量中 **877 零改动**、**2 个既有版本/stage 字面量测试按披露更新(仅字面量,行为零变化)**,全绿为程序证据(通过性待执行验证)"。
3. **风险点**:"零改动全绿"是本轮最强的不变性论据,写错会把"改了 2 个断言"洗成"存量未动"——恰好踩本仓最忌讳的"程序诚实性自伤"。
- 该条其余部分 **同意**:`store-9→10` 纯增量两张表(实读 `store.py` diff 仅新增 `stop_reason_records/endpoint_records` + docstring)、`profile-14→15`、`runflow-3→4`(`runflow.py:175`)、`FROZEN_PLAN_VERSION=ppv1-frozen-plan-1`(`runflow.py:176`)、`search-6`(`profile.py:263`)、endpoint/endpoint_policy/native_result 三契约登记(`profile.py:476-478`)、`delivered_stages`(`profile.py:639`)——**全部实读命中**;"0d/0e 正文一字未改"由本批 diff(仅 5 src + 2 tests)支持 ✓;"若认定 0f 改变判据正文须升 v2"——**我认定 0f 不改变判据一–五与 0d/0e 的含义、范围或硬门**(见末段),故不需 v2;0f 的 A 级问题是它对**实现**的描述错误,应在发出前更正。

---

## 12. §6 程序证据与状态(逐项)

1. **规则级数字(914/879/35/33 文件/1525/16)** — **待执行验证**。可报只读事实:新文件 `test_ppv1_s4a_endpoint.py` = 30 个 `def test_`,唯一参数化 F01 ×6 ⇒ **收集 35 用例**(与"35 新"结构自洽);通过性未验证。
2. **基线红绿(35 collection 红 + 2 字面量红 + 21 正控绿 + 0 行为红)** — **待执行验证**;分类逻辑与"新文件在父上必然 collection 红"相容(父无 `pollutant/endpoint.py`,实读本批为新增文件)。
3. **G01 1516/8/17、291 输入、SHA 前后一致** — **待执行验证**(我未跑控制器,也未读金标/输入清单)。
4. **契约族版本** — **实读全部命中**(见 0f.11);`format-feedback-1` 默认 0 轮实读 `profile.py` 对应注册与 `test_ppv1_profile.py` diff 中 `max_format_feedback_rounds: 0` 断言 ✓。
5. **legacy 零改动与聚合哈希** — 源码面**实读支持**(`production.py/audit.py/chemstate.py` 等与 `adf0287` 无 diff;本批变更集恰 5 src + 2 tests);"52 份文件/`18007e6a…`" **待执行验证**。
6. **判据冻结状态与行号重锚** — **同意**;冻结稿 §0/§22-25 行实读("冻结后变更 = 新版本"、"chemical endpoint 评估属 S4,本判据族不产出任何终点/矿化/解毒结论" `:46-48`)。本批 runflow/store/profile 行号漂移(+18/+18/+… 实读)已声明待重锚 ✓,建议按 0c-v15.6 的双锚标注执行。
7. **执行类声明** — 全部 **待执行验证**;需要跑的是:① `pytest tests/test_ppv1_*.py` 全量与逐文件计数;② 父 worktree 同字节对照(新文件 collection 红、profile 2 字面量红、21 正控绿);③ G01 安全隔离控制器;④ legacy code_identity 聚合;⑤ 双进程 resume 并发与四硬杀恢复;⑥ **新增建议**:一个"自洽改写 endpoint 记录(同步重算 `payload_hash`、改 `chemical_endpoint_assessment`)应被拒/或应被如实登记为不可检出"的负控 —— 用以钉死 0f.8 的边界表述。

---

## 13. 总判定

1. **P1(S4a 实现 vs 冻结判据冲突):未发现。** 判据一–五与 0d/0e 的行为面在本批零改动(实读 diff:仅 `endpoint.py`/`native_result.py` 新增 + `runflow.py`+77 行入口接线 + `store.py`/`profile.py` 登记面 + 2 个测试字面量),decision table、R5d 触发集、strict violated/None、系数构造边界、known_absent 轴归属、三个 None 早退、窄捕获义务等关键点逐条实读与判据一致。
2. **0f 通过条件 = 更正 A 级五项**(A1 0f.1 停止语义复制、A2 0f.8 洗白全称、A3 0f.11 "879 零改动"、A4 0f.9 上下文首消费、A5 0f.2 六/七映射)+ **A6(直接父措辞)**;这五处不改判据正文,属"描述本批新增消费入口"的准确性问题,建议在本轮更正后随 0f 定稿(或按版本规范说明"0f 文字修订不触判据正文")。
3. **B 级**(0f.3 证据校验时机/依赖非空语义、0f.4 范围精化、0f.5 计数口径、0f.6 零事件与次序与 fate 字段来源、0f.7 单来源门槛披露、0f.8 搜索 schema 字段、0f.9 单 run 库前提与行级时间戳、0d.3/判据五 8b 的生产链切分、判据五 8d 时态澄清、0c-v15.5 注释同步、0c-v15.6 双锚标注)可一并落字,不影响放行。
4. **C 级**全部为执行类,**待执行验证**;我未运行任何测试,以上所有"实读"均给出文件与行号,未给出任何未读到的分支名、版本或异常处置。
