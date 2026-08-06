# ChatGPT P3 Round 7 只读审计与 Round 8 单点修复

- 日期：2026-08-04
- 工作区：`/Users/frank_gong/Documents/Codex/2026-08-03/ReactionAgent-p3-strict-kernel/CC/branch/ReactionAgent/demov2`
- 分支：`codex/p3-strict-kernel`
- Round 7 实现提交：`b853f7b`
- 审计时 HEAD：`8c19e3a31fe529c5a98d96dbf9a49c4233f6a462`
- 范围：只审核上一轮要求的 R7-A、R7-B；这是普通代码正确性审核，不是网络安全审核。

## 1. 结论

```text
CHATGPT_P3_ROUND_7_READ_ONLY_AUDIT = FAIL
R7-B = CLOSED
R7-A = PARTIALLY_CLOSED_ONE_ALIASING_BUG_REMAINS
P3 = NOT_ACCEPTED
P4 = BLOCKED
```

Round 7 的主要方向正确：

- execution authority 已开始保存 mutations；
- serialized dict 中同步修改 raw receipt 与 typed fields 会被拒绝；
- fixture authority 与 production authority 已分成不同类型；
- fixture root 不能再通过修改 `kind` 冒充 production root。

但是 `GateExecutionAuthority` 保存的是与返回 `GateReport` 共用的同一批可变对象，而不是独立、不可变的执行快照。修改返回 report 中的 mutation，会同时修改 authority 中的“审核依据”，最终仍可得到 `verified=True`。

Round 8 只修这一个普通对象引用问题，不再增加其他要求。

## 2. 已通过部分

### 2.1 R7-B 已关闭

独立运行项目自带 Round 7 probe，结果为：

```text
fixture root relabel -> rejected
fixture root passed to real loader -> FIXTURE_MANIFEST_AS_PRODUCTION_AUTHORITY
public ProductionAuthorityHandle construction -> rejected
real Gate -> BLOCKED, verified=True, machinery_failures=[]
```

代码已经实现：

- `FixtureAuthorityManifest` 与 `ProductionAuthorityHandle` 类型隔离；
- fixture manifest 的 kind 固定为 `synthetic_fixture`；
- real loader 要求 `ProductionAuthorityHandle`；
- 真实 P1/P2 root 不可用时诚实返回 `PRODUCTION_AUTHORITY_UNAVAILABLE`；
- fixture mode 仍保持 `synthetic_fixture`。

裁决：R7-B CLOSED。

### 2.2 R7-A 的 serialized-dict 攻击已关闭

项目自带 Round 7 probe 能正确拒绝：

```text
同步重写 serialized raw receipt + typed fields
缺少 mutation
额外 mutation
mutation 重排
adjudication 字段修改
```

其中同步重写会得到：

```text
EXECUTED_MUTATION_MISMATCH
verified=False
```

说明 complete-match 逻辑本身正确。

### 2.3 提交证据

Round 7 structured evidence 记录：

```text
R7-A tests: 7/7 passed
R7-B tests: 7/7 passed
P3 suite: 493/493 passed
full suite: 1399/1399 passed
P0 Gate: 10/10
P1 Gate: 10/10
P3 Gate: BLOCKED, exit 2
```

本轮独立运行 `scripts/p3/r7_attack_probes.py`：exit 0，所有已声明 probes 均符合预期。

## 3. 唯一剩余问题：authority 与 report 共用可变对象

### 3.1 原因

`run_p3_gate()` 生成 `items` 和 `mutations` 后，将相同对象同时交给：

```text
GateExecutionAuthority
GateReport
```

`GateExecutionAuthority` 虽然把 list 转成了 tuple，但 tuple 只保证容器不能增删，不会让里面的 Pydantic model 和嵌套 dict 变成不可变对象。

因此：

```python
report.mutations[0] is authority.mutations[0]
```

实际为：

```text
True
```

修改 `report.mutations[0].mutated.artifact` 时，authority 中的 mutation 也被同步修改。

### 3.2 独立复现

步骤：

1. 调用真实 `run_p3_gate()`。
2. 取得返回的 `report` 和已注册的 execution authority。
3. 确认两者保存同一个 mutation object。
4. 从返回 report 的 typed mutation 修改 artifact。
5. 同步重建 raw receipt、artifact hash 和 stdout hash。
6. 再把 `report.model_dump()` 交给 `evaluate_gate_artifact()`。

实际结果：

```json
{
  "same_object": true,
  "authority_changed_through_report_alias": true,
  "verdict": "BLOCKED",
  "verified": true,
  "failures": []
}
```

这不是网络问题，只是 Python 对象引用共享导致“原始审核依据”被返回结果一起修改。

### 3.3 Round 8 唯一修复要求

`GateExecutionAuthority` 不得保存与返回 report 共享的可变对象。

推荐最小修复：

1. 注册 authority 时，立即把 executed items 和 executed mutations 转换成独立 canonical JSON snapshots，或对其做真正的深拷贝后冻结。
2. authority 内部优先保存 canonical serialized snapshots/digests，不再暴露原始可变 model references。
3. `evaluate_gate_artifact()` 使用 authority 中的独立快照进行 exact-match。
4. 修改返回的 `GateReport` 及任何嵌套 dict/list，均不得改变 authority 内的快照。
5. 同样处理 `items` 与 `mutations`，避免相同 aliasing 问题在 Gate items 上出现。
6. 不需要新增签名、网络组件、数据库或其他复杂设计。

必须新增两个精确测试：

```text
test_mutating_returned_report_mutation_does_not_change_execution_authority
test_mutating_returned_report_item_does_not_change_execution_authority
```

第一个测试必须复现本审计的完整步骤，并断言：

```text
same_object=False，或 authority 仅保存不可变 snapshot
authority snapshot unchanged
verdict=FAIL
verified=False
failure contains EXECUTED_MUTATION_MISMATCH
```

第二个测试修改返回 report 的 item status/evidence，并断言 authority 中的 executed item 不变，evaluation FAIL。

## 4. Round 8 执行边界

只允许修改：

```text
reaction_agent/p3/gate.py
tests/p3/新增或对应 Round 8 定向测试
必要的 Round 8 报告生成文件
```

禁止：

```text
重写 R7-B
修改化学 kernel
修改 P0/P1 frozen scientific contracts
启动 P4
伪造 P3 Gate PASS
push 或 merge
```

完成后运行：

```text
Round 8 两个 aliasing tests
R7-A/R7-B regression
tests/p3
tests
P0 Gate
P1 Gate
P3 Gate（真实资源仍缺失时保持 BLOCKED/exit 2）
```

提交：

```text
reports/p3/SUBMISSION_TO_CHATGPT_P3_ROUND_8.md
reports/p3/P3_ROUND_8_AUDIT_EVIDENCE.json
reports/p3/P3_ROUND_8_REMEDIATION_WORKLOG.md
reports/p3/P3_GATE_REPORT_ROUND_8.json
reports/p3/P3_ROUND_8_CHANGED_FILES.json
```

最后一行：

```text
P3_ROUND_8_READY_FOR_CHATGPT_READ_ONLY_AUDIT_P4_BLOCKED
```

## 5. 最终状态

```text
FINAL_DECISION = ROUND_7_REJECTED_ONE_FIX_REMAINS
NEXT_ACTION = REMOVE_REPORT_AUTHORITY_MUTABLE_ALIASING
P4_STATUS = BLOCKED
```
