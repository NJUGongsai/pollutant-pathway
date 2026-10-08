# S3a-r3 预算、请求、停止专项裁定

## 固定验收与关闭状态

验收为R2主审§4.2/4.3原最低条款及§7；不提前要求S3b调度/provider/科学性能。R2§4.2明列“首次注册后的读取/recovery/budget/claim/request消费必须先核冻结块…零成功执行/预约/补账”；§4.3要求“登记新/已有row复用、发送/响应/失败、恢复…策略、生命周期；坏或失效引用不得新建/改变成功状态”。当前已将原114有效矩阵全部收口，合法控保持。

- S3A-03原null/missing-version预算读、claim、recover（无expected/正确expected/同坏expected）均先search_policy_block_corrupt且零写，不再0补10；原四坏值注册/各读取全部拒；合法partial带既有version补全11键，effective同块注册/恢复幂等。上限1已执行不退/二次claim拒、未执行释放、registered-real占额不退、real0、零资源只挡相关工作保持。
- S3A-04原run/attempt已有row损坏重登记冲突零写；foreign action/attempt run、expand空attempt在sent/response/failed均拒；recover坏pending要么顶层拒，要么reference_integrity明确披露零写，不再普通pending。同内容复用、非expand空attempt、scripted/fake网络0、explicit retry新ID/剩余额度、释放后拒执行保持。
- S3A-05 claimed/open完整披露、primary=None、独立零资源/空池/user_stop、63原优先级组合均保持。

## 残余 S3A-03：请求状态消费遗漏严格冻结策略

源码search.py:681 `_limits`已严格核冻结块，register:1085会先调用；但record_request_sent:1400、record_request_response:1433、mark_request_failed:1460只核请求status与 `_verify_request_execution`:1288，后者不消费_limits。

公共链：合法register run→enqueue→claim→scripted request登记（response案先合法sent）→仅把存储search_limits置null或删version→调用相应状态口。**六案全部接受且实际写状态**，不是无副作用读取。原完整输入、唯一坏字段、前后全表见`evidence/extra_observations.json`六个`policy_request_null_limits_*` / `policy_request_missing_version_*`。bool/越界1001/未知键/负数×三口另外12案相同，共18坏案例；这不是18漏洞，而是同一个冻结消费门在三口遗漏。

三个合法状态正控分别registered→sent、sent→responded、registered→failed均成功。所有调用scripted，真实网络0，没有声称发生实际模型调用/化学verified。属于R2明确request消费最低验收内残余，不要求新冻结机制或改默认额度。最低收口：状态消费者在首次成功写之前共用严格存储policy校验，null/缺version/原四坏值各口结构化拒零状态成功写，合法生命周期/登记失败占额不退保持。

## 残余 S3A-04：未知生命周期能被写成failed

源码已存在`REQUEST_STATUSES` (search.py:205)，mark_request_failed:1461文档只允许registered/sent→failed；:1472实际只排除responded/failed/abandoned，因此未知枚举外值不在排除集合，可进入_verify_request_execution及UPDATE。

公共链：合法run/action/attempt/request→仅把stored request.status改为`corrupt-status`→mark_request_failed接受，前后status **corrupt-status→failed**；坏生命周期权威被改写成普通失败，更新updated_at。证据`extra_observations.json` / `unknown_status_failed`。同坏status在sent/response均结构化拒零写；合法registered→failed控制前述已执行；合法sent→failed另以`scripts/sent_failed_control.py`独立一次执行，exit0/1控制，失败状态正常记录、预约不退款、scripted网络0；不以推断代替。

同键正确incoming在unknownstatus已有row上重复登记returned unchanged=True/status=corrupt-status，零写；仅作既有row未消费生命周期的旁证，核心P1为上面的非法来源成功写failed。恢复未知status不属于pending过滤集，会省略，但claimed/open仍披露，不另算组。最低收口：失败入口只接受既有registered/sent允许来源（或同源合法状态判据），unknown/其他非法来源结构化拒零成功状态写；不要求新增专用错误码/更强provider机制。已有row复用对未知生命周期如实报完整性不假授证，允许保全坏行。

## 交付边界与文字真实性

1. foreign-run pending按run过滤不披露：实际恢复pending空，但action仍claimed/attemptopen且stop.primaryNone；同request状态三口均request_run_binding_mismatch拒，正确samekey登记request_identity_conflict拒，零写。该限定没有把坏引用包装成普通pending或授执行权，按原固定scope列P2诚实范围，不能凭此要求全库反向扫描。交付§7.3如实。
2. “未知requeststatus不会成功写新状态”事实错误：上述unknown→failed已执行反驳，不仅缺专用码。§7.4需改，不能只按文案边界。
3. defer未归因event保守拒旧矩阵实际保持，按R2§5允许，不增门。
4. 两事务未持锁范围由权威专项负责；本专项不新跑主动并发改库窗口。

## 执行与审核夹具精度

原115 raw109/6并不代表6缺陷；oldpriority1与5recover允许结构化披露旧期待只读调整→114/114。supplement2旧expectedidentity错误kind由更早严格冻结拒纠正，均零写。新extra脚本31完整输出后，末两合法partial准备误丢version，未进入有效正控；原脚本/log退出码保留，单独合法带version两控补，31旧案未重跑。新增计数是工程案例，和pytest、科学性能不相加。
