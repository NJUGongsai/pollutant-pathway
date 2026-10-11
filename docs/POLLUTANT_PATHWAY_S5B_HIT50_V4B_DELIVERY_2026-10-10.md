# PPV1 S5b HIT50 v4b 交付书 —— 编译墙深层修复
# (P1 stereo 消解 / P2 推断映射深层门扩展 / P3 诚实计量与版本;2026-10-10)

状态:`implementation_ready_for_review`(交回主会话复审;不自行
点火 298)。任务依据:v4b 任务书(编译墙攻坚,最大未兑现面;
mimo r28 E1-E3 评审方向)。红线继承:AGENTS.md + v2 任务书 §1 +
v3/v4/R1 交付链。

- 开工基线:HEAD = `8d92f3aa`(v4 复测轮收口;开工记录实际 HEAD);
  工作树跟踪文件干净(评审侧未跟踪文档不动);
- 本轮改动 = 3 个源文件 + 5 个测试文件(4 改 1 新)+ 本交付书
  (§十一提交清单);
- 实施期**零真实模型调用、零花费、零网络、不 push**;金标/题面/
  封存逐题 run 零读取(漏斗统计只读 `reports/ppv1_s5b/s5b_298_local/
  run_inputs/*.json` 的 `substrate_smiles` 字段与仓内授权语料资产
  ——批准字段访问,如实登记);
- **不碰红线逐条兑现**:co-substrate 许可规则
  (`corpus_cosubstrate_participants_unsupported`,另一设计线主权)
  零触碰(本轮两通道该拒因事件数逐字节不变:corpus 1,323 /
  EAWAG 0);冻结判据/scorer 匹配排序/三冻结 SHA 零触碰;金额
  守卫族零触碰;**AtomTool 全局工具零改动**(P1 执行价态墙的
  最小改动面探明并登记 §十.1,不擅改)。

## 一、三件工作包修法一句话

- **P1(mimo r28 E1-E3 落地,S5b-stereo-dissolution-1)**:公共编译器
  `s5b_compiler` 把"手性 sp3 中心随 single→double/triple 键级变化
  消解"从 `stereo_edit_unsupported` 拒面移出——谓词四条件钉死
  (lhs 真四面体标签 ∧ rhs 无手性声明 ∧ 该原子全 lhs 键单键 ∧
  该原子涉及的全部键变化均为 change_bond_order 型 ∧ ≥1 个该型
  变化),执行后 rhs 立体同源复核(`stereo_derived_mismatch` 结构化
  拒),spec 机读诊断 `stereo_dissolution_applied`;
- **P2(S5b-recorded-infer-2)**:推断映射公共判据链的预算升档
  (`_INFER_MATCH_LIMIT` 200→800、`_INFER_BOND_DIFF_CALL_LIMIT`
  512→8192)+ fallback 前置必要条件 fast-fail(元素包含/原子数,
  零语义变化)+ 加成/生成分支全组分枚举(旧 `break` 丢后续组分候选)
  ——判据零放宽:产物多重集 gate 不放宽、触顶诚实拒、
  product_set_mismatch 缺行诚实拒维持;
- **P3(诚实计量与版本)**:两通道漏斗逐记录前后对照(298 题零
  模型离线,基线 worktree 8d92f3aa 同脚本复跑),编译通过数不冒充
  命中数;版本升版 `s5b-compiler-2` / `s5b-recorded-source-2` /
  `s5b-pool-policy-4`(池成员变化;池策略配置零变化),身份随
  既有 `run_identity.code_identity` 文件哈希机制入新批。

## 二、入口消费矩阵(共用入口;每入口消费的身份/事实/版本/拒因)

| 入口 | 消费 | 本轮变化 |
|---|---|---|
| `s5b_compiler.extract_mapped_transform` | 模板双侧 map 联结变换表 | 新增 `stereo_dissolved_maps`(消解谓词分类;`stereo_changed_maps` 剔除消解例);全仓消费方 = `compile_donor_template` + `recorded_source._changed_maps`(键差端点/离去中心,不消费立体字段) |
| `s5b_compiler._compile_edits` | 变换表 → 编辑协议 | stereo 门只拒非消解残差(charge 门原样);消解例经键级编辑表达,无立体 op |
| `s5b_compiler._compile_donor_template_impl` | 编译主入口(对齐/编辑/执行) | 执行后立体同源复核(E2-③);spec.compile 新增 `stereo_dissolution_applied` + 语义说明(E2-④) |
| `recorded_source.infer_reaction_mapping` | 推断映射(两通道共用) | 预算升档 + 加成分支全组分枚举 + fallback fast-fail 前置必要条件 |
| `recorded_source.compile_recorded_reaction` | 库记录 → 池 spec | **零判据改动**(产物多重集 gate/歧义披露/触顶拒全部原样;消费新枚举面) |
| `recorded_source.find_recorded_exact`(EAWAG)/ `find_corpus_recorded_exact`(corpus) | 检索/分层/候选装配 | **字节级零改动**(分层/许可/拒因语义不动;EAWAG 引擎 lookup 序不动) |
| `s5b_builder.default_pool_provider` | 池供给(3 通道融合) | 零逻辑改动;`S5B_POOL_POLICY_VERSION` 升 `s5b-pool-policy-4`(池成员变化 ⇒ 升版;raw/池宽/阈值/补位/融合/去重全部不动) |
| worker/runflow 事件链 | plan.pools specs | 零改动(spec 新增 compile 诊断字段,prepare_hypothesis 忽略未知字段,e2e 走通) |
| `services/atom_tool.execute_edits` | 执行器 | **零改动**(消解 = sanitize 自然结算;显式氢价态墙如实走 execution_failed) |

## 三、P1 stereo 消解(S5b-stereo-dissolution-1)

### 3.1 r28 E1-E3 条款逐条落地

| r28 条款 | 落地 |
|---|---|
| E1-1 stereo_created(sp2→sp3 新增立体中心)必须排除 | 谓词第 1 条:rhs 原子必须 CHI_UNSPECIFIED;lhs 无声明→rhs 有声明 ⇒ 不满足 ⇒ 维持 `stereo_edit_unsupported`(负控 `test_p1_stereo_creation_rejected`) |
| E1-2 仍为四面体中心的断/成键(有机磷/硫、SN2)必须排除(键序重解读=静默翻转) | 谓词第 3 条:该原子涉及的全部键变化必须 single→double/triple(form/break 落在该原子 ⇒ 不满足);负控 `test_p1_sn2_ligand_exchange_rejected`(Cl 离去+Br 到达+构型翻转书写 ⇒ 拒) |
| E1-3 E/Z 键立体盲区如实披露 | 编译器模块 docstring 落字:检测面为原子四面体标签,E/Z 不在放行面也不在拒面(执行产物 E/Z 未指定,对声明 E/Z 的参考走 cn_only 如实 miss,不静默断言) |
| E1-4 非四面体/累积烯 | 谓词第 2 条:该原子全部 lhs 键必须单键(sp3)——累积烯中央原子(双键)与 sp2 中心天然不满足 ⇒ 不消解 |
| E2-① 仅 change_bond_order 型可进放行评估 | 谓词第 3 条(键表顺序不变,无 CW/CCW 重解读风险) |
| E2-③ 执行后 rhs 立体同源复核 | `_stereo_dissolution_mismatch`:执行产物在该 map 的立体状态 ≠ CHI_UNSPECIFIED(或映射缺失/产物不可解析)⇒ 结构化 `stereo_derived_mismatch` 拒(机读证明测试 `test_p1_post_execution_homology_mismatch_rejects`;真实化学路径下该门为防御性——显式氢价态墙先行) |
| E2-④ 机读诊断 | `spec["compile"]["stereo_dissolution_applied"]` + `stereo_dissolution_semantics`(供下游统计"多少 strict 命中依赖消解") |
| E2-⑤ E/Z 两头写清 | 模块 docstring + 本交付 §3.3 |
| E2-⑥ real_model capability/提示词同步改版 | **不采纳本轮实施**(登记 §十.2):capability 串描述的是模型侧 novel 编辑协议面(无 stereo op,仍然为真);recorded/analog 池模板的编译侧消解不经模型提议;mimo 自述该项是"供给侧变更须独立批归因"——与编译轮分离,留待复审裁定 |

### 3.2 正负控(公共链)

正控(合成同构用例,与真实 298 金标零重叠):

- **二级醇氧化成酮**(`[CH3:1][C@H:2]([OH:3])[Cl:4]` →
  `[CH3:1][C:2](=[O:3])[Cl:4]`,底物无手性声明):编译通过,唯一
  编辑 = `change_bond_order single→double`;production 层
  `reaction_center_match`/`strict_target_match` 均 True;**公共链
  执行成事件**(compile→prepare→AtomTool→donor 诊断→audit→
  admission→store→export;sqlite 事件参与物核对:反应物={底物}、
  产物={酮})——`test_p1_secondary_alcohol_oxidation_compiles_and_
  executes`;
- recorded 通道同构(手性 donor + 非手性底物,cn 层形态):推断映射
  编译,产物多重集 gate 核对一致(`test_p1_recorded_channel_
  chiral_donor_compiles`);
- 授权语料实盘(v3 边界冻结负控翻转):`env:EAWAG-BBD:bt0002#r0032`
  在非手性底物 `CC(O)c1ccccc1` 上编译通过(target=苯乙酮,
  dissolution=[2]);资产缺席则 skip(`test_wv3_stereo_dissolution_
  boundary_now_compiles`)。

负控族(r28 反例全拒,父 HEAD 同绿——不变量):

- 纯立体翻转(无键级变化)维持 `stereo_edit_unsupported`;
- stereo_created 维持拒;
- SN2 型配体交换(断/成键落在现存立体中心 + 构型翻转)维持拒;
- **手性声明底物(显式氢)**:消解开后执行价态墙 —— `[C@H]` 括号
  氢使 single→double 后显式价超限,`execution_failed`(诚实拒,
  不冒充消解;AtomTool 最小改动面见 §十.1);
- 同源复核负控(monkeypatch 执行器返回残留标签产物)⇒
  `stereo_derived_mismatch` 结构化拒 + helper 直测(UNSPECIFIED 通过/
  非 UNSPECIFIED/缺映射失配)。

### 3.3 EAWAG 38 例与 corpus stereo 类恢复面(修前后漏斗;298 题零模型)

EAWAG stereo_edit_unsupported 38 次事件(36 题)修后迁移(逐记录
join,证据 `/tmp/s5b_v4b_impl/funnel_{before,after}.json`):

| 修前(38) | 修后 | 数量 | 说明 |
|---|---|---|---|
| stereo_edit_unsupported | **compiled** | **1** | `bt0002#r0032`(1-苯乙醇→苯乙酮),底物无手性声明(cn 层)——恰为 v3 审计的 v1 命中模板类;编译题数 71→72 |
| stereo_edit_unsupported | execution_failed | 5 | `bt0002#r0032`×4 题(手性底物,strict 层)+ `bt0002#r1147`(甾体 17-酮醇,多手性中心):消解谓词通过、执行撞显式氢价态墙(§十.1) |
| stereo_edit_unsupported | stereo_edit_unsupported | 32 | 24 次 = **stereo_created**(donor 无手性、产物声明手性——r28 E1-1 必须拒,且即便放行也会被产物多重集 gate 以 strict 立体身份拒);8 次 = 翻转/保留型(仍为四面体中心) |
| corpus stereo_edit_unsupported | 18→18 | — | 全部为翻转/邻二醇→环氧化物型(产物保留手性中心,非消解型)——0 恢复 |

**诚实结论**:P1 在 298 题两通道的**直通编译恢复面 = 1 题**
(EAWAG bt0002#r0032 非手性底物;池层净 +1 槽,见 §五);其余
stereo 失败面被 r28 反例边界如实拦住(stereo_created 24——放行
即假阳性,不修)或撞执行价态墙(6——AtomTool 配合属待复审最小
改动面,不擅改)。analog 通道(共用编译器)的恢复面见 §五池深
对照(93 stereo 事件 → 83:1 例编译与 EAWAG 同净反应合槽、
9 例价态墙)。

## 四、P2 推断映射深层门扩展(S5b-recorded-infer-2)

### 4.1 预算升档(触顶类;判据零放宽)

- `_INFER_MATCH_LIMIT` 200→800、`_INFER_BOND_DIFF_CALL_LIMIT`
  512→8192。**依据(实测)**:修前触顶事件 11(EAWAG 6 + corpus
  整串 5)的 donor 键数实测分布 = 18/28/28/28/28/30(EAWAG)与
  ~45(corpus 腺苷三磷酸型);旧 512 调用预算对 >31 键 donor 的
  k≤2 全枚举(n(n+1)/2)不足,且 28 键级 donor 的删键组合像数
  超 200 匹配上限 ⇒ 触顶。8192 覆盖 donor ≤127 键的全 k≤2 枚举,
  800 覆盖 4× 像数;触顶语义不变(超上限仍 truncated 诚实拒,
  monkeypatch 夹具预算测试维持)。
- **修后触顶率 = 0/298 两通道**(修前 11)——触顶类全部转出
  截断拒;但**诚实披露**:转出的 11 例无一编译通过——EAWAG 6 例
  恢复映射后撞 `charge_edit_unsupported`(保留边界:v3 W5 电荷
  不动,EAWAG charge_edit 36→42 恰为 +6);corpus 5 例为磷酸
  去质子化形态的 cn 候选(donor `[O-]` vs 底物中性),全枚举后
  如实落 `no_alignment`(模板电荷形态 ≠ 底物;corpus no_alignment
  22→27 恰为 +5)。**预算升档兑现的是"触顶不再截断枚举面",
  不是编译通过数**;
- **墙钟净效应 ≈ 0**:两通道全程漏斗探针 1,141.8s(修前 worktree)
  vs 1,148.8s(修后;+0.6%)——fast-fail 前置抵消预算扩大。

### 4.2 fallback 前置必要条件(fast-fail;零语义变化)

`_infer_bond_diff_fallback` 入口新增:donor 元素多重集 ⊄ 产物并集
或 n_donor > n_union ⇒ 直接空返回(子结构匹配必要条件,与
`template_elements_fit` 同纪律——判据单一来源的必要条件前置,不
新增第二套判据)。修前该类记录(语料真实无对应,EAWAG
no_structure_correspondence 69 的大头)白耗 512 组合调用;修后
零调用同判。行为零变化(同返空 ⇒ 同 no_structure_correspondence)。

### 4.3 加成/生成分支全组分枚举

旧实现在首个可容纳 donor 的产物组分后 `break`(丢后续组分的候选
对应);修后全部组分在预算内枚举,候选映射交由编译 + 产物多重集
gate + 落位纪律全映射评估(W-V2.3 同源)。**诚实披露**:298 题两
通道实测恢复面 = 0(多组分产物并集下,跨组分新原子无锚 ⇒ 落位
纪律如实拒,枚举面扩大不改变编译结局);机制价值 = 候选对应
枚举完整性(合成正控 `test_p2_addition_branch_enumerates_all_
components`:两组分像均在候选内、判据不放宽)。

### 4.4 placement 类落位调查(诚实拒维持)

- corpus 236 类(v4 修前直方图)已全部被 R1 共底物许可规则接管
  (component 通道关闭;本轮零触碰,corpus 该拒因 1,323 逐字节
  不变),整串面修前修后均为 0;
- EAWAG placement 1 例(逐记录定位):`EAWAG-SEDIMENT:#76c273f5-…`,
  donor = N-甲基-2-萘基氨基甲酸酯,记录产物 = `C(=O)=O` +
  羟基化产物——**记录本身原子不守恒**(产物 C13 N O5 vs donor
  C12 N O2,凭空 +1C+3O),孤立新原子组分(CO₂)无锚不可落位 ⇒
  `new_atom_placement_incomplete` 诚实拒维持。**判级**:数据缺陷,
  非代码缺口;R3-2 记录自洽配平门(mimo r30)继续登记为独立选项
  (本轮不加新门,不预支)。

## 五、两通道漏斗前后对照(298 题零模型离线;逐记录 join)

探针:`/tmp/s5b_v4b_impl/funnel_perrecord.py`(BEFORE = 基线
worktree `8d92f3aa` 同脚本,AFTER = 仓内新代码;只读 run_inputs
substrate_smiles;EAWAG `find_recorded_exact` + corpus
`find_corpus_recorded_exact`,max_reactions=24;证据
`funnel_before.json` / `funnel_after.json`,聚合+逐记录)。

**EAWAG 通道(候选级失败事件直方图)**:

| 拒因 | 修前 | 修后 | 迁移说明 |
|---|---|---|---|
| no_structure_correspondence | 69 | 69 | 语料真实无对应(fast-fail 同判零语义) |
| product_set_mismatch | 33 | 33 | 缺行诚实拒维持(0 恢复,判据不动) |
| charge_edit_unsupported | 36 | 42 | +6 = 触顶类转出后撞电荷保留边界 |
| **stereo_edit_unsupported** | **38** | **32** | **-6:1 编译 + 5 价态墙(§3.3)** |
| new_atom_charge_unsupported | 14 | 14 | 电荷保留边界 |
| no_alignment | 17 | 17 | cn 层 donor ⊄ 底物,如实 |
| mapping_enumeration_truncated | 6 | 0 | 预算升档(转出:6→charge) |
| execution_failed | 3 | 8 | +5 = 消解开后的显式氢价态墙(§十.1) |
| 其余(ambiguous 1/aromatic 3/partial_dearom 3/placement 1) | 8 | 8 | 逐项不变 |
| **编译成功题数** | **71** | **72** | **+1(bt0002#r0032 非手性底物)** |

**corpus 整串通道(候选级失败事件直方图;行级拒因 wildcard 1,869/
provenance 371/missing 143/cosubstrate 1,323 修前修后逐字节不变,
本轮零触碰许可规则)**:

| 拒因 | 修前 | 修后 | 迁移说明 |
|---|---|---|---|
| stereo_edit_unsupported | 18 | 18 | 全部非消解型(§3.3) |
| mapping_enumeration_truncated | 5 | 0 | 预算升档(转出:5→no_alignment,磷酸形态 cn 候选) |
| no_alignment | 22 | 27 | +5(同上;模板电荷形态 ≠ 底物) |
| 其余(charge 3/product_set 4/ambiguous 2/transform_no_change 27) | 36 | 36 | 逐项不变 |
| **编译成功题数** | **16** | **16** | **+0(检索面 199 strict 题不变)** |

**池深/空池率前后(单变量:corpus_channel 消融臂;`pool_depth_
v3v4.py` 双臂,298 底物;BEFORE = 基线 worktree `8d92f3aa` 同脚本,
AFTER = 仓内新代码;证据 `/tmp/s5b_v4b_impl/pool_depth_{before,
after}.json`)**:

| 口径 | 修前(v3 臂 = v4 臂) | 修后(v3 臂 = v4 臂) |
|---|---|---|
| 池深 mean / median / max | 0.477 / 0 / 4 | **0.480** / 0 / 4 |
| 空池率(空池题数) | 64.43%(192/298) | **64.09%(191/298)** |
| 池直方图 0/1/2/3/4 | 192/81/19/1/5 | 191/82/19/1/5 |
| 总池槽 | 142 | **143**(+1) |
| 槽净增/净失题数 | — | +1 / 0(只增不减) |

v4 臂与 v3 臂修前修后均逐项相同(corpus 通道净贡献 0——R1 状态
保持:13 题 corpus spec 全部与既有 EAWAG/analog 同净反应签名合并;
corpus 编译成功题数 16、检索面 199 strict 修前修后不变)。

**池侧恢复分解(逐 qid join)**:

- **净 +1 槽 = `RXNG_87e7556b108…`(1-苯乙醇→苯乙酮,0→1 槽,
  空池脱离)**:EAWAG `bt0002#r0032`(cn 层)与 analog 语料同模板
  (`env:EAWAG-BBD:bt0002#r0032`)按同净反应签名合并为一槽
  (merged provenance 留痕);该槽 spec 携带
  `stereo_dissolution_applied=[2]`(池内消解 spec 总数 0→1);
- **v3 臂编译面直方图迁移(EAWAG+analog 融合口径)**:
  `stereo_edit_unsupported` 131→115(-16:EAWAG -6 见 §3.3,analog
  93→83:1 例编译成槽 + 9 例撞显式氢价态墙);`execution_failed`
  17→31(+14:EAWAG 5 + analog 9,全部为手性声明底物上的消解型
  模板);`mapping_enumeration_truncated` 6→0;`charge_edit_
  unsupported` 53→59(+6 = EAWAG 触顶类转出,§4.1);其余拒因
  逐项不变;
- **analog 通道零独占恢复**:analog 侧消解型编译成功 1 例与
  EAWAG 同净反应合并(不占新槽);v3 审计的"8 stereo 真供给损失"
  面里,其余模板的 298 底物多为手性声明形态(价态墙)或产物
  stereo_created,本轮零恢复。

**事件层**:池槽 100% 执行留存是 W1 编译门的结构性质(编译成功才
进池;e2e 正控证明链路);真实事件/命中数由新批同口径零 LLM 判分
判定,本轮不点火。**全部数字为检索/编译/池面聚合计数,不冒充
命中数;298 题域,不外推 dev**。

## 六、诚实计量与版本(P3)

| 版本 | 旧 → 新 | 理由 |
|---|---|---|
| 编译器 | `s5b-compiler-1` → **`s5b-compiler-2`** | P1 消解(公共编译判据链行为变化;spec 新增机读诊断) |
| recorded 公共源 | `s5b-recorded-source-1` → **`s5b-recorded-source-2`** | P2 推断映射预算/枚举面扩展(编译判据链行为变化) |
| 池策略 | `s5b-pool-policy-3` → **`s5b-pool-policy-4`** | 池**成员**变化(recorded 两通道 + analog 共用编译面的编译成功集变化);池策略配置(raw 24/池宽 8/阈值 0.45→0.40/补位/融合/去重)零变化 |
| corpus 检索语义 | `s5b-corpus-retrieval-2` **不变** | 检索/分层/许可语义零改动(find_corpus_recorded_exact 字节级零改动;编译面变化由 compiler/recorded-source 版本承载) |
| 代码身份 | 逐文件 SHA 自动重算 | 既有 `run_identity.code_identity` 机制,无手动登记 |

判据侧(scorer/evaluation/三冻结 SHA/S5B_PASS_LINES/participant
集合语义/match_reference_edges/主 K 候选定义)零字节改动。

## 七、回归与隔离证据(四组)

| 组 | 命令 | 结果 |
|---|---|---|
| 定向 | s5b 全家(w1/w23456/v3_wv1-wv6/v4_wv41/**v4b 新**/runtime/pairing/rework_l01/v3r1-3 cost)+ atomtool/donor/analog×3/edit/conservation/s3b_production | **410 passed / 0 failed**(276 s5b 家族 + 134 邻接族) |
| 全量 | `pytest tests/ -q -m "not slow"` | **1992 passed / 0 failed / 16 deselected**(基线 1978 + 本轮 14 新测试;324s) |
| G01 隔离 | `/private/tmp/safe_g01_s5b_hit50_v4b.py --repo … --out /private/tmp/g01_s5b_hit50_v4b`(沿 v3→r3→v4→v4-R1 血统:路径 allowlist、输入 SHA 前后全量复验、改动集 vs v4-R1 G01 输入集脚本强制双向核对、`python -B`、`-p no:cacheprovider`) | **exit 0;1981 passed / 10 skipped / 17 deselected**(317.5s;= v4-R1 G01 1967 + 本轮 14 新测试,精确兑现预期;输入 SHA 复验零失配;改动集强制核对通过:7 换字节 + 1 新增 + 0 缺失,与披露逐项一致;实际 HEAD `8d92f3aa`+dirty=true 记录于 preparation.json;7 个游离 .pyc 如实记录[仅隔离树子进程缓存例外,同前四轮模式]) |
| 父基线红绿 | 新/改测试字节覆盖到父 HEAD `8d92f3aa` 隔离 worktree | **14 红 / 65 绿**:红 = 8(v4b 新文件:正控消解编译/价态墙理由/预算字面量/fast-fail 新符号/加成分支全枚举/版本)+ 3(w1/w23456 版本字面量)+ 1(wv3 边界翻转正控)+ 2(wv41 立体夹具翻转/版本);绿 = 全部负控与不变量(纯翻转/stereo_created/SN2/门不动/标准路径/e2e 保持族)。import 前显式 sys.path.insert 指向 worktree src 并验证 `__file__` |

## 八、stereo 消解正负控结果(汇总)

- 正控 3 件全绿(合成二级醇→酮公共链成事件;recorded 通道 cn 形态;
  授权语料 bt0002#r0032);
- 负控 5 件全绿(纯翻转拒/stereo_created 拒/SN2 拒/显式氢价态墙
  诚实拒/同源复核 mismatch 结构化拒);
- 边界机读:消解例 spec 必带 `stereo_dissolution_applied`;非消解
  例拒因 detail 必带 `stereo_changed_maps`(w1 g10 既有断言维持)。

## 九、金标边界自查

- 预测侧零金标:漏斗/池深探针只读 run_inputs `substrate_smiles`
  (批准字段;v4b 任务书 §环境事实);金标/products/旧答卷/封存
  逐题 run 零读取;判分零 LLM;合成夹具与真实 298 金标零重叠
  (W2 夹具纪律;探针产物留 /tmp 易失目录);
- 语料消费沿授权资产包(corpus_v1/library/corpus_templates sha
  锚定回读;hash 不符 fail-closed 既有语义);BEFORE 探针在隔离
  worktree 执行(基线快照只读),AFTER 探针在仓内 src(未提交工作
  树,实际 HEAD+dirty 如实记录于探针输出);
- 冻结判据/scorer/评测尺子/AtomTool 零触碰(§二入口矩阵);版本
  升版是供给侧版本号,非判分尺子;co-substrate 许可规则零触碰
  (1,323 事件数不变);对外数字带题域标签(298 题域检索/编译/池面
  聚合计数,不外推 dev,不冒充命中数)。

## 十、待复审残留(不预支批准)

1. **[P1 后续最小改动面] AtomTool 显式氢价态墙**:手性声明底物
   (`[C@H]` 括号氢)上 single→double 键级变化使显式价超限 ⇒
   execution_failed(本轮 5+1 例)。最小改动面 = `atom_tool.
   execute_edits` 的 change_bond_order 路径允许端点显式氢随键级
   升高消耗(numExplicitHs-1,脱氢语义;~3 行 + 正负控)。**不擅改**
   (任务书红线:AtomTool 全局工具零改动);影响面 = 全部编辑执行
   路径(含 novel 通道),须独立红绿与复审;若批准,预期恢复
   strict 层消解型编译面(本轮 6 例事件级,题级约 4-5)。
2. **[mimo E2-⑥] real_model capability 串与提示词同步**:本轮判定
   不需要(capability 描述模型侧 novel 编辑协议,无 stereo op 仍真;
   编译侧消解不经模型提议);若复审认为须同步,属供给侧模型提示
   变更,须独立批归因(mimo 自述同款)。
3. **[既有键序重解读风险,r28 E1-2 附带披露]** 断/成键落在
   **同标签**四面体中心(SN2 同 [@H] 书写、不翻转)的模板**现状
   即可编译**(不落 stereo_changed,既有行为,本轮零变化)——
   RDKit 键表顺序变化可能静默翻转构型解读。本轮消解谓词已把
   "标签变化 + 断/成键"形态拒在门外;同标签形态的守门(执行后
   同源复核扩展到全部手性保留原子)属判据扩展,登记待复审。
4. **R3-2 记录自洽配平门**(mimo r30;本轮 EAWAG placement-1 例
   即其靶型:原子不守恒记录):维持独立选项登记,不本轮实施。
5. **corpus 整串编译面零恢复的诚实结论**:truncated 5 转出后落
   no_alignment(磷酸形态 cn 候选);stereo 18 全部非消解型;整串
   面的下一堵墙是电荷形态/去质子化变体的模板对齐(charge 保留
   边界)——属后续轮决策,不本轮放宽。
6. 发车前置:正链复审放行 + 新登记冻结(pool-policy-4 + 新
   code_identity 随 run_identity 落账)+ 冒烟前缀;本轮不自行点火。

## 十一、本轮改动清单(提交内容)

- 源码(3):`pollutant/{s5b_compiler, recorded_source, s5b_builder}.py`
  (消解谓词/同源复核/机读诊断;预算升档/fast-fail/全组分枚举;
  pool-policy-4);
- 测试(5):新 `tests/test_ppv1_s5b_hit50_v4b.py`(14 测试);改
  `tests/test_ppv1_s5b_hit50_{w1, w23456, v3_wv3, v4_wv41}.py`
  (版本字面量 ×3;v3_wv3 边界冻结负控翻转为 P1 正控(授权链
  r28 E1-E3 + 任务书);wv41 两处立体夹具按新判据修订);
- 本交付书;
- 证据(未跟踪,易失 /tmp):`/tmp/s5b_v4b_impl/`(基线/前后漏斗
  探针脚本与输出、池深探针、join 分析、RDKit 行为探针、
  placement/truncated/stereo 案例定位)、G01 输出目录、父红绿
  worktree `/tmp/s5b_v4b_before_wt/`(基线快照)。

## 十二、成本

本轮实施期真实模型费用:**0 CNY / 0 次调用**(全轮零网络、
零判分 LLM;漏斗/池深/G01/父红绿全部离线)。

---

# 附:hwall 补充节(2026-10-11)—— §十.1 登记项实施收口(S5b-hwall-1)

> 本节为 §十.1"AtomTool 显式氢价态墙最小改动面"登记的实施交付,
> 追加不改上方任何既有内容。授权链 = 本交付书 §十.1 登记 + mimo r33
> S3-b/S3-4(唯一推荐项:"不是化学边界而是执行器记账限制,列下轮
> 优先",采纳条件 ①②③)+ 主会话派工任务书。开工基线 HEAD =
> `59db0dac`(D2-R3 收口;工作树跟踪文件干净,评审侧未跟踪文档不动)。

## 十三.1 修法一句话与落点

- **修法**:`services/atom_tool.execute_edits` 的 change_bond_order
  分支在键级**升高**时,变化键**两端点**的括号显式氢
  (numExplicitHs,noImplicit 记账)按级差消耗(存量不足截 0)
  ——与隐式氢原子同口径(隐式 H 由 sanitize 按剩余价自动重算,
  括号原子固定记账才有此墙),消除执行器价态墙假阴性;
- **落点行号**:`atom_tool.py` 版本 `:63`;键级序数常量
  `_BOND_ORDER_N` `:87-89`;execute_edits docstring 脱氢记账语义段
  `:413-418`(mimo 条款 ③ 落字);放宽块 `:486-503`(SetBondType
  后,核心记账 5 行);
- **版本**:`ATOMTOOL_VERSION` v43-atomtool-1→**v43-atomtool-2**
  (执行器语义变化由版本承载);`EDIT_PROTOCOL_VERSION` 线协议零
  改动维持 v43-editproto-2(不变量测试钉死);编译器/recorded-
  source/池策略版本零变化(检索/编译判据链零触碰,§六表零改动);
- **mimo r33 采纳条件逐条兑现**:①只动 numExplicitHs——图中独立
  H 原子(含同位素 [2H])是真实图原子,零触碰(负控
  `test_hwall_isotope_h_separate_atom_still_wall`);②负控含"真实
  超价仍拒"(clamp/季碳无 H/form_bond/醚 O 四件)+"novel 通道全量
  重跑"(全量 not slow 2061/0 单次;novel 家族
  edit_protocol/phase_c/r2/r4/r5 全绿);③语义落字(docstring
  "键级升高 + 显式氢消耗 = 脱氢记账语义(执行器记账,非反应机制
  声明)")。

## 十三.2 EAWAG 离线漏斗前后(298 题零模型;沿 §五探针法,仅 EAWAG 通道)

- 探针 `/tmp/s5b_s5b_hwall/funnel_eawag.py`(`find_recorded_exact`,
  max_reactions=24;只读 run_inputs `substrate_smiles` 批准字段);
  BEFORE = 父 HEAD `59db0dac` 隔离 worktree
  `/private/tmp/s5b_hwall_before_wt`(`V3_CODE_ROOT` 指向仓外正本
  只读),AFTER = 仓内工作树;证据
  `/tmp/s5b_s5b_hwall/{funnel_before,funnel_after}.json`(逐记录);
- **恢复 5/5 全部命中**:§十.1 登记的 5 例 execution_failed
  (`bt0002#r1147` 甾体 strict + `bt0002#r0032` ×4)修后**全部
  compiled**;execution_failed 8→3(回到 v4b 前基线 3,其余 3 例
  与本墙无关零变化);**编译成功题数 72→77(+5)**——题级恢复 =
  登记自估"约 4-5"的上限 5;层级:strict_exact 3 qid + cn_candidate
  2 qid,"恢复 strict 层消解面"兑现;
- **单变量证明**:其余全部拒因直方图逐项相同
  (no_structure_correspondence 69 / product_set_mismatch 33 /
  charge_edit 42 / stereo_edit_unsupported 32 / no_alignment 17 /
  new_atom_charge 14 / aromatic 3 / partial_dearom 3 / ambiguous 1 /
  placement 1);n_qids_strict 147 不变;墙钟 1116.5s→1127.1s
  (+1.0%,噪声级)。全部数字为检索/编译面聚合计数,不冒充命中数;
  298 题域,不外推 dev。

## 十三.3 正负控清单(tests/test_ppv1_s5b_hwall.py,12 测试)

- **正控 6**(EAWAG 实盘形态的合成同构 + 真实授权语料形态):
  执行器层括号氢手性底物 single→double(双对映体书写)、级差记账
  (single→triple 每端点按级差耗 2 H)、非端点立体中心零触碰、
  recorded 通道 strict 形态(1-苯乙醇双对映体)、甾体多手性中心
  r1147 实盘同构(仅 17-醇中心消解)、production 层 novel 同根
  (reaction_center_match + strict_target_match 均 True);
- **负控 5**:clamp 真实超价(1 H 撞 triple 截 0 后仍拒)、季碳
  无 H 墙完整、form_bond 不在放宽面(显式氢不可洗非法编辑)、
  同位素 [2H] 独立图原子墙完整(条款 ①)、醚 O 非氢原子价态越界;
  **不变量 1**:EDIT_PROTOCOL_VERSION 不变(父同绿);
- **既有负控零回退**:w1 g9 六价碳、edit_protocol O 超价全绿;
  **既有边界负控授权翻转 2 处**:v4b
  `test_p1_chiral_substrate_valence_wall_honest_reject` →
  `test_p1_chiral_substrate_dissolution_now_compiles`、v3_wv3
  手性子例 execution_failed → compiled(翻转证明 = 父 HEAD 红,
  与 v4b 轮翻转 v3 边界负控同一先例模式)。

## 十三.4 四组回归

| 组 | 结果 |
|---|---|
| 定向 | s5b 全家(w1/w23456/wv1-wv6/v4_wv41/v4b/hwall/cosub_d2/runtime/pairing/rework_l01/v3r1-3 cost+scope)+ atomtool/donor/analog×3/edit/conservation/s3b_production 共 25 文件 = **479 passed / 0 failed** |
| 全量 | `pytest tests/ -q -m "not slow"` = **2061 passed / 0 failed / 16 deselected**(= 基线 2049 + 本轮 12 新测试;353 s) |
| G01 隔离 | `/private/tmp/safe_g01_s5b_hwall.py`(沿 …v4b→v4b_r1→cosub_d2→r1→r2→r3→**hwall** 血统:路径 allowlist、输入 SHA 前后全量复验、改动集 vs D2-R3 G01 输入集脚本强制双向核对) = **exit 0;2050 passed / 10 skipped / 17 deselected**(310 s;= D2-R3 2038 + 本轮 12,精确兑现;改动集强制核对通过:3 换字节 + 1 新增 + 0 缺失,与披露逐项一致;实际 HEAD `59db0dac`+dirty=true 记录于 preparation.json;7 个游离 .pyc 如实记录[同前轮模式]) |
| 父红绿 | 新/改测试字节覆盖到父 HEAD `59db0dac` 隔离 worktree = **9 红 / 29 绿**:红 = hwall 7(6 行为红:执行器双对映体/级差/非端点/recorded/甾体/production,父上全部 `sanitize_failed:AtomValenceException`/`execution_failed` 如实撞墙 + 1 版本字面量红 v43-atomtool-1≠2)+ v4b 翻转正控 1 + v3_wv3 翻转正控 1;绿 = 全部负控(clamp/季碳/form_bond/同位素/非氢/协议版本不变量)与 v4b/v3_wv3 未改测试(逐失败原因存 /tmp/s5b_s5b_hwall/parent_red_green/) |

## 十三.5 金标边界自查与成本

- 金标/题面/封存逐题 run 零读取;漏斗只读 run_inputs
  `substrate_smiles`(批准字段,沿 §五先例);语料消费 = 仓内授权
  资产包只读;判分零 LLM;合成夹具与真实 298 金标零重叠(W2
  夹具纪律);探针产物留 /tmp 易失目录;BEFORE 探针在隔离 worktree
  执行(基线快照只读),AFTER 探针在仓内工作树(实际 HEAD+dirty
  如实记录);
- 实施期真实模型费用:**0 CNY / 0 次调用**(零网络、零判分 LLM);
  不 push;
- 待复审残留:①影响面 = 全部编辑执行路径(含 novel 通道)——
  放宽语义已由 §十三.3 负控族钉死边界,但按 §十.1 既有登记仍属
  "独立红绿与复审"范围,交主会话复审;②本节落账后,298 两通道
  池成员预期再变(EAWAG +5 题入池;analog 侧同净反应合并面待新批
  实测),池策略版本未升——池成员变化由 code_identity 文件哈希
  自动入账,如需池策略版本语义化升版由复审裁定(不预支)。
