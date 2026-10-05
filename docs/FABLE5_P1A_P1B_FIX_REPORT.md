# fable5 P1a + P1b 修复报告（2026-09-29）

> 任务：`docs/TASK_V43_HIT60_PARALLEL_FABLE5_P1.md` §1-§2。
> 评审原文：`docs/FABLE5_REVIEW_RESPONSE.md` §3.1[问题2]、§5.1[缺失]、§7-1、§7-2。
> 纪律：零 LLM 调用、不碰远端、不 git commit（改动留工作树）；不动既有未提交改动
> （docs/*、reports/*、scripts/ec298_* 等）；并行代理文件
> （`services/atom_tool.py`、`domain/policy.py`、`domain/models.py`、
> `services/donor_applicability.py` 及其测试）未触碰。

## 一、评审原文摘录

### §3.1 并发与容错 → 问题 [P2]（任务书列为 P1a）

> **问题 [P2] FileRateGate 跨进程持久化竞态**
> `src/pathway_v43/adapters/rate_gate.py` 共享闸门文件，40 worker 并发读写
> `peak_in_flight` / `issued` 计数，未见互斥锁（flock）或原子操作证据。虽 Phase D 复测
> "闸门全程未停止"（`docs/EC298_PHASE_D_RETEST_REPORT.md:110`），但高并发下存在丢失更新风险。
> 建议：在 `FileRateGate._increment_issued` 实现 `fcntl.flock` 文件锁 + 读-改-写原子段，
> 或改用 SQLite 计数表。
>
> （§7-1：FileRateGate 跨进程竞态（`src/pathway_v43/adapters/rate_gate.py`）：加 `fcntl.flock`
> 或改 SQLite 计数表。）

### §5.1 Schema 显式性与校验 → 缺失 [P1]（任务书列为 P1b）

> 缺失 [P1]：检索结果无 schema 版本字段。`services/reaction_finder.py` 返回证据卡字典未见
> `schema_version`。若检索实现变更字段结构，下游无法区分旧新格式。
> 建议：返回值加 `{"schema_version": "v43-evidence-card-1", "cards": [...]}`，任务书组装时校验版本兼容性。
>
> （§7-2：检索结果无 schema 版本（`src/pathway_v43/services/reaction_finder.py`）：加 `v43-evidence-card-1`。）

## 二、核查结论（先于修复）

两条评审意见对照 HEAD 均已部分过时，如实登记后按任务书补齐缺口：

1. **P1a**：`FileRateGate._locked()`（伴生锁文件 `gate.lock` + `fcntl.flock(LOCK_EX)`）自
   仓库初始提交起已覆盖全部读-改-写段（acquire / record_response / snapshot /
   _init_state），评审所称 `_increment_issued` 方法在 HEAD 不存在。**真实缺口有二**：
   (a) 无任何多进程并发测试证明不丢更新（评审"未见证据"成立的部分）；
   (b) `_save` 以 `seek/write/truncate` 直写原文件——进程在写入中途被 SIGKILL 会留下
   半截 JSON，下一次 `_load` 判 `GateCorrupt` fail-closed，**整个批次闸门被一次崩溃砖死**
   （锁会被内核释放，但状态文件已不可读，"崩溃后继续"不成立）。
2. **P1b**：两个 finder（`EngineReactionFinder` / `ScriptedReactionFinder`）自始返回
   `schema_version: "v43-retrieval-2"`（`RETRIEVAL_SCHEMA_VERSION`，runs/ 既有产物含
   v43-retrieval-1 与 -2 两种）。**真实缺口**：全部消费端（retrieve/classify/
   prepare_prediction/validate/adjudicate/commit 与任务组装）**都不校验该字段**，
   未知版本会被按旧结构静默解析——正是评审指出的"下游无法区分旧新格式"。

## 三、改动清单（文件:行号，工作树 diff）

### P1a｜`src/pathway_v43/adapters/rate_gate.py`

| 位置 | 改动 |
|---|---|
| :24-34（模块 docstring） | 登记 flock 临界区与原子落盘语义（fable5 §3.1/§7-1） |
| :27（import） | 新增 `import os` |
| :111-121 `_init_state` | 空文件初始化改走 `_save`（原子路径），不再 `f.write+truncate` 直写 |
| :175-188 `_save(state)` | **写机制改为临时文件 `gate.json.tmp` 写全量 + `os.replace` 原子换入**（仍在 `_locked()` flock 临界区内调用）；旧签名 `_save(f, state)` 弃用文件句柄直写 |
| :237 / :284（acquire / record_response） | 调用点适配新签名（`self._save(state)`），逻辑零改动 |

flock 读-改-写临界区本身已存在，未改动其结构；`_save` 的固定临时文件名在锁内独占使用，
若未来有人在锁外调用会因并发覆盖 **响亮报错**（实验验证：去锁后 8 进程压测立即
`FileNotFoundError`，而非静默丢更新）。

### P1a｜`tests/test_rate_gate.py`（追加 :443-613）

| 用例 | 断言 |
|---|---|
| :509 `test_gate_multiprocess_no_lost_updates` | 8 子进程 × 25 次 acquire 纯竞争读-改-写：`total_requests` / `in_flight` / `peak_in_flight` / `len(request_starts)` 四项**精确等于 200**，各进程自报数齐全 |
| :539 `test_gate_lock_released_after_holder_killed` | 子进程持 `_locked()` 临界区长睡 → SIGKILL → 父进程 `FileRateGate()` 构造与 `acquire()` 立即成功（flock 内核自动释放），计数未被破坏 |
| :569 `test_gate_survives_sigkill_during_writes` | 6 worker 循环 acquire+record_response，0.4s 后 SIGKILL 其中 3 个（任意时刻，含落盘中途）：`snapshot()` 不抛 `GateCorrupt`（状态文件必须仍是合法 JSON——原子 replace 的回归锚点）、幸存者完成数全额入账、在途泄漏 ≤ 被杀数、批次继续可用 |

**测试有牙验证**：在 /tmp 副本中剥除 `fcntl.flock` 后跑同型 8 进程 × 25 并发，
`total_requests` 崩到 28/200 并出现 tmp 冲突报错——并发测试确能捕获互斥缺失。

### P1b｜`src/pathway_v43/services/reaction_finder.py`（:36-73 新增）

| 位置 | 改动 |
|---|---|
| :36 `SUPPORTED_RETRIEVAL_SCHEMA_VERSIONS` | 读取端接受的历史版本元组 `("v43-retrieval-1", "v43-retrieval-2")`（runs/ 实测两种都存在） |
| :39 `RetrievalSchemaError(RuntimeError)` | 未知版本的显式异常（fail-closed），消息点名未知版本与支持集，`detail` 携带 `schema_version`/`origin` |
| :56 `validate_retrieval_payload(payload, *, origin)` | 消费端统一校验入口：已知版本原样返回（只校验不改写）；**缺失字段按 legacy 容忍**（早期产物与手工夹具）；未知版本抛 `RetrievalSchemaError`；非 dict 拒绝 |

**不采用评审建议的 `v43-evidence-card-1` 新名字**：实际返回结构自始以
`schema_version: "v43-retrieval-2"` 版本化整个 envelope（键名 `evidences` 而非 `cards`），
任务书明确"以实际返回结构为准做最小改动"。改名/换键会改变全部既有落盘产物的
payload 哈希与 resume 身份，违背"旧产物读取不受影响"的兼容约束；常量命名风格与
`PREDICTION_TASK_SCHEMA_VERSION` 等既有版本常量一致。`prompt_versions` / run identity
机制未动。

### P1b｜消费端接线（未知版本 fail-closed，缺失字段 legacy 容忍）

| 文件:行号 | 接线点 |
|---|---|
| `src/pathway_v43/workflow/nodes.py:56-59` | 导入 `validate_retrieval_payload` |
| `nodes.py:246`（retrieve_reactions） | **活调用返回强制校验**（origin=finder_live）：未知版本在落盘前报错，不产生不可辨格式的产物 |
| `nodes.py:269`（classify_evidence） | 读取持久检索产物后校验（origin=classify_evidence） |
| `nodes.py:380`（prepare_prediction） | 任务组装入口校验（origin=prepare_prediction） |
| `nodes.py:893`（validate_products） | 验证节点读后校验（origin=validate_products） |
| `nodes.py:1084 / :1177`（adjudicate_candidates / commit_pathway） | 裁决与提交读后校验（origin=adjudication） |
| `src/pathway_v43/services/prediction.py:35, :172`（build_prediction_task） | 任务组装双保险：版本校验先于任何素材组装（评审点名的"任务书组装时校验"） |

范围界定：`output/report.py`、`output/score_report.py` 等旧 run 报告读取器**不加**报错校验
（它们本就以 `.get(...)` 容忍缺字段，是 legacy 产物读取路径的一部分）；fail-closed 落在
活工作流消费链与任务组装，与任务书"只在活调用返回上强制校验"一致。

### P1b｜`tests/test_retrieval_schema_version.py`（新建，10 用例）

| 用例 | 覆盖 |
|---|---|
| validator 单元 ×4 | 已知版本（v1/v2）放行；未知版本 fail-closed（消息点名版本+支持集+origin）；缺失字段 legacy 放行；非 dict 拒绝 |
| :77 finder envelope | 两个 finder 返回 `schema_version == RETRIEVAL_SCHEMA_VERSION == "v43-retrieval-2"` |
| :91 retrieve fail-closed | 未知版本 → `RetrievalSchemaError` 经 start_run 透传，`retrieval.json` **未落盘** |
| :101 / :109 全链兼容 | 无版本字段（legacy）与 v43-retrieval-1 的 envelope 分别端到端跑通（classify→validate→adjudicate→commit），stop_reason=completed、事件入账 1 条 |
| :119 / :137 任务组装 | 未知版本在触碰任何素材前抛错（store=None 未被使用即失败）；legacy/v1/v2 三种 payload 在真实最小 store 上照常组装出 `v43-prediction-task-3` 任务书 |

## 四、兼容性说明

### 闸门文件格式（P1a）

**格式零变更**：`gate.json` 仍是同一 JSON 结构（`schema: "v43-rate-gate-1"`，全部键名与
语义不变），`gate.lock` 伴生锁机制不变。唯一变化是**写机制**（临时文件 + `os.replace`
原子换入），对读方完全透明。既有批次根的 gate 文件可直接读、resume 不受影响
（`_load` 未改动；`in_flight/max_in_flight/peak_in_flight` 的缺省补 0 兼容逻辑原样保留）。
行为差异仅一处：进程在写入中途被杀不再可能留下半截 JSON（旧实现会 → GateCorrupt 砖死整批）。

### 旧 run 产物读取（P1b）

- **落盘产物读取路径全部保持可用**：runs/ 实测存在 `v43-retrieval-1`（1 个）与
  `v43-retrieval-2`（3 个）检索产物，两者都在 `SUPPORTED_RETRIEVAL_SCHEMA_VERSIONS` 内，
  并有 v1 envelope 端到端跑通的测试钉住；
- 缺失 `schema_version` 字段的更早期形状按 legacy 容忍继续解析（也有端到端测试钉住），
  因此无需冒险收紧——现状已满足"必须继续可用"，未更严格是**有意选择**；
- 唯一新失败模式：**存在但未知**的版本字符串 → `RetrievalSchemaError`。这正是评审要的
  "下游能区分旧新格式"能力：未来 bump 到 v43-retrieval-3 时旧代码读新产物会显式报错，
  而不是静默按 v2 解析。

## 五、测试清单与结果

| 套件 | 结果 |
|---|---|
| 基线（改动前，conda `depending43`） | 456 passed（另 1 例 `test_batch_dev` 失败为并行代理在途编辑所致，单独重跑通过，与本任务无关） |
| `tests/test_rate_gate.py`（含新增 3 例，重复 3 次验证稳定性） | 23 passed |
| `tests/test_retrieval_schema_version.py`（新建 10 例） | 10 passed |
| **全仓 `tests/`（最终）** | **480 passed, 0 failed**（456 基线 + 本任务 13 例新增 + 并行代理新增 11 例） |

行为等价性：既有跨进程 RPM 滑窗/全局停止/预算/先发后完（in_flight）用例全部原样通过；
既有检索消费链（workflow/prediction/finder/adjudication 相关 12 个测试文件）全部原样通过。

## 六、未尽事项

- `_save` 未加 `fsync`（进程崩溃由 replace 原子性覆盖；整机断电可能丢最后一次计数但不会
  损坏文件——与旧实现风险相同，热路径每次 acquire 都落盘，加 fsync 代价不成比例）；
- 评审建议名 `v43-evidence-card-1` 未采用（理由见三.P1b；若将来统一改名需连迁移一起做）；
- `output/*` 报告读取器维持宽容读取（旧产物报告路径），未纳入 fail-closed 范围（有意）。
