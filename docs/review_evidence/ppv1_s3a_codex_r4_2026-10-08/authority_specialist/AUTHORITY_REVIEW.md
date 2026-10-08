# S3a-r4 权威专项独立复核（2026-10-08）

实际 HEAD `b7f2bba02ca49edd0a45a13bc9b8434909d99175`；父 `41d0cd55f3def050a62325f00235cf22da302d2e`。固定验收为 R3 主审 §4.1 最低收口、§5 已裁定边界及 §7 放行条件，不增加 S3b、科学机制/性能、外部 SQL 并发破坏或抗整库一致重造门。全部 depending43，在新 `/private/tmp/ppv1_s3a_r4_authority_inolg6_c` 的完整 src/vendor/pyproject/worker 副本执行，`-B` 与禁字节码；只用原永久证据合成输入和新的合成控制，无网络/provider/外模，无题面、金标、封存 run 或 dependingv4 访问，主仓零修改。

**专项结论：S3A-02 三必要预约集合残余关闭；S3A-01、原行级旧反例、H07/H08、四崩溃与并发认领保持。cache_hit 存储同构边界按 R3 固定验收接受为 P2 范围披露，不声称所有检索预约完整认证。** 本专项不为工程全量、预算/request 或化学意见执行数字背书。

## 1. 逐案独立执行

| 捕获 | 当前实际 | 精度边界 |
| --- | --- | --- |
| R3 必要引用集合63 | 9入口 × 3必要资源 × 2删除模式共54坏均 `SearchIntegrityError`，前后14表逐案完全相等；9合法正常 | 27仅删ref为 `necessary_reservation_ref_missing`；27删ref+row为 `reservation_row_missing`。B3六坏均 event0→0、commit0→0、原artifact保全；done四复用拒零新成功确认 |
| R3 上限1双链2 | 干净第1完成，第二claim预算拒；坏第1complete缺必要总额度行拒，第二不同hypothesis合法链完成，只有1commit/总used1 | 坏链普通 `submit_action_event`仍成功保存第1event；随后complete拒，第二合法event保存并完成，最终events2/commits1/used1。门钉的是坏完成及commits2，不把普通独立首提说成零event；B3前置零event已单独证成 |
| R2原27 | 24坏权威 `SearchIntegrityError` 拒，恢复/正确writer重放零写；2合法与1raw输入首提拒保持 | 按原12×2分案完整捕获，不由历史observed早停推断 |
| R2原120 segmented | 111坏拒/保全，9合法 | 四异run/parent/context/hypothesis direct/write/B3均拒，artifact保全；8个H07/H08包括hash/JSON/身份/版本/task/attempt/事件/提交记录控制保持。附随投影/计划同源语义拒，无自比较授权 |
| done2 | 同event返回真实已完成event；有效异parent明确 `SearchContractError(kind=event_identity_not_frozen_to_action)` 拒零写 | foreign输入在另普通store已证可合法首提，不凭无效foreign事件制造负控 |
| normal first-submit3 | projection/plan非法产品ref、plan非法status首提拒且全表零写 | 当前公开store语义与历史附随首消费保持同源 |
| defer13 | 9坏预约/attempt行拒零写；4合法保持 | 未执行释放、alternative跨action共享used1/总actionused2、非expand空attempt非事件outcome、expand failedattempt合法done/二次幂等 |
| crash/barrier5 | B1–B4四子进程实际硬退出；双独立进程ready/GO barrier只一认领胜者 | 六worker进程实际执行；B1沿原attempt/reservation；B2悬空不默发及显式retry；B3同output一次提交；B4幂等账；网络0 |
| cache边界7 | 三可接受形态、两个损坏可检测控制、两个零检索预算控制全部按当前合同 | 具体说明见§2。分案数不与pytest/科学性能相加 |

`assert_r4_capture.py`只读已捕获的完整输入输出，合同断言 exit0；没有重跑任何上述探针。原必要探针、逐案输入、mutated前后14表和artifact信封保留。

早停与旧断言如实登记：上限1旧脚本末断言仍期待旧漏洞commits2，当前只有commits1而失败；两案完整IO已保存，后续汇总footer未运行，正确断言只读取两案IO。done旧捕获脚本末断言误期待 `SearchIdentityConflict`，实际为 `SearchContractError`；两案完整IO已保存，只读正确合同断言核验，无重跑。`probe_original.py`仅合法B3正控输出后，异run write在正确拒绝处停止，后续compound内段未运行；本轮对应120分段独立完整执行。历史 `assert_observed.py`按设计在首坏state_charge拒绝处失败，其化学后段未运行；R3原 `assert_r3_capture.py`在必要集合首坏案找不到 returned 的旧形态期待处失败，前面的原120等读取已完成。不是“所有旧assert通过”。原脚本与完整stdout/stderr/exit、只读适配diff均保留。

## 2. cache_hit 同构边界的执行级裁定

本轮新公共链对照用相同 run、query、parent、context、policy、task_key、frozen_pool_digest、action_id：

1. 合法 `claim_action(cache_hit=True)`：只创建总action预约，不创建两检索预约；recover正常、非事件outcome complete成功、done再恢复幂等。
2. 合法非cache认领：总action+两检索预约，成功完成后retrieval used1。
3. 非cache仅删两检索ref、对应row仍在：`necessary_reservation_ref_missing` 拒，零表变化。
4. 非cache仅删两检索row、ref仍在：`reservation_row_missing` 拒，零表变化。
5. 非cache同时删两ref与两row：当前存储变为合法cache形态，recover／complete／done复用成功，retrieval used0。没有凭“源码看起来如此”代替实际执行。
6. 合法cache在两检索预算0时仍可认领，仅消费总action；非cache相同0预算拒，完整事务回滚。

第1与第5在忽略**仅时间戳列**后，消费前14表逐值完全相等。action/run/policy/task及payload一致，不删除其他身份、commit/hash/attempt；认领收据同样不含cache_hit。真实区别只存在于执行夹具保存的claim参数及第5曾存在的两预约行；该参数在仓内权威账未持久化，后续guard没有独立来源可区分。`claim_action` search.py:975–986 条件创建；必要集合核验 :2045–2058 条件以预约行是否存在推断。跨run查询、artifact或task_hash也没有该分支标记，不应声称取这些字段可认证实际缓存命中。

**裁定：接受为固定S3a范围的P2边界，保留后续任务。** 不是单因“需要改schema”降级；执行表明这是一项条件历史事实没有持久来源，删除两引用与两行后形成另一合法当前形态。本轮R3最低收口明确合法cache_hit不强加未消费资源，并不要求全库抗一致重造／历史真实性证明，当前54三无条件expand必要资源与可区分的检索缺项已经闭合。若仅凭缺检索行一概拒绝，便破坏R3明确合法cache正控；在已定合同内尚不能用当前形态证明原claim不是cache_hit，也不能把“当前结构合法”说成“检索消费历史已认证”。此边界是检索额度历史真实性的限制，不外推所有必要证明均已闭合，亦不把完整性判据的范围扩成科学机制证明。

S3b生产调度若需要恢复后认证 cache/实际retrieve执行与预算历史，应登记持久cache来源／分支事实或明确unknown，再按身份/version规范待审；这是后续工程接线注意事项，不本轮新冻结门。保留此实际反例证据，后续若在相同有限合同内证明可区分权威仍被绕过，再按AGENTS规则重开。

## 3. 原边界保持

两事务之间未持锁继续是R2/R3接受的顺序单消费／合法不可变writer模型边界，本轮未重跑主动外部SQL并发破坏，不声称跨外部并发改库安全。defer无法归因event保守不退额度继续接受，不把过拒当一定已执行证明。本专项只验证已定搜索权威，不扩大到真实provider的外部exactly-once。
