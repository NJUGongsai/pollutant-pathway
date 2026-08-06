# ChatGPT P3 Round 8 Final Read-Only Audit

审计日期：2026-08-04  
审计对象：`codex/p3-strict-kernel`  
审计工作树：`/Users/frank_gong/Documents/Codex/2026-08-03/ReactionAgent-p3-strict-kernel/CC/branch/ReactionAgent/demov2`  
审计时 HEAD：`9ab712a81cbcf1c25aa3b2452d4c85d3bbef20d8`  
Round 8 实现提交：`71dd1c86a3c4a6088f81460dd94e5ae9dacf1ea5`  
Round 8 交付物提交：`b1b2ff0`，元数据收尾提交：`9ab712a`

## 1. 最终结论

**CHATGPT_P3_ROUND_8_READ_ONLY_AUDIT = PASS**

**R8-A（返回的 GateReport 与内部 execution authority 共享可变对象）= CLOSED**

**P3 实现与验证机制 = ACCEPTED；不需要 Round 9。**

本轮解除的是“等待 ChatGPT 审核”对 P4 的阻断。P4 可以使用冻结的 P3→P4 接口继续开发、集成与只读审核；正式阶段 Gate 仍必须遵守既定的 P2→P3→P4→P5 顺序，且不得把 synthetic/curated fixture 当作真实生产证据。

P3 当前真实证据 Gate 继续诚实返回 `BLOCKED`，原因是生产 snapshot、自动 donor 检索和 pilot funnel 等真实资源尚未齐备。这是数据/证据可用性状态，不是本轮实现失败，也不能被改写为 `PASS`。

## 2. 审计范围与提交边界

Round 8 的唯一代码目标是关闭 Round 7 留下的对象引用共享问题。实现提交 `71dd1c8` 修改了：

- `reaction_agent/p3/gate.py`
- `tests/p3/test_r8a_authority_aliasing.py`
- `scripts/p3/r8_aliasing_probes.py`
- `scripts/capture_p3_round8_evidence.py`
- `scripts/generate_p3_round8_reports.py`

未发现 Round 8 为迎合审核而修改 P0/P1 冻结合同、P4 实现或既有 P3 kernel/ranking 语义。工作树中仍存在大量继承的 P0/P1/P2/P4/P5 脏文件；这些文件不是 Round 8 提交的一部分，本审计没有修改、清理或把它们归因于 Round 8。

## 3. 代码复核

### 3.1 注册时建立独立快照

`reaction_agent/p3/gate.py:233-244` 使用 `model_dump(mode="json")` 后序列化为字符串，在 authority 注册时完成按值快照。字符串本身不可变，内部保存的不再是返回报告中的 Pydantic 对象或其嵌套容器引用。

`reaction_agent/p3/gate.py:287-310` 将 items 和 mutations 分别保存为 `_item_snapshots` 与 `_mutation_snapshots`，`_by_id` 也只保存对应的快照字符串。

### 3.2 所有读取接口只返回新副本

`reaction_agent/p3/gate.py:312-328` 的 `items`、`mutations` 和 `executed()` 每次都对内部字符串重新 `json.loads()`。调用方修改读取结果时，只会修改临时副本，无法反向改变内部审计基准。

### 3.3 验证逻辑按值对照内部快照

`reaction_agent/p3/gate.py:927-1002` 使用 authority 的副本与提交的 item/mutation 逐项、逐值比较。items 覆盖 status、title、evidence kind 与完整 evidence；mutations 覆盖数量、顺序和完整 mutation record。任何差异都会形成明确的 mismatch，并使 `verified=False`、verdict 为 `FAIL`。

`reaction_agent/p3/gate.py:1012-1031` 从内部执行快照派生最终状态，而不是相信调用方提交的状态。

结论：Round 8 的修复位于正确的信任边界，且没有通过额外例外、硬编码 PASS 或弱化原有完整匹配合同来绕开问题。

## 4. ChatGPT 独立验证

以下命令由本次审核独立执行，不是仅复述提交者报告。

### 4.1 独立行为探针

执行：

```bash
PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH=/Users/frank_gong/Documents/Codex/2026-08-03/ReactionAgent-p3-strict-kernel/CC/branch/ReactionAgent/demov2 \
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/.venv/bin/python \
/Users/frank_gong/Documents/Codex/2026-08-03/ReactionAgent-p3-strict-kernel/CC/branch/ReactionAgent/demov2/scripts/p3/r8_aliasing_probes.py
```

结果：exit code `0`，五类检查全部符合预期：

1. 修改返回报告中的 mutation 后：`FAIL`、`verified=false`、`EXECUTED_MUTATION_MISMATCH`；
2. 修改返回报告中的 Gate item 后：`FAIL`、`verified=false`，出现 evidence/status mismatch；
3. report mutation/item 与 authority 返回值均不是同一对象；
4. 修改后 authority snapshot 未改变，修改内容没有泄漏到 authority；
5. 未修改的真实 Gate artifact 仍为 `verified=true`，且无 machinery failure；业务状态诚实为 `BLOCKED`。

### 4.2 Round 7/8 定向回归

执行三个定向文件：

```text
tests/p3/test_r8a_authority_aliasing.py
tests/p3/test_r7a_mutation_execution_authority.py
tests/p3/test_r7b_fixture_production_authority_isolation.py
```

独立结果：**17 passed in 29.05s**。

这同时证明：

- Round 8 的对象隔离合同通过；
- Round 7 的 executed-mutation 完整绑定未退化；
- fixture/production authority 类型隔离未退化。

### 4.3 完整 P3 测试集

执行：

```bash
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/.venv/bin/python \
  -m pytest -q -p no:cacheprovider tests/p3
```

独立结果：**496 passed, 13 warnings in 61.30s**。

13 条 warning 是既有 Pydantic deprecated-access/对抗测试 serializer warning，不构成本轮失败；建议后续作为一般维护债务处理，不应据此阻断 P3→P4 交接。

## 5. 提交证据一致性核对

已读取并核对：

- `reports/p3/SUBMISSION_TO_CHATGPT_P3_ROUND_8.md`
- `reports/p3/P3_ROUND_8_AUDIT_EVIDENCE.json`
- `reports/p3/P3_ROUND_8_REMEDIATION_WORKLOG.md`
- `reports/p3/P3_GATE_REPORT_ROUND_8.json`

提交的结构化证据记录：

- R8 定向测试：3 passed；
- R7-A 回归：7 passed；
- R7-B 回归：7 passed；
- P3 suite：496 passed；
- full suite：1402 passed；
- P0 Gate：10/10；
- P1 Gate：10/10；
- P3 Gate：exit 2、诚实 `BLOCKED`。

其中行为探针、17 项定向回归和完整 P3 suite 已由 ChatGPT 独立复跑。full suite 与 P0/P1 Gate 的数字在本轮作为已提交证据核对，未再次完整复跑；它们不是关闭 R8-A 所必需的唯一依据。

Submission 末行精确为：

```text
P3_ROUND_8_READY_FOR_CHATGPT_READ_ONLY_AUDIT_P4_BLOCKED
```

该状态在提交时是正确的；本审计通过后，应更新交接语义，而不是修改历史 submission。

## 6. Findings

### Blocking findings

无。

### Major findings

无。

### Minor/non-blocking observations

1. `GateExecutionAuthority` 类文档中仍有一处旧措辞称 authority 保存 “TYPED items/mutations”，而 Round 8 实现已改为保存 canonical JSON snapshots。代码行为和测试正确；这是文档维护问题，不需要开启 Round 9。
2. 完整 P3 suite 有 13 条既有 warning，可在后续常规维护中清理，不影响本轮接受。

## 7. 阶段交接决定

最终交接状态：

```text
P3_IMPLEMENTATION_ACCEPTED
P3_ROUND_8_FINDING_CLOSED
P3_REAL_EVIDENCE_GATE_BLOCKED
P4_UNBLOCKED_FROM_CHATGPT_P3_AUDIT
NO_P3_ROUND_9_REQUIRED
```

P4 后续必须遵守：

- 只消费冻结且已审阅的 P3 candidate/trace/interface；
- 不修改 P0/P1/P2/P3 冻结合同来适配下游实现；
- fixture 只能证明流程与合同，不能冒充真实反应/真实性能证据；
- 正式 P4 Gate 仍需核验其真实上游 authority 和阶段依赖；
- P3 的真实证据条件满足前，任何报告都不得声称 P3 production Gate PASS。

## 8. 审计签字

```text
CHATGPT_P3_ROUND_8_READ_ONLY_AUDIT_PASS
P3_ACCEPTED_FOR_P4_INTEGRATION_WITH_P3_REAL_EVIDENCE_GATE_BLOCKED
```
