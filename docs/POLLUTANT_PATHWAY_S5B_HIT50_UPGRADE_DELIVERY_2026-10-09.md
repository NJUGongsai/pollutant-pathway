# PPV1 S5b HIT50 提升实施交付书（W0–W7）

状态：**`implementation_ready_for_review`**（科学目标待真实复测判定；
工程绿 ≠ 科学达标）。本轮实施零真实模型调用、零花费、未读金标/题卷/
旧答卷/封存逐题 run、未 push、未改冻结判据/旧预注册/封存批。

- 实施基线 HEAD（开工）：`0d86c48a26822cccfadd7818fec08279d6d55089`
  （末提交 = 交接文档；与任务书 §1 登记一致）。
- 本轮提交：见交付末尾 commit 记录（单 commit，不 push）。
- 工作树开工状态：src/tests 干净；52 个评审侧未跟踪文件保持不动
  （未读其内容、未提交）。
- 任务书：`docs/TASK_V43_PPV1_S5B_HIT50_UPGRADE_AND_RETEST_2026-10-09.md`
  （唯一权威；本交付按其 W0–W7 原文口径）。

## 一、W0–W7 状态矩阵

| 包 | 状态 | 一句话证据 |
|---|---|---|
| W0 数字勘误+漏斗闭合 | **done** | `docs/S5B_W0_NUMERIC_ERRATA_2026-10-09.md`（零金标冲突登记表）+ `s5b_scoring` 聚合诊断 U/H5/L 与单调性/双表闭合断言（tests/test_ppv1_s5b_hit50_w23456.py::test_w0_aggregate_diagnosis_monotonicity_closure 合成批端到端跑通） |
| W1 共同 compiler 闭合 | **done** | 新模块 `s5b_compiler.py`（s5b-compiler-1；map 号联结/同一迁移结果/D 命名空间/from_order 上下文/芳香语义/锚定单键/先 single 后变阶/charge·stereo unsupported/整环去芳香/等价对齐合并）；十二组正负控走公共链全部通过（tests/test_ppv1_s5b_hit50_w1.py，19 tests）；production 重复 state_ref 去重调度（W1 #9）落地 |
| W2 recorded 精确源 | **done** | 新模块 `recorded_source.py`（s5b-recorded-source-1；strict/CN 分层、库回读完整净产物、推断映射有界枚举、产物多重集核对、库 sha 校验、负控族 7 类）+ tests/test_ppv1_s5b_hit50_w23456.py W2 节 |
| W3 选择排序贯穿事件 | **done** | `runflow._run_decide` 统一 logical→prepared→净反应签名→effective_rank（s5b-rank-policy-1；显式模型 rank 全先于 fallback、novel 不因来源排后、novel 模型位次补回、同净反应去重合并 provenance）；`store` events 首提 INSERT 忠实采用 `PathwayEvent.created_at`（微秒级 `now_iso_hires`；重放不刷新）；时间正负控穿 store→native_export（W3 测试） |
| W4 编译后补位与有界检索 | **done** | `s5b_builder.default_pool_provider` 重写（s5b-pool-policy-1：raw24/pool8/检索序保留/失败补位/同签名去重不挤占/独特<3 时输入侧降 0.45→0.40/exact+analog 融合序）；`s5b_cli build --recorded-source` 接线 |
| W5 同一执行图载荷+中性任务+有限容错 | **done** | `real_model.execution_graph_payload`（与编译器/render/execute_edits 同一事实源：ID→idx/元素/电荷/H/手性、ID-labelled kekulé 键表、mapped SMILES、图 hash、能力版本）；系统提示词改中性"酶促单步转化"（≤8 不同净反应、弃权合法、协议示例教自动锚定）；novel 逐条 prevalidation（validate_edits 同源）+ prepare 逐条容错（一坏一合法正控、全坏 honest empty 不 run 拒） |
| W6 最小运行时闭合 | **done** | R1 批准状态白名单（approved/confirmed/preregistration_confirmed；rejected/not_approved/空/未知拒）；R2 gate 占位 ID 恰一次释放/未 acquire 不 release/幂等/死亡 owner 回收无 TTL/total_requests 不退/参数冻结装配+篡改拒；R3 响应 blob 原子保存+SHA/字节/字符校验先于 responded、responded+blob 零调用重放、blob 缺失/篡改 replay_unavailable、sent+blob 恢复、sent 无 blob 保守 failed；R4 validated case reader（qid/run_id/schema/终态/env_check 另文件）+ 原子 case 写 + 单协调者 flock + stderr 有界主动 drain；R5 首批 1 logical/qid、format 0、gate cap 1490（298×1×5）、模型身份含 retry/timeout、worker_timeout 负值拒/0 禁用/正值 monotonic+terminate/kill、孤儿禁新 logical 请求 |
| W7 公共链证据+回归+有限交付 | **done** | 见下（入口矩阵/定向/全量/G01/评审请求/本交付书） |

诚实缺口（unsupported/未执行，全部为设计内首版边界，非隐蔽失败）：

1. **charge-only/stereo-only 编辑**：v43-editproto-2 无对应 op ⇒ 编译
   层稳定 `charge_edit_unsupported`/`stereo_edit_unsupported`（W5 允许
   首版 unsupported + 能力覆盖诊断：池侧 compile_failure_histogram
   按原因计数披露）。真实语料受影响面未测（零真实批，未执行）。
2. **芳香环新合成**（新成键目标 aromatic）：诚实 unsupported
   （aromatic_new_bond_unsupported）。
3. **recorded CN candidate**（CN 同而电荷/立体异）不升格 strict 且
   编译层通常被对齐/电荷拒——供给损失如实披露（mimo 请求 C4 请评）。
4. **W4 阈值 0.45/0.40 的独立开发集比较**未执行（需授权 corpus
   开发集与零模型统计；本轮仅合成正负控 + 冻结参数实现）。
5. **W2 的"单一合法 strict 源预注册 0 模型确定性候选"**未做独立
   提交路径（任务书要求新增 source-only 路径须先交复审设计）；
   现状：无 model 配置的 run 中 recorded/exact 池候选经确定性
   fallback 排序走完整公共链提交（等价能力已具备，未单独预注册）。
6. **真实 recorded 語料上 strict 命中数**未测（需真实批；不得以
   source 卡数量宣称 150 可达——任务书 W2 明令）。

## 二、入口矩阵（任务书 §2；全部复用同源 helper，无第二套判据）

| # | 入口 | 消费的身份/事实/版本 | 本轮改动与验收 |
|---|---|---|---|
| 1 | asset lookup/build | 引擎 identity_block（library sha256）+ analog corpus | W2：库回读前 hash 校验（篡改负控过） |
| 2 | compile | `s5b_compiler.compile_donor_template`（s5b-compiler-1）/`compile_recorded_reaction`（s5b-recorded-source-1，inferred 标注） | 十二组正负控；失败结构化 reason 不吞异常 |
| 3 | payload/parse/prepare | `real_model.execution_graph_payload`（W5，与 1 同一事实源）；`parse_model_proposals`（协议 -2 不变）；`prepare_hypothesis` | novel 逐条 prevalidation（validate_edits 同源） |
| 4 | execute | `atom_tool.execute_edits`（v43-editproto-2 不变；冒烟修复已在基线） | 编译产物离线执行验证后入池 |
| 5 | donor/audit/admission | `check_edit_against_donor`（D 命名空间中心）+ `audit_hypothesis` + `decide_admission` | 组 3 正/负控（S 命名空间 ⇒ center unknown） |
| 6 | store | `store.submit_event`（events INSERT 用 `event.created_at` 微秒级；重放不刷新） | W3 时间正负控穿 store→export |
| 7 | export/score | `native_export`（读回事件 created_at 原样）→ `s5b_scoring`（U/H5/L 诊断 + 双表闭合断言） | 合成批端到端（W0 测试） |
| 8 | resume/replay | `resume_ppv1_run`（事件幂等不重提交）+ `ppv1_real_fetch`（R3 blob 零调用重放/孤儿禁新 logical） | W1/W6 测试 |

正负控公共链证据（至少一合法实例穿全链）：

- `tests/test_ppv1_s5b_hit50_w1.py::test_g1_ordered_template_through_public_chain`
  （compile→prepare→execute→diagnostic→audit→admission→store→export→
  resume/replay 幂等）；
- `tests/test_ppv1_s5b_hit50_w1.py::test_g12_duplicate_product_plan_public_`
  `chain_and_replay`（重复净反应去重→单事件→replay 不重提交）；
- `tests/test_ppv1_s5b_hit50_w23456.py::test_w0_aggregate_diagnosis_...`
  （build→orchestrate（子进程 worker）→score 合成端到端含 U/H5/L）。

## 三、回归证据（机器可复跑）

- 定向（受影响面）：
  `~/miniconda3/envs/depending43/bin/python -m pytest tests/test_ppv1_s5b_hit50_w1.py tests/test_ppv1_s5b_hit50_w23456.py tests/test_ppv1_s5b_runtime.py tests/test_ppv1_s5b_pairing.py tests/test_ppv1_s5b_rework_l01.py tests/test_rate_gate.py tests/test_ppv1_s3b_runner.py tests/test_ppv1_s3b_model.py tests/test_ppv1_s3b_r2.py tests/test_ppv1_s3b_r3.py tests/test_ppv1_s3b_production.py tests/test_ppv1_s3b_queue.py tests/test_atom_tool.py tests/test_ppv1_s4a_endpoint.py tests/test_ppv1_s4b_export.py -q`
  ⇒ **全绿**（合计 180 项级别；分批数字见执行记录）。
- 全量（仓规 required）：
  `~/miniconda3/envs/depending43/bin/python -m pytest tests/ -q -m "not slow"`
  ⇒ **1813 passed / 0 failed / 16 deselected（not slow）**（最终轮，
  含 s5b_scoring None-归一修复与导入归并后再跑；≈4.5 分钟）；
  基线 1788 passed + 本轮新增 41 tests = 1829（含 slow 16）一致闭合。
- **G01（隔离安全运行）**：控制器 `/tmp/safe_g01_s5b_hit50.py`
  （沿 s5b_rework 基谱系；allowlist = R7 清单 + 历轮增量 + 本轮
  12 个新输入：s5b_compiler/recorded_source/real_model/s5b_builder/
  s5b_cli/s5b_orchestrator/s5b_scoring/s5b_worker + 4 个 s5b 测试
  文件；变更集相对 r3 G01 披露为 20 个已允许输入换字节 —— 含
  smoke-fix 轮的 atom_tool 两件与本轮 13 件源码/5 件测试）。
  运行结果见 §七（完成后回填实际数字；`python -B`、
  `-p no:cacheprovider`、输入 SHA 前后核验、pyc 扫描、junit 缺项
  披露全部沿既有模式）。本轮首次把 s5b runtime 源码与测试纳入
  G01 拷贝集（此前 G01 证据不含这些文件 —— 历史覆盖缺口，如实
  披露）。

## 四、合成正负控覆盖表（任务书 W1 十二组 + W2/W3/W4/W5/W6）

| 组 | 覆盖 | 断言要点（测试） |
|---|---|---|
| 1 | 有序乙醇→乙醛正控（公共链）+ rhs 反写 | CC=O；center direct True；反写等价不变成 C=CO |
| 2 | 模板迁移 CCCO→CCC=O | 额外 C 保留（不能仍 CC=O）；CCCCC→CCCCC=O 旁基保留 |
| 3 | S/D 命名空间错配负控 + D 正控 | S 中心 ⇒ center unknown（donor_centers_partially_unmapped）；D ⇒ True |
| 4 | 新 O 合法 ID / 旧 S_O_N1 坏格式 / 未知元素 / 撞 ID | SN_O_* 匹配 ATOM_ID_RE 且元素一致；四类拒因逐条 |
| 5 | add_atom 锚定单键不重复 form | edits==[add_atom]；对已有键 form ⇒ 执行器 bond_already_present 硬拒 |
| 6 | 新 double/triple 真实形成 | 酸化（新 O double 落位）、炔（triple）；仅 single 的旧行为被覆盖 |
| 7 | 芳香共振不算键差 + 合法去芳香 | 甲苯→苯甲酸环零编辑；苯→1,4-环己二烯（Birch 型）执行 |
| 8 | donor 带侧链模板/current 甲苯 | 环零编辑、旁基保留、from_order 闭合；苯模板对甲苯的无差别落位归组 11 ambiguous |
| 9 | 芳香化正控 + 非法价态拒 | 1,3-环己二烯→苯；吡咯啉→吡咯（杂环）；六价碳 sanitize 拒 |
| 10 | charge-only/stereo-only | 稳定 unsupported + detail 携带受影响 map |
| 11 | 重复 map/元素变化/对称歧义/等价映射 | 三类拒 + 等价合并（乙烷断键）；丁烷两断法 ⇒ ambiguous |
| 12 | 重复产品计划公共链 + 真冲突 | 去重单事件 + replay 幂等 + export 读回；store 冲突/契约族拒绝 |
| W2 | strict exact/完整产物/推断映射/负控族 | 分层计数、多重集核对、缺产物/另一底物/CN 异/篡改/枚举触顶 |
| W3 | rank 规则/时间/去重 | 显式 rank 先于 fallback、novel 位次补回、payload 冻结字段、微秒互异 created_at、export 一致 |
| W4 | 补位/检索序/去重/降阈值 | 前 3 坏第 4 合法入池、merged_source_keys、失败直方图 |
| W5 | 载荷/容错/提示词 | 执行图与 render 同源、一坏一合法、中性任务+8 净反应 |
| W6 | R1–R5 | 白名单、占位恰一次、blob 重放、孤儿禁新 logical、case 校验、超时负值拒、1490/1/0 缺省 |

## 五、源许可/哈希与金标边界自查

- recorded 源：仅消费 `engine.identity_block` 的 library_path/sha256
  （公共接口）；库文件实际 sha ≠ 身份记录 ⇒ `library_hash_mismatch`
  fail-closed（负控过）。analog 模板通道沿 `AnalogSourceResolver`
  既有资产 SHA（未改）。未搬 C0/旧 run 答卷、qid→答案表、参考图→池。
- **金标边界自查声明**：本轮实施**未读** 298 题卷/金标/旧答卷/封存
  逐题 run（`/Volumes/CC/Enzyme_Agent/ec298_phase_a_seal/` 等未访问）；
  **零真实模型调用、零花费**（scripted 桩与合成响应 only）；**未
  push、未部署真实批**；冻结判据文本/旧预注册/`S5B_PASS_LINES`/
  旧批 batch_root 全部未动。未自行启动 298 复测（等待主会话复审）。

## 六、待复审问题清单（给主会话）

1. **W3 去重与 S4a"distinct routes"契约的边界**：本轮按任务书 W3
   （同净产品集合+step_scope+参与物语义去重、合并 provenance）在
   decide 层合并完全相同净反应的备选；S4a 时代 3 个测试夹具（同
   产物双备选）已按"不同共同产物集合"改造保留原意图。若复审认定
   不同 donor 来源的相同净反应应保留为独立事件，需改判据（同轮内
   拍板）。
2. **R2/R4/R5 的默认值变更**：S5B_DEFAULT_PROFILE_POLICY 的
   max_real_model_requests 5→1、format_feedback 2→0、gate max_calls
   600→1490 是任务书 §3 首批冻结数值的实施；真实发车前主会话按
   当日快照定稿（含 60 CNY 硬帽估算的核算）。
3. **blob 重放对 scripted 桩无 call_account_path 的跳过语义**：真实
   适配器必配 account path（worker 已如此）；测试桩未配置时跳过
   blob（resume 时 replay_unavailable 如实拒）。
4. **W2 source-only 0 模型预注册路径**未实施（见缺口 5）——是否
   需要，请复审裁定。
5. G01 历史证据未含 s5b runtime 文件的覆盖缺口已在本轮补齐（见
   §三）；是否要求评审侧重跑历史轮，由主会话决定。

## 七、G01 隔离运行结果（实际数字）

- 输出根：`/tmp/g01_s5b_hit50/`（易失；关键数字如下，junit/输入
  SHA 清单/post-run 校验在输出目录内）：
  - pytest 结果：**1802 passed / 0 failed / 10 skipped / 17
    deselected, exit 0**（261s;not slow + 显式排除 1 例沿既轮）。
    与本机全量（1813/0/16）的 11 题差 = G01 钉死环境的既知模式
    （BBD_DATA_ROOT 空 ⇒ missing_v4_parser_source 等 skip 归类差 +
    显式 deselect 1 例），与 s5b_rework 轮 G01 的环境差异模式一致。
  - 输入 SHA 前后核验：**全部一致**（input_sha_mismatches=[]，
    320 个输入复验）；pyc 扫描 7 个（子进程缓存例外，与上一轮
    G01 的同类文件清单一致，如实记录于 post_run_sha_result.json）。
  - 变更集核对：相对 r3 G01 输入集的换字节输入 = 披露清单精确一致
    （smoke-fix 轮 atom_tool 两件 + 本轮 13 件源码/5 件测试；见
    preparation.json 的 changed_inputs_vs_r3_g01）。
  - 本轮 G01 首次把 s5b runtime 源码 + 测试纳入拷贝集（此前各轮
    G01 证据不含这些文件——历史覆盖缺口，如实披露）。

## 八、成本与后续

- 本轮实施真实模型费用：**0 CNY**（零调用）。
- 后续（复审通过后，由主会话按已授权分工执行，不在本交付内）：
  新预注册冻结（同模型 GLM-5.3-Flash、profile depth=1/池 8/宽 2/
  1logical/format0/retry4/workers40/RPM180/TPM2.7M、gate cap 1490、
  同日价格快照、硬帽 60 CNY 估算）→ 一次完整真实 298 → 零 LLM 判分
  （主口径 matched_strict hit@5，分母 298 固定）→ 达标标
  `target_met_seen298` / 未达标标 `target_not_met` 并交完整报告。
- mimo 规则级化学评审请求（场景 1 判据评审）：
  `docs/S5B_HIT50_W7_MIMO_CHEM_REVIEW_REQUEST_2026-10-09.md`
  （自包含、零金标；**未发送**——按 AGENTS.md 由用户送 mimo）。

## 九、本轮改动清单（commit 内容）

源码（17 改 + 2 新）：
- 新 `src/pathway_v43/pollutant/s5b_compiler.py`（W1，s5b-compiler-1）
- 新 `src/pathway_v43/pollutant/recorded_source.py`（W2，
  s5b-recorded-source-1）
- 改 `domain/models.py`（now_iso_hires，W3）
- 改 `pollutant/events.py`（事件首提微秒时间戳，W3）
- 改 `pollutant/store.py`（events INSERT 忠实采用 event.created_at，W3）
- 改 `pollutant/runflow.py`（W3 排名统一 + novel 位次补回 + 净反应
  去重 + W5 novel 逐条容错 + 执行图载荷接线 + W1 #9 followup 去重）
- 改 `pollutant/production.py`（W1 #9/#10 产物 distinct 调度 + basis）
- 改 `pollutant/s5b_builder.py`（W4 池策略重写 + 池诊断入 manifest）
- 改 `pollutant/s5b_cli.py`（--recorded-source 接线）
- 改 `pollutant/real_model.py`（W5 载荷/中性提示词/费用字段 +
  R3 blob + R5 孤儿禁新 logical + 身份含 retry）
- 改 `pollutant/s5b_scoring.py`（W0 诊断 + R1 白名单 + 双表闭合）
- 改 `pollutant/s5b_orchestrator.py`（R4/R5 + 1490 + 协调者锁）
- 改 `pollutant/s5b_worker.py`（R4 env_check 另文件/原子写/schema）
- 改 `adapters/rate_gate.py`（R2 占位/回收/冻结装配/核对）
- 改 `adapters/llm_client.py`（R2 占位贯穿全部释放路径）

测试（2 新 + 6 改）：新 `tests/test_ppv1_s5b_hit50_w1.py`（19）、新
`tests/test_ppv1_s5b_hit50_w23456.py`（22）；改 s3b_runner/s3b_r2/
s4a_endpoint/s4b_export（W3 去重契约下的夹具改造，保留原意图）。

文档（3 新）：本交付书、W0 勘误表、W7 mimo 评审请求（均零金标）。
