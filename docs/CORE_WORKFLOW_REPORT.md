# v4.3 核心工作流实施报告（TASK_V43_CORE_WORKFLOW）

> 日期：2026-09-24。基座：已验收的资产接线（TASK_ASSET_WIRING，37 项测试 + 21/21 清单），
> 本轮在其上实现可运行、可持久化、可恢复的确定性 v4.3 主干。全程零 LLM。

## 1. 交付文件

| 层 | 文件 | 内容 |
|---|---|---|
| domain | `src/pathway_v43/domain/identity.py` | cn 身份（电荷归一化+立体盲，纯 RDKit，镜像 v3 `_cn_identity`/v4 `cn_identity` 口径） |
| domain | `domain/models.py` | Compound / ReactionEvent / PathInstance / Evidence / Decision 版本化契约；路径状态全集；稳定 ID 与内容哈希 |
| domain | `domain/pathway.py` | 祖先链、路径内循环判定、展示名（S1/S11/S211，仅展示用） |
| domain | `domain/policy.py` | 证据分级与选择策略纯函数（STRATEGY_VERSION=v43-policy-1） |
| storage | `storage/pathway_store.py` | SQLite 账本：compounds / reaction_events / event_products / path_instances / frontier（status）/ graph_revision；幂等提交 + 同键冲突 + 单事务 |
| storage | `storage/artifact_store.py` | results/<task_id> 不可变 JSON：临时文件+os.replace 原子写，同键同内容幂等、同键不同内容 ArtifactConflict |
| storage | `storage/run_identity.py` | 代码（src 逐文件 SHA）/资产/策略/依赖身份；resume 核对；统一检索资产身份构造器 |
| services | `services/reaction_finder.py` | ReactionFinder 协议；EngineReactionFinder（真实引擎）；ScriptedReactionFinder（夹具/恢复测试） |
| validation | `validation/gates.py` | SMILES/价态、同一步兄弟去重、路径内循环、方向/来源、映射显式声明、深度/预算 |
| workflow | `workflow/state.py` `graph.py` `nodes.py` `routing.py` `runner.py` | 小型 TypedDict State、StateGraph 装配、幂等节点、条件路由、run/resume 入口（含身份核对与崩溃注入） |
| output | `output/report.py` | report/pathway.json（派生视图，确定性重建）与 inspect 摘要 |
| CLI | `__main__.py` | run / resume / inspect（保留 checkenv / probe） |
| 测试 | `tests/test_domain_*.py` `test_pathway_store.py` `test_storage_contracts.py` `test_validation_gates.py` `test_workflow_scenarios.py` `test_workflow_recovery.py` `test_finder_real.py` `test_cli_workflow.py` + `tests/wf_helpers.py` `tests/recovery_driver.py` | 下方 §5 |

schema 版本：domain `v43-domain-1`、store `v43-store-1`、artifact `v43-artifact-1`、
identity `v43-identity-1`、retrieval `v43-retrieval-1`、report `v43-report-1`、策略 `v43-policy-1`。

## 2. 环境与依赖（实际安装并记录）

- 解释器：`/Users/cc/miniconda3/envs/depending43/bin/python`（Python 3.11.16，macOS arm64）。
- 本包已 `pip install -e . --no-build-isolation` 装入该环境（editable），`python -m pathway_v43` 可直接运行。
- 依赖版本：rdkit 2026.03.6 / lightgbm 4.7.0 / numpy 2.4.6 / **langgraph 1.2.12 /
  langgraph-checkpoint 4.2.0 / langgraph-checkpoint-sqlite 3.1.1**（aiosqlite 0.22.1，
  langchain-core 1.6.4，均为环境预装；pyproject 已声明 langgraph>=1.2,<2 与
  langgraph-checkpoint-sqlite>=3.1,<4）。pytest 9.1.1。
- LangGraph API 按安装版实测：`StateGraph`/`START`/`END`、`SqliteSaver(sqlite3.Connection)`
  （`from_conn_string` 为 contextmanager，长驻场景直接传连接）、每节点落 checkpoint、
  完成后 `invoke(None, cfg)` 不重放节点、`get_state(cfg)` 可取恢复前状态。

## 3. 数据流与路由（实际实现）

```text
START → normalize_input（可解析/价态门禁；根路径入账；失败→export，stop_reason=invalid_input）
      → select_frontier（depth≥上限先标 depth_limit；预算未尽按 seq 选一条）
      → retrieve_reactions（task_id 幂等：已有产物直接复用，不重新检索；否则检索+落盘；
        used_expansions 以已落盘检索产物数为准 —— 持久事实源，重放不丢计数）
      → classify_evidence（策略纯函数；裁决与全部候选持久化）
          ├─ 唯一可接受 recorded → validate_products（门禁逐产物）→ commit_pathway（单事务提交事件+产物+路径，宽度内 frontier/其余 deferred）
          ├─ 竞争 recorded 或仅规则/类比 → mark_awaiting_prediction
          └─ 无可用证据（无证据 / recorded 但条件冲突） → mark_dead_end
      → select_frontier（循环）→ export_results（stop_reason + report/pathway.json）→ END
```

- recorded_reaction 只授予 eawag lookup 的同规范底物精确键命中（`donor_exact_match`、
  方向=donor→product、可追溯 reaction ID）；**同一反应 ID 的多产物聚合为一张证据卡**，
  不同反应 ID 为竞争反应；条件缺失一律 `unknown`，原子映射一律 `unavailable`（资产无此数据）。
- 引擎 merged 池顺序 1..N 为 retrieval_rank；与 lookup 产物同分子被引擎去重的预测边
  追加编号并挂牌 `deduped_from_merged_pool`，不冒充池内排名。
- 决策不删候选：awaiting/dead_end 路径的 `status_reason` 与 decision artifact 的
  `considered`（逐卡 tier/note）完整保留。
- 展示名约定：根=S1，深度 d≥1 的路径=`S{d}`+完整位次链（S11、S12、S211、S221…），
  仅作展示；内部引用一律稳定 ID。

## 4. 真实烟测（任务书 §3 命令）

```sh
python -m pathway_v43 run --smiles 'Oc1ccccc1O' --run-id v43-smoke --max-depth 2 --max-expansions 3
python -m pathway_v43 inspect --run-id v43-smoke
python -m pathway_v43 resume --run-id v43-smoke
( cd assets && shasum -a 256 -c MANIFEST.sha256 )   # 21/21 OK
```

实际结果（runs/v43-smoke/，可直接查看 `runs/v43-smoke/report/pathway.json`）：

- `run`：stop_reason=**awaiting_prediction**（任务书预期口径）。根路径 S1 检索得
  **101 张证据卡**：3 条 recorded（`bt0254#r0601`、`bt0008#r0307`、
  `EAWAG-SOIL:97c2b761…#aa547ff7…`，三条竞争，不按分数自动淘汰）+ envipath/uspto
  规则 + 语料检索类比；**每张卡带实际来源文件与 SHA256**（recorded 卡指向
  `v3_reactions/library/library_full.jsonl`）；未提交任何反应事件；
  budget used_expansions=1；报告含待预测路径的 top-5 候选（rank 1-5，前 3 为 recorded）。
- `inspect`：status=awaiting_prediction（区别于 completed/budget_exhausted/abnormal_stop）。
- `resume`：已完成 run 幂等恢复，counts 与 graph_revision 不变（resumed=true）。
- 重复 `run` 同 run-id → exit 2 + `RunAlreadyExists` 结构化 JSON。
- v3 引擎装载横幅已改道 stderr（适配器 init 内 redirect_stdout），**run/inspect/resume
  的 stdout 为纯净 JSON**（test_cli_workflow 有回归钉子）。

## 5. 测试与验收用例对照（任务书 §3 六组）

全量：**105 passed**（`OMP_NUM_THREADS=1 python -m pytest tests/ -q`；其中 slow 14 项
装载真实引擎/跑双臂对拍/子进程恢复实测）。原资产接线 37 项测试全部继续通过。
（首轮 98 项；review 修复后新增 7 项回归钉。）

1. **多产物有序事件**：`test_workflow_scenarios.py::test_unique_recorded_multi_product_one_event_ordered`
   ——1 事件 2 有序产物；`test_width_controls_expansion_and_marks_deferred`——宽度=1 只展开 S11，
   S12 标 deferred。
2. **汇合与循环**：`test_junction_two_routes_one_compound_full_history`——S→{P1,P2}→Q：
   4 Compound / 5 PathInstance，两条 Q 路径父链 `S1->S11->S211` 与 `S1->S12->S221`；
   `test_cycle_product_back_to_ancestor_dead_end`——产物回祖先 → in_path_cycle 拒因、不入图。
3. **证据级别**：竞争 recorded / 仅规则 / 仅类比 → awaiting_prediction 且候选全保留；
   条件冲突 recorded → dead_end（recorded_not_usable）；无证据 → dead_end（no_evidence）
   （policy 单测 + 工作流场景双覆盖）。
4. **拒因与预算**：无效 SMILES（invalid_input+error 结构化）；事件内重复产物/既有兄弟去重；
   `test_budget_exhausted_with_frontier_remaining`（frontier=2 保留不删）；`test_depth_limit_status`。
5. **幂等与恢复**（子进程真实中断，os._exit(70)）：`test_workflow_recovery.py`
   - 检索落盘后杀：恢复后真实检索计数 1→3（根未重查）、3 份检索产物、事件/路径/revision
     与无崩溃基线逐项一致；
   - 提交后杀：崩溃前 DB 已有 1 事件，恢复重放 submit_event 幂等，计数与 revision 无重复；
   - 身份漂移（篡改资产身份块）→ resume exit 2 + IdentityMismatch；
   - 无检查点残留 → resume 结构化报错（首个 checkpoint 前中断应重跑）。
   另：同键不同内容提交 → EventConflict（test_pathway_store.py）；产物同键异内容 →
   ArtifactConflict（test_storage_contracts.py）。
6. **真实引擎 integration**：`test_finder_real.py::test_real_engine_catechol_recorded_evidences`
   （3 条 recorded 卡、资产身份与清单一致、引擎顺序保留）、`test_cli_workflow.py::test_real_run_inspect_resume_smoke`
   （CLI 全链路）、`test_domain_identity.py::test_identity_parity_with_frozen_engine`
   （cn 身份与 V43Engine 逐分子对拍）。

崩溃恢复前后 DB 计数（rec2，提交后杀）：

| 计数 | 崩溃后（恢复前） | 恢复后 |
|---|---|---|
| reaction_events | 1 | 1 |
| event_products | 2 | 2 |
| path_instances | 3 | 3 |
| graph_revision | 1 | 1 |

## 6. 资产与代码身份（runs/v43-smoke/run_identity.json）

- mode=repo_assets；assets_root=本仓 assets；**manifest_sha256 =
  def94d82b65915f0ecd2377971cb082ba2b1c1464b4eb165a32d5e57e259aa34**（21 文件）；
  检索来源（v3 identity block "library"，即引擎实际环境 lookup 库）
  `v3_reactions/library/library_full.jsonl` sha256 =
  042e9e2c2afccdd83088eb0b50d75619261fb096728a17ab108da06cb54667f3。
  （更正：首轮报告误将来源写作 `eawag/donor_product.jsonl`——那是旧 P4.2 库，
  v35 资产集的 lookup 库实为 library_full.jsonl；逐卡溯源修复时发现并已全局更正。）
- v3 引擎代码：dependingv3 @ eb24c1e（main，clean）。
- 本包代码身份：src/pathway_v43 全部 .py 逐文件 SHA256 + 聚合哈希（本仓非 git 仓）；
  resume 时逐字段核对（asset_identity / v3_engine_code / code_identity /
  dependency_versions / strategy / inputs）。

## 6.5 外部 review 修复记录（2026-09-24 二轮）

外部 review 复现出 6 处问题（3×P1 + 3×P2），全部修复并加回归测试：

| # | 问题 | 修复 | 回归测试 |
|---|---|---|---|
| P1-1 | 恢复后突破展开预算：retrieve 节点复用已落盘检索产物时不补记本次展开，重放路径丢 in-memory 计数 | 预算记账改为**持久事实源**：used_expansions = 已落盘检索产物数（ArtifactStore.count_retrievals），每次 retrieve 节点重算；重放/复用/新检索三种路径计数一致 | `test_workflow_recovery.py::test_resume_budget_respects_run_identity_limit`（max_expansions=1：无崩溃与崩溃恢复都停 budget_exhausted，frontier=2，检索计数停在 1） |
| P1-2 | 前序产物被拒后，后续有效产物被按提交列表重排编号，写成 S11 且状态 rejected、未进 frontier | submit_event 尊重产物**原始位次**（prod["position"]）：路径 ID、event_products.position、展示名全部按原始位次，位次稀疏不重排 | `test_workflow_scenarios.py::test_rejected_first_product_keeps_original_position`（产物 0 循环被拒、产物 1 有效 → 事件产物 position=[1]，路径 S12 正常入 frontier 并探索） |
| P1-3 | 证据出处契约未完成：score_semantics 被统一字符串覆盖；asset_file/asset_sha256 全空，101 张卡无法逐卡追溯 | ① 预测边优先透传引擎原始 score_semantics，缺席时声明实际取数字段（`engine_pred_edge_score:edge_score` / `:tanimoto`），原始分数字段全量入 source_record；② 证据卡按类别映射到实际读取文件并就地计算 SHA：recorded→library_full.jsonl、envipath→ENVIPATH_RULES、uspto→TEMPLATES、检索→corpus_v1.jsonl | `test_finder_real.py`（FakeEngine 断言每卡 asset_file 非空、哈希与总清单一致、分类映射正确、semantics 出处正确）+ 真实引擎用例（101 卡逐卡核对）+ `test_cli_workflow.py` 真实烟测逐卡核对 |
| P2-1 | 待预测路径无 top-5 报告（只列已提交事件产物） | 报告为每条有检索产物的路径（含 awaiting/dead_end）输出 `top5_candidates`（按 retrieval_rank 前 5），summary 增 `top5_reported_paths` | `test_awaiting_path_reports_top5_candidates` + 真实烟测断言 root top5=[rank1..5，前 3 为 recorded] |
| P2-2 | 展示名违反约定：S11 的子路径被命名为 S111 | 约定为 `S{深度}{完整位次链}`：根=S1、深度 1 首子=S11、S11 首子=S211、S12 首子=S221 | `test_domain_pathway.py::test_display_name_convention` + junction 场景断言 `S1->S11->S211` / `S1->S12->S221` |
| P2-3 | 不可变产物无完整性保护：读取不核对哈希；写路径 check-then-replace 有并发覆盖窗口 | ① 读取重算 payload 哈希核对信封，不符 → `ArtifactIntegrityError`（fail-closed）；② 写入改 `os.link` 原子占位（目标存在即失败），并发写同一键只有一个成功，绝不覆盖 | `test_storage_contracts.py::test_artifact_read_detects_tampering`、`::test_artifact_concurrent_write_no_overwrite` |

修复过程中另发现并更正一处来源错标：`RECORDING_SOURCE_FILE` 原硬编码为
`eawag/donor_product.jsonl`（旧 P4.2 库），而 v35 资产集引擎实际装载的 lookup 库是
`library/library_full.jsonl`（v3 identity block "library"）。该错标曾导致
retrieval_assets 的 source_file 与 source_file_sha256 配对不一致（名字是旧库、
哈希是新库）；现统一以引擎 identity block 的实际路径为准，逐卡溯源与 run_identity
均指向 library_full.jsonl。

### 二轮复核补充修复（2026-09-24）

| # | 问题 | 修复 | 回归测试 |
|---|---|---|---|
| P2-a | recorded 卡 source_record.library 仍写死旧库名 donor_product.jsonl，与同卡 asset_file（library_full.jsonl）不一致 | 删除写死库名；source_record 改为 `library_file` / `library_sha256`，直接取自 asset_file 同源字段 | FakeEngine 用例 + 真实引擎用例 + CLI 真实烟测逐卡断言 `library_file == asset_file` 且以 library_full.jsonl 结尾 |
| P2-b | 组合来源卡（如 envipath+retrieval）只列主来源文件；p_retrieval 等成分参与评分却无对应语料文件与哈希 | 新增卡字段 `asset_sources`：解析来源串全部成分，逐个列出 `{role, asset_file, asset_sha256}`（主来源保持 asset_file/asset_sha256 首位不变） | FakeEngine 用例断言 envipath+retrieval → roles=[envipath, retrieval] 且两个文件哈希均与清单一致；真实引擎与 CLI 烟测对全部 101 卡断言 asset_sources 非空、主来源一致、逐成分哈希核对 |
| 文档 | 实施报告 §5 遗留旧展示名 S111/S121 | 更正为约定名 S211/S221 | — |

## 7. 已知限制

1. `run_identity.json` 中的策略**取值**（max_depth 等）是 run 参数，仅此文件记录，
   文件被篡改不可自检；策略/代码**变更**由 code_identity（含 STRATEGY_VERSION 与
   策略模块哈希）与 asset_identity 捕获并拒绝 resume。
2. scripted 夹具 run 的跨进程 resume 必须显式传入同一 ScriptedReactionFinder
   （测试驱动 `tests/recovery_driver.py` 如此）；CLI 对 scripted run 的 resume
   结构化拒绝（无法凭空重建脚本检索器）。
3. 引擎进程守卫语义微调：同资产身份允许 reset 后重初始化（完整重走校验+装载，
   确定性安全），**跨身份拒绝不变**。此改动使本轮真实引擎测试可与已验收的
   隔离测试共存于同一 pytest 进程；`test_asset_root_isolation.py` 全部通过。
4. 条件相容性全部 unknown、原子映射 unavailable —— 如实反映本资产集内容，
   未生成任何猜测值；condition_fit=compatible 的判定路径由策略层单测覆盖。
5. 本轮不接 LLM：awaiting_prediction 是确定性阶段的**明确终态**，不是成功预测；
   PredictionAgent / AtomTool / v3 评测格式导出属下一阶段任务。
