"""Custom exception types for contract violations."""


class ContractViolation(Exception):
    """Base exception for P0 contract violations."""
    pass


class LaneMixingError(ContractViolation):
    """Raised when production and agent_proposed lanes are mixed."""
    pass


class UnknownReferenceError(ContractViolation):
    """Raised when a hypothesis references a non-existent ID."""
    pass


class InvariantViolationError(ContractViolation):
    """Raised when PredictionResult cross-field invariants are violated."""
    pass
