# ChatGPT P3 Round 6 只读审计与 Round 7 定向修复

- 审计日期：2026-08-04
- 被审计工作区：`/Users/frank_gong/Documents/Codex/2026-08-03/ReactionAgent-p3-strict-kernel/CC/branch/ReactionAgent/demov2`
- 分支：`codex/p3-strict-kernel`
- P3 实现提交：`c43d6368bbad2056e6e85e4a43327b34d946c8bf`
- 审计时 HEAD：`a0fffdb2c126473c5879f68757c4c5dab13e68e5`
- 审计性质：严格核验 ChatGPT Round 5 修复计划 R6-A～R6-E；不是网络安全评估，不扩大原验收标准。

## 1. 最终裁决

```text
CHATGPT_P3_ROUND_6_READ_ONLY_AUDIT = FAIL
R6-A = CLOSED
R6-B = NOT_CLOSED
R6-C = NOT_CLOSED
R6-D = CLOSED_WITH_SUBMITTED_EVIDENCE
R6-E = CLOSED_WITH_METADATA_CORRECTION_REQUIRED
P3_IMPLEMENTATION_COMPLETE = NOT_ACCEPTED
P4 = BLOCKED
```

Round 6 已经真正修复 R6-A：真实执行 items 中的 `BLOCKED` 不能再通过修改提交 JSON 被提升成 verified PASS。

但 R6-B 和 R6-C 仍把“所有字段内部一致”误当成“来自既定 authority”：

1. 同时重写 mutation raw receipt、typed receipt 和所有 hash 后，verifier 仍返回 `verified=True`。
2. 将 caller-built fixture root 的 `kind` 改为 `production`、修改 provenance 并重算公开 self-hash 后，production loader 接受该 root。

这两项正是 Round 6 计划要求关闭的合同，因此 Round 6 不能通过，P4 继续 BLOCKED。

## 2. 独立复核结果

### 2.1 Round 6 定向测试

```text
tests/p3/test_r6a_execution_authority.py
tests/p3/test_r6b_mutation_receipt.py
tests/p3/test_r6c_production_authority.py

25 passed in 41.48s
```

### 2.2 P3 全量测试

```text
479 passed, 13 warnings in 174.37s
```

### 2.3 P3 Gate

独立 probe 实际调用了 `run_p3_gate(run_mutations=True)`；当前 Gate 仍诚实保持：

```text
G01/G03/G07 = BLOCKED
其余 7 项 = PASS
mutations = 14/14 valid
official verdict = BLOCKED
```

### 2.4 已验证为正确的 R6-A

独立重放 Round 5 的精确攻击：保留真实 execution items，仅把提交报告的 G01/G03/G07 从 `BLOCKED` 改成 `PASS`。

实际结果：

```json
{
  "verdict": "FAIL",
  "verified": false,
  "failures": [
    "EXECUTED_STATUS_MISMATCH:G01",
    "EXECUTED_EVIDENCE_KIND_MISMATCH:G01",
    "EXECUTED_STATUS_MISMATCH:G03",
    "EXECUTED_EVIDENCE_KIND_MISMATCH:G03",
    "EXECUTED_STATUS_MISMATCH:G07",
    "EXECUTED_EVIDENCE_KIND_MISMATCH:G07"
  ]
}
```

裁决：R6-A CLOSED。

## 3. R7-A — mutation execution authority 仍未闭环

- 映射到 Round 6：R6-B
- 严重级别：P0
- 状态：NOT CLOSED

### 3.1 计划要求

Round 6 计划要求 mutation outcome 必须绑定同一次受信执行，而不是只验证提交字段之间彼此一致。尤其要求：

```text
如果选择 in-process authority，mutation receipts 必须与 R6-A 共用
不可由 submission 公开注入的 execution context。
```

### 3.2 当前实现缺口

当前 `GateExecutionAuthority` 只保存和比较：

```text
GateItemResult items
```

它没有保存：

```text
实际执行的 MutationResult
实际 receipt canonical digest
实际 mutation session nonce / execution identity
```

`run_p3_gate()` 在 mutation suite 执行之前就调用：

```python
_register_execution_authority("p3_gate", items)
```

因此 R6-A complete-match 只能保护 Gate items，不能保护 mutations。

R6-B verifier 会解析 marker-delimited JSON，并比较 raw receipt 与 typed fields；但 raw receipt、typed fields、artifact hash 和 stdout hash 全部都在 submitted report 中，调用者可以一起同步修改。

随机 `session_nonce` 也包含在 report/receipt 中，只能用于关联字段，不能单独证明 receipt 来自本次 runner execution。

### 3.3 独立复现

步骤：

1. 执行真实 P3 Gate，取得真实 report 和已注册的 R6-A item authority。
2. 解析一个真实 mutated receipt。
3. 修改 receipt 内的 artifact。
4. 重算 receipt `artifact_hash`。
5. 同步更新 typed `run.artifact` 和 `run.artifact_hash`。
6. 重新生成完整 marker-delimited raw receipt。
7. 重算 `stdout_stderr_hash`。
8. 其余 mutation contract 字段保持合法。
9. 调用 `evaluate_gate_artifact()`。

实际结果：

```json
{
  "probe": "r6b_both_raw_and_typed_receipt_rewritten",
  "verdict": "BLOCKED",
  "verified": true,
  "failures": []
}
```

这与 submission 的 residual-risk 声明直接冲突。submission 写道：

```text
a self-consistent rewrite of BOTH ... is detected by the R6-A execution authority
```

实际 R6-A authority 不包含 mutations，所以没有检测到。

### 3.4 为什么现有 9 个 R6-B 测试仍然通过

现有测试分别覆盖：

- 只改 typed artifact；
- 只改 raw output；
- 清空身份字段；
- 修改 stored status/failure code；
- 修改 nonce 的一侧。

它们没有覆盖最关键的同步变体：

```text
raw receipt + typed fields + artifact hash + stdout hash 全部同步重建
```

### 3.5 Round 7 最小修复

不要再增加一层 self-hash、marker 或普通 nonce。直接扩展已经有效的 R6-A in-process authority：

1. `GateExecutionAuthority` 必须同时绑定实际执行的 items 和 mutations。
2. authority 只能在 mutation suite 完成后注册。
3. authority 保存不可变的 executed mutations，或保存由 runner 直接计算的完整 canonical mutation digests。
4. `evaluate_gate_artifact()` 必须 exact-match submitted mutations 与 executed mutations。
5. mutation verdict、caught/valid、observed code 必须从 authority 中的 executed mutations 推导。
6. 缺少、额外、重复、顺序替换、receipt 全字段同步重写都必须产生明确 failure code，并令 `verified=False`。

必须新增一个核心测试：

```text
test_simultaneous_raw_and_typed_receipt_rewrite_fails_against_execution_authority
```

该测试必须完整执行上面九步攻击，并精确断言：

```text
verdict = FAIL
verified = False
failure contains EXECUTED_MUTATION_MISMATCH
```

## 4. R7-B — production authority 仍可由 caller 自行声明

- 映射到 Round 6：R6-C
- 严重级别：P0
- 状态：NOT CLOSED

### 4.1 计划要求

Round 6 计划明确要求：

```text
caller-built fixture manifest can NEVER be accepted as a production authority
```

### 4.2 当前实现缺口

`FrozenAuthorityManifest` 仍是普通、公开、可构造的 dataclass：

```text
kind: str
provenance: str
manifest_hash: str
```

production loader 的核心判断只是：

```python
train_view.authority_manifest.kind == "production"
```

而 `authority_manifest_hash()` 是公开函数，self-hash 的全部输入也是调用者可控字段。

因此 self-hash 只能证明字段彼此一致，不能证明 root 来自 P1/P2。

### 4.3 独立复现

步骤：

1. 使用公开 `build_fixture_authority_manifest()` 创建 fixture root。
2. 使用 `dataclasses.replace()` 把 `kind` 改为 `production`。
3. 把 provenance 改成任意 production 声明。
4. 使用公开 `authority_manifest_hash()` 重算 self-hash。
5. 把该 root 传给 train view。
6. 使用 `EvidenceKind.real` 调用真实 `load_reaction_evidence()`。

实际结果：

```json
{
  "probe": "r6c_caller_relabels_fixture_root_as_production",
  "accepted": true,
  "reaction_id": "fx_hydrolysis",
  "root_kind": "production",
  "root_provenance": "caller-claims-p1-production"
}
```

### 4.4 为什么现有 R6-C 测试没有发现

现有测试只验证未经修改的 fixture root：

```text
root.kind == synthetic_fixture -> real loader rejects
```

它没有验证调用者同步修改 `kind + provenance + self-hash`。

### 4.5 Round 7 最小修复

目前真实 P1/P2 production authority 尚不可用，所以正确行为是诚实 BLOCKED，而不是用字符串模拟 production authority。

建议最小实现：

1. 将 fixture manifest 与 production authority 分成不同类型。
2. `build_fixture_authority_manifest()` 永远只返回 `FixtureAuthorityManifest`。
3. real loader 必须要求 `ProductionAuthorityHandle`，不能接受带 `kind="production"` 的普通 manifest。
4. `ProductionAuthorityHandle` 只能由验证真实 P1/P2 snapshot/lineage/ledger/eligibility 产物的内部 adapter 创建。
5. 在真实 P1/P2 root 不可用时，real loader/kernel 必须返回 `PRODUCTION_AUTHORITY_UNAVAILABLE` 或等价的 typed BLOCKED，不得制造 production root。
6. fixture mode 继续允许 fixture authority，但 evidence kind 必须保持 synthetic fixture。
7. self-hash 仅作为 integrity check，不得作为 provenance authority。

必须新增一个核心测试：

```text
test_fixture_root_relabelled_and_rehashed_as_production_is_rejected
```

测试必须完整执行上述六步复现，并精确断言：

```text
accepted = False
failure_code = FIXTURE_MANIFEST_AS_PRODUCTION_AUTHORITY
或 PRODUCTION_AUTHORITY_UNAVAILABLE
```

## 5. 其余 finding 裁决

### R6-D

`scripts/run_p0_gate.py` 将原来的隐式 180 秒 timeout 改为显式、版本化的 600 秒，并记录 duration。submission 记录 full suite 1385/1385、P0 Gate 10/10、exit 0。本轮未发现与 R6-D 计划相冲突的实现。

裁决：CLOSED WITH SUBMITTED EVIDENCE。

### R6-E

P3 实现已冻结在本地 commit `c43d636...`，后续交付物也有独立 commits，满足“代码不再是 untracked”的核心要求。

但 submission 顶部写 `head=c43d636...`，正文又写 final HEAD `3679488...`，审计时实际 HEAD 为 `a0fffdb...`。后两次提交仅是 Round 6 文档补充/拼写修复，不改变 P3 实现，但 Round 7 submission 必须区分：

```text
implementation_commit
deliverables_commit
audit_target_head
```

裁决：CLOSED，metadata correction required。

## 6. Round 7 范围限制

Round 7 只修两项：

```text
R7-A: execution authority 覆盖 mutations
R7-B: fixture authority 与 production authority 类型隔离
```

不要再次重写全部 P3，不要修改化学 kernel、ranking、P4、P0/P1 frozen scientific contracts，也不要重新设计已经通过的 R6-A/R5-D/R5-E。

完成后必须真实运行：

```text
新增 R7-A/R7-B 定向测试
全部 R6 回归测试
tests/p3
tests
P0 Gate
P1 Gate
P3 Gate（真实资源缺失时必须继续 BLOCKED/exit 2）
```

提交文件：

```text
reports/p3/SUBMISSION_TO_CHATGPT_P3_ROUND_7.md
reports/p3/P3_ROUND_7_AUDIT_EVIDENCE.json
reports/p3/P3_ROUND_7_REMEDIATION_WORKLOG.md
reports/p3/P3_GATE_REPORT_ROUND_7.json
reports/p3/P3_ROUND_7_CHANGED_FILES.json
```

submission 最后一行：

```text
P3_ROUND_7_READY_FOR_CHATGPT_READ_ONLY_AUDIT_P4_BLOCKED
```

## 7. 最终状态

```text
FINAL_DECISION = ROUND_6_REJECTED
NEXT_ACTION = FIX_R7_A_AND_R7_B_ONLY
P4_STATUS = BLOCKED
```
