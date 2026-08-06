"""P7 agent layer — provider adapter, production policy, baseline gate, loop.

Contains the LLM-facing adapter (provider.py), the production
ProductionSelectionHypothesis policy (policy.py), the mandatory baseline gate
(baseline.py), and the bounded agent loop (loop.py). The kernel stays
provider-agnostic: the agent loop consumes a Provider via the adapter.
"""

from __future__ import annotations

from reaction_agent.agent.provider import (
    Provider,
    ProviderSpec,
    ProviderRequest,
    ProviderResponse,
    FakeProvider,
)
from reaction_agent.agent.policy import (
    AgentAction,
    ProductionPolicy,
    PolicyDecision,
)
from reaction_agent.agent.baseline import BaselineGate
from reaction_agent.agent.loop import (
    AgentLoop,
    ALLOWED_TOOLS,
    FORBIDDEN_TOOLS,
    AgentToolViolationError,
)

__all__ = [
    "Provider",
    "ProviderSpec",
    "ProviderRequest",
    "ProviderResponse",
    "FakeProvider",
    "AgentAction",
    "ProductionPolicy",
    "PolicyDecision",
    "BaselineGate",
    "AgentLoop",
    "ALLOWED_TOOLS",
    "FORBIDDEN_TOOLS",
    "AgentToolViolationError",
]