# PPV1 S5b HIT50 v4 W-V4.1-R1 交付书 —— S5B-V4-01 共底物诚实拒收口
# (2026-10-10)

状态:`implementation_ready_for_review`。

任务依据:Codex v4 复审报告
`docs/POLLUTANT_PATHWAY_S5B_HIT50_V4_CODEX_REVIEW_2026-10-10.md`
§4.3/§8(有限回修提示词;唯一 P1=S5B-V4-01)。基线
`37253796fe4c07320328752fc8cbe1fa41ff8f12`。本交付只修新增 corpus
component 适配缺口;不重开 v3 金额守卫/提交序/S3/S4/旧 EAWAG 规则/
冻结匹配评分尺子;不启动真实批;零模型零花费零 push。

- 实施期工作树:4 个已跟踪文件改动(改动集与 G01 脚本双基线
  diff 强制核对一致,见 §七);金标/题面/封存逐题 run 零读取
  (池深探针按任务书 §2 许可只读 run_inputs 的 `substrate_smiles`
  字段——是"批准字段访问",不是"run 零读取",如实登记);
- 判据零触碰:`compile_recorded_reaction`/`infer_reaction_mapping`/
  `compile_donor_template`、AtomTool、scorer/evaluator、
  `find_recorded_exact`(EAWAG)全部字节级零改动;冻结判据
  一~五、participant 集合语义、match_reference_edges、主 K 候选
  定义与 (created_at, event_id) 顺序、分母 298、S5B_PASS_LINES
  均未动。

## 一、修法一句话

**没有已经审定且实际消费的共底物参与物/原子来源语义时,有共底物
的 component 记录在 `find_corpus_recorded_exact` 候选装配层编译前
结构化 unsupported(`corpus_cosubstrate_participants_unsupported`,
保留源行/方向/共底物声明/可追溯拒因),不送单组分 LHS 编译、不产
池 spec、不产 event**——共用许可规则在检索/候选装配入口统一生效
(builder 池与公开链从源头拿不到坏 spec,无"builder 单口过滤而
find 仍返回可用坏 spec"的分裂);不按元素/角色/可锚性/方向/配平/
具体分子设例外;整串(whole)语义、EAWAG 面、公共编译判据、冻结
评测尺子全部保持。

## 二、入口消费矩阵(共用许可规则生效点)

| 入口 | 消费 | 本轮变化 |
|---|---|---|
| `recorded_source.load_corpus_index`(:304) | corpus 身份/sha/逐行回读/组分 CN 索引 | **零行为变化**(索引仍登记组分命中=检索面照旧;拒在候选装配层) |
| `recorded_source.find_corpus_recorded_exact`(:719) | 检索+分层+候选装配+编译 | **共用许可规则唯一生效点**:kind=component 且 co_substrates 非空 ⇒ 编译前结构化 unsupported(:864–905),不调 `compile_recorded_reaction`;诊断新增 `n_cosubstrate_participants_unsupported` 计数 |
| `recorded_source.compile_recorded_reaction`(:1009) | 推断映射+编译+产物多重集 gate | **零字节改动**(公共判据单一来源不动摇;整串/EAWAG 同入口) |
| `recorded_source.find_recorded_exact`(:620,EAWAG) | EAWAG 检索/编译 | **零字节改动**(旧水解能力保持,负控/正控见 §五) |
| `s5b_builder.default_pool_provider`(:412,通道 1b) | 消费 find_corpus_recorded_exact 候选 | **消费侧零新增过滤**(spec 在源头即不存在);`S5B_POOL_POLICY_VERSION` 升 `s5b-pool-policy-3`(池成员变化);池诊断透传新拒因 |
| 公开 start/resume(`runflow.start_ppv1_run`/`resume_ppv1_run`) | plan.pools specs | 零改动、无感(池里没有坏 spec ⇒ 零坏 event) |
| 导出/判分(`native_export.read_native_export`/`evaluation.match_reference_edges`) | events | 零改动(§五公开链探针验证) |

共用许可的判据来源:候选 `donor_match_kind == "component"` 且
`co_substrates` 非空——即"底物==多组分 donor 某一组分、其余组分
为共底物"这一**形态**判据,与元素/角色/可锚性/方向/记录是否配平/
具体分子无关(同根 LR/RL、可锚有机/不可锚断连辅因子、未知角色、
重复组分全覆盖,单测族见 §五)。唯一放行证明=显式共底物参与物
语义经独立设计+化学评审落地并实际消费(后续设计轮,§九)。

## 三、版本升级登记(既有身份规则)

| 版本 | 旧 → 新 | 理由 |
|---|---|---|
| corpus 检索语义 | `s5b-corpus-retrieval-1` → **`s5b-corpus-retrieval-2`** | 共底物 component 许可变化(编译前结构化 unsupported);分层/通配/映射/provenance 语义零变化;`CORPUS_RETRIEVAL_SEMANTICS` 新增 `cosubstrate_permission` 键并修订 `donor_side_semantics`/`whole_string_semantics` 措辞;`frozen_by` 登记 R1 回修依据 |
| 池策略 | `s5b-pool-policy-2` → **`s5b-pool-policy-3`** | corpus 通道池成员变化(组分级 spec 收缩为零;整串/whole spec 不变);EAWAG 面/融合/补位/池宽语义不变 |
| recorded 公共源 | `s5b-recorded-source-1` **不变** | EAWAG 路径与 `compile_recorded_reaction` 公共判据零字节改动(不偷改公共编译判据补 source 适配) |
| 代码身份 | 逐文件 SHA 自动重算(`run_identity.code_identity`) | `recorded_source.py`/`s5b_builder.py` 字节变化 ⇒ 聚合哈希变化(既有身份机制,无手动登记) |

其他版本(s5b-rank-policy-1、criteria-v1、冻结评测资产)零影响,
逐项说明:scorer/evaluation/rate_gate/llm_client/s5b_worker/runflow/
production/audit/s5b_compiler 源字节零改动;三冻结 SHA 不动。

## 四、两坏形态修后证据(零坏 spec/零坏 event)

公开链探针(评审 §4.2 两案的独立重放 + 同根全形态;fresh tmp
`/private/tmp/s5b_v4_r1_probe/`,脚本与输出已复制至
`docs/review_evidence/ppv1_v4_r1_impl_2026-10-10/public_chain_probe/`;
`-B`、socket 封禁、输入 SHA 前后核验、零金标/零题面):

| 案例(合成行) | 修前(基线 3725379 复现) | 修后 |
|---|---|---|
| `CCO.CC→CCOCC` LR(=评审 organic_anchored_lr) | 1 compiled spec;2×add_atom 折 CC 原子;公开链 1 事件(反应物仅 CCO);matched_strict | **0 池 spec、run 未启动(零事件)**;候选=结构化 unsupported,co_substrates=[CC] 声明保留 |
| `CCO.CC→CCOCC` RL(=评审 organic_anchored_rl) | 同上(方向 RL) | 同上(direction=RL 保留在拒因 detail) |
| `CCO.C=C=O→CCOC(C)=O`(=评审 balanced_cosubstrate,配平) | 1 compiled spec;3×add_atom+变键;事件只声明乙醇→乙酸乙酯;matched_strict | **0 池 spec、零事件**;co_substrates=[C=C=O] 保留 |
| `CCO.CC→CCOCCCC`(不平增强) | 1 spec(反证"不平自动拒"不成立) | 0 池 spec、零事件 |
| `CCO.c1ccncc1→CC=O+C1CCNCC1`(不可锚辅因子) | 编译层 new_atom_placement_incomplete 拒 | **编译前同因拒**(不再依赖编译层兜底;拒因前移) |
| `CCO.CC→CC=O+CC`(共组分恒等) | 编译层拒 | 编译前同因拒 |
| `CCO.CC→CCO+C=C`(底物恒等仅共组分变) | 编译层拒 | 编译前同因拒 |
| `CCOC(C)=O.O→CC(=O)O+CCO`(corpus 水解,水=共底物) | **1 compiled spec + 1 事件(水折成 add_atom 新原子)+ matched_strict(v4 正控即此形态)** | **0 池 spec、零事件**——新 component 水解如实拒并披露(见 §六诚实边界) |

修前复现脚本与输出:`repro_bad_forms/`(基线 3725379,三案
compiled/add_atom 证据);修后同脚本输出 0 spec + 拒因(本轮
证据目录)。**受影响供给零坏 spec、零坏 event**。

**无关合法写入逐项披露(不伪报整批零写入)**:正控 3 案
(整串氧化 `CCO→CC=O`、whole 多组分 `CCO.CC→CCOCC`(底物=
donor 全串)、EAWAG 水解 `CC(=O)OC→CC(=O)O+CO`)各执行公共
start:池 1 spec、原生事件 1 条(参与物从 events 表+states 复原:
反应物=底物、产物=记录产物,EAWAG 水解含共产物甲醇;无共底物
"幽灵原子"参与物)、`read_native_export` 首读真实 payload、
`match_reference_edges` 均 **matched_strict**、resume 各 17 业务表
零增量、hypothesis transformation_ref=源行键(可追溯)。8 个坏
形态案均未启动 run(builder 池空 ⇒ 零写入、零预约、零检索 run)。

## 五、测试改动与新负控/正控族(`tests/test_ppv1_s5b_hit50_v4_wv41.py`,18→20)

**改掉的测试许可**(评审 §4.2 指认):
- `CCO.CC→CCOCC` 不再是可编译正控:RL 行测试(:359)改为断言
  结构化 unsupported(父 HEAD 该行授 spec=真行为红);
- 酯水解组分正控(:312)改为诚实拒负控(断言 compile is None +
  拒因 + detail 可追溯:record_key/行号/donor 整串/方向/master/
  共底物声明/记录产物/permission_note);
- 池测试(:752)corpus 行改为整串行(CCO→CCCO 合成接线夹具,
  W2 夹具纪律);component 行断言零池槽+拒因计数(父 HEAD 3 槽
  =真行为红);e2e(:876)改整串底物(丙醇→丙酸),事件参与物
  从 sqlite 原生核(reactants=={底物}、products=={记录产物})。

**新增负控族**(`test_wv41_cosubstrate_component_reject_family`,
:412):同根 LR/RL、可锚有机(CC)、不可锚断连辅因子(吡啶)、
不同元素(S)、未知角色(苯)、配平增强(乙烯酮)、仅共组分
变化(底物恒等)、重复组分(CCO.CCO)——9 候选全拒、单一类目
`corpus_cosubstrate_participants_unsupported`、无例外;同批整串
氧化 + whole 多组分正控照旧编译入池。

**新增正控**(`test_wv41_eawag_hydrolysis_capability_preserved`,
:836):旧 EAWAG 水解能力(单组分 donor 酯、记录自身不声明共底物)
经 `find_recorded_exact`(字节零改动)照旧编译(产物多重集核)
并入池——"记录不声明共底物"(EAWAG 型隐式书写)与"记录声明
共底物但被丢弃"(corpus component)两形态分界保持。

真 corpus 实盘用例(:517)更新:master 10000 戊酰胺+水组分级
候选修后为编译前拒(拒因+水声明保留);`mapping_origin` 恒
inferred 断言保持。

**父 3725379 同字节红绿**(worktree + 新测试字节覆盖;证据
`parent_red_green/`):
- v4 文件 7 红/13 绿,w23456 1 红/21 绿;
- **真行为红 5**(父授坏 spec:组分水解 spec、RL 缩合 spec、
  拒族 spec、池第 3 槽坏 spec、坏 spec 池);
- 版本/字面量红 2(corpus-retrieval-2、pool-policy-3 字面量);
  拒因标签红 1(rhea:10001 父上也无 spec,父拒因=charge_edit_
  unsupported,本轮前移为许可拒因——标签变化非 spec 存在性翻转,
  如实分类);
- 合法正控绿:整串编译+执行、e2e 整串批、EAWAG 水解保持、
  neg1–neg11 行级负控、w23456 行为测试全绿。

## 六、受影响供给前后对照(298 题池深探针;只读 substrate_smiles)

命令:`~/miniconda3/envs/depending43/bin/python -B
/private/tmp/s5b_v4_r1_probe/pool_depth_v3v4.py`(v3 臂=
`corpus_channel=False` 单变量对照;真引擎+真 corpus;输入=
run_inputs 的 `substrate_smiles` 字段——任务书 §2 批准字段,
**不是**题面/run 零读取,如实登记;金标/products 零读取)。

探针结果(输出 `/private/tmp/s5b_v4_r1_probe/pool_depth_result.json`,
已复制至证据目录 `pool_depth/`;v4 交付书 §六 修前数字为对照):

**§六.1 池深/空池率前后(单变量:v3 臂=corpus_channel=False)**:

| 口径 | v3 臂 | v4 臂(修前,3725379) | v4 臂(修后,R1) |
|---|---|---|---|
| 池深 mean / median / max | 0.477 / 0 / 4 | 0.570 / 0 / 4 | **0.477 / 0 / 4(=v3 臂)** |
| 空池率(空池题数) | 64.43%(192/298) | 61.41%(183/298) | **64.43%(192/298,=v3 臂)** |
| 池直方图 0/1/2/3/4 | 192/81/19/1/5 | 183/80/24/2/9 | **192/81/19/1/5(=v3 臂)** |
| 槽净增/净失题数 | —(基线) | +21 / 0 | **+0 / 0** |

**§六.2 corpus 供给面前后(组分级供给诚实 unsupported 化的量)**:

- 修前:42 个最终池留存 corpus spec / 33 题(整串 14 / **组分 28**;
  strict 38 / cn 4;LR 17 / RL 25);池槽 +21(全部由组分 spec 贡献)。
- 修后:**14 个 corpus spec / 13 题(全部整串 whole)**;组分级供给
  spec **归零**;14 个整串 spec 与既有池(EAWAG/analog)同净反应
  签名合并(合并 provenance 留痕)⇒ **池深/空池率回到 v3 臂,零净
  槽变化**——corpus 直通通道修后的净池贡献=0(检索/候选面仍在,
  供给面收缩为整串且与既有池去重)。
- 候选级诚实 unsupported 化的量:**1,323 个 component-with-
  co-substrate 候选拒**(298 题检索面内,raw_top=24 截断后;
  `corpus_cosubstrate_participants_unsupported` 单一类目,无例外)。
- 检索面零变化(与修前同):256/298 题有 ≥1 corpus 候选、199 题
  有 ≥1 strict 层候选、master 多行命中 22 题(检索候选分层计数,
  非编译/供给数)。

**§六.3 失败直方图(修后,事件计数;行级类目与修前逐一相同)**:
corpus_cosubstrate_participants_unsupported **1,323**(新增,最大
类——全部 component 候选编译前拒)、unsupported_wildcard_atom
1,869(同修前)、corpus_provenance_missing 371(同)、
record_missing_or_incomplete 143(同)、transform_no_change 27
(同,整串层)、stereo_edit_unsupported 18(修前 310——差值全部
为 component 候选,已并入新类目)、no_alignment 22(修前 170)、
mapping_enumeration_truncated 5(修前 275)、charge_edit_
unsupported 3(修前 104)、product_set_mismatch 4(修前 19)、
ambiguous_mapping 2(修前 3)、new_atom_placement_incomplete/
new_atom_charge_unsupported/no_structure_correspondence/
aromatic_new_bond_unsupported **0**(修前 236/149/73/10——全部为
component 编译路径拒因,随编译通道关闭而消失)。**直方图迁移
语义**:component 候选的原编译层拒因(含修前 42 个"编译成功")
统一收敛为单一编译前许可拒因;整串(whole)路径的拒因逐类保持。

**诚实边界(先行落字)**:
- 检索面(匹配行/分层计数)零变化——被拒候选仍在检索面如实
  计数(`n_strict_exact`/`n_cn_candidate` 是检索候选分层,不是
  已编译/已供给数;新增 `n_cosubstrate_participants_unsupported`
  专用计数逐层机读);
- v4 交付"42 spec/33 题"按复审订正为**最终池留存数**(非候选
  编译通过率);本轮组分级供给归零是**许可收缩**,非命中数变化;
- corpus 水解(component 型)本轮一并诚实拒——与 EAWAG 旧水解
  能力的分界=记录是否声明共底物(§五正控);不给无机器证据的
  同类例外;
- 池深/空池率是供给侧中间指标,不冒充科学达标;命中数只由
  新批同口径零 LLM 判分判定(不自行点火);
- **未执行/待核面如实标注**:真实 298 漏斗逐题执行、chain11 发车、
  当日价格核对均为未执行待核(复审 §7 发车义务;本轮零真实模型
  调用零费用);池深探针为离线供给侧聚合(298 底物只读
  substrate_smiles),非逐题 run 执行数。

## 七、回归与隔离证据(四组)

| 组 | 命令/证据 | 结果 |
|---|---|---|
| 定向(新+既有族+金额) | `pytest tests/test_ppv1_s5b_hit50_v4_wv41.py + w23456 + v3_wv1/wv2/wv3/wv6 + s5b_runtime + v3r1_scope + v3r1{r2,r3}_cost -q` | **207 passed**(新 20 + 既有 187[含金额 72 R1 19/R2 28/R3 25];0 回退) |
| 全量 | `pytest tests/ -q -m "not slow"` | **1978 passed / 0 failed / 16 deselected**(基线 1976 + 2 新;322.6s) |
| G01 隔离 | `/private/tmp/safe_g01_s5b_hit50_v4_r1.py --repo … --out /private/tmp/g01_s5b_hit50_v4_r1` | **1967 passed / 10 skipped / 17 deselected, exit 0**(= v4 G01 1965 + 2 新测试,精确兑现;318.9s;328 输入 SHA 前后复验**零失配**;改动集双基线 diff 脚本强制核对通过:vs r3 G01 3 换字节、vs v4 G01 **4 换字节 0 新增 0 缺失**;实际 HEAD 3725379+dirty 记录;7 个游离 .pyc 如实记录[仅隔离树];证据 `g01/`) |
| 父基线红绿 | worktree 3725379 + 新测试字节 | §五(5 行为红 + 2 版本红 + 1 标签红;34 绿) |

(全量/G01 stdout 与 junit 已存证据目录 `logs/`;G01 输入
SHA/preparation/post_run 哈希随其输出目录。)

## 八、金标边界自查

- 预测侧零金标:改动只在 corpus 适配许可与池版本;池深探针只
  消费 run_inputs `substrate_smiles`(批准字段,如实登记访问
  范围);金标/products/旧答卷/封存逐题 run 零读取;判分零 LLM;
  合成夹具与真实 298 金标零重叠(W2 夹具纪律);
- 公开链探针在 fresh `/private/tmp` 隔离树执行(`-B`、socket
  封禁、旧评审证据只读、脚本独立重写);仓内证据目录只收脚本
  副本与输出文本,不在永久目录跑任何写库脚本;
- 冻结判据/scorer/评测尺子/AtomTool 零触碰(§一);池策略升版
  是供给侧版本号,非判分尺子;EAWAG 面字节级零改动;
- 对外数字带题域标签(298 题域检索/池面聚合计数,不外推 dev,
  不冒充命中数)。

## 九、待复审残留(不预支批准)

1. **[P1 后续设计轮] 显式共底物参与物语义**(mimo r30 R2-2 /
   v4 任务书 §4.2 设计件):角色拆分(cosubstrate vs 条件参与物)、
   声明式拷贝 vs 执行式生成、产物多重集 gate 扩展("执行 ∪ 声明
   拷贝")——须独立自包含设计+化学评审后落地;本轮诚实拒是
   R2-2 允许的保守处置,不是该设计的替代;
2. **mimo r31 请求已落盘**(`docs/mimo_ppv1_chem_review_request_
   r31.md`:H1 诚实拒许可范围/整串不配平记录分界、H2 披露语义、
   H3 与 R2-2 关系收口;零金标零题面规则级自包含)——按 AGENTS.md
   通道 A 送审、回复与程序证据互证;
3. **v4b 诊断细分族**(mimo r30 R1-2/R3-1/R3-2/R3-3 + EAWAG
   索引键归一差异):维持 v4 交付 §十一 #3 登记不动;
4. **发车前置**(复审 §7):chain11 新登记/新身份/双门/冒烟/
   budget_guard 机器配置沿用——本轮不自行点火,池成员变化
   (pool-policy-3)随新登记冻结;
5. R3-2 一般配平门维持 v4b 选项(本轮未加源数据完整性门;
   现行链路对不平记录的处置=许可拒/编译诚实拒,不冒充配平已核)。

## 十、对本轮前置文档事实文字的订正登记(不回写历史快照)

Codex v4 复审已指出的事实错误,在本交付订正如下(历史文档
[v4 交付书/任务书/Codex 报告]保持原字节不回写,以本节为订正
记录):
- v4 交付 §七"父基线红(18/18 收集失败)"⇒ 实为**1 文件导入
  失败、18 条未执行**(ImportError≠行为红);本轮父红绿按
  行为/版本/标签分类(§五);
- v4 交付 §六"候选面编译通过率 42/1,421≈3.0%" ⇒ 42 是
  **最终池留存供给比**(去重/截断后),非全部候选编译通过率;
- "33 题"是最终池含 corpus 的题数,**不是 33 净新增可答**;
- "204/267 含有机共底物"是**碳数零否的代理统计**,不能证明
  204 题已执行 partial 或无 strict 通路(§4 公开反例已反证该
  全称);
- "现行所有不平记录都会拒" ⇒ 撤回:现行链路只核对应与产物
  重现,配平 unknown(评审 balanced 案 1 spec 即反例;R3-2 门
  留 v4b);
- CN 覆盖差机理限定"质子化态+立体"两类(**不含互变异构**;
  Uncharger 归一失败会静默回退立体盲比较——r30 R1-2 计数留
  v4b);`CCCO` 与 `[13CH3]CCO` CN 同而 strict 异(同位素轴)。

## 十一、本轮改动清单(提交内容)

- `src/pathway_v43/pollutant/recorded_source.py`(+~100 行):
  共底物 component 编译前拒分支(结构化 unsupported+可追溯
  detail);`CORPUS_RETRIEVAL_VERSION` 升 2 + 语义键修订;诊断
  新增 `n_cosubstrate_participants_unsupported`;EAWAG 路径与
  `compile_recorded_reaction` 零改动;
- `src/pathway_v43/pollutant/s5b_builder.py`(+~10 行):
  `S5B_POOL_POLICY_VERSION` 升 `s5b-pool-policy-3` + 注释;消费侧
  零新增过滤;
- `tests/test_ppv1_s5b_hit50_w23456.py`(2 处字面量):
  pool-policy-2→3;
- `tests/test_ppv1_s5b_hit50_v4_wv41.py`(重定许可+新增,18→20):
  §五全部;
- 本交付书 + mimo r31 请求(`docs/mimo_ppv1_chem_review_request_
  r31.md`);
- 证据目录 `docs/review_evidence/ppv1_v4_r1_impl_2026-10-10/`
  (未跟踪:公开链探针脚本+输出、修前复现、池深探针、父红绿、
  回归日志、G01 输出引用)。
