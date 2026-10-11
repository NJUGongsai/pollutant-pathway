# PPV1 S5b 共底物参与物语义 D2 编译实现轮交付书
# (S5b-corpus-retrieval-3 / s5b-recorded-source-3 / s5b-pool-policy-5)

状态:`implementation_ready_for_review`。

任务依据:设计书
`docs/S5B_COSUBSTRATE_PARTICIPANT_SEMANTICS_DESIGN_2026-10-10.md`
(方案 a + §五 全部规则 + §12 T-1~T-5 主会话默认档;D1 状态
`design_approved_with_conditions`)+ mimo r32 回应
`docs/mimo_ppv1_chem_review_response_r32.md`(16 条修改建议 +
NC-8..12/PC-4/5 控件矩阵;有条件通过)+ r31 措辞护栏
`docs/mimo_ppv1_chem_review_response_r31.md`(R31-1..R31-8)。
基线 64ef32c8(v4b-R1 收口提交;开工记录实际 HEAD
64ef32c8879aaa1330edbfab56357dc6090d7749)。本轮零模型、零金标
读取、零真实批、零 push。

- 实施期工作树改动:7 个已跟踪文件换字节 + 1 个新测试文件
  (G01 隔离脚本强制核对:7 换 + 1 新 + 0 缺失,逐项一致);
  金标/题面/封存逐题 run 零读取(CS2c/漏斗探针按任务书许可只读
  run_inputs 的 `substrate_smiles` 批准字段,如实登记);
- 判据零触碰:三冻结 SHA、scorer(`s5b_scoring.py`)、匹配排序
  (`evaluation.py`/`s5b_scoring.py` 判分与排序路径)、判分口径、
  AtomTool、`compile_donor_template` 编译判据全部零改动;
  `compile_recorded_reaction` 缺省路径(declared_copies=None)与
  `find_recorded_exact`(EAWAG)行为字节等价(§五证据);
  冻结判据一~五、participant 集合语义、match_reference_edges、
  主 K 候选定义与 (created_at, event_id) 顺序、分母 298 均未动。

## 一、修法一句话

**共底物 component 候选从"一律编译前拒"(corpus-retrieval-2,
298 面实测 1,323)升级为原子归属三分类守门三分支**:A-可溯/B-可溯/
不可归属三分后——整组分拷贝子集放行(B 进事件反应物侧参与物
role=cosubstrate、系数 unknown;B 来源整组分产物声明式拷贝、中心
unknown、不执行、来源记录字段完整;union gate = 执行 ∪ 拷贝 ==
记录全量产物多重集)、键合融合子集保守拒(
`cosubstrate_bonded_contribution_unsupported`,四轴子标签)、
不可归属原子保守拒(`cosubstrate_atom_source_unattributable`,
mapping_fallback 分列)——事件在现行 P1 参与物集合语义下恒判
`matched_participant_coverage_partial`(**结构性无 strict 通路,
NC-12 批级熔断钉死**;本通道对 hit@1 预期贡献 = 0)。

## 二、入口消费矩阵(AGENTS.md 返工教训 1:开工先列)

| 入口 | 消费 | 本轮变化 |
|---|---|---|
| `recorded_source.find_corpus_recorded_exact` | 检索+分层+候选装配+component 守门 | **三分类守门三分支唯一生效点**(classification→split/bonded/unattributable/unparseable/no_exec);spec 装配 participants/co_substrate_states/declared_copy_components/cosubstrate_event_contract;诊断 T-4 机读字段 |
| `recorded_source.compile_recorded_reaction` | 推断映射+编译+产物多重集 gate | **可选参数 declared_copies/record_products**(缺省 None ⇒ EAWAG/整串路径零触碰;扩展分支加 union gate + NC-4/NC-11 拷贝身份核对 + R32-CS3-2 键空间统一与一致性披露);`recorded-source-2→3` |
| `recorded_source._classify_cosubstrate_candidate`(新) | 原子归属三分类(编译器内部规则,不进事件协议) | 同源 `infer_reaction_mapping` + `_any_bond_query`(元素包含 + any-bond 子结构,B 归属预算沿用映射枚举纪律);mapping_fallback 检测 = "n_bond_diff" in mapping(标准枚举无该键,bond-diff fallback 恒 ≥1) |
| `production.prepare_hypothesis` | 池条目 spec → 假设+状态+工具输入 | **B/拷贝状态装配**(同源 build_product_state;声明 state_ref 与重建 ID 不一致 ⇒ 拒)+ **NC-10 事件级端到端不变量**(提交前断言:声明共底物 ⊆ reactant cosubstate refs ∧ 记录产物多重集 == 事件产物参与物多重集 ∧ 拷贝全被引用 ∧ NC-9 拷贝不进执行期望;任一不满足 ⇒ ProductionContractError 零事件零提交)+ cosubstrate_disclosure 机读返回 |
| `production.expand_hypothesis_production` | 执行→audit→admission→事件提交 | 生产报告 artifact 携带 cosubstrate_disclosure(无共底物 spec ⇒ 零字段零变化);固定链顺序零改动 |
| `s5b_builder.default_pool_provider` | 通道 1b 池供给 | 消费侧零新增过滤;`pool-policy-4→5`(成员变化);诊断 n_cosubstrate_declared_specs + count_unit/count_basis 标签 |
| `s5b_compiler.net_reaction_signature` | 池去重签名(W3/W4 共用) | spec 携带 declared_copy_components 时拷贝入签名(PC-3 同净反应合并不双占槽);**无拷贝 spec 签名逐字节不变**;编译判据零触碰(版本维持 s5b-compiler-3) |
| 公开 start/resume/导出/判分 | plan.pools specs / events | 零改动、无感(spec 字段经 JSON 往返,重建同 ID) |

## 三、版本升级登记(既有身份规则)

| 版本 | 旧 → 新 | 理由 |
|---|---|---|
| corpus 检索语义 | `s5b-corpus-retrieval-2` → **`s5b-corpus-retrieval-3`** | 共底物 component 许可变化(三分类守门三分支);检索宽/分层/通配/映射/provenance/双向语义零变化;语义键新增 `cosubstrate_event_semantics`/`union_gate_semantics`,修订 `donor_side_semantics`/`cosubstrate_permission`;`frozen_by` 登记 D2 依据 |
| recorded 公共源 | `s5b-recorded-source-2` → **`s5b-recorded-source-3`** | union gate 扩展(公共函数可选参数,落点子选项 i;收窄式扩展——多一道拷贝核对不是放宽);EAWAG/整串缺省路径行为字节等价(§五) |
| 池策略 | `s5b-pool-policy-4` → **`s5b-pool-policy-5`** | 池成员变化(component 共底物拷贝子集重新入池);池策略配置零变化(raw 预算/池宽/阈值/补位/融合/EAWAG 候选序/corpus_channel 语义不动) |
| 编译器 | `s5b-compiler-3` **不变** | 编译判据零触碰;net_reaction_signature 对无拷贝字段 spec 逐字节不变(注释钉死;新字段由 corpus-retrieval-3 定义) |
| 代码身份 | 逐文件 SHA 自动重算 | 既有身份机制,无手动登记 |

## 四、方案 a 实现位置(任务书报告项)

1. **事件表示**:`_attach_cosubstrate_spec_fields`(recorded_source)
   ——participants 显式列表(A=reactant/primary_substrate +
   逐 B=reactant/cosubstrate,系数全 unknown;主产物 +
   可执行 coproduct + 逐拷贝=product/coproduct,角色复用既有枚举,
   协议层零新发明;拷贝来源 component_source=record_declared_copy
   进 provenance 层的 declared_copy_components 披露,**不进
   Participant 计量层字段**)+ `participant_list_status=
   declared_complete`(T-2 主会话默认档)+ co_substrate_states/
   declared_copy_components(拷贝 execution_status=
   declared_not_executed + record_key/provenance_sha256,R32-CS1-1
   身份轴/生成轴分立)+ cosubstrate_event_contract(NC-10 记录侧
   输入);expectation.target_smiles = 可执行子集,拷贝不进
   edits/alignment/expectation(NC-9 断言)。
2. **原子三分类守门**:`_classify_cosubstrate_candidate`
   (recorded_source;§五.1/§五.2)——A-可溯(donor_to_union 覆盖)、
   B-可溯(断连全-new 组分,元素包含 + any-bond 子结构对应到单一
   B)、不可归属(元素超出 A∪B);确定性:按枚举序取首个干净二分,
   无二分时按首映射证据定拒因(bonded 优先);拒因子类
   mapping_fallback 分列键 `cosubstrate_unattributable_mapping_
   fallback_{true,false}`(R32-CS3-1);键合拒 detail 带四轴子标签
   (bonded_kind per_component: single_atom_insertion|group_
   transfer|skeleton_merge、record_balance_status、b_class、
   b_identity_in_products,R32-CS2-3)+ 错杀类目与 EAWAG 不对称
   落字(R32-CS2-2)+ 理由两层分写(R32-CS2-1:物理层执行图不含
   B/规则层 R2-2 无条件禁令,"伪装"仅指未声明形态——r31 R31-1
   护栏原文保持)。
3. **union gate 扩展**:`compile_recorded_reaction` 可选参数
   (§五.3 子选项 i)——执行 ∪ 拷贝 == 记录全量(多重集、
   `strict_identity_of` 键空间两侧统一 `_executed_components_
   strict_unified` + 裸键/严格键一致性披露 `key_space_consistency`,
   R32-CS3-2);拷贝身份 ≠ 记录产物组分 ⇒ `declared_copy_mismatch`
   (NC-4/NC-11——拷贝只认 strict,cn 派生拒);并集不齐 ⇒
   `product_set_mismatch` 沿用;拷贝不可解析 ⇒
   `copy_component_unparseable`;扩展模式在可复现 spec 中优先选无
   add_atom 者(防御性选择);**NC-3 add_atom 机器断言**:
   component 候选产出 spec 的 edits 含任何 add_atom ⇒
   `cosubstrate_executable_add_atom_regression_guard` 结构化拒
   (规则 2/3 已结构性排除,断言防漂移)。
4. **NC-10 事件级不变量**:`_check_cosubstrate_event_invariant`
   (production;R32-CS3-3 必加)——五轴断言(声明共底物 ⊆ 事件
   reactant cosubstate state_refs 的严格身份 ∧ 记录产物多重集 ==
   事件产物参与物多重集 ∧ 参与物状态全可解析 ∧ 拷贝全被产物侧
   引用且 component_source 在位 ∧ NC-9 拷贝不在执行期望);spec 层
   gate 通过不替代事件层核对;B 与拷贝同丢的退化 spec ⇒ 零事件
   零提交(防退化为 A→P 可 exact 的 R2-2 禁形态——add_atom 负控
   对零产物贡献 B 空转,此不变量是唯一事件层闸)。
5. **NC-12 批级熔断**:e2e 合成批断言(tests/test_ppv1_s5b_
   cosub_d2.py::test_d2_e2e_...)——本通道事件 matched_strict 恒
   == 0(边匹配集合 == {matched_participant_coverage_partial},
   不断言"非 strict"以防掉出匹配被误读;PC-1 断言具体桶);真实批
   的通道归因后置聚合登记(§九)。
6. **诊断字段(T-4)**:corpus 诊断新增
   n_cosubstrate_component_candidates/compiled/rejected +
   cosubstrate_reject_split + migration_note + R31-4 标签
   (tier_count_semantics / includes_precompile_permission_rejects
   / count_unit);池诊断新增 n_cosubstrate_declared_specs +
   cosubstrate_pool_labels(count_unit/count_basis/
   expected_match_semantics——hit@1 预期贡献 = 0 落字);
   production 报告携带 cosubstrate_disclosure(declared_copy_
   components + expectation_covered_state_refs + coproduct_
   participants 字段说明 + stoichiometry_status unknown 注记,
   R32-CS1-1/CS1-3/CS5-2)。

## 五、EAWAG/整串字节等价证据(R32-CS3-2 + PC-2)

- 隔离子进程对照(父 worktree 64ef32c8 vs 本轮 HEAD;8 个真实
  298 底物;批准字段 substrate_smiles):`find_recorded_exact`
  (EAWAG)与 `find_corpus_recorded_exact`(corpus whole 面)全部
  候选 compile spec **零字节差**(剥离版本登记键 corpus_retrieval_
  version 与 co_substrate_semantics 语义文本——两者是 D2 显式
  版本登记披露,属登记面非行为面);证据
  `docs/review_evidence/ppv1_s5b_d2_impl_2026-10-10/eawag_equiv/`;
- compile_recorded_reaction 缺省路径直调:spec["compile"] 无
  declared_copies/record_products_full 新键(键空间不变);
  EAWAG 水解 add_atom 能力保持(wv41 既有正控)。

## 六、CS2c 前置探针披露表(r32 前置门;先于实施在父 HEAD 跑)

证据:`docs/review_evidence/ppv1_s5b_d2_impl_2026-10-10/cs2c_probe/`
(cs2c_result.json + 披露表 README;父 HEAD 64ef32c8 隔离
worktree;零模型零金标;只读 298 run_inputs substrate_smiles)。

- **component-with-cosubstrate 面 = 1,323**(题×候选条目,
  raw_top=24 截断后;与 r32 前值精确一致),覆盖 250 题;
- 四分类交叉(分子式/身份配对代理):balanced|no_copy|no_extra
  1,276(键合转移强代理,250 题)/ balanced|copy|no_extra 25 +
  rhs_excess|copy|extra 7(拷贝形态强代理,10 题)/ rhs_excess
  22 条含 A∪B 外元素(不可归属强代理,10 题);
- B 类别:balance_like 202 / organic_like 1,121(候选级;碳数零否
  代理,CO2 含碳归 organic_like、铵无碳归 balance_like 的已知失真
  钉死);题级 organic_like 204(与 v4-WV41 交付书 204 一致)、
  water_declared(记录写了水)118 题/204 候选;
- **EAWAG 隐式书写对照(treatment 翻转披露,R31-3 同句披露)**:
  EAWAG 面 322 候选/99 编译/**68 隐式书写形态**(单组分 donor 且
  产物元素 ⊄ donor——照旧 add_atom 放行、可 strict 可达);多组分
  donor 0(该面 EAWAG donor 均单组分——r31 未确认前提在 298 检索
  面实证);corpus 面同化学(记录写了参与物)守门拒/诚实 partial——
  **treatment 随记录书写风格翻转,两面并列披露不合并叙述**;
- 供给边际(父 HEAD 池):空池 191/298(64.09%;父为 v4b-R1 后
  状态,与 v4-R1 修后 192/298 差 1 题属 v4b 编译面扩大,非本轮
  变量)。

## 七、漏斗前后对照(1,323 面重入多少/键合拒多少/事件供给多少)

探针:`d2_funnel_probe.py`(本轮 HEAD;单变量 = corpus 通道许可;
输入 298 run_inputs substrate_smiles;零模型零金标;证据
`docs/review_evidence/ppv1_s5b_d2_impl_2026-10-10/funnel/`)。

**漏斗账目(题×候选条目,raw_top=24 截断后;1,323 账目精确闭合)**:

| 分支 | 候选数 | 占比 |
|---|---|---|
| 面总数(= r32 前值精确复现) | **1,323** | 100% |
| → 键合融合守门拒(cosubstrate_bonded_contribution_unsupported) | **984** | 74.4% |
| → 可执行子集编译层拒(迁移到既有拒因类目:枚举触顶 219、无结构对应 73、no_alignment 13、transform_no_change 10、stereo 1、charge 1) | **317** | 24.0% |
| → **放行编译成拷贝型池 spec** | **22** | 1.7% |
| 不可归属/不可解析/空可执行子集/add_atom 守卫 | 0(真 298 面实测;类目在机器,真实面未触发) | 0% |

- 拷贝型池供给:22 spec / **15 题**(其中 5 题从空池获得供给;
  10 题已有池增加槽位);事件数在下游,判分后 partial 命中数须
  真实批复测(结构性无 strict 通路,NC-12);
- 池深前后(parent 64ef32c8 → D2):mean 0.477→**0.5537**
  (+0.077);空池 191→**186**(64.09%→62.42%);直方图
  0/1/2/3/4 = 191/82/19/1/5 → 0/1/2/3/4/8 = 186/78/25/3/5/1
  (总槽 143→165,+22 = 放行 spec 数,与池侧同净反应去重后一致);
- **EAWAG 面零回退(数值对照)**:候选 322 / 编译 99,与 CS2c
  探针在父 HEAD 上的计数完全一致(EAWAG 通道不受本轮影响);
- 拒因直方图迁移总表(D2 后 vs v4-R1 修后):
  corpus_cosubstrate_participants_unsupported 1,323 →
  cosubstrate_bonded_contribution_unsupported 984 + 编译层类目
  迁移(mapping_enumeration_truncated 5→224、
  no_structure_correspondence 0→73、no_alignment 22→35、
  transform_no_change 27→37、stereo_edit_unsupported 18→19、
  charge_edit_unsupported 3→4)+ 放行 22(直方图消失 = 放行,
  计数由 n_released_compiled_specs 承接);整串层拒因
  (wildcard 1,869 / provenance 371 / record_missing 143 /
  product_set_mismatch 4 / ambiguous 2)逐类保持;
- **诚实边界**:22/1,323 = 1.7% 的供给解锁率远小于 CS2c 探针
  ②"拷贝形态代理"(32 条)——因为守门按**原子归属**(B-可溯
  any-bond 子结构)而非身份相等判定,且键合拒(984)与编译层
  拒(317,枚举预算为主)占绝对大头;这是通道开放的诚实计量,
  不是错误修复(R31-6 禁句沿用:不得表述为"编译错误下降/
  质量改善");拷贝型事件判 partial,不进 hit(hit@1 预期贡献
  = 0)。

## 八、r32 十六条落字对照表(逐条)

| r32 条款 | 落点 |
|---|---|
| R32-CS1-1 逐组分执行状态进数据 | spec.declared_copy_components(component_source/execution_status/record_key/provenance_sha256)+ production 报告 cosubstrate_disclosure(expectation_covered_state_refs + coproduct_participants_field_note"按 role 聚合,不表示执行覆盖"+ 身份轴/生成轴不得合并句);**判分 payload 的 coproduct_participants 字段说明不进 evaluation.py(判分零触碰红线)**——字段说明随生产报告与交付书落字,真实批复读以参与者 role=cosubstrate 机读事实 + 后置零 LLM 聚合(§九) |
| R32-CS1-2 gate 非配平 | spec["compile"]["declared_copies"]["verified_product_set_scope"]="executed_union_declared_copies(非元素/电荷配平核验;配平轴恒 unknown,判据二)"+ semantics 键 union_gate_semantics 同句 |
| R32-CS1-3 T-2 措辞 | participant_list_status=declared_complete + disclosure.stoichiometry_status="unknown(...只描述清单完整度,不描述计量/配平完整性)" |
| R32-CS2-1 理由两层分写 | 键合拒 detail note(物理层/规则层分写;"伪装"仅指未声明形态) |
| R32-CS2-2 错杀类目点名+不对称披露 | 键合拒 detail note 点名三类损失化学(已声明水水解/水合、已声明 O2 键合氧插入、转移基键合转移酶型;氧化酶/脱氢酶断连型不在损失面)+ CS2c 探针 EAWAG 对照表(R31-3 同句) |
| R32-CS2-3 拒因四轴细分 | bonded_kind_axes.per_component(bonded_kind/record_balance_status/b_class/b_identity_in_products) |
| R32-CS2-4 空可执行子集分支 | cosubstrate_no_executable_product_subset(NC-8;公共枚举下不可达——A 的像必落 A-可溯组分,注入测试钉死拒因名) |
| R32-CS3-1 mapping_fallback 分列 | 拒因 detail.mapping_fallback + 直方图分列键;子选项 i 保守拒(T-3 主会话默认档,mimo 已裁) |
| R32-CS3-2 键空间同源 | `_executed_components_strict_unified`(strict_identity_of)+ key_space_consistency 一致性披露(分歧计数不吞)+ EAWAG 字节等价抽查(§五) |
| R32-CS3-3 事件级不变量 | NC-10(production._check_cosubstrate_event_invariant,提交前;负控 = B/拷贝同丢退化 spec 红) |
| R32-CS3-4 控件矩阵增补 | PC-4/PC-5、NC-8..12 全部进 tests/test_ppv1_s5b_cosub_d2.py;PC-1 断言具体桶 + 氢不配平注记(测试 docstring:乙醇→乙醛释 2H、吡啶→哌啶需 6H,差 4H——元素账 unknown 非已配平) |
| R32-CS4-1 白名单机器挡板 | coproduct_ignore_tier 维持 proposed 未实施(本轮零实施);机器锚 = COMPLETION_LICENSED_IDENTITIES 无碳守卫测试(§八.1) |
| R32-CS4-2 D-T1′-3 歧义 | T-1 不立项(§12 默认档)⇒ 歧义随 T-1 落定,**登记待裁**(本交付书落字,不预选实现) |
| R32-CS4-3 补全许可不延伸 | 机器锚测试:COMPLETION_LICENSED_IDENTITIES 只允许 H2/[H](含碳入列即红);对称句落字:反应物侧已声明共底物 coverage 恒 unknown_coefficients,不因"记录声明了它"给 known |
| R32-CS4-4 四条防线 | ①通道归因:事件参与者 role=cosubstrate 机读事实 + e2e 断言(真实批复读后置聚合登记 §九);②NC-12 熔断;③D-M-1 同表:池诊断 expected_match_semantics 含"hit@1 expected contribution = 0"+ 交付书 §九;④拒因迁移对照:corpus 诊断 migration_note + 漏斗探针直方图总表 |
| R32-CS6-1..5(预注册路径) | 零实施维持(tier/四元组/exempt_identity_hash 均不存在于 src);CS6-1 追溯开关、CS6-2 H2O carve-out、CS6-4 辅因子不进清单 + 退出条件、CS6-5 长线前置依赖——全部为 T-1 立项后的预注册内容,本交付书仅登记不推进(§九) |

T1′ 三条落字(D-T1′-1/2/3):设计书 §六原文已含;本轮机器面 =
补全许可无碳守卫测试 + 对称句;D-T1′-3 与 T1′① 的读法分叉登记
待 T-1(§12 默认档:T-1 不立项)。激励倒挂(声明共底物诚实事件判
partial、EAWAG 简写 strict 可达)如实落字不修不掩盖(§九;CS2c
探针两面并列披露为机器证据)。

r33 措辞项涉及本通道的:S1-a/S1-c/S2-c/S3/S6——本轮无 stereo/
消解通道改动(编译判据零触碰),无 EAWAG 水解行为改动;措辞面
由版本登记与交付书落字承载,无源码措辞项遗漏自评。

## 九、诚实预期与待复审残留(不预支批准)

1. **本通道对 hit@1 的预期贡献 = 0**(T-1 不立项 ⇒ 事件判
   partial;NC-12 熔断钉死);D2 价值 = 事件供给解锁 + 化学诚实
   (记录保真:已声明共底物不再被丢弃/add_atom 折原子)+ T-1
   立项后 strict 转换的机读基础(拷贝组分/来源字段/执行状态全
   机读)。partial 新增计数不与 hit 混列;真实批复测的
   n_cosubstrate_partial_matches 以事件参与者 role=cosubstrate
   机读事实后置零 LLM 聚合(scorer 零触碰);
2. **D3 评审轮(Codex+mimo 场景 1)**:公开链探针面(原生事件
   参与物/拷贝披露/负控族/池深)随复审送审;发车义务沿 v4 复审
   §7 六条(新登记/新身份/双门/冒烟/金额/终局归因)——**本轮
   不启动真实批**;chain11/chain12 封存批零回写;
3. **漏斗数字与池深对照**见 §七(探针完成后回填);204 =
   碳数零否代理统计不证明 partial 命中(供给面计数单位:题×候选
   条目,不外推);
4. **T-1..T-5 维持主会话默认档**("主会话默认、待用户/teacher
   随时改判"):T-1 不立项(判分面豁免零实施,预注册草案维持
   设计件)、T-2 declared_complete、T-3 保守拒子选项 i(mimo r32
   CS3 已裁)、T-4 已机读、T-5 挂起登记;R32-CS4-2/CS6-1/CS6-2/
   CS6-4/CS6-5 属 T-1 立项后的预注册义务,登记不推进;
5. **激励倒挂显性化**(r31 H1b/r32 CS2 不对称披露):不修(判据
   冻结);根治路径 = 参考侧 omitted_coproduct_scope(T-5 挂起,
   须用户单独授权);
6. v4b 诊断细分族(R1-2/R3-1/R3-2/R3-3)维持 v4b 登记不动;R3-2
   配平门与本门正交叠合(D2 先行自包含:不可归属保守拒兜底)。

## 十、四组回归证据

| 组 | 命令/证据 | 结果 |
|---|---|---|
| 定向(新+既有族) | `pytest tests/test_ppv1_s5b_cosub_d2.py + test_ppv1_s5b_hit50_v4_wv41.py -q` | **39 passed**(新 19 + wv41 20;含真 corpus 实盘用例) |
| 全量 | `pytest tests/ -q -m "not slow"` | **2019 passed / 0 failed / 16 deselected**(基线 2000 + 19 新,精确;323.3s) |
| G01 隔离 | `/private/tmp/safe_g01_s5b_cosub_d2.py --repo … --out /private/tmp/g01_s5b_cosub_d2` | **2008 passed / 10 skipped / 17 deselected, exit 0**(= v4b-R1 1989 + 19 新,精确兑现;339.7s;输入 SHA 前后复验零失配;改动集脚本强制核对 = 7 换字节 + 1 新 + 0 缺失逐项一致;实际 HEAD 64ef32c8+dirty 记录;7 个游离 .pyc 如实记录[仅隔离树]) |
| 父基线红绿 | 父 worktree 64ef32c8 + 新/改测试字节(复制入 worktree tests/,import 前显式 sys.path 指向 worktree src) | **25 failed / 36 passed**(cosub_d2 18/19 红——唯一绿为 COMPLETION_LICENSED_IDENTITIES 无碳守卫[既存不变量,非 D2 行为,如实分类];wv41 6 红:PC-1 形态真行为红[父拒/新编译]+ 版本/拒因标签红;w23456 1 红:版本字面量;证据 parent_red_green/) |

(全量/G01 stdout 与 junit 已存证据目录;G01 输出目录引用随
preparation/execution_result 记录。)

## 十一、金标边界自查

- 预测侧零金标:改动只在 corpus 适配许可/守门/事件装配/池版本;
  CS2c 与漏斗探针只消费 run_inputs substrate_smiles(批准字段,
  如实登记访问范围);金标/products/旧答卷/封存逐题 run 零读取;
  判分零 LLM;合成夹具与真实 298 金标零重叠(W2 夹具纪律:
  CCO/吡啶/哌啶级小分子);
- 探针在隔离 tmp/父 worktree 执行(-B、零模型零网络调用、证据
  目录只收脚本副本与输出文本);封存资料零触碰;
- 冻结判据/scorer/评测尺子/AtomTool/编译判据零触碰(§一/§五);
  三冻结 SHA 不动;EAWAG 面字节级等价(§五抽查 + 既有测试族);
- 对外数字带题域标签(298 题域检索/池面聚合计数,不外推 dev,
  不冒充命中数)。

## 十二、本轮改动清单(提交内容)

- `src/pathway_v43/pollutant/recorded_source.py`(+~600 行):
  W-D2 纪律段;corpus-retrieval-3/recorded-source-3 版本与语义键;
  `_classify_cosubstrate_candidate`(三分类守门)+ `_flatten_
  product_entries` + `_executed_components_strict_unified` +
  `_attach_cosubstrate_spec_fields`/`_build_state_or_fail`/
  `_ChemStateBuildFailure`;find_corpus component 三分支;compile_
  recorded_reaction 可选参数 + union gate + add_atom 防御性选择;
  诊断 T-4 字段与 R31-4 标签;EAWAG 路径与缺省编译路径字节零改动;
- `src/pathway_v43/pollutant/production.py`(+~230 行):B/拷贝
  状态装配 + 状态引用一致性守卫 + NC-10 事件级不变量
  `_check_cosubstrate_event_invariant` + cosubstrate_disclosure
  机读返回 + 生产报告披露接线(无共底物 spec 零字段零变化);
- `src/pathway_v43/pollutant/s5b_builder.py`(+~30 行):
  pool-policy-5 + 通道 1b 文档 + n_cosubstrate_declared_specs/
  标签;
- `src/pathway_v43/pollutant/s5b_compiler.py`(+6 行):
  net_reaction_signature 拷贝扩展(无拷贝 spec 逐字节不变;编译
  判据零触碰);
- `tests/test_ppv1_s5b_cosub_d2.py`(新,~760 行):NC-1..12/
  PC-1..5 控件矩阵 + 版本登记 + 补全许可无碳守卫;
- `tests/test_ppv1_s5b_hit50_v4_wv41.py`(拒因迁移 + 版本字面量):
  91003 家族形态正控化、水/RL/池/实盘用例拒因迁移、版本断言;
- `tests/test_ppv1_s5b_hit50_w23456.py`、`tests/test_ppv1_s5b_
  hit50_v4b.py`(版本字面量);
- 本交付书;
- 证据目录 `docs/review_evidence/ppv1_s5b_d2_impl_2026-10-10/`
  (未跟踪:CS2c 探针、EAWAG 等价抽查、父红绿、漏斗探针、G01
  引用、回归日志)。
