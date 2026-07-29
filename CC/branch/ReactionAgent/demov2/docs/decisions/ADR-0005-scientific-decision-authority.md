# ADR-0005: Scientific Decision Authority

**Status:** Approved
**Date:** 2026-07-29

## Background

The system must have a clear separation between:
- What the LLM can do (evidence strategy, hypothesis selection, explanation)
- What the deterministic decision policy decides (predicted/abstained/partial/failed, rankings, lanes)

LLM must not be able to override scientific status, fabricate confidence, or confuse infrastructure failures with scientific abstention.

## Decision

### Versioned Decision Policy is Sole Authority

The following fields are determined ONLY by the versioned deterministic decision policy:
- `status` (completed / abstained / partial / failed)
- `decision` (predicted / abstained / partial / failed)
- `reason_code`
- `rank`
- `lane`
- `validation`
- `applicability`

### LLM Role

The LLM may:
- Decide when to stop retrieval and request a formal decision
- Request more evidence
- Explain kernel-returned abstention
- Compare evidence and hypotheses
- Generate grounded rationale summary

The LLM may NOT:
- Change `predicted` to `abstained` or vice versa
- Override reason codes
- Explain infrastructure failure as scientific abstention
- Modify ranking, lane, ledger, or applicability
- Self-report qualitative confidence ("high"/"medium"/"low")

### Prohibition on LLM Qualitative Confidence

Before independent calibration (Brier/ECE/risk-coverage), only these fields are permitted:
- `ranking_score`
- `support_tier`
- `evidence_strength`
- `applicability_label`

Forbidden:
- `confidence`
- `biological_probability`
- `enzyme_activity_probability`
- Any LLM self-reported qualitative confidence

Host may map structured fields to natural language (e.g., "multiple independent strict structural analogy evidence") but NOT to "LLM high confidence."

### Scientific Abstention Reasons

```
INVALID_INPUT
NO_IN_DOMAIN_DONOR
NO_RESOLVED_LINEAGE
NO_TRANSFERABLE_TRANSFORM
NO_COMPATIBLE_SITE
ALL_CANDIDATES_CHEMICALLY_INVALID
EVIDENCE_CONFLICT
INSUFFICIENT_SUPPORT
OUT_OF_DOMAIN
```

### System Failure Reasons

```
SNAPSHOT_UNAVAILABLE
MAPPER_UNAVAILABLE
TOOL_PROTOCOL_ERROR
STORAGE_FAILURE
BUDGET_CONFIGURATION_ERROR
```

### Cross-Field Invariants (PredictionResult)

| Status | Candidates | Abstention | Failure |
|--------|-----------|------------|---------|
| completed | ≥ 1 | null | null |
| abstained | 0 | scientific reason required | null |
| partial | any | optional | null + partial_reason required |
| failed | any | null | system reason required |

Enforced by Pydantic model_validator.

### Separation of Scientific Abstention and System Failure

- Scientific abstention = normal business result ("evidence insufficient")
- System failure = infrastructure error ("snapshot unavailable")
- System failure MUST NEVER be reported as scientific abstention
- System failure MUST NEVER use scientific abstention reason codes

## What This ADR Does Not Do

- Does not define the decision policy algorithm (P4)
- Does not define calibration methodology (future)
- Does not define LLM prompt engineering

## Failure Behavior

- completed + 0 candidates → invariant violation
- abstained + candidates present → invariant violation
- failed + scientific reason → invariant violation
- LLM self-reported confidence → schema violation

## Consequences

- PredictionResult schema enforces invariants via model_validator
- Scientific and system failure enums are disjoint
- No qualitative confidence field exists in any schema

## Acceptance Criteria

- [x] Decision authority clearly assigned to versioned policy
- [x] LLM permissions and prohibitions documented
- [x] Scientific abstention enum complete (9 values)
- [x] System failure enum complete (5 values)
- [x] Cross-field invariants enforced by schema
- [x] Qualitative confidence prohibited

## Traceability

- final_design.md §18.3, §15.3, §15.4, §22.5
- final_discussion.md §ChatGPT 3, 4
