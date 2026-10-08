# 污染物降解路径架构 S0–S2：Codex 第六轮独立复审（R6）

审核日期：2026-10-07。仓库：`/Volumes/CC/Enzyme_Agent/dependingv43`。锁定 HEAD：`6d9020130a481866ce2f3b79933907a33d8cfc9e`；R5 对照：`293bc627f57b1f778aa433750f7f61d00b4a9d18`。

**结论：R6 有实质修复，仍不放行 S3，不冻结化学判据或契约。** 独立隔离回归 **451 passed、0 skipped**；R5 原反例基本翻转。仍有 **5 组 P1**：计量补全泛化成未核实复杂共底物的结构覆盖；原始 CX 注册在并列类和诊断入口两处不闭合；派生子上下文能洗掉旧必要未知；既存 state/appearance 首次使用漏验；同 state 多来源的 manifest 删项漏检。

这些是当前 S0–S2 已支持公共入口的同源性和完整性缺口，不是要求提前实现 S3 搜索、完整机制库、电子/自由基新轴或科学性能评测。下一轮应按 §6、§8 的有限范围收口。

## 1. 证据范围与独立执行

读两份交付全文、架构实施书 §17、R5 审核及实际改动；化学、条件、存储三线分别复核，主审再独立执行新探针，并完成附件复跑器的 12 份探针入口及观察断言。源码和既有资料只读，只新增本报告与合成证据。未读金标、真实题面或封存逐题 run，未调用模型、未运行真实路径或付费实验。Python 使用 `-B`、`PYTHONDONTWRITEBYTECODE=1`；测试禁用 cache，数据库和损坏模拟均在新建临时目录。准入夹具显式给出通过的方向/来源 gate 合成结果，以隔离 audit 轴，不代表真实路径已通过冻结门禁。

| 执行 | 独立结果与解释 |
| --- | --- |
| 16 个 PPV1 测试文件，源码/测试隔离复制 | 专项 **451 passed、0 skipped，1 warning，3.91s**；主审复跑器再执行 **451 passed、0 skipped，1 warning，4.37s**。不相加为新增测试数；warning 为化学模块文档字符串无效转义 |
| 当前 R6 新增 70 项对 R5 源码 | **44 failed、26 passed，1 warning，1.33s**；只在临时测试替换缺失常量的 import 为同值字面量，不改 R5 源码 |
| 主审覆盖探针 | 14 条 JSONL：旧覆盖与正控 9 条、真实新增原子诊断 1 条、复杂共底物 3 条、自由基作用域说明 1 条 |
| 化学新边界 | 9 条 JSONL：metadata、两个输入矩阵、6 条完整公共诊断→audit→admission 链；主审独立复跑，无顶层异常 |
| 条件新边界 | 10 个分开案例：合法历史、直接审核/恢复拒绝、签名成员控制、派生残余和真实未知保留；主审独立复跑 |
| 存储新边界 | 17 个 case + 1 条 metadata；主审独立复跑，全部符合专项报告的观察 |
| 旧专项探针 | 化学 6+17+40 条；存储 9+21+29 条；条件 7+19 个顶层案例。条件旧复合函数在预期拒绝处停止，未把内部未执行后半段算通过，新分段案例补齐关键控制 |

记录数包含 metadata 和正负控制，不能当失败测试数。基线 44 项失败包含 7 个 KeyError，其余是断言不符或预期异常未抛；其中已有正确粗粒度行为的正控也因缺新披露字段失败。因此 **44 红不等于 44 个已修科学漏洞**，交付中的行为/字段分类须结合逐条日志理解。本审认可红绿总数，不用它替代公共链反例。

交付及 mimo 报告的全量 **1062 passed / 16 deselected** 是外部执行声明，本审未重复该套件；也没有新跑 G01/298 或外推 hit60、路径泛化和污染物实际降解性能。新流程接线、科学性能和后续阶段仍依实施书登记。

永久证据：[README](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/ppv1_r6_codex_2026-10-07/README.md)。包含脚本、完整输入/诊断/审核/准入输出、测试与基线日志、专项报告、复跑器及 SHA-256 清单。复跑器复制到新临时目录；不要在永久证据目录直接运行会创建数据库或覆盖结果的脚本。附件 `assert_observed.py` 钉住 **R6 当前观察**，故包含当前缺口成立的断言，不是修复后的验收期望。

## 2. R5 修复裁定

| R5 项 | R6 独立确认 | 裁定 |
| --- | --- | --- |
| 01 单侧覆盖/系数 | 原 1/2 乙醛+1/2 环氧乙烷、额外共底物生成同产物均 unknown/retain；系数、碎片重数、两侧元素补全已披露 | 原例修复；补全适用范围见 R6-01 |
| 02 原始 CX | 单独 `r`、`Ln` 被工厂及 strict 入口拒绝，已登记元数据控制保持 | 原例修复；并列类与 donor 原始入口见 R6-02 |
| 03 known_absent | 同值 oxygen/matrix absent→conflict/defer；数值 absent→unknown；异值不凭空决定；物种 absent 保持 conflict | 关闭 |
| 04 历史快照 | summary/has_gate 篡改在恢复及直接 audit 拒绝；事实变更保 ID 拒绝；合法历史往返保持 | 原例修复；derive 和覆盖签名对应见 R6-03 |
| 05 出现清单 | 全量/部分先存现在绑定，唯一物种清单缩短拒绝；多既存出现缺依据零写入拒绝，明确提供可通过 | 原例修复；首提已存事实和同 state 多出现完整性见 R6-04/05 |
| 06 已有假设首用 | 内容重推 ID、inner ID、schema 和参与物契约都拒绝损坏；合法先存保持 | 关闭，含 ID/inner ID/行键同源但 entry_id 错的独立控制 |
| 07 同父兄弟来源 | 确定性 product path 锚检出错兄弟，降 CN-only 并披露原因；正确来源保留，旧库字节不变 | 关闭 |
| 08 自然 E/Z 消失 | 真实相邻断键后实际与镜像终态重解析一致，零声明失配、True/True；真实立体差异保护保持 | 关闭，不要求改冻结执行器或新增立体 op |
| P2 proof/basis、循环分轴 | scope/basis 机器披露及篡改拒绝；initial 与 reaction/regeneration 支持分别消费，跨轴不污染 | 原控制关闭 |

live ID、from_order、序列净效应、指定手性联合位点、合法 CIP 优先级变化、非四面体 unsupported 披露、单位未知、正常阶段转换、排序幂等、CN-only 降级及 off/空计划等旧保护保持。不能将上述关闭项在下轮重新算成未修，也不能以旧字符串翻转推断所有消费入口都闭合。

## 3. 仍阻塞的 5 组 P1

### R6-01 [P1] 计量补全不限参与物结构/贡献范围，复杂共底物未核初始图仍 full/R6

位置：[audit.py:886](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/audit.py:886)、[915](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/audit.py:915)、[928](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/audit.py:928)。未覆盖参与物只贡献元素总数；两侧与 Δ 的正负部分相等即授 `product_coverage=full`。注册常量 `atom_delta_stoichiometric_completion` 没有限定哪种严格结构、角色或贡献可以由该规则补全。

真实 AtomTool：甲烷 `C` 依次新增 C、C、O，得到 `CCCO`。验证/执行成功，新增 ID 与中心映射完整，checker center/strict=True，未篡改 proof 轴。该执行 **没有载入、映射或编辑任何共底物初始分子图**。

| 审核声明，系数均 1 | 额外未核实的初始结构 | 实际公共 audit/admission |
| --- | --- | --- |
| `C + CC=O → CCCO` | 乙醛的初始 C=O 与连接贡献没有进入证明 | 元素/形式电荷 verified；center verified；full；R6 expand |
| `C + C1CO1 → CCCO` | 环氧乙烷的环键/开环贡献没有进入证明 | 同上 |
| `C + C=CO → CCCO` | 乙烯醇的初始 C=C 与连接贡献没有进入证明 | 同上 |

三者都是 C2H4O，恰好补足甲烷→丙醇的原子增量；Δ 数值绑定正确，却不能核实三种不同初始图的转化。strict 轴只绑定当前诊断的目标产物，**不自动检查所有未覆盖参与物的初始键变化**。证据自包含复算两遍仍不能扩大其证明范围。

这不是宣称三条路线化学不可能，也不是将 atom addition 本身视为假执行；问题是把局部图编辑及式量补全授为整条复杂转化的 full。R5-01 原验收已要求未核复杂结构转换不能凭集合/数值条件升 full，不是新增 S3 机制要求。

**有限验收：**补全许可绑定明确的严格结构身份/角色/贡献和适用 scope，或补足可确定复算的初始图贡献证据；未登记复杂多原子贡献保留 partial/unknown，不得 R6。规则 scope、依据与未核结构范围机器披露。保留正常氧化/还原中的明确计量补全、合法比例缩放及真实断裂分列/合并；不要求全部共产物走 AtomTool，不按名称一刀切免审/拒绝。`H2` 对 `2[H]` 只作 composition-only 的作用域控制，不以此另要求本轮实现电子/自由基轴。

### R6-02 [P1] 原始 CX 契约仍有两个入口缺口

**A. 工厂/strict 守卫只认首头，后续并列未知类未经检查。** [chemstate.py:247](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/chemstate.py:247) 按空格拆块，[266](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/chemstate.py:266) 首头为 atomProp/SgD/Sg 就整块放行。

公开输入 `C[C@@H](N)C(=O)O |atomProp:0.note.hello,r|`，工厂与 strict 都接受，原始并列 `r` 被解析器丢掉，与裸串同身份、四轴 as_written。单独 `|r|` 正确拒绝，普通 atomProp 正确按注记移除。`SgD:…::::,r`、`Sg:n:…:::,r` 和 atomProp 后并列 Ln 同根漏查。保留 DAT 数据内部逗号不能作为整块免查后续类的依据；不要粗暴逗号 split 破坏合法 DATA。

**B. donor 诊断直接 parse 原始字符串，绕过工厂的输入守卫。** [audit.py:2479](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/audit.py:2479)、[2482](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/audit.py:2482) 直接解析 current 和 mapped product；[2738](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/audit.py:2738) 用解析后的规范串绑身份。

真实干净乙醇→乙醛执行结果作基准，**仅在接口指定原始字段加 `|r|`**，再走公开诊断→evidence→audit→admission。current 或 mapped product 加标记均 True/True、verified/full/R6；复算同样剥掉后自洽。proof 保留原串，但 bound substrate/product 已失去标记。指定手性底物 `F[C@H](Cl)CCO` 的远端氧化，仅在 current 加标记，同样 R6。plain product/expected target 加标记则 strict=None、retain；不夸称所有字段都误放行。

本例证明未登记原始事实静默丢失，不能推定实验样品精确消旋、裸结构实验纯度或真实生物反应成立。[RDKit 官方说明](https://www.rdkit.org/docs/RDKit_Book.html#cxsmiles-cxsmarts-extensions)仅承诺解析/写出扩展功能子集，写出缺某块不足以证明输入保真。

**有限验收：**所有消费原始字符串的 current/mapped/plain/target 与工厂/strict 共用注册感知校验；按实际 CX 类边界逐类检查，未知类拒绝或明确 unsupported/unknown，不能经剥除后作为 verified/R6 证据。保留已登记标签/属性/DAT 去除、增强组/自由基/映射号/SRU 保留与往返控制。无需解释新 CX 类，不改冻结 AtomTool。

### R6-03 [P1] derive 未验父身份，合法签名可掩盖被删除的历史必要评估

位置：[path_context.py:2250](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/path_context.py:2250) 派生入口不验证父对象；[2361](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/path_context.py:2361) 重算新 child ID。[1408](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/path_context.py:1408) 必要键/旗标只从现有评估行派生，[1443](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/path_context.py:1443) 签名只检属于累积要求，不检对应评估实际存在。

合法 p0 必要 pH 6–8、事实缺失为 unknown；转 p1 当前有氧必要条件满足，旧 pH 快照使审核 retain。只将父快照 `per_requirement=[]`、coverage 各键列表清空、`has_gate_requirements=False`，**保留旧 pH 的真实要求签名，摘要仍 unknown**。直接 audit 父正确报 `context_content_identity_mismatch`；public `derive_child_context(parent)` 不传新事实/要求/转换却生成合法新 ID，旧 pH 不再参与门禁，audit verified/R6。child→dict→from_dict 后再审也 R6。

凭空签名负控正确拒绝；本残余用的是现存合法签名。未改历史的 unknown 保持 retain，合法 conflict 往返保持 defer、合法 satisfied 保持 expand。

**有限验收：**派生入口先使用与恢复/审核同源的父内容身份与快照验证；历史覆盖的具体要求签名须对应已记录评估和必要覆盖，不能仅证明要求存在于累积列表。保留历史原评估，不用当前事实重评旧边；保留合法 unknown 摘要及正常转换。这里不认证用户事实真实性，不要求防住完全重造自洽历史；只要求现有可检测损坏不能被公开派生 API 再认证。

### R6-04 [P1] 首次引用已存 state/appearance 只验存在性，成功后重放才报损坏

位置：[store.py:1505](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/store.py:1505) 首提只核本次 states，[1507](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/store.py:1507) 缺本次载荷的 state 只查存在；[1532](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/store.py:1532) 唯一既存 appearance 只读 hash，不核内容。现有事实/hash 校验在 [1424](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/store.py:1424) 重放路径执行。

先 public put 合法 CCO 与 CC=O，再只在新建合成 SQLite 损坏一个字段，public 首提 `states=[]`、假设正常：

| 已存单字段损坏 | 首提实际 | 紧接无重复输入重放 |
| --- | --- | --- |
| 产物 CN 改 CCN，结构仍 CC=O | created=True，事件/投影/计划新增 | 正确报 state_row_corrupt |
| state schema 改未来版本 | 同上 | state_schema_corrupt |
| state inner ID 与行键不符 | 同上 | state_inner_id_corrupt |
| appearance source_refs 改、hash 不改 | 同上 | appearance_hash_corrupt |

有效先存的首提/重放正确；已有 hypothesis 四项校验正确。故本项不是否定 R5-06 修复，也不声称公开 put 能直接写错误数据。问题是受支持首提入口复用已损坏行，校验被拖到第二次调用。

**有限验收：**首提复用既存 state/appearance 立即共用事实、版本、身份和内容 hash 校验；上述错误首提零新增事件/投影/计划，明确 LedgerCorrupt，不自动补账。保留合法全量/部分先存、正常首提与重放。无需新迁移或真实来源认证。

### R6-05 [P1] manifest 用 state 集合代替完整 appearance 集合，同图多来源删项漏检

位置：[store.py:1254](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/store.py:1254) 只核 manifest 的 state_id 集合；[1001](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/store.py:1001) event 语义 hash 不包含 manifest。首提明确允许同 SID 不同 hash 分别保留（[1557](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/store.py:1557)）。

合法公共首提 `[底物, prod-A, prod-B]`：A=`CC=O`/refs A，B=`O=CC`/refs B，同 product SID、不同 appearance hash；manifest 3 项，正常重放成功。只在合成数据库删除 manifest 的 A 项，B 仍覆盖 product SID，无输入重放仍 created=False；再同时删除实际 A 行仍成功。**只删 A 行、保持原 manifest** 则正确报 entry_missing，是有区分力的控制。

这不是同 hash 重复输入，也不要求抵抗重造整本账本。未重算身份/hash/其他附件，只删除首提明确绑定的一项，说明完整出现集合没有独立完整性依据。原“删除唯一产物清单项”已拒绝，应认可；同物种尚有 B 不足以证明 A 从未属于事件。

**有限验收：**持久化可独立复核的完整 `(state_id, appearance_hash)` 集合/摘要，或等效同源校验，检测 manifest 删项及实际来源丢失，即使同 state 还有另一出现。保留同图多来源、正常首提/无输入重放与幂等；损坏拒绝且不补账，不能用合并不同来源绕过验收。

## 4. 非阻塞事项和范围

1. **登记类含空格过拒（P2）：** RDKit writer 生成 `$foo bar;$`、`atomProp:0.note.hello world`、`SgD:…:hello world::::` 可合法往返，却被空格拆块报未登记。方向保守，未证明错误 expand，不单独升级 P1；可与 R6-02 词法修复同做，或准确登记当前内容限制/unsupported。无空格与 DATA 内逗号正控保持。
2. **DATA 前提文本不一致（P2）：** R6 delivery 声称 request 已写“化学事实不得编码进将被移除 DAT”，当前 request 只有内容不查/逗号句。应补明确适配器边界或修正交付说法。不能把 SRU/所有 SGroup 一概当注释。没有以缺这句话另制造 P1。
3. **具体签名负控：** invented signature 目前正确拒绝；建议补正式独立回归，不能将缺此单例当新 P1。R6-03 所需的是现存签名与评估的对应关系。
4. **继续 pending：** 完整模板/机制、单位换算、自由基/电子新轴、非四面体完整比较、S3 搜索恢复、终点及 S5 性能；不转为本轮强制功能。composition-only 和自包含候选复算可以作为诚实的局部证明，不认证真实运行发生、来源真伪或生物可行性。

## 5. 对 mimo R6 的采信与修正

- 采纳其撤回 R5 覆盖“完全同意”和自然 E/Z 必须新协议的旧判断；本审独立证据确认 R6 的原例修复。采纳 third consumer 和含空格过拒，本审补出 mapped product 到 R6 及指定手性底物控制。
- 不采纳“输入登记类及默认拒绝已完整”：已登记首头后的并列 `r` 等仍绕过工厂/strict。仅第三入口补守卫不足以闭合。
- 不采纳以 composition-only 注册说明或 strict 轴作为复杂共底物全覆盖的兜底。数值补全合法与结构贡献未核实可同时成立；strict 仅检当前绑定产品。R6-01 是实际配平、正常 proof 自包含复算仍达 R6，不靠猜反应机制下结论。
- 认可 absent、summary/flag 拒绝、凭空签名拒绝及循环分轴；现存签名删评估后经 derive 接受不在其原控制内。
- mimo 明确不审存储，故不能用化学意见替代首提/清单的账本验收。

## 6. 下一轮有限升级范围

按五组边界做统一修复，避免只针对字符串加特判：补全许可与结构/角色/贡献及 proof scope 同源；CX 原始解析登记由所有消费入口共享；derive/from_dict/audit 的父身份及快照评估覆盖共用验证；新载荷、既存引用与重放共用 ledger 事实校验；manifest 保留独立完整 appearance 集合依据。

允许诚实 partial/unknown/unsupported，不得仅补“有风险/仅计量”的文字而继续把本审复杂共底物、CX 丢事实、旧必要未知洗掉的案例送 R6。修复应保留上述正控和未知可 retain 的策略；不要求本轮证明机制，不以全面 reject 换通过，不改冻结 legacy/G2/AtomTool。语义变化按既有规则版本和身份契约登记为待审；未发布 PPV1 profile 可明确拒绝旧版，不额外要求兼容/迁移。

## 7. S3 放行条件

目前 **不放行 S3**。下一轮提交五组修复、旧 451 项及必要新回归、各残余反例翻转和正控保持、可复现红绿日志及更新后的无金标化学审核请求后，再由本会话审核。化学判据冻结仍须用户提交独立 mimo 复核；不替用户调用模型。

不追加完整机制、真实样本量或 S5 性能门。五组当前契约闭合且回归/独立复核通过后，按实施书 §17 进入 S3 工程实现；科学性能可 pending。不根据“测试数量更多”或“又一轮完成”自动通过，也不在未看修复 diff 前承诺日期。

## 8. 可直接交给实施 Agent 的 R7 提示词

```text
你负责 pollutant_pathway_v1 的第七轮 S0–S2 回修（R7）。工作目录 /Volumes/CC/Enzyme_Agent/dependingv43；审核基线 HEAD 6d9020130a481866ce2f3b79933907a33d8cfc9e。目标是污染物降解路径预测：已核实的边，其结构变化、计量贡献、条件和来源范围必须与实际证明相符。先读 AGENTS，优先统一消费入口的验证契约，不继续只修上一轮脚本中的孤立字符串。

必读绝对路径：
1. /Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_ARCHITECTURE_UPGRADE_SPEC_2026-10-05.md（以 §17 阶段裁定为准）
2. /Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S0_S2_CODEX_REVIEW_R6_2026-10-07.md（§3 五组 P1、§4 非阻塞、§6 有限范围）
3. /Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S0_S2_REWORK_DELIVERY_R6_2026-10-07.md
4. /Volumes/CC/Enzyme_Agent/dependingv43/docs/mimo_ppv1_chem_review_response_r6.md（是外部意见，不代替实际代码/复现裁定）
5. /Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S0_S2_CODEX_REVIEW_R5_2026-10-07.md（认可原例修复，核对既有验收边界）
6. /Volumes/CC/Enzyme_Agent/dependingv43/docs/mimo_ppv1_chem_review_request.md

永久证据目录：/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/ppv1_r6_codex_2026-10-07/。先读 README，用 reproduce.py 或将脚本复制到新临时目录复跑；不得在永久证据目录造数据库/覆盖日志。记录数含对照，assert_observed.py 钉住 R6 当前缺口，不是修复后的通过条件。旧探针含旧 HEAD 常量，实际运行身份看 manifest。

只修以下五组 S0–S2 P1，保留已修行为与正控：

R6-01：收紧 atom_delta_stoichiometric_completion 的许可范围。真实 AtomTool C→CCCO 只依次新增 C/C/O，未载入任何共底物初始图；同一证明用于 C+CC=O→CCCO、C+C1CO1→CCCO、C+C=CO→CCCO，当前元素/形式电荷和center都 verified、full、R6。数值全配平不证明乙醛 C=O、环氧环键或乙烯醇 C=C 的贡献已核实。补全许可须绑定明确严格结构身份/角色/贡献及适用 scope，或补另份可确定复算的初始图贡献证据；未登记复杂多原子贡献 partial/unknown、不得 R6，机器披露实际证明范围/依据。保留正常氧化/还原明确计量补全、比例缩放、真实断裂分列/合并。不要求 S3 full_template/机制库，不要求所有小分子共产物完整走 AtomTool，也不按整类名称免审。H2 对 2[H] 只是作用域说明，不新增电子/自由基轴。

R6-02：统一原始 CX 注册与解析。工厂/strict 接受 alanine |atomProp:0.note.hello,r|，SgD/Sg 首头后并列 r 同样漏查，解析后丢 r 仍 as_written；须按真实 CX 类边界检查未知并列类，保护 DAT 内容内逗号和已登记内容。donor checker 的 current/mapped/plain/target 所有原始字符串须走同源守卫；真实干净输出只在 current/mapped 接口加 |r| 后，目前诊断 True/True、公共 audit→R6，指定手性底物远端编辑亦成立。未知拒绝或明确 unsupported/unknown，不得剥身份后当 verified 证据。保留合法标签/属性/DAT 移除、增强组/自由基/映射号/SRU 与公开往返。含空格的合法登记内容过拒为 P2，可同修词法或准确登记边界；不要粗暴 split 逗号，不要求解释新 CX 类，不改冻结执行器。

R6-03：derive_child_context 先验证父内容身份/快照，共用 from_dict/audit 契约；历史 covered_requirement_signatures 必须对应实际记录的评估/必要覆盖，不能只属累积要求集合。旧 pH unknown 快照删 per_requirement、清 coverage、has_gate=False，保留真实 pH 签名，直接父 audit 已拒，但 derive 不加任何新事实即可重算 child ID 并 R6，恢复后也 R6。此例必须拒绝损坏或诚实保留 unknown。保留合法历史 unknown/conflict/satisfied、正常阶段转换、same phase 跨 scenario、现存签名与 invented signature 拒绝控制。不用当前事实重评旧边，不要求认证用户事实真实性或防完全重造自洽历史。

R6-04：首提复用已存 state/appearance 时立即共用重放的版本/内容身份/科学事实/hash 验证。public put 合法后仅在合成 SQLite 分别改 CN、未来 schema、inner ID、appearance refs 不改 hash，再 states=[] 首提当前 created=True 写事件/投影/计划，重放才 LedgerCorrupt。四例应首提 LedgerCorrupt、零新增；合法全量/部分先存和显式状态、正常首提/重放保持。认可已有 hypothesis 四项校验修复，不新增迁移，不自动补账。

R6-05：完整 event appearance 集合要有独立完整性依据，不只 state_id set。合法首提含底物及同 SID 两个不同 raw/source_refs/hash 的 prod-A/prod-B，manifest 三项；删清单 A 留 B，或连 A 行也删，当前无输入重放仍 created=False。两例须拒绝损坏；保持原清单只删 A 行已经正确拒绝，保留此控制。可持久完整 (state_id,appearance_hash) 集合/摘要或等效同源校验，保留多来源/排序幂等/正常无输入重放；不得合并不同出现或自动补账规避。不要求抵抗重造整本账本。

P2 文档同步：明确 SgD/DAT 被移除的适配器前提——化学事实不能只编码进将被视为注记的 DAT；修正 R6 delivery 声称此句已落字的不一致。proof_scope/basis 与 initial/relationship 分轴原控制已修，继续保留。不要把原始 r 标记解释成已证实验精确消旋，也不要把裸指定 SMILES 称实验纯品。

实施约束：只做本轮 S0–S2；不实施 S3–S5，不改冻结 legacy/G2/AtomTool，不访问金标/题面/封存逐题 run，不调用真实模型或付费实验。化学/条件/存储可以并行委派；所有新反例用合成夹具和公共消费链，SQL 只在新合成库准备损坏并记录零写入。语义变动按既有身份/version规范版本化并明确待审，未发布 profile 可明确拒旧，不额外引入兼容迁移。允许诚实 unknown/partial，不能只补风险说明仍把上述残余送 R6，也不能全部 reject 破坏正控。

交付要求：逐项给源码位置、前后实际行为、红绿日志、正负控制、完整命令/输入/版本及证据哈希。保留现有451项，新测试有效检验五组残余和关键正控；报告实际 passed/failed/skipped/deselected及原因，新增数量不能当漏洞修复数，区分字段缺失与行为红，不改预期抹平失败。更新自包含无金标 mimo 化学审核请求，说明补全scope、全部原始CX入口、DATA前提和镜像终态语义，交用户提交外部复核，不自行调用外部模型。提交 R7 交付书和证据，停止跨阶段实施，交回本会话 review；五组契约闭合与回归/独立复核通过后才进入 S3，科学性能继续可 pending。
```
