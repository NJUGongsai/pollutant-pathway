# v4.3 第三阶段实施计划:PredictionAgent、AtomTool 与预测接线

> 对应任务书 `docs/TASK_V43_PREDICTION_ATOMTOOL.md`。日期:2026-09-24。
> 基线:第一阶段主干(105 passed,21/21 资产清单)不回退;本计划先写后做。

## 0. 总体决策(带理由)

| 决策 | 选择 | 理由 |
|---|---|---|
| 类比供体来源 | 主源 `assets/analog/corpus_templates_v1.jsonl`(带 `mapped_lhs/mapped_rhs/center_atoms/qc_flags`,稳定键 `record_id`,含 `line_no`);辅源 `assets/v3_reactions/corpus_env/{corpus_v1,donor_index}.jsonl`(用于把检索候选产物找回贡献记录) | analog corpus 是本仓唯一"逐行带原子映射+质量旗标"的供体库;corpus_v1 是引擎检索事实源(记录 product_components),可确定性地反查"哪些记录能产出该产物" |
| 引擎检索卡的 donor 找回 | 检索时按"产物身份 → corpus_v1 记录"扫描(每 find 一次建立反向索引);唯一贡献记录且供体可与当前分子对齐 → 卡标 `mapping_status=resolved` + `donor_refs`;多记录贡献 → `ambiguous`;无记录/对齐失败 → `unavailable`(拒因留痕)。**不用来源字符串或候选产物编造映射** | 引擎 pred 边不携带 record_id(读 v3 源码确认),扫描是确定性事实推导;歧义时宁缺毋滥 |
| 检索卡补字段 | schema 升 `v43-retrieval-2`,新增 `donor_refs`/`mapping_status`/`mapping_reason`,旧 v1 读取兼容(全部 `.get` 缺省) | 任务书 §1:升版本+兼容读取 |
| 对齐策略 | 先全供体子结构匹配(full_donor_substructure),失败再映射中心子图(reaction_center_substructure);取 RDKit 确定性首匹配;供体==当前分子不算类比 | 可复核、确定性;过严的代价(对齐失败→mapping_unavailable)如实留痕,不假成功 |
| 模型路由 | 纯函数策略 `decide_prediction_route`(domain/policy.py):≥2 条可用 recorded → `rank_candidates`;存在 resolved+aligned 类比卡 → `analogy_edit`;仅规则/类比但映射不可用 → 策略允许时 `novel_proposal`,否则按原语义停留;无证据 → 策略允许时 `novel_proposal`,否则 dead_end。**唯一可用 recorded 永不进模型**(确定性直通不变) | 三协议分工照任务书 §2 表;第一层路由必须是确定性代码 |
| MoleCode | vendor `molecule/` + `prompts/` 子集(字节一致)+ 本仓自写包 `__init__`(不 import markush/polymer/llm,环境无 networkx);PROVENANCE+LICENSE+子集 MANIFEST 随包;AtomTool 启动时核验子集哈希 | 上游 MIT 允许再分发;mk/llm 子模块本仓不用;code_identity 自动锁 MoleCode 实现 |
| 模型接入 | `adapters/llm_client.py` 唯一出网点;provider ∈ {off, fake, openai_compatible};真实提供者 OpenAI 兼容 /chat/completions(urllib),密钥只读环境变量 `V43_LLM_API_KEY`,请求带 `Idempotency-Key`;无凭证 → 结构化 unavailable,不冒充在线验证 | REPO_DESIGN 依赖方向;任务书 §2/§4 |
| 悬空调用 | 调用前写 `prediction_call.aN`(status=issued,含请求哈希+幂等键);响应落 `prediction_response.aN`;恢复时 issued 无响应 → 写 `prediction_orphan.aN`(审计记录:孤儿请求,处置=重试为第 N+1 次),再发新调用;重试上限 `max_parse_retries`+1 | 不可变产物存储不允许改写已落盘状态,孤儿单独立卡可审计;明确不声称恰好一次 |
| 预测产物 | `results/<task_id>/`: `prediction_task.json`、`prediction_call.aN.json`、`prediction_response.aN.json`、`prediction_orphan.aN.json`(如有)、`prediction.json`(最终结构化结果)、`validation.json`(既有) | 任务书 §4 分别落盘;同键幂等/冲突语义沿用 ArtifactStore |
| 预测 task_id | stable_id(run_id, path_id, "prediction", 当前分子身份, 检索产物 payload_hash, mode, model_id, prompt 版本, PREDICTION_POLICY_VERSION, STRATEGY_VERSION) | 任务书 §4 同键定义(路径+分子+检索哈希+模式+模型/提示词/策略) |
| 事件模型决策引用 | reaction_events 加列 `model_ref TEXT NOT NULL DEFAULT ''`(init 时 pragma 检查+ALTER 迁移),store schema 升 `v43-store-2`;ARCHITECTURE §6 要求事件保存模型决策引用 | 旧 DB 可迁移;旧 run 仍被身份门槛拒绝 resume |
| 旧 run 入口 | `run --migrate-from OLD --run-id NEW`:只读旧 run_identity.json 取 inputs/strategy,新身份记录 `migrated_from`(旧指纹+原因),旧目录零改动;旧 run 直接 resume → IdentityMismatch(显式、fail-closed) | 任务书 §4 二选一里的"显式迁移入口";绝不静默改写旧身份 |
| 预测纪律 | 模型响应只产生"提案卡"(proposed card)或"选择既有卡";一切经既有 validate_products 门禁;提案卡 kind ∈ {analog_reaction, novel_proposal},score_semantics 声明 `model_proposal` 置信定性;拒因全部留 validation/prediction 产物 | 硬约束 D;模型输出永远不是化学事实 |

## 1. 模块划分

新增:

| 文件 | 职责 |
|---|---|
| `src/pathway_v43/vendor/__init__.py`、`vendor/molecode/*` | molecode molecule+prompts 子集(字节一致)+ 自写包 init + PROVENANCE.md + LICENSE + MANIFEST.sha256 |
| `services/atom_tool.py` | SMILES↔MoleCode 往返、往返身份核对(有损即拒)、原子 ID 表(渲染期 atom_id_map)、编辑引用存在性核验、供体映射→当前分子的确定性对齐辅助、vendor 完整性自检 |
| `services/analog_source.py` | DonorResolver:按稳定 ID 流式找回供体(analog corpus / corpus_v1+donor_index);`align_donor_to_current`;`recover_donors_for_card`(产物→记录反查);映射质量判定 |
| `services/prediction.py` | PredictionTask 组装(完整祖先链+证据+预算+兄弟)、三协议解析器(parse_model_response)、提案卡构造、响应契约常量 |
| `adapters/llm_client.py` | ModelSetup/LLMClient 协议、FakeLLMClient(剧本+计数)、OpenAICompatibleClient(仅凭证就绪时可用)、`resolve_model_setup`、提示词装载与版本哈希 |
| `configs/prompts/{ranker,analogy_editor,novel_proposal}.md` | 三协议提示词(含响应 JSON 契约与预测纪律) |
| 测试 `tests/test_atom_tool.py`、`test_analog_source.py`、`test_prediction_task.py`、`test_prediction_routes.py`、`test_prediction_workflow.py`、`test_prediction_recovery.py`、`test_identity_prediction.py`(并入)等 | §3 列表 |

修改:`domain/models.py`(EVIDENCE_KIND_NOVEL、Decision.prediction_*)、`domain/policy.py`(v43-policy-2、PREDICTION_POLICY、decide_prediction_route、stop_reason 感知 LLM 预算)、`services/reaction_finder.py`(v43-retrieval-2 卡字段;scripted 卡透传 donor 字段)、`storage/pathway_store.py`(model_ref 列+迁移+参数)、`storage/run_identity.py`(prediction 身份块+核对)、`workflow/{state,nodes,routing,graph,runner}.py`(prepare_prediction/call_model/apply_prediction 三节点、预算扩展、migrate-from)、`output/report.py`(prediction 块/孤儿调用/model_ref/汇总)、`__main__.py`(`--model off|fake|real`、`--fake-script`、`--migrate-from`)、README。

## 2. 数据契约(草案)

### PredictionTask(`v43-prediction-task-1`,只读组装,不可变落盘)
```
run_id, task_id, path_id, mode ∈ {rank_candidates, analogy_edit, novel_proposal}
root: {smiles_raw, smiles_canonical, identity}
current: {smiles_raw, smiles_canonical, identity, molecode(仅 analogy_edit), molecode_atom_ids}
ancestry: [ {position, path_id, display_name, substrate_identity, event_id, evidence_id,
             evidence_kind, evidence_source_id, product_position, depth} ]  # 根→当前,按时间序
conditions, retrieval: {task_id, payload_hash, substrate_identity}
candidates: [ {evidence_id, kind, source_id, retrieval_rank, condition_fit,
               mapping_status, products:[{position, product_smiles, product_identity, score, score_semantics}],
               asset_sources, donor_refs} ]           # rank 全量可用卡;analogy=选中卡;novel=[]
donor: {donor_ref, mapped_lhs, mapped_rhs, center_atoms, mapping_quality,
        alignment: {strategy, donor_atom→current_atom, n_aligned}, asset_file, asset_sha256, line_no}
siblings: [{path_id, substrate_identity}]              # 同父既有产物路径
budget: {depth_remaining, expansions_remaining, llm_remaining, proposals_remaining,
         max_reportable_products: 5}
discipline: {model_may_not: ["declare_exact_hit","claim_condition_compatible","claim_calibrated_probability", ...]}
prompt_versions, model: {provider, model_id}, policy_version, strategy_version
```

### 模型响应契约(提示词内声明,解析器确定性校验)
- rank_candidates: `{"decision":"select"|"hold","evidence_id":...,"order":[...],"reasons":{...},"reason":...}`;select 的 evidence_id 必须 ∈ candidates,产物不得改写。
- analogy_edit: `{"target_molecode":...,"edits":[{"op","atom"/"atom1","atom2","element"?}...],"referenced_evidence_id":...,"reason":...}`;编辑引用的原子 ID 必须存在于当前 MoleCode。
- novel_proposal: `{"products":[{"smiles":...,"note":...}] (≤5),"uncertainty":...,"reason":...}`;全部标 novel_proposal。

解析失败/超时/空响应/非法证据 ID → 显式 parse 结果(ok=false + error_kind),计入重试上限。

### 检索卡 v2 新增字段
`donor_refs: [{record_id, index, asset_file, asset_sha256, line_no, mapping_quality, mapped_lhs, mapped_rhs, center_atoms}]`、`mapping_status: resolved|ambiguous|unavailable`、`mapping_reason`。v1 卡读取:字段缺省 → unavailable。

## 3. 路由判定(decide_prediction_route,纯函数)

```
输入: decision.outcome, evidence cards(+mapping_status), policy
1. outcome=commit_recorded            → 不进模型(唯一 recorded 直通)
2. usable_recorded ≥ 2                → rank_candidates
3. 存在 analog 卡 mapping_status=resolved(且对齐成功)
                                      → analogy_edit(取 retrieval_rank 最高者)
4. 仅规则/类比但映射 unavailable/ambiguous
   → policy.allow_novel_on_mapping_failure ? novel_proposal : hold(awaiting_prediction)
5. outcome=dead_end(无可用证据)
   → policy.allow_novel_on_no_evidence ? novel_proposal : dead_end
预算: llm_remaining≤0 或 proposals_remaining≤0 → 不进模型(停留原状态)
```
默认 policy(`v43-predpol-1`):max_candidates_for_ranking=8、max_reportable=5、
allow_novel_on_mapping_failure=true、allow_novel_on_no_evidence=true、
max_parse_retries=2、max_llm_calls=max_expansions+2、max_proposals=max_expansions。

## 4. 图接线

```
classify_evidence → route_after_classify:
    commit_recorded → validate_products(不变)
    awaiting/dead_end 且 prediction_mode≠None(且模型已配置)
        → prepare_prediction(组装+落盘 task)
        → call_model(查同键产物→调用/重放→解析;悬空点注入 crash_after="call_model")
        → apply_prediction(选择既有卡 或 构造提案卡;写 prediction.json;model_ref)
        → validate_products → commit_pathway(model_ref 入账)
    否则 → mark_awaiting_prediction / mark_dead_end(第一阶段语义原样)
模型未配置(mode=off):与第一阶段完全一致,明确停 awaiting_prediction/dead_end。
```
State 新增:`prediction_mode, prediction_task_id, prediction_response_ref, predicted_evidence_id, prediction_error`;Budget 新增 `used_llm_calls/max_llm_calls/used_proposals/max_proposals`(持久事实源:used_llm_calls=已落盘 prediction_call.*.json 数;used_proposals=账本中 kind=novel_proposal 事件数)。

## 5. 测试清单(全部无凭证可跑)

1. test_atom_tool:往返(手性/电荷/芳香/多组分/断键成键编辑)、有损拒绝(同位素等,以实测为准)、编辑引用不存在原子/键 → 拒因、vendor 哈希自检。
2. test_analog_source:真实 analog corpus 按 record_id 找回(mapped_lhs/rhs/中心/质量/文件/SHA/行号)、无此 ID → unavailable、产物→记录反查、对齐成功与失败、corpus_v1 未映射记录 → mapping_unavailable 不编造。
3. test_prediction_task:S→S11→S211 两步祖先链逐级证据入任务;两条来路同分子 → 两任务不串线(不同 task_id/ancestry/path_id);schema 与纪律块。
4. test_prediction_routes:§3 判定逐分支 + 唯一 recorded 不进模型 + 预算归零不进模型。
5. test_prediction_workflow:e2e 假模型——竞争裁决(未选候选与理由全留)、类比编辑(可核对映射+MoleCode 往返)、缺映射不得假成功、无证据提案(≤5、坏产物逐个拒因不污染账本)、解析失败/非法证据 ID 显式结果+重试上限、价态/重复兄弟/循环/预算/深度拒因。
6. test_prediction_recovery(子进程):响应落盘后杀 → 不重复调用不重复事件;请求已发响应未落盘(悬空)→ 孤儿卡可审计+重试恰好一次新调用;身份含 prediction 块,漂移即拒;LLM 预算耗尽停机。
7. 旧 run:第一阶段式 run 的 resume → IdentityMismatch;`--migrate-from` → 新 run 成功且旧目录逐字节未动。
8. 检索卡 v1→v2 兼容读取回归。
9. 真实资产烟测(slow):catechol 假模型 rank_candidates 全链 + 逐卡哈希核对;真实提供者无凭证 → 结构化 unavailable(如实标未实测)。

## 6. 顺序与门槛

1) vendor+AtomTool(先跑 test_atom_tool)→ 2) analog_source+检索卡 v2(跑 finder 回归+新测)→ 3) prediction.py+llm_client+提示词 → 4) policy/存储/工作流接线 → 5) 验收测试+全量 → 6) 烟测+报告+README。
每步跑相关子集;最后 `OMP_NUM_THREADS=1 PYTHONPATH=src python -m pytest -q` 全量(基线 105 必须全绿)。
