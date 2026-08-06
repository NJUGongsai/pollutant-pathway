# P1 Final Acceptance — Direct Remediation and Independent G10 Audit

**Date:** 2026-08-02  
**Scope:** P1 data foundation, mapping/evidence boundaries, legacy lineage audit,
snapshot authority, manual audit, Gate resistance  
**Final verdict:** **P1 PASS / ACCEPTED**  
**P2 decision:** **UNBLOCKED by this ChatGPT final acceptance**; no P2 code was
started in this remediation.

## 1. Executive result

P1 is now complete under its frozen contracts. This acceptance is based on
executed tests, two failed independent G10 rounds preserved as evidence, a
third independent G10 round, and anti-false-positive mutations. It is not a
status-string promotion.

| Verification | Final observed result |
|---|---:|
| Standalone full test suite | **906 passed** |
| Fail / error / skip / xfail / xpass | **0 / 0 / 0 / 0 / 0** |
| P0 Gate | **10/10 PASS** |
| P1 Gate | **10/10 PASS** |
| P1 Gate mutations | **91/91 caught** |
| G10 raw A/B agreement | **44/44 = 1.000000** |
| G10 disagreements | **0** |
| G10 catastrophic error types | **0** |
| G10 mapping / role / lineage / ledger scores | **1.0 / 1.0 / 1.0 / 1.0** |
| G10 H1–H7 | **all PASS** |
| G10 Q1–Q4 | **all PASS** |

The G10-internal full-suite run reports 889/889 because it intentionally
excludes `test_p1_gate_contract.py` to prevent Gate→pytest→Gate recursion. The
standalone command includes that file and reports 906/906.

## 2. Scientific remediation completed

### 2.1 Real proline/2OG required case

The legacy audit processed all **3601/3601** real source reactions and located
three real proline/2OG rows by exact stereo-independent participant
structures. All three exhibit the legacy cross-lineage selection class.

The available RDKit result is an MCS/formal diagnostic fallback, not a complete
atom map and not mechanistic-origin evidence. Therefore P1 does **not** claim
that the real lineages have been solved. The new fail-closed policy generates
an explicit quarantine disposition for every real row:

- real cases: **3**;
- explicitly quarantined: **3**;
- production eligible: **0**;
- synthesized resolved lineages: **0**;
- forbidden 2-oxoglutarate→hydroxyproline lineage present: **0**.

This is the honest H2 branch: “correctly resolved **or quarantined**.” Future
promotion requires a validated complete mapper plus independently audited
multi-lineage resolution.

### 2.2 Fixture evidence corrected

The first independent audit detected that the T10 contract fixtures were
described as hydroxylation/transfer/cleavage, multi-reactant, and sometimes
cofactor-containing even though the serialized records did not contain those
facts. Those labels were removed. The current manifest is generated from the
serialized snapshot and truthfully records:

- four synthetic contract fixtures, one per eligibility lane;
- one reactant and one product in every fixture;
- no explicit cofactor role in the fixture census;
- actual mapping status, ledger status, lane, participant count, and source;
- no claim of real chemical-diversity or production-performance coverage.

### 2.3 Mapping and ledger contradictions corrected

- `CC>>CCC` is now `partially_mapped`; the product's third atom remains an
  explicit unknown source and changed-atom coverage is not overstated.
- The quarantine fixture now uses a real +1→0 charge change and ledger
  `charge_balance=-1`; it no longer attaches an invented imbalance to
  `CC>>CC`.
- Formal mapping remains separate from mechanistic origin on every path.

### 2.4 Snapshot authority and replay

The sample manifest, on-disk manifest, loader record, and sealed packet now
share one identity:

- snapshot ID: `snap_c589494081df`;
- snapshot hash:
  `c589494081dfeb19d178fb6e057bfe41a9b402827054ae4bc5b28d48eb077d89`.

Replay evidence is executed rather than asserted: hash-only computation,
forward-order build, reverse-order build, loader A, and loader B all produce or
accept the same ID/hash; both record-content-hash lists match.

### 2.5 G04 report/live coherence

The final mutation run initially exposed two G04 weaknesses. They were not
waived:

- M12 was updated to inject an actual skeleton at the live adapter boundary,
  because the production adapter is no longer a skeleton;
- G04 now rejects contradictions between live availability, stored backend
  probes, `all_backends_unavailable`, integration status, and stored live-probe
  fields.

After remediation, M12 and M13 are both caught and the full mutation result is
91/91.

## 3. Independent G10 chain of custody

The earlier judgments were never rewritten into PASS.

| Round | Raw A/B agreement | Independent outcome | Preserved result |
|---|---:|---|---|
| 1 | 0.818182 | H2 FAIL, H7 FAIL | **FAIL**, archived |
| 2 | 0.772727 | H1–H7 PASS; Q1 below 0.90 | **FAIL**, archived |
| 3 | 1.000000 | H1–H7 and Q1–Q4 PASS | **PASS**, canonical |

Round 2 proved that the remaining disagreement concerned applicability only:
A used N/A for some R7/R9/R11 cells while B used PASS; the independent
adjudicator resolved all ten as PASS. Before Round 3, protocol version
`p1-t11-3` froze the per-row interpretation and retained every existing
threshold and denominator. The validator then enforced that every R1–R11 cell
listed as applicable must be pass/fail.

Round-3 A and B were fresh no-shared-context instances. A malformed JSON
nesting from B was rejected; B was allowed only to mechanically nest its own
unchanged R/C judgments. A third fresh instance independently reviewed all 36
catastrophic cells and H1–H7 even though A/B had zero disagreements.

## 4. Primary evidence paths

- P1 Gate: `/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/P1_GATE_REPORT.md`
- P1 Gate JSON: `/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/P1_GATE_REPORT.json`
- P0 Gate: `/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p0/P0_GATE_REPORT.md`
- Canonical G10 report: `/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/manual_audit_report.md`
- Canonical G10 JSON: `/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/manual_audit_report.json`
- Round-1 FAIL archive: `/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/g10_round_1/`
- Round-2 FAIL archive: `/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/g10_round_2/`
- Round-3 PASS archive: `/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/g10_round_3/`
- Sealed evidence packet: `/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/manual_audit_evidence_packet.json`
- Real-case quarantine evidence: `/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/required_case_quarantine_evidence.json`
- Legacy full-corpus audit: `/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/data_audit/legacy_lineage_audit.json`
- Mutation results: `/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p1/mutation_results.json`
- Frozen Round-3 protocol: `/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/docs/manual_audit_protocol.md`

## 5. What this P1 PASS does and does not mean

This P1 PASS means the evidence foundation is reproducible, typed, fail-closed,
auditable, and safe enough for downstream development. It does **not** mean the
final product already performs the user's desired inference
`donor A→B + query X → predicted transformed X`.

That capability remains the responsibility of the downstream stages:

- P2: truth/isolation/funnel and evaluation authority;
- P3: strict transfer kernel and candidate/trace authority;
- P4: evidence/ranking/abstention authority;
- P5: leakage-safe benchmark and reporting.

P2–P5 may continue with parallel development and frozen interfaces, but formal
integration/Gate acceptance remains sequential P2→P3→P4→P5, using the P1
snapshot/lineage/ledger/eligibility outputs as the sole data authority.

## 6. Final acceptance statement

**ChatGPT final decision: ACCEPT P1.**

P1 has no remaining implementation failure or external blocker under the
frozen P1 scope. P2 is now unblocked by this audit. No dependency was installed,
no network access was used, and no legacy source was modified during this final
remediation.

