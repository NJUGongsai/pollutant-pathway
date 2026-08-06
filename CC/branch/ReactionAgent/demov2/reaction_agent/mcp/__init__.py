"""P6 MCP Service — strict tool contracts, idempotency, immutable runs.

Provides the kernel for the ReactionAgent MCP service:
- strict JSON schemas for 4 tools (``reaction.*_v1``)
- canonical request hashing + idempotency store (atomic dedup)
- immutable run store (write-once, child expansion preserves parent)
- typed error taxonomy (SchemaError / ProtocolError / IdempotencyConflict
  / RunNotFound / Storage)

Side-effect contract is authoritative in
``reaction_agent.contracts.mcp_side_effects`` (F3 matrix).
"""
from __future__ import annotations

from reaction_agent.mcp.errors import (
    P6Error,
    SchemaError,
    ProtocolError,
    IdempotencyConflictError,
    RunNotFoundError,
    StorageError,
    IntegrityViolationError,
    SnapshotUnavailableError,
    BudgetExceededError,
)
from reaction_agent.mcp.schemas import (
    GOLDEN_SCHEMAS,
    MCP_TOOL_SCHEMAS,
    P6_SCHEMA_VERSION,
    validate_input,
)
from reaction_agent.mcp.runs import RunStore, RunRecord
from reaction_agent.mcp.idempotency import (
    IdempotencyStore,
    IdempotencyRecord,
    canonical_request_hash,
    make_request_hash,
)

__all__ = [
    "P6Error",
    "SchemaError",
    "ProtocolError",
    "IdempotencyConflictError",
    "RunNotFoundError",
    "StorageError",
    "IntegrityViolationError",
    "SnapshotUnavailableError",
    "BudgetExceededError",
    "GOLDEN_SCHEMAS",
    "MCP_TOOL_SCHEMAS",
    "P6_SCHEMA_VERSION",
    "validate_input",
    "RunStore",
    "RunRecord",
    "IdempotencyStore",
    "IdempotencyRecord",
    "canonical_request_hash",
    "make_request_hash",
]