# pollutant_pathway_v1：S4 回修 r1 交付书（确认复核四组 P1 闭合，2026-10-08）

- 基线：待审 HEAD `8735601b75825388fe9f4a177a1131ef264054a1`（S4b 批次；确认复核
  `POLLUTANT_PATHWAY_S4_CODEX_CONFIRM_REVIEW_2026-10-08.md` 的裁定对象）；父
  `fc40605819201ae4a7101fc500b19083d78383b0`。本批为确认复核 §4 四组 P1 的
  **一次性回修实施**：只修 S4-C01/S4-C02/S4-C03/S4-C04 ＋ §5/§6 文案 P2 同步
  ＋ mimo 新请求；不实施 S5，不改冻结判据/legacy/G2/AtomTool/export_v3，不改
  金标/题面/封存逐题 run，不调用外部模型或真实 provider，判分零 LLM，不 push。
- 证据根：`docs/review_evidence/ppv1_s4_impl_2026-10-08/s4_rework_r1/`
  （README + manifest.json + SHA256SUMS，300 附件；全部执行在仓外新
  /private/tmp，本永久目录未运行任何写库程序）。
- 提交：v4.3 本地提交（显式路径 git add；哈希见 §11；不 push）。

## 0. 结论一句话

四组 P1 全部按确认复核 §4 最低收口闭合：C01 必要条件 unknown/conflict 经同源
`PathContext.route_assessment()` 接入 endpoint 阻断与输入摘要（证据全文保留、
已知兼容/无必要条件正控保持 supported、不全拒）；C02 manifest core 自身 digest
复算 + run/版本/策略内容绑定 + 必要 artifact 引用集合由独立权威同源枚举整集
闭合（与每行 hash 分别核、合法缺席保留）；C03 soutc 键按 action_id 独立枚举
不被空 task_key 挡住（child retrieve 结论全文入原生输出与 manifest、坏必要
soutc build/read 双拒）；C04 投影构建与首消费验证真实原生来源（假 native +
真 export 引用、projection-only 自洽改内容 + 真 reference 均拒）。隔离源
PPV1 全量 **951 passed/0 skipped/0 failed exit 0**（932 存量 + 19 新；存量
零行为改动，仅披露的版本字面量）；隔离全量非 slow（G01 同口径）**1553/8/17
exit 0**；G01 安全隔离（295 输入新控制器）**1553/8/17 exit 0**；父 8735601
同字节对照新文件 19 红全为缺拒绝/缺字段/缺签名类行为红（0 collection 红）；
legacy 52 文件聚合与两树四产物导出字节与父逐一致；确认复核各反例复制到新
tmp 复跑全部翻转为拒（修前 2F/3P oracle 对修后重捕获数据 5/5、对修前数据
保持 2F/3P 不改期待；两支旧观察脚本逐字复跑按修后预期失败登记）。

## 1. 四组 P1：入口矩阵与源码位置（file:line）、前后行为

适用入口矩阵（每项：消费的权威/必要集合/版本与身份/内容与证明范围/合法与
诚实控制）：

| 入口 | 消费的权威 | 必要集合 | 版本/身份绑定 | 内容/证明范围 | 合法/诚实控制 |
| --- | --- | --- | --- | --- | --- |
| start/resume → derive_run_endpoint | search_actions.context_ref 枚举的 PathContext artifact（H07+内容身份首消费）+ endpoint_evidence（冻结计划）+ events/stop 行 | 全部上下文 × route_assessment 的 essential_claimed 行 | endpoint-2/policy-2；derived_from.route_conditions_digest | 评估仍只由来源层直报证据决定；必要条件只作阻断输入 | 已知兼容/无必要条件保持可支持；证据全文保留 |
| read_run_endpoint / consume（首读/首消费） | endpoint/stop 行 + 同源重算（含 route_conditions_digest） | 同 derive | schema 版本门 + payload_hash + 跨表引用 | staleness 对照同源 | 上下文损坏 ⇒ endpoint_context_consumption_failed |
| build_native_result | store 行 + artifact_reference_index（单一来源） | 索引内全部必要 artifact（soutc 键独立于 task_key） | native-result-2 | 只消费已验证 endpoint 记录 | 合法缺席跳过；坏必要 artifact 结构化拒 |
| export_native_result（export） | 同 index + 冻结计划 + 原生结果 artifact | 同上 | native-export-2/policy-2 | 不产生新化学判定 | 写入侧撞损坏 artifact 先拒 |
| read_native_export（consume） | manifest 文件本体 + DB 行 + artifact store + profile 常量 | manifest core 复算 + run/契约版本/策略绑定 + 必要集合闭合 | 同上 + contract_versions 整组 | 八 kind 拒绝面保持 | 先拒、零业务写、原文件保全 |
| build_v3_projection（project） | read_native_export 首消费（同一绑定源） | 传入 native_result = 已验证导出 payload | v3-projection-2 | 有损投影不产生终点/矿化 | 假 native 拒；真链不受影响 |
| read_v3_projection（read） | 原生 manifest+payload 文件（可选 ledger 走完整原生首消费） | reference 内部一致 + adapter 同源复算 | 同上 | 12 轴/空答卷/逐事件步骤保持 | projection-only 改内容拒；旧投影随原生文件保全仍可读 |

### S4-C01（endpoint.py）

- 源码：`src/pathway_v43/pollutant/endpoint.py:354`（`_route_condition_assessments`
  ：上下文去重枚举 → load_context 首消费 → `route_assessment()` 同源消费，
  必要行全文保留）；`:422`（`_necessary_condition_keys` 键聚合）；`:556`
  （`_assess_endpoint` 新增 route_conditions 入参与
  necessary_conditions_unknown/conflict 阻断，`:620`）；`:728`
  （`_endpoint_current_input_digests` 增 route_conditions_digest 同源重算）；
  `:823`（`derive_run_endpoint`：`:898` record.route_condition_assessment 全文
  字段、`:923` derived_from 摘要）；`:939`（summary 增必要条件键）；模块头
  入口矩阵与 F02 段同步更新。
- 前行为（8735601）：评估只消费 inherited dependencies（`:298` 旧位）；条件
  快照只采事实计数、不参与评估；必要条件 unknown/conflict 不阻断 ⇒ 充分矿化
  声明 + 缺失/显式 unknown 的 essential oxygen_regime 仍 supported_mineralization
  （确认复核两反例，event=1）。
- 后行为：上述输入 ⇒ unknown，blocked_reasons=necessary_conditions_unknown/
  conflict，逐条评估行与 coverage 全文入记录；start/resume/严格首消费/native
  导出载荷/v3 摘要同值；首消费 staleness 重算消费同一必要条件集合及其内容
  摘要（route_conditions_digest）；上下文损坏 ⇒ 首消费拒。
- 旧边：`route_assessment` 本身按 phase_history 快照消费旧边记录值（不重评）
  —— 本批直接复用该同源函数，未另造第二套评估。

### S4-C02（native_export.py）

- 源码：`src/pathway_v43/pollutant/native_export.py:485`（manifest core 自身
  digest 复算，check=manifest_core_digest）；`:521`（contract_versions 整组
  绑定，export_version_unknown）；`:537`（run 绑定，export_reference_
  mismatch/run_binding）；`:646`/`:657`（策略正文与自记 hash 双绑定，
  export_policy_stale）；`:167`（`_necessary_artifact_reference_keys` 独立权威
  同源枚举，与 `_artifact_references`/index 同一来源）；`:690`（集合闭合，
  omitted/dangling 分列，check=necessary_artifact_reference_set_closure）；
  `:153`（`_current_contract_versions` 与导出侧共用单一版本源）；`120`
  policy v2 描述；`:374` export 侧 `_artifact_references` 撞损坏 artifact
  结构化拒。
- 前行为：只比对 manifest.export_digest 字面值；重算的是 payload 而非 manifest
  core；遍历 manifest 自报引用集合；策略只比 hash 字段 ⇒ 四例 manifest-only
  改坏全被接受；自洽重封漏单 production_report 被接受；坏/缺 H07 部分被
  （逐行）拒、自洽重封路径绕过。
- 后行为：反例 A 四例（run_id/契约版本/策略正文/引用）⇒ export_manifest_
  corrupt（core 复算）；反例 B 自洽新 digest 漏单项/全部必要引用 ⇒ 集合闭合
  拒（omitted 清单）；自洽换 run_id/版本/策略 ⇒ 绑定拒；坏/缺 H07 ⇒ 逐行或
  枚举结构化拒；还原后正控全部读回。集合闭合置于 stale 检查之后（事实漂移
  先以 export_stale 浮出——次序披露，八 kind 及既有测试全部保持）。

### S4-C03（native_result.py）

- 源码：`src/pathway_v43/pollutant/native_result.py:92`
  （`artifact_reference_index`：`:147` soutc 键按 action_id 独立枚举——空
  task_key 不再挡；task_key 键引用仅在键合法时列举，缺键不产空键引用）；
  `:276`（build 的 `_envelope` 撞损坏 artifact ⇒ NativeResultContractError
  kind=native_result_artifact_corrupt，不静默略过）。
- 前行为：`:123-125`（旧位）空 task_key 提前 continue ⇒ child retrieve 的
  no_local_candidate/unresolved_continuation=True soutc 在 build 聚合与
  manifest 引用全部漏掉；损坏该漏聚 artifact 时 build/read 仍接受。
- 后行为：双备选+共同产物夹具 4 个 soutc 全聚合（原 2）、manifest 引用含
  child soutc、坏必要 soutc ⇒ build 与 read_native_export 双拒、还原正控；
  build 与 manifest 与 C02 集合闭合共用同一索引（不各修一套规则）。

### S4-C04（v3_projection.py）

- 源码：`src/pathway_v43/pollutant/v3_projection.py:273`
  （`_verify_native_source_binding`：构建侧先 read_native_export 完整首消费
  ＋ 传入对象=导出 payload 整比对 ＋ content digest/run/payload sha 绑定）；
  `:346`（`_derived_projection_content` 登记 adapter 单一来源派生内容，构建
  与读取共用）；`:371`（build 接入绑定）；`:578`（read：`:624` 可选 ledger
  先走原生首消费；`:653` 已表达字段同源复算比对 check=adapter_derived_
  content）；`:659`（`_load_bound_native_export` 文件级绑定：manifest core/
  payload sha/content digest/reference 内部一致/graph aggregate/run_id，
  check=native_reference_internal_consistency）；`:438`
  （`_unprojectable_summaries` 增必要条件键）；`runflow.py:1380`（读回传
  ledger 联动原生首消费）。
- 前行为：构建直接信调用方对象；读取只核投影自 hash/版本/lossy 标记/原生
  manifest 文件存在 ⇒ 假 native（删 events/deferred 自洽重算 digest）+ 真
  export 引用全链接受（steps=0）；projection-only 自洽改内容 + 真 reference
  接受。
- 后行为：两反例均拒（v3_projection_source_binding_mismatch：export_
  content_digest_binding / adapter_derived_content）；真实投影无/有 ledger
  均可读；原生导出与 DB 不变；旧投影随其原生文件保全仍可读（历史语义保持）。

### 版本/身份登记（profile.py）

`profile.py:204`（profile 16→17）、`:227`（endpoint-1→2）、`:230`
（endpoint-policy-1→2）、`:235`（native-result-1→2）、`:240`
（native-export-1→2）、`:243`（native-export-policy-1→2）、`:249`
（v3-projection-1→2）；store 保持 -10（无新表）、runflow 保持 -5（接线
不变）。旧 run 按版本门拒（不跨版本续跑）。改动的 runflow/store/profile
行号漂移沿既有披露（判据冻结稿 §8 重锚待下一判据版本）。

## 2. 正负控制清单（新增 19 用例 tests/test_ppv1_s4_rework_r1.py）

- C01 负控：必要条件事实缺失 / 显式 unknown（双参数化，确认复核两反例原样）
  ⇒ unknown（start/resume/记录/阻断原因/摘要/严格首消费/导出/v3 八处断言）；
  anaerobic 冲突 ⇒ conflict 阻断；上下文 artifact 损坏 ⇒ 首消费拒（还原正控）。
- C01 正控：已知 aerobic 满足必要条件 ⇒ supported；无必要条件（legal
  supported source 对照）⇒ supported；NAD 依赖负/正控沿既有 f02 测试保持。
- C02 负控：manifest-only 四例 mutation（run_id/契约 profile 版本/策略正文/
  引用删除，保持原 digest）⇒ core 复算拒；自洽重封漏单项 production_report
  引用 ⇒ 集合闭合拒（omitted 断言）＋全删 soutc 复合案；自洽换 run_id ⇒
  run 绑定拒；自洽换契约版本 ⇒ 版本门拒；自洽改策略正文保持自记 hash ⇒
  策略绑定拒；manifest 记录的必要 artifact 被删 ⇒ 逐行拒。
- C02 正控：每例还原后原导出读回。
- C03 负控：坏 child soutc（H07 篡改）⇒ build 拒＋导出读取拒（还原正控）。
- C03 正控：child soutc 全文（no_local_candidate＋unresolved_continuation=
  True）入原生对象与 manifest 引用；索引无空 task_key 引用。
- C04 负控：假 native（删 events/deferred 自洽重算 digest）+ 真 export 引用
  ⇒ 构建拒（零新投影目录）；projection-only 自洽改 steps/deferred 计数换
  新目录 + 真 reference ⇒ 读取拒（fields 断言）；混搭 reference content_
  digest/task_key ⇒ 引用内部一致拒；原生导出文件缺失（带 ledger）⇒ 投影
  读取先拒（还原正控）。
- C04 正控：真实投影无/有 ledger 均可读、步骤保真；完整公共链一致性
  （记录/native/v3 三处同值）＋ resume 幂等（业务账零新增、model_requests
  0）。
- 既有 S4a/S4b 控制全部保持：35＋18 用例零改动（除披露的版本字面量）全绿；
  确认复核边界控制 5/5 复跑通过；确认复核 oracle 对修前捕获数据保持
  2F/3P（期待未改）。

## 3. 实际数字（全部隔离源/新 tmp 正式执行；含缺席依赖）

| 执行 | 命令口径 | 结果 |
| --- | --- | --- |
| 当前 PPV1 全量 | 隔离源（src 含 vendor/普通 dependingv3 同级副本，父/子同 V3_CODE_ROOT），`-k ppv1` | **951 passed / 0 skipped / 0 failed，exit 0**（932 存量 + 19 新，34 文件；仓内树同数 951） |
| 当前 S4 焦点 | 同上，三份 S4 测试文件 | **72 passed，exit 0** |
| 隔离全量非 slow（G01 同口径 deselect） | 同上，`-m "not slow" --deselect <export charge-fixture>` | **1553 passed / 8 skipped / 17 deselected，exit 0** |
| 仓内全量非 slow（不 deselect） | 仓工作树 | 1562 passed / 16 deselected（charge-fixture 用例仓内通过；隔离树缺其评测侧夹具，属 G01 明确排除项） |
| G01 安全隔离 | 新控制器 safe_g01_s4_rework_r1.py，295 输入 | **1553 passed / 8 skipped / 17 deselected，exit 0**；8 skip 逐 nodeid：5 真实冻结评价（batch_runner:52、score_report:110/163/172/184）＋1 缺 v4 对照（analog_assets:95）＋2 phase_d 派生（analog_v2_corpus:62/153）；17 = 16 slow＋1 明确排除；295 项输入 SHA 前后一致；网络 0 |
| 直接父 8735601 | detached 稀疏 worktree（src+tests），同字节 4 份测试文件 | 新文件 19 红（11 缺拒绝行为红＋5 断言红＋2 签名红（read_v3_projection 无 ledger 参数）＋1 字段红（summary 无必要条件键）；**0 collection 红**，四模块在父上存在，属行为红）；更新文件 4 版本字面量红（profile-17/endpoint-2/policy-2/native-export-2/v3-projection-2/fook policy-3 字面量）＋72 合法正控绿 |
| legacy 字节专项 | s4b_r1 探针，当前树 vs 父 worktree | legA/legB 的 predictions.jsonl＋export_metadata.json **4/4 逐字节一致**；52 文件 code_identity 聚合 `18007e6a…` 与父一致 |
| 确认复核 oracle 复跑 | 7 案新库只读重捕获 | **5 passed**（修前同 oracle 对修前捕获数据 2F/3P，缺口钉住） |
| 确认复核各案复跑 | 评审脚本复制到新 tmp（逐字＋忠实微调） | 全部反例翻转为拒；两支逐字脚本 exit 1 于缺口闭合点（预期失败登记）；public_resume 正控全过、网络 0 |

准备错误如实保留（metadata/preparation_incidents.json）：隔离全量第一次
（无同级 dependingv3）18 failed＝S3b 硬杀子进程身份环境不一致（与确认复核
准备事故同类，不采信为产品回退；唯一环境修正重试 951/0）；隔离非 slow 第一次
（缺 v3 assets）8 failed→修正后 1553/8/17；G01 控制器一次编辑笔误后重跑。
父/子同指一个隔离普通 dependingv3 根（含普通 assets，无 evaluation）；无
V3_CODE_ROOT 精简丢根问题。

历史基线 932/1534/8/17/294（确认复核）只作对照；实际数以上表为准。基线
本轮父分类 0 collection 红与 S4a/S4b 批的 collection 红不同——本批新文件
在父 8735601 上模块齐备可收集，红全部为行为/字段/签名/字面量类，如实分开
登记（不因新模块让既有用例停收集：951 存量全绿证明）。

## 4. 与确认复核 §4/§7 的逐条映射

| 复核要求 | 本批落点 |
| --- | --- |
| C01 同源条件评估接入阻断＋输入摘要；旧边历史快照；已知兼容正控；NAD 控 | §1 C01（route_assessment 同源复用＋route_conditions_digest 入 derived_from/首消费重算）；正控见 §2 |
| C01 覆盖 derive/首读/consume/start/resume/native 导出/v3 摘要 | 记录字段＋summary 字段＋导出载荷＋v3 unprojectable_summaries.necessary_condition_*_keys＋测试八处断言 |
| C02 manifest core digest＋run/版本/策略内容绑定；必要集合独立权威闭合、分别核；普通 manifest-only/自洽漏单/坏缺 H07 先拒 | §1 C02（core 复算/整组绑定/正文 hash 绑定/集合闭合+每行校验；先拒零写保全） |
| C02 八 kind/正常导出/幂等/合法空池保持 | 既有 18 用例零改动全绿；空池用例保持 |
| C03 空键不挡 soutc(action_id) 枚举；统一 build/manifest 索引；全文入原生输出；坏必要 soutc 不跳过；合法缺席/去重/非空两键保持 | §1 C03（单一索引共用；task_key 键仅在合法时列举） |
| C04 构建与首消费验证真实原生来源/reference 内部一致/adapter 派生内容复算；已验证存在/自 hash 非证书；消费 API 可明示 ledger | §1 C04（构建先消费＋整对象比对；读取文件级绑定＋同源复算＋可选 ledger） |
| C04 保留有损 12 轴、正常/空池答卷、反向禁止/零 DB 写 | 既有用例零改动全绿；反向消费负控保持 |
| 保留 S3/已关项、首消费/ledger/AuditContractError、正常链、未知/partial/deferred/失败、幂等、子进程确定性、八 kind、已登记 P2 | 951 存量零行为改动；G02 子进程重导出用例保持；production.py 零触碰 |
| 旧观察脚本钉缺口、按修后预期失败登记；不改永久反例期待造绿 | 逐字复跑 exit 1 登记；修前数据 oracle 2F/3P 保持；忠实微调版（差异点注明）记录全部翻转为拒 |
| 新增回归在父 8735601 detached 稀疏 worktree 同字节运行 | §3 父基线行 |
| 全量/G01 复跑；基线数字只作历史比较、缺席依赖逐 nodeid 如实报 | §3（G01 disclosure 逐 nodeid） |
| 父/子同一隔离普通/空根 | §3 准备错误与修正 |
| 交付书四组映射＋§5/§6 文案 P2 同步＋自包含 mimo 新请求（无金标；r16/r17 不回写；执行声明留待复审） | 本文 §5＋mimo v18（0h 节七条；旧回应原样保留；送审快照入证据 mimo/） |
| 证据根含 README/HEAD/父/schema/version/输入/argv/env/exit/stdout/stderr/JUnit/准备失败原日志/SHA256 manifest；不以控制器 JSON 替代 pytest 输出 | s4_rework_r1/（g01/g01_safe.stdout.txt 为实际 pytest 输出；junit 全存） |
| v4.3 本地提交显式路径、不 push；四组闭合后依同一范围收口、不启动 S5、不承诺科学性能、不自动改判据冻结状态 | §11＋§6/§7 |

## 5. 确认复核 §5/§6 文案 P2 同步（本轮按回修提示词落实）

- "879/914/932 存量零改动"口径明确为**除披露的 profile/契约版本字面量**外零
  改动（本批更新 3 份既有测试文件的 6 处版本字面量，逐处披露于 §1/§9）。
- 拒绝优先级区分：endpoint 首消费先行（read_native_export 步骤 6 之前，
  输入漂移先以 endpoint_record_stale 浮出）；导出八 kind 全保持，新增拒绝
  复用既有 kind（manifest 核心复算→export_manifest_corrupt；集合闭合/坏
  artifact→export_reference_mismatch；绑定→export_version_unknown/
  policy_stale）；集合闭合置于 export_stale 之后（次序披露）；v3 新增
  v3_projection_source_binding_mismatch 一个 kind（模块头登记）。
- 24 字符 digest 目录命名（native_export/v3_projection 目录取
  digest[:24]，完整值保留在 manifest/载荷）沿既有披露。
- 多 reactant collapse 分支仍未由公共生产夹具动态覆盖（本批未改 v3 逐事件
  步骤语义；读码披露不冒称执行）。
- stop 视图会话成分与独立权威分写沿 S4a/S4b 披露（本批 E2E 用例断言事件/
  预算零新增为硬边界；resume 后当前导出/投影为消费对象）。
- H07（artifact 信封）与上下文内容身份（context_id 重算）分层保持：C01
  上下文损坏测试同时覆盖两层（信封 payload_hash 失配触发首消费拒）。
- 确认复核 §6.1 备用报告归档质量项（JUnit/stdout 缺席等）在本轮证据包
  已补齐（g01 实际 pytest stdout/stderr/JUnit 全存；各复跑命令/exit/env
  记录）。
- S4a 实际父 0e345e8 与源码基线 adf0287、mimo r16 行号按其 S4a HEAD 解释
  等 r16/r17 采信精度项沿复核 §6.2 保留，不在本批回写旧回应。

## 6. 未完成项与残留 P2（诚实清单）

1. **S5 未启动**（评测器/数据规范/统计预注册/阈值/真实 provider/敏感资料
   边界全部 pending）；本批不承诺科学性能。
2. **已确认复核列出的既有 P2 保持**：来源层证据真实性/现实来源认证不在
   范围；同机 flock 非分布式；cache_hit 同构；外部 SQL 两事务窗口；
   foreign-run 反向诊断；stop 对象有界；已登记 RuntimeError 逃逸面；来源
   标签精度；24 字符目录名；多 reactant 分支未动态覆盖；行号锚漂移。
3. **本批新增残留（如实登记）**：
   - 集合闭合不抗全库协同改写（沿 S3B-01/S4a 边界：DB 行+artifact store
     同源重算，无密码学签名；自洽重封能被拒是因为枚举集合来自独立于
     manifest 的权威）；
   - C01 阻断粒度 = 路线上下文的 essential_claimed 行（含 phase_history
     快照行）；observed_reference（文献参考）级别行不阻断（沿判据四
     basis 语义）——若评审认为应更严，属判据侧另议，不在本批擅自加门；
   - v3 读取的文件级绑定核 manifest/payload 自洽与相互绑定，不重算 DB
     事实（无 ledger 调用方的新鲜度判定仍由 read_native_export 负责，
     与 0g 既有分工一致）；带 ledger 时先走完整原生首消费；
   - 确认复核补充观察"已知 anaerobic 冲突 event=0 仍 supported"在修后
     已翻转为 unknown（conflict 阻断），与最低收口锚（两条 event=1
     unknown 反例）一并闭合；
   - G01 运行树内出现的 `__pycache__` 为全套件既有非 PPV1 子进程用例写
     入的字节码（与本批无关；输入 SHA 只覆盖 .py 源；仓内工作树收尾已
     清理）；
   - 父基线 2 个签名红（read_v3_projection 的 ledger 参数）属"父上接口
     不存在"类，非行为差异，已逐条分类。
4. **mimo 送审状态**：v18 请求（0h 节七条）已落盘并入证据快照；**本批
   实施方未调用任何外部模型**；送审由主会话按 AGENTS.md 通道执行，回应
   原文落盘 docs/ 后按与程序证据互证采信；执行类声明待 Codex 复审。

## 7. 交付物绝对路径

- 本交付书：`/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S4_REWORK_DELIVERY_2026-10-08.md`
- mimo 新请求（v18）：`/Volumes/CC/Enzyme_Agent/dependingv43/docs/mimo_ppv1_chem_review_request.md`
  （送审快照：`…/s4_rework_r1/mimo/mimo_ppv1_chem_review_request_v18_sent.md`）
- 证据根：`/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/ppv1_s4_impl_2026-10-08/s4_rework_r1/`
  （current/ baseline/ confirm_rerun/ g01/ legacy/ metadata/ mimo/
  README.md manifest.json SHA256SUMS；运行工作区与父 worktree 留
  /private/tmp/s4r1_* 供复审，SQLite 二进制不封包）
- 源码/测试改动：`src/pathway_v43/pollutant/{endpoint,native_result,
  native_export,v3_projection,profile,runflow}.py`、
  `tests/test_ppv1_s4_rework_r1.py`（新）、
  `tests/test_ppv1_{profile,s4a_endpoint,s4b_export}.py`（版本字面量）。

## 8. scripted 输入与消费摘要（合成规则级；网络 0）

夹具与确认复核/既有 S4 测试同源（spec/mineralization_evidence/
oxygen_req）；公共链断言面：endpoint 四分账＋必要条件键、
endpoint_record_payload_hash、native_result.content_digest、
export_digest、projection_digest、DB 行/表、幂等计数、model_requests=0。
无真实模型调用、无金标/题面/封存资料；判分零 LLM。

## 9. 实际源码 diff 构成（git diff 8735601 --stat）

endpoint.py（+152 行段）、native_export.py（+235）、v3_projection.py
（+309）、native_result.py（+73）、profile.py（+58）、runflow.py（1 行：
投影读回传 ledger）；tests：test_ppv1_s4_rework_r1.py（新，19 用例）、
test_ppv1_profile.py（1 字面量 profile-17）、test_ppv1_s4a_endpoint.py
（2 字面量 endpoint-2/policy-2）、test_ppv1_s4b_export.py（6 处字面量：
native-export-2/policy-2/profile-17/v3-projection-2×2/未来策略 -3）。
零触碰：output/export_v3.py、services/atom_tool.py、workflow/runner.py、
production.py、chemstate.py、path_context.py、hypothesis.py、events.py、
audit.py、search.py、queue.py、model_protocol.py、store 既有表。

## 10. 基线红绿分类 JSON

`…/s4_rework_r1/baseline/parent_r1_classification.json`（新文件 19 用例逐
条分类：11 behavior_failure_refusal_missing / 5 assertion_failure /
2 signature_missing_on_parent / 1 field_missing_on_parent；更新文件 4
版本字面量红＋72 合法绿；0 collection 红）。

## 11. 提交

v4.3 本地提交（不 push；git add 仅显式路径）：src/pathway_v43/pollutant/
endpoint.py、native_result.py、native_export.py、v3_projection.py、
profile.py、runflow.py、tests/test_ppv1_s4_rework_r1.py、
tests/test_ppv1_profile.py、tests/test_ppv1_s4a_endpoint.py、
tests/test_ppv1_s4b_export.py、docs/POLLUTANT_PATHWAY_S4_REWORK_
DELIVERY_2026-10-08.md、docs/mimo_ppv1_chem_review_request.md、
docs/review_evidence/ppv1_s4_impl_2026-10-08/s4_rework_r1/。
提交哈希：见 `git log -1`（提交信息含本交付书摘要；登记于主会话）。
用户既有未跟踪评审材料（.zcodeignore、确认复核报告、r16/r17 回应、
ppv1_s4_confirm_codex_2026-10-08/ 等旧证据目录）不纳入本批提交。

## 12. 完成声明（不冒称）

四组 P1 按确认复核 §4 最低收口闭合并有正负控与复跑证据；**不宣称完整 S4
通过**——依同一验收范围交主会话安排 mimo 送审（v18）与 Codex 复审收口；
不启动 S5、不承诺科学性能、不自动改变判据冻结状态。
