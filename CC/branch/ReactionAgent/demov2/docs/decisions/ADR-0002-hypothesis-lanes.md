# ADR-0002: Hypothesis Lanes

**Status:** Approved
**Date:** 2026-07-29

## Background

The system must support two distinct modes of LLM hypothesis generation:
1. **Production selection**: LLM chooses/types/prioritizes within evidence-derived T/S space
2. **Agent-proposed**: LLM proposes novel T/S not yet in evidence space

These must be strictly separated to prevent unvalidated LLM inventions from entering production rankings.

## Decision

### Two Lanes, Enforced by Discriminated Union

Hypotheses are discriminated by `hypothesis_origin`:

#### ProductionSelectionHypothesis

- `hypothesis_origin = "agent_selected_from_evidence_space"`
- References only kernel-generated IDs (transformation_id, site_id)
- LLM may: select, compare, type, prioritize, stop retrieval, request decision
- LLM may NOT: create new transform/site IDs, modify structures, change rankings

Fields:
```
hypothesis_id, hypothesis_origin, support_reaction_ids[], support_lineage_ids[],
transformation_id, site_id, rationale_summary, policy_version
```

#### AgentProposedHypothesis

- `hypothesis_origin = "agent_proposed"`
- Proposes novel T/S via structured fields (typed_target_atom_or_bond_set)
- Free-text relaxation is forbidden; must use registered relaxation IDs
- Must pass full validation chain before receiving candidate_id
- Gets `agent_proposed` lane candidate, NOT production rank

Fields:
```
hypothesis_id, hypothesis_origin, support_reaction_ids[], support_lineage_ids[],
transformation_family_id, typed_target_atom_or_bond_set[], relaxation_policy_id,
allowed_relaxation_ids[], rationale_summary, policy_version
```

### Lane Mixing Forbidden

- ProductionSelection fields must not appear in AgentProposed and vice versa
- Schema enforces via discriminated union on `hypothesis_origin`
- Tests verify lane mixing is rejected

### Graduation Gate

Agent-proposed hypotheses cannot automatically enter production ranking. Graduation requires:
- Held-out benchmark evaluation
- Incremental recall and risk assessment
- Invented ID/structure mutation = 0
- Decision record (ADR)
- Human approval

Graduation is evidence-based, not declaration-based.

## What This ADR Does Not Do

- Does not define the validation chain (implementation detail)
- Does not define graduation metrics (deferred to P9)
- Does not define LLM prompt engineering

## Failure Behavior

- Unknown support_reaction_id → rejected
- Unknown transformation_id/site_id in ProductionSelection → rejected
- Free-text relaxation → rejected
- Missing or wrong origin → rejected
- Lane field mixing → rejected
- Unknown fields → rejected (extra="forbid")

## Consequences

- Schema uses Pydantic discriminated union for type-safe lane separation
- All hypothesis validation must check ID existence against evidence context
- Agent-proposed candidates are tracked separately for independent benchmarking

## Acceptance Criteria

- [x] Two hypothesis schemas defined with discriminated union
- [x] Lane mixing rejected by schema
- [x] Unknown ID references rejected
- [x] Free-text relaxation rejected
- [x] Graduation gate contract defined

## Traceability

- final_design.md §19
- final_discussion.md §ChatGPT 2.1, 2.2, 2.3
