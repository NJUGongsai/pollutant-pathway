"""T1 RED tests — provider adapter (final_plan §10.2).

Must FAIL (RED) until ``reaction_agent/agent/provider.py`` exists.

Scope (final_plan §10.2):
- provider/model/revision
- messages/tools
- temperature/seed
- budgets
- structured output
- retries
- typed provider failure
- kernel does NOT fixate provider (adapter injection)

Iron rules: fake/mock provider for all tests (no real API calls); typed
provider failure must NEVER be conflated with scientific abstention.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from reaction_agent.agent.provider import (
    ProviderFailure,
    ProviderInfrastructureError,
    ProviderInvalidRequestError,
    ProviderBudgetError,
    ProviderMalformedOutputError,
    ProviderSpec,
    ProviderRequest,
    ProviderResponse,
    Provider,
    FakeProvider,
    RetryPolicy,
    retry_call,
)


# -- provider/model/revision --

class TestProviderIdentity:
    def test_spec_identity_fields(self):
        spec = ProviderSpec(
            provider="anthropic",
            model="claude-fable-5",
            revision="rev-1",
        )
        assert spec.provider == "anthropic"
        assert spec.model == "claude-fable-5"
        assert spec.revision == "rev-1"

    def test_spec_rejects_missing_provider(self):
        with pytest.raises(ValidationError):
            ProviderSpec(provider="", model="m")

    def test_spec_rejects_missing_model(self):
        with pytest.raises(ValidationError):
            ProviderSpec(provider="anthropic", model="")

    def test_spec_rejects_unknown_field(self):
        with pytest.raises(ValidationError):
            ProviderSpec(
                provider="anthropic",
                model="m",
                made_up_field="x",
            )


# -- temperature / seed --

class TestSampling:
    def test_temperature_seed_stored(self):
        spec = ProviderSpec(
            provider="anthropic",
            model="m",
            temperature=0.2,
            seed=42,
        )
        assert spec.temperature == 0.2
        assert spec.seed == 42

    def test_temperature_range_enforced(self):
        with pytest.raises(ValidationError):
            ProviderSpec(provider="a", model="m", temperature=2.0)

    def test_seed_non_negative(self):
        with pytest.raises(ValidationError):
            ProviderSpec(provider="a", model="m", seed=-1)


# -- messages / tools --

class TestRequestPayload:
    def test_request_carries_messages_and_tools(self):
        req = ProviderRequest(
            messages=[{"role": "user", "content": "hi"}],
            tools=[{"name": "expand"}],
        )
        assert req.messages[0]["role"] == "user"
        assert req.tools[0]["name"] == "expand"


# -- budgets --

class TestBudgets:
    def test_budget_limits_calls(self):
        spec = ProviderSpec(
            provider="anthropic",
            model="m",
            max_calls=2,
        )
        fake = FakeProvider(spec=spec)
        fake.call(ProviderRequest(messages=[]))
        fake.call(ProviderRequest(messages=[]))
        with pytest.raises(ProviderBudgetError):
            fake.call(ProviderRequest(messages=[]))


# -- structured output --

class TestStructuredOutput:
    def test_fake_provider_returns_structured_output(self):
        spec = ProviderSpec(provider="anthropic", model="m")
        fake = FakeProvider(spec=spec)
        resp = fake.call(ProviderRequest(messages=[]))
        assert isinstance(resp, ProviderResponse)
        assert resp.content == {}

    def test_response_typed(self):
        spec = ProviderSpec(provider="anthropic", model="m")
        fake = FakeProvider(spec=spec)
        resp = fake.call(ProviderRequest(messages=[]))
        assert resp.model == spec.model


# -- retries --

class TestRetries:
    def test_retry_transient_failure_then_success(self):
        spec = ProviderSpec(provider="anthropic", model="m")
        # Fails twice with infra error, succeeds on 3rd attempt.
        calls = {"n": 0}

        class FlakyProvider(Provider):
            def call(self, request):
                calls["n"] += 1
                if calls["n"] < 3:
                    raise ProviderInfrastructureError("transient")
                return ProviderResponse(
                    provider=spec.provider,
                    model=spec.model,
                    content={},
                )

        policy = RetryPolicy(max_attempts=5)
        resp = retry_call(FlakyProvider(), policy, ProviderRequest(messages=[]))
        assert resp.content == {}
        assert calls["n"] == 3

    def test_retry_exhausts_raises_typed(self):
        spec = ProviderSpec(provider="anthropic", model="m")

        class AlwaysFail(Provider):
            def call(self, request):
                raise ProviderInfrastructureError("down")

        policy = RetryPolicy(max_attempts=2)
        with pytest.raises(ProviderFailure):
            retry_call(AlwaysFail(), policy, ProviderRequest(messages=[]))

    def test_non_retryable_error_not_retried(self):
        spec = ProviderSpec(provider="anthropic", model="m")
        calls = {"n": 0}

        class BadRequest(Provider):
            def call(self, request):
                calls["n"] += 1
                raise ProviderInvalidRequestError("bad payload")

        policy = RetryPolicy(max_attempts=5)
        with pytest.raises(ProviderInvalidRequestError):
            retry_call(BadRequest(), policy, ProviderRequest(messages=[]))
        assert calls["n"] == 1  # not retried

    def test_max_attempts_must_be_positive(self):
        # config error must be rejected at the schema layer, not disguised
        # as a transient ProviderInfrastructureError at runtime.
        with pytest.raises(ValidationError):
            RetryPolicy(max_attempts=0)


# -- typed provider failure / injection --

class TestTypedFailureAndInjection:
    def test_infrastructure_error_is_typed_failure(self):
        assert issubclass(ProviderInfrastructureError, ProviderFailure)

    def test_malformed_output_is_typed_failure(self):
        assert issubclass(ProviderMalformedOutputError, ProviderFailure)

    def test_kernel_does_not_fixate_provider(self):
        """The agent loop consumes Provider via the adapter; swapping the
        fake for a different fake must be transparent."""
        spec = ProviderSpec(provider="anthropic", model="m")
        fake_a = FakeProvider(spec=spec)
        fake_b = FakeProvider(spec=spec)

        # A thin consumer that only sees the Provider interface.
        def consume(p: Provider) -> ProviderResponse:
            return p.call(ProviderRequest(messages=[]))

        r1 = consume(fake_a)
        r2 = consume(fake_b)
        assert isinstance(r1, ProviderResponse)
        assert isinstance(r2, ProviderResponse)