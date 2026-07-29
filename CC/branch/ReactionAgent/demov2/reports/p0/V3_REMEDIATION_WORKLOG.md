# V3 Remediation Worklog

> ChatGPT P0 Gate 第三轮修复工作日志。本文记录复现、决策、证据。

## 环境

专用 venv(满足 pyproject.toml 全部 specifier):

| 依赖 | 实际版本 | 要求 | 满足 |
|---|---|---|---|
| Python | 3.11.15 | >=3.11 | ✅ |
| pydantic | 2.13.4 | >=2.8,<3 | ✅ |
| pytest | 9.1.1 | >=8.0 | ✅ |
| pytest-json-report | 1.5.0 | 第17节需要 | ✅ |
| packaging | 26.2 | 第16节需要 | ✅ |

venv 路径:`demov2/.venv`(由 uv 创建)。Gate 运行命令:`.venv/bin/python scripts/run_p0_gate.py`。

注意:系统 anaconda 自带 pytest 7.4.0 < 8.0,不满足要求。系统 pip 损坏(启动即 SIGKILL)。改用 uv 创建独立 venv 解决。pydantic 从 2.11.10 升至 2.13.4,197 测试仍全过,向后兼容。

## 复现结果(第 2-3 步)

### 当前 Gate 与测试

- `197 passed`(venv 与系统环境均复现)
- 当前 Gate 报告 `10/10 PASS · READY_FOR_CHATGPT_AUDIT` — **假阳性**,ChatGPT REJECTED 正确

### 8 个残留假阳性复现(第 4 节)

脚本:`scripts/reproduce_v3_false_positives.py`

```text
site_transform_mismatch                       ACCEPTED (false positive)
target_not_in_query                           ACCEPTED (false positive)
unknown_source_ledger_reference               ACCEPTED (false positive)
donor_context_not_assumption                  ACCEPTED (false positive)
qualitative_confidence_note                   ACCEPTED (false positive)
self_bond_target                              ACCEPTED (false positive)
mechanistic_evidence_mismatch                 ACCEPTED (false positive)
formal_assignment_method_mismatch             ACCEPTED (false positive)

ACCEPTED (false positives): 8/8
```

8/8 全部复现。修复后须 0/8 接受。

### 根因定位

| 假阳性 | 根因 |
|---|---|
| site_transform_mismatch | `validate_hypothesis_references` 只查 ID 集合存在性,无 site→transformation 关系校验 |
| target_not_in_query | `AtomTarget` 只查非负,无 query 归属校验 |
| unknown_source_ledger_reference | `CandidateAnalogyLedger.source_ledger_id` 只 NonEmptyStr,无存在性校验 |
| donor_context_not_assumption | `InheritedDonorContext.is_assumption: bool` 接受 False |
| qualitative_confidence_note | `QueryCandidateAdaptation.confidence_note: NonEmptyStr` 绕过 confidence 禁令 |
| self_bond_target | `BondTarget` 无 begin≠end 校验 |
| mechanistic_evidence_mismatch | `MappingReport` 无 typed/flat evidence IDs 一致性校验 |
| formal_assignment_method_mismatch | `MappingReport` 无 typed/flat assignment method 一致性校验 |

### Gate 假阳性根因(第 15-18 节)

- `check_contract_tests`(run_p0_gate.py:386-418)**根本没有 JSON freshness 检查**,尽管 gate 名叫 "Contract tests + JSON freshness"
- skip/xfail 用 `"skip" in output.lower()` 字符串匹配(第 17 节)
- 环境版本只读 pyproject 不解析(第 16 节)
- P0-G02 只查 README wildcard,不查 ADR-0001 的 "All discussion files"(第 5 节)
- P0-G05 只验 policy 内部自洽,不查 ADR-0004/policy drift(第 13 节);ADR-0004 用 `partial_cofactor`,policy 用 `partial_cofactor_stoichiometry`

## 修复计划

按第 21 节 22 步顺序,分阶段 TDD(每阶段 RED→GREEN→REFACTOR):

1. ✅ 阅读权威文件 + 复现(本文)
2. ADR-0001 wildcard 修复(第 5 节)
3. relation-aware validation context(第 6-7 节)
4. is_assumption / confidence_note / canonical exception(第 8-9, 14 节)
5. MappingReport 双事实来源 / typed pair / unbound evidence(第 10-12 节)
6. ADR-0004 与 policy 对齐(第 13 节)
7. Gate 重写:freshness / env / pytest stats / 十项检查(第 15-18 节)
8. 隔离运行 + 完整报告(第 20-22 节)

## 权限边界遵守

- 仅写 `demov2/`
- 未执行任何 git 操作
- 未删除用户文件
- venv 为运行环境,非产品代码

## 最终结果(第三轮修复完成)

### 测试

- `270 passed`(原 197 + 73 新回归测试),零 fail/error/skip/xfail/xpass
- 6 个 v3 测试文件覆盖第 19 节 25 个负例

### 8 个残留假阳性(第 4 节)

修复后 8/8 REJECTED(脚本 `scripts/reproduce_v3_false_positives.py` 验证):

```text
site_transform_mismatch                       REJECTED (UnknownReferenceError)
target_not_in_query                           REJECTED (UnknownReferenceError)
unknown_source_ledger_reference               REJECTED (UnknownReferenceError)
donor_context_not_assumption                  REJECTED (ValidationError)
qualitative_confidence_note                   REJECTED (ValidationError)
self_bond_target                              REJECTED (ValidationError)
mechanistic_evidence_mismatch                 REJECTED (ValidationError)
formal_assignment_method_mismatch             REJECTED (ValidationError)
```

### Gate

- 10/10 PASS,`READY_FOR_CHATGPT_AUDIT`
- mutation 验证:改 `AgentProposedHypothesis.json` minLength=999 → P0-G10 FAIL → `NOT_READY`(证明非假阳性)

### 环境

| 依赖 | 实际 | 要求 | 满足 |
|---|---|---|---|
| Python | 3.11.15 | >=3.11 | ✅ |
| pydantic | 2.13.4 | >=2.8,<3 | ✅ |
| pytest | 9.1.1 | >=8.0 | ✅ |
| pytest-json-report | 1.5.0 | 第17节 | ✅ |
| packaging | 26.2 | 第16节 | ✅ |

### 修复项映射

| 提示词节 | 修复 | 状态 |
|---|---|---|
| §5 ADR-0001 wildcard | "All discussion files" → 精确措辞;README wildcard 加 exception;14 旧文档加 banner | ✅ |
| §6 relation registry | HypothesisReferenceRegistry 加关系字段;HypothesisValidationContext + validate_hypothesis_against_context | ✅ |
| §6 target-query | atom/bond target → query 校验 | ✅ |
| §7 ledger reference | LedgerReferenceRegistry + validate_candidate_ledger_references | ✅ |
| §8 is_assumption | Literal[True] | ✅ |
| §9 confidence_note | 删字段,换 AdaptationVerificationStatus 枚举;FORBIDDEN 扩展 | ✅ |
| §10 双事实来源 | typed/flat 一致性 + 派生 validator | ✅ |
| §11 typed atom pair | FormalMappedAtomPair, MechanisticAtomPair | ✅ |
| §12 unbound evidence | 禁止(ADR-0003 决策方案 A) | ✅ |
| §13 ADR/policy drift | 统一 partial_cofactor_stoichiometry;ADR-0004 加列 + JSON manifest;compare_manifests | ✅ |
| §14 canonical exception | UnknownReferenceError 统一到 schemas.errors | ✅ |
| §15 JSON freshness | json_structural_equal 全结构比较 | ✅ |
| §16 env specifier | packaging.version 真实比较 | ✅ |
| §17 pytest stats | pytest-json-report 结构化,零 skip/xfail | ✅ |
| §18 十项 Gate | 全部扩展真实检查 | ✅ |

### P1 状态

BLOCKED — P0 only,awaiting ChatGPT round-3 read-only audit。未进入 P1。

