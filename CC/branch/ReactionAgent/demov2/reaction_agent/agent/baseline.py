"""P7-T2: mandatory deterministic baseline gate (final_plan §10.3).

The agent loop's FIRST step MUST obtain a deterministic baseline run via MCP
predict. Every bypass path is typed-rejected:

1. skip baseline (agent step before any baseline obtained)
2. direct call to the low-level structure generator
3. access to test labels

P7-T0②-02 contract: a blocked-kernel baseline failure (predictor raises)
surfaces as a TYPED ``BaselineViolationError`` — never a bare exception
piercing the agent loop.
"""

from __future__ import annotations

from typing import Callable, Any

from reaction_agent.mcp.idempotency import IdempotencyStore
from reaction_agent.mcp.runs import RunStore
from reaction_agent.mcp.tools import (
    TOOL_PREDICT,
    ReactionMCPKernel,
    resolve_prediction_result,
)
from reaction_agent.schemas.result import PredictionResult


# -- typed baseline failure taxonomy --

class BaselineViolationError(Exception):
    """Base class for all mandatory-baseline violations."""

    code = "BASELINE_VIOLATION"

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class SkipBaselineError(BaselineViolationError):
    """Agent step attempted before the mandatory baseline was obtained."""

    code = "SKIP_BASELINE"


class DirectStructureGeneratorError(BaselineViolationError):
    """Agent attempted to call the low-level structure generator directly."""

    code = "DIRECT_STRUCTURE_GENERATOR"


class LabelAccessViolationError(BaselineViolationError):
    """Agent attempted to access test labels."""

    code = "TEST_LABEL_ACCESS"


# -- baseline gate --

class BaselineGate:
    """The ONLY path to a deterministic, mandatory baseline run.

    The agent loop must call :meth:`obtain_baseline` (which routes through MCP
    predict) before acting on baseline-derived evidence. ``require_baseline``
    after that returns the frozen typed result; before it, it raises
    ``SkipBaselineError``.
    """

    def __init__(
        self,
        kernel: ReactionMCPKernel,
        run_store: RunStore,
        predict_payload: dict,
    ):
        self._kernel = kernel
        self._run_store = run_store
        self._predict_payload = predict_payload
        self._baseline: PredictionResult | None = None

    def obtain_baseline(self) -> PredictionResult:
        """Run the deterministic baseline via MCP predict and freeze it.

        A blocked kernel or any resolution failure (missing run_id, missing
        run, malformed stored result) is wrapped into a typed
        ``BaselineViolationError`` — never leaked as a bare exception.
        """
        try:
            out = self._kernel.handle(TOOL_PREDICT, self._predict_payload)
            result = resolve_prediction_result(self._run_store, out["run_id"])
        except BaselineViolationError:
            raise
        except Exception as exc:  # noqa: BLE001 — typed fail-closed
            raise BaselineViolationError(
                f"baseline predict/resolve failed (blocked kernel): "
                f"{type(exc).__name__}: {exc}"
            ) from exc
        if result is None:
            raise BaselineViolationError(
                "baseline predict produced no typed PredictionResult"
            )
        self._baseline = result
        return result

    def require_baseline(self) -> PredictionResult:
        """Return the frozen baseline, or raise SkipBaselineError if none yet.

        Returns a deep copy so callers cannot mutate the cached baseline
        (immutability contract).
        """
        if self._baseline is None:
            raise SkipBaselineError(
                "skip baseline: agent step attempted before the mandatory "
                "baseline run was obtained"
            )
        return self._baseline.model_copy(deep=True)

    def reject_direct_structure_generator(self) -> None:
        """Typed rejection of the low-level structure generator bypass."""
        raise DirectStructureGeneratorError(
            "direct low-level structure generator call is forbidden; "
            "baseline must come from MCP predict"
        )

    def reject_test_label_access(self) -> None:
        """Typed rejection of the test-label access bypass."""
        raise LabelAccessViolationError(
            "access to test labels is forbidden; baseline uses train evidence only"
        )


__all__ = [
    "BaselineViolationError",
    "SkipBaselineError",
    "DirectStructureGeneratorError",
    "LabelAccessViolationError",
    "BaselineGate",
]