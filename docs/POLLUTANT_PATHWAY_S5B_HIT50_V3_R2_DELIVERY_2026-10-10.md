# PPV1 S5b HIT50 v3 回修轮 R2 交付书(S5B-V3-02 三残余子案,2026-10-10)

状态:`implementation_ready_for_review`(本轮零真实模型调用、零花费、
不 push、不启动 chain10、不改冻结判据与 scorer 匹配/排序、不回写旧批、
S5B-V3-01 保持关闭零回退)。

依据:R1 正链复审报告
`docs/POLLUTANT_PATHWAY_S5B_HIT50_V3_R1_CODEX_REVIEW_2026-10-10.md`
§4.2/4.3/4.4 三残余最低收口 + §8 回修提示词(权威);上轮主审报告
`docs/POLLUTANT_PATHWAY_S5B_HIT50_V3_CODEX_REVIEW_2026-10-10.md` §4.2/§8;
R1 交付书 `docs/POLLUTANT_PATHWAY_S5B_HIT50_V3_R1_DELIVERY_2026-10-10.md`。
基线 HEAD `b502b75c267842caa109ec8bb6735b5a0555584a`(直接父;行为基线
沿 R1 报告口径:R1 行为修复提交 `fecb0005`,注释父不充当行为基线)。
范围限三个已证子案,不借此扩大为新阶段防篡改体系,不重开化学供给/
提交序/S3/S4,不实施 V4/E。

## 一、三子案修法(一句话)与入口矩阵

**残余 A(usage 完整性)**:重写 `adapters/rate_gate.py::_cost_of_usage`
——单轴三分类(缺席 / 显式存在且有效 / 显式存在但类型坏·负数·非
有限),缺轴不再 `or 0` 补零:input/output 两轴均显式且有效(含明确
0)⇒ 完整合法拆分按各自单价精确结算;两轴不齐而 total 显式有效且 >0
⇒ 合法可核总计走既有保守总计口径(全额较贵单价);其余(prompt-only/
output-only/空 usage/字段坏/非 dict)⇒ `None` 不可计,预留按未知保守
保留,不退可能已付金额。结算唯一消费入口 = `record_response`(其余
usage 消费面为 TPM 滑窗速率记账,不是金额结算,不在本子案,见 §十)。

**残余 B(429 保守保留)**:`record_response` 结算分支删除 429 专属
退回路径——无可计 usage 的一切结局(含显式 429)一律预留全额转
unsettled;`llm_client` 不读取 429 的 HTTP 错误体作为计费依据(模块
与分支注释同步改为"提供者对 429 是否计费未核验,不凭状态码退预留";
"提供者不把 429 计费"旧注释属未核验声明,已从源码删除);槽位释放/
429 冷却/HTTP 有界重试/HTTP 数量门(total_requests 不退)保持;重试
每次先重新原子预留、余额不足先于重试传输拒;闸门直收完整 usage 的
429 按同源完整性判据结算(已知完整 usage 走保守计费路径)。

**残余 C(存储冻结块首消费)**:新增模块级
`rate_gate.verify_stored_cost_guard(stored) -> dict`——存储/恢复的
gate.json `cost_guard` 冻结块(已有派生 per_attempt_bound_cny/
config_sha256)对照同源 core 重算(`normalize_cost_guard_config` 同一
判据),错/缺派生值、错哈希 ⇒ ValueError(结构化 detail:字段/stored
值/重算值),调用方 fail-closed;四个消费入口全部核验并消费**同一
重算规范对象**:`_init_state`(恢复装配)、`cost_guard_summary`
(client/worker/身份首消费)、`acquire`(发送临界区,bound/cap/sha
全取重算值,不再读 raw stored `per_attempt_bound_cny`)、
`record_response`(结算临界区,坏块不结算、预留保守转未结算、记账
照常、坏记录保全)。`s5b_worker.worker_main` 在 RealModelAdapter 装配
期捕获 `GateCorrupt` ⇒ 结构化失败 case(budget_guard_invalid,失败题
留分母,零发送);`llm_client._gate_block` 把 acquire 期 `GateCorrupt`
映射为 `budget_config_invalid` 结构化失败(不裸抛)。builder 原始
core(`normalize_cost_guard_config`:CLI `budget`/`load_budget_guard`/
构造参数)保持合法派生入口,与 stored 恢复入口区分(不全面拒绝)。

入口矩阵(输入 → 行为 → 首消费 → 写入/传输边界):

| 入口 | 输入 | 行为 | 首消费 | 写入/边界 |
|---|---|---|---|---|
| `_cost_of_usage`(经 `record_response`) | provider usage(prompt/completion/total 轴分类) | 完整拆分(含显式 0)精确结算;可核 total>0 保守总计;一轴缺席且无完整总计/字段坏/空 ⇒ None 不可计(保守保留) | 结算临界区(锁内) | settled/unsettled 账本;幂等(重复回执 no-op) |
| `record_response` 429 结局 | status=429±usage | 无可计 usage ⇒ 预留全额保守保留(不退);槽位释放/冷却/计数照常;直收完整 usage ⇒ 同源结算 | 结算临界区 | 同上;`total_429`/`cooldown_until`/`in_flight` 保持 |
| `llm_client.complete`(429 路径) | HTTPError(429,可能带 body usage) | 不读错误体作计费依据 ⇒ 闸门侧保守保留;有界退避重试,每次 acquire 先预留 | `record_response`(usage 缺席) | 零依据归零;重试上限/退避封顶保持 |
| `verify_stored_cost_guard` | gate.json `cost_guard` 冻结块 | 派生 bound/hash 对照同源重算;错/缺 ⇒ ValueError(结构化) | 四入口共用判据 | 调用方 fail-closed(保全坏记录) |
| `_init_state` | 状态文件 cost_guard 块 | 恢复装配先核验;坏块 ⇒ GateCorrupt(构造期拒) | 闸门构造(恢复) | 零发起;坏记录原样在盘 |
| `cost_guard_summary` | 同上 | 坏块 ⇒ GateCorrupt,不返回重算洗白值 | client complete 首步/worker `_verify_budget_guard`/`identity_block` | budget_config_invalid 零发送 |
| `acquire` | 状态文件(每次锁内重读) | 锁内核验 + 消费重算 bound/cap;坏块 ⇒ GateCorrupt(零新预留/发送,拒发计数不增,不落盘) | 发送临界区(flock) | 主审反例复现先拒 |
| `record_response`(结算) | 状态文件 + usage | 坏块 ⇒ 不结算,预留保守转 unsettled(账本事实 bound),token 记账照常 | 结算临界区 | 坏记录保全 |
| `worker_main` 装配 | env `V43_LLM_RATE_GATE` → 客户端闸门构造 | 构造期 GateCorrupt ⇒ case failed(budget_guard_invalid),rc=5 | worker 公开入口 | 失败题留分母,零发送 |
| `normalize_cost_guard_config`(builder) | 原始 core(无派生字段) | 合法派生入口不变(CLI/编排器/构造参数) | CLI `budget`/`load_budget_guard`/构造 | 数值字段与 config_sha256 口径零变化 |

## 二、金额语义(v3-R2 修订口径)与契约/代码身份登记

- **结算**(R2 修订):完整合法拆分(含显式 0)结算、合法可核总计
  (total>0)走既有保守总计口径、一轴缺席且无完整总计 ⇒ 未知保守
  保留;预留/孤儿/幂等/overrun 语义与 R1 相同(孤儿只退槽位、金额
  保守保留;重复结算 no-op;超帽披露不回滚);
- **429**(R1 §4.3 正式裁定落地):无可靠未计费证据 ⇒ 全额保守
  保留;"提供者不把 429 计费"为未核验声明,不再作为任何源码口径;
  客户端不读 429 错误体;`released_unbilled` 不再写入(旧状态文件中
  的历史条目是账本事实,不受影响,源码注释已注明);
- **契约**:`s5b-budget-guard-1` schema、五个数值字段、
  `config_sha256` 计算口径、CLI 幂等/改值拒、orchestrator 冻结副本
  均零变化(本 R1 交付既有控制全绿);**结算语义是代码行为**,新批
  登记按既有规范引用实际部署代码身份:本提交 HEAD + legacy 52 文件
  聚合 `cd683e36f46d3c1afb6389bec38746555d0ecd7d324f3823c994db7fa94ef978`
  (相对 R1 聚合 `e4b934e9d83affbb…` 变化文件 = rate_gate.py/
  llm_client.py 两共享 adapter,逐文件 SHA 见
  `/tmp/s5b_v3r2_impl/legacy_identity_r2.json`);R1 语义批按其当时代码
  身份解读,不回写;
  【v3-R3 订正 2026-10-10,R2 正链复审 §5】本处 `cd683e…` 聚合
  算法未确认、与公开函数
  `pathway_v43.storage.run_identity.code_identity('legacy_v43')`
  (排序 k:v 换行聚合)不相容,不能当部署身份(复审观察 R2 公开
  聚合实际为 `b0d4e9bc…`,父 `e4b934e9…`,仅两 adapter 字节变)。
  新发车登记必须用实际公开聚合实测值:R3 修复后实测为
  `279d9bc19bad25e51b7c23ee276da95151a8f25cf598b9dc3642b508d817c4bb`
  (52 文件;见 `/tmp/s5b_v3r3_impl/legacy_identity_r3.json`),
  勿沿用本处 `cd683e…` 与任何旧值;
- **不变面**:TPM 滑窗/429 冷却/HTTP max_calls/40 在途/1 logical/
  format0/RPM 全部不动(`test_other_gates_untouched_with_cost_guard`
  及 178/258 定向绿在案);`cost_snapshot` 维持 raw 只读披露(披露
  工具,不作为发送/结算决策入口,如实列明)。

## 三、逐案控制清单结果(`tests/test_ppv1_s5b_hit50_v3r2_cost.py`,
28 用例全绿;全部合成假传输,urllib 打桩,零网络零花费)

**残余 A(client→gate 公开链 + worker 级)**:

| # | 控制 | 结果 | 测试 |
|---|---|---|---|
| A1 | prompt-only(900,无输出轴/总计) | ✅ 不可计:unsettled=BOUND、settled=0(旧口径 settled=input-only 金额并退预留) | test_usage_completeness_matrix_client[prompt_only] |
| A2 | output-only(500) | ✅ 同保守保留 | …[output_only] |
| A3 | 空 usage {} | ✅ 保守保留 | …[empty] |
| A4 | 完整拆分 900+1000(+total) | ✅ 精确结算 .00352 | …[complete] |
| A5 | 显式 0 拆分(0+0+0) | ✅ 结算 0.0(完整合法拆分含明确 0;预留全额退回) | …[explicit_zero_split] |
| A6 | 显式 0 输出(1000+0) | ✅ 按输入价精确结算 .0008 | …[explicit_zero_output] |
| A7 | total-only(3000) | ✅ 既有保守总计口径 .0084(全额较贵单价) | …[total_only] |
| A8 | 一轴 + 可核总计(900+total 1900,缺输出轴) | ✅ 走保守总计 .00532,不按 input-only 结算 | …[prompt_plus_total] |
| A9 | 字段坏(负数/字符串/bool) | ✅ 该轴不可用 ⇒ 不可计,保守保留 | …[negative_prompt/string_prompt/bool_prompt] |
| A10 | 部分usage不得退款挤出第二次发送(帽=一次保守界) | ✅ 第一题后第二次 acquire 先拒,calls=1 | test_partial_usage_no_refund_squeeze_second_send |
| A11 | 合法低费用仍可发(完整拆分 .00036) | ✅ 两题都发送(calls=2) | test_low_complete_usage_still_sends |
| A12 | 重复回执幂等(部分 usage ×3) | ✅ unsettled 恰一次,不重退不重扣 | test_partial_usage_duplicate_receipt_idempotent |
| A13 | worker 级反例复现(R1 §4.2:两题批 prompt-only,旧口径两题均发送仅 settled=.00144) | ✅ 第一题 1 次发送(保守保留),第二题零发送留分母;完整 usage 对照批两题照发 | test_worker_partial_usage_second_question_zero_send |

**残余 B**:

| # | 控制 | 结果 | 测试 |
|---|---|---|---|
| B1 | 429 无 usage(client,预算内) | ✅ 保守保留(unsettled=BOUND);槽位释放 in_flight=0、冷却 total_429=1、HTTP 计数 total_requests=2 不退;重试继续 | test_429_no_usage_conservative_keep_client |
| B2 | 429 body 含 usage(R1 §4.3 独立控制) | ✅ 不读错误体 ⇒ 不归零,保守保留(unsettled=BOUND,settled=0) | test_429_body_usage_not_zeroed_without_basis |
| B3 | 429 直收完整 usage(闸门级) | ✅ 按同源完整性结算(USAGE_ACTUAL);429 直收部分 usage ⇒ 保守保留 | test_429_with_complete_usage_settles_gate_level |
| B4 | 重试余额不足先拒(帽=一次保守界) | ✅ 第一次 429 保留后,重试第二次 acquire 先于传输拒(budget_cost_exhausted,calls=1) | test_429_insufficient_balance_stops_retry_before_transmission |
| B5 | R1 文件 6a 控制改写 | ✅ 每次 retry 先预留(3 留痕:unsettled×2+settled);余额耗尽先拒 | test_http_retry_each_attempt_reserves_429_kept_conservatively |

**残余 C**:

| # | 控制 | 结果 | 测试 |
|---|---|---|---|
| C1 | verify_stored 单元(合法/坏 bound .000001/缺 bound/sha 全 0/缺 sha) | ✅ 合法返回重算规范对象;错/缺 ⇒ ValueError 结构化 detail(reason/field/stored/recalculated) | test_verify_stored_cost_guard_unit |
| C2 | 同值恢复 + verify_config + 旧未启用分支 | ✅ 重开装配正常,摘要=规范对象;无 cost_guard 块闸门行为不变 | test_gate_reopen_same_value_and_verify_config |
| C3 | 恢复装配期坏块 | ✅ FileRateGate 构造 GateCorrupt;坏记录保全(篡改值原样在盘) | test_gate_reopen_tampered_bound_rejects_and_preserves |
| C4 | 发送临界区坏块(构造后篡改 sha 全 0) | ✅ acquire GateCorrupt;零新预留/零发送/拒发计数不增/不落盘 | test_acquire_tampered_state_rejects_zero_reservation |
| C5 | 摘要首消费坏块(缺派生 bound) | ✅ cost_guard_summary GateCorrupt(不返回重算洗白值) | test_cost_guard_summary_tampered_rejects |
| C6 | client complete 首消费(stored bound 坏 / sha 全 0,R1 §4.4"存储SHA改全0也不拒"控制) | ✅ budget_config_invalid,零 urlopen | test_client_stored_bad_block_refuses_before_transmission |
| C7 | acquire 期 GateCorrupt 映射 | ✅ _gate_block → budget_config_invalid(与 summary 首消费同 kind) | test_client_gate_block_maps_corrupt_to_budget_config_invalid |
| C8 | 结算临界区坏块 | ✅ 不结算:预留保守转 unsettled(账本事实 bound)+note;token 记账照常;坏记录保全 | test_settlement_with_tampered_guard_keeps_conservative |
| C9 | **主审反例复现(R1 §4.4 原数值)**:批根合法 bound=.046938(30000×0.8+8192×2.8)/1e6、帽=.001;只把 gate.json stored bound 改 .000001(核心价格/界/原 SHA 不动) | ✅ 正控(不篡改):合法 bound>帽 ⇒ 零发送(budget_limit 终态留分母);反例:worker 装配期先结构化拒(case failed budget_guard_invalid,detail kind=cost_guard_config_invalid/reason=stored_derived_mismatch/field=per_attempt_bound_cny),零 urlopen、零新预留、settled=0(旧代码实际发送 1 次 settled=.00352 超帽不复现)、坏记录保全 | test_worker_stored_bound_tamper_main_audit_counterexample |

**保持控制(不重做,R1 文件既有,本轮全绿)**:预算额度 1-3、双进程
barrier 抢最后额度(4)、未知 usage(5)、失败/超时保留(6b)、崩溃/
孤儿/幂等(6c-6d)、配置三层拒(7)、CLI 机器配置(7d)、公开
worker→adapter→client→gate 假传输端到端 8a/8b/8c(含 run_s5b_batch
子进程 → 真客户端 → 闸门 → localhost 假提供者)、其他门/请求体冻结
输出上限/身份块(9)——见
`tests/test_ppv1_s5b_hit50_v3r1_cost.py`(19 用例)。

## 四、红绿分类(直接父 b502b75 同字节;JUnit 口径,沿 R1 复审 §2 表)

父源 = `git archive b502b75` 解到 fresh `/tmp`(**无仓内 worktree
元数据**),子测试文件覆盖(本轮触碰的 2 个测试文件:r1_cost 改写 +
r2_cost 新增);`python -B -p no:cacheprovider
--continue-on-collection-errors`:

- 父:**1 failed / 18 passed / 1 collection error**;
- 分类:**行为红 1**(r1_cost::test_http_retry_each_attempt_
  reserves_429_kept_conservatively —— 父 429 退回预留、子保守保留;
  旧 nodeid …_and_429_released 按 R1 复审 §4.3 裁定改写为保守保留
  语义并改名,非静默删除);**collection 1**(r2_cost 模块导入
  `verify_stored_cost_guard` 在父版本缺席 ⇒ ImportError,28 用例未
  执行,**不记 28 行为红**);**保持绿 18**(R1 既有控制零回归);
  拒绝类型/拒因顺序/字段差异红均 0;
- 子(当前 HEAD 工作树):同 2 文件 **47/47 全绿**;
- 逐 nodeid 与 identity SHA(child/parent 每文件)见
  `/tmp/s5b_v3r2_impl/parent_redgreen/classification.json` + 双侧
  JUnit XML 与 stdout/stderr;
- **不写"47 旧放行翻转"式合并标签**(R1 复审 §2 已订正 R1 交付的
  同类标签,R1 交付书 §四 已同步订正)。

## 五、回归数字(当前工作树,depending43 `-B` + `-p no:cacheprovider`)

| 组 | 口径 | 结果 |
|---|---|---|
| 定向(14 文件) | s5b 全家(wv1/2/3/6 + v3r1 scope/cost + **v3r2 cost** + runtime/pairing/rework_l01/hit50 w1/w23456)+ test_rate_gate + test_prediction_task | **258 passed / 0 failed**(46.7s) |
| 全量 | `pytest tests/ -q -m "not slow"` | **1933 passed / 0 failed / 16 deselected**(4:47;R1 基线 1905 + 本轮 28 新测试;6a 为改写不增数) |
| G01 安全隔离 | `/tmp/safe_g01_s5b_hit50_v3_r2.py`(sha256 `6b04031ccbb1…952952`;沿 R1 G01 血统:路径 allowlist、SHA 前后核验、变更集精确披露、`python -B`、`-p no:cacheprovider`) | **exit 0;1922 passed / 10 skipped / 17 deselected**(4:35;R1 G01 1894 + 28;326 输入前后重核零失配;pyc 7 = 子进程缓存例外,如实登记) |
| 父基线红绿 | 见 §四 | 1F/18P/1C(1 行为 + 1 collection,28 未执行) |

## 六、G01 隔离细节

- 脚本:`/tmp/safe_g01_s5b_hit50_v3_r2.py`(sha256
  `6b04031ccbb17fff422bc5c913d4edee5ffaf608eefaf6265c991393ff952952`,
  由 R1 版 `396e6f9056bc…f1d80` 派生:R2 上下文 docstring + 新增
  r2_cost 输入 + 变更集相对 R1 G01 的 5 项披露);输出根
  `/tmp/g01_s5b_hit50_v3_r2/`(fresh tmp,不在永久证据建库);
- 变更集核对:expected_changed == observed_changed = **恰 5 项**——
  本轮 4(3 源文件 + r1_cost 测试)+ **父提交 b502b75 遗留 1**
  (recorded_source.py 注释级修,provenance 单列,非本轮实施改动);
  新输入 1(r2_cost)vs R1 G01 集;零缺失;
- 实际 HEAD `b502b75` + dirty(4 个本轮修改文件)记录于
  preparation.json;10 skip 逐 nodeid 与 R1 轮缺席类别一致(v4 对照
  代码根不可用/v2 provenance 未生成/v3 冻结基准不可用/G01 边界冻结
  文档缺席);17 deselect = controller `-k` 口径 + 1 显式 deselect
  (沿 R7/R8…R1 血统);pyc 7 逐路径登记(子进程例外);
- 全部 argv/env/exit/stdout/stderr/JUnit/preparation/input_sha256/
  post_run 落盘输出根,可复核。

## 七、文稿同步订正清单(R1 交付书 4 处,均加【v3-R2 订正 2026-10-10】
标记,不改历史结论、不删原文语义)

1. **§二 429"不计费"未确认声明**:原文"429 是提供者明示未处理未
   计费的确定性结局…预留退回" ⇒ 订正为 R2 现行口径(缺轴不补 0/
   429 保守保留),并注明"提供者不把 429 计费"是未核验声明;
2. **§二 存储摘要与首消费范围**:新增订正块,如实写明 R1 实现里
   摘要/身份首消费走重算而 acquire 消费 raw stored 金额的口径差
   (主审反例),R2 起四入口同源核验;
3. **§四 父红标签**:原"50 红 = 47 行为 + 3 字段" ⇒ 按 R1 正链
   复审 §2 JUnit 分类表订正(7 行为+20 拒绝类型+15 拒因 kind+4 拒因
   顺序+1 裸 IO+3 字段+6 绿+1 collection;40 拒绝边界单列,总数
   50F/6P/1C 一致);
4. **§十.1 429 待复审问题**:标记为 R1 复审 §4.3 已裁决 + R2 已
   实施。

## 八、金标边界自查

- 零真实模型调用、零花费、零外部网络(测试内唯一"网络"是
  127.0.0.1 假提供者与 urllib 打桩,本机回环);不 push、不部署
  真实批、不启动 chain10、不改封存/冻结产物;
- 未读 298 题卷/金标/旧答卷/封存逐题 run;合成测试分子沿用
  s5b_runtime 夹具(乙醇级合成小分子,与真实集合零重叠口径沿旧);
- 冻结三 SHA 工作树复核逐字节一致:
  `7fd35aabdb4d2d5b67b0bf58693dab6f8765ad872efedf5f886503c4907064e4`、
  `6e046e2970a102c63e693cebb81f2564b5d79fea1a6e7a776b0fc00c09662610`、
  【v3-R3 订正 2026-10-10,R2 正链复审 §5】上一行为复制笔误:冻结
  记录实际完整值为
  `6e046e2970a102c63e693cebb81f2564b5d79fea1b6e7a776b0fc00c09662610`
  (见 R2 复审 §6 全值);冻结文件本身未改,旧主审/永久证据不回写;
  `971ad00f42fc56915bad3724300759aa86552bf08199f8335c7f0286b40d588d`;
- 冻结判据/scorer 匹配/排序/(created_at,event_id)/S5B_PASS_LINES
  零触碰(本轮改动 = 金额守卫三子案 + 配套注释/测试,全部 fail-closed
  方向);S5B-V3-01 关闭状态零回退(scope/basis 定向 258 绿含
  v3r1_scope 52 用例);
- 父红绿父源用 `git archive` fresh tmp 副本,未新增仓内 worktree
  元数据,用后即弃;旧批/旧 G01 产物只读。

## 九、提交构成与证据

- 源码(3):`src/pathway_v43/adapters/{rate_gate,llm_client}.py`、
  `src/pathway_v43/pollutant/s5b_worker.py`;
- 测试(2):新增 `tests/test_ppv1_s5b_hit50_v3r2_cost.py`(28 用例);
  改写 `tests/test_ppv1_s5b_hit50_v3r1_cost.py` §三 6a 控制与模块
  docstring(429 保守保留语义,1 用例改名,总数 19 不变);
- 文稿(2):本交付书;R1 交付书 4 处订正(§七清单);
- 证据(未跟踪,按 AGENTS 默认留 /tmp 易失):`/tmp/s5b_v3r2_impl/`
  (父红绿分类 + 双侧 JUnit/stdout/stderr/exit + 回归日志 + legacy52
  新身份 + G01 运行日志)、`/tmp/g01_s5b_hit50_v3_r2/`(G01 完整
  产物:preparation/input_sha256/execution_result/post_run/junit/
  stdout/stderr)、`/tmp/safe_g01_s5b_hit50_v3_r2.py`(脚本,
  sha256 `6b04031c…`)。

## 十、执行事件与待复审残留

执行事件(准备事件不删):源码改后首跑 r1_cost = 1 failed(即 429
行为翻转点,留作翻转证据后改写该控制);父红绿首跑用 parent_redgreen
相对路径(rootdir 不规范)后以 parent_src 根目录重跑留档(两次结果
一致);G01 脚本 `python -B -m py_compile` 语法校验在 /tmp/__pycache__
留 1 个 pyc,已删(非证据);G01/全量/定向各一次通过,无失败重试,
无账号中断事件。

待复审残留(如实,不虚报闭合):

1. **429 错误体 usage 读取未实现**(选择保守保留口径;若未来核验
   provider 政策后要读,须按同源完整性判据结算并受审——本轮 B3 已
   验证闸门直收完整 usage 的结算路径可用);
2. **TPM 滑窗对部分 usage 的补零**(`record_response` 尾部
   total/prompt+completion 的 `or 0` 记账):速率机制不是金额结算,
   不在三子案范围;如实披露,未改;
3. **total=0-only**(显式零总计、无拆分轴):按不可计保守保留
   (未证 provider 会用 0 表达"零计费",保守方向;完整拆分含显式 0
   已可结算);
4. **结算临界区坏块时不做 overrun 披露**(cap 不可核;新发送已被
   发送临界区拒,committed 账本事实仍完整在盘);
5. `cost_snapshot` 仍为 raw 只读披露(不校验;协调者报告/测试用,
   非发送/结算决策入口);
6. 60 帽真实值/输入保守界/输出上界的发车定稿仍属受权协调者
   (R1 §4.5 残留②③,CLI 默认 60/30000/8192 仅为缺省)。

本轮报告不代替放行;新金额语义/代码身份随新批登记引用,由主会话
核对 → 规则级 mimo → 正链有限复审。
