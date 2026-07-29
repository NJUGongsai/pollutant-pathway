# ADR-0003: Ledger and Source Semantics

**Status:** Approved
**Date:** 2026-07-29

## Background

Two critical semantic boundaries must be enforced:

1. **Formal mapping ≠ Mechanistic origin**: Generic atom mappers provide formal graph correspondence, not proven mechanistic atom origin. Only isotope tracing or curated mechanistic evidence can establish mechanism.

2. **Source ledger ≠ Candidate ledger**: What the source database records about a donor reaction is fundamentally different from what we assume when transferring that context to X→Y.

## Decision

### Formal vs Mechanistic Separation

The following concepts are independent and must not be conflated:

| Field | Meaning |
|-------|---------|
| `formal_mapped_source_assignment` | Atom-to-atom correspondence from mapper |
| `mechanistic_atom_origin` | Experimentally proven atom origin |
| `source_assignment_method` | How the assignment was derived |
| `source_assignment_quality` | Quality of the assignment |
| `source_assignment_ambiguity` | Whether assignment is ambiguous |
| `mechanistic_origin_evidence_ids` | Evidence IDs proving mechanism |

**Rules:**
- Mapper output → formal mapping only
- Mapper output ≠ mechanistic origin (automatic upgrade forbidden)
- Mechanistic origin requires independent evidence IDs
- UI/reports must not label formal assignments as proven mechanism

### Unbound Mechanistic Evidence (Section 12 decision)

Unbound mechanistic evidence — `mechanistic_origin_evidence_ids` non-empty
without a `mechanistic_atom_origin` object — is **prohibited**.

Rationale: a bare list of evidence IDs without a bound `mechanistic_atom_origin`
is ambiguous — it cannot be distinguished from proven mechanistic origin in
reports, and invites conflating formal mapping with mechanism. If mechanistic
evidence exists, it must be expressed as a `mechanistic_atom_origin` typed
object with matching `evidence_ids`.

The flat `mechanistic_origin_evidence_ids` field is derived from the typed
`mechanistic_atom_origin.evidence_ids` and must be consistent with it
(Section 10). Atom pairs are typed skeletons (`FormalMappedAtomPair`,
`MechanisticAtomPair`), not arbitrary dict (Section 11).

### Dual Ledger Design

#### SourceReactionLedger

Records what the source database actually documents about the donor reaction:
- Complete participants with roles
- Stoichiometry
- Formal atom transfers
- Element/charge balance
- Cofactor changes
- Source/mapping completeness
- Balance status
- Unknowns (explicitly preserved, never silently filled)

#### CandidateAnalogyLedger

Records analogy assumptions when transferring donor context to X→Y:
- Source ledger linkage (mandatory)
- Adaptation map (donor→query)
- Inherited donor context
- Inherited assumptions
- Unknown actual co-substrates, cofactors, stoichiometry
- Balance status under assumptions

**Critical rule:** Donor uses NAD(P), O₂, H₂O does NOT mean X→Y actually uses the same cofactors. These are inherited assumptions only, explicitly labeled as such.

### COFACTORS Policy

COFACTORS list serves as:
- Participant role prior
- Donor eligibility prior
- Retrieval downweighting prior

COFACTORS list is NOT:
- A destructive reaction stripping rule
- A ground-truth role label
- An atom-balance exclusion rule

Small molecules may be: transferred atom sources, leaving groups, true substrates, or byproducts. Complete reaction evidence must be preserved losslessly.

## What This ADR Does Not Do

- Does not define the mapping algorithm (P1)
- Does not define ledger computation (P1)
- Does not define COFACTORS list contents

## Failure Behavior

- Formal mapping auto-populated as mechanistic origin → schema violation
- Mechanistic origin without evidence IDs → rejected
- Source and candidate ledger fields mixed → schema violation
- Candidate ledger without source linkage → rejected
- Source unknown silently filled as fact → schema violation
- Unbound mechanistic evidence (evidence IDs without mechanistic_atom_origin) → rejected (Section 12)
- Typed/flat assignment fields contradicting → rejected (Section 10)

## Consequences

- MappingReport schema separates formal/mechanistic fields
- Two separate ledger schemas with mandatory cross-reference
- All reports must use precise language: "formal source assignment" vs "proven mechanistic origin"

## Acceptance Criteria

- [x] MappingReport has formal/mechanistic separation
- [x] SourceReactionLedger and CandidateAnalogyLedger are separate schemas
- [x] Candidate ledger requires source ledger linkage
- [x] COFACTORS policy documented
- [x] Formal ≠ mechanistic enforced in schema

## Traceability

- final_design.md §6, §8.2, §10
- final_discussion.md §ChatGPT 6.1, 6.2, 6.4
