# 专项裁定：S3A-03/04/05

源码与证据以 README 的当前 dcb7ed62 HEAD 为准。

## S3A-03：退款原缺口关闭，冻结坏策略读消费仍 P1

原上限 1 的公开 submit → defer 链已拒：event 保留 1、总 action used=1、defer 零写，第二备选 claim 因预算拒且零写。合法未执行 defer 正控全部释放/abandon，registered real 请求随 defer abandoned，但真实登记 used=1 保留；sent/responded/failed 请求和 recorded/failed attempt 不能退款。原 bool/越界1001/unknown/-1 在 register、budget、enqueue、claim、request register、recover 均消费前拒，零成功写。

残余不是 profile 用户覆盖配置补默认本身。`profile.validate_search_limits` 本来允许用户省略覆盖键并补默认；对已注册的完整冻结块，需要注册和读消费用同一**完整块**形状/版本门。`search.py:533` 注册在调用 validator 前检查 dict 和版本；`:584-599` `_limits` 没做相同门，直接把持久 `null`/缺版本交给允许用户覆盖的 validator；`profile.py:273-288` 从默认字典开始，`(limits or {})` 对 null 返回默认。

完整原冻结块总 action 上限 0；只把其 `search_limits` 字段改成 null 后：

- `_limits`（通过 budget_snapshot）实际返回总上限10；没有拒坏块。
- 原矩阵 expand claim 成功，action pending→claimed，新增 1 attempt + 3 预约。补证 decide claim 成功新增 1 总额度预约。二者均是从总预算0被阻止的合法未执行动作，损坏字段后获得执行权，不能称一般过拒或只读展示精度。
- recover 默认不传 policy_block 返回正常恢复报告并显示默认10；传入同损坏块也正常返回。若调用方仍持有原完整冻结块并传入，既有 policy identity mismatch 正确拒。**这个可选比对正控不补默认入口的漏闸**。

只删除原完整 search_limits.version 时：预算、默认 recover、same-damaged-expected recover 均接受，默写当前 limits version 的派生视图。claim 因原总上限0拒为 budget_exhausted，不能报坏策略拒；原-frozen-expected recover 身份比对拒成立。证据补证全部保存原完整块/损坏块/expectedpolicy argument/前后 rows。

对应首轮 S3A-03 最低修复“注册与后续读取/恢复实际消费配置用同源类型、范围、键、版本验证，拒坏块在写入/执行之前”。最低回修只需共用完整持久策略门与现成数值 validator，不改变用户合法覆盖装配语义。

未归因事件的保守 defer 拒已按交付披露核验：事件存在且没有任何 action commit 归因时不退额度。该过拒不升级本轮新 P1；有普通未执行合法释放正控，也没有全面拒 defer。

## S3A-04：登记原例关闭，但坏现存引用与消费/恢复仍 P1

当前 intake 原非法 action/attempt 均拒；合法 non-expand 空 attempt 保持；payload/purpose/另合法 action/retry_of/损坏 payload_hash 的同键冲突均零写。合法 scoped scripted/fake sent→responded 网络0、同键零新写、real0登记拒、显式新 retry ID 恰占剩余额度、悬空不默发保持。

三条同根入口残余：

1. **已有请求复用只验证 caller 引用，不验证 stored 引用**。合法 expand request 登记后，保持 request_id 和其余内容不变，仅把 stored model_requests.run_id 改 foreign_run 或 attempt_id 改 missing_attempt；再次提交原正确 action/attempt/payload/purpose/provider/key，`register_model_request` 返回 unchanged/same_request_key。`:1100-1127` 对比 action/purpose/hash/retry，未对比 stored run/attempt/provider，也没把 stored 引用交共享执行门。这是有完整 incoming 参数情况下的确定性一致性问题，无需凭 digest 重建旧 payload。
2. **状态门漏 run 归属及 expand 必需 attempt**。`:1170-1229` `_verify_request_execution` 核 action存在/claimed、非空 attempt存在/action绑定/open；不核 action.run_id、attempt.run_id 和空 attempt 的 expand 必需性。合法 scripted 请求先登记，分别仅改 action.run_id、attempt.run_id 或 request.attempt_id 为空，再走 sent/response/failed：9 个组合均成功，把请求真实写成 sent/responded/failed，网络仍0。相同坏引用在 intake 会被拒；状态消费不是新 S3b 功能。相反，missing action、pending action、missing attempt、foreign attempt.action_id、closed attempt 的状态入口已零写拒，保留为有效修复。
3. **恢复未共用请求完整归属门**。`:2192-2220` recover 从 `_crash_boundary_rows` 把 registered/sent 行直接投影为普通 pending/unknown；请求 action 缺失、action处于pending或foreignrun、closed attempt、expand请求空attempt、defer后把request状态拨回 registered，均可返回普通pending且没有相应坏引用披露。它没有授予新认领或调用 provider、也没有写库，**不宣称恢复已真实执行模型**；但按首轮明确要求恢复消费请求权威的合法引用门，这仍是接受已损坏必要引用为可用普通 pending 的同合同残余。B1自身 action/attempt引用核验能拒 missing/foreignattempt 的部分案，不能替代请求引用全覆盖。

反例全部在合法注册后只改单项事实；登记 real 的坏案都仅登记，状态调用 scripted；完整输入/前后 rows与结果在 contract 原日志。同键坏stored run/attempt 均不新增，但仍错误“unchanged”接受；state9案均有成功状态写。是否把仅pending报告异常处置为整体raise或单请求明确隔离，可按原有限合同实现，本审不加新外部 exactly-once 门。

不要求 recover 在只有旧 digest、没有原 payload时凭空重算 payload hash。原 incoming payload 对比已足够修复该旧入口；本轮新增残余全部有 caller参数/存储身份/引用事实可以直接比对。

## S3A-05：关闭保持

有余预算 claimed action 的 stop primary=None、claimed=1/open=1，recover报告B1；user_stop支配。完成后和真正空run exhaustion成立；pending/deferred/blocked不会冒充exhausted，悬空请求 awaiting_prediction，空池 no_local_candidate。六原因原固定顺序63个非空子集主因/其他原因全部保持。真实请求/检索/转换/总动作/深度/宽度独立零资源夹具只拒适用动作，其他资源的decide/scripted正控保持。

旧 stop 的同输入在独立新目录原 observed exhausted断言失败；合同捕获 primaryNone/claimed1/open1；无需追加 S3b队列调度才能证明已修复。初始 expected priority错误已在README诚实更正，未当源码阻塞。
