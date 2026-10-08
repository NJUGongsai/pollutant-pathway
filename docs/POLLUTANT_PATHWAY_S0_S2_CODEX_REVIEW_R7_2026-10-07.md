# pollutant_pathway_v1 S0–S2 第八轮独立复审（R7 交付）

日期：2026-10-07。仓库：`/Volumes/CC/Enzyme_Agent/dependingv43`。实际 HEAD：`858dd94c7c6c8fc387940242403d67b6b36b5313`；父提交/验收基线：`6d9020130a481866ce2f3b79933907a33d8cfc9e`。

**结论：不放行 S3。R6 五组原探针均已翻转，三组可以关闭；同一既有契约仍有两项 P1：状态恢复/直接审核漏验原始结构，以及显式重给有效状态时首次提交复用损坏 appearance。** 不追加机制、化学类型、科学性能或后续阶段门；下轮只收这两处入口。不能用 508 项绿或“旧探针全翻转”替代入口完整性验收。

## 1. 审核范围、纪律与执行

按用户转发授权及本仓 AGENTS，固定 R6 主报告 §3 五组、§6 有限范围及 §7 放行条件。已读 R7 交付书、mimo v7 回应与请求、R6 主报告和源码/测试 diff。三条专项线分别核查，主审独立再执行新化学/条件/存储探针和 R6 12 入口；打包控制器也在新 tmp 验证，508/G01 不重复凑数。只新增本报告与证据目录；源码、测试、AGENTS、既有 docs 和永久审核证据不动；不 git push、不访问真实金标/题面/封存逐题 run、不调用外部模型。没有修改 `/Volumes/CC/Enzyme_Agent/dependingv4`。

| 独立执行 | 实际结果 |
| --- | --- |
| PPV1 全量，19 文件、完整源码/vendor 隔离复制 | **508 passed、0 skipped，1 warning，3.97s** |
| R7 新增三文件在 6d90201 detached worktree | **33 failed / 24 passed**；worktree 已清理 |
| 同三文件在 R7 隔离副本 | **57 passed** |
| R6 永久证据的 reproduce.py，`--allow-head-change --skip-pytest` | **12 个入口全部 exit 0**；主审逐记录验证五组原反例翻转及旧关键控制保持 |
| 原 R6 assert_observed.py | 修前断言在复杂共底物不再 verified 的位置失败，符合设计；它不是修后验收线 |
| 新化学公共链 | **57 条顶层 JSONL**，主审独立复跑及观察断言通过；含恢复/直接审核残余和合法对照 |
| 新条件公共链 | **16 个独立 case 全达预期**，含三入口双向删改拒绝、合法历史与正确旗标调用 |
| 新存储公共链 | **15 个 case + metadata**，主审独立复跑；两条显式提供 SID 的首提残余成立 |
| G01 安全隔离 | **1110 passed / 8 skipped / 17 deselected，1 warning，222.45s**，具体缺席/排除及第一轮环境失败见 §2；不能写成本轮独立 1119 全绿 |

文件保全核对：初始登记244份既有输入，243份内容完全保持；AGENTS.md 在审核期间由本审之外追加“自动循环与外部通道”一节，旧全文仍是精确前缀。本审未写该文件，不回滚、不猜改者；前后哈希和新增段落保留 `prepublication_integrity.json`。追加规则不改变本轮既定验收/零金标/禁外部模型；本审只交报告，停在轮间，不自动启动R8。

唯一 PPV1 warning 是 chemstate 文档字符串无效转义，不是 skip。记录数含 metadata、工厂/store 对照和拒绝案例，不等于漏洞数。508/57 是工程回归数字，不代表污染物路径、dev（B1 环境中间步骤）或 298（RHEA 通用酶学）的科学性能。

基线只在临时化学测试把缺失 `COMPLETION_LICENSE` import 换成同值字面量，断言和 R6 源码不改；保存原始测试、适配 patch、SHA、完整红日志及 worktree 创建/清理日志。粗分 **26 行为红 + 7 披露/结构红 + 24 基线绿**成立；“7 项全因 KeyError/缺表”不精确：实际 **6 项字段/缺表 + 1 项新增 violation kind**。26 行为红含 3 个含空格元数据的 P2 保守过拒翻转，不能都算 P1 漏洞修复。复合控制遇 KeyError 后的内部后半段未执行，不算基线已验。

永久证据：[README](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/ppv1_r7_codex_2026-10-07/README.md)。附件含完整输入、proof、审核/准入、损坏准备与提交前后 counts、基线及测试日志、专项报告、复跑脚本与 SHA-256 清单。探针必须复制到新临时目录；不要在永久证据内运行写库/覆日志的脚本。观察断言含当前 P1 成立，不能当修后期望。

## 2. G01 全量数字与零金标访问的冲突

用户同时要求独立 `tests/ -m "not slow"` 和“金标/题面一律不访问”。静态检查发现当前非 slow 用例包含真实评价路径：

- [test_score_report.py:115](/Volumes/CC/Enzyme_Agent/dependingv43/tests/test_score_report.py:115)、[189](/Volumes/CC/Enzyme_Agent/dependingv43/tests/test_score_report.py:189) 读取 v3 benchmark 的 gold_routes；其模块跳过条件只检测评价脚本是否存在。
- [test_batch_runner.py:58](/Volumes/CC/Enzyme_Agent/dependingv43/tests/test_batch_runner.py:58) 经 build_input_manifest 到 [batch.py:198](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/batch.py:198)、[225](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/batch.py:225) 哈希/读取评价文件。
- [score_report.py:69](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/output/score_report.py:69)、[117](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/output/score_report.py:117) 调评价程序并读取金标路径。

因此没有在真实 benchmark 存在的原仓运行该命令。本审先执行无真实 v3/v4/evaluation 的隔离副本：**2 failed / 1099 passed / 18 skipped / 16 deselected，87.34s**；两败是合成 batch worker 缺 v3 引擎源码的 `EngineBootstrapError`，不能算本次架构失败。随后只补普通 v3 源码、使用本仓已有非题面反应资产的隔离副本，仍不复制 evaluation/金标题面，得到 **1110 passed / 8 skipped / 17 deselected，1 warning，222.45s**。一条仅以 v3/src 存在作前提、实际还加载缺席评价脚本的 export 用例显式排除；其它按原 skip 条件缺席，完整名单和命令留附件。

**R7 交付与主会话宣称的 1119 passed / 16 deselected 是外部执行数字，本审未在零真实金标访问条件下独立证成。** 完整绿日志本身不能证成“未访问金标”；当前测试若原样在真实 benchmark 环境执行就会访问上述路径。除非另有可核查的隔离/替换证据，不能把交付 §4 零访问声明与 §5 原命令全通过同时当作已核实。本审不猜外部会话具体读到何种数据，也不为凑数字复制金标。

源码 diff 确认 frozen AtomTool、legacy 存储/门禁/runner 未变；安全隔离 G01 的环境缺席不是新增架构 P1。该执行限制要透明登记，不能冒充满足本次“独立 1119”要求，也不能变成扩大 S0–S2 化学功能的理由。

## 3. R6 五组逐项裁定

| 原项 | 实际修复与控制 | 裁定 |
| --- | --- | --- |
| R6-01 复杂共底物补全 | 三个 C2H4O 初始图均 unknown/partial/retain；H2/[H] 精确许可、氧化/氢化、缩放、碎片控制保持；scope 与未登记身份机器披露 | **关闭**；不加机制/电子轴，不要求扩许可集 |
| R6-02 原始 CX | 登记首头后 r/Ln 拒绝；含空格移除类放行；donor 四字段和 proof 复算拒绝；指定手性远端编辑对照保持 | 原例关闭；恢复/直传原始字段仍见 R7-01 |
| R6-03 历史条件 | derive 先验父；签名↔行双向一致；三入口单删任一侧均拒；合法 unknown/conflict/satisfied、正常转换/孙上下文保持 | **关闭**；不重评旧边，不认证用户事实 |
| R6-04 首提既存行 | states=[] 的 CN/schema/inner ID/appearance hash 损坏均首提拒绝零写入；合法先存保持 | 原例关闭；显式重给有效载荷仍见 R7-02 |
| R6-05 多来源 manifest | 独立 links 集合检出删 manifest/连行删/只删 links；只删行旧控制保持；同图多来源与排序/正常重放保持 | **关闭**；不要求抵抗整本账本一致重造 |

主审对旧化学 6+17+40 条、旧存储 9+21+29 条逐记录比较关键轴/准入/错误/created 与 R6 快照；这些控制保持。旧条件复合块在已修异常处停止，只有顶层继续；新 16 分段案例补足，不声称旧块所有内部步骤都运行。

## 4. 两项剩余 P1（原契约内）

### R7-01 [P1；R6-02/C1 残余] 原始结构恢复/直接对象未核验，却给 as_written/verified/R6

位置：[chemstate.py:618](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/chemstate.py:618) 的 from_dict 只校版本及 fidelity 枚举；[audit.py:448](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/audit.py:448) 优先直接用 states；[493](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/audit.py:493) parse 不重推原始串，[549](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/audit.py:549) fidelity 只查自报轴值。

最小公开链：正常工厂建 `CCO`、`CC=O`、H2；真实 AtomTool 乙醇氧化证明保持不变；只改底物序列化 payload 的 `structure_smiles_raw="CCO |r|"`，保留 state_id、规范串、版本及四轴 as_written。`ChemicalState.from_dict` 接受，恢复对象经 `audit_hypothesis`→`decide_admission` 全 verified、full、**R6 expand**。`F[C@H](Cl)CCO` 的指定手性表示远端氧化，同样只在恢复 raw 加 r，也 R6。

辅助同根例只把 H2 状态 raw 改 `CC=O`，canonical/ID 仍 H2，恢复/审核也 R6：原始串与规范身份的一致性完全未核。**store.put_state 对这些相同载荷会拒绝且零写入**，已有 [store.py:463](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/store.py:463)、[507](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/store.py:507) 的重推导/raw strict 比较证明可确定校验。不声称此错误状态已成功入账或已产生真实 S3 路线。

mimo C1 特指在 **smiles_isomeric** 加 r 的三个例子，本审确认均 retain，认可其窄判断；不能扩成整个恢复路径不可达 R6。raw 字段反例是另一条已有公共恢复/审核消费链，未要求新化学类型。此处也不从 r 推断实验消旋或样品纯度，只核表示字段一致性。

**最低验收：**from_dict 与 audit 直接对象在首次授信前使用与 writer 同源的纯状态验证，检查规范表示/身份及现有结构事实、原始表示守卫与 raw→strict identity 一致性；违约拒绝或身份未核 unknown，不 R6。不能只补 from_dict 后让直接 dataclass 绕过，也不能静默删 raw 信息再授 full。保留 raw `OCC` 与 canonical `CCO` 的同图不同写法、登记 atomProp 注记、指定手性正常链、CN-only/存档形原有未知与保真边界。不认证调用方来源真伪、历史执行或生物可行性。

证据：`chemistry_current/chemical_boundary_output.jsonl` 中 C1_raw_substrate_unknown_flag、C1_chiral_raw_unknown_flag、C1_raw_uncovered_H2_different_molecule 及恢复/工厂/store 对照。主审独立复跑 57 记录和观察断言。

### R7-02 [P1；R6-04 残余] 同 hash 已存 appearance 损坏，显式重给有效状态仍先提交成功

位置：[store.py:1602](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/store.py:1602) 将本次提供 SID 从 reuse_refs 排除；[_collect_state_writes:994](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/store.py:994) 校当前有效载荷及已存 semantic，没有核同 hash 已存 appearance；[1771](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/store.py:1771) INSERT OR IGNORE 留下损坏行。

先 public put 正常底物/产物，仅在新合成 SQLite 把产物 appearance.source_refs 改掉而 hash 不改，然后首次提交：

| 随事务提供 states | 实际首提 | 同事件无重复输入重放 |
| --- | --- | --- |
| 空列表 | appearance_hash_corrupt，零写入（原例已修） | 未提交 |
| 只重新给原本有效的产物 payload | **created=True**，新增 event/projection/plan 各 1、links 2 | appearance_hash_corrupt |
| 重新给原本有效的全量 payload | **同样成功并新增记录** | appearance_hash_corrupt |

三个 supply 形状在无损坏的正控均首提 created=True、重放 created=False；损坏后的重放拒绝自身零写入。不是 public put 能创建该损坏，也不是要求验证无关整库；首次事件明确引用的 `(SID,hash)` 已有行坏了，有效输入不能证明被 INSERT OR IGNORE 复用的行有效。

**最低验收：**首提校验实际将引用/复用的既存 state 与 appearance，包括 supplied SID 的已存同 hash 行；实际复用的坏 appearance 在各 supply 路径立即 LedgerCorrupt、event/projection/plan/links 零新增，不延到 replay、不自动覆盖修库。已正确零写入拒绝的 semantic 冲突保持，不仅为改错误类型返工。可将纯验证统一到收集/绑定阶段；不按 supplied/unsupplied 两套规则授信。保留合法空/部分/全量先存、显式多来源、排序及无输入重放。补公共矩阵回归，不重开已关闭 links 集合完整性。

证据：`storage_current/storage_contract_probe.output.jsonl` 中 first_existing_appearance_prod_only_corrupt、first_existing_appearance_all_corrupt 和 none/valid 对照，15 case 的主审独立复跑与断言。

## 5. mimo C1–C6 与八项待执行清单裁定

本回复来自用户授权的本机 opencode 免费模型只读通道；手机 mimo 是否同实例未经证实。其只读意见不作为测试背书；头部主会话 PPV1/G01 执行声明与本审执行分开登记，不调用该通道。

| 条件 | 独立裁定 |
| --- | --- |
| C1 恢复可达性 | canonical 加 r 三例 retain 成立；raw 恢复/直接 states 仍全 verified/R6，见唯一状态首消费 P1 R7-01。不能用“调用方信任边界”文字继续核实内部可检测矛盾 |
| C2 preview/外围划界 | preview 为 diagnostic_only/pool_unchanged；冻结执行器内解析经 donor 四字段后守卫。范围文字可补，未证新增错误 admission，不加 P1、不改 executor |
| C3 保留类往返 | RDKit 锁定版本下正常 SRU、增强组/自由基项边界空格等 **6 个放行形状**规范写出稳定、严格身份往返且不同裸串；移除类 **3 个**按登记剥离并同裸 ID。另 **4 个**含空格/逗号 SRU 字段被输出守卫保守拒绝，属 P2 限制；无已证静默丢失/R6。原子索引写出重排不算事实丢失 |
| C4 full 两根据未落字 | 缺逐字整理句属实；request 现有分条及 src 已实现无未覆盖→full、有未覆盖须双侧数值精确且身份许可。实质非缺实现，整理文字 P2，不能凭 grep 缺一句增加阶段门 |
| C5 scope 顶层/同屏 | center detail 在 ChemicalAudit.to_dict 机器保留，满足 R6 原门；admission tuple 不复制 scope。顶层别名、license_applied、渲染同屏列后续/API 展示 P2；未证当前消费链把 H2 活化机制错误授信，不以 UI 尚未实现阻塞 |
| C6 异常/失败早退 | 成功执行的四未登记输入均抛 AuditContractError，无返回诊断/处置；失败执行四例早退、三轴 None/空 evidence，不解析污染字段。口径落字可补，不凭假设吞异常新增 P1 |

其八项待执行：①PPV1 508证成；②基线33/24证成、窄分类更正；③G01仅证成§2安全隔离结果，外部1119待纪律兼容证据；④12入口原例翻转与关键控制证成，但不等于全部入口已闭，两个残余如上；⑤C3具体放行形状证成并登记过拒；⑥canonical窄例retain证成，raw广义恢复可达R6；⑦合法快照及双向删除三入口证成；⑧四原始字段、手性例及 tainted proof 复算拒绝由新回归和旧公共探针证成。要求不可变前提、拒绝不反推实验消旋/纯度等为已有边界的文字澄清，不新增机制/真实性认证。

## 6. 新回归有效性与交付表述

1. **有效覆盖：**三复杂共底物检查 partial/unknown/retain；并列未知在 build/strict 拒；donor 四字段/手性/proof 复算拒；条件派生与签名行；states=[] 的首用损坏；manifest/links 双向完整性。不是单看进程 exit 0。
2. **未覆盖的两个消费入口：**没有 state.from_dict/直接 audit raw 一致性；存储损坏只测 states=[]，漏显式重给有效 payload 的同 hash 复用。508 绿无法关闭这两处。
3. [test_ppv1_r7_conditions.py:340](/Volumes/CC/Enzyme_Agent/dependingv43/tests/test_ppv1_r7_conditions.py:340) `_audit(*_oxygen_hyp(), child2)` 把 evidence 当 context，实际报 context_object_invalid_type，不验证 gate_flag_mismatch。独立正确参数链已检出旗标矛盾，旧保护仍在；修测试属 P2，不因缺单例重开 R6-03。
4. 同文件 from_dict 反例说明将旧 ID 的恢复写成基线已接受，事实不符：此项基线已绿。原漏洞是 derive 先洗出新 ID 后恢复接受。33 红粗分可认；“7 都 KeyError/缺表”和复合氢控制所有内部在基线运行须更正。许可非类名例本来有数值 surplus/deficit，不能单凭它证明“完全配平仍被身份许可阻断”；三个 C2H4O 原例才有该证据。
5. 存量 r6_chem violation 断言改为数值类仍带数值、许可类带 identities，并加许可常量断言，保留原数值意图，修改合理；5 份机械版本测试加 1 份该语义修改，实际 **6 份存量测试改动 + 3 新文件**。源码实际 **5 文件**（4 逻辑+profile），不是把表当额外模块。
6. R7 §0/状态“全部按统一入口收口”超出已证范围，需按本报告改为原反例修复、两个既有入口残余。DATA/DAT 适配器前提与 R6 文案夸大纠正已落在 v7 请求，认可；不回写 R6 历史快照。G01及零访问声明按 §2 分开。

## 7. 放行与下一轮有限范围

**不放行 S3，P1 清单只有 R7-01/R7-02。** 已关闭 R6-01、03、05 和 R6-02/04 原例保持关闭；下轮补状态恢复/直传首次验证及 supplied appearance 首提复用校验，保留合法对照、旧508和必要新增回归，再审核。C2–C6 的文字/展示、保守过拒、测试参数和数字更正可同步处理，不作为新阶段或化学功能门。

G01安全隔离与完整1119的差异须明列，不用真实金标凑数。本审无法同时实现原命令真实环境全量与本条零访问禁令；下一次应给符合既有纪律的工程回归口径/独立依赖，而非自动授权读取基准。不得因这项环境限制增加化学机制/科学性能要求。

契约/判据仍不宣称冻结。两个公共入口闭合且既定回归/独立复核通过后按规格 §17进入S3工程；S5科学性能可pending。本次没有源码修复或接线，不承诺下轮必过，不扩阻塞清单凭据。

## 8. 可交实施 Agent 的有限 R8 提示词

```text
你负责 /Volumes/CC/Enzyme_Agent/dependingv43 的 PPV1 S0–S2 有限回修R8。基线 HEAD 858dd94c7c6c8fc387940242403d67b6b36b5313；先读本仓AGENTS。
必读绝对路径：
1. /Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S0_S2_CODEX_REVIEW_R7_2026-10-07.md（§4两个剩余P1、§7有限范围）
2. /Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S0_S2_CODEX_REVIEW_R6_2026-10-07.md（原验收，不扩大阶段）
3. /Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S0_S2_REWORK_DELIVERY_R7_2026-10-07.md
4. /Volumes/CC/Enzyme_Agent/dependingv43/docs/mimo_ppv1_chem_review_response_r7.md（读码意见，采信限本次程序互证）
5. /Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_ARCHITECTURE_UPGRADE_SPEC_2026-10-05.md（§17阶段裁定）
证据：/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/ppv1_r7_codex_2026-10-07/。先复制脚本到新临时目录，不原地写库/覆日志；观察断言钉住R7仍有缺口，不是修后验收线。

只修两个同既有契约P1，先列入口矩阵，共用验证源：
R7-01：正常乙醇氧化证明不动，只改序列化状态raw=CCO |r|，ChemicalState.from_dict→audit(states=...)全部verified/R6；H2 raw=CC=O同根，store.put_state已有同源规则拒。把既有规范身份/结构事实、raw登记与raw strict一致性校验用于恢复和直接对象首次审核，不只补from_dict留dataclass绕路、不静默清洗信息再授full。非法对象拒或诚实身份unknown、不R6。保留clean、raw OCC vs canonical CCO、登记atomProp含空格、指定手性正常链、CN-only及存档fidelity边界。只核对象内部可确定一致性，不认证来源真伪/历史执行/机制。
R7-02：先put合法状态、合成SQLite仅改appearance.source_refs不改hash；空states首提现已拒，但重新提供有效prod-only或全states仍created=True并写event/projection/plan/links，重放才hash_corrupt。首提校验实际将引用的所有既存同(SID,hash)出现，包括supplied SID；立即LedgerCorrupt且零新增，不延后、不覆盖修库。共享收集/绑定/重放规则，保留合法none/partial/all先存、同图多来源、排序和无输入重放。链接集合R6-05已关，不新增整本账本抗一致重造要求。

R6-01/03/05及02/04原反例已证修复，不重开。H2/[H] composition-only许可保留，不新增电子/自由基/机制库、不扩许可类型、不实现S3–S5、不改冻结legacy/G2/AtomTool。
P2可同步修：r7_conditions最后flag测试参数顺序；from_dict基线说明；7披露红准确为6字段/缺表+1violation披露；复合控制未执行部分如实报告；v7规则整理full两根据及拒绝/早退口径、DATA前提保持。scope已在center detail机器披露，top-level/同屏展示和SRU保守过拒列后续，不变新增阶段门。

金标/题面/封存逐题run一律不访问，判分零LLM、不自己外发模型。G01当前not slow含真实gold_routes读取，不能把外部1119或无skip命令当零访问证明；用可核查安全隔离工程回归，逐项报告实际pass/fail/skip/deselect及缺席依赖，不为凑数字读取评价基准或伪造fixture。完整科学验收仍pending，不因此扩本輪化学功能。普通源码及非题面反应资产与真实评价数据分别识别。

保留现有508项和必要新回归，两个公共反例在858dd94先红、修后翻转；合法正控保持，不能全部reject换过。记录实际HEAD/schema/命令/输入输出/哈希，区分字段红与行为红，不改预期抹平失败。更新自包含无金标化学复核请求与交付/证据，用户提交外部意见；不自行调用外部模型。实施交付前按入口矩阵自审，提交后停止跨阶段，交回本会话review。
```
