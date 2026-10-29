# T-G Step C2 draft_v4 Codex 复核报告（2026-10-19）

**总裁定：可进 CC 预注册确认；P0=0，P1=0，P2=0。原 P1-C2-02 关闭。** v4 已把旧元素门决定的路由与新中心判据决定的准入分开：先按原规则完成供给/wildcard 拦截并固定执行输入，再由中心 helper 判断该输入能否进入编译。上轮两种反例均有明确接线约束和一对一公共链验收。该裁定只关闭**设计回修缺口**；不表示生产代码已经实现、正式 R2′ 已验收或性能已兑现。本报告不替 CC 选择路线、参数或冻结预注册。

> **题域标签**：本报告合成控制均为**纯合成、非 298 成绩**。引用的既有可达记账均属 **298=RHEA 通用酶学/已见题**，不是化学成绩，不向 dev（B1 环境路径）外推；本轮没有重跑真实池或重新计算科学性能。
>
> 实际 HEAD：`d9cee973566fff8692b0c2abc51ab91f8122cfb3`。被审文件：`docs/T_G_C2_DESIGN_PREREG_2026-10-19.md`，draft_v4，**790 行**，SHA256=`c6f2612df4aa9ca1ab2e51fb94e0f0b3c23de1f59e691cd9b3a99c5e4f3fa579`。以下被审稿行号均指该字节版本。
>
> 实际执行来源为本会话三个子代理：`review_p1`（公共入口合成接线）、`review_consistency`（全文/历史一致性）、`evidence_steward`（独立表格/版本/完整性）。主会话只读抽查源码和证据，**没有另行独立重跑这些探针**。结论采信到文稿、源码与本次实际执行互证的范围。

## 1. 固定验收面与逐项裁定

本轮继承 v3 报告唯一未闭合的 **P1-C2-02**，只查“同输入、既有 C1 不被跳过、供给检查不被 raw 中心命中绕开”及 v4 引入的同契约矛盾。已关闭的歧义硬拒、错桶、芳香范围项保持关闭；未实施、unsupported、保守过拒、尚待 CC 选路线本身不构成本轮新阻塞。

| 用户请求 | 裁定 | 被审稿位置与主要证据 |
|---|---|---|
| 1① F1–F5 解耦、两种 builder 反证 | **闭合** | `:378-399` 真源/顺序；本轮 [p1/route_results.json](review_evidence/t_g_c2_codex_v4_2026-10-19/p1/route_results.json) 的 `ordinary_bag`、`wildcard_bag` 三口径对照 |
| 1② 全入口与 recorded 消费者 | **闭合** | `:402-410` 七行入口表与 `:755-773` 附录一致；源码互证见 [p1/findings.md](review_evidence/t_g_c2_codex_v4_2026-10-19/p1/findings.md) §1、[consistency/findings.md](review_evidence/t_g_c2_codex_v4_2026-10-19/consistency/findings.md) |
| 1③ §6.2 四行及公共链调用账 | **覆盖原两类验收** | `:635-658`；四行及额外 no_supply 辅助控实际执行，全部断言通过；证明范围见 §3 |
| 1④ R1/R2′ 两路线交 CC | **如实保留** | `:39`、`:531-543`、`:593-608`、`:692`、`:752`、`:790`，未自行选定 |
| 1⑤ 轻刀 B 动 F1 的互斥关系 | **成立，限当前设计** | `:287-291`、`:368-373`、`:541-543`、`:746`、`:758-760`；B 改的就是 R2′ 要求原样冻结的 F1 判据 |
| 2 表格/历史/可达口径及新矛盾 | **无新 P0/P1/P2** | 22 张表列数一致；v3/v2 历史块未改；R2′ 可达数始终待冻结接线后重算。两处非阻塞元信息澄清见 §4 |

## 2. 原 P1-C2-02 为什么可以关闭

### 2.1 路由事实先确定，中心 helper 不得反改

当前源码中，`s5b_builder.py:1115-1125` 的旧元素前门支配是否尝试供给；wildcard 诊断位于该拒分支的 `:1128-1133`；供给输入组装在 `:1134-1136`，二次门在 `:1137-1138`，未 rescue 记账与直编在 `:1197-1216`。所以单纯把旧前门换成中心命中，确实会改变分支及输入。

v4 `:380-386` 将这些决定拆清：

| 事实 | 唯一来源与作用 | 不得扩大到的作用 |
|---|---|---|
| F1 | 原 `template_elements_fit(mapped_lhs, substrate)`；只决定 raw 直编路由或供给分支 | 不再授予新编译层准入；不得用 raw 中心命中代替它 |
| F2 | 原 `analog_cosub_supply`；原样产生 supply/no_supply/wildcard_blocked 及供给内容 | 不由 F5 重算或改变 |
| F3 | F2=wildcard_blocked；原计数+1，不供给、不编译 | F5/raw 中心命中不得解除或抢先越过 |
| F4 | F1 过用 raw；F1 拒且 supply 用原加袋串；no_supply 用 raw | F5/编译/诊断装配不得另选输入；F5 与编译必须消费同一串 |
| F5 | 与中心枚举同源的新 helper，只对 F4 作新的结构准入判断 | 过门仍要接受编译/编辑等下游检查，不是完整化学许可 |

`:390-399` 的可执行顺序为 **F1 →（仅 F1 拒者）F2 → F3 → F4 → F5 → 编译或拒绝**。F1 过时不调用 F2 是原基线策略；本稿保护的是既有 F1 拒分支的 C1 拦截，没有给所有 F1 过候选另加一套 wildcard 检查。`F1–F4` 共用一次计算、同一版本与输入事实；F5 无权改变它们。由此，上轮 raw 中心命中不能再跳过两种反例本来应该走的供给/C1 路径。

**同输入不等于同可达。** F1 拒、F2=no_supply、F5 过的候选可以在 R2′ 下新增进入编译；这是 `:388-395`、`:407` 明示的准入变化。冻结的是供给策略和执行输入，未承诺候选结果与基线全部相同。R2′ 的正式可达数仍需接线冻结后重算。

### 2.2 七个入口没有各自另设判据

`:402-410` 将前门、wildcard、供给后二次门、未 rescue、直编、编译层声明、recorded 公共消费者逐行登记，附录 `:755-773` 同步：前门保留 F1、准入交 F5；二次门只作 F5 准入位；未 rescue 承接 F3 或 F5 拒；直编的路由进入条件仍是 F1 过，且必须先过 F5。

`recorded_source.py:1251/:1519/:1708 → compile_recorded_reaction:2060 → compile_donor_template:2126` 消费公共编译器，源码无 recorded 独立 `template_elements_fit` 前门。v4 不给该通道新增 analog 路由门，只保留公共编译器变化所需的既定回归、非目标字节不变和池对拍义务，边界成立。compiler 文档/不变量与版本键更新也已登记；本轮未要求实施未来阶段功能。

### 2.3 路线与轻刀 B 保持由 CC 决定

R1 仍是“前门与路由全不动”；R2′ 是上述解耦接线。正文、验收表和附录均交 CC 在预注册确认时选择。轻刀 B 会修改 `s5b_compiler.py:138-163` 的同一个元素 helper 判据；builder `:1115` 正用它决定供给路由，所以 B 会改变 R2′ 要求冻结的 F1 真源。两者在**当前同一函数、同一版本、单变量约束**下互斥，论证成立；不宣称未来另设变量/版本的组合永远不可能。

## 3. 本轮程序互证及证明范围

公共执行入口为复制源码中的真实 `default_pool_provider(...)(substrate)`；注入纯合成 donor resolver，关闭 engine/corpus 入口，`min_unique_targets=0`。旧元素谓词和 `analog_cosub_supply` 使用复制源码的真实函数。

三个口径分别是：真实当前基线 `baseline_current`；只在内存换旧门谓词的反例 `v3_gate_only_swap`；按文稿 F1–F5 在 AST 内存中替换 provider 内 `_compile_analog_refs` 的 `draft_v4_reference`。第三者是**评审参考接线**，不是生产实现；外层公共入口、诊断/失败记账和池返回沿真实代码。源码文件及隔离副本字节均未修改。

| 纯合成用例 | 当前公共基线 | 旧换门反证 | v4 参考接线经公共入口 |
|---|---|---|---|
| §6.2 #1 普通 `[Na+:4]` 袋，`CCO` | 供给 1 次=supply；编译输入 `CCO.[Na+]` | 供给 0；编译输入变 `CCO` | 供给 1 次=supply；F4/F5/编译均用 `CCO.[Na+]`；编译 1 次 |
| §6.2 #2 wildcard `[*:4]` 袋，`CCO` | 供给 1 次=wildcard_blocked；计数 1；编译 0 | 供给/C1 检查 0；编译 1 次用 `CCO` | 供给 1 次=wildcard_blocked；计数 1；F5 0 次；编译 0；no_alignment 1 |
| §6.2 #3 无袋 `CCO` | F1 过、供给 0；真实冻结编译器 compiled `CC=O`，公共池 1 件 | 不适用 | F1 过、供给 0；F5 输入 `CCO`；真实冻结编译器 compiled `CC=O`，公共池 1 件 |
| §6.2 #4 供给后中心不过：`CCC`、同 #1 模板 | supply 1 次；旧二次门拒；编译 0 | 不适用 | supply 1 次；F4=`CCC.[Na+]`；F5 不过；编译 0；no_alignment 1；路由/输入不变 |
| 额外 no_supply 辅助控：远端 Cl 模板、`CCCO` | F1 拒、供给 1 次=no_supply；编译 0 | 不适用 | 供给仍 1 次=no_supply；F4/F5/编译均用 `CCCO`；编译调用 1，不私造供给 |

四行对应 `:647-650`；#1、#2 一对一覆盖上轮“普通袋输入保持”和“wildcard 不绕过”，#1/#3 为供给/无供给正控，#4 防止 F5 只做装饰。`:640-643`、`:653-655` 要求沿公共 builder 链断言供给次数/状态、F4 输入、wildcard 计数、F5 判定输入、编译次数/输入，足以覆盖原固定验收，且不以全面拒绝换通过。

主模板为 `[CH3:1][CH2:2][OH:3] → [CH3:1][CH:2]=[O:3]`；两种独立袋前后不编辑。#4 为本轮自造 `CCC` 缺氧负控。额外控使用单组分远端 Cl 模板，两壳层合成查询为 `CCCO`。**F5 在本轮用明确的普通重原子查询 `CCO`/`CCCO` 作参考，未认证未来正式中心 helper。** #1/#2/#4/额外控的编译函数为记录输入后拒绝的桩，只证明分支、调用、输入与诊断；#3 使用真实冻结编译器，提供不被全面拒绝的合法正控。compiled 也不代表完整机制或生物可行性。

机读 schema=`t_g_c2_v4_p1_synthetic_routing_review_1`，`matrix_rows_executed=[1,2,3,4]`，`all_assertions_passed=true`；首次执行退出 0，无失败重试。版本仍为 `s5b-compiler-3` / `s5b-pool-policy-7`。详见 [完整调用/事件账](review_evidence/t_g_c2_codex_v4_2026-10-19/p1/route_results.json)、[参考函数](review_evidence/t_g_c2_codex_v4_2026-10-19/p1/reference_inner.py)、[执行清单](review_evidence/t_g_c2_codex_v4_2026-10-19/p1/execution_manifest.json)。

## 4. 无新引入的同契约阻塞

| 核验 | 实际结果与限制 |
|---|---|
| 表格管道一致性 | 两个标准库核算独立得到 **22 张表、0 处列数异常**；steward 解析完整代码跨度、转义管道和反斜杠奇偶，5 项解析正负控通过。见 [audit_result.json](review_evidence/t_g_c2_codex_v4_2026-10-19/steward/audit_result.json) |
| v3/v2 历史记录 | 从旧精确临时路径恢复 v3 全稿，先算 SHA256=`215315f562e0ccb6a81b7cd9dbb5ee6859cbdf0a79b5383b9c091efef94a9557`，再归档；v4 当前 `:63-133` 历史总块及两个子块与该 v3 逐字一致，总块 SHA256=`63bf15ac0a28d94f5a07e75e9b15dff173b083daec64ac8cec7854c7fa78ef76`。证明 v4 未回写 v3/v2 修订记录；**没有独立恢复原始 v2 全稿**。见 [精确 v3 副本](review_evidence/t_g_c2_codex_v4_2026-10-19/consistency/design_v3_sha215315f5.md)、[全文 diff](review_evidence/t_g_c2_codex_v4_2026-10-19/consistency/v3_to_v4.diff) |
| R2′ 可达口径 | `:58`、`:439-446`、`:537-543`、`:561`、`:587`、`:608`、`:692`、`:752`、`:780-782` 均明确接线冻结后重算。165/58、45/68、39/24 等均保留为 **298 旧原型/旧路径工程记账**，未转写成 R2′ 正式收益或成绩；本轮不将这些台账数字作为成绩或正式收益背书。裸 R2 仅作历史/反证命名 |
| 已关闭项 | v4 `:41-45` 明示收严旧门替换表述；旧历史块保持不变。没有新的同契约代码/公共链反例，不重开 P1-C2-01、两条 P2 或另加阶段门 |

两处非阻塞澄清如下，均不改变设计、输入身份或验收，不另立 P2、不要求再回修：

1. 请求称 v3/v4 SHA“均在文件头登记”；实际 `:13-14` 登记的是 v3/v2，没有 v4 自哈希。本轮实际 v4 哈希与请求的 `c6f2612d…` 吻合；不要求文件自登记自身哈希。
2. `:20-22` 把 `probe_audit/counts.json` 隐含列在 v3 证据目录下，该路径不存在。正确路径为 `docs/review_evidence/t_g_c2_codex_2026-10-19/probe_audit/counts.json`；`:65-67` 和附录 A `:723-725` 已可消歧。这是引用位置勘误，可随下次整理改正；本轮依纪律未修改被审稿。

## 5. 执行、哈希与纪律

所有程序核算都在各自新建临时目录执行；永久目录只保存脚本、输入副本与结果。公共链核验复制 `src`（含 `src/pathway_v43/vendor`）及 `pyproject.toml`，92 个复制文件与原仓前后字节相同；AST 参考函数只在内存构造。

| 专项 | 实际隔离命令/证据 | 退出与范围 |
|---|---|---|
| P1 公共链合成 | `/Users/cc/miniconda3/envs/depending43/bin/python /tmp/t_g_c2_v4_p1_4zrcg41j/review_routes.py`；cwd 同临时根，PYTHONPATH 为其 `repo/src`；[execution_manifest.json](review_evidence/t_g_c2_codex_v4_2026-10-19/p1/execution_manifest.json) | exit 0；schema=`t_g_c2_v4_p1_execution_manifest_1`；真实供给/旧门，参考 F5，桩边界见 §3 |
| 全文/历史 | `/private/tmp/t_g_c2_v4_consistency__ii62jjp` 内 `PYTHONDONTWRITEBYTECODE=1 python3 audit_consistency_v4.py`；[execution_manifest.json](review_evidence/t_g_c2_codex_v4_2026-10-19/consistency/execution_manifest.json) | exit 0；schema=`t_g_c2_v4_consistency_1`；标准库，不导入仓库模块 |
| 版本/表格/基线 | 新 `/tmp/t_g_c2_v4_steward.*` 内 `PYTHONDONTWRITEBYTECODE=1 python audit_v4.py /Volumes/CC/Enzyme_Agent/dependingv43`；[execution.json](review_evidence/t_g_c2_codex_v4_2026-10-19/steward/execution.json) | exit 0；标准库，只读文稿/源码与元数据字节和 git 状态 |

全部设置 `PYTHONDONTWRITEBYTECODE=1`；公共链环境同时设置 `PYTEST_ADDOPTS=-p no:cacheprovider`，本轮未调用 pytest。未执行原探针 main，未读取真实候选池、材料、金标、题面或封存逐题 run；未调用外部模型，未 push；未改源码、测试、被审稿或旧报告/证据。现有 dirty tree 作为输入状态保留，不能把它误报成本轮修改。

关键输出 SHA256：

| 文件 | SHA256 |
|---|---|
| `p1/route_results.json` | `475940e42b553bfdca86f06181b3051c1f1cf5054c9c15a01bb01fc150f80fb1` |
| `p1/reference_inner.py` | `3e53d0601596445f2d887ef2d54608b63650f1e2f30fd25c970b92d7ad2e047b` |
| `consistency/consistency_results.json` | `228b25a54aa90c089131f3b5e41f25b7a4356db8e3b8800eeba987309a769c79` |
| `steward/audit_result.json` | `db3f55c762a2b31c4442a86336b8940fc29278c57bd3930dc6218cfceb69dd30` |

最终完整性实核通过：298 项基线（含缺失可选元数据）无字节/存在性变化；src/tests 与旧两轮证据树无新增、删除或改写；原有 4 项 tracked dirty 文件字节保持；HEAD 与获准范围外 git 状态一致。本轮只新增获准报告及证据目录。详细结果见 [integrity_final.json](review_evidence/t_g_c2_codex_v4_2026-10-19/integrity_final.json)；总 [MANIFEST.sha256](review_evidence/t_g_c2_codex_v4_2026-10-19/MANIFEST.sha256) 排除自身，覆盖最终报告及本轮全部证据，并按最终报告文字计算 SHA256。

## 6. 交回 CC 的下一步

本轮无需再做设计回修。可以进入 **CC 预注册确认**：选择 R1 或 R2′，确认轻刀选项与版本/供给策略边界，按选定路线确定正式可达口径及验收线（含材料 ≥19 口径的拆分/合并选择）。R2′ 的可达数继续留待接线冻结后只读重算。CC 确认后再按冻结任务书实施，并沿 §6.1/§6.2 和既定回归矩阵交付；本次参考接线不能替代正式实现验收。
