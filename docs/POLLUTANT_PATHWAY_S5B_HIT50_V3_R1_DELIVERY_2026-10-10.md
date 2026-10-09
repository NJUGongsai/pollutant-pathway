# PPV1 S5b HIT50 v3 回修轮交付书(S5B-V3-01 / S5B-V3-02,2026-10-10)

状态:`implementation_ready_for_review`(本轮零真实模型调用、零花费、
不 push、不启动 chain10、不改冻结判据与 scorer 匹配/排序、不回写旧批)。

依据:正链复审报告 `docs/POLLUTANT_PATHWAY_S5B_HIT50_V3_CODEX_REVIEW_
2026-10-10.md` §4 两 P1 + §8 有限回修提示词(权威);本轮只修两 P1 与
同门 P2 文案/测试搭车,不实施 V4/E 设计、S5 科学新尺子、真实评测或语料
升级。基线 HEAD `0c6e45d074d55ba14b5db7926cebb3f4141013a7`(直接父
`35727eb` 的 v3 交付)。

## 一、S5B-V3-01:域身份严格校验(修法与入口矩阵)

**修法一句话**:新增共用判据 `evaluation.resolve_data_scope`(显式
空/None/bool/数值/未知串 ⇒ 结构化拒;完全缺省 ⇒ 既有默认语义保留并
机读披露归一来源),评测首消费(`validate_evaluation_input`/
`evaluate_scientific`)与判分首消费(`score_s5b_batch`,包装
`S5bScoringError kind=s5b_data_scope_invalid`)同源消费,废除
`get(...) or synthetic_rule_level` 的 truthiness 洗白;同批补齐 §9-4
独立 basis 门的 shape 全集核。

入口矩阵(输入 → 行为 → 首消费 → 写入/传输边界):

| 入口 | 输入 | 行为 | 首消费 | 写入/边界 |
|---|---|---|---|---|
| `validate_evaluation_input` | `evaluation_input["data_scope"]` 显式提供 | 非 `DATA_SCOPES` 字符串(空/null/bool/数值/列表/未知串/大小写空白变体)⇒ `EvaluationContractError(kind=data_scope_invalid)`;完全缺省 ⇒ 保留既有 synthetic_rule_level 默认 | 本函数(评测校验首消费,共用 `resolve_data_scope`) | 零写入(拒时不产任何评测产物) |
| `evaluate_scientific` | 同上(经校验后二次同源解析) | 缺省 ⇒ synthetic、显式合法值照旧走 real 门 | 与校验同判据 | 输出 `scoring_provenance.data_scope_normalized_from`(explicit / missing_field_default)机读披露;real 门/配对门判定零触碰 |
| `score_s5b_batch` | 参数 `data_scope`(缺省=签名默认 real,保留) | 显式坏值 ⇒ `S5bScoringError(kind=s5b_data_scope_invalid)` **先于任何批文件装载**;合法值照旧 | 函数入口第一条(判分首消费) | 聚合 `data_scope_provenance`(normalized_from + signature_default 登记缺省语义);拒时零 metrics 落盘 |
| CLI `s5b_cli score --data-scope` | choices={real,synthetic_rule_level} | choices 只是输入便利;**API 以 `score_s5b_batch` 门为权威**(直接 API 调用带坏值同样拒) | `score_s5b_batch` | 同上 |
| §9-4 basis 门(s5b_scoring) | `evaluate_scientific` 产物 `coverage_report.pairing.bases_by_graph` + 注册图集合 | real 档:缺 coverage/缺 pairing/缺 bases/空/非 dict/缺键/foreign 键/非字符串值/非 qid_strict ⇒ `S5bScoringError(kind=s5b_real_pairing_not_all_qid_strict, reasons 细分)`**先于逐题聚合**(先拒零 metrics);synthetic 档不受影响 | 判分入口(双保险独立复核) | detail 机读:reasons / non_qid_strict_bases / expected_graph_ids / missing_graph_ids / foreign_graph_ids / **gate_scope(门只核档位与覆盖,不核映射)** |

**不动面**:完全缺省字段的既有默认语义(evaluation=synthetic、
score=real)逐字节保留;显式 real 的 prereg 批准门、evaluation-5 real
配对禁回退门、qid 缺配 not_evaluated 与四个既有输入守卫全部保持
(正控测试在案);scorer 匹配/排序/判据零触碰。

## 二、S5B-V3-02:批级金额硬帽——发送前原子预留(修法与入口矩阵)

**修法一句话**:60 CNY 帽 + 当日价/计费口径/输入保守界/输出上限冻结为
批根机器配置 `budget_guard.json`(`s5b_cli budget` 落盘,派生
`per_attempt_bound_cny` 与 `config_sha256` 可核验),由协调者写进闸门
状态文件 `cost_guard` 块;公开实际发送链(worker → RealModelAdapter →
OpenAICompatibleClient → FileRateGate)在**每次可能付费的发送尝试
(含 HTTP retry)的 acquire 临界区内原子预留**——已知借记 settled +
未结算未知占用 unsettled + 在途预留 reserved + 单次保守上界 ≤ 帽才发,
否则 `GateCostBudgetExhausted` 结构化拒(余额不足先于传输)。

金额语义(冻结口径,`s5b-budget-guard-1`):

- **预留**:bound =(输入保守界×入价 + 输出上限×出价)/1e6;每个
  HTTP 尝试(acquire 占位)原子预留一次,reservations 逐尝试留痕;
- **结算**:响应带 usage ⇒ 按冻结价结算实际金额(预留差值退回恰一次,
  幂等;只有 total 无拆分 ⇒ 全额按较贵单价保守计);**显式 429 之外
  的一切无 usage 结局(失败/超时/401/402/403/5xx/空响应/未知)⇒ 预留
  全额转未结算借记,不释放**(可能已付);429 是提供者明示未处理未
  计费的确定性结局(沿 llm_client 既有口径"提供者不把 429 计费"),
  预留退回;
- **孤儿/崩溃**:死亡 owner 占位回收只退在途槽位,金额预留保守转
  未结算;恢复/重复结算幂等,不重退不重扣;结算后 committed 超帽 ⇒
  记 overrun(事后披露,不回滚已付事实,后续发送拒);
- **不自动升帽**:帽只在批根配置;CLI 同值幂等、改值拒;同批根
  orchestration.json 冻结副本核对,变更 ⇒ `s5b_orchestration_conflict`。

入口矩阵:

| 入口 | 输入 | 行为 | 首消费 | 写入/传输边界 |
|---|---|---|---|---|
| `s5b_cli budget` | 帽/当日价/输入保守界/输出上限 | 归一校验(normalize_cost_guard_config 单一判据)+ 派生 bound/config_sha256;同价同步写 price_snapshot.json | CLI | 落 `budget_guard.json`(机器配置,可核验);改值拒 |
| `run_s5b_batch` | `batch_manifest.provider_kind` + `budget_guard.json` | **real 批缺/坏配置 ⇒ `S5bOrchestratorError(s5b_budget_guard_missing/invalid)` 先于任何 worker 派发**;配置冻结进 orchestration.json + 闸门状态 cost_guard 块 | 发车装载(load_budget_guard 同源归一) | 零 cases/零 orchestration.json(拒时);frozen 含 budget_guard(续跑变更拒) |
| `FileRateGate.acquire` | 状态 cost_guard(冻结) | committed+bound ≤ cap 才放行;不足 ⇒ `GateCostBudgetExhausted`(不等待;先于传输) | acquire flock 临界区(原子) | 预留与占位绑定原子落盘(gate.json);拒发计数机读 |
| `FileRateGate.record_response` | usage/状态/占位 | 结算/429 退回/未知保留(见上) | 结算(幂等) | gate.json cost 账本(settled/unsettled/reserved/overrun) |
| `FileRateGate.reclaim_dead_placeholders` | 死亡 owner 占位 | 在途槽位回收;**金额预留保守保留为未结算** | 父协调者轮询 | 同上 |
| `OpenAICompatibleClient.complete` | 闸门 cost_guard | 配置坏 ⇒ `budget_config_invalid` 结构化拒(零发送);请求体注入冻结 `max_tokens`(输出上限随请求发送,提供者侧可核);显式 request_params 携带不同 max_tokens ⇒ 冲突拒(单一事实源) | complete 首步 + acquire | 零 urlopen 调用于拒;`_gate_block` 新映射 budget_cost_exhausted |
| `RealModelAdapter.identity_block` | 闸门 cost_guard | budget_guard 块(帽/价/界/输出上限/配置哈希)入 run 身份 | 身份装配 | resume 逐字段核对(金额配置变化=不同批次身份);配置坏 ⇒ 装配期拒 |
| `s5b_worker`(real 批) | 闸门 + 批根 budget_guard.json | 无闸门/无金额配置/配置哈希不一致 ⇒ 先拒(闭合绕开编排器手动起 worker 的口子;scripted 桩不经此路径) | worker 公开入口 | 失败 case 落盘留分母,零发送 |

**保持的其他门**:HTTP1490(S5B_DEFAULT_GATE_MAX_CALLS)、每题
1logical(format0/反馈轮 0,profile_policy 不变)、40 在途
(max_in_flight 语义不变)、RPM/TPM、429 有界退避、401/403/402 付费
停止——全部不动(测试 `test_other_gates_untouched_with_cost_guard`
与既有回归在案)。金额门是**新增**门,不替换上述任何门。

## 三、§4.2 合成控制清单结果(逐条;tests/test_ppv1_s5b_hit50_v3r1_cost.py)

| # | 控制 | 结果 | 测试 |
|---|---|---|---|
| 1 | 零/不足预算零发送 | ✅ cap<单次上界 ⇒ acquire 拒、urlopen 零调用、拒发计数=1 | test_zero_insufficient_budget_zero_sends |
| 2 | 恰好额度 | ✅ committed==cap 放行恰一次;第二次拒(浮点容差不误拒) | test_exact_last_budget_admitted_once |
| 3 | 已知超帽 | ✅ 实际结算超保守界 ⇒ committed>cap:overrun 机读披露、不回滚、后续发送拒 | test_known_over_cap_blocks_and_discloses_overrun |
| 4 | 双进程 barrier 抢最后额度 | ✅ 两子进程互见 marker 后同时 acquire:恰一成功一拒;committed 不超帽 | test_two_process_barrier_last_budget |
| 5 | 未知 usage | ✅ 200 无 usage ⇒ 预留全额转 unsettled(committed 计入);余额耗尽后拒 | test_unknown_usage_reservation_kept |
| 6 | 重试/崩溃恢复/幂等结算 | ✅ 6a 每次retry先预留(3 尝试=3 预留留痕;429 退回后重试可继续);6b 失败/超时全额保留;6c SIGKILL 孤儿:槽位回收+金额保留;6d 结算后回收不重扣、重复结算 no-op | test_http_retry_each_attempt_reserves_and_429_released / test_failure_and_timeout_keep_full_bound / test_crash_recovery_reclaim_keeps_money / test_settled_then_dead_owner_reclaim_no_double_count |
| 7 | 配置坏/缺先于传输拒 | ✅ 7a 闸门配置坏 ⇒ budget_config_invalid 零发送;7b real 批缺/坏 budget_guard.json ⇒ 发车先拒(零 cases/零 orchestration);7c 同批根改值 ⇒ orchestration_conflict;CLI 同值幂等/改值拒 | test_corrupt_cost_config_refuses_before_transmission / test_orchestrator_real_batch_requires_budget_config / test_orchestrator_budget_frozen_and_change_rejected / test_cli_budget_writes_machine_config |
| 8 | 公开 adapter/worker 假传输端到端 | ✅ 8a worker_main 进程内(urllib 打桩):case completed、结算=冻结价×假 usage、请求体带 max_tokens、身份块带 budget_guard;8b 预算不足:零发送、run 以 budget_limit 终态留分母、run_error 结构化披露;旁路守卫(无闸门)⇒ budget_guard_missing;8c run_s5b_batch 子进程 worker → 真客户端 → 闸门 → urllib → **localhost 假提供者(127.0.0.1,零外部网络)**:2 题完成、结算/committed/批报告 cost_guard 账本全对 | test_worker_real_client_fake_transport_end_to_end / test_worker_insufficient_budget_stays_in_denominator / test_orchestrator_subprocess_real_chain_end_to_end |
| 9 | 其他门/身份 | ✅ max_calls 门独立生效;请求体冻结输出上限+冲突拒;身份块 budget_guard(无密钥) | test_other_gates_untouched_with_cost_guard / test_request_body_carries_frozen_output_cap / test_identity_block_includes_budget_guard |

口径声明:全部合成假传输(urllib 打桩或 127.0.0.1 假提供者),零真实
模型/零外部网络/零花费;不冒充真实账单对齐或完整 PPV1 真实批生命周期。

## 四、红绿分类(当前 + 直接父同字节;分类表定义)

**分类表定义**(本轮交付统一口径;同时订正 v3 轮"17 红全行为"的
旧表述——复审已改为 13红+4绿+1collection=10 行为+1 拒因 kind 差异+
2 字段缺失,本轮沿用同一分类法):

- **行为红**:父版本无该行为/放行坏输入,修后行为改变(如显式坏
  data_scope 被洗白放行、坏 shape basis 被接受、金额无预留照发);
- **kind 差异红**:父/子都拒但拒因 kind 不同(v3 轮 1 例;本轮无——
  新 kind 均为父版本"不拒"转为子版本新拒,归行为红);
- **字段红**:断言新增机读字段(detail 字段/聚合 provenance)⇒ 父上
  KeyError/字段缺席,不属行为差异;
- **collection 红**:测试模块导入父版本不存在的 API ⇒ 模块收集失败,
  该文件用例未执行(不计为已执行红);
- **绿(保持控制)**:断言新旧一致的不变量(既有门正控、合成档聚合、
  入口锁、trigger_equivalence 等),父/子都应通过。

**本轮数字**(3 个测试文件 = 2 新 + wv6 升级,在父 0c6e45d 隔离
worktree 同字节运行):

- 父:**50 failed / 6 passed / 1 collection error**(cost 文件 19 用例
  未执行——`GateCostBudgetExhausted` 等父版本 API 缺席);
- 50 红 = **47 行为 + 3 字段**(字段:data_scope_provenance、
  data_scope_normalized_from、wv6 gate_scope;0 kind 差异);
- 6 绿 = 保持控制(real 门正控、synthetic 档聚合 ×2、真实链披露、
  入口锁(升级后定义域 src+scripts 下父上仍唯一调用)、
  trigger_equivalence);
- 子(当前):同 3 文件 75/75 全绿;`--continue-on-collection-errors`
  运行;逐 nodeid 分类见证据
  `/tmp/s5b_v3r1_impl/parent_redgreen/classification.json`。

**支持范围**:父红绿只证明"新测试断言的是本轮新增行为/字段,且父
版本确实无此行为";不证明真实 298 可达性、不证明评测器权威链映射
正确(见 §七/§八)。

## 五、回归数字(当前 HEAD,depending43 `-B` + `-p no:cacheprovider`)

| 组 | 命令/口径 | 结果 |
|---|---|---|
| 定向(13 文件) | s5b 全家(wv1/wv2/wv3/wv6 + v3r1 scope/cost + runtime/pairing/rework_l01/hit50 w1/w23456)+ test_rate_gate + test_prediction_task | **230 passed / 0 failed**(41.5s) |
| 全量 | `pytest tests/ -q -m "not slow"` | **1905 passed / 0 failed / 16 deselected**(4:28;基线 1834 + 本轮 71 新测试 = 52 scope + 19 cost) |
| G01 安全隔离 | `/tmp/safe_g01_s5b_hit50_v3_r1.py`(sha256 `396e6f9056bc…f1d80`;沿 hit50_v3 血统:路径 allowlist、SHA 前后核验、变更集精确披露、`python -B`、`-p no:cacheprovider`) | **exit 0;1894 passed / 10 skipped / 17 deselected**(4:24;v3 G01 1823 + 本轮 71;输入 SHA 失配 = [];325 输入前后重核全一致;pyc 7(子进程缓存例外,同前几轮模式);实际 HEAD 0c6e45d + dirty=true 记录于 preparation.json) |
| 父基线红绿 | 见 §四 | 50F/6P/1C(47 行为+3 字段+1 collection) |

## 六、G01 隔离结果

- 脚本:`/tmp/safe_g01_s5b_hit50_v3_r1.py`(sha256
  `396e6f9056bce3c4d50635cabbde6bed51c0054355186edf70b6f693905f1d80`);
  输出根 `/tmp/g01_s5b_hit50_v3_r1/`(fresh tmp;不在永久目录建库);
- 变更集核对:expected_changed == observed_changed = **恰本轮 9 输入**
  (8 源文件 + wv6 测试);2 新输入(v3r1 scope/cost)vs v3 G01 集;
  325 输入 SHA 前后重核零失配;
- **exit 0;1894 passed / 10 skipped / 17 deselected**;10 skip 逐
  nodeid 见 `post_run_sha_result.json`(v4 对照代码根不可用/v2
  provenance 未生成/v3 冻结基准不可用/G01 边界冻结文档缺席——与
  v3 轮缺席类别一致,不新增缺席类别);17 deselect = controller
  `-k` 口径 + 1 显式 deselect(沿 R7/R8 血统);
- pyc 7(子进程缓存例外,如实登记;父进程 `-B`、
  PYTHONDONTWRITEBYTECODE、pytest cacheoff 保持)。

## 七、同门 P2 文案/工程搭车清单

1. **evaluation 集合、recorded 多重集**(mimo r28 A5 采纳):判分侧
   参与物比较 = **集合语义**(现行为 `evaluation.py:reactants ==
   from_states and products == to_states`,state_ref/state_id 集合,
   重复组分天然塌缩;源码注释与预注册 §3 表述已是"集合相等")——
   任何"参与物多重集严格相等"的文稿表述(如 r28 请求稿 P1)与实现
   不符,**禁止静默改冻结判据为 multiset**;recorded 编译墙
   (W-V2/recorded_source)的产物核对 = 严格**多重集**,两口径分别
   写真、不混用;
2. **"恰一可复现"修词**(复审 §3.2):W-V2 编译择优应表述为
   "至少一可复现、同严格多重集合并、确定性选首"(源码取可复现首项,
   等价目标可多个)——不改算法迁就措辞;
3. **v3 交付 §5.1 分类算术订正**(复审 §3.2):前三"修"类合计 50 与
   "另 15 水解也写本轮修"不闭合;正确分层为元素缺席 9+29=38、其余
   6+7=13;该订正为文稿层,4/228 等真实恢复数字只以 v3 轮自身证据
   背书,本轮不重新外推;
4. **父红分类订正**:v3 轮"17 红全行为"改为 13红+4绿+1collection
   (10 行为+1 kind+2 字段);本轮交付书 §四按同分类法定义并给出
   本轮 50F/6P/1C 分类;
5. **入口锁定义域升级**(mimo r28 D2):扫描面 src → **src+scripts**;
   evaluation.py 内豁免从整行前缀改为**计数==1** 断言(代码+测试已
   升级:tests/test_ppv1_s5b_hit50_v3_wv6.py);
6. **"核档位不核映射"落字**(mimo r28 D1-②):判分门 detail 新增
   机读 `gate_scope`(wv6 测试断言内容);
7. **trigger_equivalence / §9-4 同步句**(mimo r28 D3):评测器 L01
   detail 已有 trigger_equivalence(不变);判分门 gate_scope 已落;
   预注册发车侧 §9-④ 同步句**随新登记**执行(不改冻结稿)——登记为
   发车清单义务,不在本轮伪造。

## 八、金标边界自查

- 实施期零真实模型调用、零花费、零外部网络(唯一"网络"是测试内
  127.0.0.1 假提供者,本机回环)、不 push、不部署真实批、不启动
  chain10、不改封存/冻结产物;
- 未读 298 题卷/金标/旧答卷/封存逐题 run;合成测试分子与真实集合
  零重叠口径沿用 s5b_runtime 夹具(乙醇级合成小分子);
- 冻结判据/scorer 匹配/排序/(created_at,event_id) 顺序/S5B_PASS_LINES
  零触碰;本轮改动 = 判分入口校验 + 守卫新增 + 发送前金额门(全部
  fail-closed 方向);
- 旧批/旧 G01 产物只读;父 worktree 用后即删。

## 九、提交构成与证据

- 源码(8):`adapters/{rate_gate,llm_client}.py`、
  `pollutant/{evaluation,s5b_scoring,s5b_orchestrator,s5b_cli,
  s5b_worker,real_model}.py`;
- 测试(3):新增 `tests/test_ppv1_s5b_hit50_v3r1_{scope,cost}.py`
  (71 用例);升级 `tests/test_ppv1_s5b_hit50_v3_wv6.py`(锁测试
  计数断言+gate_scope 断言,4 用例保持全绿);
- 新文档(1):本交付书;
- 证据(未跟踪,按 AGENTS 默认留 /tmp 易失):`/tmp/s5b_v3r1_impl/`
  (父红绿分类 + junit/stdout/stderr/exit + 回归命令与日志清单)、
  `/tmp/g01_s5b_hit50_v3_r1/`(G01 完整产物:preparation/input_sha256/
  execution_result/post_run/junit/stdout/stderr)、
  `/tmp/safe_g01_s5b_hit50_v3_r1.py`(G01 脚本,sha256
  `396e6f9056bc…f1d80`)。

## 十、待复审问题

1. **429 释放口径**:本轮工程判断 = 显式 429(提供者明示未处理未
   计费,llm_client 既有文档口径)预留退回;其余无 usage 结局一律
   保守保留。若复审要求 429 也保守保留,改动面仅
   rate_gate.record_response 一分支 + 2 个测试断言;
2. **60 CNY 真实值与输入保守界/输出上限的定稿**属受权协调者发车
   当日(CLI 默认 60/30000/8192 仅为缺省值,发车按当日报价与实测
   prompt 尺寸定稿并冻结);
3. 预注册 §9-④ 同步句、stereo/E-Z 能力边界披露等 P2 项按报告 §5
   随新登记/下一小修落字;
4. `s5b_orchestrator` 契约版本升 s5b-orchestrator-2(新增 budget
  冻结字段;既有批根无 orchestration.json 兼容——新旧字段缺省不
  冲突);真实批按新登记走新批根,不回写旧批。
