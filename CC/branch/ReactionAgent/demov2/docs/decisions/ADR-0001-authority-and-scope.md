# ADR-0001: Authority and Scope

**Status:** Approved
**Date:** 2026-07-29
**Supersedes:** All prior design/plan documents

## Background

Three models (ChatGPT, Claude, Qwen) independently produced design documents for the Reaction Analogy Agent demov2. After extensive cross-review and discussion, the three models converged on a unified architecture. This ADR freezes which documents are authoritative and what the first version will deliver.

## Decision

### Authority

The following three documents are the **sole implementation authority**:

1. `plan/final_design.md` — system semantics, object boundaries, scientific contracts
2. `plan/final_plan.md` — implementation phases, gates, tests, stop conditions
3. `plan/final_discussion.md` — three-model fusion decisions, §15 resolution, signing record

All other documents (except the three final authority files above) are **historical reference only**:
- `chatgpt-reaction-analogy-agent-design-v2.md` — historical baseline
- `chatgpt-reaction-analogy-agent-plan-v2.md` — historical baseline
- `UNIFIED_DESIGN_*` / `UNIFIED_PLAN_*` — concept quick-reference
- `FUSION_DESIGN_V5.md` — historical
- `qwen_design.md` / `qwen_plan.md` — historical
- `CLAUDE_DESIGN_*` / `CLAUDE_PLAN_*` — historical
- Non-final discussion drafts (`chatgpt-discussion.md`, `CLAUDE_discussion.md`, `qwen_discussion.md`) — historical decision evidence only

If any conflict exists between this ADR and the three final documents, the final documents prevail.

### Scope — First Version

The first reliable version delivers:

- **Input:** Single query molecule X (SMILES)
- **Output:** One-step strict structural analogy candidates (ranked top-K) or typed abstention
- **Prediction type:** Structural transformation analogy only
- **Not predicted:** Enzyme activity probability, environmental occurrence, kinetics, yield

### Non-Goals (First Version)

- Generalized lane (deferred to P8)
- External open-world evidence (deferred to P9)
- Multi-step degradation paths (deferred to P9)
- Enzyme applicability module (future independent design)
- LLM qualitative confidence (prohibited; see ADR-0005)

### Legacy Metrics

All prior benchmark numbers (41.5%, 23.5%, 79.5%, A1/A2 diagnostics, etc.) are **provisional**. They were computed on data with known fragment-lineage bugs and cannot serve as v2 KPIs. New benchmarks will be established in P5 after data foundation is rebuilt.

## What This ADR Does Not Do

- Does not define schemas (see schemas/ modules)
- Does not define hypothesis lanes (see ADR-0002)
- Does not define ledger semantics (see ADR-0003)
- Does not define eligibility matrix (see ADR-0004)
- Does not define decision authority (see ADR-0005)
- Does not define MCP semantics (see ADR-0006)

## Failure Behavior

Any implementation that references non-authority documents as normative, or that claims legacy metrics as v2 targets, violates this ADR.

## Consequences

- Implementers must consult only the three final documents
- README must link only to final documents as authority
- All old metrics must be clearly marked provisional in any report

## Acceptance Criteria

- [x] Six ADRs approved
- [x] README points to three final documents only
- [x] No old document listed as current implementation authority
- [x] Legacy metrics marked provisional

## Environment Note

pyproject.toml requires Python >= 3.11 (adjusted from original >= 3.12 because the development environment only has Python 3.11.8 available, and all schema code is fully compatible with 3.11). This is documented, not silently changed. No authority document specifies a Python version requirement.

## Traceability

- final_design.md §0, §1, §2
- final_plan.md §3 (P0)
- final_discussion.md §ChatGPT (document status table)
