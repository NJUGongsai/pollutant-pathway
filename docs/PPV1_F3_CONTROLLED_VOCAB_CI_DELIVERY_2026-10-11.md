# PPV1 F3 受控词表单一来源 + CI 双向断言 交付书（老师提效包 F3 项）

- 日期：2026-10-11（开工日）；实施轮：teacher efficiency-pack F3
- 基线 HEAD：8da11cb7（开工实测一致；工作树开工时 dirty=104 个未跟踪 docs/assets，已跟踪文件零改动）
- 交付 commit：见本文件所在 commit（不 push 不部署；chain12 远端批次与本地零冲突——本地改动不外发）
- 红线自查：零模型零网络零花费（0 调用 0 CNY）；金标/题面/封存逐题 run 零读取（全部工作面 = src 常量/提示词字符串/新测试/源码 ast 只读扫描）；判分/scorer/AtomTool 行为语义零改动（atom_tool.py 零触碰一字）；不 push

## 1. 任务与根因

**任务原文**：全部受控词表（op/order/side/status/output_origin）从执行器常量单一来源生成 + CI 双向断言——防止"提示词词表与执行器词表漂移"再犯。

**事故背景（57ea99b4，2026-10-09）**：S5b 应急提示词手写键级词表 `single|double|triple|aromatic`，执行器 `atom_tool._BOND_TOKENS` 只认凯库勒三词；模型按提示词规范输出 `to_order=aromatic`，执行器 `KeyError` 整题崩溃（chenyu 冒烟 2/10 题，RXNG_22901c/RXNG_330df2）。根因 = 提示词词表与执行器词表**两处手写、无同步机制**。

## 2. 关键结论（先看这里）

1. **提示词哈希字节不变（设计红线达成）**：`_PROPOSALS_SYSTEM_PROMPT` 改为从受控词表单一来源拼接生成后，渲染输出与基线 8da11cb7 手写版**逐字节一致**（4360 字节，sha256 = `e28b5342b0036a6af0893ca310045bed9d0e9d8bfc85f3d21c880e9a7917b962`）。⇒ `PROPOSALS_PROMPT_VERSION` 不变 ⇒ **批身份 / 批 resume 语义零影响**，chain12 在跑批次与后续新批的提示词身份不受任何扰动。此锚点被 CI 测试 T1 写死（此后任何词表演进改变拼接结果 ⇒ T1 红 ⇒ 显式决定升版，不静默漂移）。
2. **单一来源**：新模块 `src/pathway_v43/pollutant/controlled_vocab.py`，全部词表从**执行器/权威模块既有常量导入**并集合化（零复制、零新事实、零行为变化）；唯三"首次常量化"（OUTPUT_ORIGIN / ALIGNMENT_STATUS / PRODUCTION_REPORT_STATUS 族）为原有字面量的搬运，值域零变化。
3. **CI 断言族**：新测试 `tests/test_controlled_vocab_ci.py` 17 件（T1-T12 + D1-D7 漂移注入），正向/反向/孪生一致/字面量登记四层。
4. **四组回归**：定向 557/0（30 文件）；全量 not slow **2078/0/16**（= 基线 2061 + 17 新测试，364s，零回退）；G01 隔离 exit 0（数字见 §6.3）；父红绿：父 8da11cb7 上新测试 ImportError 红（纯新增依赖红，本轮零行为改动、无行为红——如实登记），父既有面抽验 57 绿。
5. **零行为改动面**：atom_tool.py / audit.py / runflow.py / store.py / queue.py / events.py / search.py / hypothesis.py / s5b_compiler.py / model_protocol.py 全部零触碰；只动 2 个新文件 + real_model.py 提示词段（渲染字节不变的拼接改造 + 一处 import 块新增）。

## 3. 词表散落点全景清单（开工摸底实测）

| # | 词表族 | 权威定义（单一来源锚） | 提示词面 | 其他散落点（本轮不改源码，CI 锚定） |
|---|--------|----------------------|----------|--------------------------|
| 1 | 编辑操作 op | `services/atom_tool.py:73 _EDIT_OPS`（break_bond/form_bond/change_bond_order/add_atom） | real_model 契约段（**本轮改为生成**） | s5b_compiler 产出 edits 字典字面量；audit 消费 |
| 2 | 逐操作字段 schema | `atom_tool.py:75-81 _EDIT_OP_FIELDS` | real_model 契约段字段名（静态） | validate_edits 校验 |
| 3 | 键级 order | `atom_tool.py:82-86 _BOND_TOKENS`（single/double/triple，凯库勒空间）+ `:89 _BOND_ORDER_N` | real_model 契约段 from_order/to_order 枚举（**改为生成**） | s5b_compiler.py:106-119 `_ORDER_NAME`/`_ORDER_OF_TOKEN` **孪生映射**；real_model.py:269-273 execution_graph 内联映射 |
| 4 | 图事实键级词 | execution_graph bonds[].order 的 "aromatic" fallback（只读图描述，**非可编辑词**——57ea99b4 根因即两面混写） | 不入 edits 词表 | real_model/s5b_compiler 字面量 |
| 5 | action 状态 | `search.py:252-256 ACTION_STATUS_*`（pending/claimed/done/deferred/blocked） | 不入提示词（内部豁免） | queue/store/runflow/native_export 经 import 常量 ✓ |
| 6 | attempt 状态 | `search.py:262-265 ATTEMPT_STATUS_*`（open/recorded/failed/abandoned） | 不入提示词（内部豁免） | queue/store 经 import 常量 ✓ |
| 7 | 展开计划状态 | `events.py:41-46 EXPANSION_STATUSES`（expanded/deferred/not_tracked） | 不入提示词（事件载荷契约） | store 校验（import 常量 ✓）；runflow/queue 消费；plan_status="incomplete" 字面量（store） |
| 8 | deferred 两类 | `queue.py:60-63 DEFERRED_TYPES` | 不入提示词（内部豁免） | queue 内部 ✓ |
| 9 | provider kinds | `search.py:271-274 PROVIDER_KINDS`（real/scripted/fake） | 不入提示词（内部豁免） | model_protocol/search 校验 ✓ |
| 10 | 侧别 side | `hypothesis.py:77-80 PARTICIPANT_SIDES`（reactant/product） | 不入提示词 | store:989/1016、runflow:594/643、audit:1013/1017、s5b_scoring:631、recorded_source/v3_projection 等**字面量** |
| 11 | 角色 role | `hypothesis.py:82-90 PARTICIPANT_ROLES`（primary_substrate/cosubstrate/principal_product/coproduct/unknown） | 不入提示词 | recorded_source:1928-1936、production、reference_graph 等**字面量** |
| 12 | output_origin | 原无常量：real_model:95/133（提示词声明）+ runflow:921（默认值）两处字面量 | real_model 契约段（**改为生成**） | runflow:921 默认值（T11 登记锚定） |
| 13 | alignment status | 原无常量：audit.py:2628 字面量 tuple（resolved/ambiguous/unavailable，校验值域）；s5b_compiler:1069 产出 "resolved" | real_model 契约段示范 resolved（**改为生成**） | audit:2628/2787、s5b_compiler:1069 字面量（T10/T11 锚定）；提示词只示范 resolved，ambiguous/unavailable 为审计值不入提示词（豁免登记） |
| 14 | 生产报告状态 | production._report 取值域（method_failed/deferred/rejected/submitted，散落字面量） | 不入提示词 | runflow:1377 消费 "deferred"（T11 登记锚定） |
| 15 | 编辑协议 v2 废除词 | atom_tool validate_edits/execute_edits 严格四操作（remove_atom 已废除；remove_bond/add_bond 旧别名 v2 面一律 unknown_op 拒）。注意 `check_edit_references`（Phase B 旧引用核验入口）代码内仍宽松接受旧别名——两属不同入口面，如实按面区分 | RETIRED_EDIT_OPS 清单（提示词出现任一 ⇒ CI 红） | — |

另有 services 侧同名词族（prediction.py 的 mapping "resolved"/"unavailable"、analog_source.py 的 MAPPING_RESOLVED、donor_applicability 的 mapping_status）属 **dev/298 题域不同字段族**，按题域标签纪律不入本轮 PPV1 断言面（豁免登记）。

## 4. 单一来源设计

### 4.1 模块

`src/pathway_v43/pollutant/controlled_vocab.py`（新建，放 pollutant 侧的理由：词表消费方主要在 pollutant 域，而编辑词权威在 services/atom_tool——pollutant → services 是既有合法依赖方向，反向会引入环）：

- **A 编辑协议**：`EDIT_OPS` / `EDIT_OP_FIELDS` / `BOND_ORDER_TOKENS` / `BOND_ORDER_N` = atom_tool 私有常量的**直接别名**（同一对象，零复制）；`BOND_ORDER_ALTERNATION = "|".join(BOND_ORDER_TOKENS)`（= "single|double|triple"）；`RETIRED_EDIT_OPS`（协议 v2 废除词）；
- **B 图事实词**：`GRAPH_ORDER_AROMATIC` / `GRAPH_ORDER_FACT_TOKENS`（凯库勒三词 ∪ aromatic，只读图描述）；
- **C-I 状态/计划/deferred/provider/侧别/角色/output_origin/alignment/生产报告**：全部从权威模块常量导入并集合化（`ACTION_STATUSES` 等）；OUTPUT_ORIGIN / ALIGNMENT_STATUS / PRODUCTION_REPORT_STATUS 三族为原有字面量的**首次常量化**（值域零变化）；
- **INTERNAL_ONLY_VOCABS**：九个内部族（不入提示词）的豁免登记面（CI 反向断言用）；
- 导入链无环（controlled_vocab → search/queue/events/hypothesis/atom_tool 均为叶子方向；real_model → controlled_vocab 新增，real_model 本已 import search）。

### 4.2 提示词改造（字节不变红线）

real_model.py：`_PROPOSALS_SYSTEM_PROMPT` 从单一三引号字面量改为 **7 段拼接**（4 个静态段 `"""..."""` 原文不动 + 3 个 f-string 词表声明段）：

- `_PROMPT_SEGMENT_OUTPUT_ORIGIN`（:95 行）：`"output_origin": "{OUTPUT_ORIGIN_NOVEL_OUTSIDE_POOL}"`；
- `_PROMPT_SEGMENT_EDITS`（:101-107 edits 契约段）：四操作名 `{_OP_BREAK/_OP_FORM/_OP_CHANGE/_OP_ADD}`（`EDIT_OPS` 四元解包——长度/顺序变化导入期 fail-fast）+ from_order/to_order 枚举 `{BOND_ORDER_ALTERNATION}`；
- `_PROMPT_SEGMENT_ALIGNMENT_STATUS`（:111 行）：`"status": "{ALIGNMENT_STATUS_RESOLVED}"`。

**验证**：拼接结果 sha256 == 基线冻结值 e28b5342…（4360 字节、55 行换行逐项一致）——见 §2.1。规则文本（Rules 段）与 Example 段保持字面量（叙述实例非枚举声明），由 CI 检测器全文兜底。

### 4.3 消费入口矩阵（返工教训 #1：先列入口）

| 入口 | 消费 | 本轮改动 |
|------|------|----------|
| real_model 提示词生成（`_PROPOSALS_SYSTEM_PROMPT`） | 词表声明段 | **改为单一来源拼接（字节不变）** |
| real_model `ppv1_real_fetch` / `ScriptedRealModelAdapter._complete` | system_prompt 运行时传入 | 零改动（同一运行时字符串） |
| model_protocol `parse_model_proposals` | output_origin 非空校验（自由文本） | 零改动 |
| runflow decide 层 novel prevalidation | `validate_edits`（同一执行器常量） | 零改动 |
| atom_tool `validate_edits` / `execute_edits` | `_EDIT_OPS`/`_EDIT_OP_FIELDS`/`_BOND_TOKENS` 权威 | 零改动 |
| s5b_compiler 三个编译入口 | `_ORDER_NAME`/`_ORDER_OF_TOKEN` 孪生 + edits 产出 | 零改动（T10 锚定一致性） |
| real_model `execution_graph_payload` | 内联 BondType→token 映射 + aromatic fallback | 零改动（T12 运行时锚定 + T11 登记） |
| store 展开计划校验 | `EXPANSION_STATUSES` 常量 + "incomplete" 字面量 | 零改动（T9/T11 锚定） |
| audit alignment 校验 | :2628 字面量 tuple | 零改动（T10/T11 锚定） |

## 5. CI 断言族（tests/test_controlled_vocab_ci.py，17 件）

- **T1 哈希稳定**：`PROPOSALS_PROMPT_VERSION == e28b5342…（基线冻结字面量）`+ 字节数 4360——单一来源改造不升版；此后词表演进 ⇒ 红 ⇒ 显式升版；
- **T2-T8 提示词↔执行器双向同步检测器**（`_assert_prompt_vocab_sync(prompt)`，对任意文本可用）：
  - T2 正向：`"op"` 声明 ⊆ EDIT_OPS（声明位教执行器不认的词 ⇒ 红——aromatic 事故同型）；
  - T7 反向：四操作全声明（删声明 ⇒ 红）；
  - T4 双向：from_order/to_order **枚举声明**（含 "|" 的 alternation）split 后 == 凯库勒三词集合（加词/删词 ⇒ 红）；实例值（Example 段单一值）⊆ 词表；`test_t4_*` 另断言枚举串 = `BOND_ORDER_ALTERNATION` 生成串（防手写回潮）；
  - T5 双向：output_origin 声明 == OUTPUT_ORIGINS；
  - T6 正向：alignment status 示范 ⊆ ALIGNMENT_STATUSES；ambiguous/unavailable 豁免登记（不入提示词断言）；
  - T3 正向：RETIRED_EDIT_OPS 三词与 "aromatic" 在提示词**任何形式**零出现（aromatic 是只读图事实词，混入可编辑词面即 57ea99b4 根因）；
  - T8：INTERNAL_ONLY_VOCABS 九族词以带引号 JSON 值形式零入提示词；
- **T9 权威同源**：controlled_vocab 各族集合 == 权威模块常量集合（字面期望写死，集合化零抄漏；BOND_ORDER_TOKENS 保序 tuple 快照钉死渲染序）；
- **T10 孪生映射一致**：`s5b_compiler._ORDER_OF_TOKEN == atom_tool._BOND_TOKENS`（dict 全等）；`_BOND_ORDER_N` 键域/值域；`_ORDER_NAME` 键集 = 四 BondType、值域 ⊆ 三词 ∪ aromatic、三词条目与 _BOND_TOKENS 反向一致；
- **T11 字面量消费点登记（ast 源码扫描，任务 d 的落地）**：扫描 pollutant 全家 + atom_tool（glob 动态枚举，新文件自动入面；剥 docstring；含 dict 键与 f-string 静态段；精确匹配词值），**发现集（154 项基线）⊆ 登记集**（新写受控字面量必须登记或走常量——防绕过）+ **登记词 ∈ 当前词表并集**（权威改值 ⇒ 旧字面量过期 ⇒ 红）。删字面量不破（演进自由）。能力边界如实登记：断言基于词值不基于位置语义，同词异义巧合覆盖（如 model_requests 状态 "failed" 与 ATTEMPT_STATUS_FAILED 同词）属保守面；
- **T12 execution_graph 运行时词域**：苯（凯库勒化 single/double）与乙醇（single）实盘锚定图键级 ⊆ GRAPH_ORDER_FACT_TOKENS；
- **D1-D7 漂移注入**（对提示词副本注入，检测器必须红）：D1 键级枚举混 aromatic（**复现 57ea99b4 前形态**）；D2 删 triple；D3 add_atom 声明位换 remove_atom；D4 break_bond→remove_bond；D5 output_origin 换非法值；D6 alignment status 换非法值；D7 add_atom 全词换 insert_atom（执行器词失可达）+ 注入红须携带逐词定位信息（多/少词列表）。

## 6. 验证与回归（四组 + 漂移注入演示）

### 6.1 漂移注入演示（红→绿，隔离 tmp 副本 /private/tmp/f3_drift_demo）

- 基线：17 passed；
- **场景 1（aromatic 事故复现）**：隔离副本 real_model 生成段手写回潮 + 加 aromatic ⇒ **3 failed**（T1 哈希漂移红：报"渲染字节与基线不一致，须显式升版"；T2-T8 检测器红：报"声明 [aromatic, double, single, triple] vs 执行器 [double, single, triple]（多 [aromatic]）"；T4 生成证据红）；
- **场景 2（权威词表改值）**：隔离副本 search.py `ACTION_STATUS_PENDING = "pending"` → `"waiting"` ⇒ **2 failed**（T9 同源红；T11 红：报 unregistered [('audit.py','waiting'),('search.py','waiting')]——新词进词表后，源码中同值字面量立即要求登记）；
- 还原后：17 passed（绿）。

### 6.2 定向回归

30 文件（新 CI + atom_tool + edit_protocol + donor/analog×3 + conservation + s3b model/queue/production/runner/r2/r3 + s5b 全家 17 文件）：**557 passed / 0 failed**（121s）。

### 6.3 全量回归（not slow）

**2078 passed / 0 failed / 16 deselected** = 基线 2061 + 17 新测试，**零回退**（首轮 364s；最终交付字节重跑 453s 复确认同数字）。

### 6.4 G01 隔离复跑

- 脚本：`/private/tmp/safe_g01_ppv1_f3.py`（fork hwall 版，同 allowlist 纪律；血统链 …→v4b→v4b_r1→cosub_d2→r1→r2→r3→hwall→**f3**）；
- 输入集：hwall G01 331 项 + F3 新增 2 项（controlled_vocab.py、test_controlled_vocab_ci.py）；
- **强制双向核对 vs hwall G01 输入集**：observed_changed == 1 项（repo/src/pathway_v43/pollutant/real_model.py）= expected_changed 逐项一致；new_inputs == 2 项逐项一致；missing == 0；
- 隔离运行：PYTHONDONTWRITEBYTECODE=1、no:cacheprovider、BBD_DATA_ROOT 指空、V3_CODE_ROOT 指隔离副本、禁止 evaluation/benchmark/data 树、输入 SHA 前后复验（333 项零失配）；
- 结果（**最终交付字节**重跑版）：**exit 0 = 2050 + 17 = 2067 passed / 10 skipped / 17 deselected / 1 warning**（416s；实际 HEAD 8da11cb7 + dirty=true 记入 preparation.json）；核对记录：observed_changed == expected_changed == ['repo/src/pathway_v43/pollutant/real_model.py'] 逐项一致、new_inputs_vs_hwall == 2 项（controlled_vocab.py / test_controlled_vocab_ci.py）逐项一致、missing == []；333 项输入 SHA 前后复验零失配；
- 如实披露：1 warning = chemstate.py 既有 docstring 无效转义的 DeprecationWarning（非本轮触碰面，不修源码）；测试子进程产生的游离 .pyc 逐文件记录在 post_run_sha_result.json（同 hwall 轮模式）；证据目录 /private/tmp/g01_ppv1_f3/（fresh 输出目录，不删任何日志）；

### 6.5 父红绿（父 = 8da11cb7 干净 worktree /private/tmp/f3_parent_wt）

- **红**：新测试文件在父上 `ImportError: cannot import name 'controlled_vocab' from 'pathway_v43.pollutant'`（collection error）——纯新增依赖红。本轮为 CI 增量轮，零行为改动，**不存在行为红**（如实登记；对照 hwall 轮的"行为红"形态）；
- **绿**：父上既有词面测试（s5b_runtime + atom_tool + edit_protocol）57 passed；父全量 = 基线 2061（8da11cb7 既有记录，本轮当前 HEAD 全量 2078 全绿 + 零回退双向支撑）。

## 7. 金标边界自查

- 金标/题面/封存逐题 run：**零读取**。漂移注入演示与全部测试只用 src 常量、提示词字符串、合成分子（苯/乙醇/CCO）；
- 提示词内容为规则级表述（不含金标不含题面），本次改造渲染字节不变，无新增外发内容；
- mimo 三触发点：本任务为纯工程 CI 项（不评判化学结构、不出题卷、不复核跑分结果），**不属任一触发点**，未发起 mimo 评审请求；
- 零模型零网络零花费：全轮无任何模型调用、无网络请求、无远端操作（不 push 不部署，chain12 在跑批次零干扰——本地提示词身份字节不变）；
- 判分/评测零 LLM：未触碰任何判分路径。

## 8. 待复审残留（如实登记）

1. **内部词表族的字面量未搬运为常量引用**：runflow/store/audit/s5b_compiler/recorded_source 等处的受控词字面量（§3 清单第 10-14 行）按任务书限定面（"只碰新模块 + real_model 提示词段 + 新测试文件"，避免与并行会话冲突）**不改源码**，以 T9/T10/T11 断言锚定同步；后续可另行一轮做常量化搬运（改动面更广，需独立授权与回归）；
2. **T11 基于词值不基于位置语义**：同词异义巧合覆盖属保守面（不会漏抓，可能多覆盖）；"该比较位本该用哪个族"的位置语义由既有行为测试族承载；
3. real_model `execution_graph_payload` 内联键级映射（:269-273 一带）未提为模块级常量（由 T12 运行时断言 + T11 发现集登记覆盖）；runflow:921 output_origin 默认值字面量同理（T11 登记锚定）；
4. atom_tool `check_edit_references` 旧入口仍宽松接受 remove_bond/add_bond（既有行为零触碰；RETIRED_EDIT_OPS 语义已按入口面如实区分——v2 严格面不认、旧入口宽松、提示词面一律禁）；
5. services 侧同名词族（prediction/analog_source/donor_applicability 的 mapping "resolved" 等）属 dev/298 题域不同字段族，按题域标签纪律不入 PPV1 断言面（豁免登记，未断言）；
6. 新增 import 链（real_model → controlled_vocab → search/queue/events/hypothesis）：全量绿证明无环无副作用；若未来重构 pollutant 模块拓扑需保持 controlled_vocab 叶子地位；
7. 测试数 2061 → 2078（+17），G01 血统输入集 +2（后续轮 G01 脚本应以此为父基线）。

## 9. Provenance

- 实施代理：ZCode（子代理，单人全程）；模型调用 0 次、网络 0 次、花费 0 CNY；
- 实际 HEAD：8da11cb7（开工=收工，无中途提交）；
- **并行会话如实登记**：本轮运行期间工作树出现并行会话对 `src/pathway_v43/pollutant/s5b_orchestrator.py` 的未提交改动（s5b-orchestrator-3 HPC 多作业分片适配线，199+/46-），与本轮四件交付物零文件交集、零 import 依赖（controlled_vocab 不 import orchestrator，反向亦然）；本轮 commit **不含**该文件（仅暂存的四件交付物）；两线共存验证：当前树（含该改动）下本 CI 测试 + s5b_runtime 37 绿、orchestrator 相关 w23456/v3r*cost 94 绿；全量 2078 与 G01 2067 的最终重跑均在该改动存在的工作树上完成；
- 工作树开工时 dirty = 104 个未跟踪 docs/assets（已跟踪文件零改动），本轮未动这些未跟踪项；
- 证据目录：/private/tmp/f3_drift_demo/（漂移注入红→绿演示副本）、/private/tmp/g01_ppv1_f3/（G01 隔离复跑全部产物）、/private/tmp/f3_parent_wt/（父红绿 worktree）、/private/tmp/f3_vocab_probe.py（发现集探针）、/private/tmp/safe_g01_ppv1_f3.py（G01 脚本）、/private/tmp/f3_full_run_result.txt（全量结果）；
- 交付物：src/pathway_v43/pollutant/controlled_vocab.py（新）、src/pathway_v43/pollutant/real_model.py（提示词段改造）、tests/test_controlled_vocab_ci.py（新 17 件）、本交付书；随轮 commit（不 push）。
