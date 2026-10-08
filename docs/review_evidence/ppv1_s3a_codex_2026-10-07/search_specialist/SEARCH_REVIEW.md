# S3a 搜索持久底座专项独立复核

基线/实际 HEAD：9b78f4279cc6fa50b3b51c31a5c8e07abbeda207，父 00e509a974b40a7c9779fcd35e53b16637a13d60。仅合成 CCO→CC=O、隔离 src/vendor/pyproject 和 s3a_worker，depending43 Python，bytecode off。未跑 PPV1/G01/基线全套；工程专项承担。未访问真实金标、题面、封存逐题 run、dependingv4 或外部模型。

## 入口矩阵与结论

| 本批契约 | 公共入口 | 独立观察 | 裁定建议 |
|---|---|---|---|
| action/事件冻结身份 | enqueue→claim→submit_action_event；B3 write_bundle→recover | 直接提交四种外身份均拒；同一有效事件经 artifact 恢复四种均被消费并将原 action 标 done | P1：恢复没有绑定回当前 action，实际跨 run/parent/context/hypothesis 消费 |
| 首次完成/提交事实一致 | complete_action→done/consume/commit | 不存在 event_id 或另父有效事件均先落 done/consume/commit；以后 recover 才 H08 拒 | P1，与提交权威消费同组：校验不能延至下一次恢复 |
| B4 完整权威 | 已经 submit 的 action→新连接 recover | 事件 payload 损坏、预算预约全删、attempt 全删三案仍 done 补账；损坏事件普通 writer replay 当场 Ppv1LedgerCorrupt | P1：不能以正确身份列代替完整事件/搜索权威；事件部分与继承专项同组 |
| 预约 consume/release | submit_action_event→defer_action | 事件已提交后 defer 将 total/alternative/attempt 预约全部释放，已执行预算 used=0、事件保持 | P1：已执行事实不能按未执行挂起退额度 |
| 停止与未探索集合 | claim 后 stop_report | 默认预算有余，唯一 claimed action 被漏计，primary=exhausted_search，unexplored 各集合全 0 | P1：H05 对仍进行的动作不应宣称搜索耗尽 |
| attempt/reopen 计数 | 同假设不同 revision 新 action→claim→failed complete | max_reopens=0；调用不填 reopen_of，3 个 semantic attempts 成功、reopens 无记录 | 附 P2/条件：基础层允许绕过 reopen 标签已证；新信息 trigger 的生产语义属于 S3b，不凭调用没给证据就断言所有三个应算 reopen，需明确本批 trusted-caller 边界；不得交付书写已强制覆盖所有重开 |
| B1/B2/B3/B4合法正控 | 各 os._exit 子进程→新连接 recover | 四个分别通过；B1沿原 attempt/3预约续跑；B2不默发、显式retry另请求、网络0；B3/B4仅1事件+1commit/3预约，二次恢复无新增 | 已交付的合法硬杀恢复路径保持 |
| H06 并发 | 2进程 ready/GO 同 action claim | 一胜一 SearchClaimError(already_claimed)，1 attempt/3预约/0request/0event | 合法并发基本口径成立；不证明全部恶意/损坏消费入口 |

不是化学机制/科学性能结论，也未要求提前实现 S3b。真实请求协议的同键载荷/claim 验证由 root 独立审，本专项不重复。

## 具体代码与闭合验收

1. **B3**：search.py:1536–1575 直接 `store.submit_event`；:1622 `_verify_bundle_identity` 仅 bundle 自身 action/attempt 引用和 event_id 自洽，不把 event run/parent/context/hypothesis 与 action 冻结身份核对，也不核 envelope/task 与 payload.task/current action.task 的完整绑定。正常 submit_action_event:1086 调 `_verify_event_frozen_to_action`，恢复未复用。四案所有 payload 与 artifact hash 都合法，未篡改 hash；恢复实际 0→1 event，0→1 commit，原 action claimed→done。最少修复：所有输出首次消费及恢复走同源 action+attempt+task+事件身份校验，先拒零写入；合法 B3保持1事件，二次恢复不重复。
2. **首次 complete 与 B4**：complete_action:1170–1267 未先核 `event_id` 所指事件存在/与冻结 action 一致/内容及必要关联完整；recover 的 B4 find_event 分支直接 complete，_verify_commit_event:1595 只读身份列。最少修复：complete_event / 幂等 done / B4 恢复共用完整权威消费；预约/attempt 应按 action 的必需 refs 核存在、归属、版本/状态/额度，不可 UPDATE 0行仍成功；坏资料保全拒且零写入。不能猜补 event/缺预算行/attempt，也不能以 future replay 能拒当首次已闭合。
3. **defer**：:1269–1313 无“未执行”可核验前提，release 所有 reserved refs。最少修复：已提交事件/已发出请求/真实完成执行的 action 不能走未执行 release；按已登记计数规则 consumed/failed/pending恢复，保留原因；未执行正控继续 release。不应从 action claimed 直接推定没执行。
4. **H05**：stop_report:1360–1422 仅 pending/deferred/blocked/requests，claimed 不进入终止前提或 unexplored。最少修复：inflight claimed/未关闭attempt与实际持久操作状态可见；执行仍进行时 primary=None（或版本登记真实等待状态），不能 exhausted_search；空run、done完成run、deferred、悬空请求和资源适用零预算正控保持。

## 执行计数/日志

- `probe.py`：16 独立 case，全部观测断言成立。其中四个合法对照：B3、complete、B4、未执行 defer。其他12是已观察缺口或上表明确条件项，不是12个新化学漏洞。完整输入/事件/提交载荷/rows前后/返回异常在 `observations.json` 和 `probe.stdout.jsonl`。
- `crash_concurrency_as_executed.py`：B1/B2/B3/B4 + H06 共5个case、6子进程，4个强制 os._exit exit1，barrier胜方exit0、败方exit3。实际 args/stdout/stderr/cwd/exit完整在 `crash_commands.json`，载荷/账表/恢复/前后在 `crash_observations.json`、`crash.stdout.jsonl`。
- S3b 未交付队列、trigger 语义、生产 caller、中心工具链，不在上述 P1 追加功能门。

## 审核夹具准备修正（不得隐去）

第一次 probe：用异常别名文字 `LedgerCorrupt` 写类型名断言，实际异常类为 `Ppv1LedgerCorrupt`，故运行在 B4损坏event案的最后断言早停；原 stdout 已完成9行、后面未执行，不称16过。以另一个全新 generated_run2，仅更正断言类名字后完整16案通过；源码/输入规则未改。原 script/stdout/stderr 保留 `probe_attempt1.*`。

硬杀控制器首次原体遗漏父进程 GO 门写步骤；4硬杀分案已经全部执行且通过，两个并发 worker 已写好 ready 等待。父侧续接只在两个ready均存在后写一次GO，成功完成H06。真实续接载荷记录 `barrier_external_release.json`。`crash_concurrency_as_executed.py` 是原执行体；新 `crash_concurrency.py` 将该同一步骤内联为便携复现，未冒称新体另跑了四崩溃。没有靠顺序调用或随机睡眠代替 barrier，同步仍由双ready+GO保证。

`input_hashes.json` 锁定实际仓源；所有执行只写隔离临时 generated 数据，不会把 SQLite、完整源码或vendor复制到永久证据附件。归档保存脚本+日志+输入hash，可由新tmp取同源复现。
