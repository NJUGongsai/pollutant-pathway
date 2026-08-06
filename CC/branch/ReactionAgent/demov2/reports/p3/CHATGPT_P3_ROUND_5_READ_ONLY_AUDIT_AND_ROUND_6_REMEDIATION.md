# ChatGPT P3 Round 5 只读审计与 Round 6 定向修复要求

- 审计日期：2026-08-04
- 审计模型：ChatGPT / Codex
- 审计类型：严格、只读、对抗性复核
- 审计对象分支：`codex/p3-strict-kernel`
- 审计对象工作区：`/Users/frank_gong/Documents/Codex/2026-08-03/ReactionAgent-p3-strict-kernel/CC/branch/ReactionAgent/demov2`
- 审计时报告的 HEAD：`4eb463368e38f2faa3d3656a05974c4b1c1211a6`
- 提交入口：`reports/p3/SUBMISSION_TO_CHATGPT_P3_ROUND_5.md`

## 1. 最终结论

```text
CHATGPT_P3_ROUND_5_READ_ONLY_AUDIT = FAIL
P3_IMPLEMENTATION_COMPLETE = NOT_ACCEPTED
P3_MACHINERY = FAIL_REMEDIATION_REQUIRED
P3_REAL_EVIDENCE = HONESTLY_BLOCKED
P4 = BLOCKED_PENDING_CHATGPT_P3_ROUND_6_AUDIT
```

Round 5 的常规测试、完整测试和当前 P3 Gate 输出可以复现，但关键安全合同仍存在三个 P0 级漏洞：

1. 真实 Gate 上下文中的 `BLOCKED` 可以被提交 JSON 提升成 `verified=True, PASS`。
2. mutation 的 raw output 与 typed artifact 彼此没有密码学或执行语义绑定，二者均可被分别替换并自重算哈希后继续通过验证。
3. 所谓 frozen P1 authority root 在默认 `TrainView`、默认 kernel 和默认 loader 路径中仍是可选项，而且可以由调用方提供或重建。

因此，不能以“官方 P3 Gate 当前诚实输出 BLOCKED”为理由接受 P3 machinery。官方 Gate 的当前输出是诚实的，但 Gate verifier 本身仍能产生假阳性的 verified PASS。

## 2. 审计边界与方法

本轮没有修改被审计 P3 源码，也没有 merge、push、checkout 或重写提交。

为避免污染原工作区，审计在隔离副本中执行：

```text
/private/tmp/p3-r5-audit.iiVvb7/ReactionAgent/demov2
```

隔离副本使用以下已存在虚拟环境：

```text
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/.venv/bin/python
```

审计包括：

- 检查 Round 5 submission、structured evidence、worklog、Gate、mutation 和 interface manifest 产物；
- 阅读 R5-A 至 R5-E 的实现和测试；
- 独立执行 Round 5 定向测试；
- 独立执行全部 P3 测试和全部项目测试；
- 独立执行 P0、P1、P3 Gate；
- 编写并运行不进入被审计源码的临时对抗性 probe；
- 不信任 submission 中的 stored status、stored count 或 stored hash，而以当前代码执行结果为准。

## 3. 可复现的正向结果

### 3.1 Round 5 定向测试

命令：

```bash
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/.venv/bin/python -m pytest -q \
  tests/p3/test_r5a_execution_authority.py \
  tests/p3/test_r5b_mutation_contract.py \
  tests/p3/test_r5c_frozen_authority.py \
  tests/p3/test_r5d_manifest_nested.py \
  tests/p3/test_r5e_report_counts.py
```

独立结果：

```text
75 passed in 31.27s
```

### 3.2 P3 全量测试

命令：

```bash
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/.venv/bin/python -m pytest -q tests/p3
```

独立结果：

```text
454 passed, 13 warnings in 46.22s
```

### 3.3 项目全量测试

命令：

```bash
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/.venv/bin/python -m pytest -q tests
```

独立结果：

```text
1360 passed, 13 warnings in 203.55s
```

### 3.4 P3 Gate

命令：

```bash
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/.venv/bin/python scripts/run_p3_gate.py
```

独立结果：

```text
P3 GATE VERDICT: BLOCKED (exit 2)
G01 = BLOCKED
G03 = BLOCKED
G07 = BLOCKED
其余 7 项 = PASS
mutations = 14/14 caught，14/14 valid
```

这部分“没有伪造真实 evidence PASS”的行为是正确的。但是，它不能抵消下文 verifier 可以被提升成假 PASS 的 P0 漏洞。

### 3.5 P1 Gate

独立结果：

```text
10/10 passed, exit 0
```

### 3.6 R5-D 与 R5-E

R5-D 的 nested unknown semantic field 覆盖已独立验证：

```text
base_hash     = 07ab8f71ba3d4e15026ba09d0d2d5f73260ead9e7eaa79ef84f55bac85f63aae
tampered_hash = 984902a7ea1258c631a6b2dad5326eb945fcc0b6fee913496f5b0da6b8c88a54
hash_changed  = true
```

R5-E 当前报告中的 Gate item 和 mutation 数量与实际 JSON 一致：

```text
Gate items: PASS=7, BLOCKED=3
mutations: total=14, caught=14, valid=14
```

结论：R5-D 已关闭；R5-E 的单一来源计数合同在本轮检查范围内已关闭。

## 4. Finding R6-A — Gate 可信执行上下文仍可被绕过

- 严重级别：P0
- 对应旧 finding：R5-A
- 状态：NOT CLOSED

### 4.1 根因

文件：

```text
reaction_agent/p3/gate.py
```

问题链如下：

1. `evaluate_gate_artifact(..., trusted_context=...)` 公开接受调用方传入的普通字典。
2. `set_trusted_execution_context(items)` 也是公开函数，任何调用者都能登记自己创建的 `GateItemResult`。
3. `has_trusted_context` 只判断 `ctx is not None`，所以空字典 `{}` 也被视为可信上下文。
4. verifier 只在 executed item 存在时检查 submitted evidence 的 artifact ID 是否出现在 executed evidence 中；executed item 缺失时没有 fail-closed。
5. verifier 没有比较 submitted item 与 executed item 的：
   - status；
   - evidence kind；
   - artifact type；
   - evidence content；
   - evidence content hash；
   - title；
   - 完整 item identity。
6. 最终 verdict 和 `item_statuses` 来自提交 JSON 解析出的 `items`，而不是 trusted context 中实际执行的 items。

关键实现位置：

```text
reaction_agent/p3/gate.py:174-188
reaction_agent/p3/gate.py:396-421
reaction_agent/p3/gate.py:581-621
```

### 4.2 独立攻击复现

攻击步骤：

1. 调用真实 `run_p3_gate()`，获得真实 execution context。
2. 保留每个真实 artifact ID 和全部 mutation 数据。
3. 仅把提交 JSON 中 G01/G03/G07 的 `status` 从 `BLOCKED` 改成 `PASS`，把 `evidence_kind` 改成 `real`。
4. 将未修改的真实 execution context 传给 `evaluate_gate_artifact`。

实际结果：

```json
{
  "probe": "submitted_status_elevation_with_actual_context",
  "verdict": "PASS",
  "verified": true,
  "machinery_failures": [],
  "item_statuses": {
    "G01": "PASS",
    "G02": "PASS",
    "G03": "PASS",
    "G04": "PASS",
    "G05": "PASS",
    "G06": "PASS",
    "G07": "PASS",
    "G08": "PASS",
    "G09": "PASS",
    "G10": "PASS"
  }
}
```

真实 execution context 中 G01/G03/G07 仍然是 `BLOCKED`。这已经直接证明“status 从真实执行对象推导”的提交声明不成立。

第二个复现：

```json
{
  "probe": "empty_public_context",
  "verdict": "BLOCKED",
  "verified": true,
  "machinery_failures": []
}
```

空字典不是 execution authority，却能使 `verified=True`。

第三个复现：将真实 evidence 的 artifact type 改成不匹配其 content 的另一个已知类型，保留 artifact ID：

```json
{
  "probe": "artifact_type_content_mismatch_with_actual_context",
  "verdict": "BLOCKED",
  "verified": true,
  "machinery_failures": []
}
```

这证明 `KNOWN_ARTIFACT_TYPES` 目前只是字符串 allowlist，并没有实现按 artifact type 分派的 typed content schema。

### 4.3 为什么现有测试没有发现

`tests/p3/test_r5a_execution_authority.py` 中的 fabricated artifact 把 `mutations` 设置为空数组，因此许多“伪造被拒绝”的测试会先因 `EMPTY_MUTATIONS` 失败；它们不能证明 execution authority 真正拒绝了伪造。

现有测试没有覆盖最关键攻击：

- 使用真实 execution context；
- 保留真实 artifact ID；
- 只提升 submitted status；
- 验证 verdict 是否仍由真实 executed status 决定。

### 4.4 Round 6 必须修复

必须冻结并实现一个明确的 trust model，建议采用以下合同：

1. offline serialized artifact 永远只能 `structurally_valid`，不能 `verified=True`。
2. 删除或封闭公共 `trusted_context` 注入和全局 setter；普通调用方不能创建 execution authority。
3. verified evaluation 必须由 runner 内部直接消费本次实际执行对象，或由不可由提交方伪造的受信 execution receipt/store 解析。
4. verdict 必须从 executed items 推导，绝不能从 submitted status 推导。
5. submitted report 若存在，必须与 executed result 做完整精确匹配；任何 item 缺失、额外、状态变化、evidence kind 变化、type/content/hash/namespace 变化都必须 FAIL。
6. 空 context、缺项 context、错 run context、重复/跨 run artifact ID 均必须 FAIL 且 `verified=False`。
7. 为每个 artifact type 定义实际的 strict typed content model；不能仅检查字符串属于 allowlist。

必须新增至少以下对抗测试：

```text
test_actual_context_blocked_status_cannot_be_elevated_to_pass
test_empty_context_is_not_execution_authority
test_missing_executed_item_fails_closed
test_executed_and_submitted_status_mismatch_fails
test_executed_and_submitted_evidence_kind_mismatch_fails
test_executed_and_submitted_content_rehash_mismatch_fails
test_artifact_type_specific_content_schema_mismatch_fails
test_public_caller_cannot_construct_verified_context
```

## 5. Finding R6-B — Mutation receipt 仍是自签名数据

- 严重级别：P0
- 对应旧 finding：R5-B
- 状态：NOT CLOSED

### 5.1 根因

`_verify_mutation_contract` 当前分别做了：

- 从 `run.raw_output` 重算 `stdout_stderr_hash`；
- 从 `run.artifact` 重算 `artifact_hash`；
- 检查 stored status 与 exit code；
- 检查 stored failure code 与另一个 stored field。

但是它没有：

1. 从 raw output 严格解析唯一的 typed payload；
2. 将解析出的 artifact 与 `run.artifact` 做精确一致性比较；
3. 将解析出的 artifact hash 与 `run.artifact_hash` 做交叉比较；
4. 将解析出的 status、failure code、case、variant 与 receipt 字段做交叉比较；
5. 证明记录的 command 真正执行过；
6. 要求 receipt 的 `run_id`、`component` 和 `schema_version` 非空。

实际 Gate 报告里的 mutation case receipt 中：

```text
run_id = ""
component = ""
schema_version = ""
```

验证器使用 `if run.run_id ...`、`if run.component ...`、`if run.schema_version ...` 的条件式检查，所以空值会绕过所谓 current-run/component/schema binding。

关键实现位置：

```text
reaction_agent/p3/gate.py:294-383
reaction_agent/p3/mutation_harness.py
```

### 5.2 独立攻击复现一：替换 typed artifact

攻击步骤：

1. 获取真实 Gate report 和真实 context。
2. 修改一个 mutation receipt 的 `run.artifact`。
3. 从修改后的 artifact 自行重算 `artifact_hash`。
4. 保持真实 raw output 不变。

实际结果：

```json
{
  "probe": "mutation_artifact_rewritten_and_rehashed",
  "verdict": "BLOCKED",
  "verified": true,
  "machinery_failures": []
}
```

### 5.3 独立攻击复现二：替换 raw output

攻击步骤：

1. 修改一个真实 mutation receipt 的 `raw_output`。
2. 自行重算 `stdout_stderr_hash`。
3. 保持 typed artifact、status、failure code 等字段不变。

实际结果：

```json
{
  "probe": "mutation_stdout_rewritten_and_rehashed",
  "verdict": "BLOCKED",
  "verified": true,
  "machinery_failures": []
}
```

这两个结果证明 raw output hash 和 artifact hash 都只是提交方可重算的 self-hash，而不是 execution proof。

### 5.4 为什么现有测试没有发现

`test_attack_raw_output_and_hash_updated_but_receipt_not_current_run` 只在 raw output 尾部追加文本并重算 hash，但没有真正改变 receipt 的 run identity。它不能证明 receipt 属于 current run。

现有正向测试只分别重算两个 hash，没有验证 raw output 与 typed artifact 之间的内容绑定。

### 5.5 Round 6 必须修复

1. mutation subprocess 必须输出一个唯一、严格、版本化的 JSON receipt；不得从混合 stdout/stderr 中任意挑选自报 payload。
2. runner 必须解析该 receipt，并从解析结果构建内存中的 typed receipt；提交 artifact 不得重复提供另一份可独立修改的数据。
3. 必须把以下字段绑定到同一次受信执行：
   - execution/session nonce；
   - run_id；
   - mutation_id；
   - case；
   - variant；
   - component；
   - schema version；
   - command identity；
   - exit code；
   - status；
   - failure code；
   - typed artifact；
   - canonical artifact hash。
4. `run_id`、`component`、`schema_version`、case 和 variant 必须是 required non-empty fields，不能用条件式“非空才比较”。
5. verifier 必须从受信执行 receipt 推导 mutation outcome，不得从 submission 的 stored fields 推导。
6. 如果选择签名 receipt，密钥/能力必须不由 submission 持有；如果选择 in-process authority，必须与 R6-A 共用同一个不可公开注入的执行上下文。

必须新增至少以下测试：

```text
test_rewrite_typed_artifact_and_rehash_is_rejected
test_rewrite_raw_output_and_rehash_is_rejected
test_empty_receipt_run_id_is_rejected
test_empty_receipt_component_is_rejected
test_empty_receipt_schema_version_is_rejected
test_raw_payload_artifact_must_equal_typed_receipt_artifact
test_raw_payload_status_and_failure_code_must_equal_receipt
test_receipt_from_previous_execution_nonce_is_rejected
```

## 6. Finding R6-C — Frozen P1 authority 未成为唯一生产 authority

- 严重级别：P0
- 对应旧 finding：R5-C
- 状态：NOT CLOSED

### 6.1 根因

当前实现：

- `TrainView.authority_manifest` 默认是 `None`；
- `build_train_view()` 不附加 authority manifest；
- `run_kernel()` 的默认路径调用 `build_train_view(load_fixture_reactions())`，得到无 frozen authority 的 train view；
- kernel 调用 `load_reaction_evidence()` 时不传 authority manifest；
- `load_reaction_evidence(..., authority_manifest=None)` 允许无 manifest 工作；
- public `build_fixture_authority_manifest(fixtures)` 可以从调用方当前提供的内容重建 manifest；
- frozen validator 对 manifest 中缺少 reaction ID 的情况使用 `continue`，没有 exact-set fail-closed；
- manifest 的 snapshot identity 没有在生产路径中形成不可替代的上游 binding。

关键实现位置：

```text
reaction_agent/p3/fixtures.py:286-381
reaction_agent/p3/fixtures.py:533-598
reaction_agent/p3/fixtures.py:637-694
reaction_agent/p3/load.py:76-102
reaction_agent/p3/kernel.py:243-245
reaction_agent/p3/kernel.py:324-334
```

独立 probe：

```json
{
  "probe": "default_train_view_authority",
  "authority_manifest_is_none": true,
  "reaction_count": 5
}
```

所以 Round 5 修复只证明“测试显式保留一个旧 root 时可以拒绝变化”，没有证明生产/default kernel 只能接受 P1/P2 frozen authority。

### 6.2 测试与声明不一致

`tests/p3/test_r5c_frozen_authority.py::_fully_stripped_hydrolysis()` 的 docstring 声称同步剥离：

```text
participants, evidence, ledger, mapping, lineages, raw/normalized reaction
```

但函数实际只更新了：

```text
fixture.participants
fixture.evidence.participants
```

它没有同步更新 ledger、mapping、lineages、reactant/product SMILES、raw reaction 和 normalized reaction。因此该测试没有复现其标题描述的“全部表示同步剥离”。

`test_retrieval_stripping_does_not_change_reaction_authority()` 中的核心断言：

```python
full_hash == canonical_reaction_hash(fx)
```

只是同一对象与自身比较，没有运行真实 retrieval cofactor stripping pipeline，也没有证明 retrieval identity 与 complete reaction authority 的隔离。

### 6.3 Round 6 必须修复

1. 生产 `TrainView` 必须要求不可缺失的 upstream authority handle；fixture authority 必须使用独立类型和明确的 `synthetic_fixture` 语义。
2. production kernel 缺少 P1/P2 frozen snapshot authority 时必须立即 BLOCKED/FAIL-CLOSED，不能继续 donor/reaction processing。
3. production loader 不能接受调用者通过 `build_fixture_authority_manifest(current_content)` 创建的新 root 作为 P1 authority。
4. authority manifest 必须来源于冻结的 P1/P2 snapshot/lineage/ledger/eligibility data authority，并具有可验证 provenance。
5. manifest reaction ID 集合与 TrainView 可用 reaction refs 必须 exact match；缺少 expected reaction hash 不得 `continue`。
6. snapshot_id、snapshot_hash、fold_id、reaction hashes 和 authority version 必须交叉绑定。
7. 真正实现完整同步 A/B-only mutation：participants、evidence、ledger、mapping、lineages、raw/normalized reaction、fixture reaction strings 和本地 hashes 全部同步重建；旧的 upstream frozen root 必须保持不变，production loader 必须拒绝。
8. retrieval 测试必须调用真实 donor identity/cofactor stripping 路径，并证明 complete reaction object 和 authority hash 在 retrieval 前后完全不变。

必须新增至少以下测试：

```text
test_production_train_view_requires_upstream_authority
test_default_kernel_blocks_without_upstream_authority
test_caller_built_fixture_manifest_is_not_production_authority
test_manifest_missing_reaction_id_fails_closed
test_manifest_extra_reaction_id_fails_closed
test_snapshot_identity_and_reaction_hashes_are_cross_bound
test_fully_synchronized_all_representations_ab_strip_rejected
test_real_retrieval_stripping_does_not_mutate_complete_reaction_authority
```

## 7. Finding R6-D — P0 Gate 10/10 未能独立复现

- 严重级别：P1 / integration blocker
- 状态：NOT REPRODUCED

独立执行：

```bash
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/.venv/bin/python scripts/run_p0_gate.py
```

实际结果：

```text
exit 1
subprocess.TimeoutExpired
full pytest command timed out after 180 seconds
```

同一隔离副本中的完整测试实际需要：

```text
203.55 seconds
```

因此 submission 中的“P0 Gate 10/10”不能在当前完整代码和当前隔离环境复现。P1 Gate 仍返回 10/10，说明它没有替代本轮要求的独立 P0 Gate 重跑。

Round 6 必须：

1. 明确 P0 Gate 应只跑冻结 P0 contract subset，还是要跑全阶段测试；不能让不断增长的全量 tests 隐式突破固定 180 秒。
2. 如果 P0 Gate 设计上必须跑全量 tests，timeout 必须是显式、版本化、可解释的配置，并在报告中记录真实时长和 timeout。
3. 不得读取旧报告后声称当前 P0 Gate PASS。
4. Round 6 最终必须在干净隔离副本中重新运行并得到真实 exit 0。

## 8. Finding R6-E — 审计目标没有被 Git 提交冻结

- 严重级别：P1 / reproducibility
- 状态：OPEN

审计时 `git status` 显示整个 `reaction_agent/p3/`、`tests/p3/`、`reports/p3/` 和 P3 scripts 为 untracked；报告所称 HEAD `4eb4633...` 并不包含这些 P3 文件。

因此 HEAD 不能唯一标识本轮被审计实现。changed-files manifest 可以辅助，但不能替代冻结的提交边界。

Round 6 在完成修复和自检后必须：

1. 只提交本阶段合法范围内的文件；
2. 保留已有 P0/P1 用户修改，不得 reset、checkout 或覆盖；
3. 创建本地 commit，不 push、不 merge；
4. submission 写明准确 commit SHA、parent SHA、branch、clean/dirty 状态；
5. 若仍有继承的非 P3 dirty 文件，必须列出并证明它们不属于 Round 6 修改；
6. changed-files manifest 必须从最终 commit/tree 生成，而不是从未冻结工作区手填。

## 9. Round 5 五项 finding 的裁决

| Round 5 finding | Round 5 声明 | ChatGPT 独立裁决 | 说明 |
|---|---|---|---|
| R5-A Gate execution authority | FIXED | NOT CLOSED | 真实 BLOCKED context 可被 submitted status 提升成 verified PASS；空 context 也 verified |
| R5-B mutation full contract | FIXED | NOT CLOSED | raw output 与 typed artifact 可分别替换并自重算 hash；execution identity 字段为空仍通过 |
| R5-C frozen P1 authority | FIXED | NOT CLOSED | authority optional、caller-provided、默认 kernel 不使用；测试未做完整同步剥离 |
| R5-D nested manifest hash | FIXED | CLOSED | nested unknown semantic field 独立 probe 会改变 hash |
| R5-E report single source | FIXED | CLOSED WITHIN CHECKED SCOPE | 当前 Gate item/mutation/test counts 可复算且一致 |

## 10. Round 6 执行边界

### 10.1 允许

- 只修复本文件列出的 R6-A 至 R6-E；
- 新增真实对抗测试；
- 在独立 worktree 内运行测试和 Gate；
- 更新 P3 Round 6 报告、structured evidence、worklog、Gate report 和 changed-files manifest；
- 完成后创建本地 commit。

### 10.2 禁止

- 修改 P0/P1 frozen contracts、final design、final plan 或 ADR 来迎合当前实现；
- fixture 冒充 real evidence；
- 把 P3 official Gate 的 BLOCKED 改写成 PASS；
- 用 stored status、stored counts、stored hashes 或旧报告作为当前执行证明；
- 只让现有测试变绿而不加入本审计给出的实际攻击复现；
- 公开暴露可由 submission 构造的“trusted context”；
- 用 self-hash 冒充 execution proof；
- 未经用户授权安装依赖、联网、push 或 merge；
- 删除或覆盖已有用户工作；
- 提前启动 P4 集成。

## 11. Round 6 必须提交的交付物

全部放在：

```text
/Users/frank_gong/Documents/Codex/2026-08-03/ReactionAgent-p3-strict-kernel/CC/branch/ReactionAgent/demov2/reports/p3/
```

必须至少包含：

```text
SUBMISSION_TO_CHATGPT_P3_ROUND_6.md
P3_ROUND_6_AUDIT_EVIDENCE.json
P3_ROUND_6_REMEDIATION_WORKLOG.md
P3_GATE_REPORT_ROUND_6.json
P3_GATE_REPORT_ROUND_6.md
P3_MUTATION_RESULTS_ROUND_6.json
p3_p4_interface_manifest_round_6.json
P3_ROUND_6_CHANGED_FILES.json
P3_ROUND_6_STARTING_WORKTREE_STATE.md
P3_ROUND_6_FINAL_WORKTREE_STATE.md
```

Submission 必须逐项回答 R6-A 至 R6-E，并为每项提供：

- 原始失败攻击；
- RED 命令、exit code、真实输出摘要和输出 hash；
- 修复后的 GREEN 命令、exit code、真实输出摘要和输出 hash；
- 代码位置；
- 测试位置；
- 不变量；
- residual risk；
- changed files；
- 是否使用 fixture、real evidence 或 diagnostic evidence；
- 不得用占位符 hash 或手写假时间戳。

## 12. Round 6 最低验收矩阵

以下必须全部真实执行：

1. R6-A 新增对抗测试全部通过；
2. R6-B 新增对抗测试全部通过；
3. R6-C 新增对抗测试全部通过；
4. R5-D/R5-E 回归测试全部通过；
5. `tests/p3` 全部通过；
6. `tests` 全部通过；
7. P0 Gate 真实 exit 0；
8. P1 Gate 真实 exit 0；
9. P3 Gate 若真实资源仍缺失，必须保持 `BLOCKED`, exit 2；
10. 所有 machinery item 必须无 FAIL；
11. mutation registry exact match；
12. 所有 mutation baseline/mutated receipts 均由受信执行上下文绑定；
13. 不得声称 real performance；
14. P4 继续 BLOCKED；
15. 最终本地 commit 唯一标识本次审计对象。

## 13. 下一轮最终状态字符串

在完成全部修复、自检和本地提交后，Round 6 submission 最后一行必须是：

```text
P3_ROUND_6_READY_FOR_CHATGPT_READ_ONLY_AUDIT_P4_BLOCKED
```

在 ChatGPT Round 6 审计明确通过之前，不得写：

```text
P3_PASS
P3_GATE_PASS
P3_ACCEPTED
P4_UNBLOCKED
```

## 14. 本轮审计最终裁决

Round 5 的测试数量和诚实 BLOCKED Gate 值得保留，但“测试绿”没有覆盖真正的信任边界。三个 P0 finding 都能用当前代码直接复现，且其中 R6-A 可以把真实 BLOCKED 执行提升成 `verified=True, PASS`，这是阶段验收的决定性否决项。

```text
FINAL_DECISION = ROUND_5_REJECTED
NEXT_ACTION = COMPLETE_R6_A_THROUGH_R6_E_AND_RESUBMIT
P4_STATUS = BLOCKED
```
