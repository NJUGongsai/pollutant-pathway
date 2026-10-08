# R8 独立化学/state 专项复核（2026-10-07）

**专项结论：R7-01 关闭；未发现该既定验收内剩余 P1。** 本专项不裁定存储 R7-02、不替主审认证 PPV1/G01/基线数字；mimo v8 八项条件属已有边界的规则措辞精度，④优先更正文案归属，均不能凭缺一句话重新制造 S3 功能门。

## 1. 范围、输入、执行纪律

固定 R7 主报告 §4 R7-01 最低验收及 §7/§8，不扩大机制、电子轴、支持类型、科学性能或未来展示接口。已读当前 AGENTS、R7 主报告相关段、R8 交付书、mimo v8 回应和实际请求 `docs/mimo_ppv1_chem_review_request.md`、本轮 chemstate/audit/store diff 和新增化学回归。真正当前源码 HEAD=`00e509a974b40a7c9779fcd35e53b16637a13d60`，父=`858dd94c7c6c8fc387940242403d67b6b36b5313`。

所有执行只在新临时目录 `/private/tmp/ppv1_r8_chem_00e509a_oblgdx4_`，完整 src（含 vendor）和 pyproject、两份普通 helper tests 隔离复制，禁 Python 字节码。不跑 pytest、不触永久证据、源码/测试/既有 docs/AGENTS；无金标/题面/封存数据访问，无模型、网络或推送。RDKit 实际版本见 metadata.json/JSONL metadata，schema=`ppv1-chemstate-8`。原 R7 探针内 expected_source_HEAD 保持历史值，不当当前 HEAD；本专项 metadata.json 和静态输出钉实际 HEAD。

## 2. 源码与公开链闭合

- `chemstate.py:630–650` from_dict 校版本/fidelity 后调用 `validate_state_object`；`audit.py:474–475` 在任何检查或处置前对传入 states 逐个同验；故直接 `ChemicalState(**payload)` 不豁免。
- `chemstate.py:754–910` 纯对象验证涵盖原契约：schema、origin、fidelity 全轴、CN-only 专用身份及未知事实、结构可得、canonical/state_id/电荷/CN/立体/同位素同工厂重推导、raw 必填并 strict 重推身份一致。raw 未登记项先拒，不通过删除 raw 后冒充 full。
- writer `store.py:377–540` 仍有单独包装实现，和新增函数共享 **build_chemical_state / strict_identity_of / _validate_fidelity 的事实源**，判据内部可确定语义相同。这里的“同源”是契约一致性，不是独立双算，也不要求本轮改成一个包装函数才放行。
- 最小公开链保持真实冻结 AtomTool 乙醇氧化证明；只改 state raw，恢复与直接对象两路均 `ChemicalStateError`，无 audit/admission 返回。底物 CCO、产物 CC=O、未覆盖 H2 的 raw 加 r 皆 `raw_structure_rejected`，reason.kind=`unregistered_cx_class`；H2 raw 改 CC=O 为 `raw_identity_mismatch`；指定手性表示的远端氧化同样两路拒。相同载荷 writer 拒绝、counts 不变。
- state_id/CN/formal_charge/stereo/isotope 不符都首次拒（`state_fact_rederivation_mismatch`）；未知 origin 和 schema 亦拒。只是检查已有内部事实，没有声称来源真伪、历史执行或生物可行性。

## 3. 实际输出、正控与历史保持

1. 冻结原 R7 化学探针原样复制执行：**55 条顶层 JSONL，exit 1**。在原第123行未包 capture 的手性 `from_dict` 新拒绝停止；尾部手性 raw case 与 CN-only case 不在原日志，不冒称57条全执行。正控和原始55条内捕获拒绝按 `assert_r8_chemical_observed.py` 判行为。
2. 新拆分公开矩阵：**60 条顶层 JSONL（1 metadata +59 case），exit 0**。补齐手性 raw 与 CN-only，覆盖恢复/直接 dataclass 两消费路及 writer 对照；合成输入/payload/hypothesis/proof/audit/admission 或结构化异常原文均记录。记录数不是漏洞数。
3. 修后期望断言 **exit 0**；static inventory **exit 0**。原 R7 `assert_chemical_observed.py` **exit 1**，首先因旧 `len(rows)==57` 失败，未执行它后面的缺口断言；不能称旧观察断言逐个钉住翻转，逐案翻转由新断言证明。
4. 合法 CCO clean、raw OCC/canonical CCO、atomProp 空格、SgD 含逗号与空格、label 空格、指定手性正常链均恢复/直传 **R6 expand**。CN-only 两路 **retain/identity unknown**；archive absent_in_archive 两路保留 **retain/identity unknown**。
5. 已支持保留类正常 SRU、两种 enhanced group、三种 radical 分隔形状，共 **6**，在当前锁定版本均 writer/reparse 稳定、same strict ID、不同 bare ID；新增 `ChemicalState.from_dict` 验证也保留同ID。移除类3形状（atomProp/SgD/label）仍同 bare ID；SRU四个含空格/逗号/escape/双group形状仍被原输出守卫保守拒绝，为 R7 已登记 P2，不是新的 unsafe R6。RDKit 原子索引重排及对象内存地址不当成事实丢失。
6. R6-01 三个 C2H4O 初始图仍 center unknown、detail.product_coverage=`partial_unchecked_transformation`、retain；不能只看外层 check.coverage（它是 mapping_dependent）。
7. 判据五四原始字段在 execution_ok=True 时均 AuditContractError，不返回诊断/处置；False 路径保持执行失败早退。具体 **三个**判定字段 reaction_center_match/strict_target_match/legacy_cn_match 均 None，diagnostic.center_evidence={}。`center_evidence_from_donor_diagnostic` 的转换 dict 并非空：有版本/来源元数据且 center_match=None。mimo“全四轴None”及笼统“evidence为空”应按这一实际形状精确更正，安全方向不回退。

## 4. canonical 加 r 三例的裁定

canonical CCO、CC=O、H2 追加 `|r|`，恢复与直传共6路现在拒，和 R7 retain 的控制流不同，但 R7 最低验收明确允许“拒绝或诚实 unknown，不R6”，因此 **无回退、无新P1**。

上层错误 kind=`state_structure_unparseable` 不等于 RDKit 本身无法解析，也不等于输入真实化学非法；底层是 build 工厂输入守卫 `reason.kind=unregistered_cx_class`。该上层包名/交付“结构不可解析”文案应精确说“未通过身份重推导入口守卫”。不从 r 推断实验消旋或样品纯度。

## 5. mimo 八项落字条件

| 条件 | 独立裁定 |
|---|---|
| ① r拒绝不反推含义移入规则 | 现位于“请评审”段，正文升格可取；拒绝事实不认证化学含义，P2文字 |
| ② 同源非独立双算 | 代码共享工厂/strict/fidelity事实源，两个包装实现；补括注准确，P2文字 |
| ③ 判据二入口限定 | 当前 audit 首消费同验已实证；声明依赖首消费验证应点明，P2文字 |
| ④ scope字面/归属对齐 | 请求称scope文本有“本许可不区分…键断裂…电子去向”，**代码实际字面未含该句**。实际scope写registered:composition_only_hydrogen_equivalents、H2/[H]按2[H]、数值配平不证明未登记多原子共底物初始图贡献。mimo此项读码正确；优先追加字面或把归属改成规则文本，不是新增化学功能/P1 |
| ⑤ 恒入不等于适用 | licensed-H2 full与没有未覆盖参与物full（后者故意省H2、元素轴拒）都携scope，公开链实证字段存在≠许可已用。推导必须结合product_coverage=full、uncovered_*非空、unlicensed列表空；license_applied/top-level/UI依既有裁定P2 |
| ⑥ frozen与内容哈希分写 | Requirement/ConditionFact frozen和PathContext非frozen+消费前内容验证的区别读码属实。条件链执行由主审另线核验；文字应分写，不因可变类型本身加门 |
| ⑦ None不是通过 | 当前失败诊断三判定字段None，中心证据未执行；如上精确更正轴数和converter dict，P2文字 |
| ⑧ 异常承担方 | 当前 src 无audit调用方，donor复算唯一调用无try包覆，守卫拒绝逃逸；未来调用方不得吞异常的职责落字可取，P2文字 |

这些是化学说明的建议/文字修正，审核方不能只因句子未入当前规则就重开已闭状态 P1。契约/判据是否正式冻结由主审按既定流程记录；本专项没有替任何人宣布科学性能已验。

## 6. grep与宽捕获完整性

基于隔离完整 src 的 AST + literal grep 已执行并完整记录：

- 全 src **2** 个 `ChemicalState(...)` 实际调用均在 chemstate 的结构/CN工厂；**0** 个 `.smiles_isomeric` / `.structure_smiles_raw` 属性赋值；**32** 个 MolFromSmiles 实际调用。
- pollutant 解析入口：工厂/strict先守卫；audit _mol_of 消费已验证states；_elements_of 消费已绑定/strict查过的身份；供体三个原始解析在四字段守卫之后；_simulate_declared_edits 解析本模块已构造终态并宽捕获为诊断未知；substrate_profile 消费canonical、只产profile不产verified。events/legacy经工厂归一。
- 外围 adapters/domain identity、services analog_source/donor_applicability/冻结AtomTool、conservation、gold_health及vendor 的解析属既有外围/诊断/渲染，不是PPV1 state/admission绕过入口。本专项只看它们的普通源码，不执行gold_health或评价数据读取。
- `rg -n 'except AuditContractError' src` **rc1、stdout空、stderr空**，mimo这一读码结论证成。
- AST找到 **10** 个 AuditContractError raise，**无一个处于捕获 Exception/bare 的 try body**。四原始字段守卫包装raise在 ChemicalStateError handler内（其自身try不捕获handler再抛异常）；donor唯一复算调用 audit.py:746 **无 try祖先**；guard audit.py:2584 与该复算链无宽catch包覆。未来重构风险不等于当前已吞异常。

## 7. 附件与复跑

`run_commands.json` 登记实际命令/工作目录/rc/输出；`metadata.json` 登记HEAD、schema、Python/RDKit、源文件/夹具SHA；`static_contract_inventory.json` 是完整AST证据；`SHA256SUMS` 保全本专项可交付脚本/日志/报告/元数据（不含庞大临时src和临时SQLite库）。只复制到全新tmp再执行，见README。源码隔离副本/SQLite不是仓内交付修改。

本专项冻结到此，不再扩边探查。主审核仍须独立裁定R7-02及全量/基线/G01和历史五组；没有把专项通过冒充整轮放行。
