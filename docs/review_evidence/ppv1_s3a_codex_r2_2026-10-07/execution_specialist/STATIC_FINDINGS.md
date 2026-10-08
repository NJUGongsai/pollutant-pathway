# S3a-r2 窄化学复核与 mimo r10 精度核对

实际 HEAD `dcb7ed62bd4271cfa7bde2732dc0b4fdd0360d03`，直接父基线
`9b78f4279cc6fa50b3b51c31a5c8e07abbeda207`。本文件只核现成化学契约、源码描述和已执行小控制；不增加机制、真实来源、科学性能或 S3b 门。

## 实际执行

`chemistry_probe.stdout.jsonl` 保存一次窄探针完整 15 cases 与 `assertions=complete`，退出 0，墙钟 1.118 秒。历史脚本先复制到本次 scratch；只把硬编码的 runner 改动列表改为实际字节比较所得，并加入实际 HEAD/父基线。两份 baseline 输入用本次 `git show 9b78:...`，适配全文差异在 `chemistry_adaptation.diff`，没有更改化学输入和期待。runner 小正控与先前工程控制重叠，不作相加。

- `raw_r`：RDKit 可把 `CCO |r|` 解析并写成 `CCO`；恢复和 writer 均拒，writer 零写入。恢复外层 `raw_structure_rejected`、内因 `unregistered_cx_class`；writer 外层为其 raw 守卫包装 `raw_structure_unparseable`，具体 detail 原文留存。
- `canonical_r`：恢复/writer 外层均 `state_structure_unparseable`，内因均 `unregistered_cx_class`；不能把外层包装名称误读成实际语法必然非法或样品属性结论。
- `canonical_bad`：恢复/writer 同一外层包装，内因 `unparseable_smiles`；实际 RDKit 解析失败。
- 执行失败诊断的 strict_target_match / legacy_cn_match / reaction_center_match 均为 None，center_evidence 为 `{}`；converter 无 checker_scope/proof_record，center_match=None；公共 audit 的 transformation_center 为 unknown，原因 `center_checker_scope_unknown`。没有把失败归作中心相合、化学否定或 verified。
- 九个既有 CX 小控制完整保存逐输入、canonical 重解析与身份比较，保留首轮已登记的文字/坐标/增强立体/自由基控制。其结果只证明锁定运行版本的小输入契约，不认证样品或未登记类别。

实际运行版本为 Python 3.11.16 / RDKit **2026.03.6** / SQLite 3.53.4。mimo §6 的 RDKit 2025.03.1 与本次环境不符；`655c7e8` 不是本轮红基线。本审未执行其所谓既有 2 failed /79 passed；直接父基线只执行本轮新增同字节 54 项，分类见下一节及 `baseline_case_classification.json`。

chemstate / audit / path_context / hypothesis / events 五源对 9b78 全部字节相同，五对 SHA 在 `static_precision_inventory.json`。profile/search 的版本与实际新库 meta/schema 另见 current_runtime / baseline_runtime 输出；旧源码脚本字符串不作实际 HEAD。

## 基线红绿分类的必要更正

裸 pytest 结果为 52 failed /2 passed /0 collection error，不能直接写成 52 个完成全段的行为反例：

- 48 项在正确行为的拒绝/状态/停止断言上失败。
- B3 run/parent/context 三项在返回 disposition 为字符串处发生 TypeError，后续内部断言未执行。
- B3 hypothesis 一项在正常 submit 已拒绝、旧 reason.kind 与新预期名称不同处先停；该测试的 B3 恢复段未执行。
- 两项正控完整通过：合法未执行 defer 释放；非 expand decide 的合法空 attempt 请求。

`baseline_case_classification.json` 对 54 项逐 node 记录失败行、原文和后续未执行断言，不把形态失败与行为失败混报。`retryfoo` 不在本次新增测试文件中；本审没有复用历史更新既有测试的早停结果。

额外四案使用独立 capture，不改原测试：普通提交拒绝后仍继续跑 B3、记录全部表。父基线四案都 event=1、commit=1、action done/预约已 consume；当前四案都 event=0、commit=0、action 保持 claimed，artifact 保全，结构化记录 `bundle_event_identity_not_frozen`。这是独立补充的完整行为证据，不能反过来声称原测试后半段已经执行。

## mimo r10 哪些读码声明需更正

1. **AuditContractError 分布错误。** 整个复制 src 中 10 个抛点全部在 `pollutant/audit.py`，实际行 464、739、1076、1110、1589、1596、1603、1607、2547、2584；mimo 所述 search×2/context×2/profile×1/store×4/audit×1 被现源反驳。src 与白名单完整 tests 的显式 except AuditContractError 均为 0；所有 10 点未处在包覆的 broad catch try-body。扫描不为未来 S3b caller 的动态异常逃逸背书，也不外推未复制 scripts/tools。
2. **未知 checker_scope 不抛。** audit.py:1064–1070 添加 `CHECK_UNKNOWN`、`center_checker_scope_unknown`；不是 mimo 所述 AuditContractError。类型违约/自报与复算不符是另两条结构化异常入口。
3. **判据五大量“读码确认”对应不存在的代码。** donor_present、donor_element、donor_charge、donor_consistency、_walk_conversions、same_cid、graph_simple_iso、formal_iso、conversion_warnings、donor_ligand_context 等 24 个术语在当前完整 src 中全 token 计数均为 0。清单和每个引行的实际源码在 `static_precision_inventory.json`；这些段落和据此推得的额外路径、WARN/CRIT/步数/固定处置不采信。不能据此新增未实现机制或转化库门。
4. **真实边界保留。** DonorConsistencyDiagnostic 的现有 docstring 确实写明不核验供体反应自身变换模板、图等价不等于酶识别或机制等价；legacy_cn_match 只旁证不进计数，失败返回三个 None；audit_hypothesis 在 src 中仍无生产 caller，S3b 接线与 caller 正常/异常路径尚未交付。这些与程序证据相符，继续诚实披露。

## 判据四和 known_absent 的有限文字裁定

- **孤儿方向的意见成立。** 旧作用域的累积要求没有历史快照按签名承载，assess_candidate_conditions:1245–1268 生成 orphan_binding/unknown；反方向“快照签名不在累积要求中、签名与逐行集合不对应”在 :1470–1499 结构化拒。v10 把“评估行无对应要求”写成 unknown，方向和处置均需改字。源码循环累积要求，不借此增加本轮功能门。
- **入口全称需限定。** derive_child_context 先 validate 父对象；from_dict 有同款版本/快照/内容身份门；audit 先 validate 直接 context 对象。assess_conditions、assess_candidate_conditions、route_assessment 本体均无 validate_context_object 调用，依赖上游合法对象。mimo 的此项静态限度正确；不能把纯评估函数不存在的校验说成已强制，也不由本次窄探针声称新增的未 validate 对象绕过矩阵已执行。
- **合法重建保留。** :2403–2418 派生建立新内容身份并令 parent_context_ref=parent.context_id；原对象就地改语义仍保留原 ID 会被同源身份门拒。不能把“能重算 ID”直接当损坏可洗白，也不能要求全面拒绝合法新内容。
- **known_absent 三标签没有代码枚举对应。** registered_missing/documented_absent/unrecorded 在现源全 token 为 0；只能标作规则层描述或换成实际理由码。实际实体自身 known_absent→required_entity_known_absent；非物种字符串同值→required_value_known_absent、异值→other_value_known_absent_not_determining；数值/区间缺席还有 numeric_absence_semantics_undefined 的 unknown 分支。不能把三句压成穷尽所有值域的规则，也不能因事实未列出便推 known_absent。
- **系数两类问题分开。** 零/负/bool/非有限/known-null/unknown有值等表示契约在构造/提交边界拒绝；R2b 需要 caller 将异常 detail 明确传入 contract_violation，源码没有自动映射。coefficient_binding_mismatch 是覆盖轴违例，不自动成为表示层 R2b；可造成覆盖 partial/中心 unknown，最终 disposition 仍由其他轴与规则优先级共同决定。mimo 写成固定 partial→R5/retain 的说法不可扩大采纳。

本审未冻结判据，不修改源码或已有文档。工程通过、小控制和静态纠错均不代表 dev(B1 环境中间步骤)或 298(RHEA 通用酶学)科学性能。
