# P0 Gate Report v3

**Timestamp (UTC):** 2026-08-06T11:07:22.578002+00:00
**Working directory:** /Volumes/CC/Enzyme_Agent/depending/.claude/worktrees/p6-mcp-kernel/CC/branch/ReactionAgent/demov2
**Python:** 3.11.15 (required >=3.11, satisfied=True)
**Pydantic:** 2.13.4 (required >=2.8,<3, satisfied=True)
**pytest:** 9.1.1 (required >=8.0, satisfied=True)

## Result: NOT_READY_FOR_CHATGPT_AUDIT

**Passed:** 9 / 10
**Failed:** 1 / 10

## Gate Checks

### P0-G01: Six ADRs complete and approved
**Status:** ✅ PASS
**Evidence:** 6/6 approved
**ADR:** docs/decisions/ADR-0001..ADR-0006 | **Schema:** - | **Policy:** - | **Tests:** test_authority_contract.py::test_adr_status_is_approved

### P0-G02: Authority consistency (README + ADR-0001)
**Status:** ✅ PASS
**Evidence:** consistent
**ADR:** ADR-0001-authority-and-scope.md | **Schema:** - | **Policy:** - | **Tests:** test_v3_authority_drift.py, test_authority_contract.py

### P0-G03: Hypothesis lanes + relation validation
**Status:** ✅ PASS
**Evidence:** lanes + fail-closed relations verified (1 positive, 5+ negatives)
**ADR:** ADR-0002-hypothesis-lanes.md | **Schema:** schemas/hypothesis.py | **Policy:** - | **Tests:** test_v3_hypothesis_relations.py, test_hypothesis_lanes.py

### P0-G04: Dual ledger boundary
**Status:** ✅ PASS
**Evidence:** dual ledgers verified
**ADR:** ADR-0003-ledger-and-source-semantics.md | **Schema:** schemas/ledger.py | **Policy:** - | **Tests:** test_v3_hypothesis_relations.py, test_ledger_contracts.py

### P0-G05: Eligibility policy + ADR drift check
**Status:** ✅ PASS
**Evidence:** 8 rows + ADR/policy consistent
**ADR:** ADR-0004-partial-eligibility.md | **Schema:** schemas/common.py | **Policy:** policies/partial_eligibility.py | **Tests:** test_v3_policy_drift.py, test_partial_eligibility_contract.py

### P0-G06: Mapping/mechanism consistency
**Status:** ✅ PASS
**Evidence:** mapping consistency verified
**ADR:** ADR-0003-ledger-and-source-semantics.md | **Schema:** schemas/mapping.py | **Policy:** - | **Tests:** test_v3_mapping_consistency.py, test_ledger_contracts.py

### P0-G07: Decision state machine + recursive forbidden scan
**Status:** ✅ PASS
**Evidence:** state machine + recursive scan OK
**ADR:** ADR-0005-scientific-decision-authority.md | **Schema:** schemas/result.py, common.py | **Policy:** - | **Tests:** test_v3_assumption_confidence.py, test_result_invariants.py

### P0-G08: MCP side-effect policy
**Status:** ✅ PASS
**Evidence:** 5 tools, 3 idem, 4 invariants
**ADR:** ADR-0006-mcp-side-effects.md | **Schema:** - | **Policy:** contracts/mcp_side_effects.py | **Tests:** test_mcp_side_effect_contract.py

### P0-G09: Legacy metrics provisional
**Status:** ✅ PASS
**Evidence:** README=yes, ADR=yes
**ADR:** ADR-0001-authority-and-scope.md | **Schema:** - | **Policy:** - | **Tests:** test_authority_contract.py

### P0-G10: Contract tests + JSON freshness + env
**Status:** ❌ FAIL
**Evidence:** stats fail: {'collected': 1138, 'passed': 1112, 'failed': 1, 'errors': 0, 'skipped': 25, 'xfailed': 0, 'xpassed': 0} (exit=1)
**ADR:** ADR-0001..ADR-0006 | **Schema:** schemas/json/*.json | **Policy:** - | **Tests:** all tests/contracts/*.py

## Authority Files

- `plan/final_design.md`: exists
- `plan/final_discussion.md`: exists
- `plan/final_plan.md`: exists

## ADRs

- `ADR-0001-authority-and-scope.md`: exists
- `ADR-0002-hypothesis-lanes.md`: exists
- `ADR-0003-ledger-and-source-semantics.md`: exists
- `ADR-0004-partial-eligibility.md`: exists
- `ADR-0005-scientific-decision-authority.md`: exists
- `ADR-0006-mcp-side-effects.md`: exists

## Changed Files (git status, demov2)

- `M` CC/branch/ReactionAgent/demov2/reports/p0/P0_GATE_REPORT.json
- `M` CC/branch/ReactionAgent/demov2/reports/p0/P0_GATE_REPORT.md
- `M` CC/branch/ReactionAgent/demov2/reports/p1/P1_GATE_REPORT.json
- `M` CC/branch/ReactionAgent/demov2/reports/p1/P1_GATE_REPORT.md

## Deviations / Assumptions / Risks

- **Deviations:** none
- **Assumptions:**
  - venv (.venv) is the supported environment; system anaconda pytest 7.4.0 is below spec and is NOT used to run the Gate
  - Relation validation is fail-closed: missing relation evidence is a rejection, not a skip
- **Known risks:**
  - None: validation is fail-closed; missing relation evidence rejects the hypothesis

## User Files Protection

No user files deleted, moved, or overwritten. Historical plan/*.md docs received a prepend-only HISTORICAL banner (original content preserved). All writes confined to demov2/. No git add/commit/push/reset/clean executed.

## P1 Status

BLOCKED — P0 only, awaiting ChatGPT round-4 read-only audit

## Conclusion

**NOT_READY_FOR_CHATGPT_AUDIT**

### Blocking items:

- P0-G10: stats fail: {'collected': 1138, 'passed': 1112, 'failed': 1, 'errors': 0, 'skipped': 25, 'xfailed': 0, 'xpassed': 0} (exit=1)