# PPV1 S5b HIT50 v4b-R1 正链有限复审

日期：2026-10-10（Asia/Shanghai）。实际HEAD `1f5111bd2e150d15e0bd90dd17082e3d8feeca59`，直接父 `9a0a60ea0a426fcfe0df3c82de5a9ab1fcbdaa46`。本轮只验上一轮唯一P1 `S5B-V4B-01` 及r33采纳，不重开其他已关闭组；正链主审＋三个子代理独立取证，无外部模型调用。

## 1. 编号结论

- **V4BR1-C01：工程通过，S5B-V4B-01关闭，P1=[]。** 入口只允许碳中心消解；执行后按同源原子同时核已指派标签与潜在立体中心，后者包含未指派。原P3/P4/S4逐案从父的坏消解许可变为先拒，无不合格spec或事件；实际碳消解及recorded/批准catalog正控保持。详见§4。
- **V4BR1-C02：r28 E2在已批准窄域兑现。** 不是用标签为空替代真实非立体中心，也不是通过全面拒绝碳正控过验收。潜在轴只核被消解原子，不把其他原子或键轴E/Z索引碰撞误当该中心。
- **V4BR1-C03：r33采纳主体成立，精度项列P2。** S1-a/b、S2双轴/元素/机读诊断、S3分通道计数、S6协议scope落字成立；S1-c的亚砜公开测试被元素条件0先拒，不能独自证明条件2隔离覆盖。该分支已由本轮独立夹具隔离互证，不构成新的程序阻塞。几处旧内联注释与“Codex独立采信”措辞须订正，见§5/§6。
- **V4BR1-C04：v4b轮以工程证据收口；chain12继续缓发。** 接受 `s5b-compiler-3` 为后续登记的已审工程基线；不宣布真实批已发或科学性能已通过。下一真实批须为另获授权、分别工程通过并登记实际组合的D2合批，或用户另行明确指示；原发车六项义务保持。当前不启动D2或真实批。
- **V4BR1-C05：红线保持。** 三冻结、AtomTool、scorer/匹配排序、共底物许可、金额/提交链字节不变；recorded_source/real_model为纯说明改动，模型payload不变；没有push/commit/禁止数据访问。

本轮是合成工程验收，不将结果外推为298真实题已发生同样错误或本轮增加命中，更不外推到dev污染物降解路径题域。

## 2. 固定验收面、输入与隔离

基准：上一轮报告§4三案/最低收口＋§7缓发/合批裁定。本轮不重开共底物许可、金额族、提交序、旧供给各轮、S3/S4、历史launch、推断预算/fast-fail或既有同标签SN2/EZ残留。

必读绝对路径：

1. `/Volumes/CC/Enzyme_Agent/dependingv43/AGENTS.md`。
2. `/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S5B_HIT50_V4B_CODEX_REVIEW_2026-10-10.md`。
3. `/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S5B_HIT50_V4B_R1_DELIVERY_2026-10-10.md`。
4. `/Volumes/CC/Enzyme_Agent/dependingv43/docs/mimo_ppv1_chem_review_response_r28.md`，E1–E3。
5. `/Volumes/CC/Enzyme_Agent/dependingv43/docs/mimo_ppv1_chem_review_response_r33.md`，S1–S3及六项采纳条件。
6. `/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/ppv1_v4b_codex_2026-10-10/`，只读原始输入/执行/判断基线。

实际提交6路径：compiler行为＋recorded_source/real_model说明共3源码、2测试、1交付书。源码、vendor、metadata、批准普通资产及source-only v3复制fresh `/private/tmp`；父子v3同根。旧探针复制新tmp，不在永久证据内建库。禁止真实仓tests全量；安全隔离G01仅读固定329输入白名单，不补题面/金标/封存逐题run/dependingv4/原v3评价资产凑绿。

## 3. 独立执行与红绿

| 面 | 独立结果 | 解释 |
|---|---|---|
| 安全定向23文件 | **415 passed / 3 skipped，exit0** | 269 S5b（含22 v4b）、邻接149项为146通过/3缺席；不是交付250＋149全绿 |
| 交付250的对应子集 | **250 passed** | 从269 S5b中扣除w1的19；交付列出的文件表包含w1却写14文件/250，应写实际选择范围 |
| 安全G01 | **1989 passed / 10 skipped / 17 deselected，exit0** | 329输入；5合法变更、0新、0缺；执行前后SHA零失配 |
| 同次G01的PPV1子集 | **1386 passed / 2 skipped** | 同一次执行，不另加进总数 |
| 直接父同字节 | **9 failed / 14 passed / 0 collection，exit1** | v4b22项＋w1单个版本项；6行为/轴＋2版本＋1语义串 |
| 旧金额族 | **72 passed** | 定向/G01子集；前轮R1/R2/R3三文件19＋28＋25，源码不变 |
| 原反例公共链 | ****父/HEAD各6案，12次start＋12次resume**** | 父/HEAD原样P3/P4/S4与碳对照，原生首读与恢复；坏许可事件由3→0 |
| 双轴/隔离控制 | ****每侧3实际旧产物轴＋11helper＋7旧拒/mock＋3隔离/解析控制**** | 区分真实化学反例与显式mock/临时放宽元素的防御单元，不冒充生产开放 |

原环境全量 **2000 passed / 0 skipped / 16 deselected** 为交付及主会话来源声明，本主审未在真实树执行该全量；安全隔离结果单列，不混报。本轮两个S5a docs守卫/原v3评价资产等缺席沿既定口径；10skip/17deselect逐nodeid与原因、3定向skip、全JUnit/命令/结果在 `execution/logs/` 与README。三个定向skip为原v4对照代码及analog v2 provenance/summary缺席；不算通过。

父9红的6行为/轴：三P/S编译许可翻转×3、绕过元素守卫的P/S helper轴、模拟无标签仍潜在中心的主编译拒、helper双轴直测；后三项均属防御控制，不是新增6个真实化学漏洞。碳正控在父也能编译，但新增语义串断言失败，单列语义字面；两版本字面单列。完整逐nodeid与失败原文在 `execution/parent_red_green_classification.json`。

执行环境/事故：根pytest均-B/PYTHONDONTWRITEBYTECODE=1/no:cacheprovider；既有子进程在隔离树产生7pyc，未纳封包。预算套件有本机假HTTP，不冒称所有本地网络0，外部提供者/模型0；stereo/scope socket封禁。83个合成DB转完整schema/全表文本，无liveDB入证。scope首次探针误用常量名import退出1、尚未执行payload，修正适配后成功；stereo首次辅助只读断言误要求17表全内容不变，保留失败脚本/输出/exit1，改按合同行数增量后只重读同一批既有DB，无公共start/resume重跑。stereo封包还遇构建器嵌套引号SyntaxError及未生成finalize.py的runner退出2，保留失败构建器/日志后安全重构续封，同样无产品重跑。所有成功及事故原始日志保留。没有本轮额度中断；旧已完成证据只读继承，新核验分别记录实际HEAD、argv/env/exit，不拿旧脚本硬编码HEAD冒充当前。

## 4. S5B-V4B-01最低收口逐项

源码均为 `/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/` 当前HEAD，以下为实读行号。

### 4.1 共用入口与真实同源双轴

`s5b_compiler.py:339` 元素域仅C；`:352–389` 许可谓词先核条件0，再核标签/全单键/全部single→double或triple/至少一变。非碳中心不再进入新消解许可，继续落stereo_changed与结构化stereo_edit_unsupported。extract、recorded、analog/corpus候选装配共用公共编译器，没有builder单口过滤但compile仍给坏spec的分裂。

`:392–433` 恢复执行结果的同源原子：由当前ID找到执行idx，再以product_mapped_smiles的map=idx+1跨canonical/重解析定位。除GetChiralTag，还用FindPotentialStereo核该原子是否存在潜在立体类型，包含未指派。原子轴枚举`:344–349`；只比同一原子，滤键轴条目的centeredOn（键索引），避免数值碰撞误拒。解析/定位/map缺席先失配，潜在轴计算异常以potential_check_error拒；不是未知当通过。

`:436–461` 双轴合取：标签UNSPECIFIED且potential为None才通过；仍潜在中心用potential:<type>披露。主调用点 ``:998–1008`` 在有效target/spec完成前消费；诊断 ``:1076–1092`` 明示C-only、两轴、FindPotentialStereo及未指派。原r28 E2“执行+sanitize后该原子非立体中心∧rhs无声明”的最低行为在此窄域兑现，不主张全面立体机制或参考E/Z已证一致。

### 4.2 原三案逐字节复用与碳正控

P3原输入：`[P@:1]([OH:2])([CH3:3])[CH2:4][CH3:5]` → `[P:1](=[O:2])([CH3:3])[CH2:4][CH3:5]`，current=`CCP(C)O`，center=[1,2]。P4/S4用上一轮永久 `stereo/public/` 的原样输入，包括括号原子写法，不改成另一个“相似反例”。完整输入及前后SHA/实际执行/native/17表在本轮 `stereo/`。

父：三个案仍compiled并携dissolution=[1]，各真实事件1；P3/P4执行仍Atom_Tetrahedral，S4仍Atom_TrigonalBipyramidal。新HEAD：三案均unsupported/stereo_edit_unsupported，stereo_changed_maps=[1]，无不合格spec；候选编译先拒，无spec进入池，公开空接受候选池run各0event/0production_report，native首次读取实际验证；未把坏spec强塞production，公开根retrieve等正常基础账不冒称全零写。不会把未执行的坏spec内部链报通过。

碳二级醇→酮：父/子均compiled、dissolution=[2]，实际目标CC(=O)Cl、真实native事件/恢复保持；执行中心SP2、无potential。recorded/CN形态与批准catalog bt0002#r0032碳消解保持。合法事件仍整体R5/retain_conditional；carbon_control的local transformation_center为verified/full，另外两个正控为unknown/unknown_coefficients，诊断的center_match/strict_target_match仍true，均不称R6或完整生物机制证明。每案resume17表**行数**零新增；stop/endpoint记录可以更新payload，不冒称业务表全字节零写。

### 4.3 纵深防御与非全面拒绝

不依赖元素守卫，直接把原真实P/S执行mapped产物送同源复核：父单标签轴空窗，新P潜在四面体与S三角双锥均明确失配；同源位置、map缺失、无效产物、轴异常、残留标签、多产物重排、无关中心及键轴碰撞控制按原适用范围完成。碳合法正控保持，失败方向不是全面拒绝。

暂不支持P/S/Si/N等消解范围是上轮已授权的保守收窄，不另立性能阻塞；以后若扩范围须独立规则设计＋真实中心消失的执行证据及化学互证。旧同标签断成键/EZ/显式氢/共底物功能保持登记，不塞进本轮。

## 5. mimo r33六条采纳核对

**r33按父9a0a60ea读码，并非compiler-3修后执行证明。** 其旧S2“无P1/隐式碳保证”的定级不足以否定上一轮P/S已执行公共链证据；本轮以实际修复证据裁定关闭。其范围引导语混用了r28模板，回应已经自纠按r33正文评审，不因外部通道扩大采信。

| 条件族 | 本轮裁定 |
|---|---|
| 1 S1-a（标签变化形态限定） | 主模块头限定成立，同标签/模板无声明但底物有声明的断成键残留继续披露，不重开。helper内部注释仍有未带适用前提的“一律”句，列P2同步 |
| S1-b（E/Z双侧无声明） | 已补“无声明对无声明，非E/Z已核一致”，未改冻结身份/评测；不把无声明匹配当立体证明 |
| 2 S1-c（归因与隔离负控） | 两旧docstring归因已改；条件3碳案例确隔离断成键拒，sp2碳解析清tag已实测。亚砜公开测试先被C域条件0盖住，因此只证明综合拒，不能单称条件2独立覆盖；独立fixture隔离/对照证据详见stereo，生产域仍C-only。旧内联归因句与亚砜“隔离”命名列P2 |
| 3 S2-a/b/c（两轴、元素、诊断） | 组合①＋②合格：旧非碳残差已关闭，不照抄“仍未覆盖”。机读语义串已含C-only和两轴；潜在类型S为三角双锥的实值保持，没有误写成四面体 |
| 4 S3-a/b（分通道与5/6） | EAWAG38=1编译＋5墙＋24created＋8翻转/保留；谓词通过6=1＋5；analog1＋9/corpus18另列，跨通道墙14是事件不是独立题数。本轮不重跑漏斗，来源声明限定成立 |
| 5 S3-c（显式氢下一轮） | 登记为另轮优先选项可采；不批准约3行补丁或承诺真实恢复4–5题。只改记账/同位素H不被擅消耗、真实超价负控/novel影响面、语义落字等条件原样保持 |
| 6 S6（模型协议scope） | real_model.execution_graph_payload的说明/内联注释已加；父/子可执行AST相同，实际父/子各8个合成payload，8/8字典及canonical JSON逐字节相同。unsupported指模型novel编辑协议；编译器经既有键级op消解，不在此字段新增立体op或暗改模型提示变量 |

S1-c测试包装精度不改变条件0/双轴先拒的已执行事实，按上轮约定列P2，不再逼开下一程序回修轮。r33其他待执行项：本轮RDKit清tag/潜在类型/索引碰撞已互证，真实298漏斗/逐题分母/同标签翻转量级仍未验证；不拿合成结论补真实题域科学证据。

## 6. 版本、披露与遗留P2

接受compiler-3承载本轮许可收窄/双轴行为，spec.compile.compiler_version实测登记；recorded-source-2/corpus-retrieval-2与pool-policy-4保持。pool provider代码字节不变；所有recorded顶层定义字节不变，只模块说明改，real_model只docstring/注释。**编译行为并非零改变**，后续实际批必须将compiler-3实际部署HEAD/code_identity/资产SHA冻结入新登记，不能沿旧身份复跑覆盖旧批。

交付“池成员零变化”与非碳候选在真实298两通道为0仍是来源声明；本审仅验证原合成反例先拒和碳/catalog正控保持。上一轮§6只有聚合算术独立核对，不能被本交付`:108`“Codex独立采信”写成逐题形态认证。本轮不重跑真实漏斗的范围选择合格；保留pool-policy-4因池选择策略字节未变且新compiler/code_identity承载行为，不靠未经本审复算的“零影响”豁免身份。

下一交付搭车文字/测试精度清单，不另设程序阻塞：

1. 亚砜条件2测试命名改“综合拒＋解析事实”；如需常驻单条件证明可加明确夹具隔离，不能以临时放宽S域冒充生产许可。条件3及碳sp2解析事实保留。
2. 旧SN2/非四面体测试剩余内联条件归因与helper docstring“一律拒”补标签变化分支前提；UNSPECIFIED helper通过句补无potential条件。不改已关闭程序判断。
3. 本交付§五“Codex独立采信”改来源声明＋独立聚合算术；真实池零变化/各通道0/预期恢复量不用已认证字样。不把语料catalog记录号称298题目输入或对应科学命中。
4. 250子集选择范围写清排w1，邻接149在安全树是146/3；文件数和加法勿混。2000原环境与1989安全口径分开。
5. 交付表§十.1等继承指针注明是旧v4b交付，当前§八.1才是显式氢残留；未知完整源反应/系数保持unknown，不由孤立donor配平差定性数据错误。
6. 原helper“键轴碰撞”常驻夹具选中atom_idx=1，实际Bond_Double.centeredOn=2，并未碰撞。本审另构造真正同索引=2的控制，不误拒；下轮可把常驻测试改为真实碰撞，不把原测试名当覆盖证明。这是测试精度，不重开E/Z功能。

显式氢墙、同标签断成键、完整E/Z、非碳范围、D2共底物解除许可属于各自另轮设计/授权/验证面，本次只登记；不用这些pending否定已完成有限修复。

## 7. v4b轮收口与下一真实批

**工程轮正式收口，P1清零；chain12缓发裁定不变。** 当前compiler-3可作为新登记的已审基线，但本报告不等于实际发车登记已经落盘/读回/封包，也不宣布判据重新冻结、2000测试证明科学性能或达到119/298。

下一真实批：若D2获得授权并分别工程验收，可按实际纳入v4b＋D2的组合登记；其他显式氢等改动不能默认为已授权或必含。组合批是多变量探索，不能把变化独占归因v4b；需要因果归因时另做保持其他项固定的配对消融/预注册多臂。或用户明确另行要求单独回归批，则按既有数量/金额/独立登记执行；不凭仅净增一槽另设技术禁令。本轮不自行实施D2、修AtomTool或启动真实模型。

实际发车仍逐条落实上轮六项：新batch/deployed HEAD/代码资产SHA/compiler-3/recorded-source-2/corpus-retrieval-2/pool-policy-4；119/298主列、H5 150参考与seen/旧敏感性/UH5L不外推dev；40在途/1logical/HTTP1490/60CNY帽及同日价输入输出保守bound机器生效；真实qid配对双门＋§9-④原文插新登记/读回/SHA封包；固定前10同身份冒烟；298全终态留分母、封存后零LLM判分与费用对账。当前这些实际执行事实未确认，不预填已完成。

## 8. 红线与永久证据

三冻结父/HEAD/工作树一致：

| 项 | SHA-256 |
|---|---|
| criteria-v1 | `7fd35aabdb4d2d5b67b0bf58693dab6f8765ad872efedf5f886503c4907064e4` |
| FREEZE_RECORD | `6e046e2970a102c63e693cebb81f2564b5d79fea1b6e7a776b0fc00c09662610` |
| path_context | `971ad00f42fc56915bad3724300759aa86552bf08199f8335c7f0286b40d588d` |

16列明闭合文件及scorer/匹配排序/金额/AtomTool保持；recorded共底物许可原函数逐字节同、实际守卫行号`recorded_source.py:933`；真实1323拒记录未逐条重读，统计不变仅继承来源声明。legacy52聚合仍 `279d9bc19bad25e51b7c23ee276da95151a8f25cf598b9dc3642b508d817c4bb`；PPV1 84仅compiler/recorded_source/real_model三文件变，聚合 `f845999e…→659cf08935ddaeaa37746039f6ee74dff0a1d5cce810744744b20b62a88f562c`。

只新增本报告与 `/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/ppv1_v4br1_codex_2026-10-10/`。`execution/`安全套件/父分类/329谱系/身份/逐nodeid缺席；`stereo/`前后原案/真实native/恢复表/元素与双轴/正负控；`scope/`r33条款/注释精度/payload；`root_audit/`固定验收/diff/实际行号/封包读回/发布完整性。

封包只排根manifest.json/SHA256SUMS，嵌套manifest/SHA清单全部纳哈希；无liveSQLite/pyc/cache。报告SHA单列。发布前后170固定输入、17,924旧永久证据文件精确集合/hash/HEAD/tracked diff/status核验；旧证据不改。无push/commit/外部模型/真实批/禁止数据访问，不以diff认证实施方全部历史网络与资产访问行为。
