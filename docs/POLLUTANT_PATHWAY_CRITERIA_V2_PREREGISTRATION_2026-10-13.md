# ppv1-criteria-v2 预注册：T-1 判分面参与物集合比较豁免（2026-10-13）

> 状态：**preregistration_pending_final_confirmation**（交 CC 最终确认读；按任务书 §4.1 与代码同轮交付，不阻塞实施）。
> 上位链：teacher 裁定 docs/TEACHER_DECISION_PPV1_T1_COSUBSTRATE_TIER_2026-10-12.md（b 档）→ CS2c 探针 analysis/cs2c_exemption_probe.md（N1=16）→ mimo r36 docs/mimo_ppv1_chem_review_response_r36.md（九条件）→ CS2c 补证 reports/ppv1_s5b/chain12_s5b_298_v4b_20261012/analysis/cs2c_side_predicates.md（N1''=13）→ 冻结前拍板包 docs/TEACHER_T1_FREEZE_DECISION_PACKAGE_2026-10-13.md（CC 拍板"冻结+授权实施"）。
> 题域标签：**298 / RHEA 通用酶学 / 已见题**；本预注册全部数字为判分面模拟（13 题），≠实施后成绩；headline 恒为现行 v1 口径直到新批次出数。
> 实施位置：判分侧（evaluation.py 参与物集合比较轴 + s5b_scoring 版本承载）；**生成侧零改动**。

## 一、方向限定版豁免清单（冻结方向，mimo r36 条件 1）

| 侧 | 豁免身份（cn 层） | cn 收敛键（版本化 sha256 前 16 位） | 依据 |
|---|---|---|---|
| **产物侧** | H₂O | `O` / `c4694f2e93d5c4e7` | 老师 b 档四类 + r28 A2 产物侧原裁 |
| **产物侧** | H⁺ | `[H+]` / `db9399d022ea5663` | 同上（质子化/电荷记账；判据二 unknown 轴） |
| **产物侧** | Pi | `O=P(O)(O)O` / `4332f3bd637634fe` | 同上（带 P 追溯） |
| **产物侧** | PPi | `O=P(O)(O)OP(=O)(O)O` / `d6646ff3c2be5353` | 同上（带 P 追溯） |
| **反应物侧** | 仅 H₂O、H⁺ | 同上两键 | 磷酰化机制判别子保护（`A+PPi→A-P+Pi` 与 `A+Pi→A-P` 不可塌缩）；维持 r28 A2 原裁非推翻；本批零实例，纯防御性收窄 |

- 判定键 = **cn 身份哈希集**（非族签名）：豁免身份经质子化变体组（H₂O 3 变体 / H⁺ 1 / Pi 4 / PPi 4，照抄补证脚本 `V1_VARIANTS`）经 `cn_identity` 收敛单一键，cn 幂等 + Uncharger 往返稳定（补证 §5 已验）；实现内嵌同组变体在导入期收敛断言（不收敛即导入失败，fail-closed）。
- cn 键明文仅为裁定已列名的规则常量（与补证机器数据同批存档）；运行期披露用 sha256 前 16 位版本化哈希。

## 二、三谓词（全过才豁免；任一不过/unknown = 该 extras 维持比较）

豁免作用点 = `evaluation.match_reference_edges` 的逐侧集合比较（`reactants==from_states ∧ products==to_states`，evaluation.py:1062-1068 区域）。仅当事件为 superset 形态（`from_states ⊆ reactants ∧ to_states ⊆ products` 且两侧存在 extras）时进入豁免评审；partial_subset（缺物种）事件豁免救不了，恒维持 partial。逐 extra 实例（粒度 = **身份 + 侧 + 角色**）评估：

1. **记录已声明（pred1）**
   - 执法对象与数据源（mimo r36 条件 3/M3.5 指明）：**payload 内 provenance 回溯链** —— `event.hypothesis_id → hypothesis.provenance_refs → payload.provenance_records 行（record_id 匹配）→ 行 payload 的记录方程声明`。
   - 消费契约（v2 判分侧定义；生成侧将来按此发射，本任务生成侧零改动）：声明行 payload 含 `record_equation`，形如 `{"reactants": [{"smiles": str, "role": str?}…], "products": […]}`；逐条目取 `cn_identity(smiles)`。
   - 判定（身份+侧+角色绑定）：extra 的 cn ∈ 同侧声明 cn 集合（声明条目带 role 时还须与 extra 角色一致）⇒ `true`；声明链可解析且同侧集合可判而 cn 不在 ⇒ `false`；**声明链缺席/引用悬空/方程缺失/任一条目不可解析 ⇒ `unknown`**。
   - **fail-closed：unknown = 不通过 = 不豁免**（不造数据）。
2. **元素可追溯（pred2，计数判据照抄补证脚本口径）**
   - 事件级元素账（O/P 原子计数，RDKit 解析，非豁免侧为供给、豁免簿记侧为需求）：
     `P 供给(非豁免反应物) ≥ P 需求(产物侧豁免 Pi/PPi)`；`O 供给(非豁免反应物) ≥ O 需求(产物侧豁免物 O 合计)`；`O 净消耗 ≤ 反应物侧豁免物 O 合计`（反应物侧水/质子记账轴）；各自无需求时 `not_applicable`。
   - 事件级任一账 `fail` ⇒ 事件整体不豁免；实例级：H⁺ 无 O/P 涉及 ⇒ `not_applicable`（按任务书 §1.1"豁免实例涉及的 O/P"语义记过，**与补证脚本 inst_pass 对 H⁺ 的字面差异如实披露**——本批 H⁺ 实例为 0，对 N1''=13 零影响）；其余实例要求 `pass`。
   - 拦截形态（补证实证）：反应物侧 O=0 而产物豁免水 ⇒ 拒豁免（"无中生水"）。
3. **cn 身份成员（pred3）**：extra 的 `cn_identity` ∈ 该侧豁免身份哈希集（§一）；不可解析 ⇒ 不通过。

## 三、完备二分 + 单归属（mimo r36 条件 5 / M3）

- 每条 extras（身份+侧+角色级）**恰好一个 tier 标签**：`v1_exempt`（三谓词全过）或 `not_exempt_maintains_partial`（其余一切：不在豁免集/方向不许可/任一谓词不过或 unknown）；无第三态，代码内单归属断言 + 常量测试钉死。
- **T1′ 档未实施 ⇒ 未声明多余产物维持 partial**（明字常量注释 + 测试；不理解为"应当实施 T1′"）。
- 事件级：全部 extras（两侧）均为 `v1_exempt` ⇒ 该事件参与物覆盖升为 exact（**逐边机读披露** `exempted_participants`：身份哈希/族标签/侧/角色/tier/pred1/pred2/pred3）并按既有规则进 `matched_strict`；任一 extras 非 `v1_exempt` ⇒ 事件维持 superset（partial）。
- **H⁺/[H] 无合流**（补证 §5 已验 + 常量测试钉死）：`cn([H+]) ≠ cn([H]) ≠ cn([H][H])`；豁免身份集 ∩ `COMPLETION_LICENSED_IDENTITIES` = ∅；`strict_identity_of("[H+]") ∉ 许可集`。

## 四、机器挡板（mimo r36 条件 1 附/8；任务书 §1.2）

- **豁免构造非法断言**：豁免清单所有变体 SMILES **零碳原子**（导入期断言）；含碳身份（CO₂/HCO₃⁻/CO₃²⁻ 等）构造性禁入豁免清单——**known gap：CO₂/HCO₃⁻ 是 v2 未来冲突点**（mimo r36 M1 末：r28 A2 曾建议白名单但含碳被挡），登记不重开。
- **辅因子硬拒绝表**（进比较面绝不豁免；正面清单语义 + 常量测试 + 负控钉死）：NAD(P) 系、ATP/ADP/AMP、CoA、FAD/FMN、THF、O₂、NH₃、T1′ 恒不忽略族（CN⁻/SCN⁻/H₂O₂/NH₂OH/NO）——其 cn 身份断言不在豁免集。

## 五、披露与批级聚合

- 豁免发生时逐边机读 `exempted_participants`（进 evaluation 输出与判分聚合）；
- 批级（v2 口径 evaluate 输出 `criteria_v2` 块）：`criteria_version`、edges/events 豁免计数、tier 单归属计数、`exempted_participant_occurrences`；
- **参考侧监控**（mimo r36 条件 4，应为 0）：统计参考图节点 cn 身份落入豁免集次数；非 0 ⇒ `reference_side_v1_identity_signal = EXIT_CONDITION_SIGNAL_nonzero`（退出条件信号，批级披露字段）。

## 六、版本承载与 NC-12 前提域重写（mimo r36 条件 6）

- 判据版本常量：`ppv1-criteria-v1`（既有冻结口径，缺省）→ **`ppv1-criteria-v2`**（本次）；承载于 evaluation 输出（v2 时 `scoring_provenance`/`criteria_v2` 块）与 s5b_scoring 聚合（v2 时并列块）；**不动 EDIT_PROTOCOL/ATOMTOOL/池策略/PPV1_EVALUATION_VERSION（评测器 schema 版本保持 ppv1-evaluation-5，冻结输入仍合法）**。
- **豁免开关**：`evaluate_scientific`/`match_reference_edges`/`score_s5b_batch` 新增 keyword-only `criteria_version`（缺省 v1）。**缺省 v1 路径零行为差（豁免关闭字节不变）**；v2 为显式启用（新批次经预注册启用）。
- NC-12 前提域重写："本通道 matched_strict 恒 0" → "**未获豁免披露的本通道 matched_strict 恒 0**"（tests/test_ppv1_s5b_cosub_d2.py 断言注记 + recorded_source.py 注释措辞同步；不静默删除旧文字，改动处注明 v2 依据）。

## 七、双口径与生效

- **v1 口径恒为 headline** 直到新批次按 v2 预注册出数；v2 敏感性经同批双跑并列（rescore 先例：`scripts/s5b_offline_rescore.py` 同一遍读取链分 criteria_version=v1/v2 两遍）。
- post-hoc 标签 + 位次/新覆盖分离计数沿用 W0 诊断口径；**探针仅覆盖 43 道 partial 桶 ⇒ 13 题投影为下界**（mimo r36 条件 9/M4-5），已有 strict 题的位次效应未模拟。
- 旧批零回写：chain12 及此前批次的已判产物不重写；本任务仅做只读重算对照。

## 八、预期（模拟下界，非承诺）

- 模拟解锁面 N1''=13（三层账：16 池化 → 16 逐侧 → 16 方向限定 → **13 三谓词+元素账**）；剔除 3 题均为"无中生水"（pred2 拦截实证）；hit@1 +3 / hit@3 +9 / hit@5 +0 / U +1；298 投影 hit@1 95 / hit@3 138 / hit@5 142（冻结基线 92/126/130，仅供条款对照）。
- 降档条款：13 ≥ 5 不触发"仅记录不实施"。
- **实施面兑现前提（如实登记）**：pred1 数据源 = payload 声明链；chain12 全 298 payload 的 `provenance_records` 行数 = 0、hypothesis `provenance_refs` 非空数 = 0、`transformation_ref` 仅为 RHEA 引用号非方程（本预注册前实测）⇒ **chain12 只读重算下 v2 预期解锁 0 题**（fail-closed 兑现，非 13）；13 的兑现待生成侧/批装配按 §二.1 消费契约填充声明链（生成侧零改动红线内本任务不填充）。v2 重算与 13 的逐题 diff 归因如实报告（任务书 §4.6）。

## 九、退出条件

- 参考侧 `omitted_coproduct_scope`（辅因子/共底物信息加回金标参考）落地即**废止本豁免**（teacher 裁定条款）；
- 参考侧出现豁免身份计数非 0 = 退出条件信号（§五）；
- 豁免被用于洗白机制主张的任何实证 ⇒ 停用待审。

## 十、known gaps（预注册登记）

1. **CO₂/HCO₃⁻ v2 冲突点**：含碳身份构造非法断言将其挡在豁免面外（§四）；未来如需豁免须重开裁定。
2. **pred2 计数级追溯**：P/O 计数账不证明键级机制来源；判据二（系数/电荷账 unknown）口径不变。
3. **pred1 实例级 H⁺ 语义差**：实现按任务书"涉及 O/P"语义将 H⁺ 记 `not_applicable`（过），与补证脚本 inst_pass 字面（要求恰 `pass`）不同；本批 H⁺ 实例 0，对 13 零影响（§二.2 如实披露）。
4. **声明链消费契约先行**：声明方程格式为判分侧消费契约（§二.1），生成侧发射器未装配（`put_provenance` 零调用方实测）；v1 口径 headline 不受影响。
5. 模拟数字均为 298 题域 partial 桶下界；不外推 dev。
