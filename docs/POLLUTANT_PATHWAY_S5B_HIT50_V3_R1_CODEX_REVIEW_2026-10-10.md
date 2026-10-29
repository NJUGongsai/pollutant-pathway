# PPV1 S5b HIT50 v3 回修 R1 正链有限复审（2026-10-10）

## 1. 正式裁定与实际基线

**R1 暂不通过，chain10 不放行；P1=[S5B-V3-02]。S5B-V3-01 关闭。** 金额原子预留已落地，但同一金额帽规则还有三个残余：部分 usage 被当完整计费证明、429 无未计费证据退款、存储派生金额与实际发送消费不一致。没有新增 P1 编号，也不重开提交顺序、化学供给、S3/S4/ISO 或历史 launch 已闭合组。

| 裁定项 | 结论 |
|---|---|
| 1：S5B-V3-01 | 收口。原公共链 8 个空值反例全部先拒零 metrics；合法 real/synthetic、真正省略参数和缺省字段控制保持；basis 四个原模拟坏形态先拒。 |
| 2：S5B-V3-02 | 尚未收口。flock 原子预留、worker 接线、空 usage/孤儿保留、幂等和低费用正控成立，§4 三个子案仍使可能已付未知额度退回或坏派生金额被消费。 |
| 3：429 政策 | **改为无可核未计费证据时保守保留金额**。HTTP 429 状态码本身不证明计费为零；当前代码没有额外依据。槽位释放、冷却、有界重试保持。 |
| 4：chain10 | 暂不发车；只修原 S5B-V3-02 的三个残余，再有限复审。§7 六条清单映射已列，但金额帽机器生效不能签为完成。 |
| 5：红线 | 冻结三 SHA 父子一致，匹配/排序 helper AST 未改；b502b75 仅注释改动、全文件 AST 相同。R1 两共享 adapter 字节和 legacy 身份确有变化，须如实用新身份登记。 |

实际审定 HEAD：`b502b75c267842caa109ec8bb6735b5a0555584a`；直接父及行为修复提交：`fecb00055c4bb91cee26b8ed35962b6e9fd32338`；红绿行为基线：`0c6e45d074d55ba14b5db7926cebb3f4141013a7`。三者用途不同，不能把注释父当作行为回归基线。

范围仅上轮主审报告 §4 两 P1、§7 清单、§8 有限提示词与 R1 交付/mimo r29。三个本地审核分支的完整输入输出由主审读取、封包哈希复核后采信；没有调用外部模型。所有运行均为 fresh tmp 的合成工程验证，不取真实题面、金标、封存逐题 run 或原 v3 评价资产，不启动 chain10，不认证 298 科学目标。

## 2. 独立执行与红绿精度

| 执行面 | 独立结果 | 证明边界 |
|---|---|---|
| 定向 13 文件 | **230 passed，exit 0** | 包括 scope/cost、新旧 S5b、rate_gate/prediction_task；不与 G01 相加。 |
| 安全隔离 G01 | **1894 passed / 10 skipped / 17 deselected，exit 0** | 325 准入输入，SHA 前后零失配；相对上轮323新增2测试，10变化包含 recorded_source 注释微修。完整日志/逐nodeid缺席封包。 |
| G01 内 PPV1 子集 | **1291 passed / 2 skipped** | 冻结 docs 白名单缺席守卫，冻结完整性由只读 SHA 另核；不称独立 unrestricted 全量。 |
| 基线 0c6 同字节三个测试文件 | **50 failed / 6 passed / 1 collection error** | cost 文件缺 API，19 用例未执行；父源用 git show 复制到 fresh tmp，不新增仓内 worktree 元数据。 |
| scope 专项 | **19 旧观测+31 新观测+7 断言** | 包括预期拒绝、合法接受和模拟 producer；不是50个pytest绿。旧真正放行的8案逐案翻转。 |
| 费用 client 专项 | **10 场景，20 次 complete 调用，14 次假传输** | 全 usage、空 usage、total-only、partial、429、坏派生金额/哈希与输入界说明；网络/账单结论不外推。 |
| 费用公开 worker | **4 fresh 场景，7次 worker_main、6次假传输** | worker→adapter→client→gate，完整合成 case/gate/run_identity 留档；不是仅 helper 结果。 |
| 费用双进程 barrier | **1 成功发送 / 1 金额拒；1次假传输** | 最后额度原子竞争保持，金额机制已有正确部分。 |

费用专项总计 **21 次假传输、真实服务商调用与费用为0**。统一回归含本机回环假提供者，不声称没有本机 HTTP。交付/主会话“1905 passed/0 failed/16 deselected”登记为他方真实仓树全量声明；本审使用安全隔离回归，不在真实树跑 `tests/` 全量，不混报为同一口径。

**父50红分类须订正，不能写47次旧放行→新拒。** 独立 JUnit 分类如下：

| 类 | 数量 | 实际旧行为 |
|---|---:|---|
| 明确缺预期拒绝的行为红 | 7 | validate 的5种 falsy + 2个 basis shape；另有真正旧公开链8案由专项补证，数量有重叠不能相加。 |
| score API 拒绝类型/边界变化 | 20 | 父已抛 EvaluationContractError，测试期待 S5bScoringError。 |
| validate 拒因 kind 变化 | 15 | 父已拒，新 reason 不同。 |
| evaluate 拒因优先级变化 | 4 | 父先 reference_graph_missing，当前先 data_scope_invalid。 |
| 裸 IO 错误→入口拒 | 1 | 父 FileNotFoundError，当前先 scope 拒。 |
| 新字段披露红 | 3 | data_scope_provenance、data_scope_normalized_from、gate_scope。 |
| 合法保持绿 | 6 | 实际保持控制，非新行为。 |
| cost module collection | 1 | 19个内部案未执行，不能记19行为红。 |

交付50F/6P/1C总数一致，47行为+3字段标签不成立；应按上表把“40个拒绝边界/类型/顺序变化”单列。该订正不取消有效修复：S5B-V3-01 收口依据是原合法公开 fixture 的逐案翻转，而不是缺图/缺文件弱夹具的异常名替换。

10 skip/17 deselected 逐 nodeid 在 `execution/logs/g01_absences.json`，报告附表按实际 observer 列出。G01 子进程 pyc 例外逐路径登记，不归档；父进程 `-B`、禁字节码与 cacheoff 保持。准备事件与失败不删、不将未执行部分报通过。

## 3. S5B-V3-01：关闭与保留的边界

`evaluation.py:269-324` 的 resolve_data_scope 是共同判据；`:469-475/:2171-2177` 供校验/评测首消费，`s5b_scoring.py:203-226` 在批文件读取前消费并包装结构化异常。显式空串/None/bool/数值/列表/未知/大小写空白变体不再 truthiness 默认。

旧 gate_probe 脚本逐字节复制到 fresh tmp，8 个原可接受 falsy scope（有/无假批准形状）全部变成 `s5b_data_scope_invalid`、零 metrics。批准文档来源固定为缺席输入，evaluator/score 规则本体不替换；basis 族另用模拟 evaluator 产物，二者分开。真实合法 qid_strict 与 synthetic 正控保持；真正省略 score 参数依旧默认 real 并消费批准；evaluation 字段完全缺省保持 synthetic，并输出 missing_field_default，显式合法值输出 explicit。

`s5b_scoring.py:338-399` 的真实档独立门补齐字典形态/空/缺键/foreign/value类型/全 strict，先于逐题聚合和 metrics。原缺 coverage/缺 bases/空/foreign-only 四个模拟接受形态全部拒，合法接受、非 strict 仍拒。注册序为空在 `:235-240` 先拒，正常装载注册图后 expectedGraphIds 非空；没有专属 expected-empty reason，但此输入路径结构上不能通过，不虚报已实现独立专属检查。

非阻塞精度：键经 str 归一，值才是严格字符串；当前正常 evaluator 发字符串键。模拟混合键/归一碰撞与非dict coverage 可保守拒零metrics但异常非结构化，列后续 P2。省略 score 与显式 real 在当前签名不可区分，normalized_from 两者皆 explicit，signature_default=real 记录默认规则；不要声称来源精确区分调用者是否省略。实施测试所谓“完全省略”实际显式 real，本审已补真实省略控制。以上不重开已证实的坏 scope 或 qid配对组。

## 4. S5B-V3-02：已成立部分与三个残余

### 4.1 已成立，不重做

`budget_guard.json` 经共同 normalize 装配，`s5b_orchestrator.py:340-397` 在 real worker 派发前要求配置并冻结到 orchestration；`:365` 消费金额配置，`real_model.py:390-407` 把规范摘要/哈希入 run 身份；`s5b_worker.py:198-268` 对照批根与 gate 配置。契约 `s5b-orchestrator-2` 合理承载新增冻结字段，新真实批走新根；原批字段冲突拒、不回写旧冻结对象。

`rate_gate.py:445-494/:511-546` 的 flock 内先检查 settled+unsettled+reserved+bound，再与占位原子保存；`llm_client.py:339-384` 注入冻结 max_tokens、每次 HTTP attempt 先 acquire。双进程争最后额度只有一个发送，低费用与完整 usage 控制合法；空 usage 转未知借记、第二题额度不足停止/留分母；孤儿只退槽位，结算幂等控制保持。这不是“完全没接预算”旧缺口，须认可这些已修部分。

但不能把这些局部事实扩成所有首消费/未知结算已闭合。以下三案均属于原 §4.2 “可能已付不释放、配置坏/不一致首消费拒”的最低行为要求。

### 4.2 残余 A：部分 usage 缺轴被补0，退掉未知费用

`rate_gate.py:657-685` 特别是 `:667-682` 用 `or 0`；只有 prompt_tokens、没有 completion_tokens/total_tokens 也给 input-only 实际金额，`record_response:601-608` 当完整 settled 退回预留。

独立公开 worker 返回 **prompt_tokens=900、缺输出轴/总计**，两题均发送，仅 settled=.00144。相同配置返回 usage={} 的控制只发送一次，全额未知借记 .046938，第二题预算终态留分母。client 另独立观测 prompt-only/output-only，均不是完整拆分证据。模型响应有实际合成内容，不可由字段缺席推输出费用为0。

最低收口：显式字段存在、类型/非负有效与缺席分开；完整 input/output 拆分（含明确0）可结算，合法可核总计可走既有保守总计口径。只知一轴且无完整总计，不用缺席补0退金额，按未知保留可能已付预留；幂等和合法0/total-only/完整拆分正控保持。不是要求真实账单或新增化学功能。

### 4.3 残余 B：429仅凭状态码退款；正式裁定保守保留

`rate_gate.py:609-613` 的 status==429 分支无其他依据即 released_unbilled；`llm_client.py:399-416` 不读 HTTPError body、不核未计费事实，只把429传 gate。legacy 注释“提供者不把429计费”是既有文字声明，不是本审已核到的提供者计费政策。

两个独立真实客户端/假HTTPError控制：无未计费说明的429、429 body 含 usage，两者都退金额到0并继续第二次发送。该证据证明客户端没有消费计费依据，不证明真实提供者曾收费或 HTTP429一般必收费。

**本轮选择“无可靠未计费证据则全额保守保留”。** 保留槽位释放、429冷却、HTTP有界重试；重试仍需重新预留，余额不足就停止，不自动加帽。若今后要免计费退款，须有绑定当前 provider/计费政策/版本的可核依据并受审，不靠状态码或旧注释。本次有限修复可直接将无usage的429归入未知借记；已知完整usage按保守计费路径处理。未知预算导致早停保留298分母是合法结果。

### 4.4 残余 C：身份摘要重算洗掉坏派生值，发送却消费 raw

`normalize_cost_guard_config:195-198` 生成派生 bound/hash但不比对存储给出的派生值；`cost_guard_summary:779-785` 返回重算规范值；`acquire:458-463` 却用 raw stored per_attempt_bound_cny。同一配置的身份证明和实际发送额度不是同一事实。

公开 worker 反例：批根合法 bound=.046938、cap=.001，本应零发送；只把 gate.json 的 stored bound 改 .000001，核心价格/界/配置原SHA不改，worker批根核对仍过，run身份记录正常重算bound，但实际发送1次，settled=.00352超帽。这是公开首消费错误，不是仅 helper/mock产物。另 client 存储SHA改为全0也不拒，原始坏输入与输出留档。

最低收口：创建配置可从合法原始core派生；**存储/恢复的冻结块**已有派生金额和hash须对照同源重算。发送临界区校验并使用同一合法规范对象，不能摘要重算正常而实际消费另一raw金额。错/缺派生值、错哈希先结构化拒、保全坏记录、零新预留/发送；合法新建/同值恢复/幂等/旧未启用金额分支保持。修复限定当前已证字段不一致，不借此扩大为新阶段防篡改体系。

### 4.5 残留②/③的裁定

60帽、当日价、输入保守界和输出上限真实数值由受权协调者定稿；CLI 60/30000/8192是默认，不是本审已验证provider上界。price/bound/输出参数须在首次发送前冻结，核包括reasoning的计费输出是否真的受该请求参数上界约束、每个实际prompt是否不超输入界。专项故意把提供者usage设超过输入界仅说明外部假设须核，不以任意低配置另立P1；真实provider语义本轮未联网/调用核验，标未确认。

orchestrator-2 契约升级可以接受；预算配置变化产生新身份与新批，而不是继续旧批改参。overrun应披露不回滚实际已付事实，但不能用事后overrun来替代“坏配置先拒/未知不退”的两个剩余守卫。

## 5. mimo r29 与 b502b75 条件互证

| 条款 | 正链处置 |
|---|---|
| F1 集合/多重集 | 按既有判分集合、recorded严格多重集分别落字。集合相等不证明份数/计量一致；一般化学“唯一诚实比较”论断不由本轮程序证据背书。 |
| F2 恰一残留 | b502b75 只改 recorded_source 9行注释；全文件AST父子相同。现 `:541-546` 写至少一可复现+确定性选首，保持算法，不能说映射唯一。旧v3交付176–177行的“恰一”作为历史快照不改，本报告勘误指向R1交付§七.2及b502即可。 |
| F3 门采纳 | scope和basis实际负控互证，gate_scope机读是“核档位/覆盖、不核映射”。键str归一与expected空集合结构拒的表述精度列P2，不冒称键值均严格类型或有专属empty reason。 |
| F4 同步句 | 义务仍待新登记，§7给原文+读回/SHA核对步骤，不签“已落字”。**r29“全qid_strict⇒阻断”方向写反**：合法非空全集strict通过，坏形态/非strict才拒。 |
| F5/F6 | compiler与能力边界不改，源码未实施coproduct_ignore_tier；设计登记不等于授权，保持已关闭/未实施范围。 |
| F7 采纳总裁定 | 化学零新增阻塞意见采信到源码互证范围；不能据此代替金额程序审。请求头文件清单与git构成不一致属实：fecb有8源文件，未改builder；b502另加recorded注释。 |

独立 src+scripts AST 盘点唯一配对活动调用 `evaluation.py:2304`，定义 `:1937`。入门锁计数增强合理。P2词句可随新登记，但其未来设计细则不成为本轮新增门。

## 6. 源码构成与红线核验

fecb00055：8源文件 `{adapters/rate_gate,llm_client; pollutant/evaluation,s5b_scoring,s5b_orchestrator,s5b_cli,s5b_worker,real_model}.py`、2新测试+wv6升级、1新交付书。b502b75仅recorded_source注释。actualgit差异/编号源码和完整AST比较封包。

冻结文件/记录/path_context 在 0c6、fecb、b502 与工作树均逐字节一致：

- `7fd35aabdb4d2d5b67b0bf58693dab6f8765ad872efedf5f886503c4907064e4`
- `6e046e2970a102c63e693cebb81f2564b5d79fea1b6e7a776b0fc00c09662610`
- `971ad00f42fc56915bad3724300759aa86552bf08199f8335c7f0286b40d588d`

evaluation既存函数仅 validate/evaluate入口有语义AST变化，scoring仅score入口变；匹配/排序helper全部保持。runflow/store既存函数AST相同；未改(created_at,event_id)、S5B_PASS_LINES或科学匹配尺子。

legacy52本轮两共享adapter字节变化是事实，旧无配置分支工程保持由定向/G01验证；不能继续写52文件字节不变。新聚合为 `e4b934e9d83affbb3d5a7449d6227523c575509bd4b0b97c30091e09e669a9b0`，对照基线为 `92b6dfa6c9e4c5c7e1421e9f99be0bb894d91cbd93e53da57ab80cfdf869f247`；逐文件SHA见 `execution/legacy_identity_comparison.json`，新批用实际代码身份登记。审核只读本地git/允许文档/源码与合成程序，没有访问禁区、push、commit、外部模型或启动真实批；历史远端/push/封存文件写入行为不是本次完整审计，不作绝对背书。

## 7. chain10 六条发车清单的执行映射

本表登记职责/入口，不代表已执行真实发车准备。**目前第3条被S5B-V3-02阻塞。** 其余当日步骤由受权协调者在后续新登记执行，本审不替其读取真实资产或点火。

| 上轮清单 | 本轮映射与状态 |
|---|---|
| 1 新根/锁/完整身份 | 新登记引用最终复审HEAD、代码/vendor/资产/protocol/prompt/池/融合/排序/profile/模型/金额配置SHA；run_s5b_batch冻结参数、coord锁、run锁及run模型identity接线存在。b502/fecb不能替代后续修复HEAD。旧根只读。 |
| 2 目标/题域 | 新登记独立target主列298 strict hit@1≥119/298；H5≥150参考；旧116/128/130历史参照保留。seen298_post_hoc_repair_check / known_evidence_reconstruction，泛化pending，零dev外推。 |
| 3 参数+金额机器生效 | depth1/8备选/width2/1logical/format0/retries4/workers与在途40/RPM180/TPM2.7M/HTTP1490分别冻结；CLI budget生成机器配置、worker/gate接线已在。**部分usage/429/存储派生首消费未闭合，不能勾完成**。修完后以public控制和新configSHA证明发送前60帽，再核真实输入/计费输出界。 |
| 4 当日qid/题源SHA/配对全集 | 当日权威资产/298唯一qid/预测白名单隔离由受权数据通道核；score scope门与basis门已通过。新登记插以下原文并全文SHA封包，读取源码和正负控方向核对。未访问真实gold，不伪签已核。 |
| 5 正式前缀10 | 同新批/同身份/同分母固定前10题，只看运行完整性/费用，不看gold调参、不重采样；身份变则停批新登记。当前未执行。 |
| 6 终态/封存/零模型评分 | 298全留分母，预算/unknown/失败不豁免；请求/usage/未知借记/价格/账单对账后封存，零LLM score，主/老/any-of/各K联合表/U-H5-L与全部批披露。当前未执行，不认证科学结果。 |

**§9-④ 新登记待插原文（满足r29 F4义务）：**

> 现行真实批配对采用整批二档；`data_scope=real` 时禁止根身份回退的守卫触发 ⇔ `manifest_qids` 与 `export_qids` 皆空。判分前须核注册图集合非空、`bases_by_graph` 键集精确覆盖注册图且值全为 `qid_strict`，任一缺失、额外键、坏类型或非 strict 即阻断。本门只核配对档位与覆盖，不核 qid↔图映射正确性，映射由评测器权威链负责。若配对档改为逐图混合，§9-④、evaluation-5 守卫与判分门须同步改为逐图判定，不得沿用整批判。

执行步骤：受权协调者将该原文加入**新**发车登记，不改旧冻结稿；读回确认原文在位、方向与 `evaluation.py:2316-2340` 和 `s5b_scoring.py:338-399` 相同；合法全strict通过、空/缺/foreign/non-strict拒的证据挂登记；计算新登记全文SHA，连金额configSHA/实际部署代码身份纳发车证据。未完成读回和封SHA之前，只能写“待落字”。本报告提供原文不等于登记已经完成。

## 8. 下一轮有限回修提示词

你在 `/Volumes/CC/Enzyme_Agent/dependingv43` 修唯一残余 **S5B-V3-02**。必读AGENTS、本报告§4/7、上轮主审报告§4.2/8、R1交付；基线 `b502b75c267842caa109ec8bb6735b5a0555584a`。保持S5B-V3-01关闭及合法real/synthetic/缺省、basis全集正负控，不重开化学供给/提交序/S3/S4，不实施V4/E，不改冻结判据/scorer匹配排序，不读真实题面/金标/封存逐题run，不push、不自行真批或调用模型。

入口先列后修，范围限三个已证子案：

1. **usage完整性**：缺轴不补0。完整合法计费拆分含明确0可结算；合法总计保守路径保留；一轴缺席且无可核总计，可能已付预留保持。公开client/worker的prompt-only、output-only、空、完整、显式0、total-only、重复回执逐案；部分usage不得继续靠退款挤出第二次发送，合法低费用仍可发。
2. **429保留**：无usage/未计费依据按未知保守借记；槽位释放/冷却/HTTP有界重试/HTTP数量不退保持；重试每次先预留，没钱先拒。含bodyusage的429不得被忽略后无依据归零；若实现读取完整usage须按同源完整性结算，否则保守保留。本次无需联网建立provider退款政策。
3. **stored配置首消费**：恢复金额冻结块的派生bound/hash对照core同源重算；acquire临界区验证并消费同一规范对象。身份摘要正确不能洗存储坏字段。复现worker合法bound>.001帽但存储bound=.000001的案：先结构化拒/零发送，坏形态保全；存储hash坏/缺派生/正常新建/同值恢复/合法幂等、两进程竞争保持。builder raw core的合法派生入口和stored恢复入口区分，避免全面拒绝替代校验。

复用本轮专项脚本复制fresh tmp；实际源码/vendor/metadata同根，depending43 -B/pytest cacheoff，不在永久证据建库。提交前公开worker→adapter→client→gate合成端到端及双进程budget控制，保留unknown/预算终态留分母；当前+直接父同字节红绿逐nodeid按行为/拒绝类型/拒因顺序/字段/collection如实分类，不写47旧放行翻转。PPV1/G01安全隔离口径、缺席逐nodeid、输入SHA前后、完整argv/env/exit/stdout/stderr/输入输出与嵌套manifest SHA。准备事件不删。

文稿同步：修正R1父红标签、429“不计费”未确认声明、存储摘要与首消费范围；§9-④原文在新登记核对，不静默改旧稿。新金额语义/契约/代码身份按既有规范登记新批，由主会话复核→规则级mimo→正链有限复审；本轮报告不代替放行。

## 9. 证据与复核入口

报告：`/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S5B_HIT50_V3_R1_CODEX_REVIEW_2026-10-10.md`。

永久证据：`/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/ppv1_v3r1_codex_2026-10-10/`。

- `execution/`：230/G01/父完整日志、逐nodeid分类/缺席、源代码/资产准入SHA、冻结三hash/匹配排序AST/legacy52事实。父源副本来自git对象，不改仓.git/worktrees。
- `scope/`：逐字节旧probe19+新31/7断言、合法真实/合成/省略控制、basis模拟边界、b502与mimo F1-F7互证/§9-④原文。
- `budget/`：10client/4worker/barrier、完整机器配置/合成gate/case/run_identity/输出、counterexample原输入、实际行号、91输入前后SHA；21假传输非真实计费。
- `root_audit/`：156初始输入和7550旧证据只读保护、实际commit构成/源码编号/三冻结SHA/既存函数比较、封包复核/发布前后工作树收据。

根manifest/SHA只排根两控制文件，子包manifest与清单、nested合成artifact控制纳外层哈希；报告SHA单独封包。SQLite/pyc不归档，省略逐路径/原因与合成表JSON明示。探针复跑先复制新tmp，不在永久目录原地写库/费用gate。来源声明、独立执行、模拟producer和真实公开链分别登记；不认证评审独立性、历史真实账单、性能或推广能力。

## 附：安全G01缺席逐nodeid

以下为真实skip原因，不补读红线依赖。

| nodeid | 原因 |
|---|---|
| `tests/test_analog_assets.py::test_row_counts_match_v4_parser` | v4 对照代码根不可用:/private/tmp/ppv1_v3r1_execution.trnjb2l7/g01/dependingv4 |
| `tests/test_analog_v2_corpus.py::test_v2_selected_and_remapped_rows_decidable` | v2 provenance 未生成 |
| `tests/test_analog_v2_corpus.py::test_v2_line_level_one_to_one_and_duplicate_ids_recorded` | v2 summary 未生成 |
| `tests/test_batch_runner.py::test_input_manifest_whitelist_from_frozen_v3` | v3 冻结基准不可用 |
| `tests/test_ppv1_s5a_rework_r2.py::test_s5a_r2_contract_version_registration_and_frozen_integrity` | frozen criteria text not copied into allowlisted isolation trees (G01 boundary); byte integrity verified at the evidence level (shasum in review_evidence package) |
| `tests/test_ppv1_s5a_rework_r3.py::test_s5a_r3_contract_version_registration_and_frozen_integrity` | frozen criteria text not copied into allowlisted isolation trees (G01 boundary); byte integrity verified at the evidence level (shasum in review_evidence package) |
| `tests/test_score_report.py::test_frozen_evaluator_cli_really_runs_dev` | v3 冻结基准不可用 |
| `tests/test_score_report.py::test_evaluator_refusal_on_wrong_split` | v3 冻结基准不可用 |
| `tests/test_score_report.py::test_evaluator_refusal_on_missing_lines` | v3 冻结基准不可用 |
| `tests/test_score_report.py::test_diagnose_route_buckets` | v3 冻结基准不可用 |

以下17个nodeid按安全controller的筛选/deselect口径排除，不记为通过：

- `tests/test_export_v3.py::test_charge_fixture_cn_hits_raw_sb_misses_neutralization_forbidden`
- `tests/test_asset_root_isolation.py::test_engine_load_isolation_and_reinit`
- `tests/test_cli_workflow.py::test_real_run_inspect_resume_smoke`
- `tests/test_domain_identity.py::test_identity_parity_with_frozen_engine`
- `tests/test_engine_asset_parity.py::test_all_fixtures_parity`
- `tests/test_engine_asset_parity.py::test_parity_covers_required_categories`
- `tests/test_engine_asset_parity.py::test_arms_ran_on_expected_roots`
- `tests/test_engine_asset_parity.py::test_same_runtime_failure_on_valid_fixture_fails`
- `tests/test_engine_asset_parity.py::test_runtime_failure_in_one_arm_only_fails`
- `tests/test_engine_asset_parity.py::test_unparseable_passes_only_with_expected_error`
- `tests/test_engine_asset_parity.py::test_category_and_count_expectations_enforced_against_actual_candidates`
- `tests/test_engine_asset_parity.py::test_missing_fixtures_in_both_arms_fail`
- `tests/test_engine_asset_parity.py::test_duplicate_and_unexpected_result_names_fail`
- `tests/test_engine_asset_parity.py::test_real_comparison_reports_found_categories`
- `tests/test_finder_real.py::test_real_engine_catechol_recorded_evidences`
- `tests/test_prediction_real.py::test_real_catechol_rank_candidates_smoke`
- `tests/test_prediction_real.py::test_real_donor_recovery_attempt_recorded`

准备/证据事件：scope副本初次找仓根独立vendor目录不存在，未执行任何业务probe；改为源码内vendored树后首probe完成，原失败保存。本轮不重跑已绿suite，不移植上一任务的账号中断事件；root只读audit和封包验证首执行成功。全部脚本执行环境/退出码及复现辅助脚本是否实际执行，在子包各自明示。
