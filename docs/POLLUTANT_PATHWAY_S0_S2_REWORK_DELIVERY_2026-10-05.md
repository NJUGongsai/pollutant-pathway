# pollutant_pathway_v1 S0–S2 回修交付书

- 日期:2026-10-05
- 回修依据:`docs/POLLUTANT_PATHWAY_S0_S2_CODEX_REVIEW_2026-10-05.md`
  (F01–F11 + §3 P2 + §4 mimo 裁定;§7 回修提示词)
- 回修基线:7fb198f(S0–S2 首轮);实施书
  `docs/POLLUTANT_PATHWAY_ARCHITECTURE_UPGRADE_SPEC_2026-10-05.md` §17
- 回修范围:**仅 S0–S2 底座回修**;S3 边界不解除(执行流入口对
  pollutant profile 仍显式 fail-closed),契约与化学判据**不宣称
  冻结**(待本会话 review + mimo 第二轮)
- 状态:工程回修完成,全部规则级测试通过(含复核反例的仓库化
  回归);legacy 默认行为零改动

---

## 1. 一句话结论

F01–F11 全部修复、§3 五项 P2 全部落实(实现或列明设计);v1 的
错误氢计数正例已修正为真正的配平正例;Codex 复核的全部已复现
反例已转成仓库回归测试并通过;mimo 第一轮意见按 §4 裁定逐条
处置;影响语义的契约全部升版并声明兼容行为。

## 2. 逐项处置表(F01–F11)

| 项 | 缺陷摘要 | 修复(代码/测试) | 验证(规则级正反例) |
|---|---|---|---|
| F01 | 元素账漏算氢;2C2H6O+O2→2C2H4O2 被当配平正例;歧义参与物可 full | `audit.py:element_counts_full`(重原子 GetTotalNumHs+独立氢顶点);`substrate_profile` 同一基准;`ambiguous_participants` 阻止 full;结构化 Δ 向量+模式标注;错误正例废除 | 正例 CCO+O2→CC(=O)O+**H2O**(v2 测试);反例:缺 H2 violated(ΔH=+2+2H 模式)、v1 错例(ΔH=4)钉住、显式 H2 产物平衡、惯例水解(H2O:product_side 模式)、歧义不 full;`test_f01_*` 5 例 |
| F02 | 同键要求被覆盖丢失,冲突不沿路径保持 | `path_context v2`:要求全量累积不去重(仅语义相同去重);聚合按合取(任一 conflict→conflict);`derive_child` 同键双方保留+显式注记 | 两个复核复现反例均钉住:父 20–30/当前 45 ⇒ 子加 40–50 后仍 conflicted;当前 25 子 40–50 ⇒ 仍 conflicted;`test_f02_*` 3 例 |
| F03 | 事实忽略 absent/场景/阶段/必要性来源;标签假冲突 | `path_context v2`:`known_absent⇒conflict`;`scenario_ref`+`_applicable_facts`(curated 须场景匹配、phase 限定);无源 essential=未核实假设(不进门禁不证相容);`value_basis` 分 range/point/optimum/label/未声明;标签注册表(首版空⇒unknown);数值有限性校验;UNASSESSED_DIMENSIONS 显式随附 | absent 冲突、unsourced、历史场景(不采用不作数/采用后作数)、阶段限定、mesophilic unknown、optimum 偏离不冲突、单数值未声明 unknown、未评估维度披露;`test_c0*`/`test_f03_*` 9 例 |
| F04 | put_state 按全 payload 比较,同结构不同来源假冲突;连续导入失败 | `store v2`:states(结构语义,幂等校验)+state_appearances(出现记录追加);语义冲突仍拒;两步路径连续导入修复 | 同结构双来源不冲突+双出现保留、真语义冲突仍拒、两步旧路径导入 2 事件+中间物双出现;`test_f04_*` 3 例 |
| F05 | 增强立体三输入身份碰撞;CN-only 走通用工厂冒充可知;audit 把 CN-only 判 R1 | `chemstate v2`:`_identity_key`(canonical 重排+StereoGroups 序列化);通用工厂拒 legacy_cn_only;分轴 fidelity;audit:CN-only⇒parse unknown(reason=structure_unavailable),仅语法非法是 violated;strict 轴用同源 `strict_identity_of` | 三增强立体输入三身份、幂等;CN-only 工厂拒绝;CN-only 参与物 parse=unknown 非 R1(不 reject);电荷账 original_charge_unavailable;`test_b02_*`/`test_f05_*` |
| F06 | context_id 漏语义字段;供给环只识二元 | `path_context v2`:context_id 冻结全部语义字段(含 scope/assumptions/dependency_refs/scenario_ref/transition);供给多边图+DFS 任意长环;依赖引用存在但状态未提供⇒unknown | scope=[]/["oxygen_regime"] 不同身份;depX/depY 不同身份;A→B→C→A 检出;未提供解析状态不视为已解决;`test_f06_*` 3 例 |
| F07 | 事件事务缺参照完整性(悬空引用/欺骗 state_ref/重放缺附随不报/双状态) | `store v2 submit_event`:事务内验证全部参与物状态引用(缺⇒回滚)、state 语义一致(INSERT OR IGNORE 废除)、假设关联(缺⇒回滚);重放附随记录缺失⇒Ppv1LedgerCorrupt;`events v2`:state_ref 欺骗检查、展开互斥;`hypothesis v2`:底物锚点校验;audit 的 raw_structures 欺骗检查 | 缺产物 state 回滚零事件、state_ref 张冠李戴拒绝、锚点违约构造期拒绝、删投影重放报损坏、expanded+deferred 互斥、缺假设回滚;`test_f07_*` 6 例 |
| F08 | schema 先写后验;未知身份版本通过 resume 比较 | `store v2`:已有文件先读 meta 验证(DDL 前,字节不变),新文件才初始化;`run_identity`:SUPPORTED 版本门(future-identity-999 拒;v1 兼容不扩展);from_dict 版本门(chemstate/context/hypothesis) | future-store-999 字节不变拒绝、future-identity-999 拒绝、chemstate/context from_dict 未知版本拒绝;`test_f08_*` 2 例+域内 2 例 |
| F09 | 子路径缺存档时根污染物冒充子底物 | `legacy_reader v2`:is_root=路径关系确认(event_id 与 position 均空);子路径缺档⇒CN-only+未知注记,绝不借根结构 | 两步路径删中间物存档:步骤 2 底物 CN-only(电荷轴 unknown)、根底物仍 raw_input、旧库字节不变;`test_f09_*` |
| F10 | 无标识 rule 升格 biotransformation_rule;组合来源 retrieval 成分错标;布尔开关冒充研究身份;导入丢 model_ref/provenance | `provenance v2`:显式标识才映射(无标识⇒unknown);retrieval/corpus 成分⇒analog_transfer;study_map(库记录→原研究)替代布尔,无 map⇒None;`legacy_reader v2`:model_ref⇒model_proposal 且 hypothesis.model_decision_ref 保留;provenance_records 持久化 | 无标识 rule unknown、组合成分分标、同论文双库 ID(study_map=1 独立支持;无 map=None)、model_ref 导入保留+provenance 可查;`test_f10_*` 4 例 |
| F11 | 供体诊断不消费真实编辑协议(atom_id 虚构键);部分映射/伪造等价类仍 True | `audit v2 check_edit_against_donor`:输入=真实 v43-editproto-2 编辑+execute_edits 输出;实际键变化 diff(成/断/键级)为判定基础;全部中心原子须有映射(部分缺⇒unknown);等价类经分子图自同构验证(非等价类整体拒用);center_match_basis ∈ {direct, symmetric_equivalent};执行失败⇒全轴 unknown;extra_changes 逐原子 Δ 摘要 | 乙醇 C–O 编辑(复核复现场景)v1 None→v2 True(direct);部分中心缺映射 unknown;伪造等价类(C/O)拒;苯对称等价 symmetric_equivalent;断键案例 extra_changes 元素摘要;`test_f11_*`/`test_d0*` |

## 3. P2 事项处置(设计/接口,§3)

| 项 | 处置 |
|---|---|
| P2-1 理由码不实 | violated⇒R5d `declared_account_violated`(独立于 R5 的 unknown_checks_present);空审计⇒R7 `no_applicable_checks_conservative_retain`(不再冒 empty_audit);表示契约失败⇒R2b `contract_violated_representation`(参数 contract_violation)。测试 3 例 |
| P2-2 旧门禁适配 | `legacy_validation_to_gate_decisions`(ppv1-gate-mapper-1):direction_source/recorded_eligibility 映射入名单形状,atom_mapping 附带,**逐产物 verdicts 全量保留**(元素门禁在逐产物层),gate_ref 带原产物引用;mapper 输出可直接喂 decide_admission。测试含资格失败→reject |
| P2-3 上限单位混淆 | 键拆分:`max_alternative_hypotheses_per_parent`(父路径备选**假设**数)与 `max_attempts_per_hypothesis`(单假设语义**尝试**数)独立计数;`max_reopens_per_hypothesis` 保留(无新信息重开)。v1 混合键废除 |
| P2-4 配置往返与零 | `_validate_search_limits`:version 字符串键仅校验版本值(v1 KeyError 修复);输出恒为完整配置可原样回灌(round-trip 测试);全部键下限放宽到 0(独立零深度/零预算夹具合法:`max_search_depth=0`/`max_total_search_actions=0` 测试通过) |
| P2-5 哈希链/limit | `build_pool_audit` 校验相邻已执行阶段 output_hash==input_hash(断裂拒绝);跳过/注入须 from_previous=False+transition_reason(缺失拒绝);`order_pool` limit 值域(None 或 ≥0;负数拒绝,v1 静默切片废除)。测试 3 例 |

## 4. mimo 意见处置表(按复核 §4 裁定,不整段照搬)

| mimo 建议 | 裁定 | 落实 |
|---|---|---|
| 严格身份不用 CN;增强立体不能丢;来源保真分轴 | 接受(碰撞须代码级解决) | StereoGroups 序列化入身份键;分轴 fidelity(F05) |
| 原始电荷未知时账 unknown;不自动补物 | 接受(依据=来源转换历史) | fidelity.formal_charge 轴门控电荷账;CN-only/中和轴 unknown |
| 元素/电荷差值与 violated/unknown 分码 | 接受 | Δ 向量+模式数值相符(仅数值相符语义);R5d 独立码 |
| 未声明完整性子型默认 complete_stoichiometric | **不采纳**(Codex) | 未说明⇒完整性/核算适用性 unknown,不升级为完整净反应 |
| 缺 2H 标 +2e;"高度疑似惯例" | 收紧(Codex) | 模式匹配只标数值相符+方向;语义声明不含电子/质子计量、不证缺项原因 |
| [nH]/N 一般可由芳香感知统一 | 不泛化(Codex) | 只归一确属同一分子图的表示差异(canonical 感知后输出) |
| 存档串无电荷标记即认定电荷丢失 | 不采纳(Codex) | 电荷轴 as_written;中性是合法结构事实;丢失与否按转换历史 |
| optimum 不产生硬冲突 | 接受+纠偏 | optimum 偏离只 preference;**单点 basis 不明不自动推 optimum**⇒unknown |
| 注册表标签可直接参与硬判 | 修改(Codex) | 标签注册表首版为空⇒一律 unknown;通用类别范围不替代来源支持范围 |
| 首版必须加光照/盐度/Eh 等全部条件键 | 不一刀切(Codex) | UNASSESSED_DIMENSIONS 登记并随相容结论显式输出;"已评估维度内相容" |
| 中心匹配带 basis;不充分/多解不一致 unknown | 接受(先对接真实编辑) | F11 重写后落地 direct/symmetric_equivalent |
| 仅产物自同构即证迁移中心等价 | 修改(Codex) | 等价类经分子图自同构验证;图等价≠酶识别等价(不升格机制) |
| 七项均"只改文字不动语义" | 不采纳(Codex) | 严格身份/条件适用性/中心判定均改了代码+测试+版本 |

未触发冲突:以上处置与实施书 §5–§8 的冻结口径无实质冲突
(实施书只冻结 legacy 判据;新 profile 判据本就待冻结);若 review
认为某条与实施书正文冲突,请在回执中指出,我们单列冲突报告。

## 5. 版本清单与兼容行为

| 契约 | v1 | v2 | 兼容声明 |
|---|---|---|---|
| profile | ppv1-profile-1 | ppv1-profile-2 | 本 profile 从未放行执行流(入口 fail-closed),无任何已发布 run/产物;升版即生效,无数据迁移 |
| chemstate | ppv1-chemstate-1 | ppv1-chemstate-2 | 同上;fidelity 单旗标→分轴、身份键含增强立体 |
| hypothesis | ppv1-hypothesis-1 | ppv1-hypothesis-2 | +底物锚点/from_dict 版本门 |
| event | ppv1-event-1 | ppv1-event-2 | +互斥/欺骗检查 |
| store | ppv1-store-1 | ppv1-store-2 | 表结构变化(states 拆分+appearances+provenance);schema 写前门;v1 新模式库不存在(未放行),无需迁移 |
| context/dependency/condition | -1 | -2 | 合取聚合/适用性/身份全字段;同上无历史数据 |
| provenance | ppv1-provenance-1 | ppv1-provenance-2 | 映射修正+study_map |
| substrate_profile | -1 | -2 | 全氢基准 |
| audit | ppv1-audit-1 | ppv1-audit-2 | 全氢/差值/CN-only 语义/理由码 |
| admission | ppv1-admission-1 | ppv1-admission-2 | +R2b/R5d/R7;policy JSON 往返 |
| donor_diagnostic | -1 | -2 | 真实协议/basis/等价类验证 |
| pool_audit/pool_order | -1 | -2 | 哈希链/limit 值域 |
| input_preview | -1 | -2 | 不变语义,随族升版 |
| gate_mapper | — | ppv1-gate-mapper-1 | 新增(P2-2) |
| search_limits | …-1-proposed | …-2-proposed | 键拆分/零值/往返;仍为 proposed(S3 落地) |
| run identity | v43-identity-2 | 同号(内容增强) | +SUPPORTED 版本门;v1 旧身份仍兼容读取;legacy resume 语义不变 |

**legacy_v43**:零改动承诺继续成立 —— 本轮回修只动了
`storage/run_identity.py`(版本门,legacy 语义不变)、`pollutant/`
包与 `tests/`;`nodes.py` 等冻结路径零触碰。全量通用单测见 §7。

## 6. 规则级正反例摘要(全部在仓库测试中)

正例:CCO+O2→CC(=O)O+H2O(全氢配平,verified+expand);
CCO→CC=O+H2(显式氢产物平衡);乙醇 C–O 真实编辑 center=direct;
苯对称等价 symmetric_equivalent;两步旧路径连续导入;study_map
归并独立支持=1;optimum 命中/偏离 preference。

反例(v1 缺陷全部钉住):CCO→CC=O violated(ΔH=+2,2H 模式);
2C2H6O+O2→2C2H4O2 violated(ΔH=4);惯例水解(H2O:product_side);
父冲突被子要求覆盖(v2 保持 conflicted);NADH known_absent ⇒
conflict;无源 essential 不证相容;mesophilic unknown;单数值未
声明 basis unknown;增强立体三输入三身份;CN-only 工厂拒绝+
parse 非 R1;unknown store schema 字节不变拒绝;future-identity-999
拒绝;子路径缺档 CN-only(不借根);state_ref 张冠李戴拒绝;缺产物
state 回滚;删投影重放报损坏;expanded+deferred 互斥;部分中心缺
映射 unknown;伪造等价类拒;同结构双来源不冲突(真语义冲突仍拒)。

## 7. 测试证据

~~~bash
~/miniconda3/envs/depending43/bin/python -m pytest \
  tests/test_ppv1_profile.py tests/test_ppv1_domain.py \
  tests/test_ppv1_s2.py tests/test_ppv1_rework.py -q
# 129 passed, 1 skipped(skip=显式环境守卫,非缺陷)

~/miniconda3/envs/depending43/bin/python -m pytest tests/ -q -m "not slow"
# G01 legacy 回归:<见 §7.1 回填>
~~~

新增 `tests/test_ppv1_rework.py`(16 例:F04/F07/F08/F09/F10 的
存储与导入反例仓库化);domain/s2/profile 测试同步升 v2 语义。
**不以测试数量作为通过依据**:每个 F 项的验证锚定复核报告的具体
复现场景(§2 表末列)。

### 7.1 G01 legacy 回归结果

~~~
$ ~/miniconda3/envs/depending43/bin/python -m pytest tests/ -q -m "not slow"
740 passed, 1 skipped, 16 deselected in 226.94s (0:03:46)
~~~

740 = 既有 legacy 通用单测 611(全部通过,零行为回归)+ 本轮 ppv1
测试 129。1 skipped 为显式环境守卫;16 deselected 为 `slow` 标记的
真实资产慢测(未运行)。回修过程中出现过一次 legacy 测试失败
(test_analog_v2_corpus:手工 identity 夹具无 schema_version 字段被
版本门误拒),已修正为只拒**显式未知版本**(缺失按字段差异正常
核对),复跑全量通过——该修正本身有测试钉住
(test_ppv1_rework.py 的 future-identity-999 拒绝 + 上述 legacy 用例)。

## 8. 剩余未知与边界(不宣称冻结)

1. 化学判据 v2 **未冻结**:mimo 第二轮评审请求已更新
   (`docs/mimo_ppv1_chem_review_request.md` v2 文本),待用户转交;
   冻结以本轮 review + mimo 回应与本仓程序证据互证为准。
2. 契约 v2 未冻结:待本会话 review;`delivered_stages` 仍为 S0-S2,
   S3 入口 fail-closed 未解除。
3. 供体诊断的"供体侧预期键变化"对比(当前比对中心区域;供体
   反应自身的变化模板)留 S3 与映射管道一并落;当前语义(区域命中
   +basis)已在 docstring 声明边界。
4. 条件标签注册表为空(设计如此:无来源支持范围一律 unknown);
   注册表的初始条目与审定流程待化学复核后定。
5. 互变/质子化等价类(tautomer_group_id 等)与 edge_kind 标注:
   S3 搜索展开去重时落地(当前已有"禁 CN 去重"的门禁)。
6. 科学验收整体 pending(S5);本轮回修的测试仍是工程契约证据,
   不构成任何路径科学性能声明。

## 9. 与原规格的冲突清单

无新增实质冲突。两处"规格未逐字规定、回修采用更强语义"的说明:
- §6"同键要求合并次序未规定"→ 回修采用合取不覆盖(复核 §6 裁定
  "不接受 v1 交付书 §9.4",据审核执行;与规格"条件要求必须按步骤
  和阶段累积,不许覆盖"一致)。
- §5.2 参与物契约 → 回修增加底物锚点校验(规格未明文,属fail-closed
  收紧,不改任何既有冻结判据)。
