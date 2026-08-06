"""P7-T3: ProductionSelectionHypothesis policy (final_plan §10.4).

Enforces the production agent's permission boundary and surfaces a
priority-only decision over existing hypotheses. Reuses the existing
ProductionSelectionHypothesis schema and validate_hypothesis_against_context
— it does NOT recreate the schema.

Scope:
- ID validation (delegated to the shared schema validator)
- transform/site exists, support exists (delegated + surfaced)
- rationale summary, policy version, priority only

Permission boundary:
- CAN: expand local evidence / compare IDs / choose T/S / prioritize / stop
- CANNOT: create structure / mutate rank.lane.ledger / write abstention
"""

from __future__ import annotations

from enum import Enum

from pydantic import Field, model_validator

from reaction_agent.schemas.common import StrictModel, NonEmptyStr
from reaction_agent.schemas.hypothesis import (
    ProductionSelectionHypothesis,
    HypothesisValidationContext,
    validate_hypothesis_against_context,
)


# -- permission boundary --

class AgentAction(str, Enum):
    """Actions the production agent may attempt.

    The ``ALLOWED`` set is the positive permission boundary; everything else
    is forbidden and raises PolicyViolationError.
    """

    # allowed
    EXPAND_LOCAL_EVIDENCE = "expand_local_evidence"
    COMPARE_IDS = "compare_ids"
    CHOOSE_T_S = "choose_t_s"
    PRIORITIZE = "prioritize"
    STOP = "stop"

    # forbidden
    CREATE_STRUCTURE = "create_structure"
    MUTATE_RANK = "mutate_rank"
    MUTATE_LANE = "mutate_lane"
    MUTATE_LEDGER = "mutate_ledger"
    WRITE_ABSTENTION = "write_abstention"


ALLOWED_ACTIONS = frozenset({
    AgentAction.EXPAND_LOCAL_EVIDENCE,
    AgentAction.COMPARE_IDS,
    AgentAction.CHOOSE_T_S,
    AgentAction.PRIORITIZE,
    AgentAction.STOP,
})

FORBIDDEN_ACTIONS = frozenset({
    AgentAction.CREATE_STRUCTURE,
    AgentAction.MUTATE_RANK,
    AgentAction.MUTATE_LANE,
    AgentAction.MUTATE_LEDGER,
    AgentAction.WRITE_ABSTENTION,
})


class PolicyViolationError(Exception):
    """Raised when the agent attempts a forbidden action.

    Accepts an ``AgentAction`` OR a raw string / None (defensive: the loop may
    pass untyped input). The offending value is preserved on ``action``.
    """

    def __init__(self, action):
        self.action = action
        label = action.value if isinstance(action, AgentAction) else str(action)
        super().__init__(f"forbidden production action: {label}")


# -- policy decision --

class PolicyDecision(StrictModel):
    """Priority-only outcome: an ordered list of EXISTING hypothesis IDs.

    Strict schema forbids rank/lane/ledger mutation and structure creation —
    any such field is rejected at construction time.
    """

    policy_version: NonEmptyStr
    priority: list[NonEmptyStr] = Field(default_factory=list)

    @model_validator(mode="after")
    def _non_empty_priority(self) -> "PolicyDecision":
        if not self.priority:
            raise ValueError("PolicyDecision requires a non-empty priority list")
        return self


# -- policy --

class ProductionPolicy:
    """Production agent policy: permission boundary + priority decision."""

    def __init__(self, policy_version: str):
        if not policy_version or not policy_version.strip():
            raise ValueError("policy_version must be non-empty")
        self.policy_version = policy_version

    def assert_allowed(self, action) -> None:
        """Raise PolicyViolationError if the action is forbidden.

        Accepts an ``AgentAction`` or a raw string / None (defensive, P2
        closure P7-T1T3-01). Raw strings are normalized to ``AgentAction`` so
        allowed actions pass; None / unknown / forbidden values raise a typed
        ``PolicyViolationError`` (never AttributeError).
        """
        if action is None:
            raise PolicyViolationError(action)
        if not isinstance(action, AgentAction):
            try:
                action = AgentAction(action)
            except ValueError:
                # unknown raw string -> typed violation, not a bare ValueError
                raise PolicyViolationError(action) from None
        if action not in ALLOWED_ACTIONS:
            raise PolicyViolationError(action)

    def decide(
        self,
        context: HypothesisValidationContext,
        hypotheses: list[ProductionSelectionHypothesis],
    ) -> PolicyDecision:
        """Validate every hypothesis against context, then emit a
        priority-only decision over their existing hypothesis IDs.

        Raises UnknownReferenceError (via the shared validator) when any
        hypothesis cites unknown IDs / missing relations — fail-closed.

        Duplicate ``hypothesis_id`` values are deduped preserving first-seen
        order (P2 closure P7-T1T3-02) — never double-listed.
        """
        seen: set[str] = set()
        ordered: list[ProductionSelectionHypothesis] = []
        for h in hypotheses:
            validate_hypothesis_against_context(h, context)
            if h.hypothesis_id not in seen:
                seen.add(h.hypothesis_id)
                ordered.append(h)
        return PolicyDecision(
            policy_version=self.policy_version,
            priority=[h.hypothesis_id for h in ordered],
        )


__all__ = [
    "AgentAction",
    "ALLOWED_ACTIONS",
    "FORBIDDEN_ACTIONS",
    "PolicyViolationError",
    "PolicyDecision",
    "ProductionPolicy",
]