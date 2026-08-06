"""P7-T1: provider adapter (final_plan §10.2).

Abstracts the LLM provider behind a small typed interface so the kernel and
agent loop never fixate on a specific vendor. The adapter owns:

- provider/model/revision identity
- request payload (messages/tools)
- sampling (temperature/seed)
- budgets (max calls per run)
- structured output (typed ProviderResponse)
- retries (transient infrastructure failures only)
- typed provider failure taxonomy

Typed provider failure is SEPARATE from scientific abstention — a provider
failure must never be reported as a scientific abstention (final_plan §10.9,
common.py forbids biological_probability on schemas).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pydantic import Field, field_validator

from reaction_agent.schemas.common import StrictModel, NonEmptyStr


# -- typed provider failure taxonomy --

class ProviderFailure(Exception):
    """Base class for all typed provider failures."""

    code = "PROVIDER_FAILURE"

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class ProviderInfrastructureError(ProviderFailure):
    """Transient infrastructure failure (network, timeout, 5xx). Retryable."""

    code = "PROVIDER_INFRASTRUCTURE"


class ProviderInvalidRequestError(ProviderFailure):
    """Provider rejected the request (bad payload, 4xx). Not retryable."""

    code = "PROVIDER_INVALID_REQUEST"


class ProviderBudgetError(ProviderFailure):
    """Run call budget exhausted before a provider response."""

    code = "PROVIDER_BUDGET"


class ProviderMalformedOutputError(ProviderFailure):
    """Provider response failed to parse into a typed result."""

    code = "PROVIDER_MALFORMED_OUTPUT"


# -- provider spec --

class ProviderSpec(StrictModel):
    """Immutable provider configuration.

    ``provider``/``model``/``revision`` pin the identity; ``temperature``/
    ``seed`` control sampling; ``max_calls`` caps the run budget.
    """

    provider: NonEmptyStr
    model: NonEmptyStr
    revision: str = ""
    temperature: float = 0.0
    seed: int | None = None
    max_calls: int = 0  # 0 = unlimited (kernel injects a real budget)

    @field_validator("temperature")
    @classmethod
    def _temperature_range(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"temperature must be in [0,1], got {v}")
        return v

    @field_validator("seed")
    @classmethod
    def _seed_non_negative(cls, v: int | None) -> int | None:
        if v is not None and v < 0:
            raise ValueError(f"seed must be non-negative, got {v}")
        return v

    @field_validator("max_calls")
    @classmethod
    def _max_calls_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError(f"max_calls must be non-negative, got {v}")
        return v


# -- request / response --

class ProviderRequest(StrictModel):
    """A single provider call payload: messages + tools."""

    messages: list[dict] = Field(default_factory=list)
    tools: list[dict] = Field(default_factory=list)


class ProviderResponse(StrictModel):
    """Structured provider output (typed)."""

    provider: NonEmptyStr
    model: NonEmptyStr
    content: dict = Field(default_factory=dict)


# -- provider interface --

@runtime_checkable
class Provider(Protocol):
    """Minimal provider surface the kernel/agent loop depends on."""

    def call(self, request: ProviderRequest) -> ProviderResponse:
        """Perform one provider call, returning a typed response.

        Raises a ProviderFailure subclass on failure.
        """
        ...


class FakeProvider:
    """Deterministic fake provider for tests (no real API calls).

    Enforces ``max_calls`` budget. ``scripted_failures`` lets tests inject
    transient infrastructure errors before a real response.
    """

    def __init__(self, spec: ProviderSpec, scripted_failures: int = 0):
        self.spec = spec
        self._scripted_failures = scripted_failures
        self._calls = 0

    def call(self, request: ProviderRequest) -> ProviderResponse:
        if self.spec.max_calls > 0 and self._calls >= self.spec.max_calls:
            raise ProviderBudgetError(
                f"max_calls={self.spec.max_calls} exceeded for "
                f"{self.spec.provider}/{self.spec.model}"
            )
        self._calls += 1
        if self._calls <= self._scripted_failures:
            raise ProviderInfrastructureError("scripted transient failure")
        return ProviderResponse(
            provider=self.spec.provider,
            model=self.spec.model,
            content={},
        )


# -- retry policy --

class RetryPolicy(StrictModel):
    """Retry policy: retries ONLY transient infrastructure failures."""

    max_attempts: int = 1


def retry_call(
    provider: Provider,
    policy: RetryPolicy,
    request: ProviderRequest,
) -> ProviderResponse:
    """Call ``provider`` with retry on ProviderInfrastructureError only.

    Other ProviderFailure subclasses propagate immediately (not retried).
    """
    last_error: ProviderInfrastructureError | None = None
    for attempt in range(policy.max_attempts):
        try:
            return provider.call(request)
        except ProviderInfrastructureError as exc:
            last_error = exc
            # transient: retry until attempts exhausted
    if last_error is not None:
        raise last_error
    # max_attempts < 1 guard (should not happen given validation default)
    raise ProviderInfrastructureError("no attempts permitted by RetryPolicy")


__all__ = [
    "ProviderFailure",
    "ProviderInfrastructureError",
    "ProviderInvalidRequestError",
    "ProviderBudgetError",
    "ProviderMalformedOutputError",
    "ProviderSpec",
    "ProviderRequest",
    "ProviderResponse",
    "Provider",
    "FakeProvider",
    "RetryPolicy",
    "retry_call",
]