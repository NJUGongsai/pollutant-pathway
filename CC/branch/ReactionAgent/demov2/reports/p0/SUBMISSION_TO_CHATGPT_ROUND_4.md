# P0-G03 V4 Fail-Closed Remediation — Submission to ChatGPT Round-4 Read-Only Audit

> **Task:** P0 第四轮精确修复（fail-closed context validation）
> **Executing model:** Qwen (代码实施) + Claude (多智能体编排 SDD)
> **Auditing model:** ChatGPT (第四轮只读审核)
> **Working directory:** `/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2`
> **Gate timestamp (UTC):** 2026-07-29T11:10:19Z
> **Status:** `READY_FOR_CHATGPT_ROUND_4_AUDIT`
> **P1:** `BLOCKED pending ChatGPT audit`

---

## 0. 本轮目标与根因（供审核上下文）

### 目标（spec §0）
把 hypothesis/context validation 从"有上下文时才检查"的 opt-in 行为，修复为生产接纳路径上的 fail-closed 行为：

```
缺少验证所必需的上下文  ≠  暂时跳过验证  =  明确拒绝并返回 typed contract violation
```

### 根因（OLD `hypothesis.py` 的 4 个 fail-open 点）
1. **ProductionSelection 关系校验 map-absent 跳过** — 三个 `if X in map:` 守卫，map 为空（默认）时跳过，IDs 仅存在即被接受。
2. **AgentProposed relaxation policy-null 跳过** — 仅 `if policy is not None:` 时校验，`allowed_relaxation_ids=[r1]` + `policy=None` 被接受（只查全局存在，不查归属 policy）。
3. **target membership 双空跳过** — `if context.query_atom_ids or context.query_bond_pairs:` 守卫，两集合都空（默认）时整块跳过；且字段默认 `frozenset()` 无法区分"未提供"与"显式空"。
4. **registry 无 `model_validator`** — 可构造 `site_to_transformation_id={"s1": "t_unknown"}` 而 `"t_unknown"` 不在 `transformation_ids` 中，构造成功，自相矛盾。

### 修复（6 处，详见 §7 文件清单）
- `HypothesisReferenceRegistry` 加 `@model_validator(mode="after")` 校验 5 个 relation map 的 key/value 内部一致性（spec §5.3）
- `validate_hypothesis_references` ProductionSelection 分支 fail-closed 完整关系链（spec §5.1 规则 1-13）
- `validate_hypothesis_references` AgentProposed 分支 relaxation 成对不变量（spec §5.5）
- `HypothesisValidationContext` query 字段三态化 `frozenset[int] | None = None`（spec §5.4）
- `validate_hypothesis_against_context` target membership fail-closed（spec §5.4）
- docstrings 删除 opt-in 口径（spec §11.1）

### 错误方案
**Plan A**：复用现有 `UnknownReferenceError`（`ContractViolation` 子类），零改 `errors.py` / `__init__.py`，靠 5 类消息文本区分（unknown ID / missing relation coverage / relation mismatch / missing query context / relaxation policy missing）。registry 构造时一致性违例抛 `ValueError`（pydantic 包成 `ValidationError`）。

---

## 1. 审核材料文件（§15.1-3）

请审核以下三个文件（已重新生成/创建，内容一致）：

| # | 文件 | 路径 | 说明 |
|---|------|------|------|
| 1 | Gate 报告 (MD) | `reports/p0/P0_GATE_REPORT.md` | 10 项 gate check 逐项证据 + deviations/assumptions/risks |
| 2 | Gate 报告 (JSON) | `reports/p0/P0_GATE_REPORT.json` | 结构化报告，含 G10 stats、env、freshness、changed_files |
| 3 | V4 修复工作日志 | `reports/p0/V4_REMEDIATION_WORKLOG.md` | §11.3 全 12 节：baseline、RED、根因、改动、schema 决策、测试、gate、反例、行为矩阵、声明 |

---

## 2. 最终 Gate 命令（§15.4）

```bash
.venv/bin/python scripts/run_p0_gate.py
```

**结果（gate timestamp 2026-07-29T11:10:19Z）：**

```
✅ PASS  P0-G01: Six ADRs complete and approved
✅ PASS  P0-G02: Authority consistency (README + ADR-0001)
✅ PASS  P0-G03: Hypothesis lanes + relation validation
✅ PASS  P0-G04: Dual ledger boundary
✅ PASS  P0-G05: Eligibility policy + ADR drift check
✅ PASS  P0-G06: Mapping/mechanism consistency
✅ PASS  P0-G07: Decision state machine + recursive forbidden scan
✅ PASS  P0-G08: MCP side-effect policy
✅ PASS  P0-G09: Legacy metrics provisional
✅ PASS  P0-G10: Contract tests + JSON freshness + env

Result: 10/10 passed
Status: READY_FOR_CHATGPT_AUDIT
exit code: 0
```

- **P0-G03 evidence:** `lanes + fail-closed relations verified (1 positive, 5+ negatives)`
  - positive：完整关系链（reaction / lineage / lineage→reaction / transformation / transformation→lineage / site / site→transformation 全部提供）
  - 5 个 gate 直接执行的负例：empty relation maps、uncovered site、missing query context、relaxation+policy-null、inconsistent registry key/value（construction-time ValidationError）
- **Gate 失败时仍返回非零退出码**（`main(): return 0 if all_passed else 1`）。

---

## 3. 测试精确统计（§15.5）

### Targeted tests（spec §12.1）
```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest \
  tests/contracts/test_v3_hypothesis_relations.py \
  tests/contracts/test_hypothesis_lanes.py \
  tests/contracts/test_v4_fail_closed_context.py \
  -q -p no:cacheprovider -ra
```
**结果：`45 passed`**（0 fail / 0 error / 0 skip / 0 xfail / 0 xpass）

### Full contract tests（spec §12.2）
```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest tests/contracts -q -p no:cacheprovider -ra
```
**结果：`290 passed`**（0 fail / 0 error / 0 skip / 0 xfail / 0 xpass）

### Gate G10 内部 pytest 结构化统计（从 `P0_GATE_REPORT.json`）
```
collected = 290, passed = 290, failed = 0, errors = 0,
skipped = 0, xfailed = 0, xpassed = 0
```
满足 spec §12.2 要求：`failed=0, errors=0, skipped=0, xfailed=0, xpassed=0, passed=collected`。

### Existing false-positive reproduction（spec §12.3）
```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/reproduce_v3_false_positives.py
```
**结果：`12/12 REJECTED`**（原 8 个 c1-c8 + 新 4 个 fail-open 反例 c9-c12）

```
  site_transform_mismatch                       REJECTED (UnknownReferenceError)
  target_not_in_query                           REJECTED (UnknownReferenceError)
  unknown_source_ledger_reference               REJECTED (UnknownReferenceError)
  donor_context_not_assumption                  REJECTED (ValidationError)
  qualitative_confidence_note                   REJECTED (ValidationError)
  self_bond_target                              REJECTED (ValidationError)
  mechanistic_evidence_mismatch                 REJECTED (ValidationError)
  formal_assignment_method_mismatch             REJECTED (ValidationError)
  production_empty_relation_maps_mismatch       REJECTED (UnknownReferenceError)   ← §3.2 A
  agent_empty_query_context_target              REJECTED (UnknownReferenceError)   ← §3.2 B
  relaxation_without_selected_policy            REJECTED (UnknownReferenceError)   ← §3.2 C
  registry_internal_contradiction               REJECTED (ValidationError)         ← §3.3

ACCEPTED: 0/12
REJECTED: 12/12
```

### JSON Schema freshness（G10 子项）
`12/12 fresh`（导出 schema 与 `model_json_schema()` 结构相等；`HypothesisValidationContext` 不在导出列表，三态字段改动不影响 freshness）。

---

## 4. 行为矩阵（§15.6 / spec §13）— ACTUAL ACCEPT/REJECT 结果

20 项全部实跑，每项标注实际结果 + 可追溯证据（测试名/reproduce case/gate negative）。**20/20 实际结果匹配预期**（5 ACCEPT + 15 REJECT）。

| # | Case | Expected | Actual | Evidence |
|---|------|----------|--------|----------|
| 1 | 完整、关系一致的 ProductionSelection | ACCEPT | ACCEPT ✓ | `test_v4::test_full_production_selection_accepted` passed (no raise) |
| 2 | 所有 ID 单独存在，但 relation maps 为空 | REJECT | REJECT ✓ | `test_v4::test_all_ids_exist_but_relation_maps_empty` (raises UnknownReferenceError); reproduce c9; gate G03 neg1 |
| 3 | site ID 存在，但 site relation 未覆盖当前 site | REJECT | REJECT ✓ | `test_v4::test_relation_maps_present_but_site_uncovered`; gate G03 neg2 |
| 4 | site 属于另一 transformation | REJECT | REJECT ✓ | `test_v3::test_site_belongs_to_another_transformation_rejected`; reproduce c1; gate G03 orig-neg |
| 5 | transformation relation 未覆盖当前 transformation | REJECT | REJECT ✓ | `test_v4::test_relation_maps_present_but_transformation_uncovered` |
| 6 | transformation 不来源于 cited lineage | REJECT | REJECT ✓ | `test_v3::test_transformation_not_from_cited_lineage_rejected` |
| 7 | lineage relation 未覆盖 cited lineage | REJECT | REJECT ✓ | `test_v4::test_cited_lineage_has_no_lineage_to_reaction_mapping` |
| 8 | lineage 属于另一 reaction | REJECT | REJECT ✓ | `test_v3::test_lineage_belongs_to_another_reaction_rejected` |
| 9 | registry relation 指向未知 ID | REJECT | REJECT ✓ | `test_v4::test_registry_site_map_value_not_in_transformation_ids` + 3 sibling; reproduce c12; gate G03 neg5 (ValidationError at construction) |
| 10 | AgentProposed AtomTarget 属于 query | ACCEPT | ACCEPT ✓ | `test_v4::test_legal_atom_target_accepted` |
| 11 | AgentProposed AtomTarget 不属于 query | REJECT | REJECT ✓ | `test_v3::test_atom_target_not_in_query_rejected`; reproduce c2 |
| 12 | AgentProposed target 存在，但 query context 未提供 | REJECT | REJECT ✓ | `test_v4::test_agent_target_present_but_query_context_not_provided`; reproduce c10; gate G03 neg3 |
| 13 | 合法 BondTarget 属于 query | ACCEPT | ACCEPT ✓ | `test_v4::test_legal_bond_target_accepted` |
| 14 | BondTarget 不属于 query | REJECT | REJECT ✓ | `test_v3::test_bond_target_not_in_query_rejected` |
| 15 | BondTarget context 未提供 | REJECT | REJECT ✓ | `test_v4::test_bond_target_present_but_query_bond_pairs_none` |
| 16 | 无 policy 且无 relaxation | ACCEPT | ACCEPT ✓ | `test_v4::test_legal_atom_target_accepted` (AgentProposed default policy=null, allowed=[]) |
| 17 | 无 policy 但有 relaxation | REJECT | REJECT ✓ | `test_v4::test_relaxation_non_empty_but_policy_null`; reproduce c11; gate G03 neg4 |
| 18 | policy 存在且 relaxation 被允许 | ACCEPT | ACCEPT ✓ | `test_v4::test_legal_relaxation_accepted` |
| 19 | policy 存在但 relation map 未覆盖 policy | REJECT | REJECT ✓ | `test_v4::test_policy_non_empty_but_not_covered_by_map` |
| 20 | relaxation 全局存在但不属于所选 policy | REJECT | REJECT ✓ | `test_v3::test_relaxation_not_under_selected_policy_rejected` |

---

## 5. Changed files（§15.7）

| 文件 | 改动类型 | 作用 |
|------|----------|------|
| `tests/contracts/test_v4_fail_closed_context.py` | NEW | 20 个 fail-closed 测试（15 neg + 5 pos） |
| `reaction_agent/schemas/hypothesis.py` | MODIFIED | 6 处 fail-closed 修复（registry model_validator、ProductionSelection 规则 1-13、relaxation 不变量、三态 query、target fail-closed、docstrings） |
| `tests/contracts/test_hypothesis_lanes.py` | MODIFIED | 1 处正例补全 lineage 链（`test_reference_validation_passes_with_known_ids`，未删/弱化任何断言） |
| `scripts/run_p0_gate.py` | MODIFIED | G03 完整链正例 + 5 核心负例；`p1_status` → round-4；删除 §11.1 opt-in 措辞 |
| `scripts/reproduce_v3_false_positives.py` | MODIFIED | 新增反例 c9-c12（§3.2 A/B/C + §3.3），计数 8→12 |
| `reports/p0/P0_GATE_REPORT.md` | REGENERATED | 由 gate 重新生成：fail-closed assumptions/risks、round-4、G03 fail-closed evidence |
| `reports/p0/P0_GATE_REPORT.json` | REGENERATED | 由 gate 重新生成：`p1_status` / `assumptions` / `known_risks` / `deviations` 均 fail-closed |
| `reports/p0/V4_REMEDIATION_WORKLOG.md` | NEW | §11.3 工作日志 + §13 行为矩阵 |

**未触碰：** `errors.py`、`schemas/__init__.py`、`plan/final_*.md`、所有 ADR、`schemas/json/*.json`、其他 schema 文件、rank/candidate/retrieval/mapping 等 P1 内容。

---

## 6. §14 完成标准自检

| # | 完成标准 | 实际状态 | 证据 |
|---|----------|----------|------|
| 1 | 新 fail-closed 测试先 RED、修复后 GREEN | ✅ | Task1 RED: 15 failed/5 passed; Task2 GREEN: 20/20 passed |
| 2 | ProductionSelection 当前引用链缺失任何 relation 都会拒绝 | ✅ | hypothesis.py L254/263/275 (missing mapping → error); matrix #2,3,5,7 |
| 3 | 各 ID 分别存在但关系未知时不会被生产接纳 | ✅ | matrix #2; reproduce c9; gate neg1 |
| 4 | Registry relation key/value 内部一致 | ✅ | model_validator L135-168; matrix #9; reproduce c12; gate neg5 |
| 5 | AgentProposed 缺少 query context 时拒绝 | ✅ | hypothesis.py L344; matrix #12; reproduce c10; gate neg3 |
| 6 | 能区分 query context omitted 与 explicit-empty | ✅ | 三态字段 L322-325; P4 `test_explicit_empty_bond_set_accepted` ACCEPT + neg7 `None` REJECT |
| 7 | relaxation 非空时必须有有效 policy | ✅ | hypothesis.py L288; matrix #17; reproduce c11; gate neg4 |
| 8 | policy relation 缺失时拒绝 | ✅ | hypothesis.py L294; matrix #19 |
| 9 | 原有 8 个 false positives 继续 8/8 REJECTED | ✅ | reproduce c1-c8 all REJECTED |
| 10 | 新行为矩阵全部符合预期 | ✅ | 20/20 match (§4 above) |
| 11 | targeted tests 全绿 | ✅ | 45 passed |
| 12 | full contract tests 全绿 | ✅ | 290 passed |
| 13 | 零 fail/error/skip/xfail/xpass | ✅ | G10 stats: all 0 |
| 14 | JSON Schema fresh | ✅ | G10: 12/12 fresh |
| 15 | Gate 10/10 PASS | ✅ | 10/10, exit 0 |
| 16 | Gate 失败时仍返回非零退出码 | ✅ | `main(): return 0 if all_passed else 1` |
| 17 | 报告不再把 relation validation 描述为 opt-in | ✅ | §11.1 banned phrases grep empty; assumptions/risks fail-closed |
| 18 | P1 仍标记 BLOCKED，等待 ChatGPT 审核 | ✅ | `p1_status: round-4 BLOCKED` |
| 19 | 未执行 git 写操作 | ✅ | 无 add/commit/push/reset/clean; HEAD 仍 f4fedc4 |
| 20 | 未删除、移动或覆盖用户文件 | ✅ | 见 §7 声明 |
| 21 | 未修改权威设计来迁就实现 | ✅ | plan/final_*.md、ADR 全未触碰 |

---

## 7. 声明

- **P1 remains BLOCKED, awaiting ChatGPT round-4 read-only audit.** Gate 10/10 只是提交 ChatGPT 复核的前置条件，不代表 P0 最终通过，更不代表可以进入 P1。
- **No git add/commit/push/reset/clean executed.** 仅 read-only `git status` 用于核对范围。HEAD 仍为 `f4fedc4`，所有改动留在 working tree（文件未 tracked）。
- **No user files deleted, moved, or overwritten.** 本轮仅创建/修改 §5 所列 8 个文件。
- **No authoritative design modified to accommodate the implementation.** `plan/final_design.md`、`plan/final_plan.md`、`plan/final_discussion.md`、所有 ADR 均未修改；fail-closed 语义实现以匹配既有 spec，未弱化任何设计。
- **未进入或实现 P1。** 未改 rank、candidate generation、retrieval、mapping 算法等 P1 内容。
- **未用 skip/xfail/xpass 掩盖失败，未删除/弱化现有测试。** 唯一的现有测试改动是 `test_hypothesis_lanes.py` 一处正例补全 lineage 链（反映更严格的新合同，非弱化）。

---

## 8. 审核请求

请按 spec §14 的 21 项完成标准进行第四轮只读审核，重点核对：

1. **fail-closed 真实性** — `hypothesis.py` 中是否存在任何"missing evidence → acceptance"的残留路径（两个 lane + registry 构造）。
2. **行为矩阵** — §4 的 20 项实际结果是否全部匹配预期，证据是否可追溯。
3. **报告口径** — `P0_GATE_REPORT.md/.json` 是否仍含 §11.1 禁用措辞（opt-in / empty-map registry cannot detect / caller must supply context / silently passes）。
4. **范围合规** — 是否触碰 git 写操作、权威设计、P1 内容。

**提交状态：`READY_FOR_CHATGPT_ROUND_4_AUDIT`**
**P1：`BLOCKED pending ChatGPT audit`**
