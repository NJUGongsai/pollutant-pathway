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

from dataclasses import dataclass
from typing import Any, Optional

from reaction_agent.agent.baseline import BaselineGate, BaselineViolationError
from reaction_agent.agent.grounding import (
    GroundingError,
    assert_id_belongs_to_run,
    build_grounded_run,
)
from reaction_agent.agent.provider import (
    Provider,
    ProviderRequest,
    ProviderSpec,
    FakeProvider,
)
from reaction_agent.policies.p4_decision_policy import P4_POLICY_VERSION
from reaction_agent.schemas.result import PredictionResult


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
            self.provider: Provider = self._require_bounded(provider)
        elif provider_spec is not None:
            self.provider: Provider = FakeProvider(self._with_budget(provider_spec))
        else:
            raise ValueError("AgentLoop requires provider_spec or provider")
        self._baseline_gate = baseline_gate

    @staticmethod
    def _require_bounded(provider: Provider) -> Provider:
        """Validate an INJECTED provider has a positive call budget (P7-T6-01).

        The injected-provider path must NOT silently accept an unbounded
        (``max_calls=0``) provider — the loop must never run an unbounded LLM
        interaction (P7-T1T3-03), on the spec path OR the injection path.
        """
        spec = getattr(provider, "spec", None)
        max_calls = getattr(spec, "max_calls", 0)
        if max_calls <= 0:
            raise ValueError(
                "AgentLoop injected provider must have max_calls > 0 (bounded); "
                f"got max_calls={max_calls!r} — a loop must never run an "
                "unbounded LLM interaction"
            )
        return provider

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

    # -- real agent run (T7) -------------------------------------------

    def run(
        self,
        substrate: str,
        *,
        max_steps: int = 100,
        counters: Any = None,
    ) -> "AgentRunResult":
        """Run the bounded agent loop over a mandatory baseline.

        Consumes the injected provider's action stream (one action per
        ``provider.call``) to drive the agent tool surface
        (expand/compare/choose/prioritize/stop). The mandatory baseline is
        obtained FIRST (via ``obtain_baseline``); every agent-claimed ID is
        grounded against the typed result (``build_grounded_run`` /
        ``assert_id_belongs_to_run``) — invented candidate/evidence IDs are
        rejected (recorded, run continues). Unauthorized tools are rejected
        by the allowlist. A defense-in-depth final pass calls
        ``counters.escape(...)`` if any invented ID nonetheless appears in
        the final selection (should never happen if grounding is intact).

        ``counters`` (optional ``HardGateCounters``): per-gate escape counters;
        stays all-zero when the defense rejects every invention.
        """
        baseline = self.obtain_baseline()
        grounded = build_grounded_run(baseline)
        actions: list[dict] = []
        selected: list[str] = []
        rejections: list[dict] = []
        grounded_evidence: set[str] = set()
        step = 0
        for step in range(max_steps):
            request = ProviderRequest(
                messages=[{"role": "user", "content": substrate}],
                tools=[{"name": t} for t in sorted(ALLOWED_TOOLS)],
            )
            response = self.provider.call(request)
            action = dict(response.content or {})
            tool = action.get("tool")
            if tool is None or tool == "stop":
                break
            # P7-T2-02: allowlist rejects unauthorized tools (no structure
            # generator / test-label path on the surface).
            if tool not in ALLOWED_TOOLS:
                rejections.append({
                    "tool": tool, "reason": "allowlist_violation", "action": action,
                })
                continue
            # Grounding: every agent-claimed ID must belong to the run.
            try:
                self._validate_action_ids(grounded, action)
            except GroundingError as exc:
                rejections.append({
                    "tool": tool, "reason": "grounding",
                    "detail": str(exc), "action": action,
                })
                continue
            # Valid action -> execute + record.
            actions.append(action)
            if tool == "choose_t_s":
                cid = action.get("candidate_id")
                if cid:
                    selected.append(cid)
            elif tool == "expand_evidence":
                eid = action.get("evidence_id")
                if eid:
                    grounded_evidence.add(eid)
            # compare_ids / prioritize: recorded as actions, no state change.
        abstained = len(selected) == 0
        result = AgentRunResult(
            baseline=baseline,
            selected_candidate_ids=tuple(selected),
            actions=tuple(actions),
            tool_calls=len(actions),
            steps=step + 1,
            abstained=abstained,
            grounded_evidence_ids=tuple(sorted(grounded_evidence)),
            rejections=tuple(rejections),
        )
        # Defense-in-depth: if grounding missed an invention, the final result
        # would carry an unknown ID -> count the escape (gate stays 0 when the
        # defense is intact). Non-vacuous: this WOULD catch a pass-through.
        if counters is not None:
            for cid in result.selected_candidate_ids:
                if cid not in grounded.candidate_ids:
                    counters.escape("invented_candidate_id")
            for eid in result.grounded_evidence_ids:
                if eid not in grounded.evidence_ids:
                    counters.escape("invented_evidence_id")
        return result

    @staticmethod
    def _validate_action_ids(grounded: Any, action: dict) -> None:
        """Ground every ID the action references against the typed run.

        Raises ``GroundingError`` if any candidate/evidence id is unknown.
        """
        for key, kind in (
            ("candidate_id", "candidate"),
            ("candidate_id_a", "candidate"),
            ("candidate_id_b", "candidate"),
            ("evidence_id", "evidence"),
        ):
            value = action.get(key)
            if value is not None:
                assert_id_belongs_to_run(grounded, kind=kind, id_=value)


@dataclass(frozen=True)
class AgentRunResult:
    """Immutable result of one agent loop run.

    ``baseline`` is the typed ``PredictionResult`` obtained first (mandatory).
    ``selected_candidate_ids`` / ``grounded_evidence_ids`` are grounded (every
    ID belongs to the run — no inventions). ``rejections`` records inventions
    the defense rejected (allowlist / grounding) so the run continued.
    """

    baseline: PredictionResult
    selected_candidate_ids: tuple[str, ...]
    actions: tuple[dict, ...]
    tool_calls: int
    steps: int
    abstained: bool
    grounded_evidence_ids: tuple[str, ...]
    rejections: tuple[dict, ...]


__all__ = [
    "ALLOWED_TOOLS",
    "FORBIDDEN_TOOLS",
    "AgentToolViolationError",
    "AgentLoop",
    "AgentRunResult",
]