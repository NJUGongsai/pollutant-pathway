# P1 Gate Report

**Timestamp (UTC):** 2026-07-30T11:19:35.247495+00:00
**Gate version:** p1-gate-1
**Working directory:** /Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2
**Python:** 3.11.15

## Result: BLOCKED

**Passed:** 7 / 10
**Blocked:** 3 / 10
**Failed:** 0 / 10

## Preflight Context

- Status: BLOCKED
- Blockers: rdkit_absent, real_reaction_source_not_confirmed, required_case_missing
- Impact: G03 (real source), G04 (rdkit mapping), G10 (proline-2OG in audit) blocked by preflight

## Gate Checks

### P1-G01: package/runtime/lock + config & snapshot + no legacy write
**Status:** PASS
**Evidence:** package import + python + lock + config/snapshot + no-legacy-write guard verified
- config: reaction_agent/config.py
- provenance: reaction_agent/provenance.py
- snapshot: reaction_agent/snapshot/
- lock: requirements.lock.txt

### P1-G02: strict schemas/IDs/provenance + P0 contract green
**Status:** PASS
**Evidence:** strict schemas + deterministic IDs/hashes + provenance + P0 gate 10/10 green
- schemas: reaction_agent/schemas/
- hashing: reaction_agent/hashing.py
- p0_gate: scripts/run_p0_gate.py
- tests: tests/contracts/

### P1-G03: legacy lineage audit complete
**Status:** BLOCKED
**Evidence:** BLOCKED: verdict=PARTIAL: ['real_reaction_source_not_confirmed', 'rdkit_absent_runtime_unable_to_execute_legacy_transformed_pair', 'required_case_missing_proline_2og_source_record']; real_reaction_source_not_confirmed; required_case_missing_proline_2og
- evidence: reports/data_audit/legacy_lineage_audit.json
- legacy_source: ../benchmark/canonical_identity.py (read-only)

### P1-G04: mapping adapter integration
**Status:** BLOCKED
**Evidence:** BLOCKED: integration_status=INTEGRATION_BLOCKED: rdkit/numpy/networkx/scipy all absent in .venv (Preflight BLOCKED)
- evidence: reports/p1/mapping_integration_sample.json
- adapter: reaction_agent/mapping/adapter.py
- tests: tests/p1/test_mapping_adapter.py

### P1-G05: participant preservation/roles
**Status:** PASS
**Evidence:** participant multiset preserved, COFACTORS non-destructive, small molecules retained, ambiguity preserved + T5 tests pass zero-skip
- evidence: reports/p1/participant_role_sample.json
- roles: reaction_agent/roles/
- tests: tests/p1/test_participant_roles.py

### P1-G06: lineage graph bipartite/split-merge-transfer/no-silent-tie
**Status:** PASS
**Evidence:** 14 cases: bipartite + split/merge/transfer + no-silent-tie + stable IDs + proline-2OG correct + T6 tests pass zero-skip
- evidence: reports/p1/lineage_regression_cases.json
- lineage: reaction_agent/lineage/resolver.py
- tests: tests/p1/test_lineage_graph.py

### P1-G07: dual ledgers valid
**Status:** PASS
**Evidence:** SourceReactionLedger + CandidateAnalogyLedger valid, unknowns preserved, formal≠mechanism, source linkage valid + T7/T8 tests pass zero-skip
- evidence_src: reports/p1/source_ledger_samples.json
- evidence_cand: reports/p1/candidate_ledger_samples.json
- tests: tests/p1/test_source_ledger.py, tests/p1/test_candidate_ledger_skeleton.py

### P1-G08: eligibility/quarantine policy
**Status:** PASS
**Evidence:** 8 policy rows + warnings + quarantine behavior + production excludes prohibited/quarantine + reasons typed
- evidence: reports/p1/eligibility_matrix_execution.json
- policy: reaction_agent/policies/partial_eligibility.py
- engine: reaction_agent/eligibility/engine.py
- tests: tests/p1/test_eligibility_engine.py

### P1-G09: snapshot reproducibility
**Status:** PASS
**Evidence:** INDEPENDENT rebuild (2x same hash) + cross-verify stored hash + deterministic 3-way + content hash + manifest complete + filters counted + frozen + read-only loader
- evidence: reports/p1/snapshot_build_sample.json
- builder: reaction_agent/snapshot/builder.py
- loader: reaction_agent/snapshot/loader.py
- tests: tests/p1/test_snapshot_builder.py

### P1-G10: manual audit + full tests
**Status:** BLOCKED
**Evidence:** BLOCKED: annotator_a=NOT_PRODUCED; annotator_b=NOT_PRODUCED; adjudication=NOT_PRODUCED; catastrophic_error_count is null (cannot determine without double annotation)
- evidence: reports/p1/manual_audit_report.json
- protocol: docs/manual_audit_protocol.md
- tests: tests/p1/test_manual_audit_contract.py

## P0 Baseline

- Contract tests: 290 passed
- Gate: 10/10
- Status: READY_FOR_CHATGPT_AUDIT

## Mutation Results (§18.3)

**8/8 mutations CAUGHT** — each mutation on an isolated temp copy caused the corresponding gate check to fail.

| ID | Mutation | Result |
|----|----------|--------|
| M1 | delete participant preservation (invariant_holds=False) | CAUGHT |
| M2 | critical tie takes max (silent pick) | CAUGHT |
| M3 | MCS marked as full mapping (assignment_method=mcs_full_mappi | CAUGHT |
| M4 | mapper fills mechanism (formal_only_verified=False) | CAUGHT |
| M5 | quarantine record into production index | CAUGHT |
| M6 | snapshot hash non-deterministic (same_hash_3way=False) | CAUGHT |
| M7 | delete proline/2OG required case | CAUGHT |
| M8 | add skipped/xfailed test | CAUGHT |

Mutations ONLY on isolated temp copies (`/tmp/p1_mutation_<n>/`). Formal code never polluted (§18.3).

## Deviations / Assumptions / Risks

**Deviations:**
- Execution model: ChatGPT-designed P1 tasks executed by Claude Code subagent (documented in SUBMISSION §15)
- rdkit absent: T4 mapping integration, T6 lineage on real data, T7 source ledger balance blocked — unit contracts complete via FakeAtomMapper + structured fixtures
- Manual audit BLOCKED: no independent second annotator available in single LLM session (§17.1/§17.7)

**Assumptions:**
- Gate reads machine-readable evidence (JSON fields, schema imports, subprocess results), never just os.path.exists (§18.2)
- BLOCKED is an honest outcome: §23 states BLOCKED is correct, fake PASS is not
- P0 baseline 290 + Gate 10/10 preserved (G02 re-runs P0 gate to verify no regression)

**Known risks:**
- G03/G04/G10 BLOCKED by preflight (rdkit/real-source/annotator) — cannot be resolved without external dependencies
- Fixture snapshot (4 synthetic records) is not real production data — audit validates pipeline contract, not real chemistry
- Proline-2OG case (H2) absent from fixture snapshot — cannot be evaluated until real data available

## User Files Protection

No user files deleted, moved, or overwritten. Gate is read-only: it reads evidence JSON, imports schemas, and runs pytest/P0-gate as subprocesses. No writes to ../benchmark, ../core, or reports/p0. No git add/commit/push/reset/clean.

## P2 Status

BLOCKED pending ChatGPT P1 read-only audit

## Conclusion

**BLOCKED**

### Blocking items:

- P1-G03 [BLOCKED]: BLOCKED: verdict=PARTIAL: ['real_reaction_source_not_confirmed', 'rdkit_absent_runtime_unable_to_execute_legacy_transformed_pair', 'required_case_missing_proline_2og_source_record']; real_reaction_source_not_confirmed; required_case_missing_proline_2og
- P1-G04 [BLOCKED]: BLOCKED: integration_status=INTEGRATION_BLOCKED: rdkit/numpy/networkx/scipy all absent in .venv (Preflight BLOCKED)
- P1-G10 [BLOCKED]: BLOCKED: annotator_a=NOT_PRODUCED; annotator_b=NOT_PRODUCED; adjudication=NOT_PRODUCED; catastrophic_error_count is null (cannot determine without double annotation)