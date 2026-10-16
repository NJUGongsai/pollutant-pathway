# 交付书 — chain14 发车物实施(证据卡批级开关+transport 重试+双臂发车族,2026-10-15)

> 任务书:`docs/TASK_CHAIN14_LAUNCH_2026-10-15.md`(三实施件+红线+测试
> 要求+回传义务)。执行者:实施子代理。基线:HEAD `b4b89dc`(证据卡
> 实施+P1 修复),全量 not-slow 2158/0/16。题域标签:**298=RHEA 通用
> 酶学/已见题**。上游:预注册 `docs/CHAIN14_EVIDENCE_AB_PREREG_2026-10-15.md`
> (已确认生效)。本交付**只在本地实施与验证**,HPC 部署与发车归主会话;
> 不 commit 不 push(主会话统一)。

## 一、三件改动清单(文件与行数)

| 件 | 文件 | 改动 |
|---|---|---|
| 件1 开关 | `src/pathway_v43/pollutant/s5b_orchestrator.py` | +71:发车参数 `evidence_card_enabled`(None⇒True 现行行为;非 bool ⇒ `s5b_evidence_card_flag_invalid` 结构化拒);冻结进 orchestration.json(批身份含该键,同批根改参即拒由既有比对覆盖);`load_evidence_card_flag` 单一验证源(副本缺席⇒None 合法;在场缺键/坏值/不可解析⇒拒,fail-closed 沿 no-cap 坏标记不当缺席先例);批报告披露 `evidence_card_enabled`;summarize 账目增 `model_call_retries_total` |
| 件1 开关 | `src/pathway_v43/pollutant/s5b_worker.py` | +45:worker 侧同判据核对(`load_evidence_card_flag`,先于任何 run 启动/发送;缺键/坏值 ⇒ 失败 case `evidence_card_flag_invalid` rc=5;副本缺席⇒回退现行行为 on);开关+重试计数入 case(`evidence_card_enabled`/`model_call_retries`);start/resume 显式传值 |
| 件1 开关 | `src/pathway_v43/pollutant/runflow.py` | +64/-8:消费点 `_call_real_fetch`——`evidence_card_enabled=false` ⇒ 池条目不带 `evidence`、载荷不带 `substrate_evidence`(=实施前四字段形状);true ⇒ 现行 candidate-evidence-2;`start_ppv1_run`/`resume_ppv1_run` 新参(None⇒True,非 bool ⇒ `evidence_card_flag_invalid`);开关入策略身份块(`_strategy_block`)+resume 同判据核对(换臂 ⇒ `evidence_card_flag_mismatch` 拒;前代身份无键按 on 兼容);summary 披露 `evidence_card_enabled` |
| 件2 重试 | `src/pathway_v43/pollutant/real_model.py` | +132/-9:首发传输失败 ⇒ 自动重试 1 次(`S5B_TRANSPORT_RETRY_MAX=1`,双臂共享);重试=**显式新 request**(键=来源 request_id+`:transport-retry-1`,全局唯一防 decide/反馈两支碰撞;`retry_of` 记来源;经同一预算/gate 诚实占额);发送结算序抽 `_send_and_settle`(首发/重试同一序);裁定入口 `_transport_retry`(取舍见 §三);预算拒不掩盖原失败;每次尝试 `http_attempts` 字段随调用记账(**如实更正 2026-10-16**:该字段只在传输失败/异常路径由 llm_client 完整填充,成功路径不 append 当前尝试 = 旧诊断缺口,逐 HTTP 留痕在生产 client 不完整;gate 计数与 issued/responded/failed 调用行诚实不受影响,补记留后续轮,本交付不改 llm_client 行为) |
| 件2 重试 | `src/pathway_v43/pollutant/model_protocol.py` | +7/-3:`format_feedback_rounds_used` 排除 `retry_of != ''` 行——传输重试是**同轮**的第二次尝试,不是新的一轮(max_format_feedback_rounds 语义不变) |
| 件3 发车族 | `scripts/hpc/sbatch_chain14_build.sh`(新 52 行) | chain13 build 参数化:ARM=a/b 环境变量前置(非法值拒),批根 `~/ppv1_hpc/batch/chain14{a,b}_s5b_20261015`,两臂同构构建(同题卷同 sha,build-gate 沿 chain13_gate.py),CODE 默认 `~/EnzymeAgent/v43c14` |
| 件3 发车族 | `scripts/hpc/sbatch_chain14_run.sh`(新 66 行) | 冒烟 2→10→全量三段+每段 chain13_gate.py run-gate;发车门=批准记录+no-cap 标记+凭证 env(沿 chain13);wrapper `--arm`;runs 根同款按臂派生 |
| 件3 发车族 | `scripts/hpc/chain14_run_wrapper.py`(新 90 行) | 臂→开关映射单一写死 `EVIDENCE_CARD_BY_ARM={"a":False,"b":True}`(worker 无选择权);profile 沿 chain13 **直接 import 复用**(每题≤3 真实调用+2 反馈轮);gate RPM 200/TPM 3M/max_calls 4470/workers 8 沿 chain13;输出 JSON 带臂与开关 |
| 件3 发车族 | `scripts/hpc/sbatch_chain14_score.sh`(新 52 行) | 双口径判分沿 chain13:v1(`s5b_cli score`+产物改名 `.v1`)+v2 headline(`chain13_score_v2.py` 复用);score-gate 全 qid 终态门 |
| 测试 | `tests/test_chain14_evidence_switch_retry.py`(新 679 行,15 测) | 开关正负控 8 + 重试正负控 6 + 发车物冒烟 1(§四) |

合计:5 个源文件 +356/-18;4 个发车物新文件;1 个测试新文件(15 测)。

## 二、A 臂字节兼容断言结果(红线 1)

- `test_evidence_flag_off_payload_byte_equal_pre_evidence_shape`:
  开关 off 的 decide 载荷与**重构的证据卡实施前四字段形状逐字节相等**
  (同源输入重构 hypothesis_id/atom_id_map/execution_graph 后
  `json.dumps(..., ensure_ascii=False, sort_keys=True)` 全等断言);
  顶层键集精确 = {substrate_smiles, substrate_atom_id_map,
  pool_hypotheses, protocol_version, execution_graph};池条目键集
  精确 = {hypothesis_id, product_smiles, transformation_ref,
  coproducts};`"evidence"`/`"substrate_evidence"`/
  `candidate_evidence_schema_version` 零出现。
- 判分侧/池/检索/排序/硬拒绝表零改动(git diff 仅上述 5 源文件;
  判分入口 s5b_scoring 零触碰)。
- **提示词两臂同版**:`_PROPOSALS_SYSTEM_PROMPT`/`PROPOSALS_PROMPT_
  VERSION` 零改动(单一常量;开关不入提示词/模型身份块,测试断言)。

## 三、transport 重试设计取舍(如实登记,排障表"重试与预算/gate 冲突"项)

- **触发族** = 服务端不稳 `{transport_error, empty_response}`。
  **不重试**(逐条理由,代码头注释同文):timeout(首发可能仍在服务端
  处理中,重发双计费风险+最多再挂一个 timeout 时长)、
  rate_limited_exhausted(429 有界退避已在传输层完成,沿既有语义)、
  forbidden_permanent(401/403/402 鉴权/付费停止)、gate/预算资源拒
  (forbidden_stopped_by_gate/budget_*)、sent-无-blob 悬空与 blob
  持久化失败(崩溃恢复保守态/本地盘故障非传输不稳)。
- **计费/账目**:每次 HTTP 尝试=一次 issued 请求(重试登记走同一
  register_model_request 即时占额);每题 max_real_model_requests=3
  语义不变——额度不足以登记重试 ⇒ SearchBudgetExhausted 被
  `_transport_retry` 捕获 ⇒ **原传输失败语义保持**(留痕
  `transport_retry_budget_refused`,不改判、不升格);每逻辑调用至多
  1 次重试,重试仍败 ⇒ 第二次失败为终态(现行失败语义,零静默吞)。
- **反馈轮账目**:重试行 `retry_of != ''` 不计入
  format_feedback_rounds_used(同轮第二次尝试≠新一轮)。
- **批报告披露**:summarize 账目 `model_call_retries_total` + 逐 case
  `model_call_retries`(worker 从 model_requests 的 retry_of 列复算)。
- **P2 更正(2026-10-16,Codex 代审非阻塞项;如实登记,不改行为)**:
  「逐 HTTP 尝试留痕」在生产 client **不完整** —— `llm_client.py` 的
  HTTPError 分支记录 attempt,成功路径与网络异常路径未 append 当前
  attempt(旧诊断缺口,先于本交付存在)。实测:真实 client 本地桩
  4 次发送仅记 2 条 attempt、429→503→200 三次发送仅 2 条。
  **不受影响的面**:gate 计数(每 HTTP 尝试一次闸门)、issued/
  responded/failed 调用行(每逻辑请求一行)均诚实;新测试断言的
  http_attempts 合计 2 由 stub 自行补条承载(不证明生产完整)。
  成功/异常/429 同源补记留后续轮,**本交付不改 llm_client 行为**。

## 四、测试数字

- **新测 15 件全绿**(tests/test_chain14_evidence_switch_retry.py,
  3.2s):开关 8(off 字节兼容/on+缺省全等/提示词同版/run 入口非法值拒/
  resume 换臂拒+同臂幂等/批冻结+改参拒+非法值拒+缺省冻结 True/worker
  fail-closed 缺键坏值+副本缺席回退/loader 单元契约)+ 重试 6(首败
  重试成功 http_attempts 合计 2(由 stub 自行补条承载;生产 client
  成功路径缺口见 §三 P2 更正)+retry_of 链接/两连败现行失败语义/
  timeout 与 forbidden_permanent 不重试/预算拒不掩盖原失败/反馈轮重试
  不越轮数/常量面登记)+ 发车物冒烟 1(三脚本在位+bash -n+ARM 映射+
  双臂批根样例;本地零提交)。
- **定向回归**:candidate_evidence 18 + controlled_vocab CI +
  s5b_runtime + no_cap + hit50 w23456/shard/v3r1/r2/r3 cost 全绿。
- **T11**:新字面量零登记需求(mismatch detail 键 "submitted" 撞
  受控词,改名 "current" 收口;测试断言零翻转)。
- **全量 not-slow**:见 §六(主会话将独立复跑)。

## 五、偏差清单

1. **发车参数缺席(None)⇒ 冻结 True,非"缺席即拒"**:任务书
   "键缺失/非法值 ⇒ 结构化拒"落点在**冻结副本消费侧**(
   load_evidence_card_flag:在场但缺键/坏值 ⇒ 拒,不当缺省)——
   发车 API 缺席即拒会翻转 20 处既有 run_s5b_batch 调用(红线 4 零翻转
   优先)。对冲:A/B 两臂发车脚本恒显式传值(wrapper 单一写死,无
   缺省路径);缺省值冻结后同样进批身份、同样改参即拒。请复审确认
   此取舍。
2. **worker 侧核对覆盖面**:orchestration.json 缺席(批根未经协调者
   冻结的手动/测试直连路径)⇒ 回退现行行为 on 而非拒——存在约 10 处
   既有手动 worker_main 测试依赖该路径;协调者发车链(生产 A/B 路径)
   恒有冻结副本,绕行口子已闭合。沿 no-cap 先例"缺席=合法,坏标记=拒"。
3. **重试族不含 timeout**:任务书括注仅点名 transport_error;扩入
   empty_response(同为服务端不稳且无长挂风险),timeout 依理由排除
   (§三)。若复审要求扩族,改 `TRANSPORT_RETRYABLE_ERROR_KINDS` 一处。
4. **gate_max_calls 维持 4470**(预注册"gate 4470 同 chain13"):重试
   尝试计入同一门,理论上限场景(3 logical×6 HTTP)超 4470 时按既有
   语义停批同参重投,不放开。

## 六、全量数字

- **全量 not-slow:2173 passed / 0 failed / 16 deselected**(336.7s;
  基线 2158/0/16 + 新测 15 = 2173,**零翻转**)。实施子代理单机跑;
  主会话将独立复跑并抽查(A 臂字节形状/fail-closed/重试计数)。

## 七、HPC 交接(主会话执行项)

1. 部署树:本仓 @ 本交付 HEAD → `~/EnzymeAgent/v43c14`(脚本默认;
   可用 `CODE=` 覆盖);venv 沿 `~/ppv1_hpc/venv_v44run`。
2. 每臂流程:build(`ARM=a sbatch sbatch_chain14_build.sh`)→
   `s5b_cli approve`(预注册已确认生效;用户授权记录落批根)→
   no-cap 标记(`s5b_cli budget --budget-mode
   no_monetary_cap_user_decision ...`,沿 chain13 拍板原文)→
   run(`ARM=a sbatch sbatch_chain14_run.sh`)→ score(`ARM=a sbatch
   sbatch_chain14_score.sh`);B 臂同流程 `ARM=b`。
3. 双臂批根/独立:batch/runs 根按臂分立;A/B 唯一差分 =
   orchestration.json 的 `evidence_card_enabled`(发车后可
   `python -c` 读批根 orchestration.json 复核臂标识)。
4. 发车前照旧 no-cap 费用拍板点;红线沿仓规(金标/题面/封存 run)。

## 七、mimo 修正案小修增量（主会话直改，2026-10-16 凌晨；供 Codex 代审核对）

> 依据：预注册 §六修正案（mimo 场景 1 采纳项，docs/mimo_evidence_card_scene1_review_response.md）。
> 改动由主会话直接实施（非子代理），全部增量如实披露：

| 项 | 位置 | 内容 |
|---|---|---|
| SMARTS 口径修 ×3 | candidate_evidence.py:63/65/66 | hydroxyl_oh 加 `[#6;!$(C=[OX1])]`（羧酸 OH 排除）；amine_primary/secondary 补 `!$(NC=[OX1])`（同 tertiary 先例）——RDKit 实测：乙酸只报羧酸/酰胺只报酰胺/乙醇 CCN 苯胺正常命中/乳酸仅醇 OH |
| descriptor 升版 | candidate_evidence.py:47 | candidate-evidence-descr-1→**-2**（表口径变化承载；schema 维持 candidate-evidence-2 不变） |
| 提示词四句补丁 | real_model.py 证据注记段 | 记账非机制（含隐式氢不计 bond 计数）/role unknown=在场未指派≠事实不可得+系数 unknown=未记录≠未配平+参与物表可能 partial/输入 unknown≠弃权理由（并入既有 unknown 行）/电荷按所绘质子化形式算 |
| 一处合规修正 | 同上 | mimo 原文 role "unknown" 带引号触发 T2-T8「提示词不教内部载荷词」检测 ⇒ 去引号（既有 unquoted unknown 先例） |
| T1 基线换钉 | tests/test_controlled_vocab_ci.py | 哈希 13698065…→**fe9eaf77…**、字节 5380→**6123**（提示词变更合法升版路径，注释留链条） |
| 新增正负控 ×2 | tests/test_ppv1_s5b_candidate_evidence.py 末尾 | 酰胺≠胺（含苯胺正控）/羧酸 OH≠羟羟基（含乙醇/乳酸正控，n_hits 断言） |

测试：受影响三文件 **53 passed**（18+15+18+2 新）；全量 not-slow 主会话独立复跑
**2175 passed / 0 failed / 16 deselected（338.7s）**=基线 2158+发车物 15+增量 2，
零翻转。A 臂字节兼容/判分零触碰/池检索零触碰不受本增量影响
（增量仅 B 臂载荷内容+提示词两臂同版原则不变）。

## 八、P1 回修轮（2026-10-16；Codex 代审 CHAIN14_LAUNCH_CODEX_REVIEW_2026-10-16 四项 P1 回修，任务书 TASK_CHAIN14_P1FIX_2026-10-16）

> 实施子代理单人串行；只修列出的 4×P1+P2 措辞；A 臂字节兼容/判分/池/
> 检索/重试族/gate_max_calls=4470 零触碰；零金标零题面零模型零网络
> （真实 client/gate 仅 urllib.urlopen 换本地桩）；不 commit 不 push。

| 项 | 修复点（文件:行） | 内容 |
|---|---|---|
| P1-1 | runflow.py:1196-1208 | 反馈轮登记沿**实际 provider_kind**（`self.model_provider_kind`，与 decide 登记同源；旧硬编码 SCRIPTED 而反馈响应走 real fetch ⇒ 每题预算被旁路）⇒ 全部真实发送共用每题预算，第 4 次发送前被 register_model_request 即时占额拦截（拒绝优先于 HTTP）；gate/batch 硬门不动 |
| P1-2 | real_model.py:741-762+790-914 | 来源 failed ⇒ 「来源→唯一重试终态」链：恰好一个 retry_of 后继 + run/action/attempt/provider/purpose/payload_hash 逐列一致 + request_id 可由确定性重试键（来源 id+`:transport-retry-1`）重算复现 ⇒ 零调用消费既有 responded blob（或 sent+有效 blob 先闭合 sent→responded）；唯一性破坏/错身份/非终态/blob 缺失篡改 ⇒ 维持拒（request_not_consumable/replay_unavailable），不补调用、不重算新键、禁止为恢复另发付费请求 |
| P1-3 | s5b_worker.py:214-222 | resume 删无效 `profile_policy=None` 参数（签名无该参 ⇒ 合法中断 run 被 TypeError 写成失败终态；profile 策略 start 时已冻结进 run 身份，resume 只核对不重传） |
| P1-4 | s5b_worker.py:41-46+79-140+271；s5b_orchestrator.py:393-441+444-453+806-811+871-878+912-929+1074-1090 | worker 新 `--evidence-card-flag`（协调者从冻结参数派发，可信批上下文显式传预期 bool）：冻结副本**缺席=拒**（evidence_card_frozen_copy_missing，不回退；旧 None→True 让已冻结 A 丢副本静默变 B 错账）、**换臂=拒**（evidence_card_flag_mismatch）；手动/测试直连缺席 ⇒ 显式手动模式（case 披露 `evidence_card_mode`）；case 在 skip/收割/汇总接纳前核同源开关（validate_case/read_validated_case 新 `expected_evidence_card`，错臂终态不进分母）；批报告开关改从冻结副本同源装载核对（副本缺席/不一致 ⇒ 结构化拒，不写错账报告） |
| P2 | 本交付书 §一/§三/§四 | 「逐 HTTP 尝试留痕」更正为如实（llm_client 成功/异常路径未 append = 旧诊断缺口；gate/调用行诚实；补记留后续轮，**不改 llm_client 行为**） |

**新测试 10 件全绿**（tests/test_chain14_evidence_switch_retry.py，15→25）：
P1-1 组合路径第 4 次发送前被每题预算拒（真实 client+gate+本地桩：HTTP 3 次/gate 3/预约 3/反馈行 real+network=1/预算拒留痕/原失败终态）+ 正常·单支重试·反馈正常三正控；
P1-2 重试成功崩溃重放零新增调用（同配置 resume 完成、blob 消费不新增）+ 单次成功同点崩溃正控 + 四负控（坏 blob=replay_unavailable/错身份·后继缺失·唯一性破坏=request_not_consumable，零补调用、坏记录保全）；
P1-3 真实协调者冻结→公开 crash 注入中断→公共 worker 恢复路径同臂 resume 成功（failure_kind≠TypeError，批 n_completed=1）；
P1-4 评审反例复现（真实协调者冻 False→worker 启动前移走副本 ⇒ worker 拒+零 run 零发送+批报告前同源核对 fail-closed）、worker 层换臂双向拒、可信上下文副本缺席拒、错臂已完成 case 在 skip/汇总接纳前拒。

**全量 not-slow：2185 passed / 0 failed / 16 deselected（终态复认证
344.2s；P1-2 purpose 锚定微修前后两跑同数；主会话独立复跑 2185/0/16
347.1s 逐字相同）**=基线 2175/0/16 + 新测 10，
**零翻转**。定向回归先行全绿：s3b_model/s5b_runtime/no_cap/s3b_runner 58
+ hit50_w23456/v3r1/v3r2/v3r3/cosub_d2 143。全量唯一 warning =
chemstate.py:1 既有 docstring DeprecationWarning（先于本交付在案，非
本轮引入）。

**偏差清单**：
1. P1-4 报告开关同源核对（orchestrator.py:912-929）采取**缺席/不一致即
   raise**（不写批报告）：评审最小修法未指明落点形态，取 fail-closed——
   副本丢失属批根被改坏，错账报告不如结构化拒；失败 case 已在盘（worker
   先写），恢复副本重跑即得完整报告。
2. P1-4 接纳面核对只对**披露了该键**的 case 生效（worker 失败路径部分
   case 不带 evidence_card_enabled，如 evidence_card_flag_invalid/
   budget_guard 类先拒 case）：避免翻转既有失败 case 形状；completed
   case 恒披露，错臂 completed 必被拒。
3. P1-2 链核验含 payload_hash 重算比对（评审核验面列了 payload）：resume
   重入时按当前调用确定性重算登记 payload 与后继行比对；prompt 载荷变更
   = 身份变更 ⇒ 拒（与 resume 身份门同向）。
4. 手动兼容保留但**显式化**：worker 未传 `--evidence-card-flag` 且副本
   缺席 ⇒ 现行行为 on + case 披露 `evidence_card_mode=manual_no_frozen_
   copy`（评审允许保留，要求显式进手动模式；既有 ~10 处手动 worker_main
   测试零翻转）。

## 九、P1 余项回修轮（2026-10-16；Codex 同范围复核 CHAIN14_LAUNCH_CODEX_REREVIEW_2026-10-16 §⑤ 两项余项，任务书 TASK_CHAIN14_P1_RESIDUAL_2026-10-16）

> 实施子代理单人串行；只修两项余项；P1-1/P1-3 修复不动；A 臂字节兼容/
> 判分/池/检索/重试族/gate_max_calls=4470 零触碰；零金标零题面零模型零
> 网络（合成验证）；不 commit 不 push；PYTHONDONTWRITEBYTECODE=1。
> 修前两项评审反例均先独立复现（P1-2 预算 3 场景 3→3 但 model_structure_
> failure、单次成功 2→3 另发一轮；P1-4 completed 删字段/置 null 均被接纳）
> 再修，修后反例全部翻转为预期行为。

| 项 | 修复点（文件:行） | 内容 |
|---|---|---|
| P1-2 余项 | model_protocol.py:278-326（新 `latest_format_feedback_round`）+ runflow.py:1204-1241 | 真实取响应路径（real_fetch 在场）解析失败进反馈分支时**先查既有反馈轮**：最新轮 = 第 rounds_used 轮，request_id 由原登记键 `format-feedback:{action}:{round}` 确定性重算（同键复算，不是换键洗记录）⇒ 复用该行进 ppv1_real_fetch 既有行状态机（responded+完整 blob ⇒ R3 零调用重放；failed ⇒ 唯一重试终态链核验后零调用消费；registered ⇒ 补首发；坏 blob/错身份 ⇒ 维持拒）——**不先分配新轮、不为恢复另发付费请求**；purpose 被篡改行 ⇒ feedback_round_identity_corrupt 拒（漏网时同键重登记撞 S3A-04 同键身份冲突，不以新轮登记掩盖）；**无既有轮才走新轮登记**（register_format_feedback_round 轮数/每题预算判据不变，预算第 4 次发送前拒保持）；scripted/非 fetch 路径字节不变 |
| P1-4 余项 | s5b_orchestrator.py:406-421+441-465（validate_case 严格化） | expected 明确时 completed **必须有键 + 严格 bool + 同值**（缺键=evidence_card_flag_missing / null·"on"·1·{}·0 等非严格 bool=evidence_card_flag_not_bool / 错臂=evidence_card_flag_mismatch，全拒——旧实现只核「有键且非 null」且先 bool() 强转，删字段/置 null 绕过接纳门）；失败（及非完成）case **披露了才核**（严格 bool + 同值；null/字串披露=坏披露拒），**缺键豁免保留**（合法 run 前早失败可缺字段；worker 早失败路径本不写该键）；expected 缺席（手动批）不核（现行豁免面不变）；skip/汇总双入口经同一 validate_case 生效 |

**新测试 7 件全绿**（tests/test_chain14_evidence_switch_retry.py，25→32）：
P1-2 正控 2 件——预算 3「首提 BAD→反馈首发传输失败→反馈重试成功→解析前崩溃→resume」**3→3 且完成**（零新增调用/零新轮/零新行/blob 零新增/链重放留痕/预约 3）；单次反馈成功同点崩溃 **2→2**（复核标注「既有入口缺口」一并闭合）。P1-2 负控 2 件——坏 blob（重试终态 blob 篡改 ⇒ replay_unavailable）/错身份（后继行 purpose 篡改 ⇒ request_not_consumable）/首发行 purpose 篡改 ⇒ request_identity_conflict/后继缺失 ⇒ request_not_consumable，均零补调用、坏记录保全、零新行；无重试终态（反馈首发败+重试登记被预算拒）resume ⇒ 拒且**零补发零新行**（预算第 4 次发送前拒在 resume 面保持为「根本不发生第 4 次发送」）。P1-4 3 件——validate_case 双臂纯矩阵（completed 缺键/null/"on"/1/{}/0/错臂全拒+原因分列、正确 bool 过；failed 披露错臂/null 拒、缺键豁免）；公共 skip/汇总入口 completed 删字段/置 null ⇒ 双入口结构化拒（零 worker 派发零 run，不写错账报告）；公共入口合法正控（在位正确 bool 同值 ⇒ skip 接纳 + n_completed=1）。

**全量 not-slow：2192 passed / 0 failed / 16 deselected（344.0s）= 基线
2185/0/16 + 新测 7，零翻转**。定向先行全绿：chain14 文件 32/32。

**偏差/语义清单（如实登记）**：
1. **real 路径反馈轮恢复语义收敛**：resume 重入反馈分支一律先复用既有
   最新轮（§⑤.1「不得先分配新轮、不为恢复另发付费请求」字面执行）⇒
   既有轮响应被消费且解析再败时，resume 重放同一响应、结构失败保持，
   **不再在恢复路径分配下一轮**（旧行为=resume 另发第 N+1 轮付费请求，
   复核已标注「只用于定位，不表示本批允许 4」）；max_format_feedback_
   rounds 对 real 路径单 action 的有效轮数由此收敛（轮上限/轮计数判据
   本身未改，scripted 非 fetch 路径不变）。
2. **无重试终态的 resume 判定从 model_structure_failure 变为
   request_not_consumable**：反馈首发传输失败且重试从未登记时，旧 resume
   路径先登记新轮→撞每题预算→model_structure_failure；修后复用既有
   failed 行→链核验无后继→request_not_consumable（零补发；原传输失败
   语义在首发面保持不变，P1-1 测试零翻转）。
3. P1-2 负控「首发行 purpose 篡改」的实际拒绝机制 = S3A-04 同键身份冲突
   （request_identity_conflict，登记路径既有判据）；helper 内
   feedback_round_identity_corrupt 为纵深防御（当前派生面下主要靠登记
   冲突路径拦截，两者均零写入零调用）。
4. P1-4 失败 case「披露了才核」取**键在场即披露**口径：null/字串等非
   bool 在场披露=坏披露拒（§⑤.2「若披露也须严格 bool」从严读法）；
   缺键才豁免。既有 worker 失败路径（evidence_card_flag_invalid/
   budget_guard/run_already_exists 等早失败 case）不写该键，零翻转。

## 十、P1-2 收口轮（2026-10-16 第四轮；Codex 复核2 findings 唯一余项=复用前身份核验漏口，任务书 TASK_CHAIN14_P1_FINAL_2026-10-16）

> 实施子代理单人串行；只修本项（P1-1/P1-3/P1-4 及全部既有正控不动）；
> A 臂字节兼容/判分/池/检索/重试族/gate_max_calls=4470 零触碰；零金标零
> 题面零模型零网络（合成验证沿评审 probe 手法：公开 start_ppv1_run
> (scripted=True, provider_kind=real)+合成 CCO+ScriptedRealModelAdapter
> 状态机+解析前崩溃注入+受控损坏权威 SQLite 原行+公开 resume_ppv1_run）；
> 不 commit 不 push；PYTHONDONTWRITEBYTECODE=1。评审 findings 8 场景反例
> 均先按 result.json 现状表对齐（responded 单字段改坏被复用/sent+registered
> 改坏被消费或另发/failed 来源 payload 未核/原键缺失 2→3 另建第 2 轮），
> 修后全部翻转为结构化拒+零新增调用+零新轮+坏记录保全。

**修复点（文件:行）**：
- `src/pathway_v43/pollutant/model_protocol.py:278-408`（`latest_format_feedback_round`
  重写为**复用前统一身份核验门**）；`:331-346` 附近 `register_format_feedback_round`
  登记载荷确定性化；
- `src/pathway_v43/pollutant/runflow.py:1204-1229`（调用点传当前解析错误与
  重放响应摘录进核验门）。

**统一身份核验判据清单**（门在 `latest_format_feedback_round`，ppv1_real_fetch
状态机（responded/sent/registered/failed）之前一次性闭合，所有状态分支共用）：
1. **原键确定性重算**：轮序由持久计数承载（format_feedback_rounds_used，
   retry_of='' 行）⇒ 最新轮=第 rounds_used 轮，request_id 由原登记键
   `format-feedback:{action}:{round}` 重算（同键复算，不是换键；跨
   attempt/通道不跨源复用）；
2. **计数>0 却查不到应有原行 ⇒ 结构化拒**（reason=original_row_missing）：
   不返回 None 走新登记——那会以 rounds_used+1 构成新键另发一次并洗掉
   坏记录；维持原状（零新增调用、零新轮、坏行保全）；
3. **逐列身份一致**（reason=identity_conflict，conflicts 分列）：查到行的
   purpose/run_id/action_id/attempt_id/provider_kind/retry_of 必须与原登记
   事实（本调用身份）逐列一致——request_id 列未被改时存储行改坏仍被原参数
   命中，列比对揭示篡改；反馈轮首发行 retry_of 必须=''；
4. **payload_hash 同源确定性重算核验**：反馈登记载荷只含同源可重算内容
   （feedback_version/model_protocol_version/round/error_kind/error_detail/
   response_excerpt），**recorded_at 移出载荷**（登记时间由
   model_requests.created_at 持久承载）⇒ 复用前按本调用当前解析错误与重放
   响应重算 content_hash 与存储 payload_hash 比对——原行 payload_hash 被改
   坏、或原登记并非本次错误/响应 ⇒ 拒；不存在「以新 recorded_at 重新生成
   payload 冒充原内容」的面（载荷无时间戳可重算，不指定新存储结构）。
   purpose 被篡改且计数排除的旧路径仍由同键重登记撞 S3A-04 同键身份冲突
   兜底（request_identity_conflict，既有判据零改动）。

**8 场景矩阵测试结果**（tests/test_chain14_evidence_switch_retry.py
`test_feedback_resume_unified_identity_gate_matrix`，合成受控损坏+公开恢复；
每场景断言 run_error kind=feedback_round_identity_corrupt + 零新增调用 +
零新轮/新行 + 坏字段原样保全）：

| # | 受控损坏（现状=被接受/另发，评审 result.json） | 修后实测 |
|---|---|---|
| 1 | responded 原行 run_id 改坏 | 结构化拒；2→2 调用/2→2 行 |
| 2 | responded 原行 attempt_id 改坏 | 同上 |
| 3 | responded 原行 provider_kind real→scripted | 同上 |
| 4 | responded 原行 payload_hash 改坏 | 同上 |
| 5 | sent + provider 改坏（状态同改） | 同上（状态分支消费前已拒） |
| 6 | registered + provider 改坏（状态同改） | 结构化拒，**不分配新轮**（旧 2→3 另发） |
| 7 | failed 原行 payload_hash 改坏（成功后继完整） | 结构化拒；3→3 调用/3→3 行，后继保全 |
| 8 | 原行 request_id 改坏（键缺失） | 结构化拒（original_row_missing）；**不返回 None 走新登记**（旧 2→3 另建第 2 轮），坏行原样保全 |
| 9 | 正控：3→3 反馈重试成功恢复 / 2→2 单次成功恢复 | 照常完成（既有两正控测试零改动通过） |

**全量 not-slow：2193 passed / 0 failed / 16 deselected（349.6s）= 基线
2192/0/16 + 新测 1，零翻转**。定向先行：chain14 文件 33/33 全绿（32 既有
+ 1 新矩阵）。

**偏差/语义清单（如实登记）**：
1. **反馈登记载荷形状变更（去 recorded_at）**：payload_hash 对新登记 run
   全部按新形状计算；model_requests 只存 payload_hash、载荷不外投
   （native_result 投影不含 payload），S3A-04 同键幂等比对语义不变（时间
   事实由 created_at 承载，无信息丢失）；封存 run 只读不受影响（不 resume
   旧形状行；若跨版本 resume 旧行 ⇒ payload_hash 重算失配 ⇒ fail-closed
   结构化拒，不静默接纳）。
2. **核验门签名收紧**：latest_format_feedback_round 新增必填
   error/response_excerpt 关键字参（复用核验必须携带本次解析错误与重放
   响应）；唯一调用点 runflow 已同步，直接调用缺参即 TypeError（fail-closed）。
3. purpose+request_id 双字段同时改坏的合谋形状（计数归 0 → 新登记第 1 轮
   成功、坏行成为孤儿）不在本轮 8 场景矩阵/评审主证明（单字段权威损坏）
   范围内，未扩面处理；评审原文「主证明为单字段身份损坏的 responded 及
   原键缺失场景」。如需覆盖属新验收面，列后续不阻塞本轮。
4. resume 带 run_error 时仍产出部分状态 native_export（既有行为，既有负控
   同形状）：拒绝判据以 run_error.kind + 零新增调用/零新轮为准，不以
   export 缺席为准。
