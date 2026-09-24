# v4.3 预测接线实施报告(TASK_V43_PREDICTION_ATOMTOOL)

> 日期:2026-09-24。基座:第一阶段确定性主干(105 项测试、21/21 资产清单)。
> 本轮交付:类比来源适配、PredictionTask 三协议、AtomTool(MoleCode)、
> LangGraph 预测分支、预测产物持久化与恢复、旧 run 显式迁移入口;
> R1 review 4 项缺陷修复见 §13。
> 全程无凭证环境可运行;真实提供者在线调用**未实测**(本机无凭证,如实标注)。

## 0. 结论速览

- 全量测试:**168 passed**(105 项第一阶段基线全绿 + 56 项第二阶段新增
  + 7 项 R1 修复回归),`5:24`;资产清单 21/21 OK。
- 真实资产烟测(catechol + 假模型):3 条竞争 recorded → `rank_candidates` →
  选中卡经确定性门禁提交,事件带 `model_ref`;101 张证据卡逐卡哈希核对通过。
- 供体找回真实覆盖率(98 张预测卡):**5 resolved**(唯一映射模板且对齐)、
  15 ambiguous(多模板产出同产物)、78 unavailable —— 拒因逐卡留痕,
  未编造任何映射。
- 示例 run:`runs/v43-predict-smoke`(假模型,completed)、
  `runs/v43-predict-off`(无模型,awaiting_prediction)、
  `runs/v43-smoke`(第一阶段原样保留)。

## 1. 交付文件

### 新增

| 文件 | 职责 |
|---|---|
| `src/pathway_v43/vendor/molecode/` | AtomFlow-AI/MoleCode **molecule+prompts 子集**(逐字节拷贝,MIT,`PROVENANCE.md`+`LICENSE`+`MANIFEST.sha256` 随包);顶层 `__init__` 为本仓自写(不导入 markush/polymer/llm,环境无 networkx),上游原文存档于 PROVENANCE §4 |
| `services/atom_tool.py` | SMILES↔MoleCode 渲染(带 atom_id_map)、往返身份核对(有损即拒)、编辑引用核验(原子/键存在性)、目标 MoleCode 原子不灭检查、供体映射确定性对齐、元素 delta、vendor 哈希自检 |
| `services/analog_source.py` | DonorResolver:稳定 record_id 解析映射模板(`assets/analog/corpus_templates_v1.jsonl`)、产物→模板/记录反查(`corpus_v1`)、映射质量判定(qc_flags:element_balance+bijection)、供体→当前分子两级对齐(全供体→反应中心) |
| `services/prediction.py` | PredictionTask 组装(v43-prediction-task-1)、响应确定性解析器、提案卡构造(全部挂牌预测) |
| `adapters/llm_client.py` | 唯一出网点:off/fake/openai_compatible;FakeLLMClient(剧本+跨进程计数);真实提供者(urllib,密钥只读环境变量,支持 Idempotency-Key);提示词版本哈希 |
| `configs/prompts/{ranker,analogy_editor,novel_proposal}.md` | 三协议提示词:响应 JSON 契约 + 预测纪律(不得宣布确切命中/条件相容/校准概率) |
| `tests/test_atom_tool.py`(14)、`test_analog_source.py`(10)、`test_prediction_task.py`(19)、`test_prediction_workflow.py`(10)、`test_prediction_recovery.py`(8)、`test_prediction_real.py`(2, slow) | 验收用例(§4) |

### 修改

| 文件 | 变更 |
|---|---|
| `domain/models.py` | `EVIDENCE_KIND_NOVEL`、预测模式常量、`Decision.prediction_mode/reason`、`ReactionEvent.model_ref` |
| `domain/policy.py` | STRATEGY_VERSION→`v43-policy-2`;`decide_prediction_route`(纯函数路由);`prediction_policy`(`v43-predpol-1`);stop_reason 感知 LLM 预算 |
| `services/reaction_finder.py` | 检索卡 schema→`v43-retrieval-2`(+`donor_refs/mapping_status/mapping_reason`);可注入 AnalogSourceResolver;scripted 卡透传 donor 字段 |
| `storage/pathway_store.py` | store→`v43-store-2`:`reaction_events.model_ref` 列(pragma 检查+ALTER 迁移);`count_events_by_kind` |
| `storage/artifact_store.py` | `count_llm_calls()`(调用记录数=持久 LLM 记账源,悬空也计费) |
| `storage/run_identity.py` | 身份新增 `prediction`(provider/model/提示词版本/策略)与 `molecode`(vendor 哈希)块;resume 逐字段核对 |
| `workflow/state.py` | Budget + LLM/提案额度;State + prediction_mode/task_id/response_ref/predicted_evidence_id/prediction_failed(仍只持引用) |
| `workflow/nodes.py` | classify 后路由预测协议;新增 `prepare_prediction`/`call_model`/`apply_prediction` 三节点;call_model 同键重放+悬空孤儿审计+重试上限+LLM 预算守卫;validate/commit 接受选中卡与提案卡;提案加元素变化门禁 |
| `workflow/routing.py`、`graph.py` | 预测分支条件边(模型未配置时与第一阶段图完全一致) |
| `workflow/runner.py` | start_run/resume_run 接收 model;`migrate_from` 显式迁移;身份重建含 prediction 块;resume 时 prediction 启用而 model 缺失 → 结构化拒绝 |
| `output/report.py` | 路径级 prediction 视图、事件 model_ref、`llm_calls` 统计(调用/响应/孤儿/传输失败)、summary 预测计数 |
| `__main__.py` | run/resume 增 `--model off|fake|real`、`--fake-script`、`--max-llm-calls/--max-proposals`、`--migrate-from` |

## 2. 协议与 schema

| 项 | 值 |
|---|---|
| 预测任务 | `v43-prediction-task-2`(R1 起升版:siblings 实装、current 去 smiles_raw,§13):run_id/task_id(派生)/path_id/mode/root(**smiles_raw=真实原始输入**+identity)/current(**smiles_canonical+identity;原始 SMILES 非根路径不可得,不再以 canonical 冒充 raw**)**/ancestry(按时间序,每步父/子 path_id、入边事件 evidence_id+hash+kind)**/conditions/retrieval(task_id+payload_hash)/candidates(含 asset_sources、donor_refs)/donor(映射+对齐+当前分子 MoleCode)/**siblings(同父已提交兄弟:path_id/substrate_identity/depth/status/product_position/入边事件 event_id+evidence_id+evidence_kind/display_name=S{深度}{位次链};根路径无兄弟=空)**/budget(depth/expansions/llm/proposals 剩余, max_reportable=5)/discipline/model/prompt_version/policy_version |
| 预测调用 | `prediction_call.aN.json`(status=issued、request_hash、idempotency_key、模型、提示词哈希);`prediction_response.aN.json`(transport+parsed);`prediction_orphan.aN.json`(悬空审计卡) |
| 预测结果 | `prediction.json`(`v43-prediction-result-1`):outcome ∈ selected/proposed/held/abstained/failed/rejected + parsed 响应 + 提案卡全文 + atomtool_checks |
| 提案卡 | kind=`analog_reaction`(类比)/`novel_proposal`(新提案);`score_semantics=model_proposal_qualitative_only_no_calibrated_probability`;source_record 携带 task/attempt/model/prompt/policy/donor/atomtool 引用 |
| 预测 task_id | stable_id(run_id, path_id, "prediction", 当前分子身份, **检索产物 payload_hash**, mode, model_id, prompt 版本哈希, policy_version, strategy_version)——同键由路径+分子+检索哈希+模式+模型/提示词/策略决定(任务书 §4) |
| 三协议输出契约 | rank:`{decision: select|hold, evidence_id∈候选, order, reasons, reason}`;analogy:`{decision: apply|abstain, target_molecode, edits, referenced_evidence_id, reason}`;novel:`{decision: propose|abstain, products≤5, uncertainty, reason}` |

## 3. 三协议路由判定(domain/policy.decide_prediction_route,纯函数)

```
0. commit_recorded(唯一可用 recorded)      → 永不进模型(确定性直通,验收 5.2 钉子)
1. 模型未配置 / LLM 预算耗尽                → ""(走第一阶段 mark_awaiting/mark_dead_end)
2. usable recorded ≥ 2                      → rank_candidates(模型只能在既有候选中裁决)
3. 存在 mapping_status=resolved 的规则/类比卡 → analogy_edit(取排位最高者)
4. 规则/类比但映射 unavailable/ambiguous     → 策略 allow_novel_on_mapping_failure
                                              且提案额度>0 → novel_proposal;否则停留(hold)
5. 无可用证据(dead_end)                    → allow_novel_on_no_evidence 且提案额度>0
                                              → novel_proposal;否则 dead_end
```
预算持久事实源:`used_llm_calls`=已落盘 `prediction_call.*.json` 数(悬空/失败
attempt 都真实耗额,如实计入);`used_proposals`=账本中 `novel_proposal` 事件数;
`used_expansions`=已落盘检索产物数(第一阶段语义不变)。

## 4. 验收用例对照(任务书 §5.1–§5.7)

| 验收项 | 测试 | 状态 |
|---|---|---|
| 5.1 两步祖先链入任务书;两来路不串线 | `test_prediction_task.py::test_task_carries_full_two_step_ancestry_with_evidence`、`::test_same_molecule_two_routes_two_tasks_no_cross_talk`、`::test_model_never_sees_display_name_only_identity` | PASS |
| 5.2 竞争裁决只选既有反应;多产物同一事件;未选候选+理由留痕;唯一 recorded 不触发 LLM | `test_prediction_workflow.py::test_rank_selects_recorded_multi_product_one_event`、`::test_single_recorded_never_calls_model` | PASS |
| 5.3 四类路由正确;类比编辑可核对映射+MoleCode 往返;缺映射不得假成功 | `test_prediction_task.py::test_route_*`(5 项)、`test_prediction_workflow.py::test_analogy_edit_end_to_end_with_roundtrip`、`::test_analogy_missing_mapping_cannot_fake_success`、`::test_hold_stays_awaiting_with_model_reason` | PASS |
| 5.4 无效结构/价态/映射错位/重复兄弟/循环/条件冲突/表示有损/预算/终点锁定各有拒因不污染账本 | `test_prediction_workflow.py::test_novel_invalid_products_rejected_with_reasons`;AtomTool: `test_atom_tool.py::test_roundtrip_isotope_is_lossy_and_refused`、`::test_edit_reference_*`、`::test_target_molecode_*`;`test_prediction_workflow.py::test_parse_failure_retries_then_explicit_stop`、`::test_invalid_evidence_id_never_commits`、`::test_llm_budget_exhaustion_stops_run`;深度锁定 `test_workflow_scenarios.py::test_depth_limit_status`(基线) | PASS |
| 5.5 假模型计数器 + 中断夹具:响应落盘后/事件提交后恢复无重复;悬空状态按文档处理 | `test_prediction_recovery.py::test_crash_after_response_persisted_no_recall_no_duplicate`、`::test_crash_after_commit_resume_replays_prediction_idempotently`、`::test_dangling_request_orphan_audited_then_retried_once`、`::test_prediction_identity_drift_rejected_on_resume`、`::test_resume_with_model_off_rejected_when_prediction_enabled` | PASS |
| 5.6 真实资产烟测逐卡核对哈希;停机原因/候选/提交结果如实;真实提供者未实测如实标注 | `test_prediction_real.py::test_real_catechol_rank_candidates_smoke`、`::test_real_donor_recovery_attempt_recorded`;提供者: `test_prediction_task.py::test_real_provider_without_credentials_structurally_unavailable` | PASS |
| 5.7 第一阶段测试与 21/21 清单继续通过;新增测试无凭证可运行;报告测试数/环境/命令/runs 示例 | 全量 161 passed;`(cd assets && shasum -a 256 -c MANIFEST.sha256)` 21/21 OK;`runs/v43-predict-smoke/report/pathway.json` | PASS |

## 5. 来源映射覆盖率与缺口(真实资产,catechol 检索)

101 张证据卡 = 3 recorded + 16 rule + 82 analog。98 张预测卡:

| mapping_status | 数量 | 主要 mapping_reason |
|---|---|---|
| **resolved**(唯一映射模板+对齐) | 5 | unique_mapped_template_aligned |
| ambiguous(多模板产出同产物) | 15 | ambiguous:{2,3,5,6,17}_templates_produce_product |
| unavailable | 78 | no_donor_record(47)、no_mapped_template:traceability_only(26,corpus_v1 仅溯源无映射)、donor_not_aligned(5) |

- resolved 卡的 donor 全部来自 `assets/analog/corpus_templates_v1.jsonl`
  (`mapped_lhs/mapped_rhs`、`center_atoms`、qc_flags 双射),ref 上带
  文件 SHA256、行号、对齐表(`{供体原子 idx: 当前分子原子 idx}`)。
- 缺口(如实):① 引擎预测边不携带 record_id,找回只能靠"产物身份→模板/记录"
  反查,多模板同产物即判 ambiguous(宁缺毋滥);② corpus_v1 记录多数
  `mapping_status=absent`,只作溯源,不冒充映射;③ 对齐采用确定性子结构
  匹配(全供体→反应中心),过严导致的 donor_not_aligned 拒因留痕。
- 找回不影响排序:retrieval_rank/score 仍为引擎原值;mapping 字段只为
  预测路由服务。

## 6. MoleCode 往返结果(AtomTool,vendor 子集完整性已锁定)

| 能力 | 结果 |
|---|---|
| 芳香/酚类(aspirin、catechol) | 无损往返 PASS |
| 手性(R/S)、E/Z 双键 | 无损往返 PASS(atom ID 带 `_R/_S` 后缀) |
| 电荷(`[NH3+]`、`[O-]`) | 无损往返 PASS |
| 多组分盐(`CC(=O)[O-].[Na+]`) | 无损往返 PASS |
| 断键/成键编辑核验 | 引用不存在的原子/键 → `edit_invalid:*` 拒;重复成键/断不存在的键 → 拒 |
| **同位素(`[13CH4]`)** | **有损**:渲染标签丢失同位素 → 往返身份不一致 → `representation_lossy` 拒绝(任务书要求的诚实行为;不做悄悄替代) |
| 目标 MoleCode 原子不灭 | 丢原子 → `mapping_inconsistent:atom_removed` 拒;同名 ID 改元素 → `element_mismatch` 拒 |
| vendor 完整性 | `verify_vendor_integrity()` 逐文件 SHA256 核验;实现被改即 fail-closed,哈希入 run_identity(`molecode` 块) |

## 7. 每类路由实际产物(runs/ 示例)

- **rank_candidates**(`runs/v43-predict-smoke`,真实引擎+假模型):
  任务书候选 8 条(3 recorded 置顶)→ 模型选 `bt0254#r0601`(检索首位)→
  确定性校验 → 1 事件 1 产物,`model_ref=prediction:T_1ccf…#a1`;
  未选候选+理由在 `prediction.json.reasons` 与报告 prediction 视图。
  任务书 schema `v43-prediction-task-2`:current 只有
  smiles_canonical+identity(无 smiles_raw);siblings=[] 如实 —— 该任务
  是根路径任务,根路径无兄弟(兄弟实装与"不串线"由 §13.2 回归钉死)。
- **analogy_edit**(测试 `ana1`,供体=真实 record `env:EAWAG-BBD:bt0001#r0022`
  辛醇→辛醛):反应中心对齐(CH2-OH)→ 模型目标 MoleCode → AtomTool 往返+映射核验
  → `analog_reaction` 事件(预测挂牌,非校准分数声明,donor/对齐/核验结果全入卡)。
- **novel_proposal**(测试 `nov1`):5 产物提案,4 个无效产物逐个拒因
  (unparseable / `element_change_not_justified:Cl` / in_path_cycle / sibling_dedup),
  有效产物保持原始位次 0 入账;`element_delta` 例外依据随校验留痕。
- **hold/abstain/failed**:显式停留待预测或 dead_end(理由 `model_hold:` /
  `model_abstain:` / `prediction_failed:`),零事件、不假成功。

## 8. 恢复前后调用/事件/路径计数(子进程硬杀实测)

| 场景 | 崩溃后 | 恢复后 | 断言 |
|---|---|---|---|
| 响应落盘后杀(`call_model_response`) | LLM 调用=1,prediction.json 未写 | 调用仍=1;事件=1;产物=2;路径=3 | 不重复调用/事件;无孤儿 |
| 提交后杀(`commit_pathway`) | 事件=1 | 事件/产物/路径/revision 与崩溃后逐项一致;LLM 调用=1 | submit_event 幂等重放 |
| 悬空(`call_model`,请求已登记未响应) | call.a1=issued | 孤儿卡×1(disposition=retried_as_attempt_2);call 记录=2;真实调用=1;事件=1;**used_llm_calls=2(悬空也计费)** | 不声称恰好一次;审计可复核 |

## 9. 运行身份(runs/v43-predict-smoke/run_identity.json)

- `strategy`: `v43-policy-2` + max_depth/max_expansions/max_frontier_width/
  **max_llm_calls/max_proposals**;
- `prediction`: `{enabled: true, provider: fake, model_id: fake-scripted-v1,
  prompt_versions: {rank_candidates/analogy_edit/novel_proposal: sha256},
  policy_version: v43-predpol-1, policy: 取值}`;无模型 run 为
  `{enabled: false, provider: off, ...}`(身份仍可比);
- `molecode`: upstream commit `a4df3b04…`、vendor 7 文件 SHA256、聚合哈希;
- `asset_identity`: 本仓 21 文件清单(manifest_sha256=def94d82…,与第一阶段一致);
- resume 逐字段核对:任一块被改 → `IdentityMismatch`(测试 pr4 钉子)。
- **第一阶段旧 run**:`prediction/molecode` 块缺失 → 直接 resume 被拒(显式、
  fail-closed);迁移入口 `run --migrate-from OLD --run-id NEW` 只读旧身份、
  记录 `migrated_from`(旧指纹),旧目录逐字节不动(测试
  `test_phase1_style_run_resume_rejected_then_migrate_from_works` 双向钉死)。

## 10. 测试与环境

```sh
cd /Volumes/CC/Enzyme_Agent/dependingv43
OMP_NUM_THREADS=1 PYTHONPATH=src /Users/cc/miniconda3/envs/depending43/bin/python -m pytest -q
# ........................................................................ [ 42%]
# ........................................................................ [ 85%]
# ........................                                                 [100%]
# 168 passed in 324.85s (0:05:24)
( cd assets && shasum -a 256 -c MANIFEST.sha256 )   # 21/21 OK
```

- 环境:Python 3.11.16(macOS arm64);rdkit 2026.03.6、lightgbm 4.7.0、
  numpy 2.4.6;langgraph 1.2.12 / langgraph-checkpoint 4.2.0 /
  langgraph-checkpoint-sqlite 3.1.1;pytest 9.1.1。
- 计数:第一阶段基线 105(全绿)+ 第二阶段新增 56 + R1 修复回归 7
  = **168**(atom_tool 14、analog_source 10、prediction_task 19、
  prediction_workflow 10、prediction_recovery 8、prediction_real 2[slow])。
  全部无凭证可运行。
- 凭证探测:本机无 `V43_LLM_*` 环境变量;真实提供者在线调用**未实测**,
  无任何假模型结果冒充在线验证(适配器与缺凭证结构化失败有测试覆盖)。

## 11. 已知限制与未尽事项

1. **真实提供者未实测**:`OpenAICompatibleClient` 为 OpenAI 兼容
   /chat/completions(urllib),仅传输层实现 + 缺凭证结构化失败有测试;
   在线行为(超时/重试/计费/Idempotency-Key 兼容性)待有凭证后验证。
2. **对齐策略保守**:全供体→反应中心两级子结构匹配;供体与当前分子
   不构成子结构关系时即 donor_not_aligned(拒因留痕)。MCS 类对齐未做。
3. **映射一致性为表示层检查**:AtomTool 保证"既有原子不灭、引用存在、
   往返无损";产物与对齐映射的逐原子化学归属仍由门禁+审计引用保证,
   不声称机理证明(元素 delta 仅作约束检查并留例外依据)。
4. `recorded_reaction` 卡原生 `atom_mapping` 仍为 unavailable(资产无此
   数据,第一阶段口径不变);proposal 卡的 `atom_mapping=model_edit_view`
   表示 MoleCode 编辑视图。
5. rank 协议候选上限 `max_candidates_for_ranking=8`(任务书未定值,
   dev 实验后冻结);冻结 eval / 298 外考未运行(任务书边界)。
6. 悬空请求的"恰好一次"由提供者幂等键支持,本地只能做到**审计+重试**
   (孤儿卡),文档明确不声称恰好一次。
7. 类比/提案事件的条件相容性一律 `unknown`(资产无条件数据,不猜测)。

## 12. 有争议的设计决策(供 review)

1. **类比来源适配选型**:主源取 `assets/analog/corpus_templates_v1.jsonl`
   (唯一逐行带原子映射+qc 旗标的供体库);`corpus_v1/donor_index` 仅作
   产物溯源。备选方案(直接用引擎内部 `_G_RECORDS` 重建)被否:那需要
   深入 v3 引擎进程内状态,且多数记录无映射,不能支持"已对齐映射"的前提。
2. **映射找回策略**:产物身份反查 + 唯一性要求(多模板即 ambiguous)。
   代价是真实资产上只有 5/98 卡 resolved;收益是每一张 resolved 卡都可
   逐项复核(文件/SHA/行号/对齐表),绝不"挑一个像的"冒充供体。
3. **悬空调用处理**:请求先落 `issued` 调用记录再发外部请求;恢复时
   issued-无-响应 → 独立孤儿审计卡 + 重试为新 attempt;悬空计入 LLM 预算。
   备选(先调用后补记录)可少一张卡但无法在崩溃后证明"请求已发出",被否。
4. **事件 model_ref**:以 `reaction_events.model_ref` 列(store v43-store-2,
   自动向旧库 ALTER 迁移)落实 ARCHITECTURE §6"事件保存模型决策引用";
   也可只在 prediction 产物中记录(少一次 schema 变更),但事件级引用
   是账本自洽审计的最短路径,选择加列。
5. **novel 弃权=dead_end**:无证据路径上模型弃权/失败记 dead_end(带模型
   理由),而非 awaiting —— 与"没有可用证据"的领域语义一致;类比/裁决路径
   的弃权/失败仍记 awaiting(证据存在,可换模型重试)。

## 13. R1 review 修复记录(2026-09-24)

外部 review(R1)发现 4 处缺陷,逐项修复如下。全量测试 **168 passed**
(161 原有全绿 + 7 项新增回归);示例 run 已删旧目录后按 README/报告同一
CLI 命令、同 run-id 重生成;不改其他任何行为,第一阶段固化语义未回退,
assets/ 未动,`runs/v43-smoke` 原样保留。

### 13.1(P1)novel 弃权/失败的重放语义分歧 —— `_novel_route` 死变量

- 缺陷:`apply_prediction` 用 `state.get("_novel_route")` 判 novel 弃权/
  失败是否落 dead_end,但该键全仓从未写入(死变量)。正常路径由
  `call_model` finalize 落账不受影响;崩溃恢复重放路径
  (crash_after="prediction_recorded":prediction.json 已落盘、checkpoint
  未写)恢复后 `call_model` 直接走 `done → phase=apply_prediction`,跳过
  finalize 的状态落账,`apply_prediction` 因 `_novel_route` 恒空把 novel
  弃权/失败错标 awaiting_prediction —— 同一局面因崩溃时点不同产生两种
  账本状态,run stop_reason 也被错误翻成 awaiting_prediction,违反恢复
  确定性。
- 修复(`workflow/nodes.py`):抽出共用判据
  `_novel_dead_route(svc, state, mode)`(读决策产物,outcome=dead_end 且
  mode=novel_proposal,与 §12.5 设计一致);`call_model` 正常路径与
  `apply_prediction` 重放路径的 abstained、failed/rejected 分支都用它;
  删除 `_novel_route` 死引用。held 分支语义不变(恒 awaiting_prediction)。
- 回归:`test_prediction_recovery.py::
  test_crash_after_prediction_recorded_novel_abstain_resumes_dead_end`、
  `::test_crash_after_prediction_recorded_novel_failure_resumes_dead_end`
  (novel 弃权 / 空响应剧本失败 × prediction_recorded 崩溃 → resume 后
  status=dead_end、stop_reason=completed(≠awaiting_prediction)、无重复
  调用);正常路径钉子 `test_novel_abstain_is_a_valid_dead_end` 继续通过。

### 13.2(P2)预测任务书缺"已有兄弟路径"(任务书 §2 违约)

- 缺陷:`build_prediction_task` 的 `siblings` 硬编码 `[]`,全仓无其他
  赋值;任务书 §2 要求的"已有兄弟路径"从未实装(烟测任务书中即空)。
- 修复(`services/prediction.py` + `workflow/nodes.py`):新增
  `sibling_task_block(store, path_id)` —— 取与当前路径同父
  (parent_path_id 相同且 path_id 不同)的全部路径;根路径无父 → 空列表。
  每条含 path_id、substrate_identity、depth、status、product_position、
  入边事件引用(event_id/evidence_id/evidence_kind,经 store.get_event,
  无事件为 None)、display_name(domain.pathway 按结构计算,
  S{深度}{完整位次链} 口径)。`build_prediction_task` 增加
  `siblings: list[dict] | None = None` 参数写入任务书;
  `prepare_prediction` 组装传入。
- 回归:`test_prediction_task.py::
  test_sibling_paths_in_task_from_committed_parent_event`(父路径事件已
  提交且已有另一条子路径 → 后续预测任务书 siblings 恰含那条兄弟:身份/
  状态/位次/事件引用/展示名,且不含当前路径自身;根任务 siblings=[])、
  `::test_same_molecule_two_routes_two_tasks_no_cross_talk` 扩展兄弟断言
  (S211 任务 siblings=[] —— S12 来路的 S221/S222 不串入;S221 任务兄弟
  恰含 S222,与自身同源同父事件)。

### 13.3(P2)`urllib.error.TimeoutExpired` 不存在 → 真实提供者超时路径 AttributeError

- 缺陷(Python 3.11.16 实测):`urllib.error` 只有
  ContentTooShortError/HTTPError/URLError,**没有 TimeoutExpired**;网络
  超时实际抛 TimeoutError(socket.timeout 的 3.10+ 别名)或
  URLError(reason=TimeoutError())。原代码异常匹配在求值
  `urllib.error.TimeoutExpired` 时即 AttributeError,吞掉原始异常炸掉
  节点,而不是返回结构化 `LLMResponse(ok=False, error_kind="timeout")`。
- 修复(`adapters/llm_client.py`,OpenAICompatibleClient.complete):
  异常分类改为 HTTPError(URLError 子类,先分出以保留类型名消息)→
  TimeoutError → URLError(按 reason 是否 TimeoutError 分
  timeout/transport_error,消息仅类型名)→ 兜底 Exception
  (transport_error)。其余逻辑不变;error_message 不含密钥或 URL。
- 回归(`test_prediction_task.py`,monkeypatch urllib.request.urlopen,
  无网络;全部 ok=False、不抛异常):
  `::test_real_provider_timeout_error_structured`(TimeoutError→timeout)、
  `::test_real_provider_urlerror_with_timeout_reason`
  (URLError(TimeoutError)→timeout)、
  `::test_real_provider_urlerror_transport_error`
  (URLError(OSError)→transport_error)、
  `::test_real_provider_http_error_transport_error`
  (HTTPError→transport_error)。

### 13.4(P3)任务书 `current.smiles_raw` 名不副实

- 缺陷:`current.smiles_raw` 传的是 canonical 身份(店内只持久化身份,
  非根路径的原始 SMILES 不可得),与字段名及任务书 §2"原始/规范 SMILES"
  不符,误导模型与审计。
- 修复(`services/prediction.py`,诚实化):root 块保留 `smiles_raw`
  (真实原始输入,run_identity inputs)+ identity;current 块删除
  `smiles_raw`,只保留 `smiles_canonical`(检索产物 query)+ identity;
  破坏性字段变更升 `PREDICTION_TASK_SCHEMA_VERSION = "v43-prediction-
  task-2"`(prediction_task_id 派生不含 schema 版本,旧产物仍可读)。
- 回归:§13.5 示例产物断言;既有任务书测试全绿(current 键断言不依赖
  smiles_raw)。

### 13.5 收尾核验

- 全量:`OMP_NUM_THREADS=1 PYTHONPATH=src /Users/cc/miniconda3/envs/
  depending43/bin/python -m pytest -q` → **168 passed in 324.85s
  (0:05:24)**;资产清单 21/21 OK。
- 示例 run 重生成(`rm -rf` 旧目录后同命令同 run-id 重跑):
  - `runs/v43-predict-smoke`:任务书 schema=`v43-prediction-task-2`;
    current 键 = {identity, smiles_canonical}(无 smiles_raw);
    root.smiles_raw="Oc1ccccc1O";根路径 rank 任务 siblings=[] 如实
    (根无兄弟,不硬凑);行为与旧样本一致 —— 8 候选(3 recorded 置顶)
    → 选 `bt0254#r0601` → 1 事件 1 产物,stop_reason=completed。
  - `runs/v43-predict-off`:无模型,stop_reason=awaiting_prediction,
    0 预测任务(不变)。
- `runs/v43-smoke`(第一阶段样本)未做任何改动。
