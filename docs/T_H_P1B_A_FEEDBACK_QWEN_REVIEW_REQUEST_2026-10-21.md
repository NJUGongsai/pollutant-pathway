# T-H P1-B A（修复反馈）QwenReviewer 复审请求（2026-10-21）

> **题域：[298域] = RHEA 通用酶学 / 已见题（post-hoc）。** 本请求及所附
> 材料只在该题域成立；合成控制不是科学性能，不外推到 dev/新题。
>
> **送审对象：** 设计稿 A 章 + patch + 测试 + 证据。**本轮未调用真实
> 模型/付费批/HPC**；请求方已完成程序正负控与 disclose 零漂移，但
> **A 的实际回收率、B 残余拒的命中损失、146 条的化学真伪均 unknown**。
>
> **2026-10-21 r1fix（对 qwen 复审 §3 必改项的回应）**：`_p0b_d6_event_product_side`
> 非 dict 参与物分支已由裸 `return None` 改为 **`return None, None`**，并补
> 1 条回归测试（`test_non_dict_event_participant_is_unknown_not_reject`）。
> 新 patch SHA256 = `0ae6535733cf97cbb4439b12e27528fcc7777a770aded2aee8ed8c68a18f491f`；
> 旧 patch 保留为 `impl_r1_b9d91f98.patch`。复跑：新测试 **17 passed**、
> qwen 432 项相关面 **432 passed**、disclose 三方 `all_pass=true`（SHA 均
> `ab8e976a…78fed1`）。证据见 `test_run_r1fix.log`、
> `disclose_equivalence_r1fix.json`、`SHA256SUMS_r1fix`。
>
> **评审纪律（请逐条遵守）：**
> - 只读；可读下列文件，不执行付费批、不调外部模型、不跑 HPC。
> - 不读金标/题面/`reference_graphs` 内容/`questions.jsonl`/`llm.env`/
>   私钥；不要求提供结构正文。
> - 结论采信到与程序证据互证为止；不得把合成控制当科学性能。
> - 不冒充 Codex 正链终审；本请求由 CC 决定送审通道与采信顺序。

## 1. 输入文件（全部自包含）

| # | 件 | 路径 |
|---|---|---|
| 1 | 设计稿（A 首选 + B 残余；§2A 为 A） | `docs/T_H_P1B_RECONCILIATION_GATE_DESIGN_2026-10-21.md` |
| 2 | 实施报告 | `docs/T_H_P1B_A_FEEDBACK_IMPL_2026-10-21.md` |
| 3 | patch（4 源文件 + 1 新测试；r1fix） | `docs/review_evidence/p1b_impact_2026-10-21/impl.patch`（SHA256 `0ae6535733cf97cbb4439b12e27528fcc7777a770aded2aee8ed8c68a18f491f`；r0=`impl_r1_b9d91f98.patch`） |
| 4 | 新测试 | `tests/test_p1b_reconciliation_feedback.py`（在 worktree `/tmp/dependingv43_p1b`） |
| 5 | 146 分类证据 | `docs/review_evidence/p1b_impact_2026-10-21/principal_absent_classification.json` |
| 6 | disclose 三方等价 | `docs/review_evidence/p1b_impact_2026-10-21/disclose_equivalence.json` |
| 7 | 测试日志 | `docs/review_evidence/p1b_impact_2026-10-21/test_run_{new,relevant,full}.log` |
| 8 | P0b 合同/复审背景 | `docs/T_H_P0B_D6_CONTRACT_2026-10-20.md`、`docs/T_H_P0B_D6_QWEN_REREVIEW_2026-10-21.md` |
| 9 | r1fix 复跑证据 | `docs/review_evidence/p1b_impact_2026-10-21/` 下 `test_run_r1fix.log`、`disclose_equivalence_r1fix.json`、`SHA256SUMS_r1fix` |

基线 HEAD `11aeeaf`；实现 worktree `/tmp/dependingv43_p1b`（主树 src/tests
零改动）。patch 在全新 11aeeaf worktree `git apply --check` + 应用通过。

## 2. 请评审的规则点（按 A 章逐条）

### Q1 触发是否正确

- 只对 `status=inconsistent` 且 `inconsistency_subclass=principal_absent`
  触发反馈/拒；
- `consistent` / `principal_stereo_only` / `principal_isomeric_unspecified`
  / `unknown` / `not_applicable` / 其它 inconsistent 子类不反馈、不拒；
- 是否错误地把 stereo/isomeric/copy/unknown 纳入反馈或拒？
- `principal_absent` 的判定是否仍复用 P0b 单一判据（无第二套字符串比较）？

### Q2 反馈内容是否只涉及模型自己的声明/执行

- 反馈块只含当前 `reaction_spec`、声明主产物/共同产物、执行碎片、
  对账计数/关系/归属、指令；
- 是否读了金标/参考图/题面/reference_graphs？
- 对真实模型而言，这些摘要是否足以修 edits，且不诱导其改判据/评分？

### Q3 预算是否真的没有新增

- purpose 仍 `format_feedback`；轮数仍
  `format_feedback_rounds_used(ledger, action_id)`；上限仍
  `max_format_feedback_rounds`（T-I=2）；
- 每 expand action 最多 2 轮；每轮仍受 run 级
  `max_real_model_requests`（每题 3）即时占额；
- 是否出现新 purpose/新计数器/新调用上限/绕过预算的路径？
- 反馈登记新增 `declared_product_not_executed` 可接受类别，是否侵占了
  既有四类 JSON 格式反馈的语义/预算？

### Q4 流程与身份是否闭合

- 执行 → 检测 → 未提交 → 反馈 → 修订 → 重建 prepared → 重执行 →
  对账 → 一致才提交；
- revised spec 只允许覆盖 `edits/donor/alignment`；
  `product_smiles/coproducts/copy/requirements/dependencies/assumptions/
  transformation_ref/expectation/compile/...` 必须不变；
- 新 `hypothesis_id` 必须 == action `subject_ref`（事件身份冻结门）；
- 是否存在“改 expectation/改声明主产物”绕过 `principal_absent` 判据、
  或把不同假设塞进同一 action 的路径？
- 2 轮耗尽/非 model_declared/坏响应 ⇒ 拒提交；不写事件；分母不变；
- 传输失败是否仍走 run 失败（不吞成拒/成功）？

### Q5 disclose 默认是否零漂移

- 默认 `disclose` 是否完全不调用 reconcile、不写 `p0b_d6` 键、不登记
  反馈、不改变事件/报告/候选/排序？
- `disclose_equivalence.json` 的三方 SHA256 相同，其证明范围是否被
  如实限定（合成场景；不含 run_identity；不替代 298 全链重跑）？
- `gate` 是否只作对照/残余，不被误当实验臂？

### Q6 测试是否足以支撑“可交预注册”

- 16 项新测试是否覆盖：1 轮修复提交、2 轮持续 absent 拒、非 absent
  六组不触发、0 轮预算拒、同 purpose/上限、disclose 不调用、gate 拒、
  身份变化拒、载荷渲染同形？
- 是否有“只测状态不测行为”的弱点（例如只看 `status` 不看事件/报告）？
- 全量 2365 passed / 1 failed（已知 symlink 环境路径，主树同测试通过）
  是否被如实披露，而非当作“全绿”？
- 相关既有面 203 passed 是否覆盖 production/endpoint/export/T11？

### Q7 红线与范围

- 是否改判分/池/检索/排序/prompt/R1–R7/答案定义？
- 是否回溯改旧批/封存 run/旧成绩？
- 是否新增第六个源码文件或读金标/参考图？
- 146 条分类的“146 真不符 / 0 合法多步 / 0 unknown”是否被过度解读？
  程序级分类 ≠ 化学真伪是否写清？
- 33 题多 absent 争用每题 3 次真实请求额度的代价是否被如实登记？

### Q8 总体

- 是否存在**阻塞**缺陷（同合同内具体代码/公共链证据）？
- 是否存在非阻塞观察/措辞澄清？
- 是否具备进入 P1-B 预注册的条件（不是问是否付费/发车）？
- 哪些结论仍必须标 unknown（A 回收率、B 残余命中损失、化学真伪、
  真实结构复核）？

## 3. 期望回复格式

请按以下结构回复（可附证据行号/文件路径；不要输出结构正文）：

1. **总裁定**：可接受 / 需修正 / 不可接受；一句话理由。
2. **逐条结论**（Q1–Q8）：每条给 `sound` / `clarify` / `unsound` /
   `cannot_assess` + 依据（文件/行/字段）。
3. **必须修正项**：逐条列阻塞缺陷、最小修复范围、对应验收点；
   没有则写“0”。
4. **非阻断观察**：措辞/测试增强/文档澄清，不影响本轮放行。
5. **unknown/未核**：明确哪些结论不能从本轮材料得出。
6. **预注册条件**：是否具备进入 P1-B 预注册的条件；若否，缺什么。

## 4. 请求方已声明的 unknown（不要求评审方补证）

- A 的实际回收率：离线不能模拟“模型会不会改对”，只能新批测量。
- B 残余拒的离线命中损失：尚未用冻结 scorer 复算。
- 146 条 absent / 58 条 stereo 的化学真伪：未做真实结构复核。
- A 对 298 域 hit@1 的影响：unknown；预注册必须写“可能降分”。
- 真实 HPC 环境复跑：未做；本机 RDKit 2026.03.6 vs 批内登记
  2026.03.5 的差异未逐事件对照。
- 无效修订/预算耗尽路径的 rejected report 已补；其公共链消费与
  普通 rejected report 同形，但未做 298 题真实重跑。
- **多轮反馈的崩溃恢复**：修订 spec 只在进程内存；若在修订应用后、
  bundle 写出前崩溃，resume 从 action 冻结的原始 spec 重跑，既有反馈轮
  身份核验会 fail-closed（不静默提交错误事件）；bundle 写出后的崩溃由
  既有 B3 恢复消费修订事件。本实现不声称反馈路径的 B1–B4 全恢复已闭合；
  若预注册批要求，需后续单独设计修订 artifact 持久化。

## 5. 请求方声明

- 本轮未调用真实模型/付费批/HPC；未读金标/题面/参考图内容/私钥。
- 主树 src/tests 零改动；未合并、未 push；全部代码在独立 worktree。
- 本请求不要求评审方执行代码；若评审方自行执行，须在隔离副本、
  禁字节码/pytest 缓存，并记录实际 HEAD/命令/哈希。
- 评审意见与程序证据互证后才采信；最终放行/预注册/发车归 CC/Codex。