"""P6 MCP Service — T6 budget guard.

Per-tenant cumulative budget enforcement for the predict mutation. The
schema already caps ``budgets.max_candidates`` at 200 per request; this
guard adds a *cumulative* cap across all of a tenant's runs so a noisy
tenant cannot exhaust the corpus. Fail-closed: ``check_and_commit`` raises
``BudgetExceededError`` BEFORE mutating the ledger, so a rejected request
does not consume budget.

Thread-safe: the kernel calls ``check_and_commit`` inside the idempotency
layer's create-run lambda (under the idempotency store's lock), so budget
checks serialize per-key; the internal lock also guards the ledger map for
any direct callers.
"""
from __future__ import annotations

import threading
from typing import Optional

from reaction_agent.mcp.errors import BudgetExceededError


class BudgetGuard:
    """Cumulative per-tenant budget ledger."""

    __slots__ = ("_cap", "_spent", "_lock")

    def __init__(self, per_tenant_cap: int):
        if per_tenant_cap <= 0:
            raise ValueError("per_tenant_cap must be positive")
        self._cap = per_tenant_cap
        self._spent: dict[str, int] = {}
        self._lock = threading.Lock()

    def check_and_commit(
        self,
        tenant_id: Optional[str],
        requested: int,
    ) -> None:
        """Atomically check + commit ``requested`` units for ``tenant_id``.

        Raises ``BudgetExceededError`` (typed) if the cumulative total would
        exceed the cap, WITHOUT mutating the ledger (a rejected request is
        free). Idempotent reuse does not call this — the kernel only charges
        on NEW run creation.
        """
        if requested <= 0:
            return  # nothing to charge (e.g. read-only tool with no budgets)
        tenant = tenant_id or "default"
        with self._lock:
            spent = self._spent.get(tenant, 0)
            if spent + requested > self._cap:
                raise BudgetExceededError(
                    f"budget exceeded for tenant '{tenant}': "
                    f"{spent + requested} > {self._cap}"
                )
            self._spent[tenant] = spent + requested

    def spent(self, tenant_id: str) -> int:
        """Inspect cumulative spend (test/diagnostic helper)."""
        with self._lock:
            return self._spent.get(tenant_id or "default", 0)
