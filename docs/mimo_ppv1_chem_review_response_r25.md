> **通道与 provenance（主会话 ZCode 记录，非 mimo 回应正文）**
>
> - 2026-10-09 上午（S5b 准备批轮内化学评审，AGENTS.md mimo 三触发点之 1——题源/结构判据冻结前）：请求 `docs/mimo_ppv1_chem_review_request_r25.md`（自包含、只规则级+合成例、合成例经与真实金标零重叠核验）经 **opencode 免费模型 `opencode/mimo-v2.6-flash-free`** 只读评审；opencode 会话 `ses_ee1bd5afcffevAUBf9Mgj4N783`（标题 "mimo ppv1 v25 chem review"）。与手机 mimo 应用是否同一实例未经证实，采信按本通道口径区分。
> - 一次运行完整输出（无断流、无 TLS 错误）。
> - 评审为**只读**：执行类断言一律"待执行验证"；读码引用带行号；未访问任何金标/题面/gitignored 目录。
> - **本轮结论：转换规则与冻结判据 ppv1-criteria-v1 零冲突（无旁证升格/无范围扩大）。**四面裁定：step_scope=net_reaction 有条件同意（unknown 反而系统性误伤）；角色口径全 principal+未区分披露有条件同意；partial+严格为主+CN 封顶同意（判据既定）；轨道 A known_evidence_reconstruction 同意。**两处 ⚠️P1 结构风险（任务书/评测器契约层，须在转换规则与预注册冻结前裁定）——主会话已亲自读码核实为真**：①G1 配对错位：`_pair_exports_to_samples`（evaluation.py:1718-1728）按根严格身份首中即 break + `digests[0]`（:2019）——53 个重复底物下同根的两个 export 全配给排序在前的图，判分张冠李戴、后图大面积 pending；②known_gaps 桶：图级 known_gaps 非空把无候选边全部路由进 `unmatched_reference_coverage`（:895，排在 budget/plain unmatched 之前）——若预注册把覆盖不足排除出分母，真未命中被免计 → 虚高。mimo 建议：①改评测器配对（ppv1-evaluation-4 单列评审）或回退 G2（分母 209）；②known_gaps 披露保留+预注册写死"图级 known_gaps 仅为披露、不使 unmatched 边免计，不可判边只走 not_evaluable_edge_ids 逐边登记"。另 #6 superset 计 hit 与旧 scorer 口径的同构性待执行核验。
> - 请求原文：`docs/mimo_ppv1_chem_review_request_r25.md`。运行证据与原始输出：`docs/review_evidence/ppv1_s5b_prep_mimo_2026-10-09/`。
> - 以下为 mimo 回应原文（仅清理终端控制字符，未做任何内容改动）。

---
# mimo 化学评审回应 r25：S5b 题源转换规则四判断面

**执行边界声明**：本轮仅用读取类工具浏览仓库根 `/Volumes/CC/Enzyme_Agent/dependingv43` 下 `docs/POLLUTANT_PATHWAY_S5B_PREP_2026-10-09.md`、`docs/POLLUTANT_PATHWAY_CRITERIA_FROZEN_V1_2026-10-08.md`、`docs/POLLUTANT_PATHWAY_S5_SPEC_TASK_2026-10-08.md`、`src/pathway_v43/pollutant/reference_graph.py`、`evaluation.py`、`production.py`、`audit.py`、`src/pathway_v43/domain/identity.py`。未执行任何代码、未跑测试、未访问任何金标/题面/封存 run/gitignored 目录；引用行号均为本轮实读，未读到的标"未确认"；匹配行为类判断属读码推断，一律**待执行验证**。评审对象是 proposed 草案，以下"条件"即建议的冻结前置条件。

**与冻结判据冲突检查（先行）**：逐面比对 ppv1-criteria-v1 判据一~五与 0d/0e——面三"严格为主 + CN 旁证封顶"正是判据五"legacy_cn_match 仅旁证、旁证不叠加升格"（冻结稿行 397–402）与 §0（行 42）的要求，**不存在旁证升格**；`coefficient_status=unknown` 与判据二"未知系数 ⇒ coverage unknown，不猜"（行 161–166）一致；面一 `net_reaction` 不附带任何守恒声明，不触碰判据二的账目边界。**结论：与冻结判据无冲突。** 下文标"⚠️P1"的两项属 S5 任务书 §6/§7 与 S5a 评测器契约层面的结构风险，不是冻结判据冲突，但建议按 P1 在转换规则冻结前裁定。

---

## 判断面一：单步参考边的 step_scope

**① 结论：有条件同意 `net_reaction`（不选 `unknown`）。**
理由一句：RHEA/EnzymeMap/BRENDA 方向化记录就是总包转化，`net_reaction` 是四个枚举值里对源记录最诚实的标签；而 `unknown` 并不"更保守"——评测器按**字符串相等**比对 step_scope（`evaluation.py:851-858`），生产侧假设默认 `step_scope="net_reaction"`（`production.py:241`），参考边标 `unknown` 反而与默认候选系统性不一致，把同形净反应打到 `matched_structure_only` 桶（`evaluation.py:878-890`），比选 `net_reaction` 更误伤。

**条件（建议写成冻结前置）**：
1. 规则文字必须写明：参考边为"方向化记录的净转化形状，无配平、无辅因子计量，**不构成元素/电荷守恒已核**"（与 `coefficient_status=unknown`、判据二"不猜数值"一致）。
2. 保留**逐题例外**规则：转换时若发现某源记录实为多酶/多步拼接才成立的复合转化，该题标 `multistep_summary` 或 `unknown`，不强行全卷统一；例外题数按计数披露（各源记录是否全为单步，未逐题核，**待执行验证**）。
3. 命中前提须披露：评测器要求**存在一条**同时命中 from/to 侧的候选事件（`evaluation.py:837-848`）。纯基元步分解、没有任何净形事件的输出在本口径下不命中——把这句写进 `step_scope_policy`，别让"不要求机理对齐"被读成"任何路径形状都算命中"。

**② 可直接落进规则文字的修改建议**：
> `step_scope=net_reaction`：源记录为数据库方向化总包反应，非基元步；标 elementary_step 属机理过度声明，multistep_summary 留给转换时逐题认定的复合记录（例外计数披露）；unknown 作无法认定时的兜底。本字段只声明净转化口径，参考边不附配平与守恒声明。命中按"至少一条与参考边同形的候选事件"判，纯分解路径无净形事件不计命中（预注册披露）。

**③ 风险点 / 反例类（规则级）**：
- **"程序上诚实但化学上误导"**：step_scope 一致轴可能退化为"常数对常数"——参考侧标 `net_reaction`、生产侧默认也是 `net_reaction`（`production.py:241`），`step_scope_consistent` 几乎恒真；audit 侧对 net_reaction 直接给 CHECK_VERIFIED（`audit.py:1300-1305`）。规则文字不得把"step_scope 一致率"当成任何机理/机制覆盖证据。
- 反例类 (i)：**水解题**——水属无碳组分、按提取规则不入参与物（草案 §1.3，prep 行 99-106），模型若如实列水作共反应物 → 事件反应物侧成超集 → `participant_coverage=superset` → 非 strict（`evaluation.py:870-876`，详见面三③）。
- 反例类 (ii)：**氧化还原题**——NAD⁺/NADH/H⁺ 被剥离后净边无电子受体，模型给对有机产物即命中；"氧化计量/电子受体不在本判分面"须入 coverage_statement，否则读者会把命中理解成氧化还原半反应已核。
- 反例类 (iii)：源记录实为复合转化的题（条件 2）。
- 以上匹配行为均为读码推断，**待执行验证**。

---

## 判断面二：共同产物与主/共产物角色口径

**① 结论：(a) 有条件同意，且必须叠加 (c) 的披露；(b) 作为规则级一刀切不同意。**
理由一句：金标按提取规则只含含碳组分——水、氨这类无碳共底物**根本不在金标里**（prep 行 104），(b) 举的"水/氨"例子在本题集不成立，实际只剩 CO₂ 一个真命题；而按元素/大小切会把甲酸/甲醇/甲醛这类脱卤、脱甲基的真产物误判成 coproduct，模型不报即命中 → 虚高。(a) 与评测器现码同构：`to_node_ids` 全部必要节点须有许可严格命中才授 strict（S5A-03，`evaluation.py:806-821`），这正是"全主产物组分命中"的现码形状；且 347 个金标产物里 45 题（2 产物 41 + 3 产物 4，prep 行 74-76）是多产物题，(a) 的严宽正好在这些题上生效。

**条件**：
1. **角色标签不改变判定**这句必须写进规则：评测器匹配消费的是 `to_node_ids` 成员资格，不是 role——参考侧 participants 角色只回显 node_id（`evaluation.py:909-911`），role 实际只用于事件侧 coproduct 收集（`862-865`）与 key_intermediate 过滤（`2046-2048`）。所以 (a) 的落字要写死"全部金标产物节点既入 nodes（role=principal_product）又入该边 to_node_ids"；将来若启用 (b)，coproduct 节点放不放 `to_node_ids` 是决定性的，不是措辞问题。
2. 保留 (c) 披露：known_gaps 带 `principal_vs_coproduct_undistinguished`（合成例 A 行 314-316 已有）——(a)+(c) 才完整；同时按任务书 §7.4（行 413-421）"必须区分主/副产物"的读法，披露句要写明"本卷金标无角色标注，全列主产物是口径选择，不是化学认定"。
3. "与旧判分口径同构"这句**降级为待核**：请求自述旧口径是"候选 ⊇ 金标即命中"，而评测器 strict 要求集合**相等**——事件多报一个组分 → superset → `matched_participant_coverage_partial`，不计 strict（`evaluation.py:870-876、885-888`）。若 hit 只认 matched_strict，新口径比旧口径严，通过线对齐（预注册第 2 项 A 档）会失真。旧 scorer v3 的额外组分处理与身份归一规则须先核对（仓外文件，**待执行验证**），再定 hit 是否含 superset 档。

**② 可直接落进规则文字的修改建议**：
> 全部金标产物节点 role=principal_product，并全部列入该边 to_node_ids（判分按必要节点集合严格命中）；主/共不作规则级切分，coverage_statement 显式披露"主/共未区分：金标提取产物无角色信息，全部按主产物计；小分子共产物不豁免召回"。禁止按元素/大小启发式降级任何金标产物为 coproduct。相同结构的共同产物（对称裂解）按**结构集合**匹配，不承诺份数（见③）。hit 档位（strict / 是否含 superset）在预注册第 1/9 项一并裁定，须先核旧 scorer 口径再谈"同构"。

**③ 风险点 / 结构性缺陷（建议按 P1 裁定，非冻结判据冲突）**：
- **⚠️P1：known_gaps 非空会把真未命中洗进"参考覆盖不足"桶。** 评测器无候选时的状态分支是 `elif edge_id in not_evaluable_edges or known_gaps: status="unmatched_reference_coverage"`（`evaluation.py:895`），排在 budget 分支（`897-899`）与 plain `unmatched` **之前**。草案计划每图都带 3 条 known_gaps（合成例 A 行 314-316）⇒ 真未命中、预算未展开、真覆盖不足**三种情况全部**落进任务书 §9.1 第 4 桶"因参考覆盖不足而无法判断的边"（spec 行 574）；若预注册按第 8 项把"覆盖不足"排除出分母（spec 行 704），诚实披露 known_gaps 反而替模型的真未命中免了分母责任 → **虚高**，且方向正是"程序上诚实、化学上误导"。落字建议：known_gaps **保留不删**（为凑桶删披露是反向造假），但预注册必须写死"图级 known_gaps 仅为披露字段，不自动使该图 unmatched 边免计；真正不可判的边只经 not_evaluable_edge_ids 逐边登记"——或评测器改分支（评测器变更不属本轮，单列）。读码推断，**待执行验证**。
- **同结构双产物语义虚松**：合成例 B 想表达"同结构两份产物都要报"，但匹配按 state 集合运算（`evaluation.py:822-827、843-848`），一份预测 state 会同时严中两个 occurrence 节点（`718-728`），且 `participant_coverage` 的 `products == to_states` 是集合相等——模型只报一份即可能 exact。化学上"报一份还是两份"在无配平系数时本就不可验证，故建议落字：**相同结构共同产物按结构集合匹配，份数不在判分面（coverage_statement 披露），不得据参考图声称模型漏报第二份**。读码推断，**待执行验证**。
- 反例类（(b) 若强行启用）：脱羧产 CO₂（含碳不剥离，prep 行 104；CO₂ 实际是否全部留在金标**待执行验证**，本轮不接触金标）、脱卤/脱甲基产小分子有机酸、醚/酯裂解双酸、水合产醇——大小/元素启发式全会误伤，且 (b) 下把 coproduct 节点移出 to_node_ids 会让"如实多报共产物"的模型落 superset 降档、少报的反而 strict——惩罚方向倒挂。
- 附带披露项：298 卷无 intermediate 节点 ⇒ `key_intermediate_recall`（只统计 role=intermediate，`evaluation.py:2046-2048`）在本题域恒空，须在 coverage/预注册里写明"该指标本题域不可评"，别让空桶被读成"已测得 0"（prep §2.7 只披露了深度单档，此条未见，**未确认**）。

---

## 判断面三：参与物列表口径 + 匹配身份范围

**① 结论：`partial`+显式覆盖声明——同意；`source_complete`——不同意；`coefficient_status=unknown`——同意；严格为主 + CN 旁证封顶——有条件同意（这是冻结判据既定，本轮无松动空间）。**
理由一句：partial 如实对应提取事实（反应物侧共剥 473 项，prep 行 99-106），而 source_complete 会把"剥离"这个信息优势变成判分参与物——若把 NAD⁺/水放进 `from_node_ids`，S5A-03 要求每个必要 from 节点有许可严格命中（`evaluation.py:806-821`），不报辅因子的模型整边落 `unmatched_required_node_uncovered` → 系统性误伤，同时与金标定义（剥离后含碳组分）脱钩、共底物与金标主产物混列冲垮角色语义——草案对 (b) 的担心成立。

**条件**：
1. 覆盖声明落字建议：
> 参与物 = 提取后的含碳组分；辅因子/共底物（NAD(P)±/H、ATP、GSH、水、金属离子、>80 字符大分子辅因子）按 2026-09-22 提取规则未列；本参考边无配平系数（coefficient_status=unknown），**不作元素/电荷/电子供体计量声明**，不构成守恒已核。`source_complete`/`declared_complete` 本批禁用（前者需新解析器且混淆角色，后者需 teacher 对逐题完整性的另行认定）。
2. 严格档的**系统性低估方向必须预先披露**（不是事后解释）：电荷差（金标中性 vs 模型电离态）→ CN 旁证、不授 strict；立体（金标未指明 vs 模型指定）→ CN 旁证；**互变异构体 → 连 CN 都不等**——`cn_identity = stereo_blind(normalize_charge_smiles(...))`（`identity.py:46-55`），只做电荷归一+去立体，不做互变异构归一，互变差异**完全不命中**。三类都写进 coverage_statement 与预注册 `identity_matching_policy`，并按任务书 §9.1/§9.2（行 571-572、586）同时报 strict 桶与 CN 桶。
3. 不建议本轮新增"互变异构等价"轴：判据一身份键是冻结的 canonical CXSMILES 哈希（冻结稿 §1），把互变等价升为严格身份 = 改判据版本（P1，须 v2 起新评）；如确需，只能作为**新的非严格披露轴**走评测器版本升级 + 预注册，且仍不授 strict（旁证不叠加升格）。
4. 惩罚方向须在预注册裁定：参与物覆盖是**集合相等**判定（`evaluation.py:870-876`）——参考边已声明 partial，模型若如实多列共底物（水/NAD⁺）→ superset → 非 strict。"诚实的更完整输出被降档"这一不对称必须明写（hit 是否含 superset 档），否则"partial 如实"与"判分从紧"叠加会双重惩罚完整输出。**待执行验证**（档位属预注册 TBD）。

**② 可直接落进规则文字的修改建议**：
> participant_list_status=partial + coverage_statement 固定披露句（见①条件 1）；coefficient_status=unknown（逐题、逐参与物）；identity_scope：根/产物节点 strict_structure，严格命中为主，CN 仅旁证披露（identity_scope_cap）不授严格命中；三类已知低估方向（电荷/立体/互变异构）预先入 known_gaps；superset（模型多列共底物）的 hit 档位在预注册第 9 项裁定并披露方向。

**③ 风险点 / 反例类（规则级）**：
- **"程序上诚实但化学上误导"**：partial 本身诚实，但若评测器的 exact 判定不同时披露"参考清单已声明不完整"，superset 降档会被外部读成"模型参与物报错"——落字要写"superset 在参考 partial 语境下不等于化学错误"。
- 反例类：(i) 羧酸产物 pH 电离态 vs 金标中性写法 → CN 旁证（`[CH3-]C=O` 例同理，与请求表述一致）；(ii) 酮-烯醇/酰胺-亚胺酸互变 → 完全不命中；(iii) 金标立体未指明、模型给定立体 → CN 旁证；(iv) Uncharger 无法中和的电荷形态（如特定两性离子/季铵）CN 也可能不等 → 连旁证都没有，低估更强（读码推断，**待执行验证**）。
- 旧 scorer 对电荷/立体的处理若比本口径宽，通过线对齐须重新核算（**待执行验证**，仓外）。

---

## 判断面四：known/unseen 轨道与 recorded 语义

**① 结论分四条**：
1. **轨道 A `known_evidence_reconstruction`：同意。** 一句理由：首轮+Phase D 分数在案、题源与检索语料重叠未经审计，两条都不满足轨道 B 前置——任务书行 216-232 要求未见必须先冻结排除清单，且明写"不能把训练集没有相同字符串称为未见"（行 228）；轨道 A 定义恰好是"允许纳入检索支持范围的反应记录、衡量已有来源支持下的重建"（行 201-214）。结论句式带"已见 298 题、冻结配置"并带题域标签，同意。
2. **一题一组（S1）：有条件同意**——分组键可以一题一组，**独立性标签不能全标 independent**（见②1）。
3. **`reference_only`：同意，不升 `observed`；** 条件是把筛选事实放进 provenance（见②2）。
4. **"同底物两题各算独立样本"：不同意（按独立样本口径）。** 一句理由：任务书 §6.1 行 252 原文"同一根底物的多个分支不能自动视为多个独立样本"；§6.2 行 267-272 原始研究身份未知 ⇒ `independence_status=unknown`。53 底物/89 题（prep 行 84-86）按 S1 全标 independent 属过度声明。

**② 可直接落进规则文字的修改建议**：
1. 独立性落字：
> source_group_id=qid（S1，分组键不变）；但 independence_status 分层：跨题重复底物的 89 题标 `related`（理由：同底物关联，非研究级已核）；其余题在研究级（论文/实验系列）重叠审计完成前标 `unknown` 或明示"独立性仅到数据库记录级已核（rhea/brenda 零共享、enzymemap 5 个共享标 related），**研究级未核，待执行验证**"。S2（按底物归并）作为预注册敏感性分析必报一档；CI 按 source group 聚类/bootstrap（预注册第 5 项 B 档）。**分母仍为 298 题**（逐题描述性命中率不受影响）；受影响的只是"独立支持/置信区间"声明——点估计与独立性两句分开写，不让 independence_status 吃掉分母，也不让分母冒充独立样本数。
2. reference_only 落字（防反向低估）：
> 节点/边 status=reference_only、evidence_basis=`database_recorded_reaction`（合成例 行 306）；provenance.observation_scope 写明"源记录经 V6 卷构造的 chemistry_audit + microbe-confirmed 文献筛选（计数级事实，prep 行 92-98）"——reference_only 表示"库记录+文献筛选"，不是"未经核实的裸记录"；反向不得因筛选升 `observed`（任务书行 457：recorded 不自动表示该场景直接实测；§7.5 recorded 不升格实测，`reference_graph.py` 模块头行 15-17 同义）。`observed` 留给 teacher 若认定"本题域直接实测"的另行裁定，本轮不启用。
3. split=`held_out` + 披露"PPV1 本体未跑过 298、旧版结果在案"：同意（非化学问题，照草案）。

**③ 风险点 / 结构性缺陷（建议按 P1 裁定，非冻结判据冲突）**：
- **⚠️P1：G1（一题一图）在同底物多题下配对错位。** 样本↔导出配对**只按根实体严格身份、命中即 break**（`evaluation.py:1718-1728`），随后取 `digests[0]`（`2019`）。53 个重复底物 ⇒ 同根的两个 export 全部配给排序在前的图：该图可能拿**另一题的 run** 判自己的边（判分张冠李戴），后一图 `not_evaluated_export_missing` → 大面积 pending（`2010-2018`）。qid/root 复合配对信息（graph 的 source_refs= qid，prep 行 174-176）未被消费。**转换规则若选 G1，必须先裁定此条**：改评测器配对（= ppv1-evaluation-4，单列评审）或回退 G2（分母语义变 209）。读码推断，**待执行验证**。
- **独立性虚增的反例类**：同底物+同菌株/同论文两题（S1 会虚增，正是面四问的"偏乐观"来源——点估计不偏、CI 偏窄）；反方向 S2 按底物归并会把不同研究的无关题过度合并；enzymemap 5 对共享标 related 是对的，但它只覆盖"可检测的记录级重叠"，检测不到论文级重叠。
- **"程序上诚实但化学上误导"**：reference_only 若不带筛选事实（②2），会被外部读成"证据等级低"；independence 全标 independent 则相反——程序字段合法、化学/统计声明过强。
- 例 C（两题同底物、occurrence 不合并）与 schema 一致：同结构不同 occurrence 合法保留（`reference_graph.py:312-320` 只拒同 (state, occurrence) 重复），G1 下 entity_id 同、图不同无契约问题——**问题只在配对与独立性，不在图本身**。

---

## 收口清单（供圈定用，全部是条件不是背书）

| # | 事项 | 建议 |
|---|---|---|
| 1 | step_scope | `net_reaction` + 无守恒声明 + 逐题例外规则 + "须存在净形事件"披露 |
| 2 | 角色口径 | (a)+(c)：全 principal 入 to_node_ids + 未区分披露；禁元素/大小启发式；同结构共同产物按集合匹配披露 |
| 3 | ⚠️P1 known_gaps 桶 | 披露保留，预注册写死"图级 known_gaps 不使 unmatched 边免计；不可判边只走 not_evaluable_edge_ids 逐边登记" |
| 4 | participant | partial+固定披露句；source_complete/declared_complete 禁用；coefficient unknown |
| 5 | identity | 严格为主、CN 旁证封顶（判据既定）；电荷/立体/互变异构三类低估方向预披露；互变等价轴本轮不加 |
| 6 | hit 档位 | superset 是否计 hit 须先核旧 scorer 口径再定（**待执行验证**）——否则"同构/可比"不成立 |
| 7 | 轨道/status | 轨道 A 同意；reference_only 同意 + provenance 写入筛选事实 |
| 8 | 独立性 | 分组键 S1 可行；重复底物 89 题不得标 independent（related/unknown），S2 敏感性必报，CI 聚类 |
| 9 | ⚠️P1 G1 配对 | 冻结前裁定：改评测器配对（新版本单列）或 G2；否则 53 底物 89 题判分不可信 |

**冻结判据冲突最终结论：0 项**（无旁证升格、无范围扩大类 P1）。上述第 3、9 项为任务书/评测器契约级结构风险，建议按 P1 在转换规则与预注册冻结前逐条交用户/teacher 裁定。所有读码行为结论**待执行验证**；本回应不含、未索取任何真实题面/金标/运行结果。
