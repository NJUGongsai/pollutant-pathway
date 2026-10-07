# pollutant_pathway_v1 S0–S2 第六轮回修交付书(R6)

- 日期:2026-10-07
- 回修依据:`docs/POLLUTANT_PATHWAY_S0_S2_CODEX_REVIEW_R5_2026-10-07.md`
  (R5-01～R5-08 八组 P1 + §4 两项 P2 + §5 mimo 采纳边界 + §6 R6 架构要求)
- 回修基线:293bc627f57b1f778aa433750f7f61d00b4a9d18(=审核锁定 HEAD;
  六份必读文档全部读取;工作区原有三个用户未跟踪审核文件原样保留——
  R5 审查报告、mimo R5 回应、R5 审核证据目录,未回退未覆盖未写入)
- 回修范围:**仅 S0–S2 底座回修**;S3 入口继续 fail-closed(未解除);
  契约与化学判据**不宣称冻结**(待 review + mimo 第六轮)
- 状态:化学证据/条件前提/存储适配三线在统一载荷与验证边界下落地;
  全部 ppv1 测试 **451 通过**(381 存量 + 70 新增,0 skip);新增
  回归在基线 293bc62 **红 44/70**(38 真实反例翻转 + 6 个仅因 v6
  新披露键红而核心语义基线已绿 + 26 正控制基线亦绿);G01 legacy
  回归全量结果见 §5;三处被本轮证伪的旧测试语义修正见 §5.2
- 探针纪律:R5 审核探针全部复制到新临时目录复跑(证据
  `docs/review_evidence/ppv1_r6_impl_2026-10-07/`);未在审核方
  证据目录写任何 SQLite/覆盖任何日志

## 0. 一句话结论

R5-01～R5-08 八组 P1 与 §4 两项 P2 全部处置(实现+回归+探针翻转);
复审 8 组反例逐项翻转、正控制保持(对照见 §5.3);契约全族升 v6;
**先统一载荷/验证边界,再三线并行落地**(覆盖证明的注册计量补全
规则、CX 输入侧类级登记表、快照同源派生+内容身份重算、appearance
清单全量覆盖绑定、首提/重放同源假设验证、独立路径身份锚
product_path_id、镜像终态序列化归一是七个统一契约对象);mimo v6
评审请求已更新待用户转交。

## 1. 提交与 diff

| commit | 内容 |
|---|---|
| (本次单提交) | R6 底座:六模块 v6(audit/chemstate/legacy_reader/ path_context/profile/store)+ 6 个存量测试文件修正(5 个版本串机械升位 + 2 处被证伪语义修正)+ 3 个新增 r6 测试文件(70 用例)+ 交付文档 + mimo v6 请求 + 实施证据 |

源码 diff(相对 293bc62,仅 src/ppv1):6 文件(audit/chemstate/
legacy_reader/path_context/profile/store);测试 diff:6 文件修改 +
3 新文件 1785 行。触碰面仅 `src/pathway_v43/pollutant/` 与 ppv1 测试
(+docs)。**legacy 路径零触碰**(services/atom_tool.py 冻结执行器
未改——镜像终态归一为诊断侧重序列化,不改执行器;storage/
pathway_store.py 未改——legacy_reader 仅 import product_path_id;
G01 全量回归为证)。

## 2. R5 逐项处置表(八组 P1 全部)

### 统一接口(先行落地,三线共用)

| 契约对象 | 定义 | 位置 |
|---|---|---|
| **注册计量补全规则** | `COVERAGE_COMPLETION_RULE = "atom_delta_stoichiometric_completion"`:证据覆盖绑定参与物**系数/贡献**——λ_s=反应物侧 identity==s 的系数和;覆盖产物集整分子/碎片两级映射;每个覆盖 identity 的产物侧声明系数总和 == λ_s×重数;未覆盖参与物元素账与 λ_s×Δ⁺/λ_s×(−Δ)⁺ **各自精确相等不许抵消**(Δ=elements(s)−elements(p));无未覆盖参与物 ⇒ full;未知系数 ⇒ coverage unknown | audit.py 模块级 + `_center_evidence_binding` |
| **CX 输入侧类级登记表** | 移除类($…$ 标签/值、(…) 坐标、atomProp、SgD)/保留类(Sg)/保留注记类(a/oN/&N/^N 逐 token)/其余与无冒号旗标块 ⇒ 拒绝;两个公共结构入口解析前执行 | chemstate.py `_guard_input_cx_classes` |
| **快照同源派生 + 内容身份** | `_validate_phase_history_snapshot`(摘要/旗标/必要行/签名同源,单向矛盾判定)+ `_recompute_context_hash`(构造期同源重算,≠载荷 id ⇒ 拒);from_dict 与 audit 直接对象入口共用 | path_context.py |
| **事件出现清单全量覆盖绑定** | 首提 manifest = 事务提供 + 先存显式绑定(唯一出现绑定/多出现零写入拒)/覆盖断言;重放增覆盖完整性校验 | store.py submit_event + `_verify_event_appearance_manifest` |
| **首提/重放同源假设验证** | 首提复用既存行执行与重放同一复算源(recompute ID + 载荷内 ID=行键 + schema 版本 + 参与物契约,四项同源) | store.py 首提 hyp_row 分支 |
| **独立路径身份锚** | 旧库子路径 path_id == product_path_id(run_id, event_id, position) 确定性派生,替代 child_paths 循环查询 | legacy_reader.py `_substrate_structure_for_path` |
| **镜像终态归一** | 镜像终态 MolToSmiles 序列化→MolFromSmiles 重解析(映射号随 [C:1] 穿越)后才比较,与冻结执行器产物同口径 | audit.py `_simulate_declared_edits` 末尾 |

### 化学与证据线(R5-01/02/08 + P2-1)

| 项 | 修复(代码位置) | 测试 | 结果 | 边界 |
|---|---|---|---|---|
| **R5-01** 单侧未覆盖被无条件授为 full | `_center_evidence_binding` 重写(audit.py,~744-940):系数绑定 + 注册补全规则(见统一表);detail 披露 coverage_rule/substrate_scale/atom_delta/两侧未覆盖元素/coverage_violations(逐条带数值);⑦ 分支条件扩 partial 与 unknown_coefficients 两族进 unknown | r6_chem 12 例(两反例/乙醇氧化/氢化/分列/合并/双侧/比例缩放/H2 不按名称免审/同式量异构不抵消/未知系数/披露字段) | 探针 one_sided_product 与 one_sided_cosubstrate:verified/full/expand → **unknown/partial/retain_conditional**;genuine 控制 verified/expand 保持;元素/电荷账仍 verified(覆盖轴独立) | 补全规则只核元素组成(电荷归 formal_charge_accounting 轴);不要求实现 S3 full_template;合法 H2 计量补全/分列/合并/比例缩放保持 |
| **R5-02** CX 守卫只看规范输出 | `_guard_input_cx_classes`(chemstate.py,新增):原始串解析前按类级登记表校验;build_chemical_state 与 strict_identity_of 一致调用;主会话实证 RDKit 静默丢弃类(r/Ln/c/wU/o/O/d/n/F)构造即拒 | r6_chem 21 例(|r|/|Ln:1| 拒、参数化丢弃类拒、五类登记移除同 id、SgD 逗号/SRU 往返/增强组/自由基、双管道段、token 级、机读码分列) | 探针:\|r\| 与 \|Ln:1\| accepted(同 id)→ **rejected(unregistered_cx_class)**;atomProp/$_AV 保持 accepted;语法不可解析维持 unparseable_smiles | 登记表是类级白名单,新 CX 类默认拒绝(fail-closed);RDKit 行为变化须重登记 |
| **R5-08** 镜像漏执行器终态序列化 | `_simulate_declared_edits` 末尾(audit.py,~2228-2248):镜像终态序列化/重解析后参与比较;失败按原内存图(如实失配);**不改冻结 executor** | r6_chem 4 例(断邻位σ键零失配/远端断尾/改双键/断双键正控制) | 探针:真实 C/C=C/C 断 U_C_1–U_C_2:undeclared_bond_change U_C_2–U_C_3/center None → **mismatches=[]/center True/strict True**;actual_bond_diff == mirror_reparsed_bond_diff | 不新增立体操作协议、不删 E/Z 轴、不默认忽略 stereo loss;真翻转/伪造失配/from_order/净效应控制保持 |
| **P2-1** proof_scope/basis 空串 | evidence_payload 增 center_match_basis 与 proof_scope(audit.py ~2725);`_evidence_integrity_mismatches` 增 basis 比对;复算分支 base_detail/axis_detail 同源披露;verified 理由码 basis= 非空 | r6_chem 2 例(披露/篡改 basis ⇒ integrity 拒) | 探针:proof_scope None → **self_contained_recompute**;basis= 空串 → **basis=direct** | 自包含重算不证明历史执行(命题边界如实披露,不升级为实验/模板证明) |

### 条件与科学前提线(R5-03/04 + P2-2)

| 项 | 修复 | 测试 | 结果 | 边界 |
|---|---|---|---|---|
| **R5-03** 非物种 known_absent 当正事实 | `_assess_requirement`(path_context.py,~791-823):单位三态检查后、值匹配前消费 fact.status——数值缺席 unknown(numeric_absence_semantics_undefined)/同词缺席 conflict(required_value_known_absent)/异词缺席 unknown(other_value_known_absent_not_determining) | r6_conditions 4 反例+物种/单位/枚举正控制 | 探针:oxygen aerobic absent satisfied+expand → **violated/defer**;matrix soil absent → **violated/defer**;温度 25/C absent → **unknown/retain**;物种 NADH absent conflict 保持 | 首版未定义数值否定语义(unknown,不化学 reject);"25不存在"不推整区间不存在 |
| **R5-04** 恢复入口信任矛盾快照 | `_validate_phase_history_snapshot` + `_recompute_context_hash`(path_context.py,新增):from_dict 与 validate_context_object(audit 直接对象入口)双道校验(见统一表);消费方逻辑不动 | r6_conditions 6 例(摘要篡改/旗标篡改/就地篡改 audit 拒/事实篡改保 id 拒/合法往返幂等/正常阶段转换) | 探针:summary_changed 与 has_gate_false expand → **from_dict ConditionContractError(fit_conflict_mismatch 族)**;before(conflict→defer)保持 | 单向矛盾判定不误拒合法历史(全部满足但 scope 空记 unknown 合法);不拿当前事实重评旧边;不认证用户事实真实性 |
| **P2-2** 循环诊断以总 status 污染两种语义 | `_relation_axes_supported` + detect_circular_dependencies(path_context.py):has_initial 只看 initial_supply 轴(去总体 status 门);关系按关系轴(reaction/regeneration)各自当前有效状态 | r6_conditions 4 例 + s2 h04 正例 | 探针:initial_supported_reaction_contradicted:误报启动未知 → **unresolved:0/unsupported:1**;initial_contradicted_later_regen:混入关系不支持 → **unresolved:1/unsupported:0**;双支持/恢复正控制 0/0 | 关系轴加"任一关系轴被反驳 ⇒ 关系不成立"保守门(超出字面公式,只增披露不减,理由见 §6);audit 侧消费总体 status 保持(方向正确) |

### 存储与适配线(R5-05/06/07)

| 项 | 修复 | 测试 | 结果 | 边界 |
|---|---|---|---|---|
| **R5-05** appearance manifest 只覆盖本次 states | submit_event 首提绑定段(store.py,~1516-1620):非事务提供的 derived_ref 从账本显式绑定(唯一出现/0 行损坏/≥2 行 appearance_source_ambiguous 零写入拒);manifest=提供+绑定(去重)+覆盖断言;`_verify_event_appearance_manifest` 增覆盖完整性(缩成子集 ⇒ event_appearance_manifest_coverage_corrupt) | r6_storage 8 例(全先存幂等/部分先存删出现损坏/清单缩子集损坏/歧义拒绝/零出现损坏/全量删出现损坏/正常重放/cn_only 控制) | 探针:pre_stored_all 重放 Ppv1LedgerCorrupt → **created=False 幂等**;partial 删实际出现 success → **Ppv1LedgerCorrupt**;缩子集 success → **Ppv1LedgerCorrupt**;supplied_all 控制保持 | 歧义时选"零写入拒绝"方案(要求随事务显式提供载荷或唯一出现下先提交;未实现显式 appearance 引用参数);损坏保全不补账 |
| **R5-06** 首次复用既存假设行不验 | 首提 hyp_row 分支(store.py):与重放同源四项(recompute_hypothesis_id/载荷内 ID=行键/schema 版本/参与物契约——末三项为主会话补齐存储线申报残留);校验区执行 ⇒ 零新增事件/投影/计划 | r6_storage 6 例(篡改 assumptions/内 ID/schema 参数化首提即拒 + 正常先存 created=True + 排序幂等) | 探针:tampered assumptions first created=True → **首提 Ppv1LedgerCorrupt(hypothesis_payload_id_corrupt)**;正常先存假设首提 created=True 保持 | put_hypothesis 入口复算既有(提供载荷路径);SQL 篡改后 put 同 ID 原载荷 ⇒ hash 冲突已挡 |
| **R5-07** 同父同 CN 兄弟来源循环证明 | `_substrate_structure_for_path`(legacy_reader.py):删 child_paths 循环查询,改 path_id == product_path_id(run_id, event_ptr, pos_ptr) 独立确定性身份锚(storage/pathway_store 派生规则;仅 import 不改) | r6_storage 3 例(错指针降级/正控制/多位次锚) | 探针:错指针 → **CN-only + substrate_source_event_relation_mismatch + uncertainty 披露,不导入相反立体 raw**;正确兄弟来源/多位次/旧库字节不变保持 | root/指针残缺/存档缺失/身份矛盾既有降级分支不动;旧库只读 |

## 3. §4 披露项与 mimo R5 意见处置(按 §5 采纳边界)

| 项 | 处置 |
|---|---|
| §4-1 proof_scope/basis 展示 | 落实(载荷+detail+理由码三处同源;篡改 basis ⇒ integrity 拒);mimo 冻结前条件 ①② 完成,③(覆盖括注交叉引用)并入 mimo v6 请求判据三文本 |
| §4-2 循环诊断轴消费 | 落实(P2-2,按对应有效轴;含一处只增披露的保守门,见 §6) |
| 自洽虚拟记录不是 P1 | 采纳:本轮不把"虚拟但自洽"列为缺陷;其命题=输入集重算自洽,已由 proof_scope 披露边界;不升级为历史执行/机制/实验事实 |
| mimo"判据三覆盖完全同意" | **不采纳并修正**(Codex §5):mimo 单侧共底物例碰到元素 violated 不能证明覆盖逻辑安全;本审两组数值完全配平反例证明问题在覆盖轴——已按系数绑定+注册补全规则修复 |
| mimo"断键 E/Z 消失须另设立体申报通道" | **不采纳并修正**:同一终态序列化(镜像写出/重解析)足以对齐;实际执行已成功、镜像同口径后一致;mimo"3b 两路皆失"与实测 STEREOE/STEREONONE 直接证据矛盾;不靠登记误报关闭 |
| mimo 探针建议留存 | R6 新增回归已覆盖全部 8+2 反例与正控制(规则级合成夹具入库 tests/);探针复跑证据存 ppv1_r6_impl 目录 |
| DATA 全类注记假设约束适配器 | 保持(SgD 剥离前提已写入 mimo v6 请求判据一) |
| 单位换算/full_template/edge_kind/scoring_key/S3 调度/S5 性能 | 不转为新增强制功能(见 §6) |

## 4. 模块内实现说明

三线并行实施(化学/条件/存储,文件不相交),统一接口先行(§2 统一表
在主会话定稿:注册补全规则的数学语义、输入侧登记表的类级划分、
快照同源判定方向、manifest 绑定方案、同源四项、product_path_id 锚、
镜像归一口径),profile 版本族由主会话单点升 -6(避免并行冲突),
主会话补齐存储线申报的 R5-06 残留(首提既存行三项检查)并审查全部
diff。

## 5. 测试证据与命令

~~~bash
PY=~/miniconda3/envs/depending43/bin/python
REPO=/Volumes/CC/Enzyme_Agent/dependingv43

# 全量 ppv1(16 文件)
PYTHONDONTWRITEBYTECODE=1 $PY -B -m pytest -p no:cacheprovider -q \
  tests/test_ppv1_profile.py tests/test_ppv1_domain.py tests/test_ppv1_s2.py \
  tests/test_ppv1_rework.py tests/test_ppv1_r2_conditions.py \
  tests/test_ppv1_r2_storage.py tests/test_ppv1_r2_chem.py \
  tests/test_ppv1_r4_conditions.py tests/test_ppv1_r4_storage.py \
  tests/test_ppv1_r4_chem.py tests/test_ppv1_r5_chem.py \
  tests/test_ppv1_r5_conditions.py tests/test_ppv1_r5_storage.py \
  tests/test_ppv1_r6_chem.py tests/test_ppv1_r6_conditions.py \
  tests/test_ppv1_r6_storage.py
# => 451 passed in 3.69s,0 skipped(381 存量 + 70 新增)

# G01 legacy 回归(全量 not slow)
PYTHONDONTWRITEBYTECODE=1 $PY -B -m pytest -p no:cacheprovider -q \
  -m "not slow" tests/
# => 1062 passed, 16 deselected in 231.70s,0 failed
#    (611 legacy + 451 ppv1;legacy 路径零改动;日志 g01_legacy_run.txt)

# R5 审核探针复跑(复制到新临时目录;每脚本独立子目录)
tmp=$(mktemp -d /private/tmp/ppv1-r6-probes.XXXXXX)
cp $REPO/docs/review_evidence/ppv1_r5_codex_2026-10-07/*.py "$tmp/"
cd "$tmp" && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$REPO/src $PY -B \
  admission_coverage_probe.py   # exit 0;反例翻转,控制保持
# chemistry_boundary_probe / conditions_probe / storage_boundary_probe:exit 0
# r4_admission_probe 原样脚本 exit 1 于篡改证据用例(结构化拒绝是修复
#   行为,R5 交付已记录,非回归);recheck 版(AST 逐调用捕获)exit 0
# r3/r4 chemistry/storage/conditions 旧探针 exit 0
# 复跑证据存 docs/review_evidence/ppv1_r6_impl_2026-10-07/
~~~

### 5.1 红验证(先红后绿)

- 基线:`git worktree add --detach <tmp> 293bc62`,复制 3 个 r6 测试
  文件(r6_chem 对 v6 新常量 COVERAGE_COMPLETION_RULE 做字面量替换,
  仅影响 import 不影响断言语义),运行 ⇒ **44 failed / 26 passed**
  (70 用例);
- 26 个基线通过项全部为**正控制**(五类登记移除同 id/w:1.0 输出侧
  拒绝/SgD 逗号值/SRU 往返/增强组与自由基/R5-08 三个正控制/lumped
  控制/unparseable 机读码分列);
- 44 红中 **38 个为 R5 复审反例的行为翻转**(断言形如
  satisfied==conflict、verified==unknown、DID NOT RAISE);
- **6 个红是正控制语义基线已绿、仅因 v6 新披露键缺失**(KeyError:
  substrate_scale/atom_delta/coverage_rule/center_match_basis——其核心
  语义断言 center=verified/full/expand 在基线 293bc62 已通过;这 6 个
  是"披露新增"测试,非缺陷翻转);
- v6(当前工作树)⇒ **70/70 全绿**;工作树已清理。

### 5.2 修改的既有测试与理由

| 测试 | 改动 | 理由 |
|---|---|---|
| test_ppv1_profile/s2/r2_chem/r2_conditions/r4_chem 版本断言(11 处) | -5 → -6 | 契约族升 v6(机械) |
| test_ppv1_r5_conditions `test_r4_04_empty_snapshot_...` 的"删空快照对照" | 就地 `child.phase_history = []` 改为 build_path_context 合法构造等价无快照上下文 | 就地删除快照正是 R5-04 要求 audit 入口拒绝的内容身份篡改形状(该拒绝由 r6_conditions 钉住);原控制意图"孤儿 ⇒ unknown 不依赖快照存在"保留 |
| test_ppv1_s2 `test_h04_circular_...` 第三段 | 断言改为"A→B 仅 initial_supply 证据 ⇒ 关系未支持仍披露",并补 reaction 轴正例 | 原断言把"总体 supported(仅接种证据)"当关系成立,是被 P2 点名的"以总 status 判关系"混用;原控制意图(关系轴都有支持 ⇒ 清空)以正例保留 |

### 5.3 复审探针前后对照(关键行)

| 探针行 | v5(293bc62,R5 复审记录) | v6(本轮回跑) |
|---|---|---|
| admission one_sided_product_unchecked_isomer_half | verified/full/expand | unknown/partial_unchecked_transformation/retain_conditional |
| admission one_sided_cosubstrate_unchecked_to_same_product | verified/full/expand | unknown/partial_unchecked_transformation/retain_conditional |
| admission genuine_bound/hydrogenation 控制 | verified/expand | verified/expand(保持) |
| admission old_two_sided_unchecked 控制 | unknown/retain | unknown/retain(保持) |
| admission P2 披露 | proof_scope=None;basis=) | proof_scope=self_contained_recompute;basis=direct |
| chemistry cx \|r\| / \|Ln:1\| | accepted,与裸串同 id | rejected(unregistered_cx_class) |
| chemistry cx atomProp/$_AV/坐标/标签 | accepted 同 id | accepted 同 id(保持) |
| chemistry adjacent_sigma_break | undeclared_bond_change U_C_2–U_C_3;center/strict None | mismatches=[];center/strict True;actual==mirror_reparsed |
| chemistry 三个 R5-08 正控制 | 通过 | 通过(保持) |
| conditions oxygen/matrix absent | satisfied+expand | violated/defer |
| conditions temperature absent | satisfied+expand | unknown/retain |
| conditions species NADH absent 控制 | conflict | conflict(保持) |
| conditions snapshot summary/flag tamper | expand | from_dict ConditionContractError |
| conditions 轴控制(交叉两例) | 启动误报/关系混入 | 分立(见 §2 P2-2) |
| storage pre_stored_all replay | Ppv1LedgerCorrupt | created=False 幂等 |
| storage partial 删实际出现 | created=False(成功) | Ppv1LedgerCorrupt |
| storage manifest 缩非空子集 | 成功 | Ppv1LedgerCorrupt |
| storage existing_hyp 首提 | created=True | Ppv1LedgerCorrupt(hypothesis_payload_id_corrupt) |
| storage legacy 错指针兄弟 | 接受相反立体 raw 无注记 | CN-only+原因+不导入该 raw;旧库字节不变 |
| storage supplied_all/正常重放/正控制 | 通过 | 通过(保持) |

## 6. schema/语义版本与兼容策略

| 契约 | v5 → v6 | 兼容声明 |
|---|---|---|
| profile/chemstate/hypothesis/event/store/context/dependency/ provenance/substrate_profile/audit/admission_policy/donor_diagnostic/pool_audit/pool_order/input_preview/condition_assessment | -5 → -6 | profile 从未放行执行流(入口 fail-closed),无已发布 run/产物;升版即生效,无迁移;v5 文件按未知版本拒绝(既有门) |
| gate_mapper | -3(不动) | 本轮未触碰 |
| run identity | v43-identity-2(不动) | 未触碰 run_identity.py |
| search_limits | -2-proposed(不动) | proposed 草案,S3 落地 |

语义变化要点(v6):中心证据覆盖绑定参与物系数/贡献(注册补全规则;
coeff 绑定与补全对账数值化);CX 输入侧类级登记(原始输入守卫先于
解析);条件评估消费事实 status(known_absent 三分);context 恢复/
审核入口核快照同源派生 + 内容身份重算(篡改任何语义字段保 id ⇒ 拒);
事件 payload 的 manifest 语义从"事务内 states"扩为"本事件全部出现
引用"(表结构未变);首提复用既存假设行与重放同源四项验证;旧导入
关系锚改独立确定性派生;镜像终态与执行器同口径序列化。

legacy_v43:零改动承诺继续成立——全部改动在 pollutant/ 包与 ppv1
测试;冻结执行器 services/atom_tool.py 未改(镜像归一为诊断侧重
序列化);storage/pathway_store.py 未改(仅 import product_path_id);
G01 全量回归为证。

## 7. 剩余未知与边界(不宣称冻结)

1. 化学判据 v6 **未冻结**:mimo v6 评审请求已更新(§8),待用户
   转交;冻结以 review + mimo 回应与程序证据互证为准。
2. 契约 v6 未冻结;S3 入口 fail-closed 未解除(runner 未触碰);
   不实施搜索/队列/终点/评测。
3. **补全规则边界**:atom_delta_stoichiometric_completion 只核元素
   组成(逐元素分数,含氢全计),不核电荷分布(电荷归
   formal_charge_accounting 独立轴);补全通过只解除覆盖轴,不证明
   机制/酶可行性/计量必然性。
4. **输入侧登记表是类级白名单**:未登记 CX 类默认拒绝(fail-closed,
   不猜测解析);RDKit 新版本解析行为变化须重登记;数值否定语义
   首版未定义(评估 unknown)。
5. **环诊断关系轴的保守门**:在"至少一条关系轴 supported"之上加
   "任一关系轴当前 contradicted ⇒ 关系不成立"(为满足
   initial_supported+reaction_contradicted 的轴语义分立;只增披露
   不减,方向 fail-closed)——已写入 mimo v6 请求请评审表态。
6. **appearance 歧义方案**:选"零写入拒绝"而非"显式 appearance
   引用参数"(R5-05 验收允许二选一);调用方须随事务显式提供载荷
   或先在唯一出现下提交。
7. **S3 排期项(不冒充已实现)**:完整供体变换模板 checker
   (full_template scope)独立注册;执行流接 center_evidence;
   local_delta/edge_kind/scoring_key;互变/质子化等价类;被拒
   共同产物的展开计划消费。
8. 已知缺口(登记保留):增强组联合映射范围(unsupported);平面
   手性等非四面体构型比较(unsupported+公开);条件单位不换算
   (入口契约);matrix 同义/包含须注册;fidelity 的 radical 保真轴;
   cip_label_change_is_not_config_change 就地标注(mimo 建议,
   未实现);manifest 歧义显式引用参数。
9. 科学验收整体 pending(S5);451 项工程测试不构成任何路径
   科学性能声明;合成计量闭合不证明机制/生物可行性/酶选择性
   (探针与测试全部如实标注来源;自洽虚拟记录只证明输入集重算
   自洽,不证明历史执行)。

## 8. mimo v6 化学评审请求

已更新 `docs/mimo_ppv1_chem_review_request.md` 为 v6 文本(判据一
输入侧类级登记表;判据三系数绑定+注册补全规则+proof_scope/basis
披露;判据四 known_absent 三分+快照同源+内容身份+环诊断分轴;
判据五镜像终态归一废除"3b 恒失配/申报通道/知觉差边界")。自包含、
规则级、无金标;**由用户转交**,回复原文落盘 docs/;不自行外发。

## 9. 与原规格的冲突清单

无新增实质冲突。八处"规格未逐字规定、按 R5 复审验收收紧/具体化":
- §8 中心证据具体化为参与物系数绑定+注册计量补全规则(R5-01 验收;
  规格只要求"可核验证据",未定系数/贡献语义);
- §5.1 身份键入口具体化为 CX 输入侧类级登记表(R5-02 验收);
- §6 条件事实消费顺序具体化为 status 先于值匹配 + known_absent
  三分(R5-03 验收;规格 §6 定义了枚举但未定优先级);
- §6 快照一致性 + context 内容身份同源重算(R5-04 验收;规格无
  显式条款);
- §5.3/§9.2 事件持久格式具体化为 appearance manifest 全量覆盖绑定
  (R5-05 验收);
- §9.2 事件幂等验证扩到首提既存行同源四项(R5-06 验收);
- §3.1 legacy 只读适配具体化为独立确定性身份锚 product_path_id
  (R5-07 验收);
- §7.1 供体诊断镜像终态归一与冻结执行器同口径(R5-08 验收;
  规格无镜像条款,不改执行器)。
