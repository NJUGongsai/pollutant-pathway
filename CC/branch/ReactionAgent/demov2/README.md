# Reaction Analogy Agent — demov2

> Evidence-grounded one-step structural analogy prediction for unknown substrate X.

## Authoritative Documents

The following three documents are the **sole implementation authority**:

| Document | Scope |
|----------|-------|
| [`plan/final_design.md`](plan/final_design.md) | System semantics, object boundaries, scientific contracts |
| [`plan/final_plan.md`](plan/final_plan.md) | Implementation phases, gates, tests, stop conditions |
| [`plan/final_discussion.md`](plan/final_discussion.md) | Three-model fusion decisions, §15 resolution, signing record |

**All other documents in `plan/` (except the three final authority files above) are historical reference only** and must not guide implementation.

## Current Phase

**P0 — Contract Freeze** (current)

P0 delivers:
- 6 Architecture Decision Records (ADRs)
- Pydantic v2 schema skeletons (data contracts only, no business logic)
- Contract tests (positive + negative)
- JSON Schema exports
- P0 Gate runner

P0 does NOT implement:
- Donor retrieval algorithms
- Atom mapping or graph edit algorithms
- Transformation extraction
- Candidate generation
- Ranking or scoring
- MCP server or LLM agent
- Any P1+ functionality

## Quick Start

### Run P0 Gate

```bash
cd /Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2
python scripts/run_p0_gate.py
```

### Run Contract Tests

```bash
pip install -e ".[dev]"
python -m pytest tests/ -v
```

### Export JSON Schemas

```bash
python scripts/export_json_schemas.py
```

## Directory Structure

```
demov2/
├── docs/decisions/          # 6 ADRs
├── plan/                    # Authority documents + historical reference
├── reaction_agent/
│   └── schemas/             # Pydantic v2 data contracts
├── schemas/json/            # Exported JSON Schema
├── scripts/                 # Gate runner + export scripts
├── tests/contracts/         # Contract tests
└── reports/p0/              # P0 gate report
```

## Legacy Metrics

All prior benchmark numbers (41.5%, 23.5%, 79.5%, etc.) are **provisional** and cannot serve as v2 KPIs. See ADR-0001.

## Non-Authoritative Historical Documents

The following documents are retained for decision history only and must NOT guide implementation:

- `plan/chatgpt-reaction-analogy-agent-design-v2.md` — historical baseline
- `plan/chatgpt-reaction-analogy-agent-plan-v2.md` — historical baseline
- `plan/chatgpt-reaction-analogy-agent-design.md` — historical
- `plan/chatgpt-reaction-analogy-agent-plan.md` — historical
- `plan/UNIFIED_DESIGN_REACTION_ANALOGY_AGENT_2026-07-29.md` — concept quick-reference
- `plan/UNIFIED_PLAN_REACTION_ANALOGY_AGENT_2026-07-29.md` — concept quick-reference
- `plan/FUSION_DESIGN_V5.md` — historical
- `plan/qwen_design.md` / `plan/qwen_plan.md` — historical
- `plan/CLAUDE_DESIGN_LLM_LATENT_STAGE_REASONING_2026-07-29.md` — historical
- `plan/CLAUDE_PLAN_LLM_LATENT_STAGE_REASONING_2026-07-29.md` — historical
- `plan/chatgpt-discussion.md` — discussion draft (non-final)
- `plan/CLAUDE_discussion.md` — discussion draft (non-final)
- `plan/qwen_discussion.md` — discussion draft (non-final)

Note: `plan/final_discussion.md` IS an authoritative document (see above).
