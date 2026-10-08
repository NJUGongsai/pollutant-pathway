# S3a-r2 权威与恢复专项独立审核

实际 HEAD `dcb7ed62bd4271cfa7bde2732dc0b4fdd0360d03`，直接父 `9b78f4279cc6fa50b3b51c31a5c8e07abbeda207`。仅 S3a 首轮报告 §4/§7 有限回修面，合成 CCO→CC=O；无科学性能结论，无 S3b/机制库/分布式 exactly-once 新门。

**裁定：S3A-01 四种事件异身份的修复已证；S3A-02 原 12×2 坏事件账、首次空/不存在/异父 event、B4 删除引用控制已修复，但完整搜索账权威仍未闭合。合法四硬杀、双独立进程 barrier、幂等和 H07/H08 保持。**

## 已证修复与合法控制

- 原 `inheritance_probe.py` 同字节隔离复跑 27 案：12 类坏事件账 × B4/done 两模式全拒 `SearchIntegrityError`，全部表保持原样；同库公共 writer 携带原输入也拒且零写。合法 B4 一次补账、done 重放无变化；raw 首提交拒且全表零变化。
- 原 `probe.py` 同字节重跑只完成合法 B3，随后 `b3_run` 在写侧身份拒处提前退出。其后内部 B3/complete/B4/defer/stop 未执行，未报通过。另一个分段脚本逐案补齐四种事件身份：write/submit 均拒且零落盘/零事件/提交/consume；把同一有效异身份 artifact 另行写入后新连接 B3 两次拒绝，全表零变、artifact 字节保全。异身份 input 参数沿用旧反例，当前 claim 冻结引用完整登记。
- 首次 complete 合法控制一次完成、第二次复用零写；空 event_id、不存在 event、另父合法 event 分案拒且零成功写。
- `crash_concurrency_as_executed.py` 实际执行的是首轮便携控制器的同字节副本（含父侧 GO 步骤）；四 worker 分别在 claim/request/bundle/submit 后 `os._exit(1)`，父新连接恢复。B1 沿旧 attempt/3 预约续跑；B2 原悬空可见且网络 0，显式 retry 新 request；B3/B4 各 event=1/commit=1，二次恢复零新增。两个独立进程双 ready 后 GO 争抢同 action，exit 0/3，一个 winner、一个 already_claimed，attempt=1、预约=3、request=0、event=0。各 worker 全 argv/cwd/exit/stdout/stderr、前后 rows 在 crash 日志。
- H07 的 hash 字节损坏、非法 JSON、未知 bundle version、错 task/attempt 绑定均明确拒并保全 artifact；H08 的缺 event、缺 commit、commit event_id 篡改均拒且全表零变。

## 同契约残余：搜索预约、attempt 和 commit 引用只验部分列

来源：`search.py:1461` `_verify_action_references` 预约仅读 run/limit/scope/subject/action/status，不验 units 或必需预约集合与额度语义；自有 action 的 scope/subject 未核（只有跨 action alternatives 特判才核）。仅拒 status=released，不拒未知 status。attempt 仅读 run/action，不核 open/recorded/failed 状态、hypothesis/task 归属。`complete_action:1840` 在完成前使用此窄校验；done/已有提交复用 `:1691/:1730/:2334` 完全未使用它。

公共链分案（`segmented_cases/<入口>__<mutation>/input_output.json`）：

| 坏事实 | first complete / B4 recover | done recover/claim/complete/submit | B1/B3 recover |
| --- | --- | --- | --- |
| 总 action 预约 units=0、未知 status、错误 scope | 都成功写 done/commit；快照 used=0、remaining=10 | 全复用成功，恢复明确 done_commit_verified，预算仍 0 | B1 明确 intact；B3 插 event/commit、done，预算 0 |
| attempt=abandoned、hypothesis/task 错绑 | 都成功 done/commit；abandoned 未改 recorded 仍宣完成 | 全复用成功、done_commit_verified | B1 明确 intact；B3 插 event/commit并 done |
| 删除预约/attempt 行 | 首次/B4 已正确拒、零写 | 四入口全复用成功；缺预约快照 used=0 | B1 正确拒；B3 先写入 event 和 states/appearances/hypothesis/projection/plan/links，再拒，event 0→1、commit 0、action claimed |
| commit.attempt_id 指不存在 attempt | — | 四入口全复用成功 | — |
| commit.run_id 异属 | — | recover 正确拒 done_without_commit；claim/complete/submit 却成功复用 | — |

对应首轮 S3A-02：首次消费与复用必须信实际必要权威记录，不能存在/两列归属即认证完整；不能延后到重放洗掉损坏，坏单 action 消费前零成功写。预约坏内容会直接让预算快照把已执行事件计为 0，用于搜索停止/继续；不是不影响验收的保守过拒。B3 缺行属于同一引用规则漏入口，不能以最终抛异常冒充首次消费前拒。

有限建议：共用完整的合法搜索引用验证，按 claimed/done/非事件 outcome 的许可状态区别，核必要记录集合、实际额度、冻结身份和引用；B3 在事件事务消费 artifact 之前核持久 action/attempt/预约，done 首用/重用也核相同必要历史。保持合法主体共享 alternatives、正常 recorded/failed 及非 expand 空 attempt，不全面拒绝合法结果。

## 同契约残余：附随 projection/plan 载荷用当前坏值自比较

来源：`search.py:1557/:1593` 从当前库取 projection/plan 原样传公共 writer。`store.py:1693–1707` 重放只把存储附随 payload 与传入 payload 比 hash；此处两者就是同一当前值。已知版本门和行存在仍在，不能证明内容正确。正常首次提交的产物范围/status 校验在 `store.py:1029/:1058/:1071`；搜索核验到的 replay 分支没有重新做这些关系。

分案将合法事件的 projection.product_ranks 指不存在 state；plan.entries 指不存在 state；plan.status 改成 invalid-status，保留正确 projection/policy version：

- first complete 与 B4 均成功写 done/commit/consume。
- done 的 recover、claim、complete、submit 四入口均成功；恢复声明 done_commit_verified。
- 每案同库公共 writer 带原正确 event/投影/计划输入重放拒 `Ppv1EventConflict/attached_payload_mismatch`，全表零写。另三案直接以坏附随输入首次正常 submit_action_event 均拒 `projection_ref_out_of_products` / `expansion_ref_out_of_products` / `invalid_expansion_status`，全表零写，证明这些坏值违反既定 writer 契约。
- 同批 event.participants=[] 六入口全正确拒且零写，已证修复保持关闭。

对应首轮 S3A-02 的“完整账权威”与 R8 公共 writer 继承；这不是新化学机制要求。有限修复需避免当前附随载荷自作原始证书，至少共用首提交的产物/状态/集合关系契约，并明确可信原始内容身份范围；不能只把更多表名列进注释。

## 已完成结果复用返回错 event 引用（零写，不是插错事件）

`search.py:1351–1354` 的 done submit 分支先核旧提交权威，随即 `created=False, event_id=event.event_id, reason=already_completed`；event_id 来自这次入参，没有返回原已完成结果的实际事件引用。

`done_result_reuse_probe.py` 两案：同 A 的合法复用正常返回 A；合法已完成 A 上传入另父的有效 B（另独立公共 store 首提交已验证 B 有效），返回 `already_completed/event_id=B`，当前 A 库无 B、commit 仍指 A，全表零变化。这不是无害忽略参数后复用 A，而是成功结果给了并非旧 outcome 的引用。对应任务书 §4.3 复用已完成结果，以及 S3A-02 成功复用引用闭合，原 S3A-01 四身份 B3 修复仍保持关闭；不把零写误报为插入错事件。

## 并发窗口：仅故障注入证据与披露精度，不自行升级阻塞

用户要求的两案位于 `supplementary_cases/TOCTOU_clean|corrupt/`。实例上的 hook 先完整执行原 `_preverify_completion`（原公共 writer replay 验证、rollback），仅在它返回后暂停并发双 barrier；未替换任何验证逻辑。此时原连接 `in_transaction=false`，另独立进程/SQLite 连接 `BEGIN IMMEDIATE → UPDATE states formal_charge=99 → COMMIT` 成功，原 complete 继续成功写 done/commit。正确 writer 携原输入重放拒 `Ppv1EventConflict/state_semantic_conflict`，零写。干净同 harness 正控成功。

因此“busy可见”不保证核验后的第二写者会 busy；本案约 7.7ms 间隙并不说明窗口只有微秒，源码无时间上界。此是主动并发坏库 SQL 故障注入，未证明合法不可变 public writer 会改 state，也未证明顺序单消费会自动交错；是否既定合同内阻塞留主审，优先上述顺序、无需并发的坏权威事实。

## 准备错误与数字解释

旧 inheritance observed 断言是修前现象断言，当前在第二案（首坏 state_charge）按设计失败；其化学/static/CX 后段未执行且不计通过。原 search observed 脚本只发一行合法 B3 后在 b3_run 写侧提前拒，四种坏身份 B3 分支靠独立分段补执行。

本审补充脚本末尾误把坏 state 重放错误限定成 `Ppv1LedgerCorrupt`，实际携原正确 states 时先报 `Ppv1EventConflict/state_semantic_conflict`；第5案已经完整写出 input/output、SQL、双进程日志、before/after，随后断言失败。原脚本与 stdout/stderr 原样保留；只读 `assert_current_capture.py` 用正确错误类型确认全部5案，不重复执行，也不把 assertion 红当行为失败。

执行计数：旧权威 27 案、硬杀/barrier 5 案、分段 120 案、补充 5 案、done结果复用 2 案。分段的捕获/修复控制检查完成并不等于正确合同全通过：其中 81 行坏记录被接受，2 行缺引用晚拒却已写事件；这些是同根入口证据行，**不是 83 个漏洞或性能数**。工程 pytest/G01 属另一专项，不在此重复执行、不与此相加。
