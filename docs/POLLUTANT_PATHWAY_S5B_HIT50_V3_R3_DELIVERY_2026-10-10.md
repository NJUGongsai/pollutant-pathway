# PPV1 S5b HIT50 v3 回修轮 R3 交付书(S5B-V3-02 两同规则残余 A'/C',2026-10-10)

状态:`implementation_ready_for_review`(本轮零真实模型调用、零花费、
不 push、不启动 chain10、不改冻结判据与 scorer 匹配/排序、不回写旧批、
S5B-V3-01 保持关闭零回退)。

依据:R2 正链复审报告
`docs/POLLUTANT_PATHWAY_S5B_HIT50_V3_R2_CODEX_REVIEW_2026-10-10.md`
§4.1(A' 自矛盾总计被当合法可核总计)/§4.2(C' 已启用金额帽整块缺失
被当 legacy 未启用)/§5/§7/§8 有限回修提示词(权威);R1 正链复审
§4.2/§4.4 最低收口原文;R2 交付书
`docs/POLLUTANT_PATHWAY_S5B_HIT50_V3_R2_DELIVERY_2026-10-10.md`。
基线 HEAD `d08432c6014ec476436df0b85765058e43464ffa`(直接父;红绿
基线)。范围限两条同规则残余;B 保守 429、原 prompt/output 缺轴不补 0、
原坏派生字段首消费拒保持零回退;不重开 S5B-V3-01/化学供给/提交序/
S3/S4/历史 launch;不实施 V4/E;不读真实题面/金标/封存逐题 run;不调
模型;不自行真批。

本轮源码改动**唯一文件** = `src/pathway_v43/adapters/rate_gate.py`
(llm_client.py / s5b_worker.py / 全部既有测试零字节改动:client 的
summary 首消费与 retry acquire 的 GateCorrupt→budget_config_invalid
映射、worker 装配期 GateCorrupt→budget_guard_invalid 捕获均是 R2 已
闭合的既有通路,本轮四入口在闸门侧收口后直接复用)。

## 一、两残余修法(一句话)与适用入口矩阵

**残余 A'(合法总计回退)**:重写 `_cost_of_usage` 的 total 回退分支
—— 两轴不齐而走总计口径前**先核已知有效轴下界**(`total ≥ 同一 usage
的已知有效轴之和`,仅显式存在且有效的轴计入;坏类型/负数轴不可用不
计入),内部自矛盾(如 prompt=900 而 total=1)⇒ `None` 不可计,预留
按未知保守保留,不当"合法可核总计"低额结清未知费用;通过下界 ⇒ 既有
保守总计口径(全额较贵单价)不变。完整双轴(两轴显式有效,含明确 0)
仍精确结算,**冗余矛盾 total 不参与该分支**(完整双轴的冗余矛盾 total
与缺轴回退分开处理,不全面拒绝替代安全规则)。

**残余 C'(已启用配置存在性)**:新增闸门共用判据
`FileRateGate._cost_guard_missing_after_enabled`(证据 =
`_cost_ledger_evidence` 既存金额账本 ∨ 本进程已装配/构造配置
`self.cost_guard`;worker 冻结预算经既有 `_verify_budget_guard` 首消费
闭合)—— 四个运行中消费入口先按既有启用事实辨别"合法旧未启用"与
"已启用块消失/置空",坏形态 ⇒ GateCorrupt 结构化拒(零新发送/零新
预约、坏形态保全、第一次已发账本保守保留不删除不假退款);
`record_response` 结算临界区对该形态不结算不假退款 —— 该占位预留保守
转未结算(账本事实 bound + 结构化 note `cost_guard_block_missing_
settlement_kept`),占位/429/token 记账照常,下一次发送由 acquire 先
结构化拒。

### 适用入口矩阵(先列入口,再共用校验与消费事实)

| 入口 | 消费事实 | 共用校验 | 坏形态行为 | 位置 |
|---|---|---|---|---|
| `_load`(acquire/summary/verify_config/snapshot/cost_snapshot/reclaim 共用验证源) | 状态文件 raw `cost_guard` 块 + 既有启用事实 | `_cost_guard_missing_after_enabled`(reject 档) | 块缺/置空+证据 ⇒ GateCorrupt(kind=cost_guard_config_invalid,reason=cost_guard_block_missing_after_enabled) | `rate_gate.py::_load` |
| `_init_state`(重开装配/worker 装配) | 状态文件(块/账本),构造参数 | 同上(账本证据优先;构造侧给了配置而既有状态无块的既有 `cost_guard_config_mismatch` 冲突分支不变) | 账本在而块缺 ⇒ 构造期 GateCorrupt | `rate_gate.py::_init_state` |
| `cost_guard_summary`(client complete 首消费/worker `_verify_budget_guard`/run 身份) | 状态文件(经 `_load` reject 档) | 同上 | 坏形态 GateCorrupt(不再返回 None 冒充未启用);None 仅余真正旧未启用 | `rate_gate.py::cost_guard_summary` |
| `acquire`(发送临界区,client retry 每次先走) | 状态文件(flock 锁内重读) | 同上(先于槽位分配) | GateCorrupt:零新预留/零新发送/拒发计数不增/不落盘;client `_gate_block` ⇒ budget_config_invalid 结构化失败 ⇒ **第二 HTTP 先拒** | `rate_gate.py::acquire` + `llm_client.complete` retry 循环 |
| `record_response`(结算临界区) | 状态文件 + usage + 占位 | 同上(**conserve 档**:不抛,占位/429/token 记账照常) | 不结算不假退款:预留保守转 unsettled(bound+note),坏形态原样保全;下一次发送先拒 | `rate_gate.py::record_response` |
| `llm_client.complete`(429/失败/成功各分支 record_response 调用) | 上述 | — | record_response 不裸抛(调用方 429 记账路径完整走完);重试的第二 HTTP 由 acquire 先拒 | `llm_client.py:394-507`(既有,零改动) |
| worker 装配(`RealModelAdapter.from_env`→`OpenAICompatibleClient`→`FileRateGate(env)`) | env `V43_LLM_RATE_GATE` → `_init_state` | 账本证据 | 装配期 GateCorrupt ⇒ `budget_guard_invalid` 失败 case(rc=5,失败题留分母,零发送) | `s5b_worker.py:106-117`(既有,零改动) |
| worker `_verify_budget_guard`(worker 冻结预算证据) | 批根 budget_guard.json ↔ `cost_guard_summary` | 既有 R2 通路 | summary 抛 GateCorrupt ⇒ budget_guard_invalid;summary None ⇒ budget_guard_missing(均先拒零发送) | `s5b_worker.py:211-286`(既有,零改动) |
| `_cost_of_usage`(经 `record_response` 唯一结算消费) | provider usage(prompt/completion/total 三轴分类) | total ≥ 已知有效轴之和下界 | 矛盾 ⇒ None 不可计(保守保留);兼容总计/完整双轴/无轴 total-only>0/显式 0/重复回执保持 | `rate_gate.py::_cost_of_usage` |

**共用校验与消费事实**(单一判据源,避免各入口各写一套):

- 证据①**既存金额账本**:`_cost_ledger_evidence(state)` —— `cost`
  块带任一账本键(settled/unsettled/reserved/send_rejections/
  reservations/overrun)。`cost` 块只与 `cost_guard` 块**同生共写**
  (`_fresh_state`/acquire/结算临界区);单独存在的账本 = 已启用守卫的
  块被移除后的残账;真正旧 dev 批状态**没有** cost 块(零金额状态,
  合法旧分支保持)。
- 证据②**已装配/构造配置**:`self.cost_guard is not None`(构造参数
  或 `_init_state` 从状态块装配;块在、后来没了 = 消失)。到达运行中
  该证据非 None 的所有路径都要求块当时在盘(构造给了配置+既有状态无
  块的冲突在 `_init_state` 先抛),因此运行中块缺 + 该证据 = 块消失,
  不是 legacy。
- 证据③**worker 冻结预算**:批根 `budget_guard.json` 经 worker 侧
  `_verify_budget_guard` ↔ `cost_guard_summary` 首消费(既有 R2 通路,
  本轮闸门侧收口后该入口对坏形态同样先拒)。
- 证明边界(如实):块+账本同时被移除且换新进程(无装配证据)⇒ 闸门
  侧无证据走旧分支,由 real 批 worker `_verify_budget_guard`
  (budget_guard_missing)兜底 —— 即 R2 报告 §4.2 原文"不要求抵抗全库
  协同改写"边界,不冒称闭合;同进程内装配证据仍先拒(有专项控制)。
- `cost_snapshot`(raw 只读披露工具)经 `_load` reject 档:对坏形态
  由返回 `{"enabled": False}` 改为抛 GateCorrupt(fail-closed 披露;
  R2 复审 §5"当前块空会披露 enabled=false,不能据此签旧未启用"的
  精度项随本轮修复自然闭合,如实登记为行为变化)。

## 二、金额语义(v3-R3 修订口径)与代码身份登记

- **结算**(R3 增量):缺轴回退走总计口径前核已知有效轴下界,自矛盾
  ⇒ None 不可计(预留保守保留);其余 R2 语义零变化(完整拆分含显式 0
  精确结算、兼容总计保守口径、缺轴不补 0、429 保守保留、孤儿/幂等/
  overrun 不回滚);
- **已启用块消失**(R3 新语义):四入口结构化拒/保守结算(见 §一);
  已发账本保守保留,不删除不假退款;结算幂等(重复回执 no-op)保持;
- **契约**:`s5b-budget-guard-1` schema、五个数值字段、`config_sha256`
  口径、CLI 幂等/改值拒、orchestrator 冻结副本零变化;**结算语义是
  代码行为**,新批登记按既有规范引用实际部署代码身份:**本提交 HEAD +
  公开函数实测 legacy 52 文件聚合
  `279d9bc19bad25e51b7c23ee276da95151a8f25cf598b9dc3642b508d817c4bb`**
  (`pathway_v43.storage.run_identity.code_identity('legacy_v43')` 排序
  k:v 换行聚合;52 文件,本轮变化文件恰 1 = rate_gate.py,逐文件 SHA
  见 `/tmp/s5b_v3r3_impl/legacy_identity_r3.json`)。R2 交付的
  `cd683e…` 聚合与公开函数不相容不能当部署身份(R2 复审 §5),已按
  其要求在本轮 R2 交付书加订正标记并用实测公开值;R1/R2 语义批按其
  当时代码身份解读,不回写,不静默改旧 429 账;
- **不变面**:TPM 滑窗/429 冷却/HTTP max_calls/40 在途/1 logical/
  format0/RPM 全部不动(r1/r2 既有控制 47 用例全绿在案)。

## 三、逐案控制清单结果(`tests/test_ppv1_s5b_hit50_v3r3_cost.py`,
25 用例全绿;全部合成假传输,urllib 打桩,零网络零花费)

**残余 A'(client→gate 公开链)**:

| # | 控制 | 结果 | 测试 |
|---|---|---|---|
| A'1 | **R2 复审 §4.1 反例复现(矩阵案)**:prompt900/total1/缺输出轴 | ✅ 不可计:unsettled=BOUND(.0064)、settled=0(旧口径 settled=3e-6 低额结清) | test_contradictory_total_matrix_client[incomplete_prompt_total_contradiction] |
| A'2 | output 轴下界同规则:completion500/total1/缺输入轴 | ✅ 同保守保留 | …[incomplete_output_total_contradiction] |
| A'3 | 两轴情形:完整双轴 900/1000 + 冗余矛盾 total1 | ✅ 精确结算 .00352(冗余 total 不参与;分开处理不全面拒绝) | …[complete_split_with_redundant_contradictory_total] |
| A'4 | 保持:兼容已知轴总计(prompt900+total1900) | ✅ 保守总计 .00532 | …[prompt_plus_compatible_total] |
| A'5 | 保持:兼容已知 output 轴总计(completion1000+total1500) | ✅ .0042 | …[output_plus_compatible_total] |
| A'6 | 边界:total 恰等于已知轴和(下界通过) | ✅ 保守总计 .00252 | …[total_equals_known_axis] |
| A'7 | 保持:无轴 total-only>0(3000) | ✅ .0084 | …[total_only_positive] |
| A'8 | **反例数值复现(R2 §4.1 原数值)**:cap=.00768/bound=.0064 | ✅ 第一次 ok;金额保守保留;第二次发送 budget_cost_exhausted 先拒,calls=1(旧口径两次 settled=.000003 均退掉预留、两次发送) | test_contradictory_total_no_refund_squeeze_second_send |
| A'9 | 重复回执幂等(自矛盾总计 usage ×3) | ✅ unsettled 恰一次,不重退不重扣 | test_contradictory_total_duplicate_receipt_idempotent |

**残余 C'(闸门四入口 + client + worker 公开链)**:

| # | 控制 | 结果 | 测试 |
|---|---|---|---|
| C'1 | 四入口(两形态 null/deleted):装配+预留已发生后块消失 | ✅ summary 与 acquire 均 GateCorrupt(reason=cost_guard_block_missing_after_enabled);零新预留/拒发计数不增/坏形态保全;重开装配(_init_state,账本证据)构造期拒 | test_gate_entries_block_missing_after_enabled_reject[null/deleted] |
| C'2 | 结算临界区:块消失后 record_response | ✅ 不裸抛;预留保守转 unsettled(bound+note cost_guard_block_missing_settlement_kept);占位/token 记账照常;坏形态保全;下一次 acquire 先拒 | test_record_response_block_missing_keeps_conservative[null/deleted] |
| C'3 | client 逻辑调用间(首消费 summary) | ✅ 第二次逻辑调用 budget_config_invalid(reason 机读),零新增 urlopen | test_client_between_calls_block_missing_structural_reject[null/deleted] |
| C'4 | client retry(第一次 429 时破坏) | ✅ 重试的第二次 HTTP 先于传输结构化拒;第一次预留转 unsettled(不删除不假退款);429 记账照常(冷却/槽位/total_429=1) | test_client_retry_block_missing_second_http_rejected[null/deleted] |
| C'5 | 同进程装配证据(块+账本同时移除的部分改写) | ✅ record_response 不裸抛(记账照常),下一次 acquire GateCorrupt(assembled_cost_guard_present=true);新进程侧由 worker _verify_budget_guard 兜底(不要求抵抗全库协同改写,证明边界如实) | test_assembled_config_evidence_blocks_after_ledger_removed |
| C'6 | 合法旧未启用保持 | ✅ 无 guard 无账本:acquire/记账/summary None/重开全合法,状态不新增 cost 块 | test_legacy_no_guard_no_ledger_stays_legal |
| C'7 | **主审反例复现(R2 §4.2 原数值,worker 公开端到端、两形态分别 fresh)**:cap=.056326/bound=.046938,第一次合法 HTTP429 时仅破坏 cost_guard(账本/批根不动) | ✅ 第二 HTTP 必须先拒:calls=1、total_requests=1、reservations 恰 1 条转 unsettled(note 在)、settled=0、send_rejections=0、坏形态保全、批根 budget_guard.json 不被破坏;失败题留分母(case 终态 + run_error real_model_transport_failure 含 budget_config_invalid + endpoint failed;沿 R2 复审口径 case 标签不单独证明成功,机器事实为准) | test_worker_retry_block_missing_second_http_rejected[null/deleted] |
| C'8 | worker 装配入口(协调者已写闸门,账本已存在,块消失) | ✅ 装配期 GateCorrupt ⇒ budget_guard_invalid 失败 case(rc=5,零发送,坏形态保全) | test_worker_assembly_block_missing_with_ledger_rejects[null/deleted] |
| C'9 | 正控:守卫完整同构 429(不破坏) | ✅ 重试照常第二 HTTP 发生(calls=2;429 保守保留 + 第二次完整 usage 结算 .00352) | test_client_retry_intact_429_control_still_sends / test_worker_budget_guard_json_unchanged_intact_control |

**保持控制(不重做,既有文件本轮全绿)**:r1_cost 19 + r2_cost 28
(预算额度 1-3、双进程最后额度、未知 usage、429 全家、坏派生字段四入口、
同值恢复、正常 builder、孤儿/幂等、CLI 机器配置、worker→adapter→
client→gate 假传输端到端、其他门/身份块)—— 本轮零改动下 47/47 绿。

## 四、父红绿分类(直接父 d08432c;JUnit 口径,沿 R1/R2 复审 §2 表)

父源 = `git archive d08432c` 解到 fresh `/tmp`(无仓内 worktree 元数据);
子测试文件覆盖 = 本轮触碰的 1 个测试文件(新增 r3_cost;**r1/r2 cost
零改动**);`python -B -p no:cacheprovider --continue-on-collection-
errors`:

- 父:**17 failed / 8 passed / 0 collection error**(本轮新文件不导入
  任何父版本缺席的新 API,无 ImportError ⇒ 无 collection 红,全部为
  真执行后断言红);
- 分类(**逐 nodeid 在
  `/tmp/s5b_v3r3_impl/parent_redgreen/classification.json`**,双侧
  JUnit XML 与 stdout/stderr 在档):
  - **行为红 15**:A' 占 4(两矩阵案 settled 低额结算、挤出第二次发送、
    重复回执按总计口径结算);C' 占 11(四入口 DID NOT RAISE GateCorrupt
    ×2、结算临界区预留卡 reserved ×2、client 首消费照发 ×2、client
    retry 第二 HTTP 到传输层 ×2、已装配证据放行 ×1、worker 主反例第二
    HTTP 照发 ×2);
  - **拒绝 kind 红 2**:worker 装配案两形态 —— 父代**同样先拒零发送**
    (经 `_verify_budget_guard` 报 budget_guard_missing),子代装配期
    GateCorrupt 报 budget_guard_invalid;两代均 fail-closed,红在拒因
    kind/检出入口,不冒称父代放行;
  - **保持绿 8**(父代已符合的正控,非新行为):A' 矩阵 5 个保持案
    (完整双轴+冗余矛盾 total/两兼容总计/边界相等/total-only)+ 完整
    429 正控 + legacy 合法 + worker 完整正控;
- 子(当前工作树):同文件 **25/25 全绿**;
- 缺模块不报内部行为绿:本轮无 collection error,无未执行内部案。

## 五、回归数字(当前工作树,depending43 `-B` + `-p no:cacheprovider`)

| 组 | 口径 | 结果 |
|---|---|---|
| 定向(15 文件) | R2 定向 14 文件(wv1/2/3/6 + v3r1 scope/cost + v3r2 cost + runtime/pairing/rework_l01/hit50 w1/w23456 + test_rate_gate + test_prediction_task)+ **v3r3 cost** | **283 passed / 0 failed**(49.3s;R2 258 + 25) |
| 全量 | `pytest tests/ -q -m "not slow"` | **1958 passed / 0 failed / 16 deselected**(282s;R2 1933 + 25) |
| G01 安全隔离 | `/tmp/safe_g01_s5b_hit50_v3_r3.py`(sha256 `b06329032613…bbdc0d`,由 R2 版 `6b04031c…952952` 派生:R3 上下文 + 新输入 r3_cost + 换字节集恰 1) | **exit 0;1947 passed / 10 skipped / 17 deselected**(275s;R2 1922 + 25) |
| 父基线红绿 | 见 §四 | 17F/8P/0C(15 行为 + 2 拒绝 kind) |

## 六、G01 隔离细节

- 脚本:`/tmp/safe_g01_s5b_hit50_v3_r3.py`(sha256
  `b06329032613c30738be3a9f4cb56ddf532d4ef553170635a965066b62bbdc0d`);
  输出根 `/tmp/g01_s5b_hit50_v3_r3/`(fresh tmp,不在永久证据建库);
- 变更集核对:expected_changed == observed_changed = **恰 1 项**
  (`repo/src/pathway_v43/adapters/rate_gate.py`,本轮唯一实施文件;
  无父提交遗留变化);new_inputs_vs_r2 = 恰 1(r3_cost);零缺失
  (326 → **327** 输入);
- 327 输入前后重核零失配(post_run_sha_result.json:input_sha_
  mismatches=[]);10 skip 逐 nodeid 与 R2 轮缺席类别一致;17 deselect
  沿 controller 口径 + 1 显式;pyc 7 = 子进程缓存例外逐路径登记
  (与 R2 轮同量级,如实不报"无 pyc");
- 实际 HEAD `d08432c` + dirty(2 个本轮修改文件)记录于
  preparation.json;完整 argv/env/exit/stdout/stderr/JUnit 落盘输出根;
- 嵌套 manifest 纳哈希:两 probe 证据包(§九)根 manifest.json +
  SHA256SUMS 覆盖全部嵌套合成 artifact;G01 自身产物(preparation/
  input_sha256/execution_result/post_run/junit/stdout/stderr)单列。

## 七、文稿同步订正清单(R2 交付书 2 处,均加【v3-R3 订正 2026-10-10,
R2 正链复审 §5】标记,不改历史结论、不删原文语义;旧主审报告/永久
证据未回写)

1. **§二 legacy 聚合不相容**:R2 交付的 `cd683e…` 聚合算法未确认、
   与公开函数不相容不能当部署身份 ⇒ 订正标记内登记本轮实测公开聚合
   `279d9bc1…`(52 文件)与新发车登记要求;
2. **§八 冻结记录 SHA 笔误**:R2 交付写 `…fea1a6e7…`,实际为
   `…fea1b6e7…`(全值 `6e046e2970a102c63e693cebb81f2564b5d79fea1b6e7
   a776b0fc00c09662610`,即冻结记录
   `docs/POLLUTANT_PATHWAY_CRITERIA_FREEZE_RECORD_V1_2026-10-08.md`
   实测)⇒ 订正标记登记;冻结文件未改。

本轮交付书内**精度登记(不回写旧文)**:

3. **total 分支可信范围**(R2 复审 §5"usage 坏轴+合法 total 的文字"
   P2 项落字):源码现状 = 坏类型/负数轴不可用**不计入下界**(轴值
   不可核不能当界),total>0 即走总计口径 ⇒ 坏轴+合法 total 仍结算
   (正控 bad_prompt_with_valid_total settled=.00532 在 A' probe 留档);
   本轮真正阻塞是 **total 与已知有效轴自矛盾**,二者分开表述,不写
   "所有坏字段必 None";
4. **四入口整块缺失证明范围**(R2 交付"worker 装配期捕获"的证明
   范围澄清):R2 的 worker 装配期 GateCorrupt 捕获证明的是**装配时
   点**的坏块先拒;运行中(retry/第二次逻辑发送)的整块缺失范围差
   是本轮 C' 补的(§4.2 公开 429 重试反例);二者都是真拒绝,但不可
   互相冒充覆盖。

## 八、金标边界自查

- 零真实模型调用、零花费、零外部网络(测试与 probe 内唯一"网络"是
  127.0.0.1 假提供者/urllib 打桩,本机回环);不 push、不部署真实批、
  不启动 chain10、不改封存/冻结产物;
- 未读 298 题卷/金标/旧答卷/封存逐题 run;probe 合成分子沿用
  s5b_runtime 夹具(乙醇级合成小分子,与真实集合零重叠口径沿旧);
  probe 隔离副本只读引用真实仓 assets(V43_ASSET_ROOT),状态/闸门/
  批根全写 fresh tmp,禁字节码;
- 冻结三 SHA 工作树复核逐字节一致(实测全值):
  判据 `7fd35aabdb4d2d5b67b0bf58693dab6f8765ad872efedf5f886503c4907064e4`
  (docs/POLLUTANT_PATHWAY_CRITERIA_FROZEN_V1_2026-10-08.md)、冻结记录
  `6e046e2970a102c63e693cebb81f2564b5d79fea1b6e7a776b0fc00c09662610`、
  path_context
  `971ad00f42fc56915bad3724300759aa86552bf08199f8335c7f0286b40d588d`
  (src/pathway_v43/pollutant/path_context.py);
- 冻结判据/scorer 匹配/排序/(created_at,event_id)/S5B_PASS_LINES
  零触碰(本轮改动 = 金额守卫两残余 + 配套注释/新测试,全部
  fail-closed 方向);S5B-V3-01 关闭状态零回退(v3r1_scope 52 用例含
  于定向 283 绿);
- 父红绿父源用 `git archive` fresh tmp 副本,未新增仓内 worktree
  元数据,用后即弃;旧批/旧 G01 产物只读;两个 probe 先复制 fresh tmp
  复跑(隔离源码副本 + PYTHONDONTWRITEBYTECODE=1),不在永久证据
  目录原地跑。

## 九、提交构成与证据

- 源码(1):`src/pathway_v43/adapters/rate_gate.py`(A' 下界校验 +
  C' 四入口共用判据/保守结算 + docstring/注释;唯一实施文件);
- 测试(1):新增 `tests/test_ppv1_s5b_hit50_v3r3_cost.py`(25 用例);
- 文稿(2):本交付书;R2 交付书 2 处订正(§七清单);
- 证据(未跟踪,按 AGENTS 默认留 /tmp 易失):
  - `/tmp/s5b_v3r3_impl/probes/ab/`(A' probe:16 reviewer 保持检查 +
    3 R3 检查全绿 + 1 陈旧期望单列两代同为 false;manifest.json/
    SHA256SUMS/完整 16 client 场景 + 5 worker 场景 input_output/
    stdout/stderr/exit);
  - `/tmp/s5b_v3r3_impl/probes/c/`(C' probe:reviewer 原 5 检查全绿
    —— 含 R2 观察为 false 的 worker_retry_block_absent_blocks_
    second_send 翻绿 + 3 R3 检查;24 四入口形态案 + 8 worker 案
    null/deleted 两形态;manifest.json/SHA256SUMS/checks.json/
    stdout/stderr/exit);
  - `/tmp/s5b_v3r3_impl/parent_redgreen/`(classification.json 逐
    nodeid + 双侧 JUnit XML + stdout/stderr/exit);
  - `/tmp/s5b_v3r3_impl/legacy_identity_r3.json`(公开函数实测
    legacy52 聚合 279d9bc1…);
  - `/tmp/s5b_v3r3_impl/preparation_events/`(准备/失败事件登记 +
    debug 脚本留档);
  - `/tmp/g01_s5b_hit50_v3_r3/`(G01 完整产物:preparation/
    input_sha256(327)/execution_result/post_run_sha_result/junit/
    stdout/stderr);`/tmp/safe_g01_s5b_hit50_v3_r3.py`(脚本);
  - 两 probe 假传输合计 31 次(ab 22+7、c 2)+ pytest 内本机回环假
    提供者,零真实 provider 调用;数字不相加成科学样本,不外推真实
    费用/历史远端行为/科学性能。

## 十、执行事件与待复审残留

执行事件(准备事件不删,详见 preparation_events.json):r3 测试首轮
3 failed(worker 级:intact 正控 cap 配置笔误致批根/闸门不一致
budget_guard_mismatch + case 终态断言按实际观察修正为 R2 复审口径),
修正后 25 全绿;ab probe 首两跑 exit=1(隔离副本布局致仓根误判 /
键名笔误 KeyError),修正后全绿,失败细节因 stdout/stderr 同名覆盖
以会话记录誊录登记;G01 派生脚本 py_compile 留 1 pyc 已删(非证据);
定向/全量/G01 各一次通过,无失败重试,无账号中断。

待复审残留(如实,不虚报闭合):

1. 429 错误体 usage 读取未实现(保守保留口径保持;R2 §十.1);
2. TPM 滑窗对部分 usage 的补零(速率机制非金额结算;R2 §十.2);
3. total=0-only 保守过拒(未证 provider 用 0 表达零计费;完整拆分含
   显式 0 已可结算;R2 §十.3);
4. 结算坏块不做 overrun 披露(cap 不可核;新发送已拒,committed 账本
   事实完整在盘;R2 §十.4);
5. `cost_snapshot` 对"已启用块消失"形态由 enabled=false 改为抛
   GateCorrupt(fail-closed 方向的行为变化,如实登记;协调者报告须
   处理该异常,不把 raw 摘要当完整性证明的 R2 §5 要求不变);
6. 坏轴 + 合法 total 仍走总计口径(§七.3 精度登记;非本轮阻塞);
7. C' 证据边界:块+账本同时移除且换新进程 ⇒ 闸门侧无证据走旧分支,
   real 批由 worker `_verify_budget_guard` 兜底(不要求抵抗全库协同
   改写,沿 R2 报告 §4.2 原文边界);
8. 当日价/上下界/60 帽真实数值发车定稿仍属受权协调者(R2 §5"发车
   前必办"不变;CLI 60/30000/8192 仅缺省);
9. **mimo 登记**:本轮为纯程序回修(金额/存储语义,无化学判据、
   scorer、题面变更),按 AGENTS 既有职责分工登记**实际跳过**化学
   mimo 评审,不编造回应;下一份完整 mimo 请求按惯例携带本跳过注记;
10. **§9-④ 读回状态(如实)**:新登记
    `docs/S5B_HIT50V3_RETEST_REGISTRATION_2026-10-10.md` 的条款正文
    读回已由 R2 复审 §7.1 完成(该登记本轮未改、未再读回);真实部署
    config/发车封包仍未确认,本轮不假称已发车 —— R2 复审 §7.1 指出的
    价格义务缺口(沿用 9 月 29 价未兑现当日核价)属受权协调者发车条件,
    未另增编号;金额 P1 清零与否由正链有限复审裁定。

本轮报告不代替放行;新金额语义/代码身份(公开聚合 279d9bc1…)随新批
登记引用,由主会话核对 → 正链有限复审;金额 P1 清零前不发 chain10。
