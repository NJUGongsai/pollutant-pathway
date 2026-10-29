# PPV1 S5b HIT50 v3 正链复审、launch/runtime 补审与 chain10 发车裁定

日期：2026-10-10（Asia/Shanghai）。身份：正链 Codex 主评审；三个本地审核分支的程序证据经主审读取、哈希复核后采信。没有调用 mimo、其他外部模型或真实服务商。

## 1. 编号结论与固定验收范围

**本轮整体不通过，chain10 暂不放行。P1=[S5B-V3-01, S5B-V3-02]。** 已证的提交顺序、recorded 有界编译和元素前置门保持通过；不因为实际恢复数量小、科学目标尚未实现或没有开发集而另加阻塞。修复范围仅限第 4 节两项与第 8 节同门控制，不重开化学判据、历史分数或已关闭组。

| 编号 | 正式裁定 |
|---|---|
| A1 | W-V1 设计成立，独立正负控通过。事务内时间分配兑现已有调度序；scorer 排序函数未改。仅保证成功的新入队顺序，不能把并发锁失败说成成功写入，也不回写旧行。 |
| A2 | W-V2 工程面通过；4/228 恢复是交付方测量声明，本审不访问封存逐题 run 复算。恢复少本身可接受，不能承诺新增命中或达到 119。stereo/charge 能力边界须按实际检测范围披露。 |
| A3 | W-V3 前置必要条件门成立，合成公共链保持；本轮不换装语料、不开新阈值合理。其效益主要是减少无效编译，不能直接算新增候选或命中。 |
| A4 | W-V6 原任务三件已落代码；真实档程序门仍有输入范围缺口，见 S5B-V3-01。mimo 空 basis 建议在模拟评测产物下成立，但未证明当前正常 evaluator 可产生该形态。 |
| B1 | 非空 `Real`/未知文字已拒，mimo 的疑问不能照抄为漏洞；显式空串/None/False/0 公开可接受、绕过 real 门，确认为发车前 P1。空 basis/缺键控制同门补齐，但单独不冒称当前正常链已错误判分。 |
| B2 | 集合/多重集、核档位不独立核映射、触发条件同步、入口锁测试精度列 P2；下一小修/新发车登记落字，不改冻结尺子。V4 T1′和消解设计未获本报告实施或启用授权。 |
| C1 | launch 原 L01/L02 经 b636f43 及当前 HEAD 的回归/源码互证，保持关闭。runtime 的假传输接线、编排、恢复、判分接口可采信到本轮合成证据；真实并发/账单/历史分数不由这些测试背书。 |
| C2 | runtime 缺金额发送前守卫是新任务明确硬帽义务的现实缺口，确认为 S5B-V3-02；不能拿初版“费用不设上限”抵消本次单批 60 CNY 约束。 |
| D1 | chain10 暂不发车。两 P1 清零后走有限复审、新登记、前缀 10 题，再按同身份续批；目标主列固定为 298 题域 strict hit@1≥119/298，hit@5≥150/298 只作参考。 |
| E1 | 本次父→HEAD 的冻结正文、FREEZE_RECORD、path_context 逐字节相同；核心排序/提交函数去 docstring 的 AST 相同。没有发现本轮修改评分排序规则的证据。历史封存目录写入或 push 的完整行为日志未审，不能作绝对背书；本审没有触碰、push 或启动真实批。 |

实际 HEAD：`0c6e45d074d55ba14b5db7926cebb3f4141013a7`；直接父：`35727eb2b5f548d07755430ad6d5f59fbb429b5c`。不能把 a399d6e、b636f43 或 efefb20 当成本轮直接父。初始工作树的既有未跟踪资料保留，既有源码和文档不改。

验收材料为本轮任务书 W-V0/1/2/3/6 与 §3、交付书、尸检/登记指定文档、mimo r28、交接书 §5.1 及挂账 launch/runtime 交付。真实题面、金标、封存逐题 run 和原 v3 评价资产不读；只用自行构造的规则级分子与假响应。W-V0 的真实 295/298、反事实 73/98/100 等仅登记来源，不复制其逐题材料，不伪称独立复算。

## 2. 独立执行数字、红绿分类与缺席

| 执行面 | 本轮独立结果 | 精度与证据 |
|---|---|---|
| 当前安全 G01 | **1823 passed / 10 skipped / 17 deselected，exit 0** | 323 个准入输入，前后 SHA 零失配；见 `execution_order/g01/`、allowlists 与 input postcheck。历史 307 是旧 launch 谱系数字，不是本轮输入数。 |
| G01 内 PPV1 子集 | **1220 passed / 2 skipped** | 两项冻结 docs 白名单缺席控制，已按 nodeid 披露。不是“独立完整 PPV1 零 skip”。 |
| 当前定向九个 S5b 文件 | **103 passed，exit 0** | G01 的子集，不与 1823 相加。包含四个新文件和已有 W0–W7。 |
| 直接父同字节四新文件 | **13 failed / 4 passed / 1 collection error** | `--continue-on-collection-errors`；WV3 顶层导入父版本不存在的 `template_elements_fit`，该模块 4 用例未执行。不能写 17 个全行为红。 |
| 父 13 失败细分 | **10 行为 + 1 拒因 kind 差异 + 2 字段缺失** | 该 kind 案父/子都拒；字段案分别 `n_bond_diff` KeyError、已拒之后缺 `trigger_equivalence`。逐 nodeid 在 `parent_failure_classification.json`，不将字段或 collection 算行为。 |
| W-V1 独立附加控制 | 同微秒、时钟后退/前进、幂等不读 clock、新 Ledger 恢复、跨 run、旧秒行、blocked 幂等、双进程 barrier 全部保持 | 两进程同钟成功写入 8 行，时间全部互异；事务 SQL 与公开链产物留档。 |
| runtime/W-V6/L01 | **31 个不同 nodeid 最终通过** | 首轮 24 passed/7 资产依赖失败；补安全准入普通检索资产后只续 7 passed，不重复旧绿。此前缺 helper 的 collection 失败也保留。与 G01 有覆盖重叠，不加总。 |
| 化学供给专项 | **16 个合成观测 + 3 条公开链** | 3 条链各 1 event，全部 `retain_conditional`；完整组分保持，不声称 verified/full/R6。 |
| scope/basis 专项 | **19 个观测=13 公开 score 调用+6 模拟 evaluator 产物** | 包含漏洞与拒绝控制，不能写 19 项验收全通过。13 案仅将文档批准来源固定为缺席输入，evaluator/score 本体未替换；6 案另行替换产物，严格分开。 |
| 费用专项 | **3 个控制** | 61.6 CNY 合成 summary 后仍可两次假传输发送；HTTP 额度 0 拒。真实客户端和 gate，urllib 假传输；网络/费用均 0，未冒称真实账单或完整 PPV1 请求生命周期。 |

交付“全量 1834 passed/0 failed/16 deselected”与主会话本机复跑作为**他方来源声明**登记。本审没有在真实仓树跑 `tests/` 全量；它与安全 G01 的筛选、题域资产缺席不同，不能因数字相近而称已独立互证全量。G01 和定向的完整 stdout/stderr/JUnit/argv/env/exit 均封包；永久证据是读取和复验入口，写库脚本必须再复制到 fresh tmp 执行。

10 个 skip、17 个 deselected 逐 nodeid 与实际原因在安全 G01 的 observer/缺席表中；不省略为“环境问题若干”。准入树不含真实金标/题面/封存 run。隔离树中的子进程生成了 7 个 pyc，已逐路径登记并排出永久包；父进程 `-B`、PYTHONDONTWRITEBYTECODE 与 pytest cacheoff 保持，没有将例外涂成零缓存。

## 3. A：v3 工程验收与证明范围

### 3.1 W-V1：修生产提交序，不改评分顺序

`search.py:707-747` 的 `_next_action_created_at` 消费当前 run 已落账 `MAX(created_at)`，时间不前进就加 1µs；`:751-758` 的 `BEGIN IMMEDIATE` 串行化写事务。普通 enqueue `:954-986` 与 blocked 入队 `:1199-1230` 的新插入均在事务内分配；同键同载荷 `:967-971/:1211-1214` unchanged 直接回滚返回，不重排旧动作，也不让重启重写它的时间。

成功提交的 MAX→INSERT 不存在并发成功写入同时间的正常窗口；双进程同钟 8 行反例实测互异。进程锁是生产单驱动纪律，SQLite 写事务又闭合了存储分配；事务占用失败仍可能结构化 busy，不能报告为成功。交付对“极限并发退化 tie-break”的说法宜更正：现有成功写入路径保证同 run 严格时间；成功前失败、旧行或损坏不属于这份保证。

时钟后退、同微秒、旧秒行、新 Ledger floor、跨 run 不共用 floor、blocked 与正常动作交叉、unchanged 不读 clock 都有独立控制。公开合成链的执行/事件/导出保持已排定序。`_inflight_action_ids`、`drive`、`_main_caliber_row`、`store.submit_event` 去 docstring AST 父子相同；事件仍按既有 `(created_at,event_id)` 评分。没有将 eff_rank 混入 scorer，也没有按金标重排候选。

限制：不迁移历史记录；同 run 并发两生产者的到达先后只保证落账顺序，不证明模型置信排序；created_at 在本契约承载提交序，时钟后退时不应解释成精确物理墙钟。正常公开 flow 沿冻结顺序入队，单驱动保持，才能叫“调度序贯彻提交序”。新批登记必须记 `s5b-submit-order-1`、实际代码身份和冻结池/排序参数，不把此政策后补到旧批。

### 3.2 W-V2：保留原子覆盖，有界搜索，完整产物守门

`recorded_source.py:173-239/:345-348` 标准枚举无解才放松 donor 最多两条键，元素与全部 donor 原子覆盖仍保留；512 次查询/200 像边界和触顶拒见 `:488-496`。`:499-574` 多候选进入共同 compiler，执行完整严格产物**多重集**与原记录核对。保留原子之间的新成键不再因“无新增原子”被跳过，按公共工具执行。

独立重排、水解、标准路径、重复产物、缺元素、过滤缺产物、歧义、触顶控制成立；公开 recorded 重排/水解各 1 event。记录系数缺来源仍 unknown；推断 mapping、不完整条件/机制的证明范围没有升级。此机制证明指定库记录的净产物可复现，不证明反应机制、生物适用性或完整化学计量。

4/228、47/116 及真实直方图是交付来源声明，本审不取真实原记录复算。恢复少是诚实工程结果，本任务没有冻结“必须恢复 N 条”门；无法恢复仍 unsupported 不是自动阻塞。但交付 §5.1 分类有文字算术不闭合：前三“修”类合计 50，另 15 水解也写“本轮修”；明确元素缺席为 9+29=38，其余 6+7=13，不能直接背书摘要 50/44/22。应补分类定义、层级与互斥计数，不能在报告里编造归并规则。

“恰一可复现”也不精确：源码 `:546-551` 取可复现的首项，等价目标可有多个。应写“至少一可复现、同严格多重集合并、确定性选首”，不修改既有算法来迁就措辞。

### 3.3 W-V3：只前置必要条件；不把优化算供给

`s5b_compiler.py:92-117` 比较 lhs 元素多重集是否为底物子集，坏解析交回 compiler；它是已有完整对齐的必要条件预筛，不是额外化学判据或最终许可。`s5b_builder.py:494-520` 不满足时仍记 no_alignment，并披露 `analog_pregate_skipped`，不占池槽。

独立 Br 缺席/Cl 合法混池：坏模板编译调用 0，好模板 1；公开 analogy 去氯保留主产物及离去 Cl，1 event/retain_conditional。单测与源码共同支持“减少不必要编译”，不支持“这 1829 个噪声变成新增供给”。3821/1946/1829、76<84、≤7/24 等真实聚合仅来源登记。无授权独立开发集时维持阈值/池宽；语料不换装可接受，不据此认证其真实全域资产质量。

### 3.4 stereo/charge、V4 与设计意见

维持未授权能力边界合理，不能用全面拒绝替代正控，也不能夸大为所有 stereo 都检出。`s5b_compiler.py:230-237/:270-275/:381-395` 对形式电荷和原子 chiral tag 的变化明确 unsupported；独立控制确认。**E/Z 盲区实测成立**：只变 E/Z 被 transform_no_change；E/Z 与另一合法变阶同现可 compiled，目标保留原 E/Z，不吻合 rhs 的新 E/Z。当前 compiled 不等于完整源模板立体变化已兑现；该案属于既有、已披露、未授权升级边界，本轮未出现据此授新完整源证明的证据，不单凭支持缺口升级 P1。

mimo E1–E3 与 T1′只是规则级设计意见，不是实现证书。消解须另批证明执行后确实不再为立体中心、rhs 无手性声明、仍有中心/新建中心不放行、执行后 rhs 立体同源复核与机器诊断；E/Z、非四面体等未支持范围明确。不能从“发生变阶”推出全部立体都能消解。

V4 当前仅请求稿，没有启用 `coproduct_ignore_tier`。T0 headline 保持；T1′九条件包括仅 product 方向、反应物 H2O 独立特例、来源元素追溯、O2 不忽略、I-/CO3 的边界、CN/SCN/H2O2/NH2OH/NO 等排除、版本+白名单 SHA+方向+追溯开关四元组、角色标签不作许可、post-hoc/纯位次与新增覆盖分别报告。用户/teacher 如裁定，走独立新预注册字段，不升本批 partial、不回填旧分数；本报告不代做裁定。

## 4. 阻塞 P1：具体公开证据与最低收口

### 4.1 S5B-V3-01：显式坏 data_scope 被洗为 synthetic，真实档两门不消费

对应既定验收：launch L01 真实身份边界、W-V6 §9-4 判分前守卫、mimo r28 D1 的 data_scope 白名单建议。源码 `evaluation.py:387-388` 用 `get(...) or synthetic_rule_level`，`:2084` 与 `s5b_scoring.py:209/:292` 只在值恰等于 real 时执行真实批准/配对门；`:271` 把原值送评测器。

公开 score 的显式 `''/None/False/0` 各带批准/缺批准形状，共 8 个接受，metrics 原样保留非法值并写入，real 门跳过。为构造未批准输入，仅替代文档批准读取器使其返回缺席，不替代 evaluator/分类/score 本体；不拿当前仓已 confirmed 的用户稿冒充未批准。非空 `Real`/`typo_unknown` 明确被白名单拒，mimo 对这两类未知值的疑问不成立，须更正。

这是消费侧域身份缺口，CLI choices 不能覆盖可调用的公开 API。没有真实数据外发、真实题面或非法批准事故发生的推断，只确认同一公开消费链能接受非法域标识并绕过相应规则。

最低收口：公开 score 入口严格字符串 enum，显式空/null/bool/数值/未知值先结构化拒；不动完全省略 score 参数的既有 real 默认。evaluation 对显式提供的坏值不可用 truthiness 洗成 synthetic；如历史 schema 允许**字段完全缺省**，保留且明确机读归一来源，不能把缺省与坏值混为一类。所有适用 build/validate/evaluate/score 首消费同源处理，合法 synthetic 回退、合法 real qid_strict、真实无导出未命中和 real 未批准拒正负控保持。

同门补充：6 个模拟 evaluator 产物中，缺 coverage/缺 bases/空 bases/只有 foreign strict key 均被 scorer 接受；合法 basis 接受、非 strict 拒且零 metrics。**真实当前 evaluator 即使无导出仍给非空 qid_strict，尚未证明坏产物正常可达**，不另报成真实 298 错分 P1。既然门自称独立复核，建议本次同门小修要求 expected graphIds 非空、basis 字典类型与键集合精确覆盖注册图、值全 qid_strict，缺失/额外键先拒；注明其只核档位/覆盖，映射正确性仍由 evaluator 权威链负责。对此补充不改 scorer 匹配算法或 qid 配对策略。

### 4.2 S5B-V3-02：60 CNY 只有估算和事后小计，没有发送前硬帽

对应既定验收：v3 任务 §3 `:241` 硬帽 60 CNY，继承 v2 任务 `:229-232` 明确“预算/总 HTTP/输出上限及未知 usage 保守预留真正先于 send”，复测登记 `:63-65` 同样声明。初版费用不设上限是历史用户偏好，不能取消这次单批冻结帽。

`s5b_orchestrator.py:614-642` 仅按 case 已知 usage 与价格快照事后算 cost_known；“usage 缺失保守预留”写在 note，未形成发送许可。`adapters/rate_gate.py:241-280` 原子消费请求数、RPM/TPM 与在途槽，无金额/价格/输出界状态；`adapters/llm_client.py:341` 默认请求体无输出 token 上界；`real_model.py:609` 接线没有补金额闸门。

独立合成合法 case 的 public summarize_batch 小计为 **61.6 CNY** 后，同批 public FileRateGate + OpenAICompatibleClient.complete 仍连续发送两次；urllib 全假传输，返回 usage={}，gate 未产生金额预留，token_events 也空。HTTP max_calls=0 负控在传输前拒。这是发送前金额机制缺席的执行互证，不是真实账单、不是完整 PPV1 生命周期复现，更不是声称已发生真实超支。

1490 是 HTTP 请求尝试上限，1 logical 是每题的逻辑请求资源，均不能由历史平均 tokens 保证 ≤60。40 在途若只有事后查看费用，停止前已发送的请求仍可能计费，不能称硬帽。

最低收口：同日价格与计费口径/输入保守界/可核输出上限冻结入新机器配置与身份；每个可能付费的发送尝试之前，共享批级原子预留，已知借记+在途预留+缺 usage 未结算预留不超过 60 才发。失败/超时/未知 usage/孤儿不得因“没有返回 tokens”释放可能已付金额；恢复/重复回执不得重退或重扣；HTTP retry 同样先预留，保持 1490 HTTP/1 logical/format0/40 在途其他门。无法确定上界就保守阻断/早停，不自动提高帽。

所需合成控制：零/不足预算零发送、恰好额度、已知超帽、两进程 barrier 抢最后额度、未知 usage、重试/崩溃恢复/幂等结算；公开 adapter/worker 消费该守卫，不能只测独立 helper。价格或输出配置坏/缺先拒；合法低成本请求与预算导致未作答留分母保持。无需真实模型或真实账单来实现工程守卫。

## 5. B：mimo r28 逐项互证与非阻塞项

| r28 项 | 正链互证与处置 |
|---|---|
| D1 §9-4 空集/键缺失 | 模拟 evaluator 产物可复现；当前正常 evaluator 可达性未证。与 S5B-V3-01 同门补 shape/全集负控，不当作真实错分已发生。 |
| D1 data_scope 白名单 | 非空错误字串已拒；显式 falsy 类型真实 API 接受，P1 成立，见 §4.1。 |
| D1 “核档位，不核映射” | P2 文字精度，下一小修/登记落字。门不替代 source/reference 绑定，也不证明 qid 真值。 |
| D2 唯一消费入口锁 | 独立 AST 盘点 src+scripts，当前唯一活动调用 `evaluation.py:2212`，定义 `:1850`，没有发现第二 caller。原锁只扫 src、整行前缀豁免可能让未来相同写法漏计，P2 测试增强；改 count/AST 并明写定义域，不据假设报现有绕过。 |
| D3 触发等价 | L01 代码/detail 已写“两 qid 映射皆空”；预注册 §9-4 同步句随新登记，不混淆全局档位与将来逐图混合。P2。 |
| A5 集合/多重集 | `evaluation.py:945-948/:975-981` 是参与物 state_ref 集合；`recorded_source.py:539-574` 与 compiler 槽去重是严格多重集。两种合同分别写真；本轮选择订正文稿为现有 evaluation 集合语义，禁止静默改冻结判据为 multiset。 |
| A–C T1′九条件 | 设计有条件意见，未执行新 tier；由 user/teacher 另裁定。各物质/机制一般性断言不由本轮合成输出证明。 |
| E1–E3 消解/E/Z | 设计未实施；E/Z 检测盲区独立实测成立。披露实际检测范围，另批申请窄能力与执行后诊断，不泛化为全部立体。 |

P2 清单：父红分类订正；§5.1 类别定义与算术；“恰一可复现”修词；成功入队并发保证与失败边界；上述入口锁和档位 note；实际 stereo 检测面；新登记保持 cap/旧老口径、K 事件/字符串/提交序非模型置信序等旧精度条款。合成分子“与真实金标零重叠”没有在本轮禁金标纪律下独立验证，只记自构造合成，不背书这项声明。

## 6. C：挂账 launch/runtime 事后补审

依交接书 §5.1，本次兑现挂账补审，不将历史先跑后补审擅自改写为当时已获本审放行。实际历史提交与文件构成读取 local git：a399d6e launch、b636f43 回修、efefb20 runtime；本次行为裁定以 0c6e45d 为准。

**C1：launch L01/L02 关闭保持。** 当前 evaluation 首消费 real fallback 拒与合法 synthetic/real qid、缺配未命中等控制成立，qid 不因根身份相同串题。b636f43 文档修正了 flatten/fusion、report_rank=None、老整串 any-one 与新四轴/必要参与物区别、逐 K 非单调、CI/重复组暴露与旧口径不升格。已读 scorer v2 的来源为仓内 `exam_v2.py` 源码，不读取原 v3 评价资产或旧真实答案。本轮 runtime/scoring 回归维持；不重新核 116/128/130 等历史成绩。原 L01 空映射触发合同未被重开，新增非法 scope 是不同消费形态的具体新证据。

**C2：runtime 工程接线有合成互证，金额硬帽尚未成立。** runtime、请求账本、失败补位、同批参数身份拒、已完成题 skip/恢复、Scripted adapter→production→导出→零模型 scoring 的有限接口证据可采信。31 个不同 nodeid 的最终绿不代表真实 DashScope 成功率、40 实际在途峰值、真实账单对齐或全 298 成绩。真实价格、远端权威 SHA 与发车时环境由受权协调者再核，本审不访问这些资产。审批早期“任意非 pending 即批准”的宽文本属于历史旧说明，当前代码与回归按已闭合白名单，不重新以旧句升级问题。

**C3：legacy 身份需分时期披露。** 本轮父/子 legacy 52 文件聚合均为 `92b6dfa6c9e4c5c7e1421e9f99be0bb894d91cbd93e53da57ab80cfdf869f247`。不是 S5a 旧 `18007e6a…` 一直未变。source history 指向 `atom_tool.py` 的 57ea99b smoke-fix，`llm_client.py/rate_gate.py/domain/models.py` 的 35727eb HIT50 W0–W7。V3 这次没有再次改变这 52 文件；挂账 runtime 的接线和后续 W0–W7 已产生历史变化，必须用新代码身份登记，不能说“从 launch 以来 legacy 全字节零变化”。安全 G01 是当前工程回归，不认证旧环境科学分数或所有历史行为完全相同。

历史义务保留：真实结果的后置化学复核、全部批/失败/成本披露、seen298 自适应评测定位、known_gaps 不豁免分母。r28 是规则设计与采纳核对，不自动代替每个真实结果的第三触发点。

## 7. D/E：chain10 与红线裁定

**chain10 不放行原因只有 §4 两项；目标可能达不到不是新增工程阻塞。** W-V1 修位次、W-V2 有限新增、W-V3 主要降噪，不能把已有供给不足转述成“测试全绿必达 119”。W-V0 反事实所述约 73 H1 与 U=100 是旧候选固定集合诊断来源；不说明新模型响应/新批一定如此，不当 oracle 调度，更不改变评分尺子。当前科学状态仍 `scientific_target_pending`，不把 v3 工程收益认证为指标达标。

两 P1 关闭后，发车前清单：

1. 受权协调者新登记/新根/同批锁；部署字节核到新审定 HEAD，代码/vendor/资产/protocol/prompt/池/融合/排序/profile/模型/计费配置全部冻结。禁止在旧封存批试跑或回写 created_at。
2. 主目标 **298 strict hit@1≥119/298** 单独字段；H5≥150 参考，不反向改变主目标，旧 S5B_PASS_LINES 116/128/130 保留历史含义。承认 seen298_post_hoc_repair_check / known_evidence_reconstruction，不叫独立盲测，不外推 dev。
3. depth1、8 备选、width2、1 logical/题、format0、HTTP retries4、workers/在途40、RPM180/TPM2.7M、HTTP cap1490；预算60、输出上界与同日价已机器生效。数量帽和金额帽分别验证，未知 usage 保守借记。
4. 由受权数据通道核题源/唯一298 qid/当日 SHA、预测白名单与参考隔离；本报告只登记义务，不读取权威金标或替别人签发当日核验。real 档合法值及 qid_strict 全集门先于评分聚合。
5. 正式注册前缀10题仅看链路/费用，不看金标命中挑参数或重采样；前缀纳同一298分母。若身份/模型/预算配置要变则停批另登记；不多批 best-of 拼答。
6. 所有298注册题终态、失败/unknown/预算早停留分母；完整 usage/unknown/HTTP/逻辑调用/成本对账后封存，再零 LLM score；主/老/any-of、每 K 联合表、U/H5/L 与全部批并列披露，未达标诚实交下一版，不自动机械付费循环。

红线复核：冻结正文 SHA `7fd35aabdb4d2d5b67b0bf58693dab6f8765ad872efedf5f886503c4907064e4`、FREEZE_RECORD `6e046e2970a102c63e693cebb81f2564b5d79fea1b6e7a776b0fc00c09662610`、path_context `971ad00f42fc56915bad3724300759aa86552bf08199f8335c7f0286b40d588d` 均父子相同。评分排序核心 AST 相同，source_diff 是新提交序生产/编译/预筛/守卫与文案，非旧答卷重排。实施方 no push/no旧批写入的历史行为，本次只读 git 构成与声明不足以排除仓外/远端历史操作，因此记“未发现违反证据，完整行为未确认”，不冒称全历史审计。**本审**零真实模型/网络/费用、无 push/commit/发车，不访问禁区，只新增本报告和指定证据目录。

## 8. 有限回修提示词（可直接交实施方）

你在 `/Volumes/CC/Enzyme_Agent/dependingv43` 修 PPV1 S5b v3 两项发车 P1。必读 AGENTS.md、本报告 §4/§7、本轮任务 `docs/TASK_V43_PPV1_S5B_HIT50_V3_2026-10-10.md` §3、继承任务 `docs/TASK_V43_PPV1_S5B_HIT50_UPGRADE_AND_RETEST_2026-10-09.md` §3、mimo r28 与本轮证据 README。基线 `0c6e45d074d55ba14b5db7926cebb3f4141013a7`；不读取真实题面/金标/封存逐题 run，不跑真实模型、不 push、不启动 chain10、不修改冻结判据或 scorer 匹配/排序，不回写旧批。

先列入口，后修同规则：

- **S5B-V3-01**：score 与评测首消费共用严格 data_scope 校验；显式空/null/bool/数值/未知值结构化拒，合法默认与 real/synthetic 正控保持。不要用 CLI choices 代 API 校验，也不借此重构无关 schema。对独立 basis 门同批补 expected graphIds 非空/精确键集合/类型/全 strict，缺 coverage/缺 bases/空/缺键/额外 foreign/非 strict 负控先拒零 metrics；注明模拟产物与当前真链控制差别，门只核档位与覆盖、不核映射。保持实际唯一配对消费链。文稿改“evaluation 集合、recorded 多重集”；note/trigger_equivalence/入口锁定义域可搭车，不改冻结判据。
- **S5B-V3-02**：公开实际发送链消费批级金额原子预留。冻结60CNY、当日价/计费口径/输入保守界/真实请求输出上限，余额不足或缺合法配置先于传输拒；40在途、HTTP retry、usage缺失/超时/孤儿、恢复/重复结算安全，不能退未知可能已付额度。保持HTTP1490、1logical/题、format0、40在途等其他门。双进程抢最后额度和公开adapter/worker假传输端到端，合法低费用正控保持；不凭历史均值算硬帽、不自动升帽。

交付：逐入口输入→行为→首消费→写入/传输边界矩阵，当前+直接父同字节红绿按行为/kind/字段/版本/collection分类，合法控制不退。复用本轮证据反例时复制 fresh tmp，不在永久目录建库；depending43 `-B`、cacheoff。PPV1/G01 用安全隔离口径，逐 nodeid 披露缺席与输入 SHA，不混真实仓全量声明。新证据完整 argv/env/exit/stdout/stderr/输入/输出/SHA，嵌套 manifest 纳外层哈希；准备失败如实保留。交付文案订正本轮13红+4绿+1collection、分类表定义和支持范围，真实恢复数字只以自身证据背书，不假借本审独立核验。

涉及新的费用/入口契约或语义变化按既有 identity/version 规范登记，新批机器配置能核验；只做两 P1 与同门 P2，不实施 V4/E 设计、S5科学新尺子/真实评测或语料升级。提交按仓约显式路径本地处理，由主会话核对→规则级mimo→正链有限复审；本报告不代替后续放行。

## 9. 证据入口、执行事件与可复核限度

报告：`/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S5B_HIT50_V3_CODEX_REVIEW_2026-10-10.md`。

证据：`/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/ppv1_v3_codex_2026-10-10/`。

- `execution_order/`：当前/父源码身份、隔离 controller/allowlists、103/G01/父回归完整日志、逐 nodeid 红分类/缺席、时间及双进程 SQL/公开链、52文件身份；本轮业务数字主入口。
- `gates_runtime/`：19 scope/basis观测、3费用控制、31回归续跑与初次失败、实际caller AST、公共假批产物。批准文档来源替代、评测产物替代与假网络传输边界均明示。
- `chemistry_supply/`：16合成观测+3公开链、完整产物/unknown诊断、E/Z两个观察、源代码行号、两夹具/资产事件；真实聚合未独立复算明示。
- `root_audit/`：初始HEAD/输入SHA/旧6557文件只读保护、原始git/source差异、冻结/核心AST、指定输入文档、封包复核、最终只新增两路径的工作树保护。
- 根 `manifest.json`/`SHA256SUMS`：只排根两个控制文件；子包 manifest 与其 SHA 清单作为附件纳根哈希；报告SHA另封，路径无SQLite二进制/缓存/密钥。

审核自身事件如实登记：化学首夹具 COOC 误写 COOCC 后修正；公共链首次副本缺资产，正式 scripted 参数只补未完成3链；runtime 缺 helper collection、7资产依赖失败，只续7；G01 runner 首次插件参数误放在模块名前、Python 在 pytest 前拒绝，纠正后首次实际 G01 全绿；root只读捕获误猜继承任务文件名与 verifier 只支持旧manifest的 files字段，纠正为实际名字/attachments兼容后仅重做只读封包；初始 snapshot 的验收描述误留上一轮 wording，保留原文件并用 correction明示当前scope。均不是产品通过证据，不删首失败、不反复跑已绿suite。本轮没有账号额度中断事件；历史上一任务的中断不复制成本轮事件。

放行意见只到这些本地可复核程序事实为止，不认证评审独立性、历史真实分数、零源泄漏或科学泛化。

## 附：G01 缺席逐 nodeid

这是本轮隔离执行的真实缺席，未补读缺依赖。详细 when/路径在 `execution_order/logs/g01_absences.json`。

| skip nodeid | 实际原因 |
|---|---|
| `tests/test_analog_assets.py::test_row_counts_match_v4_parser` | v4 对照代码根不可用:/private/tmp/ppv1_v3_order_execution.wxruevjg/g01/dependingv4 |
| `tests/test_analog_v2_corpus.py::test_v2_selected_and_remapped_rows_decidable` | v2 provenance 未生成 |
| `tests/test_analog_v2_corpus.py::test_v2_line_level_one_to_one_and_duplicate_ids_recorded` | v2 summary 未生成 |
| `tests/test_batch_runner.py::test_input_manifest_whitelist_from_frozen_v3` | v3 冻结基准不可用 |
| `tests/test_ppv1_s5a_rework_r2.py::test_s5a_r2_contract_version_registration_and_frozen_integrity` | frozen criteria text not copied into allowlisted isolation trees (G01 boundary); byte integrity verified at the evidence level (shasum in review_evidence package) |
| `tests/test_ppv1_s5a_rework_r3.py::test_s5a_r3_contract_version_registration_and_frozen_integrity` | frozen criteria text not copied into allowlisted isolation trees (G01 boundary); byte integrity verified at the evidence level (shasum in review_evidence package) |
| `tests/test_score_report.py::test_frozen_evaluator_cli_really_runs_dev` | v3 冻结基准不可用 |
| `tests/test_score_report.py::test_evaluator_refusal_on_wrong_split` | v3 冻结基准不可用 |
| `tests/test_score_report.py::test_evaluator_refusal_on_missing_lines` | v3 冻结基准不可用 |
| `tests/test_score_report.py::test_diagnose_route_buckets` | v3 冻结基准不可用 |

以下 17 nodeid 在安全隔离筛选中排除（详见 controller -k 口径，不登记为通过）：

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
