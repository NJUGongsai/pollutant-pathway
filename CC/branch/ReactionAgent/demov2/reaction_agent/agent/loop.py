"""P7-T2: agent loop (final_plan §10.3).

The agent loop's FIRST step must obtain a mandatory deterministic baseline
run via MCP predict (through :class:`BaselineGate`). The loop constructs its
LLM provider with a positive call budget (``max_calls > 0``) so the LLM
interaction is bounded (P7-T1T3-03) — the kernel stays provider-agnostic via
the T1 provider adapter.
"""

from __future__ import annotations

from reaction_agent.agent.baseline import BaselineGate
from reaction_agent.agent.provider import (
    Provider,
    ProviderSpec,
    FakeProvider,
)


class AgentLoop:
    """Bounded agent loop over a mandatory baseline.

    The loop injects a positive provider ``max_calls`` budget at construction
    (P7-T1T3-03): a real loop must never run an UNBOUNDED LLM interaction.
    """

    def __init__(
        self,
        provider_spec: ProviderSpec,
        baseline_gate: BaselineGate | None = None,
    ):
        self.provider: Provider = FakeProvider(self._with_budget(provider_spec))
        self._baseline_gate = baseline_gate

    @staticmethod
    def _with_budget(spec: ProviderSpec) -> ProviderSpec:
        """Return a spec with a positive ``max_calls`` budget (immutable)."""
        if spec.max_calls > 0:
            return spec
        # Default bounded budget for a loop-used provider (never unlimited).
        return spec.model_copy(update={"max_calls": 1_000})

    def require_baseline(self):
        """Route the mandatory baseline acquisition through the gate."""
        if self._baseline_gate is None:
            raise RuntimeError(
                "AgentLoop requires a BaselineGate to obtain the mandatory baseline"
            )
        return self._baseline_gate.obtain_baseline()


__all__ = ["AgentLoop"]