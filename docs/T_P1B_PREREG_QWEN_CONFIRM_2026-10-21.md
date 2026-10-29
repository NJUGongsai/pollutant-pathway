# P1-B 方案 A（feedback）预注册草案确认（2026-10-21）

> **provenance：qwen3.8max 代 Codex 复审，按 CC 2026-10-21 指示。**
> 非 Codex 正链终审、非 CC 本人；不冒充。结论采信到与程序证据互证为止。
> **本文只是预注册草案确认，不是付费/HPC 发车批准**（付费与授权归 CC/老师/
> Codex 正链）。
> **已并入 CC 2026-10-21 纠正**：R4 规则级化学复审状态是
> **`PASS_WITH_CONDITIONS`（不是「已通过」）**，4 条措辞级条件未闭合 +
> 58/146 化学真伪 unknown；P1-B「改 edits 提示面」需**独立的**化学规则级
> 评审，尚未完成，属**付费前硬前置**；化学条件未闭前**不得进付费批**。
> 题域：**[298域] = RHEA 通用酶学 / 已见题（post-hoc）**；与 dev 双向不外推。
> 审阅对象：`docs/T_P1B_PREREG_FEEDBACK_2026-10-21.md`（草案 SHA256
> `a9d6183ed5f25605d8e28324bf92fbfeeb5b87b4ec62688492bf8263be3f37ea`）
> 及其上游 6 件 + 证据目录 `docs/review_evidence/p1b_impact_2026-10-21/`
> + `docs/T_H_P0B_D6_CHEM_REVIEW_2026-10-21.md`（R4 规则级化学复审）。
> 本审实际主树 HEAD `966bc5664a7daa30f24860d2b5594a9dddc6eee2`（`git rev-parse`
> 实核）；草案钉的 `baseline_head=11aeeaf…` 与 HEAD 之间
> `git diff --name-only 11aeeaf..HEAD -- src tests scripts` = **0 文件**（仅新增
> docs/review_evidence），代码面等同。
> 本审只读：未改 src/tests/scripts/既有 docs/证据原件；未跑 HPC；未调任何模型；
> 未读金标/题面/reference_graphs 内容/llm.env/私钥；本文不输出化学结构正文。
> 本审独立执行（隔离副本 `/tmp/qwen_p1b_prereg_check` = `git archive HEAD` +
> `impl.patch`；`PYTHONDONTWRITEBYTECODE=1`、`-p no:cacheprovider`、
> Python 3.11.16 / conda env depending43；日志与哈希落
> `docs/review_evidence/qwen_p1b_prereg_confirm_2026-10-21/`）：
> 1. `git apply --check` + 应用 `impl.patch`（SHA256
>    `0ae6535733cf97cbb4439b12e27528fcc7777a770aded2aee8ed8c68a18f491f`）在
>    **当前 HEAD 通过**；patch 恰 4 源文件 + 1 新测试文件；
> 2. `SHA256SUMS_r1fix` 4/4 `OK`；草案 `impl_patch_sha256` 与实测同值；
> 3. r1fix 相对 r0（`b9d91f98…`）逐行 diff = **仅一行**
>    （`return None` → `return None, None`）+ 1 条回归测试（466→510 行）；
> 4. 新测试 **17 passed**、10 文件相关面 **235 passed**、6 文件相关面
>    **197 passed**（=432），全部本审本轮独立复跑，非只信日志；
> 5. `principal_absent_classification.json` 逐字段重算（146/95/146-0-0/66+80/
>    35-91-20/33 题{2:18,3:13,4:1,5:1}/boundary 全 model_declared/origin 全
>    novel/strict_control_rank {1:3,2:2}）与草案 §5.2、§3.3 声明**全部吻合**；
> 6. `strict_control_events.json`（126 strict 题、6 条 inconsistent = 5 absent
>    + 1 stereo）与 `phase_d_replay.py` 选取语义核对（见 §2 核点 3）；
> 7. `disclose_equivalence_r1fix.json`：`all_pass=true`、三方 SHA 均
>    `ab8e976a…78fed1`、`diff_paths` 三组均空、note 明示不含 run_identity
>    （证明范围如实限定）；
> 8. T-I 预注册 / P2 预注册 / TI-F1 任务书 / R4 化学复审逐行核对草案的引用值
>    与化学状态（见 §2）。

## 1. 总裁定

**需修正后放行——但仅限「进入签字准备」；化学条件未闭合前，付费批 NO-GO。**

- 程序/效度面：单变量、复用 2 轮反馈、不新增预算、2 轮后拒
  `declared_product_not_executed`、分母 298、触发面仅 `principal_absent`、
  崩溃 fail-closed、unknown 保持 unknown——**均有代码或本审独立复跑证据支撑，
  无同契约内阻塞缺陷，无「合成绿冒充真实可发车」**。
- **化学面（CC 2026-10-21 纠正后口径）**：R4 是 `PASS_WITH_CONDITIONS`，
  只覆盖 P0b/D-6 **规则级**语义；4 条措辞级条件在冻结合同文本中**实核未落**
  （`T_H_P0B_D6_CONTRACT_2026-10-20.md` 内「立体粒度 / 注记差 / 同位素或 CX /
  participant_list_status / 互变异构 / 质子化微状态」命中数均为 **0**），
  58 stereo_only / 146 principal_absent 的化学真伪仍 unknown；P1-B 新增的
  「改 edits 提示面」**尚无独立化学规则级评审**。⇒ **付费批 NO-GO 直到
  §4-C 两条化学前置闭合**。
- 草案文本必修 9 条（§3 M1–M9），全部是文本级；本文件本就是
  `DRAFT_NOT_SIGNED`，修正属预期动作，不需新设计。
- 最大未登记工程硬前置：**P1-B 专用发车工具链不存在**，且现有 T-I 校验器的
  四文书键集/臂名/脚本锁 schema/no-cap marker 与草案 §9.2 模板**不兼容**
  （直接复用会在 prepare 阶段 fail-closed）→ M6。
- **本审不批准付费、不批准签字**；签字、`no_cap_ack`、模型选定、化学评审送审、
  付费/HPC 授权均归 CC/老师（§4）。

## 2. 逐项审核（对应 CC 指定核点 1–5）

### 核点 1：单变量 / 复用 2 轮 / 无新预算 / 2 轮后拒 / 分母 298 —— **通过（2 处需修正）**

| 检查 | 结论 | 证据 |
|---|---|---|
| 唯一变量 = `P0B_D6_RECONCILIATION_POLICY`（D=disclose / F=feedback） | 成立 | 草案 §2.1/§2.2 冻结表逐项与 T-I 预注册同值（本审逐行核对：题卷 SHA `9f5955d4…`、`s5b-compiler-6`/`pool-policy-9`/`recorded-source-4`/`record-side-formnorm-1`/`analog-route-f1f4-1`、`s5b-corpus-retrieval-6`、`s5b-rank-policy-2`、profile 3/2、gate RPM200/TPM3M/`max_calls=4470`、workers 8/8 全为 T-I 原文同值引用，非新造） |
| 该 env 不在 run identity ⇒ 必须显式记录 | 条款成立、机制缺 | 设计 §2A.5 + 上轮复审 Q5；草案 §2.1 要求写入每臂 `arm_config.json`、smoke2 核对，§6 把「arm_config env 值与臂名不符」列为停批信号——条款正确；但 `ti_operations.py:1371-1417` 的 arm_config 字段集**不含**该 env，机制尚不存在（M6） |
| 复用现有 2 轮 `format_feedback`、不新增预算 | 成立 | 草案 §3.3；上轮已核同 purpose / 同 `format_feedback_rounds_used` 持久计数 / 同 `max_format_feedback_rounds`，且经 `ledger.register_model_request` 即时占每题 3 次真实请求额度；本轮在隔离副本核 `runflow.py:1316/1542` 处理路径存在 |
| 2 轮仍 absent ⇒ 拒 `declared_product_not_executed`、不写事件、分母不变 | 成立 | 草案 §3.2 第 6 条；`production.py:1434` 常量；`production.py:1272` 仅对 `principal_absent`；17 项测试本审独立复跑全绿 |
| 未知 policy 取值 fail-closed | 成立 | `production.py:1489-1503`：非法值抛 RuntimeError，不静默回退 disclose |
| 分母 298、失败/零调用不剔题 | 成立 | 草案 §4.1/§4.3/§10.9，与 T-I §5 同口径 |
| **措辞缺陷 (a)** | 需修正 | §2.2「逻辑调用上限：每题至多 3 次逻辑调用 **+** 2 轮格式反馈」可读成 3+2=5；实际反馈轮从同一 3 次真实请求额度扣（同表下一行才澄清）。冻结表会被任务书/gate 数学照抄 → M1 |
| **登记缺陷 (b)** | 需修正 | 预算挤出通道未显式登记：额度耗尽时 `runflow.py:728/910` 记 `budget_limit` refusal 并**停止该题扩展**（非 run 失败）⇒ F 臂同题后续**非 absent** 候选也可能拿不到真实请求，候选/事件数可能少于 D 臂。§5.4#3 只写「后面的 absent 拿不到反馈」 → M2 |

### 核点 2：触发面仅 `principal_absent`；stereo/isomeric/copy/unknown 不触发不拒 —— **通过（1 处需修正）**

- 代码：单一等值判定 `status=="inconsistent" and inconsistency_subclass=="principal_absent"`（`production.py:1272`），无第二套字符串比较；判据仍走 P0b 单一入口 `reconcile_declared_vs_executed`。
- 正控：6 组非 absent（consistent / stereo_only / isomeric_unspecified / copy 违规 / unknown / not_applicable）不反馈、不拒、正常提交，由新测试覆盖；本轮 17 passed 独立复跑。
- disclose 零漂移：`disclose_equivalence_r1fix.json` `all_pass=true`、三方 SHA 全同、`diff_paths` 全空；范围如实限定「不含 run_identity、合成场景、不替代 298 全链重跑」——**未夸大成真实批等价**。
- §3.1 把「其它 inconsistent 子类（`copy_contract_violation` / `expectation_contradiction` / `assembly_contradiction`）正常提交、不反馈、不拒」写入表格，与代码一致；但这些子类仍是未修的效度缺口，§1.3 未点明 → M3。
- 非 `model_declared` 边界不发反馈直接残余拒：与代码/设计 §2A.4-6 一致；分类 JSON 实核 146 条 `principal_boundary` 全 `model_declared`、`origin` 全 `novel`、`step_scope` 全 `net_reaction` ⇒「本批预期不触发该分支」有数据支撑（该分支无直接测试，上轮列非阻断缺口，草案 §5.4#9 如实登记）。
- **化学侧提醒（与 R4 条件 1/2 直接相关）**：`principal_stereo_only` 不触发本批反馈/拒，这一点程序上正确；但按 R4 未闭合条件 1，该子类含「立体粒度差（指定 vs 未指定）与增强立体注记差」，**不得读作「已证构型错误」**；条件 2 同理，`principal_isomeric_unspecified` 桶必含同位素或 CX 扩展（SGroup）差。草案 §3.1 表格与 §11 报告模板目前**没有**把这两条子类语义限度写进去 → M8。

### 核点 3：停点/风险登记（5 个 strict absent、崩溃 fail-closed）—— **通过（3 处需补）**

- **5 个 strict absent（3 rank1 + 2 rank2）独立重算吻合**：分类 JSON 内 `strict_control_event=True` 恰 5 条、`strict_control_rank` {1:3, 2:2}；`strict_control_events.json` 侧 126 strict 题中 6 条 inconsistent = 5 `principal_absent` + 1 `principal_stereo_only`，与草案 §5.2/§11.6 一致。
- **§5.2 最坏上限有依据**：`phase_d_replay.py`（committed 证据）选取语义是——对每个 `matched_strict` 题取 `candidates[rank-1]`，`rank` = 冻结 scorer 的**首个 strict 命中位次** ⇒ 这 5 个 absent 事件就是**承载命中的事件**；故「rank1 被残余拒 ⇒ hit@1 损失 ≤3 题」「rank1+rank2 ⇒ hit@3/@5 损失 ≤5 事件所在题」是保守上限，方向正确。
- **需补脚注（M4）**：同批 JSON 行里 `audit_cross_ref.strict_target_match=False`（5 absent + 1 stereo 全 False）是**事件局部审计字段**，不等于「scorer 未命中」；不写清可能被后人据此把上限改成 0，或反过来当实测。并应写明：移除承载命中的事件后，同题更后的 strict 命中可能上移 ⇒ ≤3/≤5 是上限非点估计，实数只能由 §3.3 复算给出。
- **unknown 诚实**：§3.3 离线复算**未做**在 §5.2、§8.1 P2、§12 三处一致登记，并明写「不得把 unknown 写成 0 损失，也不得把最坏情况写成实测」「不得用 5 条 strict 上限代替 146 条非 strict 的 hit 贡献」——**未把最坏上限冒充全量结论**。通过。
- **需补（M5）**：§3.3 复算输入是 `/tmp/t_h_p0_r2`（分类 JSON `source` 字段原文指向该路径与 `/tmp/.../runs`）。本审实核该目录**当前存在**但属易失件；仓内只有派生 JSON，原始导出未入仓。要么签字前就地复算，要么登记易失性 + 「需从 HPC 批根重拉、不改封存批」的路径。
- **崩溃 fail-closed**：§5.3 与上轮必核 6 一致（修订 spec 仅在内存、resume 走原始 spec、(a) 同 attempt 重放零新增付费调用 /(b) `feedback_round_identity_corrupt` 结构化拒 → run 失败、题留分母、不静默提交坏事件），并如实登记「路径 (b) 把本可残余拒转成 run 失败、F 臂失败题数可能高于 D 臂」；是否先做修订 artifact 持久化列为 D2 交 CC —— 归属正确，本审不代决。
- **工程停点继承忠实**：§6 与 TI-F1 原文核对一致（smoke2/smoke10/full 阈值、非豁免 `failed>0`、未登记结构性零调用 `>0`、pending、full `>15`、恢复一次/二败停），且明写「工程守卫，不是科学判定线」；§5.1 复盘触发 `Δstrict ≤ −3` 与 P2 预注册 §6.1（原文 line 374）同值，并明写「只触发人工复盘、不构成 F 失败/否决、不改读数、CC 可关」——**未偷设提分线/否决线**。
- NC-9 豁免与 T-I §5 原文一致；建议补精度（并入 M2）：豁免仅限**同 qid + 同登记 reason**（`cosubstrate_copy_expectation`），反馈路径新产生的零调用一律视为未登记 → 停。

### 核点 3b：化学评审状态（CC 2026-10-21 纠正）—— **需修正（草案当前登记不足）**

| 事实（本审实核） | 结论 |
|---|---|
| `docs/T_H_P0B_D6_CHEM_REVIEW_2026-10-21.md` §1 总裁定原文 = 「规则级语义可接受（可冻结）」，0 必须修正、4 项 clarify，并明写「**本报告不解除既有硬挂账**：58 stereo_only / 146 principal_absent 的化学正确性仍需真实结构复核，规则级评审不替代」；§2 Q8 附**冻结条件 (a)(b)**；§3 列 4 条措辞澄清 | 按 CC 2026-10-21 口径记为 **`PASS_WITH_CONDITIONS`**；**不得写成「化学已过」/PASS** |
| 4 条未闭合条件在冻结合同文本中的落地情况：`T_H_P0B_D6_CONTRACT_2026-10-20.md` 对「立体粒度」「注记差」「同位素或 CX」「`participant_list_status`」「互变异构」「质子化微状态」的命中数**均为 0** | 4 条**实核未闭合**（仅存在于评审文档的建议表中） |
| P1-B 草案对上列 4 条的登记：`grep` 命中 **0**；草案只有 §5.4#5「146/58 化学真伪 unknown」、§8.1 P5「改 edits 提示面评审**未做**、不声称已评」、§8.2 D6「是否作为发车硬前置——**待 CC**」 | 草案**没有**把 R4 的 `PASS_WITH_CONDITIONS` 状态与 4 条未闭合条件写进风险面；D6 需按 CC 本次指示回填为「已定：是硬前置」 |
| 设计稿 `T_H_P1B_RECONCILIATION_GATE_DESIGN_2026-10-21.md` line 378 原文：「先化学复核定性（**R4 规则级评审已过**，但 58/146 化学真伪仍 unknown）」 | 与 CC 纠正冲突；该文件是既有 docs，**本审不改**，仅提请文件所有者/CC 更正为 `PASS_WITH_CONDITIONS` |
| P1-B 新增「让模型改 edits」提示面的独立化学规则级评审 | **未取得**；按 CC 2026-10-21 指示列为**付费前硬前置**（四文书 `chem_review` 键），化学条件未闭前付费批 NO-GO |

⇒ 必修 M8（草案登记 R4 真实状态 + 4 条条件 + 子类语义限度）、M9（把「改 edits 提示面」化学评审写成付费前硬前置 + D6 回填为 CC 已定）。

### 核点 4：可否进入签字/付费准备 + 还缺哪些硬前置 —— **修完 M1–M9 可进签字准备；付费前 11 项未闭合**

程序面（本审已核，支持进入签字准备）：r1fix 一行修复已合入且**本审独立复跑** 17+235+197 全绿；patch 在当前 HEAD 干净应用；disclose 三方零漂移 all_pass；146 分类数字全部重算吻合；T-I/P2/TI-F1 引用值逐条忠实。

**新发现（草案未登记 → M6）**：现有 `scripts/hpc/ti_operations.py` 的批准包校验与草案 §9.2 模板**不兼容**：

| 现有校验器事实（实核行号） | 草案模板 | 后果 |
|---|---|---|
| `APPROVAL_REQUIRED_KEYS = ("prereg","task","final_review","script_lock")`（:89）；缺件报错、**多余键也报错**（:1200-1210） | 第四键是 `chem_review` | 直接复用 ⇒ prepare fail-closed（既缺 `final_review`，又含未冻结条目） |
| 脚本锁 `schema` 必须 `t-i-script-lock-1`、`source_commit` 必须等于 cfg（:1247-1252） | 只说「逐文件 SHA」 | 需 P1-B 自己的 schema 与 commit 绑定 |
| `REQUIRED_ARMS = ("glm","deepseek")`（:42），`arms_lock` 按臂校验 | 臂是 `disclose`/`feedback` | 臂集不匹配 |
| `ti_arm_config.json.no_cap`：marker `no_monetary_cap_user_decision_2026-10-20`、`user_decision_date=2026-10-20` | §7/§9.1 用 `2026-10-21` | 需 P1-B 自己的 `budget_no_cap.json` + cfg；且 no-cap 须按**本批**重新知悉——`P2_CC_DECISION_FULL_V2_2026-10-21.md` 是 P2 范围文档，其 §4 明写「旧批、P0b、P1-B(A) 均不受影响」，不能被当作 P1-B 的既有批准 |
| `write_arm_config`/`require_arm_config` 比对固定字段集（:1371-1417），**不含** `P0B_D6_RECONCILIATION_POLICY` | §2.1 要求写进 arm_config 并 smoke2 核对 | 需代码改动 + 测试，否则单变量无法机器核对 |
| `s5b_worker.py:131-135`：无协调者/无冻结副本的手动路径 **默认 `evidence_card_enabled=True`**（`th_run_wrapper.py:33` 才钉 False） | §2.2 冻结「证据卡关」 | wrapper 必须显式传 expected=False + 批根冻结副本；smoke2 断言 `evidence_card_enabled=false`/`mode=frozen_batch`，否则该冻结项无机制保障 |

### 核点 5：本审性质 —— **确认（写明）**

本文只确认预注册草案是否可进入签字流程；**不批准付费、不批准发车、不批准判据变更（v3/T1′ 类）、不批准新付费批、不批准真实题面外发、不认定 R4 通道等效性**。这些只给建议，归 CC/老师。

## 3. 最小回修清单（仅本请求范围内；全部是草案文本级）

| # | 位置 | 修法 |
|---|---|---|
| M1 | §2.2「逻辑调用上限」行 | 改为无歧义：每题**真实模型请求总额度仍为 3**；`format_feedback`（含对账反馈）轮次从同一额度扣，不是 3+2 |
| M2 | §4.2/§4.3 + §5.4#3 | 增逐臂 `budget_limit` refusal 计数与「反馈挤占 ⇒ 同题后续非 absent 候选可能拿不到请求、扩展提前停止（非 run 失败）」；NC-9 豁免限定同 qid + 同登记 reason |
| M3 | §1.3 | 补：P1-B **不修**其它 inconsistent 子类（copy_contract_violation / expectation_contradiction / assembly_contradiction 等），两臂这些子类计数应同分布；不得把 F 臂读成「所有声明-执行不符已修」 |
| M4 | §5.2 | 补脚注：上限推导依据 = `strict_control_rank`（冻结 scorer 首个 strict 命中位次），选中事件即命中承载事件；同行 `audit_cross_ref.strict_target_match=False` 是事件局部审计字段、**不等于 scorer 未命中**；移除后同题更后 strict 命中可能上移，故 ≤3/≤5 是上限非点估计 |
| M5 | §5.2/§8.1 P2、§9.1 | (a) 登记 §3.3 复算输入 `/tmp/t_h_p0_r2` 为易失件（当前存在，实核），仓内只有派生 JSON；签字前就地复算，或写明需从 HPC 批根重拉且不改封存批。(b) `baseline_head` 补：`11aeeaf..HEAD` 仅新增 docs/review_evidence，`src/tests/scripts` **0 文件**变更（实核），代码面与 HEAD `966bc56` 等同；发车以合并 commit 实核为准 |
| M6 | §8.1 增 P11 | 登记「P1-B 专用发车工具链与批准包键集兼容」为硬前置：arms=disclose/feedback、四文书键含 `chem_review`、脚本锁 schema、`source_commit`、no-cap marker/日期=2026-10-21、arm_config 记录并校验 policy env、证据卡 expected=False 机制化 + smoke2 断言；均需代码/配置 + 本机合成正负控测试 |
| M7（建议） | 证据目录 | `SHA256SUMS_r1fix` 未含 `principal_absent_classification.json`（实测 `bbf4a848…`）；建议补完整 SHA256SUMS，便于脚本锁绑定 |
| **M8** | §3.1 表格、§5.4、§8.1 P5、§11.7 | 如实写入 **R4 = `PASS_WITH_CONDITIONS`（不是已过）**，并逐条登记 4 条未闭合条件：① `principal_stereo_only` 含立体粒度差/增强立体注记差，不得读作「已证构型错误」；② `principal_isomeric_unspecified` 桶必含同位素或 CX 扩展（SGroup）差（可伴立体差），连接/电荷差已排除；③ 空参与物判不一致**不读** `participant_list_status=partial`（或改为消费该字段，二选一）；④ 互变异构/质子化微状态/分子盐形态**未归一**，须写入 `does_not_prove`（此类差异不意味着生物学上不同分子物种）。同时写明：本审实核这 4 条在冻结合同文本中命中数为 0（未落地）；58/146 化学真伪 unknown 不因程序级修复解除 |
| **M9** | §8.1 P5、§8.2 D6、§10 | 把「改 edits 提示面」的**独立**化学规则级评审写成**付费前硬前置**（四文书 `chem_review` 键，未取得即不得进付费批）；D6 由「待 CC / 建议是」回填为 **CC 2026-10-21 已定：是硬前置**；§10 增一条红线「化学条件未闭合前不得进付费批、不得把 R4 写成 PASS」 |
| 附带（不属本审可改） | 设计稿 line 378 | 「R4 规则级评审已过」应更正为 `PASS_WITH_CONDITIONS`（4 条条件未闭）；该文件是既有 docs，**本审不改**，提请文件所有者/CC 处理 |

无其它必须修正项。**与上轮结论无冲突**：上轮 §3 唯一必改项（`return None, None`）已修并附回归测试（本审逐行 diff + 独立复跑确认）；上轮 §6「化学规则级评审按三触发点单独送审、不冒充已评」的要求本轮按 CC 纠正**加强**为付费前硬前置，非推翻。

## 4. 仍需 CC/老师（或 Codex 正链）批准/决定的事项

**A. 化学前置（CC 2026-10-21 指示；未闭合 ⇒ 付费批 NO-GO）**

1. **R4 的 4 条 `PASS_WITH_CONDITIONS` 条件闭合**：落进 P0b/D-6 冻结合同文本（或经 CC/Codex 明确以披露方式接受并记录），本审实核当前命中数为 0。
2. **P1-B「改 edits 提示面」独立化学规则级评审**：按仓库 mimo 三触发点（场景 1/2）单独产出请求 md、由 CC 送审、回复原文落盘并作为四文书 `chem_review`；涉题面/金标外发须 CC 逐次拍板。本审不代送、不冒充已评、不认定通道等效性。

**B. 签字与授权**

3. 签字字段回填：`approval_status`/`approved_at`/`approval_source`/`approval_source_kind`/四文书 SHA（现均 TBD）。
4. `no_cap_ack=true`：CC 阅 §7 后按**本批**重新知悉；不得沿用 P2/T-I 的 marker 与日期当作已批。
5. D3 模型 ID（T-I 有效批选定或 CC 指定；两臂同值；发车后不得换）。
6. D1（是否启用 `Δstrict ≤ −3` 复盘触发）、D2（是否要求付费批前做修订 artifact 持久化）、D4（是否要 gate 对照臂）。D6 按 CC 本次指示已定为硬前置，只需回填文本。
7. 付费/HPC 发车授权、批根独立、旧批零回写、push 时机。
8. 判据冻结类（v3/T1′）、新付费批、真实题面外发：不在本审职权，仅提示需另走拍板。

**C. 付费前硬前置清单（工程/文书，逐项未闭合）**

| # | 前置 | 状态 |
|---|---|---|
| 1 | R4 4 条化学条件闭合（§4-A1） | **未闭合**（实核命中 0） |
| 2 | 「改 edits」提示面独立化学规则级评审（§4-A2） | **未取得** |
| 3 | model_id | **TBD**（T-I 站点阻塞） |
| 4 | P1-B 专用发车工具链：arm config（arms=disclose/feedback、expected_model_id、policy env 字段）+ operations 模块（approval 键集含 `chem_review`、脚本锁 schema、`source_commit`、no-cap marker/日期 2026-10-21）+ 本机合成正负控测试 | **不存在**（仓内只有 ti_/th_ 两套且键集/臂名/schema/marker 不兼容） |
| 5 | 证据卡关的机制化（wrapper 显式 expected=False + 批根冻结副本 + smoke2 断言） | **未做**（worker 手动路径默认 True） |
| 6 | 任务书 `TASK_P1B_FEEDBACK_LAUNCH_*.md`（含 §6 停点可执行判定、env 记录、批根/回滚、易失件清单） | **未生成** |
| 7 | 脚本锁 JSON（逐文件 SHA，绑 `impl.patch 0ae653…`、prereg、task；建议纳入分类 JSON `bbf4a8…`） | **未生成** |
| 8 | 四文书 SHA 回填 + 签字 + `no_cap_ack=true` | **待 CC** |
| 9 | §3.3 残余拒离线命中损失复算 | **未做**（建议签字前做，`/tmp` 冻结副本现存） |
| 10 | 题卷 SHA `9f5955d4…` 在 HPC 侧发车日实核 | **本机不可核**（本地同名文件均属 dev 域、哈希不同） |
| 11 | 付费/HPC 授权 | **未做**；本审不授权 |

## 5. unknown / 未核清单（保持 unknown，不因本审解除）

- **58 stereo_only / 146 principal_absent 的化学真伪**——R4 只是规则级
  `PASS_WITH_CONDITIONS`，真实结构复核未做；程序级修复 ≠ 化学正确；本审不作
  任何化学结论。
- **R4 的 4 条条件是否/何时闭合**、**R4 通道等效性**（该规则级评审可否充抵
  R4 硬挂账所要求的化学评审）——归 CC/Codex 认定，本审未认定。
- **P1-B「改 edits」提示面的化学可接受性**——未评审，unknown；不得因程序测试
  全绿推断化学合理。
- **F 臂实际回收率**（含 66 disjoint vs 80 overlap 分层）——只能新批测量；本审
  未测、不估。
- **§3.3 残余拒离线命中损失**——未做；本审只核「最坏上限的推导依据成立」，
  未产生实数。
- **model_id**——TBD；本审未指定、不推荐。
- **题卷 SHA `9f5955d4…`**——本机无可核文件，只与 T-I 预注册同值互证。
- **P1-B 发车工具链行为**（prepare/smoke2 对 policy env 的记录与断言、四文书
  校验、证据卡断言）——尚不存在，未核。
- **真实 HPC 复跑、崩溃注入实测、resume 场景 (a) 在真实 attempt 语义下是否
  可达**——未做（上轮同样未做）。
- **RDKit 2026.03.6（本机）vs 2026.03.5（批内登记）逐事件对照**——未做。
- **全量 2365/1**——本轮未复跑；沿用上轮结论（唯一失败为主树通过的环境路径
  断言，与 patch 无关）。本轮独立复跑的是 17 + 235 + 197。
- **`/tmp/dependingv43_p1b`、`/tmp/t_h_p0_r2`** 当前存在但为易失件；本审结论
  基于当前快照。

## 6. 结论一句话

草案在「单变量、无新预算、只碰 `principal_absent`、2 轮后拒、分母 298、
fail-closed、unknown 不冒充实数」这些效度与诚实性要点上**站得住**，数字全部
经本审独立重算/复跑吻合；但**化学面必须按 CC 纠正记为
`PASS_WITH_CONDITIONS`**——R4 的 4 条条件在冻结文本中实核未落地、P1-B 新提示面
尚无独立化学评审。修完 M1–M9 后**可交 CC 签字准备**；**化学条件未闭合前付费批
NO-GO**；付费与发车不归本审。
