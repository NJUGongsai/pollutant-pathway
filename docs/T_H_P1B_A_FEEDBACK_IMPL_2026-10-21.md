# T-H P1-B A（修复反馈）实施报告（2026-10-21）

> **题域：[298域] = RHEA 通用酶学 / 已见题（post-hoc）。** 本文全部计数、
> 结论与证据只在该题域成立，不外推到 dev、新题或其他题域。
>
> **性质：效度修复（A 修复反馈），不是提分项。** 默认 `disclose` 与基线
> 逐字节等价；`feedback` 只在 P1-B 预注册批作为单变量实验臂启用；`gate`
> 只作对照/残余。未跑 HPC、未调真实模型、未读金标/题面/参考图内容、
> 未 push、未写封存批根/runs 根、未改判分/池/检索/排序/R1–R7。
>
> 基线 HEAD：`11aeeaf`（父 `c9c6c7a`）。实现位置：独立 worktree
> `/tmp/dependingv43_p1b`（detached 11aeeaf）；主树 src/tests 零改动。
> 设计：`docs/T_H_P1B_RECONCILIATION_GATE_DESIGN_2026-10-21.md` §2A。
>
> **2026-10-21 r1fix（qwen 复审 §3 必改项已修）**：`impl.patch` 已更新为
> SHA256 `0ae65357…a18f491f`；旧 r0 patch 保留为
> `impl_r1_b9d91f98.patch`（SHA256 `b9d91f98…d9d181d4`）。§1–§10 为
> r0 历史快照，不覆盖；回修与复跑证据见 **§11**。

## 1. 交付物

| 件 | 路径 |
|---|---|
| 设计稿（A 首选 + B 残余） | `docs/T_H_P1B_RECONCILIATION_GATE_DESIGN_2026-10-21.md` |
| 实施报告（本文） | `docs/T_H_P1B_A_FEEDBACK_IMPL_2026-10-21.md` |
| patch（4 源文件 + 1 新测试；r1fix 当前值） | `docs/review_evidence/p1b_impact_2026-10-21/impl.patch`（SHA256 `0ae6535733cf97cbb4439b12e27528fcc7777a770aded2aee8ed8c68a18f491f`；r0=`impl_r1_b9d91f98.patch`，见 §11） |
| 146 条只读影响分类 | `docs/review_evidence/p1b_impact_2026-10-21/principal_absent_classification.json` |
| disclose 零漂移证据 | `docs/review_evidence/p1b_impact_2026-10-21/disclose_equivalence.json` |
| 测试日志 | `docs/review_evidence/p1b_impact_2026-10-21/test_run_{new,relevant,full}.log` |
| Qwen 复审请求 | `docs/T_H_P1B_A_FEEDBACK_QWEN_REVIEW_REQUEST_2026-10-21.md` |

## 2. 改动面（白名单核对）

patch 只包含：

| 文件 | 改动 |
|---|---|
| `src/pathway_v43/pollutant/production.py` | `P0B_D6_RECONCILIATION_*` 开关/常量；`p0b_d6_reconciliation_policy()`；`p0b_d6_origin_from_logical_id()`；`_p0b_d6_action_payload()`；`_p0b_d6_event_product_side()`；`_p0b_d6_reconcile_for_production()`；`_p0b_d6_row_summary()`；`write_reconciliation_rejection_report()`；`expand_hypothesis_production(..., reconciliation_policy/reconciliation_spec/reconciliation_history)` 的提交前分支。**未改** prepare/execute/admission/既有 disclose 路径。 |
| `src/pathway_v43/pollutant/runflow.py` | `_run_expand` 消费 `revision_required`；`_reconciliation_feedback_revision()`；`_record_reconciliation_rejection()`；`_call_real_fetch` 新增可选 `prompt_payload/request_key/purpose` 覆盖（缺省路径不变）。 |
| `src/pathway_v43/pollutant/model_protocol.py` | 新增 `FEEDBACK_KIND_DECLARED_PRODUCT_NOT_EXECUTED` / `RECONCILIATION_FEEDBACK_ELIGIBLE`；`register_format_feedback_round(..., allowed_error_kinds=None)`。**同一 purpose/同一 `format_feedback_rounds_used`/同一 `max_format_feedback_rounds`**；既有四类 JSON 错误不变。 |
| `src/pathway_v43/pollutant/real_model.py` | `build_proposals_user_payload(..., reconciliation_feedback=None)`；`_send_and_settle` 透传。无该块时输出逐字节不变。 |
| `tests/test_p1b_reconciliation_feedback.py`（新增） | 16 项正负控；stub/scripted，零真实调用。 |

未改 `native_result.py`、`native_export.py`、`evaluation.py`、
`s5b_scoring.py`、`store.py`、`reference_graph.py`、`profile.py`、
`questions.jsonl`、`llm.env`、T-I 树；未新增第六个源码文件；未改既有
测试断言。

## 3. 实现语义

### 3.1 触发

只在**执行后、admission 可提交后、事件提交前**，对
`reconcile_declared_vs_executed` 的
`status=inconsistent` 且 `inconsistency_subclass=principal_absent` 动作：

- `consistent` / `principal_stereo_only` / `principal_isomeric_unspecified`
  / `unknown` / `not_applicable` / 其它 inconsistent 子类：不反馈、不拒，
  正常提交（与 P0b 披露口径一致）。
- 复用 P0b 单一判据；不另写字符串比较/身份/规范器。

### 3.2 反馈内容

结构化 `feedback_error`（`kind=declared_product_not_executed`）+
用户载荷 `reconciliation_feedback` 块：

- 模型自己的当前 `reaction_spec`、声明主产物、共同产物；
- 实际执行碎片 `execution.result.product_smiles`；
- 对账摘要（relation/boundary/`declared_missing_from_executed`/
  `executed_extra`/rank1 归属）；
- 指令：保持声明主产物/共同产物/expectation/requirements/dependencies/
  assumptions/transformation_ref **不变**，只改 edits（必要时
  donor/alignment），使声明主产物真实出现在执行碎片中。

不读金标/参考图/题面/`reference_graphs`/`questions.jsonl`/`llm.env`。

### 3.3 预算（不新增）

- purpose 仍 `format_feedback`；
- 轮数仍由 `format_feedback_rounds_used(ledger, action_id)` 持久计数；
- 上限仍 `max_format_feedback_rounds`（T-I/chain13 = 2）；
- 每 expand action 最多 2 轮；每轮仍受 run 级
  `max_real_model_requests`（每题 3）即时占额；
- **不新增 purpose/轮数/调用上限/计数器**。

### 3.4 流程

1. 执行 edits → audit → admission（R1–R7 不变；只对可提交候选进对账）；
2. 构建事件/投影/展开计划 → 同一 P0b 判据对账；
3. `principal_absent` 且 principal 边界 `model_declared`：
   - 未提交；登记/复用反馈轮 → 取模型响应；
   - revised spec 只允许覆盖 `edits/donor/alignment`；
     `product_smiles/coproducts/copy/requirements/dependencies/assumptions/
     transformation_ref/expectation/compile/...` 出现且不同 ⇒ 该轮失败；
   - revised edits 必须与当前 edits 不同且过 `validate_edits`；
   - 重建 prepared：`hypothesis_id` 必须 == action `subject_ref`
     （事件身份冻结门）；
   - 重新执行/对账；一致 ⇒ 正常提交；仍 absent 且还有轮 ⇒ 再反馈；
     2 轮耗尽 ⇒ 残余拒；
4. 非 `model_declared` 边界（compiled/unknown）不发起反馈，直接残余拒；
5. 反馈响应不可解析 / 改身份字段 / edits 非法或未变：该轮失败，
   **直接残余拒**（不再花第二轮）；
6. 残余拒：structured reason=`declared_product_not_executed`；不写事件；
   action 记 `admission_rejected`（detail 带 `p0b_d6`/history/轮数）；
   候选/池/分母不变；写 rejected production_report（无事件身份）；
7. 传输失败/超时/悬空：既有 run 失败语义（失败题留分母），不吞成拒/成功。

### 3.5 开关

`P0B_D6_RECONCILIATION_POLICY`：

| 取值 | 行为 |
|---|---|
| `disclose`（默认） | 不执行对账段；不写 `p0b_d6` 键；不登记反馈；与基线逐字节等价 |
| `feedback` | A 实验臂（上述流程） |
| `gate` | 纯 B：principal_absent 直接残余拒，不发反馈（仅对照/残余） |

未知取值 `ProductionContractError(kind=p0b_d6_reconciliation_policy_invalid)`
fail-closed，不静默回退。

## 4. 测试与回归

| 项 | 结果 |
|---|---|
| 新测试 `tests/test_p1b_reconciliation_feedback.py` | **16 passed** |
| 相关既有面（P0b/生产/模型/队列/runner/r2/r3/endpoint/export/T11） | **203 passed** |
| 全量 `pytest tests`（worktree，终版代码） | **2365 passed, 1 failed, 1 warning**（687.69s） |
| 唯一失败 | `tests/test_engine_asset_parity.py::test_arms_ran_on_expected_roots`：断言 `/private/tmp/dependingv3/assets` vs 实际 `/Volumes/CC/Enzyme_Agent/dependingv3/assets`（symlink 被 resolve）；**主树同测试 1 passed**，与本 patch 无关（与 P0b §4 已披露的环境路径问题同源） |
| patch 应用 | 在全新 11aeeaf worktree `git apply --check` + 应用通过；16 新测试全过 |

新测试覆盖（对应任务 6 项）：

1. `test_absent_feedback_once_then_repair_submits`：absent → 1 轮反馈 →
   改 edits → 提交；`format_feedback` 行 1 条、purpose/轮数正确；
2. `test_absent_two_rounds_rejects_without_event`：两次不同的有效修订仍
   absent → 2 轮 → 拒；0 事件；history 5 条；
3. `test_non_absent_statuses_do_not_feedback_or_reject`（6 组）：
   consistent/stereo/isomeric/copy/unknown/not_applicable → 不反馈、不拒；
   `test_consistent_without_feedback_submits` 真链一致正控；
4. `test_feedback_rounds_zero_rejects_absent`：0 轮预算 → 直接残余拒；
   `test_reconciliation_feedback_uses_existing_purpose_and_budget`：
   同 purpose/同一上限；第 3 次超限；不带 allowed 类别时不可进 JSON 反馈；
5. `test_disclose_never_calls_reconcile_and_adds_no_keys`：disclose 路径
   连 reconcile 都不调用；无 `p0b_d6` 键；无反馈行；事件照常；
   `disclose_equivalence.json` 三方哈希一致；
6. `test_gate_rejects_principal_absent_without_event`：B 残余/对照分支；
   `test_feedback_response_changing_declared_principal_rejected`：改声明
   主产物 ⇒ 直接残余拒并写 rejected report；
   `test_reconciliation_feedback_payload_rendering`：无该块时旧载荷同形。

## 5. disclose 零漂移（正式证据）

`docs/review_evidence/p1b_impact_2026-10-21/disclose_equivalence.json`：

| 比较 | 结果 |
|---|---|
| base 11aeeaf vs 补丁默认（env 未设） | pass |
| base 11aeeaf vs 补丁显式 `disclose` | pass |
| 补丁默认 vs 补丁显式 `disclose` | pass |
| 三方确定性载荷 SHA256 | 均 `ab8e976a0324212dff518f627e321fddcd22eddb54c488ecc50318ee0378fed1` |

- 场景：scripted CCO 坏 edits 候选（声明 CC=O，edits 断 C-C），一个
  abstain 响应，`max_format_feedback_rounds=2`。
- 比较面：`events/hypotheses/states/state_appearances/search_actions/
  search_attempts/search_commit_records/model_requests/report_projections/
  expansion_plans/budget_reservations` 去时间字段后的行 +
  `results/**` artifact payload（native-result envelope 的易失
  `task_id`/`payload_hash` 不计）。
- **不包含** `run_identity.json`：补丁必然改变代码身份；本证据只声明
  执行载荷/表行为等价，不声明 run-identity 等价。
- 该证据是**合成场景**，不是 298 题全链重跑；不替代 T-I 新批。

## 6. 146 条 principal_absent 影响分类（零成本）

| 项 | 数值 |
|---|---:|
| principal_absent 事件 | 146 |
| 涉及题数（qid 前缀） | 95 |
| 真声明-执行不符（程序级） | 146 |
| 合法多步/装配分工 | 0 |
| unknown（元数据不足） | 0 |
| disjoint / overlap | 66 / 80 |
| 声明共同产物 0/1/2 个 | 35 / 91 / 20 |
| 6 个 strict 对照中的 absent | 5（3 rank1 + 2 rank2） |
| 有 2–5 条 absent 的题 | 33 |

- 146 条全部 novel、无 `compile`、principal `model_declared`、
  `step_scope=net_reaction`、rank1 归属与声明一致、expectation 含声明
  主产物 ⇒ 全部落“真声明-执行不符”；没有可归为“合法多步/装配分工”的
  元数据依据。
- **程序级分类 ≠ 化学真伪**；146 条的化学正确性仍 unknown。
- 33 题多 absent 会争用每题 3 次真实请求额度，是 A 的真实代价。

## 7. 仍缺的前置 / unknown

| 项 | 状态 |
|---|---|
| 多轮反馈的崩溃恢复 | 修订 spec 只在当前进程内存中；若在修订应用后、`write_commit_bundle` 前崩溃，resume 会从 action 冻结的**原始 spec** 重跑，既有反馈轮身份核验（`latest_format_feedback_round`）会 fail-closed（`feedback_round_identity_corrupt`），**不会静默提交错误事件**；bundle 写出后的崩溃由既有 B3 恢复消费修订事件。若预注册批要求反馈路径的 B1–B4 全恢复，需后续单独设计“修订 artifact”持久化；本实现不声称该面已闭合 |
| 开关冻结 | `P0B_D6_RECONCILIATION_POLICY` 是运行期 env，**不在** run identity/profile 块（未改 `profile.py`）；预注册/发车脚本必须显式记录该值，并保证两臂只差这一项 |
| P1-B 预注册（单变量 `feedback`、A 可能降分/回收率 unknown 的报告口径） | **未做**；需 CC/Codex 拍板 |
| 付费批 / T-I 发车 | **未做**；另需预注册与费用记录 |
| A 的实际回收率 | **unknown**；只能新批测量（离线不能模拟模型改对） |
| B 残余拒的离线命中损失 | **未做**；需冻结 scorer 复算（A 全部失败的最坏情况） |
| 化学评审 | 本轮未送审；A 新增“让模型改 edits”的提示面，规则级化学评审仍按仓库触发点单独产出/送审 |
| 真实结构化学复核 | 146 absent / 58 stereo 的化学真伪仍 unknown，不因本实现解除 |
| 全链 298 题 production/compiler/model 重跑 | 未做；disclose 证据只到合成场景 |
| RDKit 版本差 | 本机 2026.03.6；P0b/T-H 批登记 2026.03.5；未观察到本实现的分类漂移，但未做逐事件版本对照 |
| 无效修订/预算耗尽路径的 production_report | 已补 `write_reconciliation_rejection_report`；与 gate/轮数耗尽的 rejected report 同形 |

## 8. 复现命令

```bash
# 1) worktree
git -C /Volumes/CC/Enzyme_Agent/dependingv43 worktree add \
  /tmp/dependingv43_p1b 11aeeaf
git -C /tmp/dependingv43_p1b apply \
  /Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/p1b_impact_2026-10-21/impl.patch

# 2) 新测试 + 相关既有面
cd /tmp/dependingv43_p1b
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src \
  ~/miniconda3/envs/depending43/bin/python -m pytest \
  tests/test_p1b_reconciliation_feedback.py -q -p no:cacheprovider

# 3) disclose 三方等价
cd /Volumes/CC/Enzyme_Agent/dependingv43
PYTHONDONTWRITEBYTECODE=1 ~/miniconda3/envs/depending43/bin/python \
  docs/review_evidence/p1b_impact_2026-10-21/disclose_equivalence.py

# 4) 146 分类
PYTHONDONTWRITEBYTECODE=1 ~/miniconda3/envs/depending43/bin/python \
  docs/review_evidence/p1b_impact_2026-10-21/classify_principal_absent.py
```

## 9. 红线合规

- 主树 src/tests 零改动；未合并、未 push；全部代码改动在
  `/tmp/dependingv43_p1b`。
- 未跑 HPC/sbatch；未调真实模型/外部网络；未读金标/题面/
  `reference_graphs` 内容/`llm.env`/私钥；分类/证据输出无真实候选或
  金标结构正文（合成正负控固定使用 CCO/CC=O 作测试夹具，不涉及
  298 域真实候选）。
- 未写封存批根/runs 根；未回写旧成绩；未把 absent 写成“化学错误”；
  unknown 未洗成通过。
- 未改 R1–R7、`ADMISSION_SUBMITTABLE`、评分/池/检索/排序/prompt 版本。
- 默认 `disclose` 与基线逐字节等价（合成场景三方哈希一致）。

## 10. 交审状态

**程序面具备交 QwenReviewer 复审条件**：设计稿 A 章、patch、16 项新
测试、203 项相关回归、全量回归（唯一失败为已披露环境路径）、disclose
三方等价、146 分类证据齐备。

**仍缺**：预注册、付费批、A 实际回收率、B 残余命中损失离线复算、
化学规则级/真实结构复核。以上不由本实施自行放行。

## 11. r1fix addendum（2026-10-21；qwen 复审 §3 必改项）

> 题域同上：**[298域]**。本节是 §1–§10 之后的最小回修快照；前文保留为
> r0 历史记录，不回写。

### 11.1 必改项与修复

- qwen 复审唯一必须修正项：`production.py::_p0b_d6_event_product_side`
  的非 dict 参与物分支裸 `return None`。调用方
  `refs, smiles = _p0b_d6_event_product_side(...)` 会解包失败抛
  `TypeError`（非结构化崩溃），且与同义源
  `native_result._p0b_d6_product_participants` 的 `return None, None`
  不一致。
- 修复：该分支改为 **`return None, None`**（仅一行）。
- 回归：新增
  `tests/test_p1b_reconciliation_feedback.py::test_non_dict_event_participant_is_unknown_not_reject`，
  断言 helper 返回 `(None, None)`、对账落 `unknown`
  （`event_assembly_unavailable`）、不构成 `principal_absent` 拒因。
- 除该一行 + 新测试外，无其它代码改动；仍是 4 源文件 + 1 新测试。

### 11.2 新的 patch 与证据

| 件 | 值 |
|---|---|
| `impl.patch`（r1fix） | SHA256 `0ae6535733cf97cbb4439b12e27528fcc7777a770aded2aee8ed8c68a18f491f` |
| `impl_r1_b9d91f98.patch`（r0 保留） | SHA256 `b9d91f985c152a7633cd5cc213aa253829addcba5eebae42fa7f93fcd9d181d4` |
| `test_run_r1fix.log` | HEAD `11aeeaf`；17 passed；235 passed；197 passed |
| `disclose_equivalence_r1fix.json` | 三方 `all_pass=true`；SHA 均 `ab8e976a…78fed1` |
| `SHA256SUMS_r1fix` | 上述件逐件 SHA |

### 11.3 复跑结果（本机隔离）

| 面 | 结果 |
|---|---|
| 新测试（原 16 + 1 回归） | **17 passed** |
| qwen 432 项相关面口径（10 文件 235 + 6 文件 197） | **432 passed** |
| 全新 11aeeaf worktree `git apply --check` + 应用 | 通过；17 passed |
| disclose 三方等价（隔离 tmp 复制脚本，非证据目录原地跑） | `all_pass=true`；三方 SHA 均 `ab8e976a…`，与 r0 落盘一致 |

### 11.4 未改变项

- disclose/gate 语义、触发面、预算口径、身份门、146 分类均未改；
- A 回收率、B 残余命中损失、146/58 化学真伪、真实 HPC/RDKit 差仍为
  unknown；
- 预注册仍未签字；付费批/HPC 未做。