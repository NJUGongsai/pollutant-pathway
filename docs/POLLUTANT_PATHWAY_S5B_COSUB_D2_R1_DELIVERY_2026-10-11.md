# PPV1 S5b 共底物参与物语义 D2-R1 回修轮交付书
# (S5b-corpus-retrieval-4 / s5b-recorded-source-3 / s5b-pool-policy-5)

状态:`implementation_ready_for_review`。

任务依据:Codex D2 正链复审
`docs/POLLUTANT_PATHWAY_S5B_COSUB_D2_CODEX_REVIEW_2026-10-11.md`
§4 唯一 P1 **S5B-D2-01**(NC-10 触发条件可被装配层删字段关闭)
+ §8 下一轮有限回修提示词全文(权威收口范围);§6 P2 五项搭车。
基线 2e679b31(D2 收口提交;开工记录实际 HEAD
`2e679b31ded26e8b977896800bda3c8f17e9bf14`)。本轮零模型、零金标
读取、零真实批、零 push。

- 实施期工作树改动:6 个已跟踪文件换字节(3 源码 + 3 测试),
  0 新增源码/测试文件;金标/题面/封存逐题 run 零读取;
- 判据零触碰:三冻结 SHA 前后一致(criteria-v1
  `7fd35aab…` / FREEZE_RECORD `6e046e29…` / path_context
  `971ad00f…`,工作树逐一复验)、scorer(`s5b_scoring.py`)、
  匹配排序(`evaluation.py`)、判分口径、AtomTool、
  `compile_donor_template` 编译判据、金额链全部零改动;
  EAWAG/整串通道编译输出字节等价(§六,剥离版本登记键后
  NONE——byte-equivalent)。

## 一、修法一句话

**NC-10 事件不变量的触发条件从"装配数组任一非空"改挂"记录侧
单一声明来源"**:新函数 `production._cosubstrate_record_declaration`
(单一判定函数)以 `cosubstrate_event_contract` 为 dict 或 corpus
块声明 B/copy(co_substrates 非空或 record_products 非空)判共底物
语义适用——同一记录把 B 参与物与拷贝状态**两侧同时**删/置空/置
null/省略(strip_both_empty/missing/null、all_arrays_missing_
participants_default 四形态)后,守卫不再被静默关闭;装配数组缺失/
null/非 list 先结构化拒(kind=`cosubstrate_assembly_missing`,不
静默 or-[] 归一)、participants 省略拒(`cosubstrate_participants_
required`,缺省装配不覆盖共底物语义)、NC-10 断言无条件执行
(轴 1 声明共底物集 = contract ∪ corpus 合并——contract 单侧清空
不失效);首消费结构化拒、零新增坏 event/相关事件提交。

## 二、入口消费矩阵(AGENTS.md 返工教训 1:开工先列)

记录侧单一声明来源 = `production._cosubstrate_record_declaration`
(唯一判定函数,contract ∪ corpus 合并去重保序;装配数组非空与否
不参与判定)。适用入口全部经 **prepare_hypothesis 单一构建源**
共用同一核验(不在各入口复制不同规则):

| 入口 | 消费 | 本轮变化 |
|---|---|---|
| `production.prepare_hypothesis` | 池条目 spec → 假设/状态/工具输入(**唯一构建源**) | **触发条件改挂记录侧声明**(declaration-based);装配数组形状契约(缺失/null/非 list ⇒ `cosubstrate_assembly_missing`);participants 显式契约扩展到声明在位的一切形态;NC-10 无条件调用;轴 1 合并声明集;披露新增 `declaration_sources`/`trigger_semantics` 机读键 |
| `runflow._run_decide`(池条目;首提) | prepare_hypothesis(spec) | 经单一构建源自动收口:prepare 拒 ⇒ `ProductionContractError` ⊂ `SearchContractError` ⇒ drive 层 run_error 结构化停止、零事件(公开 start 链路,探针+回归双证) |
| `runflow._run_decide`(novel 提案) | prepare_hypothesis(reaction_spec) | 同上共用;W5 逐条容错把契约拒留 novel_rejections(不洗成方法失败) |
| `runflow._run_expand`(expand 重放;resume 恢复路径) | prepare_hypothesis(payload spec) | 同上共用;公开 resume 重驱动再拒(同 kind,零新增行——探针+回归双证) |
| `_check_cosubstrate_event_invariant` | NC-10 五轴 | 轴 1 声明集改用 declaration 合并集;其余四轴口径不变 |
| `recorded_source` 检索/装配/编译 | find_corpus/compile/`_attach_cosubstrate_spec_fields` | **行为零变化**;版本键 corpus-retrieval-3→4 + 语义文本 + 契约 invariant_note(登记面) |
| `s5b_builder.default_pool_provider` | 池供给 + 诊断 | 池成员/策略零变化;`n_cosubstrate_declared_specs` 改**去重后池槽**计数(P2-3)+ NC-12 参考范围标签 |
| 公开 start/resume/导出/判分 | plan.pools specs / events | 判分尺子零改动(NC-12 只加范围限定文字,不改 evaluation) |

## 三、版本升级登记(既有身份规则)

| 版本 | 旧 → 新 | 理由 |
|---|---|---|
| corpus 检索语义 | `s5b-corpus-retrieval-3` → **`s5b-corpus-retrieval-4`** | **共底物事件契约消费语义变更**(NC-10 触发条件 + NC-12 参考范围限定;spec 装配/检索/编译行为零变化——W-D2-R1 沿 W-V4.1-R1→W-D2 版本链登记);`cosubstrate_event_semantics`/`cosubstrate_permission` 语义文本与 `frozen_by` 补 W-D2-R1 条目;契约 invariant_note 更新;recorded_source.py 版本注释登记 |
| recorded 公共源 | `s5b-recorded-source-3` **不变** | compile_recorded_reaction/EAWAG/整串路径零触碰(eawag_equiv 复验) |
| 池策略 | `s5b-pool-policy-5` **不变** | 池成员/配置零变化(仅诊断计数口径 P2-3 修正,登记于标签文本) |
| search-production | `ppv1-search-production-2` **不变** | NC-10 自 D2 起即由 corpus-retrieval 语义块承载登记;不硬升无关契约(复审 §7) |
| 编译器 | `s5b-compiler-3` **不变** | 编译判据零触碰 |

## 四、四反例修前红/修后绿(Codex §4.2 复审四形态)

证据:`docs/review_evidence/ppv1_s5b_d2_r1_impl_2026-10-11/
semantics_repro/`(Codex public_probe 的 fresh tmp 复制改造:路径
重排 + 同一 scripted 模型身份的 resume + 逐表先行合法账披露;
before = 父 2e679b31 隔离树,after = 本轮修复源码隔离树;socket
封禁尝试 0)。同一合成记录 `CCO + c1ccncc1 → CC=O + C1CCNCC1`
(守卫夹具,氢不配平,计量 unknown;不是真实酶学反应):

| 形态 | 修前(父) | 修后(本轮) |
|---|---|---|
| strip_both_empty(两装配数组=[]、B/copy 参与物删、contract/corpus 保留) | 无拒,1 坏 event(仅 CCO→CC=O),root-only 参考 **matched_strict** | prepare 拒 `cosubstrate_event_invariant_violation`(axis=declared_cosubstrates_subset);start run_error 同 kind;**events=0**;resume 同 kind 再拒、逐表 delta 全零 |
| strip_both_missing(两装配键删除) | 同上 1 坏 event + matched_strict | prepare 拒 `cosubstrate_assembly_missing`(field=co_substrate_states);start/resume 同拒;events=0 |
| strip_both_null(两装配键=null) | 同上 | prepare 拒 `cosubstrate_assembly_missing`;start/resume 同拒;events=0 |
| all_arrays_missing_participants_default(装配数组+participants 均省略) | 默认 A→P 装配,1 坏 event + matched_strict | prepare 拒 `cosubstrate_participants_required`(缺省装配不覆盖共底物语义);start/resume 同拒;events=0 |
| (追加守卫)corpus_only_declaration(contract 删除、corpus 声明保留、两侧同删) | 无拒,1 坏 event + matched_strict | prepare 拒 `cosubstrate_contract_missing`(declaration_sources=[corpus]);start/resume 同拒;events=0 |

- **保全输入与拒因**:每案 JSON 含原行/变更后公开 plan(记录侧
  contract/corpus 原文保留)、prepare 异常全文(kind/message/detail)、
  start/resume stop 报告 run_error 原文;
- **逐表先行合法账**(不伪称全表零写):修后四案表行如实保留
  root 检索/认领/预算/底物状态(如 strip_both_empty 修后
  search_actions=2、states=1、budget_reservations=4、
  search_commit_records=1[run 注册]、events/event_appearance_
  links/hypotheses=0);resume 逐表 delta 全零;
- 合法事件对照(legal_cofactor/bystander/multiple)修前修后均
  1 event、partial;whole 两案均 strict——**修复零回退**。

## 五、首提与恢复入口回归 + 正负控族

- **首提**:四反例经 plan 池 spec 进 start_ppv1_run ⇒ run_error
  结构化拒、零事件(探针 + `test_d2_nc10_r1_public_start_resume_
  reject`×3 + `test_d2_nc10_r1_public_start_participants_default_
  rejected`);
- **恢复**:同一 scripted 模型身份的公开 resume_ppv1_run 重驱动
  ⇒ 同 kind 再拒、零新增行(探针 resume_run_error + 测试断言);
- **正控族保持**(探针 + 既有测试族,不以全面拒绝换通过):合法
  copy(legal_cofactor)、旁观 B 零 copy(legal_bystander/PC-4,
  `copy=[]` 数组在位不拒——新增正控测试钉死)、多 B/多 copy
  (legal_multiple/PC-5)、whole(whole_oxidation)、多组分 whole
  (whole_multicomponent)、EAWAG 水解与默认编译(wv41 既有族 +
  eawag_equiv 字节等价复验 + PC-2 缺省键空间);
- **负控族保持**:单删 B/单删 copy(strip_B/copy_participant)、
  坏状态引用(bad_B/copy_reference)、坏 component_source、坏
  参与物引用、缺/重复记录产物、拷贝入期望(NC-9)、坏声明 B、
  键合融合(NC-1/2)、不可归属(NC-5)、B 不可解析(NC-6)、
  add_atom 伪装(NC-3)——探针修后全部同 kind 拒,零行为迁移;
- **新增守卫负控**:corpus-only 声明(contract 删除 corpus 保留
  ⇒ `cosubstrate_contract_missing`)、contract 单侧清空 B +
  两侧同删(合并声明集 ⇒ 轴 1 拒)。

## 六、EAWAG/整串字节等价复验(PC-2)

D2 轮同方法同 8 底物(批准资产,零金标):父 2e679b31 vs 本轮,
`find_recorded_exact`(EAWAG)与 `find_corpus_recorded_exact`
(whole 面)全候选 compile spec,剥离版本登记键
(corpus_retrieval_version / co_substrate_semantics)后逐字节比对
**NONE — byte-equivalent**(证据 eawag_equiv/;d2r1_equiv_parent.
json vs d2r1_equiv_current.json)。本轮 corpus-retrieval-4 的版本
键与语义文本变化属登记面非行为面;recorded-source-3 缺省编译路径
零触碰。

## 七、NC-12 范围限定(r32 CS5 口径;复审 §5)

- **落字位置**:corpus 语义块 `cosubstrate_permission`
  ("structurally no strict path under the CURRENT ROOT-ONLY
  (B/copy-stripped) reference construction scope — NC-12 batch
  fuse asserts matched_strict == 0 for that scope only; a legal
  complete B/copy reference may legitimately match the same
  declared event strict, which is NOT drift and must NOT be
  masked by editing the evaluator")、池标签
  `cosubstrate_pool_labels.expected_match_semantics` 同句、
  e2e 测试 docstring/断言注释、pool-policy 版本注释;
- **机器正控**(新测试 `test_d2_nc12_r1_complete_reference_
  strict_allowed`,复现 Codex reference_control 口径):同一声明
  事件在当前 root-only 参考(剥除 B/copy)下 matched_participant_
  coverage_partial、在合法完整 B/copy 参考(经
  validate_reference_graph 冻结 schema 校验;B 节点 role=unknown
  ——参考图 role 枚举无 cosubstrate,Codex 同口径)下
  **matched_strict 合法**——熔断只针对"当前 root-only 参考构建
  口径"恒 0;判分尺子(evaluation.py/scorer)零改动,不为守 0
  改评价;
- **熔断本体**:e2e 批断言维持(root-only 参考下
  statuses == {matched_participant_coverage_partial}、
  matched_strict 不在集合)。

## 八、§6 P2 搭车(文稿/计数标签精度及父红绿分类)

1. **池深均值算术订正**(登记于漏斗证据 README + 本交付书;
   D2 交付书 §七原文为舍入口径,历史件不回写):旧
   143/298=0.479866、新 165/298=0.553691、增量 22/298=0.073826
   (非「0.477→0.5537(+0.077)」);空池 191/298=64.094% →
   186/298=62.416%;直方图 191/82/19/1/5 → 186/78/25/3/5/1
   (0/1/2/3/4/8 槽,总槽 143→165);
2. **CS2c 重叠格口径澄清**(cs2c_probe/README):四互斥格
   1276/25/7/15=1,323;②copy=32(25+7)与③不可归属=22(7+15)
   为跨格聚合、交集 7(rhs_excess×copy×extra 格),当互斥格相加
   会误成 1,330——不报数据错误、不悄悄改观测;「放行集大于②
   代理」限定到 distinct 题级(15>10;候选级 22 并不大于 32);
3. **池计数标签精度(P2-3,源码修复)**:
   `s5b_builder.py` 的 `n_cosubstrate_declared_specs` 从去重前
   递增改为**同净反应签名去重后、截断前**计数(标签口径
   "pool_specs(去重后、截断前)"与数值一致;去重前编译候选数由
   corpus_diagnostics.n_cosubstrate_component_compiled 承接;
   count_precision_note 机读注记;不凭该字段计算命中或池净槽);
   机器锚 = PC-3 测试扩展断言(3 来源 spec → 2 池槽 ⇒ 计 2,
   父上红);
4. **「零字段」限定**(P2-4):本轮起交付书与披露明确
   cosubstrate_disclosure 键在无共底物 spec 的 prepare 返回为
   None(键本身在位、值为 None——D2 已有的行为,如实登记;生产
   报告/事件零字段不变);
5. **父红绿分类**(P2-2,按实际类别分组、测试数不当漏洞数):
   父 2e679b31 + 本轮新/改测试字节 ⇒ 15 failed / 58 passed /
   0 collection error,分类 = 真行为红 10(NC-10 守卫不拒
   DID-NOT-RAISE 6 + 公开 start/resume 无结构化拒 4——父上四反例
   的坏 event 提交由 before 探针另行证明,不拿测试红冒充事件级
   反例)、新披露键缺失 1(旁观 B 正控行为面父保持接受,仅
   declaration_sources 新键 KeyError)、池计数去重前口径红 1
   (P2-3)、版本/语义字面量红 3(cosub_d2/wv41/v4b 版本断言);
   同时订正 D2 交付书 §十口径(原「cosub_d2 18/19 红、wv41 六红」
   为按文件的粗分,本轮按逐 nodeid 实际类别登记——历史件不回写,
   以 classification.json 为准);
6. **来源声明与独立执行分清**:本交付书四组回归全部为本会话
   独立执行数字(§十);CS2c/漏斗/池深 298 面聚合计数仍为 D2 轮
   来源声明(未重跑真实面,数字未变、口径订正在案)。

## 九、四组回归证据

| 组 | 命令/证据 | 结果 |
|---|---|---|
| 定向(cosub_d2 + wv41 + v4b + w23456) | `pytest tests/test_ppv1_s5b_cosub_d2.py tests/test_ppv1_s5b_hit50_v4_wv41.py tests/test_ppv1_s5b_hit50_v4b.py tests/test_ppv1_s5b_hit50_w23456.py -q` | **95 passed**(cosub_d2 31 = D2 19 + 本轮 12 新;含四反例/守卫/公开 start+resume/NC-12 完整参考正控/去重计数锚) |
| 全量 | `pytest tests/ -q -m "not slow"` | **2031 passed / 0 failed / 16 deselected**(基线 2019 + 12 新,精确;最终测试字节重跑) |
| G01 隔离 | `/private/tmp/safe_g01_s5b_cosub_d2_r1.py --repo … --out /private/tmp/g01_s5b_cosub_d2_r1` | **2020 passed / 10 skipped / 17 deselected, exit 0**(= D2 2008 + 12,精确兑现;334.2s;改动输入集脚本强制核对 = 6 换 + 0 新 + 0 缺逐项一致;330 输入前后 SHA 零失配;7 游离 pyc 如实记录[仅隔离树];实际 HEAD 2e679b31+dirty 94 行记录) |
| 父基线红绿 | 父 git archive 树 + 新/改测试字节(测试文件自插父 src) | **15 failed / 58 passed**(分类见 §八.5;证据 parent_red_green/classification.json) |

(全量 stdout 留 /private/tmp/d2r1_full_final.log;G01 完整
stdout/stderr/JUnit/缺席逐 nodeid 在证据 g01/ 目录。)

## 十、诚实边界与待复审残留

1. **适用入口边界**:本轮核验的适用入口 = prepare_hypothesis
   单一构建源的全部消费面(池条目/novel/expand/公开 start+resume)
   与直接公开调用;NC-10 轴 2(记录产物多重集)的权威输入仍为
   contract.record_products——contract 与 corpus 的 record_products
   分歧(如篡改 contract 收缩产物集而 corpus 保留全量、participants
   同步收缩的复合形态)不在四反例内,本轮未加 contract-vs-corpus
   产物一致性核验(超出复审 §4.3 最低收口;如实登记为已知边界,
   声明来源两处任一在位即触发+轴 1 合并集已闭合 B 侧);
2. **mimo r34**:交付时 `docs/mimo_ppv1_chem_review_response_r34.md`
   尚未落盘——**pending 如实登记**;r32 的 NC-10 义务(R32-CS3-3)
   经本轮落地并与复审程序证据互证,r34 到达后按互证原则另行核对,
   不预填其意见、不宣布三方 D3 收口;
3. **设计线状态**:本轮只修 S5B-D2-01 + §6 P2 搭车;T-1..T-5
   维持主会话默认档;chain12 仍缓发;D3 收口与组合批发车条件沿
   复审 §7(修复并正链通过 + r34 采纳核对后才可工程收口);
   显式氢墙不是本轮授权内容;
4. 池深/漏斗/CS2c 298 面数字维持 D2 来源声明(§八.6);真实批
   未启动;本通道 hit@1 预期贡献 = 0 的登记口径不变(受 NC-12
   范围限定约束:root-only 参考口径)。

## 十一、金标边界自查

- 预测侧零金标:改动只在 NC-10 触发/装配形状契约/披露键/池诊断
  计数;探针全部合成夹具(CCO/吡啶/哌啶级,与真实 298 金标零
  重叠,W2 纪律);金标/products/旧答卷/封存逐题 run 零读取;
- eawag_equiv 只读授权语料资产(8 个硬编码底物,同 D2 轮方法);
  判分零 LLM;socket 封禁在语义探针(尝试 0);
- 冻结判据/scorer/评测尺子/AtomTool/编译判据/金额链零触碰
  (§首;三冻结 SHA 工作树逐一复验一致);EAWAG/整串面字节级
  等价(§六);
- 对外数字带题域标签(298 题域聚合计数为来源声明,不外推 dev,
  不冒充命中数)。

## 十二、本轮改动清单(提交内容)

- `src/pathway_v43/pollutant/production.py`(+~180 行净):
  `_cosubstrate_record_declaration`(记录侧单一声明来源,NC-10
  触发条件唯一判定函数)+ prepare_hypothesis 触发改挂声明 +
  装配数组形状契约(`cosubstrate_assembly_missing`)+
  participants 显式契约扩展 + NC-10 无条件调用 + 轴 1 合并声明集
  + 披露 declaration_sources/trigger_semantics + 版本注释登记
  W-D2-R1(携带 corpus-retrieval-4);
- `src/pathway_v43/pollutant/recorded_source.py`(登记面):
  corpus-retrieval-3→4 版本与 W-D2-R1 注释 + `cosubstrate_
  permission`(NC-12 参考范围限定)/`cosubstrate_event_semantics`
  (触发语义)/`frozen_by` 语义文本 + 契约 invariant_note;
- `src/pathway_v43/pollutant/s5b_builder.py`(P2-3):
  `n_cosubstrate_declared_specs` 去重后计数 + count_precision_
  note + NC-12 范围标签 + pool-policy 注释范围限定;
- `tests/test_ppv1_s5b_cosub_d2.py`(+~470 行):四反例
  parametrized 拒因 + all_arrays_default + corpus-only + 合并声明
  + 旁观 B 零 copy 正控 + 公开 start/resume 双入口(4 形态)+
  NC-12 完整参考 strict 正控 + PC-3 去重计数锚 + 版本 -4;
- `tests/test_ppv1_s5b_hit50_v4_wv41.py`(语义文本断言 + 版本
  字面量 -4)、`tests/test_ppv1_s5b_hit50_v4b.py`(版本字面量 -4);
- 本交付书;
- 证据目录 `docs/review_evidence/ppv1_s5b_d2_r1_impl_2026-10-11/`
  (未跟踪:语义复现 before/after、父红绿分类、G01、EAWAG 等价);
- D2 轮实施证据 README 订正(cs2c_probe/funnel,未跟踪证据内
  P2 口径澄清)。
