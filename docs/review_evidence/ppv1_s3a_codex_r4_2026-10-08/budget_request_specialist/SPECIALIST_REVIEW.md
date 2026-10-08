# S3a-r4 预算 / 请求 / stop 独立专项结论

HEAD `b7f2bba02ca49edd0a45a13bc9b8434909d99175`，父 `41d0cd55f3def050a62325f00235cf22da302d2e`，2026-10-08。

**本专项 S3A-03 / S3A-04 关闭，S3A-05 保持关闭。** 本裁定只覆盖既有固定验收，不认证全库抗任意一致重造、不要求 S3b caller、真实 provider 或科学性能。

## 1. 原 R3 状态消费反例已翻转

原字节复制 `scripts/extra_probe.py` 完整执行前31案：

- 18案，sent/response/failed × 已冻结块 null/缺version/bool/1001/未知key/-1：`SearchRecoveryError` / `search_policy_block_corrupt`，全部先拒、零账表变化。
- 3合法状态控制成功且scripted网络记录0。
- unknown `corrupt-status`：sent / response 保持拒；failed改为 `SearchContractError` / `request_status_unknown` 拒；同键复用 `SearchIntegrityError` / `request_status_unknown` 拒。四口均零写、原坏状态保全。
- recover 正常返回的是恢复报告；run范围枚举外行实在 `unknown_status_requests` 披露，未变合法pending/新status，不授执行权，零写。原脚本为顶层必须抛错写的checks不适合本轮明确的披露契约，已只读校正，原输出不改。
- foreign-run行状态口/同键复用拒；run范围recover不扫描foreign行而普通返回，此为R3已接受P2作用域边界，不能当新P1或跨run完整诊断。

原脚本最后两合法装配控制仍误删已有必需version（已在R3登记的夹具准备错误）：注册失败后读取未注册run使exit1；前31案完整输出、后两未执行，未报通过。原合法带version的`legal_assembly.py`两案独立执行一次，完整块11键、同effective配置合法幂等、总预算0保持。

## 2. 公共入口与同源规则互证

源码r4行号：

- `record_request_sent`:1454，`:1480`之后 `_verify_request_execution` 与 `_limits` 在事务内、新status写入前执行。
- `record_request_response`:1493，`:1510–1513` 消费执行引用及严格冻结块后写responded。
- `mark_request_failed`:1524，`:1547` 枚举外拒，`:1555–1556`正面限定registered/sent；`:1563–1565`核执行引用及冻结块后才写failed。
- `register_model_request`:1126，`:1287`核stored status枚举，不再凭同键返回坏unchanged。
- `recover_run`:2704，`:2767–2774`构造run范围unknown_status_requests，`:2803`返回；pending行引用守卫保持。recover报告正常返回不等于未知行成功消费。

以非expand合法空attempt的decide动作追加全表35案：18坏policy×三口全部先拒（与原expand动作同一规则）；unknown五入口；三real登记记账正控（实际未调用provider）；responded/failed/abandoned终态×三状态口9拒。**35/35符合，逐案15张表前后完整快照。** real样例sent的账内`network_request_count=1`为主动调用账接口的记录，不宣称发生真实网络发送。实际网络/外部模型均0。

## 3. 继承控制

原矩阵raw115案仍109/6：五recover旧脚本只要求顶层抛异常，但实际已按最低合同给`reference_integrity`显式披露；一个历史priority期待把awaiting和no_local次序写反。保留原stdout和checks，不修改原probe。只读adjudication按既有合同校正后 **有效114/114**（03=40，04=60，05=14）。六原因正确63非空组合 **63/63**，10冻结块读/claim/recover（包含无expected）全部search_policy_block_corrupt且零写。

已执行event/defer不退额度、上限1第二claim拒、未执行defer合法释放、已登记真实请求占额不退、合法nonexpand空attempt、scripted/fake零真实额度、显式retry新ID且剩余额度/real0、claimed/open披露/独立零资源/空池/真正耗尽保持。合法sent→failed单控制保持，不退款。

此处计数为合成控制案，不是漏洞数，不与PPV1/G01相加，不外推dev(B1)或298(RHEA)科学性能。必要集合/cache_hit专项由authority同事负责，本专项不代为裁定。
