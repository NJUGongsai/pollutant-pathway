# ppv1-criteria-v2 appearance 首次消费第二轮正链终裁（2026-10-14）

**终判：不放行。仅余 1 项同合同 P1：第三项 state_id 绑定只核 appearance 与 SQL 行键，没有核对应语义块。** `dda852b` 已修复非对象漏验、内容哈希腐蚀及 appearance 自身错绑；这些修复保持关闭。新的公共合成正负控证明，损坏的语义身份仍能通过官方六步消费、正式导出，而同库公共重放拒 `state_inner_id_corrupt`。本轮不授予 v2 工程放行，不以仓内既有 effective 文档替代本次证据。

题域标签：298=RHEA 通用酶学/已见题。本文数字均为工程验收/合成探针，不是判分成绩，不外推化学机制或科学性能。

## 评审对象与固定范围

本报告由当前正链 Codex 会话汇总代码核查、独立隔离执行和提交范围证据；不沿用既有本地代审报告的判定，不声称恢复旧 CLI 链式 fork。已有 `POLLUTANT_PATHWAY_CRITERIA_V2_FINAL_DECISION_R2_2026-10-14.md` 保持只读，本轮另名新增。

| 项目 | 本次实际对象/范围 |
|---|---|
| 修复目标 | `dda852ba71cd41518d2cf390ee843c4db8508633` |
| 修复父/C 线 | `873c323116e065ca7596f7655bbf74f31c3881f3`；其父 `7e7855cb3ead11c7153f57b8e47a5b018f9e4ba3` |
| 本会话主要执行树 | `27300cfe7fc5998e2f57e8c838d6952ecfe315fd`；另以 git archive 的 **exact dda852b** 新树复现余项 |
| schema | chemstate=`ppv1-chemstate-8`；store=`ppv1-store-10`；native result=`ppv1-native-result-2`；evaluation=`ppv1-evaluation-5` |
| 固定验收 | 完整 appearance 集合的形状/内容哈希/state_id 三查；state_id 与行键及语义块一致；首次消费与公共重放身份闭合；合法正控及既有回归 |
| 不新增范围 | C 功能审查、机制证明、新阶段能力或真实题域成绩；原 CN 腐蚀 P1 与 P2 不重开 |

依据是 [上一轮有限验收](/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_CRITERIA_V2_FINAL_DECISION_2026-10-14.md:81)、[本次交付第三项绑定承诺](/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_CRITERIA_V2_P1FIX2_DELIVERY_2026-10-14.md:21) 和 [本轮任务书](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/criteria_v2_final_r2_2026-10-14/TASK_REVIEW.md)。这是第三项的实证缺口，不是新增阶段门。

## 已修复项与唯一余项

| 验收项 | 本次结论 | 本会话证据 |
|---|---|---|
| 完整出现集合不丢非 dict | **关闭**；`[]` 在 build 结构化拒 `payload_not_object` | [基线复现](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/criteria_v2_final_r2_2026-10-14/verification/parent_participant_appearance_output.json)、[当前探针](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/criteria_v2_final_r2_2026-10-14/verification/current_participant_appearance_output.json) |
| appearance 内容哈希，首用/收集/重放共源 | **关闭**；旧 hash 的 state_id 错绑拒 `appearance_hash_mismatch`，底层 `appearance_hash_corrupt` detail 保全 | 当前探针；[代码核查](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/criteria_v2_final_r2_2026-10-14/code_review/notes.md) |
| 重签后 appearance 载荷 ID 与行键错绑 | **关闭**；新增测试拒 `state_id_binding_mismatch` | [s4b 测试:986](/Volumes/CC/Enzyme_Agent/dependingv43/tests/test_ppv1_s4b_export.py:986)、[211 项输出](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/criteria_v2_final_r2_2026-10-14/verification/pytest_affected.stdout) |
| 上述旧负控拒绝后链截断 | **关闭**；仅 read_endpoint 成功，build 拒绝；persist/export/reader/evaluator **未执行**，不报通过 | 当前探针的 steps/first_rejection |
| 合法多出现及公共重放幂等 | **通过**；六步完整执行，三条出现保全导出，submit_event replay `created=false` | 当前探针；[s4b 正控:900](/Volumes/CC/Enzyme_Agent/dependingv43/tests/test_ppv1_s4b_export.py:900) |
| semantic 内 ID 与 SQL/appearance 绑定 | **唯一 P1 未关闭**；自洽的另一套 CN-only 语义被放入旧行，官方六步接纳/同库 replay 拒绝 | 下节双人隔离重现及 exact dda852b 复现 |
| 原 CN、零出现、P2 和、合法边界 | **保持关闭/通过本轮测试范围**；受影响 211 项 passed、0 skipped | 下节回归矩阵；不声称本轮重跑旧 CN 长探针 |
| 缺省 v1 字节保持 | **通过四组实跑对照**，9 命令 exit 0 | [四对照结果](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/criteria_v2_final_r2_2026-10-14/verification/v1_differential/comparison.json) |

哈希唯一判据在 [store.py:464](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/store.py:464)，调用方为 native 首次消费、既存出现收集、完整出现重放、事件 appearance manifest 重放。非对象分支把共享 helper 的哈希异常转换为 `appearance_hash_matches` 布尔，自身形状错误仍结构化定位；它没有原样附底层异常 detail。哈希 mismatch 分支才原样附 `appearance_error_detail`。纠正“每个 reason 都原样附底层 detail”的笼统表述，不把这项措辞差异升级为新 P1。

## P1 源码与公共链证据

[native_result.py:173](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/native_result.py:173) 只核 `app_payload.state_id == appearance 行键`；随后取 states 行键寻找出现，但没有核 `semantic.state_id == states 行键`。[:197 的拼接](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/native_result.py:197) 保留 semantic 内 ID，只覆盖 [五项 appearance 字段](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/store.py:382)，其中没有 state_id，再调用 from_dict。

[chemstate.py:648](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/chemstate.py:648) 校验对象自身；[CN-only 专用分支:795](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/chemstate.py:795) 核内部 ID 与 CN 自洽及诚实 unknown，无法知道外部 SQL/appearance 键。公共 replay 则在 [store.py:1297](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/store.py:1297) 明确拒 semantic 内 ID 与持久行键不同。因此局部对象自洽仍不足以证明该对象属于被消费的旧权威行。

[最终公开探针:93](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/criteria_v2_final_r2_2026-10-14/code_review/cn_only_binding_probe.py:93) 先以公共 CN-only 工厂、hypothesis/event 工厂和 submit_event 保存合法 CCO 产品，再于任何腐蚀前合法派生 endpoint。负控仅在 [:125](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/criteria_v2_final_r2_2026-10-14/code_review/cn_only_binding_probe.py:125) 用公共工厂生成自洽 CCN，然后替换原 states.payload 的 `(state_id, cn_identity)` 两字段；SQL 行键、非目标 state、完整 appearance（含 payload/hash/created_at）、所有其他表及非数据库文件均不动。[:119](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/criteria_v2_final_r2_2026-10-14/code_review/cn_only_binding_probe.py:119) 的完整性断言比较 17 个 SQLite 表和 14 个非数据库文件，只有 states 表变化，appearance 哈希仍真。最终脚本 SHA256=`13ebba0088001b9f896a8ecbda00bb0c65c5b225c8b84b70b346ca30933dd506`；旧观察版另存，未用新脚本行号冒充旧输出。

| 合成臂 | 官方六步消费（read→build→persist→export→reader→evaluator） | 同库公共 submit_event replay |
|---|---|---|
| 合法 CN-only CCO 正控 | 六步全部成功，完整导出 | accepted=true，created=false |
| 旧行键/appearance 不动，semantic 换为自洽 CCN 身份 | **六步全部成功**；导出仍为旧 SQL 行键、内 payload 却为新 CCN ID | **拒绝** `Ppv1LedgerCorrupt`，`kind=state_inner_id_corrupt` |

负控旧 SQL/appearance ID=`cs_f80ce0ec44c8f89444e6`，semantic 新 ID=`cs_465fed23ff90a5f67f3c`。实际 evaluator 为 `interface_verified_only`，边为 `matched_participant_coverage_partial`；本报告不声称 wrong strict、错误分数/豁免或 R6。P1 的证据是损坏权威身份被官方重新封装并完整消费，而同库公共 replay 已判为损坏。

| 执行来源 | 实际源树/结果 | 原始证据 |
|---|---|---|
| 代码审查代理最终完整性版 | 当前 27300cf 的新 tmp；合法六步/幂等与负控六步/replay拒绝均断言通过，exit 0 | [命令](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/criteria_v2_final_r2_2026-10-14/code_review/cn_only_binding.command.json)、[最终输出](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/criteria_v2_final_r2_2026-10-14/code_review/cn_only_binding_output.json) |
| 验证代理第二个独立新 tmp | 同一最终脚本 hash；only states 变化、非目标表/文件不动等完整性断言通过，exit 0 | [第二执行命令](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/criteria_v2_final_r2_2026-10-14/verification/cn_only_integrity_crosscheck/command.json)、[summary](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/criteria_v2_final_r2_2026-10-14/verification/cn_only_integrity_crosscheck/summary.json)、[原始输出](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/criteria_v2_final_r2_2026-10-14/verification/cn_only_integrity_crosscheck/cn_only_binding_output.json) |
| exact 修复目标树 | git archive dda852b 新 tmp，vendor 与必要 metadata；同样复现，exit 0。证明缺口属于目标修复自身 | [目标树命令](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/criteria_v2_final_r2_2026-10-14/code_review/target_cn_only_binding.command.json)、[目标输出](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/criteria_v2_final_r2_2026-10-14/code_review/target_cn_only_binding_output.json)、[源码 manifest](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/criteria_v2_final_r2_2026-10-14/code_review/target_source_manifest.json) |

以上 exit 0 代表探针完整复现并验证正控/证据完整性，**不是负控产品验收通过**。独立执行指分别实跑，不为内部代理或评审模型的独立性背书。

## 既有回归和 v1 字节核对

| 本会话实际执行 | 已覆盖内容 | 结果/出处 |
|---|---|---|
| 11 文件受影响子集 | s4b:776 原 CN 腐蚀/合法 digest；:840 零 appearance；:927/:955/:986 三 reason；:900 多出现/幂等；criteria_v2:694/:722 两 tier/失败与批级和；完整 criteria 与 s5a 结构/CN-only、水/H+/PPi/混合 partial 边界 | **211 passed，0 skipped**；[命令和隔离来源](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/criteria_v2_final_r2_2026-10-14/verification/selected_summary.json)、[stdout](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/criteria_v2_final_r2_2026-10-14/verification/pytest_affected.stdout) |
| R7/R8 存储重放子集 | 共源哈希、存储及重放既有测试 | **21 passed**；[stdout](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/criteria_v2_final_r2_2026-10-14/verification/pytest_store_replay.stdout) |
| 双树四对照 | 7e7855c 基线与当前 27300cf；共享一次合成 run/同库，不用独立生成时间戳制造假差异 | 9 个命令全部 exit 0；如下四组 stdout 字节全等 |

21 项与全量可能重叠，不把子集计数累加成不重叠总数。原 CN 长探针本轮没有独立重跑；上表如实登记具体测试覆盖，不冒称旧探针亲跑。

| v1 对照 | 两树相同 stdout SHA256 |
|---|---|
| 同库 build 载荷 | `9e32c7de0dd7bd614584086e72e4058386cde1a6bb1638e090c8beefa01ae6c8` |
| 公共缺省 v1 evaluate/score | `50b6bf0a5f3a3220560623ef67e3aa0d6bb3b3539a3a83b947fb8811bc549ec2` |
| direct17 | `95814eb28e9dbae0349e2043207a6a773dad192bffb3df3ab8c03b6587909bc9` |
| true-default | `2b1d95343dafd8ea392fef1b076f0c76081ed84b9c23f16f72930d56a97aad1b` |

[四对照比较](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/criteria_v2_final_r2_2026-10-14/verification/v1_differential/comparison.json) 和 [全部命令](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/criteria_v2_final_r2_2026-10-14/verification/v1_differential/commands.json) 包含实际 HEAD、输入脚本 hash 和返回码；true-default 在双树都真正省略参数，并对照显式 v1。

## 安全全量实测及限度

| 执行 | 本会话实际结果 | 解释 |
|---|---|---|
| 当前 HEAD 全量 `-m 'not slow'` | **2101 passed / 18 failed / 16 skipped / 16 deselected**，exit 1 | 18 项均为隔离 start/resume 选用不同 v3 根而触发 `IdentityMismatch(v3_engine_code)`；原输出保留 |
| 仅上述 18 项，统一隔离 v3 根复验一次 | **18 passed**，exit 0 | 只改隔离环境，src/tests 未改；不是第二次全量，不拼成全量 0 failed |
| 交付方历史口径 | P1fix2 2125 passed / 0 failed / 16 deselected；叠加 C 后 2135 passed / 0 failed / 16 deselected | **交付转述**，不冒充本会话全量独立结果 |

原 full 的 selected=2101+18+16=2135；再加 16 deselected，collected=2151。与交付 2135 passed+16 deselected 的总数一致，差异来自本次 18 环境失败与 16 skip。16 skip 原文是 11 项缺少 v3/v4 同级代码根、5 项 v3 冻结基准不可用；不能笼统说全部因金标。没有复制/读取真实题面、reference_graphs、gold_routes 或封存 run 来补这些资源。

原始 [full 命令/白名单/隔离 provenance](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/criteria_v2_final_r2_2026-10-14/verification/full_safe.command.json)、[full stdout](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/criteria_v2_final_r2_2026-10-14/verification/pytest_full_safe.stdout)、[18 项环境复验命令](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/criteria_v2_final_r2_2026-10-14/verification/full_environment_recheck.command.json)、[复验 stdout](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/criteria_v2_final_r2_2026-10-14/verification/pytest_full_environment_recheck.stdout) 均落盘。本轮没有获得单次全量全绿；环境错误和安全 skip 不升级为判据 P1，终判仅依据前述具体权威身份公共链反证。

执行主进程设置 `-B`、`PYTHONDONTWRITEBYTECODE=1` 及 `-p no:cacheprovider`。全量后隔离 tmp 实有 **7 个 pyc**，不能宣称隔离源码目录零写入；[test_rate_gate.py:424](/Volumes/CC/Enzyme_Agent/dependingv43/tests/test_rate_gate.py:424) 和 :503 的测试子进程不带 -B，并仅以 OMP/PATH 重建环境，丢失 PYTHONDONTWRITEBYTECODE。只做 stat 的 [bytecode 审计](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/criteria_v2_final_r2_2026-10-14/verification/bytecode_stat_audit.json) 记录这些隔离产物，未读其内容；本仓 src/tests 自本轮 TASK 标记以来新/改 pyc 与新 pytest-cache 项为空。这个时间窗口检查不等于此前仓库全部缓存的完整哈希证明。本轮正负探针的字节码/pytest-cache 检查通过；此方法学限制不冒充产品错误，也不改变 exact 目标树及第二新 tmp 的身份反证。

## C 线文件污染与终态

[提交矩阵](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/criteria_v2_final_r2_2026-10-14/scope/notes.md) 确认 dda852b 的 4 文件与 873c323 的 10 文件交集 **为空**，包括源码、测试及 docs。C 是目标修复直接父；当前后续还包含 s5b_builder 的 `direction_limitation_note` 输出字段、6 个 scripts/hpc 和 3 份 docs，**不是仅文档**。目标 native_result/store/测试/交付书无后续变更，evaluation/chemstate 与全部 tests 也无后续变更。零提交文件交集不等于运行绝无共同依赖；本报告不审 C、不替 C 放行。

截至最后取样时间 `2026-10-14T20:14:22.092348+08:00`，观测 HEAD=`27300cfe7fc5998e2f57e8c838d6952ecfe315fd`。本次主要执行身份仍为 27300cf，余项归因另由 exact dda852b 新树承接，不因后续仓内状态自动扩大重测。起始 tracked 工作树/index 无改动；本次固定取样观察出现本审阅代理未修改的并行活树改动 `src/pathway_v43/pollutant/s5b_cli.py`、`s5b_orchestrator.py`、`s5b_worker.py`，index 仍为空。所有本会话执行使用既已隔离的 27300cf/exact dda852b 源树，没有消费该后到活树改动，**本轮未验证终态外部未提交的这三处改动**，不自动扩大重测。原有未跟踪材料保留，完整 [最终 git status 与 diff](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/criteria_v2_final_r2_2026-10-14/scope/final_workspace_status.json) 在证据中。没有 commit/push；没有修改源码、测试、既有 docs 或 AGENTS.md；没有外部模型调用。

## 有限回修与放行验收

仅补第三项绑定：复用/抽取公共重放已有的权威 state 内 ID=SQL 行键验证源，让首次消费核 semantic、SQL 与 appearance 身份一致；不能只靠 from_dict 局部自洽，也不能重算新 ID 洗损坏。新负控应在 build 结构化拒绝、保全底层身份 detail，persist/export/reader/evaluator 未执行。

保留合法 CN-only 六步/重放幂等、合法多出现完整导出、已修三 reason、原 CN/零出现、P2 和、v1 字节对照。不要全面拒 CN-only，也不要增加机制库、结构推测、化学新判据或真实题域性能门。补齐同合同这一 P1 后按固定矩阵重新收口，不追加新阶段门。

本轮证据最终 SHA256 目录清单与本报告 hash 见 [FINAL_MANIFEST.json](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/criteria_v2_final_r2_2026-10-14/FINAL_MANIFEST.json)；manifest 排除其自身，避免循环哈希。此前观察版与正式执行版分别保全。
