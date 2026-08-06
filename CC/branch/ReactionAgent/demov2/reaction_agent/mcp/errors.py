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


# -- T5/T6 (Phase B) additions — access control, retention, chaos hardening --


class UnauthorizedError(P6Error):
    """No access context supplied to a secured resource (fail-closed).

    Raised when a tool/resource is invoked in secured mode (a RetentionPolicy
    is configured) without an ``AccessContext``. Possession of a resource URI
    is never a capability — resolution always requires an authorized context.
    """

    code = "UNAUTHORIZED"
    httpish_status = 401


class ForbiddenError(P6Error):
    """Cross-tenant or insufficient-role access (fail-closed)."""

    code = "FORBIDDEN"
    httpish_status = 403


class ResourceExpiredError(P6Error):
    """Resource passed its retention TTL (``expires_at``)."""

    code = "RESOURCE_EXPIRED"
    httpish_status = 410


class PayloadTooLargeError(P6Error):
    """Serialized payload exceeds the configured byte cap."""

    code = "PAYLOAD_TOO_LARGE"
    httpish_status = 413


class ProtocolVersionMismatchError(P6Error):
    """Client protocolVersion does not match the server-pinned version."""

    code = "PROTOCOL_VERSION_MISMATCH"
    httpish_status = 400