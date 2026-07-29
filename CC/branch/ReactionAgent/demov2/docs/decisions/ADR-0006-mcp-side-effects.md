# ADR-0006: MCP Side Effects

**Status:** Approved
**Date:** 2026-07-29

## Background

P0 does not implement an MCP server, but the side-effect and idempotency contracts for future MCP tools must be frozen now to prevent ambiguity during P6 implementation.

## Decision

### Tool Categories and Side Effects

| Tool | Evidence Corpus | Run Store | Network | Idempotency |
|------|----------------|-----------|---------|-------------|
| `predict` | read-only | append/write immutable run | no | request hash + snapshot/version + idempotency key → reuse |
| `get_run` | read-only | read-only | no | read-only/idempotent |
| `get_candidate_evidence` | read-only | read-only | no | read-only/idempotent |
| `expand_evidence` (local) | read-only | append child run | no | child request reuse |
| `expand_evidence` (external) | append augmentation | append child | yes | independent retrieval; post-MVP |

### Idempotency Semantics

Every mutation request requires:
- `client_request_id`
- `idempotency_key`
- `snapshot_id`

Server behavior:
- Same idempotency key + same canonical request → return same run
- Same idempotency key + different request → typed conflict error
- Concurrent identical requests → atomic dedup (exactly one run created)

### Run Immutability

- Completed/frozen runs cannot be modified in place
- Evidence expansion creates child run, parent unchanged
- External evidence creates augmentation with separate provenance
- Resource URIs are opaque; agents must not derive them

### Field Naming

Unified field names (no aliases):
- `manifest_uri` (not `run_manifest_uri`)
- `source_reaction_ledger` (not `ledger` or `reaction_ledger` for source)
- `candidate_analogy_ledger` (not `ledger` for candidate)

### Resource URIs

```
reactionagent://runs/{run_id}
reactionagent://runs/{run_id}/manifest
reactionagent://runs/{run_id}/candidates/{candidate_id}
reactionagent://runs/{run_id}/evidence/{evidence_id}
reactionagent://snapshots/{snapshot_id}
```

IDs and URIs are opaque — agents must not construct or derive them.

### External Evidence (Post-MVP)

External evidence tools:
- Not part of MVP
- Have network I/O
- Require source licensing, caching, timestamps, content hash, provenance
- Must not modify frozen primary run
- Must not read hidden answers in benchmark

## What This ADR Does Not Do

- Does not implement MCP server (P6)
- Does not define tool schemas beyond side-effect contracts
- Does not define authentication/authorization

## Failure Behavior

- Predict without idempotency key → protocol error
- Same key + different request → typed conflict
- Modification of frozen run → integrity violation
- Agent-constructed resource URI → grounding violation

## Consequences

- MCP contracts are testable via structured contract models
- Side-effect matrix is machine-verifiable
- Idempotency semantics prevent duplicate runs
- Parent runs are protected from child mutations

## Acceptance Criteria

- [x] Four tool categories with side-effect matrix defined
- [x] Idempotency semantics specified (same key/same request, same key/different request, concurrent)
- [x] Run immutability contract defined
- [x] Field naming unified (no aliases)
- [x] Resource URI scheme defined
- [x] External evidence marked post-MVP

## Traceability

- final_design.md §22
- final_discussion.md §ChatGPT 8
