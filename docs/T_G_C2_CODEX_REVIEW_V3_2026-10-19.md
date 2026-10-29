# T-G Step C2 draft_v3 Codex 复核报告（2026-10-19）

**总裁定：再回修；P0=0，P1=1，P2=0。暂不可进 CC 预注册确认。** 上轮歧义硬拒与两条 P2 已闭合；P1-C2-02 的入口清单、可达分账和路线验收线已补齐，但 R2 直接替换前门会同时改变执行输入，并绕过原来只在旧门拒分支检查的 wildcard 袋拦截。它与本稿“同输入、C1 边界不动”的承诺冲突，属于原 P1-C2-02 尚未闭合，不另拆成新问题。只需再修这处接线设计，不要求本轮改源码或跑真实池；本报告不替 CC 冻结或选择路线。

> **题域标签**：除明确写作“纯合成”的控制外，下文数字均为 **298＝RHEA 通用酶学/已见题** 的存储结果重数与工程记账，**不是化学成绩，不外推 dev（B1 环境路径）**。compiled 不代表完整化学可行或 strict 命中。
>
> 实际 HEAD：`d9cee973566fff8692b0c2abc51ab91f8122cfb3`。被审设计：`docs/T_G_C2_DESIGN_PREREG_2026-10-19.md`（draft_v3），SHA256：`215315f562e0ccb6a81b7cd9dbb5ee6859cbdf0a79b5383b9c091efef94a9557`。上轮 v2 SHA256：`a6a04a15c7c491f4251c1fd11e323bd811ed21679a6ad1b7ffbbec4681f76c8c`，已在本稿文件头登记；本轮仅核对文件头与上轮报告一致，未重建 v2 全文或重新计算旧稿SHA。
>
> 执行者为本次会话的三个子代理：歧义/芳香、重刀入口/可达性、计数/全文一致性。以下“本轮执行、重算”指对应子代理的实际执行，**不表示主窗口另行重跑**。证据仅采信到与源码及程序结果互证的范围。

## 1. 固定验收面

本轮只复核上轮报告 §2、§7 的两条 P1、两条 P2 及 v3 修订造成的同契约矛盾。输入为本稿、上轮报告、AGENTS.md、必要编译器/builder 源码、现有授权结果 JSON 与上轮证据；不扩大到完整机制认证、未来阶段能力或科学性能。未冻结、参数待 CC 选择、保守过拒、unsupported 或尚无正式实现本身不构成新增阻塞。

| 上轮项 | 本轮裁定 | 主要证据位置（均为 draft_v3 行号） |
|---|---|---|
| P1-C2-01 歧义即拒 | **关闭** | `:393-412` 全 M 核验/异目标必拒/截断默认拒；`:527-535` 合成矩阵与公共链要求；`:560-561` 同步 |
| P1-C2-02 重刀前门与记账 | **部分闭合，保留 1 项 P1** | `:315-359` 清单和分账正确；R2 的执行输入/C1 承诺仍互相冲突，见 §2 |
| P2-C2-01 错桶两处 | **关闭** | `:160-170` 299 构成；`:189-202` 56 交叉表/D17 子集；`:619-620` 同步 |
| P2-C2-02 芳香保证范围 | **关闭** | `:260-270`、`:579` 收窄为模板芳香边/键级的约束，不再宣称原子旗标精确双向相等 |
| v3 新引入问题 | **无另立 P0/P1/P2** | 剩余矛盾并入原 P1-C2-02；19 张表列数一致，v2 历史旧分支有明确收严注 |

## 2. 唯一保留项：P1-C2-02——R2 门替换会改输入并跳过既有 wildcard 检查

**对应原验收**：上轮最小回修要求明确执行输入、C1 拦截和所有入口；v3 `:333-336` 冻结现行供给策略和 wildcard 边界，`:477`、`:510` 又要求基线/变体同执行输入。不是新增科学门槛。

**设计冲突**：v3 `:327`、`:329` 让前门/供给后二次门换为中心同源判据，同时保留“前门拒后才加袋”；但被替换的前门还决定是否进入供给与 wildcard 检查分支。换判据以后，原来必须加袋或被 wildcard 拦截的候选，可能在 raw 输入已命中中心，直接跳到编译。

**当前源码链路**（`src/pathway_v43/pollutant/s5b_builder.py`）：`:1115-1116` 前门拒才进入 `:1122` 的 `analog_cosub_supply`；`:1128-1133` 的 wildcard 记数/不供给也只在该分支内。普通供给在 `:1134-1138` 加袋并重过门，`:1144-1156` 将 supplied 输入交编译器；未 rescue 则 `:1197-1205` 拒绝/continue。首次前门通过时，直接走 `:1206-1211`，输入是 raw `substrate`，不调用供给检查。因此，仅共用中心 helper 并替换两处门，不能同时守住所承诺的输入与 C1 边界。

**本轮纯合成互证，非 298 成绩**：固定乙醇氧化模板主份 `[CH3:1][CH2:2][OH:3] → [CH3:1][CH:2]=[O:3]`，另加未编辑独立袋组分；在复制源码中执行真实 builder `:1115-1216` 片段，分别注入旧元素门与中心门。该片段中的编译器是记录输入并返回拒绝的 **stub（替身函数）**，只证明调用/输入/诊断分支；另行调用隔离原型真实执行 raw `CCO`，确实得到 compiled `CC=O`。

| 纯合成形状 | 旧门片段实际行为 | 只将两门换成中心门后的片段行为 | 违反的本稿承诺 |
|---|---|---|---|
| 未编辑 `[Na+:4]` 袋 | raw 元素门拒；供给检查 1 次；编译输入 `CCO.[Na+]` | raw 中心门过；供给检查 0 次；编译输入 `CCO` | 同供给策略的文字未变，**实际执行输入已变** |
| 未编辑 `[*:4]` 袋 | wildcard 记数 1；编译调用 0 | supply/wildcard 检查 0 次；编译调用 1，输入 `CCO` | **既有 wildcard 拦截/计数被跳过** |

证据：[结果](review_evidence/t_g_c2_codex_v3_2026-10-19/heavy/heavy_results.json) 的 `synthetic_route_probe`、[探针脚本](review_evidence/t_g_c2_codex_v3_2026-10-19/heavy/review_probe.py)、[实际命令与输入/输出哈希](review_evidence/t_g_c2_codex_v3_2026-10-19/heavy/execution_manifest.json)。这不是 R2 已实施后的正式行为认证，不表示真实 298 已产生新假阳性，也没有跑正式候选池。两种合成形状揭示的是同一入口接线缺口，合计仍只记原 P1-C2-02 一项。C1 原规则核心是“整袋不供给”；上述 raw 路径没有供给 dummy，本项是对 v3 明写的“维持既有拦截/计数”和同输入承诺的反证，不是声称 dummy 被供给。

**最小设计回修，两种路线交执行者明确，最终由 CC 选择**：

1. 保留 R2：将基线每候选的 **raw / supplied / blocked 路由决定**与新中心准入判据解耦；中心 helper 只对已冻结的执行输入判定。既有 wildcard 拦截决定须在直编分支前同样受保护，不因 raw 中心命中而跳过。写清哪个来源决定供给、输入与 blocked，所有适用 analog 路由入口共用；不能只写“维持策略不变”。
2. 或本稿只留 R1：保留旧前门与路由，647 面线=0；39/24 仍只是同输入旧原型记账，待硬规则实施后重算。R2 另稿设计。

所选设计须补入上述普通袋输入保持、wildcard 不绕过两类合成验收，沿 **builder 公共入口**验证，并保留合法供给与无供给正控。接线确定后再重算可达数和验收线。本轮只修设计，不要求现在动 src/tests，不替 CC 选路线或冻结数字。

## 3. 已闭合项及核算边界

**P1-C2-01 已闭合。** 当前规则 `:395-405` 定义 M＝全部语义允许匹配，G＝度全等子集；prefer 只排序、不裁量准入。M 中每个候选均执行冻结编辑段，按净目标归并，出现至少两个不同可执行目标必须结构化 `ambiguous_alignment`；披露不能代替拒绝。`:408-412` 默认截断拒绝并披露未核范围；任何另定放行均被登记为规则变化且本稿默认不启用。`:527-535` 已收进混合位点反例、非全等单产物正控、合法正控、中心缺失负控、预算截断及公共链要求。

本轮隔离合成再次得到：`OCCC(O)C` 的全 M 参考有 3 匹配/2 净目标而拒绝；旧 prefer 丢 2 匹配后 compiled。`CC(O)C` 两个匹配同目标 `CC(C)=O` 可合并；`CCO` 编译为 `CC=O`、`CCC` 拒绝；65 份乙醇在 64 预算下截断拒绝。全 M 参考采用旧隔离函数的 off 模式，**不是新生产 prefer 实现已经通过**。新未核范围机读字段和接线后的完整验收仍待实施。[合成结果](review_evidence/t_g_c2_codex_v3_2026-10-19/admission/synthetic_result.json)、[专项判定](review_evidence/t_g_c2_codex_v3_2026-10-19/admission/findings.md)。

**P1-C2-02 其余回修有效。** 同源中心必要条件、**analog 本次前门接线面**的 builder 前门/wildcard/二次门/未 rescue/compiler 元素账声明、与轻刀 B 互斥、版本/spec 冻结项均已登记（`:315-338`）。静态搜索另见共同编译器的 `recorded_source.py:2126`（`compile_recorded_reaction`）消费者；它没有需 R2 替换的独立元素前门，仍纳入既有全量/非目标/池对拍义务，不因未单列而新增阻塞（[入口搜索与边界](review_evidence/t_g_c2_codex_v3_2026-10-19/heavy/findings.md) §4）。验收线按 R1/R2 交 CC，R1 的 647 面为0，R2 待重算，不再拿直调45行直接当正式线。以下存储结果已本轮重数，但不能替代 §2 的接线闭合：

| 298 工程记账 | 本轮核算结果 | 证明范围 |
|---|---|---|
| 原型 prefer2 新编译 | 165 行/58题＝45供给后旧门拒＋68前门拒无供给＋7wildcard＋45旧路可达 | 授权结果逐行字段重数，未重跑原探针 |
| 旧路可达与输入 | 45行/28题，内含6行/6题被原型加袋；扣除后39行/24题 | 同输入旧原型账；不是R2正式收益，题数不作直接相减 |
| 材料7件兑现 | 旧路可达3；其余2供给后门拒＋1无供给＋1wildcard | 原始靶集存储标签；保留6maintain＋1overturn，不统称终审确认正控 |
| 存疑层 | a-21c2f2454ee4 从当前 no_alignment 到原型 compiled | 单独复核分账；不并入0/72，不随路线重算消失 |
| single_element_heavy 299 | **O119＋C99＋N58＋`*`13＋S5＋Cl5＝299** | 同一299集合重数；旧O247等明确为全647模式统计 |
| 56 pass交叉表 | single16+8／no_def12+0／multi4+9／light7+0＝**no_alignment39＋transform17** | D17从56内筛得，env15+rhea2；不得与56加成73 |

这里的材料归桶/判读标签是存储标签重数，**不是本轮重新判读或化学复核**；原机读无遍历 occurrence ID，`qid+record_key` 不声称唯一，也不宣称旧新身份逐行闭合。[重刀核算](review_evidence/t_g_c2_codex_v3_2026-10-19/heavy/heavy_results.json)、[错桶/交叉表核算](review_evidence/t_g_c2_codex_v3_2026-10-19/consistency/aggregate_consistency.json)。

**P2-C2-01 关闭。** `:160-170`、`:189-202` 与附录B `:619-620` 均采用上述正确构成和交叉表，同集合重数与上轮 counts 一致。无新错桶。

**P2-C2-02 关闭。** `:263-265` 已将芳香要求限定为模板芳香边按芳香语义匹配，明确原子旗标精确双向保证尚未成立。本轮复现旧原型与现公共编译器均允许 `Oc1ccccc1 → O.c1ccccc1`；含芳香键的查询可匹配苯酚、拒绝环己醇，支持**模板芳香边/键级**这一收窄范围。普通 Atom 的孤立诊断不能认证芳香 true/false 任一方向的原子精确谓词；本报告不扩大该保证，不把既有共性指控为 C2 新误放行，不增加本轮验收门。[结果](review_evidence/t_g_c2_codex_v3_2026-10-19/admission/synthetic_result.json) 的 `aromatic`、`ordinary_atom_aromatic_positive_requirements`、`aromatic_bond_positive_requirements`。

**全文一致性未另立问题。** 19张表的管道列数一致；当前可达账、验收与附录已区分原型/正式可达/同输入。`:70` 保留 v2“拒或披露”追溯原文，`:86-88` 明确已收严，当前硬规则无此分支。`:116` 残留“逐行对账”历史措辞，但 `:49-51`、`:94-96`、`:129-130` 明示迁移桥只核历史聚合、未独立重建身份，足以消歧，不据此新增 P2。[一致性专项](review_evidence/t_g_c2_codex_v3_2026-10-19/consistency/findings.md)。

## 4. 执行、证据与纪律

全部核算/合成执行均在**全新临时目录**，`PYTHONDONTWRITEBYTECODE=1`；需要运行源码的专项复制 `src`（含 vendor）和 `pyproject.toml`，未在永久证据目录原地运行会写结果的脚本。未跑 pytest，无 pytest 缓存写入；没有将未执行的正式接线、真实池或科学性能报通过。

| 专项 | 实际临时目录与命令 | 永久证据 |
|---|---|---|
| 歧义/芳香真实合成 | `.../T/t_g_c2_v3_admission_rtndl1v2`；depending43 Python 执行 `synthetic_v3_admission.py` | [provenance](review_evidence/t_g_c2_codex_v3_2026-10-19/admission/provenance.json)：完整路径/argv/env、HEAD、输入前后哈希、源版本、结果schema与输出哈希；[源码manifest](review_evidence/t_g_c2_codex_v3_2026-10-19/admission/isolated_source_manifest.json) |
| 入口片段/原型合成与存储重数 | `.../T/t_g_c2_v3_heavy_xsxhz9dh`；depending43 Python 执行 `review_probe.py` | [execution_manifest](review_evidence/t_g_c2_codex_v3_2026-10-19/heavy/execution_manifest.json)：完整路径/argv/env、HEAD、必要输入/输出SHA256；[execution.log](review_evidence/t_g_c2_codex_v3_2026-10-19/heavy/execution.log) |
| 计数/全文一致性 | `/private/tmp/t_g_c2_v3_consistency.YcvYGA`；depending43 Python 执行 `audit_consistency.py` | [脚本](review_evidence/t_g_c2_codex_v3_2026-10-19/consistency/audit_consistency.py)、[聚合输出](review_evidence/t_g_c2_codex_v3_2026-10-19/consistency/aggregate_consistency.json)：环境、schema键、8项检查、19表与关键词行号 |

源版本仍为 `s5b-compiler-3` / `s5b-pool-policy-7`，无 v3 新生产实现/生产schema。原探针 JSON 无显式 `schema_version`；本轮记录其实际键集合，不拿旧脚本硬编码 HEAD 当实际 HEAD。合成结果/专项证据的schema及范围以各 manifest/provenance 如实登记。

输入保护基线在最初只读文档检查**之后**采集，不声称证明更早时点；记录实际 HEAD、17个必要输入SHA256、原有4份dirty文档状态，另对上轮证据目录34个文件取全量SHA256，未改旧manifest。[输入基线](review_evidence/t_g_c2_codex_v3_2026-10-19/consistency/input_protection_before.json)、[历史证据保护](review_evidence/t_g_c2_codex_v3_2026-10-19/consistency/historical_evidence_before.json)。结束核验通过：17个必要输入、34个历史证据、实际HEAD、原4份dirty状态均保持；src/tests无跟踪变更，新增路径只在本单允许范围。heavy自有SHA256SUMS与admission输出哈希均核对通过。[结束完整性证据](review_evidence/t_g_c2_codex_v3_2026-10-19/integrity_final.json)、[总MANIFEST](review_evidence/t_g_c2_codex_v3_2026-10-19/MANIFEST.sha256)（含最终报告及本轮证据，排除manifest自身）。

本轮只新增本报告及 `docs/review_evidence/t_g_c2_codex_v3_2026-10-19/`；未修改 src/tests/AGENTS.md 或任何既有 docs，未访问金标、题面、封存逐题 run，未调用外部模型、未付费、未 push。原探针 main/helper 和材料重建未执行。临时目录可失效；永久脚本、源码身份、命令与输出支持复查。

**再次复核仅需检查原 P1-C2-02 的路由/输入/C1 接线回修及相应合成验收设计；其余已闭合项保持关闭。通过后再交 CC 预注册确认，路线、验收线与冻结权仍归 CC。**
