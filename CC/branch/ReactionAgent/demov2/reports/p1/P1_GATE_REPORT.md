# P1 Gate Report

**Timestamp (UTC):** 2026-08-06T09:12:06.855866+00:00
**Gate version:** p1-gate-1
**Working directory:** /Volumes/CC/Enzyme_Agent/depending/.claude/worktrees/p6-mcp-kernel/CC/branch/ReactionAgent/demov2
**Python:** 3.11.15

## Result: NOT_READY_FOR_CHATGPT_AUDIT

**Passed:** 8 / 10
**Blocked:** 0 / 10
**Failed:** 2 / 10

## Preflight Context

- Status: BLOCKED
- Blockers: real_reaction_source_not_confirmed, required_case_missing
- Impact: G03 (real source not confirmed), G04 (RealMapperAdapter skeleton not implemented), G10 (independent annotator/adjudicator not produced) blocked by external inputs; rdkit is available at runtime (no longer a blocker)

## Gate Checks

### P1-G01: package/runtime/lock + config & snapshot + no legacy write
**Status:** PASS
**Evidence:** package import + python + lock + config/snapshot + no-legacy-write guard verified
- config: reaction_agent/config.py
- provenance: reaction_agent/provenance.py
- snapshot: reaction_agent/snapshot/
- lock: requirements.lock.txt

### P1-G02: strict schemas/IDs/provenance + P0 contract green
**Status:** FAIL
**Evidence:** P0 gate exit=1 (regression!)
- schemas: reaction_agent/schemas/
- hashing: reaction_agent/hashing.py
- p0_gate: scripts/run_p0_gate.py
- tests: tests/contracts/

### P1-G03: legacy lineage audit complete
**Status:** PASS
**Evidence:** legacy full-corpus audit verified (counts/categories/source_ids/examples/hash + project-declared source + proline/2OG structure case)
- evidence: reports/data_audit/legacy_lineage_audit.json
- legacy_source: ../benchmark/canonical_identity.py (read-only)

### P1-G04: mapping adapter integration
**Status:** PASS
**Evidence:** mapping adapter: live probe + FakeAtomMapper unit contract (8 dims, formal_mapped, formal≠mechanism, MCS/center not strict) + T4 tests pass
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
**Evidence:** 14 cases: bipartite + split/merge/transfer + no-silent-tie + stable IDs + proline-2OG correct (identity-based) + T6 tests pass zero-skip
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
**Evidence:** 8 policy rows + warnings + quarantine behavior + production excludes prohibited/quarantine + reasons typed + fail-closed tests pass (incomplete/failed/MCS/unknown never strict)
- evidence: reports/p1/eligibility_matrix_execution.json
- policy: reaction_agent/policies/partial_eligibility.py
- engine: reaction_agent/eligibility/engine.py
- tests: tests/p1/test_eligibility_engine.py

### P1-G09: snapshot reproducibility
**Status:** PASS
**Evidence:** INDEPENDENT rebuild (2x same hash) + cross-verify stored hash + deterministic 3-way + content hash + manifest complete + filters counted + frozen + read-only loader + nested-evidence mutation/tamper tests pass
- evidence: reports/p1/snapshot_build_sample.json
- builder: reaction_agent/snapshot/builder.py
- loader: reaction_agent/snapshot/loader.py
- tests: tests/p1/test_snapshot_builder.py

### P1-G10: manual audit + full tests
**Status:** FAIL
**Evidence:** pytest has failures/errors: {'collected': 975, 'passed': 950, 'failed': 3, 'errors': 0, 'skipped': 0, 'xfailed': 0, 'xpassed': 0}
- evidence: reports/p1/manual_audit_report.json
- protocol: docs/manual_audit_protocol.md
- tests: tests/p1/test_manual_audit_contract.py

## P0 Baseline

- Contract tests: 290 passed
- Gate: 10/10
- Status: READY_FOR_CHATGPT_AUDIT

## Mutation Results (§18.3)

**91/91 mutations CAUGHT** — each mutation on an isolated temp copy caused the corresponding gate check to fail.

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
| M9 | G03 verdict COMPLETE but zero audited records | CAUGHT |
| M10 | G03 verdict COMPLETE but source_ids/examples empty | CAUGHT |
| M11 | G03 legacy source file hash mismatch | CAUGHT |
| M12 | G04 status-only promotion against injected live skeleton | CAUGHT |
| M13 | G04 all_backends_unavailable=true but status COMPLETE | CAUGHT |
| M14 | G06 remove proline case while keeping >=14 cases | CAUGHT |
| M15 | G06 inject forbidden 2OG->hydroxyproline strict pair | CAUGHT |
| M16 | G08 mapping_completeness=failed enters strict production | CAUGHT |
| M17 | G08 source_completeness=incomplete enters strict production | CAUGHT |
| M18 | G09 mutate participant provenance without hash change | CAUGHT |
| M19 | G09 mutate mapping pair without hash change | CAUGHT |
| M20 | G09 mutate source ledger without hash change | CAUGHT |
| M21 | G09 mutate transformed lineage without hash change | CAUGHT |
| M22 | G10 COMPLETE statuses with null annotation files | CAUGHT |
| M23 | G10 same annotator ID for A and B | CAUGHT |
| M24 | G10 missing adjudication for disagreement | CAUGHT |
| M25 | blocked Gate also contains implementation failure | CAUGHT |
| M26 | reaction-level provenance changes but hash unchanged | CAUGHT |
| M27 | source citation changes but hash unchanged | CAUGHT |
| M28 | fragment-lineage/ambiguity evidence changes but hash unchang | CAUGHT |
| M29 | quality/quarantine evidence changes but hash unchanged | CAUGHT |
| M30 | EligibilityDecision warning/evidence changes but hash unchan | CAUGHT |
| M31 | QuarantineRecord changes but hash unchanged | CAUGHT |
| M32 | mapped_heavy_atom_fraction < strict threshold enters strict | CAUGHT |
| M33 | formal assignment ambiguity enters strict | CAUGHT |
| M34 | formal pair unknown participant enters strict | CAUGHT |
| M35 | formal pair unknown atom map enters strict | CAUGHT |
| M36 | formal pair wrong-side participant enters strict | CAUGHT |
| M37 | unresolved/failed lineage enters strict | CAUGHT |
| M38 | partial identity ambiguity enters strict | CAUGHT |
| M39 | lineage unsupported by formal mapping enters strict | CAUGHT |
| M40 | two reactants claim one transformed product and enter strict | CAUGHT |
| M41 | embedded/external source ledgers disagree but snapshot build | CAUGHT |
| M42 | non-zero element delta on a balanced ledger enters strict | CAUGHT |
| M43 | explicit ReactionEvidence.quarantine enters production stric | CAUGHT |
| M44 | identity ambiguity set enters strict | CAUGHT |
| M45 | embedded lineage id conflicts with external lineage enters s | CAUGHT |
| M46 | uncontrolled direction value 'sideways' enters strict | CAUGHT |
| M47 | participant mapped_fraction 0.25 enters strict | CAUGHT |
| M48 | dropped formal pair (uncovered declared atom map) enters str | CAUGHT |
| M49 | two reactant atoms target one product atom (reverse collisio | CAUGHT |
| M50 | AddedAtomSource ghost participant enters strict | CAUGHT |
| M51 | RoleAssignment ghost participant enters strict | CAUGHT |
| M52 | StoichiometricEntry ghost participant enters strict | CAUGHT |
| M53 | FormalAtomTransferAssignment ghost participant enters strict | CAUGHT |
| M54 | generic ledger unknown enters strict | CAUGHT |
| M55 | duplicate lineage id/content enters strict | CAUGHT |
| M56 | remove/shadow G08/G09 mandatory test node -> corresponding G | CAUGHT |
| M57 | AddedAtomSource participant exists but atom map missing ente | CAUGHT |
| M58 | reactant_entries ghost participant enters strict | CAUGHT |
| M59 | product_entries ghost participant enters strict | CAUGHT |
| M60 | stoichiometry wrong-side / coefficient<=0 / contradictory ro | CAUGHT |
| M61 | FormalAtomTransfer endpoints exist but sides reversed enters | CAUGHT |
| M62 | FormalAtomTransfer unknown/conflicting map enters strict | CAUGHT |
| M63 | RemovedAtomSink ghost participant/map enters strict | CAUGHT |
| M64 | CofactorChange ghost participant enters strict | CAUGHT |
| M65 | MechanisticOriginEvidence ghost/map/dangling-linkage enters  | CAUGHT |
| M66 | negative element counts enter strict | CAUGHT |
| M67 | partial ledger consistent non-zero delta mislabeled as fully | CAUGHT |
| M68 | within-participant duplicate atom map enters strict | CAUGHT |
| M69 | same-side cross-participant atom map collision enters strict | CAUGHT |
| M70 | duplicate participant ID / uncontrolled participant side ent | CAUGHT |
| M71 | duplicate embedded lineage IDs enter strict | CAUGHT |
| M72 | reordered-map semantic duplicate lineage enters strict (dire | CAUGHT |
| M73 | existing cofactor participant + uncontrolled direction enter | CAUGHT |
| M74 | same participant/side duplicate/conflicting coefficients ent | CAUGHT |
| M75 | mechanistic reactant-only target map enters strict | CAUGHT |
| M76 | empty/duplicate formal transfer assignment enters strict | CAUGHT |
| M77 | heavy-atom participant with empty maps + mapped_fraction=1.0 | CAUGHT |
| M78 | heavy-atom map count underflow/overflow enters strict (direc | CAUGHT |
| M79 | atom map IDs containing 0/negative enter strict (direct + pu | CAUGHT |
| M80 | duplicate/conflicting AddedAtomSource/RemovedAtomSink enter  | CAUGHT |
| M81 | duplicate FAT / conflicting FAT / duplicate mechanistic targ | CAUGHT |
| M82 | RemovedAtomSink formal_assignment=False without authority en | CAUGHT |
| M83 | records diagnostic but wrongly injected into production inde | CAUGHT |
| M84 | delete expected diagnostic_index member (metadata untouched) | CAUGHT |
| M85 | mutate production_index entry nested payload (hash kept) | CAUGHT |
| M86 | delete required manifest diagnostic_index_hash field | CAUGHT |
| M87 | tamper manifest summary fields (counts / source summary / in | CAUGHT |
| M88 | forge manifest snapshot_id | CAUGHT |
| M89 | set manifest.record_count=true (boolean in exact-int field) | CAUGHT |
| M90 | nested failure_counts_by_reason count typed true/1.0 | CAUGHT |
| M91 | build_status authority order (delete / boolean / partial) | CAUGHT |

Mutations ONLY on isolated temp copies (`/tmp/p1_mutation_<n>/`). Formal code never polluted (§18.3).

## Deviations / Assumptions / Risks

**Deviations:**
- Execution model: ChatGPT-designed P1 tasks executed by Claude Code subagent (documented in SUBMISSION §15)
- rdkit available at runtime: G03 no longer reports rdkit_absent; remaining G03 blocker is real reaction source not confirmed; G04 blocker is RealMapperAdapter.map_reaction() skeleton (a scoped follow-up), not rdkit
- Manual audit BLOCKED: no independent second annotator available in single LLM session (§17.1/§17.7)

**Assumptions:**
- Gate reads machine-readable evidence (JSON fields, schema imports, subprocess results), never just os.path.exists (§18.2)
- BLOCKED is an honest outcome: §23 states BLOCKED is correct, fake PASS is not
- P0 baseline 290 + Gate 10/10 preserved (G02 re-runs P0 gate to verify no regression)

**Known risks:**
- G03/G04/G10 BLOCKED by external inputs (real-source / skeleton mapper / independent annotator) — cannot be resolved without external dependencies; rdkit is available and is no longer a blocker
- Fixture snapshot (4 synthetic records) is not real production data — audit validates pipeline contract, not real chemistry
- Proline-2OG case (H2) absent from fixture snapshot — cannot be evaluated until real data available

## User Files Protection

No user files deleted, moved, or overwritten. Gate is read-only: it reads evidence JSON, imports schemas, and runs pytest/P0-gate as subprocesses. No writes to ../benchmark, ../core, or reports/p0. No git add/commit/push/reset/clean.

## P2 Status

BLOCKED pending ChatGPT P1 read-only audit

## Conclusion

**NOT_READY_FOR_CHATGPT_AUDIT**

### Blocking items:

- P1-G02 [FAIL]: P0 gate exit=1 (regression!)
- P1-G10 [FAIL]: pytest has failures/errors: {'collected': 975, 'passed': 950, 'failed': 3, 'errors': 0, 'skipped': 0, 'xfailed': 0, 'xpassed': 0}