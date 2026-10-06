# pollutant_pathway_v1 S0–S2 第五轮回修交付书(R5)

- 日期:2026-10-07
- 回修依据:`docs/POLLUTANT_PATHWAY_S0_S2_CODEX_REVIEW_R4_2026-10-07.md`
  (R4-01～R4-11 + §4 披露项 + §5 mimo 采纳边界 + §6 R5 实施要求)
- 回修基线:e80f459(=审核 HEAD;六份必读文档全部读取;工作区原有
  三个用户未跟踪文件原样保留——R4 审查报告、mimo R4 回应、R4 审核
  证据目录,未回退未覆盖)
- 回修范围:**仅 S0–S2 底座回修**;S3 入口继续 fail-closed(未解除);
  契约与化学判据**不宣称冻结**(待 review + mimo 第五轮)
- 状态:三线(化学证据/条件前提/存储适配)+ 横切(hash/身份/清单)
  在统一接口下落地;全部 ppv1 测试 **381 通过**(312 存量 + 69 新增,
  0 skip);G01 legacy 回归全量 **992 passed / 16 deselected / 0 failed**
  (611 legacy + 381 ppv1,legacy 路径零改动)
- 探针纪律:R4 审核探针全部复制到新临时目录复跑(证据
  `docs/review_evidence/ppv1_r5_impl_2026-10-07/`);未在审核方证据
  目录写任何 SQLite/覆盖任何日志

## 0. 一句话结论

R4-01～R4-11 十一项 P1 与 §4 全部处置(实现+回归);新增 69 项
回归在基线 e80f459 **红 58/69**(11 个为正控制,基线亦绿——见
§5.1 红绿口径);复审探针的已复现反例逐项翻转(对照见 §5.3);
契约全族升 v5;**先统一载荷/身份/证明记录/出现集合接口,再三线
落地**(证明链 proof_record、事件 appearance manifest、CX 逐类
登记表是三个新增的统一契约对象);mimo v5 评审请求已更新待用户
转交。

## 1. 提交与 diff

| commit | 内容 |
|---|---|
| (本次单提交) | R5 底座:七模块 v5(audit/chemstate/hypothesis/legacy_reader/ path_context/profile/store)+ 10 个存量测试夹具修正 + 3 个新增 r5 测试文件 + 交付文档 + mimo v5 请求 + 实施证据 |

源码 diff(相对 e80f459,仅 src/ppv1):7 文件 +1393/−322;测试
diff:14 文件 +1501/−379(含 3 新文件 1559 行)。触碰面仅
`src/pathway_v43/pollutant/` 与 ppv1 测试。**legacy 路径零触碰**
(services/atom_tool.py 冻结执行器未改;镜像/证明链均为诊断侧
重推导;G01 全量 992 通过为证)。

## 2. R4 逐项处置表(P1 全部)

### 统一接口(先行落地,三线共用)

| 契约对象 | 定义 | 位置 |
|---|---|---|
| **证明记录 proof_record** | 诊断完整输入集(current/donor/alignment/expectation/result/edits),随 center_evidence 内嵌;audit 复跑同源 checker 重算轴结论与绑定 | audit.py `check_edit_against_donor`(生成)+ 证据门(消费) |
| **事件出现清单 event_appearance_manifest** | 首次提交把本事件断言的出现集合(state_id+appearance_hash 列表)持久进事件 payload;重放从账本校验,不依赖 caller 重复提供 dict | store.py 首提写入 + `_verify_event_appearance_manifest` |
| **CX 逐类登记表** | 移除类(坐标/标签/atomProp/映射号/SgD)/保留类(增强组/自由基/Sg)/未登记类 ⇒ 结构化拒绝 | chemstate.py `_identity_key`/`_guard_registered_cx_classes` |
| **载荷冻结** | requirement dict 顶层冻结映射+嵌套 value 递归冻结(hypothesis 存储侧);冻结 dict 封 `__ior__` | hypothesis.py `_freeze_requirement_dict`;path_context.py `_FrozenValueDict.__ior__` |

### 化学与证据线(R4-01/06/07/08)

| 项 | 修复(代码位置) | 测试 | 结果 | 边界 |
|---|---|---|---|---|
| **R4-01** 证明链可自造到 R6;绑定只覆盖底物与任一产物 | 证据门重写(audit.py ⑦ 分支):①**类型契约**——center_match/strict 须 bool\|None、declaration_mismatch 须 bool、bound_inputs 六项分型,违约 ⇒ AuditContractError(kind=center_evidence_type_violation;字符串'false'/0/{}[]不再绕过 is False/is None);②**内部重算**——audit 复跑 check_edit_against_donor(证明记录),自报轴/绑定字段须与复算一致,不一致 ⇒ 结构化拒绝(center_evidence_integrity_mismatch);③**无 proof_record ⇒ unknown**(center_evidence_proof_missing;两身份串/六自报字段不构成证明);④**产物集合覆盖**——复算的底物/产物身份对参与物做整分子或碎片两级映射(真实断裂分列产物绑定成功);未申报碎片/未覆盖产物+未覆盖共底物并存 ⇒ 部分覆盖 unknown(额外转化不借一产物达 all_verified);仅未覆盖产物(计量共产物)或仅未覆盖共底物(并入产物)⇒ 完全覆盖;⑤ 区域/strict 分轴保留 | r5_chem 11 例(genuine 控制保持/两串/六字段/四字段篡改各拒/四类型违约各拒/真实 strict False→R5v/碎片绑定/合并控制/额外转化部分覆盖) | 探针 genuine_bound_control 保持 expand;binding_only/six_fields → retain;四个 mutated_* → 结构化拒绝;'false'/0/{}/[] → 结构化拒绝;separate_participants → verified+expand(曾 unknown);lumped 控制不变;unchecked_additional → unknown(曾 R6) | **信任边界(诚实声明)**:proof_record 是自包含输入集——自洽构造的记录复跑即通过;证明链保证"该输入集上 checker 结论可复现",不证明"有人真实运行过该编辑"(运行事实归执行器通道;S3 完整模板另议)。区域 checker 命名不变(region_net_change);S3 完整供体模板未实现(按验收不要求) |
| **R4-06** 镜像漏新增 ID 与显式前置 | `_simulate_declared_edits` 重写:①**活 ID 表**——id→idx 映射从 before 表改为逐操作更新的活表(先增后引合法,与执行器 validate/execute 的列表时点语义一致);②**逐操作前置复核**——break_bond 键须存在/form_bond 键须不存在/**change_bond_order 的 from_order == 列表时点实际键级**(冻结执行器 bond_order_mismatch 同语义);③失败为结构化机读码 declared_precondition_violated:\*(不再笼统 not_simulable);净效应比较/add_atom 隐含 anchor/s→d→s→d 终态结算保持 | r5_chem 3 例(add-then-add/add-then-change 零失配+center True;wrong_from_order → bond_order_mismatch 失配+strict/center None) | 探针 real_add_then_add/change → 零失配+True(曾 not_simulable/None);interface_wrong_from_order → 失配+None(曾零失配+True);冻结执行器实测同拒(execution ok=False) | 不改冻结 executor(镜像重推导);sanitize 失败仍按原样比较 |
| **R4-07** 键 E/Z 与非四面体轴静默缺失 | ①`_bond_changes` 增 **bond_stereo_change**(映射原子对前后 GetStereo 不同;入实际变化集与声明对账签名——ops 语言无 E/Z ⇒ 执行图带未声明立体变化即失配);②`_stereo_config_delta` **分支顺序**——非四面体标签先判 unsupported(None),不再先命中"都不是四面体⇒保持";③**公开清单** stereo_comparison_unsupported_atoms(诊断字段)+ 中心内 atom 进 center_property_deltas(过滤条件加 unsupported);④**中心外 unsupported ⇒ center 不可判 True**;⑤身份不同而图轴空 ⇒ 理由码 net_change_only_in_stereo_representation,不再称"实际净变化为空";⑥`_joint_symmetric_image` 增**非四面体标签门**(useChirality 只覆盖四面体;返回 unsupported_stereo ⇒ unknown);⑦支持范围声明扩三类(全指定/无手性骨架/部分或全未指定——按所写表示) | r5_chem 7 例(ez_only 检出+不称空/off_center 不 True/真实逆控制身份相等/非四面体 delta None/身份异图轴空诚实理由/联合映射非四面体门/中心外 unsupported 阻断) | 探针 ez_only → stereo_change=1+失配+center None(曾 net_change_empty=False 却报"实际净变化为空");off_center_ez → center None(曾 True);ez_real_control → 身份相等+无伪立体变化;non_tetra same/different/unspecified → None+公开清单(曾 ""/静默);non_tetra_joint → unsupported+None(曾 True) | E/Z 按映射原子对几何入 diff(采纳 mimo 5.3(1) 前案);接口合成仅检出表示差异,不冒称执行器产该变化(真实逆控制证明执行器不产);平面手性等非四面体构型比较 unsupported(不猜) |
| **R4-08** 任意 DATA SGroup 仍改变身份 | `_identity_key`:**DATA SGroup(SgD)分子级剥离**——按 SubstanceGroup 类型 Clear+重加(值可含逗号,实测 SgD:0:note:a,b:::: 的字符串级令牌解析不可靠,故分子级);**SRU/聚合物(Sg:)保留**(化学事实);**未登记类守卫** `_guard_registered_cx_classes`——登记头 Sg/SgD/a/oN/&N/^N,未登记注解头/无冒号旗标块 ⇒ ChemicalStateError(kind=unregistered_cx_class;$_AV/molLnkNode 实测以 atomProp 承载、bond prop 实测不外写,均登记测试钉住) | r5_chem 4 例(DATA 三输入同 id/值含逗号边界/SRU 保留+往返/未登记类拒绝) | 探针 data_sgroup → 1 个 id(曾 3);atomic_value 控制 1(保持);SRU 与裸骨架不同 id+往返同 id | SgD 全类=非结构注记(登记决定;DATA 若未来承载化学事实须重登记);Sg 全类=化学事实;`r`/`H:`/`w:`/`LN:` 未登记 ⇒ 拒绝该表示 |

### 条件与科学前提线(R4-03/04/05)

| 项 | 修复 | 测试 | 结果 | 边界 |
|---|---|---|---|---|
| **R4-03** 单位未知仍 satisfied | CONDITION_KEY_UNITS 拆分:temperature_C **必须显式**规范单位(°C/C/celsius);**空单位 ⇒ 原来源单位未知 ⇒ unknown**(source_unit_unknown,不参与数值比较,不以注记升级 satisfied/conflict);pH 等无量纲键空单位合法;显式 K ⇒ unit_mismatch(既有) | r5_conditions 3 例(unknown+不 expand/显式 °C verified/无量纲不受影响) | 探针 source_unit_unknown_still_R6 → unknown+retain(曾 satisfied+R6) | 首版不做单位换算(既定);单位归一由事实来源/适配器承担 |
| **R4-04** 场景未入 live 筛选;空快照掩盖孤儿 | ①`_effective_scope`(scenario,phase) 二元组;`current_step_assessment`/`assess_candidate_conditions` 的 live 筛选用二元组——同阶段名不同场景的旧要求不被当前场景事实重评;②`derive_child_context` 冻结快照记录 **covered_requirement_signatures**(该次评估实际覆盖的要求集合);孤儿判定按**具体要求签名**匹配快照,不是"阶段存在即覆盖" | r5_conditions 5 例(同阶段名转场景与 p1 行为一致/旧边冲突保持/audit 全链不 defer/空快照孤儿 unknown(有无快照一致)/覆盖签名正控制) | 探针 new_same_local_phase → compatible/verified/expand(曾 conflict/defer);orphan(有/无空快照)→ unknown+retain(曾 R6);old_cross 两控制保持 | 跨阶段事实(空 phase)服务多边保持;快照签名含绑定字段(边级出处) |
| **R4-05** 分轴只累积;再生洗绿反驳 | `Dependency`:**轴状态从 resolution_log 重推导**(每轴取最近一次结论;__post_init__/resolve_dependency/序列化往返同源);**contradicted 撤销该轴**此前的 supported;总体 status=任一轴矛盾⇒contradicted/任一轴支持⇒supported;support_axes=**当前有效支持轴**;`dependency_states()` 披露 axis_status;恢复某轴须该轴新证据 | r5_conditions 5 例(反驳撤销+audit 不 R6/环诊断 unresolved_initial_supply 保持/恢复须该轴证据/正控制/axis_status 披露) | 探针 contradicted_initial_axis → status=contradicted、support_axes=[regeneration](曾 supported+初始轴保留)、circular unresolved 保持、admission retain(曾 R6) | 环不自动 reject/defer(§17.4);S3 调度不实施 |

### 存储与适配线(R4-09/10/11)

| 项 | 修复 | 测试 | 结果 | 边界 |
|---|---|---|---|---|
| **R4-09** writer 只验部分事实 | `_verify_state_payload_facts` 扩为完整契约:①有结构 state 重推 state_id/形式电荷/**CN/立体/同位素状态**须与提供值一致;smiles_isomeric 须为身份键规范形;original_structure_available 须 True;②fidelity 走 chemstate 同源校验(未知枚举/缺轴 ⇒ state_fidelity_contract_violated);③**全部原结构可得来源核 raw 与 strict 身份**(raw_input/source_product/executed_product 一致;同图异拼写 OCC 接受、跨分子 CCN/非法 raw 拒);④**CN-only 专用契约闭合**——按专用命名空间重算 id(cs(cn-only,cn))+未知事实契约(电荷 None/结构不可得/立体同位素 unknown/fidelity 模板),空串不自动当 CN-only | r5_storage 11 例(十类 put 变体 + submit raw 拒) | 探针十类 put:cn/isotope/stereo/fidelity×2/raw×3/cn_only 伪造全部结构化拒绝(曾全部接受);same_graph_alternate_raw 接受(控制);submit_raw_mismatch 拒(曾 created=True) | CN-only 不从 CN 猜结构(只验隔离身份与未知契约);v4 曾声明"source raw 不强制"已按 R4-09 验收加严(R4 交付 §7 预告的一行加严) |
| **R4-10** 无重复输入重放不能验出现集合;空结构逃逸 | ①**event_appearance_manifest**:首提把事务各 state 的 (state_id, appearance_hash) 持久进事件 payload;重放 `_verify_event_appearance_manifest` 从账本校验每项(行存在+内容哈希复算一致+不引用事件外状态);②重放侧 `_verify_stored_state_rows` 强化:载荷内 state_id==行键、CN/立体/同位素重推一致、**空结构行须满足 CN-only 专用契约**;③`_verify_stored_appearances` 既有期望集合核对保持 | r5_storage 5 例(删本事件出现 ⇒ manifest 损坏/三类 state 篡改各损坏/无 dict 幂等控制) | 探针 replay_missing_appearance_no_states → event_appearance_manifest_entry_missing(曾 created=False);replay_stored_state cn/inner_id/blank → 各损坏(曾成功);replay_normal 控制 created=False 幂等 | 损坏 ⇒ Ppv1LedgerCorrupt 保全,不静默补账(无自动修补策略保持);manifest 覆盖事务内 state(先存 state 由既有 no_appearance 检查覆盖存在性) |
| **R4-11** 旧导入只核 CN | `_substrate_structure_for_path` archive 分支增**关系核对**:①来源事件 E 的 parent_path_id == 本路径 parent_path_id;②E 的该 position 产物生成的子路径包含本路径;违反(即使 CN 同)⇒ CN-only+原因 substrate_source_event_relation_mismatch;`import_legacy_event` 增**记录间矛盾披露**:事件声明底物 vs 路径声明、产物行声明 CN vs raw 重算 ⇒ uncertainty 披露(保留可信 raw,不为服从错误 CN 丢可信 raw) | r5_storage 4 例(错关系降级+旧库字节不变/两类矛盾披露+raw 保留/合法多步控制) | 探针 same_cn_wrong_relation → CN-only+原因+uncertainty(曾接受错误手性产物为 source_product 无注记);event_vs_path/product_vs_raw → 披露+raw 保留(曾无披露);legal_multistep 控制不变 | 旧库只读(字节不变断言);合法两步/root-return/多位置/空指针降级控制保持(r3_storage 探针 29 行无意外异常) |

### 横切(R4-02 + §4)

| 项 | 修复 | 测试 | 结果 |
|---|---|---|---|
| **R4-02a** finite_rule_diagnostic 漏 hash | input_fingerprint 增 finite_rule_diagnostic(content_hash)与 proof_record/bound_inputs 哈希 | r5_chem 1 例 | 探针两次 input_hash 不同(曾同为 ain_62e14e27…) |
| **R4-02b** 冻结 dict `\|=` | `_FrozenValueDict.__ior__ = _immutable`(dict.\_\_ior\_\_ 就地合并不经 \_\_setitem\_\_) | r5_conditions 1 例 | 探针 frozen_ior → TypeError(曾静默改区间 defer→R6) |
| **R4-02c** hypothesis 前提可变 | requirements 存储侧冻结(顶层冻结映射+嵌套递归冻结);to_dict 输出普通可变副本 | r5_conditions 1 例 | 探针 live_nested_mutation → TypeError(曾改科学前提保留 id) |
| **R4-02d** put/submit/replay 不复算身份 | `_verify_hypothesis_id_rederivation`:put_hypothesis/submit_event(随事务提供)/重放(已存载荷 recompute)三入口同源复算 | r5_storage 3 例 | 探针 put/submit 变前提旧 ID → 结构化拒绝(曾成功);replay 篡改已存 → hypothesis_payload_id_corrupt(曾 created=False) |
| **§4 audit.scope 遮蔽** | 证据门局部 checker scope 改名 ev_scope;audit.scope/audit_id 用函数 scope 参数 | r5_chem 1 例 | 探针显式 'synthetic:review-scope' 如实返回(曾 region_net_change) |

## 3. §4 披露项处置

| 项 | 处置 |
|---|---|
| audit.scope 变量覆盖 | 修复(§2 横切表);checker scope 与 verified 同屏保持(理由码 center_evidence_verified:…(scope=region_net_change;basis=…),detail 亦带) |
| center_evidence scope/每轴状态结构化输出不截断 | detail 携带 center_match/strict_target_match/coverage_mode/covered/uncovered 清单;checker_scope 字段保留(§2) |
| CIP 标签不同但配置保持 | 既就地披露(cip_labels before/after + 奇偶法构型判定分开);mimo R4 建议的 cip_label_change_is_not_config_change 就地标注为**建议项**列入 v5 请求(未实现字段,不虚报) |
| plain≡ABS 表示层差异/重叠矛盾组/映射号 | v5 请求判据一:已登记分歧扩到混合并列 ABS 剥离;"组覆盖 ABS"矛盾输入解析规则登记;往返句补映射号例外(全部文本级+登记测试) |
| 原子属性/键立体声明语言范围/未指定四面体/未登记 CX | 判据五:原子属性与键级立体都不在 ops 对账(声明语言两者皆无)+ 键立体检出通道入变化集;联合映射支持范围扩三类;CX 登记表(§2 R4-08) |
| 不虚构 full_template/local_delta/equivalence 评分 | 保持 pending 声明(audit 模块 docstring/判据二 8) |
| per-product off 披露/空计划/跳阶段 | v4 已修控制全部保持(r4_chem/r4_storage 既有测试续绿;本轮回归未触碰) |

## 4. mimo R4 意见处置(按 §5 采纳边界)

| mimo 冻结前清单 # | 裁定 | 落实 |
|---|---|---|
| 1 键立体缺轴+理由码矛盾 | 接受(行为级) | R4-07:diff 入变化集+理由码拆开(§2) |
| 2 非四面体分支顺序+无公开通道 | 接受(行为级) | R4-07:顺序调整+公开清单(§2) |
| 3 逐字相同句缺映射号例外 | 接受(文本) | v5 请求判据一 3(§3) |
| 4 CX 拒绝表未登记类默认进身份 | 接受(登记表+测试) | R4-08:三类登记+守卫(§2) |
| 5 bound_inputs 六项只交叉核两项 | **超过原案,按 Codex R4-01 更强落实** | 内部重算:六项全部复算比对(自报≠复算 ⇒ 结构化拒绝);Codex 采信限度"补必填或收窄文本不够"由 proof_record 重算满足 |
| 6 单位 assumed_canonical 满足 | 接受(案 A 入口契约) | R4-03:空单位 ⇒ source_unit_unknown ⇒ unknown(§2) |
| 7 联合映射范围未声明部分/未指定 | 接受(文本) | v5 请求判据五 3 三类(§2 R4-07⑦) |
| 8 混合 ABS 归一第二处分歧+重叠解析 | 接受(文本) | v5 请求判据一 2(§3) |
| 9 cip_labels 空 delta 误导 | 接受(建议项) | v5 请求判据五 5 标注"建议项,未实现字段" |

**不照搬的 mimo 项**(Codex §5):$_AV 反例(本轮实测同 ID,不
构成已证缺陷——以实测为准);SGroup/SRU 全剥(不采纳盲剥);
"补必填字段即可"(改为内部重算,更强)。

## 5. 测试证据与命令

~~~bash
PY=~/miniconda3/envs/depending43/bin/python

# 全量 ppv1(13 文件,联合验证)
PYTHONDONTWRITEBYTECODE=1 $PY -B -m pytest -p no:cacheprovider -q \
  tests/test_ppv1_profile.py tests/test_ppv1_domain.py tests/test_ppv1_s2.py \
  tests/test_ppv1_rework.py tests/test_ppv1_r2_conditions.py \
  tests/test_ppv1_r2_storage.py tests/test_ppv1_r2_chem.py \
  tests/test_ppv1_r4_conditions.py tests/test_ppv1_r4_storage.py \
  tests/test_ppv1_r4_chem.py tests/test_ppv1_r5_chem.py \
  tests/test_ppv1_r5_conditions.py tests/test_ppv1_r5_storage.py
# => 381 passed in 2.70s,0 skipped

# G01 legacy 回归(全量 not slow)
PYTHONDONTWRITEBYTECODE=1 $PY -B -m pytest -p no:cacheprovider -q \
  -m "not slow" tests/
# => 992 passed, 16 deselected in 194.53s,0 failed
#    (611 legacy + 381 ppv1;legacy 行为零改动)

# R4 审核探针复跑(修复后;原样脚本复制到新临时目录)
tmp=$(mktemp -d /private/tmp/ppv1-r5-probes.XXXXXX)
cp docs/review_evidence/ppv1_r4_codex_2026-10-07/*.py "$tmp/"
cd "$tmp" && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<repo>/src $PY -B \
  chemistry_boundary_probe.py   # 17 行:新反例翻转+旧控制保持,exit 0
# r3_chemistry_probe(40 行旧控制)exit 0 无异常
# conditions_probe exit 0(结果 JSON:R4 反例全部翻转,见下)
# storage_boundary_probe / r3_storage_probe exit 0(结构化拒绝逐项捕获)
# admission_probe exit 1 于 genuine_evidence_mutated_edits_signature:
#   篡改证据现在结构化拒绝(AuditContractError)—— 观察脚本退出
#   非 0 正是修复行为;前 5 行(正控制/两串/六字段)均已输出翻转
# 复跑证据存 docs/review_evidence/ppv1_r5_impl_2026-10-07/
~~~

### 5.1 红验证(先红后绿)

- 基线:`git worktree add <tmp> e80f459`,复制 3 个 r5 测试文件,
  `PYTHONPATH=<worktree>/src` 运行 ⇒ **58 failed / 11 passed**;
- 11 个基线通过项全部为**正控制**(genuine 绑定控制/真实逆控制/
  SRU 保留/显式单位/无量纲键/旧边冲突保持/快照覆盖正控制/初始+
  再生正控制/同图异拼写/重放幂等/合法多步导入)——正控制在基线
  亦绿是预期(它们断言的是 v4 已正确的行为);
- v5(当前工作树)⇒ **69/69 全绿**;工作树已清理。

### 5.2 修改的既有测试与理由(仅被 R4 复审证伪语义/版本机械升位)

| 测试 | 改动 | 理由 |
|---|---|---|
| test_ppv1_profile 等版本断言(4 处)+ 模块内 donor-diagnostic/ pool-order 字符串(8 处) | -4 → -5 | 契约族升 v5(机械) |
| s2/r2_cond/r4_cond 温度事实夹具(9 处) | 补 `unit="C"` | R4-03 后温度事实须显式规范单位;旧夹具依赖"无单位照比"(复审否定行为);测试科学意图(阶段作用域/标签/最适/分支隔离)不变 |
| r4_cond 单位两测(assumed_canonical) | 断言改 source_unit_unknown+unknown(正例补显式单位) | 断言的是 R4-03 点名缺陷行为本身 |
| r2_chem center_evidence 手工字典 3 例 | 改用真实诊断(strict=None 用期望缺失构造;center=False 用供体中心偏移构造) | v5 证据须带 proof_record 且自报=复算;手写字段拼接不再是可采信输入(缺陷路径) |
| r2_chem cross_reaction/name_only 理由码 | binding_mismatch:product → undeclared_product_fragment;binding_missing → proof_missing | R4-01 覆盖模型细化根因;unknown+不 R6 结论不变 |
| r4_chem joint 消息断言 | enhanced_stereo_unsupported → stereo_unsupported | 消息覆盖增强组+非四面体两类 |
| r4_chem input_hash ② | 改写 center_match 改为真实 center=False 诊断 | v4 的"改字段换 hash"在 v5 是篡改(结构化拒绝);用真实不同结论证 hash 区分 |
| r4_storage raw kind | raw_input_identity_mismatch → raw_identity_mismatch | 全来源统一核 raw(§2 R4-09) |

### 5.3 复审探针前后对照(关键行)

| 探针行 | v4(R4 复审记录) | v5(本轮回跑) |
|---|---|---|
| admission genuine_bound_control | verified→R6(正控制) | verified→expand(保持) |
| admission binding_only/six_fields | verified→R6 | unknown→retain |
| admission genuine_evidence_mutated_×4 | R6(仅 hash 变) | AuditContractError(integrity) |
| admission strict_axis_type_str/int/dict/list | R6 | AuditContractError(type) |
| admission real_fragment_separate | unknown/retain | verified→expand |
| admission unchecked_additional | R6 | unknown→retain(partial) |
| admission finite_rule_hash | 两次同 hash | 不同 hash |
| admission audit_scope_label | region_net_change | synthetic:review-scope |
| chem real_add_then_add/change | not_simulable,None | 零失配,True |
| chem interface_wrong_from_order | 零失配,True | bond_order_mismatch 失配,None |
| chem ez_only | 报"实际净变化为空" | stereo_change+失配,None |
| chem off_center_ez | center=True,extra 空 | center=None |
| chem non_tetra same/different | ""/静默 | None+公开清单 |
| chem non_tetra_joint | center=True | unsupported,None |
| chem data_sgroup | 3 个 id | 1 个 id |
| conditions source_unit | satisfied+R6 | unknown+retain |
| conditions same_local_phase | conflict→defer | compatible→expand |
| conditions orphan(empty snapshot) | verified→R6 | unknown→retain(有无快照一致) |
| conditions axis_contradiction | supported→R6 | contradicted→retain |
| conditions frozen_ior/hyp_mutation | 静默改 | TypeError |
| storage put 十类 | 全部接受 | 按类结构化拒绝(OCC 控制接受) |
| storage replay_missing_appearance | created=False | manifest 损坏 |
| storage replay_stored_state×3 | 成功 | 各损坏 |
| storage hyp 变前提 put/submit/replay | 成功/created=False | 拒绝/损坏 |
| legacy same_cn_wrong_relation | 接受错误手性产物 | CN-only+原因 |
| legacy 两类矛盾 | 无披露 | 披露+raw 保留 |

## 6. schema/语义版本与兼容策略

| 契约 | v4 → v5 | 兼容声明 |
|---|---|---|
| profile/chemstate/hypothesis/event/store/context/dependency/ provenance/substrate_profile/audit/admission_policy/donor_diagnostic/pool_audit/pool_order/input_preview/condition_assessment | -4 → -5 | profile 从未放行执行流(入口 fail-closed),无已发布 run/产物;升版即生效,无迁移;v4 文件按未知版本拒绝(既有门) |
| gate_mapper | -3(不动) | 本轮未触碰 |
| run identity | v43-identity-2(不动) | 未触碰 run_identity.py |
| search_limits | -2-proposed(不动) | proposed 草案,S3 落地 |

语义变化要点(v5):身份键含 CX 登记表(SgD 剥离/Sg 保留/未登记
拒;键值全变,无历史数据);事件 payload 增 event_appearance_
manifest(重放校验依据;表结构未变,仅 payload 字段);states
语义事实扩展(CN/立体/同位素入 writer 复核);context 快照增
covered_requirement_signatures(旧载荷无签名字段 ⇒ 覆盖判定
保守 unknown,不误覆盖);dependency 轴状态从 log 重推导(旧载荷
仅 support_axis 时按唯一轴补齐);hypothesis 载荷格式不变(冻结
仅存储侧);audit input_hash 域扩展(同输入幂等保持);中心证据
须带 proof_record(v4 形状证据自动降 unknown,不授信)。

legacy_v43:零改动承诺继续成立——全部改动在 pollutant/ 包与
ppv1 测试;冻结执行器 services/atom_tool.py 未改(镜像/证明链均
为诊断侧重推导;wrong_from_order 用真实执行器同拒为证)。

## 7. 剩余未知与边界(不宣称冻结)

1. 化学判据 v5 **未冻结**:mimo v5 评审请求已更新(§8),待用户
   转交;冻结以 review + mimo 回应与程序证据互证为准。
2. 契约 v5 未冻结;S3 入口 fail-closed 未解除(runner 未触碰)。
3. **证明链信任边界**(诚实声明,亦列入 v5 请求请评审):
   proof_record 保证"输入集上 checker 结论可复现+绑定一致",
   不证明"该编辑被真实执行过"——完全自洽的虚拟执行记录可通过
   重算(其证明的命题本身为真);运行事实归执行器通道(真实
   AtomTool 调用与证据同源),S3 接线时供体模板 checker 另议。
4. **S3 排期项(不冒充已实现)**:完整供体变换模板 checker
   (full_template scope)独立注册;执行流接 center_evidence;
   local_delta/edge_kind/scoring_key;互变/质子化等价类;被拒
   共同产物的展开计划消费。
5. 已知缺口(登记):增强组联合映射范围(unsupported);平面
   手性等非四面体构型比较(unsupported+公开);条件单位不换算
   (入口契约);matrix 同义/包含须注册;manifest 覆盖事务内
   state(先存 state 仅核存在性);fidelity 的 radical 保真轴;
   cip_label_change_is_not_config_change 就地标注(mimo 建议,
   未实现)。
6. 科学验收整体 pending(S5);381 项工程测试不构成任何路径
   科学性能声明;合成计量闭合不证明机制/生物可行性/酶选择性
   (探针全部如实标注来源)。

## 8. mimo v5 化学评审请求

已更新 `docs/mimo_ppv1_chem_review_request.md` 为 v5 文本(判据
一 CX 逐类登记表+映射号例外+组覆盖 ABS;判据三证明链内部重算+
产物集合覆盖+信任边界声明;判据四单位未知 unknown+快照签名覆盖
+分轴撤销;判据五非四面体判据+三类支持范围+镜像活 ID/前置+键
立体+理由码拆分)。自包含、规则级、无金标;**由用户转交**,回
复原文落盘 docs/;不自行外发。

## 9. 与原规格的冲突清单

无新增实质冲突。五处"规格未逐字规定、按 R4 复审验收收紧/具体化":
- §8 中心证据具体化为证明链+内部重算+产物集合覆盖(R4-01 验收);
- §5.1 身份键具体化为 CX 逐类登记表(R4-08/mimo R4 1.1);
- §6 快照覆盖具体化为要求签名级(R4-04 验收);
- §6 依赖分轴具体化为按轴当前有效状态+撤销语义(R4-05 验收);
- §5.3/§9.2 事件持久格式具体化为 appearance manifest(R4-10 验收)。
