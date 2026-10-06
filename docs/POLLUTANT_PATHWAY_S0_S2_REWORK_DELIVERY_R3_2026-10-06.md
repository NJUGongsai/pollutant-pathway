# pollutant_pathway_v1 S0–S2 第三轮回修交付书(R3)

- 日期:2026-10-06
- 回修依据:`docs/POLLUTANT_PATHWAY_S0_S2_CODEX_REVIEW_R2_2026-10-06.md`
  (R2-01～R2-12 + §4 P2 + §5 mimo 采纳边界;§8 回修提示词)
- 回修基线:0002f71(=审核 HEAD;R2 复审的全部反例在本轮开始时经
  4 个附件探针复跑确认与审核版本行为一致,输出 diff 仅时间戳/路径差)
- 回修范围:**仅 S0–S2 底座回修**;S3 入口继续 fail-closed(未解除);
  契约与化学判据**不宣称冻结**(待本会话 review + mimo 第三轮)
- 状态:三线(化学/审计、条件/身份、存储/适配)全部落地并合并,
  在公开 API 边界联合验证;legacy 默认行为零改动(G01 全量回归)

## 0. 一句话结论

R2-01～R2-12 十二项 P1 与 §4 P2 全部处置(实现+回归);复审探针的
全部已复现反例已翻转并钉住;每条线先红后绿(化学线 8/8 行为级红
验证于基线 0002f71);契约全族升 v3(profile 未放行执行流,无历史
产物需迁移);mimo 第二轮意见按 R2 复审 §5 采纳边界逐条处置,并
准备 v3 评审请求(§8)待用户转交。

## 1. 提交与 diff

| commit | 内容 |
|---|---|
| 1b74a17 | R3 底座:契约版本常量 -2 → -3(唯一触碰 profile.py 的提交;三线从其分叉) |
| 8edf3a0 | R3 条件线:R2-04/05/06/07 + scope/coverage/basis/label P2 |
| af5b4e0 | R3 存储线:R2-08/09/10/11 + 池哈希链/study_map/provenance 引用/断键夹具 |
| 0d2aa43 | 合并 r3-store |
| 9a90ef0 | 合并收尾:2 处旧 -2 字面量 pin → -3(admission/pool order) |
| c36d36a | R3 化学线:R2-01/02/03/12 + audit input_hash + mimo 采纳 |

总 diff(0002f71..c36d36a):32 文件,+7801/−636;
`git diff 0002f71..HEAD` 可复算。触碰面仅
`src/pathway_v43/pollutant/`(11 模块)+ `tests/` 7 个 ppv1 文件
(4 新增:`test_ppv1_r2_{conditions,storage,chem}.py`) +
`tests/test_ppv1_profile.py`(版本 pin)。**legacy 路径零触碰**
(`workflow/ services/ storage/ output/ domain/` 除 `storage/
run_identity.py` 未动——本轮连 run_identity 也未改)。

## 2. R2 逐项处置表(P1 全部)

### 化学与审计线(本会话主窗口实施;R2 复审 §6 线 1)

| 项 | 修复(代码位置) | 测试 | 结果 | 未完成边界 |
|---|---|---|---|---|
| **R2-01** admission 覆盖/崩溃/自报签名 | ①缺参与物 state 不再 AttributeError:`audit.py` charge 前提推导加 None 守卫;新增 `CHECK_PARTICIPANT_STATE_REFS` 检查(violated/participant_state_missing),parse 检查记 unknown(引用悬空≠语法非法),后续项 unknown+prerequisite_failed_not_run;②admission 新行 **R1b**(悬空引用 reject,理由码保留不压平成 R1:structure_unparseable,mimo 3.2(2));③context 缺失 ⇒ condition_check=**unknown**(condition_assessment_not_run),不得 not_applicable(mimo 3.2(1));④**R5c required_check_coverage_missing**:必需适用检查(REQUIRED_CHECK_NAMES)缺覆盖 ⇒ 不得 R6;窄 audit_scope 只是诊断;语义 NA 白名单(`SEMANTIC_NA_ALLOWED`:关闭的有限规则诊断/汇总边)外的 NA 记缺口;⑤**R6 重定义**:全部必需适用检查覆盖且 verified、无 unknown/violated/缺输入未执行;⑥自报 `transformation_signature_status=verified` 不授信:中心检查须 `center_evidence`(注册 checker 版本 ∈ `CENTER_CHECKER_REGISTRY`,现含 ppv1-donor-diagnostic-3),无证据 ⇒ unknown(center_evidence_missing),declared 状态只进 detail;⑦R5d 触发集合显式限定 {element,charge}(mimo 3.2(4)),其他 violated 走 R5v declared_violated_other;⑧**input_hash** 覆盖实际科学输入:hypothesis 完整语义载荷(to_dict 含 requirements/assumptions/dependency_refs)+ sorted state ids + context_id + audit_scope + checker_versions + 中心 checker | `test_ppv1_r2_chem.py` 9 例(missing-state/无 context/窄 scope/自报签名/真实诊断证据到 R6/未注册 checker/center_mismatch→R5v/R5d 限定/input_hash) | 探针 `admission_*`、`missing_state_*` 全部翻转:no_context→R5 retain;窄 scope→R5c;缺 state→R1b reject 不崩溃 | 中心检查的其他注册确定性 checker(供体诊断之外)须独立列项评审后加入注册表;审计调用方(执行流)在 S3 接线 `center_evidence` |
| **R2-02** 增强立体规范化+公开表示往返 | `chemstate.py` v3:身份键 = **规范化 canonical CXSMILES**(剥原子映射号 + 剥 ABS 冗余段)。RDKit canonical 写出器对增强立体做规范:AND/OR 组**整组翻转**同键(同一相对事实);**部分翻转**保持不同;AND vs OR 不合并;原子排列归一。`smiles_isomeric` = 同一规范化串(**携带 \|&1:…\|/\|o1:…\| 注解**),重解析重建同 state_id(v2 用普通 MolToSmiles 丢注解);plain 与 \|a:…\| 同键同公开表示;无组分子输出与 v2 逐字相同(无 CX 段)。`substrate_profile.structure_smiles` 用 state.smiles_isomeric(同源);strict 轴 `strict_identity_of` 同一键;identity_fidelity 检查改为**分轴呈现**(任一轴≠as_written ⇒ unknown + 轴列明,mimo 1.4(4)) | `test_ppv1_r2_chem.py` 10 例(plain=ABS/单中心 AND/OR 整组反转/双中心部分反转控制/AND≠OR/4 输入往返/profile 往返/strict 同规范化/映射号/手性 ID) | 探针 `f05_*` 全部翻转:roundtrip 4 输入 true;整组反转 4 例 current_identity_equal=true;部分反转控制例 false | 互变/质子化等价类 edge_kind 与 scoring_key 标记 = contract clause pending(S3;docstring 显式标注,不得当已实现);fidelity 的 radical 轴登记为已知缺口(身份层区分,保真轴未实现) |
| **R2-03** 供体诊断实际净变化+联合对称 | `audit.py` check_edit_against_donor v3:①判定基础 = **实际净变化集合** = 键 diff(kekulé 归一,芳香表示差异不是化学变化)∪ 原子增删 ∪ 逐原子(形式电荷/ΔH/CIP 立体)diff;声明的编辑原子单列 `declaration_only`,**不并入变化集**(v2"声明触及即命中"废除);②**零净变化**(执行前后结构身份一致)⇒ center=unknown(no_executed_change)永不 True(真实执行器 single→single 与 s→d→s 两例复现);③**声明–执行对账** `_declaration_accounting`:声明键变化(atom 对+to_order)须实际出现、实际键变化须被声明覆盖、add_atom 原子须存在/被声明;失配 ⇒ declaration_mismatches,strict/center 至少 unknown(mimo 5.2(a));④**联合中心对称** `_joint_symmetric_image`:symmetric_equivalent=True 须存在**单一自同构**把整个中心集合映到实际变化集合(GetSubstructMatches 枚举,截断 ⇒ unknown);单原子轨道覆盖不再冒充(环己烷 {0,1} vs {0,3} 反例判 False);⑤**plain 产物 vs mapped 执行图对账**:不一致 ⇒ 两轴 unknown+原因;⑥extra_changes 逐原子 Δ 补 **ΔH 与 ΔCIP**(before/after 成对输出);⑦等价类降为披露(验证+equivalence_basis=canonical_rank_breakTies_false+拒用记录),不参与判定;⑧等价类四组夹具:对称命中/破对称后不外推/非等价类拒/部分缺映射 unknown | `test_ppv1_r2_chem.py` 11 例 + 既有 D01/D02/F11 用例续绿 | 探针 `f11_*` 全部翻转:zero_net_change→None+理由;联合反例→False;plain/mapped 不一致→双 None;非键变化可见(charge 案例center=True at center) | 完整供体变换模板(供体侧预期键变化对比)按阶段排期 S3 接线;当前命名诚实:**实际净变化区域诊断**(docstring 声明,不冒充变换一致);芳香环编辑造成的环重感知按实际变化如实报告(苯测试已改为诚实结果) |
| **R2-12** 冻结门禁逐产物拒绝真实消费 | `audit.py` decide_admission 新行 **R2p**:`gate_decisions.per_product_verdicts` 被真实消费——全部共同产物被活动门禁拒绝 ⇒ reject(all_products_gate_rejected);部分被拒 ⇒ retain_conditional(被拒产物**保留拒因、不可展开**;reasons 含逐产物 position/原因,可选 product_state_refs 落到具体 state_ref);不删除被拒共同产物、不改冻结门禁真假、不把明确拒绝降成普通 unknown;消费开关 `per_product_gate_consumption ∈ {on,off}` 由 **AdmissionPolicy 显式版本化**(off=显式 diagnostic-only 声明,非遗漏);mapper 版本升 ppv1-gate-mapper-2 | `test_ppv1_r2_chem.py` 5 例(全拒 reject/部分拒 retain+拒因/state_ref 落名/策略开关+往返/全 accepted 无影响) | 探针 `mapped_per_product_reject_ignored` 场景翻转:全 verified+逐产物拒绝不再 expand | mapper 的 gate_atom_mapping_declared 仍为只读旁证(启用为拒绝门禁须扩 DEFAULT_REJECT_GATES 并升策略版本,mimo 3.2(6) 文本已写);事件层"被拒产物不展开"的最终执行在 S3 展开计划接线(存储线已校验展开计划范围) |

### 条件与科学前提线(r3-cond 分支,8edf3a0;R2 复审 §6 线 2)

| 项 | 修复(代码位置) | 测试 | 结果 | 未完成边界 |
|---|---|---|---|---|
| **R2-04** 要求所属边/阶段;转换错杀/洗冲突;分支共享 | `path_context.py`:Requirement 构造即绑定引入阶段/场景/边(`_bind_requirement`,introduced_phase_id/scenario_ref/introduced_edge);评估用**该要求引入阶段**的适用事实(`_applicable_facts`/`_effective_phase`),不拿新阶段事实重评旧要求;阶段转换冻结 `phase_history` 历史快照(snapshot_basis=scenario_transition),路线聚合 `route_assessment` = 历史快照逐边合取+当前 live——**旧边冲突保持**;本步 vs 全路线两层 API(`current_step_assessment`/`route_assessment`);Requirement/ConditionFact/Dependency 全 frozen dataclass + 派生路径深拷贝(分支互不污染);context_id 继续覆盖全部语义字段(phase_history 入哈希);转换只影响后续,不写成反应边 | `test_ppv1_r2_conditions.py` 7 例 | 探针 phase_transition_false_conflict(conflict→compatible 路线)、phase_transition_erases_past_conflict(路线保 conflicted)、requirement_branch_alias(改 A 不动 parent/B)全部翻转;F02 固定场景正反例续绿 | 空 phase_id 事实对所有阶段适用(v2 语义,测试有对照);phase_id 回退复用的边角 per 行重复但合取幂等 |
| **R2-05** 区间/点/单位/物种作用域 | 区间×点双向+退化区间,独立理由码(point_in_uncertain_range/point_outside_interval);`CONDITION_KEY_UNITS` 规范单位表,单位不匹配 ⇒ **unknown(unit_mismatch)**,不做 K→°C 换算(显式边界:可入账不参与数值比较);物种键 `_assess_species_requirement` **实体身份先匹配**(他实体缺席≠本实体状态;多供体并存不 last-wins;同实体 present+absent 才是不一致);枚举键(oxygen_regime 封闭集)不匹配仍 conflict;label 定案:**仅区间键+注册表(空⇒unknown)**,物种/枚举键走 entity/枚举比对(新 VALUE_BASIS_ENTITY) | 同上 8 例 | 探针 point_interval_*/temperature_kelvin_*/unrelated_donor_absence/multiple_present_donors 全部翻转 | 首版无单位换算(评估时 unknown+unit_mismatch);物种键字符串未匹配 ⇒ unknown(不可解析实体引用不判 conflict) |
| **R2-06** 再生支持≠启动供给已解决 | `resolve_dependency` 增 `support_axis`(reaction/regeneration/initial_supply,默认 reaction,轨迹按轴留痕);仅再生支持 ⇒ unresolved_initial_supply 保留;补 initial_supply 轴证据才解决;环不自动 reject、不称化学不可能;关系未支持单独披露 `unsupported_relation_cycles` | 同上 4 例 | 探针 regeneration_only_cycle_loses_startup_unknown([ ]→[[A,B,C]])、three_node_unresolved_control 保持 | — |
| **R2-07** 假设变体身份 | `hypothesis.py`:hypothesis_id 哈希纳入 requirements(全语义,顺序无关排序)/assumptions/dependency_refs——同父同结构同来源但条件/依赖前提不同 ⇒ **不同 id 可共存落账**(put 不冲突);相同语义重放同 id 幂等;from_dict 版本门 v3 | 同上 3 例 | 探针 hypothesis_condition_dependency_identity_collision:三 id 全异、second_put 无异常 | audit input_hash 见化学线 R2-01(两端配合) |

### 存储与旧数据适配线(r3-store 分支,af5b4e0;R2 复审 §6 线 3)

| 项 | 修复(代码位置) | 测试 | 结果 | 未完成边界 |
|---|---|---|---|---|
| **R2-08** 结构状态与出现分离不彻底 | `store.py`:representation_fidelity 移出 `_STATE_SEMANTIC_FIELDS`(入 `_STATE_APPEARANCE_FIELDS`);同图不同来源 fidelity 同 state_id 各自 appearance,不冲突、不升级;`get_state` 兼容形状(顶层=严格事实+appearances+首出现镜像,docstring 声明取用方式);`legacy_reader.py`:导入先保留**全部 occurrence** 再归并分子身份(不再按 state_id 建字典覆盖)——同事件同图不同位置两条原串/来源都保留;root 再出现(CCO→CC=O→CCO)为 source_product 出现;报告位次按物种去重+留痕 | `test_ppv1_r2_storage.py` 4 例 | 探针 same_structure_source_fidelity(Conflict→accepted)、legacy_cycle_import(n=2)、legacy_same_structure_two_positions(双出现保留)翻转 | v2 账本(ppv1-store-2)按未知版本拒绝(fidelity 移出致语义块布局变化;v2 仅存在于合成测试目录,无线上数据,不提供迁移,docstring 声明) |
| **R2-09** 真实提交入口参照校验/重放 | `store.py submit_event`:participant_state_refs 从 event.participants **实际派生**(少报产物拒绝);`_check_hypothesis_event_relation`(parent/锚点/participants 一致;同 ID 异内容随事务提交 ⇒ Ppv1EventConflict 不静默忽略);`_check_projection_scope`/`_check_expansion_plan`(投影只指本事件产物、计划产物范围合法+互斥+无悬空);首次违约零写入回滚(全部校验先于 INSERT);重放核验**全部必要记录**(states/出现/假设/投影/计划;随事务再提供的 states **不修补**缺行)⇒ 缺任一 Ppv1LedgerCorrupt | 同上 7 例 | 探针 event_refs_omit_real_product/event_hypothesis_mismatch/existing_hypothesis_payload_ignored/commit_invalid_projection_and_expansion/replay_missing_* 全部翻转 | 首版重放策略=报损坏,无自动恢复;state 身份重推导未在 store 层硬接(R2-02 在 chemstate 层已使同事实输入必然同 id,构造边界欺骗检查仍在 events.build_event_states) |
| **R2-10** 对象版本门接 writer | `store.py`:`_check_object_version` 在**任何写入前**校验 states/hypothesis/event/投影/计划的对象版本(引用 profile 常量);put_state/put_hypothesis/put_provenance 同样设门;event 持久 payload 保存 schema_version;reopen 支持集引用常量(修复基座升版后"新建库无法重开"的自洽 bug) | 同上 4 例 | 探针 future_object_schemas_written(created=True→Ppv1ObjectSchemaError+counts 全 0)翻转 | legacy 缺版本字段走 legacy_reader 版本名单(v43-store-1/2)兼容,不照搬"凡缺均拒" |
| **R2-11** 损坏引用不得借根 | `legacy_reader.py`:root 须 parent_path_id 空 AND event/position 指针空 AND substrate_identity 与 run 根身份一致;子路径指针损坏 ⇒ CN-only+原因码(child_missing_archive_pointers/archive_pointers_broken/root_identity_unconfirmed),分轴 unknown+uncertainty note;旧库字节不变 | 同上 3 例 | 探针 child_missing_archive_pointers_as_root(root 冒充→CN-only+原因)翻转 | — |

## 3. P2 事项处置(§4 表)

| 项 | 处置 | 测试 |
|---|---|---|
| 断键夹具不实 | `test_ppv1_s2.py`:S_O_3→S_O_1(skip_control.json 对照:同环境 S_C_2–S_O_1 断键成功,产物 CC.CCO);恢复真实断言、删"环境原因"skip;苯编辑同款死 skip 一并清理(实测可执行) | test_f11_same_center_*(实跑)、test_d02_*(实跑) |
| 处理池跳阶段绕哈希链 | `pool_audit.py`:校验**相邻实际记录** output==input(非协议索引相邻);跳过/注入须 from_previous=False+transition_reason | test_p2_pool_* 2 例 |
| scope 冒充已评估 | `path_context.py`:assessment_scope 从实际执行的必要检查派生;缩范围留痕 scope_narrowed/scope_narrowed_by;缩 scope 不得隐藏必需未知 | test_p2_scope_* 2 例 |
| coverage 同键 last-wins | 聚合按最坏状态(conflict>unknown>satisfied),assessed/satisfied 分开,covered_keys 不含冲突键;总判定不回退 | test_p2_coverage_* |
| 同值不同来源误标不一致 | `_semantic_value_signature`(状态+值+单位,数值归一)比较;同值不同来源不降 unknown,来源全保留 fact_sources;值真正不同才 unknown | test_p2_identical_facts_* |
| basis 形状不一致 | 构造/from_dict 双路径校验(dict⇒range;标量⇒point/optimum/unspecified;字符串⇒区间键 label/实体键 entity),不一致抛 ConditionContractError;不静默规范化 | test_p2_basis_shape_mismatch_rejected_at_construction |
| 标签规则文字范围过宽 | 定案:label 仅区间键+注册表;物种/枚举另行(见 R2-05) | test_r2_05_label_basis_only_for_interval_keys |
| study_map 下界 | `provenance.py`:SupportGroup 增 count_basis ∈ {exact, known_lower_bound, unknown_study_identity} + n_unresolved;部分映射 count=1 标 known_lower_bound | test_p2_study_map_count_basis_axes |
| legacy provenance 引用解析 | 导入的 provenance_refs 指向**新 record_id**(映射方案);ProvenanceInfo 增 legacy_evidence_id(旧 ID 可追溯);get_provenance 可解析 | test_p2_legacy_provenance_refs_resolvable |
| pending 子句标注 | local_delta/edge_kind/scoring_key = "contract clause, implementation pending"(audit/chemstate docstring;有测试钉住声明存在,不当已实现) | test_pending_clauses_declared_not_implemented |

搜索上限拆分/配置往返/零预算/负 limit:上轮已修,R2 复审确认保留,回归续绿。

## 4. mimo 第二轮意见处置(按 R2 复审 §5 采纳边界,不整段照搬)

| mimo 建议 | R2 复审裁定 | 本轮落实 |
|---|---|---|
| 缺 context ⇒ not_applicable 直达 R6 | 接受 | condition_check=unknown(condition_assessment_not_run)+R6 定义收紧(化学线 R2-01) |
| 声明原子混入变化集/声明-执行一致性未实现/非键变化缺轴 | 接受+补强(真实执行器反例) | 实际净变化集合+declaration_accounting+ΔH/ΔCIP(化学线 R2-03);真实执行器零净变化两例钉住 |
| point×interval 假 conflict | 接受 | 三态+独立理由码(条件线 R2-05) |
| label"一律 unknown" vs 非区间键硬判 | 定案 | label 仅区间键;物种/枚举走 entity 比对(条件线) |
| ABS/plain 分裂 | 接受 | 归一(plain=ABS 同键)+ AND/OR 整组反转归一(化学线 R2-02;超出 mimo 的"只剥 ABS") |
| R1 吞悬空引用;R5d 全集触发 | 接受 | R1b 分行;R5d 限定 {element,charge}+R5v(化学线) |
| 未落地条款标注 | 接受 | pending 显式标注+测试钉住 |
| 同位素/自由基口径、coverage 双报、mode 方向词 | 接受(字段级) | accounting_notes/excess_on-missing_from 结构化/H+_count1;coverage 最坏状态;radical 轴登记已知缺口 |
| "中心 verified 必须仅由供体诊断生成" | **不采纳(过窄)** | CENTER_CHECKER_REGISTRY 注册制:其他注册、版本化、可追溯的确定性 checker 亦可;自报字符串一律不够 |
| "scope 只由可用事实键派生" | **不采纳(不足)** | scope 从**实际执行的检查**派生(有事实≠已检查);缩范围留痕 |
| 单纯剥 ABS 解决 AND/OR | **不采纳(不足)** | canonical CXSMILES 规范化(整组反转归一);公开表示往返一并修 |
| 近似口径说明+夹具不足以解决联合反例 | 接受 | symmetric_equivalent 由联合图映射证明(单原子轨道不冒充) |

## 5. 测试证据与命令

~~~bash
# 全量 ppv1(联合验证,7 文件)
PYTHONDONTWRITEBYTECODE=1 ~/miniconda3/envs/depending43/bin/python -m pytest \
  tests/test_ppv1_profile.py tests/test_ppv1_domain.py tests/test_ppv1_s2.py \
  tests/test_ppv1_rework.py tests/test_ppv1_r2_conditions.py \
  tests/test_ppv1_r2_storage.py tests/test_ppv1_r2_chem.py -q -p no:cacheprovider
# => 226 passed(profile 23/domain 31/s2 60/rework 16/conditions 31/storage 26/chem 39)

# G01 legacy 回归(全量 not slow)
PYTHONDONTWRITEBYTECODE=1 ~/miniconda3/envs/depending43/bin/python -m pytest \
  tests/ -q -m "not slow" -p no:cacheprovider
# => <见 §5.1>

# 复审探针复跑(修复后;探针即审核附件原样,未改)
task_scratch="$(mktemp -d /private/tmp/ppv1-r3-after.XXXXXX)"
cp docs/review_evidence/ppv1_r2_2026-10-06/*.py "$task_scratch/"
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src \
  ~/miniconda3/envs/depending43/bin/python "$task_scratch/chemistry_probe.py"
# chemistry_probe:exit 0;admission_no_context→R5、narrow_scope→R5c、
#   missing_state→R1b、zero_net_change→None+no_executed_change、
#   independent_orbits→False、plain/mapped_disagree→双 None、
#   export_roundtrip 4 输入 roundtrip_same=true、
#   whole_group_inversion 4 例 current_identity_equal=true
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .../admission_probe.py
# no_context/only_structure_parse→retain(R5/R5c);context_provided→
#   retain(中心缺证据;不再 R6)
# conditions_probe/storage_probe:在第一个旧反例段即抛结构化错误
#   (ConditionContractError/Ppv1SubmitContractError 等)= 修复后行为;
#   分段驱动对照见各线报告(条件线 before/after JSON、存储线驱动日志)
~~~

### 5.1 G01 legacy 回归结果

~~~
$ ~/miniconda3/envs/depending43/bin/python -m pytest tests/ -q \
    -m "not slow" -p no:cacheprovider
837 passed, 16 deselected in 230.73s (0:03:50)
~~~

837 = 既有 legacy 通用单测 611(零行为回归)+ 本轮 ppv1 226;
16 deselected = `slow` 标记的真实资产慢测(未运行)。无 failed、
无 skipped(上轮 1 处显式环境守卫 skip 已随断键/苯两处死 skip
清理一并消失——本轮 skip 清理见 §5.3)。

### 5.2 红验证(先红后绿)

- 基线探针复跑(本轮开始):4 探针输出与审核附件**逐字节等价**
  (diff 仅时间戳/临时路径/traceback 路径)——R2 反例全部在本轮
  修复前复现;
- 行为级红(化学线):`/private/tmp/ppv1-r3-red.10mlBj/
  red_behavior_probe.py` 对基线 0002f71 断言 v3 预期,**8/8 失败**
  (plain=ABS/整组反转/往返/零净变化/缺 context+自报签名/窄 scope/
  逐产物拒绝/联合对称含轨道类);
- 条件/存储线:各自新测试在修复前 28 红/导入失败(实现前收集即
  ImportError),详见两线报告;
- 修复后:226 全绿。

### 5.3 修改的既有测试与理由(仅被复审证伪语义)

| 测试 | 改动 | 理由 |
|---|---|---|
| test_ppv1_s2::test_admission_all_verified_expand | 补真实供体诊断 center_evidence 才到 expand | 编码"自报签名可 R6"(R2-01 证伪) |
| test_ppv1_s2::test_admission_policy_decision_table_explicit | 9 行→13 行(+R1b/R2p/R5v/R5c)+per_product 开关 | 决策表扩展(本轮回修) |
| test_ppv1_s2::test_p2_2_legacy_gate_mapper_* | mapper 版本 pin -1→-2 | 版本升 |
| test_ppv1_s2::test_f01_* 两例 | omission 模式断言改结构化字段 | mimo 2.3(2) 采纳 |
| test_ppv1_s2::test_d02_symmetry_equivalent_center_via_validated_class | 苯等价类夹具:保留执行断言,判定走联合映射;等价类仅为披露 | v2"等价类区域覆盖⇒symmetric_equivalent"被联合反例证伪;苯芳香编辑产生真实环变化,按实际变化诚实报告 |
| test_ppv1_s2::test_f11_same_center_*(断键) | S_O_3→S_O_1+恢复断言 | 夹具原子 ID 不存在(§4 P2) |
| test_ppv1_s2::test_h04_*/test_f06_three_node(条件线) | "全部边 supported⇒启动未知为空"改为分轴 | R2-06 点名的过强正例 |
| test_ppv1_profile 2 处版本 pin | -2→-3 | 版本升 |
| 7 处 -2 字面量(admission/pool-order/store 重开等) | 常量化/-3 | 版本升(含 store 线修复"基座升版后重开失败"自洽 bug) |

skip 说明:本轮**无新增 skip**;清理 2 处"环境原因"死 skip
(苯编辑/断键,实测可执行)。全仓 slow 标记真实资产慢测照旧
deselected,不触发。

## 6. schema/语义版本与兼容策略

| 契约 | v2 → v3 | 兼容声明 |
|---|---|---|
| profile | ppv1-profile-2 → -3 | profile 从未放行执行流(入口 fail-closed),无已发布 run/产物;升版即生效,无数据迁移 |
| chemstate | -2 → -3 | 同上;身份键改规范化 CXSMILES(plain/ABS 同键、整组反转归一——v2 键值全变,无历史数据);smiles_isomeric 对无组分子输出与 v2 逐字相同 |
| hypothesis | -2 → -3 | +requirements/assumptions/dependency_refs 入身份;同反应不同前提 ⇒ 新 id |
| event/store | -2 → -3 | store 语义块布局变化(fidelity 移出);v2 库按未知版本拒绝(v2 仅存于合成测试目录,不迁移,docstring 声明);event payload 持久化 schema_version |
| context/dependency/condition | -2 → -3 | 要求绑定引入阶段/历史快照/不可变化;assessment 域升 -2→-3 |
| provenance | -2 → -3 | count_basis 分轴+legacy_evidence_id |
| audit/admission | -2 → -3 | +R1b/R2p/R5v/R5c;participant_state_refs 检查;center 证据门;input_hash 语义变化 |
| donor_diagnostic | -2 → -3 | 实际净变化/对账/联合映射;新字段 declaration_only/declaration_mismatches/equivalence_basis/joint_mapping/net_change_empty |
| gate_mapper | -1 → -2 | 逐产物 verdict 被消费(语义变化) |
| substrate_profile/pool_audit/pool_order/input_preview | -2 → -3 | 随族升版(全氢基准/哈希链已 v2 语义,本轮随族) |
| run identity | v43-identity-2(不动) | 本轮未触碰 run_identity.py;legacy resume 语义不变 |
| search_limits | -2-proposed(不动) | proposed 草案,S3 落地 |

legacy_v43:零改动承诺继续成立——本轮全部改动在 `pollutant/` 包、
ppv1 测试与 profile.py 版本常量;`nodes.py` 等冻结路径、
`storage/run_identity.py`、模型/依赖/资产均未触碰。

## 7. 剩余未知与边界(不宣称冻结)

1. 化学判据 v3 **未冻结**:mimo 第三轮评审请求已更新
   (§8),待用户转交;冻结以本轮 review + mimo 回应与本仓程序证据
   互证为准。
2. 契约 v3 未冻结;`delivered_stages` 仍为 S0–S2,S3 入口
   fail-closed 未解除。
3. **S3 排期项(不冒充已实现)**:中心证据的其他注册 checker;
   执行流接 center_evidence;供体变换模板的供体侧预期对比;
   local_delta/edge_kind/scoring_key 标记;互变/质子化等价类;
   被拒共同产物的展开计划消费(存储线已校验范围,接线在 S3)。
4. 已知缺口(登记):fidelity 的 radical 保真轴未实现(身份层区分);
   条件单位不做换算(评估时 unknown+unit_mismatch);物种键不可解析
   引用 ⇒ unknown。
5. 科学验收整体 pending(S5);226 项工程测试不构成任何路径科学
   性能声明。

## 8. mimo v3 化学评审请求

已更新 `docs/mimo_ppv1_chem_review_request.md` 为 v3 文本
(判据一~五按本轮实际实现修订:规范化 CXSMILES 身份、admission
13 行决策表+证据门、条件阶段绑定、实际净变化诊断、逐产物门禁
消费)。自包含、规则级夹具表述、无金标;**由用户转交**,回复原文
落盘 `docs/`。

## 9. 与原规格的冲突清单

无新增实质冲突。三处"规格未逐字规定、按复审验收收紧"的说明:
- 实施书 §8 admission 四态处置 → 本轮增加 R1b/R2p/R5v/R5c 四行
  (复审 R2-01/12 验收要求;不改四态枚举本身);
- §5.1 "state_id 按确定性分子图生成" → v3 具体化为规范化 canonical
  CXSMILES(整组反转归一 = 相对立体事实同一性;复审 R2-02 验收);
- §6 条件评估 → 要求绑定所属边/阶段+历史快照合取(复审 R2-04
  验收;与"累积约束不许覆盖"一致)。
