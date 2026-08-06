# Submission to ChatGPT — P3 Round 7 (directed remediation)

- generated_at: 2026-08-04T08:54:46Z
- worktree: /Users/frank_gong/Documents/Codex/2026-08-03/ReactionAgent-p3-strict-kernel/CC/branch/ReactionAgent/demov2
- branch: **codex/p3-strict-kernel**
- head: **24e6b03b1c16c1f6e40b7add076b41184818cd88**
- git_status:
```text
 M docs/manual_audit_protocol.md
 M reaction_agent/eligibility/engine.py
 M reaction_agent/lineage/__init__.py
 M reaction_agent/mapping/adapter.py
 M reaction_agent/snapshot/builder.py
 M reaction_agent/snapshot/loader.py
 M reports/data_audit/legacy_lineage_audit.json
 M reports/data_audit/legacy_lineage_audit.md
 M reports/p0/P0_GATE_REPORT.json
 M reports/p0/P0_GATE_REPORT.md
 M reports/p1/P1_GATE_REPORT.json
 M reports/p1/P1_GATE_REPORT.md
 M reports/p1/P1_PREFLIGHT.json
 M reports/p1/P1_PREFLIGHT.md
 M reports/p1/P1_REMEDIATION_WORKLOG.md
 M reports/p1/lineage_regression_cases.json
 M reports/p1/manual_audit_report.json
 M reports/p1/manual_audit_report.md
 M reports/p1/manual_audit_sample_manifest.json
 M reports/p1/mapping_integration_sample.json
 M reports/p1/mutation_results.json
 M reports/p1/snapshot_build_sample.json
 M reports/p3/P3_ROUND_7_AUDIT_EVIDENCE.json
 M requirements.lock.txt
 M scripts/legacy_lineage_audit.py
 M scripts/p1_preflight.py
 M scripts/run_p1_gate.py
 M scripts/run_p1_mutations.py
 M tests/p1/test_eligibility_engine.py
 M tests/p1/test_legacy_audit_contract.py
 M tests/p1/test_lineage_graph.py
 M tests/p1/test_manual_audit_contract.py
 M tests/p1/test_mapping_adapter.py
 M tests/p1/test_p1_preflight.py
 M tests/p1/test_snapshot_builder.py
?? ../benchmark/
?? ../core/
?? docs/orchestra/
?? reaction_agent/lineage/required_case.py
?? reaction_agent/p5/
?? reports/p1/CHATGPT_P1_REMEDIATION_PROMPT_ROUND_2.md
?? reports/p1/CHATGPT_P1_REMEDIATION_PROMPT_ROUND_3.md
?? reports/p1/CHATGPT_P1_REMEDIATION_PROMPT_ROUND_4_FOR_CLAUDE.md
?? reports/p1/CHATGPT_P1_REMEDIATION_PROMPT_ROUND_5.md
?? reports/p1/CHATGPT_P1_REMEDIATION_PROMPT_ROUND_6.md
?? reports/p1/CHATGPT_P1_REMEDIATION_PROMPT_ROUND_7.md
?? reports/p1/CHATGPT_P1_REMEDIATION_PROMPT_ROUND_8.md
?? reports/p1/CHATGPT_P1_REMEDIATION_PROMPT_ROUND_9.md
?? reports/p1/CHATGPT_P1_ROUND_10_TASK_A_MANIFEST_CORE.md
?? reports/p1/CHATGPT_P1_ROUND_10_TASK_B_GATE_MUTATIONS.md
?? reports/p1/CHATGPT_P1_ROUND_10_TASK_C_INTEGRATION_AUDIT.md
?? reports/p1/P1_ROUND_10_AUDIT_EVIDENCE.json
?? reports/p1/P1_ROUND_2_AUDIT_EVIDENCE.json
?? reports/p1/P1_ROUND_3_AUDIT_EVIDENCE.json
?? reports/p1/P1_ROUND_4_AUDIT_EVIDENCE.json
?? reports/p1/P1_ROUND_5_AUDIT_EVIDENCE.json
?? reports/p1/P1_ROUND_6_AUDIT_EVIDENCE.json
?? reports/p1/P1_ROUND_7_AUDIT_EVIDENCE.json
?? reports/p1/P1_ROUND_8_AUDIT_EVIDENCE.json
?? reports/p1/P1_ROUND_9_AUDIT_EVIDENCE.json
?? reports/p1/ROUND_10_INTEGRATION_RESULTS.json
?? reports/p1/ROUND_10_TASK_A_HANDOFF.md
?? reports/p1/ROUND_10_TASK_B_HANDOFF.md
?? reports/p1/SUBMISSION_TO_CHATGPT_P1_FINAL_PASS.md
?? reports/p1/SUBMISSION_TO_CHATGPT_P1_ROUND_10.md
?? reports/p1/SUBMISSION_TO_CHATGPT_P1_ROUND_2.md
?? reports/p1/SUBMISSION_TO_CHATGPT_P1_ROUND_3.md
?? reports/p1/SUBMISSION_TO_CHATGPT_P1_ROUND_4.md
?? reports/p1/SUBMISSION_TO_CHATGPT_P1_ROUND_5.md
?? reports/p1/SUBMISSION_TO_CHATGPT_P1_ROUND_6.md
?? reports/p1/SUBMISSION_TO_CHATGPT_P1_ROUND_7.md
?? reports/p1/SUBMISSION_TO_CHATGPT_P1_ROUND_8.md
?? reports/p1/SUBMISSION_TO_CHATGPT_P1_ROUND_9.md
?? reports/p1/eligibility_cross_invariant_results.json
?? reports/p1/eligibility_fail_closed_results.json
?? reports/p1/eligibility_reference_integrity_results_round_5.json
?? reports/p1/eligibility_reference_integrity_results_round_6.json
?? reports/p1/eligibility_reference_integrity_results_round_7.json
?? reports/p1/eligibility_semantic_invariant_results_round_4.json
?? reports/p1/eligibility_semantic_invariant_results_round_5.json
?? reports/p1/eligibility_semantic_invariant_results_round_6.json
?? reports/p1/eligibility_semantic_invariant_results_round_7.json
?? reports/p1/g10_round_1/
?? reports/p1/g10_round_2/
?? reports/p1/g10_round_3/
?? reports/p1/gate_false_positive_mutation_results.json
?? reports/p1/gate_false_positive_mutation_results_round_10.json
?? reports/p1/gate_false_positive_mutation_results_round_3.json
?? reports/p1/gate_false_positive_mutation_results_round_4.json
?? reports/p1/gate_false_positive_mutation_results_round_5.json
?? reports/p1/gate_false_positive_mutation_results_round_6.json
?? reports/p1/gate_false_positive_mutation_results_round_7.json
?? reports/p1/gate_false_positive_mutation_results_round_8.json
?? reports/p1/gate_false_positive_mutation_results_round_9.json
?? reports/p1/index_partition_integrity_results_round_8.json
?? reports/p1/manifest_authority_integrity_results_round_9.json
?? reports/p1/manifest_type_authority_results_round_10.json
?? reports/p1/manual_audit_adjudication.json
?? reports/p1/manual_audit_annotations_a.json
?? reports/p1/manual_audit_annotations_b.json
?? reports/p1/manual_audit_evidence_packet.json
?? reports/p1/required_case_quarantine_evidence.json
?? reports/p1/snapshot_complete_evidence_mutation_results.json
?? reports/p1/snapshot_nested_mutation_results.json
?? scripts/finalize_manual_audit.py
?? scripts/generate_manual_audit_manifest.py
?? scripts/generate_manual_audit_packet.py
?? scripts/generate_required_case_quarantine_evidence.py
?? scripts/regenerate_snapshot_sample.py
?? scripts/validate_manual_annotations.py
?? tests/p1/test_eligibility_cross_invariants.py
?? tests/p1/test_eligibility_fail_closed.py
?? tests/p1/test_eligibility_reference_integrity.py
?? tests/p1/test_manifest_authority_type_integrity.py
?? tests/p1/test_required_case_quarantine.py
?? tests/p1/test_snapshot_complete_evidence.py
?? tests/p1/test_snapshot_nested_evidence.py
?? training/CHATGPT_P2_IMPLEMENTATION_PROMPT_2026-08-02.md
?? training/CHATGPT_P3_IMPLEMENTATION_PROMPT_2026-08-03.md
?? training/CHATGPT_P4_IMPLEMENTATION_PROMPT_2026-08-03.md
?? training/CHATGPT_P5_IMPLEMENTATION_PROMPT_2026-08-03.md
?? training/COPY_PROMPT_P3_TO_AI.md
?? training/COPY_PROMPT_P4_TO_AI.md
?? training/COPY_PROMPT_P5_TO_AI.md
?? training/chatgpt_parallel_p2_p5_fresh_window_prompt.md

```

- implementation_commit: **b853f7b**
- implementation_commit_parent: **a0fffdb2c126473c5879f68757c4c5dab13e68e5**
- deliverables_commit: **24e6b03**
- audit_target_head: **24e6b03b1c16c1f6e40b7add076b41184818cd88**

## Final status

```text
P3_ROUND_7_READY_FOR_CHATGPT_READ_ONLY_AUDIT_P4_BLOCKED
```

## Summary

Round 7 fixes exactly the two NOT-CLOSED contracts from the ChatGPT Round 6 audit: **R7-A** (execution authority now covers mutations — a fully-synchronized raw+typed receipt rewrite is rejected) and **R7-B** (fixture authority and production authority are TYPE-isolated — a caller-built fixture root can never be relabeled or accepted as a production authority).  R6-A / R6-B / R6-C remain closed; all R6 regression tests pass; tests/p3 passes; the full suite passes; P0 Gate exit 0; P1 Gate exit 0; P3 Gate stays honestly BLOCKED (exit 2) because real evidence resources are still missing — P4 remains BLOCKED.

## R7-A — execution authority covers mutations

**Original attack (RED)**: rewriting the raw marker-delimited receipt AND the typed fields AND the artifact hash AND the stdout hash together (fully self-consistent) produced `verified=True, BLOCKED` with no machinery failures — the R6-A authority only bound the Gate items, not the mutations.

**GREEN command**: `python -m pytest tests/p3/test_r7a_mutation_execution_authority.py -q`
- green exit_code: 0
- green: 7 passed, 0 failed

**Code**: `reaction_agent/p3/gate.py` — `GateExecutionAuthority` binds the EXECUTED items AND the EXECUTED mutation results; the authority is registered AFTER the mutation suite completes; `evaluate_gate_artifact()` exact-matches the submitted mutations against the executed mutations (count / order / full record).
**Tests**: `tests/p3/test_r7a_mutation_execution_authority.py` (7 tests, incl. `test_simultaneous_raw_and_typed_receipt_rewrite_fails_against_execution_authority`).
**Invariants**: (1) missing / extra / duplicate mutations fail (`EXECUTED_MUTATION_COUNT_MISMATCH`); (2) order substitution fails (`EXECUTED_MUTATION_ORDER_MISMATCH`); (3) any full-record rewrite fails (`EXECUTED_MUTATION_MISMATCH`); (4) the mutation verdict / caught / valid / observed code are derived from the executed mutations.
**Residual risk**: within one process the authority is in-memory (keyed by run_id); a fresh process cannot verify a stored artifact (by design).

## R7-B — fixture/production authority type isolation

**Original attack (RED)**: relabeling a caller-built fixture root `kind=production` + changing provenance + recomputing the public self-hash made the production loader accept it (`accepted=true, root_kind=production`).

**GREEN command**: `python -m pytest tests/p3/test_r7b_fixture_production_authority_isolation.py -q`
- green exit_code: 0
- green: 7 passed, 0 failed

**Code**: `reaction_agent/p3/fixtures.py`, `reaction_agent/p3/load.py`, `reaction_agent/p3/kernel.py` — `FixtureAuthorityManifest` (kind fixed `synthetic_fixture`, immutable) and `ProductionAuthorityHandle` (only constructible via the internal P1/P2 authority adapter) are DIFFERENT types; the real loader requires a `ProductionAuthorityHandle`.
**Tests**: `tests/p3/test_r7b_fixture_production_authority_isolation.py` (7 tests, incl. `test_fixture_root_relabelled_and_rehashed_as_production_is_rejected`).
**Invariants**: (1) fixture kind is immutable (relabeling raises); (2) a fixture root passed to the real loader is rejected (`FIXTURE_MANIFEST_AS_PRODUCTION_AUTHORITY`); (3) a public caller cannot construct a `ProductionAuthorityHandle`; (4) while the real P1/P2 root is unavailable the real loader/kernel return `PRODUCTION_AUTHORITY_UNAVAILABLE` (typed BLOCKED) — they never manufacture a production root; (5) fixture mode keeps `synthetic_fixture` evidence kind.
**Residual risk**: a real P1/P2 frozen production authority is not yet available; the production path is honestly BLOCKED.

## R6-A / R6-B / R6-C regression

All R6-A / R6-B / R6-C and R5-A / R5-B / R5-C / R4-E tests still pass (see the verification matrix: `r6a_regression` / `r6b_regression` / `r6c_regression` and `r5a_regression` / `r5b_regression` / `r5c_regression` / `r4e_regression` rows).

## Verification matrix

| label | exit | collected | passed | failed | errors | skipped |
|-------|------|-----------|--------|--------|--------|---------|
| r7a_green | 0 | 7 | 7 | 0 | 0 | 0 |
| r7b_green | 0 | 7 | 7 | 0 | 0 | 0 |
| r6a_regression | 0 | 8 | 8 | 0 | 0 | 0 |
| r6b_regression | 0 | 9 | 9 | 0 | 0 | 0 |
| r6c_regression | 0 | 8 | 8 | 0 | 0 | 0 |
| r5a_regression | 0 | 15 | 15 | 0 | 0 | 0 |
| r5b_regression | 0 | 16 | 16 | 0 | 0 | 0 |
| r5c_regression | 0 | 8 | 8 | 0 | 0 | 0 |
| r4e_regression | 0 | 4 | 4 | 0 | 0 | 0 |
| p3_suite | 0 | 493 | 493 | 0 | 0 | 0 |
| full_suite | 0 | 1399 | 1399 | 0 | 0 | 0 |
| p0_gate | 0 | 0 | 10 | 0 | 0 | 0 |
| p1_gate | 0 | 0 | 10 | 0 | 0 | 0 |
| p3_gate | 2 | 0 | 0 | 0 | 0 | 0 |

## GREEN attack probes (R7)

- `simultaneous_raw_and_typed_receipt_rewrite` -> {"probe": "simultaneous_raw_and_typed_receipt_rewrite", "verdict": "FAIL", "verified": false, "machinery_failures": ["MUTATION_STDOUT_HASH_MISMATCH:m_ab_only_stripped_reaction:mutated", "EXECUTED_MUTATION_MISMATCH:m_ab_only_stripped_reaction"]}
- `missing_mutation` -> {"probe": "missing_mutation", "verdict": "FAIL", "verified": false, "machinery_failures": ["MUTATION_ID_MISMATCH:['m_ab_only_stripped_reaction']", "EXECUTED_MUTATION_COUNT_MISMATCH:executed=14:submitted=13"]}
- `extra_mutation` -> {"probe": "extra_mutation", "verdict": "FAIL", "verified": false, "machinery_failures": ["MUTATION_ID_DUPLICATE", "EXECUTED_MUTATION_COUNT_MISMATCH:executed=14:submitted=15"]}
- `reordered_mutations` -> {"probe": "reordered_mutations", "verdict": "FAIL", "verified": false, "machinery_failures": ["EXECUTED_MUTATION_ORDER_MISMATCH:m_deleted_participant:executed_position=0:m_ab_only_stripped_reaction", "EXECUTED_MUTATION_MISMATCH:m_deleted_participant", "EXECUTED_MUTATION_ORDER_MISMATCH:m_ab_only_stripped_reaction:executed_position=1:m_deleted_participant", "EXECUTED_MUTATION_MISMATCH:m_ab_only_stripped_reaction"]}
- `adjudication_rewrite` -> {"probe": "adjudication_rewrite", "verdict": "FAIL", "verified": false, "machinery_failures": ["MUTATION_ESCAPED:m_ab_only_stripped_reaction", "EXECUTED_MUTATION_MISMATCH:m_ab_only_stripped_reaction"]}
- `fixture_root_relabelled_as_production` -> {"probe": "fixture_root_relabelled_as_production", "accepted": false, "failure_code": "FIXTURE_KIND_IMMUTABLE", "detail": "relabeling a fixture manifest kind is rejected by the type"}
- `fixture_root_passed_to_real_loader` -> {"probe": "fixture_root_passed_to_real_loader", "accepted": false, "failure_code": "FIXTURE_MANIFEST_AS_PRODUCTION_AUTHORITY"}
- `public_production_handle_construction` -> {"probe": "public_production_handle_construction", "accepted": false, "failure_code": "PRODUCTION_HANDLE_NOT_CONSTRUCTIBLE", "detail": "ProductionAuthorityHandle is not constructible by callers; only the internal P1/P2 authority adapter can create one"}
- `real_gate_artifact` -> {"probe": "real_gate_artifact", "verdict": "BLOCKED", "verified": true, "machinery_failures": []}

## Gate reports

- P3 Gate verdict: BLOCKED (exit 2)
- P3 Gate session nonce: 0fa14bef84b48d78...
- P3 Gate mutation registry hash: dd4f5bb71f8f5f53...
- P0 Gate: 0 (10/10)
- P1 Gate: 0 (10/10)

## Mutation suite

- mutations: 14
- all valid: True
- all caught: True

## Changed files (from the implementation commit tree)

- commit: b853f7b
- parent: a0fffdb2c126473c5879f68757c4c5dab13e68e5
- count: 7

- CC/branch/ReactionAgent/demov2/reaction_agent/p3/fixtures.py
- CC/branch/ReactionAgent/demov2/reaction_agent/p3/gate.py
- CC/branch/ReactionAgent/demov2/reaction_agent/p3/kernel.py
- CC/branch/ReactionAgent/demov2/reaction_agent/p3/load.py
- CC/branch/ReactionAgent/demov2/scripts/p3/r7_attack_probes.py
- CC/branch/ReactionAgent/demov2/tests/p3/test_r7a_mutation_execution_authority.py
- CC/branch/ReactionAgent/demov2/tests/p3/test_r7b_fixture_production_authority_isolation.py

## Final status

P3_ROUND_7_READY_FOR_CHATGPT_READ_ONLY_AUDIT_P4_BLOCKED
