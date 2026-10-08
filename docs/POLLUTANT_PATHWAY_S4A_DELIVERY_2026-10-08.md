# pollutant_pathway_v1:S4a 首批交付书(endpoint 分账与原生结果底座,2026-10-08)

- 基线:直接父 `adf0287abef0c4803962fee0df0065d8e6f3793d`(S3b-r3
  交付/S3 工程交接点);开工 HEAD `0e345e83de27e7369334fe092da7a6ccbc8afd6c`
  (仅评审文档入库,src/tests 与 adf0287 同字节,已核对
  `git diff adf0287 -- src/ tests/` 为空);本批 = S4 任务书 §7 S4a
  边界的**一次性实施**:**只做 S4a**(endpoint 分账 + 原生结果
  底座),不做 S4b(正式文件导出/v3 有损适配/完整端到端链/完整
  G02 文件级过期矩阵)。
- 范围(任务书 §2.A + §7 S4a 十项):endpoint record/schema 与版本
  注册、execution/stop/endpoint/bookkeeping 四分账、证据与根碳账
  字段、F01/F02/F03、stop 与 endpoint 独立持久化、endpoint 读取/
  首消费/staleness+integrity 校验、原生结果对象完整字段与确定性
  规范化、endpoint-only scripted 公共链、正控/unknown 控/partial
  控/停止控/重复来源控、**v3 适配未实施**(只建立不改 legacy 的
  明确边界 = 零触碰)。
- 判据状态:**ppv1-criteria-v1 已冻结**
  (`docs/POLLUTANT_PATHWAY_CRITERIA_FROZEN_V1_2026-10-08.md`,
  底本 = mimo 请求 v15);**本批未修改冻结判据正文**(判据一–五
  与 0d/0e 语义零触碰;mimo 请求 v16 按版本规范附"语义未改变"
  声明,见 §17)。工程登记面增量(store-10/profile-15/runflow-4)
  见 §6 版本一节与 §19 残留。
- 证据根:`docs/review_evidence/ppv1_s4_impl_2026-10-08/s4a_r1/`
  (README + manifest.json + SHA256SUMS;全部执行在仓外新 tmp 或新
  worktree;G01 控制器随目录,拒绝已存在输出目录)。

## 0. 结论一句话

S4a 十项全部落地:公共 start/resume 在驱动结束后把**四分账**
(execution_status / search_stop_reason / chemical_endpoint_
assessment / bookkeeping_status)独立持久化于两张新派生投影表
(store-10),终点评估**只**由冻结计划的来源层直报证据决定
(F01 停止非终点/F02 未知依赖不洗白/F03 去重不增独立支持),
根碳账只表达核查范围(账平不当矿化、备选 CO₂ 不相加),endpoint
记录有首消费(版本门/hash/跨表引用/staleness 五负控 + 正控),
原生结果对象聚合全部路径事实并确定性规范化(同事实同 digest);
PPV1 全量 **914 passed/0 skipped**(879 存量 + 35 新 S4a,零存量
行为改动;仅 2 个 profile 版本字面量更新如实披露);直接父
adf0287 同字节对照 = 新文件 **35 collection 红(模块缺失)+ 更新
测试 2 版本字面量红 + 21 正控绿**,0 行为红;G01 安全隔离
**1516 passed/8 skipped/17 deselected exit 0(291 输入)**;
production.py 与全部 legacy/化学共享核心**逐字节同父**;S4b
(正式导出/v3 适配/完整端到端)未做,逐条列于 §20。

## 1. S4a 十项内容:源码位置与前后行为

| # | 任务书 §7 S4a 项 | 源码位置(file:line) | 前行为(adf0287) | 后行为(本批) |
| 1 | endpoint record/schema 与版本注册 | `src/pathway_v43/pollutant/endpoint.py:709-804`(derive_run_endpoint 构造 record)、`profile.py:198-203`(ppv1-endpoint-1 / endpoint-policy-1 / native-result-1)、`profile.py:219-222,237-239`(contract_versions 注册)、`store.py:353-366`(两张表) | 无 endpoint 概念;summary 只有 stop/stop_reason/counts | run 级 endpoint 四分账 record(载荷不含时间戳 ⇒ 同事实同 hash) |
| 2 | 四分账 | `endpoint.py:95-98`(execution 枚举)、`endpoint.py:727-745`(四字段独立赋值)、`runflow.py:1476-1483/1606-1623`(start/resume 接入 summary) | 停止原因 = 唯一"结束状态" | 四者独立存在互不代替;stop_reason_records 与 endpoint_records 分表,endpoint 只按 payload_hash 引用停止记录(`endpoint.py:729-735`) |
| 3 | 证据/条件/proof scope/根碳核查范围字段 | `endpoint.py:120-161`(枚举)、`endpoint.py:215-265`(证据条目契约:11 字段)、`endpoint.py:372-458`(bookkeeping:coverage/fate/CO₂)、`endpoint.py:343-370`(条件快照) | 无终点证据字段 | evidence_basis/claim/source_refs/support_scope/conditions/window/detection/necessary_dependencies/root_carbon_fate_check_scope/unverified_axes/proof_scope 全保留;coverage 只表示核查范围 |
| 4 | F01/F02/F03 | F01:`endpoint.py:460-558`(评估与停止互斥;无证据 ⇒ unknown)+ 测试六原因参数化;F02:`endpoint.py:298-341`(未解决依赖继承)+ `endpoint.py:517-525`(阻断);F03:`endpoint.py:192-213`(去重键/来源身份)+ `endpoint.py:462-500`(计数/披露) | 无终点判定 | 停止永不映射终点;recorded 边不进评估输入;存在未解决必要依赖 ⇒ unknown(evidence 保留);去重计数/来路保留 |
| 5 | stop 与 endpoint 独立持久化 | `endpoint.py:560-595`(put/read_stop_record)、`endpoint.py:598-614`(put_endpoint_record)、`store.py:353-366`(DDL)、`store.py:3-9`(v10 注记) | stop report 只在内存 summary 返回 | 两张派生投影表(纯增量);派生只读业务表(零 event/attempt/request/budget 写入) |
| 6 | 读取/首消费/stale+integrity | `endpoint.py:631-700`(read_run_endpoint:版本门/hash 复算/跨表引用/staleness 四摘要重算)、`endpoint.py:701-704`(consume 严格) | 无读取面 | 五类结构化拒(stale/corrupt/version_unknown/reference_mismatch/missing)+ 原行保全;`endpoint.py:616-629` 重算输入与派生同源 |
| 7 | 原生结果对象 + 确定性规范化 | `src/pathway_v43/pollutant/native_result.py:85-341`(build:22 字段组)、`native_result.py:70-83`(稳定排序/JSON 解析)、`native_result.py:343-355`(persist,digest 键不可变)、`native_result.py:357-374`(read + 摘要复算) | 无原生结果对象(只有 v3 冻结导出,legacy) | 同事实同 digest(载荷无时间戳);digest 键 artifact 幂等;字段组覆盖任务书 §2.B 可同源取得的全集(见 §12) |
| 8 | endpoint-only scripted 公共链 | `runflow.py:1476-1483`(start)、`runflow.py:1606-1623`(resume)、`runflow.py:1325-1351`(_derive_endpoint_and_native_result:派生→首消费读回→对象) | start/resume 止于 stop report | 公共入口 → 驱动 → 停止 → 四分账 → 首消费 → 对象底座,全链断言(测试 §8) |
| 9 | 正控/unknown/partial/停止/重复来源控制 | `tests/test_ppv1_s4a_endpoint.py`(35 用例,见 §12) | 无 | 全绿 |
| 10 | v3 适配不做/只建不改 legacy 的边界 | **零触碰**:`git diff adf0287` 不含 output/export_v3.py、atom_tool.py、workflow/runner.py;52 legacy 文件 + production/chemstate/path_context/hypothesis/events/audit/search/queue/model_protocol 逐字节同父 | — | 边界 = 不实施适配;v3 信息损失清单 N/A(见 §16) |

## 2. 与规格 §10/§11/§17 逐项映射

| 规格条目 | 本批落点 |
| §10 四分账(分别输出 execution/stop/endpoint) | §1 表行 2;stop 不覆盖终点(测试 test_f01_stop_does_not_overwrite_valid_evidence) |
| §10 search_stop_reason 六原因 + deferred 不称"搜索完毕" | 沿用 search-6 冻结优先级(endpoint.py:733 引用);stop 记录含 unexplored/deferred/blocked(测试 f01_zero_depth) |
| §10 endpoint 四值 + 无独立证据 ⇒ unknown | endpoint.py:105-124;六停止原因参数化测试 |
| §10 evidence_basis 四类;模型/推断不授 supported | endpoint.py:125-133, 460-500(测试 f03m/f03n0) |
| §10 bookkeeping 不当矿化;缺映射根碳 unknown;备选 CO₂ 不相加 | endpoint.py:372-458(测试 bk/bku/co2) |
| §10 终点源证据与模型推断分开;未解决必要依赖不升"本场景已观察事实" | F02(测试 f02/f02c) |
| §10 首版不自动推解毒 | 无解毒字段/无自动推导(mimo 0f.7 显式声明) |
| §10 原生导出保留来路/不按 CN 合并 | 对象底座(测试 preserves_distinct_routes);文件级导出 S4b |
| §10 v3 适配 lossy_projection | **S4a 未实施**(边界声明;legacy 冻结零触碰) |
| §11 S4 阶段行(endpoint 分账/路径原生结果/v3 有损适配/端到端) | 前两项交付;后两项 S4b |
| §17.3.5 evidence_basis 类型而非强度;观察期不自动更可信 | endpoint.py:125-133 注释 + 窗口为保留字段 |
| §17.3.6 root_carbon_accounting_coverage 表核查范围;来源矿化比例另存数值/计量/引用 | endpoint.py:150-158 + 证据字段载体(计量基础=source_support_scope/detection_range 字段) |

## 3. 与 S3B-R3 终审 §7.2/§7.4 逐项映射

| 交接约束(R3 §7.2 第 2 条 = S4 任务书 §4) | 本批落点 |
| F01 停止非终点 | §1 行 4;四公共链夹具 + 六原因单元全覆盖 |
| F02 未知依赖不被 recorded 洗白 | §1 行 4;未解决依赖继承 + supported 控制组 |
| F03 不同来路/重复来源不增独立支持;来路保留 | §1 行 4;三态去重测试 |
| 账目闭合不解释为矿化;备选 CO₂ 不相加;不自动推解毒;缺根碳去向保持 unknown | §1 行 3 |
| G02 导出确定性与过期可识别(旧 legacy 导出冻结) | S4a 交付对象级确定性(同事实同 digest)与 endpoint 记录级 stale;文件级 G02 矩阵(§4.4 七测)S4b 未做 —— 见 §20 |
| §7.4:继续消费恢复/ledger 首消费守卫;put_state 返回不当证书 | endpoint 派生只读业务表;上下文经 load_context(H07+内容身份)首消费(endpoint.py:298-341);put_state 未触碰 |
| §7.4:保留失败 None/unknown/partial;旧 run 不跨版本续跑;新批新根 | run_error ⇒ execution failed(不转成功);store-10 版本门拒旧库(旧 run 拒);全部测试新 tmp 根 |

## 4. 入口矩阵(任务书 §6 要求的 S4a 行)

| 入口 | 消费事实 | 独立权威 | 身份/版本绑定 | proof scope | 失败/unknown/stale 表示 | 对应场景/控制 |
| start_run(PPV1)→ endpoint derive | stop ledger/事件/上下文/冻结计划证据 | search_actions/events/state_appearances + path_context artifact + frozen plan | profile-15 契约块(含 endpoint-1/policy-1/native-result-1);record schema_version 门 | 评估只覆盖证据声明范围(不做机制/生物可行性) | 派生内契约违反 ⇒ EndpointContractError(已提交事件如实保留,endpoint 消费中止) | 四分账/公共链测试 |
| resume_run → endpoint 重派生 | 同上 + 恢复后当前事实 | 同上 | 同上(check_resume_identity 含 profile 块) | 同上 | 同上;事实变化 ⇒ record 更新(payload_hash 变化如实) | 幂等/崩溃恢复测试 |
| stop 独立持久化 | 会话 stop report(持久行派生 + 会话 refusals) | stop_reason_records 行 | record_version=ppv1-endpoint-1;payload_hash | 停止原因账(非化学) | hash 复算失败 ⇒ stop_record_corrupt | 分表断言 |
| endpoint 首消费(read/consume) | endpoint 行 + stop 行 + 当前事实摘要 | 两表行 + events/actions/证据/依赖 | 版本门 + payload_hash + 跨表引用 + derived_from 四摘要 + policy 版本 | 过期记录不包装成"正式结果" | stale/corrupt/version_unknown/reference_mismatch/missing 五 kind,原行保全 | 五负控 + 正控 |
| native result 构建 | endpoint 记录(已验证)+ 全部持久事实 | store 行 + H07 artifact | native-result-1;content_digest | 对象=事实聚合,不产生新判定 | 摘要复算失败 ⇒ digest_mismatch | 完整性/确定性/来路测试 |
| deferred/blocked/unexplored 消费 | search_actions 行(defer_reason/deferred_type) | 持久行(同 0e.6) | 同 search-6 | 停止账披露面 | 保留(不改写) | f01_zero_depth + 对象 deferred 字段组 |
| 失败状态消费 | run_error/expansion_outcome(attempts) | 持久行/artifact | 同 search-6 | 方法失败 ≠ 化学判定 | execution=failed;endpoint 恒不因失败转成功 | model 结构失败测试 |

## 5. 实际源码 diff 与提交引用

- 新增:`src/pathway_v43/pollutant/endpoint.py`(820 行)、
  `src/pathway_v43/pollutant/native_result.py`(374 行)、
  `tests/test_ppv1_s4a_endpoint.py`(825 行,30 函数/35 用例);
- 修改:`src/pathway_v43/pollutant/store.py`(+14 行 DDL/注记)、
  `src/pathway_v43/pollutant/profile.py`(版本/注册/delivered_stages)、
  `src/pathway_v43/pollutant/runflow.py`(接线 + docstring)、
  `tests/test_ppv1_profile.py`(2 处字面量:profile-15、
  delivered_stages 增 S4a-endpoint —— **本批唯一既有测试改动,
  如实披露**);
- 零触碰:output/export_v3.py、services/atom_tool.py、
  workflow/runner.py、production.py、chemstate.py、
  path_context.py、hypothesis.py、events.py、audit.py、
  search.py、queue.py、model_protocol.py、store 既有表/写入行为
  (git diff adf0287 逐文件核对);
- 提交:本地 v4.3 提交(不 push;显式路径 git add),哈希见
  `git log -1`(提交信息含本交付书摘要)。

## 6. 版本/身份/Hash 影响(逐项)

- **新增**:PPV1_ENDPOINT_SCHEMA_VERSION=
  `ppv1-endpoint-1`、PPV1_ENDPOINT_POLICY_VERSION=
  `ppv1-endpoint-policy-1`(固定规则,无用户可配项)、
  PPV1_NATIVE_RESULT_VERSION=`ppv1-native-result-1`;
- **升级**:store `ppv1-store-9 → -10`(纯增量两张派生投影表;
  旧库按版本门拒 = 旧 run 不跨版本续跑)、profile
  `ppv1-profile-14 → -15`(契约注册 + delivered_stages;run 身份
  块随之变 ⇒ 旧 run resume 按身份门拒)、runflow
  `ppv1-runflow-3 → -4`(公共入口接线);
- **保持**:search-6 / search-limits-3 / format-feedback-1 /
  model-proposals-2 / frozen-plan-1 / ppv1-*-8 化学契约族全部
  不动;production.py SHA 与父逐字节一致;
- **legacy 影响:零**(legacy code_identity 分集排除 pollutant/;
  52 份 legacy 文件 + 12 共享核心逐字节同父;聚合保持
  `18007e6a7cc239606eb30921f91045540446a7d7298108be30d47fce
  2f1374d6`,沿 r2/r3 复审核验值);
- **判据冻结面**:ppv1-criteria-v1 正文未触碰;冻结稿 §8 行号
  锚定条款的工程影响 = 本批改动的 runflow/store/profile 行号漂移
  (行为互证以 879 存量零改动全绿 + 逐字节 diff 为证;重锚待下
  一判据版本,如有)。

## 7. 实际测试命令与结果(depending43:Python 3.11.16 /
RDKit 2026.03.6 / SQLite 3.53.4;PYTHONDONTWRITEBYTECODE=1、
-B、pytest -p no:cacheprovider)

| 执行 | 命令 | 结果 | 证据 |
| S4a 焦点(当前树) | `pytest -q tests/test_ppv1_s4a_endpoint.py` | **35 passed / 0 failed,exit 0** | `current/s4a_focus.*` |
| PPV1 全量 | `pytest -q tests/ -k ppv1` | **914 passed / 0 skipped / 0 failed,exit 0**(879 存量 + 35 新;33 文件) | `current/ppv1_full.*` |
| 全量非 slow(含 legacy/export_v3 回归) | `pytest -q tests/ -m "not slow"` | **1525 passed / 16 deselected / 0 failed** | `current/full_nonslow.*`(注:该命令以终端运行,数字入 §0;G01 为其隔离口径等价复跑) |
| 父基线(同字节) | 见 §9 | 35 collection 红 + 2 字面量红 + 21 绿 | `baseline/*` |
| G01 安全隔离 | 控制器(s4a_r1/scripts) | **1516 passed / 8 skipped / 17 deselected,exit 0** | `g01/*` |

## 8. §8 验收矩阵逐行结果(S4a 范围行)

| 任务书 §8 行 | 入口→行为→断言→证据 | 结果 |
| endpoint 四分账 | 公共 start→derive;四字段独立;分表;summary 断言 + DB 行断言 | **通过**(test_endpoint_four_way_split_public_chain) |
| F01 停止非终点 | 六原因单元 + 零预算/零深度/空池公共链 + 停止不覆盖证据;deferred/未展开/预算原因保留 | **通过**(5 测试) |
| F02 unknown 依赖 | 上游假设(依赖 unresolved)→下游事件 recorded→endpoint;依赖继承;recorded 不升级 | **通过**(负/正控各 1) |
| F03 来源去重 | 同观察多包装/同来源多声明/不同来源;来路保留;计数用去重 | **通过**(4 测试含 no_evidence) |
| 根碳账 | 账平只表核查范围;未知系数 ⇒ unknown;备选 CO₂ 不相加(逐事件列示/聚合不产生) | **通过**(3 测试) |
| 终点证据 | direct/inferred/model/no_evidence 四类;字段充分性缺失披露;模型/推断不授 supported | **通过**(四类 + 缺失字段测试) |
| 终点条件 | essential 冲突假设保留不提交;条件快照保留 | **通过** |
| 原生结果完整性(对象级) | native export 行的 S4a 子集:对象含 state/path/events/alternatives/products/conditions/dependencies/audit/deferred/budget/stop/endpoint;字段 hash | **通过**(completeness/deterministic/来路 3 测试;文件级导出 S4b) |
| 失败状态 | run_error ⇒ failed 不转成功;契约异常中止 endpoint 消费(证据/事件不丢) | **通过**(2 测试) |
| resume/replay | 不重复写 event/attempt/request/budget;停止视图幂等夹具下 payload_hash/digest 稳定;四分账字段跨 resume 稳定 | **通过**(2 测试) |
| scripted E2E(endpoint-only 链) | start/resume→驱动→停止→endpoint 分账→首消费→对象;网络 0 | **通过**(全链断言;完整 export/v3 链 S4b) |
| G01 | 安全隔离源;skip/deselect 逐项披露 | **通过**(§10) |
| (S4b 行:导出确定性/过期/完整性/v3 适配/反向污染/legacy 回归行/完整 E2E) | — | **未做**(§20 逐条) |

## 9. 当前树 vs 直接父 adf0287 红绿分类

- 新文件 `tests/test_ppv1_s4a_endpoint.py` 同字节复制到 detached
  worktree(adf0287):**collection 红 35**(ModuleNotFoundError:
  `pathway_v43.pollutant.endpoint`;implementation missing 如实
  登记 —— 未 stub、未改 import、未弱化期望、未复制实现);
- 更新文件 `tests/test_ppv1_profile.py` 同字节:**2 版本/阶段
  字面量红**(ppv1-profile-15、S4a-endpoint —— 父合法实现
  profile-14;**expected behavior difference 类**)+ 21 合法
  正控绿;0 行为红;
- 分类 JSON:`baseline/parent_r1_classification.json`;父存量
  879 全量绿为 Codex S3b-r3 独立执行证成,本批不重跑冒称;
- "父基线出现红"≠ 旧错误;当前全绿 ≠ 科学正确(合成规则级)。

## 10. G01 安全隔离范围与结果

- 控制器:`s4a_r1/scripts/safe_g01_s4a_r1.py`(沿 R7→R8→S3a→
  S3b→r2→r3 白名单谱系;**新增 3 输入**:endpoint.py/
  native_result.py/test_ppv1_s4a_endpoint.py;修改的 runflow/
  profile/store/test_ppv1_profile 为既有白名单路径按当前字节
  复制、新 SHA);
- 291 输入(288 s3b_r3 + 3),SHA 前后一致
  (`g01/input_sha256.json`);固定空 BBD_DATA_ROOT/V3_CODE_ROOT/
  V43_ASSET_ROOT/DEPENDING_V3_ROOT;不复制 evaluation/gold/
  benchmark/sealed/v4;实际 HEAD(0e345e8 实施态)+dirty 记录;
- **1516 passed / 8 skipped / 17 deselected,exit 0**
  (1516 = 1481 s3b_r3 + 35 新;skip 逐项:5 真实冻结评价
  (test_batch_runner:52、test_score_report:110/163/172/184)+
  1 缺 v4 对照(test_analog_assets:95)+ 2 phase_d 派生
  (test_analog_v2_corpus:62/153);17 = 16 slow + 1 明确排除
  export 用例);
- 历史 1110/1138/1196/1250/1299/1389/1453/1473/1481 各自单列
  不混计;全部数字不外推 dev/298 科学性能。

## 11. 证据目录与 manifest

- 根:`/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/
  ppv1_s4_impl_2026-10-08/s4a_r1/`;
- 组成:README.md、manifest.json、SHA256SUMS、scripts/(G01
  控制器)、current/(焦点/全量 junit+stdout+stderr)、
  baseline/(worktree_setup.log、两父运行 junit+stdout+stderr、
  parent_r1_classification.json)、g01/(preparation/input_sha256/
  execution_result/junit/stdout/stderr)、mimo/(v15 送审快照,
  字节同父提交 adf0287)、metadata/(HEAD/parent/dirty/env);
- 全部执行在 /private/tmp 新目录(已清理父 worktree;G01 tmp
  保留至复审可随时删,证据已快照);永久证据目录未运行任何写库
  程序(仅复制结果文件);复现命令在 README。

## 12. scripted 输入、输出与断言(合成规则级;网络 0)

- 输入:计划 = 合成池(CCO→CC=O / CCO→O=C=O,冻结 AtomTool
  编辑协议形状)+ 可选 endpoint_evidence 声明(来源层直报夹具:
  study-A/B)+ 可选 condition_facts/dependencies/schedule_budget
  /model(scripted responses);
- 公共链输出断言:summary["endpoint"] 四字段 +
  endpoint_record_payload_hash + native_result.content_digest;
  DB 断言:stop_reason_records/endpoint_records 行、payload_hash、
  derived_from 四摘要;
- 原生对象断言:22 字段组(§1 行 7)非空/完整 + 两次构建同
  digest + 落盘读回摘要一致;
- provider:scripted(网络 0);model_requests 行数断言 0;
  无真实模型调用。

## 13. 预算/事件/attempt/来源/endpoint 账(代表性数字)

- 四分账公共链(CCO→CC=O 单事件):events=1、attempts=1
  (recorded)、states/hypotheses 各 2、model_requests=0、
  stop 主因 exhausted_search(或夹具指定原因)、execution=
  completed、endpoint=unknown(无证据)、bookkeeping=closed
  (系数已知);
- F02 夹具:同上 + endpoint 记录 inherited_unresolved_dependencies
  =1(dep-NAD,unresolved)、blocked_reasons=[unresolved_
  dependencies_inherited];
- F03 夹具:两条同声明同来源证据 ⇒ independent_source_support_
  count=1、distinct_observation_claims=1、endpoint_evidence=2;
- 独立支持计数与来源/观察身份的账全部在 endpoint_records.payload
  (evidence_summary);预算预约/消耗账在原生对象 budget 字段组
  (同 search 层派生,不复制判据)。

## 14. unknown/partial/deferred/stale/未执行段

- unknown:无证据/依赖未解决/系数未知/根碳去向 —— 均保持
  unknown 并披露原因(不猜数值、不升格);
- partial:claim 字段缺失 ⇒ missing_field_disclosures 逐字段披露
  (证据保留);
- deferred:stop 记录 unexplored + 原生对象 deferred_entries
  (两类分别,deferred_type/reason);
- stale:consume 五负控(§4);原行保全;
- 未执行段:本批不做 S4b 段(§20);模型结构失败夹具中,派生侧
  契约异常发生时 summary 不产出(测试断言零 endpoint/stop 记录、
  已提交事件如实保留,无"拒后报通过"段)。

## 15. legacy 未改动与回归证明

- git diff adf0287 名单(§5)不含任何 legacy/冻结文件;52 份
  legacy code_identity 文件 + production.py 等 12 共享核心逐
  字节一致(legacy 聚合沿 r2/r3 复审核验值 18007e6a…);
- legacy/export_v3 全量回归在当前树全量非 slow(1525 绿)与
  G01(1516 绿,含 -m "not slow" 全套)内执行;
- profile/runflow 的 PPV1 分流行为:31 份既有 PPV1 测试文件中
  30 份零改动全绿(唯一改动 = test_ppv1_profile.py 两字面量)。

## 16. v3 信息损失清单

**N/A(S4a 未实施 v3 适配)**:本批不产出任何 lossy_projection;
不修改 output/export_v3.py;不为填满旧字段编造终点/矿化/解毒/
来源支持(v16 请求 0f.10 边界声明)。信息损失清单与双向引用
边界属 S4b。

## 17. mimo v16 请求与送审状态

- `docs/mimo_ppv1_chem_review_request.md` 升级 **v16(S4a 批次
  版)**:新增 0f 节十一条(S4a endpoint 分账/证据/F01-F03/根碳
  账/持久化与首消费/原生对象底座/S4a 边界诚实声明/**语义未
  改变声明**),§0/§6/§7 同步(数字、契约族、判据冻结状态引用
  ppv1-criteria-v1);判据一–五与 0d/0e 正文一字未改;
- v15 送审快照(字节同 adf0287)存
  `s4a_r1/mimo/mimo_ppv1_chem_review_request_v15_sent.md`
  (SHA256 4d5974ee…);旧回应 r5–r15 原样保留不覆盖;
- 本批实施 agent 未调用任何外部模型;送审由主会话按 AGENTS.md
  通道 A 执行;回应落盘后按"与程序证据互证"采信。

## 18. 判据/科学性能/敏感资料声明

- 判据已冻结(ppv1-criteria-v1,用户 2026-10-08 拍板);本批
  未改冻结正文、未自动宣布任何新冻结;
- 科学性能 pending:全部数字为合成规则级契约结果,不代表 dev
  (B1 环境路径中间步骤)或 298(RHEA 通用酶学)科学性能;
- 未访问:金标/题面/封存逐题 run/真实评价数据/reports/data/
  evaluation/benchmark/dependingv4/冻结 v3 资产;真实 provider
  默认 off,网络请求 0;判分零 LLM。

## 19. 残留 P2(继承 + 本批新增,如实登记)

1. **停止视图的会话成分**:stop report 含会话 refusals 与
   no_local_candidate 会话观察,重复 resume 允许停止视图(与
   endpoint 记录引用)随之更新 —— 事件/预算零新增是硬边界
   (已测试);"停止原因跨会话完全同源"沿 S3 既有口径
   (blocked/deferred 同源持久,refusals 会话内存),未新增门;
2. **endpoint 证据是冻结计划合成输入**:来源层直报声明的
   真实性/现实来源认证不在本批范围(与 S3 池输入同一边界);
   来源标签逐字全链一致性仍为继承 P2;
3. **行号锚定漂移**:冻结判据正文行号锚 runflow/store/profile,
   本批改动使其漂移(行为互证以存量全绿+字节 diff 为证);下次
   判据版本(如有)须统一重锚;
4. **store-10 的 endpoint 行不抗全库协同改写**(与 S3B-01 锚同
   边界):无密码学签名;篡改会破坏 payload_hash 复算(corrupt
   拒)但自洽重写(hash 同步改)会过版本门之外的字段 staleness
   —— 由 derived_from 四摘要重算对照兜底(改事实 ⇒ stale;仅改
   记录自身且重算 hash ⇒ 需版本门/摘要对照组合,记录载荷可被
   自洽重写残留为已披露边界,同 S3 冻结计划自洽证书边界);
5. 继承 P2 不变:同机 flock、cache_hit 同构、两事务间外部 SQL
   窗口、foreign-run 反向诊断、stop 对象有界 100、三类
   RuntimeError 逃逸面、B2 口径。

## 20. S4b/S5 不在本批范围(逐条,不以 S4a 绿冒充完整 S4)

1. 路径原生**正式文件导出**(manifest/文件级格式)未做;
2. 确定性**重复生成的文件级验证**(两进程导出字节等价)未做
   (S4a 只证对象级同 digest);
3. **stale/integrity 的导出面识别**(graph revision/policy/
   source hash 变化 ⇒ 旧导出拒)未做(S4a 只证 endpoint 记录级);
4. 共同产物/备选/来路/条件/依赖/audit/deferred/预算的**全量
   导出文件**未做(对象字段组已备,未落导出契约);
5. v3 **lossy_projection 适配**未做;
6. 原生结果与 v3 投影**双向引用边界**未做;
7. legacy/export_v3 冻结**专项字节回归**(以全量绿 + 零触碰
   diff 为证,未另做导出字节专项对比脚本)留 S4b 补充;
8. start/resume→native export→v3 adapter→replay **完整公共链**
   未做(S4a 链止于对象底座 + endpoint 首消费);
9. G02 七项测试矩阵(§4.4)未做;
10. S4 全量回归 + 交付书 + mimo(本轮为 S4a 版)终轮未做;
11. S5(评测器/数据规范/预注册)未启动。

## 21. 提交

- v4.3 本地提交(不 push;git add 仅显式路径):
  `src/pathway_v43/pollutant/endpoint.py`、
  `src/pathway_v43/pollutant/native_result.py`、
  `src/pathway_v43/pollutant/runflow.py`、
  `src/pathway_v43/pollutant/profile.py`、
  `src/pathway_v43/pollutant/store.py`、
  `tests/test_ppv1_s4a_endpoint.py`、
  `tests/test_ppv1_profile.py`、
  `docs/POLLUTANT_PATHWAY_S4A_DELIVERY_2026-10-08.md`、
  `docs/mimo_ppv1_chem_review_request.md`、
  `docs/review_evidence/ppv1_s4_impl_2026-10-08/s4a_r1/`;
- 用户既有未跟踪 `.zcodeignore` 保持原样不纳入;production/
  search/queue 等未改不提交;父 worktree 已清理;G01 tmp
  (/private/tmp/ppv1_s4a_r1_g01)保留至复审(证据已快照,可随时
  删)。
