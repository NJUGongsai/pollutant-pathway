# pollutant_pathway_v1 S0–S2 第五轮独立复审（R5）

审核日期：2026-10-07。仓库：`/Volumes/CC/Enzyme_Agent/dependingv43`。锁定 HEAD：`293bc627f57b1f778aa433750f7f61d00b4a9d18`；回修基线：`e80f4594ea44b5f2bf8c78360dc2ed2368dd94ae`。

**结论：R5 有实质修复，但 S0–S2 仍未通过，不放行 S3，不冻结化学判据或契约。** 独立隔离套件 **381 passed，0 skipped**。仍有 8 组 P1：证据覆盖把未检验的额外转化授为“全部核实”，原始 CX 信息会绕过注册检查，明确缺失/历史冲突条件可被洗绿，来源出现及既存假设首次复用仍有缺口，旧同父兄弟来源串线，以及真实断键被镜像误报为未声明变化。

这些不是必须提前实现完整机制库或 S3 搜索的要求。它们发生在已经交付的 S0–S2 公开输入、诊断、审核、提交及恢复入口；接入搜索会放大错误确认、错误保留理由和不可追溯来源。

本次只改审核文档及证据附件，不改实现、测试、供应方文档或用户 mimo 原文。探针全部使用合成结构、条件和临时 SQLite；不读 gold、真实题目资产或封存逐题 run，不调用模型，不做真实路径实验。

## 1. 依据与证据范围

- [原实施书 §17 最终裁定](/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_ARCHITECTURE_UPGRADE_SPEC_2026-10-05.md:761)。
- [R4 独立复审](/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S0_S2_CODEX_REVIEW_R4_2026-10-07.md)。
- [R5 回修交付书](/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S0_S2_REWORK_DELIVERY_R5_2026-10-07.md)。
- [mimo R5 原文](/Volumes/CC/Enzyme_Agent/dependingv43/docs/mimo_ppv1_chem_review_response_r5.md)、当前源码及 13 个 ppv1 测试文件。

化学、条件及存储三线独立核查；主审最后用附件复跑器再次执行全部 10 份探针入口及隔离套件，观察断言通过。永久证据入口：[README](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/ppv1_r5_codex_2026-10-07/README.md)。附件包含主审新覆盖 9 条 JSONL、旧 admission 23 条、新化学 6 条及旧化学 17+40 条、新条件 7 个顶层案例及旧条件 19 个、新存储 9 条及旧存储 21+29 条、381 项测试日志和 SHA-256 清单。**记录数含环境与控制，不是失败测试数。**

旧 admission 原脚本遇到已修的证据篡改会中途抛错。本审以可复跑 AST 包装器逐调用捕获契约异常，23 条记录均实际执行；不是把供应方只跑出的前 5 行写成完整复跑。将真实 True 诊断擅改 False/None 被 integrity 拒绝是正确行为；合法负轴另外由 R5 回归覆盖。

| 核查 | 本审实证与限制 |
| --- | --- |
| 独立 ppv1 套件 | 存储专项隔离复制 src 与 13 个 ppv1 测试，381 passed in 3.16s；主审复跑器再验 381 passed in 3.61s；均 0 skipped，1 条文档字符串无效转义 warning 不影响判定 |
| 全量非 slow | 交付及 mimo 报告 992 passed / 16 deselected；本审未独立重跑全量，不写成主审实测 |
| 修改范围 | 相对 R4，实施源码只动 pollutant 包 7 模块；冻结 AtomTool、legacy 执行链和 runner 未改。静态 diff 不代替全量行为证明 |
| S3 / 科学验收 | S3 保持 fail-closed；科学性能 pending，工程夹具通过不代表污染物路径泛化通过 |
| 外部依据 | 仅补查 RDKit 官方文档；mimo 意见只采信到与程序证据互证的程度 |

真实执行器案例与接口合成案例分开标注。H2 及环氧乙烷等合成参与物只用于检验身份、覆盖和数值账；不声称机制、酶选择性、速率或实际降解路线成立。

## 2. R4 问题的关闭状态

| R4 项 | R5 已确认修复 | 本轮裁定 |
| --- | --- | --- |
| 01 中心证据/完整产物集合 | 无 proof unknown；篡改真实绑定拒绝；错误轴类型拒绝；真实断裂分列/合并均绑定；原双侧额外转化 retain | 证明记录与旧反例认可；单侧覆盖仍见 R5-01 |
| 02 hash/不可变/假设身份 | finite_rule 入 hash；普通 `|=` 与 hypothesis 自身嵌套修改拒绝；新提供的假设及已提交重放重推 ID | 旧控制认可；既存假设首次复用漏校验见 R5-06 |
| 03 来源单位 | 温度空单位 unknown，C/°C 正常，K unknown；pH 无量纲正例保持 | 旧反例关闭 |
| 04 条件作用域/快照覆盖 | 同 phase 跨 scenario 不重评旧边；空快照不能覆盖孤儿要求；具体签名正控制保持 | 旧反例关闭；恢复摘要与逐条结果矛盾见 R5-04 |
| 05 依赖反驳 | 按轴撤销，后续再生不洗绿初始反驳；同轴新证据才能恢复，audit retain | 原 admission 反例关闭；环诊断 P2 另列 |
| 06 编辑镜像 | 新增 ID 后引用及 change 的 from_order 前置正确，真实执行器同向 | 原反例关闭；终态归一不一致见 R5-08 |
| 07 未覆盖立体轴 | 真 E/Z 差异检出；非四面体先判 unsupported 并公开；中心外 unknown 门及联合映射门生效 | 原反例关闭，不撤销；断键归一另见 R5-08 |
| 08 DATA/CX 身份 | 任意 DATA 注记与逗号值不分裂 ID；非 DAT SGroup 保留并往返；w 等写出类拒绝 | DATA 修复认可；原始被丢弃类见 R5-02 |
| 09 状态写入事实 | raw 同源身份、CN/立体/同位素、fidelity、CN-only 专用契约违规均拒；OCC 与 CCO 同图接受 | 原 writer 反例关闭 |
| 10 不带 states 的重放 | 事务全量输入生成 manifest，缺清单项及原状态损坏拒绝；正常重放幂等 | 全量场景关闭；先存/部分存/清单缩短见 R5-05 |
| 11 旧来源绑定 | 不同父的同 CN 错来源降为 CN-only；事件/路径、产物/raw 矛盾披露，可信 raw 保留 | 原反例关闭；同父兄弟来源仍串线见 R5-07 |

§4 的 audit.scope 遮蔽已修。旧同图多出现、计量全 H/形式电荷分轴、per-product off/空计划/跳阶段披露、CN-only 未知及合法多步导入控制保持。不把这些修复说成没有进展，也不把旧用例翻转等同契约完整闭合。

## 3. 阻塞 S3 的问题及最小验收

### R5-01 [P1] 单侧未覆盖被无条件授为 full；额外异构体转化可在完整配平下达到 R6

位置：[audit.py:724](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/audit.py:724)、[761](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/audit.py:761)。覆盖按物种身份集合判定，没对齐系数/贡献范围；只有“未覆盖反应物与未覆盖产物同时存在”才阻断。

两组主审公开 API 反例，使用真实 AtomTool→真实诊断，不篡改 proof：

- 真实 CCO→CC=O 证据用于 `CCO → 1/2 CC=O + 1/2 C1CO1 + H2`。额外环氧乙烷产品从未核验，且乙醛只申报半份；仍 `product_coverage=full`、center verified、元素/电荷 verified、R6 expand。
- 真实 CC=O→CCO 证据用于 `CC=O + C1CO1 + 2 H2 → 2 CCO`。额外环氧乙烷开环/还原未进入该编辑证据，却因产物物种都是已覆盖 CCO，仍 full/verified/R6。

二者都数值配平，不能靠元素账兜底。不是声称该反应生物可行，而是证明“账平”和“出现了一个正确产品”不能证明额外成环/开环变化。原双侧额外转化负控制现在 unknown/retain，真实乙醇氧化/乙醛还原及 H2 计量控制保持 R6。

**验收：**证据覆盖须对应被审参与物及贡献/系数；未覆盖部分只有带明确注册的计量补全依据或另份可核验证据才能算已覆盖。额外复杂结构转换不能凭单侧集合为空升级 full。不能把整类 H2、水或共底物凭名称免审，也不要求每个计量共产物必须完整走 AtomTool；允许明确、可验的补全规则。不能验证时保留 partial/unknown、不得 R6。保留真实断裂分列/合并、合法比例缩放与明确计量补全控制；不要求实现 S3 full_template。

### R5-02 [P1] CX 守卫只看重写输出；原始未登记信息被解析器丢弃后以全保真入库

位置：[chemstate.py:182](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/chemstate.py:182)、[399](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/chemstate.py:399)、[474](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/chemstate.py:474)。公开 build/strict 输入先解析，守卫只检查之后的规范输出。

独立复现裸 `C[C@@H](N)C(=O)O` 与附 `|r|` 同 state_id，四轴 as_written；`C1CCCCC1 |Ln:1|` 与裸环己烷同 ID。原始块已丢失，守卫看不到。能被写出器保留的 `|w:1.0|` 正确拒绝；已登记 atomProp/原子值注记正确移除。不能因这些正控制通过就证明原始输入全覆盖。

本审判据是“承诺拒绝未登记输入，却静默丢弃”；**不把裸指定结构扩称实验纯品，也不凭本探针认定真实样品为外消旋。** [RDKit 官方 CX 说明](https://www.rdkit.org/docs/RDKit_Book.html#cxsmiles-cxsmarts-extensions)明确其只解析/写出扩展功能子集；规范输出不存在某块不是原输入完整保真的证明。

**验收：**输入解析前按同一注册表验证原始 CX，或实现等价的注册感知完整性检查；所有公共结构入口一致。未知/畸形类不能丢掉后称 as_written。不能直接把输出侧逗号拆分守卫搬到原输入，也不能将合法移除的 DATA/标签/坐标与保留事实一概“输入输出不等即拒绝”。保留逗号 DATA、SRU/聚合物、增强组、自由基、映射号与往返控制。

### R5-03 [P1] 非物种 known_absent 被当正事实；明确缺失仍满足必要条件

位置：[path_context.py:354](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/path_context.py:354)、[718](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/path_context.py:718)、[811](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/path_context.py:811)。物种分支处理 absent，普通枚举/数值分支只排 unknown，再直接比值。

纯公开构造 `oxygen_regime='aerobic', status='known_absent'`；当前 essential aerobic 有来源。实际逐条 satisfied/value_match，condition verified→R6。matrix='soil' absent 同词也 R6。温度25/C absent 仍满足20–30区间。NADH 同实体 absent 的物种负控制正确 conflict，不说所有 absence 都失效。

**验收：**先消费事实 status，再值匹配。明确缺失不能提供正支持。枚举同值否定可 conflict；数值 absence 若未定义就结构化拒绝/unknown，**不要求由“25 不成立”推出整个20–30区间不成立**。保留 present、unknown、物种实体优先、不同 matrix 标签 unknown 与单位控制。

### R5-04 [P1] 恢复入口信任矛盾快照摘要/旗标；旧冲突行仍在却总 compatible/R6

位置：[path_context.py:1750](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/path_context.py:1750)、[1154](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/path_context.py:1154)、[1182](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/path_context.py:1182)。from_dict 直接回读 phase_history，消费信 environment_fit/has_gate_requirements；具体签名仍使要求认作已覆盖。

正常 derive：sA:p0 有氧事实与旧 essential 无氧冲突；明确转 sB:p1 后当前无氧必要条件满足，正常 route conflict→defer。合法载荷 to_dict 后仅改旧快照 environment_fit='compatible'，再公开 from_dict，旧 per_requirement 仍 conflict、conflict_keys 仍有 oxygen，但总 compatible、condition verified→R6。仅改 has_gate_requirements=False 也洗掉冲突。context_id 没变，input_hash 已改变，**不是同 hash 漏项**。

**验收：**快照门禁摘要必须由已记录的逐条评估、必要要求及签名覆盖一致派生，或在恢复/审计入口拒绝内部矛盾。context 内容与派生身份同源；签名覆盖不能豁免被旗标跳过的必要评估。保留旧边原记录，不用当前事实重评旧边，也不要求认证所有用户事实真实性。相同合法载荷往返及正常阶段转换保持。

### R5-05 [P1] appearance manifest 只覆盖本次 states；先存来源漏绑定，正常首次提交也能立即不可重放

位置：[store.py:1516](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/store.py:1516)、[1180](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/store.py:1180)。首次仅把 appearance_writes 写清单；重放要求非空，并逐项验证清单，却不证明清单覆盖本事件完整出现集合。

- 两状态先 public put_state，再 submit(states=[])：首次 created=True/manifest=[]；未损坏的同事件重放却报 event_appearance_manifest_missing。
- 只先存产物、事务只供底物：manifest 仅底物。删除原产物 prod-A 出现，留同物种无关 prod-B；不带 states 重放仍 created=False。
- 全量提交正常幂等，删其已列产物出现正确报缺失。将完整 manifest 缩成非空子集后重放也成功，说明清单自身覆盖/完整性未封口。

**验收：**首次必须明确绑定本事件使用的全部出现引用，涵盖合法先存与部分先存；有多个既存出现时不能替调用方猜出处。可要求显式 appearance 引用，或在首提缺依据时零写入拒绝；不能先成功提交再正常重放判损坏。清单作为权威断言需覆盖与完整性校验，删实际来源留其他出现、缩短清单都明确损坏且不补账；合法全量/先存重放保持幂等。交付“先存仅核存在性”登记不满足 R4-10 的来源集合验收。

### R5-06 [P1] 新提供/重放假设验 ID，但首次复用既存行不验；错前提被提交后才拒绝

位置：[store.py:1473](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/store.py:1473)、[1384](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/store.py:1384)。首次读取已有假设，仅查提供载荷是否不同及事件关系；同源重推 ID 在重放分支。

public put_hypothesis 合法入库；临时 SQL 仅模拟已存 assumptions 损坏，原 ID 未换。首次 submit(hypothesis_dict=None) 仍 created=True；紧接同事件重放才 hypothesis_payload_id_corrupt。新提供假设及已提交重放的原反例已拒绝，不撤销这些修复。

**验收：**首次引用已有行与新提供载荷、重放使用同源契约/内容身份验证；首提须先拒绝并零新增事件/投影/计划，不以“下次重放能发现”代替。保留正常先存假设和排序幂等。SQL 只用于临时损坏夹具，不要求修改旧库，也不讨论恶意完整重造账本的历史真实性。

### R5-07 [P1] 同父同 CN 兄弟来源串线；关系校验用被改指针反证自身

位置：[legacy_reader.py:268](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/legacy_reader.py:268)。来源事件父路径匹配有效，但 child_paths 从同一 path_instances 的 event_id 查询；改本路径指针后，本路径自然进入查询结果。

旧库公开提交 A/B 两个同父分支，产物 `C[C@H](O)CC` 与 `C[C@@H](O)CC` 同 CN、strict 不同；A 后续有消费事件。临时只把 A 路径 source event 指向 B：导入接受 B 的相反立体 raw，uncertainty_notes=[]。现有独立关系锚 `product_path_id(run_id, source_event_id, position)` 与 A 原 path_id **不等**，但未核验。合法 A 正控制匹配。导入前后旧 SQLite 字节不变；SQL 损坏仅是准备合成负例。

**验收：**用旧存储确定性子路径身份或等效独立关系锚核来源事件/位置/本路径，不能查询已改字段来“证明来源”。同父兄弟错来源也降 CN-only 并披露原因；保留合法多步、root-return、多位置及空指针控制，旧库只读。不能用 CN 同值代替严格结构或路径来源一致。

### R5-08 [P1] 镜像漏执行器终态序列化；正确 σ 断键的自然 E/Z 消失被误报漏声明

位置：[audit.py:2033](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/audit.py:2033)、[atom_tool.py:511](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/services/atom_tool.py:511)。镜像只 sanitize 后比较内存 GetStereo；实际执行器输出后被重新解析，二者终态不同。

真实 render `C/C=C/C`，声明 break U_C_1–U_C_2；validate/execute 均 True，产物 `C.C=CC`。断邻位 σ 键使双键端烯化，已无 E/Z。诊断却 undeclared_bond_change U_C_2–U_C_3，strict/center None。私有镜像检查只解释公开诊断根因：镜像旧标志 STEREOE 未清，实际重解析 STEREONONE；镜像同样写出/重解析后，键变化集合与实际完全一致。远端断尾、直接改双键及断双键正控制无此伪失配。

**验收：**诊断镜像使用冻结执行器同等终态规范化及原子 ID 对应，正确已声明断键的自然立体后果不能称漏申报。保留实际 E/Z 变化检出、伪造翻转失配、from_order/live-ID/净效应控制；不删除 E/Z 轴、不默认忽略所有 stereo loss，不改冻结 executor，也不新增独立立体编辑协议。若确有比较支持范围外案例，明确 unsupported 理由，不能把已证镜像差异仅登记为“调用方无法正确申报”。

## 4. 非阻塞披露项

1. **proof 的命题及 basis 输出（P2）。** 自包含确定性重算可以证明候选输入集自洽，不证明历史执行发生；本轮不再把“虚拟但自洽”本身列成假证明 P1。正常机器 detail 没有 proof_scope，且 [audit.py:935](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/audit.py:935) 读未写入的 center_match_basis，理由实际 `basis=` 空串。应同源披露 `proof_scope=self_contained_recompute`、真实 direct/symmetric_equivalent basis，空字段不伪装依据；不要把它升级为实验/供体完整模板证明。
2. **循环诊断轴消费（P2）。** [path_context.py:1637](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/path_context.py:1637) 仍以总 status 判断启动和关系支持。initial supported、reaction contradicted 会误报启动未知；initial contradicted、regeneration supported 会混入关系不支持。总 contra/audit retain 已正确，不撤销 R4-05，也不要求环自动 reject/defer；后续诊断应消费对应有效轴。
3. DATA 全类注记假设须约束适配器，不能把化学事实编码进将被丢弃的 DAT。radical 保真轴、增强组/非四面体比较范围、CIP 说明字段等已登记限制保留；单位换算、full_template、edge_kind/scoring_key、S3 调度及 S5 科学性能不转为本轮新增强制功能。

## 5. 对 mimo R5 的采纳边界

- 采纳原始 CX 守卫缺口、proof_scope/basis 展示问题，及单位、scenario+phase、原孤儿要求、依赖撤销等旧控制已修的判断。
- **不采纳“判据三集合覆盖完全同意”。** mimo 的单侧共底物例碰到元素 violated，不能证明覆盖逻辑安全。本审两组数值完全配平仍 R6，说明问题在覆盖轴，补文字交叉引用不能修。
- **不采纳“断键导致 E/Z 消失须另设立体申报通道才能通过”。** 本审真实执行已成功；同样终态序列化足以对齐。mimo 文本“3b 两路皆失”与本审镜像 STEREOE/实际 STEREONONE 的直接证据相矛盾，应更正，不能靠登记误报来关闭。
- 条件判据四的旧例同意可保留；不能据此盖过 absent 或恢复载荷内部矛盾。存储/旧来源问题不在其完整化学抽查范围，不向其总体结论外推。
- mimo 临时探针建议留存合理。本审已独立留存最小证据；实施方若转录 mimo 原探针，先核脚本内容、无 gold、真实来源和更正后的夹具，不把未亲自复跑的输出冒充主审证据。

## 6. R6 回修的架构要求

不要继续只补上一份脚本中的单个字符串。优先统一这五个边界，再由三线落地：覆盖证明绑定参与物贡献/系数；原始 CX 注册与解析共用契约；事实 status/历史快照派生字段在 build/from_dict/audit 同源验证；首次新载荷/既存引用/重放共用 ledger 验证及完整出现绑定；镜像与冻结执行器终态语义一致。旧来源关系另用确定性身份锚。

最小回归须包括本审 8 组反例及各正控制；新增测试先在 293bc62 基线跑红，明确原来就通过的正控制。测试调用公开链，不能只断言私有守卫会拒绝或直接构造 AuditResult。旧观察脚本记录异常后继续，不以 exit 0 或首个预期异常代替逐案验收。

契约变更按既有无发布历史口径版本化，缺旧字段 fail-closed/显式 unknown；不要伪造兼容性。交付标清哪些是已验、局部已验、unsupported 和未实施。不得以改文字/改测试期待为唯一修复；不得将 unknown 一律化学 reject。

## 7. 当前放行决定

S0–S2 本轮不通过；S3 入口保持 fail-closed；判据与契约不冻结。上述 P1 闭合并独立复审通过后，依原实施书 §17 才进入 S3–S5。无需等待单位换算、完整机制库或 S5 科学数字才能回修底座。

原工作区只有用户已有未跟踪 mimo R5 原文；审核新增仅本报告及专属证据目录。保存前后确认 HEAD、实现和测试未变。下一轮交付由用户带回本会话 review，不自行继续跨阶段，不自行外发 mimo。

## 8. 可直接交给实施 agent 的提示词

你负责 pollutant_pathway_v1 的第六轮 S0–S2 回修（R6）。工作目录 /Volumes/CC/Enzyme_Agent/dependingv43；当前审核基线 HEAD 293bc627f57b1f778aa433750f7f61d00b4a9d18。目标是污染物降解路径预测：每条“已核实”边必须有与其实际参与物、结构变化、条件和来源范围相符的证据；账平、物种同 CN 或存在一份正确局部诊断不能代替整条声明的覆盖与追溯。

先读 AGENTS.md 和以下文档，以原实施书第17节的阶段限定及本轮独立复审验收为准，mimo 意见须与程序证据互证：

1. /Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_ARCHITECTURE_UPGRADE_SPEC_2026-10-05.md
2. /Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S0_S2_CODEX_REVIEW_R5_2026-10-07.md
3. /Volumes/CC/Enzyme_Agent/dependingv43/docs/mimo_ppv1_chem_review_response_r5.md
4. /Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S0_S2_REWORK_DELIVERY_R5_2026-10-07.md
5. /Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S0_S2_CODEX_REVIEW_R4_2026-10-07.md

永久证据目录：/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/ppv1_r5_codex_2026-10-07/。先复制脚本到新的临时目录执行，不在永久审核证据目录创建数据库或覆盖日志。README 给出复跑方式。记录数包括控制，不能当失败测试数；assert_observed.py 钉住本轮实际行为，不代表期望已修复。

本轮8组P1必须逐项关闭：

R5-01：修复单侧覆盖自动 full。真实乙醇→乙醛证据用于 CCO→1/2CC=O+1/2C1CO1+H2，及真实乙醛→乙醇证据用于 CC=O+C1CO1+2H2→2CCO，目前均全账 verified、center verified、R6；额外环氧乙烷转换未经 checker 核实。覆盖须绑定参与物贡献/系数或有明确可核验的补全规则；不能凭集合一侧为空或账平升级。不要求实现 S3 full_template，保留合法 H2 等计量补全、真断裂分列/合并及比例缩放。

R5-02：原始 CX 输入做注册感知验证。|r|、|Ln:1| 目前被解析器丢弃后与裸输入同 ID、as_written；不能只守卫规范输出。未知/畸形类须明确拒绝/unsupported，所有公共入口一致。保留 DATA逗号值、标签/坐标等已注册移除、SRU/增强组/自由基及往返；不要简单逗号拆原始输入或把输入输出不等一律拒绝。

R5-03：非物种 known_absent 不得正向 satisfied。oxygen aerobic absent、matrix soil absent、温度25/C absent目前都能满足相应必要条件并R6。按明确否定语义判 conflict；若数值 absence 没定义则拒绝/unknown，不能把“25不存在”推为整个范围不存在。保留 present/unknown/物种实体/单位控制。

R5-04：PathContext.from_dict 及审核入口核历史快照内部一致性和内容身份。旧逐条 conflict 仍在，仅改 environment_fit=compatible 或 has_gate_requirements=False 即R6。摘要、旗标、必要要求和具体签名须同源派生或矛盾拒绝；不要拿当前事实重评旧边，不要求认证所有用户事实真实性。input_hash 已改变，不要误报为原哈希漏项。

R5-05：完整事件出现绑定覆盖先存/部分先存。全先存 states=[] 首次成功但空manifest导致正常重放报损坏；部分先存删实际 prod-A、只留无关 prod-B仍重放成功；清单缩成非空子集也成功。首次明确全部appearance引用，多出现不能猜来源；缺依据先拒绝零写入。校验清单覆盖/完整性，合法首提→重放幂等，损坏明确失败且不补账。

R5-06：首次复用既存 hypothesis 行也做同源契约/ID重推。现有行改 assumptions但保留ID后，submit(hypothesis_dict=None)创建成功，下次重放才拒绝。首次即拒绝并零新增事件/投影/计划；保留正常先存及排序幂等。

R5-07：旧同父同CN兄弟来源用独立路径身份锚核验。把A路径来源event换B，相反立体raw被导入且无注记；查同一改过的event_id反证child_paths是循环证明。核product_path_id(run_id,source_event_id,position)或等效独立关系，错来源降CN-only+原因，保留合法多步/root-return/多位置，旧库只读。

R5-08：诊断镜像与冻结执行器终态归一一致。真实C/C=C/C断U_C_1–U_C_2成功得C.C=CC，E/Z自然消失；内存镜像却留STEREOE、实际重解析STEREONONE，误报undeclared_bond_change。镜像同样写出/重解析可对齐。不要新增立体操作协议、删除E/Z轴、默认忽略所有stereo loss或改冻结executor；保留伪造真翻转、from_order、live-ID和净效应控制。确实unsupported的情况用诚实理由。

同时处理两项小P2：正常center证据/audit detail披露proof_scope=self_contained_recompute及同源center_match_basis，消除空basis=；循环诊断按对应有效轴区分启动供给和关系，不以整体status污染两种语义。自洽虚拟记录本身不是本轮P1，其命题是输入集重算自洽，不是历史执行/机制/实验事实。不得把非四面体/增强组支持范围、radical保真轴、单位换算、完整供体模板或S5科学性能擅自宣称完成。

先统一上述载荷及验证边界，再并行化学/条件/存储实施，避免各入口另写半套验证。新增公开入口回归在当前293bc62基线先跑红，标清本来已绿的正控制；修改旧测试要解释被本审证伪的语义。完整跑ppv1及适当legacy回归，提供真实命令、日志、逐案翻转与未知清单，不把工程测试通过写成路径科学性能。

只做S0–S2回修，S3继续fail-closed。保留用户原文和旧审核证据；不读gold/真实题目/封存逐题run，不调用模型、不做真实实验、不自行外发。化学规则变更后产出自包含无金标mimo请求，由用户转交。交付建议保存为 /Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S0_S2_REWORK_DELIVERY_R6_2026-10-07.md，注明实际日期/HEAD/diff/版本及冲突清单。完成后停止跨阶段实施，由用户交回本会话独立review；未经review通过不得放行S3或冻结契约/判据。
