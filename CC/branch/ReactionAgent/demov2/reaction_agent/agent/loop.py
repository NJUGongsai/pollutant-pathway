"""P7-T2/T6: agent loop (final_plan §10.3) — provider injection + tool surface.

Phase 2 (T2) established the loop's bounded LLM interaction. Phase 3 (T6)
closes two P2 findings:

- **P7-T2-03**: the loop now accepts an injected ``Provider`` instance (or a
  ``provider_spec``, kept for backward compat) instead of hard-coding
  ``FakeProvider``. A dual-provider transparent swap pin proves the loop is
  provider-agnostic. ``require_baseline`` is renamed to ``obtain_baseline`` to
  disambiguate from ``BaselineGate.require_baseline`` (same-name-different-
  semantics).
- **P7-T2-02**: the agent tool surface is an explicit ALLOWLIST that
  structurally contains NO structure-generator / test-label path. Any tool not
  in the allowlist — including ``generate_structure`` / ``read_test_labels`` —
  is rejected with a typed ``AgentToolViolationError``.
"""

from __future__ import annotations

from reaction_agent.agent.baseline import BaselineGate, BaselineViolationError
from reaction_agent.agent.provider import (
    Provider,
    ProviderSpec,
    FakeProvider,
)


# -- agent tool surface (P7-T2-02) --

# The ONLY tools the production agent may call. Structurally excludes the
# low-level structure generator and test-label access (no-invention, §10.3).
ALLOWED_TOOLS = frozenset({
    "expand_evidence",
    "compare_ids",
    "choose_t_s",
    "prioritize",
    "stop",
})

# Tools that MUST NOT exist on the agent surface (forbidden/structural).
FORBIDDEN_TOOLS = frozenset({
    "generate_structure",
    "read_test_labels",
    "access_test_labels",
})


class AgentToolViolationError(Exception):
    """Typed rejection: an agent tried to call a tool outside its allowlist.

    Covers unknown tools AND the structurally-forbidden generator/label tools.
    """

    code = "AGENT_TOOL_VIOLATION"

    def __init__(self, tool: str):
        self.tool = tool
        super().__init__(f"tool {tool!r} is not on the production agent surface")


class AgentLoop:
    """Bounded agent loop over a mandatory baseline.

    The loop injects a positive provider ``max_calls`` budget at construction
    (P7-T1T3-03): a real loop must never run an UNBOUNDED LLM interaction.
    The provider is injected (P7-T2-03) — the kernel/loop stays
    provider-agnostic via the T1 provider adapter.
    """

    def __init__(
        self,
        provider_spec: ProviderSpec | None = None,
        provider: Provider | None = None,
        baseline_gate: BaselineGate | None = None,
    ):
        if provider is not None:
            self.provider: Provider = provider
        elif provider_spec is not None:
            self.provider: Provider = FakeProvider(self._with_budget(provider_spec))
        else:
            raise ValueError("AgentLoop requires provider_spec or provider")
        self._baseline_gate = baseline_gate

    @staticmethod
    def _with_budget(spec: ProviderSpec) -> ProviderSpec:
        """Return a spec with a positive ``max_calls`` budget (immutable)."""
        if spec.max_calls > 0:
            return spec
        # Default bounded budget for a loop-used provider (never unlimited).
        return spec.model_copy(update={"max_calls": 1_000})

    # -- tool surface (P7-T2-02) --

    @property
    def tools(self) -> frozenset:
        """The agent's allowed tool surface — structurally no generator/label."""
        return ALLOWED_TOOLS

    def call_tool(self, tool: str, *args, **kwargs):
        """Dispatch an agent tool, rejecting anything off-allowlist.

        Raises ``AgentToolViolationError`` (typed) for unknown tools and the
        structurally-forbidden generator/label tools.
        """
        if tool not in ALLOWED_TOOLS:
            raise AgentToolViolationError(tool)
        handler = getattr(self, f"_tool_{tool}", None)
        if handler is None:
            raise AgentToolViolationError(tool)
        return handler(*args, **kwargs)

    def assert_tool_allowed(self, tool: str) -> None:
        """Typed rejection if ``tool`` is not on the agent surface."""
        if tool not in ALLOWED_TOOLS:
            raise AgentToolViolationError(tool)

    # -- handlers (production actions only) --

    def _tool_expand_evidence(self, *args, **kwargs):  # noqa: ARG002
        return {"status": "expand_evidence"}

    def _tool_compare_ids(self, *args, **kwargs):  # noqa: ARG002
        return {"status": "compare_ids"}

    def _tool_choose_t_s(self, *args, **kwargs):  # noqa: ARG002
        return {"status": "choose_t_s"}

    def _tool_prioritize(self, *args, **kwargs):  # noqa: ARG002
        return {"status": "prioritize"}

    def _tool_stop(self, *args, **kwargs):  # noqa: ARG002
        return {"status": "stop"}

    # -- mandatory baseline (P7-T2-03 rename) --

    def obtain_baseline(self):
        """Route the mandatory baseline acquisition through the gate.

        Renamed from ``require_baseline`` (T2 Round 1) to disambiguate from
        ``BaselineGate.require_baseline`` (same-name-different-semantics).
        """
        if self._baseline_gate is None:
            raise BaselineViolationError(
                "AgentLoop must be wired with a BaselineGate to obtain the "
                "mandatory baseline"
            )
        return self._baseline_gate.obtain_baseline()


__all__ = [
    "ALLOWED_TOOLS",
    "FORBIDDEN_TOOLS",
    "AgentToolViolationError",
    "AgentLoop",
]