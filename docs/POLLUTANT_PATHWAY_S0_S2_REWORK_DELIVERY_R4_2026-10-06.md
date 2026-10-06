# pollutant_pathway_v1 S0–S2 第四轮回修交付书(R4)

- 日期:2026-10-06
- 回修依据:`docs/POLLUTANT_PATHWAY_S0_S2_CODEX_REVIEW_R3_2026-10-06.md`
  (R3-01～R3-12 + §4 边界项 + §5 mimo 采纳边界;§8 回修提示词)
- 回修基线:af14fb2(=审核 HEAD;4 个附件探针在本轮开始时于临时目录
  复跑,与审核输出一致——chemistry/admission/conditions 逐字节相同,
  storage 仅时间戳/临时路径差)
- 回修范围:**仅 S0–S2 底座回修**;S3 入口继续 fail-closed(未解除);
  契约与化学判据**不宣称冻结**(待本会话 review + mimo 第四轮)
- 状态:三线(条件/存储子代理 + 化学主会话)全部落地并合并;全部
  ppv1 测试 312 通过;legacy 默认行为零改动(G01 全量 923 通过)

## 0. 一句话结论

R3-01～R3-12 十二项 P1 与 §4 全部处置(实现+回归);复审探针的
全部已复现反例已翻转(逐案对照见 §5);每条线先红后绿(化学线
8/8 行为级红验证于基线 af14fb2;条件线 30 例/存储线 31 例先红后绿);
**复审点名的过强断言(test_ppv1_r2_chem.py:361 乙醛诊断用于乙酸
假设)已废除并改为合法绑定正例+跨反应负例**;契约全族升 v4; mimo
v4 评审请求已更新待用户转交。

## 1. 提交与 diff

| commit | 内容 |
|---|---|
| 3652a8d | R4 底座:契约版本 -3 → -4(唯一触碰 profile.py 的提交;两线从其分叉) |
| c50c73e | R4 条件线:R3-06/07/08 + R3-12 + 单位/支持轴/matrix(子代理 r4-cond) |
| f114560 | R4 存储线:R3-09/10/11 + 重放内容校验/空计划/跳阶段留痕(子代理 r4-store) |
| 27663ce | 合并 r4-store |
| 7b5b4db | 合并收尾:存储线测试夹具改用真实条件键(条件线键校验接线) |
| 8fd0239 | R4 化学线:R3-01/02/03/04/05 + audit 接线 06/07/08 + §4 off 披露(主会话) |

总 diff(af14fb2..8fd0239):17 文件 +4837/−518。触碰面仅
`src/pathway_v43/pollutant/`(path_context/hypothesis/store/
legacy_reader/pool_audit/audit/chemstate)+ 10 个 ppv1 测试文件
(3 新增 r4_*)。**legacy 路径零触碰**(services/atom_tool.py 冻结
未改——供体净效应对账以镜像重推导实现,不改执行器)。

## 2. R3 逐项处置表(P1 全部)

### 化学与证据线(主会话实施;审核 §6 线 1:R3-01～05)

| 项 | 修复(代码位置) | 测试 | 结果 | 未完成边界 |
|---|---|---|---|---|
| **R3-01** 证据绑定本反应/各轴/scope | `audit.py`:①证据契约扩展——`center_evidence` 携带 `checker_scope` ∈ CENTER_CHECKER_SCOPES(region_net_change)、`strict_target_match` 轴、`bound_inputs`(底物身份/产物身份/edits 签名/执行指纹/供体中心/对齐引用);②**绑定核验**:底物身份 == 被审假设 primary substrate state 的公开表示;产物身份 == 某产物参与物 state——跨反应复用/改产物/注册名-only True ⇒ unknown(binding_mismatch/binding_missing),不得认证;③**strict 轴消费**:False ⇒ violated(center_evidence_strict_target_mismatch→R5v);None ⇒ unknown(阻断 all_verified);区域 True 与 strict False 在 detail 分列保留;④`DonorConsistencyDiagnostic.center_evidence` 内嵌完整绑定载荷,助手透传(v3 丢弃 strict/绑定的缺陷关闭) | test_ppv1_r4_chem 5 例 + r2_chem 2 例(跨反应负例/名字-only/scope 未登记/strict unknown/绑定正例);**复审点名的 :361 过强断言废除**——正例改用绑定一致的 CCO→CC=O+[H][H] 假设,跨反应另钉负例 | 探针 acetic_acid/unrelated_propene/registered_name_only 全部 retain(曾 expand/R6);admission_binding_probe exit 0 且三反例翻转 | 中心检查的其他注册 checker(完整供体模板 full_template)预留 S3 独立注册;绑定核验依赖 states 提供(缺 state 时 binding_unverifiable,走 R1b/缺状态路径) |
| **R3-02** 联合映射手性盲 | `audit.py _joint_symmetric_image`:**useChirality=True**(保手性自同构);底物带增强立体组 ⇒ "unsupported_stereo" ⇒ unknown(声明支持范围:绝对四面体/无手性骨架;不冒称全范围);joint_mapping 记录 chirality_aware | r4_chem 3 例(meso 换位 False+两端产物异种断言/真 C2 (2S,4S)-戊二醇互换保持 symmetric_equivalent/增强组 unknown)+ r2_chem 控制续绿 | 探针 stereo_blind_joint_false_positive:center=True→**False**;环己烷/丁烷控制不变 | 增强立体组的联合映射范围(手性感知对组的语义)未覆盖——unknown 而非猜测 |
| **R3-03** CIP 标签被当构型变化 | `audit.py _stereo_config_delta`:**映射配体下的奇偶构型比较**(标签/邻居序无关:邻居集合相同 ⇒ 置换奇偶×手性标签 ⇒ 构型保持/反转;配体集改变 ⇒ None 交键 diff 承载);`_cip_labels` 用 **rdCIPLabeler**(准确标签仅入披露 cip_labels,不作变化判据);非四面体手性 ⇒ stereo_comparison_unsupported 不入变化集 | r4_chem 3 例(远端构型保持不误报/优先级重排不误报(复审新反例)/真实反转可见+标签披露) | 探针 real_priority_swap / real_bond_priority_swap:center False→**True**(两组真实反例翻转) | 平面手性等非四面体 unsupported;标签披露不等于构型判定(口径在 docstring/判据 v4 文本) |
| **R3-04** CX 身份混入绘图注释/混合 ABS 分裂 | `chemstate.py _identity_key`:**化学 CX 事实子集**——生成前移除非化学元数据(坐标 conformer/原子标签 atomLabel/任意 atomProp);保留增强立体组、自由基层、基串同位素/电荷/立体;`_strip_abs_tokens` **令牌级** ABS 剥离(注解头 token+其后裸数字延续的语法:混合并列 `a:1,&1:3`≡`&1:3`、`a:1,o1:3`≡`o1:3`、`^1:0,a:1`≡`^1:0`;不逗号盲拆、不剥全部 CX) | r4_chem 3 例(CO 五输入同键/混合 ABS 三组/radical 保留+逐字相同例外句) | 探针 cx_nonstructural_annotation_identity:5 输入同 state_id;identity_pair 混合 ABS actual_equal=true;roundtrip 全 true | RegistrationHash 一致性声明**限定**子集(文字,§4 行 8);plain≡ABS 为本仓归一设计(已登记分歧) |
| **R3-05** 声明对账未守执行器协议/有序净效应 | `audit.py _simulate_declared_edits`:**镜像执行器路径**的净效应模拟——编辑前 Kekulize(clearAromaticFlags)(执行器 atom_tool.py:417 同步)、有序应用 4 操作、add_atom 隐含 anchor 单键、终态 SanitizeMol(失败按原样比较);`_declaration_accounting` 比较**净效应**(声明终态键变化 vs 实际 diff;中间态不逐条相等;s→d→s→d 终态=double);原子属性不在 ops 对账(声明语言无对应操作);`center_property_deltas` **披露中心原子属性 Δ**(电荷/ΔH/构型/准确 CIP——E-iii 全绿零披露关闭) | r4_chem 4 例(add_atom 零失配/序列净效应零失配/电荷披露/立体翻转披露+strict 消费) | 探针 real_add_atom_anchor/real_sequence_final_net_change:失配→**零失配+center True**;center_property_inversion:披露存在 | 完整供体模板供体侧预期对比排期 S3(区域 checker 命名诚实:region_net_change) |

### 条件与科学前提线(r4-cond 分支 c50c73e;审核 §6 线 2:R3-06/07/08/12)

| 项 | 修复 | 测试 | 结果 | 边界 |
|---|---|---|---|---|
| **R3-06** 路线快照未被 audit 消费/外来绑定 | `path_context.assess_candidate_conditions`(新公共 API):旧边取 phase_history 记录值合取(**不重评**)+本候选新增要求在当前 scenario+phase 评估;detail 带 route_edge_fits/current_step/route 双层并列;`audit.py` 条件检查**改调本函数**(⑨);`hypothesis._reject_foreign_requirement_bindings`:预填外来 introduced_* ⇒ HypothesisContractError(kind=foreign_requirement_binding) | r4_conditions 7 例 + r4_chem 2 例(**audit→admission 全链**:行 1 conflict→defer/R3、行 2 compatible 不冤杀) | 探针 scenario_switch 两行:expand/defer → **conflict/compatible**(audit 级);外来绑定 verified/R6 → 结构化拒绝 | 绑定无快照覆盖旧阶段的要求显式 unknown(保守);孤儿绑定 fail-closed |
| **R3-07** 继承依赖被审计遗漏 | `audit.py`(⑩):**并集消费** hypothesis.dependency_refs ∪ context.dependency_states();None=从 context 推导、[]=显式断言(语义不混同);context 侧权威状态(supported 才 resolved);缺解析 ≠ 没有依赖(dependency_resolution_not_provided);context-only unresolved ⇒ unknown(含 detail.context_only) | r4_chem 2 例 + r4_conditions 2 例 | 探针 context 依赖:verified/no_unresolved → **unknown**;补传才解决的绕过关闭 | 下游命中不自动解决上游(保持) |
| **R3-08** input_hash 漏真实输入/载荷可变/排序半套 | `audit.py`:input_hash = hypothesis 载荷 + **state 完整 to_dict**(fidelity/appearance 差异入 hash)+ **context 全科学载荷 content_hash(context.to_dict())**(嵌套修改换 hash,即使 context_id 不变)+ audit_scope + checker 版本 + **center_evidence 规范化摘要(含各轴结论+绑定 hash)** + **unresolved_dependency_ids**;`path_context`:嵌套集合构造期深拷贝转 tuple/frozen(就地修改 TypeError);`hypothesis`:requirements 深拷贝+canonical_hypothesis_payload 排序归一(to_dict=id 存储=同 payload)+recompute_hypothesis_id;**构造校验**(Requirement 对象⇒结构化错误非裸 TypeError;level/value 必填/枚举/区间方向/键名);`validate_context_object`(audit 入口版本门) | r4_chem 3 例 + r4_conditions 10 例 | 探针 frozen_source_refs/alias/order-invariant:修改被拒/值不变/第二次 put 幂等;同输入幂等、五类输入变化各不同 hash | 结构指纹与完整输入 hash 并存(前者不替代后者) |
| **R3-12** matrix 字符串不等硬冲突 | `path_context`:无语义关系字符串不等 ⇒ **unknown(matrix_value_unresolved)**;同词 satisfied;氧枚举/实体行为不变 | r4_conditions 2 例 | 探针 matrix:conflict → **unknown** | 同义/包含关系须注册语义才可升级(不建环境本体) |

### 存储与适配线(r4-store 分支 f114560;审核 §6 线 3:R3-09/10/11)

| 项 | 修复 | 测试 | 结果 | 边界 |
|---|---|---|---|---|
| **R3-09** writer 可把另一结构挂合法 state_id | `store.py _verify_state_payload_facts`:put_state/submit 事务内全部 state **重推导**(解析 smiles_isomeric→同源重算 state_id/formal_charge;不可解析/身份错/电荷错 ⇒ Ppv1StateContractError 零写入);CN-only 不重推导(保留未知);raw_input 的 raw 须解析到同一身份;submit:参与物系数/entry 指纹/event_id(run/parent/hyp/context/语义)重推导复核 | r4_storage 8 例 | 探针 forged_state_id/formal_charge/isomeric → 结构化拒绝零写入;submit_forged_state/zero_coefficient → 拒绝 | source_product/executed_product 的 raw 不强制(同图异拼写通道,R2-08 控制);put_forged_raw_structure(source_product+CCN raw)段按约定保持 accepted——若审核要求 archive 跨分子 raw 也拒,一行加严(见 §7) |
| **R3-10** 重放只查存在 | `store.py`:重放分支**从已存行复算**——event 语义 hash 重算/payload↔hypothesis 一致/身份列↔event_id/schema 门/已存 state 重解析重算/**本事件全部期望 appearance**(逐 state 核对 source_refs 指向本事件+内容 hash 复算);不依赖调用者重复提供 dict;损坏 ⇒ Ppv1LedgerCorrupt(kind 分类)保全不补写;**导入不先 put 绕过**(import_legacy_run 重放路径先校验已存记录,缺/损 ⇒ 结构化错误不补账;仅首次导入 put+submit) | r4_storage 11 例 | 探针 9 类损坏(appearance 改 raw/缺本事件 appearance/event payload 清空/未来 schema/身份列错/hypothesis 内 ID/schema/state 行/charge)+run-context 保留 event_id 全部 Ppv1LedgerCorrupt/Ppv1SubmitContractError;legacy_import_replay_repairs_missing → 不补账 | 无自动修补(保持已声明策略);一般 submit 首次提交不强制 provenance 落账 |
| **R3-11** 旧导入信非空错引用/根矛盾/单事件绕版本门 | `legacy_reader`:archive 指针核对(指针行结构重算 CN+行声明+子底物声明三一致才用;矛盾 ⇒ CN-only+substrate_archive_identity_mismatch);root_smiles 重算旧身份 ≠ 声明 ⇒ CN-only+root_smiles_identity_mismatch;`_gate_legacy_store_version` 覆盖**所有公开导入入口**(import_legacy_event 也执行 store schema+run identity 版本门) | r4_storage 7 例 | 探针四段:错指针/根矛盾 → CN-only+原因;future-legacy-store/run-identity → 单事件入口也拒;旧库字节不变 | 合法旧无新增字段格式兼容;文件缺失仍 CN-only 降级(F09 家族) |

## 3. §4 边界项处置

| 项 | 处置 | 测试 |
|---|---|---|
| 来源单位未知 | 要求值恒为键规范单位(构造器无 unit 字段,文档钉死);无单位事实 ⇒ 仍按规范单位比较 + 评估 detail 带 `unit_basis: "assumed_canonical"`(区分已归一/来源单位未知;显式错单位仍 unknown) | r4_conditions 2 例 |
| 支持轴覆盖 | resolve_dependency 按轴集合累积(仅 supported 轴入集合):initial_supply 后 regeneration 不覆盖,启动未知不回退 | r4_conditions 2 例 |
| per-product off 披露 | off ⇒ 决策可为 expand,但被拒产物以 **R2p_disclosure** 留痕(未消费范围披露);on 默认修复保持 | r4_chem 1 例(含 on/off 对照) |
| 空展开计划 | 有产物而 entries=[] ⇒ 拒;或显式 `plan_status:"incomplete"`+原因(只补载荷契约,不实施 S3 队列) | r4_storage 2 例 |
| 跳阶段留痕 | 同 hash 跳阶段也须 transition_reason(哈希链断裂检查保留在前) | r4_storage 1 例(三向) |
| 中心属性披露 | center_property_deltas(R3-05);区域包含关系与完整操作对账分别命名(region_net_change scope) | r4_chem 2 例 |
| AND/OR 文字 | v4 请求按 RDKit Book 改正:**AND=两组分(该手性分子及其镜像)都在的混合物;OR=二者未知何者的单一未定;ABS=单一确定**;r2_chem 测试 docstring 同步改正 | 文本+docstring |
| identity 说明 | RegistrationHash 一致性限定到整组翻转/部分反转/排列/kekulé/映射号子集;plain≡ABS 为已登记分歧;无组**且无自由基层**逐字相同+自由基例外句 | v4 请求文本 |

## 4. mimo R3 意见处置(按 §5 采纳边界)

| mimo 建议 | 裁定 | 落实 |
|---|---|---|
| 混合 ABS 令牌级剥离 | 接受 | R3-04(不用逗号盲拆) |
| CIP 腿换 rdCIPLabeler | **修正**:换准确标签器不够(新反例证明准确 R/S 也会配体优先级翻转) | 奇偶构型比较+准确标签仅披露(R3-03) |
| 联合映射手性门 useChirality | 接受+补强 | useChirality=True+增强组 unsupported+产物同一性由 strict 轴前置(R3-02) |
| strict 入证据并被消费 | 接受 | strict 轴进证据+audit 消费(R3-01) |
| center_property_deltas 披露字段 | 接受 | 新字段(R3-05) |
| input_hash 补依赖/证据 | 接受(补代码不改名) | 五类实际输入全入 hash(R3-08) |
| R2b 构造期 HypothesisContractError | 接受 | requirements 校验+结构化错误(R3-08) |
| matrix 未定案 | 接受(unknown 分支) | R3-12 |
| "换 rdCIPLabeler 或单开 useChirality 即可宣称解决" | **不采纳** | 两处均声明支持范围(绝对四面体;组 unsupported) |
| AND/OR 语义句对调 | 接受(文字) | v4 请求改正 |
| R2p off 披露/RegistrationHash 限定/自由基例外 | 接受(文字/字段) | §3 |

## 5. 测试证据与命令

~~~bash
# 全量 ppv1(联合验证,10 文件)
PYTHONDONTWRITEBYTECODE=1 ~/miniconda3/envs/depending43/bin/python -m pytest \
  tests/test_ppv1_profile.py tests/test_ppv1_domain.py tests/test_ppv1_s2.py \
  tests/test_ppv1_rework.py tests/test_ppv1_r2_conditions.py \
  tests/test_ppv1_r2_storage.py tests/test_ppv1_r2_chem.py \
  tests/test_ppv1_r4_conditions.py tests/test_ppv1_r4_storage.py \
  tests/test_ppv1_r4_chem.py -q -p no:cacheprovider
# => 312 passed(profile 23/domain 31/s2 60/rework 16/r2-cond 31/
#    r2-store 26/r2-chem 41/r4-cond 30/r4-store 31/r4-chem 23)

# G01 legacy 回归(全量 not slow)
# => 923 passed, 16 deselected in 193.28s(611 legacy + 312 ppv1;
#    0 failed 0 skipped)

# 复审探针复跑(修复后;原样脚本复制到临时目录)
after=$(mktemp -d /private/tmp/ppv1-r4-after.XXXXXX)
cp docs/review_evidence/ppv1_r3_codex_2026-10-06/*.py "$after/"
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src <python> -B \
  "$after/admission_binding_probe.py"
# acetic_acid/unrelated_propene/registered_name_only → retain(R5,
#   binding mismatch;曾 expand/R6);gate off → R2p_disclosure 留痕
# chemistry_probe:stereo_blind_joint → False;real_priority_swap
#   (两例)→ center True;add_atom/sequence → 零失配;
#   cx_nonstructural 5 输入同 id;identity_pair 混合 ABS 归一;
#   roundtrip 全 true;center_property_inversion 披露存在
# conditions_probe:exit 1(外来绑定反例处 HypothesisContractError
#   fail-closed = 修复后行为;分段对照见条件线报告)
# storage_probe:分段驱动对照见存储线报告(29 段逐案翻转)
~~~

### 5.1 红验证(先红后绿)

- 基线探针复跑(本轮开始):4 探针与审核输出一致(R3 反例全复现);
- 化学线行为级红:`red4_behavior_probe.py`(证据存
  docs/review_evidence/ppv1_r4_impl_2026-10-06/)对基线 af14fb2
  断言 v4 预期,**8/8 失败**(非化学 CX 同键/混合 ABS/手性盲/
  优先级重排/add_atom/序列净效应/跨反应复用/注册名-only);
- 条件线:30 例先红(实现前 28 失败+导入失败);存储线:31 例
  先红(26 失败+5 正控制);
- 修复后:312 全绿。

### 5.2 修改的既有测试与理由(仅被复审证伪语义)

| 测试 | 改动 | 理由 |
|---|---|---|
| test_ppv1_r2_chem::…reaches_verified(:361) | **复审点名废除**:正例改绑定一致假设(CCO→CC=O+[H][H]);新增跨反应/名字-only 负例 | 过强断言(乙醛诊断→乙酸假设 expand) |
| test_r2_01_center_mismatch_is_violated_r5v | 证据补 bound_inputs/checker_scope | 绑定核验接线(无绑定 ⇒ unknown 到不了 violated) |
| r2_chem `_all_verified_audit`/test_admission_all_verified_expand | 换绑定一致假设 | 同上(合法 expand 路径须证据绑定本反应) |
| test_f06(s2) | reason_code 断言改 startswith | 理由码加语义括注 |
| r2_chem 断言码 S_O_3→S_O_1、r2_cond 分支隔离 2 处、r2_storage/rework 形式电荷 2 处 | 各线报告列明 | 夹具修正/更早更强的拒绝路径/嵌套冻结 |
| r4_storage 2 处假条件键("oxygen"/"ph") | 改真实键(oxygen_regime/pH) | 条件线键校验(合并接线) |

skip 说明:本轮**无新增 skip**;r4_chem 1 处防御性 skip 已改为
真实断言(C2 对称用断键替代价态非法编辑)。全仓 slow 慢测照旧
deselected 不触发。

## 6. schema/语义版本与兼容策略

| 契约 | v3 → v4 | 兼容声明 |
|---|---|---|
| profile/chemstate/hypothesis/event/store/context/dependency/provenance/substrate_profile/audit/admission/donor_diagnostic/pool_*/input_preview/condition_assessment | -3 → -4 | profile 从未放行执行流(入口 fail-closed),无已发布 run/产物;升版即生效,无迁移 |
| gate_mapper | -2 → -3 | 逐产物 verdict 被消费(语义升版) |
| run identity | v43-identity-2(不动) | 本轮未触碰 run_identity.py |
| search_limits | -2-proposed(不动) | proposed 草案,S3 落地 |

语义变化要点(v4):身份键为 CX 事实子集(坐标/标签/props 不入;
键值全变,无历史数据);context_id/依赖载荷含依赖对象与
support_axes(id 数值变化);hypothesis 载含 origin_group_key+
排序归一 requirements;store 重放校验已存内容(损坏结构化拒绝);
audit input_hash 覆盖完整科学输入(同 id 不同前提必不同 hash);
中心证据须绑定(v3 形状证据自动降 unknown,不授信)。

legacy_v43:零改动承诺继续成立——全部改动在 pollutant/ 包与
ppv1 测试;冻结执行器 services/atom_tool.py 未改(净效应对账为
镜像重推导)。

## 7. 剩余未知与边界(不宣称冻结)

1. 化学判据 v4 **未冻结**:mimo v4 评审请求已更新(§8),待用户
   转交;冻结以 review + mimo 回应与程序证据互证为准。
2. 契约 v4 未冻结;S3 入口 fail-closed 未解除。
3. **S3 排期项(不冒充已实现)**:完整供体变换模板 checker
   (full_template scope)独立注册;执行流接 center_evidence;
   local_delta/edge_kind/scoring_key 标记;互变/质子化等价类;
   被拒共同产物的展开计划消费(存储线已校验范围)。
4. 已知缺口(登记):增强立体组的联合映射范围(unsupported);
   非四面体手性比较;条件单位不换算(assumed_canonical 注记);
   matrix 同义/包含需注册;source_product raw 跨分子不强制
   (一行可加严,见 R3-09 边界);fidelity 的 radical 保真轴。
5. 科学验收整体 pending(S5);312 项工程测试不构成任何路径
   科学性能声明。

## 8. mimo v4 化学评审请求

已更新 `docs/mimo_ppv1_chem_review_request.md` 为 v4 文本(判据
一~五按本轮实际实现修订:CX 事实子集身份+AND/OR 语义按 RDKit
Book 改正+RegistrationHash 限定;证据绑定契约与 region scope;
奇偶构型比较;净效应对账;路线快照消费与依赖并集;完整输入
hash;单位/matrix/支持轴)。自包含、规则级、无金标;**由用户
转交**,回复原文落盘 docs/。

## 9. 与原规格的冲突清单

无新增实质冲突。四处"规格未逐字规定、按复审验收收紧/具体化":
- §5.1 身份键具体化为化学 CX 事实子集(R3-04 验收);
- §8 中心证据具体化为绑定契约+注册 scope(R3-01 验收);
- §8 声明–执行对账具体化为执行器镜像净效应(R3-05 验收);
- §6 audit 消费具体化为候选级评估+依赖并集(R3-06/07 验收)。
