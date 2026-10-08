# pollutant_pathway_v1 S4 回修 r3 交付书(2026-10-08)

实施者:主会话按 AGENTS.md 评审-回修循环派出的唯一 S4 r3 实施
agent。回修范围 = 复审 R3(`docs/POLLUTANT_PATHWAY_S4_CODEX_REVIEW_R3_
2026-10-08.md`)§4 **唯一阻塞 P1 = PPV1-ISO-01**(同位素变化漏核导致
错误中心 verified/full、R6 与实际提交) + §8 有限回修提示词;C01/C02/
C03/C04、其它 S3 已证组保持关闭,不改 legacy/G2/AtomTool,不加科学门,
不含 S5。开工 HEAD = `2ff919fa6ef127d4a477b1b1bb52beb685365a9d`
(直接父 = r2 提交)。**S4 完成交接点不由本批宣布**;判分零 LLM,不
调用外部模型(mimo 请求仅落盘文档,由用户送审)。

**处置方案:方案 A(唯一执行)。**复审 R3 §4.4 给出 A/B 两案;本仓
操作约定明确默认且只允许方案 A——按冻结判据五 §5 现义(冻结正文
`docs/POLLUTANT_PATHWAY_CRITERIA_FROZEN_V1_2026-10-08.md` 394–396 行
早已承诺"键 diff ∪ 电荷/立体/同位素变化集"为实际净变化基础)把
isotope diff 并入实现。这是**兑现既有冻结承诺,不改冻结正文/判定
规则/理由码语义框架**;实施全程未出现需要缩窄冻结文字才能收口的
情形(无方案 B 触发)。criteria-v1 冻结正文与 FREEZE_RECORD 逐字节
零触碰。

---

## 1. 入口矩阵(开工先立;登记实际净变化轴/映射/scope/身份版本/
正常与 unknown 控制)

回修链六层,每层登记 isotope 轴的实际状态与本批变化:

| 层 | 入口(源码锚) | isotope 轴改前状态 | 本批变化 | 版本/身份 |
| --- | --- | --- | --- | --- |
| 1 原始诊断 | `check_edit_against_donor`(audit.py:2504;净变化计算 :2630–2654、属性 diff `_atom_property_diffs` :2110) | 身份键(chemstate)保留同位素但 `_atom_property_diffs` 从不比较 ⇒ 纯同位素落"身份不同而图轴空"分支,被 `net_change_only_in_stereo_representation`(旧 :2711–2726)误标"仅立体";混合案中心外同位素变化**不入** changed atoms ⇒ 漏核后 center True | isotope diff 入 deltas(机读码 `isotope`)/records(`isotope:[before,after]`)/changed atoms/中心外 extra_changes/中心属性披露;`net_change_only_in_stereo_representation` 文字如实缩窄(同位素轴已入图变化集,残余=真立体表示差异;**不改码名**);判定规则(实际变化 ⊆ 对齐中心 ⇒ True/中心外 ⇒ False)不变 | **ppv1-donor-diagnostic-8 → -9** |
| 2 converter | `center_evidence_from_donor_diagnostic`(audit.py:2972) | 透传诊断内嵌绑定载荷 | 不变(透传);载荷 checker_version 随 -9 | 同诊断 |
| 3 audit 重算/proof gate | `_rerun_proof_record` + `_evidence_integrity_mismatches` + `_center_evidence_binding`(audit.py:727/753/797) | 复跑同一确定性 checker ⇒ 同漏核;篡改自报 center_match=True 与复算 True 一致 ⇒ 不可检出 | **公开重算自动同轴**(复跑同一 checker);混合案复算 center False ⇒ 篡改 True 被完整性门拒;`CENTER_CHECKER_REGISTRY` 随 -9(旧 -8 载荷按未注册 ⇒ unknown,既有版本门行为) | audit-8/admission-8 不变(决策表/理由码/分支零改动;语义变化全部由 donor-diagnostic-9 承载) |
| 4 admission | `decide_admission`(audit.py:1643) | 中心 verified + 全核实 ⇒ R6 expand | 决策表不变;输入变化 ⇒ 混合中心外中心 violated ⇒ **R5v retain_conditional,先于 R6** | 同上 |
| 5 公开 production caller | `expand_hypothesis_production` → `execute_atomtool_expansion`(production.py:341/:263) | 经 execute_edits → check_edit_against_donor → converter → audit → admission 全链 ⇒ 混合案 submitted + verified/full + expand/R6 | 同链路传播:混合中心外 ⇒ center violated + R5v(**不再 R6**;按已登记策略 expand/retain_conditional 均可提交,后者轴结论如实 violated 保留,"未展开项/unknown 不消失") | production 零改动(行号字节不变;行为由上游诊断决定) |
| 6 submit/replay | `store.submit_event`(store.py) | admission expand 才提交 | 探针层(公开诊断→准入入口)混合案 admission 非 expand ⇒ **不提交**;生产层 retain 按已登记策略提交但事件/报告如实记 violated/R5v;重放幂等不变 | store-10 不变 |

**正常/unknown 控制(全部保留,不以全面拒绝换通过)**:正常键变
(bond_control)、原有 13C 保持(isotope_retained_bond_control)、中心内
isotope(mixed_inside)、全中心范围控制(all_center)⇒ verified/R6
不变;strict False ⇒ violated 不变;非四面体 stereo-only ⇒ unknown +
`net_change_only_in_stereo_representation` + 公开 unsupported 清单
不变;带标签结构不一概拒绝(13C 保持正控钉住)。

**未核轴/scope 如实性**:纯同位素不再以"仅立体"中性码冒充(走真实
轴:isotope delta + 中心范围判定);立体表示残差仍走原码且文字声明
同位素轴不在其列。**不宣称**原 AtomTool 会编辑同位素(冻结协议无该
op;反例是合成工具返回的公共防御消费链),不认证实验/机制/来源真实
性(self_contained_recompute 证明输入自洽重算,非执行事实)。

## 2. PPV1-ISO-01 修复:isotope diff 并入实际净变化(方案 A)

**改前行为**(复审 R3 §4.2 反例,本仓复现确认):`CCO` 真实 AtomTool
执行 S_C_2–S_O_1 single→double 得 `CC=O`,合成返回仅把中心外
S_C_1 置 13C(plain/mapped 一致,`[13CH3]C=O`);声明中心
S_C_2/S_O_1、完整 maps/系数/自包含 proof 合法 ⇒ 变化集只列中心键/H
变化 ⇒ diagnostic center=True、strict=True、missing=[] ⇒ audit
transformation_center=**verified**、product_coverage=full ⇒ **R6
expand** ⇒ 公开 submit created=True(事件 ppev_622dcbaa1c42bbdc24dc
入库);production 同链 submitted/expand/R6(事件
ppev_0819a581aaf3ab0e7c91)。

**改后行为**(audit.py,共四处语义落点):
1. `_atom_property_diffs`(:2110):逐原子 `GetIsotope()` 比较
   (b_iso≠a_iso ⇒ deltas 加 `isotope`,记录 `isotope:[b,a]`)——
   **入 changed atoms**;与零净变化分支自洽(身份键含同位素 ⇒ 身份
   相同则同位素必相同,该轴不可能在身份等同时报告差异);
2. 中心判定沿用既有规则:changed_atoms 含 S_C_1(中心外)⇒ 联合
   映射不存在(2 元中心集不可能映到 3 元变化集)⇒ center=False +
   extra_changes(S_C_1:delta=[isotope, present_in_product],
   isotope={before:0, after:13});
3. 披露:`center_property_deltas` 记录增 `isotope` 键(中心原子
   前后值),`_atom_change_summary`(中心外逐原子 Δ 摘要)增
   isotope before/after;`net_change_only_in_stereo_representation`
   文字缩窄为"残余差异属未比较/未承载的立体表示轴(同位素轴已入
   图变化集,不在此列)"——**不改码名、不新增拒绝面**,纯同位素
   v9 起不再落入该分支;
4. **公开重算**:`_rerun_proof_record` 复跑同一 checker ⇒ isotope
   轴自动进 audit 复算;`evidence_payload.checker_version` = -9,
   `CENTER_CHECKER_REGISTRY` 随之(旧 -8 证据按未注册 ⇒ unknown,
   fail-closed 不静默兼容)。

**声明–执行对账边界保持**:`_declaration_accounting` 仍只对账键
变化/原子增删(ops 声明语言无同位素操作;同位素检出走属性 diff
披露 + 中心范围判定,与"电荷/ΔH/构型不在对账范围"的既有登记
一致,audit.py:2358–2359 注释不变)。**不加科学门**:不认证同位素
计量学/核反应/现实可行性;全部受变原子列入中心的声明是范围控制
(评审 §4.2 语),v9 下仍 verified/R6。

## 3. 版本与身份登记(工程注册;判据冻结范围零触碰)

- `ppv1-donor-diagnostic-8 → -9`(profile.py;诊断 schema_version/
  checker_version/CENTER_CHECKER_REGISTRY 同源单点)、
  `ppv1-profile-18 → -19`(身份块含 donor_diagnostic ⇒ 随升;注册
  注释落 v9 条目)。audit-8/admission-8/store-10/runflow-5/
  endpoint-2/endpoint-policy-2/native-result-2/native-export-3/
  native-export-policy-3/v3-projection-3 全部不变(语义变化由
  donor-diagnostic-9 承载,profile 身份块如实反映)。
- 既有测试字面量 7 处(7 文件):test_ppv1_profile.py(profile-19 +
  donor-diagnostic-9 断言)、test_ppv1_s4b_export.py(profile-19)、
  test_ppv1_r2_chem.py ×2、test_ppv1_r4_chem.py、test_ppv1_r7_chem.py、
  test_ppv1_s3b_production.py(checker_version -9;手造证据输入随
  当前注册版,语义用途不变)。test_ppv1_s4_rework_r2.py 的
  `ppv1-profile-17` 冲突反例**保持不动**(旧版本按未注册拒的语义
  正确)。
- **criteria-v1 冻结正文/FREEZE_RECORD 逐字节零触碰**;代码/证据
  契约语义变化全部登记于 profile.py v9 注释与本交付书。

## 4. 新回归(tests/test_ppv1_s4_rework_r3.py,14 用例)

| 用例 | 断言核心 | 对父 2ff919f |
| --- | --- | --- |
| test_iso01_pure_isotope_real_axis_not_stereo_mislabel | 纯同位素 center False + 真实轴披露;不再有立体误标码 | 行为红 |
| test_iso01_mixed_outside_isotope_center_false | 混合中心外 center False、strict True、missing 空、extra isotope 披露 | 行为红 |
| test_iso01_mixed_inside_center_still_true | 中心内 isotope ⇒ center True + isotope 披露键 | 字段红 |
| test_iso01_all_atoms_center_scope_control | 全中心范围控制 ⇒ True/basis=direct | 控(父绿) |
| test_iso01_retained_isotope_bond_change_still_true | 原 13C 保持 ⇒ center True、isotope 披露键 | 字段红 |
| test_iso01_non_tetra_stereo_only_still_unknown_stereo_code | stereo-only ⇒ unknown + 立体码 + 公开清单 | 控(父绿) |
| test_iso01_wrong_target_strict_false_still_violated | strict False ⇒ violated(分支优先级不变) | 控(父绿) |
| test_iso01_diagnostic_version_bumped | checker_version = -9 | 版本红 |
| test_iso01_mixed_outside_audit_violated_not_expand | 公开 audit 重算 ⇒ violated/R5v/非 expand、中心轴分轴披露 | 行为红 |
| test_iso01_mixed_outside_tampered_true_blocked_by_recompute | 篡改自报 True ⇒ integrity 结构化拒(父上复算同 True 不可检出) | 行为红 |
| test_iso01_retained_control_audit_verified_r6 | 13C 保持全链 ⇒ verified/R6 | 控(父绿) |
| test_iso01_production_mixed_outside_not_r6 | 生产 caller(唯一替换工具输出通道,其余真实)⇒ 非 R6/violated/R5v retain | 行为红 |
| test_iso01_production_bond_control_still_r6 | 生产正控 ⇒ expand/R6/submitted/done | 控(父绿) |
| test_iso01_production_retained_isotope_control_still_r6 | 生产 13C 保持正控 ⇒ expand/R6 | 控(父绿) |

生产 caller 反例复现与评审同法:`unittest.mock.patch.object(pm,
"execute_edits", controlled)`,controlled **先真实调用 AtomTool**
再只在返回通道一致置 13C;donor/converter/audit/admission/writer/
complete 全真实,不 patch 审核结论。

## 5. 独立执行数字(合成规则级工程回归,不外推 dev/298)

| 验证 | 本批实际结果 | 说明 |
| --- | --- | --- |
| PPV1 全量(仓内树) | **976 passed / 0 skipped,exit 0** | 36+1 文件(962 存量 + 14 新);`-B`/PYTHONDONTWRITEBYTECODE=1/no:cacheprovider |
| 父 2ff919f 同字节 | **15 failed / 961 passed,0 collection 红** | 5 行为 + 2 字段(KeyError `isotope`) + 8 版本;含 7 存量版本字面量用例;基线树 = `git archive 2ff919f` 解包 + 7 个本批触改测试文件同字节覆入(逐文件 SHA 相等) |
| 8 分案复现(fresh tmp 隔离源码) | 混合中心外 **violated/R5v/不提交**;纯同位素 violated(真实轴);正常键变/13C 保持/中心内/全中心/strict-False/stereo-only 全保持 | 评审 probe.py 逐字复用;`PYTHONPATH=<隔离>/src_copy`;控制案事件 ID 与评审逐字相同(ppev_caabf93…/ppev_6a36cd…/ppev_1a646c…/ppev_fdfb91…),混合案 ppev_622dcbaa… 不再创建 |
| 3 production caller 复现 | 混合案 **retain_conditional(R5v)/center violated/非 R6**;两正控 expand/R6/submitted 不变(事件 ID 与评审相同) | production_probe.py 逐字复用;混合案事件 ppev_0819a581aaf3ab0e7c91 仍按已登记 retain 提交策略落库(轴结论如实 violated/R5v);工具 raw vs 消费返回确定性 diff 仅 product_smiles/product_mapped_smiles 变 |
| G01 安全隔离 | **1578 passed / 8 skipped / 17 deselected,exit 0**(1564 存量 + 14 新;228.21s) | 297 输入(296 谱系 + 1 新 r3 测试文件)执行前后 SHA-256 **全同**(297/297);8 skip/17 deselect 逐 nodeid 与评审 R3 相同;证据包 g01/ |

红绿分类(对父同字节):**行为红 5**(混合/纯同位素诊断与 audit/
篡改检出/生产 R6)、**字段红 2**(isotope 披露键)、**版本红 8**
(7 存量字面量 + 1 新用例)、**collection 红 0**;正常控 6 项父绿
子绿不翻红。数字是工程回归,不是漏洞数或科学性能。

## 6. 8 分案改前/改后对照(证据 before_after_comparison.json)

| 分案 | 诊断 center | audit 中心 | admission | 探针层提交 |
| --- | --- | --- | --- | --- |
| isotope_only | None→**False** | unknown→**violated** | R5→**R5v** | 否→否 |
| bond_control | True(不变) | verified(不变) | R6(不变) | 是(不变) |
| isotope_retained_bond_control | True(不变) | verified(不变) | R6(不变) | 是(不变) |
| **mixed_outside_isotope** | **True→False** | **verified→violated** | **R6→R5v** | **是→否** |
| mixed_inside_isotope | True(不变) | verified(不变) | R6(不变) | 是(不变) |
| mixed_outside_isotope_all_center_control | True(不变) | verified(不变) | R6(不变) | 是(不变) |
| mixed_outside_wrong_target_control | True→False | violated(不变) | R5v(不变) | 否→否 |
| non_tetra_stereo_only_control | None(不变) | unknown(不变) | R5(不变) | 否→否 |

生产 caller:production_mixed_outside_isotope **expand/R6/verified →
retain_conditional/R5v/violated**(status 仍 submitted = 已登记 retain
提交策略,事件内容如实记 violated);两正控不变。strict 轴/声明对账
轴全部 8+3 案前后一致(declaration_mismatches 均空)。

## 7. G01 安全隔离(隔离口径;数字为工程回归,不与仓内树混计)

隔离谱系沿 R7→s3a_r4→s3b_r1/r2/r3→s4a_r1→s4b_r1→s4_rework_r1/
r2→**本批 r3**;白名单路径同源(R7 manifests + 历批新输入),本批
新增安全项 = tests/test_ppv1_s4_rework_r3.py(1 项,296→297 输入),
触改文件以当前字节新鲜 SHA 登记(audit.py/profile.py + 6 个测试
文件)。复用评审 safe_g01 脚本谱系改 r3 副本(fresh tmp 执行,旧
永久证据零触碰):**1578 passed / 8 skipped / 17 deselected,
exit 0(228.21s)** = 1564(r2 基线)+ 14(本批新);8 skip 逐项
(v4 对照根 1、v2 provenance/summary 2、冻结 v3 真实评价依赖 5)
与 17 deselect nodeid 逐项与评审 R3 相同(g01/preparation.json +
execution_result.json);297 输入 SHA-256 执行前后**全部不变**
(g01_sha_verification.json:297/297,changed_count=0);BBD_DATA_
ROOT 空目录 + V3_CODE_ROOT/V43_ASSET_ROOT 钉隔离源、禁 pyc/cache。
缺席不是通过;工程用例数不称科学性能。

## 8. 证据目录与完整性

`docs/review_evidence/ppv1_s4_rework_r3_2026-10-08/`:README(命令/
argv/env/exit/边界)、commands.json、logs/(PPV1 全量、父同字节、
8 分案、3 caller、G01 stdout/stderr/JUnit)、results/(8 分案完整
输入/proof/诊断/audit/admission/表前后)、production_results/(3 案
完整输入/工具原输出与合成输出/全表/生产报告/artifact JSON)、
controlled_result_diff.json(工具 raw vs 消费返回确定性 diff)、
before_after_comparison.json(对评审 R3 逐案前后)、g01/(preparation/
input_sha256 前后/execution_result/JUnit)、source_snapshot(当前树
关键源文件 SHA 与父字节 diff 范围)、manifest.json + SHA256SUMS
(覆盖全部附件含嵌套业务 manifest;根 manifest.json/SHA256SUMS/
manifest.sha256 三控制文件自排除)。所有执行在 fresh
/private/tmp(ppv1_s4_rework_r3_iso_20261008_222322 与 redgreen/
g01 副本),旧永久证据目录(含评审 R3 ppv1_s4_codex_r3_2026-10-08/)
只读零触碰。不访问金标/题面/封存逐题 run/dependingv4/原 v3 评价
资产;判分零 LLM;不 push。

## 9. 诚实边界(本批不声称的事项)

- 不宣称原 AtomTool 会编辑同位素(冻结 v43-editproto-2 无该 op;
  反例是合成工具返回的公共防御消费链,证明的是表示契约范围核验,
  不是工具行为或现实反应);
- 不认证实验/机制/同位素计量学/生物可行性/科学性能;工程测试数
  不外推 dev(298 题域标签保持);
- `self_contained_recompute` 证明自包含输入集确定性重算自洽,不
  证明"编辑曾被执行";
- retain_conditional 在生产链按已登记策略仍提交事件(轴结论如实
  violated/R5v);这是 S3b 起的注册行为,本批不改动该策略,如需
  缩窄须另行走用户裁定;
- 旧复合脚本早停未执行段/网络口径等历史事项不属本批范围,如实
  沿评审 R3 §6 登记口径引用,不重跑凑数。
