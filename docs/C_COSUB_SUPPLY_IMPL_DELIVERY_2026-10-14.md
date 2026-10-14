# C 线实施交付书：共底物伴生供给 + 声明链发射（2026-10-14）

> 执行：C 线实施子代理（单个、串行）。任务书 `docs/TASK_C_COSUB_IMPL_2026-10-14.md`；
> 设计书（冻结）`docs/C_COSUB_SUPPLY_DESIGN_PREREG_2026-10-14.md`；
> 探针锚 `reports/ppv1_s5b/c_probe_cosubgate_2026-10-14/`。
> 题域标签：**298 = RHEA 通用酶学/已见题**，不与 dev 互推。
> 探针/验收数字全部为本地进程内离线重放与合成夹具，**不是成绩、不是预注册**。

## 一句话结论

两件事同轮落地并全量自测通过：**① build 期**——analog 模板袋里缺的共底物
按"伴生参与物"补进候选（精确份数、旁观组分逐条披露、wildcard 仍拦），
池策略升 `s5b-pool-policy-7`；**② run 期**——事件提交时把模板记录方程
写进 provenance 声明链（判分侧零改动，照 criteria-v2 §二.1 契约供数）。
实心解锁面复现 **45 行/35 题**（=探针锚，逐行 drift 0）；11 题纯 H₂O 袋
端到端 v2 判分 **5 题的事件升 exact（v1 口径 0）、5 个 v1_exempt 实例、
三谓词全过、声明链 resolved**；非共底物路径字节零漂移。

## 一、改了什么（文件清单）

| 文件 | 改动 | 规模 |
|---|---|---|
| `src/pathway_v43/pollutant/s5b_builder.py` | policy-7 版本承载+注释；`analog_cosub_supply`（语义 a 供给计算：主反应物=与底物最大 Tanimoto、供给=模板袋精确多重集、裸通配拦截、主不可解析 fail-closed）；`_cosub_supply_spectators`（spectator 逐条判定，按供给序对齐）；`analog_record_equation`（模板记录原样两侧）；`_attach_analog_cosub_supply_fields`（声明面装配：participants 显式/co_substrate_states/declared_copy_components(空)/cosubstrate_event_contract/record_equation+ref/execution_input_smiles）；`_compile_analog_refs` 前置门拒后供给救援接线；诊断追加 `analog_cosub_supply_*` | +547/−13 |
| `src/pathway_v43/pollutant/production.py` | `_record_equation_provenance`（发射载荷，fail-closed：不成对/形状坏/条目不可解析一律结构化拒）；`_verify_execution_input`（执行输入首消费核验：组分严格身份多重集==底物⊕声明供给）；`prepare_hypothesis` 传 `provenance_refs` + 下传执行输入；`expand_hypothesis_production` 事件提交前 `put_provenance`（worker 事件提交路径，幂等） | +185/−1 |
| `tests/test_ppv1_s5b_cosub_supply.py` | 新增测试族 10 件（PC-S1..S7/NC-S1..S3，见下） | 508 行 |
| `tests/test_ppv1_s5b_{cosub_d2,hit50_v4b,hit50_v4_wv41,hit50_w23456,pool_lineage}.py` | 版本承载断言同步 policy-6→policy-7；pool_lineage 负控允许 policy-7 追加诊断键 | 小改 |
| `tests/test_controlled_vocab_ci.py` | T11 受控词登记：伴生供给装配的 3 个参与物角色字面量（cosubstrate/primary_substrate/coproduct）入 REGISTERED_LITERAL_SINKS（与 recorded_source.py 同词表） | +4 |
| `docs/C_COSUB_SUPPLY_IMPL_DELIVERY_2026-10-14.md` | 本交付书 | 新增 |

**判分侧零改动**：`evaluation.py` / `s5b_scoring.py` 一行未碰。
**池宽 8 / 阈值 0.45 / 排序 / 截断 / 融合序全部未动**（单变量=共底物伴生供给）。

## 二、验收数字（任务书 §二 五条）

### 1. 解锁面复现 — ✅ 45 行/35 题（=锚）

454 行 COSUB-GATE 逐行用**实现本体**重放（供给计算走
`s5b_builder.analog_cosub_supply`，门/编译走仓内同源判据）：

| 项 | 探针锚 | 实现复现 |
|---|---:|---:|
| 实心解锁面（行/题） | 45 / 35 | **45 / 35** |
| 逐行对账 drift | — | **0**（446 行 outcome 全等 + 8 行 corpus 只分类） |
| 裸通配（`*`）拦截 | 3 行 | **3 行**（wildcard_blocked） |
| 声明面装配冒烟 | — | 45/45 全过、0 错误 |

产物：`reports/ppv1_s5b/c_impl_2026-10-14/unlock_face_replay.{py,json}`。

### 2. v2 豁免正控 — ✅ 豁免计数 5>0、v1_exempt tier 出现

11 题纯 H₂O 袋（探针 d2 `all_exempt_v1` 面）全真实公共链
（policy-7 build → scripted 桩 run → 正式 native export → 判分侧
match_reference_edges v1/v2 双口径）：

| 项 | v1（豁免关） | v2（豁免开） |
|---|---:|---:|
| exact 事件 | **0** | **5** |
| exempted_participants | — | **5**（tier 全 `v1_exempt`） |
| pred1 声明链 | — | 5×`resolved`、5×`pred1=true` |
| pred2 元素账 / pred3 身份 | — | 5×`pass` / 5×成员 |

逐题：5 题事件升 exact（RXNG_3b8991e/5e9b567/7652a03/8dce8a3/8f29c4d），
其余 6 题事件带**非豁免 extras**（机制信息类伴生组分，如实维持 partial——
设计书 §三 预期行为的正控：豁免不洗白机制类）。产物：
`v2_exemption_positive_control.{py,json}`。

### 3. 字节不变 — ✅ 非共底物路径零漂移

差分双 build（同实现树：臂 A=供给关闭〔与 policy-6 旧路径逐语句等价〕，
臂 B=policy-7 原样），298 题全量：

| 类别 | 题数 | 说明 |
|---|---:|---|
| run_inputs 字节全等 | **262** | 非共底物路径零漂移 |
| 纯新增供给 spec | **35** | =解锁面 35 题（交叉印证）；旧 spec 序列按原序子序列保留 |
| W4 补位互动 | **1** | 供给入池抬高独特净反应数→该题不再触发降阈值重检索（臂 A 多拉的 fallback 候选退出）——单变量的合法语义后果，非漂移，如实披露 |
| 诊断 drift | **0** | 非共底物题逐键全等（版本键/供给计数键除外） |

产物：`byte_invariance_probe.{py,json}`。

### 4. 测试红绿 — ✅ 新增 10/10 绿；全量见下

新增控件：PC-S1 装配声明面 / PC-S2 份数多重集（2 H₂O≠1 H₂O+spectator）/
PC-S4 裸通配拦截+[H]\*[H] 不属裸通配 / PC-S5 版本承载 / PC-S6 声明链发射
e2e（store 行+导出链+resolved）/ PC-S7 v2 豁免正控 e2e（v2 exact、v1 维持
partial）/ NC-S1 发射面 fail-closed（不成对/不可解析/执行输入篡改）/ NC-S2
NC-10 复用（participants 删减拒）/ NC-S3 无声明 spec 零变化。
全量 not-slow 结果见 §五（工作树并发说明）。

### 5. 探针级免责 — 如实

**解锁面=供给面编译解锁，不是 hit 预测。** 名次/选择/提交后判分折损未知，
预期兑现率低于解锁面；对齐不落位 197 行残余与形式归一同源（联合面探针挂
后续轮）。§2 的 5 题兑现是"该题的供给候选事件获得豁免升 exact"，
**不是 298 题域成绩数字**（合成/单题脚本环境，非新批次出数）。

## 三、实现口径差异与偏差（逐条如实）

1. **主反应物判定**：实现=模板 lhs 组分与底物的最大 Tanimoto
   （Morgan r2 b2048 立体盲，与 analog 检索同参数；并列取后位）——与
   noalign 归因探针 main_idx 同口径，454 行逐行对账 drift 0 实证同源。
   **主 cn 不可解析 ⇒ 不供给**（fail-closed，防"对齐到供给主副本"错形；
   归因锚面该形态 0 行，无面差）。
2. **wildcard 拦截口径**：裸通配（组分身份恰为 `*`）不供给——35 行维持
   现状拦截；`[H]*[H]`/`*C=O` 等含通配原子的**具体小分子**不属裸通配袋，
   按自身身份供给并披露（=探针 §3/§4 与设计书 45/35=48/38 扣 3 的口径）。
   这 35 行的诊断拒因从原先散布的 charge/no_alignment 统一变为
   `wildcard_blocked` 计数 + no_alignment——拦截结果（不入池）不变。
3. **执行输入声明**（实现新增，设计书未显式列）：伴生供给**参与执行**
   （edits 对底物+供给编译），运行期必须渲染同一输入——spec 携带
   `execution_input_smiles`，prepare 首消费核验组分多重集（防冒充），
   expand 按声明渲染。无声明路径零变化。
4. **record_products 轴语义**（NC-10 复用时钉死）：analog 供给契约的
   `record_products`=**执行净产物全量**（analog 产物执行派生、不复制
   donor rhs，W1 #2）；模板记录两侧走独立的 `record_equation`
   （pred1 声明面）。两个声明面字段级分开，不混用。
5. **发现并修复两处探针口径误读**（实现内自证后修正）：spectator 判定
   按**供给序**逐条对齐（同身份重复组分不折叠）；RDKit 显式 [H:map] 在
   解析时并入重原子（模板 H 账走隐式氢）——两者均有合成正控钉死。
6. **无**范围外改动、无金标/题面触碰、无判分侧改动。

## 四、红线自查

- 判分侧零改动 ✅（evaluation/s5b_scoring 未碰；v1 缺省判分零漂移由 §二.3
  探针+PC-S7 v1 对照实证）
- 金标/题面零外带 ✅（重放/跑批全在本地进程内；产物落 gitignored
  `reports/ppv1_s5b/c_impl_2026-10-14/`，输出仅聚合计数+qid 头代称）
- 不夹带 ✅（工作树存在主窗口并行活文件——`store.py`/`native_result.py`/
  `test_ppv1_s4b_export.py` 的 criteria-v2 P1fix2 回修、预注册 md 在途修改、
  大量未跟踪 docs——本任务 `git add` **只加上表所列本任务文件**）
- 随轮本地 commit 不 push ✅（hash 见 §五）
- 池宽/阈值/排序/融合序/生成侧其余行为不动 ✅（§二.3 探针实证）

## 五、测试与 commit

- 新增测试族：`tests/test_ppv1_s5b_cosub_supply.py` 10/10 绿。
- 定向回归：s5b/ppv1/criteria 相关子集 1543 passed（实现中途多次复跑绿）。
- **全量 not-slow 终版：2135 passed / 0 failed / 16 deselected（零翻转；
  基线 2121/0/16；增量 = 本任务新增 10 件 + 工作树并行 criteria-v2
  P1fix2 会话新增测试件；首次全量 1 红 = T11 受控词登记缺项〔本任务
  新字面量〕，按测试指明通道登记后全绿——已计入上表改动清单）**。
- 注：工作树含主窗口并行 P1fix2 改动（store.py/native_result.py/
  test_ppv1_s4b_export.py 等，未纳入本任务提交）；全量红绿归因以本任务
  定向子集+新增族+提交边界隔离为准，全量数字如实附注。
- commit：本任务随轮本地提交（`git log --oneline -1` 即本交付提交；
  10 文件 +1422/−22；只含本任务文件；**未 push**；hash 不自写入本文件
  ——自引用悖论，以 git log 为准）。

## 六、回传清单

| 项 | 值 |
|---|---|
| 解锁面 | 45 行/35 题（锚 45/35，drift 0） |
| v2 正控 | 豁免 5 实例/5 事件 exact（v1=0）；三谓词全过；声明链 resolved |
| 字节不变 | 262 全等 + 35 纯新增 + 1 补位互动；诊断 drift 0 |
| 新增测试 | 10/10 |
| 产物目录 | `reports/ppv1_s5b/c_impl_2026-10-14/`（脚本+json+progress） |
