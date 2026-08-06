# P1-T11 Manual Audit Report — Round 3

**Status:** `COMPLETE`
**Pass:** `true`
**Packet:** `505e5ee66fb56a5c7ea94be08016497ce4750b641d877e44d6e2633c7bf3519f`

## Outcome

Two fresh blinded annotators completed the four-record census and a third
independent adjudicator resolved every disagreement. Round 1 is preserved at
`reports/p1/g10_round_1/`; this report is computed only from Round
3 inputs.

| Metric | Value |
|---|---:|
| Raw A/B agreement | 1.000000 |
| Disagreements | 0 |
| Distinct catastrophic error types | 0 |
| All disagreements resolved | true |

## Frozen hard conditions

| Condition | Verdict | Independent adjudicator reason |
|---|---|---|
| H1 | PASS | The production index contains only rxn_strict_001 and rxn_cond_001, and independent review finds no C1-C9 occurrence on either production row. |
| H2 | PASS | All three real required-case rows are explicitly quarantined with zero production eligibility, zero synthesized lineages, and zero forbidden lineages. |
| H3 | PASS | No census row contains an ambiguity set or silently selected critical tie; each retained lineage is unambiguous, and unresolved real required-case rows are quarantined. |
| H4 | PASS | rxn_quar_001 appears only in quarantine membership, while the production index contains only the strict and conditional rows. |
| H5 | PASS | Every census row retains its one reactant and one product, and both participant identifiers appear in the corresponding source-ledger role assignments. |
| H6 | PASS | All census mapping reports label source assignment as formal_mapped, with null mechanistic origin and empty mechanistic evidence identifiers. |
| H7 | PASS | The executed hash-only result, two completed builds, and two accepted loader results share snapshot ID snap_c589494081df and hash c589494081dfeb19d178fb6e057bfe41a9b402827054ae4bc5b28d48eb077d89; both record-hash lists are identical. |

## Domain rubric scores

| Score | Value |
|---|---:|
| mapping_rubric_score | 1.000000 |
| role_rubric_score | 1.000000 |
| lineage_rubric_score | 1.000000 |
| ledger_rubric_score | 1.000000 |

## Evidence boundary

The four snapshot records are synthetic contract fixtures, not real chemical
performance evidence. H2 is evaluated separately against three real
proline/2OG source rows. The new pipeline explicitly quarantines those rows
because the available mapping is diagnostic formal MCS evidence; it does not
claim that their expected lineages have already been resolved.
