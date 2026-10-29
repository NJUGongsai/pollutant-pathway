# PPV1 S5b HIT50 v4b 正链复审与 chain12 发车裁定

日期：2026-10-10（Asia/Shanghai）。实际HEAD `9a0a60ea0a426fcfe0df3c82de5a9ab1fcbdaa46`；直接父 `8d92f3aa0e1a16ba454aa97702a076f319195aed`。正链主审及三个子代理独立核验；无外部模型调用。

## 1. 编号结论

- **V4B-C01：v4b 工程不通过，唯一新P1=`S5B-V4B-01`。** 新消解门把“产物不写手性标签”当成“产物已无立体中心”。两个磷、一个硫合成案均获 `stereo_dissolution_applied=[1]` 并真实提交事件，但执行产物仍有潜在立体中心，未兑现mimo r28 E2的既定放行条件。正常碳中心真实消解正控保持；详见§4。
- **V4B-C02：推断枚举部分通过有限验收。** fast-fail 必要条件、预算有界拒与多组分枚举合成前后对照成立；产物多重集/截断门未放宽。扩大预算、去掉首组分break确实改变候选面，按recorded-source-2登记合格，不能把全部改动称“零语义变化”。
- **V4B-C03：chain12 当前不放行。** 技术阻塞仅§4的新消解许可，不重开共底物/金额/提交序等已关组。收口后也建议缓发单独298性能批：交付仅报告净恢复1题1槽，已有合成公共链足以先验工程；单次重跑不能从模型波动中分离此增量。后续合批与归因条件见§7；低预期收益本身不另立P1。
- **V4B-C04：计量仅来源声明＋聚合算术互证。** 71→72、1323拒、38类分解、192→191及1141.8→1148.8秒未在本评审读取真实题逐案复跑。可以登记诚实支持面，不能认证“80失败题大半正确拒”、每池槽100%提交、净命中增加或±数题方差。
- **V4B-C05：红线与已闭合组保持。** 三冻结、scorer匹配排序、金额链、AtomTool字节不变；corpus共底物许可函数不变，20条旧v4回归及72条金额回归保持。mimo r33只有请求稿，回应未到不妨碍本轮工程否决；没有编造回应同意。

P1清单 **`[S5B-V4B-01]`**。本轮不是科学性能验收，不将合成反例外推为真实298题已发生同样错误，也不将298外推到dev污染物路径域。

## 2. 固定验收面与输入

本轮只验新stereo消解/推断预算与枚举面、版本与计量、chain12发车/合批裁定。继承关闭：S5B-V4-01共底物诚实拒、金额守卫族、提交序、v1–v3供给、S3/S4、历史launch；旧同标签SN2断成键风险仅沿交付既有披露，不在本轮重开。

必读绝对路径：

1. `/Volumes/CC/Enzyme_Agent/dependingv43/AGENTS.md`。
2. `/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S5B_HIT50_V4B_DELIVERY_2026-10-10.md`。
3. `/Volumes/CC/Enzyme_Agent/dependingv43/docs/mimo_ppv1_chem_review_response_r28.md`，E1–E3，尤其`:140–141`及`:152`的“执行后非立体中心”条件。
4. `/Volumes/CC/Enzyme_Agent/dependingv43/docs/mimo_ppv1_chem_review_request_r33.md`，S1/S2采纳核对。
5. `/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S5B_HIT50_V4_CODEX_REVIEW_2026-10-10.md`。
6. `/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S5B_HIT50_V4_R1_CODEX_REVIEW_2026-10-10.md`，关闭基线及发车清单。

HEAD九个提交路径：三源码、四旧测试修改及一新14条测试、交付书。全执行在fresh `/private/tmp` 源码/vendor/metadata/批准普通资产/source-only v3；父子v3同根。未真实仓跑tests全量；未读真实金标/题面/封存逐题run/dependingv4/原v3评价资产。漏斗仅读交付聚合和静态统计方法，不打开逐qid JSON或run_inputs。

## 3. 独立执行数字、红绿与事故

| 验收面 | 独立结果 | 范围 |
|---|---|---|
| 安全定向410用例 | **407 passed / 3 skipped，exit0** | S5b族261（已含新v4b14）、AtomTool15均绿；其余134项为131通过/3合法缺席，不能登记410全绿 |
| 安全G01 | **1981 passed / 10 skipped / 17 deselected，exit0** | 329输入，前后SHA零失配；从旧328沿7合法换字节＋1新测试＋0缺失恢复 |
| G01的PPV1子集 | **1378 passed / 2 skipped** | 同一次执行，docs白名单边界2项；不重复累加 |
| 直接父，五文件同测试字节 | **14 failed / 65 passed / 0 collection，exit1** | 6行为＋5版本＋1枚举预算字面量＋1执行阶段拒因标签＋1运行期缺helper |
| 旧金额控制 | **72 passed** | R1/R2/R3三文件字节不变，19＋28＋25；属于上述套件子集 |
| 推断前后合成 | **16案×父/子=32观察** | 6无解fast-fail、5普通/同位素/缺产物、3多组分、2人为小预算控制 |
| 消解公开链 | **4次start/4次resume** | 碳正控＋P3/P4/S4，各1事件；真实native首读后合成参考均matched_strict；每案resume17表全0 |
| 消解附加控制 | **6编译负控＋6映射helper** | 模拟残留标签仅用于门控负控，三P/S漏洞均为真实执行，不是mock |

自报原环境 **1992 passed / 0 skipped / 16 deselected**、原定向410全绿仅来源声明。本评审安全隔离G01结果与交付同口径1981一致；不为凑原环境数字搬禁止资产。

定向3skip为 `test_analog_assets.py::test_row_counts_match_v4_parser` 与 `test_analog_v2_corpus.py` 的 `::test_v2_selected_and_remapped_rows_decidable`、`::test_v2_line_level_one_to_one_and_duplicate_ids_recorded`，原因分别原v4对照不可用、v2 provenance/summary缺席。

G01完整10skip/17deselected逐nodeid/原因在 `execution/logs/g01_absences.json`、`execution/README.md`；包括上述3、原v3冻结评测资产5、两S5a docs守卫2；排除指定电荷夹具1与16 slow/真实引擎测试。全部如实缺席，不算通过。

父14红完整逐nodeid/full failure在 `execution/parent_red_green_classification.json` 与JUnit。不是“14全真行为”：6行为为碳正控编译、recorded正控、后执行复核分支、多组分枚举、实盘边界、CN新夹具；5为版本字面量。预算参数断言不是行为反例；`_elements_contained` 是测试内运行期ImportError，不是collection红；显式氢案父早拒、新到执行价态拒，仅拒因/阶段翻转，未变成可提交。

所有根pytest使用 `-B`、`PYTHONDONTWRITEBYTECODE=1`、`-p no:cacheprovider`。定向/G01并行的既有子进程产生7pyc，仅隔离树且创建者未逐个追踪，封包不纳缓存。成本套件有本机假HTTP，不把它写成所有网络0；外部提供者/模型调用0，stereo/scope探针socket禁。

审核事故完整保存：执行封证首次遇SQLite BLOB不能JSON序列化，改用可逆hex导出同库续封，无套件重跑；97个合成DB封完整schema/表文本。stereo审计4次包装器/夹具断言错误（ParsedSide JSON适配、P4手写current省略原子状态、proof_record读取路径、Pt拒因期望）及修正日志保留；已成功的公开start不重复执行。主审纯证据读回首次将manifest列表当字典，保留失败脚本/输出/exit1，修正适配后读回成功，没有重跑产品。未发生当前轮额度中断，旧永久证据只读复用。

## 4. 唯一P1：S5B-V4B-01，未指定标签被当成真实立体消解

### 4.1 对应既定条件与实际代码

mimo r28 E2已把放行谓词缩为 **执行＋sanitize后该原子非立体中心，且rhs无手性声明**，再核rhs同源状态和机读诊断。r33 S2主动询问“仍为立体中心不放行”是否被当前复核覆盖。这是本轮新增许可的原验收，不是新加机制库或全局stereo要求。

实际代码（下列文件均在 `/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/`，源码按实际HEAD读取并封行号文本）：

1. `s5b_compiler.py:309–341` 只核lhs标签CW/CCW、rhs标签UNSPECIFIED、lhs所有邻键single、涉及变化全single→double/triple且至少一个。没有判定消解后的实际几何/立体潜力；**全单键并不等于所有元素均为碳型sp3，升双键也不保证中心不再具有立体性**。
2. `:344–359` 在执行mapped产物中按atom_id_map找到原子，只返回GetChiralTag。
3. `:362–378` 只拒tag缺失或不等于UNSPECIFIED；**UNSPECIFIED说明未指定构型，不能证明该原子不是潜在立体中心**。
4. `:909–923` 该门通过即继续保留compiled target，`:991–1002` 写 `stereo_dissolution_applied` 与固定 `sp3_to_sp2` 语义。

单纯残余标签mock负控证明此门会拒已有标签，不证明没有标签的保留中心被拒。新增14绿未检验后一个分支。

### 4.2 三个真实公开链反例与一个合法碳对照

最小P3输入：

```text
lhs = [P@:1]([OH:2])([CH3:3])[CH2:4][CH3:5]
rhs = [P:1](=[O:2])([CH3:3])[CH2:4][CH3:5]
current = CCP(C)O
center = [1,2]
```

lhs真四面体tag、全单键；rhs不声明手性；只有P–O single→double。新编译器返回compiled，消解map=[1]，而真实执行产物为 `CC[PH](C)=O`：P仍SP3，三个重原子邻接＋explicit H1、tagUNSPECIFIED，`Chem.FindPotentialStereo` 在该同源执行原子报 `Atom_Tetrahedral / Unspecified`。直接父对同一P3输入拒 `stereo_edit_unsupported`，确认是本轮新开口。

P4加强案完整输入/输出不依赖P3的氢表示：

```text
lhs = [P@:1]([OH:2])([CH3:3])([CH2:4][CH3:5])[CH2:6][CH2:7][CH3:8]
rhs = [P:1](=[O:2])([CH3:3])([CH2:4][CH3:5])[CH2:6][CH2:7][CH3:8]
current = CCC[P](C)(O)CC
target = CCCP(C)(=O)CC
```

P4执行原子degree4、H0、电荷0、radical0、SP3、tagUNSPECIFIED，仍是 `Atom_Tetrahedral`。S4同根以S替P：执行产物 `CCC[SH](C)(=O)CC`，S为SP3D、degree4＋H1，潜在类型 **Atom_TrigonalBipyramidal**，不是四面体；同样不能称sp3→sp2消解。初期消息把该S类型概括成四面体，已按原始输出纠正。

| 案 | 实际目标/同源原子 | 当前结果 |
|---|---|---|
| carbon_control | `CC(=O)Cl`，C为SP2/UNSPECIFIED，potential集合无该中心 | 正常compiled、map=[2]；1event，matched_strict |
| phosphorus_three | `CC[PH](C)=O`，P为SP3且潜在四面体 | 仍compiled、map=[1]；1event，matched_strict |
| phosphorus_four | `CCCP(C)(=O)CC`，P为SP3且潜在四面体 | 仍compiled、map=[1]；1event，matched_strict |
| sulfur_four | `CCC[SH](C)(=O)CC`，S为SP3D且潜在三角双锥 | 仍compiled、map=[1]；1event，matched_strict |

每案真实compile→plan spec→公开start→prepare/AtomTool→donor诊断→audit/admission→store→native首消费→合成参考结构匹配；真实事件各1，resume17表全0。实例是规则级合成，不声明它们是298实题或某种酶的真实反应。

整体均 **retain_conditional/R5，不是R6**。变换中心检查可为verified、product_coverage=full、proof_scope=self_contained_recompute、strict_target_match=True；这些只支持既有结构净变换范围，不能替新编译许可证明“立体性已消失”。合成参考正是执行目标的结构声明，matched_strict也不认证化学消解。问题是实际授予了错误的消解许可/机读凭证，不是冻结匹配器被改或绝对构型凭空授R6。

证据：`stereo/public/{phosphorus_three,phosphorus_four,sulfur_four,carbon_control}.json`，完整输入/执行原子映射/native payload/production report/表数据，及 `stereo/readback_and_controls.json`。该路径不走新corpus component许可，不重开共底物；它可作为analog公共编译器spec消费进入公开链。

### 4.3 最低收口

只修本轮消解许可：**同源执行原子的标签为空还不够；必须证明该原子真实不再属于被允许消解的立体中心，无法证明/仍有潜在立体性则不授消解spec。** 保守收紧允许的原子/变换类别可接受，不要求支持完整P/S或所有立体类型。

同时保留实际执行后同源复核：映射、产物解析、原子定位缺席先拒；实际仍为潜在中心或出现不支持立体类型先拒；无关原子的立体性不应造成正常碳案全面过拒。不得只改诊断文案继续开放同样不符合E2的spec，也不能只封本SMILES或一个元素实例。

P3/P4/S4逐案零不合格spec、公开池不产生这些坏许可事件；正常碳sp3→sp2、原bt0002#r0032非手性底物能力、原creation/纯翻转/SN2/显式氢拒与map缺席/产物重排/残留标签控制保持。不改AtomTool、冻结尺子、全局audit规则或已关组。后续完整异原子立体设计另审，不借本轮扩大范围。

## 5. 推断枚举、版本与mimo采纳

`recorded_source.py:444–456` 用元素多重集包含；`:459–532` fast-fail在删键枚举前，`:535–646` 全组分候选装配。具体分子图删键不改变元素/原子数，该前置是必要条件；其本身不替代同位素/电荷/结构匹配。6无解案父/子均映射0，fallback调用3/21等降0；另5标准/同位素保留及不匹配/缺产物控制同判。3个双组分顺序/重复案候选1→2但编译仍new_atom_placement_incomplete；两种人为预算1仍truncated并拒，未靠截断取首。

800/8192及全组分枚举是**搜索面行为变化**，已登记 `s5b-recorded-source-2`。产物多重集、实际目标/歧义/触顶门源片段不变。`compile_recorded_reaction`、find两个入口及共底物许可逐字节相同；builder可执行AST相同，仅池成员版4。compiler-2承载新消解语义，corpus-retrieval-2不变。身份登记方向合格，不能豁免§4行为缺口。

mimo r28逐条：

| 条款 | 互证与处置 |
|---|---|
| E1 creation/纯翻转/断成键排除 | 对应有标签变化反例实际unsupported保持；不声称本轮解决旧同标签SN2风险 |
| E1非四面体与E/Z | 谓词入口排除非四面体标签；独立Pt形态实际transform_no_change，不冒称全族统一stereo_edit_unsupported。E/Z检测盲区仍如实披露，本轮未新授E/Z支持 |
| **E2执行后非立体中心** | **未兑现，P1成立。** tagUNSPEC不是non-stereocenter；P/S真实公共链反证 |
| E2同源map/残余标签/机读诊断 | 原有map失败与残余标签门有效，但不能补足潜在中心缺口；诊断须对应真实许可 |
| E2-⑥ capability/prompt同步 | 本轮可不搭车改：real_model的stereo_edits仍指显式novel编辑op；本变更是recorded/analog经既有键级op编译。新增模型提示变量需单独身份/实验登记，不能当当前必须放宽op的理由 |
| E3冻结正文无冲突 | 三冻/评测字节互证成立，不代表新适配许可已正确；不靠strict匹配代替E2 |

r33本轮开始及封包前仅请求，未消费回应；回应到达后与本报告P/S反例互证。不会因其“同意”覆盖已执行缺口，也不因其缺席延迟本轮工程裁定。

## 6. 漏斗/计量可采范围与P2

以下仅交付源声明：EAWAG成功71→72、bt0002#r0032恢复1题、38候选失败迁移=1compiled＋5execution_failed＋24created＋8保留/翻转；corpus成功16不变、截断5→no_alignment；池142→143槽、空池192→191；两臂相同、1323许可拒不变；墙钟1141.8→1148.8秒。真实题域统计未读、未独立执行，交付“批准底物字段访问”不冒称本评审零题数据逐案复跑。

独立聚合算术：[192,81,19,1,5]→[191,82,19,1,5]各合计298，槽142→143，均值0.476510→0.479866，空池64.4295%→64.0940%；38=1+5+24+8。墙钟变化(1148.8−1141.8)/1141.8=**+0.613%**，这是该来源运行耗时比，不是+0.6%命中/供给提升，也没有重复计时误差界。

P2/下轮落字清单（不另加阻塞）：

1. ≤127键只说明k≤2删键组合调用数≤8128；800匹配上限仍可能先触顶，不能普遍保证全部枚举完成。
2. “预算/全组分扩展零语义变化”限定为后级门未放宽；fast-fail无解结果等价单列，候选面改变如实登记。
3. “池槽100%执行留存”不能从编译门＋单e2e推出；运行预算/恢复/准入/条件等仍可使池未提交，写编译可用集与实际提交分开。
4. “80失败题大半是正确拒”缺同域逐题去重分母证据。24+8是38个候选事件的子类，不能推80独立题多数；可说具体creation/翻转控制符合当前不支持边界，不说所有拒都是科学必然正确。
5. EAWAG placement例只证明当前孤立donor/列出RHS在指定一次计数不闭合；系数、隐式水/受体或来源完整反应未知时，不能定性“完整源反应是数据缺陷”。继续来源/配平unknown，R3-2独立设计边界不变。
6. “显式氢6例”与五个EAWAG迁移事件、九个analog迁移事件、独立测试夹具别混用；真实恢复4–5题与约3行AtomTool改动均未审定，不预支保证。
7. “±数题”是未量化波动风险，不是本轮估出的方差/置信区间；净新增一槽不等于必增一命中。目标仍119/298，H5 150参考，不改known_gaps分母。

## 7. chain12最终裁定与后续路线

**当前HEAD不发chain12；原因是S5B-V4B-01，非仅增一题或科学性能pending。** 先按§8有限回修，不重开任何已关组。r33未到不挡工程否决；真实发车前仍需其互证采纳与现有登记/预算/读回封包义务。

该P1清零后的路线建议：**缓发单独v4b正式298性能批**。合成链已验证碳正控，源报告仅新1题1槽；单次seen298重跑只能作集成回归/运行观察，不能可靠归因H1小差异，更不能声称达119的新供给证据。若用户明确要单独回归批，工程清零后可按既有数量/60CNY帽/独立登记执行，不凭收益低另立技术禁令。

如下一轮D2或显式氢改动获得授权并分别工程通过，建议一个新身份的**组合探索批**，先冻结每个改动及各自前后合成/离线对照，登记“v4b＋D2＋H实际纳入哪些”，不称单变量v4b测试。若需要将分数变化归因到某一项，必须使用保持其他项固定的配对消融或预注册多臂；不能在一批同时换三项后独占归功v4b。不强制本轮实施D2/H，也不代用户/teacher批准全局工具语义或科学阈值。

后续实际发车继承v4-R1报告§7六项：新batch/部署HEAD/代码资产SHA与compiler/recorded/pool/corpus版本；119/298与seen/旧敏感性及UH5L；40在途/1logical/HTTP1490/60帽/同日价保守bound机器生效；真实配对双门＋§9-④原文插新登记/读回/SHA；固定前10同身份冒烟；298全终态留分母、封存后零LLM判分与费用对账。当前这些执行事实未确认，不预填已完成。

AtomTool“减一显式H约3行”影响所有novel/recorded执行路径，并不自动证明single→triple/带电/不同元素语义。此处只登记另轮审批与验证面，不实施或批准该补丁。D2解除共底物拒同样是下一独立设计/实施验收面，当前许可继续冻结。

## 8. 有限回修提示词（只修S5B-V4B-01）

你是实施agent；仓库 `/Volumes/CC/Enzyme_Agent/dependingv43`。基线 `9a0a60ea0a426fcfe0df3c82de5a9ab1fcbdaa46`；先读AGENTS、本报告§4/§5、v4b交付、mimo r28 E1–E3/r33请求及本轮证据 `docs/review_evidence/ppv1_v4b_codex_2026-10-10/stereo/`。旧证据只读，探针复制fresh tmp。验收只沿既定“真实消解＋同源复核”承诺，不重开已关组，不启动真实批。

1. 列extract/许可谓词/执行后复核/编译spec/池/公开消费入口。共用同一消解许可，不能builder挡但compile仍返回带错误dissolution凭证的spec。
2. 收紧本轮许可：lhs全single＋rhs无tag不能单独授消解。实际同源执行原子仍是潜在立体中心或属于不支持类型、无法确定时结构化unsupported，零该不合格spec/事件；可保守只支持已有证据的碳型真实sp3→sp2/相应窄化范围，不要求全面P/S立体机制。不得按本三个SMILES或一个atom_id设例外。
3. 执行后必须核真实同源原子的立体潜力/消解事实，不能只比UNSPEC标签；映射/解析/定位不完整先拒。报告机读证明范围、诊断及拒因准确，不靠改注释继续同样放行。若采用入口保守拒＋后置纵深守卫，逐项说明适用范围与不可达分支控制。
4. 复制本轮P3/P4/S4输入fresh tmp逐案验拒；公开混合合法碳池核0坏事件、合法事件保持。保留碳真实消解/public native，bt0002#r0032非手性正控、recorded/cn，creation/纯翻转/断成键/非四面体/价态墙/残留标签/缺map/多产物序列化控制；区分真实执行反例与mock防御门测试，不把结构matched_strict称全化学verified。
5. 不修改AtomTool、scorer/evaluation/三冻结、金额/共底物许可/提交序或旧同标签SN2。预算扩展/全组分枚举保持关闭验收。许可/spec成员改变按既有版本与身份规范登记compiler/池；是否影响recorded枚举版逐项说明，不为凑绿扩大变更面。
6. 同步本报告§6精度文字及r33采纳/反例。新父同字节红绿逐nodeid：真实P/S许可行为翻转与合法控制保持，字段/版本/拒因/运行缺符号另列；安全G01缺席不补禁止资产。新交付完整输入输出/argv/env/exit/SHA、嵌套manifest纳哈希、实际HEAD/sourcecode身份；源码测试交付只显式add授权路径，本地提交不push。

下一轮只复审本组先拒/真消解/真实同源复核与正控，不把D2/H/配平/全面E/Z功能塞入有限回修。若坚持开放异原子消解，须给规则级设计＋实际中心不再立体的执行证据及化学评审，不以标签空或冻结零冲突预支批准。

## 9. 红线与永久封包

父/HEAD/实际工作树三冻结一致：

| 项 | SHA-256 |
|---|---|
| criteria-v1 | `7fd35aabdb4d2d5b67b0bf58693dab6f8765ad872efedf5f886503c4907064e4` |
| FREEZE_RECORD | `6e046e2970a102c63e693cebb81f2564b5d79fea1b6e7a776b0fc00c09662610` |
| path_context | `971ad00f42fc56915bad3724300759aa86552bf08199f8335c7f0286b40d588d` |

scorer/匹配排序/evaluation、金额守卫链、AtomTool等16列明闭合文件字节不变；recorded公共gate与两个find原文不变，新co拒实际守卫已移至 `recorded_source.py:931`（行号移动，原函数正文不变）。1323统计不变只是源报告，许可函数原文与旧控制保持是本轮独立证据。legacy52聚合仍 `279d9bc19bad25e51b7c23ee276da95151a8f25cf598b9dc3642b508d817c4bb`；PPV1 84文件仅recorded/builder/compiler三处变，聚合 `8d993b95…→f845999e61d7ce5f65b7514ebe68146944e7698e27436667ab7ca37effb3a3f8`。

本评审无push/commit/外部模型/真实批/禁止数据访问；不能用diff认证实施方所有历史网络或文件访问行为。新写只有本报告和证据目录，不改src/tests/既有docs/AGENTS/旧永久证据。

证据路径 `/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/ppv1_v4b_codex_2026-10-10/`：`execution/`安全全套/父分类/329谱系/身份/逐nodeid缺席；`stereo/`真实P/S事件与碳正控/原子映射/native/防御控制；`scope/`16×2推断合成/源字节/计量精度；`root_audit/`固定输入和旧证据guard、完整diff/实际行号、sealed证据读回/发布receipt。脚本只能复制新tmp执行，禁止永久目录原地建库。

封包仅排根manifest.json/SHA256SUMS，所有嵌套manifest及SHA清单纳哈希；报告SHA单列。发布前后167固定输入、旧15,595证据文件精确集合/SHA和原工作树核验；若r33并行到达，只读消费并单独登记外部新增，不把它当本评审写入。最终根附件数与SHA以封包为准。
