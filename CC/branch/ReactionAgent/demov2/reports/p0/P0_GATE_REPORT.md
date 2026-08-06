# P0 Gate Report v3

**Timestamp (UTC):** 2026-08-06T09:12:01.190087+00:00
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
**Evidence:** stats fail: {'collected': 992, 'passed': 966, 'failed': 4, 'errors': 0, 'skipped': 0, 'xfailed': 0, 'xpassed': 0} (exit=1)
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

- `M` CC/branch/ReactionAgent/demov2/docs/manual_audit_protocol.md
- `M` CC/branch/ReactionAgent/demov2/reaction_agent/eligibility/engine.py
- `M` CC/branch/ReactionAgent/demov2/reaction_agent/lineage/__init__.py
- `M` CC/branch/ReactionAgent/demov2/reaction_agent/mapping/adapter.py
- `M` CC/branch/ReactionAgent/demov2/reaction_agent/snapshot/builder.py
- `M` CC/branch/ReactionAgent/demov2/reaction_agent/snapshot/loader.py
- `M` CC/branch/ReactionAgent/demov2/reports/data_audit/legacy_lineage_audit.json
- `M` CC/branch/ReactionAgent/demov2/reports/data_audit/legacy_lineage_audit.md
- `M` CC/branch/ReactionAgent/demov2/reports/p0/P0_GATE_REPORT.json
- `M` CC/branch/ReactionAgent/demov2/reports/p0/P0_GATE_REPORT.md
- `M` CC/branch/ReactionAgent/demov2/reports/p1/P1_GATE_REPORT.json
- `M` CC/branch/ReactionAgent/demov2/reports/p1/P1_GATE_REPORT.md
- `M` CC/branch/ReactionAgent/demov2/reports/p1/P1_PREFLIGHT.json
- `M` CC/branch/ReactionAgent/demov2/reports/p1/P1_PREFLIGHT.md
- `M` CC/branch/ReactionAgent/demov2/reports/p1/P1_REMEDIATION_WORKLOG.md
- `M` CC/branch/ReactionAgent/demov2/reports/p1/lineage_regression_cases.json
- `M` CC/branch/ReactionAgent/demov2/reports/p1/manual_audit_report.json
- `M` CC/branch/ReactionAgent/demov2/reports/p1/manual_audit_report.md
- `M` CC/branch/ReactionAgent/demov2/reports/p1/manual_audit_sample_manifest.json
- `M` CC/branch/ReactionAgent/demov2/reports/p1/mapping_integration_sample.json
- `M` CC/branch/ReactionAgent/demov2/reports/p1/mutation_results.json
- `M` CC/branch/ReactionAgent/demov2/reports/p1/snapshot_build_sample.json
- `M` CC/branch/ReactionAgent/demov2/requirements.lock.txt
- `M` CC/branch/ReactionAgent/demov2/scripts/legacy_lineage_audit.py
- `M` CC/branch/ReactionAgent/demov2/scripts/p1_preflight.py
- `M` CC/branch/ReactionAgent/demov2/scripts/run_p1_gate.py
- `M` CC/branch/ReactionAgent/demov2/scripts/run_p1_mutations.py
- `M` CC/branch/ReactionAgent/demov2/tests/p1/test_eligibility_engine.py
- `M` CC/branch/ReactionAgent/demov2/tests/p1/test_legacy_audit_contract.py
- `M` CC/branch/ReactionAgent/demov2/tests/p1/test_lineage_graph.py
- `M` CC/branch/ReactionAgent/demov2/tests/p1/test_manual_audit_contract.py
- `M` CC/branch/ReactionAgent/demov2/tests/p1/test_mapping_adapter.py
- `M` CC/branch/ReactionAgent/demov2/tests/p1/test_p1_preflight.py
- `M` CC/branch/ReactionAgent/demov2/tests/p1/test_snapshot_builder.py
- `??` CC/branch/ReactionAgent/demov2/docs/orchestra/
- `??` CC/branch/ReactionAgent/demov2/plan/P6_ISSUE_TEMPLATE.md
- `??` CC/branch/ReactionAgent/demov2/plan/chatgpt-user-collaboration-style.md
- `??` CC/branch/ReactionAgent/demov2/reaction_agent/lineage/required_case.py
- `??` CC/branch/ReactionAgent/demov2/reaction_agent/p5/
- `??` CC/branch/ReactionAgent/demov2/reports/p1/CHATGPT_P1_REMEDIATION_PROMPT_ROUND_2.md
- `??` CC/branch/ReactionAgent/demov2/reports/p1/CHATGPT_P1_REMEDIATION_PROMPT_ROUND_3.md
- `??` CC/branch/ReactionAgent/demov2/reports/p1/CHATGPT_P1_REMEDIATION_PROMPT_ROUND_4_FOR_CLAUDE.md
- `??` CC/branch/ReactionAgent/demov2/reports/p1/CHATGPT_P1_REMEDIATION_PROMPT_ROUND_5.md
- `??` CC/branch/ReactionAgent/demov2/reports/p1/CHATGPT_P1_REMEDIATION_PROMPT_ROUND_6.md
- `??` CC/branch/ReactionAgent/demov2/reports/p1/CHATGPT_P1_REMEDIATION_PROMPT_ROUND_7.md
- `??` CC/branch/ReactionAgent/demov2/reports/p1/CHATGPT_P1_REMEDIATION_PROMPT_ROUND_8.md
- `??` CC/branch/ReactionAgent/demov2/reports/p1/CHATGPT_P1_REMEDIATION_PROMPT_ROUND_9.md
- `??` CC/branch/ReactionAgent/demov2/reports/p1/CHATGPT_P1_ROUND_10_TASK_A_MANIFEST_CORE.md
- `??` CC/branch/ReactionAgent/demov2/reports/p1/CHATGPT_P1_ROUND_10_TASK_B_GATE_MUTATIONS.md
- `??` CC/branch/ReactionAgent/demov2/reports/p1/CHATGPT_P1_ROUND_10_TASK_C_INTEGRATION_AUDIT.md
- `??` CC/branch/ReactionAgent/demov2/reports/p1/P1_ROUND_10_AUDIT_EVIDENCE.json
- `??` CC/branch/ReactionAgent/demov2/reports/p1/P1_ROUND_2_AUDIT_EVIDENCE.json
- `??` CC/branch/ReactionAgent/demov2/reports/p1/P1_ROUND_3_AUDIT_EVIDENCE.json
- `??` CC/branch/ReactionAgent/demov2/reports/p1/P1_ROUND_4_AUDIT_EVIDENCE.json
- `??` CC/branch/ReactionAgent/demov2/reports/p1/P1_ROUND_5_AUDIT_EVIDENCE.json
- `??` CC/branch/ReactionAgent/demov2/reports/p1/P1_ROUND_6_AUDIT_EVIDENCE.json
- `??` CC/branch/ReactionAgent/demov2/reports/p1/P1_ROUND_7_AUDIT_EVIDENCE.json
- `??` CC/branch/ReactionAgent/demov2/reports/p1/P1_ROUND_8_AUDIT_EVIDENCE.json
- `??` CC/branch/ReactionAgent/demov2/reports/p1/P1_ROUND_9_AUDIT_EVIDENCE.json
- `??` CC/branch/ReactionAgent/demov2/reports/p1/ROUND_10_INTEGRATION_RESULTS.json
- `??` CC/branch/ReactionAgent/demov2/reports/p1/ROUND_10_TASK_A_HANDOFF.md
- `??` CC/branch/ReactionAgent/demov2/reports/p1/ROUND_10_TASK_B_HANDOFF.md
- `??` CC/branch/ReactionAgent/demov2/reports/p1/SUBMISSION_TO_CHATGPT_P1_FINAL_PASS.md
- `??` CC/branch/ReactionAgent/demov2/reports/p1/SUBMISSION_TO_CHATGPT_P1_ROUND_10.md
- `??` CC/branch/ReactionAgent/demov2/reports/p1/SUBMISSION_TO_CHATGPT_P1_ROUND_2.md
- `??` CC/branch/ReactionAgent/demov2/reports/p1/SUBMISSION_TO_CHATGPT_P1_ROUND_3.md
- `??` CC/branch/ReactionAgent/demov2/reports/p1/SUBMISSION_TO_CHATGPT_P1_ROUND_4.md
- `??` CC/branch/ReactionAgent/demov2/reports/p1/SUBMISSION_TO_CHATGPT_P1_ROUND_5.md
- `??` CC/branch/ReactionAgent/demov2/reports/p1/SUBMISSION_TO_CHATGPT_P1_ROUND_6.md
- `??` CC/branch/ReactionAgent/demov2/reports/p1/SUBMISSION_TO_CHATGPT_P1_ROUND_7.md
- `??` CC/branch/ReactionAgent/demov2/reports/p1/SUBMISSION_TO_CHATGPT_P1_ROUND_8.md
- `??` CC/branch/ReactionAgent/demov2/reports/p1/SUBMISSION_TO_CHATGPT_P1_ROUND_9.md
- `??` CC/branch/ReactionAgent/demov2/reports/p1/eligibility_cross_invariant_results.json
- `??` CC/branch/ReactionAgent/demov2/reports/p1/eligibility_fail_closed_results.json
- `??` CC/branch/ReactionAgent/demov2/reports/p1/eligibility_reference_integrity_results_round_5.json
- `??` CC/branch/ReactionAgent/demov2/reports/p1/eligibility_reference_integrity_results_round_6.json
- `??` CC/branch/ReactionAgent/demov2/reports/p1/eligibility_reference_integrity_results_round_7.json
- `??` CC/branch/ReactionAgent/demov2/reports/p1/eligibility_semantic_invariant_results_round_4.json
- `??` CC/branch/ReactionAgent/demov2/reports/p1/eligibility_semantic_invariant_results_round_5.json
- `??` CC/branch/ReactionAgent/demov2/reports/p1/eligibility_semantic_invariant_results_round_6.json
- `??` CC/branch/ReactionAgent/demov2/reports/p1/eligibility_semantic_invariant_results_round_7.json
- `??` CC/branch/ReactionAgent/demov2/reports/p1/g10_round_1/
- `??` CC/branch/ReactionAgent/demov2/reports/p1/g10_round_2/
- `??` CC/branch/ReactionAgent/demov2/reports/p1/g10_round_3/
- `??` CC/branch/ReactionAgent/demov2/reports/p1/gate_false_positive_mutation_results.json
- `??` CC/branch/ReactionAgent/demov2/reports/p1/gate_false_positive_mutation_results_round_10.json
- `??` CC/branch/ReactionAgent/demov2/reports/p1/gate_false_positive_mutation_results_round_3.json
- `??` CC/branch/ReactionAgent/demov2/reports/p1/gate_false_positive_mutation_results_round_4.json
- `??` CC/branch/ReactionAgent/demov2/reports/p1/gate_false_positive_mutation_results_round_5.json
- `??` CC/branch/ReactionAgent/demov2/reports/p1/gate_false_positive_mutation_results_round_6.json
- `??` CC/branch/ReactionAgent/demov2/reports/p1/gate_false_positive_mutation_results_round_7.json
- `??` CC/branch/ReactionAgent/demov2/reports/p1/gate_false_positive_mutation_results_round_8.json
- `??` CC/branch/ReactionAgent/demov2/reports/p1/gate_false_positive_mutation_results_round_9.json
- `??` CC/branch/ReactionAgent/demov2/reports/p1/index_partition_integrity_results_round_8.json
- `??` CC/branch/ReactionAgent/demov2/reports/p1/manifest_authority_integrity_results_round_9.json
- `??` CC/branch/ReactionAgent/demov2/reports/p1/manifest_type_authority_results_round_10.json
- `??` CC/branch/ReactionAgent/demov2/reports/p1/manual_audit_adjudication.json
- `??` CC/branch/ReactionAgent/demov2/reports/p1/manual_audit_annotations_a.json
- `??` CC/branch/ReactionAgent/demov2/reports/p1/manual_audit_annotations_b.json
- `??` CC/branch/ReactionAgent/demov2/reports/p1/manual_audit_evidence_packet.json
- `??` CC/branch/ReactionAgent/demov2/reports/p1/required_case_quarantine_evidence.json
- `??` CC/branch/ReactionAgent/demov2/reports/p1/snapshot_complete_evidence_mutation_results.json
- `??` CC/branch/ReactionAgent/demov2/reports/p1/snapshot_nested_mutation_results.json
- `??` CC/branch/ReactionAgent/demov2/reports/p3/
- `??` CC/branch/ReactionAgent/demov2/reports/p4/
- `??` CC/branch/ReactionAgent/demov2/reports/p5/
- `??` CC/branch/ReactionAgent/demov2/scripts/finalize_manual_audit.py
- `??` CC/branch/ReactionAgent/demov2/scripts/generate_manual_audit_manifest.py
- `??` CC/branch/ReactionAgent/demov2/scripts/generate_manual_audit_packet.py
- `??` CC/branch/ReactionAgent/demov2/scripts/generate_required_case_quarantine_evidence.py
- `??` CC/branch/ReactionAgent/demov2/scripts/generate_round3_evidence.py
- `??` CC/branch/ReactionAgent/demov2/scripts/regenerate_snapshot_sample.py
- `??` CC/branch/ReactionAgent/demov2/scripts/run_kimi_audit.py
- `??` CC/branch/ReactionAgent/demov2/scripts/run_kimi_remediate.py
- `??` CC/branch/ReactionAgent/demov2/scripts/run_p5_audit_evidence.py
- `??` CC/branch/ReactionAgent/demov2/scripts/run_p5_gate.py
- `??` CC/branch/ReactionAgent/demov2/scripts/run_p5_packet_selfcheck.py
- `??` CC/branch/ReactionAgent/demov2/scripts/validate_manual_annotations.py
- `??` CC/branch/ReactionAgent/demov2/tests/p1/test_eligibility_cross_invariants.py
- `??` CC/branch/ReactionAgent/demov2/tests/p1/test_eligibility_fail_closed.py
- `??` CC/branch/ReactionAgent/demov2/tests/p1/test_eligibility_reference_integrity.py
- `??` CC/branch/ReactionAgent/demov2/tests/p1/test_manifest_authority_type_integrity.py
- `??` CC/branch/ReactionAgent/demov2/tests/p1/test_required_case_quarantine.py
- `??` CC/branch/ReactionAgent/demov2/tests/p1/test_snapshot_complete_evidence.py
- `??` CC/branch/ReactionAgent/demov2/tests/p1/test_snapshot_nested_evidence.py
- `??` CC/branch/ReactionAgent/demov2/tests/p5/
- `??` CC/branch/ReactionAgent/demov2/training/CHATGPT_P2_IMPLEMENTATION_PROMPT_2026-08-02.md
- `??` CC/branch/ReactionAgent/demov2/training/CHATGPT_P3_IMPLEMENTATION_PROMPT_2026-08-03.md
- `??` CC/branch/ReactionAgent/demov2/training/CHATGPT_P3_REMEDIATION_PROMPT_ROUND_2_2026-08-03.md
- `??` CC/branch/ReactionAgent/demov2/training/CHATGPT_P4_IMPLEMENTATION_PROMPT_2026-08-03.md
- `??` CC/branch/ReactionAgent/demov2/training/CHATGPT_P5_IMPLEMENTATION_PROMPT_2026-08-03.md
- `??` CC/branch/ReactionAgent/demov2/training/COPY_PROMPT_P3_REMEDIATION_ROUND_2_TO_AI.md
- `??` CC/branch/ReactionAgent/demov2/training/COPY_PROMPT_P3_TO_AI.md
- `??` CC/branch/ReactionAgent/demov2/training/COPY_PROMPT_P4_TO_AI.md
- `??` CC/branch/ReactionAgent/demov2/training/COPY_PROMPT_P5_TO_AI.md
- `??` CC/branch/ReactionAgent/demov2/training/chatgpt_parallel_p2_p5_fresh_window_prompt.md

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

- P0-G10: stats fail: {'collected': 992, 'passed': 966, 'failed': 4, 'errors': 0, 'skipped': 0, 'xfailed': 0, 'xpassed': 0} (exit=1)