# T-E 记录侧形式归一 —— run 身份 / 缓存 key 闭合设计稿（**DRAFT · v2**）

> ## 状态横幅（先读）
>
> - **本文件是设计稿 DRAFT（草案 · v2）**，用于送复审（Codex/主窗口组织）；**不是冻结、不是预注册、
>   不是实施授权**。任何实施、任何对外表述不得引用本文件为依据（以 FROZEN_V3 与 CC 拍板为准）。
> - **v2 依据**：`docs/T_E_RUN_IDENTITY_DESIGN_CODEX_REVIEW_2026-10-19.md`（Codex 终审：裁定=需修正，
>   无 P0，四组 P1 + Q1–Q11 逐条裁定 + §5「实施前必须落字的口径」表）。v2 逐条落实该报告要求的
>   实施前动作；落实位置见「修订记录（v2）」。**本稿仍处 DRAFT，待同范围复审后才能进入实施。**
> - 性质：**零模型 / 零网络 / 零 LLM / 零费用**；本稿只做**只读代码考古 + 只读计数/算子探针**
>   （命令见附录 A；探针只读资产文件、只打印计数与类别，不落任何结构串）。
> - **金标/题面零接触**：本稿不含任何结构串（SMILES）、不含题面/参考图内容；所有定位只用
>   `文件:行号`、`qid 头哈希`、计数与类别。
> - **考古基线 HEAD**：`26ad11977852644ac581d8422e88f85074d7afcb`（评审同基线；本稿不 git add/
>   commit/push）。行号以该 HEAD 为准；**涉及编译层（s5b_compiler）的行号/行为一律以评审固定副本
>   `docs/review_evidence/t_e_run_identity_codex_2026-10-19/baseline_sources/src/pathway_v43/pollutant/s5b_compiler.py`
>   （= compiler-4）为准**——同期另有执行者在并行改 compiler（D1.2 补映射，compiler-4→5），本稿
>   **不引用 compiler-5 的任何新行为、不裁定其改动**（该副本 SHA256 `aa6806b8…`；与当前工作树
>   不同，即并发变更的固定证据）。
> - 上游（按读取顺序）：`docs/POLLUTANT_PATHWAY_CRITERIA_FROZEN_V3_2026-10-19.md`（语义权威，§5 /
>   §5.2 C-1/C-3/C-5 / §5.3 / §11 缺口 6；本稿只细化工程合同，不改写冻结判据）→
>   `docs/TASK_T_G_FIX_ENGINEERING_2026-10-19.md`（§3 Step E1 前置 2）→
>   `docs/TASK_T_DE_E1_PRE1_RECOMPUTE_2026-10-19.md`（§0–2）→ `docs/T_E_RUN_IDENTITY_DESIGN_CODEX_REVIEW_2026-10-19.md`
>   （v2 回修任务书）→ 本仓 `AGENTS.md`（「实施先列入口，再修同一规则」「身份与完整性在首次消费时闭合」）。
> - 题域标签：**298 = RHEA 通用酶学 / 已见题（post-hoc）**；本稿全部数字挂在该标签下，**不向 dev 外推**。
> - 范围声明：本稿**只管 run 身份/缓存 key 闭合设计**；数值重算（缺口 5）归 E1 前置 1 子任务，不在本稿。

---

## 修订记录（v2，2026-10-19；依据 Codex 审核报告逐条落实）

> 评审报告结构对应：§4 四组 P1（最小回修清单）、§2 Q1–Q11 逐条裁定、§3 八项重点裁定、
> §5「实施前必须落字的口径」表。以下为 v2 逐条落实位置。

1. **P1-1 build→首次消费绑定** → 新增 **§3.6（受控批 build 身份/输入字节绑定设计）**；并**更正
   原稿 §1.4/A9 的旧导出过期门错误论证**（改为如实陈述「现有机制只保证启动后的身份，不能证明
   build 出处」+ 正确消费链 `s5b_scoring.py:584-587 → native_export.py:180-191/600-616`）。
2. **P1-2 corpus 分类/装配漏入口 + raw/视体字面冲突** → 改 **§1.1（注入点表 + 统一消费视体）**、
   **§1.2（消费者矩阵改为"消费视体 vs 原始面"两分）**、**§3.1（corpus 视体建立时点前移到分类前）**；
   明确 `record_equation`/`matched_component` 为 raw 来源例外（评审 §3.5）。
3. **P1-3 真实参数/事务/幂等合同** → 改 **§3.2（删无效参数写法；构造器签名三默认值实测登记；
   不可自省面单列）**、**§4（applied/not_applicable/failed 重定义；事务单位=一次候选消费视体；
   双遍合同更正；applied 允许保留永久电荷）**。
4. **P1-4 C-5 审计/字节不变/差分基线可验合同** → 重写 **§5（逐候选 trace 坐标系统一定死；风险交集
   限定实际消费查询/匹配原子；unknown 语义；spec 条件披露与证明域；对拍两层；A 臂等价证明）**。
5. **Q1–Q11 改写同步** → 正文各落点（Q1§3.1/§3.2、Q2§4.1、Q3§1.2/§3.1、Q4§1.2/§3.1、Q5§3.1/§4.1、
   Q6§4.1、Q7§4.2、Q8§3.3/§3.6/§5.4、Q9§3.2、Q10§5.2/§5.3、Q11§5.1）；**§6 改为裁定-落点表**。
6. **版本口径**（评审 §3.3 裁定）→ §3.3：`pool-9`、`source-4`、`formnorm-1` + 实参指纹；
   `route-1`/`compiler-4` 保留但**绑定 formnorm 版本/指纹**并注明**路由结果可变、算法未改**。
7. **与评审 §5 口径表逐项对应**（落实对照）：

| 评审 §5 合同面 | v2 落实节 |
|---|---|
| 算子／标签 | §3.2（真实参数+指纹）、§4.1（三值按提交事务状态） |
| 事务／入口 | §4.2（全消费视体原子提交）、§3.1（corpus 分类前贯通）、§1.1（analog 同 ref 同域） |
| 身份／来源 | §1.2（raw 例外表）、§3.1（tier 零触碰硬约束）、§5.1（消费态/trace 披露，归一对齐不授严格身份） |
| build／缓存 | §3.6（build 身份与输入字节绑定、worker 首消费核对）、§3.4（缓存 key 不加归一版本、值不可变/写时复制）、§3.2（memo 带指纹与原串） |
| 版本／历史 | §3.3（pool-9/source-4/formnorm-1 及实参指纹；route-1 绑定）、§3.6（旧批零回写）、§5.4（历史事实重判不冒充新策略产物） |
| C-5／对拍 | §5.1（逐候选三值+trace、风险交集、unknown）、§5.2（applied spec 条件加证明域；未 applied spec 不变）、§5.3（旧 diag 投影／新增审计分别验；A 臂先证旧基线等价） |
| N10／正交 | §5.4（固定同批同事实同 criteria 逐项对拍；N3/N7 固定 payload 比；新池变化另表归因） |

**v1（首稿）保留说明**：v1 的只读考古事实（§1 表格、§1.5 计数、§2 A 面清单、§5 差分探针方法学）
继续有效；v2 对其中**被评审指出不成立的口径**（旧导出论证、`neutralize=True`、单串回退、
双遍推导、同树恒等即旧基线）就地改写，并在原处标注 `v2：依据 …`。

---

## 0. 一页总览（结论先行；v2 更新）

| 段 | 结论（一句话） | 落点 |
|---|---|---|
| **A 面清单** | 归一字符串**不流进任何 file-keyed / asset-keyed 缓存的 key**；流进的是**诊断物化面与 run_inputs 字节面**（仅对"归一实际发生"的候选/题）；**现有 run 身份只保证启动后的代码身份，不证明 build 出处**——受控批新增 build→首次消费绑定 | §2、§3.6 |
| **B 处置** | 推荐"**源资产零改动 + 内存变换 + 实测无操作短路（先运行算子、按同原子核对）**"三件套；算子版本化常量＋**真实参数**指纹（含 RDKit）；池策略 `s5b-pool-policy-8 → 9`、`recorded-source-3 → 4`；**每候选三值标签＋trace 落 `pool_diagnostics.candidates` 行**，spec 仅在 applied 行做条件性披露（附证明域） | §3 |
| **C 事务/幂等** | 失败＝**整候选消费视体回原始＋`failed` 披露**；**事务单位＝一次候选消费视体**（donor/lhs、rhs/products、copies、full_products、派生供给及装配字段全量原子化）；成功域双遍字节固定点（第二遍无新增改动）；applied 输出**允许保留永久电荷** | §4 |
| **D 审计/对拍** | 新增**可验合同**：逐候选（全形态）三值＋可定位 trace；风险交集＝实际消费查询/匹配原子 ∩ 同坐标 lhs 改动原子；**对拍分两层**（旧字段投影不变 / 新审计字段另验）；**恒等 A 臂先证与 pre-T-E 旧树等价**才能称"旧基线" | §5 |
| **E 裁定落点** | Q1–Q11 已由 Codex 逐条裁定（Q1/Q2/Q7/Q8/Q9/Q10/Q11 改写；Q3/Q4/Q5/Q6 采纳原倾向）；本稿 §6 为**裁定-落点表**，无新增开放问题 | §6 |

关键实证（v1 新做，只读；仍有效）：**记录侧资产字符串大面积"无电荷但非 canonical"**——若采用"无条件
归一"，约 **75%** 的 EAWAG donor 串会被纯重规范化改写，字节漂移面将远超化学目标面；**短路设计
把字节差面收敛为"算子实际改变化学状态"的行**（§1.5/§3.1）。

---

## 1. 事实基线（只读代码考古；逐项 `文件:行号`）

### 1.1 归一注入点候选与当前消费链（v2：依据 P1-2，含统一消费视体）

FROZEN_V3 §5.2 C-1 已冻结：**仅记录侧**（donor+products）施加 `Uncharger()` 默认配置
（逐组分 → 点号重接；analog 保留原子映射号），作用在检索/编译链的**对齐层**。代码考古得到的
现行消费链（即注入点候选与各自影响面）：

| 通道 | 记录侧字符串来源 | 现行消费点（文件:行号） | 影响面 |
|---|---|---|---|
| recorded（EAWAG） | `load_library_index` 回读 `donor_smiles`/`products`（`src/pathway_v43/pollutant/recorded_source.py:419-460`），消费者 `find_recorded_exact:1196` | 编译调用 `:1251-1255`；`compile_recorded_reaction:2060` 内部：映射推断 `:2095`（`infer_reaction_mapping:728`，donor+products 并集）、`mapped_lhs/rhs` 构建 `:2117-2123`、产物 strict 门 `:2144-2147/:2182-2185`、union gate `:2195-2273`、spec 内嵌 `compile.record_products :2279` | 池成员/编译结果；spec 字节 |
| corpus（RHEA/enviPath） | `load_corpus_index` 回读（`:523-611`），消费者 `find_corpus_recorded_exact:1295` | **候选识别之后、分类之前**（`_classify_cosubstrate_candidate` 调用点 `:1483`；函数体 `:933-1013`，解析 B/推断映射/原子归属全在视体上）→ 三分支编译 `:1519-1525`（split，带 `declared_copies`/`record_products`）、整串编译 `:1708-1712`；编译后装配 `_attach_cosubstrate_spec_fields:1862-2023`（`co_comps`/`flat_products`/`copy_products` 全量）与候选条目 `_corpus_candidate:2026-2057`；**NC-10 两处声明** `:1957`（contract `record_products`）与 `:2021`（corpus 块 `record_products`）；union gate `:2195-2273`；spec 元数据 `matched_component :1735`（**原始串＝来源例外**，v2：依据 Q4） | 同上 + corpus 元数据一致性 |
| analog（模板） | `AnalogSourceResolver`（`src/pathway_v43/services/analog_source.py`）：`DonorRef.mapped_lhs/mapped_rhs :80-92`；召回 `templates_similar_to:359-411`（原始行，含 map 号） | builder `_compile_analog_refs`（`src/pathway_v43/pollutant/s5b_builder.py:1193-1412`）：**`for ref in refs` 起点建"归一视体"，循环内全部 ref 消费者同域**——F1 `template_elements_fit :1277`、F2 `analog_cosub_supply :1307-1311`、F3 wildcard `:1312-1326`、F5 `center_anchor_probe :1219-1232`、编译 `_compile_at :1247-1258`、spectators `:1353-1356`（随 F2 同域）；**`record_equation :1357-1359` 读原始串＝来源例外**（v2：依据 Q3） | 路由/准入/编译/声明面/诊断 |

**统一消费视体（v2：依据 P1-2）**：候选识别后、分类/编译/装配之前建立**每候选一份**的
"记录侧消费视体"（记录侧各串 × 同一算子，单一实现源）；以下**真实消费面**一律读视体且**同域同源**：
分类（corpus `_classify_cosubstrate_candidate` 的 `co_comps`/`matched_side`/`products` 入参）、
编译（`compile_recorded_reaction` 入参：`donor_smiles`/`products`/`declared_copies`/`record_products`）、
装配（`co_comps`/`flat_products`/`copy_products`/participants/`co_substrate_states`/
`declared_copy_components`）与 **NC-10 两处声明**（`:1957`/`:2021` 的 `record_products`）。
**来源例外面（保 raw）**只限来源/身份声明：检索分层 tier、召回与来源字段、
`record_equation`（analog pred1 契约，v2：依据 Q3）、`matched_component`（corpus spec/候选 detail，
v2：依据 Q4）——例外面**不得**被实际装配/NC-10 计量字段冒充"只读 provenance"（评审 §3.5）。
**不变量**：原始召回/tier/来源字段不变；**公共 compile 直接入口（`compile_recorded_reaction` 被
直呼时）仍共用同一算子，不留旁路**——corpus 视体输入经 compile 入口二次过算子 = 成功域固定点
（第二遍无操作），不发生二次变形（双遍合同见 §4.3）。
**行级通配预筛（`recorded_source.py:1391-1397`）与 T-4 碳类诊断代理剖面
（`recorded_source.py:1476-1478`、`:1800-1807`）判据零改动**，
登记为**原始域**及不变性（v2：依据 P1-2；评审 §P1-2 要求动作）。

**设计输入更正（工程事实，不改冻结文本）**：`TASK_T_G_FIX_ENGINEERING_2026-10-19.md` §3 Step E1
所列入口 "`s5b_compiler.py:487-505` 消费点" 已**失效**——该行区间在审前基线即为
`_stereo_dissolution_mismatch`（固定副本 `s5b_compiler.py:485`），旧的 `enumerate_template_alignments`
（全供体对齐）**已随 s5b-compiler-4 从 src 移除**（`TASK_T_DE_E1_PRE1_RECOMPUTE_2026-10-19.md` §2.2
已记载；legacy 复现需 vendor 旧函数）。现行编译层对齐 = 中心锚定匹配（固定副本
`build_center_query:621` / `enumerate_center_alignments:653`（`maxMatches=_COMPILE_ALIGNMENT_LIMIT=64 :130`）
/ `center_anchor_probe:671`，编译侧消费 `:1234-1235`）。T-E 实施的实际注入面是上表三行，不是 `:487-505`。
（v2 附注：同期 compiler-5 改动不由本稿引用或裁定，行号口径见状态横幅。）

**同一规则多入口纪律（AGENTS 返工教训 1）**：三通道的注入点必须共用**同一个归一算子函数
（单一实现源）**，不得各写一套；且注入点必须选在"该通道内**全部**记录侧消费者之前"，否则
F5（中心 helper，与编译层同源校验，见 `s5b_builder.py:1203-1207`）与编译器会对**不同字符串**
判同一件事——同源不变量被破坏。**analog 特别条款（v2：依据 P1-2）**：视体必须在 `for ref in refs`
起点一次性建立并**整体替换 ref 供下游消费**——不得只改局部 `lhs/rhs` 而仍把 raw ref（raw
`mapped_lhs/mapped_rhs`/`center_atoms`）传编译（评审 §3.7）。

### 1.2 记录侧消费者矩阵（v2：依据 P1-2/Q3/Q4/Q5，改为"消费视体 vs 原始面"两分）

| 消费者（文件:行号） | 读什么 | 归一后读哪面 | 备注 |
|---|---|---|---|
| recorded/corpus 检索分层 tier（`recorded_source.py:1238-1250` / `:1445-1455`） | 原始 donor strict/CN 身份 | **原始面（硬约束）** | tier（strict/cn 分层标注）属身份面：FROZEN_V3 §5.1/D06 明言 T-E 不得升格身份；若归一后重判 tier＝静默升格 strict，禁。归一后相等**不得**改名 strict exact，不改底物 strict/CN 定义；真实执行产物仍按既有 strict 判据**独立验证**（评审 §3.2） |
| 检索/召回与来源字段（引擎 lookup 序、`filter_flags`、`provenance_sha256`、`asset_sha256`、`record_key/master_id/direction/ec`） | 记录行来源事实 | **原始面** | 原始召回序/来源字段不变（评审 §P1-2 要求动作） |
| `infer_reaction_mapping`（`:728`，经 `:2095` 调用；corpus 经分类内 `:984`） | donor+products（结构对应枚举） | **视体** | 对应关系须在同一归一域内建立 |
| `mapped_lhs/rhs` 构建（`:2117-2123`） | donor/products | **视体** | EAWAG 无原生 map，map 号按 donor 原子 idx 赋（`:2110-2116`）⇒ 字符串重排会改 map 标号（短路把该风险限制在 applied 行内，§1.5 注） |
| 产物 strict 门 / union gate（`:2144-2147/:2182-2185/:2195-2273`） | products / `record_products` / `declared_copies` | **视体（全部同域）** | 混域（一半原始一半归一）会产生假拒/假过 |
| spec 内嵌 `compile.record_products`（`:2279`）、`record_products_full`（`:2289-2290`） | products 入参 | **视体（＝消费态）** | 原始串可由 `record_key` + 源资产 sha 机械重认（§3.5）；`verified_product_set` 的证明域见 §5.2 |
| corpus spec `matched_component`（`:1735`；候选 detail 同串） | 匹配侧原始串 | **原始面（来源例外；v2：依据 Q4）** | 保持 raw；applied 时**另**披露消费态与 trace，标明它不是归一后严格身份声明；实际 `co_substrates`/copies/`record_products` 依同一消费域装配（评审 §2-Q4） |
| corpus 分类（`_classify_cosubstrate_candidate:933-1013`；调用点 `:1483`）| `matched_side`/`co_comps`/`products` | **视体（v2：依据 P1-2）** | 分类早于编译：视体必须**分类前**建立，否则分类与编译不同域（审核 §P1-2 的具体缺口） |
| corpus 装配（`_attach_cosubstrate_spec_fields:1862-2023`；`_corpus_candidate:2026-2057`） | `co_comps`/`flat_products`/`copy_products`/participants/states | **视体（v2：依据 P1-2）** | NC-10 两处声明（`:1957`/`:2021`）与事件级断言（`production.py:839-858`）同域；混域会在首消费按 strict 不等拒 |
| analog F1（`s5b_builder.py:1277`） | mapped_lhs 元素账 | 视体（结论不变） | **元素多重集不变**：Uncharger 不增删重原子 ⇒ F1 verdict 不变（`template_elements_fit` 只算元素，固定副本 `s5b_compiler.py:169-204`） |
| analog F2 供给（`:1307-1311`，`analog_cosub_supply:603`） | lhs/rhs 组分 + Morgan 指纹 | **视体（否则与编译不同域）** | **指纹电荷敏感（实证：酸/阴离子 Tanimoto=0.5，§1.5）** ⇒ 主份选择/供给清单可变化，须在字节面归因 |
| analog F3 wildcard（`:1312-1326`） | 去 map 组分含 `*` 判 | 视体（结论不变） | Uncharger 不改 dummy 原子 |
| analog F5（`:1219-1232`，`center_anchor_probe:671`） | lhs/rhs/执行输入 | **视体（必须）** | F5 与编译层同源校验依赖同一输入串 |
| analog 编译（`:1247-1258`） | ref.mapped_lhs/rhs | **视体** | map 号必须保留（FROZEN_V3 C-1）；不得把 raw ref 传编译（v2：依据 P1-2） |
| analog `record_equation`（`:1357-1359`，`analog_record_equation:806-822`） | ref 原始串（文档口径＝"记录原样"） | **原始面（来源例外；v2：依据 Q3 终裁）** | criteria-v2 pred1 消费契约（`builder:404-406`；判分侧消费 `evaluation.py:1017-1101` 按同侧 cn/role）；applied 行**另**披露归一消费事实——不把原始记录声明改写成消费态（评审 §3.5） |
| analog spectators/co_substrate_states（`:1353-1356`，`_attach_analog_cosub_supply_fields:825-906`） | 供给清单（源自 lhs/rhs 解析） | **视体（随 F2 同域）** | `co_substrate_states[].smiles` 嵌供给组分串；与 F2 用同一视体（v2：依据 P1-2） |
| 池诊断 `_diag_row`（`:1069-1100`）/`signature_head`（`:1065-1067`→`net_reaction_signature` 固定副本 `s5b_compiler.py:206-233`）/`execution_input_sha256`（`:1216-1217`） | spec 内容 / F4 串 | 视体（如实反映新事实） | 写进 `batch_manifest.entries[].pool_diagnostics`（`:1644`）；**新增审计字段**（三值+trace）落同一行、**单独验收**（§5.3） |

### 1.3 缓存面清单（grep `lru_cache|_CACHE|cache_key` 于 `src/pathway_v43/pollutant/`、`services/` 的逐条判定）

| 缓存 | 位置 | key 构成 | 归一字符串是否在 key/值 |
|---|---|---|---|
| `_LIBRARY_CACHE` | `recorded_source.py:393, 419-460` | `(library_path, library_sha256)`（`:427`） | **不在 key**；值为**原始行**（`:440-459`）。前提：归一必须在读取之后施加（§3.1 约束） |
| `_CORPUS_CACHE` | `:471, 523-611` | `(corpus_v1_path, corpus_v1_sha256)`（`:540-541`） | 同上（`:602-610`）；同页构建的 CN 检索索引（`:587-601`）读原始串，归一无涉（检索侧 cn_identity 本就电荷归一，`domain/identity.py:46`） |
| `AnalogSourceResolver._INDEX_CACHE` | `analog_source.py:196-257` | `(name, asset_sha256)`（`:196-200`）＋变体 tag（含指纹先例：`_reactant_fp_index` 键并入 `SIMILARITY_VERSION`，`:265-267`） | **不在 key**；值为原始行。归一下游施加（召回保持原始，§3.1） |
| `domain/identity.py` lru 三件套 | `:21-23, :26-37, :40-43` | 纯函数 memo，键＝输入串本身 | 串 keyed 但**纯函数**（同串同果）；新增归一如做 memo 见 §3.4 |
| `donor_applicability.assess_cache` | `services/donor_applicability.py:747-753`，键 `(asset_sha256, line_no, record_id)+(substrate)`（`:833-838`），**每次 `build_eligibility` 调用内局部**（`:924`） | 记录 id 键（**form 无关**） | T-E 不触及该路径（workflow 证据卡侧，非 s5b 池侧）；若未来扩展，键须并入指纹（§3.4） |
| `substrate_feature_cache_key` | `search.py:465-475` | `state_digest + feature_policy_version` | **底物侧**；T-E 不动底物串 ⇒ 不变（且 src 内暂无生产消费者，仅测试引用） |
| `atom_tool._verified_vendor` | `services/atom_tool.py:163` `@lru_cache(maxsize=1)` | 无参（vendor 完整性） | 无关 |
| `recorded_source.py:170` `from functools import lru_cache` | — | **未使用**（全文件无 `@lru_cache`） | 死 import，登记为事实，不构成面 |

### 1.4 run 身份与物化面（v2：依据 P1-1，更正旧导出过期门论证 + build 出处缺口）

| 面 | 位置 | 与归一的关系 |
|---|---|---|
| 每题 run_id | `s5b_builder.py:343-345`：`f"{batch_tag}-{stable_id('s5br', qid)[:16]}"` | **与记录串无关**（batch_tag+qid 派生）；新批次＝新 batch_tag（AGENTS 红线：封存 run 只读、新实验新批次根） |
| run 身份（resume 门） | `storage/run_identity.py:76-100`（`code_identity`＝`src/pathway_v43/**/*.py` 逐文件 SHA＋聚合；pollutant profile 全树）、`:103-112`（依赖版本含 rdkit）、`:115-187`（`build_run_identity`）、`:190-198`（`identity_fingerprint`）；`runflow.py:1859-1876`（start 写入）、`:1997-2005`（resume 重建＋`check_resume_identity`） | **T-E 改码 ⇒ code_identity 变 ⇒ 旧 run resume 直接拒**（设计行为）；**但该机制只证明"启动之后"的身份**——resume 拒既存 run 跨代码续跑（曾由合成探针证实 `IdentityMismatch(code_identity)`），**不能证明输入在首次 start 前由当前代码构建**（v2：依据 P1-1） |
| run 输入字节面 | `s5b_builder.py:351-374`（`build_run_input`：`plan.pools` = **编译后池 spec 原文**；**当前无任何 build 身份/输入字节 sha 字段**）、`:1627-1633`（`run_inputs/<qid>.json` 落盘）；消费 `s5b_worker.py:70-74`（读盘）、`:215-229`（无 `run_identity.json` 即 start，**此前不核对输入出处**） | **归一改池 ⇒ 受影响题的 run_inputs 字节变**（T-E 的预期效果面）；**旧输入可被新代码首次 start 接纳并登记新身份**（评审合成探针）⇒ 须新增 build→首次消费绑定（§3.6） |
| 批清单 | `s5b_builder.py:1634-1647`（entries：`substrate_smiles`/`run_input_rel`/`pool_size`/`pool_diagnostics`/图 sha；**当前无输入字节 sha、无 build 身份块**）、`:1665-1680`（manifest 落盘） | 底物串不变；`pool_size`/`pool_diagnostics` **可随归一变**；v2 新增 `build_identity` 旁块（§3.6） |
| **导出"过期门"（v1 论证更正）** | 实际导出读取链：`s5b_scoring.py:584-587` 调 `native_export.read_native_export`；`native_export.py:180-191`（`_current_contract_versions`）与 `:600-616`（manifest 核心）**不含 pool/formnorm/code 身份字段**。v1 所引 `output/export_v3.py:869-871` 是 **legacy 导出路径**，其比较对象是 **run 目录内保存的身份**（`export_v3.py:845` `_load_run_identity(run_dir)`）与导出元数据（rev/policy/predictions sha 等）之间的一致性——**不是对当前源码自动重新哈希** | **结论更正（v2：依据 P1-1）**：现有机制**只保证启动后的身份、不证明 build 出处**；旧导出/旧输入不会因代码变化自动失效。⇒ 不能靠既有门宣布"旧导出过期"；受控批须走 §3.6 新绑定（不要求升级 native-export schema、不拒所有历史导出） |
| spec 身份键 | 固定副本 `s5b_compiler.py:1414`（`key=f"{key_prefix}-{record_id}"`）、`:1419`（`origin_group_key`）、`:1426`（`alignment.ref`）；analog 覆写 `s5b_builder.py:1238-1245`（`tpl-<rid>`/`analog-template:<rid>`） | **id-based，不含模板内容/哈希** ⇒ 归一不改 spec 身份（同一记录不因 form 分裂成两个 key） |
| 运行时物化 | `production.py:599`（`spec_digest = content_hash(spec)` 进假设事件载荷）；`storage/artifact_store.py:1-60`（task_id 键＋payload 内容哈希自校验，run 目录内）；`s5b_scoring.py:567-601`（判分侧按 `export_digest` 读回）；读取器缓存 `s5b_scoring.py:563-589`（digest 键，批内） | 全部**批次/run 目录内**物化；跨版本不复用（新批次根）；受影响 spec 的 digest 变化＝预期 |
| 诊断内的记录身份 | `recorded_source.py:1275-1282`（`recorded_source_version`＋计数）、`:1780-1830`（`corpus_v1_sha256`/`n_rows`/直方图） | **文件级事实不变**；计数可随归一变 |

### 1.5 实测基线（v1 只读探针 + v2 算子参数/行为实测；命令见附录 A）

**(a) 记录侧资产字符串分类计数**（类别：`no-op`＝无电荷且已是 canonical（归一后串＝原串）；
`charged`＝含形式电荷；`canon-only`＝无电荷但**非 canonical**（若无条件归一，将被纯重规范化改写）；
`missing`＝空字段；`unparseable`＝0 行）：

| 资产 | 字段 | 行/组分总数 | no-op | charged | canon-only | missing |
|---|---|---|---|---|---|---|
| `assets/v3_reactions/library/library_full.jsonl`（4,454 行） | donor_smiles | 4,454 | 449 | 663 | **3,342** | 0 |
| 同上 | product_smiles | 4,454 | 404 | 655 | **3,395** | 0 |
| `assets/v3_reactions/corpus_env/corpus_v1.jsonl`（43,177 行） | donor_A_smiles | 43,177 | 3,767 | 35,132 | 4,276 | 2 |
| 同上 | product_B_smiles | 43,177 | 3,350 | 34,883 | 4,362 | 582 |
| 同上 | donor_components | 108,551 | 29,131 | 75,144 | 4,276 | 0 |
| 同上 | product_components | 107,971 | 28,714 | 74,895 | 4,362 | 0 |
| `assets/analog/corpus_templates_v1.jsonl`（17,183 行） | mapped_lhs | 17,183 | 4,659 | 12,119 | 405 | 0 |
| 同上 | mapped_rhs | 17,183 | 4,735 | 12,137 | 311 | 0 |

⇒ 两条设计结论：①记录侧**带电串占比高**（analog 模板约 70%、corpus donor_A 约 81%）——
T-E 的"作用面"与"字节漂移面"都不会只限 7 题，必须**全 298 题全量测量**（§5.5）；
②`canon-only` 类**数量级与带电类同阶甚至更大**（EAWAG donor：3,342 vs 663）——**无条件归一
会把大量化学上无变化的串改写**，这正是 §3.1 短路设计的依据。题域标签：298；不外推。

**(b) 语义敏感度与算子实测（v1 探针 + v2 复验，只读）**：
- Morgan r2/b2048：酸式 vs 阴离子 Tanimoto = **0.5**（≠1）⇒ F2 供给（主份选择）电荷敏感；
  召回本身保持原始串（本稿推荐）则召回序不变，F2 可变化须在字节面归因。
- 季铵型永久阳离子：`Uncharger` 为 **no-op**（v1 电荷向量前后一致；v2 复验为"运行算子后按
  同原子状态核无操作"，§4.1）⇒ 短路设计下此类记录零字节漂移。
- `MolFromSmiles` **保持输入原子顺序**，canonical 输出按规范排序 ⇒ EAWAG 通道的 map 号赋值
  （`recorded_source.py:2110-2116` 按 donor 原子 idx）**会因重排而不稳定**——短路设计把该风险
  限制在"applied"（真改动）行内；未 applied 行原串不变 ⇒ map 号不变 ⇒ 字节不变。
- `rdkit 2026.03.6`；`rdMolStandardize.Uncharger()` **构造器签名实测**（v2 新增，
  与评审 operator_execution 记录互证，命令见附录 A）：
  - 构造器 PyDoc/C++ signature 明确三参数默认值：`canonicalOrder=True, force=False,
    protonationOnly=False`（**构造器签名可读**，属 R03 要求的"未显式设置时的默认有效值"之一）；
  - **实例层不可自省**：`dir(instance)` 仅 `uncharge/unchargeInPlace`，三参数 `getattr` 均
    `AttributeError` ⇒ 按"不可读项单列登记"处理，不以文档语义替代环境验证；
  - `neutralize=True` 关键字 **被拒**（`ArgumentError`，C++ signature 只收上述三 bool）——
    **v1 稿的 `neutralize=True` 写法作废**（v2：依据 P1-3/Q9）。
- `applied` 输出**允许保留永久电荷**（v2 新增实测）：一个"可中和的羧酸根阴离子 + 季铵–羧酸根
  永久内盐"混合组分串运行时，第一遍中和羧酸根组分、内盐组分保持±电荷不变，输出串仍带电荷
  ⇒ **"applied ⇒ 输出全无电荷 ⇒ 二遍必 not_applicable"的错误推导删除**（v2：依据 P1-3；详见 §4.3）。
- 无效输入（不完整价态串）`uncharge` 抛 `ArgumentError`（与评审"1 个故意无效输入两遍均 failed"
  互证）；合法构造输入 16 例的成功域双遍字节固定点证据见评审 operator_execution 记录——
  **该证据只覆盖构造输入，批内实际消费串的既定双遍义务仍待实施履行**。

---

## 2. A 面：归一后记录侧字符串流经的身份/缓存/物化面（清单表）

| # | 面 | 证据（文件:行号） | 是否受影响 | 处置建议 |
|---|---|---|---|---|
| A1 | `_LIBRARY_CACHE` | `recorded_source.py:393,427-429,459` | **否**（file-keyed，值＝原始行） | 不改 key；**约束**：归一不得下沉进 `load_library_index`（§3.1） |
| A2 | `_CORPUS_CACHE` | `:471,540-543,610` | **否**（同上） | 同上；CN 检索索引维持原始（检索面零变化） |
| A3 | `_INDEX_CACHE`（analog 三索引） | `analog_source.py:196-257` | **否**（asset-sha-keyed，值＝原始行） | 不改 key；归一位于召回之后 |
| A4 | identity 纯函数 memo | `domain/identity.py:21-43` | 否（纯函数，串 keyed） | 新增 memo 见 §3.4 |
| A5 | `assess_cache`（证据卡侧） | `donor_applicability.py:747-753,833-838,924` | 否（不在 T-E 路径；键为记录 id，form 无关） | 本轮回 "不适用" 登记；若未来接入须并入指纹 |
| A6 | `substrate_feature_cache_key` | `search.py:465-475` | 否（底物侧） | 不动 |
| A7 | `net_reaction_signature` 去重/合并 | `s5b_builder.py:495-500,1436-1461`；固定副本 `s5b_compiler.py:206-233` | **是（间接）**：signature 取 spec 产物严格身份 ⇒ 归一会改受影响的槽合并 | 视为池策略级的**预期语义后果**（version 升号覆盖）；字节面按 §5.3 归因 |
| A8 | 每题 run_id | `s5b_builder.py:343-345` | **否** | 不改；新批次新 batch_tag |
| A9 | run 身份/导出指纹（**v1 论证更正**） | `storage/run_identity.py:76-100,103-112,115-198`；`runflow.py:1859-1876,1997-2005`；**实际导出读取链** `s5b_scoring.py:584-587`→`native_export.py:180-191,600-616`；v1 所引 `output/export_v3.py:845,869-871` 为 legacy 路径 | **部分**：改码 ⇒ code_identity ⇒ 指纹变 ⇒ 旧 run **resume** 拒续；**但旧导出/旧输入不自动失效**——既有机制只保证启动后的身份，不证明 build 出处（v2：依据 P1-1） | 不动既有机制；受控批新增 §3.6 build→首次消费绑定；E1 批次登记新 HEAD |
| A10 | run_inputs 字节（`plan.pools`） | `s5b_builder.py:351-374,1627-1633` | **是（受影响题）**：spec 增/改/删＋spec 内嵌记录侧串（`compile.record_products :2279`、corpus `matched_component :1735`（raw）、analog participants/`record_equation :1357-1359`（raw）） | 分题归因（§5.3）；未发生改动题**零字节**（短路设计保证）；受控批另绑逐输入字节 sha（§3.6） |
| A11 | batch_manifest（entries/诊断） | `s5b_builder.py:1634-1647` | **是（受影响候选）**：`pool_size`、`pool_diagnostics.candidates` 行（`signature_head :1065-1067`、`execution_input_sha256 :1216-1217/:1269`、`route/f5/reason`、**v2 新增三值+trace 审计字段**）、计数与直方图 | 对拍**分两层**（§5.3）：旧字段投影（除版本键）逐键对照；**新审计字段正确性另验**；`substrate_smiles`/图 sha 不变 |
| A12 | spec 身份键 | 固定副本 `s5b_compiler.py:1414-1426`；`s5b_builder.py:1238-1245` | **否**（record-id based，无内容哈希） | 不动；披露"归一不改 spec 身份" |
| A13 | 运行时物化（spec_digest/产物/判分读回） | `production.py:599`；`artifact_store.py:1-60`；`s5b_scoring.py:567-601` | **是（内容派生）** | 批次内闭合；无跨版本复用面（新批次根） |
| A14 | 诊断内文件级身份 | `recorded_source.py:1275-1282,1780-1784` | **否**（library/corpus sha、行数不变） | 不改 |
| A15 | **build 身份/输入字节绑定（v2 新增）** | `s5b_builder.py:351-374,1634-1647`（现无）；`s5b_worker.py:70-74,215-229`（现不核） | **是（新设计面）** | 受控批 manifest 旁块绑定 + worker/公共批首消费核对（§3.6） |

**A 面一句话**：**缓存全在文件/资产哈希侧，归一是内存变换 ⇒ 无 key 需要改；真正要设计的是
"哪些字节面允许变、怎么归因、未变面怎么证明"（§5 对拍合同）＋"build 出处怎么绑定"（§3.6）。**

---

## 3. B 处置设计（推荐一套；备选取舍点写明）

### 3.1 ①源资产不改动 + 内存变换 + 统一消费视体（v2：依据 P1-2/Q1/Q5）

- 归一**不得**写回任何资产文件、**不得**下沉进 `load_library_index`/`load_corpus_index`/
  `_INDEX_CACHE` 的构建（A1–A3）；这些缓存的值保持**原始行**，key 保持文件/资产 sha。
  ⇒ 同一进程内无论哪个臂（短路/归一）消费缓存，拿到的都是同一份原始索引；**归一版本变化
  不会产生陈旧复用**（缓存里从来没有归一态）。**值不可变承诺（评审 P2 登记随修）**：
  新增/局部视体一律**写时复制**（新列表、新局部 view），不在原地改缓存返回的原始行对象；
  同进程 A-B-A / B-A-B 与缓存内容 hash 对拍核既定承诺。
- 注入点（推荐口径；未 applied 行对编译器输入**零差异**，compiler 判据零改动）：
  - **recorded（EAWAG）**：在 `compile_recorded_reaction` **函数入口**对全部记录侧入参
    （`donor_smiles`、`products`、`record_products`、`declared_copies` 及其派生成分）过同一算子，
    然后走既有 `:2095` 起的全部逻辑（映射/构建/gate 同域）；**tier 判定（`find_*` 内）保持原始串**
    （§1.2 第一行；身份面零触碰＝硬约束，评审 §3.2；归一后相等不得改名 strict exact，不改底物
    strict/CN 定义，真实产物另按既有 strict 独立验证）。
  - **corpus**：**候选识别之后、分类之前**（`ordered_matches` 装配完成、进 `_classify_cosubstrate_candidate`
    之前）建立**每候选消费视体**，贯穿分类（`:1483` 调用点的 `matched_side`/`co_comps`/
    `flat_products`）、编译（`:1519-1525`/`:1708-1712` 入参）、装配（`:1862-2023`/`:2026-2057`）与
    **NC-10 两处声明**（`:1957`/`:2021`）；`matched_component` 与候选 detail 的来源字段保 raw（§1.2）。
    **公共 compile 直接入口不留旁路**：`compile_recorded_reaction` 入口同样过算子——视体输入二次
    过算子＝成功域固定点（第二遍无操作，§4.3），不发生二次变形（v2：依据 P1-2）。
  - **analog**：在 `_compile_analog_refs` 的 `for ref in refs` 起点（`:1273-1275`）生成"归一视体"，
    **该循环内所有记录侧消费者（F1/F2/F3/F5/编译/spectators/light_gap）一律读视体，raw ref 不得
    再传编译**（v2：依据 P1-2）；**`record_equation` 保持原始串**（来源例外，Q3 终裁）。
    召回（`:1414-1415` 与降阈值第二次召回 `:1424-1430`）与去重阈值逻辑不变。"视体"必须保留
    atom map 号（实现要求：`GetMolFrags(asMols=True)` 逐组分 `uncharge` 后 `MolToSmiles`（保留
    map/立体）再按**输入组分序**点号重接）。
- **短路（实测无操作直通；v2：依据 Q1/Q2 裁定改写）**：对每个记录侧串**先实际运行默认算子**；
  随后按**同一原子对应**核 q/H、重原子图、键、map、同位素、立体（任一变化即"有操作"）。
  仅当全部未变 ⇒ **输出原串直通**（成功无操作 ⇒ `not_applicable`）。**不得**以"电荷向量不变"
  断言全部原子状态不变（v1 的证明过强，评审 §2-Q1）；也**不得**据"图等价/元素多重集不变"
  宣称与来源实验的无条件 canonical 臂在字节/枚举结果上恒等——来源锚对账由实施臂另行做
  （F:309–312；评审 §3.1）。理由与实证：§1.5(a) `canon-only` 类巨大，无条件归一将把化学无变化
  的串重写并连带 map 号/字节漂移；短路把"字节差面"收敛为"算子实际改变化学状态"的行，使 §5.3
  的归因与负控可机械成立。（备选：无条件归一——与来源实验臂字面一致，但字节面≈全库重规范化；
  若复审选择无条件，探针须把 `canon-only` 漂移面按 record_key 全量披露并另设负控。）
- **组分序（v2：依据 Q5 采纳）**：保输入组分序与重复份数，不跨组分排序；applied 组分内部重排
  保原子对应；成功无操作保原串。
- **不提供生产臂开关**：T-E 即新池策略语义（policy-9），不做运行时 `formnorm=False` 参数
  （防静默消融）；差分探针的恒等臂**不是实现内开关**（其自证义务见 §5.3——同树 monkeypatch
  恒等**不能**自称旧基线）。

### 3.2 ②归一算子版本化（真实参数 + 指纹；v2：依据 P1-3/Q9，删无效参数写法）

- 新常量（单一实现源模块；建议落 `recorded_source.py`（record side 归属；builder 已 import 该模块））：
  - `RECORD_SIDE_FORMNORM_VERSION = "record-side-formnorm-1"`
  - `RECORD_SIDE_FORMNORM_PARAM_SHA256`：指纹口径照 FROZEN_V3 §3 条 3 / §8 登记规范，
    内容 = sha256(canonical_json({
    `operator`: `"rdMolStandardize.Uncharger"`；
    `constructor_call`: `"Uncharger()"`（默认构造；**不传任何关键字**——`neutralize` 等关键字
    在该版本不存在，传即 `ArgumentError`，v1 写法作废）；
    `constructor_defaults_from_signature`: `{canonicalOrder: true, force: false,
    protonationOnly: false}`（**构造器签名实测登记**；v2 实测：PyDoc/C++ signature 可读这三默认值）；
    `instance_introspection`: `"unavailable"`（实例仅 `uncharge/unchargeInPlace`；三参数 `getattr`
    均 `AttributeError`——**不可读项单列**，不以文档语义替代，也不因不可读免掉已可取得的三默认值）；
    `application`: `"per-component(GetMolFrags,asMols=True)→ 逐组分算子 → MolToSmiles(保留map/立体)
    → '.'按输入组分序重接"`；
    `serialization`: `"MolToSmiles 默认(isomericSmiles=True)；不额外 canonical 排序组分"`；
    `noop_rule`: `"先实际运行算子，再按同一原子对应核 q/H、重原子图、键、map、同位素、立体未变
    ⇒ 成功无操作，直通原串"`；
    `transaction`: `"一次候选消费视体原子提交（任一分量失败全部回原始）"`；
    `rdkit_version`: 实测串（本环境 `"2026.03.6"`）}))
- **不更换算子**（评审 §P1-3 要求动作）：短路/事务都基于**默认** `Uncharger()` 实跑，不得改用
  `force=True` 等另一构造参数组合替代短路判据。
- 绑定纪律：算子/参数/短路规则/序列化/事务策略任一改动 ⇒ `RECORD_SIDE_FORMNORM_VERSION` 升号
  **且** `S5B_POOL_POLICY_VERSION` 升号（§3.3），二者在批诊断里同时输出（机读，不靠文档标签——
  先例 `corpus_diagnostics` 的 R31-4 纪律 `recorded_source.py:1789-1792`）。

### 3.3 ③池策略版本升号与版本绑定（v2：依据 Q8；评审 §3.3）

- `S5B_POOL_POLICY_VERSION`（`s5b_builder.py:477`）：`"s5b-pool-policy-8" → "s5b-pool-policy-9"`。
  理由：池**成员/诊断面**变化（既有先例逐条登记于 `:380-476`：s5b-pool-policy-N 的升号判据即
  "池成员变化 ⇒ 按既有身份规则升版"）。
- **同批升号**（v2 定案，不再留二选）：
  `RECORDED_SOURCE_VERSION`（`recorded_source.py:180`）`"s5b-recorded-source-3" → "-4"`
  ——公共 compile 默认输入的核验域与 spec 会改变，source-3 不能静默解释成已有归一；该常量随
  `find_recorded_exact` 诊断输出（`:1276`）与 corpus 诊断（`:1781` 区域）一并出。
- **保留但绑定上下文**：`S5B_ANALOG_ROUTE_VERSION`（`s5b_builder.py:492`）保留 `"s5b-analog-route-f1f4-1"`
  ——**F1–F4 分支公式/算法未改**，但该版本串的解读上下文随输入域改变：**路由结果可变**（输入串
  变了，同一公式可给出不同分支），批次诊断必须**同输出 `RECORD_SIDE_FORMNORM_VERSION` +
  指纹**（机读绑定），且表述一律写"**路由算法未改**"，**不得**写成"路由结果不变"（评审 §3.3；
  P2 术语纪律，v2：依据 Q8）。
- **不动**（FROZEN_V3 §8 明列）：`PPV1_EVALUATION_VERSION`（`profile.py:396`）、
  `EDIT_PROTOCOL_VERSION`/`ATOMETOOL_VERSION`（`services/atom_tool.py:63,71`）、
  `S5B_COMPILER_VERSION`（固定副本 `s5b_compiler.py:125`，本设计不动编译器——判分语义与
  编译判据均不动）、criteria V1/V2/V3 路径。
- 批次纪律：新 batch_tag + 新批次根；旧批零回写（AGENTS 红线）；run_id 机制不动（A8）。

### 3.4 ④缓存 key 是否并入归一卷版本（逐项判定；v2 补充值不可变）

| 缓存 | 判定 | 依据 |
|---|---|---|
| `_LIBRARY_CACHE`/`_CORPUS_CACHE`/`_INDEX_CACHE` | **不并入**（key 不加归一版本） | 值为原始行、key 为文件/资产 sha（§1.3）⇒ 归一无物可失效；并入反而把"原始索引"错误标成"归一产物" |
| 缓存值不可变 | **写时复制承诺** | 新列表/局部 view 不原地改缓存（评审 P2 第 1 项随修登记）；同进程 A-B-A/B-A-B 与缓存内容 hash 核承诺 |
| 若未来新增"归一后索引/去重表"类缓存 | **必须并入**（key 追加 `RECORD_SIDE_FORMNORM_PARAM_SHA256`） | 先例：`analog_source.py:265-267` 把 `SIMILARITY_VERSION` 并入 fp 索引键（"跨版本缓存不串用"） |
| 若新增归一转 memo（lru/字典） | key 必须含 `(指纹, 原串)`；或按臂构造独立闭包 | 串 keyed 纯函数 memo 仅在"同进程单版本"下安全（`domain/identity.py:26-37` 属此类）；一旦支持同进程双臂对照（探针/测试）即会串用 |
| "以记录字符串为 key"的既有缓存 | **本仓现状：无命中**（§1.3 全表逐条已核） | 若复审发现遗漏面，按"并入指纹"处理 |

### 3.5 ⑤per-candidate 可追溯（披露落点；审计合同全部口径见 §5）

- **三值标签**（FROZEN_V3 §5.2 C-5：`record_side_form_norm ∈ {applied, not_applicable, failed}`）：
  落 **`pool_diagnostics.candidates` 行**（`_diag_row :1069-1100`；行 schema 为"向后兼容追加"先例
  `:1079-1087`）。recorded/corpus 通道候选行同样追加（`:1143-1149`/`:1175-1181` 调用处），
  行键 `record_key` 即追认锚。analog 行键＝`tpl-<rid>`（`:1265`/`:1298`）。
  批级输出：`record_side_form_norm_version` + `record_side_form_norm_param_sha256`
  （随 `pool_diagnostics` 顶层，`:1472-1560` 处）。
- **全形态覆盖（v2：依据 P1-4）**：compiled、compile_rejected、merged_into、pool_truncated
  **四态行全部**保留归一事件三值与 trace（不能只从成功 spec 回填；四态行 schema 先例
  `s5b_builder.py:417-420`）。
- **逐行原子级 trace（C-5 补齐承诺）**：applied 行追加被改原子明细与 trace（坐标口径、
  q/H 分列、风险交集、unknown 语义——**全部写死在 §5.1**）。
- **spec 侧披露（条件性，保字节面）**：**未 applied 行 spec 零改动**；applied 行在
  `spec.compile` 条件性追加 `record_side_form_norm`（status/version/param_sha256/trace_ref）
  与 `verification_domain: "normalized_record_side"`；`verified_product_set` 的证明域明示
  （§5.2）。
- **原始串可追认性论证**：原始记录串 = 哈希锚定源资产（library sha 于 `:427`；corpus sha 于
  `:540-541`、诊断输出 `:1783`；analog 资产 sha 于 `DonorRef.asset_sha256 :80-92`）+
  `record_key`/`record_id` **可机械重读**；spec/诊断里的归一后串是"消费态"。⇒ 不需要在 spec
  里复制原始串；来源声明面（`record_equation`/`matched_component`）保持 raw 不在此列。

### 3.6 ⑥build→首次消费绑定设计（**v2 新增：依据 P1-1**）

**问题（评审 P1-1 证据）**：`build_run_input`（`s5b_builder.py:351-374`）只落
qid/run_id/substrate/plan/note；落文件与 manifest（`:1627-1647`）**不绑定输入字节 sha 与构建
算子身份**；worker 读盘 plan（`s5b_worker.py:70-74`）→ run 不存在即 start（`:215-229`）→
此时才登记当前源码身份（`runflow.py:1859-1876`）。`code_identity` resume 门（`run_identity.py:76-100`、
`runflow.py:1997-2005`）只拒既存 run 跨代码续跑，**不能证明输入在首次 start 前由当前代码构建**；
合成探针已证实**旧输入可被新代码首次 start 接纳并登记新身份**。加之旧导出无自动失效机制
（§1.4 更正），"启动后登记身份"与 `batch_tag` 都**不能**充当 build 出处证明。

**设计（受控批强制；通用无批 scripted start 不要求）**：

1. **批级 build 身份块（旁块，不升级 native-export schema）**：受控批在批根新写
   `build_identity.json` 旁块（或等价并入 `batch_manifest.json` 顶层块；二选一在实施任务书定，
   内容相同）。字段：
   - `code_identity_aggregate_sha256`：`storage/run_identity.code_identity(profile=
     "pollutant_pathway_v1")` 的 `aggregate_sha256`（单一实现源复用；逐文件映射可选携带）；
   - `pool_policy_version` / `recorded_source_version` / `corpus_retrieval_version` +
     `formnorm_version` + `formnorm_param_sha256`；（v2 值预记：`s5b-pool-policy-9`、
     `s5b-recorded-source-4`、`record-side-formnorm-1`）
   - `route_version`（`s5b-analog-route-f1f4-1`，附"路由算法未改"注记）；
   - `compiler_version`（`s5b-compiler-4`，判分/编译判据不动）；
   - `rdkit_version`（跨 RDKit 版本 canonical 可变，须入绑定）；
   - `asset_identity`：复用 `retrieval_asset_identity`（`run_identity.py:40-64`；manifest_sha256 +
     library/corpus/analog 各文件 sha）；
   - `run_inputs`：逐 qid 一条 `{qid, run_id, run_input_sha256（该 run_inputs/<qid>.json 原始
     字节 sha256）, substrate_sha256}`。
2. **首次消费先核对（worker/公共批，在创建 run/调用模型之前）**：
   - 读盘 run_input 原始字节 → sha256 必须等于旁块记录值（缺键/缺文件/字节不符 ⇒ 结构化拒）；
   - 旁块 build 身份 vs 当前运行时逐字段核（代码聚合、各版本与指纹、RDKit、资产身份）；
   - 全过 ⇒ 放行 start/resume；拒 ⇒ 新结构化 `failure_kind`（如 `build_identity_mismatch` /
     `run_input_bytes_mismatch`，命名在实施任务书按本口径定），**失败题留分母、零发送、不建 run**。
   - 核对放置点在现有 worker 前置检查序列内（同 `s5b_worker.py:93-201` 的 fail-closed 先例风格：
     拒因写 case、返回非零、不触模型），并在**任何** run 创建/模型调用之前。
3. **绑定进 run 来源**：核对通过后，把 `{build_identity_fingerprint, run_input_sha256}` 写入该
   run 的来源记录面（案例 case / ledger provenance 块之一；**不改 `run_identity.json` schema**，
   不靠"start 时登记当前源码"充当出处证据）。
4. **正式批拒复策略**：受控正式批遇到**旧/缺/损坏/错版本**的输入或旁块 ⇒ **拒并新 build**
   （新批次根 + 新 batch_tag 重出旁块与 run_inputs）——**不得**靠新 batch_tag 改名或启动后
   登记身份"洗白"旧输入（v2：依据 P1-1 要求动作原文）。
5. **范围预算（评审边界）**：可放批侧实施以保**未 applied 输入可比**（旁块只加不拦旧批只读）；
   不要求所有通用无批 scripted start 加新协议；不要求升级 native-export schema；不要求拒绝
   所有历史导出（历史导出保合法固定事实重判，§5.4）。
6. **与缓存 key 面的关系**：本绑定是**批级旁块 + 首消费核对**，不给任何既有缓存加 key
   （§3.4 判定不变）；旁块自身即"输入字节缓存 key"的显式化（sha 钉死）。

---

## 4. C 事务合同、fail-closed 与幂等（v2：依据 P1-3/Q2/Q6/Q7，整体改写）

### 4.1 三值语义（按提交事务状态，不按字符串或净电荷）

- **`applied`＝事务成功提交的原子化学状态改变**（成功运行算子 + 事务提交 + 同一原子对应下
  q/H/重原子图/键/map/同位素/立体**任一改变**）。**不是**比较净总电荷，**不是**比较输出字符串；
  `canon-only`（无电荷但非 canonical、算子状态无操作）**不得**记 applied。
- **`not_applicable`＝成功无操作**：**必须先实际运行默认算子**，再按**同一原子对应**核
  q/H、重原子图、键、map、同位素、立体**全未变**，才认成功无操作并**直通原串**（v2：依据 Q1；
  v1"电荷向量不变便足证"作废——序列化顺序可影响映射与枚举，R:2110-2123、固定副本 C:653-668）。
  **不更换为 `force=True` 等另一算子**。
- **`failed`＝未提交并完整回滚**：任一组分不可解析/算子异常 ⇒ 该候选**整消费视体回原始**，
  标签 `failed` + 机读原因（如 `component_unparseable`/`operator_exception`）；下游编译按既有
  判据照常出拒（`record_donor_unparseable` 等，`recorded_source.py:755-764`）。
- **失败处置=原串直通＋`failed` 披露，不拒候选**（v2：依据 Q6 采纳）：FROZEN_V3 §3 条 2
  "fail-closed＝不授归一"，对 T-E 的解释是**不授归一收益**（该字段），**不是**移除候选；
  也不新增"一律拒候选"规则，不继续享用另一字段成功归一的收益（整候选粒度见 §4.2）；
  原始编译仍按既有门运行。（备选"失败即结构化拒"会改既有池成员，须单独预注册，不推荐。）

### 4.2 事务单位＝一次候选消费视体（v2：依据 Q7 改写）

- 一次归一的**事务边界＝该候选的完整消费视体**：`donor/lhs`、`rhs/products`、`copies`、
  `full_products`（记录全量产物）、**派生供给及装配字段**（供给清单、spectators、participants/
  states、NC-10 声明输入）——**全量原子化**。
- **任一分量失败 ⇒ 全部回原始**（不是单串回退；v1 的"单串 all-or-nothing"作废）。
- **保留 None、空列表、顺序、重数的既有区别**：回退与提交都不得把 `None` 与 `[]`、空集与缺键、
  多份与单份、原序与排序混写（`s5b_builder.py:1219-1258` 共同消费 lhs/rhs；`recorded_source.py:2061-2064`
  一次消费多个列表）。
- **幂等（可测断言）**：成功域 `norm(norm(s)) == norm(s)`（**字节级**）；failed 域**确定性重现
  failed 且原串不变**（同串两遍均 failed、两遍输出均＝原串）；not_applicable 输出＝原串（平凡固定点）。

### 4.3 双遍合同（v2 更正；删除 v1 错误推导）

- **成功域（applied）**：**双遍字节固定点**——对第一遍输出再运行算子，**第二遍无新增改动**，
  输出与第一遍**逐字节相同**。第二遍的标签按 §4.1 实测判定（若输出仍有状态可再变，则说明该串
  不满足固定点 ⇒ 属合同违例，须出结构化证据行，**不得静默**）。
- **failed 域**：确定性重现 failed 且原串不变（§4.2）。
- **applied 输出允许保留永久电荷**（v2 实测反例：可中和羧酸根 + 季铵–羧酸根永久内盐混合组分串，
  第一遍中和可中和组分、内盐组分原样保留 ±电荷）。⇒ **删除 v1 的"applied 输出＝无电荷
  canonical ⇒ 二遍必 not_applicable"推导**——applied 与"输出无电荷"不构成等价，第二遍标签
  由实跑判定，不强制改标签换通过（评审 §P1-3）。
- v1 已登记的实施义务保留：E1 实施轮须对批内**全部实际消费**的记录侧串跑双遍断言（计数入报告）；
  16 个合法构造输入的双遍证据（评审 operator_execution）**只作局部证据**，不代表批内全量。

### 4.4 重复消费无差异与确定性

- 同记录多题复用（缓存命中 `_LIBRARY_CACHE`/`_CORPUS_CACHE`）恰因缓存存原始行、归一是
  **无状态纯函数（串→串）** ⇒ 同串同果；若加 memo 见 §3.4 键纪律。
- 归一结果只依赖单串 + 指纹（无全局状态、无枚举序依赖）；重排（组分序）按 §3.1 固定口径
  （保输入序，Q5）。

---

## 5. D 审计 / 对拍可验合同（v2：依据 P1-4/Q10/Q11，整体重写）

### 5.1 逐候选审计与 trace 坐标合同（v2：依据 P1-4/Q11）

**覆盖范围**：`pool_diagnostics.candidates` 的**全形态**行（compiled / compile_rejected /
merged_into / pool_truncated）**均**保留该候选的 `record_side_form_norm` 三值与其 trace /
原因——不从成功 spec 回填、不因合并/截断丢归一事件。

**trace 坐标系（写死，实施不得另立）**：每条"被改原子"一行，坐标字段固定为

| 字段 | 语义 |
|---|---|
| `side` | 侧（记录侧内：donor/lhs 侧 或 products/rhs 侧） |
| `field` | 来源字段/串（如 donor 串、某产品组分串、copies 串；analog＝mapped_lhs/mapped_rhs） |
| `component_index` | 组分序（保输入序；与装配多重集同序） |
| `original_idx` | 该组分**原始串**内原子 idx（`MolFromSmiles` 保输入序） |
| `origin_map`（可选） | analog 行原始 map 号（有则填） |
| 对应关系 | **源 idx → 归一 idx → 生成 map 号**的逐原子对应（recorded/corpus：源原子 idx → 归一后串原子 idx → `:2110-2116` 生成 map；analog：源 map 号 → 归一后 map 号） |

仅凭 `record_key` 不能消歧（R:1427-1437 允许同源记录的不同匹配侧各成候选）——trace 必须
逐候选可定位到侧/字段/组分/原子。

**q/H 分列与 H 口径**：`Δq`（形式电荷变化）与 `ΔH` **分列**；**H 口径定义**＝同一原子对应下
`GetTotalNumHs()`（显式+隐式氢总数）的变化；涨/失氢与电荷增减分列落账（FROZEN_V3 §5.2 C-5；
R06）。

**「过度对齐风险」交集（写死）**＝**实际消费的查询/匹配原子** ∩ **同坐标 lhs 改动原子**
（非空 ⇒ 登记风险行）。**注意坐标事实（评审 §2-Q11）**：固定副本 `build_center_query:621` /
`enumerate_center_alignments:653`（消费 `:1234-1235`）的中心查询**仅覆盖 lhs 子集**
（`qidx_of_map` 覆盖 L1+壳层查询命中原子），F5/中心枚举**不返回完整匹配原子集** ⇒ 交集只在
"实际消费的查询/匹配原子"内计算，**不得**按"整侧 lhs 全命中"伪算；rhs 侧另列（不并入 lhs 交集）。
grep 确认审前 src 无 `enumerate_template_alignments`（§1.1 更正），交集口径不得复用旧函数语义。

**unknown 语义（不得伪填 risk=false）**：无法追溯（trace 坐标缺失/对应不可建立）、无匹配
（该候选零对齐）、截断（枚举触顶）**各给机读原因或 `unknown`**；`risk=false` 只在"交集已计算
且为空"时允许。

**人工复核义务**：风险行清单（含 unknown 行）逐批输出并交人工复核（FROZEN_V3 §5.2 C-5）；
风险行**不作机制证明**（不据此宣称化学可行性/整侧对齐正确）。

**来源例外面的披露**：`record_equation`/`matched_component` 保持 raw（§1.2）；applied 时**另**
披露消费态与其 trace，并标明**它不是归一后严格身份声明**（Q3/Q4 裁定；覆盖 whole `:1735`
与 component `:2002` 两装配分支）。

### 5.2 spec 条件披露与证明域合同（v2：依据 P1-4/Q10）

- **仅 applied 行**在 `spec.compile` 条件性追加：`record_side_form_norm`（status/version/
  param_sha256/trace_ref）＋ **`verification_domain = "normalized_record_side"`**（固定字符串，
  写死）。**未 applied 行 spec 零改动**。
- **`verified_product_set=True`（`recorded_source.py:2280`）证明域明示**：该布尔只核**消费态归一
  记录**产品集（strict 键多重集在归一后记录域内一致），**不冒充**原始资产完整离子身份通过
  strict——条件元数据随行明示证明域（如 `verified_product_set_domain: "normalized_record_side"`；
  命名按本口径在实施任务书定，**不得省略证明域表述**）。
- **诊断新增 ≠ 版本键**：新审计字段（三值/trace/风险）**不是**版本号，**单独验收**（§5.3），
  不得通过"扩大排除键/把整诊断当新增版本块"掩盖漂移（评审 §P1-4）。

### 5.3 对拍两层合同与 A 臂等价证明（v2：依据 P1-4/Q10）

**方法学沿用**：差分双 build 探针（先例 `reports/ppv1_s5b/t_g_fix_2026-10-19/c1_readback/byte_invariance_probe.py`
与 `reports/ppv1_s5b/c2_impl/r2p_byte_invariance_probe.py`；隔离 tmp 执行、`PYTHONDONTWRITEBYTECODE=1`、
`-B`，`VERSION_KEYS` 排除结构与"逐字节＋诊断分组对照"结构可参照）。

**A 臂（旧基线）自证义务（更正 v1）**：v1 把"同树 monkeypatch 归一回恒等"直接称 policy-8 旧基线
——**不成立**（同树还带着其它新增接线/装配/披露差异）。v2 合同：**A 臂必须先证明与 pre-T-E 旧树
等价**（对全 298 题 run_inputs 与诊断旧字段投影逐字节），**或直接使用旧树/新树两棵树对比**
（旧树＝T-E 实施前 HEAD 记录、新树＝实施后）——两种方式**任一落实**才可称"旧基线"。

**对拍两层（分别验，不混）**：
- **第 1 层：旧字段投影不变（未 applied 题）**——该题全部被消费记录侧串三值 ∈ {not_applicable,
  failed}（短路直通）⇒ `run_inputs/<qid>.json` 逐字节相等；`pool_diagnostics` **旧字段**（s5b-pool-policy-8
  时点 schema）除**版本键**（`pool_policy_version`、`recorded_source_version`、新增 formnorm 键）
  外逐键相等。任何漂移 ⇒ **停**（drift≠0 即停）。
- **第 2 层：新审计字段正确性（另验）**——三值/trace/q/H 分列/风险交集/unknown 语义按 §5.1
  逐条验收（含全形态行覆盖、坐标可定位、risk=false 合法性）；**不得**把新字段当版本键整块排除。
- **受影响题**（至少 1 串 applied）：允许差异，但**每一差异须归因**：差异形态 ∈ {spec 新增/
  内容变更/移除/诊断行字段变更}，每条挂到具体 `record_key`（或 `tpl-<rid>`）与其 applied 事件；
  失败/无操作题保持未改 spec/输入；**新产生的对齐恢复候选**与 E1 前置 1 重算账分通道对账
  （口径差如实披露——C1/C2 对齐判据替换属已登记变量）。
- **"预期变化"与 C1/C2"非目标题字节不变"的区分（保留）**：T-E 是池策略级变量，版本键必然变、
  受影响题允许变；不变性压在"未发生归一事件的题"且须**机制可证**（短路：无状态改变 ⇒ 串逐字节
  同 ⇒ spec/诊断同）。
- **隔离与证据纪律**：探针在隔离目录执行、不改封存资料、记录实际 HEAD/输入哈希（AGENTS
  「审核证据在隔离目录执行」）。

### 5.4 N10 固定事实对拍（v2：依据 Q8；评审 §3.4）

- **固定对象**：同一批**不可变事件、产物、参考事实、导出及 criteria 版本**（含 v1 与显式 v2
  分开），**钉输入哈希**；旧/新实现逐事件核 **strict 布尔、身份/参与物判据及原因**——**只比总
  命中数会掩盖交换，不足**。
- **新池另列**：policy-9 的候选/事件面与旧池**可以不同**，其 strict/hit 变化**另表归因**——
  既不能要求不同事件总数必同，也不能拿"池策略级"豁免 N10（评审 §3.4）。
- **N3/N7 正交（保留）**：V2 豁免面固定**同 payload** 比（F:241/287/377-378）；不要求"不同新事件
  的 v2 总计数恒等"。
- **历史原事实**：合法只读重判与禁止旧产物冒充 policy-9 新产物**并不冲突**——历史导出保合法
  固定事实重判（§3.6 范围预算第 5 条），但不得以历史产物充当 policy-9 出数。

### 5.5 附加义务（E1 实施轮报告必须含；v2 更新）

1. 全 298 题**穷举**受影响/未受影响清单（qid 头哈希定位）与差异归因表；**不得以"7 题目标面"
   代替全量测量**（§1.5(a)）。
2. 归一事件计数：`applied/not_applicable/failed` 三值分布（按通道分列）＋ trace/风险行计数；
   「过度对齐风险」信号行清单（含 unknown 行）交人工复核。
3. 幂等双遍断言结果（§4.3）：成功域字节固定点计数 + failed 域重现计数；同批 repeated-substrate
   复用（`_LIBRARY_CACHE` 命中）下的字节一致。
4. 非目标面负控：未受影响题的**旧字段**诊断（`signature_head`/`execution_input_sha256`/`route`/`f5`）
   逐键相等（比 run_inputs 更敏感的漂移探针面）；**新审计字段按第 2 层另验**（§5.3）。
5. 与 E1 前置 1（缺口 5 重算）的锚对账：池变化面（新增/变更 spec）与重算的 P3/P4 逐行账
   交集/差集；**P4 背离表**沿用前置 1 口径。
6. N10 按 §5.4 出对照（固定同批同事实逐项 + 新池另表）。
7. 旧批零回写、新批次根、新 batch_tag、新 HEAD 记录；受控批 build 旁块与首消费核对证据
   （§3.6：核对命令、逐 qid 输入 sha 对拍表、拒例合成负控）。

---

## 6. Q1–Q11 复审裁定与 v2 落点（v2：依据评审 §2 逐条裁定）

> v1 的"本稿倾向"列已被裁定取代；下表为**裁定结果 + v2 落点**（Q3/Q4/Q5/Q6＝采纳原倾向，
> 也在此落字明确）。

| # | 裁定 | v2 落点 |
|---|---|---|
| Q1 短路 | **改写**：先实际运行默认算子；按同一原子对应核 q/H 及重原子图、键、map、同位素、立体未变才认成功无操作并直通原串；不得据图等价宣称与来源无条件 canonical 臂字节/枚举恒等，实施臂另行对账 | §3.1（短路改写）、§3.2（noop_rule 入指纹）、§4.1 |
| Q2 applied 判据 | **改写**：applied＝事务成功提交的原子化学状态改变（非净电荷、非字符串）；not_applicable＝成功无操作；failed＝未提交并完整回滚；canon-only 且状态不变走 not_applicable | §4.1、§4.3 |
| Q3 record_equation | **采纳原倾向**：固定 raw 供记录方程与出处；消费视体供路由/编译/供给/spectator；明确"一律读视体"的例外＝record_equation（保原始条目、侧、重数）；N3/N7 固定同 payload 比 | §1.1、§1.2、§5.1、§5.4 |
| Q4 matched_component | **采纳原倾向**：保 raw；applied 时另披露消费态/trace，标明非归一后严格身份声明；覆盖两装配分支；实际 `co_substrates`/copies/`record_products` 依同一消费域装配 | §1.2、§3.1、§5.1 |
| Q5 组分顺序 | **采纳原倾向**：保输入组分序、重复份数，不跨组分排序；applied 组分内部重排保原子对应，成功无操作保原串 | §3.1、§4.4 |
| Q6 失败直通 | **采纳原倾向**：任失败整候选回原始并记原因；不新增"一律拒候选"；不享另一字段收益；原始编译仍按既有门 | §4.1 |
| Q7 all-or-nothing | **改写**：事务单位升为一次候选消费视体（donor/lhs、rhs/products、copies、full_products、派生供给及装配字段）；任一分量失败全部回原始；保 None/空列表/顺序/重数 | §4.2 |
| Q8 N10 与版本 | **改写**：选定 pool-policy-9、recorded-source-4；route-f1f4-1 保留但绑定 formnorm 版本/指纹、注明路由结果可变、算法未改；compiler-4 及判分语义不动；N10 固定同批同事实逐项对拍、新池结果另列；补 build→首次消费绑定 | §3.3、§3.6、§5.4 |
| Q9 参数指纹 | **驳回原倾向，替代口径明确**：默认调用仍 `Uncharger()`；构造器签名三默认值（canonicalOrder=true/force=false/protonationOnly=false）实测登记；实例不可自省单列；`neutralize=True` 写法删除；逐组分/序列化/短路/事务策略及 RDKit 入指纹 | §3.2、§1.5(b) |
| Q10 披露/零字节 | **改写**：逐候选三态与 trace 落诊断；成功 spec 仅 applied 条件加 status/version/hash/trace_ref 及 `verification_domain=normalized_record_side`；未 applied spec 不改；旧诊断字段投影不变、新审计字段另验；A 恒等臂先证等价旧树 | §5.2、§5.3 |
| Q11 原子追踪/风险交集 | **改写**：本设计轮定同一坐标（侧/字段/组分序/原始 idx/可选原 map + 源 idx→归一 idx→生成 map 关系）；q/H 分列并定 H 口径；取实际消费查询/匹配原子 ∩ 同坐标 lhs 改动原子；rhs 另列；无法追溯/无匹配/截断各给原因/unknown，不得伪填 risk=false；风险行交人工复核 | §5.1 |

---

## 7. 残余事项与送复审提示（v2）

1. **本轮回修范围**：四组 P1 + Q1–Q11 已逐条落字（§修订记录 对照表）；无新增开放问题。
   复审关注点建议按评审 §5 口径表逐行核对 v2 节（对照表见「修订记录（v2）」第 7 条）。
2. **并发声明**：`s5b_compiler.py` 与部分 tests 在回修期由另一子代理并行改（D1.2 compiler-4→5）；
   本稿编译层行号/行为全部锚定评审固定副本（compiler-4），**不引用 compiler-5 新行为**；
   复审若需对齐新树，须先固定副本口径再比。
3. **实施前仍待用户/复审确认的工程选择（非阻塞 P1）**：批旁块文件名与结构化拒因命名
   （§3.6 第 1/2 条给了口径，具体字符串交实施任务书）；spec 条件披露字段名按 §5.2 口径定名。
4. **既有登记（非本轮 P1，随修保持不扩边）**：P2 三项（缓存写时复制已在 §3.4 落字；术语与版本
   注释已随 P1 统一；执行强度边界已写入 §1.5/§5.5——16 合法构造仅局部证据）。
5. **叙事纪律**：全稿术语统一——「归一收益／来源声明／消费态／独立 strict 验证」；route 只写
   "路由算法未改"，不写"路由结果不变"。对外数字全部带 298 题域标签，不外推 dev。

---

## 附录 A：本稿只读复现命令（零模型/零网络）

```bash
cd /Volumes/CC/Enzyme_Agent/dependingv43 && git rev-parse HEAD   # 26ad1197…（本稿基线）
# (a) 记录侧资产字符串分类计数（只打印计数，无结构串）
PYTHONDONTWRITEBYTECODE=1 ~/miniconda3/envs/depending43/bin/python -B - <<'PY'
import json
from collections import Counter
from rdkit import Chem, RDLogger
from rdkit.Chem.MolStandardize import rdMolStandardize
RDLogger.DisableLog('rdApp.*')
unch = rdMolStandardize.Uncharger()
def cls(s):
    m = Chem.MolFromSmiles(str(s or ''))
    if m is None: return 'unparseable'
    hasq = any(a.GetFormalCharge() != 0 for a in m.GetAtoms())
    try:
        canon = Chem.MolToSmiles(unch.uncharge(Chem.Mol(m)))
    except Exception: return 'operator_exception'
    if hasq: return 'charged'
    return 'no-op' if canon == str(s) else 'canon-only'
def scan(path, fields):
    n = 0; per = {f: Counter() for f in fields}
    for line in open(path, encoding='utf-8'):
        line = line.strip()
        if not line: continue
        row = json.loads(line); n += 1
        for f in fields:
            v = row.get(f)
            if v is None or v == '': per[f]['missing'] += 1; continue
            for x in (v if isinstance(v, list) else [v]): per[f][cls(x)] += 1
    return n, per
for path, fields in (
    ('assets/v3_reactions/library/library_full.jsonl', ['donor_smiles', 'product_smiles']),
    ('assets/v3_reactions/corpus_env/corpus_v1.jsonl',
     ['donor_A_smiles', 'product_B_smiles', 'donor_components', 'product_components']),
    ('assets/analog/corpus_templates_v1.jsonl', ['mapped_lhs', 'mapped_rhs'])):
    n, per = scan(path, fields)
    print(path, 'rows', n, {f: dict(c) for f, c in per.items()})
PY

# (b) 算子构造器参数实测（v2 新增；无结构串；输出=三默认值 + 实例不可自省 + neutralize 关键字被拒）
PYTHONDONTWRITEBYTECODE=1 ~/miniconda3/envs/depending43/bin/python -B - <<'PY'
from rdkit import RDLogger
from rdkit.Chem.MolStandardize import rdMolStandardize
RDLogger.DisableLog('rdApp.*')
u = rdMolStandardize.Uncharger()
print('instance dir:', [x for x in dir(u) if not x.startswith('_')])
for attr in ('canonicalOrder', 'force', 'protonationOnly'):
    try: print(attr, '=', getattr(u, attr))
    except Exception as e: print(attr, 'GETFAIL', type(e).__name__)
try:
    rdMolStandardize.Uncharger(neutralize=True); print('neutralize kw: accepted')
except Exception as e: print('neutralize kw:', type(e).__name__)
print('signature doc:', (rdMolStandardize.Uncharger.__init__.__doc__ or '')[:200])
import rdkit; print('rdkit:', rdkit.__version__)
PY

# (c) 语义敏感度小实验（Morgan 电荷敏感 / 季铵 no-op / applied 保留永久电荷反例）见 §1.5(b)；
#     其后两例使用合成结构串，本文件不收录（零结构串纪律），复现走评审证据目录
#     docs/review_evidence/t_e_run_identity_codex_2026-10-19/operator_execution.md 同款方法。
```

## 附录 B：本稿边界（不做什么）

- 不实施任何代码改动、不改任何既有文件（本轮回修只改本设计稿文件本身）、不动冻结文本与封存批；
- 不做数值重算（缺口 5 归 E1 前置 1 子任务）；
- 不做化学裁定（化学边界以 FROZEN_V3 D01–D07 与后续评分流程为准）；
- 不编辑 src/、tests/ 与其他 docs/；不引用/裁定同期 compiler-5 新行为（编译层口径锚定评审固定副本）；
- 不 git add/commit/push；不调用任何模型/网络；产物零结构串。

---

*设计稿 DRAFT（v2）结束。本文件不构成冻结、不构成预注册、不构成实施授权。*