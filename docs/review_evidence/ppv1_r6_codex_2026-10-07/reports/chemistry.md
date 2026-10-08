# R6 化学专项独立只读复审

日期：2026-10-07。仓库 `/Volumes/CC/Enzyme_Agent/dependingv43`；锁定 HEAD `6d9020130a481866ce2f3b79933907a33d8cfc9e`。读 AGENTS、R6 delivery、mimo R6 全文、R5 主复审及规格 §17。原仓源码、测试、文档未改；无金标、题目资产、封存 runs、模型调用或真实路径实验。所有证据仅写本目录；Python `-B`，`PYTHONDONTWRITEBYTECODE=1`。

## 1. 确认修复的旧项

R5 新化学 6 条、旧边界 17 条及旧化学 40 条 JSONL 记录全部在当前 HEAD 复跑，无异常记录。记录包含 metadata/对照，不是 pytest 通过数；复用脚本内旧 HEAD 常量保留原样，实际运行身份以 `run_metadata.json` 为准。

- R5-08 已关闭：真实 `render('C/C=C/C')` → `execute_edits(break U_C_1–U_C_2)` 得 `C.C=CC`，现在 `declaration_mismatches=[]`、strict/center 都 True，实际 diff、镜像 diff、镜像重解析 diff 完全一致。远端断尾、双键降级和断双键正控同样一致。实现是 `/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/audit.py:2240`–`:2243` 的镜像终态写出—重解析，冻结 executor 未改。
- live ID、错误 from_order 及序列净效应保持关闭：先新增后引用、先新增后改键正确；错误前置键级报 `declared_precondition_violated:bond_order_mismatch`；`single→double→single→double` 正常无失配。
- E/Z 真实翻转的接口合成仍被检出：零编辑 E→Z 和远端编辑后再篡改 E/Z 均产生声明失配，未用忽略全部立体变化换正控通过。它们不是真实 AtomTool 执行了翻转。
- 指定手性联合位点假等价仍 False；合法优先级变化/远程 CIP 标签变化不误报构型反转。增强组身份规范化、公开串往返、混合 ABS、DATA 注记去除保持旧控制。
- 非四面体联合映射仍 unknown，公开 unsupported 原子清单与理由；真实配体集合改变的 unsupported 披露保持。不能把这些保护外推成完整非四面体支持，也不把配体集合改变强判保留/反转。
- R5-02 裸 `|r|` 与 `|Ln:1|` 在 build/strict 两入口现在拒绝，已登记的普通 atomProp/AV、逗号 DATA 等正控保持。下述残余不撤销这一修复。

## 2. C1 [P1] 已登记首头掩盖逗号并列的未登记类，build/strict 本身仍可静默丢事实

精准源码位置：

- `/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/chemstate.py:247`–`:248` 仅按空格拆块；`:266`–`:269` 首头命中 atomProp/SgD/Sg 就对整个块 `continue`。
- 同文件 `:506`–`:507`、`:583`–`:584` 两公开入口确实调用守卫，但上述分支让后续逗号并列类未经检查。
- 同文件 `:513`–`:534` 接受后仍缺省四轴 as_written，公开身份用解析后规范串。

最小公开输入：

```python
build_chemical_state('C[C@@H](N)C(=O)O |atomProp:0.note.hello,r|', 'raw_input')
strict_identity_of('C[C@@H](N)C(=O)O |atomProp:0.note.hello,r|')
```

实际：两入口都接受。RDKit 重新输出保留 atomProp、丢掉并列 `r`；工厂公开结构为裸 `C[C@@H](N)C(=O)O`，ID `cs_5110e7190bdbd9979a26`，四轴均 as_written。单独相同 `|r|` 被拒绝，是有区分力的负控制。登记的 atomProp 单独输入正确与裸串同身份。

同根变体均实际验证：

- `C1CCCCC1 |atomProp:0.note.hello,Ln:1|` 接受，与裸环己烷同 ID；Ln 仅证明未知/畸形块未防住，不称它代表合法的另一种环己烷物种。
- `CO |SgD:0:note:hello::::,r|` 及 `CO |SgD:0:note:a,b::::,r|` 接受，r 被丢，DATA 按登记移除。
- `CCCCCC |Sg:n:1,2,3:3:ht:::,r|` 接受，SRU 保留但 r 被丢。
- `CO |atomProp:0.note.hello,w:1.0|` 因 w 重写后仍存在而被输出守卫拒绝。故问题专门影响被解析器丢弃的后续类，不能以 w 控制通过证明原始类完整检查。

预期：按实际 CX 类边界检查每个原始块；同一未登记类不能因排在已登记头后面就静默放行。保持 DAT 值中的逗号合法，不要求粗暴逗号拆分，也不要求输入输出所有注记相同。

影响：R5-02 的原始入口保真缺口仍可从工厂/strict 进入；仅修第三入口不足以闭合。本例的科学结论是未登记的分子层非绝对/相对立体标记丢失，不能据此认定实验样品精确消旋，也不能把裸指定结构称实验纯品。`r` 的语义口径沿用 R5 官方 CX 格式核查。

验收：共享输入解析/登记器识别真正 CX 类起点及闭合字段，检查未知并列类，同时保护标签、属性、SgD 内容中的逗号/空格。对 atomProp/SgD/Sg 首头后并列 r/Ln 的公开入口补反例；保留普通元数据去除、SRU/增强组/自由基/映射号及往返正控。未知仍可拒绝或明确 unsupported，无须实现它的化学解释。

## 3. C2 [P1] donor 公共入口绕过原始输入守卫，自包含复算同样丢弃后达到 R6

精准源码位置：

- `/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/audit.py:2479`、`:2482`、`:2498` 分别直接 `Chem.MolFromSmiles` 解析 current、mapped product、plain product。
- 同文件 `:2517`–`:2518` 及 `:2738`–`:2741` 采用解析后 `_norm_smiles` 形成净变化身份和 bound_inputs。
- 同文件 `:2755` 保留原 current 串，完整性复算入口 `:691` 使用同一 checker，故两次相同丢弃会自洽通过。
- 同文件 `:2558`–`:2562` 只有 plain result/expected target 的 strict 分支走 guarded strict_identity_of，入口处理并不对称。

独立公开链：真实干净乙醇 AtomTool 键级编辑生成乙醛输出，然后只在诊断输入指定字段附加原始 `|r|`。调用公开 check_edit_against_donor → center_evidence_from_donor_diagnostic → audit_hypothesis → decide_admission。hyp 为配平 `CCO→CC=O+H2`、正常 condition context、非篡改 proof 轴。这是接口合成的原始 CX 违规测试，真实 executor 只负责产生干净基准结果；不冒称 executor 实际返回了带旗标的结构或存在实验反应记录。

| 诊断输入变体 | center / strict | 审核/准入实际 |
| --- | --- | --- |
| clean | True / True | verified，coverage full，R6 expand 正控 |
| current.smiles=`CCO |r|` | True / True，无 missing reason | bound substrate=`CCO`，verified/full，R6 expand |
| mapped product 尾附 `|r|` | True / True，无 missing reason | 同样 verified/full，R6 expand；指纹含原串但重算两侧同丢弃 |
| plain product 尾附 `|r|` | True / None | strict 明确 unknown，retain_conditional |
| expected target 尾附 `|r|` | True / None | strict 明确 unknown，retain_conditional |

为排除非手性乙醇里 r 的物质意义有限，另以指定手性底物 `F[C@H](Cl)CCO` 做远端 C–O 单→双编辑，并仅在诊断 current 附 `|r|`。实际原串保留在 proof_record，bound substrate=`OCC[C@H](F)Cl` 已无 r，diag True/True，审核 verified/full、R6；元素/形式电荷全账 verified。此处仍只证明原始标记被丢失并未阻断审核，不证明真实样品构成或该反应生物可行。

预期：所有消费原始字符串的诊断字段均走同一注册感知入口。拒绝该表示或给结构化 unknown，使该证据不能作为已核实中心进入 R6；可保留原串便于追溯。仅在规则文字登记“未设防通道”而继续把被剥身份用于 verified/R6 不满足旧入口验收。

验收：current/mapped/plain/target 未登记原始类一致处理；既有 clean 真执行、自包含复算的命题边界、合法已登记移除/保留、strict None/False 轴分工不被破坏。不能把自洽虚拟候选本身称假证明，也不要求运行事实证明或完整机制 checker。

## 4. C3 [P2] 登记类合法内容含空格被过拒，方向保守但不是未知类

来源是 RDKit writer 实际生成的合法输入，而非猜造畸形语法：

- atomLabel=`foo bar` → `CO |$foo bar;$|`；RDKit 原样重解析/写出；工厂/strict 拒绝，kind unregistered_cx_class、block `$foo`。
- atomProp note=`hello world` → `CO |atomProp:0.note.hello world|`；RDKit 原样往返；两入口拒绝 block `world`。
- DAT review_note=`hello world` → `CO |SgD:0:review_note:hello world::::|`；RDKit 原样往返；两入口拒绝 head `world`。

同一内容去空格及 DAT 内容含逗号均通过并与 CO 同 ID。根因仍 chemstate.py:248 的空格拆块和 :251/:259/:295 的类判断，未遵守已登记闭合字段/值域。

这是保守过拒和理由归类错误，没有证明错误 expand；不另升为化学 P1、不要求扩大到新 CX 类。应修现有类词法或准确登记当前内容限制/unsupported，不能说这些 writer 输入本身非法或属于未登记类。可与 C1 的语法感知解析同修。

## 5. mimo R6 采纳边界与覆盖范围

- 其关于 R5-08 两处旧表态撤回成立；本审旧 6 条独立翻转证明自然 E/Z 消失已正常闭合。from_order/netchange/non-tetra 旧保护保持。
- X1/X1b/X2 第三入口结论独立成立；本审补充 mapped 输入达到 R6 及指定手性底物正交对照。plain/target 变体只 unknown/retain，不能夸称同函数所有字段都能 expand。
- Y1/Y2 空格过拒独立成立；本审补充 writer 生成 DAT 含空格。是现有登记类词法问题，方向保守。
- 不采纳其“输入登记类划分及默认拒绝已完整同意”：C1 证明 atomProp/SgD/Sg 之后的常规并列未知类未查。保护 DAT 内逗号不等于整个首头块可以免查后续 CX 类。
- SgD 注记适配器前提应明确。源码身份函数已按 DAT 类型视注记，但请求文本 `docs/mimo_ppv1_chem_review_request.md:58` 只有内容不查/逗号机制句；delivery 声称前提已落字需校正。该文档一致性问题不新增一个已证实化学丢失的 P1；不能把全部 SGroup/SRU 当纯注释。
- coverage/proof 主审另审。本专项经原 R5-01 验收及规格 §17 范围校核：composition-only 的计量补全可以明确限定范围，不能替代未覆盖复杂共底物初始图的变化核实。主审 C→CCCO 证据应用于不同 C2H4O 共底物的案例，是未核初始内部键仍被称全覆盖的残余；最小约束是注册明确结构身份/角色/贡献与补全 scope，未登记复杂多原子贡献保留 partial/unknown 或另核其初始图，不要求 S3 full_template/机制库。H2 对 2H• 仅作为 composition-only 作用域对照，不能据此要求本轮新增电子/自由基轴或证明实际路线不可行。该判断不是本专项独立复跑主审探针的程序证据。

## 6. 文件、复跑与放行

完整目录 `/private/tmp/ppv1_r6_chem_6d90201_TFsVC1/`。

| 文件 | 内容 |
| --- | --- |
| `cx_boundary_probe.py` / `.output.jsonl` | 本次 9 条 JSONL，含 metadata、两个输入矩阵、6 个 donor 公共链对照；完整入参、diag、hyp、audit、admission |
| `r5_focused_replay.py` / `.output.jsonl` | 原 R5 新 6 条记录，含自然 E/Z 修复翻转 |
| `r4_boundary_replay.py` / `.output.jsonl` | 旧 17 条边界记录 |
| `r3_probe_replay.py` / `.output.jsonl` | 旧 40 条化学记录 |
| 各 `.stderr.txt` | 完整 RDKit 原生标准错误 |
| `run_metadata.json`、`SHA256.txt` | 固定 HEAD/命令/版本/记录统计及哈希 |

复跑（替换文件名即可重跑另外三份）：

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/Volumes/CC/Enzyme_Agent/dependingv43/src /Users/cc/miniconda3/envs/depending43/bin/python -B /private/tmp/ppv1_r6_chem_6d90201_TFsVC1/cx_boundary_probe.py
```

本专项认可 R5-08 及已修旧项，但 C1/C2 仍阻塞原始身份消费闭环，不建议放行 S3。C3 为保守过拒，不以此扩大阶段功能。没有重复完整套件，没有改冻结执行器，没有将尚未接线的新流程误报为 legacy 模式改变。科学性能继续 pending；合成程序夹具不构成污染物路径泛化或实验可行性证明。
