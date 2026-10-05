# pollutant_pathway_v1 S0–S2 阶段交付包

- 日期:2026-10-05
- 实施依据:`docs/POLLUTANT_PATHWAY_ARCHITECTURE_UPGRADE_SPEC_2026-10-05.md`
  (v1.2,§17 裁定为执行依据)
- 实施范围:**仅 S0–S2**(profile 定位、领域契约与存储、上下文与固定
  诊断);S3–S5(有界搜索、任务身份/恢复、终点、原生导出/评测)
  **未实施**——执行流入口对新模式显式 fail-closed(见 §9 偏离说明 2)
- 交付状态:工程实现完成、全部规则级测试通过;科学验收未开始
  (S5 范畴,状态 pending);新增化学判据**未冻结**,已产出 mimo 评审
  请求 `docs/mimo_ppv1_chem_review_request.md`
- 本文档自包含 review 所需的:P0-1/P0-2/P0-4 回答、P0-3 设计草案、
  完成项对照、偏离说明、测试证据

---

## 1. 一句话结论

S0–S2 按 §17 裁定完成:新旧 profile 在 run identity/代码身份层分开
(legacy 冻结口径零改动),新模式的领域契约(ChemicalState/
ReactionHypothesis/事件-报告-展开三集合)与固定诊断(条件/依赖/
ChemicalAudit/admission 策略/候选池审计)已实现并有规则级测试;
第一阶段 P0 问题已回答(见 §3–§6)。

## 2. 完成项对照(实施书章节 → 交付物)

| 实施书要求 | 状态 | 交付物(代码/测试) |
|---|---|---|
| §3.1 新旧模式分开:profile 进 run identity | 完成 | `pollutant/profile.py`;`storage/run_identity.py`(v43-identity-2,profile 块 + code_identity 分集);`workflow/runner.py`(profile 参数);CLI `--profile` |
| §3.1 旧 run 不原地迁移/换 profile resume | 完成 | resume 从保存身份读 profile,不允许切换;旧身份缺 profile 字段按 legacy_v43 兼容读取 |
| §3.1 新增 schema 未知时明确失败 | 完成 | `Ppv1StoreSchemaError`/`RetrievalSchemaError` 模式延续;profile/开关取值域 fail-closed |
| §3.1 输出写新根目录 | 完成 | 新 store 独立文件 `pollutant_pathway.sqlite`(run 目录内),不写 legacy 账本 |
| §3.2 不修改旧门禁真假 | 完成 | legacy 门禁(v43 gates/G2)零改动;audit 只**引用** `frozen_hit60_gate` 结果,不回写 |
| §5.1 ChemicalState | 完成 | `pollutant/chemstate.py`(B01/B02 测试) |
| §5.2 ReactionHypothesis + 参与物契约 | 完成 | `pollutant/hypothesis.py`(A01/H02/H03 测试) |
| §5.3 事件/报告/展开三集合 | 完成 | `pollutant/events.py` + `pollutant/store.py`(A02/A03 测试) |
| §5.3 非法共同产物不静默丢 | 完成 | `ParticipantStateError`(整体失败,不部分提交) |
| §5.3 酶/催化剂另存 | 完成 | `CatalyticSupport`(不进净反应计量) |
| §5.4 Provenance source_origin 细分 | 完成 | `pollutant/provenance.py`(P0-1 映射,§3) |
| §5.4 支持组/独立支持数诚实 | 完成 | `build_support_groups`(原研究身份未知 → None) |
| §6 PathContext/条件/依赖 | 完成 | `pollutant/path_context.py`(C01–C05、H04 依赖诊断测试) |
| §7.1 build_chemical_state / build_substrate_profile / assess_conditions / audit_hypothesis / check_edit_against_donor | 完成 | 五个固定函数全部落位(§7.1 其余三个接口属 S3 搜索范畴) |
| §7.3 候选池阶段审计 | 完成 | `pollutant/pool_audit.py`(8 阶段记录 + input preview off/diagnostic + 排序 + 截断披露) |
| §8 ChemicalAudit + admission(P0-4) | 完成 | `pollutant/audit.py`(H01/C06/D03 测试;决策表 §6) |
| §8 供体诊断分轴 | 完成 | `check_edit_against_donor`(D01/D02 测试) |
| §11 S0 基线夹具 | 完成 | legacy 基线 = 既有全量通用测试(G01);新模式夹具 = 本交付新增 88 个 ppv1 测试 |
| §3.2 mimo 化学评审请求 | 完成 | `docs/mimo_ppv1_chem_review_request.md`(规则级,无金标) |

**未完成项(按计划不属于本阶段)**:§9 有界搜索/SearchAction/预算/
恢复(S3);§10 终点与原生导出(S4);§13 评测器与数据规范(S5);
G2 输入侧 preview 的**消费**类策略(§17.2 明确禁止在首版 preview
中消费筛选/排序结果——本交付只提供 diagnostic 通道)。

## 3. P0-1 回答:现有检索系统的证据类型现状与映射

**现状:已有标注的取值与产出位置(全部为代码事实,无金标材料)。**

1. `kind` 四值,单一事实源 `src/pathway_v43/domain/models.py:35-38`:
   `recorded_reaction`、`rule_application`、`analog_reaction`、
   `novel_proposal`。
2. 产出方与实际样例(规则级夹具样例,`tests/test_ppv1_domain.py` /
   `tests/wf_helpers.py`):
   - recorded 卡:`services/reaction_finder.py:216-268` —— kind=
     `recorded_reaction`、match_type=`exact_donor_cn_match`、
     source_id=引擎反应 ID(形如 `bt0254#r0601`)、asset_sources=
     `[{"role": "recorded", asset_file/sha256=library_full.jsonl}]`;
   - 规则/类比卡:`services/reaction_finder.py:271-340`(kind 由
     `_kind_for_source`:102-108 从来源字符串判定;预测块来源字面含
     eawag_lookup 也降格为 rule:273-275;组合来源如 envipath+retrieval
     的每成分在 asset_sources:299-302);
   - 模型提案卡:`services/prediction.py:854-931`(kind=analog(类比)/
     novel(新提案)、match_type=`model_analogy_transfer`/
     `model_constrained_proposal`、source_record.predicted_by_model=True
     :918、asset_sources=[])。
3. v2 检索卡附加标注:`donor_refs`/`mapping_status`(resolved/
   ambiguous/unavailable)/`mapping_reason`,产出
   `reaction_finder.py:366-384` 与 `services/analog_source.py:448-485`。

**映射表(kind/match_type → 新 source_origin/evidence_basis)——
实现于 `pollutant/provenance.py:map_legacy_card`,测试
`test_ppv1_s2.py`/`test_ppv1_domain.py`:**

| legacy 判别 | source_origin | evidence_basis |
|---|---|---|
| kind=recorded_reaction(match_type=exact_donor_cn_match) | curated_reaction | curated_record_only |
| kind=rule_application,来源含 uspto | patent_template | rule_derived |
| kind=rule_application,其余(envipath/eawag 规则/无标识) | biotransformation_rule | rule_derived |
| kind=analog_reaction 且 match_type=model_analogy_transfer 或 predicted_by_model | model_proposal | model_proposed |
| kind=analog_reaction(检索邻居) | analog_transfer | analog_transferred |
| kind=novel_proposal | model_proposal | model_proposed |
| 组合来源 | 主成分 + components[] 每成分各自细分 | 同左 |

**补标注逻辑(现状不足部分)**:
- `evidence_basis` 是**新增轴**(§17.3.1):映射函数永不产出
  `experimentally_observed_exact` —— 该值要求可追溯观察记录、明确匹配
  范围与结构信息,只能经显式构造路径授予;本资产集的 recorded 卡
  只有库记录链(btid#reac_id + library_full.jsonl 哈希),故映射为
  `curated_record_only`(库中记录 ≠ 本场景直接实测);
- 既有 kind/source_id/match_type/asset_sources/score_semantics 原样
  透传保留(`ProvenanceInfo.legacy_*` 字段),不重做成另一套分类。

## 4. P0-2 回答:G2 输入侧与输出侧执行顺序

**结论(代码证据):当前仓库没有输入侧 G2 调用;输出侧 G2 在
`call_model` 内 finalize 阶段、`validate_products` 之前执行;输入侧
preview 是本交付新增的 diagnostic 通道,默认 off。**

调用链(行号为本交付后 HEAD 的实际行号):

- **实现**:`validation/conservation.py:1080`
  `conservation_filter_and_rank(substrate_smiles, candidates,
  surface_text)` → FilterResult(versions v43-cons-2 族,conservation.py:
  73-79)。
- **输出侧调用(既有,未改动)**:
  `workflow/nodes.py:914-941 _apply_conservation`(唯一调用点包装)→
  由 `_apply_analogy`(:808-821,类比提案)与 `_apply_novel`
  (:868-880,新提案)触发,两者都在 `_finalize_parsed`
  (:677-720)内,即 `call_model` 节点写 `prediction.json` 之前;
  `validate_products`(:1014-1104)只消费已经过(或未过)G2 的产物。
- **输入侧**:`grep -rn conservation_filter_and_rank src/` 命中仅
  conservation.py(定义)、nodes.py(输出侧)、
  `pollutant/pool_audit.py`(本交付新增 preview,**见下**)。
  legacy 图的 retrieve/classify/prepare 路径零调用。
- **开关与参数对比**:

| 维度 | 输出侧(legacy) | 输入侧(新 preview) |
|---|---|---|
| 函数 | 同一 `conservation_filter_and_rank` | 同一函数 |
| 参数 | substrate_smiles=当前底物 CN、candidates=提案产物、surface_text=题面条件 | 形状一致(substrate_smiles/candidates/surface_text) |
| 开关 | `novel_conservation_filter`(off/on,默认 off,`domain/policy.py:83,95`;进 run identity policy 块) | `input_preview_policy`(off/diagnostic,默认 off;进 profile 身份块,`pollutant/profile.py`) |
| 返回值消费 | **消费**:剔除项不入卡、降位垫底、剔空→held(nodes.py:813-819/875-879) | **不消费**:`run_input_preview` 返回 pool_unchanged=True,诊断逐项附注,池成员/档位/原顺序不变(`pool_audit.py`;§17.2) |

- **legacy 顺序未被偷改的程序证据**:
  `nodes.py` 本阶段零改动(git diff 无该文件);G01 回归 = 全量既有
  通用测试通过(§8);`test_s1_arm_switches.py` 等既有字节级一致性
  测试全部在回归集内。

## 5. P0-3 配置与计数设计草案(**proposed,非冻结**)

**完整草案见 `pollutant/profile.py` 常量区(SEARCH_LIMITS_*);此处
为摘要。S3 才实施实际计数/恢复代码与 E04 验收;S2 只冻结键名、
默认值、允许范围、计数单位与优先级。**

| 配置键 | 默认 | 允许范围 | 计数单位 |
|---|---|---|---|
| max_hypotheses_per_parent_alternative | 2 | 1–8 | 同一父路径上每个备选反应假设的语义尝试次数 |
| max_product_expansion_width | 2 | 1–8 | 单事件产物继续展开宽度 |
| max_search_depth | 3 | 1–10 | 路径边数(与 legacy max_depth 语义分开) |
| max_total_search_actions | 10 | 1–1000 | run 级 SearchAction 总数(含 scenario_transition) |
| max_scenario_transitions | 2 | 0–4 | 阶段转换次数(不是反应边,单独计数) |
| max_reopens_per_hypothesis | 1 | 0–3 | 同一假设无新信息时的重开上限 |
| max_real_model_requests | 0 | 0–10000 | 真实模型请求**登记**数(0=默认不发出付费请求;悬空请求也计额度) |
| max_retrievals_per_parent | 1 | 1–4 | 每父路径实际检索次数(复用产物不重复计数) |
| max_retrievals_total | 64 | 1–4096 | run 级实际检索总数 |

- 工程验收小值(§17.1 建议):每父备选 2、产物宽度 2、深度 3、
  总 action 10 —— 已在允许范围内,S3 用作 E04 夹具;
- 停止原因优先级(多因并存时的主因次序,S3 冻结;user_stop 恒最
  优先):user_stop > budget_limit > depth_limit > no_local_candidate
  > awaiting_prediction > exhausted_search;
- 计数全部取持久记录(SearchAction 表/请求登记/检索 artifact 数),
  不取内存状态;重放可复算(§9.3 语义,S3 落地);
- 取值校验 fail-closed:未知键/类型/越界在装配期拒绝
  (`_validate_search_limits`,测试 `test_ppv1_profile.py`);
- 版本串 `ppv1-search-limits-1-proposed` 显式标注草案状态。

## 6. P0-4 回答:admission_policy 完整规则

**schema:`pollutant/audit.py:AdmissionPolicy`(dataclass + JSON 往返,
版本 `ppv1-admission-1`;测试 `test_admission_policy_decision_table_explicit`)。**

字段:`policy_version`、`reject_gates`(默认名单:gate_direction_source/
gate_recorded_eligibility/gate_smiles——全部为 frozen_hit60_gate 既有
门,**新增门禁进名单必须独立列项评审**,测试保证未知门禁 fail-closed)、
`chemical_reproposal`(默认 off)、`rules`(有序决策表)。

**完整决策表(有序,首中即决):**

| 规则 | 条件 | 处置 | 理由码/语义 |
|---|---|---|---|
| R1 | 结构无法解析(audit parse_check=violated) | **reject** | structure_unparseable;受影响后续项 status=unknown、reason_code=prerequisite_failed_not_run(H01) |
| R2 | 活动门禁显式拒绝(仅 reject_gates 名单内) | **reject** | active_gate_rejected;名单外门禁违规不触发(不暗改冻结判据) |
| R3 | 当前场景有来源的必要条件冲突 | **defer**(action=blocked) | current_scenario_conflict;假设保留不在此场景展开,可展示为需不同条件的备选(C02) |
| R4 | 预算/等待状态 | **defer** | budget_or_wait(独立原因,不混入 R3) |
| R5 | 存在 unknown 检查(条件/完整账/映射/step_scope 未知) | **retain_conditional** | unknown_checks_present;可有界探索可能路径,继承未解决依赖;未知步长不进确认单步指标 |
| R6 | 全部适用检查 verified 且无冲突 | **expand** | all_verified_no_conflict |
| — | 空审计(无适用检查) | retain_conditional | 无证据不冒充核实(保守) |

**unknown 不自动 reject 的保证**:决策表无任何 "unknown→reject" 行;
新增"诊断转拒绝"必须扩表并升版本(`policy_version` 读取端 fail-closed)。

**C06 策略级测试**(`test_c06_structure_valid_gate_ok_unknowns_retain_conditional`):
结构有效(parse verified)、活动 gate 接受、账目/依赖未知 →
disposition=retain_conditional,reasons 明示 unknown 项与"不自动拒绝",
未解决依赖引用在 audit 的 provenance_dependency 检查中保留
(§17.1:S2 不要求实现完整有界搜索,S3 集成验收)。

## 7. 代码结构与版本清单

新增包 `src/pathway_v43/pollutant/`(legacy 路径不 import 该包;
legacy code_identity 排除该目录):

| 模块 | 职责 | 版本常量 |
|---|---|---|
| profile.py | profile 注册/版本清单/开关/P0-3 草案 | ppv1-profile-1 |
| chemstate.py | ChemicalState(§5.1) | ppv1-chemstate-1 |
| hypothesis.py | ReactionHypothesis/参与物(§5.2) | ppv1-hypothesis-1 |
| events.py | 事件/报告投影/展开计划(§5.3) | ppv1-event-1 |
| store.py | 新模式 SQLite 账本 | ppv1-store-1 |
| legacy_reader.py | 旧账本只读适配(§3.1) | (读取 v43-store-1/2) |
| provenance.py | source_origin/evidence_basis/支持组(§5.4) | ppv1-provenance-1 |
| path_context.py | PathContext/条件/依赖(§6) | ppv1-context-1 / ppv1-dependency-1 / ppv1-condition-assessment-1 |
| substrate_profile.py | 底物档案(§7.1) | ppv1-substrate-profile-1 |
| audit.py | ChemicalAudit/admission/供体诊断(§8) | ppv1-audit-1 / ppv1-admission-1 / ppv1-donor-diagnostic-1 |
| pool_audit.py | 候选池阶段审计/输入 preview(§7.3/§17.2) | ppv1-pool-audit-1 / ppv1-pool-order-1 / ppv1-input-preview-1 |

改动的 legacy 文件(共 3 个,行为冻结部分零改动):
- `storage/run_identity.py`:IDENTITY_SCHEMA v1→v2(+profile 块;
  code_identity 按 profile 分集);
- `workflow/runner.py`:start/resume 增加 profile 参数(pollutant 显式
  拒绝);legacy 默认路径逻辑不变;
- `__main__.py`:parser 抽取 build_parser()(纯结构重构)+ run/resume
  `--profile` 参数。

复用(只读引用,未修改)的冻结资产/判据:frozen_hit60_gate
(validation/gates)、G2 v43-cons-2 族(validation/conservation)、
CN 口径 cn-v1(domain/identity)、MoleCode vendor(services/atom_tool)。

## 8. 测试证据

命令(可复现,本仓根目录):

~~~bash
~/miniconda3/envs/depending43/bin/python -m pytest tests/test_ppv1_profile.py tests/test_ppv1_domain.py tests/test_ppv1_s2.py -q
# 88 passed

~/miniconda3/envs/depending43/bin/python -m pytest tests/ -q -m "not slow"
# G01 legacy 回归:全量既有通用测试(结果见 §8.1)
~~~

新增测试(3 个文件,88 个用例,全部规则级夹具、模型 off、无金标、
无封存逐题材料):

- `tests/test_ppv1_profile.py`(23):profile 注册/身份块 fail-closed/
  code_identity 分集(加 pollutant 文件不改变 legacy 身份的程序证据)/
  v1 旧身份兼容读取/pollutant 执行流显式拒绝且不建目录/CLI 参数;
- `tests/test_ppv1_domain.py`(30):A01–A04、B01–B02、H02、H03、
  事件幂等/冲突/事务原子性、催化支持不入计量、legacy 只读导入
  (零写回的字节级断言 + 幂等重放 + 存档形保真标注);
- `tests/test_ppv1_s2.py`(35):C01–C06、D01–D03、H01、H04(依赖
  诊断部分)、admission 决策表显式性、池审计(off/diagnostic/排序/
  截断披露/CN 去重拒绝)、底物档案(CN-only 诚实)。

关键验收点的用例映射:A01 `test_a01_*`;A02
`test_a02_cleavage_event_keeps_both_products_even_k1`;A03
`test_a03_not_tracked_product_kept_with_reason`;A04
`test_a04_legacy_novel_flat_list_import_labeled`;B01/B02 `test_b0*`;
C01–C05 `test_c0*`;C06 `test_c06_*`;D01–D03 `test_d0*`/`test_d03_*`;
H01 `test_h01_*`;H02/H03 `test_h0*`;G01 见 §8.1。

### 8.1 G01 legacy 回归结果

本仓 HEAD(实施基线 536c977 + 本阶段 diff)运行全量通用单测
(`-m "not slow"`;真实资产慢测与真实模型请求不在默认触发范围,
按实施书 §12 另列执行范围):

~~~
$ ~/miniconda3/envs/depending43/bin/python -m pytest tests/ -q -m "not slow"
699 passed, 16 deselected in 191.57s (0:03:11)
~~~

699 = 既有测试 611(全部通过,含字节级一致性守卫
test_s1_arm_switches / test_export_v3 / test_prediction_task 等)
+ 本阶段新增 88。16 个 deselected 为 `slow` 标记的真实引擎/资产
慢测,未运行。**legacy 行为与评测口径零回归。**

## 9. 偏离说明(需 review 特别注意)

1. **run identity schema 升级(v43-identity-1 → v43-identity-2)是
   一次性变更**:实现 profile 分集必须改 `run_identity.py` 本身,因此
   本次升级后,**升级前创建的旧 run 的一次 resume 会被身份门槛拒绝**
   (code_identity 变化)——这与"任何代码变更拒绝跨版本 resume"的
   既有 fail-closed 语义一致,不是行为回归。此后:pure `pollutant/`
   内的变更不再影响 legacy code identity(有测试
   `test_code_identity_legacy_stable_under_pollutant_changes` 的程序
   证明);legacy 行为/评测口径零改动(G01)。
2. **pollutant 执行流入口显式拒绝**:`start_run/resume` 对
   profile=pollutant_pathway_v1 抛结构化 RunError("执行流未交付,
   属 S3"),不建 run 目录、不写 identity。这是 §11 阶段边界的
   fail-closed 实现,不是功能缺陷;S3 交付后解除。
3. **C06 按策略级验收**(§17.1 裁定):S2 交付 admission 策略的
   retain_conditional 语义与测试;有界搜索的实际展开/依赖继承/预算
   在 S3 集成验收。
4. **`assess_conditions` 的评估范围**:实现为"上下文累积必要要求 +
   该假设自带 requirements"合并(同键以假设侧为准;同固定场景的
   同键冲突在 derive_child_context 显式记入 assumptions)。规格 §6
   未逐字规定合并次序;此为最小惊讶实现,请 review 确认。
5. **legacy 导入的缺省投影/展开计划只是占位**:`legacy_reader` 导入
   事件时给全部产物位次=旧位次、展开状态=not_tracked
   (reason=legacy_import_no_expansion_info)。真实报告/展开决策不
   在导入侧猜——占位参数显式标注,请 review 确认可接受。
6. **未做的兼容动作(故意)**:没有为旧 retrieval artifact 自动补
   source_origin 标注(读取端按需映射);没有把 legacy run 批量迁入
   新 store(导入接口按 run/事件显式调用)。

## 10. 遗留科学未知与需要化学复核的事项

1. **新增化学判据未冻结**——需按 `docs/mimo_ppv1_chem_review_request.md`
   走 mimo 评审 + 本会话化学 review,重点:
   - 元素/电荷核算的"不补水/氧/辅酶、先中和后验禁令"边界;
   - admission 决策表中"元素账 violated 不进 reject(保守
     retain_conditional)"的立场;
   - pH/温度区间语义;供体诊断三轴;对称等价类处理。
2. 互变异构体/芳香表示的 canonical 等价性未做专门处理
   (ChemicalState 直接使用 RDKit canonical;B01/B02 只覆盖对映体/
   电荷/映射号三轴)。风险:同一互变体可能得到不同 state_id——
   对"可能路径"语义无碍(不合并不误导),但影响去重;留待 review
   裁定是否需要在 S3+ 加显式互变等价轴。
3. 观察条件(§17.3.2)只保存不门禁;essential 的判定完全依赖来源
   声明质量,首版没有独立的 essential 性核实通道(如实标注)。
4. 科学验收整体 pending(§13):题源、评测器、预注册全部属 S5;
   本交付的 88 个测试是工程契约测试,**不是路径科学性能证据**,
   不构成任何命中率/费用声明。

## 11. S3–S5 前置状态(供第二阶段交接)

- profile 身份块已含 `delivered_stages: "S0-S2"`;S3 交付时须更新
  为 "S0-S3"(版本常量随模块追加);
- P0-3 草案键名/默认值/范围已冻结进 profile 身份,S3 实施计数时
  直接消费(如需改默认值 = 身份变更,须升版本);
- 新 store 的事务/幂等/冲突语义(ppv1-store-1)是 S3 搜索队列的
  落账底座;SearchAction 表/预算预约/恢复测试(§9.3 四个崩溃边界)
  属 S3;
- 供体诊断/池审计/底物档案的接口形状(§7.1)已冻结,S3 的模型任务
  组装按此消费。
