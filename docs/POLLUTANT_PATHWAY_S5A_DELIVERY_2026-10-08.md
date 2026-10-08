# pollutant_pathway_v1 S5a 交付书(评测接口工程侧先行批)

日期:2026-10-08。实施方:S5a 批次唯一实施代理(工程侧先行,用户已
授权;S5b 真实数据评测未启动、本批一律未触碰)。

- 任务书:`docs/POLLUTANT_PATHWAY_S5_SPEC_TASK_2026-10-08.md`(唯一
  任务书,tokeasy 撰写、用户拍板采用);
- S4 交接:`docs/POLLUTANT_PATHWAY_S4_CODEX_REVIEW_R4_2026-10-08.md`
  (S4 通过、P1=[];§5 P2/§8 授权搭车,本批同车兑现);
- 证据:`docs/review_evidence/ppv1_s5a_impl_2026-10-08/`(SHA-256
  封包,嵌套 manifest 纳哈希);
- mimo 化学评审请求(本批产出、只写不发):`docs/mimo_ppv1_chem_
  review_request_r21.md`。

**结论先行**:S5a 交付评测接口(输入/参考图/split/leakage/输出指标
schema + 预注册模板 + 零 LLM 确定性评测器 + S5-01~28 全部落测试 +
R4 §8 授权搭车 P2);PPV1 全量 1045 绿(976 既有 + 69 新)、G01 安全
隔离 1647/8/17 绿、父基线 12 红 + 2 collection(新测试真咬合);
**零科学指标数值、零金标/题面/收费请求;科学状态只用
interface_verified_only / pending;S5b 未启动**。

---

## 1. 定位与边界

- 本批是 **S5a(接口与数据规格)**,不是 S5b(独立数据评测):全部
  夹具为自包含合成规则级(合成参考图 + 公共 `start_run` 真实链路合成
  run),不读任何真实科学数据/金标/题面/封存逐题 run;
- 评测器**零 LLM 判分**(评分路径无任何模型调用;自然语言字段不进
  判定,S5-25);收费 provider 默认关(`real` 无逐次授权结构化拒绝,
  S5-26;模块无任何网络代码,网络 0、费用 0);
- 评测器**永不生成 `evaluated_*` 状态**(§11 第 19 步:最终科学状态
  由用户/teacher 按预注册裁定;程序只发 pending_*/interface_verified_
  only/blocked_*);
- §10.1 全部 20 项 TBD 属用户/teacher 裁定,未代定任何阈值/样本量/
  分母/金标口径;匹配规则为 proposed(预注册模板中逐项标注);
- criteria-v1 冻结正文与 FREEZE_RECORD 逐字节不改;S4/S3 已关项不
  重开;legacy/G2/AtomTool/export_v3 零触碰;**不实施 S5b**。

## 2. 交付清单对照(任务书 §15 S5a)

| # | §15 交付项 | 落点 | 状态 |
|---|---|---|---|
| 1 | 评测输入 schema + 参考图 schema(§7 全字段)+ source group/split manifest schema + leakage check 规格 | `src/pathway_v43/pollutant/reference_graph.py`(§7.1–7.5 全字段确定性校验,fail-closed)+ `evaluation.py`(`validate_evaluation_input` §8.1、`validate_split_manifest` §6.3、`check_leakage` §6.3) | 交付 |
| 2 | native export 消费契约(§3.1,消费 S4 公开入口;合成 run 产物走真实链路,不造假对象) | `evaluation.native_export_reader_from_ledger` → `native_export.read_native_export`(S4 首消费链:integrity→版本门→digest→权威引用→策略→staleness);测试经公共 `start_run` 真实生成 run 与导出 | 交付 |
| 3 | 输出指标 schema(§8 输出 + §9 八项指标分轴;零科学指标数值;状态只用 interface_verified_only/pending) | `evaluation.evaluate_scientific`(§8.2 全字段输出 + §9.1–9.8 聚合接口:`reference_edge_recall`/`key_intermediate_recall`/`confirmed_error_rate`/`outside_reference_unverified_edges`/`environment_conflict_rate`/`endpoint_mineralization_misclaim_rate`/`depth_performance`/`budget_omission`;axis=domain/track/split;分母/阈值逐项 `TBD_USER_TEACHER_DECISION`;状态枚举 §12,程序永不发 evaluated_*) | 交付 |
| 4 | preregistration 模板(§14.3:TBD 逐项标注/proposed 规则/未冻结阈值/接口级指标/冻结前不得发布) | `src/pathway_v43/pollutant/preregistration.py`(§10.2 全字段模板;20 项用户/teacher 裁定逐项 TBD;`publication_restriction=no_release_before_freeze`;`frozen=False`) | 交付 |
| 5 | 评测器实现(零 LLM/收费默认关/损坏输入结构化拒/确定性一致/输出 hash 稳定) | `evaluation.py` + `reference_graph.py`(结构化 `*ContractError` fail-closed;输出 canonical_json 无时间戳 + `output_sha256`;同输入字节级一致 S5-24) | 交付 |
| 6 | 规则级合成测试(§16 全部 S5-01~28 + §14.1 行为点) | `tests/test_ppv1_s5a_schema.py`(20)+ `test_ppv1_s5a_evaluator.py`(32)+ `test_ppv1_s5a_isotope_regressions.py`(17)= 69 项 | 交付 |
| 7 | 接口报告(无金标/无题面/无收费请求;携带 R4 §5 交接常驻披露与遗留 P2) | 本交付书 §5/§6 | 交付 |

## 3. 入口 → 行为 → 证据 → 红绿映射

**入口**:公共入口三件——

1. `reference_graph.validate_reference_graph / load_reference_graph`
   (参考图权威输入,§7 全字段;缺字段/坏版本/重复 occurrence/悬垂
   引用/矿化注记最低口径缺字段 ⇒ 结构化拒,S5-01);
2. `evaluation.evaluate_scientific(evaluation_input, *,
   reference_graphs, native_export_reader, preregistration)`
   (§11 判分流程 1–18 步程序侧;step 19 人裁永不程序化);
3. `preregistration.build_preregistration_template /
   preregistration_frozen_fields`(§10.2/§14.3)。

**行为**(§11 确定性、可重放、零 LLM):

- 输入校验(manifest sha 绑定/导出版本绑定/题域与轨道一致性
  S5-21/22/lossy 投影契约)→ 泄漏检查(同 source group 跨集合
  S5-07/known-unseen 重叠 S5-08/路线与根对象跨集合 proposed 规则)
  → 导出读取(S4 公开 `read_native_export`;失败/lossy/缺席结构化
  披露,S5-28)→ 样本级匹配(节点严格身份 vs CN 旁证分轴、distinct
  occurrence 不合并、边参与物精确覆盖与共同产物保留、step_scope
  分轴、条件 conflict/unknown/compatible/preference/unmapped 分桶、
  endpoint/矿化声明检查、预算漏展开分桶、深度分桶)→ 分层聚合
  (§9 八项,分轴接口结构)→ 确定性输出与 `output_sha256`;
- 状态裁定顺序(§12):leakage 失败 ⇒ `blocked_leakage`(零聚合);
  导出缺席/全部样本不可评 ⇒ `pending_no_independent_data`(优先于
  接口模式,S5-28);接口验证模式 ⇒ `interface_verified_only`;
  prereg TBD ⇒ `pending_preregistration`(S5-23);否则
  `pending_user_teacher_decision`。

**证据**:`docs/review_evidence/ppv1_s5a_impl_2026-10-08/`(README/
commands/manifest/SHA256SUMS;ppv1/g01/parent_baseline/scripts 子包,
17 附件,嵌套 manifest 纳哈希;G01 脚本 fresh /private/tmp 执行)。

**红绿**:

| 项目 | 数字 | 说明 |
|---|---|---|
| PPV1 全量(当前) | **1045 passed / 0 skipped,exit 0** | 976 既有 + 69 新增;37+3 文件 |
| 父基线 a19960f(当前测试同字节) | **12 failed + 2 collection / 981 passed** | 2 collection = S5a 模块父上缺失;3 = isotope 搭车 P2 行为/字段(presence records isotope/axis_detail 披露/版本登记);9 = 版本字面量(profile-20/donor-diagnostic-10) |
| G01 安全隔离 | **1647 passed / 8 skipped / 17 deselected,exit 0** | 1578(r3 谱系)+ 69;303 输入前后 SHA-256 全同 |

G01 逐项缺席披露(缺席不算通过):v4 parser 对照根 1(v4 红线不
复制);v2 provenance/summary 2;v3 冻结真实评价基准 5;17
deselect = 16 slow + 1 显式排除 charge/evaluation fixture(沿
R7→S5a 谱系)。工程回归不外推 dev/298 科学性能。

## 4. S5-01~S5-28 逐项对照表(验收矩阵)

| 编号 | 场景 | 落点测试 | 通过 |
|---|---|---|---|
| S5-01 | 合成 reference graph 读取(schema/版本/字段完整性;缺字段明确失败) | `test_s5_01_reference_graph_full_field_validation`、`..._missing_field_fails_with_field_path`、`..._unknown_schema_version_refused`、`..._unparseable_file_refused` | 是 |
| S5-02 | A→B 与 A→C 备选不合并 | `test_s5_02_alternatives_not_merged`(两参考边各匹配不同事件;非精确覆盖单独披露) | 是 |
| S5-03 | 共同生成 B+C 不被报告 K 删 | `test_s5_03_coproduct_not_deleted_by_report_k`(匹配事件携带 [H][H] 共同产物;缺共同产物的事件只进覆盖失配披露) | 是 |
| S5-04 | distinct occurrence 不按 CN/首现合并 | `test_s5_04_distinct_occurrence_not_merged_by_cn`(两个 occurrence 条目保留;schema 重复 occurrence 拒绝) | 是 |
| S5-05 | 多条库记录同研究只计一组 | `test_s5_05_same_study_records_one_group`(泄漏检查记账:2 组/3 记录) | 是 |
| S5-06 | 研究身份 unknown 不进独立分母 | `test_s5_06_unknown_independence_not_counted` | 是 |
| S5-07 | 同研究相邻边跨开发/留出 ⇒ leakage 阻断 | `test_s5_07_source_group_across_splits_blocks`(blocked_leakage + 零聚合) | 是 |
| S5-08 | known/unseen 直接证据重叠阻断 | `test_s5_08_known_unseen_overlap_blocks` | 是 |
| S5-09 | 未画出的参考边不判错(coverage 限制) | `test_s5_09_unpainted_reference_edge_coverage_limit` | 是 |
| S5-10 | 严格身份与中心证据分轴,不授完整确认 | `test_s5_10_strict_identity_and_center_evidence_separate_axes`(conditional admission 不计 confirmed) | 是 |
| S5-11 | CN 相同不计严格结构命中 | `test_s5_11_cn_same_not_strict_hit`(对映体单元级 + 正控) | 是 |
| S5-12 | step_scope 分轴 | `test_s5_12_step_scope_separate_axis`(matched_structure_only;net/summary 不混) | 是 |
| S5-13 | 必要项缺失报 unknown | `test_condition_classifier_...` + `test_s5_13_14_15_condition_axes_end_to_end` | 是 |
| S5-14 | 明确 essential 冲突不含 unknown | 同上(essential_conflict 与 condition_unknown 独立分桶) | 是 |
| S5-15 | 历史来源条件保留不改写 | `..._end_to_end`(source_conditions_preserved 原样) | 是 |
| S5-16 | unknown/partial/conditional 不计 confirmed 不计错误 | `test_s5_16_unknown_partial_not_confirmed_not_error` | 是 |
| S5-17 | 仅 CO₂ 无根碳账不判矿化 | `test_s5_17_mineralization_negative_control`(真实链路负控)+ `..._without_root_carbon_flagged`(分类器负控)+ 正控(带证据合法) | 是 |
| S5-18 | stop budget/depth 不改写为终点/矿化 | `test_s5_18_stop_reason_is_not_endpoint` + 分类器负控 | 是 |
| S5-19 | 上游 unresolved 不被 recorded 洗白 | `test_s5_19_unresolved_dependency_not_washed`(真实链路 F02 保持 unknown + 分类器负控) | 是 |
| S5-20 | 预算未展开单独报告,不静默删分母 | `test_s5_20_budget_unexpanded_edge_separate_bucket` + `test_budget_omission_from_export_buckets` | 是 |
| S5-21 | dev/298 混合拒绝 | `test_s5_21_mixed_domain_refused` | 是 |
| S5-22 | known/unseen 混合拒绝 | `test_s5_22_mixed_track_refused` | 是 |
| S5-23 | TBD ⇒ pending,无科学通过结论 | `test_s5_23_preregistration_template_tbd_marking` + `test_interface_mode_status_and_pending_semantics` + `test_emitted_status_never_evaluated` | 是 |
| S5-24 | 同输入重复评测确定性一致(含 hash) | `test_s5_24_repeat_evaluation_deterministic` | 是 |
| S5-25 | 零 LLM;自然语言不改程序结果 | `test_s5_25_natural_language_cannot_change_result`(输入层自由文本 ⇒ 输出字节一致;参考图叙述 ⇒ 匹配结果不变) | 是 |
| S5-26 | 收费 provider 默认关(无授权网络 0 费用 0,不启动) | `test_s5_26_paid_provider_off_by_default` + 真实数据须批准预注册 | 是 |
| S5-27 | 含金标产物写普通目录拒绝 | `test_s5_27_gold_output_write_guard`(授权 gitignored 根放行) | 是 |
| S5-28 | S4 导出未交付 ⇒ 接口可验、状态 pending | `test_s5_28_no_native_export_pending` + `test_s5_28_unreadable_export_disclosed` + `test_lossy_projection_not_scorable` | 是 |

§14.1 行为点清单逐项同覆盖(输入 schema 校验/native export 读取/
参考图读取/节点与边确定性匹配/共同产物/备选/distinct occurrence/
step_scope/条件三分类/endpoint 与 stop 分开/矿化负控/budget omission
分开/unknown-partial 保留/输出 hash 稳定/重复评测一致/损坏输入明确
失败/参考缺覆盖不判错/unseen 不误报为 known)。

## 5. R4 §8 授权搭车 P2 落实清单(同批提交;全部披露/测试级,零新门、判定语义零变化)

| P2 项(R4 §5) | 落实 | 证据 |
|---|---|---|
| P2-1 四处 docstring/属性注释补 isotope | `audit.py`:`DonorConsistencyDiagnostic` 类 docstring(净变化集合加"同位素 diff")、`center_property_deltas` 字段注释(加 Δ同位素)、`_declaration_accounting` docstring(ops 无 isotope op 口径)、`check_edit_against_donor` docstring(extra_changes 加 Δ同位素) | 源码 diff;`tests/test_ppv1_s5a_isotope_regressions.py` 常驻回归同批 |
| P2-1 profile 旧注释修正 | `profile.py` r3 历史注释尾"profile 仍未放行执行流,无历史产物需要迁移" ⇒ v20 注释如实:S3b 起公开 PPV1 start/resume 已开放;旧版本载荷按既有版本门拒绝,迁移另议 | 源码 diff |
| P2-2 被增/删原子 records 补 isotope | `_atom_property_diffs` presence 分支:`atom_added` 记 after 侧、`atom_removed` 记 before 侧 isotope 单侧值(`_atom_change_summary` presence 分支本就消费该键;不改判定) | `test_presence_records_carry_isotope_disclosure`(父基线红 ⇒ 真咬合) |
| P2-3 audit center axis_detail 携带复算 extra_changes/center_property_deltas | `audit.py` axis_detail 增两键(源自 `_rerun_proof_record` 复算诊断;披露级) | `test_axis_detail_carries_recomputed_disclosures`(父基线红) |
| P2-4 isotope_contract 合成控制转常驻回归 | 对称四分案 + raw matcher 方向控制 + 标签方向控制(4 案)+ 篡改拒绝,从 `ppv1_s4_codex_r4_2026-10-08/isotope_contract/` 脚本与 JSON 取口径写成 `tests/test_ppv1_s5a_isotope_regressions.py`(17 项;不复制旧证据文件进交付,旧目录只读) | 全部通过;父基线 3 红 |

版本登记(既有规范):上述输出契约变化由
**ppv1-donor-diagnostic-9 → ppv1-donor-diagnostic-10** 承载(沿
S4 r3"语义变化由 donor-diagnostic 版本承载"先例;audit/admission
决策表与理由码不变 —— 判定语义零变化);profile 随登记
**ppv1-profile-19 → ppv1-profile-20**(同时登记 S5a 新契约)。9 处
测试字面量同步(disclosed;父基线 9 版本红)。

## 6. 契约版本登记(S5a 全部)

| 契约 | 版本 | 说明 |
|---|---|---|
| 参考图 schema | `ppv1-reference-graph-1`(新) | §7 全字段校验;`reference_graph.py` |
| split manifest | `ppv1-split-manifest-1`(新) | §6.3 划分清单 schema;`evaluation.py` |
| 评测契约 | `ppv1-evaluation-1`(新) | §8 输入/输出 + leakage + 确定性匹配/指标接口 + 零 LLM + provider 默认 off + 金标写入守卫;`evaluation.py` |
| 预注册模板 | `ppv1-preregistration-template-1`(新) | §10.2/§14.3;`preregistration.py` |
| 供体诊断 | `ppv1-donor-diagnostic-9 → -10` | 搭车 P2 披露承载(见 §5) |
| profile | `ppv1-profile-19 → -20` | 随登记 + delivered_stages 加 `S5a-interface` |

全部登记进 `contract_versions()`(profile 身份块)。

## 7. R4 §5 交接常驻披露(随本交付携带)

- isotope 表示的是**结构标签整数差异**(0=未标);0↔13 不断言样品
  实测同位素组成或核过程;
- violated 表示实际变化与声明中心范围不符,**不裁定反应化学不可能**;
  中心内可 verified 只认证表示层范围,不能读成酶反应机制已核实;
- **D/T 元素账计 H,身份/同位素轴区分,两个结论不互推**(常驻回归
  `test_deuterium_to_tritium_*` 两案对向保留);
- 固定 AtomTool 没有 isotope op;合成输出防御验证不证明正常工具会改
  标签(本批常驻回归全部为合成防御变异,同口径);
- `self_contained_recompute` 证明输入自洽重算,不认证编辑曾执行、
  来源真实性、生物可行性或污染物降解性能;
- 评测器接口验证与 S3/S4 工程绿数**不能倒推 dev 或 298 科学性能**;
  对外数字必须带题域标签(dev=B1 环境路径中间步骤、298=RHEA 通用
  酶学,双向不外推)。

遗留 P2 状态(R4 §5 全清单处置):P2-1/P2-2/P2-3/P2-4 已落实(本批
搭车);P2-5(主会话方向性 matcher 取证措辞、版本/字段红分类)为
评审侧文字裁定,不属实施批范围,状态不变。

## 8. 诚实边界与未完成项

- **零科学指标数值**:输出指标桶是合成规则级接口结果;未读任何真实
  数据,未跑任何真实评测;不宣布 dev/298 任何性能;置信区间/通过线/
  分母/样本量全部 TBD(§10.1,用户/teacher 裁定);
- **S5b 未启动**:题源/金标口径/划分/样本量/阈值/预算/provider 均
  无裁定;`data_scope=real` 无已批准预注册时结构化拒绝;
- 匹配/分桶/leakage 路线根规则为 **proposed**(预注册模板逐项标注),
  冻结前不改任何判定语义;评测器 `evaluated_*` 永不程序生成;
- 本批新增模块不写数据库、无网络代码;`persist_evaluation_output`
  的金标守卫为接口级预置(授权根镜像 .gitignore 金标隔离目录);
- 未完成项:mimo r21 请求**只写不发送**(按 AGENTS 三触发点,由
  用户决定是否送评;回复落盘后另行采信互证);S5b 全部前置裁定
  属用户/teacher;无一因实施阻塞遗留。

## 9. 数字汇总

- PPV1 全量:**1045 passed / 0 skipped / exit 0**(976 既有 + 69 新
  增:20 schema + 32 evaluator + 17 isotope 回归);
- G01 安全隔离:**1647 passed / 8 skipped / 17 deselected / exit 0**;
  303 输入前后 SHA-256 全同;
- 父基线 a19960f(同字节测试):**12 failed + 2 collection / 981
  passed**;
- 费用/网络/LLM 判分:**0/0/无**;金标/题面/封存 run/dependingv4/
  原 v3 评价资产访问:**无**;push:**无**(主会话负责推)。
