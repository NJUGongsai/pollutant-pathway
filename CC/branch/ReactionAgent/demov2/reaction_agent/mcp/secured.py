"""P6 MCP Service — T5/T6 secured facade.

``SecuredKernel`` is a thin facade over the Phase-A ``ReactionMCPKernel``
that wires in the resource manager (opaque URI + access control + tenant
binding + retention) and the Phase-B hardening hooks (payload cap, protocol
pin, cumulative budget). It is the single entry point a deployment uses
when it wants fail-closed multi-tenant behavior; the bare kernel remains
available for unsecured / legacy / LLM-less single-tenant use.

The facade delegates every tool call to the kernel (so the F3 side-effect
matrix still holds through this layer — predict remains
``append_write_immutable_run``, reads remain read-only, expand remains
``append_immutable_child_run``). It adds:

- ``handle(tool, payload, ctx, protocol_version)`` — secured dispatch.
- ``resolve_resource(uri, ctx)`` — authorized opaque-URI resolution.
- ``sweep()`` — retention purge (TTL + count cap).
"""
from __future__ import annotations

from typing import Any, Callable, Optional

from reaction_agent.mcp.idempotency import IdempotencyStore
from reaction_agent.mcp.resources import AccessContext, ResourceManager, RetentionPolicy
from reaction_agent.mcp.runs import RunStore
from reaction_agent.mcp.tools import ReactionMCPKernel


class SecuredKernel:
    """Secured facade: kernel + resource manager + hardening hooks."""

    def __init__(
        self,
        run_store: RunStore,
        idem_store: IdempotencyStore,
        policy: Optional[RetentionPolicy] = None,
        payload_max_bytes: Optional[int] = None,
        protocol_version: Optional[str] = None,
        budget_guard: Any | None = None,
        snapshots: Callable[[str], bool] | None = None,
    ):
        self._kernel = ReactionMCPKernel(
            run_store=run_store,
            idem_store=idem_store,
            snapshots=snapshots,
            policy=policy,
            payload_max_bytes=payload_max_bytes,
            protocol_version=protocol_version,
            budget_guard=budget_guard,
        )
        self._resources = ResourceManager(run_store, policy, idem_store=idem_store)

    # -- dispatch (delegates to the kernel; preserves F3 side effects) --

    def handle(
        self,
        tool_name: str,
        payload: dict,
        ctx: Optional[AccessContext] = None,
        protocol_version: Optional[str] = None,
    ) -> dict:
        return self._kernel.handle(
            tool_name, payload, ctx=ctx, protocol_version=protocol_version
        )

    # -- resource resolution (opaque URI + access control + retention) --

    def resolve_resource(self, uri: str, ctx: Optional[AccessContext]) -> dict:
        return self._resources.resolve(uri, ctx)

    def mint_manifest_uri(self, run_id: str) -> str:
        return self._resources.mint_manifest_uri(run_id)

    def mint_evidence_uri(self, run_id: str, evidence_id: str) -> str:
        return self._resources.mint_evidence_uri(run_id, evidence_id)

    # -- retention sweep --

    def sweep(self) -> int:
        return self._resources.sweep()
