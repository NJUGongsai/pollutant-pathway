# ChatGPT P4 Round 1 Read-Only Audit and Remediation

审计日期：2026-08-04  
审计类型：P4 既有实现只读代码审阅、独立行为复现、Gate/报告一致性核验  
审计结论：**FAIL — NEEDS REMEDIATION**  
P5 状态：**BLOCKED pending P4 remediation and ChatGPT re-audit**

## 1. 审计对象

P4 工作树：

```text
/Volumes/CC/Enzyme_Agent/depending/.claude/worktrees/p4-strict-kernel/CC/branch/ReactionAgent/demov2
```

Git/工作树状态：

```text
branch: worktree-p4-strict-kernel
HEAD: 4eb463368e38f2faa3d3656a05974c4b1c1211a6
P4 files: all untracked
tracked files modified: 0
```

这是一版建立在 P1 旧基线上的早期 P4 实现。它当时还没有当前已冻结的 P3 Round 8 interface manifest。现有 P4 文件未 commit，因此本报告使用绝对路径、文件内容和独立复现结果定义审计对象，不把 `4eb4633` 误称为 P4 实现提交。

本次未修改被审计 P4 worktree 的任何文件，未联网、未安装依赖、未调用 LLM/MCP/Orchestra、未 commit/push/merge。独立复现脚本只写在：

```text
/private/tmp/p4_audit_probes.py
```

## 2. 与目标的一致性结论

这版 P4 的方向与最终设计一致：模块划分覆盖 evidence identity、support、counterevidence、strict ranking、applicability、abstention、PredictionResult adapter、run manifest、Gate 和 mutation；缺少真实 P3/evidence 时也没有声称 production Gate PASS。

但是，它目前主要证明了“synthetic happy-path fixture 可以运行”，尚未证明“P4 只能消费真实、冻结、同 namespace 的 P3/P1 authority，并可靠地拒绝错误组合”。独立复核发现多个跨模块不变量没有实现，因此当前 `machinery 11/11 PASS` 结论不成立。

最终状态必须改为：

```text
P4_ROUND_1_AUDIT_FAIL_NEEDS_REMEDIATION
P4_GATE_PASS_NOT_AUTHORIZED
P5_BLOCKED_PENDING_P4_REAUDIT
```

## 3. 已独立验证通过的部分

### 3.1 P4 自有测试

独立执行：

```bash
PYTHONDONTWRITEBYTECODE=1 \
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/.venv/bin/python \
  -m pytest -q -p no:cacheprovider tests/p4
```

结果：

```text
64 passed in 1.53s
```

### 3.2 P0 contract regression

独立执行：

```bash
PYTHONDONTWRITEBYTECODE=1 \
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/.venv/bin/python \
  -m pytest -q -p no:cacheprovider tests/contracts
```

结果：

```text
290 passed in 0.48s
```

这些结果说明已有单元测试全部通过、P0 schema contracts 未被 P4 新文件直接破坏；但下面的独立反例表明测试覆盖不足，不能据此接受 P4。

## 4. Blocking findings

### P4-R1-A — 当前冻结 P3 manifest 无法被 P4 consumer 读取（P0）

位置：

```text
reaction_agent/adapters/p3_consumer.py:57-90
```

P4 consumer 预期以下顶层字段：

```text
classification
components
fields
hash_algo
blocker_semantics: dict
```

当前冻结的 P3 manifest 位于：

```text
/Users/frank_gong/Documents/Codex/2026-08-03/ReactionAgent-p3-strict-kernel/CC/branch/ReactionAgent/demov2/reports/p3/p3_p4_interface_manifest.json
```

它实际使用：

```text
manifest_version
producer
consumer
hash_algorithm
interfaces
blocker_semantics: string
evidence_kind_semantics
```

独立实测：

```text
P3InterfaceConsumer(actual_manifest).load()
→ ValueError: dictionary update sequence element #0 has length 1; 2 is required
```

这不是“缺少真实 P3 数据”这么简单，而是接口 schema 已经不兼容。P4 目前也只读取 interface specification，没有读取并验证 current-run `KernelRunManifest + StrictCandidate[] + CandidateTrace + CapabilityStatus` artifact，因此即使文件存在，也不能证明 P4 获得了可排名候选。

必须修复：

1. 以当前 `manifest_version=p3-p4-1` 为冻结合同，写 strict typed parser；
2. 精确支持 `interfaces`、`hash_algorithm` 和 string `blocker_semantics`，未知/缺失/错误类型 fail-closed；
3. interface manifest 只证明 schema，不得自动令 `capability_available=True`；
4. 必须另行接收并验证 current-run P3 artifact，其中包含 manifest、candidates、trace、capability、hash 和 namespace；
5. 只有 artifact schema、hash、evidence kind、run/query/case/fold/snapshot 全部匹配时，才能提供 candidates；
6. 当前只有 interface specification、没有 current-run artifact 时，返回 typed BLOCKED，不抛裸异常，也不生成候选。

### P4-R1-B — Capability/classification 可以自相矛盾并把 synthetic 重标为 real（P0）

位置：

```text
reaction_agent/schemas/p4/decision.py:55-67
reaction_agent/schemas/p4/run.py:32-48
reaction_agent/inference/predictor.py:99-146
```

`P4CapabilityStatus.classification` 和 manifest classification 是自由字符串，没有 enum/cross-field validator。pipeline 只检查 `capability_available`，然后完全信任调用方提供的 classification。

独立实测使用以下矛盾状态：

```text
capability_available=True
p3_interface_manifest_present=False
real_evidence_available=False
classification="real"
```

配合 synthetic fixture，结果仍为：

```text
status=completed
decision=predicted
outcome.classification=real
manifest.classification=real
```

这直接破坏 fixture/real evidence 隔离。

必须修复：

1. classification 改为冻结 enum：`real|synthetic_fixture|blocked|diagnostic`；
2. 加 cross-field invariants；至少要求 `real` 同时满足 verified P3 current-run artifact、real evidence、正确 namespace 和所需上游 authority；
3. `p3_interface_manifest_present=False` 或 `real_evidence_available=False` 时不得构造 `classification=real`；
4. pipeline 不得接收任意调用方自报 capability 作为 authority；必须由 verified adapter result 构造不可伪装的 typed handle；
5. synthetic fixture authority 与 production authority 使用不同类型，不能仅靠字符串区分。

### P4-R1-C — PredictionResult adapter 会在没有 P3 Candidate 时创建未验证 candidate（P0）

位置：

```text
reaction_agent/adapters/prediction_result_adapter.py:145-177
```

当 `candidate_map` 中没有 ranked candidate 时，adapter 使用 `RankedStrictCandidate.canonical_product` 新建一个 shared `Candidate`，并给出：

```text
origin="agent_selected_from_evidence_space"
validation={}
```

独立实测在 `candidate_map={}` 时仍得到：

```text
status=completed
candidate_ids=[invented_by_rank_record]
canonical_product=CC=O
validation={}
```

这违反：P4 不创建/修改化学结构；completed 必须来自已验证的 P3 strict candidate；versioned policy 是 validation 唯一权威。

必须修复：

1. 删除 fallback candidate construction；
2. completed/predicted 时，ranked candidate 必须在 verified P3 candidate map 中精确存在；
3. 精确核对 candidate ID、canonical product identity、lane、validation、generation path、ledger、evidence kind 和 namespace；
4. 任一缺失或不一致都必须 typed FAIL/BLOCKED，不能用 ranking record 补造 Candidate；
5. 添加“rank record 存在但 P3 candidate 缺失/不同 product/validation 空/namespace 不同”的 RED→GREEN tests。

### P4-R1-D — Cross-case/fold/snapshot/policy 隔离未实现（P0）

位置：

```text
reaction_agent/inference/predictor.py:99-180
reaction_agent/adapters/p3_consumer.py:92-104
```

prompt 要求 cross-case/fold/snapshot/policy rejection，但 pipeline 没有验证 query、evidence、candidate、trace、capability 是否属于同一 namespace；`wrap_p4_output()` 只是把调用方给的 IDs 附加到 dict，并未验证来源。

独立实测：query 使用 `snap_other_namespace` 和 `wrong-policy-version`，evidence 仍属于 `snap_c589494081df`，pipeline 仍返回：

```text
decision=predicted
status=completed
```

并静默使用内部 `p4-policy-1`，没有拒绝 query 声明的错误 policy。

必须修复：

1. 定义唯一 `RunNamespace`/authority handle，至少绑定 run/query/case/fold/snapshot ID/hash、policy/config/component versions；
2. evidence、candidate、trace、P3 manifest 与 P4 request 必须 exact-match；
3. test/calibration/train view 必须使用 typed fold/view authority，不得靠 evidence ID 前缀判断；
4. query 指定 policy 与实际 policy 不匹配时 fail-closed；
5. 添加 cross-case、cross-fold、cross-snapshot、snapshot-hash、policy-version、test-label contamination 的独立 mutation tests。

### P4-R1-E — 正常 completed pipeline 的 result hash 无法自验证，冻结对象仍可直接修改（P0）

位置：

```text
reaction_agent/inference/predictor.py:272-300
reaction_agent/runtime/manifest.py:21-117
reaction_agent/runtime/run.py:30-117
```

predictor 先用一套自定义 request-hash preimage 计算 `result_hash`：

```text
query + snapshot_id + policy_version
```

随后 `build_run_manifest()` 用另一套 preimage 生成并保存 `request_hash`：

```text
query + snapshot_id + snapshot_hash + all versions
```

因此正常 completed fixture run 立即验证失败：

```text
stored result hash: 3c1632e61d26488a...
recomputed hash:    6acf32f390e965ea...
RunHashMismatchError
```

此外，`RuntimeRun.manifest` 直接返回可变 Pydantic 对象。即使 store 已 freeze，调用方仍可执行：

```text
frozen.manifest.result_hash = "directly_mutated_after_freeze"
```

独立实测修改成功，并立即改变 store 内保存的值。

必须修复：

1. 删除 predictor 中重复的 request hash 算法，只允许 `compute_request_hash()` 一个来源；
2. 构建 manifest 时由 manifest builder 唯一计算 result hash，创建后立即 `verify()`；
3. result hash 必须覆盖最终 decision、完整 ranking/applicability、support/counterevidence hashes、trace、namespace、versions 和 classification；
4. run ID 不能只由 query 生成；必须绑定冻结 namespace/evidence/versions，或采用不会覆盖的唯一 run identity；
5. runtime 内部保存 immutable canonical snapshot/deep copy；公共 getter 返回只读模型或副本；
6. freeze 前验证 hash；freeze 后任何直接/嵌套修改都必须失败或不影响内部状态；
7. child ID 已存在时拒绝覆盖，child 必须重新计算并验证 hash；
8. 添加“真实 pipeline output 立即 verify”“直接字段修改”“nested list/dict 修改”“同 query 不同 snapshot/evidence/version”“child collision”测试。

### P4-R1-F — Gate 与 mutation runner 存在可复现的误判（P0）

位置：

```text
scripts/run_p4_gate.py:546-584
scripts/run_p4_gate.py:591-640
scripts/run_p4_gate.py:698-742
scripts/run_p4_mutations.py:69-115
scripts/run_p4_mutations.py:165-166
reports/p4/P4_MUTATION_RESULTS.json
```

#### F1. pytest 失败仍可令 G11 PASS

G11 保存了 subprocess `returncode`，但没有检查它；固定的 `/tmp/.pytest_p4_gate_report.json` 在运行前也没有删除或 freshness binding。

独立实测预置一个旧的成功 JSON，同时令 pytest return code 为 7，结果：

```text
passed=true
evidence="P4 test suite passes zero-skip"
details.pytest_exit=7
```

#### F2. M04 执行异常被计为 caught mutation

M04 patch 后的 `_add_test_evidence()` 调用已经被 patch 的自身，触发 recursion。`check_g03_support()` 把异常吞成普通 `passed=False`，mutation runner 随后把它计为目标 `PASS→FAIL`。

当前报告和独立复现均显示：

```text
mutation_id=M04
caught=true
error=false
evidence="G03 error: maximum recursion depth exceeded"
```

这违反“no-op/error/escaped 不能计为 caught”。因此当前 `14/14 CAUGHT` 不可信。

#### F3. 上游 authority 检查过浅

- G12 只看 manifest 是否 present，没有验证 schema/current-run artifact/hash；
- G13 只看 `classification == real`；
- G14 只看存储 JSON 中 `status == READY_FOR_CHATGPT_P2_AUDIT`；
- report 中 `p4_authority` 又被硬编码为 P2 blocked/P3 absent/synthetic，与动态检查可能不一致；
- report 决策只统计 machinery fail；若未来 real-input check 返回 `passed=false, blocked=false`，可能没有被计入 fail。

必须修复：

1. G11 在执行前删除/隔离旧 report，使用本次唯一 temp path，检查 subprocess exit code、report 创建时间/nonce、collected/passed 总数；
2. Gate check 的执行异常必须返回 typed `ERROR`，不能与目标 invariant `FAIL` 混为一类；
3. mutation 必须声明 expected failure code；只有 baseline PASS、mutated 正常执行、expected code 精确出现时才 caught；
4. 修复 M04 使用 patch 前保存的原函数，并证明 `test:` evidence 导致特定 isolation failure，而不是 recursion；
5. G12/G13 使用 P4-R1-A/B 的 verified P3/production authority；
6. G14 不得信任存储 status 字符串；在 P2 formal authority 尚未被 ChatGPT 接受时保持 BLOCKED；未来必须验证 current-run P2 artifact/hash/receipt；
7. 任一非 PASS 且非合法 BLOCKED 的 Gate item都必须令整体 FAIL；
8. report authority 字段必须从当前 run artifacts 派生，不得硬编码；
9. Gate/Mutation 报告增加 run ID、session nonce、command/cwd/python、start/end、exit code、stdout hash、artifact hash、expected/observed failure code。

## 5. Major findings

### P4-R1-G — Evidence/support/applicability/counterevidence 没有真实逐特征绑定（P1）

位置：

```text
reaction_agent/inference/features.py:42-96
reaction_agent/inference/support.py:58-123
reaction_agent/inference/applicability.py:28-76
reaction_agent/inference/counterevidence.py:88-160
```

问题：

1. `structural_context` 是任意调用方 dict，ordinal scalar 没有 P3 artifact/hash/evidence binding；
2. support 将**全部 evidence IDs**赋给每一个 observable feature，并不能证明某条 evidence 真正产生该 feature；
3. applicability 只要 caller 给 `donor_similarity=3`，即使 `evidence_records=[]`，仍返回 `in_domain + IN_DOMAIN_DONOR + evidence_ids=[]`；
4. 非 competing-transform counterevidence 在没有任何 evidence 时会生成 `unresolved:<target>` 伪 evidence ID，并使用 `source_identity=unknown`；
5. evidence identity resolver 接受任意 dict，缺少完整 schema/namespace validation；缺失关键 source record 字段可能造成错误去重。

独立复现：

```text
in_domain_without_evidence:
  label=in_domain
  evidence_ids=[]
  reason_codes=[IN_DOMAIN_DONOR]

counterevidence_without_source_evidence:
  type=FAILED_TRANSFORM_PRECONDITIONS
  evidence_ids=[unresolved:missing_transform]
  source_identity=unknown
```

必须修复：

1. 用 typed `FeatureObservation` 替代 raw dict；每项包含 feature key、ordinal、真实 evidence IDs、source stage/artifact/hash、namespace；
2. 每个 feature 只绑定真正支持它的 evidence，禁止复制全部 evidence IDs；
3. applicability 的非 unknown label 必须拥有可验证 structural observation 和非空 evidence/path IDs；否则只能 unknown/BLOCKED；
4. counterevidence 不得制造 `unresolved:*` evidence ID；缺证据时不生成 record，或产生独立 typed unknown/blocked reason；
5. evidence IDs 必须存在于 verified resolution 且 namespace 一致；unknown ID 拒绝；
6. 添加 orphan evidence ID、empty evidence + high scalar、all-evidence indiscriminate binding、fake unresolved ID、missing source identity 的 RED→GREEN tests。

### P4-R1-H — 一个弱/冲突候选会错误地让整个候选集 abstain（P1）

位置：

```text
reaction_agent/inference/predictor.py:199-243
```

当前逻辑：

```text
insufficient_support = any(candidate.support_tier == none)
evidence_conflict = any(candidate.has_conflict)
```

因此只要一个候选弱或冲突，即使另一个 candidate 有 strong support，整个结果也会 0 candidate abstention。

独立实测：

```text
candidate A support=strong
candidate B support=none
result=abstained
reason=INSUFFICIENT_SUPPORT
ranked_candidate_count=0
```

必须修复：

1. 先进行 per-candidate eligibility/applicability/support/conflict adjudication；
2. 弱、out-of-domain、invalid 或 candidate-local conflict 应移出 production ranking，并保留 trace；
3. 只要至少一个 verified strict candidate 通过 policy，就对合格子集排名并 completed；
4. 只有合格候选集为空时才进行全局 typed abstention；
5. global evidence conflict 与 candidate-local conflict 必须分型；
6. 添加 strong+weak、good+conflicted、two-good、all-weak、all-conflicted、candidate-order permutation tests。

## 6. Medium findings / incomplete prompt coverage

### P4-R1-I — Ranker 与声明语义不完全一致（P2）

位置：

```text
reaction_agent/inference/ranker.py:25-69
reaction_agent/policies/p4_decision_policy.py:84-97
```

注释称 score 是“over observable features”的 weighted average，但 denominator 使用全部冻结 feature 权重；unobservable feature 实际相当于 0 分并压低总分。必须明确选择一种冻结语义：

- 若缺失即 0，则更新 policy/docs/tests；
- 若只在 observable features 上平均，则按 observable weights 重新归一化。

此外原 prompt 要求 ablation outputs，目前只有 contribution 列表，没有明确 ablation result/trace。

### P4-R1-J — Gate 缺少 selective metrics 和真正的 train-only isolation 证明（P2）

Gate prompt 要求 selective metrics computable、train-only/test-label isolation。当前 G03 只拒绝以 `test:` 开头的 evidence ID；没有基于 fold/view authority 验证，也没有 selective metric artifact。P2 truth authority 仍 BLOCKED 时可以诚实保持相关项 BLOCKED，但不能用字符串前缀测试声称 isolation 已证明。

## 7. 必须新增的 RED→GREEN tests

至少新增以下独立测试组，不得只扩展 happy-path fixture：

### A. P3 interface/current-run authority

1. 当前真实 `p3_p4_interface_manifest.json` 可解析；
2. manifest schema 正确但 current-run candidate artifact 缺失 → BLOCKED；
3. blocker_semantics string/dict 类型严格按冻结合同；
4. malformed/unknown manifest → typed BLOCKED/FAIL，不抛裸异常；
5. wrong manifest version/hash/interface fields → reject；
6. current-run candidate/trace/capability hash 不匹配 → reject。

### B. Real/fixture authority

1. synthetic authority 不能 relabel real；
2. `classification=real` + no P3/no real evidence → schema reject；
3. blocked authority 不能执行 completed pipeline；
4. caller 手写 capability 不能成为 production authority。

### C. Candidate provenance

1. ranked ID 不在 P3 candidate map → reject；
2. canonical product identity 不同 → reject；
3. empty/failed validation → reject；
4. non-strict/evidence_kind mismatch → reject；
5. P4 不得构造 fallback Candidate。

### D. Namespace/leakage

1. cross query/case/fold/snapshot ID/hash；
2. wrong policy/config/component version；
3. train runtime 输入 test/calibration evidence；
4. unknown evidence ID / cross-run trace；
5. same ID but changed nested content/hash。

### E. Evidence grounding

1. `donor_similarity=3` + no evidence → unknown/reject；
2. feature evidence IDs 必须是该 feature 的真实子集；
3. counterevidence empty source → no record/reject；
4. `unresolved:*` pseudo evidence ID forbidden；
5. duplicate/mirror/publication transitive cases和输入顺序不变性。

### F. Decision aggregation

1. strong + weak → completed with strong only；
2. good + conflicted → completed with good only（除非 typed global conflict）；
3. all weak → INSUFFICIENT_SUPPORT；
4. all out-of-domain → OUT_OF_DOMAIN；
5. candidate input permutation 不改变结果/hash。

### G. Hash/freeze/replay

1. normal completed pipeline immediately verifies；
2. direct manifest assignment blocked/non-leaking；
3. nested trace/evidence list/dict mutation blocked/non-leaking；
4. result/support/counter/applicability change affects result hash；
5. same query but different snapshot/evidence/version does not collide；
6. child collision rejected；parent unchanged；child verifies。

### H. Gate/mutation false-positive prevention

1. pytest exit nonzero + stale success JSON → G11 FAIL；
2. report absent/truncated/wrong nonce → FAIL；
3. mutation execution exception → ERROR，不 caught；
4. wrong failure code → not caught；
5. M04 真实 test-evidence isolation mutation → expected typed failure；
6. stored P2/P3 status string不能满足 authority Gate；
7. real-input item `false, non-blocked` → overall Gate FAIL。

## 8. 修复执行顺序

必须按以下顺序，避免继续围绕错误接口写测试：

1. **冻结 P3→P4 current interface proposal**：对齐当前 P3 manifest，明确 interface spec 与 current-run artifact 的区别；
2. **实现 typed authority 与 namespace**：production/fixture 分型、cross-field invariants、current-run binding；
3. **删除 candidate fallback**：P4 只消费 verified P3 Candidate；
4. **修复 hash/immutable run**：单一 hash preimage、深度不可变、pipeline verify；
5. **修复 evidence grounding**：per-feature evidence observations、applicability/counterevidence fail-closed；
6. **修复 per-candidate decision aggregation**；
7. **加固 Gate/mutation runner**；
8. **补充全部 RED→GREEN 对抗测试**；
9. **重新生成 reports/p4 全套交付物**；
10. **提交 ChatGPT Round 2 只读审核**。

不得通过修改 P0/P1/P2/P3 冻结合同来迁就 P4。若 P3 current-run artifact 合同仍未冻结，只能提交 interface proposal，并保持真实 P4 Gate BLOCKED。

## 9. Round 2 必须交付

在 P4 worktree 的 `reports/p4/` 生成：

```text
SUBMISSION_TO_CHATGPT_P4_ROUND_2.md
P4_ROUND_2_AUDIT_EVIDENCE.json
P4_ROUND_2_REMEDIATION_WORKLOG.md
P4_GATE_REPORT_ROUND_2.md
P4_GATE_REPORT_ROUND_2.json
P4_MUTATION_RESULTS_ROUND_2.json
p4_p5_interface_manifest_round_2.json
P4_ROUND_2_CHANGED_FILES.json
P4_ROUND_2_STARTING_WORKTREE_STATE.md
P4_ROUND_2_FINAL_WORKTREE_STATE.md
```

Submission 必须逐项回答 P4-R1-A 至 P4-R1-J，并提供：

- 每个 finding 的真实 RED 命令、RED 输出、GREEN 命令、GREEN 输出；
- source commit/未提交状态与完整 changed-files；
- 精确 Python、cwd、command、start/end、exit code、stdout hash；
- 独立 P4 tests、P0 contracts，以及所有可用上游 regression；
- Gate/mutation receipts 与 expected/observed failure code；
- fixture vs real evidence 分类；
- 所有仍缺失的 P3/P2/real-evidence blockers。

若代码修复完成但真实 P3 current-run artifact/P2 authority/real evidence 仍不可用，最后一行必须是：

```text
P4_ROUND_2_IMPLEMENTATION_COMPLETE_REAL_GATE_BLOCKED_READY_FOR_CHATGPT_AUDIT
```

如果存在任何 machinery failure，最后一行必须是：

```text
P4_ROUND_2_GATE_FAIL_NEEDS_REMEDIATION
```

不得声称 P4 Gate PASS，除非所有 machinery 与真实 current-run authority 项都由本次执行产物机器核验。

## 10. 审计结论

```text
CHATGPT_P4_ROUND_1_READ_ONLY_AUDIT_FAIL
P4_REMEDIATION_REQUIRED
P4_GATE_PASS_NOT_AUTHORIZED
P5_BLOCKED_PENDING_CHATGPT_P4_ROUND_2_AUDIT
```
