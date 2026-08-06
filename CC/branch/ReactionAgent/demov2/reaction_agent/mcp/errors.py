"""P6 MCP Service — typed error taxonomy.

All contract violations surface as typed P6Error subclasses with a stable
machine-readable ``code``. The MCP server maps these to JSON-RPC error
responses so callers can distinguish protocol errors, validation errors,
idempotency conflicts, missing resources, and storage failures without
crashing.
"""
from __future__ import annotations


class P6Error(Exception):
    """Base class for all P6 kernel errors."""

    code = "P6_ERROR"
    httpish_status = 500

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message

    def as_dict(self) -> dict:
        return {
            "error": self.code,
            "message": self.message,
        }


class SchemaError(P6Error):
    """Invalid request payload (unknown field, bad type, missing required).

    Maps to a strict input-schema rejection — never a crash.
    """

    code = "SCHEMA_VALIDATION_ERROR"
    httpish_status = 400


class ProtocolError(P6Error):
    """Protocol-level violation (missing idempotency key, wrong protocol)."""

    code = "PROTOCOL_ERROR"
    httpish_status = 400


class IdempotencyConflictError(P6Error):
    """Same idempotency key + different canonical request (ADR-0006)."""

    code = "IDEMPOTENCY_CONFLICT"
    httpish_status = 409


class RunNotFoundError(P6Error):
    """Requested run does not exist."""

    code = "RUN_NOT_FOUND"
    httpish_status = 404


class StoreError(P6Error):
    """Generic store error."""

    code = "STORE_ERROR"
    httpish_status = 500


class StorageError(P6Error):
    """Run/idempotency record corrupt or unreadable (interrupted write)."""

    code = "STORAGE_ERROR"
    httpish_status = 500


class IntegrityViolationError(P6Error):
    """Attempt to mutate or violate an immutable run invariant."""

    code = "INTEGRITY_VIOLATION"
    httpish_status = 409


class SnapshotUnavailableError(P6Error):
    """Requested snapshot is not available."""

    code = "SNAPSHOT_UNAVAILABLE"
    httpish_status = 404


class BudgetExceededError(P6Error):
    """Requested budget exceeded."""

    code = "BUDGET_EXCEEDED"
    httpish_status = 400